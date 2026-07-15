"""
Phase 4 v2: プレイヤー識別MLモデル（コントローラー設計向け特徴量）

アプローチ:
  ① 一元配置ANOVA + η²（効果量）でプレイヤー間差異を特定
  ② RandomForestClassifierで識別モデルを構築

特徴量構成 (43列):
  - ボタンダミー変数 (30列): 各ボタンの使用有無 0/1
  - 特殊技・距離 (6列): hadouken/shoryuken/char_distance の mean + std
  - 行動特徴量 (7列): jump_rate, crouch_rate, input_density,
                      diagonal_ratio, attack_entropy, combo_rate, special_ratio

使用方法:
    python train_model_v2.py
"""

import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, cohen_kappa_score
from sklearn.preprocessing import StandardScaler

# ---- パス定義 ----------------------------------------------------------------
BASE_DIR   = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "output"
DOCS_DIR   = BASE_DIR / "docs"
TRAIN_CSV  = OUTPUT_DIR / "train.csv"
TEST_CSV   = OUTPUT_DIR / "test.csv"

# ---- 列定義 ------------------------------------------------------------------
BUTTON_COLS_RAW = [
    "X", "Y", "B", "A", "RB", "LB", "RT", "LT", "RStick", "LStick",
    "SELECT", "START",
    "CenterArrow", "UpArrow", "DownArrow", "LeftArrow", "RightArrow",
    "UpRightArrow", "UpLeftArrow", "DownRightArrow", "DownLeftArrow",
    "Center", "Up", "Down", "Right", "Left",
    "UpRight", "UpLeft", "DownRight", "DownLeft",
]
SPECIAL_COLS   = ["hadouken_flag", "shoryuken_flag", "char_distance_px"]
ATTACK_BTNS    = ["X", "Y", "B", "A", "RB", "LB", "RT", "LT"]
DIRECTION_BTNS = ["Up", "Down", "Left", "Right", "UpRight", "UpLeft", "DownRight", "DownLeft"]
JUMP_BTNS      = ["Up", "UpRight", "UpLeft"]
CROUCH_BTNS    = ["Down", "DownRight", "DownLeft"]

LABEL_COL = "username"
MATCH_COL = "source_file"
NEED_COLS = BUTTON_COLS_RAW + SPECIAL_COLS + [LABEL_COL, MATCH_COL, "timestamp_sec"]

# η² 効果量の閾値
ETA_LARGE  = 0.14
ETA_MEDIUM = 0.06
ETA_SMALL  = 0.01


# ---- 特徴量計算 ---------------------------------------------------------------

def compute_profiles(path: Path) -> pd.DataFrame:
    """CSV → 試合×選手単位のプロファイル（43特徴量）"""
    print(f"[INFO] 読み込み中: {path.name}")
    df = pd.read_csv(path, usecols=NEED_COLS, low_memory=False)

    rows = []
    for (match, user), grp in df.groupby([MATCH_COL, LABEL_COL]):
        grp = grp.sort_values("timestamp_sec").reset_index(drop=True)
        duration = grp["timestamp_sec"].iloc[-1] - grp["timestamp_sec"].iloc[0]
        if duration <= 0:
            duration = 1.0

        row = {MATCH_COL: match, LABEL_COL: user}

        # 1. ボタンダミー変数 (30列): 試合中に1回でもそのボタンを押したか
        for btn in BUTTON_COLS_RAW:
            row[f"{btn}_used"] = int(grp[btn].max() > 0)

        # 2. 特殊技・動画特徴量 (6列)
        for col in SPECIAL_COLS:
            row[f"{col}_mean"] = grp[col].mean()
            row[f"{col}_std"]  = grp[col].std(ddof=0)

        # 3. 行動特徴量 (7列)

        # ジャンプ頻度: 上方向入力フレーム / 試合時間(秒)
        row["jump_rate"] = grp[JUMP_BTNS].max(axis=1).sum() / duration

        # しゃがみ頻度: 下方向入力フレーム / 試合時間(秒)
        row["crouch_rate"] = grp[CROUCH_BTNS].max(axis=1).sum() / duration

        # 入力密度: いずれかのボタンが押されているフレーム / 試合時間(秒)
        row["input_density"] = (grp[BUTTON_COLS_RAW].max(axis=1) > 0).sum() / duration

        # 方向入力複雑度: 斜め入力フレーム / 全方向入力フレーム
        diag      = grp[["UpRight", "UpLeft", "DownRight", "DownLeft"]].max(axis=1).sum()
        total_dir = grp[DIRECTION_BTNS].max(axis=1).sum()
        row["diagonal_ratio"] = float(diag / total_dir) if total_dir > 0 else 0.0

        # 攻撃多様性: 攻撃ボタン分布の Shannon エントロピー
        attack_counts = grp[ATTACK_BTNS].sum()
        total_attack  = float(attack_counts.sum())
        if total_attack > 0:
            probs = attack_counts / total_attack
            row["attack_entropy"] = float(-np.sum(probs * np.log2(probs + 1e-10)))
        else:
            row["attack_entropy"] = 0.0

        # コンボ頻度: 150ms以内の連続攻撃入力数 / 試合時間(秒)
        attack_any  = grp[ATTACK_BTNS].max(axis=1)
        is_press    = (attack_any == 1) & (attack_any.shift(1, fill_value=0) == 0)
        press_times = grp.loc[is_press, "timestamp_sec"].values
        combo_count = int(np.sum(np.diff(press_times) <= 0.150)) if len(press_times) > 1 else 0
        row["combo_rate"] = combo_count / duration

        # 特殊技比率: 特殊技フレーム / 攻撃フレーム
        special_frames    = grp[["hadouken_flag", "shoryuken_flag"]].max(axis=1).sum()
        row["special_ratio"] = float(special_frames / total_attack) if total_attack > 0 else 0.0

        rows.append(row)

    profiles = pd.DataFrame(rows)
    print(f"  → {len(profiles)} プロファイル ({profiles[LABEL_COL].nunique()} 選手)")
    return profiles


def get_feature_cols(profiles: pd.DataFrame) -> list[str]:
    return [c for c in profiles.columns if c not in (MATCH_COL, LABEL_COL)]


# ---- ANOVA + η² ---------------------------------------------------------------

def run_anova(profiles: pd.DataFrame, feat_cols: list[str]) -> pd.DataFrame:
    """一元配置ANOVA + η² 効果量を全特徴量に対して実行"""
    players = sorted(profiles[LABEL_COL].unique())
    records = []

    for col in feat_cols:
        groups = [profiles.loc[profiles[LABEL_COL] == p, col].dropna().values for p in players]
        groups = [g for g in groups if len(g) > 0]
        if len(groups) < 2:
            continue

        try:
            f_stat, p_val = stats.f_oneway(*groups)
        except Exception:
            f_stat, p_val = np.nan, np.nan

        all_vals   = np.concatenate(groups)
        grand_mean = all_vals.mean()
        ss_total   = np.sum((all_vals - grand_mean) ** 2)
        ss_between = sum(len(g) * (g.mean() - grand_mean) ** 2 for g in groups)
        eta_sq     = float(ss_between / ss_total) if ss_total > 0 else 0.0

        records.append({
            "feature": col,
            "F":       float(f_stat) if not np.isnan(f_stat) else np.nan,
            "p_value": float(p_val)  if not np.isnan(p_val)  else np.nan,
            "eta_sq":  eta_sq,
        })

    return pd.DataFrame(records).sort_values("eta_sq", ascending=False).reset_index(drop=True)


# ---- レポート生成 ---------------------------------------------------------------

def _eta_label(eta: float) -> str:
    if eta >= ETA_LARGE:
        return "大"
    elif eta >= ETA_MEDIUM:
        return "中"
    elif eta >= ETA_SMALL:
        return "小"
    return "なし"


def _get_design_insight(fname: str) -> str:
    insights = {
        "jump_rate":           "ジャンプ頻度 → 上入力の操作しやすさを個人ごとに調整",
        "crouch_rate":         "しゃがみ頻度 → 下入力の感度を個人ごとに調整",
        "input_density":       "入力密度 → ボタン応答速度・クリック感の設計値に反映",
        "diagonal_ratio":      "斜め入力比率 → レバー/十字キーの斜め精度を調整",
        "attack_entropy":      "攻撃多様性 → 多用するボタンをアクセスしやすい位置に配置",
        "combo_rate":          "連続入力頻度 → 隣接ボタンのレイアウト最適化",
        "special_ratio":       "特殊技比率 → 波動拳/昇竜拳入力のしやすさを優先",
        "hadouken_flag_mean":  "波動拳使用頻度 → 前QC入力の操作性を優先",
        "hadouken_flag_std":   "波動拳使用のばらつき → 操作安定性の指標",
        "shoryuken_flag_mean": "昇竜拳使用頻度 → DP入力の操作性を優先",
        "shoryuken_flag_std":  "昇竜拳使用のばらつき",
        "char_distance_px_mean": "対戦距離 → 遠距離プレイヤーは飛び道具入力を優先設計",
        "char_distance_px_std":  "対戦距離変動 → 押し付け vs 立ち回りスタイルの指標",
    }
    if fname.endswith("_used"):
        btn = fname[:-5]
        return f"{btn}ボタン → 未使用なら省略・配置変更可、使用なら最適位置に配置"
    return insights.get(fname, "—")


def build_report(
    anova_df:      pd.DataFrame,
    rf_imp:        pd.DataFrame,
    acc_tr:        float,
    acc_te:        float,
    kappa_te:      float,
    n_tr:          int,
    n_te:          int,
    n_feat:        int,
    test_profiles: pd.DataFrame,
    feat_cols:     list[str],
    clf:           RandomForestClassifier,
    sc:            StandardScaler,
) -> str:
    lines: list[str] = []
    a = lines.append

    a("# プレイヤー識別MLモデル v2 レポート")
    a("")
    a("> **目的**: 格闘ゲームのコントローラ入力ログからプレイヤーを識別し、")
    a("> **どの指標でプレイヤー間に差が生じるか** を明らかにすることで、")
    a("> 個人対応コントローラ設計に役立てる。")
    a("")
    a("---")
    a("")
    a("## 1. モデル概要（v2 変更点）")
    a("")
    a("| 項目 | v1（旧） | v2（本レポート） |")
    a("|---|---|---|")
    a("| 特徴量数 | 66（ボタン mean+std） | **43**（ダミー+行動+特殊技） |")
    a("| ボタン特徴量 | 各ボタン押下率の mean/std | **ダミー変数**（試合中の使用有無 0/1） |")
    a("| 特殊技 | hadouken/shoryuken mean+std | 同左（継続） |")
    a("| 行動特徴量 | なし | **7種追加** |")
    a("| 分析手法 | RF のみ | **ANOVA + η² + RF（2本立て）** |")
    a("")
    a("### 特徴量構成（合計 43列）")
    a("")
    a("| カテゴリ | 列数 | 内容 |")
    a("|---|---|---|")
    a("| ボタンダミー変数 | 30 | 各ボタンの使用有無（0=未使用, 1=使用） |")
    a("| 特殊技・距離 | 6 | hadouken_flag / shoryuken_flag / char_distance_px の mean+std |")
    a("| 行動特徴量 | 7 | jump_rate, crouch_rate, input_density, diagonal_ratio, attack_entropy, combo_rate, special_ratio |")
    a("")
    a("#### 行動特徴量の定義")
    a("")
    a("| 特徴量 | 定義 | コントローラ設計への示唆 |")
    a("|---|---|---|")
    a("| jump_rate | 上方向入力フレーム数 / 試合時間(秒) | 上入力の使用頻度 → 十字キー上の感度 |")
    a("| crouch_rate | 下方向入力フレーム数 / 試合時間(秒) | 下入力の使用頻度 → 十字キー下の感度 |")
    a("| input_density | 入力フレーム数 / 試合時間(秒) | 操作の密度 → ボタン応答速度・クリック感の設計値 |")
    a("| diagonal_ratio | 斜め入力フレーム / 全方向入力フレーム | 斜め入力依存度 → レバーの斜め精度 |")
    a("| attack_entropy | 攻撃ボタン分布の Shannon エントロピー | 高=多様 / 低=特定ボタン集中 |")
    a("| combo_rate | 150ms以内の連続攻撃入力数 / 試合時間(秒) | 連続入力頻度 → 隣接ボタン配置の重要度 |")
    a("| special_ratio | 特殊技フレーム / 攻撃フレーム | 特殊技依存度 → QC/DP入力のしやすさの優先度 |")
    a("")
    a("---")
    a("")

    # ---- ANOVA ---------------------------------------------------------------
    a("## 2. 分析① 一元配置ANOVA + η² 効果量")
    a("")
    a("> **η²（eta-squared）の解釈**")
    a("> | 区分 | η² | 意味 |")
    a("> |---|---|---|")
    a("> | 大 | ≥ 0.14 | プレイヤー間に明確な差 → コントローラ設計で最優先 |")
    a("> | 中 | ≥ 0.06 | 中程度の差 → 参考として個人対応を検討 |")
    a("> | 小 | ≥ 0.01 | 小さい差 |")
    a("> | なし | < 0.01 | 実質的な差なし |")
    a("")
    a("> **分析データ**: train + test の全36プロファイルを使用（探索的分析のため全データ使用）")
    a("")
    a("### 全特徴量 ANOVA結果（η²降順）")
    a("")
    a("| ランク | 特徴量 | F値 | p値 | η² | 効果量 |")
    a("|---|---|---|---|---|---|")

    for idx, r in anova_df.iterrows():
        rank  = int(idx) + 1
        sig   = " *" if pd.notna(r["p_value"]) and r["p_value"] < 0.05 else ""
        label = _eta_label(r["eta_sq"])
        f_str = f"{r['F']:.2f}"   if pd.notna(r["F"])       else "N/A"
        p_str = f"{r['p_value']:.4f}{sig}" if pd.notna(r["p_value"]) else "N/A"
        a(f"| {rank} | {r['feature']} | {f_str} | {p_str} | {r['eta_sq']:.4f} | {label} |")

    a("")
    a("> \\* p < 0.05")
    a("")

    large_eta  = anova_df[anova_df["eta_sq"] >= ETA_LARGE]
    medium_eta = anova_df[(anova_df["eta_sq"] >= ETA_MEDIUM) & (anova_df["eta_sq"] < ETA_LARGE)]
    small_eta  = anova_df[(anova_df["eta_sq"] >= ETA_SMALL)  & (anova_df["eta_sq"] < ETA_MEDIUM)]
    none_eta   = anova_df[anova_df["eta_sq"] < ETA_SMALL]

    a("### ANOVA 効果量サマリ")
    a("")
    a("| 効果量区分 | 件数 | 特徴量 |")
    a("|---|---|---|")
    a(f"| 大 (η²≥0.14) | {len(large_eta)} | {', '.join(large_eta['feature'].tolist()) or '—'} |")
    a(f"| 中 (0.06≤η²<0.14) | {len(medium_eta)} | {', '.join(medium_eta['feature'].tolist()) or '—'} |")
    a(f"| 小 (0.01≤η²<0.06) | {len(small_eta)} | {', '.join(small_eta['feature'].tolist()) or '—'} |")
    a(f"| なし (η²<0.01) | {len(none_eta)} | — |")
    a("")
    a("---")
    a("")

    # ---- RF 分類精度 ----------------------------------------------------------
    a("## 3. 分析② RandomForest 分類精度")
    a("")
    a("| セット | 正解率 | 正解数 / 総試合数 |")
    a("|---|---|---|")
    a(f"| TRAIN | **{acc_tr:.1%}** | {int(round(acc_tr * n_tr))} / {n_tr} |")
    a(f"| TEST  | **{acc_te:.1%}** | {int(round(acc_te * n_te))} / {n_te} |")
    a("")
    a(f"Cohen's Kappa (TEST): κ = **{kappa_te:.4f}**")
    a("")
    a("### v1 との比較")
    a("")
    a("| 指標 | v1 | v2 | 変化 |")
    a("|---|---|---|---|")
    delta_acc = acc_te - 0.8889
    delta_str = f"{'▲' if delta_acc > 0.001 else '▼' if delta_acc < -0.001 else '='} {abs(delta_acc)*100:.1f}pt"
    a(f"| テスト正解率 | 88.9% | {acc_te:.1%} | {delta_str} |")
    a(f"| Cohen's κ | 0.8631 | {kappa_te:.4f} | — |")
    a(f"| 特徴量数 | 66 | {n_feat} | -{66 - n_feat}列 |")
    a("")
    a("### 試合別分類結果（TEST）")
    a("")
    a("| 真のラベル | 予測ラベル | ファイル | 正誤 |")
    a("|---|---|---|---|")

    X_te_feat = sc.transform(test_profiles[feat_cols].values)
    y_te_pred = clf.predict(X_te_feat)
    for sf, true, pred in sorted(
        zip(test_profiles[MATCH_COL], test_profiles[LABEL_COL], y_te_pred),
        key=lambda x: x[1],
    ):
        mark = "✓" if true == pred else "✗"
        a(f"| {true} | {pred} | {sf} | {mark} |")

    a("")
    a("---")
    a("")

    # ---- RF 特徴量重要度 -------------------------------------------------------
    a("## 4. 分析③ RandomForest 特徴量重要度（全43列）")
    a("")
    a("| ランク | 特徴量 | 重要度 | カテゴリ |")
    a("|---|---|---|---|")

    for idx, r in rf_imp.iterrows():
        rank  = int(idx) + 1
        fname = r["feature"]
        if fname.endswith("_used"):
            cat = "ボタンダミー"
        elif any(s in fname for s in ["hadouken", "shoryuken", "char_distance"]):
            cat = "特殊技・距離"
        else:
            cat = "行動特徴量"
        a(f"| {rank} | {fname} | {r['importance']:.6f} | {cat} |")

    a("")
    a("---")
    a("")

    # ---- 総括 ----------------------------------------------------------------
    a("## 5. 総括: コントローラ設計への示唆")
    a("")
    a("### ANOVA（η²） × RF重要度 統合評価（上位15特徴量）")
    a("")

    merged = anova_df.merge(rf_imp, on="feature", how="inner")
    merged["rf_rank"]   = merged["importance"].rank(ascending=False).astype(int)
    merged["anova_rank"] = merged["eta_sq"].rank(ascending=False).astype(int)
    top15 = merged.sort_values("eta_sq", ascending=False).head(15)

    a("| 特徴量 | η² | 効果量 | RF重要度 | RF順位 | コントローラ設計への示唆 |")
    a("|---|---|---|---|---|---|")
    for _, r in top15.iterrows():
        a(f"| {r['feature']} | {r['eta_sq']:.4f} | {_eta_label(r['eta_sq'])} | {r['importance']:.6f} | {r['rf_rank']} | {_get_design_insight(r['feature'])} |")

    a("")
    a("### コントローラ設計 推奨事項")
    a("")
    a("**効果量「大」（η²≥0.14）の特徴量 — 最優先で個人対応**")
    a("")
    if len(large_eta) > 0:
        for _, r in large_eta.iterrows():
            a(f"- `{r['feature']}` (η²={r['eta_sq']:.3f}): {_get_design_insight(r['feature'])}")
    else:
        a("- 該当なし（データ量不足のため大効果量の特徴量が検出されませんでした）")

    a("")
    a("**効果量「中」（0.06≤η²<0.14）の特徴量 — 参考として個人対応を検討**")
    a("")
    if len(medium_eta) > 0:
        for _, r in medium_eta.iterrows():
            a(f"- `{r['feature']}` (η²={r['eta_sq']:.3f}): {_get_design_insight(r['feature'])}")
    else:
        a("- 該当なし")

    a("")
    a("### 注意事項・今後の改善")
    a("")
    a("| 課題 | 内容 |")
    a("|---|---|")
    a("| サンプル数不足 | n=36プロファイルのため統計的検出力が低い（推奨: 各選手10試合以上） |")
    a("| 偏りあり | nakamura・yamagutは各1試合のみ → η²の推定誤差が大きい |")
    a("| ANOVAの前提 | 正規性・等分散性は未検証（探索的分析として解釈すること） |")

    return "\n".join(lines)


# ---- メインエントリポイント ---------------------------------------------------

def main() -> None:
    t0 = time.time()

    train_profiles = compute_profiles(TRAIN_CSV)
    test_profiles  = compute_profiles(TEST_CSV)
    feat_cols      = get_feature_cols(train_profiles)

    print(f"\n特徴量数: {len(feat_cols)}")

    # ANOVA: train + test の全データで実行（探索的分析のため）
    all_profiles = pd.concat([train_profiles, test_profiles], ignore_index=True)
    print("\n[INFO] ANOVA分析中...")
    anova_df = run_anova(all_profiles, feat_cols)

    # RandomForest
    X_tr  = train_profiles[feat_cols].values
    y_tr  = train_profiles[LABEL_COL].values
    sc    = StandardScaler()
    X_trs = sc.fit_transform(X_tr)

    print("[INFO] RandomForest学習中...")
    clf = RandomForestClassifier(
        n_estimators=500,
        class_weight="balanced",
        n_jobs=-1,
        random_state=42,
    )
    clf.fit(X_trs, y_tr)

    X_te      = sc.transform(test_profiles[feat_cols].values)
    y_te      = test_profiles[LABEL_COL].values
    y_tr_pred = clf.predict(X_trs)
    y_te_pred = clf.predict(X_te)

    acc_tr   = accuracy_score(y_tr, y_tr_pred)
    acc_te   = accuracy_score(y_te, y_te_pred)
    kappa_te = cohen_kappa_score(y_te, y_te_pred)

    print(f"\nTRAIN accuracy : {acc_tr:.1%}")
    print(f"TEST  accuracy : {acc_te:.1%}")
    print(f"TEST  κ        : {kappa_te:.4f}")

    rf_imp = pd.DataFrame({
        "feature":    feat_cols,
        "importance": clf.feature_importances_,
    }).sort_values("importance", ascending=False).reset_index(drop=True)

    report = build_report(
        anova_df      = anova_df,
        rf_imp        = rf_imp,
        acc_tr        = acc_tr,
        acc_te        = acc_te,
        kappa_te      = kappa_te,
        n_tr          = len(X_tr),
        n_te          = len(X_te),
        n_feat        = len(feat_cols),
        test_profiles = test_profiles,
        feat_cols     = feat_cols,
        clf           = clf,
        sc            = sc,
    )

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = DOCS_DIR / "ml_model_report_v2.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"\n[INFO] レポート保存: {report_path}")
    print(f"[INFO] 完了: {time.time() - t0:.1f}秒")


if __name__ == "__main__":
    main()
