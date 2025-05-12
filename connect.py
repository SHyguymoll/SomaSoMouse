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

FINGER_HEADER = bytearray(b'\xF1\xF1')
FINGER_STRUCT_LEN = 22
POSITION_HEADER = bytearray(b'\xF0\xF0')
POSITION_STRUCT_LEN = 34
finger_seen = 0
position_seen = 0

print(len(FINGER_HEADER))
buffer = bytearray()

import struct

def callback(sender: BleakGATTCharacteristic, data: bytearray):
    print(f"{len(data)} {str(data)}")
    return

    global finger_seen, position_seen
    for b in data:
        buffer.append(b)
        if finger_seen > 0:
            finger_seen -= 1
            if finger_seen == 0:
                thumb, pointer, middle, ring, pinky = struct.unpack_from("5f", buffer)
                print(f"thumb = {thumb}, pointer = {pointer}, middle = {middle}, ring = {ring}, pinky = {pinky}")
                buffer.clear()
        if position_seen > 0:
            position_seen -= 1
            if position_seen == 0:
                ax1, ay1, az1, gx1, gy1, gz1, radX, radY = struct.unpack_from("8f", buffer)
                print(f"acceleration = ({ax1}, {ay1}, {az1}), angular velocity = ({gx1}, {gy1}, {gz1}), inclination = ({radX}, {radY})")
                buffer.clear()
        elif len(buffer) == 2:
            if buffer == FINGER_HEADER:
                print("finger found")
                finger_seen = FINGER_STRUCT_LEN - len(FINGER_HEADER)
            elif buffer == POSITION_HEADER:
                print("position found")
                position_seen = POSITION_STRUCT_LEN - len(POSITION_HEADER)
            print("neither found, worrying")
            buffer.clear()

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