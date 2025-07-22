# Instructions to build and compile the project

---
pip install openmesh

## install prerequisities
```sh
sudo apt update
sudo apt install cmake git build-essential
sudo apt install -y cmake g++ wget unzip
```

## install dependencies: Boost & GMP & MPFR

```sh
sudo apt install libboost-all-dev libgmp-dev libmpfr-dev
sudo apt install libgeotiff-dev
sudo apt install libtiff-dev
sudo apt install python3-tifffile
```


##  OpenMesh ## v11.0.0

Download source package **version 11.0.0**: [ici](https://www.graphics.rwth-aachen.de/software/openmesh/download/)
```sh
cd <path_to_project_folder> # where OpenMesh .tar.gz is stored
tar -xvf OpenMesh11.0.0.tar.gz # extract
# build and compile lib
cd OpenMesh-11.0.0/
mkdir build
cd build
cmake .. -DBUILD_APPS=OFF
make
sudo make install
```


## OpenCV ## v4.10.0
```sh
# Download and unpack sources
cd <path_to_project_folder>
wget -O opencv.zip https://github.com/opencv/opencv/archive/4.10.0.zip
unzip opencv.zip
mv opencv-4.10.0 OpenCV
cd OpenCV
# Create build directory, configure and build
mkdir -p build && cd build
cmake ..
cmake --build .
sudo make install
```


## CGAL ## v6.0.1

Download and unpack sources package [ici](https://github.com/CGAL/cgal/releases/tag/v5.6) (bottom of page)

```sh
# unpack sources
cd <path_to_project_folder>
unzip CGAL-6.0.1-library.zip
# Create build directory, configure and build
cd CGAL-6.0.1/
mkdir build && cd build
cmake -DCMAKE_BUILD_TYPE=Release ..
sudo make install
```

## GLOG ## v0.7.1

```sh
cd <path_to_project_folder>
git clone https://github.com/google/glog.git
cd glog
git checkout v0.7.1
mkdir build
cd build
cmake ..
make -j 16
sudo make install
```

## CCM vxxx

```sh
cd <path_to_project_folder>
tar -xvf CCM.tar.xz
cd CCM
mkdir build && cd build
cmake ..
make -j16
sudo make install
# Update the Dynamic Linker Cache
sudo ldconfig
# the script is executable on the project repository and globally on system.
# use python command "os.subprocess.run" (while specifying the path to project) to run the script from a different repository if CCM command dont work globally on a different repository
```

## Test installation
```sh
# 1_ test of CCM command on repository
cd <path_to_project_folder>
#command to execute CCM segmentation
CCM <path_to_project_folder>/CCM/input/lena.jpg 40 3.0 0.7 4.0 45 0.1 0.3 1024 <path_to_project_folder>/CCM/output/

# 2_ test of CCM command outside of project repository
cd ~
CCM <path_to_project_folder>/CCM/input/lena.jpg 40 3.0 0.7 4.0 45 0.1 0.3 1024 <path_to_project_folder>/CCM/output/
```
