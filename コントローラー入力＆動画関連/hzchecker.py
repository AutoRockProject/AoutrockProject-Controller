import inputs
import time
import datetime
import threading

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

print("コントローラーの入力を待っています... (Ctrl+C で終了)")

def listen_to_controller(pad, con_name):
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




                print(
                    f"[{con_name}] "
                    f"Timestamp: {ts.strftime('%Y-%m-%d %H:%M:%S.%f')}, "
                    f"Code: {BUTTONNAME[event.code]}, State: {event.state}"
                )
            time.sleep(1/60)



                        
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
