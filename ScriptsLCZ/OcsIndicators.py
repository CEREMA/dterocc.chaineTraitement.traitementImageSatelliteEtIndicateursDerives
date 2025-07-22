#!/usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

"""
Nom de l'objet : OcsIndicators.py
Description :
------------
Objectif : générer des indicateurs LCZ liés à l'occupation du sol (taux de chaque classe)
Remarque : indicateurs LCZ supplémentaires, non compris à l'origine dans l'article de Stewart & Oke (2012)

-----------------
Outils utilisés :

------------------------------
Historique des modifications :
16/01/2017 : création (AdditionalIndicators)
12/04/2019 : renommage (AdditionalIndicators --> OcsIndicators)
30/09/2020 : internationalisation (usage avec/sans MNH, OCS vecteur/raster, avec/sans dinstinction végétation haute et basse)

-----------------------
A réfléchir / A faire :

"""

# Import des bibliothèques Python
from __future__ import print_function
import os, sys, argparse
from osgeo import ogr
from Lib_display import bold,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_file import cleanTempData, copyVectorFile, deleteDir, removeFile, removeVectorFile
from Lib_log import timeLine
from Lib_vector import addNewFieldVector, filterSelectDataVector, fusionVectors, getAttributeNameList, renameFieldsVector, updateFieldVector
from Lib_raster import identifyPixelValues, getNodataValueImage, reallocateClassRaster
from CrossingVectorRaster import statisticsVectorRaster

# Niveau de debug (variable globale)
debug = 3

########################################################################
# FONCTION occupationIndicator()                                       #
########################################################################
def occupationIndicator(input_grid, output_grid, class_label_dico_out, input_vector_classif, field_classif_name, input_soil_occupation, input_height_model, class_build_list, class_road_list, class_baresoil_list, class_water_list, class_vegetation_list, class_high_vegetation_list, class_low_vegetation_list, epsg=2154, no_data_value=0, format_raster='GTiff', format_vector='ESRI Shapefile', extension_raster='.tif', extension_vector='.shp', path_time_log='', save_results_intermediate=False, overwrite=True):
    """
    # ROLE :
    #     calcul d'indicateurs liés au taux d'occupation de chaque classe OCS
    #
    # ENTREES DE LA FONCTION :
    #     input_grid : fichier maillage en entrée (vecteur)
    #     output_grid : fichier maillage en sortie, avec les indicateurs (vecteur)
    #     class_label_dico_out : dictionaire de correspondance entre label de classes et valeur pour le fichier output_grid de sortie
    #     input_vector_classif : fichier OCS (classif) en entrée au format vecteur
    #     field_classif_name : nom du champ contenant l'information de classif dans le fichier vecteur input_vector_classif
    #     input_soil_occupation : fichier OCS en entrée au format raster le fichier vecteur input_vector_classif est utilisé ce parametre sert de fichier de reference par rasteriser le veteur
    #     input_height_model : fichier MNH en entrée (raster)
    #     class_build_list : liste des classes 'bâti' de l'OCS
    #     class_road_list : liste des classes 'minéral' de l'OCS
    #     class_baresoil_list : liste des classes 'sol nu' de l'OCS
    #     class_water_list : liste des classes 'eau' de l'OCS
    #     class_vegetation_list : liste des classes 'végétation' de l'OCS
    #     class_high_vegetation_list : liste des classes 'végétation haute' de l'OCS
    #     class_low_vegetation_list : liste des classes 'végétation basse' de l'OCS
    #     epsg : code epsg du système de projection. Par défaut : 2154
    #     no_data_value : valeur NoData des pixels des fichiers raster. Par défaut : 0
    #     format_raster : format des fichiers raster. Par défaut : 'GTiff'
    #     format_vector : format des fichiers vecteur. Par défaut : 'ESRI Shapefile'
    #     extension_raster : extension des fichiers raster. Par défaut : '.tif'
    #     extension_vector : extension des fichiers vecteur. Par défaut : '.shp'
    #     path_time_log : fichier log de sortie, par défaut vide
    #     save_results_intermediate : fichiers temporaires conservés, par défaut = False
    #     overwrite : écrase si un fichier existant a le même nom qu'un fichier de sortie, par défaut = True
    #
    # SORTIES DE LA FONCTION :
    #     N.A.
    """

    if debug >= 3:
        print('\n' + bold + green + "Calcul d'indicateurs du taux de classes OCS - Variables dans la fonction :" + endC)
        print(cyan + "    occupationIndicator() : " + endC + "input_grid : " + str(input_grid) + endC)
        print(cyan + "    occupationIndicator() : " + endC + "output_grid : " + str(output_grid) + endC)
        print(cyan + "    occupationIndicator() : " + endC + "class_label_dico_out : " + str(class_label_dico_out) + endC)
        print(cyan + "    occupationIndicator() : " + endC + "input_vector_classif : " + str(input_vector_classif) + endC)
        print(cyan + "    occupationIndicator() : " + endC + "field_classif_name : " + str(field_classif_name) + endC)
        print(cyan + "    occupationIndicator() : " + endC + "input_soil_occupation : " + str(input_soil_occupation) + endC)
        print(cyan + "    occupationIndicator() : " + endC + "input_height_model : " + str(input_height_model) + endC)
        print(cyan + "    occupationIndicator() : " + endC + "class_build_list : " + str(class_build_list) + endC)
        print(cyan + "    occupationIndicator() : " + endC + "class_road_list : " + str(class_road_list) + endC)
        print(cyan + "    occupationIndicator() : " + endC + "class_baresoil_list : " + str(class_baresoil_list) + endC)
        print(cyan + "    occupationIndicator() : " + endC + "class_water_list : " + str(class_water_list) + endC)
        print(cyan + "    occupationIndicator() : " + endC + "class_vegetation_list : " + str(class_vegetation_list) + endC)
        print(cyan + "    occupationIndicator() : " + endC + "class_high_vegetation_list : " + str(class_high_vegetation_list) + endC)
        print(cyan + "    occupationIndicator() : " + endC + "class_low_vegetation_list : " + str(class_low_vegetation_list) + endC)
        print(cyan + "    occupationIndicator() : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "    occupationIndicator() : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "    occupationIndicator() : " + endC + "format_raster : " + str(format_raster) + endC)
        print(cyan + "    occupationIndicator() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "    occupationIndicator() : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "    occupationIndicator() : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "    occupationIndicator() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "    occupationIndicator() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "    occupationIndicator() : " + endC + "overwrite : " + str(overwrite) + endC + '\n')

    # Définition des constantes
    CODAGE_8BITS = 'uint8'
    CODAGE_FLOAT = 'float'
    NODATA_FIELD = 'nodata'

    PREFIX_S = 'S_'
    SUFFIX_TEMP = '_temp'
    SUFFIX_RASTER = '_raster'
    SUFFIX_HEIGHT = '_height'
    SUFFIX_VEGETATION = '_vegetation'

    VEG_MEAN_FIELD = 'veg_h_mean'
    VEG_MAX_FIELD = 'veg_h_max'
    VEG_RATE_FIELD = 'veg_h_rate'
    MAJ_OCS_FIELD = 'class_OCS'

    BUILT_FIELD, BUILT_LABEL = 'built', 1
    MINERAL_FIELD, MINERAL_LABEL = 'mineral', 2
    BARESOIL_FIELD, BARESOIL_LABEL = 'baresoil', 3
    WATER_FIELD, WATER_LABEL = 'water', 4
    VEGETATION_FIELD, VEGETATION_LABEL = 'veget', 5
    HIGH_VEGETATION_FIELD, HIGH_VEGETATION_LABEL = 'high_veg', 6
    LOW_VEGETATION_FIELD, LOW_VEGETATION_LABEL = 'low_veg', 7

    # Mise à jour du log
    starting_event = "occupationIndicator() : Début du traitement : "
    timeLine(path_time_log, starting_event)

    print(cyan + "occupationIndicator() : " + bold + green + "DEBUT DES TRAITEMENTS" + endC + '\n')

    # Définition des variables 'basename'
    output_grid_basename = os.path.basename(os.path.splitext(output_grid)[0])
    output_grid_dirname = os.path.dirname(output_grid)
    soil_occupation_basename = os.path.basename(os.path.splitext(input_soil_occupation)[0])

    # Définition des variables temp
    temp_directory = output_grid_dirname + os.sep + output_grid_basename
    temp_grid = temp_directory + os.sep + output_grid_basename + SUFFIX_TEMP + extension_vector
    temp_soil_occupation = temp_directory + os.sep + soil_occupation_basename + SUFFIX_TEMP + SUFFIX_RASTER + extension_raster
    temp_height_vegetation = temp_directory + os.sep + output_grid_basename + SUFFIX_HEIGHT + SUFFIX_VEGETATION + extension_raster

    # Nettoyage des traitements précédents
    if overwrite:
        if debug >= 3:
            print(cyan + "occupationIndicator() : " + endC + "Nettoyage des traitements précédents." + endC + '\n')
        removeFile(output_grid)
        cleanTempData(temp_directory)
    else:
        if os.path.exists(output_grid):
            raise NameError (cyan + "occupationIndicator() : " + bold + yellow + "Le fichier de sortie existe déjà et ne sera pas regénéré." + endC + '\n')
        pass

    #############
    # Etape 0/3 # Préparation des traitements
    #############

    print(cyan + "occupationIndicator() : " + bold + green + "ETAPE 0/3 - Début de la préparation des traitements." + endC + '\n')

    # Rasterisation de l'information de classification (OCS) si au format vecteur en entrée
    if input_vector_classif != "":
        if debug >= 3:
            print(cyan + "occupationIndicator() : " + endC + bold + "Rasterisation de l'OCS vecteur." + endC + '\n')
        reference_image = input_soil_occupation
        soil_occupation_vector_basename = os.path.basename(os.path.splitext(input_vector_classif)[0])
        input_soil_occupation =  temp_directory + os.sep + soil_occupation_vector_basename + SUFFIX_RASTER + extension_raster
        command = "otbcli_Rasterization -in %s -out %s %s -im %s -background 0 -mode attribute -mode.attribute.field %s" % (input_vector_classif, input_soil_occupation, CODAGE_8BITS, reference_image, field_classif_name)
        if debug >= 3:
            print(command)
        exit_code = os.system(command)
        if exit_code != 0:
            raise NameError (cyan + "occupationIndicator() : " + bold + red + "Erreur lors de la rasterisation de l'OCS vecteur." + endC)

    # Analyse de la couche OCS raster
    class_other_list = identifyPixelValues(input_soil_occupation)
    no_data_ocs = getNodataValueImage(input_soil_occupation, 1)
    if no_data_ocs != None :
        no_data_value = no_data_ocs

    # Affectation de nouveaux codes de classification
    divide_vegetation_classes = False
    if class_high_vegetation_list != [] and class_low_vegetation_list != []:
        divide_vegetation_classes = True

    col_to_delete_list = ["minority", 'count', PREFIX_S + NODATA_FIELD, PREFIX_S + BUILT_FIELD, PREFIX_S + MINERAL_FIELD, PREFIX_S + BARESOIL_FIELD, PREFIX_S + WATER_FIELD]
    if input_height_model == "":
        col_to_delete_list.append('majority')
    class_label_dico = {int(no_data_value):NODATA_FIELD, int(BUILT_LABEL):BUILT_FIELD, int(MINERAL_LABEL):MINERAL_FIELD, int(BARESOIL_LABEL):BARESOIL_FIELD, int(WATER_LABEL):WATER_FIELD}
    if not divide_vegetation_classes:
        class_label_dico[int(VEGETATION_LABEL)] = VEGETATION_FIELD
        col_to_delete_list.append(PREFIX_S + VEGETATION_FIELD)
    else:
        class_label_dico[int(HIGH_VEGETATION_LABEL)] = HIGH_VEGETATION_FIELD
        class_label_dico[int(LOW_VEGETATION_LABEL)] = LOW_VEGETATION_FIELD
        col_to_delete_list.append(PREFIX_S + HIGH_VEGETATION_FIELD)
        col_to_delete_list.append(PREFIX_S + LOW_VEGETATION_FIELD)

    # Gestion de la réaffectation des classes
    if debug >= 3:
        print(cyan + "occupationIndicator() : " + endC + bold + "Reaffectation du raster OCS." + endC + '\n')

    reaff_class_list = []
    macro_reaff_class_list = []

    for label in class_build_list:
        if label in class_other_list :
            class_other_list.remove(label)
        reaff_class_list.append(label)
        macro_reaff_class_list.append(BUILT_LABEL)

    for label in class_road_list:
        if label in class_other_list :
            class_other_list.remove(label)
        reaff_class_list.append(label)
        macro_reaff_class_list.append(MINERAL_LABEL)

    for label in class_baresoil_list:
        if label in class_other_list :
            class_other_list.remove(label)
        reaff_class_list.append(label)
        macro_reaff_class_list.append(BARESOIL_LABEL)

    for label in class_water_list:
        if label in class_other_list :
            class_other_list.remove(label)
        reaff_class_list.append(label)
        macro_reaff_class_list.append(WATER_LABEL)

    if not divide_vegetation_classes:
        for label in class_vegetation_list:
            if label in class_other_list :
                class_other_list.remove(label)
            reaff_class_list.append(label)
            macro_reaff_class_list.append(VEGETATION_LABEL)
    else:
        for label in class_high_vegetation_list:
            if label in class_other_list :
                class_other_list.remove(label)
            reaff_class_list.append(label)
            macro_reaff_class_list.append(HIGH_VEGETATION_LABEL)
        for label in class_low_vegetation_list:
            if label in class_other_list :
                class_other_list.remove(label)
            reaff_class_list.append(label)
            macro_reaff_class_list.append(LOW_VEGETATION_LABEL)

    # Reste des valeurs de pixel nom utilisé
    for label in class_other_list:
        reaff_class_list.append(label)
        macro_reaff_class_list.append(no_data_value)

    reallocateClassRaster(input_soil_occupation, temp_soil_occupation, reaff_class_list, macro_reaff_class_list, CODAGE_8BITS)

    print(cyan + "occupationIndicator() : " + bold + green + "ETAPE 0/3 - Fin de la préparation des traitements." + endC + '\n')

    #############
    # Etape 1/3 # Calcul des indicateurs de taux de classes OCS
    #############

    print(cyan + "occupationIndicator() : " + bold + green + "ETAPE 1/3 - Début du calcul des indicateurs de taux de classes OCS." + endC + '\n')

    if debug >= 3:
        print(cyan + "occupationIndicator() : " + endC + bold + "Calcul des indicateurs de taux de classes OCS." + endC + '\n')

    statisticsVectorRaster(temp_soil_occupation, input_grid, temp_grid, 1, True, True, False, col_to_delete_list, [], class_label_dico, True, no_data_value, format_vector, path_time_log, save_results_intermediate, overwrite)

    # Fusion des classes végétation dans le cas où haute et basse sont séparées (pour utilisation du taux de végétation dans le logigramme)
    if divide_vegetation_classes:
        temp_grid_v2 = os.path.splitext(temp_grid)[0] + "_v2" + extension_vector
        sql_statement = "SELECT *, (%s + %s) AS %s FROM %s" % (HIGH_VEGETATION_FIELD, LOW_VEGETATION_FIELD, VEGETATION_FIELD, os.path.splitext(os.path.basename(temp_grid))[0])
        os.system("ogr2ogr -sql '%s' -dialect SQLITE %s %s" % (sql_statement, temp_grid_v2, temp_grid))
        removeVectorFile(temp_grid, format_vector=format_vector)
        copyVectorFile(temp_grid_v2, temp_grid, format_vector=format_vector)

    print(cyan + "occupationIndicator() : " + bold + green + "ETAPE 1/3 - Fin du calcul des indicateurs de taux de classes OCS." + endC + '\n')

    #############
    # Etape 2/3 # Calcul de l'indicateur de "hauteur de végétation"
    #############

    print(cyan + "occupationIndicator() : " + bold + green + "ETAPE 2/3 - Début du calcul de l'indicateur de \"hauteur de végétation\"." + endC + '\n')

    if input_height_model != "" or divide_vegetation_classes:
        computeVegetationHeight(temp_grid, output_grid, temp_soil_occupation, input_height_model, temp_height_vegetation, divide_vegetation_classes, VEGETATION_LABEL, HIGH_VEGETATION_LABEL, LOW_VEGETATION_LABEL, HIGH_VEGETATION_FIELD, LOW_VEGETATION_FIELD, VEG_MEAN_FIELD, VEG_MAX_FIELD, VEG_RATE_FIELD, CODAGE_FLOAT, SUFFIX_TEMP, no_data_value, format_vector, path_time_log, save_results_intermediate, overwrite)
    else:
        print(cyan + "occupationIndicator() : " + bold + yellow + "Pas de calcul de l'indicateur de \"hauteur de végétation\"." + endC + '\n')
        copyVectorFile(temp_grid, output_grid, format_vector=format_vector)

    print(cyan + "occupationIndicator() : " + bold + green + "ETAPE 2/3 - Fin du calcul de l'indicateur de \"hauteur de végétation\"." + endC + '\n')

    #############
    # Etape 3/3 # Calcul de l'indicateur de classe majoritaire
    #############

    print(cyan + "occupationIndicator() : " + bold + green + "ETAPE 3/3 - Début du calcul de l'indicateur de classe majoritaire." + endC + '\n')

    if input_height_model != "":
        computeMajorityClass(output_grid, temp_directory, NODATA_FIELD, BUILT_FIELD, MINERAL_FIELD, BARESOIL_FIELD, WATER_FIELD, VEGETATION_FIELD, HIGH_VEGETATION_FIELD, LOW_VEGETATION_FIELD, MAJ_OCS_FIELD, VEG_MEAN_FIELD, class_label_dico_out, format_vector, extension_vector, overwrite)
    else:
        print(cyan + "occupationIndicator() : " + bold + yellow + "Pas de calcul de l'indicateur de classe majoritaire demandé (pas de MNH en entrée)." + endC + '\n')

    print(cyan + "occupationIndicator() : " + bold + green + "ETAPE 3/3 - Fin du calcul de l'indicateur de classe majoritaire." + endC + '\n')

    ####################################################################

    # Suppression des fichiers temporaires
    if not save_results_intermediate:
        if debug >= 3:
            print(cyan + "occupationIndicator() : " + endC + "Suppression des fichiers temporaires." + endC + '\n')
        deleteDir(temp_directory)

    print(cyan + "occupationIndicator() : " + bold + green + "FIN DES TRAITEMENTS" + endC + '\n')

    # Mise à jour du log
    ending_event = "occupationIndicator() : Fin du traitement : "
    timeLine(path_time_log, ending_event)

    return 0

########################################################################
# FONCTION computeVegetationHeight()                                   #
########################################################################

def computeVegetationHeight(input_grid, output_grid, soil_occupation, height_model, height_vegetation, divide_vegetation_classes, vegetation_label, high_vegetation_label, low_vegetation_label, high_vegetation_field, low_vegetation_field, veg_mean_field, veg_max_field, veg_rate_field, codage_float, suffix_temp, no_data_value, format_vector, path_time_log, save_results_intermediate, overwrite):

    PRECISION = 0.0000001

    temp_grid = os.path.splitext(input_grid)[0] + suffix_temp + os.path.splitext(input_grid)[1]

    if height_model != "":

        ### Récupération de la hauteur de végétation

        if debug >= 3:
            print(cyan + "computeVegetationHeight() : " + endC + bold + "Récupération de la hauteur de végétation." + endC + '\n')

        if not divide_vegetation_classes:
            expression = "im1b1 == %s ? im2b1 : %s" % (vegetation_label, no_data_value)
        else:
            expression = "im1b1 == %s or im1b1 == %s ? im2b1 : %s" % (high_vegetation_label, low_vegetation_label, no_data_value)

        command = "otbcli_BandMath -il %s %s -out %s %s -exp '%s'" % (soil_occupation, height_model, height_vegetation, codage_float, expression)
        if debug >= 3:
            print(command)
        exit_code = os.system(command)
        if exit_code != 0:
            raise NameError (cyan + "computeVegetationHeight() : " + bold + red + "Erreur lors de la récupération de la hauteur de végétation." + endC)

        ### Récupération de la hauteur moyenne de végétation

        if debug >= 3:
            print(cyan + "computeVegetationHeight() : " + endC + bold + "Récupération de la hauteur moyenne de végétation." + endC + '\n')

        col_to_delete_list = ["min", "median", "sum", "std", "unique", "range"]
        statisticsVectorRaster(height_vegetation, input_grid, temp_grid, 1, False, False, True, col_to_delete_list, [], {}, True, no_data_value, format_vector, path_time_log, save_results_intermediate, overwrite)

        renameFieldsVector(temp_grid, ['mean'], [veg_mean_field], format_vector=format_vector)
        renameFieldsVector(temp_grid, ['max'], [veg_max_field], format_vector=format_vector)

    else:
        print(cyan + "computeVegetationHeight() : " + bold + yellow + "Pas de calcul de l'indicateur 'hauteur moyenne de végétation' (pas de MNH en entrée)." + endC + '\n')
        copyVectorFile(input_grid, temp_grid, format_vector=format_vector)

    if divide_vegetation_classes:

        ### Récupération du taux de végétation haute

        if debug >= 3:
            print(cyan + "computeVegetationHeight() : " + endC + bold + "Récupération du taux de végétation haute." + endC + '\n')

        sql_statement = "SELECT *, ((%s/(%s+%s+%s))*100) AS %s FROM %s" % (high_vegetation_field, high_vegetation_field, low_vegetation_field, PRECISION, veg_rate_field, os.path.splitext(os.path.basename(temp_grid))[0])

        command = "ogr2ogr -sql '%s' -dialect SQLITE %s %s" % (sql_statement, output_grid, temp_grid)
        if debug >= 3:
            print(command)
        exit_code = os.system(command)
        if exit_code != 0:
            raise NameError (cyan + "computeVegetationHeight() : " + bold + red + "Erreur lors de la récupération du taux de végétation haute." + endC)

    else:
        print(cyan + "computeVegetationHeight() : " + bold + yellow + "Pas de calcul de l'indicateur 'taux de végétation haute' (pas de distinction végétation haute/basse dans l'OCS)." + endC + '\n')
        copyVectorFile(temp_grid, output_grid, format_vector=format_vector)

    return 0

########################################################################
# FONCTION computeMajorityClass()                                      #
########################################################################

def computeMajorityClass(input_grid, temp_directory, nodata_field, built_field, mineral_field, baresoil_field, water_field, vegetation_field, high_vegetation_field, low_vegetation_field, maj_ocs_field, veg_mean_field, class_label_dico_out, format_vector, extension_vector, overwrite):

    SUFFIX_CLASS = '_class'
    FIELD_TYPE = ogr.OFTInteger
    FIELD_NAME_MAJORITY = 'majority'

    temp_class_list = []

    base_name = os.path.splitext(os.path.basename(input_grid))[0]
    temp_grid = temp_directory + os.sep + base_name + SUFFIX_CLASS + extension_vector
    temp_class0 = temp_directory + os.sep + base_name + SUFFIX_CLASS +  "0" + extension_vector
    temp_class1 = temp_directory + os.sep + base_name + SUFFIX_CLASS +  "1" + extension_vector
    temp_class2 = temp_directory + os.sep + base_name + SUFFIX_CLASS +  "2" + extension_vector
    temp_class3 = temp_directory + os.sep + base_name + SUFFIX_CLASS +  "3" + extension_vector
    temp_class4 = temp_directory + os.sep + base_name + SUFFIX_CLASS +  "4" + extension_vector

    ### Récupération de la classe majoritaire

    if debug >= 3:
        print(cyan + "computeMajorityClass() : " + endC + bold + "Récupération de la classe majoritaire." + endC + '\n')

    addNewFieldVector(input_grid, maj_ocs_field, FIELD_TYPE, field_value=None, field_width=None, field_precision=None, format_vector=format_vector)
    attr_names_list = getAttributeNameList(input_grid, format_vector=format_vector)
    attr_names_list_str = "'"
    for attr_name in attr_names_list:
        attr_names_list_str += attr_name + ', '
    attr_names_list_str = attr_names_list_str[:-2] + "'"

    expression = "%s = '%s' OR %s = '%s' OR %s = '%s' OR %s = '%s'" % (FIELD_NAME_MAJORITY, nodata_field, FIELD_NAME_MAJORITY, built_field, FIELD_NAME_MAJORITY, mineral_field, FIELD_NAME_MAJORITY, water_field)
    ret = filterSelectDataVector (input_grid, temp_class0, attr_names_list_str, expression, overwrite=overwrite, format_vector=format_vector)
    updateFieldVector(temp_class0, field_name=maj_ocs_field, value=class_label_dico_out["MAJ_OTHERS_CLASS"], format_vector=format_vector)
    temp_class_list.append(temp_class0)

    expression = "%s = '%s'" % (FIELD_NAME_MAJORITY, baresoil_field)
    ret = filterSelectDataVector (input_grid, temp_class1, attr_names_list_str, expression, overwrite=overwrite, format_vector=format_vector)
    updateFieldVector(temp_class1, field_name=maj_ocs_field, value=class_label_dico_out["MAJ_BARESOIL_CLASS"], format_vector=format_vector)
    temp_class_list.append(temp_class1)

    expression = "(%s = '%s' OR %s = '%s' OR %s = '%s') AND (%s < 1)" % (FIELD_NAME_MAJORITY, vegetation_field, FIELD_NAME_MAJORITY, low_vegetation_field, FIELD_NAME_MAJORITY, high_vegetation_field, veg_mean_field)
    ret = filterSelectDataVector (input_grid, temp_class2, attr_names_list_str, expression, overwrite=overwrite, format_vector=format_vector)
    updateFieldVector(temp_class2, field_name=maj_ocs_field, value=class_label_dico_out["MAJ_LOW_VEG_CLASS"], format_vector=format_vector)
    temp_class_list.append(temp_class2)

    expression = "(%s = '%s' OR %s = '%s' OR %s = '%s') AND (%s >= 1 AND %s < 5)" % (FIELD_NAME_MAJORITY, vegetation_field, FIELD_NAME_MAJORITY, low_vegetation_field, FIELD_NAME_MAJORITY, high_vegetation_field, veg_mean_field, veg_mean_field)
    ret = filterSelectDataVector (input_grid, temp_class3, attr_names_list_str, expression, overwrite=overwrite, format_vector=format_vector)
    updateFieldVector(temp_class3, field_name=maj_ocs_field, value=class_label_dico_out["MAJ_MED_VEG_CLASS"], format_vector=format_vector)
    temp_class_list.append(temp_class3)

    expression = "(%s = '%s' OR %s = '%s' OR %s = '%s') AND (%s >= 5)" % (FIELD_NAME_MAJORITY, vegetation_field, FIELD_NAME_MAJORITY, low_vegetation_field, FIELD_NAME_MAJORITY, high_vegetation_field, veg_mean_field)
    ret = filterSelectDataVector (input_grid, temp_class4, attr_names_list_str, expression, overwrite=overwrite, format_vector=format_vector)
    updateFieldVector(temp_class4, field_name=maj_ocs_field, value=class_label_dico_out["MAJ_HIGH_VEG_CLASS"], format_vector=format_vector)
    temp_class_list.append(temp_class4)

    fusionVectors(temp_class_list, temp_grid, format_vector=format_vector)
    removeVectorFile(input_grid, format_vector=format_vector)
    copyVectorFile(temp_grid, input_grid, format_vector=format_vector)

    return 0

#############################################################################################################################
################################################## Mise en place du parser ##################################################
#############################################################################################################################

def main(gui=False):
    parser = argparse.ArgumentParser(prog = "Indicateurs LCZ liés à l'OCS", description = "\
    Calcul d'indicateurs liés au taux d'occupation de classes OCS, et de \"hauteur de végétation\" avec ou sans MNH, pour une utilisation des LCZ à l'international. \n\
    Remarque : différents cas possibles, si on rentre avec OCS vecteur ou raster, si on a ou non le MNH, si on distingue végétation haute/basse dans l'OCS. \n\
    Exemple (entrée OCS raster, sans MNH, en distinguant végétation haute/basse) : \n\
        python3 -m OcsIndicators \n\
                -in /mnt/Data/20_Etudes_Encours/URBAIN/Production/Lille/Climatologie/SatLCZ_Airbus/10_PROCESSED_DATA/maillage_etude.shp \n\
                -out /mnt/Data/20_Etudes_Encours/URBAIN/Production/Lille/Climatologie/SatLCZ_Airbus/20_LCZ_INDICATORS/OcsIndicators.shp \n\
                -ocs /mnt/Data/20_Etudes_Encours/URBAIN/Production/Lille/Climatologie/SatLCZ_Airbus/10_PROCESSED_DATA/Airbus_Lille_landcover.tif \n\
                -cbl 2 -crl 5 6 8 12 13 -csl 1 7 9 -cwl 10 11 -chvl 3 -clvl 4")

    parser.add_argument('-in', '--input_grid', default="", type=str, required=True, help="Input grid file (vector).")
    parser.add_argument('-out', '--output_grid', default="", type=str, required=True, help="Output grid file, with indicators (vector).")
    parser.add_argument("-clo", "--class_label_dico_out",nargs="+",default=["MAJ_OTHERS_CLASS:0", "MAJ_BARESOIL_CLASS:1",  "MAJ_LOW_VEG_CLASS:2", "MAJ_MED_VEG_CLASS:3", "MAJ_HIGH_VEG_CLASS:4"], help = "Dictionary contain class value in output. Default : MAJ_OTHERS_CLASS:0 MAJ_BARESOIL_CLASS:1 MAJ_LOW_VEG_CLASS:2 MAJ_MED_VEG_CLASS:3 MAJ_HIGH_VEG_CLASS:4", type=str,required=False)
    parser.add_argument('-cla', '--input_vector_classif', default="", type=str, required=False, help="Input modele classification OCS (vector).")
    parser.add_argument('-fcn', '--field_classif_name', default="OCS", type=str, required=False, help="The field contain classification information.")
    parser.add_argument('-ocs', '--input_soil_occupation', default="", type=str, required=True, help="Input soil occupation file (raster) or if vector input_vector_classif define this is the reference image.")
    parser.add_argument('-mnh', '--input_height_model', default="", type=str, required=False, help="Input height model file (raster).")
    parser.add_argument('-cbl', '--class_build_list', nargs="+", default=[11100], type=int, required=False, help="List of built class labels from the soil occupation classification.")
    parser.add_argument('-crl', '--class_road_list', nargs="+", default=[11200], type=int, required=False, help="List of road (mineral) class labels from the soil occupation classification.")
    parser.add_argument('-csl', '--class_baresoil_list', nargs="+", default=[13000], type=int, required=False, help="List of baresoil class labels from the soil occupation classification.")
    parser.add_argument('-cwl', '--class_water_list', nargs="+", default=[12200], type=int, required=False, help="List of water class labels from the soil occupation classification.")
    parser.add_argument('-cvl', '--class_vegetation_list', nargs="+", default=[20000], type=int, required=False, help="List of vegetation class labels from the soil occupation classification. Not required if 'class_high_vegetation_list' and 'class_low_vegetation_list' are filled.")
    parser.add_argument('-chvl', '--class_high_vegetation_list', nargs="+", default=[], type=int, required=False, help="List of high vegetation class labels from the soil occupation classification. Required if not input height model.")
    parser.add_argument('-clvl', '--class_low_vegetation_list', nargs="+", default=[], type=int, required=False, help="List of low vegetation class labels from the soil occupation classification. Required if not input height model.")
    parser.add_argument('-epsg', '--epsg', default=2154, type=int, required=False, help="Projection of the output file. Default: 2154.")
    parser.add_argument('-ndv', '--no_data_value', default=0, type=int, required=False, help="Value of the NoData pixel. Default: 0.")
    parser.add_argument('-raf', '--format_raster', default="GTiff", type=str, required=False, help="Format of raster file. Default: 'GTiff'.")
    parser.add_argument('-vef', '--format_vector', default="ESRI Shapefile", type=str, required=False, help="Format of vector file. Default: 'ESRI Shapefile'.")
    parser.add_argument('-rae', '--extension_raster', default=".tif", type=str, required=False, help="Extension file for raster file. Default: '.tif'.")
    parser.add_argument('-vee', '--extension_vector', default=".shp", type=str, required=False, help="Extension file for vector file. Default: '.shp'.")
    parser.add_argument('-log', '--path_time_log', default="", type=str, required=False, help="Option: Name of log. Default, no log file.")
    parser.add_argument('-sav', '--save_results_intermediate', action='store_true', default=False, required=False, help="Option: Save intermediate result after the process. Default, False.")
    parser.add_argument('-now', '--overwrite', action='store_false', default=True, required=False, help="Option: Overwrite files with same names. Default, True.")
    parser.add_argument('-debug', '--debug', default=3, type=int, required=False, help="Option: Value of level debug trace. Default, 3.")
    args = displayIHM(gui, parser)

    # Récupération du fichier maillage d'entrée
    if args.input_grid != None:
        input_grid = args.input_grid
        if not os.path.isfile(input_grid):
            raise NameError (cyan + "OcsIndicators: " + bold + red  + "File %s not exists (input_grid)." % input_grid + endC)

    # Récupération du fichier maillage de sortie
    if args.output_grid != None:
        output_grid = args.output_grid

    # Creation du dictionaire de sortie reliant les labels de classes à leur valeur
    class_label_dico_out = {}
    if args.class_label_dico_out != None and args.class_label_dico_out != "":
        for tmp_txt_class in args.class_label_dico_out:
            class_label_list = tmp_txt_class.split(':')
            class_label_dico_out[str(class_label_list[0])] = int(class_label_list[1])

    # Récupération du fichier OCS vecteur d'entrée
    if args.input_vector_classif != None:
        input_vector_classif = args.input_vector_classif
        if not input_vector_classif == "" and not os.path.isfile(input_vector_classif):
            raise NameError (cyan + "OcsIndicators: " + bold + red  + "File %s not exists (input_vector_classif)." % input_vector_classif + endC)

    # Récupération du nom du champs contenant la classif fichier OCS vecteur
    if args.field_classif_name != None:
        field_classif_name = args.field_classif_name

    # Récupération du fichier OCS raster d'entrée
    if args.input_soil_occupation != None:
        input_soil_occupation = args.input_soil_occupation
        if not os.path.isfile(input_soil_occupation):
            raise NameError (cyan + "OcsIndicators: " + bold + red  + "File %s not exists (input_soil_occupation_file or reference_image)." % input_soil_occupation + endC)

    # Récupération du fichier MNH d'entrée
    if args.input_height_model != None:
        input_height_model = args.input_height_model
        if not input_height_model == "" and not os.path.isfile(input_height_model):
            raise NameError (cyan + "OcsIndicators: " + bold + red  + "File %s not exists (input_height_model)." % input_height_model + endC)

    # Récupération des paramètres de classes OCS
    if args.class_build_list != None:
        class_build_list = args.class_build_list
    if args.class_road_list != None:
        class_road_list = args.class_road_list
    if args.class_baresoil_list != None:
        class_baresoil_list = args.class_baresoil_list
    if args.class_water_list != None:
        class_water_list = args.class_water_list
    if args.class_vegetation_list != None:
        class_vegetation_list = args.class_vegetation_list
    if args.class_high_vegetation_list != None:
        class_high_vegetation_list = args.class_high_vegetation_list
    if args.class_low_vegetation_list != None:
        class_low_vegetation_list = args.class_low_vegetation_list

    # Récupération du code EPSG de la projection du shapefile trait de côte
    if args.epsg != None :
        epsg = args.epsg

    # Paramettre des no data
    if args.no_data_value != None:
        no_data_value = args.no_data_value

    # Paramètre format des images de sortie
    if args.format_raster != None:
        format_raster = args.format_raster

    # Récupération du format du fichier de sortie
    if args.format_vector != None :
        format_vector = args.format_vector

    # Paramètre de l'extension des images rasters
    if args.extension_raster != None:
        extension_raster = args.extension_raster

    # Récupération de l'extension des fichiers vecteurs
    if args.extension_vector != None:
        extension_vector = args.extension_vector

    # Récupération du nom du fichier log
    if args.path_time_log!= None:
        path_time_log = args.path_time_log

    # Récupération de l'option de sauvegarde des fichiers intermédiaires
    if args.save_results_intermediate != None:
        save_results_intermediate = args.save_results_intermediate

    # Récupération de l'option écrasement
    if args.overwrite!= None:
        overwrite = args.overwrite

    # Protection du fichier de soertie si il existe deja
    if os.path.isfile(output_grid) and not overwrite:
        raise NameError (cyan + "OcsIndicators: " + bold + red  + "File %s already exists, and overwrite is not activated." % output_grid + endC)

    if debug >= 3:
        print('\n' + bold + green + "Calcul d'indicateurs LCZ liés à l'OCS - Variables dans le parser :" + endC)
        print(cyan + "OcsIndicators : " + endC + "input_grid : " + str(input_grid) + endC)
        print(cyan + "OcsIndicators : " + endC + "output_grid : " + str(output_grid) + endC)
        print(cyan + "OcsIndicators : " + endC + "class_label_dico_out : " + str(class_label_dico_out) + endC)
        print(cyan + "OcsIndicators : " + endC + "input_vector_classif : " + str(input_vector_classif) + endC)
        print(cyan + "OcsIndicators : " + endC + "field_classif_name : " + str(field_classif_name) + endC)
        print(cyan + "OcsIndicators : " + endC + "input_soil_occupation : " + str(input_soil_occupation) + endC)
        print(cyan + "OcsIndicators : " + endC + "input_height_model : " + str(input_height_model) + endC)
        print(cyan + "OcsIndicators : " + endC + "class_build_list : " + str(class_build_list) + endC)
        print(cyan + "OcsIndicators : " + endC + "class_road_list : " + str(class_road_list) + endC)
        print(cyan + "OcsIndicators : " + endC + "class_baresoil_list : " + str(class_baresoil_list) + endC)
        print(cyan + "OcsIndicators : " + endC + "class_water_list : " + str(class_water_list) + endC)
        print(cyan + "OcsIndicators : " + endC + "class_vegetation_list : " + str(class_vegetation_list) + endC)
        print(cyan + "OcsIndicators : " + endC + "class_high_vegetation_list : " + str(class_high_vegetation_list) + endC)
        print(cyan + "OcsIndicators : " + endC + "class_low_vegetation_list : " + str(class_low_vegetation_list) + endC)
        print(cyan + "OcsIndicators : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "OcsIndicators : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "OcsIndicators : " + endC + "format_raster : " + str(format_raster) + endC)
        print(cyan + "OcsIndicators : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "OcsIndicators : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "OcsIndicators : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "OcsIndicators : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "OcsIndicators : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "OcsIndicators : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "OcsIndicators : " + endC + "debug : " + str(debug) + endC + '\n')

    # Création du dossier de sortie, s'il n'existe pas
    if not os.path.isdir(os.path.dirname(output_grid)):
        os.makedirs(os.path.dirname(output_grid))

    # EXECUTION DES FONCTIONS
    occupationIndicator(input_grid, output_grid, class_label_dico_out, input_vector_classif, field_classif_name, input_soil_occupation, input_height_model, class_build_list, class_road_list, class_baresoil_list, class_water_list, class_vegetation_list, class_high_vegetation_list, class_low_vegetation_list, epsg, no_data_value, format_raster, format_vector, extension_raster, extension_vector, path_time_log, save_results_intermediate, overwrite)

if __name__ == '__main__':
    main(gui=False)

