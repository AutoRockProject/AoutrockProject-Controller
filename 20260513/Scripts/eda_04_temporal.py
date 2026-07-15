"""EDA Script 4: Temporal Dynamics"""
import argparse
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
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

BASE_DIR = Path(__file__).resolve().parent.parent
COLORS   = plt.cm.tab10(np.linspace(0, 1, len(PLAYERS)))


def assign_phase(grp: pd.DataFrame) -> pd.Series:
    t0, t1 = grp["timestamp_sec"].min(), grp["timestamp_sec"].max()
    duration = max(t1 - t0, 1.0)
    pct = (grp["timestamp_sec"] - t0) / duration
    return pd.cut(pct, bins=[0, 0.25, 0.5, 0.75, 1.0],
                  labels=["0-25%", "25-50%", "50-75%", "75-100%"],
                  include_lowest=True)


def main(data_dir: Path, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)

    both = pd.concat([
        pd.read_csv(data_dir / "train.csv", low_memory=False),
        pd.read_csv(data_dir / "test.csv",  low_memory=False),
    ], ignore_index=True)

    lines = ["# EDA Report 04: Temporal Dynamics\n\n"]

    # ── 1. Match phase input density ──────────────────────────────────────
    both["any_input"] = (both[BUTTON_COLS_RAW].max(axis=1) > 0).astype(int)

    phase_records = []
    for (match, user), grp in both.groupby([MATCH, LABEL]):
        grp = grp.sort_values("timestamp_sec").reset_index(drop=True)
        t0, t1 = grp["timestamp_sec"].iloc[0], grp["timestamp_sec"].iloc[-1]
        duration = max(t1 - t0, 1.0)
        grp["phase"] = assign_phase(grp)
        for phase, pgrp in grp.groupby("phase", observed=True):
            phase_dur = (pgrp["timestamp_sec"].max() - pgrp["timestamp_sec"].min())
            if phase_dur <= 0:
                phase_dur = 1.0
            density = pgrp["any_input"].sum() / phase_dur
            phase_records.append({LABEL: user, MATCH: match, "phase": phase,
                                   "input_density": density})

    phase_df = pd.DataFrame(phase_records)
    phase_order = ["0-25%", "25-50%", "50-75%", "75-100%"]

    fig, axes = plt.subplots(1, len(PLAYERS), figsize=(20, 5), sharey=True)
    for ax, (player, color) in zip(axes, zip(PLAYERS, COLORS)):
        sub = phase_df[phase_df[LABEL] == player]
        means = [sub[sub["phase"] == ph]["input_density"].mean() for ph in phase_order]
        ax.bar(range(len(phase_order)), means, color=color, alpha=0.8)
        ax.set_title(player, fontsize=10)
        ax.set_xticks(range(len(phase_order)))
        ax.set_xticklabels(list(phase_order), rotation=30, fontsize=7)
        ax.set_ylim(0)
    axes[0].set_ylabel("Input Density (inputs/sec)")
    plt.suptitle("Input Density by Match Phase per Player")
    plt.tight_layout()
    plt.savefig(out_dir / "04_match_phases.png", dpi=120)
    plt.close()
    print("[04] Saved: 04_match_phases.png")

    # Phase summary to report
    lines.append("## 1. Input Density by Match Phase\n\n")
    lines.append("| Player | 0-25% | 25-50% | 50-75% | 75-100% |\n")
    lines.append("|---|---|---|---|---|\n")
    for player in PLAYERS:
        sub = phase_df[phase_df[LABEL] == player]
        vals = [f"{sub[sub['phase']==ph]['input_density'].mean():.2f}" for ph in phase_order]
        lines.append(f"| {player} | {' | '.join(vals)} |\n")
    lines.append("\n")

    # ── 2. char_distance vs special flags ─────────────────────────────────
    lines.append("## 2. Special Flags by char_distance_px\n\n")
    lines.append("（shoryuken が遠距離で多発 → 誤検知の疑い）\n\n")

    nonzero = both[both["char_distance_px"] > 0].copy()
    bins = pd.cut(nonzero["char_distance_px"],
                  bins=[0, 100, 200, 300, 400, 600, 1000, 9999],
                  labels=["<100", "100-200", "200-300", "300-400", "400-600", "600-1000", ">1000"])
    hadouken_by_dist  = nonzero.groupby(bins, observed=True)["hadouken_flag"].mean() * 100
    shoryuken_by_dist = nonzero.groupby(bins, observed=True)["shoryuken_flag"].mean() * 100

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    for ax, vals, title, color in zip(
        axes,
        [hadouken_by_dist, shoryuken_by_dist],
        ["Hadouken Rate % by Distance", "Shoryuken Rate % by Distance"],
        ["steelblue", "coral"]
    ):
        ax.bar(range(len(vals)), vals.values, color=color, edgecolor="none")
        ax.set_xticks(range(len(vals)))
        ax.set_xticklabels(vals.index, rotation=30)
        ax.set_title(title); ax.set_ylabel("Rate (%)")
        ax.set_xlabel("char_distance_px range")
    plt.tight_layout()
    plt.savefig(out_dir / "04_distance_vs_special.png", dpi=120)
    plt.close()
    print("[04] Saved: 04_distance_vs_special.png")

    lines.append("| Distance Range | hadouken_rate% | shoryuken_rate% |\n")
    lines.append("|---|---|---|\n")
    for dist_label in hadouken_by_dist.index:
        h = hadouken_by_dist[dist_label]
        s = shoryuken_by_dist[dist_label]
        lines.append(f"| {dist_label} | {h:.2f} | {s:.2f} |\n")
    lines.append("\n")

    # ── 3. Attack button input density over normalized match time ──────────
    lines.append("## 3. Input Density Timeline (Attack Buttons)\n\n")

    bins_time = np.linspace(0, 1, 21)
    labels_time = [f"{b:.2f}" for b in bins_time[:-1]]

    fig, ax = plt.subplots(figsize=(14, 6))
    for player, color in zip(PLAYERS, COLORS):
        records = []
        for (match, user), grp in both[both[LABEL] == player].groupby([MATCH, LABEL]):
            grp = grp.sort_values("timestamp_sec").reset_index(drop=True)
            t0, t1 = grp["timestamp_sec"].iloc[0], grp["timestamp_sec"].iloc[-1]
            duration = max(t1 - t0, 1.0)
            pct = (grp["timestamp_sec"] - t0) / duration
            grp["atk_any"] = grp[ATTACK_BTNS].max(axis=1)
            grp["pct_bin"] = pd.cut(pct, bins=bins_time, labels=labels_time,
                                    include_lowest=True)
            for bin_label, bgrp in grp.groupby("pct_bin", observed=True):
                records.append({"bin": bin_label, "rate": bgrp["atk_any"].mean()})
        if not records:
            continue
        rdf = pd.DataFrame(records)
        means = rdf.groupby("bin")["rate"].mean().reindex(labels_time)
        ax.plot(range(len(means)), means.values, color=color, label=player,
                linewidth=1.5, alpha=0.9)

    tick_pos = list(range(0, 20, 4))
    tick_labels = [f"{bins_time[i]:.0%}" for i in tick_pos]
    ax.set_xticks(tick_pos)
    ax.set_xticklabels(tick_labels, fontsize=9)
    ax.set_title("Attack Button Activation Rate over Normalized Match Time")
    ax.set_xlabel("Match Progress (%)"); ax.set_ylabel("Attack Input Rate")
    ax.legend(loc="upper right", fontsize=9)
    plt.tight_layout()
    plt.savefig(out_dir / "04_input_density_timeline.png", dpi=120)
    plt.close()
    print("[04] Saved: 04_input_density_timeline.png")

    # ── 4. Shoryuken distance summary ─────────────────────────────────────
    s1 = both[both["shoryuken_flag"] == 1]["char_distance_px"]
    lines.append("## 4. Shoryuken Detection Validity\n\n")
    if len(s1) > 0:
        lines.append(f"- shoryuken=1 の char_distance 中央値: {s1.median():.1f}px\n")
        lines.append(f"- 300px 以上での発火率: {(s1 > 300).mean() * 100:.1f}%\n")
        lines.append(f"- 0px（キャラ未検出）での発火率: {(s1 == 0).mean() * 100:.1f}%\n\n")
        if (s1 > 300).mean() > 0.3:
            lines.append("**⚠ 注意: 遠距離（>300px）での shoryuken 発火が 30% 超 → 誤検知の可能性あり**\n\n")
    else:
        lines.append("shoryuken=1 フレームなし\n\n")

    (out_dir / "eda_04_temporal.md").write_text("".join(lines), encoding="utf-8")
    print("[04] Done. Report: eda_04_temporal.md")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--data-dir", type=Path, default=BASE_DIR / "output")
    p.add_argument("--out-dir",  type=Path, default=BASE_DIR / "docs" / "eda")
    args = p.parse_args()
    main(args.data_dir, args.out_dir)
