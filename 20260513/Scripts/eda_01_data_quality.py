"""EDA Script 1: Data Quality & Overview"""
import argparse
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

PLAYERS  = ["akira", "jin", "keita", "kotaro", "nakamura", "ryo", "yamaguti"]
LABEL    = "username"
MATCH    = "source_file"
BASE_DIR = Path(__file__).resolve().parent.parent


def _run_lengths(arr):
    """Return list of consecutive-1 run lengths."""
    lengths, run, prev = [], 0, 0
    for v in arr:
        if v == 1:
            run += 1
        else:
            if prev == 1:
                lengths.append(run)
            run = 0
        prev = v
    if prev == 1:
        lengths.append(run)
    return lengths


def main(data_dir: Path, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)

    train = pd.read_csv(data_dir / "train.csv", low_memory=False)
    test  = pd.read_csv(data_dir / "test.csv",  low_memory=False)
    both  = pd.concat([train, test], ignore_index=True)

    lines = ["# EDA Report 01: Data Quality & Overview\n\n"]

    # ── 1. Basic stats ─────────────────────────────────────────────────────
    lines.append("## 1. Basic Stats\n\n")
    for name, df in [("Train", train), ("Test", test)]:
        lines.append(f"**{name}**\n")
        lines.append(f"- Shape: {df.shape[0]:,} rows × {df.shape[1]} cols\n")
        lines.append(f"- Missing values: {df.isnull().sum().sum()}\n")
        lines.append(f"- Unique players: {df[LABEL].nunique()}\n")
        lines.append(f"- Unique source files: {df[MATCH].nunique()}\n\n")

    # ── 2. Class balance ───────────────────────────────────────────────────
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    for ax, (name, df) in zip(axes, [("Train", train), ("Test", test)]):
        counts = df[LABEL].value_counts().reindex(PLAYERS).fillna(0)
        bars = ax.bar(counts.index, counts.values, color="steelblue")
        ax.set_title(f"{name} — Rows per Player")
        ax.set_xlabel("Player"); ax.set_ylabel("Rows")
        ax.tick_params(axis="x", rotation=30)
        for bar, v in zip(bars, counts.values):
            ax.text(bar.get_x() + bar.get_width() / 2, v + 300,
                    f"{int(v):,}", ha="center", fontsize=8)
    plt.tight_layout()
    plt.savefig(out_dir / "01_class_balance.png", dpi=120)
    plt.close()
    print("[01] Saved: 01_class_balance.png")

    # ── 3. Special flag rates per player ──────────────────────────────────
    lines.append("## 2. Special Flag Rates per Player\n\n")
    lines.append("| Player | hadouken_rate% (tr) | shoryuken_rate% (tr) | hadouken_rate% (te) | shoryuken_rate% (te) |\n")
    lines.append("|---|---|---|---|---|\n")

    tr_h, tr_s, te_h, te_s = [], [], [], []
    for player in PLAYERS:
        gr_tr = train[train[LABEL] == player]
        gr_te = test[test[LABEL] == player]
        h_tr = gr_tr["hadouken_flag"].mean() * 100 if len(gr_tr) else 0.0
        s_tr = gr_tr["shoryuken_flag"].mean() * 100 if len(gr_tr) else 0.0
        h_te = gr_te["hadouken_flag"].mean() * 100 if len(gr_te) else 0.0
        s_te = gr_te["shoryuken_flag"].mean() * 100 if len(gr_te) else 0.0
        lines.append(f"| {player} | {h_tr:.2f} | {s_tr:.2f} | {h_te:.2f} | {s_te:.2f} |\n")
        tr_h.append(h_tr); tr_s.append(s_tr); te_h.append(h_te); te_s.append(s_te)
    lines.append("\n")

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    x = np.arange(len(PLAYERS))
    for ax, tr_vals, te_vals, title in zip(
        axes,
        [tr_h, tr_s], [te_h, te_s],
        ["Hadouken Flag Rate (%)", "Shoryuken Flag Rate (%)"]
    ):
        ax.bar(x - 0.2, tr_vals, 0.4, label="Train", color="steelblue")
        ax.bar(x + 0.2, te_vals, 0.4, label="Test",  color="coral")
        ax.set_xticks(x); ax.set_xticklabels(PLAYERS, rotation=30)
        ax.set_title(title); ax.set_ylabel("Rate (%)"); ax.legend()
        ax.axhline(np.mean(tr_vals + te_vals), color="gray",
                   linestyle="--", linewidth=0.8, label="Overall mean")
    plt.tight_layout()
    plt.savefig(out_dir / "01_special_flag_rates.png", dpi=120)
    plt.close()
    print("[01] Saved: 01_special_flag_rates.png")

    # ── 4. Shoryuken consecutive frame analysis ────────────────────────────
    lines.append("## 3. Shoryuken Flag: Consecutive Frame Analysis\n\n")
    lines.append("（発火フレームが長く続くなら誤検知の可能性が高い）\n\n")
    for split_name, df in [("Train", train), ("Test", test)]:
        df_sorted = df.sort_values([MATCH, LABEL, "timestamp_sec"])
        runs = _run_lengths(df_sorted["shoryuken_flag"].values)
        if runs:
            lines.append(f"**{split_name}**\n")
            lines.append(f"- 発火区間数: {len(runs)}\n")
            lines.append(f"- 平均連続フレーム数: {np.mean(runs):.2f}\n")
            lines.append(f"- 中央値: {np.median(runs):.1f}\n")
            lines.append(f"- 最大連続フレーム数: {max(runs)}\n")
            lines.append(f"- 1フレームのみ区間の割合: {sum(1 for r in runs if r == 1) / len(runs) * 100:.1f}%\n\n")

    # ── 5. Timestamp intervals ─────────────────────────────────────────────
    lines.append("## 4. Timestamp Interval Distribution\n\n")
    diffs = (both.sort_values([MATCH, LABEL, "timestamp_sec"])
                 .groupby([MATCH, LABEL])["timestamp_sec"]
                 .diff().dropna())
    lines.append(f"- 平均間隔: {diffs.mean():.4f}s\n")
    lines.append(f"- 中央値間隔: {diffs.median():.4f}s\n")
    lines.append(f"- 最大間隔（ギャップ）: {diffs.max():.4f}s\n")
    lines.append(f"- 1秒以上のギャップ数: {(diffs > 1.0).sum()}\n\n")

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.hist(diffs[diffs < 0.5], bins=100, color="steelblue", edgecolor="none")
    ax.axvline(diffs.median(), color="red", linestyle="--",
               label=f"Median: {diffs.median():.4f}s")
    ax.set_title("Timestamp Intervals Distribution (< 0.5s)")
    ax.set_xlabel("Interval (sec)"); ax.set_ylabel("Count"); ax.legend()
    plt.tight_layout()
    plt.savefig(out_dir / "01_timestamp_gaps.png", dpi=120)
    plt.close()
    print("[01] Saved: 01_timestamp_gaps.png")

    # ── 6. char_distance_px distribution ──────────────────────────────────
    lines.append("## 5. char_distance_px Distribution\n\n")
    z_tr = (train["char_distance_px"] == 0).mean() * 100
    z_te = (test["char_distance_px"]  == 0).mean() * 100
    lines.append(f"- Train ゼロ値率（未検出フレーム）: {z_tr:.2f}%\n")
    lines.append(f"- Test  ゼロ値率（未検出フレーム）: {z_te:.2f}%\n\n")

    nonzero = both[both["char_distance_px"] > 0]["char_distance_px"]
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.hist(nonzero, bins=100, color="steelblue", edgecolor="none")
    ax.axvline(nonzero.median(), color="red", linestyle="--",
               label=f"Median: {nonzero.median():.0f}px")
    ax.set_title("char_distance_px Distribution (non-zero)")
    ax.set_xlabel("Distance (px)"); ax.set_ylabel("Count"); ax.legend()
    plt.tight_layout()
    plt.savefig(out_dir / "01_distance_distribution.png", dpi=120)
    plt.close()
    print("[01] Saved: 01_distance_distribution.png")

    # ── Write report ───────────────────────────────────────────────────────
    (out_dir / "eda_01_data_quality.md").write_text("".join(lines), encoding="utf-8")
    print("[01] Done. Report: eda_01_data_quality.md")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--data-dir", type=Path, default=BASE_DIR / "output")
    p.add_argument("--out-dir",  type=Path, default=BASE_DIR / "docs" / "eda")
    args = p.parse_args()
    main(args.data_dir, args.out_dir)
