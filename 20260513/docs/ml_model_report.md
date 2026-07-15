# プレイヤー識別MLモデル 評価レポート

## 1. モデル概要

| 項目 | 内容 |
|---|---|
| モデル | RandomForestClassifier |
| タスク | 多クラス分類（7クラス: akira / jin / keita / kotaro / nakamura / ryo / yamaguti） |
| アプローチ | 試合単位プロファイル照合（match-level profile aggregation） |
| 特徴量数 | 66（33ボタン列 × mean + std） |
| 学習サンプル数 | 18プロファイル（9試合 × 2選手/試合） |
| テストサンプル数 | 18プロファイル（9試合 × 2選手/試合） |
| ハイパーパラメータ | n_estimators=500, class_weight="balanced", random_state=42 |

---

## 2. 評価指標

### 正解率（Accuracy）

| セット | 正解率 | 正解数 / 総試合数 |
|---|---|---|
| TRAIN | **100.0%** | 18 / 18 |
| TEST  | **88.9%**  | 16 / 18 |

### Cohen's Kappa

> Cohen's Kappa（κ）は偶然一致を除外した分類精度の指標。κ=1.0が完全一致、κ=0が偶然レベル、κ<0が偶然以下。

| セット | κ値 |
|---|---|
| TRAIN | 1.0000 |
| TEST  | 0.8631 |

テストκ=0.863は「ほぼ完全一致（Almost Perfect）」の水準（0.81以上）。

---

## 3. 決定係数（R²）・自由度調整済み決定係数について

> **本モデルは分類タスク（RandomForestClassifier）であり、回帰モデルを前提とする決定係数R²は定義上適用できません。**

回帰モデルでの参考値（仮想的に計算した場合）：

| 指標 | 式 | 値 |
|---|---|---|
| 決定係数 R² | Accuracy（正解率） | TEST: 0.889 |
| 自由度調整済み R² | 1 − (1−R²)(n−1)/(n−k−1) | **計算不能（k=66 > n=18）** |

自由度調整済み R² は、特徴量数 k が サンプル数 n を超えると分母が負になり発散します（k=66、n=18 のため n−k−1=−49）。  
これはサンプル不足の警告でもあり、追加データ（試合数の増加）による改善が望まれます。

分類モデルの適合度として Cohen's Kappa（κ=0.863）を代替指標として使用します。

### 誤識別の詳細

| 真のラベル | 予測ラベル | ファイル |
|---|---|---|
| nakamura | jin | 20260513_nakamura_yamaguti_2 |
| yamaguti | ryo | 20260513_nakamura_yamaguti_2 |

原因: nakamura・yamaguti は学習試合が各1試合のみ（他の選手は3〜4試合）。

---

## 4. 特徴量重要度（Feature Importance）

### 4-1. Random Forest Impurity-based Importance（全66カラム）

| ランク | 特徴量 | 重要度 |
|---|---|---|
| 1 | X_mean | 0.039283 |
| 2 | Center_mean | 0.037381 |
| 3 | Down_mean | 0.037180 |
| 4 | UpLeft_mean | 0.036555 |
| 5 | B_std | 0.034806 |
| 6 | Down_std | 0.034804 |
| 7 | Center_std | 0.034303 |
| 8 | RT_mean | 0.033053 |
| 9 | RT_std | 0.032964 |
| 10 | X_std | 0.032214 |
| 11 | B_mean | 0.028807 |
| 12 | UpLeft_std | 0.028768 |
| 13 | A_mean | 0.027086 |
| 14 | Y_mean | 0.026312 |
| 15 | Y_std | 0.025801 |
| 16 | A_std | 0.025565 |
| 17 | Right_mean | 0.024786 |
| 18 | Up_std | 0.024369 |
| 19 | UpRight_mean | 0.022106 |
| 20 | Left_mean | 0.021689 |
| 21 | Right_std | 0.021378 |
| 22 | DownRight_mean | 0.020909 |
| 23 | DownRight_std | 0.020568 |
| 24 | UpRight_std | 0.020187 |
| 25 | Up_mean | 0.019346 |
| 26 | LT_std | 0.019154 |
| 27 | hadouken_flag_mean | 0.018804 |
| 28 | Left_std | 0.018287 |
| 29 | hadouken_flag_std | 0.017598 |
| 30 | char_distance_px_std | 0.016477 |
| 31 | char_distance_px_mean | 0.015907 |
| 32 | LT_mean | 0.015712 |
| 33 | DownLeft_std | 0.013719 |
| 34 | DownLeftArrow_mean | 0.011185 |
| 35 | DownArrow_std | 0.011118 |
| 36 | DownArrow_mean | 0.011017 |
| 37 | DownLeft_mean | 0.010977 |
| 38 | shoryuken_flag_std | 0.009861 |
| 39 | RB_std | 0.009009 |
| 40 | DownRightArrow_mean | 0.008820 |
| 41 | DownLeftArrow_std | 0.007700 |
| 42 | shoryuken_flag_mean | 0.007198 |
| 43 | LStick_mean | 0.006860 |
| 44 | DownRightArrow_std | 0.006791 |
| 45 | RightArrow_mean | 0.006363 |
| 46 | LeftArrow_std | 0.006313 |
| 47 | RB_mean | 0.006234 |
| 48 | LStick_std | 0.006098 |
| 49 | LB_mean | 0.006017 |
| 50 | RightArrow_std | 0.005423 |
| 51 | LB_std | 0.004665 |
| 52 | LeftArrow_mean | 0.004538 |
| 53 | CenterArrow_std | 0.004214 |
| 54 | CenterArrow_mean | 0.003725 |
| 55 | UpRightArrow_std | 0.000000 |
| 56 | UpLeftArrow_std | 0.000000 |
| 57 | SELECT_std | 0.000000 |
| 58 | RStick_std | 0.000000 |
| 59 | START_std | 0.000000 |
| 60 | UpArrow_std | 0.000000 |
| 61 | UpRightArrow_mean | 0.000000 |
| 62 | UpLeftArrow_mean | 0.000000 |
| 63 | RStick_mean | 0.000000 |
| 64 | SELECT_mean | 0.000000 |
| 65 | START_mean | 0.000000 |
| 66 | UpArrow_mean | 0.000000 |

---

### 4-2. Permutation Importance（テストセット, n_repeats=30）と有意性

> 有意性の判定: mean − 2×std > 0 を満たす場合を「有意（YES）」とする（95%信頼区間が0より大）。

| 特徴量 | mean | std | 有意 |
|---|---|---|---|
| X_mean | 0.000000 | 0.000000 | NO |
| Y_mean | 0.012963 | 0.023497 | NO |
| B_mean | 0.038889 | 0.025459 | NO |
| **A_mean** | **0.046296** | **0.020704** | **YES** |
| RB_mean | 0.000000 | 0.000000 | NO |
| LB_mean | 0.000000 | 0.000000 | NO |
| RT_mean | 0.033333 | 0.027217 | NO |
| LT_mean | 0.000000 | 0.000000 | NO |
| RStick_mean | 0.000000 | 0.000000 | NO |
| LStick_mean | 0.000000 | 0.000000 | NO |
| SELECT_mean | 0.000000 | 0.000000 | NO |
| START_mean | 0.000000 | 0.000000 | NO |
| CenterArrow_mean | 0.000000 | 0.000000 | NO |
| UpArrow_mean | 0.000000 | 0.000000 | NO |
| DownArrow_mean | 0.000000 | 0.000000 | NO |
| LeftArrow_mean | 0.000000 | 0.000000 | NO |
| RightArrow_mean | 0.000000 | 0.000000 | NO |
| UpRightArrow_mean | 0.000000 | 0.000000 | NO |
| UpLeftArrow_mean | 0.000000 | 0.000000 | NO |
| DownRightArrow_mean | 0.000000 | 0.000000 | NO |
| DownLeftArrow_mean | 0.000000 | 0.000000 | NO |
| Center_mean | 0.009259 | 0.020704 | NO |
| Up_mean | 0.000000 | 0.000000 | NO |
| Down_mean | 0.000000 | 0.000000 | NO |
| Right_mean | 0.000000 | 0.000000 | NO |
| Left_mean | 0.003704 | 0.013858 | NO |
| UpRight_mean | 0.012963 | 0.023497 | NO |
| UpLeft_mean | 0.000000 | 0.000000 | NO |
| DownRight_mean | 0.000000 | 0.000000 | NO |
| DownLeft_mean | 0.000000 | 0.000000 | NO |
| hadouken_flag_mean | 0.000000 | 0.000000 | NO |
| shoryuken_flag_mean | 0.000000 | 0.000000 | NO |
| char_distance_px_mean | 0.000000 | 0.000000 | NO |
| X_std | 0.029630 | 0.027716 | NO |
| Y_std | 0.027778 | 0.027778 | NO |
| B_std | 0.038889 | 0.025459 | NO |
| **A_std** | **0.046296** | **0.020704** | **YES** |
| RB_std | 0.000000 | 0.000000 | NO |
| LB_std | 0.000000 | 0.000000 | NO |
| RT_std | 0.007407 | 0.018885 | NO |
| LT_std | 0.005556 | 0.016667 | NO |
| RStick_std | 0.000000 | 0.000000 | NO |
| LStick_std | 0.000000 | 0.000000 | NO |
| SELECT_std | 0.000000 | 0.000000 | NO |
| START_std | 0.000000 | 0.000000 | NO |
| CenterArrow_std | 0.000000 | 0.000000 | NO |
| UpArrow_std | 0.000000 | 0.000000 | NO |
| DownArrow_std | 0.000000 | 0.000000 | NO |
| LeftArrow_std | 0.000000 | 0.000000 | NO |
| RightArrow_std | 0.000000 | 0.000000 | NO |
| UpRightArrow_std | 0.000000 | 0.000000 | NO |
| UpLeftArrow_std | 0.000000 | 0.000000 | NO |
| DownRightArrow_std | 0.000000 | 0.000000 | NO |
| DownLeftArrow_std | 0.000000 | 0.000000 | NO |
| Center_std | 0.000000 | 0.000000 | NO |
| Up_std | 0.000000 | 0.000000 | NO |
| Down_std | 0.033333 | 0.027217 | NO |
| Right_std | 0.000000 | 0.000000 | NO |
| Left_std | 0.001852 | 0.009973 | NO |
| UpRight_std | 0.000000 | 0.000000 | NO |
| UpLeft_std | 0.000000 | 0.000000 | NO |
| DownRight_std | 0.000000 | 0.000000 | NO |
| DownLeft_std | 0.000000 | 0.000000 | NO |
| hadouken_flag_std | 0.000000 | 0.000000 | NO |
| shoryuken_flag_std | 0.000000 | 0.000000 | NO |
| char_distance_px_std | 0.000000 | 0.000000 | NO |

#### 有意と判定された特徴量（2件）

| 特徴量 | mean | std | 解釈 |
|---|---|---|---|
| A_mean | 0.0463 | 0.0207 | Aボタン押下率の平均（攻撃頻度の個人差） |
| A_std | 0.0463 | 0.0207 | Aボタン押下率のばらつき（攻撃リズムの個人差） |

#### 注意: 有意性判定の統計的制限

Permutation Importanceの有意性判定は **テストサンプル数=18** に基づいており、  
統計的検出力（power）が極めて低い状態です。  
「NO（非有意）」であっても実際には予測に貢献している可能性があります  
（RF impurity importanceでは `X_mean`, `Center_mean`, `Down_mean` なども高い値を示している）。  
信頼性向上には試合数の増加（最低50試合以上を推奨）が必要です。

---

## 5. まとめ

| 観点 | 評価 |
|---|---|
| 全体精度 | テスト正解率 88.9%（16/18）・κ=0.863 |
| 決定係数 R² | 分類モデルのため非適用。Cohen's Kappa を代替使用 |
| 自由度調整済み R² | k(66) > n(18) のため計算不能（過学習リスク）|
| 有意な特徴量 | A_mean・A_std のみ（サンプル不足による統計的制限） |
| 重要度上位グループ | X, Center, Down, UpLeft, B, RT（基本操作系） |
| 動画特徴量の貢献 | hadouken_flag_mean: rank27・char_distance_px: rank30〜31 |
| 改善方針 | 試合数増加（特にnakamura・yamaguti）、クロスバリデーション導入 |
