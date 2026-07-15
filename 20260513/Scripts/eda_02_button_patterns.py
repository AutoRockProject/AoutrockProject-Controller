"""EDA Script 2: Button Usage Patterns"""
import argparse
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
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
ATTACK_BTNS = ["X", "Y", "B", "A", "RB", "LB", "RT", "LT"]
ARROW_BTNS  = [
    "CenterArrow", "UpArrow", "DownArrow", "LeftArrow", "RightArrow",
    "UpRightArrow", "UpLeftArrow", "DownRightArrow", "DownLeftArrow",
]
DPAD_BTNS = [
    "Center", "Up", "Down", "Right", "Left",
    "UpRight", "UpLeft", "DownRight", "DownLeft",
]

BASE_DIR = Path(__file__).resolve().parent.parent


def main(data_dir: Path, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)

    both = pd.concat([
        pd.read_csv(data_dir / "train.csv", low_memory=False),
        pd.read_csv(data_dir / "test.csv",  low_memory=False),
    ], ignore_index=True)

    lines = ["# EDA Report 02: Button Usage Patterns\n\n"]

    # ── 1. Player × Button press-rate heatmap ─────────────────────────────
    rate_matrix = pd.DataFrame(index=PLAYERS, columns=BUTTON_COLS_RAW, dtype=float)
    for player in PLAYERS:
        grp = both[both[LABEL] == player]
        if len(grp) == 0:
            rate_matrix.loc[player] = 0.0
            continue
        rate_matrix.loc[player] = grp[BUTTON_COLS_RAW].mean().values

    fig, ax = plt.subplots(figsize=(18, 5))
    sns.heatmap(rate_matrix.astype(float), annot=True, fmt=".2f",
                cmap="YlOrRd", ax=ax, linewidths=0.3,
                annot_kws={"size": 6}, vmin=0, vmax=1)
    ax.set_title("Button Press Rate per Player (0=never, 1=always pressed)")
    ax.set_xlabel("Button"); ax.set_ylabel("Player")
    plt.xticks(rotation=45, ha="right", fontsize=8)
    plt.tight_layout()
    plt.savefig(out_dir / "02_button_heatmap.png", dpi=120)
    plt.close()
    print("[02] Saved: 02_button_heatmap.png")

    # ── 2. Attack buttons comparison ──────────────────────────────────────
    atk_rates = rate_matrix[ATTACK_BTNS].astype(float)
    fig, ax = plt.subplots(figsize=(12, 5))
    x = np.arange(len(ATTACK_BTNS))
    width = 0.1
    colors = plt.cm.tab10(np.linspace(0, 1, len(PLAYERS)))
    for i, (player, color) in enumerate(zip(PLAYERS, colors)):
        ax.bar(x + i * width, atk_rates.loc[player], width,
               label=player, color=color)
    ax.set_xticks(x + width * (len(PLAYERS) - 1) / 2)
    ax.set_xticklabels(ATTACK_BTNS)
    ax.set_title("Attack Button Press Rate per Player")
    ax.set_ylabel("Press Rate"); ax.legend(loc="upper right", fontsize=8)
    plt.tight_layout()
    plt.savefig(out_dir / "02_attack_buttons.png", dpi=120)
    plt.close()
    print("[02] Saved: 02_attack_buttons.png")

    # ── 3. Arrow vs DPad comparison ───────────────────────────────────────
    lines.append("## Arrow 系 vs DPad 系 ボタン使用率比較\n\n")
    lines.append("（両者が同じ方向を入力する重複ボタン）\n\n")
    lines.append("| ボタン | Arrow 系 rate | DPad 系 rate | 差 |\n")
    lines.append("|---|---|---|---|\n")

    arrow_map = {
        "Up": ("UpArrow", "Up"),
        "Down": ("DownArrow", "Down"),
        "Left": ("LeftArrow", "Left"),
        "Right": ("RightArrow", "Right"),
        "UpRight": ("UpRightArrow", "UpRight"),
        "UpLeft": ("UpLeftArrow", "UpLeft"),
        "DownRight": ("DownRightArrow", "DownRight"),
        "DownLeft": ("DownLeftArrow", "DownLeft"),
    }
    for direction, (arr_col, dpad_col) in arrow_map.items():
        arr_rate  = both[arr_col].mean()
        dpad_rate = both[dpad_col].mean()
        lines.append(f"| {direction} | {arr_rate:.4f} | {dpad_rate:.4f} | {abs(arr_rate - dpad_rate):.4f} |\n")
    lines.append("\n")

    fig, axes = plt.subplots(2, 4, figsize=(16, 7))
    axes = axes.flatten()
    for idx, (direction, (arr_col, dpad_col)) in enumerate(arrow_map.items()):
        ax = axes[idx]
        arr_rates  = [both[both[LABEL] == p][arr_col].mean() for p in PLAYERS]
        dpad_rates = [both[both[LABEL] == p][dpad_col].mean() for p in PLAYERS]
        x = np.arange(len(PLAYERS))
        ax.bar(x - 0.2, arr_rates,  0.4, label="Arrow", color="steelblue")
        ax.bar(x + 0.2, dpad_rates, 0.4, label="DPad",  color="coral")
        ax.set_title(direction, fontsize=9)
        ax.set_xticks(x); ax.set_xticklabels(PLAYERS, rotation=45, fontsize=7)
        if idx == 0: ax.legend(fontsize=7)
    plt.suptitle("Arrow vs DPad Button Rates per Player", y=1.01)
    plt.tight_layout()
    plt.savefig(out_dir / "02_arrow_vs_dpad.png", dpi=120)
    plt.close()
    print("[02] Saved: 02_arrow_vs_dpad.png")

    # ── 4. Button correlation matrix ──────────────────────────────────────
    corr = both[BUTTON_COLS_RAW].corr()
    fig, ax = plt.subplots(figsize=(16, 14))
    mask = np.triu(np.ones_like(corr, dtype=bool))
    sns.heatmap(corr, mask=mask, cmap="coolwarm", center=0,
                annot=False, linewidths=0.2, ax=ax, vmin=-1, vmax=1)
    ax.set_title("Button Correlation Matrix")
    plt.xticks(rotation=45, ha="right", fontsize=8)
    plt.yticks(fontsize=8)
    plt.tight_layout()
    plt.savefig(out_dir / "02_button_correlation.png", dpi=120)
    plt.close()
    print("[02] Saved: 02_button_correlation.png")

    # ── 5. Buttons with η²≈0 (used by everyone) ───────────────────────────
    lines.append("## η²≈0 ボタン（全員が常用するため識別不能）\n\n")
    zero_eta_candidates = []
    for btn in BUTTON_COLS_RAW:
        rates = [both[both[LABEL] == p][btn].mean() for p in PLAYERS if len(both[both[LABEL] == p]) > 0]
        if rates and (max(rates) - min(rates)) < 0.05:
            zero_eta_candidates.append((btn, np.mean(rates), max(rates) - min(rates)))
    lines.append("| ボタン | 平均使用率 | プレイヤー間差 |\n")
    lines.append("|---|---|---|\n")
    for btn, mean_rate, diff in sorted(zero_eta_candidates, key=lambda x: x[2]):
        lines.append(f"| {btn} | {mean_rate:.4f} | {diff:.4f} |\n")
    lines.append("\n")

    (out_dir / "eda_02_button_patterns.md").write_text("".join(lines), encoding="utf-8")
    print("[02] Done. Report: eda_02_button_patterns.md")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--data-dir", type=Path, default=BASE_DIR / "output")
    p.add_argument("--out-dir",  type=Path, default=BASE_DIR / "docs" / "eda")
    args = p.parse_args()
    main(args.data_dir, args.out_dir)
