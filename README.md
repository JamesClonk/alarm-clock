alarm_clock.py
===========

An alarm clock that syncs with Google Calendar, for the Adafruit 16x2 LCD+Keypad Kit for use with a Raspberry Pi, written in Python.

#### What is this?
It is an alarm clock application for the
[Adafruit RGB Negative 16x2 LCD+Keypad Kit for Raspberry Pi](http://adafruit.com/products/1110) that sits on top of a [Raspberry Pi](http://www.raspberrypi.org) computer.
The LCD "shield" provides 5 push buttons that can be used to interact with the Raspberry Pi, to switch to different menus, enable / disable alarm times, etc..

#### Features
The alarm dates are read from Google Calendar, any event with the text **ALARM** will be fetched and its alarm date stored locally. 
You can enable or disable certain alarm dates you do not wish to use. 
They will only be disabled locally. 

The application is only using *Read-Only* access to Google Calendar, so nothing gets updated back.

#### Requirements

It needs the following libraries installed on your Raspberry Pi:

* The kernel modules *i2c-bcm2708* and *i2c-dev*. 
* python-smbus
* [Google Calendar API v3 for Python](https://developers.google.com/api-client-library/python/start/installation)
* [Adafruit_CharLCDPlate.py](https://github.com/adafruit/Adafruit-Raspberry-Pi-Python-Code/blob/master/Adafruit_CharLCDPlate/Adafruit_CharLCDPlate.py)
* [Adafruit_I2C.py](https://github.com/adafruit/Adafruit-Raspberry-Pi-Python-Code/blob/master/Adafruit_I2C/Adafruit_I2C.py)
* [Adafruit_MCP230xx.py](https://github.com/adafruit/Adafruit-Raspberry-Pi-Python-Code/blob/master/Adafruit_MCP230xx/Adafruit_MCP230xx.py)

Please read this here for installation instructions: [Adafruit Learning System - 16x2 LCD Usage](http://learn.adafruit.com/adafruit-16x2-character-lcd-plus-keypad-for-raspberry-pi/usage)

#### Howto use
* Copy all provided files into a new directory.
* Edit the configfile *alarm_clock.cfg*. The variables client\_id, client\_secret, developerKey are part of the Google Developer API.
Information about these values can be found here: [Google Developer Console - Help](https://developers.google.com/console/help/)
* The alarm clock can be started by running the command: 
> sudo python alarm_clock.py.

(root access is needed for GPIO usage on the Raspberry Pi)

* The provided shellscript *monitor_alarm_clock.sh* can be setup to run every few minutes / hours from crontab to make sure the script is still running. (root crontab)

#### Menu Structure

The main menu shows the current date, time and IP address of your Raspberry Pi.

* Pressing UP force reloads the data from Google Calendar.
* Pressing DOWN force starts a test alarm.
* Pressing SELECT switches to the alarm date menu.

The alarm date menu shows all currently loaded alarm dates and times.

* Pressing UP switches to the previous alarm date.
* Pressing DOWN switches to the next alarm date.
* Pressing LEFT enables the currently shown alarm date (an alarm date is enabled by default when first fetched from Google Calendar).
* Pressing RIGHT disables the currently shown alarm date.
* Pressing SELECT switches to the "nothing" menu.

The "nothing" menu (called so because it does show nothing) displays nothing, and turns of the LCD backlight.
This is useful for when you have the alarm clock in your bedroom and want to get some sleep. Otherwise the LCD backlight from the other 2 menu modes would keep you awake. ;)

* Pressing LEFT + RIGHT shuts down the Raspberry Pi (via "shutdown -h now").
* Pressing SELECT switches back to the main menu.

#### Todo

Clean up the code.
Seriously! It is a mess.
My excuse? These are my first few lines of Python, ever. ;)

#### License

Written by Fabio Berchtold. 
BSD license, all text above must be included in any redistribution.
