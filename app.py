#!/usr/bin/env python3
"""
@File:          app.py
@Descrption:    Systemcontroll of Stratoflight
@Author:        Prossinger Jakob
@Date:          22 February 2022
@Todo:          * add logging TODO
                * find better way to init flask app with settings TODO 
                * Shutdown Raspberrs PIs
"""
from sensor import ina260
from sensor import sensor
from sensor import neo6m
from sensor import internal
from controller import controller
from controller.secondary.secondary import Secondary
from config import *
import config as config
from flask import Flask, redirect, render_template
from csv_handler.csv_handler import CSV_HANDLER
import RPi.GPIO as GPIO
import atexit
import threading


app = Flask(__name__)
app.led_blink_state = True
app.run_main_system = True
app.LED_states = default_LED_states

# init GPIO pins
GPIO.setmode(GPIO.BOARD)
GPIO.setwarnings(False)
for pin in app.LED_states:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, app.LED_states[pin]['state'])

for pin in config._REQUEST_SHUTDOWN_PINS:
    GPIO.setup(pin, GPIO.OUT)

for pin in config._POWER_OFF_PINS:
    GPIO.setup(pin, GPIO.OUT)


@atexit.register
def atexit_function() -> None:
    GPIO.cleanup()


def raspberry_shutdown() -> None:
    pass


def raspbery_request_shutdown() -> None:
    pass


def led_blink_thread() -> None:
    global app
    if app.led_blink_state is False:
        return
    for pin in app.LED_states:
        app.LED_states[pin]['state'] = not app.LED_states[pin]['state']
        GPIO.output(pin, app.LED_states[pin]['state'])
    threading.Timer(config._BLINK_INTERVAL_SEC, led_blink_thread).start()


def sensor_reading_thread() -> None:
    if app.run_main_system is False:
        return
    strato_controller.reload()
    strato_controller.write_csv_data()
    threading.Timer(config._MEASURING_INTERVAL_SEC,
                    sensor_reading_thread).start()


@app.route("/")
def main() -> None:
    template_data = {
        'led_blink_mode': app.led_blink_state
    }
    return render_template('index.html', **template_data)


@app.route("/sensors")
def show_data() -> None:
    # read new data from all sensors
    strato_controller.reload()
    # store data in csv file
    strato_controller.write_csv_data()
    template_data = {
        'sensors': strato_controller.sensors
    }
    return render_template('sensor_data.html', **template_data)


if __name__ == "__main__":
    # init csv handler
    strato_csv_handler = CSV_HANDLER(
        "/home/pi/Documents/StratoFlight-System-Control/data/sensor_data.csv")

    # init controller
    strato_controller = controller.Controller(
        "strato_controller", strato_csv_handler)

    # init all sensors
    sensor_ina1 = ina260.INA260(
        "INA260 Secondary I", config._SECONDARY1_INA260_ADDRESS)
    sensor_ina2 = ina260.INA260(
        "INA260 Primary", config._PRIMARY_INA260_ADDRESS)
    sensor_neo = neo6m.NEO6M(name="NEO6M GPS")
    sensor_internal = internal.INTERNAL("Raspberry")

    # add sensors to controller
    strato_controller.addSensor(sensor_internal)
    strato_controller.addSensor(sensor_ina1)
    strato_controller.addSensor(sensor_ina2)
    strato_controller.addSensor(sensor_neo)
    strato_controller.write_csv_header()

    # init secondaries
    secondary1 = Secondary(
        "secondary1", config._SECONDARY1_REQUEST_SHUTDOWN_PIN, config._SECONDARY1_POWER_OFF_PIN)
    secondary2 = Secondary(
        "secondary2", config._SECONDARY2_REQUEST_SHUTDOWN_PIN, config._SECONDARY2_POWER_OFF_PIN)
    secondary3 = Secondary(
        "secondary3", config._SECONDARY3_REQUEST_SHUTDOWN_PIN, config._SECONDARY3_POWER_OFF_PIN)
    secondary4 = Secondary(
        "secondary4", config._SECONDARY4_REQUEST_SHUTDOWN_PIN, config._SECONDARY4_POWER_OFF_PIN)

    # add secondaries to controller
    strato_controller.add_Secondary(secondary1)
    strato_controller.add_Secondary(secondary2)
    strato_controller.add_Secondary(secondary3)
    strato_controller.add_Secondary(secondary4)

    # starting led blink thread
    led_blink_thread()
    # start sensor reading thread
    sensor_reading_thread()
    app.run(host="localhost", port=5000, debug=False)
