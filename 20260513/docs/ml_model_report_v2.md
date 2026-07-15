# プレイヤー識別MLモデル v2 レポート

> **目的**: 格闘ゲームのコントローラ入力ログからプレイヤーを識別し、
> **どの指標でプレイヤー間に差が生じるか** を明らかにすることで、
> 個人対応コントローラ設計に役立てる。

---

## 1. モデル概要（v2 変更点）

| 項目 | v1（旧） | v2（本レポート） |
|---|---|---|
| 特徴量数 | 66（ボタン mean+std） | **43**（ダミー+行動+特殊技） |
| ボタン特徴量 | 各ボタン押下率の mean/std | **ダミー変数**（試合中の使用有無 0/1） |
| 特殊技 | hadouken/shoryuken mean+std | 同左（継続） |
| 行動特徴量 | なし | **7種追加** |
| 分析手法 | RF のみ | **ANOVA + η² + RF（2本立て）** |

### 特徴量構成（合計 43列）

| カテゴリ | 列数 | 内容 |
|---|---|---|
| ボタンダミー変数 | 30 | 各ボタンの使用有無（0=未使用, 1=使用） |
| 特殊技・距離 | 6 | hadouken_flag / shoryuken_flag / char_distance_px の mean+std |
| 行動特徴量 | 7 | jump_rate, crouch_rate, input_density, diagonal_ratio, attack_entropy, combo_rate, special_ratio |

#### 行動特徴量の定義

| 特徴量 | 定義 | コントローラ設計への示唆 |
|---|---|---|
| jump_rate | 上方向入力フレーム数 / 試合時間(秒) | 上入力の使用頻度 → 十字キー上の感度 |
| crouch_rate | 下方向入力フレーム数 / 試合時間(秒) | 下入力の使用頻度 → 十字キー下の感度 |
| input_density | 入力フレーム数 / 試合時間(秒) | 操作の密度 → ボタン応答速度・クリック感の設計値 |
| diagonal_ratio | 斜め入力フレーム / 全方向入力フレーム | 斜め入力依存度 → レバーの斜め精度 |
| attack_entropy | 攻撃ボタン分布の Shannon エントロピー | 高=多様 / 低=特定ボタン集中 |
| combo_rate | 150ms以内の連続攻撃入力数 / 試合時間(秒) | 連続入力頻度 → 隣接ボタン配置の重要度 |
| special_ratio | 特殊技フレーム / 攻撃フレーム | 特殊技依存度 → QC/DP入力のしやすさの優先度 |

---

## 2. 分析① 一元配置ANOVA + η² 効果量

> **η²（eta-squared）の解釈**
> | 区分 | η² | 意味 |
> |---|---|---|
> | 大 | ≥ 0.14 | プレイヤー間に明確な差 → コントローラ設計で最優先 |
> | 中 | ≥ 0.06 | 中程度の差 → 参考として個人対応を検討 |
> | 小 | ≥ 0.01 | 小さい差 |
> | なし | < 0.01 | 実質的な差なし |

> **分析データ**: train + test の全36プロファイルを使用（探索的分析のため全データ使用）

### 全特徴量 ANOVA結果（η²降順）

| ランク | 特徴量 | F値 | p値 | η² | 効果量 |
|---|---|---|---|---|---|
| 1 | combo_rate | 55.48 | 0.0000 * | 0.9199 | 大 |
| 2 | B_used | 14.86 | 0.0000 * | 0.7545 | 大 |
| 3 | jump_rate | 9.38 | 0.0000 * | 0.6599 | 大 |
| 4 | crouch_rate | 8.07 | 0.0000 * | 0.6255 | 大 |
| 5 | RT_used | 8.06 | 0.0000 * | 0.6250 | 大 |
| 6 | Y_used | 6.67 | 0.0002 * | 0.5800 | 大 |
| 7 | input_density | 4.99 | 0.0013 * | 0.5081 | 大 |
| 8 | LT_used | 4.09 | 0.0043 * | 0.4583 | 大 |
| 9 | special_ratio | 3.98 | 0.0050 * | 0.4518 | 大 |
| 10 | RB_used | 3.72 | 0.0073 * | 0.4346 | 大 |
| 11 | X_used | 2.92 | 0.0237 * | 0.3765 | 大 |
| 12 | hadouken_flag_std | 2.81 | 0.0280 * | 0.3676 | 大 |
| 13 | hadouken_flag_mean | 2.79 | 0.0289 * | 0.3660 | 大 |
| 14 | diagonal_ratio | 2.47 | 0.0473 * | 0.3381 | 大 |
| 15 | attack_entropy | 2.27 | 0.0643 | 0.3197 | 大 |
| 16 | SELECT_used | 2.26 | 0.0658 | 0.3182 | 大 |
| 17 | LeftArrow_used | 2.01 | 0.0960 | 0.2941 | 大 |
| 18 | DownLeftArrow_used | 1.81 | 0.1327 | 0.2721 | 大 |
| 19 | DownArrow_used | 1.81 | 0.1327 | 0.2721 | 大 |
| 20 | DownRightArrow_used | 1.81 | 0.1327 | 0.2721 | 大 |
| 21 | LStick_used | 1.77 | 0.1396 | 0.2685 | 大 |
| 22 | LB_used | 1.71 | 0.1548 | 0.2611 | 大 |
| 23 | char_distance_px_mean | 1.63 | 0.1735 | 0.2527 | 大 |
| 24 | char_distance_px_std | 1.61 | 0.1810 | 0.2495 | 大 |
| 25 | RightArrow_used | 1.51 | 0.2093 | 0.2383 | 大 |
| 26 | CenterArrow_used | 1.51 | 0.2093 | 0.2383 | 大 |
| 27 | A_used | 0.82 | 0.5660 | 0.1445 | 大 |
| 28 | UpRightArrow_used | 0.81 | 0.5739 | 0.1429 | 大 |
| 29 | UpLeftArrow_used | 0.54 | 0.7756 | 0.1000 | 中 |
| 30 | UpArrow_used | 0.51 | 0.7951 | 0.0956 | 中 |
| 31 | shoryuken_flag_std | 0.47 | 0.8223 | 0.0892 | 中 |
| 32 | shoryuken_flag_mean | 0.41 | 0.8662 | 0.0782 | 中 |
| 33 | RStick_used | N/A | N/A | 0.0000 | なし |
| 34 | START_used | N/A | N/A | 0.0000 | なし |
| 35 | Center_used | N/A | N/A | 0.0000 | なし |
| 36 | UpRight_used | N/A | N/A | 0.0000 | なし |
| 37 | Left_used | N/A | N/A | 0.0000 | なし |
| 38 | Right_used | N/A | N/A | 0.0000 | なし |
| 39 | Down_used | N/A | N/A | 0.0000 | なし |
| 40 | Up_used | N/A | N/A | 0.0000 | なし |
| 41 | DownRight_used | N/A | N/A | 0.0000 | なし |
| 42 | DownLeft_used | N/A | N/A | 0.0000 | なし |
| 43 | UpLeft_used | N/A | N/A | 0.0000 | なし |

> \* p < 0.05

### ANOVA 効果量サマリ

| 効果量区分 | 件数 | 特徴量 |
|---|---|---|
| 大 (η²≥0.14) | 28 | combo_rate, B_used, jump_rate, crouch_rate, RT_used, Y_used, input_density, LT_used, special_ratio, RB_used, X_used, hadouken_flag_std, hadouken_flag_mean, diagonal_ratio, attack_entropy, SELECT_used, LeftArrow_used, DownLeftArrow_used, DownArrow_used, DownRightArrow_used, LStick_used, LB_used, char_distance_px_mean, char_distance_px_std, RightArrow_used, CenterArrow_used, A_used, UpRightArrow_used |
| 中 (0.06≤η²<0.14) | 4 | UpLeftArrow_used, UpArrow_used, shoryuken_flag_std, shoryuken_flag_mean |
| 小 (0.01≤η²<0.06) | 0 | — |
| なし (η²<0.01) | 11 | — |

---

## 3. 分析② RandomForest 分類精度

| セット | 正解率 | 正解数 / 総試合数 |
|---|---|---|
| TRAIN | **100.0%** | 18 / 18 |
| TEST  | **77.8%** | 14 / 18 |

Cohen's Kappa (TEST): κ = **0.7293**

### v1 との比較

| 指標 | v1 | v2 | 変化 |
|---|---|---|---|
| テスト正解率 | 88.9% | 77.8% | ▼ 11.1pt |
| Cohen's κ | 0.8631 | 0.7293 | — |
| 特徴量数 | 66 | 43 | -23列 |

### 試合別分類結果（TEST）

| 真のラベル | 予測ラベル | ファイル | 正誤 |
|---|---|---|---|
| akira | akira | 20260513_jin_akira_2 | ✓ |
| akira | akira | 20260513_kotaro_akira_2 | ✓ |
| jin | kotaro | 20260513_jin_akira_2 | ✗ |
| jin | jin | 20260513_jin_ryo_2 | ✓ |
| jin | jin | 20260513_keita_jin_2 | ✓ |
| jin | jin | 20260513_kotaro_jin_2 | ✓ |
| keita | keita | 20260513_keita_jin_2 | ✓ |
| keita | keita | 20260513_keita_kotaro_2 | ✓ |
| keita | keita | 20260513_keita_ryo_2 | ✓ |
| kotaro | kotaro | 20260513_keita_kotaro_2 | ✓ |
| kotaro | kotaro | 20260513_kotaro_akira_2 | ✓ |
| kotaro | kotaro | 20260513_kotaro_jin_2 | ✓ |
| kotaro | kotaro | 20260513_kotaro_ryo_2 | ✓ |
| nakamura | jin | 20260513_nakamura_yamaguti_2 | ✗ |
| ryo | akira | 20260513_jin_ryo_2 | ✗ |
| ryo | ryo | 20260513_keita_ryo_2 | ✓ |
| ryo | keita | 20260513_kotaro_ryo_2 | ✗ |
| yamaguti | yamaguti | 20260513_nakamura_yamaguti_2 | ✓ |

---

## 4. 分析③ RandomForest 特徴量重要度（全43列）

| ランク | 特徴量 | 重要度 | カテゴリ |
|---|---|---|---|
| 1 | crouch_rate | 0.095543 | 行動特徴量 |
| 2 | jump_rate | 0.087747 | 行動特徴量 |
| 3 | combo_rate | 0.080229 | 行動特徴量 |
| 4 | input_density | 0.066685 | 行動特徴量 |
| 5 | special_ratio | 0.061386 | 行動特徴量 |
| 6 | diagonal_ratio | 0.059855 | 行動特徴量 |
| 7 | hadouken_flag_mean | 0.055556 | 特殊技・距離 |
| 8 | char_distance_px_mean | 0.048927 | 特殊技・距離 |
| 9 | hadouken_flag_std | 0.047587 | 特殊技・距離 |
| 10 | attack_entropy | 0.046261 | 行動特徴量 |
| 11 | char_distance_px_std | 0.044807 | 特殊技・距離 |
| 12 | shoryuken_flag_std | 0.036824 | 特殊技・距離 |
| 13 | shoryuken_flag_mean | 0.031597 | 特殊技・距離 |
| 14 | B_used | 0.027570 | ボタンダミー |
| 15 | LT_used | 0.022774 | ボタンダミー |
| 16 | LB_used | 0.022436 | ボタンダミー |
| 17 | DownArrow_used | 0.019107 | ボタンダミー |
| 18 | RB_used | 0.018463 | ボタンダミー |
| 19 | LStick_used | 0.017756 | ボタンダミー |
| 20 | CenterArrow_used | 0.016447 | ボタンダミー |
| 21 | DownRightArrow_used | 0.015970 | ボタンダミー |
| 22 | RT_used | 0.015729 | ボタンダミー |
| 23 | Y_used | 0.014422 | ボタンダミー |
| 24 | DownLeftArrow_used | 0.013439 | ボタンダミー |
| 25 | LeftArrow_used | 0.012250 | ボタンダミー |
| 26 | RightArrow_used | 0.010812 | ボタンダミー |
| 27 | X_used | 0.009818 | ボタンダミー |
| 28 | SELECT_used | 0.000000 | ボタンダミー |
| 29 | RStick_used | 0.000000 | ボタンダミー |
| 30 | A_used | 0.000000 | ボタンダミー |
| 31 | Left_used | 0.000000 | ボタンダミー |
| 32 | UpRight_used | 0.000000 | ボタンダミー |
| 33 | Center_used | 0.000000 | ボタンダミー |
| 34 | UpRightArrow_used | 0.000000 | ボタンダミー |
| 35 | UpLeftArrow_used | 0.000000 | ボタンダミー |
| 36 | START_used | 0.000000 | ボタンダミー |
| 37 | UpArrow_used | 0.000000 | ボタンダミー |
| 38 | Right_used | 0.000000 | ボタンダミー |
| 39 | Down_used | 0.000000 | ボタンダミー |
| 40 | Up_used | 0.000000 | ボタンダミー |
| 41 | DownRight_used | 0.000000 | ボタンダミー |
| 42 | DownLeft_used | 0.000000 | ボタンダミー |
| 43 | UpLeft_used | 0.000000 | ボタンダミー |

---

## 5. 総括: コントローラ設計への示唆

### ANOVA（η²） × RF重要度 統合評価（上位15特徴量）

| 特徴量 | η² | 効果量 | RF重要度 | RF順位 | コントローラ設計への示唆 |
|---|---|---|---|---|---|
| combo_rate | 0.9199 | 大 | 0.080229 | 3 | 連続入力頻度 → 隣接ボタンのレイアウト最適化 |
| B_used | 0.7545 | 大 | 0.027570 | 14 | Bボタン → 未使用なら省略・配置変更可、使用なら最適位置に配置 |
| jump_rate | 0.6599 | 大 | 0.087747 | 2 | ジャンプ頻度 → 上入力の操作しやすさを個人ごとに調整 |
| crouch_rate | 0.6255 | 大 | 0.095543 | 1 | しゃがみ頻度 → 下入力の感度を個人ごとに調整 |
| RT_used | 0.6250 | 大 | 0.015729 | 22 | RTボタン → 未使用なら省略・配置変更可、使用なら最適位置に配置 |
| Y_used | 0.5800 | 大 | 0.014422 | 23 | Yボタン → 未使用なら省略・配置変更可、使用なら最適位置に配置 |
| input_density | 0.5081 | 大 | 0.066685 | 4 | 入力密度 → ボタン応答速度・クリック感の設計値に反映 |
| LT_used | 0.4583 | 大 | 0.022774 | 15 | LTボタン → 未使用なら省略・配置変更可、使用なら最適位置に配置 |
| special_ratio | 0.4518 | 大 | 0.061386 | 5 | 特殊技比率 → 波動拳/昇竜拳入力のしやすさを優先 |
| RB_used | 0.4346 | 大 | 0.018463 | 18 | RBボタン → 未使用なら省略・配置変更可、使用なら最適位置に配置 |
| X_used | 0.3765 | 大 | 0.009818 | 27 | Xボタン → 未使用なら省略・配置変更可、使用なら最適位置に配置 |
| hadouken_flag_std | 0.3676 | 大 | 0.047587 | 9 | 波動拳使用のばらつき → 操作安定性の指標 |
| hadouken_flag_mean | 0.3660 | 大 | 0.055556 | 7 | 波動拳使用頻度 → 前QC入力の操作性を優先 |
| diagonal_ratio | 0.3381 | 大 | 0.059855 | 6 | 斜め入力比率 → レバー/十字キーの斜め精度を調整 |
| attack_entropy | 0.3197 | 大 | 0.046261 | 10 | 攻撃多様性 → 多用するボタンをアクセスしやすい位置に配置 |

### コントローラ設計 推奨事項

**効果量「大」（η²≥0.14）の特徴量 — 最優先で個人対応**

- `combo_rate` (η²=0.920): 連続入力頻度 → 隣接ボタンのレイアウト最適化
- `B_used` (η²=0.755): Bボタン → 未使用なら省略・配置変更可、使用なら最適位置に配置
- `jump_rate` (η²=0.660): ジャンプ頻度 → 上入力の操作しやすさを個人ごとに調整
- `crouch_rate` (η²=0.625): しゃがみ頻度 → 下入力の感度を個人ごとに調整
- `RT_used` (η²=0.625): RTボタン → 未使用なら省略・配置変更可、使用なら最適位置に配置
- `Y_used` (η²=0.580): Yボタン → 未使用なら省略・配置変更可、使用なら最適位置に配置
- `input_density` (η²=0.508): 入力密度 → ボタン応答速度・クリック感の設計値に反映
- `LT_used` (η²=0.458): LTボタン → 未使用なら省略・配置変更可、使用なら最適位置に配置
- `special_ratio` (η²=0.452): 特殊技比率 → 波動拳/昇竜拳入力のしやすさを優先
- `RB_used` (η²=0.435): RBボタン → 未使用なら省略・配置変更可、使用なら最適位置に配置
- `X_used` (η²=0.377): Xボタン → 未使用なら省略・配置変更可、使用なら最適位置に配置
- `hadouken_flag_std` (η²=0.368): 波動拳使用のばらつき → 操作安定性の指標
- `hadouken_flag_mean` (η²=0.366): 波動拳使用頻度 → 前QC入力の操作性を優先
- `diagonal_ratio` (η²=0.338): 斜め入力比率 → レバー/十字キーの斜め精度を調整
- `attack_entropy` (η²=0.320): 攻撃多様性 → 多用するボタンをアクセスしやすい位置に配置
- `SELECT_used` (η²=0.318): SELECTボタン → 未使用なら省略・配置変更可、使用なら最適位置に配置
- `LeftArrow_used` (η²=0.294): LeftArrowボタン → 未使用なら省略・配置変更可、使用なら最適位置に配置
- `DownLeftArrow_used` (η²=0.272): DownLeftArrowボタン → 未使用なら省略・配置変更可、使用なら最適位置に配置
- `DownArrow_used` (η²=0.272): DownArrowボタン → 未使用なら省略・配置変更可、使用なら最適位置に配置
- `DownRightArrow_used` (η²=0.272): DownRightArrowボタン → 未使用なら省略・配置変更可、使用なら最適位置に配置
- `LStick_used` (η²=0.268): LStickボタン → 未使用なら省略・配置変更可、使用なら最適位置に配置
- `LB_used` (η²=0.261): LBボタン → 未使用なら省略・配置変更可、使用なら最適位置に配置
- `char_distance_px_mean` (η²=0.253): 対戦距離 → 遠距離プレイヤーは飛び道具入力を優先設計
- `char_distance_px_std` (η²=0.249): 対戦距離変動 → 押し付け vs 立ち回りスタイルの指標
- `RightArrow_used` (η²=0.238): RightArrowボタン → 未使用なら省略・配置変更可、使用なら最適位置に配置
- `CenterArrow_used` (η²=0.238): CenterArrowボタン → 未使用なら省略・配置変更可、使用なら最適位置に配置
- `A_used` (η²=0.145): Aボタン → 未使用なら省略・配置変更可、使用なら最適位置に配置
- `UpRightArrow_used` (η²=0.143): UpRightArrowボタン → 未使用なら省略・配置変更可、使用なら最適位置に配置

**効果量「中」（0.06≤η²<0.14）の特徴量 — 参考として個人対応を検討**

- `UpLeftArrow_used` (η²=0.100): UpLeftArrowボタン → 未使用なら省略・配置変更可、使用なら最適位置に配置
- `UpArrow_used` (η²=0.096): UpArrowボタン → 未使用なら省略・配置変更可、使用なら最適位置に配置
- `shoryuken_flag_std` (η²=0.089): 昇竜拳使用のばらつき
- `shoryuken_flag_mean` (η²=0.078): 昇竜拳使用頻度 → DP入力の操作性を優先

### 注意事項・今後の改善

| 課題 | 内容 |
|---|---|
| サンプル数不足 | n=36プロファイルのため統計的検出力が低い（推奨: 各選手10試合以上） |
| 偏りあり | nakamura・yamagutは各1試合のみ → η²の推定誤差が大きい |
| ANOVAの前提 | 正規性・等分散性は未検証（探索的分析として解釈すること） |