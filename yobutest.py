import videocapture
import time
import threading

stop_event = threading.Event()
thread1 = threading.Thread(target=videocapture.Startcapture, args=(stop_event,))

thread1.start()



print("カウント開始")
time.sleep(3)

stop_event.set()
# 終了待ち（重要）
thread1.join()

print("全部終了")


# def Start():
#     videocapture.Startcapture()

# print("大気開始")
# time.sleep(3)

# videocapture.Stopcapture()