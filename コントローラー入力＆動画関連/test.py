import inputs
import time
import datetime
import threading


# デバウンス閾値（秒）
DEBOUNCE_THRESHOLD = 0.1  # 20 ms

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
    "UpRight": "UpRight",
    "UpLeft": "UpLeft",
    "DownRight": "DownRight",
    "DownLeft": "DownLeft",
    
    
}

# (con_name, code) -> last_press_timestamp (float, seconds since epoch)
last_press_times = {}
last_press_lock = threading.Lock()

print("コントローラーの入力を待っています... (Ctrl+C で終了)")

def is_debounced(con_name: str, code: str, event_ts: float) -> bool:
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

def listen_to_controller(pad, con_name):
    """特定のコントローラを常時監視するスレッド関数"""
    RZBeforeState = 0
    ZBeforeState = 0
    isRZpushing = False
    isZpushing = False
    
    #十字ボタンの状態を保持
    hat_x = 0  # -1: 左, 0: 中立, 1: 右
    hat_y = 0  # -1: 上, 0: 中立, 1: 下

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
                
                # ① まず HAT の状態更新
                if event.code == "ABS_HAT0X":
                    hat_x = event.state   # -1, 0, 1
                elif event.code == "ABS_HAT0Y":
                    hat_y = event.state   # -1, 0, 1

                # ② HAT 関連のイベントなら、今の (hat_x, hat_y) から方向を決めて出力
                if event.code in ("ABS_HAT0X", "ABS_HAT0Y"):
                    dir_name = None

                    if hat_x == 0 and hat_y == 0:
                         break
                    if hat_x == 0:
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
                    # HATイベントはここで処理完了。他の if/elif に行かないように continue
                    continue
                
                #条件式：Stateが３７以下かつRZボタンかつ直前のStateより現在のほうが押されているならば
                if (isRZpushing == False) and (event.code == "ABS_RZ") and (event.state > RZBeforeState) and (is_debounced(con_name, event.code, event_ts) == False):
                    isRZpushing = True
                    RZBeforeState = event.state

                    
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
