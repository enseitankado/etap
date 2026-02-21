import asyncio
import time
import websockets
import json
import uuid

HOST = "localhost"
PORT = 8765

fake_data = """
{
  "type": "validation",
  "status": "success",
  "user_data": {
    "hasRole": "0",
    "isEmailVerify": "0",
    "isForeign": "0",
    "isGuardian": "0",
    "selectedSchool": {
      "boroughId": "1",
      "boroughName": "MERKEZ TEŞKİLATI",
      "cityId": "999",
      "cityName": "BAKANLIK",
      "schoolId": "974422",
      "schoolName": "Yenilik ve Eğitim Teknolojileri Genel Müdürlüğü"
    },
    "taskId": "0",
    "tckn": "31313131313",
    "uid": "313131313131313131313",
    "uname": "Sagopa KAJMER",
    "utype": "TESTTEACHER"
  }
}
"""

async def handler(websocket, path):
    try:
        while True:
            print(await websocket.recv())
            qid = str(uuid.uuid4())
            message = json.dumps({"uuid": qid, "expire_at": int(time.time() + 31)})
            await websocket.send(message)
            await asyncio.sleep(3)
            await websocket.send(fake_data)
            await asyncio.sleep(5)
            await websocket.close()
    except websockets.exceptions.ConnectionClosed:
        print("Client disconnected")
    except Exception as e:
        print(f"Error: {e}")

async def main():
    print(f"WebSocket server starting at ws://{HOST}:{PORT}")
    async with websockets.serve(handler, HOST, PORT):
        await asyncio.Future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n WebSocket server shutting down...")
