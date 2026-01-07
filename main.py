import inputs
import time
import datetime
import threading
import csv
import os
import atexit
import shutil
from pathlib import Path


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

FILE = input() + ".csv"
# 先にカラム（列）を固定
FIELDNAMES = [
    "username", "Timestamp", "X", "Y", "B", "A", "RB", "LB", "RStick", "LStick", "SELECT", "START",
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
        
        
        



def listen_to_controller(pad, con_name):
    """特定のコントローラを常時監視するスレッド関数"""
    global hat_x, hat_y, ts, event_ts, ROWORIZIN
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
                
                ts = datetime.datetime.fromtimestamp(event.timestamp)
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

                #SYN_REPORTは１フレーム内でここまで処理しましたというアラームなので除外
                elif event.code not in ("SYN_REPORT","ABS_RZ", "ABS_Z") and (event.state == 1 or event.state == 0) :
                    
                    # row[ ButtonName「イベントコード」] = state
                    print(event.code)
                    row[BUTTONNAME[event.code]] = event.state

                    continue
            #ここにrowを追加する処理を書く
            row["Timestamp"] = ts
            append_row(row)
            
                        
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


def on_exit():
    
    # 移動したいファイル（元の場所）
    src = Path(r"C:\Users\22311\GitHub\AoutrockProject\output.csv")

    # 移動先フォルダ
    saveDir =  Path(r"C:\Users\22311\GitHub\AoutrockProject\csvfiles")

    # 移動先フォルダが無ければ作る
    # dst_dir.mkdir(parents=True, exist_ok=True)

    # 移動する（移動先は「フォルダ」を指定すればOK）
    shutil.move(str(src), str(saveDir))
    