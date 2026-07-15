"""
学習済み分類器でコマンドイベントの技を判定する。

入力:
  20260513/data/command_events.csv  — 1415 イベント
  20260513/data/move_model/         — classifier.pkl, scaler.pkl, label_encoder.pkl
  20260513/2026_05_13対戦動画/       — MP4 動画

出力:
  20260513/data/move_predictions.csv
    列: source_file, username, timestamp_sec, command(rule-based),
        pred_label, pred_prob_shoryuken, pred_prob_hadouken,
        pred_prob_negative, verified(0/1)
"""

import pickle
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import timm
import torch
from PIL import Image
from torchvision import transforms
from tqdm import tqdm

BASE_DIR   = Path(__file__).resolve().parent.parent
VIDEO_DIR  = BASE_DIR / "2026_05_13対戦動画"
MODEL_DIR  = BASE_DIR / "data" / "move_model"
EVENTS_CSV = BASE_DIR / "data" / "command_events.csv"
OUT_CSV    = BASE_DIR / "data" / "move_predictions.csv"

# コマンド時刻前後のオフセット（学習と同じ設定）
OFFSETS_SEC  = [-0.5, -0.25, 0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5]
FRAME_W, FRAME_H = 640, 360
IMG_SIZE     = 224


def load_model():
    backbone = timm.create_model("efficientnet_b0", pretrained=False, num_classes=0)
    backbone.eval()

    tf = transforms.Compose([
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406],
                             std=[0.229, 0.224, 0.225]),
    ])

    with open(MODEL_DIR / "classifier.pkl", "rb") as f:
        clf = pickle.load(f)
    with open(MODEL_DIR / "scaler.pkl", "rb") as f:
        scaler = pickle.load(f)
    with open(MODEL_DIR / "label_encoder.pkl", "rb") as f:
        le = pickle.load(f)

    return backbone, tf, clf, scaler, le


def read_frame_cv(cap, t_sec):
    cap.set(cv2.CAP_PROP_POS_MSEC, t_sec * 1000)
    ret, frame = cap.read()
    if not ret or frame is None:
        return None
    frame = cv2.resize(frame, (FRAME_W, FRAME_H))
    return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)


def extract_event_features(row, backbone, tf, vid_dur, cap):
    """1イベント分のフレームから特徴を抽出し平均を返す。"""
    t_cmd = float(row["timestamp_sec"])
    imgs = []
    for offset in OFFSETS_SEC:
        t = t_cmd + offset
        if t < 0 or t > vid_dur:
            continue
        rgb = read_frame_cv(cap, t)
        if rgb is None:
            continue
        img = Image.fromarray(rgb)
        imgs.append(tf(img))

    if not imgs:
        return None

    batch = torch.stack(imgs)
    with torch.no_grad():
        feats = backbone(batch)  # (k, 1280)
    return feats.mean(dim=0).numpy()  # (1280,) — 複数フレームの平均


def main():
    events = pd.read_csv(EVENTS_CSV)
    print(f"Events: {len(events)}")

    print("Loading model...")
    backbone, tf, clf, scaler, le = load_model()
    print(f"  Classifier: {type(clf).__name__}")
    print(f"  Classes: {le.classes_}")

    results = []
    # source_file ごとに動画を開いてまとめて処理（無駄な open を減らす）
    for src, grp in tqdm(events.groupby("source_file"),
                         desc="source files", total=events["source_file"].nunique()):
        mp4 = VIDEO_DIR / f"{src}.mp4"
        if not mp4.exists():
            print(f"  MISSING: {mp4.name}")
            continue

        cap = cv2.VideoCapture(str(mp4))
        vid_dur = cap.get(cv2.CAP_PROP_FRAME_COUNT) / max(cap.get(cv2.CAP_PROP_FPS), 1)

        for _, row in grp.iterrows():
            feat = extract_event_features(row, backbone, tf, vid_dur, cap)
            if feat is None:
                continue
            feat_s = scaler.transform(feat.reshape(1, -1))
            pred_idx  = clf.predict(feat_s)[0]
            pred_prob = clf.predict_proba(feat_s)[0]  # (3,) in class order

            prob_dict = dict(zip(le.classes_, pred_prob))
            pred_label = le.inverse_transform([pred_idx])[0]

            # verified: ルールベースのコマンドと予測が一致するか
            verified = 1 if pred_label == row["command"] else 0

            results.append({
                "source_file":         row["source_file"],
                "username":            row["username"],
                "timestamp_sec":       row["timestamp_sec"],
                "command":             row["command"],
                "direction":           row["direction"],
                "pred_label":          pred_label,
                "pred_prob_shoryuken": prob_dict.get("shoryuken", 0),
                "pred_prob_hadouken":  prob_dict.get("hadouken", 0),
                "pred_prob_negative":  prob_dict.get("negative", 0),
                "verified":            verified,
            })

        cap.release()

    df_out = pd.DataFrame(results)
    df_out.to_csv(OUT_CSV, index=False, encoding="utf-8")

    print(f"\n=== Prediction Summary ===")
    print(f"Total predicted: {len(df_out)}")
    print(df_out.groupby(["command", "pred_label"]).size().unstack(fill_value=0).to_string())

    print(f"\n検証率 (command == pred_label):")
    for cmd in ["shoryuken", "hadouken"]:
        sub = df_out[df_out["command"] == cmd]
        vr  = sub["verified"].mean() * 100
        print(f"  {cmd:12s}: {vr:.1f}%  ({sub['verified'].sum()}/{len(sub)})")

    print(f"\nSaved: {OUT_CSV}")


if __name__ == "__main__":
    main()
