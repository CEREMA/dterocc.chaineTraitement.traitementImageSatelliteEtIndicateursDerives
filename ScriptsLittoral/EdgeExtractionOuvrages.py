#! /usr/bin/env pyt/hon
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT D'EXTRACTION DES OUVRAGES À PARTIR D'UN TRAIT DE CÔTE GRÂCE AU FILTRE DE SOBEL                                                     #
#                                                                                                                                           #
#############################################################################################################################################

"""
Nom de l'objet : EdgeExtractionOuvrages.py
Description    :
----------------
Objectif   : Extraction des ouvrages par la méthodes de Sobel, à partir d'images brutes ou NDWI2

Date de creation : 07/06/2016
"""

from __future__ import print_function
import os, sys, shutil, argparse
from Lib_display import bold, magenta, red, cyan, green, endC, displayIHM
from Lib_log import timeLine
from Lib_vector import bufferVector, simplifyVector, cleanMiniAreaPolygons, cutVectorAll
from Lib_raster import createBinaryMask, polygonizeRaster, createEdgeExtractionImage, createBinaryMaskMultiBand, getNodataValueImage, cutImageByVector
from Lib_index import createNDWI2
from Lib_file import removeVectorFile

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 3

###########################################################################################################################################
# FONCTION edgeExtractionOuvrages                                                                                                         #
###########################################################################################################################################
def edgeExtractionOuvrages(input_im_seuils_dico, output_dir, input_cut_vector, calc_ndwi2_image, no_data_value, path_time_log, format_raster='GTiff', format_vector="ESRI Shapefile", extension_raster=".tif", extension_vector=".shp", save_results_intermediate=True, overwrite=True):
    """
    # ROLE:
    #    Extraction des ouvrages en mer à partir du trait de côte, selon la méthode de détection des contours (Sobel), à partir d'une image brute ou NDWI2
    #
    # ENTREES DE LA FONCTION :
    #    input_im_seuils_dico : dictionnaire (chaîne de caractères) associant les images brutes aux seuils pr le masque binaire sur l'image de Sobel et éventuellement à leur image NDWI2 déjà calculée
    #    output_dir : Répertoire de sortie pour les traitements
    #    input_cut_vector : Shapefile de découpe pour la suppression des artéfacts (zone d'intérêt autour du TDC)
    #    calc_ndwi2_image : Booléen : calcul ou non de l'image NDI2 (selon si elle est renseignée dans le dictionnaire ou non)
    #    format_vector : Format des fichiers vecteur. Par défaut "ESRI Shapefile"
    #    no_data_value : Valeur de  pixel du no data
    #    path_time_log : le fichier de log de sortie
    #    format_raster : Format de l'image de sortie, par défaut : GTiff
    #    format_vector : Format des fichiers vecteur. Par défaut "ESRI Shapefile"
    #    extension_raster : extension des fichiers raster de sortie, par defaut = '.tif'
    #    extension_vector : extension du fichier vecteur de sortie, par defaut = '.shp'
    #    save_results_intermediate : fichiers de sorties intermediaires non nettoyées, par defaut = True
    #    overwrite : supprime ou non les fichiers existants ayant le meme nom, par défaut = True
    #
    # SORTIES DE LA FONCTION :
    #    Le fichier contenant les ouvrages extraits par la méthode du filtre de Sobel
    #    Eléments modifiés aucun
    #
    """

    # Mise à jour du Log
    starting_event = "edgeExtractionOuvrages() : Select edge extraction ouvrages starting : "
    timeLine(path_time_log,starting_event)

    # Affichage des paramètres
    if debug >= 3:
        print(bold + green + "Variables dans edgeExtractionOuvrages - Variables générales" + endC)
        print(cyan + "edgeExtractionOuvrages() : " + endC + "input_im_seuils_dico : " + str(input_im_seuils_dico) + endC)
        print(cyan + "edgeExtractionOuvrages() : " + endC + "output_dir : " + str(output_dir) + endC)
        print(cyan + "edgeExtractionOuvrages() : " + endC + "input_cut_vector : " + str(input_cut_vector) + endC)
        print(cyan + "edgeExtractionOuvrages() : " + endC + "calc_ndwi2_image : " + str(calc_ndwi2_image) + endC)
        print(cyan + "edgeExtractionOuvrages() : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "edgeExtractionOuvrages() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "edgeExtractionOuvrages() : " + endC + "format_raster : " + str(format_raster) + endC)
        print(cyan + "edgeExtractionOuvrages() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "edgeExtractionOuvrages() : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "edgeExtractionOuvrages() : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "edgeExtractionOuvrages() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "edgeExtractionOuvrages() : " + endC + "overwrite : " + str(overwrite) + endC)

    # Constantes
    REP_TEMP = "temp_sobel"

    # Variables
    repertory_temp = output_dir + os.sep + REP_TEMP

    # Création du répertoire de sortie s'il n'existe pas déjà
    if not os.path.exists(repertory_temp):
        os.makedirs(repertory_temp)

    ouvrages_final_list = []
    for elt in input_im_seuils_dico.split():
        seuils = ""
        elt_list = elt.split(":")
        if calc_ndwi2_image:
            im_sobel = createSobelImage(elt_list[0], repertory_temp, calc_ndwi2_image, path_time_log, extension_raster, save_results_intermediate, overwrite)
            for i in range(len(elt_list[1].split(","))):
                seuils += str(elt_list[1].split(",")[i]) + ","
            seuils = seuils[:-1]
            ouvrages_shp_list = sobelToOuvrages(elt_list[0] + ":" + im_sobel + "," + seuils, output_dir, input_cut_vector, no_data_value, path_time_log, format_raster, format_vector, extension_raster, extension_vector, save_results_intermediate, overwrite)
        else:
            im_sobel = createSobelImage(elt_list[1].split(",")[0], repertory_temp, calc_ndwi2_image, path_time_log, extension_raster, save_results_intermediate, overwrite)
            for i in range(1,len(elt_list[1].split(","))):
                seuils += str(elt_list[1].split(",")[i]) + ","
            seuils = seuils[:-1]
            ouvrages_shp_list = sobelToOuvrages(elt_list[0]+":" + im_sobel + "," + seuils, output_dir, input_cut_vector, no_data_value, path_time_log, format_raster, format_vector, extension_raster, extension_vector, save_results_intermediate, overwrite)
        for shp in ouvrages_shp_list:
            ouvrages_final_list.append(shp)

    # Suppression du repertoire temporaire
    if not save_results_intermediate and os.path.exists(repertory_temp):
        shutil.rmtree(repertory_temp)

    # Mise à jour du Log
    ending_event = "edgeExtractionOuvrages() : Select edge extraction ouvrages ending : "
    timeLine(path_time_log, ending_event)

    return ouvrages_final_list

###########################################################################################################################################
# FONCTION createSobelImage                                                                                                               #
###########################################################################################################################################
def createSobelImage(input_image, output_dir, calc_ndwi2_image, path_time_log, extension_raster=".tif", save_results_intermediate=True, overwrite=True):
    """
    # ROLE:
    #    Création d'une image dont les contours sont détectés
    #
    # ENTREES DE LA FONCTION :
    #    input_image : image pour l'extraction des contours
    #    output_dir : dossier pour les fichiers en sortie
    #    calc_ndwi2_image : True si input_image est une image brute, False si c'est déjà une image calculée d'indice
    #    path_time_log : le fichier de log de sortie
    #    extension_raster : extension des fichiers raster de sortie, par defaut = '.tif'
    #    save_results_intermediate : fichiers de sorties intermediaires non nettoyées, par defaut = False
    #    overwrite : supprime ou non les fichiers existants ayant le meme nom
    #
    # SORTIES DE LA FONCTION :
    #    Le fichier contenant les contours extraits
    #    Eléments modifiés aucun
    #
    """

    # Mise à jour du Log
    starting_event = "createSobelImage() : Select create Sobel Image starting : "
    timeLine(path_time_log,starting_event)

    # Affichage des paramètres
    if debug >= 3:
        print(bold + green + "Variables dans createSobelImage - Variables générales" + endC)
        print(cyan + "createSobelImage : " + endC + "input_image : " + str(input_image) + endC)
        print(cyan + "createSobelImage : " + endC + "output_dir : " + str(output_dir) + endC)
        print(cyan + "createSobelImage : " + endC + "calc_ndwi2_image : " + str(calc_ndwi2_image) + endC)
        print(cyan + "createSobelImage : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "createSobelImage : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "createSobelImage : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "createSobelImage : " + endC + "overwrite : " + str(overwrite) + endC)

    output_image = output_dir + os.sep + "im_sobel_" + os.path.splitext(os.path.basename(input_image))[0] + extension_raster

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    if calc_ndwi2_image:
        index_image = output_dir + os.sep + "im_NDWI2_" + os.path.splitext(os.path.basename(input_image))[0] + extension_raster
        createNDWI2(input_image, index_image, ["Red", "Green", "Blue", "NIR"])
    else:
        index_image = input_image

    createEdgeExtractionImage(index_image, output_image, 'sobel')

    return output_image

###########################################################################################################################################
# FONCTION sobelToOuvrages                                                                                                                #
###########################################################################################################################################
def sobelToOuvrages(input_im_seuils_dico, output_dir, input_cut_vector, no_data_value, path_time_log, format_raster='GTiff', format_vector="ESRI Shapefile", extension_raster=".tif", extension_vector=".shp", save_results_intermediate=True, overwrite=True):
    """
    # ROLE:
    #    Extraction des ouvrages en mer à partir d'une image de Sobel déjà calculée
    #
    # ENTREES DE LA FONCTION :
    #    input_im_seuils_dico : Dictionnaire (chaîne de caractères) associant l'image brute avec son image de Sobel et les seuils pour le masque binaire
    #    output_dir : Répertoire de sortie pour les traitements
    #    input_cut_vector : Shapefile de découpe de la zone d'intérêt (pou suppression des artéfacts : bateaux, ...)
    #    no_data_value : Valeur de  pixel du no data
    #    path_time_log : le fichier de log de sortie
    #    format_raster : Format de l'image de sortie, par défaut : GTiff
    #    format_vector : Format des fichiers vecteur. Par défaut "ESRI Shapefile"
    #    extension_raster : extension des fichiers raster de sortie, par defaut = '.tif'
    #    extension_vector : extension du fichier vecteur de sortie, par defaut = '.shp'
    #    save_results_intermediate : fichiers de sorties intermediaires non nettoyées, par defaut = False
    #    overwrite : supprime ou non les fichiers existants ayant le meme nom
    #
    # SORTIES DE LA FONCTION :
    #    Le fichier contenant les ouvrages extraits
    #    Eléments modifiés aucun
    #
    """

    # Constantes
    REPERTORY_TEMP = "temp_sobel"
    CODAGE_8B = "uint8"
    ID = "id"

    # Mise à jour du Log
    starting_event = "sobelToOuvrages() : Select Sobel to ouvrages starting : "
    timeLine(path_time_log,starting_event)

    # Création du répertoire de sortie s'il n'existe pas déjà
    if not os.path.exists(output_dir + os.sep + REPERTORY_TEMP):
        os.makedirs(output_dir + os.sep + REPERTORY_TEMP)

    # Affichage des paramètres
    if debug >= 3:
        print(bold + green + "Variables dans SobelToOuvrages - Variables générales" + endC)
        print(cyan + "sobelToOuvrages() : " + endC + "input_im_seuils_dico : " + str(input_im_seuils_dico) + endC)
        print(cyan + "sobelToOuvrages() : " + endC + "output_dir : " + str(output_dir) + endC)
        print(cyan + "sobelToOuvrages() : " + endC + "input_cut_vector : " + str(input_cut_vector) + endC)
        print(cyan + "sobelToOuvrages() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "sobelToOuvrages() : " + endC + "format_raster : " + str(format_raster) + endC)
        print(cyan + "sobelToOuvrages() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "sobelToOuvrages() : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "sobelToOuvrages() : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "sobelToOuvrages() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "sobelToOuvrages() : " + endC + "overwrite : " + str(overwrite) + endC)

    sobel_ouvrages_shp_list = []

    for elt in input_im_seuils_dico.split():
        raw_image = elt.split(":")[0]
        sobel_image = elt.split(":")[1].split(",")[0]

        for i in range(1,len(elt.split(":")[1].split(","))):
            seuil = elt.split(":")[1].split(",")[i]

            # Initialisation des noms des fichiers en sortie
            image_name = os.path.splitext(os.path.basename(raw_image))[0]
            sobel_binary_mask = output_dir + os.sep + REPERTORY_TEMP + os.sep + "bin_mask_sobel_" + image_name + "_" + str(seuil) + extension_raster
            sobel_binary_mask_vector_name = "bin_mask_vect_sobel_" + image_name + "_" + str(seuil)
            sobel_binary_mask_vector = output_dir + os.sep + REPERTORY_TEMP + os.sep + sobel_binary_mask_vector_name + extension_vector
            sobel_binary_mask_vector_cleaned = output_dir + os.sep + REPERTORY_TEMP + os.sep + "bin_mask_vect_sobel_cleaned_" + image_name + "_" + str(seuil) + extension_vector
            sobel_decoup = output_dir + os.sep + "sobel_decoup_" + image_name + "_" + str(seuil) + extension_vector

            binary_mask_zeros_name = "b_mask_zeros_vect_" + image_name
            binary_mask_zeros_raster = output_dir + os.sep + REPERTORY_TEMP + os.sep + "b_mask_zeros_" + image_name + extension_raster
            binary_mask_zeros_vector = output_dir + os.sep + REPERTORY_TEMP + os.sep + binary_mask_zeros_name + extension_vector
            binary_mask_zeros_vector_simpl = output_dir + os.sep + REPERTORY_TEMP + os.sep + "b_mask_zeros_vect_simpl_" + image_name + extension_vector
            true_values_buffneg = output_dir + os.sep + REPERTORY_TEMP + os.sep + "true_values_buffneg_" + image_name + extension_vector
            ouvrages_decoup_final = output_dir + os.sep + "ouvrages_sobel_" + image_name + "_" + str(seuil) + extension_vector

            # Création du masque binaire
            createBinaryMask(sobel_image, sobel_binary_mask, float(seuil), True)

            # Découpe du masque binaire par le shapefile de découpe en entrée
            cutImageByVector(input_cut_vector, sobel_binary_mask, sobel_decoup, None, None, False, no_data_value, 0, format_raster, format_vector)

            # Vectorisation du masque binaire Sobel découpé
            polygonizeRaster(sobel_decoup, sobel_binary_mask_vector, sobel_binary_mask_vector_name)

            # Création masque binaire pour séparer les no data des vraies valeurs
            nodata_value = getNodataValueImage(raw_image)
            if no_data_value == None :
                no_data_value = 0
            createBinaryMaskMultiBand(raw_image, binary_mask_zeros_raster, no_data_value, CODAGE_8B)

            # Vectorisation du masque binaire true data/false data -> polygone avec uniquement les vraies valeurs
            if os.path.exists(binary_mask_zeros_vector):
                removeVectorFile(binary_mask_zeros_vector, format_vector)

            # Polygonisation
            polygonizeRaster(binary_mask_zeros_raster, binary_mask_zeros_vector, binary_mask_zeros_name, ID, format_vector)

            # Simplification du masque obtenu
            simplifyVector(binary_mask_zeros_vector, binary_mask_zeros_vector_simpl, 2, format_vector)

            # Buffer négatif sur ce polygone
            bufferVector(binary_mask_zeros_vector_simpl, true_values_buffneg, -2, "", 1.0, 10, format_vector)
            cleanMiniAreaPolygons(sobel_binary_mask_vector, sobel_binary_mask_vector_cleaned, 15, ID, format_vector)

            # Découpe par le buffer négatif autour des true data
            cutVectorAll(true_values_buffneg, sobel_binary_mask_vector_cleaned, ouvrages_decoup_final, overwrite, format_vector)
            sobel_ouvrages_shp_list.append(ouvrages_decoup_final)

        return sobel_ouvrages_shp_list

###########################################################################################################################################
# MISE EN PLACE DU PARSER                                                                                                                 #
###########################################################################################################################################

# Code executé seulement dans le cas ou le script est lancé depuis une ligne de commande
# Il n'est pas executé lors d'un import EdgeExtraction.py.py
# Exemple de lancement en ligne de commande:
# python /home/scgsi/Documents/ChaineTraitement/ScriptsLittoral/EdgeExtractionOuvrages.py -isd "/mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Test_TDCSeuil/image1.tif:0.2,0.3 /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Test_TDCSeuil/image2.tif:0.1,0.25" -c -outd /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Tests/Tests_EdgeExtractionOuvrages -d /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/08_Donnees/Histolitt/TCH_simplifie2_buffer270_adapte_mediterranee_simpl200.shp

def main(gui=False):

    parser = argparse.ArgumentParser(prog="EdgeExtraction", description=" \
    Info : Creating an shapefile (.shp) containing the structures from a coastline by the edge extraction (Sobel) method.\n\
    Objectif   : Extrait les ouvrages à partir d'une image brute ou NDVI par la méthode de détection des ouvrages (Sobel). \n\
    Example : python /home/scgsi/Documents/ChaineTraitement/ScriptsLittoral/EdgeExtractionOuvrages.py \n\
                -isd \"/mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Test_TDCSeuil/image1.tif:0.2,0.3 /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Test_TDCSeuil/image2.tif:0.1,0.25\" \n\
                -c \n\
                -outd /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Tests/Tests_EdgeExtractionOuvrages \n\
                -d /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/08_Donnees/Histolitt/TCH_simplifie2_buffer270_adapte_mediterranee_simpl200.shp")

    parser.add_argument('-isd','--input_im_seuils_dico', default="", help="Dictionnary associating raw image withits thresholds for binary mask on Sobel image and potentially its NDWI2 image (if calc_ndwi2 == False).", type=str, required=True)
    parser.add_argument('-outd','--output_dir', default="",help="Output directory.", type=str, required=True)
    parser.add_argument('-d','--input_cut_vector', default="",help="Cutting file.", type=str, required=True)
    parser.add_argument('-c','--calc_ndwi2_image', action='store_true', default=False, help="True if input images are raw images, False if they are already calculated index images.", required=False)
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

    # Récupération de l'image en entrée
    if args.input_im_seuils_dico != None :
        input_im_seuils_dico = args.input_im_seuils_dico

    # Récupération du dossier des traitements en sortie
    if args.output_dir != None :
        output_dir = args.output_dir

    # Récupération du fichier pour la découpe (suppression des artéfacts)
    if args.input_cut_vector != None :
        input_cut_vector = args.input_cut_vector

    # Récupération de la valeur (True/False) du calcul du NDWI2
    if args.calc_ndwi2_image != None :
        calc_ndwi2_image = args.calc_ndwi2_image

    # Récupération du parametre no_data_value
    if args.no_data_value!= None:
        no_data_value = args.no_data_value

    # Récupération du nom du fichier log
    if args.path_time_log != None:
        path_time_log = args.path_time_log

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
        print(cyan + "edgeExtractionOuvrages : " + endC + "input_im_seuils_dico : " + str(input_im_seuils_dico) + endC)
        print(cyan + "edgeExtractionOuvrages : " + endC + "output_dir : " + str(output_dir) + endC)
        print(cyan + "edgeExtractionOuvrages : " + endC + "input_cut_vector : " + str(input_cut_vector) + endC)
        print(cyan + "edgeExtractionOuvrages : " + endC + "calc_ndwi2_image : " + str(calc_ndwi2_image) + endC)
        print(cyan + "edgeExtractionOuvrages : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "edgeExtractionOuvrages : " + endC + "format_raster : " + str(format_raster) + endC)
        print(cyan + "edgeExtractionOuvrages : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "edgeExtractionOuvrages : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "edgeExtractionOuvrages : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "edgeExtractionOuvrages : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "edgeExtractionOuvrages : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "edgeExtractionOuvrages : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "edgeExtractionOuvrages : " + endC + "debug : " + str(debug) + endC)

    # Fonction générale
    edgeExtractionOuvrages(input_im_seuils_dico, output_dir, input_cut_vector, calc_ndwi2_image, no_data_value, path_time_log, format_raster, format_vector, extension_raster, extension_vector, save_results_intermediate, overwrite)

# ================================================

if __name__ == '__main__':
  main(gui=False)
