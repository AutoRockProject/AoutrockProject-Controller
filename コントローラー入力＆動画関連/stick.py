# pip install inputs
from inputs import get_gamepad

# ---- 調整しやすい設定 ----
DEADZONE = 8000      # この値より小さい動きは「触ってない」とみなす（0〜32767の範囲が多い）
DIAG_RATIO = 0.60    # 斜め判定の比率（大きいほど斜めになりにくい）

# inputs の軸コード → (スティック名, 軸名)
AXIS_MAP = {
    "ABS_X":  ("LeftStick", "x"),
    "ABS_Y":  ("LeftStick", "y"),
    "ABS_RX": ("RightStick", "x"),
    "ABS_RY": ("RightStick", "y"),
}

# 各スティックの現在値を保存（x, y）
state = {
    "LeftStick":  {"x": 0, "y": 0},
    "RightStick": {"x": 0, "y": 0},
}

def direction_from_xy(x: int, y: int) -> str | None:
    """
    x, y から方向文字列を返す。
    None は「ほぼ中央（入力なし）」。
    ※ inputs では多くの場合、Yは下がプラス（下方向で値が増える）なので注意。
    """
    # デッドゾーン処理
    ax, ay = abs(x), abs(y)
    if ax < DEADZONE and ay < DEADZONE:
        return None

    # 斜めも含めて判定したいので、どちらが優勢かを見る
    # ay が大きいほど上下、ax が大きいほど左右
    # 比率で「斜め」を決める
    # 例：左右が強く、上下もそこそこなら「右上」みたいにする
    dir_x = ""
    dir_y = ""

    if ax >= DEADZONE:
        dir_x = "Right" if x > 0 else "Left"

    # 多くのデバイスで y>0 が「下」
    if ay >= DEADZONE:
        dir_y = "Down" if y > 0 else "Up"

    # 斜め判定：両方ある場合のみ
    if dir_x and dir_y:
        # どちらも十分強い（弱すぎる方を無視しない）なら斜め
        # 小さい方 / 大きい方 が DIAG_RATIO 以上なら斜め採用
        small = min(ax, ay)
        big = max(ax, ay)
        if small / big >= DIAG_RATIO:
            return f"{dir_y}-{dir_x}"  # 例: Up-Right
        # 斜めに届かないなら、強い方だけ返す
        return dir_y if ay > ax else dir_x

    # 片方だけならそれ
    return dir_y or dir_x


def main():
    print("Listening gamepad... (Ctrl+C to stop)")
    last_printed = {"LeftStick": None, "RightStick": None}

    while True:
        events = get_gamepad()  # 入力イベントをまとめて取得（ブロッキング）
        updated_sticks = set()

        for e in events:
            if e.ev_type != "Absolute":
                continue
            if e.code not in AXIS_MAP:
                continue
            
            
            stick, axis = AXIS_MAP[e.code]
            state[stick][axis] = e.state
            updated_sticks.add(stick)

        # 更新があったスティックだけ方向判定して表示
        for stick in updated_sticks:
            x = state[stick]["x"]
            y = state[stick]["y"]
            d = direction_from_xy(x, y)

            # ずっと同じ方向を連打表示しない（必要なら外してOK）
            if d != last_printed[stick]:
                if d is None:
                    print(f"{stick}: Center")
                else:
                    print(f"{stick}: {d}  (x={x}, y={y})")
                last_printed[stick] = d


if __name__ == "__main__":
    main()
