# 昇竜拳・波動拳 動的検知モデル 計画書

## 背景と目的

現状の `shoryuken_flag` は動画解析由来だが誤検知が深刻：
- 平均連続 145 フレーム発火（約 29 秒間連続 → 技の発生時間は < 0.5 秒なので明らかに異常）
- 86% が char_distance > 300px（遠距離）で発火 → 昇竜拳は近接技なので誤り

`hadouken_flag` は比較的正常だが、精度向上の余地あり。

**目的**: 動画クリップをもとに学習させた分類モデルで精度の高い技検知を実現し、
プレイヤー識別モデル (`train_model_v*.py`) の特徴量として使用する。

---

## 全体アーキテクチャ

```
[コマンド入力から候補フレーム特定]
        ↓
[動画クリップ切り出し (N 秒前後)]
        ↓
[アノテーション (正例: shoryuken / hadouken / negative)]
        ↓
[CNN モデル学習 + 検証]
        ↓
[全フレームへの推論 → フラグ生成]
        ↓
[train_model_v*.py に統合]
```

---

## フェーズ 1: 学習データ作成

### 1-1. 正例候補フレームの特定（コマンド入力逆算）

既存の CSV データからコントローラーコマンドを逆算して「技が出た可能性が高いフレーム」を特定する。

| 技名 | コマンド | ボタン列パターン（15フレーム以内） |
|---|---|---|
| **昇竜拳** (Dragon Punch) | → ↓ ↘ + 攻撃 | `Right=1` → `Down=1` → `DownRight=1` → `(X or Y or B or A)=1` |
| **波動拳** (Hadouken) | ↓ ↘ → + 攻撃 | `Down=1` → `DownRight=1` → `Right=1` → `(X or Y or B or A)=1` |

実装スクリプト: `Scripts/detect_commands.py`

```python
def detect_dp_command(df: pd.DataFrame, window: int = 15) -> pd.Series:
    """
    昇竜拳コマンド (Right→Down→DownRight+attack) を window フレーム以内に検出。
    Returns: boolean Series (True = コマンド成立フレーム)
    """
    ...

def detect_qcf_command(df: pd.DataFrame, window: int = 15) -> pd.Series:
    """
    波動拳コマンド (Down→DownRight→Right+attack) を window フレーム以内に検出。
    """
    ...
```

### 1-2. 動画ファイルの構成

動画ファイルは解凍済みで直接アクセス可能：

```
20260513/2026_05_13対戦動画/
  20260513_jin_akira_1.mp4       ← train.csv の source_file = "20260513_jin_akira_1"
  20260513_jin_akira_2.mp4       ← test.csv  の source_file = "20260513_jin_akira_2"
  20260513_jin_ryo_1.mp4
  20260513_jin_ryo_2.mp4
  20260513_keita_jin_1.mp4
  20260513_keita_jin_2.mp4
  20260513_keita_kotaro_1.mp4
  20260513_keita_kotaro_2.mp4
  20260513_keita_ryo_1.mp4
  20260513_keita_ryo_2.mp4
  20260513_kotaro_akira_1.mp4
  20260513_kotaro_akira_2.mp4
  20260513_kotaro_jin_1.mp4
  20260513_kotaro_jin_2.mp4
  20260513_kotaro_ryo_1.mp4
  20260513_kotaro_ryo_2.mp4
  20260513_nakamura_yamaguti_1.mp4
  20260513_nakamura_yamaguti_2.mp4
```

**source_file → 動画パスのマッピング:**
```python
VIDEO_DIR = Path("20260513/2026_05_13対戦動画")
video_path = VIDEO_DIR / f"{source_file}.mp4"
```

**⚠ 要確認: timestamp_sec とビデオ内時刻の対応**
CSV の `timestamp_sec` がビデオの経過秒数と一致するか検証が必要。
- 一致する場合: `ffmpeg -ss {timestamp_sec - 0.5}` で直接シーク可能
- ズレがある場合: 録画開始時刻との差分を補正する必要あり

### 1-3. 動画クリップ切り出し

コマンド成立フレームの `timestamp_sec` から前後の動画区間を切り出す。

```
切り出し範囲: コマンド成立フレーム の -0.5秒 ～ +2.0秒
形式: MP4（元動画と同じコーデック、-c copy で高速切り出し）
出力先: 20260513/data/clips/{move}/{source_file}_{timestamp:.2f}.mp4
```

使用ツール: `ffmpeg` によるクリップ切り出し

```bash
ffmpeg -i "20260513/2026_05_13対戦動画/{source_file}.mp4" \
       -ss {start_sec} -t 2.5 -c copy \
       "20260513/data/clips/{move}/{source_file}_{ts:.2f}.mp4"
```

実装スクリプト: `Scripts/extract_clips.py`
- `detect_commands.py` の出力（候補フレーム CSV）を入力として受け取る
- 全 18 本の MP4 に対してバッチ処理
- 切り出しクリップの数・配置を CSV で記録（後のアノテーション管理用）

### 1-4. アノテーション

| ラベル | 内容 | 収集目標 |
|---|---|---|
| `shoryuken` | 昇竜拳が成立（コマンド + 技モーション確認） | 各プレイヤー 20〜50 クリップ |
| `hadouken` | 波動拳が成立 | 各プレイヤー 20〜50 クリップ |
| `negative` | コマンド入力なし（ランダムサンプリング） | 200〜300 クリップ |
| `failed_dp` | コマンドは入力されたが技が出なかった（誤入力） | 取得できれば追加 |

アノテーションツール: 手動確認 or `labelImg` / `VGG Image Annotator`

---

## フェーズ 2: モデル学習

### 選択肢比較

| アプローチ | 実装コスト | 期待精度 | 備考 |
|---|---|---|---|
| **A: ルールベース（コマンド検出のみ）** | 低 | 中（技が出るとは限らない） | CSV のみで動作、動画不要 |
| **B: CNN（動画フレーム分類）** | 高 | 高 | GPU 環境推奨、データ量依存 |
| **C: A + B ハイブリッド** | 最高 | 最高 | コマンド検出 × 映像確認の AND 条件 |

**推奨実装順序**:
1. まず **A（ルールベース）** で評価 → 精度確認
2. 不十分なら **B（CNN）** に移行
3. A・B どちらも一定精度が出たら **C（ハイブリッド）** を検討

### B: CNN モデル仕様

```
入力: 224 × 224 RGB × 8 フレーム積み（時間軸をチャンネルとして扱う）
バックボーン: ResNet-18（ImageNet 事前学習済み）
出力: 3 クラス (none / hadouken / shoryuken)
損失: CrossEntropyLoss（class_weight でクラス不均衡対応）
Optimizer: Adam (lr=1e-4)
Epoch: 30〜50（EarlyStopping 付き）
Train/Val 分割: 試合単位でホールドアウト（同じ試合のフレームが train/val に混在しないよう）
```

フレームの前処理:
```python
transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                         std=[0.229, 0.224, 0.225]),
])
```

---

## フェーズ 3: 推論・フラグ生成

### スライディングウィンドウ推論

```python
# 全フレームに 8 フレームウィンドウで推論
for i in range(0, total_frames, stride=1):
    clip = frames[i:i+8]
    prob = model(clip)  # shape: (3,)
    shoryuken_prob[i] = prob[2]
    hadouken_prob[i]  = prob[1]
```

### フラグ生成ルール

```python
shoryuken_flag_new = (shoryuken_prob > 0.7).astype(int)
hadouken_flag_new  = (hadouken_prob  > 0.7).astype(int)
```

後処理（短すぎる発火の除去）:
- 連続 3 フレーム未満の発火はノイズとして除去
- 連続 30 フレーム以上の発火も異常として除去（技のモーションは最大 0.5〜1 秒 ≈ 2.5〜5 フレーム@5fps）

### 出力

```
20260513/output/video_cache_v2/{source_file}_labels.csv
  列: timestamp_sec, shoryuken_flag, hadouken_flag, shoryuken_prob, hadouken_prob
```

---

## フェーズ 4: プレイヤー識別モデルへの統合

### 変更内容 (train_model_v4.py)

```python
# 旧: video_cache の shoryuken_flag (誤検知)
# 新: video_cache_v2 の shoryuken_flag (新モデル)

features += [
    "shoryuken_flag_mean",   # 復活（精度改善後）
    "shoryuken_flag_std",
    "shoryuken_valid_rate",  # 距離 < 200px での発火率
]
```

### 精度比較目標

| モデル | 精度 | κ |
|---|---|---|
| v2（現状、誤検知込み） | 77.8% | 0.7293 |
| v3（Arrow 系削除 + フェーズ特徴量追加） | 目標 79%+ | — |
| v4（新 shoryuken_flag 統合後） | 目標 82%+ | — |

---

## 実装チェックリスト

### フェーズ 1
- [ ] `Scripts/detect_commands.py` 作成（コマンド検出ロジック）
- [ ] コマンド候補フレームの CSV 出力（全 18 試合分）
- [ ] timestamp_sec とビデオ内時刻の対応を1本のMP4で検証
- [ ] `Scripts/extract_clips.py` 作成（ffmpeg バッチ切り出し）
- [ ] クリップ切り出し実行（対象: `20260513/2026_05_13対戦動画/*.mp4`）
- [ ] アノテーション（手動確認・ラベル付け）

### フェーズ 2
- [ ] A: ルールベース評価スクリプト作成・実行
- [ ] B: CNN モデル定義・学習スクリプト作成（要 GPU 環境）
- [ ] 検証: Precision/Recall/F1 per class

### フェーズ 3
- [ ] 推論スクリプト作成
- [ ] `video_cache_v2/` への出力
- [ ] 後処理（短い発火の除去）

### フェーズ 4
- [ ] `train_model_v4.py` への統合
- [ ] 精度比較（v2 vs v3 vs v4）

---

## 備考・前提条件

- **動画ファイルは解凍済みで直接利用可能**: `20260513/2026_05_13対戦動画/*.mp4`（18 本）
- 旧 `.7z` ファイルは `past/` ディレクトリに移動済み（バックアップとして残存）
- `ffmpeg` が PATH に通っていることを事前に確認すること
- GPU 環境は任意だが、CNN 学習には推奨（CPU でも可、時間がかかる）
- フェーズ 1 のアノテーションは最低 100 クリップ程度から始めて様子を見る
- コマンド検出（フェーズ 2A）だけで十分な精度が出た場合、CNN は不要
- 実装前に承認依頼を行う（各フェーズ着手前）
