#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerSO/DALETT/SCGSI  All rights reserved.                                                                            #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT QUI APPLIQUE UNE CLASSIFICATION PAR RESEAU DE NEURONES                                                                             #
#                                                                                                                                           #
#############################################################################################################################################
'''
Nom de l'objet : NeuralNetworkClassification.py
Description :
    Objectif : exécute une classification via réseaux de neurones sur des images découpées d'une seule image satellite en se basant sur un réseau Encodeur/Decodeur type Unet

Date de creation : 08/04/2021
----------
Histoire :
----------
Origine : le script originel provient du regroupement de fichier du stagiaire Romain TARDY, dossier "reseau_keras" crée en 2020
-----------------------------------------------------------------------------------------------------
Modifications

------------------------------------------------------

'''
##### Import propre à l'evaluation de performance #####
from __future__ import print_function
import os
import numpy as np
import random
import math
import tensorflow as tf
import keras


##### Import propre à Unet et ResUnet #####

from keras.models import *
from keras.layers import *
from keras.optimizers import *
from keras.losses import SparseCategoricalCrossentropy
from keras import backend as k_backend #WARNING
from keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau, CSVLogger
from keras.utils.vis_utils import plot_model


import glob,string,shutil,time,argparse, threading
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_log import timeLine
from Lib_operator import getExtensionApplication
from Lib_vector import simplifyVector, cutoutVectors, bufferVector, fusionVectors, filterSelectDataVector, getAttributeNameList, getNumberFeature, getGeometryType, getEmpriseFile, createEmpriseShapeReduced, createGridVector, splitVector
from Lib_raster import createVectorMask, rasterizeBinaryVector, getNodataValueImage, getGeometryImage, getProjectionImage, updateReferenceProjection, getGeometryImage, roundPixelEmpriseSize, getEmpriseImage, cutImageByVector, getPixelWidthXYImage, countPixelsOfValue, countPixelsOfValueBis
from Lib_file import removeVectorFile, removeFile
from Lib_text import appendTextFileCR

##### Import propre à Data Generator #####

from skimage import img_as_float
from tifffile import imread

##### Import propre à Prediction #####
from gdal import *
from gdalconst import *
from skimage import img_as_ubyte
from tqdm import tqdm

##### Import propre au Main #####
import sys
from datetime import date
import time

import copy

import shutil

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 3
 


###########################################################################################################################################
# STRUCTURE StructNnParameter                                                                                                             #
###########################################################################################################################################
# Structure contenant les parametres utiles au calcul du Reseau de neurones
class StructNnParameter:
    def __init__(self):

        # Hyperparameters NN
        # es : earlyStopping
        # rl : reduce_lr
        self.batch = 0
        self.number_conv_filter = 0
        self.kernel_size = 0
        self.test_in_one_block = 0
        self.validation_split = 0
        self.number_epoch = 0
        self.es_monitor = ""
        self.es_patience = 0
        self.es_min_delta = 0
        self.es_verbose = 0
        self.rl_monitor = ""
        self.rl_factor = 0
        self.rl_patience = 0
        self.rl_min_lr = 0
        self.rl_verbose = 0
        


###########################################################################################################################################
#                                                                                                                                         #
# PARTIE DATAGENERATOR (génération des données pour les mettre en entrée du réseau de neurones)                                           #
#                                                                                                                                         #
###########################################################################################################################################

class DataGenerator(keras.utils.Sequence):
    def __init__(self, batch_size, input_img_paths, target_mask_paths, augmentation, data_type):
        self.batch_size = batch_size
        self.input_img_paths = input_img_paths
        self.target_mask_paths = target_mask_paths
        self.augmentation = augmentation
        self.data_type = data_type
    ###########################################################################################################################################
    # FONCTION __len__()                                                                                                                      #
    ###########################################################################################################################################
    # ROLE:
    #    Redefinition de la fonction __len__ la taille du DataGenerator
    #
    # ENTREES DE LA FONCTION :
    #
    # SORTIES DE LA FONCTION :
    #    taille de la liste générée par DataGenerator
    #
    def __len__(self):
        return (len(self.input_img_paths) // self.batch_size) + 1

    ###########################################################################################################################################
    # FONCTION __getitem__()                                                                                                                  #
    ###########################################################################################################################################
    # ROLE:
    #    Redefinition de la fonction __getitem__ pour recupérer un lot d'images et de masques stockés à l'indice index
    #
    # ENTREES DE LA FONCTION :
    #    index (int) : indice pour récuperer le lot à l'indice souhaité
    #
    # SORTIES DE LA FONCTION :
    #    images en float32
    #    masques en uint8
    #
    def __getitem__(self, index):
        # Pour la prédiction, on a juste besoin des images
        if self.data_type == 'test':
            i = index * self.batch_size
            if i + self.batch_size > len(self.input_img_paths):
                batch_input_img_paths = self.input_img_paths[i:]
            else:
                batch_input_img_paths = self.input_img_paths[i : i + self.batch_size]
            images = []
            for j, path in enumerate(batch_input_img_paths):
                img = self.loadTiffImage(path)
                images.append(img)
            return np.asarray(images, dtype = np.float32)
        else:
        # Pour l'apprentissage, on a besoin des images et des masques
            i = index * self.batch_size
            if i + self.batch_size > len(self.input_img_paths):
                batch_input_img_paths = self.input_img_paths[i:]
                batch_target_mask_paths = self.target_mask_paths[i:]
            else:
                batch_input_img_paths = self.input_img_paths[i : i + self.batch_size]
                batch_target_mask_paths = self.target_mask_paths[i : i + self.batch_size]
            images = []
            for j, path in enumerate(batch_input_img_paths):
                img = self.loadTiffImage(path)
                images.append(img)
            masks = []
            for j, path in enumerate(batch_target_mask_paths):
                mask = self.loadTiffMask(path)
                masks.append(mask)
            if self.augmentation:
                for i in range(len(images)):
                    images[i], masks[i] = self.augmentData(images[i], masks[i])
            return np.asarray(images, dtype = np.float32), np.asarray(masks, dtype = np.uint8)

    ###########################################################################################################################################
    # FONCTION augmentData()                                                                                                                 #
    ###########################################################################################################################################
    # ROLE:
    #    Assure une augmentation des données avec rotation (90°) et retournement (vertical/horizontal) selon un nombre aléatoire.
    #
    # ENTREES DE LA FONCTION :
    #    image (array) : l'image
    #    mask  (array) : le masque
    #
    # SORTIES DE LA FONCTION :
    #    image et masque augmentés (modifiés avec rotation/retournement)
    #
    def augmentData(self, image, mask):
        if random.random() < 0.5:
            image = np.flipud(image)
            mask = np.flipud(mask)

        if random.random() < 0.5:
            image = np.fliplr(image)
            mask = np.fliplr(mask)

        if random.random() < 0.5:
            rotation = random.randint(0, 3)
            image = np.rot90(image, rotation)
            mask = np.rot90(mask, rotation)

        return image, mask

    ###########################################################################################################################################
    # FONCTION loadTiffImage()                                                                                                              #
    ###########################################################################################################################################
    # ROLE:
    #    Chargement de l'image et changement de ses dimensions et de son type pour être utilisé en entrée du reseau de neurones.
    #
    # ENTREES DE LA FONCTION :
    #    image_name (string) : chemin du fichier contenant l'image
    #
    # SORTIES DE LA FONCTION :
    #    image redimensionné et convertit en float32
    #
    def loadTiffImage(self, image_name):
        tiff_image = imread(image_name)
        float_image = img_as_float(tiff_image).astype(np.float32)

        return float_image

    ###########################################################################################################################################
    # FONCTION loadTiffMask()                                                                                                               #
    ###########################################################################################################################################
    # ROLE:
    #    Chargement du masque et changement de ses dimensions et de son type pour être utilisé en entrée du reseau de neurones.
    #
    # ENTREES DE LA FONCTION :
    #    mask_name (string) : chemin du fichier contenant le masque
    #
    # SORTIES DE LA FONCTION :
    #    masque redimensionné et convertit en uint8
    #
    def loadTiffMask(self, mask_name):
        mask = imread(mask_name)
        mask = mask[..., np.newaxis]
        
        return mask.astype(np.uint8)

###########################################################################################################################################
#                                                                                                                                         #
# PARTIE RESEAU DE NEURONE (création des differents réseaux de neurones)                                                                  #
#                                                                                                                                         #
###########################################################################################################################################

            ##########################################################################
            #                                                                        #
            #                              UNET                                      #
            #                                                                        #
            ##########################################################################



###########################################################################################################################################
# FONCTION conv2dBlock()                                                                                                               #
###########################################################################################################################################
# ROLE:
#    Création d'un bloc de convolutions comprenant 2 couches de neurones convolutif ainsi qu'une activation ReLu et une BatchNormalization.
#
# ENTREES DE LA FONCTION :
#    input_tensor (tensor) : image modifiée pour être utilisable par un réseau de neurones
#    n_filters (int) : nombre de filtres présents pour chaque couche convolutive
#    kernel_size (int): taille du filtre, par défaut 3 donc de dimension 3x3
#    batchnorm (bool) : booléen pour en fonction rajouter ou non une couche de BatchNormalization, par défaut True
#
# SORTIES DE LA FONCTION :
#    Cela renvoie input_tensor transformée après le passage dans les couches du bloc convolutif
#
def conv2dBlock(input_tensor, n_filters, kernel_size = 3, batchnorm = True):
    # Première couche
    x = Conv2D(filters = n_filters, kernel_size = kernel_size, padding = 'same', activation = 'relu', kernel_initializer="he_normal")(input_tensor)
    if batchnorm:
        x = BatchNormalization()(x)
    # Deuxième couche
    x = Conv2D(filters = n_filters, kernel_size = kernel_size, padding = "same", activation = 'relu', kernel_initializer="he_normal")(x)
    if batchnorm:
        x = BatchNormalization()(x)
    return x

###########################################################################################################################################
# FONCTION unet()                                                                                                                         #
###########################################################################################################################################
# ROLE:
#    Création du réseau de neurone type UNet basé sur l'article https://arxiv.org/abs/1505.04597
#
# ENTREES DE LA FONCTION :
#    input_size (int) : dimension de l'image passée en entrée du réseau
#    n_filters (int) : nombre de filtres présents pour chaque couche convolutive
#    n_classes(int) : nombre de classes. Utile pour la dernière couche du réseau afin de classer
#    mode (string) : "mono" ou "multi" en fonction du nombre de classe que l'on utilise.
#    upconv (bool) : booléen utile pour la partie décodeur. Soit on utilise une UpConvolution soit on fait une convolution Transposée
#             True : conv2D + Upsampling2D, upconv = False : Conv2DTranspose (conseillé)
#
# SORTIES DE LA FONCTION :
#    Modèle Unet
#
def unet(input_size, n_filters, n_classes, kernel_size, mode, upconv = False):
    inputs = Input(input_size)

    # Encodeur
    convBlock1 = conv2dBlock(inputs, n_filters = n_filters, kernel_size = kernel_size)
    pool1 = MaxPooling2D(pool_size = 2, strides = 2)(convBlock1)

    convBlock2 = conv2dBlock(pool1, n_filters = n_filters*2, kernel_size = kernel_size)
    pool2 = MaxPooling2D(pool_size = 2, strides = 2)(convBlock2)

    convBlock3 = conv2dBlock(pool2, n_filters = n_filters*4, kernel_size = kernel_size)
    pool3 = MaxPooling2D(pool_size = 2, strides = 2)(convBlock3)

    convBlock4 = conv2dBlock(pool3, n_filters = n_filters*8, kernel_size = kernel_size)
    pool4 = MaxPooling2D(pool_size = 2, strides = 2)(convBlock4)

    # Centre
    convBlock5 = conv2dBlock(pool4, n_filters = n_filters*16, kernel_size = kernel_size)

    # Décodeur
    if upconv:
        up6 = Conv2D(n_filters*8, kernel_size = 2, activation = 'relu', padding = 'same', kernel_initializer="he_normal")(UpSampling2D(size = (2, 2))(convBlock5))
    else:
        up6 = Conv2DTranspose(filters = n_filters*8, kernel_size = kernel_size, strides = 2, activation = 'relu', padding = 'same', kernel_initializer="he_normal") (convBlock5)
    concat6 = Concatenate()([up6, convBlock4])
    convBlock6 = conv2dBlock(concat6, n_filters=n_filters*8, kernel_size=kernel_size)

    if upconv:
        up7 = Conv2D(n_filters*4, kernel_size = 2, activation = 'relu', padding = 'same', kernel_initializer="he_normal")(UpSampling2D(size = (2, 2))(convBlock6))
    else:
        up7 = Conv2DTranspose(filters = n_filters*4, kernel_size = kernel_size, strides = 2, activation = 'relu', padding = 'same', kernel_initializer="he_normal")(convBlock6)
    concat7 = Concatenate() ([up7, convBlock3])
    convBlock7 = conv2dBlock(concat7, n_filters = n_filters*4, kernel_size = kernel_size)

    if upconv:
        up8 = Conv2D(n_filters*2, kernel_size = 2, activation = 'relu', padding = 'same', kernel_initializer="he_normal")(UpSampling2D(size = (2, 2))(convBlock7))
    else:
        up8 = Conv2DTranspose(filters = n_filters*2, kernel_size = kernel_size, strides = 2, activation = 'relu', padding = 'same', kernel_initializer="he_normal") (convBlock7)
    concat8 = Concatenate()([up8, convBlock2])
    convBlock8 = conv2dBlock(concat8, n_filters = n_filters*2, kernel_size = kernel_size)

    if upconv:
        up9 = Conv2D(n_filters*1, kernel_size = 2, activation = 'relu', padding = 'same', kernel_initializer="he_normal")(UpSampling2D(size = (2, 2))(convBlock8))
    else:
        up9 = Conv2DTranspose(filters = n_filters*1, kernel_size = kernel_size, strides = 2, activation = 'relu',  padding = 'same', kernel_initializer="he_normal") (convBlock8)
    concat9 = Concatenate()([up9, convBlock1])
    convBlock9 = conv2dBlock(concat9, n_filters = n_filters*1, kernel_size = kernel_size)

    # Possibilité de mettre d'autres metrics en ajoutant le nom de la fonction dans la liste
    metrics = ['accuracy']

    # Couche de sortie/de classification
    if mode == "mono":
        outputs = Conv2D(n_classes, kernel_size = 1, activation='sigmoid') (convBlock9)
        model = Model(inputs = inputs, outputs = outputs)
        model.compile(optimizer = Adam(lr = 1e-3), loss = "binary_crossentropy", metrics = metrics)
    else:
        outputs = Conv2D(n_classes, kernel_size = 1) (convBlock9)
        model = Model(inputs = inputs, outputs = outputs)
        model.compile(optimizer = Adam(lr = 1e-3), loss = SparseCategoricalCrossentropy(from_logits = True), metrics = metrics)

    return model


            ##########################################################################
            #                                                                        #
            #                              RESUNET                                   #
            #                                                                        #
            ##########################################################################

###########################################################################################################################################
# FONCTION convBlock()                                                                                                                   #
###########################################################################################################################################
# ROLE:
#    Création d'un bloc de convolutions comprenant une BatchNormalization, une activation ReLu et une couche de neurones convolutif.
#
# ENTREES DE LA FONCTION :
#    x (tensor) : soit l'image modifiée en entrée du réseau de neurones soit l'activation de la couche précédente
#    n_filters (int) : nombre de filtres présents pour chaque couche convolutive
#    kernel_size (int) : taille du filtre, par défaut 3 donc de dimension 3x3
#    padding (int) : rajoute des 0 au filtre de telle sorte qu'en sortie de la convolution, l'image conserve sa dimension
#    strides (int) : permet de determiner de combien se déplace le filtre après chaque opération
#
# SORTIES DE LA FONCTION :
#    Cela renvoie x transformée après le passage dans les couches du bloc convolutif
#
def convBlock(x, n_filters, kernel_size = 3, padding = 'same', strides = 1):
    x = BatchNormalization()(x)
    x = Activation('relu')(x)
    x = Conv2D(n_filters, kernel_size, padding = padding, strides = strides, kernel_initializer="he_normal")(x)
    return x

###########################################################################################################################################
# FONCTION inputBlock()                                                                                                                  #
###########################################################################################################################################
# ROLE:
#    Création du premier bloc de convolution en entrée du réseau.
#
# ENTREES DE LA FONCTION :
#    x (tensor) : soit l'image modifiée en entrée du réseau de neurones soit l'activation de la couche précédente
#    n_filters (int) : nombre de filtres présents pour chaque couche convolutive
#    kernel_size (int) : taille du filtre, par défaut 3 donc de dimension 3x3
#    padding (int) : rajoute des 0 à l'image de telle sorte qu'en sortie de la convolution, l'image conserve sa dimension
#    strides (int) : permet de determiner de combien se déplace le filtre après chaque opération
#
# SORTIES DE LA FONCTION :
#    Cela renvoie add qui est un modèle représentant le block d'entrée de l'encodeur.
#
def inputBlock(x, n_filters, kernel_size = 3, padding = 'same', strides = 1):
    conv = Conv2D(n_filters, kernel_size, padding = padding, strides = strides, kernel_initializer="he_normal")(x)
    conv = convBlock(conv, n_filters, kernel_size, padding, strides)
    x_skip = Conv2D(n_filters, kernel_size = 3, padding = padding, strides = strides, kernel_initializer="he_normal")(x)
    x_skip = BatchNormalization()(x_skip)
    add = Add()([conv, x_skip])
    return add

###########################################################################################################################################
# FONCTION residualBlock()                                                                                                               #
###########################################################################################################################################
# ROLE:
#    Création d'un bloc basique dans les réseaux de neurones type ResNet.
#
# ENTREES DE LA FONCTION :
#    x (tensor) : soit l'image modifiée en entrée du réseau de neurones soit l'activation de la couche précédente
#    n_filters (int) : nombre de filtres présents pour chaque couche convolutive
#    kernel_size (int) : taille du filtre, par défaut 3 donc de dimension 3x3
#    padding (int) : rajoute des 0 à l'image de telle sorte qu'en sortie de la convolution, l'image conserve sa dimension
#    strides (int) : permet de determiner de combien se déplace le filtre après chaque opération
#
# SORTIES DE LA FONCTION :
#    Cela renvoie add qui est un modèle représentant un block basique dans les réseaux de neurones type ResNet.
#
def residualBlock(x, n_filters, kernel_size = 3, padding = 'same', strides = 1):
    res = convBlock(x, n_filters, kernel_size, padding, strides)
    res = convBlock(res, n_filters, kernel_size, padding, 1)
    x_skip = Conv2D(n_filters, kernel_size, padding = padding, strides = strides, kernel_initializer="he_normal")(x)
    x_skip = BatchNormalization()(x_skip)
    add = Add()([x_skip, res])
    return add

###########################################################################################################################################
# FONCTION resunet()                                                                                                                      #
###########################################################################################################################################
# ROLE:
#    Création du réseau de neurone type ResUNet basé sur les articles https://arxiv.org/pdf/1711.10684.pdf et https://www.kaggle.com/ekhtiar/lung-segmentation-cropping-resunet-tf-#    keras.
#
# ENTREES DE LA FONCTION :
#    input_size (int) : dimension de l'image passée en entrée du réseau
#    n_filters (int) : nombre de filtres présents pour chaque couche convolutive
#    n_classes (int) : nombre de classes. Utile pour la dernière couche du réseau afin de classer
#    mode (string) : "mono" ou "multi" en fonction du nombre de classe que l'on utilise.
#
# SORTIES DE LA FONCTION :
#    Modèle ResUNet
#
def resunet(input_size, n_filters, n_classes, kernel_size, mode):
    inputs = Input(input_size)

    # Encodeur
    block_down = inputBlock(inputs, n_filters, kernel_size)

    res_down1 = residualBlock(block_down, n_filters * 2, kernel_size = kernel_size, strides = 2)
    res_down2 = residualBlock(res_down1, n_filters * 4, kernel_size = kernel_size, strides = 2)

    # Centre
    middle_block1 = convBlock(res_down2, n_filters * 8, kernel_size = kernel_size, strides = 2)
    middle_block2 = convBlock(middle_block1, n_filters * 8, kernel_size = kernel_size)

    # Decodeur
    up1 = UpSampling2D(size = (2, 2))(middle_block2)
    concat1 = Concatenate()([res_down2, up1])
    res_up1 = residualBlock(concat1, n_filters * 4, kernel_size)

    up2 = UpSampling2D(size = (2, 2))(res_up1)
    concat2 = Concatenate()([res_down1, up2])
    res_up2 = residualBlock(concat2, n_filters * 2, kernel_size)

    up3 = UpSampling2D(size = (2, 2))(res_up2)
    concat3 = Concatenate()([block_down, up3])
    res_up3 = residualBlock(concat3, n_filters, kernel_size)

    # Possibilité de mettre d'autres metrics en ajoutant le nom de la fonction dans la liste
    metrics = ['accuracy']

    # Couche de sortie/de classification
    if mode == "mono":
        outputs = Conv2D(n_classes, kernel_size = 1, activation='sigmoid')(res_up3)
        model = Model(inputs = inputs, outputs = outputs)
        model.compile(optimizer = Adam(lr = 1e-3), loss = "binary_crossentropy", metrics = metrics)
    else:
        outputs = Conv2D(n_classes, kernel_size = 1) (res_up3)
        model = Model(inputs = inputs, outputs = outputs)
        model.compile(optimizer = Adam(lr = 1e-3), loss = SparseCategoricalCrossentropy(from_logits = True), metrics = metrics)

    return model

###########################################################################################################################################
#                                                                                                                                         #
# PARTIE PREDICTION (génération des résultats)                                                                                            #
#                                                                                                                                         #
###########################################################################################################################################

###########################################################################################################################################
# FONCTION savePredictedMaskAsRasterGenerator()                                                                                      #
###########################################################################################################################################
# ROLE:
#    Création des fichiers pour y stocker les masques obtenus après la prédiction du réseau de neurones. Production de nom_masque.tif
#
# ENTREES DE LA FONCTION :
#    predicted_mask (string list) : la liste des masques obtenus après le keras.predict()
#    filenames (string list) : la liste des noms des fichiers (chemins)
#    prediction_dir (string) : le chemin pour sauvegarder les masques
#    pixel_size (int) : taille d'un pixel
#    size_grid (int) : définis la dimension des imagettes
#
# SORTIES DE LA FONCTION :
#    Aucune sortie
#
def savePredictedMaskAsRasterGenerator(predicted_mask, filenames, prediction_dir, pixel_size, size_grid):
    no_of_bands = predicted_mask[0].shape[2]
    #print("no_of_bands : "+str(no_of_bands))
    height = predicted_mask[0].shape[1]
    width = predicted_mask[0].shape[0]
    j=0
    with tqdm(total = len(filenames)) as pbar:
        for filename in filenames:

            mask = predicted_mask[j]
            mask_name = filename.split("/")[-1]
            #print("mask_name :"+mask_name)
            output_name = prediction_dir + mask_name
            #print("output_name :"+output_name)
            if no_of_bands != 1:
                mask = changeNodataInPrediction(mask, size_grid)
            else:
                mask[mask >= 0.5] = 1
                mask[mask < 0.5] = 0

            source_ds = Open(filename, GA_ReadOnly)
            source_projection = source_ds.GetProjection()
            ulx = source_ds.GetGeoTransform()[0]
            uly = source_ds.GetGeoTransform()[3]
            geotransform = [0, 0, 0, 0, 0, 0]
            geotransform[0] = ulx
            geotransform[1] = pixel_size
            geotransform[2] = 0
            geotransform[3] = uly
            geotransform[4] = 0
            geotransform[5] = - pixel_size

            driver = GetDriverByName('GTiff')
            target_ds = driver.Create(output_name, width, height, 1, GDT_Byte)
            target_ds.SetGeoTransform(geotransform)
            target_ds.SetProjection(source_projection)
            mask = mask.squeeze()
            band = target_ds.GetRasterBand(1)
            band.WriteArray(mask)

            source_ds = None
            target_ds = None
            band = None
            j = j+1
            pbar.update(1)

###########################################################################################################################################
# FONCTION changeNodataInPrediction()                                                                                                  #
###########################################################################################################################################
# ROLE:
#    Changement du masque prédit en enlevant la classe no_data. Les pixels ayant la classe no_data attribué ont maintenant la deuxième classe la plus probable
#
# ENTREES DE LA FONCTION :
#    mask (array) : un masque résultant d'un keras.predict()
#    size_grid (int) : définis la dimension des imagettes
#
# SORTIES DE LA FONCTION :
#    Le même masque auquel on a retiré la classe no_data
#
def changeNodataInPrediction(mask, size_grid):
    new_mask = np.zeros((mask.shape[0], mask.shape[1], 1), dtype = np.uint8)
    #print("mask : "+str(len(mask[0][0])))
    cpt_px_change_classif = 0
    for i in range(size_grid):
        for j in range(size_grid):
            temp = mask[i,j]
            
            if np.argmax(temp) == 0:
                temp = np.delete(temp, 0)
                #print("0 -> "+str(np.argmax(temp)))
                new_mask[i,j] = np.argmax(temp) + 1
                cpt_px_change_classif = cpt_px_change_classif + 1 
            else:
                new_mask[i,j] = np.argmax(temp)
            
            #new_mask[i,j] = np.argmax(temp) + 1
    if debug >= 2 and cpt_px_change_classif != 0:
        print("cpt_px_change_classif : "+str(cpt_px_change_classif))
    return new_mask

###########################################################################################################################################
# FONCTION predictionTestGenerator()                                                                                                    #
###########################################################################################################################################
# ROLE:
#    Prédiction sur les données d'évaluations puis modification pour les pixels no_data et stockage dans des fichiers .tiff.
#
# ENTREES DE LA FONCTION :
#    model (string) : le modèle (réseau de neurones) entrainé
#    test_gen (array list) : les données à tester (issues de DataGenerator)
#    filenames (string list) : la liste des noms des fichiers (chemins)
#    prediction_dir (string) : le chemin pour sauvegarder les masques
#    pixel_size (int) : taille d'un pixel
#    size_grid (int) : définis la dimension des imagettes
#
# SORTIES DE LA FONCTION :
#    Aucune sortie
#
def predictionTestGenerator(model, test_gen, filenames, prediction_dir, pixel_size, size_grid):
    #print("LEN test_gen : "+str(len(test_gen)))
    pred_test = model.predict(test_gen)
    #print("LEN pred_test : "+str(len(pred_test)))
    savePredictedMaskAsRasterGenerator(pred_test, filenames, prediction_dir, pixel_size, size_grid)

###########################################################################################################################################
#                                                                                                                                         #
# PARTIE EVALUATION DE PERFORMANCE (Matrice de confusion)                                                                                 #
#                                                                                                                                         #
###########################################################################################################################################

###########################################################################################################################################
# FONCTION cleanConfusionMatrixFile()                                                                                                  #
###########################################################################################################################################
# ROLE:
#    Filtrage du fichier pour ne garder que ce qui nous intéresse à partir de mots clés. Modification de ce fichier
#
# ENTREES DE LA FONCTION :
#    cm_file (string) : fichier .txt contenant la redirection du résultat de la commande otbcli_ComputeConfusionMatrix
#
# SORTIES DE LA FONCTION :
#    Aucune sortie
#
def cleanConfusionMatrixFile(cm_file):
    # Mots clés à chercher dans le fichier
    keyword = [
        "#Reference labels",
        "#Produced labels",
        "Precision",
        "Recall",
        "F-score",
        "Kappa",
        "Overall"
    ]

    # Lecture/Ecriture du fichier final pour ne garder que les informations importantes
    with open(cm_file) as f_read:
        lines = f_read.readlines()
    with open(cm_file, "w") as f_write:
        for line in lines:
            if (any(word in line for word in keyword) or (not(line[0].isnumeric()))):
                if line[0].isnumeric():
                    w = [word for word in keyword if word in line]
                    f_write.write(line[line.index(*w):])
                else:
                    f_write.write(line)

###########################################################################################################################################
# FONCTION computeMatrix()                                                                                                                #
###########################################################################################################################################
# ROLE:
#    Calcul de la matrice de confusion entre le masque de référence et la prédiction avec otbcli_ComputeConfusionMatrix
#    Récupération des résultats de cette commande dans un fichier .txt
#
# ENTREES DE LA FONCTION :
#    NN (structure) : structure contenant tout les paramètres propre au réseau de neurones
#    n_bands (int) : nombre de bandes des images utilisées
#    n_classes (int) : nombre de classes
#    training_input (string list) : chemin vers les imagettes d'entrainement 
#
# SORTIES DE LA FONCTION :
#    Aucune sortie
#
def computeMatrix(NN, n_bands, n_classes, training_input):
    # Récupération des chemins
    dir_ref = training_input
    dir_pred = NN.predict
    dir_quality = NN.quality

    # Calcul matrice de confusion pour tous les masques
    filenames = os.listdir(dir_pred)
    with tqdm(total = len(filenames)) as pbar:
        for mask in filenames:
            mask_name = mask.split(".")[0]
            # Chemin complet pour la référence et la prédiction
            ref = dir_ref + mask
            # Vérification de l'existance du masque car certaines images n'avaient pas de masque associé
            if os.path.exists(ref):
                pred = dir_pred + mask
                # Fichier final
                matrix_file = dir_quality + mask_name + ".txt"
                # Fichier servant à rediriger ce que produit otbcli_ComputeConfusionMatrix
                temp_file = dir_quality + mask_name + "_temp.txt"
                open(temp_file, 'a').close()
                command = "otbcli_ComputeConfusionMatrix -in %s -ref raster -ref.raster.in %s -no_data_value %s -ref.raster.nodata %s -out %s > %s" %(pred, ref, str(5), str(5), temp_file, matrix_file)
                os.system(command)
                os.remove(temp_file)
                cleanConfusionMatrixFile(matrix_file)

            pbar.update(1)
            


###########################################################################################################################################
#                                                                                                                                         #
# PARTIE FONCTION PRINCIPALES  (Train,Test,Pretraitement)                                                                                 #
#                                                                                                                                         #
###########################################################################################################################################


#########################################################################
# FONCTION cutImageByGrid()                                             #
#########################################################################
# ROLE:
#    Cette fonction découpe une image (.tif) par un vecteur (.shp) 
#
# ENTREES DE LA FONCTION :
#    cut_shape_file (string) : le nom du shapefile de découpage (exple : "/chemin/path_clipper.shp")
#    input_image (string) : le nom de l'image à traiter (exmple : "/users/images/image_raw.tif")
#    output_image (string) : le nom de l'image resultat découpée (exmple : "/users/images/image_cut.tif")
#    grid_size_x (int) : dimension de la grille en x
#    grid_size_y (int) : dimension de la grille en y
#    debord (int) : utilisé pour éviter les effets de bord. Agrandit artificiellement les imagettes
#    pixel_size_x (float) : taille du pixel de sortie en x
#    pixel_size_y (float) : taille du pixel de sortie en y
#    no_data_value (int) : valeur de l'image d'entrée à transformer en NoData dans l'image de sortie
#    epsg (int) : Valeur de la projection par défaut 0, si à 0 c'est la valeur de projection du fichier raster d'entrée qui est utilisé automatiquement
#    format_raster (string) : le format du fichier de sortie, par defaut : 'GTiff'
#    format_vector (string) : format du fichier vecteur, par defaut : 'ESRI Shapefile' 
#
# SORTIES DE LA FONCTION :
#    Aucune sortie 
#
def cutImageByGrid(cut_shape_file ,input_image, output_image, grid_size_x, grid_size_y, debord, pixel_size_x=None, pixel_size_y=None, no_data_value=0, epsg=0, format_raster="GTiff", format_vector='ESRI Shapefile'):

    if debug >= 3:
        print(cyan + "cutImageByGrid() : Vecteur de découpe des l'image : " + cut_shape_file + endC)
        print(cyan + "cutImageByGrid() : L'image à découper : " + input_image + endC)

    # Constante
    EPSG_DEFAULT = 2154

    ret = True

    # Récupération de la résolution du raster d'entrée
    if pixel_size_x == None or pixel_size_y == None :
        pixel_size_x, pixel_size_y = getPixelWidthXYImage(input_image)

    if debug >= 5:
        print("Taille des pixels : ")
        print("pixel_size_x = " + str(pixel_size_x))
        print("pixel_size_y = " + str(pixel_size_y))
        print("grid_size_x = " + str(grid_size_x))
        print("grid_size_y = " + str(grid_size_y))
        print("debord = " + str(debord))
        print("\n")

    # Récuperation de l'emprise de l'image
    ima_xmin, ima_xmax, ima_ymin, ima_ymax = getEmpriseImage(input_image)

    if debug >= 5:
        print("Emprise raster : ")
        print("ima_xmin = " + str(ima_xmin))
        print("ima_xmax = " + str(ima_xmax))
        print("ima_ymin = " + str(ima_ymin))
        print("ima_ymax = " + str(ima_ymax))
        print("\n")

    # Récuperation de la projection de l'image
    if epsg == 0:
        epsg_proj = getProjectionImage(input_image)
    else :
        epsg_proj = epsg
    if epsg_proj == 0:
        epsg_proj = EPSG_DEFAULT

    if debug >= 3:
        print(cyan + "cutImageByGrid() : EPSG : " + str(epsg_proj) + endC)

    # Identification de l'emprise de vecteur de découpe
    empr_xmin, empr_xmax, empr_ymin, empr_ymax = getEmpriseFile(cut_shape_file, format_vector)

    if debug >= 5:
        print("Emprise vector : ")
        print("empr_xmin = " + str(empr_xmin))
        print("empr_xmax = " + str(empr_xmax))
        print("empr_ymin = " + str(empr_ymin))
        print("empr_ymax = " + str(empr_ymax))
        print("\n")

    # Calculer l'emprise arrondi
    xmin, xmax, ymin, ymax = roundPixelEmpriseSize(pixel_size_x, pixel_size_y, empr_xmin, empr_xmax, empr_ymin, empr_ymax)

    if debug >= 5:
        print("Emprise vecteur arrondi a la taille du pixel : ")
        print("xmin = " + str(xmin))
        print("xmax = " + str(xmax))
        print("ymin = " + str(ymin))
        print("ymax = " + str(ymax))
        print("(debord * pixel_size_x)/2 = "+str((debord * pixel_size_x)/2))
        print("\n")

    # Trouver l'emprise optimale   
    opt_xmin = xmin - (debord * pixel_size_y)/2
    opt_xmax = xmin + grid_size_x + (debord * pixel_size_x)/2
    
    opt_ymin = ymax - grid_size_y - (debord * pixel_size_y)/2
    opt_ymax = ymax + (debord * pixel_size_x)/2
    
    
    if debug >= 5:
        print("Emprise retenu : ")
        print("opt_xmin = " + str(opt_xmin))
        print("opt_xmax = " + str(opt_xmax))
        print("opt_ymin = " + str(opt_ymin))
        print("opt_ymax = " + str(opt_ymax))
        print("\n")

    # Découpage grace à gdal
    command = 'gdalwarp -t_srs EPSG:%s  -te %s %s %s %s -tap -multi -co "NUM_THREADS=ALL_CPUS" -tr %s %s -dstnodata %s -overwrite -of %s %s %s' %(str(epsg_proj), opt_xmin, opt_ymin, opt_xmax, opt_ymax, pixel_size_x, pixel_size_y, str(no_data_value), format_raster, input_image, output_image)

    if debug >= 4:
        print(command)

    exit_code = os.system(command)
    if exit_code != 0:
        print(command)
        print(cyan + "cutImageByGrid() : " + bold + red + "!!! Une erreur c'est produite au cours du decoupage de l'image : " + input_image + ". Voir message d'erreur." + endC, file=sys.stderr)
        ret = False

    else :
        if debug >= 4:
            print(cyan + "cutImageByGrid() : L'image résultat découpée : " + output_image + endC)

    return ret
    
#########################################################################
# FONCTION createFileOutputImagette()                                   #
#########################################################################
# ROLE:
#    Cette fonction crée le chemin du fichier de sortie correspondant à une imagette redimensionnée 
#
# ENTREES DE LA FONCTION :
#    file_grid_temp (string) : fichier de découpe de l'imagette
#    file_imagette (string) : fichier de l'imagette classifiée
#    classification_resized_dir (string) : dossier où stocker les imagettes classifiées redimensionnées
#    extension_raster (string) :  extension d'un fichier raster
#
# SORTIES DE LA FONCTION :
#    Renvoie les fichiers d'entrée file_grid_temp, file_imagette ainsi que le chemin du fichier de sortie créé
#
def createFileOutputImagette(file_grid_temp, file_imagette, classification_resized_dir, extension_raster):

    # Récupération du nom de l'imagette
    imagette_file = file_imagette.split(os.sep)[-1]
    imagette_file_name = imagette_file.split(".")[0]
    output_imagette = classification_resized_dir + imagette_file_name + "_tmp" + extension_raster
        
    if debug >= 5 :
        print("file_grid_temp : "+file_grid_temp)
        print("file_imagette : "+file_imagette)
        print("output_imagette : "+output_imagette)
            
    return file_grid_temp, file_imagette, output_imagette

###########################################################################################################################################
# FONCTION assemblyImages()                                                                                                               #
###########################################################################################################################################
# ROLE:
#    Reconstruction de l'image satellite entière. Utilisé pour assembler les différentes imagettes résultats de la prédiction
#
# ENTREES DE LA FONCTION :
#    NN (structure) : structure contenant tout les paramètres propre au réseau de neurones
#    prediction_dir (string) : chemin du dossier Predict
#    classification_resized_dir (string) : chemin du dossier des imagettes classifiées redimmensionnées 
#    input_img_paths (string list) : liste contenant les chemins vers toutes les imagettes
#    output_assembly (string) : chemin pour l'image de sortie assemblée
#    vector_simple_mask (string) : vecteur simplifié de l'image 
#    split_tile_vector_list (string list) : liste des vecteurs de découpe
#    image_input (string) : image satellite d'entrée
#    debord (int) : utilisé pour éviter les effets de bord. Agrandit artificiellement les imagettes
#    no_data_value (int) : valeur que prend un pixel qui ne contient pas d'information
#    epsg (int) : identificateur de SIG
#    extension_raster (string) : extension de fichier des imagettes
#    format_vector (string) : format des vecteurs
#    format_raster (string) : format des imagettes
#
# SORTIES DE LA FONCTION :
#    Renvoie l'image satellite assemblée 
#
def assemblyImages(NN, prediction_dir, classification_resized_dir, input_img_paths, output_assembly, vector_simple_mask, split_tile_vector_list, image_input, debord, no_data_value=0, epsg=2154, extension_raster=".tif", format_vector='ESRI Shapefile', format_raster='GTiff'):

    imagette_file_list = prediction_dir + "liste_images_tmp.txt"

    # Récupération de la taille d'un pixel
    pixel_size, _ = getPixelWidthXYImage(image_input)
    # Pour avoir le même ordre d'apparition de fichiers que input_img_paths
    split_tile_vector_list = sorted(split_tile_vector_list)

    
    number_vector = len(split_tile_vector_list)
    #print("number_vector : "+str(number_vector))
    number_CPU = int(os.cpu_count()/4) #number_vector
    #print("Output os.cpu_count()/2 :"+str(os.cpu_count()/2))
    #print("number_CPU : "+str(number_CPU))
    rapport_division_CPU = number_vector // number_CPU
    #print("rapport_division_CPU : "+str(rapport_division_CPU))
    rapport_modulo_CPU = number_vector % number_CPU
    #print("rapport_modulo_CPU : "+str(rapport_modulo_CPU))
    
    if debord != 0 :
        for i in range(rapport_division_CPU):
            # Initialisation de la liste pour le multi-threading
            thread_list = []
            for j in range(number_CPU):
            
                file_grid_temp, file_imagette, output_imagette =  createFileOutputImagette(split_tile_vector_list[(i * number_CPU) + j], input_img_paths[i * number_CPU + j], classification_resized_dir, extension_raster)
                
                # Découpage de l'image par multi-threading
                thread = threading.Thread(target=cutImageByVector, args=(file_grid_temp ,file_imagette, output_imagette, pixel_size, pixel_size, no_data_value, epsg, format_raster, format_vector))
                thread.start()
                thread_list.append(thread)
                
                appendTextFileCR(imagette_file_list, output_imagette)
              
            # Attente fin de tout les threads
            try:
                for thread in thread_list:
                    thread.join()
            except:
                print(cyan + "computePreTreatment() : " + bold + red + "computePreTreatment() : " + endC + "Erreur lors de le decoupe : impossible de demarrer le thread" + endC, file=sys.stderr)
                
        # Initialisation de la liste pour le multi-threading
        thread_list = []            
        for i in range(rapport_modulo_CPU):
        
            file_grid_temp, file_imagette, output_imagette =  createFileOutputImagette(split_tile_vector_list[(rapport_division_CPU * number_CPU) + i], input_img_paths[(rapport_division_CPU * number_CPU) + i], classification_resized_dir, extension_raster)
            
            # Découpage de l'image par multi-threading
            thread = threading.Thread(target=cutImageByVector, args=(file_grid_temp ,file_imagette, output_imagette, pixel_size, pixel_size, no_data_value, epsg, format_raster, format_vector))
            thread.start()
            thread_list.append(thread)
            
            appendTextFileCR(imagette_file_list, output_imagette)           

        # Attente fin de tout les threads
        try:
            for thread in thread_list:
                thread.join()
        except:
            print(cyan + "computePreTreatment() : " + bold + red + "computePreTreatment() : " + endC + "Erreur lors de le decoupe : impossible de demarrer le thread" + endC, file=sys.stderr)       
    
    # Cas où il n'y a pas de débord et donc pas besoin de redécouper les images
    else :
        for i in range(len(input_img_paths)):
            appendTextFileCR(imagette_file_list, input_img_paths[i])
            
            
    # Fusion des imagettes
    cmd_merge = "gdal_merge" + getExtensionApplication() + " -of " + format_raster + " -ps " + str(pixel_size) + " " + str(pixel_size) + " -n " + str(no_data_value) + " -a_nodata " + str(no_data_value) + " -o "  + output_assembly + " --optfile " + imagette_file_list
    print(cmd_merge)
    exit_code = os.system(cmd_merge)
    if exit_code != 0:
        raise NameError (bold + red + "!!! Une erreur c'est produite au cours du merge des images. Voir message d'erreur."  + endC)
        
    # Decoupage selon l'emprise 
    if vector_simple_mask != "":
    
        decoupe = "_decoupe"
        splitText = output_assembly.split(".")
        output_assembly_decoupe = splitText[0] + decoupe + "." + splitText[1]
        cutImageByVector(vector_simple_mask , output_assembly, output_assembly_decoupe, pixel_size, pixel_size, no_data_value, epsg, format_raster, format_vector)
        
        output_assembly = output_assembly_decoupe
        
        if debug >= 2:
            print("Decoupage de l'image assemblée effectué")
                   
    # Si le fichier de sortie mergé a perdu sa projection on force la projection à la valeur par defaut
    if getProjectionImage(output_assembly) == None or getProjectionImage(output_assembly) == 0:
        if epsg != 0 :
            updateReferenceProjection(None, output_assembly, int(epsg))
        else :
            raise NameError (bold + red + "!!! Erreur les fichiers images d'entrée non pas de projection défini et vous n'avez pas défini de projection (EPSG) en parametre d'entrée."  + endC)
    
    return output_assembly

###########################################################################################################################################
# FONCTION fillTableFiles()                                                                                                               #
###########################################################################################################################################
# ROLE:
#    Remplir la matrice contenant les chemins vers l'ensemble des imagettes
#
# ENTREES DE LA FONCTION :
#    split_tile_vector (string) : vecteur de découpe
#    input_table (string list list) : matrice dans laquelle on va stocker l'imagette de sortie 
#    repertory_data_imagette_temp (string) : dossier contenant les imagettes
#    name_file (string) : nom du fichier de l'imagette 
#    extension_raster (string) : extension de fichier des imagettes
#
# SORTIES DE LA FONCTION :
#    Renvoie le chemin de l'imagette 
#    
def fillTableFiles(split_tile_vector, input_table, repertory_data_imagette_temp, name_file , extension_raster):

        # Récupération du numéro de ligne et de colonne
        sub_name = split_tile_vector.split(".")[0].split("_")[-1]
        #print(sub_name)
        find_ligne = sub_name.find("l")
        find_colonne = sub_name.find("c")
        id_ligne = int(sub_name[find_ligne+1:find_colonne]) - 1
        id_colonne = int(sub_name[find_colonne+1:]) - 1

        # Création de l'iamge de sortie
        output_image = repertory_data_imagette_temp + os.sep + name_file + sub_name + extension_raster
        #print("Output_image : "+output_image)
        
        # Remplis les matrices
        #print("Image que l'on veut stocker : "+output_image)
        #print("Coordonnées :" +str(id_ligne) +" | "+ str(id_colonne))

        # Remplis la matrice
        input_table[id_ligne].append(output_image)
        #print("Apres ajout dans la matrice il y a : "+ str(input_table[id_ligne]))
       
        return output_image
                 
###########################################################################################################################################
# FONCTION computePreTreatment()                                                                                                          #
###########################################################################################################################################
# ROLE:
#    Pré-traitement de l'image qui va être découpée en imagettes pour pouvoir entrer en entrée du réseau de neurones
#
# ENTREES DE LA FONCTION :
#    NN (structure) : structure contenant tout les paramètres propre au réseau de neurones
#    debord (int) : utilisé pour éviter les effets de bord. Agrandit artificiellement les imagettes
#    neural_network_mode (string) : nom du type de réseau de neurones
#    model (string) : nom du modèle, réseau de neurones
#    training_input (string) : l'image satellite d'apprentissage
#    image_input (string) : l'image satellite 
#    vector_input (string) : vecteur de découpe d'entrée (pas obligatoire)
#    image_output (string) : chemin de l'image de sortie du réseau de neurones, classifiée
#    size_grid (int) : dimension d'une cellule de la grille de découpe de l'image satellite initiale 
#    overwrite (bool) : booléen pour écrire ou non par dessus un fichier existant
#    extension_raster (string) : extension de fichier des imagettes
#    extension_vector (string) : extension de fichier des vecteurs
#    format_raster (string) : format des imagettes
#    format_vector (string) : format des vecteurs
#    epsg (int) : Identificateur de SIG
#
# SORTIES DE LA FONCTION :
#    Renvoie les martices contenant les chemins des imagettes, l'emprise de l'image, la liste des vecteurs de découpes ainsi que le nom des dossieres où sont stockés les vecteurs et imagettes
#    
def computePreTreatment(NN,debord,neural_network_mode, model, training_input, image_input, vector_input, image_output, size_grid, overwrite=True, extension_raster=".tif", extension_vector=".shp", format_raster='GTiff', format_vector='ESRI Shapefile', epsg=2154):

    simplify_vector_param=10.0
    
    # Constantes pour les dossiers et fichiers
    FOLDER_VECTOR_TEMP = "_Vect_"
    FOLDER_DATA_TEMP = "_Data_"
    FOLDER_IMAGETTE = "Imagette_"
    FOLDER_TRAIN = "Train_"
    FOLDER_GRID = "Grid_"

    SUFFIX_VECTOR = "_vect"
    SUFFIX_CUT = "_cut"
    SUFFIX_MASK_CRUDE = "_crude"
    SUFFIX_VECTOR_SIMPLIFY = "_vect_simplify"
    SUFFIX_GRID_TEMP = "_grid_temp"
    
    # Récupération du nom du réseau
    model_file = model.split(os.sep)[-1]
    model_file_name = model_file.split(".")[0]

    # Récupération de la taille d'un pixel
    pixel_size, _  = getPixelWidthXYImage(image_input)


    repertory = os.path.dirname(image_output)
    repertory_vect_temp = repertory + os.sep + neural_network_mode + FOLDER_VECTOR_TEMP + model_file_name

    # Création du dossier s'il n'existe pas déjà
    if not os.path.isdir(repertory_vect_temp):
        os.makedirs(repertory_vect_temp)
    
    # Récupération du nom de l'image et de la valeur de nodata
    image_name = os.path.splitext(os.path.basename(image_input))[0]
    cols, rows, num_band = getGeometryImage(image_input)
    no_data_value = getNodataValueImage(image_input, num_band)
    if no_data_value == None :
        no_data_value = 0
    
    # Creation du vecteur d'emprise s'il n'es pas déjà fournis (vecteur d'emprise sous forme de polygone .shp)
    if vector_input == "" :

        # Création du masque délimitant l'emprise de la zone par image
        vector_mask = repertory_vect_temp + os.sep + image_name + SUFFIX_MASK_CRUDE + extension_vector
        createVectorMask(image_input, vector_mask, no_data_value, format_vector) 

        # Simplification du masque
        vector_simple_mask = repertory_vect_temp + os.sep + image_name + SUFFIX_VECTOR_SIMPLIFY + extension_vector
        simplifyVector(vector_mask, vector_simple_mask, simplify_vector_param, format_vector)
    else :
        vector_simple_mask = vector_input
    
    # Creer le fichier grille
    image_dimension = size_grid*pixel_size
    vector_grid_temp = repertory_vect_temp + os.sep + image_name + SUFFIX_GRID_TEMP + extension_vector
    nb_polygon = createGridVector(vector_simple_mask, vector_grid_temp, image_dimension - (debord * pixel_size), image_dimension - (debord * pixel_size), None, overwrite, epsg , format_vector)
    
    repertory_data_temp = repertory + os.sep + neural_network_mode + FOLDER_DATA_TEMP + model_file_name
    
    repertory_data_imagette_temp = repertory_data_temp + os.sep + FOLDER_IMAGETTE + model_file_name
    # Création du dossier s'il n'existe pas déjà
    if not os.path.isdir(repertory_data_imagette_temp):
        os.makedirs(repertory_data_imagette_temp)

    repertory_data_train_temp = repertory_data_temp + os.sep + FOLDER_TRAIN + model_file_name
    # Création du dossier s'il n'existe pas déjà
    if not os.path.isdir(repertory_data_train_temp):
        os.makedirs(repertory_data_train_temp)
        
    repertory_data_grid_temp = repertory_data_temp + os.sep + FOLDER_GRID + model_file_name
    # Création du dossier s'il n'existe pas déjà
    if not os.path.isdir(repertory_data_grid_temp):
        os.makedirs(repertory_data_grid_temp) 
        
    # Extraire chaque polygone en un fichier vector_grid_temp    
    split_tile_vector_list = splitVector(vector_grid_temp, repertory_data_grid_temp, "sub_name", epsg, format_vector, extension_vector)

   
    #print("len(split_tile_vector_list) : " + str(len(split_tile_vector_list)))
    
    # Récupération des dimensions des matrices
    sub_name = split_tile_vector_list[-1].split(".")[0].split("_")[-1]
    find_ligne = sub_name.find("l")
    find_colonne = sub_name.find("c")
    nombre_ligne = int(sub_name[find_ligne+1:find_colonne])
    nombre_colonne = int(sub_name[find_colonne+1:])
    
    # Initialisation des deux listes de listes
    training_table = []
    input_table = []
    for i in range(nombre_ligne):
        input_table.append([])
        training_table.append([])

    # Récupération du nombre de vecteurs de découpe et définition du nombre de threads à utiliser
    number_vector = len(split_tile_vector_list)
    number_CPU = int(os.cpu_count()/2) #number_vector
    #print("os.cpu_count()/2 :"+str(os.cpu_count()/2))
    
    rapport_division_CPU = number_vector // number_CPU
    rapport_modulo_CPU = number_vector % number_CPU
    
    # Initialisation des listes
    output_image_path_list = []
    output_train_image_path_list = []

    # Découpage de l'image d'entrée
    for i in range(rapport_division_CPU):
        # Initialisation de la liste pour le multi-threading
        thread_list = []
        for j in range(number_CPU):
        
            #output_image = output_image_path_list[(i * number_CPU) + j]
            output_image = fillTableFiles(split_tile_vector_list[(i * number_CPU) + j], input_table, repertory_data_imagette_temp, "sat_", extension_raster)
            output_image_path_list.append(output_image)
            #print("Output Image :" + output_image)

            if debug >= 1 :
                print("Traitement de la tuile " + str((i * number_CPU) + j+1) +"/"+ str(number_vector) + "...")
            if os.path.exists(split_tile_vector_list[(i * number_CPU) + j]):
                # Découpage de l'image par multi-threading
                thread = threading.Thread(target=cutImageByGrid, args=(split_tile_vector_list[i * number_CPU + j], image_input, output_image, image_dimension - (debord * pixel_size), image_dimension - (debord * pixel_size), debord, pixel_size, pixel_size, no_data_value, epsg, format_raster, format_vector))
                thread.start()
                thread_list.append(thread)
        
        # Attente fin de tout les threads
        try:
            for thread in thread_list:
                thread.join()
        except:
            print(cyan + "computePreTreatment() : " + bold + red + "computePreTreatment() : " + endC + "Erreur lors de le decoupe : impossible de demarrer le thread" + endC, file=sys.stderr)
            
    #print(input_table)
       
    # Initialisation de la liste pour le multi-threading
    thread_list = []            
    for i in range(rapport_modulo_CPU):
    
        #output_image = output_image_path_list[(rapport_division_CPU * number_CPU) + i]
        output_image = fillTableFiles(split_tile_vector_list[(rapport_division_CPU * number_CPU) + i], input_table, repertory_data_imagette_temp, "sat_", extension_raster)
        output_image_path_list.append(output_image)
        #print("Output Imuage :" + output_image)
        if debug >= 1 :
            print("Traitement de la tuile " + str(i+1) +"/"+ str(number_vector) + "...")
        if os.path.exists(split_tile_vector_list[(rapport_division_CPU * number_CPU) + i]):
        
            # Découpage de l'image par multi-threading
            thread = threading.Thread(target=cutImageByGrid, args=(split_tile_vector_list[rapport_division_CPU * number_CPU + i], image_input, output_image, image_dimension - (debord * pixel_size), image_dimension - (debord * pixel_size), debord, pixel_size, pixel_size, no_data_value, epsg, format_raster, format_vector))
            thread.start()
            thread_list.append(thread)

    # Attente fin de tout les threads
    try:
        for thread in thread_list:
            thread.join()
    except:
        print(cyan + "computePreTreatment() : " + bold + red + "computePreTreatment() : " + endC + "Erreur lors de le decoupe : impossible de demarrer le thread" + endC, file=sys.stderr)          
          
    if training_input != "" :

        # Découpage de l'image d'entrainement           
        for i in range(rapport_division_CPU):
            # Initialisation de la liste pour le multi-threading
            thread_list = []            
            for j in range(number_CPU):
    
                #output_train_img = output_train_image_path_list[(i * number_CPU) + j]
                output_train_image = fillTableFiles(split_tile_vector_list[(i * number_CPU) + j], training_table, repertory_data_train_temp, "train_", extension_raster)
                output_train_image_path_list.append(output_train_image)
                #print("Output Train Image :" + output_train_img)
                if debug >= 1 :
                    print("Traitement de la tuile " + str((i * number_CPU) + j) +"/"+ str(number_vector) + "...")
                # Découpage du masque
                if os.path.exists(split_tile_vector_list[(i * number_CPU) + j]):

                    # Découpage de l'image par multi-threading
                    thread = threading.Thread(target=cutImageByGrid, args=(split_tile_vector_list[i * number_CPU + j], training_input, output_train_image, image_dimension - (debord * pixel_size), image_dimension - (debord * pixel_size), debord, pixel_size, pixel_size, no_data_value, epsg, format_raster, format_vector))
                    thread.start()
                    thread_list.append(thread)

            # Attente fin de tout les threads
            try:
                for thread in thread_list:
                    thread.join()
            except:
                print(cyan + "computePreTreatment() : " + bold + red + "computePreTreatment() : " + endC + "Erreur lors de le decoupe : impossible de demarrer le thread" + endC, file=sys.stderr)

        # Initialisation de la liste pour le multi-threading
        thread_list = []
        for i in range(rapport_modulo_CPU):
        
            #output_train_img = output_train_image_path_list[rapport_division_CPU * number_CPU + i]
            
            output_train_image = fillTableFiles(split_tile_vector_list[(rapport_division_CPU * number_CPU) + i], training_table, repertory_data_train_temp, "train_", extension_raster)
            output_train_image_path_list.append(output_train_image)
            #print("Output Train Imuage :" + output_train_img)
            if debug >= 1 :
                print("Traitement de la tuile " + str(rapport_division_CPU * number_CPU + i) +"/"+ str(number_vector) + "...")
            if os.path.exists(split_tile_vector_list[rapport_division_CPU * number_CPU + i]):
                # Découpage de l'image par multi-threading
                thread = threading.Thread(target=cutImageByGrid, args=(split_tile_vector_list[rapport_division_CPU * number_CPU + i], training_input, output_train_image, image_dimension - (debord * pixel_size), image_dimension - (debord * pixel_size), debord, pixel_size, pixel_size, no_data_value, epsg, format_raster, format_vector))
                thread.start()
                thread_list.append(thread)

        # Attente fin de tout les threads
        try:
            for thread in thread_list:
                thread.join()
        except:
            print(cyan + "computePreTreatment() : " + bold + red + "computePreTreatment() : " + endC + "Erreur lors de le decoupe : impossible de demarrer le thread" + endC, file=sys.stderr)   
    
      
    return input_table, training_table, vector_simple_mask, split_tile_vector_list, repertory_vect_temp, repertory_data_temp

###########################################################################################################################################
# FONCTION reset_random_seeds()                                                                                                           #
###########################################################################################################################################
def reset_random_seeds(rand_seed):
   print("APPEL")
   os.environ['PYTHONHASHSEED']=str(rand_seed)
   tf.random.set_seed(rand_seed)
   np.random.seed(rand_seed)
   random.seed(rand_seed)
   
###########################################################################################################################################
# FONCTION computeTrain()                                                                                                                 #
###########################################################################################################################################
# ROLE:
#    Calcul de la matrice de confusion entre le masque de référence et la prédiction avec otbcli_ComputeConfusionMatrix
#    Récupération des résultats de cette commande dans un fichier .txt
#
# ENTREES DE LA FONCTION :
#    NN (structure) : structure contenant tout les paramètres propre au réseau de neurones
#    neural_network_mode (string) : nom du type de réseau de neurones
#    training_input (string) : l'image satellite d'apprentissage
#    image_input (string) : l'image satellite d'entrée
#    vector_input (string) : vecteur de découpe d'entrée
#    model_output (string) : chemin où stocker le réseau de neurones entrainé
#    image_output (string) : chemin où stocker l'image finale classifiée
#    size_grid (int) : dimension d'une cellule de la grille de découpe de l'image satellite initiale
#    augment_training (int) : booléen pour determiner si on augmente artificiellement le jeu de données par des rotations
#    number_class (int) : nombre de classes
#    debord (int) : utilisé pour éviter les effets de bord. Agrandit artificiellement les imagettes
#    path_time_log (string) : chemin du fichier de log
#    save_data (bool) : booléen pour determiner si on conserve ou non le dossier Data
#    overwrite (bool) : booléen pour écrire ou non par dessus un fichier existant
#    extension_raster (string) : extension de fichier des imagettes
#    extension_vector (string) : extension de fichier des vecteurs
#    format_raster (string) : format des imagettes
#    format_vector (string) : format des vecteurs
#    epsg (int) : Identificateur de SIG
#    save (int) : booléen qui determine si on sauvegarde ou non les fichiers temporaires
#
# SORTIES DE LA FONCTION :
#    Renvoie le modèle de sortie entraîné, la table des imagettes, l'emprise de l'image d'entrée, la liste des vecteurs de découpe ainsi que les noms des dossiers où sont stockés les vecteurs et imagettes
#
def computeTrain(NN, neural_network_mode, training_input, image_input, vector_input, model_output, image_output, size_grid, augment_training, number_class, debord, path_time_log, save_data, overwrite=True, extension_raster=".tif", extension_vector=".shp", format_raster='GTiff', format_vector='ESRI Shapefile', rand_seed=0, epsg=2154, save=False):
    
    # Constantes
    FOLDER_HISTORY = "_History_"
    FOLDER_MODEL = "Model"
    extension_neural_network = ".hdf5"

    # Récupération d'informations
    img_size = size_grid
    n_classes = number_class
    batch_size = NN.batch
    kernel_size = NN.kernel_size
    _, _, n_bands = getGeometryImage(image_input)
    n_filters = NN.number_conv_filter
    model_name = neural_network_mode

    # Récupére la date courante
    current_date = date.today().strftime("%d_%m_%Y")
    # Récupére le répertoire courant
    repertory = os.path.dirname(image_output)

    # Création du nom du fichier stockant le réseau de neurones que l'on entraine
    # Cas où l'utilisateur ne renseigne pas model_output
    if model_output == "" :
        # Récupération du nom du réseau
        model_file = image_output.split(os.sep)[-1]
        model_file_name = model_file.split(".")[0] 
        model_dir = repertory + os.sep + FOLDER_MODEL
        # Création du dossier History s'il n'existe pas
        if not os.path.isdir(model_dir):
            os.makedirs(model_dir)
            
        # Création du model output   
        model_save_dir = model_dir + os.sep + model_file_name + extension_neural_network
        model_path = model_save_dir
    else:

        # Récupération du nom du réseau
        model_file = model_output.split(os.sep)[-1]
        model_file_name = model_file.split(".")[0] 
        model_path = model_output

    
    # Determine le type de classification
    if n_classes == 1:
        type_class = '_mono_'
    else:
        type_class = '_multi_'

    

    history_dir = repertory + os.sep + model_name + FOLDER_HISTORY + model_file_name

    # Création du dossier History s'il n'existe pas
    if not os.path.isdir(history_dir):
        os.makedirs(history_dir)

    # Regarde si le fichier de log existe
    check_log = os.path.isfile(path_time_log)

    # Création du nom du fichier stockant l'historique de l'entrainnement (attention necessite d'avoir le dossier Model au même endroit que le dossier History)
    csv_filename = history_dir + os.sep + model_file_name + type_class + current_date + ".csv"
    csv_logger = CSVLogger(csv_filename)

    # Mise à jour du Log
    if check_log :
        pre_treatment_event = "Starting of pre-treatment : "
        timeLine(path_time_log, pre_treatment_event)
    
    # Récupération des imagettes et masques associés
    input_table, training_table, vector_mask, split_tile_vector_list, repertory_vect_temp, repertory_data_temp = computePreTreatment(NN,debord,neural_network_mode, model_path, training_input, image_input, vector_input, image_output, size_grid, overwrite, extension_raster, extension_vector, format_raster, format_vector, epsg)

    # CI-DESSUS A DECOMMENTER LORS DE L UTILISATION FINALE DE L APPLI
        
    ######################################################################################################
    """
    input_list = sorted(glob.glob("/mnt/RAM_disk/resunet_Data_Model_Deb6_Batch32_Filt8/Imagette_Model_Deb6_Batch32_Filt8/*"))
    training_list = sorted(glob.glob("/mnt/RAM_disk/resunet_Data_Model_Deb6_Batch32_Filt8/Train_Model_Deb6_Batch32_Filt8/*"))
    
    ligne_indice_list = []
    colonne_indice_list = []
    
    for f in input_list :
        # Récupération des dimensions des matrices
        sub_name = f.split(".")[0].split("_")[-1]
        find_ligne = sub_name.find("l")
        find_colonne = sub_name.find("c")
        nombre_ligne = int(sub_name[find_ligne+1:find_colonne])
        nombre_colonne = int(sub_name[find_colonne+1:])
        
        ligne_indice_list.append(nombre_ligne)
        colonne_indice_list.append(nombre_colonne)

    nombre_ligne = max(ligne_indice_list)
    nombre_colonne = max(colonne_indice_list)
    
    input_table = []
    training_table = []
    
    for i in range (nombre_ligne):
        input_table.append([""]*nombre_colonne)
        training_table.append([""]*nombre_colonne)

    for i in range (len(input_list)) :
        # Récupération des dimensions des matrices
        sub_name = input_list[i].split(".")[0].split("_")[-1]
        find_ligne = sub_name.find("l")
        find_colonne = sub_name.find("c")
        nombre_ligne = int(sub_name[find_ligne+1:find_colonne])
        nombre_colonne = int(sub_name[find_colonne+1:])
        
        input_table[nombre_ligne-1][nombre_colonne-1] = input_list[i]
        training_table[nombre_ligne-1][nombre_colonne-1] = training_list[i]
        
    
    # TO CHANGE
    vector_mask = "/mnt/RAM_disk/resunet_Vect_Model_Deb6_Batch32_Filt8/ORT_2017071337806444_LA93_stacked_vect_simplify.shp"   
    # TO CHANGE
    split_tile_vector_list = sorted(glob.glob("/mnt/RAM_disk/resunet_Data_Model_Deb6_Batch32_Filt8/Grid_Model_Deb6_Batch32_Filt8/*.shp"))
    # TO CHANGE
    repertory_vect_temp = "/mnt/RAM_disk/resunet_Vect_Model_Deb6_Batch32_Filt8"
    # TO CHANGE
    repertory_data_temp = "/mnt/RAM_disk/resunet_Data_Model_Deb6_Batch32_Filt8"
    """
    ######################################################################################################
     
    # Mise à jour du Log
    if check_log :
        ending_pre_treatment_event = "Ending of pre-treatment : "
        timeLine(path_time_log, ending_pre_treatment_event)
    
    # Copie de la matrice avant d'être modifiée car on veut la conserver intacte pour la phase de classification
    input_table_copy = copy.deepcopy(input_table)

                
 
    # Suppression de la derniere ligne et colonne de l'image pour éviter de faire apprendre sur des images avec beaucoup de nodata
    """
    del input_table[-1]
    del training_table[-1]

    for i in range(len(input_table)):
        input_table[i] = input_table[i][:-1]
        training_table[i] = training_table[i][:-1]
    """
    # Remplissage des listes et Suppression de toute image d'entrée ayant plus de 10% des px en nodata
    input_img_paths_list = []
    input_train_img_list = []
    pourcent_10 = int(((img_size*img_size) * 10) / 100)
    cpt_img_supprime = 0

    for i in range(len(input_table)):
        for j in range(len(input_table[0])):
        
            cpt_nodata = countPixelsOfValue(input_table[i][j],0)
            #cpt_nodata = countPixelsOfValueBis(input_table[i][j],0)
            if cpt_nodata < pourcent_10:
                input_img_paths_list.append(input_table[i][j])
                input_train_img_list.append(training_table[i][j])
            else:
                cpt_img_supprime = cpt_img_supprime + 1

    #for i in range(len(input_img_paths_list)):
        #print(input_img_paths_list[i])  
    if debug >=3:
        print("Nombres d'images et images d'entrainement supprimes :"+str(cpt_img_supprime))
        print("Nombres d'images :"+str(len(input_img_paths_list)))
        print("Nombres d'images d'entrainement :"+str(len(input_train_img_list)))
        print("Fin du prétraitement de l'image")

    # Séparation train | validation
    validation_idx = int(len(input_img_paths_list) * NN.validation_split)
    random.Random(1337).shuffle(input_img_paths_list)
    random.Random(1337).shuffle(input_train_img_list)
    train_input_img_paths = input_img_paths_list[:-validation_idx]
    train_target_mask_paths = input_train_img_list[:-validation_idx]
    val_input_img_paths = input_img_paths_list[-validation_idx:]
    val_target_mask_paths = input_train_img_list[-validation_idx:]

        
    # Chargement des données par lots de taille batch_size avec augmentation pour le train (générateur)
    train_gen = DataGenerator(batch_size, train_input_img_paths, train_target_mask_paths, augment_training, data_type = 'train')
    val_gen = DataGenerator(batch_size, val_input_img_paths, val_target_mask_paths, 0, data_type = 'train')
    
    # Chargement du modèle
    if model_name.lower() == "unet":
        if n_classes == 1:
            model = unet((img_size, img_size, n_bands), n_filters, n_classes, kernel_size, "mono")
        else:
            model = unet((img_size, img_size, n_bands), n_filters, n_classes, kernel_size, "multi")
    else:
        if n_classes == 1:
            model = resunet((img_size, img_size, n_bands), n_filters, n_classes, kernel_size, "mono")
        else:
            model = resunet((img_size, img_size, n_bands), n_filters, n_classes, kernel_size, "multi")
    
    # Outils pour l'apprentissage du modèle
    model_checkpoint = ModelCheckpoint(model_path, monitor = 'loss', verbose = 1, save_best_only = True)

    model_early_stopping = EarlyStopping(monitor = NN.es_monitor, patience = NN.es_patience, min_delta = NN.es_min_delta, verbose = NN.es_verbose, restore_best_weights = True)
    model_reducelronplateau = ReduceLROnPlateau(monitor = NN.rl_monitor, factor = NN.rl_factor, patience = NN.rl_patience, min_lr = NN.rl_min_lr, verbose =NN.rl_verbose, mode = 'min')

    callbacks = [model_checkpoint, model_early_stopping, model_reducelronplateau, csv_logger]

    # Mise à jour du Log
    if check_log :
        fitting_event = "Starting to fit model : "
        timeLine(path_time_log, fitting_event)

    # Apprentissage du modèle
    model.fit(train_gen, epochs = NN.number_epoch, verbose = 2, callbacks = callbacks, validation_data = val_gen)

    # Mise à jour du Log
    if check_log :
        ending_fitting_event = "Ending to fit model : "
        timeLine(path_time_log, ending_fitting_event)
        
    # Suppression des dossiers temporaires
    if not save :
        
        if debug >= 1 :
            print("Suppression des dossiers temporaires")
            
        try:
            shutil.rmtree(history_dir)
        except Exception:
            pass
        try:
            shutil.rmtree(repertory_vect_temp)
        except Exception:
            pass        
        
        if not save_data :
            try:
                shutil.rmtree(repertory_data_temp)
            except Exception:
                pass
            
   
    return model_path, input_table_copy, vector_mask, split_tile_vector_list, repertory_vect_temp, repertory_data_temp

###########################################################################################################################################
# FONCTION computeTest()                                                                                                                #
###########################################################################################################################################
# ROLE:
#    Prediction des différents résultats en imagettes et assemblage en une seule image
#
# ENTREES DE LA FONCTION :
#    NN (structure) : structure contenant tout les paramètres propre au réseau de neurones
#    neural_network_mode (string) : nom du type de réseau de neurones
#    model_input (string) : nom du réseau de neurones à utiliser pour classifier
#    training_input (string) : l'image satellite d'apprentissage
#    image_input (string) : l'image satellite d'entrée
#    vector_input (string) : vecteur de découpe d'entrée
#    image_output (string) : chemin où stocker l'image finale classifiée
#    size_grid (int) : dimension d'une cellule de la grille de découpe de l'image satellite initiale
#    number_class (int) : nombre de classes
#    debord (int) : utilisé pour éviter les effets de bord. Agrandit artificiellement les imagettes
#    overwrite (bool) : booléen pour écrire ou non par dessus un fichier existant
#    extension_raster (string) : extension de fichier des imagettes
#    extension_vector (string) : extension de fichier des vecteurs
#    format_raster (string) : format des imagettes
#    format_vector (string) : format des vecteurs
#    epsg (int) : Identificateur de SIG
#    no_data_value (int) : valeur que prend un pixel qui ne contient pas d'information 
#    save (bool) : booléen qui determine si on sauvegarde ou non les fichiers temporaires
#
# SORTIES DE LA FONCTION :
#    Aucune sortie
#
def computeTest(NN, neural_network_mode, model_input, training_input, image_input, vector_input, image_output, size_grid, input_table, vector_simple_mask, split_tile_vector_list, repertory_vect_temp, repertory_data_temp, number_class, debord, path_time_log, overwrite=True, extension_raster=".tif", extension_vector=".shp", format_raster='GTiff', format_vector='ESRI Shapefile', epsg=2154, no_data_value=0, save=False):

    # Création d'un dossier temporaire Prédiction
    FOLDER_PREDICTION = "_Predict_"
    FOLDER_CLASSIFICATION_IMAGETTES = "Classified_Imagettes"
    FOLDER_CLASSIFICATION_RESHAPE = "Resized_Classified_Imagettes"
    repertory = os.path.dirname(image_output)
    
    # Récupération du nom du réseau
    model_file = model_input.split(os.sep)[-1]
    model_file_name = model_file.split(".")[0]
    
    
    prediction_dir = repertory + os.sep + neural_network_mode + FOLDER_PREDICTION + model_file_name + os.sep
    classification_dir = prediction_dir + FOLDER_CLASSIFICATION_IMAGETTES + os.sep
    classification_resized_dir = prediction_dir + FOLDER_CLASSIFICATION_RESHAPE + os.sep

    # Création du dossier Predict s'il n'existe pas
    if not os.path.isdir(prediction_dir):
        os.makedirs(prediction_dir)
    # Création du dossier Classified_Imagettes s'il n'existe pas
    if not os.path.isdir(classification_dir):
        os.makedirs(classification_dir)
    # Création du dossier Predict s'il n'existe pas
    if not os.path.isdir(classification_resized_dir):
        os.makedirs(classification_resized_dir)
    
    # Regarde si le fichier de log existe
    check_log = os.path.isfile(path_time_log)
    
    # Dans le cas où l'on fait seulement une classification, il faut découper l'image d'entrée
    if len(input_table) == 0 or vector_simple_mask == "" or len(split_tile_vector_list) == 0 or repertory_vect_temp == "" or repertory_data_temp == "" :

        # Mise à jour du Log
        if check_log :
            pre_treatment_event = "Starting of pre-treatment : "
            timeLine(path_time_log, pre_treatment_event) 
           
        # Récupération des imagettes et masques associés
        input_table, _, vector_simple_mask, split_tile_vector_list, repertory_vect_temp, repertory_data_temp = computePreTreatment(NN, debord, neural_network_mode, model_input, training_input, image_input, vector_input, image_output, size_grid, overwrite, extension_raster, extension_vector, format_raster, format_vector, epsg)

        # Mise à jour du Log
        if check_log :
            ending_pre_treatment_event = "Ending of pre-treatment : "
            timeLine(path_time_log, ending_pre_treatment_event)  
          
    input_img_paths_list = []
    input_train_img_list = []

    for i in range(len(input_table)):
        for j in range(len(input_table[0])):
            input_img_paths_list.append(input_table[i][j])
            #input_train_img_list.append(training_table[i][j])
           
    # Récupération du nombre de bandes dans l'image
    _, _, n_bands = getGeometryImage(image_input)
    # Récupération de la taille des pixels
    pixel_size, _ = getPixelWidthXYImage(image_input)

    if debug >=3:
        print("Nombres d'images :"+str(len(input_img_paths_list)))
        print("Nombres d'images d'entrainement :"+str(len(input_train_img_list)))
        print("Fin du prétraitement de l'image")

    # Prédiction à partir d'un modèle
    # Chargement de toutes les images (générateur)
    if debug >= 1:
        print("Chargement de toutes les images")
    test_gen = DataGenerator(NN.batch, input_img_paths_list, input_train_img_list, 0, data_type = 'test')
    if debug >= 1:
        print("Fin du chargement de toutes les images")

    # Chargement d'un modèle déjà entraîné
    if debug >= 1:
        print("Chargement du modele entraine")
    model = keras.models.load_model(model_input)
    if debug >= 1:
        print("Fin du chargement du modèle")

    # Mise à jour du Log
    if check_log :
        predicting_event = "Starting to predict : "
        timeLine(path_time_log, predicting_event)
    
    # Prédiction sur toutes les données
    if debug >= 1:
        print("Debut de prediction")
    if(NN.test_in_one_block):
        predictionTestGenerator(model, test_gen, input_img_paths_list, classification_dir, pixel_size, size_grid)

    else:
        nb_mask = len(test_gen[0])
        
        """
        print("Nombre d'images a predire dans un lot :"+str(nb_mask))
        print("Nombre de lots : "+str(len(test_gen)))
        print("len(input_img_paths_list) mod nb_mask : "+str((len(input_img_paths_list))%nb_mask))
        nb_espace_dispo = len(test_gen)*nb_mask
        print("nb_espace_dispo : "+str(nb_espace_dispo))
        print("Nombres d'images a predire :"+str(len(input_img_paths_list)))
        """
        # Cas où il n'y aura aucune array vide transmise à Keras
        if (len(input_img_paths_list))%nb_mask != 0 :
        
            for i in range (len(test_gen)):
                if debug >= 1:
                    print("Test ", (i+1), "/", (len(test_gen)))
                predictionTestGenerator(model, test_gen[i], input_img_paths_list[i*nb_mask:i*nb_mask+nb_mask], classification_dir, pixel_size, size_grid)
        else:
            nb_lots_utile = int(len(input_img_paths_list)/nb_mask)
            for i in range (nb_lots_utile):
                if debug >= 1:
                    print("Test ", (i+1), "/", nb_lots_utile)
                predictionTestGenerator(model, test_gen[i], input_img_paths_list[i*nb_mask:i*nb_mask+nb_mask], classification_dir, pixel_size, size_grid)
        
    # Mise à jour du Log
    if check_log :
        ending_predicting_event = "Ending to predict : "
        timeLine(path_time_log, ending_predicting_event)
        
    if debug >= 1:
        print("Fin de prediction")
    
    # Récuperation dans une seule de l'ensemble des imagettes classifiees
    predict_img_list = []

    for f in os.listdir(classification_dir):
        predict_img_list.append(classification_dir + f)
    
    predict_img_list = sorted(predict_img_list)

    # Mise à jour du Log
    if check_log :
        assembly_event = "Starting to assembly : "
        timeLine(path_time_log, assembly_event)
    
    # Assemblage de l'image en une seule
    output_assembly = assemblyImages(NN, prediction_dir, classification_resized_dir, predict_img_list, image_output, vector_simple_mask, split_tile_vector_list, image_input, debord, no_data_value, epsg, extension_raster, format_vector, format_raster)

    # Mise à jour du Log
    if check_log :
        ending_assembly_event = "Ending to assembly : "
        timeLine(path_time_log, ending_assembly_event)
        
    if debug >= 1:
        print("Image complete stockee a :"+output_assembly)
        
    
    #Suppression des dossiers temporaires
    if not save :
        
        if debug >= 1 :
            print("Suppression des dossiers temporaires")
        try:
            shutil.rmtree(prediction_dir)
        except Exception:
            pass
            
        try:
            shutil.rmtree(repertory_vect_temp)
        except Exception:
            pass

        try:
            shutil.rmtree(repertory_data_temp)
        except Exception:
            pass
        
    
    # Mesures de performance
    
    # evaluate_prediction_mono(target_mask_paths, compute_quality_path, n_bands)
    # evaluate_prediction_multi(target_mask_paths, n_classes, n_bands)
    # computeMatrix(NN, n_bands, n_classes)


###########################################################################################################################################
# FONCTION computeNeuralNetwork()                                                                                                         #
###########################################################################################################################################
# ROLE:
#    Choix entre une simple classification ou entrainement, ou bien un enchainement des deux
#
# ENTREES DE LA FONCTION :
#    NN (structure) : structure contenant tout les paramètres propre au réseau de neurones
#    use_graphic_card (bool) : booléen qui determine si on utilise la GPU ou la CPU
#    id_graphic_card (int) : determine l'identifiant de la carte graphique à utiliser (int)
#    debug (int) : gère l'affichage dans la console pour aider au débogage
#    neural_network_mode (string) : nom du type de réseau de neurones
#    model_input (string) : nom du réseau de neurones à utiliser pour classifier
#    training_input (string) : l'image satellite d'apprentissage
#    image_input (string) : l'image satellite d'entrée
#    vector_input (string) : vecteur de découpe d'entrée
#    image_output (string) : chemin où stocker l'image finale classifiée
#    model_output (string) : chemin où stocker le modèle (réseau de neurones) une fois entraîné
#    augment_training (bool) : booléen qui determine si on procède à l'augmentation artificielle de données sur le jeu de donnée d'entrainement
#    size_grid (int) : dimension d'une cellule de la grille de découpe de l'image satellite initiale
#    number_class (int) : nombre de classes
#    debord (int) : utilisé pour éviter les effets de bord. Agrandit artificiellement les imagettes
#    overwrite (bool) : booléen pour écrire ou non par dessus un fichier existant
#    extension_raster (string) : extension de fichier des imagettes
#    extension_vector (string) : extension de fichier des vecteurs
#    format_raster (string) : format des imagettes
#    format_vector (string) : format des vecteurs
#    epsg (int) : Identificateur de SIG
#    no_data_value (int) : valeur que prend un pixel qui ne contient pas d'information 
#    save_results_intermediate (bool) : booléen qui determine si on sauvegarde ou non les fichiers temporaires
#
# SORTIES DE LA FONCTION :
#    Aucune sortie
#
def computeNeuralNetwork(NN,use_graphic_card, id_graphic_card, debug, neural_network_mode, model_input, training_input, image_input, vector_input, image_output, model_output, augment_training, size_grid, number_class, debord, path_time_log, overwrite=True, extension_raster=".tif", extension_vector=".shp", format_raster='GTiff', format_vector='ESRI Shapefile', rand_seed=0, epsg=2154, no_data_value=0, save_results_intermediate=False):
    
    # Nettoyer l'environnement si overwrite est à True
    if overwrite :
        
        FOLDER_PREDICTION = "_Predict_"
        FOLDER_HISTORY = "_History_"
        FOLDER_VECTOR = "_Vect_"
        FOLDER_DATA = "_Data_"
        
        # Récupération du nom de l'image de sortie ou du modèle de sortie qui sert à la création des noms des differents dossiers
        if model_output == "" :
            folder_end = image_output.split(os.sep)[-1]
            folder_end_name = folder_end.split(".")[0]
            repertory = os.path.dirname(image_output)
        else:
            folder_end = model_output.split(os.sep)[-1]
            folder_end_name = folder_end.split(".")[0]
            repertory = os.path.dirname(model_output)
        
        # Création des noms des différents dossiers
        vect_dir = repertory + os.sep + neural_network_mode + FOLDER_VECTOR + folder_end_name
        data_dir = repertory + os.sep + neural_network_mode + FOLDER_DATA + folder_end_name
        prediction_dir = repertory + os.sep + neural_network_mode + FOLDER_PREDICTION + folder_end_name
        history_dir = repertory + os.sep + neural_network_mode + FOLDER_HISTORY + folder_end_name
         

        # Si le dossier Vect existe deja et que overwrite est activé
        check = os.path.isdir(vect_dir)
        if check:
            print(bold + yellow + "Delete of Vect folder already existing" + endC)
            if check:
                try:
                    shutil.rmtree(vect_dir)
                except Exception:
                    pass # Si le dossier ne peut pas être supprimé, on suppose qu'il n'existe pas et on passe à la suite
                    
        # Si le dossier Data existe deja et que overwrite est activé
        check = os.path.isdir(data_dir)
        if check:
            print(bold + yellow + "Delete of Data folder already existing" + endC)
            if check:
                try:
                    shutil.rmtree(data_dir)
                except Exception:
                    pass # Si le dossier ne peut pas être supprimé, on suppose qu'il n'existe pas et on passe à la suite
                    
         # Si le dossier Predict existe deja et que overwrite est activé
        check = os.path.isdir(prediction_dir)
        if check:
            print(bold + yellow + "Delete of Predict folder already existing" + endC)
            if check:
                try:
                    shutil.rmtree(prediction_dir)
                except Exception:
                    pass # Si le dossier ne peut pas être supprimé, on suppose qu'il n'existe pas et on passe à la suite
                    
        # Si le dossier History existe deja et que overwrite est activé
        check = os.path.isdir(history_dir)
        if check:
            print(bold + yellow + "Delete of History folder already existing" + endC)
            if check:
                try:
                    shutil.rmtree(history_dir)
                except Exception:
                    pass # Si le dossier ne peut pas être supprimé, on suppose qu'il n'existe pas et on passe à la suite
                    
        # Si le fichier de log existe deja et que overwrite est activé
        check = os.path.isfile(path_time_log)
        if check:
            print(bold + yellow + "Delete of path_time_log file already existing" + endC)
            if check:
                try:
                    os.remove(path_time_log)
                except Exception:
                    pass # Si le dossier ne peut pas être supprimé, on suppose qu'il n'existe pas et on passe à la suite        
                    
    # Cas où on ne remplace pas
    else:
        if image_output != "":
            check = os.path.isfile(image_output)
            if check:
                raise NameError (cyan + "NeuralNetworkClassification : " + bold + red  + "File %s already exist!" %(image_output) + endC)
                exit()
        
                                             
    # Utilisation du CPU au lieu d'une GPU
    if use_graphic_card :
        os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
        os.environ["CUDA_VISIBLE_DEVICES"] = str(id_graphic_card)
    else:
        os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
        os.environ["CUDA_VISIBLE_DEVICES"] = ""    
    
    # Gestion du taux d'information affiché pour l'early stopping et le reduce learning rate en fonction de debug
    if debug >=3:
    
        NN.es_verbose = 2
        NN.rl_verbose = 2
        
    elif debug == 2 or debug == 1 :
    
        NN.es_verbose = 1
        NN.rl_verbose = 1
    
    else:

        NN.es_verbose = 0
        NN.rl_verbose = 0
    
    # Création du fichier de log
    if path_time_log != "" :
        open(path_time_log, 'a').close()
         
    # Regarde si le fichier de log existe
    check_log = os.path.isfile(path_time_log)   
    
    # Choix entre entrainement,classification ou les deux
    
    # Cas d'une simple classification
    if image_output != "" and model_input != "":
    
         if debug >=1:
            print("Début de la phase de classification")

         # Initialisation 
         input_table = []
         vector_simple_mask = ""
         split_tile_vector_list = []
         repertory_vect_temp = ""
         repertory_data_temp = ""
         
         # Mise à jour du Log
         if check_log : 
            starting_event = "Starting of classification : "
            timeLine(path_time_log, starting_event)
         
         # Classification            
         computeTest(NN, neural_network_mode, model_input, training_input, image_input, vector_input, image_output, size_grid, input_table, vector_simple_mask, split_tile_vector_list, repertory_vect_temp, repertory_data_temp, number_class, debord, path_time_log, overwrite, extension_raster, extension_vector, format_raster, format_vector, epsg, no_data_value, save_results_intermediate)

         # Mise à jour du Log
         if check_log :
            ending_event = "Ending of classification : "
            timeLine(path_time_log, ending_event)
         
         if debug >=1:
            print("Fin de la classification avec reseau de neurones")
            
    # Cas d'un entrainement puis classification             
    elif image_output != "" and model_input == "" and training_input != "":
    
         if debug >=1:
            print("Début de la phase d'entrainement")
 
         # Mise à jour du Log
         if check_log :
            starting_event = "Starting of training phase : "
            timeLine(path_time_log, starting_event)
         
         # Permet de ne pas supprimer le dossier temporaire Data
         save_data = True
         
         # Entrainement
         model_input_tmp, input_table, vector_simple_mask, split_tile_vector_list, repertory_vect_temp, repertory_data_temp = computeTrain(NN, neural_network_mode, training_input, image_input, vector_input, model_output, image_output, size_grid, augment_training, number_class, debord, path_time_log, save_data, overwrite, extension_raster, extension_vector, format_raster, format_vector, rand_seed, epsg, save_results_intermediate)

         if debug >=1:
            print("Fin de l'entrainement du réseau de neurones")
            print("Début de la phase de classification")
            
         # Mise à jour du Log
         if check_log :
            ending_training_starting_classification_event = "Ending of training phase and starting of classification : "
            timeLine(path_time_log, ending_training_starting_classification_event)
         
         # Classification           
         computeTest(NN, neural_network_mode, model_input_tmp, training_input, image_input, vector_input, image_output, size_grid, input_table, vector_simple_mask, split_tile_vector_list, repertory_vect_temp, repertory_data_temp, number_class, debord, path_time_log, overwrite, extension_raster, extension_vector, format_raster, format_vector, epsg, no_data_value, save_results_intermediate)

         # Mise à jour du Log
         if check_log :
            ending_event = "Ending of classification : "
            timeLine(path_time_log, ending_event)
         
         # Dans ce cas là s'il n'y a pas model_output de renseigné et qu'on ne save pas, on supprime le modèle entrainé
         if not save_results_intermediate and model_output == "":
            try:
                os.remove(model_input_tmp)
            except Exception:
                pass # Si le dossier ne peut pas être supprimé, on suppose qu'il n'existe pas et on passe à la suite                 
            
                
         if debug >=1:
            print("Fin de la classification avec reseau de neurones")
            
         
            
    # Cas d'un nouvel entrainement d'un réseau déjà existant
    elif model_input != "" and training_input != "":

        # Mise à jour du Log
        if check_log :
            starting_event = "Starting of training phase : "
            timeLine(path_time_log, starting_event)

        # Permet supprimer le dossier temporaire Data
        save_data = False
        
        # Entrainement              
        _,_,_,_,_,_ = computeTrain(NN, neural_network_mode, training_input, image_input, vector_input, model_output, image_output, size_grid, augment_training, number_class, debord, path_time_log, save_data, overwrite, extension_raster, extension_vector, format_raster, format_vector, rand_seed, epsg, save_results_intermediate)

        # Mise à jour du Log
        if check_log :
            ending_event = "Ending of training phase : "
            timeLine(path_time_log, starting_event)
            
    else :
        if debug >=1:
            print("Vous n'avez pas renseignés les éléments nécessaire à un entrainnement du réseau ou à une classification")
    
    # Clear la session
    keras.backend.clear_session()

###########################################################################################################################################
# MISE EN PLACE DU PARSER                                                                                                                 #
###########################################################################################################################################

# Code executé seulement dans le cas ou le script est lancé depuis une ligne de commande
# Il n'est pas executé lors d'un import NeuralNetworkClassification.py

# Exemple de lancement en ligne de commande pour entrainer un réseau de neurones:
#python3 NeuralNetworkClassification.py -mo /mnt/Donnees_Etudes/30_Stages/2020/DeepLearning_Romain/reseau_keras/Model/Test.hdf5 -i /mnt/Data/30_Stages_Encours/2021/DeepLearning_Leo/Test/Draguignan_zoneTest_georef_scriptannexe.tif -ti /mnt/Data/30_Stages_Encours/2021/DeepLearning_Leo/Test/Draguignan_zoneTest_maskAssembly_multi_georef_cut.tif -nc 6 -nm ResUnet


# Exemple de lancement en ligne de commande pour tester un réseau de neurones existant:
#python3 NeuralNetworkClassification.py -mi /mnt/Data/30_Stages_Encours/2021/DeepLearning_Leo/Test/Model/ResUnet_multi_26_04_2021_1.hdf5 -i /mnt/Data/30_Stages_Encours/2021/DeepLearning_Leo/Test/Draguignan_zoneTest_georef_scriptannexe.tif  -nc 6 -nm ResUnet -o /mnt/Data/30_Stages_Encours/2021/DeepLearning_Leo/Test/Resultat.tif


def main(gui=False):
    # Définition des arguments possibles pour l'appel en ligne de commande
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, prog="NeuralNetworkClassification", description="\
    Info : Classification supervisee  a l'aide de reseau de neurones. \n\
    Objectif : Execute une classification supervisee NN sur chaque pixels d'une images. \n\
    Exemple utilisation pour entrainer un reseau : python3 NeuralNetworkClassification.py  \n\
                                                           -mo /mnt/Donnees_Etudes/30_Stages/2020/DeepLearning_Romain/reseau_keras/Model/Test.hdf5 \n\
                                                           -i /mnt/Data/30_Stages_Encours/2021/DeepLearning_Leo/Test/Draguignan_zoneTest_georef_scriptannexe.tif \n\
                                                           -ti /mnt/Data/30_Stages_Encours/2021/DeepLearning_Leo/Test/Draguignan_zoneTest_georef_scriptannexe.tif \n\
                                                           -nc 6 \n\
                                                           -nm ResUnet\n\
    Exemple utilisation pour classifier avec un reseau : python3 NeuralNetworkClassification.py \n\
                                                           -mi /mnt/Donnees_Etudes/30_Stages/2020/DeepLearning_Romain/reseau_keras/Model/UNet_multi_31_03_2021_1.hdf5 \n\
                                                           -i /mnt/Data/30_Stages_Encours/2021/DeepLearning_Leo/Test/Draguignan_zoneTest_georef_scriptannexe.tif \n\
                                                           -o /mnt/Data/30_Stages_Encours/2021/DeepLearning_Leo/Test/Resultat_ResUnet.tif \n\
                                                           -nc 6 \n\
                                                           -nm ResUnet \n")

    # Paramètres
    

    # Directory path
    parser.add_argument('-i','--image_input',default="",help="Image input to classify", type=str, required=True)
    parser.add_argument('-ti','--training_input',default="",help="Training input (groundtruth)", type=str, required=False)
    parser.add_argument('-v','--vector_input',default="",help="Emprise vector of input image", type=str, required=False)
    parser.add_argument('-o','--image_output',default="",help="Image output classified", type=str, required=False)
    parser.add_argument('-mi','--model_input',default="",help="Neural Network already trained", type=str, required=False)
    parser.add_argument('-mo','--model_output',default="",help="Neural Network to train", type=str, required=False)

    # Input image parameters
    parser.add_argument('-sg','--size_grid',default=256,help="Size of study grid in pixels. Not used, if vector_grid_input is inquired", type=int, required=False)
    parser.add_argument('-at','--augment_training',action='store_true',default=False,help="Modify image and mask to artificially increase the data set", required=False)
    parser.add_argument('-deb','--debord',default=0,help="Reduce size of grid cells. Useful to avoid side effect",type=int, required=False)
    parser.add_argument('-ugc','--use_graphic_card',action='store_true',default=False,help="Use CPU for training phase", required=False)
    parser.add_argument('-igpu','--id_graphic_card',default=0,help="Id of graphic card used to classify", type=int, required=False)
    parser.add_argument('-nc','--number_class',default=0,help="Number of classes to classify", type=int, required=True)
    parser.add_argument('-nm','--neural_network_mode',default="Unet",help="Type of Neural Network (Unet | ResUnet)", type=str, required=True)

    # Hyperparameters NN
    parser.add_argument('-nn.b','--batch',default=32,help="Number of samples per gradient update", type=int, required=False)
    parser.add_argument('-nn.ncf','--number_conv_filter',default=8,help="Number of convolutional filters in one layer of Neural Network", type=int, required=False)
    parser.add_argument('-nn.ks','--kernel_size',default=3,help="Size of kernel in Neural Network", type=int, required=False)
    parser.add_argument('-nn.tiob','--test_in_one_block',default=0,help="During prediction of Neural Networks, predict all mask in one predict or several", type=int, required=False)
    parser.add_argument('-nn.vs','--validation_split',default=0.2,help="Share of the dataset dedicated to validation", type=float, required=False)
    
    parser.add_argument('-nn.ne','--number_epoch',default=200,help="Number of epoch to train the Neural Network", type=int, required=False)
    parser.add_argument('-nn.esm','--early_stopping_monitor',default="val_loss",help="Quantity to be monitored", type=str, required=False)
    parser.add_argument('-nn.esp','--early_stopping_patience',default=20,help="Number of epochs with no improvement after which training will be stopped", type=int, required=False)
    parser.add_argument('-nn.esmd','--early_stopping_min_delta',default=1e-7,help="An absolute change of less than min_delta, will count as no improvement", type=float, required=False)
    parser.add_argument('-nn.rlrm','--reduce_learning_rate_monitor',default="val_loss",help="Quantity to be monitored", type=str, required=False)
    parser.add_argument('-nn.rlrf','--reduce_learning_rate_factor',default=0.1,help="Factor by which the learning rate will be reduced", type=float, required=False)
    parser.add_argument('-nn.rlrp','--reduce_learning_rate_patience',default=10,help="Number of epochs with no improvement after which learning rate will be reduced", type=int, required=False)
    parser.add_argument('-nn.rlrmlr','--reduce_learning_rate_min_lr',default=1e-7,help="Threshold for measuring the new optimum, to only focus on significant changes.", type=float, required=False)
    


    # A CONSERVER
    parser.add_argument('-rand','--rand_seed',default=0,help="User defined seed for tensorflow random sample", type=int, required=False)
    parser.add_argument('-ram','--ram_otb',default=0,help="Ram available for processing otb applications (in MB)", type=int, required=False)
    parser.add_argument('-ndv','--no_data_value', default=0, help="Option : Value of the pixel no data. By default : 0", type=int, required=False)
    parser.add_argument('-epsg','--epsg', default=2154,help="Projection of the output file.", type=int, required=False)
    parser.add_argument('-raf','--format_raster', default="GTiff", help="Option : Format output image, by default : GTiff (GTiff, HFA...)", type=str, required=False)
    parser.add_argument('-vef','--format_vector', default="ESRI Shapefile",help="Format of the output file.", type=str, required=False)
    parser.add_argument('-rae','--extension_raster', default=".tif", help="Option : Extension file for image raster. By default : '.tif'", type=str, required=False)
    parser.add_argument('-vee','--extension_vector',default=".shp",help="Option : Extension file for vector. By default : '.shp'", type=str, required=False)
    parser.add_argument('-log','--path_time_log',default="",help="Name of log", type=str, required=False)
    parser.add_argument('-sav','--save_results_inter',action='store_true',default=False,help="Save or delete intermediate result after the process. By default, False", required=False)
    parser.add_argument('-now','--overwrite',action='store_false',default=True,help="Overwrite files with same names. By default, True", required=False)
    parser.add_argument('-debug','--debug',default=5,help="Option : Value of level debug trace, default : 3 ",type=int, required=False)
    args = displayIHM(gui, parser)

    # CREATION STRUCTURE
    NN = StructNnParameter()

    # RECUPERATION DES ARGUMENTS
   
    # Récupération du chemin contenant l'image d'entrée
    if args.image_input != None:
        image_input = args.image_input
        if image_input != "" and not os.path.isfile(image_input):
            raise NameError (cyan + "NeuralNetworkClassification : " + bold + red  + "File %s not exist!" %(image_input) + endC)

    # Récupération du chemin contenant l'image d'apprentissage
    if args.training_input != None:
        training_input = args.training_input
        if training_input != "" and not os.path.isfile(training_input):
            raise NameError (cyan + "NeuralNetworkClassification : " + bold + red  + "File %s not exist!" %(training_input) + endC)
            
    # Récupération du vecteur d'emprise sous forme de polygone
    if args.vector_input != None:
        vector_input = args.vector_input
        if vector_input != "" and not os.path.isfile(vector_input):
            raise NameError (cyan + "NeuralNetworkClassification : " + bold + red  + "File %s not exist!" %(vector_input) + endC)

    # Stockage de l'image classifiée
    if args.image_output != None:
        image_output = args.image_output
                    
    # Récupération du modèle déjà entrainé
    if args.model_input != None:
        model_input = args.model_input
        if model_input != "" and not os.path.isfile(model_input):
            raise NameError (cyan + "NeuralNetworkClassification : " + bold + red  + "File %s not exist!" %(model_input) + endC)

    # Récupération du modèle à entrainer
    if args.model_output != None:
        model_output = args.model_output

    # Récupération de la taille des images à découper
    if args.size_grid != None :
        size_grid = args.size_grid
        # Doit être une  puissance de 2
        #if not math.log2(size_grid).is_integer() :
            #raise NameError (cyan + "NeuralNetworkClassification : " + bold + red  + "%i not a correct size for an image!" %(size_grid) + endC)

    # Récupération d'un int utilisé comme un booléen pour savoir si on augmente artificiellement les données
    if args.augment_training != None :
        augment_training = args.augment_training
        if type(augment_training) != bool:
            raise NameError (cyan + "NeuralNetworkClassification : " + bold + red  + "augment_training takes False or True in input!" + endC)

    # Récupération du nombre d'échantillons qui passe dans le réseau avant une mise à jour des poids
    if args.debord != None :
        debord = args.debord
        if debord < 0 :
            raise NameError (cyan + "NeuralNetworkClassification : " + bold + red  + "0 and negative numbers not allowed!" + endC)
                        
    # Récupération d'un int utilisé comme un booléen pour savoir si on utilise ou non la CPU pour effectuer les calculs
    use_graphic_card = args.use_graphic_card
    if type(use_graphic_card) != bool:
        raise NameError (cyan + "NeuralNetworkClassification : " + bold + red  + "use_cpu takes False or True in input!" + endC)
        
    # Récupération de l'identifiant de la carte graphique à utiliser
    if args.id_graphic_card != None :
        id_graphic_card = args.id_graphic_card
        if (id_graphic_card < 0):
            raise NameError (cyan + "NeuralNetworkClassification : " + bold + red  + "%i not a correct number!" %(id_graphic_card) + endC)
               
    # Récupération du nombre de classes pour classifier avec le réseau
    # Ajoute une classe no_data lorsque l'on est dans une classification à plus d'une classe
    if args.number_class != None :
        if (args.number_class < 1):
            raise NameError (cyan + "NeuralNetworkClassification : " + bold + red  + "%i not a correct number of classes!" %(args.number_class) + endC)
            
        if args.number_class != 1 :
            # Ajout de la classe nodata
            number_class = args.number_class + 1 
            #number_class = args.number_class
        else :
            number_class = args.number_class 
    
    # Récupération du type de réseau de neurones
    if args.neural_network_mode != None:
        neural_network_mode = args.neural_network_mode
        if neural_network_mode.lower() != "resunet" and neural_network_mode.lower() != "unet" :
            raise NameError (cyan + "NeuralNetworkClassification : " + bold + red  + "Not a good name! (Resunet or Unet)" + endC)
 
    # Récupération du nombre d'échantillons qui passe dans le réseau avant une mise à jour des poids
    if args.batch != None :
        NN.batch = args.batch
        if NN.batch <= 0 :
            raise NameError (cyan + "NeuralNetworkClassification : " + bold + red  + "0 and negative numbers not allowed!" + endC)
        
    # Récupération du nombre de filtres convolutifs appliqués à chaque couche du réseau
    if args.number_conv_filter != None :
        NN.number_conv_filter = args.number_conv_filter
        if NN.number_conv_filter <= 0 :
            raise NameError (cyan + "NeuralNetworkClassification : " + bold + red  + "0 and negative numbers not allowed!" + endC)

    # Récupération du nombre de filtres convolutifs appliqués à chaque couche du réseau
    if args.kernel_size != None :
        NN.kernel_size = args.kernel_size
        if NN.kernel_size <= 0 :
            raise NameError (cyan + "NeuralNetworkClassification : " + bold + red  + "0 and negative numbers not allowed!" + endC)
                    
    # Récupération d'un int utilisé comme un booléen pour savoir si on fait la prediction en un seul appel (couteux en mémoire) ou en plusieurs appels
    if args.test_in_one_block != None :
        NN.test_in_one_block = args.test_in_one_block
        if not NN.test_in_one_block == 0 and not NN.test_in_one_block == 1:
            raise NameError (cyan + "NeuralNetworkClassification : " + bold + red  + "test_in_one_block takes 0 or 1 in input!" + endC)

    # Récupération d'un float entre 0 et 1 pour determiner la part de données utilisée pour la validation
    if args.validation_split != None :
        NN.validation_split = args.validation_split
        if NN.validation_split<0 or NN.validation_split>1:
            raise NameError (cyan + "NeuralNetworkClassification : " + bold + red  + "number must be between 0 and 1!" + endC)

    # Récupération du nombre d'époques pour entrainer le réseau
    if args.number_epoch != None :
        NN.number_epoch = args.number_epoch
        if NN.number_epoch <=0 :
            raise NameError (cyan + "NeuralNetworkClassification : " + bold + red  + "0 and negative numbers not allowed!" + endC)

    # Récupération de ceux qui doit être surveillé pour l'early stopping
    if args.early_stopping_monitor != None:
        NN.es_monitor = args.early_stopping_monitor

    # Récupération du nombre d'époque après lequel l'entrainement va s'arrêter s'il n'y a pas eu d'amélioration
    if args.early_stopping_patience != None :
        NN.es_patience = args.early_stopping_patience
        if NN.es_patience <=0 :
            raise NameError (cyan + "NeuralNetworkClassification : " + bold + red  + "0 and negative numbers not allowed!" + endC)

    # Récupération de la valeur minimale que peut atteindre le delta
    if args.early_stopping_min_delta != None :
        NN.es_min_delta = args.early_stopping_min_delta
        if NN.es_min_delta>1 or NN.es_min_delta<=0:
            raise NameError (cyan + "NeuralNetworkClassification : " + bold + red  + "number must be between 0 and 1!" + endC)

    # Récupération de ceux qui doit être surveillé pour le learning rate
    if args.reduce_learning_rate_monitor != None:
        NN.rl_monitor = args.reduce_learning_rate_monitor

    # Récupération d'un float qui determine de combien va être réduit le learning rate
    if args.reduce_learning_rate_factor != None :
        NN.rl_factor = args.reduce_learning_rate_factor
        # Doit être inférieur à 1 pour réduire
        if NN.rl_factor>=1 or NN.rl_factor<=0:
            raise NameError (cyan + "NeuralNetworkClassification : " + bold + red  + "number must be strictly between 0 and 1!" + endC)

    # Récupération du nombre d'époque après lequel le learning rate va diminuer s'il n'y a pas eu d'amélioration reduce_learning_rate_patience
    if args.reduce_learning_rate_patience != None :
        NN.rl_patience = args.reduce_learning_rate_patience
        if NN.rl_patience <=0 :
            raise NameError (cyan + "NeuralNetworkClassification : " + bold + red  + "0 and negative numbers not allowed!" + endC)

    # Récupération de la valeur minimale que peut atteindre le learning rate reduce_learning_rate_min_lr
    if args.reduce_learning_rate_min_lr != None :
        NN.rl_min_lr = args.reduce_learning_rate_min_lr
        if NN.rl_min_lr<=0:
            raise NameError (cyan + "NeuralNetworkClassification : " + bold + red  + "number must be above 0!" + endC)

    # A CONSERVER
    
    # Récupération du parametre rand
    if args.rand_seed != None:
        rand_seed = args.rand_seed
        
    # Récupération du parametre ram
    if args.ram_otb != None:
        ram_otb = args.ram_otb

    # Parametres de valeur du nodata
    if args.no_data_value!= None:
        no_data_value = args.no_data_value
        
    # Récupération de l'indice de projection
    if args.epsg != None:
        epsg = args.epsg
        
    # Paramètre format des images de sortie
    if args.format_raster != None:
        format_raster = args.format_raster

    # Paramètre format des vecteurs
    if args.format_vector != None:
        format_vector = args.format_vector

    # Récupération de l'extension des fichiers images
    if args.extension_raster != None:
        extension_raster = args.extension_raster
        
    # Récupération de l'extension des fichiers vecteurs
    if args.extension_vector != None:
        extension_vector = args.extension_vector

    # Récupération du nom du fichier log
    if args.path_time_log!= None:
        path_time_log = args.path_time_log

    # Ecrasement des fichiers
    if args.save_results_inter != None:
        save_results_intermediate = args.save_results_inter
        
    # Ecrit par dessus un fichier existant
    if args.overwrite!= None:
        overwrite = args.overwrite

    # Récupération de l'option niveau de debug
    if args.debug!= None:   
        debug = args.debug

    # Affichage des arguments récupérés
    if debug >= 3:
        print(bold + green + "Variables dans le parser" + endC)
        
        # Directory path
        print(cyan + "NeuralNetworkClassification : " + endC + "image_input : " + image_input + endC)
        print(cyan + "NeuralNetworkClassification : " + endC + "training_input : " + training_input + endC)
        print(cyan + "NeuralNetworkClassification : " + endC + "vector_input : " + vector_input + endC)
        print(cyan + "NeuralNetworkClassification : " + endC + "image_output : " + image_output + endC)
        print(cyan + "NeuralNetworkClassification : " + endC + "model_input : " + model_input + endC)
        print(cyan + "NeuralNetworkClassification : " + endC + "model_output : " + model_output + endC)

        print(cyan + "NeuralNetworkClassification : " + endC + "size_grid : " + str(size_grid) + endC)
        print(cyan + "NeuralNetworkClassification : " + endC + "augment_training : " + str(augment_training) + endC)
        print(cyan + "NeuralNetworkClassification : " + endC + "debord : " + str(debord) + endC)
        print(cyan + "NeuralNetworkClassification : " + endC + "use_graphic_card : " + str(use_graphic_card) + endC)
        print(cyan + "NeuralNetworkClassification : " + endC + "id_graphic_card : " + str(id_graphic_card) + endC)
        print(cyan + "NeuralNetworkClassification : " + endC + "number_class : " + str(number_class) + endC)
        print(cyan + "NeuralNetworkClassification : " + endC + "neural_network_mode : " + neural_network_mode + endC)
        
        # Hyperparameters NN
        print(cyan + "NeuralNetworkClassification : " + endC + "batch : " + str(NN.batch) + endC)
        print(cyan + "NeuralNetworkClassification : " + endC + "number_conv_filter : " + str(NN.number_conv_filter) + endC)
        print(cyan + "NeuralNetworkClassification : " + endC + "kernel_size : " + str(NN.kernel_size) + endC)
        print(cyan + "NeuralNetworkClassification : " + endC + "test_in_one_block : " + str(NN.test_in_one_block) + endC)
        print(cyan + "NeuralNetworkClassification : " + endC + "validation_split : " + str(NN.validation_split) + endC)
        print(cyan + "NeuralNetworkClassification : " + endC + "number_epoch : " + str(NN.number_epoch) + endC)
        print(cyan + "NeuralNetworkClassification : " + endC + "es_monitor : " + NN.es_monitor + endC)
        print(cyan + "NeuralNetworkClassification : " + endC + "es_patience : " + str(NN.es_patience) + endC)
        print(cyan + "NeuralNetworkClassification : " + endC + "es_min_delta : " + str(NN.es_min_delta) + endC)
        print(cyan + "NeuralNetworkClassification : " + endC + "rl_monitor : " + NN.rl_monitor + endC)
        print(cyan + "NeuralNetworkClassification : " + endC + "rl_factor : " + str(NN.rl_factor) + endC)
        print(cyan + "NeuralNetworkClassification : " + endC + "rl_patience : " + str(NN.rl_patience) + endC)
        print(cyan + "NeuralNetworkClassification : " + endC + "rl_min_lr : " + str(NN.rl_min_lr) + endC)

        # A CONSERVER
        print(cyan + "NeuralNetworkClassification : " + endC + "rand_seed : " + str(rand_seed) + endC)
        print(cyan + "NeuralNetworkClassification : " + endC + "ram_otb : " + str(ram_otb) + endC)
        print(cyan + "NeuralNetworkClassification : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "NeuralNetworkClassification : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "NeuralNetworkClassification : " + endC + "format_raster : " + format_raster + endC)
        print(cyan + "NeuralNetworkClassification : " + endC + "format_vector : " + format_vector + endC)
        print(cyan + "NeuralNetworkClassification : " + endC + "extension_raster : " + extension_raster + endC)
        print(cyan + "NeuralNetworkClassification : " + endC + "extension_vector : " + extension_vector + endC)
        print(cyan + "NeuralNetworkClassification : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "NeuralNetworkClassification : " + endC + "save_results_inter : " + str(save_results_intermediate) + endC)
        print(cyan + "NeuralNetworkClassification : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "NeuralNetworkClassification : " + endC + "debug : " + str(debug) + endC)

        # Appel de la fonction principale
        computeNeuralNetwork(NN,use_graphic_card, id_graphic_card, debug, neural_network_mode, model_input, training_input, image_input, vector_input, image_output, model_output, augment_training, size_grid, number_class, debord, path_time_log, overwrite, extension_raster, extension_vector, format_raster, format_vector, rand_seed, epsg, no_data_value, save_results_intermediate)
    
# ================================================

if __name__ == '__main__':
  main(gui=False)
