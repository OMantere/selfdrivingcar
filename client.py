#!/usr/bin/env python

import asyncio
import websockets
import time
import functools
import struct
import sys

train = len(sys.argv) > 1
print("train: ", train)

async def image_recv(q):
    i = 0
    prev_time = time.time()
    async with websockets.connect(
            'ws://192.168.43.231:8001') as websocket:
        while True:
            await websocket.send('')
            data = await websocket.recv()
            img = data[0:-16]
            throttle = struct.unpack('d', data[-16:-8])[0]
            steering = struct.unpack('d', data[-8:])[0]
            # print("THROTTLE: {:.2f}, STEERING: {:.2f}".format(throttle, steering))
            if train:
                with open('img_{}.jpg'.format(i), 'wb') as f:
                    f.write(img)
                with open('actions_{}'.format(i), 'w') as f:
                    f.write(' '.join([str(throttle), str(steering)]))
            await q.put(data)
            i += 1
            if i % 10 == 0:
                new_time = time.time()
                fps = 1.0/(new_time - prev_time) * 10
                prev_time = new_time
                print("*** FPS: {0:.2f} ***".format(fps))


async def image_send(websocket, path, q):
    while True:
        await websocket.recv()
        data = await q.get()
        await websocket.send(data)

queue = asyncio.Queue()
start_server = websockets.serve(functools.partial(image_send, q=queue), 'localhost', 8002)
loop = asyncio.get_event_loop()
loop.run_until_complete(asyncio.gather(image_recv(queue), start_server))
