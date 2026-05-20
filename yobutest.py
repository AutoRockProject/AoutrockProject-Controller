import videocapture
import time
import threading

stop_event = threading.Event()
thread1 = threading.Thread(target=videocapture.Startcapture, args=(stop_event,))

thread1.start()

input("Enter押して終了")

stop_event.set()

# 終了待ち（重要）
thread1.join()

print("全部終了")