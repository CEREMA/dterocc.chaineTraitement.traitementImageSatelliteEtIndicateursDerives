@echo off
echo from RasterAssembly import main > tmp.py
echo main(True) >> tmp.py
python tmp.py
rm tmp.py
