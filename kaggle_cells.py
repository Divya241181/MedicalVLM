# Cell 1 — check dataset is mounted:
import os
dataset_path = '/kaggle/input/'
try:
    print(os.listdir(dataset_path))
except FileNotFoundError:
    print(f"Directory {dataset_path} not found (standard locally).")

# Cell 2 — install dependencies:
# !pip install transformers==4.40.0 peft==0.10.0 accelerate wandb \
#             rouge-score bert-score nltk -q
print("All dependencies installed (placeholder for notebook)")

# Cell 3 — verify GPU:
import torch
print("CUDA available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))
    print("VRAM:", round(torch.cuda.get_device_properties(0).total_memory / 1e9, 1), "GB")
