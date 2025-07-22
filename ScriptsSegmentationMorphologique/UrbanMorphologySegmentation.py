#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT DE CREATION D'UNE SEGMENTATION MORPHOLOGIE URBAINE AFIN DE SEGMENTER LES POLYGONES A L'ECHELLE DES QUARTIERS                       #
#                                                                                                                                           #
#############################################################################################################################################

"""
Nom de l'objet : UrbanMorphologySegmentation.py
Description :
    Objectif : Sortie un decoupage d'une zone urbaine par segmentation morphologique.

Date de creation : 25/01/2024
----------
Histoire :
----------
Origine : Fonction qui à pour but la segmentation morphologique du tissu urbain, suite au stage de Levis Antonetti (Tuteurs: Aurélien Mure, Gilles Fouvet).

-----------------------------------------------------------------------------------------------------
Modifications

------------------------------------------------------
"""

# Import des bibliothèques python
from __future__ import print_function
import os, sys, glob, copy, string, time, shutil, numpy, argparse
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_log import timeLine
from CreateDataIndicateurPseudoRGB import createDataIndicateurPseudoRGB
from SLICsegmentation import processingSLIC, DEFAULT_PARAMETERS_SLIC
from SegPostProcessing import segPostProcessing
from PolygonsMerging import segPolygonsMerging

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 2

###########################################################################################################################################
# FONCTION processSegmentationUrbanMorpho()                                                                                               #
###########################################################################################################################################
def processSegmentationUrbanMorpho(base_folder, emprise_vector, OSO_file_input, QML_file_input, vectors_road_input_list, vectors_railway_input_list, vectors_build_input_list, vectors_water_area_input_list, sql_exp_road_list, sql_exp_railway_list, sql_exp_build_list, sql_exp_water_list, OSO_file_output, pseudoRGB_file_output, raster_build_height_output, vector_roads_output, vector_roads_main_output, vector_waters_area_output, vector_line_skeleton_main_roads_output, vector_roads_pres_seg_output, vector_file_seg_algo, vector_file_seg_post, vector_file_seg_output, optimize_slic_parameters=True, road_importance_field="IMPORTANCE", road_importance_threshold=4, road_width_field="LARGEUR", road_nature_field="NATURE", railway_nature_field="NATURE", railway_importance_values="Principale", buffer_size_skeleton=35.0, extension_length_lines=20,  min_area_water_area=100000.0, project_encoding="latin1", server_postgis="localhost", port_number=5433, user_postgis="postgres", password_postgis="postgres", database_postgis="cutbylines", schema_postgis="public", resolution=5, no_data_value=0, epsg=2154, format_raster='GTiff', format_vector='ESRI Shapefile', extension_raster=".tif", extension_vector=".shp", path_time_log="", save_results_intermediate=False, overwrite=True) :

    """
    # ROLE:
    #     Verifier et corrige des vecteurs resultats de classifications OCS en traitement sous postgis
    #
    # ENTREES DE LA FONCTION :
    #     base_folder (str): Base repertoire de travail des fichiers temporaires et de sorties.
    #     emprise_vector (str): le vecteur d'emprise de référence.
    #     OSO_file_input (str): chemin vers le fichier raster d'entrée OSO(Occupation du sol).
    #     QML_file_input (str):chemin vers le fichier xml de style pour l'OSO (Fichier de style QGIS).
    #     vectors_road_input_list (list) : les fichiers contenant les routes d'entrée (routes primaires et secondaires).
    #     vectors_railway_input_list (list) : list of paths to railway files (voies ferrées).
    #     vectors_build_input_list (list) : les fichiers contenant les batis d'entrée.
    #     vectors_water_area_input_list (list) : les fichiers contenant les surfaces en eau d'entrée.
    #     sql_exp_road_list (list) : liste d'expression sql pour le filtrage des fichiers vecteur de bd exogenes routes.
    #     sql_exp_railway_list (list) : liste d'expression sql pour le filtrage des fichiers vecteur de bd exogenes voies ferrées.
    #     sql_exp_build_list (list) : liste d'expression sql pour le filtrage des fichiers vecteur de bd exogenes batis.
    #     sql_exp_water_list (list) : liste d'expression sql pour le filtrage des fichiers vecteur de bd exogenes surfaces en eau.
    #     OSO_file_output (str): fichier rastrer découpé de l'OSO resultat en sortie.
    #     pseudoRGB_file_output (str): fichier de pseudo-RGB image resultat en sortie.
    #     raster_build_height_output (str):  fichier de sortie rasteur des batis.
    #     vector_roads_output (str): fichier de sortie vecteur contenant toutes les routes.
    #     vector_roads_main_output (str) :  fichier de sortie vecteur des routes importantes à  2 voies buffurisé.
    #     vector_waters_area_output (str): fichier de sortie vecteur contenant toutes les surfaces en eaux.
    #     vector_line_skeleton_main_roads_output (str) : fichier de sortie vecteur contenant le skelette ligne des routes principales.
    #     vector_roads_pres_seg_output (str) : fichier de sortie vecteur contenant une prés segmentation avec les routes.
    #     vector_file_seg_algo (str): fichier temporaire vecteur contenant la segmentation sortie de l'algo CCM ou SLIC.
    #     vector_file_seg_post (str): fichier temporaire vecteur contenant la segmentation sortie de post tratement.
    #     vector_file_seg_output (str): fichier final vecteur contenant la segmentation apres fusion.
    #     optimize_slic_parameters (bool) : activation du calcul optimisation des parametres de SLIC( default: True).
    #     road_importance_field (str) : champs importance des routes (par defaut : "IMPORTANCE").
    #     road_importance_threshold (int) : valeur du seuil d'importance (par défaut : 4).
    #     road_width_field (str) : champs largeur des routes (par defaut : "LARGEUR").
    #     road_nature_field (str) : champ nature des routes (par défaut : "NATURE").
    #     railway_nature_field : champs nature des voies ferrées (par defaut : "NATURE").
    #     railway_importance_values : valeur des voies ferrées à garder (par defaut : "Principale").
    #     buffer_size_skeleton (float) : valeur du buffer pour l'importance des routes pour la creation du squelette (par défaut : 35.0).
    #     extension_length_lines (int) : taille de l'extension des lignes pour la segmentation route (par défaut : 20).
    #     min_area_water_area (float) : seuil minimale pour les surfaces d'eau (par défaut : 100000.0).
    #     project_encoding : encodage des fichiers d'entrés
    #     server_postgis : nom du serveur postgis
    #     port_number : numéro du port pour le serveur postgis
    #     user_postgis : le nom de l'utilisateurs postgis
    #     password_postgis : le mot de passe de l'utilisateur posgis
    #     database_postgis : le nom de la base posgis à utiliser
    #     schema_postgis : le nom du schéma à utiliser
    #     resolution (float) : défini la resolution  pixel X and Y of image
    #     no_data_value : Value pixel of no data
    #     epsg : EPSG code de projection
    #     format_raster : Format de l'image de sortie par défaut GTiff (GTiff, HFA...)
    #     format_vector : format du fichier vecteur. Optionnel, par default : 'ESRI Shapefile'
    #     extension_raster : extension des fichiers raster de sortie, par defaut = '.tif'
    #     extension_vector : extension du fichier vecteur de sortie, par defaut = '.shp'
    #     path_time_log : le fichier de log de sortie
    #     save_results_intermediate : fichiers de sorties intermediaires non nettoyees, par defaut = False
    #     overwrite : supprime ou non les fichiers existants ayant le meme nom
    #
    # SORTIES DE LA FONCTION :
    #     na
    #
    """

    # Affichage des paramètres
    if debug >= 3:
        print(bold + green + "Variables dans le processSegmentationUrbanMorpho - Variables générales" + endC)
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "base_folder : " + str(base_folder))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "emprise_vector : " + str(emprise_vector))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "OSO_file_input : " + str(OSO_file_input))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "QML_file_input : " + str(QML_file_input))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "vectors_road_input_list : " + str(vectors_road_input_list))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "vectors_railway_input_list : " + str(vectors_railway_input_list))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "vectors_build_input_list : " + str(vectors_build_input_list))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "vectors_water_area_input_list : " + str(vectors_water_area_input_list))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "sql_exp_road_list : " + str(sql_exp_road_list))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "sql_exp_railway_list : " + str(sql_exp_railway_list))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "sql_exp_build_list : " + str(sql_exp_build_list))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "sql_exp_water_list : " + str(sql_exp_water_list))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "OSO_file_output : " + str(OSO_file_output))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "pseudoRGB_file_output : " + str(pseudoRGB_file_output))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "raster_build_height_output : " + str(raster_build_height_output))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "vector_roads_output : " + str(vector_roads_output))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "vector_roads_main_output : " + str(vector_roads_main_output))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "vector_waters_area_output : " + str(vector_waters_area_output))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "vector_line_skeleton_main_roads_output : " + str(vector_line_skeleton_main_roads_output))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "vector_roads_pres_seg_output : " + str(vector_roads_pres_seg_output))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "vector_file_seg_algo : " + str(vector_file_seg_algo))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "vector_file_seg_post : " + str(vector_file_seg_post))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "vector_file_seg_output : " + str(vector_file_seg_output))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "road_importance_field : " + str(road_importance_field))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "road_importance_threshold : " + str(road_importance_threshold))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "road_width_field : " + str(road_width_field))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "road_nature_field : " + str(road_nature_field))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "railway_nature_field : " + str(railway_nature_field))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "railway_importance_values : " + str(railway_importance_values))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "buffer_size_skeleton : " + str(buffer_size_skeleton))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "extension_length_lines : " + str(extension_length_lines))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "min_area_water_area : " + str(min_area_water_area))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "project_encoding : " + str(project_encoding))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "server_postgis : " + str(server_postgis))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "port_number : " + str(port_number))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "user_postgis : " + str(user_postgis))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "password_postgis : " + str(password_postgis))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "database_postgis : " + str(database_postgis))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "schema_postgis : " + str(schema_postgis))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "resolution : " + str(resolution))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "no_data_value : " + str(no_data_value))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "epsg : " + str(epsg))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "format_raster : " + str(format_raster))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "format_vector : " + str(format_vector))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "path_time_log : " + str(path_time_log))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "save_results_intermediate : " + str(save_results_intermediate))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "overwrite : " + str(overwrite))

    # Mise à jour du Log
    starting_event = "processSegmentationUrbanMorpho() : Process urban segementation morphologique starting : "
    timeLine(path_time_log,starting_event)
    print(bold + green + "## START : SEGMENTATION  URBAN  MORPHOLOGY" + endC)

    # 1) Create Data Indicateur and PseudoRGB
    createDataIndicateurPseudoRGB(base_folder,
                                  emprise_vector,
                                  OSO_file_input,
                                  QML_file_input,
                                  vectors_road_input_list,
                                  vectors_railway_input_list,
                                  vectors_build_input_list,
                                  vectors_water_area_input_list,
                                  sql_exp_road_list,
                                  sql_exp_railway_list,
                                  sql_exp_build_list,
                                  sql_exp_water_list,
                                  OSO_file_output,
                                  pseudoRGB_file_output,
                                  raster_build_height_output,
                                  vector_roads_output,
                                  vector_roads_main_output,
                                  vector_waters_area_output,
                                  vector_line_skeleton_main_roads_output,
                                  vector_roads_pres_seg_output,
                                  road_importance_field,
                                  road_importance_threshold,
                                  road_width_field,
                                  road_nature_field,
                                  railway_nature_field,
                                  railway_importance_values,
                                  buffer_size_skeleton,
                                  extension_length_lines,
                                  min_area_water_area,
                                  resolution,
                                  no_data_value,
                                  epsg,
                                  server_postgis,
                                  port_number,
                                  user_postgis,
                                  password_postgis,
                                  database_postgis,
                                  schema_postgis,
                                  project_encoding,
                                  format_raster,
                                  format_vector,
                                  extension_raster,
                                  extension_vector,
                                  path_time_log,
                                  save_results_intermediate,
                                  overwrite
                                  )

    # 2) SLIC segmentation
    slic_parameters = DEFAULT_PARAMETERS_SLIC
    processingSLIC(base_folder,
                  emprise_vector,
                  pseudoRGB_file_output,
                  OSO_file_output,
                  vector_file_seg_algo,
                  optimize_slic_parameters,
                  slic_parameters,
                  no_data_value,
                  epsg,
                  format_vector,
                  extension_vector,
                  path_time_log,
                  save_results_intermediate,
                  overwrite
                  )

    # 3) PostProcessing of segmentation
    segPostProcessing(base_folder,
                      emprise_vector,
                      vector_roads_pres_seg_output,
                      vector_file_seg_algo,
                      vector_line_skeleton_main_roads_output,
                      vector_waters_area_output,
                      vector_file_seg_post,
                      no_data_value,
                      epsg,
                      format_raster,
                      format_vector,
                      extension_raster,
                      extension_vector,
                      path_time_log,
                      save_results_intermediate,
                      overwrite
                      )

    # 4) Polygons Merging
    segPolygonsMerging(base_folder,
                       emprise_vector,
                       OSO_file_output,
                       raster_build_height_output,
                       vector_roads_output,
                       vector_roads_main_output,
                       vector_file_seg_post,
                       vector_file_seg_output,
                       no_data_value,
                       epsg,
                       server_postgis,
                       port_number,
                       project_encoding,
                       user_postgis,
                       password_postgis,
                       database_postgis,
                       schema_postgis,
                       format_raster,
                       format_vector,
                       extension_raster,
                       extension_vector,
                       path_time_log,
                       save_results_intermediate,
                       overwrite
                       )

    # Mise à jour du Log
    print(bold + green + "## END : SEGMENTATION  URBAN  MORPHOLOGY" + endC)
    ending_event = "processSegmentationUrbanMorpho() : Process urban segementation morphologique ending : "
    timeLine(path_time_log,ending_event)

    return

###########################################################################################################################################
# MISE EN PLACE DU PARSER                                                                                                                 #
###########################################################################################################################################

# Code executé seulement dans le cas ou le script est lancé depuis une ligne de commande
# Il n'est pas executé lors d'un import UrbanMorphologySegmentation.py
# Exemple de lancement en ligne de commande:
# python UrbanMorphologySegmentation.py -r /mnt/RAM_disk/INTEGRATION
#                                      -e /mnt/RAM_disk/INTEGRATION/emprise/Emprise_Toulouse_Metropole.shp
#                                      -oso /mnt/RAM_disk/INTEGRATION/OCS_2023_in.tif
#                                      -qml /mnt/RAM_disk/INTEGRATION/oso_modif.qml
#                                      -vrl /mnt/RAM_disk/INTEGRATION/bd_topo/N_ROUTE_PRIMAIRE_BDT_031.SHP /mnt/RAM_disk/INTEGRATION/bd_topo/N_ROUTE_SECONDAIRE_BDT_031.SHP
#                                      -val /mnt/RAM_disk/INTEGRATION/bd_topo/N_TRONCON_VOIE_FERREE_BDT_031.SHP
#                                      -vbl /mnt/RAM_disk/INTEGRATION/bd_topo/N_BATI_INDIFFERENCIE_BDT_031.shp /mnt/RAM_disk/INTEGRATION/bd_topo/N_BATI_INDUSTRIEL_BDT_031.shp /mnt/RAM_disk/INTEGRATION/bd_topo/N_BATI_REMARQUABLE_BDT_031.shp
#                                      -vwl /mnt/RAM_disk/INTEGRATION/bd_topo/N_SURFACE_EAU_BDT_031.shp
#                                      -sqlr "FRANCHISST !='Tunnel'":"FRANCHISST !='Tunnel'"
#                                      -sqla "ETAT ='NR'"
#                                      -sqlb "":"NATURE !='Serre'":""
#                                      -sqlw "REGIME ='Permanent'"
#                                      -ofo /mnt/RAM_disk/INTEGRATION/create_data/result/OCS_2023_cut.tif
#                                      -rgb /mnt/RAM_disk/INTEGRATION/create_data/result/pseudoRGB_seg_res5.tif
#                                      -rbh /mnt/RAM_disk/INTEGRATION/create_data/result/builds_height.tif
#                                      -vro /mnt/RAM_disk/INTEGRATION/create_data/result/all_roads.shp
#                                      -vwo /mnt/RAM_disk/INTEGRATION/create_data/result/all_waters_area.shp
#                                      -vsk /mnt/RAM_disk/INTEGRATION/create_data/result/skeleton_primary_roads.shp
#                                      -vrps /mnt/RAM_disk/INTEGRATION/create_data/result/pres_seg_road.shp
#                                      -vfsa /mnt/RAM_disk/INTEGRATION/slic_lissage_chaiken_5.shp
#                                      -vpost /mnt/RAM_disk/INTEGRATION/seg_post_processing/toulouse_seg_post.shp
#                                      -vseg /mnt/RAM_disk/INTEGRATION/seg_res_fusion/res/toulouse_seg_end.shp

def main(gui=False):

    # Définition des différents paramètres du parser
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,  prog="UrbanMorphologySegmentation", description="\
    Info : Cutting list of raster and vector file by vector file. \n\
    Objectif : Découper des fichiers raster et vecteurs. \n\
    Example : python UrbanMorphologySegmentation.py \n\
    python UrbanMorphologySegmentation.py -r /mnt/RAM_disk/INTEGRATION \n\
                                      -e /mnt/RAM_disk/INTEGRATION/emprise_fusion.shp \n\
                                      -oso /mnt/RAM_disk/OSO_20220101_RASTER_V1-0/DATA/OCS_2022.tif \n\
                                      -qml /mnt/RAM_disk/INTEGRATION/SLIC/test.qml \n\
                                      -vrl /mnt/RAM_disk/INTEGRATION/bd_topo/N_ROUTE_PRIMAIRE_BDT_031.SHP /mnt/RAM_disk/INTEGRATION/bd_topo/N_ROUTE_SECONDAIRE_BDT_031.SHP \n\
                                      -val /mnt/RAM_disk/INTEGRATION/bd_topo/N_TRONCON_VOIE_FERREE_BDT_031.SHP \n\
                                      -vbl /mnt/RAM_disk/INTEGRATION/bd_topo/N_BATI_INDIFFERENCIE_BDT_031.SHP /mnt/RAM_disk/INTEGRATION/bd_topo/N_BATI_INDUSTRIEL_BDT_031.SHP /mnt/RAM_disk/INTEGRATION/bd_topo/N_BATI_REMARQUABLE_BDT_031.SHP \n\
                                      -vwl /mnt/RAM_disk/INTEGRATION/bd_topo/N_SURFACE_EAU_BDT_031.SHP \n\
                                      -sqlr \"FRANCHISST !='Tunnel'\":\"FRANCHISST !='Tunnel'\" \n\
                                      -sqla \"ETAT ='NR'\" \n\
                                      -sqlb \"\":\"NATURE !='Serre'\":\"\" \n\
                                      -sqlw \"REGIME ='Permanent'\" \n\
                                      -ofo /mnt/RAM_disk/INTEGRATION/create_data/result/OCS_2023_cut.tif \n\
                                      -rgb /mnt/RAM_disk/INTEGRATION/create_data/result/pseudoRGB_seg_res5.tif \n\
                                      -rbh /mnt/RAM_disk/INTEGRATION/create_data/result/builds_height.tif \n\
                                      -vro /mnt/RAM_disk/INTEGRATION/create_data/result/all_roads.shp \n\
                                      -vwo /mnt/RAM_disk/INTEGRATION/create_data/result/all_waters_area.shp \n\
                                      -vsk /mnt/RAM_disk/INTEGRATION/create_data/result/skeleton_primary_roads.shp \n\
                                      -vrps /mnt/RAM_disk/INTEGRATION/create_data/result/pres_seg_road.shp \n\
                                      -vfsa /mnt/RAM_disk/INTEGRATION/slic_lissage_chaiken_5.shp \n\
                                      -vpost /mnt/RAM_disk/INTEGRATION/seg_post_processing/toulouseseg_post.shp \n\
                                      -vseg /mnt/RAM_disk/INTEGRATION/seg_res_fusion/res/toulouse_seg_end.shp")

    parser.add_argument('-r','--base_folder',default="",help="Working repertory.", type=str, required=True)
    parser.add_argument('-e','--emprise_vector',default="",help="Vector input contain the vector emprise reference.", type=str, required=True)
    parser.add_argument('-oso','--OSO_file_input',default="",help="Raster input OSO, Occupation du SOL.", type=str, required=True)
    parser.add_argument('-qml','--QML_file_input',default="",help="File input QML, style QGIS for OSO.", type=str, required=True)
    parser.add_argument('-vrl','--vectors_road_input_list',default="",nargs="+",help="List vectors input contain roads.", type=str, required=True)
    parser.add_argument('-val','--vectors_railway_input_list',default="",nargs="+",help="List vectors input contain railway.", type=str, required=False)
    parser.add_argument('-vbl','--vectors_build_input_list',default="",nargs="+",help="List vectors input contain builds.", type=str, required=True)
    parser.add_argument('-vwl','--vectors_water_area_input_list',default="",nargs="+",help="Vector input contain the water area.", type=str, required=True)
    parser.add_argument('-sqlr','--sql_exp_road_list',default=None,help="List containt sql expression to filter each db file road input (separator is ':' and not used \" for string value)", type=str, required=False)
    parser.add_argument('-sqla','--sql_exp_railway_list',default=None,help="List containt sql expression to filter each db file railway input (separator is ':' and not used \" for string value)", type=str, required=False)
    parser.add_argument('-sqlb','--sql_exp_build_list',default=None,help="List containt sql expression to filter each db file build input (separator is ':' and not used \" for string value)", type=str, required=False)
    parser.add_argument('-sqlw','--sql_exp_water_list',default=None,help="List containt sql expression to filter each db file water input (separator is ':' and not used \" for string value)", type=str, required=False)
    parser.add_argument('-ofo','--OSO_file_output',default="",help="Raster output oso cut on emprise.", type=str, required=True)
    parser.add_argument('-rgb','--pseudoRGB_file_output',default="",help="Raster output image pseudo rgb.", type=str, required=True)
    parser.add_argument('-rbh','--raster_build_height_output',default="",help="Raster output build height.", type=str, required=True)
    parser.add_argument('-vro','--vector_roads_output',default="",help="Vector all roads output.", type=str, required=True)
    parser.add_argument('-vrm','--vector_roads_main_output',default="",help="Vector buff main roads output.", type=str, required=True)
    parser.add_argument('-vwo','--vector_waters_area_output',default="",help="Vector all waters area output.", type=str, required=True)
    parser.add_argument('-vsk','--vector_line_skeleton_main_roads_output',default="",help="Vector lines contain skeletopn of main roads output.", type=str, required=True)
    parser.add_argument('-vrps','--vector_roads_pres_seg',default="",help="Vector segmentation output of crossing roads.", type=str, required=True)
    parser.add_argument('-vfsa','--vector_file_seg_algo',default="",help="Vector segmentation output of processing algorithm.", type=str, required=True)
    parser.add_argument('-vpost','--vector_file_seg_post',default="",help="Vector segmentation output of post treatment.", type=str, required=True)
    parser.add_argument('-vseg','--vector_file_seg_output',default="",help="Vector segmentation output ending.", type=str, required=True)
    parser.add_argument('-osp','--optimize_slic_parameters',action='store_true',default=False,help="Optimize SLIC parametres. By default, False.", required=False)
    parser.add_argument('-rif','--road_importance_field',default="IMPORTANCE",help="Option : Field name of importance road.", type=str, required=False)
    parser.add_argument('-rit','--road_importance_threshold',default=4,help="Option : Threshold value of importance road.", type=int, required=False)
    parser.add_argument('-rwf','--road_width_field',default="LARGEUR",help="Option : Field name of width road.", type=str, required=False)
    parser.add_argument('-rnf','--road_nature_field',default="NATURE",help="Option : Field name of nature road.", type=str, required=False)
    parser.add_argument('-anf','--railway_nature_field',default="NATURE",help="Option : Field name of nature road.", type=str, required=False)
    parser.add_argument('-aiv','--railway_importance_values',default="Principale",help="Option : Field name of nature road.", type=str, required=False)
    parser.add_argument('-bsr', '--buffer_size_skeleton', default=35.0, help="Option : Size of buffer contain importante road in meter. By default : 35.0.", type=float, required=False)
    parser.add_argument('-ell', '--extension_length_lines', default=20, help="Option : Size of length extention lines. By default : 20.", type=int, required=False)
    parser.add_argument('-mwa', '--min_area_water_area', default=50000.0, help="Option : min water area  in meter². By default : 100000.0.", type=float, required=False)
    parser.add_argument('-pe','--project_encoding', default="latin1",help="Project encoding.", type=str, required=False)
    parser.add_argument('-serv','--server_postgis', default="localhost",help="Postgis serveur name or ip.", type=str, required=False)
    parser.add_argument('-port','--port_number', default=5433,help="Postgis port number.", type=int, required=False)
    parser.add_argument('-user','--user_postgis', default="postgres",help="Postgis user name.", type=str, required=False)
    parser.add_argument('-pwd','--password_postgis', default="postgres",help="Postgis password user.", type=str, required=False)
    parser.add_argument('-db','--database_postgis', default="segmentation",help="Postgis database name.", type=str, required=False)
    parser.add_argument('-sch','--schema_postgis', default="public",help="Postgis schema name.", type=str, required=False)
    parser.add_argument('-res', '--resolution', default=5.0, help="Option : Resolution pixel coordinate X and Y in meter. By default : 5.0.", type=float, required=False)
    parser.add_argument('-ndv','--no_data_value', default=0, help="Option : Value of the pixel no data. By default : 0.", type=int, required=False)
    parser.add_argument('-epsg','--epsg', default=2154,help="EPSG code projection.", type=int, required=False)
    parser.add_argument('-raf','--format_raster', default="GTiff", help="Option : Format output image, by default : GTiff (GTiff, HFA...).", type=str, required=False)
    parser.add_argument('-vef','--format_vector', default="ESRI Shapefile",help="Format of the output file.", type=str, required=False)
    parser.add_argument('-rae','--extension_raster', default=".tif", help="Option : Extension file for image raster. By default : '.tif'.", type=str, required=False)
    parser.add_argument('-vee','--extension_vector',default=".shp",help="Option : Extension file for vector. By default : '.shp'.", type=str, required=False)
    parser.add_argument('-log','--path_time_log',default="",help="Name of log.", type=str, required=False)
    parser.add_argument('-sav','--save_results_inter',action='store_true',default=False,help="Save or delete intermediate result after the process. By default, False.", required=False)
    parser.add_argument('-now','--overwrite',action='store_false',default=True,help="Overwrite files with same names. By default, True.", required=False)
    parser.add_argument('-debug','--debug',default=3,help="Option : Value of level debug trace, default : 3.",type=int, required=False)
    args = displayIHM(gui, parser)

    # RECUPERATION DES ARGUMENTS

    # Récupération des répertoire de travail
    if args.base_folder != None:
        base_folder = args.base_folder
        if not os.path.isdir(base_folder):
            os.makedirs(base_folder)

    # Récupération du vecteur d'emprise
    if args.emprise_vector != None :
        emprise_vector = args.emprise_vector
        if not os.path.isfile(emprise_vector):
            raise NameError (cyan + "UrbanMorphologySegmentation : " + bold + red  + "File %s not existe!" %(emprise_vector) + endC)

    # Récupération des fichiers raster OSO et de son style QML
    if args.OSO_file_input != None :
        OSO_file_input = args.OSO_file_input
        if not os.path.isfile(OSO_file_input):
            raise NameError (cyan + "UrbanMorphologySegmentation : " + bold + red  + "File %s not existe!" %(OSO_file_input) + endC)

    if args.QML_file_input != None :
        QML_file_input = args.QML_file_input
        if not os.path.isfile(QML_file_input):
            raise NameError (cyan + "UrbanMorphologySegmentation : " + bold + red  + "File %s not existe!" %(QML_file_input) + endC)

    # Récupération des vecteurs d'entrées routes
    if args.vectors_road_input_list != None:
        vectors_road_input_list = args.vectors_road_input_list
        for vector_input in vectors_road_input_list :
            if not os.path.isfile(vector_input):
                raise NameError (cyan + "UrbanMorphologySegmentation : " + bold + red  + "File %s not existe!" %(vector_input) + endC)

    # Récupération des vecteurs d'entrées des voies ferrées
    if args.vectors_railway_input_list != None:
        vectors_railway_input_list = args.vectors_railway_input_list
        for vector_input in vectors_railway_input_list :
            if not os.path.isfile(vector_input):
                raise NameError (cyan + "UrbanMorphologySegmentation : " + bold + red  + "File %s not existe!" %(vector_input) + endC)

    # Récupération des vecteurs d'entrées batis
    if args.vectors_build_input_list != None:
        vectors_build_input_list = args.vectors_build_input_list
        for vector_input in vectors_build_input_list :
            if not os.path.isfile(vector_input):
                raise NameError (cyan + "UrbanMorphologySegmentation : " + bold + red  + "File %s not existe!" %(vector_input) + endC)

    # Récupération du vecteur d'entrée surface en eau
    if args.vectors_water_area_input_list != None :
        vectors_water_area_input_list = args.vectors_water_area_input_list
        for vector_input in vectors_water_area_input_list :
            if not os.path.isfile(vector_input):
                raise NameError (cyan + "UrbanMorphologySegmentation : " + bold + red  + "File %s not existe!" %(vector_input) + endC)

    # liste des expression sql pour filtrer les vecteurs de bd exogenes de routes
    if args.sql_exp_road_list != None:
        sql_exp_road_list = args.sql_exp_road_list.replace('"','').split(":")
        if len(sql_exp_road_list) != len(vectors_road_input_list) :
             raise NameError (cyan + "MacroSamplesCreation : " + bold + red  + "List sql expression size %d is differente at size bd roads vector input list!" %(len(sql_exp_road_list)) + endC)
    else :
        sql_exp_road_list = []

    # liste des expression sql pour filtrer les vecteurs de bd exogenes des voies ferrées
    if args.sql_exp_railway_list != None:
        sql_exp_railway_list = args.sql_exp_railway_list.replace('"','').split(":")
        if len(sql_exp_railway_list) != len(vectors_railway_input_list) :
             raise NameError (cyan + "MacroSamplesCreation : " + bold + red  + "List sql expression size %d is differente at size bd railway vector input list!" %(len(sql_exp_railway_list)) + endC)
    else :
        sql_exp_railway_list = []

    # liste des expression sql pour filtrer les vecteurs de bd exogenes de batis
    if args.sql_exp_build_list != None:
        sql_exp_build_list = args.sql_exp_build_list.replace('"','').split(":")
        if len(sql_exp_build_list) != len(vectors_build_input_list) :
             raise NameError (cyan + "MacroSamplesCreation : " + bold + red  + "List sql expression size %d is differente at size bd builds vector input list!" %(len(sql_exp_build_list)) + endC)
    else :
        sql_exp_build_list = []

    # liste des expression sql pour filtrer les vecteurs de bd exogenes de surfaces en eau
    if args.sql_exp_water_list != None:
        sql_exp_water_list = args.sql_exp_water_list.replace('"','').split(":")
        if len(sql_exp_water_list) != len(vectors_water_area_input_list) :
             raise NameError (cyan + "MacroSamplesCreation : " + bold + red  + "List sql expression size %d is differente at size bd waters area vector input list!" %(len(sql_exp_water_list)) + endC)
    else :
        sql_exp_water_list = []

    # Récupération du raster de sortie OSO découpé
    if args.OSO_file_output != None :
        OSO_file_output = args.OSO_file_output

    # Récupération du raster de sortie image RGB
    if args.pseudoRGB_file_output != None :
        pseudoRGB_file_output = args.pseudoRGB_file_output

    # Récupération du raster de sortie hauteur des batis
    if args.raster_build_height_output != None :
        raster_build_height_output = args.raster_build_height_output

    # Récupération du vecteur de sortie fusion de toutes les routes
    if args.vector_roads_output != None :
        vector_roads_output = args.vector_roads_output

    # Récupération du vecteur de sortie des routes principales 2 voies buffurisées
    if args.vector_roads_main_output != None :
        vector_roads_main_output = args.vector_roads_main_output

    # Récupération du vecteur de sortie fusion de toutes les surfaces en eau
    if args.vector_waters_area_output != None :
        vector_waters_area_output = args.vector_waters_area_output

    # Récupération du vecteur de sortie skelette des lines des routes principales
    if args.vector_line_skeleton_main_roads_output != None :
        vector_line_skeleton_main_roads_output = args.vector_line_skeleton_main_roads_output

    # Récupération du vecteur temporaire segmentation sortie du croisement des routes
    if args.vector_roads_pres_seg != None :
        vector_roads_pres_seg = args.vector_roads_pres_seg

    # Récupération du vecteur temporaire segmentation sortie de l'algo CCM / SLIC
    if args.vector_file_seg_algo != None :
        vector_file_seg_algo = args.vector_file_seg_algo

    # Récupération du vecteur temporaire segmentation sortie du post traitement
    if args.vector_file_seg_post != None :
        vector_file_seg_post = args.vector_file_seg_post

    # Récupération du vecteur de sortie de la segmentation final
    if args.vector_file_seg_output != None :
        vector_file_seg_output = args.vector_file_seg_output

    # Récupération de l'option d'optimisation des paramtres de SLIC
    if args.optimize_slic_parameters!= None:
        optimize_slic_parameters = args.optimize_slic_parameters

    # Récupération du nom du champs importance des routes
    if args.road_importance_field != None :
        road_importance_field = args.road_importance_field

   # Récupération de la valeur de seuil pour l'importance des routes
    if args.road_importance_threshold != None :
        road_importance_threshold = args.road_importance_threshold

    # Récupération du nom du champs largeur des routes
    if args.road_width_field != None :
        road_width_field = args.road_width_field

    # Récupération du nom du champs nature des routes
    if args.road_nature_field != None :
        road_nature_field = args.road_nature_field

    # Récupération du nom du champs nature des voies ferrées
    if args.railway_nature_field != None :
        railway_nature_field = args.railway_nature_field

    # Récupération des valeurs de l'importance des voies ferrées
    if args.railway_importance_values != None :
        railway_importance_values = args.railway_importance_values

   # Récupération de la valeur du buffer pour l'importance des routes pour la creation du squelette
    if args.buffer_size_skeleton != None :
        buffer_size_skeleton = args.buffer_size_skeleton

   # Récupération de la valeur de la longueur pour l'extention des routes pour la creation de la segmentation route
    if args.extension_length_lines != None :
        extension_length_lines = args.extension_length_lines

   # Récupération de la valeur de seuil minimale pour les surfaces d'eau
    if args.min_area_water_area != None :
        min_area_water_area = args.min_area_water_area

    # Récupération de l'encodage des fichiers
    if args.project_encoding != None :
        project_encoding = args.project_encoding

    # Récupération du serveur de Postgis
    if args.server_postgis != None :
        server_postgis = args.server_postgis

    # Récupération du numéro du port
    if args.port_number != None :
        port_number = args.port_number

    # Récupération du nom de l'utilisateur postgis
    if args.user_postgis != None :
        user_postgis = args.user_postgis

    # Récupération du mot de passe de l'utilisateur
    if args.password_postgis != None :
        password_postgis = args.password_postgis

    # Récupération du nom de la base postgis
    if args.database_postgis != None :
        database_postgis = args.database_postgis

    # Récupération du nom du schéma
    if args.schema_postgis != None :
        schema_postgis = args.schema_postgis

    # Paramètres de définition de la résolution
    if args.resolution != None:
        resolution = args.resolution

    # Parametres de valeur du nodata des fichiers de sortie
    if args.no_data_value!= None:
        no_data_value = args.no_data_value

    # Récupération du code EPSG de la projection du shapefile trait de côte
    if args.epsg != None :
        epsg = args.epsg

    # Paramètre format des images de sortie
    if args.format_raster != None:
        format_raster = args.format_raster

    # Récupération du format des vecteurs de sortie
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
        print(bold + green + "UrbanMorphologySegmentation : Variables dans le parser" + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "base_folder : " + str(base_folder) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "emprise_vector : " + str(emprise_vector) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "OSO_file_input : " + str(OSO_file_input) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "QML_file_input : " + str(QML_file_input) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "vectors_road_input_list : " + str(vectors_road_input_list) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "vectors_railway_input_list : " + str(vectors_railway_input_list) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "vectors_build_input_list : " + str(vectors_build_input_list) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "vectors_water_area_input_list : " + str(vectors_water_area_input_list) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "sql_exp_road_list : " + str(sql_exp_road_list) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "sql_exp_railway_list : " + str(sql_exp_railway_list) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "sql_exp_build_list : " + str(sql_exp_build_list) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "sql_exp_water_list : " + str(sql_exp_water_list) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "OSO_file_output : " + str(OSO_file_output) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "pseudoRGB_file_output : " + str(pseudoRGB_file_output) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "raster_build_height_output : " + str(raster_build_height_output) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "vector_roads_output : " + str(vector_roads_output) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "vector_roads_main_output : " + str(vector_roads_main_output) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "vector_waters_area_output : " + str(vector_waters_area_output))
        print(cyan + "UrbanMorphologySegmentation : " + endC + "vector_line_skeleton_main_roads_output : " + str(vector_line_skeleton_main_roads_output))
        print(cyan + "UrbanMorphologySegmentation : " + endC + "vector_roads_pres_seg : " + str(vector_roads_pres_seg))
        print(cyan + "UrbanMorphologySegmentation : " + endC + "vector_file_seg_algo : " + str(vector_file_seg_algo) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "vector_file_seg_post : " + str(vector_file_seg_post) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "vector_file_seg_output : " + str(vector_file_seg_output) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "optimize_slic_parameters : " + str(optimize_slic_parameters) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "road_importance_field : " + str(road_importance_field) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "road_importance_threshold : " + str(road_importance_threshold) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "road_width_field : " + str(road_width_field) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "road_nature_field : " + str(road_nature_field) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "railway_nature_field : " + str(railway_nature_field) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "railway_importance_values : " + str(railway_importance_values) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "buffer_size_skeleton : " + str(buffer_size_skeleton) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "extension_length_lines : " + str(extension_length_lines) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "min_area_water_area : " + str(min_area_water_area) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "project_encoding : " + str(project_encoding) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "server_postgis : " + str(server_postgis) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "port_number : " + str(port_number) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "user_postgis : " + str(user_postgis) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "password_postgis : " + str(password_postgis) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "database_postgis : " + str(database_postgis) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "schema_postgis : " + str(schema_postgis) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "resolution : " + str(resolution) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "format_raster : " + str(format_raster) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "save_results_inter : " + str(save_results_intermediate) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "debug : " + str(debug) + endC)

    # EXECUTION DE LA FONCTION

    # execution de la fonction pour une image
    processSegmentationUrbanMorpho(base_folder, emprise_vector, OSO_file_input, QML_file_input, vectors_road_input_list, vectors_railway_input_list, vectors_build_input_list, vectors_water_area_input_list, sql_exp_road_list, sql_exp_railway_list, sql_exp_build_list, sql_exp_water_list, OSO_file_output, pseudoRGB_file_output, raster_build_height_output, vector_roads_output, vector_roads_main_output, vector_waters_area_output, vector_line_skeleton_main_roads_output, vector_roads_pres_seg, vector_file_seg_algo, vector_file_seg_post, vector_file_seg_output, optimize_slic_parameters, road_importance_field, road_importance_threshold, road_width_field, road_nature_field, railway_nature_field, railway_importance_values, buffer_size_skeleton, extension_length_lines, min_area_water_area, project_encoding, server_postgis, port_number, user_postgis, password_postgis, database_postgis, schema_postgis, resolution, no_data_value, epsg, format_raster, format_vector, extension_raster, extension_vector, path_time_log, save_results_intermediate, overwrite)

# ================================================

if __name__ == '__main__':
  main(gui=False)
