
from enum import Enum
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
FINGER_ACCEL_HEADER = bytearray(b'\xF2\xF2')
GYRO_HEADER = bytearray(b'\xF3\xF3')
EXTRA_HEADER = bytearray(b'\xF4\xF4')

Window.size = (640, 480)

PLEASE_WAIT = "Connection Failed!\nPlease Wait..."
CONNECTING = "Connecting..."
CONNECT_AVAILABLE = "Connect to Glove"
DISCONNECT_AVAILABLE = "Disconnect"
DISCONNECTING = "Disconnecting..."
GLOVE_RECALIBRATING = "Glove Re-calibrating..."


class Hand(FloatLayout):
    CLOSED = 100.0
    OPEN = 200.0
    class Modes(Enum):
        ACCEL_XY = 0
        ACCEL_ZY = 1
        ACCEL_ZX = 2
        GYRO_XY = 3
        GYRO_ZY = 4
        GYRO_ZX = 5

    
    mode = Modes.ACCEL_XY
    invert_hor = False
    invert_ver = False

    def mode_is_accel(self) -> bool:
        return self.mode in [self.Modes.ACCEL_XY, self.Modes.ACCEL_ZY, self.Modes.ACCEL_ZX]
    
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
        
    
    def update_hand(self, is_accel : bool, new_pos : tuple[float, float], thu_s : float, poi_s : float, mid_s : float, rin_s : float, pin_s : float):
        if new_pos is not None and self.mode_is_accel() == is_accel:
            new_pos = (new_pos[0] * (-1 if self.invert_hor else 1), new_pos[1] * (-1 if self.invert_ver else 1))
            Logger.info(str(new_pos) + " " + str(is_accel))
            if is_accel:
                self.pal.pos = (new_pos[0] * 1000 + Window.width / 2., new_pos[1] * 1000 + Window.height / 2.)
            else:
                self.pal.pos = (self.pal.pos[0] + (new_pos[0] * 0.01), self.pal.pos[1] + (new_pos[1] * 0.01))
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

class GloveWindowApp(App):
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
        # radio buttons for handling how the glove values are interpreted
        # use accelerometer or gyroscope
        self.use_accel = ToggleButton(text="Accelerometer", group="interp mode", state="down", size_hint = (1, .125), allow_no_selection = False)
        self.use_accel.bind(on_press=self.change_mode)
        self.use_gyro = ToggleButton(text="Gyroscope Velocity", group="interp mode", size_hint = (1, .125), allow_no_selection = False)
        self.use_gyro.bind(on_press=self.change_mode)
        # use XY, ZY, or ZX
        self.used_values = BoxLayout(size_hint = (1, .125), spacing = 5, padding = 5)
        self.xy_but = ToggleButton(text="XY", group="move values", state="down", size_hint = (.125, 1), allow_no_selection = False)
        self.xy_but.bind(on_press=self.change_mode)
        self.zy_but = ToggleButton(text="ZY", group="move values", size_hint = (.125, 1), allow_no_selection = False)
        self.zy_but.bind(on_press=self.change_mode)
        self.zx_but = ToggleButton(text="ZX", group="move values", size_hint = (.125, 1), allow_no_selection = False)
        self.zx_but.bind(on_press=self.change_mode)
        # invert horizontal and vertical
        self.invert_horizontal = ToggleButton(text="Invert Horizontal", size_hint = (1, .125))
        self.invert_horizontal.bind(state=self.invert_dir)
        self.invert_vertical = ToggleButton(text="Invert Vertical", size_hint = (1, .125))
        self.invert_vertical.bind(state=self.invert_dir)
        # add buttons
        self.used_values.add_widget(self.xy_but)
        self.used_values.add_widget(self.zy_but)
        self.used_values.add_widget(self.zx_but)
        self.layout_side.add_widget(self.use_accel)
        self.layout_side.add_widget(self.use_gyro)
        self.layout_side.add_widget(self.used_values)
        self.layout_side.add_widget(self.invert_horizontal)
        self.layout_side.add_widget(self.invert_vertical)
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

    def change_mode(self, instance):
        match instance:
            case self.use_accel:
                match self.hand.mode:
                    case self.hand.Modes.GYRO_XY:
                        self.line("Changed mode to ACCEL, XY")
                        self.hand.mode = self.hand.Modes.ACCEL_XY
                    case self.hand.Modes.GYRO_ZY:
                        self.line("Changed mode to ACCEL, ZY")
                        self.hand.mode = self.hand.Modes.ACCEL_ZY
                    case self.hand.Modes.GYRO_ZX:
                        self.line("Changed mode to ACCEL, ZX")
                        self.hand.mode = self.hand.Modes.ACCEL_ZX
            case self.use_gyro:
                match self.hand.mode:
                    case self.hand.Modes.ACCEL_XY:
                        self.line("Changed mode to GYRO, XY")
                        self.hand.mode = self.hand.Modes.GYRO_XY
                    case self.hand.Modes.ACCEL_ZY:
                        self.line("Changed mode to GYRO, ZY")
                        self.hand.mode = self.hand.Modes.GYRO_ZY
                    case self.hand.Modes.ACCEL_ZX:
                        self.line("Changed mode to GYRO, ZX")
                        self.hand.mode = self.hand.Modes.GYRO_ZX
            case self.xy_but:
                self.line(f"Changed mode to {"ACCEL" if self.hand.mode_is_accel() else "GYRO"}, XY")
                self.hand.mode = self.hand.Modes.ACCEL_XY if self.hand.mode_is_accel() else self.hand.Modes.GYRO_XY
            case self.zy_but:
                self.line(f"Changed mode to {"ACCEL" if self.hand.mode_is_accel() else "GYRO"}, ZY")
                self.hand.mode = self.hand.Modes.ACCEL_ZY if self.hand.mode_is_accel() else self.hand.Modes.GYRO_ZY
            case self.zx_but:
                self.line(f"Changed mode to {"ACCEL" if self.hand.mode_is_accel() else "GYRO"}, ZX")
                self.hand.mode = self.hand.Modes.ACCEL_ZX if self.hand.mode_is_accel() else self.hand.Modes.GYRO_ZX
    
    def invert_dir(self, instance, state):
        match instance:
            case self.invert_horizontal:
                self.hand.invert_hor = state == "down"
            case self.invert_vertical:
                self.hand.invert_ver = state == "down"

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
            self.hand.update_hand(None, None, thumb, pointer, middle, ring, None)
        elif data.startswith(FINGER_ACCEL_HEADER):
            if self.connect_disconnect_button.text == GLOVE_RECALIBRATING and self.calibrate_flag == True:
                self.connect_disconnect_button.text = DISCONNECT_AVAILABLE
                self.calibrate_flag = False
            pinky, ax1, ay1, az1 = struct.unpack_from("4f", data, 2)
            #self.line(f"pos = ({"{0:.2g}".format(ax1)}, {"{0:.2g}".format(ay1)}, {"{0:.2g}".format(az1)})")
            match self.hand.mode:
                case self.hand.Modes.ACCEL_XY:
                    self.hand.update_hand(True, (ax1, -ay1), None, None, None, None, pinky)
                case self.hand.Modes.ACCEL_ZY:
                    self.hand.update_hand(True, (az1, -ay1), None, None, None, None, pinky)
                case self.hand.Modes.ACCEL_ZX:
                    self.hand.update_hand(True, (az1, ax1), None, None, None, None, pinky)
        elif data.startswith(GYRO_HEADER):
            if self.connect_disconnect_button.text == GLOVE_RECALIBRATING and self.calibrate_flag == True:
                self.connect_disconnect_button.text = DISCONNECT_AVAILABLE
                self.calibrate_flag = False
            gy1, gx1, gz1, radX = struct.unpack_from("4f", data, 2)
            #self.line(f"vel = ({"{0:.2g}".format(gx1)}, {"{0:.2g}".format(gy1)}, {"{0:.2g}".format(gz1)}) inx = {"{0:.2g}".format(radX)}")
            match self.hand.mode:
                case self.hand.Modes.GYRO_XY:
                    self.hand.update_hand(False, (gx1, -gy1), None, None, None, None, None)
                case self.hand.Modes.GYRO_ZY:
                    self.hand.update_hand(False, (gz1, -gy1), None, None, None, None, None)
                case self.hand.Modes.GYRO_ZX:
                    self.hand.update_hand(False, (gz1, gx1), None, None, None, None, None)
        elif data.startswith(EXTRA_HEADER):
            if self.connect_disconnect_button.text == GLOVE_RECALIBRATING and self.calibrate_flag == True:
                self.connect_disconnect_button.text = DISCONNECT_AVAILABLE
                self.calibrate_flag = False
            radY = struct.unpack_from("f", data, 2)
            #self.line(f"iny = {radY}")
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
            Clock.schedule_once(self.reset_glove_text, 1.0)
        except bleak.exc.BleakError:
            self.connect_disconnect_button.text = PLEASE_WAIT
            self.line("Glove failed to connect.", True)
            Clock.schedule_once(self.reset_glove_text, 1.5)


    
    async def disconnect(self, instance):
        self.disc_purposeful = True
        instance.text = DISCONNECTING
        await self.client.disconnect()
        instance.bind(on_press=self.connect_button)
        instance.text = CONNECT_AVAILABLE

async def main(app : GloveWindowApp):
    await app.async_run("asyncio")
    # for safety, incase glove was connected, disconnect now
    await app.client.disconnect()

if __name__ == "__main__":
    Logger.setLevel(logging.DEBUG)

app = GloveWindowApp()
asyncio.run(main(app))
