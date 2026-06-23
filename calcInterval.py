"""
【オプション】プレイヤーごとの入力間隔カラム追加
==================================
使い方：
  python calcInterval.py <対象ディレクトリのパス>

例：
  python calcInterval.py C:/Users/sat00/Documents/matches

仕組み：
  main.py が出力したボタン入力CSV（username, Timestamp カラムを持つもの）を
  対象ディレクトリから自動検索し、各行に「同じusernameの直前の行からの経過秒」
  を表す interval_sec カラムを追加して上書き保存する。
  各プレイヤーの最初の入力には 0 を入れる。

  *_distance.csv と gamestartandKOtiming.csv は対象外。

注意：
  元のCSVを上書き保存するため、実行前にGitでcommitしておくこと。
"""

import argparse
import glob
import os
import pandas as pd

KO_TIMING_CSV_NAME = "gamestartandKOtiming.csv"


def parse_timestamp(val):
    """Timestamp ( "MM:SS.microseconds" ) を秒（float）に変換する"""
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


def add_interval_column(csv_path):
    df = pd.read_csv(csv_path)

    if "username" not in df.columns:
        print(f"スキップ: 'username' カラムが見つかりません → {csv_path}")
        return
    ts_col = next((c for c in df.columns if c.lower() == "timestamp"), None)
    if ts_col is None:
        print(f"スキップ: 'Timestamp' カラムが見つかりません → {csv_path}")
        return

    ts_sec = df[ts_col].apply(parse_timestamp)

    last_time = {}
    intervals = []
    for username, t in zip(df["username"], ts_sec):
        if username in last_time and not pd.isna(t) and not pd.isna(last_time[username]):
            intervals.append(round(t - last_time[username], 6))
        else:
            intervals.append(0.0)
        last_time[username] = t

    df["interval_sec"] = intervals
    df.to_csv(csv_path, index=False)
    print(f"  完了 → {os.path.basename(csv_path)} ({len(df)} 行)")


def main():
    parser = argparse.ArgumentParser(
        description="プレイヤーごとの入力間隔（interval_sec）カラムを追加")
    parser.add_argument("target_dir", help="対象ディレクトリのパス")
    args = parser.parse_args()

    target_dir = args.target_dir
    if not os.path.isdir(target_dir):
        print(f"エラー: ディレクトリが見つかりません → {target_dir}")
        return

    csv_files = [
        f for f in glob.glob(os.path.join(target_dir, "*.csv"))
        if not f.endswith("_distance.csv")
        and os.path.basename(f) != KO_TIMING_CSV_NAME
    ]

    if not csv_files:
        print("処理対象のCSVが見つかりませんでした。")
        return

    print(f"{len(csv_files)} 件のCSVを処理します。")
    for csv_path in csv_files:
        add_interval_column(csv_path)

    print("\n全ての処理が完了しました！")


if __name__ == "__main__":
    main()
