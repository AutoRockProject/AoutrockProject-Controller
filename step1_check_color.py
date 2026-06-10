"""
【ステップ1】HSV色確認ツール
==================================
使い方：
  python step1_check_color.py 動画ファイル名.mp4

操作：
  ・画面上でクリック → そのピクセルのHSV値が表示される
  ・'s' キー        → 現在のフレームをframe.pngとして保存
  ・'n' キー        → 次のフレームへ進む
  ・'q' キー        → 終了

目的：
  リュウ（白い道着）とケン（オレンジの道着）の
  HSV値を調べて step2 の LOWER/UPPER に入れる
  
"""

import cv2
import numpy as np
import sys

def on_mouse_click(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        frame_bgr = param["frame"]
        hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
        h, s, v = hsv[y, x]
        print(f"クリック座標 ({x}, {y})  →  HSV: H={h}, S={s}, V={v}")
        print("  ※ LOWER の目安: H-10, S-40, V-40")
        print("  ※ UPPER の目安: H+10, S+40, V+40")
        print("-" * 50)

def main():
    if len(sys.argv) < 2:
        print("使い方: python step1_check_color.py 動画ファイル名.mp4")
        sys.exit(1)

    video_path = sys.argv[1]
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        print(f"エラー: 動画を開けませんでした → {video_path}")
        sys.exit(1)

    param = {"frame": None}
    win_name = "HSV確認ツール  [クリック=HSV表示 / n=次フレーム / s=保存 / q=終了]"
    cv2.namedWindow(win_name)
    cv2.setMouseCallback(win_name, on_mouse_click, param)

    frame_no = 0
    print("=" * 50)
    print("リュウ（白い道着）とケン（オレンジの道着）の色をクリックしてHSV値を確認してください")
    print("=" * 50)

    while True:
        ret, frame = cap.read()
        if not ret:
            print("動画の終端に達しました")
            break

        param["frame"] = frame.copy()
        frame_no += 1

        display = frame.copy()
        cv2.putText(display, f"Frame: {frame_no}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        cv2.imshow(win_name, display)

        key = cv2.waitKey(0) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            cv2.imwrite("frame.png", frame)
            print(f"フレーム {frame_no} を frame.png として保存しました")
        elif key == ord('n'):
            continue

    cap.release()
    cv2.destroyAllWindows()
    print("終了しました")

if __name__ == "__main__":
    main()
