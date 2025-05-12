import asyncio
from bleak import BleakClient, BleakGATTCharacteristic

#import logging
#logging.basicConfig(level=logging.DEBUG)

address = "f8:2e:0c:a6:53:bf"
MODEL_NBR_UUID = "FFE1"

client = BleakClient(address)


async def try_connect():
    await client.connect()

async def begin_notif():
    print("CONNECTING!")
    await client.start_notify(MODEL_NBR_UUID, callback=callback)
    print("CONNECTED!")

async def disconnect_client():
   print("DISCONNECTING!")
   await client.disconnect()
   print("DISCONNECTED!")

FINGER1_HEADER = bytearray(b'\xF1\xF1')
FINGER2_HEADER = bytearray(b'\xF2\xF2')
ROTATION_HEADER = bytearray(b'\xF3\xF3')
EXTRA_HEADER = bytearray(b'\xF4\xF4')

import struct

def callback(sender: BleakGATTCharacteristic, data: bytearray):
    if data.startswith(FINGER1_HEADER):
        thumb, pointer, middle, ring = struct.unpack_from("4f", data, 2)
        print(f"thumb = {thumb}, pointer = {pointer}, middle = {middle}, ring = {ring}")
    elif data.startswith(FINGER2_HEADER):
        pinky, ax1, ay1, az1 = struct.unpack_from("4f", data, 2)
        print(f"pinky = {pinky}, acceleration = ({ax1}, {ay1}, {az1})")
    elif data.startswith(ROTATION_HEADER):
        gx1, gy1, gz1, radX = struct.unpack_from("4f", data, 2)
        print(f"angular velocity = ({gx1}, {gy1}, {gz1}), inclination x = {radX}")
    elif data.startswith(EXTRA_HEADER):
        radY = struct.unpack_from("f", data, 2)
        print(f"inclination y = {radY}")
    else:
        print("!!!!malformed packet!!!!")

async def test():
    print("CONNECTING!")
    await client.connect()
    print("CONNECTED!")
    print("SETTING UP NOTIF STREAM")
    await client.start_notify(MODEL_NBR_UUID, callback=callback)
    print("OBTAINING DATA")
    await asyncio.sleep(10.0)
    print("DISCONNECTING!")
    await client.disconnect()
    print("DISCONNECTED!")

if __name__ == "__main__":
    print("TESTING CONNECTIVITY")
    asyncio.run(test())