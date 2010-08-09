@echo off
cls

charts.py --profile=cloud
charts.py --profile=dcsm

make_report.py --profile=cloud
make_report.py --profile=dcsm

