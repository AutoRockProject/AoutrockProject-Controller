import time
import cv2
import numpy as np
import mss
import threading

fps = 60

# mss用の指定（dict形式）
# monitor = {"top": 0, "left": 0, "width": 1920, "height": 1030}
monitor = {"top": 0, "left": 0, "width": 1280, "height": 720}

def Startcapture(stop_event):
    # fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter('capture.mp4', fourcc, fps, (1280, 720))

    sct = mss.mss()

    print("録画開始")
    frame_count = 0
    start_time = time.perf_counter()

    while not stop_event.is_set():
        # 高速キャプチャ
        sct_img = sct.grab(monitor)

        # numpy配列に変換（BGRA → BGR）
        img = np.array(sct_img)[:, :, :3]
        
        out.write(img)
        frame_count += 1

    
    end_time = time.perf_counter()

    actual_fps = frame_count / (end_time - start_time)
    print(actual_fps)

    # while not stop_event.is_set():
    #     start = time.perf_counter()

    #     # 高速キャプチャ
    #     sct_img = sct.grab(monitor)

    #     # numpy配列に変換（BGRA → BGR）
    #     img = np.array(sct_img)[:, :, :3]

    #     out.write(img)

    #     end = time.perf_counter()

    #     # FPS制御
    #     elapsed = end - start
    #     if elapsed < 1 / fps:
    #         time.sleep(1 / fps - elapsed)

    out.release()
    print("録画終了")

def get_ts():
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_id = 0

    ts = frame_id / fps



stop_event = threading.Event()
capturethread = threading.Thread(target=Startcapture, args=(stop_event,))
#録画開始
capturethread.start()

time.sleep(10)

stop_event.set()

# 終了待ち（重要）
capturethread.join()