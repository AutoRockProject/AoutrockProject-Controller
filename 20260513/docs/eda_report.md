# EDA 総合レポート

## 概要

本レポートは `eda_run_all.py` により自動生成された EDA 分析の統合版です。

- Script 01: データ品質・概要（欠損値・クラスバランス・特殊フラグ）
- Script 02: ボタン使用パターン（ヒートマップ・相関）
- Script 03: 行動特徴量分布（ANOVA η²・バイオリンプロット）
- Script 04: 時系列ダイナミクス（フェーズ分析・距離 vs 特殊技）

---

# EDA Report 01: Data Quality & Overview

## 1. Basic Stats

**Train**
- Shape: 703,672 rows × 38 cols
- Missing values: 0
- Unique players: 7
- Unique source files: 9

**Test**
- Shape: 589,176 rows × 38 cols
- Missing values: 0
- Unique players: 7
- Unique source files: 9

## 2. Special Flag Rates per Player

| Player | hadouken_rate% (tr) | shoryuken_rate% (tr) | hadouken_rate% (te) | shoryuken_rate% (te) |
|---|---|---|---|---|
| akira | 4.70 | 10.86 | 4.00 | 6.93 |
| jin | 3.32 | 10.53 | 2.94 | 7.67 |
| keita | 0.93 | 8.34 | 1.78 | 10.30 |
| kotaro | 3.82 | 9.66 | 2.68 | 9.79 |
| nakamura | 2.94 | 10.15 | 5.22 | 9.86 |
| ryo | 2.22 | 12.61 | 2.89 | 9.15 |
| yamaguti | 2.91 | 10.12 | 5.19 | 9.85 |

## 3. Shoryuken Flag: Consecutive Frame Analysis

（発火フレームが長く続くなら誤検知の可能性が高い）

**Train**
- 発火区間数: 497
- 平均連続フレーム数: 145.84
- 中央値: 135.0
- 最大連続フレーム数: 892
- 1フレームのみ区間の割合: 4.2%

**Test**
- 発火区間数: 389
- 平均連続フレーム数: 136.57
- 中央値: 116.0
- 最大連続フレーム数: 525
- 1フレームのみ区間の割合: 2.8%

## 4. Timestamp Interval Distribution

- 平均間隔: 0.0025s
- 中央値間隔: 0.0006s
- 最大間隔（ギャップ）: 8.8554s
- 1秒以上のギャップ数: 159

## 5. char_distance_px Distribution

- Train ゼロ値率（未検出フレーム）: 8.95%
- Test  ゼロ値率（未検出フレーム）: 7.65%


---

# EDA Report 02: Button Usage Patterns

## Arrow 系 vs DPad 系 ボタン使用率比較

（両者が同じ方向を入力する重複ボタン）

| ボタン | Arrow 系 rate | DPad 系 rate | 差 |
|---|---|---|---|
| Up | 0.0000 | 0.0582 | 0.0582 |
| Down | 0.0000 | 0.1667 | 0.1667 |
| Left | 0.0000 | 0.2220 | 0.2219 |
| Right | 0.0000 | 0.2793 | 0.2793 |
| UpRight | 0.0000 | 0.0309 | 0.0309 |
| UpLeft | 0.0000 | 0.0323 | 0.0323 |
| DownRight | 0.0000 | 0.0727 | 0.0727 |
| DownLeft | 0.0000 | 0.0460 | 0.0460 |

## η²≈0 ボタン（全員が常用するため識別不能）

| ボタン | 平均使用率 | プレイヤー間差 |
|---|---|---|
| RStick | 0.0000 | 0.0000 |
| START | 0.0000 | 0.0000 |
| UpLeftArrow | 0.0000 | 0.0000 |
| UpRightArrow | 0.0000 | 0.0000 |
| UpArrow | 0.0000 | 0.0000 |
| SELECT | 0.0000 | 0.0000 |
| DownRightArrow | 0.0000 | 0.0000 |
| RightArrow | 0.0000 | 0.0000 |
| DownArrow | 0.0000 | 0.0000 |
| DownLeftArrow | 0.0000 | 0.0000 |
| LeftArrow | 0.0000 | 0.0001 |
| LB | 0.0008 | 0.0033 |
| LStick | 0.0012 | 0.0075 |
| Y | 0.0135 | 0.0254 |
| UpRight | 0.0290 | 0.0307 |
| LT | 0.0060 | 0.0311 |
| RB | 0.0172 | 0.0432 |
| UpLeft | 0.0333 | 0.0471 |
| DownLeft | 0.0438 | 0.0477 |


---

# EDA Report 03: Behavioral Feature Distributions

## 1. ANOVA η² Top 20

| # | Feature | η² | F | p |
|---|---|---|---|---|
| 1 | combo_rate | 0.9199 | 55.48 | 0.0000 |
| 2 | B_used | 0.7545 | 14.86 | 0.0000 |
| 3 | jump_rate | 0.6599 | 9.38 | 0.0000 |
| 4 | crouch_rate | 0.6255 | 8.07 | 0.0000 |
| 5 | RT_used | 0.6250 | 8.06 | 0.0000 |
| 6 | Y_used | 0.5800 | 6.67 | 0.0002 |
| 7 | input_density | 0.5081 | 4.99 | 0.0013 |
| 8 | LT_used | 0.4583 | 4.09 | 0.0043 |
| 9 | special_ratio | 0.4518 | 3.98 | 0.0050 |
| 10 | RB_used | 0.4346 | 3.72 | 0.0073 |
| 11 | X_used | 0.3765 | 2.92 | 0.0237 |
| 12 | diagonal_ratio | 0.3381 | 2.47 | 0.0473 |
| 13 | attack_entropy | 0.3197 | 2.27 | 0.0643 |
| 14 | SELECT_used | 0.3182 | 2.26 | 0.0658 |
| 15 | LeftArrow_used | 0.2941 | 2.01 | 0.0960 |
| 16 | DownArrow_used | 0.2721 | 1.81 | 0.1327 |
| 17 | DownLeftArrow_used | 0.2721 | 1.81 | 0.1327 |
| 18 | DownRightArrow_used | 0.2721 | 1.81 | 0.1327 |
| 19 | LStick_used | 0.2685 | 1.77 | 0.1396 |
| 20 | LB_used | 0.2611 | 1.71 | 0.1548 |

## 2. η²<0.01 ダミーボタン（識別不能）

| ボタン | η² |
|---|---|
| RStick_used | 0.0000 |
| START_used | 0.0000 |
| Center_used | 0.0000 |
| Up_used | 0.0000 |
| Down_used | 0.0000 |
| Right_used | 0.0000 |
| Left_used | 0.0000 |
| UpRight_used | 0.0000 |
| UpLeft_used | 0.0000 |
| DownRight_used | 0.0000 |
| DownLeft_used | 0.0000 |


---

# EDA Report 04: Temporal Dynamics

## 1. Input Density by Match Phase

| Player | 0-25% | 25-50% | 50-75% | 75-100% |
|---|---|---|---|---|
| akira | 402.04 | 306.50 | 412.12 | 385.14 |
| jin | 360.33 | 383.00 | 388.74 | 438.27 |
| keita | 388.02 | 409.05 | 341.08 | 525.76 |
| kotaro | 338.28 | 444.16 | 327.72 | 439.94 |
| nakamura | 510.66 | 560.85 | 469.77 | 371.99 |
| ryo | 417.27 | 383.89 | 329.40 | 447.68 |
| yamaguti | 643.08 | 564.51 | 444.89 | 412.03 |

## 2. Special Flags by char_distance_px

（shoryuken が遠距離で多発 → 誤検知の疑い）

| Distance Range | hadouken_rate% | shoryuken_rate% |
|---|---|---|
| <100 | 0.00 | 0.00 |
| 100-200 | 5.37 | 44.17 |
| 200-300 | 12.73 | 21.30 |
| 300-400 | 3.64 | 11.64 |
| 400-600 | 2.99 | 9.58 |
| 600-1000 | 2.39 | 9.62 |
| >1000 | 0.70 | 3.08 |

## 3. Input Density Timeline (Attack Buttons)

## 4. Shoryuken Detection Validity

- shoryuken=1 の char_distance 中央値: 504.8px
- 300px 以上での発火率: 86.0%
- 0px（キャラ未検出）での発火率: 0.0%

**⚠ 注意: 遠距離（>300px）での shoryuken 発火が 30% 超 → 誤検知の可能性あり**


---

## 生成画像一覧 (14 枚)

- `01_class_balance.png`
- `01_distance_distribution.png`
- `01_special_flag_rates.png`
- `01_timestamp_gaps.png`
- `02_arrow_vs_dpad.png`
- `02_attack_buttons.png`
- `02_button_correlation.png`
- `02_button_heatmap.png`
- `03_anova_eta_sq.png`
- `03_behavioral_violin.png`
- `03_scatter_top3.png`
- `04_distance_vs_special.png`
- `04_input_density_timeline.png`
- `04_match_phases.png`

