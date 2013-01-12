#!/usr/bin/python

from time import sleep
from datetime import datetime, timedelta
from Adafruit_I2C import Adafruit_I2C
from Adafruit_MCP230xx import Adafruit_MCP230XX
from Adafruit_CharLCDPlate import Adafruit_CharLCDPlate
from apiclient.discovery import build
from oauth2client.file import Storage
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.tools import run
from ConfigParser import SafeConfigParser
import gflags
import httplib2
import time
import subprocess
import smbus
import pygame
import pickle
import os
import sys
import random
import threading

   
# *************************************************************************************************************************    
# initialize the LCD plate
# use busnum = 0 for raspi version 1 (256MB) and busnum = 1 for version 2
# *************************************************************************************************************************  
lcd = Adafruit_CharLCDPlate(busnum = 1)

# *************************************************************************************************************************    
# ********    global variables & constants   
# *************************************************************************************************************************    

# global variables
gcal_client_id = ""
gcal_client_secret = ""
gcal_developerKey = ""
gcal_storage = ""
data_file = ""
mp3_path = ""

service = -1

SHOW_CURRENT_TIME = 0
SHOW_ALARM_TIMES = 1
SHOW_ALARM_RUNNING = 2
SHOW_NOTHING = 3

pygame_status = False
ipaddr = "0.0.0.0"
    
menu_state = SHOW_CURRENT_TIME
alarm_times = []
alarm_index = 0
current_alarm = " --- "

hours = datetime.now().hour - 1
minutes = datetime.now().minute - 1
timestamp = time.time()

# *************************************************************************************************************************    
# ********    threaded class for loading google calendar data   
# *************************************************************************************************************************  

class GoogleCalendarData(threading.Thread):
    def __init__(self, service):
        self.service = service
        threading.Thread.__init__ (self)
      
    def run(self):
        self.alarm_times = ""
        date = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000Z")
        endDate = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        
        calendar = self.service.calendars().get(calendarId='primary').execute()
        events = self.service.events().list(
                calendarId=calendar['id'], 
                singleEvents=True, 
                #maxResults=20, 
                orderBy="startTime", 
                timeMin=date,
                timeMax=endDate,
                q="ALARM"
            ).execute()

        new_alarm_times = []
        while True:
            for event in events.get('items', []):
                # read in / parse time format
                timedata = time.strptime(event['start']['dateTime'].split("+")[0], "%Y-%m-%dT%H:%M:%S")
                # convert to unix epoch
                timestamp = time.mktime(timedata)
                # append new alarm date
                new_alarm_times.append( { "date": timestamp, "status": True } )
                
            page_token = events.get('nextPageToken')
            if page_token:
                    events = self.service.events().list(
                    calendarId=calendar['id'], 
                    singleEvents=True, 
                    orderBy="startTime", 
                    timeMin=date,
                    timeMax=endDate,
                    q="ALARM",
                    pageToken=page_token
                ).execute()
            else:
                break
        self.alarm_times = new_alarm_times

    def stop(self):
        try:
            self._Thread__stop()
        except:
            print(str(self.getName()) + " did not stop!")

# *************************************************************************************************************************    
# ********    helpers   
# *************************************************************************************************************************  

def _read_config_file():
    global gcal_client_id, gcal_client_secret, gcal_developerKey, gcal_storage, data_file, mp3_path
    parser = SafeConfigParser()
    parser.read('alarm_clock.cfg')

    gcal_client_id = parser.get('google_calendar', 'client_id')
    gcal_client_secret = parser.get('google_calendar', 'client_secret')
    gcal_developerKey = parser.get('google_calendar', 'developerKey')
    gcal_storage = parser.get('google_calendar', 'storage')
    data_file = parser.get('alarm_clock', 'data_file')
    mp3_path = parser.get('alarm_clock', 'mp3_path')
    
def _init_google_calendar():
    global service
    FLAGS = gflags.FLAGS
    FLOW = OAuth2WebServerFlow(
        client_id=gcal_client_id, client_secret=gcal_client_secret,
        scope='https://www.googleapis.com/auth/calendar.readonly',
        user_agent='alarm_clock.py/1.0.0')

    FLAGS.auth_local_webserver = False

    storage = Storage(gcal_storage)
    credentials = storage.get()
    if (credentials is None) or (credentials.invalid == True):
        credentials = run(FLOW, storage)

    http = httplib2.Http()
    http = credentials.authorize(http)
    service = build(serviceName='calendar', version='v3', http=http, developerKey=gcal_developerKey)

def _run_cmd_and_return(cmd):
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    output = p.communicate()[0]
    return output
    
def _run_cmd_in_background(cmd):
    subprocess.Popen(cmd, shell=True)
    
def _shutdown_pi():
    #subprocess.call(["shutdown", "-h", "now"])
    #subprocess.call("shutdown -h now", shell=True)
    os.system("sudo shutdown -h now")
    sys.exit(0)

def _play_mp3(mp3):
    global pygame_status
    if (not pygame_status):
        pygame.init()
        pygame.mixer.init()
        pygame_status = True
        
    if (pygame.mixer.music.get_busy()):
        pygame.mixer.music.stop() 
    pygame.mixer.music.load(mp3)
    pygame.mixer.music.play(-1)
    
def _stop_mp3():
    global pygame_status
    # unload pygame stuff to save cpu time
    if (pygame_status):
        if (pygame.mixer.music.get_busy()):
            pygame.mixer.music.stop()
        pygame.mixer.quit()
        pygame.quit()
        pygame_status = False
    
def _check_alarm_times():
    global current_alarm
    current_timestamp = time.time()
    
    for index, alarm in enumerate(alarm_times):
        date = alarm["date"]
        status = alarm["status"]
        # only if alarm is enabled
        if (status):
            # only during a 5 minute window
            if (current_timestamp >= date) and (current_timestamp < date + 300):
                current_alarm = datetime.fromtimestamp(date).strftime('%b %d --- %H:%M')
                del alarm_times[index]
                return True
    return False
    
def _load_data():
    global hours, alarm_times
    alarm_times = pickle.load( open( data_file, "rb" ) )
    hours = datetime.now().hour
    
    _merge_alarm_data(_get_gcal_data())
    _save_data()
    
def _save_data():
    pickle.dump( alarm_times, open( data_file, "wb" ) )

def _get_gcal_data():
    gcal = GoogleCalendarData(service)
    gcal.start()

    # timeout of 60 seconds
    gcal.join(60)

    # check if there was a timeout and the thread is still alive
    new_alarm_times = alarm_times 
    if gcal.isAlive():
        gcal.stop()
    else:
        new_alarm_times = gcal.alarm_times 
    return new_alarm_times
    
def _merge_alarm_data(new_alarm_times):
    global alarm_times

    for alarm in alarm_times:
        # check if status == False, if so then check if alarm date exists inside new_alarm_times too, 
        # and update its status in there in order to not overwrite the status=False state from the current alarm data
        if (not alarm["status"]):
            for index, new_alarm in enumerate(new_alarm_times):
                if (new_alarm["date"] == alarm["date"]):
                    new_alarm_times[index]["status"] = False
    alarm_times = new_alarm_times
    
def _set_alarm_status(index, status):
    global alarm_times
    alarm_times[index]["status"] = status
    _save_data()

def _add_mp3_path(file):
    return mp3_path + file
    
def _get_mp3_files():
    files = os.listdir(mp3_path)
    return map(_add_mp3_path, files)
    
def _get_random_mp3_file():
    return random.choice(_get_mp3_files())

def _get_ip():
    cmd = "ip addr show eth0 | grep inet | awk '{print $2}' | cut -d/ -f1"
    ip = _run_cmd_and_return(cmd)
    return ip
    
# *************************************************************************************************************************    
# ********    interact with LCD   
# *************************************************************************************************************************    
    
def init_display():
    lcd.clear()
    lcd.backlight(lcd.YELLOW)
    lcd.message("JamesClonk's\nAlarm Clock!")
    sleep(2)
    lcd.backlight(lcd.VIOLET)
    
def show_time():
    global minutes
    lcd.clear()
    lcd.message(datetime.now().strftime('%b %d --- %H:%M\n'))
    lcd.message('IP %s' % ( ipaddr ) )
    minutes = datetime.now().minute
    
def show_alarm():
    global timestamp
    
    alarm = alarm_times[alarm_index]
    date = datetime.fromtimestamp(alarm["date"]).strftime('%b %d --- %H:%M')
    status = "is enabled" if alarm["status"] else "is disabled"
    
    lcd.clear()
    lcd.message(date + "\n" + status)
    # activity reset
    timestamp = time.time()
    
def start_alarm():
    switch_to_menu_alarm_running()
    _play_mp3(_get_random_mp3_file())
    lcd.message("ALARM !!!\n" + current_alarm)
    
def stop_alarm():
    _stop_mp3()
    
def load_data():
    # only display loading message in current time menu, as to not disturb the "nothing" menu
    if (menu_state == SHOW_CURRENT_TIME):
        lcd.clear()
        lcd.backlight(lcd.BLUE)
        lcd.message("loading data..")
        _load_data()
        switch_to_menu_time_display()
    else:
        _load_data()

def shutdown_pi():
    lcd.clear()
    lcd.backlight(lcd.RED)
    lcd.message("shutting down..")
    sleep(1)
    _shutdown_pi()
    
def time_menu_up():
    # force load of alarm data
    load_data()
    
def time_menu_down():
    global current_alarm
    current_alarm = "   ..forced"
    # force start of alarm
    start_alarm()
    sleep(2)
    
def time_menu_left():
    _run_cmd_in_background("sudo /etc/init.d/rain.sh stop")
    lcd.clear()
    lcd.message("stop rain.sh\nservice")
    sleep(2)
    show_time()
    
def time_menu_right():
    _run_cmd_in_background("sudo /etc/init.d/rain.sh start")
    lcd.clear()
    lcd.message("start rain.sh\nservice")
    sleep(2)
    show_time()
 
def alarm_menu_up():
    global alarm_index, timestamp
    alarm_index = alarm_index - 1
    if (alarm_index < 0):
        alarm_index = len(alarm_times) - 1
    show_alarm()
    
def alarm_menu_down():
    global alarm_index, timestamp
    alarm_index = alarm_index + 1
    if (alarm_index >= len(alarm_times)):
        alarm_index = 0
    show_alarm()
    
def alarm_menu_left():
    lcd.clear()
    lcd.message("enabled!")
    _set_alarm_status(alarm_index,True)
    sleep(2)
    show_alarm()
    
def alarm_menu_right():
    lcd.clear()
    lcd.message("disabled!")
    _set_alarm_status(alarm_index,False)
    sleep(2)
    show_alarm()

def switch_to_menu_time_display():
    global menu_state, minutes
    lcd.clear()
    lcd.backlight(lcd.VIOLET)
    menu_state = SHOW_CURRENT_TIME
    minutes = datetime.now().minute - 1
    
def switch_to_menu_alarm_times():
    global menu_state, alarm_index
    lcd.clear()
    lcd.backlight(lcd.RED)
    menu_state = SHOW_ALARM_TIMES
    alarm_index = 0
    show_alarm()
    
def switch_to_menu_alarm_running():
    global menu_state, timestamp
    lcd.clear()
    lcd.backlight(lcd.YELLOW)
    menu_state = SHOW_ALARM_RUNNING
    timestamp = time.time()
    
def switch_to_menu_nothing():
    global menu_state
    lcd.clear()
    lcd.backlight(lcd.OFF)
    menu_state = SHOW_NOTHING

# *************************************************************************************************************************    
# ********    menus   
# *************************************************************************************************************************    
    
def menu_time_display():
    # reload alarm data every hour
    if (datetime.now().hour != hours):
        load_data()
        
    # write current time to LCD every minute
    elif (datetime.now().minute != minutes):
        show_time()
        
    elif (lcd.buttonPressed(lcd.SELECT)):
        switch_to_menu_alarm_times()
        
    elif (lcd.buttonPressed(lcd.UP)):
        time_menu_up()

    elif (lcd.buttonPressed(lcd.DOWN)):
        time_menu_down()
        
    elif (lcd.buttonPressed(lcd.LEFT)):
        time_menu_left()
        
    elif (lcd.buttonPressed(lcd.RIGHT)):
        time_menu_right()

def menu_alarm_times():
    # switch back to time display after 15 seconds of "inactivity"
    if (time.time() >= timestamp + 15):
        switch_to_menu_time_display()
    
    elif (lcd.buttonPressed(lcd.SELECT)):
        switch_to_menu_nothing()
    
    elif (lcd.buttonPressed(lcd.UP)):
        alarm_menu_up()

    elif (lcd.buttonPressed(lcd.DOWN)):
        alarm_menu_down()
        
    elif (lcd.buttonPressed(lcd.LEFT)):
        alarm_menu_left()
        
    elif (lcd.buttonPressed(lcd.RIGHT)):
        alarm_menu_right()
        
def menu_alarm_running():
    # switch back to time display after 300 seconds of alarm, or if select is pressed
    if (time.time() >= timestamp + 300) or (lcd.buttonPressed(lcd.SELECT)):
        stop_alarm()
        switch_to_menu_time_display()
        
    elif (lcd.buttonPressed(lcd.LEFT)) and (lcd.buttonPressed(lcd.RIGHT)):
        shutdown_pi()
        
def menu_nothing():
    if (datetime.now().hour != hours):
        load_data()
        
    elif (lcd.buttonPressed(lcd.SELECT)):
        switch_to_menu_time_display()
        
    elif (lcd.buttonPressed(lcd.LEFT)) and (lcd.buttonPressed(lcd.RIGHT)):
        shutdown_pi()

# *************************************************************************************************************************    
# ********    main   
# *************************************************************************************************************************    
            
def main():
    global ipaddr
    ipaddr = _get_ip()
    
    _read_config_file()
    _init_google_calendar()
    
    init_display()

    while True:
        if (menu_state == SHOW_ALARM_RUNNING):
            menu_alarm_running() 
        elif (_check_alarm_times()):
            start_alarm()
        elif (menu_state == SHOW_CURRENT_TIME):
            menu_time_display()
        elif (menu_state == SHOW_ALARM_TIMES):
            menu_alarm_times()
        elif (menu_state == SHOW_NOTHING):
            menu_nothing()

        sleep(0.1)

main()
