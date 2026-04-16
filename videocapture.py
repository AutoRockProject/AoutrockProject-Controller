import time
import pyautogui
import cv2
import numpy as np

# 3秒スリープ
# time.sleep(3)

# 動画のフレームレート
fps=15

# 録画時間(秒)
# rec_sec = 3

i = 0

# キャプチャー領域
cap_region = (0,0, 1920, 1030)

# キャプチャー画像を格納するリスト
frames = []

def Startcapture(stop_event):
    global i

    #画面をキャプチャーし
    while not stop_event.is_set():
        time.sleep(1)
        
        i = i + 1
        print(i)
    #     # 処理開始時間の取得
    #     start = time.perf_counter()
        
    #     # 画面をキャプチャー
    #     cap = pyautogui.screenshot(region = cap_region)
        
    #     # pillow形式からOpenCV形式に変換
    #     img = cv2.cvtColor(np.array(cap), cv2.COLOR_RGB2BGR)

    #     # # マウス位置を取得しマウスの絵を描画
    #     # mx, my = pyautogui.position()
    #     # pts = np.array([[mx, my], [mx, my+25], [mx+5, my+20],
    #     #                 [mx+10, my+28],[mx+14, my+27],[mx+11, my+20],
    #     #                 [mx+20, my+20]])
    #     # cv2.polylines(img, [pts], True, 30, thickness=1)
        
    #     # リストにキャプチャー画像を追加
    #     frames.append(img)
        
    #     # 処理終了時間の取得
    #     end = time.perf_counter()
        
    #     # 1回の処理時間が1フレームより短い場合、不足分スリープ
    #     if end-start<1/fps:
    #         time.sleep(1/fps-(end-start))

    # # 保存用動画ファイルのフォーマット設定
    # fourcc = cv2.VideoWriter_fourcc('m', 'p', '4', 'v') 
    # out = cv2.VideoWriter('capture.mp4', fourcc, fps, (1920, 1030))         

    # # キャプチャー画像を読み出して出力動画ファイルに追記
    # for img in frames:        
    #     out.write(img) 
        
    # out.release() # 出力動画ファイルをクローズ 




print('モジュール名：{}'.format(__name__))