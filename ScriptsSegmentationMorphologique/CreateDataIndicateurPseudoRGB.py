#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT QUI CREER UNE PSEUDO IMAGE RGB À PARTIR D'INDICATEURS SPECIFIES                                                                    #
#                                                                                                                                           #
#############################################################################################################################################

"""
Nom de l'objet : CreateDataIndicateurPseudoRGB.py
Description :
    Objectif : Créer une image pseudo-RGB à partir d'indicateurs d'impermeabilités, de végétations et de routes qui servira ensuite comme image d'entrée
    pour la segmentation morphologique du tissu urbain

Date de creation : 02/10/2023
----------
Histoire :
----------
Origine : Ce script a été réalisé par Levis Antonetti dans le cadre de son stage sur la segmentation morphologique du tissu urbain (Tuteurs: Aurélien Mure, Gilles Fouvet).
          Ce script est le résultat de la synthèse du développement effectué sur des notebooks disponibles dans le répertoire /mnt/Data2/30_Stages_Encours/2023/MorphologieUrbaine_Levis/03_scripts
-----------------------------------------------------------------------------------------------------
Modifications
         le 14/05/2025 changement des données d'entrées des HRLayer aux données OSO

------------------------------------------------------
"""

##### Import #####

# System
import os, sys
from osgeo import ogr

# Geomatique
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.crs import CRS
from rasterio.enums import ColorInterp
import numpy as np
import networkx as nx
import pandas as pd
import geopandas as gpd
from geopandas import GeoDataFrame
from collections import Counter
from shapely.geometry import MultiLineString, LineString, MultiPolygon, Polygon, Point, box
from shapely.ops import unary_union, split
from centerline.geometry import Centerline
##from pygeoops import centerline

# Interne libs
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC
from Lib_raster import cutImageByVector, getProjectionImage, getPixelWidthXYImage, rasterizeVector
from Lib_vector import bufferVector, filterSelectDataVector, getAttributeNameList, addNewFieldVector, updateIndexVector, cutVectorAll
from Lib_vector2 import extendLines, removeRing, cutShapefileByExtent, removeInteriorPolygons, bufferPolylinesToPolygons
from Lib_file import deleteDir, copyVectorFile, removeVectorFile
from Lib_xml import parseDom, getListValueAttributeDom
from Lib_postgis import cutPolygonesByLines_Postgis

from PolygonsMerging import mergeSmallPolygons, FIELD_FID, FIELD_AREA, FIELD_ORG_ID_LIST, THRESHOLD_NANO_SMALL_AREA, THRESHOLD_MICRO_SMALL_AREA, THRESHOLD_SMALL_AREA_ROAD

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 3 : affichage maximum de commentaires lors de l'execution du script. Intermédiaire : affichage intermédiaire
debug = 1

###########################################################################################################################################
#                                                                                                                                         #
# UTILS                                                                                                                                   #
#                                                                                                                                         #
###########################################################################################################################################

########################################################################
# FUNCTION reprojectRaster()                                           #
########################################################################
def explodeGeom2Polygon(geom):
    """
    # ROLE:
    #     Fonction pour extraire tous les polygones simples
    """
    if geom is None:
        return []
    if isinstance(geom, Polygon):
        return [geom]
    elif isinstance(geom, MultiPolygon):
        return list(geom.geoms)
    elif isinstance(geom, GeometryCollection):
        return [g for g in geom.geoms if isinstance(g, Polygon)]
    else:
        return []

########################################################################
# FUNCTION reprojectRaster()                                           #
########################################################################
def reprojectRaster(input_file, output_file, src_epsg, dst_epsg):
    """
    # ROLE:
    #     Reprojects a GeoTIFF file from the source coordinate reference system (CRS) to the destination CRS.
    #
    # PARAMETERS:
    #     input_file (str): Path to the input GeoTIFF file to be reprojected.
    #     output_file (str): Path to the output GeoTIFF file where the reprojected data will be saved.
    #     src_epsg (int): EPSG code or the source CRS of the input GeoTIFF.
    #     dst_epsg (int): EPSG code or the destination CRS to which the input GeoTIFF will be reprojected.
    #
    # RETURNS:
    #     None
    #
    # EXAMPLE:
    #     reprojectRaster('input.tif', 'output.tif', 4326, 2154)
    #
    """

    src_crs = CRS.from_epsg(src_epsg)
    dst_crs = CRS.from_epsg(dst_epsg)

    with rasterio.open(input_file) as src:
        transform, width, height = calculate_default_transform(src_crs, dst_crs, src.width, src.height, *src.bounds)

        kwargs = src.meta.copy()
        kwargs.update({
            'crs': dst_crs,
            'transform': transform,
            'width': width,
            'height': height
        })

        with rasterio.open(output_file, 'w', **kwargs) as dst:
            reproject(
                source=rasterio.band(src, 1),
                destination=rasterio.band(dst, 1),
                src_transform=src.transform,
                src_crs=src_crs,
                dst_transform=transform,
                dst_crs=dst_crs,
                resampling=Resampling.nearest
            )
    return

########################################################################
# FUNCTION reprojectVector()                                           #
########################################################################
def reprojectVector(vector_input, vector_output, epsg=2154, format_vector='ESRI Shapefile'):
    """
    # ROLE:
    #     Update the projection of a GeoDataFrame and save it to a new file.
    #
    # PARAMETERS:
    #     vector_input (str): Path to the input GeoDataFrame file.
    #     vector_output (str): Path to the output GeoDataFrame file with the updated projection.
    #     epsg (int): EPSG code of the desired projection (default is 2154).
    #     format_vector (str): Format for the output vector file (default is 'ESRI Shapefile').
    #
    # RETURNS:
    #     None
    #
    # EXAMPLE:
    #     reprojectVector('input.shp', 'output.shp', 4326, 'ESRI Shapefile')
    #
    """

    gdf = gpd.read_file(vector_input)
    # Sauvegardez le GeoDataFrame avec la nouvelle projection dans un fichier de sortie
    #gdf.to_file(vector_output, crs="EPSG:" + str(epsg), driver=format_vector)
    gdf = gdf.set_crs(epsg=epsg, inplace=False)
    gdf.to_file(vector_output, driver=format_vector)
    return

########################################################################
# FUNCTION gdfFusionVectors()                                          #
########################################################################
def gdfFusionVectors(vectors_list, vector_all, format_vector, epsg=2154):
    """
    # ROLE:
    #    Fusion d'une fiste de vecteur avec geoPandas.
    #
    # PARAMETERS:
    #     vectors_list : liste des vecteur à fusionnés.
    #     vector_all : le vecteur fusionné.
    #     epsg (int): EPSG code of the desired projection (default is 2154).
    # RETURNS:
    #     le vecteur fusionné
    """

    gdf_vector_list = [gpd.read_file(vector_tmp) for vector_tmp in vectors_list]
    gdf_vector_all = gpd.GeoDataFrame(pd.concat(gdf_vector_list))
    #gdf_vector_all.to_file(vector_all, driver=format_vector, crs="EPSG:"+str(epsg))
    gdf_vector_all = gdf_vector_all.set_crs(epsg=epsg, inplace=False)
    gdf_vector_all.to_file(vector_all, driver=format_vector)

    return vector_all

########################################################################
# FUNCTION filterVectorsSql()                                          #
########################################################################
def filterVectorSql(vector_input_list, vector_output_list, sql_expression_list, format_vector='ESRI Shapefile'):
    """
    # ROLE:
    #     Reprojects a GeoTIFF file from the source coordinate reference system (CRS) to the destination CRS.
    #
    # PARAMETERS:
    #     vector_input (list): Liste de fichier vecteur d'entrée à filtrer.
    #     vector_outpout (list): Liste de fichier vecteur de sortie filtré par l'expression sql.
    #     sql_expression_list (list): Liste d'expression sql pour le filtrage des fichiers vecteur de bd exogenes.
    #     format_vector (str): Format for the output vector file (default is 'ESRI Shapefile').
    #
    # RETURNS:
    #     None
    #
    """

    if debug >= 1:
        print(cyan + "filterVectorSql() : " + endC + "Filtrage SQL BD input...")

    if sql_expression_list != [] :
        for idx_vector in range (len(vector_input_list)):
            vector_input = vector_input_list[idx_vector]
            vector_filtered = vector_output_list[idx_vector]

            if idx_vector < len(sql_expression_list) :
                sql_expression = sql_expression_list[idx_vector]
            else :
                sql_expression = ""

            # Filtrage par ogr2ogr
            if sql_expression != "":
                names_attribut_list = getAttributeNameList(vector_input, format_vector)
                column = "'"
                for name_attribut in names_attribut_list :
                    column += name_attribut + ", "
                column = column[0:len(column)-2]
                column += "'"
                ret = filterSelectDataVector(vector_input, vector_filtered, column, sql_expression, format_vector)
                if not ret :
                    print(cyan + "filterVectorSql() : " + bold + yellow + "Attention problème lors du filtrage des BD vecteurs l'expression SQL %s est incorrecte" %(sql_expression) + endC)
                    copyVectorFile(vector_input, vector_filtered)
            else :
                print(cyan + "filterVectorSql() : " + bold + yellow + "Pas de filtrage sur le fichier du nom : " + endC + vector_filtered)
                copyVectorFile(vector_input, vector_filtered)

    return

########################################################################
# FUNCTION calculateAndCleanSmallPolygonArea()                         #
########################################################################
def calculateAndCleanSmallPolygonArea(gdf, field_area, min_area_polygon):
    """
    # ROLE:
    #     Nettoye les petits polygonnes d'une surface min.
    #
    # PARAMETERS:
    #     gdf : dataframe du vecteur polygones d'entrée.
    #     field_area : le champs de surface à filter par min_area_polygon
    #     min_area_polygon : la valeur min de la surface des polygonnes.
    #
    # RETURNS:
    #     la data frame de sortie filtrer
    """
    # Fusion des polygones eau
    gdf = gdf.explode(index_parts=False).reset_index(drop=True)

    # Construire un graphe de connexité spatiale
    G = nx.Graph()
    for idx, geom in gdf.geometry.items():
        G.add_node(idx)

    for i in range(len(gdf)):
        for j in range(i + 1, len(gdf)):
            if gdf.geometry[i].touches(gdf.geometry[j]):
                G.add_edge(i, j)

    # Déterminer les groupes connectés
    components = list(nx.connected_components(G))

    # Assigner un identifiant de groupe
    group_ids = {}
    for group_idx, comp in enumerate(components):
        for idx in comp:
            group_ids[idx] = group_idx

    gdf["group"] = gdf.index.map(group_ids)

    # Dissoudre seulement les groupes avec plusieurs polygones
    multi_groups = gdf["group"].value_counts()
    groups_to_merge = multi_groups[multi_groups > 1].index

    # Fusionner les groupes qui se touchent
    gdf_merged = gdf[gdf["group"].isin(groups_to_merge)].dissolve(by="group")

    # Garder les polygones isolés (pas à fusionner)
    gdf_isolated = gdf[~gdf["group"].isin(groups_to_merge)]

    # Combiner les deux
    gdf_clean = gpd.GeoDataFrame(pd.concat([gdf_merged, gdf_isolated], ignore_index=True), crs=gdf.crs)

    # Calculer la superficie de chaque polygone
    gdf_clean[field_area] = gdf_clean.geometry.area

    # Supprimer les polygones ayant une superficie inférieure à min_area_polygon
    gdf_clean = gdf_clean[gdf_clean[field_area] >= min_area_polygon]

    return gdf_clean

########################################################################
# FONCTION cleanSegmentsWithIsolatedEndpoints()                        #
########################################################################
def cleanSegmentsWithIsolatedEndpoints(gdf_lines, gdf_polygons, nb_max_iteration=5):
    """
    # ROLE:
    #     Nettoyer les segment en bout de ligne contenu dans le polygone.
    #
    # PARAMETERS:
    #     gdf_lines : dataframe du vecteur lignes à nettoyer
    #     gdf_polygons dataframe du vecteur polygones d'emprise d'entrée.
    #     nb_max_iteration : le nombre maximun d'iteration
    #
    # RETURNS:
    #     le dataframe ligne nettoyé de ses extrémités
    #
    """
    gdf = gdf_lines.explode(ignore_index=True).copy()
    polygon_union = gdf_polygons.unary_union

    iteration = 0
    while iteration <= nb_max_iteration:
        iteration += 1

        # 1. Récupérer tous les endpoints
        endpoints = []
        for geom in gdf.geometry:
            if geom and not geom.is_empty and len(geom.coords) >= 2:
                endpoints.extend([geom.coords[0], geom.coords[-1]])

        # 2. Compter les endpoints
        endpoint_counts = Counter(endpoints)

        # 3. Fonction de filtrage
        def is_unique_endpoint_inside_emprise(geom):
            if geom is None or geom.is_empty or len(geom.coords) < 2:
                return False
            start = geom.coords[0]
            end = geom.coords[-1]

            start_unique = endpoint_counts[start] == 1 and polygon_union.contains(Point(start))
            end_unique = endpoint_counts[end] == 1 and polygon_union.contains(Point(end))

            return start_unique or end_unique

        # 4. Masque des segments à supprimer
        mask = gdf.geometry.astype(object).apply(is_unique_endpoint_inside_emprise)
        count_to_remove = mask.sum()
        if debug >= 3:
            print(cyan + "cleanSegmentsWithIsolatedEndpoints() : " + endC + f"Iteration {iteration}: {count_to_remove} segments à supprimer")

        if count_to_remove == 0:
            break  # Fin du nettoyage

        # 5. Supprimer les segments concernés
        gdf = gdf[~mask].copy()

    return gdf

########################################################################
# FONCTION reprojectAndCutRaster()                                     #
########################################################################
def reprojectAndCutRaster(emprise_vector, file_raster_input, file_raster_output, resolution, no_data_value=0, epsg=2154, format_raster='GTiff', format_vector='ESRI Shapefile', save_results_intermediate=False):
    """
    # ROLE:
    #     Reprojects and cuts raster files in a given folder based on a specified extent.
    #
    # PARAMETERS:
    #     emprise_vector (str): vector file representing the geographic extent for cutting.
    #     file_raster_input (str): path to the raster to be processed.
    #     file_raster_output (str): path to the raster output reproj and cut.
    #     resolution( int): resolution forcé des rasters de travail.
    #     no_data_value : Option : Value pixel of no data (par défaut : 0).
    #     epsg (int): EPSG code of the desired projection (default is 2154).
    #     format_raster (str): Format de l'image de sortie (défaut GTiff)
    #     format_vector (str): Format for the output vector file (default is 'ESRI Shapefile').
    #     save_results_intermediate : (boolean): supprime les fichiers temporaires si True, (defaut = False).
    #
    # RETURNS:
    #     NA
    #
    # EXAMPLE:
    #     reprojectAndCutRaster(emprise_vector, path_file_raster_input, path_file_raster_output, epsg=2154)
    #
    """

    # Constante
    FOLDER_TMP = "temp"

    # Create projection and cut results folder if not exist
    path_folder_raster = os.path.dirname(file_raster_output)
    path_folder_tmp = path_folder_raster + os.sep + FOLDER_TMP
    filename_raster = os.path.splitext(os.path.basename(file_raster_input))[0]
    raster_proj = path_folder_tmp +  os.sep + filename_raster +  "_" + str(epsg) + os.path.splitext(file_raster_output)[1].lower()
    if not os.path.exists(path_folder_tmp):
        os.makedirs(path_folder_tmp)

    if debug >= 1:
        print(cyan + "reprojectAndCutRaster() : " + endC + "reprojecting and cutting raster file...")

    # Reprojection
    proj_src,_ = getProjectionImage(file_raster_input)
    if proj_src != epsg :
        reprojectRaster(file_raster_input, raster_proj, proj_src, epsg)
    else :
        raster_proj = file_raster_input

    # Cut
    cutImageByVector(emprise_vector, raster_proj, file_raster_output, pixel_size_x=resolution, pixel_size_y=resolution, in_line=False, no_data_value=no_data_value, epsg=epsg, format_raster=format_raster, format_vector=format_vector)

    # Supression des fichiers temporaires
    if not save_results_intermediate:
        if os.path.exists(path_folder_tmp):
            deleteDir(path_folder_tmp)

    # End
    if debug >= 1:
        print()
        print(cyan + "reprojectAndCutRaster() : " + endC + "reprojecting and cutting done to {} and {}\n".format(file_raster_input, file_raster_output))

    return

########################################################################
# FONCTION reprojectAndCutVector()                                     #
########################################################################
def reprojectAndCutVector(emprise_vector, vector_input, vector_output, epsg=2154, format_vector='ESRI Shapefile', save_results_intermediate=False):
    """
    # ROLE:
    #     Reprojects and cuts vector files in a given folder based on a specified extent.
    #
    # PARAMETERS:
    #     path_folder_vectors (str): path to the folder containing the vector files to be processed.
    #     emprise_vector (str): vector file representing the geographic extent for cutting.
    #     vector_input (str): path to the vector file to be processed.
    #     vector_output (str): path to the vector file output reproj and cut.
    #     epsg (int): projection to use for vector reprojection (default is 2154).
    #     save_results_intermediate (boolean): supprime ou non les fichiers temporaires si True (default=False).
    #
    # RETURNS:
    #     NA
    #
    # EXAMPLE:
    #     reprojectAndCutVector(emprise_vector, path_file_vector_input, path_file_vector_output, epsg=2154)
    #
    """

    # Constante
    FOLDER_TMP = "temp"

    # Create projection and cut results folder if not exist
    path_folder_vector = os.path.dirname(vector_output)
    path_folder_tmp = path_folder_vector + os.sep + FOLDER_TMP
    filename_vector = os.path.splitext(os.path.basename(vector_input))[0]
    vector_proj = path_folder_tmp + os.sep + filename_vector +  "_" + str(epsg) + os.path.splitext(vector_output)[1].lower()
    if not os.path.exists(path_folder_tmp):
        os.makedirs(path_folder_tmp)

    if debug >= 1:
        print(cyan + "reprojectAndCutVector() : " + endC + "reprojecting and cutting vector file...")

    # Reprojection
    reprojectVector(vector_input, vector_proj, epsg, format_vector)

    # Cut
    cutShapefileByExtent(emprise_vector, vector_proj, vector_output, epsg, format_vector)

    # Supression des fichiers temporaires
    if not save_results_intermediate:
        if os.path.exists(path_folder_tmp):
            deleteDir(path_folder_tmp)

    # End
    if debug >= 1:
        print(cyan + "reprojectAndCutVector() : " + endC + "reprojecting and cutting done to {} and {}\n".format(vector_input, vector_output))

    return

###########################################################################################################################################
#                                                                                                                                         #
# CREATE IMAGE PSEUDO RGB WITH INDICATEURS DATA                                                                                           #
#                                                                                                                                         #
###########################################################################################################################################

###########################################################################################################################################
# FUNCTION skeletonRoads()                                                                                                                #
###########################################################################################################################################
def skeletonRoads(path_folder_union_roads, emprise_vector, vector_all_roads_input, vector_line_skeleton_main_roads_output, vector_roads_main_output, vector_roads_secondary_output, field_fid, road_importance_field="IMPORTANCE", road_importance_threshold=4, road_importance_threshold_sup=2, road_width_field="LARGEUR", field_road_shod="NATURE", road_shod_threshold_list=["Autoroute", "Quasi-autoroute", "Route à 2 chaussées"], buffer_size=30.0, epsg=2154, format_vector='ESRI Shapefile', extension_vector=".shp", save_results_intermediate=False):
    """
    # ROLE:
    #     Creation du sequelette des routes principales (vecteurs).
    #
    # PARAMETERS:
    #     path_folder_union_roads : répertoire de travail local.
    #     emprise_vector (str): le fichier vecteur d'emprise de la zone d'étude.
    #     vector_all_roads_input : fichier vecteur d'entrées contenant toutes les routes.
    #     vector_line_skeleton_main_roads_output : fichier vecteur de sortie contenant le squelette des routes principales.
    #     vector_roads_main_output (str) :  fichier de sortie vecteur des routes importantes à  2 voies buffurisé.
    #     vector_roads_secondary_output (str) :  fichier de sortie vecteur des routes segondaire et non 2 voies.
    #     field_fid :  nom du champs contenat l'id.
    #     road_importance_field : champs importance des routes (par defaut : "IMPORTANCE").
    #     road_width_field : champs largeur des routes (par defaut : "LARGEUR").
    #     road_importance_threshold : valeur du seuil d'importance (par défaut : 4).
    #     road_importance_threshold_sup : valeur du seuil d'importance (par défaut : 2).
    #     field_road_shod : champs nature des routes nombre de chaussées (par defaut : "NATURE").
    #     road_shod_threshold_list : Liste des valeurs des natures de routes à retenir (par défaut : "Autoroute", "Quasi-autoroute", "Route à 2 chaussées").
    #     buffer_size : taille du buffer limite pour le skelette (par défaut :30.0).
    #     epsg (int): EPSG code of the desired projection (default is 2154).
    #     format_vector : format du fichier vecteur de sortie
    #     extension_vector : extension du fichier vecteur de sortie, par defaut = '.shp'
    #     save_results_intermediate : fichiers de sorties intermediaires non nettoyées, par defaut = False
    # RETURNS:
    #     NA
    """

    # Constantes
    SUFFIX_BUF = "_buf"
    SUFFIX_TWO_SHODS = "_two_shods"
    SUFFIX_POLY = "_poly"
    MAX_ITERATION = 5

    if debug >= 1:
        print(cyan + "skeletonRoads() : " + endC + "Union of segmentation result with main roads...")

    # Creation des répertoires
    if debug >= 4:
        FOLDER_FILTER_BUF = "filter_buf"
        path_folder_union_roads_buf = os.path.dirname(vector_line_skeleton_main_roads_output) + os.sep + FOLDER_FILTER_BUF
        if not os.path.exists(path_folder_union_roads_buf):
            os.makedirs(path_folder_union_roads_buf)

    # Get main roads according to an importance threshold and buffer roads (linestrings to polygons)
    gdf_roads = gpd.read_file(vector_all_roads_input)
    gdf_emprise = gpd.read_file(emprise_vector)

    # Remove no data value in column modify if needed depending on data
    gdf_roads[road_importance_field] = gdf_roads[road_importance_field].fillna("NC")
    gdf_roads[road_importance_field] = gdf_roads[road_importance_field].replace("NC", 6).astype(int)

    # Get roads with road_importance_field <= road_importance_threshold
    gdf_roads[road_importance_field] = pd.to_numeric(gdf_roads[road_importance_field], errors='coerce')
    gdf_roads_primary = gdf_roads[gdf_roads[road_importance_field] <= road_importance_threshold]
    gdf_roads_primary_sup = gdf_roads[gdf_roads[road_importance_field] <= (road_importance_threshold_sup)]
    gdf_roads_secondary = gdf_roads[gdf_roads[road_importance_field] > road_importance_threshold]

    # Filtrage des routes à 2 chaussées
    gdf_roads_two_shods = gdf_roads_secondary[gdf_roads_secondary[field_road_shod].isin(road_shod_threshold_list)]
    gdf_roads_secondary_simple = gdf_roads_secondary[~gdf_roads_secondary[field_road_shod].isin(road_shod_threshold_list) & gdf_roads_secondary[field_road_shod].notna()]

    # Sauvegarde du lineaires routes secondaires
    #gdf_roads_secondary_simple.to_file(vector_roads_secondary_output, driver=format_vector, crs="EPSG:" + str(epsg))
    gdf_roads_secondary_simple = gdf_roads_secondary_simple.set_crs(epsg=epsg, inplace=False)
    gdf_roads_secondary_simple.to_file(vector_roads_secondary_output, driver=format_vector)

    # Fusion des donnees routes en combinant les deux GeoDataFrames
    gdf_roads_select = gpd.GeoDataFrame(pd.concat([gdf_roads_primary, gdf_roads_two_shods], ignore_index=True))

    if debug >= 4:
        vector_roads_two_shods = path_folder_union_roads_buf + os.sep + os.path.splitext(os.path.basename(vector_all_roads_input))[0] + SUFFIX_TWO_SHODS + extension_vector
        #gdf_roads_select.to_file(vector_roads_two_shods, driver=format_vector, crs="EPSG:" + str(epsg))
        gdf_roads_select = gdf_roads_select.set_crs(epsg=epsg, inplace=False)
        gdf_roads_select.to_file(vector_roads_two_shods, driver=format_vector)
        print(cyan + "skeletonRoads() : " + endC + "Sortie fichier vector_roads_two_shods : ", vector_roads_two_shods)

    # Delete incorrect geometries which are neither LineString or MultiLineString
    if debug >= 4:
        print(cyan + "skeletonRoads() : " + endC + "length before: {}".format(len(gdf_roads)))
        print(cyan + "skeletonRoads() : " + endC + "length after {}".format(len(gdf_roads_select)))
        print(cyan + "skeletonRoads() : " + endC + "unique values: {}".format(gdf_roads["geometry"].geom_type.unique()))

    gdf_roads_select_clean = gdf_roads_select[(gdf_roads_select["geometry"].geom_type == 'LineString') | (gdf_roads_select["geometry"].geom_type == 'MultiLineString')]
    gdf_roads_primary_clean = gdf_roads_primary_sup[(gdf_roads_primary_sup["geometry"].geom_type == 'LineString') | (gdf_roads_primary_sup["geometry"].geom_type == 'MultiLineString')]

    if debug >= 1:
        print(cyan + "skeletonRoads() : " + endC + "Nettoyage du vecteur route d'entrée : ", vector_all_roads_input)

    # Create buffers  around the lines --> polygons main roads
    factor_buff = 1.0
    gdf_roads_main_buf = bufferPolylinesToPolygons(gdf_roads_primary_clean, None, road_width_field, factor_buff=factor_buff, resolution=2, cap_style=2)
    gdf_roads_main_buf['geometry'] = gdf_roads_main_buf['geometry'].apply(lambda geom: removeRing(geom, area_threshold=250.0))
    gdf_roads_main_buf = gdf_roads_main_buf.buffer(distance=1, resolution=0, cap_style=1)
    gdf_roads_main_buf = gdf_roads_main_buf.buffer(distance=-1, resolution=0, cap_style=1)

    # Appliquer l'extraction et reconstituer un GeoDataFrame propre
    gdf_roads_main_buf = GeoDataFrame(gdf_roads_main_buf.drop(columns="geometry"), geometry=gdf_roads_main_buf, crs=gdf_roads_main_buf.crs)
    gdf_roads_main_buf.reset_index(drop=True, inplace=True)
    gdf_roads_main_buf[field_fid] = range(1, len(gdf_roads_main_buf) + 1)
    gdf_roads_main_buf = gdf_roads_main_buf.rename(columns={field_fid: "index"})
    gdf_roads_main_buf = gdf_roads_main_buf[["index", "geometry"]]

    # Appliquer l'extraction
    polygons = []
    attributes = []

    for idx, row in gdf_roads_main_buf.iterrows():
        for poly in explodeGeom2Polygon(row.geometry):
            polygons.append(poly)
            attributes.append(row.drop('geometry'))

    # Reconstruction du GeoDataFrame propre
    gdf_roads_main_exploded = gpd.GeoDataFrame(attributes, geometry=polygons, crs=gdf_roads_main_buf.crs)
    gdf_roads_main_exploded.reset_index(drop=True, inplace=True)
    gdf_roads_main_exploded["id"] = range(1, len(gdf_roads_main_exploded) + 1)
    #gdf_roads_main_exploded.to_file(vector_roads_main_output, driver=format_vector, crs="EPSG:" + str(epsg))
    gdf_roads_main_exploded = gdf_roads_main_exploded.set_crs(epsg=epsg, inplace=False)
    gdf_roads_main_exploded.to_file(vector_roads_main_output, driver=format_vector)

    # Create buffers around the lines --> polygons
    buffer_size_line = 0.25
    gdf_roads_buf = bufferPolylinesToPolygons(gdf_roads_select_clean, buffer_size_line, "", factor_buff=1, resolution=1, cap_style=2)

    if debug >= 4:
        # To file
        s_road_importance_threshold = str(road_importance_threshold).replace(".", "f")
        s_buffer_size = str(buffer_size_line).replace(".", "f")
        vector_roads_filter_buf = path_folder_union_roads_buf + os.sep + os.path.splitext(os.path.basename(vector_all_roads_input))[0] + "_" + road_importance_field[:3] + s_road_importance_threshold + SUFFIX_BUF + s_buffer_size + extension_vector
        #gdf_roads_buf.to_file(vector_roads_filter_buf, driver=format_vector, crs="EPSG:" + str(epsg))
        gdf_roads_buf = gdf_roads_buf.set_crs(epsg=epsg, inplace=False)
        gdf_roads_buf.to_file(vector_roads_filter_buf, driver=format_vector)
        print(cyan + "skeletonRoads() : " + endC + "Sortie fichier vector_roads_filter_buf : ", vector_roads_filter_buf)

    # Create Buffer to polygon and fusion polygon
    gdf_roads_buf_poly = gdf_roads_buf.buffer(distance=buffer_size, resolution=0, cap_style=2)
    gdf_roads_buf_poly_union = gpd.GeoDataFrame(geometry=[gdf_roads_buf_poly.unary_union], crs=gdf_roads_buf_poly.crs)

    if debug >= 4:
        vector_roads_filter_buf_poly = path_folder_union_roads_buf + os.sep + os.path.splitext(os.path.basename(vector_all_roads_input))[0] + "_" + road_importance_field[:3] + SUFFIX_BUF + SUFFIX_POLY + extension_vector
        #gdf_roads_buf_poly_union.to_file(vector_roads_filter_buf_poly, driver=format_vector, crs="EPSG:" + str(epsg))
        gdf_roads_buf_poly_union = gdf_roads_buf_poly_union.set_crs(epsg=epsg, inplace=False)
        gdf_roads_buf_poly_union.to_file(vector_roads_filter_buf_poly, driver=format_vector)
        print(cyan + "skeletonRoads() : " + endC + "Sortie fichier vector_roads_filter_buf_poly : ", vector_roads_filter_buf_poly)

    if debug >= 1:
        print(cyan + "skeletonRoads() : " + endC + "Buffer du vecteur route nettoyé : ", vector_all_roads_input)

    # Create the squelette line into buffer_polygon
    gdf_roads_buf_poly_line = gdf_roads_buf_poly_union.copy(deep=True)
    gdf_roads_buf_poly_line['geometry'] = gdf_roads_buf_poly_line['geometry'].simplify(tolerance=4, preserve_topology=True)
    gdf_roads_buf_poly_line['geometry'] = gdf_roads_buf_poly_line['geometry'].astype(object).apply(lambda geom: Centerline(geom, interpolation_distance=5).geometry)
    gdf_roads_line = gpd.GeoDataFrame(gdf_roads_buf_poly_line, crs="EPSG:" + str(epsg), geometry="geometry")

    if debug >= 4:
        vector_roads_line = path_folder_union_roads_buf + os.sep + os.path.splitext(os.path.basename(vector_all_roads_input))[0] + "_" + road_importance_field[:3] + extension_vector
        #gdf_roads_line.to_file(vector_roads_line, driver=format_vector, crs="EPSG:" + str(epsg))
        gdf_roads_line = gdf_roads_line.set_crs(epsg=epsg, inplace=False)
        gdf_roads_line.to_file(vector_roads_line, driver=format_vector)
        print(cyan + "skeletonRoads() : " + endC + "Sortie fichier vector_roads_line : ", vector_roads_line)

    if debug >= 1:
        print(cyan + "skeletonRoads() : " + endC + "Squelette du buffer route : ", vector_all_roads_input)

    # Filter only squelette line into buffer_polygon erode
    gdf_roads_line_clean = gdf_roads_line[(gdf_roads_line["geometry"].geom_type == 'LineString') | (gdf_roads_line["geometry"].geom_type == 'MultiLineString')]

    # Ne garder que les brins à l'exterieur de l'emprise
    gdf_roads_line_filter_ext = cleanSegmentsWithIsolatedEndpoints(gdf_roads_line_clean, gdf_emprise, MAX_ITERATION)
    gdf_roads_line_filter_clean = gpd.clip(gdf_roads_line_filter_ext, gdf_emprise.unary_union)

    # Sauvegarde du lineaires routes principales fusionées et filtrées
    #gdf_roads_line_filter_clean.to_file(vector_line_skeleton_main_roads_output, driver=format_vector, crs="EPSG:" + str(epsg))
    gdf_roads_line_filter_clean = gdf_roads_line_filter_clean.set_crs(epsg=epsg, inplace=False)
    gdf_roads_line_filter_clean.to_file(vector_line_skeleton_main_roads_output, driver=format_vector)
    if debug >= 1:
        print(cyan + "skeletonRoads() : " + endC + "Résultat du squelette des routes fichier de sortie : ", vector_line_skeleton_main_roads_output)

    # Supression des repertoirtes temporaires
    if not save_results_intermediate :
         if debug >= 4:
             if os.path.isfile(vector_roads_two_shods) :
                removeVectorFile(vector_roads_two_shods)
             if os.path.isfile(vector_roads_filter_buf) :
                removeVectorFile(vector_roads_filter_buf)
             if os.path.isfile(vector_roads_filter_buf_poly) :
                removeVectorFile(vector_roads_filter_buf_poly)
             if os.path.isfile(vector_roads_line) :
                removeVectorFile(vector_roads_line)

    return

###########################################################################################################################################
# FUNCTION simplificationRoadTwoWay()                                                                                                     #
###########################################################################################################################################
def simplificationRoadTwoWay(vector_all_roads_input, vector_squeleton_input, vector_new_roads_output, road_importance_field="IMPORTANCE", road_importance_threshold=4, field_road_shod="NATURE", road_shod_threshold_list=["Autoroute", "Quasi-autoroute", "Route à 2 chaussées"], extension_length_lines=15, epsg=2154, format_vector='ESRI Shapefile', extension_vector='.shp', save_results_intermediate=False):
    """
    # ROLE:
    #     Creation d'un vecteur de route ou les axes à 2 voies sont remplacées par le squelette des routes à 2 voies.
    #
    # PARAMETERS:
    #     vector_all_roads_input : fichier vecteur d'entrée contenant toutes les routes.
    #     vector_squeleton_input : fichier vecteur d'entrée le squelette des routes principales.
    #     vector_new_roads_output : fichier vecteur de sortie contenant le shema des routes avec implification
    #     road_importance_field : champs importance des routes (par defaut : "IMPORTANCE").
    #     road_importance_threshold : valeur du seuil d'importance (par défaut : 4).
    #     field_road_shod : champs nuture des routes nombre de chaussées (par defaut : "NATURE").
    #     road_shod_threshold_list : Liste des valeurs des natures de routes à retenir (par défaut : "Autoroute", "Quasi-autoroute", "Route à 2 chaussées").
    #     extension_length_lines : taille de l'extension des lignes (par défaut :15).
    #     epsg (int): EPSG code of the desired projection (default is 2154).
    #     format_vector : format du fichier vecteur de sortie, par defaut = 'ESRI Shapefile'
    #     extension_vector (str) : extension du fichier vecteur de sortie, par defaut = '.shp'
    #     save_results_intermediate (Bool) : fichiers de sorties intermediaires non nettoyées, par defaut = False
    # RETURNS:
    #     NA
    """

    if debug >= 1:
        print(cyan + "simplificationRoadTwoWay() : " + endC + "Simplification main roads 2 ways...")

    # Constantes
    SUFFIX_EXTEND = "_extend"
    SUFFIX_SIMPLE = "_simple"

    # Charger les données
    gdf_roads = gpd.read_file(vector_all_roads_input)
    gdf_skeletton = gpd.read_file(vector_squeleton_input)

    # Convertir MultiLineString en plusieurs LineString
    gdf_roads = gdf_roads.explode(index_parts=False)

    # Filtrer les géométries invalides
    gdf_roads = gdf_roads[gdf_roads.is_valid]
    gdf_skeletton = gdf_skeletton[gdf_skeletton.is_valid]

    # Filter les routes principales et les routes a 2 axes
    gdf_roads[road_importance_field] = pd.to_numeric(gdf_roads[road_importance_field], errors='coerce')
    gdf_roads_secondary = gdf_roads[gdf_roads[road_importance_field] > road_importance_threshold]
    gdf_roads_simple = gdf_roads_secondary[~gdf_roads_secondary[field_road_shod].isin(road_shod_threshold_list)]

    # Etendre les extrémitées des routes si possible jusqu'à intersection
    vector_roads_extend = os.path.dirname(vector_all_roads_input) + os.sep + os.path.splitext(os.path.basename(vector_all_roads_input))[0] + SUFFIX_EXTEND + extension_vector
    vector_roads_simple = os.path.dirname(vector_all_roads_input) + os.sep + os.path.splitext(os.path.basename(vector_all_roads_input))[0] + SUFFIX_SIMPLE + extension_vector
    #gdf_roads_simple.to_file(vector_roads_simple, driver=format_vector, crs="EPSG:" + str(epsg))
    gdf_roads_simple = gdf_roads_simple.set_crs(epsg=epsg, inplace=False)
    gdf_roads_simple.to_file(vector_roads_simple, driver=format_vector)

    extendLines(vector_roads_simple, vector_roads_extend, vector_squeleton_input, extension_length_lines, False, epsg, format_vector)
    gdf_roads_new = gpd.read_file(vector_roads_extend)

    # Combiner les deux GeoDataFrames
    combined_gdf = gpd.GeoDataFrame(pd.concat([gdf_roads_new, gdf_skeletton], ignore_index=True))

    # Effacer les résutats intermédiaires
    if not save_results_intermediate :
        if os.path.isfile(vector_roads_extend) :
            removeVectorFile(vector_roads_extend)
        if os.path.isfile(vector_roads_simple) :
            removeVectorFile(vector_roads_simple)

    # Sauvegarder le résultat
    #combined_gdf.to_file(vector_new_roads_output, driver=format_vector, crs="EPSG:" + str(epsg))
    combined_gdf = combined_gdf.set_crs(epsg=epsg, inplace=False)
    combined_gdf.to_file(vector_new_roads_output, driver=format_vector)

    if debug >= 1:
        print(cyan + "simplificationRoadTwoWay() : " + endC + "Fin simplification des routes à 2 voies fichier de sortie : ", vector_new_roads_output)

    return

###########################################################################################################################################
# FUNCTION convertRaster2ImageRGB()                                                                                                       #
###########################################################################################################################################
def convertRaster2ImageRGB(raster_input, QML_file_input, rgb_image_output, epsg=2154, codage="uint8", no_data_value=0, format_raster="GTiff", overwrite=True):
    """
    # ROLE:
    #      Transformation d'une image d'entrée contenant des valeurs sur  une bande en fichier 3 bandes rgb
    #      grace à un fichier de style QML.
    #
    # PARAMETERS:
    #     raster_input(str): raster file containing the values.
    #     QML_file_input (str): the file concatenated style to apply.
    #     rgb_image_output (str): image de sortie en RGB (3 bandes).
    #     epsg (int): EPSG code of the desired projection (default is 2154).
    #     codage (str): encodage du fichier raster de sortie, (default="uint8").
    #     no_data_value : value pixel of no data (par défaut : 0).
    #     format_raster (str) : Format de l'image de sortie (défaut GTiff).
    #     overwrite : supprime ou non les fichiers existants ayant le meme nom, (par defaut = True).
    #
    # RETURNS:
    #     NA.
    #
    """

    # Supprimer le fichier de sortie si il existe déjà
    if os.path.exists(rgb_image_output) :
        if overwrite :
            os.remove(rgb_image_output)
        else :
            return

    # Lecture du fichier de style OSO
    xmldoc = parseDom(QML_file_input)
    valueList = getListValueAttributeDom(xmldoc, 'colorPalette','paletteEntry', 'value', 'rasterrenderer')
    colorList = getListValueAttributeDom(xmldoc, 'colorPalette','paletteEntry', 'color', 'rasterrenderer')

    # Initialiser la LUT avec des zéros
    lut = np.zeros((256, 3), dtype=np.uint8)

    for index in range (len(valueList)) :
        value = valueList[index]
        hex_color = colorList[index]
        #if int(value) == no_data_value :
        #    lut[int(value)] = [255, 255, 255]
        if hex_color != "#000000" :
            r = int(hex_color[1:3], 16)
            g = int(hex_color[3:5], 16)
            b = int(hex_color[5:7], 16)
            lut[int(value)] = [r, g, b]

    # Charger l'image d'entrée
    with rasterio.open(raster_input) as src:
        val_image = src.read(1)  # Lire la première bande
        transform = src.transform
        crs = src.crs
        height, width = src.height, src.width

    # Transformation du fichier image en fichier RGB
    rgb_image = lut[val_image]

    # Définir le profil pour le fichier de sortie
    profile = {
        'driver': format_raster,
        'height': height,
        'width': width,
        'count': 3,  # Trois bandes pour R, G, B
        'dtype': codage,
        'crs': 'EPSG:%s'%(str(epsg)),
        'transform': transform,
        'photometric': 'RGB'
    }

    # Écrire l'image RGB
    with rasterio.open(rgb_image_output, 'w', **profile) as dst:
        # Rasterio attend les données sous la forme (bandes, lignes, colonnes)
        dst.write(rgb_image[:, :, 0], 1)  # Rouge
        dst.write(rgb_image[:, :, 1], 2)  # Vert
        dst.write(rgb_image[:, :, 2], 3)  # Bleu

        # Définir l'interprétation des couleurs pour chaque bande
        dst.colorinterp = [ColorInterp.red, ColorInterp.green, ColorInterp.blue]

    return

###########################################################################################################################################
# FONCTION createDataIndicateurPseudoRGB()                                                                                                #
###########################################################################################################################################
def createDataIndicateurPseudoRGB(path_base_folder, emprise_vector, OSO_file_input, QML_file_input, vectors_road_input_list, vectors_railway_input_list, vectors_build_input_list, vector_water_area_input_list, sql_exp_road_list, sql_exp_railway_list, sql_exp_build_list, sql_exp_water_list, OSO_file_output, pseudoRGB_file_output, raster_build_height_output, vector_roads_output, vector_roads_main_output,  vector_waters_area_output, vector_line_skeleton_main_roads_output, vector_roads_pres_seg_output, road_importance_field="IMPORTANCE", road_importance_threshold=4, road_importance_threshold_sup=2, road_width_field="LARGEUR", road_nature_field="NATURE", railway_nature_field="NATURE", railway_importance_values= "Principale", buffer_size_skeleton=30.0, extension_length_lines=20, min_area_water_area=30000, resolution=10, no_data_value=0, epsg=2154, server_postgis="localhost", port_number=5432, user_postgis="postgres", password_postgis="postgres", database_postgis="cutbylines", schema_postgis="public", project_encoding="latin1" , format_raster="GTiff", format_vector='ESRI Shapefile', extension_raster=".tif", extension_vector=".shp", path_time_log="", save_results_intermediate=False, overwrite=True):

    """
    # ROLE:
    #     Creates pseudo-RGB image data from various indicators and input files.
    #
    # PARAMETERS:
    #     path_base_folder, (str): le répertoire de base de travail.
    #     emprise_vector (str): le fichier vecteur d'emprise de la zone d'étude.
    #     OSO_file_input (str) : chemin vers le fichier raster d'entrée OSO (Occupation des Sols).
    #     QML_file_input (str) :chemin vers le fichier style de l'OSO (Passage valeur classe OSO en RVB).
    #     vectors_road_input_list (list) : list of paths to road files (routes primaires et secondaires).
    #     vectors_railway_input_list (list) : list of paths to railway files (voies ferrées).
    #     vectors_build_input_list (list) : liste des fichiers contenant les batis d'entrées.
    #     vector_water_area_input_list (list) : liste des fichiers contenant les surface en eau d'entrées.
    #     sql_exp_road_list (list) : liste d'expression sql pour le filtrage des fichiers vecteur de bd exogenes routes.
    #     sql_exp_railway_list (list) : liste d'expression sql pour le filtrage des fichiers vecteur de bd exogenes voies ferrées.
    #     sql_exp_build_list (list) : liste d'expression sql pour le filtrage des fichiers vecteur de bd exogenes batis.
    #     sql_exp_water_list (list) : liste d'expression sql pour le filtrage des fichiers vecteur de bd exogenes surfaces en eau.
    #     OSO_file_output (str) : fichier raster OSO découpé en sortie.
    #     pseudoRGB_file_output (str) : fichier de pseudo-RGB image resultat en sortie.
    #     raster_build_height_output (str) :  fichier de sortie rasteur des batis.
    #     vector_roads_output (str) : fichier de sortie vecteur contenant toutes les routes.
    #     vector_roads_main_output (str) :  fichier de sortie vecteur des routes importantes à  2 voies buffurisé.
    #     vector_waters_area_output (str) : fichier de sortie vecteur contenant toutes les surfaces en eau.
    #     vector_line_skeleton_main_roads_output (str) : fichier de sortie vecteur contenant le skelette ligne des routes principales.
    #     vector_roads_pres_seg_output (str) : fichier de sortie vecteur contenant une prés segmentation avec les routes.
    #     road_importance_field (str) : champs importance des routes (par defaut : "IMPORTANCE").
    #     road_importance_threshold (int) : valeur du seuil d'importance (par défaut : 4).
    #     road_importance_threshold_sup (int) : valeur du seuil d'importance (par défaut : 2).
    #     road_width_field (str) : champs largeur des routes (par defaut : "LARGEUR").
    #     road_nature_field : champs nature des routes (par defaut : "NATURE").
    #     railway_nature_field : champs nature des voies ferrées (par defaut : "NATURE").
    #     railway_importance_values : valeur des voies ferrées à garder (par defaut : "Principale").
    #     buffer_size_skeleton : taille du buffer pour la creation du squelette (par défaut : 30.0).
    #     extension_length_lines : taille de l'extension des lignes (par défaut : 20).
    #     min_area_water_area : seuil minimun de surface d'eau (par défaut : 30000).
    #     resolution (int): resolution forcé des rasters de travail (par défaut : 10).
    #     no_data_value  (int) : Option : Value pixel of no data (par défaut : 0).
    #     epsg (int):  EPSG code of the desired projection (default is 2154).
    #     server_postgis : nom du serveur postgis.
    #     port_number : numéro du port pour le serveur postgis.
    #     user_postgis : le nom de l'utilisateurs postgis.
    #     password_postgis : le mot de passe de l'utilisateur postgis.
    #     database_postgis : le nom de la base postgis à utiliser.
    #     schema_postgis : le nom du schéma à utiliser.
    #     project_encoding : format des strings
    #     format_raster (str) : Format de l'image de sortie (défaut GTiff)
    #     format_vector (str) : Format for the output vector file (default is 'ESRI Shapefile').
    #     extension_raster (str) : extension des fichiers raster de sortie, par defaut = '.tif'
    #     extension_vector (str) : extension du fichier vecteur de sortie, par defaut = '.shp'
    #     path_time_log (str) : fichier de log de sortie, par defaut = ""
    #     save_results_intermediate (Bool) : fichiers de sorties intermediaires non nettoyées, par defaut = False
    #     overwrite (Bool) : supprime ou non les fichiers existants ayant le meme nom, par defaut = True
    #
    # RETURNS:
    #     None
    #
    # EXAMPLE:
    #     createDataIndicateurPseudoRGB("/data_folder", "emprise.shp", ["primary_routes.shp","secondary_routes.shp"], "surfaces_eau.shp", "GRA.tif", "TCD.tif", "IMD.tif", "resolution_ref.tif")
    """

    # Affichage des paramètres
    if debug >= 3:
        print(bold + green + "Variables dans le createDataIndicateurPseudoRGB - Variables générales" + endC)
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "path_base_folder : " + str(path_base_folder))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "emprise_vector : " + str(emprise_vector))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "OSO_file_input : " + str(OSO_file_input))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "QML_file_input : " + str(QML_file_input))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "vectors_road_input_list : " + str(vectors_road_input_list))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "vectors_railway_input_list : " + str(vectors_railway_input_list))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "vectors_build_input_list : " + str(vectors_build_input_list))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "vector_water_area_input_list : " + str(vector_water_area_input_list))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "sql_exp_road_list : " + str(sql_exp_road_list))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "sql_exp_railway_list : " + str(sql_exp_railway_list))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "sql_exp_build_list : " + str(sql_exp_build_list))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "sql_exp_water_list : " + str(sql_exp_water_list))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "OSO_file_output : " + str(OSO_file_output))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "pseudoRGB_file_output : " + str(pseudoRGB_file_output))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "raster_build_height_output : " + str(raster_build_height_output))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "vector_roads_output : " + str(vector_roads_output))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "vector_roads_main_output : " + str(vector_roads_main_output))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "vector_waters_area_output : " + str(vector_waters_area_output))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "vector_line_skeleton_main_roads_output : " + str(vector_line_skeleton_main_roads_output))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "vector_roads_pres_seg_output : " + str(vector_roads_pres_seg_output))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "road_importance_field : " + str(road_importance_field))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "road_importance_threshold : " + str(road_importance_threshold))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "road_importance_threshold_sup : " + str(road_importance_threshold_sup))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "road_width_field : " + str(road_width_field))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "road_nature_field : " + str(road_nature_field))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "railway_nature_field : " + str(railway_nature_field))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "railway_importance_values : " + str(railway_importance_values))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "buffer_size_skeleton : " + str(buffer_size_skeleton))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "min_area_water_area : " + str(min_area_water_area))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "resolution : " + str(resolution))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "no_data_value : " + str(no_data_value))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "epsg : " + str(epsg))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "server_postgis : " + str(server_postgis) + endC)
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "port_number : " + str(port_number) + endC)
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "user_postgis : " + str(user_postgis) + endC)
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "password_postgis : " + str(password_postgis) + endC)
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "database_postgis : " + str(database_postgis) + endC)
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "schema_postgis : " + str(schema_postgis) + endC)
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "project_encoding : " + str(project_encoding) + endC)
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "format_raster : " + str(format_raster))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "format_vector : " + str(format_vector))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "path_time_log : " + str(path_time_log))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "save_results_intermediate : "+ str(save_results_intermediate))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "overwrite : "+ str(overwrite))

    # Répertoires
    FOLDER_CREATE_DATA = "create_data"
    FOLDER_VECTOR = "vecteur"

    # Constantes
    SUFFIX_CUT = "_cut"
    SUFFIX_BUF = "_buf"
    SUFFIX_CLEAN = "_clean"
    SUFFIX_FILTER = "_filt"
    SUFFIX_TEMP = "_tmp"
    SUFFIX_EXTEND = "_extend"
    SUFFIX_SIMPLE = "_simp"
    SUFFIX_SECONDARY = "_secondary"

    BASE_NAME_ALL_RAILWAY = "all_railway"
    BASE_NAME_ALL_NETWORKS = "all_networks"
    BASE_NAME_ALL_BUILT = "all_build"

    CODAGE_8BITS = 'uint8'

    # Filtre route a double voies
    ROAD_SHOD_THRESHOLD_LIST = ["Autoroute", "Quasi-autoroute", "Route à 2 chaussées"]

    # Creation du répertoire de sortie si il n'existe pas
    if not os.path.exists(path_base_folder):
        os.makedirs(path_base_folder)
    path_folder_output = os.path.dirname(vector_roads_output)
    if not os.path.exists(path_folder_output):
        os.makedirs(path_folder_output)
    path_folder_output = os.path.dirname(vector_waters_area_output)
    if not os.path.exists(path_folder_output):
        os.makedirs(path_folder_output)
    path_folder_output = os.path.dirname(vector_line_skeleton_main_roads_output)
    if not os.path.exists(path_folder_output):
        os.makedirs(path_folder_output)
    path_folder_output = os.path.dirname(raster_build_height_output)
    if not os.path.exists(path_folder_output):
        os.makedirs(path_folder_output)
    path_folder_output = os.path.dirname(pseudoRGB_file_output)
    if not os.path.exists(path_folder_output):
        os.makedirs(path_folder_output)

    # Creation des répertoires temporaires
    # Vecteur
    path_folder_base_vector = path_base_folder + os.sep + FOLDER_CREATE_DATA + os.sep + FOLDER_VECTOR
    if not os.path.exists(path_folder_base_vector):
        os.makedirs(path_folder_base_vector)

    # RASTER
    # Reproject (2154) and cut with emprise raster file
    path_folder_cut_raster = ""
    path_folder_cut_raster_ref_img = ""
    pixel_size, _ = getPixelWidthXYImage(OSO_file_input)
    buffer_dist = 2 * pixel_size
    emprise_vector_tmp = path_folder_base_vector + os.sep + os.path.splitext(os.path.basename(emprise_vector))[0] + SUFFIX_BUF + extension_vector
    bufferVector(emprise_vector, emprise_vector_tmp, buffer_dist, "", 1.0, 10, format_vector)
    reprojectAndCutRaster(emprise_vector_tmp, OSO_file_input, OSO_file_output, resolution, no_data_value, epsg, format_raster, format_vector, save_results_intermediate)

    # Définir une image de référence à partir d'une image raster pour établir la résolution de la rasterisation
    file_img_ref = OSO_file_output

    # Vecteurs voies ferrées #
    #------------------------#
    if debug >= 1:
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "creation of files containing railway width informations")
    vectors_railway_filtered_list = []

    if vectors_railway_input_list and len(vectors_railway_input_list) > 0 :
        # Listes des valeurs a prendre en compte
        railway_importance_value_list = [element.strip() for element in railway_importance_values.split(',')]

        # Filtrage des voies ferrées non importante
        if sql_exp_railway_list == None or sql_exp_railway_list == []:
            sql_exp_railway_list = []
            for vectors_railway_input in vectors_railway_input_list :
                sql_exp_railway_list.append("")
        railway_importance_values_str = ""
        for railway_importance_value in railway_importance_value_list :
            railway_importance_values_str += "'" + railway_importance_value + "',"
        railway_nature_condition_str = "%s IN (%s)"%(railway_nature_field, railway_importance_values_str[:-1])
        for i in range(len(sql_exp_railway_list)) :
            sql_exp_railway = sql_exp_railway_list[i]
            if sql_exp_railway == "" :
                sql_exp_railway_list[i] = railway_nature_condition_str
            else :
                sql_exp_railway_list[i] = sql_exp_railway + " AND " + railway_nature_condition_str

        # Filtrage SQL voies ferrées
        if sql_exp_railway_list != None and  sql_exp_railway_list != [] :
            vectors_railway_filtered_list = []
            for vector_railway in vectors_railway_input_list :
                vector_railway_filtered = path_folder_base_vector + os.sep + os.path.splitext(os.path.basename(vector_railway))[0] + SUFFIX_FILTER + extension_vector
                vectors_railway_filtered_list.append(vector_railway_filtered)
            filterVectorSql(vectors_railway_input_list, vectors_railway_filtered_list, sql_exp_railway_list, format_vector)
        else :
           vectors_railway_filtered_list = vectors_railway_input_list

        # Concatenantion des fichiers voies ferrées
        vectors_railway_cut_list = []
        for vector_railway in vectors_railway_filtered_list :
            vector_railway_cut = path_folder_base_vector + os.sep + os.path.splitext(os.path.basename(vector_railway))[0] + "_" +  str(epsg) + SUFFIX_CUT + extension_vector
            reprojectAndCutVector(emprise_vector, vector_railway, vector_railway_cut, epsg, format_vector, save_results_intermediate)
            vectors_railway_cut_list.append(vector_railway_cut)

        # Fusionner les fichiers de voies ferrées
        vector_railway_output = path_folder_output + os.sep + BASE_NAME_ALL_RAILWAY + extension_vector
        if len(vectors_railway_cut_list) > 1 :
            gdfFusionVectors(vectors_railway_cut_list, vector_railway_output, format_vector, epsg)
        else :
            copyVectorFile(vectors_railway_cut_list[0], vector_railway_output, format_vector)

        # Nettoyage des données voies ferrées
        gdf_railway = gpd.read_file(vector_railway_output)
        if "id" in gdf_railway.columns:
            gdf_railway.rename(columns={"id":"ID"}, inplace=True)
        gdf_railway = gdf_railway[["ID", "geometry", railway_nature_field]]
        #gdf_railway.to_file(vector_railway_output, driver=format_vector, crs="EPSG:" + str(epsg))
        gdf_railway = gdf_railway.set_crs(epsg=epsg, inplace=False)
        gdf_railway.to_file(vector_railway_output, driver=format_vector)

    # Vecteurs Routes #
    #-----------------#
    if debug >= 1:
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "creation of files containing roads width informations")

    vector_roads_tmp = os.path.splitext(vector_roads_output)[0] + SUFFIX_TEMP + os.path.splitext(vector_roads_output)[1]
    # Filtrage SQL Routes
    if sql_exp_road_list != None and  sql_exp_road_list != [] :
        vectors_road_filtered_list = []
        for vector_road in vectors_road_input_list :
            vector_road_filtered = path_folder_base_vector + os.sep + os.path.splitext(os.path.basename(vector_road))[0] + SUFFIX_FILTER + extension_vector
            vectors_road_filtered_list.append(vector_road_filtered)
        filterVectorSql(vectors_road_input_list, vectors_road_filtered_list, sql_exp_road_list, format_vector)
    else :
       vectors_road_filtered_list = vectors_road_input_list

    # Concatenantion des fichiers routes
    vectors_road_cut_list = []
    for vector_road in vectors_road_filtered_list :
        vector_road_cut = path_folder_base_vector + os.sep + os.path.splitext(os.path.basename(vector_road))[0] + "_" +  str(epsg) + SUFFIX_CUT + extension_vector
        reprojectAndCutVector(emprise_vector, vector_road, vector_road_cut, epsg, format_vector, save_results_intermediate)
        vectors_road_cut_list.append(vector_road_cut)

    # Fusionner routes_primaires et secondaires
    if len(vectors_road_cut_list) > 1 :
        gdfFusionVectors(vectors_road_cut_list, vector_roads_tmp, format_vector, epsg)
    else :
        copyVectorFile(vectors_road_cut_list[0], vector_roads_tmp, format_vector)

    # Remplir l'imformation importances des routes si vide
    gdf_roads = gpd.read_file(vector_roads_tmp)
    gdf_roads[road_importance_field] = gdf_roads[road_importance_field].fillna("NC")
    gdf_roads[road_importance_field] = gdf_roads[road_importance_field].replace("NC", 6).astype(int)
    if "id" in gdf_roads.columns:
        gdf_roads.rename(columns={"id":"ID"}, inplace=True)
    gdf_roads = gdf_roads[["ID", "geometry", road_importance_field, road_width_field, road_nature_field]]
    #gdf_roads.to_file(vector_roads_tmp, driver=format_vector, crs="EPSG:" + str(epsg))
    gdf_roads = gdf_roads.set_crs(epsg=epsg, inplace=False)
    gdf_roads.to_file(vector_roads_tmp, driver=format_vector)

    # Creation du fichier vecteur contenant les informations ligne du squelette des route principale
    if debug >= 1:
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "creating vector file containing skeleton line of main roads")

    vector_line_skeleton_main_roads_tmp = os.path.splitext(vector_line_skeleton_main_roads_output)[0] + SUFFIX_TEMP + os.path.splitext(vector_line_skeleton_main_roads_output)[1]
    vector_roads_secondary_output = os.path.splitext(vector_line_skeleton_main_roads_output)[0] + SUFFIX_SECONDARY + os.path.splitext(vector_line_skeleton_main_roads_output)[1]
    vector_roads_main_tmp = os.path.splitext(vector_roads_main_output)[0] + SUFFIX_TEMP + os.path.splitext(vector_roads_main_output)[1]
    vector_roads_main_cut = os.path.splitext(vector_roads_main_output)[0] + SUFFIX_CUT + os.path.splitext(vector_roads_main_output)[1]

    skeletonRoads(path_folder_base_vector, emprise_vector, vector_roads_tmp, vector_line_skeleton_main_roads_tmp, vector_roads_main_tmp, vector_roads_secondary_output, FIELD_FID, road_importance_field, road_importance_threshold, road_importance_threshold_sup, road_width_field,road_nature_field, ROAD_SHOD_THRESHOLD_LIST, buffer_size_skeleton, epsg, format_vector, extension_vector, save_results_intermediate)

    # Decoupe des polygones routes principales par les routes secondaires
    vector_roads_secondary_extend = os.path.splitext(vector_roads_secondary_output)[0] + SUFFIX_EXTEND + os.path.splitext(vector_roads_secondary_output)[1]
    vector_roads_secondary_extend_cut = os.path.splitext(vector_roads_secondary_output)[0] + SUFFIX_EXTEND + SUFFIX_CUT + os.path.splitext(vector_roads_secondary_output)[1]
    extendLines(vector_roads_secondary_output, vector_roads_secondary_extend, vector_line_skeleton_main_roads_tmp, 20, False, epsg, format_vector)
    gdf_roads_secondary_extend = gpd.read_file(vector_roads_secondary_extend)
    gdf_roads_secondary_extend = gdf_roads_secondary_extend[(gdf_roads_secondary_extend["geometry"].geom_type == 'LineString') | (gdf_roads_secondary_extend["geometry"].geom_type == 'MultiLineString')]
    gdf_roads_secondary_extend['ID'] = gdf_roads_secondary_extend.index
    gdf_roads_secondary_extend = gdf_roads_secondary_extend.explode(index_parts=False).reset_index(drop=True)
    gdf_roads_secondary_extend = gdf_roads_secondary_extend[["geometry","ID"]]
    #gdf_roads_secondary_extend.to_file(vector_roads_secondary_extend, driver=format_vector, crs="EPSG:" + str(epsg))
    gdf_roads_secondary_extend = gdf_roads_secondary_extend.set_crs(epsg=epsg, inplace=False)
    gdf_roads_secondary_extend.to_file(vector_roads_secondary_extend, driver=format_vector)

    cutVectorAll(vector_roads_main_tmp, vector_roads_secondary_extend, vector_roads_secondary_extend_cut, save_results_intermediate, format_vector)
    cutPolygonesByLines_Postgis(vector_roads_secondary_extend_cut, vector_roads_main_tmp, vector_roads_main_cut, epsg, project_encoding, server_postgis, port_number, user_postgis, password_postgis, database_postgis, schema_postgis, path_time_log="", format_vector=format_vector, save_results_intermediate=False, overwrite=True)
    cutVectorAll(emprise_vector, vector_roads_main_cut, vector_roads_main_output, save_results_intermediate, format_vector)

    # Fusion des tres petits polygons routes
    gdf_roads_main = gpd.read_file(vector_roads_main_output)
    gdf_roads_main = gdf_roads_main.reset_index(drop=False)
    gdf_roads_main[FIELD_AREA] = gdf_roads_main.geometry.area
    gdf_roads_main[FIELD_FID] = range(1, len(gdf_roads_main) + 1)
    gdf_roads_main = gdf_roads_main[["geometry", FIELD_FID, FIELD_AREA]]
    gdf_roads_main[FIELD_ORG_ID_LIST] = [[i] for i in range(100000000, 100000000 + len(gdf_roads_main))]
    gdf_roads_main_merged = mergeSmallPolygons(gdf_roads_main, threshold_small_area_poly=THRESHOLD_SMALL_AREA_ROAD, fid_column=FIELD_FID, org_id_list_column=FIELD_ORG_ID_LIST, area_column=FIELD_AREA)
    del gdf_roads_main_merged[FIELD_ORG_ID_LIST]
    gdf_roads_main_merged = gdf_roads_main_merged[gdf_roads_main_merged['geometry'].notnull()]
    gdf_roads_main_merged = gdf_roads_main_merged[gdf_roads_main_merged.geometry.area > THRESHOLD_NANO_SMALL_AREA]
    #gdf_roads_main_merged.to_file(vector_roads_main_output, driver=format_vector, crs="EPSG:" + str(epsg))
    gdf_roads_main_merged = gdf_roads_main_merged.set_crs(epsg=epsg, inplace=False)
    gdf_roads_main_merged.to_file(vector_roads_main_output, driver=format_vector)

    if debug >= 1:
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "creation of vector file containing  skeleton line of main roads done to {}".format(vector_line_skeleton_main_roads_tmp))

    # Vecteurs Batis #
    #----------------#
    if debug >= 1:
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "creation of files containing build width informations")

    # Filtrage SQL Batis
    if sql_exp_build_list != None and  sql_exp_build_list != [] :
        vectors_build_filtered_list = []
        for vector_build in vectors_build_input_list :
            vector_build_filtered = path_folder_base_vector + os.sep + os.path.splitext(os.path.basename(vector_build))[0] + SUFFIX_FILTER + extension_vector
            vectors_build_filtered_list.append(vector_build_filtered)
        filterVectorSql(vectors_build_input_list, vectors_build_filtered_list, sql_exp_build_list, format_vector)
    else :
       vectors_build_filtered_list = vectors_build_input_list

    # Concatenantion des fichiers batis
    vectors_build_cut_list = []
    for vector_build in vectors_build_filtered_list:
        # Cut shapefiles with emprise
        vector_build_cut = path_folder_base_vector + os.sep + os.path.splitext(os.path.basename(vector_build))[0] + "_" +  str(epsg) + SUFFIX_CUT + extension_vector
        reprojectAndCutVector(emprise_vector, vector_build, vector_build_cut, epsg, format_vector, save_results_intermediate)
        vectors_build_cut_list.append(vector_build_cut)

    vector_all_build = path_folder_base_vector + os.sep + BASE_NAME_ALL_BUILT + SUFFIX_CUT + extension_vector
    if len(vectors_build_cut_list) > 1 :
        gdfFusionVectors(vectors_build_cut_list, vector_all_build, format_vector, epsg) # version avec geopandas
    else :
        copyVectorFile(vectors_build_cut_list[0], vector_all_build, format_vector)

    # Rasterise building vector to raster building height
    rasterizeVector(vector_all_build, raster_build_height_output, file_img_ref, field="HAUTEUR")

    if debug >= 1:
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "creation of raster file containing builds width informations done to {}".format(raster_build_height_output))

    # Vecteurs Eaux #
    #---------------#
    if debug >= 1:
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "creation of files containing water width informations")

    # Filtrage SQL Eaux
    if sql_exp_water_list != None and  sql_exp_water_list != [] :
        vectors_water_filtered_list = []
        for vector_water in vector_water_area_input_list :
            vector_water_filtered = path_folder_base_vector + os.sep + os.path.splitext(os.path.basename(vector_water))[0] + SUFFIX_FILTER + extension_vector
            vectors_water_filtered_list.append(vector_water_filtered)
        filterVectorSql(vector_water_area_input_list, vectors_water_filtered_list, sql_exp_water_list, format_vector)
    else :
       vectors_water_filtered_list = vector_water_area_input_list

    # Concatenantion des fichiers surfaces en eau
    vectors_water_area_cut_list = []
    for vector_water in vectors_water_filtered_list:
        # Cut shapefiles with emprise
        vector_water_cut = path_folder_base_vector + os.sep + os.path.splitext(os.path.basename(vector_water))[0] + "_" +  str(epsg) + SUFFIX_CUT + extension_vector
        cutVectorAll(emprise_vector, vector_water, vector_water_cut, save_results_intermediate, format_vector)
        vectors_water_area_cut_list.append(vector_water_cut)

    vector_waters_area_tmp = path_folder_base_vector + os.sep + os.path.splitext(os.path.basename(vector_waters_area_output))[0] + SUFFIX_TEMP + extension_vector
    if len(vectors_water_area_cut_list) > 1 :
        gdfFusionVectors(vectors_water_area_cut_list, vector_waters_area_tmp, format_vector, epsg) # version avec geopandas
    else :
        copyVectorFile(vectors_water_area_cut_list[0], vector_waters_area_tmp, format_vector)

    # Suppression des petites surfaces et les colonnes inutiles du fichier contenant les zones en eau
    fields_name_list = getAttributeNameList(vector_waters_area_tmp, format_vector)
    addNewFieldVector(vector_waters_area_tmp, FIELD_FID, ogr.OFTInteger64, None, None, None, format_vector)
    updateIndexVector(vector_waters_area_tmp, FIELD_FID, format_vector)
    gdf_waters_area = gpd.read_file(vector_waters_area_tmp)
    for colonne in fields_name_list:
        del gdf_waters_area[colonne]

    gdf_waters_area_clean = calculateAndCleanSmallPolygonArea(gdf_waters_area, FIELD_AREA, min_area_water_area)
    gdf_waters_area_clean[FIELD_FID] = range(1, len(gdf_waters_area_clean) + 1)
    #gdf_waters_area_clean.to_file(vector_waters_area_tmp, driver=format_vector, crs="EPSG:" + str(epsg))
    gdf_waters_area_clean = gdf_waters_area_clean.set_crs(epsg=epsg, inplace=False)
    gdf_waters_area_clean.to_file(vector_waters_area_tmp, driver=format_vector)

    # Transformation image d'entrée OSO valeur 1 bandes en fichier 3 bandes rgb
    convertRaster2ImageRGB(OSO_file_output, QML_file_input, pseudoRGB_file_output, epsg, CODAGE_8BITS, no_data_value, format_raster, overwrite)

    # Création d'un fichier vecteur prés segmenté, avec les routes secondaires et primaires et voies ferrées
    input_lignes_table =  os.path.splitext(os.path.basename(vector_roads_output))[0].lower()
    input_polygons_table =  os.path.splitext(os.path.basename(emprise_vector))[0].lower()
    output_polygones_table =  os.path.splitext(os.path.basename(vector_roads_pres_seg_output))[0].lower()

    vector_roads_simple = os.path.splitext(vector_roads_output)[0] + SUFFIX_SIMPLE + os.path.splitext(vector_roads_output)[1]
    vector_roads_pres_seg_cut_tmp = os.path.splitext(vector_roads_pres_seg_output)[0] + SUFFIX_CUT + SUFFIX_TEMP + os.path.splitext(vector_roads_pres_seg_output)[1]
    vector_roads_pres_seg_clean_tmp = os.path.splitext(vector_roads_pres_seg_output)[0] + SUFFIX_CLEAN + SUFFIX_TEMP + os.path.splitext(vector_roads_pres_seg_output)[1]
    vector_networks_tmp = path_folder_base_vector + os.sep + BASE_NAME_ALL_NETWORKS + SUFFIX_CUT + extension_vector

    # Remplacer les axes à 2 voies par le squelette des routes
    simplificationRoadTwoWay(vector_roads_tmp, vector_line_skeleton_main_roads_tmp, vector_roads_simple, road_importance_field, road_importance_threshold, road_nature_field, ROAD_SHOD_THRESHOLD_LIST, extension_length_lines, epsg, format_vector, extension_vector, save_results_intermediate)

    # Ajout du reseau voie ferrée si disponible
    if vectors_railway_filtered_list :
        gdfFusionVectors([vector_line_skeleton_main_roads_tmp, vector_railway_output], vector_line_skeleton_main_roads_output, format_vector, epsg)
        gdfFusionVectors([vector_roads_simple, vector_railway_output], vector_roads_output, format_vector, epsg)
    else :
        copyVectorFile(vector_line_skeleton_main_roads_tmp, vector_line_skeleton_main_roads_output, format_vector)
        copyVectorFile(vector_roads_simple, vector_roads_output, format_vector)

    # Decouper les polygones eau avec les routes.
    cutPolygonesByLines_Postgis(vector_roads_output, vector_waters_area_tmp, vector_waters_area_output, epsg, project_encoding, server_postgis, port_number, user_postgis, password_postgis, database_postgis, schema_postgis, path_time_log="", format_vector=format_vector, save_results_intermediate=False, overwrite=True)

    # Decoupe de l'emprise par les reseaux route et ferrée
    gdf_netwoks = gpd.read_file(vector_roads_output)
    gdf_netwoks = gdf_netwoks[['geometry']]
    gdf_netwoks_clean = gdf_netwoks[(gdf_netwoks["geometry"].geom_type == 'LineString') | (gdf_netwoks["geometry"].geom_type == 'MultiLineString')]
    gdf_netwoks_clean['id'] = gdf_netwoks_clean.index
    gdf_netwoks_exploded = gdf_netwoks_clean.explode(index_parts=False).reset_index(drop=True)
    gdf_netwoks_exploded = gdf_netwoks_exploded[["id", "geometry"]]
    #gdf_netwoks_exploded.to_file(vector_networks_tmp, driver=format_vector, crs="EPSG:" + str(epsg))
    gdf_netwoks_exploded = gdf_netwoks_exploded.set_crs(epsg=epsg, inplace=False)
    gdf_netwoks_exploded.to_file(vector_networks_tmp, driver=format_vector)

    cutPolygonesByLines_Postgis(vector_networks_tmp, emprise_vector, vector_roads_pres_seg_cut_tmp, epsg, project_encoding, server_postgis, port_number, user_postgis, password_postgis, database_postgis, schema_postgis, path_time_log="", format_vector=format_vector, save_results_intermediate=False, overwrite=True)
    removeInteriorPolygons(vector_roads_pres_seg_cut_tmp, vector_roads_pres_seg_clean_tmp, epsg, format_vector)

    # Creation d'une colonne surface
    gdf_poly_seg_road = gpd.read_file(vector_roads_pres_seg_cut_tmp)
    gdf_poly_seg_road[FIELD_AREA] = gdf_poly_seg_road.geometry.area

    # Fusion des tres petits polygons (de la segmentation issue des routes)
    gdf_poly_seg_road = gdf_poly_seg_road.reset_index(drop=False)
    gdf_poly_seg_road = gdf_poly_seg_road.rename(columns={'index': FIELD_FID})
    gdf_poly_seg_road[FIELD_ORG_ID_LIST] = [[i] for i in range(100000000, 100000000 + len(gdf_poly_seg_road))]
    gdf_small_poly_merged = mergeSmallPolygons(gdf_poly_seg_road, threshold_small_area_poly=THRESHOLD_MICRO_SMALL_AREA, fid_column=FIELD_FID, org_id_list_column=FIELD_ORG_ID_LIST, area_column=FIELD_AREA)
    del gdf_small_poly_merged[FIELD_ORG_ID_LIST]
    #gdf_small_poly_merged.to_file(vector_roads_pres_seg_output, driver=format_vector, crs="EPSG:" + str(epsg))
    gdf_small_poly_merged = gdf_small_poly_merged.set_crs(epsg=epsg, inplace=False)
    gdf_small_poly_merged.to_file(vector_roads_pres_seg_output, driver=format_vector)

    # Suppression des repertoirtes temporaires
    if not save_results_intermediate :
        if os.path.isfile(emprise_vector_tmp) :
            removeVectorFile(emprise_vector_tmp)
        if os.path.isfile(vector_roads_pres_seg_cut_tmp) :
            removeVectorFile(vector_roads_pres_seg_cut_tmp)
        if os.path.isfile(vector_roads_pres_seg_clean_tmp) :
            removeVectorFile(vector_roads_pres_seg_clean_tmp)
        if os.path.isfile(vector_line_skeleton_main_roads_tmp) :
            removeVectorFile(vector_line_skeleton_main_roads_tmp)
        if os.path.isfile(vector_roads_main_tmp) :
            removeVectorFile(vector_roads_main_tmp)
        if os.path.isfile(vector_roads_main_cut) :
            removeVectorFile(vector_roads_main_cut)
        if os.path.isfile(vector_roads_secondary_output) :
            removeVectorFile(vector_roads_secondary_output)
        if os.path.isfile(vector_roads_secondary_extend) :
            removeVectorFile(vector_roads_secondary_extend)
        if os.path.isfile(vector_roads_tmp) :
            removeVectorFile(vector_roads_tmp)
        if os.path.isfile(vector_roads_simple) :
            removeVectorFile(vector_roads_simple)
        if os.path.isfile(vector_networks_tmp) :
            removeVectorFile(vector_networks_tmp)
        if os.path.isfile(vector_waters_area_tmp) :
            removeVectorFile(vector_waters_area_tmp)
        if os.path.exists(path_folder_base_vector):
            deleteDir(path_folder_base_vector)

    if debug >= 1:
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "Ending result : " + pseudoRGB_file_output)

    return

# ==================================================================================================================================================

if __name__ == '__main__':

    ##### paramètres en entrées #####
    #################################
    # Pl est recommandé de prendre un répertoire avec accès rapide en lecture et écriture pour accélérer les traitements

    # Dossier principale
    BASE_FOLDER = "/mnt/RAM_disk/INTEGRATION"

    # Fichiers vecteurs
    emprise_vector =  "/mnt/RAM_disk/INTEGRATION/emprise/Emprise_Toulouse_Metropole.shp"
    vector_water_area_input_list = ["/mnt/RAM_disk/INTEGRATION/bd_topo/N_SURFACE_EAU_BDT_031.shp"]
    vectors_road_input_list = ["/mnt/RAM_disk/INTEGRATION/bd_topo/N_ROUTE_PRIMAIRE_BDT_031.SHP",
                               "/mnt/RAM_disk/INTEGRATION/bd_topo/N_ROUTE_SECONDAIRE_BDT_031.SHP"]
    vectors_railway_input_list = ["/mnt/RAM_disk/INTEGRATION/bd_topo/N_TRONCON_VOIE_FERREE_BDT_031.SHP"]
    vectors_build_input_list = ["/mnt/RAM_disk/INTEGRATION/bd_topo/N_BATI_INDIFFERENCIE_BDT_031.shp",
                                "/mnt/RAM_disk/INTEGRATION/bd_topo/N_BATI_INDUSTRIEL_BDT_031.shp",
                                "/mnt/RAM_disk/INTEGRATION/bd_topo/N_BATI_REMARQUABLE_BDT_031.shp"]

    # Les filtres
    filter_road = [ "POS_SOL !='-1'","POS_SOL !='-1'"]
    filter_railway = ["ETAT ='NR'"]
    filter_build = ["","NATURE !='Serre'",""]
    filter_waters = ["REGIME ='Permanent'"]

    # Fichier raster
    OSO_file_input = "/mnt/RAM_disk/INTEGRATION/OCS_2023.tif"
    QML_file_input = "/mnt/RAM_disk/INTEGRATION/oso_modif.qml"

    # Fichiers resultats de sortie
    OSO_file_output = "/mnt/RAM_disk/INTEGRATION/create_data/result/OCS_2023_TlsMtp.tif"
    pseudoRGB_file_output = "/mnt/RAM_disk/INTEGRATION/create_data/result/pseudoRGB_output.tif"
    raster_build_height_output = "/mnt/RAM_disk/INTEGRATION/create_data/result/builds_height.tif"
    vector_roads_output = "/mnt/RAM_disk/INTEGRATION/create_data/result/all_roads.shp"
    vector_waters_area_output = "/mnt/RAM_disk/INTEGRATION/create_data/result/all_waters.shp"
    vector_line_skeleton_main_roads_output = "/mnt/RAM_disk/INTEGRATION/create_data/result/skeleton_primary_roads.shp"
    vector_roads_pres_seg_output = "/mnt/RAM_disk/INTEGRATION/create_data/result/pres_seg_road.shp"
    vector_roads_main_output = "/mnt/RAM_disk/INTEGRATION/create_data/result/roads_main.shp"

    #################################

    # Exec
    createDataIndicateurPseudoRGB(BASE_FOLDER,
                                  emprise_vector,
                                  OSO_file_input,
                                  QML_file_input,
                                  vectors_road_input_list,
                                  vectors_railway_input_list,
                                  vectors_build_input_list,
                                  vector_water_area_input_list,
                                  filter_road,filter_railway,filter_build,filter_waters,
                                  OSO_file_output,
                                  pseudoRGB_file_output,
                                  raster_build_height_output,
                                  vector_roads_output,
                                  vector_roads_main_output,
                                  vector_waters_area_output,
                                  vector_line_skeleton_main_roads_output,
                                  vector_roads_pres_seg_output,
                                  road_importance_field="IMPORTANCE",
                                  road_importance_threshold=4,
                                  road_importance_threshold_sup=2,
                                  road_width_field="LARGEUR",
                                  road_nature_field="NATURE",
                                  railway_nature_field="NATURE",
                                  railway_importance_values ="Principale",
                                  buffer_size_skeleton=25.0,
                                  extension_length_lines=20,
                                  min_area_water_area=30000,
                                  resolution=5,
                                  no_data_value=0,
                                  epsg=2154,
                                  server_postgis = "localhost",
                                  port_number = 5433,
                                  user_postgis = "postgres",
                                  password_postgis = "postgres",
                                  database_postgis = "cutbylines",
                                  schema_postgis = "public",
                                  project_encoding="latin1",
                                  format_raster="GTiff",
                                  format_vector='ESRI Shapefile',
                                  extension_raster=".tif",
                                  extension_vector=".shp",
                                  path_time_log="",
                                  save_results_intermediate=False,
                                  overwrite=True
                                  )
