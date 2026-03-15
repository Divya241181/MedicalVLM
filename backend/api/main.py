from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from jose import jwt, JWTError
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os

load_dotenv()

app = FastAPI(title="Medical VLM API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()
JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(
            credentials.credentials,
            JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False}
        )
        return payload.get("sub")   # returns user_id
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

@app.get("/health")
async def health():
    return {"status": "ok", "model_loaded": False}

@app.post("/generate")
async def generate_report(
    file: UploadFile = File(...),
    user_id: str = Depends(verify_token)
):
    # Placeholder — real model code added in Week 7
    if file.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(status_code=400, detail="Only JPEG and PNG accepted")
    return {
        "report": "Model not yet loaded. Train on Kaggle first.",
        "tokens": [],
        "attention_map": None,
        "latency_ms": 0,
        "user_id": user_id
    }

@app.get("/history")
async def get_history(user_id: str = Depends(verify_token)):
    # Placeholder — Supabase query added in Week 7
    return {"reports": [], "total": 0, "user_id": user_id}
