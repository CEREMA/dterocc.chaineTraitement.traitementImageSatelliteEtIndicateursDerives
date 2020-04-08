#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerSO/DALETT/SCGSI  All rights reserved.                                                                            #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT FAIT UNE SELECTIONNE DES POINTS D'ECHANTILLONS D'APPRENTISSAGE DIRECTEMENT DANS LES FICHIERS MASK MACRO D'APPRENTISSAGE            #
#                                                                                                                                           #
#############################################################################################################################################
'''
Nom de l'objet : selectSamples.py
Description :
    Objectif : Selectionner des points d'echantillons d'apprentissage par tirage aléatoire, pour la classification dans les fichiers masques macro d'apprentissage
    ceux-ci sont d'abord fusionnés.
    Rq : utilisation des OTB Applications :  otbcli_BandMath, otbcli_SampleExtraction

Date de creation : 16/03/2017
----------
Histoire :
----------
Origine : Nouveau
16/03/2017 : Création
-----------------------------------------------------------------------------------------------------
Modifications

------------------------------------------------------
A Reflechir/A faire
 -
 -
'''

# Import des bibliothèques python
from __future__ import print_function
import os, sys, glob, argparse, copy, gdal, ogr, random, math, threading
from Lib_raster import identifyPixelValues, countPixelsOfValue, getRawDataImage, getGeometryImage, getEmpriseImage, getPixelWidthXYImage, getProjectionImage
from Lib_vector import createPointsFromCoordList, getAttributeValues, getAttributeNameList, createEmpriseShapeReduced, fusionVectors
from Lib_text import writeTextFile, appendTextFileCR
from Lib_file import removeVectorFile, removeFile
from Lib_operator import switch, case
from Lib_math import average, standardDeviation
from Lib_log import timeLine
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 3

###########################################################################################################################################
# STRUCTURE StructInfoMicoClass                                                                                                           #
###########################################################################################################################################
# Structure contenant contenant les informations nombre de points, valeur du label microclass et liste de points associé à une micro classe
class StructInfoMicoClass:
    def __init__(self):
        self.label_class = 0
        self.nb_points = 0
        self.info_points_list = None
        sample_points_list = None

###########################################################################################################################################
# FONCTION selectSamples                                                                                                                  #
###########################################################################################################################################
# ROLE:
#     fonction de selection de points d'échantions dans un fichier raster apres fusion de toute les fichiers macro, de facon aléatoire
#
# ENTREES DE LA FONCTION :
#    image_input_list : liste d'image d'entrée stacké au format .tif
#    sample_image_input : image d'echantillons de micro classes d'entrée .tif
#    vector_output : fichier vecteur résultat de la vectorisation de la classification
#    table_statistics_output : fichier contenant le resultat des statistiques sur les valeurs des points par micro classes .csv
#    sampler_strategy : mode de strategie de selection
#    select_ratio_floor : ratio de taux de selection pour toutes les micro classes avec une valeur plancher
#    ratio_per_class_dico : dictionaire de ratio  de taux de selection pour chaque macro classe
#    name_column : nom de la colonne du fichier shape contenant l'information de classification
#    no_data_value : Option : Value pixel of no data
#    path_time_log : fichier de log de sortie
#    rand_seed : graine pour la partie randon sample
#    ram_otb : memoire RAM disponible pour les applications OTB
#    epsg : Optionnel : par défaut 2154
#    format_vector : format du fichier vecteur. Optionnel, par default : 'ESRI Shapefile'
#    extension_vector : extension du fichier vecteur de sortie, par defaut = '.shp'
#    save_results_intermediate : sauvegarde les fichier de sorties intermediaires, par defaut = False
#    overwrite : supprime ou non les fichiers existants ayant le meme nom
#
# SORTIES DE LA FONCTION :
#    Le fichier vecteur de points d'échantions
#    Eléments modifiés auccun
#
def selectSamples(image_input_list, sample_image_input, vector_output, table_statistics_output, sampler_strategy, select_ratio_floor, ratio_per_class_dico, name_column, no_data_value, path_time_log, rand_seed=0, ram_otb=0, epsg=2154, format_vector='ESRI Shapefile', extension_vector=".shp", save_results_intermediate=False, overwrite=True) :

    # Mise à jour du Log
    starting_event = "selectSamples() : Select points in raster mask macro input starting : "
    timeLine(path_time_log, starting_event)

    if debug >= 3:
        print(cyan + "selectSamples() : " + endC + "image_input_list : " + str(image_input_list) + endC)
        print(cyan + "selectSamples() : " + endC + "sample_image_input : " + str(sample_image_input) + endC)
        print(cyan + "selectSamples() : " + endC + "vector_output : " + str(vector_output) + endC)
        print(cyan + "selectSamples() : " + endC + "table_statistics_output : " + str(table_statistics_output) + endC)
        print(cyan + "selectSamples() : " + endC + "sampler_strategy : " + str(sampler_strategy) + endC)
        print(cyan + "selectSamples() : " + endC + "select_ratio_floor : " + str(select_ratio_floor) + endC)
        print(cyan + "selectSamples() : " + endC + "ratio_per_class_dico : " + str(ratio_per_class_dico) + endC)
        print(cyan + "selectSamples() : " + endC + "name_column : " + str(name_column) + endC)
        print(cyan + "selectSamples() : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "selectSamples() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "selectSamples() : " + endC + "rand_seed : " + str(rand_seed) + endC)
        print(cyan + "selectSamples() : " + endC + "ram_otb : " + str(ram_otb) + endC)
        print(cyan + "selectSamples() : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "selectSamples() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "selectSamples() : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "selectSamples() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "selectSamples() : " + endC + "overwrite : " + str(overwrite) + endC)

    # Constantes
    EXT_XML = ".xml"

    SUFFIX_SAMPLE = "_sample"
    SUFFIX_STATISTICS = "_statistics"
    SUFFIX_POINTS = "_points"
    SUFFIX_VALUE = "_value"

    BAND_NAME = "band_"
    COLUMN_CLASS = "class"
    COLUMN_ORIGINFID = "originfid"

    NB_POINTS = "nb_points"
    AVERAGE = "average"
    STANDARD_DEVIATION = "st_dev"

    print(cyan + "selectSamples() : " + bold + green + "DEBUT DE LA SELECTION DE POINTS" + endC)

    # Definition variables et chemins
    repertory_output = os.path.dirname(vector_output)
    filename = os.path.splitext(os.path.basename(vector_output))[0]
    sample_points_output = repertory_output + os.sep + filename +  SUFFIX_SAMPLE + extension_vector
    file_statistic_points = repertory_output + os.sep + filename + SUFFIX_STATISTICS + SUFFIX_POINTS + EXT_XML

    if debug >= 3:
        print(cyan + "selectSamples() : " + endC + "file_statistic_points : " + str(file_statistic_points) + endC)

    # 0. EXISTENCE DU FICHIER DE SORTIE
    #----------------------------------

    # Si le fichier vecteur points de sortie existe deja et que overwrite n'est pas activé
    check = os.path.isfile(vector_output)
    if check and not overwrite:
        print(bold + yellow + "Samples points already done for file %s and will not be calculated again." %(vector_output) + endC)
    else:   # Si non ou si la vérification est désactivée : creation du fichier d'échantillons points

        # Suppression de l'éventuel fichier existant
        if check:
            try:
                removeVectorFile(vector_output)
            except Exception:
                pass # Si le fichier ne peut pas être supprimé, on suppose qu'il n'existe pas et on passe à la suite
        if os.path.isfile(table_statistics_output) :
            try:
                removeFile(table_statistics_output)
            except Exception:
                pass # Si le fichier ne peut pas être supprimé, on suppose qu'il n'existe pas et on passe à la suite


        # 1. STATISTIQUE SUR L'IMAGE DES ECHANTILLONS RASTEUR
        #----------------------------------------------------

        if debug >= 3:
            print(cyan + "selectSamples() : " + bold + green + "Start statistique sur l'image des echantillons rasteur..." + endC)

        id_micro_list = identifyPixelValues(sample_image_input)

        if 0 in id_micro_list :
            id_micro_list.remove(0)

        min_micro_class_nb_points = -1
        min_micro_class_label = 0
        infoStructPointSource_dico = {}

        writeTextFile(file_statistic_points, '<?xml version="1.0" ?>\n')
        appendTextFileCR(file_statistic_points, '<GeneralStatistics>')
        appendTextFileCR(file_statistic_points, '    <Statistic name="pointsPerClassRaw">')

        if debug >= 2:
            print("Nombre de points par micro classe :" + endC)

        for id_micro in id_micro_list :
            nb_pixels = countPixelsOfValue(sample_image_input, id_micro)

            if debug >= 2:
                print("MicroClass : " + str(id_micro) + ", nb_points = " + str(nb_pixels))
            appendTextFileCR(file_statistic_points, '        <StatisticPoints class="%d" value="%d" />' %(id_micro, nb_pixels))

            if min_micro_class_nb_points == -1 or min_micro_class_nb_points > nb_pixels :
                min_micro_class_nb_points = nb_pixels
                min_micro_class_label = id_micro

            infoStructPointSource_dico[id_micro] = StructInfoMicoClass()
            infoStructPointSource_dico[id_micro].label_class = id_micro
            infoStructPointSource_dico[id_micro].nb_points = nb_pixels
            infoStructPointSource_dico[id_micro].info_points_list = []
            del nb_pixels

        if debug >= 2:
            print("MicroClass min points find : " + str(min_micro_class_label) + ", nb_points = " + str(min_micro_class_nb_points))

        appendTextFileCR(file_statistic_points, '    </Statistic>')

        pending_event = cyan + "selectSamples() : " + bold + green + "End statistique sur l'image des echantillons rasteur. " + endC
        if debug >= 3:
            print(pending_event)
        timeLine(path_time_log,pending_event)

        # 2. CHARGEMENT DE L'IMAGE DES ECHANTILLONS
        #------------------------------------------

        if debug >= 3:
            print(cyan + "selectSamples() : " + bold + green + "Start chargement de l'image des echantillons..." + endC)

        # Information image
        cols, rows, bands = getGeometryImage(sample_image_input)
        xmin, xmax, ymin, ymax = getEmpriseImage(sample_image_input)
        pixel_width, pixel_height = getPixelWidthXYImage(sample_image_input)
        projection_input = int(getProjectionImage(sample_image_input))
        if projection_input == None or projection_input == 0 :
            projection_input = epsg

        pixel_width = abs(pixel_width)
        pixel_height = abs(pixel_height)

        # Lecture des données
        raw_data = getRawDataImage(sample_image_input)

        if debug >= 3:
            print("projection = " + str(projection_input))
            print("cols = " + str(cols))
            print("rows = " + str(rows))

        # Creation d'une structure dico contenent tous les points différents de zéro
        progress = 0
        pass_prog = False
        for y_row in range(rows) :
            for x_col in range(cols) :
                value_class = raw_data[y_row][x_col]
                if value_class != 0 :
                    infoStructPointSource_dico[value_class].info_points_list.append(x_col + (y_row * cols))

            # Barre de progression
            if debug >= 4:
                if  ((float(y_row) / rows) * 100.0 > progress) and not pass_prog :
                    progress += 1
                    pass_prog = True
                    print("Progression => " + str(progress) + "%")
                if ((float(y_row) / rows) * 100.0  > progress + 1) :
                    pass_prog = False

        del raw_data

        pending_event = cyan + "selectSamples() : " + bold + green + "End chargement de l'image des echantillons. " + endC
        if debug >= 3:
            print(pending_event)
        timeLine(path_time_log,pending_event)

        # 3. SELECTION DES POINTS D'ECHANTILLON
        #--------------------------------------

        if debug >= 3:
            print(cyan + "selectSamples() : " + bold + green + "Start selection des points d'echantillon..." + endC)

        appendTextFileCR(file_statistic_points, '    <Statistic name="pointsPerClassSelect">')

        # Rendre deterministe la fonction aléatoire de random.sample
        if rand_seed > 0:
            random.seed( rand_seed )

        # Pour toute les micro classes
        for id_micro in id_micro_list :

            # Selon la stategie de selection
            nb_points_ratio = 0
            while switch(sampler_strategy.lower()):
                if case('all'):
                    # Le mode de selection 'all' est choisi
                    nb_points_ratio = infoStructPointSource_dico[id_micro].nb_points
                    infoStructPointSource_dico[id_micro].sample_points_list = range(nb_points_ratio)

                    break
                if case('percent'):
                    # Le mode de selection 'percent' est choisi
                    id_macro_class = int(math.floor(id_micro / 100) * 100)
                    select_ratio_class = ratio_per_class_dico[id_macro_class]
                    nb_points_ratio = int(infoStructPointSource_dico[id_micro].nb_points * select_ratio_class / 100)
                    infoStructPointSource_dico[id_micro].sample_points_list = random.sample(range(infoStructPointSource_dico[id_micro].nb_points), nb_points_ratio)
                    break
                if case('mixte'):
                    # Le mode de selection 'mixte' est choisi
                    nb_points_ratio = int(infoStructPointSource_dico[id_micro].nb_points * select_ratio_floor / 100)
                    if id_micro == min_micro_class_label :
                        # La plus petite micro classe est concervée intégralement
                        infoStructPointSource_dico[id_micro].sample_points_list = range(infoStructPointSource_dico[id_micro].nb_points)
                        nb_points_ratio = min_micro_class_nb_points
                    elif nb_points_ratio <= min_micro_class_nb_points :
                        # Les micro classes dont le ratio de selection est inferieur au nombre de points de la plus petite classe sont égement conservées intégralement
                        infoStructPointSource_dico[id_micro].sample_points_list = random.sample(range(infoStructPointSource_dico[id_micro].nb_points), min_micro_class_nb_points)
                        nb_points_ratio = min_micro_class_nb_points
                    else :
                        # Pour toutes les autres micro classes tirage aleatoire d'un nombre de points correspondant au ratio
                        infoStructPointSource_dico[id_micro].sample_points_list = random.sample(range(infoStructPointSource_dico[id_micro].nb_points), nb_points_ratio)

                    break
                break


            if debug >= 2:
                print("MicroClass = " + str(id_micro) + ", nb_points_ratio " + str(nb_points_ratio))
            appendTextFileCR(file_statistic_points, '        <StatisticPoints class="%d" value="%d" />' %(id_micro, nb_points_ratio))

        appendTextFileCR(file_statistic_points, '    </Statistic>')
        appendTextFileCR(file_statistic_points, '</GeneralStatistics>')

        pending_event = cyan + "selectSamples() : " + bold + green + "End selection des points d'echantillon. " + endC
        if debug >= 3:
            print(pending_event)
        timeLine(path_time_log,pending_event)

        # 4. PREPARATION DES POINTS D'ECHANTILLON
        #----------------------------------------

        if debug >= 3:
            print(cyan + "selectSamples() : " + bold + green + "Start preparation des points d'echantillon..." + endC)

        # Création du dico de points
        points_random_value_dico = {}
        index_dico_point = 0
        for micro_class in infoStructPointSource_dico :
            micro_class_struct = infoStructPointSource_dico[micro_class]
            label_class = micro_class_struct.label_class
            point_attr_dico = {name_column:int(label_class), COLUMN_CLASS:int(label_class), COLUMN_ORIGINFID:0}

            for id_point in micro_class_struct.sample_points_list:

                # Recuperer les valeurs des coordonnees des points
                coor_x = float(xmin + (int(micro_class_struct.info_points_list[id_point] % cols) * pixel_width)) + (pixel_width / 2.0)
                coor_y = float(ymax - (int(micro_class_struct.info_points_list[id_point] / cols) * pixel_height)) - (pixel_height / 2.0)
                points_random_value_dico[index_dico_point] = [[coor_x, coor_y], point_attr_dico]
                del coor_x
                del coor_y
                index_dico_point += 1
            del point_attr_dico
        del infoStructPointSource_dico

        pending_event = cyan + "selectSamples() : " + bold + green + "End preparation des points d'echantillon. " + endC
        if debug >=3:
            print(pending_event)
        timeLine(path_time_log,pending_event)

        # 5. CREATION DU FICHIER SHAPE DE POINTS D'ECHANTILLON
        #-----------------------------------------------------

        if debug >= 3:
            print(cyan + "selectSamples() : " + bold + green + "Start creation du fichier shape de points d'echantillon..." + endC)

        # Définir les attibuts du fichier résultat
        attribute_dico = {name_column:ogr.OFTInteger, COLUMN_CLASS:ogr.OFTInteger, COLUMN_ORIGINFID:ogr.OFTInteger}

        # Creation du fichier shape
        createPointsFromCoordList(attribute_dico, points_random_value_dico, sample_points_output, projection_input, format_vector)
        del attribute_dico
        del points_random_value_dico

        pending_event = cyan + "selectSamples() : " + bold + green + "End creation du fichier shape de points d'echantillon. " + endC
        if debug >=3:
            print(pending_event)
        timeLine(path_time_log,pending_event)

        # 6.  EXTRACTION DES POINTS D'ECHANTILLONS
        #-----------------------------------------

        if debug >= 3:
            print(cyan + "selectSamples() : " + bold + green + "Start extraction des points d'echantillon dans l'image..." + endC)

        # Cas ou l'on a une seule image
        if len(image_input_list) == 1:
            # Extract sample
            image_input = image_input_list[0]
            command = "otbcli_SampleExtraction -in %s -vec %s -outfield prefix -outfield.prefix.name %s -out %s -field %s" %(image_input, sample_points_output, BAND_NAME, vector_output, name_column)
            if ram_otb > 0:
                command += " -ram %d" %(ram_otb)
            if debug >= 3:
                print(command)
            exitCode = os.system(command)
            if exitCode != 0:
                raise NameError(cyan + "selectSamples() : " + bold + red + "An error occured during otbcli_SampleExtraction command. See error message above." + endC)

        # Cas de plusieurs imagettes
        else :

            # Le repertoire de sortie
            repertory_output = os.path.dirname(vector_output)
            # Initialisation de la liste pour le multi-threading et la liste de l'ensemble des echantions locaux
            thread_list = []
            vector_local_output_list = []

            # Obtenir l'emprise des images d'entrées pour redecouper le vecteur d'echantillon d'apprentissage pour chaque image
            for image_input in image_input_list :
                # Definition des fichiers sur emprise local
                file_name = os.path.splitext(os.path.basename(image_input))[0]
                emprise_local_sample = repertory_output + os.sep + file_name + SUFFIX_SAMPLE + extension_vector
                vector_sample_local_output = repertory_output + os.sep + file_name + SUFFIX_VALUE + extension_vector
                vector_local_output_list.append(vector_sample_local_output)

                # Gestion sans thread...
                #SampleLocalExtraction(image_input, sample_points_output, emprise_local_sample, vector_sample_local_output, name_column, BAND_NAME, ram_otb, format_vector, extension_vector, save_results_intermediate)

                # Gestion du multi threading
                thread = threading.Thread(target=SampleLocalExtraction, args=(image_input, sample_points_output, emprise_local_sample, vector_sample_local_output, name_column, BAND_NAME, ram_otb, format_vector, extension_vector, save_results_intermediate))
                thread.start()
                thread_list.append(thread)

            # Extraction des echantions points des images
            try:
                for thread in thread_list:
                    thread.join()
            except:
                print(cyan + "selectSamples() : " + bold + red + "Erreur lors de l'éextaction des valeurs d'echantion : impossible de demarrer le thread" + endC, file=sys.stderr)

            # Fusion des multi vecteurs de points contenant les valeurs des bandes de l'image
            fusionVectors(vector_local_output_list, vector_output, format_vector)

            # Clean des vecteurs point sample local file
            for vector_sample_local_output in vector_local_output_list :
                removeVectorFile(vector_sample_local_output)

        if debug >= 3:
            print(cyan + "selectSamples() : " + bold + green + "End extraction des points d'echantillon dans l'image." + endC)

        # 7. CALCUL DES STATISTIQUES SUR LES VALEURS DES POINTS D'ECHANTILLONS SELECTIONNEES
        #-----------------------------------------------------------------------------------

        if debug >= 3:
            print(cyan + "selectSamples() : " + bold + green + "Start calcul des statistiques sur les valeurs des points d'echantillons selectionnees..." + endC)

        # Si le calcul des statistiques est demandé presence du fichier stat
        if table_statistics_output != "":

            # On récupère la liste de données
            pending_event = cyan + "selectSamples() : " + bold + green + "Encours calcul des statistiques part1... " + endC
            if debug >=4:
                print(pending_event)
            timeLine(path_time_log,pending_event)

            attribute_name_dico = {}
            name_field_value_list = []
            names_attribut_list = getAttributeNameList(vector_output, format_vector)
            if debug >=4:
                print("names_attribut_list = " + str(names_attribut_list))

            attribute_name_dico[name_column] = ogr.OFTInteger
            for name_attribut in names_attribut_list :
                if BAND_NAME in name_attribut :
                    attribute_name_dico[name_attribut] = ogr.OFTReal
                    name_field_value_list.append(name_attribut)

            name_field_value_list.sort()

            res_values_dico = getAttributeValues(vector_output, None, None, attribute_name_dico, format_vector)
            del attribute_name_dico

            # Trie des données par identifiant micro classes
            pending_event = cyan + "selectSamples() : " + bold + green + "Encours calcul des statistiques part2... " + endC
            if debug >=4:
                print(pending_event)
            timeLine(path_time_log,pending_event)

            data_value_by_micro_class_dico = {}
            stat_by_micro_class_dico = {}

            # Initilisation du dico complexe
            for id_micro in id_micro_list :
                data_value_by_micro_class_dico[id_micro] = {}
                stat_by_micro_class_dico[id_micro] = {}
                for name_field_value in res_values_dico :
                    if name_field_value != name_column :
                        data_value_by_micro_class_dico[id_micro][name_field_value] = []
                        stat_by_micro_class_dico[id_micro][name_field_value] = {}
                        stat_by_micro_class_dico[id_micro][name_field_value][AVERAGE] = 0.0
                        stat_by_micro_class_dico[id_micro][name_field_value][STANDARD_DEVIATION] = 0.0

            # Trie des valeurs
            pending_event = cyan + "selectSamples() : " + bold + green + "Encours calcul des statistiques part3... " + endC
            if debug >=4:
                print(pending_event)
            timeLine(path_time_log,pending_event)

            for index in range(len(res_values_dico[name_column])) :
                id_micro = res_values_dico[name_column][index]
                for name_field_value in name_field_value_list :
                    data_value_by_micro_class_dico[id_micro][name_field_value].append(res_values_dico[name_field_value][index])
            del res_values_dico

            # Calcul des statistiques
            pending_event = cyan + "selectSamples() : " + bold + green + "Encours calcul des statistiques part4... " + endC
            if debug >=4:
                print(pending_event)
            timeLine(path_time_log,pending_event)

            for id_micro in id_micro_list :
                for name_field_value in name_field_value_list :
                    try :
                        stat_by_micro_class_dico[id_micro][name_field_value][AVERAGE] = average(data_value_by_micro_class_dico[id_micro][name_field_value])
                    except:
                        stat_by_micro_class_dico[id_micro][name_field_value][AVERAGE] = 0
                    try :
                        stat_by_micro_class_dico[id_micro][name_field_value][STANDARD_DEVIATION] = standardDeviation(data_value_by_micro_class_dico[id_micro][name_field_value])
                    except:
                        stat_by_micro_class_dico[id_micro][name_field_value][STANDARD_DEVIATION] = 0
                    try :
                        stat_by_micro_class_dico[id_micro][name_field_value][NB_POINTS] = len(data_value_by_micro_class_dico[id_micro][name_field_value])
                    except:
                        stat_by_micro_class_dico[id_micro][name_field_value][NB_POINTS] = 0

            del data_value_by_micro_class_dico

            # Creation du fichier statistique .csv
            pending_event = cyan + "selectSamples() : " + bold + green + "Encours calcul des statistiques part5... " + endC
            if debug >= 4:
                print(pending_event)
            timeLine(path_time_log,pending_event)

            text_csv = " Micro classes ; Champs couche image ; Nombre de points  ; Moyenne ; Ecart type \n"
            writeTextFile(table_statistics_output, text_csv)
            for id_micro in id_micro_list :
                for name_field_value in name_field_value_list :
                    # Ecriture du fichier
                    text_csv = " %d " %(id_micro)
                    text_csv += " ; %s" %(name_field_value)
                    text_csv += " ; %d" %(stat_by_micro_class_dico[id_micro][name_field_value][NB_POINTS])
                    text_csv += " ; %f" %(stat_by_micro_class_dico[id_micro][name_field_value][AVERAGE])
                    text_csv += " ; %f" %(stat_by_micro_class_dico[id_micro][name_field_value][STANDARD_DEVIATION])
                    appendTextFileCR(table_statistics_output, text_csv)
            del name_field_value_list

        else :
            if debug >=3:
                print(cyan + "selectSamples() : " + bold + green + "Pas de calcul des statistiques sur les valeurs des points demander!!!." + endC)

        del id_micro_list

        pending_event = cyan + "selectSamples() : " + bold + green + "End calcul des statistiques sur les valeurs des points d'echantillons selectionnees. " + endC
        if debug >= 3:
            print(pending_event)
        timeLine(path_time_log,pending_event)


    # 8. SUPRESSION DES FICHIERS INTERMEDIAIRES
    #------------------------------------------

    if not save_results_intermediate:

        if os.path.isfile(sample_points_output) :
            removeVectorFile(sample_points_output)

    print(cyan + "selectSamples() : " + bold + green + "FIN DE LA SELECTION DE POINTS" + endC)

    # Mise à jour du Log
    ending_event = "selectSamples() : Select points in raster mask macro input ending : "
    timeLine(path_time_log,ending_event)

    return

###########################################################################################################################################
# FONCTION SampleLocalExtraction()                                                                                                        #
###########################################################################################################################################
# ROLE:
#     Extracteur des valeurs de toutes les bandes pour les points d'echantillons pour d'une image
#
# ENTREES DE LA FONCTION :
#     image_input : imagette d'entrée
#     sample_points : vecteur points d'echantillons global
#     emprise_local_sample : zone vecteur d'echantion local sur l'emprise de l'imagette
#     vector_sample_local_output : vecteur points d'echantillons sur la zone de sortie
#     name_column : nom de la colonne id
#     band_name : prefixe nom des colonnes
#     ram_otb : memoire RAM disponible pour les applications OTB
#     format_vector : format du fichier vecteur. Optionnel, par default : 'ESRI Shapefile'
#     extension_vector : extension du fichier vecteur de sortie, par defaut = '.shp'
#     save_results_intermediate : sauvegarde les fichier de sorties intermediaires, par defaut = False
# SORTIES DE LA FONCTION :
#     Vecteur polygonisé
#
def SampleLocalExtraction(image_input, sample_points, emprise_local_sample, vector_sample_local_output, name_column, band_name, ram_otb=0, format_vector='ESRI Shapefile', extension_vector=".shp", save_results_intermediate=False):

    # Creation de la zone local
    empr_xmin, empr_xmax, empr_ymin, empr_ymax = getEmpriseImage(image_input)
    createEmpriseShapeReduced(sample_points, empr_xmin, empr_ymin, empr_xmax, empr_ymax, emprise_local_sample, format_vector)

    # Extract sample
    command = "otbcli_SampleExtraction -in %s -vec %s -outfield prefix -outfield.prefix.name %s -out %s -field %s" %(image_input, emprise_local_sample, band_name, vector_sample_local_output, name_column)
    if ram_otb > 0:
        command += " -ram %d" %(ram_otb)
    print(command)
    exitCode = os.system(command)
    if exitCode != 0:
        raise NameError(cyan + "SampleLocalExtraction() : " + bold + red + "An error occured during otbcli_SampleExtraction command. See error message above." + endC)

    # Clean temp file
    if not save_results_intermediate :
        removeVectorFile(emprise_local_sample)

    return

###########################################################################################################################################
# MISE EN PLACE DU PARSER                                                                                                                 #
###########################################################################################################################################

# Code executé seulement dans le cas ou le script est lancé depuis une ligne de commande
# Il n'est pas executé lors d'un import SampleSelectionRaster..py
# Exemple de lancement en ligne de commande:
# python SampleSelectionRaster.py il /mnt/Data/10_Agents_travaux_en_cours/Gilles/Test_chaine_classif_methodo/10_IMAGE/ZoneTest_stacked.tif -s /mnt/Data/10_Agents_travaux_en_cours/Gilles/Test_chaine_classif_methodo/40_ECHANTILLONS/42_MICRO/samples_micro_merged.tif  -o /mnt/Data/10_Agents_travaux_en_cours/Gilles/Test_chaine_classif_methodo/40_ECHANTILLONS/43_SAMPLES/Samples_Points_Micro.shp -st mixte -srf 10.0 -col id -log /mnt/Data/10_Agents_travaux_en_cours/Gilles/Test_chaine_classif_methodo/SamplesfichierTest.log

def main(gui=False):

    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, prog="SampleSelectionRaster.", description='\
    Info : Vectoring function of a tiff image classification result shapefile. \n\
    Objectif : Creer un fichier vecteur de points tirer de facon aleatoire a partir d un fichier raster masque macro. \n\
    Example : python SampleSelectionRaster.py -il /mnt/Data/10_Agents_travaux_en_cours/Gilles/Test_chaine_classif_methodo/10_IMAGE/ZoneTest_stacked.tif \n\
                                      -s /mnt/Data/10_Agents_travaux_en_cours/Gilles/Test_chaine_classif_methodo/40_ECHANTILLONS/42_MICRO/samples_micro_merged.tif \n\
                                      -o /mnt/Data/10_Agents_travaux_en_cours/Gilles/Test_chaine_classif_methodo/40_ECHANTILLONS/43_SAMPLES/Samples_Points_Micro.shp \n\
                                      -st mixte \n\
                                      -srf 10.0 \n\
                                      -col id \n\
                                      -log /mnt/Data/10_Agents_travaux_en_cours/Gilles/Test_chaine_classif_methodo/SamplesfichierTest.log')

    parser.add_argument('-il','--image_input_list',default=[],nargs="+",help="List images input to classify", type=str, required=True)
    parser.add_argument('-s','--sample_image_input',default="",help="Input sample images.", type=str, required=True)
    parser.add_argument('-o','--vector_output',default="",help="Vector output result of vectorisation classification image", type=str, required=True)
    parser.add_argument('-t','--table_statistics_output',default="",help="Statistics on values of points in file format csv ", type=str, required=False)
    parser.add_argument('-st','--sampler_strategy',default="mixte",help="Choice mode of strategy sample (Choice of : 'all' or 'mixte' or 'percent'). By default, 'mixte'", type=str, required=False)
    parser.add_argument('-srf','--select_ratio_floor',default=10.0,help="Ratio selection in percent for all micro class, with floor nb min points micro class", type=float, required=False)
    parser.add_argument('-rpc','--ratio_per_class_list',default=None,nargs="+",help="Dictionary of ratio in percent per class (format : class_id,value_ratio), ex. 11100,10.0 11200,15.0 12200,10.0 13000,12.0 20000,5.0", type=str, required=False)
    parser.add_argument('-col','--name_col', default="id",help="Name of the column containing the shapefile classification of information", type=str, required=True)
    parser.add_argument('-rand','--rand_seed',default=0,help="User defined seed for python random sample", type=int, required=False)
    parser.add_argument('-ram','--ram_otb',default=16,help="Ram available for processing otb applications (in MB)", type=int, required=False)
    parser.add_argument('-epsg','--epsg', default=2154,help="Projection of the output file.", type=int, required=False)
    parser.add_argument('-ndv','--no_data_value', default=0, help="Option in option optimize_emprise_nodata  : Value of the pixel no data. By default : 0", type=int, required=False)
    parser.add_argument('-vef','--format_vector', default="ESRI Shapefile",help="Format of the output vector file.", type=str, required=False)
    parser.add_argument('-vee','--extension_vector',default=".shp",help="Option : Extension file for vector. By default : '.shp'", type=str, required=False)
    parser.add_argument('-log','--path_time_log',default="",help="Name of log", type=str, required=False)
    parser.add_argument('-sav','--save_results_inter',action='store_true',default=False,help="Save or delete intermediate result after the process. By default, False", required=False)
    parser.add_argument('-now','--overwrite',action='store_false',default=True,help="Overwrite files with same names. By default : True", required=False)
    parser.add_argument('-debug','--debug',default=3,help="Option : Value of level debug trace, default : 3 ",type=int, required=False)
    args = displayIHM(gui, parser)

    # RECUPERATION DES ARGUMENTS
    # Récupération de l'image d'entrée
    if args.image_input_list != None:
        image_input_list = args.image_input_list
        for image_input in image_input_list :
            if not os.path.isfile(image_input):
                raise NameError (cyan + "SampleSelectionRaster : " + bold + red  + "File %s not existe!" %(image_input) + endC)

    # Récupération des images macro
    if args.sample_image_input != None:
        sample_image_input = args.sample_image_input
        if not os.path.isfile(sample_image_input):
            raise NameError (cyan + "SampleSelectionRaster : " + bold + red  + "File %s not existe!" %(sample_image_input) + endC)

    # Récupération de l'image de sortie
    if args.vector_output != None:
        vector_output = args.vector_output

    # Récupération du fichier de statistique de sortie
    if args.table_statistics_output != None:
        table_statistics_output = args.table_statistics_output

    # Récupération des noms liés aux polygones
    if args.name_col != None:
        name_column = args.name_col

    # Récupération du mode de strategie de selection
    if args.sampler_strategy != None:
        sampler_strategy = args.sampler_strategy
        if sampler_strategy.lower() not in ['all', 'mixte', 'percent'] :
            raise NameError(cyan + "SampleSelectionRaster : " + bold + red + "Parameter 'sampler_strategy' value  is not in list ['all', 'mixte', 'percent']." + endC)

    # Récupération du taux de selection
    if args.select_ratio_floor != None:
        select_ratio_floor = args.select_ratio_floor

    # Creation du dictionaire contenant les valeurs du pour centage de points pour chaque macro class
    ratio_per_class_dico = {}
    if args.ratio_per_class_list != None:
        tmp_ratio_per_class_list = args.ratio_per_class_list
        for ratio_per_class in tmp_ratio_per_class_list:
            info_list = ratio_per_class.split(',')
            ratio_per_class_dico[int(info_list[0])] = float(info_list[1])

    # Récupération de la projection du fichier de sortie
    if args.epsg != None :
        epsg = args.epsg

    # Parametres de valeur du nodata
    if args.no_data_value!= None:
        no_data_value = args.no_data_value

    # Récupération du format du fichier de sortie
    if args.format_vector != None :
        format_vector = args.format_vector

    # Récupération de l'extension des fichiers vecteurs
    if args.extension_vector != None:
        extension_vector = args.extension_vector

    # Récupération du nom du fichier log
    if args.path_time_log!= None:
        path_time_log = args.path_time_log

    # Récupération du parametre rand
    if args.rand_seed != None:
        rand_seed = args.rand_seed

    # Récupération du parametre ram
    if args.ram_otb != None:
        ram_otb = args.ram_otb

    # Ecrasement des fichiers
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
        print(cyan + "SampleSelectionRaster : " + endC + "image_input_list : " + str(image_input_list) + endC)
        print(cyan + "SampleSelectionRaster : " + endC + "sample_image_input : " + str(sample_image_input) + endC)
        print(cyan + "SampleSelectionRaster : " + endC + "vector_output : " + str(vector_output) + endC)
        print(cyan + "SampleSelectionRaster : " + endC + "table_statistics_output : " + str(table_statistics_output) + endC)
        print(cyan + "SampleSelectionRaster : " + endC + "sampler_strategy : " + str(sampler_strategy) + endC)
        print(cyan + "SampleSelectionRaster : " + endC + "select_ratio_floor : " + str(select_ratio_floor) + endC)
        print(cyan + "SampleSelectionRaster : " + endC + "ratio_per_class_dico : " + str(ratio_per_class_dico) + endC)
        print(cyan + "SampleSelectionRaster : " + endC + "name_col : " + str(name_column) + endC)
        print(cyan + "SampleSelectionRaster : " + endC + "rand_seed : " + str(rand_seed) + endC)
        print(cyan + "SampleSelectionRaster : " + endC + "ram_otb : " + str(ram_otb) + endC)
        print(cyan + "SampleSelectionRaster : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "SampleSelectionRaster : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "SampleSelectionRaster : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "SampleSelectionRaster : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "SampleSelectionRaster : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "SampleSelectionRaster : " + endC + "save_results_inter : " + str(save_results_intermediate) + endC)
        print(cyan + "SampleSelectionRaster : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "SampleSelectionRaster : " + endC + "debug : " + str(debug) + endC)

    # EXECUTION DE LA FONCTION

    # Si le dossier de sortie n'existe pas, on le crée
    repertory_output = os.path.dirname(vector_output)
    if not os.path.isdir(repertory_output):
        os.makedirs(repertory_output)

    # Si le dossier de sortie n'existe pas, on le crée
    if table_statistics_output != "":
        repertory_output = os.path.dirname(table_statistics_output)
        if not os.path.isdir(repertory_output):
            os.makedirs(repertory_output)

    # Traitement image à vectoriser
    selectSamples(image_input_list, sample_image_input, vector_output, table_statistics_output, sampler_strategy, select_ratio_floor, ratio_per_class_dico, name_column, no_data_value, path_time_log, rand_seed, ram_otb, epsg, format_vector, extension_vector, save_results_intermediate, overwrite)

# ================================================

if __name__ == '__main__':
  main(gui=False)
