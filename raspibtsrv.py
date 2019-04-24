#!/usr/bin/env python

import logging
import logging.handlers
import argparse
import sys
import os
import time
from bluetooth import *
import math
from carpwm import *
import traceback
import time
import multiprocessing
from PyImageStream.main import ws_main


class LoggerHelper(object):
    def __init__(self, logger, level):
        self.logger = logger
        self.level = level

    def write(self, message):
        if message.rstrip() != "":
            self.logger.log(self.level, message.rstrip())


def setup_logging():
    return
    # Default logging settings
    LOG_FILE = "/var/log/raspibtsrv.log"
    LOG_LEVEL = logging.INFO

    # Define and parse command line arguments
    argp = argparse.ArgumentParser(description="Raspberry PI Bluetooth Server")
    argp.add_argument("-l", "--log", help="log (default '" + LOG_FILE + "')")

    # Grab the log file from arguments
    args = argp.parse_args()
    if args.log:
        LOG_FILE = args.log

    # Setup the logger
    logger = logging.getLogger(__name__)
    # Set the log level
    logger.setLevel(LOG_LEVEL)
    # Make a rolling event log that resets at midnight and backs-up every 3 days
    handler = logging.handlers.TimedRotatingFileHandler(LOG_FILE,
        when="midnight",
        backupCount=3)

    # Log messages should include time stamp and log level
    formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
    # Attach the formatter to the handler
    handler.setFormatter(formatter)
    # Attach the handler to the logger
    logger.addHandler(handler)

    # Replace stdout with logging to file at INFO level
    sys.stdout = LoggerHelper(logger, logging.INFO)
    # Replace stderr with logging to file at ERROR level
    sys.stderr = LoggerHelper(logger, logging.ERROR)


# Main loop
def main(last_throttle, last_steering):
    setup_logging()
    # We need to wait until Bluetooth init is done
    time.sleep(1)

    # Make device visible
    os.system("hciconfig hci0 piscan")

    # Create a new server socket using RFCOMM protocol
    server_sock = BluetoothSocket(RFCOMM)
    # Bind to any port
    server_sock.bind(("", PORT_ANY))
    # Start listening
    server_sock.listen(1)

    # Get the port the server socket is listening
    port = server_sock.getsockname()[1]

    # The service UUID to advertise
    uuid = "7be1fcb3-5776-42fb-91fd-2ee7b5bbb86d"

    # Start advertising the service
    advertise_service(server_sock, "RaspiBtSrv",
                       service_id=uuid,
                       service_classes=[uuid, SERIAL_PORT_CLASS],
                       profiles=[SERIAL_PORT_PROFILE])

    # These are the operations the service supports
    # Feel free to add more
    operations = ["ping", "example"]
    client_sock = None
    normalize_c = 8.0
    midcutoff = 0.15
    premult_rear = 1.0
    max_throttle = 0.7
    min_throttle = 0.5
    neutral_throttle = 0.5
    min_steer = 0.0
    max_steer = 1.0
    center_steer = 0.5
    control = CarControl(40, 7, verbose=False)
    control.start()
    control.set_steering_angle(0.5)
    control.set_throttle(0.5)
    print("Initing")
    time_start = None
    time_delay = 5.0
    armed = False

    # Main Bluetooth server loop
    while True:
        try:
            try:
                name = client_sock.getpeername()
                #print "Still connected to ", name
            except:
                traceback.print_exc()
                client_sock = None
                # This will block until we get a new connection
                print("No peer name, waiting for connection on RFCOMM channel %d" % port)
                client_sock, client_info = server_sock.accept()
                print("Accepted connection from ", client_info)

            # Read data sent by client
            data = client_sock.recv(1024)
            if len(data) == 0:
                print("Len of data was 0")
                break
            #print("Received [%s]" % data)
            data = client_sock.recv(1024)
            values = data.split(b'msg')[1].strip().split()
            try:
                header = values[0]
            except:
                traceback.print_exc()
                continue


            
            if header == b'control':
                x = y = z = 0.0
                try:
                    z_sign = max(min(z * 9999999, 1.0), -1.0)
                    y = max(min(float(values[2]) / normalize_c, 1.0), -1.0)
                    y = (y + 1.0) / 2.0
                    z = max(min(float(values[3]) * premult_rear / normalize_c, 1.0), -1.0)
                    z = sign(z) * max(min(math.sqrt(y*y + z*z), 1.0), -1.0)
                    z = max(z, 0.0)
                    z = z * (max_throttle - neutral_throttle) + neutral_throttle
                    car_control.set_steering_angle(y)
                    car_control.set_throttle(z)
                    if not armed and time_start is None:
                        time_start = time.time()
                except:
                    traceback.print_exc()
                    continue

                if not armed and time_start is not None:
                    if time.time() > time_start + time_delay:
                        armed = True
                    else:
                        control.set_throttle(neutral_throttle)
                        continue

                # Right is positive y
                # Forward is positive z
                last_steering.value = y
                last_throttle.value = z
                control.set_steering_angle(y)
                control.set_throttle(z)
 
        except IOError:
            traceback.print_exc()
            pass

        except KeyboardInterrupt:
            if client_sock is not None:
                client_sock.close()
            server_sock.close()
            print("Server going down")
            break



steer = multiprocessing.Value('d', 0.0)

def loop_steer(steer):
    while True:
        angle = steer.value
        angle = 5.0*angle
        angle += 0.5
        angle = max(angle, 0.0)
        angle = min(angle, 1.0)
        print("Pred angle: {}".format(angle))
        control.set_steering_angle(angle)
        time.sleep(0.1)


selfdrive = False
if selfdrive:
    from productionmodel import pull_loop, push_loop
    #max_throttle = 0.65
    #control.set_throttle(max_throttle)
    p1 = multiprocessing.Process(target=push_loop)
    p2 = multiprocessing.Process(target=pull_loop, args=(steer,))
    #p3 = multiprocessing.Process(target=loop_steer, args=(steer,))
    p1.start()
    p2.start()
    p3.start()
    p1.join()
    p2.join()
    p3.join()
else:
    # defining actions as shared globals
    last_throttle = multiprocessing.Value('d', 0.5)
    last_steering = multiprocessing.Value('d', 0.5)
    bt_loop = multiprocessing.Process(target=main, args=(last_throttle, last_steering))
    ws_server = multiprocessing.Process(target=ws_main, args=(last_throttle, last_steering))
    bt_loop.start()
    ws_server.start()
    bt_loop.join()
    ws_server.join()


