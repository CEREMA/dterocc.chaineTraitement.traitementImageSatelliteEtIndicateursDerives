#! /usr/bin/env pyt/hon
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerSO/DALETT/SCGSI  All rights reserved.                                                                            #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT D'EXTRACTION DU TRAIT DE CÔTE PAR LA MÉTHODE DES K-MEANS                                                                           #
#                                                                                                                                           #
#############################################################################################################################################

'''
Nom de l'objet : TDCKmeans.py
Description    :
    Objectif   : Extrait le trait de côte par la méthode des k-means à partir d'une image satellite
    Rq : utilisation des OTB Applications :  otbcli_ConcatenateImages, otbcli_KMeansClassification, otbcli_ClassificationMapRegularization

Date de creation : 23/06/2016
'''

from __future__ import print_function
import os, argparse, sys, shutil
from Lib_display import bold, black, red, green, yellow, blue, magenta, cyan, endC, displayIHM
from Lib_log import timeLine
from Lib_index import createNDVI, createNDWI2, createBI
from Lib_raster import createBinaryMask, polygonizeRaster, cutImageByVector, classificationKmeans
from PolygonMerToTDC import polygonMerToTDC

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 3

# Les parametres de la fonction OTB otbcli_KMeansClassification a changé à partir de la version 7.0 de l'OTB
IS_VERSION_UPPER_OTB_7_0 = False
pythonpath = os.environ["PYTHONPATH"]
print ("Identifier la version d'OTB : ")
pythonpath_list = pythonpath.split(os.sep)
otb_info = ""
for info in pythonpath_list :
    if info.find("OTB") > -1:
        otb_info = info.split("-")[1]
        break
print (otb_info)
if int(otb_info.split(".")[0]) >= 7 :
    IS_VERSION_UPPER_OTB_7_0 = True

###########################################################################################################################################
# FONCTION runTDCKmeans                                                                                                                   #
###########################################################################################################################################
# ROLE:
#    Extraction du trait de côte avec la méthode des k-means à partir d'une image satellite
#
# ENTREES DE LA FONCTION :
#    input_images : Liste des images pour l'extraction du trait de côte (.tif)
#    output_dir : Répertoire de sortie pour les traitements
#    input_sea_points : Fichier shp de points dans la mer pour identifier les polygones mer sur le masque terre/mer
#    input_cut_vector : Fichier shp de contour pour la découpe de la zone d'intérêt
#    nb_classes : Nombre de classes pour la classification. Par défaut, 5
#    no_data_value : Valeur de  pixel du no data
#    path_time_log : le fichier de log de sortie
#    epsg : Code EPSG des fichiers
#    format_raster : Format de l'image de sortie, par défaut : GTiff
#    format_vector  : format du vecteur de sortie, par defaut = 'ESRI Shapefile'
#    extension_raster : extension des fichiers raster de sortie, par defaut = '.tif'
#    extension_vector : extension du fichier vecteur de sortie, par defaut = '.shp'
#    save_results_intermediate : fichiers de sorties intermediaires non nettoyées, par defaut = True
#    overwrite : supprime ou non les fichiers existants ayant le meme nom
#
# SORTIES DE LA FONCTION :
#    Le fichier contenant le trait de côte
#    Eléments modifiés aucun
#

def runTDCKmeans(input_images, output_dir, input_sea_points, input_cut_vector, no_data_value, path_time_log, nb_classes=5, epsg=2154, format_raster='GTiff', format_vector="ESRI Shapefile", extension_raster=".tif", extension_vector=".shp", save_results_intermediate=True, overwrite=True):

    # Mise à jour du Log
    starting_event = "runTDCKmeans() : Select TDC kmeans starting : "
    timeLine(path_time_log,starting_event)

    # Initialisation des constantes
    ID = "id"
    REP_TEMP = "temp_TDCKmeans"
    CHANNEL_ORDER = ["Red", "Green", "Blue", "NIR"]

    # Initialisation des variables
    repertory_temp = output_dir + os.sep + REP_TEMP

    # Nettoyage du repertoire de sortie
    if overwrite and os.path.exists(output_dir):
        shutil.rmtree(output_dir)

    # Création du répertoire de sortie s'il n'existe pas déjà
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Création du répertoire de sortie temporaire s'il n'existe pas déjà
    if not os.path.exists(repertory_temp):
        os.makedirs(repertory_temp)

    # Vérification de l'existence des fichiers
    if not os.path.exists(input_cut_vector):
        print(cyan + "runTDCKmeans() : " + bold + red + "The file %s does not exist" %(input_cut_vector) + endC, file=sys.stderr)
        sys.exit(1)

    # Affichage des paramètres
    if debug >= 3:
        print(bold + green + "Variables dans runTDCKmeans - Variables générales" + endC)
        print(cyan + "runTDCKmeans() : " + endC + "input_images : " + str(input_images) + endC)
        print(cyan + "runTDCKmeans() : " + endC + "output_dir : " + str(output_dir) + endC)
        print(cyan + "runTDCKmeans() : " + endC + "input_sea_points : " + str(input_sea_points) + endC)
        print(cyan + "runTDCKmeans() : " + endC + "input_cut_vector : " + str(input_cut_vector) + endC)
        print(cyan + "runTDCKmeans() : " + endC + "nb_classes : " + str(nb_classes) + endC)
        print(cyan + "runTDCKmeans() : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "runTDCKmeans() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "runTDCKmeans() : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "runTDCKmeans() : " + endC + "format_raster : " + str(format_raster) + endC)
        print(cyan + "runTDCKmeans() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "runTDCKmeans() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "runTDCKmeans() : " + endC + "overwrite : " + str(overwrite) + endC)

    dico = ""
    for image in input_images:
        # Vérification de l'existence des fichiers
        if not os.path.exists(image):
            print(cyan + "runTDCKmeans() : " + bold + red + "The file %s does not exist" %(image) + endC, file=sys.stderr)
            sys.exit(1)

        # Initialisation des fichiers de sortie
        image_name = os.path.splitext(os.path.basename(image))[0]
        im_NDVI = repertory_temp +os.sep + "im_NDVI_" + image_name + extension_raster
        im_NDWI2 = repertory_temp +os.sep + "im_NDWI2_" + image_name + extension_raster
        im_BI = repertory_temp + os.sep + "im_BI_" + image_name + extension_raster
        im_concat = repertory_temp + os.sep + "im_concat_" + image_name + extension_raster
        im_kmeans = repertory_temp + os.sep + "im_kmeans_" + image_name + extension_raster
        im_kmeans_decoup = repertory_temp + os.sep + "im_kmeans_decoup_" + image_name + extension_raster
        im_kmeans_decoup_filter = repertory_temp + os.sep + "im_filter_" + image_name + extension_raster
        im_kmeans_vect_name = "im_kmeans_vect_" + image_name
        im_kmeans_vector = output_dir + os.sep + "temp_TDCKMeans" + os.sep + im_kmeans_vect_name + extension_vector

        # Création des images indice
        createNDVI(image, im_NDVI, CHANNEL_ORDER)
        createNDWI2(image, im_NDWI2, CHANNEL_ORDER)
        createBI(image, im_BI, CHANNEL_ORDER)

        # Concaténation des bandes des images brute, NDVI, NDWI2 et BI
        command = "otbcli_ConcatenateImages -il %s %s %s %s -out %s" %(image, im_NDVI, im_NDWI2, im_BI, im_concat)
        if debug >= 3:
            print(command)
        exitCode = os.system(command)
        if exitCode != 0:
            raise NameError(cyan + "runTDCKmeans() : " + endC + bold + red + "An error occured during otbcli_ConcatenateImages command. See error message above." + endC)
        else:
            print(cyan + "runTDCKmeans() : " + endC + bold + green + "Create binary file %s complete!" %(im_concat) + endC)

        # K-Means sur l'image concaténée
        if IS_VERSION_UPPER_OTB_7_0 :
            classificationKmeans(im_concat, "", im_kmeans, nb_classes, 300, 1, no_data_value, format_raster)
            if debug >= 2:
                print(cyan + "runTDCKmeans() : " + endC + bold + green + "Create binary file %s complete!" %(im_kmeans) + endC)
        else :
            command = "otbcli_KMeansClassification -in %s -nc %s -nodatalabel %s -rand %s -out %s" %(im_concat, str(nb_classes), str(no_data_value), str(1), im_kmeans)
            if debug >= 3:
                print(command)
            exitCode = os.system(command)
            if exitCode != 0:
                raise NameError(cyan + "runTDCKmeans() : " + endC + bold + red + "An error occured during otbcli_ConcatenateImages command. See error message above." + endC)
            else:
                print(cyan + "runTDCKmeans() : " + endC + bold + green + "Create binary file %s complete!" %(im_kmeans) + endC)

        # Découpe du raster image Kmeans
        cutImageByVector(input_cut_vector, im_kmeans, im_kmeans_decoup, None, None, no_data_value, epsg, format_raster, format_vector)

         # Nettoyage de l'image raster Kmeans
        command = "otbcli_ClassificationMapRegularization -io.in %s -io.out %s -ip.radius %s" %(im_kmeans_decoup, im_kmeans_decoup_filter, str(5))
        if debug >= 3:
            print(command)
        exitCode = os.system(command)
        if exitCode != 0:
            raise NameError(cyan + "runTDCKmeans() : " + endC + bold + red + "An error occured during otbcli_ClassificationMapRegularization command. See error message above." + endC)
        else:
            if debug >= 2:
                print(cyan + "runTDCKmeans() : " + endC + bold + green + "Create binary file %s complete!" %(im_kmeans_decoup_filter) + endC)

        # Vectorisation de l'image découpée
        polygonizeRaster(im_kmeans_decoup_filter, im_kmeans_vector, im_kmeans_vect_name, ID, format_vector)

        # Création du dictionnaire pour le passage à PolygonMerToTDC
        dico += image + ":" + im_kmeans_vector + " "

    # Appel à PolygonMerToTDC pour l'extraction du TDC
    dico = dico[:-1]
    polygonMerToTDC(str(dico), output_dir, input_sea_points, False, 1, input_cut_vector, 1, -1, no_data_value, path_time_log, epsg, format_vector, extension_raster, extension_vector, save_results_intermediate, overwrite)

    # Suppression du repertoire temporaire
    if not save_results_intermediate and os.path.exists(repertory_temp):
        shutil.rmtree(repertory_temp)

    # Mise à jour du Log
    ending_event = "runTDCKmeans() : Select TDC kmeans ending : "
    timeLine(path_time_log,ending_event)

    return

###########################################################################################################################################
# MISE EN PLACE DU PARSER                                                                                                                 #
###########################################################################################################################################

# Code executé seulement dans le cas ou le script est lancé depuis une ligne de commande
# Il n'est pas executé lors d'un import TDCKmeans.py
# Exemple de lancement en ligne de commande:
# python /home/scgsi/Documents/ChaineTraitement/ScriptsLittoral/TDCKmeans.py python /home/scgsi/Documents/ChaineTraitement/ScriptsLittoral/TDCKmeans.py -pathi /mnt/Donnees_Etudes/20_Etudes/Mediterranee/2Miseenforme/Images_Paysages/Images_individuelles_ass/emprise_image_opti_0824_ass_20140222.tif -outd /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Tests/Tests_TDCKmeans_0824 -nbc 6 -mer /mnt/Donnees_Etudes/20_Etudes/Mediterranee/2Miseenforme/Mer.shp -d /mnt/Donnees_Etudes/20_Etudes/Mediterranee/2Miseenforme/decoupe_zone_interet.shp

def main(gui=False):

    parser = argparse.ArgumentParser(prog="TDCKmeans", description=" \
    Info : Creating an shapefile (.shp) containing the coastline extracted from a satellite image, by kmeans method.\n\
    Objectif   : Extrait le trait de côte par la méthode des k-means à partir d'une image satellite et de l'identification des polygones mer. \n\
    Example : python /home/scgsi/Documents/ChaineTraitement/ScriptsLittoral/TDCKmeans.py \n\
                    -pathi /mnt/Donnees_Etudes/20_Etudes/Mediterranee/2Miseenforme/Images_Paysages/Images_individuelles_ass/emprise_image_opti_0824_ass_20140222.tif \n\
                    -outd /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Tests/Tests_TDCKmeans_0824 \n\
                    -mer /mnt/Donnees_Etudes/20_Etudes/Mediterranee/2Miseenforme/Mer.shp \n\
                    -nbc 6 \n\
                    -d /mnt/Donnees_Etudes/20_Etudes/Mediterranee/2Miseenforme/decoupe_zone_interet.shp")

    parser.add_argument('-pathi','--input_images', default="", nargs="+", help="List of raw images for the treatment (.tif).", type=str, required=True)
    parser.add_argument('-outd','--output_dir', default="",help="Output directory.", type=str, required=True)
    parser.add_argument('-mer','--input_sea_points', default="",help="Input vector file containing points in the sea (.shp).", type=str, required=True)
    parser.add_argument('-d','--input_cut_vector', default="", help="Vector file containing shape of the area to keep (.shp).", type=str, required=True)
    parser.add_argument('-nbc','--nb_classes', default=5, help="Nombre de classes pour la classification k-means.", type=int, required=False)
    parser.add_argument('-ndv','--no_data_value', default=0, help="Option : Value of the pixel no data. By default : 0", type=int, required=False)
    parser.add_argument('-epsg','--epsg', default=2154,help="EPSG code projection.", type=int, required=False)
    parser.add_argument('-raf','--format_raster', default="GTiff", help="Option : Format output image raster. By default : GTiff (GTiff, HFA...)", type=str, required=False)
    parser.add_argument('-vef','--format_vector',default="ESRI Shapefile",help="Option : Vector format. By default : ESRI Shapefile", type=str, required=False)
    parser.add_argument('-rae','--extension_raster', default=".tif", help="Option : Extension file for image raster. By default : '.tif'", type=str, required=False)
    parser.add_argument('-vee','--extension_vector',default=".shp",help="Option : Extension file for vector. By default : '.shp'", type=str, required=False)
    parser.add_argument('-log','--path_time_log',default="",help="Name of log", type=str, required=False)
    parser.add_argument('-sav','--save_results_inter',action='store_true',default=False,help="Option : Save or delete intermediate result after the process. By default, False", required=False)
    parser.add_argument('-now','--overwrite',action='store_false',default=True,help="Option : Overwrite files with same names. By default : True", required=False)
    parser.add_argument('-debug','--debug',default=3,help="Option : Value of level debug trace, default : 3 ",type=int, required=False)
    args = displayIHM(gui, parser)

    # Récupération de la liste des images à traiter
    if args.input_images != None :
        input_images = args.input_images

    # Récupération du dossier des traitements en sortie
    if args.output_dir != None :
        output_dir = args.output_dir

    # Récupération de la couche points mer
    if args.input_sea_points != None :
        input_sea_points = args.input_sea_points

    # Récupération du shapefile de découpe
    if args.input_cut_vector != None :
        input_cut_vector = args.input_cut_vector

    # Récupération du nombre de classes
    if args.nb_classes != None :
        nb_classes = args.nb_classes

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

    # Récupération du code EPSG de la projection du shapefile trait de côte
    if args.epsg != None :
        epsg = args.epsg

    if args.overwrite != None:
        overwrite = args.overwrite

    # Récupération de l'option niveau de debug
    if args.debug!= None:
        global debug
        debug = args.debug

    # Affichage des arguments récupérés
    if debug >= 3:
        print(bold + green + "Variables dans le parser" + endC)
        print(cyan + "TDCKmeans : " + endC + "input_images : " + str(input_images) + endC)
        print(cyan + "TDCKmeans : " + endC + "output_dir : " + str(output_dir) + endC)
        print(cyan + "TDCKmeans : " + endC + "input_sea_points : " + str(input_sea_points) + endC)
        print(cyan + "TDCKmeans : " + endC + "input_cut_vector : " + str(input_cut_vector) + endC)
        print(cyan + "TDCKmeans : " + endC + "nb_classes : " + str(nb_classes) + endC)
        print(cyan + "TDCKmeans : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "TDCKmeans : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "TDCKmeans : " + endC + "format_raster : " + str(format_raster) + endC)
        print(cyan + "TDCKmeans : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "TDCKmeans : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "TDCKmeans : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "TDCKmeans : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "TDCKmeans : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "TDCKmeans : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "TDCKmeans : " + endC + "debug : " + str(debug) + endC)

    # Fonction générale
    runTDCKmeans(input_images, output_dir, input_sea_points, input_cut_vector, no_data_value, path_time_log, nb_classes, epsg, format_raster, format_vector, extension_raster, extension_vector, save_results_intermediate, overwrite)

# ================================================

if __name__ == '__main__':
  main(gui=False)



