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

import argparse
import cv2
import numpy as np
import pandas as pd
import sys
import os

# ============================================================
# HSV設定値（frame.pngから計算済み）
#cv2で使う時はHSVの色相は（0,0,0）から（180,255,255）で表すことに注意
# ------------------------------------------------------------
# リュウ（白い道着）
RYU_LOWER = np.array([15,  0,   180])
RYU_UPPER = np.array([45,  55,  255])

# ケン（紫がかった道着）
KEN_LOWER = np.array([130, 200, 130])
KEN_UPPER = np.array([150, 255, 255])

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
# この値を超える連続欠損 → Noneのまま記録（戦闘中か否かはgamestartandKOtiming.csvで判定）
INTERPOLATE_MAX_FRAMES = 10

# 試合開始・KOタイミングを記録したCSVのファイル名（target_dir内を探す）
KO_TIMING_CSV_NAME = "gamestartandKOtiming.csv"
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


def load_match_info(timing_csv_path):
    """gamestartandKOtiming.csv を読み込み、{filename: {...}} を返す。

    各試合の情報：
      windows         : 戦闘区間 [(start_sec, end_sec), ...]
                        [gamestarttime, KOstart1), [KOend1, KOstart2), [KOend2, KOstart3) の順に
                        構築し、対応する開始値（KOstartN）がNaNになった時点で打ち切る
                        （KOendが無いのは、そのKOで試合が終了したことを意味する）
      offset_timestamp: 動画開始オフセット検出用、drop地点フレームのoverlayタイムスタンプ（秒）
      offset_frame    : drop地点フレームの番号（動画の最初のフレームを1とした連番）
    """
    timing_df = pd.read_csv(timing_csv_path)
    info_by_file = {}
    ko_start_cols = ["KOstart1", "KOstart2", "KOstart3"]
    ko_end_cols   = ["KOend1", "KOend2"]

    for _, row in timing_df.iterrows():
        windows = []
        start = parse_timestamp(row["gamestarttime"])
        for i, start_col in enumerate(ko_start_cols):
            ko_start = parse_timestamp(row[start_col])
            if np.isnan(ko_start):
                break
            windows.append((start, ko_start))
            if i >= len(ko_end_cols):
                break
            ko_end = parse_timestamp(row[ko_end_cols[i]])
            if np.isnan(ko_end):
                break
            start = ko_end

        info_by_file[row["filename"]] = {
            "windows":          windows,
            "offset_timestamp": parse_timestamp(row["offset_timestamp"]),
            "offset_frame":     float(row["offset_frame"]),
        }

    return info_by_file


def in_combat_windows(t, windows):
    """秒(t)がいずれかの戦闘区間 [start, end) に含まれるか判定する"""
    return any(start <= t < end for start, end in windows)


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
    """動画から距離ログをDataFrameとして返す。戻り値は (DataFrame, fps)。"""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"  エラー: 動画を開けませんでした → {video_path}")
        return None, None

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps          = cap.get(cv2.CAP_PROP_FPS)
    print(f"  動画情報: {total_frames}フレーム / {fps:.1f}fps")

    records = []
    frame_no = 0
    missing_count = 0
    kernel = np.ones((5, 5), np.uint8)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame_no += 1
        time_sec = round(frame_no / fps, 3)

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

        if ryu_center and ken_center:
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
        elif records:
            missing_count += 1
            if missing_count <= INTERPOLATE_MAX_FRAMES:
                # 閾値以内 → 前回値で補完
                prev = records[-1].copy()
                prev["time_sec"]     = time_sec
                prev["interpolated"] = True
                records.append(prev)
            else:
                # 閾値超え → Noneのまま記録
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
    return pd.DataFrame(records), fps


def process(video_path, csv_path, match_info):
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
    dist_df, fps = extract_distance_log(video_path)
    if dist_df is None or dist_df.empty:
        print(f"  エラー: 距離データの取得に失敗しました")
        return

    # 全検出結果を新規CSVとして保存
    video_stem = os.path.splitext(os.path.basename(video_path))[0]
    dist_csv_path = os.path.join(os.path.dirname(video_path), f"{video_stem}_distance.csv")
    dist_df.to_csv(dist_csv_path, index=False)
    print(f"  距離ログ保存 → {os.path.basename(dist_csv_path)} ({len(dist_df)} 行)")

    # 動画開始オフセット（秒）を計算: drop地点のoverlayタイムスタンプから
    # drop地点フレームの動画内経過時間（offset_frame ÷ fps）を引き、
    # 動画フレーム時間とボタンCSV基準時間の差分を求める
    video_offset = match_info["offset_timestamp"] - match_info["offset_frame"] / fps
    print(f"  動画開始オフセット: {video_offset:.3f}秒"
          f"（drop地点: {match_info['offset_timestamp']:.3f}秒 / "
          f"{match_info['offset_frame']:.0f}フレーム目, fps={fps:.1f}）")

    dist_time = dist_df["time_sec"].values + video_offset

    # 追加カラムを初期化（空欄）
    add_cols = ["1P_pos", "2P_pos", "distance_px", "interpolated"]
    for col in add_cols:
        input_df[col] = None

    # numpy を使って高速に最近傍マッチング
    for i, ts in enumerate(ts_sec):
        if np.isnan(ts):
            continue

        # 戦闘区間外（KO演出・待機画面）は記録しない
        if not in_combat_windows(ts, match_info["windows"]):
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
    parser = argparse.ArgumentParser(
        description="動画から距離を計算してボタン入力CSVに追記")
    parser.add_argument("target_dir", help="対象ディレクトリのパス")
    args = parser.parse_args()

    target_dir = args.target_dir

    if not os.path.isdir(target_dir):
        print(f"エラー: ディレクトリが見つかりません → {target_dir}")
        sys.exit(1)

    # 試合開始・KOタイミングCSVを読み込む
    timing_csv_path = os.path.join(target_dir, KO_TIMING_CSV_NAME)
    if not os.path.exists(timing_csv_path):
        print(f"エラー: {KO_TIMING_CSV_NAME} が見つかりません → {timing_csv_path}")
        sys.exit(1)
    match_info_by_file = load_match_info(timing_csv_path)

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
        name = os.path.splitext(os.path.basename(video_path))[0]
        if name not in match_info_by_file:
            print(f"スキップ: {name} は {KO_TIMING_CSV_NAME} に記録がありません")
            continue
        process(video_path, csv_path, match_info_by_file[name])

    print("\n全ての処理が完了しました！")


if __name__ == "__main__":
    main()
