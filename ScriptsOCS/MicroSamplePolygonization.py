#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT QUI CONVERTIT DES VECTEURS EN RASTER, FILTRE LES PETITS POLYGONES, ERODE ET SIMPLIFIE LA GEOMETRIE                                 #
# Peut être utilise dans la chaine pour créer les échantillons d'aprentissage a partir de la sortie de kmeans                               #
#                                                                                                                                           #
#############################################################################################################################################
"""
Nom de l'objet : MicroSamplePolygonization.py
Description :
-------------
Objectif : Convertir les poygones raster en vecteur nettoyer les petit polygones et fusion en un seul fichier vecteur
Rq : utilisation de la base de donnée spatialite : érosion et fusion
Rq : utilisation des OTB Applications :  otbcli_band_math, otbcli_mean_shift_smoothing, otbcli_lsms_segmentation, otbcli_lsms_small_regions_merging, otbcli_lsms_vectorization
Rq : utilisation des GDAL et OGR Applications : gdal_polygonize, ogr2ogr

Date de creation : 31/07/2014
----------
Histoire :
----------
Origine : le script originel provient du fichier Chain5_MicroclassesMicroSamplePolygonization.py cree en 2013 et utilise par la chaine de traitement OCSOL V1.X
31/07/2014 : Transformation en brique elementaire (suppression des liens avec la chaine OCSOL)
-----------------------------------------------------------------------------------------------------
Modifications :
01/10/2014 : refonte du fichier harmonisation des régles de qualitées des niveaux de boucles et des paramétres dans args
21/05/2015 : simplification des parametres en argument plus de liste d'image en emtrée à traiter uniquement une image
14/02/2017 : ajout de la possibilité de faire la partie polygonisation avec GDAL (seul choix possible avant) ou avec OTB (via l'appli Vectorization, et par défaut maintenant)
23/03/2015 : ajout de la possibilité de faire une érosion morpholoqique sur les images d'entrée (avant vectorisation)
------------------------------------------------------
A Reflechir/A faire :

"""

from __future__ import print_function
import os,sys,glob,string,shutil,time,argparse,threading
from osgeo import ogr
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_raster import polygonizeRaster, identifyPixelValues, bufferBinaryRaster, identifyPixelValues, mergeListRaster
from Lib_vector import cleanMiniAreaPolygons, simplifyVector, bufferVector, fusionVectors, multigeometries2geometries, addNewFieldVector, getAttributeValues,  setAttributeIndexValuesList, deleteClassVector
from Lib_file import cleanTempData, deleteDir, copyVectorFile, removeVectorFile, removeFile
from Lib_text import writeTextFile
from Lib_spatialite import sqlCreatetableQuery, sqlSimplifyBufferPolyQuery, sqlInsertTable, sqlExportShape, sqlExecuteQuery
from Lib_log import timeLine
from Vectorization import vectorizeClassification

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 3 : affichage maximum de commentaires lors de l'execution du script. Intermédiaire : affichage intermédiaire
debug = 3

###########################################################################################################################################
# FONCTION erodeImages()                                                                                                                  #
###########################################################################################################################################
def erodeImages(images_input_list, images_erode_list, raster_erode_values_list, path_time_log, save_results_intermediate=False, overwrite=True):
    """
    # ROLE:
    #     Simplifie les images raster d'entrée par erosion binaire morphologique
    #
    # ENTREES DE LA FONCTION :
    #     images_input_list : liste d'image de microclasse d'entrée .tif à éroder
    #     images_erode_list :liste d'image de microclasse érodée
    #     raster_erode_values_list : liste de parametre taille de la fenetre en pixel (positif => buffer, negatif => erosion)
    #     path_time_log : le fichier de log de sortie
    #     save_results_intermediate : fichiers de sorties intermediaires nettoyees, par defaut = False
    #     overwrite : ecrasement ou non des fichiers existants, par defaut = True
    # SORTIES DE LA FONCTION :
    #     Vecteur polygonisé
    #
    """

    # Mise à jour du Log
    starting_event = "erodeImages() : Erosion starting : "
    timeLine(path_time_log,starting_event)

    print(endC)
    print(bold + green + "## START : POLYGONIZATION" + endC)
    print(endC)

    if debug >= 3:
        print(bold + green + "Variables dans le parser" + endC)
        print(cyan + "erodeImages() : " + endC + "images_input_list : " + str(images_input_list) + endC)
        print(cyan + "erodeImages() : " + endC + "images_erode_list : " + str(images_erode_list) + endC)
        print(cyan + "erodeImages() : " + endC + "raster_erode_values_list : " + str(raster_erode_values_list) + endC)
        print(cyan + "erodeImages() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "erodeImages() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "erodeImages() : " + endC + "overwrite : " + str(overwrite) + endC)

    # VECTORISATION DES MICROCLASSES
    print(endC)
    print(cyan + "erodeImages() : " + bold + green + "MicroSamplePolygonization par classe" + endC)

    CODAGE = "uint16"
    NODATA_VALUE = 0

    thread_list = [] # Initialisation de la liste pour le multi-threading

    # Eroder toutes les fichiers macroclasse raster d'une image
    for macroclass_id in range(len(images_input_list)):
        image_input = images_input_list[macroclass_id]
        image_erode = images_erode_list[macroclass_id]
        raster_erode_value = abs(raster_erode_values_list[macroclass_id]) * (-1)

        check = os.path.isfile(image_erode)
        if check and not overwrite :          # Si les polygones existent deja et que overwrite n'est pas activé
            print(cyan + "erodeImages() : " + bold + yellow + "erodeImages() : " + endC + image_erode + " has already been eroded and will not be eroded again." + endC)
        else:
            if check :
                try:
                    removeFile(image_erode) # Tentative de suppression du fichier
                except Exception:
                    pass                      # Si le fichier ne peut pas être supprimé, on suppose qu'il n'existe pas et on passe à la suite

            # Gestion du multi threading
            if raster_erode_value != 0 :
                thread = threading.Thread(target=erodeImage, args=(image_input, image_erode, raster_erode_value, CODAGE, NODATA_VALUE, save_results_intermediate))
                thread.start()
                thread_list.append(thread)
            else :
                shutil.copy2(image_input, image_erode)

    # Erosion des images
    try:
        for thread in thread_list:
            thread.join()
    except:
        print(cyan + "erodeImages() : " + bold + red + "erodeImages() : " + endC + "Erreur lors de l'érosion : impossible de demarrer le thread" + endC, file=sys.stderr)

    # Mise à jour du Log
    ending_event = "erodeImages() : Erosion ending : "
    timeLine(path_time_log,ending_event)

    return

###########################################################################################################################################
# FONCTION erodeImage()                                                                                                                   #
###########################################################################################################################################
def erodeImage(image_input, image_erode, raster_erode_value, codage, nodata, save_results_intermediate=False):
    """
    # ROLE:
    #     Erosion binaire morphologique d'une image
    #
    # ENTREES DE LA FONCTION :
    #     image_input : image de microclasse d'entrée .tif à éroder
    #     image_erode : image de microclasse érodée
    #     raster_erode_value : parametre taille de la fenetre en pixel (positif => buffer, negatif => erosion)
    #     codage : encodage du fichier de sortie
    #     nodata : valeur du no data pour l'image de sortie
    #     save_results_intermediate : fichiers de sorties intermediaires nettoyees, par defaut = False
    # SORTIES DE LA FONCTION :
    #     Vecteur polygonisé
    #
    """

    # Recuperation des valeurs des pixels de l'image
    microclass_values_list = identifyPixelValues(image_input)

    # Suppression de la valeur zéro
    if nodata in microclass_values_list :
        microclass_values_list.remove(nodata)

    # Erosion
    images_erode_temp_list = []
    for microclass_value in microclass_values_list :
        image_erode_temp = os.path.splitext(image_erode)[0] + "_" + str(microclass_value) + os.path.splitext(image_erode)[1]
        images_erode_temp_list.append(image_erode_temp)
        bufferBinaryRaster(image_input, image_erode_temp, raster_erode_value, codage, microclass_value, nodata)
        image_input = image_erode_temp

    shutil.copy2(image_erode_temp, image_erode)

    # Nettoyage des fichiers images temporaires
    if not save_results_intermediate:
        for image_erode_temp in images_erode_temp_list:
            removeFile(image_erode_temp)

    return

###########################################################################################################################################
# FONCTION polygonize_gdal()                                                                                                              #
###########################################################################################################################################
def polygonize_gdal(images_input_list, vector_macro_output_list, path_time_log, name_column, format_vector='ESRI Shapefile', save_results_intermediate=False, overwrite=True):
    """
    # ROLE:
    #     Convertit des vecteurs en raster avec la fonction gdal_polygonize
    #
    # ENTREES DE LA FONCTION :
    #     images_input_list : list d'image de microclasse d'entrée .tif à rasteriser
    #     vector_macro_output_list : liste de polygones de microclasse de sortie poylygonisés
    #     path_time_log : le fichier de log de sortie
    #     name_column : Nom de la colonne du fichier shape contenant l'inforaltion de classification
    #     format_vector  : format du vecteur de sortie, par defaut = 'ESRI Shapefile'
    #     save_results_intermediate : fichiers de sorties intermediaires nettoyees, par defaut = False
    #     overwrite : ecrasement ou non des fichiers existants, par defaut = True
    # SORTIES DE LA FONCTION :
    #     Vecteur polygonisé
    #
    """

    # Mise à jour du Log
    starting_event = "polygonize_gdal() : Polygonization starting : "
    timeLine(path_time_log,starting_event)

    print(endC)
    print(bold + green + "## START : POLYGONIZATION" + endC)
    print(endC)

    if debug >= 3:
        print(bold + green + "Variables dans le parser" + endC)
        print(cyan + "polygonize_gdal() : " + endC + "images_input_list : " + str(images_input_list) + endC)
        print(cyan + "polygonize_gdal() : " + endC + "vector_macro_output_list : " + str(vector_macro_output_list) + endC)
        print(cyan + "polygonize_gdal() : " + endC + "name_column : " + str(name_column) + endC)
        print(cyan + "polygonize_gdal() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "polygonize_gdal() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "polygonize_gdal() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "polygonize_gdal() : " + endC + "overwrite : " + str(overwrite) + endC)

    LAYER_NAME = "Layer_polygon"

    # VECTORISATION DES MICROCLASSES
    print(endC)
    print(cyan + "polygonize_gdal() : " + bold + green + "MicroSamplePolygonization par classe" + endC)

    thread_list = [] # Initialisation de la liste pour le multi-threading

    # Polygonisation pour toutes les fichiers macroclasse raster d'une image
    for macroclass_id in range(len(images_input_list)):
        image_input = images_input_list[macroclass_id]
        polygon_output = vector_macro_output_list[macroclass_id]

        check = os.path.isfile(polygon_output)
        if check and not overwrite :          # Si les polygones existent deja et que overwrite n'est pas activé
            print(bold + yellow + "polygonize_gdal() : " + endC + polygon_output + " has already been polygonized and will not be polygonized again." + endC)
        else:
            if check :
                try:
                    removeFile(polygon_output) # Tentative de suppression du fichier
                except Exception:
                    pass                      # Si le fichier ne peut pas être supprimé, on suppose qu'il n'existe pas et on passe à la suite

            # Gestion du multi threading
            thread = threading.Thread(target=polygonizeRaster, args=(image_input, polygon_output, LAYER_NAME, name_column, format_vector))
            thread.start()
            thread_list.append(thread)

    try:
        for thread in thread_list:
            thread.join()
    except:
        print(cyan  + "polygonize_gdal() : " + bold + red + "Erreur lors de la polygonization : impossible de demarrer le thread" + endC, file=sys.stderr)

    # Mise à jour du Log
    ending_event = "polygonize_gdal() : Polygonization ending : "
    timeLine(path_time_log,ending_event)

    return

###########################################################################################################################################
# FONCTION polygonize_otb()                                                                                                               #
###########################################################################################################################################
def polygonize_otb(images_input_list, vector_macro_output_list, path_time_log, name_column, umc_value, tilesize, format_vector='ESRI Shapefile', extension_raster=".tif", extension_vector=".shp", save_results_intermediate=False, overwrite=True):
    """
    # ROLE:
    #     convertit des vecteurs en raster avec les fonctions otb : otbcli_mean_shift_smoothing, otbcli_lsms_segmentation, otbcli_lsms_small_regions_merging, otbcli_lsms_vectorization
    #
    # ENTREES DE LA FONCTION :
    #     images_input_list : list d'image de microclasse d'entrée .tif à rasteriser
    #     vector_macro_output_list : liste de polygones de microclasse de sortie poylygonisés
    #     path_time_log : le fichier de log de sortie
    #     name_column : Nom de la colonne du fichier shape contenant l'inforaltion de classification
    #     umc_value : valeur de l'UMC voulue (en m²). Mettre un multiple de la surface du pixel
    #     tilesize : taille des carreaux minimal de traitement en x et y
    #     format_vector  : format du vecteur de sortie, par defaut = 'ESRI Shapefile'
    #     extension_raster : extension des fichiers raster de sortie, par defaut = '.tif'
    #     extension_vector : extension du fichier vecteur de sortie, par defaut = '.shp'
    #     save_results_intermediate : fichiers de sorties intermediaires nettoyees, par defaut = False
    #     overwrite : ecrasement ou non des fichiers existants, par defaut = True
    # SORTIES DE LA FONCTION :
    #     Vecteur polygonisé
    """

    # Mise à jour du Log
    starting_event = "polygonize_otb() : Polygonization starting : "
    timeLine(path_time_log,starting_event)

    print(endC)
    print(bold + green + "## START : POLYGONIZATION" + endC)
    print(endC)

    if debug >= 3:
        print(bold + green + "Variables dans le parser" + endC)
        print(cyan + "polygonize_otb() : " + endC + "images_input_list : " + str(images_input_list) + endC)
        print(cyan + "polygonize_otb() : " + endC + "vector_macro_output_list : " + str(vector_macro_output_list) + endC)
        print(cyan + "polygonize_otb() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "polygonize_otb() : " + endC + "name_column : " + str(name_column) + endC)
        print(cyan + "polygonize_otb() : " + endC + "umc_value : " + str(umc_value) + endC)
        print(cyan + "polygonize_otb() : " + endC + "tilesize : " + str(tilesize) + endC)
        print(cyan + "polygonize_otb() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "polygonize_otb() : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "polygonize_otb() : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "polygonize_otb() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "polygonize_otb() : " + endC + "overwrite : " + str(overwrite) + endC)

    # VECTORISATION DES MICROCLASSES
    print(endC)
    print(cyan + "polygonize_otb() : " + bold + green + "MicroSamplePolygonization par classe" + endC)

    thread_list = [] # Initialisation de la liste pour le multi-threading

    # Polygonisation pour toutes les fichiers macroclasse raster d'une image
    for macroclass_id in range(len(images_input_list)):
        image_input = images_input_list[macroclass_id]
        vector_output = vector_macro_output_list[macroclass_id]

        check = os.path.isfile(vector_output)
        if check and not overwrite :          # Si les polygones existent deja et que overwrite n'est pas activé
            print(bold + yellow + "polygonize_otb() : " + endC + vector_output + " has already been vectorized and will not be vectorized again." + endC)
        else:
            if check :
                try:
                    removeFile(vector_output) # Tentative de suppression du fichier
                except Exception:
                    pass                      # Si le fichier ne peut pas être supprimé, on suppose qu'il n'existe pas et on passe à la suite

            # Gestion du multi threading
            thread = threading.Thread(target=vectorizeClassification, args=(image_input, vector_output, name_column, [umc_value], tilesize, False, True, True, True, True, False, None, False, True, False, [], path_time_log, "", 0, format_vector, extension_raster, extension_vector, save_results_intermediate, overwrite))

            thread.start()
            thread_list.append(thread)

    try:
        for thread in thread_list:
            thread.join()
    except:
        print(cyan + "polygonize_otb() : " + bold + red + "Erreur lors de la polygonization : impossible de demarrer le thread" + endC, file=sys.stderr)

    # Mise a jour des fichiers polygonisés
    for macroclass_id in range(len(images_input_list)):
        image_input = images_input_list[macroclass_id]
        vector_output = vector_macro_output_list[macroclass_id]
        updateVectorizedFile(image_input, vector_output, name_column, format_vector)

    # Mise à jour du Log
    ending_event = "polygonize_otb() : Polygonization ending : "
    timeLine(path_time_log,ending_event)

    return

###########################################################################################################################################
# FONCTION updateVectorizedFile()                                                                                                         #
###########################################################################################################################################
def updateVectorizedFile(image_input, vector_output, name_column, format_vector) :
    """
    # ROLE:
    #     Nettoyage du vecteur creer, mauvais poygones et creation d'une colonne class
    #
    # ENTREES DE LA FONCTION :
    #     image_input : image de microclasse d'entrée
    #     vector_output : vecteur de microclasse de sortie poylygonisés
    #     name_column : Nom de la colonne du fichier shape contenant l'infomaltion de classification
    #     format_vector  : format du vecteur de sortie, par defaut = 'ESRI Shapefile'
    # SORTIES DE LA FONCTION :
    #     Vecteur nettoyé
    """

    # Constante des noms de colonnes sortie de la vectorisation otb
    COLUMN_INDEX = "label"
    COLUMN_VALUE_ORIGIN = "meanB0"

    # Mise a jour du fichier polygonisé
    if debug >= 3:
        print(cyan + "updateVectorizedFile() : " + endC + "vector_output : " + str(vector_output) + endC)

    # Récuperer les valeurs possibles de la classif
    values_classif_list = identifyPixelValues(image_input)
    if debug >= 3:
        print(cyan + "updateVectorizedFile() : " + endC + "values_classif_list : " + str(values_classif_list) + endC)

    # Ajouter le champs contenant l'identifiant de classe
    addNewFieldVector(vector_output, name_column, ogr.OFTInteger, 0, None, None, format_vector)

    # Récuperer les valeur de classe issu de la vectorisation
    attribute_name_dico = {}
    attribute_name_dico[COLUMN_INDEX] = ogr.OFTInteger
    attribute_name_dico[COLUMN_VALUE_ORIGIN] = ogr.OFTReal
    values_dico = getAttributeValues(vector_output, None, None, attribute_name_dico, format_vector)

    # Identifier les manvaises valeurs correspondant aux polygones à supprimer et preparation du dico de valeurs à mettre à jour
    values_to_delete_list = [0.0]
    field_new_values_dico = {}
    for i in range(len(values_dico[COLUMN_INDEX])):
        index_polygon = values_dico[COLUMN_INDEX][i]
        value = values_dico[COLUMN_VALUE_ORIGIN][i]

        if not round(value) in values_classif_list:
            values_to_delete_list.append(value)

        field_new_values_dico[index_polygon] = {name_column:int(round(value))}

    values_to_delete_list = list(set(values_to_delete_list))
    if debug >= 3:
        print(cyan + "updateVectorizedFile() : " + endC + "values_to_delete_list : " + str(values_to_delete_list) + endC)

    # Mettre à jour la colonne d'identifiant de classe en integer et avec le bon nom
    setAttributeIndexValuesList(vector_output, COLUMN_INDEX, field_new_values_dico, format_vector)

    # Nettoyage des mauvais polygones
    deleteClassVector(values_to_delete_list, vector_output, COLUMN_VALUE_ORIGIN, format_vector)

    return

###########################################################################################################################################
# FONCTION polygonize_otb2()                                                                                                              #
###########################################################################################################################################
def polygonize_otb2(images_input_list, vector_macro_output, path_time_log, name_column, umc_value, tilesize, format_vector='ESRI Shapefile', extension_raster=".tif", extension_vector=".shp",save_results_intermediate=False, overwrite=True):
    """
    # ROLE:
    #     Convertit des vecteurs en raster avec l'otb, un seul fichier est vectoriser car les les fichiers rasteurs sont préalablement fusionnés
    #
    # ENTREES DE LA FONCTION :
    #     images_input_list : list d'image de microclasse d'entrée .tif à rasteriser
    #     vector_macro_output : fichier vecteur de polygones de microclasse de sortie poylygonisés
    #     path_time_log : le fichier de log de sortie
    #     name_column : Nom de la colonne du fichier shape contenant l'information de classification
    #     umc_value : valeur de l'UMC voulue (en m²). Mettre un multiple de la surface du pixel
    #     tilesize : taille des carreaux minimal de traitement en x et y
    #     format_vector  : format du vecteur de sortie, par defaut = 'ESRI Shapefile'
    #     save_results_intermediate : fichiers de sorties intermediaires nettoyees, par defaut = False
    #     overwrite : ecrasement ou non des fichiers existants, par defaut = True
    # SORTIES DE LA FONCTION :
    #     Vecteur polygonisé
    """

    # Mise à jour du Log
    starting_event = "polygonize_otb2() : Polygonization starting : "
    timeLine(path_time_log,starting_event)

    print(endC)
    print(bold + green + "## START : POLYGONIZATION" + endC)
    print(endC)

    if debug >= 3:
        print(bold + green + "Variables dans le parser" + endC)
        print(cyan + "polygonize_otb2() : " + endC + "images_input_list : " + str(images_input_list) + endC)
        print(cyan + "polygonize_otb2() : " + endC + "vector_macro_output : " + str(vector_macro_output) + endC)
        print(cyan + "polygonize_otb2() : " + endC + "name_column : " + str(name_column) + endC)
        print(cyan + "polygonize_otb2() : " + endC + "umc_value : " + str(umc_value) + endC)
        print(cyan + "polygonize_otb2() : " + endC + "tilesize : " + str(tilesize) + endC)
        print(cyan + "polygonize_otb2() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "polygonize_otb2() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "polygonize_otb2() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "polygonize_otb2() : " + endC + "overwrite : " + str(overwrite) + endC)

    CODAGE = "uint16"

    # Fichier temporaire
    repertory_output = os.path.dirname(vector_macro_output)
    image_merge_input = repertory_output + os.sep + os.path.splitext(os.path.basename(vector_macro_output))[0] + "_merged" + extension_raster

    # VECTORISATION DES MICROCLASSES
    print(endC)
    print(cyan + "polygonize_otb2() : " + bold + green + "MicroSamplePolygonization par classe" + endC)

    # Test si le fichier de sortie existe
    check = os.path.isfile(vector_macro_output)
    if check and not overwrite :          # Si le fichier existent deja et que overwrite n'est pas activé
        print(bold + yellow + "polygonize_otb2() : " + endC + vector_macro_output + " has already been vectorized and will not be vectorized again." + endC)
    else:
        if check :
            try:
                removeFile(vector_macro_output) # Tentative de suppression du fichier
            except Exception:
                pass                      # Si le fichier ne peut pas être supprimé, on suppose qu'il n'existe pas et on passe à la suite

        # Fusion des images rasters de macroclasse d'entrée
        mergeListRaster(images_input_list, image_merge_input, CODAGE)

        # Polygonisation le fichier raster des images macroclasse fusionnées
        vectorizeClassification(image_merge_input, vector_macro_output, name_column, [umc_value], tilesize, False, True, True, True, True, False, None, False, True, False, [], path_time_log, "", 0, format_vector, extension_raster, extension_vector, save_results_intermediate, overwrite)

        # Mise a jour du fichier polygonisé
        updateVectorizedFile(image_merge_input, vector_macro_output, name_column, format_vector)

        # netoyage des fichiers temporaire
        if not save_results_intermediate:
            removeFile(image_merge_input)

    # Mise à jour du Log
    ending_event = "polygonize_otb2() : Polygonization ending : "
    timeLine(path_time_log,ending_event)

    return

###########################################################################################################################################
# FONCTION cleanMergeVectors_sql()                                                                                                        #
###########################################################################################################################################
def cleanMergeVectors_sql(polygon_macro_input_list, vector_cleaned_output, path_time_log, buffer_size_list, minimal_area_list, simplification_tolerance_list, shared_geometry_field='GEOMETRY', vector_geometry_type='POLYGON', project_encoding='UTF-8', epsg=2154, format_vector='ESRI Shapefile', extension_raster=".tif", extension_vector=".shp", save_results_intermediate=True, overwrite=True):
    """
    # ROLE:
    #     Filtre les petits polygones
    #     Erode et simplifie la geometrie
    #     Nettoie les fichiers vecteurs
    #     Fusionne les polygones
    #
    # ENTREES DE LA FONCTION :
    #     polygon_macro_input_list : Liste des fichiers vecteurs contenant les polygones à filtrer
    #     vector_cleaned_output : vecteur fichier shape de sortie au bon format ESRI
    #     path_time_log : le fichier de log de sortie
    #     buffer_size_list : listes des buffer, par macroclasses
    #     minimal_area_list : liste des surfaces minimales gardées pour les polygones
    #     simplification_tolerance_list : listes des parametres de simplification des polygones, par macroclasses
    #     shared_geometry_field : champ décrivant la géométrie des polygones, par defaut = 'GEOMETRY'
    #     vector_geometry_type  : type de géométrie des couches utilisées, par defaut = 'POLYGON'
    #     project_encoding      : encodage des vecteurs de sortie, par defaut = 'UTF-8'
    #     epsg : EPSG des entrees et des sorties  par defaut = 2154
    #     format_vector  : format des vecteurs de sortie, par defaut = 'ESRI Shapefile'
    #     extension_raster : extension des fichiers raster de sortie, par defaut = '.tif'
    #     extension_vector : extension du fichier vecteur de sortie, par defaut = '.shp'
    #     save_results_intermediate : liste des sorties intermediaires nettoyees, par defaut = True
    #     overwrite : ecrasement ou non des fichiers existants, par defaut = True
    # SORTIES DE LA FONCTION :
    #     Vecteurs polygonises, erodes et simplifies places dans path_output_polygons
    #     nettoyage des dossiers selon save_results_intermediate
    #
    """

    # Mise à jour du Log
    starting_event = "cleanMergeVectors_sql() : Clean polygons starting : "
    timeLine(path_time_log,starting_event)

    # constantes
    FOLDER_CLEAN_TEMP = 'Clean_'
    SUFFIX_VECTOR_CLEAN = '_clean'

    if debug >= 3:
        print(bold + green + "Variables dans le parser" + endC)
        print(cyan + "cleanMergeVectors_sql() : " + endC + "polygon_macro_input_list : " + str(polygon_macro_input_list) + endC)
        print(cyan + "cleanMergeVectors_sql() : " + endC + "vector_cleaned_output : " + str(vector_cleaned_output) + endC)
        print(cyan + "cleanMergeVectors_sql() : " + endC + "buffer_size_list : " + str(buffer_size_list) + endC)
        print(cyan + "cleanMergeVectors_sql() : " + endC + "minimal_area_list : " + str(minimal_area_list) + endC)
        print(cyan + "cleanMergeVectors_sql() : " + endC + "simplification_tolerance_list : " + str(simplification_tolerance_list) + endC)
        print(cyan + "cleanMergeVectors_sql() : " + endC + "shared_geometry_field : " + str(shared_geometry_field) + endC)
        print(cyan + "cleanMergeVectors_sql() : " + endC + "vector_geometry_type : " + str(vector_geometry_type) + endC)
        print(cyan + "cleanMergeVectors_sql() : " + endC + "project_encoding : " + str(project_encoding) + endC)
        print(cyan + "cleanMergeVectors_sql() : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "cleanMergeVectors_sql() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "cleanMergeVectors_sql() : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "cleanMergeVectors_sql() : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "cleanMergeVectors_sql() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "cleanMergeVectors_sql() : " + endC + "overwrite : " + str(overwrite) + endC)

    # SUPRESSION DES ANCIENS FICHIERS
    #--------------------------------

    print(cyan + "cleanMergeVectors_sql() : " + bold + green + "Polygons cleaning" + endC)

    # nom de la base
    name = os.path.splitext(os.path.basename(vector_cleaned_output))[0]
    data_base_name = os.path.dirname(vector_cleaned_output) + os.sep + name + ".sqlite"

    # Mise en place des variables
    output_shape = os.path.splitext(data_base_name)[0] + "_cleaned_samples"
    vector_cleaned_training_output = output_shape + extension_vector
    output_table = os.path.splitext(os.path.basename(data_base_name))[0] + "_cleaned_samples"

    if debug >= 2:
        print(cyan + "cleanMergeVectors_sql() : " + endC + "output_shape : " + str(output_shape) + endC)
        print(cyan + "cleanMergeVectors_sql() : " + endC + "vector_cleaned_training_output : " + str(vector_cleaned_training_output) + endC)
        print(cyan + "cleanMergeVectors_sql() : " + endC + "data_base_name : " + str(data_base_name) + endC)
        print(cyan + "cleanMergeVectors_sql() : " + endC + "output_table : " + str(output_table) + endC)

    # test si le fichier vecteur de sortie existe déjà et que overwrite n'est pas activé
    check = os.path.isfile(vector_cleaned_output)
    if check and not overwrite :
        print(bold + yellow + "cleanMergeVectors_sql() : Vector file %s already done : no actualisation."%(vector_cleaned_output) + endC)
    else:
        if check:
            try:
                # Tentative de suppression du fichier vecteur résultat
                removeFile(vector_cleaned_output)
                print(bold + green + "cleanMergeVectors_sql() : Vector file %s removed."%(vector_cleaned_output) + endC)
            except Exception:
                pass  # Si le fichier ne peut pas être supprimé, on suppose qu'il n'existe pas et on passe à la suite

        # définition des répertoires temporaires
        repertory_output = os.path.dirname(vector_cleaned_output)
        repertory_clean_temp = repertory_output + os.sep + FOLDER_CLEAN_TEMP + name

        print(repertory_clean_temp)

        # Creer les répertoires temporaire si ils n'existent pas
        if not os.path.isdir(repertory_output):
            os.makedirs(repertory_output)
        if not os.path.isdir(repertory_clean_temp):
            os.makedirs(repertory_clean_temp)

        # Nettoyer les répertoires temporaire si ils ne sont pas vide
        cleanTempData(repertory_clean_temp)

        # si la base de donnée existe déjà
        check_db = os.path.isfile(data_base_name)
        if check_db:
            try:
                # Tentative de suppression de la base de donnees spatialite
                removeFile(data_base_name)
                print(bold + green + "cleanMergeVectors_sql() : Database %s removed."%(data_base_name) + endC)
                print(endC)
            except Exception:
                pass  # Si le fichier ne peut pas être supprimé, on suppose qu'il n'existe pas et on passe à la suite

        print(bold + green + "Creating database %s ..." %(data_base_name)+ endC)

        # NETTOYAGE DES PETITS VECTEURS
        #------------------------------

        # Suppression des polygones à petites surface
        print(bold + green + "START : Suppression des petits polygones" + endC)

        polygon_macro_cleaned_list = []

        # pour toutes les macroclasses d'une image
        for macroclass_id in range(len(polygon_macro_input_list)):
            polygon_input = polygon_macro_input_list[macroclass_id]
            polygon_cleaned = repertory_clean_temp + os.sep + os.path.splitext(os.path.basename(polygon_input))[0] + SUFFIX_VECTOR_CLEAN + os.path.splitext(polygon_input)[1]
            polygon_macro_cleaned_list.append(polygon_cleaned)
            minimal_area = minimal_area_list[macroclass_id]

            if debug >= 3:
                print(cyan + "cleanMergeVectors_sql() : " + endC + "polygon_input : " + str(polygon_input) + endC)
                print(cyan + "cleanMergeVectors_sql() : " + endC + "polygon_cleaned : " + str(polygon_cleaned) + endC)
                print(cyan + "cleanMergeVectors_sql() : " + endC + "minimal_area : " + str(minimal_area) + endC)
                print(cyan + "cleanMergeVectors_sql() : " + endC + "format_vector : " + str(format_vector) + endC)

            # nettoyage des petites surfaces
            cleanMiniAreaPolygons(polygon_input, polygon_cleaned, minimal_area, format_vector)

        # EROSION DES VECTEURS
        #---------------------

        # requete de creation de la table
        global_query = sqlCreatetableQuery(output_table)

        # pour toutes les macroclasses d'une image
        for macroclass_id in range(len(polygon_macro_input_list)):
            polygon_input = polygon_macro_cleaned_list[macroclass_id]
            input_shape = os.path.splitext(polygon_input)[0]
            input_table = os.path.splitext(os.path.basename(polygon_input))[0]
            buffer_size = buffer_size_list[macroclass_id]
            simplification_tolerance = simplification_tolerance_list[macroclass_id]

            if debug >= 3:
                print(cyan + "cleanMergeVectors_sql() : " + endC + "polygon_input : " + str(polygon_input) + endC)
                print(cyan + "cleanMergeVectors_sql() : " + endC + "input_shape : " + str(input_shape) + endC)
                print(cyan + "cleanMergeVectors_sql() : " + endC + "data_base_name : " + str(data_base_name) + endC)
                print(cyan + "cleanMergeVectors_sql() : " + endC + "input_table : " + str(input_table) + endC)
                print(cyan + "cleanMergeVectors_sql() : " + endC + "shared_geometry_field : " + str(shared_geometry_field) + endC)
                print(cyan + "cleanMergeVectors_sql() : " + endC + "project_encoding : " + str(project_encoding) + endC)
                print(cyan + "cleanMergeVectors_sql() : " + endC + "epsg : " + str(epsg) + endC)
                print(cyan + "cleanMergeVectors_sql() : " + endC + "vector_geometry_type : " + str(vector_geometry_type) + endC)
                print(cyan + "cleanMergeVectors_sql() : " + endC + "buffer_size : " + str(buffer_size) + endC)
                print(cyan + "cleanMergeVectors_sql() : " + endC + "simplification_tolerance : " + str(simplification_tolerance) + endC)

            # Import de input_table
            requete_cmd = sqlInsertTable(input_shape, input_table, data_base_name, epsg, shared_geometry_field, project_encoding, vector_geometry_type)
            exitCode = os.system(requete_cmd)
            if exitCode != 0:
                raise NameError(cyan + "cleanMergeVectors_sql() : " + bold + red + "An error occured during table import (spatialite_tool command). See error message above." + endC)

            global_query = sqlSimplifyBufferPolyQuery(global_query, input_table, buffer_size, simplification_tolerance)

        # Les tables correspondantes aux macroclasses ont été importées dans la base créée
        print(bold + green + "Database import complete." + '\n' + endC)

        starting_event = "cleanMergeVectors_spatialite() : Start merge polygons : "
        timeLine(path_time_log,starting_event)

        global_query_length = len(global_query)
        final_query = global_query[:global_query_length-6] + ";\""

        if debug >= 3:
            print(cyan + "cleanMergeVectors_sql() : " + endC + "final_query : " + str(final_query) + endC)

        # Application de la requete : erosions et lissage des bords
        print(bold + green + "START : erosion, simplification des polygones" + endC)

        if debug >= 1:
            print(cyan + "cleanMergeVectors_sql() : " + bold + green + "Queries applications" + endC)
        requete_cmd = sqlExecuteQuery(data_base_name, final_query)
        if debug >= 3:
            print(requete_cmd)
        exitCode = os.system(requete_cmd)
        if exitCode != 0:
            raise NameError(cyan + "cleanMergeVectors_sql() : " + bold + red + "An error occured during querying (spatialite command). See error message above." + endC)

        # Export de output_table
        if debug >= 1:
            print(cyan + "cleanMergeVectors_sql() : " + bold + green + "Table Export" + endC)
        requete_cmd = sqlExportShape(output_shape, output_table, data_base_name, epsg, shared_geometry_field, project_encoding, vector_geometry_type)
        exitCode = os.system(requete_cmd)
        if exitCode != 0:
            raise NameError(cyan + "cleanMergeVectors_sql() : " + bold + red + "An error occured during table export (spatialite_tool command). See error message above." + endC)

        # CONVERSION AU BON FORMAT ESRI SHAPEFILE
        #----------------------------------------
        if debug >= 1:
            print(cyan + "cleanMergeVectors_sql() : " + bold + green + "Conversion en ESRI SHAPEFILE" + endC)

        if debug >= 3:
            print(cyan + "cleanMergeVectors_sql() : " + endC + "format_vector : " + str(format_vector) + endC)
            print(cyan + "cleanMergeVectors_sql() : " + endC + "vector_cleaned_output : " + str(vector_cleaned_output) + endC)
            print(cyan + "cleanMergeVectors_sql() : " + endC + "vector_cleaned_training_output : " + str(vector_cleaned_training_output) + endC)

        # Compléments sur la fonction ogr2ogr : http://www.gdal.org/ogr2ogr.html
        exitCode = os.system("ogr2ogr -overwrite -a_srs  EPSG:%d -f \"%s\" \"%s\" \"%s\"" %(epsg, format_vector, vector_cleaned_output, vector_cleaned_training_output))
        if exitCode != 0:
            raise NameError(cyan + "cleanMergeVectors_sql() : " + bold + red + "An error occured during ogr2ogr command. See error message above." + endC)

        ending_event = "cleanMergeVectors_spatialite() : End merge polygons : "
        timeLine(path_time_log,ending_event)

        print(cyan + "cleanMergeVectors_sql() : " + bold + green + "Shape file polygons cleaning created." + endC)

    # NETTOYAGE DES FICHIERS INTERMEDIAIRES
    #--------------------------------------

    print(cyan + "cleanMergeVectors_sql() : " + bold + green + "Delete Temporary Files." + endC)

    output_folder = os.path.dirname(vector_cleaned_output)
    base_name = os.path.splitext(os.path.basename(data_base_name))[0]

    if debug >= 2:
        print(cyan + "cleanMergeVectors_sql() : " + endC + "base_name : " + str(base_name))
        print(cyan + "cleanMergeVectors_sql() : " + endC + "output_folder : " + str(output_folder))

    # Supression des .geom du dossier
    if debug >= 1:
        print(cyan + "cleanMergeVectors_sql() : " + endC + "Suppression des .geom" + endC)
    for to_delete in glob.glob(output_folder + os.sep + "*.geom"):
        removeFile(to_delete)

    # Supression des .xml du dossier
    if debug >= 1:
        print(cyan + "cleanMergeVectors_sql() : " + endC + "Suppression des .xml" + endC)
    for to_delete in glob.glob(output_folder + os.sep + "*.xml"):
        removeFile(to_delete)

    # Supression des .sqlite du dossier
    if debug >= 1:
        print(cyan + "cleanMergeVectors_sql() : " + endC + "Suppression des .sqlite" + endC)
    for to_delete in glob.glob(output_folder + os.sep + "*.sqlite"):
        removeFile(to_delete)

    # Nettoyer les répertoires temporaire
    deleteDir(repertory_clean_temp)

    # Suppression des fichiers vecteurs temporaires nettoyer des petites surfaces en entrée de sqlite
    for macro_input in polygon_macro_input_list:
        macroclass_name = os.path.splitext(os.path.basename(macro_input))[0]
        removeVectorFile(output_folder + os.sep + macroclass_name + "_masqued_micro_filtered" + extension_vector)

    # Supression du fichier vecteur temporaire sortie de sqlite
    if debug >= 1:
        print(cyan + "cleanMergeVectors_sql() : " + endC + "Suppression fichier shape temporaire sortie de sqlite" + endC)
    if os.path.isfile(vector_cleaned_training_output) :
        removeVectorFile(vector_cleaned_training_output)

    # Nettoyage des fichiers sources d'entrée si demandé
    if not save_results_intermediate:
        # Supression des resultats de kmeans masques (.../Image01_Macroclasse_masqued_micro.tif) si demande dans les parametres
        # et des échantillons d'apprentissage microclasses bruts, sans erosion ni simplification
        if debug >= 1:
            print(cyan + "cleanMergeVectors_sql() : " + endC + "Suppression des resultats de kmeans masques et des chantillons d'apprentissage microclasses bruts, sans erosion ni simplification" + endC)

        for polygon_macro_input in polygon_macro_input_list:
            base_polygon_macro_input = os.path.splitext(polygon_macro_input)[0]
            removeFile(base_polygon_macro_input + extension_raster)
            removeVectorFile(polygon_macro_input)

    print(cyan + "cleanMergeVectors_sql() : " + bold + green + "Temporary Files Cleaned." + endC)

    # Mise à jour du Log
    ending_event = "cleanMergeVectors_sql() : Clean polygons ending : "
    timeLine(path_time_log,ending_event)

    return
###########################################################################################################################################
# FONCTION cleanMergeVectors_ogr()                                                                                                        #
###########################################################################################################################################
def cleanMergeVectors_ogr(polygon_macro_input_list, vector_cleaned_output, table_output_file, path_time_log, buffer_size_list, buffer_approximate_list, minimal_area_list, simplification_tolerance_list, rate_clean_micro_class, name_column, shared_geometry_field='GEOMETRY', vector_geometry_type='POLYGON', project_encoding='UTF-8', epsg=2154, format_vector='ESRI Shapefile', extension_raster=".tif", extension_vector=".shp", save_results_intermediate=False, overwrite=True):
    """
    # ROLE:
    #     Filter les petits polygones, erode et simplifie la geometrie et nettoyer les fichiers vecteurs
    #   puis fusion des polygones
    #
    # ENTREES DE LA FONCTION :
    #     polygon_macro_input_list : Liste des fichiers vecteurs contenant les polygones à filtrer
    #     vector_cleaned_output : vecteur fichier shape de sortie au bon format ESRI
    #     table_output_file : fichier texte de proposition de realocation (suppression)
    #     path_time_log : le fichier de log de sortie
    #     buffer_size_list : listes taille des buffers, par macroclasses
    #     buffer_approximate_list: listes approximation des buffers, par macroclasses
    #     minimal_area_list : liste des surfaces minimales gardées pour les polygones
    #     simplification_tolerance_list : listes des parametres de simplification des polygones, par macroclasses
    #     rate_clean_micro_class : ratio pour le nettoyage des micro classes dont la somme total des surfaces est trop petites
    #     name_column : Nom de la colonne du fichier shape contenant l'information de classification
    #     shared_geometry_field : champ décrivant la géométrie des polygones, par defaut = 'GEOMETRY'
    #     vector_geometry_type  : type de géométrie des couches utilisées, par defaut = 'POLYGON'
    #     project_encoding      : encodage des vecteurs de sortie, par defaut = 'UTF-8'
    #     epsg : EPSG des entrees et des sorties  par defaut = 2154
    #     format_vector  : format des vecteurs de sortie, par defaut = 'ESRI Shapefile'
    #     extension_raster : extension des fichiers raster de sortie, par defaut = '.tif'
    #     extension_vector : extension du fichier vecteur de sortie, par defaut = '.shp'
    #     save_results_intermediate : fichiers de sorties intermediaires nettoyees, par defaut = False
    #     overwrite : ecrasement ou non des fichiers existants, par defaut = True
    # SORTIES DE LA FONCTION :
    #     Vecteurs polygonises, erodes et simplifies places dans path_output_polygons
    #     nettoyage des dossiers selon save_results_intermediate
    #
    """

    # Mise à jour du Log
    starting_event = "cleanMergeVectors_ogr() : Clean polygons starting : "
    timeLine(path_time_log,starting_event)

    if debug >= 3:
        print(bold + green + "Variables dans le parser" + endC)
        print(cyan + "cleanMergeVectors_ogr() : " + endC + "polygon_macro_input_list : " + str(polygon_macro_input_list) + endC)
        print(cyan + "cleanMergeVectors_ogr() : " + endC + "vector_cleaned_output : " + str(vector_cleaned_output) + endC)
        print(cyan + "cleanMergeVectors_ogr() : " + endC + "table_output_file : " + str(table_output_file) + endC)
        print(cyan + "cleanMergeVectors_ogr() : " + endC + "buffer_size_list : " + str(buffer_size_list) + endC)
        print(cyan + "cleanMergeVectors_ogr() : " + endC + "buffer_approximate_list : " + str(buffer_approximate_list) + endC)
        print(cyan + "cleanMergeVectors_ogr() : " + endC + "minimal_area_list : " + str(minimal_area_list) + endC)
        print(cyan + "cleanMergeVectors_ogr() : " + endC + "simplification_tolerance_list : " + str(simplification_tolerance_list) + endC)
        print(cyan + "cleanMergeVectors_ogr() : " + endC + "rate_clean_micro_class : " + str(rate_clean_micro_class) + endC)
        print(cyan + "cleanMergeVectors_ogr() : " + endC + "name_column : " + str(name_column) + endC)
        print(cyan + "cleanMergeVectors_ogr() : " + endC + "shared_geometry_field : " + str(shared_geometry_field) + endC)
        print(cyan + "cleanMergeVectors_ogr() : " + endC + "vector_geometry_type : " + str(vector_geometry_type) + endC)
        print(cyan + "cleanMergeVectors_ogr() : " + endC + "project_encoding : " + str(project_encoding) + endC)
        print(cyan + "cleanMergeVectors_ogr() : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "cleanMergeVectors_ogr() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "cleanMergeVectors_ogr() : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "cleanMergeVectors_ogr() : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "cleanMergeVectors_ogr() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "cleanMergeVectors_ogr() : " + endC + "overwrite : " + str(overwrite) + endC)

    # constantes
    HEADER_TABLEAU_MODIF = "MICROCLASSE;TRAITEMENT\n"

    FOLDER_CLEAN_TEMP = 'Clean_'
    FOLDER_SIMPLE_TEMP = 'Simplification_'
    FOLDER_BUFF_TEMP = 'Buff_'

    SUFFIX_VECTOR_CLEAN = '_clean'
    SUFFIX_VECTOR_SIMPLE = '_simple'
    SUFFIX_VECTOR_BUFF = '_buff'
    SUFFIX_VECTOR_BUFF_POLY = '_buff_poly'
    SUFFIX_VECTOR_BUFF_CLEAN = '_buff_clean'

    # SUPRESSION DES ANCIENS FICHIERS
    #--------------------------------

    print(cyan + "cleanMergeVectors_ogr() : " + bold + green + "Polygons cleaning" + endC)

    # test si le fichier vecteur de sortie existe déjà et que overwrite n'est pas activé
    check = os.path.isfile(vector_cleaned_output)
    if check and not overwrite :
        print(bold + yellow + "cleanMergeVectors_ogr() : Vector file %s already done : no actualisation."%(vector_cleaned_output) + endC)
    else:
        if check:
            try:
                # Tentative de suppression du fichier vecteur résultat
                removeFile(vector_cleaned_output)
                print(bold + green + "cleanMergeVectors_ogr() : Vector file %s removed."%(vector_cleaned_output) + endC)
            except Exception:
                pass  # Si le fichier ne peut pas être supprimé, on suppose qu'il n'existe pas et on passe à la suite

        # nom de la base
        name = os.path.splitext(os.path.basename(vector_cleaned_output))[0]

        # définition des répertoires temporaires
        repertory_output = os.path.dirname(vector_cleaned_output)
        repertory_clean_temp = repertory_output + os.sep + FOLDER_CLEAN_TEMP + name
        repertory_simple_temp = repertory_output + os.sep + FOLDER_SIMPLE_TEMP + name
        repertory_buff_temp = repertory_output + os.sep + FOLDER_BUFF_TEMP + name

        if debug >= 4:
            print(cyan + "cleanMergeVectors_ogr() : " + endC + "repertory_clean_temp : " + str(repertory_clean_temp) + endC)
            print(cyan + "cleanMergeVectors_ogr() : " + endC + "repertory_simple_temp : " + str(repertory_simple_temp) + endC)
            print(cyan + "cleanMergeVectors_ogr() : " + endC + "repertory_buff_temp : " + str(repertory_buff_temp) + endC)

        # Creation des répertoires temporaire si ils n'existent pas
        if not os.path.isdir(repertory_output):
            os.makedirs(repertory_output)
        if not os.path.isdir(repertory_clean_temp):
            os.makedirs(repertory_clean_temp)
        if not os.path.isdir(repertory_simple_temp):
            os.makedirs(repertory_simple_temp)
        if not os.path.isdir(repertory_buff_temp):
            os.makedirs(repertory_buff_temp)

        # Nettoyage des répertoires temporaires non vides

        cleanTempData(repertory_clean_temp)
        cleanTempData(repertory_simple_temp)
        cleanTempData(repertory_buff_temp)

        # NETTOYAGE DES PETITS VECTEURS puis SIMPLIFICATION DES VECTEURS puis EROSION DES VECTEURS
        #-----------------------------------------------------------------------------------------
        polygon_macro_cleaned_list = []
        polygon_macro_simplified_list = []
        polygon_macro_bufferized_list = []
        polygon_macro_bufferized_poly_list = []
        polygon_macro_bufferized_cleaned_list = []
        size_micro_class_list = []

        # pour toutes les macroclasses d'une image
        for macroclass_id in range(len(polygon_macro_input_list)):

            polygon_input = polygon_macro_input_list[macroclass_id]
            buffer_size = buffer_size_list[macroclass_id]
            buffer_approximate = buffer_approximate_list[macroclass_id]
            simplification_tolerance = simplification_tolerance_list[macroclass_id]
            minimal_area = minimal_area_list[macroclass_id]

            extension = os.path.splitext(polygon_input)[1]
            base_name = os.path.splitext(os.path.basename(polygon_input))[0]

            polygon_cleaned = repertory_clean_temp + os.sep + base_name +  SUFFIX_VECTOR_CLEAN + extension
            polygon_macro_cleaned_list.append(polygon_cleaned)

            polygon_simplified = repertory_simple_temp + os.sep + base_name + SUFFIX_VECTOR_SIMPLE + extension
            polygon_macro_simplified_list.append(polygon_simplified)

            polygon_bufferized = repertory_buff_temp + os.sep +  base_name + SUFFIX_VECTOR_BUFF + extension
            polygon_macro_bufferized_list.append(polygon_bufferized)

            polygon_bufferized_poly = repertory_buff_temp + os.sep +  base_name + SUFFIX_VECTOR_BUFF_POLY + extension
            polygon_macro_bufferized_poly_list.append(polygon_bufferized_poly)

            polygon_bufferized_cleaned = repertory_buff_temp + os.sep +  base_name + SUFFIX_VECTOR_BUFF_CLEAN + extension
            polygon_macro_bufferized_cleaned_list.append(polygon_bufferized_cleaned)

            if debug >= 3:
                print(cyan + "cleanMergeVectors_ogr() : " + endC + "polygon_input : " + str(polygon_input) + endC)
                print(cyan + "cleanMergeVectors_ogr() : " + endC + "polygon_cleaned : " + str(polygon_cleaned) + endC)
                print(cyan + "cleanMergeVectors_ogr() : " + endC + "polygon_simplified : " + str(polygon_simplified) + endC)
                print(cyan + "cleanMergeVectors_ogr() : " + endC + "polygon_bufferized : " + str(polygon_bufferized) + endC)
                print(cyan + "cleanMergeVectors_ogr() : " + endC + "polygon_bufferized_poly : " + str(polygon_bufferized_poly) + endC)
                print(cyan + "cleanMergeVectors_ogr() : " + endC + "polygon_bufferized_cleaned : " + str(polygon_bufferized_cleaned) + endC)
                print(cyan + "cleanMergeVectors_ogr() : " + endC + "shared_geometry_field : " + str(shared_geometry_field) + endC)
                print(cyan + "cleanMergeVectors_ogr() : " + endC + "project_encoding : " + str(project_encoding) + endC)
                print(cyan + "cleanMergeVectors_ogr() : " + endC + "epsg : " + str(epsg) + endC)
                print(cyan + "cleanMergeVectors_ogr() : " + endC + "vector_geometry_type : " + str(vector_geometry_type) + endC)
                print(cyan + "cleanMergeVectors_ogr() : " + endC + "format_vector : " + str(format_vector) + endC)
                print(cyan + "cleanMergeVectors_ogr() : " + endC + "minimal_area : " + str(minimal_area) + endC)
                print(cyan + "cleanMergeVectors_ogr() : " + endC + "buffer_size : " + str(buffer_size) + endC)
                print(cyan + "cleanMergeVectors_ogr() : " + endC + "buffer_approximate : " + str(buffer_approximate) + endC)
                print(cyan + "cleanMergeVectors_ogr() : " + endC + "simplification_tolerance : " + str(simplification_tolerance) + endC)

            # nettoyage des petites surfaces
            if minimal_area != 0 :
                cleanMiniAreaPolygons(polygon_input, polygon_cleaned, minimal_area, name_column, format_vector)
            else :
                polygon_cleaned = polygon_input

            # Simplification des vecteurs
            if simplification_tolerance != 0 :
                simplifyVector(polygon_cleaned, polygon_simplified, simplification_tolerance, format_vector)
            else :
                polygon_simplified = polygon_cleaned

            # Erosion des vecteurs
            if buffer_size != 0 :
                bufferVector(polygon_simplified, polygon_bufferized, buffer_size, "", 1.0, buffer_approximate, format_vector)
            else :
                polygon_bufferized = polygon_simplified

            # Transformation des multi-polygones en simple polygones
            multigeometries2geometries(polygon_bufferized, polygon_bufferized_poly, [name_column], format_vector)

            # nettoyage des petites surfaces
            size_area_by_class_dico = cleanMiniAreaPolygons(polygon_bufferized_poly, polygon_bufferized_cleaned, minimal_area, name_column, format_vector)
            size_micro_class_list.append(size_area_by_class_dico)

        # IDENTIFICATION DES PETITES MICRO CLASSES DONT LA SURFACE TOTALE EST INFERIEURE AU RATIO
        #---------------------------------------------------------------------------------
        min_area_micro_class = 0
        for macroclass_id in range(len(size_micro_class_list)):
            size_area_by_class_dico = size_micro_class_list[macroclass_id]
            print(cyan + "cleanMergeVectors_ogr() : " + endC + "Size Area by class" + endC)
            if size_area_by_class_dico is None :
                print(bold + yellow + "No subclasses " + endC)
            else:
                sum_area_micro_class = 0
                nb_micro_cass = 0
                for key, value in size_area_by_class_dico.items():
                    print(bold + green + "Class : " + endC + str(key) + bold + green + " Area : " + endC + str(value) + endC + bold + green + endC)
                    sum_area_micro_class += value
                    nb_micro_cass += 1
                if nb_micro_cass != 0:
                    moy_area_micro_class = sum_area_micro_class / nb_micro_cass
                else :
                    moy_area_micro_class = 0
                if min_area_micro_class == 0 :
                    min_area_micro_class = moy_area_micro_class
                elif min_area_micro_class > moy_area_micro_class :
                    min_area_micro_class = moy_area_micro_class

        print(bold + green + "min_area_micro_class : " + endC + str(min_area_micro_class) + endC)
        suppress_micro_class_list = []
        for macroclass_id in range(len(size_micro_class_list)):
            size_area_by_class_dico = size_micro_class_list[macroclass_id]
            if size_area_by_class_dico is None :
                print(bold + yellow + "No subclasses " + endC)
            else:
                for key, value in size_area_by_class_dico.items():
                    if value < (min_area_micro_class * (rate_clean_micro_class / 100)) :
                        print(bold + green + "Suppress micro class : " + endC + str(key) + endC)
                        suppress_micro_class_list.append(key)

        # FUSION DES VECTEURS DES MACRO CLASSES
        #--------------------------------------
        starting_event = "cleanMergeVectors_ogr() : Start merge polygons : "
        timeLine(path_time_log,starting_event)
        if len(polygon_macro_bufferized_cleaned_list) > 1:
            fusionVectors(polygon_macro_bufferized_cleaned_list, vector_cleaned_output, format_vector)
        else :
            copyVectorFile(polygon_macro_bufferized_cleaned_list[0], vector_cleaned_output)
        ending_event = "cleanMergeVectors_ogr() : End merge polygons : "
        timeLine(path_time_log,ending_event)

        # ECRITURE DANS LE FICHIER DES MICRO CLASSES IDENTIFIEES TROP PETITES
        #--------------------------------------------------------------------
        # Test si ecrassement de la table précédemment créée
        check = os.path.isfile(table_output_file)
        if check and not overwrite :
            print(cyan + "cleanMergeVectors_ogr() : " + bold + yellow + "Modifier table already exists." + '\n' + endC)
        else:
            # Tenter de supprimer le fichier
            try:
                removeFile(table_output_file)
            except Exception:
                pass   # Ignore l'exception levee si le fichier n'existe pas (et ne peut donc pas être supprime)
            # lister les micro classes à supprimer
            text_output = HEADER_TABLEAU_MODIF
            for micro_class_del in suppress_micro_class_list:
                text_output += "%d;-1\n" %(micro_class_del)

            # Ecriture du fichier proposition de réaffectation
            writeTextFile(table_output_file, text_output)

    # NETTOYAGE DES FICHIERS INTERMEDIAIRES
    #--------------------------------------

    print(cyan + "cleanMergeVectors_ogr() : " + bold + green + "Delete Temporary Files." + endC)
    output_folder = os.path.dirname(vector_cleaned_output)

    # Supression des .geom du dossier input
    if debug >= 1:
        print(cyan + "cleanMergeVectors_ogr() : " + endC + "Suppression des .geom" + endC)
    for to_delete in glob.glob(output_folder + os.sep + "*.geom"):
        removeFile(to_delete)

    # Supression des .xml du dossier input
    if debug >= 1:
        print(cyan + "cleanMergeVectors_ogr() : " + endC + "Suppression des .xml" + endC)
    for to_delete in glob.glob(output_folder + os.sep + "*.xml"):
        removeFile(to_delete)

    # Nettoyage des fichiers sources d'entrée si demandé
    if not save_results_intermediate:

        # Suppression des fichiers vecteurs temporaires
        deleteDir(repertory_clean_temp)
        deleteDir(repertory_simple_temp)
        deleteDir(repertory_buff_temp)

    print(cyan + "cleanMergeVectors_ogr() : " + bold + green + "Temporary Files Cleaned." + endC)

    # Mise à jour du Log
    ending_event = "cleanMergeVectors_ogr() : Clean polygons ending : "
    timeLine(path_time_log,ending_event)

    return

###########################################################################################################################################
# MISE EN PLACE DU PARSER                                                                                                                 #
###########################################################################################################################################

# Code executé seulement dans le cas ou le script est lancé depuis une ligne de commande
# Il n'est pas executé lors d'un import MicroSamplePolygonization.py
# Exemple de lancement en ligne de commande:
# python MicroSamplePolygonization.py -il ../ImagesTestChaine/APTV_05/Micro/APTV_05_Anthropise_masqued_micro.tif ../ImagesTestChaine/APTV_05/Micro/APTV_05_Eau_masqued_micro.tif ../ImagesTestChaine/APTV_05/Micro/APTV_05_Ligneux_masqued_micro.tif -o ../ImagesTestChaine/APTV_05/Micro/APTV_05_cleaned.shp -t ../ImagesTestChaine/APTV_05/Micro/APTV_05_prop_tab.txt -bsl -0.5 -0.5 -0.5 -bal 2 2 2 -mal 2.0 2.0 2.0 -stl 1.0 1.0 1.0 -rcmc 15.0 -sgf GEOMETRY -vgt POLYGON -vef 'ESRI Shapefile' -pe UTF-8 -epsg 2154 -log ../ImagesTestChaine/APTV_05/fichierTestLog.txt -sav
# python -m MicroSamplePolygonization -il /home/scgsi/Test/ZoneTest1Vectoristion/Echantillons_Micro/bati_kmeans.tif /home/scgsi/Test/ZoneTest1Vectoristion/Echantillons_Micro/route_kmeans.tif /home/scgsi/Test/ZoneTest1Vectoristion/Echantillons_Micro/eau_kmeans.tif /home/scgsi/Test/ZoneTest1Vectoristion/Echantillons_Micro/solnu_kmeans.tif /home/scgsi/Test/ZoneTest1Vectoristion/Echantillons_Micro/vegetation_kmeans.tif -o /home/scgsi/Test/ZoneTest1Vectoristion/Echantillons_Micro2/microsamples_merged.shp -t /home/scgsi/Test/ZoneTest1Vectoristion/Echantillons_Micro2/microsamples_merged_realocation_table.txt -ero 1 1 1 1 2 -umc 8 -ts 3000 -bsl 0.0 0.0 0.0 0.0 0.0  -bal 2 2 2 2 2  -mal 2.0 2.0 2.0 2.0 2.0  -stl 1.0 1.0 1.0 1.0 1.0 -rcmc 25.0 -sgf GEOMETRY -vgt POLYGON -vef 'ESRI Shapefile' -pe UTF-8 -epsg 2154 -col id -log /home/scgsi/Test/ZoneTest1Vectoristion/Echantillons_Micro2/test_classification_image_sat.log

def main(gui=False):

    # Définition des arguments possibles pour l'appel en ligne de commande
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, prog="MicroSamplePolygonization", description="\
    Info : MicroSamplePolygonization of raster. \n\
    Objectif : Convertir les polygones raster en vecteur, nettoyer les petit polygones et fusioner en un seul fichier vecteur. \n\
    Example : python MicroSamplePolygonization.py -il ../ImagesTestChaine/APTV_05/Micro/APTV_05_Anthropise_masqued_micro.tif \n\
                                           ../ImagesTestChaine/APTV_05/Micro/APTV_05_Eau_masqued_micro.tif \n\
                                           ../ImagesTestChaine/APTV_05/Micro/APTV_05_Ligneux_masqued_micro.tif \n\
                                        -o ../ImagesTestChaine/APTV_05/Micro/APTV_05_cleaned.shp \n\
                                        -t ../ImagesTestChaine/APTV_05/Micro/APTV_05_prop_tab.txt \n\
                                        -ero 1 1 1 -umc 8 -ts 3000 -bsl -0.5 -0.5 -0.5 -bal 2 2 2 -mal 2.0 2.0 2.0 -stl 1.0 1.0 1.0 \n\
                                        -rcmc 15.0 -sgf GEOMETRY -vgt POLYGON -vef 'ESRI Shapefile' -pe UTF-8 -epsg 2154 \n\
                                        -log ../ImagesTestChaine/APTV_05/fichierTestLog.txt ")

    # Paramètres
    parser.add_argument('-il','--images_input_list',default="",nargs="+",help="List of input images to polygonize.", type=str, required=True)
    parser.add_argument('-o','--vector_output',default="",help="Vector output result polygonization and fusion of the input images list", type=str, required=True)
    parser.add_argument('-t','--proposal_table_output',default="",help="Proposal table output to realocation micro class", type=str, required=True)
    parser.add_argument('-ero','--raster_erode_values_list',nargs="+",default=[],help="List of value to erode input raster micro class. By default at 0 no erode action need", type=int, required=False)
    parser.add_argument('-umc','--umc_value',default=10,help="For vectorisation, value of appropriate UMC (in number of pixels). Put a multiple of the pixel. By default : 10", type=int, required=False)
    parser.add_argument('-ts','--tilesize',default=3000,help="For vectorisation, size of the working windows in x and y. By default : 3000", type=int, required=False)
    parser.add_argument("-bsl",'--buffer_size_list',nargs="+",default=[],help="list of buffer size for polygon erosion (in meters by macroclass) ex : -0.5", type=float, required=True)
    parser.add_argument("-bal",'--buffer_approximate_list',nargs="+",default=[],help="list of buffer approximate for polygon erosion (number of segments in 90 degre) ex : 2", type=int, required=True)
    parser.add_argument("-mal",'--minimal_area_list',nargs="+",default=[],help="list minimum sizes for polygons to keep during cleaning (in SurfaceMeters by macroclass) ex : 2.0", type=float, required=True)
    parser.add_argument("-stl",'--simplification_tolerance_list',nargs="+",default=[],help="Simplification parameter of contour for polygons, by class (in meters by macroclass) ex : 1.0", type=float, required=True)
    parser.add_argument("-rcmc",'--rate_clean_micro_class',default=0.0,help="ratio for cleaning micro classes, the total sum of the surfaces is too small, in percentage, example : 20 percent)", type=float, required=False)
    parser.add_argument("-sgf",'--shared_geometry_field',default='GEOMETRY',help="The geometry of polygons", type=str, required=False)
    parser.add_argument("-vgt",'--vector_geometry_type',default='POLYGON',help="The geometry type of layers", type=str, required=False)
    parser.add_argument("-pe",'--project_encoding',default='UTF-8',help="The encoding of vectors", type=str, required=False)
    parser.add_argument("-epsg",'--epsg',default=2154,help="Projection parameter of data.", type=int, required=False)
    parser.add_argument('-col','--name_col',default="class", help="Name of the column containing the shapefile classification of information", type=str, required=False)
    parser.add_argument("-vef",'--format_vector',default='ESRI Shapefile',help="The format of vectors", type=str, required=False)
    parser.add_argument('-rae','--extension_raster', default=".tif", help="Option : Extension file for image raster. By default : '.tif'", type=str, required=False)
    parser.add_argument('-vee','--extension_vector',default=".shp",help="Option : Extension file for vector. By default : '.shp'", type=str, required=False)
    parser.add_argument('-log','--path_time_log',default="",help="Name of log", type=str, required=False)
    parser.add_argument('-sav','--save_results_inter',action='store_true',default=False,help="Save or delete intermediate result after the process. By default, False", required=False)
    parser.add_argument('-now','--overwrite',action='store_false',default=True,help="Overwrite files with same names. By default, True", required=False)
    parser.add_argument('-debug','--debug',default=3,help="Option : Value of level debug trace, default : 3 ",type=int, required=False)
    args = displayIHM(gui, parser)

    # RECUPERATION DES ARGUMENTS

    # Récupération des images à traiter
    if args.images_input_list != None:
        images_input_list = args.images_input_list
        for image_input in images_input_list :
            if not os.path.isfile(image_input):
                raise NameError (cyan + "MicroSamplePolygonization : " + bold + red  + "File %s not existe!" %(image_input) + endC)

    # Récupération de la table de proposition de sortie
    if args.proposal_table_output != None:
        proposal_table_output = args.proposal_table_output

    # Parametre valeur d'érostion des fichiers rasteurs d'entrée
    if args.raster_erode_values_list != None:
        raster_erode_values_list = args.raster_erode_values_list

    # Les parametres de vectorisation
    if args.umc_value != None:
        umc_value = args.umc_value

    if args.tilesize != None:
        tilesize = args.tilesize

    if args.buffer_size_list != None:
        buffer_size_list = args.buffer_size_list

    if args.buffer_approximate_list != None:
        buffer_approximate_list = args.buffer_approximate_list

    if args.minimal_area_list != None:
        minimal_area_list = args.minimal_area_list

    if args.simplification_tolerance_list != None:
        simplification_tolerance_list = args.simplification_tolerance_list

    if args.rate_clean_micro_class != None:
        rate_clean_micro_class = args.rate_clean_micro_class

    if args.shared_geometry_field != None:
        shared_geometry_field = args.shared_geometry_field

    if args.vector_geometry_type != None:
        vector_geometry_type = args.vector_geometry_type

    if args.format_vector != None:
        format_vector = args.format_vector

    if args.project_encoding != None:
        project_encoding = args.project_encoding

    if args.epsg != None:
        epsg = args.epsg

    # polygones
    if args.name_col != None:
        name_column = args.name_col

    # Récupération de l'image de sortie
    if args.vector_output != None:
        vector_output = args.vector_output

    # Paramètre de l'extension des images rasters
    if args.extension_raster != None:
        extension_raster = args.extension_raster

    # Récupération de l'extension des fichiers vecteurs
    if args.extension_vector != None:
        extension_vector = args.extension_vector

    # Récupération du nom du fichier log
    if args.path_time_log!= None:
        path_time_log = args.path_time_log

    if args.save_results_inter != None:
        save_results_intermediate = args.save_results_inter

    if args.overwrite!= None:
        overwrite = args.overwrite

    # Récupération de l'option niveau de debug
    if args.debug!= None:
        global debug
        debug = args.debug

    # Affichage des arguments récupérés
    if debug >= 3:
        print(bold + green + "Variables dans le parser" + endC)
        print(cyan + "MicroSamplePolygonization : " + endC + "images_input_list : " + str(images_input_list) + endC)
        print(cyan + "MicroSamplePolygonization : " + endC + "vector_output : " + str(vector_output) + endC)
        print(cyan + "MicroSamplePolygonization : " + endC + "proposal_table_output : " + str(proposal_table_output) + endC)
        print(cyan + "MicroSamplePolygonization : " + endC + "raster_erode_values_list : " + str(raster_erode_values_list) + endC)
        print(cyan + "MicroSamplePolygonization : " + endC + "umc_value : " + str(umc_value) + endC)
        print(cyan + "MicroSamplePolygonization : " + endC + "tilesize : " + str(tilesize) + endC)
        print(cyan + "MicroSamplePolygonization : " + endC + "buffer_size_list : " + str(buffer_size_list) + endC)
        print(cyan + "MicroSamplePolygonization : " + endC + "buffer_approximate_list : " + str(buffer_approximate_list) + endC)
        print(cyan + "MicroSamplePolygonization : " + endC + "minimal_area_list : " + str(minimal_area_list) + endC)
        print(cyan + "MicroSamplePolygonization : " + endC + "simplification_tolerance_list : " + str(simplification_tolerance_list) + endC)
        print(cyan + "MicroSamplePolygonization : " + endC + "rate_clean_micro_class : " + str(rate_clean_micro_class) + endC)
        print(cyan + "MicroSamplePolygonization : " + endC + "shared_geometry_field : " + str(shared_geometry_field) + endC)
        print(cyan + "MicroSamplePolygonization : " + endC + "vector_geometry_type : " + str(vector_geometry_type) + endC)
        print(cyan + "MicroSamplePolygonization : " + endC + "project_encoding : " + str(project_encoding) + endC)
        print(cyan + "MicroSamplePolygonization : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "MicroSamplePolygonization : " + endC + "name_col : " + str(name_column) + endC)
        print(cyan + "MicroSamplePolygonization : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "MicroSamplePolygonization : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "MicroSamplePolygonization : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "MicroSamplePolygonization : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "MicroSamplePolygonization : " + endC + "save_results_inter : " + str(save_results_intermediate) + endC)
        print(cyan + "MicroSamplePolygonization : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "MicroSamplePolygonization : " + endC + "debug : " + str(debug) + endC)

    # MODE EXECUTION DES FONCTIONS
    is_spatialite = False

    # Si les dossier de sorties n'existent pas, on les crées
    repertory_output = os.path.dirname(proposal_table_output)
    if not os.path.isdir(repertory_output):
        os.makedirs(repertory_output)

    repertory_output = os.path.dirname(vector_output)
    if not os.path.isdir(repertory_output):
        os.makedirs(repertory_output)

    # Pour tous les fichiers rasters macro à polygoniser
    vector_macro_output_list = []
    images_erode_list = []

    # Création des chemins complet des images d'entrée et des polygones de sortie
    for image_input in images_input_list :
        vector_temp_output = repertory_output + os.sep + os.path.splitext(os.path.basename(image_input))[0] + extension_vector
        vector_macro_output_list.append(vector_temp_output)
        image_erode = repertory_output + os.sep + os.path.splitext(os.path.basename(image_input))[0] + "_erode" + extension_raster
        images_erode_list.append(image_erode)

    # Execution d'érosion des fichiers images d'entrées
    if len(raster_erode_values_list) != 0:
        erodeImages(images_input_list, images_erode_list,  raster_erode_values_list, path_time_log, save_results_intermediate, overwrite)
    else :
        images_erode_list = images_input_list

    # Execution de la polygonisation
    if tilesize == 0:
        polygonize_gdal(images_erode_list, vector_macro_output_list, path_time_log, name_column, format_vector, save_results_intermediate, overwrite)
    else:
        #~ polygonize_otb(images_erode_list, vector_macro_output_list, path_time_log, name_column, umc_value, tilesize, format_vector, extension_raster, extension_vector, save_results_intermediate, overwrite)
        vector_temp_output = os.path.splitext(vector_output)[0] + "_temp" + os.path.splitext(vector_output)[1]
        polygonize_otb2(images_erode_list, vector_temp_output, path_time_log, name_column, umc_value, tilesize, format_vector, extension_raster, extension_vector, save_results_intermediate, overwrite)
        vector_macro_output_list = [vector_temp_output]

    # Execution du nettoyage des polygones
    if is_spatialite :
        cleanMergeVectors_sql(vector_macro_output_list, vector_output, path_time_log, buffer_size_list, minimal_area_list, simplification_tolerance_list, shared_geometry_field, vector_geometry_type, project_encoding, epsg, format_vector, extension_raster, extension_vector, save_results_intermediate, overwrite)
    else :
        cleanMergeVectors_ogr(vector_macro_output_list, vector_output, proposal_table_output, path_time_log, buffer_size_list, buffer_approximate_list, minimal_area_list, simplification_tolerance_list, rate_clean_micro_class, name_column, shared_geometry_field, vector_geometry_type, project_encoding, epsg, format_vector, extension_raster, extension_vector, save_results_intermediate, overwrite)

    # Suppression des images érodées et temp
    if not save_results_intermediate :
        if len(raster_erode_values_list) != 0 :
            for image_erode in images_erode_list :
                removeFile(image_erode)

# ================================================

if __name__ == '__main__':
  main(gui=False)
