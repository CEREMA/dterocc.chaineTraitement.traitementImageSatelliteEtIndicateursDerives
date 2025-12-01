#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.               #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT QUI APPLIQUE UNE SEGMENTATION SEMANTIQUE PAR RESEAU DE NEURONES                                                                    #
#                                                                                                                                           #
#############################################################################################################################################

"""
Nom de l'objet : NeuralNetworkSegmentation.py
Objectif : exécute une segmentation via réseaux de neurones sur des images découpées d'une seule image satellite en se basant sur un réseau Encodeur/Decodeur type ResU-net
----------
Date de creation : 07/04/2025
----------
Origine : le script originel provient du regroupement de fichier du script NeuralNetworkClassification
-----------------------------------------------------------------------------------------------------
Modifications

------------------------------------------------------
"""

##### Import pour le prétraitement #####
import os
import numpy as np
import random
import math

import sys
from datetime import date
import time
import copy
import shutil

import geopandas as gpd
import concurrent.futures
import pandas as pd
import fiona

import glob,string,shutil,time,argparse, threading
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_log import timeLine
from Lib_operator import getExtensionApplication
from Lib_vector import simplifyVector, createGridVector, splitVector
from QualityIndicatorComputation import computeConfusionMatrix
from Lib_raster import createVectorMask, getNodataValueImage, getGeometryImage, getProjectionImage, updateReferenceProjection, cutImageByVector, getPixelWidthXYImage, countPixelsOfValue, cutImageByGrid
from Lib_text import appendTextFileCR

##### Import pour le modèle #####
import tensorflow as tf
import keras
from keras import ops
from keras.models import *
from keras.layers import *
from keras.optimizers import *
from keras.losses import *
from keras import backend as k_backend #WARNING
from keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau, CSVLogger, TensorBoard
from keras.saving import register_keras_serializable

#### Import pour la recherche paramétrique ####
import optuna

##### Import propre à Data Generator #####
from skimage import img_as_float32
from tifffile import imread
import cv2
import tempfile

##### Import propre à Prediction #####
from osgeo import gdal, gdalconst
from osgeo.gdalconst import *
from skimage import img_as_ubyte
from tqdm import tqdm

# Fixe des seed pour la reproductibilite
seed = 42
os.environ['PYTHONHASHSEED']=str(seed)
os.environ['KERAS_BACKEND'] = 'tensorflow'
keras.utils.set_random_seed(seed)
np.random.seed(seed)
random.seed(seed)
# os.environ['TF_XLA_FLAGS'] = '--tf_xla_enable_xla_devices=false'
# os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
# Gestion de la memoire gpu
from keras import mixed_precision
mixed_precision.set_global_policy('mixed_float16')

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 3

###########################################################################################################################################
# STRUCTURE StructNnParameter                                                                                                             #
###########################################################################################################################################

class StructNnParameter:
    """
    Structure contenant les paramètres du réseau.
    es = earlystopping et rl = reduce_lr
    """
    def __init__(self):
        self.batch = 0
        self.number_conv_filter = 0
        self.kernel_size = 0
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
        self.dp_rate = 0
        self.alpha_loss = 0.5

###########################################################################################################################################
#                                                                                                                                         #
# PARTIE DATAGENERATOR                                                                                                                    #
#                                                                                                                                         #
###########################################################################################################################################

class DataGenerator(keras.utils.Sequence):
    """ Génération des batches de données pour les mettre en entrée du réseau de neurones.
    Args:
        batch_size (int): Taille des batches de données.
        tiles_paths (List[str]): Chemins vers les imagettes.
        mask_paths (List[str]): Chemins vers les fichiers de masques correspondants.
        augmentation (bool): Si True, applique l'augmentation aux données d'entrainement.
        aug_factor (int) : Nombre d'imagettes modifiées générées par imagettes + l'originale.
        n_classes (int): Nombre de classes.
        data_type (str): Type de données ('train', 'valid', 'test').
        shuffle (bool, optional): Si True, mélange les données à chaque époque.
            Defaults to False.
        **kwargs: Arguments supplémentaires passés à la classe parent.
    """
    def __init__(self, batch_size, tiles_paths, mask_paths, augmentation, n_classes, data_type, shuffle = False, **kwargs):
        super().__init__(**kwargs)

        self.batch_size = batch_size
        self.tiles_paths = tiles_paths
        self.mask_paths = mask_paths
        self.augmentation = augmentation
        self.aug_factor = 4
        self.n_classes = n_classes
        self.data_type = data_type
        self.shuffle = shuffle

        # Initialisation des indices et mélange si nécessaire
        self.indices = np.arange(len(tiles_paths))
        if self.shuffle :
            np.random.shuffle(self.indices)

        # Pour les données de validation, on ne mélange qu'une seule fois au début
            if self.data_type == "valid" :
                self.shuffle = False
        return

    ###########################################################################################################################################
    # FONCTION on_epoch_end()                                                                                                                 #
    ###########################################################################################################################################
    def on_epoch_end(self):
        """
        Fonction appellée à la fin de chaque epoch pour remélanger les batchs des données d'entrainement
        """
        if self.shuffle:
            np.random.shuffle(self.indices)
        return

    ###########################################################################################################################################
    # FONCTION __len__()                                                                                                                      #
    ###########################################################################################################################################
    def __len__(self):
        """
        Redéfinition de la fonction __len__ . Retourne le nombre de batch par epoch
        """
        if self.augmentation :
            return (len(self.tiles_paths) * self.aug_factor) // self.batch_size + 1
        else :
            return (len(self.tiles_paths) // self.batch_size) + 1

    ###########################################################################################################################################
    # FONCTION __getitem__()                                                                                                                  #
    ###########################################################################################################################################
    def __getitem__(self, index):
        """Redéfinition de la fonction __getitem__ pour recupérer un lot d'images et de masques stockés à l'indice index
        Args:
            index (int): Taille des batches de données.
        Returns:
            Tuple[np.ndarray, Dict[str, np.ndarray]]:
                - `x` : Tableau contenant le batch d'images
                - `{'segmentation': y_true, 'gradient_map': y_grad}` : Dictionnaire contenant les masques de vérité terrain et les cartes de gradient initialisées à zéro
        """
        start_idx = index * self.batch_size

        if self.data_type == 'train' and self.augmentation:
            # Avec augmentation
            base_idx = start_idx // self.aug_factor
            end_idx = min(base_idx + (self.batch_size // self.aug_factor), len(self.tiles_paths))
            batch_indices = self.indices[base_idx:end_idx]
            batch_tiles_paths = [self.tiles_paths[i] for i in batch_indices]
            batch_mask_paths = [self.mask_paths[i] for i in batch_indices] if self.mask_paths else None
        else:
            # Sans augmentation ou pour valid/test
            end_idx = min(start_idx + self.batch_size, len(self.tiles_paths))
            batch_indices = self.indices[start_idx:end_idx]
            batch_tiles_paths = [self.tiles_paths[i] for i in batch_indices]
            batch_mask_paths = [self.mask_paths[i] for i in batch_indices] if self.mask_paths else None

        # Pour test, on ne renvoie que les images
        if self.data_type == 'test':
            images = [self.loadTiffImage(path) for path in batch_tiles_paths]
            return np.asarray(images, dtype=np.float32)

        # Pour train et valid, on renvoie les masques et les images
        images = []
        masks = []

        for i, img_path in enumerate(batch_tiles_paths):

            img = self.loadTiffImage(img_path)
            mask = self.loadTiffMask(batch_mask_paths[i], nb_classes = self.n_classes)

            # Ajouter l'original
            images.append(img)
            masks.append(mask)

            # Appliquer l'augmentation si nécessaire
            if self.augmentation and self.data_type == 'train':
                augmented_pairs = self.generate_augmentations(img, mask, self.aug_factor - 1)
                for aug_img, aug_mask in augmented_pairs:
                    images.append(aug_img)
                    masks.append(aug_mask)

        # Limiter au batch_size exact si nécessaire (après augmentation)
        if len(images) > self.batch_size:
            images = images[:self.batch_size]
            masks = masks[:self.batch_size]

        x = np.asarray(images, dtype=np.float32)
        y_true = np.asarray(masks, dtype=np.uint8)
        y_grad = np.zeros((len(masks),256,256,1), dtype=np.float32)

        return x, {'segmentation': y_true, 'gradient_map': y_grad}

    ###########################################################################################################################################
    # FONCTION generate_augmentations()                                                                                                        #
    ###########################################################################################################################################
    def generate_augmentations(self, image, mask, num_variants=2):
        """
        Génère plusieurs versions augmentées d'une même image.

        Args:
            image: Image d'entrée.
            mask: Masque correspondant.
            num_variants: Nombre de variantes à générer.
                Defaults to 2

        Returns:
            Liste de tuples (image_augmentée, masque_augmenté).
        """
        augmented_pairs = []

        # Cas monoclasse
        if mask.shape[2] <= 1 :
            last_transform = None

            # Génération des variantes.
            for _ in range(num_variants):
                img_copy = image.copy()
                mask_copy = mask.copy()
                transforms = ['flipv', 'fliph', 'rotation', 'channel', 'None']
                weights = [0.2, 0.2, 0.2, 0.3, 0.1]
                if last_transform is not None: # impossible d'appliquer deux fois de suite la même transformation.
                    idx = transforms.index(last_transform)
                    available_transforms = transforms[:idx] + transforms[idx+1:]
                    available_weights = weights[:idx] + weights[idx+1:]
                    sum_weights = sum(available_weights)
                    available_weights = [w / sum_weights for w in available_weights]
                else :
                    available_transforms = transforms
                    available_weights = weights

                transform = random.choices(available_transforms, weights = available_weights , k=1)[0]
                last_transform = transform

                if transform == "flipv" :
                    img_copy = np.flipud(img_copy)
                    mask_copy = np.flipud(mask_copy)

                elif transform == "fliph" :
                    img_copy = np.fliplr(img_copy)
                    mask_copy = np.fliplr(mask_copy)

                elif transform == "rotation" :
                    rotation = random.randint(0, 3)
                    img_copy = np.rot90(img_copy, rotation)
                    mask_copy = np.rot90(mask_copy, rotation)

                elif transform == "channel":
                    if len(img_copy.shape) > 2 and img_copy.shape[2] > 1:
                        channel_idx = random.choice([0,1,2]) # On ne modifie que les canaux RGB
                        factor = random.uniform(0.8, 1.2)
                        img_copy[:, :, channel_idx] = np.clip(img_copy[:, :, channel_idx] * factor, 0, 1)
                elif transform == "None":
                    pass
                augmented_pairs.append((img_copy, mask_copy))


        # Cas multiclasse, les masques sont oneHot encodés:
        else :
            last_transform = None

            for _ in range(num_variants):
                img_copy = tf.identity(image).numpy()
                mask_copy = tf.identity(mask).numpy()

                transforms = ['flipv', 'fliph', 'rotation', 'channel', 'None']
                weights = [0.2, 0.2, 0.2, 0.3, 0.1]

                if last_transform is not None:
                    idx = transforms.index(last_transform)
                    available_transforms = transforms[:idx] + transforms[idx+1:]
                    available_weights = weights[:idx] + weights[idx+1:]
                    sum_weights = sum(available_weights)
                    available_weights = [w / sum_weights for w in available_weights]
                else :
                    available_transforms = transforms
                    available_weights = weights

                transform = random.choices(available_transforms, weights = available_weights , k=1)[0]
                last_transform = transform

                if transform == "flipv" :
                    img_copy = np.flipud(img_copy)
                    mask_copy = np.flipud(mask_copy)

                elif transform == "fliph" :
                    img_copy = np.fliplr(img_copy)
                    mask_copy = np.fliplr(mask_copy)

                elif transform == "rotation" :
                    rotation = random.randint(0, 3)
                    img_copy = np.rot90(img_copy, rotation)
                    mask_copy = np.rot90(mask_copy, rotation)

                elif transform == "channel":
                    if len(img_copy.shape) > 2 and img_copy.shape[2] > 1:
                        channel_idx = random.choice([0,1,2]) # On ne modifie que les canaux RGB
                        factor = random.uniform(0.8, 1.2)
                        img_copy[:, :, channel_idx] = np.clip(img_copy[:, :, channel_idx] * factor, 0, 1)
                elif transform == "None" :
                    pass

                augmented_pairs.append((img_copy, mask_copy))
        return augmented_pairs

    ###########################################################################################################################################
    # FONCTION loadTiffImage()                                                                                                                #
    ###########################################################################################################################################
    def loadTiffImage(self, image_name):
        """ Charge une image TIFF et la convertie en tableau compatible avec l'entrée d'un réseau de neurone
        Args:
            image_name (str) : chemin vers le fichier TIFF à charger

        Returns :
            float_image (np.ndarray): Image convertie en tableau `float32`.

        """

        tiff_image = imread(image_name)
        float_image = img_as_float32(tiff_image)

        return float_image

    ###########################################################################################################################################
    # FONCTION loadTiffMask()                                                                                                                 #
    ###########################################################################################################################################
    def loadTiffMask(self, mask_name, nb_classes = 2):
        """Charge un masque TIFF et le converti en tableau compatible avec l'entrée d'un réseau de neurone.
        Si `nb_classes` est égal à 1 (cas monoclasse), le masque est mis au format uint8.
        Si `nb_classes` est > 1 (cas multiclasse), le masque est converti en encodage one-hot.

        Args:
            mask_name (str): Chemin du fichier TIFF contenant le masque.
            nb_classes (int, optional): Nombre de classes de segmentation. Par défaut 2.

        Returns:
            np.ndarray or tf.Tensor:
                - Si `nb_classes == 1` : Masque de forme (H, W, 1) et type uint8.
                - Si `nb_classes > 1` : Tensor one-hot encodé de forme (H, W, nb_classes) et type tf.uint8 par défaut.
        """
        if nb_classes == 1 :
            mask = imread(mask_name)
            mask = mask[..., np.newaxis]
            return mask.astype(np.uint8)

        else :
            mask = imread(mask_name)
            mask_onehot = tf.one_hot(mask, depth = nb_classes)
            return mask_onehot

###########################################################################################################################################
#                                                                                                                                         #
# PARTIE RESEAU DE NEURONE                                                                                                                #
#                                                                                                                                         #
###########################################################################################################################################

            ##########################################################################
            #                                                                        #
            #                              RESUNET                                   #
            #                                                                        #
            ##########################################################################
###########################################################################################################################################
# FONCTION gradient_map()                                                                                                                    #
###########################################################################################################################################
def sqrt_activation(x):
    """Fonction d'activation personnalisée.
    Args:
        x (tf.Tensor): Tenseur en entrée.

    Returns:
        tf.Tensor: racine carrée avec un facteur 1e-8 pour éviter les racines nulles
    """
    return tf.sqrt(x + 1e-8)


def gradient_map_block(x):
    """Extrait la carte des gradient de l'image d'entrée via un filtre de sobel.
    Args:
        x (tf.Tensor): Tenseur d'entrée de forme (batch_size, H, W, C).
    Returns:
        tf.Tensor: Carte de gradient normalisée, de forme (batch_size, H, W, 1) et valeurs dans [0, 1].
    """
    # Conversion en niveau de gris.
    if x.shape[-1] > 1:
        rgb_only = x[:, :, :, :3]
        rgb_to_gray = Conv2D(1, (1, 1), use_bias=False, trainable=False, name='rgb_to_gray')
        rgb_to_gray.build(rgb_only.shape)
        weights = np.array([0.2125, 0.7154, 0.0721]).reshape((1, 1, 3, 1))
        rgb_to_gray.set_weights([weights])

        gray = rgb_to_gray(rgb_only)
    else:
        gray = x

    # Filtres de Sobel.
    # Gradients horizontaux.
    sobel_x_kernel = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=np.float32)
    sobel_x_kernel = sobel_x_kernel.reshape(3, 3, 1, 1)

    sobel_x_layer = Conv2D(1, (3, 3), padding='same', use_bias=False, trainable=False, name='sobel_x')
    sobel_x_layer.build(gray.shape)
    sobel_x_layer.set_weights([sobel_x_kernel])
    grad_x = sobel_x_layer(gray)

    # Gradients verticaux.
    sobel_y_kernel = np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]], dtype=np.float32)
    sobel_y_kernel = sobel_y_kernel.reshape(3, 3, 1, 1)
    sobel_y_layer = Conv2D(1, (3, 3), padding='same', use_bias=False, trainable=False, name='sobel_y')
    sobel_y_layer.build(gray.shape)
    sobel_y_layer.set_weights([sobel_y_kernel])
    grad_y = sobel_y_layer(gray)

    # Norme du gradient.
    grad_x_squared = Multiply(name='grad_x_squared')([grad_x, grad_x])
    grad_y_squared = Multiply(name='grad_y_squared')([grad_y, grad_y])

    grad_sum = Add(name='grad_sum')([grad_x_squared, grad_y_squared])

    gradient_norm = Lambda(sqrt_activation, name='gradient_norm')(grad_sum)

    # Normalisation.
    gradient_map = Activation('sigmoid', name='gradient_sigmoid')(gradient_norm)

    return gradient_map

###########################################################################################################################################
# FONCTION cbam_block()                                                                                                                   #
###########################################################################################################################################
def cbam_block(x, reduction_ratio=16):
    """Crée un block d'attention CBAM (Convolutional Block Attention Module).
    Args:
        x (tf.Tensor) : tensor d'entrée.
        reduction_ratio (int) : ratio de réduction pour l'attention par canal.

    Returns:
        tf.Tensor : tenseur de sortie qui est le tenseur d'entrée multiplié aux cartes d'attention
    """

    # Attention par canaux (Channel attention)
    channel_axis = -1
    channels = x.shape[channel_axis]

    avg_pool = GlobalAveragePooling2D()(x)
    avg_pool = Reshape((1, 1, channels))(avg_pool)
    max_pool = GlobalMaxPooling2D()(x)
    max_pool = Reshape((1, 1, channels))(max_pool)

    dense1 = Dense(channels // reduction_ratio, activation='relu')
    dense2 = Dense(channels, activation='sigmoid')

    avg_out = dense2(dense1(avg_pool))
    max_out = dense2(dense1(max_pool))

    channel_attention = Add()([avg_out, max_out])
    x = Multiply()([x, channel_attention])

    # Attention spatiale (Spatial Attention)
    avg_pool_spatial = keras.ops.mean(x, axis=-1, keepdims=True)
    max_pool_spatial = keras.ops.max(x, axis=-1, keepdims=True)

    spatial_input = Concatenate(axis=-1)([avg_pool_spatial, max_pool_spatial])

    spatial_input = keras.ops.pad(spatial_input, [[0, 0], [3, 3], [3, 3], [0, 0]], mode='REFLECT')
    spatial_attention = Conv2D(1, kernel_size=7, padding='valid', activation='sigmoid')(spatial_input)

    x = Multiply()([x, spatial_attention])

    return x

###########################################################################################################################################
# FONCTION convBlock()                                                                                                                    #
###########################################################################################################################################
def convBlock(x, n_filters, kernel_size = 3, strides = 1, use_cbam = False):
    """ Crée un bloc convolutionnel composé d'une normalisation par batch, d'une activation ReLu, d'un padding miroir et parfois un block d'attention CBAM.
    Args:
        x (tf.Tensor): Tenseur d'entrée.
        n_filters (int): Nombre de filtres (canaux).
        kernel_size (int): Taille du noyau de convolution.
            Defaults to 3
        strides (int): Pas de déplacement du filtre convolutionnel.
            Défaults to 1
        use_cbam (bool): Si True, applique un bloc d'attention CBAM après la convolution.
            Defaults to False.

    Returns:
        tf.Tensor: Tenseur transformé.
    """
    x = BatchNormalization()(x)
    x = Activation('relu')(x)

    # Application du padding miroir.
    pad_size = kernel_size // 2
    if kernel_size % 2 == 0:
        pad_size -= 1
    if pad_size > 0:
        x = keras.ops.pad(x, [[0, 0], [pad_size, pad_size], [pad_size, pad_size], [0, 0]], mode='REFLECT')


    x = Conv2D(n_filters, kernel_size, strides=strides, kernel_initializer="he_normal")(x)

    if use_cbam :
        x = cbam_block(x)

    return x

###########################################################################################################################################
# FONCTION inputBlock()                                                                                                                   #
###########################################################################################################################################
def inputBlock(x, n_filters, kernel_size = 3, strides = 1):
    """ Crée le premier bloc de convolution en entrée du réseau.
    Args :
        x (tf.Tensor) : Soit l'image en entrée du réseau de neurones.
        n_filters (int) : Nombre de filtres présents pour chaque couche convolutive.
        kernel_size (int) : Taille des filtres.
            Defaults to 3.
        strides (int) : Pas de déplacement du filtre convolutionnel.
            Defaults to 1.

    Returns:
        tf.Tensor: Tenseur transformé après passage par les couches du bloc d'entrée.
    """
    # Application du padding miroir
    pad_size = kernel_size // 2
    if kernel_size % 2 == 0:
        pad_size -= 1
    if pad_size > 0:
        x = keras.ops.pad(x, [[0, 0], [pad_size, pad_size], [pad_size, pad_size], [0, 0]], mode='REFLECT')


    conv = Conv2D(n_filters, kernel_size, strides = strides, kernel_initializer="he_normal")(x)
    conv = convBlock(conv, n_filters, kernel_size,strides)


    x_skip = Conv2D(n_filters, kernel_size = 3, strides = strides, kernel_initializer="he_normal")(x)
    x_skip = BatchNormalization()(x_skip)

    add = Add()([conv, x_skip])

    return add

###########################################################################################################################################
# FONCTION residualBlock()                                                                                                                #
###########################################################################################################################################
def residualBlockDown(x, n_filters, kernel_size = 3, strides = 1, ):
    """ Crée un block résiduel de l'encodeur.
    Args:
        x (tf.Tensor): Tenseur d'entrée.
        n_filters (int): Nombre de filtres pour chaque convolution.
        kernel_size (int): Taille du noyau convolutionnel.
            Defaults to 3.
        strides (int): Pas de déplacement du filtre, utilisé ici pour réduire la taille.
            Defaults to 1.

    Returns:
        tf.Tensor: Tenseur transformé après addition de la branche principale et de la branche résiduelle.
    """

    res = convBlock(x, n_filters, kernel_size, strides)
    res = convBlock(res, n_filters, kernel_size, 1)

    # Application du padding miroir
    pad_size = kernel_size // 2
    if kernel_size % 2 == 0:
        pad_size -= 1
    if pad_size > 0:
        x = keras.ops.pad(x, [[0, 0], [pad_size, pad_size], [pad_size, pad_size], [0, 0]], mode='REFLECT')


    x_skip = Conv2D(n_filters, kernel_size, strides = strides, kernel_initializer="he_normal")(x)
    x_skip = BatchNormalization()(x_skip)
    add = Add()([x_skip, res])

    return add

###########################################################################################################################################
# FONCTION residualBlockUp()                                                                                                              #
###########################################################################################################################################
def residualBlockUp(x, n_filters,  dropout_rate = 0.5, kernel_size = 3, strides = 1):
    """ Crée un block résiduel du decodeur.
    Args:
        x (tf.Tensor): Tenseur d'entrée.
        n_filters (int): Nombre de filtres pour chaque convolution.
        dropout_rate (float) : Taux de dropout
            Defaults to 0.5.
        kernel_size (int): Taille du noyau convolutionnel.
            Defaults to 3.
        strides (int): Pas de déplacement du filtre.
            Defaults to 1.

    Returns:
        tf.Tensor: Tenseur transformé après addition de la branche principale et de la branche résiduelle.
    """

    res = convBlock(x, n_filters, kernel_size, strides)

    # Ajout du SpatialDropout dans le deuxième block de convolution.
    res = BatchNormalization()(res)
    res = SpatialDropout2D(dropout_rate)(res)
    res = Activation('relu')(res)

    pad_size = kernel_size // 2
    if kernel_size % 2 == 0:
        pad_size -= 1
    if pad_size > 0:
        res = keras.ops.pad(res, [[0, 0], [pad_size, pad_size], [pad_size, pad_size], [0, 0]], mode='REFLECT')
        x = keras.ops.pad(x, [[0, 0], [pad_size, pad_size], [pad_size, pad_size], [0, 0]], mode='REFLECT')
    res = Conv2D(n_filters, kernel_size, strides=strides, kernel_initializer="he_normal")(res)

    x_skip = Conv2D(n_filters, kernel_size, strides = strides, kernel_initializer="he_normal")(x)
    x_skip = BatchNormalization()(x_skip)

    add = Add()([x_skip, res])

    return add

###########################################################################################################################################
# FONCTION resunet()                                                                                                                      #
###########################################################################################################################################
def resunet(input_size, n_filters, dropout_rate, alpha_loss, n_classes, kernel_size, mode, use_cbam = True,use_gradient_map = True):
    """
    Construit une architecture de type ResU-net avec possibilité d'attention (CBAM) et intégration de cartes de gradients.

    Cette version est inspirée de :
    - [1] Diakogiannis et al., 2019 (https://arxiv.org/pdf/1904.00592.pdf)
    - [2] Kaggle kernel ResUNet (https://www.kaggle.com/ekhtiar/lung-segmentation-cropping-resunet-tf)

    Elle est adaptée pour la segmentation binaire ("mono") ou multi-classe ("multi").

    Args:
        input_size (int or tuple): Dimensions de l'image d'entrée
        n_filters (int): Nombre de filtres de base (multiplié à chaque bloc de profondeur).
        dropout_rate (float): Taux de dropout.
        alpha_loss (float): Paramètre alpha pour pondérer les classes dans la focal Loss.
        n_classes (int): Nombre de classes.
        kernel_size (int): Taille des noyaux de convolution.
        mode (str): "mono" pour segmentation monoclasses ou "multi" pour segmentation multi-classe.
        use_cbam (bool, optional): Si True, ajoute un bloc CBAM (attention) dans les blocs de convolution.
            Defaults to True.
        use_gradient_map (bool, optional): Si True, génère une carte de gradient pour guider le centre du réseau.
            Defaults to True.

    Returns:
        keras.Model: Modèle Keras compilé.
    """

    inputs = Input(input_size)
    gradient_map= None

    # Generation des cartes de contour
    if use_gradient_map:
        gradient_map = gradient_map_block(inputs)

    # Encodeur
    block_down = inputBlock(inputs, n_filters, kernel_size)

    res_down1 = residualBlockDown(block_down, n_filters * 2, kernel_size = kernel_size, strides = 2)
    res_down2 = residualBlockDown(res_down1, n_filters * 4, kernel_size = kernel_size, strides = 2)

    # Espace Latent
    middle_block1 = convBlock(res_down2, n_filters * 8, kernel_size = kernel_size, strides = 2,  use_cbam = use_cbam)
    middle_block2 = convBlock(middle_block1, n_filters * 8, kernel_size = kernel_size,  use_cbam = use_cbam)

    # Attention grace aux cartes de gradient
    if use_gradient_map:
        x_resized = AveragePooling2D(pool_size=(2, 2), name='attention_pool_1')(gradient_map)
        x_resized = AveragePooling2D(pool_size=(2, 2), name='attention_pool_2')(x_resized)
        gradient_map_resized = AveragePooling2D(pool_size=(2, 2), name='attention_pool_3')(x_resized)
        middle_block3 = Multiply(name='latent_gradient_multiply')([middle_block2, gradient_map_resized])

    # Decodeur
    up1 = UpSampling2D(size = (2, 2))(middle_block3)
    concat1 = Concatenate()([res_down2, up1])
    res_up1 = residualBlockUp(concat1, n_filters * 4, dropout_rate, kernel_size)
    up2 = UpSampling2D(size = (2, 2))(res_up1)
    concat2 = Concatenate()([res_down1, up2])
    res_up2 = residualBlockUp(concat2, n_filters * 2, dropout_rate,  kernel_size)
    up3 = UpSampling2D(size = (2, 2))(res_up2)
    concat3 = Concatenate()([block_down, up3])
    res_up3 = residualBlockUp(concat3, n_filters, dropout_rate,  kernel_size)


    metrics = ['accuracy']

    # Couche de sortie/de classification
    if mode == "mono":
        outputs = Conv2D(n_classes, kernel_size = 1, activation='sigmoid', dtype='float32', name ='segmentation')(res_up3)
        gradient_map = Activation("linear",  name='gradient_map')(gradient_map)
        model = Model(inputs = inputs, outputs = [outputs, gradient_map])
        loss = {'segmentation' : CombinedLoss(n_classes = n_classes, alpha =0.75 ), 'gradient_map': None}
        model.compile(optimizer = AdamW(learning_rate = 1e-3, clipnorm=1.0), loss = loss, metrics = {'segmentation': metrics})

    else:
        output = Conv2D(n_classes, kernel_size = 1, activation = 'softmax', dtype='float32', name='segmentation')(res_up3)
        gradient_map = Activation("linear",  name='gradient_map')(gradient_map)

        model = Model(inputs = inputs, outputs = [output, gradient_map])
        loss = {'segmentation' : CombinedLoss(alpha = alpha_loss), 'gradient_map': None}
        model.compile(optimizer = AdamW(learning_rate = 1e-3,clipnorm=1.0), loss = loss, metrics = {'segmentation': metrics})
    return model

###########################################################################################################################################
# CLASSE DiceLossMulti()   & CombinedLoss()                                                                                               #
###########################################################################################################################################
@register_keras_serializable()
class DiceLossMulti(keras.losses.Loss):
    def __init__(self, smooth=1e-6, reduction='sum_over_batch_size', name='dice_loss', **kwargs):
        super().__init__(reduction = reduction, name = name)
        self.smooth = smooth

    def call(self, y_true, y_pred):

        # Applanissement pour calculer les sommes. On passe de (batch, H,W,C) à (nb_pixel, C)
        y_true_flat = tf.reshape(y_true, [-1, tf.shape(y_true)[-1]])
        y_pred_flat = tf.reshape(y_pred, [-1, tf.shape(y_pred)[-1]])

        # Calcul de l'intersection et de l'union pour chaque classe
        intersection = tf.reduce_sum(y_true_flat * y_pred_flat, axis=0)
        union = tf.reduce_sum(y_true_flat, axis=0) + tf.reduce_sum(y_pred_flat, axis=0)

        # Calcul du coefficient de Dice pour chaque classe
        dice_coeff = (2. * intersection + self.smooth) / (union + self.smooth)

        dice_loss = 1. - dice_coeff

        log_cosh_loss=tf.math.log(tf.math.cosh(dice_loss))

        # Moyenne sur toutes les classes
        return tf.reduce_mean(log_cosh_loss)

@register_keras_serializable()
class CombinedLoss(keras.losses.Loss):
    def __init__(self, n_classes = 2, smooth=1e-6, dice_weight = 0.5, focal_weight= 0.5, alpha = 0.75, gamma = 2.0, reduction='sum_over_batch_size', name='combined_loss', **kwargs):
        super().__init__(reduction = reduction, name = name, **kwargs)
        self.dice_weight = dice_weight
        self.focal_weight = focal_weight
        self.dice_loss = DiceLossMulti(smooth=smooth)
        if n_classes == 1 :
            self.focal_loss = BinaryFocalCrossentropy(apply_class_balancing=True, alpha=alpha, gamma=gamma)
        else :
            self.focal_loss = CategoricalFocalCrossentropy(alpha=alpha, gamma=gamma)

    def call(self, y_true, y_pred):
        dice = self.dice_loss(y_true, y_pred)
        focal = self.focal_loss(y_true, y_pred)
        return self.dice_weight * dice + self.focal_weight*focal

###########################################################################################################################################
#                                                                                                                                         #
# PARTIE PREDICTION (génération des résultats)                                                                                            #
#                                                                                                                                         #
###########################################################################################################################################

###########################################################################################################################################
# FONCTION changeNodataInPrediction()                                                                                                     #
###########################################################################################################################################
def changeNodataInPrediction(mask, complete_background, size_grid):
    """
    # Cas d'une classification multi-classe avec complete_background = True:
    #    Changement du masque prédit en enlevant la classe no_data. Les pixels ayant la classe no_data attribué ont maintenant la deuxième classe la plus probable
    #
    # Args:
    #    mask (array) : un masque résultant d'un keras.predict()
    #    size_grid (int) : définis la dimension des imagettes
    #
    # Returns:
    #    Le masque et la carte de confiance
    #
    """

    new_mask = np.zeros((mask.shape[0], mask.shape[1], 1), dtype = np.uint8)
    confidence_map = np.zeros((mask.shape[0], mask.shape[1], 1), dtype = np.float32)
    nb_px_change_classif = 0

    for i in range(size_grid):
        for j in range(size_grid):
            temp = mask[i,j]
            new_mask[i,j] = np.argmax(temp)
            confidence_map[i,j] = np.amax(temp)

            # Dans le cas d'un OCS complete, l'option complete_background doit être activée et les pixels prédits comme background deviendront la 2ème classe la plus probable.
            if np.argmax(temp) == 0 and complete_background:
                temp = np.delete(temp,0)
                new_mask[i,j] = np.argmax(temp) + 1
                nb_px_change_classif += 1

    if debug >= 5 and nb_px_change_classif != 0:
        print(cyan + "changeNodataInPrediction() : " + endC + "nombre de pixels dont on a pris la deuxieme classe la plus probable : "+str(nb_px_change_classif))

    return new_mask, confidence_map

###########################################################################################################################################
# FONCTION savePredictedMaskAsRasterGenerator()                                                                                           #
###########################################################################################################################################
def savePredictedMaskAsRasterGenerator(predicted_mask, gradient_maps, filenames, prediction_dir, confidence_dir, gradient_dir, pixel_size, size_grid, format_raster, save_confidence, complete_background):
    """
    #  Création des fichiers pour y stocker les masques obtenus après la prédiction du réseau de neurones.
    #
    # Args:
    #    predicted_mask (list) : la liste des masques obtenus après le keras.predict()
    #    filenames (list) : la liste des noms des fichiers (chemins)
    #    prediction_dir (string) : le chemin pour sauvegarder les masques
    #    pixel_size (int) : taille d'un pixel
    #    size_grid (int) : définis la dimension des imagettes
    #
    # Returns:
    #    Aucune sortie
    #
    """
    no_of_bands = predicted_mask[0].shape[2]
    height = predicted_mask[0].shape[1]
    width = predicted_mask[0].shape[0]
    j=0
    with tqdm(total = len(filenames)) as pbar:
        for filename in filenames:

            mask = predicted_mask[j]
            mask_name = filename.split(os.sep)[-1]
            output_name = prediction_dir + mask_name
            if no_of_bands != 1:

                mask, confidence_map = changeNodataInPrediction(mask, complete_background, size_grid)

                if save_confidence :
                    output_name_confidence = confidence_dir + mask_name
                if gradient_maps is not None:
                    gradient_map = gradient_maps[j]
                    output_name_gradient = gradient_dir + mask_name
            else:
                confidence_map = mask.copy()
                mask[mask >= 0.5] = 1
                mask[mask < 0.5] = 0

                if save_confidence:
                    output_name_confidence = confidence_dir + mask_name

                if gradient_maps is not None:
                    gradient_map = gradient_maps[j]
                    output_name_gradient = gradient_dir + mask_name

            source_ds = gdal.Open(filename, GA_ReadOnly)
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

            driver = gdal.GetDriverByName(format_raster)
            target_ds = driver.Create(output_name, width, height, 1, GDT_Byte)
            target_ds.SetGeoTransform(geotransform)
            target_ds.SetProjection(source_projection)
            mask = mask.squeeze()
            band = target_ds.GetRasterBand(1)
            band.WriteArray(mask)

            if save_confidence:
                target_ds_confidence = driver.Create(output_name_confidence, width, height, 1, GDT_Float32)
                target_ds_confidence.SetGeoTransform(geotransform)
                target_ds_confidence.SetProjection(source_projection)

                confidence_squeezed = confidence_map.squeeze()
                band_confidence = target_ds_confidence.GetRasterBand(1)
                band_confidence.WriteArray(confidence_squeezed)

                # Fermeture du dataset de confiance
                target_ds_confidence = None
                band_confidence = None

            save_gradient=True
            if save_gradient:
                target_ds_gradient = driver.Create(output_name_gradient, width, height, 1, GDT_Float32)
                target_ds_gradient.SetGeoTransform(geotransform)
                target_ds_gradient.SetProjection(source_projection)

                gradient_squeezed = gradient_map.squeeze()
                band_gradient = target_ds_gradient.GetRasterBand(1)
                band_gradient.WriteArray(gradient_squeezed)

                # Fermeture du dataset de confiance
                target_ds_gradient = None
                band_gradient = None

            source_ds = None
            target_ds = None
            band = None
            j = j+1
            pbar.update(1)

    return
###########################################################################################################################################
# FONCTION predictionTestGenerator()                                                                                                      #
###########################################################################################################################################
def predictionTestGenerator(model, test_gen, filenames, prediction_dir, confidence_dir, gradient_dir, pixel_size, size_grid, format_raster, save_confidence, complete_background):
    """
    #    Prédiction sur les données d'évaluation et stockage dans des fichiers .tiff.
    #
    # Args :
    #    model (string) : le modèle (réseau de neurones) entrainé
    #    test_gen (array list) : les données à tester (issues de DataGenerator)
    #    filenames (list) : la liste des noms des fichiers (chemins)
    #    prediction_dir (string) : le chemin pour sauvegarder les prédictions
    #    pixel_size (int) : taille d'un pixel
    #    size_grid (int) : définis la dimension des imagettes
    #    format_raster (string) : format des imagettes
    #
    # Returns :
    #    Aucune sortie
    #
    """
    pred_test, gradient_maps = model.predict(test_gen)
    savePredictedMaskAsRasterGenerator(pred_test,gradient_maps, filenames, prediction_dir, confidence_dir, gradient_dir, pixel_size, size_grid, format_raster, save_confidence, complete_background)

    return

###########################################################################################################################################
#                                                                                                                                         #
# PARTIE FONCTION SECONDAIRES                                                                                                             #
#                                                                                                                                         #
###########################################################################################################################################

#########################################################################
# FONCTION createFileOutputImagette()                                   #
#########################################################################
def createFileOutputImagette(file_grid_temp, file_imagette, classification_resized_dir, extension_raster):
    """
    # Crée le chemin du fichier de sortie correspondant à une imagette redimensionnée
    #
    # Args:
    #    file_grid_temp (string) : fichier de découpe de l'imagette
    #    file_imagette (string) : fichier de l'imagette classifiée
    #    classification_resized_dir (string) : dossier où stocker les imagettes classifiées redimensionnées
    #    extension_raster (string) :  extension d'un fichier raster
    #
    # Returns :
    #    Renvoie les fichiers d'entree file_grid_temp, file_imagette ainsi que le chemin du fichier de sortie créé
    #
    """

    # Récupération du nom de l'imagette
    imagette_file = file_imagette.split(os.sep)[-1]
    imagette_file_name = imagette_file.split(".")[0]
    output_imagette = classification_resized_dir + os.sep +  imagette_file_name + "_tmp" + extension_raster

    if debug >= 3 :
        print(cyan + "createFileOutputImagette() : " + endC + "file_grid_temp : " + file_grid_temp)
        print(cyan + "createFileOutputImagette() : " + endC + "file_imagette : " + file_imagette)
        print(cyan + "createFileOutputImagette() : " + endC + "output_imagette : " + output_imagette)

    return file_grid_temp, file_imagette, output_imagette

###########################################################################################################################################
# FONCTION assemblyImages()                                                                                                               #
###########################################################################################################################################
def assemblyImages(prediction_dir, classification_resized_dir, input_img_paths, output_assembly, vector_simple_mask, split_tile_vector_list, input_raster_path, debord, no_data_value=-1, epsg=2154, extension_raster=".tif", format_vector='ESRI Shapefile', format_raster='GTiff'):
    """
    # Reconstruction de l'image satellite entière. Utilisé pour assembler les différentes imagettes résultats de la prédiction
    #
    # Args:
    #    prediction_dir (string) : chemin du dossier Predict
    #    classification_resized_dir (string) : chemin du dossier des imagettes classifiées redimmensionnées
    #    input_img_paths (list) : liste contenant les chemins vers toutes les imagettes
    #    output_assembly (string) : chemin pour l'image de sortie assemblée
    #    vector_simple_mask (string) : vecteur simplifié de l'image
    #    split_tile_vector_list (list) : liste des vecteurs de découpe
    #    input_raster_path (string) : Chemin de l'image satellite d'entrée
    #    debord (int) : utilisé pour éviter les effets de bord. Agrandit artificiellement les imagettes
    #    no_data_value (int) : valeur que prend un pixel qui ne contient pas d'information
    #    epsg (int) : identificateur de SIG
    #    extension_raster (string) : extension de fichier des imagettes
    #    format_vector (string) : format des vecteurs
    #    format_raster (string) : format des imagettes
    #
    # Returns:
    #    Renvoie l'image satellite assemblée
    #
    """
    imagette_file_list = os.path.join(prediction_dir, "liste_images_tmp.txt")

    pixel_size, _ = getPixelWidthXYImage(input_raster_path)
    split_tile_vector_list = sorted(split_tile_vector_list)

    if debord != 0:
        max_workers = int(os.cpu_count()/4)

        def process_imagette(vector_tile, img_path):
            try:
                file_grid_temp, file_imagette, output_imagette = createFileOutputImagette(vector_tile, img_path, classification_resized_dir, extension_raster)
                cutImageByVector(file_grid_temp, file_imagette, output_imagette, pixel_size, pixel_size, False, no_data_value, epsg, format_raster, format_vector)
                appendTextFileCR(imagette_file_list, output_imagette)
                return output_imagette

            except Exception as e:
                print(cyan + "assemblyImages() : " + bold + red + f"Erreur lors du traitement d'une imagette: {str(e)}" + endC, file=sys.stderr)
                raise e

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(process_imagette, vector_tile, img_path) for vector_tile, img_path in zip(split_tile_vector_list, input_img_paths)]

            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(cyan + "assemblyImages() : " + bold + red + f"Une tâche a échoué: {str(e)}" + endC, file=sys.stderr)

    # Cas où il n'y a pas de débord et donc pas besoin de redécouper les images
    else:
        for i in range(len(input_img_paths)):
            appendTextFileCR(imagette_file_list, input_img_paths[i])

    # Fusion des imagettes
    cmd_merge = "gdal_merge" + getExtensionApplication() + " -of " + format_raster + " -ps " + str(pixel_size) + " " + str(pixel_size) + " -n " + str(no_data_value) + " -a_nodata " + str(no_data_value) + " -o " + output_assembly + " --optfile " + imagette_file_list
    if debug >= 2:
        print(cmd_merge)
    exit_code = os.system(cmd_merge)
    if exit_code != 0:
        print(cmd_merge)
        raise NameError(cyan + "assemblyImages() : " + bold + red + "!!! Une erreur c'est produite au cours du merge des images. Voir message d'erreur." + endC)

    # Conserve le nom de la classification pour pouvoir la supprimer apres la decoupe
    old_output_assembly = output_assembly

    # Decoupage selon l'emprise
    if vector_simple_mask != "":
        decoupe = "_decoupe"
        splitText = output_assembly.split(".")
        output_assembly_decoupe = splitText[0] + decoupe + "." + splitText[1]
        cutImageByVector(vector_simple_mask, output_assembly, output_assembly_decoupe, pixel_size, pixel_size, False, no_data_value, epsg, format_raster, format_vector)

        output_assembly = output_assembly_decoupe

        if debug >= 2:
            print(cyan + "assemblyImages() : " + endC + "Decoupage de l'image assemblée effectué")

    # Si le fichier de sortie mergé a perdu sa projection on force la projection à la valeur par defaut
    epsg_ima, _ = getProjectionImage(output_assembly)
    if epsg_ima == None or epsg_ima == 0:
        if epsg != 0:
            updateReferenceProjection(None, output_assembly, int(epsg))
        else:
            raise NameError(cyan + "assemblyImages() : " + bold + red + "!!! Erreur les fichiers images d'entrée non pas de projection défini et vous n'avez pas défini de projection (EPSG) en parametre d'entrée." + endC)

    # Suppression de l'image predite non decoupee et rennomage de la decoupe
    if os.path.exists(old_output_assembly):
        os.remove(old_output_assembly)
        os.rename(output_assembly, old_output_assembly)

    return old_output_assembly

###########################################################################################################################################
# FONCTION cutInThreads()                                                                                                                 #
###########################################################################################################################################
def cutInThreads(tile_vector_paths, output_dir, file_prefix, extension_raster, output_tile_paths, input_raster_path, tile_size, debord, pixel_size, no_data_value, epsg=2154, format_raster='GTiff', format_vector='ESRI Shapefile', overwrite=True):
    """
    #    Découpe une grande image en imagettes de taille prédéfinies en utilisant le multithreading
    #
    # Args :
    #    tile_vector_paths (list) : Liste des chemins des fichiers vecteurs de découpage
    #    output_dir (str) : Répertoire de sortie où les tuiles seront enregistrées
    #    file_prefix (str) : Préfixe pour les noms de fichiers des images découpées
    #    extension_raster (str) : Extension des fichiers raster (ex. ".tif")
    #    output_tile_paths(list) : Liste pour stocker les chemins des fichiers image de sortie
    #    input_raster_path (str) : Chemin de l'image à découper
    #    tile_size (int) : Taille d'une imagette (supposée carrée)
    #    debord (int) : débord à ajouter pour éviter les effets de bord
    #    no_data_value (int/float) : Valeur de NoData pour les pixels vides
    #    pixel_size (float) : Taille des pixels de l'image
    #           -- optional args --
    #    epsg (int) : Code EPSG pour la projection de l'image
    #    raster_format (str) : Format du raster
    #    vector_format (str) : Format du vecteur
    #    overwrite (bool) : Si True, écrasera les fichiers existants, sinon, évitera l'écrasement
    #
    #
    # Returns :
    #    None
    #
    """
    # Définition de la taille de la grille
    grid_size = tile_size - (debord * pixel_size) * 2 #m

    # Calcul du nombre de CPUs à utiliser
    number_CPU = max(1, int(os.cpu_count() / 2))

    tasks = []

    for idx, tile_vector_path in enumerate(tile_vector_paths):
        # Extraction du nom de sous-tuile
        sub_name = tile_vector_path.split(".")[0].split("_")[-1]
        output_tile_path = os.path.join(output_dir, file_prefix + sub_name + extension_raster)
        output_tile_paths.append(output_tile_path)

        # Vérifier si le fichier d'entrée existe et si on doit traiter cette tuile
        if os.path.exists(tile_vector_path) and (overwrite or not os.path.exists(output_tile_path)):
            # Ajouter la tâche à la liste
            tasks.append((idx, tile_vector_path, output_tile_path, sub_name))
        elif debug >= 1 and os.path.exists(output_tile_path):
            print(f"{cyan}cutInThreads() : {bold}{yellow}Tile {file_prefix + sub_name} already exists{endC}")

    # Fonction de traitement
    def process_tile(task):
        idx, tile_vector_path, output_tile_path, sub_name = task

        if debug >= 1:
            print(f"{cyan}cutInThreads() : {endC}Cutting tile {file_prefix + sub_name} {idx+1}/{len(tile_vector_paths)}...")

        try:
            cutImageByGrid(tile_vector_path, input_raster_path, output_tile_path,
                          grid_size, grid_size, debord, pixel_size, pixel_size,
                          no_data_value, epsg, format_raster, format_vector)
            return True
        except Exception as e:
            print(f"{cyan}cutInThreads() : {bold}{red}Error cutting tile {sub_name}: {str(e)}{endC}", file=sys.stderr)
            return False

    # Exécution des tâches en parallèle avec ThreadPoolExecutor
    if tasks:
        with concurrent.futures.ThreadPoolExecutor(max_workers=number_CPU) as executor:
            results = list(executor.map(process_tile, tasks))

        if debug >= 1:
            success_count = sum(1 for result in results if result)
            print(f"{cyan}cutInThreads() : {endC}Cutting completed. {success_count}/{len(tasks)} tiles processed successfully.")
    else:
        if debug >= 1:
            print(f"{cyan}cutInThreads() : {endC}No tiles to process.")
    return

###########################################################################################################################################
# FONCTION selectInThreadsTiles()                                                                                                         #
###########################################################################################################################################
def selectTilesInThreads(vector_tiles, vector_emprise, vector_output, vector_output_excluded = None, epsg=2154, format_vector='ESRI Shapefile'):
    """
    #   Filtrer les tuiles dont le centroide est contenu dans une emprise avec parallélisation simple
    #
    # Args :
    #   vector_tiles (str) : Fichier vecteur contenant les tuiles à filter
    #   vector_emprise (str) : fichier vecteur de l'emprise de référence
    #   vector_output (str) : Fichier de sortie pour les tuiles filtrée
    # Returns:
    #   None
    """
    # Lecture de l'emprise
    gdf_tiles = gpd.read_file(vector_emprise)
    gdf_emprise = gpd.read_file(vector_emprise)
    # geom_emprise = gdf_emprise.union_all()
    geom_emprise = gdf_emprise.unary_union


    xmin_emprise = geom_emprise.bounds[0]
    # Déterminer le nombre total de polygones dans le fichier
    with fiona.open(vector_tiles) as src:
        total_features = len(src)
    if debug >=2 :
        print(f"{cyan}selectTiles() {endC}: il y a {total_features} polygones à trier dans le vecteur {vector_tiles}")

    number_CPU = max(1, int(os.cpu_count() / 2))
    batch_size = max(1, total_features // number_CPU)
    results = []
    results_excluded = []

    def process_batch(start_idx, end_idx):
        gdf_batch = gpd.read_file(vector_tiles, rows=slice(start_idx, end_idx))
        gdf_batch["centroid"] = gdf_batch.geometry.centroid

        mask_within = gdf_batch["centroid"].within(geom_emprise)
        gdf_filtered = gdf_batch[mask_within].copy()
        mask_excluded = (gdf_batch["centroid"].x >= xmin_emprise) & ~mask_within
        gdf_excluded = gdf_batch[mask_excluded].copy()

        if not gdf_filtered.empty:
            gdf_filtered = gdf_filtered.drop(columns=["centroid"])
        if not gdf_excluded.empty :
            gdf_excluded = gdf_excluded.drop(columns=["centroid"])
        return gdf_filtered, gdf_excluded

    # Exécuter les tâches en parallèle
    with concurrent.futures.ThreadPoolExecutor(max_workers=number_CPU) as executor:
        futures = []
        for i in range(0, total_features, batch_size):
            start_idx = i
            end_idx = min(i + batch_size, total_features)
            futures.append(executor.submit(process_batch, start_idx, end_idx))
    # Récupérer les résultats
        for future in concurrent.futures.as_completed(futures):
            batch_result, batch_excluded = future.result()
            if not batch_result.empty:
                results.append(batch_result)
            if not batch_excluded.empty:
                results_excluded.append(batch_excluded)

    # Fusionner tous les résultats
    if results:
        gdf_final = pd.concat(results, ignore_index=True)
        gdf_final.set_crs(epsg=epsg, inplace=True)
        # Sauvegarder les résultats
        gdf_final.to_file(vector_output, layer="tuiles_centroid_emprise", driver=format_vector)
        if debug >= 1:
            print(f"{cyan}selectTiles() : {endC}{len(gdf_final)} tuiles filtrées sauvegardées dans : {vector_output}")
    else:
        if debug >= 1:
            print(f"{cyan}selectTiles() : {endC}Aucune tuile ne correspond aux critères")

    if results_excluded and vector_output_excluded:
        gdf_final_excluded = pd.concat(results_excluded, ignore_index=True)
        gdf_final_excluded.set_crs(epsg=epsg, inplace=True)
        gdf_final_excluded.to_file(vector_output_excluded, layer="tuiles_hors_ROI", driver=format_vector)
        if debug >=1 :
            print(f"{cyan}selectTiles() : {endC}{len(gdf_final_excluded)} tuiles hors emprises sauvegardées dans : {vector_output_excluded}")
    else :
        if debug>=1 :
            print(f"{cyan}select_tiles(){endC}{len(pd.concat(results_excluded, ignore_index=True))} tuiles exclues (non sauvegardées)")
    return

###########################################################################################################################################
# FONCTION deleteNoDataInThreads()                                                                                                        #
###########################################################################################################################################
def deleteNoDataInThreads(output_tile_paths, output_mask_paths, split_tile_vector_paths, dirname_tile, tile_prefix, dirname_mask, mask_prefix, dirname_vect, vect_prefix, percent_no_data, image_size, debord, pixel_size, no_data_value, n_bands, overwrite,extension_raster=".tif", extension_vector=".shp"):
    """
    #    Supprime les imagettes et masques associés contenant un pourcentage de no_data supérieur au seuil défini,
    #    en utilisant le multithreading pour accélérer le traitement
    #
    # Args:
    #    output_tile_paths (list): Liste des chemins vers les imagettes
    #    output_mask_paths (list): Liste des chemins vers les masques correspondants
    #    dirname_tile (string) : Nom du repertoir dans lequel sont les imagettes
    #    tile_prefix (string) : Préfix des noms des imagettes
    #    dirname_mask (string) : Nom du repertoir dans lequel sont les masques
    #    mask_prefix (string) : Préfix des noms des masques
    #    percent_no_data (float): Pourcentage maximum de no_data autorisé
    #    image_size (int): Taille de l'image en pixels
    #    debord (int): Taille du débord en pixels
    #    pixel_size (float): Taille d'un pixel en unités de projection
    #    no_data_value (float/int): Valeur de no_data à rechercher
    #    n_bands (int): Nombre de bandes dans l'image
    #    overwrite (bool) : si True, force le retraitement
    #
    # Returns:
    #    tuple: Listes filtrées des chemins d'imagettes et de masques conservés
    """

    # Pour ne pas refaire tout cela à chaque lancement de pretreatment
    flag_dir = os.path.join(os.path.dirname(output_tile_paths[0]), "flag")
    flag_file = os.path.join(flag_dir, ".nodata_checked")

    if not os.path.exists(flag_dir):
        os.makedirs(flag_dir)

    if os.path.exists(flag_file) and not overwrite:
        to_delete_paths = []
        try:
            with open(flag_file, "r") as f:
                to_delete_paths = [line.strip() for line in f if line.strip()]
                mask_path = ""
            for img_path in to_delete_paths:
                try:
                    mask_path = img_path.replace(dirname_tile, dirname_mask).replace(tile_prefix, mask_prefix)
                    vect_path = img_path.replace(dirname_tile, dirname_vect).replace(tile_prefix, vect_prefix).replace(extension_raster, extension_vector)
                    if os.path.exists(img_path):
                        os.remove(img_path)
                    if os.path.exists(mask_path):
                        os.remove(mask_path)
                    if debug >= 2:
                        print(f"{cyan}deleteNoDataInThreads() : {bold}Deleting immediatly : {img_path} + {mask_path}{endC}")
                except Exception as e:
                    print(f"{cyan} deleteNoDataInThreads() : {red}Error during deletion of : {img_path}  {str(e)}{endC}", file=sys.stderr)

            # Filtrer les listes pour conserver uniquement ce qui reste
            output_tile_paths = [p for p in output_tile_paths if p not in to_delete_paths]
            output_mask_paths = [p for p in output_mask_paths if p.replace( dirname_mask,dirname_tile).replace(mask_prefix, tile_prefix) not in to_delete_paths]
            split_tile_vector_paths = [p for p in split_tile_vector_paths if p.replace(dirname_vect, dirname_tile).replace(vect_prefix, tile_prefix).replace(extension_vector, extension_raster) not in to_delete_paths]

            return output_tile_paths, output_mask_paths, split_tile_vector_paths

        except Exception as e:
            print(f"{red}{cyan} deleteNoDataInThreads() : Error when reading the file: {str(e)}{endC}", file=sys.stderr)
            # Si erreur, on continue avec le traitement normal

    threshold_pixels = int(((image_size * image_size) * percent_no_data) / 100)
    tiles_to_process = output_tile_paths.copy()
    masks_to_process = output_mask_paths.copy()
    vects_to_process = split_tile_vector_paths.copy()
    cpt_delete = 0
    lock = threading.Lock()
    to_delete_files = []

    results = {}

    def process_nodata_tile(args):
        idx, tile_path, mask_path, band = args
        try:
            if not os.path.exists(tile_path) or not os.path.exists(mask_path):
                return idx, False
            cpt_nodata = countPixelsOfValue(tile_path, no_data_value, band)
            if cpt_nodata >= threshold_pixels:
                if debug >= 2:
                    print(f"{cyan}deleteNoDataInThreads() : {bold}Deleting image: {tile_path} who has more than {percent_no_data}% of NoData on band {band}. We also delete the mask {mask_path}{endC} \n")

                try:
                    os.remove(tile_path)
                    os.remove(mask_path)
                    with lock:
                        nonlocal cpt_delete
                        cpt_delete += 1
                        to_delete_files.append(tile_path)
                except Exception as e:
                    print(f"{cyan}deleteNoDataInThreads() : {bold}{red}Error during the deletion of file {str(e)}{endC}", file=sys.stderr)

                return idx, False

            return idx, True

        except Exception as e:
            print(f"{cyan}deleteNoDataInThreads() : {bold}{red}Erreur for {tile_path}: {str(e)}{endC}", file=sys.stderr)
            return idx, True

    number_CPU = max(1, int(os.cpu_count() / 2))

    # Traitement pour chaque bande
    for band in range(1, n_bands + 1):
        if debug >= 1:
            print(f"{cyan}deleteNoDataInThreads() : {endC}Treating band {band}/{n_bands}...")

        tasks = [(idx, tile_path, mask_path, band)
                for idx, (tile_path, mask_path) in enumerate(zip(tiles_to_process, masks_to_process))]
        with concurrent.futures.ThreadPoolExecutor(max_workers=number_CPU) as executor:
            for idx, keep in executor.map(process_nodata_tile, tasks):
                results[idx] = keep

        # Filtrer les tuiles et masques selon les résultats
        tiles_to_process = [tiles_to_process[idx] for idx in range(len(tiles_to_process)) if results.get(idx, True)]
        masks_to_process = [masks_to_process[idx] for idx in range(len(masks_to_process)) if results.get(idx, True)]
        vects_to_process = [vects_to_process[idx] for idx in range(len(vects_to_process)) if results.get(idx, True)]

        # Réinitialiser les résultats pour la prochaine bande
        results.clear()

    # Enregistrement des chemins supprimés dans le fichier flag
    with open(flag_file, "w") as f:
        for path in to_delete_files:
            f.write(f"{path}\n")

    # Mise à jour des listes originales
    output_tile_paths.clear()
    output_tile_paths.extend(tiles_to_process)

    output_mask_paths.clear()
    output_mask_paths.extend(masks_to_process)

    split_tile_vector_paths.clear()
    split_tile_vector_paths.extend(vects_to_process)

    print(f"{cyan}deleteNoDataInThreads() : {endC}Number of images deleted : {cpt_delete} \n")

    return output_tile_paths, output_mask_paths, split_tile_vector_paths

###########################################################################################################################################
#                                                                                                                                         #
# PARTIE FONCTION PRINCIPALES  (Train,Test,Pretraitement)                                                                                 #
#                                                                                                                                         #
###########################################################################################################################################

###########################################################################################################################################
# FONCTION computePreTreatment()                                                                                                          #
###########################################################################################################################################
def computePreTreatment(groundtruth_path, input_raster_path, roi_vector, output_raster_path, neural_network_mode, model_path, size_grid, debord, grid_vector="", overwrite=True, percent_no_data=10, extension_raster=".tif", extension_vector=".shp", format_raster='GTiff', format_vector='ESRI Shapefile', epsg=2154, select_excluded = False):
    """
    # Pré-traitement de l'image et de la vérité terrain qui vont être découpées en imagettes pour entrer dans un réseau de neuronnes.
    #
    # Args:
    #    groundtruth_path (string) : Chemin du masque (raster)
    #    input_raster_path (string) : Chemin de l'image satellite
    #    roi_vector (string) : vecteur de la région de l'image que l'on souhaite découper en imagettes (pas obligatoire)
    #    output_raster_path (string) : chemin de l'image de sortie du réseau de neurones, classifiée
    #    neural_network_mode (string) : nom du type de réseau de neurones ('resunet')
    #    model_path (string) : Chemin vers le fichier du modèle
    #    size_grid (int) : dimension d'une cellule de la grille de découpe de l'image satellite initiale
    #    debord (int) : nombre de pixels utilisé pour éviter les effets de bord. Agrandit artificiellement les imagettes
    #       -- Optional args --
    #    grid_vector (string) : chemin de la grille qui servira à la découpe (pas obligatoire)
    #    overwrite (bool) : booléen pour écrire ou non par dessus les fichiers existants
    #    percent_no_data (int) : pourcentage de l'image max qui peut-être no-data
    #    extension_raster (string) : extension de fichier des imagettes
    #    extension_vector (string) : extension de fichier des vecteurs
    #    format_raster (string) : format des imagettes
    #    format_vector (string) : format des vecteurs
    #    epsg (int) : Identificateur de SIG
    #
    # Returns :
    #    tuple : Renvoie les listes contenant les chemins des imagettes (satellite et groundtruth) l'emprise de l'image,
    #               la liste des vecteurs de découpes, le nom des dossiers où sont stockés les vecteurs et imagettes
    #
    """
    simplify_vector_param = 10.0

    # Constantes pour les dossiers et fichiers
    FOLDER_VECTOR_TEMP = "_Vect_"
    FOLDER_DATA_TEMP = "_Data_"
    FOLDER_IMAGETTE = "Imagette_"
    FOLDER_TRAIN = "Mask_"
    FOLDER_GRID = "Grid_"

    SUFFIX_VECTOR = "_vect"
    SUFFIX_CUT = "_cut"
    SUFFIX_MASK_CRUDE = "_crude"
    SUFFIX_VECTOR_SIMPLIFY = "_vect_simplify"
    SUFFIX_GRID_TEMP = "_grid_temp"
    SUFFIX_ROI_GRID = "_roi_grid"
    SUFFIX_EXCLUDED_GRID = "_excluded_grid"


    # Taille (en m) d'une cellule de la grille avant d'appliquer le débord
    pixel_size, _  = getPixelWidthXYImage(input_raster_path)
    image_dimension = size_grid*pixel_size

    _, _, n_bands = getGeometryImage(input_raster_path)

    # Récupération du nom du modèle
    model_file = model_path.split(os.sep)[-1]
    model_file_name = model_file.split(".")[0]

    directory = os.path.dirname(output_raster_path)
    vector_temp_dir = os.path.join(directory , neural_network_mode + FOLDER_VECTOR_TEMP + model_file_name)
    os.makedirs(vector_temp_dir, exist_ok = True)


    # Récupération du nom de l'image satellite et de la valeur de nodata
    image_name = os.path.splitext(os.path.basename(input_raster_path))[0]
    cols, rows, num_band = getGeometryImage(input_raster_path)
    no_data_value = getNodataValueImage(input_raster_path, num_band) # -1
    if no_data_value == None or no_data_value ==-1.0:
        no_data_value = -1

    # Si le vecteur d'emprise n'est pas fourni, on le génère à partir de l'image d'entrée ;
    if roi_vector == "" :
        roi_vector = os.path.join(vector_temp_dir , image_name + SUFFIX_MASK_CRUDE + extension_vector)
        vector_exists = os.path.isfile(roi_vector)
        if vector_exists and not overwrite :
            if debug >= 1 :
                print(f"{cyan} computePreTreatment() : {bold}{yellow} roi vector {str(roi_vector)} already exists \n {endC}")
        else :
            createVectorMask(input_raster_path, roi_vector, no_data_value, format_vector)
        roi_vector_simplified = os.path.join(vector_temp_dir , image_name + SUFFIX_VECTOR_SIMPLIFY + extension_vector)
        simplifyVector(roi_vector, roi_vector_simplified, simplify_vector_param, format_vector)

    else :
        roi_vector_simplified = roi_vector
        simplifyVector(roi_vector, roi_vector_simplified, simplify_vector_param, format_vector)


    # Si la grille de découpe n'est pas fournie, on la crée
    if grid_vector == "" :
        full_grid_temp = os.path.join(vector_temp_dir, image_name + SUFFIX_GRID_TEMP + extension_vector)
        grid_exists = os.path.isfile(full_grid_temp)
        if grid_exists and not overwrite:
            if debug >= 1 :
                print(f"{cyan}computePreTreatement() : {bold}{yellow}Vector grid {str(full_grid_temp)} already exists. We delete it\n {endC}")
                os.remove(full_grid_temp)
        tiles_dimension = image_dimension - (debord * pixel_size) * 2
        createGridVector(roi_vector_simplified, full_grid_temp, tiles_dimension, tiles_dimension, None, overwrite, epsg , format_vector)
    else :
        full_grid_temp = grid_vector

    dir_basename = os.path.basename(roi_vector_simplified).split(".")[0]

    # Selection de certaines tuiles pour un possible pré entrainement
    if select_excluded :
        excluded_basename = "pretrain"
        excluded_grid_vector = os.path.join(vector_temp_dir, dir_basename, image_name + SUFFIX_EXCLUDED_GRID + extension_vector)
        os.makedirs(os.path.dirname(excluded_grid_vector), exist_ok = True)
        data_pretrain_dir = os.path.join(directory, neural_network_mode + FOLDER_DATA_TEMP + model_file_name, excluded_basename)
        data_pretrain_imagette_dir = os.path.join(data_pretrain_dir , FOLDER_IMAGETTE + model_file_name)
        data_pretrain_grid_dir = os.path.join(data_pretrain_dir , FOLDER_GRID + model_file_name)
        data_pretrain_mask_dir = os.path.join(data_pretrain_dir , FOLDER_TRAIN + model_file_name)

        for d in [data_pretrain_dir, data_pretrain_imagette_dir, data_pretrain_grid_dir, data_pretrain_mask_dir] :
            if not os.path.isdir(d):
                os.makedirs(d)

        pretrain_tile_paths = []
        pretrain_mask_paths = []
    else :
        excluded_grid_vector = None

    # Recadrage de la grille pour le garder que les polygones dont le centre est dans la zone d'intérêt
    roi_grid_vector = os.path.join(vector_temp_dir, dir_basename, image_name + SUFFIX_ROI_GRID + extension_vector)
    os.makedirs(os.path.dirname(roi_grid_vector), exist_ok=True)


    grid_exists = os.path.isfile(roi_grid_vector)
    if grid_exists and not overwrite :
        if debug >= 1 :
            print(f"{cyan}computePreTreatment() : {bold}{yellow} the grid for the roi already exits at {roi_grid_vector} {endC}")
    else :
        selectTilesInThreads(full_grid_temp, roi_vector_simplified, roi_grid_vector, excluded_grid_vector)

    # Création des répertoires temporaires
    data_temp_dir = os.path.join(directory, neural_network_mode + FOLDER_DATA_TEMP + model_file_name, dir_basename)
    data_imagette_temp_dir = os.path.join(data_temp_dir , FOLDER_IMAGETTE + model_file_name)
    data_train_temp_dir = os.path.join(data_temp_dir , FOLDER_TRAIN + model_file_name)
    data_grid_temp_dir = os.path.join(data_temp_dir , FOLDER_GRID + model_file_name)

    for d in [data_temp_dir , data_imagette_temp_dir , data_train_temp_dir , data_grid_temp_dir] :
        if not os.path.isdir(d) :
            os.makedirs(d)

    # Extraire chaque polygone du fichier roi_grid_vector s'ils ne l'ont pas déjà été fait
    if len(os.listdir(data_grid_temp_dir)) == 0 or overwrite:
        split_tile_vector_paths = splitVector(roi_grid_vector, data_grid_temp_dir, "sub_name", epsg, format_vector, extension_vector)
    else :
        if debug >= 1 :
            print(f"{cyan}ComputePreTreatement() : {bold}{yellow} grid already split. You can find the vector here : {data_grid_temp_dir} {endC}")
        split_tile_vector_paths = [os.path.join(data_grid_temp_dir, f) for f in os.listdir(data_grid_temp_dir) if f.endswith(extension_vector)][::-1]

    if select_excluded :
        if len(os.listdir(data_pretrain_grid_dir))==0 or overwrite:
            split_tile_pretrain_paths = splitVector(excluded_grid_vector, data_pretrain_grid_dir, "sub_name", epsg, format_vector, extension_vector)
        else :
            if debug >=1 :
                print(f"{cyan}ComputePreTreatement() : {bold}{yellow} grid for pretrainning already spli here {data_pretrain_grid_dir}{endC}")
            split_tile_pretrain_paths = [os.path.join(data_pretrain_grid_dir, f) for f in os.listdir(data_pretrain_grid_dir) if f.endswith(extension_vector)][::-1]

    # Initialisation des listes qui vont contenir les chemins des imagettes et masques
    output_tile_paths = []
    output_mask_paths = []

    # Découpage de l'image d'entrée en imagettes
    tile_prefix= "sat_"
    mask_prefix = "mask_"
    grid_prefix = image_name + SUFFIX_ROI_GRID +"_"
    cutInThreads(split_tile_vector_paths, data_imagette_temp_dir, tile_prefix, extension_raster, output_tile_paths, input_raster_path, image_dimension, debord, pixel_size, no_data_value, epsg, format_raster, format_vector, overwrite)

    if select_excluded :
        cutInThreads(split_tile_pretrain_paths, data_pretrain_imagette_dir, tile_prefix, extension_raster, pretrain_tile_paths, input_raster_path, image_dimension, debord, pixel_size, no_data_value, epsg, format_raster, format_vector, overwrite)
        if groundtruth_path != "" :
            cutInThreads(split_tile_pretrain_paths, data_pretrain_mask_dir, mask_prefix, extension_raster, pretrain_mask_paths, groundtruth_path, image_dimension, debord, pixel_size, no_data_value, epsg, format_raster, format_vector, overwrite)
        pretrain_tile_paths, pretrain_mask_paths, split_tile_pretrain_paths = deleteNoDataInThreads(pretrain_tile_paths, pretrain_mask_paths, split_tile_pretrain_paths, FOLDER_IMAGETTE + model_file_name ,tile_prefix, FOLDER_TRAIN + model_file_name ,mask_prefix, FOLDER_GRID + model_file_name, grid_prefix,percent_no_data, size_grid, debord, pixel_size, no_data_value, n_bands, overwrite, extension_raster,extension_vector)

    # Découpage de la vérité terrain en imagettes si elle a été fournie
    if groundtruth_path != "" :
        cutInThreads(split_tile_vector_paths, data_train_temp_dir,mask_prefix, extension_raster, output_mask_paths, groundtruth_path, image_dimension, debord, pixel_size, no_data_value, epsg, format_raster, format_vector, overwrite)

    # Suppression des imagettes(et leur masque si +10% des pixels sont en no_data) mais pas des dossiers, seulement des listes
    output_tile_paths, output_mask_paths, split_tile_vector_paths = deleteNoDataInThreads(output_tile_paths, output_mask_paths, split_tile_vector_paths, FOLDER_IMAGETTE + model_file_name ,tile_prefix, FOLDER_TRAIN + model_file_name ,mask_prefix, FOLDER_GRID + model_file_name, grid_prefix,percent_no_data, size_grid, debord, pixel_size, no_data_value, n_bands, overwrite, extension_raster,extension_vector)

    if debug >= 2 :
        print(f" {cyan}computePreTreatment() : {endC} There are {len(output_tile_paths)} imagettes et {len(output_mask_paths)} masks \n")

    print(f"{cyan} computePreTreatment() : end of pre-treatment. \n {endC}")

    return output_tile_paths, output_mask_paths, roi_vector_simplified, split_tile_vector_paths, vector_temp_dir, data_temp_dir

###########################################################################################################################################
# FONCTION computeTrain()                                                                                                                 #
###########################################################################################################################################
def computeTrain(groundtruth_path, input_raster_path, train_vector, valid_vector, model_output, output_raster_path, grid_path, NN, neural_network_mode, size_grid, debord, augment_data, number_class, time_log_path, save_data, overwrite=True, extension_raster=".tif", extension_vector=".shp", format_raster='GTiff', format_vector='ESRI Shapefile', rand_seed=0, epsg=2154, percent_no_data=10, save_temp_files=False):

    """
    #    Entraine un réseau de neurone grâce à un dataset de train et validation
    #
    # Args :
    #    groundtruth_path (string) : l'image satellite d'apprentissage ( = ground truth)
    #    input_raster_path (string) : Chemin de l'image satellite d'entrée
    #    train_vector(string): emprise jeu d'entrainement
    #    valid_vector (string): emprise jeu de validation
    #    model_output (string) : chemin où stocker le réseau de neurones entrainé
    #    output_raster_path (string) : chemin où stocker l'image finale classifiée
    #    NN (structure) : structure contenant tout les paramètres propre au réseau de neurones
    #    neural_network_mode (string) : nom du type de réseau de neurones
    #    size_grid (int) : dimension d'une cellule de la grille de découpe de l'image satellite initiale
    #    debord (int) : utilisé pour éviter les effets de bord. Agrandit artificiellement les imagettes
    #    augment_data (int) : booléen pour determiner si on augmente artificiellement le jeu de données par des rotations
    #    number_class (int) : nombre de classes
    #    time_log_path (string) : chemin du fichier de log
    #    save_data (bool) : booléen pour determiner si on conserve ou non le dossier Data
            -- Optional Args --
    #    overwrite (bool) : booléen pour écrire ou non par dessus un fichier existant
    #    extension_raster (string) : extension de fichier des imagettes
    #    extension_vector (string) : extension de fichier des vecteurs
    #    format_raster (string) : format des imagettes
    #    format_vector (string) : format des vecteurs
    #    epsg (int) : Identificateur de SIG
    #    save_temp_files (int) : booléen qui determine si on sauvegarde ou non les fichiers temporaires
    #
    # Returns :
    #    tuple : Renvoie le modèle de sortie entraîné, la table des imagettes, l'emprise de l'image d'entrée, la liste des vecteurs de découpe ainsi que les noms des dossiers où sont stockés les vecteurs et imagettes
    #
    """

    # Constantes
    FOLDER_HISTORY = "_History_"
    FOLDER_DATA = "_Data_"
    FOLDER_MODEL = "Model"
    EXTENSION_NEURONAL_NETWORK = ".hdf5"

    # Récupération d'informations
    img_size = size_grid
    n_classes = number_class
    batch_size = NN.batch
    kernel_size = NN.kernel_size
    dropout_rate = NN.dp_rate
    alpha_loss = NN.alpha_loss
    _, _, n_bands = getGeometryImage(input_raster_path)
    n_filters = NN.number_conv_filter
    model_name = neural_network_mode

    # Récupére la date et le repertoire
    current_date = date.today().strftime("%d_%m_%Y")
    directory = os.path.dirname(output_raster_path)

    # Création du nom du fichier stockant le réseau de neurones que l'on entraine
    if model_output == "" :
        # Récupération du nom du réseau
        model_filename = os.path.basename(output_raster_path).split(".")[0]
        model_dir = os.path.join(directory, FOLDER_MODEL)
        os.makedirs(model_dir, exist_ok=True)

        # Création du model output
        model_path = os.path.join(model_dir , model_filename + EXTENSION_NEURONAL_NETWORK)
    else:
        model_path = model_output
        model_filename = os.path.basename(model_output).split(".")[0]

    # Determine le type de classification
    if n_classes == 1:
        type_class = '_mono_'
    else:
        type_class = '_multi_'

    history_dir = os.path.join(directory, model_name + FOLDER_HISTORY + model_filename)
    os.makedirs(history_dir, exist_ok=True)

    # Regarde si le fichier de log existe
    check_log = os.path.isfile(time_log_path)

    # Création du nom du fichier stockant l'historique de l'entrainnement (attention necessite d'avoir le dossier Model au même endroit que le dossier History)
    csv_filename = history_dir + os.sep + model_filename + type_class + current_date + ".csv"
    csv_logger = CSVLogger(csv_filename)

    # Création du tensorboard
    log_dir=os.path.join(history_dir, model_filename + type_class )
    tensorboard_callback = TensorBoard(log_dir=log_dir, histogram_freq = 1)

    # Mise à jour du Log
    if check_log :
        pre_treatment_event = "Starting of pre-treatment : "
        timeLine(time_log_path, pre_treatment_event)

    data_dir = os.path.join(directory, model_name + FOLDER_DATA + model_filename)
    os.makedirs(data_dir, exist_ok=True)

    train_image_output = os.path.join(directory, "train_" + model_filename)
    valid_image_output = os.path.join(directory, "valid_" +model_filename)

    # Pretraitement pour les dataset d'entrainement et de validation
    train_tile_paths, train_mask_paths, train_vector_simplified, split_tile_vector_paths, vector_temp_dir, data_temp_dir = computePreTreatment(groundtruth_path, input_raster_path, train_vector, train_image_output, neural_network_mode, model_path, size_grid, debord, grid_path, overwrite, percent_no_data, extension_raster, extension_vector, format_raster, format_vector, epsg, select_excluded = False)
    valid_tile_paths, valid_mask_paths, valid_vector_simplified, split_tile_vector_paths, vector_temp_dir, data_temp_dir = computePreTreatment(groundtruth_path, input_raster_path, valid_vector, valid_image_output, neural_network_mode, model_path, size_grid, debord, grid_path, overwrite, percent_no_data,extension_raster, extension_vector, format_raster, format_vector, epsg)

    if len(train_tile_paths) != len(train_mask_paths) :
        print(f"{cyan}computeTrain() : {bold}{red} Il n'y a une différence de {len(train_tile_paths) - len(train_mask_paths)} entre les tuiles et les masques pour le dataset d'entrainement {endC}\n")
    if len(valid_tile_paths) != len(valid_mask_paths) :
        print(f"{cyan}computeTrain() : {bold}{red} Il n'y a une différence de {len(valid_tile_paths) - len(valid_mask_paths)} entre les tuiles et les masques pour le dataset d'entrainement {endC}\n")

    if debug >=2 :
        print(f"{cyan}computeTrain() : Il y a {len(train_tile_paths)} données d'entrainement et {len(valid_tile_paths)} données de validation{endC}")

    # Mise à jour du Log
    if check_log :
        ending_pre_treatment_event = "Ending of pre-treatment : "
        timeLine(time_log_path, ending_pre_treatment_event)

    # Chargement des données par lots de taille batch_size avec augmentation pour le train (générateur)
    train_gen = DataGenerator(batch_size, train_tile_paths, train_mask_paths, augment_data, n_classes, data_type = 'train', shuffle = True)
    valid_gen = DataGenerator(batch_size, valid_tile_paths, valid_mask_paths, 0, n_classes, data_type = 'valid', shuffle = True)

    # Chargement du modèle
    if model_name.lower() == "resunet":
        if n_classes == 1:
            model = resunet((img_size, img_size, n_bands), n_filters, dropout_rate, alpha_loss, n_classes, kernel_size, "mono")
        else:
            model = resunet((img_size, img_size, n_bands), n_filters, dropout_rate, alpha_loss, n_classes, kernel_size, "multi")


    if debug >= 1:
        model.summary()

    # Outils pour l'apprentissage du modèle
    model_checkpoint = ModelCheckpoint(model_path, monitor = 'val_loss', verbose = 1, save_best_only = True)

    model_early_stopping = EarlyStopping(monitor = NN.es_monitor, patience = NN.es_patience, min_delta = NN.es_min_delta, verbose = NN.es_verbose, restore_best_weights = True)
    model_reducelronplateau = ReduceLROnPlateau(monitor = NN.rl_monitor, factor = NN.rl_factor, patience = NN.rl_patience, min_lr = NN.rl_min_lr, verbose =NN.rl_verbose, mode = 'min')

    callbacks = [model_checkpoint, model_early_stopping, model_reducelronplateau, csv_logger, tensorboard_callback]

    # Mise à jour du Log
    if check_log :
        fitting_event = "Starting to fit model : "
        timeLine(time_log_path, fitting_event)

    # Apprentissage du modèle
    model.fit(train_gen, epochs = NN.number_epoch, verbose = 2, callbacks = callbacks, validation_data = valid_gen)

    # Mise à jour du Log
    if check_log :
        ending_fitting_event = "Ending to fit model : "
        timeLine(time_log_path, ending_fitting_event)

    # Suppression des dossiers temporaires
    if not save_temp_files :

        if debug >= 1 :
            print(cyan + "computeTrain() : " + endC + "Suppression des dossiers temporaires")

        try:
            shutil.rmtree(history_dir)
        except Exception:
            pass
        try:
            shutil.rmtree(vector_temp_dir)
        except Exception:
            pass

        if not save_data :
            try:
                shutil.rmtree(data_temp_dir)
            except Exception:
                pass

    return model_path, split_tile_vector_paths, vector_temp_dir, data_temp_dir

###########################################################################################################################################
# FONCTION computeClassification()                                                                                                        #
###########################################################################################################################################
def computeClassification(groundtruth_path, input_raster_path, vector_test, output_raster_path, evaluation_path, split_tile_vector_paths, vector_temp_dir, data_temp_dir, model_input, NN, neural_network_mode,size_grid, debord, number_class, complete_background, log_path, grid_vector = "", overwrite=True, extension_raster=".tif", extension_vector=".shp", format_raster='GTiff', format_vector='ESRI Shapefile', epsg=2154, no_data_value=-1, percent_no_data = 10, save_temp_files=False):
    """
    #    Prediction des différents résultats en imagettes et assemblage en une seule image
    #
    # Args:
    #    groundtruth_path (string) : l'image satellite d'apprentissage
    #    input_raster_path (string) : Chemin de l'image satellite d'entrée
    #    vector_test (string) : Vecteur délimitant la zone des données test
    #    output_raster_path (string) : chemin où stocker l'image finale classifiée
    #    split_tile_vector_paths (list) : liste des vecteurs de découpe
    #    vector_temp_dir (string) : Chemin du répertoire temporaire contenant les vecteurs
    #    data_temp_dir (string) : Chemin du répertoire temporaire contenant les imagettes
    #    model_input (string) : nom du réseau de neurones à utiliser pour classifier
    #    NN (structure) : structure contenant tout les paramètres propre au réseau de neurones
    #    neural_network_mode (string) : nom du type de réseau de neurones
    #    size_grid (int) : dimension d'une cellule de la grille de découpe de l'image satellite initiale
    #    debord (int) : utilisé pour éviter les effets de bord. Agrandit artificiellement les imagettes
    #    number_class (int) : nombre de classes
    #    complete_background (bool) : booléen pour savoir si on remplace le background par la seconde classe la plus probable
    #    log_path (string) : chemin du fichier de log
    #       -- Optionnal Args --
    #    grid_vector (string) : chemin d'une grille de découpe prédéfinie
    #    overwrite (bool) : booléen pour écrire ou non par dessus un fichier existant
    #    extension_raster (string) : extension de fichier des imagettes
    #    extension_vector (string) : extension de fichier des vecteurs
    #    format_raster (string) : format des imagettes
    #    format_vector (string) : format des vecteurs
    #    epsg (int) : Identificateur de SIG
    #    no_data_value (int) : valeur que prend un pixel qui ne contient pas d'information
    #    percent_no_data (int) : pouventage de pixel max en no_data dans une imagette
    #    save_temp_files (bool) : booléen qui determine si on sauvegarde ou non les fichiers temporaires
    #
    # Returns:
    #    None
    #
    """
    # Récupération du nombre de bandes dans l'image et de la taille des pixels
    _, _, n_bands = getGeometryImage(input_raster_path)
    pixel_size, _ = getPixelWidthXYImage(input_raster_path)

    # Création d'un dossier temporaire Prédiction
    FOLDER_PREDICTION = "_Predict_"
    FOLDER_CLASSIFICATION_IMAGETTES = "Classified_Imagettes"
    FOLDER_CONFIDENCE_IMAGETTES = "Confidence_Imagettes"
    FOLDER_GRADIENT_IMAGETTES = "Gradient_Imagettes"
    FOLDER_CLASSIFICATION_RESHAPE = "Resized_Classified_Imagettes"
    FOLDER_CONFIDENCE_RESHAPE = "Resized_Confidence_Imagettes"
    FOLDER_GRADIENT_RESHAPE = "Resized_Gradient_Imagettes"
    directory = os.path.dirname(output_raster_path)

    # Récupération du nom du réseau
    model_file = model_input.split(os.sep)[-1]
    model_file_name = model_file.split(".")[0]

    #Creation des dossiers s'ils n'existent pas déjà
    prediction_dir= os.path.join(directory,neural_network_mode + FOLDER_PREDICTION + model_file_name)
    classification_dir = os.path.join(prediction_dir,FOLDER_CLASSIFICATION_IMAGETTES , "")
    confidence_dir = os.path.join(prediction_dir,FOLDER_CONFIDENCE_IMAGETTES , "")
    gradient_dir = os.path.join(prediction_dir,FOLDER_GRADIENT_IMAGETTES , "")
    classification_resized_dir = os.path.join(prediction_dir,FOLDER_CLASSIFICATION_RESHAPE, "")
    confidence_resized_dir = os.path.join(prediction_dir,FOLDER_CONFIDENCE_RESHAPE, "")
    gradient_resized_dir = os.path.join(prediction_dir,FOLDER_GRADIENT_RESHAPE, "")
    for d in [prediction_dir , classification_dir, confidence_dir, gradient_dir, gradient_resized_dir, classification_resized_dir, confidence_resized_dir] :
        os.makedirs(d, exist_ok=True)

    # Regarde si le fichier de log existe
    log_exists = os.path.isfile(log_path)
    # Mise à jour du Log
    if log_exists :
        pre_treatment_event = "Starting of pre-treatment : "
        timeLine(log_path, pre_treatment_event)

    # Prétraitement de l'image à classifier
    tile_paths, mask_paths, vector_simplified, split_tile_vector_paths, vector_temp_dir, data_temp_dir = computePreTreatment(groundtruth_path, input_raster_path, vector_test, output_raster_path, neural_network_mode, model_input, size_grid, debord, grid_vector, overwrite, percent_no_data, extension_raster, extension_vector, format_raster, format_vector, epsg)

    # Mise à jour du Log
    if log_exists :
        ending_pre_treatment_event = "Ending of pre-treatment : "
        timeLine(log_path, ending_pre_treatment_event)

    mask_paths_copy = mask_paths
    mask_paths = []

    if debug >=3:
        print(f"{cyan}computeClassification() : {endC}Nombres d'images à classifier:{len(tile_paths)}")

    # Prédiction à partir d'un modèle
    if debug >= 1:
        print(f"{cyan}computeClassification() : {endC}Chargement de toutes les images")
    test_gen = DataGenerator(NN.batch, tile_paths, mask_paths, 0, number_class, data_type = 'test')
    if debug >= 1:
        print(f"{cyan}computeClassification() : {endC}Fin du chargement de toutes les images")

    # Chargement d'un modèle déjà entraîné
    if debug >= 1:
        print(f"{cyan}computeClassification() : {endC}Chargement du modele entraine")
    model = keras.models.load_model(model_input,custom_objects={"DiceLossMulti": DiceLossMulti, "CombinedLoss": CombinedLoss, "sqrt_activation": sqrt_activation})
    if debug >= 1:
        print(f"{cyan}computeClassification() : {endC}Fin du chargement du modèle")

    # Mise à jour du Log
    if log_exists :
        predicting_event = "Starting to predict : "
        timeLine(log_path, predicting_event)

    # Prédiction sur toutes les données
    if debug >= 1:
        print(f"{cyan}computeClassification() : {endC}Debut de prediction")

    # Prediction en batches
    nb_mask = len(test_gen[0])
    if (len(tile_paths))%nb_mask != 0 :
        for i in range (len(test_gen)):
            if debug >= 1:
                print(f"{cyan}computeClassification() : {endC}Test{(i+1)}/{len(test_gen)}")
            predictionTestGenerator(model, test_gen[i], tile_paths[i*nb_mask:i*nb_mask+nb_mask], classification_dir, confidence_dir, gradient_dir, pixel_size, size_grid, format_raster, save_confidence = True, complete_background = complete_background)
    else:
        nb_lots_utile = int(len(tile_paths)/nb_mask)
        for i in range (nb_lots_utile):
            if debug >= 1:
                print(f"{cyan}computeClassification() : {endC}Test {(i+1)}/{nb_lots_utile}")
            predictionTestGenerator(model, test_gen[i], tile_paths[i*nb_mask:i*nb_mask+nb_mask], classification_dir, confidence_dir, gradient_dir, pixel_size, size_grid, format_raster, save_confidence = True, complete_background = complete_background)

    # Mise à jour du Log
    if log_exists :
        ending_predicting_event = "Ending to predict : "
        timeLine(log_path, ending_predicting_event)

    if debug >= 1:
        print(f"{cyan}computeClassification() : {endC} Fin de prediction")

    # Récuperation dans une seule liste de l'ensemble des imagettes classifiees
    predict_paths = []
    confidence_paths = []
    gradient_paths = []

    for f in os.listdir(classification_dir):
        predict_paths.append(classification_dir + f)
    for f in os.listdir(confidence_dir):
        confidence_paths.append(confidence_dir + f)
    for f in os.listdir(gradient_dir):
        gradient_paths.append(gradient_dir + f)

    predict_paths = sorted(predict_paths)
    confidence_paths = sorted(confidence_paths)
    gradient_paths = sorted(gradient_paths)

    # Mise à jour du Log
    if log_exists :
        assembly_event = "Starting to assembly : "
        timeLine(log_path, assembly_event)

    # Assemblage de l'image en une seule
    output_confidence_map_path = os.path.join(directory, "confidence_map.tif")
    output_gradient_map_path = os.path.join(directory, "gradient_map.tif")
    output_assembly_path = assemblyImages(classification_resized_dir, classification_resized_dir, predict_paths, output_raster_path, vector_simplified, split_tile_vector_paths, input_raster_path, debord, no_data_value, epsg, extension_raster, format_vector, format_raster)
    output_confidence_assembly_path = assemblyImages(confidence_resized_dir, confidence_resized_dir, confidence_paths, output_confidence_map_path, vector_simplified, split_tile_vector_paths, input_raster_path, debord, no_data_value, epsg, extension_raster, format_vector, format_raster)
    output_gradient_assembly_path = assemblyImages(gradient_resized_dir, gradient_resized_dir, gradient_paths, output_gradient_map_path, vector_simplified, split_tile_vector_paths, input_raster_path, debord, no_data_value, epsg, extension_raster, format_vector, format_raster)

    # Mise à jour du Log
    if log_exists :
        ending_assembly_event = "Ending to assembly : "

    # Suppression des dossiers temporaires
    if not save_temp_files :

        if debug >= 1 :
            print(cyan + "computeClassification() : " + endC + "Suppression des dossiers temporaires")
        try:
            shutil.rmtree(prediction_dir)
            shutil.rmtree(confidence_dir)
            shutil.rmtree(gradient_dir)
        except Exception:
            pass

        try:
            shutil.rmtree(vector_temp_dir)
        except Exception:
            pass

        try:
            shutil.rmtree(data_temp_dir)
        except Exception:
            pass

    # Mesures de performance et évaluation
    evaluation_exists = os.path.exists(evaluation_path)
    _, ext = os.path.splitext(evaluation_path)
    if evaluation_exists and not overwrite :
        print(f"{cyan}computeClassification(): vérité terrain déjà découpée {evaluation_exists}{endC}")
    else :
        cutImageByVector(vector_test, evaluation_path,evaluation_path, pixel_size, pixel_size, True, no_data_value , epsg, format_raster, format_vector)

    matrix_file = "/mnt/RAM_disk/confusion_matrice.xml"
    no_data_value = -1

    if ext == ".tif" :
        computeConfusionMatrix(output_assembly_path, None, evaluation_path, "", matrix_file, no_data_value, overwrite )
    elif ext == ".shp":
        computeConfusionMatrix(output_assembly_path, evaluation_path, None, "ValRef", matrix_file, no_data_value, overwrite )

    if debug >=1 :
        print(f"{cyan}computeClassification() {endC} Matrice de confusion généré ici : {matrix_file}")

    return

###########################################################################################################################################
# FONCTION computeNeuralNetwork()                                                                                                         #
###########################################################################################################################################
def computeNeuralNetwork(input_raster_path, groundtruth_path, grid_path, evaluation_path, vector_train, vector_valid, vector_test, output_raster_path, model_input, model_output, NN, use_graphic_card, id_graphic_card, neural_network_mode, augment_training, complete_background, size_grid, debord, number_class, path_time_log, extension_raster=".tif", extension_vector=".shp", format_raster='GTiff', format_vector='ESRI Shapefile', rand_seed=0, epsg=2154, percent_no_data=10, no_data_value=0, save_results_intermediate=False, overwrite=True):
    """
    #    Choix entre une simple classification ou entrainement, ou bien un enchainement des deux
    #
    # Args:
    #    input_raster_path (string) : Chemin de l'image satellite d'entrée
    #    groundtruth_path (string) : GroundTruth
    #    grid_path (string) : grille de découpe si elle existe déjà
    #    evaluation_path (string) : Fichier de vérité pour la zone de test
    #    output_raster_path (string) : chemin où stocker l'image finale classifiée
    #    model_input (string) : nom du réseau de neurones à utiliser pour classifier
    #    model_output (string) : chemin où stocker le modèle (réseau de neurones) une fois entraîné
    #    NN (structure) : structure contenant tout les paramètres propre au réseau de neurones
    #    use_graphic_card (bool) : booléen qui determine si on utilise la GPU ou la CPU
    #    id_graphic_card (int) : determine l'identifiant de la carte graphique à utiliser (int)
    #    neural_network_mode (string) : nom du type de réseau de neurones
    #    augment_training (bool) : booléen qui determine si on procède à l'augmentation artificielle de données sur le jeu de donnée d'entrainement
    #    size_grid (int) : dimension d'une cellule de la grille de découpe de l'image satellite initiale
    #    debord (int) : utilisé pour éviter les effets de bord. Agrandit artificiellement les imagettes
    #    number_class (int) : nombre de classes
    #    path_time_log (string) : le fichier de log de sortie
    #    extension_raster (string) : extension de fichier des imagettes
    #    extension_vector (string) : extension de fichier des vecteurs
    #    format_raster (string) : format des imagettes
    #    format_vector (string) : format des vecteurs
    #    rand_seed (int): graine pour la partie randon
    #    epsg (int) : Identificateur de SIG
    #    percent_no_data (int) : pourcentage de no data
    #    no_data_value (int) : valeur que prend un pixel qui ne contient pas d'information
    #    save_results_intermediate (bool) : booléen qui determine si on sauvegarde ou non les fichiers temporaires
    #    overwrite (bool) : booléen pour écrire ou non par dessus un fichier existant
    #
    # Returns :
    #    ANone
    #
    """
    # Nettoyer l'environnement si overwrite est à True
    if overwrite :

        FOLDER_PREDICTION = "_Predict_"
        FOLDER_HISTORY = "_History_"
        FOLDER_VECTOR = "_Vect_"
        FOLDER_DATA = "_Data_"

        # Récupération du nom de l'image de sortie ou du modèle de sortie qui sert à la création des noms des differents dossiers
        if model_output == "" :
            folder_end = output_raster_path.split(os.sep)[-1]
            folder_end_name = folder_end.split(".")[0]
            directory = os.path.dirname(output_raster_path)
        else:
            folder_end = model_output.split(os.sep)[-1]
            folder_end_name = folder_end.split(".")[0]
            directory = os.path.dirname(model_output)

        # Création des noms des différents dossiers
        vect_dir = os.path.join(directory, neural_network_mode + FOLDER_VECTOR + folder_end_name)
        data_dir = os.path.join(directory, neural_network_mode + FOLDER_DATA + folder_end_name)
        prediction_dir = os.path.join(directory, neural_network_mode + FOLDER_PREDICTION + folder_end_name)
        history_dir = os.path.join(directory, neural_network_mode + FOLDER_HISTORY + folder_end_name)

        # Suppression des dossiers si Overwrite = True et qu'ils existent :
        folders_to_clean = [ (vect_dir, "Vect") , (data_dir, "Data"), (prediction_dir, "Predict"), (history_dir, "History")]
        for folder_path, label in folders_to_clean :
            if os.path.isdir(folder_path):
                print(f"{cyan} computeNeuralNetwork() : {bold}{yellow} Delete of {label} folder already existing {endC}")
                try :
                    shutil.rmtree(folder_path)
                except Exception :
                    pass

        # Suppression du fichier log
        if os.path.isfile(path_time_log):
            print(f"{cyan}computeNeuralNetwork() : {bold}{yellow}Delete of path_time_log file already existing{endC}")
            try:
                os.remove(path_time_log)
            except Exception:
                pass

    # Cas où on ne remplace pas
    else:
        if output_raster_path != "":
            check = os.path.isfile(output_raster_path)
            if check:
                raise NameError (cyan + "NeuralNetworkSegmentation : " + bold + red  + "File %s already exist!" %(output_raster_path) + endC)
                exit()


    # Configuration de l'environnement CUDA
    os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
    if use_graphic_card :
        # Activation GPU spécifique
        os.environ["CUDA_VISIBLE_DEVICES"] = str(id_graphic_card)
        physical_devices = tf.config.list_physical_devices('GPU')
        if physical_devices :
            tf.config.experimental.set_memory_growth(physical_devices[0], True)
            print(f"Using GPU {id_graphic_card}: {physical_devices}")
        else :
            print(f"GPU {id_graphic_card} not found. Falling back to CPU")
    else:
        #utilisation du CPU
        os.environ["CUDA_VISIBLE_DEVICES"] = ""

    if debug >=1:
        if use_graphic_card:
            print(f"GPU activated : GPU {id_graphic_card}")
        else:
            print("GPU desactivated, using CPU")


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
    check_log = os.path.isfile(path_time_log)

    # Choix entre entrainement,classification ou les deux

    # Cas d'une simple classification
    if output_raster_path != "" and model_input != "" and vector_test !="" and groundtruth_path =="":

         if debug >=1:
            print(cyan + "computeNeuralNetwork() : " + endC + "Début de la phase de classification")
         # Initialisation
         input_table = []
         split_tile_vector_list = []
         vect_temp_dir = ""
         data_temp_dir = ""

         # Mise à jour du Log
         if check_log :
            starting_event = "Starting of classification : "
            timeLine(path_time_log, starting_event)

         # Classification
         computeClassification(groundtruth_path, input_raster_path, vector_test, output_raster_path, evaluation_path, split_tile_vector_list, vect_temp_dir, data_temp_dir, model_input, NN, neural_network_mode, size_grid, debord, number_class, complete_background, path_time_log, grid_path, overwrite, extension_raster, extension_vector, format_raster, format_vector, epsg, no_data_value, percent_no_data, save_results_intermediate)

         # Mise à jour du Log
         if check_log :
            ending_event = "Ending of classification : "
            timeLine(path_time_log, ending_event)

         if debug >=1:
            print(cyan + "computeNeuralNetwork() : " + endC + "Fin de la classification avec reseau de neurones")

    # Cas d'un entrainement puis classification
    elif output_raster_path != "" and model_input == "" and groundtruth_path != "" and vector_train!="" and vector_valid !="":

         if debug >=1:
            print(f"{cyan}computeNeuralNetwork() : {endC}Début de la phase d'entrainement")

         # Mise à jour du Log
         if check_log :
            starting_event = "Starting of training phase : "
            timeLine(path_time_log, starting_event)

         # Permet de ne pas supprimer le dossier temporaire Data
         save_data = True

         # Entrainement
         model_path_temp, split_tile_vector_list, vect_temp_dir, data_temp_dir = computeTrain(groundtruth_path, input_raster_path,vector_train, vector_valid, model_output, output_raster_path, grid_path, NN, neural_network_mode, size_grid, debord, augment_training, number_class, path_time_log, save_data, overwrite, extension_raster, extension_vector, format_raster, format_vector, rand_seed, epsg, percent_no_data, save_results_intermediate)

         if debug >=1:
            print(cyan + "computeNeuralNetwork() : " + endC + "Fin de l'entrainement du réseau de neurones")
            print(cyan + "computeNeuralNetwork() : " + endC + "Début de la phase de classification")

         # Mise à jour du Log
         if check_log :
            ending_training_starting_classification_event = "Ending of training phase and starting of classification : "
            timeLine(path_time_log, ending_training_starting_classification_event)

         # Classification
         computeClassification(groundtruth_path, input_raster_path, vector_test, output_raster_path, evaluation_path, split_tile_vector_list, vect_temp_dir, data_temp_dir, model_path_temp, NN, neural_network_mode, size_grid, debord, number_class, complete_background, path_time_log, grid_path, overwrite, extension_raster, extension_vector, format_raster, format_vector, epsg, no_data_value, percent_no_data, save_results_intermediate)

         # Mise à jour du Log
         if check_log :
            ending_event = "Ending of classification : "
            timeLine(path_time_log, ending_event)

         # Dans ce cas là s'il n'y a pas model_output de renseigné et qu'on ne save pas, on supprime le modèle entrainé
         if not save_results_intermediate :
            try:
                os.remove(model_path_temp)
            except Exception:
                pass

         if debug >=1:
            print(cyan + "computeNeuralNetwork() : " + endC + "Fin de la classification avec reseau de neurones")

    # Cas d'un nouvel entrainement d'un réseau déjà existant
    elif model_input != "" and groundtruth_path != "" and vector_train !="" and vector_valid !="":

        # Mise à jour du Log
        if check_log :
            starting_event = "Starting of training phase (re training {model_input} : "
            timeLine(path_time_log, starting_event)

        # Permet supprimer le dossier temporaire Data
        save_data = False

        # Entrainement
        _,_,_,_ = computeTrain(groundtruth_path, input_raster_path,vector_train, vector_valid, model_output, output_raster_path, grid_path, NN, neural_network_mode, size_grid, debord, augment_training, number_class, path_time_log, save_data, overwrite, extension_raster, extension_vector, format_raster, format_vector, rand_seed, epsg, percent_no_data, save_results_intermediate)

        # Mise à jour du Log
        if check_log :
            ending_event = "Ending of training phase : "
            timeLine(path_time_log, starting_event)

    else :
        if debug >=1:
            print(cyan + "computeNeuralNetwork() : " + endC + "Vous n'avez pas renseignés les éléments nécessaire à un entrainnement du réseau ou à une classification" + "model_input" + model_input + "groundtruth_path" + groundtruth_path + "output_raster_path" + output_raster_path)

    # Clear la session
    keras.backend.clear_session()

    return

###########################################################################################################################################
#                                                                                                                                         #
# PARTIE FINETUNNING AVEC OPTUNA                                                                                                          #
#                                                                                                                                         #
###########################################################################################################################################
###########################################################################################################################################
# FONCTION objective()                                                                                                                    #
###########################################################################################################################################
def objective(trial, train_tile_paths, train_mask_paths, valid_tile_paths, valid_mask_paths, time_log_path):

    # On nettoye l'environnement
    keras.backend.clear_session()

    # Paramètres NN
    n_filters = trial.suggest_categorical('n_filters', [16, 32, 64])
    kernel_size = 3
    batch_size = trial.suggest_categorical('batch_size', [16, 32, 64])
    dropout_rate = trial.suggest_float('dp_rate', 0.2, 0.6, step = 0.1)

    # EarlyStopping et LearningRate
    es_patience = trial.suggest_int('es_patience', 5, 20)
    es_min_delta = trial.suggest_float('es_min_delta', 1e-5, 1e-3, log=True)
    learning_rate = trial.suggest_float('learning_rate', 1e-5, 1e-2, log = True)
    rl_patience = trial.suggest_int('rl_patience', 2, 10)
    l2_reg = trial.suggest_loguniform('l2_reg', 1e-6, 1e-2)


    # Création de l'instance NN
    NN = StructNnParameter()
    NN.batch = batch_size
    NN.number_conv_filter = n_filters
    NN.kernel_size = kernel_size
    NN.number_epoch = 100
    NN.es_monitor = 'val_loss'
    NN.es_patience = es_patience
    NN.es_min_delta = es_min_delta
    NN.es_verbose = 1
    NN.rl_monitor = 'val_loss'
    NN.rl_factor = 0.1
    NN.rl_patience = rl_patience
    NN.rl_min_lr = 1e-6
    NN.rl_verbose = 1
    NN.dp_rate = dropout_rate
    NN.l2_reg = l2_reg


    # Dossier unique pour chaque essai
    input_raster_path="/mnt/RAM_disk/stacked_treated_normalized.tif"
    result_dir = os.path.join(os.path.dirname(input_raster_path) , "results_optuna")
    os.makedirs(result_dir, exist_ok = True )

    model_output = os.path.join(result_dir, f"model_trial_{trial.number}.hdf5")
    csv_path = os.path.join(result_dir, f"history_trial_{trial.number}.csv")
    print(f"{cyan} Objective() {endC} : le nom du fichier csv est {csv_path}")

    try :
        check_log = os.path.isfile(time_log_path)
        if check_log :
            trial_event = f"Starting of trial_{trial.number} : n_filters = {n_filters} ; batch_size = {batch_size} ; es_patience = {es_patience}; es_min_delta = {es_min_delta} ; lr = {learning_rate} ; rl_patience = {rl_patience} ; dropout_rate = {dropout_rate} ; l2_reg = {l2_reg} ## "
            timeLine(time_log_path, trial_event)

        train_gen = DataGenerator(batch_size, train_tile_paths, train_mask_paths, 0, n_classes = 1, data_type = 'train', shuffle = True)
        valid_gen = DataGenerator(batch_size, valid_tile_paths, valid_mask_paths, 0, n_classes = 1, data_type = 'valid', shuffle = True)

        img_size = 256
        n_bands = 6
        n_classes = 1

        model = resunet((img_size, img_size, n_bands), n_filters, dropout_rate, l2_reg, n_classes, kernel_size, "mono")

        # On recompile le modèle car on fait évoluer le LearningRate
        metrics = ['accuracy']
        loss = keras.losses.BinaryFocalCrossentropy(apply_class_balancing=True, alpha=0.75, gamma=2) # alpha = proportion class minoriaire
        model.compile(optimizer = adam_v2.Adam(learning_rate = learning_rate), loss = loss, metrics = metrics)
        # Callback personnalisé pour le pruning Optuna
        class OptunaPruningCallback(keras.callbacks.Callback):
            def __init__(self, trial):
                self.trial = trial

            def on_epoch_end(self, epoch, logs=None):
                # Rapporte la val_loss à Optuna après chaque époque
                current_val_loss = logs.get('val_loss')
                self.trial.report(current_val_loss, epoch)

                # Vérifie si l'essai doit être interrompu
                if self.trial.should_prune():
                    print(f"Trial {self.trial.number} pruned at epoch {epoch}")
                    self.model.stop_training = True

        pruning_callback = OptunaPruningCallback(trial)
        csv_logger = CSVLogger(csv_path)
        model_checkpoint = ModelCheckpoint(model_output, monitor = 'val_loss', verbose = 1, save_best_only = True)
        early_stopping = EarlyStopping(monitor = NN.es_monitor, patience = NN.es_patience, min_delta = NN.es_min_delta, verbose = NN.es_verbose, restore_best_weights = True)
        reduce_lr = ReduceLROnPlateau(monitor = NN.rl_monitor, factor = NN.rl_factor, patience = NN.rl_patience, min_lr = NN.rl_min_lr, verbose =NN.rl_verbose, mode = 'min')

        callbacks = [model_checkpoint, early_stopping, reduce_lr, csv_logger, pruning_callback]

        history = model.fit(train_gen, epochs = NN.number_epoch, verbose = 2, callbacks = callbacks, validation_data = valid_gen)

        if trial.should_prune():
            raise optuna.TrialPruned()

        history_df = pd.read_csv(csv_path)
        best_val_loss = history_df['val_loss'].min()
        if check_log :
            end_trial_event = f"Ending trial_{trial.number} with loss = {best_val_loss}: "
            timeLine(time_log_path, end_trial_event)
        return best_val_loss

    except optuna.TrialPruned:
        if check_log :
            pruned_event = f"Trial_{trial.number} was pruned"
            timeLine(time_log_path, pruned_event)
        raise

    except Exception as e:
        print(f"Erreur pendant l'essai {trial.number}: {str(e)}")
        # En cas d'erreur, on retourne une valeur très élevée
        # Pour que cet essai soit ignoré
        return float('inf')

###########################################################################################################################################
# FONCTION computeOptimizeHyperparameters()                                                                                               #
###########################################################################################################################################
def computeOptimizeHyperparameters(n_trials = 50):

    input_raster_path="/mnt/RAM_disk/stacked_treated_normalized.tif"
    groundtruth_path="/mnt/RAM_disk/bd_topo_TM_2024_filtered_v3.tif"
    output_raster_path="/mnt/RAM_disk/classified.tif"
    train_vector="/mnt/RAM_disk/trainset1/train/train.shp"
    train_image_output = "/mnt/RAM_disk/train_classified_img"
    valid_image_output = "/mnt/RAM_disk/valid_classified_img"
    valid_vector="/mnt/RAM_disk/trainset1/valid/valid.shp"

    time_log_path = "/mnt/RAM_disk/log"
    if time_log_path != "" :
        open(time_log_path, 'a').close()
    check_log = os.path.isfile(time_log_path)

    grid_path="/mnt/RAM_disk/trainset1/Grid/stacked_grid_temp.shp"

    # Paramètres fixes pour l'entrainement
    size_grid = 256
    debord = 3
    number_class = 1
    percent_no_data = 10
    save_data = False
    neural_network_mode = "resunet"
    overwrite = False

    extension_raster = ".tif"
    extension_vector=".shp"
    format_raster='GTiff'
    format_vector='ESRI Shapefile'
    epsg = 2154

    # Pretraitement
    print(f"{cyan} OPTUNA {endC} : début prétraitement")
    train_tile_paths, train_mask_paths, train_vector_simplified, split_tile_vector_paths, vector_temp_dir, data_temp_dir = computePreTreatment(groundtruth_path, input_raster_path, train_vector, train_image_output, neural_network_mode, "Model/classified.hdf5", size_grid, debord, grid_path, overwrite, percent_no_data, extension_raster, extension_vector, format_raster, format_vector, epsg)
    valid_tile_paths, valid_mask_paths, valid_vector_simplified, split_tile_vector_paths, vector_temp_dir, data_temp_dir = computePreTreatment(groundtruth_path, input_raster_path, valid_vector, valid_image_output, neural_network_mode, "Model/classified.hdf5", size_grid, debord, grid_path, overwrite, percent_no_data,extension_raster, extension_vector, format_raster, format_vector, epsg)
    print(f"{cyan} OPTUNA {endC} : fin prétraitement")

    # Configurration du pruner pour eviter les essais peu prometteur
    pruner = optuna.pruners.MedianPruner(n_startup_trials = 5, n_warmup_steps = 20 , interval_steps = 1)
    # Création de l'étude Optuna
    print(f"{cyan} OPTUNA {endC} : début étude avec pruning")

    study = optuna.create_study(direction='minimize', pruner = pruner )
    objective_with_data = lambda trial: objective(trial, train_tile_paths, train_mask_paths, valid_tile_paths, valid_mask_paths, time_log_path)

    # Lancement de l'optimisation
    study.optimize(objective_with_data, n_trials=n_trials)

    # Affichage des meilleurs hyperparamètres
    print("Meilleurs hyperparamètres:")
    for key, value in study.best_params.items():
        print(f"{key}: {value}")

    print(f"Meilleure valeur de val_loss: {study.best_value}")
    return study.best_params

###########################################################################################################################################
# MISE EN PLACE DU PARSER                                                                                                                 #
###########################################################################################################################################

# Code executé seulement dans le cas ou le script est lancé depuis une ligne de commande ou depuis le fichier shell run_segmentation.sh
# Il n'est pas executé lors d'un import NeuralNetworkSegmentation.py

def main(gui=False):
    # Définition des arguments possibles pour l'appel en ligne de commande
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, prog="NeuralNetworkSegmentation", description="\
    Info : Segmentation supervisee  a l'aide de reseau de neurones. \n\
    Objectif : Execute une segmentation sémantique sur chaque pixels d'une images. \n\ ")

    # Paramètres

    # Directory path
    parser.add_argument('-i','--input_raster_path',default="",help="Path to the image input to classify", type=str, required=True)
    parser.add_argument('-gt','--groundtruth_path',default="",help="Path ot the groundtruth image", type=str, required=False)
    parser.add_argument('-gp', '--grid_path', default="", help="Path to the cutting grid", type=str, required=False)
    parser.add_argument('-ep', '--evaluation_path', default="", help="Path to the groundthruth for test zone", type=str, required=False)
    parser.add_argument('-o','--output_raster_path',default="",help="Path to the classified image", type=str, required=False)
    parser.add_argument('-mi','--model_input',default="",help="Neural Network already trained", type=str, required=False)
    parser.add_argument('-mo','--model_output',default="",help="Neural Network to train", type=str, required=False)

    parser.add_argument('-vtr','--vector_train',default="",help="Vector of the training dataset", type=str, required=False)
    parser.add_argument('-vv','--vector_valid',default="",help="Vector of the validation dataset", type=str, required=False)
    parser.add_argument('-vte','--vector_test',default="",help="Vector of the test dataset", type=str, required=False)

    # Input image parameters
    parser.add_argument('-sg','--size_grid',default=256,help="Size of study grid in pixels. Not used, if vector_grid_input is inquired", type=int, required=False)
    parser.add_argument('-at','--augment_training',action='store_true',default=False,help="Modify image and mask to artificially increase the dataset", required=False)
    parser.add_argument('-cb','--complete_background',action='store_true',default=False,help="Attribute the second most likely class to the pixel predicted as background", required=False)
    parser.add_argument('-deb','--debord',default=0,help="Reduce size of grid cells in pixels. Useful to avoid side effect",type=int, required=False)
    parser.add_argument('-ugc','--use_graphic_card',action='store_true',default=False,help="Use CPU for training phase", required=False)
    parser.add_argument('-igpu','--id_graphic_card',default=0,help="Id of graphic card used to classify", type=int, required=False)
    parser.add_argument('-nc','--number_class',default=0,help="Number of classes to classify", type=int, required=True)
    parser.add_argument('-nm','--neural_network_mode',default="Unet",help="Type of Neural Network (Unet | ResUnet)", type=str, required=True)
    parser.add_argument('-pnd','--percent_no_data',default=10,help="Percentage of no data allowed in an input image", type=int, required=False)


    # Hyperparameters NN
    parser.add_argument('-nn.b','--batch',default=32,help="Number of samples per gradient update", type=int, required=False)
    parser.add_argument('-nn.ncf','--number_conv_filter',default=8,help="Number of convolutional filters in one layer of Neural Network", type=int, required=False)
    parser.add_argument('-nn.ks','--kernel_size',default=3,help="Size of kernel in Neural Network", type=int, required=False)
    parser.add_argument('-nn.dp','--dp_rate',default=3,help="Rate for the SpatialDropout", type=float, required=False)
    parser.add_argument('-nn.al','--alpha_loss',default=[0.5],help="Ponderation coefficient of the focal loss", type=float, nargs='+',required=False)

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
    args = displayIHM(gui, parser)

    # CREATION STRUCTURE
    NN = StructNnParameter()

    # RECUPERATION DES ARGUMENTS

    # Récupération du chemin contenant l'image d'entrée
    if args.input_raster_path != None:
        input_raster_path = args.input_raster_path
        if input_raster_path != "" and not os.path.isfile(input_raster_path):
            raise NameError (cyan + "NeuralNetworkSegmentation : " + bold + red  + "File %s not exist!" %(input_raster_path) + endC)

    # Récupération du chemin contenant l'image d'apprentissage
    if args.groundtruth_path != None:
        groundtruth_path = args.groundtruth_path
        if groundtruth_path != "" and not os.path.isfile(groundtruth_path):
            raise NameError (cyan + "NeuralNetworkSegmentation : " + bold + red  + "File %s not exist!" %(groundtruth_path) + endC)

    # Récupération du chemin contenant la grille de découpe
    if args.grid_path != None:
        grid_path = args.grid_path
        if grid_path != "" and not os.path.isfile(grid_path):
            raise NameError (cyan + "NeuralNetworkSegmentation : " + bold + red  + "File %s not exist!" %(grid_path) + endC)

    # Récupération du chemin contenant le fichier d'évaluation
    if args.evaluation_path != None:
        evaluation_path  = args.evaluation_path
        if evaluation_path  != "" and not os.path.isfile(evaluation_path ):
            raise NameError (cyan + "NeuralNetworkSegmentation : " + bold + red  + "File %s not exist!" %(evaluation_path ) + endC)

    # Récupération du vecteur d'emprise du train dataset sous forme de polygone
    if args.vector_train != None:
        vector_train = args.vector_train
        if vector_train != "" and not os.path.isfile(vector_train):
            raise NameError (cyan + "NeuralNetworkSegmentation : " + bold + red  + "File %s not exist!" %(vector_train) + endC)

    # Récupération du vecteur d'emprise du validation dataset sous forme de polygone
    if args.vector_valid != None:
        vector_valid = args.vector_valid
        if vector_valid != "" and not os.path.isfile(vector_valid):
            raise NameError (cyan + "NeuralNetworkSegmentation : " + bold + red  + "File %s not exist!" %(vector_valid) + endC)

    # Récupération du vecteur d'emprise du train dataset sous forme de polygone
    if args.vector_test != None:
        vector_test = args.vector_test
        if vector_test != "" and not os.path.isfile(vector_test):
            raise NameError (cyan + "NeuralNetworkSegmentation : " + bold + red  + "File %s not exist!" %(vector_test) + endC)

    # Stockage de l'image classifiée
    if args.output_raster_path != None:
        output_raster_path = args.output_raster_path

    # Récupération du modèle déjà entrainé
    if args.model_input != None:
        model_input = args.model_input
        if model_input != "" and not os.path.isfile(model_input):
            raise NameError (cyan + "NeuralNetworkSegmentation : " + bold + red  + "File %s not exist!" %(model_input) + endC)

    # Récupération du modèle à entrainer
    if args.model_output != None:
        model_output = args.model_output

    # Récupération de la taille des images à découper
    if args.size_grid != None :
        size_grid = args.size_grid
        # Doit être une  puissance de 2
        #if not math.log2(size_grid).is_integer() :
            #raise NameError (cyan + "NeuralNetworkSegmentation : " + bold + red  + "%i not a correct size for an image!" %(size_grid) + endC)

    # Récupération d'un int utilisé comme un booléen pour savoir si on augmente artificiellement les données
    if args.augment_training != None :
        augment_training = args.augment_training
        if type(augment_training) != bool:
            raise NameError (cyan + "NeuralNetworkSegmentation : " + bold + red  + "augment_training takes False or True in input!" + endC)

    # Récupération d'un int utilisé comme un booléen pour savoir si on complète le background avec la deuxième classe la plus probable
    if args.complete_background != None :
        complete_background = args.complete_background
        if type(complete_background) != bool:
            raise NameError (cyan + "NeuralNetworkSegmentation : " + bold + red  + "complete_background takes False or True in input!" + endC)

    # Récupération du nombre d'échantillons qui passe dans le réseau avant une mise à jour des poids
    if args.debord != None :
        debord = args.debord
        if debord < 0 :
            raise NameError (cyan + "NeuralNetworkSegmentation : " + bold + red  + "0 and negative numbers not allowed!" + endC)

    # Récupération d'un int utilisé comme un booléen pour savoir si on utilise ou non la CPU pour effectuer les calculs
    use_graphic_card = args.use_graphic_card
    if type(use_graphic_card) != bool:
        raise NameError (cyan + "NeuralNetworkSegmentation : " + bold + red  + "use_cpu takes False or True in input!" + endC)

    # Récupération de l'identifiant de la carte graphique à utiliser
    if args.id_graphic_card != None :
        id_graphic_card = args.id_graphic_card
        if (id_graphic_card < 0):
            raise NameError (cyan + "NeuralNetworkSegmentation : " + bold + red  + "%i not a correct number!" %(id_graphic_card) + endC)

    # Récupération du nombre de classes pour classifier avec le réseau
    # Ajoute une classe no_data lorsque l'on est dans une classification à plus d'une classe
    if args.number_class != None :
        if (args.number_class < 1):
            raise NameError (cyan + "NeuralNetworkSegmentation : " + bold + red  + "%i not a correct number of classes!" %(args.number_class) + endC)

        if args.number_class != 1 :
            # Ajout de la classe background
            number_class = args.number_class + 1
            #number_class = args.number_class
        else :
            number_class = args.number_class

    # Récupération du type de réseau de neurones
    if args.neural_network_mode != None:
        neural_network_mode = args.neural_network_mode
        if neural_network_mode.lower() != "resunet":
            raise NameError (cyan + "NeuralNetworkSegmentation : " + bold + red  + "Not a good name! (Resunet)" + endC)

    # Récupération du pourcentage de no data autoriser dans une imagette
    if args.percent_no_data != None :
        percent_no_data = args.percent_no_data
        if (percent_no_data < 0):
            raise NameError (cyan + "NeuralNetworkSegmentation : " + bold + red  + "%i not a correct number!" %(percent_no_data) + endC)

    # Récupération du nombre d'échantillons qui passe dans le réseau avant une mise à jour des poids
    if args.batch != None :
        NN.batch = args.batch
        if NN.batch <= 0 :
            raise NameError (cyan + "NeuralNetworkSegmentation : " + bold + red  + "0 and negative numbers not allowed!" + endC)

    # Récupération du nombre de filtres convolutifs appliqués à chaque couche du réseau
    if args.number_conv_filter != None :
        NN.number_conv_filter = args.number_conv_filter
        if NN.number_conv_filter <= 0 :
            raise NameError (cyan + "NeuralNetworkSegmentation : " + bold + red  + "0 and negative numbers not allowed!" + endC)

    # Récupération du nombre de filtres convolutifs appliqués à chaque couche du réseau
    if args.kernel_size != None :
        NN.kernel_size = args.kernel_size
        if NN.kernel_size <= 0 :
            raise NameError (cyan + "NeuralNetworkSegmentation : " + bold + red  + "0 and negative numbers not allowed!" + endC)

    # Récupération du taux de dropout
    if args.dp_rate != None :
        NN.dp_rate = args.dp_rate
        if NN.dp_rate <= 0 :
            raise NameError (cyan + "NeuralNetworkSegmentation : " + bold + red  + "0 and negative numbers not allowed!" + endC)

    # Récupération de la pondération de la focal loss
    if args.alpha_loss != None :
        if len(args.alpha_loss) != number_class:
            NN.alpha_loss = (args.alpha_loss * number_class)[:number_class]
        else :
            NN.alpha_loss = args.alpha_loss
    total = sum(NN.alpha_loss)
    NN.alpha_loss = [x/total for x in NN.alpha_loss]


    # Récupération du nombre d'époques pour entrainer le réseau
    if args.number_epoch != None :
        NN.number_epoch = args.number_epoch
        if NN.number_epoch <=0 :
            raise NameError (cyan + "NeuralNetworkSegmentation : " + bold + red  + "0 and negative numbers not allowed!" + endC)

    # Récupération de ceux qui doit être surveillé pour l'early stopping
    if args.early_stopping_monitor != None:
        NN.es_monitor = args.early_stopping_monitor

    # Récupération du nombre d'époque après lequel l'entrainement va s'arrêter s'il n'y a pas eu d'amélioration
    if args.early_stopping_patience != None :
        NN.es_patience = args.early_stopping_patience
        if NN.es_patience <=0 :
            raise NameError (cyan + "NeuralNetworkSegmentation : " + bold + red  + "0 and negative numbers not allowed!" + endC)

    # Récupération de la valeur minimale que peut atteindre le delta
    if args.early_stopping_min_delta != None :
        NN.es_min_delta = args.early_stopping_min_delta
        if NN.es_min_delta>1 or NN.es_min_delta<=0:
            raise NameError (cyan + "NeuralNetworkSegmentation : " + bold + red  + "number must be between 0 and 1!" + endC)

    # Récupération de ceux qui doit être surveillé pour le learning rate
    if args.reduce_learning_rate_monitor != None:
        NN.rl_monitor = args.reduce_learning_rate_monitor

    # Récupération d'un float qui determine de combien va être réduit le learning rate
    if args.reduce_learning_rate_factor != None :
        NN.rl_factor = args.reduce_learning_rate_factor
        # Doit être inférieur à 1 pour réduire
        if NN.rl_factor>=1 or NN.rl_factor<=0:
            raise NameError (cyan + "NeuralNetworkSegmentation : " + bold + red  + "number must be strictly between 0 and 1!" + endC)

    # Récupération du nombre d'époque après lequel le learning rate va diminuer s'il n'y a pas eu d'amélioration reduce_learning_rate_patience
    if args.reduce_learning_rate_patience != None :
        NN.rl_patience = args.reduce_learning_rate_patience
        if NN.rl_patience <=0 :
            raise NameError (cyan + "NeuralNetworkSegmentation : " + bold + red  + "0 and negative numbers not allowed!" + endC)

    # Récupération de la valeur minimale que peut atteindre le learning rate reduce_learning_rate_min_lr
    if args.reduce_learning_rate_min_lr != None :
        NN.rl_min_lr = args.reduce_learning_rate_min_lr
        if NN.rl_min_lr<=0:
            raise NameError (cyan + "NeuralNetworkSegmentation : " + bold + red  + "number must be above 0!" + endC)

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

    # Affichage des arguments récupérés
    if debug >= 3:
        print(bold + green + "Variables dans le parser" + endC)

        # Directory path
        print(cyan + "NeuralNetworkSegmentation : " + endC + "input_raster_path : " + input_raster_path + endC)
        print(cyan + "NeuralNetworkSegmentation : " + endC + "groundtruth_path : " + groundtruth_path + endC)
        print(cyan + "NeuralNetworkSegmentation : " + endC + "grid_path : " + grid_path + endC)
        print(cyan + "NeuralNetworkSegmentation : " + endC + "evaluation_path : " + evaluation_path + endC)
        print(cyan + "NeuralNetworkSegmentation : " + endC + "output_raster_path : " + output_raster_path + endC)
        print(cyan + "NeuralNetworkSegmentation : " + endC + "model_input : " + model_input + endC)
        print(cyan + "NeuralNetworkSegmentation : " + endC + "model_output : " + model_output + endC)

        print(cyan + "NeuralNetworkSegmentation : " + endC + "vector_train : " + vector_train + endC)
        print(cyan + "NeuralNetworkSegmentation : " + endC + "vector_valid : " + vector_valid + endC)
        print(cyan + "NeuralNetworkSegmentation : " + endC + "vector_test : " + vector_test + endC)


        print(cyan + "NeuralNetworkSegmentation : " + endC + "augment_training : " + str(augment_training) + endC)
        print(cyan + "NeuralNetworkSegmentation : " + endC + "complete_background : " + str(complete_background) + endC)
        print(cyan + "NeuralNetworkSegmentation : " + endC + "size_grid : " + str(size_grid) + endC)
        print(cyan + "NeuralNetworkSegmentation : " + endC + "debord : " + str(debord) + endC)
        print(cyan + "NeuralNetworkSegmentation : " + endC + "number_class : " + str(number_class) + endC)
        print(cyan + "NeuralNetworkSegmentation : " + endC + "use_graphic_card : " + str(use_graphic_card) + endC)
        print(cyan + "NeuralNetworkSegmentation : " + endC + "id_graphic_card : " + str(id_graphic_card) + endC)
        print(cyan + "NeuralNetworkSegmentation : " + endC + "neural_network_mode : " + neural_network_mode + endC)
        print(cyan + "NeuralNetworkSegmentation : " + endC + "percent_no_data : " + str(percent_no_data) + endC)

        # Hyperparameters NN
        print(cyan + "NeuralNetworkSegmentation : " + endC + "batch : " + str(NN.batch) + endC)
        print(cyan + "NeuralNetworkSegmentation : " + endC + "number_conv_filter : " + str(NN.number_conv_filter) + endC)
        print(cyan + "NeuralNetworkSegmentation : " + endC + "kernel_size : " + str(NN.kernel_size) + endC)
        print(cyan + "NeuralNetworkSegmentation : " + endC + "dropout_rate : " + str(NN.dp_rate) + endC)
        print(cyan + "NeuralNetworkSegmentation : " + endC + "alpha_loss : " + str(NN.alpha_loss) + endC)
        print(cyan + "NeuralNetworkSegmentation : " + endC + "number_epoch : " + str(NN.number_epoch) + endC)
        print(cyan + "NeuralNetworkSegmentation : " + endC + "es_monitor : " + NN.es_monitor + endC)
        print(cyan + "NeuralNetworkSegmentation : " + endC + "es_patience : " + str(NN.es_patience) + endC)
        print(cyan + "NeuralNetworkSegmentation : " + endC + "es_min_delta : " + str(NN.es_min_delta) + endC)
        print(cyan + "NeuralNetworkSegmentation : " + endC + "rl_monitor : " + NN.rl_monitor + endC)
        print(cyan + "NeuralNetworkSegmentation : " + endC + "rl_factor : " + str(NN.rl_factor) + endC)
        print(cyan + "NeuralNetworkSegmentation : " + endC + "rl_patience : " + str(NN.rl_patience) + endC)
        print(cyan + "NeuralNetworkSegmentation : " + endC + "rl_min_lr : " + str(NN.rl_min_lr) + endC)

        # A CONSERVER
        print(cyan + "NeuralNetworkSegmentation : " + endC + "rand_seed : " + str(rand_seed) + endC)
        print(cyan + "NeuralNetworkSegmentation : " + endC + "ram_otb : " + str(ram_otb) + endC)
        print(cyan + "NeuralNetworkSegmentation : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "NeuralNetworkSegmentation : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "NeuralNetworkSegmentation : " + endC + "format_raster : " + format_raster + endC)
        print(cyan + "NeuralNetworkSegmentation : " + endC + "format_vector : " + format_vector + endC)
        print(cyan + "NeuralNetworkSegmentation : " + endC + "extension_raster : " + extension_raster + endC)
        print(cyan + "NeuralNetworkSegmentation : " + endC + "extension_vector : " + extension_vector + endC)
        print(cyan + "NeuralNetworkSegmentation : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "NeuralNetworkSegmentation : " + endC + "save_results_inter : " + str(save_results_intermediate) + endC)
        print(cyan + "NeuralNetworkSegmentation : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "NeuralNetworkSegmentation : " + endC + "debug : " + str(debug) + endC)

        # Appel de la fonction principale
        computeNeuralNetwork(input_raster_path, groundtruth_path, grid_path, evaluation_path, vector_train, vector_valid, vector_test, output_raster_path, model_input, model_output, NN, use_graphic_card, id_graphic_card, neural_network_mode, augment_training, complete_background, size_grid, debord, number_class, path_time_log, extension_raster, extension_vector, format_raster, format_vector, rand_seed, epsg, percent_no_data, no_data_value, save_results_intermediate, overwrite)
# ================================================

if __name__ == '__main__':
  main(gui=False)
