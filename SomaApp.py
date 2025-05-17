
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
#import renderer


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

PLEASE_WAIT = "Connection Failed!\nPlease Wait..."
CONNECTING = "Connecting..."
CONNECT_AVAILABLE = "Connect to Glove"
DISCONNECT_AVAILABLE = "Disconnect"
DISCONNECTING = "Disconnecting..."
GLOVE_RECALIBRATING = "Glove Re-calibrating..."

class FingerState(Rectangle):
    CLOSED = 100.0
    OPEN = 200.0
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.stretch = self.OPEN
    
    def set_stretch(self):
        self.size = (10., (self.stretch * 10.0) / self.CLOSED)


class Hand(FloatLayout):
    CLOSED = 100.0
    OPEN = 200.0
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas:
            Color(1., 1., 1.)
            self.pal = Rectangle(size=(40, 30), pos=(Window.size[0] / 2., Window.size[1] / 2.))
            self.thu = Rectangle(size=(10, 20), pos=(self.pal.pos[0] - 20, self.pal.pos[1] + 0))
            self.poi = Rectangle(size=(10, 20), pos=(self.pal.pos[0] - 10, self.pal.pos[1] + 35))
            self.mid = Rectangle(size=(10, 20), pos=(self.pal.pos[0] + 5, self.pal.pos[1] + 35))
            self.rin = Rectangle(size=(10, 20), pos=(self.pal.pos[0] + 20, self.pal.pos[1] + 35))
            self.pin = Rectangle(size=(10, 20), pos=(self.pal.pos[0] + 35, self.pal.pos[1] + 35))
        
    
    def update_hand(self, new_pos : tuple[float, float], thu_s : float, poi_s : float, mid_s : float, rin_s : float, pin_s : float):
        if new_pos is not None:
            self.pal.pos = (new_pos[0] * 1000, new_pos[1] * 1000)
            self.thu.pos = (self.pal.pos[0] - 20, self.pal.pos[1] + 0)
            self.poi.pos = (self.pal.pos[0] - 10, self.pal.pos[1] + 35)
            self.mid.pos = (self.pal.pos[0] + 5, self.pal.pos[1] + 35)
            self.rin.pos = (self.pal.pos[0] + 20, self.pal.pos[1] + 35)
            self.pin.pos = (self.pal.pos[0] + 35, self.pal.pos[1] + 35)
        if thu_s is not None:
            self.thu.size = (10, (thu_s * 10.) / self.CLOSED)
        if poi_s is not None:
            self.poi.size = (10, (poi_s * 10.) / self.CLOSED)
        if mid_s is not None:
            self.mid.size = (10, (mid_s * 10.) / self.CLOSED)
        if rin_s is not None:
            self.rin.size = (10, (rin_s * 10.) / self.CLOSED)
        if pin_s is not None:
            self.pin.size = (10, (pin_s * 10.) / self.CLOSED)


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
        self.disc_purposeful = False
        self.client = bleak.BleakClient(address, self.glove_disconnected)

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
        self.min_on_exit = ToggleButton(text="Minimize on Exit", group="on exit", size_hint = (1, .25))
        self.close_on_exit = ToggleButton(text="Close on Exit", group="on exit", state="down", size_hint = (1, .25))
        self.layout_side.add_widget(self.min_on_exit)
        self.layout_side.add_widget(self.close_on_exit)
        # button for connecting and disconnecting, changes depending on if glove is connected
        self.connect_disconnect_button = Button(text=CONNECT_AVAILABLE, size_hint = (1, .125))
        self.connect_disconnect_button.bind(on_press=self.connect_button)
        self.layout_side.add_widget(self.connect_disconnect_button)
        # debug scroll for debugging (who could've guessed)
        self.scrollview = ScrollView(do_scroll_x=False, scroll_type=["bars", "content"])
        self.layout_side.add_widget(self.scrollview)
        self.label = Label(font_size="10sp")
        self.scrollview.add_widget(self.label)
        # flag for calibrating glove
        self.calibrate_flag = False
        return self.layout_main

    def connect_button(self, instance):
        if instance.text != CONNECT_AVAILABLE:
            return
        asyncio.create_task(self.connect(instance))
    
    def disconnect_button(self, instance):
        if instance.text != DISCONNECT_AVAILABLE:
            return
        asyncio.create_task(self.disconnect(instance))

    def reset_glove_text(self, _dt):
        self.connect_disconnect_button.text = CONNECT_AVAILABLE
    
    def glove_disconnected(self, client : bleak.BleakClient):
        if self.disc_purposeful:
            return
        self.line("Glove lost connection!")
    
    def line(self, text, empty=False):
        Logger.info(text)
        if self.label is None:
            return
        text += "\n"
        if empty:
            self.label.text = text
        else:
            self.label.text += text
            if len(self.label.text.split("\n")) > 5:
                self.label.text = "\n".join(self.label.text.split("\n")[1:])

    def on_stop(self):
        self.running = False

    def callback(self, sender: bleak.BleakGATTCharacteristic, data: bytearray):
        if data.startswith(FINGER1_HEADER):
            if self.connect_disconnect_button.text == GLOVE_RECALIBRATING and self.calibrate_flag == True:
                self.connect_disconnect_button.text = DISCONNECT_AVAILABLE
                self.calibrate_flag = False
            thumb, pointer, middle, ring = struct.unpack_from("4f", data, 2)
            #self.line(f"thumb = {thumb}, pointer = {pointer}, middle = {middle}, ring = {ring}")
            self.hand.update_hand(None, thumb, pointer, middle, ring, None)
        elif data.startswith(FINGER2_HEADER):
            if self.connect_disconnect_button.text == GLOVE_RECALIBRATING and self.calibrate_flag == True:
                self.connect_disconnect_button.text = DISCONNECT_AVAILABLE
                self.calibrate_flag = False
            pinky, ax1, ay1, az1 = struct.unpack_from("4f", data, 2)
            self.line(f"pos = ({"{0:.2g}".format(ax1)}, {"{0:.2g}".format(ay1)}, {"{0:.2g}".format(az1)})")
            self.hand.update_hand((ax1, -ay1), None, None, None, None, pinky)
        elif data.startswith(ROTATION_HEADER):
            if self.connect_disconnect_button.text == GLOVE_RECALIBRATING and self.calibrate_flag == True:
                self.connect_disconnect_button.text = DISCONNECT_AVAILABLE
                self.calibrate_flag = False
            gx1, gy1, gz1, radX = struct.unpack_from("4f", data, 2)
            #self.transf.rot["x"], self.transf.rot["y"], self.transf.rot["z"], self.transf.inclin["x"] = gx1, gy1, gz1, radX
            self.line(f"vel = ({"{0:.2g}".format(gx1)}, {"{0:.2g}".format(gy1)}, {"{0:.2g}".format(gz1)}) inx = {"{0:.2g}".format(radX)}")
        elif data.startswith(EXTRA_HEADER):
            if self.connect_disconnect_button.text == GLOVE_RECALIBRATING and self.calibrate_flag == True:
                self.connect_disconnect_button.text = DISCONNECT_AVAILABLE
                self.calibrate_flag = False
            radY = struct.unpack_from("f", data, 2)
            #self.transf.inclin["y"] = radY
            self.line(f"iny = {radY}")
        elif data == b'-----CALIBRATING----':
            self.connect_disconnect_button.text = GLOVE_RECALIBRATING
            self.calibrate_flag = True
            pass
        else:
            self.line("!!!!malformed packet!!!!")
    
    async def connect(self, instance):
        self.line(f"Attempting Connect", True)
        instance.text = CONNECTING
        try:
            await self.client.connect()
            await self.client.start_notify("FFE1", self.callback)
            self.disc_purposeful = False
            instance.text = DISCONNECT_AVAILABLE
            instance.bind(on_press=self.disconnect_button)
        except bleak.exc.BleakDeviceNotFoundError:
            self.connect_disconnect_button.text = PLEASE_WAIT
            self.line("Glove was not found.", True)
            Clock.schedule_once(self.reset_glove_text, 3.0)
    
    async def disconnect(self, instance):
        self.disc_purposeful = True
        instance.text = DISCONNECTING
        await self.client.disconnect()
        instance.bind(on_press=self.connect_button)
        instance.text = CONNECT_AVAILABLE

async def main(app : ExampleApp):
    await app.async_run("asyncio")
    # for safety, incase glove was connected, disconnect now
    await app.client.disconnect()

if __name__ == "__main__":
    Logger.setLevel(logging.DEBUG)

app = ExampleApp()
asyncio.run(main(app))
