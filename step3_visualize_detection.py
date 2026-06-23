"""
【ステップ3】検出結果の可視化（目視チェック用）
==================================
使い方：
  python step3_visualize_detection.py 対象ディレクトリのパス

例：
  python step3_visualize_detection.py C:/Users/sat00/Documents/matches

仕組み：
  指定ディレクトリ内の .mp4 ファイルを全て処理する。
  各フレームをモノクロ化し、検出した塊（バウンディボックス）と
  中心点を色付きでマークした動画を出力する。

  リュウ → 赤枠 + 赤い中心点
  ケン   → 青枠 + 青い中心点

  例）match001.mp4 を処理すると
      match001_detection_check.mp4 を同じディレクトリに出力する。

  ※元動画ファイルは上書きしない（新しいファイルとして出力する）

注意：
  HSV設定値・ROI・MIN_AREAは step2_calc_distance.py と同じものを使用。
  設定を変えたらこのファイルも合わせて変更すること。
"""

import cv2
import numpy as np
import sys
import os

# ============================================================
# HSV設定値（step2_calc_distance.py と同じ値）
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

# 描画設定
RYU_COLOR = (0,   0,   255)  # 赤（BGR形式）
KEN_COLOR = (255, 0,   0)    # 青（BGR形式）
BOX_THICKNESS    = 2
CENTER_RADIUS    = 6
OUTPUT_SUFFIX    = "_detection_check"
# ============================================================


def get_contour_info(mask):
    """マスク画像から一番大きい塊の(バウンディボックス, 中心座標)を返す"""
    contours, _ = cv2.findContours(
        mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    biggest = max(contours, key=cv2.contourArea)
    if cv2.contourArea(biggest) < MIN_AREA:
        return None
    x, y, w, h = cv2.boundingRect(biggest)
    center = (x + w // 2, y + h // 2)
    return (x, y, w, h, center)


def process_video(video_path):
    """1本の動画を処理して検出確認用動画を出力する"""
    print(f"\n処理中: {os.path.basename(video_path)}")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"  エラー: 動画を開けませんでした → {video_path}")
        return

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps          = cap.get(cv2.CAP_PROP_FPS)
    width        = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height       = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"  動画情報: {total_frames}フレーム / {fps:.1f}fps / {width}x{height}")

    # 出力ファイルパスを組み立てる
    base_dir  = os.path.dirname(video_path)
    name, ext = os.path.splitext(os.path.basename(video_path))
    output_path = os.path.join(base_dir, f"{name}{OUTPUT_SUFFIX}{ext}")

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    if not writer.isOpened():
        print(f"  エラー: 出力動画を作成できませんでした → {output_path}")
        cap.release()
        return

    kernel = np.ones((5, 5), np.uint8)
    frame_no = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame_no += 1

        # モノクロ化（3チャンネルのグレースケールに変換して描画可能にする）
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        output_frame = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

        # 検出処理は元のカラー画像（HSV変換）で行う
        roi = frame[ROI_Y_START:ROI_Y_END, :]
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

        ryu_mask = cv2.morphologyEx(
            cv2.inRange(hsv, RYU_LOWER, RYU_UPPER), cv2.MORPH_OPEN, kernel)
        ken_mask = cv2.morphologyEx(
            cv2.inRange(hsv, KEN_LOWER, KEN_UPPER), cv2.MORPH_OPEN, kernel)

        ryu_info = get_contour_info(ryu_mask)
        ken_info = get_contour_info(ken_mask)

        # リュウの枠と中心点を描く（赤）
        if ryu_info:
            x, y, w, h, (cx, cy) = ryu_info
            # ROI内の座標なのでY座標をオフセットして元画像の座標に戻す
            y_full  = y + ROI_Y_START
            cy_full = cy + ROI_Y_START
            cv2.rectangle(output_frame, (x, y_full), (x + w, y_full + h),
                          RYU_COLOR, BOX_THICKNESS)
            cv2.circle(output_frame, (cx, cy_full), CENTER_RADIUS,
                      RYU_COLOR, -1)
            cv2.putText(output_frame, "RYU", (x, y_full - 8),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, RYU_COLOR, 2)

        # ケンの枠と中心点を描く（青）
        if ken_info:
            x, y, w, h, (cx, cy) = ken_info
            y_full  = y + ROI_Y_START
            cy_full = cy + ROI_Y_START
            cv2.rectangle(output_frame, (x, y_full), (x + w, y_full + h),
                          KEN_COLOR, BOX_THICKNESS)
            cv2.circle(output_frame, (cx, cy_full), CENTER_RADIUS,
                      KEN_COLOR, -1)
            cv2.putText(output_frame, "KEN", (x, y_full - 8),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, KEN_COLOR, 2)

        # 両者検出できていれば距離も表示（目視確認の補助）
        if ryu_info and ken_info:
            distance = float(np.linalg.norm(
                np.array(ryu_info[4]) - np.array(ken_info[4])))
            cv2.putText(output_frame, f"distance: {distance:.1f}px",
                       (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                       (0, 255, 0), 2)

        # ROI範囲も薄く表示（対戦エリアの境界確認用）
        cv2.line(output_frame, (0, ROI_Y_START), (width, ROI_Y_START),
                 (0, 255, 255), 1)
        cv2.line(output_frame, (0, ROI_Y_END), (width, ROI_Y_END),
                 (0, 255, 255), 1)

        writer.write(output_frame)

        if frame_no % 100 == 0:
            print(f"  {frame_no} / {total_frames} フレーム処理済み")

    cap.release()
    writer.release()
    print(f"  完了！ → {os.path.basename(output_path)} を出力しました")


def main():
    if len(sys.argv) < 2:
        print("使い方: python step3_visualize_detection.py 対象ディレクトリのパス")
        sys.exit(1)

    target_dir = sys.argv[1]

    if not os.path.isdir(target_dir):
        print(f"エラー: ディレクトリが見つかりません → {target_dir}")
        sys.exit(1)

    # 対象の.mp4ファイルを探す（既に処理済みの_detection_check動画は除外）
    mp4_files = [
        f for f in os.listdir(target_dir)
        if f.endswith(".mp4") and OUTPUT_SUFFIX not in f
    ]

    if not mp4_files:
        print("処理対象の動画が見つかりませんでした。")
        sys.exit(1)

    print(f"{len(mp4_files)} 本の動画を処理します。")
    for mp4 in mp4_files:
        process_video(os.path.join(target_dir, mp4))

    print("\n全ての処理が完了しました！")


if __name__ == "__main__":
    main()
