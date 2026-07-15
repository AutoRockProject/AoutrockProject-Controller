"""
EfficientNet-B0 特徴量を使った技検知分類器の学習。

入力: 20260513/data/features.npz
出力: 20260513/data/move_model/classifier.pkl  (sklearn SVM)
      20260513/data/move_model/label_encoder.pkl
      20260513/data/move_model/eval_report.txt
"""

import pickle
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.svm import SVC

BASE_DIR  = Path(__file__).resolve().parent.parent
NPZ_PATH  = BASE_DIR / "data" / "features.npz"
MODEL_DIR = BASE_DIR / "data" / "move_model"
MODEL_DIR.mkdir(parents=True, exist_ok=True)


def main():
    print("Loading features...")
    data = np.load(NPZ_PATH, allow_pickle=True)
    X       = data["X"]        # (N, 1280) float32
    y_str   = data["y"]        # (N,) str labels
    splits  = data["splits"]   # (N,) "train" / "val"
    paths   = data["paths"]

    print(f"  X: {X.shape}, labels: {np.unique(y_str)}")
    print(f"  Train: {(splits=='train').sum()}, Val: {(splits=='val').sum()}")

    # ラベルエンコード
    le = LabelEncoder()
    le.fit(["hadouken", "negative", "shoryuken"])
    y = le.transform(y_str)

    tr = splits == "train"
    va = splits == "val"
    X_tr, y_tr = X[tr], y[tr]
    X_va, y_va = X[va], y[va]

    # 特徴量のスケーリング
    scaler = StandardScaler()
    X_tr_s = scaler.fit_transform(X_tr)
    X_va_s = scaler.transform(X_va)

    print(f"\nTrain label dist: {np.bincount(y_tr)}")
    print(f"Val   label dist: {np.bincount(y_va)}")

    # ── モデル1: SVM (RBF) ─────────────────────────────────────────────
    print("\n[1/2] Training SVM (RBF, class_weight='balanced')...")
    svm = SVC(kernel="rbf", C=10.0, gamma="scale",
              class_weight="balanced", probability=True, random_state=42)
    svm.fit(X_tr_s, y_tr)

    svm_preds = svm.predict(X_va_s)
    print("\n=== SVM Validation Report ===")
    print(classification_report(y_va, svm_preds,
                                target_names=le.classes_, digits=3))
    cm_svm = confusion_matrix(y_va, svm_preds)
    print("Confusion Matrix (hadouken / negative / shoryuken):")
    print(cm_svm)

    # ── モデル2: Logistic Regression (速度確認用) ────────────────────────
    print("\n[2/2] Training Logistic Regression (baseline)...")
    lr = LogisticRegression(C=1.0, class_weight="balanced",
                            max_iter=500, random_state=42)
    lr.fit(X_tr_s, y_tr)
    lr_preds = lr.predict(X_va_s)
    print("\n=== LR Validation Report ===")
    print(classification_report(y_va, lr_preds,
                                target_names=le.classes_, digits=3))

    # ── 良い方を保存 ──────────────────────────────────────────────────
    from sklearn.metrics import f1_score
    svm_f1 = f1_score(y_va, svm_preds, average="macro")
    lr_f1  = f1_score(y_va, lr_preds,  average="macro")
    print(f"\nSVM macro F1: {svm_f1:.4f}")
    print(f"LR  macro F1: {lr_f1:.4f}")

    best_model  = svm    if svm_f1 >= lr_f1 else lr
    best_name   = "SVM"  if svm_f1 >= lr_f1 else "LR"
    best_preds  = svm_preds if svm_f1 >= lr_f1 else lr_preds
    print(f"\nBest model: {best_name} (macro F1={max(svm_f1, lr_f1):.4f})")

    with open(MODEL_DIR / "classifier.pkl", "wb") as f:
        pickle.dump(best_model, f)
    with open(MODEL_DIR / "scaler.pkl", "wb") as f:
        pickle.dump(scaler, f)
    with open(MODEL_DIR / "label_encoder.pkl", "wb") as f:
        pickle.dump(le, f)

    report_txt = (
        f"Best model: {best_name}\n"
        f"SVM macro F1: {svm_f1:.4f}\n"
        f"LR  macro F1: {lr_f1:.4f}\n\n"
        + classification_report(y_va, best_preds,
                                target_names=le.classes_, digits=3)
        + f"\nConfusion Matrix:\n{confusion_matrix(y_va, best_preds)}\n"
    )
    with open(MODEL_DIR / "eval_report.txt", "w", encoding="utf-8") as f:
        f.write(report_txt)

    print(f"\nSaved: {MODEL_DIR}/classifier.pkl, scaler.pkl, label_encoder.pkl")
    print(f"Saved: {MODEL_DIR}/eval_report.txt")


if __name__ == "__main__":
    main()
