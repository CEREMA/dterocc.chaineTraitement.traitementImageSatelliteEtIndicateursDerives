#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT QUI REDECOUPE UNE LISTE DE RASTEUR et de VECTEURS PAR UN VECTEUR D'EMPRISE                                                         #
#                                                                                                                                           #
#############################################################################################################################################
"""
Nom de l'objet : VectorRasterCutting.py
Description :
-------------
Objectif : Découper les fichier rasteurs et vecteurs finaux de la classificationsd'échantillons
Rq : utilisation des OTB Applications : na

Date de creation : 23/05/2016
----------
Histoire :
----------
Origine : Nouveau
23/05/2016 : Création
-----------------------------------------------------------------------------------------------------
Modifications :

------------------------------------------------------
A Reflechir/A faire :

"""

from __future__ import print_function
import os,sys,glob,argparse,string
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_log import timeLine
from Lib_raster import getPixelWidthXYImage, getProjectionImage, getEmpriseImage, roundPixelEmpriseSize
from Lib_vector import getEmpriseVector, bufferVector, cutoutVectors, createEmpriseShapeReduced
from Lib_file import removeVectorFile, removeFile
from math import *

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 3

###########################################################################################################################################
# FONCTION cutRasterImages()                                                                                                              #
###########################################################################################################################################
def cutRasterImages(images_input_list, vector_cut, images_output_list, buffer_size, round_pixel_size, epsg, no_data_value, resampling_methode, z_compress, path_time_log, format_raster='GTiff', format_vector='ESRI Shapefile', extension_raster=".tif", extension_vector=".shp", save_results_intermediate=False, overwrite=True) :
    """
    # ROLE:
    #     remplace par 0 les pixels d'une image places hors de vecteurs de decoupage et par 1 les pixels a l'interieur des polygones
    #     Compléments sur la fonction rasterization : http://www.orfeo-toolbox.org/CookBook/CookBooksu71.html#x99-2770005.2.2
    #
    # ENTREES DE LA FONCTION :
    #     images_input_list : les images d'entrée qui seront découpées
    #     vector_cut: le vecteur pour le découpage des images et des vecteurs
    #     images_output_list : les images de sorties découpées
    #     buffer_size : valeur du buffer pour la decoupe des images
    #     round_pixel_size : valeur de l'arrondi de la taille des pixels en X et Y (en metre) pour le recalage si à 0 la valeur est lu dans l'image source
    #     epsg : EPSG des fichiers de sortie utilisation de la valeur du fichier d'entrée si la valeur = 0
    #     no_data_value : Valeur des pixels sans données pour les rasters
    #     resampling_methode : Option : Definie la methode de resampling
    #     z_compress :  Option : Flag si True demande d'une version compressée et décompée pour les rasters
    #     path_time_log : le fichier de log de sortie
    #     format_raster : Format de l'image de sortie, par défaut : GTiff
    #     format_vector : format du fichier vecteur. Optionnel, par default : 'ESRI Shapefile'
    #     extension_raster : extension des fichiers raster de sortie, par defaut = '.tif'
    #     extension_vector : extension du fichier vecteur de sortie, par defaut = '.shp'
    #     save_results_intermediate : fichiers de sorties intermediaires nettoyees, par defaut = False
    #     overwrite : écrase si un fichier existant a le même nom qu'un fichier de sortie, par defaut a True
    #
    # SORTIES DE LA FONCTION :
    #    un masque binaire par vecteur d'entrée compatible avec l'image de référence
    #
    """

    # Mise à jour du Log
    starting_event = "cutRasterImages() : Cutting rasters and vector starting : "
    timeLine(path_time_log,starting_event)

    print(endC)
    print(bold + green + "## START : CUTTING IMAGES" + endC)
    print(endC)

    if debug >= 2:
        print(bold + green + "cutRasterImages() : Variables dans la fonction" + endC)
        print(cyan + "cutRasterImages() : " + endC + "images_input_list : " + str(images_input_list) + endC)
        print(cyan + "cutRasterImages() : " + endC + "vector_cut : " + str(vector_cut) + endC)
        print(cyan + "cutRasterImages() : " + endC + "images_output_list : " + str(images_output_list) + endC)
        print(cyan + "cutRasterImages() : " + endC + "buffer_size : " + str(buffer_size) + endC)
        print(cyan + "cutRasterImages() : " + endC + "round_pixel_size : " + str(round_pixel_size) + endC)
        print(cyan + "cutRasterImages() : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "cutRasterImages() : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "cutRasterImages() : " + endC + "resampling_methode : " + str(resampling_methode))
        print(cyan + "cutRasterImages() : " + endC + "z_compress : " + str(z_compress))
        print(cyan + "cutRasterImages() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "cutRasterImages() : " + endC + "format_raster : " + str(format_raster) + endC)
        print(cyan + "cutRasterImages() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "cutRasterImages() : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "cutRasterImages() : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "cutRasterImages() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "cutRasterImages() : " + endC + "overwrite : " + str(overwrite) + endC)

    # PREPARATION DES FICHIERS INTERMEDIAIRES
    BUFF_SUFFIX = "_buf"
    CUT_SUFFIX = "_cut"
    COMPRESS_SUFFIX = "_compress"

    EPSG_DEFAULT = 2154

    if buffer_size > 0 and len(images_input_list) > 0:  # Cas le vecteur de découpe des rasteurs est bufferisé
        vector_buf_for_raster_cut = os.path.splitext(vector_cut)[0] + BUFF_SUFFIX + str(int(round(buffer_size,0))) + 'm' + extension_vector
        if debug >= 3:
            print("vector_buf_for_raster_cut : " + str(vector_buf_for_raster_cut) + endC)

        # Test si le vecteur decoupe existe déjà et si il doit être écrasés
        check = os.path.isfile(vector_buf_for_raster_cut)

        if check and not overwrite: # Si le fichier existe deja et que overwrite n'est pas activé
            print(bold + yellow + "File vector cutting : " + vector_buf_for_raster_cut + " already exists and will not be created again." + endC)
        else :
            if check:
                try:
                    removeVectorFile(vector_buf_for_raster_cut)
                except Exception:
                    pass # si le fichier n'existe pas, il ne peut pas être supprimé : cette étape est ignorée

            # Création du vecteur de découpe bufferisé
            bufferVector(vector_cut, vector_buf_for_raster_cut, buffer_size, "", 1.0, 10, format_vector)

    else : # Cas le vecteur de découpe des rasteurs n'est pas bufferisé idem vecteur de découpe que les vecteurs
        vector_buf_for_raster_cut = vector_cut


    # DECOUPAGE DES RASTEURS PAR LE VECTEUR DE DECOUPE

    # Pour tous les fichiers raster à découpper
    for index_raster in range (len(images_input_list)) :

        # Préparation des rasters de travail d'entrée et de sortie
        raster_input = images_input_list[index_raster]
        raster_output = images_output_list[index_raster]
        raster_output_compress = os.path.splitext(raster_output)[0] + COMPRESS_SUFFIX + extension_raster
        vector_cut_temp = os.path.splitext(raster_output)[0] + CUT_SUFFIX + extension_vector

        if debug >= 1:
            print("\n")
            print(cyan + "cutRasterImages() : " + endC + bold + green + "Découpe fichier raster : " + endC  + str(raster_input) + endC)

        # Récuperation de l'emprise de l'image
        ima_xmin, ima_xmax, ima_ymin, ima_ymax = getEmpriseImage(raster_input)

        # Recuperation de la valeur de l'arrondi de la taille des pixels en X et Y si non définie
        if round_pixel_size == 0.0 and os.path.isfile(raster_input) :
            # Identification de la tailles de pixels en x et en y
            pixel_size_x, pixel_size_y = getPixelWidthXYImage(raster_input)
            round_pixel_size = abs(pixel_size_x)
        else :
            pixel_size_x = round_pixel_size
            pixel_size_y = round_pixel_size

        # Préparation du vecteur de découpe temporaire
        createEmpriseShapeReduced(vector_buf_for_raster_cut, ima_xmin, ima_ymin, ima_xmax, ima_ymax, vector_cut_temp, format_vector)

        # Identification de l'emprise de vecteur de découpe
        empr_xmin,empr_xmax,empr_ymin,empr_ymax = getEmpriseVector(vector_cut_temp, format_vector)

        # Calculer l'emprise arrondi
        xmin, xmax, ymin, ymax = roundPixelEmpriseSize(pixel_size_x, pixel_size_y, empr_xmin, empr_xmax, empr_ymin, empr_ymax)

        # Trouver l'emprise optimale
        opt_xmin = xmin
        opt_xmax = xmax
        opt_ymin = ymin
        opt_ymax = ymax

        if ima_xmin > xmin :
            opt_xmin = ima_xmin
        if ima_xmax < xmax :
            opt_xmax = ima_xmax
        if ima_ymin > ymin :
            opt_ymin = ima_ymin
        if ima_ymax < ymax :
            opt_ymax = ima_ymax

        # Récuperation de la projection de l'image
        if epsg == 0:
            epsg_proj, _ = getProjectionImage(raster_input)
        else :
            epsg_proj = epsg
        if epsg_proj == 0:
            epsg_proj = EPSG_DEFAULT

        if debug >= 3:
            print("epsg : " + str(epsg_proj) + endC)
            print("\n")


        # Test si le rasteur de sortie existe déjà et si il doit être écrasés
        check = os.path.isfile(raster_output)

        if check and not overwrite: # Si le fichier existe deja et que overwrite n'est pas activé
            print(bold + yellow + "File raster output : " + raster_output + " already exists and will not be created again." + endC)
        else :
            if check:
                try:
                    removeFile(raster_output)
                except Exception:
                    pass # si le fichier n'existe pas, il ne peut pas être supprimé : cette étape est ignorée


            # Commande de découpe raster
            command = 'gdalwarp -t_srs EPSG:' + str(epsg_proj) + ' -te ' +  str(opt_xmin) + ' ' + str(opt_ymin)  + ' ' + str(opt_xmax) + ' ' + str(opt_ymax) + ' -tap -multi -wo "NUM_THREADS=ALL_CPUS" -dstnodata ' + str(no_data_value)  + ' -tr ' + str(abs(pixel_size_x)) + ' ' + str(abs(pixel_size_y)) + ' -cutline ' + vector_cut_temp + ' -of ' + format_raster + ' ' + raster_input + ' ' + raster_output

            if resampling_methode != "" :
                command += " -r " + resampling_methode

            if overwrite:
                command += ' -overwrite'

            if debug >=2:
                print(bold + green + "Command : " + command + endC)
            exit_code = os.system(command)
            if exit_code != 0:
                print(cyan + "cutRasterImages() : " + bold + red + "!!! Une erreur c'est produite au cours du decoupage de l'image : " + raster_input + ". Voir message d'erreur." + endC, file=sys.stderr)
                raise
            if debug >=2:
                print(cyan + "cutRasterImages() : " + bold + green + "DECOUPAGE DU RASTER %s AVEC LE VECTEUR %s" %(raster_input, vector_buf_for_raster_cut) + endC)
                print(command)

            if z_compress:
                # Commande de découpe raster et compression
                command = 'gdalwarp -t_srs EPSG:' + str(epsg_proj) + ' -te ' +  str(opt_xmin) + ' ' + str(opt_ymin)  + ' ' + str(opt_xmax) + ' ' + str(opt_ymax) + ' -tap -multi -wo "NUM_THREADS=ALL_CPUS" -dstnodata ' + str(no_data_value)  + ' -tr ' + str(abs(pixel_size_x)) + ' ' + str(abs(pixel_size_y)) + ' -co "COMPRESS=DEFLATE" -co "PREDICTOR=2" -co "ZLEVEL=9" -cutline ' + vector_cut_temp + ' -of ' + format_raster + ' ' + raster_input + ' ' + raster_output_compress

                if resampling_methode != "" :
                    command += ' -r ' + resampling_methode

                if overwrite:
                    command += ' -overwrite'

                if debug >=2:
                    print(bold + green + "Command : " + command + endC)
                exit_code = os.system(command)
                if exit_code != 0:
                    print(cyan + "cutRasterImages() : " + bold + red + "!!! Une erreur c'est produite au cours du decoupage de l'image : " + raster_input + ". Voir message d'erreur." + endC, file=sys.stderr)
                    raise
                if debug >=2:
                    print(cyan + "cutRasterImages() : " + bold + green + "DECOUPAGE ET COMPRESSION DU RASTER %s AVEC LE VECTEUR %s" %(raster_input, vector_buf_for_raster_cut) + endC)
                    print(command)

        # Suppression des fichiers intermédiaires
        removeVectorFile(vector_cut_temp)

    # SUPPRESIONS FICHIERS INTERMEDIAIRES INUTILES

    # Suppression des fichiers intermédiaires
    if not save_results_intermediate and os.path.isfile(vector_buf_for_raster_cut) and vector_buf_for_raster_cut != vector_cut:
        removeVectorFile(vector_buf_for_raster_cut)

    print(endC)
    print(bold + green + "## END : CUTTING IMAGES" + endC)
    print(endC)

    # Mise à jour du Log
    ending_event = "cutRasterImages() : Cutting rasters and vector  ending : "
    timeLine(path_time_log,ending_event)

    return

###########################################################################################################################################
# MISE EN PLACE DU PARSER                                                                                                                 #
###########################################################################################################################################

# Code executé seulement dans le cas ou le script est lancé depuis une ligne de commande
# Il n'est pas executé lors d'un import VectorRasterCutting.py
# Exemple de lancement en ligne de commande:
# python VectorRasterCutting.py -il /mnt/Data/gilles.fouvet/RA/Haute-Savoie_SansTunnel/haute_savoie_usage_sans_tunnels.tif /mnt/Data/gilles.fouvet/RA/Haute-Savoie_500m/Global/Resultats/Raster/Haute_Savoie_Couverture_Apres_PT_Directs_et_Indirects.tif /mnt/Data/gilles.fouvet/RA/Haute-Savoie_200m/Global/Resultats/Raster/Haute_Savoie_Couverture_Apres_PT_Directs_et_Indirects_200m2.tif /mnt/Data/gilles.fouvet/RA/Haute-Savoie_500m/Global/Resultats/Raster/Haute-Savoie_Couverture_Apres_PT_Directs_et_Indirects_500m2.tif -vl  /mnt/Data/gilles.fouvet/RA/Haute-Savoie_500m/Global/Resultats/Vecteur/Sauvegarde_500m2/Haute-Savoie_Couverture_Apres_PT_Directs_et_Indirects_clnd_500m2.shp /mnt/Data/gilles.fouvet/RA/Haute-Savoie_200m/Global/Resultats/Vecteur/Sauvegarde_200m2/Haute-Savoie_Couverture_Apres_PT_Directs_et_Indirects_clnd_200m2.shp -c /mnt/Data/gilles.fouvet/RA/Haute-Savoie/Global/Preparation/Study_Boundaries/DEP74.SHP -iol /mnt/Data/gilles.fouvet/RA/Haute-Savoie_SansTunnel/haute_savoie_usage_sans_tunnels.tif /mnt/Data/gilles.fouvet/RA/Haute-Savoie_500m/Global/Resultats/Raster/Haute_Savoie_Couverture_Apres_PT_Directs_et_Indirects_cut.tif /mnt/Data/gilles.fouvet/RA/Haute-Savoie_200m/Global/Resultats/Raster/Haute_Savoie_Couverture_Apres_PT_Directs_et_Indirects_200m2_cut.tif /mnt/Data/gilles.fouvet/RA/Haute-Savoie_500m/Global/Resultats/Raster/Haute-Savoie_Couverture_Apres_PT_Directs_et_Indirects_500m2_cut.tif -vol /mnt/Data/gilles.fouvet/RA/Haute-Savoie_500m/Global/Resultats/Vecteur/Sauvegarde_500m2/Haute-Savoie_Couverture_Apres_PT_Directs_et_Indirects_clnd_500m2_cut.shp /mnt/Data/gilles.fouvet/RA/Haute-Savoie_200m/Global/Resultats/Vecteur/Sauvegarde_200m2/Haute-Savoie_Couverture_Apres_PT_Directs_et_Indirects_clnd_200m2_cut.shp  -b 10.0 -r 5.0 -epsg 2154 -z -log /mnt/Data/gilles.fouvet/RA/Haute-Savoie_SansTunnel/FichierHaute-Savoie.log -sav
def main(gui=False):

    # Définition des différents paramètres du parser
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,  prog="VectorRasterCutting", description="\
    Info : Cutting list of raster and vector file by vector file. \n\
    Objectif : Découper des fichiers raster et vecteurs. \n\
    Example : python VectorRasterCutting.py -il /mnt/Data/gilles.fouvet/RA/Haute-Savoie_SansTunnel/haute_savoie_usage_sans_tunnels.tif \n\
                                                /mnt/Data/gilles.fouvet/RA/Haute-Savoie_500m/Global/Resultats/Raster/Haute_Savoie_Couverture_Apres_PT_Directs_et_Indirects.tif \n\
                                                /mnt/Data/gilles.fouvet/RA/Haute-Savoie_200m/Global/Resultats/Raster/Haute_Savoie_Couverture_Apres_PT_Directs_et_Indirects_200m2.tif \n\
                                                /mnt/Data/gilles.fouvet/RA/Haute-Savoie_500m/Global/Resultats/Raster/Haute-Savoie_Couverture_Apres_PT_Directs_et_Indirects_500m2.tif  \n\
                                            -vl /mnt/Data/gilles.fouvet/RA/Haute-Savoie_500m/Global/Resultats/Vecteur/Sauvegarde_500m2/Haute-Savoie_Couverture_Apres_PT_Directs_et_Indirects_clnd_500m2.shp \n\
                                                /mnt/Data/gilles.fouvet/RA/Haute-Savoie_200m/Global/Resultats/Vecteur/Sauvegarde_200m2/Haute-Savoie_Couverture_Apres_PT_Directs_et_Indirects_clnd_200m2.shp \n\
                                            -c  /mnt/Data/gilles.fouvet/RA/Haute-Savoie/Global/Preparation/Study_Boundaries/DEP74.SHP \n\
                                            -iol /mnt/Data/gilles.fouvet/RA/Haute-Savoie_SansTunnel/haute_savoie_usage_sans_tunnels.tif \n\
                                                /mnt/Data/gilles.fouvet/RA/Haute-Savoie_500m/Global/Resultats/Raster/Haute_Savoie_Couverture_Apres_PT_Directs_et_Indirects_cut.tif \n\
                                                /mnt/Data/gilles.fouvet/RA/Haute-Savoie_200m/Global/Resultats/Raster/Haute_Savoie_Couverture_Apres_PT_Directs_et_Indirects_200m2_cut.tif \n\
                                                /mnt/Data/gilles.fouvet/RA/Haute-Savoie_500m/Global/Resultats/Raster/Haute-Savoie_Couverture_Apres_PT_Directs_et_Indirects_500m2_cut.tif  \n\
                                            -vol /mnt/Data/gilles.fouvet/RA/Haute-Savoie_500m/Global/Resultats/Vecteur/Sauvegarde_500m2/Haute-Savoie_Couverture_Apres_PT_Directs_et_Indirects_clnd_500m2_cut.shp \n\
                                                /mnt/Data/gilles.fouvet/RA/Haute-Savoie_200m/Global/Resultats/Vecteur/Sauvegarde_200m2/Haute-Savoie_Couverture_Apres_PT_Directs_et_Indirects_clnd_200m2_cut.shp \n\
                                            -b 10.0 \n\
                                            -r 5.0 \n\
                                            -epsg 2154 \n\
                                            -ndv 65535 \n\
                                            -z \n\
                                            -log /mnt/Data/gilles.fouvet/RA/Haute-Savoie_SansTunnel/FichierHaute-Savoie.log")

    parser.add_argument('-il','--images_input_list',default="",nargs="+",help="List input images to cut", type=str, required=False)
    parser.add_argument('-vl','--vectors_input_list',default="",nargs="+",help="List input vectors to cut.", type=str, required=False)
    parser.add_argument('-c','--vector_cut',default="",help="Vector input contain the vector to cut images and vectors input.", type=str, required=True)
    parser.add_argument('-iol','--images_output_list',default="",nargs="+",help="List output images cut", type=str, required=False)
    parser.add_argument('-vol','--vectors_output_list',default="",nargs="+",help="List output vectors to cut.", type=str, required=False)
    parser.add_argument('-b','--buffer_size',default=0,help="Option : Value of positive buffer in metrer , default : 0 ",type=float, required=False)
    parser.add_argument('-r','--round_pixel_size',default=0,help="Option : Value of around to dunnage if at 0 the value is read size pixel image (in metre), default : 0 ",type=float, required=False)
    parser.add_argument("-epsg",'--epsg',default=0,help="Option : Projection parameter of data if 0 used projection of raster file", type=int, required=False)
    parser.add_argument("-ndv",'--no_data_value',default=0,help="Option pixel value for raster file to no data, default : 0 ", type=int, required=False)
    parser.add_argument('-rm','--resampling_methode',default="",help="Option : Define the algo methode uses to resampling. By default : if empty (by default) not used.", type=str, required=False)
    parser.add_argument('-z', '--z_compress', action='store_true', default=False, help="Option : The rasters images cutting and compress are produced, default : False", required=False)
    parser.add_argument('-raf','--format_raster', default="GTiff", help="Option : Format output image, by default : GTiff (GTiff, HFA...)", type=str, required=False)
    parser.add_argument('-vef','--format_vector', default="ESRI Shapefile",help="Format of the output file.", type=str, required=False)
    parser.add_argument('-rae','--extension_raster', default=".tif", help="Option : Extension file for image raster. By default : '.tif'", type=str, required=False)
    parser.add_argument('-vee','--extension_vector',default=".shp",help="Option : Extension file for vector. By default : '.shp'", type=str, required=False)
    parser.add_argument('-log','--path_time_log',default="",help="Name of log", type=str, required=False)
    parser.add_argument('-sav','--save_results_inter',action='store_true',default=False,help="Save or delete intermediate result after the process. By default, False", required=False)
    parser.add_argument('-now','--overwrite',action='store_false',default=True,help="Overwrite files with same names. By default, True", required=False)
    parser.add_argument('-debug','--debug',default=3,help="Option : Value of level debug trace, default : 3 ",type=int, required=False)
    args = displayIHM(gui, parser)

    # RECUPERATION DES ARGUMENTS

    # Récupération des l'images d'entrées
    if args.images_input_list != None:
        images_input_list = args.images_input_list
        for image_input in images_input_list :
            if image_input != "" and not os.path.isfile(image_input):
                raise NameError (cyan + "VectorRasterCutting : " + bold + red  + "File %s not existe!" %(image_input) + endC)

    # Récupération des vecteurs d'entrées
    if args.vectors_input_list != None:
        vectors_input_list = args.vectors_input_list
        for vector_input in vectors_input_list :
            if vector_input != "" and not os.path.isfile(vector_input):
                raise NameError (cyan + "VectorRasterCutting : " + bold + red  + "File %s not existe!" %(vector_input) + endC)

    # Récupération du vecteur de découpe
    if args.vector_cut != None :
        vector_cut = args.vector_cut
        if not os.path.isfile(vector_cut):
            raise NameError (cyan + "VectorRasterCutting : " + bold + red  + "File %s not existe!" %(vector_cut) + endC)

    # Récupération des l'images de sorties
    if args.images_output_list != None:
        images_output_list = args.images_output_list

    # Récupération des vecteurs de sorties
    if args.vectors_output_list != None:
        vectors_output_list = args.vectors_output_list

    # Parametre du buffer
    if args.buffer_size!= None:
        buffer_size = args.buffer_size

    # Parametre de l'arrondi
    if args.round_pixel_size!= None:
        round_pixel_size = args.round_pixel_size

    # Paramettre de projection
    if args.epsg != None:
        epsg = args.epsg

    # Paramettre des no data
    if args.no_data_value != None:
        no_data_value = args.no_data_value

    # Paramètres definition de la metode de resampling
    if args.resampling_methode != None:
        resampling_methode = args.resampling_methode

    # option de compression
    if args.z_compress != None:
        z_compress = args.z_compress

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

    # Récupération de l'option de sauvegarde des fichiers temporaires
    if args.save_results_inter != None:
        save_results_intermediate = args.save_results_inter

    # Récupération de l'option écrasement
    if args.overwrite!= None:
        overwrite = args.overwrite

    # Récupération de l'option niveau de debug
    if args.debug!= None:
        global debug
        debug = args.debug

    if debug >= 3:
        print(bold + green + "VectorRasterCutting : Variables dans le parser" + endC)
        print(cyan + "VectorRasterCutting : " + endC + "images_input_list : " + str(images_input_list) + endC)
        print(cyan + "VectorRasterCutting : " + endC + "vectors_input_list : " + str(vectors_input_list) + endC)
        print(cyan + "VectorRasterCutting : " + endC + "vector_cut : " + str(vector_cut) + endC)
        print(cyan + "VectorRasterCutting : " + endC + "images_output_list : " + str(images_output_list) + endC)
        print(cyan + "VectorRasterCutting : " + endC + "vectors_output_list : " + str(vectors_output_list) + endC)
        print(cyan + "VectorRasterCutting : " + endC + "round_pixel_size : " + str(round_pixel_size) + endC)
        print(cyan + "VectorRasterCutting : " + endC + "buffer_size : " + str(buffer_size) + endC)
        print(cyan + "VectorRasterCutting : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "VectorRasterCutting : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "VectorRasterCutting : " + endC + "resampling_methode : " + str(resampling_methode) + endC)
        print(cyan + "VectorRasterCutting : " + endC + "z_compress : " + str(z_compress) + endC)
        print(cyan + "VectorRasterCutting : " + endC + "format_raster : " + str(format_raster) + endC)
        print(cyan + "VectorRasterCutting : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "VectorRasterCutting : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "VectorRasterCutting : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "VectorRasterCutting : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "VectorRasterCutting : " + endC + "save_results_inter : " + str(save_results_intermediate) + endC)
        print(cyan + "VectorRasterCutting : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "VectorRasterCutting : " + endC + "debug : " + str(debug) + endC)

    # EXECUTION DE LA FONCTION
    # Si les dossiers de sorties n'existent pas, on les crées
    for image_output in images_output_list:
        if not os.path.isdir(os.path.dirname(image_output)):
            os.makedirs(os.path.dirname(image_output))

    for vector_output in vectors_output_list:
        if not os.path.isdir(os.path.dirname(vector_output)):
            os.makedirs(os.path.dirname(vector_output))

    # Execution de la fonction de decoupe pour une liste d'image raster
    if len(images_input_list) > 0:
        cutRasterImages(images_input_list, vector_cut, images_output_list, buffer_size, round_pixel_size, epsg, no_data_value, resampling_methode, z_compress, path_time_log, format_raster, format_vector, extension_raster, extension_vector, save_results_intermediate, overwrite)

    # Execution de la fonction de decoupe pour une liste de vecteur
    if len(vectors_input_list) > 0:
        # Pour tous les fichiers vecteurs à découpper
        cutoutVectors(vector_cut, vectors_input_list, vectors_output_list, overwrite, format_vector)

# ================================================

if __name__ == '__main__':
  main(gui=False)
