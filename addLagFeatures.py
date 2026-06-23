"""各行に過去10行分の全カラムをラグ特徴量として追加するスクリプト。

使い方:
    python addLagFeatures.py <対象ディレクトリのパス>

対象ディレクトリ内の `*_1.csv` / `*_2.csv`（distance.csv等を除く）に対して、
各行に prev1_<列名> 〜 prev10_<列名> の列を追加し、上書き保存する。
過去の行が存在しない場合は欠損値(NaN)になる。
"""

import argparse
import glob
import os

import pandas as pd

LAG_COUNT = 10


def is_target_csv(path: str) -> bool:
    name = os.path.basename(path)
    if name.endswith("_distance.csv"):
        return False
    if name == "gamestartandKOtiming.csv":
        return False
    return True


def add_lag_features(df: pd.DataFrame) -> pd.DataFrame:
    lag_frames = []
    for lag in range(1, LAG_COUNT + 1):
        shifted = df.shift(lag)
        shifted.columns = [f"prev{lag}_{col}" for col in df.columns]
        lag_frames.append(shifted)
    return pd.concat([df] + lag_frames, axis=1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("target_dir")
    args = parser.parse_args()

    csv_paths = glob.glob(os.path.join(args.target_dir, "*.csv"))
    for path in csv_paths:
        if not is_target_csv(path):
            continue
        df = pd.read_csv(path)
        result = add_lag_features(df)
        result.to_csv(path, index=False)
        print(f"updated: {path}")


if __name__ == "__main__":
    main()
