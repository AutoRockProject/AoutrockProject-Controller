"""
バイナリ分類版: special_move (shoryuken + hadouken) vs negative

3クラス版 (macro F1=0.49) の代替として、
shoryuken / hadouken を一つにまとめて2クラスで再学習する。

入力: 20260513/data/features.npz
出力: コンソール出力のみ（良ければ move_model_binary/ に保存）
"""

import pickle
from pathlib import Path

import numpy as np
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.svm import SVC

BASE_DIR  = Path(__file__).resolve().parent.parent
NPZ_PATH  = BASE_DIR / "data" / "features.npz"
MODEL_DIR = BASE_DIR / "data" / "move_model_binary"


def main():
    print("Loading features...")
    data = np.load(NPZ_PATH, allow_pickle=True)
    X      = data["X"]       # (N, 1280)
    y_str  = data["y"]       # shoryuken / hadouken / negative
    splits = data["splits"]  # train / val

    # ラベルをバイナリに変換
    y_bin = np.where(y_str == "negative", "negative", "special_move")

    print(f"  Total: {len(X)}")
    print(f"  Train: {(splits=='train').sum()}, Val: {(splits=='val').sum()}")

    tr = splits == "train"
    va = splits == "val"
    X_tr, y_tr = X[tr], y_bin[tr]
    X_va, y_va = X[va], y_bin[va]

    print(f"\nTrain label dist: {dict(zip(*np.unique(y_tr, return_counts=True)))}")
    print(f"Val   label dist: {dict(zip(*np.unique(y_va, return_counts=True)))}")

    scaler = StandardScaler()
    X_tr_s = scaler.fit_transform(X_tr)
    X_va_s = scaler.transform(X_va)

    print("\nTraining binary SVM (RBF, class_weight='balanced')...")
    svm = SVC(kernel="rbf", C=10.0, gamma="scale",
              class_weight="balanced", probability=True, random_state=42)
    svm.fit(X_tr_s, y_tr)

    preds = svm.predict(X_va_s)
    macro_f1 = f1_score(y_va, preds, average="macro")

    print(f"\n=== Binary SVM Validation ===")
    print(classification_report(y_va, preds, digits=3))
    print("Confusion Matrix (negative / special_move):")
    print(confusion_matrix(y_va, preds, labels=["negative", "special_move"]))
    print(f"\nMacro F1: {macro_f1:.4f}")

    threshold = 0.65
    if macro_f1 >= threshold:
        print(f"\n[OK] F1 ({macro_f1:.4f}) >= {threshold} -- move_model_binary/ に保存します")
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        le = LabelEncoder()
        le.fit(["negative", "special_move"])
        with open(MODEL_DIR / "classifier.pkl", "wb") as f:
            pickle.dump(svm, f)
        with open(MODEL_DIR / "scaler.pkl", "wb") as f:
            pickle.dump(scaler, f)
        with open(MODEL_DIR / "label_encoder.pkl", "wb") as f:
            pickle.dump(le, f)
        # 確率閾値確認: special_move prob by true label
        proba = svm.predict_proba(X_va_s)
        sm_idx = list(svm.classes_).index("special_move")
        sm_prob_true  = proba[y_va == "special_move", sm_idx].mean()
        sm_prob_false = proba[y_va == "negative",     sm_idx].mean()
        print(f"  special_move確率 (真陽性平均): {sm_prob_true:.3f}")
        print(f"  special_move確率 (偽陽性平均): {sm_prob_false:.3f}")
        print(f"Saved: {MODEL_DIR}")
    else:
        print(f"\n[NG] F1 ({macro_f1:.4f}) < {threshold} -- 保存しません（精度不十分）")
        print("  → train_model_v3.py では command_events.csv のカウント特徴量のみを使用します")


if __name__ == "__main__":
    main()
