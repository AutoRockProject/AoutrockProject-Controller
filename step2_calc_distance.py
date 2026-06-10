"""
【ステップ2】キャラクター距離計算プログラム
==================================
使い方：
  python step2_calc_distance.py 動画ファイル名.mp4

出力：
  distance_log.csv（フレームごとの距離データ）

interpolated列について：
  False = 実際に検出できた実測値
  True  = 検出できなかったため直前の値で補完した値
"""

import cv2
import numpy as np
import csv
import sys

# ============================================================
# HSV設定値（frame.pngから自動計算済み）
# ------------------------------------------------------------
# リュウ（白い道着）
RYU_LOWER = np.array([15,  0,   180])
RYU_UPPER = np.array([45,  55,  255])

# ケン（青緑がかった道着）
KEN_LOWER = np.array([85,  50,  40])
KEN_UPPER = np.array([115, 210, 110])

# UIを除いた対戦エリアのY座標範囲
# 画像サイズが1920x1080なのでそれに合わせた値
ROI_Y_START = 200   # HPバーより下
ROI_Y_END   = 950   # 床より上

# 誤検出除去：この面積より小さい塊は無視（ピクセル数）
MIN_AREA = 800
# ============================================================


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


def main():
    if len(sys.argv) < 2:
        print("使い方: python step2_calc_distance.py 動画ファイル名.mp4")
        sys.exit(1)

    video_path = sys.argv[1]
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        print(f"エラー: 動画を開けませんでした → {video_path}")
        sys.exit(1)

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps          = cap.get(cv2.CAP_PROP_FPS)
    print(f"動画情報: {total_frames}フレーム / {fps:.1f}fps")
    print("処理中...")

    results = []
    frame_no = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame_no += 1

        # ROI（対戦エリアだけ切り出す）
        roi = frame[ROI_Y_START:ROI_Y_END, :]
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

        # 色マスク作成
        ryu_mask = cv2.inRange(hsv, RYU_LOWER, RYU_UPPER)
        ken_mask = cv2.inRange(hsv, KEN_LOWER, KEN_UPPER)

        # ノイズ除去
        kernel = np.ones((5, 5), np.uint8)
        ryu_mask = cv2.morphologyEx(ryu_mask, cv2.MORPH_OPEN, kernel)
        ken_mask = cv2.morphologyEx(ken_mask, cv2.MORPH_OPEN, kernel)

        # 中心座標取得（ROIのオフセットを戻す）
        ryu_roi = get_center(ryu_mask)
        ken_roi = get_center(ken_mask)

        ryu_center = (ryu_roi[0], ryu_roi[1] + ROI_Y_START) if ryu_roi else None
        ken_center = (ken_roi[0], ken_roi[1] + ROI_Y_START) if ken_roi else None

        # 距離計算
        distance = None
        if ryu_center and ken_center:
            distance = float(np.linalg.norm(
                np.array(ryu_center) - np.array(ken_center)))

        # 結果を記録
        if ryu_center and ken_center:
            # 両キャラ検出できた → 実測値として記録
            results.append({
                "frame":        frame_no,
                "time_sec":     round(frame_no / fps, 3),
                "ryu_x":        ryu_center[0],
                "ryu_y":        ryu_center[1],
                "ken_x":        ken_center[0],
                "ken_y":        ken_center[1],
                "distance_px":  round(distance, 1),
                "interpolated": False,
            })
        elif results:
            # 検出できなかった → 直前の値をコピーしてフラグを立てる
            prev = results[-1].copy()
            prev["frame"]        = frame_no
            prev["time_sec"]     = round(frame_no / fps, 3)
            prev["interpolated"] = True
            results.append(prev)
        # resultsが空（対戦開始前）は何も記録しない

        # 進捗表示
        if frame_no % 100 == 0:
            print(f"  {frame_no} / {total_frames} フレーム処理済み")

    cap.release()

    # CSVに書き出し
    output_path = "distance_log.csv"
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["frame", "time_sec",
                      "ryu_x", "ryu_y",
                      "ken_x", "ken_y",
                      "distance_px", "interpolated"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"\n完了！ → {output_path} に保存しました")
    print(f"総フレーム数: {frame_no}")
    real = sum(1 for r in results if not r["interpolated"])
    interp = sum(1 for r in results if r["interpolated"])
    print(f"実測値: {real}フレーム / 補完値: {interp}フレーム")


if __name__ == "__main__":
    main()
