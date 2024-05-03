#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT DE CREATION D4UNE SEGMENTATION MORPHOLOGIE URBAINE AFIN DE SEGMENTER LES POLYGONES A L'ECHELLE DES QUARTIERS                       #
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
from CCMsegmentation import processingCCM, DICT_CCM_BEST_PARAMETERS
from CCMpostprocessing import segPostProcessing
from PolygonsMerging import segPolygonsMerging

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 2

###########################################################################################################################################
# FONCTION processSegmentationUrbanMorpho()                                                                                               #
###########################################################################################################################################
def processSegmentationUrbanMorpho(base_folder, ccm_folder, emprise_vector, GRA_file_input, TCD_file_input, IMD_file_input,  vectors_road_input_list, vectors_build_input_list, vectors_water_area_input_list, sql_exp_road_list, sql_exp_build_list, sql_exp_water_list, pseudoRGB_file_output, raster_road_width_output, raster_build_height_output, vector_roads_output, vector_waters_area_output, vector_file_seg_ccm, vector_file_seg_post, vector_file_seg_output, roads_width_field="LARGEUR", road_importance_field="IMPORTANCE", road_importance_threshold=4, buffer_size_road=35.0, min_area_water_area=100000.0, project_encoding="latin1", server_postgis="localhost", port_number=5432, user_postgis="postgres", password_postgis="postgres", database_postgis="cutbylines", schema_postgis="public", resolution=5, no_data_value=0, epsg=2154, format_raster='GTiff', format_vector='ESRI Shapefile', extension_raster=".tif", extension_vector=".shp", path_time_log="", save_results_intermediate=False, overwrite=True) :

    """
    # ROLE:
    #     Verifier et corrige des vecteurs resultats de classifications OCS en traitement sous postgis
    #
    # ENTREES DE LA FONCTION :
    #     base_folder (str): Base repertoire de travail des fichiers temporaires et de sorties.
    #     ccm_folder (str): Repertoire ou sont stocker les code source de l'algo CCM C++ script.
    #     emprise_vector (str): le vecteur d'emprise de référence.
    #     GRA_file_input (str): chemin vers le fichier raster d'entrée GRA (Grassland).
    #     TCD_file_input (str):chemin vers le fichier raster d'entrée TCD (Tree Cover Density).
    #     IMD_file_input (str): chemin vers lefichier raster d'entrée IMD (Imperviousness Density).
    #     vectors_road_input_list (list) : les fichiers contenant les routes d'entrée (routes primaires et secondaires).
    #     vectors_build_input_list (list) : les fichiers contenant les batis d'entrée.
    #     vectors_water_area_input_list (list) : les fichiers contenant les surfaces en eau d'entrée.
    #     sql_exp_road_list (list) : liste d'expression sql pour le filtrage des fichiers vecteur de bd exogenes routes.
    #     sql_exp_build_list (list) : liste d'expression sql pour le filtrage des fichiers vecteur de bd exogenes batis.
    #     sql_exp_water_list (list) : liste d'expression sql pour le filtrage des fichiers vecteur de bd exogenes surfaces en eau.
    #     pseudoRGB_file_output (str): fichier de pseudo-RGB image resultat en sortie.
    #     raster_road_width_output (str):  fichier de sortie rasteur largeur de routes.
    #     raster_build_height_output (str):  fichier de sortie rasteur des batis.
    #     vector_roads_output (str): fichier de sortie vecteur contenant toutes les routes.
    #     vector_waters_area_output (str): fichier de sortie vecteur contenant toutes les surfaces en eaux.
    #     vector_file_seg_ccm (str): fichier temporaire vecteur contenant la segmentation sortie de l'algo CCM.
    #     vector_file_seg_post (str): fichier temporaire vecteur contenant la segmentation sortie de post tratement.
    #     vector_file_seg_output (str): fichier final vecteur contenant la segmentation apres fusion.
    #     roads_width_field (str): name of the column containing road width data (default: "LARGEUR").
    #     road_importance_field (str) : champs importance des routes (par defaut : "IMPORTANCE").
    #     road_importance_threshold (int) : valeur du seuil d'importance (par défaut : 4).
    #     buffer_size_road (float) : valeur du buffer pour l'importance des routes (par défaut : 35.0).
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
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "ccm_folder : " + str(ccm_folder))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "emprise_vector : " + str(emprise_vector))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "GRA_file_input : " + str(GRA_file_input))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "TCD_file_input : " + str(TCD_file_input))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "IMD_file_input : " + str(IMD_file_input))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "vectors_road_input_list : " + str(vectors_road_input_list))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "vectors_build_input_list : " + str(vectors_build_input_list))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "vectors_water_area_input_list : " + str(vectors_water_area_input_list))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "sql_exp_road_list : " + str(sql_exp_road_list))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "sql_exp_build_list : " + str(sql_exp_build_list))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "sql_exp_water_list : " + str(sql_exp_water_list))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "pseudoRGB_file_output : " + str(pseudoRGB_file_output))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "raster_road_width_output : " + str(raster_road_width_output))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "raster_build_height_output : " + str(raster_build_height_output))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "vector_roads_output : " + str(vector_roads_output))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "vector_waters_area_output : " + str(vector_waters_area_output))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "vector_file_seg_ccm : " + str(vector_file_seg_ccm))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "vector_file_seg_post : " + str(vector_file_seg_post))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "vector_file_seg_output : " + str(vector_file_seg_output))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "roads_width_field : " + str(roads_width_field))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "road_importance_field : " + str(road_importance_field))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "road_importance_threshold : " + str(road_importance_threshold))
        print(cyan + "processSegmentationUrbanMorpho() : " + endC + "buffer_size_road : " + str(buffer_size_road))
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

    # 1) CreateDataIndicateurPseudoRGB
    createDataIndicateurPseudoRGB(base_folder,
                                  emprise_vector,
                                  GRA_file_input,
                                  TCD_file_input,
                                  IMD_file_input,
                                  vectors_road_input_list,
                                  vectors_build_input_list,
                                  vectors_water_area_input_list,
                                  sql_exp_road_list,
                                  sql_exp_build_list,
                                  sql_exp_water_list,
                                  pseudoRGB_file_output,
                                  raster_road_width_output,
                                  raster_build_height_output,
                                  vector_roads_output,
                                  vector_waters_area_output,
                                  roads_width_field,
                                  road_importance_field,
                                  road_importance_threshold,
                                  resolution,
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

    # 2) CCMsegmentation
    dict_ccm_parameters = DICT_CCM_BEST_PARAMETERS
    processingCCM(base_folder,
                  emprise_vector,
                  pseudoRGB_file_output,
                  vector_file_seg_ccm,
                  ccm_folder,
                  dict_ccm_parameters,
                  resolution,
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


    # 3) CCMpostprocessing
    segPostProcessing(base_folder,
                      emprise_vector,
                      vector_file_seg_ccm,
                      vector_roads_output,
                      vector_waters_area_output,
                      vector_file_seg_post,
                      road_importance_field,
                      road_importance_threshold,
                      buffer_size_road,
                      min_area_water_area,
                      no_data_value,
                      epsg,
                      server_postgis,
                      port_number,
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

    # 4) PolygonsMerging
    segPolygonsMerging(base_folder,
                       emprise_vector,
                       pseudoRGB_file_output,
                       raster_road_width_output,
                       raster_build_height_output,
                       vector_file_seg_post,
                       vector_file_seg_output,
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
#                                      -e /mnt/RAM_disk/INTEGRATION/emprise/toulouse_emprise.shp
#                                      -gra /mnt/RAM_disk/INTEGRATION/GRA_2018_010m_E36N23_03035_v010.tif
#                                      -tcd /mnt/RAM_disk/INTEGRATION/TCD_2018_010m_E36N23_03035_v020.tif
#                                      -imd /mnt/RAM_disk/INTEGRATION/IMD_2018_010m_E36N23_03035_v020.tif
#                                      -vrl /mnt/RAM_disk/INTEGRATION/bd_topo/N_ROUTE_PRIMAIRE_BDT_031.SHP /mnt/RAM_disk/INTEGRATION/bd_topo/N_ROUTE_SECONDAIRE_BDT_031.SHP
#                                      -vbl /mnt/RAM_disk/INTEGRATION/bd_topo/N_BATI_INDIFFERENCIE_BDT_031.shp /mnt/RAM_disk/INTEGRATION/bd_topo/N_BATI_INDUSTRIEL_BDT_031.shp /mnt/RAM_disk/INTEGRATION/bd_topo/N_BATI_REMARQUABLE_BDT_031.shp
#                                      -vwl /mnt/RAM_disk/INTEGRATION/bd_topo/N_SURFACE_EAU_BDT_031.shp
#                                      -sqlr "FRANCHISST !='Tunnel'":"FRANCHISST !='Tunnel'"
#                                      -sqlb "":"NATURE !='Serre'":""
#                                      -sqlw "REGIME ='Permanent'"
#                                      -rgb /mnt/RAM_disk/INTEGRATION/create_data/result/pseudoRGB_seg_res5.tif
#                                      -rrw /mnt/RAM_disk/INTEGRATION/create_data/result/roads_width.tif
#                                      -rbh /mnt/RAM_disk/INTEGRATION/create_data/result/builds_height.tif
#                                      -vro /mnt/RAM_disk/INTEGRATION/create_data/result/all_roads.shp
#                                      -vwo /mnt/RAM_disk/INTEGRATION2/create_data/result/all_waters_area.shp
#                                      -vccm /mnt/RAM_disk/INTEGRATION/ccm/result/toulouse_seg_ccm.shp
#                                      -vpost /mnt/RAM_disk/INTEGRATION/seg_post_processing/toulouse_seg_post.shp
#                                      -vseg /mnt/RAM_disk/INTEGRATION/seg_res_fusion/res/toulouse_seg_end.shp

def main(gui=False):

    # Définition des différents paramètres du parser
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,  prog="UrbanMorphologySegmentation", description="\
    Info : Cutting list of raster and vector file by vector file. \n\
    Objectif : Découper des fichiers raster et vecteurs. \n\
    Example : python UrbanMorphologySegmentation.py \n\
    python UrbanMorphologySegmentation.py -r /mnt/RAM_disk/INTEGRATION \n\
                                      -e /mnt/RAM_disk/INTEGRATION/emprise/toulouse_emprise.shp \n\
                                      -gra /mnt/RAM_disk/INTEGRATION/GRA_2018_010m_E36N23_03035_v010.tif \n\
                                      -tcd /mnt/RAM_disk/INTEGRATION/TCD_2018_010m_E36N23_03035_v020.tif \n\
                                      -imd /mnt/RAM_disk/INTEGRATION/IMD_2018_010m_E36N23_03035_v020.tif \n\
                                      -vrl /mnt/RAM_disk/INTEGRATION/bd_topo/N_ROUTE_PRIMAIRE_BDT_031.SHP /mnt/RAM_disk/INTEGRATION/bd_topo/N_ROUTE_SECONDAIRE_BDT_031.SHP \n\
                                      -vbl /mnt/RAM_disk/INTEGRATION/bd_topo/N_BATI_INDIFFERENCIE_BDT_031.shp /mnt/RAM_disk/INTEGRATION/bd_topo/N_BATI_INDUSTRIEL_BDT_031.shp /mnt/RAM_disk/INTEGRATION/bd_topo/N_BATI_REMARQUABLE_BDT_031.shp \n\
                                      -vwl /mnt/RAM_disk/INTEGRATION/bd_topo/N_SURFACE_EAU_BDT_031.shp \n\
                                      -sqlr \"FRANCHISST !='Tunnel'\":\"FRANCHISST !='Tunnel'\" \n\
                                      -sqlb \"\":\"NATURE !='Serre'\":\"\" \n\
                                      -sqlw \"REGIME ='Permanent'\" \n\
                                      -rgb /mnt/RAM_disk/INTEGRATION/create_data/result/pseudoRGB_seg_res5.tif \n\
                                      -rrw /mnt/RAM_disk/INTEGRATION/create_data/result/roads_width.tif \n\
                                      -rbh /mnt/RAM_disk/INTEGRATION/create_data/result/builds_height.tif \n\
                                      -vro /mnt/RAM_disk/INTEGRATION/create_data/result/all_roads.shp \n\
                                      -vwo /mnt/RAM_disk/INTEGRATION2/create_data/result/all_waters_area.shp \n\
                                      -vccm /mnt/RAM_disk/INTEGRATION/ccm/result/toulouse_seg_ccm.shp \n\
                                      -vpost /mnt/RAM_disk/INTEGRATION/seg_post_processing/toulouseseg_post.shp \n\
                                      -vseg /mnt/RAM_disk/INTEGRATION/seg_res_fusion/res/toulouse_seg_end.shp")

    parser.add_argument('-r','--base_folder',default="",help="Working repertory.", type=str, required=True)
    parser.add_argument('-ccm','--ccm_folder',default="/home/scgsi/CCM",help="CCM code repertory.", type=str, required=False)
    parser.add_argument('-e','--emprise_vector',default="",help="Vector input contain the vector emprise reference.", type=str, required=True)
    parser.add_argument('-gra','--GRA_file_input',default="",help="Raster input copernicus, High Resolution Layer Grassland.", type=str, required=True)
    parser.add_argument('-tcd','--TCD_file_input',default="",help="Raster input copernicus, High Resolution Layer Tree Cover Density.", type=str, required=True)
    parser.add_argument('-imd','--IMD_file_input',default="",help="Raster input copernicus, .High Resolution Layer Imperviousness.", type=str, required=True)
    parser.add_argument('-vrl','--vectors_road_input_list',default="",nargs="+",help="List vectors input contain roads.", type=str, required=True)
    parser.add_argument('-vbl','--vectors_build_input_list',default="",nargs="+",help="List vectors input contain builds.", type=str, required=True)
    parser.add_argument('-vwl','--vectors_water_area_input_list',default="",nargs="+",help="Vector input contain the water area.", type=str, required=True)
    parser.add_argument('-sqlr','--sql_exp_road_list',default=None,help="List containt sql expression to filter each db file road input (separator is ':' and not used \" for string value)", type=str, required=False)
    parser.add_argument('-sqlb','--sql_exp_build_list',default=None,help="List containt sql expression to filter each db file build input (separator is ':' and not used \" for string value)", type=str, required=False)
    parser.add_argument('-sqlw','--sql_exp_water_list',default=None,help="List containt sql expression to filter each db file water input (separator is ':' and not used \" for string value)", type=str, required=False)
    parser.add_argument('-rgb','--pseudoRGB_file_output',default="",help="Raster output image pseudo rgb.", type=str, required=True)
    parser.add_argument('-rrw','--raster_road_width_output',default="",help="Raster output road width.", type=str, required=True)
    parser.add_argument('-rbh','--raster_build_height_output',default="",help="Raster output build height.", type=str, required=True)
    parser.add_argument('-vro','--vector_roads_output',default="",help="Vector all roads output.", type=str, required=True)
    parser.add_argument('-vwo','--vector_waters_area_output',default="",help="Vector all waters area output.", type=str, required=True)
    parser.add_argument('-vccm','--vector_file_seg_ccm',default="",help="Vector segmentation output of CCM algorithm.", type=str, required=True)
    parser.add_argument('-vpost','--vector_file_seg_post',default="",help="Vector segmentation output of post treatment.", type=str, required=True)
    parser.add_argument('-vseg','--vector_file_seg_output',default="",help="Vector segmentation output ending.", type=str, required=True)
    parser.add_argument('-rwf','--roads_width_field',default="LARGEUR",help="Option : Field name of width road.", type=str, required=False)
    parser.add_argument('-rif','--road_importance_field',default="IMPORTANCE",help="Option : Field name of importance road.", type=str, required=False)
    parser.add_argument('-rit','--road_importance_threshold',default=4,help="Option : Threshold value of importance road.", type=int, required=False)
    parser.add_argument('-bsr', '--buffer_size_road', default=35.0, help="Option : Size of buffer contain importante road in meter. By default : 35.0.", type=float, required=False)
    parser.add_argument('-mwa', '--min_area_water_area', default=50000.0, help="Option : min water area  in meter². By default : 100000.0.", type=float, required=False)
    parser.add_argument('-pe','--project_encoding', default="latin1",help="Project encoding.", type=str, required=False)
    parser.add_argument('-serv','--server_postgis', default="localhost",help="Postgis serveur name or ip.", type=str, required=False)
    parser.add_argument('-port','--port_number', default=5432,help="Postgis port number.", type=int, required=False)
    parser.add_argument('-user','--user_postgis', default="postgres",help="Postgis user name.", type=str, required=False)
    parser.add_argument('-pwd','--password_postgis', default="postgres",help="Postgis password user.", type=str, required=False)
    parser.add_argument('-db','--database_postgis', default="cutbylines",help="Postgis database name.", type=str, required=False)
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

    # Récupération des répertoire code source de CCM
    if args.ccm_folder != None:
        ccm_folder = args.ccm_folder
        if not os.path.isdir(ccm_folder):
            os.makedirs(ccm_folder)

    # Récupération du vecteur d'emprise
    if args.emprise_vector != None :
        emprise_vector = args.emprise_vector
        if not os.path.isfile(emprise_vector):
            raise NameError (cyan + "UrbanMorphologySegmentation : " + bold + red  + "File %s not existe!" %(emprise_vector) + endC)

    # Récupération des fichiers raster copernicus HR-Layer
    if args.GRA_file_input != None :
        GRA_file_input = args.GRA_file_input
        if not os.path.isfile(GRA_file_input):
            raise NameError (cyan + "UrbanMorphologySegmentation : " + bold + red  + "File %s not existe!" %(GRA_file_input) + endC)

    if args.TCD_file_input != None :
        TCD_file_input = args.TCD_file_input
        if not os.path.isfile(TCD_file_input):
            raise NameError (cyan + "UrbanMorphologySegmentation : " + bold + red  + "File %s not existe!" %(TCD_file_input) + endC)

    if args.IMD_file_input != None :
        IMD_file_input = args.IMD_file_input
        if not os.path.isfile(IMD_file_input):
            raise NameError (cyan + "UrbanMorphologySegmentation : " + bold + red  + "File %s not existe!" %(IMD_file_input) + endC)

    # Récupération des vecteurs d'entrées routes
    if args.vectors_road_input_list != None:
        vectors_road_input_list = args.vectors_road_input_list
        for vector_input in vectors_road_input_list :
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

    # Récupération du raster de sortie image RGB
    if args.pseudoRGB_file_output != None :
        pseudoRGB_file_output = args.pseudoRGB_file_output

    # Récupération du raster de sortie largeur de route
    if args.raster_road_width_output != None :
        raster_road_width_output = args.raster_road_width_output

    # Récupération du raster de sortie hauteur des batis
    if args.raster_build_height_output != None :
        raster_build_height_output = args.raster_build_height_output

    # Récupération du vecteur de sortie fusion de toutes les routes
    if args.vector_roads_output != None :
        vector_roads_output = args.vector_roads_output

    # Récupération du vecteur de sortie fusion de toutes les surfaces en eau
    if args.vector_waters_area_output != None :
        vector_waters_area_output = args.vector_waters_area_output

    # Récupération du vecteur temporaire segmentation sortie de l'algo CCM
    if args.vector_file_seg_ccm != None :
        vector_file_seg_ccm = args.vector_file_seg_ccm

    # Récupération du vecteur temporaire segmentation sortie du post traitement
    if args.vector_file_seg_post != None :
        vector_file_seg_post = args.vector_file_seg_post

    # Récupération du vecteur de sortie de la segmentation final
    if args.vector_file_seg_output != None :
        vector_file_seg_output = args.vector_file_seg_output

    # Récupération du nom du champs largeur pour les routes
    if args.roads_width_field != None :
        roads_width_field = args.roads_width_field

    # Récupération du nom du champs importnace des routes
    if args.road_importance_field != None :
        road_importance_field = args.road_importance_field

   # Récupération de la valeur de seuil pour l'importance des routes
    if args.road_importance_threshold != None :
        road_importance_threshold = args.road_importance_threshold

   # Récupération de la valeur du buffer pour l'importance des routes
    if args.buffer_size_road != None :
        buffer_size_road = args.buffer_size_road

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
        print(cyan + "UrbanMorphologySegmentation : " + endC + "ccm_folder : " + str(ccm_folder) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "emprise_vector : " + str(emprise_vector) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "GRA_file_input : " + str(GRA_file_input) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "TCD_file_input : " + str(TCD_file_input) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "IMD_file_input : " + str(IMD_file_input) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "vectors_road_input_list : " + str(vectors_road_input_list) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "vectors_build_input_list : " + str(vectors_build_input_list) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "vectors_water_area_input_list : " + str(vectors_water_area_input_list) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "sql_exp_road_list : " + str(sql_exp_road_list) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "sql_exp_build_list : " + str(sql_exp_build_list) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "sql_exp_water_list : " + str(sql_exp_water_list) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "pseudoRGB_file_output : " + str(pseudoRGB_file_output) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "raster_road_width_output : " + str(raster_road_width_output) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "raster_build_height_output : " + str(raster_build_height_output) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "vector_roads_output : " + str(vector_roads_output) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "vector_waters_area_output : " + str(vector_waters_area_output))
        print(cyan + "UrbanMorphologySegmentation : " + endC + "vector_file_seg_ccm : " + str(vector_file_seg_ccm) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "vector_file_seg_post : " + str(vector_file_seg_post) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "vector_file_seg_output : " + str(vector_file_seg_output) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "roads_width_field : " + str(roads_width_field) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "road_importance_field : " + str(road_importance_field) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "road_importance_threshold : " + str(road_importance_threshold) + endC)
        print(cyan + "UrbanMorphologySegmentation : " + endC + "buffer_size_road : " + str(buffer_size_road) + endC)
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
    processSegmentationUrbanMorpho(base_folder, ccm_folder, emprise_vector, GRA_file_input, TCD_file_input, IMD_file_input, vectors_road_input_list, vectors_build_input_list, vectors_water_area_input_list, sql_exp_road_list, sql_exp_build_list, sql_exp_water_list, pseudoRGB_file_output, raster_road_width_output, raster_build_height_output, vector_roads_output, vector_waters_area_output, vector_file_seg_ccm, vector_file_seg_post, vector_file_seg_output, roads_width_field, road_importance_field, road_importance_threshold, buffer_size_road, min_area_water_area, project_encoding, server_postgis, port_number, user_postgis, password_postgis, database_postgis, schema_postgis, resolution, no_data_value, epsg, format_raster, format_vector, extension_raster, extension_vector, path_time_log, save_results_intermediate, overwrite)

# ================================================

if __name__ == '__main__':
  main(gui=False)
