import inputs
import time
import datetime
import threading
import csv
import os


# デバウンス閾値（秒）
DEBOUNCE_THRESHOLD = 0.1  # 20 ms

DEADZONE = 8000      # この値より小さい動きは「触ってない」とみなす（0〜32767の範囲が多い）
DIAG_RATIO = 0.60    # 斜め判定の比率（大きいほど斜めになりにくい）

AXIS_MAP = {
    "ABS_X":  ("LeftStick", "x"),
    "ABS_Y":  ("LeftStick", "y"),
    # "ABS_RX": ("RightStick", "x"),
    # "ABS_RY": ("RightStick", "y"),
}

FILE = "output.csv"
# 先にカラム（列）を固定
FIELDNAMES = [
    "Timestamp", "X", "Y", "B", "A", "RB", "LB", "RStick", "LStick", "SELECT", "START",
    "CenterArrow", "UpArrow", "DownArrow", "LeftArrow", "RightArrow", "UpRightArrow", "UpLeftArrow", "DownRightArrow", "DownLeftArrow", 
    "Center", "Up", "Down", "Right", "Left", "UpRight", "UpLeft", "DownRight", "DownLeft",
    ]  
ROWORIZIN = {col: "" for col in FIELDNAMES}  # まず空で作る
row = {}

BUTTONNAME = {
    "BTN_WEST": "X",
    "BTN_NORTH": "Y",
    "BTN_EAST": "B",
    "BTN_SOUTH": "A",
    "BTN_THUMBR": "RStick",
    "BTN_THUMBL": "LStick",
    "BTN_TR": "RB",
    "BTN_TL": "LB",
    "ABS_RZ": "RT",
    "ABS_Z": "LT",
    "BTN_SELECT": "SELECT",
    "BTN_START": "START",
    "UpArrow": "UpArrow",
    "DownArrow": "DownArrow",
    "LeftArrow": "LeftArrow",
    "RightArrow": "RightArrow",
    "CenterArrow": "CenterArrow",
    "UpRightArrow": "UpRightArrow",
    "UpLeftArrow": "UpLeftArrow",
    "DownRightArrow": "DownRightArrow",
    "DownLeftArrow": "DownLeftArrow",
    "Center":"Center",
    "Up":"Up",
    "Down":"Down",
    "Right":"Right",
    "Left":"Left",
    "UpRight":"UpRight",
    "UpLeft":"UpLeft",
    "DownRight":"DownRight",
    "DownLeft":"DownLeft",
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
        return "Center"

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
        dir_y = "Down" if y < 0 else "Up"

    # 斜め判定：両方ある場合のみ
    if dir_x and dir_y:
        # どちらも十分強い（弱すぎる方を無視しない）なら斜め
        # 小さい方 / 大きい方 が DIAG_RATIO 以上なら斜め採用
        small = min(ax, ay)
        big = max(ax, ay)
        if small / big >= DIAG_RATIO:
            return f"{dir_y}{dir_x}"  # 例: Up-Right
        # 斜めに届かないなら、強い方だけ返す
        return dir_y if ay > ax else dir_x

    # 片方だけならそれ
    return dir_y or dir_x


def printArrows() :
    dir_name = None

    if hat_x == 0 and hat_y == 0:
        dir_name = "CenterArrow"
    elif hat_x == 0:
        dir_name = "UpArrow" if hat_y == -1 else "DownArrow"
    elif hat_y == 0:
        dir_name = "LeftArrow" if hat_x == -1 else "RightArrow"
    else:
        # ここが斜め
        if hat_x == 1 and hat_y == -1:
            dir_name = "UpRightArrow"
        elif hat_x == -1 and hat_y == -1:
            dir_name = "UpLeftArrow"
        elif hat_x == 1 and hat_y == 1:
            dir_name = "DownRightArrow"
        elif hat_x == -1 and hat_y == 1:
            dir_name = "DownLeftArrow"

    return dir_name




def listen_to_controller(pad, con_name):
    """特定のコントローラを常時監視するスレッド関数"""
    
    #十字ボタンの状態を保持
    global hat_x, hat_y, ts, event_ts
    hat_x = 0 
    hat_y = 0
    
    Rstick_x = 0
    Rstick_y = 0
    
    last_printed = {"RightStick": None}
    
    print(f"[スレッド開始] {con_name}: {pad.name}")
    while True:
        try:
            events = pad.read()  # そのコントローラ専用の入力を取得
            #csvに入れる行の値をリセット
            row.update(ROWORIZIN)
            for event in events:
                
                ts = datetime.datetime.fromtimestamp(event.timestamp)
                # デバウンス用は float 秒
                event_ts = event.timestamp
                
                if event.code == "ABS_X":
                    Rstick_x = event.state

                elif event.code == "ABS_Y":
                    Rstick_y = event.state

                
                if event.code == "ABS_X" or event.code == "ABS_Y":
                    StickStatecode = direction_from_xy(Rstick_x,Rstick_y)
                    
                    #前回と同じコードが出力されないかを審査
                    if StickStatecode != last_printed["RightStick"]:
                        dircode = BUTTONNAME[StickStatecode]

                        print(
                        f"[{con_name}] "
                        f"Timestamp: {ts.strftime('%Y-%m-%d %H:%M:%S.%f')}, "
                        f"Code: {dircode}, State: (x={Rstick_x}, y={Rstick_y})"
                        )
                        
                        last_printed["RightStick"] = StickStatecode
                        continue
                            

                    
                
                # ① まず HAT の状態更新
                if event.code == "ABS_HAT0X":
                    hat_x = event.state   # -1, 0, 1
                elif event.code == "ABS_HAT0Y":
                    hat_y = event.state   # -1, 0, 1

                # ② HAT 関連のイベントなら、今の (hat_x, hat_y) から方向を決めて出力
                if event.code in ("ABS_HAT0X", "ABS_HAT0Y"):
                    Arrowdir = printArrows()
                    print(
                    f"[{con_name}] "
                    f"Timestamp: {ts.strftime('%Y-%m-%d %H:%M:%S.%f')}, "
                    f"Code: {BUTTONNAME[Arrowdir]}, State: (x={hat_x}, y={hat_y})"
                    )   
                    # HATイベントはここで処理完了。他の if/elif に行かないように continue
                    continue

                
                elif event.state == 1 or event.state == 0 :
                    
                    # print(
                    #     f"[{con_name}] "
                    #     f"Timestamp: {ts.strftime('%Y-%m-%d %H:%M:%S.%f')}, "
                    #     f"Code: {BUTTONNAME[event.code]}, State: {event.state}"
                    # )
                    print(
                        f"Timestamp: {ts.strftime('%Y-%m-%d %H:%M:%S.%f')}, "
                        f"Code: {event.code}, State: {event.state}"
                    )
                    continue
            #ここにrowを追加する処理を書く

                        
        except inputs.UnpluggedError:
            print(f"⚠️ {con_name} ({pad.name}) が切断されました。")
            break
        except Exception as e:
            print(f"{con_name} ({pad.name}) 読み取りエラー: {e}")
            # time.sleep(0.1)

try:
    gamepads = inputs.devices.gamepads

    if not gamepads:
        print("エラー: ゲームパッドが見つかりません。")
    else:
        print(f"{len(gamepads)}台のコントローラーが見つかりました:")

        threads = []
        con_names = {}

        # 見つけた順に con1, con2... を割り当てる
        for i, pad in enumerate(gamepads, start=1):
            con_name = f"con{i}"
            con_names[pad] = con_name
            print(f"  {con_name}: {pad.name}")

            # スレッドを起動
            t = threading.Thread(target=listen_to_controller, args=(pad, con_name), daemon=True)
            t.start()
            threads.append(t)

        print("\n--- すべてのコントローラからの入力を監視中 ---")
        print("（Ctrl+C で終了）\n")

        while True:
            time.sleep(1)

except KeyboardInterrupt:
    print("\nプログラムを終了します。")

