from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from jose import jwt, JWTError
from PIL import Image
from io import BytesIO
import torch
import torch.nn as nn
import numpy as np
import cv2
import base64
import time
import os
import logging

load_dotenv()

# ── Logging ──────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── App ───────────────────────────────────────────────────────────────
app = FastAPI(title="Medical VLM API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Auth ──────────────────────────────────────────────────────────────
security       = HTTPBearer()
JWT_SECRET     = os.getenv("SUPABASE_JWT_SECRET")
SUPABASE_URL   = os.getenv("SUPABASE_URL")
SUPABASE_KEY   = os.getenv("SUPABASE_ANON_KEY")
MODEL_PATH     = os.getenv("MODEL_PATH", "./checkpoints")

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        # Supabase JWTs are signed with HS256 using the JWT secret
        payload = jwt.decode(
            credentials.credentials,
            JWT_SECRET,
            algorithms=["HS256"],
            options={
                "verify_aud"        : False,
                "verify_exp"        : True,
                "verify_signature"  : True
            }
        )
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        return user_id
    except JWTError as e:
        logger.error(f"JWT error: {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired token")
# ── Model globals (loaded once at startup) ────────────────────────────
model_instance  = None
processor_inst  = None
device          = None
model_loaded    = False

# ── Projector MLP (must match training definition) ────────────────────
class ProjectorMLP(nn.Module):
    def __init__(self, input_dim=768, hidden_dim=1024, output_dim=768):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.GELU(),
            nn.LayerNorm(hidden_dim),
            nn.Linear(hidden_dim, output_dim)
        )
    def forward(self, x):
        return self.net(x)

# ── Load model at startup ─────────────────────────────────────────────
@app.on_event("startup")
async def load_model():
    global model_instance, processor_inst, device, model_loaded

    try:
        from transformers import AutoModelForCausalLM, AutoProcessor
        from peft import PeftModel

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Using device: {device}")

        lora_dir      = os.path.join(MODEL_PATH, "best", "lora")
        projector_path = os.path.join(MODEL_PATH, "best", "projector.pt")

        if not os.path.exists(lora_dir):
            logger.warning(f"LoRA weights not found at {lora_dir}")
            logger.warning("Starting without model — /generate will return placeholder")
            return

        logger.info("Loading processor...")
        processor_inst = AutoProcessor.from_pretrained("microsoft/git-base")

        logger.info("Loading base model...")
        base_model = AutoModelForCausalLM.from_pretrained(
            "microsoft/git-base",
            torch_dtype=torch.float32
        )

        logger.info("Loading LoRA adapters...")
        model_instance = PeftModel.from_pretrained(base_model, lora_dir)
        model_instance = model_instance.to(device)
        model_instance.eval()

        logger.info("Loading projector...")
        projector = ProjectorMLP()
        projector.load_state_dict(
            torch.load(projector_path, map_location=device)
        )
        projector = projector.to(device)
        projector.eval()

        # Attach projector to model for easy access
        model_instance.projector = projector

        model_loaded = True
        logger.info("Model loaded successfully")

    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        model_loaded = False

# ── Image preprocessing ───────────────────────────────────────────────
def preprocess_image(image_bytes: bytes) -> torch.Tensor:
    from torchvision import transforms

    image = Image.open(BytesIO(image_bytes)).convert("RGB")

    # CLAHE enhancement
    gray     = np.array(image.convert("L"))
    clahe    = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    rgb      = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2RGB)
    image    = Image.fromarray(rgb)

    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std =[0.229, 0.224, 0.225]
        )
    ])

    pixel_values = transform(image).unsqueeze(0)  # [1, 3, 224, 224]
    return pixel_values

# ── Attention heatmap ─────────────────────────────────────────────────
def build_heatmap(pixel_values: torch.Tensor, generated_ids: torch.Tensor) -> str:
    """
    Extract cross-attention from the model and build a heatmap.
    Returns base64-encoded PNG string.
    """
    try:
        attn_weights = {}

        def hook_fn(module, input, output):
            if isinstance(output, tuple) and len(output) > 1:
                if output[1] is not None:
                    attn_weights["attn"] = output[1].detach().cpu()

        # Register hook on first decoder attention layer
        hook = None
        for name, module in model_instance.named_modules():
            if "attention" in name.lower() and hasattr(module, "forward"):
                try:
                    hook = module.register_forward_hook(hook_fn)
                    break
                except Exception:
                    continue

        with torch.no_grad():
            model_instance(
                pixel_values=pixel_values.to(device),
                input_ids=generated_ids.to(device)
            )

        if hook:
            hook.remove()

        if "attn" not in attn_weights:
            return _placeholder_heatmap(pixel_values)

        # Process attention weights
        attn = attn_weights["attn"]  # [1, heads, T, T]
        attn = attn.mean(dim=1)      # mean over heads → [1, T, T]
        attn = attn[0].mean(dim=0)   # mean over tokens → [T]

        # Try to reshape to spatial map
        seq_len = attn.shape[0]
        side    = int(seq_len ** 0.5)
        if side * side == seq_len:
            spatial = attn[:side*side].reshape(side, side)
        else:
            spatial = attn[:196].reshape(14, 14) if seq_len >= 196 \
                      else attn.reshape(1, -1).repeat(14, 1)[:14, :14]

        # Normalize and upsample to 224×224
        spatial = spatial.numpy().astype(np.float32)
        spatial = (spatial - spatial.min()) / (spatial.max() - spatial.min() + 1e-8)
        heatmap = cv2.resize(spatial, (224, 224), interpolation=cv2.INTER_LINEAR)

        # Apply colormap
        colored = cv2.applyColorMap(
            (heatmap * 255).astype(np.uint8),
            cv2.COLORMAP_JET
        )

        # Overlay on original image
        orig = np.array(
            Image.open(BytesIO(
                _tensor_to_bytes(pixel_values)
            )).resize((224, 224))
        )
        overlay = cv2.addWeighted(orig, 0.5, colored, 0.5, 0)

        # Encode to base64
        _, buf = cv2.imencode(".png", overlay)
        return base64.b64encode(buf).decode("utf-8")

    except Exception as e:
        logger.warning(f"Heatmap generation failed: {e} — using placeholder")
        return _placeholder_heatmap(pixel_values)


def _tensor_to_bytes(pixel_values: torch.Tensor) -> bytes:
    """Convert normalized tensor back to image bytes."""
    mean = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
    std  = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)
    img  = pixel_values.squeeze(0).cpu() * std + mean
    img  = (img.clamp(0, 1).numpy().transpose(1, 2, 0) * 255).astype(np.uint8)
    _, buf = cv2.imencode(".png", cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
    return buf.tobytes()


def _placeholder_heatmap(pixel_values: torch.Tensor) -> str:
    """Return the original image as base64 when heatmap fails."""
    img_bytes = _tensor_to_bytes(pixel_values)
    return base64.b64encode(img_bytes).decode("utf-8")

# ── Save report to Supabase ───────────────────────────────────────────
async def save_to_history(user_id: str, image_name: str,
                          report: str, bleu_score: float):
    try:
        from supabase import create_client
        sb = create_client(SUPABASE_URL, SUPABASE_KEY)
        sb.table("report_history").insert({
            "user_id"          : user_id,
            "image_name"       : image_name,
            "generated_report" : report,
            "bleu_score"       : bleu_score
        }).execute()
        logger.info(f"Report saved to history for user {user_id[:8]}...")
    except Exception as e:
        logger.warning(f"Failed to save to history: {e}")

# ══════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ══════════════════════════════════════════════════════════════════════

@app.get("/health")
async def health():
    return {
        "status"      : "ok",
        "model_loaded": model_loaded,
        "device"      : str(device) if device else "not loaded"
    }


@app.post("/generate")
async def generate_report(
    file    : UploadFile = File(...),
    user_id : str        = Depends(verify_token)
):
    # ── Validate file ────────────────────────────────────────────────
    if file.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(
            status_code=400,
            detail="Only JPEG and PNG files are accepted"
        )

    image_bytes = await file.read()
    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="File too large. Maximum size is 10MB"
        )

    # ── Placeholder if model not loaded ──────────────────────────────
    if not model_loaded:
        return JSONResponse({
            "report"        : "Model is loading. Please try again in 30 seconds.",
            "tokens"        : [],
            "attention_map" : None,
            "bleu4"         : None,
            "rougeL"        : None,
            "latency_ms"    : 0
        })

    start_time = time.time()

    try:
        # ── Preprocess image ─────────────────────────────────────────
        pixel_values = preprocess_image(image_bytes).to(device)

        # ── Generate report ───────────────────────────────────────────
        with torch.no_grad():
            generated_ids = model_instance.generate(
                pixel_values       = pixel_values,
                max_new_tokens     = 128,
                num_beams          = 4,
                no_repeat_ngram_size = 3,
                early_stopping     = True,
                length_penalty     = 1.0
            )

        # ── Decode report ─────────────────────────────────────────────
        report = processor_inst.tokenizer.decode(
            generated_ids[0],
            skip_special_tokens=True
        ).strip()

        tokens = processor_inst.tokenizer.convert_ids_to_tokens(
            generated_ids[0]
        )

        # ── Build attention heatmap ───────────────────────────────────
        attention_map = build_heatmap(pixel_values, generated_ids)

        latency_ms = int((time.time() - start_time) * 1000)
        logger.info(f"Report generated in {latency_ms}ms for user {user_id[:8]}...")

        # ── Save to Supabase history ──────────────────────────────────
        await save_to_history(
            user_id    = user_id,
            image_name = file.filename or "uploaded_image.png",
            report     = report,
            bleu_score = None  # no ground truth at inference time
        )

        return JSONResponse({
            "report"        : report,
            "tokens"        : [t for t in tokens if t not in
                               ["<s>", "</s>", "<pad>"]],
            "attention_map" : attention_map,
            "bleu4"         : None,
            "rougeL"        : None,
            "latency_ms"    : latency_ms
        })

    except torch.cuda.OutOfMemoryError:
        torch.cuda.empty_cache()
        raise HTTPException(
            status_code=500,
            detail="GPU out of memory. Please try a smaller image."
        )
    except Exception as e:
        logger.error(f"Generation error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Report generation failed: {str(e)}"
        )


@app.get("/history")
async def get_history(
    user_id : str = Depends(verify_token),
    limit   : int = 20,
    offset  : int = 0
):
    try:
        from supabase import create_client
        sb = create_client(SUPABASE_URL, SUPABASE_KEY)

        response = sb.table("report_history") \
            .select("*") \
            .eq("user_id", user_id) \
            .order("created_at", desc=True) \
            .limit(limit) \
            .offset(offset) \
            .execute()

        return {
            "reports": response.data,
            "total"  : len(response.data)
        }

    except Exception as e:
        logger.error(f"History fetch error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch report history"
        )