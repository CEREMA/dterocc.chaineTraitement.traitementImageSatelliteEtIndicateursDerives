#!/bin/bash

#This script will run the NeuralNetworkSegmentation.py file

#To use tensorboard : tensorboard --logdir=/mnt/RAM_disk/resunet_History_classified/classified_mono_/ --host=172.22.130.64 --port=6006


###########################################################################################################################################
#                                                                                                                                         #
# REQUIRED ARGUMENTS                                                                                                                      #
#    a noter qu'il existe aussi :                                                                                                         #
#at --augment_training , action ='store_true', default =False                                                                             #
#ugc --use graphic_card ,action = 'store_true', default = False                                                                           #
#sav --save_results_inter , action ='store_true', default=False                                                                           #
#now --overwrite, action='store_false', default=True                                                                                      #
###########################################################################################################################################

# PATHS
input_raster_path="/mnt/RAM_disk/stacked_treated_normalized_hiver.tif"
groundtruth_path=""
output_raster_path="/mnt/RAM_disk/classified.tif"

model_input="Model/classified.keras"
model_output=""

vector_train="/mnt/RAM_disk/trainset1/train/train.shp"
vector_valid="/mnt/RAM_disk/trainset1/valid/valid.shp"
vector_test="/mnt/RAM_disk/trainset1/test/test.shp"

grid_path="/mnt/RAM_disk/trainset1/Grid/stacked_treated_normalized_grid_temp.shp"

evaluation_path="/mnt/RAM_disk/bd_topo_TM_2024_route_bati.tif"

# PARAMETERS
number_class=2
neural_network_mode="resunet"

size_grid=256
debord=3

batch=16
n_conv_filter=16
kernel_size=3
dropout_rate=0.2
l2_reg=7.6e-6
alpha_loss="0.1 0.7 0.2"

number_epoch=200
es_monitor="val_loss"
es_patience=10
es_min_delta=8e-5
rl_monitor="val_loss"
rl_factor=0.1
rl_patience=4
rl_min_lr=1e-6

id_graphic_card=0
percent_no_data=10


###########################################################################################################################################
#                                                                                                                                         #
# EXECUTION                                                                                                                               #
#                                                                                                                                         #
###########################################################################################################################################

python3 -m NeuralNetworkSegmentation \
  -i "$input_raster_path" \
  -nc "$number_class" \
  -nm "$neural_network_mode" \
  -gp "$grid_path" \
  -ep "$evaluation_path" \
  -gt "$groundtruth_path" \
  -vtr "$vector_train" \
  -vv "$vector_valid" \
  -vte "$vector_test" \
  -o "$output_raster_path" \
  -mi "$model_input" \
  -mo "$model_output" \
  -sg "$size_grid" \
  -deb "$debord" \
  -igpu "$id_graphic_card" \
  -pnd "$percent_no_data" \
  -nn.b "$batch" \
  -nn.ncf "$n_conv_filter" \
  -nn.ks "$kernel_size" \
  -nn.dp "$dropout_rate" \
  -nn.l2 "$l2_reg" \
  -nn.al $alpha_loss \
  -nn.ne "$number_epoch" \
  -nn.esm "$es_monitor" \
  -nn.esp "$es_patience" \
  -nn.esmd "$es_min_delta" \
  -nn.rlrm "$rl_monitor" \
  -nn.rlrf "$rl_factor" \
  -nn.rlrp "$rl_patience" \
  -nn.rlrmlr "$rl_min_lr" \
  -rand 42 \
  -ram 0 \
  -ndv -1 \
  -epsg 2154 \
  -raf "GTiff" \
  -vef "ESRI Shapefile" \
  -rae ".tif" \
  -vee ".shp" \
  -log "/mnt/RAM_disk/log" \
  -now \
  -ugc \
  -sav \
