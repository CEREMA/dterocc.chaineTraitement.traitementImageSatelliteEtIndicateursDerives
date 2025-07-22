#!/usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

"""
Nom de l'objet : WaterHeight.py
Description :
-------------
Objectif : calculer les hauteurs d'eau sur une zone inondée
Remarque : issu en partie de la traduction du plugin cartoZI, développé par le SPC Loire Cher Indre et porté par le SCHAPI : http://wikhydro.developpement-durable.gouv.fr/index.php/CartoZI

-----------------
Outils utilisés :

------------------------------
Historique des modifications :
01/02/2019 : création

-----------------------
A réfléchir / A faire :

"""

# Import des bibliothèques Python
from __future__ import print_function
import os, argparse
from osgeo import ogr
from Lib_display import bold,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_file import cleanTempData, deleteDir, removeFile, removeVectorFile
from Lib_grass import initializeGrass, connectionGrass, importVectorOgr2Grass, exportVectorOgr2Grass, importRasterGdal2Grass, pointsAlongPolylines, sampleRasterUnderPoints
from Lib_log import timeLine
from Lib_raster import getEmpriseImage, getPixelWidthXYImage, rasterCalculator, cutImageByVector
from Lib_saga import triangulationDelaunay
from Lib_vector import convertePolygon2Polylines, addNewFieldVector, updateIndexVector
from VectorRasterCutting import cutRasterImages
from Vectorization import vectorizeClassification, vectorizeGrassClassification

# Niveau de debug (variable globale)
debug = 3

########################################################################
# FONCTION classesOfWaterHeights()                                     #
########################################################################
def classesOfWaterHeights(input_flooded_areas_vector, input_digital_elevation_model_file, output_heights_classes_file, output_heights_classes_vector, heights_classes='0,0.5,1,1.5,2', epsg=2154, no_data_value=0, format_raster='GTiff', format_vector='ESRI Shapefile', extension_raster='.tif', extension_vector='.shp', grass_gisbase=os.environ['GISBASE'], grass_gisdb='GRASS_database', grass_location='LOCATION', grass_mapset='MAPSET', path_time_log='', save_results_intermediate=False, overwrite=True):
    """
    # ROLE :
    #     Cartographie des classes de hauteurs d'eau
    #
    # ENTREES DE LA FONCTION :
    #     input_flooded_areas_vector : fichier d'emprise inondée en entrée (en format vecteur)
    #     input_digital_elevation_model_file : fichier du MNT en entrée (en format raster)
    #     output_heights_classes_file : fichier des classes de hauteurs d'eau en sortie (en format raster)
    #     output_heights_classes_vector : fichier des classes de hauteurs d'eau en sortie (en format vecteur)
    #     heights_classes : classes de hauteurs d'eau à générer. Par défaut : '0,0.5,1,1.5,2'
    #     epsg : code epsg du système de projection. Par défaut : 2154
    #     no_data_value : valeur NoData des pixels des fichiers raster. Par défaut : 0
    #     format_raster : format des fichiers raster. Par défaut : 'GTiff'
    #     format_vector : format des fichiers vecteur. Par défaut : 'ESRI Shapefile'
    #     extension_raster : extension des fichiers raster. Par défaut : '.tif'
    #     extension_vector : extension des fichiers vecteur. Par défaut : '.shp'
    #     grass_gisbase : variable d'environnement GRASS. Par défaut : os.environ['GISBASE']
    #     grass_gisdb : nom de la géodatabase GRASS. Par défaut : 'GRASS_database'
    #     grass_location : paramètre 'location' de la géodatabase GRASS. Par défaut : 'LOCATION'
    #     grass_mapset : paramètre 'mapset' de la géodatabase GRASS. Par défaut : 'MAPSET'
    #     path_time_log : fichier log de sortie, par défaut vide
    #     save_results_intermediate : fichiers temporaires conservés, par défaut = False
    #     overwrite : écrase si un fichier existant a le même nom qu'un fichier de sortie, par défaut = True
    #
    # SORTIES DE LA FONCTION :
    #     N.A.
    """

    if debug >= 3:
        print('\n' + bold + green + "Classes de hauteurs d'eau - Variables dans la fonction :" + endC)
        print(cyan + "    classesOfWaterHeights() : " + endC + "input_flooded_areas_vector : " + str(input_flooded_areas_vector) + endC)
        print(cyan + "    classesOfWaterHeights() : " + endC + "input_digital_elevation_model_file : " + str(input_digital_elevation_model_file) + endC)
        print(cyan + "    classesOfWaterHeights() : " + endC + "output_heights_classes_file : " + str(output_heights_classes_file) + endC)
        print(cyan + "    classesOfWaterHeights() : " + endC + "output_heights_classes_vector : " + str(output_heights_classes_vector) + endC)
        print(cyan + "    classesOfWaterHeights() : " + endC + "heights_classes : " + str(heights_classes) + endC)
        print(cyan + "    classesOfWaterHeights() : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "    classesOfWaterHeights() : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "    classesOfWaterHeights() : " + endC + "format_raster : " + str(format_raster) + endC)
        print(cyan + "    classesOfWaterHeights() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "    classesOfWaterHeights() : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "    classesOfWaterHeights() : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "    classesOfWaterHeights() : " + endC + "grass_gisbase : " + str(grass_gisbase) + endC)
        print(cyan + "    classesOfWaterHeights() : " + endC + "grass_gisdb : " + str(grass_gisdb) + endC)
        print(cyan + "    classesOfWaterHeights() : " + endC + "grass_location : " + str(grass_location) + endC)
        print(cyan + "    classesOfWaterHeights() : " + endC + "grass_mapset : " + str(grass_mapset) + endC)
        print(cyan + "    classesOfWaterHeights() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "    classesOfWaterHeights() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "    classesOfWaterHeights() : " + endC + "overwrite : " + str(overwrite) + endC + '\n')

    # Définition des constantes
    ENCODING_RASTER_FLOAT = 'float'
    ENCODING_RASTER_UINT8 = 'uint8'
    EXTENSION_RASTER_SAGA = '.sdat'
    FORMAT_VECTOR_GRASS = format_vector.replace(' ', '_')
    SUFFIX_TEMP = '_temp'
    SUFFIX_LINES = '_lines'
    SUFFIX_POINTS = '_points'
    SUFFIX_ALTI = '_altitude'
    SUFFIX_CUT = '_cut'
    SUFFIX_RAW = '_raw_heights'
    INDEX_FIELD = 'idx'
    ALTI_FIELD = 'altitude'
    VECTORISATION = 'GRASS'

    # Mise à jour du log
    starting_event = "classesOfWaterHeights() : Début du traitement : "
    timeLine(path_time_log, starting_event)

    print(cyan + "classesOfWaterHeights() : " + bold + green + "DEBUT DES TRAITEMENTS" + endC + '\n')

    # Définition des variables 'basename'
    flooded_areas_basename = os.path.splitext(os.path.basename(input_flooded_areas_vector))[0]
    digital_elevation_model_basename = os.path.splitext(os.path.basename(input_digital_elevation_model_file))[0]
    flooded_areas_lines_basename = flooded_areas_basename + SUFFIX_LINES
    flooded_areas_points_basename = flooded_areas_basename + SUFFIX_POINTS
    if output_heights_classes_file != "":
        output_heights_classes_basename = os.path.splitext(os.path.basename(output_heights_classes_file))[0]
        output_dirname = os.path.dirname(output_heights_classes_file)
    else:
        output_heights_classes_basename = os.path.splitext(os.path.basename(output_heights_classes_vector))[0]
        output_dirname = os.path.dirname(output_heights_classes_vector)

    # Définition des variables temp
    temp_directory = output_dirname + os.sep + output_heights_classes_basename + SUFFIX_TEMP
    flooded_areas_lines = temp_directory + os.sep + flooded_areas_lines_basename + extension_vector
    flooded_areas_points = temp_directory + os.sep + flooded_areas_points_basename + extension_vector
    altitude_points = temp_directory + os.sep + flooded_areas_points_basename + SUFFIX_ALTI + extension_vector
    altitude_grid = temp_directory + os.sep + flooded_areas_basename + SUFFIX_ALTI + EXTENSION_RASTER_SAGA
    altitude_file = temp_directory + os.sep + flooded_areas_basename + SUFFIX_ALTI + SUFFIX_CUT + extension_raster
    digital_elevation_model_cut = temp_directory + os.sep + digital_elevation_model_basename + SUFFIX_CUT + extension_raster
    raw_heights = temp_directory + os.sep + flooded_areas_basename + SUFFIX_RAW + extension_raster
    heights_classes_temp = temp_directory + os.sep + output_heights_classes_basename + extension_raster
    if output_heights_classes_file == "":
        output_heights_classes_file = output_dirname + os.sep + output_heights_classes_basename + extension_raster

    # Nettoyage des traitements précédents
    if debug >= 3:
        print(cyan + "classesOfWaterHeights() : " + endC + "Nettoyage des traitements précédents." + endC + '\n')
    removeFile(output_heights_classes_file)
    removeVectorFile(output_heights_classes_vector, format_vector=format_vector)
    cleanTempData(temp_directory)

    #############
    # Etape 0/6 # Préparation des traitements
    #############

    print(cyan + "classesOfWaterHeights() : " + bold + green + "ETAPE 0/6 - Début de la préparation des traitements." + endC + '\n')

    # Préparation de GRASS
    xmin, xmax, ymin, ymax = getEmpriseImage(input_digital_elevation_model_file)
    pixel_width, pixel_height = getPixelWidthXYImage(input_digital_elevation_model_file)
    grass_gisbase, grass_gisdb, grass_location, grass_mapset = initializeGrass(temp_directory, xmin, xmax, ymin, ymax, pixel_width, pixel_height, projection=epsg, gisbase=grass_gisbase, gisdb=grass_gisdb, location=grass_location, mapset=grass_mapset, clean_old=True, overwrite=overwrite)

    # Gestion des classes de hauteurs d'eau
    thresholds_list = heights_classes.split(',')
    thresholds_list_float = [float(x) for x in thresholds_list]
    thresholds_list_float.sort()
    thresholds_list_float_len = len(thresholds_list_float)

    print(cyan + "classesOfWaterHeights() : " + bold + green + "ETAPE 0/6 - Fin de la préparation des traitements." + endC + '\n')

    #############
    # Etape 1/6 # Création de points sur le périmètre de l'emprise inondée
    #############

    print(cyan + "classesOfWaterHeights() : " + bold + green + "ETAPE 1/6 - Début de la création de points sur le périmètre de l'emprise inondée." + endC + '\n')

    # Conversion de l'emprise inondée en polylignes
    convertePolygon2Polylines(input_flooded_areas_vector, flooded_areas_lines, overwrite=overwrite, format_vector=format_vector)

    # Création de points le long du polyligne
    use = 'vertex'
    dmax = 10
    percent = False
    importVectorOgr2Grass(flooded_areas_lines, flooded_areas_lines_basename, overwrite=overwrite)
    pointsAlongPolylines(flooded_areas_lines_basename, flooded_areas_points_basename, use=use, dmax=dmax, percent=percent, overwrite=overwrite)
    exportVectorOgr2Grass(flooded_areas_points_basename, flooded_areas_points, format_vector=FORMAT_VECTOR_GRASS, overwrite=overwrite)

    # Ajout d'un index sur les points
    addNewFieldVector(flooded_areas_points, INDEX_FIELD, ogr.OFTInteger, field_value=None, field_width=None, field_precision=None, format_vector=format_vector)
    updateIndexVector(flooded_areas_points, index_name=INDEX_FIELD, format_vector=format_vector)

    print(cyan + "classesOfWaterHeights() : " + bold + green + "ETAPE 1/6 - Fin de la création de points sur le périmètre de l'emprise inondée." + endC + '\n')

    #############
    # Etape 2/6 # Récupération de l'altitude sous chaque point
    #############

    print(cyan + "classesOfWaterHeights() : " + bold + green + "ETAPE 2/6 - Début de la récupération de l'altitude sous chaque point." + endC + '\n')

    # Ajout d'un champ pour récupérer l'altitude
    addNewFieldVector(flooded_areas_points, ALTI_FIELD, ogr.OFTReal, field_value=None, field_width=None, field_precision=None, format_vector=format_vector)

    # Echantillonnage du MNT sous le fichier points
    importVectorOgr2Grass(flooded_areas_points, flooded_areas_points_basename, overwrite=overwrite)
    importRasterGdal2Grass(input_digital_elevation_model_file, digital_elevation_model_basename, overwrite=overwrite)
    sampleRasterUnderPoints(flooded_areas_points_basename, digital_elevation_model_basename, ALTI_FIELD, overwrite=overwrite)
    exportVectorOgr2Grass(flooded_areas_points_basename, altitude_points, format_vector=FORMAT_VECTOR_GRASS, overwrite=overwrite)

    print(cyan + "classesOfWaterHeights() : " + bold + green + "ETAPE 2/6 - Fin de la récupération de l'altitude sous chaque point." + endC + '\n')

    #############
    # Etape 3/6 # Triangulation de l'altitude
    #############

    print(cyan + "classesOfWaterHeights() : " + bold + green + "ETAPE 3/6 - Début de la triangulation de l'altitude." + endC + '\n')

    pixel_size = abs(min(pixel_width, pixel_height))
    triangulationDelaunay(altitude_points, altitude_grid, ALTI_FIELD, cellsize=pixel_size)

    print(cyan + "classesOfWaterHeights() : " + bold + green + "ETAPE 3/6 - Fin de la triangulation de l'altitude." + endC + '\n')

    #############
    # Etape 4/6 # Calcul des hauteurs brutes
    #############

    print(cyan + "classesOfWaterHeights() : " + bold + green + "ETAPE 4/6 - Début du calcul des hauteurs brutes." + endC + '\n')

    # Redécoupage sur l'emprise inondée
    cutRasterImages([altitude_grid, input_digital_elevation_model_file], input_flooded_areas_vector, [altitude_file, digital_elevation_model_cut], 0, 0, epsg, no_data_value, "", False, path_time_log, format_raster=format_raster, format_vector=format_vector, extension_raster=extension_raster, extension_vector=extension_vector, save_results_intermediate=save_results_intermediate, overwrite=overwrite)

    # BandMath pour les hauteurs brutes (triangulation - MNT)
    expression = "im1b1 - im2b1"
    rasterCalculator([altitude_file, digital_elevation_model_cut], raw_heights, expression, codage=ENCODING_RASTER_FLOAT)

    print(cyan + "classesOfWaterHeights() : " + bold + green + "ETAPE 4/6 - Fin du calcul des hauteurs brutes." + endC + '\n')

    #############
    # Etape 5/6 # Attribution des classes de hauteurs d'eau
    #############

    print(cyan + "classesOfWaterHeights() : " + bold + green + "ETAPE 5/6 - Début de l'attribution des classes de hauteurs d'eau." + endC + '\n')

    # Génération de l'expression
    expression = ""
    for i in range(thresholds_list_float_len-1):
        min_threshold = thresholds_list_float[i]
        max_threshold = thresholds_list_float[i+1]
        expression += "im1b1>=%s and im1b1<%s ? %s : " % (min_threshold, max_threshold, i+1)
    expression += "im1b1>=%s ? %s : 0" % (thresholds_list_float[thresholds_list_float_len-1], thresholds_list_float_len)

    # Calcul des classes de hauteurs d'eau
    rasterCalculator([raw_heights], heights_classes_temp, expression, codage=ENCODING_RASTER_UINT8)

    # Redécoupage propre des zones en dehors de l'emprise inondée
    cutImageByVector(input_flooded_areas_vector, heights_classes_temp, output_heights_classes_file, pixel_size_x=pixel_width, pixel_size_y=pixel_height, in_line=False, no_data_value=no_data_value, epsg=epsg, format_raster=format_raster, format_vector=format_vector)

    print(cyan + "classesOfWaterHeights() : " + bold + green + "ETAPE 5/6 - Fin de l'attribution des classes de hauteurs d'eau." + endC + '\n')

    #############
    # Etape 6/6 # Vectorisation des classes de hauteurs d'eau
    #############

    if output_heights_classes_vector != "":

        print(cyan + "classesOfWaterHeights() : " + bold + green + "ETAPE 6/6 - Début de la vectorisation des classes de hauteurs d'eau." + endC + '\n')

        name_column = 'class'
        umc_list = 0

        if VECTORISATION == 'GRASS':
            vectorizeGrassClassification(output_heights_classes_file, output_heights_classes_vector, name_column, [umc_list], False, True, True, input_flooded_areas_vector, True, path_time_log, expression="", format_vector=format_vector, extension_raster=extension_raster, extension_vector=extension_vector, save_results_intermediate=save_results_intermediate, overwrite=overwrite)
        else:
            vectorizeClassification(output_heights_classes_file, output_heights_classes_vector, name_column, [umc_list], 2000, False, True, True, True, True, True, input_flooded_areas_vector, True, False, False, [0], path_time_log, expression="", format_vector=format_vector, extension_raster=extension_raster, extension_vector=extension_vector, save_results_intermediate=save_results_intermediate, overwrite=overwrite)

        print(cyan + "classesOfWaterHeights() : " + bold + green + "ETAPE 6/6 - Fin de la vectorisation des classes de hauteurs d'eau." + endC + '\n')

    else:
        print(cyan + "classesOfWaterHeights() : " + bold + yellow + "ETAPE 6/6 - Pas de vectorisation des classes de hauteurs d'eau demandée." + endC + '\n')

    # Suppression des fichiers temporaires
    if not save_results_intermediate:
        if debug >= 3:
            print(cyan + "classesOfWaterHeights() : " + endC + "Suppression des fichiers temporaires." + endC + '\n')
        deleteDir(temp_directory)

    print(cyan + "classesOfWaterHeights() : " + bold + green + "FIN DES TRAITEMENTS" + endC + '\n')

    # Mise à jour du log
    ending_event = "classesOfWaterHeights() : Fin du traitement : "
    timeLine(path_time_log, ending_event)

    return

#############################################################################################################################
################################################## Mise en place du parser ##################################################
#############################################################################################################################

def main(gui=False):
    parser = argparse.ArgumentParser(prog = "Hauteur d'eau sur une zone inondée", description = "\
    Calcul de la hauteur d'eau sur une zone inondée, par croisement avec le MNT. \n\
    Exemple : python3 -m WaterHeight.py -infld /mnt/RAM_disk/emprise_inondee.shp \n\
                                        -indem /mnt/RAM_disk/MNT_RGE_ALTI_1m.tif \n\
                                        -outr /mnt/RAM_disk/WaterHeight.tif \n\
                                        -outv /mnt/RAM_disk/WaterHeight.shp")

    parser.add_argument('-infld', '--input_flooded_areas_vector', default="", type=str, required=True, help="Input flooded areas vector file.")
    parser.add_argument('-indem', '--input_digital_elevation_model_file', default="", type=str, required=True, help="Input Digital Elevation Model raster file.")
    parser.add_argument('-outr', '--output_heights_classes_file', default="", type=str, required=False, help="Output classes of water heights raster file")
    parser.add_argument('-outv', '--output_heights_classes_vector', default="", type=str, required=False, help="Output classes of water heights vector file")
    parser.add_argument('-hcla', '--heights_classes', default="0,0.5,1,1.5,2", type=str, required=False, help="Classes of water heights to generate. Default: '0,0.5,1,1.5,2'.")
    parser.add_argument('-epsg', '--epsg', default=2154, type=int, required=False, help="Projection of the output file. Default: 2154.")
    parser.add_argument('-ndv', '--no_data_value', default=0, type=int, required=False, help="Value of the NoData pixel. Default: 0.")
    parser.add_argument('-raf', '--format_raster', default="GTiff", type=str, required=False, help="Format of raster file. Default: 'GTiff'.")
    parser.add_argument('-vef', '--format_vector', default="ESRI Shapefile", type=str, required=False, help="Format of vector file. Default: 'ESRI Shapefile'.")
    parser.add_argument('-rae', '--extension_raster', default=".tif", type=str, required=False, help="Extension file for raster file. Default: '.tif'.")
    parser.add_argument('-vee', '--extension_vector', default=".shp", type=str, required=False, help="Extension file for vector file. Default: '.shp'.")
    parser.add_argument('-ggis', '--grass_gisbase', default=os.environ['GISBASE'], type=str, required=False, help="GRASS environment variable. Default: os.environ['GISBASE'].")
    parser.add_argument('-gdbn', '--grass_gisdb', default="GRASS_database", type=str, required=False, help="GRASS geodatabase name. Default: 'GRASS_database'.")
    parser.add_argument('-gloc', '--grass_location', default="LOCATION", type=str, required=False, help="GRASS 'location' parameter for geodatabase. Default: 'LOCATION'.")
    parser.add_argument('-gmap', '--grass_mapset', default="MAPSET", type=str, required=False, help="GRASS 'mapset' parameter for geodatabase. Default: 'MAPSET'.")
    parser.add_argument('-log', '--path_time_log', default="", type=str, required=False, help="Option: Name of log. Default, no log file.")
    parser.add_argument('-sav', '--save_results_intermediate', action='store_true', default=False, required=False, help="Option: Save intermediate result after the process. Default, False.")
    parser.add_argument('-now', '--overwrite', action='store_false', default=True, required=False, help="Option: Overwrite files with same names. Default, True.")
    parser.add_argument('-debug', '--debug', default=3, type=int, required=False, help="Option: Value of level debug trace. Default, 3.")
    args = displayIHM(gui, parser)

    # Récupération du fichier d'emprise inondée d'entrée
    if args.input_flooded_areas_vector != None:
        input_flooded_areas_vector = args.input_flooded_areas_vector
        if not os.path.isfile(input_flooded_areas_vector):
            raise NameError (cyan + "WaterHeight: " + bold + red  + "File %s not exists (input_flooded_areas_vector)." % input_flooded_areas_vector + endC)

    # Récupération du fichier MNT d'entrée
    if args.input_digital_elevation_model_file != None:
        input_digital_elevation_model_file = args.input_digital_elevation_model_file
        if not os.path.isfile(input_digital_elevation_model_file):
            raise NameError (cyan + "WaterHeight: " + bold + red  + "File %s not exists (input_digital_elevation_model_file)." % input_digital_elevation_model_file + endC)

    # Récupération du fichier raster de sortie
    if args.output_heights_classes_file != None:
        output_heights_classes_file = args.output_heights_classes_file

    # Récupération du fichier vecteur de sortie
    if args.output_heights_classes_vector != None:
        output_heights_classes_vector = args.output_heights_classes_vector

    # Récupération des classes de hauteurs d'eau à générer
    if args.heights_classes != None:
        heights_classes = args.heights_classes

    # Récupération des paramètres fichiers
    if args.epsg != None:
        epsg = args.epsg
    if args.no_data_value != None:
        no_data_value = args.no_data_value
    if args.format_raster != None:
        format_raster = args.format_raster
    if args.format_vector != None:
        format_vector = args.format_vector
    if args.extension_raster != None:
        extension_raster = args.extension_raster
    if args.extension_vector != None:
        extension_vector = args.extension_vector

    # Récupération des paramètres GRASS
    if args.grass_gisbase != None:
        grass_gisbase = args.grass_gisbase
    if args.grass_gisdb != None:
        grass_gisdb = args.grass_gisdb
    if args.grass_location != None:
        grass_location = args.grass_location
    if args.grass_mapset != None:
        grass_mapset = args.grass_mapset

    # Récupération des paramètres généraux
    if args.path_time_log != None:
        path_time_log = args.path_time_log
    if args.save_results_intermediate != None:
        save_results_intermediate = args.save_results_intermediate
    if args.overwrite != None:
        overwrite = args.overwrite
    if args.debug != None:
        global debug
        debug = args.debug

    if output_heights_classes_file == "" and output_heights_classes_vector == "":
        raise NameError (cyan + "WaterHeight: " + bold + red  + "No water heights classes output file(s)." + endC)

    if output_heights_classes_file != "" and os.path.isfile(output_heights_classes_file) and not overwrite:
        raise NameError (cyan + "WaterHeight: " + bold + red  + "File %s already exists, and overwrite is not activated." % output_heights_classes_file + endC)
    if output_heights_classes_vector != "" and os.path.isfile(output_heights_classes_vector) and not overwrite:
        raise NameError (cyan + "WaterHeight: " + bold + red  + "File %s already exists, and overwrite is not activated." % output_heights_classes_vector + endC)

    if debug >= 3:
        print('\n' + bold + green + "Hauteur d'eau sur une zone inondée - Variables dans le parser :" + endC)
        print(cyan + "    WaterHeight : " + endC + "input_flooded_areas_vector : " + str(input_flooded_areas_vector) + endC)
        print(cyan + "    WaterHeight : " + endC + "input_digital_elevation_model_file : " + str(input_digital_elevation_model_file) + endC)
        print(cyan + "    WaterHeight : " + endC + "output_heights_classes_file : " + str(output_heights_classes_file) + endC)
        print(cyan + "    WaterHeight : " + endC + "output_heights_classes_vector : " + str(output_heights_classes_vector) + endC)
        print(cyan + "    WaterHeight : " + endC + "heights_classes : " + str(heights_classes) + endC)
        print(cyan + "    WaterHeight : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "    WaterHeight : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "    WaterHeight : " + endC + "format_raster : " + str(format_raster) + endC)
        print(cyan + "    WaterHeight : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "    WaterHeight : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "    WaterHeight : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "    WaterHeight : " + endC + "grass_gisbase : " + str(grass_gisbase) + endC)
        print(cyan + "    WaterHeight : " + endC + "grass_gisdb : " + str(grass_gisdb) + endC)
        print(cyan + "    WaterHeight : " + endC + "grass_location : " + str(grass_location) + endC)
        print(cyan + "    WaterHeight : " + endC + "grass_mapset : " + str(grass_mapset) + endC)
        print(cyan + "    WaterHeight : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "    WaterHeight : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "    WaterHeight : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "    WaterHeight : " + endC + "debug : " + str(debug) + endC + '\n')

    # Création du dossier de sortie, s'il n'existe pas
    if output_heights_classes_file != "" and not os.path.isdir(os.path.dirname(output_heights_classes_file)):
        os.makedirs(os.path.dirname(output_heights_classes_file))
    if output_heights_classes_vector != "" and not os.path.isdir(os.path.dirname(output_heights_classes_vector)):
        os.makedirs(os.path.dirname(output_heights_classes_vector))

    # EXECUTION DE LA FONCTION
    classesOfWaterHeights(input_flooded_areas_vector, input_digital_elevation_model_file, output_heights_classes_file, output_heights_classes_vector, heights_classes, epsg, no_data_value, format_raster, format_vector, extension_raster, extension_vector, grass_gisbase, grass_gisdb, grass_location, grass_mapset, path_time_log, save_results_intermediate, overwrite)

if __name__ == '__main__':
    main(gui=False)

