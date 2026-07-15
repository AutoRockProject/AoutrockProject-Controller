"""
コマンドイベント CSV をもとに、動画から学習用フレームを抽出する。

各コマンドイベントに対して:
  - コマンド時刻の -0.5s から +1.5s の範囲を 0.25s 刻み (9 フレーム) で保存
  - 解像度: 640x360 (元の 1/3、ストレージ節約)
  - 保存先: 20260513/data/clips/{command}/{username}/{source_file}_{ts:.3f}_{offset:+.2f}.jpg
  - negative サンプル: コマンドイベントから 10s 以上離れた区間をランダムサンプリング

出力サマリ: 20260513/data/clips/extraction_summary.csv
"""

import argparse
import random
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import cv2
import numpy as np
import pandas as pd

BASE_DIR   = Path(__file__).resolve().parent.parent
VIDEO_DIR  = BASE_DIR / "2026_05_13対戦動画"
FRAME_W, FRAME_H = 640, 360
OFFSETS_SEC = [-0.5, -0.25, 0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5]
NEG_PER_MATCH = 30     # 1試合あたりのネガティブサンプル数
MIN_DIST_NEG   = 10.0  # コマンドイベントから何秒以上離れた区間をネガティブとするか


def read_frame(cap: cv2.VideoCapture, t_sec: float):
    """指定時刻のフレームを読み取る。失敗時は None。"""
    cap.set(cv2.CAP_PROP_POS_MSEC, t_sec * 1000)
    ret, frame = cap.read()
    if not ret or frame is None:
        return None
    return cv2.resize(frame, (FRAME_W, FRAME_H))


def extract_event_frames(row, video_dir: Path, out_base: Path):
    src   = row["source_file"]
    user  = row["username"]
    cmd   = row["command"]
    t_cmd = float(row["timestamp_sec"])

    mp4 = video_dir / f"{src}.mp4"
    if not mp4.exists():
        return [], 0, len(OFFSETS_SEC)

    out_dir = out_base / cmd / user
    out_dir.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(mp4))
    vid_dur = cap.get(cv2.CAP_PROP_FRAME_COUNT) / max(cap.get(cv2.CAP_PROP_FPS), 1)
    saved, skipped = 0, 0
    paths = []
    for offset in OFFSETS_SEC:
        t = t_cmd + offset
        if t < 0 or t > vid_dur:
            skipped += 1
            continue
        frame = read_frame(cap, t)
        if frame is None:
            skipped += 1
            continue
        sign = "+" if offset >= 0 else ""
        fname = out_dir / f"{src}_{t_cmd:.3f}_{sign}{offset:.2f}.jpg"
        cv2.imwrite(str(fname), frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        paths.append(str(fname))
        saved += 1
    cap.release()
    return paths, saved, skipped


def extract_negatives(src: str, event_times: list, video_dir: Path, out_base: Path):
    mp4 = video_dir / f"{src}.mp4"
    if not mp4.exists():
        return [], 0

    cap = cv2.VideoCapture(str(mp4))
    vid_dur = cap.get(cv2.CAP_PROP_FRAME_COUNT) / max(cap.get(cv2.CAP_PROP_FPS), 1)

    # ネガティブサンプル候補: コマンドから MIN_DIST_NEG 秒以上離れた時刻
    candidate_times = []
    step = 2.0
    t = 2.0
    while t < vid_dur - 2.0:
        if all(abs(t - et) >= MIN_DIST_NEG for et in event_times):
            candidate_times.append(t)
        t += step

    if not candidate_times:
        cap.release()
        return [], 0

    sampled = random.sample(candidate_times, min(NEG_PER_MATCH, len(candidate_times)))
    out_dir = out_base / "negative"
    out_dir.mkdir(parents=True, exist_ok=True)

    paths, saved = [], 0
    for t_neg in sampled:
        frame = read_frame(cap, t_neg)
        if frame is None:
            continue
        fname = out_dir / f"{src}_{t_neg:.3f}_+0.00.jpg"
        cv2.imwrite(str(fname), frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        paths.append(str(fname))
        saved += 1
    cap.release()
    return paths, saved


def main(data_dir: Path, video_dir: Path, out_dir: Path, max_workers: int = 4):
    events_csv = data_dir / "command_events.csv"
    events = pd.read_csv(events_csv)
    print(f"Command events: {len(events)}")
    print(events.groupby("command").size().to_string())

    out_clips = out_dir / "clips"
    out_clips.mkdir(parents=True, exist_ok=True)

    summary_rows = []
    total_saved = 0
    total_skip  = 0

    # ── ポジティブサンプル（並列抽出）────────────────────────────────────
    print(f"\n[1/2] Extracting positive frames (workers={max_workers})...")
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        future_map = {
            ex.submit(extract_event_frames, row, video_dir, out_clips): idx
            for idx, row in events.iterrows()
        }
        done = 0
        for future in as_completed(future_map):
            idx = future_map[future]
            row = events.iloc[idx]
            paths, saved, skipped = future.result()
            total_saved += saved
            total_skip  += skipped
            for p in paths:
                summary_rows.append({
                    "path": p,
                    "label": row["command"],
                    "source_file": row["source_file"],
                    "username": row["username"],
                    "event_ts": row["timestamp_sec"],
                })
            done += 1
            if done % 100 == 0:
                print(f"  {done}/{len(events)} events processed...")

    print(f"  Positive frames saved: {total_saved}, skipped: {total_skip}")

    # ── ネガティブサンプル────────────────────────────────────────────────
    print("\n[2/2] Extracting negative frames...")
    neg_saved_total = 0
    for src, grp in events.groupby("source_file"):
        event_times = grp["timestamp_sec"].tolist()
        paths, neg_saved = extract_negatives(src, event_times, video_dir, out_clips)
        neg_saved_total += neg_saved
        for p in paths:
            summary_rows.append({
                "path": p,
                "label": "negative",
                "source_file": src,
                "username": "",
                "event_ts": None,
            })
        print(f"  {src}: {neg_saved} negative frames")

    print(f"  Negative frames saved: {neg_saved_total}")

    # ── サマリ CSV ────────────────────────────────────────────────────────
    df_summary = pd.DataFrame(summary_rows)
    out_summary = out_clips / "extraction_summary.csv"
    df_summary.to_csv(out_summary, index=False, encoding="utf-8")

    print(f"\n=== Extraction Complete ===")
    print(df_summary.groupby("label")["path"].count().rename("frames"))
    print(f"\nSummary CSV: {out_summary}")
    print(f"Output dir:  {out_clips}")


if __name__ == "__main__":
    random.seed(42)
    p = argparse.ArgumentParser()
    p.add_argument("--data-dir",    type=Path, default=BASE_DIR / "data")
    p.add_argument("--video-dir",   type=Path, default=BASE_DIR / "2026_05_13対戦動画")
    p.add_argument("--out-dir",     type=Path, default=BASE_DIR / "data")
    p.add_argument("--max-workers", type=int,  default=4)
    args = p.parse_args()
    main(args.data_dir, args.video_dir, args.out_dir, args.max_workers)
