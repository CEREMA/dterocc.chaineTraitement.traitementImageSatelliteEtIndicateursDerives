@echo off
echo from ImagesAssembly import main > tmp.py
echo main(True) >> tmp.py
python tmp.py
rm tmp.py
