#! /usr/bin/env python

import curses
import time
import RPi.GPIO as GPIO

class PWMControl(object):
    def __init__(self, pin):
	self.pin = pin
	self.rate = 50 # 50 Hz is RC standard
	self.cycle_length = 1.0/self.rate
        GPIO.setup(self.pin, GPIO.OUT)
	self.pwm = GPIO.PWM(self.pin, self.rate)
	self.min_pulse_length = 1.0
	self.max_pulse_length = 2.0
        self.neutral_pulse_length = 1.5

    def _dc_from_pl(self, pulse_length):
	"""Pulse length in milliseconds"""
	pulse_length = pulse_length / 1000
	return pulse_length / self.cycle_length * 100

    def start(self):
	"""Start the PWM"""
	self.duty_cycle = self._dc_from_pl(self.neutral_pulse_length)
	self.pwm.start(self.duty_cycle)

    def set_pulse_length(self, pulse_length):
	"""Set pulse length in milliseconds"""
        pulse_length = min(self.max_pulse_length, pulse_length)
        pulse_length = max(self.min_pulse_length, pulse_length)
	self.duty_cycle = self._dc_from_pl(pulse_length)
	self.pwm.ChangeDutyCycle(self.duty_cycle)
    
    def unit_adjust(self, value):
        """Value in [0.0, 1.0]"""
        value = min(1.0, value)
        value = max(0.0, value)
        pulse_length = (self.max_pulse_length - self.min_pulse_length) * value + self.min_pulse_length
	self.set_pulse_length(pulse_length)


class CarControl(object):
    def __init__(self, esc_pin, steerpin):
        GPIO.setmode(GPIO.BOARD)
	self.throttle = PWMControl(esc_pin) 
	self.steering = PWMControl(steerpin)

    def start(self):
	self.throttle.start()
	self.steering.start()

    def set_steering_angle(self, value):
        print("Set steering to %.2f" % value)
	self.steering.unit_adjust(value)

    def set_throttle(self, value):
        print("Set throttle to %.2f" % value)
	self.throttle.unit_adjust(value)


class KeyboardControl(object):
    def __init__(self):
        self.control = CarControl(40, 7)

    def start(self):
        self.control.start()
        screen = curses.initscr()
        curses.noecho()
        curses.cbreak()
        screen.keypad(True)
        throttle = 0.5
        steering = 0.5
	try:
	    while 1:
		c = screen.getch()
		if c == ord('a'):
                    steering = 0.0
		elif c == ord('d'):
                    steering = 1.0
		elif c == ord('w'):
                    throttle += 0.01
		elif c == ord('s'):
                    throttle -= 0.01
                self.control.set_steering_angle(steering)
                self.control.set_throttle(throttle)
        finally:	
	    curses.nocbreak()
	    screen.keypad(0)
	    curses.echo()
	    curses.endwin()
	    GPIO.cleanup() 

keyboard_control = KeyboardControl()
keyboard_control.start()

