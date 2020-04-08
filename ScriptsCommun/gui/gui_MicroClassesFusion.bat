@echo off
echo from MicroClassesFusion import main > tmp.py
echo main(True) >> tmp.py
python tmp.py
rm tmp.py
