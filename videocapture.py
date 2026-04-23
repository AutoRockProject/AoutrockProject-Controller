import time
import pyautogui
import cv2
import numpy as np

fps = 60
cap_region = (0, 0, 1920, 1030)

def Startcapture(stop_event):

    # 動画ライターを最初に作る
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter('capture.mp4', fourcc, fps, (1920, 1030))

    print("録画開始")

    while not stop_event.is_set():
        start = time.perf_counter()

        cap = pyautogui.screenshot(region=cap_region)
        img = cv2.cvtColor(np.array(cap), cv2.COLOR_RGB2BGR)

        # ★ここで即書き込み
        out.write(img)

        end = time.perf_counter()

        if end - start < 1 / fps:
            time.sleep(1 / fps - (end - start))

    # 終了処理
    out.release()
    print("録画終了")