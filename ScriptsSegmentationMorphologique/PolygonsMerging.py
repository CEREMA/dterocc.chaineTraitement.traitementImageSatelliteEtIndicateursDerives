#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT QUI FUSIONNE LES POLYGONS D'UNE SEGMENTATION MORPHOLOGIE URBAINE AFIN DE SEGMENTER LES POLYGONES A L'ECHELLE DES QUARTIERS         #
#                                                                                                             (UTILISATION CARTE LCZ)       #
#                                                                                                                                           #
#############################################################################################################################################

"""
Nom de l'objet : PolygonsMerging.py
Description :
    Objectif : TODO

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

# data processing
import numpy as np
import pandas as pd
from ast import literal_eval

# geomatique
import geopandas as gpd
import shapely
from shapely.geometry import shape, Polygon, MultiPolygon, GeometryCollection, LineString

# intern libs
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC
from Lib_raster import setNodataValueImage, getPixelSizeImage, getPixelWidthXYImage, identifyPixelValues, cutImageByVector
from Lib_vector import getEmpriseVector, cutVectorAll, fusionVectors, renameFieldsVector
from Lib_file import removeVectorFile, deleteDir
from Lib_file import removeFile
from CrossingVectorRaster import statisticsVectorRaster
from CCMpostprocessing import removeRing, computePolygonAreas

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 3 : affichage maximum de commentaires lors de l'execution du script. Intermédiaire : affichage intermédiaire
debug = 2

## Constantes Generales ##
# variables fusion (= best params cf grid search)
THRESHOLD_ROAD_AREA_POLY = 10000
THRESHOLD_SMALL_AREA_POLY = 5000
THRESHOLD_MEDIUM_AREA_POLY = 10000
REF_METRE = 200
THRESHOLD_AREA_POLY = REF_METRE**2
AREA_MAX_POLYGON = THRESHOLD_AREA_POLY * 1.5

THRESHOLD_EUCLIDIAN_DIST = 0.2
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
    area_intersect = 0

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
        if (fid != gdf.loc[idx, fid_column]) and not any(element in test_org_id_list for element in org_id_l) and (polygon != target_geometry) and (polygon.intersects(buffered_target_geometry)) :
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
    dist = (np.sqrt((row_poly["mean_r"]-row_adj_poly["mean_r"])**2+((row_poly["mean_g"]+row_poly["mean_b"])-(row_adj_poly["mean_g"]+row_adj_poly["mean_b"]))**built_weight+2*(row_poly["mean_haut"]-row_adj_poly["mean_haut"])**2) + (1-row_adj_poly['i_compact_merged']) )/2

    return dist

###########################################################################################################################################
# FUNCTION computeProportionWithCond()                                                                                                    #
###########################################################################################################################################
# !!! Non utilisé !!!
def computeProportionWithCond(total_count, pixel_dict, key_conditions=None):
    """
    # ROLE:
    #   Calcule la proportion de pixels en fonction de conditions sur la valeur du pixels à partir d'un dictionnaire d'occurences de pixels.
    #
    # PARAMETERS:
    #     total_count : le nombre total d'entrée.
    #     pixel_dict : dictonaire des pixels.
    #     key_conditions : clé de condition(default is None).
    # RETURNS:
    #     la proportion, le nombre de pixels, le nombre total
    """
    # Case when no pixels are in the polygons
    if total_count == 0:
        proportion = 0
        nb_of_pixels = sum(pixel_dict.values())
        return proportion, nb_of_pixels, total_count

    if key_conditions == None:
        nb_of_pixels = sum(pixel_dict.values())
    else:
        l_keys = []
        for key_condition in key_conditions:
            operateur, num = key_condition
            for key in pixel_dict.keys():
                if eval(str(key) + operateur + str(num)):
                    l_keys.append(key)

        nb_of_pixels = sum([pixel_dict[key] for key in l_keys])
    proportion = nb_of_pixels/total_count

    return proportion, nb_of_pixels, total_count

###########################################################################################################################################
# FUNCTION sumProportion()                                                                                                                #
###########################################################################################################################################
# !!! Non utilisé !!!
def sumProportion(resProp1, resProp2):
    """
    # ROLE:
    #   Somme proportionelle.
    #
    # PARAMETERS:
    #     resProp1 : liste1 d'entrée.
    #     resProp2 : liste2 d'entrée.
    # RETURNS:
    #     Liste de somme proportionel.
    """
    nb_of_pixels1 = resProp1[1]
    total_count1 = resProp1[2]
    nb_of_pixels2 = resProp2[1]
    total_count2 = resProp2[2]

    if (total_count1 + total_count2) == 0:
        sum_prop = 0
    else:
        sum_prop = nb_of_pixels1 + nb_of_pixels2 / total_count1 + total_count2
    return sum_prop

###########################################################################################################################################
"""
# Fonction pour imprimer les détails de chaque GeometryCollection
def printGeometryCollectionDetails(geom):
    if isinstance(geom, GeometryCollection):
        for sub_geom in geom.geoms:
            print(sub_geom)
    elif isinstance(geom, Polygon):
        print(geom)
    else:
        print("Not a GeometryCollection or Polygon")
   return

# Fonction pour filtrer les polygones à partir d'une GeometryCollection
def filterPolygons(geom):
    if isinstance(geom, GeometryCollection):
        polygons = [sub_geom for sub_geom in geom.geoms if isinstance(sub_geom, Polygon)]
        return GeometryCollection(polygons)
    elif isinstance(geom, Polygon):
        return geom
    else:
        return None

# Fonction pour corriger les erreur topologyque
def fixTopologyError(geometry):
    try:
        # Essayez de créer une géométrie valide
        fixed_geometry = geometry.buffer(0)
        return fixed_geometry
    except Exception as e:
        # En cas d'erreur, essayez de simplifier la géométrie
        simplified_geometry = geometry.simplify(tolerance=0.1, preserve_topology=True)
        return simplified_geometry

# Fonction pour merger des polygones entre eux
def mergeMultiPolygons(geom):
    if geom.geom_type == 'MultiPolygon':
        return Polygon(list(geom.buffer(0).exterior.coords))
    else:
        return geom
"""
###########################################################################################################################################
#                                                                                                                                         #
# Fusion processing polygones segmentation                                                                                                #
#                                                                                                                                         #
###########################################################################################################################################

###########################################################################################################################################
# FUNCTION computeStatisticIndiceSegmentation()                                                                                           #
###########################################################################################################################################
def computeStatisticIndiceSegmentation(path_folder_work, emprise_vector, file_data_input, raster_road_width_input, raster_build_height_intput, vector_seg_stat_input, vector_seg_stat_output, no_data_value=0, epsg=2154, format_raster="GTiff", format_vector='ESRI Shapefile', extension_raster=".tif", extension_vector=".shp", path_time_log = "", save_results_intermediate=False, overwrite=True) :
    """
    # ROLE:
    #    Calcul les statistiques des indicateurs de l'image d'entrée de la segmentation, végétation, imperméabilité, routes
    #    pour les polygones issues de la segmentation et découpés par les routes
    #
    # PARAMETERS:
    #     path_folder_work : répertoire de travail local.
    #     emprise_vector : vecteur d'emprise de la zone d'étude.
    #     file_data_input : le fichier de donnée pseudo RGB d'entrée.
    #     raster_road_width_input :  fichier d'entrée rasteur largeur de routes d'entrée.
    #     raster_build_height_intput : fichier d'entrée rasteur hauteur des batis d'entrée.
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
    SUFFIX_CUT = "_cut"

    # Nettoyage du vecteur stat de sortie si il existe deja
    if os.path.isfile(vector_seg_stat_output):
        removeVectorFile(vector_seg_stat_output, format_vector)

    # Definir la resolution
    resolution = getPixelSizeImage(file_data_input)
    pixel_size_x, pixel_size_y = getPixelWidthXYImage(file_data_input)

    # Découpage du fichier donnée d'entrée pseudo RGB
    file_input_data_cut = path_folder_work + os.sep + os.path.splitext(os.path.basename(file_data_input))[0] + SUFFIX_CUT + extension_raster
    if os.path.isfile(file_input_data_cut):
        removeFile(file_input_data_cut)
    cutImageByVector(emprise_vector, file_data_input, file_input_data_cut, pixel_size_x, pixel_size_y, False, no_data_value, epsg, format_raster, format_vector)
    setNodataValueImage(file_input_data_cut, no_data_value)

    # Découpage du fichier largeur de route
    raster_road_width_cut = path_folder_work + os.sep + os.path.splitext(os.path.basename(raster_road_width_input))[0] + SUFFIX_CUT + extension_raster
    if os.path.isfile(raster_road_width_cut):
        removeFile(raster_road_width_cut)
    cutImageByVector(emprise_vector, raster_road_width_input, raster_road_width_cut, pixel_size_x, pixel_size_y, False, no_data_value, epsg, format_raster, format_vector)

    # Découpage du fichier hauteur de bati
    raster_builds_height_cut = path_folder_work + os.sep + os.path.splitext(os.path.basename(raster_build_height_intput))[0] + SUFFIX_CUT + extension_raster
    if os.path.isfile(raster_builds_height_cut):
        removeFile(raster_builds_height_cut)
    cutImageByVector(emprise_vector, raster_build_height_intput, raster_builds_height_cut, pixel_size_x, pixel_size_y, False, no_data_value, epsg, format_raster, format_vector)

    if debug >= 1:
        print(cyan + "computeStatisticIndiceSegmentation() : " + endC + "path file data segmentation input cut to match with segmentation output extends to {}\n".format(file_input_data_cut))

    # Dico des traitements statistiques à réaliser
    stat_processing_dico = {"r":[file_input_data_cut,1], "g":[file_input_data_cut,2], "b":[file_input_data_cut,3], "larg":[raster_road_width_cut,1], "haut":[raster_builds_height_cut,1]}

    col_to_delete_list = ["minority", "median", "unique", "range"]
    col_to_add_list = ["count"]
    fields_name_list = ["count","majority", "min", "max", "mean", "sum", "std"]

    # Pour chaque traitement ...
    for key_value, file_band in stat_processing_dico.items():
        image_input = file_band[0]
        band_number = file_band[1]
        image_values_list = identifyPixelValues(image_input)
        class_label_dico = {}
        fields_dico_list = []
        new_fields_dico_list = []
        if key_value !=  "haut" :
            vector_seg_stat_tmp = path_folder_work + os.sep + os.path.splitext(os.path.basename(vector_seg_stat_output))[0] + "_" + key_value + extension_vector
        else :
            vector_seg_stat_tmp = vector_seg_stat_output

        statisticsVectorRaster(image_input, vector_seg_stat_input, vector_seg_stat_tmp, band_number, False, True, True, col_to_delete_list, col_to_add_list, class_label_dico, False, no_data_value, format_vector, path_time_log, save_results_intermediate, overwrite)

        # Rename columns
        new_fields_name_list = ["coun_"+ str(key_value), "maj_"+ str(key_value), "min_"+ str(key_value), "max_"+ str(key_value), "mean_"+ str(key_value), "sum_"+ str(key_value), "std_"+ str(key_value)]
        renameFieldsVector(vector_seg_stat_tmp, fields_name_list + fields_dico_list , new_fields_name_list + new_fields_dico_list, format_vector)
        vector_seg_stat_input = vector_seg_stat_tmp

    return

###########################################################################################################################################
# FUNCTION mergeRoadPolygons()                                                                                                            #
###########################################################################################################################################
def mergeRoadPolygons(gdf, threshold_road_area_poly=THRESHOLD_ROAD_AREA_POLY, fid_column='FID', is_road_column='is_road', org_id_list_column='org_id_l', area_column='area'):
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
    # RETURNS:
    #     dataframe des polygones routes mergés.
    """

    # Récupère les polygones routes
    gdf_road_poly = gdf[gdf[is_road_column] == 1]

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
        gdf_adj_select_poly = gdf_adj_select_poly.copy()
        ##gdf_adj_select_poly['geom_merged'] = gdf_adj_select_poly['geom_merged'].apply(lambda geom: geom.convex_hull if isinstance(geom, GeometryCollection) else geom)
        gdf_adj_select_poly['geom_merged'] = gdf_adj_select_poly["geometry"].apply(lambda x: gpd.GeoSeries([x, geom_road_poly]).unary_union)
        gdf_adj_select_poly['geom_merged'] = gdf_adj_select_poly['geom_merged'].apply(removeRing)

        # Fusionner les multi-polygons
        gdf_adj_select_poly['geom_merged'] = gdf_adj_select_poly['geom_merged'].apply(lambda geom: geom if geom.geom_type == 'Polygon' else Polygon(list(geom.buffer(0).exterior.coords)))
        gdf_adj_select_poly = gdf_adj_select_poly[gdf_adj_select_poly['geom_merged'].apply(lambda geom: geom.geom_type in ['Polygon'])]

        if gdf_adj_select_poly.empty :
            if debug >= 1:
                print(cyan + "mergeRoadPolygons() : " + endC + "fid: %s, EMPTY_CASE" %(FID_road_poly))
            continue

        new_geom = gdf_adj_select_poly["geom_merged"].values[0]
        new_area = gdf_adj_select_poly[area_column].values[0] + area_road_poly
        new_org_id_list = gdf_adj_select_poly[org_id_list_column].values[0] + orig_id_l_road_poly

        # Récupère le FID du polygone merged et updates des champs de la nouvelle geometrie
        best_fid_geom = gdf_adj_select_poly[fid_column].values[0]

        # Maj fields
        idx_row_to_change = gdf.loc[gdf[fid_column] == best_fid_geom].index[0]
        gdf.at[idx_row_to_change, "geometry"] = new_geom
        gdf.at[idx_row_to_change, area_column] = new_area
        gdf.at[idx_row_to_change, org_id_list_column] = new_org_id_list
        gdf.at[idx_row_to_change, is_road_column] = is_route_road_poly
        new_row = gdf.loc[gdf[fid_column] == best_fid_geom]

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
def mergeSmallPolygons(gdf, threshold_small_area_poly=THRESHOLD_SMALL_AREA_POLY, fid_column='FID', org_id_list_column='org_id_l', area_column='area'):
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
    # RETURNS:
    #     dataframe des petis polygones mergés.
    """

    # Récupère les petits polygones en fonction d'un seuil
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
        gdf_adj_select_poly['geom_merged'] = gdf_adj_select_poly["geometry"].apply(lambda x: gpd.GeoSeries([x, geom_small_poly]).unary_union)
        gdf_adj_select_poly['geom_merged'] = gdf_adj_select_poly['geom_merged'].apply(removeRing)

        # Fusionner les multi-polygons (ne marche pas!!)
        #gdf_adj_select_poly['geom_merged'] = gdf_adj_select_poly['geom_merged'].apply(lambda geom: geom if geom.geom_type == 'Polygon' else Polygon(list(geom.buffer(0).exterior.coords)))
        #gdf_adj_select_poly['geom_merged'] = gdf_adj_select_poly['geom_merged'].apply(lambda geom: geom if geom.geom_type == 'Polygon' else Polygon([list(sub_geom.exterior.coords) for sub_geom in geom.geoms]))
        #gdf_adj_select_poly['geom_merged'] = gdf_adj_select_poly['geom_merged'].apply(lambda geom: geom if geom.geom_type == 'Polygon' else Polygon([list(sub_geom.exterior.coords) if isinstance(sub_geom.exterior.coords, tuple) else list(sub_geom.exterior.coords) for sub_geom in geom.geoms]))
        gdf_adj_select_poly = gdf_adj_select_poly[gdf_adj_select_poly['geom_merged'].apply(lambda geom: geom.geom_type in ['Polygon','MultiPolygon'])]

        if gdf_adj_select_poly.empty :
            if debug >= 1:
                print(cyan + "mergeSmallPolygons() : " + endC + "fid: %s, EMPTY_CASE" %(FID_small_poly))
            continue

        new_geom = gdf_adj_select_poly["geom_merged"].values[0]
        new_area = gdf_adj_select_poly[area_column].values[0] + area_small_poly
        new_org_id_list = gdf_adj_select_poly[org_id_list_column].values[0] + orig_id_l_small_poly

        # Récupère le FID du polygone merged et updates des champs de la nouvelle geometrie
        best_fid_geom = gdf_adj_select_poly[fid_column].values[0]

        # Maj fields
        idx_row_to_change = gdf.loc[gdf[fid_column] == best_fid_geom].index[0]
        gdf.at[idx_row_to_change, "geometry"] = new_geom
        gdf.at[idx_row_to_change, area_column] = new_area
        gdf.at[idx_row_to_change, org_id_list_column] = new_org_id_list
        new_row = gdf.loc[gdf[fid_column] == best_fid_geom]

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
    #     area_column : nom de la colonne contenant la valeur d ela surface du polygones (default : 'area').
    # RETURNS:
    #     datafame des polygones fusionnés.
    """
    # Constantes

    # Calcul surface polygons
    gdf = computePolygonAreas(gdf)
    # Récupère les petits polygones en fonction d'un seuil
    gdf_poly = gdf[gdf[area_column] <= threshold_area_poly]

    if debug >= 1:
        print(cyan + "mergePolygonsWithConds() : " + endC + "length polygons medium list:", len(gdf_poly))
        print(cyan + "mergePolygonsWithConds() : " + endC + "length polygons list:", len(gdf))

    # Sort polygons by size
    gdf_poly = gdf_poly.sort_values(by=area_column, ascending=True)
    l_poly = gdf_poly[fid_column].tolist()

    # iterate over polygons
    while len(l_poly) > 0:

        # Get polygon fields
        FID_poly = l_poly.pop(0)
        if debug >= 3:
            print(cyan + "mergePolygonsWithConds() : " + endC +"FID", FID_poly)

        row_medium_poly = gdf.loc[gdf[fid_column] == FID_poly]
        geom_poly = row_medium_poly["geometry"].values[0]
        area_poly = row_medium_poly[area_column].values[0]
        count_larg_poly = row_medium_poly["coun_larg"].values[0]
        count_rgb_poly = row_medium_poly["count_rgb"].values[0]
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
        gdf_adj_poly['geom_merged'] = gdf_adj_poly["geometry"].apply(lambda x: gpd.GeoSeries([x, geom_poly]).unary_union)

        # Eliminate merged geometries where intersection is defined only by a point
        gdf_adj_poly = gdf_adj_poly[gdf_adj_poly['geom_merged'].geom_type == 'Polygon']

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
            fid_best_dist_eucl = gdf_adj_poly[gdf_adj_poly['dist_eucl'] == gdf_adj_poly['dist_eucl'].min()][fid_column].values[0]
            if debug >= 3:
                print(cyan + "mergePolygonsWithConds() : " + endC + "FID best dist eucl:", fid_best_dist_eucl)
            gdf_adj_poly = gdf_adj_poly[gdf_adj_poly[fid_column] == fid_best_dist_eucl]

        # Big polygons
        elif threshold_medium_area_poly<= area_poly <= threshold_area_poly :
            if debug >= 3:
                print(cyan + "mergePolygonsWithConds() : " + endC + "Case2 Big polygons")

            # On ne dépasse pas la surface maximale de polygone lors du merging
            gdf_adj_poly = gdf_adj_poly[gdf_adj_poly['area_merged'] <= area_max_poly]

            # Distance euclidienne avec le polygone et tous ses voisins (cette distance inclue la compacité)
            if not gdf_adj_poly[(gdf_adj_poly['dist_eucl'] == gdf_adj_poly['dist_eucl'].min()) & (gdf_adj_poly['dist_eucl'] > threshold_euclidian_dist)].empty:
                fid_best_dist_eucl = gdf_adj_poly[(gdf_adj_poly['dist_eucl'] == gdf_adj_poly['dist_eucl'].min()) & (gdf_adj_poly['dist_eucl'] > threshold_euclidian_dist)][fid_column].values[0]
            else:
                # Gérer le cas où le DataFrame filtré est vide
                fid_best_dist_eucl = None  # ou une autre valeur par défaut

            if not fid_best_dist_eucl :
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
        new_area = gdf_adj_poly[area_column].values[0]  + area_poly
        new_count_larg = gdf_adj_poly["coun_larg"].values[0] + count_larg_poly
        new_count_rgb = gdf_adj_poly["count_rgb"].values[0] + count_rgb_poly
        new_org_id_list = gdf_adj_poly[org_id_list_column].values[0] + orig_id_l_poly

        # Maj fields
        idx_row_to_change = gdf.loc[gdf[fid_column] == fid_best_dist_eucl].index[0]
        gdf.at[idx_row_to_change, "geometry"] = new_geom
        gdf.at[idx_row_to_change, area_column] = new_area
        gdf.at[idx_row_to_change, "coun_larg"] = new_count_larg
        gdf.at[idx_row_to_change, "count_rgb"] = new_count_rgb
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
        print(cyan + "mergePolygonsWithConds() : " + endC +"Fin des traitements des polygones moyens nouveaux polygons list:", len(gdf))
    return gdf

###########################################################################################################################################
# FUNCTION segPolygonsMerging()                                                                                                           #
###########################################################################################################################################
def segPolygonsMerging(path_base_folder,  emprise_vector, file_data_input, raster_road_width_input, raster_build_height_intput, vector_seg_input, vector_seg_output, no_data_value=0, epsg=2154, format_raster="GTiff", format_vector='ESRI Shapefile', extension_raster=".tif", extension_vector=".shp", path_time_log = "", save_results_intermediate=False, overwrite=True):
    """
    # ROLE:
    #     Fusion des polygones de la segmentation.
    #
    # PARAMETERS:
    #     path_base_folder : le dossier de travail.
    #     emprise_vector : fichier d'emprise.
    #     file_data_input : le fichier de donnée pseudo RGB d'entrée.
    #     raster_road_width_input :  fichier d'entrée rasteur largeur de routes.
    #     raster_build_height_intput : fichier d'entrée rasteur des hauteurs de batis.
    #     vector_seg_input : le fichier vecteur de segmentation d'entrée.
    #     vector_seg_output : le fichier vecteur de segmentation avec les polygones fusionnés en sortie
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
        print(bold + green + "Variables dans le segPolygonsMerging - Variables générales" + endC)
        print(cyan + "segPolygonsMerging() : " + endC + "path_base_folder : " + str(path_base_folder))
        print(cyan + "segPolygonsMerging() : " + endC + "emprise_vector : " + str(emprise_vector))
        print(cyan + "segPolygonsMerging() : " + endC + "file_data_input : " + str(file_data_input))
        print(cyan + "segPolygonsMerging() : " + endC + "raster_road_width_input : " + str(raster_road_width_input))
        print(cyan + "segPolygonsMerging() : " + endC + "raster_build_height_intput : " + str(raster_build_height_intput))
        print(cyan + "segPolygonsMerging() : " + endC + "vector_seg_input : " + str(vector_seg_input))
        print(cyan + "segPolygonsMerging() : " + endC + "vector_seg_output : " + str(vector_seg_output))
        print(cyan + "segPolygonsMerging() : " + endC + "no_data_value : " + str(no_data_value))
        print(cyan + "segPolygonsMerging() : " + endC + "epsg : " + str(epsg))
        print(cyan + "segPolygonsMerging() : " + endC + "format_raster : " + str(format_raster))
        print(cyan + "segPolygonsMerging() : " + endC + "format_vector : " + str(format_vector))
        print(cyan + "segPolygonsMerging() : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "segPolygonsMerging() : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "segPolygonsMerging() : " + endC + "path_time_log : " + str(path_time_log))
        print(cyan + "segPolygonsMerging() : " + endC + "save_results_intermediate : "+ str(save_results_intermediate))
        print(cyan + "segPolygonsMerging() : " + endC + "overwrite : "+ str(overwrite))

    # Les constantes
    FIELD_FID = "FID"
    FIELD_IS_ROAD = "is_road"
    FIELD_ORG_ID = "org_id"
    FIELD_ORG_ID_LIST = "org_id_l"
    FIELD_AREA = "area"

    SUFFIX_STAT_IN = "_stat_in"
    SUFFIX_STAT_OUT = "_stat_out"

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

    # Passer org_id sous forme de liste org_id_l
    gdf_seg[FIELD_ORG_ID_LIST] = gdf_seg[FIELD_ORG_ID].apply(lambda x: [x])

    # Fusion des polygons bords de routes
    gdf_poly_road_merged = mergeRoadPolygons(gdf_seg, threshold_road_area_poly=THRESHOLD_ROAD_AREA_POLY, fid_column=FIELD_FID, is_road_column=FIELD_IS_ROAD, org_id_list_column=FIELD_ORG_ID_LIST, area_column=FIELD_AREA)

    # Fusion petits polygons
    gdf_small_poly_merged = mergeSmallPolygons(gdf_poly_road_merged, threshold_small_area_poly=THRESHOLD_SMALL_AREA_POLY, fid_column=FIELD_FID, org_id_list_column=FIELD_ORG_ID_LIST, area_column=FIELD_AREA)
    gdf_small_poly_merged[FIELD_ORG_ID_LIST] = gdf_small_poly_merged[FIELD_ORG_ID_LIST].apply(str)
    vector_seg_stat_input = path_folder_stat + os.sep + os.path.splitext(os.path.basename(vector_seg_input))[0] + SUFFIX_STAT_IN + extension_vector
    gdf_small_poly_merged.to_file(vector_seg_stat_input, driver=format_vector, crs="EPSG:" + str(epsg))

    # Calcul des statistiques des indicateurs de l'image d'entrée de la segmentation, végétation, imperméabilité, routes.
    vector_seg_stat_output = path_folder_stat + os.sep + os.path.splitext(os.path.basename(vector_seg_input))[0] + SUFFIX_STAT_OUT + extension_vector
    computeStatisticIndiceSegmentation(path_folder_val_tmp, emprise_vector, file_data_input, raster_road_width_input, raster_build_height_intput, vector_seg_stat_input, vector_seg_stat_output, no_data_value, epsg, format_raster, format_vector, extension_raster, extension_vector, path_time_log, save_results_intermediate, overwrite)
    if debug >= 1:
        print(bold + green + "Calculs des statistiques Ok" + endC)
        print(cyan + "segPolygonsMerging() : " + endC + "Fichier de stat => vector_seg_stat_output : " + str(vector_seg_stat_output))

    # Fusion de polygons moyens et grand avec critères sur les statistiques
    gdf_seg_stat = gpd.read_file(vector_seg_stat_output)
    gdf_seg_stat['count_rgb'] = gdf_seg_stat[['coun_r', 'coun_g', 'coun_b']].sum(axis=1)
    gdf_seg_stat = gdf_seg_stat[[FIELD_FID, FIELD_IS_ROAD, FIELD_ORG_ID, FIELD_ORG_ID_LIST, FIELD_AREA,'maj_larg', 'coun_larg', 'count_rgb', 'mean_r', 'mean_b', 'mean_g', 'coun_haut', 'mean_haut', 'geometry']]
    gdf_seg_stat[FIELD_ORG_ID_LIST] = gdf_seg_stat[FIELD_ORG_ID_LIST].apply(literal_eval)
    gdf_cond_poly_merged = mergePolygonsWithConds(gdf_seg_stat, threshold_medium_area_poly=THRESHOLD_MEDIUM_AREA_POLY, threshold_area_poly=THRESHOLD_AREA_POLY, area_max_poly=AREA_MAX_POLYGON, threshold_euclidian_dist=THRESHOLD_EUCLIDIAN_DIST, max_adjacent_neighbor=MAX_ADJACENT_NEIGHBOR, fid_column=FIELD_FID, org_id_list_column=FIELD_ORG_ID_LIST, area_column=FIELD_AREA)

    # Supprimer les colonnes
    gdf_cond_poly_merged[FIELD_ORG_ID_LIST] = gdf_cond_poly_merged[FIELD_ORG_ID_LIST].apply(str)
    colonnsToDel = [ FIELD_IS_ROAD, FIELD_ORG_ID, FIELD_ORG_ID_LIST, FIELD_AREA,'maj_larg', 'coun_larg', 'count_rgb', 'mean_r', 'mean_b', 'mean_g', 'coun_haut', 'mean_haut']
    #gdf_cond_poly_merged = gdf_cond_poly_merged.drop(columns=colonnsToDel)
    for colonne in colonnsToDel:
        del gdf_cond_poly_merged[colonne]

    # Sauvegarde des results en fichier vecteur
    gdf_cond_poly_merged.to_file(vector_seg_output, driver=format_vector, crs="EPSG:" + str(epsg))
    if debug >= 1:
        print(bold + green + "Fin des calculs" + endC)
        print(cyan + "segPolygonsMerging() : " + endC + "Fichier de sortie => vector_seg_output : " + str(vector_seg_output))

    # Supression des repertoirtes et fichiers temporaires
    if not save_results_intermediate :
        if os.path.exists(path_folder_val_tmp):
            deleteDir(path_folder_val_tmp)

    return

# ==================================================================================================================================================
if __name__ == '__main__':

    ##### paramètres en entrées #####
    # il est recommandé de prendre un répertoire avec accès rapide en lecture et écriture pour accélérer les traitements
    BASE_FOLDER = "/mnt/RAM_disk/INTEGRATION"
    emprise_vector =  "/mnt/RAM_disk/INTEGRATION/emprise/Emprise_Toulouse_Metropole.shp"
    file_data_input = "/mnt/RAM_disk/INTEGRATION/create_data/result/pseudoRGB_input_seg_res5.tif"
    raster_road_width_input = "/mnt/RAM_disk/INTEGRATION/create_data/result/roads_width.tif"
    raster_build_height_intput = "/mnt/RAM_disk/INTEGRATION/create_data/result/builds_height.tif"
    vector_seg_input = "/mnt/RAM_disk/INTEGRATION/seg_post_processing/toulouse_rgb_output_seg_res5.shp"
    vector_seg_output = "/mnt/RAM_disk/INTEGRATION/seg_res_fusion/res/toulouse_output_seg_res5.shp"

    # exec
    segPolygonsMerging(
        path_base_folder = BASE_FOLDER,
        emprise_vector = emprise_vector,
        file_data_input = file_data_input,
        raster_road_width_input = raster_road_width_input,
        raster_build_height_intput = raster_build_height_intput,
        vector_seg_input = vector_seg_input,
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
