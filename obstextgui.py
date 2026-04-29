import time
from main import get_ts
from datetime import datetime


def writets(stop_event):
    # --- 初期化（ここでファイルを空にする） ---
    with open("timestamp.txt", "w") as f:
        f.write("")  # ← これで中身クリア

    # --- 追記モードで開く ---
    with open("timestamp.txt", "a") as f:
        while not stop_event.is_set():
            now = main.get_ts()
            f.seek(0)           # 常に先頭に書く（上書きしたい場合）
            f.write(now)
            f.truncate()        # 古い内容を消す
            f.flush()           # 即反映（OBS用に重要）
            time.sleep(0.01)    # 100Hz更新