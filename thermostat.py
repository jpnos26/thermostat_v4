#!/usr/bin/python
# -*- coding: latin-1 -*-

### BEGIN LICENSE
# Copyright (c) 2016 Jpnos <jpnos@gmx.com>

# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:

# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
### END LICENSE

##############################################################################
#                                                                            #
#       Core Imports                                                         #
#                                                                            #
##############################################################################
import threading
import os, os.path, sys
import time
import datetime
import urllib2
import json
import socket
import re
import locale
locale.setlocale(locale.LC_ALL, '')
from requests import get

###Upnp Import
from urlparse import urlparse
from xml.dom.minidom import parseString
from xml.dom.minidom import Document
import httplib
import argparse

##############################################################################
#                                                                            #
#       Kivy UI Imports                                                      #
#                                                                            #
##############################################################################

import kivy

kivy.require('1.9.0')  # replace with your current kivy version !
from threading import Thread
from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.label import Label
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.storage.jsonstore import JsonStore
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition
from urllib2 import URLError
from kivy.animation import Animation
from kivy.core.window import Window
from functools import partial


##############################################################################
#                                                                            #
#       Other Imports                                                        #
#                                                                            #
##############################################################################

import cherrypy
import schedule



##############################################################################
#                                                                            #
#       GPIO & Simulation Imports                                            #
#                                                                            #
##############################################################################

try:
    import RPi.GPIO as GPIO
except ImportError:
    import FakeRPi.GPIO as GPIO
    print ("No RPI used")
try:
    import Adafruit_DHT
except ImportError:
    print ("No DHT Library")
##############################################################################
#                                                                            #
#       Sensor Imports                                                       #
#                                                                            #
##############################################################################

from w1thermsensor import W1ThermSensor


##############################################################################
#                                                                            #
#       Utility classes                                                      #
#                                                                            #
##############################################################################

class switch(object):
    def __init__(self, value):
        self.value = value
        self.fall = False

    def __iter__(self):
        """Return the match method once, then stop"""
        yield self.match
        raise StopIteration

    def match(self, *args):
        """Indicate whether or not to enter a case suite"""
        if self.fall or not args:
            return True
        elif self.value in args:  # changed for v1.5, see below
            self.fall = True
            return True
        else:
            return False


##############################################################################
#                                                                            #
#       MySensor.org Controller compatible translated constants              #
#                                                                            #
##############################################################################

MSG_TYPE_SET = "set"
MSG_TYPE_PRESENTATION = "presentation"
CHILD_DEVICE_NODE = "node"
CHILD_DEVICE_UICONTROL_HEAT = "heatControl"
CHILD_DEVICE_UICONTROL_COOL = "coolControl"
CHILD_DEVICE_UICONTROL_HOLD = "holdControl"
CHILD_DEVICE_WEATHER_FCAST_TODAY = "weatherForecastToday"
CHILD_DEVICE_WEATHER_FCAST_TOMO = "weatherForecastTomorrow"
CHILD_DEVICE_WEATHER_CURR = "weatherCurrent"
CHILD_DEVICE_HEAT = "heat"
CHILD_DEVICE_COOL = "cool"
CHILD_DEVICE_PIR = "motionSensor"
CHILD_DEVICE_TEMP = "temperatureSensor"
CHILD_DEVICE_SCREEN = "screen"
CHILD_DEVICE_SCHEDULER = "scheduler"
CHILD_DEVICE_WEBSERVER = "webserver"
CHILD_DEVICE_DHTIN = "DhtIn"
CHILD_DEVICE_DHTOUT = "DhtOut"
CHILD_DEVICE_DHTIR = "DhtIr"
CHILD_DEVICE_DHTZONE = "DhtZone"
CHILD_DEVICE_DHTRELE = "DhtRele"
CHILD_DEVICE_DHTCLEAR = "Clear_dht"

CHILD_DEVICES = [
    CHILD_DEVICE_NODE,
    CHILD_DEVICE_UICONTROL_HEAT,
    CHILD_DEVICE_UICONTROL_COOL,
    CHILD_DEVICE_UICONTROL_HOLD,
    CHILD_DEVICE_WEATHER_CURR,
    CHILD_DEVICE_WEATHER_FCAST_TODAY,
    CHILD_DEVICE_WEATHER_FCAST_TOMO,
    CHILD_DEVICE_HEAT,
    CHILD_DEVICE_COOL,
    CHILD_DEVICE_PIR,
    CHILD_DEVICE_TEMP,
    CHILD_DEVICE_SCREEN,
    CHILD_DEVICE_SCHEDULER,
    CHILD_DEVICE_WEBSERVER,
    CHILD_DEVICE_DHTIN,
    CHILD_DEVICE_DHTOUT,
    CHILD_DEVICE_DHTIR,
    CHILD_DEVICE_DHTZONE,
    CHILD_DEVICE_DHTRELE,
    CHILD_DEVICE_DHTCLEAR
]

CHILD_DEVICE_SUFFIX_UICONTROL = "Control"

MSG_SUBTYPE_NAME = "sketchName"
MSG_SUBTYPE_VERSION = "sketchVersion"
MSG_SUBTYPE_BINARY_STATUS = "binaryStatus"
MSG_SUBTYPE_TRIPPED = "armed"
MSG_SUBTYPE_ARMED = "tripped"
MSG_SUBTYPE_TEMPERATURE = "temperature"
MSG_SUBTYPE_FORECAST = "forecast"
MSG_SUBTYPE_CUSTOM = "custom"
MSG_SUBTYPE_TEXT = "text"
MSG_SUBTYPE_DHT = "DhtWifi"

##############################################################################
#                                                                            #
#       Settings                                                             #
#                                                                            #
##############################################################################

THERMOSTAT_VERSION = "4.2.0"

# Debug settings

debug = False
useTestSchedule = False

# Threading Locks

thermostatLock = threading.RLock()
weatherLock = threading.Lock()
scheduleLock = threading.RLock()
dhtLock = threading.RLock()


# Thermostat persistent settings

settings = JsonStore("./setting/thermostat_settings.json")
state = JsonStore("./setting/thermostat_state.json")
actual = JsonStore("./setting/thermostat_actual.json")

# graphics


# Logging settings/setup

LOG_FILE_NAME = "./log/thermostat.log"

LOG_ALWAYS_TIMESTAMP = True

LOG_LEVEL_DEBUG = 1
LOG_LEVEL_INFO = 2
LOG_LEVEL_ERROR = 3
LOG_LEVEL_STATE = 4
LOG_LEVEL_NONE = 5

LOG_LEVELS = {
    "debug": LOG_LEVEL_DEBUG,
    "info": LOG_LEVEL_INFO,
    "state": LOG_LEVEL_STATE,
    "error": LOG_LEVEL_ERROR
}

LOG_LEVELS_STR = {v: k for k, v in LOG_LEVELS.items()}

logFile = None


def log_dummy(level, child_device, msg_subtype, msg, msg_type=MSG_TYPE_SET, timestamp=True, single=False):
    pass


def log_file(level, child_device, msg_subtype, msg, msg_type=MSG_TYPE_SET, timestamp=True, single=False):
    if level >= logLevel:
        ts = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z ")
        logFile.write(
            ts + LOG_LEVELS_STR[level] + "/" + child_device + "/" + msg_type + "/" + msg_subtype + ": " + msg + "\n")


def log_print(level, child_device, msg_subtype, msg, msg_type=MSG_TYPE_SET, timestamp=True, single=False):
    if level >= logLevel:
        ts = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z ") if LOG_ALWAYS_TIMESTAMP or timestamp else ""
        print(ts + LOG_LEVELS_STR[level] + "/" + child_device + "/" + msg_type + "/" + msg_subtype + ": " + msg)


loggingChannel = "none" if not (settings.exists("logging")) else settings.get("logging")["channel"]
loggingLevel = "state" if not (settings.exists("logging")) else settings.get("logging")["level"]

for case in switch(loggingChannel):
    if case('none'):
        log = log_dummy
        break
    if case('file'):
        log = log_file
        logFile = open(LOG_FILE_NAME, "a", 0)
        break
    if case('print'):
        log = log_print
        break
    if case():  # default
        log = log_dummy

logLevel = LOG_LEVELS.get(loggingLevel, LOG_LEVEL_NONE)

# Send presentations for Node

log(LOG_LEVEL_STATE, CHILD_DEVICE_NODE, MSG_SUBTYPE_NAME, "Thermostat Starting Up...", msg_type=MSG_TYPE_PRESENTATION)
log(LOG_LEVEL_STATE, CHILD_DEVICE_NODE, MSG_SUBTYPE_VERSION, THERMOSTAT_VERSION, msg_type=MSG_TYPE_PRESENTATION)

# send presentations for all other child "sensors"

for i in range(len(CHILD_DEVICES)):
    child = CHILD_DEVICES[i]
    if child != CHILD_DEVICE_NODE:
        log(LOG_LEVEL_STATE, child, child, "", msg_type=MSG_TYPE_PRESENTATION)

# Various temperature settings:

tempScale = settings.get("scale")["tempScale"]
scaleUnits = u"\xb0" if tempScale == "metric" else u"f"
precipUnits = " mm" if tempScale == "metric" else '"'
precipFactor = 1.0 if tempScale == "metric" else 0.0393701
precipRound = 0 if tempScale == "metric" else 1
sensorUnits = W1ThermSensor.DEGREES_C if tempScale == "metric" else W1ThermSensor.DEGREES_F
windFactor = 3.6 if tempScale == "metric" else 1.0
windUnits = " km/h" if tempScale == "metric" else " mph"
typeSensor = 0 if not (settings.exists("thermostat")) else (settings.get("thermostat")["sensTemp"])
dhtpin = 0 if not (settings.exists("thermostat")) else (settings.get("thermostat")["sensPin"])

TEMP_TOLERANCE = 0.1 if tempScale == "metric" else 0.18
currentTemp = 20.0 if tempScale == "metric" else 72.0
correctedTemp = 20.0
priorCorrected = -100.0
# openDoor e openDoorcheck for stop sistem for a time set in thermostat_setting and temperature change quickly of 1 C degrees
openDoor = 21 if not (state.exists("thermostat")) else int(
    (state.get("thermostat")["openDoor"] / state.get("thermostat")["tempCheckInterval"]) + 1)
openDoorCheck = 20 if not (state.exists("thermostat")) else int(
    state.get("thermostat")["openDoor"] / state.get("thermostat")["tempCheckInterval"])

setTemp = 22.0 if not (state.exists("state")) else state.get("state")["setTemp"]
setice = 15.0 if not (settings.exists("thermostat")) else settings.get("thermostat")["tempice"]
tempHysteresis = 0.5 if not (settings.exists("thermostat")) else settings.get("thermostat")["tempHysteresis"]
tempCheckInterval = 3 if not (settings.exists("thermostat")) else settings.get("thermostat")["tempCheckInterval"]
out_temp = 0.0
temp_vis = 0

minUIEnabled = 0 if not (settings.exists("thermostat")) else settings.get("thermostat")["minUIEnabled"]
minUITimeout = 20 if not (settings.exists("thermostat")) else settings.get("thermostat")["minUITimeout"]
lightOff = 60 if not (settings.exists("thermostat")) else settings.get("thermostat")["lightOff"]

minUITimer = None
lightOffTimer = None
csvSaver = None
dhtIrTimer = None
dhtZoneTimer = None
dhtReleTimer = None
dhtClearTimer = None
dhtLanTimer = None
animationTimer = None

csvTimeout = 300 if not (settings.exists("thermostat")) else settings.get("thermostat")["saveCsv"]

log(LOG_LEVEL_INFO, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/settings/temperature/tempScale", str(tempScale),
    timestamp=False)
# log( LOG_LEVEL_INFO, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/settings/temperature/scaleUnits", scaleUnits , timestamp=False )
log(LOG_LEVEL_INFO, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/settings/temperature/precipUnits", str(precipUnits),
    timestamp=False)
log(LOG_LEVEL_INFO, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/settings/temperature/precipFactor", str(precipFactor),
    timestamp=False)
log(LOG_LEVEL_INFO, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/settings/temperature/sensorUnits", str(sensorUnits),
    timestamp=False)
log(LOG_LEVEL_INFO, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/settings/temperature/windFactor", str(windFactor),
    timestamp=False)
log(LOG_LEVEL_INFO, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/settings/temperature/windUnits", str(windUnits),
    timestamp=False)
log(LOG_LEVEL_INFO, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/settings/temperature/currentTemp", str(currentTemp),
    timestamp=False)
log(LOG_LEVEL_INFO, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/settings/temperature/setTemp", str(setTemp),
    timestamp=False)
log(LOG_LEVEL_INFO, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/settings/temperature/tempHysteresis", str(tempHysteresis),
    timestamp=False)
log(LOG_LEVEL_INFO, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/settings/temperature/tempCheckInterval",
    str(tempCheckInterval), timestamp=False)
log(LOG_LEVEL_INFO, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/settings/temperature/minUIEnabled", str(minUIEnabled),
    timestamp=False)
log(LOG_LEVEL_INFO, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/settings/temperature/minUITimeout", str(minUITimeout),
    timestamp=False)
log(LOG_LEVEL_INFO, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/settings/temperature/lightOff", str(lightOff),
    timestamp=False)

# Temperature calibration settings:

elevation = 0 if not (settings.exists("thermostat")) else settings.get("calibration")["elevation"]
boilingPoint = (100.0 - 0.003353 * elevation) if tempScale == "metric" else (212.0 - 0.00184 * elevation)
freezingPoint = 0.01 if tempScale == "metric" else 32.018
referenceRange = boilingPoint - freezingPoint
correctSensor = 0 if not (settings.exists("thermostat")) else settings.get("calibration")["correctSensor"]

boilingMeasured = settings.get("calibration")["boilingMeasured"]
freezingMeasured = settings.get("calibration")["freezingMeasured"]
measuredRange = boilingMeasured - freezingMeasured

log(LOG_LEVEL_INFO, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/settings/calibration/elevation", str(elevation),
    timestamp=False)
log(LOG_LEVEL_INFO, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/settings/calibration/boilingPoint", str(boilingPoint),
    timestamp=False)
log(LOG_LEVEL_INFO, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/settings/calibration/freezingPoint", str(freezingPoint),
    timestamp=False)
log(LOG_LEVEL_DEBUG, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/settings/calibration/referenceRange",
    str(referenceRange), timestamp=False)
log(LOG_LEVEL_INFO, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/settings/calibration/boilingMeasured",
    str(boilingMeasured), timestamp=False)
log(LOG_LEVEL_INFO, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/settings/calibration/freezingMeasured",
    str(freezingMeasured), timestamp=False)
log(LOG_LEVEL_DEBUG, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/settings/calibration/measuredRange", str(measuredRange),
    timestamp=False)

# DHT and Temp setting:

minTemp = 15.0 if not (settings.exists("thermostat")) else settings.get("thermostat")["minTemp"]
maxTemp = 30.0 if not (settings.exists("thermostat")) else settings.get("thermostat")["maxTemp"]
tempStep = 0.5 if not (settings.exists("thermostat")) else settings.get("thermostat")["tempStep"]
dhtRele = 0 if not (settings.exists("thermostat")) else settings.get("dht_rele")["rele_enabled"]
dhtReleIP = "" if not (settings.exists("thermostat")) else settings.get("dht_rele")["rele_ip"]
dhtIr_number = 0 if not (settings.exists("thermostat")) else settings.get("dht_ir")["number"]
dhtZone_number = 0 if not (settings.exists("thermostat")) else settings.get("dht_zone")["number"]
telegramSend = 0 if not (settings.exists("thermostat")) else settings.get("telegram")["enabled"]
chatIdTest = 0
dhtCheckIr = 0
dhtCheckRele = 0
dhtCheckZone = 0
dhtCheckIce = 0

# GPIO Pin setup and utility routines:

heatPin = 27 if not (settings.exists("thermostat")) else settings.get("thermostat")["heatPin"]
lightPin = 24 if not (settings.exists("thermostat")) else settings.get("thermostat")["lightPin"]
coolPin = 18 if not (settings.exists("thermostat")) else settings.get("thermostat")["coolPin"]

GPIO.setmode(GPIO.BCM)
GPIO.setup(heatPin, GPIO.OUT)
GPIO.output(heatPin, GPIO.HIGH)
GPIO.setup(lightPin, GPIO.OUT)
GPIO.output(lightPin, GPIO.HIGH)
GPIO.setup(coolPin, GPIO.OUT)
GPIO.output(coolPin, GPIO.HIGH)

#####Framework Telegram
if telegramSend == 1:
    import telepot
    from telepot.loop import MessageLoop
    telegramTimeout = 60 if not (settings.exists("thermostat")) else settings.get("telegram")["timeout"]
    testTimeout = 0
    
if dhtIr_number > 0:
    dhtIRLabel = {}
    dhtIR = {}
    for c in range(0, dhtIr_number):
        dhtIRLabel[c, 0] = Label(text=" ", size_hint=(None, None), font_size='15sp', markup=True, text_size=(300, 300),
                                 color=(1, 1, 1, 1))

        dhtIR[c, 0] = settings.get("dht_ir")["zoneir_interval"]
        dhtIR[c, 1] = "http://" + settings.get("dht_ir")["zoneir_ip_" + str(c + 1)]
        dhtIR[c, 2] = settings.get("dht_ir")["zoneir_name_" + str(c + 1)]
        dhtIR[c, 3] = 0  # temperatura
        dhtIR[c, 4] = 0  # Umidita
        dhtIR[c, 5] = 0  # stato comando Inviato
        dhtIR[c, 6] = 0  # temperatura impostata
        dhtIR[c, 7] = 1  # setto abilitato

if dhtZone_number > 0:
    dhtZoneLabel = {}
    dhtZone = {}
    for c in range(0, dhtZone_number):
        dhtZoneLabel[c, 0] = Label(text=" ", size_hint=(None, None), font_size='15sp', markup=True,
                                   text_size=(300, 300), color=(1, 1, 1, 1))
        dhtZone[c, 0] = settings.get("dht_zone")["zone_interval"]
        dhtZone[c, 1] = "http://" + settings.get("dht_zone")["zone_ip_" + str(c + 1)]
        dhtZone[c, 2] = settings.get("dht_zone")["zone_name_" + str(c + 1)]
        dhtZone[c, 3] = 0  # temperatura
        dhtZone[c, 4] = 0  # Umidita
        dhtZone[c, 5] = 0  # stato comando Inviato
        dhtZone[c, 6] = 0  # temperatura impostata
        dhtZone[c, 7] = 1  # setto abilitato

log(LOG_LEVEL_INFO, CHILD_DEVICE_DHTRELE, MSG_SUBTYPE_CUSTOM + "/Dht Rele: ", str(dhtRele), timestamp=False)
log(LOG_LEVEL_INFO, CHILD_DEVICE_DHTZONE, MSG_SUBTYPE_CUSTOM + "//Dht Zone : ", str(dhtZone_number), timestamp=False)
log(LOG_LEVEL_INFO, CHILD_DEVICE_DHTIR, MSG_SUBTYPE_CUSTOM + "/Dht IR", str(dhtIr_number), timestamp=False)
log(LOG_LEVEL_INFO, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/settings/UISlider/minTemp", str(minTemp), timestamp=False)
log(LOG_LEVEL_INFO, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/settings/UISlider/maxTemp", str(maxTemp), timestamp=False)
log(LOG_LEVEL_INFO, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/settings/UISlider/tempStep", str(tempStep),
    timestamp=False)

try:
    if (typeSensor == 0):
        tempSensor = W1ThermSensor()
    else:
        tempSensor = "dht"
        dht = Adafruit_DHT.DHT22

    ##print("tempsensor ON", typeSensor)
except:
    tempSensor = None
# print("tempsensor OFF")

# PIR (Motion Sensor) setup:

pirEnabled = 0 if not (settings.exists("pir")) else settings.get("pir")["pirEnabled"]
pirPin = 5 if not (settings.exists("pir")) else settings.get("pir")["pirPin"]

pirCheckInterval = 0.5 if not (settings.exists("pir")) else settings.get("pir")["pirCheckInterval"]

pirIgnoreFromStr = "00:00" if not (settings.exists("pir")) else settings.get("pir")["pirIgnoreFrom"]
pirIgnoreToStr = "00:00" if not (settings.exists("pir")) else settings.get("pir")["pirIgnoreTo"]

pirIgnoreFrom = datetime.time(int(pirIgnoreFromStr.split(":")[0]), int(pirIgnoreFromStr.split(":")[1]))
pirIgnoreTo = datetime.time(int(pirIgnoreToStr.split(":")[0]), int(pirIgnoreToStr.split(":")[1]))

log(LOG_LEVEL_INFO, CHILD_DEVICE_PIR, MSG_SUBTYPE_ARMED, str(pirEnabled), timestamp=False)
log(LOG_LEVEL_INFO, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/settings/pir/checkInterval", str(pirCheckInterval),
    timestamp=False)
log(LOG_LEVEL_INFO, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/settings/pir/ignoreFrom", str(pirIgnoreFromStr),
    timestamp=False)
log(LOG_LEVEL_INFO, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/settings/pir/ignoreTo", str(pirIgnoreToStr),
    timestamp=False)


if pirEnabled:
    GPIO.setup(pirPin, GPIO.IN)

CHILD_DEVICE_HEAT = "heat"
CHILD_DEVICE_COOL = "cool"

log(LOG_LEVEL_INFO, CHILD_DEVICE_COOL, MSG_SUBTYPE_BINARY_STATUS, str(coolPin), timestamp=False)
log(LOG_LEVEL_INFO, CHILD_DEVICE_HEAT, MSG_SUBTYPE_BINARY_STATUS, str(heatPin), timestamp=False)
log(LOG_LEVEL_INFO, CHILD_DEVICE_PIR, MSG_SUBTYPE_TRIPPED, str(pirPin), timestamp=False)

##############################################################################
#                                                                            #
#       dht22 esp8266 external temp connect  for cold room                   #
#                                                                            #
##############################################################################
# dht ext temp setup:
dhtEnabled = 0 if not (settings.exists("dhtext")) else settings.get("dhtext")["dhtEnabled"]
dhtInterval = 2000 if not (settings.exists("dhtext")) else settings.get("dhtext")["dhtTimeout"]
dhtTemp = 0
dhtUm = 0
dht_label = Label(text=" ", size_hint=(None, None), font_size='25sp', markup=True, text_size=(300, 75),
                  color=(0.5, 0.5, 0.5, 0.2))
dhtTest = 0
dhtSchedule = 0
dhtCorrect = 0 if not (settings.exists("dhtext")) else settings.get("dhtext")["dhtCorrect"]
dhtweb = "http://" + settings.get("dhtext")["dhtClientIP"]


def dht_load(dt):
    global dhtTemp, dhtEnabled, dhtTest, dhtSchedule, umiditaLabel
    Clock.unschedule(dht_load)
    try:
        dhtUrl = "http://" + settings.get("dhtext")["dhtClientIP"] + "/dati"
        dhtread = json.loads(urllib2.urlopen(dhtUrl, None, 3).read())
        dhtTemp = dhtread["S_temperature"]
        dhtUm = dhtread["S_humidity"]
        dht_label.text = "Dht : T: " + str(dhtTemp) + scaleUnits + " , Ur: " + str(dhtUm) + " %"
        umiditaLabel.text = str(int(round(dhtUm, 0))) + "%"
        dhtEnabled = 1
        dhtTest = 0
        if dhtSchedule == 0:
            dhtSchedule = 1
            reloadSchedule()
        log(LOG_LEVEL_DEBUG, CHILD_DEVICE_DHTIN, MSG_SUBTYPE_CUSTOM + "/read/dhtIn/", dhtUrl, timestamp=False)
    except:
        dht_label.text = ""
        dhtTest += 1
        dhtEnabled = 0
        dhtSchedule = 0
    if dhtTest <= 5:
        Clock.schedule_once(dht_load, dhtInterval)
        log(LOG_LEVEL_DEBUG, CHILD_DEVICE_DHTIN, MSG_SUBTYPE_CUSTOM + "/read/dhtin/number_let<5", str(dhtTest),
            timestamp=False)
    elif dhtTest >= 7:
        Clock.schedule_once(dht_load, 120)
        log(LOG_LEVEL_ERROR, CHILD_DEVICE_DHTIN, MSG_SUBTYPE_CUSTOM + "/read/dhtin/number_let>7", str(dhtTest),
            timestamp=False)
    else:
        reloadSchedule()
        Clock.schedule_once(dht_load, 60)
        log(LOG_LEVEL_ERROR, CHILD_DEVICE_DHTIN, MSG_SUBTYPE_CUSTOM + "/read/dhtin/number_let=6", str(dhtTest),
            timestamp=False)


##############################################################################
#                                                                            #
#       dht22 esp8266 out temp 				                     #
#                                                                            #
##############################################################################
tempStep = 1
dhtoutEnabled = 0 if not (settings.exists("dhtout")) else settings.get("dhtout")["dhtoutEnabled"]
dhtoutweb = "http://" + settings.get("dhtout")["dhtoutIP"] + "/dati"


def dhtoutRead():
    global out_temp, out_humidity, dhtoutweb
    try:
        dhtoutread = json.loads(urllib2.urlopen(dhtoutweb, None, 3).read())
        out_temp = dhtoutread["S_temperature"]
        out_humidity = dhtoutread["S_humidity"]
        log(LOG_LEVEL_INFO, CHILD_DEVICE_DHTOUT, MSG_SUBTYPE_CUSTOM + "/read/dhtout/temp", str(out_temp),
            timestamp=False)
    except:
        out_temp = 0
        out_humidity = 0
        log(LOG_LEVEL_ERROR, CHILD_DEVICE_DHTOUT, MSG_SUBTYPE_CUSTOM + "/read/dhtout/", dhtoutweb, timestamp=False)


##############################################################################
#                                                                            #
#       dht22 esp8266 ir read Temperature    	                             #
#                                                                            #
##############################################################################
def dhtIrRead(dt):
    if dhtIr_number > 0:
        global dhtIrTimer
        Clock.unschedule(dhtIrTimer)
        dhtCheckIr = 0
        with dhtLock:
            for c in range(0, dhtIr_number):
                t = Thread(target=dhtIrThread(c))
                t.start()
        dhtIrTimer = Clock.schedule_once(dhtIrRead, dhtIR[0, 0])


def dhtIrThread(c):
    global dhtCheckIr, dhtIRLabel
    if dhtIR[c, 7] == 1:
        try:
            dhtirread = json.loads(urllib2.urlopen(dhtIR[c, 1] + "/dati", None, 3).read())
            dhtIR[c, 3] = dhtirread["S_temperature"]
            dhtIR[c, 4] = dhtirread["S_humidity"]
            dhtIR[c, 5] = dhtirread["S_control"]
            dhtIR[c, 6] = dhtirread["S_setTemp"]
            dhtIR[c, 7] = 1
            if dhtIR[c, 5] == 1 and dhtCheckIr == 0:
                dhtCheckIr = dhtirread["S_control"]
            elif dhtIR[c, 5] == 2 and dhtCheckIr == 0:
                dhtCheckIr = dhtirread["S_control"]
            elif dhtIR[c, 5] <> dhtCheckIr and dhtCheckIr <> 0:
                dhtCheckIr = 5000
            labelState = "ON" if (dhtIR[c, 5] == 1) else  "OFF"
            dhtIRLabel[c, 0].text = "[b]    - " + dhtIR[c, 2] + "[/b] - \n \n " + dhtIR[c, 1] + "\n temp : " + str(
                dhtIR[c, 3]) + "\n Umidita : " + str(dhtIR[c, 4]) + "% \n set Temp : " + str(
                round(float(dhtIR[c, 6]), 1)) + "\n Stato : " + labelState
            log(LOG_LEVEL_DEBUG, CHILD_DEVICE_DHTIR, MSG_SUBTYPE_CUSTOM + "/read/dhtir/number", str(c), timestamp=False)
        except:
            dhtIR[c, 7] = 0
            dhtIRLabel[c, 0].text = "[b]    - " + dhtIR[c, 2] + "[/b] - \n \n " + dhtIR[
                c, 1] + "\n Zona Non raggiungibile\n\n\n"
            log(LOG_LEVEL_ERROR, CHILD_DEVICE_DHTIR, MSG_SUBTYPE_CUSTOM + "/read/dhtir/number", str(c) + " - ",
                timestamp=False)

    else:
        log(LOG_LEVEL_ERROR, CHILD_DEVICE_DHTIR, MSG_SUBTYPE_CUSTOM + "/read/dhtir/number", dhtIR[c, 1] + " - Disabled",
            timestamp=False)


##############################################################################
#                                                                            #
#       dht22 esp8266 ir send Temperature		                     #
#                                                                            #
##############################################################################

def dhtIRSend(dt):
    if dhtIr_number >= 1:
        with dhtLock:
            for c in range(0, dhtIr_number):
                t = Thread(target=dhtIRSendThread(c))
                t.start()


def dhtIRSendThread(c):
    if dhtIR[c, 7] == 1:
        try:
            if setTemp >= 27:
                f = urllib2.urlopen(dhtIR[c, 1] + "/irSender?99", None, 3)
            else:
                f = urllib2.urlopen(dhtIR[c, 1] + "/irSender?" + str(setTemp))
                log(LOG_LEVEL_DEBUG, CHILD_DEVICE_DHTIR, MSG_SUBTYPE_CUSTOM + "/send/dhtir/number", str(c),
                    timestamp=False)
        except:
            log(LOG_LEVEL_ERROR, CHILD_DEVICE_DHTIR, MSG_SUBTYPE_CUSTOM + "/send/dhtir/number", str(c) + "- ",
                timestamp=False)
    else:
        log(LOG_LEVEL_ERROR, CHILD_DEVICE_DHTIR, MSG_SUBTYPE_CUSTOM + "/send/dhtir/number", dhtIR[c, 1] + " - Disabled",
            timestamp=False)


##############################################################################
#                                                                            #
#       dht22 esp8266 zone read				                    			 #
#                                                                            #
##############################################################################

def dhtZoneRead(dt):
    if dhtZone_number >= 1:
        global dhtCheckZone, dhtZoneLabel, dhtZoneTimer
        Clock.unschedule(dhtZoneTimer)
        dhtCheckZone = 0
        with dhtLock:
            for c in range(0, dhtZone_number):
                t = Thread(target=dhtZoneReadThread(c))
                t.start()
            dhtZoneTimer = Clock.schedule_once(dhtZoneRead, dhtZone[0, 0])


def dhtZoneReadThread(c):
    global dhtCheckZone, dhtZoneLabel
    if dhtZone[c, 7] == 1:
        try:
            dhtzoneread = json.loads(urllib2.urlopen(dhtZone[c, 1] + "/dati", None, 3).read())
            dhtZone[c, 3] = dhtzoneread["S_temperature"]
            dhtZone[c, 4] = dhtzoneread["S_humidity"]
            dhtZone[c, 5] = dhtzoneread["S_control"]
            dhtZone[c, 6] = dhtzoneread["S_setTemp"]
            if dhtZone[c, 5] == 3 and dhtCheckZone == 0:
                dhtCheckZone = dhtzoneread["S_control"]
            elif dhtZone[c, 5] == 100 and dhtCheckZone == 0:
                dhtCheckZone = dhtzoneread["S_control"]
            elif dhtZone[c, 5] <> dhtCheckZone and dhtCheckZone <> 0:
                dhtCheckZone = 3
            dhtZone[c, 7] = 1
            labelState = "ON" if (dhtZone[c, 5] == 3) else  "OFF"
            dhtZoneLabel[c, 0].text = "[b]    - " + dhtZone[c, 2] + "[/b] - \n \n " + dhtZone[
                c, 1] + "\n temp : " + str(dhtZone[c, 3]) + "\n Umidita : " + str(
                dhtZone[c, 4]) + "% \n set Temp : " + str(round(float(dhtZone[c, 6]), 1)) + "\n Stato : " + labelState
            log(LOG_LEVEL_DEBUG, CHILD_DEVICE_DHTZONE, MSG_SUBTYPE_CUSTOM + "/read/dhtzone/number", str(c),
                timestamp=False)
        except:
            dhtZone[c, 7] = 0
            log(LOG_LEVEL_ERROR, CHILD_DEVICE_DHTZONE, MSG_SUBTYPE_CUSTOM + "/read/dhtzone/number",
                dhtZone[c, 1] + " - ", timestamp=False)
            dhtZoneLabel[c, 0].text = "[b]    - " + dhtZone[c, 2] + "[/b] - \n \n " + dhtZone[
                c, 1] + "\n Zona Non raggiungibile\n\n\n"
    else:

        log(LOG_LEVEL_ERROR, CHILD_DEVICE_DHTZONE, MSG_SUBTYPE_CUSTOM + "/read/dhtzone/number",
            dhtZone[c, 1] + " - Disabled", timestamp=False)


##############################################################################
#                                                                            #
#       dht22 esp8266 set zone				                                 #
#                                                                            #
##############################################################################
def dhtZoneSend(dt):
    global setTemp, dhtCheckIce
    if dhtZone_number >= 1:
        with dhtLock:
            for c in range(0, dhtZone_number):
                t = Thread(target=dhtZoneSendThread(c))
                t.start()


def dhtZoneSendThread(c):
    global setTemp, dhtCheckIce
    if dhtCheckIce == 0:
        tempsetting = setTemp
    else:
        tempsetting = setice
    if dhtZone[c, 7] == 1:
        try:
            f = urllib2.urlopen(dhtZone[c, 1] + "/zoneON?" + str(tempsetting), None, 3)
            log(LOG_LEVEL_DEBUG, CHILD_DEVICE_DHTZONE, MSG_SUBTYPE_CUSTOM + "/send//tempsetting/dhtzone/number", str(c),
                timestamp=False)
        except:
            log(LOG_LEVEL_ERROR, CHILD_DEVICE_DHTZONE, MSG_SUBTYPE_CUSTOM + "/send/tempsetting/dhtzone/number",
                str(c) + " - ", timestamp=False)

    else:
        log(LOG_LEVEL_ERROR, CHILD_DEVICE_DHTZONE, MSG_SUBTYPE_CUSTOM + "/send/dhtzone/number",
            dhtZone[c, 1] + " - Disabled", timestamp=False)


##############################################################################
#                                                                            #
#       dht22 esp8266 comandi vari			                     #
#                                                                            #
##############################################################################
def dhtSend(comando):
    if dhtZone_number > 0:
        for c in range(0, dhtZone_number):
            t = Thread(target=dhtSendZoneCommand(c, comando))
            t.start()
    if dhtIr_number > 0:
        for c in range(0, dhtIr_number):
            t = Thread(target=dhtSendIrCommand(c, comando))
            t.start()
    if dhtRele == 1:
        try:
            f = urllib2.urlopen("http://" + dhtReleIP + "/" + comando, None, 3)
            log(LOG_LEVEL_DEBUG, CHILD_DEVICE_DHTRELE, MSG_SUBTYPE_CUSTOM + "/send/dhtRele/command", comando,
                timestamp=False)
        except:
            log(LOG_LEVEL_ERROR, CHILD_DEVICE_DHTRELE, MSG_SUBTYPE_CUSTOM + "/send/dhtRele/command", comando,
                timestamp=False)


def dhtSendZoneCommand(c, comando):
    if dhtZone[c, 7] == 1:
        try:
            f = urllib2.urlopen(dhtZone[c, 1] + "/" + comando, None, 3)
            log(LOG_LEVEL_DEBUG, CHILD_DEVICE_DHTZONE, MSG_SUBTYPE_CUSTOM + "/send/dhtzone/command", comando,
                timestamp=False)
        except:
            log(LOG_LEVEL_ERROR, CHILD_DEVICE_DHTZONE, MSG_SUBTYPE_CUSTOM + "/send/dhtzone/command", comando,
                timestamp=False)


def dhtSendIrCommand(c, comando):
    if dhtIR[c, 7] == 1:
        try:
            f = urllib2.urlopen(dhtIR[c, 1] + "/" + comando, None, 3)
            log(LOG_LEVEL_DEBUG, CHILD_DEVICE_DHTIR, MSG_SUBTYPE_CUSTOM + "/send/dhtIr/command", comando,
                timestamp=False)
        except:
            log(LOG_LEVEL_ERROR, CHILD_DEVICE_DHTIR, MSG_SUBTYPE_CUSTOM + "/send/dhtIr/command", comando,
                timestamp=False)


def dhtReleSend(comando):
    if dhtRele == 1:
        try:
            f = urllib2.urlopen("http://" + dhtReleIP + "/" + comando, None, 3)
            log(LOG_LEVEL_DEBUG, CHILD_DEVICE_DHTRELE, MSG_SUBTYPE_CUSTOM + "/send/dhtRele/command", comando,
                timestamp=False)
        except:

            log(LOG_LEVEL_ERROR, CHILD_DEVICE_DHTRELE, MSG_SUBTYPE_CUSTOM + "/send/dhtRele/command", comando,
                timestamp=False)


def dhtReleRead(dt):
    if dhtRele == 1:
        global dhtCheck, dhtReleTimer, dhtCheckRele
        Clock.unschedule(dhtReleTimer)
        dhtCheckRele = 0
        try:
            dhtReleread = json.loads(urllib2.urlopen("http://" + dhtReleIP + "/dati", None, 3).read())
            dhtCheckRele = dhtReleread["S_control"]
            log(LOG_LEVEL_DEBUG, CHILD_DEVICE_DHTRELE, MSG_SUBTYPE_CUSTOM + "/read/dhtRele/", str(dhtCheckRele),
                timestamp=False)
        except:

            log(LOG_LEVEL_ERROR, CHILD_DEVICE_DHTRELE, MSG_SUBTYPE_CUSTOM + "/read/dhtRele/", str(dhtCheckRele),
                timestamp=False)
            dhtcheckRele = 5000
        dhtReleTimer = Clock.schedule_once(dhtReleRead, settings.get("dht_rele")["rele_timeout"])


def test_dht(dt):
    with dhtLock:
        if dhtZone_number > 0:
            for c in range(0, dhtZone_number):
                t = Thread(target=testDhtLan(c, 1))
                t.start()
        if dhtIr_number > 0:
            for c in range(0, dhtIr_number):
                t = Thread(target=testDhtLan(c, 2))
                t.start()

    dhtLanTimer = Clock.schedule_once(test_dht, 900)


def testDhtLan(c, comando):
    try:
        if comando == 1:
            dhtLanRead = urllib2.urlopen(dhtZone[c, 1] + "/testLan", None, 3).read()
        elif comando == 2:
            dhtLanRead = urllib2.urlopen(dhtIR[c, 1] + "/testLan", None, 3).read()
        if comando == 1:
            dhtZone[c, 7] = 1
            log(LOG_LEVEL_INFO, CHILD_DEVICE_DHTZONE, MSG_SUBTYPE_CUSTOM + "/test/dhtZone/", "Presente",
                timestamp=False)
        elif comando == 2:
            dhtIR[c, 7] = 1
            log(LOG_LEVEL_INFO, CHILD_DEVICE_DHTIR, MSG_SUBTYPE_CUSTOM + "/read/dhtRele/", "Presente", timestamp=False)
    except:
        if comando == 1:
            dhtZone[c, 7] = 0
            dhtZoneLabel[c, 0].text = "[b]    - " + dhtZone[c, 2] + "[/b] - \n \n " + dhtZone[
                c, 1] + "\n\n Zona Non raggiungibile\n\n"
            log(LOG_LEVEL_ERROR, CHILD_DEVICE_DHTZONE, MSG_SUBTYPE_CUSTOM + "/test/dhtZone/", "Non Raggiungibile",
                timestamp=False)
        elif comando == 2:
            dhtIR[c, 7] = 0
            dhtIRLabel[c, 0].text = "[b]    - " + dhtIR[c, 2] + "[/b] - \n \n " + dhtIR[
                c, 1] + "\n\n Zona Non raggiungibile\n\n"
            log(LOG_LEVEL_ERROR, CHILD_DEVICE_DHTZONE, MSG_SUBTYPE_CUSTOM + "/test/dhtZone/", "Non Raggiungibile",
                timestamp=False)


##########################################################################
## Telegram Section
#########################################################################
def logTermostat(errore):
    out_file = open(("./log/" + "telegramlog.csv"), "a")
    out_file.write(time.strftime("%Y/%m/%d %H:%M:%S", time.localtime()) + ", " + errore + "\n")
    out_file.close()
    
def closeTelegram(chat_id,dt):
    global telegramTimeout,chatIdTest,testTimeout
    if testTimeout > 0:
        try:
            bot.sendMessage(chat_id, "Bot disabilitato.... Stand bye")
        except telepot.exception.TelegramError:
            logTermostat("Error during Closing..")
    testTimeout = 0
    chatIdTest = 0
    
if telegramSend == 1:
    bot = telepot.Bot(settings.get("telegram")["token"])
    with thermostatLock:
        def handle(msg):
            global telegramTimeout, chatIdTest,testTimeout
            try:
                chat_id = msg['chat']['id']
                command = msg['text']
                #print 'Got command: %s' % command
                #print chat_id
                if command == "/"+ settings.get("telegram")["pwd"] and chatIdTest == 0:
                    chatIdTest = chat_id
                    testTimeout = 100
                    Clock.schedule_once(partial(closeTelegram,chat_id), telegramTimeout)
                    bot.sendMessage(chat_id, "Pwd OK - Bot Abilitato per id : "+ str(chatIdTest)+" per : "+str(telegramTimeout)+"sec")
                else:
                    if chatIdTest == chat_id and testTimeout > 0:
                        telegramCommand(command,chat_id)
            except telepot.exception.TelegramError:
                logTermostat("Error during Pwd access..")
def telegramCommand(command,chat_id):
    try:
        if command == "/ip":
            f = get("https://api.ipify.org").text
            look_ip = str(f)
            if settings.get("upnp")["enabled"] == 1:
                try: 
                    test_upnp = open_upnp()
                except: 
                    test_upnp = 100
            if cherrypy.server.socket_port == 443:
                    if test_upnp == 200:
                        bot.sendMessage(chat_id, "Da Internet Thermostat su: https://" + look_ip + ":"+str(settings.get("upnp")["ext_port"]))
                    else :
                        bot.sendMessage(chat_id, "Da Internet Thermostat su: https://" + look_ip )
                        bot.sendMessage(chat_id, "add :port open in you router no upnp ")
            else:
                bot.sendMessage(chat_id, "Da Internet Thermostat su: http://" + look_ip + "/")
            ip_int = str(get_ip_address())
            if cherrypy.server.socket_port == 443:
                bot.sendMessage(chat_id, "Da Lan Thermostat su: https://" + ip_int )
            else:
                bot.sendMessage(chat_id, "Da Lan Thermostat su: http://" + ip_int )
        elif command == "/stato":
            bot.sendMessage(chat_id, test_ip)
        elif command == "/time":
            bot.sendMessage(chat_id, str(datetime.datetime.now().strftime("%H:%M -- %d/%m/%Y")))
        elif command[:8] == "/settemp":
            tempe_set = command[command.index(":")+1:]
            #print str(tempe_set),str(setTemp)
            settaTemp(float(tempe_set))
            change_system_settings()
            bot.sendMessage(chat_id, "Set Temp : "+str(setTemp))
            bot.sendMessage(chat_id, test_ip)
        elif command == "/help":
            risposta = "/ip : leggi ip Thermostat \n/time : leggi ora Thermostat \n/stato : leggi lo stato di Thermostat \n/settemp:20.0 : setta Temperatura \n/inverno : setta Sistema per inverno \n/estate : setta Sistema per Estate \n/manuale : prima settare Estate o Inverno quindi setta Il Funzionamento Manuale \n/off : Setta NoIce \n/close : Chiude Bot in questa Connessione\n/help : leggi i comandi possibili"
            bot.sendMessage(chat_id,risposta)
        elif command == "/inverno":
            setControlState(heatControl, "down")
            holdControl.state="normal"
            change_system_settings()
            bot.sendMessage(chat_id,"Settato Inverno")
            bot.sendMessage(chat_id, test_ip)
        elif command == "/estate":
            setControlState(coolControl, "down")
            holdControl.state="normal"
            change_system_settings()
            bot.sendMessage(chat_id,"Settato Estate")
            bot.sendMessage(chat_id, test_ip)
        elif command == "/manuale":
            setControlState(holdControl, "down")
            change_system_settings()
            bot.sendMessage(chat_id,"Settato Manuale")
            bot.sendMessage(chat_id, test_ip)
        elif command =="/off":
            holdControl.state="normal"
            coolControl.state="normal"
            setControlState(heatControl, "normal")
            change_system_settings()
            bot.sendMessage(chat_id, test_ip)
        elif command == "/close":
            Clock.unschedule(closeTelegram)
            Clock.schedule_once(partial(closeTelegram,chat_id), 0.4)
            bot.sendMessage(chat_id, "Disabilitazione Bot......")
    except telepot.exception.TelegramError:
        logTermostat("Error during Command: "+command)

##############################################################################
#                                                                            #
#       UI Controls/Widgets                                                  #
#                                                                            #
##############################################################################

controlColours = {
    "normal": (1.0, 1.0, 1.0, 1.0),
    "Cool": (1.0, 1.0, 1.0, 1.0),
    "Heat": (1.0, 1.0, 1.0, 1.0),
    "Hold": (1.0, 1.0, 1.0, 1.0),
}


def setControlState(control, state):
    global setTemp, tempStep, dhtIr_number
    with thermostatLock:
        control.state = state
        if control == coolControl and state == "down":
            if dhtIr_number > 0:
                tempStep = 1
                setTemp = round(int(setTemp), 1)

            else:
                setControlState(coolControl, "normal")

        elif control == heatControl and state == "down":
            tempStep = 0.5 if not (settings.exists("thermostat")) else settings.get("thermostat")["tempStep"]


        elif coolControl.state == "normal" and heatControl.state == "normal":
            tempStep = 0.5 if not (settings.exists("thermostat")) else settings.get("thermostat")["tempStep"]


        # if state == "normal":
        #	control.background_color = controlColours[ "normal" ]
        # else:
        #	control.background_color = controlColours[ control.text.replace( "[b]", "" ).replace( "[/b]", "" ) ]
        controlLabel = control.text.replace("[b]", "").replace("[/b]", "").lower()
        log(LOG_LEVEL_INFO, controlLabel + CHILD_DEVICE_SUFFIX_UICONTROL, MSG_SUBTYPE_BINARY_STATUS,
            "0" if state == "normal" else "1")


coolControl = ToggleButton(text="[b]       Estate  [/b]",
						   markup=True,
						   size_hint=(None, None),
						   font_size="28sp",
						   border=(0, 0, 0, 0),
						   background_normal="web/images/button_1.png",
						   background_down="web/images/button_21.png",
						   color=(1, 1, 1, 1)
						   )

heatControl = ToggleButton(text="[b]         Inverno  [/b]",
                           markup=True,
                           size_hint=(None, None),
                           font_size="28sp",
                           border=(0, 0, 0, 0),
                           background_normal="web/images/button_1.png",
                           background_down="web/images/button_11.png",
                           color=(1, 1, 1, 1)
                           )

holdControl = ToggleButton(text="[b]           Manuale  [/b]",
                           markup=True,
                           size_hint=(None, None),
                           font_size="28sp",
                           border=(0, 0, 0, 0),
                           background_normal="web/images/button_1.png",
                           background_down="web/images/button_31.png",
                           color=(1, 1, 1, 1)
                           )

holdControl.state = "normal" if not (state.exists("state")) else state.get("state")["holdControl"]
if holdControl.state == "down":
    setControlState(holdControl, holdControl.state)
coolControl.state = "normal" if not (state.exists("state")) else state.get("state")["coolControl"]
if coolControl.state == "down":
    setControlState(coolControl, coolControl.state)
heatControl.state = "normal" if not (state.exists("state")) else state.get("state")["heatControl"]
if heatControl.state == "down":
    setControlState(heatControl, heatControl.state)
if heatControl.state == "normal" and coolControl.state == "normal":
    setControlState(heatControl, heatControl.state)

plusControl = Button(text="",
                     markup=True,
                     size_hint=(None, None),
                     font_size="28sp",
                     border=(0, 0, 0, 0),
                     background_normal="web/images/plus.png",
                     background_down="web/images/plus_1.png",
                     color=(1, 1, 1, 1)
                     )

minusControl = Button(text="",
                      markup=True,
                      size_hint=(None, None),
                      font_size="28sp",
                      border=(0, 0, 0, 0),
                      background_normal="web/images/minus.png",
                      background_down="web/images/minus_1.png",
                      color=(1, 1, 1, 1)
                      )


def get_status_string():
    global test_ip,sched
    with thermostatLock:
        sched = "None"
        temperature = 0
        if holdControl.state == "down":
            sched = "Manuale"
            if heatControl.state == "down":
                testText = "Caldaia"
            else:
                testText = "Clima"
            temperature = setTemp
        elif useTestSchedule:
            sched = "Test"
            temperature = setTemp
        elif heatControl.state == "down":
            testText = "Caldaia"
            if dhtSchedule == 0:
                sched = "Inverno"
            else:
                sched = "Dht "
            temperature = setTemp
        elif coolControl.state == "down":
            testText = "Clima"
            sched = "Estate"
            temperature = setTemp
        else:
            testText = "Caldaia"
            sched = "No Ice"
            temperature = settings.get("thermostat")["tempice"]
            testHeat = False
        if GPIO.input(heatPin) == 0:
            testHeat = True
        elif GPIO.input(coolPin) == 0:
            testHeat = True
        else:
            testHeat = False

        setLabel.color = (1, 1, 1, 1)

        test_ip = "SetTemp : " + str(temperature) + "\nTemp IN : " + str(currentTemp) + "\nSchedule : " + sched +"\nSistema : "+("ON" if testHeat else "OFF")

        return "  Temp. Set: [b][color=#5F81F1]" + str(temperature) + scaleUnits + "[/b][/color]\n  " + \
               testText + " :    " + (
               "[i][b][color=ff3333]On[/b][/i][/color]" if testHeat else "[b][color=#5F81F1]Off[/b][/color]") + "\n  " + \
               "Prog :  [b][color=#5F81F1]" + sched + "[/b][/color]"


versionLabel = Label(text="Thermostat v" + str(THERMOSTAT_VERSION), size_hint=(None, None), font_size='10sp',
                     markup=True, text_size=(150, 20))
umiditaLabel = Label(text="", size_hint=(None, None), font_size='20sp', markup=True, text_size=(150, 70))
currentLabel = Label(text="[b]" + str(currentTemp) + scaleUnits + "[/b]", size_hint=(None, None), font_size='100sp',
                     markup=True, text_size=(300, 200))
altCurLabel = Label(text=currentLabel.text, size_hint=(None, None), font_size='100sp', markup=True,
                    text_size=(300, 200), color=(0.5, 0.5, 0.5, 0.4))

setLabel = Label(text="[b]" + str(round(setTemp, 1)) + " " + "[/b]", size_hint=(None, None), font_size='40sp',
                 markup=True, text_size=(120, 120))
statusLabel = Label(text="\n   Thermostat \n    version " + str(THERMOSTAT_VERSION) + "\n    Starting.....",
                    size_hint=(None, None), font_size='30sp', markup=True, text_size=(240, 230))

altStatusLabel = Label(text="", size_hint=(None, None), markup=True, font_size='30sp', text_size=(400, 400),
                       color=(0.3, 0.3, 0.3, 0.4))

dateLabel = Label(text="[b]" + time.strftime("%d %b %a, %Y") + "[/b]", size_hint=(None, None), font_size='25sp',
                  markup=True, text_size=(270, 40))

timeStr = time.strftime("%H:%M").lower()
timeInit = time.time()

timeLabel = Label(text="[b]" + (timeStr if timeStr[0:1] != "0" else timeStr[1:]) + "[/b]", size_hint=(None, None),
                  font_size='45sp', markup=True, text_size=(180, 75))
altTimeLabel = Label(text=timeLabel.text, size_hint=(None, None), font_size='40sp', markup=True, text_size=(180, 75),
                     color=(0.5, 0.5, 0.5, 0.2))

screenMgr = None

#############################################################################
#                                                                            #
#       Weather functions/constants/widgets                                  #
#                                                                            #
##############################################################################

weatherLocation = settings.get("weather")["location"]
weatherAppKey = settings.get("weather")["appkey"]
weatherURLBase = "https://api.darksky.net/forecast/"
weatherURLTimeout = settings.get("weather")["URLtimeout"]
weatherURLCurrent = weatherURLBase + weatherAppKey + "/" + weatherLocation + "?units=si&exclude=[minutely,hourly,flags,alerts]&lang=it"

forecastRefreshInterval = settings.get("weather")["forecastRefreshInterval"] * 60
weatherExceptionInterval = settings.get("weather")["weatherExceptionInterval"] * 60
weatherRefreshInterval = settings.get("weather")["weatherRefreshInterval"] * 60

weatherSummaryLabel = Label(text="", size_hint=(None, None), font_size='20sp', markup=True, text_size=(200, 20))
weatherDetailsLabel = Label(text="", size_hint=(None, None), font_size='20sp', markup=True, text_size=(300, 150),
                            valign="top")
weatherImg = Image(source="web/images/na.png", size_hint=(None, None))
weatherminSummaryLabel = Label(text="", size_hint=(None, None), font_size='20sp', markup=True, text_size=(200, 20),
                               color=(0.5, 0.5, 0.5, 0.2))
weatherminImg = Image(source="web/images/na.png", size_hint=(None, None), color=(1, 1, 1, 0.4))
forecastData = []
forecastSummaryLabel = []
forecastDetailsLabel = []
forecastImg = []
for c in range(0, 3):
    forecastData.append(Label(text="", size_hint=(None, None), font_size='16sp', markup=True, text_size=(300, 20)))
    forecastSummaryLabel.append(
        Label(text="", size_hint=(None, None), font_size='16sp', markup=True, text_size=(250, 50)))
    forecastDetailsLabel.append(
        Label(text="", size_hint=(None, None), font_size='16sp', markup=True, text_size=(300, 150), valign="top"))
    forecastImg.append(Image(source="web/images/na.png", size_hint=(None, None)))
forecastSummary = Label(text="", size_hint=(None, None), font_size='18sp', markup=True, text_size=(800, 50))


def get_cardinal_direction(heading):
    directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW", "N"]
    return directions[int(round(((heading % 360) / 45)))]


def display_current_weather(dt):
    with weatherLock:
        global out_temp, out_humidity, temp_vis
        interval = weatherRefreshInterval
        try:

            weather = json.loads(urllib2.urlopen(weatherURLCurrent, None, weatherURLTimeout).read())
            weatherImg.source = "web/images/" + weather["currently"]["icon"] + ".png"
            weatherSummaryLabel.text = "[b]" + weather["currently"]["summary"] + "[/b]"
            forecastSummary.text = "[b]" + weather["daily"]["summary"] + "[/b]"
            # compile data for forecast
            for c in range(0, 3):
                today = weather["daily"]["data"][c]
                forecastData[c].text = "[b]" + time.strftime('%A  %d/%m ', time.localtime(today["time"])) + "[/b]"
                forecastImg[c].source = "web/images/" + today["icon"] + ".png"
                forecastSummaryLabel[c].text = "[b]" + today["summary"][:-1] + "[/b] "
                forecastText = "\n".join((
                    "Max: " + str(int(round(today["temperatureMax"], 0))) + "        Min: " + str(
                        int(round(today["temperatureMin"], 0))),
                    "Umidita:        " + str(today["humidity"] * 100) + "%",

                    "Nuvole:          " + str(today["cloudCover"] * 100) + "%",

                    "Pressione:     " + str(int(today["pressure"])) + "mBar",

                    "Vento:            " + str(
                        int(round(today["windSpeed"] * windFactor))) + windUnits + " " + get_cardinal_direction(
                        today["windBearing"]),

                ))

                forecastDetailsLabel[c].text = forecastText
            if dhtoutEnabled == 1:
                dhtoutRead()
                if out_temp == 0:
                    temp_vis = str(int(round(weather["currently"]["temperature"], 1)))
                    um_vis = str(int(round(weather["currently"]["humidity"], 2) * 100))
                else:

                    temp_vis = str(round(out_temp, 1))
                    um_vis = str(int(round(out_humidity, 0)))
            else:
                temp_vis = str(int(round(weather["currently"]["temperature"], 1)))

                um_vis = str(int(round(weather["currently"]["humidity"], 2) * 100))
            weatherDetailsLabel.text = "\n".join((
                "Temp :   " + temp_vis + " " + scaleUnits,
                "  Ur :   " + um_vis + "%"

                # "Vento:       " + str( int( round( weather[ "wind" ][ "speed" ] * windFactor ) ) ) + windUnits + " " + get_cardinal_direction( weather[ "wind" ][ "deg" ] ),
                # "Nuvole:     " + str( weather[ "clouds" ][ "all" ] ) + "%",
            ))
            log(LOG_LEVEL_INFO, CHILD_DEVICE_WEATHER_CURR, MSG_SUBTYPE_TEXT,
                weather["currently"]["summary"] + "; " + re.sub('\n', "; ", re.sub(' +', ' ', temp_vis).strip()))

        except:
            interval = weatherExceptionInterval

            weatherImg.source = "web/images/na.png"
            weatherSummaryLabel.text = ""
            weatherDetailsLabel.text = ""

            log(LOG_LEVEL_ERROR, CHILD_DEVICE_WEATHER_CURR, MSG_SUBTYPE_TEXT, "Update FAILED!")

        Clock.schedule_once(display_current_weather, interval)


def get_precip_amount(raw):
    precip = round(raw * precipFactor, precipRound)

    if tempScale == "metric":
        return str(int(precip))
    else:
        return str(precip)


##############################################################################
#                                                                            #
#       Utility Functions                                                    #
#                                                                            #
##############################################################################

def get_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(10)  # 10 seconds
    try:
        s.connect(("8.8.8.8", 80))  # Google DNS server
        ip = s.getsockname()[0]
        log(LOG_LEVEL_INFO, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/settings/ip", ip, timestamp=False)
    except socket.error:
        ip = "127.0.0.1"
        log(LOG_LEVEL_ERROR, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/settings/ip",
            "FAILED to get ip address, returning " + ip, timestamp=False)

    return ip

def settaTemp(temperature):
    global setTemp
    setTemp = round(temperature, 1)
    #print setTemp,temperature
    setLabel.text = "[b]" + str(round(setTemp, 1)) + "[/b]"
    
def getVersion():
    log(LOG_LEVEL_STATE, CHILD_DEVICE_NODE, MSG_SUBTYPE_VERSION, THERMOSTAT_VERSION)


def restart():
    log(LOG_LEVEL_STATE, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/restart", "Thermostat restarting...", single=True)
    GPIO.cleanup()

    if logFile is not None:
        logFile.flush()
        os.fsync(logFile.fileno())
        logFile.close()

    os.execl(sys.executable, 'python', __file__, *sys.argv[1:])  # This does not return!!!


def setLogLevel(msg):
    global logLevel

    if LOG_LEVELS.get(msg.payload):
        log(LOG_LEVEL_STATE, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/loglevel", "LogLevel set to: " + msg.payload)

        logLevel = LOG_LEVELS.get(msg.payload, logLevel)
    else:
        log(LOG_LEVEL_ERROR, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/loglevel", "Invalid LogLevel: " + msg.payload)
#####################################################################################
##  UPNP routines
#####################################################################################
def open_upnp():
    res = discover()
    for path in res:
        discparsed = urlparse(path)
        service_path = get_wanip_path(path)
        service_url = "%s://%s%s"%(discparsed.scheme,discparsed.netloc,service_path)
        routerip = discparsed.netloc.split(':')[0]

        localip = get_my_ip(routerip)

        dis='Upnp :  '

        status,message = open_port(service_url,settings.get("upnp")["ext_port"],internal_client=localip,internal_port=443,protocol="TCP",duration=settings.get("upnp")["time"],description="thermo_web",enabled = 1)
        if status==200:
                print "%sport forward on %s successful, %s->%s:%s"%(dis,routerip,settings.get("upnp")["ext_port"],localip,"443")
        else:
            sys.stderr.write("%sport forward on %s failed, status=%s message=%s\n"%(dis,routerip,status,message))
            allok = False
        return status
    
def discover():
    """Discover UPNP capable routers in the local network
    Returns a lit of urls with service descriptions
    """
    SSDP_ADDR = "239.255.255.250"
    SSDP_PORT = 1900
    SSDP_MX = 2
    SSDP_ST = "urn:schemas-upnp-org:device:InternetGatewayDevice:1"

    WAIT = 1

    ssdpRequest = "M-SEARCH * HTTP/1.1\r\n" + \
                    "HOST: %s:%d\r\n" % (SSDP_ADDR, SSDP_PORT) + \
                    "MAN: \"ssdp:discover\"\r\n" + \
                    "MX: %d\r\n" % (SSDP_MX, ) + \
                    "ST: %s\r\n" % (SSDP_ST, ) + "\r\n"

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setblocking(0)
    sock.sendto(ssdpRequest, (SSDP_ADDR, SSDP_PORT))
    time.sleep(WAIT)
    paths = []
    for _ in range(10):
        try:
            data, fromaddr = sock.recvfrom(1024)
            ip = fromaddr[0]
            #print "from ip: %s"%ip
            parsed = re.findall(r'(?P<name>.*?): (?P<value>.*?)\r\n', data)

            # get the location header
            location = filter(lambda x: x[0].lower() == "location", parsed)

            # use the urlparse function to create an easy to use object to hold a URL
            router_path = location[0][1]
            paths.append(router_path)

        except socket.error:
            '''no data yet'''
            break
    return paths


def get_wanip_path(upnp_url):
    # get the profile xml file and read it into a variable
    directory = urllib2.urlopen(upnp_url).read()

    # create a DOM object that represents the `directory` document
    dom = parseString(directory)

    # find all 'serviceType' elements
    service_types = dom.getElementsByTagName('serviceType')

    # iterate over service_types until we get either WANIPConnection
    # (this should also check for WANPPPConnection, which, if I remember correctly
    # exposed a similar SOAP interface on ADSL routers.
    for service in service_types:
        # I'm using the fact that a 'serviceType' element contains a single text node, who's data can
        # be accessed by the 'data' attribute.
        # When I find the right element, I take a step up into its parent and search for 'controlURL'
        if service.childNodes[0].data.find('WANIPConnection') > 0:
            path = service.parentNode.getElementsByTagName('controlURL')[0].childNodes[0].data
            return path

def open_port(service_url,external_port,internal_client,internal_port=None,protocol='TCP',duration=0,description=None,enabled=1):
    parsedurl = urlparse(service_url)

    if internal_port==None:
        internal_port = external_port

    if description == None:
        description = 'generated by port-forward.py'

    if not enabled:
        duration=1

    doc = Document()

    # create the envelope element and set its attributes
    envelope = doc.createElementNS('', 's:Envelope')
    envelope.setAttribute('xmlns:s', 'http://schemas.xmlsoap.org/soap/envelope/')
    envelope.setAttribute('s:encodingStyle', 'http://schemas.xmlsoap.org/soap/encoding/')

    # create the body element
    body = doc.createElementNS('', 's:Body')

    # create the function element and set its attribute
    fn = doc.createElementNS('', 'u:AddPortMapping')
    fn.setAttribute('xmlns:u', 'urn:schemas-upnp-org:service:WANIPConnection:1')

    # setup the argument element names and values
    # using a list of tuples to preserve order
    arguments = [
        ('NewRemoteHost', ""), # unused - but required
        ('NewExternalPort', external_port),           # specify port on router
        ('NewProtocol', protocol),                 # specify protocol
        ('NewInternalPort', internal_port),           # specify port on internal host
        ('NewInternalClient', internal_client), # specify IP of internal host
        ('NewEnabled', enabled),                    # turn mapping ON
        ('NewPortMappingDescription', description), # add a description
        ('NewLeaseDuration', duration)]              # how long should it be opened?

    # NewEnabled should be 1 by default, but better supply it.
    # NewPortMappingDescription Can be anything you want, even an empty string.
    # NewLeaseDuration can be any integer BUT some UPnP devices don't support it,
    # so set it to 0 for better compatibility.

    # container for created nodes
    argument_list = []

    # iterate over arguments, create nodes, create text nodes,
    # append text nodes to nodes, and finally add the ready product
    # to argument_list
    for k, v in arguments:
        v = str(v)
        tmp_node = doc.createElement(k)
        tmp_text_node = doc.createTextNode(v)
        tmp_node.appendChild(tmp_text_node)
        argument_list.append(tmp_node)

    # append the prepared argument nodes to the function element
    for arg in argument_list:
        fn.appendChild(arg)

    # append function element to the body element
    body.appendChild(fn)

    # append body element to envelope element
    envelope.appendChild(body)

    # append envelope element to document, making it the root element
    doc.appendChild(envelope)

    # our tree is ready, conver it to a string
    pure_xml = doc.toxml()

    # use the object returned by urlparse.urlparse to get the hostname and port
    conn = httplib.HTTPConnection(parsedurl.hostname, parsedurl.port)

    # use the path of WANIPConnection (or WANPPPConnection) to target that service,
    # insert the xml payload,
    # add two headers to make tell the server what we're sending exactly.
    conn.request('POST',
        parsedurl.path,
        pure_xml,
        {'SOAPAction': '"urn:schemas-upnp-org:service:WANIPConnection:1#AddPortMapping"',
         'Content-Type': 'text/xml'}
    )

    # wait for a response
    resp = conn.getresponse()

    return resp.status,resp.read()


def get_my_ip(routerip=None):
    if routerip==None:
        routerip="8.8.8.8" #default route
    ret = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect((routerip,80))
        ret = s.getsockname()[0]
        s.close()
    except:
        pass
    return ret

   


##############################################################################
#                                                                            #
#       Thermostat Implementation                                            #
#                                                                            #
##############################################################################

# Main furnace/AC system control function:

def change_system_settings():
    with thermostatLock:
        global csvSaver, dhtCheckRele, dhtCheckZone, dhtCheckIr, dhtCheckIce
        hpin_start = str(GPIO.input(heatPin))
        cool_start = str(GPIO.input(coolPin))
        if heatControl.state == "down":
            if dhtCheckZone == 0:
                Clock.unschedule(dhtIrTimer)
                dhtReleRead(0.5)
                dhtCheckIr = 0
                dhtCheckIce = 0
                dhtZoneSend(0.5)
                dhtZoneRead(0.5)
            if setTemp >= currentTemp + tempHysteresis or dhtCheckZone == 3:
                if dhtRele == 1 and dhtCheckRele <= 200:
                    dhtReleSend("releON")
                    dhtReleRead(0.5)
                GPIO.output(heatPin, GPIO.LOW)
                GPIO.output(coolPin, GPIO.HIGH)
            elif setTemp <= currentTemp:
                if dhtRele == 1 and dhtCheckRele >= 201:
                    dhtReleSend("releOFF")
                    dhtReleRead(0.5)
                GPIO.output(heatPin, GPIO.HIGH)
                GPIO.output(coolPin, GPIO.HIGH)
        elif coolControl.state == "down":
            if dhtCheckIr == 1:
                GPIO.output(coolPin, GPIO.LOW)
                GPIO.output(heatPin, GPIO.HIGH)

            elif dhtCheckIr == 2:
                GPIO.output(coolPin, GPIO.HIGH)
                GPIO.output(heatPin, GPIO.HIGH)

            else:
                GPIO.output(coolPin, GPIO.LOW)
                GPIO.output(heatPin, GPIO.HIGH)
                Clock.unschedule(dhtZoneTimer)
                Clock.unschedule(dhtReleTimer)
                dhtCheckZone = 0
                dhtIRSend(0.5)
                dhtIrRead(0.5)
        else:
            # modifica per minima temp antigelo
            if dhtCheckZone == 0:
                dhtCheckIce = 1
                Clock.unschedule(dhtIrTimer)
                dhtCheckIr = 0
                dhtZoneSend(0.5)
                dhtZoneRead(0.5)
            if setice >= currentTemp + tempHysteresis or dhtCheckZone == 3:
                if dhtRele == 1 and dhtCheckRele <= 200:
                    dhtReleSend("releON")
                    dhtReleRead(0.5)
                GPIO.output(heatPin, GPIO.LOW)
                GPIO.output(coolPin, GPIO.HIGH)
            elif setice <= currentTemp:
                if dhtRele == 1 and dhtCheckRele >= 201:
                    dhtReleSend("releOFF")
                    dhtReleRead(0.5)
                GPIO.output(heatPin, GPIO.HIGH)
                GPIO.output(coolPin, GPIO.HIGH)

        # save the thermostat state in case of restart
        state.put("state", setTemp=setTemp, heatControl=heatControl.state, coolControl=coolControl.state,
                  holdControl=holdControl.state, dhtEnabled=dhtEnabled)

        statusLabel.text = get_status_string()
        untrusttext = statusLabel.text.replace("[color=#5F81F1]", "").replace("[/color]", "").replace("[color=ff3333]",
                                                                                                      "")  # .replace("[b]","").replace("[/b]","")
        altStatusLabel.text = "           " + timeLabel.text + "\n[size=100sp][b] " + str(
            currentTemp) + "[/b][/size]\n" + untrusttext
        setLabel.text = "[b]" + str(setTemp) + "[/b]"
        if hpin_start != str(GPIO.input(heatPin)):
            Clock.unschedule(csvSaver)
            csvSaver = Clock.schedule_once(save_graph, 1)
            log(LOG_LEVEL_STATE, CHILD_DEVICE_HEAT, MSG_SUBTYPE_BINARY_STATUS, "1" if GPIO.input(heatPin) else "0")
        if cool_start != str(GPIO.input(coolPin)):
            Clock.unschedule(csvSaver)
            csvSaver = Clock.schedule_once(save_graph, 1)
            log(LOG_LEVEL_STATE, CHILD_DEVICE_HEAT, MSG_SUBTYPE_BINARY_STATUS, "1" if GPIO.input(coolPin) else "0")
        try:
            if settings.get("thermostat")["checkPin"] == 1:
                print "Gpio heat : " ,str(GPIO.input(heatPin))," - Gpio cool : ",str(GPIO.input(coolPin)) , " - pirPin : ",str(GPIO.input(pirPin)), " - Light Pin :",str(GPIO.input(lightPin))
                print "Stato check Dht  - DhtIR: ",dhtCheckIr," - dhtZone : ",dhtCheckZone," - dhtCheckRele : ",dhtCheckRele 
        except:
            log(LOG_LEVEL_STATE, CHILD_DEVICE_HEAT, MSG_SUBTYPE_BINARY_STATUS, "print pin error.....")

# This callback will be bound to the touch screen UI buttons:

def control_callback(control):
    global setTemp, dhtCheckZone, dhtCheckIr, dhtCheckRele
    with thermostatLock:
        # Azzeriamo tutto cosi poi il check Rimette a Posto Tutto#
        ##########################################################

        Clock.unschedule(dhtZoneTimer)
        Clock.unschedule(dhtReleTimer)
        Clock.unschedule(dhtIrTimer)
        Clock.schedule_once(clear_dht, 1)
        dhtCheckIr = 0
        dhtCheckZone = 0
        dhtCheckRele = 0
        ###########################################################
        statusLabel.text = "\n  Aggiorno \n  Stato \n  Sistema  ......"
        altStatusLabel.text = "\n  Aggiorno \n  Stato \n  Sistema  ......"
        setControlState(control, control.state)  # make sure we change the background colour!
        if control is holdControl:
            if control.state == "down" and heatControl.state == "normal" and coolControl.state == "normal":
                holdControl.state = "normal"
                reloadSchedule()
            elif control.state == "down" and heatControl.state == "down":
                reloadSchedule()

            elif control.state == "down" and coolControl.state == "down":
                reloadSchedule()
            elif control.state == "normal":

                reloadSchedule()
        elif control is coolControl:
            if dhtIr_number > 0:
                if control.state == "down":
                    setControlState(heatControl, "normal")
                    holdControl.state = "normal"
                else:
                    coolControl.state = "normal"
                    holdControl.state = "normal"
            else:
                coolControl.state = "normal"
                holdControl.state = "normal"

        elif control is heatControl:
            if control.state == "down":
                setControlState(coolControl, "normal")
                holdControl.state = "normal"
            holdControl.state = "normal"


# Check the current sensor temperature

def check_sensor_temp(dt):
    with thermostatLock:
        global currentTemp, priorCorrected
        global tempSensor, dhtTemp, openDoor, openDoorCheck
        correctedTemp = 20
        if dhtEnabled == 1 and dhtTemp <> 0:
            rawTemp = dhtTemp
            #print rawTemp
            correctedTemp = (((rawTemp - freezingMeasured) * referenceRange) / measuredRange) + freezingPoint + dhtCorrect
            log(LOG_LEVEL_DEBUG, CHILD_DEVICE_TEMP, MSG_SUBTYPE_CUSTOM + "/dhtTemp", str(rawTemp))
            log(LOG_LEVEL_DEBUG, CHILD_DEVICE_TEMP, MSG_SUBTYPE_CUSTOM + "/corrected", str(correctedTemp))
            #print rawTemp,correctedTemp
        else:
            if tempSensor is not None:
                #print ("check temp")
                if (typeSensor == 0):
                    rawTemp = tempSensor.get_temperature(sensorUnits)
                    #print ("ds1820 Temp :", rawTemp)
                else:
                    letHum, letTemp = Adafruit_DHT.read_retry(dht, dhtpin)
                    #print    ("dht Temp: ", letTemp)
                    if letHum is not None and letTemp is not None:
                        rawTemp = letTemp
                correctedTemp = (((rawTemp - freezingMeasured) * referenceRange) / measuredRange) + freezingPoint + correctSensor
                log(LOG_LEVEL_DEBUG, CHILD_DEVICE_TEMP, MSG_SUBTYPE_CUSTOM + "/raw", str(rawTemp))
                log(LOG_LEVEL_DEBUG, CHILD_DEVICE_TEMP, MSG_SUBTYPE_CUSTOM + "/corrected", str(correctedTemp))
        if abs(priorCorrected - correctedTemp) >= TEMP_TOLERANCE:
            if abs(priorCorrected - correctedTemp) >= 1 and openDoor <= openDoorCheck:
                openDoor += 1
            else:
                openDoor == 0
                log(LOG_LEVEL_STATE, CHILD_DEVICE_TEMP, MSG_SUBTYPE_TEMPERATURE, str(currentTemp))
                priorCorrected = correctedTemp
                currentTemp = round(correctedTemp, 1)

        currentLabel.text = "[b]" + str(currentTemp) + scaleUnits + "[/b]"
        altCurLabel.text = currentLabel.text

        dateLabel.text = "[b]" + time.strftime("%d %b %a, %Y") + "[/b]"

        timeStr = time.strftime("%H:%M").lower()

        timeLabel.text = ("[b]" + (timeStr if timeStr[0:1] != "0" else timeStr[1:]) + "[/b]").lower()
        altTimeLabel.text = timeLabel.text

        change_system_settings()


# This is called when the desired temp slider is updated:

def update_set_temp(control):
    with thermostatLock:
        global setTemp, tempStep,maxTemp,minTemp
        priorTemp = setTemp
        if control is plusControl:
            setTemp = priorTemp + tempStep
            if setTemp >= maxTemp:
                setTemp = maxTemp
        if control is minusControl:
            setTemp = priorTemp - tempStep
            if setTemp <= minTemp:
                setTemp = minTemp
        setLabel.text = "[b]" + str(round(setTemp, 1)) + "[/b]"
        if heatControl.state == "down":
            Clock.schedule_once(dhtZoneSend, 1)
        if coolControl.state == "down":
            Clock.schedule_once(dhtIRSend, 1)
        if priorTemp != setTemp:
            log(LOG_LEVEL_STATE, "Set Temperature", MSG_SUBTYPE_TEMPERATURE, str(setTemp))


# Check the PIR motion sensor status

def check_pir(pin):
    global minUITimer
    global lightOffTimer
    with thermostatLock:
        if GPIO.input(pirPin):
            log(LOG_LEVEL_INFO, CHILD_DEVICE_PIR, MSG_SUBTYPE_TRIPPED, "1")

            if minUITimer != None:
                Clock.unschedule(show_minimal_ui)
                if lightOffTimer != None:
                    Clock.unschedule(light_off)
            minUITimer = Clock.schedule_once(show_minimal_ui, minUITimeout)
            lighOffTimer = Clock.schedule_once(light_off, lightOff)
            ignore = False
            now = datetime.datetime.now().time()

            if pirIgnoreFrom > pirIgnoreTo:
                if now >= pirIgnoreFrom or now < pirIgnoreTo:
                    ignore = True
            else:
                if now >= pirIgnoreFrom and now < pirIgnoreTo:
                    ignore = True

            if screenMgr.current == "minimalUI" and not (ignore):
                screenMgr.current = "thermostatUI"
                log(LOG_LEVEL_DEBUG, CHILD_DEVICE_SCREEN, MSG_SUBTYPE_TEXT, "Full")

        else:
            log(LOG_LEVEL_DEBUG, CHILD_DEVICE_PIR, MSG_SUBTYPE_TRIPPED, "0")


# Salvo i dati per il grafico
def save_graph(dt):
    # save graph
    # conversione heatpin in temperatura 10=off 12=on
    global csvSaver,sched
    global csvTimeout
    Clock.unschedule(csvSaver)
    switchTemp = 0
    if sched == "No Ice":
            graphtemperature = settings.get("thermostat")["tempice"]
    else:
            graphtemperature = setTemp
            
    if GPIO.input(heatPin) == 0:
        switchTemp = 12
    else:
        if GPIO.input(coolPin) == 0:
            switchTemp = 5
        else:
            switchTemp = 0

        # scrivo il file csv con i dati
    out_file = open(("./web/graph/" + "thermostat.csv"), "a")
    out_file.write(time.strftime("%Y/%m/%d %H:%M:%S", time.localtime()) + ", " + str(graphtemperature) + ", " + str(
        currentTemp) + ", " + str(switchTemp) + "\n")
    out_file.close()
    timeInit = time.time()

    csvSaver = Clock.schedule_once(save_graph, csvTimeout)


# premendo set label change dht enabled


def dht_change(comando):
    global dhtEnabled, dhtSchedule
    global setTemp
    with thermostatLock:
        if heatControl.state == "down":
            setLabel.color = (1, 0.1, 0.1, 1)
            if dhtEnabled == 0 and settings.get("dhtext")["dhtEnabled"] == 1:
                dhtEnabled = 1
                Clock.schedule_once(dht_load, 3)
                reloadSchedule()
                umiditaLabel.color = 1,1,1,1
                # print "dht Enabled"
            else:
                dhtEnabled = 0
                dhtSchedule = 0
                dht_label.text = ""
                Clock.unschedule(dht_load)
                reloadSchedule()
                umiditaLabel.color = 0,0,0,0
                # print "dht Disabled"
                # print "change dht"	,x_pos	,y_pos


# Minimal UI Display functions and classes
# shell.shell(has_input=False, record_output=True, record_errors=True, strip_empty=True)

def show_minimal_ui(dt):
    with thermostatLock:
        global animationTimer
        screenMgr.current = "minimalUI"
        if animationTimer != None:
            Clock.unschedule(animationMinimal)
        animationTimer = Clock.schedule_once(animationMinimal, 5)
        log(LOG_LEVEL_DEBUG, CHILD_DEVICE_SCREEN, MSG_SUBTYPE_TEXT, "Minimal")


def animationMinimal(dt):
    with thermostatLock:
        checkPos = altStatusLabel.pos
        # print checkPos
        anim = Animation(pos=(150, 150), t='linear', d=30)
        anim += Animation(pos=(700, 360), t='linear', d=30)
        anim += Animation(pos=(150, 360), t='linear', d=30)
        anim += Animation(pos=(700, 150), t='linear', d=30)
        anim.repeat = True
        anim.start(altStatusLabel)


def light_off(dt):
    with thermostatLock:
        GPIO.output(lightPin, GPIO.HIGH)
        log(LOG_LEVEL_DEBUG, CHILD_DEVICE_SCREEN, MSG_SUBTYPE_TEXT, "Screen Off")


def select_meteo(testo):
    global minUITimer
    global lightOffTimer
    if minUITimer != None:
        Clock.unschedule(show_minimal_ui)
    if lightOffTimer != None:
        Clock.unschedule(light_off)
    screenMgr.current = "meteoUI"
    Clock.schedule_once(returnScreen, 20)


def select_menu(testo):
    with thermostatLock:
        # print "select menu: ", testo.text
        global minUITimer
        global lightOffTimer
        if testo.text == "Reboot":
            # Window.minimize()
            restart()
        if testo.text == "Stato":
            if minUITimer != None:
                Clock.unschedule(show_minimal_ui)
            if lightOffTimer != None:
                Clock.unschedule(light_off)
            if coolControl.state == "down":
                screenMgr.current = "coolUI"
            else:
                if dhtZone_number > 0:
                    screenMgr.current = "zoneUI"
            Clock.schedule_once(returnScreen, 20)


def open_menu(testo):
    with thermostatLock:
        global minUITimer
        global lightOffTimer
        if minUITimer != None:
            Clock.unschedule(show_minimal_ui)
        if lightOffTimer != None:
            Clock.unschedule(light_off)
        screenMgr.current = "menuUI"
        Clock.schedule_once(returnScreen, 20)


def returnScreen(dt):
    with thermostatLock:
        minUITimer = Clock.schedule_once(show_minimal_ui, minUITimeout)
        lighOffTimer = Clock.schedule_once(light_off, lightOff)
        screenMgr.current = "thermostatUI"


def clear_dht(dt):
    dhtSend("clear")
    reloadSchedule()


def clear_dht_init(dt):
    with thermostatLock:
        statusLabel.text = "\n  Inizializzo \n  Comunicazioni \n  Sistema  ......"
        test_dht(1)
        clear_dht(1)
        # Start checking the temperature
        Clock.schedule_interval(check_sensor_temp, tempCheckInterval)


class MinimalScreen(Screen):
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            touch.grab(self)
            return True

    def on_touch_up(self, touch):
        global minUITimer
        global lightOffTimer
        if touch.grab_current is self:
            touch.ungrab(self)
            with thermostatLock:
                Clock.unschedule(light_off)
                Clock.unschedule(animationTimer)
                if minUITimer != None:
                    Clock.unschedule(show_minimal_ui)
                minUITimer = Clock.schedule_once(show_minimal_ui, minUITimeout)
                lightOffTimer = Clock.schedule_once(light_off, lightOff)
                Animation.stop_all(altStatusLabel)
                Animation.cancel_all(altStatusLabel)
                altStatusLabel.pos = (400, 300)
                GPIO.output(lightPin, GPIO.LOW)
                self.manager.current = "thermostatUI"
                log(LOG_LEVEL_DEBUG, CHILD_DEVICE_SCREEN, MSG_SUBTYPE_TEXT, "Full")
            return True


class meteoScreen(Screen):
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            touch.grab(self)
            return True

    def on_touch_up(self, touch):
        global minUITimer
        global lightOffTimer
        if touch.grab_current is self:
            touch.ungrab(self)
            with thermostatLock:
                Clock.unschedule(light_off)
                if minUITimer != None:
                    Clock.unschedule(show_minimal_ui)
                minUITimer = Clock.schedule_once(show_minimal_ui, minUITimeout)
                lightOffTimer = Clock.schedule_once(light_off, lightOff)
                GPIO.output(lightPin, GPIO.LOW)
                self.manager.current = "thermostatUI"
                log(LOG_LEVEL_DEBUG, CHILD_DEVICE_SCREEN, MSG_SUBTYPE_TEXT, "Full")
            return True


class coolScreen(Screen):
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            touch.grab(self)
            return True

    def on_touch_up(self, touch):
        global minUITimer
        global lightOffTimer
        if touch.grab_current is self:
            touch.ungrab(self)
            with thermostatLock:
                Clock.unschedule(light_off)
                if minUITimer != None:
                    Clock.unschedule(show_minimal_ui)
                minUITimer = Clock.schedule_once(show_minimal_ui, minUITimeout)
                lightOffTimer = Clock.schedule_once(light_off, lightOff)
                GPIO.output(lightPin, GPIO.LOW)
                self.manager.current = "thermostatUI"
                log(LOG_LEVEL_DEBUG, CHILD_DEVICE_SCREEN, MSG_SUBTYPE_TEXT, "Full")
            return True


class zoneScreen(Screen):
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            touch.grab(self)
            return True

    def on_touch_up(self, touch):
        global minUITimer
        global lightOffTimer
        if touch.grab_current is self:
            touch.ungrab(self)
            with thermostatLock:
                Clock.unschedule(light_off)
                if minUITimer != None:
                    Clock.unschedule(show_minimal_ui)
                minUITimer = Clock.schedule_once(show_minimal_ui, minUITimeout)
                lightOffTimer = Clock.schedule_once(light_off, lightOff)
                GPIO.output(lightPin, GPIO.LOW)
                self.manager.current = "thermostatUI"
                log(LOG_LEVEL_DEBUG, CHILD_DEVICE_SCREEN, MSG_SUBTYPE_TEXT, "Full")
            return True


class menuScreen(Screen):
    def on_touch_up(self, touch):
        global minUITimer
        global lightOffTimer
        x_pos = touch.pos[0]
        y_pos = touch.pos[1]
        # print x_pos,y_pos
        if x_pos <= 267 or x_pos >= 530:
            with thermostatLock:
                Clock.unschedule(light_off)
                if minUITimer != None:
                    Clock.unschedule(show_minimal_ui)
                minUITimer = Clock.schedule_once(show_minimal_ui, minUITimeout)
                lightOffTimer = Clock.schedule_once(light_off, lightOff)
                GPIO.output(lightPin, GPIO.LOW)
                self.manager.current = "thermostatUI"
                log(LOG_LEVEL_DEBUG, CHILD_DEVICE_SCREEN, MSG_SUBTYPE_TEXT, "Full")
        return True


##############################################################################
#                                                                            #
#       Kivy Thermostat App class                                            #
#                                                                            #
##############################################################################

class ThermostatApp(App):
    def build(self):
        global screenMgr

        # Set up the thermostat UI layout:
        thermostatUI = FloatLayout(size=(800, 480))

        # Make the background black:
        with thermostatUI.canvas.before:
            Color(0.0, 0.0, 0.0, 1)
            self.rect = Rectangle(size=(800, 480), pos=thermostatUI.pos)
            Color(1.0, 1.0, 1.0, 1)

        # Create the rest of the UI objects ( and bind them to callbacks, if necessary ):
        wimg = Image(source='web/images/sfondo.png')
        coolControl.bind(on_press=control_callback)
        heatControl.bind(on_press=control_callback)
        holdControl.bind(on_press=control_callback)
        plusControl.bind(on_press=update_set_temp)
        minusControl.bind(on_press=update_set_temp)

        # creo un bottone per il cambio dht/Inverno
        btndht = Button(text="", size_hint=(None, None), font_size='20sp')
        btndht.background_color = (0, 0, 0, 0)
        btndht.border = (0, 0, 0, 0)
        btndht.size = (85, 45)
        btndht.bind(on_press=dht_change)
        # creo un bottone per Visualizzare meteo
        btnmeteo = Button(text="", size_hint=(None, None), font_size='20sp')
        btnmeteo.background_color = (0, 0, 0, 0)
        btnmeteo.border = (0, 0, 0, 0)
        btnmeteo.size = (200, 100)
        btnmeteo.bind(on_press=select_meteo)
        # set sizing and position info

        wimg.size = (800, 480)
        wimg.size_hint = (None, None)
        wimg.pos = (0, 0)

        plusControl.size = (80, 80)
        plusControl.pos = (670, 170)

        minusControl.size = (80, 80)
        minusControl.pos = (670, 30)

        heatControl.size = (210, 80)
        heatControl.pos = (40, 160)

        coolControl.size = (210, 80)
        coolControl.pos = (40, 260)

        statusLabel.pos = (400, 215)

        holdControl.size = (210, 80)
        holdControl.pos = (40, 60)

        setLabel.pos = (680, 130)
        btndht.pos = (680, 130)
        umiditaLabel.pos = (350, 360)
        currentLabel.pos = (200, 405)

        dateLabel.pos = (530, 295)
        timeLabel.pos = (700, 305)

        weatherImg.pos = (440, 380)
        weatherSummaryLabel.pos = (640, 410)
        weatherDetailsLabel.pos = (690, 320)
        btnmeteo.pos = (440, 380)

        versionLabel.pos = (240, 0)
        d = 60
        for c in range(0, 3):
            forecastData[c].pos = (d + 85, 360)
            forecastImg[c].pos = (d - 20, 290)
            forecastSummaryLabel[c].pos = (d + 40, 220)
            forecastDetailsLabel[c].pos = (d + 70, 110)
            d += 260
        forecastSummary.pos = (360, 410)

        # Add the UI elements to the thermostat UI layout:
        thermostatUI.add_widget(wimg)
        thermostatUI.add_widget(plusControl)
        thermostatUI.add_widget(minusControl)
        thermostatUI.add_widget(heatControl)
        thermostatUI.add_widget(coolControl)
        thermostatUI.add_widget(holdControl)
        thermostatUI.add_widget(currentLabel)
        thermostatUI.add_widget(setLabel)
        thermostatUI.add_widget(statusLabel)
        thermostatUI.add_widget(dateLabel)
        thermostatUI.add_widget(timeLabel)
        thermostatUI.add_widget(weatherImg)
        thermostatUI.add_widget(weatherSummaryLabel)
        thermostatUI.add_widget(weatherDetailsLabel)
        thermostatUI.add_widget(versionLabel)
        thermostatUI.add_widget(btndht)
        thermostatUI.add_widget(btnmeteo)
        
        if dhtEnabled:
            thermostatUI.add_widget(umiditaLabel)
            
        menu_init = [" ", "Stato", "Reboot"]
        p = 325
        for index in range(3):
            if dhtIr_number == 0 and dhtZone_number == 0 and menu_init[index] == "Stato":
                btn = Button(text=" ", size_hint=(None, None), font_size='20sp')
                log(LOG_LEVEL_DEBUG, CHILD_DEVICE_SCREEN, MSG_SUBTYPE_TEXT, "No Stato")
            else:
                btn = Button(text=menu_init[index], size_hint=(None, None), font_size='20sp')
            btn.background_color = (0, 0, 0, 0)
            btn.border = (0, 0, 0, 0)
            btn.size = (85, 45)
            btn.pos = (p, 30)
            thermostatUI.add_widget(btn)
            p += 100
            btn.bind(on_press=select_menu)

        layout = thermostatUI

        # Minimap UI initialization

        uiScreen = Screen(name="thermostatUI")
        uiScreen.add_widget(thermostatUI)

        minScreen = MinimalScreen(name="minimalUI")
        minUI = FloatLayout(size=(800, 480))

        with minUI.canvas.before:
            Color(0.0, 0.0, 0.0, 1)
            self.rect = Rectangle(size=(800, 480), pos=minUI.pos)
            # altCurLabel.pos = ( 390, 290 )
            # altTimeLabel.pos = ( 335, 380 )
            altStatusLabel.pos = (400, 300)

        # minUI.add_widget( altCurLabel )
        # minUI.add_widget( altTimeLabel )
        minUI.add_widget(altStatusLabel)
        # se abilitato dhext scrivo i dati in minUI
        # if dhtEnabled:
        #	dht_label.pos = ( 400, 40)
        #	minUI.add_widget(dht_label)

        minScreen.add_widget(minUI)

        # creo la pagina per il meteo
        meteScreen = meteoScreen(name="meteoUI")
        meteoUI = FloatLayout(size=(800, 480))
        with meteoUI.canvas.before:
            Color(0.0, 0.0, 0.0, 1)
            self.rect = Rectangle(size=(800, 480), pos=meteoUI.pos)
        meteoUI.add_widget(forecastSummary)

        for c in range(0, 3):
            meteoUI.add_widget(forecastData[c])
            meteoUI.add_widget(forecastImg[c])
            meteoUI.add_widget(forecastSummaryLabel[c])
            meteoUI.add_widget(forecastDetailsLabel[c])

        meteScreen.add_widget(meteoUI)

        screenMgr = ScreenManager(
            transition=NoTransition())  # FadeTransition seems to have OpenGL bugs in Kivy Dev 1.9.1 and is unstable, so sticking with no transition for now

        # creo pagina dedicata ai moduli IR per i Condizionatori
        if dhtIr_number > 0:
            coolwScreen = coolScreen(name="coolUI")
            coolUI = FloatLayout(size=(800, 480))
            coolimage = Image(source='web/images/sfondo_cool.png')
            with coolUI.canvas.before:
                Color(0.0, 0.0, 0.0, 1)
                self.rect = Rectangle(size=(800, 480), pos=coolUI.pos)
            coolimage.size = (800, 480)
            coolimage.size_hint = (None, None)
            coolimage.pos = (0, 0)
            coolUI.add_widget(coolimage)
            d = 30
            p = 350
            s = 0
            for c in range(0, dhtIr_number):
                dhtIRLabel[c, 0].size = (300, 200)
                dhtIRLabel[c, 0].pos = (d, p)
                coolUI.add_widget(dhtIRLabel[c, 0])
                d += 260
                s += 1
                if s > 2:
                    p -= 145
                    s = 0
                    d = 30
            coolwScreen.add_widget(coolUI)
            screenMgr.add_widget(coolwScreen)
        # creo pagina dedicata ai moduli  per le zone
        if dhtZone_number > 0:
            zonewScreen = zoneScreen(name="zoneUI")
            zoneUI = FloatLayout(size=(800, 480))
            zoneimage = Image(source='web/images/sfondo_zone.png')
            with zoneUI.canvas.before:
                Color(0.0, 0.0, 0.0, 1)
                self.rect = Rectangle(size=(800, 480), pos=zoneUI.pos)
            zoneimage.size = (800, 480)
            zoneimage.size_hint = (None, None)
            zoneimage.pos = (0, 0)
            zoneUI.add_widget(zoneimage)
            d = 30
            p = 350
            s = 0
            for c in range(0, dhtZone_number):
                dhtZoneLabel[c, 0].size = (300, 200)
                dhtZoneLabel[c, 0].pos = (d, p)
                zoneUI.add_widget(dhtZoneLabel[c, 0])
                d += 260
                s += 1
                if s > 2:
                    p -= 145
                    s = 0
                    d = 30

            zonewScreen.add_widget(zoneUI)
            screenMgr.add_widget(zonewScreen)

        screenMgr.add_widget(uiScreen)
        screenMgr.add_widget(minScreen)
        screenMgr.add_widget(meteScreen)

        screenMgr.current = "thermostatUI"

        layout = screenMgr

        minUITimer = Clock.schedule_once(show_minimal_ui, minUITimeout)
        lighOffTimer = Clock.schedule_once(light_off, lightOff)
        csvSaver = Clock.schedule_once(save_graph, 30)
        # azzerro tutti i dht se ce ne sono
        Clock.schedule_once(clear_dht_init, 3)

        if pirEnabled:
            Clock.schedule_interval(check_pir, pirCheckInterval)

        if dhtEnabled == 1:
            Clock.schedule_once(dht_load, 4)
        # Show the current weather
        Clock.schedule_once(display_current_weather, 4)

        return layout


##############################################################################
#                                                                            #
#       Scheduler Implementation                                             #
#                                                                            #
##############################################################################



def startScheduler():
    log(LOG_LEVEL_INFO, CHILD_DEVICE_SCHEDULER, MSG_SUBTYPE_TEXT, "Started")
    while True:
        if holdControl.state == "normal":
            with scheduleLock:
                log(LOG_LEVEL_DEBUG, CHILD_DEVICE_SCHEDULER, MSG_SUBTYPE_TEXT, "Running pending")
                schedule.run_pending()

        time.sleep(10)


def setScheduledTemp(temp):
    with thermostatLock:
        global setTemp, dhtEnabled
        actual.put("state", setTemp=round(temp, 1), dhtEnabled=dhtEnabled, heatControl=heatControl.state,
                   coolControl=coolControl.state, holdControl=holdControl.state)
        if holdControl.state == "normal":
            setTemp = round(temp, 1)
            setLabel.text = "[b]" + str(round(setTemp, 1)) + "[/b]"
            if heatControl.state == "down":
                dhtZoneSend(0.5)
            if coolControl.state == "down":
                dhtIRSend(0.5)
            log(LOG_LEVEL_STATE, CHILD_DEVICE_SCHEDULER, MSG_SUBTYPE_TEMPERATURE, str(setTemp))


def getTestSchedule():
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    testSched = {}

    for i in range(len(days)):
        tempList = []
        for minute in range(60 * 24):
            hrs, mins = divmod(minute, 60)
            tempList.append([
                str(hrs).rjust(2, '0') + ":" + str(mins).rjust(2, '0'),
                float(i + 1) / 10.0 + ((19.0 if tempScale == "metric" else 68.0) if minute % 2 == 1 else (
                22.0 if tempScale == "metric" else 72.0))
            ])

        testSched[days[i]] = tempList

    return testSched


def reloadSchedule():
    with scheduleLock:
        schedule.clear()

        activeSched = None

        with thermostatLock:
            thermoSched = JsonStore("./setting/thermostat_schedule.json")
            if holdControl != "down":
                if coolControl.state == "down":
                    activeSched = thermoSched["cool"]
                    log(LOG_LEVEL_INFO, CHILD_DEVICE_SCHEDULER, MSG_SUBTYPE_CUSTOM + "/load", "cool")
                elif heatControl.state == "down":
                    if dhtSchedule == 0:
                        activeSched = thermoSched["heat"]
                        log(LOG_LEVEL_INFO, CHILD_DEVICE_SCHEDULER, MSG_SUBTYPE_CUSTOM + "/load", "heat")
                    else:
                        activeSched = thermoSched["dht"]
                        log(LOG_LEVEL_INFO, CHILD_DEVICE_SCHEDULER, MSG_SUBTYPE_CUSTOM + "/load", "dht")
            if useTestSchedule:
                activeSched = getTestSchedule()
                log(LOG_LEVEL_INFO, CHILD_DEVICE_SCHEDULER, MSG_SUBTYPE_CUSTOM + "/load", "test")
            # print "Using Test Schedule!!!"

        if activeSched != None:
            for day, entries in activeSched.iteritems():
                for i, entry in enumerate(entries):
                    getattr(schedule.every(), day).at(entry[0]).do(setScheduledTemp, entry[1])
                    log(LOG_LEVEL_DEBUG, CHILD_DEVICE_SCHEDULER, MSG_SUBTYPE_TEXT,
                        "Set " + day + ", at: " + entry[0] + " = " + str(entry[1]) + scaleUnits)


##############################################################################
#                                                                            #
#       Web Server Interface                                                 #
#                                                                            #
##############################################################################

##############################################################################
#      encoding: UTF-8                                                       #
# Form based authentication for CherryPy. Requires the                       #
# Session tool to be loaded.                                                 #
##############################################################################
cherrypy.server.socket_host = '0.0.0.0'

SESSION_KEY = '_cp_username'

def check_credentials(username, password):
    """Verifies credentials for username and password.
    Returns None on success or a string describing the error on failure"""
    # Adapt to your needs
    if username in (settings.get( "thermostat" )[ "user" ]) and password == settings.get( "thermostat" )[ "pass" ]:
        return None
    else:
        return u"Username o Password errato."
    
    # An example implementation which uses an ORM could be:
    # u = User.get(username)
    # if u is None:
    #     return u"Username %s is unknown to me." % username
    # if u.password != md5.new(password).hexdigest():
    #     return u"Incorrect password"

def check_auth(*args, **kwargs):
    """A tool that looks in config for 'auth.require'. If found and it
    is not None, a login is required and the entry is evaluated as a list of
    conditions that the user must fulfill"""
    if settings.get("web")["auth"] == 1:
        conditions = cherrypy.request.config.get('auth.require', None)
        if conditions is not None:
            username = cherrypy.session.get(SESSION_KEY)
            if username:
                cherrypy.request.login = username
                for condition in conditions:
                    # A condition is just a callable that returns true or false
                    if not condition():
                        raise cherrypy.HTTPRedirect("/auth/login")
            else:
                raise cherrypy.HTTPRedirect("/auth/login")
    else:
        return None
cherrypy.tools.auth = cherrypy.Tool('before_handler', check_auth)

def require(*conditions):
    """A decorator that appends conditions to the auth.require config
    variable."""
    def decorate(f):
        if not hasattr(f, '_cp_config'):
            f._cp_config = dict()
        if 'auth.require' not in f._cp_config:
            f._cp_config['auth.require'] = []
        f._cp_config['auth.require'].extend(conditions)
        return f
    return decorate


# Conditions are callables that return True
# if the user fulfills the conditions they define, False otherwise
#
# They can access the current username as cherrypy.request.login
#
# Define those at will however suits the application.

def member_of(groupname):
    def check():
        # replace with actual check if <username> is in <groupname>
        return cherrypy.request.login == 'termo' and groupname == 'admin'
    return check

def name_is(reqd_username):
    return lambda: reqd_username == cherrypy.request.login

# These might be handy

def any_of(*conditions):
    """Returns True if any of the conditions match"""
    def check():
        for c in conditions:
            if c():
                return True
        return False
    return check

# By default all conditions are required, but this might still be
# needed if you want to use it inside of an any_of(...) condition
def all_of(*conditions):
    """Returns True if all of the conditions match"""
    def check():
        for c in conditions:
            if not c():
                return False
        return True
    return check


# Controller to provide login and logout actions

class AuthController(object):
    
    def on_login(self, username):
        """Called on successful login"""
    
    def on_logout(self, username):
        """Called on logout"""
    
    def get_loginform(self, username, msg="Login ", from_page="/"):
        
	
        file = open( "web/html/thermostat_login.html", "r" )

        html = file.read()

        file.close()
		
        return html %locals()

    @cherrypy.expose
    def login(self, username=None, password=None, from_page="/"):
        if username is None or password is None:
            return self.get_loginform("", from_page=from_page)
        
        error_msg = check_credentials(username, password)
        if error_msg:
            return self.get_loginform(username, error_msg, from_page)
        else:
            cherrypy.session[SESSION_KEY] = cherrypy.request.login = username
            self.on_login(username)
            raise cherrypy.HTTPRedirect(from_page or "/")
    
    @cherrypy.expose
    def logout(self, from_page="/"):
        sess = cherrypy.session
        username = sess.get(SESSION_KEY, None)
        sess[SESSION_KEY] = None
        if username:
            cherrypy.request.login = None
            self.on_logout(username)
        raise cherrypy.HTTPRedirect(from_page or "/")


class WebInterface(object):
        
    _cp_config = {
        'tools.sessions.on': True,
        'tools.auth.on': True
        }
    
    auth = AuthController()
    
    @cherrypy.expose
    @require()
        
    
    def index(self):
        log(LOG_LEVEL_INFO, CHILD_DEVICE_WEBSERVER, MSG_SUBTYPE_TEXT,"Served thermostat.html to: " + cherrypy.request.remote.ip)

        file = open("web/html/thermostat.html", "r")

        html = file.read()

        file.close()

        with thermostatLock:

            html = html.replace("@@version@@", str(THERMOSTAT_VERSION))
            html = html.replace("@@temp@@", str(setTemp))
            html = html.replace("@@current@@", str(currentTemp))
            html = html.replace("@@minTemp@@", str(minTemp))
            html = html.replace("@@maxTemp@@", str(maxTemp))
            html = html.replace("@@tempStep@@", str(tempStep))
            html = html.replace("@@temp_extern@@", str(temp_vis))

            status = statusLabel.text.replace("[b]", "<b>").replace("[/b]", "</b>").replace("[/color]",
                                                                                            "</font>").replace(
                "[color=ff3333]", "<font color=\"#ff3333\">").replace("[i]", "<i>").replace("[/i]", "</i>").replace(
                "\n", "<br>").replace("[color=#5F81F1]", "<font color=\"#5F81F1\">")
            status = status.replace("[color=00ff00]", '<font color="red">').replace("[/color]", '</font>')

            html = html.replace("@@status@@", status)
            html = html.replace("@@dt@@", dateLabel.text.replace("[b]", "<b>").replace("[/b]",
                                                                                       "</b>") + " - " + timeLabel.text.replace(
                "[b]", "<b>").replace("[/b]", "</b>"))
            html = html.replace("@@heatChecked@@", "checked" if heatControl.state == "down" else "no")
            html = html.replace("@@coolChecked@@", "checked" if coolControl.state == "down" else "no")
            html = html.replace("@@holdChecked@@", "checked" if holdControl.state == "down" else "no")
            html = html.replace("@@dhtIrsubmit@@", "style='display:none'" if dhtIr_number == 0 else "")
            html = html.replace("@@dhtZonesubmit@@", "style='display:none'" if dhtZone_number == 0 else "")
            html = html.replace("@@dhtsubmit@@", "style='display:none'" if dhtEnabled == 0 else "")
            if dhtZone_number == 0:
                html = html.replace("@@displayzone@@", "display:none")
            if dhtIr_number == 0:
                html = html.replace("@@displayir@@", "display:none")
            if dhtEnabled == 0:
                html = html.replace("@@displaydht@@", "display:none")

        return html
    
    @cherrypy.expose
    @require()
    def mobile(self):
        log(LOG_LEVEL_INFO, CHILD_DEVICE_WEBSERVER, MSG_SUBTYPE_TEXT,"Served thermostat.html to: " + cherrypy.request.remote.ip)

        file = open("web/html/thermostat_mobile.html", "r")

        html = file.read()

        file.close()

        with thermostatLock:

            html = html.replace("@@version@@", str(THERMOSTAT_VERSION))
            html = html.replace("@@temp@@", str(setTemp))
            html = html.replace("@@current@@", str(currentTemp))
            html = html.replace("@@minTemp@@", str(minTemp))
            html = html.replace("@@maxTemp@@", str(maxTemp))
            html = html.replace("@@tempStep@@", str(tempStep))
            html = html.replace("@@temp_extern@@", str(temp_vis))

            status = statusLabel.text.replace("[b]", "<b>").replace("[/b]", "</b>").replace("[/color]",
                                                                                            "</font>").replace(
                "[color=ff3333]", "<font color=\"#ff3333\">").replace("[i]", "<i>").replace("[/i]", "</i>").replace(
                "\n", "<br>").replace("[color=#5F81F1]", "<font color=\"#5F81F1\">")
            status = status.replace("[color=00ff00]", '<font color="red">').replace("[/color]", '</font>')

            html = html.replace("@@status@@", status)
            html = html.replace("@@dt@@", dateLabel.text.replace("[b]", "<b>").replace("[/b]",
                                                                                       "</b>") + " - " + timeLabel.text.replace(
                "[b]", "<b>").replace("[/b]", "</b>"))
            html = html.replace("@@heatChecked@@", "checked" if heatControl.state == "down" else "no")
            html = html.replace("@@coolChecked@@", "checked" if coolControl.state == "down" else "no")
            html = html.replace("@@holdChecked@@", "checked" if holdControl.state == "down" else "no")
            html = html.replace("@@dhtIrsubmit@@", "style='display:none'" if dhtIr_number == 0 else "")
            html = html.replace("@@dhtZonesubmit@@", "style='display:none'" if dhtZone_number == 0 else "")
            html = html.replace("@@dhtsubmit@@", "style='display:none'" if dhtEnabled == 0 else "")
            if dhtZone_number == 0:
                html = html.replace("@@displayzone@@", "display:none")
            if dhtIr_number == 0:
                html = html.replace("@@displayir@@", "display:none")
            if dhtEnabled == 0:
                html = html.replace("@@displaydht@@", "display:none")

        return html

    @cherrypy.expose
    @require()
    def set(self, temp, heat="off", hold="off", cool="off"):
        global setTemp, setLabel, coolControl, heatControl, holdControl

        log(LOG_LEVEL_INFO, CHILD_DEVICE_WEBSERVER, MSG_SUBTYPE_TEXT,
            "Set thermostat received from: " + cherrypy.request.remote.ip)

        tempChanged = setTemp != float(temp)

        with thermostatLock:
            setTemp = float(temp)
            setLabel.text = "[b]" + str(round(setTemp, 1)) + "[/b]"

            if tempChanged:
                log(LOG_LEVEL_STATE, CHILD_DEVICE_WEBSERVER, MSG_SUBTYPE_TEMPERATURE, str(setTemp))

            if heat == "on":
                setControlState(heatControl, "down")
            else:
                setControlState(heatControl, "normal")

            if cool == "on":
                setControlState(coolControl, "down")
            else:
                setControlState(coolControl, "normal")

            if hold == "on":
                setControlState(holdControl, "down")
            else:
                setControlState(holdControl, "normal")

            dhtSend("clear")
            reloadSchedule()

        file = open("web/html/thermostat_set.html", "r")

        html = file.read()

        file.close()

        with thermostatLock:
            html = html.replace("@@version@@", str(THERMOSTAT_VERSION))
            html = html.replace("@@dt@@", dateLabel.text.replace("[b]", "<b>").replace("[/b]",
                                                                                       "</b>") + ", " + timeLabel.text.replace(
                "[b]", "<b>").replace("[/b]", "</b>"))
            html = html.replace("@@temp@@", ('<font color="red"><b>' if tempChanged else "") + str(setTemp) + (
            '</b></font>' if tempChanged else ""))
            html = html.replace("@@heat@@", ('<font color="red"><b>' if heat == "on" else "") + heat + (
            '</b></font>' if heat == "on" else ""))
            html = html.replace("@@cool@@", ('<font color="red"><b>' if cool == "on" else "") + cool + (
            '</b></font>' if heat == "on" else ""))
            html = html.replace("@@hold@@", ('<font color="red"><b>' if hold == "on" else "") + hold + (
            '</b></font>' if hold == "on" else ""))

        return html

    @cherrypy.expose
    @require()
    def schedule(self):
        log(LOG_LEVEL_INFO, CHILD_DEVICE_WEBSERVER, MSG_SUBTYPE_TEXT,
            "Served thermostat_schedule.html to: " + cherrypy.request.remote.ip)
        file = open("web/html/thermostat_schedule.html", "r")

        html = file.read()

        file.close()

        with thermostatLock:
            html = html.replace("@@version@@", str(THERMOSTAT_VERSION))
            html = html.replace("@@minTemp@@", str(minTemp))
            html = html.replace("@@maxTemp@@", str(maxTemp))
            html = html.replace("@@tempStep@@", str(tempStep))

            html = html.replace("@@dt@@", dateLabel.text.replace("[b]", "<b>").replace("[/b]",
                                                                                       "</b>") + ", " + timeLabel.text.replace(
                "[b]", "<b>").replace("[/b]", "</b>"))

        return html

    @cherrypy.expose
    @require()
    @cherrypy.tools.json_in()
    def save(self):
        log(LOG_LEVEL_STATE, CHILD_DEVICE_WEBSERVER, MSG_SUBTYPE_TEXT,
            "Set schedule received from: " + cherrypy.request.remote.ip)
        schedule = cherrypy.request.json

        with scheduleLock:
            file = open("./setting/thermostat_schedule.json", "w")

            file.write(json.dumps(schedule, indent=4))

            file.close()

        reloadSchedule()

        file = open("web/html/thermostat_saved.html", "r")

        html = file.read()

        file.close()

        with thermostatLock:
            html = html.replace("@@version@@", str(THERMOSTAT_VERSION))
            html = html.replace("@@dt@@", dateLabel.text.replace("[b]", "<b>").replace("[/b]",
                                                                                       "</b>") + ", " + timeLabel.text.replace(
                "[b]", "<b>").replace("[/b]", "</b>"))

        return html

    @cherrypy.expose
    @require()
    def graph(self):
        log(LOG_LEVEL_INFO, CHILD_DEVICE_WEBSERVER, MSG_SUBTYPE_TEXT, "graph.html to: " + cherrypy.request.remote.ip)
        file = open("web/html/graph.html", "r")

        html = file.read()

        file.close()

        return html

    @cherrypy.expose
    @require()
    def zonedht(self, ipdht=""):
        log(LOG_LEVEL_INFO, CHILD_DEVICE_WEBSERVER, MSG_SUBTYPE_TEXT, "zone.html to: " + cherrypy.request.remote.ip)
        #print "ip DHT: ", ipdht
        file = open("web/html/zone.html", "r")

        html = file.read()

        file.close()
        with thermostatLock:

            html = html.replace("@@version@@", str(THERMOSTAT_VERSION))
            html = html.replace("@@dt@@", dateLabel.text.replace("[b]", "<b>").replace("[/b]",
                                                                                       "</b>") + ", " + timeLabel.text.replace(
                "[b]", "<b>").replace("[/b]", "</b>"))
            status = statusLabel.text.replace("[b]", "<b>").replace("[/b]", "</b>").replace("[/color]",
                                                                                            "</font>").replace(
                "[color=ff3333]", "<font color=\"#ff3333\">").replace("[i]", "<i>").replace("[/i]", "</i>").replace(
                "\n", "<br>").replace("[color=#5F81F1]", "<font color=\"#5F81F1\">")
            status = status.replace("[color=00ff00]", '<font color="red">').replace("[/color]", '</font>')

            html = html.replace("@@status@@", status)
            for c in range(0, 9):
                if (c < dhtZone_number):
                    zone = dhtZoneLabel[c, 0].text.replace("[b]", "<b>").replace("[/b]", "</b>").replace("[/color]",
                                                                                                         "</font>").replace(
                        "[color=ff3333]", "<font color=\"red\">").replace("[i]", "<i>").replace("[/i]", "</i>").replace(
                        "\n", "<br>")
                    zone = zone.replace("[color=00ff00]", '<font color="red">').replace("[/color]", '</font>')
                    zone_name = "@@zone" + str(c) + "@@"
                    html = html.replace(zone_name, zone)
                else:
                    zone_name = "@@zone_name" + str(c) + "@@"
                    zone = "@@zone" + str(c) + "@@"
                    html = html.replace(zone_name, "style=\"display:none\"")
                    html = html.replace(zone, "")

        return html

    @cherrypy.expose
    @require()
    def irdht(self, ipdht=""):
        log(LOG_LEVEL_INFO, CHILD_DEVICE_WEBSERVER, MSG_SUBTYPE_TEXT, "ir.html to: " + cherrypy.request.remote.ip)
        file = open("web/html/ir.html", "r")

        html = file.read()

        file.close()
        with thermostatLock:

            html = html.replace("@@version@@", str(THERMOSTAT_VERSION))
            html = html.replace("@@dt@@", dateLabel.text.replace("[b]", "<b>").replace("[/b]",
                                                                                       "</b>") + ", " + timeLabel.text.replace(
                "[b]", "<b>").replace("[/b]", "</b>"))
            status = statusLabel.text.replace("[b]", "<b>").replace("[/b]", "</b>").replace("[/color]",
                                                                                            "</font>").replace(
                "[color=ff3333]", "<font color=\"#ff3333\">").replace("[i]", "<i>").replace("[/i]", "</i>").replace(
                "\n", "<br>").replace("[color=#5F81F1]", "<font color=\"#5F81F1\">")
            status = status.replace("[color=00ff00]", '<font color="red">').replace("[/color]", '</font>')

            html = html.replace("@@status@@", status)
            for c in range(0, 9):
                if (c < dhtIr_number):
                    zone = dhtIRLabel[c, 0].text.replace("[b]", "<b>").replace("[/b]", "</b>").replace("[/color]",
                                                                                                       "</font>").replace(
                        "[color=ff3333]", "<font color=\"red\">").replace("[i]", "<i>").replace("[/i]", "</i>").replace(
                        "\n", "<br>")
                    zone = zone.replace("[color=00ff00]", '<font color="red">').replace("[/color]", '</font>')
                    zone_name = "@@zone_name" + str(c) + "@@"
                    zone_name1 = "@@zone" + str(c) + "@@"
                    html = html.replace(zone_name, "")
                    html = html.replace(zone_name1, zone)

                else:
                    zone_name = "@@zone_name" + str(c) + "@@"
                    zone = "@@zone" + str(c) + "@@"
                    html = html.replace(zone_name, "style=\"display:none\"")
                    html = html.replace(zone, "")

        return html

    @cherrypy.expose
    def redirect(self, ipdht=""):
        global dhtweb
        global send_ip
        if (int(ipdht) == 99):
            send_ip = dhtweb
        else:
            if (int(ipdht) >= 10):
                send_ip = dhtIR[int(ipdht) - 10, 1]
            else:
                send_ip = dhtZone[int(ipdht), 1]

        f = urllib2.urlopen(send_ip + "/", None, 5)

        return f

    @cherrypy.expose
    def grafico(self):
        f = urllib2.urlopen(send_ip + "/grafico", None, 5)

        return f

    @cherrypy.expose
    def tabella(self):
        f = urllib2.urlopen(send_ip + "/tabella", None, 5)

        return f

    @cherrypy.expose
    def irDecoder(self):
        f = urllib2.urlopen(send_ip + "/irDecoder", None, 5)

        return f

    @cherrypy.expose
    def irSender(self):
        f = urllib2.urlopen(send_ip + "/irSender", None, 5)

        return f

    @cherrypy.expose
    def zone(self):
        f = urllib2.urlopen(send_ip + "/zone", None, 5)

        return f


def startWebServer():
    host = "discover" if not (settings.exists("web")) else settings.get("web")["host"]
    # cherrypy.server.socket_host = host if host != "discover" else get_ip_address()	# use machine IP address if host = "discover"
    cherrypy.server.socket_port = 80 if not (settings.exists("web")) else settings.get("web")["port"]
    if cherrypy.server.socket_port == 443:
        cherrypy.server.ssl_module = "pyopenssl"
        cherrypy.server.ssl_certificate = settings.get("web")["cert"]
        cherrypy.server.ssl_private_key = settings.get("web")["key"]

    log(LOG_LEVEL_STATE, CHILD_DEVICE_WEBSERVER, MSG_SUBTYPE_TEXT,
        "Starting on " + cherrypy.server.socket_host + ":" + str(cherrypy.server.socket_port))

    conf = {
        '/': {
            'tools.staticdir.root': os.path.abspath(os.getcwd()),
            'tools.staticfile.root': os.path.abspath(os.getcwd())
        },
        '/css': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': './web/css'
        },
        '/javascript': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': './web/javascript'
        },
        '/images': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': './web/images'
        },
        '/schedule.json': {
            'tools.staticfile.on': True,
            'tools.staticfile.filename': './setting/thermostat_schedule.json'
        },
        '/favicon.ico': {
            'tools.staticfile.on': True,
            'tools.staticfile.filename': './web/images/favicon.ico'
        },
        '/graph': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': './web/graph'
        }

    }

    cherrypy.config.update(
        {'log.screen': debug,
         'log.access_file': "",
         'log.error_file': "",
         'server.thread_pool': 10
         }
    )

    cherrypy.quickstart(WebInterface(), '/', conf)


##############################################################################
#                                                                            #
#       Main                                                                 #
#                                                                            #
##############################################################################

def main():
    # Start Web Server
    webThread = threading.Thread(target=startWebServer)
    webThread.daemon = True
    webThread.start()

    # Start Scheduler
    reloadSchedule()
    schedThread = threading.Thread(target=startScheduler)
    schedThread.daemon = True
    schedThread.start()

    # setControlState
    # webThread = threading.Thread( target=setControlState( control, state ) )
    # webThread.daemon = True
    # webThread.start()
    ####Start thread Telegram
    if telegramSend == 1: 
        try:
            MessageLoop(bot, handle).run_as_thread()
        except telepot.exception.TelegramError:
            logTermostat("Telegram error on start.....")
    # Start Thermostat UI/App
    ThermostatApp().run()


if __name__ == '__main__':
    try:
        main()
    finally:
        log(LOG_LEVEL_STATE, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/shutdown", "Thermostat Shutting Down...")
        GPIO.cleanup()
        dhtSend("clear")
        if logFile is not None:
            logFile.flush()
            os.fsync(logFile.fileno())
            logFile.close()
