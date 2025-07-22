#! /usr/bin/env pyt/hon
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT D'EXTRACTION DES OUVRAGES EN MER A PARTIR D'UN TRAIT DE COTE                                                                       #
#                                                                                                                                           #
#############################################################################################################################################

"""
Nom de l'objet : DetectionOuvrages.py
Description    :
----------------
Objectif   : Extrait les ouvrages en mer à partir

Date de creation : 07/06/2016
"""

from __future__ import print_function
import os, sys, argparse, shutil
from Lib_display import bold, cyan, red, green, magenta, endC, displayIHM
from Lib_log import timeLine
from Lib_operator import *
from Lib_vector import fusionVectors
from BuffersOuvrages import buffersOuvrages
from EdgeExtractionOuvrages import edgeExtractionOuvrages
from TDCSeuil import runTDCSeuil

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 3

###########################################################################################################################################
# FONCTION detectionOuvrages                                                                                                              #
###########################################################################################################################################
def detectionOuvrages(input_dico, output_dir, method, im_indice_buffers, im_indice_sobel, input_cut_vector, input_sea_points, no_data_value, path_time_log, channel_order=['Red','Green','Blue','NIR'], epsg=2154, format_raster='GTiff', format_vector="ESRI Shapefile", extension_raster=".tif", extension_vector=".shp", save_results_intermediate=True, overwrite=True):
    """
    # ROLE:
    #    Extraction des ouvrages en mer, en combinant la méthode des buffers et du filtre de Sobel, et éventuellement calcul du jet de rive par seuillage
    #
    # ENTREES DE LA FONCTION :
    #    input_dico : Dictionnaire contenant principalement les images à traiter et les seuils, l'ordre et le contenu dépend des cas d'utilisation (cf. Documentation chaine littoral)
    #    output_dir : Répertoire de sortie pour les traitements
    #    method : Méthode à utiliser pour la détection des ouvrages : b pour buffers, s pour Sobel et bs pour combinaison des 2
    #    im_indice_buffers : Booléen : présence de l'image NDVI ou autre indice calculée dans le dictionnaire (pour le calcul du jet de rive)
    #    im_indice_sobel : Booléen : présence de l'image NDWI2 ou autre indice calculée dans le dictionnaire (pour la détection des ouvrages par Sobel)
    #    input_cut_vector : Shapefile de découpe de la zone d'intérêt pour la suppression des artéfacts (bateaux, ...)
    #    input_sea_points : Shapefile de points dans la mer pour l'identification des polygones mer (pour le calcul du jet de rive)
    #    no_data_value : Valeur de  pixel du no data
    #    path_time_log : le fichier de log de sortie
    #    channel_order : identifiant des canaux de l image, exmple : {"Red":1,"Green":2,"Blue":3,"NIR":4}, defaut=[Red,Green,Blue,NIR]
    #    epsg : Code EPSG des fichiers
    #    format_raster : Format de l'image de sortie, par défaut : GTiff
    #    format_vector : Format des fichiers vecteur. Par défaut "ESRI Shapefile"
    #    extension_raster : extension des fichiers raster de sortie, par defaut = '.tif'
    #    extension_vector : extension du fichier vecteur de sortie, par defaut = '.shp'
    #    save_results_intermediate : fichiers de sorties intermediaires non nettoyées, par defaut = True
    #    overwrite : supprime ou non les fichiers existants ayant le meme nom
    #
    # SORTIES DE LA FONCTION :
    #    Le fichier contenant les ouvrages extraits
    #    Eléments modifiés aucun
    #
    """

    # Mise à jour du Log
    starting_event = "detectionOuvrages() : Select Detection Ouvrages starting : "
    timeLine(path_time_log,starting_event)

    # Affichage des paramètres
    if debug >= 3:
        print(bold + green + "Variables dans detectionOuvrages - Variables générales" + endC)
        print(cyan + "detectionOuvrages() : " + endC + "input_dico : " + str(input_dico) + endC)
        print(cyan + "detectionOuvrages() : " + endC + "output_dir : " + str(output_dir) + endC)
        print(cyan + "detectionOuvrages() : " + endC + "method : " + str(method) + endC)
        print(cyan + "detectionOuvrages() : " + endC + "im_indice_buffers : " + str(im_indice_buffers) + endC)
        print(cyan + "detectionOuvrages() : " + endC + "im_indice_sobel : " + str(im_indice_sobel) + endC)
        print(cyan + "detectionOuvrages() : " + endC + "input_cut_vector : " + str(input_cut_vector) + endC)
        print(cyan + "detectionOuvrages() : " + endC + "input_sea_points : " + str(input_sea_points) + endC)
        print(cyan + "detectionOuvrages() : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "detectionOuvrages() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "detectionOuvrages() : " + endC + "channel_order: " + str(channel_order) + endC)
        print(cyan + "detectionOuvrages() : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "detectionOuvrages() : " + endC + "format_raster : " + str(format_raster) + endC)
        print(cyan + "detectionOuvrages() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "detectionOuvrages() : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "detectionOuvrages() : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "detectionOuvrages() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "detectionOuvrages() : " + endC + "overwrite : " + str(overwrite) + endC)

    # Initialisation des constantes
    PREFIX_OUVRAGES = "Ouvrages_final_"

    # Variables
    type_extension = os.path.splitext(input_dico[0].split(":")[0])[1]

    # Création du répertoire de sortie s'il n'existe pas déjà
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    while switch(method):
        if case("b"):
            if type_extension == extension_raster:
                if im_indice_buffers:
                    if debug >= 2:
                        print(cyan + "detectionOuvrages() : " + endC + green + bold + "Cas2 : méthode buffers avec imageIndice en entrée et avec calcul TDC, en entrée : -meth b -indb -dico ImageBrute:TailleBuffer+,TailleBuffer-,ImageIndice,SeuilTerreMer -mer -d -outd" + endC)
                    for elt_dico in input_dico :
                        elt_list = elt_dico.split(":")

                        tdc = runTDCSeuil(elt_list[0]+":"+elt_list[1].split(",")[2]+","+elt_list[1].split(",")[3], output_dir, input_sea_points, input_cut_vector, "", "", "", "", "", "", "", "", 1.0,  False, no_data_value, path_time_log, channel_order, epsg, format_raster, format_vector, extension_raster, extension_vector, save_results_intermediate, overwrite)

                        buffersOuvrages(tdc, output_dir, elt_list[1].split(",")[0], elt_list[1].split(",")[1], input_cut_vector, path_time_log, format_vector, extension_vector, save_results_intermediate, overwrite)
                else:
                    if debug >= 2:
                        print(cyan + "detectionOuvrages() : " + endC + green + bold + "Cas3 : méthode buffers avec image brute en entrée et avec calcul TDC, en entrée : -meth b -dico ImageBrute:TailleBuffer+,TailleBuffer-,SeuilTerreMer -mer -d -outd" + endC)
                    for elt_dico in input_dico:
                        elt_list = elt_dico.split(":")

                        tdc = runTDCSeuil(elt_list[0]+":"+elt_list[1].split(",")[2], output_dir, input_sea_points, input_cut_vector, "", "", "", "", "", "", "", "", 1.0, True, no_data_value, path_time_log, channel_order, epsg, format_raster, format_vector, extension_raster, extension_vector, save_results_intermediate, overwrite)

                        buffersOuvrages(tdc, output_dir, elt_list[1].split(",")[0], elt_list[1].split(",")[1], input_cut_vector, path_time_log, format_vector, extension_vector, save_results_intermediate, overwrite)
            elif type_extension == extension_vector:
                if debug >= 2:
                    print(cyan + "detectionOuvrages() : " + endC + green + bold + "Cas1 : méthode buffers sans calculTDC, en entrée : -meth b -dico TDC:TailleBuffer+,TailleBuffer- -outd" + endC)
                for elt_dico in input_dico:
                    elt_list = elt_dico.split(":")
                    buffersOuvrages(elt_list[0], output_dir, elt_list[1].split(",")[0], elt_list[1].split(",")[1], input_cut_vector, path_time_log, format_vector, extension_vector, save_results_intermediate, overwrite)
            else:
                print(cyan + "detectionOuvrages() : " + bold + red + "Format de fichier non valide pour la détection des ouvrages" + endC, file=sys.stderr)
                sys.exit(1)
            break

        if case("s"):
            if im_indice_sobel :
                if debug >= 2:
                    print(cyan + "detectionOuvrages() : " + endC + green + bold + "Cas4 : méthode Sobel avec image NDWI2 déjà calculée, en entrée : -meth s -inds -dico ImageBrute:ImageNDWI2,SeuilSobel -d -outd" + endC)
                for elt_dico in input_dico:
                    elt_list = elt_dico.split(":")
                    edgeExtractionOuvrages(elt_list[0] + ":" + elt_list[1].split(",")[0]+","+elt_list[1].split(",")[1], output_dir, input_cut_vector, False, no_data_value, path_time_log, format_raster, format_vector, extension_raster, extension_vector, save_results_intermediate, overwrite)
            else:
                if debug >= 2:
                    print(cyan + "detectionOuvrages() : " + endC + green + bold + "Cas5 : méthode Sobel avec calcul NDWI2, en entrée : -meth s -dico ImageBrute:SeuilSobel -d -outd" + endC)
                for elt_dico in input_dico:
                    elt_list = elt_dico.split(":")
                    edgeExtractionOuvrages(elt_list[0]+":" + elt_list[1], output_dir, input_cut_vector, True, no_data_value, path_time_log, format_raster, format_vector, extension_raster, extension_vector, save_results_intermediate, overwrite)
            break

        if case("bs"):
            if im_indice_buffers and im_indice_sobel:
                if debug >= 2:
                    print(cyan + "detectionOuvrages() : " + endC + green + bold + "Cas6 : méthode buffers+Sobel avec calcul TDC mais imageIndice et imageNDWI2 déjà calculées, en entrée : -meth bs -indb -inds -dico ImageBrute:TailleBuffer+,TailleBuffer-,ImageIndice,SeuilTerreMer,ImageNDWI2,SeuilSobel -d -outd -mer" + endC)
                for elt_dico in input_dico :
                    elt_list = elt_dico.split(":")

                    tdc = runTDCSeuil(elt_list[0] + ":" + elt_list[1].split(",")[2]+","+elt_list[1].split(",")[3], output_dir, input_sea_points, input_cut_vector, "", "", "", "", "", "", "", "", 1.0, False, no_data_value, path_time_log, channel_order, epsg, format_raster, format_vector, extension_raster, extension_vector, save_results_intermediate, overwrite)

                    buffers_ouvrages_shp = buffersOuvrages(tdc, output_dir, elt_list[1].split(",")[0], elt_list[1].split(",")[1], input_cut_vector, path_time_log, format_vector, extension_vector, save_results_intermediate, overwrite)
                    sobel_ouvrages_shp = edgeExtractionOuvrages(elt_list[0]+":" + elt_list[1].split(",")[4]+","+elt_list[1].split(",")[5], output_dir, input_cut_vector, False, no_data_value, path_time_log, format_raster, format_vector, extension_raster, extension_vector, save_results_intermediate, overwrite)
                    fusionVectors([buffers_ouvrages_shp, sobel_ouvrages_shp[0]], output_dir + os.sep + PREFIX_OUVRAGES + os.path.splitext(os.path.basename(elt_list[0]))[0] + extension_vector, format_vector)
            elif im_indice_buffers :
                if debug >= 2:
                    print(cyan + "detectionOuvrages() : " + endC + green + bold + "Cas7 : méthode buffers+Sobel avec calcul TDC, imageIndice déjà calculée mais imageNDWI2 à calculer, en entrée : -meth bs -indb -dico ImageBrute:TailleBuffer+,TailleBuffer-,ImageIndice,SeuilTerreMer,SeuilSobel -d -outd -mer" + endC)
                for elt_dico in input_dico :
                    elt_list = elt_dico.split(":")

                    tdc = runTDCSeuil(elt_list[0] + ":" + elt_list[1].split(",")[2]+","+elt_list[1].split(",")[3], output_dir, input_sea_points, input_cut_vector, "", "", "", "", "", "", "", "", 1.0, False, no_data_value, path_time_log, channel_order, epsg, format_raster, format_vector, extension_raster, extension_vector, save_results_intermediate, overwrite)

                    buffers_ouvrages_shp = buffersOuvrages(tdc, output_dir, elt_list[1].split(",")[0], elt_list[1].split(",")[1], input_cut_vector, path_time_log, format_vector, extension_vector, save_results_intermediate, overwrite)
                    sobel_ouvrages_shp = edgeExtractionOuvrages(elt_list[0]+":" + elt_list[1].split(",")[4], output_dir, input_cut_vector, True, no_data_value, path_time_log, format_raster, format_vector, extension_raster, extension_vector, save_results_intermediate, overwrite)
                    fusionVectors([buffers_ouvrages_shp, sobel_ouvrages_shp[0]], output_dir + os.sep + PREFIX_OUVRAGES + os.path.splitext(os.path.basename(elt_list[0]))[0] + extension_vector, format_vector)
            elif im_indice_sobel:
                if debug >= 2:
                    print(cyan + "detectionOuvrages() : " + endC + green + bold + "Cas8 : méthode buffers+Sobel avec TDC et imageNDWI2 déjà calculés, en entrée : -meth bs -inds -dico TDC:TailleBuffer+,TailleBuffer-,ImageBrute,ImageNDWI2,SeuilSobel -d -outd" + endC)
                for elt_dico in input_dico:
                    elt_list = elt_dico.split(":")
                    buffers_ouvrages_shp = buffersOuvrages(elt_list[1].split(",")[2], output_dir, elt_list[1].split(",")[0], elt_list[1].split(",")[1], input_cut_vector, path_time_log, format_vector, extension_vector, save_results_intermediate, overwrite)
                    sobel_ouvrages_shp = edgeExtractionOuvrages(elt_list[0]+":" + elt_list[1].split(",")[3]+","+elt_list[1].split(",")[4], output_dir, input_cut_vector, False, no_data_value, path_time_log, format_raster, format_vector, extension_raster, extension_vector, save_results_intermediate, overwrite)
                    fusionVectors([buffers_ouvrages_shp, sobel_ouvrages_shp[0]], output_dir + os.sep + PREFIX_OUVRAGES + os.path.splitext(os.path.basename(elt_list[0]))[0] + extension_vector, format_vector)
            else:
                if type_extension == extension_vector:
                    if debug >= 2:
                        print(cyan + "detectionOuvrages() : " + endC + green + bold + "Cas9 : méthode buffers+Sobel avec TDC déjà calculé mais imageNDWI2 à calculer, en entrée : -meth bs -dico TDC:TailleBuffer+,TailleBuffer-,ImageBrute,SeuilSobel -d -outd" + endC)
                    for elt_dico in input_dico:
                        elt_list = elt_dico.split(":")
                        buffers_ouvrages_shp = buffersOuvrages(elt_list[0], output_dir, elt_list[1].split(",")[0], elt_list[1].split(",")[1], input_cut_vector, path_time_log, format_vector, extension_vector, save_results_intermediate, overwrite)
                        sobel_ouvrages_shp = edgeExtractionOuvrages(elt_list[1].split(",")[2]+":" + elt_list[1].split(",")[3], output_dir, input_cut_vector, True, no_data_value, path_time_log, format_raster, format_vector, extension_raster, extension_vector, save_results_intermediate, overwrite)
                        fusionVectors([buffers_ouvrages_shp, sobel_ouvrages_shp[0]], output_dir + os.sep + PREFIX_OUVRAGES + os.path.splitext(os.path.basename(elt_list[1].split(",")[2]))[0] + extension_vector, format_vector)
                elif type_extension == extension_raster:
                    if debug >= 2:
                        print(cyan + "detectionOuvrages() : " + endC + green + bold + "Cas10 : méthode buffers+Sobel avec calculs TDC, imageNDVI et imageNDWI2 à faire, en entrée : -meth bs -dico ImageBrute:TailleBuffer+,TailleBuffer-,SeuilTerreMer,SeuilSobel -d -outd -mer" + endC)
                    for elt_dico in input_dico:
                        elt_list = elt_dico.split(":")

                        tdc = runTDCSeuil(elt_list[0] + ":" + elt_list[1].split(",")[2], output_dir, input_sea_points, input_cut_vector, "", "", "", "", "", "", "", "", 1.0, True, no_data_value, path_time_log, channel_order, epsg, format_raster, format_vector, extension_raster, extension_vector, save_results_intermediate, overwrite)

                        buffers_ouvrages_shp = buffersOuvrages(tdc, output_dir, elt_list[1].split(",")[0], elt_list[1].split(",")[1], input_cut_vector, path_time_log, format_vector, extension_vector, save_results_intermediate, overwrite)
                        sobel_ouvrages_shp = edgeExtractionOuvrages(elt_list[0]+":" + elt_list[1].split(",")[3], output_dir, input_cut_vector, True, no_data_value, path_time_log, format_raster, format_vector, extension_raster, extension_vector, save_results_intermediate, overwrite)
                        fusionVectors([buffers_ouvrages_shp, sobel_ouvrages_shp[0]], output_dir + os.sep + PREFIX_OUVRAGES + os.path.splitext(os.path.basename(elt_list[0]))[0] + extension_vector, format_vector)
                else:
                    print(cyan + "detectionOuvrages() : " + bold + red + "Format de fichier non valide pour la détection des ouvrages" + endC, file=sys.stderr)
                    sys.exit(1)
            break

        else :
            print(cyan + "detectionOuvrages() : " + bold + red + "Méthode de détection des ouvrages non valide : b pour buffers, s pour méthode de Sobel, bs pour combiner les 2" + endC, file=sys.stderr)
            sys.exit(1)

    # Mise à jour du Log
    ending_event = "detectionOuvrages() : Select Detection Ouvrages ending : "
    timeLine(path_time_log, ending_event)

    return

###########################################################################################################################################
# MISE EN PLACE DU PARSER                                                                                                                 #
###########################################################################################################################################

# Code executé seulement dans le cas ou le script est lancé depuis une ligne de commande
# Il n'est pas executé lors d'un import DetectionOuvrages.py
# Exemple de lancement en ligne de commande:
# Cas 1
# python /home/scgsi/Documents/ChaineTraitement/ScriptsLittoral/DetectionOuvrages.py -dico /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Test_TDCSeuil/Result/tdc_simplif_1_image1_-0.2.shp:12,-14 -outd /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Tests/Tests_DetectionOuvrages_1 -meth b -d /mnt/Donnees_Etudes/20_Etudes/Mediterranee/2Miseenforme/decoupe_zone_interet.shp
# Cas 2
# python /home/scgsi/Documents/ChaineTraitement/ScriptsLittoral/DetectionOuvrages.py -dico /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Test_TDCSeuil/image1.tif:12,-14,/mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Test_TDCSeuil/Result/image_NDVI_image1.tif,-0.1 -outd /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Tests/Tests_DetectionOuvrages_1 -d /mnt/Donnees_Etudes/20_Etudes/Mediterranee/2Miseenforme/decoupe_zone_interet.shp -meth b -mer /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Test_TDCSeuil/points_mer.shp -indb
# Cas 3
# python /home/scgsi/Documents/ChaineTraitement/ScriptsLittoral/DetectionOuvrages.py -dico /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Test_TDCSeuil/image1.tif:12,-14,-0.1 -outd /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Tests/Tests_DetectionOuvrages_1 -d /mnt/Donnees_Etudes/20_Etudes/Mediterranee/2Miseenforme/decoupe_zone_interet.shp -meth b -mer /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Test_TDCSeuil/points_mer.shp
# Cas 4
# python /home/scgsi/Documents/ChaineTraitement/ScriptsLittoral/DetectionOuvrages.py -dico /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Test_TDCSeuil/image2.tif:/mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/im_NDWI2_image2.tif,0.4 -meth s -d /mnt/Donnees_Etudes/20_Etudes/Mediterranee/2Miseenforme/decoupe_zone_interet.shp -outd /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Tests/Tests_DetectionOuvrages_1 -inds
# Cas 5
# python /home/scgsi/Documents/ChaineTraitement/ScriptsLittoral/DetectionOuvrages.py -dico /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Test_TDCSeuil/image2.tif:0.4 -meth s -d /mnt/Donnees_Etudes/20_Etudes/Mediterranee/2Miseenforme/decoupe_zone_interet.shp -outd /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Tests/Tests_DetectionOuvrages_1
# Cas 6
# python /home/scgsi/Documents/ChaineTraitement/ScriptsLittoral/DetectionOuvrages.py -meth bs -indb -inds -dico /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Test_TDCSeuil/image2.tif:12,-14,/mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Test_TDCSeuil/Result/image_NDVI_image2.tif,-0.2,/mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/im_NDWI2_image2.tif,0.4 -outd /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Tests/Tests_DetectionOuvrages_1 -d /mnt/Donnees_Etudes/20_Etudes/Mediterranee/2Miseenforme/decoupe_zone_interet.shp -mer /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Test_TDCSeuil/points_mer.shp
# Cas 7
# python /home/scgsi/Documents/ChaineTraitement/ScriptsLittoral/DetectionOuvrages.py -meth bs -indb -dico /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Test_TDCSeuil/image2.tif:12,-14,/mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Test_TDCSeuil/Result/image_NDVI_image2.tif,-0.1,0.4 -outd /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Tests/Tests_DetectionOuvrages_1 -d /mnt/Donnees_Etudes/20_Etudes/Mediterranee/2Miseenforme/decoupe_zone_interet.shp -mer /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Test_TDCSeuil/points_mer.shp
# Cas 8
# python /home/scgsi/Documents/ChaineTraitement/ScriptsLittoral/DetectionOuvrages.py -meth bs -inds -dico /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Test_TDCSeuil/image2.tif:12,-14,/mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Test_TDCSeuil/Result/tdc_simplif_1_image2_0.0.shp,/mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/im_NDWI2_image2.tif,0.4 -outd /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Tests/Tests_DetectionOuvrages_1 -d /mnt/Donnees_Etudes/20_Etudes/Mediterranee/2Miseenforme/decoupe_zone_interet.shp
# Cas 9
# python /home/scgsi/Documents/ChaineTraitement/ScriptsLittoral/DetectionOuvrages.py -meth bs -dico /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Test_TDCSeuil/Result/tdc_simplif_1_image1_-0.2.shp:12,-14,/mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Test_TDCSeuil/image1.tif,0.4 -outd /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Tests/Tests_DetectionOuvrages_1 -d /mnt/Donnees_Etudes/20_Etudes/Mediterranee/2Miseenforme/decoupe_zone_interet.shp
# Cas 10 deux images
# python /home/scgsi/Documents/ChaineTraitement/ScriptsLittoral/DetectionOuvrages.py -meth bs -dico /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Test_TDCSeuil/image1.tif:12,-14,-0.1,0.4 /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Test_TDCSeuil/image2.tif:12,-14,-0.15,0.2 -outd /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Tests/Tests_DetectionOuvrages_1 -d /mnt/Donnees_Etudes/20_Etudes/Mediterranee/2Miseenforme/decoupe_zone_interet.shp -mer /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Test_TDCSeuil/points_mer.shp

def main(gui=False):

    parser = argparse.ArgumentParser(prog="DetectionOuvrages", description=" \
    Info : Creating a shapefile (.shp) the structures of the coastline, extracted by buffer or Sobel method and coastline potentially calculated thanks to jet de rive method (TDCSeuil).\n\
    Objectif   : Extrait les ouvrages en mer par la méthode des buffers, celle de Sobel ou une combinaison de leurs deux résultats. Possibilité de calculer le trait de côte jet de rive avant la méthode des buffers. \n\
    Example : python /home/scgsi/Documents/ChaineTraitement/ScriptsLittoral/DetectionOuvrages.py \n\
                    -dico /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Test_TDCSeuil/Result/tdc_simplif_1_image1_-0.2.shp:12,-14 \n\
                    -outd /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Tests/Tests_DetectionOuvrages_1 \n\
                    -meth b \n\
                    -d /mnt/Donnees_Etudes/20_Etudes/Mediterranee/2Miseenforme/decoupe_zone_interet.shp")

    parser.add_argument('-dico','--input_dico', default="", nargs="+", help="Dictionnary containing images and thresholds, different for each use case : consult documentation of the 'chaine littoral'.", type=str, required=True)
    parser.add_argument('-outd','--output_dir', default="",help="Output directory.", type=str, required=True)
    parser.add_argument('-d','--input_cut_vector', default="",help="Cutting file.", type=str, required=True)
    parser.add_argument('-mer','--input_sea_points', default="",help="Input vector file containing points in the sea (.shp).", type=str, required=False)
    parser.add_argument('-meth','--method', default="",help="Method for ouvrages detection : b for buffers, s for Sobel, bs for a combination of both.", type=str, required=True)
    parser.add_argument('-indb','--im_indice_buffers', action='store_true', default=False, help="True if the dictionnary contains an NDVI or calculated index image for jet de rive extraction.", required=False)
    parser.add_argument('-inds','--im_indice_sobel', action='store_true', default=False, help="True if the dictionnary contains a NDWI2 image or calculated index image for Sobel structures extraction.", required=False)
    parser.add_argument('-chao','--channel_order',nargs="+", default=['Red','Green','Blue','NIR'],help="Type of multispectral image : rapideye or spot6 or pleiade. By default : [Red,Green,Blue,NIR]",type=str,required=False)
    parser.add_argument('-epsg','--epsg',default=2154,help="Option : Projection EPSG for the layers. By default : 2154", type=int, required=False)
    parser.add_argument('-ndv','--no_data_value', default=0, help="Option : Value of the pixel no data. By default : 0", type=int, required=False)
    parser.add_argument('-raf','--format_raster', default="GTiff", help="Option : Format output image, by default : GTiff (GTiff, HFA...)", type=str, required=False)
    parser.add_argument('-vef','--format_vector',default="ESRI Shapefile",help="Option : Vector format. By default : ESRI Shapefile", type=str, required=False)
    parser.add_argument('-rae','--extension_raster', default=".tif", help="Option : Extension file for image raster. By default : '.tif'", type=str, required=False)
    parser.add_argument('-vee','--extension_vector',default=".shp",help="Option : Extension file for vector. By default : '.shp'", type=str, required=False)
    parser.add_argument('-log','--path_time_log',default="",help="Name of log", type=str, required=False)
    parser.add_argument('-sav','--save_results_inter',action='store_true',default=False,help="Option : Save or delete intermediate result after the process. By default, False", required=False)
    parser.add_argument('-now','--overwrite',action='store_false',default=True,help="Option : Overwrite files with same names. By default : True", required=False)
    parser.add_argument('-debug','--debug',default=3,help="Option : Value of level debug trace, default : 3 ",type=int, required=False)
    args = displayIHM(gui, parser)

    # Récupération du dictionnaire contenant images et seuils
    if args.input_dico != None :
        input_dico = args.input_dico

    # Récupération du dossier des traitements en sortie
    if args.output_dir != None :
        output_dir = args.output_dir

    # Récupération de la méthode pour détection des ouvrages
    if args.method != None :
        method = args.method

    # Récupération du shp des points dans la mer
    if args.input_sea_points != None :
        input_sea_points = args.input_sea_points

    # Récupération du fichier pour la découpe (suppression des artéfacts)
    if args.input_cut_vector != None :
        input_cut_vector = args.input_cut_vector

    # Récupération de la valeur du calcul de l'indice de l'image NDVI pour calcul jet de rive
    if args.im_indice_buffers != None :
        im_indice_buffers = args.im_indice_buffers

    # Récupération de la valeur du calcul de l'indice de l'image NDWI2 pour méthode Sobel
    if args.im_indice_sobel != None :
        im_indice_sobel = args.im_indice_sobel

    # Récupération de la valeur (vrai/faux) du calcul de l'image indice
    if args.is_calc_indice_image != None :
        is_calc_indice_image = args.is_calc_indice_image

    # Récupération de la projection
    if args.epsg != None:
        epsg = args.epsg

    # Récupération du parametre no_data_value
    if args.no_data_value!= None:
        no_data_value = args.no_data_value

    # Paramètre format des images de sortie
    if args.format_raster != None:
        format_raster = args.format_raster

    # Récupération du nom du format des fichiers vecteur
    if args.format_vector != None:
        format_vector = args.format_vector

    # Paramètre de l'extension des images rasters
    if args.extension_raster != None:
        extension_raster = args.extension_raster

    # Récupération de l'extension des fichiers vecteurs
    if args.extension_vector != None:
        extension_vector = args.extension_vector

    # Récupération du nom du fichier log
    if args.path_time_log != None:
        path_time_log = args.path_time_log

    # Ecrasement des fichiers
    if args.save_results_inter != None:
        save_results_intermediate = args.save_results_inter

    if args.overwrite != None:
        overwrite = args.overwrite

    # Récupération de l'option niveau de debug
    if args.debug!= None:
        global debug
        debug = args.debug

    # Affichage des arguments récupérés
    if debug >= 3:
        print(bold + green + "Variables dans le parser" + endC)
        print(cyan + "DetectionOuvrages : " + endC + "input_dico : " + str(input_dico) + endC)
        print(cyan + "DetectionOuvrages : " + endC + "output_dir : " + str(output_dir) + endC)
        print(cyan + "DetectionOuvrages : " + endC + "method : " + str(method) + endC)
        print(cyan + "DetectionOuvrages : " + endC + "im_indice_buffers : " + str(im_indice_buffers) + endC)
        print(cyan + "DetectionOuvrages : " + endC + "im_indice_sobel : " + str(im_indice_sobel) + endC)
        print(cyan + "DetectionOuvrages : " + endC + "input_cut_vector : " + str(input_cut_vector) + endC)
        print(cyan + "DetectionOuvrages : " + endC + "input_sea_points : " + str(input_sea_points) + endC)
        print(cyan + "DetectionOuvrages : " + endC + "channel_order : " + str(channel_order) + endC)
        print(cyan + "DetectionOuvrages : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "DetectionOuvrages : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "DetectionOuvrages : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "DetectionOuvrages : " + endC + "channel_order: " + str(channel_order) + endC)
        print(cyan + "DetectionOuvrages : " + endC + "format_raster : " + str(format_raster) + endC)
        print(cyan + "DetectionOuvrages : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "DetectionOuvrages : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "DetectionOuvrages : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "DetectionOuvrages : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "DetectionOuvrages : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "DetectionOuvrages : " + endC + "debug : " + str(debug) + endC)

    # Fonction générale
    detectionOuvrages(input_dico, output_dir, method, im_indice_buffers, im_indice_sobel, input_cut_vector, input_sea_points, no_data_value, path_time_log, channel_order, epsg, format_raster, format_vector, extension_raster, extension_vector, save_results_intermediate, overwrite)

# ================================================

if __name__ == '__main__':
  main(gui=False)
