#!/bin/bash

cd /home/pi/<my_directory>

running=`ps -ef | grep 'python alarm_clock.py' | grep -v 'grep' | wc -l`

if [ "$running" -eq "0" ]
then
    python alarm_clock.py &
fi
