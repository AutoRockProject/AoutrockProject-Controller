"""
Mosquittoと通信する送信スクリプト(送信専用)

やっていること:
1. config.json から接続設定を読み込む
2. MQTT経由で "unlock" を1回だけ送信する

このスクリプトは「送信すること」だけが役割。
呼び出す側(action_mock.py)が、送信していいかどうかを判断してから実行する。
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


def send_unlock():
    """MQTT経由で unlock メッセージを1回だけ送信する"""
    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(USERNAME, PASSWORD)
    client.connect(BROKER_HOST, BROKER_PORT)

    # 裏側の通信処理(loop)を別スレッドで開始する
    # これが動いていないと、publish()で予約したメッセージが実際には送信されない
    client.loop_start()

    msg_info = client.publish(TOPIC, "unlock")
    msg_info.wait_for_publish()  # 実際に送信が完了するまでここで待つ

    print(f"[送信] トピック '{TOPIC}' に \"unlock\" を送信しました")

    client.loop_stop()
    client.disconnect()


# --- 2. 送信を実行する ---
if __name__ == "__main__":
    send_unlock()
