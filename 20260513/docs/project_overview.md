# 20260513 対戦データ解析プロジェクト — 概要

> **目的**: 格闘ゲーム（Street Fighter）のコントローラ入力ログから  
> プレイヤーを識別するMLモデルを構築し、個人対応コントローラ設計の基礎データを得る。

---

## ディレクトリ構成

```
20260513/
├── 2026_05_13対戦動画/          # MP4 対戦動画 (18本)  ← Git管理外
├── csv_data/                    # 生CSVデータ (18試合) ← Git管理外
├── output/                      # 前処理済み train.csv / test.csv
│
├── Scripts/                     # 全Pythonスクリプト
│   ├── run_pipeline.py              # メインパイプライン (Phase 1-3)
│   ├── video_analyzer.py            # Phase 1: 動画から視覚特徴を抽出
│   ├── preprocessor.py              # Phase 2: CSV前処理・マージ
│   ├── detect_commands.py           # 波動拳/昇竜拳のルールベース検出
│   ├── extract_clips.py             # 技クリップ画像の切り出し
│   ├── extract_negatives_only.py    # ネガティブサンプル抽出
│   ├── extract_features.py          # EfficientNet-B0 特徴量抽出 → features.npz
│   ├── train_move_detector.py       # [非推奨] 3クラス技検知SVM (F1=0.49)
│   ├── train_move_detector_binary.py# バイナリ技検知SVM (F1=0.76)
│   ├── predict_moves.py             # 学習済みモデルで技判定
│   ├── train_model.py               # [非推奨] プレイヤー識別RF v1
│   ├── train_model_v2.py            # プレイヤー識別RF v2 (TEST 77.8%)
│   ├── train_model_v3.py            # プレイヤー識別RF v3 (TEST 83.3%) ← 現行
│   ├── eda_01_data_quality.py       # EDA: データ品質確認
│   ├── eda_02_button_patterns.py    # EDA: ボタン使用パターン
│   ├── eda_03_behavioral_features.py# EDA: 行動特徴量分布・ANOVA
│   ├── eda_04_temporal.py           # EDA: 時系列ダイナミクス
│   ├── eda_05_distance_preference.py# EDA: 対戦距離の選好
│   ├── eda_06_hold_duration.py      # EDA: ボタン保持時間
│   ├── eda_run_all.py               # EDA全スクリプト並列実行
│   └── video_cache/                 # 動画特徴量CSVキャッシュ (run_pipeline.py が使用)
│
├── data/
│   ├── command_events.csv           # ルールベース検出コマンド (1,415件)
│   ├── features.npz                 # EfficientNet特徴量 (12,079フレーム × 1,280次元)
│   ├── clips/                       # 技クリップ画像 (hadouken/shoryuken/negative)
│   ├── move_model/                  # 3クラスSVM (非推奨, F1=0.49)
│   ├── move_model_binary/           # バイナリSVM (F1=0.76) ← 現行
│   └── player_model_v1/             # RFプレイヤーモデル v1 (アーカイブ)
│
└── docs/
    ├── project_overview.md          # このファイル
    ├── ml_model_report_v3.md        # プレイヤー識別モデル 最新レポート
    ├── ml_model_report_v2.md        # プレイヤー識別モデル v2 レポート
    ├── eda_report.md                # EDA総合レポート
    ├── eda/                         # EDA個別レポート + PNG
    └── plan_shoryuken_hadouken_detection.md
```

---

## データ概要

| 項目 | 値 |
|---|---|
| 対戦日 | 2026-05-13 |
| プレイヤー | 7名: akira, jin, keita, kotaro, nakamura, ryo, yamaguti |
| 試合数 | 18試合 (train: 9試合 `_1`, test: 9試合 `_2`) |
| 生フレーム数 | train 703,672 / test 589,176 |
| 特徴量列 | ボタン30列 + 視覚特徴 (hadouken_flag, shoryuken_flag, char_distance_px) |
| 分割方式 | 試合ファイル番号: `_1` → train, `_2` → test (データリーク防止) |

---

## 解析パイプライン

### Phase 1: 動画特徴量抽出 (`video_analyzer.py`)

MP4動画を1フレームずつ処理し、視覚的特徴を抽出する。

| 特徴量 | 説明 |
|---|---|
| `hadouken_flag` | 波動拳モーション検知 (0/1) |
| `shoryuken_flag` | 昇竜拳モーション検知 (0/1) ※精度低 (発火率9.7%、遠距離誤検知86%) |
| `char_distance_px` | キャラクター間距離 (ピクセル) |

**出力**: `Scripts/video_cache/{source_file}_features.csv`

### Phase 2: 前処理・マージ (`preprocessor.py`)

CSVを読み込み、動画特徴量とマージ、train/testに分割する。

**出力**: `output/train.csv`, `output/test.csv`

### Phase 3: コマンド検出 (`detect_commands.py`)

入力シーケンスからルールベースで波動拳/昇竜拳を検出する。

| コマンド | 件数 |
|---|---|
| hadouken (波動拳: ↓↘→ + 攻撃) | 643件 |
| shoryuken (昇竜拳: →↓↘ + 攻撃) | 772件 |
| 合計 | 1,415件 |

**出力**: `data/command_events.csv`

### Phase 4: 技検知ML (`extract_features.py` → `train_move_detector_binary.py`)

EfficientNet-B0で画像特徴を抽出し、SVMで技を判定する。

| モデル | クラス数 | Val macro F1 | 判定 |
|---|---|---|---|
| 3クラスSVM (`move_model/`) | shoryuken/hadouken/negative | 0.49 | **非推奨** |
| バイナリSVM (`move_model_binary/`) | special_move/negative | 0.76 | 現行 |

> バイナリSVMはプレイヤー識別特徴量としては不採用（negative recall=41.5%、全選手のverified_rate≒0.99で無差別）。コマンドカウント特徴量は `command_events.csv` から直接使用。

### Phase 5: プレイヤー識別ML (`train_model_v3.py`)

試合単位プロファイルを作成し、RandomForestでプレイヤーを識別する。

→ 詳細: [ml_model_report_v3.md](ml_model_report_v3.md)

---

## モデル進化履歴

| バージョン | スクリプト | TEST正解率 | Cohen's κ | 特徴量数 | 主な変更 |
|---|---|---|---|---|---|
| v1 | `train_model.py` | 88.9% | 0.8631 | 66 | 各ボタン押下率 mean+std |
| v2 | `train_model_v2.py` | 77.8% | 0.7293 | 43 | ダミー変数化 + 行動7特徴量追加 |
| **v3** | **`train_model_v3.py`** | **83.3%** | **0.7978** | **28** | EDA知見反映 + フェーズ・コマンド特徴量追加 |

> **v1→v2で精度が下がった理由**: ダミー変数化で情報量が減少（mean/stdは押下強度を含む）。  
> **v2→v3で精度が上がった理由**: 不要特徴量の削除（Arrow系0使用率、shoryuken誤検知86%）と新特徴量追加（フェーズ別密度、コマンドカウント）の相乗効果。

---

## EDA 主要知見 (→ 詳細: [eda_report.md](eda_report.md))

### プレイヤー識別に有効な特徴量 (η² 上位)

| 特徴量 | η² | 効果量 | 意味 |
|---|---|---|---|
| combo_rate | 0.920 | 大 | 連続入力頻度 (150ms以内) |
| B_used | 0.755 | 大 | Bボタン使用有無 |
| jump_rate | 0.660 | 大 | ジャンプ入力頻度 |
| crouch_rate | 0.626 | 大 | しゃがみ入力頻度 |
| RT_used | 0.625 | 大 | RTボタン使用有無 |

### 削除した特徴量とその理由

| 特徴量 | 理由 |
|---|---|
| Arrow系 9列 (CenterArrow/UpArrow等) | 全プレイヤーで使用率 = 0.000 |
| 方向系 11列 (Center/Up/Down/Left/Right/斜め4方向/RStick/START) | η² < 0.01 (個人差なし) |
| shoryuken_flag mean/std | 86%が距離>300pxで発火 → 誤検知主体 |
| special_ratio | shoryuken誤検知を含む → 信頼性低 |

### フェーズ別入力密度パターン

試合を4等分した各フェーズの入力密度 (フレーム/秒):

| プレイヤー | Phase 1 | Phase 2 | Phase 3 | Phase 4 | 傾向 |
|---|---|---|---|---|---|
| yamaguti | 643 | ... | ... | 412 | 序盤積極的 |
| nakamura | 高 | ... | ... | 低 | 序盤積極的 |
| keita | 388 | ... | ... | 526 | 終盤積極的 |

---

## コントローラ設計への示唆

プレイヤーを識別するほどの個人差がある特徴量は、コントローラのパーソナライズ優先度が高い。

### 最優先 (η² ≥ 0.60)

| 特徴量 | 設計への適用 |
|---|---|
| `combo_rate` (η²=0.92) | 隣接ボタン配置の最適化、素早い連続入力のしやすさ |
| `jump_rate` (η²=0.66) | 上入力感度・操作しやすさの個人設定 |
| `crouch_rate` (η²=0.63) | 下入力感度・操作しやすさの個人設定 |
| `input_density` (η²=0.51) | ボタン応答速度・クリック感の設計値 |

### 中優先 (η² 0.30–0.60)

| 特徴量 | 設計への適用 |
|---|---|
| `B_used` (η²=0.75) | Bボタン使用者 → アクセスしやすい位置に配置 |
| `RT_used` (η²=0.63) | RT使用者 → トリガー位置・感度調整 |
| `Y_used` (η²=0.58) | Y使用者 → 上ボタンへのアクセス最適化 |
| `diagonal_ratio` (η²=0.34) | 斜め入力依存度 → スティック/十字キーの斜め精度 |
| `hadouken_flag_mean` (η²=0.37) | 波動拳使用頻度 → QC入力のしやすさ優先 |

---

## 現行モデル (v3) の精度詳細

| プレイヤー | Precision | Recall | F1 | サンプル数 |
|---|---|---|---|---|
| akira | 1.000 | 1.000 | 1.000 | 2 |
| jin | 0.750 | 0.750 | 0.750 | 4 |
| keita | 0.667 | 0.667 | 0.667 | 3 |
| kotaro | 0.800 | 1.000 | 0.889 | 4 |
| nakamura | 1.000 | 1.000 | 1.000 | 1 |
| ryo | 1.000 | 0.667 | 0.800 | 3 |
| yamaguti | 1.000 | 1.000 | 1.000 | 1 |
| **macro avg** | **0.888** | **0.869** | **0.872** | **18** |

### 誤分類の内訳 (3件 / 18試合)

| 真ラベル | 予測 | 試合ファイル | 考察 |
|---|---|---|---|
| jin → kotaro | `20260513_keita_jin_2` | keita との対戦でjinがkotaro風のプレイをした可能性 |
| keita → jin | `20260513_keita_ryo_2` | ryo との対戦でkeita がjin風のプレイをした可能性 |
| ryo → keita | `20260513_kotaro_ryo_2` | kotaro との対戦でryo がkeita風のプレイをした可能性 |

jin / keita / ryo は三つ巴の誤分類パターン。対戦相手の影響でプレイスタイルが変化している可能性がある。

---

## 今後の改善候補

| 優先度 | 改善案 | 期待効果 |
|---|---|---|
| 高 | 対戦相手情報を特徴量に追加 | jin/keita/ryo の三つ巴誤分類を解消できる可能性 |
| 中 | ボタン保持時間特徴量の追加 (EDA 06) | 押下スタイルの個人差を捉える |
| 中 | 対戦距離の選好特徴量 (EDA 05) | 遠距離/近距離プレイヤーの識別精度向上 |
| 低 | LOO-CV（Leave-One-Match-Out）による汎化性能推定 | より信頼性の高い評価 |
| 低 | GBM/XGBoost への切替 | RF比で数%の精度向上が見込まれる |

---

## 実行手順 (再現方法)

```bash
# 1. パイプライン実行 (Phase 1-3: 動画処理 + CSV前処理)
cd 20260513/Scripts
python run_pipeline.py

# 2. コマンド検出
python detect_commands.py

# 3. 技検知ML (EfficientNet特徴抽出 → バイナリSVM学習)
python extract_clips.py
python extract_negatives_only.py
python extract_features.py
python train_move_detector_binary.py

# 4. プレイヤー識別MLモデル v3 (現行最良モデル)
python train_model_v3.py

# 5. EDA (全6スクリプト並列実行)
python eda_run_all.py
```
