"""EDA Script 05: char_distance Preference per Player"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import argparse
import numpy as np
import pandas as pd
from pathlib import Path
from scipy import stats

PLAYERS = ["akira", "jin", "keita", "kotaro", "nakamura", "ryo", "yamaguti"]
LABEL   = "username"
MATCH   = "source_file"

BASE_DIR = Path(__file__).resolve().parent.parent
COLORS   = plt.cm.tab10(np.linspace(0, 1, len(PLAYERS)))

DIST_BINS   = [0, 200, 400, 600, 800, np.inf]
DIST_LABELS = ["0-200", "200-400", "400-600", "600-800", "800+"]


def main(data_dir: Path, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)

    # 必要列のみ読み込んでメモリを節約
    USE_COLS = [LABEL, MATCH, "char_distance_px"]
    both = pd.concat([
        pd.read_csv(data_dir / "train.csv", usecols=USE_COLS, low_memory=False),
        pd.read_csv(data_dir / "test.csv",  usecols=USE_COLS, low_memory=False),
    ], ignore_index=True)

    # char_distance_px > 0 のみ使用（0 = キャラ未検出）
    nonzero = both[both["char_distance_px"] > 0].copy()
    print(f"Total rows: {len(both):,}  /  nonzero distance rows: {len(nonzero):,}")

    # ── 1. プレイヤー別統計 ────────────────────────────────────────────────
    stats_records = []
    for player in PLAYERS:
        s = nonzero.loc[nonzero[LABEL] == player, "char_distance_px"]
        stats_records.append({
            "player": player,
            "n":      len(s),
            "mean":   s.mean(),
            "median": s.median(),
            "std":    s.std(),
            "p25":    s.quantile(0.25),
            "p75":    s.quantile(0.75),
        })
    stats_df = pd.DataFrame(stats_records).set_index("player")
    print("\n--- Player Distance Stats ---")
    print(stats_df.round(1).to_string())

    # ── 2. ボックスプロット ────────────────────────────────────────────────
    fig, axes = plt.subplots(1, len(PLAYERS), figsize=(20, 6), sharey=True)
    for ax, (player, color) in zip(axes, zip(PLAYERS, COLORS)):
        data = nonzero.loc[nonzero[LABEL] == player, "char_distance_px"].dropna()
        bp = ax.boxplot(data, patch_artist=True, showfliers=False,
                        medianprops=dict(color="black", linewidth=2))
        bp["boxes"][0].set_facecolor(color)
        bp["boxes"][0].set_alpha(0.7)
        ax.set_title(player, fontsize=11, fontweight="bold")
        ax.set_xticks([])
        ax.set_xlabel("")
        ax.tick_params(axis="y", labelsize=8)

    axes[0].set_ylabel("char_distance_px")
    plt.suptitle("char_distance_px Distribution per Player\n(outliers hidden, 0=未検出 除外済)",
                 fontsize=13)
    plt.tight_layout()
    plt.savefig(out_dir / "05_distance_boxplot.png", dpi=120)
    plt.close()
    print("[05] Saved: 05_distance_boxplot.png")

    # ── 3. ヒストグラム重ね合わせ ──────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(14, 6))
    for player, color in zip(PLAYERS, COLORS):
        data = nonzero.loc[nonzero[LABEL] == player, "char_distance_px"].dropna()
        # ビン集計してパーセンテージへ変換
        counts, _ = np.histogram(data, bins=DIST_BINS)
        pcts = counts / counts.sum() * 100
        ax.plot(range(len(DIST_LABELS)), pcts, marker="o", color=color,
                label=player, linewidth=2, alpha=0.85)

    ax.set_xticks(range(len(DIST_LABELS)))
    ax.set_xticklabels(DIST_LABELS, fontsize=10)
    ax.set_xlabel("char_distance_px range (px)")
    ax.set_ylabel("Frame share (%)")
    ax.set_title("Distance Range Distribution per Player\n(share of nonzero-distance frames)")
    ax.legend(loc="upper right", fontsize=9)
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_dir / "05_distance_hist.png", dpi=120)
    plt.close()
    print("[05] Saved: 05_distance_hist.png")

    # ── 4. η² 計算（ANOVA）──────────────────────────────────────────────
    # 試合単位（source_file × username）でchar_distance_pxの平均を集計
    match_means = (
        nonzero
        .groupby([MATCH, LABEL])["char_distance_px"]
        .mean()
        .reset_index()
        .rename(columns={"char_distance_px": "preferred_dist_mean"})
    )
    print(f"\nMatch-level records: {len(match_means)}")

    groups = [
        match_means.loc[match_means[LABEL] == p, "preferred_dist_mean"].dropna().values
        for p in PLAYERS
    ]
    # グループが存在するもののみ
    groups = [g for g in groups if len(g) > 0]

    f_stat, p_val = stats.f_oneway(*groups)

    # η² = SS_between / SS_total
    all_vals = np.concatenate(groups)
    grand_mean = all_vals.mean()
    ss_total   = np.sum((all_vals - grand_mean) ** 2)
    ss_between = sum(len(g) * (g.mean() - grand_mean) ** 2 for g in groups)
    eta2 = ss_between / ss_total if ss_total > 0 else 0.0

    print(f"ANOVA  F={f_stat:.3f}  p={p_val:.4f}  eta2={eta2:.4f}")

    # ── 5. レポート生成 ────────────────────────────────────────────────────
    # 近距離・遠距離の判定
    sorted_by_mean = stats_df["mean"].sort_values()
    n_group = max(2, len(PLAYERS) // 3)
    close_players = sorted_by_mean.index[:n_group].tolist()
    far_players   = sorted_by_mean.index[-n_group:].tolist()

    recommend = "Yes" if eta2 >= 0.06 else "No"
    if eta2 >= 0.14:
        recommend_reason = (
            f"η²={eta2:.4f} は大きな効果量（≥0.14）を示す。"
            "プレイヤー間の距離偏好に明確な差異があり、識別特徴として高い価値を持つ。"
        )
    elif eta2 >= 0.06:
        recommend_reason = (
            f"η²={eta2:.4f} は中程度の効果量（0.06〜0.14）。"
            "識別に一定の貢献が期待でき、モデルへの追加を推奨する。"
        )
    else:
        recommend_reason = (
            f"η²={eta2:.4f} は小さい効果量（<0.06）。"
            "プレイヤー間の距離偏好の差異は小さく、モデルへの追加効果は限定的と予想される。"
            "他の特徴量との組み合わせで検討するとよい。"
        )

    lines = [
        "# EDA Report 05: char_distance Preference per Player\n\n",
        "## 統計サマリ\n\n",
        "| Player | n | mean | median | std | p25 | p75 |\n",
        "|---|---:|---:|---:|---:|---:|---:|\n",
    ]
    for player in PLAYERS:
        r = stats_df.loc[player]
        lines.append(
            f"| {player} | {int(r['n']):,} | {r['mean']:.1f} | {r['median']:.1f} |"
            f" {r['std']:.1f} | {r['p25']:.1f} | {r['p75']:.1f} |\n"
        )
    lines.append("\n")

    close_mean_str = ", ".join(f"{stats_df.loc[p, 'mean']:.1f}px" for p in close_players)
    far_mean_str   = ", ".join(f"{stats_df.loc[p, 'mean']:.1f}px" for p in far_players)
    overall_mean   = nonzero["char_distance_px"].mean()

    lines += [
        "## 所見\n\n",
        f"- 距離が短い（近距離好き）プレイヤー: {', '.join(close_players)}\n",
        f"  - 平均距離: {close_mean_str}\n",
        f"- 距離が長い（遠距離好き）プレイヤー: {', '.join(far_players)}\n",
        f"  - 平均距離: {far_mean_str}\n",
        "\n",
        "### 補足\n",
        f"- 全体の char_distance_px 平均: {overall_mean:.1f}px\n",
        f"- 分析対象フレーム数: {len(nonzero):,} (nonzero のみ)\n",
        "\n",
        "## 新特徴量の評価\n\n",
        f"- `preferred_dist_mean` (試合単位の平均距離): η²値 = {eta2:.4f}\n",
        f"  - ANOVA F={f_stat:.3f}, p={p_val:.4f}\n",
        f"  - 試合単位サンプル数: {len(match_means)}\n",
        f"- モデルへの追加推奨: **{recommend}** — {recommend_reason}\n",
        "\n",
        "## 生成ファイル\n\n",
        "- `05_distance_boxplot.png`: プレイヤー別ボックスプロット（外れ値非表示）\n",
        "- `05_distance_hist.png`: ビン別フレーム割合の折れ線グラフ（プレイヤー比較）\n",
    ]

    report_path = out_dir / "eda_05_distance_preference.md"
    report_path.write_text("".join(lines), encoding="utf-8")
    print(f"[05] Done. Report: {report_path}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--data-dir", type=Path, default=BASE_DIR / "output")
    p.add_argument("--out-dir",  type=Path, default=BASE_DIR / "docs" / "eda")
    args = p.parse_args()
    main(args.data_dir, args.out_dir)
