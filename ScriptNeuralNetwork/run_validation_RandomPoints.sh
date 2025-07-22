#!/bin/bash

#This script will run the QualityClassificationRandomPoints.py file

#To run it from everywhere do : export PATH=$PATH:/home/scgsi/Documents/ChaineTraitementPCI/ScriptsNeuralNetwork

###########################################################################################################################################
#                                                                                                                                         #
# REQUIRED ARGUMENTS                                                                                                                      #
#                                                                                                                                         #
###########################################################################################################################################
input_image="/mnt/RAM_disk/bd_topo_TM_2024_route_bati.tif"
roi_vector="/mnt/RAM_disk/trainset1/test/test.shp"
output_vector="/mnt/RAM_disk/Evaluation/RandomPoints.shp"
vector_sample_input""
nb_points=150
log_path="/mnt/RAM_disk/Evaluation/fichierTestLog.txt"
class_near_fifty=95
debug=5

python3 -m QualityClassificationRandomPoints \
  -i "$input_image" \
  -v "$roi_vector" \
  -o "$output_vector" \
  -nb "$nb_points" \
  -log "$log_path" \
  -cnf "$class_near_fifty"\
  -p "$vector_sample_input" \
  -debug "$debug" \
  -now \

