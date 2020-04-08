@echo off
echo from KmeansMaskApplication import main > tmp.py
echo main(True) >> tmp.py
python tmp.py
rm tmp.py
