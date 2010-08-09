@echo off

cls

if "%1" == "" goto ERROR

wget %1 -Oqueues.txt -t1

queues.py --profile=dcsm

goto END

:ERROR
echo Usage: queues PATH_TO_QUEUES_RSS

:END