"""
ネガティブサンプルのみ再抽出。
MIN_DIST_NEG=3.0s, NEG_PER_MATCH=60 で再取得し、
既存の extraction_summary.csv のネガティブ行を置き換える。
"""

import random
from pathlib import Path

import cv2
import pandas as pd

random.seed(42)

BASE_DIR    = Path(__file__).resolve().parent.parent
VIDEO_DIR   = BASE_DIR / "2026_05_13対戦動画"
OUT_CLIPS   = BASE_DIR / "data" / "clips"
EVENTS_CSV  = BASE_DIR / "data" / "command_events.csv"
SUMMARY_CSV = OUT_CLIPS / "extraction_summary.csv"

FRAME_W, FRAME_H = 640, 360
NEG_PER_MATCH  = 60
MIN_DIST_NEG   = 3.0


def read_frame(cap, t_sec):
    cap.set(cv2.CAP_PROP_POS_MSEC, t_sec * 1000)
    ret, frame = cap.read()
    if not ret or frame is None:
        return None
    return cv2.resize(frame, (FRAME_W, FRAME_H))


def main():
    events = pd.read_csv(EVENTS_CSV)
    neg_dir = OUT_CLIPS / "negative"
    neg_dir.mkdir(parents=True, exist_ok=True)

    # 既存の negative ファイルを削除
    existing = list(neg_dir.glob("*.jpg"))
    print(f"Removing {len(existing)} existing negative frames...")
    for f in existing:
        f.unlink()

    new_rows = []
    total_saved = 0

    for src, grp in events.groupby("source_file"):
        mp4 = VIDEO_DIR / f"{src}.mp4"
        if not mp4.exists():
            print(f"  MISSING: {mp4.name}")
            continue

        event_times = grp["timestamp_sec"].tolist()
        cap = cv2.VideoCapture(str(mp4))
        vid_dur = cap.get(cv2.CAP_PROP_FRAME_COUNT) / max(cap.get(cv2.CAP_PROP_FPS), 1)

        # 候補時刻: 2s 間隔で、全イベントから MIN_DIST_NEG 秒以上離れた点
        candidates = []
        t = 2.0
        while t < vid_dur - 2.0:
            if all(abs(t - et) >= MIN_DIST_NEG for et in event_times):
                candidates.append(t)
            t += 2.0

        sampled = random.sample(candidates, min(NEG_PER_MATCH, len(candidates)))
        saved = 0
        for t_neg in sampled:
            frame = read_frame(cap, t_neg)
            if frame is None:
                continue
            fname = neg_dir / f"{src}_{t_neg:.3f}_+0.00.jpg"
            cv2.imwrite(str(fname), frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            new_rows.append({
                "path": str(fname),
                "label": "negative",
                "source_file": src,
                "username": "",
                "event_ts": None,
            })
            saved += 1
        cap.release()
        total_saved += saved
        print(f"  {src}: {saved} negative frames (candidates={len(candidates)})")

    print(f"\nTotal negative frames: {total_saved}")

    # summary CSV の negative 行を置き換える
    if SUMMARY_CSV.exists():
        df_old = pd.read_csv(SUMMARY_CSV)
        df_pos = df_old[df_old["label"] != "negative"]
    else:
        df_pos = pd.DataFrame()

    df_neg_new = pd.DataFrame(new_rows)
    df_updated = pd.concat([df_pos, df_neg_new], ignore_index=True)
    df_updated.to_csv(SUMMARY_CSV, index=False, encoding="utf-8")

    print("\n=== Updated label distribution ===")
    print(df_updated.groupby("label")["path"].count().rename("frames").to_string())
    print(f"\nSummary CSV updated: {SUMMARY_CSV}")


if __name__ == "__main__":
    main()
