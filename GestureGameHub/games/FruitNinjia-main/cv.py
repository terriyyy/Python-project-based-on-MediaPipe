import cv2
import numpy as np
import time
from imutils.video import WebcamVideoStream


def loop(cam,lower_red,upper_red,height,width):
    time.sleep(0.1)
    stop=0
    x, y = width // 2, height // 2  # 初始化x和y为屏幕中心
    frame = cam.read()
    hsv=cv2.cvtColor(frame,cv2.COLOR_BGR2HSV)
    mask=cv2.inRange(hsv,lower_red,upper_red)
    frame=cv2.bitwise_and(frame,frame,mask=mask)
    contours, hierarchy = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    area = []
    for k in range(len(contours)):
        area.append(cv2.contourArea(contours[k]))
    if area!=[]:
        max_idx = np.argmax(np.array(area))
        x,y,w,h = cv2.boundingRect(contours[max_idx]) # (x,y)是rectangle的左上角坐标， (w,h)是width和height
        frame = cv2.rectangle(frame,(x,y),(x+w,y+h),(0,255,0),2)
    
    cv2.imshow('frame', frame)
    k = cv2.waitKey(1)
    if k == ord('q'):
        stop=1
    return x+w//2,y+h//2,stop

    
def main(pos):
    cam = WebcamVideoStream(src=0).start()

    frame = cam.read()
    imgInfo = frame.shape
    height = imgInfo[0]
    width = imgInfo[1]
    
    lower_red=np.array([120,100,100])
    upper_red=np.array([180,255,255])
    while(1):
        x,y,stop=loop(cam,lower_red,upper_red,height,width)
        pos[0]=[x,y]
        if stop:
            break
        

if __name__ == '__main__':
    from multiprocessing import Manager
    mgr = Manager()
    pos = mgr.list()
    pos.append([300, 200])
    main(pos)
    
    