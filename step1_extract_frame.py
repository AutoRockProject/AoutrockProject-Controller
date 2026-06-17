"""
ステップ①：動画から任意フレームを画像として保存するツール
使い方：
    python step1_extract_frame.py
"""

import cv2
import os

# ==========================================
# ここを編集してね
VIDEO_PATH = "sf2.mp4"       # 動画ファイルのパス
OUTPUT_DIR = "frames"        # 保存先フォルダ
# ==========================================


def extract_frame(video_path, output_dir):
    """動画を再生しながら、好きなフレームを保存できるツール"""

    # 保存先フォルダがなければ作成
    os.makedirs(output_dir, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"エラー：動画ファイルが開けません → {video_path}")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps

    print("=" * 50)
    print(f"動画情報")
    print(f"  FPS         : {fps:.1f}")
    print(f"  総フレーム数 : {total_frames}")
    print(f"  再生時間     : {duration:.1f}秒")
    print("=" * 50)
    print("操作方法：")
    print("  スペース → 一時停止 / 再生")
    print("  s       → 今のフレームを保存")
    print("  ←      → 1フレーム戻る")
    print("  →      → 1フレーム進む")
    print("  q       → 終了")
    print("=" * 50)

    saved_count = 0
    paused = False
    frame_idx = 0

    while True:
        if not paused:
            ret, frame = cap.read()
            if not ret:
                print("動画が終わりました")
                break
            frame_idx = int(cap.get(cv2.CAP_PROP_POS_FRAMES))

        # タイムスタンプをフレームに表示
        timestamp = frame_idx / fps
        minutes = int(timestamp // 60)
        seconds = timestamp % 60
        display_frame = frame.copy()
        cv2.putText(
            display_frame,
            f"Frame: {frame_idx}  Time: {minutes:02d}:{seconds:05.2f}  [S]ave [SPACE]pause [Q]uit",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 0),
            2
        )

        cv2.imshow("Frame Extractor - SF2", display_frame)

        key = cv2.waitKey(30 if not paused else 0) & 0xFF

        if key == ord('q'):
            break

        elif key == ord(' '):
            paused = not paused
            print(f"{'一時停止' if paused else '再生'}")

        elif key == ord('s'):
            # フレームを保存
            filename = f"{output_dir}/frame_{frame_idx:06d}_time_{minutes:02d}m{seconds:05.2f}s.png"
            cv2.imwrite(filename, frame)
            saved_count += 1
            print(f"保存しました → {filename}")

        elif key == 81 or key == 2:  # ← キー（Linux/Mac/Windows対応）
            # 1フレーム戻る
            frame_idx = max(0, frame_idx - 2)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if ret:
                frame_idx = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
            paused = True

        elif key == 83 or key == 3:  # → キー
            # 1フレーム進む（pausedのまま次のフレームへ）
            ret, frame = cap.read()
            if ret:
                frame_idx = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
            paused = True

    cap.release()
    cv2.destroyAllWindows()
    print(f"\n完了！{saved_count}枚のフレームを保存しました → {output_dir}/")


if __name__ == "__main__":
    extract_frame(VIDEO_PATH, OUTPUT_DIR)
