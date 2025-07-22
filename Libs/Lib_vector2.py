#! /usr/bin/python
# -*- coding: utf-8 -*-

#############################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.               #
#############################################################################

#############################################################################
#                                                                           #
# FONCTIONS DE EVOLUEES SUR LES VECTEURS (Traitement en GeoPandas)          #
#                                                                           #
#############################################################################


from __future__ import print_function
import sys,os,glob
import pandas as pd
import geopandas as gpd
from shapely.geometry import MultiLineString, LineString, MultiPolygon, Polygon, box, GeometryCollection, Point
from shapely.strtree import STRtree
from shapely.ops import unary_union, split, linemerge
from joblib import Parallel, delayed
from Lib_operator import *
from Lib_log import timeLine
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC
from Lib_file import renameVectorFile, removeVectorFile, removeFile

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 3 : affichage maximum de commentaires lors de l'execution du script. Intermédiaire : affichage intermédiaire
debug = 2

########################################################################
# FONCTION reduce_line()                                               #
########################################################################
def reduce_line(line, length):
    """
    Réduire l'extrémité d'une ligne.
    """
    if not isinstance(line, LineString):
        raise TypeError(cyan + "reduce_line() : " + bold + red +"Expected a LineString geometry" + endC)

    # Vérifier si la ligne a au moins deux points
    if len(line.coords) < 2:
        return line

    # Définition des points de départ et d'arrivée
    start_point = line.coords[0]
    end_point = line.coords[-1]

    # Calculer les différences de coordonnées (direction de la ligne)
    dx_start = line.coords[1][0] - start_point[0]
    dy_start = line.coords[1][1] - start_point[1]
    dx_end = end_point[0] - line.coords[-2][0]
    dy_end = end_point[1] - line.coords[-2][1]

    # Calcul de la longueur des segments de départ et de fin
    start_length = (dx_start**2 + dy_start**2)**0.5
    end_length = (dx_end**2 + dy_end**2)**0.5

    # Vérifier si la ligne est trop courte pour être réduite
    total_length = line.length
    if total_length <= 2 * length:
        return LineString([line.interpolate(length), line.interpolate(total_length - length)])

    # Éviter la division par zéro
    if start_length == 0 or end_length == 0:
        return line

    # Calcul des nouveaux points raccourcis
    new_start = (start_point[0] + (dx_start / start_length) * length,
                 start_point[1] + (dy_start / start_length) * length)
    new_end = (end_point[0] - (dx_end / end_length) * length,
               end_point[1] - (dy_end / end_length) * length)

    # Création de la nouvelle ligne
    new_coords = [new_start] + list(line.coords[1:-1]) + [new_end]

    try:
        new_coords = [(x, y) for x, y, *rest in new_coords]  # Suppression des altitudes si présentes
        reduced_line = LineString(new_coords)
    except ValueError as e:
        print(cyan + "reduce_line() : " + bold + red + f"Failed to create LineString: {e}" + endC)
        return line

    return reduced_line

########################################################################
# FONCTION reduce_multiline()                                          #
########################################################################
def reduce_multiline(multiline, length):
    if not isinstance(multiline, MultiLineString):
        return multiline  # Retourner tel quel si ce n'est pas un MultiLineString
    reduced_lines = [reduce_line(line, length) for line in multiline.geoms]
    return MultiLineString(reduced_lines)

########################################################################
# FONCTION process_reduction_lines()                                   #
########################################################################
def process_reduction_lines(geom, reduction_length):
    if isinstance(geom, LineString):
        return reduce_line(geom, reduction_length)
    elif isinstance(geom, MultiLineString):
        return reduce_multiline(geom, reduction_length)
    return geom  # Retourne tel quel si ce n'est ni une ligne ni une multi-ligne

########################################################################
# FONCTION extend_line()                                               #
########################################################################
def extend_line(line, length):
    """
    Étend une ligne de type LineString en ajoutant un segment à ses extrémités.
    """
    if not isinstance(line, LineString):
        raise TypeError(cyan + "extend_line() : " + bold + red + "Expected a LineString geometry" + endC)

    start_point = line.coords[0]
    end_point = line.coords[-1]

    if len(line.coords) > 1:
        dx_start = line.coords[1][0] - start_point[0]
        dy_start = line.coords[1][1] - start_point[1]
        dx_end = end_point[0] - line.coords[-2][0]
        dy_end = end_point[1] - line.coords[-2][1]
    else:
        dx_start = dy_start = dx_end = dy_end = 0

    start_length = (dx_start**2 + dy_start**2)**0.5
    end_length = (dx_end**2 + dy_end**2)**0.5

    if start_length == 0 or end_length == 0:
        return line

    new_start = (start_point[0] - (dx_start / start_length) * length,
                 start_point[1] - (dy_start / start_length) * length)
    new_end = (end_point[0] + (dx_end / end_length) * length,
               end_point[1] + (dy_end / end_length) * length)

    new_coords = [new_start] + list(line.coords[1:-1]) + [new_end]

    try:
        new_coords = [(x, y) for x, y, *rest in new_coords]
        extended_line = LineString(new_coords)
    except ValueError as e:
        print(cyan + "extend_line() : " + bold + red + f"Failed to create LineString: {e}" + endC)
        return line

    return extended_line

########################################################################
# FONCTION extract_extension_part()                                    #
########################################################################
def extract_extension_part(extended_line, original_line, buffer_size=1e-9):
    """
    Renvoie uniquement les parties nouvellement ajoutées de la ligne étendue.
    """
    if not isinstance(original_line, LineString) or not isinstance(extended_line, LineString):
        return None

    # Étendre légèrement original_line avec un buffer pour éviter les résidus
    buffered_original = original_line.buffer(buffer_size)

    # Soustraire avec la version légèrement étendue
    extension_part = extended_line.difference(buffered_original)

    # Si l'extension reste vide après soustraction, retourner None
    if extension_part.is_empty:
        return None

    # Gérer le cas où on obtient plusieurs segments
    if isinstance(extension_part, MultiLineString):
        # Supprimer toute portion touchant encore l'original (vérification finale)
        filtered_parts = [line for line in extension_part.geoms if not line.intersects(original_line)]
        return MultiLineString(filtered_parts) if filtered_parts else None

    # Vérifier si l'extension restante touche encore `original_line`
    if extension_part.intersects(original_line):
        return None

    return extension_part

########################################################################
# FONCTION check_intersection_with_reference()                         #
########################################################################
def check_intersection_with_reference(extension_part, reference_lines, reference_index):
    """
    Vérifiez si la partie d'extension croise l'une des lignes de références.
    """
    if extension_part is None:
        return False

    bounding_box = box(*extension_part.bounds)
    possible_indices = reference_index.query(bounding_box)

    for idx in possible_indices:
        reference_line = reference_lines[idx]
        if isinstance(reference_line, (LineString, MultiLineString)):
            if extension_part.intersects(reference_line):
                return True

    return False

########################################################################
# FONCTION process_extension()                                         #
########################################################################
def process_extension(extension, segment_line, is_cut_extension, reference_lines, reference_index):
    """
    Traite une extension en la coupant avec les lignes de référence et en gardant le segment le plus proche.
    """
    if extension is None or not check_intersection_with_reference(extension, reference_lines, reference_index):
        return []

    if not is_cut_extension :
        return [extension]

    reference_union = unary_union(reference_lines)
    if extension.intersects(reference_union):
        extension_cut = extension.difference(reference_union)
    else:
        extension_cut = extension

    extension_split = split(extension_cut, reference_union)

    # Sélectionner le segment le plus proche
    if isinstance(extension_split, GeometryCollection):
        closest_segment = min(extension_split.geoms, key=lambda seg: seg.distance(segment_line))
    else:
        closest_segment = extension

    # Retourner les segments sous forme de liste
    if isinstance(closest_segment, MultiLineString):
        return list(closest_segment.geoms)
    else:
        return [closest_segment]

########################################################################
# FONCTION process_extend_segment()                                    #
########################################################################
def process_extend_segment(segment_line, length, is_cut_extension, reference_lines, reference_index):
    """
    Étend un segment et traite ses extensions.
    """
    extended_line = extend_line(segment_line, length)
    extension_part = extract_extension_part(extended_line, segment_line)

    segments_line_list = [segment_line]  # Toujours conserver le segment original

    if isinstance(extension_part, LineString):
        segments_line_list.extend(process_extension(extension_part, segment_line, is_cut_extension, reference_lines, reference_index))

    elif isinstance(extension_part, MultiLineString):
        for extension in extension_part.geoms:
            segments_line_list.extend(process_extension(extension, segment_line, is_cut_extension, reference_lines, reference_index))

    return segments_line_list

########################################################################
# FONCTION apply_extend_line_and_check_intersection()                  #
########################################################################
def apply_extend_line_and_check_intersection(segment_line, length, is_cut_extension, reference_lines, reference_index):
    """
    Applique l'extension aux segments, gère les intersections et retourne les nouvelles géométries.
    """
    if isinstance(segment_line, LineString):
        result_segments = process_extend_segment(segment_line, length, is_cut_extension, reference_lines, reference_index)
        return MultiLineString(result_segments)

    elif isinstance(segment_line, MultiLineString):
        extended_lines_list = []
        for line in segment_line.geoms:
            extended_lines_list.extend(process_extend_segment(line, length, is_cut_extension, reference_lines, reference_index))

        if extended_lines_list:
            return unary_union(extended_lines_list)  # Fusionner toutes les lignes étendues
        else:
            return segment_line

    return segment_line  # Si ce n'est ni LineString ni MultiLineString, on retour

########################################################################
# FONCTION extendLines()                                               #
########################################################################
def extendLines(vector_input, vector_output, vector_ref_input="", extension_length_lines=10, is_cut_extension=True, epsg=2154, format_vector='ESRI Shapefile'):
    """
    # Rôle : cette fonction permet d'etendre les extrémitées de lignes.
    # Paramètres en entrée :
    #       vector_input : vecteur d'entrée lignes, celui à qui on veut etendre les extrémitées des lignes
    #       vector_output : vecteur de sortie, resultat du traitement vector_input + les extensions de lignes jusqu'au croisement de lignes
    #       vector_ref_input : vecteur d'entrée lignes, celui à qui sert pour detecter le croisement et stoper l'extension
    #       extension_length_lines : valeur de l'extention des lignes maximales en mètres (par défaut : 10)
    #       is_cut_extension : boolean si demande de couper l'extension à l'intersection d'une autre lignes (par défaut : True)
    #       epsg : projection à appliquer, code EPSG (par défaut : 2154)
    #       format_vector : format du vecteur de sortie (par défaut : ESRI Shapefile)
    # Paramètres en sortie :
    #       N.A.
    """
    if debug >=2:
        print(cyan + "extendLines() : " + bold + green + "Extension des extrémitées de lignes du fichier vecteur : " + endC + vector_input)
        starting_event = "extendLines() : starting : "
        timeLine("", starting_event)

    # Les données d'entrées
    reduction_length = 0.1 # taille de la reduction des lignes de référence en metres

    # Cas ou vector_ref_input est vide
    if vector_ref_input == "" :
        vector_ref_input = vector_input

    # Charger les données
    gdf_lines = gpd.read_file(vector_input)
    gdf_reference = gpd.read_file(vector_ref_input)

    # Convertir MultiLineString en plusieurs LineString
    gdf_lines = gdf_lines.explode(index_parts=False)

    # Filtre pour ne garder que les lignes et munti-lignes
    gdf_reference_clean = gdf_reference[(gdf_reference["geometry"].geom_type == 'LineString') | (gdf_reference["geometry"].geom_type == 'MultiLineString')]

    # Filtrer les géométries invalides
    gdf_lines = gdf_lines[gdf_lines.is_valid]
    gdf_reference_clean = gdf_reference_clean[gdf_reference_clean.is_valid]

    # Reduire la ligne de reference pour la verification de connexion
    if vector_ref_input == vector_input :
        gdf_reference_clean["geometry"] = gdf_reference_clean["geometry"].apply(lambda geom: process_reduction_lines(geom, reduction_length))

    # Créer un spatial index pour les lignes de reference
    reference_lines = list(gdf_reference_clean['geometry'])
    reference_index = STRtree(reference_lines)

    # Appliquer l'extension à chaque ligne avec condition d'intersection en parallèle
    gdf_lines['geometry'] = Parallel(n_jobs=-1, backend='threading')(
        delayed(apply_extend_line_and_check_intersection)(geom, extension_length_lines, is_cut_extension, reference_lines, reference_index)
        for geom in gdf_lines['geometry'])

    # Sauvegarder le résultat
    gdf_lines.to_file(vector_output, driver=format_vector, crs="EPSG:" + str(epsg))

    if debug >=2:
        print(cyan + "extendLines() : " + bold + green + "Fin du traitement d'extension des lignes, résultat : " + endC + vector_output )
        ending_event = "extendLines() : Ending : "
        timeLine("", ending_event)
    return

########################################################################
# FONCTION cutShapefileByExtent()                                      #
########################################################################
def cutShapefileByExtent(emprise_vector, vector_input, vector_output, epsg=2154, format_vector='ESRI Shapefile'):
    """
    # ROLE:
    #     Cut a shapefile by the extent of another shapefile and save the result.
    #
    # PARAMETERS:
    #     emprise_vector (str): the vector file used for cutting.
    #     vector_input (str): the input vector file  to be cut.
    #     vector_output (str): the output vector file  containing the clipped features.
    #     epsg (int): EPSG code of the desired projection (default is 2154).
    #     format_vector (str): Format for the output vector file (default is 'ESRI Shapefile').
    #
    # RETURNS:
    #     None
    #
    # EXAMPLE:
    #     cut_shapefile_by_extent('input.shp', 'extent.shp', 'output.shp', 2154)
    #
    """

    crs = "EPSG:" + str(epsg)
    input_gdf = gpd.read_file(vector_input)
    extent_gdf = gpd.read_file(emprise_vector).to_crs(crs)
    extent_gdf = extent_gdf.drop(columns=extent_gdf.columns.difference(['geometry']))

    # Corriger les géométries invalides
    input_gdf['geometry'] = input_gdf['geometry'].apply(lambda geom: geom.buffer(0) if not geom.is_valid else geom)

    # Clip the input shapefile by the extent shapefile
    clipped_gdf = gpd.overlay(input_gdf, extent_gdf, how='intersection', keep_geom_type=True)

    # Save the clipped shapefile to the output file
    clipped_gdf.to_file(vector_output, crs=crs, driver=format_vector)
    return

########################################################################
# FUNCTION removeOverlaps()                                            #
########################################################################
def removeOverlaps(vector_input, vector_output, area_column='area', epsg=2154, format_vector='ESRI Shapefile'):
    """
    # ROLE:
    #   Suppression des superpositions de polygones
    #
    # PARAMETERS:
    #     vector_input (str): fichier vecteur d'entrée contenant des polygones qui se superpossent.
    #     vector_output (str): fichier vecteur de sortie nettoyés de superposition.
    #     area_column : nom de la colonne contenant la valeur de la surface du polygones (default : 'area').
    #     epsg (int): EPSG code of the desired projection (default is 2154).
    #     format_vector (str): Format for the output vector file (default is 'ESRI Shapefile').
    # RETURNS:
    #     None
    """
    # correct_geometry()
    def correct_geometry(geom):
        try:
            if not geom.is_valid or geom.is_empty:
                return make_valid(geom)
        except (TopologicalError, ValueError, AttributeError):
            return None
        return geom

    # Lire le fichier d'entrée
    crs = "EPSG:" + str(epsg)
    input_gdf = gpd.read_file(vector_input)
    new_geometries = []

    # Corriger les géométries invalides et les filtrer
    input_gdf['geometry'] = input_gdf['geometry'].apply(correct_geometry)
    input_gdf = input_gdf.dropna(subset=['geometry'])
    input_gdf = input_gdf[input_gdf.is_valid]

    # Calculer les surfaces des polygones et trier par surface
    input_gdf[area_column] = input_gdf['geometry'].area
    input_gdf = input_gdf.sort_values(by=area_column, ascending=False)

    # Fusionner les polygones pour éviter les chevauchements initiaux
    unified = unary_union(input_gdf['geometry'].tolist())
    i = 0
    for polygon in input_gdf['geometry']:
        if debug >= 1:
            print(cyan + "removeOverlaps() : " + endC + "polygone : " + str(i))
        i += 1
        if not polygon.is_valid:
            polygon = make_valid(polygon)  # Corriger les géométries invalides
        if unified.intersects(polygon):
            try:
                polygon = polygon.difference(unified)
                polygon = correct_geometry(polygon)
            except TopologicalError as e:
                print(f"TopologyException: {e}")
        if not polygon.is_empty:
            new_geometries.append(polygon)
            unified = unary_union(new_geometries)  # Mettre à jour la géométrie fusionnée

    # Créer un nouveau GeoDataFrame avec les géométries ajustées
    gdf_cleaned = gpd.GeoDataFrame(geometry=new_geometries, crs=input_gdf.crs)

    # Sauvegarde en fichier vecteur
    gdf_cleaned.to_file(vector_output, crs=crs, driver=format_vector)

    if debug >= 2:
        print(cyan + "removeOverlaps() : " + endC + "Fin des traitements suppression des superpositions des polygones nouveau fichier : " + vector_output)
    return

########################################################################
# FONCTION cutPolygonesByLines()                                       #
########################################################################
# !!! Non utilisé  ne fonctionne pas !!!
def cutPolygonesByLines(vector_lines_input, vector_poly_input, vector_poly_output, epsg, path_time_log, format_vector, save_results_intermediate=False, overwrite=True) :
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
    starting_event = "cutPolygonesByLines() : Cuting polygons by lines  starting : "
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
        print(cyan + "cutPolygonesByLines() : " + endC + "Découpage des polygones par les lignes fichier de sortie :", vector_poly_output)

    # Mise à jour du Log
    ending_event = "cutPolygonesByLines() : Cuting polygons by lines ending : "
    timeLine(path_time_log,ending_event)

    return

########################################################################
# FONCTION removeInteriorPolygons()                                    #
########################################################################
def getContainmentIndex(gdf):
    """
    Définie les polygones intérieurs
    """
    gdf = gdf.copy()
    gdf['contain_idx'] = gdf.index  # Par défaut, chaque polygone s'appartient à lui-même

    spatial_index = gdf.sindex

    for idx_inner, inner_row in gdf.iterrows():
        inner_geom = inner_row.geometry
        buffered_inner_geom = inner_geom.buffer(0.001)

        # Récupération robuste de tous les sommets extérieurs du polygone ou multipolygone
        inner_coords = []
        if isinstance(inner_geom, Polygon):
            inner_coords.extend(list(inner_geom.exterior.coords))
        elif isinstance(inner_geom, MultiPolygon):
            for part in inner_geom.geoms:
                inner_coords.extend(list(part.exterior.coords))
        else:
            continue  # On ignore les géométries non prises en charge

        # Recherche des polygones potentiellement contenant
        possible_matches_index = list(spatial_index.intersection(buffered_inner_geom.bounds))

        for idx in possible_matches_index:
            if idx != idx_inner:
                polygon = gdf.loc[idx, 'geometry']

                # Vérification : tous les points du polygone sont-ils couverts ?
                if all(polygon.covers(Point(x, y)) for x, y in inner_coords):
                    gdf.at[idx_inner, 'contain_idx'] = idx
                    break

    return gdf

def removeInteriorPolygons(vector_input, vector_output, epsg=2154, format_vector='ESRI Shapefile'):

    """
    # ROLE:
    #   Suppression des polygonnes entierement contenus dans un autres polygones.
    #
    # PARAMETERS:
    #     vector_input (str): fichier vecteur d'entrée contenant des polygones qui se superpossent.
    #     vector_output (str): fichier vecteur de sortie nettoyés des polygones interieurs.
    #     epsg : EPSG code de projection
    #     format_vector (str): Format for the output vector file (default is 'ESRI Shapefile').
    # RETURNS:
    #     None
    """
    def merge_by_containment_index(gdf):
        """
        Fusionne les polygones contenus
        """
        return gdf.dissolve(by='contain_idx', as_index=False)

    if debug >=2:
        print(cyan + "removeInteriorPolygons() : " + bold + green + "Supression des polyones interieurs du fichier vecteur : " + endC + vector_input)
        starting_event = "removeInteriorPolygons() : starting : "
        timeLine("", starting_event)

    # Chargement
    gdf = gpd.read_file(vector_input)

    # Étape 1 : marquage des inclusions
    gdf_marked = getContainmentIndex(gdf)

    # Étape 2 : fusion par index
    gdf_merged = merge_by_containment_index(gdf_marked)

    # Export final
    del gdf_merged['contain_idx']
    gdf_merged.to_file(vector_output, driver=format_vector, crs="EPSG:" + str(epsg))

    if debug >=2:
        print(cyan + "removeInteriorPolygons() : " + bold + green + "Fin du traitement supression des polyones interieurs, résultat : " + endC + vector_output )
        ending_event = "removeInteriorPolygons() : Ending : "
        timeLine("", ending_event)

    return

########################################################################
# FONCTION is_vector_file_empty()                                      #
########################################################################
def is_vector_file_empty(filepath, layer=None):
    """
    # ROLE:
    #   Teste si un fichier vecteur est vide.
    #
    # PARAMETERS:
    #     filepath (str): fichier vecteur à tester.
    #     layer (str): nom de la couche.
    # RETURNS:
    #     None
    """
    try:
        gdf = gpd.read_file(filepath, layer=layer) if layer else gpd.read_file(filepath)

        # Vérifie s'il y a au moins une ligne ET que la géométrie n'est pas nulle
        print()
        return gdf.empty or gdf['geometry'].isna().all()
    except Exception as e:
        print(cyan + "is_vector_file_empty() : " + bold + yellow + f"Erreur lors de la lecture du fichier : {e}" + endC)
        return True  # On considère qu’il est vide si on ne peut pas le lire


########################################################################
# FUNCTION bufferPolylinesToPolygons()                                 #
########################################################################
def bufferPolylinesToPolygons(gdf, buffer_distance, field_buff, factor_buff, resolution=1, cap_style=2):
    """
    # ROLE:
    #     Convertie des polylignes en polygones avec une valeur de buffer contenu dans un champs ou avec une valeur fixe.
    #
    # PARAMETERS:
    #     gdf : descripteur vers les polylignes.
    #     buffer_distance : la valeur du buffer fixe None si field_buff != ""
    #     field_buff : le nom du champs contenant la valeur du buffer pour chaque troncon.
    #     factor_buff : le facteur à appliquer à la valeur de buffer
    #     resolution :
    #     cap_style :
    # RETURNS:
    #     descripteur vers les polygones
    """
    # 1. Calcul du buffer distance
    if buffer_distance is None and field_buff != "" :
        buffer_distance = gdf[field_buff] * factor_buff
    elif buffer_distance != 0  :
        buffer_distance = buffer_distance * factor_buff
    else :
        return gdf

    # 2. Ajouter une colonne temporaire pour la distance
    gdf = gdf.copy()
    gdf["__buffer__"] = buffer_distance

    # 3. Fusionner toutes les lignes en un seul MultiLineString propre
    merged_lines = linemerge(unary_union(gdf.geometry))

    # 4. Calculer un buffer avec la distance moyenne ou max
    if isinstance(buffer_distance, pd.Series):
        buffer_distance_global = buffer_distance.mean()  # ou .max()
    else:
        buffer_distance_global = buffer_distance

    # 5. Créer le buffer propre
    buffered_geom = merged_lines.buffer(buffer_distance_global, resolution, cap_style)

    # 6. Retourner un GeoDataFrame unique
    gdf_polygons = gpd.GeoDataFrame(geometry=[buffered_geom], crs=gdf.crs)

    return gdf_polygons

########################################################################
# FUNCTION explodeMultiGdf()                                           #
########################################################################
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
def removeRing(geometry, area_threshold=500):
    """
    # ROLE:
    #     Fonction pour supprimer les anneaux (rings) d'une géométrie.
    #     Supprime les anneaux internes d'une géométrie si leur surface est inférieure à area_threshold.
    #
    # PARAMETERS:
    #     geometry : géometry polygone d'entrée.
    #     area_threshold (float): La surface maximale sous laquelle un anneau est supprimé.
    # RETURNS:
    #     La géométrie nettoyée sans ring (anneaux)
    """
    if geometry.geom_type == 'Polygon':
        # Filtrer les anneaux internes (interiors) selon la surface
        new_interiors = [
            ring for ring in geometry.interiors
            if Polygon(ring).area >= area_threshold
        ]
        return Polygon(geometry.exterior, new_interiors)

    elif geometry.geom_type == 'MultiPolygon':
        cleaned_polygons = [
            removeRing(poly, area_threshold) for poly in geometry.geoms
        ]
        return MultiPolygon(cleaned_polygons)

    else:
        # Ne rien faire si la géométrie n'est pas un polygone
        return geometry
