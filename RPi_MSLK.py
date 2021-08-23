import socket
import time
from picamera import PiCamera
import cv2
import numpy as np
from imutils.video import VideoStream
import imagezmq
import socket
import sys

#pridobivanje ip računalnika
ip_pc=sys.argv[1]

#priprava za pišiljanje podatkov
sender = imagezmq.ImageSender(connect_to = "tcp://"+ip_pc+":5555")

#določanje resolucije slike
res=(1088,720)
camera = PiCamera(resolution=res,framerate=20)
#Nastavljanje kamere
camera.iso=100
time.sleep(2)
camera.exposure_compensation=10
camera.shutter_speed = 20000 
camera.exposure_mode = "off"
g = camera.awb_gains
camera.awb_mode = "off"
camera.awb_gains = g



#povezovanje soceta
soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
soc.connect((ip_pc, 5577))

#globalne spremenljivke
ROI=[]
threshold=175
#priprava slike za opencv
image = np.empty(res[0]*res[1]*3,dtype=np.uint8)

while True:
    #branje sporočila iz PC
    msg = soc.recv(32)
    msg = msg.decode("utf-8")
    msg = msg.split(",")
    #zajem slike iz kamere
    camera.capture(image,"bgr",use_video_port=True)
    image=image.reshape((res[1],res[0],3))
    
    #določanje ROI
    if len(ROI)==4:
        imageROI=image[ROI[1]:ROI[3],ROI[0]:ROI[2]]
    else:
        imageROI=image

    #razdelitev slike na različne barvne kanale
    b,g,r = cv2.split(imageROI)
    
    #določanje thresholda na rdečem kanalu
    ret, mask = cv2.threshold(r,threshold,255,cv2.THRESH_TOZERO)
    
    #iskanje žarka
    center = None
    countours = cv2.findContours(mask, cv2.RETR_EXTERNAL,
                                 cv2.CHAIN_APPROX_SIMPLE)[-2]
    # only proceed if at least one contour was found
    if len(countours) > 0:
        c = max(countours, key=cv2.contourArea)
        ((x, y), radius) = cv2.minEnclosingCircle(c)
        if len(ROI)==4:
            x = x + ROI[0]
            y = y + ROI[1]
        moments = cv2.moments(c)
        if moments["m00"] > 0 and len(ROI)==4:
            center = int(moments["m10"] / moments["m00"])+ ROI[0], \
                     int(moments["m01"] / moments["m00"])+ ROI[1]
        elif moments["m00"] > 0:
            center = int(moments["m10"] / moments["m00"]), \
                     int(moments["m01"] / moments["m00"])
        else:
            center = int(x), int(y)

        # only proceed if the radius meets a minimum size
        if  radius < 30:
            # draw the circle and centroid on the frame,
            cv2.circle(image, (int(x), int(y)), int(radius),
                       (0, 255, 255), 2)
            cv2.circle(image, center, 5, (0, 0, 255), -1)
    
    #vračanje ustreznih podatkov glede na zahtevo PC
    if msg[0] == "loc":
        print("pšiljam lokacijo")
        center = str(center)
        soc.send(bytes(center,"utf-8"))
        print(center)
    elif msg[0] == "img":
        print("pošljam sliko")
        sender.send_image(str(np.shape(imageROI)),image)
    elif msg[0] == "msk":
        print("pošljam sliko")
        sender.send_image(str(threshold),mask)
    elif msg[0] == "roi":
        roi=msg[1].split(":")
        ROI=[]
        for i in roi:
            ROI.append(int(i))
    elif msg[0] == "nst":
        nst=msg[1].split(":")
        camera.iso = int(nst[0])
        camera.shutter_speed = int(nst[1])
        threshold = int(nst[2])
    elif msg[0] == "end":
        break
    else:
        print("Nepoznan ukaz")