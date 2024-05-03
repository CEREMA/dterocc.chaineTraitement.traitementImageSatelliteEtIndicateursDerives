#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT QUI EFFECTUE DES TRAITEMENTS POST SEGMENTATION SUR LE MAILLAGE DE SORTIE DE L'ALGORITHME DE SEGMENTATION SUPERPIXEL CCM            #
#                                                                                                       (CONVEX CONSTRAINED MESH)           #
#                                                                                                                                           #
#############################################################################################################################################

"""
Nom de l'objet : CCMpostprocessing.py
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

# System
import os, sys
from osgeo import ogr ,osr, gdal

# Geomatique
import geopandas as gpd
import pandas as pd
from shapely.geometry import MultiLineString, LineString, MultiPolygon, Polygon
from centerline.geometry import Centerline

# Intern libs
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC
from Lib_file import removeFile, removeVectorFile, deleteDir
from Lib_vector import getEmpriseVector, cutVectorAll, createEmpriseVector, fusionVectors, getAttributeType, getAttributeValues, addNewFieldVector, setAttributeValuesList, deleteFieldsVector, renameFieldsVector, updateIndexVector
from Lib_log import timeLine
from Lib_postgis import openConnection, closeConnection, dropDatabase, createDatabase, importVectorByOgr2ogr, exportVectorByOgr2ogr, cutPolygonesByLines

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 3 : affichage maximum de commentaires lors de l'execution du script. Intermédiaire : affichage intermédiaire
debug = 2

###########################################################################################################################################
#                                                                                                                                         #
# UTILS                                                                                                                                   #
#                                                                                                                                         #
###########################################################################################################################################

###########################################################################################################################################
# FUNCTION bufferPolylinesToPolygons()                                                                                                    #
###########################################################################################################################################
def bufferPolylinesToPolygons(gdf, buffer_distance):
    """
    # ROLE:
    #     Convertie des polylignes en polygones avec une valeur de buffer.
    #
    # PARAMETERS:
    #     gdf : descripteur vers les polylignes.
    #     buffer_distance : la valeur du buffer.
    # RETURNS:
    #     descripteur vers les polygones
    """

    # Create buffers around the polylines
    buffered_geoms = gdf.geometry.apply(lambda x: x.buffer(buffer_distance, resolution=1, cap_style=2))
    # Create a GeoDataFrame with the buffered polygons
    gdf_polygons = gpd.GeoDataFrame(geometry=buffered_geoms, crs=gdf.crs)

    return gdf_polygons

###########################################################################################################################################
# FUNCTION calculateAndCleanSmallPolygonArea()                                                                                            #
###########################################################################################################################################
def calculateAndCleanSmallPolygonArea(input_vector, output_vector, field_area, min_area_polygon, epsg=2154, format_vector='ESRI Shapefile'):
    """
    # ROLE:
    #     Nettoye les petits polygonnes d'une surface min.
    #
    # PARAMETERS:
    #     input_vector : le fichier vecteur d'entrée.
    #     output_vector: le fichier vecteur de sortie.
    #     field_area : le champs de surface à filter par min_area_polygon
    #     min_area_polygon : la valeur min de la surface des polygonnes.
    #     epsg (int): EPSG code of the desired projection (default is 2154).
    #     format_vector : format du fichier vecteur de sortie
    #
    # RETURNS:
    #     la data frame de sortie filtrer
    """

    # Lire le fichier Shapefile d'entrée
    gdf = gpd.read_file(input_vector)

    # Calculer la superficie de chaque polygone
    gdf[field_area] = gdf.geometry.area

    # Supprimer les polygones ayant une superficie inférieure à min_area_polygon
    gdf = gdf[gdf[field_area] >= min_area_polygon]
    ##gdf = gdf.query(field_area + ' >= @min_area_polygon')

    # Enregistrer le résultat dans un nouveau fichier Shapefile
    ##gdf.to_file(output_vector, crs="EPSG:" + str(epsg), driver=format_vector)

    return gdf

###########################################################################################################################################
# FUNCTION explodeMultiGdf()                                                                                                              #
###########################################################################################################################################
def explodeMultiGdf(gdf, field_fid):
    """
    # ROLE:
    #     Transforme des géométries multiple en géométries simple.
    #
    # PARAMETERS:
    #     gdf : descripteur sur les multi géométries à transormer.
    #     field_fid :  nom du champs contenat l'id.
    # RETURNS:
    #     une GeoDataFrame sur les géométries transormés
    """

    new_geometries = []
    new_data = []  # List to store data from input DataFrame

    index = 0
    for _, row in gdf.iterrows():
        geometry = row['geometry']
          # Dictionary to store data from the input row

        if geometry.geom_type == 'Polygon' or geometry.geom_type == 'LineString':
            new_geometries.append(geometry)
            row[field_fid] = index
            data = {}
            data.update(row.drop('geometry'))  # Add non-geometry fields to data
            new_data.append(data)
            index += 1
        elif geometry.geom_type == 'MultiPolygon' or geometry.geom_type == 'MultiLineString':
            for poly in geometry.geoms:
                new_geometries.append(poly)
                new_row = row.copy()
                new_row[field_fid] = index
                data = {}
                data.update(new_row.drop('geometry'))  # Add non-geometry fields to data
                new_data.append(data)
                index += 1

    # Create a GeoDataFrame from new_data and new_geometries
    return gpd.GeoDataFrame(new_data, geometry=new_geometries, crs=gdf.crs)

###########################################################################################################################################
# FUNCTION removeRing()                                                                                                                   #
###########################################################################################################################################
    """
    # ROLE:
    #     Fonction pour supprimer les anneaux (rings) d'une géométrie.
    #
    # PARAMETERS:
    #     geometry : géometry polygone d'entrée.
    # RETURNS:
    #     geometry sans ring (anneaux)
    """
# Fonction pour supprimer les anneaux (rings) d'une géométrie
def removeRing(geometry):
    if geometry.geom_type == 'Polygon':
        return Polygon(geometry.exterior)
    elif geometry.geom_type == 'MultiPolygon':
        return MultiPolygon(Polygon(poly.exterior) for poly in geometry.geoms)
    else:
        return geometry

###########################################################################################################################################
# FUNCTION computePolygonAreas()                                                                                                        #
###########################################################################################################################################
def computePolygonAreas(gdf, geometry_column="geometry", area_col_name="area"):
    """
    # ROLE:
    #   Calcule surface polygons.
    #
    # PARAMETERS:
    #     gdf :  dataframe des polygones d'entrée.
    #     geometry_column : nom de la colonne contenant la géometrie (default : "geometry").
    #     area_col_name : nom de a colonne contenant la valeur de surface calculée (default : "area").
    # RETURNS:
    #      dataframe des polygones de sortie avec la valeur de surface
    """
    if geometry_column not in gdf.columns:
        raise ValueError("Le DataFrame doit contenir une colonne {} contenant les géométries des polygones.".format(geometry_column))

    # Ajout colonne contenant les surfaces
    gdf[area_col_name] = gdf[geometry_column].apply(lambda polygon: polygon.area)

    return gdf

###########################################################################################################################################
#                                                                                                                                         #
# Post processing CONVEX CONSTRAINED MESH segmentation                                                                                    #
#                                                                                                                                         #
###########################################################################################################################################

###########################################################################################################################################
# FONCTION cutPolygonesByLines_Postgis()                                                                                                  #
###########################################################################################################################################
def cutPolygonesByLines_Postgis(vector_lines_input, vector_poly_input, vector_poly_output, epsg=2154, project_encoding="UTF-8", server_postgis="localhost", port_number=5432, user_postgis="postgres", password_postgis="postgres", database_postgis="cutbylines", schema_postgis="public", path_time_log="", format_vector='ESRI Shapefile', save_results_intermediate=False, overwrite=True) :
    """
    # ROLE:
    #     Découper des polygones ou multi-polygones par des lignes ou multi-lignes en traitement sous postgis
    #
    # ENTREES DE LA FONCTION :
    #     vector_lines_input: le vecteur de lignes de découpe d'entrée
    #     vector_poly_input: le vecteur de polygones à découpés d'entrée
    #     vector_poly_output: le vecteur e polygones de sortie découpés
    #     epsg : EPSG code de projection
    #     project_encoding : encodage des fichiers d'entrés
    #     server_postgis : nom du serveur postgis
    #     port_number : numéro du port pour le serveur postgis
    #     user_postgis : le nom de l'utilisateurs postgis
    #     password_postgis : le mot de passe de l'utilisateur postgis
    #     database_postgis : le nom de la base postgis à utiliser
    #     schema_postgis : le nom du schéma à utiliser
    #     path_time_log : le fichier de log de sortie
    #     format_vector : format du fichier vecteur. Optionnel, par default : 'ESRI Shapefile'
    #     save_results_intermediate : fichiers de sorties intermediaires nettoyees, par defaut = False
    #     overwrite : écrase si un fichier existant a le même nom qu'un fichier de sortie, par defaut a True
    #
    # SORTIES DE LA FONCTION :
    #     na
    #
    """

    # Mise à jour du Log
    starting_event = "cutPolygonesByLines_Postgis() : Cuting polygons by lines  starting : "
    timeLine(path_time_log,starting_event)

    if debug >= 4:
        print(bold + green + "cutPolygonesByLines_Postgis() : Variables dans la fonction" + endC)
        print(cyan + "cutPolygonesByLines_Postgis() : " + endC + "vector_lines_input : " + str(vector_lines_input) + endC)
        print(cyan + "cutPolygonesByLines_Postgis() : " + endC + "vector_poly_input : " + str(vector_poly_input) + endC)
        print(cyan + "cutPolygonesByLines_Postgis() : " + endC + "vector_poly_output : " + str(vector_poly_output) + endC)
        print(cyan + "cutPolygonesByLines_Postgis() : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "cutPolygonesByLines_Postgis() : " + endC + "project_encoding : " + str(project_encoding) + endC)
        print(cyan + "cutPolygonesByLines_Postgis() : " + endC + "server_postgis : " + str(server_postgis) + endC)
        print(cyan + "cutPolygonesByLines_Postgis() : " + endC + "port_number : " + str(port_number) + endC)
        print(cyan + "cutPolygonesByLines_Postgis() : " + endC + "user_postgis : " + str(user_postgis) + endC)
        print(cyan + "cutPolygonesByLines_Postgis() : " + endC + "password_postgis : " + str(password_postgis) + endC)
        print(cyan + "cutPolygonesByLines_Postgis() : " + endC + "database_postgis : " + str(database_postgis) + endC)
        print(cyan + "cutPolygonesByLines_Postgis() : " + endC + "schema_postgis : " + str(schema_postgis) + endC)
        print(cyan + "cutPolygonesByLines_Postgis() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "cutPolygonesByLines_Postgis() : " + endC + "path_time_log : " + str(format_vector) + endC)
        print(cyan + "cutPolygonesByLines_Postgis() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "cutPolygonesByLines_Postgis() : " + endC + "overwrite : " + str(overwrite) + endC)

    # Création de la base de données
    input_lignes_table=  os.path.splitext(os.path.basename(vector_lines_input))[0].lower()
    input_polygons_table =  os.path.splitext(os.path.basename(vector_poly_input))[0].lower()
    output_polygones_table =  os.path.splitext(os.path.basename(vector_poly_output))[0].lower()
    createDatabase(database_postgis, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number))

    # Import du fichier vecteur lines dans la base
    importVectorByOgr2ogr(database_postgis, vector_lines_input, input_lignes_table, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema_name=schema_postgis, epsg=str(epsg), codage=project_encoding)

    # Import du fichier vecteur polygones dans la base
    importVectorByOgr2ogr(database_postgis, vector_poly_input, input_polygons_table, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema_name=schema_postgis, epsg=str(epsg), codage=project_encoding)

    # Connexion à la base SQL postgis
    connection = openConnection(database_postgis, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema_name=schema_postgis)

    # Decoupage des polgones
    cutPolygonesByLines(connection, input_polygons_table, input_lignes_table, output_polygones_table, geom_field='geom')

    # Déconnexion de la base de données, pour éviter les conflits d'accès
    closeConnection(connection)

    # Récupération de la base du fichier vecteur de sortie
    exportVectorByOgr2ogr(database_postgis, vector_poly_output, output_polygones_table, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema_name=schema_postgis, format_type=format_vector)

    # Suppression des fichiers intermédiaires
    if not save_results_intermediate:
        try :
            dropDatabase(database_postgis, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number))
        except :
            print(cyan + "cutPolygonesByLines_Postgis() : " + bold + yellow + "Attention impossible de supprimer la base de donnée : " + endC + database_postgis)

    # Mise à jour du Log
    ending_event = "cutPolygonesByLines_Postgis() : Cuting polygons by lines ending : "
    timeLine(path_time_log,ending_event)

    return

###########################################################################################################################################
# FONCTION cutPolygonesByLines_Pandas()                                                                                                   #
###########################################################################################################################################
def cutPolygonesByLines_Pandas(vector_lines_input, vector_poly_input, vector_poly_output, epsg, path_time_log, format_vector, save_results_intermediate=False, overwrite=True) :
    """
    # ROLE:
    #     Découper des polygones ou multi-polygones par des lignes ou multi-lignes en traitement sous postgis
    #
    # ENTREES DE LA FONCTION :
    #     vector_lines_input: le vecteur de lignes de découpe d'entrée
    #     vector_poly_input: le vecteur de polygones à découpés d'entrée
    #     vector_poly_output: le vecteur e polygones de sortie découpés
    #     epsg : EPSG code de projection
    #     path_time_log : le fichier de log de sortie
    #     format_vector : format du fichier vecteur. Optionnel, par default : 'ESRI Shapefile'
    #     save_results_intermediate : fichiers de sorties intermediaires nettoyees, par defaut = False
    #     overwrite : écrase si un fichier existant a le même nom qu'un fichier de sortie, par defaut a True
    #
    # SORTIES DE LA FONCTION :
    #     na
    #
    """
    SUFFIX_DIFF = "_diff"

    # Mise à jour du Log
    starting_event = "cutPolygonesByLines_Pandas() : Cuting polygons by lines  starting : "
    timeLine(path_time_log,starting_event)

    # Transformer les fichiers d'entrées en dataframe
    gdf_roads_line_filter = gpd.read_file(vector_lines_input)
    gdf_segmentation = gpd.read_file(vector_poly_input)

    # Bufferiser les ligne pour avoir des polygones très fin
    gdf_roads_line_filter_buf = gdf_roads_line_filter.copy()
    gdf_roads_line_filter_buf['geometry'] = gdf_roads_line_filter_buf.buffer(distance=0.00001)

    # Decoupage des polygones de segmentation avec les polygones très fin (presque lignes)
    gdf_seg_diff = gpd.overlay(gdf_segmentation, gdf_roads_line_filter_buf, how='difference', keep_geom_type=True)

    # Nettoyage des ring dans les polygones
    gdf_seg_diff['geometry'] = gdf_seg_diff['geometry'].apply(removeRing)
    gdf_seg_diff_explode = gdf_seg_diff.explode(index_parts=True)
    gdf_seg_diff_explode['geometry'] = gdf_seg_diff_explode.buffer(distance=0.00002)
    #gdf_seg_diff_explode['geometry'] = gdf_seg_diff_explode['geometry'].buffer(0)
    gdf_seg_diff_explode_clean = gdf_seg_diff_explode[(gdf_seg_diff_explode["geometry"].geom_type == 'Polygon') | (gdf_seg_diff_explode["geometry"].geom_type == 'MultiPolygon')]

    # Appliquer l'opération difference pour chaque paire de polygones qui se chevauchent
    for i, polygon1 in gdf_seg_diff_explode_clean.iterrows():
        polygon1['geometry'] = polygon1['geometry'].buffer(0)
        for j, polygon2 in gdf_seg_diff_explode_clean.iterrows():
            # Vérifier si les polygones se chevauchent et ne sont pas les mêmes
            polygon2['geometry'] = polygon2['geometry'].buffer(0)
            if polygon1['geometry'].is_valid and polygon2['geometry'].is_valid :
                try :
                    if i != j and polygon1['geometry'].intersects(polygon2['geometry']):
                        # Obtenir la différence entre les polygones
                        difference_geometry = polygon1['geometry'].difference(polygon2['geometry'])
                        # Mettre à jour la géométrie du polygone d'origine
                        gdf_seg_diff_explode_clean.at[i, 'geometry'] = difference_geometry
                except Exception:
                    pass # Pass car TopologyException : This can occur if the input geometry is invalid.

    # Filtrer les geometries non-polygons
    gdf_seg_diff_explode_clean = gdf_seg_diff_explode_clean[gdf_seg_diff_explode_clean['geometry'].apply(lambda geom: geom.geom_type in ['Polygon','MultiPolygon'])]

    # Sauvegarde vecteur polygones découpé
    vector_seg_diff_explode_tmp = os.path.splitext(vector_poly_output)[0] + SUFFIX_DIFF + os.path.splitext(vector_poly_output)[1]
    gdf_seg_diff_explode_clean.to_file(vector_seg_diff_explode_tmp, driver=format_vector, crs="EPSG:" + str(epsg))
    deleteFieldsVector(vector_seg_diff_explode_tmp, vector_poly_output, ['level_0', 'level_1'], format_vector)
    if os.path.isfile(vector_seg_diff_explode_tmp):
        removeVectorFile(vector_seg_diff_explode_tmp, format_vector)
    if debug >= 1:
        print(cyan + "cutPolygonesByLines_Pandas() : " + endC + "Découpage des polygones par les lignes fichier de sortie :", vector_poly_output)

    # Mise à jour du Log
    ending_event = "cutPolygonesByLines_Pandas() : Cuting polygons by lines ending : "
    timeLine(path_time_log,ending_event)

    return

###########################################################################################################################################
# FUNCTION unionSegRoads()                                                                                                                #
###########################################################################################################################################
def unionSegRoads(path_folder_union_roads, vector_all_roads_input, vector_seg_input, vector_seg_roads_output, vector_line_skeleton_main_roads_output, field_fid, field_org_fid, road_importance_field="IMPORTANCE", road_importance_threshold=4, buffer_size=35.0, epsg=2154, server_postgis="localhost", port_number=5432, user_postgis="postgres", password_postgis="postgres", database_postgis="cutbylines", schema_postgis="public", format_vector='ESRI Shapefile', extension_vector=".shp", save_results_intermediate=False, overwrite=True):
    """
    # ROLE:
    #     Union des segmentations de route (vecteurs).
    #
    # PARAMETERS:
    #     path_folder_union_roads : répertoire de travail local.
    #     vector_all_roads_input : fichier vecteur d'entrées contenant toutes les routes.
    #     vector_seg_input : fichier vecteur d'entrées contenant la segmentation.
    #     vector_seg_roads_output : fichier vecteur de sortie contenant la segmentation découpée par les routes.
    #     vector_line_skeleton_main_roads_output : fichier vecteur de sortie contenant le squelette des routes principales.
    #     field_fid :  nom du champs contenat l'id.
    #     field_org_fid: nom du champs contenat l'orgine ava,t decoupage de l'id du polygone.
    #     road_importance_field : champs importance des routes (par defaut : "IMPORTANCE").
    #     road_importance_threshold : valeur du seuil d'importance (par défaut : 4).
    #     buffer_size : taille du buffer (par défaut :35.0).
    #     epsg (int): EPSG code of the desired projection (default is 2154).
    #     server_postgis : nom du serveur postgis
    #     port_number : numéro du port pour le serveur postgis
    #     user_postgis : le nom de l'utilisateurs postgis
    #     password_postgis : le mot de passe de l'utilisateur postgis
    #     database_postgis : le nom de la base postgis à utiliser
    #     schema_postgis : le nom du schéma à utiliser
    #     format_vector : format du fichier vecteur de sortie
    #     extension_vector : extension du fichier vecteur de sortie, par defaut = '.shp'
    #     save_results_intermediate : fichiers de sorties intermediaires non nettoyées, par defaut = False
    #     overwrite : supprime ou non les fichiers existants ayant le meme nom
    # RETURNS:
    #     NA
    """

    # Constantes repertoires temporaires
    if debug >= 4:
        FOLDER_FILTER_BUF = "filter_buf"

    # Constantes
    SUFFIX_BUF = "_buf"
    SUFFIX_POLY = "_poly"
    SUFFIX_ERODE = "_erode"

    if debug >= 1:
        print(cyan + "unionSegRoads() : " + endC + "Union of segmentation result with main roads...")

    # Creation des répertoires
    if debug >= 4:
        path_folder_union_roads_buf = path_folder_union_roads + os.sep + FOLDER_FILTER_BUF
        if not os.path.exists(path_folder_union_roads_buf):
            os.makedirs(path_folder_union_roads_buf)

    # Get main roads according to an importance threshold and buffer roads (linestrings to polygons)
    gdf_roads = gpd.read_file(vector_all_roads_input)

    # Remove no data value in column modify if needed depending on data
    gdf_roads[road_importance_field] = gdf_roads[road_importance_field].replace("NC", 6).astype(int)

    # Get roads with road_importance_field <= road_importance_threshold
    gdf_roads_select = gdf_roads[gdf_roads[road_importance_field] <= road_importance_threshold]

    # Delete incorrect geometries which are neither LineString or MultiLineString
    if debug >= 4:
        print(cyan + "unionSegRoads() : " + endC + "length before: {}".format(len(gdf_roads)))
        print(cyan + "unionSegRoads() : " + endC + "length after {}".format(len(gdf_roads_select)))
        print(cyan + "unionSegRoads() : " + endC + "unique values: {}".format(gdf_roads["geometry"].geom_type.unique()))

    gdf_roads_select_clean = gdf_roads_select[(gdf_roads_select["geometry"].geom_type == 'LineString') | (gdf_roads_select["geometry"].geom_type == 'MultiLineString')]

    if debug >= 1:
        print(cyan + "unionSegRoads() : " + endC + "Nettoyage du vecteur route d'entrée : ", vector_all_roads_input)

    # Create buffers around the lines --> polygons
    buffer_size_line = 0.25
    gdf_roads_buf = bufferPolylinesToPolygons(gdf_roads_select_clean, buffer_size_line)

    if debug >= 4:
        # To file
        s_road_importance_threshold = str(road_importance_threshold).replace(".", "f")
        s_buffer_size = str(buffer_size_line).replace(".", "f")
        vector_roads_filter_buf = path_folder_union_roads_buf + os.sep + os.path.splitext(os.path.basename(vector_all_roads_input))[0] + "_" + road_importance_field[:3] + s_road_importance_threshold + SUFFIX_BUF + s_buffer_size + extension_vector
        gdf_roads_buf.to_file(vector_roads_filter_buf, driver=format_vector, crs="EPSG:" + str(epsg))
        print(cyan + "unionSegRoads() : " + endC + "Sortie fichier vector_roads_filter_buf : ", vector_roads_filter_buf)

    # Create Buffer to polygon and fusion polygon
    gdf_roads_buf_poly = gdf_roads_buf.buffer(distance=buffer_size, resolution=0, cap_style=2)
    gdf_roads_buf_poly_union = gpd.GeoDataFrame(geometry=[gdf_roads_buf_poly.unary_union], crs=gdf_roads_buf_poly.crs)
    if debug >= 4:
        vector_roads_filter_buf_poly = path_folder_union_roads_buf + os.sep + os.path.splitext(os.path.basename(vector_all_roads_input))[0] + "_" + road_importance_field[:3] + SUFFIX_BUF + SUFFIX_POLY + extension_vector
        gdf_roads_buf_poly_union.to_file(vector_roads_filter_buf_poly, driver=format_vector, crs="EPSG:" + str(epsg))
        print(cyan + "unionSegRoads() : " + endC + "Sortie fichier vector_roads_filter_buf_poly : ", vector_roads_filter_buf_poly)

    if debug >= 1:
        print(cyan + "unionSegRoads() : " + endC + "Buffer du vecteur route nettoyé : ", vector_all_roads_input)

    # Create the squelette line into buffer_polygon
    gdf_roads_buf_poly_line = gdf_roads_buf_poly_union.copy(deep=True)
    gdf_roads_buf_poly_line['geometry'] = gdf_roads_buf_poly_line['geometry'].simplify(tolerance=10, preserve_topology=True)
    gdf_roads_buf_poly_line['geometry'] = gdf_roads_buf_poly_line['geometry'].apply(lambda geom: Centerline(geom, interpolation_distance=5).geometry)
    gdf_roads_line = gpd.GeoDataFrame(gdf_roads_buf_poly_line, crs="EPSG:" + str(epsg), geometry="geometry")

    if debug >= 4:
        vector_roads_line = path_folder_union_roads_buf + os.sep + os.path.splitext(os.path.basename(vector_all_roads_input))[0] + "_" + road_importance_field[:3] + extension_vector
        gdf_roads_line.to_file(vector_roads_line, driver=format_vector, crs="EPSG:" + str(epsg))
        print(cyan + "unionSegRoads() : " + endC + "Sortie fichier vector_roads_line : ", vector_roads_line)

    if debug >= 1:
        print(cyan + "unionSegRoads() : " + endC + "Squelette du buffer route : ", vector_all_roads_input)

    # Create buffer_polygon erode to decrease zone into squelette line
    gdf_roads_buf_poly_erode = gdf_roads_buf_poly_union.copy(deep=True)
    gdf_roads_buf_poly_erode['geometry'] = gdf_roads_buf_poly_erode['geometry'].buffer(distance=((-1 * buffer_size) + 10.0), cap_style=3)
    if debug >= 4:
        vector_roads_filter_buf_erode = path_folder_union_roads_buf + os.sep + os.path.splitext(os.path.basename(vector_all_roads_input))[0] + "_" + road_importance_field[:3] + SUFFIX_BUF + SUFFIX_ERODE + extension_vector
        gdf_roads_buf_poly_erode.to_file(vector_roads_filter_buf_erode, driver=format_vector, crs="EPSG:" + str(epsg))
        print(cyan + "unionSegRoads() : " + endC + "Sortie fichier vector_roads_filter_buf_erode : ", vector_roads_filter_buf_erode)

    # Filter only squelette line into buffer_polygon erode
    gdf_roads_line_clean = gdf_roads_line[(gdf_roads_line["geometry"].geom_type == 'LineString') | (gdf_roads_line["geometry"].geom_type == 'MultiLineString')]
    gdf_roads_buf_poly_erode_clean = gdf_roads_buf_poly_erode[(gdf_roads_buf_poly_erode["geometry"].geom_type == 'Polygon') | (gdf_roads_buf_poly_erode["geometry"].geom_type == 'MultiPolygon')]
    gdf_roads_line_filter = explodeMultiGdf(gdf_roads_line_clean, field_fid)
    gdf_roads_line_filter['check'] =  gdf_roads_line_filter['geometry'].apply(lambda geom: geom.within(gdf_roads_buf_poly_erode_clean['geometry']))
    gdf_roads_line_filter = gdf_roads_line_filter[gdf_roads_line_filter.check ==1]

    # Sauvegarde du lineaires routes principales fusionées et filtrées
    gdf_roads_line_filter.to_file(vector_line_skeleton_main_roads_output, driver=format_vector, crs="EPSG:" + str(epsg))
    if debug >= 1:
        print(cyan + "unionSegRoads() : " + endC + "Nettoyage du squelette route fichier de sortie : ", vector_line_skeleton_main_roads_output)

    # Decoupage des polygones de segmentation avec les routes principales
    ##cutPolygonesByLines_Pandas(vector_line_skeleton_main_roads_output, vector_seg_input, vector_seg_roads_output, epsg, "", format_vector, save_results_intermediate, overwrite)
    cutPolygonesByLines_Postgis(vector_line_skeleton_main_roads_output, vector_seg_input, vector_seg_roads_output, epsg, "UTF-8", server_postgis, port_number, user_postgis, password_postgis, database_postgis, schema_postgis, "", format_vector, save_results_intermediate=False, overwrite=True)

    # Pour les polygones découpés par les routes principales garder l'id du polygone d'origine
    attribute_fid_type = ogr.OFTInteger64
    renameFieldsVector(vector_seg_roads_output, [field_fid.lower()] , [field_org_fid], format_vector)
    addNewFieldVector(vector_seg_roads_output, field_fid, attribute_fid_type, None, None, None, format_vector)
    updateIndexVector(vector_seg_roads_output, field_fid, format_vector)
    """
    attribute_fid_type = getAttributeType(vector_seg_roads_output, field_fid, format_vector)
    attribute_name_dico = {}
    attribute_name_dico[field_fid] = attribute_fid_type
    fid_values_dico = getAttributeValues(vector_seg_roads_output, None, None, attribute_name_dico, format_vector)

    # Préparation des donnees
    field_new_values_list = []
    for val in fid_values_dico[field_fid]:
        val_attr_dico = {}
        val_attr_dico[field_org_fid] = val
        field_new_values_list.append(val_attr_dico)
    addNewFieldVector(vector_seg_roads_output, field_org_fid, attribute_fid_type, None, None, None, format_vector)
    setAttributeValuesList(vector_seg_roads_output, field_new_values_list, format_vector)
    """

    if debug >= 1:
        print(cyan + "unionSegRoads() : " + endC + "Résultat de la segmentation en polygones par le decoupage des routes fichier de sortie :", vector_seg_roads_output)

    # Supression des repertoirtes temporaires
    if not save_results_intermediate :
        if debug >= 4:
            if os.path.exists(path_folder_union_roads_buf):
                deleteDir(path_folder_union_roads_buf)
    return

###########################################################################################################################################
# FUNCTION indentifieSegmentationRoad()                                                                                                   #
###########################################################################################################################################
def indentifieSegmentationRoad(vector_line_skeleton_main_roads_input, vector_seg_input, vector_seg_crossroad_output, field_is_road, epsg=2154, format_vector='ESRI Shapefile') :
    """
    # ROLE:
    #     Identifer les polygones traversés par les routes mise à jour de la colonne "is_road".
    #
    # PARAMETERS:
    #     vector_line_skeleton_main_roads_input : vecteur du squelette des route tres légerement bufferisé d'entrée.
    #     vector_seg_input : fichier de segmentation d'entrée.
    #     vector_seg_crossroad_output : vecteur de segmentation ave l'information "is_road" de sortie.
    #     field_is_road :  nom du champs boolean contenat l'information si le polygone est traversé par une route ou non.
    #     epsg (int): EPSG code of the desired projection (default is 2154).
    #     format_vector : format du fichier vecteur de sortie
    # RETURNS:
    #     NA.
    """

    # Chargement des données
    gdf_roads_line_filter = gpd.read_file(vector_line_skeleton_main_roads_input)
    gdf_seg_tag_roads = gpd.read_file(vector_seg_input)
    gdf_seg_tag_roads['geometry'] = gdf_seg_tag_roads['geometry'].buffer(0)

    # Bufferiser les ligne pour avoir des polygones très fin
    gdf_roads_line_filter_buf = gdf_roads_line_filter.copy()
    gdf_roads_line_filter_buf['geometry'] = gdf_roads_line_filter_buf.buffer(distance=0.00001)

    # Application de la fonction calculateIntersects à la colonne 'geometry'
    gdf_seg_tag_roads[field_is_road] = gdf_seg_tag_roads.intersects(gdf_roads_line_filter_buf.unary_union)

    # Sauvegarde dans un fichier shape
    gdf_seg_tag_roads.to_file(vector_seg_crossroad_output, driver=format_vector, crs="EPSG:" + str(epsg))

    if debug >= 1:
        print(cyan + "indentifieSegmentationRoad() : " + endC + "Identification des polygones de la segmentation traversés par les routes fichier de sortie :", vector_seg_crossroad_output)

    return

###########################################################################################################################################
# FUNCTION removeWaterSurfacesSeg()                                                                                                       #
###########################################################################################################################################
def removeWaterSurfacesSeg(vector_seg_input, vector_water_area_input, vector_seg_clean_water, field_fid, field_area, min_area_water_area=50000, epsg=2154, format_vector='ESRI Shapefile', extension_vector='.shp'):
    """
    # ROLE:
    #     Nettoyage des segmentations des surfaces d'eau.
    #
    # PARAMETERS:
    #     vector_seg_input : fichier de segmentation d'entrée.
    #     vector_water_area_input : vecteur d'entrée surface en eau.
    #     vector_seg_clean_water : vecteur de segmentation nettoyer des surface d'eau de sortie.
    #     field_fid :  nom du champs contenat l'id.
    #     field_area : le champs de surface à filter par min_area_polygon
    #     min_area_water_area : seuil minimun de surface d'eau (par défaut : 50000).
    #     epsg (int): EPSG code of the desired projection (default is 2154).
    #     format_vector : format du fichier vecteur de sortie
    #     extension_vector : extension du fichier vecteur de sortie, par defaut = '.shp'
    # RETURNS:
    #     NA.
    """

    # Constantes
    SUFFIX_CLEAN = "_clean"

    if debug >= 1:
        print(cyan + "removeWaterSurfacesSeg() : " + endC + "Removing main water surface area from segmentation file...")

    # Remove small geometries from water surface file
    vector_water_area_clean = os.path.dirname(vector_water_area_input) + os.sep + os.path.splitext(os.path.basename(vector_water_area_input))[0] + SUFFIX_CLEAN + extension_vector
    gdf_water_area_clean = calculateAndCleanSmallPolygonArea(vector_water_area_input, vector_water_area_clean, field_area, min_area_water_area, epsg, format_vector)

    # Apply difference between segmentation shpfile and clean water surface shapfile
    ##gdf_water_area_clean = gpd.read_file(vector_water_area_clean)
    gdf_seg_out = gpd.read_file(vector_seg_input)
    gdf_seg_seg_clean_water_area = gpd.overlay(gdf_seg_out, gdf_water_area_clean, how='difference', keep_geom_type=True)

    if debug >= 1:
        print(cyan + "removeWaterSurfacesSeg() : " + endC + "main water surface area removed from segmentation file to {}\n".format(vector_seg_clean_water))

    gdf_seg_poly_only = explodeMultiGdf(gdf_seg_seg_clean_water_area, field_fid)
    gdf_seg_poly_only.to_file(vector_seg_clean_water, driver=format_vector, crs="EPSG:" + str(epsg))
    if debug >= 1:
        print(cyan + "removeWaterSurfacesSeg() : " + endC + "segmentation vector clean water: Multipolygons --> simple polygons to {}\n".format(vector_seg_clean_water))

    return

###########################################################################################################################################
# FUNCTION segPostProcessing()                                                                                                            #
###########################################################################################################################################
def segPostProcessing(path_base_folder,  emprise_vector, vector_seg_input, vector_roads_input, vector_water_area_input, vector_seg_output, road_importance_field="IMPORTANCE", road_importance_threshold=4, buffer_size=35.0, min_area_water_area=50000, no_data_value=0, epsg=2154, server_postgis="localhost", port_number=5432, user_postgis="postgres", password_postgis="postgres", database_postgis="cutbylines", schema_postgis="public", format_raster="GTiff", format_vector='ESRI Shapefile', extension_raster=".tif", extension_vector=".shp", path_time_log = "", save_results_intermediate=False, overwrite=True):
    """
    # ROLE:
    #     Post Processing de la segmentation.
    #
    # PARAMETERS:
    #     path_base_folder : le dossier de travail.
    #     emprise_vector : fichier d'emprise.
    #     vector_seg_input : le fichier vecteur de segmentation d'entrée.
    #     vector_roads_input : fichier contenant toutes les routes d'entrée.
    #     vector_water_area_input : fichier contenant les surfaces en eau d'entrée.
    #     vector_seg_output : le fichier vecteur de segmentation de sortie
    #     road_importance_field : champs importance des routes (par defaut : "IMPORTANCE").
    #     road_importance_threshold : valeur du seuil d'importance (par défaut : 4).
    #     buffer_size : taille du buffer (par défaut : 35.0).
    #     min_area_water_area : seuil minimun de surface d'eau (par défaut : 50000).
    #     no_data_value : Option : Value pixel of no data (par défaut : 0).
    #     epsg (int): EPSG code of the desired projection (default is 2154).
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
        print(bold + green + "Variables dans le segPostProcessing - Variables générales" + endC)
        print(cyan + "segPostProcessing() : " + endC + "path_base_folder : " + str(path_base_folder))
        print(cyan + "segPostProcessing() : " + endC + "emprise_vector : " + str(emprise_vector))
        print(cyan + "segPostProcessing() : " + endC + "vector_roads_input : " + str(vector_roads_input))
        print(cyan + "segPostProcessing() : " + endC + "vector_water_area_input : " + str(vector_water_area_input))
        print(cyan + "segPostProcessing() : " + endC + "vector_seg_output : " + str(vector_seg_output))
        print(cyan + "segPostProcessing() : " + endC + "road_importance_field : " + str(road_importance_field))
        print(cyan + "segPostProcessing() : " + endC + "road_importance_threshold : " + str(road_importance_threshold))
        print(cyan + "segPostProcessing() : " + endC + "buffer_size : " + str(buffer_size))
        print(cyan + "segPostProcessing() : " + endC + "min_area_water_area : " + str(min_area_water_area))
        print(cyan + "segPostProcessing() : " + endC + "no_data_value : " + str(no_data_value))
        print(cyan + "segPostProcessing() : " + endC + "epsg : " + str(epsg))
        print(cyan + "segPostProcessing() : " + endC + "server_postgis : " + str(server_postgis) + endC)
        print(cyan + "segPostProcessing() : " + endC + "port_number : " + str(port_number) + endC)
        print(cyan + "segPostProcessing() : " + endC + "user_postgis : " + str(user_postgis) + endC)
        print(cyan + "segPostProcessing() : " + endC + "password_postgis : " + str(password_postgis) + endC)
        print(cyan + "segPostProcessing() : " + endC + "database_postgis : " + str(database_postgis) + endC)
        print(cyan + "segPostProcessing() : " + endC + "schema_postgis : " + str(schema_postgis) + endC)
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
    FOLDER_UNION_ROADS = "union_roads"

    FOLDER_INPUT_DATA = "input_data"
    FOLDER_OUTPUT_SEG = "output_seg"
    FOLDER_WATER_SURFACE = "water_area"
    FOLDER_ROAD_WIDTH = "road_width"
    FOLDER_BUILT = "built"
    FOLDER_EMPRISE = "emprise"
    FOLDER_HEIGHT = "height"

    # Constantes
    SUFFIX_CUT = "_cut"
    SUFFIX_EMPRISE = "_emprise"
    SUFFIX_ROADS = "_roads"
    SUFFIX_WATERCLEAN = "_water_clean"
    SUFFIX_CROSS_ROADS = "_cross_road"
    SUFFIX_RES = "_res"
    SUFFIX_HAUTEUR = "_hauteur"
    SUFFIX_LINE = "_line"
    SUFFIX_FILTER = "_filter"

    FIELD_FID = "FID"
    FIELD_IS_ROAD = "is_road"
    FIELD_AREA = "area"
    FIELD_ORG_FID = "org_id"

    # Creation des répertoires
    path_folder_postprocess = path_base_folder + os.sep + FOLDER_POSTPROCESSING
    if not os.path.exists(path_folder_postprocess):
        os.makedirs(path_folder_postprocess)

    path_folder_union_roads = path_folder_postprocess + os.sep + FOLDER_UNION_ROADS
    if not os.path.exists(path_folder_union_roads):
        os.makedirs(path_folder_union_roads)

    path_folder_input = path_folder_postprocess + os.sep + FOLDER_INPUT
    if not os.path.exists(path_folder_input):
        os.makedirs(path_folder_input)

    path_folder_local_emprise = path_folder_input + os.sep + FOLDER_EMPRISE
    if not os.path.exists(path_folder_local_emprise):
        os.makedirs(path_folder_local_emprise)

    path_folder_seg_output = path_folder_input + os.sep + FOLDER_OUTPUT_SEG
    if not os.path.exists(path_folder_seg_output):
        os.makedirs(path_folder_seg_output)

    path_folder_seg_input = path_folder_input + os.sep + FOLDER_INPUT_DATA
    if not os.path.exists(path_folder_seg_input):
        os.makedirs(path_folder_seg_input)

    path_folder_road_width = path_folder_input + os.sep + FOLDER_ROAD_WIDTH
    if not os.path.exists(path_folder_road_width):
        os.makedirs(path_folder_road_width)

    path_folder_water = path_folder_input + os.sep + FOLDER_WATER_SURFACE
    if not os.path.exists(path_folder_water):
        os.makedirs(path_folder_water)

    path_folder_batis = path_folder_input + os.sep + FOLDER_BUILT
    if not os.path.exists(path_folder_batis):
        os.makedirs(path_folder_batis)

    path_folder_height = path_folder_batis + os.sep + FOLDER_HEIGHT
    if not os.path.exists(path_folder_height):
        os.makedirs(path_folder_height)

    # Redefinition de l'emprise local avec le fichier vecteur segmentation d'entrée
    xmin_seg, xmax_seg, ymin_seg, ymax_seg = getEmpriseVector(vector_seg_input)
    vector_local_emprise_output = path_folder_local_emprise + os.sep + os.path.splitext(os.path.basename(vector_seg_input))[0] + SUFFIX_EMPRISE + extension_vector
    createEmpriseVector(xmin_seg, ymin_seg, xmax_seg, ymax_seg, vector_local_emprise_output, epsg, format_vector)

    # Recoupage du vecteur route d'entrée sur l'emprise local
    vector_roads_cut = path_folder_road_width + os.sep + os.path.splitext(os.path.basename(vector_roads_input))[0] + SUFFIX_CUT + extension_vector
    cutVectorAll(vector_local_emprise_output, vector_roads_input, vector_roads_cut)

    # Union segmentation output file with roads simplification des routes principales via le squelette
    vector_seg_road = path_folder_union_roads + os.sep + os.path.splitext(os.path.basename(vector_seg_input))[0] + SUFFIX_CUT + SUFFIX_ROADS + extension_vector
    vector_line_skeleton_main_roads_output = path_folder_union_roads + os.sep + os.path.splitext(os.path.basename(vector_roads_input))[0] + "_" + road_importance_field[:3] + SUFFIX_LINE + SUFFIX_FILTER +  extension_vector

    unionSegRoads(path_folder_union_roads, vector_roads_cut, vector_seg_input, vector_seg_road, vector_line_skeleton_main_roads_output, FIELD_FID, FIELD_ORG_FID, road_importance_field, road_importance_threshold, buffer_size, epsg, server_postgis, port_number, user_postgis, password_postgis, database_postgis, schema_postgis, format_vector, extension_vector, save_results_intermediate, overwrite)

    # Decoupage de la donnée eau sur l'emprise de l'étude
    vector_water_area_cut = path_folder_water + os.sep + os.path.splitext(os.path.basename(vector_water_area_input))[0] + SUFFIX_CUT + extension_vector
    cutVectorAll(emprise_vector, vector_water_area_input, vector_water_area_cut)

    # Nettoyage des segmentations des surfaces d'eau
    vector_seg_clean_water = path_folder_seg_output + os.sep + os.path.splitext(os.path.basename(vector_seg_input))[0] + SUFFIX_WATERCLEAN + extension_vector
    removeWaterSurfacesSeg(vector_seg_road, vector_water_area_cut, vector_seg_clean_water, FIELD_FID, FIELD_AREA, min_area_water_area, epsg, format_vector, extension_vector)

    # Identification des polygones decoupés par les routes
    vector_seg_id_input = path_folder_seg_output + os.sep + os.path.splitext(os.path.basename(vector_seg_input))[0] + SUFFIX_CROSS_ROADS + extension_vector
    indentifieSegmentationRoad(vector_line_skeleton_main_roads_output, vector_seg_clean_water, vector_seg_id_input, FIELD_IS_ROAD, epsg, format_vector)

    # calcul de de la surface et du nombre de points
    THRESHOLD_VERY_SMALL_AREA = 0.01
    gdf_seg_input = gpd.read_file(vector_seg_id_input)
    gdf_seg_input = computePolygonAreas(gdf_seg_input, geometry_column="geometry", area_col_name="area")

    # Suppression des sufarces de polygones vraiment trop petites
    gdf_seg_input = gdf_seg_input[gdf_seg_input['area'] > THRESHOLD_VERY_SMALL_AREA].copy()
    #gdf_seg_input.drop(gdf_seg_input[gdf_seg_input['area'] <= THRESHOLD_VERY_SMALL_AREA].index, inplace=True)
    gdf_seg_input.to_file(vector_seg_output, driver=format_vector, crs="EPSG:" + str(epsg))

    if debug >= 1:
        print(cyan + "segPostProcessing() : " + endC + "Fin resulat segementation découpé par les routes principales sans les sufaces d'eau {}\n".format(vector_seg_output))

    # Supression des repertoirtes temporaires
    if not save_results_intermediate :
        if os.path.exists(path_folder_input):
            deleteDir(path_folder_input)

    return

# ==================================================================================================================================================

if __name__ == '__main__':

    ##### paramètres en entrées #####
    # Il est recommandé de prendre un répertoire avec accès rapide en lecture et écriture pour accélérer les traitements
    BASE_FOLDER = "/mnt/RAM_disk/INTEGRATION"
    emprise_vector =  "/mnt/RAM_disk/INTEGRATION/emprise/Emprise_Toulouse_Metropole.shp"
    vector_roads_input = "/mnt/RAM_disk/INTEGRATION/create_data/result/all_roads.shp"
    vector_water_area_input = "/mnt/RAM_disk/INTEGRATION/bd_topo/N_SURFACE_EAU_BDT_031.shp"
    vector_seg_input = "/mnt/RAM_disk/INTEGRATION/ccm/result/segmentation_result.shp"
    vector_seg_output = "/mnt/RAM_disk/INTEGRATION/seg_post_processing/toulouse_rgb_output_seg_res5.shp"

    # Exec
    segPostProcessing(
        path_base_folder = BASE_FOLDER,
        emprise_vector = emprise_vector,
        vector_seg_input = vector_seg_input,
        vector_roads_input = vector_roads_input,
        vector_water_area_input = vector_water_area_input,
        vector_seg_output = vector_seg_output,
        road_importance_field="IMPORTANCE",
        road_importance_threshold=4,
        buffer_size=35.0,
        min_area_water_area=50000,
        no_data_value=0,
        epsg=2154,
        server_postgis = "localhost",
        port_number = 5432,
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
