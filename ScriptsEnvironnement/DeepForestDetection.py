#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT QUI APPLIQUE UNE DETECTION DES ARBRES PAR RESEAU DE NEURONES                                                                       #
#                                                                                                                                           #
#############################################################################################################################################
"""
Nom de l'objet : DeepForestDetection.py
Description :
Objectif : exécute une détéction des arbres via réseaux de neurones d'une seule image satellite en creant une polygone énglobant pour chaque arbre

Date de creation : 13/04/2022
----------
Histoire :
----------
Origine : le script originel provient de l étude mener par Ludovic Randon en formation en alternance en ID à DterMed
--------------------------------------------------------------------------------------------------------------------
Modifications

------------------------------------------------------
https://github.com/weecology/DeepForest-pytorch/releases/tag/v0.1.17
https://github.com/mittrees/Treepedia_Public/tree/master/Treepedia
https://deepforest.readthedocs.io/en/latest/getting_started.html#saving-and-loading-models
https://deepforest.readthedocs.io/en/latest/_modules/deepforest/main.html
https://deepforest.readthedocs.io/en/latest/_modules/deepforest/main.html
https://deepforest.readthedocs.io/en/latest/ConfigurationFile.html
https://github.com/mtourne/marseille_trees/blob/main/deepforest_marseille/save%20deepforest%20prediction%20to%20prodigy%20for%20human%20augmentation.ipynb
https://github.com/waspinator/deep-learning-explorer/blob/master/mask-rcnn/docker/keras.dockerfile
"""

##### Import genéreaux #####

import os, time, argparse, threading

#from tqdm import tqdm

##### Import lib images #####
import numpy as np
from PIL import Image
#from libtiff import TIFFimage

##### Import Geospatial packages #####
from osgeo import gdal, osr, ogr
from osgeo.gdalnumeric import *
from osgeo.gdalconst import *
import osgeo.gdalnumeric as gdn

import shapely
import pandas
import geopandas
import rasterio

##### Import matplotlib #####
from matplotlib import pyplot as plt
from matplotlib.patches import Rectangle
import matplotlib.image as img

##### Import propre au reseau de neurone deepforest #####
import torch
import torchvision.models as models
import deepforest
from deepforest import main
from deepforest import preprocess
from deepforest import utilities
from deepforest import get_data
from deepforest import __version__

##### Import des lib interne #####
from Lib_log import timeLine
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_file import removeVectorFile, renameVectorFile, removeFile, deleteDir
from Lib_text import fillTableFiles, writeTextFile, appendTextFileCR
from Lib_operator import getNumberCPU
from Lib_vector import saveVectorFromDataframe, simplifyVector, createGridVector, splitVector, cutVectorAll, createPolygonsFromCoordList, intersectVector, getNumberFeature, getGeometryType, getGeomPolygons, filterSelectDataVector, renameFieldsVector
from Lib_raster import getProjectionImage, getEmpriseVector, getPixelWidthXYImage, getGeometryImage, getEmpriseImage, getNodataValueImage, getPixelWidthXYImage, cutImageByVector, createVectorMask, cutImageByGrid
from CrossingVectorRaster import statisticsVectorRaster

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 3


###########################################################################################################################################
#def bgr2rgb(numpy_image):
#    return numpy_image[...,::-1]

###########################################################################################################################################
# FONCTION createTrainConfigCsv()                                                                                                         #
###########################################################################################################################################
def createTrainConfigCsv(image_path_list, train_vector_path_list, train_file_csv, size_grid, label="Tree", format_vector='ESRI Shapefile'):
    """
    # ROLE:
    #    Créer le fichier de configuration au format CSV contenant les informations de données d'entrainement deu réseau
    #    au format : image_path,xmin,ymin,xmax,ymax,label  => exemple ImagetteXX.tif,25,99,28,140,Tree
    #
    # ENTREES DE LA FONCTION :
    #    image_path_list (string) : liste des fichiers les imagettes découpés
    #    train_vector_path_list (string) : liste des fichiers les vecteurs d'aprentissage
    #    train_file_csv (string) : le chemin complet du fichier CSV de configuration de l'apprentissage
    #    size_grid (int) : dimension d'une cellule de la grille de découpe de l'image satellite initiale
    #    label (string) : la valeur du label (par default : Tree)
    #    format_vector (string) : format des vecteurs
    #
    # SORTIES DE LA FONCTION :
    #    Remplit le fichier .scv passer en entréé
    """

    # Entête du fichier
    HEADER_FILE = "image_path,xmin,ymin,xmax,ymax,label\n"

    # Creer le fichier vide
    writeTextFile(train_file_csv, HEADER_FILE)

    # Get pixel size image
    if os.path.exists(image_path_list[0]) :

        pixel_width, pixel_height = getPixelWidthXYImage(image_path_list[0])

        # Pour toutes les imagettes verifier qu'il existe des données d'apprentissage associées
        for index in range (len(image_path_list)) :
            image_train = image_path_list[index]
            vector_train = train_vector_path_list[index]
            ima_x_min, ima_x_max, ima_y_min, ima_y_max = getEmpriseImage(image_train)
            cols, rows, bands = getGeometryImage(image_train)

            if debug >= 6:
                print("Vector = " + str(vector_train))
                print("Image = " + str(image_train))
                print("ima_x_min = " +  str(ima_x_min))
                print("ima_x_max = " +  str(ima_x_max))
                print("ima_y_min = " +  str(ima_y_min))
                print("ima_y_max = " +  str(ima_y_max))

            # Identifier si le fichier vecteur contient de la donnée
            if (getNumberFeature(vector_train, format_vector) > 0) and (getGeometryType(vector_train, format_vector) in ('POLYGON', 'MULTIPOLYGON')) :

                geom_list = getGeomPolygons(vector_train, None, None, format_vector)
                # Pour tout les polygones
                for geom in geom_list :
                    poly_x_min, poly_x_max, poly_y_min, poly_y_max = geom.GetEnvelope()

                    x_min = round((poly_x_min - ima_x_min) / pixel_width)
                    x_max = round((poly_x_max - ima_x_min) / pixel_width)
                    y_min = cols - round((poly_y_max - ima_y_min) / pixel_height)
                    y_max = cols - round((poly_y_min - ima_y_min) / pixel_height)

                    if x_min < 0 :
                        x_min = 0
                    if x_min > size_grid:
                        x_min = size_grid

                    if x_max < 0 :
                        x_max = 0
                    if x_max > size_grid:
                        x_max = size_grid

                    if y_min < 0 :
                        y_min = 0
                    if y_min > size_grid:
                        y_min = size_grid

                    if y_max < 0 :
                        y_max = 0
                    if y_max > size_grid:
                        y_max = size_grid

                    if debug >= 6:
                        print("Vector = " + str(vector_train))
                        print("Image = " + str(image_train))
                        #print("Polygone = " + str(geom))
                        print("poly_x_min = " +  str(poly_x_min))
                        print("poly_x_max = " +  str(poly_x_max))
                        print("poly_y_min = " +  str(poly_y_min))
                        print("poly_y_max = " +  str(poly_y_max))
                        print("x_min = " +  str(x_min))
                        print("x_max = " +  str(x_max))
                        print("y_min = " +  str(y_min))
                        print("y_max = " +  str(y_max))
                        print("width = " +  str(x_max-x_min))
                        print("heigth = " +  str(y_max-y_min))

                    # Show Image
                    '''
                    raster = Image.open(image_train, mode='r')
                    fig, ax = plt.subplots()
                    plt.imshow(raster)
                    ax = plt.gca()
                    rect = Rectangle((x_min, y_min), x_max-x_min , y_max-y_min, linewidth=1, edgecolor='r', facecolor='none')
                    ax.add_patch(rect)
                    plt.show()
                    '''
                    text = image_train + ',' + str(x_min) + ',' + str(y_min) + ',' + str(x_max) + ',' + str(y_max) + ',' + label
                    appendTextFileCR(train_file_csv, text)
    return

###########################################################################################################################################
# FONCTION decoupeImageTraining()                                                                                                         #
###########################################################################################################################################
def decoupeImageTraining( training_input, vector_training_input, path_output, size_grid, debord, epsg=2154, folder_imagette="Imagette", folder_train="Train",  folder_grid="Grid", extension_raster=".tif", extension_vector=".shp", format_raster='GTiff', format_vector='ESRI Shapefile',  overwrite=True):
    """
    # ROLE:
    #    Pré-traitement de l'image qui va être découpée en imagettes pour pouvoir entrer en entrée du réseau de neurones
    #
    # ENTREES DE LA FONCTION :
    #    training_input (string) : l'image satellite d'apprentissage
    #    vector_training_input (string) : le fichier vecteur contenant les polygones d'apprentissage
    #    path_output (string) : chemin de sortie contenant les imagettes et vecteur découpé
    #    size_grid (int) : dimension d'une cellule de la grille de découpe de l'image satellite initiale
    #    debord (int) : utilisé pour éviter les effets de bord. Agrandit artificiellement les imagettes
    #    epsg (int) : Identificateur de projection
    #    folder_imagette (int) : nom du sous répertoire contenant les imagettes découpé selon la grille + le débord
    #    folder_train (int) :  nom du sous répertoire contenant les vecteurs de données d'apprentissage découpé selon la grille + le débord
    #    folder_grid (int) :  nom du sous répertoire contenant les vecteurs de coupe des carrés de grille
    #    extension_raster (string) : extension de fichier des imagettes
    #    extension_vector (string) : extension de fichier des vecteurs
    #    format_raster (string) : format des imagettes
    #    format_vector (string) : format des vecteurs
    #    overwrite (bool) : booléen pour écrire ou non par dessus un fichier existant
    #
    # SORTIES DE LA FONCTION :
    #    Renvoie la liste output_image_path_list contenant les imagettes de decoupe
    #    et la liste output_train_vector_path_list contenant les vecteurs d'aprentissage
    """

    # Constantes pour les dossiers et fichiers
    SIMPLIFY_VECTOR_VALUE = 2.0
    FIELD_NAME = "sub_name"
    BASE_NAME_IMAGETTE = "sat_"
    BASE_NAME_TRAIN = "train_"

    SUFFIX_MASK_CRUDE = "_crude"
    SUFFIX_VECTOR_SIMPLIFY = "_vect_simplify"
    SUFFIX_EMPRISE = "_emprise"
    SUFFIX_GRID = "_grid"
    SUFFIX_BUFF = "_buff"
    SUFFIX_INTER = "_inter"

    # Récupération de la taille d'un pixel
    pixel_size, _  = getPixelWidthXYImage(training_input)
    imagette_dimension = size_grid * pixel_size

    # Création du dossier s'il n'existe pas déjà
    if not os.path.isdir(path_output):
        os.makedirs(path_output)
    else :
        # Nettoyage du dossier temporaire
        deleteDir(path_output)
        os.makedirs(path_output)

    # Récupération du nom de l'image et de la valeur de nodata
    image_name = os.path.splitext(os.path.basename(training_input))[0]
    cols, rows, num_band = getGeometryImage(training_input)
    no_data_value = getNodataValueImage(training_input, num_band)
    if no_data_value == None :
        no_data_value = 0

    # Creation du vecteur d'emprise de la zone d entrainement

    # Création du masque délimitant l'emprise de la zone par image
    vector_mask = path_output + os.sep + image_name + SUFFIX_MASK_CRUDE + extension_vector
    createVectorMask(training_input, vector_mask, no_data_value, format_vector)

    # Simplification du masque
    vector_simple_mask = path_output + os.sep + image_name + SUFFIX_VECTOR_SIMPLIFY + extension_vector
    simplifyVector(vector_mask, vector_simple_mask, SIMPLIFY_VECTOR_VALUE, format_vector)

    # Creation d'un vecteur multiple des dimension de la grille
    vector_emprise_grid = path_output + os.sep + image_name + SUFFIX_EMPRISE + SUFFIX_GRID + extension_vector
    xmin,xmax,ymin,ymax = getEmpriseVector(vector_simple_mask, format_vector)
    dimension_grid = imagette_dimension - (debord * pixel_size) * 2

    if ((xmax - xmin) % dimension_grid) > 0 :
        factor_x = 1
    else :
        factor_x = 0
    if ((ymax - ymin) % dimension_grid) > 0 :
        factor_y = 1
    else :
        factor_y = 0

    width = ((xmax - xmin) // dimension_grid) * dimension_grid + (factor_x * dimension_grid)
    height = ((ymax - ymin) // dimension_grid) * dimension_grid + (factor_y * dimension_grid)
    if debug >= 6:
        print("dimension_grid = " + str(dimension_grid))
        print("xmin = " + str(xmin))
        print("ymin = " + str(ymin))
        print("xmax = " + str(xmax))
        print("ymax = " + str(ymax))
        print("l = " + str(xmax - xmin))
        print("h = " + str(ymax - ymin))
        print("div_x = " + str((xmax - xmin) // dimension_grid))
        print("div_y = " + str((ymax - ymin) // dimension_grid))
        print("width = " + str(width))
        print("height =" + str(height))

    x1 = xmin                                        # x1,y1          x2,y2
    y1 = ymax                                        #    ---------------
    x2 = xmin + width                                #    |             |
    y2 = ymax                                        #    |             |
    x3 = xmin + width                                #    |             |
    y3 = ymax - height                               #    |             |
    x4 = xmin                                        #    ---------------
    y4 = ymax - height                               # x4,y4          x3,y3

    polygons_attr_coord_dico = {1:[[x1, y1, x2, y2, x3, y3, x4, y4], {}]}
    createPolygonsFromCoordList({}, polygons_attr_coord_dico, vector_emprise_grid, epsg, format_vector)

    # Initialisation des listes de sortie
    output_image_path_list = []
    output_train_vector_path_list = []

    # Creer le fichier grille
    vector_grid_temp = path_output + os.sep + image_name + SUFFIX_GRID + extension_vector
    grid_ligne, grid_colonne = createGridVector(vector_emprise_grid, vector_grid_temp, dimension_grid, dimension_grid, None, overwrite, epsg , format_vector)

    # Intersection de la grille sur l'emprise
    vector_grid_temp_inter = path_output + os.sep + image_name + SUFFIX_GRID + SUFFIX_INTER + extension_vector
    intersectVector(vector_simple_mask, vector_grid_temp, vector_grid_temp_inter, overwrite, format_vector)

    # Création du dossier contenant les imagettes s'il n'existe pas déjà
    repertory_data_imagette_temp = path_output + os.sep + folder_imagette
    if not os.path.isdir(repertory_data_imagette_temp):
        os.makedirs(repertory_data_imagette_temp)

    # Création du dossier contenant les vecteurs d'apprentissage s'il n'existe pas déjà
    repertory_data_train_temp = path_output + os.sep + folder_train
    if not os.path.isdir(repertory_data_train_temp):
        os.makedirs(repertory_data_train_temp)

    # Création du dossier contenant les polygones de la grille s'il n'existe pas déjà
    repertory_data_grid_temp = path_output + os.sep + folder_grid
    if not os.path.isdir(repertory_data_grid_temp):
        os.makedirs(repertory_data_grid_temp)

    # Extraire chaque polygone en un fichier vector_grid_temp_inter
    split_tile_vector_list = splitVector(vector_grid_temp_inter, repertory_data_grid_temp, FIELD_NAME, epsg, format_vector, extension_vector)
    if debug >= 4:
        print(cyan + "decoupeImageTraining() : " + endC + "len(split_tile_vector_list) : " + str(len(split_tile_vector_list)))

    # Récupération des dimensions des la listes des vecteurs de découpe
    number_vector = len(split_tile_vector_list)

    # Initialisation des deux matrices
    training_table = []
    input_table = []
    for i in range(grid_ligne):
        input_table.append([])
        training_table.append([])

    # Récupération du nombre de vecteurs de découpe et définition du nombre de threads à utiliser
    number_CPU = int(getNumberCPU()/2)
    rapport_division_CPU = number_vector // number_CPU
    rapport_modulo_CPU = number_vector % number_CPU
    if debug >= 3:
        print(cyan + "decoupeImageTraining() : " + endC + "number_vector :" + str(number_vector  ))
        print(cyan + "decoupeImageTraining() : " + endC + "number_ligne :" + str(grid_ligne  ))
        print(cyan + "decoupeImageTraining() : " + endC + "number_colonne :" + str(grid_ligne  ))
        print(cyan + "decoupeImageTraining() : " + endC + "number_CPU :" + str(number_CPU  ))
        print(cyan + "decoupeImageTraining() : " + endC + "rapport_division_CPU :" + str(rapport_division_CPU))
        print(cyan + "decoupeImageTraining() : " + endC + "rapport_modulo_CPU :" + str(rapport_modulo_CPU))

    # Découpage de l'image d'entrée
    for i in range(rapport_division_CPU):
        # Initialisation de la liste pour le multi-threading
        thread_list = []
        for j in range(number_CPU):
            output_image = fillTableFiles(split_tile_vector_list[(i * number_CPU) + j], input_table, repertory_data_imagette_temp, BASE_NAME_IMAGETTE, extension_raster)
            output_image_path_list.append(output_image)
            if debug >= 4:
                print(cyan + "decoupeImageTraining() : " + endC + "Output image :" + output_image)
            if debug >= 2 :
                print(cyan + "decoupeImageTraining() : " + endC + "Traitement de la tuile " + str((i * number_CPU) + j + 1) + "/" + str(number_vector) + "...")

            if os.path.exists(split_tile_vector_list[(i * number_CPU) + j]):
                # Découpage de l'image par multi-threading
                image_tmp = split_tile_vector_list[i * number_CPU + j]
                thread = threading.Thread(target=cutImageByGrid, args=(image_tmp, training_input, output_image, dimension_grid, dimension_grid, debord, pixel_size, pixel_size, no_data_value, epsg, format_raster, format_vector))
                thread.start()
                thread_list.append(thread)

        # Attente fin de tout les threads
        try:
            for thread in thread_list:
                thread.join()
        except:
            print(cyan + "decoupeImageTraining() : " + bold + red + "Erreur lors de le decoupe : impossible de demarrer le thread" + endC, file=sys.stderr)

    # Initialisation de la liste pour le multi-threading
    thread_list = []
    for i in range(rapport_modulo_CPU):

        output_image = fillTableFiles(split_tile_vector_list[(rapport_division_CPU * number_CPU) + i], input_table, repertory_data_imagette_temp, BASE_NAME_IMAGETTE, extension_raster)
        output_image_path_list.append(output_image)
        if debug >= 4:
            print(cyan + "decoupeImageTraining() : " + endC + "Output image :" + output_image)
        if debug >= 2 :
            print(cyan + "decoupeImageTraining() : " + endC + "Traitement de la tuile " + str((rapport_division_CPU * number_CPU) + i + 1) + "/" + str(number_vector) + "...")

        if os.path.exists(split_tile_vector_list[(rapport_division_CPU * number_CPU) + i]):

            # Découpage de l'image par multi-threading
            image_tmp = split_tile_vector_list[rapport_division_CPU * number_CPU + i]
            thread = threading.Thread(target=cutImageByGrid, args=(image_tmp, training_input, output_image, dimension_grid, dimension_grid, debord, pixel_size, pixel_size, no_data_value, epsg, format_raster, format_vector))
            thread.start()
            thread_list.append(thread)

    # Attente fin de tout les threads
    try:
        for thread in thread_list:
            thread.join()
    except:
        print(cyan + "decoupeImageTraining() : " + bold + red + "Erreur lors de le decoupe : impossible de demarrer le thread" + endC, file=sys.stderr)

    if vector_training_input != "" :

        # Découpage des données vecteur d'entrainement
        for i in range(rapport_division_CPU):
            # Initialisation de la liste pour le multi-threading
            thread_list = []
            for j in range(number_CPU):
                output_train_vector = fillTableFiles(split_tile_vector_list[(i * number_CPU) + j], training_table, repertory_data_train_temp, BASE_NAME_TRAIN, extension_vector)
                output_train_vector_path_list.append(output_train_vector)
                if debug >= 4:
                    print(cyan + "decoupeImageTraining() : " + endC + "Output train vector : " + output_train_vector)
                if debug >= 2 :
                    print(cyan + "decoupeImageTraining() : " + endC + "Traitement du vecteur d'apprentissage : " + str((i * number_CPU) + j + 1) + "/" + str(number_vector) + "...")

                # Découpage du masque
                if os.path.exists(split_tile_vector_list[(i * number_CPU) + j]):

                    # Découpage du vecteur par multi-threading
                    vector_tmp = split_tile_vector_list[i * number_CPU + j]
                    vector_cut_buf = os.path.splitext(vector_tmp)[0] + SUFFIX_BUFF + extension_vector
                    xmin,xmax,ymin,ymax = getEmpriseVector(vector_tmp, format_vector)
                    x1 = xmin - debord * pixel_size                  # x1,y1          x2,y2
                    y1 = ymax + debord * pixel_size                  #    ---------------
                    x2 = xmax + debord * pixel_size                  #    |             |
                    y2 = ymax + debord * pixel_size                  #    |             |
                    x3 = xmax + debord * pixel_size                  #    |             |
                    y3 = ymin - debord * pixel_size                  #    |             |
                    x4 = xmin - debord * pixel_size                  #    ---------------
                    y4 = ymin - debord * pixel_size                  # x4,y4          x3,y3
                    polygons_attr_coord_dico = {1:[[x1, y1, x2, y2, x3, y3, x4, y4], {}]}
                    createPolygonsFromCoordList({}, polygons_attr_coord_dico, vector_cut_buf, epsg, format_vector)
                    thread = threading.Thread(target=cutVectorAll, args=(vector_cut_buf, vector_training_input, output_train_vector, overwrite, format_vector))
                    thread.start()
                    thread_list.append(thread)

            # Attente fin de tout les threads
            try:
                for thread in thread_list:
                    thread.join()
            except:
                print(cyan + "decoupeImageTraining() : " + bold + red + "Erreur lors de le decoupe : impossible de demarrer le thread" + endC, file=sys.stderr)

        # Initialisation de la liste pour le multi-threading
        thread_list = []
        for i in range(rapport_modulo_CPU):

            output_train_vector = fillTableFiles(split_tile_vector_list[(rapport_division_CPU * number_CPU) + i], training_table, repertory_data_train_temp, BASE_NAME_TRAIN, extension_vector)
            output_train_vector_path_list.append(output_train_vector)
            if debug >= 4:
                print(cyan + "decoupeImageTraining() : " + endC + "Output train vector :" + output_train_vector)
            if debug >= 2 :
                print(cyan + "decoupeImageTraining() : " + endC + "Traitement du vecteur d'apprentissage : " + str((rapport_division_CPU * number_CPU) + i + 1) + "/" + str(number_vector) + "...")

            if os.path.exists(split_tile_vector_list[(rapport_division_CPU * number_CPU) + i]):
                # Découpage du vecteur par multi-threading
                vector_tmp = split_tile_vector_list[(rapport_division_CPU * number_CPU) + i]
                vector_cut_buf = os.path.splitext(vector_tmp)[0] + SUFFIX_BUFF + extension_vector
                xmin,xmax,ymin,ymax = getEmpriseVector(vector_tmp, format_vector)
                x1 = xmin - debord * pixel_size                  # x1,y1          x2,y2
                y1 = ymax + debord * pixel_size                  #    ---------------
                x2 = xmax + debord * pixel_size                  #    |             |
                y2 = ymax + debord * pixel_size                  #    |             |
                x3 = xmax + debord * pixel_size                  #    |             |
                y3 = ymin - debord * pixel_size                  #    |             |
                x4 = xmin - debord * pixel_size                  #    ---------------
                y4 = ymin - debord * pixel_size                  # x4,y4          x3,y3
                polygons_attr_coord_dico = {1:[[x1, y1, x2, y2, x3, y3, x4, y4], {}]}
                createPolygonsFromCoordList({}, polygons_attr_coord_dico, vector_cut_buf, epsg, format_vector)
                thread = threading.Thread(target=cutVectorAll, args=(vector_cut_buf, vector_training_input, output_train_vector, overwrite, format_vector))
                thread.start()
                thread_list.append(thread)

        # Attente fin de tout les threads
        try:
            for thread in thread_list:
                thread.join()
        except:
            print(cyan + "decoupeImageTraining() : " + bold + red + "Erreur lors de le decoupe : impossible de demarrer le thread" + endC, file=sys.stderr)

    return output_image_path_list, output_train_vector_path_list

###########################################################################################################################################
# FONCTION cleanFilteredPredictionVector()                                                                                                #
###########################################################################################################################################
def cleanFilteredPredictionVector(image_ndvi_input, vector_predict_input, vector_output, threshold_ndvi_value, path_time_log, no_data_value, extension_vector, format_vector, save_results_intermediate, overwrite) :
    """
    # ROLE:
    #    Netoyage des boites englobantes par supression des boites ayant une valeur moyen de NDVI trop faible
    #
    # ENTREES DE LA FONCTION :
    #    image_ndvi_input (string) : le NDVI de l'image satellite d'entrée à detecter
    #    vector_predict_input (string) : le vecteur contenant les boites englobantes à nettoyer
    #    vector_output (string) : le vecteur final contenant les boites englobantes des arbres
    #    threshold_ndvi_value (float) : valeur de seuillage du NDVI moyen des boites englobantes
    #    path_time_log (string) : le fichier de log de sortie
    #    no_data_value (int) : valeur que prend un pixel qui ne contient pas d'information
    #    extension_vector (string) : extension de fichier des vecteurs
    #    format_vector (string) : format des vecteurs
    #    save_results_intermediate (bool) : booléen qui determine si on sauvegarde ou non les fichiers temporaires
    #    overwrite (bool) : booléen pour écrire ou non par dessus un fichier existant
    #
    #
    # SORTIES DE LA FONCTION :
    #    None
    """

    # Constantes
    SUFFIX_SAT = "_sat"

    COLUMN_XMIN = "xmin"
    COLUMN_YMIN = "ymin"
    COLUMN_XMAX = "xmax"
    COLUMN_YMAX = "ymax"
    COLUMN_LABEL = "label"
    COLUMN_SCORE = "score"
    COLUMN_MEAN = "mean"
    COLUMN_MEAN_NDVI = "meanNdvi"

    vector_predict_stat = os.path.dirname(vector_output) + os.sep + os.path.splitext(os.path.basename(vector_output))[0] + SUFFIX_SAT + extension_vector

    # Calcul statistique des boites englobantes pour récupérer la moyenne avec le NDVI
    col_to_delete_list = []
    col_to_delete_list = ["min", "max", "median", "sum", "std", "unique", "range"]
    statisticsVectorRaster(image_ndvi_input, vector_predict_input, vector_predict_stat, 1, False, False, True, col_to_delete_list, [], {}, True, no_data_value, format_vector, path_time_log, save_results_intermediate, overwrite)
    renameFieldsVector(vector_predict_stat, [COLUMN_MEAN], [COLUMN_MEAN_NDVI], format_vector)

    # Filtrage des valeurs moyen de ndvi inferieur à threshold_ndvi_value
    column = "'%s, %s, %s, %s, %s, %s, %s'"% (COLUMN_XMIN, COLUMN_YMIN, COLUMN_XMAX, COLUMN_YMAX, COLUMN_LABEL, COLUMN_SCORE, COLUMN_MEAN_NDVI)
    expression = "%s > %s" % (COLUMN_MEAN_NDVI, threshold_ndvi_value)
    filterSelectDataVector (vector_predict_stat, vector_output, column, expression, overwrite, format_vector)

    # Suppression des données intermédiaires
    if not save_results_intermediate:
        removeVectorFile(vector_predict_stat)

    return

###########################################################################################################################################
# FONCTION trainModelForest()                                                                                                             #
###########################################################################################################################################
def trainModelForest(training_input, vector_training_input, repertory_output, model_input, model_output, number_epoch, use_graphic_card, id_graphic_card, size_grid, debord, epsg=2154, extension_raster=".tif", extension_vector=".shp", format_raster='GTiff', format_vector='ESRI Shapefile',  overwrite=True):
    """
    # ROLE:
    #    Fonction de chargement creation renforcement et sauvegarde du modele
    #
    # ENTREES DE LA FONCTION :

    #    training_input (string) : l'image satellite d'apprentissage
    #    vector_training_input (string) : le fichier vecteur contenant les polygones d'apprentissage
    #    repertory_output (string) : chemin de sortie contenant les données temporaires
    #    model_input (string) : nom du réseau de neurones à utiliser pour classifier
    #    model_output (string) : chemin où stocker le modèle (réseau de neurones) une fois entraîné
    #    number_epoch (int) : nombre d'époche pour le reseau
    #    use_graphic_card (bool) : booléen pour utiliser la carte GPU pour les calcul
    #    id_graphic_card (int) : le numero de devices du gpu
    #    size_grid (int) : dimension d'une cellule de la grille de découpe de l'image satellite initiale
    #    debord (int) : utilisé pour éviter les effets de bord. Agrandit artificiellement les imagettes
    #    epsg (int) : Identificateur de projection
    #    extension_raster (string) : extension de fichier des imagettes
    #    extension_vector (string) : extension de fichier des vecteurs
    #    format_raster (string) : format des imagettes
    #    format_vector (string) : format des vecteurs
    #    overwrite (bool) : booléen pour écrire ou non par dessus un fichier existant
    #
    # SORTIES DE LA FONCTION :
    #    le modele
    #
    """

    if debug >= 3:
        print(cyan + "trainModelForest() : " + endC + "training_input : " + str(training_input) + endC)
        print(cyan + "trainModelForest() : " + endC + "vector_training_input : " + str(vector_training_input) + endC)
        print(cyan + "trainModelForest() : " + endC + "repertory_output : " + str(repertory_output) + endC)
        print(cyan + "trainModelForest() : " + endC + "model_input : " + str(model_input) + endC)
        print(cyan + "trainModelForest() : " + endC + "model_output : " + str(model_output) + endC)
        print(cyan + "trainModelForest() : " + endC + "number_epoch : " + str(number_epoch) + endC)
        print(cyan + "trainModelForest() : " + endC + "use_graphic_card : " + str(use_graphic_card) + endC)
        print(cyan + "trainModelForest() : " + endC + "id_graphic_card : " + str(id_graphic_card) + endC)
        print(cyan + "trainModelForest() : " + endC + "size_grid : " + str(size_grid) + endC)
        print(cyan + "trainModelForest() : " + endC + "debord : " + str(debord) + endC)
        print(cyan + "trainModelForest() : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "trainModelForest() : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "trainModelForest() : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "trainModelForest() : " + endC + "format_raster : " + str(format_raster) + endC)
        print(cyan + "trainModelForest() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "trainModelForest() : " + endC + "overwrite : " + str(overwrite) + endC)

    # Constantes
    LABEL_TREE = "Tree"
    EXT_CSV = '.csv'
    SUFFIX_CONFIG = "_config"

    if debug >= 2:
        print(cyan + "trainModelForest() : " + endC + "Traning started" )

    # Utilisation du GPU
    if use_graphic_card :
        compute_hardware = 'gpu'
    else :
        compute_hardware = 'cpu'

    # Chargement du modèle
    model = deepforest.main.deepforest()
    if model_input != "" and os.path.isfile(model_input) :
        model.model.load_state_dict(torch.load(model_input, map_location=compute_hardware))
    else :
        #model.use_release()
        model.use_release(check_release=False)

    # Augmentation du modele
    if training_input != "" and os.path.isfile(training_input) and vector_training_input != "" and os.path.isfile(vector_training_input) :

        # Preparation de la données d'apprentissage
        image_name = os.path.splitext(os.path.basename(training_input))[0]
        folder_imagette = "Imagette_" + image_name
        folder_train = "Train_" + image_name
        folder_grid = "Grid_" + image_name
        output_image_path_list, output_train_vector_path_list = decoupeImageTraining(training_input, vector_training_input, repertory_output, size_grid, debord, epsg, folder_imagette, folder_train, folder_grid, extension_raster, extension_vector, format_raster, format_vector,  overwrite)

        # Ceation du fichier d'apprentissage csv
        train_file_csv = repertory_output  + os.sep + os.path.splitext(os.path.basename(vector_training_input))[0] + SUFFIX_CONFIG + EXT_CSV
        createTrainConfigCsv(output_image_path_list, output_train_vector_path_list, train_file_csv, size_grid, LABEL_TREE, format_vector)
        ground_truth = get_data(train_file_csv)
        if debug >= 2:
            print(cyan + "trainModelForest() : " + endC + "ground_truth : " + str(ground_truth) + endC)

        # Entrainement du modele
        model.config["workers"] = getNumberCPU()
        model.config["train"]["epochs"] = number_epoch
        model.config["save-snapshot"] = False
        model.config["train"]["csv_file"] = ground_truth
        model.config["train"]["root_dir"] = os.path.dirname(ground_truth)
        model.config["distributed_backend"] = compute_hardware
        if use_graphic_card :
            model.config["gpus"] = id_graphic_card

        model.create_trainer()
        model.config["train"]["fast_dev_run"] = True

        model.trainer.fit(model)

    # Sauvegarde du modèle
    if model_output != "" :
        torch.save(model.model.state_dict(), model_output)

    if debug >= 2:
        print(cyan + "trainModelForest() : " + endC + "Traning End..." )

    return model

###########################################################################################################################################
# FONCTION detectForest()                                                                                                                 #
###########################################################################################################################################
def detectForest(image_input, image_ndvi_input, vector_input, vector_output, training_input, vector_training_input, model_input, model_output, use_graphic_card, id_graphic_card, size_grid, debord, number_epoch, threshold_ndvi_value, path_time_log, rand_seed=0, epsg=2154, no_data_value=0, extension_raster=".tif", extension_vector=".shp", format_raster='GTiff', format_vector='ESRI Shapefile', save_results_intermediate=False,  overwrite=True ):
    """
    # ROLE:
    #    Fonction d'appel au reseau deepforest pour la detection d'arbre en sortie un fichier vecteur de detection
    #
    # ENTREES DE LA FONCTION :
    #    image_input (string) : l'image satellite d'entrée à detecter
    #    image_ndvi_input (string) : le NDVI de l'image satellite d'entrée à detecter
    #    vector_input (string) : vecteur de découpe d'entrée
    #    vector_output (string) : le vecteur final contenant les boites englobantes des arbres
    #    training_input (string) : l'image satellite d'apprentissage
    #    vector_training_input (string) : le fichier vecteur contenant les polygones d'apprentissage
    #    model_input (string) : nom du réseau de neurones à utiliser pour classifier
    #    model_output (string) : chemin où stocker le modèle (réseau de neurones) une fois entraîné
    #    use_graphic_card (bool) : booléen pour utiliser la carte GPU pour les calcul
    #    id_graphic_card (int) : le numero de devices du gpu
    #    size_grid (int) : dimension d'une cellule de la grille de découpe de l'image satellite initiale
    #    debord (float) : utilisé pour éviter les effets de bord. Agrandit artificiellement les imagettes
    #    number_epoch (int) : nombre d'époche pour le reseau
    #    threshold_ndvi_value (float) : valeur de seuillage du NDVI moyen des boites englobantes
    #    path_time_log (string) : le fichier de log de sortie
    #    rand_seed (int): graine pour la partie randon sample
    #    epsg (int) : Identificateur de projection
    #    no_data_value (int) : valeur que prend un pixel qui ne contient pas d'information
    #    extension_raster (string) : extension de fichier des imagettes
    #    extension_vector (string) : extension de fichier des vecteurs
    #    format_raster (string) : format des imagettes
    #    format_vector (string) : format des vecteurs
    #    save_results_intermediate (bool) : booléen qui determine si on sauvegarde ou non les fichiers temporaires
    #    overwrite (bool) : booléen pour écrire ou non par dessus un fichier existant
    #
    # SORTIES DE LA FONCTION :
    #    Aucune sortie
    #
    """

    # Mise à jour du Log
    starting_event = "detectForest() : Detecte tree in image starting : "
    timeLine(path_time_log, starting_event)

    print(endC)
    print(bold + green + "## START : DEEP FOREST" + endC)
    print(endC)

    if debug >= 3:
        print(cyan + "detectForest() : " + endC + "image_input : " + str(image_input) + endC)
        print(cyan + "detectForest() : " + endC + "image_ndvi_input : " + str(image_ndvi_input) + endC)
        print(cyan + "detectForest() : " + endC + "vector_input : " + str(vector_input) + endC)
        print(cyan + "detectForest() : " + endC + "vector_output : " + str(vector_output) + endC)
        print(cyan + "detectForest() : " + endC + "training_input : " + str(training_input) + endC)
        print(cyan + "detectForest() : " + endC + "vector_training_input : " + str(vector_training_input) + endC)
        print(cyan + "detectForest() : " + endC + "model_input : " + str(model_input) + endC)
        print(cyan + "detectForest() : " + endC + "model_output : " + str(model_output) + endC)
        print(cyan + "detectForest() : " + endC + "use_graphic_card : " + str(use_graphic_card) + endC)
        print(cyan + "detectForest() : " + endC + "id_graphic_card : " + str(id_graphic_card) + endC)
        print(cyan + "detectForest() : " + endC + "size_grid : " + str(size_grid) + endC)
        print(cyan + "detectForest() : " + endC + "debord : " + str(debord) + endC)
        print(cyan + "detectForest() : " + endC + "number_epoch : " + str(number_epoch) + endC)
        print(cyan + "detectForest() : " + endC + "threshold_ndvi_value : " + str(threshold_ndvi_value) + endC)
        print(cyan + "detectForest() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "detectForest() : " + endC + "rand_seed : " + str(rand_seed) + endC)
        print(cyan + "detectForest() : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "detectForest() : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "detectForest() : " + endC + "format_raster : " + str(format_raster))
        print(cyan + "detectForest() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "detectForest() : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "detectForest() : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "detectForest() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "detectForest() : " + endC + "overwrite : " + str(overwrite) + endC)

    # Constantes
    SUFFIX_CUT = "_cut"
    SUFFIX_REP = "_rep"
    SUFFIX_TEMP = "_temp"

    # Si le résultat de la détection existe deja et que overwrite n'est pas activé
    check = os.path.isfile(vector_output)
    if check and not overwrite:
        print(cyan + "detectForest() : " + bold + yellow + "Detection tree in the image %s already computed and will not be create again."  %(image_input) + endC)
    else: # Si non ou si la vérification est désactivée : création de la classification

        # Suppression de l'éventuel fichier existant
        if check:
            try:
                removeVectorFile(vector_output, format_vector)
            except Exception:
                pass # Si le fichier ne peut pas être supprimé, on suppose qu'il n'existe pas et on passe à la suite

        # Si une zone d'étude est demander découper l'image d'entrée
        if vector_input != "" and os.path.isfile(vector_input) :
            image_study = os.path.dirname(vector_output) + os.sep + os.path.splitext(os.path.basename(image_input))[0] + SUFFIX_CUT + extension_raster
            cutImageByVector(vector_input ,image_input, image_study, None, None, False, no_data_value, epsg, format_raster, format_vector)
        else :
            image_study = image_input


        # Dossier de travail contenant les fichiers temporaires
        repertory_output = os.path.dirname(vector_output)
        base_name = os.path.splitext(os.path.basename(vector_output))[0]
        if not os.path.isdir(repertory_output):
            os.makedirs(repertory_output)
        repertory_output_temp = repertory_output + os.sep + base_name + SUFFIX_TEMP + SUFFIX_TEMP
        if not os.path.isdir(repertory_output_temp):
            os.makedirs(repertory_output_temp)

        ######################################
        # Detection des arbres avec le model #
        ######################################

        '''
        # Ouverture de l'image raster avec PIL
        raster = Image.open(image_study, mode='r')
        numpy_image = np.array(raster)
        '''

        # Ouverture de l'image raster avec GDAL
        #dtype='float32'
        #dtype='uint16'
        dataset = gdal.Open(image_study, GA_ReadOnly) # Ouverture de l'image en lecture
        bands = [dataset.GetRasterBand(i) for i in range(1, dataset.RasterCount + 1)]
        #numpy_image = np.array([gdn.BandReadAsArray(band) for band in bands]).astype(dtype)
        numpy_image = np.array([gdn.BandReadAsArray(band) for band in bands])
        numpy_image = numpy_image.transpose(1, 2, 0)

        # Récupération de la taille de l'image, possède 4 canaux
        if debug >= 2:
            taille_numpy_image = numpy_image.shape
            print(cyan + "detectForest() : " + endC + "taille de l'image : " + str(taille_numpy_image))

        numpy_image = numpy_image[:,:,:3]           # On retire le 4 ème canal --> PIR
        #plt.imshow(numpy_image)
        #plt.show()
        numpy_image = numpy_image[...,::-1]         # On inverse l'ordre des canaux, donc on doit nous même le faire RGB --> BGR
        numpy_image = numpy_image.astype('float32') # Passage en type floatant de l'image

        # Récupération des coordonnées de l'image de taille des pixels
        with rasterio.open(image_study) as dataset:
            bounds = dataset.bounds
            pixelSizeX, pixelSizeY  = dataset.res

        if debug >= 2:
            print(cyan + "detectForest() : " + endC + "pixelSizeX = " + str(pixelSizeX))
            print(cyan + "detectForest() : " + endC + "pixelSizeY = " + str(pixelSizeY))
            print(cyan + "detectForest() : " + endC + "bounds = " + str(bounds))

        # Chargement ou creation du modèle
        model = trainModelForest(training_input, vector_training_input, repertory_output_temp, model_input, model_output, number_epoch, use_graphic_card, id_graphic_card, size_grid, debord, epsg, extension_raster, extension_vector, format_raster, format_vector,  overwrite)

        # Utilisation du GPU
        if use_graphic_card :
            model.to("cuda")
        if debug >= 2:
            print(cyan + "detectForest() : " + endC + "Current device is {}".format(model.device))

        # Initialiser le data frame vide
        df_boxes = pandas.DataFrame()

        # Redimensionne la donnée dans un format soutenable pour l'entrainement ou la prédiction
        overlap = debord / (size_grid / 2)
        if debug >= 2:
            print(cyan + "detectForest() : " + endC + "overlap = " + str(overlap))
        windows = preprocess.compute_windows(numpy_image, patch_size = size_grid, patch_overlap = overlap) # Création d'une fenêtre coulissante

        #for index, window in enumerate(tqdm(windows)):
        for index, window in enumerate(windows):
            xmin, ymin, w, h = windows[index].getRect()

            if debug >= 4:
                print(cyan + "detectForest() : " + endC + "Traiement imagette index = " + str(index))
                print(cyan + "detectForest() : " + endC + " xmin = " + str(xmin))
                print(cyan + "detectForest() : " + endC + " ymin = " + str(ymin))
                print(cyan + "detectForest() : " + endC + " w = " + str(w))
                print(cyan + "detectForest() : " + endC + " h = " + str(h))
                print("")

            # Selectionner une imagette par l'index et calculer la prediction
            crop = numpy_image[windows[index].indices()]
            '''
            plt.imshow(bgr2rgb(crop))
            plt.show()

            boxes = model.predict_image(image=crop,return_plot=True)
            plt.imshow(bgr2rgb(boxes[...,::-1] ))
            plt.show()
            #exit()
            '''
            boxes = model.predict_image(image=crop)

            if debug >= 4:
                print(cyan + "detectForest() : " + endC + " boxes = " + str(boxes))

            # Calculer les cordonnees de la prediction
            if boxes is not None :
                # Subtract origin. Recall that numpy origin is top left! Not bottom left.
                boxes["xmin"] = ((boxes["xmin"] + xmin) * pixelSizeX) + bounds.left
                boxes["xmax"] = ((boxes["xmax"] + xmin) * pixelSizeX) + bounds.left
                boxes["ymin"] = bounds.top - ((boxes["ymin"] + ymin) * pixelSizeY)
                boxes["ymax"] = bounds.top - ((boxes["ymax"] + ymin) * pixelSizeY)

                # Combine column to a shapely Box() object, save shapefile
                boxes['geometry'] = boxes.apply(lambda x: shapely.geometry.box(x.xmin,x.ymin,x.xmax,x.ymax), axis=1)

                # Concatene les dataframes
                df_boxes = pandas.concat([df_boxes, boxes], ignore_index=True)

        vector_predict_input = ""
        if not df_boxes.empty:
            ##########################################
            # Sauvegarde de la prediction en vecteur #
            ##########################################
            epsg, srs = getProjectionImage(image_study)
            #boxes_geometry = geopandas.GeoDataFrame(df_boxes, geometry='geometry', crs = {'init' :'epsg:%s'%(epsg)})
            boxes_geometry = geopandas.GeoDataFrame(df_boxes, geometry='geometry')
            saveVectorFromDataframe(vector_output, boxes_geometry, epsg, srs, overwrite, format_vector)

            ##########################################
            # Filtrage de la prediction par le NDVI  #
            ##########################################
            if image_ndvi_input != "" and os.path.isfile(image_ndvi_input) :
                vector_predict_input = os.path.dirname(vector_output) + os.sep + os.path.splitext(os.path.basename(vector_output))[0] + SUFFIX_TEMP + extension_vector
                renameVectorFile(vector_output, vector_predict_input)
                cleanFilteredPredictionVector(image_ndvi_input, vector_predict_input, vector_output, threshold_ndvi_value, path_time_log, no_data_value, extension_vector, format_vector, save_results_intermediate, overwrite)
        else :
            print(cyan + "detectForest() : " + bold + red  + "Pas de resultat de boites englobantes!!! File %s non crée !" %(vector_output) + endC)
    ##########################################
    # Suppression des données intermédiaires #
    ##########################################
    if not save_results_intermediate:
        if vector_input != "" and os.path.isfile(vector_input) :
            removeFile(image_study)
        if os.path.isdir(repertory_output_temp) :
            deleteDir(repertory_output_temp)
        if os.path.isfile(vector_predict_input) :
            removeVectorFile(vector_predict_input)

    print(endC)
    print(bold + green + "## END : DEEP FOREST" + endC)
    print(endC)

    # Mise à jour du Log
    ending_event = "detectForest() : Detecte tree in image ending : "
    timeLine(path_time_log,ending_event)

    return

###########################################################################################################################################
# MISE EN PLACE DU PARSER                                                                                                                 #
###########################################################################################################################################

# Code executé seulement dans le cas ou le script est lancé depuis une ligne de commande
# Il n'est pas executé lors d'un import DeepForestDetection.py

# Exemple de lancement en ligne de commande pour entrainer un réseau de neurones:
# python3 -m DeepForestDetection -i /mnt/Data/10_Agents_travaux_en_cours/Gilles/TESTS/Test_Deepforest/Extrait_image_8bit.tif -vo /mnt/RAM_disk/Englobe_box.shp

def main(gui=False):
    # Définition des arguments possibles pour l'appel en ligne de commande
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, prog="DeepForestDetection", description="\
    Info : Detection d'arbre  a l'aide de reseau de neurones. \n\
    Objectif : Execute une recher de groupe de pixels correspondant à des arbres dans une images. \n\
    Exemple utilisation pour entrainer un reseau en gpu : python3 DeepForestDetection.py  \n\
                                                           -i /mnt/RAM_disk/PleiadesToulouseMetropoleZ4_8bit.tif \n\
                                                           -vo /mnt/RAM_disk/Toulouse/Englobe_box_tls.shp \n\
                                                           -sg 1024 -deb 77 \n\
                                                           -ti /mnt/RAM_disk/PleiadesToulouseMetropoleZ4_8bit.tif \n\
                                                           -vti /mnt/RAM_disk/Toulouse/vector_train_tlse.shp \n\
                                                           -ugc -igpu 0 \n\
    Exemple utilisation pour labeliser avec un reseau en gpu : python3 DeepForestDetection.py \n\
                                                           -i /mnt/RAM_disk/PleiadesToulouseMetropoleZ4_8bit.tif \n\
                                                           -vo /mnt/RAM_disk/Toulouse/Englobe_box_tls.shp \n\
                                                           -sg 1024 -deb 77 \n\
                                                           -ugc -igpu 0 \n\
    Exemple utilisation pour labeliser avec un reseau en cpu avec un model a charger : python3 DeepForestDetection.py \n\
                                                           -i /mnt/RAM_disk/PleiadesToulouseMetropoleZ4_8bit.tif \n\
                                                           -vo /mnt/RAM_disk/Toulouse/Englobe_box_tls.shp \n\
                                                           -sg 1024 -deb 77 \n\
                                                           --mo /mnt/RAM_disk/Toulouse/modelTrained.pth \n")

    # Paramètres


    # Directory path
    parser.add_argument('-i','--image_input',default="",help="Image input to classify", type=str, required=True)
    parser.add_argument('-indvi','--image_ndvi_input',default="",help="Image threshold ndvi input", type=str, required=False)
    parser.add_argument('-ti','--training_input',default="",help="Training input (groundtruth)", type=str, required=False)
    parser.add_argument('-v','--vector_input',default="",help="Emprise vector of study zone", type=str, required=False)
    parser.add_argument('-vti','--vector_training_input',default="",help="Vector input training polygone", type=str, required=False)
    parser.add_argument('-vo','--vector_output',default="",help="Vector output classified", type=str, required=True)
    parser.add_argument('-mi','--model_input',default="",help="Neural Network already trained, extension .pth", type=str, required=False)
    parser.add_argument('-mo','--model_output',default="",help="Neural Network to train, extension .pth ", type=str, required=False)

    # Input parameters
    parser.add_argument('-sg','--size_grid',default=400,help="Size of study grid in pixels. Not used, if vector_grid_input is inquired", type=int, required=False)
    parser.add_argument('-deb','--debord',default=0,help="Reduce size of grid cells in pixels. Useful to avoid side effect",type=int, required=False)
    parser.add_argument('-ugc','--use_graphic_card',action='store_true',default=False,help="Use CPU for training phase", required=False)
    parser.add_argument('-igpu','--id_graphic_card',default=0,help="Id of graphic card used to classify", type=int, required=False)
    parser.add_argument('-thrval','--threshold_ndvi_value',default=0.30,help="Parameter value of threshold  NDVI file. By default : 0.30", type=float, required=False)

    # Hyperparameters Reseau
    parser.add_argument('-nn.ne','--number_epoch',default=10,help="Number of epoch to train the Neural Network", type=int, required=False)

    # Base
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


    # RECUPERATION DES ARGUMENTS

    # Récupération du chemin contenant l'image d'entrée
    if args.image_input != None:
        image_input = args.image_input
        if image_input != "" and not os.path.isfile(image_input):
            raise NameError (cyan + "DeepForestDetection : " + bold + red  + "File %s not exist!" %(image_input) + endC)

    # Récupération du chemin contenant l'image NDVI
    if args.image_ndvi_input != None:
        image_ndvi_input = args.image_ndvi_input
        if image_ndvi_input != "" and not os.path.isfile(image_ndvi_input):
            raise NameError (cyan + "DeepForestDetection : " + bold + red  + "File %s not exist!" %(image_ndvi_input) + endC)

    # Récupération du vecteur d'emprise sous forme de polygone
    if args.vector_input != None:
        vector_input = args.vector_input
        if vector_input != "" and not os.path.isfile(vector_input):
            raise NameError (cyan + "DeepForestDetection : " + bold + red  + "File %s not exist!" %(vector_input) + endC)

   # Récupération du chemin contenant l'image d'apprentissage
    if args.training_input != None :
        training_input = args.training_input
        if training_input != "" and not os.path.isfile(training_input):
            raise NameError (cyan + "DeepForestDetection : " + bold + red  + "File %s not exist!" %(training_input) + endC)
    elif vector_input != "" :
        training_input = image_input

    # Récupération du vecteur d'apprentissage contenant les polygones
    if args.vector_training_input != None:
        vector_training_input = args.vector_training_input
        if vector_training_input != "" and not os.path.isfile(vector_training_input):
            raise NameError (cyan + "DeepForestDetection : " + bold + red  + "File %s not exist!" %(vector_training_input) + endC)

    # Stockage du vecteur emprise de detection des arbres
    if args.vector_output != None:
        vector_output = args.vector_output
        # Test si le repertoire de sortie existe
        repertory_output = os.path.dirname(vector_output)
        if not os.path.isdir(repertory_output):
            os.makedirs(repertory_output)

    # Récupération du modèle déjà entrainé
    if args.model_input != None:
        model_input = args.model_input
        if model_input != "" and not os.path.isfile(model_input):
            raise NameError (cyan + "DeepForestDetection : " + bold + red  + "File %s not exist!" %(model_input) + endC)

    # Récupération du modèle à entrainer
    if args.model_output != None:
        model_output = args.model_output

    # Récupération de la taille des images à découper
    if args.size_grid != None :
        size_grid = args.size_grid

    # Récupération du nombre d'échantillons qui passe dans le réseau avant une mise à jour des poids
    if args.debord != None :
        debord = args.debord
        if debord < 0 :
            raise NameError (cyan + "DeepForestDetection : " + bold + red  + "Debord 0 and negative numbers not allowed!" + endC)
        if debord >= (size_grid /2) :
            raise NameError (cyan + "DeepForestDetection : " + bold + red  + "Debord >= (size_grid /2) is not allowed!" + endC)

    # Récupération d'un int utilisé comme un booléen pour savoir si on utilise ou non la CPU pour effectuer les calculs
    use_graphic_card = args.use_graphic_card
    if type(use_graphic_card) != bool:
        raise NameError (cyan + "DeepForestDetection : " + bold + red  + "use_cpu takes False or True in input!" + endC)

    # Récupération de l'identifiant de la carte graphique à utiliser
    if args.id_graphic_card != None :
        id_graphic_card = args.id_graphic_card
        if (id_graphic_card < 0):
            raise NameError (cyan + "DeepForestDetection : " + bold + red  + "%i not a correct number!" %(id_graphic_card) + endC)

    # Paramettre valeur de seuillage du NDVI
    if args.threshold_ndvi_value != None:
        threshold_ndvi_value = args.threshold_ndvi_value

    # A PARAMETTRE DU RESEAU

    # Récupération du nombre d'époques pour entrainer le réseau
    if args.number_epoch != None :
        number_epoch = args.number_epoch
        if number_epoch <=0 :
            raise NameError (cyan + "DeepForestDetection : " + bold + red  + "0 and negative numbers not allowed!" + endC)

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
        print(cyan + "DeepForestDetection : " + endC + "image_input : " + image_input + endC)
        print(cyan + "DeepForestDetection : " + endC + "image_ndvi_input : " + image_ndvi_input + endC)
        print(cyan + "DeepForestDetection : " + endC + "training_input : " + training_input + endC)
        print(cyan + "DeepForestDetection : " + endC + "vector_input : " + vector_input + endC)
        print(cyan + "DeepForestDetection : " + endC + "vector_training_input : " + vector_training_input + endC)
        print(cyan + "DeepForestDetection : " + endC + "vector_output : " + vector_output + endC)
        print(cyan + "DeepForestDetection : " + endC + "model_input : " + model_input + endC)
        print(cyan + "DeepForestDetection : " + endC + "model_output : " + model_output + endC)

        # Info
        print(cyan + "DeepForestDetection : " + endC + "size_grid : " + str(size_grid) + endC)
        print(cyan + "DeepForestDetection : " + endC + "debord : " + str(debord) + endC)
        print(cyan + "DeepForestDetection : " + endC + "use_graphic_card : " + str(use_graphic_card) + endC)
        print(cyan + "DeepForestDetection : " + endC + "id_graphic_card : " + str(id_graphic_card) + endC)

        print(cyan + "DeepForestDetection : " + endC + "threshold_ndvi_value : " + str(threshold_ndvi_value) + endC)

        # Parametres reseau
        print(cyan + "DeepForestDetection : " + endC + "number_epoch : " + str(number_epoch) + endC)

        # A CONSERVER
        print(cyan + "DeepForestDetection : " + endC + "rand_seed : " + str(rand_seed) + endC)
        print(cyan + "DeepForestDetection : " + endC + "ram_otb : " + str(ram_otb) + endC)
        print(cyan + "DeepForestDetection : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "DeepForestDetection : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "DeepForestDetection : " + endC + "format_raster : " + format_raster + endC)
        print(cyan + "DeepForestDetection : " + endC + "format_vector : " + format_vector + endC)
        print(cyan + "DeepForestDetection : " + endC + "extension_raster : " + extension_raster + endC)
        print(cyan + "DeepForestDetection : " + endC + "extension_vector : " + extension_vector + endC)
        print(cyan + "DeepForestDetection : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "DeepForestDetection : " + endC + "save_results_inter : " + str(save_results_intermediate) + endC)
        print(cyan + "DeepForestDetection : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "DeepForestDetection : " + endC + "debug : " + str(debug) + endC)

        # Appel de la fonction principale
        detectForest(image_input, image_ndvi_input, vector_input, vector_output, training_input, vector_training_input, model_input, model_output, use_graphic_card, id_graphic_card, size_grid, debord, number_epoch, threshold_ndvi_value, path_time_log, rand_seed, epsg, no_data_value, extension_raster, extension_vector, format_raster, format_vector, save_results_intermediate, overwrite)

# ================================================

if __name__ == '__main__':
  main(gui=False)

