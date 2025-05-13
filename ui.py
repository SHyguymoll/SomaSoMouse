
from kivy.app import App

# from kivy.core.window import Window
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView

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

class ExampleApp(App):
    def __init__(self):
        super().__init__()
        self.label = None
        self.running = True
        self.client = bleak.BleakClient(address)

    def build(self):
        self.scrollview = ScrollView(do_scroll_x=False, scroll_type=["bars", "content"])
        self.label = Label(font_size="10sp")
        self.scrollview.add_widget(self.label)
        return self.scrollview

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


    def callback(self, sender, data):
        if data.startswith(FINGER1_HEADER):
            thumb, pointer, middle, ring = struct.unpack_from("4f", data, 2)
            self.line(f"thumb = {thumb}, pointer = {pointer}, middle = {middle}, ring = {ring}")
        elif data.startswith(FINGER2_HEADER):
            pinky, ax1, ay1, az1 = struct.unpack_from("4f", data, 2)
            self.line(f"pinky = {pinky}, acceleration = ({ax1}, {ay1}, {az1})")
        elif data.startswith(ROTATION_HEADER):
            gx1, gy1, gz1, radX = struct.unpack_from("4f", data, 2)
            self.line(f"angular velocity = ({gx1}, {gy1}, {gz1}), inclination x = {radX}")
        elif data.startswith(EXTRA_HEADER):
            radY = struct.unpack_from("f", data, 2)
            self.line(f"inclination y = {radY}")
        else:
            self.line("!!!!malformed packet!!!!")

    async def example(self):
        self.line(f"Connected")
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
