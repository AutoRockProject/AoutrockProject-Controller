"""EDA Script 6: Button Hold Duration per Player"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import argparse
import numpy as np
import pandas as pd
import seaborn as sns
from pathlib import Path
from scipy import stats

PLAYERS = ["akira", "jin", "keita", "kotaro", "nakamura", "ryo", "yamaguti"]
LABEL   = "username"
MATCH   = "source_file"

ATTACK_BTNS = ["X", "Y", "B", "A", "RB", "LB", "RT", "LT"]

BASE_DIR = Path(__file__).resolve().parent.parent


def run_lengths(arr):
    """バイナリ配列から 1 が連続するランの長さリストを返す"""
    lengths = []
    count = 0
    for v in arr:
        if v == 1:
            count += 1
        elif count > 0:
            lengths.append(count)
            count = 0
    if count > 0:
        lengths.append(count)
    return lengths


def main(data_dir: Path, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)

    both = pd.concat([
        pd.read_csv(data_dir / "train.csv", low_memory=False),
        pd.read_csv(data_dir / "test.csv",  low_memory=False),
    ], ignore_index=True)

    # ── 1. ホールド時間の収集 ──────────────────────────────────────────────
    # 各 (source_file, username) グループ単位でボタン別の連続フレーム数を収集
    # group_records: list of dicts {username, source_file, btn, lengths_list}
    group_records = []

    for (match, user), grp in both.groupby([MATCH, LABEL]):
        grp = grp.sort_values("timestamp_sec").reset_index(drop=True)
        row = {LABEL: user, MATCH: match}
        for btn in ATTACK_BTNS:
            arr = grp[btn].fillna(0).values.astype(int)
            rl = run_lengths(arr)
            row[btn] = rl
        group_records.append(row)

    group_df = pd.DataFrame(group_records)

    # ── 2. プレイヤー × ボタン の中央値ホールド時間 ────────────────────────
    # all_records: {player: {btn: [all hold lengths]}}
    player_btn_lengths = {p: {b: [] for b in ATTACK_BTNS} for p in PLAYERS}
    player_all_lengths = {p: [] for p in PLAYERS}  # 全攻撃ボタン合算

    for _, row in group_df.iterrows():
        user = row[LABEL]
        if user not in PLAYERS:
            continue
        for btn in ATTACK_BTNS:
            player_btn_lengths[user][btn].extend(row[btn])
            player_all_lengths[user].extend(row[btn])

    # 中央値マトリクス (PLAYERS × ATTACK_BTNS)
    median_matrix = pd.DataFrame(index=PLAYERS, columns=ATTACK_BTNS, dtype=float)
    for player in PLAYERS:
        for btn in ATTACK_BTNS:
            lens = player_btn_lengths[player][btn]
            median_matrix.loc[player, btn] = float(np.median(lens)) if lens else 0.0

    # 全攻撃ボタン合算中央値
    all_median = {p: float(np.median(player_all_lengths[p])) if player_all_lengths[p] else 0.0
                  for p in PLAYERS}

    # ── 3. ヒートマップ ────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.heatmap(
        median_matrix.astype(float),
        annot=True, fmt=".1f",
        cmap="YlOrRd",
        linewidths=0.5,
        ax=ax,
        cbar_kws={"label": "Median Hold Duration (frames)"}
    )
    ax.set_title("Median Button Hold Duration per Player × Button (frames)")
    ax.set_xlabel("Button")
    ax.set_ylabel("Player")
    plt.tight_layout()
    plt.savefig(out_dir / "06_hold_duration_heatmap.png", dpi=120)
    plt.close()
    print("[06] Saved: 06_hold_duration_heatmap.png")

    # ── 4. バイオリンプロット（全攻撃ボタン合算）─────────────────────────
    violin_data = []
    for player in PLAYERS:
        for v in player_all_lengths[player]:
            violin_data.append({"Player": player, "HoldDuration": v})
    violin_df = pd.DataFrame(violin_data)

    fig, ax = plt.subplots(figsize=(12, 6))
    if len(violin_df) > 0:
        sns.violinplot(
            data=violin_df,
            x="Player", y="HoldDuration",
            order=PLAYERS,
            palette="tab10",
            inner="box",
            cut=0,
            ax=ax
        )
    ax.set_title("Hold Duration Distribution per Player (All Attack Buttons Combined)")
    ax.set_xlabel("Player")
    ax.set_ylabel("Hold Duration (frames)")
    ax.set_ylim(0)
    plt.tight_layout()
    plt.savefig(out_dir / "06_hold_duration_violin.png", dpi=120)
    plt.close()
    print("[06] Saved: 06_hold_duration_violin.png")

    # ── 5. ANOVA η² 計算（試合単位の平均ホールド時間）──────────────────
    # 試合 × username 単位で各ボタンの平均ホールドフレーム数を計算
    anova_rows = []
    for _, row in group_df.iterrows():
        user = row[LABEL]
        if user not in PLAYERS:
            continue
        rec = {LABEL: user, MATCH: row[MATCH]}
        for btn in ATTACK_BTNS:
            lens = row[btn]
            rec[btn] = float(np.mean(lens)) if lens else 0.0
        # all_attack: 全攻撃ボタン合算の全長を使った平均
        all_lens = []
        for btn in ATTACK_BTNS:
            all_lens.extend(row[btn])
        rec["all_attack"] = float(np.mean(all_lens)) if all_lens else 0.0
        anova_rows.append(rec)

    anova_df = pd.DataFrame(anova_rows)

    anova_results = []
    for col in ATTACK_BTNS + ["all_attack"]:
        groups = [anova_df[anova_df[LABEL] == p][col].dropna().values
                  for p in PLAYERS]
        groups = [g for g in groups if len(g) > 0]
        if len(groups) < 2:
            anova_results.append({"btn": col, "eta2": float("nan"),
                                   "F": float("nan"), "p": float("nan")})
            continue
        try:
            f_val, p_val = stats.f_oneway(*groups)
            # η² = SS_between / SS_total
            grand_mean = np.concatenate(groups).mean()
            ss_total = sum(((v - grand_mean) ** 2).sum() for v in groups)
            ss_between = sum(len(g) * (g.mean() - grand_mean) ** 2 for g in groups)
            eta2 = ss_between / ss_total if ss_total > 0 else 0.0
            anova_results.append({"btn": col, "eta2": eta2, "F": f_val, "p": p_val})
        except Exception as e:
            anova_results.append({"btn": col, "eta2": float("nan"),
                                   "F": float("nan"), "p": float("nan")})

    anova_res_df = pd.DataFrame(anova_results)

    # ── 6. レポート生成 ────────────────────────────────────────────────────
    lines = ["# EDA Report 06: Button Hold Duration per Player\n\n"]

    lines.append("## 中央値ホールド時間（フレーム数）\n\n")
    header = "| Player | " + " | ".join(ATTACK_BTNS) + " | 全攻撃合算 |\n"
    lines.append(header)
    lines.append("|---|" + "---|" * (len(ATTACK_BTNS) + 1) + "\n")
    for player in PLAYERS:
        vals = [f"{median_matrix.loc[player, btn]:.1f}" for btn in ATTACK_BTNS]
        all_med = f"{all_median[player]:.1f}"
        lines.append(f"| {player} | {' | '.join(vals)} | {all_med} |\n")
    lines.append("\n")

    lines.append("## ANOVA η²（試合単位の平均ホールド時間）\n\n")
    lines.append("| ボタン | η² | F値 | p値 |\n")
    lines.append("|---|---|---|---|\n")
    for _, row in anova_res_df.iterrows():
        eta2_s = f"{row['eta2']:.4f}" if not np.isnan(row["eta2"]) else "N/A"
        f_s    = f"{row['F']:.3f}"    if not np.isnan(row["F"])    else "N/A"
        p_s    = f"{row['p']:.4f}"    if not np.isnan(row["p"])    else "N/A"
        lines.append(f"| {row['btn']} | {eta2_s} | {f_s} | {p_s} |\n")
    lines.append("\n")

    # 所見の自動生成
    # 長押しスタイル: 全攻撃合算中央値 > 3フレーム
    long_press = [p for p in PLAYERS if all_median[p] > 3.0]
    tap_press  = [p for p in PLAYERS if all_median[p] <= 3.0]

    # 最も discriminative なボタン (η²最大)
    best_row = anova_res_df[anova_res_df["btn"] != "all_attack"].sort_values("eta2", ascending=False).iloc[0]
    best_btn = best_row["btn"]
    best_eta2 = best_row["eta2"]

    # all_attack の η²
    all_atk_row = anova_res_df[anova_res_df["btn"] == "all_attack"].iloc[0]
    all_atk_eta2 = all_atk_row["eta2"]
    all_atk_p    = all_atk_row["p"]

    lines.append("## 所見\n\n")
    lines.append(f"- 長押しスタイルのプレイヤー（中央値 > 3f）: "
                 f"{', '.join(long_press) if long_press else 'なし'}\n")
    lines.append(f"- タッピングスタイルのプレイヤー（中央値 ≤ 3f）: "
                 f"{', '.join(tap_press) if tap_press else 'なし'}\n")
    lines.append(f"- 最も識別力の高いボタン: {best_btn} (η²={best_eta2:.4f})\n")
    lines.append(f"- 全攻撃ボタン合算の η²={all_atk_eta2:.4f}, p={all_atk_p:.4f}\n")
    lines.append("\n")

    lines.append("## 新特徴量の評価\n\n")
    recommend = "Yes" if all_atk_eta2 >= 0.05 else "No"
    reason = (
        f"全攻撃ボタン合算の平均ホールドフレーム数の η²={all_atk_eta2:.4f}（p={all_atk_p:.4f}）。"
    )
    if recommend == "Yes":
        reason += " η² ≥ 0.05 は中程度以上の効果量であり、プレイヤー識別に有効な特徴量と評価できる。"
    else:
        reason += f" η² < 0.05 は小さな効果量であり、識別力は限定的。ただし他特徴量との組み合わせで有用な可能性はある。"

    lines.append(f"- `mean_hold_duration`（全攻撃ボタン合算の平均ホールドフレーム数）の追加推奨: "
                 f"**{recommend}**\n")
    lines.append(f"  - 理由: {reason}\n")

    report_path = out_dir / "eda_06_hold_duration.md"
    report_path.write_text("".join(lines), encoding="utf-8")
    print(f"[06] Done. Report: {report_path}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--data-dir", type=Path, default=BASE_DIR / "output")
    p.add_argument("--out-dir",  type=Path, default=BASE_DIR / "docs" / "eda")
    args = p.parse_args()
    main(args.data_dir, args.out_dir)
