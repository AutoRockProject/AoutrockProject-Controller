"""
ESP32のふり役プログラム(STEP 4: サーボ制御を仮の数値で組み込む)

やっていること:
1. config.json から接続設定を読み込む
2. MQTTブローカー(Mosquitto)に接続する
3. 決めたトピックを購読(subscribe)する
4. メッセージを受信したら、画面にログを表示する
5. "unlock" / "lock" を受信したら、サーボを仮の角度まで回した「ふり」をする
   (UNLOCK_ANGLE / LOCK_ANGLE の値を変えるだけで、後から本番の角度に差し替えられる)
"""

import json
import paho.mqtt.client as mqtt

# --- 1. 設定ファイルを読み込む ---
with open("connect_to_ESP32\config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

BROKER_HOST = config["broker_host"]
BROKER_PORT = config["broker_port"]
TOPIC = config["topic"]
USERNAME = config["username"]
PASSWORD = config["password"]

# --- サーボの仮の角度(ハード担当から正式な数値が出たらここだけ差し替える) ---
UNLOCK_ANGLE = 90  # 解錠時にサーボを回す角度(仮)
LOCK_ANGLE = 0     # 施錠時にサーボを戻す角度(仮)


# --- 2. ブローカーに接続できたときに呼ばれる関数 ---
def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code == 0:
        print(f"[接続成功] {BROKER_HOST}:{BROKER_PORT} に接続しました")
        client.subscribe(TOPIC)
        print(f"[購読開始] トピック '{TOPIC}' を見張っています")
    else:
        print(f"[接続失敗] reason_code={reason_code}")


# --- 3. メッセージを受信したときに呼ばれる関数 ---
def on_message(client, userdata, msg):
    payload = msg.payload.decode()
    print(f"[受信] トピック: {msg.topic} / 中身: \"{payload}\"")

    # 受信した中身によって、サーボを回すふりをする処理を分ける
    if payload == "unlock":
        print(f"[サーボ(仮)] {UNLOCK_ANGLE}度まで回します → 解錠")
    elif payload == "lock":
        print(f"[サーボ(仮)] {LOCK_ANGLE}度まで戻します → 施錠")
    else:
        # 想定外の文字列が来た場合は何もしない(安全のため無視する)
        print(f"[警告] 想定外のメッセージなので無視しました: \"{payload}\"")


# --- 4. クライアントを作成して接続する ---
client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
client.username_pw_set(USERNAME, PASSWORD)
client.on_connect = on_connect
client.on_message = on_message

print("MQTTブローカーへの接続を試みています...")
client.connect(BROKER_HOST, BROKER_PORT)

# ずっと見張り続ける(Ctrl+Cで終了)
client.loop_forever()
