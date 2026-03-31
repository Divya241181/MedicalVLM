"""
MedicalVLM Backend — LLaVA-1.5-7b-hf Edition
FastAPI + HuggingFace LLaVA + GradCAM + fpdf2 + Supabase
"""

from __future__ import annotations

import base64
import io
import logging
import os
import re
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

import cv2
import numpy as np
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from PIL import Image

load_dotenv()

# ── Logging ───────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("medvlm")

# ── Env ───────────────────────────────────────────────────────────────
SUPABASE_URL         = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY    = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
HF_HOME              = os.getenv("HF_HOME", "./hf_cache")
PORT                 = int(os.getenv("PORT", 8000))

os.environ.setdefault("HF_HOME", HF_HOME)

# ── Model globals ─────────────────────────────────────────────────────
model_instance  = None
processor_inst  = None
device          = None
model_loaded    = False
model_error     = ""


# ── Lifespan — load model once at startup ────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    global model_instance, processor_inst, device, model_loaded, model_error
    try:
        import torch
        from transformers import LlavaForConditionalGeneration, LlavaProcessor, BitsAndBytesConfig

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Device: {device} | CUDA available: {torch.cuda.is_available()}")

        processor_inst = LlavaProcessor.from_pretrained(
            "llava-hf/llava-1.5-7b-hf",
            cache_dir=HF_HOME,
        )

        if device.type == "cuda":
            # ── 4-bit quantisation — fits in ~4 GB VRAM (RTX 3050 / Colab T4) ──
            logger.info("Loading LLaVA in 4-bit (NF4) quantisation …")
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
            )
            model_instance = LlavaForConditionalGeneration.from_pretrained(
                "llava-hf/llava-1.5-7b-hf",
                quantization_config=bnb_config,
                device_map="auto",
                cache_dir=HF_HOME,
            )
        else:
            # CPU fallback — float32, no quantisation
            logger.info("Loading LLaVA in float32 on CPU (slow) …")
            model_instance = LlavaForConditionalGeneration.from_pretrained(
                "llava-hf/llava-1.5-7b-hf",
                torch_dtype=torch.float32,
                device_map=None,
                cache_dir=HF_HOME,
            )
            model_instance = model_instance.to(device)

        model_instance.eval()
        model_loaded = True
        logger.info("✅  LLaVA model loaded successfully")
    except Exception as exc:
        model_error = str(exc)
        logger.error(f"❌  Model load failed: {exc}")
        model_loaded = False

    yield  # ── application runs here ──

    logger.info("Shutting down — releasing model.")
    del model_instance, processor_inst
    import torch
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    logger.info("GPU memory released.")


# ── App ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="MedicalVLM API",
    version="3.0.0",
    description="LLaVA-powered chest X-ray analysis",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "*",  # Colab / ngrok support — restrict in production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ══════════════════════════════════════════════════════════════════════
# AUTH
# ══════════════════════════════════════════════════════════════════════
security = HTTPBearer()


def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """Validates Supabase JWT; returns user_id (UUID string)."""
    try:
        from supabase import create_client

        sb       = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        response = sb.auth.get_user(credentials.credentials)
        if not response or not response.user:
            raise HTTPException(status_code=401, detail="Invalid token")
        return response.user.id
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning(f"Token verification error: {exc}")
        raise HTTPException(status_code=401, detail="Invalid or expired token")


# ══════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════

STRUCTURED_PROMPT_TEMPLATE = """You are an expert radiologist analysing a chest X-ray.
{history_block}
Provide a detailed structured medical report with these sections:

CLINICAL HISTORY:
[Summarise patient history or write "Not provided" if unavailable]

FINDINGS:
[Describe what you observe in the chest X-ray — lung fields, cardiac silhouette, mediastinum, bones, soft tissue]

IMPRESSION:
[Provide concise diagnostic impression / differential diagnoses]

RECOMMENDATIONS:
[Suggest follow-up, additional investigations, or clinical management steps]

Now analyse the provided chest X-ray image and produce the report in exactly the above format."""


def build_prompt(patient_history: Optional[str] = None) -> str:
    if patient_history and patient_history.strip():
        history_block = f"Patient history: {patient_history.strip()}"
    else:
        history_block = ""
    return STRUCTURED_PROMPT_TEMPLATE.format(history_block=history_block)


def llava_prompt_wrap(text_prompt: str) -> str:
    """Wrap text in LLaVA conversation format expected by the processor."""
    return f"USER: <image>\n{text_prompt}\nASSISTANT:"


def clean_report(raw: str) -> str:
    """Strip the echoed prompt / USER:/ASSISTANT: tokens from LLaVA output."""
    if not raw:
        return raw
    # Remove everything up to and including ASSISTANT:
    raw = re.sub(r".*?ASSISTANT:\s*", "", raw, flags=re.DOTALL).strip()
    # Collapse excess whitespace while preserving newlines between sections
    raw = re.sub(r"\n{3,}", "\n\n", raw)
    raw = re.sub(r" {2,}", " ", raw)
    return raw.strip()


def read_image(data: bytes) -> Image.Image:
    """Convert raw bytes → PIL RGB image."""
    img = Image.open(io.BytesIO(data)).convert("RGB")
    return img


def image_to_base64(img: Image.Image, fmt: str = "PNG") -> str:
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return base64.b64encode(buf.getvalue()).decode()


# ── Inference core ────────────────────────────────────────────────────
def run_llava(
    pil_image: Image.Image,
    text_prompt: str,
    max_new_tokens: int = 512,
) -> str:
    import torch

    conversation = llava_prompt_wrap(text_prompt)
    inputs = processor_inst(
        text=conversation,
        images=pil_image,
        return_tensors="pt",
    )
    inputs = {k: v.to(device) for k, v in inputs.items()}
    with torch.no_grad():
        generated_ids = model_instance.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=True,
            temperature=0.7,
            top_p=0.9,
            repetition_penalty=1.2,
        )
    output_text = processor_inst.decode(
        generated_ids[0], skip_special_tokens=True
    )
    return clean_report(output_text)


# ── GradCAM heatmap ───────────────────────────────────────────────────
def build_gradcam_heatmap(pil_image: Image.Image) -> str:
    """
    Apply GradCAM on LLaVA's vision tower last encoder layer.
    Returns base64-encoded PNG of the overlay.
    Falls back to placeholder if pytorch-grad-cam is unavailable.
    """
    try:
        import torch
        from pytorch_grad_cam import GradCAM
        from pytorch_grad_cam.utils.image import show_cam_on_image

        vision_tower   = model_instance.vision_tower
        target_layer   = [vision_tower.vision_model.encoder.layers[-1].layer_norm1]
        rgb_np         = np.array(pil_image.resize((336, 336))).astype(np.float32) / 255.0

        # Build a forward wrapper that returns vision features
        class VisionWrapper(torch.nn.Module):
            def __init__(self, tower):
                super().__init__()
                self.tower = tower

            def forward(self, pixel_values):
                out = self.tower(pixel_values=pixel_values, output_attentions=False)
                # pool to [B, C]
                return out.last_hidden_state[:, 0, :]

        wrapper = VisionWrapper(vision_tower).to(device)

        preproc = processor_inst.image_processor
        proc_out = preproc(images=pil_image.resize((336, 336)), return_tensors="pt")
        pixel_values = proc_out["pixel_values"].to(device)

        cam = GradCAM(model=wrapper, target_layers=target_layer)
        grayscale_cam = cam(
            input_tensor=pixel_values,
            targets=None,
        )
        grayscale_cam = grayscale_cam[0]

        visualization = show_cam_on_image(rgb_np, grayscale_cam, use_rgb=True)
        overlay_img   = Image.fromarray(visualization)
        return image_to_base64(overlay_img)

    except ImportError:
        logger.warning("pytorch-grad-cam not installed — using attention fallback")
        return _attention_fallback_heatmap(pil_image)
    except Exception as exc:
        logger.warning(f"GradCAM failed: {exc} — using attention fallback")
        return _attention_fallback_heatmap(pil_image)


def _attention_fallback_heatmap(pil_image: Image.Image) -> str:
    """Simple saliency-like heatmap when GradCAM is unavailable."""
    try:
        img_np  = np.array(pil_image.resize((224, 224))).astype(np.float32)
        gray    = cv2.cvtColor(img_np.astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)
        norm    = (gray - gray.min()) / (gray.max() - gray.min() + 1e-8)
        colored = cv2.applyColorMap((norm * 255).astype(np.uint8), cv2.COLORMAP_JET)
        rgb     = cv2.cvtColor(colored, cv2.COLOR_BGR2RGB)
        orig    = img_np.astype(np.uint8)
        overlay = cv2.addWeighted(orig, 0.55, rgb, 0.45, 0)
        return image_to_base64(Image.fromarray(overlay))
    except Exception:
        return image_to_base64(pil_image.resize((224, 224)))


# ── Supabase history ─────────────────────────────────────────────────
async def save_to_history(
    user_id: str,
    image_name: str,
    report: str,
    endpoint: str = "generate",
):
    try:
        from supabase import create_client

        sb   = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        data = {
            "user_id"          : user_id,
            "image_name"       : image_name,
            "generated_report" : report,
            "bleu_score"       : None,
            "endpoint"         : endpoint,
        }
        sb.table("report_history").insert(data).execute()
        logger.info(f"Saved report to history for user {user_id[:8]}")
    except Exception as exc:
        logger.error(f"History save failed: {exc}")


# ── PDF generation ────────────────────────────────────────────────────
def generate_pdf(
    report: str,
    patient_history: Optional[str],
    pil_image: Image.Image,
) -> bytes:
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()

    # Header
    pdf.set_fill_color(20, 184, 166)          # teal-500
    pdf.rect(0, 0, 210, 22, "F")
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 14, "MedVLM — AI Radiology Report", ln=True, align="C")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 8, f"Generated: {datetime.now().strftime('%Y-%m-%d  %H:%M:%S')}", ln=True, align="C")
    pdf.ln(6)

    # Disclaimer
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(180, 0, 0)
    pdf.multi_cell(0, 5, "FOR RESEARCH / EDUCATIONAL USE ONLY — NOT FOR CLINICAL DIAGNOSIS")
    pdf.ln(4)

    # Patient history block
    if patient_history and patient_history.strip():
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(30, 30, 30)
        pdf.cell(0, 8, "Patient History", ln=True)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(60, 60, 60)
        pdf.multi_cell(0, 6, patient_history.strip())
        pdf.ln(4)

    # X-ray thumbnail
    try:
        thumb = pil_image.resize((160, 160))
        tmp_path = f"/tmp/xray_{uuid.uuid4().hex}.jpg"
        thumb.save(tmp_path, "JPEG")
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(30, 30, 30)
        pdf.cell(0, 8, "X-Ray Image", ln=True)
        pdf.image(tmp_path, x=10, w=70)
        pdf.ln(4)
        os.remove(tmp_path)
    except Exception:
        pass

    # Report body
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 8, "Generated Report", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(40, 40, 40)
    for line in report.split("\n"):
        line = line.strip()
        if not line:
            pdf.ln(2)
            continue
        # Section headers in bold
        if re.match(r"^(CLINICAL HISTORY|FINDINGS|IMPRESSION|RECOMMENDATIONS)\s*:", line):
            pdf.set_font("Helvetica", "B", 10)
            pdf.multi_cell(0, 6, line)
            pdf.set_font("Helvetica", "", 10)
        else:
            pdf.multi_cell(0, 6, line)

    # Footer
    pdf.set_y(-15)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 10, "MedVLM  |  Powered by LLaVA-1.5-7b  |  AI-Assisted Analysis", align="C")

    return bytes(pdf.output())


# ══════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ══════════════════════════════════════════════════════════════════════

@app.get("/health")
async def health():
    import torch
    return {
        "status"      : "ok",
        "model_loaded": model_loaded,
        "model_error" : model_error,
        "device"      : str(device) if device else "not loaded",
        "cuda_available": torch.cuda.is_available(),
    }


# ── /generate ─────────────────────────────────────────────────────────
@app.post("/generate")
async def generate_report(
    file            : UploadFile = File(...),
    patient_history : str        = Form(""),
    user_id         : str        = Depends(verify_token),
):
    """
    Primary endpoint — returns full structured radiology report,
    GradCAM heatmap overlay, and metadata.
    """
    if file.content_type not in ("image/jpeg", "image/png", "image/jpg"):
        raise HTTPException(400, "Only JPEG and PNG files are accepted.")

    raw = await file.read()
    if len(raw) > 20 * 1024 * 1024:
        raise HTTPException(413, "File too large — max 20 MB.")

    if not model_loaded:
        raise HTTPException(503, f"Model not ready. {model_error or 'Please try again shortly.'}")

    t0 = time.time()
    try:
        pil_image = read_image(raw)
        prompt    = build_prompt(patient_history or None)
        report    = run_llava(pil_image, prompt, max_new_tokens=512)
        heatmap   = build_gradcam_heatmap(pil_image)
        ms        = int((time.time() - t0) * 1000)

        await save_to_history(
            user_id    = user_id,
            image_name = file.filename or "upload.png",
            report     = report,
            endpoint   = "generate",
        )

        return JSONResponse({
            "report"               : report,
            "heatmap_base64"       : heatmap,
            "attention_map"        : heatmap,           # alias for legacy frontend key
            "confidence_level"     : "High" if model_loaded else "Low",
            "processing_time_ms"   : ms,
            "patient_history"      : patient_history or "",
        })

    except (MemoryError, Exception) as exc:
        import torch
        if isinstance(exc, torch.cuda.OutOfMemoryError):
            torch.cuda.empty_cache()
            raise HTTPException(500, "GPU out of memory — try a smaller image.")
        logger.error(f"/generate error: {exc}", exc_info=True)
        raise HTTPException(500, f"Report generation failed: {exc}")


# ── /briefing ─────────────────────────────────────────────────────────
@app.post("/briefing")
async def xray_briefing(
    file    : UploadFile = File(...),
    user_id : str        = Depends(verify_token),
):
    """
    Returns a short 3-5 sentence plain-English summary suitable for patients.
    Avoids medical jargon.
    """
    if not model_loaded:
        raise HTTPException(503, "Model not ready.")

    raw = await file.read()
    t0  = time.time()

    try:
        pil_image = read_image(raw)
        prompt    = (
            "You are explaining a chest X-ray to a patient with no medical background. "
            "In 3 to 5 simple sentences, describe what you see in this X-ray. "
            "Avoid medical jargon. Be reassuring and clear. "
            "Do NOT use bullet points or section headers — just plain paragraphs."
        )
        briefing = run_llava(pil_image, prompt, max_new_tokens=200)
        ms       = int((time.time() - t0) * 1000)

        await save_to_history(
            user_id    = user_id,
            image_name = file.filename or "upload.png",
            report     = briefing,
            endpoint   = "briefing",
        )

        return JSONResponse({
            "briefing"           : briefing,
            "processing_time_ms" : ms,
        })
    except Exception as exc:
        logger.error(f"/briefing error: {exc}", exc_info=True)
        raise HTTPException(500, f"Briefing generation failed: {exc}")


# ── /compare ─────────────────────────────────────────────────────────
@app.post("/compare")
async def compare_xrays(
    file_prev   : UploadFile = File(...),
    file_curr   : UploadFile = File(...),
    user_id     : str        = Depends(verify_token),
):
    """
    Generates independent reports for two X-rays then produces an interval
    change summary.
    """
    if not model_loaded:
        raise HTTPException(503, "Model not ready.")

    raw_prev = await file_prev.read()
    raw_curr = await file_curr.read()
    t0       = time.time()

    try:
        prompt = build_prompt()
        img_p  = read_image(raw_prev)
        img_c  = read_image(raw_curr)

        prev_report = run_llava(img_p, prompt, max_new_tokens=512)
        curr_report = run_llava(img_c, prompt, max_new_tokens=512)

        comparison_prompt = (
            f"Below are two radiology reports for the same patient taken at different times.\n\n"
            f"PREVIOUS REPORT:\n{prev_report}\n\n"
            f"CURRENT REPORT:\n{curr_report}\n\n"
            "Based on these two reports, summarise the interval changes observed. "
            "What has improved, worsened, or remained stable? "
            "Be concise and clinically precise."
        )

        # Compare text-only (no image needed for this step)
        inputs = processor_inst(
            text=llava_prompt_wrap(comparison_prompt),
            images=img_c,       # provide current image as context
            return_tensors="pt",
        )
        import torch
        inputs = {k: v.to(device) for k, v in inputs.items()}
        with torch.no_grad():
            out = model_instance.generate(
                **inputs,
                max_new_tokens=300,
                do_sample=True,
                temperature=0.7,
                top_p=0.9,
                repetition_penalty=1.2,
            )
        interval_changes = clean_report(
            processor_inst.decode(out[0], skip_special_tokens=True)
        )

        ms = int((time.time() - t0) * 1000)

        await save_to_history(
            user_id    = user_id,
            image_name = f"{file_prev.filename} vs {file_curr.filename}",
            report     = f"[COMPARE]\n{interval_changes}",
            endpoint   = "compare",
        )

        return JSONResponse({
            "previous_report"    : prev_report,
            "current_report"     : curr_report,
            "interval_changes"   : interval_changes,
            "processing_time_ms" : ms,
        })
    except Exception as exc:
        logger.error(f"/compare error: {exc}", exc_info=True)
        raise HTTPException(500, f"Comparison failed: {exc}")


# ── /export-pdf ───────────────────────────────────────────────────────
@app.post("/export-pdf")
async def export_pdf(
    file            : UploadFile = File(...),
    patient_history : str        = Form(""),
    report          : str        = Form(""),
    user_id         : str        = Depends(verify_token),
):
    """
    Generates a report (if not already done) and returns a downloadable PDF.
    """
    if not model_loaded:
        raise HTTPException(503, "Model not ready.")

    raw = await file.read()
    try:
        pil_image = read_image(raw)
        if not report or not report.strip():
            prompt    = build_prompt(patient_history or None)
            report    = run_llava(pil_image, prompt, max_new_tokens=512)
        pdf_bytes = generate_pdf(report, patient_history or None, pil_image)

        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": (
                    f'attachment; filename="medvlm_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
                )
            },
        )
    except Exception as exc:
        logger.error(f"/export-pdf error: {exc}", exc_info=True)
        raise HTTPException(500, f"PDF export failed: {exc}")


# ── /history ──────────────────────────────────────────────────────────
@app.get("/history")
async def get_history(
    user_id : str = Depends(verify_token),
    limit   : int = 20,
    offset  : int = 0,
):
    try:
        from supabase import create_client

        sb       = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        response = (
            sb.table("report_history")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .offset(offset)
            .execute()
        )
        return {"reports": response.data, "total": len(response.data)}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"/history error: {exc}")
        raise HTTPException(500, f"Failed to fetch history: {exc}")