#!/usr/bin/env python

import numpy as np
import cv2 as cv
from PIL import Image, ImageTk

cap : cv.VideoCapture = None
lower_red = np.array([160,20,70])
upper_red = np.array([190,255,255])

def start_camera():
    global cap
    cap = cv.VideoCapture(0)
    if not cap.isOpened():
        print("Camera failed to initialize.")
        cap = None
        return
    

def get_virtual_position():
    global cap
    if cap == None:
        print("Camera not initialized.")
        return
    ret, frame = cap.read()
    if not ret:
        print("Frame failed to recieve.")
        return
    hsv_frame = cv.cvtColor(frame, cv.COLOR_BGR2HSV_FULL)
    
    isolated_frame = cv.inRange(hsv_frame, lower_red, upper_red)
    cv.imshow("not red", frame)
    cv.imshow("red", isolated_frame)


def end_camera():
    global cap
    cap.release()

start_camera()
while True:
    get_virtual_position()
    if ord("q") == cv.waitKey(1):
        end_camera()
        break