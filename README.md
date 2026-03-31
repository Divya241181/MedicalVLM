# MedVLM — Advanced AI Radiology Platform

A state-of-the-art, full-stack Medical Vision-Language Model (VLM) application designed to automate and enhance chest X-ray interpretation. 

This platform integrates the powerful **LLaVA-1.5-7b** multimodal model with a high-performance **FastAPI** backend and a modern **React 19** frontend, providing radiologists and patients with structured diagnostic insights, visual heatmaps, and historical tracking.

---

## 🚀 Key Features

- **🔬 LLaVA-1.5 Powered Analysis**: Leverages `llava-hf/llava-1.5-7b-hf` for deep multimodal understanding of medical imagery.
- **📊 Structured Reports**: Automatically generates clinical reports with dedicated sections for *Findings*, *Impression*, and *Recommendations*.
- **🔥 Visual Explainability (GradCAM)**: Provides GradCAM-based heatmaps overlaying X-rays to visualize the model's focus areas during diagnosis.
- **📄 Professional PDF Export**: Instant generation of downloadable, formatted radiology reports using `fpdf2`.
- **🏥 Patient-Friendly Briefings**: An AI-powered "briefing" mode that simplifies complex medical jargon into clear, reassuring language for patients.
- **⏱️ Interval Comparison**: Compare current and previous X-rays to detect interval changes and track progression over time.
- **🔐 Secure Healthcare Hub**: Full **Supabase** integration for HIPAA-ready authentication and secure storage of patient report history.
- **⚡ Performance Optimized**: Supports CUDA acceleration with FP16 precision and intelligent GPU memory management.

---

## 🛠️ Tech Stack

**Frontend:**
- **React 19 (Vite)** — Blazing fast UI development.
- **Tailwind CSS** — Modern, responsive design system.
- **Lucide React** — Premium iconography.
- **Supabase JS** — Real-time backend integration.

**Backend:**
- **Python 3.10+**
- **FastAPI / Uvicorn** — High-performance asynchronous API.
- **HuggingFace Transformers / Accelerate** — Cutting-edge VLM pipeline.
- **PyTorch / Bitsandbytes** — GPU-accelerated inference with memory optimization.
- **Pytorch-Grad-CAM** — Explainable AI visualizations.
- **FPDF2** — Structured PDF generation.

**Database & Authentication:**
- **Supabase** — PostgreSQL database and GoTrue Auth.

---

## 📂 Project Structure

```text
MedicalVLM/
├── backend/                  # FastAPI Application and AI Logic
│   ├── api/
│   │   └── main.py           # Core FastAPI endpoints & Inference logic
│   ├── ml/                   # Model-related data processing
│   └── checkpoints/          # Local model storage (if applicable)
├── frontend/                 # Vite/React Frontend App
│   ├── src/                  # React Components, Pages, Stores
│   └── public/               # Static assets
├── hf_cache/                 # Cached HuggingFace model files
├── outputs/                  # Exported metrics and reports
├── .env                      # Environment configurations
├── requirements.txt          # Python dependencies
├── run.bat                   # One-click Windows startup script
├── colab_setup.ipynb         # Google Colab deployment notebook
└── supabase_schema.sql       # Database table & policy definitions
```

---

## 🖥️ Setup & Installation

### 1. Requirements
Ensure you have the following installed:
- **Node.js (v18+)**
- **Python 3.10+**
- **NVIDIA GPU (8GB+ VRAM)** — Highly recommended for LLaVA-1.5-7b inference.

### 2. Environment Configuration
Create a `.env` file in the root and in the `frontend` directory:
```ini
# Found in: MedicalVLM/.env
SUPABASE_URL="your-project-url"
SUPABASE_ANON_KEY="your-anon-key"
SUPABASE_SERVICE_KEY="your-service-role-key"
HF_HOME="./hf_cache"
```

### 3. Backend Setup
```bash
# Create virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Frontend Setup
```bash
cd frontend
npm install
```

---

## ⚡ Running the Application

### One-Click Startup (Windows)
Simply run the master startup script from the root:
```bash
.\run.bat
```
This launches the **FastAPI Backend (Port 8000)** and **Vite Frontend (Port 5173)** in separate windows.

### Manual Launch
- **Backend:** `uvicorn backend.api.main:app --reload --port 8000`
- **Frontend:** `cd frontend && npm run dev`

---

## 🔧 Database Configuration
Initialize your Supabase project by running the scripts in the root:
1. `supabase_schema.sql`: Sets up the `report_history` table.
2. `supabase_policy_update.sql`: Configures Row Level Security (RLS) for user privacy.

---

## 🤖 Deep Learning Implementation Details
The model pipeline uses `LlavaForConditionalGeneration` with `device_map="auto"` to intelligently load shards across available GPU memory. Inference uses a custom prompt wrapper (`USER: <image>\n{text}\nASSISTANT:`) to optimize LLaVA's instruction-following capabilities. GradCAM is implemented on the last layer of the vision encoder (`layer_norm1`) to provide the most relevant spatial attention maps for diagnosis.
