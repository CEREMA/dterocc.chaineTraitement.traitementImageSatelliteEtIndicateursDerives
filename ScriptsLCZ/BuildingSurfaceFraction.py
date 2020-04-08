#!/usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerSO/DALETT/SCGSI  All rights reserved.                                                                            #
#############################################################################################################################################

from __future__ import print_function
import os, sys, argparse, shutil
from Lib_log import timeLine
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_file import removeVectorFile
from CrossingVectorRaster import statisticsVectorRaster

debug = 3

####################################################################################################
# FONCTION buildingSurfaceFraction()                                                               #
####################################################################################################
# ROLE :
#     Calcul de l'indicateur LCZ pourcentage de surface bâtie
#
# ENTREES DE LA FONCTION :
#     grid_input : fichier de maillage en entrée
#     grid_output : fichier de maillage en sortie
#     classif_input : fichier raster de l'occupation du sol en entrée
#     path_time_log : fichier log de sortie
#     format_vector : format du fichier vecteur. Optionnel, par default : 'ESRI Shapefile'
#     extension_raster : extension des fichiers raster de sortie, par defaut = '.tif'
#     save_results_intermediate : fichiers de sorties intermédiaires nettoyés, par défaut = False
#     overwrite : écrase si un fichier existant a le même nom qu'un fichier de sortie, par défaut = True
#
# SORTIES DE LA FONCTION :
#     N.A

def buildingSurfaceFraction(grid_input, grid_output, classif_input, path_time_log, format_vector='ESRI Shapefile', extension_raster=".tif", save_results_intermediate=False, overwrite=True):

    print(bold + yellow + "Début du calcul de l'indicateur Building Surface Fraction." + endC + "\n")
    timeLine(path_time_log, "Début du calcul de l'indicateur Building Surface Fraction : ")

    if debug >= 3 :
        print(bold + green + "buildingSurfaceFraction() : Variables dans la fonction" + endC)
        print(cyan + "buildingSurfaceFraction() : " + endC + "grid_input : " + str(grid_input) + endC)
        print(cyan + "buildingSurfaceFraction() : " + endC + "grid_output : " + str(grid_output) + endC)
        print(cyan + "buildingSurfaceFraction() : " + endC + "classif_input : " + str(classif_input) + endC)
        print(cyan + "buildingSurfaceFraction() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "buildingSurfaceFraction() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "buildingSurfaceFraction() : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "buildingSurfaceFraction() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "buildingSurfaceFraction() : " + endC + "overwrite : " + str(overwrite) + endC)

    if not os.path.exists(grid_output) or overwrite:

        ############################################
        ### Préparation générale des traitements ###
        ############################################

        if os.path.exists(grid_output):
            removeVectorFile(grid_output)

        temp_path = os.path.dirname(grid_output) + os.sep + "BuildingSurfaceFraction"
        building_raster = temp_path + os.sep + "building" + extension_raster

        if os.path.exists(temp_path):
            shutil.rmtree(temp_path)
        os.makedirs(temp_path)

        ##############################
        ### Calcul de l'indicateur ###
        ##############################

        print(bold + cyan + "Création de la carte de bâti :" + endC)
        timeLine(path_time_log, "    Création de la carte de bâti : ")

        command = "otbcli_BandMath -il %s -out %s uint8 -exp 'im1b1==11100 ? 1 : 99'" % (classif_input, building_raster)
        if debug >= 3 :
            print(command)
        exit_code = os.system(command)
        if exit_code != 0:
            print(command)
            print(cyan + "buildingSurfaceFraction() : " + bold + red + "!!! Une erreur c'est produite au cours de la commande otbcli_BandMath : " + command + ". Voir message d'erreur." + endC, file=sys.stderr)
            raise

        print(bold + cyan + "Récupération de Building Surface Fraction par maille :" + endC)
        timeLine(path_time_log, "    Récupération de Building Surface Fraction par maille : ")
        statisticsVectorRaster(building_raster, grid_input, grid_output, 1, True, False, False, [], [], {99:'NonBati', 1:'Bati'}, path_time_log, True, format_vector, save_results_intermediate, overwrite)
        print("\n")

        ##########################################
        ### Nettoyage des fichiers temporaires ###
        ##########################################

        if not save_results_intermediate:
            if os.path.exists(temp_path):
                shutil.rmtree(temp_path)

    else:
        print(bold + magenta + "Le calcul du Building Surface Fraction a déjà eu lieu." + endC)
        print("\n")

    print(bold + yellow + "Fin du calcul de l'indicateur Building Surface Fraction." + endC + "\n")
    timeLine(path_time_log, "Fin du calcul de l'indicateur Building Surface Fraction : ")

    return

#############################################################################################################################
################################################## Mise en place du parser ##################################################
#############################################################################################################################

def main(gui=False):
    parser = argparse.ArgumentParser(prog = "Calcul du pourcentage de surface batie (Building Surface Fraction)",
    description = """Calcul de l'indicateur LCZ pourcentage de surface batie (Building Surface Fraction) :
    Exemple : python /home/scgsi/Documents/ChaineTraitement/ScriptsLCZ/BuildingSurfaceFraction.py
                        -in  /mnt/Donnees_Etudes/10_Agents/Benjamin/LCZ/Nancy/UrbanAtlas.shp
                        -out /mnt/Donnees_Etudes/10_Agents/Benjamin/LCZ/Nancy/BuildingSurfaceFraction.shp
                        -cla /mnt/Donnees_Etudes/10_Agents/Benjamin/LCZ/Nancy/Classif.tif""")

    parser.add_argument('-in', '--grid_input', default="", type=str, required=True, help="Fichier de maillage en entree (vecteur).")
    parser.add_argument('-out', '--grid_output', default="", type=str, required=True, help="Fichier de maillage en sortie, avec la valeur moyenne de Building Surface Fraction par maille (vecteur).")
    parser.add_argument('-cla', '--classif_input', default="", type=str, required=True, help="Fichier raster de l'occupation du sol en entree (raster).")
    parser.add_argument('-vef','--format_vector',default="ESRI Shapefile",help="Option : Vector format. By default : ESRI Shapefile", type=str, required=False)
    parser.add_argument('-rae','--extension_raster', default=".tif", help="Option : Extension file for image raster. By default : '.tif'", type=str, required=False)
    parser.add_argument('-log', '--path_time_log', default="/home/scgsi/Bureau/logLCZ.txt", type=str, required=False, help="Name of log")
    parser.add_argument('-sav', '--save_results_intermediate', action='store_true', default=False, required=False, help="Save or delete intermediate result after the process. By default, False")
    parser.add_argument('-now', '--overwrite', action='store_false', default=True, required=False, help="Overwrite files with same names. By default, True")
    parser.add_argument('-debug', '--debug', default=3, type=int, required=False, help="Option : Value of level debug trace, default : 3")
    args = displayIHM(gui, parser)

    if args.grid_input != None:
        grid_input = args.grid_input
    if args.grid_output != None:
        grid_output = args.grid_output
    if args.classif_input != None:
        classif_input = args.classif_input

    # Récupération du nom du format des fichiers vecteur
    if args.format_vector != None:
        format_vector = args.format_vector

    # Paramètre de l'extension des images rasters
    if args.extension_raster != None:
        extension_raster = args.extension_raster

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
        print(bold + green + "Calcul du pourcentage de surface bâtie :" + endC)
        print(cyan + "BuildingSurfaceFraction : " + endC + "grid_input : " + str(grid_input) + endC)
        print(cyan + "BuildingSurfaceFraction : " + endC + "grid_output : " + str(grid_output) + endC)
        print(cyan + "BuildingSurfaceFraction : " + endC + "classif_input : " + str(classif_input) + endC)
        print(cyan + "BuildingSurfaceFraction : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "BuildingSurfaceFraction : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "BuildingSurfaceFraction : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "BuildingSurfaceFraction : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "BuildingSurfaceFraction : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "BuildingSurfaceFraction : " + endC + "debug : " + str(debug) + endC)

    if not os.path.exists(os.path.dirname(grid_output)):
        os.makedirs(os.path.dirname(grid_output))

    buildingSurfaceFraction(grid_input, grid_output, classif_input, path_time_log, format_vector, extension_raster, save_results_intermediate, overwrite)

if __name__ == '__main__':
    main(gui=False)

