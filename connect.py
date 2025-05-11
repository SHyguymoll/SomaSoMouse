import asyncio
from bleak import BleakClient, BleakGATTCharacteristic

address = "f8:2e:0c:a6:53:bf"
MODEL_NBR_UUID = "FFE1"

async def main(address):
    async with BleakClient(address) as client:
        model_number = await client.read_gatt_char(MODEL_NBR_UUID)
        print("Model Number: {0}".format("".join(map(chr, model_number))))
        print("Available Services: {0}".format(str(client.services.get_service("FFE0"))))
        #print("Now pairing...")
        #await client.pair()
        print("Starting notifs...")
        await client.start_notify(MODEL_NBR_UUID, callback)
        print("Recieving frames...")
        await check_frames()
        print("Disconnecting...")
        #await client.unpair()

frames_recieved = 0
async def check_frames():
    global frames_recieved
    while frames_recieved < 5:
        pass
    return


def callback(sender: BleakGATTCharacteristic, data: bytearray):
        global frames_recieved
        print(f"{sender}: {data}")
        frames_recieved += 1


asyncio.run(main(address))