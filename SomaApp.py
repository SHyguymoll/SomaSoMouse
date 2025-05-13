
from kivy.app import App

from kivy.core.window import Window
Window.size = (640, 480)
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.dropdown import DropDown
from kivy.uix.button import Button
from kivy.uix.anchorlayout import AnchorLayout
import objloader


# bind bleak's python logger into kivy's logger before importing python module using logging
from kivy.logger import Logger
import logging

logging.Logger.manager.root = Logger

import asyncio
import bleak

address = "f8:2e:0c:a6:53:bf"

import struct

FINGER1_HEADER = bytearray(b'\xF1\xF1')
FINGER2_HEADER = bytearray(b'\xF2\xF2')
ROTATION_HEADER = bytearray(b'\xF3\xF3')
EXTRA_HEADER = bytearray(b'\xF4\xF4')

class FingerState():
    CLOSED = 100.0
    OPEN = 200.0
    def __init__(self):
        self.thu : float = self.OPEN
        self.poi : float = self.OPEN
        self.mid : float = self.OPEN
        self.rin : float = self.OPEN
        self.pin : float = self.OPEN

class PositionRotationState():
    def __init__(self):
        self.accel = { "x": 0.0, "y": 0.0, "z": 0.0, }
        self.rot = { "x": 0.0, "y": 0.0, "z": 0.0, }
        self.inclin = { "x": 0.0, "y": 0.0, }

class LabelWithDropdown():
    def __init__(self, l_text : str, drp_itms : list[str], drp_label : str):
        self.parent = AnchorLayout(anchor_x='center', anchor_y='top')
        self.box = BoxLayout(spacing=5)
        self.label = Label(text=l_text, font_size="10sp")
        self.drdown = DropDown()
        for drp_itm in drp_itms:
            btn = Button(text=drp_itm, size_hint=(1, None), height=24)
            btn.bind(on_release=lambda btn: self.drdown.select(btn.text))
            self.drdown.add_widget(btn)
        self.drdownbutton = Button(text=drp_label, size_hint = (1, None))
        self.drdown.bind(on_select=lambda instance, x: setattr(self.drdownbutton, 'text', x))
        self.drdown.dismiss()
        self.box.add_widget(self.label)
        self.box.add_widget(self.drdown)
        self.box.add_widget(self.drdownbutton)
        self.parent.add_widget(self.box)

class ExampleApp(App):
    def __init__(self):
        super().__init__()
        self.label = None
        self.running = True
        self.client = bleak.BleakClient(address)
        self.hand = FingerState()
        self.transf = PositionRotationState()

    def build(self):
        self.layout_main = BoxLayout()
        self.button_placeholder = Button(text="placeholder", size_hint = (.7, 1))
        self.layout_side = BoxLayout(orientation="vertical", size_hint = (.3, 1))
        self.layout_main.add_widget(self.button_placeholder)
        self.layout_main.add_widget(self.layout_side)
        self.scrn_dropdown = LabelWithDropdown("Current Screen", ["Screen A", "Screen B", "Screen C"], "Screen A")
        self.layout_side.add_widget(self.scrn_dropdown.parent)
        self.scrollview = ScrollView(do_scroll_x=False, scroll_type=["bars", "content"], size_hint = (1, .25))
        self.layout_side.add_widget(self.scrollview)
        self.label = Label(font_size="10sp")
        self.scrollview.add_widget(self.label)
        return self.layout_main

    def line(self, text, empty=False):
        #Logger.info("example:" + text)
        if self.label is None:
            return
        text += "\n"
        if empty:
            self.label.text = text
        else:
            self.label.text += text

    def on_stop(self):
        self.running = False


    def callback(self, sender: bleak.BleakGATTCharacteristic, data: bytearray):
        if data.startswith(FINGER1_HEADER):
            thumb, pointer, middle, ring = struct.unpack_from("4f", data, 2)
            self.hand.thu, self.hand.poi, self.hand.mid, self.hand.rin = thumb, pointer, middle, ring
            self.line(f"thumb = {thumb}, pointer = {pointer}, middle = {middle}, ring = {ring}")
        elif data.startswith(FINGER2_HEADER):
            pinky, ax1, ay1, az1 = struct.unpack_from("4f", data, 2)
            self.hand.pin, self.transf.accel["x"], self.transf.accel["y"], self.transf.accel["z"] = pinky, ax1, ay1, az1
            self.line(f"pinky = {pinky}, acceleration = ({ax1}, {ay1}, {az1})")
        elif data.startswith(ROTATION_HEADER):
            gx1, gy1, gz1, radX = struct.unpack_from("4f", data, 2)
            self.transf.rot["x"], self.transf.rot["y"], self.transf.rot["z"], self.transf.inclin["x"] = gx1, gy1, gz1, radX
            self.line(f"angular velocity = ({gx1}, {gy1}, {gz1}), inclination x = {radX}")
        elif data.startswith(EXTRA_HEADER):
            radY = struct.unpack_from("f", data, 2)
            self.transf.inclin["y"] = radY
            self.line(f"inclination y = {radY}")
        else:
            self.line("!!!!malformed packet!!!!")

    async def example(self):

        self.line(f"Connected")
        return
        await self.client.connect()
        await self.client.start_notify("FFE1", self.callback)

async def main(app):
    await asyncio.gather(app.async_run("asyncio"), app.example())
    await app.client.disconnect()


if __name__ == "__main__":
    Logger.setLevel(logging.DEBUG)


# app running on one thread with two async coroutines
app = ExampleApp()
asyncio.run(main(app))
