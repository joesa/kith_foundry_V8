@echo off
cd /d %~dp0
copy /y storage_service_new.py storage_service.py
echo DONE
