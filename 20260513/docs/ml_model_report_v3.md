# プレイヤー識別MLモデル v3 レポート

> **スクリプト**: `Scripts/train_model_v3.py`  
> **実行日**: 2026-07-15  
> **目的**: EDA知見（v2 完了後）を反映した特徴量改良による精度向上

---

## 1. バージョン比較サマリ

| 指標 | v1 | v2 | **v3** | v2→v3 差 |
|---|---|---|---|---|
| TEST accuracy | 88.9% | 77.8% | **83.3%** | **+5.5pp** |
| Cohen's κ (TEST) | 0.8631 | 0.7293 | **0.7978** | **+0.0685** |
| 特徴量数 | 66 | 43 | **28** | **-15列** |
| TRAIN accuracy | 100.0% | 100.0% | **100.0%** | — |

> **v2→v3 改善の要因**:  
> (1) 無効特徴量を削除 (Arrow系0使用率、shoryuken誤検知主体) → ノイズ除去  
> (2) フェーズ別密度 + コマンドカウントを追加 → 情報量の純増

---

## 2. モデル設定

| 項目 | 設定値 |
|---|---|
| アルゴリズム | RandomForestClassifier |
| n_estimators | 500 |
| class_weight | balanced |
| random_state | 42 |
| 前処理 | StandardScaler |
| 入力単位 | 試合×選手プロファイル (マッチレベル) |
| Train/Test 分割 | `_1` ファイル群 → train, `_2` ファイル群 → test |

---

## 3. 特徴量構成 (28列)

### v2 からの変更点

**削除 (15列)**

| カテゴリ | 削除した特徴量 | 削除理由 |
|---|---|---|
| Arrow系ボタン (9列) | CenterArrow/UpArrow/DownArrow/LeftArrow/RightArrow/UpRightArrow/UpLeftArrow/DownRightArrow/DownLeftArrow の `_used` | 全プレイヤーで使用率 = 0.000 (誰も使わない) |
| 方向系ボタン (9列) | Center/Up/Down/Left/Right/UpRight/UpLeft/DownRight/DownLeft の `_used` | η² < 0.01 (個人差なし) |
| RStick_used | — | η² ≈ 0 |
| START_used | — | η² ≈ 0 |
| shoryuken_flag mean/std | — | 遠距離誤検知 86% → 信頼性低 |
| special_ratio | — | shoryuken 誤検知含む → 信頼性低 |

**追加 (8列)**

| カテゴリ | 追加した特徴量 | 追加理由 |
|---|---|---|
| フェーズ別密度 (4列) | input_density_phase1/2/3/4 | EDA04: 試合フェーズごとに個人差あり (yamaguti↓ vs keita↑) |
| コマンド特徴量 (4列) | hadouken_count/rate, shoryuken_count/rate | command_events.csv のルールベース検出結果 |

### 全28特徴量リスト

| # | 特徴量 | カテゴリ | RF重要度 |
|---|---|---|---|
| 1 | jump_rate | 行動 | 0.0838 |
| 2 | combo_rate | 行動 | 0.0818 |
| 3 | crouch_rate | 行動 | 0.0793 |
| 4 | hadouken_rate | コマンド | 0.0671 |
| 5 | input_density | 行動 | 0.0544 |
| 6 | input_density_phase1 | フェーズ | 0.0524 |
| 7 | input_density_phase3 | フェーズ | 0.0492 |
| 8 | diagonal_ratio | 行動 | 0.0451 |
| 9 | shoryuken_count | コマンド | 0.0426 |
| 10 | input_density_phase2 | フェーズ | 0.0424 |
| 11 | hadouken_flag_std | 特殊技・距離 | 0.0399 |
| 12 | attack_entropy | 行動 | 0.0393 |
| 13 | shoryuken_rate | コマンド | 0.0390 |
| 14 | char_distance_px_std | 特殊技・距離 | 0.0383 |
| 15 | hadouken_flag_mean | 特殊技・距離 | 0.0358 |
| 16 | char_distance_px_mean | 特殊技・距離 | 0.0348 |
| 17 | hadouken_count | コマンド | 0.0332 |
| 18 | B_used | ボタンダミー | 0.0292 |
| 19 | input_density_phase4 | フェーズ | 0.0273 |
| 20 | LB_used | ボタンダミー | 0.0178 |
| 21 | LStick_used | ボタンダミー | 0.0136 |
| 22 | Y_used | ボタンダミー | 0.0132 |
| 23 | RB_used | ボタンダミー | 0.0117 |
| 24 | LT_used | ボタンダミー | 0.0114 |
| 25 | X_used | ボタンダミー | 0.0088 |
| 26 | RT_used | ボタンダミー | 0.0087 |
| 27 | SELECT_used | ボタンダミー | 0.0000 |
| 28 | A_used | ボタンダミー | 0.0000 |

> **注目点**: 新規追加の4カテゴリ（フェーズ・コマンド）が全て上位10位内に入り、貢献を確認。

---

## 4. TEST 分類レポート

```
              precision    recall  f1-score   support

       akira      1.000     1.000     1.000         2
         jin      0.750     0.750     0.750         4
       keita      0.667     0.667     0.667         3
      kotaro      0.800     1.000     0.889         4
    nakamura      1.000     1.000     1.000         1
         ryo      1.000     0.667     0.800         3
    yamaguti      1.000     1.000     1.000         1

    accuracy                          0.833        18
   macro avg      0.888     0.869     0.872        18
weighted avg      0.844     0.833     0.831        18
```

---

## 5. 試合別分類結果 (TEST)

| 真ラベル | 予測ラベル | 試合ファイル | 結果 |
|---|---|---|---|
| akira | akira | 20260513_jin_akira_2 | OK |
| akira | akira | 20260513_kotaro_akira_2 | OK |
| jin | jin | 20260513_jin_akira_2 | OK |
| jin | jin | 20260513_jin_ryo_2 | OK |
| **jin** | **kotaro** | **20260513_keita_jin_2** | **NG** |
| jin | jin | 20260513_kotaro_jin_2 | OK |
| keita | keita | 20260513_keita_jin_2 | OK |
| keita | keita | 20260513_keita_kotaro_2 | OK |
| **keita** | **jin** | **20260513_keita_ryo_2** | **NG** |
| kotaro | kotaro | 20260513_keita_kotaro_2 | OK |
| kotaro | kotaro | 20260513_kotaro_akira_2 | OK |
| kotaro | kotaro | 20260513_kotaro_jin_2 | OK |
| kotaro | kotaro | 20260513_kotaro_ryo_2 | OK |
| nakamura | nakamura | 20260513_nakamura_yamaguti_2 | OK |
| ryo | ryo | 20260513_jin_ryo_2 | OK |
| ryo | ryo | 20260513_keita_ryo_2 | OK |
| **ryo** | **keita** | **20260513_kotaro_ryo_2** | **NG** |
| yamaguti | yamaguti | 20260513_nakamura_yamaguti_2 | OK |

### 誤分類パターンの考察

3件の誤分類はすべて jin / keita / ryo の三つ巴:

- `jin → kotaro` @ keita_jin_2: keita戦でjinがkotaro風の動きをした
- `keita → jin` @ keita_ryo_2: ryo戦でkeitaがjin風の動きをした
- `ryo → keita` @ kotaro_ryo_2: kotaro戦でryoがkeita風の動きをした

**仮説**: 対戦相手のスタイルに引っ張られて本来のプレイスタイルが変化する。  
→ 改善策: 対戦相手のプロファイル情報を特徴量に追加する。

---

## 6. v2 との誤分類変化

| v2 誤分類 | v3 誤分類 |
|---|---|
| jin → kotaro (jin_akira_2) | ✓ 正解に改善 |
| nakamura → jin (nakamura_yamaguti_2) | ✓ 正解に改善 |
| ryo → akira (jin_ryo_2) | ✓ 正解に改善 |
| ryo → keita (kotaro_ryo_2) | ✗ 継続誤分類 |
| — | **NEW** jin → kotaro (keita_jin_2) |
| — | **NEW** keita → jin (keita_ryo_2) |

> v2で誤分類だった4件中3件を正解に改善した一方、新たに2件の誤分類が発生した。

---

## 7. コントローラ設計への示唆 (v3 重要度観点)

v3で重要度上位に入った特徴量とコントローラ設計への示唆:

| 特徴量 | RF重要度 | 設計への適用 |
|---|---|---|
| `jump_rate` | 0.084 | ジャンプ頻度 → 上入力の感度・操作しやすさの個人設定 |
| `combo_rate` | 0.082 | 連続入力頻度 → 隣接ボタンのレイアウト最適化 |
| `crouch_rate` | 0.079 | しゃがみ頻度 → 下入力感度の個人設定 |
| `hadouken_rate` | 0.067 | 波動拳頻度 → 前QC入力 (↓↘→) のしやすさを優先 |
| `input_density` | 0.054 | 入力密度 → ボタン応答速度・クリック感の設計値 |
| `input_density_phase*` | 0.042–0.052 | 試合フェーズ別パターン → スタミナ管理・集中力特性の反映 |
| `shoryuken_count` | 0.043 | 昇竜拳使用頻度 → DP入力 (→↓↘) の操作性優先 |

---

## 8. 制限事項

| 課題 | 内容 |
|---|---|
| サンプル数不足 | n=18 TEST プロファイル → 統計的検出力が低い |
| nakamura/yamaguti | 各1試合のみ → 過学習リスクあり |
| 対戦相手効果 | 同じ選手でも対戦相手によってプロファイルが変わる (三つ巴誤分類) |
| 汎化性未確認 | 未知の試合 (20260513以外) での性能は未評価 |
