#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT QUI FUSIONNE LES POLYGONS D'UNE SEGMENTATION MORPHOLOGIE URBAINE AFIN DE SEGMENTER LES POLYGONES A L'ECHELLE DES QUARTIERS         #
#                                                                                                                                           #
#############################################################################################################################################

"""
Nom de l'objet : PolygonsMerging.py
Description :
    Objectif : Merger les polygones entre eux les petits sans conditions et les moyens en fonction de critères compasité et resemblance de l'OCS

Date de creation : 02/10/2023
----------
Histoire :
----------
Origine : Ce script a été réalisé par Levis Antonetti dans le cadre de son stage sur la segmentation morphologique du tissu urbain (Tuteurs: Aurélien Mure, Gilles Fouvet).
          Ce script est le résultat de la synthèse du développement effectué sur des notebooks disponibles dans le répertoire /mnt/Data2/30_Stages_Encours/2023/MorphologieUrbaine_Levis/03_scripts
-----------------------------------------------------------------------------------------------------
Modifications

------------------------------------------------------
"""

##### Import #####

# system
import os, shutil, json
import warnings
# data processing
import numpy as np
import pandas as pd
from ast import literal_eval

# geomatique
import shapely
import pandas as pd
import geopandas as gpd
import topojson as tp
from shapely.geometry import Polygon, MultiPolygon, GeometryCollection, LineString, mapping, shape
from shapely.ops import unary_union
from shapely.validation import make_valid
from shapely.errors import TopologicalError

# intern libs
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC
from Lib_raster import setNodataValueImage, getPixelSizeImage, getPixelWidthXYImage, identifyPixelValues, cutImageByVector
from Lib_vector import getEmpriseVector, cutVectorAll, fusionVectors, renameFieldsVector
from Lib_vector2 import getContainmentIndex, removeRing
from Lib_file import removeFile, removeVectorFile, deleteDir
from Lib_log import timeLine
from Lib_postgis import cutPolygonesByLines_Postgis, correctTopology_Postgis
from CrossingVectorRaster import statisticsVectorRaster

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 3 : affichage maximum de commentaires lors de l'execution du script. Intermédiaire : affichage intermédiaire
debug = 2

## Constantes Generales ##
# variables fusion (= best params cf grid search)
THRESHOLD_ROAD_AREA_POLY = 2000
THRESHOLD_MEDIUM_AREA_POLY = 10000
#THRESHOLD_MEDIUM_AREA_POLY = 30000
THRESHOLD_SMALL_AREA_POLY = 1000
THRESHOLD_VERY_SMALL_AREA_POLY = 400
THRESHOLD_VERY_SMALL_WATER_POLY = 50
THRESHOLD_MICRO_SMALL_AREA = 50
THRESHOLD_NANO_SMALL_AREA = 0.0001

THRESHOLD_AREA_POLY = 40000 # 4 ha
#AREA_MAX_POLYGON = THRESHOLD_AREA_POLY * 1.5
AREA_MAX_POLYGON = 200000

THRESHOLD_EUCLIDIAN_DIST = 0.7
#THRESHOLD_EUCLIDIAN_DIST = 1.0
MAX_ADJACENT_NEIGHBOR = 4
BUILT_WEIGHT = 2
BUFF_TOLERANCE_SUPERPOSITION = 0.001

###########################################################################################################################################
#                                                                                                                                         #
# UTILS                                                                                                                                   #
#                                                                                                                                         #
###########################################################################################################################################

###########################################################################################################################################
# FUNCTION findAdjacentPolygons()                                                                                                         #
###########################################################################################################################################
def findAdjacentPolygons(gdf, target_polygon, fid_column='FID', org_id_list_column='org_id_l', buffer_tolerance=BUFF_TOLERANCE_SUPERPOSITION):
    """
    # ROLE:
    #   Recherche des polygones adjacents.
    #
    # PARAMETERS:
    #     gdf : dataframe des polygones d'entrée
    #     target_geometry : la géometrie de destination.
    #     fid_column : nom de la colonne contenant l'identifant du polygones (default : 'FID').
    #     org_id_list_column : nom de a colonne contenant la liste des valeur d'id d'origine (default : 'org_id_l').
    #     buffer_tolerance : la valeur de tolérance du buffer (default is BUFF_TOLERANCE_SUPERPOSITION).
    # RETURNS:
    #     la liste des polygones adjacents eventuel par ordre de lineaire de contact
    """

    adjacent_polygons_dico = {}

    # Create an R-tree spatial index for the GeoDataFrame
    spatial_index = gdf.sindex

    # Apply buffering to the target_geometry
    target_geometry = target_polygon['geometry'].values[0]
    buffered_target_geometry = target_polygon['geometry'].values[0].buffer(buffer_tolerance)
    org_id_l = list(target_polygon[org_id_list_column].values[0])
    fid = target_polygon[fid_column].values[0]

    # Get the indices of candidate polygons that intersect with the buffered_target_geometry
    possible_matches_index = list(spatial_index.intersection(buffered_target_geometry.bounds))
    # Check for actual adjacency by using the intersects relationship
    for idx in possible_matches_index:
        polygon = gdf.loc[idx, 'geometry']
        test_org_id_list = list(gdf.loc[idx, org_id_list_column])
        test_fid = gdf.loc[idx, fid_column]
        if (fid != gdf.loc[idx, fid_column]) and (set(test_org_id_list).isdisjoint(set(org_id_l))) and (polygon != target_geometry) and (polygon.intersects(buffered_target_geometry)) :
            intersection = polygon.intersection(buffered_target_geometry)
            if not intersection.is_empty and intersection.area > 0.00001:
                adjacent_polygons_dico[gdf.loc[idx, fid_column]] = intersection.area

    # Ordonnée les valeurs du dictionaire
    adjacent_polygons_ordo_dico = dict(sorted(adjacent_polygons_dico.items(), key=lambda item: item[1], reverse=True))
    adjacent_polygons_list = list(adjacent_polygons_ordo_dico.keys())

    return adjacent_polygons_list

###########################################################################################################################################
# FUNCTION computeMillerCompactnessIndex()                                                                                                #
###########################################################################################################################################
def computeMillerCompactnessIndex(gdf, geometry_column="geometry", compactness_col_name="i_compactness"):
    """
    # ROLE:
    #   Calculate indice de compacité polygons.
    #
    # PARAMETERS:
    #     gdf : dataframe des polygones d'entrée.
    #     geometry_column : nom de la colonne contenant la géometrie (default : "geometry").
    #     compactness_col_name : nom de a colonne contenant la compasitée calculée (default : "i_compactness").
    # RETURNS:
    #     dataframe des polygones de sortie avec la valeur de compasité
    """
    # Vérifie que le Df contient une colonne "geometry"
    if geometry_column not in gdf.columns:
        raise ValueError("Le DataFrame doit contenir une colonne {} contenant les géométries des polygones.".format(geometry_column))

    # Ajouter une nouvelle colonne pour stocker les indices de compacité
    gdf[compactness_col_name] = gdf[geometry_column].apply(lambda polygon: (4 * np.pi * polygon.area) / (polygon.length ** 2))

    return gdf

###########################################################################################################################################
# FUNCTION computeEuclidianDist()                                                                                                         #
###########################################################################################################################################
def computeEuclidianDist(row_poly, row_adj_poly, built_weight=BUILT_WEIGHT):
    """
    # ROLE:
    #   Custom le calcul de distance euclidienne en intégrant l'indicateur de compacité
    #
    # PARAMETERS:
    #     row_poly : liste des vecteur à fusionnés.
    #     row_adj_poly : le vecteur fusionné.
    #     built_weight : poids pour mieux prendre en compte les différence de hauteur de bâti
    # RETURNS:
    #     le résultat de la distance enclidienne .
    """
    # (1- compacité) pour aller dans le même sens que la distance euclidienne
    dist = np.sqrt( ((row_poly["maj_oso"].values[0] != row_adj_poly["maj_oso"])*1)**2  + (1 - row_adj_poly["stat_maj"]/100.0)**2 + ((row_poly["mean_haut"].values[0] - row_adj_poly["mean_haut"])/50)**2)  + (1 - row_adj_poly['i_compact_merged'])
    """
    print("DEBUG :")
    print("Maj = " + str((row_poly["maj_oso"].values[0] != row_adj_poly["maj_oso"])*1))
    print("Stat = " + str((row_adj_poly["stat_maj"] / 100.0)))
    print("Mean = " + str(abs(row_poly["mean_haut"].values[0] - row_adj_poly["mean_haut"]) / 50 ))
    print("Compasite = " + str((1 - row_adj_poly['i_compact_merged'])))
    print("Dist = " + str(dist))
    """
    return dist

###########################################################################################################################################
#                                                                                                                                         #
# Fusion processing polygones segmentation                                                                                                #
#                                                                                                                                         #
###########################################################################################################################################

###########################################################################################################################################
# FUNCTION computeStatisticIndiceSegmentation()                                                                                           #
###########################################################################################################################################
def computeStatisticIndiceSegmentation(path_folder_work, emprise_vector, raster_data_input, raster_build_height_input, vector_seg_stat_input, vector_seg_stat_output, no_data_value=0, epsg=2154, format_raster="GTiff", format_vector='ESRI Shapefile', extension_raster=".tif", extension_vector=".shp", path_time_log = "", save_results_intermediate=False, overwrite=True) :
    """
    # ROLE:
    #    Calcul les statistiques des indicateurs de l'image d'entrée de la segmentation, végétation, imperméabilité, routes
    #    pour les polygones issues de la segmentation et découpés par les routes
    #
    # PARAMETERS:
    #     path_folder_work : répertoire de travail local.
    #     emprise_vector : vecteur d'emprise de la zone d'étude.
    #     raster_data_input : le fichier de donnée pseudo RGB d'entrée.
    #     raster_build_height_input : fichier d'entrée rasteur hauteur des batis d'entrée.
    #     vector_seg_stat_input : le fichier vecteur d'entrée issue de la segmentation.
    #     vector_seg_stat_output : le fichier vecteur de sortie contenant toutes les statistiques par polygon.
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
    #     NA.
    """
    SUFFIX_TMP = "_tmp"
    col_to_add_list = ["count"]

    # Nettoyage du vecteur stat de sortie si il existe deja
    if os.path.isfile(vector_seg_stat_output):
        removeVectorFile(vector_seg_stat_output, format_vector)

    # Fichier vecteur temporaire
    vector_seg_stat_tmp = path_folder_work + os.sep + os.path.splitext(os.path.basename(vector_seg_stat_output))[0] + SUFFIX_TMP + extension_vector

    # Stat pour les hauteurs de bati
    class_label_dico = {}
    col_to_delete_list = ["median", "unique", "range", "min", "max", "sum", "std", "majority", "minority"]
    statisticsVectorRaster(raster_build_height_input,  vector_seg_stat_input, vector_seg_stat_tmp, 1, False, False, True, col_to_delete_list, col_to_add_list, class_label_dico, False, no_data_value, format_vector, path_time_log, save_results_intermediate, overwrite)

    # Rename columns
    fields_name_list = ["count", "mean"]
    new_fields_name_list = ["coun_haut", "mean_haut"]
    renameFieldsVector(vector_seg_stat_tmp, fields_name_list, new_fields_name_list, format_vector)

    # Stat pour les classes OSO
    class_label_dico = {}
    colonns_val_to_delete_list = []
    col_to_delete_list = ["minority", "median", "mean", "unique", "range", "min", "max", "sum", "std"]

    # Pour toutes les valeurs
    image_values_list = identifyPixelValues(raster_data_input)
    if no_data_value in image_values_list :
        del image_values_list[no_data_value]

    for id_value in image_values_list :
        class_label_dico[id_value] = str(id_value)
        col_to_delete_list.append("S_" + str(id_value))
        colonns_val_to_delete_list.append(str(id_value))

    statisticsVectorRaster(raster_data_input, vector_seg_stat_tmp, vector_seg_stat_output, 1, True, True, False, col_to_delete_list, col_to_add_list, class_label_dico, False, no_data_value, format_vector, path_time_log, save_results_intermediate, overwrite)

    # Rename columns
    fields_name_list = ["count", "majority"]
    new_fields_name_list = ["coun_oso", "maj_oso"]
    renameFieldsVector(vector_seg_stat_output, fields_name_list, new_fields_name_list, format_vector)

    # Creer une colonne stat majoritaire
    gdf_stat = gpd.read_file(vector_seg_stat_output)
    gdf_stat["stat_maj"] = gdf_stat.apply(lambda row: row[row["maj_oso"]] if pd.notnull(row["maj_oso"]) and row["maj_oso"] in gdf_stat.columns else None, axis=1)
    for colonne in colonns_val_to_delete_list:
        del gdf_stat[colonne]

    # Corriger la colonne mean_haut si NULL
    gdf_stat["mean_haut"] = gdf_stat["mean_haut"].fillna(0)

    # Nettoyer les fichiers temporaires
    if os.path.isfile(vector_seg_stat_output) :
        removeVectorFile(vector_seg_stat_output)
    if os.path.isfile(vector_seg_stat_tmp) :
        removeVectorFile(vector_seg_stat_tmp)

    # Sauvegarde du fichier stat
    gdf_stat.to_file(vector_seg_stat_output, driver=format_vector, crs="EPSG:" + str(epsg))

    return

###########################################################################################################################################
# FUNCTION mergeRoadPolygons()                                                                                                            #
###########################################################################################################################################
def mergeRoadPolygons(gdf, threshold_road_area_poly=THRESHOLD_ROAD_AREA_POLY, fid_column='FID', is_road_column='is_road', org_id_list_column='org_id_l', area_column='area', clean_ring=True):
    """
    # ROLE:
    #   Merging des polygones qui ont étaient découpés par les routes avec les polygones voisins.
    #
    # PARAMETERS:
    #     gdf : dataframe des polygones à fusionnés d'entrée.
    #     threshold_road_area_poly : seuil des surfaces des polgones de routes à fusioner (default : THRESHOLD_ROAD_AREA_POLY).
    #     fid_column : nom de la colonne contenant l'identifant du polygones (default : 'FID').
    #     is_road_column : nom de la colonne contenant l'information si le polygone d'origine etait traversé par une route (default : 'is_road').
    #     org_id_list_column : nom de a colonne contenant la liste des valeur d'id d'origine (default : 'org_id_l').
    #     area_column : nom de la colonne contenant la valeur d ela surface du polygones (default : 'area').
    #     clean_ring : nettoyage des anneaux sur les polygones (default : 'True').
    # RETURNS:
    #     dataframe des polygones routes mergés.
    """

    # Récupère les polygones routes
    gdf_road_poly = gdf[gdf[is_road_column] == "1"]

    # Sort polygons by size area
    gdf_road_small_area = gdf_road_poly[gdf_road_poly[area_column] < threshold_road_area_poly]
    gdf_road_small_area = gdf_road_small_area.sort_values(by=area_column, ascending=True)
    l_road_poly = gdf_road_small_area[fid_column].tolist()

    if debug >= 2:
        print(cyan + "mergeRoadPolygons() : " + endC +"length polygons road list:", len(gdf_road_small_area))
        print(cyan + "mergeRoadPolygons() : " + endC +"length polygons list:", len(gdf))

    # iterate over polygons
    while len(l_road_poly) > 0:

        # Get road small polygon fields
        FID_road_poly = l_road_poly.pop(0)
        row_road_poly = gdf.loc[gdf[fid_column] == FID_road_poly]
        geom_road_poly = row_road_poly["geometry"].values[0]
        area_road_poly = row_road_poly[area_column].values[0]
        is_route_road_poly = row_road_poly[is_road_column].values[0]
        orig_id_l_road_poly = row_road_poly[org_id_list_column].values[0]

        if debug >= 3:
            print(cyan + "mergeRoadPolygons() : " + endC + "FID", FID_road_poly)

        # Get adjacent polygon
        adj_fid_list = findAdjacentPolygons(gdf, row_road_poly, fid_column, org_id_list_column)

        # Case when polygon is isolated (no neighbors)
        if not adj_fid_list:
            if debug >= 2:
                print(cyan + "mergeRoadPolygons() : " + endC + "fid: %s, no adjacent polygons" %(FID_road_poly))
            continue

        adj_fid = adj_fid_list[0]
        if debug >= 2:
            print(cyan + "mergeRoadPolygons() : " + endC +"fid: %s, adjacent %s "%(FID_road_poly, adj_fid))
        gdf_adj_select_poly = gdf[gdf[fid_column].isin([adj_fid])].copy()

        # Merge polygons with every of its adjacent polygons
        merged_geometries = []
        for geom in gdf_adj_select_poly["geometry"]:
            merged_geometry = geom.union(geom_road_poly)
            merged_geometries.append(merged_geometry)
        gdf_adj_select_poly['geom_merged'] = merged_geometries
        if clean_ring :
            gdf_adj_select_poly['geom_merged'] = gdf_adj_select_poly['geom_merged'].apply(removeRing)

        # Fusionner les multi-polygons
        def handle_union(geom1, geom2):
            union_result = geom1.union(geom2)
            if isinstance(union_result, MultiPolygon):
                # Si le résultat est un MultiPolygon, calculez l'union de tous les composants et renvoyez-le
                return union_result.convex_hull  # Par exemple, on peut utiliser le plus petit polygone convexe qui contient tous les composants
            else:
                return union_result  # Sinon, retournez simplement le résultat de l'union

        # Utilisation de la fonction
        merged_geometries = []
        for geom in gdf_adj_select_poly['geometry']:
            merged_geometries.append(handle_union(geom, geom_road_poly))
        gdf_adj_select_poly['geom_merged'] = merged_geometries
        gdf_adj_select_poly = gdf_adj_select_poly[gdf_adj_select_poly['geom_merged'].apply(lambda geom: geom.geom_type in ['Polygon'])]

        if gdf_adj_select_poly.empty :
            if debug >= 1:
                print(cyan + "mergeRoadPolygons() : " + endC + "fid: %s, EMPTY_CASE" %(FID_road_poly))
            continue

        new_geom = gdf_adj_select_poly["geom_merged"].values[0]
        new_area = gdf_adj_select_poly[area_column].values[0] + area_road_poly
        new_org_id_list = gdf_adj_select_poly[org_id_list_column].values[0] + orig_id_l_road_poly
        new_org_id_list = list(set(new_org_id_list))

        # Récupère le FID du polygone merged et updates des champs de la nouvelle geometrie
        best_fid_geom = gdf_adj_select_poly[fid_column].values[0]

        # Maj fields
        idx_row_to_change = gdf.loc[gdf[fid_column] == best_fid_geom].index[0]
        gdf.at[idx_row_to_change, "geometry"] = new_geom
        gdf.at[idx_row_to_change, area_column] = new_area
        gdf.at[idx_row_to_change, org_id_list_column] = new_org_id_list
        gdf.at[idx_row_to_change, is_road_column] = is_route_road_poly

        # Remove the small polygon that have been merged
        gdf = gdf.drop(gdf.loc[gdf[fid_column] == FID_road_poly].index[0])
        gdf.reset_index(drop=True, inplace=True)

        # Add FID of merged polygon to the list of polygons if the geometry area < threshold
        if new_area <= threshold_road_area_poly and not best_fid_geom in l_road_poly :
            l_road_poly.append(best_fid_geom)
            if debug >= 3:
                print(cyan + "mergeRoadPolygons() : " + endC + 'ajout FID {} to dataframe small poly'.format(best_fid_geom))

    if debug >= 1:
        print(cyan + "mergeRoadPolygons() : " + endC +"Fin des traitements des polygones routes nouveaux polygons list:", len(gdf))
    return gdf

###########################################################################################################################################
# FUNCTION mergeSmallPolygons()                                                                                                           #
###########################################################################################################################################
def mergeSmallPolygons(gdf, threshold_small_area_poly=THRESHOLD_SMALL_AREA_POLY, fid_column='FID', org_id_list_column='org_id_l', area_column='area', clean_ring=True):
    """
    # ROLE:
    #   Merging des petits polygones à partir de seuils sur la surface du polygone.
    #
    # PARAMETERS:
    #     gdf : dataframe des polygones à fusionnés d'entrée.
    #     threshold_small_area_poly : seuil des surfaces des petits polgones (default : THRESHOLD_SMALL_AREA_POLY).
    #     fid_column : nom de la colonne contenant l'identifant du polygones (default : 'FID').
    #     org_id_list_column : nom de a colonne contenant la liste des valeur d'id d'origine (default : 'org_id_l').
    #     area_column : nom de la colonne contenant la valeur d ela surface du polygones (default : 'area').
    #     clean_ring : nettoyage des anneaux sur les polygones (default : 'True').
    # RETURNS:
    #     dataframe des petis polygones mergés.
    """

    # Récupère les petits polygones en fonction d'un seuil
    gdf['geometry'] = gdf['geometry'].buffer(0)
    gdf_small_area = gdf[gdf[area_column] < threshold_small_area_poly]
    gdf_small_area = gdf_small_area.sort_values(by=area_column, ascending=True)

    if debug >= 1:
        print(cyan + "mergeSmallPolygons() : " + endC +"length small polygon list:", len(gdf_small_area))
        print(cyan + "mergeSmallPolygons() : " + endC +"length polygons list:", len(gdf))

    # List of small polygons FID
    l_small_poly = gdf_small_area[fid_column].tolist()

    # Iterate over small polygons
    while len(l_small_poly) > 0:

        # Get small polygon fields
        FID_small_poly = l_small_poly.pop(0)
        row_small_poly = gdf.loc[gdf[fid_column] == FID_small_poly]
        geom_small_poly = row_small_poly["geometry"].values[0]
        area_small_poly = row_small_poly[area_column].values[0]
        orig_id_l_small_poly = row_small_poly[org_id_list_column].values[0]

        # Get adjacent polygons
        adj_fid_list = findAdjacentPolygons(gdf, row_small_poly, fid_column, org_id_list_column)

        # Case when polygon is isolated (no neighbors)
        if not adj_fid_list:
            if debug >= 2:
                print(cyan + "mergeSmallPolygons() : " + endC + "fid: %s, no adjacent polygons" %(FID_small_poly))
            continue

        adj_fid = adj_fid_list[0]
        if debug >= 3:
            print(cyan + "mergeSmallPolygons() : " + endC + "fid: %s, adjacent %s "%(FID_small_poly, adj_fid))
        gdf_adj_select_poly = gdf[gdf[fid_column].isin([adj_fid])].copy()

        # Merge polygons with every of its adjacent polygons
        gdf_adj_select_poly = gdf_adj_select_poly.copy()
        merged_geometries = []
        for geom in gdf_adj_select_poly["geometry"]:
            merged_geometry = geom.union(geom_small_poly)
            merged_geometries.append(merged_geometry)
        gdf_adj_select_poly['geom_merged'] = merged_geometries
        if clean_ring :
            gdf_adj_select_poly['geom_merged'] = gdf_adj_select_poly['geom_merged'].apply(removeRing)

        # Fusionner les multi-polygons (ne marche pas!!)
        gdf_adj_select_poly = gdf_adj_select_poly[gdf_adj_select_poly['geom_merged'].apply(lambda geom: geom.geom_type in ['Polygon','MultiPolygon'])]

        if gdf_adj_select_poly.empty :
            if debug >= 1:
                print(cyan + "mergeSmallPolygons() : " + endC + "fid: %s, EMPTY_CASE" %(FID_small_poly))
            continue

        new_geom = gdf_adj_select_poly["geom_merged"].values[0]
        new_area = gdf_adj_select_poly[area_column].values[0] + area_small_poly
        new_org_id_list = gdf_adj_select_poly[org_id_list_column].values[0] + orig_id_l_small_poly
        new_org_id_list = list(set(new_org_id_list))

        # Récupère le FID du polygone merged et updates des champs de la nouvelle geometrie
        best_fid_geom = gdf_adj_select_poly[fid_column].values[0]

        # Maj fields
        idx_row_to_change = gdf.loc[gdf[fid_column] == best_fid_geom].index[0]
        gdf.at[idx_row_to_change, "geometry"] = new_geom
        gdf.at[idx_row_to_change, area_column] = new_area
        gdf.at[idx_row_to_change, org_id_list_column] = new_org_id_list

        # Remove the small polygon that have been merged
        gdf = gdf.drop(gdf.loc[gdf[fid_column] == FID_small_poly].index[0])
        gdf.reset_index(drop=True, inplace=True)

        # Add FID of merged polygon to the list of polygons if the geometry area < threshold
        if new_area <= threshold_small_area_poly and not best_fid_geom in l_small_poly :
            l_small_poly.append(best_fid_geom)
            if debug >= 1:
                print(cyan + "mergeSmallPolygons() : " + endC + 'ajout FID {} to dataframe small poly'.format(best_fid_geom))

    if debug >= 1:
        print(cyan + "mergeSmallPolygons() : " + endC +"Fin des traitements des petits polygones nouveaux polygons list:", len(gdf))

    return gdf

###########################################################################################################################################
# FUNCTION mergePolygonsWithConds()                                                                                                       #
###########################################################################################################################################
def mergePolygonsWithConds(gdf, threshold_medium_area_poly=THRESHOLD_MEDIUM_AREA_POLY, threshold_area_poly=THRESHOLD_AREA_POLY, area_max_poly=AREA_MAX_POLYGON, threshold_euclidian_dist=THRESHOLD_EUCLIDIAN_DIST, max_adjacent_neighbor=MAX_ADJACENT_NEIGHBOR, fid_column='FID', org_id_list_column='org_id_l', area_column='area'):
    """
    # ROLE:
    #   Récupération en entrée de 3 Tresholds de surface : Medium, LCZ et Max area.
    #   LCZ représente la taille convenable de polygone (200m x 200m).
    #   Medium représente le seuil de taille intermédiaire et Max area une taille plafond au delà de laquelle la fusion n'est plus faite.
    #
    # PARAMETERS:
    #     gdf : dataframe des polygones à fusionnés d'entrée.
    #     threshold_medium_area_poly : seuil des surfaces des polgones moyens (default :THRESHOLD_MEDIUM_AREA_POLY).
    #     threshold_area_poly : seuil de surface des polygones (default : THRESHOLD_AREA_POLY).
    #     area_max_poly : surface max des polygones (default : AREA_MAX_POLYGON).
    #     threshold_euclidian_dist : seuil de la distance euclidien (default : THRESHOLD_EUCLIDIAN_DIST)
    #     max_adjacent_neighbor : maximun de polygones voisin étudiés (default : MAX_ADJACENT_NEIGHBOR)
    #     fid_column : nom de la colonne contenant l'identifant du polygones (default : 'FID').
    #     org_id_list_column : nom de a colonne contenant la liste des valeur d'id d'origine (default : 'org_id_l').
    #     area_column : nom de la colonne contenant la valeur de la surface du polygones (default : 'area').
    # RETURNS:
    #     datafame des polygones fusionnés.
    """
    # Constantes

    # Calcul surface polygons
    gdf[area_column] = gdf.geometry.area
    # Récupère les petits polygones en fonction d'un seuil
    gdf_poly = gdf[gdf[area_column] <= threshold_area_poly]

    if debug >= 1:
        print(cyan + "mergePolygonsWithConds() : " + endC + "length polygons medium list:", len(gdf_poly))
        print(cyan + "mergePolygonsWithConds() : " + endC + "length polygons list:", len(gdf))

    # Sort polygons by size
    gdf_poly = gdf_poly.sort_values(by=area_column, ascending=True)
    l_poly = gdf_poly[fid_column].tolist()

    # Iterate over polygons
    while len(l_poly) > 0:

        # Get polygon fields
        FID_poly = l_poly.pop(0)
        if debug >= 3:
            print(cyan + "mergePolygonsWithConds() : " + endC +"FID", FID_poly)

        row_medium_poly = gdf.loc[gdf[fid_column] == FID_poly]

        geom_poly = row_medium_poly["geometry"].values[0]
        area_poly = row_medium_poly[area_column].values[0]
        mean_haut_poly = row_medium_poly["mean_haut"].values[0]
        orig_id_l_poly = row_medium_poly[org_id_list_column].values[0]

        # Get Adjacent Polygons
        adj_fid_list = findAdjacentPolygons(gdf, row_medium_poly, fid_column, org_id_list_column)

        # Case when polygon is isolated (no neighbors)
        if not adj_fid_list:
            if debug >= 2:
                print(cyan + "mergePolygonsWithConds() : " + endC + "fid: %s, no adjacent polygons" %(FID_poly))
            continue

        adj_fid_list = adj_fid_list[:max_adjacent_neighbor]
        gdf_adj_poly = gdf[gdf[fid_column].isin(adj_fid_list)].copy()

        # Merge polygons with every of its adjacent polygons
        merged_geometries = []
        for geom in gdf_adj_poly["geometry"]:
            merged_geometry = geom.union(geom_poly)
            merged_geometries.append(merged_geometry)
        gdf_adj_poly['geom_merged'] = merged_geometries

        # Eliminate merged geometries where intersection is defined only by a point
        gdf_adj_poly = gdf_adj_poly[gdf_adj_poly['geom_merged'].apply(lambda geom: geom.geom_type == 'Polygon')]

        if gdf_adj_poly.empty:
            if debug >= 1:
                print(cyan + "mergePolygonsWithConds() : " + endC + "fid: %s, EMPTY_CASE" %(FID_poly))
            continue

        # Compute euclidian distance, compactness index, areas of merged geometries
        gdf_adj_poly = computeMillerCompactnessIndex(gdf_adj_poly, geometry_column="geom_merged", compactness_col_name="i_compact_merged")
        gdf_adj_poly['area_merged'] = gdf_adj_poly["geom_merged"].apply(lambda x: x.area)
        gdf_adj_poly['dist_eucl'] = gdf_adj_poly.apply(lambda x: computeEuclidianDist(row_medium_poly, x, BUILT_WEIGHT), axis=1)
        if debug >= 3:
            print(cyan + "mergePolygonsWithConds() : " + endC + str(gdf_adj_poly['dist_eucl'].values[0]))

        # Medium polygons
        if area_poly <= threshold_medium_area_poly :
            # Case when polygon have medium size
            if debug >= 3:
                print(cyan + "mergePolygonsWithConds() : " + endC + "Case1 when polygon have medium size")

            # Distance euclidienne avec le polygone et tous ses voisins
            # Vérification supplémentaire avant d'accéder à fid_best_dist_eucl
            if not gdf_adj_poly.empty:
                list_best_dist_eucl_candidates = gdf_adj_poly[gdf_adj_poly['dist_eucl'] == gdf_adj_poly['dist_eucl'].min()]

                # Vérifiez si les candidats ne sont pas vides avant de continuer
                if not list_best_dist_eucl_candidates.empty:
                    fid_best_dist_eucl = list_best_dist_eucl_candidates[fid_column].values[0]
                    if debug >= 3:
                        print(cyan + "mergePolygonsWithConds() : " + endC + "FID best dist eucl:", fid_best_dist_eucl)
                    gdf_adj_poly = gdf_adj_poly[gdf_adj_poly[fid_column] == fid_best_dist_eucl]
                else:
                    if debug >= 3:
                        print(cyan + "mergePolygonsWithConds() : " + endC + "No valid candidate for best euclidian distance.")
                    continue
            else:
                if debug >= 3:
                    print(cyan + "mergePolygonsWithConds() : " + endC + "No adjacent polygons satisfy conditions.")
                continue
        # Big polygons
        elif threshold_medium_area_poly<= area_poly <= threshold_area_poly :
            if debug >= 3:
                print(cyan + "mergePolygonsWithConds() : " + endC + "Case2 Big polygons")

            # On ne dépasse pas la surface maximale de polygone lors du merging
            gdf_adj_poly = gdf_adj_poly[gdf_adj_poly['area_merged'] <= area_max_poly]

            # Distance euclidienne avec le polygone et tous ses voisins (cette distance inclue la compacité)
            gdf_adj_poly_sup_euclidienne =  gdf_adj_poly[gdf_adj_poly['dist_eucl'] < threshold_euclidian_dist]
            if not gdf_adj_poly_sup_euclidienne.empty:
                list_best_dist_eucl_candidates = gdf_adj_poly_sup_euclidienne[gdf_adj_poly_sup_euclidienne['dist_eucl'] == gdf_adj_poly_sup_euclidienne['dist_eucl'].min()]
                # Vérifiez si les candidats ne sont pas vides avant de continuer
                if not list_best_dist_eucl_candidates.empty:
                    fid_best_dist_eucl = list_best_dist_eucl_candidates[fid_column].values[0]
                    if debug >= 3:
                        print(cyan + "mergePolygonsWithConds() : " + endC + "FID best dist eucl:", fid_best_dist_eucl)
                    gdf_adj_poly = gdf_adj_poly[gdf_adj_poly[fid_column] == fid_best_dist_eucl]
                else:
                    if debug >= 3:
                        print(cyan + "mergePolygonsWithConds() : " + endC + "No valid candidate for best euclidian distance.")
                    continue
            else:
                if debug >= 3:
                    print(cyan + "mergePolygonsWithConds() : " + endC + "No adjacent polygons satisfy conditions.")
                continue
            if debug >= 3:
                print(cyan + "mergePolygonsWithConds() : " + endC + "FID best dist eucl:", fid_best_dist_eucl)
            gdf_adj_poly = gdf_adj_poly[gdf_adj_poly[fid_column] == fid_best_dist_eucl]

        # Others polygons
        # Ne pas merge si la surface est trop grande
        else:
            if debug >= 3:
                print(cyan + "mergePolygonsWithConds() : " + endC + "Case3 very Big polygons non fusioné")
            continue

        # Récupère le FID du polygone merged avec le meilleur indice de compacité après merging et màj des champs de la nouvelle geometrie
        # Besoin de calculer un nouvel indicateur qui sera plus ou moins une pondération entre la distance euclidienne et (1-compacité). Le seuil sera à définir.
        new_geom = gdf_adj_poly["geom_merged"].values[0]
        new_mean_haut = (gdf_adj_poly["mean_haut"].values[0]  + mean_haut_poly) / 2
        new_org_id_list = gdf_adj_poly[org_id_list_column].values[0] + orig_id_l_poly
        new_org_id_list = list(set(new_org_id_list))

        # Maj fields
        idx_row_to_change = gdf.loc[gdf[fid_column] == fid_best_dist_eucl].index[0]
        gdf.at[idx_row_to_change, "geometry"] = new_geom
        gdf.at[idx_row_to_change, "mean_haut"] = new_mean_haut
        gdf.at[idx_row_to_change, area_column] = new_geom.area
        gdf.at[idx_row_to_change, org_id_list_column] = new_org_id_list

        # Remove the polygon that have been merged
        gdf = gdf.drop(gdf.loc[gdf[fid_column] == FID_poly].index[0])
        gdf.reset_index(drop=True, inplace=True)

        # Add FID of merged polygon to the list of polygons if the geometry area < threshold
        if new_geom.area <= threshold_area_poly and not fid_best_dist_eucl in l_poly:
            l_poly.append(fid_best_dist_eucl)
            if debug >= 2:
                print(cyan + "mergePolygonsWithConds() : " + endC + 'ajout FID {} to dataframe medium poly'.format(fid_best_dist_eucl))

    if debug >= 1:
        print(cyan + "mergePolygonsWithConds() : " + endC +"Fin des traitements des polygones moyens nouveaux polygons list: ", len(gdf))
    return gdf

###########################################################################################################################################
# FUNCTION cleanPolygons()                                                                                                                #
###########################################################################################################################################
def cleanPolygons(gdf_poly_in, threshold_small_area_poly=THRESHOLD_VERY_SMALL_AREA_POLY, fid_column='FID', org_id_list_column='org_id_l', area_column='area', clean_ring=True):
    """
    # ROLE:
    #   Nettoyage des geometries de polygones problème topologique et fusion des très petits polygones.
    #
    # PARAMETERS:
    #     gdf_poly_in : dataframe des polygones à nettoyer d'entrée.
    #     threshold_small_area_poly : tail en surface des petits polyones à fusionnés (default : THRESHOLD_VERY_SMALL_AREA_POLY).
    #     fid_column : nom de la colonne contenant l'identifant du polygones (default : 'FID').
    #     org_id_list_column : nom de a colonne contenant la liste des valeur d'id d'origine (default : 'org_id_l').
    #     area_column : nom de la colonne contenant la valeur de la surface du polygones (default : 'area').
    #     clean_ring : nettoyage des anneaux sur les polygones (default : 'True').
    # RETURNS:
    #     dataframe des polygones de sortie nettoyés.
    """
    if debug >= 1:
        print(cyan + "cleanPolygons() : " + endC + "length polygons to clean:", len(gdf_poly_in))


    # Nettoyage des geometries dans les polygones
    if clean_ring :
        gdf_poly_in['geometry'] = gdf_poly_in['geometry'].apply(removeRing)
    gdf_cond_poly_merged_explode = gdf_poly_in.explode(index_parts=True)
    gdf_cond_poly_merged_explode['geometry'] = gdf_cond_poly_merged_explode.buffer(distance=0.00002)
    gdf_seg_output = gdf_cond_poly_merged_explode[(gdf_cond_poly_merged_explode["geometry"].geom_type == 'Polygon') | (gdf_cond_poly_merged_explode["geometry"].geom_type == 'MultiPolygon')]

    # Initialiser une liste pour stocker les nouvelles géométries
    new_geometries = []
    # Parcourir chaque géométrie du GeoDataFrame
    for geom in gdf_seg_output.geometry:
        # Rendre la géométrie valide si elle ne l'est pas déjà
        valid_geom = make_valid(geom)

        if isinstance(geom, MultiPolygon):
            # Fusionner les multipolygones en un seul polygone
            merged_geom = unary_union(geom)
            new_geometries.append(merged_geom)
        else:
            # Garder les polygones simples inchangés
            new_geometries.append(geom)

    # Créer un nouveau GeoDataFrame avec les géométries traitées
    gdf_seg_output_fusion = gpd.GeoDataFrame(geometry=new_geometries, crs=gdf_seg_output.crs)

    # Fusion des tres petits polygons
    gdf_seg_output_fusion[fid_column] = range(1, len(gdf_seg_output_fusion) + 1)
    gdf_seg_output_fusion[area_column] = gdf_seg_output_fusion.geometry.area
    gdf_seg_output_fusion[org_id_list_column] = [[i] for i in range(100000000, 100000000 + len(gdf_seg_output_fusion))]
    gdf_poly_out = mergeSmallPolygons(gdf_seg_output_fusion, threshold_small_area_poly, fid_column=fid_column, org_id_list_column=org_id_list_column, area_column=area_column, clean_ring=clean_ring)
    gdf_poly_out[area_column] = gdf_poly_out.geometry.area

    # Supprimer les colonnes inutiles
    del gdf_poly_out[org_id_list_column]

    if debug >= 1:
        print(cyan + "cleanPolygons() : " + endC +"Fin du nettoyage des polygones : ", len(gdf_poly_out))
    return gdf_poly_out

###########################################################################################################################################
# FUNCTION segPolygonsMerging()                                                                                                           #
###########################################################################################################################################
def segPolygonsMerging(path_base_folder,  emprise_vector, raster_data_input, raster_build_height_input, vector_roads_input, vector_roads_main_input, vector_seg_input, vector_seg_output, no_data_value=0, epsg=2154,server_postgis="localhost", port_number=5432, project_encoding = "latin1", user_postgis="postgres", password_postgis="postgres", database_postgis="correctionTopo", schema_postgis="public",  format_raster="GTiff", format_vector='ESRI Shapefile', extension_raster=".tif", extension_vector=".shp", path_time_log = "", save_results_intermediate=False, overwrite=True):
    """
    # ROLE:
    #     Fusion des polygones de la segmentation.
    #
    # PARAMETERS:
    #     path_base_folder : le dossier de travail.
    #     emprise_vector : fichier d'emprise.
    #     raster_data_input : le fichier de donnée pseudo RGB d'entrée.
    #     raster_build_height_input : fichier d'entrée rasteur des hauteurs de batis.
    #     vector_roads_input : le fichier vecteur des routes d'entrée.
    #     vector_roads_main_input : le fichier vecteur des routes principales d'entrée bufferisées (polygones).
    #     vector_seg_input : le fichier vecteur de segmentation d'entrée.
    #     vector_seg_output : le fichier vecteur de segmentation avec les polygones fusionnés en sortie
    #     no_data_value : Option : Value pixel of no data (par défaut : 0).
    #     epsg (int): EPSG code of the desired projection (default is 2154).
    #     project_encoding : encodage des fichiers d'entrés.
    #     server_postgis : nom du serveur postgis.
    #     port_number : numéro du port pour le serveur postgis.
    #     user_postgis : le nom de l'utilisateurs postgis.
    #     password_postgis : le mot de passe de l'utilisateur postgis.
    #     database_postgis : le nom de la base postgis à utiliser.
    #     schema_postgis : le nom du schéma à utiliser.
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
        print(bold + green + "Variables dans le segPolygonsMerging - Variables générales" + endC)
        print(cyan + "segPolygonsMerging() : " + endC + "path_base_folder : " + str(path_base_folder))
        print(cyan + "segPolygonsMerging() : " + endC + "emprise_vector : " + str(emprise_vector))
        print(cyan + "segPolygonsMerging() : " + endC + "raster_data_input : " + str(raster_data_input))
        print(cyan + "segPolygonsMerging() : " + endC + "raster_build_height_input : " + str(raster_build_height_input))
        print(cyan + "segPolygonsMerging() : " + endC + "vector_roads_input : " + str(vector_roads_input))
        print(cyan + "segPolygonsMerging() : " + endC + "vector_roads_main_input : " + str(vector_roads_main_input))
        print(cyan + "segPolygonsMerging() : " + endC + "vector_seg_input : " + str(vector_seg_input))
        print(cyan + "segPolygonsMerging() : " + endC + "vector_seg_output : " + str(vector_seg_output))
        print(cyan + "segPolygonsMerging() : " + endC + "no_data_value : " + str(no_data_value))
        print(cyan + "segPolygonsMerging() : " + endC + "epsg : " + str(epsg))
        print(cyan + "segPolygonsMerging() : " + endC + "project_encoding : " + str(project_encoding))
        print(cyan + "segPolygonsMerging() : " + endC + "server_postgis : " + str(server_postgis) + endC)
        print(cyan + "segPolygonsMerging() : " + endC + "port_number : " + str(port_number) + endC)
        print(cyan + "segPolygonsMerging() : " + endC + "user_postgis : " + str(user_postgis) + endC)
        print(cyan + "segPolygonsMerging() : " + endC + "password_postgis : " + str(password_postgis) + endC)
        print(cyan + "segPolygonsMerging() : " + endC + "database_postgis : " + str(database_postgis) + endC)
        print(cyan + "segPolygonsMerging() : " + endC + "schema_postgis : " + str(schema_postgis) + endC)
        print(cyan + "segPolygonsMerging() : " + endC + "format_raster : " + str(format_raster))
        print(cyan + "segPolygonsMerging() : " + endC + "format_vector : " + str(format_vector))
        print(cyan + "segPolygonsMerging() : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "segPolygonsMerging() : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "segPolygonsMerging() : " + endC + "path_time_log : " + str(path_time_log))
        print(cyan + "segPolygonsMerging() : " + endC + "save_results_intermediate : "+ str(save_results_intermediate))
        print(cyan + "segPolygonsMerging() : " + endC + "overwrite : "+ str(overwrite))

    # Fonction pour convertir une chaîne de caractères en liste de nombres
    def convert_to_list(value):
        try:
            # Vérifie si la valeur est une chaîne non vide
            if isinstance(value, str) and value.strip():
                return list(map(int, value.split(',')))
            else:
                return []  # Retourne une liste vide si la valeur est vide ou non valide
        except ValueError:
            return []  # Retourne une liste vide si une erreur de conversion se produit

    # Les constantes
    FIELD_FID = "FID"
    FIELD_IS_ROAD = "is_road"
    FIELD_ORG_ID = "org_id"
    FIELD_ORG_ID_LIST = "org_id_l"
    FIELD_AREA = "area"

    SUFFIX_STAT_IN = "_stat_in"
    SUFFIX_STAT_OUT = "_stat_out"
    SUFFIX_TEMP = "_temp"
    SUFFIX_CUT = "_cut"
    SUFFIX_WATER = "_water"

    FOLDER_FUSION = "seg_res_fusion"
    FOLDER_STAT = "stat"
    FOLDER_TMP = "tmp"

    # Creation des répertoires
    path_folder_fusion = path_base_folder + os.sep + FOLDER_FUSION
    if not os.path.exists(path_folder_fusion):
        os.makedirs(path_folder_fusion)

    path_folder_stat = path_folder_fusion + os.sep + FOLDER_STAT
    if not os.path.exists(path_folder_stat):
        os.makedirs(path_folder_stat)

    path_folder_val_tmp = path_folder_fusion + os.sep + FOLDER_TMP
    if not os.path.exists(path_folder_val_tmp):
        os.makedirs(path_folder_val_tmp)

    path_folder_seg_output = os.path.dirname(vector_seg_output)
    if not os.path.exists(path_folder_seg_output):
        os.makedirs(path_folder_seg_output)

    # Récupération  input data
    gdf_seg = gpd.read_file(vector_seg_input)
    gdf_seg = gdf_seg[[FIELD_FID, FIELD_IS_ROAD, FIELD_ORG_ID,'geometry',FIELD_AREA]]
    # Correction des géométries invalides (très important pour éviter les TopologyException)
    gdf_seg["geometry"] = gdf_seg["geometry"].buffer(0)
    #gdf_seg = gdf_seg.explode(index_parts=False).reset_index(drop=True)
    gdf_seg[FIELD_AREA] = gdf_seg.geometry.area

    # Passer org_id sous forme de liste org_id_l
    gdf_seg[FIELD_ORG_ID_LIST] = gdf_seg[FIELD_ORG_ID].apply(convert_to_list)

    # Fusion des polygons bords de routes
    gdf_poly_road_merged = mergeRoadPolygons(gdf_seg, threshold_road_area_poly=THRESHOLD_ROAD_AREA_POLY, fid_column=FIELD_FID, is_road_column=FIELD_IS_ROAD, org_id_list_column=FIELD_ORG_ID_LIST, area_column=FIELD_AREA, clean_ring=True)
    gdf_poly_road_merged[FIELD_AREA] = gdf_poly_road_merged.geometry.area

    # Fusion petits polygons
    gdf_small_poly_merged = mergeSmallPolygons(gdf_poly_road_merged, threshold_small_area_poly=THRESHOLD_VERY_SMALL_AREA_POLY, fid_column=FIELD_FID, org_id_list_column=FIELD_ORG_ID_LIST, area_column=FIELD_AREA, clean_ring=True)
    gdf_small_poly_merged[FIELD_AREA] = gdf_small_poly_merged.geometry.area

    # Supprimer les géométries vides (None ou NaN)
    gdf_small_poly_merged = gdf_small_poly_merged.dropna(subset=["geometry"])
    gdf_small_poly_merged[FIELD_ORG_ID_LIST] = gdf_small_poly_merged[FIELD_ORG_ID_LIST].apply(str)
    vector_seg_stat_input = path_folder_stat + os.sep + os.path.splitext(os.path.basename(vector_seg_input))[0] + SUFFIX_STAT_IN + extension_vector
    gdf_small_poly_merged.to_file(vector_seg_stat_input, driver=format_vector, crs="EPSG:" + str(epsg))

    # Calcul des statistiques des indicateurs de l'image d'entrée de la segmentation, végétation, imperméabilité, routes.
    vector_seg_stat_output = path_folder_stat + os.sep + os.path.splitext(os.path.basename(vector_seg_input))[0] + SUFFIX_STAT_OUT + extension_vector
    computeStatisticIndiceSegmentation(path_folder_val_tmp, emprise_vector, raster_data_input, raster_build_height_input, vector_seg_stat_input, vector_seg_stat_output, no_data_value, epsg, format_raster, format_vector, extension_raster, extension_vector, path_time_log, save_results_intermediate, overwrite)
    if debug >= 1:
        print(bold + green + "Calculs des statistiques Ok" + endC)
        print(cyan + "segPolygonsMerging() : " + endC + "Fichier de stat => vector_seg_stat_output : " + str(vector_seg_stat_output))
    print(vector_seg_stat_output)

    # Fusion de polygons moyens et grand avec critères sur les statistiques
    gdf_seg_stat = gpd.read_file(vector_seg_stat_output)
    gdf_seg_stat = gdf_seg_stat[[FIELD_FID, FIELD_IS_ROAD, FIELD_ORG_ID, FIELD_ORG_ID_LIST, FIELD_AREA, 'coun_oso', 'maj_oso', 'stat_maj', 'coun_haut', 'mean_haut', 'geometry']]
    gdf_seg_stat[FIELD_ORG_ID_LIST] = gdf_seg_stat[FIELD_ORG_ID_LIST].apply(lambda x: x + "]" if "[" in x and "]" not in x else x)
    gdf_seg_stat[FIELD_ORG_ID_LIST] = gdf_seg_stat[FIELD_ORG_ID_LIST].apply(literal_eval)

    # Correction geometry invalide
    gdf_seg_stat['geometry'] = gdf_seg_stat['geometry'].apply(lambda geom: geom.buffer(0) if not geom.is_valid else geom)

    # Fusion des polygones
    gdf_cond_poly_merged = mergePolygonsWithConds(gdf_seg_stat, threshold_medium_area_poly=THRESHOLD_MEDIUM_AREA_POLY, threshold_area_poly=THRESHOLD_AREA_POLY, area_max_poly=AREA_MAX_POLYGON, threshold_euclidian_dist=THRESHOLD_EUCLIDIAN_DIST, max_adjacent_neighbor=MAX_ADJACENT_NEIGHBOR, fid_column=FIELD_FID, org_id_list_column=FIELD_ORG_ID_LIST, area_column=FIELD_AREA)
    gdf_cond_poly_merged[FIELD_AREA] = gdf_cond_poly_merged.geometry.area

    # Supprimer les polygones interieurs
    if debug >=2:
        print(cyan + "removeInteriorPolygons() : " + bold + green + "Supression des polyones interieurs du fichier vecteur : " + endC)
        starting_event = "removeInteriorPolygons() : starting : "
        timeLine("", starting_event)

    gdf_cond_poly_merged_clean = getContainmentIndex(gdf_cond_poly_merged)
    gdf_cond_poly_merged = gdf_cond_poly_merged_clean.dissolve(by='contain_idx', as_index=False)

    if debug >=2:
        print(cyan + "removeInteriorPolygons() : " + bold + green + "Fin du traitement supression des polyones interieurs, résultat : " + endC )
        ending_event = "removeInteriorPolygons() : Ending : "
        timeLine("", ending_event)

    # Supprimer les colonnes
    colonnsToDel = ['coun_oso', 'maj_oso', 'stat_maj', 'coun_haut', 'mean_haut', 'contain_idx']
    for colonne in colonnsToDel:
        del gdf_cond_poly_merged[colonne]

    # Nettoyage des geometries dans les polygones
    gdf_seg_output_fusion_clean = mergeSmallPolygons(gdf_cond_poly_merged, threshold_small_area_poly=THRESHOLD_SMALL_AREA_POLY, fid_column=FIELD_FID, org_id_list_column=FIELD_ORG_ID_LIST, area_column=FIELD_AREA, clean_ring=True)
    gdf_seg_output_fusion_clean[FIELD_AREA] = gdf_seg_output_fusion_clean.geometry.area
    gdf_emprise = gpd.read_file(emprise_vector)
    gdf_emprise["geometry"] = gdf_emprise.geometry.buffer(0)
    gdf_seg_output_fusion_clean = gpd.clip(gdf_seg_output_fusion_clean, gdf_emprise.unary_union)

    # Supprimer les colonnes
    colonnsToDel = [ FIELD_IS_ROAD, FIELD_ORG_ID, FIELD_ORG_ID_LIST, FIELD_AREA]
    for colonne in colonnsToDel:
        del gdf_cond_poly_merged[colonne]

    # Désactiver les warnings
    warnings.filterwarnings("ignore", category=FutureWarning, module="geopandas")
    warnings.filterwarnings("ignore", category=RuntimeWarning, module="shapely")

    # Rajouter les polygones eau
    gdf_seg_masked = gdf_seg_output_fusion_clean.dissolve()

    # Decouper puis convertir GeoSeries en GeoDataFrame
    def extract_polygons(geom):
        if geom.geom_type == "GeometryCollection":
            return [g for g in geom.geoms if isinstance(g, (Polygon, MultiPolygon))]
        elif isinstance(geom, (Polygon, MultiPolygon)):
            return [geom]
        else:
            return []
    # Appliquer la fonction et reconstruire un GeoDataFrame propre
    all_polygons = []
    for geom in gdf_seg_masked.geometry:
        all_polygons.extend(extract_polygons(geom))
    gdf_seg_masked = gpd.GeoDataFrame(geometry=all_polygons, crs=gdf_seg_masked.crs)
    gdf_seg_masked[(gdf_seg_masked["geometry"].geom_type == 'Polygon') | (gdf_seg_masked["geometry"].geom_type == 'MultiPolygon')]
    gdf_seg_masked['geometry'] = gdf_seg_masked['geometry'].apply(lambda geom: geom.buffer(0) if not geom.is_valid else geom)
    gdf_seg_water = gdf_emprise.geometry.difference(gdf_seg_masked.unary_union)
    gdf_seg_water = gpd.GeoDataFrame(geometry=gdf_seg_water)
    gdf_seg_water.crs = gdf_emprise.crs
    gdf_seg_water = gdf_seg_water.explode(index_parts=False)
    gdf_seg_water = gdf_seg_water.reset_index(drop=True)
    vector_water_temp = path_folder_val_tmp + os.sep + os.path.basename(os.path.splitext(vector_seg_output)[0]) + SUFFIX_WATER + SUFFIX_TEMP + extension_vector
    vector_water_temp_cut = path_folder_val_tmp + os.sep + os.path.basename(os.path.splitext(vector_seg_output)[0]) + SUFFIX_WATER + SUFFIX_TEMP + SUFFIX_CUT + extension_vector
    gdf_seg_water.to_file(vector_water_temp, driver=format_vector, crs="EPSG:" + str(epsg))
    renameFieldsVector(vector_water_temp, ["FID"], ["id"], format_vector)

    # Decouper les polygones eau avec les routes.
    cutPolygonesByLines_Postgis(vector_roads_input, vector_water_temp, vector_water_temp_cut, epsg, project_encoding, server_postgis, port_number, user_postgis, password_postgis, database_postgis, schema_postgis, path_time_log="", format_vector=format_vector, save_results_intermediate=False, overwrite=True)
    gdf_seg_water_cut_road = gpd.read_file(vector_water_temp_cut)

    # Nettoyer les polygones eau
    gdf_seg_water_cut_road = gdf_seg_water_cut_road[["geometry"]]
    gdf_seg_water_cut_road[FIELD_AREA] = gdf_seg_water_cut_road.geometry.area
    gdf_seg_water_cut_road[FIELD_FID] = range(1000000, len(gdf_seg_water_cut_road) + 1000000)
    gdf_seg_water_cut_road_clean = cleanPolygons(gdf_seg_water_cut_road, THRESHOLD_VERY_SMALL_WATER_POLY, FIELD_FID, FIELD_ORG_ID_LIST, FIELD_AREA, clean_ring=False)

    # Corriger les géométries invalides
    gdf_seg_water_cut_road_clean = gdf_seg_water_cut_road_clean[(gdf_seg_water_cut_road_clean["geometry"].geom_type == 'Polygon') | (gdf_seg_water_cut_road_clean["geometry"].geom_type == 'MultiPolygon')]
    gdf_seg_water_cut_road_clean = gdf_seg_water_cut_road_clean[gdf_seg_water_cut_road_clean['geometry'].notnull()]
    gdf_seg_water_cut_road_clean = gdf_seg_water_cut_road_clean[gdf_seg_water_cut_road_clean.is_valid]
    gdf_seg_water_cut_road_clean['geometry'] = gdf_seg_water_cut_road_clean['geometry'].apply(lambda geom: geom.buffer(0) if not geom.is_valid else geom)
    gdf_seg_water_cut_road_clean = gdf_seg_water_cut_road_clean[~gdf_seg_water_cut_road_clean.geometry.is_empty & ~gdf_seg_water_cut_road_clean.geometry.isna()].copy()
    gdf_seg_water_cut_road_clean[FIELD_AREA] = gdf_seg_water_cut_road_clean.geometry.area

    # Merge polygones eau avec les autres polygones
    fields_to_get_list = [FIELD_FID, FIELD_AREA, "geometry"]
    gdf_seg_output_tmp = pd.concat([gdf_seg_water_cut_road_clean[fields_to_get_list], gdf_seg_output_fusion_clean[fields_to_get_list]], ignore_index=True)

    # Rajouter les polygones de routes principales si demandé
    if vector_roads_main_input != "" :
        gdf_main_road_primary = gpd.read_file(vector_roads_main_input)
        road_primary_union = unary_union(gdf_main_road_primary.geometry)
        gdf_road_primary_union = gpd.GeoDataFrame(geometry=[road_primary_union], crs=gdf_main_road_primary.crs)
        gdf_seg_output_tmp = gdf_seg_output_tmp[gdf_seg_output_tmp.geometry.type.isin(["Polygon", "MultiPolygon"])]
        gdf_seg_output_tmp["geometry"] = gdf_seg_output_tmp.geometry.apply(lambda geom: unary_union(geom) if geom.type == 'MultiPolygon' else geom)
        gdf_seg_cut_by_primary_road = gpd.overlay(gdf_seg_output_tmp, gdf_road_primary_union, how='difference', keep_geom_type=True)
        gdf_seg_cut_by_primary_road = gdf_seg_cut_by_primary_road[gdf_seg_cut_by_primary_road.geometry.type.isin(["Polygon", "MultiPolygon"])]
        gdf_seg_output_tmp = pd.concat([gdf_seg_cut_by_primary_road[fields_to_get_list], gdf_main_road_primary[fields_to_get_list]], ignore_index=True)

    # Re-nettoyer les polygones
    gdf_seg_output_tmp[FIELD_AREA] = gdf_seg_output_tmp.geometry.area
    gdf_seg_output_clean = cleanPolygons(gdf_seg_output_tmp, THRESHOLD_MICRO_SMALL_AREA, FIELD_FID, FIELD_ORG_ID_LIST, FIELD_AREA, clean_ring=False)
    gdf_seg_output_clean["geometry"] = gdf_seg_output_clean.geometry.apply(lambda geom: unary_union(geom) if geom.type == 'MultiPolygon' else geom)
    gdf_seg_output_clean[FIELD_AREA] = gdf_seg_output_clean.geometry.area
    gdf_seg_output_clean = gdf_seg_output_clean[gdf_seg_output_clean.geometry.area > THRESHOLD_NANO_SMALL_AREA]

    # Sauvegarde des resultats en fichier vecteur
    vector_seg_output_temp = path_folder_val_tmp + os.sep + os.path.basename(os.path.splitext(vector_seg_output)[0]) + SUFFIX_TEMP + extension_vector
    gdf_seg_output_clean.to_file(vector_seg_output_temp, driver=format_vector, crs="EPSG:" + str(epsg))

    # Correction des erreurs topologiques en SQL
    correctTopology_Postgis(vector_seg_output_temp, vector_seg_output, epsg, project_encoding, server_postgis, port_number, user_postgis, password_postgis, database_postgis, schema_postgis, path_time_log="", format_vector=format_vector)

    if debug >= 1:
        print(bold + green + "Fin des calculs" + endC)
        print(cyan + "segPolygonsMerging() : " + endC + "Fichier de sortie => vector_seg_output : " + str(vector_seg_output))

    # Supression des repertoirtes et fichiers temporaires
    if not save_results_intermediate :
        if os.path.exists(path_folder_val_tmp):
            deleteDir(path_folder_val_tmp)
        if os.path.isfile(vector_seg_output_temp) :
            removeVectorFile(vector_seg_output_temp, format_vector)
        if os.path.isfile(vector_water_temp):
            removeVectorFile(vector_water_temp, format_vector)
        if os.path.isfile(vector_water_temp_cut):
            removeVectorFile(vector_water_temp_cut, format_vector)
    return

# ==================================================================================================================================================
if __name__ == '__main__':

    ##### paramètres en entrées #####
    # il est recommandé de prendre un répertoire avec accès rapide en lecture et écriture pour accélérer les traitements
    """
    BASE_FOLDER = "/mnt/RAM_disk/INTEGRATION"
    emprise_vector =  "/mnt/RAM_disk/INTEGRATION/emprise_fusion.shp"
    raster_data_input = "/mnt/RAM_disk/INTEGRATION/create_data/result/OCS_2023_cut.tif"
    raster_build_height_input = "/mnt/RAM_disk/INTEGRATION/create_data/result/builds_height.tif"
    vector_roads_input = "/mnt/RAM_disk/INTEGRATION/create_data/result/all_roads.shp"
    #vector_seg_input = "/mnt/RAM_disk/INTEGRATION/seg_post_processing/toulouse_seg_post.shp"
    vector_seg_input = "/mnt/RAM_disk/INTEGRATION/seg_post_processing/Blagnac_slic_seg.shp"
    vector_seg_output = "/mnt/RAM_disk/INTEGRATION/seg_res_fusion/res/Blaganc_seg_end23.shp"
    """
    """
    BASE_FOLDER = "/mnt/RAM_disk/Grabel"
    emprise_vector = "/mnt/RAM_disk/Grabel/emprise_grabels.shp"
    raster_data_input = "/mnt/RAM_disk/Grabel/create_data/result/OCS_2023_cut.tif"
    raster_build_height_input = "/mnt/RAM_disk/Grabel/create_data/result/builds_height.tif"
    vector_roads_input = "/mnt/RAM_disk/Grabel/create_data/result/all_roads.shp"
    vector_seg_input = "/mnt/RAM_disk/Grabel/seg_post_processing/grabels_seg_post.shp"
    vector_seg_output = "/mnt/RAM_disk/Grabel/grabel_seg_end.shp"
    """

    """
    BASE_FOLDER = "/mnt/RAM_disk/Data_blagnac"
    emprise_vector = "/mnt/RAM_disk/Data_blagnac/emprise_fusion.shp"
    raster_data_input = "/mnt/RAM_disk/Data_blagnac/create_data/result/OCS_2023_cut.tif"
    raster_build_height_input = "/mnt/RAM_disk/Data_blagnac/create_data/result/builds_height.tif"
    vector_roads_input = "/mnt/RAM_disk/Data_blagnac/create_data/result/all_roads.shp"
    vector_seg_input = "/mnt/RAM_disk/Data_blagnac/blagnac_seg_post.shp"
    vector_seg_output = "/mnt/RAM_disk/Data_blagnac/blagnac_seg_end.shp"
    """
    BASE_FOLDER = "/mnt/RAM_disk/INTEGRATION"
    emprise_vector =  "/mnt/RAM_disk/INTEGRATION/emprise/Emprise_Toulouse.shp"
    raster_data_input = "/mnt/RAM_disk/INTEGRATION/create_data/result/OCS_2023_cut.tif"
    raster_build_height_input = "/mnt/RAM_disk/INTEGRATION/create_data/result/builds_height.tif"
    vector_roads_input = "/mnt/RAM_disk/INTEGRATION/create_data/result/all_roads.shp"
    #vector_roads_main_input = "/mnt/RAM_disk/INTEGRATION/create_data/result/roads_main.shp"
    vector_roads_main_input = ""
    vector_seg_input = "/mnt/RAM_disk/INTEGRATION/pres_seg_Toulouse.shp"
    vector_seg_output = "/mnt/RAM_disk/INTEGRATION/Toulouse_seg_end2.shp"

    # exec
    segPolygonsMerging(
        path_base_folder = BASE_FOLDER,
        emprise_vector = emprise_vector,
        raster_data_input = raster_data_input,
        raster_build_height_input = raster_build_height_input,
        vector_roads_input = vector_roads_input,
        vector_roads_main_input = vector_roads_main_input,
        vector_seg_input = vector_seg_input,
        vector_seg_output = vector_seg_output,
        no_data_value=0,
        epsg=2154,
        server_postgis = "localhost",
        port_number = 5433,
        project_encoding = "latin1",
        user_postgis = "postgres",
        password_postgis = "postgres",
        database_postgis = "cutbylines",
        schema_postgis = "public",
        format_raster="GTiff",
        format_vector='ESRI Shapefile',
        extension_raster=".tif",
        extension_vector=".shp",
        path_time_log="",
        save_results_intermediate=False,
        overwrite=True
    )
