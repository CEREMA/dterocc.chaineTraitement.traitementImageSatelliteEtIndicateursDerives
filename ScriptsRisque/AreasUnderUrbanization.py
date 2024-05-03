#!/usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

"""
Nom de l'objet : AreasUnderUrbanization.py
Description :
-------------
Objectif : produire une donnée des zones en voie d'urbanisation
Remarque : peut être utilisé comme donnée Oc0 (zones en voie d'urbanisation) du Référentiel national de vulnérabilité aux inondations

-----------------
Outils utilisés :
 -

------------------------------
Historique des modifications :
 - 24/05/2019 : création

-----------------------
A réfléchir / A faire :
 -
"""

# Import des bibliothèques Python
from __future__ import print_function
import os, argparse
from osgeo import ogr
from Lib_display import bold,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_file import cleanTempData, deleteDir, removeVectorFile
from Lib_log import timeLine
from Lib_postgis import createDatabase, openConnection, importVectorByOgr2ogr, executeQuery, exportVectorByOgr2ogr, closeConnection, dropDatabase
from Lib_raster import getPixelWidthXYImage, rasterizeBinaryVector, rasterizeBinaryVectorWithoutReference, rasterizeVector
from Lib_text import regExReplace
from Lib_vector import cutVector, fusionVectors, getAttributeValues, getEmpriseVector
from CrossingVectorRaster import statisticsVectorRaster

# Niveau de debug (variable globale)
debug = 3

########################################################################
# FONCTION buildablePlot()                                             #
########################################################################
def buildablePlot(input_plot_vector, output_plot_vector, footprint_vector, input_built_file, input_built_vector_list, input_plu_vector, input_ppr_vector, min_built_size_list=['None:100:20', '100:None:40'], plu_field='TYPEZONE', plu_u_values_list=['U'], plu_au_values_list=['AU','AUc','AUs'], ppr_field='CODEZONE', ppr_red_values_list=['R1','R2','R3'], ppr_blue_values_list=['B1','B2','B2-1','B2-2','B3'], epsg=2154, no_data_value=0, format_raster='GTiff', format_vector='ESRI Shapefile', extension_raster='.tif', extension_vector='.shp', postgis_ip_host='localhost', postgis_num_port=5432, postgis_user_name='postgres', postgis_password='postgres', postgis_database_name='database', postgis_schema_name='public', postgis_encoding='latin1', path_time_log='', save_results_intermediate=False, overwrite=True):
    """
    # ROLE :
    #     Cartographie des parcelles disponibles et constructibles
    #
    # ENTREES DE LA FONCTION :
    #     input_plot_vector : fichier parcellaire en entrée (en format vecteur)
    #     output_plot_vector : fichier parcellaire en sortie (en format vecteur)
    #     footprint_vector : fichier emprise en entrée (en format vecteur)
    #     input_built_file : fichier masque binaire du bâti en entrée (en format raster --> 1:bati; 0:non-bati)
    #     input_built_vector_list : liste des fichiers du bâti en entrée (en format vecteur)
    #     input_plu_vector : fichier PLU en entrée (en format vecteur)
    #     input_ppr_vector : fichier PPRi en entrée (en format vecteur)
    #     min_built_size_list : liste des surfaces minimales de bâti pour considérer la parcelle comme construite, fonction de la taille de la parcelle elle-même. Par défaut : ['None:100:20', '100:None:40']
    #     plu_field : champ du PLU donnant l'information de zonage. Par défaut : 'TYPEZONE'
    #     plu_u_values_list : liste de valeurs du zonage 'U' du PLU. Par défaut : ['U']
    #     plu_au_values_list : liste de valeurs du zonage 'AU' du PLU. Par défaut : ['AU','AUc','AUs']
    #     ppr_field : champ du PPR donnant l'information de zonage. Par défaut : 'CODEZONE'
    #     ppr_red_values_list : liste de valeurs du zonage 'rouge' du PPRi. Par défaut : ['R1','R2','R3']
    #     ppr_blue_values_list : liste de valeurs du zonage 'bleu' du PPRi. Par défaut : ['B1','B2','B2-1','B2-2','B3']
    #     epsg : code EPSG du système de projection. Par défaut : 2154
    #     no_data_value : valeur NoData des pixels des fichiers raster. Par défaut : 0
    #     format_raster : format des fichiers raster. Par défaut : 'GTiff'
    #     format_vector : format des fichiers vecteur. Par défaut : 'ESRI Shapefile'
    #     extension_raster : extension des fichiers raster. Par défaut : '.tif'
    #     extension_vector : extension des fichiers vecteur. Par défaut : '.shp'
    #     postgis_ip_host : nom du serveur PostGIS. Par défaut : 'localhost'
    #     postgis_num_port : numéro de port du serveur PostGIS. Par défaut : 5432
    #     postgis_user_name : nom d'utilisateur PostGIS. Par défaut : 'postgres'
    #     postgis_password : mot de passe de l'utilisateur PostGIS. Par défaut : 'postgres'
    #     postgis_database_name : nom de la base PostGIS. Par défaut : 'database'
    #     postgis_schema_name : nom du schéma dans la base PostGIS. Par défaut : 'public'
    #     postgis_encoding : l'encodage des fichiers pour l'import de vecteurs dans PostGIS. Par défaut : 'latin1'
    #     path_time_log : fichier log de sortie, par défaut vide
    #     save_results_intermediate : fichiers temporaires conservés, par défaut = False
    #     overwrite : écrase si un fichier existant a le même nom qu'un fichier de sortie, par défaut = True
    #
    # SORTIES DE LA FONCTION :
    #     N.A.
    """

    if debug >= 3:
        print('\n' + bold + green + "Parcelles disponibles et constructibles - Variables dans la fonction :" + endC)
        print(cyan + "    buildablePlot() : " + endC + "input_plot_vector : " + str(input_plot_vector) + endC)
        print(cyan + "    buildablePlot() : " + endC + "output_plot_vector : " + str(output_plot_vector) + endC)
        print(cyan + "    buildablePlot() : " + endC + "footprint_vector : " + str(footprint_vector) + endC)
        print(cyan + "    buildablePlot() : " + endC + "input_built_file : " + str(input_built_file) + endC)
        print(cyan + "    buildablePlot() : " + endC + "input_built_vector_list : " + str(input_built_vector_list) + endC)
        print(cyan + "    buildablePlot() : " + endC + "input_plu_vector : " + str(input_plu_vector) + endC)
        print(cyan + "    buildablePlot() : " + endC + "input_ppr_vector : " + str(input_ppr_vector) + endC)
        print(cyan + "    buildablePlot() : " + endC + "min_built_size_list : " + str(min_built_size_list) + endC)
        print(cyan + "    buildablePlot() : " + endC + "plu_field : " + str(plu_field) + endC)
        print(cyan + "    buildablePlot() : " + endC + "plu_u_values_list : " + str(plu_u_values_list) + endC)
        print(cyan + "    buildablePlot() : " + endC + "plu_au_values_list : " + str(plu_au_values_list) + endC)
        print(cyan + "    buildablePlot() : " + endC + "ppr_field : " + str(ppr_field) + endC)
        print(cyan + "    buildablePlot() : " + endC + "ppr_red_values_list : " + str(ppr_red_values_list) + endC)
        print(cyan + "    buildablePlot() : " + endC + "ppr_blue_values_list : " + str(ppr_blue_values_list) + endC)
        print(cyan + "    buildablePlot() : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "    buildablePlot() : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "    buildablePlot() : " + endC + "format_raster : " + str(format_raster) + endC)
        print(cyan + "    buildablePlot() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "    buildablePlot() : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "    buildablePlot() : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "    buildablePlot() : " + endC + "postgis_ip_host : " + str(postgis_ip_host) + endC)
        print(cyan + "    buildablePlot() : " + endC + "postgis_num_port : " + str(postgis_num_port) + endC)
        print(cyan + "    buildablePlot() : " + endC + "postgis_user_name : " + str(postgis_user_name) + endC)
        print(cyan + "    buildablePlot() : " + endC + "postgis_password : " + str(postgis_password) + endC)
        print(cyan + "    buildablePlot() : " + endC + "postgis_database_name : " + str(postgis_database_name) + endC)
        print(cyan + "    buildablePlot() : " + endC + "postgis_schema_name : " + str(postgis_schema_name) + endC)
        print(cyan + "    buildablePlot() : " + endC + "postgis_encoding : " + str(postgis_encoding) + endC)
        print(cyan + "    buildablePlot() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "    buildablePlot() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "    buildablePlot() : " + endC + "overwrite : " + str(overwrite) + endC + '\n')

    # Définition des constantes
    ENCODING_RASTER = 'uint8'
    ENCODING_RASTER_GDAL = 'Byte'
    SUFFIX_TEMP = '_temp'
    SUFFIX_CUT = '_cut'
    AREA_FIELD = 'st_area'
    GEOM_FIELD = 'geom'
    CONSTRUCT_FIELD = 'construct'
    NO_PLU_FIELD = 'no_plu'
    NO_PPR_FIELD = 'no_ppr'
    REGEX = '[a-zA-Z0-9_]'
    REGEX_REPLACE = '_'

    # Mise à jour du log
    starting_event = "buildablePlot() : Début du traitement : "
    timeLine(path_time_log, starting_event)

    print(cyan + "buildablePlot() : " + bold + green + "DEBUT DES TRAITEMENTS" + endC + '\n')

    # Définition des variables 'basename'
    footprint_basename = os.path.splitext(os.path.basename(footprint_vector))[0]
    input_plot_basename = os.path.splitext(os.path.basename(input_plot_vector))[0]
    built_basename = 'bati'
    if input_built_file != "":
        built_basename = os.path.splitext(os.path.basename(input_built_file))[0]
    output_plot_basename = os.path.splitext(os.path.basename(output_plot_vector))[0]

    # Définition des variables temp
    temp_directory = os.path.dirname(output_plot_vector) + os.sep + output_plot_basename + SUFFIX_TEMP
    footprint_mask = temp_directory + os.sep + footprint_basename + extension_raster
    plot_vector_cut = temp_directory + os.sep + output_plot_basename + SUFFIX_CUT + extension_vector
    built_vector_new = temp_directory + os.sep + built_basename + extension_vector
    built_file = temp_directory + os.sep + built_basename + extension_raster

    # Définition des variables PostGIS
    plot_table = input_plot_basename.lower()

    # Nettoyage des traitements précédents
    if debug >= 3:
        print(cyan + "buildablePlot() : " + endC + "Nettoyage des traitements précédents." + endC + '\n')
    removeVectorFile(output_plot_vector, format_vector=format_vector)
    cleanTempData(temp_directory)
    dropDatabase(postgis_database_name, user_name=postgis_user_name, password=postgis_password, ip_host=postgis_ip_host, num_port=postgis_num_port, schema_name=postgis_schema_name)

    #############
    # Etape 0/4 # Préparation des traitements
    #############

    print(cyan + "buildablePlot() : " + bold + green + "ETAPE 0/4 - Début de la préparation des traitements." + endC + '\n')

    # Découpage du parcellaire à la zone d'étude
    cutVector(footprint_vector, input_plot_vector, plot_vector_cut, overwrite=overwrite, format_vector=format_vector)

    # Création d'un masque binaire (pour la rastérisation des vecteurs d'entrée)
    if input_built_vector_list != [] or input_plu_vector != "" or input_ppr_vector != "":
        pixel_width, pixel_height = 1, 1
        if input_built_file != "":
            pixel_width, pixel_height = getPixelWidthXYImage(input_built_file)
        xmin, xmax, ymin, ymax = getEmpriseVector(footprint_vector, format_vector=format_vector)
        xmin, xmax, ymin, ymax = round(xmin-1), round(xmax+1), round(ymin-1), round(ymax+1)
        rasterizeBinaryVectorWithoutReference(footprint_vector, footprint_mask, xmin, ymin, xmax, ymax, pixel_width, pixel_height, burn_value=1, nodata_value=no_data_value, format_raster=format_raster, codage=ENCODING_RASTER_GDAL)

    # Préparation de PostGIS
    createDatabase(postgis_database_name, user_name=postgis_user_name, password=postgis_password, ip_host=postgis_ip_host, num_port=postgis_num_port, schema_name=postgis_schema_name)

    print(cyan + "buildablePlot() : " + bold + green + "ETAPE 0/4 - Fin de la préparation des traitements." + endC + '\n')

    #############
    # Etape 1/4 # Croisement avec le bâti
    #############

    print(cyan + "buildablePlot() : " + bold + green + "ETAPE 1/4 - Début du croisement avec le bâti." + endC + '\n')

    # Traitements dans le cas où on rentre une liste de vecteurs
    if input_built_vector_list != []:
        fusionVectors(input_built_vector_list, built_vector_new, format_vector=format_vector)
        rasterizeBinaryVector(built_vector_new, footprint_mask, built_file, label=1, codage=ENCODING_RASTER)
    else:
        built_file = input_built_file

    # Récupération des statistiques du zonage PPRi par parcelle
    class_label_dico_built = {no_data_value:'NonBati', 1:'Bati'}
    statisticsVectorRaster(built_file, plot_vector_cut, "", 1, True, False, False, [], [], class_label_dico_built, clean_small_polygons=True, no_data_value=no_data_value, format_vector=format_vector, path_time_log=path_time_log, save_results_intermediate=save_results_intermediate, overwrite=overwrite)

    print(cyan + "buildablePlot() : " + bold + green + "ETAPE 1/4 - Fin du croisement avec le bâti." + endC + '\n')

    #############
    # Etape 2/4 # Croisement avec le PLU
    #############

    if input_plu_vector != "":
        print(cyan + "buildablePlot() : " + bold + green + "ETAPE 2/4 - Début du croisement avec le PLU." + endC + '\n')

        plu_values_list_unique = crossingZoningVector(input_plu_vector, plot_vector_cut, footprint_mask, temp_directory, plu_field, NO_PLU_FIELD, REGEX, REGEX_REPLACE, epsg, no_data_value, format_vector, extension_raster, extension_vector, postgis_database_name, postgis_user_name, postgis_password, postgis_ip_host, postgis_num_port, postgis_schema_name, postgis_encoding, ENCODING_RASTER, path_time_log, save_results_intermediate, overwrite)

        print(cyan + "buildablePlot() : " + bold + green + "ETAPE 2/4 - Fin du croisement avec le PLU." + endC + '\n')

    else:
        print(cyan + "buildablePlot() : " + bold + yellow + "ETAPE 2/4 - Pas de croisement avec le PLU demandé." + endC + '\n')

    #############
    # Etape 3/4 # Croisement avec le PPRi
    #############

    if input_ppr_vector != "":
        print(cyan + "buildablePlot() : " + bold + green + "ETAPE 3/4 - Début du croisement avec le PPRi." + endC + '\n')

        ppr_values_list_unique = crossingZoningVector(input_ppr_vector, plot_vector_cut, footprint_mask, temp_directory, ppr_field, NO_PPR_FIELD, REGEX, REGEX_REPLACE, epsg, no_data_value, format_vector, extension_raster, extension_vector, postgis_database_name, postgis_user_name, postgis_password, postgis_ip_host, postgis_num_port, postgis_schema_name, postgis_encoding, ENCODING_RASTER, path_time_log, save_results_intermediate, overwrite)

        print(cyan + "buildablePlot() : " + bold + green + "ETAPE 3/4 - Fin du croisement avec le PPRi." + endC + '\n')

    else:
        print(cyan + "buildablePlot() : " + bold + yellow + "ETAPE 3/4 - Pas de croisement avec le PPRi demandé." + endC + '\n')

    #############
    # Etape 4/4 # Extraction des parcelles disponibles et constructibles
    #############

    print(cyan + "buildablePlot() : " + bold + green + "ETAPE 4/4 - Début de l'extraction des parcelles disponibles et constructibles." + endC + '\n')

    # Pré-traitements dans PostGIS
    plot_table = importVectorByOgr2ogr(postgis_database_name, plot_vector_cut, plot_table, user_name=postgis_user_name, password=postgis_password, ip_host=postgis_ip_host, num_port=postgis_num_port, schema_name=postgis_schema_name, epsg=epsg, codage=postgis_encoding)
    connection = openConnection(postgis_database_name, user_name=postgis_user_name, password=postgis_password, ip_host=postgis_ip_host, num_port=postgis_num_port, schema_name=postgis_schema_name)

    # Définition des classes possibles des parcelles (non-disponible, disponible mais non-constructible, disponible et constructible)
    case_built = "parcelle construite"
    case_free = "parcelle disponible"
    case_no_plu = "hors zonage PLU (autre commune)"
    case_plu_a_n = "disponible mais non-constructible - zone PLU A/N"
    case_ppr_red = "disponible mais non-constructible - zone PPR rouge"
    case_ppr_blue = "disponible mais non-constructible - zone PPR bleu"
    case_ppr_other = "disponible mais non-constructible - zone PPR autre"
    case_plu_u = "disponible et constructible - zone PLU U"
    case_plu_au = "disponible et constructible - zone PLU AU"
    case_plu_u_au = "disponible et constructible - zone PLU U/AU"

    # Récupération du champ contenant l'info de surface bâtie
    built_area_field_pg = 's_' + class_label_dico_built[1].lower()

    # Construction du conditionnel SQL WHERE, en lien avec les champs de % zones PLU et PPRi
    if input_plu_vector != "":
        plu_u_fields = sqlConstruction(plu_values_list_unique, plu_u_values_list, REGEX, REGEX_REPLACE)
        plu_au_fields = sqlConstruction(plu_values_list_unique, plu_au_values_list, REGEX, REGEX_REPLACE)
    if input_ppr_vector != "":
        ppr_red_fields = sqlConstruction(ppr_values_list_unique, ppr_red_values_list, REGEX, REGEX_REPLACE)
        ppr_blue_fields = sqlConstruction(ppr_values_list_unique, ppr_blue_values_list, REGEX, REGEX_REPLACE)

    # Requête SQL pour le calcul de la disponibilité des parcelles, en fonction de la taille de la parcelle
    sql_query = "ALTER TABLE %s ADD COLUMN \"%s\" REAL;\n" % (plot_table, AREA_FIELD)
    sql_query += "UPDATE %s SET \"%s\" = ST_Area(%s);\n" % (plot_table, AREA_FIELD, GEOM_FIELD)
    sql_query += "ALTER TABLE %s ADD COLUMN \"%s\" VARCHAR;\n" % (plot_table, CONSTRUCT_FIELD)

    # Boucle sur les conditions de surfaces minimales pour considérer la parcelle construite/disponible
    for min_built_size in min_built_size_list:
        min_built_size_split = min_built_size.split(':')
        min_plot_size = min_built_size_split[0]
        max_plot_size = min_built_size_split[1]
        built_size = min_built_size_split[2]

        # Si pas de limite de surface de parcelle
        if min_plot_size == 'None' and max_plot_size == 'None':
            sql_query += "UPDATE %s SET \"%s\" = '%s' WHERE \"%s\" >= %s;\n" % (plot_table, CONSTRUCT_FIELD, case_built, built_area_field_pg, built_size)
            sql_query += "UPDATE %s SET \"%s\" = '%s' WHERE \"%s\" < %s;\n" % (plot_table, CONSTRUCT_FIELD, case_free, built_area_field_pg, built_size)

        # Si pas de limite inférieure de surface de parcelle
        elif min_plot_size == 'None':
            sql_query += "UPDATE %s SET \"%s\" = '%s' WHERE \"%s\" < %s AND \"%s\" >= %s;\n" % (plot_table, CONSTRUCT_FIELD, case_built, AREA_FIELD, max_plot_size, built_area_field_pg, built_size)
            sql_query += "UPDATE %s SET \"%s\" = '%s' WHERE \"%s\" < %s AND \"%s\" < %s;\n" % (plot_table, CONSTRUCT_FIELD, case_free, AREA_FIELD, max_plot_size, built_area_field_pg, built_size)

        # Si pas de limite supérieure de surface de parcelle
        elif max_plot_size == 'None':
            sql_query += "UPDATE %s SET \"%s\" = '%s' WHERE \"%s\" >= %s AND \"%s\" >= %s;\n" % (plot_table, CONSTRUCT_FIELD, case_built, AREA_FIELD, min_plot_size, built_area_field_pg, built_size)
            sql_query += "UPDATE %s SET \"%s\" = '%s' WHERE \"%s\" >= %s AND \"%s\" < %s;\n" % (plot_table, CONSTRUCT_FIELD, case_free, AREA_FIELD, min_plot_size, built_area_field_pg, built_size)

        # Si limites inférieure et supérieure de surface de parcelle
        else:
            sql_query += "UPDATE %s SET \"%s\" = '%s' WHERE \"%s\" >= %s AND \"%s\" < %s AND \"%s\" >= %s;\n" % (plot_table, CONSTRUCT_FIELD, case_built, AREA_FIELD, min_plot_size, AREA_FIELD, max_plot_size, built_area_field_pg, built_size)
            sql_query += "UPDATE %s SET \"%s\" = '%s' WHERE \"%s\" >= %s AND \"%s\" < %s AND \"%s\" < %s;\n" % (plot_table, CONSTRUCT_FIELD, case_free, AREA_FIELD, min_plot_size, AREA_FIELD, max_plot_size, built_area_field_pg, built_size)

    # Requête SQL de ré-attribution dans le cas de l'utilisation du PLU et/ou du PPRi (non-disponible, disponible mais non-constructible, disponible et constructible)
    if input_plu_vector != "":
        sql_query += "UPDATE %s SET \"%s\" = '%s' WHERE \"%s\" >= 50;\n" % (plot_table, CONSTRUCT_FIELD, case_no_plu, NO_PLU_FIELD) # Parcelles hors PLU (autre commune)
        sql_query += "UPDATE %s SET \"%s\" = '%s' WHERE \"%s\" = '%s' AND %s + %s < 50;\n" % (plot_table, CONSTRUCT_FIELD, case_plu_a_n, CONSTRUCT_FIELD, case_free, plu_u_fields, plu_au_fields) # Parcelles disponibles mais non-constructibles (zonage PLU A et/ou N)
    if input_ppr_vector != "":
        sql_query += "UPDATE %s SET \"%s\" = '%s' WHERE \"%s\" = '%s' AND %s >= 50;\n" % (plot_table, CONSTRUCT_FIELD, case_ppr_red, CONSTRUCT_FIELD, case_free, ppr_red_fields) # Parcelles disponibles mais non-constructibles (zonage PPRi rouge)
        sql_query += "UPDATE %s SET \"%s\" = '%s' WHERE \"%s\" = '%s' AND %s >= 50;\n" % (plot_table, CONSTRUCT_FIELD, case_ppr_blue, CONSTRUCT_FIELD, case_free, ppr_blue_fields) # Parcelles disponibles mais non-constructibles (zonage PPRi bleu)
        sql_query += "UPDATE %s SET \"%s\" = '%s' WHERE \"%s\" = '%s' AND \"%s\" < 50;\n" % (plot_table, CONSTRUCT_FIELD, case_ppr_other, CONSTRUCT_FIELD, case_free, NO_PPR_FIELD) # Parcelles disponibles mais non-constructibles (zonage PPRi autre)
    if input_plu_vector != "":
        sql_query += "UPDATE %s SET \"%s\" = '%s' WHERE \"%s\" = '%s' AND %s >= 50;\n" % (plot_table, CONSTRUCT_FIELD, case_plu_u, CONSTRUCT_FIELD, case_free, plu_u_fields) # Parcelles disponibles et constructibles (zonage PLU U)
        sql_query += "UPDATE %s SET \"%s\" = '%s' WHERE \"%s\" = '%s' AND %s >= 50;\n" % (plot_table, CONSTRUCT_FIELD, case_plu_au, CONSTRUCT_FIELD, case_free, plu_au_fields) # Parcelles disponibles et constructibles (zonage PLU AU)
        sql_query += "UPDATE %s SET \"%s\" = '%s' WHERE \"%s\" = '%s' AND %s + %s >= 50;\n" % (plot_table, CONSTRUCT_FIELD, case_plu_u_au, CONSTRUCT_FIELD, case_free, plu_u_fields, plu_au_fields) # Parcelles disponibles et constructibles (zonage PLU U+AU)

    # Traitements SQL pour la définition des parcelles disponibles et constructibles
    executeQuery(connection, sql_query)
    closeConnection(connection)
    exportVectorByOgr2ogr(postgis_database_name, output_plot_vector, plot_table, user_name=postgis_user_name, password=postgis_password, ip_host=postgis_ip_host, num_port=postgis_num_port, schema_name=postgis_schema_name, format_type=format_vector)

    print(cyan + "buildablePlot() : " + bold + green + "ETAPE 4/4 - Fin de l'extraction des parcelles disponibles et constructibles." + endC + '\n')

    # Suppression des fichiers temporaires
    if not save_results_intermediate:
        if debug >= 3:
            print(cyan + "buildablePlot() : " + endC + "Suppression des fichiers temporaires." + endC + '\n')
        deleteDir(temp_directory)
        dropDatabase(postgis_database_name, user_name=postgis_user_name, password=postgis_password, ip_host=postgis_ip_host, num_port=postgis_num_port, schema_name=postgis_schema_name)

    print(cyan + "buildablePlot() : " + bold + green + "FIN DES TRAITEMENTS" + endC + '\n')

    # Mise à jour du log
    ending_event = "buildablePlot() : Fin du traitement : "
    timeLine(path_time_log, ending_event)

    return

########################################################################
# FONCTION crossingZoningVector()                                      #
########################################################################
# ROLE :
#     Croise les données vecteur de zonage (PLU et/ou PPRi) avec le parcellaire
#
# ENTREES DE LA FONCTION :
#     zoning_vector : fichier vecteur de zonage
#     plot_vector : fichier vecteur parcellaire
#     footprint_mask : fichier raster binaire de l'emprise d'étude
#     temp_directory : dossier temporaire
#     zoning_field : champ du fichier vecteur de zonage contenant l'information de zonage
#     no_zoning_field : nouveau champ pour l'absence de zonage
#     regex : liste des caractères autorisés (au format re)
#     regex_replace : caractère de remplacement pour les caractères non-autorisés
#     epsg : code EPSG du système de projection
#     no_data_value : valeur NoData des pixels des fichiers raster
#     format_vector : format des fichiers vecteur
#     extension_raster : extension des fichiers raster
#     extension_vector : extension des fichiers vecteur
#     postgis_ip_host : nom du serveur PostGIS
#     postgis_num_port : numéro de port du serveur PostGIS
#     postgis_user_name : nom d'utilisateur PostGIS
#     postgis_password : mot de passe de l'utilisateur PostGIS
#     postgis_database_name : nom de la base PostGIS
#     postgis_schema_name : nom du schéma dans la base PostGIS
#     postgis_encoding : l'encodage des fichiers pour l'import de vecteurs dans PostGIS
#     encoding_raster : encodage de sortie du fichier raster
#     path_time_log : fichier log de sortie
#     save_results_intermediate : fichiers temporaires conservés
#     overwrite : écrase si un fichier existant a le même nom qu'un fichier de sortie
#
# SORTIES DE LA FONCTION :
#     values_list_unique : liste des valeurs uniques du zonage

def crossingZoningVector(zoning_vector, plot_vector, footprint_mask, temp_directory, zoning_field, no_zoning_field, regex, regex_replace, epsg, no_data_value, format_vector, extension_raster, extension_vector, postgis_database_name, postgis_user_name, postgis_password, postgis_ip_host, postgis_num_port, postgis_schema_name, postgis_encoding, encoding_raster, path_time_log, save_results_intermediate, overwrite):

    basename = os.path.splitext(os.path.basename(zoning_vector))[0]
    zoning_vector_new = temp_directory + os.sep + basename + extension_vector
    zoning_file = temp_directory + os.sep + basename + extension_raster
    zoning_table = basename.lower()
    field_pg = zoning_field.lower()
    zoning_field_int = field_pg[:6] + "_int"

    # Pré-traitements dans PostGIS
    zoning_table = importVectorByOgr2ogr(postgis_database_name, zoning_vector, zoning_table, user_name=postgis_user_name, password=postgis_password, ip_host=postgis_ip_host, num_port=postgis_num_port, schema_name=postgis_schema_name, epsg=epsg, codage=postgis_encoding)
    connection = openConnection(postgis_database_name, user_name=postgis_user_name, password=postgis_password, ip_host=postgis_ip_host, num_port=postgis_num_port, schema_name=postgis_schema_name)

    # Récupération des valeurs uniques de l'attribut du zonage
    attr_values_list_dico = getAttributeValues(zoning_vector, None, None, {zoning_field:ogr.OFTString}, format_vector=format_vector)
    values_list = attr_values_list_dico[zoning_field]
    values_list_unique = sorted(set(values_list))

    # Boucle sur les zonages : ajout d'un champ pour préparer la rastérisation, et construction du dico pour le CVR
    class_label_key = 0
    class_label_dico = {no_data_value: no_zoning_field}
    query = "ALTER TABLE %s ADD COLUMN \"%s\" INTEGER;\n" % (zoning_table, zoning_field_int)
    for value in values_list_unique:
        class_label_key += 1
        value_dico = regExReplace(value, regex, regex_replace)
        class_label_dico[class_label_key] = value_dico
        query += "UPDATE %s SET \"%s\" = %s WHERE \"%s\" = '%s';\n" % (zoning_table, zoning_field_int, class_label_key, field_pg, value)

    # Traitement dans PostGIS
    executeQuery(connection, query)
    closeConnection(connection)
    exportVectorByOgr2ogr(postgis_database_name, zoning_vector_new, zoning_table, user_name=postgis_user_name, password=postgis_password, ip_host=postgis_ip_host, num_port=postgis_num_port, schema_name=postgis_schema_name, format_type=format_vector)

    # Récupération des statistiques du zonage par parcelle
    rasterizeVector(zoning_vector_new, zoning_file, footprint_mask, zoning_field_int, codage=encoding_raster)
    statisticsVectorRaster(zoning_file, plot_vector, "", 1, True, False, False, [], [], class_label_dico, clean_small_polygons=True, no_data_value=no_data_value, format_vector=format_vector, path_time_log=path_time_log, save_results_intermediate=save_results_intermediate, overwrite=overwrite)

    return values_list_unique

########################################################################
# FONCTION sqlConstruction()                                           #
########################################################################
# ROLE :
#     Construction du conditionnel SQL WHERE, par concaténation d'une sélection de champs possibles
#
# ENTREES DE LA FONCTION :
#     values_list_all : liste de toutes les valeurs disponibles
#     values_list_selection : liste des valeurs à retenir (si elles existent dans les valeurs disponibles)
#     regex : liste des caractères autorisés (au format re)
#     regex_replace : caractère de remplacement pour les caractères non-autorisés
#
# SORTIES DE LA FONCTION :
#     sql_query : extrait de requête SQL, contenant les noms des champs

def sqlConstruction(values_list_all, values_list_selection, regex, regex_replace):

    sql_query = ''
    for value in values_list_selection:
        if value in values_list_all:
            if len(value) > 10:
                value = value[:10]
            new_value = regExReplace(value, regex, regex_replace)
            sql_query += '"%s" + ' % new_value.lower()
    sql_query = sql_query[:-3]

    return sql_query

#############################################################################################################################
################################################## Mise en place du parser ##################################################
#############################################################################################################################

def main(gui=False):
    parser = argparse.ArgumentParser(prog = "Zones en voie d'urbanisation", description = "\
    Production d'une donnée des zones en voie d'urbanisation (parcelles disponibles et constructibles). \n\
    Exemple : python3 -m AreasUnderUrbanization.py -in /mnt/RAM_disk/BD_Parcellaire.shp \n\
                                                   -out /mnt/RAM_disk/AreasUnderUrbanization.shp \n\
                                                   -emp /mnt/RAM_disk/zone_etude.shp \n\
                                                   -ibr /mnt/RAM_disk/OCS_sat_masque_bati.tif \n\
                                                   -iplu /mnt/RAM_disk/zonage_PLU.shp \n\
                                                   -ippr /mnt/RAM_disk/zonage_PPRi.shp")

    parser.add_argument('-in', '--input_plot_vector', default="", type=str, required=True, help="Input plot vector file.")
    parser.add_argument('-out', '--output_plot_vector', default="", type=str, required=True, help="Output plot vector file.")
    parser.add_argument('-emp', '--footprint_vector', default="", type=str, required=True, help="Input footprint vector file.")
    parser.add_argument('-ibr', '--input_built_file', default="", type=str, required=False, help="Input built binary raster mask (1 = built areas; 0 = no-built areas).")
    parser.add_argument('-ibvl', '--input_built_vector_list', nargs="+", default=[], type=str, required=False, help="List of input built vector(s) file(s).")
    parser.add_argument('-iplu', '--input_plu_vector', default="", type=str, required=False, help="Input PLU vector file.")
    parser.add_argument('-ippr', '--input_ppr_vector', default="", type=str, required=False, help="Input PPRi vector file.")
    parser.add_argument('-mbsl', '--min_built_size_list', nargs="+", default=['None:100:20', '100:None:40'], type=str, required=False, help="List of minimums built sizes to consider plot as built, dependent on the size of the plot itself (min_plot_size:max_plot_size:min_built_size). If None for 'min_plot_size' and/or 'max_plot_size', no minimum and/or maximum. Default: 'None:100:20 100:None:40'.")
    parser.add_argument('-pluf', '--plu_field', default="TYPEZONE", type=str, required=False, help="Field name of PLU zoning. Default: 'TYPEZONE'.")
    parser.add_argument('-pluu', '--plu_u_values_list', nargs="+", default=['U'], type=str, required=False, help="List of values for PLU urban zoning. Default: 'U'.")
    parser.add_argument('-plua', '--plu_au_values_list', nargs="+", default=['AU','AUc','AUs'], type=str, required=False, help="List of values for PLU to urbanize zoning. Default: 'AU AUc AUs'.")
    parser.add_argument('-pprf', '--ppr_field', default="CODEZONE", type=str, required=False, help="Field name of PPRi zoning. Default: 'CODEZONE'.")
    parser.add_argument('-pprr', '--ppr_red_values_list', nargs="+", default=['R1','R2','R3'], type=str, required=False, help="List of values for PPRi red zoning. Default: 'R1 R2 R3'.")
    parser.add_argument('-pprb', '--ppr_blue_values_list', nargs="+", default=['B1','B2','B2-1','B2-2','B3'], type=str, required=False, help="List of values for PPRi blue zoning. Default: 'B1 B2 B2-1 B2-2 B3'.")
    parser.add_argument('-epsg', '--epsg', default=2154, type=int, required=False, help="Projection of the output file. Default: 2154.")
    parser.add_argument('-ndv', '--no_data_value', default=0, type=int, required=False, help="Value of the NoData pixel. Default: 0.")
    parser.add_argument('-raf', '--format_raster', default="GTiff", type=str, required=False, help="Format of raster file. Default: 'GTiff'.")
    parser.add_argument('-vef', '--format_vector', default="ESRI Shapefile", type=str, required=False, help="Format of vector file. Default: 'ESRI Shapefile'.")
    parser.add_argument('-rae', '--extension_raster', default=".tif", type=str, required=False, help="Extension file for raster file. Default: '.tif'.")
    parser.add_argument('-vee', '--extension_vector', default=".shp", type=str, required=False, help="Extension file for vector file. Default: '.shp'.")
    parser.add_argument('-pgh', '--postgis_ip_host', default="localhost", type=str, required=False, help="PostGIS server name or IP adress. Default: 'localhost'.")
    parser.add_argument('-pgp', '--postgis_num_port', default=5432, type=int, required=False, help="PostGIS port number. Default: '5432'.")
    parser.add_argument('-pgu', '--postgis_user_name', default="postgres", type=str, required=False, help="PostGIS user name. Default: 'postgres'.")
    parser.add_argument('-pgw', '--postgis_password', default="postgres", type=str, required=False, help="PostGIS user password. Default: 'postgres'.")
    parser.add_argument('-pgd', '--postgis_database_name', default="database", type=str, required=False, help="PostGIS database name. Default: 'database'.")
    parser.add_argument('-pgs', '--postgis_schema_name', default="public", type=str, required=False, help="PostGIS schema name. Default: 'public'.")
    parser.add_argument('-pge', '--postgis_encoding', default="latin1", type=str, required=False, help="PostGIS encoding for vector import. Default: 'latin1'.")
    parser.add_argument('-log', '--path_time_log', default="", type=str, required=False, help="Option: Name of log. Default, no log file.")
    parser.add_argument('-sav', '--save_results_intermediate', action='store_true', default=False, required=False, help="Option: Save intermediate result after the process. Default, False.")
    parser.add_argument('-now', '--overwrite', action='store_false', default=True, required=False, help="Option: Overwrite files with same names. Default, True.")
    parser.add_argument('-debug', '--debug', default=3, type=int, required=False, help="Option: Value of level debug trace. Default, 3.")
    args = displayIHM(gui, parser)

    # Récupération du fichier parcellaire d'entrée
    if args.input_plot_vector != None:
        input_plot_vector = args.input_plot_vector
        if not os.path.isfile(input_plot_vector):
            raise NameError (cyan + "AreasUnderUrbanization: " + bold + red  + "File %s not exists (input_plot_vector)." % input_plot_vector + endC)

    # Récupération du fichier parcellaire de sortie
    if args.output_plot_vector != None:
        output_plot_vector = args.output_plot_vector

    # Récupération du fichier d'emprise
    if args.footprint_vector != None:
        footprint_vector = args.footprint_vector
        if not os.path.isfile(footprint_vector):
            raise NameError (cyan + "AreasUnderUrbanization: " + bold + red  + "File %s not exists (footprint_vector)." % footprint_vector + endC)

    # Récupération du fichier bâti (mode raster)
    if args.input_built_file != None:
        input_built_file = args.input_built_file
        if input_built_file != "" and not os.path.isfile(input_built_file):
            raise NameError (cyan + "AreasUnderUrbanization: " + bold + red  + "File %s not exists (input_built_file)." % input_built_file + endC)

    # Récupération des fichiers bâti (mode vecteurs)
    if args.input_built_vector_list != None:
        input_built_vector_list = args.input_built_vector_list
        if input_built_vector_list != []:
            for input_built_vector in input_built_vector_list:
                if not os.path.isfile(input_built_vector):
                    raise NameError (cyan + "AreasUnderUrbanization: " + bold + red  + "File %s not exists (input_built_vector_list)." % input_built_vector + endC)

    # Récupération du fichier PLU
    if args.input_plu_vector != None:
        input_plu_vector = args.input_plu_vector
        if input_plu_vector != "" and not os.path.isfile(input_plu_vector):
            raise NameError (cyan + "AreasUnderUrbanization: " + bold + red  + "File %s not exists (input_plu_vector)." % input_plu_vector + endC)

    # Récupération du fichier PPRi
    if args.input_ppr_vector != None:
        input_ppr_vector = args.input_ppr_vector
        if input_ppr_vector != "" and not os.path.isfile(input_ppr_vector):
            raise NameError (cyan + "AreasUnderUrbanization: " + bold + red  + "File %s not exists (input_ppr_vector)." % input_ppr_vector + endC)

    # Récupération du paramètre de la taille minimale de bâti
    if args.min_built_size_list != None:
        min_built_size_list = args.min_built_size_list

    # Récupération des paramètres liés au PLU
    if args.plu_field != None:
        plu_field = args.plu_field
    if args.plu_u_values_list != None:
        plu_u_values_list = args.plu_u_values_list
    if args.plu_au_values_list != None:
        plu_au_values_list = args.plu_au_values_list

    # Récupération des paramètres liés au PPRi
    if args.ppr_field != None:
        ppr_field = args.ppr_field
    if args.ppr_red_values_list != None:
        ppr_red_values_list = args.ppr_red_values_list
    if args.ppr_blue_values_list != None:
        ppr_blue_values_list = args.ppr_blue_values_list

    # Récupération des paramètres fichiers
    if args.epsg != None:
        epsg = args.epsg
    if args.no_data_value != None:
        no_data_value = args.no_data_value
    if args.format_raster != None:
        format_raster = args.format_raster
    if args.format_vector != None:
        format_vector = args.format_vector
    if args.extension_raster != None:
        extension_raster = args.extension_raster
    if args.extension_vector != None:
        extension_vector = args.extension_vector

    # Récupération des paramètres PostGIS
    if args.postgis_ip_host != None:
        postgis_ip_host = args.postgis_ip_host
    if args.postgis_num_port != None:
        postgis_num_port = args.postgis_num_port
    if args.postgis_user_name != None:
        postgis_user_name = args.postgis_user_name
    if args.postgis_password != None:
        postgis_password = args.postgis_password
    if args.postgis_database_name != None:
        postgis_database_name = args.postgis_database_name
    if args.postgis_schema_name != None:
        postgis_schema_name = args.postgis_schema_name
    if args.postgis_encoding != None:
        postgis_encoding = args.postgis_encoding

    # Récupération des paramètres généraux
    if args.path_time_log != None:
        path_time_log = args.path_time_log
    if args.save_results_intermediate != None:
        save_results_intermediate = args.save_results_intermediate
    if args.overwrite != None:
        overwrite = args.overwrite
    if args.debug != None:
        global debug
        debug = args.debug

    if input_built_file == "" and input_built_vector_list == []:
        raise NameError (cyan + "AreasUnderUrbanization: " + bold + red  + "No built input file(s)." + endC)

    if os.path.isfile(output_plot_vector) and not overwrite:
        raise NameError (cyan + "AreasUnderUrbanization: " + bold + red  + "File %s already exists, and overwrite is not activated." % output_plot_vector + endC)

    if debug >= 3:
        print('\n' + bold + green + "Zones en voie d'urbanisation - Variables dans le parser :" + endC)
        print(cyan + "    AreasUnderUrbanization : " + endC + "input_plot_vector : " + str(input_plot_vector) + endC)
        print(cyan + "    AreasUnderUrbanization : " + endC + "output_plot_vector : " + str(output_plot_vector) + endC)
        print(cyan + "    AreasUnderUrbanization : " + endC + "footprint_vector : " + str(footprint_vector) + endC)
        print(cyan + "    AreasUnderUrbanization : " + endC + "input_built_file : " + str(input_built_file) + endC)
        print(cyan + "    AreasUnderUrbanization : " + endC + "input_built_vector_list : " + str(input_built_vector_list) + endC)
        print(cyan + "    AreasUnderUrbanization : " + endC + "input_plu_vector : " + str(input_plu_vector) + endC)
        print(cyan + "    AreasUnderUrbanization : " + endC + "input_ppr_vector : " + str(input_ppr_vector) + endC)
        print(cyan + "    AreasUnderUrbanization : " + endC + "min_built_size_list : " + str(min_built_size_list) + endC)
        print(cyan + "    AreasUnderUrbanization : " + endC + "plu_field : " + str(plu_field) + endC)
        print(cyan + "    AreasUnderUrbanization : " + endC + "plu_u_values_list : " + str(plu_u_values_list) + endC)
        print(cyan + "    AreasUnderUrbanization : " + endC + "plu_au_values_list : " + str(plu_au_values_list) + endC)
        print(cyan + "    AreasUnderUrbanization : " + endC + "ppr_field : " + str(ppr_field) + endC)
        print(cyan + "    AreasUnderUrbanization : " + endC + "ppr_red_values_list : " + str(ppr_red_values_list) + endC)
        print(cyan + "    AreasUnderUrbanization : " + endC + "ppr_blue_values_list : " + str(ppr_blue_values_list) + endC)
        print(cyan + "    AreasUnderUrbanization : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "    AreasUnderUrbanization : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "    AreasUnderUrbanization : " + endC + "format_raster : " + str(format_raster) + endC)
        print(cyan + "    AreasUnderUrbanization : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "    AreasUnderUrbanization : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "    AreasUnderUrbanization : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "    AreasUnderUrbanization : " + endC + "postgis_ip_host : " + str(postgis_ip_host) + endC)
        print(cyan + "    AreasUnderUrbanization : " + endC + "postgis_num_port : " + str(postgis_num_port) + endC)
        print(cyan + "    AreasUnderUrbanization : " + endC + "postgis_user_name : " + str(postgis_user_name) + endC)
        print(cyan + "    AreasUnderUrbanization : " + endC + "postgis_password : " + str(postgis_password) + endC)
        print(cyan + "    AreasUnderUrbanization : " + endC + "postgis_database_name : " + str(postgis_database_name) + endC)
        print(cyan + "    AreasUnderUrbanization : " + endC + "postgis_schema_name : " + str(postgis_schema_name) + endC)
        print(cyan + "    AreasUnderUrbanization : " + endC + "postgis_encoding : " + str(postgis_encoding) + endC)
        print(cyan + "    AreasUnderUrbanization : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "    AreasUnderUrbanization : " + endC + "save_results_inter : " + str(save_results_intermediate) + endC)
        print(cyan + "    AreasUnderUrbanization : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "    AreasUnderUrbanization : " + endC + "debug : " + str(debug) + endC + '\n')

    # Création du dossier de sortie, s'il n'existe pas
    if not os.path.isdir(os.path.dirname(output_plot_vector)):
        os.makedirs(os.path.dirname(output_plot_vector))

    # EXECUTION DE LA FONCTION
    buildablePlot(input_plot_vector, output_plot_vector, footprint_vector, input_built_file, input_built_vector_list, input_plu_vector, input_ppr_vector, min_built_size_list, plu_field, plu_u_values_list, plu_au_values_list, ppr_field, ppr_red_values_list, ppr_blue_values_list, epsg, no_data_value, format_raster, format_vector, extension_raster, extension_vector, postgis_ip_host, postgis_num_port, postgis_user_name, postgis_password, postgis_database_name, postgis_schema_name, postgis_encoding, path_time_log, save_results_intermediate, overwrite)

if __name__ == '__main__':
    main(gui=False)

