#!/usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerSO/DALETT/SCGSI  All rights reserved.                                                                            #
#############################################################################################################################################

from __future__ import print_function
import os, sys, shutil, argparse
from Lib_log import timeLine
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_vector import renameFieldsVector
from Lib_raster import getProjectionImage
from Lib_file import removeVectorFile
from CrossingVectorRaster import statisticsVectorRaster

debug = 3

####################################################################################################
# FONCTION computeRoughness()                                                                      #
####################################################################################################
# ROLE :
#     Calcul de l'indicateur LCZ hauteur des élements de rugosité
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

def computeRoughness(classif_input, mnh_input, vector_grid_input, vector_grid_output, class_label_dico, epsg, path_time_log, format_raster='GTiff', format_vector='ESRI Shapefile', extension_raster=".tif", extension_vector=".shp", save_results_intermediate=False, overwrite=True):

    # Constante
    FIELD_NAME_HRE = "mean_h"

    # Mise à jour du Log
    timeLine(path_time_log, "Début du calcul de l'indicateur Height of Roughness Elements par OCS et MNT starting : ")
    print(cyan + "computeRoughness() : " + endC + "Début du calcul de l'indicateur Height of Roughness Elements par OCS et MNT." + endC + "\n")

    if debug >= 3:
        print(bold + green + "computeRoughness() : Variables dans la fonction" + endC)
        print(cyan + "computeRoughness() : " + endC + "classif_input : " + str(classif_input) + endC)
        print(cyan + "computeRoughness() : " + endC + "mnh_input : " + str(mnh_input) + endC)
        print(cyan + "computeRoughness() : " + endC + "vector_grid_input : " + str(vector_grid_input) + endC)
        print(cyan + "computeRoughness() : " + endC + "vector_grid_output : " + str(vector_grid_output) + endC)
        print(cyan + "computeRoughness() : " + endC + "class_label_dico : " + str(class_label_dico) + endC)
        print(cyan + "computeRoughness() : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "computeRoughness() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "computeRoughness() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "computeRoughness() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "computeRoughness() : " + endC + "overwrite : " + str(overwrite) + endC)


    # Test si le vecteur de sortie existe déjà et si il doit être écrasés
    check = os.path.isfile(vector_grid_output)

    if check and not overwrite: # Si le fichier de sortie existent deja et que overwrite n'est pas activé
        print(cyan + "computeRoughness() : " + bold + yellow + "Le calcul de Roughness par OCS et MNT a déjà eu lieu." + endC + "\n")
        print(cyan + "computeRoughness() : " + bold + yellow + "Grid vector output : " + vector_grid_output + " already exists and will not be created again." + endC)
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
        #key_class_label_list = list(class_label_dico.keys())

        # Préparation des fichiers temporaires
        temp_path = os.path.dirname(vector_grid_output) + os.sep + "TEMP_HRE"

        # Nettoyage du repertoire temporaire si il existe
        if os.path.exists(temp_path):
            shutil.rmtree(temp_path)
        os.makedirs(temp_path)

        buit_height_temp = temp_path + os.sep + "hauteur_bati_temp" + extension_raster
        buit_height = temp_path + os.sep + "hauteur_bati" + extension_raster

        ##############################
        ### Calcul de l'indicateur ###
        ##############################

        # Récupération de la hauteur du bati
        #code_bati = [c for c,v in class_label_dico.items() if v=="bati"][0]
        code_bati = list(class_label_dico.keys())[list(class_label_dico.values()).index("bati")]
        command = "otbcli_BandMath -il %s %s -out %s float -exp 'im1b1==%s ? im2b1 : 0'" %(classif_input, mnh_input, buit_height_temp, str(code_bati))
        exit_code = os.system(command)
        if exit_code != 0:
            print(command)
            print(cyan + "computeRoughness() : " + bold + red + "!!! Une erreur c'est produite au cours de la commande otbcli_BandMath : " + command + ". Voir message d'erreur." + endC, file=sys.stderr)
            raise

        command = "gdal_translate -a_srs EPSG:%s -a_nodata 0 -of %s %s %s" %(str(epsg_proj), format_raster, buit_height_temp, buit_height)
        exit_code = os.system(command)
        if exit_code != 0:
            print(command)
            print(cyan + "computeRoughness() : " + bold + red + "!!! Une erreur c'est produite au cours de la comande : gdal_translate : " + command + ". Voir message d'erreur." + endC, file=sys.stderr)
            raise

        # Récupération de la hauteur moyenne du bati de chaque maille
        statisticsVectorRaster(buit_height, vector_grid_input, vector_grid_output, 1, False, False, True, ["min", "max", "median", "sum", "std", "unique", "range"], [], {}, path_time_log, True, format_vector, save_results_intermediate, overwrite)

        # Renomer le champ 'mean' en FIELD_NAME_HRE
        renameFieldsVector(vector_grid_output, ['mean'], [FIELD_NAME_HRE], format_vector)

        ##########################################
        ### Nettoyage des fichiers temporaires ###
        ##########################################
        if not save_results_intermediate:
            if os.path.exists(temp_path):
                shutil.rmtree(temp_path)

    print(cyan + "computeRoughness() : " + endC + "Fin du calcul de l'indicateur Height of Roughness Elements par OCS et MNT." + endC + "\n")
    timeLine(path_time_log, "Fin du calcul de l'indicateur Height of Roughness Elements par OCS et MNT  ending : ")

    return

#############################################################################################################################
################################################## Mise en place du parser ##################################################
#############################################################################################################################

def main(gui=False):
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, prog="RoughnessByOcsAndMnh", description="\
    Info : Calculation Height of Roughness Elements use OCS input and MNH. \n\
    Objectif : Calcul de la hauteur des elements de rugosite avec données OCS et MNH pour les LCZ. \n\
    Example : python RoughnessByOcsAndMnh.py -i ../Classif_OCS.tif \n\
                                    -mnh  ../Nancy/MNH.tif \n\
                                    -v ../UrbanAtlas2012_cleaned.shp \n\
                                    -o ../Nancy/occupationIndicator.shp \n\
                                    -cld 11100:bati 11200:route 12200:eau 13000:solnu 20000:cegetation \n\
                                    -epsg 2154 \n\
                                    -log ../ImagesTestChaine/APTV_05/fichierTestLog.txt")

    parser.add_argument('-i', '--classif_input', default="", type=str, required=True, help="Input file Modele classification OCS (raster).")
    parser.add_argument('-mnh', '--mnh_input', default="", type=str, required=True, help="Input file Modele Numerique de Hauteur(raster).")
    parser.add_argument('-v', '--vector_grid_input', default="", type=str, required=True, help="Input file shape grid (vector).")
    parser.add_argument('-o', '--vector_grid_output', default="", type=str, required=True, help="Output file shape grid, additional indicator soil/vegetation height (vector).")
    parser.add_argument("-cld", "--class_label_dico",nargs="+",default={}, help = "Dictionary of correspondence class Mandatory. Ex: 11100:bati", type=str,required=False)
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
            class_label_dico[int(class_label_list[0])] = class_label_list[1].lower()

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
        print(bold + green + "Calcul de la hauteur des élements de rugosité :" + endC)
        print(cyan + "RoughnessByOcsAndMnh : " + endC + "classif_input : " + str(classif_input) + endC)
        print(cyan + "RoughnessByOcsAndMnh : " + endC + "mnh_input : " + str(mnh_input) + endC)
        print(cyan + "RoughnessByOcsAndMnh : " + endC + "vector_grid_input : " + str(vector_grid_input) + endC)
        print(cyan + "RoughnessByOcsAndMnh : " + endC + "vector_grid_output : " + str(vector_grid_output) + endC)
        print(cyan + "RoughnessByOcsAndMnh : " + endC + "class_label_dico : " + str(class_label_dico) + endC)
        print(cyan + "RoughnessByOcsAndMnh : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "RoughnessByOcsAndMnh : " + endC + "format_raster : " + str(format_raster) + endC)
        print(cyan + "RoughnessByOcsAndMnh : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "RoughnessByOcsAndMnh : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "RoughnessByOcsAndMnh : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "RoughnessByOcsAndMnh : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "RoughnessByOcsAndMnh : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "RoughnessByOcsAndMnh : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "RoughnessByOcsAndMnh : " + endC + "debug : " + str(debug) + endC)

    # EXECUTION DE LA FONCTION
    # Si les dossiers de sortie n'existent pas, on les crées
    if not os.path.exists(os.path.dirname(vector_grid_output)):
        os.makedirs(os.path.dirname(vector_grid_output))

    computeRoughness(classif_input, mnh_input, vector_grid_input, vector_grid_output, class_label_dico, epsg, path_time_log, format_raster, format_vector, extension_raster, extension_vector, save_results_intermediate, overwrite)

if __name__ == '__main__':
    main(gui=False)

