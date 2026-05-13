import inputs
# import videocapture
import time
import datetime
import threading
import csv
import os
import atexit
import shutil
import json
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import obsws_python as obs

# OBS WebSocket 接続設定
OBS_HOST     = "localhost"
OBS_PORT     = 4455
# OBSのWebSocket設定でパスワードを設定した場合はここに入力
#ゼミ
OBS_PASSWORD = "31U1iYQEwXHkOCWH"  
# #家
# OBS_PASSWORD = "w9cUMDfNKHi3N63L"  


# 録画開始時刻をファイルに書き込む（obstextgui.py と共有）
START_EPOCH = time.time()
_PERF_START = time.perf_counter()  # 高精度タイマー（index.html 表示用）
_START_TIME_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "start_time.txt")
with open(_START_TIME_FILE, "w") as f:
    f.write(str(START_EPOCH))

_HTTP_PORT = 8080
_HTML_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")

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


# 先にカラム（列）を固定
FIELDNAMES = [
    "username", "Timestamp", "X", "Y", "B", "A", "RB", "LB", "RT", "LT","RStick", "LStick", "SELECT", "START",
    "CenterArrow", "UpArrow", "DownArrow", "LeftArrow", "RightArrow", "UpRightArrow", "UpLeftArrow", "DownRightArrow", "DownLeftArrow", 
    "Center", "Up", "Down", "Right", "Left", "UpRight", "UpLeft", "DownRight", "DownLeft", "StateX", "StateY",
    ]  
ROWORIZIN = {col: 0 for col in FIELDNAMES}  # まず空で作る

latestrow = {}


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



        
def direction_from_xy(x: int, y: int):
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


IGNORE_KEYS = {"Timestamp"}

def append_row(row: dict):
    file_exists = os.path.exists(FILE)
    file_is_empty = (not file_exists) or (os.path.getsize(FILE) == 0)

    with open(FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        
        # ファイルが無い or 空ならヘッダーを書く
        if file_is_empty:
            writer.writeheader()

        #IGNORE_KEYSに入っているキー以外の用をを格納
        prev_filtered = {k: v for k, v in row.items() if k not in IGNORE_KEYS}
        # cur_filtered  = {k: v for k, v in cur.items()  if k not in IGNORE_KEYS}

        #rowに変化があった時だけ追加
        if latestrow != prev_filtered:
            # 1行追加
            writer.writerow(row)
            latestrow.update(prev_filtered)
        
        
def get_ts():
    elapsed = time.perf_counter() - _PERF_START
    m = int(elapsed // 60)
    s = int(elapsed % 60)
    us = int((elapsed - int(elapsed)) * 1_000_000)
    return f"{m:02}:{s:02}.{us:06}"


#git revert コミットのハッシュ値
def listen_to_controller(pad, con_name):
    """特定のコントローラを常時監視するスレッド関数"""
    global hat_x, hat_y, ts, event_ts, ROWORIZIN, stop_event

    #"""特定のコントローラを常時監視するスレッド関数"""
    LastABS_R = False
    LastABS_L = False

    #各コントローラーに行の辞書データを付与
    row = {}
    row.update(ROWORIZIN)
    row.update(username=con_name)
    
    #十字ボタンの状態を保持

    hat_x = 0 
    hat_y = 0
    
    stickstate_x = 0
    stickstate_y = 0
    
    last_printed = {"RightStick": None}
    
    print(f"[スレッド開始] {con_name}: {pad.name}")
    while True:
        try:
            events = pad.read()  # そのコントローラ専用の入力を取得
            
            for event in events:
                
                # ts = datetime.datetime.fromtimestamp(event.timestamp)
                # デバウンス用は float 秒
                event_ts = event.timestamp
                
                if event.code == "ABS_X":
                    stickstate_x = event.state

                elif event.code == "ABS_Y":
                    stickstate_y = event.state

                
                if event.code == "ABS_X" or event.code == "ABS_Y":
                    StickStatecode = direction_from_xy(stickstate_x,stickstate_y)
                    
                    #前回と同じコードが出力されないかを審査
                    if StickStatecode != last_printed["RightStick"]:
                        
                        dircode = BUTTONNAME[StickStatecode]
                        
                        #スティックの入力は二つのコードが同時にアクティブになることは無いため、一度全てのコードを０にして変更後のコードのみに１を代入
                        row.update(Center=0, Up=0, Down=0, Left=0, Right=0, UpRight=0, UpLeft=0, DownRight=0, DownLeft=0 )
                        
                        #ボタンと違いstateで方向を表せないため、方向は関数で算出し、そこに１を代入
                        row[BUTTONNAME[dircode]] = 1
                        # print(f"前: {row}")
                        
                        #スティックのみstateも別途記録する
                        row["StateX"] = stickstate_x
                        row["StateY"] = stickstate_y
                        print(f"後: {row}")
                        last_printed["RightStick"] = StickStatecode
                        
                        continue
                
                # ① まず HAT の状態更新
                if event.code == "ABS_HAT0X":
                    hat_x = event.state   # -1, 0, 1
                elif event.code == "ABS_HAT0Y":
                    hat_y = event.state   # -1, 0, 1

                # ② HAT 関連のイベントなら、今の (hat_x, hat_y) から方向を決めて出力
                if event.code in ("ABS_HAT0X", "ABS_HAT0Y"):
                    #Arrowdirはevent.codeを変換したモノ。扱いは同じ
                    Arrowdir = printArrows()

                    #十字キーの入力があったら一度全てのコードを０にして変更後のコードのみに１を代入
                    row.update(CenterArrow=0, UpArrow=0, DownArrow=0, LeftArrow=0, RightArrow=0, UpRightArrow=0, UpLeftArrow=0, DownRightArrow=0, DownLeftArrow=0 )
                    
                    #ボタンと違いstateで方向を表せないため、方向は関数で算出し、そこに１を代入
                    row[BUTTONNAME[Arrowdir]] = 1
                    
                    continue
                

                #ABS系のボタンはStateが０１ではないため手打ちで１を入力
                if (event.code == "ABS_RZ") and (LastABS_R == False):
                    print("ABSR-ON")
                    LastABS_R = True
                    row[BUTTONNAME[event.code]] = 1


                elif (event.code == "ABS_Z") and (LastABS_L == False):
                    print("ABSL-ON")
                    LastABS_L = True
                    row[BUTTONNAME[event.code]] = 1

                
                elif (event.code == "ABS_RZ") and (event.state == 0):
                    print("ABSR-OFF")
                    LastABS_R = False
                    row[BUTTONNAME[event.code]] = event.state


                elif (event.code == "ABS_Z") and (event.state == 0):
                    print("ABSL-OFF")
                    LastABS_L = False
                    row[BUTTONNAME[event.code]] = event.state


                #SYN_REPORTは１フレーム内でここまで処理しましたというアラームなので除外
                elif event.code not in ("SYN_REPORT","ABS_RZ", "ABS_Z") and (event.state == 1 or event.state == 0) :
                    
                    # row[ ButtonName「イベントコード」] = state
                    # print(event.code)
                    row[BUTTONNAME[event.code]] = event.state

                    continue

            #ここにrowを追加する処理を書く
            row["Timestamp"] = get_ts()
            append_row(row)
            
                        
        except inputs.UnpluggedError:
            print(f"⚠️ {con_name} ({pad.name}) が切断されました。")
            break
        except Exception as e:
            print(f"{con_name} ({pad.name}) 読み取りエラー: {e}")
            # time.sleep(0.1)

class _TSHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/ts":
            body = json.dumps({"ts": get_ts()}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
        elif self.path in ("/", "/index.html"):
            try:
                with open(_HTML_FILE, "r", encoding="utf-8") as f:
                    html = f.read()
                html = html.replace("{{START_EPOCH_MS}}", str(int(START_EPOCH * 1000)))
                body = html.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(body)
            except FileNotFoundError:
                self.send_error(404)
        else:
            self.send_error(404)

    def log_message(self, _fmt, *_args):
        pass  # HTTPログを抑制


def _start_http_server():
    server = HTTPServer(("localhost", _HTTP_PORT), _TSHandler)
    server.serve_forever()


obs_client = None

try:
    gamepads = inputs.devices.gamepads


    print("名前を入力してください（例: 田中 山田）")
    names_input = input().split()
    name1 = names_input[0]
    name2 = names_input[1]

    today = datetime.date.today().strftime("%Y%m%d")
    date_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), today)
    os.makedirs(date_dir, exist_ok=True)

    base_name = f"{today}_{name1}_{name2}"
    existing = len([f for f in os.listdir(date_dir)
                    if f.startswith(base_name + "_") and f.endswith(".csv")])
    count = existing + 1
    FILE = os.path.join(date_dir, f"{base_name}_{count}.csv")

    # HTTPサーバーをバックグラウンドで起動
    http_thread = threading.Thread(target=_start_http_server, daemon=True)
    http_thread.start()
    print(f"[HTTPサーバー起動] http://localhost:{_HTTP_PORT}/")

    if not gamepads:
        print("エラー: ゲームパッドが見つかりません。")
        raise SystemExit(1)
    else:
        print(f"{len(gamepads)}台のコントローラーが見つかりました:")


        threads = []
        con_names = {}

        # 見つけた順に name1, name2... を割り当てる
        player_names = [name1, name2]
        for i, pad in enumerate(gamepads, start=1):
            con_name = player_names[i - 1] if i <= len(player_names) else f"con{i}"
            con_names[pad] = con_name
            print(f"  {con_name}: {pad.name}")

            # スレッドを起動
            t = threading.Thread(target=listen_to_controller, args=(pad, con_name), daemon=True)
            t.start()
            threads.append(t)
        
        

        print("\n--- すべてのコントローラからの入力を監視中 ---")
        print("（Ctrl+C で終了）\n")

        # OBS 録画開始
        obs_client = None
        try:
            obs_client = obs.ReqClient(host=OBS_HOST, port=OBS_PORT, password=OBS_PASSWORD)
            obs_client.start_record()
            print("[OBS] 録画開始")
            obs_client.press_input_properties_button(input_name="ts", prop_name="refreshnocache")
            print("[OBS] ブラウザソース再読み込み")
        except Exception as e:
            print(f"[OBS] 録画開始失敗（OBSが起動していないか、WebSocketが無効）: {e}")

        while True:
            time.sleep(1)

except KeyboardInterrupt:
    # OBS 録画停止
    if obs_client is not None:
        try:
            resp = obs_client.stop_record()
            print("[OBS] 録画停止")
            src = resp.output_path
            ext = os.path.splitext(src)[1]
            dst = os.path.splitext(FILE)[0] + ext
            for _ in range(10):
                try:
                    shutil.move(src, dst)
                    print(f"[OBS] 動画保存: {dst}")
                    break
                except PermissionError:
                    time.sleep(1)
            else:
                print(f"[OBS] 動画の移動に失敗しました: {src}")
        except Exception as e:
            print(f"[OBS] 録画停止失敗: {e}")

    print("\nプログラムを終了します。")
