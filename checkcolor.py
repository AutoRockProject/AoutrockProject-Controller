import cv2

# 道着の色を調べたいフレームの画像パスを入れてね
img = cv2.imread("jumpflame.png")
hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

def on_click(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        h, s, v = hsv[y, x]
        print(f"クリックした場所のHSV(OpenCV形式) → H:{h} S:{s} V:{v}")

cv2.namedWindow("frame")
cv2.setMouseCallback("frame", on_click)
while True:
    cv2.imshow("frame", img)
    if cv2.waitKey(1) == 27:  # ESCで終了
        break
cv2.destroyAllWindows()