"""
Phase 1: 動画特徴量抽出
対戦動画からキャラ間距離・波動拳・昇竜拳フラグを抽出してCSVキャッシュに保存する。

使用方法:
    python video_analyzer.py                  # 全動画を処理
    python video_analyzer.py --force          # キャッシュ無視して再処理
    python video_analyzer.py --debug-frames   # 50フレームごとにPNG保存（HSV調整用）
"""

import argparse
import math
from collections import deque
from pathlib import Path

import cv2
import numpy as np
import pandas as pd

# ---- パス定義 ----------------------------------------------------------------
BASE_DIR  = Path(__file__).parent.parent          # 20260513/
VIDEO_DIR = BASE_DIR / "2026_05_13対戦動画"
CACHE_DIR = Path(__file__).parent / "video_cache"

# ---- HSV閾値（OpenCV: H 0-179, S 0-255, V 0-255）---------------------------
RYU_HSV_LOWER  = np.array([0,   0,   180], dtype=np.uint8)  # 白道着
RYU_HSV_UPPER  = np.array([179, 50,  255], dtype=np.uint8)

# ケンは紫道着（Capcom Arcade Stadium / SF2）赤ではない
KEN_HSV_LOWER  = np.array([125, 60,  60],  dtype=np.uint8)
KEN_HSV_UPPER  = np.array([155, 255, 220], dtype=np.uint8)

# 波動拳: H:95-120（ケン紫胴着H:128-134を除外）, S>=150・V>=150（暗い背景・低彩度城を除外）
HADOUKEN_HSV_LOWER = np.array([95,  150, 150], dtype=np.uint8)
HADOUKEN_HSV_UPPER = np.array([120, 255, 255], dtype=np.uint8)

# ---- 検出パラメータ -----------------------------------------------------------
SAMPLE_FPS          = 5     # 動画サンプリングレート
MIN_CHAR_AREA       = 800   # キャラ認識の最小面積（px²）
HADOUKEN_MIN_AREA   = 800   # 波動拳認識の最小面積（px²）; 小さい背景断片を除外
HADOUKEN_MAX_AREA   = 8000  # 波動拳認識の最大面積（px²）; 背景の大きな青領域を除外
SHORYUKEN_DELTA_Y   = -30   # 昇竜拳判定の上方向変位閾値（px/frame）
SHORYUKEN_WINDOW    = 3     # 昇竜拳判定のフレーム数
MORPH_KERNEL        = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
ROI_TOP_RATIO       = 0.20  # ROI上端（フレーム高さ比）
ROI_BOTTOM_RATIO    = 0.90  # ROI下端（フレーム高さ比）


class VideoFeatureExtractor:
    def __init__(
        self,
        video_dir: Path = VIDEO_DIR,
        cache_dir: Path = CACHE_DIR,
        sample_fps: int = SAMPLE_FPS,
        force_reprocess: bool = False,
        debug_frames: bool = False,
    ):
        self.video_dir       = video_dir
        self.cache_dir       = cache_dir
        self.sample_fps      = sample_fps
        self.force_reprocess = force_reprocess
        self.debug_frames    = debug_frames
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 公開メソッド
    # ------------------------------------------------------------------

    def process_all(self) -> dict[str, Path]:
        """全MP4ファイルを処理。キャッシュ済みはスキップ（force_reprocess=Trueで強制再処理）。"""
        if not self.video_dir.exists():
            print(f"[ERROR] 動画ディレクトリが見つかりません: {self.video_dir}")
            return {}

        mp4_files = sorted(self.video_dir.glob("*.mp4"))
        if not mp4_files:
            print(f"[WARN] MP4ファイルが見つかりません: {self.video_dir}")
            return {}

        results: dict[str, Path] = {}
        for mp4_path in mp4_files:
            cache_path = self._cache_path(mp4_path.stem)
            if not self.force_reprocess and cache_path.exists():
                print(f"[SKIP] キャッシュ済み: {mp4_path.name}")
                results[mp4_path.stem] = cache_path
                continue
            try:
                results[mp4_path.stem] = self.process_video(mp4_path)
            except Exception as e:
                print(f"[ERROR] {mp4_path.name}: {e}")

        print(f"\n処理完了: {len(results)}/{len(mp4_files)} ファイル")
        return results

    def process_video(self, video_path: Path) -> Path:
        """単一MP4から特徴量を抽出してキャッシュCSVを書き出す。"""
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise IOError(f"動画を開けません: {video_path}")

        print(f"[INFO] 処理中: {video_path.name}")
        records: list[dict] = []
        ryu_history: deque = deque(maxlen=SHORYUKEN_WINDOW)
        ken_history: deque = deque(maxlen=SHORYUKEN_WINDOW)
        frame_idx = 0

        try:
            for timestamp_sec, frame in self._extract_frames(cap):
                ryu_c, ken_c = self._detect_characters(frame)
                hadouken     = self._detect_hadouken(frame, ryu_c, ken_c)
                ryu_history.append(ryu_c[1] if ryu_c else None)
                ken_history.append(ken_c[1] if ken_c else None)
                shoryuken    = self._detect_shoryuken(ryu_history) or self._detect_shoryuken(ken_history)
                distance     = self._compute_char_distance(ryu_c, ken_c)

                records.append({
                    "timestamp_sec":    round(timestamp_sec, 6),
                    "char_distance_px": round(distance, 2),
                    "hadouken_flag":    hadouken,
                    "shoryuken_flag":   shoryuken,
                })

                if self.debug_frames and frame_idx % 50 == 0:
                    debug_path = self.cache_dir / f"debug_{video_path.stem}_{frame_idx:04d}.png"
                    cv2.imwrite(str(debug_path), frame)

                frame_idx += 1
        finally:
            cap.release()

        df = pd.DataFrame(records)
        cache_path = self._cache_path(video_path.stem)
        df.to_csv(cache_path, index=False)
        print(f"[INFO] キャッシュ保存: {cache_path.name} ({len(df)} フレーム)")
        return cache_path

    # ------------------------------------------------------------------
    # フレーム抽出
    # ------------------------------------------------------------------

    def _extract_frames(self, cap: cv2.VideoCapture):
        """指定サンプリングレートでフレームを (timestamp_sec, frame_bgr) としてyieldする。"""
        native_fps   = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        duration_ms  = (total_frames / native_fps) * 1000.0
        interval_ms  = 1000.0 / self.sample_fps
        current_ms   = 0.0

        while current_ms < duration_ms:
            cap.set(cv2.CAP_PROP_POS_MSEC, current_ms)
            ret, frame = cap.read()
            if not ret:
                break
            yield current_ms / 1000.0, frame
            current_ms += interval_ms

    # ------------------------------------------------------------------
    # 検出メソッド
    # ------------------------------------------------------------------

    def _get_roi(self, frame: np.ndarray) -> tuple[np.ndarray, int]:
        """HUD・背景ノイズを除くためフレーム縦方向をROIトリミングする。上端offset(px)も返す。"""
        h = frame.shape[0]
        top    = int(h * ROI_TOP_RATIO)
        bottom = int(h * ROI_BOTTOM_RATIO)
        return frame[top:bottom, :], top

    def _largest_centroid(self, mask: np.ndarray, y_offset: int, min_area: int):
        """マスクから最大輪郭の重心を返す。面積が min_area 未満なら None。"""
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None
        largest = max(contours, key=cv2.contourArea)
        if cv2.contourArea(largest) < min_area:
            return None
        M = cv2.moments(largest)
        if M["m00"] == 0:
            return None
        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"]) + y_offset
        return (cx, cy)

    def _detect_characters(
        self, frame_bgr: np.ndarray
    ) -> tuple[tuple[int, int] | None, tuple[int, int] | None]:
        """リュウ(白)とケン(赤)の重心を検出する。"""
        roi, y_offset = self._get_roi(frame_bgr)
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

        # リュウ（白道着）
        ryu_mask = cv2.inRange(hsv, RYU_HSV_LOWER, RYU_HSV_UPPER)
        ryu_mask = cv2.morphologyEx(ryu_mask, cv2.MORPH_OPEN, MORPH_KERNEL)
        ryu_c    = self._largest_centroid(ryu_mask, y_offset, MIN_CHAR_AREA)

        # ケン（紫道着）
        ken_mask = cv2.inRange(hsv, KEN_HSV_LOWER, KEN_HSV_UPPER)
        ken_mask = cv2.morphologyEx(ken_mask, cv2.MORPH_OPEN, MORPH_KERNEL)
        ken_c     = self._largest_centroid(ken_mask, y_offset, MIN_CHAR_AREA)

        return ryu_c, ken_c

    def _detect_hadouken(
        self,
        frame_bgr: np.ndarray,
        ryu_centroid: tuple[int, int] | None,
        ken_centroid: tuple[int, int] | None,
    ) -> int:
        """青エネルギーボール（波動拳）を検出する。キャラbboxと重複する場合は除外。"""
        roi, y_offset = self._get_roi(frame_bgr)
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

        mask = cv2.inRange(hsv, HADOUKEN_HSV_LOWER, HADOUKEN_HSV_UPPER)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, MORPH_KERNEL)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < HADOUKEN_MIN_AREA or area > HADOUKEN_MAX_AREA:
                continue
            x, y, w, h = cv2.boundingRect(cnt)
            cx = x + w // 2 + 0       # ROI座標のまま比較
            cy = y + h // 2 + y_offset

            # キャラ重心と重複しない（それぞれ50px以上離れている）場合のみカウント
            overlap = False
            for char_c in [ryu_centroid, ken_centroid]:
                if char_c is not None:
                    dist = math.hypot(cx - char_c[0], cy - char_c[1])
                    if dist < 50:
                        overlap = True
                        break
            if not overlap:
                return 1
        return 0

    def _detect_shoryuken(
        self,
        history: deque,
        window: int = SHORYUKEN_WINDOW,
        threshold: int = SHORYUKEN_DELTA_Y,
    ) -> int:
        """直近 window フレームの重心Y座標が連続して threshold 以上上昇していれば 1。"""
        if len(history) < window:
            return 0
        positions = list(history)
        if any(p is None for p in positions):
            return 0
        deltas = [positions[i + 1] - positions[i] for i in range(len(positions) - 1)]
        return 1 if all(d < threshold for d in deltas) else 0

    def _compute_char_distance(
        self,
        c1: tuple[int, int] | None,
        c2: tuple[int, int] | None,
    ) -> float:
        """2重心間のユークリッド距離（px）。どちらかがNoneなら0.0。"""
        if c1 is None or c2 is None:
            return 0.0
        return math.hypot(c1[0] - c2[0], c1[1] - c2[1])

    def _cache_path(self, stem: str) -> Path:
        return self.cache_dir / f"{stem}_features.csv"


# ---- CLI エントリポイント ----------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="動画特徴量抽出 (Phase 1)")
    parser.add_argument("--force",        action="store_true", help="キャッシュ無視して再処理")
    parser.add_argument("--debug-frames", action="store_true", help="50フレームごとにPNG保存")
    parser.add_argument("--video",        type=str, default=None, help="単一動画ファイル名を指定")
    args = parser.parse_args()

    extractor = VideoFeatureExtractor(
        force_reprocess=args.force,
        debug_frames=args.debug_frames,
    )

    if args.video:
        video_path = VIDEO_DIR / args.video
        if not video_path.exists():
            print(f"[ERROR] ファイルが見つかりません: {video_path}")
            return
        extractor.process_video(video_path)
    else:
        extractor.process_all()


if __name__ == "__main__":
    main()
