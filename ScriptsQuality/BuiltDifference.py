#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT D'IDENTIFICATION DE LA DIFFERENCE DU BATI                                                                                          #
#                                                                                                                                           #
#############################################################################################################################################
"""
Nom de l'objet : BuiltDifference.py
Description :
-------------
Objectif : Réaliser identifier des différences entre la BT topo partie Bâtie et un MNS
Cela permet de préparer (copier, découper) des shapefiles(.shp) issues des BD Exogènes et les ajouter à un MNT pour en faire la différence à un MNS
Rq : utilisation des OTB Applications :   otbcli_BandMath, otbcli_BinaryMorphologicalOperation, otbcli_Rasterization
Doc : voir  Indentification_difference_batiBDtopo.odp

Date de creation : 23/02/2015
----------
Histoire :
----------
Origine :
23/02/2015 : Creation
-----------------------------------------------------------------------------------------------------
Modifications
21/05/2015 : simplification des parametres en argument plus de liste d'image en emtrée à traiter uniquement une image
------------------------------------------------------
A Reflechir/A faire
 -
 -
"""

# Import des bibliothèques python
from __future__ import print_function
import os,sys,glob,shutil,string, argparse
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_vector import simplifyVector, cutoutVectors, bufferVector, fusionVectors
from Lib_raster import createBinaryMask, createVectorMask, createDifferenceFile, filterBinaryRaster, polygonizeRaster, rasterizeVector
from Lib_index import createMNS, createNDVI
from Lib_log import timeLine
from Lib_file import cleanTempData, deleteDir, removeFile
from Lib_text import extractDico
from CrossingVectorRaster import statisticsVectorRaster

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 3

###########################################################################################################################################
# FONCTION createDifference()                                                                                                             #
###########################################################################################################################################
def createDifference(image_ortho_input, image_mns_input, image_mnt_input, bd_vector_input_list, zone_buffer_dico, departments_list, image_difference_output, vector_difference_output, fileld_bd_raster, simplifie_param, threshold_ndvi, threshold_difference, filter_difference_0, filter_difference_1, path_time_log, format_vector='ESRI Shapefile', extension_raster=".tif", extension_vector=".shp", save_results_intermediate=False, channel_order=['Red','Green','Blue','NIR'], overwrite=True) :
    """
    # ROLE:
    #    Traiter les BD exogènes
    #
    # ENTREES DE LA FONCTION :
    #    image_ortho_input : image ortho d'entrée brute
    #    image_mns_input : image du mns d'entrée
    #    image_mnt_input : image du mnt d'entrée
    #    bd_vector_input_list : liste des vecteurs de la bd exogene
    #    zone_buffer_dico : dictionaire de zone contenant les BD et les buffers à appliquer
    #    departments_list : liste des départements choisi
    #    image_difference_output :  image de différence en sortie
    #    vector_difference_output : vecteur de sortie contenant la difference
    #    fileld_bd_raster : parametre de définition du champ utiliser pour la valeur de rasterisation des données BD
    #    simplifie_param : parmetre de simplification des polygones
    #    threshold_ndvi : parametre de seuillage du NDVI
    #    threshold_difference : parametre de seuillage de la difference des MNS
    #    filter_difference_0 : parametre de filtrage du fichier de difference pour les zones à 0
    #    filter_difference_1 : parametre de filtrage du fichier de difference pour les zones à 1
    #    path_time_log : le fichier de log de sortie
    #    format_vector : format du fichier vecteur. Optionnel, par default : 'ESRI Shapefile'
    #    extension_raster : extension des fichiers raster de sortie, par defaut = '.tif'
    #    extension_vector : extension du fichier vecteur de sortie, par defaut = '.shp'
    #    save_results_intermediate : fichiers de sorties intermediaires nettoyees, par defaut à False
    #    channel_order : identifiant des canaux de l'image ortho, example : {"Red":1,"Green":2,"Blue":3,"Red_edge":4,"NIR":5}, defaut=[Red,Green,Blue,NIR]
    #    overwrite : boolen ecrasement ou non des fichiers ayant un nom similaire, par defaut à True
    #
    # SORTIES DE LA FONCTION :
    #    auccun
    #    Eléments générés par la fonction : vecteur de differnce entre les MNS
    #
    """

    # Mise à jour du Log
    starting_event = "createDifference() : create macro samples starting : "
    timeLine(path_time_log,starting_event)

    # constantes
    CODAGE = "float"

    FOLDER_MASK_TEMP = 'Mask_'
    FOLDER_CUTTING_TEMP = 'Cut_'
    FOLDER_BUFF_TEMP = 'Buff_'
    FOLDER_RESULT_TEMP = 'Tmp_'

    SUFFIX_MASK_CRUDE = '_mcrude'
    SUFFIX_MASK = '_mask'
    SUFFIX_FILTERED = '_filtered'
    SUFFIX_VECTOR_CUT = '_decoup'
    SUFFIX_VECTOR_BUFF = '_buff'
    SUFFIX_NEW_MNS = '_new_mns'
    SUFFIX_DIFF_MNS = '_diff_mns'
    SUFFIX_NDVI = '_ndvi'

    # print
    if debug >= 3:
        print(bold + green + "Variables dans la fonction" + endC)
        print(cyan + "createDifference() : " + endC + "image_ortho_input : " + str(image_ortho_input) + endC)
        print(cyan + "createDifference() : " + endC + "image_mns_input : " + str(image_mns_input) + endC)
        print(cyan + "createDifference() : " + endC + "image_mnt_input : " + str(image_mnt_input) + endC)
        print(cyan + "createDifference() : " + endC + "bd_vector_input_list : " + str(bd_vector_input_list) + endC)
        print(cyan + "createDifference() : " + endC + "zone_buffer_dico : " + str(zone_buffer_dico) + endC)
        print(cyan + "createDifference() : " + endC + "departments_list : " + str(departments_list) + endC)
        print(cyan + "createDifference() : " + endC + "image_difference_output : " + str(image_difference_output) + endC)
        print(cyan + "createDifference() : " + endC + "vector_difference_output : " + str(vector_difference_output) + endC)
        print(cyan + "createDifference() : " + endC + "fileld_bd_raster : " + str(fileld_bd_raster) + endC)
        print(cyan + "createDifference() : " + endC + "simplifie_param : " + str(simplifie_param) + endC)
        print(cyan + "createDifference() : " + endC + "threshold_ndvi : " + str(threshold_ndvi) + endC)
        print(cyan + "createDifference() : " + endC + "threshold_difference : " + str(threshold_difference) + endC)
        print(cyan + "createDifference() : " + endC + "filter_difference_0 : " + str(filter_difference_0) + endC)
        print(cyan + "createDifference() : " + endC + "filter_difference_1 : " + str(filter_difference_1) + endC)
        print(cyan + "createDifference() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "createDifference() : " + endC + "channel_order : " + str(channel_order) + endC)
        print(cyan + "createDifference() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "createDifference() : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "createDifference() : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "createDifference() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "createDifference() : " + endC + "overwrite : " + str(overwrite) + endC)

    # ETAPE 1 : NETTOYER LES DONNEES EXISTANTES

    print(cyan + "createDifference() : " + bold + green + "NETTOYAGE ESPACE DE TRAVAIL..." + endC)

    # Nom de base de l'image
    image_name = os.path.splitext(os.path.basename(image_ortho_input))[0]

    # Test si le fichier résultat différence existe déjà et si il doit être écrasés
    check = os.path.isfile(vector_difference_output)

    if check and not overwrite: # Si le fichier difference existe deja et que overwrite n'est pas activé
        print(cyan + "createDifference() : " + bold + yellow + "File difference  " + vector_difference_output + " already exists and will not be created again." + endC)
    else:
        if check:
            try:
                removeFile(vector_difference_output)
            except Exception:
                pass # si le fichier n'existe pas, il ne peut pas être supprimé : cette étape est ignorée

        # Définition des répertoires temporaires
        repertory_output = os.path.dirname(vector_difference_output)
        repertory_output_temp =  repertory_output + os.sep + FOLDER_RESULT_TEMP + image_name
        repertory_mask_temp = repertory_output + os.sep + FOLDER_MASK_TEMP + image_name
        repertory_samples_cutting_temp = repertory_output + os.sep + FOLDER_CUTTING_TEMP + image_name
        repertory_samples_buff_temp = repertory_output + os.sep + FOLDER_BUFF_TEMP + image_name

        print(repertory_output_temp)
        print(repertory_mask_temp)
        print(repertory_samples_cutting_temp)
        print(repertory_samples_buff_temp)

        # Création des répertoires temporaire qui n'existent pas
        if not os.path.isdir(repertory_output_temp):
            os.makedirs(repertory_output_temp)
        if not os.path.isdir(repertory_mask_temp):
            os.makedirs(repertory_mask_temp)
        if not os.path.isdir(repertory_samples_cutting_temp):
            os.makedirs(repertory_samples_cutting_temp)
        if not os.path.isdir(repertory_samples_buff_temp):
            os.makedirs(repertory_samples_buff_temp)

        # Nettoyage des répertoires temporaire qui ne sont pas vide
        cleanTempData(repertory_mask_temp)
        cleanTempData(repertory_samples_cutting_temp)
        cleanTempData(repertory_samples_buff_temp)
        cleanTempData(repertory_output_temp)

        BD_topo_layers_list = []
        #zone = zone_buffer_dico.keys()[0]
        zone = list(zone_buffer_dico)[0]
        # Creation liste des couches des bd exogenes utilisées
        for layers_buffer in zone_buffer_dico[zone]:
            BD_topo_layers_list.append(layers_buffer[0] )

        print(cyan + "createDifference() : " + bold + green + "... FIN NETTOYAGE" + endC)

        # ETAPE 2 : DECOUPER LES VECTEURS

        print(cyan + "createDifference() : " + bold + green + "DECOUPAGE ECHANTILLONS..." + endC)

        # 2.1 : Création du masque délimitant l'emprise de la zone par image
        vector_mask = repertory_mask_temp + os.sep + image_name + SUFFIX_MASK_CRUDE + extension_vector
        createVectorMask(image_ortho_input, vector_mask)

        # 2.2 : Simplification du masque
        vector_simple_mask = repertory_mask_temp + os.sep + image_name + SUFFIX_MASK + extension_vector
        simplifyVector(vector_mask, vector_simple_mask, simplifie_param, format_vector)

        # 2.3 : Découpage des vecteurs copiés en local avec le masque
        vector_output_list = []
        for vector_input in bd_vector_input_list :
            vector_name = os.path.splitext(os.path.basename(vector_input))[0]
            extension = os.path.splitext(os.path.basename(vector_input))[1]
            vector_output = repertory_samples_cutting_temp + os.sep + vector_name + SUFFIX_VECTOR_CUT + extension
            vector_output_list.append(vector_output)
        cutoutVectors(vector_simple_mask, bd_vector_input_list, vector_output_list, format_vector)

        print(cyan + "createDifference() : " + bold + green + "...FIN DECOUPAGE" + endC)

        # ETAPE 3 : BUFFERISER LES VECTEURS

        print(cyan + "createDifference() : " + bold + green + "MISE EN PLACE DES TAMPONS..." + endC)

        # Parcours du dictionnaire associant la zone aux noms de fichiers et aux tampons associés
        for elem_buff in zone_buffer_dico[zone] :
            # Parcours des départements
            for dpt in departments_list :

                input_shape = repertory_samples_cutting_temp + os.sep +  elem_buff[0] + "_" + dpt + SUFFIX_VECTOR_CUT + extension_vector
                output_shape = repertory_samples_buff_temp + os.sep + elem_buff[0] + "_" + dpt + SUFFIX_VECTOR_BUFF + extension_vector
                buff = elem_buff[1]
                if os.path.isfile(input_shape):
                    if debug >= 3:
                        print(cyan + "createDifference() : " + endC + "input_shape : " + str(input_shape) + endC)
                        print(cyan + "createDifference() : " + endC + "output_shape : " + str(output_shape) + endC)
                        print(cyan + "createDifference() : " + endC + "buff : " + str(buff) + endC)
                    bufferVector(input_shape, output_shape, buff, "", 1.0, 10, format_vector)
                else :
                    print(cyan + "createDifference() : " + bold + yellow + "Pas de fichier du nom : " + endC + input_shape)


        print(cyan + "createDifference() : " + bold + green + "FIN DE L AFFECTATION DES TAMPONS" + endC)

        # ETAPE 4 : FUSION DES SHAPES DE LA BD TOPO

        print(cyan + "createDifference() : " + bold + green + "FUSION DATA BD..." + endC)

        shape_buff_list = []
        # Parcours du dictionnaire associant la zone au nom du fichier
        for elem_buff in zone_buffer_dico[zone] :
            # Parcours des départements
            for dpt in departments_list :
                shape_file = repertory_samples_buff_temp + os.sep + elem_buff[0] + "_" + dpt + SUFFIX_VECTOR_BUFF + extension_vector

                if os.path.isfile(shape_file):
                    shape_buff_list.append(shape_file)
                    print("file for fusion : " + shape_file)
                else :
                    print(bold + yellow + "pas de fichiers avec ce nom : " + endC + shape_file)

            # si une liste de fichier shape existe
            if not shape_buff_list:
                print(bold + yellow + "Pas de fusion sans donnee a fusionnee" + endC)
            else :
                # Fusion des fichiers shape
                image_zone_shape = repertory_output_temp + os.sep + image_name + '_' + zone + extension_vector
                fusionVectors (shape_buff_list, image_zone_shape)

        print("File BD : " + image_zone_shape)
        print(cyan + "createDifference() : " + bold + green + "FIN DE LA FUSION" + endC)

    # ETAPE 5 : RASTERISER LE FICHIER SHAPE DE ZONE BD
    print(cyan + "createDifference() : " + bold + green + "RASTERIZATION DE LA FUSION..." + endC)
    image_zone_raster = repertory_output_temp + os.sep + image_name + '_' + zone + extension_raster
    rasterizeVector(image_zone_shape, image_zone_raster, image_ortho_input, fileld_bd_raster, codage=CODAGE)
    print(cyan + "createDifference() : " + bold + green + "FIN DE LA RASTERIZATION" + endC)

    # ETAPE 6 : CREER UN NOUVEAU MMS ISSU DU MNT + DATA BD_TOPO
    print(cyan + "createDifference() : " + bold + green + "CREATION NOUVEAU MNS..." + endC)
    image_new_mns_output = repertory_output_temp + os.sep + image_name + SUFFIX_NEW_MNS + extension_raster
    createMNS(image_ortho_input, image_mnt_input, image_zone_raster, image_new_mns_output)
    print(cyan + "createDifference() : " + bold + green + "FIN DE LA CREATION MNS" + endC)

    # ETAPE 7 : CREER D'UN MASQUE SUR LES ZONES VEGETALES
    print(cyan + "createDifference() : " + bold + green + "CREATION DU NDVI..." + endC)
    image_ndvi_output = repertory_output_temp + os.sep + image_name + SUFFIX_NDVI + extension_raster
    createNDVI(image_ortho_input, image_ndvi_output, channel_order)
    print(cyan + "createDifference() : " + bold + green + "FIN DE LA CREATION DU NDVI" + endC)

    print(cyan + "createDifference() : " + bold + green + "CREATION DU MASQUE NDVI..." + endC)
    image_ndvi_mask_output = repertory_output_temp + os.sep + image_name + SUFFIX_NDVI + SUFFIX_MASK + extension_raster
    createBinaryMask(image_ndvi_output, image_ndvi_mask_output, threshold_ndvi, False)
    print(cyan + "createDifference() : " + bold + green + "FIN DE LA CREATION DU MASQUE NDVI" + endC)

    # ETAPE 8 : CREER UN FICHIER DE DIFFERENCE DES MNS AVEC MASQUAGE DES ZONES VEGETALES
    print(cyan + "createDifference() : " + bold + green + "CREATION DIFFERENCE MNS..." + endC)
    #image_diff_mns_output = repertory_output + os.sep + image_name + SUFFIX_DIFF_MNS + extension_raster
    image_diff_mns_output = image_difference_output
    createDifferenceFile(image_mns_input, image_new_mns_output, image_ndvi_mask_output, image_diff_mns_output)
    print(cyan + "createDifference() : " + bold + green + "FIN DE LA CREATION DE LA DIFFERENCE MNS" + endC)

    print(cyan + "createDifference() : " + bold + green + "CREATION DU MASQUE DE DIFFERENCE..." + endC)
    image_diff_mns_mask_output = repertory_output_temp + os.sep + image_name + SUFFIX_DIFF_MNS + SUFFIX_MASK + extension_raster
    createBinaryMask(image_diff_mns_output, image_diff_mns_mask_output, threshold_difference, True)
    print(cyan + "createDifference() : " + bold + green + "FIN DE LA CREATION DU MASQUE DE DIFFERENCE" + endC)

    print(cyan + "createDifference() : " + bold + green + "FILTRAGE DU MASQUE DE DIFFERENCE..." + endC)
    image_diff_mns_filtered_output = repertory_output_temp + os.sep + image_name + SUFFIX_DIFF_MNS + SUFFIX_FILTERED + extension_raster
    filterBinaryRaster(image_diff_mns_mask_output, image_diff_mns_filtered_output, filter_difference_0, filter_difference_1)
    print(cyan + "createDifference() : " + bold + green + "FIN DU FILTRAGE DU MASQUE DE DIFFERENCE" + endC)

    # ETAPE 9 : RASTERISER LE FICHIER DE DIFFERENCE DES MNS
    print(cyan + "createDifference() : " + bold + green + "VECTORISATION DU RASTER DE DIFFERENCE..." + endC)
    vector_diff_mns_filtered_output = repertory_output_temp + os.sep + image_name + SUFFIX_DIFF_MNS + SUFFIX_FILTERED + extension_vector
    polygonizeRaster(image_diff_mns_filtered_output, vector_diff_mns_filtered_output, image_name, field_name="DN")
    print(cyan + "createDifference() : " + bold + green + "FIN DE VECTORISATION DU RASTER DE DIFFERENCE" + endC)

    print(cyan + "createDifference() : " + bold + green + "SIMPLIFICATION VECTEUR DE DIFFERENCE..." + endC)
    simplifyVector(vector_diff_mns_filtered_output, vector_difference_output, simplifie_param, format_vector)
    print(cyan + "createDifference() : " + bold + green + "FIN DE SIMPLIFICATION DI VECTEUR DE DIFFERENCE" + endC)

    # ETAPE 10 : SUPPRESIONS FICHIERS INTERMEDIAIRES INUTILES
    if not save_results_intermediate:

        # Supression des .geom dans le dossier
        for to_delete in glob.glob(repertory_mask_temp + os.sep + "*.geom"):
            removeFile(to_delete)

        # Suppression des repertoires temporaires
        deleteDir(repertory_mask_temp)
        deleteDir(repertory_samples_cutting_temp)
        deleteDir(repertory_samples_buff_temp)
        deleteDir(repertory_output_temp)

    # Mise à jour du Log
    ending_event = "createDifference() : create macro samples ending : "
    timeLine(path_time_log,ending_event)

    return

###########################################################################################################################################
# MISE EN PLACE DU PARSER                                                                                                                 #
###########################################################################################################################################

# Code executé seulement dans le cas ou le script est lancé depuis une ligne de commande
# Il n'est pas executé lors d'un import BuiltDifference.py
# Exemple de lancement en ligne de commande:
# python BuiltDifference.py -i /mnt/hgfs/Data_Image_Saturn/Test_Methode_CUB_zone_test_NE_1/CUB_zone_test_NE_1.tif -imns /mnt/hgfs/Data_Image_Saturn/Test_Methode_CUB_zone_test_NE_1/MNS_CUB_zone_test_NE_1.tif -imnt /mnt/hgfs/Data_Image_Saturn/Test_Methode_CUB_zone_test_NE_1/MNT_CUB_zone_test_NE_1.tif -o /mnt/hgfs/Data_Image_Saturn/Test_Methode_CUB_zone_test_NE_1/Result/CUB_zone_test_NE_1_diff.tif -v /mnt/hgfs/Data_Image_Saturn/Test_Methode_CUB_zone_test_NE_1/Result/CUB_zone_test_NE_1_diff_mns.shp -ibdl /mnt/hgfs/Data_Image_Saturn/BD/BATI_INDIFFERENCIE_033.shp /mnt/hgfs/Data_Image_Saturn/BD/BATI_INDUSTRIEL_033.shp -dep 033 -tndvi 0.3 -tdiff 8.0 -fdif0 5 -fdif1 10 -log  /mnt/hgfs/Data_Image_Saturn/Test_Methode_CUB_zone_test_NE_1/fichierTestLog.txt -sav

def main(gui=False):

   # Définition des arguments possibles pour l'appel en ligne de commande
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, prog="BuiltDifference",description="\
    Info : Create macro samples. \n\
    Objectif : Realiser identifier des differences entre la BT topo partie Batie et un MNS. \n\
    Example : python BuiltDifference.py -i /mnt/hgfs/Data_Image_Saturn/Test_Methode_CUB_zone_test_NE_1/CUB_zone_test_NE_1.tif \n\
                                        -imns /mnt/hgfs/Data_Image_Saturn/Test_Methode_CUB_zone_test_NE_1/MNS_CUB_zone_test_NE_1.tif \n\
                                        -imnt /mnt/hgfs/Data_Image_Saturn/Test_Methode_CUB_zone_test_NE_1/MNT_CUB_zone_test_NE_1.tif \n\
                                        -o /mnt/hgfs/Data_Image_Saturn/Test_Methode_CUB_zone_test_NE_1/Result/CUB_zone_test_NE_1_diff.tif \n\
                                        -v /mnt/hgfs/Data_Image_Saturn/Test_Methode_CUB_zone_test_NE_1/Result/CUB_zone_test_NE_1_diff_mns.shp \n\
                                        -ibdl /mnt/hgfs/Data_Image_Saturn/BD/BATI_INDIFFERENCIE_033.shp \n\
                                              /mnt/hgfs/Data_Image_Saturn/BD/BATI_INDUSTRIEL_033.shp \n\
                                        -dep 033 \n\
                                        -tndvi 0.3 -tdiff 8.0 -fdif0 5 -fdif1 10 \n\
                                        -log  /mnt/hgfs/Data_Image_Saturn/Test_Methode_CUB_zone_test_NE_1/fichierTestLog.txt")

    # Paramètres généraux
    parser.add_argument('-i','--image_input',default="",help="Image input to treat", type=str, required=True)
    parser.add_argument('-imns','--image_mns',default="",help="Image input of MNS", type=str, required=True)
    parser.add_argument('-imnt','--image_mnt',default="",help="Image input of MNT", type=str, required=True)
    parser.add_argument('-o','--image_output',help="Image output result difference",type=str, required=False)
    parser.add_argument('-v','--vector_output',help="Vector output result difference",type=str, required=False)
    parser.add_argument('-ibdl','--bd_vector_input_list',default="",nargs="+",help="List containt bd vector input concatened to create vector sample", type=str, required=True)
    parser.add_argument('-field','--fileld_bd_raster',default="HAUTEUR", help="Filled value used to rasterize shape BD", type=str, required=False)
    parser.add_argument('-zone','--zone_buff_dico',nargs="+",default=["Bati:BATI_INDIFFERENCIE,0:BATI_INDUSTRIEL,0"], help="Dictionary of zone containt bd and buffer, (format : zone:[BD,sizeBuffer][..]), ex. Bati:BATI_INDIFFERENCIE,0:BATI_INDUSTRIEL,0", type=str, required=False)
    parser.add_argument('-dep','--departments_list',default="",nargs="+",help="List sources departements selected (add a 0 before dep begining by 0), ex. 001 33.", type=str, required=True)
    parser.add_argument('-simp','--simple_param_vector',default=2.0,help="Parameter of polygons simplification. By default : 2.0", type=float, required=False)
    parser.add_argument('-tndvi','--threshold_ndvi',default=0.25,help="Parameter of threshold ndvi. By default : 0.25", type=float, required=False)
    parser.add_argument('-tdiff','--threshold_difference',default=6.0,help="Parameter of threshold difference mns. By default : 6.0", type=float, required=False)
    parser.add_argument('-fdif0','--filter_difference_0',default=5,help="Parameter of filter clean 0 value, result difference. By default : 5", type=int, required=False)
    parser.add_argument('-fdif1','--filter_difference_1',default=15,help="Parameter of filter clean 1 value, result difference. By default : 15", type=int, required=False)
    parser.add_argument('-chao','--channel_order',nargs="+", default=['Red','Green','Blue','NIR'],help="Type of multispectral image : rapideye or spot6 or pleiade. By default : [Red,Green,Blue,NIR]",type=str,required=False)
    parser.add_argument('-ndv','--no_data_value', default=0, help="Option : Value of the pixel no data. By default : 0", type=int, required=False)
    parser.add_argument('-vef','--format_vector', default="ESRI Shapefile",help="Format of the output file.", type=str, required=False)
    parser.add_argument('-rae','--extension_raster', default=".tif", help="Option : Extension file for image raster. By default : '.tif'", type=str, required=False)
    parser.add_argument('-vee','--extension_vector',default=".shp",help="Option : Extension file for vector. By default : '.shp'", type=str, required=False)
    parser.add_argument('-log','--path_time_log',default="",help="Name of log", type=str, required=False)
    parser.add_argument('-sav','--save_results_inter',action='store_true',default=False,help="Save or delete intermediate result after the process. By default, False", required=False)
    parser.add_argument('-now','--overwrite',action='store_false',default=True,help="Overwrite files with same names. By default, True",required=False)
    parser.add_argument('-debug','--debug',default=3,help="Option : Value of level debug trace, default : 3 ",type=int, required=False)
    args = displayIHM(gui, parser)

    # RECUPERATION DES ARGUMENTS

    # Récupération des arguments du parser images d'entrées
    if args.image_input != None:
        image_input = args.image_input
        if not os.path.isfile(image_input):
            raise NameError (cyan + "BuiltDifference : " + bold + red  + "File %s not existe!" %(image_input) + endC)

    if args.image_mns != None:
        image_mns = args.image_mns
        if not os.path.isfile(image_mns):
            raise NameError (cyan + "BuiltDifference : " + bold + red  + "File %s not existe!" %(image_mns) + endC)

    if args.image_mnt != None:
        image_mnt = args.image_mnt
        if not os.path.isfile(image_mnt):
            raise NameError (cyan + "BuiltDifference : " + bold + red  + "File %s not existe!" %(image_mnt) + endC)

    # Récupération des vecteurs de bd exogenes
    if args.bd_vector_input_list != None :
        bd_vector_input_list = args.bd_vector_input_list

    # Récupération des arguments du parser images de sorties
    if args.image_output != None:
        image_output = args.image_output

    if args.vector_output != None:
        vector_output = args.vector_output

    # Récupération des info données
    if args.departments_list != None :
        departments_list = args.departments_list

    if args.fileld_bd_raster != None :
        fileld_bd_raster = args.fileld_bd_raster

    # creation du dictionaire table macro class contenant la BD et le buffer
    if args.zone_buff_dico != None:
        zone_buffer_dico = extractDico(args.zone_buff_dico)

    # Parametres de filtrage
    if args.simple_param_vector != None:
        simplifie_param = args.simple_param_vector

    if args.threshold_ndvi != None:
        threshold_ndvi = args.threshold_ndvi

    if args.threshold_difference != None:
        threshold_difference = args.threshold_difference

    if args.filter_difference_0 != None:
        filter_difference_0 = args.filter_difference_0

    if args.filter_difference_1 != None:
        filter_difference_1 = args.filter_difference_1

    # Ordre des canaux de l'image ortho
    if args.channel_order != None:
        channel_order = args.channel_order

    # Parametres de valeur du nodata
    if args.no_data_value!= None:
        no_data_value = args.no_data_value

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

    # Ecrasement des fichiers
    if args.save_results_inter != None:
        save_results_intermediate = args.save_results_inter

    if args.overwrite != None:
        overwrite = args.overwrite

    # Récupération de l'option niveau de debug
    if args.debug!= None:
        global debug
        debug = args.debug

    if debug >= 3:
        print(bold + green + "Variables dans le parser" + endC)
        print(cyan + "BuiltDifference : " + endC + "image_input : " + str(image_input) + endC)
        print(cyan + "BuiltDifference : " + endC + "image_mns : " + str(image_mns) + endC)
        print(cyan + "BuiltDifference : " + endC + "image_mnt : " + str(image_mnt) + endC)
        print(cyan + "BuiltDifference : " + endC + "image_output : " + str(image_output) + endC)
        print(cyan + "BuiltDifference : " + endC + "bd_vector_input_list : " + str(bd_vector_input_list) + endC)
        print(cyan + "BuiltDifference : " + endC + "vector_output : " + str(vector_output) + endC)
        print(cyan + "BuiltDifference : " + endC + "zone_buffer_dico : " + str(zone_buffer_dico) + endC)
        print(cyan + "BuiltDifference : " + endC + "departments_list : " + str(departments_list) + endC)
        print(cyan + "BuiltDifference : " + endC + "fileld_bd_raster : " + str(fileld_bd_raster) + endC)
        print(cyan + "BuiltDifference : " + endC + "simple_param_vector : " + str(simplifie_param) + endC)
        print(cyan + "BuiltDifference : " + endC + "threshold_ndvi : " + str(threshold_ndvi) + endC)
        print(cyan + "BuiltDifference : " + endC + "threshold_difference : " + str(threshold_difference) + endC)
        print(cyan + "BuiltDifference : " + endC + "filter_difference_0 : " + str(filter_difference_0) + endC)
        print(cyan + "BuiltDifference : " + endC + "filter_difference_1 : " + str(filter_difference_1) + endC)
        print(cyan + "BuiltDifference : " + endC + "channel_order : " + str(channel_order) + endC)
        print(cyan + "BuiltDifference : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "BuiltDifference : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "BuiltDifference : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "BuiltDifference : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "BuiltDifference : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "BuiltDifference : " + endC + "save_results_inter : " + str(save_results_intermediate) + endC)
        print(cyan + "BuiltDifference : " + endC + "overwrite: " + str(overwrite) + endC)
        print(cyan + "BuiltDifference : " + endC + "debug: " + str(debug) + endC)

    # EXECUTION DE LA FONCTION
    # Si les dossiers de sortie n'existent pas, on les crées

    repertory_output = os.path.dirname(image_output)
    if not os.path.isdir(repertory_output):
        os.makedirs(repertory_output)
    repertory_output = os.path.dirname(vector_output)
    if not os.path.isdir(repertory_output):
        os.makedirs(repertory_output)

    # execution de la fonction pour une image
    createDifference(image_input, image_mns, image_mnt, bd_vector_input_list, zone_buffer_dico, departments_list, image_output, vector_output, fileld_bd_raster, simplifie_param, threshold_ndvi, threshold_difference, filter_difference_0, filter_difference_1, path_time_log, format_vector, extension_raster, extension_vector, save_results_intermediate, channel_order, overwrite)
    # ajouter les valeurs des hauteurs en champs suplementaire au shape
    statisticsVectorRaster(image_output, vector_output, "", 1, False, False, True, [], [], {}, True, no_data_value, format_vector, path_time_log, save_results_intermediate, overwrite)

# ================================================

if __name__ == '__main__':
  main(gui=False)
