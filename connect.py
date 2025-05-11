import asyncio
from enum import Enum
from bleak import BleakClient, BleakGATTCharacteristic

address = "f8:2e:0c:a6:53:bf"
MODEL_NBR_UUID = "FFE1"

class ConnectState(Enum):
    NO_CONNECT = 0
    CONNECT_INPROG = 1
    CLIENT_CONNECTED = 2
    DISCONNECT_INPROG = 3
    EXIT = 4

client : BleakClient = None
state : ConnectState = ConnectState.NO_CONNECT

async def main(addr):
    global state, client
    print("INITIALIZING!")
    while True:
        match state:
            case ConnectState.CONNECT_INPROG:
                print("CONNECTING!")
                client = BleakClient(addr)
                print("Available Services: {0}".format(str(client.services.get_service("FFE0"))))
                await client.start_notify(MODEL_NBR_UUID, callback=callback)
                state = ConnectState.CLIENT_CONNECTED
                print("CONNECTED!")
            case ConnectState.DISCONNECT_INPROG:
                print("DISCONNECTING!")
                await client.stop_notify(MODEL_NBR_UUID)
                client = None
                state = ConnectState.NO_CONNECT
                print("DISCONNECTED!")
            case ConnectState.EXIT:
                print("EXITING!")
                if client is not None:
                    print("DISCONNECTING!")
                    await client.stop_notify(MODEL_NBR_UUID)
                    client = None
                print("EXITED!")
                break
                

def callback(sender: BleakGATTCharacteristic, data: bytearray):
        print(f"{sender}: {data}")

def start():
    asyncio.run(main(address))