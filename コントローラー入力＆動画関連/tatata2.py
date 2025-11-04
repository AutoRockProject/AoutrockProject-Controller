import inputs
import time
import datetime
import threading


# デバウンス閾値（秒）
DEBOUNCE_THRESHOLD = 0.02  # 20 ms

RZcurrentstate = 0
RZtmpstate = 0

Zcurrentstate = 0
Ztmpstate = 0

print("コントローラーの入力を待っています... (Ctrl+C で終了)")

def listen_to_controller(pad, con_name):
    """特定のコントローラを常時監視するスレッド関数"""
    isRZpushing = False
    isZpushing = False

    print(f"[スレッド開始] {con_name}: {pad.name}")
    while True:
        try:
            events = pad.read()  # そのコントローラ専用の入力を取得
            for event in events:

                # if (event.code == "ABS_Z")((event.state  == 1) or (event.state == -1)):
                #     ts = datetime.datetime.fromtimestamp(event.timestamp)
                #     print(
                #         f"[{con_name}] "
                #         f"Timestamp: {ts.strftime('%Y-%m-%d %H:%M:%S.%f')}, "
                #         f"Code: {event.code}, State: {event.state}"
                #     )
                if (isRZpushing == False) and (event.code == "ABS_RZ"):
                    isRZpushing = True
                    

                    ts = datetime.datetime.fromtimestamp(event.timestamp)
                    print(
                        f"[{con_name}] "
                        f"Timestamp: {ts.strftime('%Y-%m-%d %H:%M:%S.%f')}, "
                        f"Code: {event.code}, State: {event.state}"
                    )
                elif (isZpushing == False) and (event.code == "ABS_Z"):
                    isZpushing = True
                    ts = datetime.datetime.fromtimestamp(event.timestamp)
                    print(
                        f"[{con_name}] "
                        f"Timestamp: {ts.strftime('%Y-%m-%d %H:%M:%S.%f')}, "
                        f"Code: {event.code}, State: {event.state}"
                    )
                elif (event.state == 0) and (event.code == "ABS_RZ"):
                    print("RZリセット")
                    isRZpushing = False
                elif (event.state == 0) and (event.code == "ABS_Z"):
                    print("Zリセット")
                    isZpushing = False
                elif event.state in (-1,1):
                    ts = datetime.datetime.fromtimestamp(event.timestamp)
                    print(
                        f"[{con_name}] "
                        f"Timestamp: {ts.strftime('%Y-%m-%d %H:%M:%S.%f')}, "
                        f"Code: {event.code}, State: {event.state}"
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
