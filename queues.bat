@echo off

cls

if "%1" == "" goto ERROR

wget %1 -Oqueues.txt -t1 -T120

goto END

:ERROR

del queues.txt

:END
-
queues.py --profile=ras