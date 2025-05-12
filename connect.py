import asyncio
from bleak import BleakClient, BleakGATTCharacteristic

import logging
logging.basicConfig(level=logging.DEBUG)

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

def callback(sender: BleakGATTCharacteristic, data: bytearray):
    print(f"{sender}: {str(data)}")

async def test():
    print("CONNECTING!")
    await client.connect()
    print("CONNECTED!")
    print("SETTING UP NOTIF STREAM")
    await client.start_notify(MODEL_NBR_UUID, callback=callback)
    print("OBTAINING DATA")
    print("DISCONNECTING!")
    await client.disconnect()
    print("DISCONNECTED!")

if __name__ == "__main__":
    print("TESTING CONNECTIVITY")
    asyncio.run(test())