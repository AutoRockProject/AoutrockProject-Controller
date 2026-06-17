# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

格闘ゲーム（Capcom Arcade Stadium / Street Fighter）の対戦データ収集パイプライン。
コントローラー入力をCSVに記録 → 動画から距離データを抽出 → CSVに転記という3段階構成。

## スクリプト実行

```bash
# ① コントローラー入力記録（OBS録画と同期して起動）
python main.py
# 起動後に「名前1 名前2」を入力（例: kotaro jin）
# Ctrl+C で終了 → CSVと動画が同じディレクトリに保存される

# ② 動画から距離データを計算してCSVに追記
python calcDistance.py <対象ディレクトリのパス>
# 例: python calcDistance.py C:/Users/sat00/Documents/matches

# easyocr がインストールされていれば動画の最初のフレームからオフセットを自動検出する。
# 検出できない場合は --offset で手動指定（動画の録画開始フレームに映っているタイムスタンプ値を秒に変換した値）
python calcDistance.py <対象ディレクトリのパス> --offset <秒数>

```

## アーキテクチャ


### main.py の構造

- **マルチスレッド**: コントローラー1台につき1スレッド（`listen_to_controller`）
- **OBS WebSocket 連携**: `obsws_python` で録画開始・停止・ファイル移動を自動化
- **タイムスタンプ**: `time.perf_counter()` 基準で `MM:SS.microseconds` 形式。`index.html` ブラウザソースをOBSに重ねて録画画面にも表示
- **入力変換の注意点**:
  - アナログスティック (ABS_X/Y): デッドゾーン処理後に方向文字列へ変換。Y軸は**下がプラス**
  - 十字キー (ABS_HAT0X/Y): 状態を保持して斜め方向を合成
  - RT/LT (ABS_RZ/ABS_Z): state が 0/1 でなくアナログ値のため手動でフラグ管理
- **デバウンス不使用**: `main.py` はデバウンス処理なし（`test.py` には実装あり）
- **差分記録**: 前回行と同一なら書き込みをスキップ (`latestrow` で追跡)

### calcDistance.py の構造

- **HSV検出**: リュウ（白い道着）とケン（青緑の道着）をHSV色空間で識別
- **ROI**: Y=200〜950 の範囲のみ処理（UIを除外）
- **KOギャップ検出**: 連続欠損が10フレーム超でギャップ状態へ移行し以降をNaNとする。ギャップ解除は5フレーム連続検出が必要（KO演出中の誤検出抑制）
- **欠損補完**: 10フレーム以下の連続欠損は前回値で補完（`interpolated=True`）
- **タイムスタンプ照合**: `main.py` 起動を基準とするボタンCSVに合わせ、動画開始オフセットを加算してから許容誤差 0.017秒（約1フレーム）で最近傍マッチング
- **オフセット検出**: easyocr で動画フレームの `index.html` タイムスタンプを読み取り自動算出。旧セッションのタイムスタンプが残るため最初の数フレームは使用せず、値が急落したフレームで検出する
- **距離ログ出力**: 動画ごとに `{動画名}_distance.csv` を別途保存

## CSVのカラム構成

| カラム | 内容 |
|--------|------|
| username | プレイヤー名 |
| Timestamp | `MM:SS.microseconds` 形式（`main.py` 起動からの経過時間） |
| X, Y, B, A, RB, LB, RT, LT | ボタン (0/1) |
| CenterArrow 〜 DownLeftArrow | 十字キー方向 (0/1) |
| Center 〜 DownLeft | アナログスティック方向 (0/1) |
| StateX, StateY | アナログスティック生値 (-32768〜32767) |
| 1P_pos, 2P_pos | キャラクター座標 (calcDistance追記) |
| distance_px | キャラクター間距離px (calcDistance追記) |
| interpolated | 補完フラグ (calcDistance追記) |

## OBS設定

- ブラウザソース名: `ts`（タイムスタンプ表示用、`index.html` を `http://localhost:8080/` で配信）
- 録画停止後、OBSの出力ファイルを自動的にCSVと同名・同ディレクトリに移動

## 依存ライブラリ

```bash
pip install inputs obsws-python opencv-python numpy pandas scikit-learn joblib
pip install easyocr  # オフセット自動検出用（オプション）
```

仮想環境: `.venv/`（`python -m venv .venv` で作成済み）
