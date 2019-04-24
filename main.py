#!/usr/bin/env python3

import functools
import argparse
import os
import io
import asyncio
import websockets
import multiprocessing
import cv2
import struct
import numpy as np
#from productionmodel import preprocess_input, read_img


class Camera:
    def undistort(self, img):
        im = read_img(img)
        return cv2.flip(cv2.cvtColor(preprocess_input(im), cv2.COLOR_BGR2RGB), -1)

    def __init__(self):
        print("Initializing camera...")
        self._cap = cv2.VideoCapture(0)
        print("Camera initialized")
        self.is_started = False
        self.stop_requested = False
        self.stopdelay = 5

    def request_start(self):
        if self.stop_requested:
            print("Camera continues to be in use")
            self.stop_requested = False
        if not self.is_started:
            self._start()

    def request_stop(self):
        if self.is_started and not self.stop_requested:
            self.stop_requested = True
            print("Stopping camera in " + str(self.stopdelay) + " seconds...")
            tornado.ioloop.IOLoop.current().call_later(self.stopdelay, self._stop)

    def _start(self):
        print("Starting camera...")
        self._cap.open(0)
        print("Camera started")
        self.is_started = True

    def _stop(self):
        if self.stop_requested:
            print("Stopping camera now...")
            self._cap.release()
            print("Camera stopped")
            self.is_started = False
            self.stop_requested = False

    def get_jpeg_image_bytes(self):
        cam_success, img = self._cap.read()
        if not cam_success:
            print("OpenCV: Camera capture failed")
            return None
        enc_success, buffer = cv2.imencode(".jpg", img)
        if not enc_success:
            print("OpenCV: Image encoding failed")
            return None
        return io.BytesIO(buffer).getvalue()



async def rpi_server(websocket, path, camera, last_throttle, last_steering):
    i = 0
    while True:
        data = camera.get_jpeg_image_bytes()
        if data:
            await websocket.recv()
            await websocket.send(data + struct.pack('d', last_throttle.value) + struct.pack('d', last_steering.value))


def ws_main(last_throttle, last_steering):
    camera = Camera()
    start_server = websockets.serve(functools.partial(rpi_server, camera=camera, last_throttle=last_throttle, last_steering=last_steering), '0.0.0.0', 8001)
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()


if __name__ == "__main__":
    ws_main(multiprocessing.Value('f', 0.5), multiprocessing.Value('f', 0.5))
