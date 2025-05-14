
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.label import Label
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.spinner import Spinner
from kivy.uix.button import Button
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.togglebutton import ToggleButton

from kivy.graphics import Color, Rectangle
import renderer


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


Window.size = (640, 480)

class FingerState(Rectangle):
    CLOSED = 100.0
    OPEN = 200.0
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.stretch = self.OPEN
    
    def set_stretch(self):
        self.size = (10., (self.stretch * 10.0) / self.CLOSED)

class PositionRotationState():
    def __init__(self):
        self.accel = { "x": 0.0, "y": 0.0, "z": 0.0, }
        self.rot = { "x": 0.0, "y": 0.0, "z": 0.0, }
        self.inclin = { "x": 0.0, "y": 0.0, }

class Hand(FloatLayout):
    CLOSED = 100.0
    OPEN = 200.0
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas:
            Color(1., 1., 1.)
            self.pal = Rectangle(size=(40, 30), pos=(self.width / 2.0 ,self.height / 2.0))
            self.thu = Rectangle(size=(10, 20), pos=(self.pal.pos[0] - 20, self.pal.pos[1] + 0))
            self.poi = Rectangle(size=(10, 20), pos=(self.pal.pos[0] - 10, self.pal.pos[1] + 35))
            self.mid = Rectangle(size=(10, 20), pos=(self.pal.pos[0] + 5, self.pal.pos[1] + 35))
            self.rin = Rectangle(size=(10, 20), pos=(self.pal.pos[0] + 20, self.pal.pos[1] + 35))
            self.pin = Rectangle(size=(10, 20), pos=(self.pal.pos[0] + 35, self.pal.pos[1] + 35))
        
    
    def position_hand(self, new_pos : tuple[float, float], thu_stretch : float, poi_stretch : float, mid_stretch : float, rin_stretch : float, pin_stretch : float):
        if new_pos is not None:
            self.pal.pos = (new_pos[0] * 1000, new_pos[1] * 1000)
            self.thu.pos = (self.pal.pos[0] - 20, self.pal.pos[1] + 0)
            self.poi.pos = (self.pal.pos[0] - 10, self.pal.pos[1] + 35)
            self.mid.pos = (self.pal.pos[0] + 5, self.pal.pos[1] + 35)
            self.rin.pos = (self.pal.pos[0] + 20, self.pal.pos[1] + 35)
            self.pin.pos = (self.pal.pos[0] + 35, self.pal.pos[1] + 35)
        if thu_stretch is not None:
            self.thu.size = (10, (thu_stretch * 10.) / self.CLOSED)
        if poi_stretch is not None:
            self.poi.size = (10, (poi_stretch * 10.) / self.CLOSED)
        if mid_stretch is not None:
            self.mid.size = (10, (mid_stretch * 10.) / self.CLOSED)
        if rin_stretch is not None:
            self.rin.size = (10, (rin_stretch * 10.) / self.CLOSED)
        if pin_stretch is not None:
            self.pin.size = (10, (pin_stretch * 10.) / self.CLOSED)


class LabelWithDropdown():
    def __init__(self, l_text : str, drp_itms : list[str], drp_label : str):
        self.parent = AnchorLayout(anchor_x='center', anchor_y='top', size_hint = (1, 0.125))
        self.box_h = BoxLayout(spacing=5)
        self.box_v = BoxLayout(orientation="vertical")
        self.label = Label(text=l_text, font_size="10sp")
        self.drdown = Spinner(
            # default value shown
            text=drp_label,
            # available values
            values=(drp_itms),
            size_hint = (1, 0.25),
        )
        self.drdown.bind(on_select=lambda instance, x: setattr(self.drdown, 'text', x))
        self.box_h.add_widget(self.label)
        self.box_v.add_widget(self.drdown)
        self.box_h.add_widget(self.box_v)
        self.parent.add_widget(self.box_h)

class ExampleApp(App):
    def __init__(self):
        super().__init__()
        self.label = None
        self.running = True
        self.client = bleak.BleakClient(address)
        #self.hand = FingerState()
        #self.transf = PositionRotationState()

    def build(self):
        #outer box
        self.layout_main = BoxLayout()
        # left side will show render of hand for visualization
        self.hand_space = RelativeLayout()
        self.hand = Hand(pos=(0,0))
        self.hand_space.add_widget(self.hand)
        #self.hand_render = renderer.Renderer(model_obj='Hand.obj')
        #Clock.schedule_interval(self.hand_render.update_glsl, 1 / 60.)
        # right side will be configuration options
        self.layout_side = BoxLayout(orientation="vertical", size_hint = (.3, 1), spacing=20, padding=10)
        self.layout_main.add_widget(self.hand_space)
        self.layout_main.add_widget(self.layout_side)
        # dropdown to control current screen mouse is on (impl tbd)
        self.scrn_dropdown = LabelWithDropdown("Current Screen", ['Screen A', 'Screen B', 'Screen C'], 'Screen A')
        self.layout_side.add_widget(self.scrn_dropdown.parent)
        # radio buttons for handling the exit button
        self.min_on_exit = ToggleButton(text="Minimize on Exit", group="on exit", state="down", size_hint = (1, .25))
        self.close_on_exit = ToggleButton(text="Close on Exit", group="on exit", size_hint = (1, .25))
        self.layout_side.add_widget(self.min_on_exit)
        self.layout_side.add_widget(self.close_on_exit)
        # button for connecting and disconnecting, changes depending on if glove is connected
        self.connect_disconnect_button = Button(text="Connect to Glove", size_hint = (1, .5))
        self.layout_side.add_widget(self.connect_disconnect_button)
        # debug scroll for debugging (who could've guessed)
        self.scrollview = ScrollView(do_scroll_x=False, scroll_type=["bars", "content"], size_hint = (1, .25))
        self.layout_side.add_widget(self.scrollview)
        self.label = Label(font_size="10sp")
        self.scrollview.add_widget(self.label)
        return self.layout_main

    def line(self, text, empty=False):
        Logger.info(text)
        #if self.label is None:
        #    return
        #text += "\n"
        #if empty:
        #    self.label.text = text
        #else:
        #    self.label.text += text

    def on_stop(self):
        self.running = False


    def callback(self, sender: bleak.BleakGATTCharacteristic, data: bytearray):
        if data.startswith(FINGER1_HEADER):
            thumb, pointer, middle, ring = struct.unpack_from("4f", data, 2)
            #self.line(f"thumb = {thumb}, pointer = {pointer}, middle = {middle}, ring = {ring}")
            self.hand.position_hand(None, thumb, pointer, middle, ring, None)
        elif data.startswith(FINGER2_HEADER):
            pinky, ax1, ay1, az1 = struct.unpack_from("4f", data, 2)
            self.line(f"pos = ({"{0:.2g}".format(ax1)}, {"{0:.2g}".format(ay1)}, {"{0:.2g}".format(az1)})")
            self.hand.position_hand((ax1, -ay1), None, None, None, None, pinky)
        elif data.startswith(ROTATION_HEADER):
            gx1, gy1, gz1, radX = struct.unpack_from("4f", data, 2)
            #self.transf.rot["x"], self.transf.rot["y"], self.transf.rot["z"], self.transf.inclin["x"] = gx1, gy1, gz1, radX
            self.line(f"vel = ({"{0:.2g}".format(gx1)}, {"{0:.2g}".format(gy1)}, {"{0:.2g}".format(gz1)})\ninx = {"{0:.2g}".format(radX)}")
        elif data.startswith(EXTRA_HEADER):
            radY = struct.unpack_from("f", data, 2)
            #self.transf.inclin["y"] = radY
            #self.line(f"inclination y = {radY}")
        else:
            self.line("!!!!malformed packet!!!!")

    async def example(self):
        self.line(f"Connected")
        await self.client.connect()
        await self.client.start_notify("FFE1", self.callback)

async def main(app : ExampleApp):
    await asyncio.gather(app.async_run("asyncio"), app.example())
    await app.client.disconnect()


if __name__ == "__main__":
    Logger.setLevel(logging.DEBUG)


# app running on one thread with two async coroutines
app = ExampleApp()
asyncio.run(main(app))
