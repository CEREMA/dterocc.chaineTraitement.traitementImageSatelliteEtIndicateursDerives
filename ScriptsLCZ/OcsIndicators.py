#!/usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerSO/DALETT/SCGSI  All rights reserved.                                                                            #
#############################################################################################################################################

from __future__ import print_function
import os, sys, argparse, shutil, ogr
from Lib_log import timeLine
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_vector import addNewFieldVector, renameFieldsVector, filterSelectDataVector, updateFieldVector, fusionVectors
from Lib_raster import getProjectionImage
from Lib_file import removeVectorFile
from CrossingVectorRaster import statisticsVectorRaster

debug = 3

####################################################################################################
# FONCTION occupationIndicator()                                                                   #
####################################################################################################
# ROLE et INFORMATIONS :
#     Calcul de l'indicateur supplémentaire sur l'occupation du sol et la hauteur de végétation
#     Attribue une classe d'OCS suivant le type d'occupation du sol et la hauteur moyenne de la végétation :
#       classe 0 = bâti + route + eau
#       classe 1 = sol nu
#       classe 2 = végétation avec H entre 0 et 1
#       classe 3 = végétation avec H entre 1 et 5
#       classe 4 = végétation avec H > 5
#
# ENTREES DE LA FONCTION :
#     classif_input : classification OCS en entrée
#     mnh_input : Modèle Numérique de Hauteur en entrée
#     vector_grid_input : fichier de maillage en entrée
#     vector_grid_output : fichier de maillage en sortie
#     class_label_dico : dictionaire affectation de label aux classes de classification
#     epsg : EPSG des fichiers de sortie utilisation de la valeur des fichiers d'entrée si la valeur = 0
#     path_time_log : fichier log de sortie
#     format_raster : Format de l'image de sortie, par défaut : GTiff
#     format_vector : format du fichier vecteur. Optionnel, par default : 'ESRI Shapefile'
#     extension_raster : extension des fichiers raster de sortie, par defaut = '.tif'
#     extension_vector : extension du fichier vecteur de sortie, par defaut = '.shp'
#     save_results_intermediate : fichiers de sorties intermédiaires nettoyés, par défaut = False
#     overwrite : écrase si un fichier existant a le même nom qu'un fichier de sortie, par défaut = True
#
# SORTIES DE LA FONCTION :
#     N.A

def occupationIndicator(classif_input, mnh_input, vector_grid_input, vector_grid_output, class_label_dico, epsg, path_time_log, format_raster='GTiff', format_vector='ESRI Shapefile', extension_raster=".tif", extension_vector=".shp", save_results_intermediate=False, overwrite=True):

    # Mise à jour du Log
    starting_event = "occupationIndicator() : Calcul de l'indicateur occupation du sol/hauteur de végétation starting : "
    timeLine(path_time_log,starting_event)
    print(bold + green + "Début du calcul de l'indicateur 'occupation du sol/hauteur de végétation'." + endC + "\n")

    if debug >= 3 :
        print(bold + green + "occupationIndicator() : Variables dans la fonction" + endC)
        print(cyan + "occupationIndicator() : " + endC + "classif_input : " + str(classif_input) + endC)
        print(cyan + "occupationIndicator() : " + endC + "mnh_input : " + str(mnh_input) + endC)
        print(cyan + "occupationIndicator() : " + endC + "vector_grid_input : " + str(vector_grid_input) + endC)
        print(cyan + "occupationIndicator() : " + endC + "vector_grid_output : " + str(vector_grid_output) + endC)
        print(cyan + "occupationIndicator() : " + endC + "class_label_dico : " + str(class_label_dico) + endC)
        print(cyan + "occupationIndicator() : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "occupationIndicator() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "occupationIndicator() : " + endC + "format_raster : " + str(format_raster) + endC)
        print(cyan + "occupationIndicator() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "occupationIndicator() : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "occupationIndicator() : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "occupationIndicator() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "occupationIndicator() : " + endC + "overwrite : " + str(overwrite) + endC)

    # Constante
    FIELD_OCS_NAME = 'class_OCS'
    FIELD_OCS_TYPE = ogr.OFTInteger
    FIELD_MAJORITY_NAME = 'majority'

    # Test si le vecteur de sortie existe déjà et si il doit être écrasés
    check = os.path.isfile(vector_grid_output)

    if check and not overwrite: # Si le fichier de sortie existent deja et que overwrite n'est pas activé
        print(bold + yellow + "Le calcul de l'indicateur occupation du sol/hauteur de végétation a déjà eu lieu. \n" + endC)
        print(bold + yellow + "Grid vector output : " + vector_grid_output + " already exists and will not be created again." + endC)
    else :
        if check:
            try:
                removeVectorFile(vector_grid_output)
            except Exception:
                pass # si le fichier n'existe pas, il ne peut pas être supprimé : cette étape est ignorée

        ############################################
        ### Préparation générale des traitements ###
        ############################################

        # Récuperation de la projection de l'image
        epsg_proj = getProjectionImage(classif_input)
        if epsg_proj == 0:
            epsg_proj = epsg

        # Liste des classes
        key_class_label_list = list(class_label_dico.keys())

        # Préparation des fichiers temporaires
        temp_path = os.path.dirname(vector_grid_output) + os.sep + "TEMP_OCS"

        # Nettoyage du repertoire temporaire si il existe
        if os.path.exists(temp_path):
            shutil.rmtree(temp_path)
        os.makedirs(temp_path)

        tempOCS = temp_path + os.sep + "occupation_du_sol" + extension_vector
        tempHveg = temp_path + os.sep + "occupation_du_sol_hauteur_de_vegetation" + extension_vector

        temp_class0 = temp_path + os.sep + "occupation_du_sol_hauteur_de_vegetation_class0" + extension_vector
        temp_class1 = temp_path + os.sep + "occupation_du_sol_hauteur_de_vegetation_class1" + extension_vector
        temp_class2 = temp_path + os.sep + "occupation_du_sol_hauteur_de_vegetation_class2" + extension_vector
        temp_class3 = temp_path + os.sep + "occupation_du_sol_hauteur_de_vegetation_class3" + extension_vector
        temp_class4 = temp_path + os.sep + "occupation_du_sol_hauteur_de_vegetation_class4" + extension_vector

        vegetation_height_temp = temp_path + os.sep + "hauteur_vegetation_temp" + extension_raster
        vegetation_height = temp_path + os.sep + "hauteur_vegetation" + extension_raster

        ##############################
        ### Calcul de l'indicateur ###
        ##############################

        # Récupération de l'occupation du sol de chaque maille
        statisticsVectorRaster(classif_input, vector_grid_input, tempOCS, 1, True, True, False, [], [], class_label_dico, path_time_log, True, format_vector, save_results_intermediate, overwrite)

        # Récupération de la hauteur moyenne et la hauteur max de la végétation de chaque maille
        command = "otbcli_BandMath -il %s %s -out %s float -exp 'im1b1==%s ? im2b1 : 0'" %(classif_input, mnh_input, vegetation_height_temp, str(key_class_label_list[4]))
        exit_code = os.system(command)
        if exit_code != 0:
            print(command)
            print(cyan + "occupationIndicator() : " + bold + red + "!!! Une erreur c'est produite au cours de la commande otbcli_BandMath : " + command + ". Voir message d'erreur." + endC, file=sys.stderr)
            raise

        command = "gdal_translate -a_srs EPSG:%s -a_nodata 0 -of %s %s %s" %(str(epsg_proj), format_raster, vegetation_height_temp, vegetation_height)
        exit_code = os.system(command)
        if exit_code != 0:
            print(command)
            print(cyan + "occupationIndicator() : " + bold + red + "!!! Une erreur c'est produite au cours de la comande : gdal_translate : " + command + ". Voir message d'erreur." + endC, file=sys.stderr)
            raise

        statisticsVectorRaster(vegetation_height, tempOCS, tempHveg, 1, False, False, True, [], [], {}, path_time_log, True, format_vector, save_results_intermediate, overwrite)

        # Définir le nom des champs
        temp_class_list = []
        list_class_str = ""

        for class_str in key_class_label_list:
            list_class_str += "%s, "%(str(class_label_dico[class_str]))
        built_str = class_label_dico[key_class_label_list[0]]
        road_str = class_label_dico[key_class_label_list[1]]
        water_str = class_label_dico[key_class_label_list[2]]
        baresoil_str = class_label_dico[key_class_label_list[3]]
        vegetation_str = class_label_dico[key_class_label_list[4]]
        vegetation_height_medium_str = "H_moy_" + vegetation_str[0:3]
        vegetation_height_max_str = "H_max_" + vegetation_str[0:3]

        if debug >= 3 :
            print("built_str = " + built_str)
            print("road_str = " + road_str)
            print("water_str = " + water_str)
            print("baresoil_str = " + baresoil_str)
            print("vegetation_str = " + vegetation_str)
            print("vegetation_height_medium_str = " + vegetation_height_medium_str)
            print("vegetation_height_max_str = " + vegetation_height_max_str)

        column = "'ID, majority, minority, %s%s, %s, %s'"%(list_class_str, vegetation_height_max_str, vegetation_height_medium_str, FIELD_OCS_NAME)

        # Ajout d'un champ renvoyant la classe d'OCS attribué à chaque polygone et renomer le champ 'mean'
        renameFieldsVector(tempHveg, ['max'], [vegetation_height_max_str], format_vector)
        renameFieldsVector(tempHveg, ['mean'], [vegetation_height_medium_str], format_vector)
        addNewFieldVector(tempHveg, FIELD_OCS_NAME, FIELD_OCS_TYPE, 0, None, None, format_vector)

        # Attribution de la classe 0 => classe majoritaire de bâti ou route ou eau
        #expression = "(" + built_str + " >= " + baresoil_str + " AND " + built_str + " >= " + vegetation_str + ") OR (" + road_str + " >= " + baresoil_str + " AND " + road_str + " >= " + vegetation_str + ") OR (" + water_str + " >= " + baresoil_str + " AND " + water_str + " >= " + vegetation_str + ")"
        expression = "(" + FIELD_MAJORITY_NAME + " = '" + built_str + "') OR (" + FIELD_MAJORITY_NAME + " = '"  + road_str + "') OR (" + FIELD_MAJORITY_NAME + " = '"  + water_str + "')"
        if debug >= 3 :
           print(expression)
        ret = filterSelectDataVector(tempHveg, temp_class0, column, expression, format_vector)
        if not ret :
            raise NameError (cyan + "occupationIndicator() : " + bold + red  + "Attention problème lors du filtrage des BD vecteurs l'expression SQL %s est incorrecte" %(expression) + endC)
        updateFieldVector(temp_class0, FIELD_OCS_NAME, 0, format_vector)
        temp_class_list.append(temp_class0)

        # Attribution de la classe 1 => classe majoritaire de sol nu
        #expression = "(" + baresoil_str + " > " + built_str + " AND " + baresoil_str + " > " + road_str + " AND " + baresoil_str + " > " + water_str + " AND " + baresoil_str + " >= " + vegetation_str + ")"
        expression = "(" + FIELD_MAJORITY_NAME + " = '" + baresoil_str + "')"
        if debug >= 3 :
           print(expression)
        ret = filterSelectDataVector(tempHveg, temp_class1, column, expression, format_vector)
        if not ret :
            raise NameError (cyan + "occupationIndicator() : " + bold + red  + "Attention problème lors du filtrage des BD vecteurs l'expression SQL %s est incorrecte" %(expression) + endC)
        updateFieldVector(temp_class1, FIELD_OCS_NAME, 1, format_vector)
        temp_class_list.append(temp_class1)

        # Attribution de la classe 2 => classe majoritaire de végétation avec Hauteur inferieur à 1
        #expression = "(" + vegetation_str + " > " + built_str + " AND " + vegetation_str + " > " + road_str + " AND " + vegetation_str + " > " + water_str + " AND " + vegetation_str + " > " + baresoil_str + ") AND (" + vegetation_height_medium_str + " < 1)"
        expression = "(" + FIELD_MAJORITY_NAME + " = '" + vegetation_str + "') AND (" + vegetation_height_medium_str + " < 1)"
        if debug >= 3 :
            print(expression)
        ret = filterSelectDataVector(tempHveg, temp_class2, column, expression, format_vector)
        if not ret :
            raise NameError (cyan + "occupationIndicator() : " + bold + red  + "Attention problème lors du filtrage des BD vecteurs l'expression SQL %s est incorrecte" %(expression) + endC)
        updateFieldVector(temp_class2, FIELD_OCS_NAME, 2, format_vector)
        temp_class_list.append(temp_class2)

        # Attribution de la classe 3 => classe majoritaire de végétation avec Hauteur entre 1 et 5
        #expression = "(" + vegetation_str + " > " + built_str + " AND " + vegetation_str + " > " + road_str + " AND " + vegetation_str + " > " + water_str + " AND " + vegetation_str + " > " + baresoil_str + ") AND (" + vegetation_height_medium_str + " >= 1 AND " + vegetation_height_medium_str + " < 5)"
        expression = "(" + FIELD_MAJORITY_NAME + " = '" + vegetation_str + "') AND (" + vegetation_height_medium_str + " >= 1 AND " + vegetation_height_medium_str + " < 5)"
        if debug >= 3 :
            print(expression)
        ret = filterSelectDataVector(tempHveg, temp_class3, column, expression, format_vector)
        if not ret :
            raise NameError (cyan + "occupationIndicator() : " + bold + red  + "Attention problème lors du filtrage des BD vecteurs l'expression SQL %s est incorrecte" %(expression) + endC)
        updateFieldVector(temp_class3, FIELD_OCS_NAME, 3, format_vector)
        temp_class_list.append(temp_class3)

        # Attribution de la classe 4 => classe majoritaire de végétation avec Hauteur > 5
        #expression = "(" + vegetation_str + " > " + built_str + " AND " + vegetation_str + " > " + road_str + " AND " + vegetation_str + " > " + water_str + " AND " + vegetation_str + " > " + baresoil_str + ") AND (" + vegetation_height_medium_str + " >= 5)"
        expression = "(" + FIELD_MAJORITY_NAME + " = '" + vegetation_str + "') AND (" + vegetation_height_medium_str + " >= 5)"
        if debug >= 3 :
            print(expression)
        ret = filterSelectDataVector(tempHveg, temp_class4, column, expression, format_vector)
        if not ret :
            raise NameError (cyan + "occupationIndicator() : " + bold + red  + "Attention problème lors du filtrage des BD vecteurs l'expression SQL %s est incorrecte" %(expression) + endC)
        updateFieldVector(temp_class4, FIELD_OCS_NAME, 4, format_vector)
        temp_class_list.append(temp_class4)

        fusionVectors(temp_class_list, vector_grid_output, format_vector)

        ##########################################
        ### Nettoyage des fichiers temporaires ###
        ##########################################

        if not save_results_intermediate:
            if os.path.exists(temp_path):
                shutil.rmtree(temp_path)

    # Mise à jour du Log
    print(bold + green + "Fin du calcul de l'indicateur 'occupation du sol/hauteur de végétation'." + endC + "\n")
    ending_event = "occupationIndicator() : Calcul de l'indicateur occupation du sol/hauteur de végétation ending : "
    timeLine(path_time_log,ending_event)

    return

#############################################################################################################################
################################################## Mise en place du parser ##################################################
#############################################################################################################################

def main(gui=False):
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, prog="OcsIndicators", description="\
    Info : Calculation of additional LCZ indicators (not included in the original indicators). \n\
    Objectif : Calcul d'indicateurs supplementaires (non-compris dans les indicateurs d'origine) pour les LCZ. \n\
    Example : python OcsIndicators.py -i ../Classif_OCS.tif \n\
                                    -mnh  ../Nancy/MNH.tif \n\
                                    -v ../UrbanAtlas2012_cleaned.shp \n\
                                    -o ../Nancy/occupationIndicator.shp \n\
                                    -cld 11100:Bati 11200:Route 12200:Eau 13000:SolNu 20000:Vegetation \n\
                                    -epsg 2154 \n\
                                    -log ../ImagesTestChaine/APTV_05/fichierTestLog.txt")

    parser.add_argument('-i', '--classif_input', default="", type=str, required=True, help="Input file Modele classification OCS (raster).")
    parser.add_argument('-mnh', '--mnh_input', default="", type=str, required=True, help="Input file Modele Numerique de Hauteur(raster).")
    parser.add_argument('-v', '--vector_grid_input', default="", type=str, required=True, help="Input file shape grid (vector).")
    parser.add_argument('-o', '--vector_grid_output', default="", type=str, required=True, help="Output file shape grid, additional indicator soil/vegetation height (vector).")
    parser.add_argument("-cld", "--class_label_dico",nargs="+",default={}, help = "NB: to inquire if option stats_all_count is enable, dictionary of correspondence class Mandatory if all or count is un col_to_add_list. Ex: 0:Nuage 63:Vegetation 127:Bati 191:Voirie 255:Eau", type=str,required=False)
    parser.add_argument('-epsg','--epsg', default=2154,help="EPSG code projection.", type=int, required=False)
    parser.add_argument('-raf','--format_raster', default="GTiff", help="Option : Format output image, by default : GTiff (GTiff, HFA...)", type=str, required=False)
    parser.add_argument('-vef','--format_vector', default="ESRI Shapefile",help="Format of the output file.", type=str, required=False)
    parser.add_argument('-rae','--extension_raster', default=".tif", help="Option : Extension file for image raster. By default : '.tif'", type=str, required=False)
    parser.add_argument('-vee','--extension_vector',default=".shp",help="Option : Extension file for vector. By default : '.shp'", type=str, required=False)
    parser.add_argument('-log', '--path_time_log',default="",help="Name of log", type=str, required=False)
    parser.add_argument('-sav', '--save_results_intermediate', action='store_true', default=False, required=False, help="Save or delete intermediate result after the process. By default, False")
    parser.add_argument('-now', '--overwrite', action='store_false', default=True, required=False, help="Overwrite files with same names. By default, True")
    parser.add_argument('-debug', '--debug', default=3, type=int, required=False, help="Option : Value of level debug trace, default : 3")
    args = displayIHM(gui, parser)

    # Récupération des images d'entrées
    if args.classif_input != None:
        classif_input = args.classif_input

    if args.mnh_input != None:
        mnh_input = args.mnh_input

    # Récupération du vecteur d'entrée de grille
    if args.vector_grid_input != None:
        vector_grid_input = args.vector_grid_input

    # Récupération du vecteur de sortie de grille
    if args.vector_grid_output != None:
        vector_grid_output = args.vector_grid_output

    # Creation du dictionaire reliant les classes à leur label
    class_label_dico = {}
    if args.class_label_dico != None and args.class_label_dico != {}:
        for tmp_txt_class in args.class_label_dico:
            class_label_list = tmp_txt_class.split(':')
            class_label_dico[int(class_label_list[0])] = class_label_list[1]

    # Paramettre de projection
    if args.epsg != None:
        epsg = args.epsg

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

    # Récupération de l'option niveau de debug
    if args.debug!= None:
        global debug
        debug = args.debug

    if debug >= 3:
        print(bold + green + "Calcul d'indicateurs supplémentaires pour les LCZ :" + endC)
        print(cyan + "OcsIndicators : " + endC + "classif_input : " + str(classif_input) + endC)
        print(cyan + "OcsIndicators : " + endC + "mnh_input : " + str(mnh_input) + endC)
        print(cyan + "OcsIndicators : " + endC + "vector_grid_input : " + str(vector_grid_input) + endC)
        print(cyan + "OcsIndicators : " + endC + "vector_grid_output : " + str(vector_grid_output) + endC)
        print(cyan + "OcsIndicators : " + endC + "class_label_dico : " + str(class_label_dico) + endC)
        print(cyan + "OcsIndicators : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "OcsIndicators : " + endC + "format_raster : " + str(format_raster) + endC)
        print(cyan + "OcsIndicators : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "OcsIndicators : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "OcsIndicators : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "OcsIndicators : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "OcsIndicators : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "OcsIndicators : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "OcsIndicators : " + endC + "debug : " + str(debug) + endC)

    # EXECUTION DE LA FONCTION
    # Si les dossiers de sortie n'existent pas, on les crées
    if not os.path.exists(os.path.dirname(vector_grid_output)):
        os.makedirs(os.path.dirname(vector_grid_output))

    # Execution de la fonction pour un vecteur grille
    occupationIndicator(classif_input, mnh_input, vector_grid_input, vector_grid_output, class_label_dico, epsg, path_time_log, format_raster, format_vector, extension_raster, extension_vector, save_results_intermediate, overwrite)

if __name__ == '__main__':
    main(gui=False)

