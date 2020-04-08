#! /usr/bin/env pyt/hon
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerSO/DALETT/SCGSI  All rights reserved.                                                                            #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT DE CLASSIFICATION EN MICRO-CLASSES À PARTIR DE BASES DE DONNÉES EXTERNES                                                           #
#                                                                                                                                           #
#############################################################################################################################################

'''
Nom de l'objet : BDToSamples.py
Description    :
    Objectif   : Crée un unique fichier vecteur contenant toutes les micro-classes constitué à partir des bases de données externes

Date de creation : 09/08/2016
'''

from __future__ import print_function
import sys, os, argparse
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_text import extractDico
from Lib_log import timeLine
from Lib_raster import rasterizeBinaryVector
from MacroSamplesCreation import createMacroSamples
from KmeansMaskApplication import applyKmeansMasks
from MicroSamplePolygonization import polygonize_gdal, cleanMergeVectors_ogr
from MacroSamplesAmelioration import processMacroSamples

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 3

###########################################################################################################################################
# FONCTION BDToSamples                                                                                                                    #
###########################################################################################################################################
# ROLE:
#    Création d'un shapefile contenant tous les échantillons fusionnés à partir de shapefiles issus de BD exogènes (formation des macroclasses)
#
# ENTREES DE LA FONCTION :
#    input_image : Image en entrée
#    output_dir : Répertoire de sortie pour les traitements
#    input_bd_buff_dico : Dictionnaire contenant toutes les informations sur les macroclasses
#    input_index_images_list : Liste des images indice pour l'amélioration des macroclasses
#    no_data_value : Valeur de  pixel du no data
#    path_time_log : le fichier de log de sortie
#    project_encoding : encodage des vecteurs de sortie, par defaut = 'UTF-8'
#    epsg : code EPSG des entrees et des sorties  par defaut = 2154
#    format_vector  : format des vecteurs de sortie, par defaut = 'ESRI Shapefile'
#    extension_raster : extension des fichiers raster de sortie, par defaut = '.tif'
#    extension_vector : extension du fichier vecteur de sortie, par defaut = '.shp'
#    save_results_intermediate : fichiers de sorties intermediaires non nettoyées, par defaut = False
#    overwrite : supprime ou non les fichiers existants ayant le meme nom
#
# SORTIES DE LA FONCTION :
#    Le fichier vecteur contenant les échantillons des micro-classes
#    Eléments modifiés aucun
#

def BDToSamples(input_image, output_dir, input_bd_buff_dico, input_index_images_list, no_data_value, path_time_log, project_encoding="UTF-8", epsg=2154, format_vector="ESRI Shapefile", extension_raster=".tif", extension_vector=".shp", save_results_intermediate=True, overwrite=True):
    # Mise à jour du Log
    starting_event = "BDToSamples() : Select BDToSamples starting : "
    timeLine(path_time_log,starting_event)

    # Affichage des paramètres
    if debug >= 3:
        print(bold + green + "Variables dans le parser" + endC)
        print(cyan + "BDToSamples : " + endC + "input_image : " + str(input_image) + endC)
        print(cyan + "BDToSamples : " + endC + "output_dir : " + str(output_dir) + endC)
        print(cyan + "BDToSamples : " + endC + "input_bd_buff_dico : " + str(input_bd_buff_dico) + endC)
        print(cyan + "BDToSamples : " + endC + "input_index_images_list : " + str(input_index_images_list) + endC)
        print(cyan + "BDToSamples : " + endC + "project_encoding : " + str(project_encoding) + endC)
        print(cyan + "BDToSamples : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "BDToSamples : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "BDToSamples : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "BDToSamples : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "BDToSamples() : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "BDToSamples : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "BDToSamples : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "BDToSamples : " + endC + "overwrite : " + str(overwrite) + endC)


    # Initialisation des constantes
    EXTENSION_TEXT = ".txt"
    REP_TEMP = "temp_BDToSamples"
    ID_CLASS = "id_class"
    INDEX_NDVI = "NDVI"
    INDEX_NDWI2 = "NDWI2"
    CODAGE = "uint8"

    SUFFIX_MASK = "_mask"
    SUFFIX_KMEANS = "_kmeans"
    SUFFIX_CENTROID = "_centroid"
    SUFFIX_POLYGON = "_polygon"
    SUFFIX_VECTOR = "_vector"
    SUFFIX_OUTPUT = "_output"
    SUFFIX_TABLE_REALLOC = "_table_realloc"
    SUFFIX_SAMPLES_MERGED = "_samples_merged"
    SUFFIX_CORRECTED = "_corrected_"

    # Variables
    repertory_temp = output_dir + os.sep + REP_TEMP
    sample_masks_final_list = []
    sample_kmeans_masks_list = []
    macroclass_labels_list = []
    nb_macroclass_samples_list = []
    centroids_list = []
    polygons_list = []
    buffer_size_list_clean = []
    buffer_approximate_list_clean = []
    minimal_area_list_clean = []
    simplification_tolerance_list_clean = []

    # Création du répertoire de sortie s'il n'existe pas déjà
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Création du répertoire de sortie temporaire s'il n'existe pas déjà
    if not os.path.exists(repertory_temp):
        os.makedirs(repertory_temp)

    # Initialisation des nom de fichiers
    input_image_name = os.path.splitext(os.path.basename(input_image))[0]
    #output_vector = repertory_temp + os.sep + input_image_name + SUFFIX_OUTPUT + SUFFIX_VECTOR + extension_vector
    output_proposal_table = repertory_temp + os.sep + input_image_name + SUFFIX_TABLE_REALLOC + SUFFIX_VECTOR + EXTENSION_TEXT
    output_merged = repertory_temp + os.sep + input_image_name + SUFFIX_SAMPLES_MERGED + extension_vector

    input_bd_buff_dico = extractDico(input_bd_buff_dico)

    # Traitements et remplissage des listes pour chaque macroclasse
    for sample, list_param in input_bd_buff_dico.items():

        repertory_sample = repertory_temp + os.sep + sample
        # Création du répertoire de sortie par macroclasse s'il n'existe pas
        if not os.path.exists(repertory_sample):
            os.makedirs(repertory_sample)

        output_sample = repertory_sample + os.sep + sample + extension_vector
        sample_mask = repertory_sample + os.sep + sample + SUFFIX_MASK + extension_raster

        sample_kmeans_mask = repertory_sample + os.sep + sample + SUFFIX_KMEANS + SUFFIX_MASK_KMEANS + extension_raster
        sample_kmeans_masks_list.append(sample_kmeans_mask)

        macroclass_label = list_param[0][0]
        macroclass_labels_list.append(macroclass_label)

        nb_macroclass_sample = list_param[0][1]
        nb_macroclass_samples_list.append(nb_macroclass_sample)

        centroid = repertory_sample + os.sep + sample + SUFFIX_CENTROID + EXTENSION_TEXT
        centroids_list.append(centroid)

        polygon = repertory_sample + os.sep + sample + SUFFIX_POLYGON + extension_vector
        polygons_list.append(polygon)

        bd_shp = list_param[0][2]
        buffer_shp = float(list_param[0][3])

        buffer_size_list_clean.append(-0.5)
        buffer_approximate_list_clean.append(2)
        minimal_area_list_clean.append(10)
        simplification_tolerance_list_clean.append(1)

        bd_shp_list = []
        bd_shp_list.append(bd_shp)

        buffer_size_list = []
        buffer_size_list.append(buffer_shp)
        createMacroSamples(input_image, output_sample, "", "", bd_shp_list, buffer_size_list, None, path_time_log, "", 10.0, format_vector, extension_vector, save_results_intermediate, overwrite)
        rasterizeBinaryVector(output_sample, input_image, sample_mask, 1, CODAGE)

    # Amélioration des échantillons avec seuils sur les images indices
    if input_index_images_list != "":
        for sample, list_param in input_bd_buff_dico.items():
            repertory_sample = repertory_temp + os.sep + sample
            if len(list_param[0]) == 7 :
                sample_mask_to_correct = repertory_sample + os.sep + sample + SUFFIX_MASK + extension_raster
                seuil_bas = list_param[0][5]
                seuil_haut = list_param[0][6]
                if list_param[0][4] == INDEX_NDVI:
                    sample_mask_corrected_NDVI = repertory_sample + os.sep + sample + SUFFIX_MASK + SUFFIX_CORRECTED + INDEX_NDVI + extension_raster
                    sample_masks_final_list.append(sample_mask_corrected_NDVI)
                    treatment_mask_list = [INDEX_NDVI, seuil_bas, seuil_haut, "0", "0", "and"]
                    processMacroSamples(sample_mask_to_correct, sample_mask_corrected_NDVI, input_index_images_list[0], treatment_mask_list, INDEX_NDVI, path_time_log, extension_raster, save_results_intermediate, overwrite)

                elif list_param[0][4] == INDEX_NDWI2:
                    sample_mask_corrected_NDWI2 = repertory_sample + os.sep + sample + SUFFIX_MASK + SUFFIX_CORRECTED + INDEX_NDWI2 + extension_raster
                    sample_masks_final_list.append(sample_mask_corrected_NDWI2)
                    treatment_mask_list = [INDEX_NDWI2, seuil_bas, seuil_haut, "0", "0", "and"]
                    processMacroSamples(sample_mask_to_correct, sample_mask_corrected_NDWI2, input_index_images_list[1], treatment_mask_list, INDEX_NDWI2, path_time_log, save_results_intermediate, overwrite)

            else:
                sample_masks_final_list.append(repertory_sample + os.sep + sample + SUFFIX_MASK + extension_raster)

    if debug >= 2:
        print(cyan + str(sample_masks_final_list) + endC)

    applyKmeansMasks(input_image, sample_masks_final_list, "", "", sample_kmeans_masks_list, centroids_list, nb_macroclass_samples_list, macroclass_labels_list, no_data_value, path_time_log, extension_raster, save_results_intermediate, overwrite)
    polygonize_gdal(sample_kmeans_masks_list, polygons_list, path_time_log, ID_CLASS, format_vector, save_results_intermediate, overwrite)
    cleanMergeVectors_ogr(polygons_list, output_merged, output_proposal_table, path_time_log, buffer_size_list_clean, buffer_approximate_list_clean, minimal_area_list_clean, simplification_tolerance_list_clean, 10, ID_CLASS, 'GEOMETRY', 'POLYGON', format_vector, extension_raster, extension_vector, project_encoding, epsg, save_results_intermediate, overwrite)

    # Suppression du repertoire temporaire
    if not save_results_intermediate and os.path.exists(repertory_temp):
        shutil.rmtree(repertory_temp)

    # Mise à jour du Log
    ending_event = "mergeMicroclasses() : BD to samples ending : "
    timeLine(path_time_log,ending_event)

    return output_merged

###########################################################################################################################################
# MISE EN PLACE DU PARSER                                                                                                                 #
###########################################################################################################################################

# Code executé seulement dans le cas ou le script est lancé depuis une ligne de commande
# Il n'est pas executé lors d'un import BDToSamples.py
# Exemple de lancement en ligne de commande:
# python /home/scgsi/Documents/ChaineTraitement/ScriptsLittoral/BDToSamples.py -pathi /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Images_test/image2.tif -outd /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Tests/Tests_BDToSample_1008 -dico sample_foret:20000,2,/mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Images_test/BDTopo/N_ZONE_VEGETATION_BDT_030.SHP,0,NDVI,0.3,1 sample_mer:12200,1,/mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Images_test/CLC_LanRou/CLC06_R91_mer.shp,-70,NDWI2,0.15,0.8 sample_artif:11000,2,/mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Images_test/BDTopo/N_BATI_INDIFFERENCIE_BDT_030.SHP,0 sample_sable:12100,1,/mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Images_test/apprentissable.shp,0 -ind /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Images_test/image_NDVI_image2.tif /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Images_test/im_NDWI2_image2.tif

def main(gui=False):

    parser = argparse.ArgumentParser(prog="BDToSamples", description=" \
    Info : Creating an shapefile (.shp) containing the macroclasses from the database shapefiles.\n\
    Objectif   : Traite et assemble des shapefiles de bases de données exogènes pour en faire des macroclasses, qui seront utilisées pour une classification. \n\
    Example : python /home/scgsi/Documents/ChaineTraitement/ScriptsLittoral/BDToSamples.py \n\
                -pathi /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Images_test/image2.tif \n\
                -outd /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Tests/Tests_BDToSample_1008 \n\
                -dico sample_foret:20000,2,/mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Images_test/BDTopo/N_ZONE_VEGETATION_BDT_030.SHP,0,NDVI,0.3,1 sample_mer:12200,1,/mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Images_test/CLC_LanRou/CLC06_R91_mer.shp,-70,NDWI2,0.15,0.8 sample_artif:11000,2,/mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Images_test/BDTopo/N_BATI_INDIFFERENCIE_BDT_030.SHP,0 sample_sable:12100,1,/mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Images_test/apprentissable.shp,0 \n\
                -ind /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Images_test/image_NDVI_image2.tif /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Images_test/im_NDWI2_image2.tif.py")

    parser.add_argument('-pathi','--input_image', default="",help="Input image for the treatment(.tif).", type=str, required=True)
    parser.add_argument('-outd','--output_dir', default="",help="Output directory.", type=str, required=True)
    parser.add_argument('-dico','--input_bd_buff_dico', default="", nargs="+", help="Dictionnary associating the name of the macroclass with its properties.", type=str, required=True)
    parser.add_argument('-ind','--input_index_images_list', default="", nargs="+", help="List of index images (NDVI and NDWI2) to improve the result of the microclasses.", type=str, required=False)
    parser.add_argument('-pe','--project_encoding',default="UTF-8",help="Option : Format for the encoding. By default : UTF-8", type=str, required=False)
    parser.add_argument('-epsg','--epsg',default=2154,help="Option : Projection EPSG for the layers. By default : 2154", type=int, required=False)
    parser.add_argument('-ndv','--no_data_value', default=0, help="Option in option optimize_emprise_nodata  : Value of the pixel no data. By default : 0", type=int, required=False)
    parser.add_argument('-vef','--format_vector',default="ESRI Shapefile",help="Option : Vector format. By default : ESRI Shapefile", type=str, required=False)
    parser.add_argument('-rae','--extension_raster', default=".tif", help="Option : Extension file for image raster. By default : '.tif'", type=str, required=False)
    parser.add_argument('-vee','--extension_vector',default=".shp",help="Option : Extension file for vector. By default : '.shp'", type=str, required=False)
    parser.add_argument('-log','--path_time_log',default="",help="Name of log", type=str, required=False)
    parser.add_argument('-sav','--save_results_inter',action='store_true',default=False,help="Option : Save or delete intermediate result after the process. By default, False", required=False)
    parser.add_argument('-now','--overwrite',action='store_false',default=True,help="Option : Overwrite files with same names. By default : True", required=False)
    parser.add_argument('-debug','--debug',default=3,help="Option : Value of level debug trace, default : 3 ",type=int, required=False)

    args = displayIHM(gui, parser)

    # Récupération de l'image à traiter
    if args.input_image != None :
        input_image = args.input_image

    # Récupération du dossier des traitements en sortie
    if args.output_dir != None :
        output_dir = args.output_dir

    # Récupération du dictionnaire
    if args.input_bd_buff_dico != None :
        input_bd_buff_dico = args.input_bd_buff_dico

    # Récupération de la liste des images index
    if args.input_index_images_list != None :
        input_index_images_list = args.input_index_images_list

    # Récupération de la projection
    if args.epsg != None:
        epsg = args.epsg

    # Récupération de l'encodage des fichiers
    if args.project_encoding != None:
        project_encoding = args.project_encoding

    # Récupération du parametre no_data_value
    if args.no_data_value!= None:
        no_data_value = args.no_data_value

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
        print(cyan + "BDToSamples : " + endC + "input_image : " + str(input_image) + endC)
        print(cyan + "BDToSamples : " + endC + "output_dir : " + str(output_dir) + endC)
        print(cyan + "BDToSamples : " + endC + "input_bd_buff_dico : " + str(input_bd_buff_dico) + endC)
        print(cyan + "BDToSamples : " + endC + "input_index_images_list : " + str(input_index_images_list) + endC)
        print(cyan + "BDToSamples : " + endC + "project_encoding : " + str(project_encoding) + endC)
        print(cyan + "BDToSamples : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "BDToSamples : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "BDToSamples : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "BDToSamples : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "BDToSamples : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "BDToSamples : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "BDToSamples : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "BDToSamples : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "BDToSamples : " + endC + "debug : " + str(debug) + endC)

    # Fonction générale
    BDToSamples(input_image, output_dir, input_bd_buff_dico, input_index_images_list, no_data_value, path_time_log, project_encoding, epsg, format_vector, extension_raster, extension_vector, save_results_intermediate, overwrite)

# ================================================

if __name__ == '__main__':
  main(gui=False)

