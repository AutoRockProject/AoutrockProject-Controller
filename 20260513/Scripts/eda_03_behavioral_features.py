"""EDA Script 3: Behavioral Feature Distributions"""
import argparse
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats
from pathlib import Path

PLAYERS = ["akira", "jin", "keita", "kotaro", "nakamura", "ryo", "yamaguti"]
LABEL   = "username"
MATCH   = "source_file"

BUTTON_COLS_RAW = [
    "X", "Y", "B", "A", "RB", "LB", "RT", "LT", "RStick", "LStick",
    "SELECT", "START",
    "CenterArrow", "UpArrow", "DownArrow", "LeftArrow", "RightArrow",
    "UpRightArrow", "UpLeftArrow", "DownRightArrow", "DownLeftArrow",
    "Center", "Up", "Down", "Right", "Left",
    "UpRight", "UpLeft", "DownRight", "DownLeft",
]
ATTACK_BTNS    = ["X", "Y", "B", "A", "RB", "LB", "RT", "LT"]
DIRECTION_BTNS = ["Up", "Down", "Left", "Right", "UpRight", "UpLeft", "DownRight", "DownLeft"]
JUMP_BTNS      = ["Up", "UpRight", "UpLeft"]
CROUCH_BTNS    = ["Down", "DownRight", "DownLeft"]

BASE_DIR = Path(__file__).resolve().parent.parent
COLORS   = plt.cm.tab10(np.linspace(0, 1, len(PLAYERS)))


def compute_profiles(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (match, user), grp in df.groupby([MATCH, LABEL]):
        grp = grp.sort_values("timestamp_sec").reset_index(drop=True)
        t0, t1 = grp["timestamp_sec"].iloc[0], grp["timestamp_sec"].iloc[-1]
        duration = max(t1 - t0, 1.0)

        row = {MATCH: match, LABEL: user}
        for btn in BUTTON_COLS_RAW:
            row[f"{btn}_used"] = int(grp[btn].max() > 0)

        row["jump_rate"]   = grp[JUMP_BTNS].max(axis=1).sum() / duration
        row["crouch_rate"] = grp[CROUCH_BTNS].max(axis=1).sum() / duration

        any_btn = (grp[BUTTON_COLS_RAW].max(axis=1) > 0)
        row["input_density"] = any_btn.sum() / duration

        diag     = grp[["UpRight", "UpLeft", "DownRight", "DownLeft"]].max(axis=1).sum()
        total_d  = grp[DIRECTION_BTNS].max(axis=1).sum()
        row["diagonal_ratio"] = float(diag / total_d) if total_d > 0 else 0.0

        atk_cnt   = grp[ATTACK_BTNS].sum()
        total_atk = float(atk_cnt.sum())
        if total_atk > 0:
            probs = atk_cnt / total_atk
            row["attack_entropy"] = float(-np.sum(probs * np.log2(probs + 1e-10)))
        else:
            row["attack_entropy"] = 0.0

        atk_any   = grp[ATTACK_BTNS].max(axis=1)
        is_press  = (atk_any == 1) & (atk_any.shift(1, fill_value=0) == 0)
        ptimes    = grp.loc[is_press, "timestamp_sec"].values
        combo_cnt = int(np.sum(np.diff(ptimes) <= 0.150)) if len(ptimes) > 1 else 0
        row["combo_rate"] = combo_cnt / duration

        sp_frames = grp[["hadouken_flag", "shoryuken_flag"]].max(axis=1).sum()
        row["special_ratio"] = float(sp_frames / total_atk) if total_atk > 0 else 0.0

        rows.append(row)
    return pd.DataFrame(rows)


def eta_sq(groups):
    all_vals   = np.concatenate(groups)
    grand_mean = all_vals.mean()
    ss_total   = np.sum((all_vals - grand_mean) ** 2)
    ss_between = sum(len(g) * (g.mean() - grand_mean) ** 2 for g in groups)
    return float(ss_between / ss_total) if ss_total > 0 else 0.0


def main(data_dir: Path, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)

    train = pd.read_csv(data_dir / "train.csv", low_memory=False)
    test  = pd.read_csv(data_dir / "test.csv",  low_memory=False)
    both  = pd.concat([train, test], ignore_index=True)

    profiles = compute_profiles(both)

    BEHAV_FEATURES = [
        "jump_rate", "crouch_rate", "combo_rate", "input_density",
        "diagonal_ratio", "attack_entropy", "special_ratio",
    ]
    DUMMY_FEATURES = [f"{btn}_used" for btn in BUTTON_COLS_RAW]
    ALL_FEATS = BEHAV_FEATURES + DUMMY_FEATURES

    lines = ["# EDA Report 03: Behavioral Feature Distributions\n\n"]

    # ── 1. ANOVA η² for all features ──────────────────────────────────────
    eta_records = []
    for col in ALL_FEATS:
        groups = [profiles.loc[profiles[LABEL] == p, col].dropna().values
                  for p in PLAYERS if len(profiles[profiles[LABEL] == p]) > 0]
        groups = [g for g in groups if len(g) > 0]
        try:
            f_stat, p_val = stats.f_oneway(*groups)
        except Exception:
            f_stat, p_val = np.nan, np.nan
        eta = eta_sq(groups)
        eta_records.append({"feature": col, "F": f_stat, "p_value": p_val, "eta_sq": eta})

    anova_df = pd.DataFrame(eta_records).sort_values("eta_sq", ascending=False).reset_index(drop=True)

    lines.append("## 1. ANOVA η² Top 20\n\n")
    lines.append("| # | Feature | η² | F | p |\n")
    lines.append("|---|---|---|---|---|\n")
    for _, row in anova_df.head(20).iterrows():
        p_str = f"{row['p_value']:.4f}" if pd.notna(row['p_value']) else "N/A"
        f_str = f"{row['F']:.2f}" if pd.notna(row['F']) else "N/A"
        lines.append(f"| {int(row.name)+1} | {row['feature']} | {row['eta_sq']:.4f} | {f_str} | {p_str} |\n")
    lines.append("\n")

    # Plot η² top 20 bar chart
    top20 = anova_df.head(20)
    fig, ax = plt.subplots(figsize=(12, 6))
    colors = ["#d62728" if v >= 0.14 else "#ff7f0e" if v >= 0.06 else "#2ca02c"
              for v in top20["eta_sq"]]
    ax.barh(top20["feature"][::-1], top20["eta_sq"][::-1], color=colors[::-1])
    ax.axvline(0.14, color="red",    linestyle="--", linewidth=1, label="Large (0.14)")
    ax.axvline(0.06, color="orange", linestyle="--", linewidth=1, label="Medium (0.06)")
    ax.set_title("ANOVA η² — Top 20 Features")
    ax.set_xlabel("η² (effect size)"); ax.legend()
    plt.tight_layout()
    plt.savefig(out_dir / "03_anova_eta_sq.png", dpi=120)
    plt.close()
    print("[03] Saved: 03_anova_eta_sq.png")

    # ── 2. Violin plots — behavioral features ─────────────────────────────
    n_cols = 4
    n_rows = (len(BEHAV_FEATURES) + n_cols - 1) // n_cols
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(16, n_rows * 4))
    axes = axes.flatten()
    for i, feat in enumerate(BEHAV_FEATURES):
        ax = axes[i]
        data_by_player = [profiles.loc[profiles[LABEL] == p, feat].dropna().values
                          for p in PLAYERS]
        parts = ax.violinplot(data_by_player, positions=range(len(PLAYERS)),
                              showmedians=True, showextrema=True)
        for body, color in zip(parts["bodies"], COLORS):
            body.set_facecolor(color); body.set_alpha(0.7)
        ax.set_xticks(range(len(PLAYERS)))
        ax.set_xticklabels(PLAYERS, rotation=30, fontsize=8)
        eta = anova_df.loc[anova_df["feature"] == feat, "eta_sq"].values[0]
        ax.set_title(f"{feat}\n(η²={eta:.3f})", fontsize=9)
        ax.set_ylabel(feat, fontsize=8)
    for j in range(len(BEHAV_FEATURES), len(axes)):
        axes[j].set_visible(False)
    plt.suptitle("Behavioral Features — Distribution per Player", y=1.01)
    plt.tight_layout()
    plt.savefig(out_dir / "03_behavioral_violin.png", dpi=120)
    plt.close()
    print("[03] Saved: 03_behavioral_violin.png")

    # ── 3. Scatter matrix of top 3 behavioral features ────────────────────
    top3 = [f for f in anova_df["feature"] if f in BEHAV_FEATURES][:3]
    fig, axes = plt.subplots(3, 3, figsize=(12, 11))
    for i, feat_y in enumerate(top3):
        for j, feat_x in enumerate(top3):
            ax = axes[i][j]
            if i == j:
                for player, color in zip(PLAYERS, COLORS):
                    vals = profiles.loc[profiles[LABEL] == player, feat_x].values
                    ax.hist(vals, bins=8, color=color, alpha=0.6, label=player)
                ax.set_title(feat_x, fontsize=9)
            else:
                for player, color in zip(PLAYERS, COLORS):
                    sub = profiles[profiles[LABEL] == player]
                    ax.scatter(sub[feat_x], sub[feat_y], color=color,
                               s=50, alpha=0.8, label=player)
                ax.set_xlabel(feat_x, fontsize=8)
                ax.set_ylabel(feat_y, fontsize=8)
    handles = [plt.Line2D([0], [0], marker="o", color="w",
                           markerfacecolor=c, markersize=8, label=p)
               for p, c in zip(PLAYERS, COLORS)]
    fig.legend(handles=handles, loc="lower center", ncol=len(PLAYERS),
               fontsize=8, bbox_to_anchor=(0.5, -0.02))
    plt.suptitle(f"Scatter Matrix: {', '.join(top3)}", y=1.01)
    plt.tight_layout()
    plt.savefig(out_dir / "03_scatter_top3.png", dpi=120, bbox_inches="tight")
    plt.close()
    print("[03] Saved: 03_scatter_top3.png")

    # ── 4. Button dummy η²=0 summary ─────────────────────────────────────
    zero_eta = anova_df[anova_df["eta_sq"] < 0.01][anova_df["feature"].str.endswith("_used")]
    lines.append("## 2. η²<0.01 ダミーボタン（識別不能）\n\n")
    lines.append("| ボタン | η² |\n|---|---|\n")
    for _, row in zero_eta.iterrows():
        lines.append(f"| {row['feature']} | {row['eta_sq']:.4f} |\n")
    lines.append("\n")

    (out_dir / "eda_03_behavioral_features.md").write_text("".join(lines), encoding="utf-8")
    print("[03] Done. Report: eda_03_behavioral_features.md")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--data-dir", type=Path, default=BASE_DIR / "output")
    p.add_argument("--out-dir",  type=Path, default=BASE_DIR / "docs" / "eda")
    args = p.parse_args()
    main(args.data_dir, args.out_dir)
