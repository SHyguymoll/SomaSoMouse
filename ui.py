
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
        Logger.info("example:" + text)
        if self.label is None:
            return
        text += "\n"
        if empty:
            self.label.text = text
        else:
            self.label.text += text

    def on_stop(self):
        self.running = False


    def callback(self,sender, data):
        self.line(f"{str(data)}")

    async def example(self):
        self.line(f"Connected")
        await self.client.connect()
        await self.client.start_notify("FFE1", self.callback)

async def main(app):
    await asyncio.gather(app.async_run("asyncio"), app.example())


if __name__ == "__main__":
    Logger.setLevel(logging.DEBUG)


# app running on one thread with two async coroutines
app = ExampleApp()
asyncio.run(main(app))
