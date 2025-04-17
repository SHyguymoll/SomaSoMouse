#!/usr/bin/env python

import numpy as np
import cv2 as cv
import tkinter as tk
from PIL import Image, ImageTk

cap : cv.VideoCapture = None

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

def end_camera():
    global cap
    cap.release()