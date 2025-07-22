#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT QUI EFFECTUE DES TRAITEMENTS POST SEGMENTATION SUR LE MAILLAGE DE SORTIE DE L'ALGORITHME DE SEGMENTATION ET DE LA SEGMENTION ROUTE #
#                                                                                                                                           #
#                                                                                                                                           #
#############################################################################################################################################


"""
Nom de l'objet : SegPostProcessing.py
Description :
    Objectif : TODO

Date de creation : 02/10/2023
----------
Histoire :
----------
Origine : Ce script a été réalisé par Levis Antonetti dans le cadre de son stage sur la segmentation morphologique du tissu urbain (Tuteurs: Aurélien Mure, Gilles Fouvet).
          Ce script est le résultat de la synthèse du développement effectué sur des notebooks disponibles dans le répertoire /mnt/Data2/30_Stages_Encours/2023/MorphologieUrbaine_Levis/03_scripts
-----------------------------------------------------------------------------------------------------
Modifications :
         15/05/2025 Changement du nom du script CCMpostprocessing.py => SegPostProcessing.py
------------------------------------------------------
"""

##### Import #####

# System
import warnings
import os, sys
from osgeo import ogr ,osr, gdal

# Geomatique
import geopandas as gpd
import pandas as pd
from shapely import prepared
from shapely.ops import unary_union
from shapely.geometry import MultiLineString, LineString, MultiPolygon, Polygon

# Intern libs
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC
from Lib_file import removeFile, removeVectorFile, deleteDir
from Lib_vector import fusionVectors, getAttributeType, getAttributeValues, addNewFieldVector, setAttributeValuesList, deleteFieldsVector, renameFieldsVector, updateIndexVector
from Lib_vector2 import is_vector_file_empty
from Lib_postgis import openConnection, closeConnection, dropDatabase, createDatabase, importVectorByOgr2ogr, exportVectorByOgr2ogr, cutPolygonesByLines, cutPolygonesByPolygones

from CreateDataIndicateurPseudoRGB import explodeMultiGdf
from PolygonsMerging import mergeSmallPolygons

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 3 : affichage maximum de commentaires lors de l'execution du script. Intermédiaire : affichage intermédiaire
debug = 3


###########################################################################################################################################
#                                                                                                                                         #
# Post processing segmentation                                                                                                            #
#                                                                                                                                         #
###########################################################################################################################################

###########################################################################################################################################
# FUNCTION mixterSegmenationRoadsAndAlgo()                                                                                                 #
###########################################################################################################################################
def mixterSegmenationRoadsAndAlgo(vector_seg_algo_input, vector_seg_road_input, vector_seg_combined_output, field_fid="FID", field_area="area", threshold_area_poly=0, epsg=2154, format_vector='ESRI Shapefile'):
    """
    # ROLE:
    #     Mixer les segmentations issues de la fusion des routes et de l'alo de segmentation choisi
    #
    # PARAMETERS:
    #     vector_seg_algo_input : fichier vecteur d'entrées contenant la segmentation issu de l'algo.
    #     vector_seg_road_input : fichier vecteur d'entrées contenant la segmentation issue des routes.
    #     vector_seg_combined_output : fichier vecteur de sortie contenant la segmentation mixée.
    #     field_fid : nom du champs contenat le FID.
    #     field_area : nom du champs contenat la surface.
    #     threshold_area_poly :valeur du seuil de la surface minimal des polygones.
    #     epsg (int): EPSG code of the desired projection (default is 2154).
    #     format_vector : format du fichier vecteur de sortie
    # RETURNS:
    #     NA
    """

    if debug >= 1:
        print(cyan + "mixterSegmenationRoadsAndAlgo() : " + endC + "Ammellioration de la segmentation avec la segmentation du découpage des routes : ", vector_seg_algo_input)

    # Récupère les petits polygones en fonction d'un seuil et creer un masque  (de la segmentation issu des routes)
    #---------------------------------------------------------------------------------------------------------------
    gdf_seg_road_input = gpd.read_file(vector_seg_road_input)
    gdf_seg_road_input[field_area] = gdf_seg_road_input.geometry.area
    gdf_seg_road_small_poly = gdf_seg_road_input[gdf_seg_road_input[field_area] <= threshold_area_poly]
    gdf_seg_road_small_poly = gdf_seg_road_small_poly.drop_duplicates(subset="geometry")

    # Récupère les grands polygones en fonction d'un seuil (de la segmentation issu des routes)
    #------------------------------------------------------------------------------------------
    gdf_seg_road_big_poly = gdf_seg_road_input[gdf_seg_road_input[field_area] > threshold_area_poly]
    gdf_seg_road_big_poly = gdf_seg_road_big_poly.drop_duplicates(subset="geometry")

    # Creation d'un mask vecteur avec les petits polygones routes
    gdf_seg_road_masked = gdf_seg_road_small_poly.dissolve()

    # Appliquer le mask à la segmentation
    #-------------------------------------
    # Lire les fichiers vecteurs
    gdf_poly_seg = gpd.read_file(vector_seg_algo_input)
    gdf_poly_seg = gdf_poly_seg[["geometry",field_fid]]

    # Fusionner toutes les géométries du masque en une seule
    if not gdf_seg_road_masked.empty:
        #mask_union = gdf_seg_road_masked.union_all()
        mask_union = gdf_seg_road_masked.unary_union
        gdf_poly_seg_copy = gdf_poly_seg.copy()
        gdf_poly_seg_copy = gdf_poly_seg_copy[~gdf_poly_seg_copy.geometry.isna()]
        gdf_poly_seg_copy["geometry"] = [geom.difference(mask_union) for geom in gdf_poly_seg_copy.geometry]
    else:
        gdf_poly_seg_copy = gdf_poly_seg.copy()

    # Supprimer les géométries vides résultant de l'opération de différence
    gdf_seg_masked = gdf_poly_seg_copy[~gdf_poly_seg_copy.is_empty]

    # Decoupage des polygonnes de la segmentation de l'algo de segmentation avec les routes
    #---------------------------------------------------------------------------------------
    # Clip the input shapefile by the extent shapefile
    gdf_seg_masked_cut = gpd.overlay(gdf_seg_masked, gdf_seg_road_input.drop(columns=[field_fid]), how='intersection', keep_geom_type=True)

    # Fusion des segmentations de l'algo de segmentation et de la segmentation des routes
    #------------------------------------------------------------------------------------
    # Combiner les deux GeoDataFrames en un seul
    fields_to_get_list = [field_fid, field_area, "geometry"]
    gdf_seg_combined_tmp = pd.concat([gdf_seg_masked_cut[fields_to_get_list], gdf_seg_road_small_poly[fields_to_get_list]], ignore_index=True)
    gdf_seg_combined = gdf_seg_combined_tmp[fields_to_get_list].copy()

    # Mise a jour des champs field_fid et field_area
    gdf_seg_combined[field_area] = gdf_seg_combined.geometry.area

    # Sauvegarder le GeoDataFrame résultant dans un nouveau fichier shapefile si nécessaire
    gdf_seg_combined.to_file(vector_seg_combined_output, driver=format_vector, crs="EPSG:" + str(epsg))

    if debug >= 1:
        print(cyan + "mixterSegmenationRoadsAndAlgo() : " + endC + "Résultat de l'amélioration de la segmentation combiné : ", vector_seg_combined_output)

    return

###########################################################################################################################################
# FUNCTION indentifieSegmentationRoad()                                                                                                   #
###########################################################################################################################################
def indentifieSegmentationRoad(vector_line_skeleton_main_roads_input, vector_seg_input, vector_seg_crossroad_output, field_is_road, field_fid, field_org_fid, epsg=2154, format_vector='ESRI Shapefile') :
    """
    # ROLE:
    #     Identifer les polygones traversés par les routes mise à jour de la colonne "is_road".
    #
    # PARAMETERS:
    #     vector_line_skeleton_main_roads_input : vecteur du squelette des route tres légerement bufferisé d'entrée.
    #     vector_seg_input : fichier de segmentation d'entrée.
    #     vector_seg_crossroad_output : vecteur de segmentation ave l'information "is_road" de sortie.
    #     field_is_road : nom du champs boolean contenat l'information si le polygone est traversé par une route ou non.
    #     field_fid : nom du champs entier identifiant du polygone
    #     field_org_fid : nom du champs liste d'identifiant de l'id et les id voisins
    #     epsg (int): EPSG code of the desired projection (default is 2154).
    #     format_vector : format du fichier vecteur de sortie
    # RETURNS:
    #     NA.
    """
    # Fonction pour s'assurer que les lignes sont orientées de manière cohérente (par exemple, de gauche à droite)
    def normalize_direction(geom):
        if geom.geom_type == "LineString":
            # Normaliser une simple LineString
            if geom.coords[0][0] > geom.coords[-1][0]:
                return LineString(list(geom.coords)[::-1])
            return geom
        elif geom.geom_type == "MultiLineString":
            # Appliquer la normalisation à chaque sous-géométrie
            lines = []
            for line in geom.geoms:
                if line.coords[0][0] > line.coords[-1][0]:
                    lines.append(LineString(list(line.coords)[::-1]))
                else:
                    lines.append(line)
            return MultiLineString(lines)
        else:
            # Laisser les autres types de géométrie inchangés
            return geom

    # Distance de la ligne d'origine pour les lignes parallèles
    distance = 1.0
    field_is_road_left = "road_left"
    field_is_road_right = "road_right"

    # Chargement des données segmentées
    gdf_seg_tag_roads = gpd.read_file(vector_seg_input)
    gdf_seg_tag_roads['geometry'] = gdf_seg_tag_roads['geometry'].where(gdf_seg_tag_roads['geometry'].is_valid, gdf_seg_tag_roads['geometry'].buffer(0))
    gdf_seg_tag_roads[field_org_fid] = gdf_seg_tag_roads[field_fid].astype(str)

    # Chargement des données squelette
    gdf_skeleton = gpd.read_file(vector_line_skeleton_main_roads_input)
    gdf_skeleton['geometry'] = gdf_skeleton['geometry'].where(gdf_skeleton['geometry'].is_valid, gdf_skeleton['geometry'].buffer(0))

    # Appliquer la fonction pour normaliser la direction
    unsupported_types = gdf_skeleton[~gdf_skeleton['geometry'].geom_type.isin(["LineString", "MultiLineString"])]
    if not unsupported_types.empty:
        print(cyan + "indentifieSegmentationRoad() : " + yellow + "Warning : Certaines géométries ne sont pas LineString ou MultiLineString :" + unsupported_types + endC)
        gdf_skeleton = gdf_skeleton[gdf_skeleton['geometry'].geom_type.isin(["LineString", "MultiLineString"])]
    gdf_skeleton['geometry'] = gdf_skeleton['geometry'].astype(object).apply(normalize_direction)

    # Créer deux lignes parallèles : une à gauche et une à droite
    gdf_skeleton['left_parallel'] = gdf_skeleton['geometry'].map(lambda geom: geom.parallel_offset(distance, side='left') if geom.geom_type == 'LineString' else None)
    gdf_skeleton['right_parallel'] = gdf_skeleton['geometry'].map(lambda geom: geom.parallel_offset(distance, side='right') if geom.geom_type == 'LineString' else None)

    gdf_skeleton_left = gpd.GeoDataFrame(geometry=gdf_skeleton['left_parallel'])
    gdf_skeleton_right = gpd.GeoDataFrame(geometry=gdf_skeleton['right_parallel'])
    gdf_skeleton_left = gdf_skeleton_left[gdf_skeleton_left['geometry'].notnull()]
    gdf_skeleton_right = gdf_skeleton_right[gdf_skeleton_right['geometry'].notnull()]

    # Bufferiser les lignes pour avoir des polygones très fin
    gdf_skeleton_buf = gdf_skeleton.copy()
    gdf_skeleton_buf['geometry'] = gdf_skeleton_buf.buffer(distance=0.00001)
    gdf_skeleton_left_buf = gdf_skeleton_left.copy()
    gdf_skeleton_left_buf['geometry'] = gdf_skeleton_left_buf.buffer(distance=0.00001)
    gdf_skeleton_right_buf = gdf_skeleton_right.copy()
    gdf_skeleton_right_buf['geometry'] = gdf_skeleton_right.buffer(distance=0.00001)

    # Application de la fonction calculate intersects à la colonne 'geometry'
    sindex = gdf_seg_tag_roads.sindex

    # Calculer l'union une seule fois
    #unary_union_skeleton_buf = gdf_skeleton_buf.union_all()
    unary_union_skeleton_buf = gdf_skeleton_buf.unary_union
    # Préparer l'objet pour accélérer les tests d'intersection
    prepared_union = prepared.prep(unary_union_skeleton_buf)
    # Utiliser l'index spatial pour ne tester que les géométries candidates
    possible_matches_index = list(gdf_seg_tag_roads.sindex.query(unary_union_skeleton_buf))
    # Extraire les lignes candidates à partir des indices
    possible_matches = gdf_seg_tag_roads.iloc[possible_matches_index]
    # Appliquer l'intersection uniquement sur les candidats
    gdf_seg_tag_roads.loc[possible_matches_index, field_is_road] = possible_matches['geometry'].astype(object).apply(prepared_union.intersects)

    #unary_union_skeleton_left_buf = gdf_skeleton_left_buf.union_all()
    unary_union_skeleton_left_buf = gdf_skeleton_left_buf.unary_union
    prepared_union_left = prepared.prep(unary_union_skeleton_left_buf)
    possible_matches_index_left = list(gdf_seg_tag_roads.sindex.query(unary_union_skeleton_left_buf))
    possible_matches_left = gdf_seg_tag_roads.iloc[possible_matches_index_left]
    gdf_seg_tag_roads.loc[possible_matches_index_left, field_is_road_left] = possible_matches_left['geometry'].astype(object).apply(prepared_union_left.intersects)

    #unary_union_skeleton_right_buf = gdf_skeleton_right_buf.union_all()
    unary_union_skeleton_right_buf = gdf_skeleton_right_buf.unary_union
    prepared_union_right = prepared.prep(unary_union_skeleton_right_buf)
    possible_matches_index_right = list(gdf_seg_tag_roads.sindex.query(unary_union_skeleton_right_buf))
    possible_matches_right = gdf_seg_tag_roads.iloc[possible_matches_index_right]
    gdf_seg_tag_roads.loc[possible_matches_index_right, field_is_road_right] = possible_matches_right['geometry'].astype(object).apply(prepared_union_right.intersects)

    # Filtrer les polygones où FIELD_IS_ROAD est True
    gdf_is_roads = gdf_seg_tag_roads[gdf_seg_tag_roads[field_is_road] == True]

    if debug >= 1:
        print(cyan + "indentifieSegmentationRoad() : " + endC + "Identification des polygones de la segmentation traversés par les routes fichier de sortie :", vector_seg_crossroad_output)

    # Boucler sur chaque polygone
    for idx, road in gdf_is_roads.iterrows():
        try:
            is_left = road[field_is_road_left]
            is_right = road[field_is_road_right]

            # Trouver les voisins géométriques
            current_geom = gdf_is_roads.at[idx, "geometry"]
            gdf_others = gdf_is_roads.drop(index=idx)
            gdf_neighbors = gdf_others[gdf_others.geometry.intersects(current_geom)]

            # Filtrer les voisins valides
            gdf_neighbors = gdf_neighbors[~gdf_neighbors.geometry.is_empty & ~gdf_neighbors.geometry.isna()].copy()

            # Sélection des voisins selon la position
            if is_left and not is_right:
                gdf_road_neighbors_select = gdf_neighbors[gdf_neighbors[field_is_road_right] == True]
            elif is_right and not is_left:
                gdf_road_neighbors_select = gdf_neighbors[gdf_neighbors[field_is_road_left] == True]
            else:
                gdf_road_neighbors_select = gdf_neighbors[gdf_neighbors[field_is_road] == True]

            # Récupération des FIDs des voisins
            fid_list = gdf_road_neighbors_select[field_fid].tolist()
            fid_str_list = ",".join(map(str, fid_list))

        except Exception as e:
            fid_str_list = ""
            print(cyan + f"indentifieSegmentationRoad() : " + yellow + "Warning processing road at index : " +  str(int(gdf_is_roads.at[idx, field_fid])) + " : {e}" + endC)

        # Mise à jour de la colonne field_org_fid
        gdf_seg_tag_roads.at[idx, field_org_fid] = f"{road[field_org_fid]},{fid_str_list}"

    # Forcer les valeurs NULL du champ 'is_road' à 0
    gdf_seg_tag_roads[field_is_road] = gdf_seg_tag_roads[field_is_road].fillna(0)

    # Sauvegarde dans un fichier shape le resultat
    del gdf_seg_tag_roads[field_is_road_right]
    del gdf_seg_tag_roads[field_is_road_left]

    gdf_seg_tag_roads.to_file(vector_seg_crossroad_output, driver=format_vector, crs="EPSG:" + str(epsg))

    if debug >= 1:
        print(cyan + "indentifieSegmentationRoad() : " + endC + "Mise à jour des id origine des polygones traversés par les routes fichier de sortie :" +  vector_seg_crossroad_output)

    return

###########################################################################################################################################
# FUNCTION removeWaterSurfacesSeg()                                                                                                       #
###########################################################################################################################################
def removeWaterSurfacesSeg(vector_seg_input, vector_water_area_input, vector_seg_clean_water, field_fid, epsg=2154, format_vector='ESRI Shapefile'):
    """
    # ROLE:
    #     Nettoyage des segmentations des surfaces d'eau.
    #
    # PARAMETERS:
    #     vector_seg_input : fichier de segmentation d'entrée.
    #     vector_water_area_input : vecteur d'entrée surface en eau.
    #     vector_seg_clean_water : vecteur de segmentation nettoyer des surface d'eau de sortie.
    #     field_fid :  nom du champs contenat l'id.
    #     epsg (int): EPSG code of the desired projection (default is 2154).
    #     format_vector : format du fichier vecteur de sortie
    # RETURNS:
    #     NA.
    """

    if debug >= 1:
        print(cyan + "removeWaterSurfacesSeg() : " + endC + "Removing main water surface area from segmentation file...")

    # Apply difference between segmentation shpfile and clean water surface shapfile
    gdf_water_area = gpd.read_file(vector_water_area_input)
    water_union = unary_union(gdf_water_area.geometry)
    gdf_water_union = gpd.GeoDataFrame(geometry=[water_union], crs=gdf_water_area.crs)

    gdf_seg_confined_clean_small_poly = gpd.read_file(vector_seg_input)
    gdf_seg_seg_clean_water_area = gpd.overlay(gdf_seg_confined_clean_small_poly, gdf_water_union, how='difference', keep_geom_type=True)
    gdf_seg_poly_only = explodeMultiGdf(gdf_seg_seg_clean_water_area, field_fid)

    gdf_seg_poly_only.to_file(vector_seg_clean_water, driver=format_vector, crs="EPSG:" + str(epsg))
    if debug >= 1:
        print(cyan + "removeWaterSurfacesSeg() : " + endC + "main water surface area removed from segmentation file to {}\n".format(vector_seg_clean_water))

    return

###########################################################################################################################################
# FUNCTION segPostProcessing()                                                                                                            #
###########################################################################################################################################
def segPostProcessing(path_base_folder,  emprise_vector, vector_seg_road_input, vector_seg_input, vector_skeleton_main_roads_input, vector_water_area_input, vector_seg_output, no_data_value=0, epsg=2154,  format_raster="GTiff", format_vector='ESRI Shapefile', extension_raster=".tif", extension_vector=".shp", path_time_log = "", save_results_intermediate=False, overwrite=True):
    """
    # ROLE:
    #     Post Processing de la segmentation.
    #
    # PARAMETERS:
    #     path_base_folder : le dossier de travail.
    #     emprise_vector : fichier d'emprise.
    #     vector_seg_road_input : le fichier vecteur de segmentation des routes d'entrée.
    #     vector_seg_input : le fichier vecteur de segmentation d'entrée.
    #     vector_skeleton_main_roads_input : fichier contenant le squelette ligne des routes principales d'entrée.
    #     vector_water_area_input : fichier contenant les surfaces en eau d'entrée.
    #     vector_seg_output : le fichier vecteur de segmentation de sortie
    #     no_data_value : Option : Value pixel of no data (par défaut : 0).
    #     epsg (int): EPSG code of the desired projection (default is 2154).
    #     format_raster (str): Format de l'image de sortie (déeaut GTiff)
    #     format_vector (str): Format for the output vector file (default is 'ESRI Shapefile').
    #     extension_raster : extension des fichiers raster de sortie, par defaut = '.tif'
    #     extension_vector : extension du fichier vecteur de sortie, par defaut = '.shp'
    #     path_time_log : le fichier de log de sortie (par défaut : "").
    #     save_results_intermediate : fichiers de sorties intermediaires non nettoyées, par defaut = False
    #     overwrite : supprime ou non les fichiers existants ayant le meme nom
    # RETURNS:
    #     none
    """

    # Affichage des paramètres
    if debug >= 3:
        print(bold + green + "Variables dans le segPostProcessing - Variables générales" + endC)
        print(cyan + "segPostProcessing() : " + endC + "path_base_folder : " + str(path_base_folder))
        print(cyan + "segPostProcessing() : " + endC + "emprise_vector : " + str(emprise_vector))
        print(cyan + "segPostProcessing() : " + endC + "vector_seg_road_input : " + str(vector_seg_road_input))
        print(cyan + "segPostProcessing() : " + endC + "vector_seg_input : " + str(vector_seg_input))
        print(cyan + "segPostProcessing() : " + endC + "vector_skeleton_main_roads_input : " + str(vector_skeleton_main_roads_input))
        print(cyan + "segPostProcessing() : " + endC + "vector_water_area_input : " + str(vector_water_area_input))
        print(cyan + "segPostProcessing() : " + endC + "vector_seg_output : " + str(vector_seg_output))
        print(cyan + "segPostProcessing() : " + endC + "no_data_value : " + str(no_data_value))
        print(cyan + "segPostProcessing() : " + endC + "epsg : " + str(epsg))
        print(cyan + "segPostProcessing() : " + endC + "format_raster : " + str(format_raster))
        print(cyan + "segPostProcessing() : " + endC + "format_vector : " + str(format_vector))
        print(cyan + "segPostProcessing() : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "segPostProcessing() : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "segPostProcessing() : " + endC + "path_time_log : " + str(path_time_log))
        print(cyan + "segPostProcessing() : " + endC + "save_results_intermediate : "+ str(save_results_intermediate))
        print(cyan + "segPostProcessing() : " + endC + "overwrite : "+ str(overwrite))

    # Constantes pour la création automatique des repertoires temporaires
    FOLDER_POSTPROCESSING = "seg_post_processing"
    FOLDER_INPUT = "input"
    FOLDER_OUTPUT_SEG = "output_seg"

    # Constantes
    SUFFIX_WATERCLEAN = "_water_clean"
    SUFFIX_COMBINED = "_combined"
    SUFFIX_SMALLPOLY = "_small_poly"

    FIELD_FID = "FID"
    FIELD_IS_ROAD = "is_road"
    FIELD_AREA = "area"
    FIELD_ORG_FID = "org_id"

    AREA_MIN_POLYGON = 40000
    THRESHOLD_VERY_SMALL_AREA = 0.1

    # Creation des répertoires
    path_folder_postprocess = path_base_folder + os.sep + FOLDER_POSTPROCESSING
    if not os.path.exists(path_folder_postprocess):
        os.makedirs(path_folder_postprocess)

    path_folder_input = path_folder_postprocess + os.sep + FOLDER_INPUT
    if not os.path.exists(path_folder_input):
        os.makedirs(path_folder_input)

    path_folder_seg_output = path_folder_input + os.sep + FOLDER_OUTPUT_SEG
    if not os.path.exists(path_folder_seg_output):
        os.makedirs(path_folder_seg_output)

    # Mixer les Segmentations issues des routes et de l'algo de segmentation
    vector_seg_combined_output = os.path.splitext(vector_seg_input)[0] + SUFFIX_COMBINED + extension_vector
    mixterSegmenationRoadsAndAlgo(vector_seg_input, vector_seg_road_input, vector_seg_combined_output, FIELD_FID, FIELD_AREA, AREA_MIN_POLYGON, epsg, format_vector)

    if debug >= 1:
        print(cyan + "segPostProcessing() : " + endC + "Résultat de la segmentation en polygones par  fusion segmentation des routes et algo de segmentation fichier de sortie :", vector_seg_combined_output)

    # Nettoyage des segmentations des surfaces d'eau
    vector_seg_clean_water = path_folder_seg_output + os.sep + os.path.splitext(os.path.basename(vector_seg_input))[0] + SUFFIX_WATERCLEAN + extension_vector
    if vector_water_area_input != "" and os.path.isfile(vector_water_area_input) and not is_vector_file_empty(vector_water_area_input) :
        removeWaterSurfacesSeg(vector_seg_combined_output, vector_water_area_input, vector_seg_clean_water, FIELD_FID, epsg, format_vector)
    else :
        vector_seg_clean_water = vector_seg_combined_output

    # Pour les polygones traversés par les routes principales garder l'id du polygone d'origine
    updateIndexVector(vector_seg_clean_water, FIELD_FID, format_vector)

    # Calcul de de la surface
    gdf_seg_confined_clean = gpd.read_file(vector_seg_clean_water)
    gdf_seg_confined_clean = gdf_seg_confined_clean.explode(index_parts=False).reset_index(drop=True)
    gdf_seg_confined_clean[FIELD_AREA] = gdf_seg_confined_clean.geometry.area
    gdf_seg_confined_clean[FIELD_ORG_FID] = [[]] * len(gdf_seg_confined_clean)

    # Fusion des sufaces de polygones vraiment trop petites et supprimer les non fusionnés
    gdf_seg_confined_clean_small_poly = mergeSmallPolygons(gdf_seg_confined_clean, threshold_small_area_poly=THRESHOLD_VERY_SMALL_AREA, fid_column=FIELD_FID, org_id_list_column=FIELD_ORG_FID, area_column=FIELD_AREA)
    gdf_seg_confined_clean_small_poly = gdf_seg_confined_clean_small_poly.explode(index_parts=False).reset_index(drop=True)
    gdf_seg_confined_clean_small_poly[FIELD_AREA] = gdf_seg_confined_clean_small_poly.geometry.area
    vector_seg_clean_small_poly = path_folder_seg_output + os.sep + os.path.splitext(os.path.basename(vector_seg_input))[0] + SUFFIX_SMALLPOLY + extension_vector
    gdf_seg_confined_clean_small_poly[FIELD_ORG_FID] = gdf_seg_confined_clean_small_poly[FIELD_ORG_FID].apply(str)
    gdf_seg_confined_clean_small_poly.to_file(vector_seg_clean_small_poly, driver=format_vector, crs="EPSG:" + str(epsg))

    # Pour les polygones traversés par les routes principales garder l'id du polygone d'origine
    updateIndexVector(vector_seg_clean_small_poly, FIELD_FID, format_vector)

    # Identification des polygones decoupés par les routes
    warnings.simplefilter(action='ignore', category=FutureWarning)
    indentifieSegmentationRoad(vector_skeleton_main_roads_input, vector_seg_clean_small_poly, vector_seg_output, FIELD_IS_ROAD, FIELD_FID, FIELD_ORG_FID, epsg, format_vector)

    if debug >= 1:
        print(cyan + "segPostProcessing() : " + endC + "Fin resulat segementation découpé par les routes principales sans les sufaces d'eau {}\n".format(vector_seg_output))

    # Suppression des repertoires temporaires
    if not save_results_intermediate :
        if os.path.isfile(vector_seg_combined_output) :
            removeVectorFile(vector_seg_combined_output)
        if os.path.isfile(vector_seg_clean_water) :
            removeVectorFile(vector_seg_clean_water)
        if os.path.isfile(vector_seg_clean_small_poly) :
            removeVectorFile(vector_seg_clean_small_poly)
        if os.path.exists(path_folder_input):
            deleteDir(path_folder_input)

    return

# ==================================================================================================================================================

if __name__ == '__main__':

    ##### paramètres en entrées #####
    # Il est recommandé de prendre un répertoire avec accès rapide en lecture et écriture pour accélérer les traitements
    """
    BASE_FOLDER = "/mnt/RAM_disk/INTEGRATION"
    emprise_vector =  "/mnt/RAM_disk/INTEGRATION/emprise_fusion.shp"
    vector_skeleton_main_roads_input = "/mnt/RAM_disk/INTEGRATION/create_data/result/skeleton_primary_roads.shp"
    vector_water_area_input = "/mnt/RAM_disk/INTEGRATION/create_data/result/all_waters_area.shp"
    vector_seg_road_input = "/mnt/RAM_disk/INTEGRATION/create_data/result/pres_seg_road.shp"
    vector_seg_input = "/mnt/RAM_disk/INTEGRATION/slic_lissage_chaiken_5.shp"
    vector_seg_output = "/mnt/RAM_disk/INTEGRATION/seg_post_processing/toulouseseg_post.shp"
    """
    """
    BASE_FOLDER = "/mnt/RAM_disk/Grabel"
    emprise_vector =  "/mnt/RAM_disk/Grabel/emprise_grabels.shp"
    vector_skeleton_main_roads_input = "/mnt/RAM_disk/Grabel/create_data/result/skeleton_primary_roads_grabels2.shp"
    vector_water_area_input = "/mnt/RAM_disk/Grabel/create_data/result/all_waters.shp"
    vector_seg_road_input = "/mnt/RAM_disk/Grabel/create_data/result/pres_seg_road.shp"
    vector_seg_input = "/mnt/RAM_disk/Grabel/segmentation_SLIC_lissage_OSO.shp"
    vector_seg_output = "/mnt/RAM_disk/Grabel/seg_post_processing/grabels_seg_post.shp"
    """
    """
    BASE_FOLDER = "/mnt/RAM_disk/Data_blagnac"
    emprise_vector = "/mnt/RAM_disk/Data_blagnac/emprise_fusion.shp"
    vector_skeleton_main_roads_input = "/mnt/RAM_disk/Data_blagnac/create_data/result/skeleton_primary_roads.shp"
    vector_water_area_input = "/mnt/RAM_disk/Data_blagnac/create_data/result/all_waters.shp"
    vector_seg_road_input = "/mnt/RAM_disk/Data_blagnac/create_data/result/pres_seg_road.shp"
    vector_seg_input = "/mnt/RAM_disk/Data_blagnac/slic_lissage_chaiken_5.shp"
    vector_seg_output = "/mnt/RAM_disk/Data_blagnac/blagnac_seg_post.shp"
    """
    """
    BASE_FOLDER = "/mnt/RAM_disk/Grabels"
    emprise_vector = "/mnt/RAM_disk/Grabels/emprise_Grabels.shp"
    vector_skeleton_main_roads_input = "/mnt/RAM_disk/Grabels/create_data/result/skeleton_primary_roads.shp"
    vector_water_area_input = "/mnt/RAM_disk/Grabels/create_data/result/all_waters.shp"
    vector_seg_road_input = "//mnt/RAM_disk/Grabels/create_data/result/pres_seg_road_grabels.shp"
    vector_seg_input = "/mnt/RAM_disk/Grabels/slic_lissage_chaiken_5.shp"
    vector_seg_output = "/mnt/RAM_disk/Grabels/pres_seg_road_grabels_GFT.shp"
    """
    BASE_FOLDER = "/mnt/RAM_disk/INTEGRATION"
    emprise_vector =  "/mnt/RAM_disk/INTEGRATION/emprise/Emprise_Toulouse.shp"
    vector_skeleton_main_roads_input = "/mnt/RAM_disk/INTEGRATION/create_data/result/skeleton_primary_roads.shp"
    vector_water_area_input = "/mnt/RAM_disk/INTEGRATION/create_data/result/all_waters.shp"
    vector_seg_road_input = "/mnt/RAM_disk/INTEGRATION/create_data/result/pres_seg_road.shp"
    vector_seg_input = "/mnt/RAM_disk/INTEGRATION/segmentation_SLIC_Toulouse.shp"
    vector_seg_output = "/mnt/RAM_disk/INTEGRATION/pres_seg_Toulouse.shp"

    # Exec
    segPostProcessing(
        path_base_folder = BASE_FOLDER,
        emprise_vector = emprise_vector,
        vector_seg_road_input = vector_seg_road_input,
        vector_seg_input = vector_seg_input,
        vector_skeleton_main_roads_input = vector_skeleton_main_roads_input,
        vector_water_area_input = vector_water_area_input,
        vector_seg_output = vector_seg_output,
        no_data_value=0,
        epsg=2154,
        format_raster="GTiff",
        format_vector='ESRI Shapefile',
        extension_raster=".tif",
        extension_vector=".shp",
        path_time_log="",
        save_results_intermediate=False,
        overwrite=True
        )


