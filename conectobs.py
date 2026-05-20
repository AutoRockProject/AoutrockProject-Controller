
from obswebsocket import obsws, requests

host = "localhost"
port = 4455
password = "31U1iYQEwXHkOCWH"  # OBSで設定したもの

ws = obsws(host, port, password)
ws.connect()

# 録画開始
ws.call(requests.StartRecord())

input("録画中...Enterで停止")

# 録画停止
ws.call(requests.StopRecord())

ws.disconnect()