import inputs
import time
import datetime
import threading


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
    "Center": "Center",
    "UpRight": "UpRightArrow",
    "UpLeft": "UpLeftArrow",
    "DownRight": "DownRightArrow",
    "DownLeft": "DownLeftArrow",
    
    
}

# (con_name, code) -> last_press_timestamp (float, seconds since epoch)
last_press_times = {}
last_press_lock = threading.Lock()

print("コントローラーの入力を待っています... (Ctrl+C で終了)")

def is_debounced(con_name: str, code: str, event_ts: float):
    """
    指定の (デバイス名, ボタンコード) に対して、
    最後の押下時刻との差が閾値未満なら True（無効化＝デバウンス判定）。
    スレッドセーフに last_press_times を参照/更新する。
    """
    key = (con_name, code)
    with last_press_lock:
        last = last_press_times.get(key)
        if last is None:
            # 初回なので無効化しない（処理する）
            last_press_times[key] = event_ts
            return False
        # 前回との差分
        delta = event_ts - last
        if delta < DEBOUNCE_THRESHOLD:
            # 閾値未満 → デバウンス（無効化）
            return True
        else:
            # 十分時間が経っている → 有効（時刻を更新）
            last_press_times[key] = event_ts
            return False
        
def direction_from_xy(x: int, y: int):
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
        dir_name = "Center"
    elif hat_x == 0:
        dir_name = "UpArrow" if hat_y == -1 else "DownArrow"
    elif hat_y == 0:
        dir_name = "LeftArrow" if hat_x == -1 else "RightArrow"
    else:
        # ここが斜め
        if hat_x == 1 and hat_y == -1:
            dir_name = "UpRight"
        elif hat_x == -1 and hat_y == -1:
            dir_name = "UpLeft"
        elif hat_x == 1 and hat_y == 1:
            dir_name = "DownRight"
        elif hat_x == -1 and hat_y == 1:
            dir_name = "DownLeft"

    print(
        f"[{con_name}] "
        f"Timestamp: {ts.strftime('%Y-%m-%d %H:%M:%S.%f')}, "
        f"Code: {BUTTONNAME[dir_name]}, State: (x={hat_x}, y={hat_y})"
    )



def listen_to_controller(pad, con_name):
    """特定のコントローラを常時監視するスレッド関数"""
    RZBeforeState = 0
    ZBeforeState = 0
    isRZpushing = False
    isZpushing = False
    
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
            for event in events:

                # if (event.code == "ABS_Z")((event.state  == 1) or (event.state == -1)):
                #     
                #     print(
                #         f"[{con_name}] "
                #         f"Timestamp: {ts.strftime('%Y-%m-%d %H:%M:%S.%f')}, "
                #         f"Code: {event.code}, State: {event.state}"
                #     )
                
                ts = datetime.datetime.fromtimestamp(event.timestamp)
                # デバウンス用は float 秒
                event_ts = event.timestamp
                
                if event.code == "ABS_X":
                    Rstick_x = event.state

                elif event.code == "ABS_Y":
                    Rstick_y = event.state

                
                if event.code == "ABS_X" or event.code == "ABS_Y":
                    StickStatecode = direction_from_xy(Rstick_x,Rstick_y)
                    
                    if StickStatecode != last_printed["RightStick"]:
                        print(StickStatecode)
                        # ずっと同じ方向を連打表示しない（必要なら外してOK）
                        if StickStatecode is None:
                            print(
                            f"[{con_name}] "
                            f"Timestamp: {ts.strftime('%Y-%m-%d %H:%M:%S.%f')}, "
                            f"Code: Center, State: (x={Rstick_x}, y={Rstick_y})"
                            )
                        else:
                            print(
                            f"[{con_name}] "
                            f"Timestamp: {ts.strftime('%Y-%m-%d %H:%M:%S.%f')}, "
                            f"Code: {StickStatecode}, State: (x={Rstick_x}, y={Rstick_y})"
                            )
                        
                        last_printed["RightStick"] = StickStatecode
                            

                    
                
                # ① まず HAT の状態更新
                if event.code == "ABS_HAT0X":
                    hat_x = event.state   # -1, 0, 1
                elif event.code == "ABS_HAT0Y":
                    hat_y = event.state   # -1, 0, 1

                # ② HAT 関連のイベントなら、今の (hat_x, hat_y) から方向を決めて出力
                if event.code in ("ABS_HAT0X", "ABS_HAT0Y"):
                    printArrows()
                    # HATイベントはここで処理完了。他の if/elif に行かないように continue
                    continue

                
                #条件式：Stateが３７以下かつRZボタンかつ直前のStateより現在のほうが押されているならば
                if (event.code == "ABS_RZ"):

                    
                    print(
                        f"[{con_name}] "
                        f"Timestamp: {ts.strftime('%Y-%m-%d %H:%M:%S.%f')}, "
                        f"Code: {event.code}, State: {event.state}"
                    )
                elif (isZpushing == False) and (event.code == "ABS_Z") and (event.state > ZBeforeState) and (is_debounced(con_name, event.code, event_ts) == False):
                    isZpushing = True
                    ZBeforeState = event.state

                    
                    print(
                        f"[{con_name}] "
                        f"Timestamp: {ts.strftime('%Y-%m-%d %H:%M:%S.%f')}, "
                        f"Code: {event.code}, State: {event.state}"
                    )
                elif (event.state <= 37) and (event.code == "ABS_RZ"):
                    RZBeforeState = event.state
                    
                    # print("RZリセット")
                    isRZpushing = False
                elif (event.state <= 37) and (event.code == "ABS_Z"):
                    ZBeforeState = event.state

                    # print("Zリセット")
                    isZpushing = False
                    
                # elif event.state == -1:
                    
                #     print(
                #         f"[{con_name}] "
                #         f"Timestamp: {ts.strftime('%Y-%m-%d %H:%M:%S.%f')}, "
                #         f"Code: {BUTTONNAME[f'-{event.code}']}, State: {event.state}"
                #     )
                elif event.state == 1:
                    
                    print(
                        f"[{con_name}] "
                        f"Timestamp: {ts.strftime('%Y-%m-%d %H:%M:%S.%f')}, "
                        f"Code: {BUTTONNAME[event.code]}, State: {event.state}"
                    )



                        
        except inputs.UnpluggedError:
            print(f"⚠️ {con_name} ({pad.name}) が切断されました。")
            break
        except Exception as e:
            print(f"{con_name} ({pad.name}) 読み取りエラー: {e}")
            time.sleep(0.1)

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

