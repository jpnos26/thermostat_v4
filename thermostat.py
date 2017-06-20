# coding: latin-1 
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
import math
import os, os.path, sys
import time
import datetime
import urllib2
import json
#import random
import socket
import re
import locale
locale.setlocale(locale.LC_ALL, '')

##############################################################################
#                                                                            #
#       Kivy UI Imports                                                      #
#                                                                            #
##############################################################################

import kivy
kivy.require( '1.9.0' ) # replace with your current kivy version !

from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.label import Label
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.storage.jsonstore import JsonStore
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition
from kivy.uix.dropdown import DropDown

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
        elif self.value in args: # changed for v1.5, see below
            self.fall = True
            return True
        else:
            return False


##############################################################################
#                                                                            #
#       MySensor.org Controller compatible translated constants              #
#                                                                            #
##############################################################################

MSG_TYPE_SET 					= "set"
MSG_TYPE_PRESENTATION 				= "presentation"

CHILD_DEVICE_NODE				= "node"
CHILD_DEVICE_UICONTROL_HEAT			= "heatControl"
CHILD_DEVICE_UICONTROL_COOL			= "coolControl"
CHILD_DEVICE_UICONTROL_HOLD			= "holdControl"
CHILD_DEVICE_WEATHER_FCAST_TODAY		= "weatherForecastToday"
CHILD_DEVICE_WEATHER_FCAST_TOMO			= "weatherForecastTomorrow"
CHILD_DEVICE_WEATHER_CURR			= "weatherCurrent"
CHILD_DEVICE_HEAT				= "heat"
CHILD_DEVICE_COOL				= "cool"
CHILD_DEVICE_PIR				= "motionSensor"
CHILD_DEVICE_TEMP				= "temperatureSensor"
CHILD_DEVICE_SCREEN				= "screen"
CHILD_DEVICE_SCHEDULER				= "scheduler"
CHILD_DEVICE_WEBSERVER				= "webserver"
CHILD_DEVICE_DHTIN				= "DhtIn"
CHILD_DEVICE_DHTOUT				= "DhtOut"
CHILD_DEVICE_DHTIR				= "DhtIr"
CHILD_DEVICE_DHTZONE				= "DhtZone"
CHILD_DEVICE_DHTRELE				= "DhtRele"

CHILD_DEVICES						= [
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
	CHILD_DEVICE_DHTRELE
]

CHILD_DEVICE_SUFFIX_UICONTROL		= "Control"

MSG_SUBTYPE_NAME			= "sketchName"
MSG_SUBTYPE_VERSION			= "sketchVersion"
MSG_SUBTYPE_BINARY_STATUS		= "binaryStatus"
MSG_SUBTYPE_TRIPPED			= "armed"
MSG_SUBTYPE_ARMED			= "tripped"
MSG_SUBTYPE_TEMPERATURE			= "temperature"
MSG_SUBTYPE_FORECAST			= "forecast"
MSG_SUBTYPE_CUSTOM			= "custom"
MSG_SUBTYPE_TEXT			= "text"
MSG_SUBTYPE_DHT				= "DhtWifi"


##############################################################################
#                                                                            #
#       Settings                                                             #
#                                                                            #
##############################################################################

THERMOSTAT_VERSION = "4.0.1"

# Debug settings

debug = False
useTestSchedule = False


# Threading Locks

thermostatLock = threading.RLock()
weatherLock    = threading.Lock()
scheduleLock   = threading.RLock()


# Thermostat persistent settings

settings	= JsonStore( "./setting/thermostat_settings.json" )
state		= JsonStore( "./setting/thermostat_state.json" )
actual		= JsonStore( "./setting/thermostat_actual.json")


#graphics


# Logging settings/setup

LOG_FILE_NAME = "./log/thermostat.log"

LOG_ALWAYS_TIMESTAMP = True

LOG_LEVEL_DEBUG = 1
LOG_LEVEL_INFO	= 2
LOG_LEVEL_ERROR = 3
LOG_LEVEL_STATE = 4
LOG_LEVEL_NONE  = 5

LOG_LEVELS = {
	"debug": LOG_LEVEL_DEBUG,
	"info":  LOG_LEVEL_INFO,
	"state": LOG_LEVEL_STATE,
	"error": LOG_LEVEL_ERROR
}

LOG_LEVELS_STR = { v: k for k, v in LOG_LEVELS.items() }

logFile = None


def log_dummy( level, child_device, msg_subtype, msg, msg_type=MSG_TYPE_SET, timestamp=True, single=False ):
	pass


def log_file( level, child_device, msg_subtype, msg, msg_type=MSG_TYPE_SET, timestamp=True, single=False ):
	if level >= logLevel:
		ts = datetime.datetime.now().strftime( "%Y-%m-%dT%H:%M:%S%z " ) 
		logFile.write( ts + LOG_LEVELS_STR[ level ] + "/" + child_device + "/" + msg_type + "/" + msg_subtype + ": " + msg + "\n" )


def log_print( level, child_device, msg_subtype, msg, msg_type=MSG_TYPE_SET, timestamp=True, single=False ):
	if level >= logLevel:
		ts = datetime.datetime.now().strftime( "%Y-%m-%dT%H:%M:%S%z " ) if LOG_ALWAYS_TIMESTAMP or timestamp else ""
		print( ts + LOG_LEVELS_STR[ level ] + "/" + child_device + "/" + msg_type + "/" + msg_subtype + ": " + msg )


loggingChannel = "none" if not( settings.exists( "logging" ) ) else settings.get( "logging" )[ "channel" ]
loggingLevel   = "state" if not( settings.exists( "logging" ) ) else settings.get( "logging" )[ "level" ]

for case in switch( loggingChannel ):
	if case( 'none' ):
		log = log_dummy
		break
	if case( 'file' ):
		log = log_file
		logFile = open( LOG_FILE_NAME, "a", 0 )
		break
	if case( 'print' ):
		log = log_print
		break
	if case():		# default
		log = log_dummy	

logLevel = LOG_LEVELS.get( loggingLevel, LOG_LEVEL_NONE )

# Send presentations for Node

log( LOG_LEVEL_STATE, CHILD_DEVICE_NODE, MSG_SUBTYPE_NAME, "Thermostat Starting Up...", msg_type=MSG_TYPE_PRESENTATION )
log( LOG_LEVEL_STATE, CHILD_DEVICE_NODE, MSG_SUBTYPE_VERSION, THERMOSTAT_VERSION, msg_type=MSG_TYPE_PRESENTATION )

#send presentations for all other child "sensors"

for i in range( len( CHILD_DEVICES ) ):
	child = CHILD_DEVICES[ i ]
	if child != CHILD_DEVICE_NODE:
		log( LOG_LEVEL_STATE, child, child, "", msg_type=MSG_TYPE_PRESENTATION )

# Various temperature settings:

tempScale		= settings.get( "scale" )[ "tempScale" ]
scaleUnits 	  	= u"\xb0" if tempScale == "metric" else u"f"
precipUnits		= " mm" if tempScale == "metric" else '"'
precipFactor		= 1.0 if tempScale == "metric" else 0.0393701
precipRound		= 0 if tempScale == "metric" else 1
sensorUnits		= W1ThermSensor.DEGREES_C if tempScale == "metric" else W1ThermSensor.DEGREES_F
windFactor		= 3.6 if tempScale == "metric" else 1.0
windUnits		= " km/h" if tempScale == "metric" else " mph"

TEMP_TOLERANCE	= 0.1 if tempScale == "metric" else 0.18
currentTemp	= 20.0 if tempScale == "metric" else 72.0
priorCorrected	= -100.0
# openDoor e openDoorcheck for stop sistem for a time set in thermostat_setting and temperature change quickly of 1 C degrees
openDoor	= 21 if not( state.exists( "thermostat" ) ) else int((state.get( "thermostat" )[ "openDoor" ]/state.get( "thermostat" )[ "tempCheckInterval" ])+1)
openDoorCheck	= 20 if not( state.exists( "thermostat" ) ) else int(state.get( "thermostat" )[ "openDoor" ]/state.get( "thermostat" )[ "tempCheckInterval" ])

setTemp			= 22.0 if not( state.exists( "state" ) ) else state.get( "state" )[ "setTemp" ]
setice			= 15.0 if not(settings.exists ( "thermostat")) else settings.get("thermostat")["tempice"]
tempHysteresis		= 0.5  if not( settings.exists( "thermostat" ) ) else settings.get( "thermostat" )[ "tempHysteresis" ]
tempCheckInterval	= 3    if not( settings.exists( "thermostat" ) ) else settings.get( "thermostat" )[ "tempCheckInterval" ]
out_temp		= 0.0
temp_vis 		= 0 

minUIEnabled		= 0    if not( settings.exists( "thermostat" ) ) else settings.get( "thermostat" )[ "minUIEnabled" ]
minUITimeout		= 3    if not( settings.exists( "thermostat" ) ) else settings.get( "thermostat" )[ "minUITimeout" ]
lightOff		= 10   if not( settings.exists( "thermostat" ) ) else settings.get( "thermostat" )[ "lightOff" ]

minUITimer		= None
csvSaver		= None
dhtIrTimer		= None
dhtZoneTimer		= None
dhtReleTimer		= None



csvTimeout		= 300 if not( settings.exists( "thermostat" ) ) else settings.get( "thermostat" )[ "saveCsv" ] 

log( LOG_LEVEL_INFO, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/settings/temperature/tempScale", str( tempScale ), timestamp=False )
log( LOG_LEVEL_INFO, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/settings/temperature/scaleUnits", scaleUnits , timestamp=False )
log( LOG_LEVEL_INFO, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/settings/temperature/precipUnits", str( precipUnits ), timestamp=False )
log( LOG_LEVEL_INFO, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/settings/temperature/precipFactor", str( precipFactor ), timestamp=False )
log( LOG_LEVEL_INFO, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/settings/temperature/sensorUnits", str( sensorUnits ), timestamp=False )
log( LOG_LEVEL_INFO, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/settings/temperature/windFactor", str( windFactor ), timestamp=False )
log( LOG_LEVEL_INFO, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/settings/temperature/windUnits", str( windUnits ), timestamp=False )
log( LOG_LEVEL_INFO, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/settings/temperature/currentTemp", str( currentTemp ), timestamp=False )
log( LOG_LEVEL_INFO, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/settings/temperature/setTemp", str( setTemp ), timestamp=False )
log( LOG_LEVEL_INFO, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/settings/temperature/tempHysteresis", str( tempHysteresis ), timestamp=False )
log( LOG_LEVEL_INFO, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/settings/temperature/tempCheckInterval", str( tempCheckInterval ), timestamp=False )
log( LOG_LEVEL_INFO, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/settings/temperature/minUIEnabled", str( minUIEnabled ), timestamp=False )
log( LOG_LEVEL_INFO, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/settings/temperature/minUITimeout", str( minUITimeout ), timestamp=False )
log( LOG_LEVEL_INFO, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/settings/temperature/lightOff", str( lightOff ), timestamp=False )

# Temperature calibration settings:

elevation	  = 0 if not( settings.exists( "thermostat" ) ) else settings.get( "calibration" )[ "elevation" ]
boilingPoint	  = ( 100.0 - 0.003353 * elevation ) if tempScale == "metric" else ( 212.0 - 0.00184 * elevation )
freezingPoint	  = 0.01 if tempScale == "metric" else 32.018
referenceRange	  = boilingPoint - freezingPoint
correctSensor	  = 0 if not( settings.exists( "thermostat" ) ) else settings.get( "calibration" )[ "correctSensor" ]

boilingMeasured   = settings.get( "calibration" )[ "boilingMeasured" ]
freezingMeasured  = settings.get( "calibration" )[ "freezingMeasured" ]
measuredRange	  = boilingMeasured - freezingMeasured

log( LOG_LEVEL_INFO, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/settings/calibration/elevation", str( elevation ), timestamp=False )
log( LOG_LEVEL_INFO, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/settings/calibration/boilingPoint", str( boilingPoint ), timestamp=False )
log( LOG_LEVEL_INFO, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/settings/calibration/freezingPoint", str( freezingPoint ), timestamp=False )
log( LOG_LEVEL_DEBUG, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/settings/calibration/referenceRange", str( referenceRange ), timestamp=False )
log( LOG_LEVEL_INFO, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/settings/calibration/boilingMeasured", str( boilingMeasured ), timestamp=False )
log( LOG_LEVEL_INFO, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/settings/calibration/freezingMeasured", str( freezingMeasured ), timestamp=False )
log( LOG_LEVEL_DEBUG, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/settings/calibration/measuredRange", str( measuredRange ), timestamp=False )


# DHT and Temp setting:

minTemp			  = 15.0 if not( settings.exists( "thermostat" ) ) else settings.get( "thermostat" )[ "minTemp" ]
maxTemp			  = 30.0 if not( settings.exists( "thermostat" ) ) else settings.get( "thermostat" )[ "maxTemp" ]
tempStep		  = 0.5  if not( settings.exists( "thermostat" ) ) else settings.get( "thermostat" )[ "tempStep" ]
dhtRele			  = 0 if not( settings.exists( "thermostat" ) ) else settings.get( "dht_rele" )[ "rele_enabled" ]
dhtReleIP		  = "" if not( settings.exists( "thermostat" ) ) else settings.get( "dht_rele" )[ "rele_ip" ]
dhtIr_number		  = 0 if not( settings.exists( "thermostat" ) ) else settings.get( "dht_ir" )[ "number" ]
dhtZone_number		  = 0 if not( settings.exists( "thermostat" ) ) else settings.get( "dht_zone" )[ "number" ]
dhtCheck		  = 0

if dhtIr_number > 0:
	dhtIRLabel = {}
	dhtIR = {}
	for c in range(0, dhtIr_number):
		dhtIRLabel[c,0] = Label( text= " ",size_hint = (None,None), font_size = '15sp', markup=True, text_size= (300,300),color=( 1,1,1,1 ))
		
		dhtIR[c,0] = settings.get( "dht_ir" )[ "zoneir_interval" ]
		dhtIR[c,1] = "http://"+settings.get("dht_ir" )["zoneir_ip_"+str(c+1)]
		dhtIR[c,2] = settings.get("dht_ir")["zoneir_name_"+str(c+1)]
		dhtIR[c,3] = 0 	# temperatura
		dhtIR[c,4] = 0	# Umidita
		dhtIR[c,5] = 0	# stato comando Inviato
		dhtIR[c,6] = 0 # temperatura impostata
	
if dhtZone_number >0:
	dhtZoneLabel = {}
	dhtZone = {}
	for c in range(0, dhtZone_number):
		dhtZoneLabel[c,0] = Label( text= " ",size_hint = (None,None), font_size = '15sp', markup=True, text_size= (300,300),color=( 1,1,1,1 ))
		dhtZone[c,0] = settings.get( "dht_zone" )[ "zone_interval" ]
		dhtZone[c,1] = "http://"+settings.get("dht_zone" )["zone_ip_"+str(c+1)]
		dhtZone[c,2] = settings.get("dht_zone")["zone_name_"+str(c+1)]
		dhtZone[c,3] = 0	# temperatura
		dhtZone[c,4] = 0	# Umidita
		dhtZone[c,5] = 0	# stato comando Inviato
		dhtZone[c,6] = 0 	# temperatura impostata
		
log( LOG_LEVEL_INFO, CHILD_DEVICE_DHTRELE, MSG_SUBTYPE_CUSTOM + "/Dht Rele: ", str( dhtRele), timestamp=False )
log( LOG_LEVEL_INFO, CHILD_DEVICE_DHTZONE, MSG_SUBTYPE_CUSTOM + "//Dht Zone : ", str( dhtZone_number), timestamp=False )
log( LOG_LEVEL_INFO, CHILD_DEVICE_DHTIR, MSG_SUBTYPE_CUSTOM + "/Dht IR", str( dhtIr_number), timestamp=False )	
log( LOG_LEVEL_INFO, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/settings/UISlider/minTemp", str( minTemp ), timestamp=False )
log( LOG_LEVEL_INFO, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/settings/UISlider/maxTemp", str( maxTemp ), timestamp=False )
log( LOG_LEVEL_INFO, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/settings/UISlider/tempStep", str( tempStep ), timestamp=False )

try:
	tempSensor = W1ThermSensor()
	#print("tempsensor ON")
except:
	tempSensor = None
	#print("tempsensor OFF")

# PIR (Motion Sensor) setup:

pirEnabled 		= 0 if not( settings.exists( "pir" ) ) else settings.get( "pir" )[ "pirEnabled" ]
pirPin  		= 5 if not( settings.exists( "pir" ) ) else settings.get( "pir" )[ "pirPin" ]

pirCheckInterval 	= 0.5 if not( settings.exists( "pir" ) ) else settings.get( "pir" )[ "pirCheckInterval" ]

pirIgnoreFromStr	= "00:00" if not( settings.exists( "pir" ) ) else settings.get( "pir" )[ "pirIgnoreFrom" ]
pirIgnoreToStr		= "00:00" if not( settings.exists( "pir" ) ) else settings.get( "pir" )[ "pirIgnoreTo" ]

pirIgnoreFrom		= datetime.time( int( pirIgnoreFromStr.split( ":" )[ 0 ] ), int( pirIgnoreFromStr.split( ":" )[ 1 ] ) )
pirIgnoreTo		= datetime.time( int( pirIgnoreToStr.split( ":" )[ 0 ] ), int( pirIgnoreToStr.split( ":" )[ 1 ] ) )

log( LOG_LEVEL_INFO, CHILD_DEVICE_PIR, MSG_SUBTYPE_ARMED, str( pirEnabled ), timestamp=False )
log( LOG_LEVEL_INFO, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/settings/pir/checkInterval", str( pirCheckInterval ), timestamp=False )
log( LOG_LEVEL_INFO, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/settings/pir/ignoreFrom", str( pirIgnoreFromStr ), timestamp=False )
log( LOG_LEVEL_INFO, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/settings/pir/ignoreTo", str( pirIgnoreToStr ), timestamp=False )

# GPIO Pin setup and utility routines:

heatPin 			= 23 if not( settings.exists( "thermostat" ) ) else settings.get( "thermostat" )[ "heatPin" ]
lightPin			= 24 if not( settings.exists( "thermostat" ) ) else settings.get( "thermostat" )[ "lightPin" ]
coolPin				= 27 if not( settings.exists( "thermostat" ) ) else settings.get( "thermostat" )[ "coolPin" ]	

GPIO.setmode( GPIO.BCM )
GPIO.setup( heatPin, GPIO.OUT )
GPIO.output( heatPin, GPIO.HIGH )
GPIO.setup( lightPin, GPIO.OUT )
GPIO.output( lightPin, GPIO.HIGH )
GPIO.setup( coolPin, GPIO.OUT )
GPIO.output( coolPin,GPIO.HIGH)


if pirEnabled:
	GPIO.setup( pirPin, GPIO.IN )

CHILD_DEVICE_HEAT					= "heat"
CHILD_DEVICE_COOL					= "cool"

log( LOG_LEVEL_INFO, CHILD_DEVICE_COOL, MSG_SUBTYPE_BINARY_STATUS, str( coolPin ), timestamp=False )
log( LOG_LEVEL_INFO, CHILD_DEVICE_HEAT, MSG_SUBTYPE_BINARY_STATUS, str( heatPin ), timestamp=False )
log( LOG_LEVEL_INFO, CHILD_DEVICE_PIR, MSG_SUBTYPE_TRIPPED, str( pirPin ), timestamp=False )


##############################################################################
#                                                                            #
#       dht22 esp8266 external temp connect                                  #
#                                                                            #
##############################################################################
#dht ext temp setup:
dhtEnabled		= 0 if not( settings.exists( "dhtext") ) else settings.get("dhtext" )[ "dhtEnabled" ]
dhtInterval		= 2000 if not( settings.exists( "dhtext") ) else settings.get("dhtext" )[ "dhtTimeout" ]
dhtTemp			= 0 
dhtUm			= 0
dht_label		= Label( text= " ",size_hint = (None,None), font_size = '25sp', markup=True, text_size= (300,75),color=( 0.5, 0.5, 0.5, 0.2 ))
dhtTest			= 0
dhtSchedule     	= 0
dhtCorrect		= 0 if not( settings.exists( "dhtext") ) else settings.get("dhtext" )[ "dhtCorrect" ]
dhtweb 			= "http://" + settings.get( "dhtext" )[ "dhtClientIP" ] 

def get_dht( url ):
		return json.loads( urllib2.urlopen( url, None, 5 ).read() )

def dht_load (dt):
	global dhtTemp,dhtEnabled,dhtTest,dhtSchedule
	try	:	
		dhtUrl	= "http://"+settings.get("dhtext" )[ "dhtClientIP" ]+"/dati"
		dhtread = get_dht(dhtUrl )
		dhtTemp=dhtread["S_temperature"] 
		dhtUm=dhtread["S_humidity"]
		dht_label.text = "Dht : T: "+str(dhtTemp)+scaleUnits+" , Ur: "+str(dhtUm)+" %"
		dhtEnabled 	= 1
		dhtTest		= 0
		if dhtSchedule	== 0 :
			dhtSchedule = 1
			reloadSchedule()
	except:
		dht_label.text = ""	
		dhtTest += 1	
		dhtEnabled = 0
		dhtSchedule = 0
	if dhtTest <= 5:
		Clock.schedule_once( dht_load, dhtInterval )	
	elif dhtTest >=7 :
		Clock.schedule_once(dht_load,120)	
	else:
		reloadSchedule()
		Clock.schedule_once(dht_load,60)

##############################################################################
#                                                                            #
#       dht22 esp8266 out temp 				                     #
#                                                                            #
##############################################################################
tempStep = 1
dhtoutEnabled		= 0 if not( settings.exists( "dhtout") ) else settings.get("dhtout" )[ "dhtoutEnabled" ]
dhtoutweb 		= "http://" + settings.get( "dhtout" )[ "dhtoutIP" ] + "/dati"
def dhtoutRead():
	global out_temp,out_humidity,dhtoutweb
	try:
		dhtoutread = get_dht(dhtoutweb)
		out_temp=dhtoutread["S_temperature"] 
		out_humidity=dhtoutread["S_humidity"]
	except:
		out_temp= 0
		out_humidity=0
		
##############################################################################
#                                                                            #
#       dht22 esp8266 ir read Temperature    	                             #
#                                                                            #
##############################################################################	
def dhtIrRead(dt):
	if dhtIr_number>=1:
		global dhtCheck, dhtIrTimer,dhtIRLabel
		dhtIrTimer = Clock.schedule_once( dhtIrRead, dhtIR[0,0])
		for c in range(0, dhtIr_number):
			try:
				dhtirread = json.loads( urllib2.urlopen( dhtIR[c,1]+"/dati", None, 5 ).read() )
				dhtIR[c,3]=dhtirread["S_temperature"] 
				dhtIR[c,4]=dhtirread["S_humidity"]
				dhtIR[c,5]=dhtirread["S_control"]
				dhtIR[c,6]=dhtirread["S_setTemp"]
				dhtCheck = dhtirread["S_control"]
				labelState = "ON" if (dhtCheck == 1) else  "OFF"
				dhtIRLabel[c,0].text =  "[b]    - "+dhtIR[c,2] + "[/b] - \n \n " + dhtIR[c,1] +"\n temp : "+ str(dhtIR[c,3]) + "\n Umidita : " +str(dhtIR[c,4])+ "% \n set Temp : " +str(round(float(dhtIR[c,6]),1))+"\n Stato : " + labelState
			except:
				dhtcheck = 0
				log( LOG_LEVEL_INFO, CHILD_DEVICE_DHTIR, MSG_SUBTYPE_CUSTOM + "/read/dhtir/number", str( c), timestamp=False )	
##############################################################################
#                                                                            #
#       dht22 esp8266 ir send Temperature		                     #
#                                                                            #
##############################################################################	
def dhtIRSend():
	if dhtIr_number>=1:
		for c in range(0, dhtIr_number):
			try:	
				if setTemp >= 27:
					f = urllib2.urlopen(dhtIR[c,1]+"/irSender?99")
				else:
					f = urllib2.urlopen(dhtIR[c,1]+"/irSender?"+str(setTemp))
			except:
				log( LOG_LEVEL_INFO, CHILD_DEVICE_DHTIR, MSG_SUBTYPE_CUSTOM + "/send/dhtir/number", str( c), timestamp=False )	
		
##############################################################################
#                                                                            #
#       dht22 esp8266 zone read				                     #
#                                                                            #
##############################################################################
def dhtZoneRead(dt):
	if dhtZone_number >=1:
		global dhtCheck ,dhtZoneTimer
		dhtCheck = 0
		for c in range(0, dhtZone_number):
			try:
				dhtzoneread = json.loads( urllib2.urlopen( dhtZone[c,1]+"/dati", None, 5 ).read() )
				dhtZone[c,3]=dhtzoneread["S_temperature"] 
				dhtZone[c,4]=dhtzoneread["S_humidity"]
				dhtZone[c,5]= dhtzoneread["S_control"]
				dhtZone[c,6]=dhtzoneread["S_setTemp"]
				dhtCheck = dhtzoneread["S_control"]
				labelState = "ON" if (dhtCheck == 3) else  "OFF"
				dhtZoneLabel[c,0].text =  "[b]    - "+dhtZone[c,2] + "[/b] - \n \n " + dhtZone[c,1] +"\n temp : "+ str(dhtZone[c,3]) + "\n Umidita : " +str(dhtZone[c,4])+ "% \n set Temp : " +str(round(float(dhtZone[c,6]),1))+"\n Stato : " + labelState
				
			except:
				log( LOG_LEVEL_INFO, CHILD_DEVICE_DHTZONE, MSG_SUBTYPE_CUSTOM + "/read/dhtzone/number", str( c), timestamp=False )
				dhtcheck = 0
		dhtZoneTimer = Clock.schedule_once( dhtZoneRead, dhtZone[0,0])
##############################################################################
#                                                                            #
#       dht22 esp8266 set zone				                     #
#                                                                            #
##############################################################################
def dhtZoneSend(tempsetting):
	if dhtZone_number >=1:
		for c in range(0, dhtZone_number):
			try:	
				f = urllib2.urlopen(dhtZone[c,1]+"/zoneON?"+ str(tempsetting))

			except:
				
				log( LOG_LEVEL_INFO, CHILD_DEVICE_DHTZONE, MSG_SUBTYPE_CUSTOM + "/send/dhtzone/number", str( c), timestamp=False )
		
##############################################################################
#                                                                            #
#       dht22 esp8266 comandi vari			                     #
#                                                                            #
##############################################################################
def dhtSend(comando):
	if dhtZone_number >=1:
		for c in range(0, dhtZone_number):
			try: 	
				f = urllib2.urlopen(dhtZone[c,1]+"/"+ comando)
			
			except:
				log( LOG_LEVEL_INFO, CHILD_DEVICE_DHTZONE, MSG_SUBTYPE_CUSTOM + "/send/dhtzone/command", comando, timestamp=False )
				
	if dhtIr_number>=1:	
		for c in range(0, dhtIr_number):	
			try:
				f = urllib2.urlopen(dhtIR[c,1]+"/"+ comando)
				
			except:
				
				log( LOG_LEVEL_INFO, CHILD_DEVICE_DHTIR, MSG_SUBTYPE_CUSTOM + "/send/dhtIr/command", comando, timestamp=False )
	if dhtRele == 1:
		try: 	
			f = urllib2.urlopen("http://"+dhtReleIP+"/"+ comando)
			
		except:
			
			log( LOG_LEVEL_INFO, CHILD_DEVICE_DHTRELE, MSG_SUBTYPE_CUSTOM + "/send/dhtRele/command", comando, timestamp=False )

def dhtReleSend(comando):
	if dhtRele == 1:
			try: 	
				f = urllib2.urlopen("http://"+dhtReleIP+"/"+ comando)
				
			except:
				
				log( LOG_LEVEL_INFO, CHILD_DEVICE_DHTRELE, MSG_SUBTYPE_CUSTOM + "/send/dhtRele/command", comando, timestamp=False )
def dhtReleRead(dt):
	if dhtRele == 1:
		global dhtCheck,dhtReleTimer
		try:
			dhtReleread = json.loads( urllib2.urlopen( "http://"+dhtReleIP+"/dati", None, 5 ).read() )
			dhtCheck =  dhtReleread["S_control"]
			
		except:
			
			log( LOG_LEVEL_INFO, CHILD_DEVICE_DHTRELE, MSG_SUBTYPE_CUSTOM + "/read/dhtRele/command", comando, timestamp=False )
			dhtcheck = 0
		dhtReleTimer = Clock.schedule_once( dhtReleRead,settings.get( "dht_rele" )[ "rele_timeout" ])
##############################################################################
#                                                                            #
#       UI Controls/Widgets                                                  #
#                                                                            #
##############################################################################

controlColours = {
					"normal": ( 1.0, 1.0, 1.0, 1.0 ),
					"Cool":   ( 1.0, 1.0, 1.0, 1.0 ),
					"Heat":   ( 1.0, 1.0 ,1.0, 1.0 ),
					"Hold":   ( 1.0, 1.0, 1.0, 1.0 ),					
				 }


def setControlState( control, state ):
	global setTemp,tempStep	
	with thermostatLock:
		control.state = state
		if control == coolControl and state == "down":
			tempStep = 1
			setTemp = round(int(setTemp),1)
		elif control == heatControl and state =="down" : 
			tempStep  = 0.5  if not( settings.exists( "thermostat" ) ) else settings.get( "thermostat" )[ "tempStep" ]
		
			
		#if state == "normal":
		#	control.background_color = controlColours[ "normal" ]
		#else:
		#	control.background_color = controlColours[ control.text.replace( "[b]", "" ).replace( "[/b]", "" ) ]
		
		controlLabel = control.text.replace( "[b]", "" ).replace( "[/b]", "" ).lower()
		log( LOG_LEVEL_STATE, controlLabel +  CHILD_DEVICE_SUFFIX_UICONTROL, MSG_SUBTYPE_BINARY_STATUS, "0" if state == "normal" else "1" )

coolControl = ToggleButton( text="[b]       Estate  [/b]", 
							markup=True, 
							size_hint = ( None, None ),
							font_size="28sp",
							border = (0,0,0,0),
							background_normal= "web/images/button_1.png",
							background_down = "web/images/button_21.png",
							color = (1,1,1,1)
							)	
			

		
	
heatControl = ToggleButton( text="[b]         Inverno  [/b]", 
				markup=True, 
				size_hint = ( None, None ),
				font_size="28sp",
				border = (0,0,0,0),
				background_normal= "web/images/button_1.png",
				background_down = "web/images/button_11.png",
				color = (1,1,1,1)
				)



holdControl = ToggleButton( text="[b]           Manuale  [/b]", 
				markup=True, 
				size_hint = ( None, None ),
				font_size="28sp",
				border = (0,0,0,0),
				background_normal= "web/images/button_1.png",
				background_down = "web/images/button_31.png",
				color = (1,1,1,1)
				)
setControlState( heatControl, "normal" if not( state.exists( "state" ) ) else state.get( "state" )[ "heatControl" ] )
setControlState( coolControl, "normal" if not( state.exists( "state" ) ) else state.get( "state" )[ "coolControl" ] )
setControlState( holdControl, "normal" if not( state.exists( "state" ) ) else state.get( "state" )[ "holdControl" ] )

plusControl = Button( text="", 
				markup=True, 
				size_hint = ( None, None ),
				font_size="28sp",
				border = (0,0,0,0),
				background_normal= "web/images/plus.png",
				background_down = "web/images/plus_1.png",
				color = (1,1,1,1)
				)
				
minusControl = Button( text="", 
				markup=True, 
				size_hint = ( None, None ),
				font_size="28sp",
				border = (0,0,0,0),
				background_normal= "web/images/minus.png",
				background_down = "web/images/minus_1.png",
				color = (1,1,1,1)
				)


def get_status_string():
	with thermostatLock:
		sched = "None"
		temperature = 0
		if holdControl.state == "down" :
			sched = "Hold"
			if heatControl.state == "down":
				testText="Caldaia"
			else:
				testText = "Clima"
			temperature = setTemp
		elif useTestSchedule:
			sched = "Test"
			temperature = setTemp
		elif heatControl.state == "down":
			testText="Caldaia"
			if dhtSchedule == 0:				
				sched = "Heat"
			else:
				sched = "Dht"
			temperature = setTemp
		elif coolControl.state == "down":
			testText="Clima"
			sched = "Cool"
			temperature = setTemp
		else:
		    testText="Caldaia"
		    sched = "No Ice" 
		    temperature = settings.get("thermostat")["tempice"]
		    testHeat = False
		if GPIO.input( heatPin ) == 0:
			testHeat = True
		elif GPIO.input( coolPin ) == 0:
			testHeat = True
		else :
			testHeat = False

		setLabel.color = (1,1,1,1)
	
		return 	   "  Temp. Set: " +str(temperature)+scaleUnits+"\n  "+\
			   testText +" :    " + ( "[i][b][color=ff3333]On[/b][/i][/color]" if testHeat else "Off" ) + "\n  "+\
			   "Sched:   " + sched


versionLabel	= Label( text="Thermostat v" + str( THERMOSTAT_VERSION ), size_hint = ( None, None ), font_size='10sp', markup=True, text_size=( 150, 20 ) )
currentLabel	= Label( text="[b]" + str( currentTemp ) + scaleUnits+"[/b]", size_hint = ( None, None ), font_size='100sp', markup=True, text_size=( 300, 200 ) )
altCurLabel	= Label( text=currentLabel.text, size_hint = ( None, None ), font_size='100sp', markup=True, text_size=( 300, 200 ), color=( 0.5, 0.5, 0.5, 0.2 ) )
coolCurLabel	= Label( text=currentLabel.text, size_hint = ( None, None ), font_size='100sp', markup=True, text_size=( 300, 200 ), color=( 0.5, 0.5, 0.5, 0.2 ) )

setLabel     = Label( text= "[b]"+ str( round(setTemp,1) ) +" "+ "[/b]", size_hint = ( None, None ), font_size='40sp', markup=True, text_size=( 120, 120 ) )
statusLabel  = Label( text=get_status_string(), size_hint = ( None, None ),  font_size='30sp', markup=True, text_size=( 240, 230 ) )

altStatusLabel = Label( text=get_status_string(), size_hint = ( None, None),font_size='30sp', markup=True, text_size=( 240, 230 ),color=(0.5,0.5,0.5,0.2))

dateLabel	= Label( text="[b]" + time.strftime("%d %b %a, %Y") + "[/b]", size_hint = ( None, None ), font_size='25sp', markup=True, text_size=( 270, 40 ) )

timeStr		= time.strftime("%H:%M").lower()
timeInit	= time.time()

timeLabel	 = Label( text="[b]" + ( timeStr if timeStr[0:1] != "0" else timeStr[1:] ) + "[/b]", size_hint = ( None, None ), font_size='45sp', markup=True, text_size=( 180, 75 ) )
altTimeLabel = Label( text=timeLabel.text, size_hint = ( None, None ), font_size='40sp', markup=True, text_size=( 180, 75 ), color=( 0.5, 0.5, 0.5, 0.2 ) )

screenMgr    = None

#############################################################################
#                                                                            #
#       Weather functions/constants/widgets                                  #
#                                                                            #
##############################################################################

weatherLocation 	 = settings.get( "weather" )[ "location" ]
weatherAppKey		 = settings.get( "weather" )[ "appkey" ]
weatherURLBase  	 = "https://api.darksky.net/forecast/"
weatherURLTimeout 	 = settings.get( "weather" )[ "URLtimeout" ]
weatherURLCurrent 	 = weatherURLBase + weatherAppKey+ "/" + weatherLocation + "?units=si&exclude=[minutely,hourly,flags,alerts]&lang=it"

forecastRefreshInterval  = settings.get( "weather" )[ "forecastRefreshInterval" ] * 60  
weatherExceptionInterval = settings.get( "weather" )[ "weatherExceptionInterval" ] * 60  
weatherRefreshInterval   = settings.get( "weather" )[ "weatherRefreshInterval" ] * 60

weatherSummaryLabel  = Label( text="", size_hint = ( None, None ), font_size='20sp', markup=True, text_size=( 200, 20 ) )
weatherDetailsLabel  = Label( text="", size_hint = ( None, None ), font_size='20sp', markup=True, text_size=( 300, 150 ), valign="top" )
weatherImg           = Image( source="web/images/na.png", size_hint = ( None, None ) )
weatherminSummaryLabel  = Label( text="", size_hint = ( None, None ), font_size='20sp', markup=True, text_size=( 200, 20 ), color=(0.5,0.5,0.5,0.2) )
weatherminImg           = Image( source="web/images/na.png", size_hint = ( None, None ), color=(1,1,1,0.4) )
forecastData = []
forecastSummaryLabel= []
forecastDetailsLabel=[]
forecastImg=[]
for c in range (0,3):
	forecastData.append(Label( text="", size_hint = ( None, None ), font_size='16sp',  markup=True, text_size=( 300, 20 )))
	forecastSummaryLabel.append(Label( text="", size_hint = ( None, None ), font_size='16sp',  markup=True, text_size=( 250, 50 )))
	forecastDetailsLabel.append(Label( text="", size_hint = ( None, None ), font_size='16sp',  markup=True, text_size=( 300, 150 ), valign="top" ))
	forecastImg.append(Image( source="web/images/na.png", size_hint = ( None, None ) )) 
forecastSummary = Label( text="", size_hint = ( None, None ), font_size='18sp',  markup=True, text_size=( 800, 50 ))

def get_weather( url ):
	return json.loads( urllib2.urlopen( url, None, weatherURLTimeout ).read() )



def get_cardinal_direction( heading ):
	directions = [ "N", "NE", "E", "SE", "S", "SW", "W", "NW", "N" ]
	return directions[ int( round( ( ( heading % 360 ) / 45 ) ) ) ]
	
	
def display_current_weather( dt ):
	with weatherLock:
		global out_temp,temp_vis
		interval = weatherRefreshInterval
		try:
	
			weather = get_weather( weatherURLCurrent )
			weatherImg.source = "web/images/" + weather[ "currently" ][ "icon" ] + ".png" 
			weatherSummaryLabel.text = "[b]" + weather[ "currently" ][ "summary" ] + "[/b]"
			forecastSummary.text = "[b]" + weather["daily"]["summary"] + "[/b]"
			# compile data for forecast
			for c in range(0,3):
				today    = weather[ "daily" ]["data"][ c ]
				forecastData[c].text = "[b]"+time.strftime('%A  %d/%m ', time.localtime(today["time"]))+"[/b]"
				forecastImg[c].source = "web/images/" + today[ "icon" ] + ".png" 
				forecastSummaryLabel[c].text =  "[b]"+ today["summary"][:-1]+"[/b] "	
				forecastText = "\n".join( (
				"Max: " + str( int( round( today[ "temperatureMax" ], 0 ) ) ) + "        Min: " + str( int( round( today[ "temperatureMin" ], 0 ) ) ) ,
				"Umidita:        "+ str( today[ "humidity" ]*100 ) + "%",
				
				"Nuvole:          " + str( today[ "cloudCover" ]*100 ) + "%",
				
				"Pressione:     " + str( int(today[ "pressure" ] )) + "mBar",
				
				"Vento:            " + str( int( round( today[ "windSpeed" ] * windFactor ) ) ) + windUnits + " " + get_cardinal_direction( today["windBearing" ] ),
				
			) )	
			
				forecastDetailsLabel[c].text = forecastText	
			
			if dhtoutEnabled == 1:
				dhtoutRead()
				
				if out_temp == 0:				
					temp_vis = str( int( round( weather[ "currently" ][ "temperature" ], 1 ) ) )
					
				else:
					temp_vis = str(round(out_temp,1))
					um_vis = str(int(round(out_humidity,0)))
					
			else:
				temp_vis = str( int( round( weather[ "currently" ][ "temperature" ], 1 ) ) )
							
				um_vis = str( int(round(weather[ "currently" ][ "humidity" ],2 )*100))
				
			weatherDetailsLabel.text = "\n".join( (
				"Temp :   " + temp_vis + " " +scaleUnits,
				"  Ur :   " + um_vis + "%"
				#"Vento:       " + str( int( round( weather[ "wind" ][ "speed" ] * windFactor ) ) ) + windUnits + " " + get_cardinal_direction( weather[ "wind" ][ "deg" ] ),
				#"Nuvole:     " + str( weather[ "clouds" ][ "all" ] ) + "%",
			) )
		
			log( LOG_LEVEL_INFO, CHILD_DEVICE_WEATHER_CURR, MSG_SUBTYPE_TEXT, weather[ "currently" ][ "summary" ] + "; " + re.sub( '\n', "; ", re.sub( ' +', ' ', weatherDetailsLabel.text ).strip() ) )
			
		except:
			interval = weatherExceptionInterval

			weatherImg.source = "web/images/na.png"
			weatherSummaryLabel.text = ""
			weatherDetailsLabel.text = ""

			log( LOG_LEVEL_ERROR, CHILD_DEVICE_WEATHER_CURR, MSG_SUBTYPE_TEXT, "Update FAILED!" )

		Clock.schedule_once( display_current_weather, interval )

	
		
def get_precip_amount( raw ):
	precip = round( raw * precipFactor, precipRound )

	if tempScale == "metric":
		return str( int ( precip ) )
	else:
		return str( precip )


##############################################################################
#                                                                            #
#       Utility Functions                                                    #
#                                                                            #
##############################################################################

def get_ip_address():
	s = socket.socket( socket.AF_INET, socket.SOCK_DGRAM )
	s.settimeout( 10 )   # 10 seconds
	try:
		s.connect( ( "8.8.8.8", 80 ) )    # Google DNS server
		ip = s.getsockname()[0] 
		log( LOG_LEVEL_INFO, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM +"/settings/ip", ip, timestamp=False )
	except socket.error:
		ip = "127.0.0.1"
		log( LOG_LEVEL_ERROR, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/settings/ip", "FAILED to get ip address, returning " + ip, timestamp=False )

	return ip


def getVersion():
	log( LOG_LEVEL_STATE, CHILD_DEVICE_NODE, MSG_SUBTYPE_VERSION, THERMOSTAT_VERSION )


def restart():
	log( LOG_LEVEL_STATE, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/restart", "Thermostat restarting...", single=True ) 
	GPIO.cleanup()

	if logFile is not None:
		logFile.flush()
		os.fsync( logFile.fileno() )
		logFile.close()

	os.execl( sys.executable, 'python', __file__, *sys.argv[1:] )	# This does not return!!!


def setLogLevel( msg ):
	global logLevel

	if LOG_LEVELS.get( msg.payload ):
		log( LOG_LEVEL_STATE, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/loglevel", "LogLevel set to: " + msg.payload ) 

		logLevel = LOG_LEVELS.get( msg.payload, logLevel )
	else:
		log( LOG_LEVEL_ERROR, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/loglevel", "Invalid LogLevel: " + msg.payload ) 

    
##############################################################################
#                                                                            #
#       Thermostat Implementation                                            #
#                                                                            #
##############################################################################

# Main furnace/AC system control function:

def change_system_settings():
	with thermostatLock:
		global csvSaver,dhtCheck
		hpin_start = str( GPIO.input( heatPin ) )
		cool_start = str( GPIO.input( coolPin))
		if heatControl.state == "down":	
			if dhtCheck == 0 :
				dhtZoneSend(setTemp)
				dhtZoneRead(2)
			if setTemp >= currentTemp + tempHysteresis or dhtCheck == 1 :
				if dhtRele == 1 and dhtCheck == 200:
					dhtReleSend("releON")
				GPIO.output( heatPin, GPIO.LOW )
				GPIO.output( coolPin,GPIO.HIGH)
			elif setTemp <= currentTemp:
				if dhtRele == 1 and dhtCheck == 201:	
					dhtReleSend("releOFF")
				GPIO.output( heatPin, GPIO.HIGH )
				GPIO.output( coolPin, GPIO.HIGH)
		elif coolControl.state== "down":
			if dhtCheck == 1 :
				GPIO.output( coolPin, GPIO.LOW)
				GPIO.output( heatPin, GPIO.HIGH)
			
			elif dhtCheck == 2:
				GPIO.output( coolPin, GPIO.HIGH)
				GPIO.output( heatPin, GPIO.HIGH )
				
			else:
				GPIO.output( coolPin, GPIO.LOW)
				GPIO.output( heatPin, GPIO.HIGH )
				dhtIRSend()
				dhtIrRead(1)
				
				
		else:
		#modifica per minima temp antigelo 
			if dhtCheck == 0 :
				dhtZoneSend(setice)
			if setice >= currentTemp +tempHysteresis and holdControl != "down" or dhtCheck == 1:
				GPIO.output(heatPin,GPIO.LOW)
				GPIO.output( coolPin, GPIO.HIGH)
			elif setice <=currentTemp:
				GPIO.output(heatPin,GPIO.HIGH)
				GPIO.output( coolPin, GPIO.HIGH)
			if holdControl.state == "down":
			    	if setTemp >= currentTemp + tempHysteresis or dhtCheck == 1:
			    		if dhtRele == 1:
						dhtReleSend("releON")
			    	    	GPIO.output(heatPin, GPIO.LOW)
			    	    	GPIO.output( coolPin, GPIO.HIGH)
			    	else:
			    	    	if dhtRele == 1:
						dhtReleSend("releOFF")
				    	GPIO.output( heatPin, GPIO.HIGH )
				    	GPIO.output( coolPin, GPIO.HIGH)


		# save the thermostat state in case of restart
		state.put( "state", setTemp=setTemp, heatControl=heatControl.state,  coolControl=coolControl.state, holdControl=holdControl.state,dhtEnabled=dhtEnabled)
		
		statusLabel.text = get_status_string()
		altStatusLabel.text = get_status_string()
		setLabel.text = "[b]"+str(setTemp)+"[/b]"
		if hpin_start != str( GPIO.input( heatPin ) ):
			Clock.unschedule(csvSaver)
			csvSaver = Clock.schedule_once(save_graph, 1)
			log( LOG_LEVEL_STATE, CHILD_DEVICE_HEAT, MSG_SUBTYPE_BINARY_STATUS, "1" if GPIO.input( heatPin ) else "0" )
		if cool_start != str( GPIO.input( coolPin ) ):
			Clock.unschedule(csvSaver)
			csvSaver = Clock.schedule_once(save_graph, 1)
			log( LOG_LEVEL_STATE, CHILD_DEVICE_HEAT, MSG_SUBTYPE_BINARY_STATUS, "1" if GPIO.input( coolPin ) else "0" )

# This callback will be bound to the touch screen UI buttons:

def control_callback( control ):
	global setTemp,tempStep
	with thermostatLock:
		setControlState( control, control.state ) 	# make sure we change the background colour!
		
				
		if control is holdControl :
			if control.state == "down" and heatControl.state == "normal" and coolControl.state == "normal":
				
				setControlState(holdControl, "normal")
			reloadSchedule()	
		elif control is coolControl:	
			dhtSend("clear")
			if dhtIr_number > 0:
				if control.state == "down":
					setControlState( heatControl, "normal" )
									
					reloadSchedule()
					
				else:
					setControlState( coolControl, "normal")
					setControlState( holdControl, "normal")
			else:
				setControlState( coolControl, "normal")
				
		elif control is heatControl:
			dhtSend("clear")
			if control.state == "down":
				setControlState( coolControl, "normal" )
				reloadSchedule()
					
			setControlState (holdControl,"normal")		

# Check the current sensor temperature

def check_sensor_temp( dt ):
	with thermostatLock:
		global currentTemp, priorCorrected
		global tempSensor,dhtTemp,openDoor,openDoorCheck
		correctedTemp=20		
		if dhtEnabled == 1 and dhtTemp <> 0:			
			rawTemp = dhtTemp
			correctedTemp = ( ( ( rawTemp - freezingMeasured ) * referenceRange ) / measuredRange ) + freezingPoint + dhtCorrect
			log( LOG_LEVEL_DEBUG, CHILD_DEVICE_TEMP, MSG_SUBTYPE_CUSTOM + "/dhtTemp", str( rawTemp ) )
			log( LOG_LEVEL_DEBUG, CHILD_DEVICE_TEMP, MSG_SUBTYPE_CUSTOM + "/corrected", str( correctedTemp ) )
			
		else:
			if tempSensor is not None:
				rawTemp = tempSensor.get_temperature( sensorUnits )
				correctedTemp = ( ( ( rawTemp - freezingMeasured ) * referenceRange ) / measuredRange ) + freezingPoint + correctSensor
				log( LOG_LEVEL_DEBUG, CHILD_DEVICE_TEMP, MSG_SUBTYPE_CUSTOM + "/raw", str( rawTemp ) )
				log( LOG_LEVEL_DEBUG, CHILD_DEVICE_TEMP, MSG_SUBTYPE_CUSTOM + "/corrected", str( correctedTemp ) )
#check if temp is changed and if opendoor 			
		
		if abs( priorCorrected - correctedTemp ) >= TEMP_TOLERANCE:
			if 	abs( priorCorrected - correctedTemp ) >= 1 and openDoor <= openDoorCheck:
							
				openDoor +=1			
			else:	
								
				openDoor == 0				
				log( LOG_LEVEL_STATE, CHILD_DEVICE_TEMP, MSG_SUBTYPE_TEMPERATURE, str( currentTemp ) )	
				priorCorrected = correctedTemp
				currentTemp = round( correctedTemp, 1 )	

		currentLabel.text = "[b]" + str( currentTemp ) +scaleUnits+ "[/b]"
		altCurLabel.text  = currentLabel.text

		dateLabel.text      = "[b]" + time.strftime("%d %b %a, %Y") + "[/b]"

		timeStr		 = time.strftime("%H:%M").lower()

		timeLabel.text      = ( "[b]" + ( timeStr if timeStr[0:1] != "0" else timeStr[1:] ) + "[/b]" ).lower()
		altTimeLabel.text  	= timeLabel.text

		change_system_settings()


# This is called when the desired temp slider is updated:

def update_set_temp( control ):
	with thermostatLock:
		global setTemp
		priorTemp = setTemp
		if control is plusControl:
			setTemp = priorTemp + tempStep
		if control is minusControl:
			setTemp = priorTemp - tempStep
			
		if setTemp >= maxTemp or setTemp <= minTemp:
			setTemp = priorTemp	
		setLabel.text = "[b]" + str( round(setTemp,1) )  + "[/b]"
		
		if heatControl.state == "down":
				dhtZoneSend(setTemp)
		if coolControl.state == "down":
				dhtIRSend()
		if priorTemp != setTemp:
			log( LOG_LEVEL_STATE,"Set Temperature", MSG_SUBTYPE_TEMPERATURE, str( setTemp ) )


# Check the PIR motion sensor status

def check_pir( pin ):
	global minUITimer
	global lightOffTimer
	with thermostatLock:
		if GPIO.input( pirPin ): 
			log( LOG_LEVEL_INFO, CHILD_DEVICE_PIR, MSG_SUBTYPE_TRIPPED, "1" )

			if minUITimer != None:
				  Clock.unschedule( show_minimal_ui )
				  if lightOffTimer != None:
					Clock.unschedule( light_off )	
			minUITimer = Clock.schedule_once( show_minimal_ui, minUITimeout ) 
			lighOffTimer = Clock.schedule_once( light_off, lightOff )	
			ignore = False
			now = datetime.datetime.now().time()
			
			if pirIgnoreFrom > pirIgnoreTo:
				if now >= pirIgnoreFrom or now < pirIgnoreTo:
					ignore = True
			else:
				if now >= pirIgnoreFrom and now < pirIgnoreTo:
					ignore = True

			if screenMgr.current == "minimalUI" and not( ignore ):
				screenMgr.current = "thermostatUI"
				log( LOG_LEVEL_DEBUG, CHILD_DEVICE_SCREEN, MSG_SUBTYPE_TEXT, "Full" )
	
		else:
			log( LOG_LEVEL_DEBUG, CHILD_DEVICE_PIR, MSG_SUBTYPE_TRIPPED, "0" )


#Salvo i dati per il grafico
def save_graph(dt):
# save graph
#conversione heatpin in temperatura 10=off 12=on
	global csvSaver
	global csvTimeout
	Clock.unschedule(csvSaver)
	switchTemp = 0
	if GPIO.input( heatPin ) == 0:
		switchTemp = 12
	else :
		if GPIO.input( coolPin ) == 0:
			switchTemp = 5
		else :
			switchTemp = 0

	#scrivo il file csv con i dati 
	out_file=open (("./web/graph/" + "thermostat.csv"),"a")
	out_file.write (time.strftime("%Y/%m/%d %H:%M:%S", time.localtime())+", "+str(setTemp)+", "+str(currentTemp)+ ", " + str(switchTemp)+ "\n")
	out_file.close()
	timeInit=time.time()
	
	csvSaver = Clock.schedule_once(save_graph, csvTimeout)		
		
#premendo set label change dht enabled

def dht_change(test,data):
	global dhtEnabled,dhtSchedule
	global setTemp
	x_pos=data.pos[0]
	y_pos=data.pos[1]	
	if (x_pos>=662 and x_pos<=758 and y_pos>=122 and  y_pos <= 163):
		if heatControl.state == "down":			
			setLabel.color=(1,0.1,0.1,1)		
			if dhtEnabled == 0 and settings.get("dhtext" )[ "dhtEnabled" ] == 1 :
				dhtEnabled = 1			
				Clock.schedule_once(dht_load,3)	
				#print "dht Enabled"
			else:
				dhtEnabled = 0
				dhtSchedule = 0
				dht_label.text = ""
				Clock.unschedule(dht_load)
				reloadSchedule()
				#print "dht Disabled"
	#print "change dht"	,x_pos	,y_pos			
			
# Minimal UI Display functions and classes
#shell.shell(has_input=False, record_output=True, record_errors=True, strip_empty=True)

def show_minimal_ui( dt ):
	with thermostatLock:
		screenMgr.current = "minimalUI"
		log( LOG_LEVEL_DEBUG, CHILD_DEVICE_SCREEN, MSG_SUBTYPE_TEXT, "Minimal" )

def light_off( dt ):
	with thermostatLock:
		GPIO.output( lightPin, GPIO.HIGH )
		log( LOG_LEVEL_DEBUG, CHILD_DEVICE_SCREEN, MSG_SUBTYPE_TEXT, "Screen Off" )
		
def select_menu(testo):
	#print "select menu: ", testo.text
	if testo.text == "Meteo":
		screenMgr.current = "meteoUI"
		Clock.schedule_once(returnScreen,10 )
	if testo.text == "Reboot":
		restart()
	if testo.text == "Cool":
		screenMgr.current = "coolUI"
		Clock.schedule_once(returnScreen,10 )
	if testo.text == "Zone":
		screenMgr.current = "zoneUI"
		Clock.schedule_once(returnScreen,10 )
			
def returnScreen(dt):
	screenMgr.current = "thermostatUI"
	
class MinimalScreen( Screen ):
	def on_touch_down( self, touch ):
		if self.collide_point( *touch.pos ):
			touch.grab( self )
			return True

	def on_touch_up( self, touch ):
		global minUITimer
		global lightOffTimer
		if touch.grab_current is self:
			touch.ungrab( self )
			with thermostatLock:
				Clock.unschedule( light_off )
				if minUITimer != None:
					Clock.unschedule( show_minimal_ui )	
				minUITimer = Clock.schedule_once( show_minimal_ui, minUITimeout )
				lighOffTimer = Clock.schedule_once( light_off, lightOff )
				GPIO.output( lightPin, GPIO.LOW )
				self.manager.current = "thermostatUI"
				log( LOG_LEVEL_DEBUG, CHILD_DEVICE_SCREEN, MSG_SUBTYPE_TEXT, "Full" )
			return True
class meteoScreen( Screen ):
	def on_touch_down( self, touch ):
		if self.collide_point( *touch.pos ):
			touch.grab( self )
			return True

	def on_touch_up( self, touch ):
		global minUITimer
		global lightOffTimer
		if touch.grab_current is self:
			touch.ungrab( self )
			with thermostatLock:
				Clock.unschedule( light_off )
				if minUITimer != None:
					Clock.unschedule( show_minimal_ui )	
				minUITimer = Clock.schedule_once( show_minimal_ui, minUITimeout )
				lighOffTimer = Clock.schedule_once( light_off, lightOff )
				GPIO.output( lightPin, GPIO.LOW )
				self.manager.current = "thermostatUI"
				log( LOG_LEVEL_DEBUG, CHILD_DEVICE_SCREEN, MSG_SUBTYPE_TEXT, "Full" )
			return True
class coolScreen( Screen ):
	def on_touch_down( self, touch ):
		if self.collide_point( *touch.pos ):
			touch.grab( self )
			return True

	def on_touch_up( self, touch ):
		global minUITimer
		global lightOffTimer
		if touch.grab_current is self:
			touch.ungrab( self )
			with thermostatLock:
				Clock.unschedule( light_off )
				if minUITimer != None:
					Clock.unschedule( show_minimal_ui )	
				minUITimer = Clock.schedule_once( show_minimal_ui, minUITimeout )
				lighOffTimer = Clock.schedule_once( light_off, lightOff )
				GPIO.output( lightPin, GPIO.LOW )
				self.manager.current = "thermostatUI"
				log( LOG_LEVEL_DEBUG, CHILD_DEVICE_SCREEN, MSG_SUBTYPE_TEXT, "Full" )
			return True
class zoneScreen( Screen ):
	def on_touch_down( self, touch ):
		if self.collide_point( *touch.pos ):
			touch.grab( self )
			return True

	def on_touch_up( self, touch ):
		global minUITimer
		global lightOffTimer
		if touch.grab_current is self:
			touch.ungrab( self )
			with thermostatLock:
				Clock.unschedule( light_off )
				if minUITimer != None:
					Clock.unschedule( show_minimal_ui )	
				minUITimer = Clock.schedule_once( show_minimal_ui, minUITimeout )
				lighOffTimer = Clock.schedule_once( light_off, lightOff )
				GPIO.output( lightPin, GPIO.LOW )
				self.manager.current = "thermostatUI"
				log( LOG_LEVEL_DEBUG, CHILD_DEVICE_SCREEN, MSG_SUBTYPE_TEXT, "Full" )
			return True

##############################################################################
#                                                                            #
#       Kivy Thermostat App class                                            #
#                                                                            #
##############################################################################

class ThermostatApp( App ):

	def build( self ):
		global screenMgr

	# Set up the thermostat UI layout:
		thermostatUI = FloatLayout( size=( 800, 480 ) )

	# Make the background black:
		with thermostatUI.canvas.before:
			Color ( 0.0, 0.0, 0.0, 1 )
			self.rect = Rectangle( size=( 800, 480 ), pos=thermostatUI.pos )
			Color ( 1.0, 1.0, 1.0, 1 )
	
	# Create the rest of the UI objects ( and bind them to callbacks, if necessary ):
		wimg = Image( source='web/images/sfondo.png' )
		coolControl.bind( on_press=control_callback )	
		heatControl.bind( on_press=control_callback )	
		holdControl.bind( on_press=control_callback )
		plusControl.bind( on_press=update_set_temp )
		minusControl.bind( on_press = update_set_temp )
		setLabel.bind( on_touch_down=dht_change)
	# creo il dropdown menu
   		menu = ["Meteo","Cool","Zone","Reboot"]
   		dropdown = DropDown()
   		for index in range(4):
   			btn = Button(text=menu[index], size_hint_y=None, height=44)
   			btn.bind(on_release=lambda btn: dropdown.select("Pagine"))
   			btn.border= (0,0,0,0)
   			btn.background_normal= "web/images/menu.png"
   			btn.bind(on_press=select_menu)
   			if dhtIr_number == 0  and menu[index] == "Cool":
   				dropdown.add_widget(btn)
   			elif dhtZone_number == 0 and menu[index] == "Zone":
   				dropdown.add_widget(btn)
   			else:
   				dropdown.add_widget(btn)
   		mainbutton = Button(text='Pagine', size_hint=(None, None))
   		mainbutton.border = (0,0,0,0)
   		mainbutton.background_normal= "web/images/menu.png" 
   		mainbutton.pos = (320,320)
   		mainbutton.size= (120,40)
   		mainbutton.bind(on_release=dropdown.open)
   		dropdown.bind(on_select=lambda instance, x: setattr(mainbutton, 'text', x))
   		

   	# set sizing and position info
		
		wimg.size = ( 800, 480 )
		wimg.size_hint = ( None, None )
		wimg.pos = ( 0,0 )
		
		plusControl.size =(80,80)
		plusControl.pos = ( 670, 170 )
		
		minusControl.size =(80,80)
		minusControl.pos = (670, 30 )

		heatControl.size  = ( 210,80 )
		heatControl.pos = ( 40, 160 )

		coolControl.size  = ( 210,80 )
		coolControl.pos = ( 40, 260 )

		statusLabel.pos = ( 400, 215 )


		holdControl.size  = ( 210,80 )
		holdControl.pos = ( 40, 60 )

		setLabel.pos = ( 680,130 )
		

		currentLabel.pos = ( 200, 405 )

		dateLabel.pos = ( 550, 300 )
		timeLabel.pos = ( 710,310 )
		
		
		weatherImg.pos = ( 440, 380 )
		weatherSummaryLabel.pos = ( 640, 410 )
		weatherDetailsLabel.pos = ( 690,320 )
		
		versionLabel.pos = ( 550, 10 )
		d = 60
		for c in range(0,3):
			forecastData[c].pos = (d+85,360)
			forecastImg[c].pos = ( d-20,290 )
			forecastSummaryLabel[c].pos = ( d+40,220 )
			forecastDetailsLabel[c].pos = ( d+70 ,110)
			d += 260
		forecastSummary.pos = (360,410)

		# Add the UI elements to the thermostat UI layout:
		thermostatUI.add_widget( wimg )
		thermostatUI.add_widget( plusControl )
		thermostatUI.add_widget( minusControl )
		thermostatUI.add_widget( heatControl )
		thermostatUI.add_widget( coolControl )
		thermostatUI.add_widget( holdControl )
		thermostatUI.add_widget( currentLabel )
		thermostatUI.add_widget( setLabel )
		thermostatUI.add_widget( statusLabel )
		thermostatUI.add_widget( dateLabel )
		thermostatUI.add_widget( timeLabel )
		thermostatUI.add_widget( weatherImg )
		thermostatUI.add_widget( mainbutton)
		thermostatUI.add_widget( weatherSummaryLabel )
		thermostatUI.add_widget( weatherDetailsLabel )
		thermostatUI.add_widget( versionLabel )
		
		layout = thermostatUI

		# Minimap UI initialization

		uiScreen 	= Screen( name="thermostatUI" )
		uiScreen.add_widget( thermostatUI )

		minScreen 	= MinimalScreen( name="minimalUI" )
		minUI 		= FloatLayout( size=( 800, 480 ) )
			
		
				
		with minUI.canvas.before:
			Color( 0.0, 0.0, 0.0, 1 )
			self.rect = Rectangle( size=( 800, 480 ), pos=minUI.pos )
			altCurLabel.pos = ( 390, 290 )
			altTimeLabel.pos = ( 335, 380 )
			altStatusLabel.pos = (360 , 170 )
				
		minUI.add_widget( altCurLabel )
		minUI.add_widget( altTimeLabel )
		minUI.add_widget( altStatusLabel )
		# se abilitato dhext scrivo i dati in minUI
		if dhtEnabled:
			dht_label.pos = ( 400, 40)
			minUI.add_widget(dht_label)
		minScreen.add_widget( minUI )
		
		
		
		# creo la pagina per il meteo 
		meteScreen      = meteoScreen( name = "meteoUI" )
		meteoUI         = FloatLayout( size=( 800, 480))
		with meteoUI.canvas.before:
			Color( 0.0, 0.0, 0.0, 1 )
			self.rect = Rectangle( size=( 800, 480 ), pos=meteoUI.pos )
		meteoUI.add_widget( forecastSummary)	
		
		for c in range(0,3):
			meteoUI.add_widget( forecastData[c] )
			meteoUI.add_widget( forecastImg[c] )
			meteoUI.add_widget( forecastSummaryLabel[c] )
			meteoUI.add_widget( forecastDetailsLabel[c] )
	
		meteScreen.add_widget( meteoUI )
		
		screenMgr = ScreenManager( transition=NoTransition())		# FadeTransition seems to have OpenGL bugs in Kivy Dev 1.9.1 and is unstable, so sticking with no transition for now	
		
		#creo pagina dedicata ai moduli IR per i Condizionatori
		if dhtIr_number >0 :
			coolwScreen     = coolScreen( name = "coolUI" )
			coolUI        	= FloatLayout(size = (800,480))
			coolimage = Image( source='web/images/sfondo_cool.png' )
			with coolUI.canvas.before:
				Color( 0.0, 0.0, 0.0, 1 )
				self.rect = Rectangle( size=( 800, 480 ), pos=coolUI.pos )
			coolimage.size = ( 800, 480 )
			coolimage.size_hint = ( None, None )
			coolimage.pos = ( 0,0 )
			coolUI.add_widget(coolimage)
			d = 30 
			p = 350
			s = 0
			for c in range (0,dhtIr_number):
				dhtIRLabel[c,0].size = (300,200)
				dhtIRLabel[c,0].pos = (d,p)
				coolUI.add_widget(dhtIRLabel[c,0])
				d +=260
				s +=1
				if s > 2:
					p -=145
					s = 0
					d = 30
			
			coolwScreen.add_widget(coolUI)
			screenMgr.add_widget ( coolwScreen )
		#creo pagina dedicata ai moduli  per le zone
		if dhtZone_number >0 :
			zonewScreen     = zoneScreen( name = "zoneUI" )
			zoneUI        	= FloatLayout(size = (800,480))
			zoneimage = Image( source='web/images/sfondo_zone.png' )
			with coolUI.canvas.before:
				Color( 0.0, 0.0, 0.0, 1 )
				self.rect = Rectangle( size=( 800, 480 ), pos=zoneUI.pos )
			zoneimage.size = ( 800, 480 )
			zoneimage.size_hint = ( None, None )
			zoneimage.pos = ( 0,0 )
			zoneUI.add_widget(zoneimage)
			d = 30 
			p = 350
			s = 0
			for c in range (0,dhtZone_number):
				dhtZoneLabel[c,0].size = (300,200)
				dhtZoneLabel[c,0].pos = (d,p)
				zoneUI.add_widget(dhtZoneLabel[c,0])
				d +=260
				s +=1
				if s > 2:
					p -=145
					s = 0
					d = 30
			
			zonewScreen.add_widget(zoneUI)
			screenMgr.add_widget ( zonewScreen )
		# Aggiungo le pagine allo Screen Manager		
		
		screenMgr.add_widget ( uiScreen )
		screenMgr.add_widget ( minScreen )
		screenMgr.add_widget ( meteScreen)
		
		screenMgr.current = "thermostatUI"
		
		layout = screenMgr
		
		minUITimer = Clock.schedule_once( show_minimal_ui, minUITimeout )
		lighOffTimer = Clock.schedule_once( light_off, lightOff )
		csvSaver = Clock.schedule_once(save_graph, 30)
		if dhtIr_number >=1:
			dhtIrTimer = Clock.schedule_once( dhtIrRead, 4 )
		if dhtZone_number >=1:
			dhtZoneTimer = Clock.schedule_once( dhtZoneRead, 5 )
		if dhtRele == 1:
			dhtReleTimer = Clock.schedule_once( dhtReleRead, 3 )
				
		if pirEnabled:
				Clock.schedule_interval( check_pir, pirCheckInterval )
			
		# Start checking the temperature
		Clock.schedule_interval( check_sensor_temp, tempCheckInterval )
		
		if dhtEnabled == 1:
				Clock.schedule_once(dht_load,2)
		# Show the current weather  		
		Clock.schedule_once( display_current_weather, 3 )
		# azzerro tutti i dht se ce ne sono
		dhtSend("clear")
		
		return layout


##############################################################################
#                                                                            #
#       Scheduler Implementation                                             #
#                                                                            #
##############################################################################

def startScheduler():
	log( LOG_LEVEL_INFO, CHILD_DEVICE_SCHEDULER, MSG_SUBTYPE_TEXT, "Started" )
	while True:
		if holdControl.state == "normal":
			with scheduleLock:
				log( LOG_LEVEL_DEBUG, CHILD_DEVICE_SCHEDULER, MSG_SUBTYPE_TEXT, "Running pending" )
				schedule.run_pending()

		time.sleep( 10 )


def setScheduledTemp( temp ):
	with thermostatLock:
		global setTemp,dhtEnabled
		actual.put( "state", setTemp=round(temp,1), dhtEnabled=dhtEnabled,heatControl=heatControl.state, coolControl=coolControl.state, holdControl=holdControl.state)		
		if holdControl.state == "normal":
			setTemp = round( temp, 1 )
			setLabel.text = "[b]"+str( round(setTemp,1) ) + "[/b]"
			if heatControl.state == "down":
				dhtZoneSend()
			if coolControl.state == "down":
				dhtIRSend()
			log( LOG_LEVEL_STATE, CHILD_DEVICE_SCHEDULER, MSG_SUBTYPE_TEMPERATURE, str( setTemp ) )


def getTestSchedule():
	days = [ "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday" ]
	testSched = {}
	
	for i in range( len( days ) ):
		tempList = []
		for minute in range( 60 * 24 ):
			hrs, mins = divmod( minute, 60 )
			tempList.append( [
					str( hrs ).rjust( 2, '0' ) + ":" + str( mins ).rjust( 2, '0' ),
					float( i + 1 ) / 10.0 + ( ( 19.0 if tempScale == "metric" else 68.0 ) if minute % 2 == 1 else ( 22.0 if tempScale == "metric" else 72.0 ) )
					] )

		testSched[ days[i] ] = tempList

	return testSched


def reloadSchedule():
	with scheduleLock:
		schedule.clear()

		activeSched = None

		with thermostatLock:
			thermoSched = JsonStore( "./setting/thermostat_schedule.json" )
			if holdControl != "down" :
				if coolControl.state == "down":
					activeSched = thermoSched[ "cool" ]  
					log( LOG_LEVEL_INFO, CHILD_DEVICE_SCHEDULER, MSG_SUBTYPE_CUSTOM + "/load", "cool" )
				elif heatControl.state == "down":
					if dhtSchedule == 0:					
						activeSched = thermoSched[ "heat" ]  
						log( LOG_LEVEL_INFO, CHILD_DEVICE_SCHEDULER, MSG_SUBTYPE_CUSTOM + "/load", "heat" )
					else:
						activeSched = thermoSched[ "dht" ]  
						log( LOG_LEVEL_INFO, CHILD_DEVICE_SCHEDULER, MSG_SUBTYPE_CUSTOM + "/load", "dht" )		
			if useTestSchedule: 
				activeSched = getTestSchedule()
				log( LOG_LEVEL_INFO, CHILD_DEVICE_SCHEDULER, MSG_SUBTYPE_CUSTOM + "/load", "test" )
				#print "Using Test Schedule!!!"
	
		if activeSched != None:
			for day, entries in activeSched.iteritems():
				for i, entry in enumerate( entries ):
					getattr( schedule.every(), day ).at( entry[ 0 ] ).do( setScheduledTemp, entry[ 1 ] )
					log( LOG_LEVEL_DEBUG, CHILD_DEVICE_SCHEDULER, MSG_SUBTYPE_TEXT, "Set " + day + ", at: " + entry[ 0 ] + " = " + str( entry[ 1 ] ) + scaleUnits )

coolPin
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


class WebInterface(object):

	@cherrypy.expose
	
	def index( self ):	
		log( LOG_LEVEL_INFO, CHILD_DEVICE_WEBSERVER, MSG_SUBTYPE_TEXT, "Served thermostat.html to: " + cherrypy.request.remote.ip )	
		
		
		file = open( "web/html/thermostat.html", "r" )

		html = file.read()

		file.close()

		with thermostatLock:		

			html = html.replace( "@@version@@", str( THERMOSTAT_VERSION ) )
			html = html.replace( "@@temp@@", str( setTemp ) )
			html = html.replace( "@@current@@", str( currentTemp ) )
			html = html.replace( "@@minTemp@@", str( minTemp ) )
			html = html.replace( "@@maxTemp@@", str( maxTemp ) )
			html = html.replace( "@@tempStep@@", str( tempStep ) )
			html = html.replace( "@@temp_extern@@",str( temp_vis ) )
		
			status = statusLabel.text.replace( "[b]", "<b>" ).replace( "[/b]", "</b>" ).replace("[/color]","</font>").replace("[color=ff3333]","<font color=\"red\">").replace("[i]","<i>").replace("[/i]","</i>").replace( "\n", "<br>" )
			status = status.replace( "[color=00ff00]", '<font color="red">' ).replace( "[/color]", '</font>' ) 
	
			html = html.replace( "@@status@@", status )
			html = html.replace( "@@dt@@", dateLabel.text.replace( "[b]", "<b>" ).replace( "[/b]", "</b>" ) + " - " + timeLabel.text.replace( "[b]", "<b>" ).replace( "[/b]", "</b>" ) )
			html = html.replace( "@@heatChecked@@", "checked" if heatControl.state == "down" else "no" )
			html = html.replace( "@@coolChecked@@", "checked" if coolControl.state == "down" else "no" )
			html = html.replace( "@@holdChecked@@", "checked" if holdControl.state == "down" else "no" )
			html = html.replace ("@@dhtIrsubmit@@", "style='display:none'" if dhtIr_number == 0 else "")
			html = html.replace ("@@dhtZonesubmit@@", "style='display:none'" if dhtIr_number == 0 else "")
			html = html.replace ("@@dhtsubmit@@", "style='display:none'"if dhtEnabled == 0 else "")
			

		return html


	@cherrypy.expose
	def set( self, temp, heat="off", hold="off", cool="off"):
		global setTemp, setLabel, coolControl, heatControl, holdControl

		log( LOG_LEVEL_INFO, CHILD_DEVICE_WEBSERVER, MSG_SUBTYPE_TEXT, "Set thermostat received from: " + cherrypy.request.remote.ip )	

		tempChanged = setTemp != float( temp )

		with thermostatLock:
			setTemp = float( temp )
			setLabel.text = "[b]"+str( round(setTemp,1) ) + "[/b]"

			if tempChanged:
				log( LOG_LEVEL_STATE, CHILD_DEVICE_WEBSERVER, MSG_SUBTYPE_TEMPERATURE, str( setTemp ) )

			if heat == "on":
				setControlState( heatControl, "down" )
			else:
				setControlState( heatControl, "normal" )

			if cool == "on":
				setControlState( coolControl, "down" )
			else:
				setControlState( coolControl, "normal" )

			if hold == "on":
				setControlState( holdControl, "down" )
			else:
				setControlState( holdControl, "normal" )

			dhtSend("clear")
			reloadSchedule()

		file = open( "web/html/thermostat_set.html", "r" )

		html = file.read()

		file.close()
		
		with thermostatLock:
			html = html.replace( "@@version@@", str( THERMOSTAT_VERSION ) )
			html = html.replace( "@@dt@@", dateLabel.text.replace( "[b]", "<b>" ).replace( "[/b]", "</b>" ) + ", " + timeLabel.text.replace( "[b]", "<b>" ).replace( "[/b]", "</b>" ) )
			html = html.replace( "@@temp@@", ( '<font color="red"><b>' if tempChanged else "" ) + str( setTemp ) + ( '</b></font>' if tempChanged else "" ) )
			html = html.replace( "@@heat@@", ( '<font color="red"><b>' if heat == "on" else "" ) + heat + ( '</b></font>' if heat == "on" else "" ) )
			html = html.replace( "@@cool@@", ( '<font color="red"><b>' if cool == "on" else "" ) + cool + ( '</b></font>' if heat == "on" else "" ) )
			html = html.replace( "@@hold@@", ( '<font color="red"><b>' if hold == "on" else "" ) + hold + ( '</b></font>' if hold == "on" else "" ) )

		return html


	@cherrypy.expose
	def schedule( self ):	
		log( LOG_LEVEL_INFO, CHILD_DEVICE_WEBSERVER, MSG_SUBTYPE_TEXT, "Served thermostat_schedule.html to: " + cherrypy.request.remote.ip )			
		file = open( "web/html/thermostat_schedule.html", "r" )

		html = file.read()

		file.close()
		
		with thermostatLock:
			html = html.replace( "@@version@@", str( THERMOSTAT_VERSION ) )
			html = html.replace( "@@minTemp@@", str( minTemp ) )
			html = html.replace( "@@maxTemp@@", str( maxTemp ) )
			html = html.replace( "@@tempStep@@", str( tempStep ) )
		
			html = html.replace( "@@dt@@", dateLabel.text.replace( "[b]", "<b>" ).replace( "[/b]", "</b>" ) + ", " + timeLabel.text.replace( "[b]", "<b>" ).replace( "[/b]", "</b>" ) )
	
		return html

	@cherrypy.expose
	@cherrypy.tools.json_in()
	
	def save( self ):
		log( LOG_LEVEL_STATE, CHILD_DEVICE_WEBSERVER, MSG_SUBTYPE_TEXT, "Set schedule received from: " + cherrypy.request.remote.ip )	
		schedule = cherrypy.request.json

		with scheduleLock:
			file = open( "./setting/thermostat_schedule.json", "w" )

			file.write( json.dumps( schedule, indent = 4 ) )
		
			file.close()

		reloadSchedule()

		file = open( "web/html/thermostat_saved.html", "r" )

		html = file.read()

		file.close()
		
		with thermostatLock:
			html = html.replace( "@@version@@", str( THERMOSTAT_VERSION ) )
			html = html.replace( "@@dt@@", dateLabel.text.replace( "[b]", "<b>" ).replace( "[/b]", "</b>" ) + ", " + timeLabel.text.replace( "[b]", "<b>" ).replace( "[/b]", "</b>" ) )
		
		return html
		
	@cherrypy.expose
	def graph( self ):	
		log( LOG_LEVEL_INFO, CHILD_DEVICE_WEBSERVER, MSG_SUBTYPE_TEXT, "graph.html to: " + cherrypy.request.remote.ip )			
		file = open( "web/html/graph.html", "r" )

		html = file.read()

		file.close()
		
		return html
		
		
	@cherrypy.expose
	def zonedht( self , ipdht = ""):	
		log( LOG_LEVEL_INFO, CHILD_DEVICE_WEBSERVER, MSG_SUBTYPE_TEXT, "zone.html to: " + cherrypy.request.remote.ip )			
		print "ip DHT: ", ipdht
		file = open( "web/html/zone.html", "r" )

		html = file.read()

		file.close()
		with thermostatLock:	
			
			html = html.replace( "@@version@@", str( THERMOSTAT_VERSION ) )
			html = html.replace( "@@dt@@", dateLabel.text.replace( "[b]", "<b>" ).replace( "[/b]", "</b>" ) + ", " + timeLabel.text.replace( "[b]", "<b>" ).replace( "[/b]", "</b>" ) )
			status = statusLabel.text.replace( "[b]", "<b>" ).replace( "[/b]", "</b>" ).replace("[/color]","</font>").replace("[color=ff3333]","<font color=\"red\">").replace("[i]","<i>").replace("[/i]","</i>").replace( "\n", "<br>" )
			status = status.replace( "[color=00ff00]", '<font color="red">' ).replace( "[/color]", '</font>' ) 
	
			html = html.replace( "@@status@@", status )
			for c in range (0 , 9):
				if(c < dhtZone_number):
					zone = dhtZoneLabel[c,0].text.replace( "[b]", "<b>" ).replace( "[/b]", "</b>" ).replace("[/color]","</font>").replace("[color=ff3333]","<font color=\"red\">").replace("[i]","<i>").replace("[/i]","</i>").replace( "\n", "<br>" )
					zone = zone.replace( "[color=00ff00]", '<font color="red">' ).replace( "[/color]", '</font>' ) 
					zone_name = "@@zone"+str(c)+"@@"
					html = html.replace( zone_name , zone )
				else:
					zone_name = "@@zone_name"+str(c)+"@@"
					zone = "@@zone"+str(c)+"@@"
					html = html.replace( zone_name , "style=\"display:none\"" )
					html = html.replace( zone , "" )
		
		return html
	
	@cherrypy.expose
	def irdht( self , ipdht = ""):	
		log( LOG_LEVEL_INFO, CHILD_DEVICE_WEBSERVER, MSG_SUBTYPE_TEXT, "ir.html to: " + cherrypy.request.remote.ip )			
		file = open( "web/html/ir.html", "r" )

		html = file.read()

		file.close()
		with thermostatLock:	
			
			html = html.replace( "@@version@@", str( THERMOSTAT_VERSION ) )
			html = html.replace( "@@dt@@", dateLabel.text.replace( "[b]", "<b>" ).replace( "[/b]", "</b>" ) + ", " + timeLabel.text.replace( "[b]", "<b>" ).replace( "[/b]", "</b>" ) )
			status = statusLabel.text.replace( "[b]", "<b>" ).replace( "[/b]", "</b>" ).replace("[/color]","</font>").replace("[color=ff3333]","<font color=\"red\">").replace("[i]","<i>").replace("[/i]","</i>").replace( "\n", "<br>" )
			status = status.replace( "[color=00ff00]", '<font color="red">' ).replace( "[/color]", '</font>' ) 
	
			html = html.replace( "@@status@@", status )
			for c in range (0 , 9):
				if(c < dhtIr_number):
					zone = dhtIRLabel[c,0].text.replace( "[b]", "<b>" ).replace( "[/b]", "</b>" ).replace("[/color]","</font>").replace("[color=ff3333]","<font color=\"red\">").replace("[i]","<i>").replace("[/i]","</i>").replace( "\n", "<br>" )
					zone = zone.replace( "[color=00ff00]", '<font color="red">' ).replace( "[/color]", '</font>' ) 
					zone_name = "@@zone_name"+str(c)+"@@"
					zone_name1 = "@@zone"+str(c)+"@@"
					html = html.replace( zone_name , "" )
					html = html.replace( zone_name1 , zone )
					
				else:
					zone_name = "@@zone_name"+str(c)+"@@"
					zone = "@@zone"+str(c)+"@@"
					html = html.replace( zone_name , "style=\"display:none\"" )
					html = html.replace( zone , "" )
		
		return html	
		
	@cherrypy.expose
	def redirect(self, ipdht = ""):
		global dhtweb
		global send_ip
		if (int(ipdht)== 99):
			send_ip = dhtweb
		else:
			if ( int(ipdht) >= 10):
				send_ip = dhtIR[int(ipdht)-10,1]
			else:	
				send_ip = dhtZone[int(ipdht),1]
		
		f = urllib2.urlopen(send_ip+"/",None,5)

		return f

	@cherrypy.expose
	def grafico(self):
		f = urllib2.urlopen(send_ip+"/grafico",None,5)

		return f

	@cherrypy.expose
	
	def tabella(self):
		f = urllib2.urlopen(send_ip+"/tabella",None,5)

		return f
		
	@cherrypy.expose	
	def irDecoder(self):
		f = urllib2.urlopen(send_ip+"/irDecoder",None,5)

		return f
		
	@cherrypy.expose
	def irSender(self):
		f = urllib2.urlopen(send_ip+"/irSender",None,5)

		return f
	
	@cherrypy.expose
	def zone(self):
		f = urllib2.urlopen(send_ip+"/zone",None,5)

		return f

def startWebServer():	
	host = "discover" if not( settings.exists( "web" ) ) else settings.get( "web" )[ "host" ]
	#cherrypy.server.socket_host = host if host != "discover" else get_ip_address()	# use machine IP address if host = "discover"
	cherrypy.server.socket_port = 80 if not( settings.exists( "web" ) ) else settings.get( "web" )[ "port" ]

	log( LOG_LEVEL_STATE, CHILD_DEVICE_WEBSERVER, MSG_SUBTYPE_TEXT, "Starting on " + cherrypy.server.socket_host + ":" + str( cherrypy.server.socket_port ) )

	conf = {
		'/': {
			'tools.staticdir.root': os.path.abspath( os.getcwd() ),
			'tools.staticfile.root': os.path.abspath( os.getcwd() )
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
		{ 'log.screen': debug,
		  'log.access_file': "",
		  'log.error_file': "",
		  'server.thread_pool' : 10  
		}
	)

	cherrypy.quickstart ( WebInterface(), '/', conf )	


##############################################################################
#                                                                            #
#       Main                                                                 #
#                                                                            #
##############################################################################

def main():
	# Start Web Server
	webThread = threading.Thread( target=startWebServer )
	webThread.daemon = True
	webThread.start()

	# Start Scheduler
	reloadSchedule()
	schedThread = threading.Thread( target=startScheduler )
	schedThread.daemon = True
	schedThread.start()

	# Start Thermostat UI/App
	ThermostatApp().run()


if __name__ == '__main__':
	try:
		main()
	finally:
		log( LOG_LEVEL_STATE, CHILD_DEVICE_NODE, MSG_SUBTYPE_CUSTOM + "/shutdown", "Thermostat Shutting Down..." )
		GPIO.cleanup()

		if logFile is not None:
			logFile.flush()
			os.fsync( logFile.fileno() )
			logFile.close()


