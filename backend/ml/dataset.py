import os
import numpy as np
import pandas as pd
import torch
import cv2
from torch.utils.data import Dataset
from PIL import Image
from torchvision import transforms
from transformers import AutoProcessor

class IUXrayDataset(Dataset):
    """
    PyTorch Dataset for IU X-Ray.
    Loads image → CLAHE enhancement → transforms → tensor.
    Tokenizes report text → input_ids, attention_mask, labels.
    """

    def __init__(self, df, images_dir, processor_name="microsoft/git-base", max_length=128, split='train'):
        self.df         = df.reset_index(drop=True)
        self.images_dir = images_dir
        self.max_length = max_length
        self.split      = split
        
        # Load the specified processor
        self.processor  = AutoProcessor.from_pretrained(processor_name)
        self.transform  = self._build_transforms()

    def _build_transforms(self):
        """Builds augmentation pipeline based on split"""
        if self.split == 'train':
            return transforms.Compose([
                transforms.Resize((224, 224)),
                transforms.RandomHorizontalFlip(p=0.5),
                transforms.RandomRotation(degrees=10),
                transforms.ColorJitter(brightness=0.2, contrast=0.2),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                     std =[0.229, 0.224, 0.225])
            ])
        else:
            return transforms.Compose([
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                     std =[0.229, 0.224, 0.225])
            ])

    def _clahe(self, pil_img):
        """Contrast Limited Adaptive Histogram Equalization to make X-rays clearer"""
        gray     = np.array(pil_img.convert('L'))
        clahe    = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        rgb      = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2RGB)
        return Image.fromarray(rgb)

    def __len__(self):
        return len(self.df)

    def __getitem__(self, idx):
        row = self.df.iloc[idx]

        # 1. Image Processing
        img_path     = os.path.join(self.images_dir, row['image_file'])
        image        = Image.open(img_path).convert('RGB')
        image        = self._clahe(image)
        pixel_values = self.transform(image)          # [3, 224, 224]

        # 2. Text Tokenization
        enc = self.processor.tokenizer(
            str(row['report']),
            max_length=self.max_length,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )
        input_ids      = enc['input_ids'].squeeze(0)       # [128]
        attention_mask = enc['attention_mask'].squeeze(0)  # [128]

        # 3. Label Preparation (ignores padding in loss calculation)
        labels = input_ids.clone()
        labels[labels == self.processor.tokenizer.pad_token_id] = -100

        return {
            'pixel_values'  : pixel_values,
            'input_ids'     : input_ids,
            'attention_mask': attention_mask,
            'labels'        : labels,
            'report'        : str(row['report']),
            'image_file'    : str(row['image_file'])
        }
