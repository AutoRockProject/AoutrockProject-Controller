"""
Phase 4: プレイヤー識別MLモデルの学習・評価

アプローチ: 試合単位プロファイル照合
  - 各試合×各選手のボタン押下率・統計量を集約
  - RandomForestClassifier で試合プロファイルから選手を識別

使用方法:
    python train_model.py            # 学習 + 評価
    python train_model.py --evaluate # 保存済みモデルで評価のみ
"""

import argparse
import pickle
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.preprocessing import StandardScaler

# ---- パス定義 ----------------------------------------------------------------
BASE_DIR     = Path(__file__).parent.parent
OUTPUT_DIR   = BASE_DIR / "output"
MODELS_DIR   = Path(__file__).parent / "models"
TRAIN_CSV    = OUTPUT_DIR / "train.csv"
TEST_CSV     = OUTPUT_DIR / "test.csv"
MODEL_PATH   = MODELS_DIR / "rf_model.pkl"
SCALER_PATH  = MODELS_DIR / "scaler.pkl"

# ---- 特徴量列 ----------------------------------------------------------------
BUTTON_COLS = [
    "X", "Y", "B", "A", "RB", "LB", "RT", "LT", "RStick", "LStick",
    "SELECT", "START",
    "CenterArrow", "UpArrow", "DownArrow", "LeftArrow", "RightArrow",
    "UpRightArrow", "UpLeftArrow", "DownRightArrow", "DownLeftArrow",
    "Center", "Up", "Down", "Right", "Left",
    "UpRight", "UpLeft", "DownRight", "DownLeft",
    "hadouken_flag", "shoryuken_flag", "char_distance_px",
]
LABEL_COL  = "username"
MATCH_COL  = "source_file"


def load_profiles(path: Path) -> pd.DataFrame:
    """CSV を読み込み試合×選手単位のプロファイルに集約する。"""
    print(f"[INFO] 読み込み中: {path.name}")
    need = BUTTON_COLS + [LABEL_COL, MATCH_COL]
    df = pd.read_csv(path, usecols=need, low_memory=False)

    grp = df.groupby([MATCH_COL, LABEL_COL])
    mean = grp[BUTTON_COLS].mean().add_suffix("_mean")
    std  = grp[BUTTON_COLS].std().fillna(0).add_suffix("_std")
    profiles = pd.concat([mean, std], axis=1).reset_index()
    print(f"  → {len(profiles)} プロファイル ({profiles[LABEL_COL].nunique()} 選手)")
    return profiles


def get_feature_cols(profiles: pd.DataFrame) -> list[str]:
    return [c for c in profiles.columns if c not in (MATCH_COL, LABEL_COL)]


def train(X: np.ndarray, y: np.ndarray) -> RandomForestClassifier:
    print(f"\n[INFO] 学習開始: {len(X)} プロファイル × {X.shape[1]} 特徴量")
    clf = RandomForestClassifier(
        n_estimators=500,
        max_depth=None,
        class_weight="balanced",
        n_jobs=-1,
        random_state=42,
    )
    t0 = time.time()
    clf.fit(X, y)
    print(f"[INFO] 学習完了: {time.time() - t0:.1f}秒")
    return clf


def evaluate(
    clf: RandomForestClassifier,
    sc: StandardScaler,
    profiles: pd.DataFrame,
    split: str,
) -> None:
    feat_cols = get_feature_cols(profiles)
    X = sc.transform(profiles[feat_cols].values)
    y_true = profiles[LABEL_COL].values
    y_pred = clf.predict(X)

    acc = accuracy_score(y_true, y_pred)
    print(f"\n--- {split} 正解率: {acc:.1%} ({int(acc * len(y_true))}/{len(y_true)} 試合) ---")
    print(classification_report(y_true, y_pred, digits=3, zero_division=0))

    print("試合別結果:")
    for sf, true, pred in sorted(
        zip(profiles[MATCH_COL], y_true, y_pred), key=lambda x: x[1]
    ):
        mark = "v" if true == pred else "x"
        print(f"  [{mark}] {true:<12} => {pred:<12}  ({sf})")


def feature_importance(clf: RandomForestClassifier, feat_cols: list[str]) -> None:
    idx = np.argsort(clf.feature_importances_)[::-1][:10]
    print("\n--- 重要度 Top 10 ---")
    for rank, i in enumerate(idx, 1):
        print(f"  {rank:2d}. {feat_cols[i]:<35} {clf.feature_importances_[i]:.4f}")


def save_model(clf: RandomForestClassifier, sc: StandardScaler) -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(clf, f)
    with open(SCALER_PATH, "wb") as f:
        pickle.dump(sc, f)
    print(f"\n[INFO] モデル保存: {MODEL_PATH}")
    print(f"[INFO] スケーラー保存: {SCALER_PATH}")


def load_model() -> tuple[RandomForestClassifier, StandardScaler]:
    with open(MODEL_PATH, "rb") as f:
        clf = pickle.load(f)
    with open(SCALER_PATH, "rb") as f:
        sc = pickle.load(f)
    return clf, sc


# ---- CLI エントリポイント ---------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="プレイヤー識別モデル学習・評価")
    parser.add_argument("--evaluate", action="store_true", help="保存済みモデルで評価のみ")
    args = parser.parse_args()

    train_profiles = load_profiles(TRAIN_CSV)
    test_profiles  = load_profiles(TEST_CSV)
    feat_cols = get_feature_cols(train_profiles)

    if args.evaluate:
        clf, sc = load_model()
        print("[INFO] 保存済みモデルをロード")
    else:
        X_tr = train_profiles[feat_cols].values
        y_tr = train_profiles[LABEL_COL].values
        sc = StandardScaler()
        X_tr_s = sc.fit_transform(X_tr)
        clf = train(X_tr_s, y_tr)
        save_model(clf, sc)

    print("\n" + "=" * 60)
    print("評価レポート")
    print("=" * 60)
    evaluate(clf, sc, train_profiles, "TRAIN")
    evaluate(clf, sc, test_profiles,  "TEST")
    feature_importance(clf, feat_cols)


if __name__ == "__main__":
    main()
