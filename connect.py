import asyncio
from bleak import BleakClient

address = "f8:2e:0c:a6:53:bf"
MODEL_NBR_UUID = "FFE1"

async def main(address):
    async with BleakClient(address) as client:
        model_number = await client.read_gatt_char(MODEL_NBR_UUID)
        print("Model Number: {0}".format("".join(map(chr, model_number))))

asyncio.run(main(address))