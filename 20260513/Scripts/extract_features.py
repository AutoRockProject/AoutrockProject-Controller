"""
pretrained EfficientNet-B0 (timm) で画像から特徴量を抽出し、
numpy 配列として保存する。

入力: 20260513/data/clips/extraction_summary.csv
出力: 20260513/data/features.npz
  X: (N, 1280) float32 — 特徴量
  y: (N,)       str     — ラベル (shoryuken / hadouken / negative)
  paths: (N,)   str     — 画像パス
  splits: (N,)  str     — "train" or "val" (source_file の _1/_2 で分割)
"""

from pathlib import Path

import numpy as np
import pandas as pd
import timm
import torch
from PIL import Image
from torchvision import transforms
from tqdm import tqdm

BASE_DIR    = Path(__file__).resolve().parent.parent
SUMMARY_CSV = BASE_DIR / "data" / "clips" / "extraction_summary.csv"
OUT_NPZ     = BASE_DIR / "data" / "features.npz"

BATCH_SIZE  = 64
IMG_SIZE    = 224


def get_model_and_transform():
    model = timm.create_model("efficientnet_b0", pretrained=True, num_classes=0)
    model.eval()
    tf = transforms.Compose([
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406],
                             std=[0.229, 0.224, 0.225]),
    ])
    return model, tf


def path_to_split(path_str: str) -> str:
    """source_file が _1 サフィックス → train, _2 → val"""
    p = Path(path_str)
    name = p.stem  # e.g. "20260513_jin_akira_1_3.540_+0.25"
    # source_file 部分は "_1_" or "_2_" で判断
    if "_1_" in name:
        return "train"
    if "_2_" in name:
        return "val"
    # negative は source_file がファイル名先頭に入っている
    if name.split("_")[-3].endswith("1") or "_1." in name:
        return "train"
    return "val"


def main():
    df = pd.read_csv(SUMMARY_CSV)
    print(f"Total images: {len(df)}")
    print(df.groupby("label").size().rename("count").to_string())

    model, tf = get_model_and_transform()
    print(f"\nModel: efficientnet_b0 (pretrained, feature dim=1280)")
    print(f"Device: cpu")

    paths  = df["path"].tolist()
    labels = df["label"].tolist()
    splits = [path_to_split(p) for p in paths]

    all_feats = []
    n = len(paths)
    print(f"\nExtracting features from {n} images (batch_size={BATCH_SIZE})...")

    for i in tqdm(range(0, n, BATCH_SIZE), unit="batch"):
        batch_paths = paths[i: i + BATCH_SIZE]
        imgs = []
        for p in batch_paths:
            try:
                img = Image.open(p).convert("RGB")
                imgs.append(tf(img))
            except Exception as e:
                print(f"  WARN: {p} — {e}")
                imgs.append(torch.zeros(3, IMG_SIZE, IMG_SIZE))
        batch_tensor = torch.stack(imgs)
        with torch.no_grad():
            feats = model(batch_tensor)  # (B, 1280)
        all_feats.append(feats.numpy())

    X = np.concatenate(all_feats, axis=0).astype(np.float32)
    y = np.array(labels)
    paths_arr = np.array(paths)
    splits_arr = np.array(splits)

    np.savez_compressed(OUT_NPZ, X=X, y=y, paths=paths_arr, splits=splits_arr)
    print(f"\nSaved: {OUT_NPZ}")
    print(f"  X shape: {X.shape}")
    print(f"  Train: {(splits_arr=='train').sum()}, Val: {(splits_arr=='val').sum()}")
    print(f"\nLabel distribution:")
    for lbl in ["shoryuken", "hadouken", "negative"]:
        n_lbl = (y == lbl).sum()
        n_tr  = ((y == lbl) & (splits_arr == "train")).sum()
        n_va  = ((y == lbl) & (splits_arr == "val")).sum()
        print(f"  {lbl:12s}: {n_lbl:5d} (train={n_tr}, val={n_va})")


if __name__ == "__main__":
    main()
