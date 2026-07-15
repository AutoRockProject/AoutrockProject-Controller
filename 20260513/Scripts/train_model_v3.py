"""
Phase 4 v3: プレイヤー識別MLモデル（EDA知見 + コマンド特徴量反映）

v2 からの変更点:
  [削除] Arrow系 9 ダミー (使用率 0.000 — 誰も使っていない)
  [削除] DPad方向系 η²<0.01 の 11 ダミー (Center/Up/Down/Left/Right/斜め4方向/RStick/START)
  [削除] shoryuken_flag_mean, shoryuken_flag_std (遠距離誤検知 86%)
  [削除] special_ratio (shoryuken 誤検知を含む)
  [追加] input_density_phase1-4 (試合を4分割したフェーズ別入力密度)
  [追加] hadouken_count, hadouken_rate (command_events.csv — ルールベース検出)
  [追加] shoryuken_count, shoryuken_rate (command_events.csv — ルールベース検出)

特徴量構成 (28列):
  - ボタンダミー変数 (10列): X,Y,B,A,RB,LB,RT,LT,LStick,SELECT の使用有無
  - 特殊技・距離 (4列): hadouken_flag mean+std, char_distance_px mean+std
  - 行動特徴量 (6列): jump_rate, crouch_rate, input_density, diagonal_ratio,
                      attack_entropy, combo_rate
  - フェーズ特徴量 (4列): input_density_phase1-4
  - コマンド特徴量 (4列): hadouken_count, hadouken_rate, shoryuken_count, shoryuken_rate

使用方法:
    python train_model_v3.py
"""

import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, cohen_kappa_score, classification_report
from sklearn.preprocessing import StandardScaler

# ---- パス定義 ----------------------------------------------------------------
BASE_DIR      = Path(__file__).parent.parent
OUTPUT_DIR    = BASE_DIR / "output"
DOCS_DIR      = BASE_DIR / "docs"
TRAIN_CSV     = OUTPUT_DIR / "train.csv"
TEST_CSV      = OUTPUT_DIR / "test.csv"
CMD_EVENTS    = BASE_DIR / "data" / "command_events.csv"

# ---- 列定義 ------------------------------------------------------------------
# v3 で使用するボタン (Arrow系・低η²方向系を除外した 10 列)
BUTTON_COLS = [
    "X", "B", "A", "RB", "LB", "RT", "LT", "LStick", "Y", "SELECT",
]

SPECIAL_COLS   = ["hadouken_flag", "char_distance_px"]  # shoryuken_flag は削除
ATTACK_BTNS    = ["X", "Y", "B", "A", "RB", "LB", "RT", "LT"]
DIRECTION_BTNS = ["Up", "Down", "Left", "Right", "UpRight", "UpLeft", "DownRight", "DownLeft"]
JUMP_BTNS      = ["Up", "UpRight", "UpLeft"]
CROUCH_BTNS    = ["Down", "DownRight", "DownLeft"]

ALL_BUTTON_COLS = [
    "X", "Y", "B", "A", "RB", "LB", "RT", "LT", "RStick", "LStick",
    "SELECT", "START",
    "CenterArrow", "UpArrow", "DownArrow", "LeftArrow", "RightArrow",
    "UpRightArrow", "UpLeftArrow", "DownRightArrow", "DownLeftArrow",
    "Center", "Up", "Down", "Right", "Left",
    "UpRight", "UpLeft", "DownRight", "DownLeft",
]

LABEL_COL = "username"
MATCH_COL = "source_file"
NEED_COLS = ALL_BUTTON_COLS + ["hadouken_flag", "shoryuken_flag", "char_distance_px",
                               LABEL_COL, MATCH_COL, "timestamp_sec"]


def load_command_counts() -> dict:
    """command_events.csv から (source_file, username) 別のコマンド回数を返す。"""
    if not CMD_EVENTS.exists():
        print(f"  [WARN] command_events.csv not found: {CMD_EVENTS}")
        return {}
    df = pd.read_csv(CMD_EVENTS)
    counts = {}
    for (sf, user), grp in df.groupby(["source_file", "username"]):
        counts[(sf, user)] = {
            "shoryuken_count": int((grp["command"] == "shoryuken").sum()),
            "hadouken_count":  int((grp["command"] == "hadouken").sum()),
        }
    return counts


def compute_profiles(path: Path, cmd_counts: dict) -> pd.DataFrame:
    """CSV → 試合×選手単位のプロファイル（28特徴量）"""
    print(f"[INFO] 読み込み中: {path.name}")
    df = pd.read_csv(path, usecols=NEED_COLS, low_memory=False)

    rows = []
    for (match, user), grp in df.groupby([MATCH_COL, LABEL_COL]):
        grp = grp.sort_values("timestamp_sec").reset_index(drop=True)
        duration = grp["timestamp_sec"].iloc[-1] - grp["timestamp_sec"].iloc[0]
        if duration <= 0:
            duration = 1.0

        row = {MATCH_COL: match, LABEL_COL: user}

        # 1. ボタンダミー変数 (10列): 試合中に1回でもそのボタンを押したか
        for btn in BUTTON_COLS:
            row[f"{btn}_used"] = int(grp[btn].max() > 0)

        # 2. 特殊技・距離 (4列): hadouken_flag + char_distance_px の mean/std
        for col in SPECIAL_COLS:
            row[f"{col}_mean"] = grp[col].mean()
            row[f"{col}_std"]  = grp[col].std(ddof=0)

        # 3. 行動特徴量 (6列)
        row["jump_rate"]   = grp[JUMP_BTNS].max(axis=1).sum() / duration
        row["crouch_rate"] = grp[CROUCH_BTNS].max(axis=1).sum() / duration
        row["input_density"] = (grp[ALL_BUTTON_COLS].max(axis=1) > 0).sum() / duration

        diag      = grp[["UpRight", "UpLeft", "DownRight", "DownLeft"]].max(axis=1).sum()
        total_dir = grp[DIRECTION_BTNS].max(axis=1).sum()
        row["diagonal_ratio"] = float(diag / total_dir) if total_dir > 0 else 0.0

        attack_counts = grp[ATTACK_BTNS].sum()
        total_attack  = float(attack_counts.sum())
        if total_attack > 0:
            probs = attack_counts / total_attack
            row["attack_entropy"] = float(-np.sum(probs * np.log2(probs + 1e-10)))
        else:
            row["attack_entropy"] = 0.0

        attack_any  = grp[ATTACK_BTNS].max(axis=1)
        is_press    = (attack_any == 1) & (attack_any.shift(1, fill_value=0) == 0)
        press_times = grp.loc[is_press, "timestamp_sec"].values
        combo_count = int(np.sum(np.diff(press_times) <= 0.150)) if len(press_times) > 1 else 0
        row["combo_rate"] = combo_count / duration

        # 4. フェーズ別入力密度 (4列): 試合を4等分して各区間の入力密度を計算
        n = len(grp)
        for ph in range(4):
            s = ph * n // 4
            e = (ph + 1) * n // 4
            ph_grp = grp.iloc[s:e]
            if len(ph_grp) < 2:
                row[f"input_density_phase{ph+1}"] = row["input_density"]
                continue
            ph_dur = ph_grp["timestamp_sec"].iloc[-1] - ph_grp["timestamp_sec"].iloc[0]
            if ph_dur > 0:
                row[f"input_density_phase{ph+1}"] = (
                    (ph_grp[ALL_BUTTON_COLS].max(axis=1) > 0).sum() / ph_dur
                )
            else:
                row[f"input_density_phase{ph+1}"] = row["input_density"]

        # 5. コマンド特徴量 (4列): command_events.csv から取得
        cmd = cmd_counts.get((match, user), {"shoryuken_count": 0, "hadouken_count": 0})
        row["hadouken_count"]  = cmd["hadouken_count"]
        row["shoryuken_count"] = cmd["shoryuken_count"]
        row["hadouken_rate"]   = cmd["hadouken_count"]  / duration
        row["shoryuken_rate"]  = cmd["shoryuken_count"] / duration

        rows.append(row)

    profiles = pd.DataFrame(rows)
    print(f"  → {len(profiles)} プロファイル ({profiles[LABEL_COL].nunique()} 選手)")
    return profiles


def get_feature_cols(profiles: pd.DataFrame) -> list[str]:
    return [c for c in profiles.columns if c not in (MATCH_COL, LABEL_COL)]


def main() -> None:
    t0 = time.time()

    cmd_counts = load_command_counts()
    print(f"[INFO] command_events: {len(cmd_counts)} (source_file, username) ペア")

    train_profiles = compute_profiles(TRAIN_CSV, cmd_counts)
    test_profiles  = compute_profiles(TEST_CSV,  cmd_counts)
    feat_cols      = get_feature_cols(train_profiles)

    print(f"\n特徴量数: {len(feat_cols)}")
    print(f"  {feat_cols}")

    X_tr  = train_profiles[feat_cols].values
    y_tr  = train_profiles[LABEL_COL].values
    X_te  = test_profiles[feat_cols].values
    y_te  = test_profiles[LABEL_COL].values

    sc    = StandardScaler()
    X_trs = sc.fit_transform(X_tr)
    X_tes = sc.transform(X_te)

    print("\n[INFO] RandomForest 学習中 (v3)...")
    clf = RandomForestClassifier(
        n_estimators=500,
        class_weight="balanced",
        n_jobs=-1,
        random_state=42,
    )
    clf.fit(X_trs, y_tr)

    y_tr_pred = clf.predict(X_trs)
    y_te_pred = clf.predict(X_tes)

    acc_tr   = accuracy_score(y_tr, y_tr_pred)
    acc_te   = accuracy_score(y_te, y_te_pred)
    kappa_te = cohen_kappa_score(y_te, y_te_pred)

    print(f"\n=== v3 結果 ===")
    print(f"TRAIN accuracy : {acc_tr:.1%}")
    print(f"TEST  accuracy : {acc_te:.1%}")
    print(f"TEST  κ        : {kappa_te:.4f}")

    print(f"\n=== v2 との比較 ===")
    print(f"{'指標':<20} {'v2':>10} {'v3':>10} {'差':>10}")
    acc_te_str   = f"{acc_te:.1%}"
    kappa_te_str = f"{kappa_te:.4f}"
    feat_n_str   = str(len(feat_cols))
    print(f"{'TEST accuracy':<20} {'77.8%':>10} {acc_te_str:>10}")
    print(f"{'Cohen kappa':<20} {'0.7293':>10} {kappa_te_str:>10}")
    print(f"{'feature count':<20} {'43':>10} {feat_n_str:>10}")

    print(f"\n=== TEST 詳細レポート ===")
    print(classification_report(y_te, y_te_pred, digits=3))

    print("\n=== 試合別分類結果 (TEST) ===")
    results = sorted(
        zip(test_profiles[MATCH_COL], y_te, y_te_pred),
        key=lambda x: x[1]
    )
    for sf, true, pred in results:
        mark = "OK" if true == pred else "NG"
        print(f"  [{mark}] {true:12s} -> {pred:12s}  ({sf})")

    print(f"\n=== RF 特徴量重要度 (上位 15) ===")
    imp_df = pd.DataFrame({
        "feature":    feat_cols,
        "importance": clf.feature_importances_,
    }).sort_values("importance", ascending=False).reset_index(drop=True)
    print(imp_df.head(15).to_string(index=False))

    # レポート保存
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = DOCS_DIR / "ml_model_report_v3.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# プレイヤー識別MLモデル v3 レポート\n\n")
        f.write("## 変更サマリ\n\n")
        f.write("| | v2 | v3 |\n|---|---|---|\n")
        f.write(f"| TEST accuracy | 77.8% | {acc_te:.1%} |\n")
        f.write(f"| Cohen's κ | 0.7293 | {kappa_te:.4f} |\n")
        f.write(f"| 特徴量数 | 43 | {len(feat_cols)} |\n\n")
        f.write("## 特徴量リスト\n\n")
        for i, c in enumerate(feat_cols, 1):
            f.write(f"{i}. `{c}`\n")
        f.write("\n## TEST 分類レポート\n\n```\n")
        f.write(classification_report(y_te, y_te_pred, digits=3))
        f.write("```\n\n## RF 特徴量重要度\n\n")
        f.write(imp_df.to_string(index=False))
        f.write("\n")
    print(f"\n[INFO] レポート保存: {report_path}")
    print(f"[INFO] 完了: {time.time() - t0:.1f}秒")


if __name__ == "__main__":
    main()
