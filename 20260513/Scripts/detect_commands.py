"""
コントローラー入力 CSV から昇竜拳(DP)・波動拳(QCF)コマンドを検出する。

昇竜拳 (Dragon Punch / DP):
  向き右: Right  → DownRight → attack  (1.5秒以内)
  向き左: Left   → DownLeft  → attack

波動拳 (Hadouken / QCF):
  向き右: Down → DownRight → Right  → attack
  向き左: Down → DownLeft  → Left   → attack

attack buttons: X, Y, B, A
"""

import argparse
import pandas as pd
from pathlib import Path

ATTACK_BTNS = ["X", "Y", "B", "A"]
LOAD_COLS = [
    "timestamp_sec", "source_file", "username",
    "Right", "Down", "DownRight", "Left", "DownLeft",
    "X", "Y", "B", "A",
]
WINDOW_SEC = 1.5  # コマンド受け付けウィンドウ（秒）
BASE_DIR = Path(__file__).resolve().parent.parent


def _has_seq(times_dict: dict, seq: list, t_attack: float) -> bool:
    """
    t_attack より前の WINDOW_SEC 以内に seq の順序でボタンが押されたかチェック。
    times_dict: {btn: sorted list of timestamps when btn==1}
    seq: [btn1, btn2, ...] の順でチェック
    """
    t_start = t_attack - WINDOW_SEC
    # 最後のボタンは t_attack の直前まで
    t_prev = t_start
    for btn in seq:
        cands = [t for t in times_dict.get(btn, []) if t_prev <= t < t_attack]
        if not cands:
            return False
        t_prev = cands[0]  # 最初に出た時刻を起点に次を探す
    return True


def detect_in_group(grp: pd.DataFrame) -> list:
    """1試合×1プレイヤーのデータからコマンドイベントを検出。"""
    grp = grp.sort_values("timestamp_sec").reset_index(drop=True)
    ts = grp["timestamp_sec"].values

    # 各ボタンが 1 になっているタイムスタンプリスト（前の状態が 0 の遷移 = 押した瞬間）
    def press_times(col):
        vals = grp[col].fillna(0).values
        prev = [0.0] + list(vals[:-1])
        return [ts[i] for i in range(len(vals)) if vals[i] == 1 and prev[i] == 0]

    times = {btn: press_times(btn) for btn in
             ["Right", "Down", "DownRight", "Left", "DownLeft"] + ATTACK_BTNS}

    events = []
    src   = grp["source_file"].iloc[0]
    user  = grp["username"].iloc[0]

    for atk in ATTACK_BTNS:
        for t_atk in times[atk]:
            # DP 右向き: Right → DownRight → attack
            if _has_seq(times, ["Right", "DownRight"], t_atk):
                events.append({
                    "source_file": src, "username": user,
                    "timestamp_sec": t_atk, "command": "shoryuken",
                    "direction": "right",
                })
            # DP 左向き: Left → DownLeft → attack
            elif _has_seq(times, ["Left", "DownLeft"], t_atk):
                events.append({
                    "source_file": src, "username": user,
                    "timestamp_sec": t_atk, "command": "shoryuken",
                    "direction": "left",
                })
            # QCF 右向き: Down → DownRight → Right → attack
            if _has_seq(times, ["Down", "DownRight", "Right"], t_atk):
                events.append({
                    "source_file": src, "username": user,
                    "timestamp_sec": t_atk, "command": "hadouken",
                    "direction": "right",
                })
            # QCF 左向き: Down → DownLeft → Left → attack
            elif _has_seq(times, ["Down", "DownLeft", "Left"], t_atk):
                events.append({
                    "source_file": src, "username": user,
                    "timestamp_sec": t_atk, "command": "hadouken",
                    "direction": "left",
                })

    return events


def main(data_dir: Path, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)

    print("Loading CSV files...")
    train = pd.read_csv(data_dir / "train.csv", usecols=LOAD_COLS, low_memory=False)
    test  = pd.read_csv(data_dir / "test.csv",  usecols=LOAD_COLS, low_memory=False)
    both  = pd.concat([train, test], ignore_index=True)
    print(f"  Total rows: {len(both):,}")

    all_events = []
    groups = list(both.groupby(["source_file", "username"]))
    print(f"  Groups: {len(groups)}")

    for i, ((src, user), grp) in enumerate(groups):
        evs = detect_in_group(grp)
        all_events.extend(evs)
        print(f"  [{i+1:2d}/{len(groups)}] {src} / {user:12s} → {len(evs)} events")

    df_events = pd.DataFrame(all_events)
    if df_events.empty:
        print("No events detected.")
        return

    # 重複除去: 同一プレイヤー・同一タイムスタンプ・同一コマンドが複数検出される場合
    df_events = df_events.drop_duplicates(
        subset=["source_file", "username", "timestamp_sec", "command"]
    ).sort_values(["source_file", "timestamp_sec"]).reset_index(drop=True)

    # クリップ間の間引き: 同一コマンドが 1 秒以内に連続して検出されたら最初のみ残す
    filtered = []
    last_t = {}
    for _, row in df_events.iterrows():
        key = (row["source_file"], row["username"], row["command"])
        t = row["timestamp_sec"]
        if key not in last_t or t - last_t[key] > 1.0:
            filtered.append(row)
            last_t[key] = t
    df_filtered = pd.DataFrame(filtered).reset_index(drop=True)

    out_path = out_dir / "command_events.csv"
    df_filtered.to_csv(out_path, index=False)

    print(f"\n=== 検出結果 ===")
    print(df_filtered.groupby("command")["username"].count().rename("count").to_string())
    print(f"\nプレイヤー別:")
    print(df_filtered.groupby(["username", "command"]).size().unstack(fill_value=0).to_string())
    print(f"\n出力: {out_path} ({len(df_filtered)} events)")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--data-dir", type=Path, default=BASE_DIR / "output")
    p.add_argument("--out-dir",  type=Path, default=BASE_DIR / "data")
    args = p.parse_args()
    main(args.data_dir, args.out_dir)
