import videocapture
import time
import threading


thread1 = threading.Thread(target=videocapture.Startcapture, args=())
thread2 = threading.Thread(target=videocapture.Stopcapture, args=())

thread1.start()

# time.sleep(3)
print("thread2を開始")
thread2.start()

# 終了待ち（重要）
# thread1.join()
thread2.join()

print("全部終了")


# def Start():
#     videocapture.Startcapture()

# print("大気開始")
# time.sleep(3)

# videocapture.Stopcapture()