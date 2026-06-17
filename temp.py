"""
【ステップ2】キャラクター距離計算 → ボタン入力CSVに追記
==================================
使い方：
  python step2_calc_distance.py 対象ディレクトリのパス

例：
  python step2_calc_distance.py C:/Users/sat00/Documents/matches

仕組み：
  指定ディレクトリ内の .mp4 ファイルと同名の .csv ファイルを自動検索し、
  動画から距離・座標を計算してボタン入力CSVに追記して上書き保存する。

追加されるカラム：
  1P_pos, 2P_pos, distance_px, interpolated

注意：
  元のCSVを上書き保存するため、実行前にGitでcommitしておくこと。
"""

import cv2
import numpy as np
import pandas as pd
import sys
import os

# ============================================================
# HSV設定値（frame.pngから計算済み）
# ------------------------------------------------------------
# リュウ（白い道着）
RYU_LOWER = np.array([15,  0,   180])
RYU_UPPER = np.array([45,  55,  255])

# ケン（青緑がかった道着）
KEN_LOWER = np.array([85,  50,  40])
KEN_UPPER = np.array([115, 210, 110])

# UIを除いた対戦エリアのY座標範囲（1920x1080想定）
ROI_Y_START = 200
ROI_Y_END   = 950

# 誤検出除去：この面積より小さい塊は無視
MIN_AREA = 800

# 紐付け許容誤差（秒）
# 60fps = 1フレーム約0.0167秒のため1フレーム分を許容誤差とする
TIME_TOLERANCE = 0.017

# 欠損補完の閾値（フレーム数）
# この値以下の連続欠損 → 前回値で補完（interpolated=True）
# この値を超える連続欠損 → ギャップ状態へ移行（KO演出・待機画面とみなす）
INTERPOLATE_MAX_FRAMES = 10

# ギャップ状態から対戦中に復帰するために必要な連続検出フレーム数
# KO画面中の散発的な誤検出（色がたまたまヒット）がこの閾値を超えることは稀
RESUME_DETECT_STREAK = 5
# ============================================================


def parse_timestamp(val):
    """
    Timestamp を秒（float）に変換する。元のカラムは書き換えない。
    対応フォーマット：
      "00:09.207534" （分:秒.マイクロ秒）→ 9.207534秒
      数値文字列 "3.167" → そのまま数値に変換
    """
    if pd.isna(val):
        return float("nan")
    val = str(val).strip()
    if ":" in val:
        try:
            parts = val.split(":")
            return float(parts[0]) * 60 + float(parts[1])
        except Exception:
            return float("nan")
    try:
        return float(val)
    except Exception:
        return float("nan")


def get_center(mask):
    """マスク画像から一番大きい塊の中心座標を返す"""
    contours, _ = cv2.findContours(
        mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    biggest = max(contours, key=cv2.contourArea)
    if cv2.contourArea(biggest) < MIN_AREA:
        return None
    x, y, w, h = cv2.boundingRect(biggest)
    return (x + w // 2, y + h // 2)


def extract_distance_log(video_path):
    """動画から距離ログをDataFrameとして返す"""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"  エラー: 動画を開けませんでした → {video_path}")
        return None

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps          = cap.get(cv2.CAP_PROP_FPS)
    print(f"  動画情報: {total_frames}フレーム / {fps:.1f}fps")

    records = []
    frame_no = 0
    missing_count = 0
    consecutive_detect = 0  # 連続検出フレーム数（ギャップ復帰判定用）
    in_gap = False           # True = KO演出などの非対戦状態
    kernel = np.ones((5, 5), np.uint8)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame_no += 1
        roi = frame[ROI_Y_START:ROI_Y_END, :]
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

        ryu_mask = cv2.morphologyEx(
            cv2.inRange(hsv, RYU_LOWER, RYU_UPPER), cv2.MORPH_OPEN, kernel)
        ken_mask = cv2.morphologyEx(
            cv2.inRange(hsv, KEN_LOWER, KEN_UPPER), cv2.MORPH_OPEN, kernel)

        ryu_roi = get_center(ryu_mask)
        ken_roi = get_center(ken_mask)

        ryu_center = (ryu_roi[0], ryu_roi[1] + ROI_Y_START) if ryu_roi else None
        ken_center = (ken_roi[0], ken_roi[1] + ROI_Y_START) if ken_roi else None

        time_sec = round(frame_no / fps, 3)

        if ryu_center and ken_center:
            consecutive_detect += 1

            if not in_gap or consecutive_detect >= RESUME_DETECT_STREAK:
                # 通常の対戦中、またはギャップから復帰できるだけ連続検出が続いた
                in_gap = False
                missing_count = 0
                distance = float(np.linalg.norm(
                    np.array(ryu_center) - np.array(ken_center)))
                records.append({
                    "time_sec":     time_sec,
                    "1P_pos":       f"({ryu_center[0]}, {ryu_center[1]})",
                    "2P_pos":       f"({ken_center[0]}, {ken_center[1]})",
                    "distance_px":  round(distance, 1),
                    "interpolated": False,
                })
            else:
                # ギャップ中の散発的な検出 → 復帰条件未達のためNaNとして記録
                records.append({
                    "time_sec":     time_sec,
                    "1P_pos":       None,
                    "2P_pos":       None,
                    "distance_px":  None,
                    "interpolated": None,
                })
        elif records:
            consecutive_detect = 0
            missing_count += 1
            if missing_count <= INTERPOLATE_MAX_FRAMES and not in_gap:
                # 閾値以内 → 前回値で補完
                prev = records[-1].copy()
                prev["time_sec"]     = time_sec
                prev["interpolated"] = True
                records.append(prev)
            else:
                # 閾値超え → ギャップ状態へ移行（KO演出・待機画面とみなす）
                in_gap = True
                records.append({
                    "time_sec":     time_sec,
                    "1P_pos":       None,
                    "2P_pos":       None,
                    "distance_px":  None,
                    "interpolated": None,
                })
        # 両キャラ未検出かつrecordsが空（待機画面）は記録しない

        if frame_no % 100 == 0:
            print(f"  {frame_no} / {total_frames} フレーム処理済み")

    cap.release()
    return pd.DataFrame(records)


def process(video_path, csv_path):
    """動画から距離を計算してボタン入力CSVに追記・上書き保存する"""
    print(f"\n処理中: {os.path.basename(video_path)}")

    # ボタン入力CSVを読み込む
    # ボタンカラムはNaN混在でもfloatに変換されないようInt64（nullable整数）で読む
    BUTTON_COLS = [
        "X", "Y", "B", "A", "RB", "LB", "RT", "LT",
        "RStick", "LStick", "SELECT", "START",
        "CenterArrow", "UpArrow", "DownArrow", "LeftArrow", "RightArrow",
        "UpRightArrow", "UpLeftArrow", "DownRightArrow", "DownLeftArrow",
        "Center", "Up", "Down", "Right", "Left",
        "UpRight", "UpLeft", "DownRight", "DownLeft",
    ]
    try:
        input_df = pd.read_csv(csv_path, dtype={col: "Int64" for col in BUTTON_COLS})
    except Exception as e:
        print(f"  エラー: CSVを読み込めませんでした → {e}")
        return

    # Timestampカラムを探す（大文字小文字を吸収）
    ts_col = next((c for c in input_df.columns if c.lower() == "timestamp"), None)
    if ts_col is None:
        print(f"  エラー: 'Timestamp' カラムが見つかりません → {csv_path}")
        return

    # 照合用の秒数を一時カラムに作成（元のTimestampカラムは変更しない）
    ts_sec = input_df[ts_col].apply(parse_timestamp).values

    # 動画から距離ログを取得
    dist_df = extract_distance_log(video_path)
    if dist_df is None or dist_df.empty:
        print(f"  エラー: 距離データの取得に失敗しました")
        return

    # 全検出結果を新規CSVとして保存
    video_stem = os.path.splitext(os.path.basename(video_path))[0]
    dist_csv_path = os.path.join(os.path.dirname(video_path), f"{video_stem}_distance.csv")
    dist_df.to_csv(dist_csv_path, index=False)
    print(f"  距離ログ保存 → {os.path.basename(dist_csv_path)} ({len(dist_df)} 行)")

    dist_time = dist_df["time_sec"].values

    # 追加カラムを初期化（空欄）
    add_cols = ["1P_pos", "2P_pos", "distance_px", "interpolated"]
    for col in add_cols:
        input_df[col] = None

    # numpy を使って高速に最近傍マッチング
    for i, ts in enumerate(ts_sec):
        if np.isnan(ts):
            continue

        # 最も近いフレームのインデックスを取得
        nearest_idx = int(np.argmin(np.abs(dist_time - ts)))

        # 許容誤差チェック
        if abs(dist_time[nearest_idx] - ts) <= TIME_TOLERANCE:
            nearest_row = dist_df.iloc[nearest_idx]
            for col in add_cols:
                input_df.at[i, col] = nearest_row[col]
        # 許容誤差外は空欄のまま

    # 上書き保存（元のTimestampカラムはそのまま保持）
    input_df.to_csv(csv_path, index=False)
    matched = input_df["distance_px"].notna().sum()
    total   = len(input_df)
    print(f"  完了！ → {os.path.basename(csv_path)} を上書き保存しました")
    print(f"  紐付け成功: {matched} / {total} 行")


def main():
    if len(sys.argv) < 2:
        print("使い方: python step2_calc_distance.py 対象ディレクトリのパス")
        sys.exit(1)

    target_dir = sys.argv[1]

    if not os.path.isdir(target_dir):
        print(f"エラー: ディレクトリが見つかりません → {target_dir}")
        sys.exit(1)

    # 同名の .mp4 と .csv のペアを探す
    mp4_files = [f for f in os.listdir(target_dir) if f.endswith(".mp4")]
    pairs = []
    for mp4 in mp4_files:
        name     = os.path.splitext(mp4)[0]
        csv_name = name + ".csv"
        csv_full = os.path.join(target_dir, csv_name)
        if os.path.exists(csv_full):
            pairs.append((os.path.join(target_dir, mp4), csv_full))
        else:
            print(f"スキップ: {mp4} に対応するCSVが見つかりません（{csv_name}）")

    if not pairs:
        print("処理対象のペアが見つかりませんでした。")
        sys.exit(1)

    print(f"{len(pairs)} ペアを処理します。")
    for video_path, csv_path in pairs:
        process(video_path, csv_path)

    print("\n全ての処理が完了しました！")


if __name__ == "__main__":
    main()
