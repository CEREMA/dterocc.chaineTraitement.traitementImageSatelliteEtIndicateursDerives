@echo off
echo from QualityClassificationRandomPoints import main > tmp.py
echo main(True) >> tmp.py
python tmp.py
rm tmp.py
