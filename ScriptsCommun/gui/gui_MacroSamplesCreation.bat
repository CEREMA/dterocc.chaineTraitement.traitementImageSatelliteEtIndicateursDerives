@echo off
echo from MacroSamplesCreation import main > tmp.py
echo main(True) >> tmp.py
python tmp.py
rm tmp.py
