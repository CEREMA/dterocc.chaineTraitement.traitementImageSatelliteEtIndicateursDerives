#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerSO/DALETT/SCGSI  All rights reserved.                                                                            #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT QUI REDECOUPE UNE LISTE DE RASTEUR (SAMPLES MACRO) PAR UN VECTEUR D'EMPRISE                                                        #
#                                                                                                                                           #
#############################################################################################################################################
'''
Nom de l'objet : MacroSamplesCutting.py
Description :
    Objectif : Découper les fichier rasteurs d'échantillons
    Rq : utilisation des OTB Applications : otbcli_Superimpose, otbcli_BandMath

Date de creation : 31/07/2014
----------
Histoire :
----------
Origine : Nouveau
07/03/2016 : Création
-----------------------------------------------------------------------------------------------------
Modifications

------------------------------------------------------
A Reflechir/A faire
 -
 -
'''

from __future__ import print_function
import os,sys,glob,argparse,string
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_log import timeLine
from Lib_raster import cutImageByVector
from Lib_file import removeFile

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 3

###########################################################################################################################################
# FONCTION cutRasterSamples()                                                                                                                  #
###########################################################################################################################################
# ROLE:
#     remplace par 0 les pixels d'une image places hors de vecteurs de decoupage et par 1 les pixels a l'interieur des polygones
#     Compléments sur la fonction rasterization : http://www.orfeo-toolbox.org/CookBook/CookBooksu71.html#x99-2770005.2.2
#
# ENTREES DE LA FONCTION :
#     image_input : l'image d'entrée qui sera découpé
#     vector_input: le vecteur pour le découpage de l'image
#     image_output : l'image de sortie découpé
#     reference_image : l'image de référence pour la superposition
#     epsg : EPSG des fichiers de sortie utilisation de la valeur du fichier d'entrée si la valeur = 0
#     no_data_value : Valeur des pixels sans données pour les rasters de sortie
#     path_time_log : le fichier de log de sortie
#     superposition : option de superposition avec l'image de référence, par defaut = False
#     format_raster : Format de l'image de sortie, par défaut : GTiff
#     format_vector : format du fichier vecteur. Optionnel, par default : 'ESRI Shapefile'
#     extension_raster : extension des fichiers raster de sortie, par defaut = '.tif'
#     save_results_intermediate : fichiers de sorties intermediaires nettoyees, par defaut = False
#     overwrite : écrase si un fichier existant a le même nom qu'un fichier de sortie, par defaut a True
#
# SORTIES DE LA FONCTION :
#    un masque binaire par vecteur d'entrée compatible avec l'image de référence
#

def cutRasterSamples(image_input, vector_input, image_output, reference_image, epsg, no_data_value, path_time_log, superposition=False, format_raster='GTiff', format_vector='ESRI Shapefile', extension_raster=".tif", save_results_intermediate=False, overwrite=True):

    # Mise à jour du Log
    starting_event = "cutRasterSamples() : Masks creation starting : "
    timeLine(path_time_log,starting_event)

    print(endC)
    print(bold + green + "## START : CUTTING IMAGE" + endC)
    print(endC)

    if debug >= 2:
        print(bold + green + "cutRasterSamples() : Variables dans la fonction" + endC)
        print(cyan + "cutRasterSamples() : " + endC + "image_input : " + str(image_input) + endC)
        print(cyan + "cutRasterSamples() : " + endC + "vector_input : " + str(vector_input) + endC)
        print(cyan + "cutRasterSamples() : " + endC + "image_output : " + str(image_output) + endC)
        print(cyan + "cutRasterSamples() : " + endC + "reference_image : " + str(reference_image) + endC)
        print(cyan + "cutRasterSamples() : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "cutRasterSamples() : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "cutRasterSamples() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "cutRasterSamples() : " + endC + "superposition : " + str(superposition) + endC)
        print(cyan + "cutRasterSamples() : " + endC + "format_raster : " + str(format_raster) + endC)
        print(cyan + "cutRasterSamples() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "cutRasterSamples() : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "cutRasterSamples() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "cutRasterSamples() : " + endC + "overwrite : " + str(overwrite) + endC)

    # ETAPE 0 : PREPARATION DES FICHIERS INTERMEDIAIRES

    SAMPLE_MASK_SUFFIX = "_mask"
    CODAGE = "uint8"

    repertory_output = os.path.dirname(image_output)

    if superposition :          # Cas où on vérifie la superposition géométrique avec l'image satellite
        output_mask_temp01 = repertory_output + os.sep + os.path.splitext(os.path.basename(image_input))[0] + SAMPLE_MASK_SUFFIX + "_temp01" + extension_raster
        output_mask_temp02 = repertory_output + os.sep + os.path.splitext(os.path.basename(image_input))[0] + SAMPLE_MASK_SUFFIX + "_temp02" + extension_raster
    else : # Cas où on ne vérifie pas la superposition géométrique avec l'image satellite
        output_mask_temp01 = image_output

    # ETAPE 1 : DECOUPAGE DU RASTEUR PAR LE VECTEUR D'EMPRISE

    # Fonction de découpe
    if not cutImageByVector(vector_input, image_input, output_mask_temp01, None, None, no_data_value, epsg, format_raster, format_vector) :
        raise NameError (cyan + "cutRasterSamples() : " + bold + red + "!!! Une erreur c'est produite au cours du decoupage de l'image : " + image_input + ". Voir message d'erreur." + endC)

    if debug >=2:
        print(cyan + "cutRasterSamples() : " + bold + green + "DECOUPAGE DU RASTER %s AVEC LE VECTEUR %s" %(image_input, vector_input) + endC)

    # ETAPE 2 : SUPERPOSITION DU FICHIER DECOUPE AVEC LE FICHIER DE REFERENCE

    if superposition :     # Cas où on vérifie la superposition géométrique
        # Commande de mise en place de la geométrie
        command = "otbcli_Superimpose -inr " + reference_image + " -inm " + output_mask_temp01 + " -out " + output_mask_temp02
        exit_code = os.system(command)
        if exit_code != 0:
            raise NameError (cyan + "cutRasterSamples() : " + bold + red + "!!! Une erreur c'est produite au cours du superimpose de l'image : " + output_mask_temp01 + ". Voir message d'erreur." + endC)

        # Commande de binarisation du nouveau masque (qui n'est plus binaire si une modification geometrique a été effectuée)
        expression_binarisation = "\"(im1b1 < %f? 0 : 1)\""%(0.5)
        command = "otbcli_BandMath -il " + output_mask_temp02 + " -out " + image_output + " " + CODAGE + " -exp " + expression_binarisation
        exit_code = os.system(command)
        if exit_code != 0:
            raise NameError (cyan + "cutRasterSamples() : " + bold + red + "!!! Une erreur c'est produite au cours de la binarisation de l'image : " + output_mask_temp02 + ". Voir message d'erreur." + endC)

        if debug >=2:
            print(cyan + "cutRasterSamples() : " + bold + green + "SUPERIMPOSE ET FICHIER BINAIRE DU FICHIER %s" %(image_input) + endC)
            print(command)

    # ETAPE 3 : SUPPRESIONS FICHIERS INTERMEDIAIRES INUTILES

    # Suppression des données intermédiaires
    if not save_results_intermediate:
        if superposition :
            removeFile(output_mask_temp01)
            removeFile(output_mask_temp02)

    print(endC)
    print(bold + green + "## END : UTTING IMAGE" + endC)
    print(endC)

    # Mise à jour du Log
    ending_event = "cutRasterSamples() : Masks creation ending : "
    timeLine(path_time_log,ending_event)

    return

###########################################################################################################################################
# MISE EN PLACE DU PARSER                                                                                                                 #
###########################################################################################################################################

# Code executé seulement dans le cas ou le script est lancé depuis une ligne de commande
# Il n'est pas executé lors d'un import MacroSamplesCutting.py
# Exemple de lancement en ligne de commande:
# python MacroSamplesCutting.py -i /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/Macro/CUB_zone_test_NE_Bati.tif -o /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/Macro/CUB_zone_test_NE_Bati_mask.tif -v /mnt/Data/gilles.fouvet/RA/Rhone/Global/Preparation/Landscapes_Boundaries/Paysage_01.shp -r mnt/Data/gilles.fouvet/RA/Rhone/Global/Images/Paysages_dep69_01_buf1Km/Paysages_dep69_01_buf1Km_20110502.tif -log /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/fichierTestLog.txt

def main(gui=False):

    # Définition des différents paramètres du parser
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,  prog="MacroSamplesCutting", description="\
    Info : Cutting macro sample mack with hold vector file. \n\
    Objectif : Découper des fichiers raster. \n\
    Example : python MacroSamplesCutting.py -i /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/Macro/CUB_zone_test_NE_Bati.tif \n\
                                     -o /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/Macro/CUB_zone_test_NE_Bati_mask.tif \n\
                                     -v /mnt/Data/gilles.fouvet/RA/Rhone/Global/Preparation/Landscapes_Boundaries/Paysage_01.shp \n\
                                     -spos \n\
                                     -r mnt/Data/gilles.fouvet/RA/Rhone/Global/Images/Paysages_dep69_01_buf1Km/Paysages_dep69_01_buf1Km_20110502.tif \n\
                                     -log /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/fichierTestLog.txt")

    parser.add_argument('-i','--image_input',default="",help="Image input to cut", type=str, required=True)
    parser.add_argument('-v','--vector_input',default="",help="Vector input contain the vector to cut image output.", type=str, required=True)
    parser.add_argument('-o','--image_output',default="",help="Mask raster image output.", type=str, required=True)
    parser.add_argument('-spos','--superposition',action='store_true',default=False,help="If asks superpose image output to reference image (reference_image must be filled). By default, False", required=False)
    parser.add_argument('-r','--reference_image',default="",help="Refence raster image.", type=str, required=False)
    parser.add_argument("-epsg",'--epsg',default=0,help="Option : Projection parameter of data if 0 used projection of raster file", type=int, required=False)
    parser.add_argument("-ndv",'--no_data_value',default=0,help="Option pixel value for raster file to no data, default : 0 ", type=int, required=False)
    parser.add_argument('-raf','--format_raster', default="GTiff", help="Option : Format output image, by default : GTiff (GTiff, HFA...)", type=str, required=False)
    parser.add_argument('-vef','--format_vector', default="ESRI Shapefile",help="Format of the output file.", type=str, required=False)
    parser.add_argument('-rae','--extension_raster', default=".tif", help="Option : Extension file for image raster. By default : '.tif'", type=str, required=False)
    parser.add_argument('-log','--path_time_log',default="",help="Name of log", type=str, required=False)
    parser.add_argument('-sav','--save_results_inter',action='store_true',default=False,help="Save or delete intermediate result after the process. By default, False", required=False)
    parser.add_argument('-now','--overwrite',action='store_false',default=True,help="Overwrite files with same names. By default, True", required=False)
    parser.add_argument('-debug','--debug',default=3,help="Option : Value of level debug trace, default : 3 ",type=int, required=False)
    args = displayIHM(gui, parser)

    # RECUPERATION DES ARGUMENTS

    # Récupération de l'image d'entrée
    if args.image_input != None:
        image_input = args.image_input
        if not os.path.isfile(image_input):
            raise NameError (cyan + "MacroSamplesCutting : " + bold + red  + "File %s not existe!" %(image_input) + endC)

    # Récupération du vecteur
    if args.vector_input != None :
        vector_input = args.vector_input
        if not os.path.isfile(vector_input):
            raise NameError (cyan + "MacroSamplesCutting : " + bold + red  + "File %s not existe!" %(vector_input) + endC)

    # Récupération du fichier de sortie
    if args.image_output != None:
        image_output = args.image_output

    # Paramettre de projection
    if args.epsg != None:
        epsg = args.epsg

    # Paramettre des no data
    if args.no_data_value != None:
        no_data_value = args.no_data_value

    # option de superposition avec l'image de référence
    if args.superposition != None:
        superposition = args.superposition

    # Récupération du fichier de référence
    if args.reference_image!= None:
        reference_image=args.reference_image
        if reference_image != "" and not os.path.isfile(reference_image):
            raise NameError (cyan + "MacroSamplesCutting : " + bold + red  + "File %s not existe!" %(reference_image) + endC)

    # Paramètre format des images de sortie
    if args.format_raster != None:
        format_raster = args.format_raster

    # Récupération du format des vecteurs de sortie
    if args.format_vector != None :
        format_vector = args.format_vector

    # Paramètre de l'extension des images rasters
    if args.extension_raster != None:
        extension_raster = args.extension_raster

    # Récupération du nom du fichier log
    if args.path_time_log!= None:
        path_time_log = args.path_time_log

    # Récupération de l'option écrasement
    if args.save_results_inter != None:
        save_results_intermediate = args.save_results_inter

    if args.overwrite!= None:
        overwrite = args.overwrite

    # Récupération de l'option niveau de debug
    if args.debug!= None:
        global debug
        debug = args.debug

    if debug >= 3:
        print(bold + green + "MacroSamplesCutting : Variables dans le parser" + endC)
        print(cyan + "MacroSamplesCutting : " + endC + "image_input : " + str(image_input) + endC)
        print(cyan + "MacroSamplesCutting : " + endC + "vector_input : " + str(vector_input) + endC)
        print(cyan + "MacroSamplesCutting : " + endC + "image_output : " + str(image_output) + endC)
        print(cyan + "MacroSamplesCutting : " + endC + "superposition : " + str(superposition) + endC)
        print(cyan + "MacroSamplesCutting : " + endC + "reference_image : " + str(reference_image) + endC)
        print(cyan + "MacroSamplesCutting : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "MacroSamplesCutting : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "MacroSamplesCutting : " + endC + "format_raster : " + str(format_raster) + endC)
        print(cyan + "MacroSamplesCutting : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "MacroSamplesCutting : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "MacroSamplesCutting : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "MacroSamplesCutting : " + endC + "save_results_inter : " + str(save_results_intermediate) + endC)
        print(cyan + "MacroSamplesCutting : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "MacroSamplesCutting : " + endC + "debug : " + str(debug) + endC)

    # EXECUTION DE LA FONCTION
    # Si le dossier de sortie n'existent pas, on le crée
    repertory_output = os.path.dirname(image_output)
    if not os.path.isdir(repertory_output):
        os.makedirs(repertory_output)

    # execution de la fonction pour une image
    cutRasterSamples(image_input, vector_input, image_output, reference_image, epsg, no_data_value, path_time_log, superposition, format_raster, format_vector, extension_raster, save_results_intermediate, overwrite)

# ================================================

if __name__ == '__main__':
  main(gui=False)
