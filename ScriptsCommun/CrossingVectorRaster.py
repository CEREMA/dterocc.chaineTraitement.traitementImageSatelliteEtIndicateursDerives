#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT FAIT UN CROISEMENT DES DONNEES VECTEUR VERS UN FICHIER RASTER POUR EN EXTRAIRE DES STATISTIQUES                                    #
#                                                                                                                                           #
#############################################################################################################################################
"""
Nom de l'objet : CrossingVectorRaster.py
Description :
-------------
Objectif : Calcule les statstiques de l'intersection d'un image_input (tif) pour chaque polygones d'un jeu de vecteurs (shape)

Date de creation : 01/10/2014
----------
Histoire :
----------
Origine : nouveau

-----------------------------------------------------
Modifications :

------------------------------------------------------
A Reflechir/A faire :

"""
# Import des bibliothèques python
from __future__ import print_function
import os,sys,glob,argparse,shutil
from osgeo import ogr
#from rasterstats2 import raster_stats
from rasterstats2 import zonal_stats
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_log import timeLine
from Lib_raster import getPixelSizeImage, getEmpriseImage, identifyPixelValues
from Lib_vector import getEmpriseVector, cleanMiniAreaPolygons
from Lib_file import copyVectorFile, removeVectorFile, renameVectorFile
from Lib_postgis import createDatabase, dropDatabase, openConnection, closeConnection, importVectorByOgr2ogr, importRaster, exportVectorByOgr2ogr, executeQuery

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 2

###########################################################################################################################################
# FONCTION cleanSmallPolygons()                                                                                                           #
###########################################################################################################################################
def cleanSmallPolygons(vector_file, clean_small_polygons, pixel_size, format_vector='ESRI Shapefile', extension_vector='shp') :
    """
    # ROLE:
    #     Fonction qui supprime les très petits polygones si demander
    #
    # ENTREES DE LA FONCTION :
    #    vector_file : Fichier vecteur d'entrée / de sortie
    #    clean_small_polygons : flag de suppression
    #    pixel_size : taille du pixel du fichier raster
    #    format_vector : format du fichier vecteur. Optionnel, par default : 'ESRI Shapefile'
    #
    # SORTIES DE LA FONCTION :
    #    Le fichier vecteur d'entrée modifié
    #
    """
    if clean_small_polygons:
        min_size_area = pixel_size * 2
        vector_temp = os.path.splitext(vector_file)[0] + "_temp" + extension_vector

        cleanMiniAreaPolygons(vector_file, vector_temp, min_size_area, '', format_vector)
        removeVectorFile(vector_file, format_vector)
        renameVectorFile(vector_temp, vector_file)
    return

###########################################################################################################################################
# FONCTION deleteColumn()                                                                                                                 #
###########################################################################################################################################
def deleteColumn(vector_file, col_to_delete_list, format_vector='ESRI Shapefile') :
    """
    # ROLE:
    #     Fonction qui supprime une liste de colonne si demander
    #
    # ENTREES DE LA FONCTION :
    #    vector_file : Fichier vecteur d'entrée / de sortie
    #    col_to_delete_list : liste des colonnes a suprimer
    #    format_vector : format du fichier vecteur. Optionnel, par default : 'ESRI Shapefile'
    #
    # SORTIES DE LA FONCTION :
    #    Le fichier vecteur d'entrée modifié
    #
    """
    if col_to_delete_list != []:

       # Récuperation du driver pour le format shape
        driver = ogr.GetDriverByName(format_vector)

        # Ouverture du fichier shape en lecture-écriture
        data_source = driver.Open(vector_file, 1) # 0 means read-only - 1 means writeable.
        if data_source is None:
            print(cyan + "deleteColumn() : " + bold + red + "Impossible d'ouvrir le fichier vecteur : " + vector_file + endC, file=sys.stderr)
            sys.exit(1) # exit with an error code

        # Récupération du vecteur
        layer = data_source.GetLayer(0)         # Recuperation de la couche (une couche contient les polygones)
        layer_definition = layer.GetLayerDefn() # GetLayerDefn => returns the field names of the user defined (created) fields

        if debug >= 2:
            print(cyan + "deleteColumn() : " + bold + green + "DEBUT DES SUPPRESSIONS DES COLONNES %s" %(col_to_delete_list) + endC)

        for col_to_delete in col_to_delete_list :

            if layer_definition.GetFieldIndex(col_to_delete) != -1 :                   # Vérification de l'existence de la colonne col (retour = -1 : elle n'existe pas)

                layer.DeleteField(layer_definition.GetFieldIndex(col_to_delete))       # Suppression de la colonne

                if debug >= 3:
                    print(cyan + "deleteColumn() : " + endC + "Suppression de %s" %(col_to_delete) + endC)

        # Fermeture du fichier shape
        layer.SyncToDisk()
        layer = None
        data_source.Destroy()

        if debug >= 2:
            print(cyan + "deleteColumn() : " + bold + green + "FIN DE LA SUPPRESSION DES COLONNES" + endC)

    else:
        print(cyan + "deleteColumn() : " + bold + yellow + "AUCUNE SUPPRESSION DE COLONNE DEMANDEE" + endC)
    return
###########################################################################################################################################
# FONCTION statisticsVectorRaster_sql()                                                                                                   #
###########################################################################################################################################
def statisticsVectorRaster_sql(image_input, vector_input, vector_output, band_number, enable_stats_all_count, enable_stats_columns_str, enable_stats_columns_real, col_to_delete_list,  class_label_dico, no_data_value, epsg, project_encoding, server_postgis, port_number, user_postgis, password_postgis, database_postgis, schema_postgis, path_time_log, format_vector='ESRI Shapefile', save_results_intermediate=False, overwrite=True) :
    """
    # ROLE:
    #     Fonction qui calcule pour chaque polygone d'un fichier vecteur (shape) les statistiques associées de l'intersection avec une image raster (tif) en traitement sous postgis
    #
    # ENTREES DE LA FONCTION :
    #     image_input : Fichier image raster de la classification information pour le calcul des statistiques
    #     vector_input : Fichier vecteur d'entrée defini les zones de polygones pour le calcul des statistiques
    #     vector_output : Fichier vecteur de sortie
    #     band_number : Numero de bande du fichier image d'entree à utiliser
    #     enable_stats_all_count : Active le calcul statistique 'all','count' sur les pixels de l'image raster
    #     enable_stats_columns_str : Active le calcul statistique 'majority','minority' sur les pixels de l'image raster
    #     enable_stats_columns_real : Active le calcul statistique 'min', 'max', 'mean' , 'median','sum', 'std', 'unique', 'range' sur les pixels de l'image raster.
    #     col_to_delete_list : liste des colonnes à suprimer
    #     class_label_dico : dictionaire affectation de label aux classes de classification
    #     no_data_value : Option : Value pixel of no data, par defaut = 0
    #     epsg : EPSG code de projection
    #     project_encoding : encodage des fichiers d'entrés
    #     server_postgis : nom du serveur postgis
    #     port_number : numéro du port pour le serveur postgis
    #     user_postgis : le nom de l'utilisateurs postgis
    #     password_postgis : le mot de passe de l'utilisateur posgis
    #     database_postgis : le nom de la base posgis à utiliser
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
    starting_event = "statisticsVectorRaster_sql() : Statistics vector/raster starting : "
    timeLine(path_time_log,starting_event)

    print(endC)
    print(bold + green + "## START : SQL STATS VECTOR / RASTER" + endC)
    print(endC)

    if debug >= 2:
        print(bold + green + "statisticsVectorRaster_sql() : Variables dans la fonction" + endC)
        print(cyan + "statisticsVectorRaster_sql() : " + endC + "image_input : " + str(image_input) + endC)
        print(cyan + "statisticsVectorRaster_sql() : " + endC + "vector_input : " + str(vector_input) + endC)
        print(cyan + "statisticsVectorRaster_sql() : " + endC + "vector_output : " + str(vector_output) + endC)
        print(cyan + "statisticsVectorRaster_sql() : " + endC + "band_number : " + str(band_number) + endC)
        print(cyan + "statisticsVectorRaster_sql() : " + endC + "enable_stats_all_count : " + str(enable_stats_all_count) + endC)
        print(cyan + "statisticsVectorRaster_sql() : " + endC + "enable_stats_columns_str : " + str(enable_stats_columns_str) + endC)
        print(cyan + "statisticsVectorRaster_sql() : " + endC + "enable_stats_columns_real : " + str(enable_stats_columns_real) + endC)
        print(cyan + "statisticsVectorRaster_sql() : " + endC + "col_to_delete_list : " + str(col_to_delete_list) + endC)
        print(cyan + "statisticsVectorRaster_sql() : " + endC + "class_label_dico : " + str(class_label_dico) + endC)
        print(cyan + "statisticsVectorRaster_sql() : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "statisticsVectorRaster_sql() : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "statisticsVectorRaster_sql() : " + endC + "project_encoding : " + str(project_encoding) + endC)
        print(cyan + "statisticsVectorRaster_sql() : " + endC + "server_postgis : " + str(server_postgis) + endC)
        print(cyan + "statisticsVectorRaster_sql() : " + endC + "port_number : " + str(port_number) + endC)
        print(cyan + "statisticsVectorRaster_sql() : " + endC + "user_postgis : " + str(user_postgis) + endC)
        print(cyan + "statisticsVectorRaster_sql() : " + endC + "password_postgis : " + str(password_postgis) + endC)
        print(cyan + "statisticsVectorRaster_sql() : " + endC + "database_postgis : " + str(database_postgis) + endC)
        print(cyan + "statisticsVectorRaster_sql() : " + endC + "schema_postgis : " + str(schema_postgis) + endC)
        print(cyan + "statisticsVectorRaster_sql() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "statisticsVectorRaster_sql() : " + endC + "path_time_log : " + str(format_vector) + endC)
        print(cyan + "statisticsVectorRaster_sql() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "statisticsVectorRaster_sql() : " + endC + "overwrite : " + str(overwrite) + endC)

    # Création de la base de données
    table_vector_input = os.path.splitext(os.path.basename(vector_input))[0].lower()
    table_raster_input = os.path.splitext(os.path.basename(image_input))[0].lower()
    table_raster_pg = table_raster_input + "_pg"
    table_stats_output = os.path.splitext(os.path.basename(vector_output))[0].lower()
    table_stats_tmp = os.path.splitext(os.path.basename(vector_output))[0].lower() + "_tmp"

    createDatabase(database_postgis, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema_name=schema_postgis)

    # Import des fichiers vecteur  et raster dans la base
    importVectorByOgr2ogr(database_postgis, vector_input, table_vector_input, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema_name=schema_postgis, epsg=str(epsg), codage=project_encoding)

    importRaster(database_postgis, image_input, band_number, table_raster_input, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema_name=schema_postgis, epsg=str(epsg), nodata_value=no_data_value)


    # Connexion à la base SQL postgis
    connection = openConnection(database_postgis, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema_name=schema_postgis)

    ############################################
    # Croisement vecteur rasteur avec postgres #
    ############################################

    # Optimisation creation de l'index spatial pour le fichier vecteur d'entrée
    #query = "CREATE INDEX space_vector_idx ON %s USING GIST (geom);" %(table_vector_input)
    #executeQuery(connection, query)
    #query = "CLUSTER %s USING space_vector_idx;" %(table_vector_input)
    #executeQuery(connection, query)

    # Récupérer les colonnes de la table vecteur d'entrée, sauf la clé primaire et la géométrie
    query = f"SELECT column_name\n"
    query += f"FROM information_schema.columns\n"
    query += f"WHERE table_name = '{table_vector_input}'\n"
    query += f"AND column_name NOT IN ('ogc_fid', 'geom');\n"
    cursor = connection.cursor()
    cursor.execute(query)
    vector_input_columns = [row[0] for row in cursor.fetchall()]
    cursor.close()
    vector_columns_str = ", ".join([f"b.{col}" for col in vector_input_columns])

    # Creation de la table raster pg
    query = "drop table if exists %s;" %(table_raster_pg)
    if debug >= 4:
        print(query)
    executeQuery(connection, query)

    query = "create table %s as\n" %(table_raster_pg)
    query += "select (ST_DumpAsPolygons(rast)).val, (ST_DumpAsPolygons(rast)).geom\n"
    query += "FROM %s;\n" %(table_raster_input)
    if debug >= 4:
        print(query)
    executeQuery(connection, query)

    # Optimisation creation de l'index spatial
    query = "CREATE INDEX space_raster_idx ON %s USING GIST (geom);" %(table_raster_pg)
    if debug >= 4:
        print(query)
    executeQuery(connection, query)
    query = "CLUSTER %s USING space_raster_idx;" %(table_raster_pg)
    if debug >= 4:
        print(query)
    executeQuery(connection, query)
    if debug >= 4:
        print(query)
    query = "REINDEX TABLE %s;" %(table_raster_pg)
    executeQuery(connection, query)

    # Suppression des valeur nodata
    query = "delete from %s where val = %s;" %(table_raster_pg, str(no_data_value))
    if debug >= 4:
        print(query)
    executeQuery(connection, query)

    # Supprimer la table si elle existe
    query = f"DROP TABLE IF EXISTS {table_stats_output};"
    if debug >= 4:
        print(query)
    executeQuery(connection, query)

    # Start Case enable_stats_columns_real #
    if enable_stats_columns_real :
        query = f"CREATE TABLE {table_stats_output} AS\n"
        query += f"WITH stats AS (\n"
        query += f"    SELECT \n"
        query += f"        b.ogc_fid AS fid, \n"
        query += f"        ST_Area(b.geom) AS total_area, \n"
        query += f"        b.geom AS input_geom, \n"
        query += f"        {vector_columns_str},\n"
        query += f"        MIN(CASE WHEN r.val <> {no_data_value} THEN r.val END)::NUMERIC(20,2) AS min,\n"
        query += f"        MAX(CASE WHEN r.val <> {no_data_value} THEN r.val END)::NUMERIC(20,2) AS max,\n"
        query += f"        ROUND(AVG(CASE WHEN r.val <> {no_data_value} THEN r.val END)::NUMERIC, 2)::NUMERIC(20,2) AS mean,\n"
        query += f"        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY CASE WHEN r.val <> {no_data_value} THEN r.val END)::NUMERIC(20,2) AS median,\n"
        query += f"        SUM(CASE WHEN r.val <> {no_data_value} THEN r.val END)::NUMERIC(20,2) AS sum,\n"
        query += f"        ROUND(STDDEV(CASE WHEN r.val <> {no_data_value} THEN r.val END)::NUMERIC, 2)::NUMERIC(20,2) AS std,\n"
        query += f"        COUNT(DISTINCT CASE WHEN r.val <> {no_data_value} THEN r.val END) AS unique,\n"
        query += f"        (MAX(CASE WHEN r.val <> {no_data_value} THEN r.val END) - MIN(CASE WHEN r.val <> {no_data_value} THEN r.val END))::NUMERIC(20,2) AS range\n"
        query += f"    FROM {table_vector_input} b\n"
        query += f"    JOIN {table_raster_pg} r\n"
        query += f"    ON ST_Intersects(b.geom, r.geom)\n"
        query += f"    GROUP BY b.ogc_fid, b.geom, {vector_columns_str}\n"
        query += f")\n"
        vector_columns_str2 =vector_columns_str.replace('b.','s.')
        query += f"SELECT \n"
        query += f"    s.fid, \n"
        query += f"    s.total_area, \n"
        query += f"    s.input_geom, \n"
        query += f"    {vector_columns_str2},\n"
        query += f"    s.min, \n"
        query += f"    s.max, \n"
        query += f"    s.mean, \n"
        query += f"    s.median, \n"
        query += f"    s.sum, \n"
        query += f"    s.std, \n"
        query += f"    s.unique, \n"
        query += f"    s.range \n"
        query += f"FROM stats s;\n"

        if debug >= 4:
            print(query)
        executeQuery(connection, query)

        # End Case enable_stats_columns_real #

    else : # Start Case enable_stats_all_count et enable_stats_columns_str #

        # Supprimer la table de statistiques précédente si elle existe
        query = "drop table if exists %s;" %(table_stats_tmp)
        if debug >= 4:
            print(query)
        executeQuery(connection, query)

        # Calcul des statistiques agrégées avec pourcentage pour chaque classe raster
        query = f"CREATE TABLE {table_stats_tmp} AS\n"
        query += f"WITH stats AS (\n"
        query += f"SELECT b.ogc_fid AS fid, r.val AS raster_val,\n"
        query += f"SUM(ST_Area(ST_Intersection(b.geom, r.geom))) AS intersect_area, ST_Area(b.geom) AS total_area\n"
        query += f"FROM {table_vector_input} b\n"
        query += f"JOIN {table_raster_pg} r\n"
        query += f"ON ST_Intersects(b.geom, r.geom)\n"
        query += f"GROUP BY b.ogc_fid, r.val, b.geom)\n"
        query += f"SELECT fid, total_area, raster_val, intersect_area, (intersect_area / total_area) * 100 AS percent_area\n"
        query += f"FROM stats;\n"
        if debug >= 4:
            print(query)
        executeQuery(connection, query)

        # Création de colonnes dynamiques pour chaque classe raster
        query = f"ALTER TABLE {table_stats_tmp}\n"
        query += f"ADD COLUMN input_geom geometry;\n"
        query += f"UPDATE {table_stats_tmp} s\n"
        query += f"SET input_geom = b.geom\n"
        query += f"FROM {table_vector_input} b\n"
        query += f"WHERE s.fid = b.ogc_fid;\n"
        if debug >= 4:
            print(query)
        executeQuery(connection, query)

        # Récupérer dynamiquement les classes de raster uniques
        query = f"SELECT DISTINCT raster_val FROM {table_stats_tmp} ORDER BY raster_val;"
        if debug >= 4:
            print(query)
        executeQuery(connection, query)

        # Construction des colonnes pour le pourcentage et les surfaces
        if enable_stats_all_count or enable_stats_columns_str :
            pivot_columns = ",\n".join([
                f"ROUND(CAST(MAX(CASE WHEN raster_val = {val} THEN percent_area ELSE 0 END) AS NUMERIC), 2)::NUMERIC(5,2) AS {str(class_label_dico[val])}, "
                f"ROUND(CAST(SUM(CASE WHEN raster_val = {val} THEN intersect_area ELSE 0 END) AS NUMERIC), 2)::NUMERIC(20,2) AS S_{str(class_label_dico[val])}"
                for val in class_label_dico.keys()
            ])

        query = f"CREATE TABLE {table_stats_output} AS\n"
        if enable_stats_columns_str:
            query += f"WITH class_stats AS (\n"
        query += f"SELECT b.ogc_fid AS fid, s.total_area, s.input_geom, {vector_columns_str}"

        # Ajout des colonnes pour chaque classe
        if enable_stats_all_count or enable_stats_columns_str :
            query += f",{pivot_columns}\n"
        else :
             query += f"\n"

        query += f"FROM {table_stats_tmp} s\n"
        query += f"JOIN {table_vector_input} b\n"
        query += f"ON s.fid = b.ogc_fid\n"
        query += f"GROUP BY  b.ogc_fid, {vector_columns_str}, s.total_area, s.input_geom"

        # Ajout des colonnes pour la classe majoritaire et minoritaire
        if enable_stats_columns_str:
            query += f"\n)\n"
            query += f"SELECT \n"
            query += f"    cs.*, \n"
            query += f"    CASE \n"

            for val, label in class_label_dico.items():
                query += f"        WHEN cs.{label} = (SELECT GREATEST({', '.join(f'cs.{l}' for l in class_label_dico.values())})) THEN '{label}'\n"
            query += f"    END AS majority,\n"
            query += f"    CASE \n"
            for val, label in class_label_dico.items():
                query += f"        WHEN cs.{label} = (SELECT LEAST({', '.join(f'cs.{l}' for l in class_label_dico.values())})) THEN '{label}'\n"
            query += f"    END AS minority\n"
            query += f"FROM class_stats cs"

        query += f";\n"

        if debug >= 4:
            print(query)
        executeQuery(connection, query)

        # Supprimer la table de statistiques tmp
        query = "drop table if exists %s;" %(table_stats_tmp)
        if debug >= 4:
            print(query)
        executeQuery(connection, query)

        # End Case enable_stats_all_count et enable_stats_columns_str #

    # Nettoyage des géométries non conformes (non-polygones)
    query = "delete from %s\n" %(table_stats_output)
    query += "where ST_GeometryType(input_geom) not in ('ST_Polygon', 'ST_MultiPolygon');\n"
    if debug >= 4:
        print(query)
    executeQuery(connection, query)

    # Déconnexion de la base de données, pour éviter les conflits d'accès
    closeConnection(connection)

    # Récupération de la base du fichier vecteur de sortie
    exportVectorByOgr2ogr(database_postgis, vector_output, table_stats_output, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema_name=schema_postgis, format_type=format_vector)

    # Suppression des colonnes non souhaitées
    if not enable_stats_all_count and enable_stats_columns_str :
        for val, class_name in class_label_dico.items() :
            col_to_delete_list.append(class_name)
            col_to_delete_list.append("S_" + str(class_name))
    deleteColumn(vector_output, col_to_delete_list, format_vector)

    # Suppression des fichiers intermédiaires
    if not save_results_intermediate :
        try :
            dropDatabase(database_postgis, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number))
        except :
            print(cyan + "statisticsVectorRaster_sql() : " + bold + yellow + "Attention impossible de supprimer la base de donnée : " + endC + database_postgis)

    print(endC)
    print(bold + green + "## END : SQL STATS VECTOR / RASTER" + endC)
    print(endC)

    # Mise à jour du Log
    ending_event = "statisticsVectorRaster_sql() :  Statistics vector/raster ending : "
    timeLine(path_time_log,ending_event)

    return

###########################################################################################################################################
# DEFINITION DE LA FONCTION statisticsVectorRaster                                                                                        #
###########################################################################################################################################
def statisticsVectorRaster(image_input, vector_input, vector_output, band_number, enable_stats_all_count, enable_stats_columns_str, enable_stats_columns_real, col_to_delete_list, col_to_add_list, class_label_dico, clean_small_polygons=False, no_data_value=0, format_vector='ESRI Shapefile', path_time_log="", save_results_intermediate=False, overwrite=True) :
    """
    # ROLE:
    #     Fonction qui calcule pour chaque polygone d'un fichier vecteur (shape) les statistiques associées de l'intersection avec une image raster (tif)
    #
    # ENTREES DE LA FONCTION :
    #    image_input : Fichier image raster de la classification information pour le calcul des statistiques
    #    vector_input : Fichier vecteur d'entrée defini les zones de polygones pour le calcul des statistiques
    #    vector_output : Fichier vecteur de sortie
    #    band_number : Numero de bande du fichier image d'entree à utiliser
    #    enable_stats_all_count : Active le calcul statistique 'all','count' sur les pixels de l'image raster
    #    enable_stats_columns_str : Active le calcul statistique 'majority','minority' sur les pixels de l'image raster
    #    enable_stats_columns_real : Active le calcul statistique 'min', 'max', 'mean' , 'median','sum', 'std', 'unique', 'range' sur les pixels de l'image raster.
    #    col_to_delete_list : liste des colonnes a suprimer
    #    col_to_add_list : liste des colonnes à ajouter
    #         NB: ce parametre n a de sens que sur une image rvb ou un MNT par exemple
    #    class_label_dico : dictionaire affectation de label aux classes de classification
    #    clean_small_polygons : Nettoyage des petits polygones, par defaut = False
    #    no_data_value : Option : Value pixel of no data, par defaut = 0
    #    format_vector : format du fichier vecteur. Optionnel, par default : 'ESRI Shapefile'
    #    path_time_log : le fichier de log de sortie
    #    save_results_intermediate : fichiers de sorties intermediaires nettoyees, par defaut = False
    #    overwrite : supprime ou non les fichiers existants ayant le meme nom
    #
    # SORTIES DE LA FONCTION :
    #    Eléments modifiés le fichier shape d'entrée
    #
    """

    # INITIALISATION
    if debug >= 3:
        print(cyan + "statisticsVectorRaster() : " + endC + "image_input : " + str(image_input) + endC)
        print(cyan + "statisticsVectorRaster() : " + endC + "vector_input : " + str(vector_input) + endC)
        print(cyan + "statisticsVectorRaster() : " + endC + "vector_output : " + str(vector_output) + endC)
        print(cyan + "statisticsVectorRaster() : " + endC + "band_number : " + str(band_number) + endC)
        print(cyan + "statisticsVectorRaster() : " + endC + "enable_stats_all_count : " + str(enable_stats_all_count) + endC)
        print(cyan + "statisticsVectorRaster() : " + endC + "enable_stats_columns_str : " + str(enable_stats_columns_str) + endC)
        print(cyan + "statisticsVectorRaster() : " + endC + "enable_stats_columns_real : " + str(enable_stats_columns_real) + endC)
        print(cyan + "statisticsVectorRaster() : " + endC + "col_to_delete_list : " + str(col_to_delete_list) + endC)
        print(cyan + "statisticsVectorRaster() : " + endC + "col_to_add_list : " + str(col_to_add_list) + endC)
        print(cyan + "statisticsVectorRaster() : " + endC + "class_label_dico : " + str(class_label_dico) + endC)
        print(cyan + "statisticsVectorRaster() : " + endC + "clean_small_polygons : " + str(clean_small_polygons) + endC)
        print(cyan + "statisticsVectorRaster() : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "statisticsVectorRaster() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "statisticsVectorRaster() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "statisticsVectorRaster() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "statisticsVectorRaster() : " + endC + "overwrite : " + str(overwrite) + endC)

    # Constantes
    PREFIX_AREA_COLUMN = "S_"

    # Mise à jour du Log
    starting_event = "statisticsVectorRaster() : Compute statistic crossing starting : "
    timeLine(path_time_log,starting_event)

    if debug >= 2:
        print(cyan + "statisticsVectorRaster() : " + bold + green + "ETAPE init : STATISTIQUE DU FICHIER RASTER %s" %(image_input) + endC)
        print(cyan + "statisticsVectorRaster() : " + bold + green + "ETAPE init : PAR LE FICHIER VECTEUR %s" %(vector_input) + endC)

    # creation du fichier vecteur de sortie
    if vector_output == "":
        vector_output = vector_input # Précisé uniquement pour l'affichage
    else :
        # Copy vector_output
        copyVectorFile(vector_input, vector_output, format_vector)

    # Vérifications
    image_xmin, image_xmax, image_ymin, image_ymax = getEmpriseImage(image_input)
    vector_xmin, vector_xmax, vector_ymin, vector_ymax = getEmpriseVector(vector_output, format_vector)

    if round(vector_xmin,4) < round(image_xmin,4) or round(vector_xmax,4) > round(image_xmax,4) or round(vector_ymin,4) < round(image_ymin,4) or round(vector_ymax,4) > round(image_ymax,4) :
        print(cyan + "statisticsVectorRaster() : " + bold + red + "image_xmin, image_xmax, image_ymin, image_ymax" + endC, image_xmin, image_xmax, image_ymin, image_ymax, file=sys.stderr)
        print(cyan + "statisticsVectorRaster() : " + bold + red + "vector_xmin, vector_xmax, vector_ymin, vector_ymax" + endC, vector_xmin, vector_xmax, vector_ymin, vector_ymax, file=sys.stderr)
        raise NameError(cyan + "statisticsVectorRaster() : " + bold + red + "The extend of the vector file (%s) is greater than the image file (%s)" %(vector_output,image_input) + endC)

    pixel_size = getPixelSizeImage(image_input)
    extension_vector = os.path.splitext(vector_output)[1]

    # Suppression des très petits polygones qui introduisent des valeurs NaN
    cleanSmallPolygons(vector_output, clean_small_polygons, pixel_size, format_vector, extension_vector)

    # Récuperation du driver pour le format shape
    driver = ogr.GetDriverByName(format_vector)

    # Ouverture du fichier shape en lecture-écriture
    data_source = driver.Open(vector_output, 1) # 0 means read-only - 1 means writeable.
    if data_source is None:
        print(cyan + "statisticsVectorRaster() : " + bold + red + "Impossible d'ouvrir le fichier shape : " + vector_output + endC, file=sys.stderr)
        sys.exit(1) # exit with an error code

    # Récupération du vecteur
    layer = data_source.GetLayer(0)         # Recuperation de la couche (une couche contient les polygones)
    layer_definition = layer.GetLayerDefn() # GetLayerDefn => returns the field names of the user defined (created) fields

    # Création automatique du dico de valeur si il n'existe pas
    if (enable_stats_all_count or enable_stats_columns_str) and class_label_dico == {}:
        image_values_list = identifyPixelValues(image_input)
        # Pour toutes les valeurs
        for id_value in image_values_list :
            class_label_dico[id_value] = str(id_value)
        # Suppression de la valeur no_data du dico label
        if no_data_value in class_label_dico :
            del class_label_dico[no_data_value]
    if debug >= 3:
        print(cyan + "statisticsVectorRaster() : " + endC + "class_label_dico : " + str(class_label_dico))

    # ETAPE 1/3 : CREATION DES COLONNES DANS LE FICHIER SHAPE
    if debug >= 2:
        print(cyan + "statisticsVectorRaster() : " + bold + green + "ETAPE 1/3 : DEBUT DE LA CREATION DES COLONNES DANS LE FICHIER VECTEUR %s" %(vector_output) + endC)

    # En entrée :
    # col_to_add_list = [UniqueID, majority/DateMaj/SrcMaj, minority, min, max, mean, median, sum, std, unique, range, all, count, all_S] - all traduisant le class_label_dico en autant de colonnes
    # Sous_listes de col_to_add_list à identifier pour des facilités de manipulations ultérieures:
    # col_to_add_inter01_list = [majority/DateMaj/SrcMaj, minority, min, max, mean, median, sum, std, unique, range]
    # col_to_add_inter02_list = [majority, minority, min, max, mean, median, sum, std, unique, range, all, count, all_S]
    # Construction des listes intermédiaires
    col_to_add_inter01_list = []

    # Valeurs à injecter dans des colonnes - Format String
    if enable_stats_columns_str :
        stats_columns_str_list = ['majority','minority']
        for e in stats_columns_str_list :
            col_to_add_list.append(e)

    # Valeurs à injecter dans des colonnes - Format Nbr
    if enable_stats_columns_real :
        stats_columns_real_list = ['min', 'max', 'mean' , 'median','sum', 'std', 'unique', 'range']
        for e in stats_columns_real_list :
            col_to_add_list.append(e)

    # Valeurs à injecter dans des colonnes - Format Nbr
    if enable_stats_all_count :
        stats_all_count_list = ['all','count']
        for e in stats_all_count_list :
            col_to_add_list.append(e)

    # Ajout colonne par colonne
    if "count" in col_to_add_list:
        col_to_add_inter01_list.append("count")
    if "majority" in col_to_add_list:
        col_to_add_inter01_list.append("majority")
    if "DateMaj" in col_to_add_list:
        col_to_add_inter01_list.append("DateMaj")
    if "SrcMaj" in col_to_add_list:
        col_to_add_inter01_list.append("SrcMaj")
    if "minority" in col_to_add_list:
        col_to_add_inter01_list.append("minority")
    if "min" in col_to_add_list:
        col_to_add_inter01_list.append("min")
    if "max" in col_to_add_list:
        col_to_add_inter01_list.append("max")
    if "mean" in col_to_add_list:
        col_to_add_inter01_list.append("mean")
    if "median" in col_to_add_list:
        col_to_add_inter01_list.append("median")
    if "sum" in col_to_add_list:
        col_to_add_inter01_list.append("sum")
    if "std" in col_to_add_list:
        col_to_add_inter01_list.append("std")
    if "unique" in col_to_add_list:
        col_to_add_inter01_list.append("unique")
    if "range" in col_to_add_list:
        col_to_add_inter01_list.append("range")

    # Copy de col_to_add_inter01_list dans col_to_add_inter02_list
    col_to_add_inter02_list = list(col_to_add_inter01_list)
    col_to_add_inter02_list.append("count")

    if "all" in col_to_add_list:
        col_to_add_inter02_list.append("all")
    if "all_S" in col_to_add_list:
        col_to_add_inter02_list.append("all_S")
        col_to_add_inter02_list.remove("all_S")
        col_to_add_inter02_list.insert(0,"all")
    if "DateMaj" in col_to_add_inter02_list:
        col_to_add_inter02_list.remove("DateMaj")
        col_to_add_inter02_list.insert(0,"majority")
    if "SrcMaj" in col_to_add_inter02_list:
        col_to_add_inter02_list.remove("SrcMaj")
        col_to_add_inter02_list.insert(0,"majority")

    # Valeurs à injecter dans des colonnes - Format Nbr
    if enable_stats_all_count :
        stats_all_count_list = ['all_S']
        for e in stats_all_count_list :
            col_to_add_list.append(e)

    # Creation de la colonne de l'identifiant unique
    if ("UniqueID" in col_to_add_list) or ("uniqueID" in col_to_add_list) or ("ID" in col_to_add_list):
        field_defn = ogr.FieldDefn("ID", ogr.OFTInteger)    # Création du nom du champ dans l'objet stat_classif_field_defn
        layer.CreateField(field_defn)
        if debug >= 3:
            print(cyan + "statisticsVectorRaster() : " + endC + "Creation de la colonne : ID")

    # Creation des colonnes de col_to_add_inter01_list ([majority/DateMaj/SrcMaj, minority, min, max, mean, median, sum, std, unique, range])
    for col in col_to_add_list:
        if layer_definition.GetFieldIndex(col) == -1 :                          # Vérification de l'existence de la colonne col (retour = -1 : elle n'existe pas)
            if col == 'majority' or col == 'minority' or col == 'DateMaj' or col == 'SrcMaj' :  # Identification de toutes les colonnes remplies en string
                stat_classif_field_defn = ogr.FieldDefn(col, ogr.OFTString)     # Création du champ (string) dans l'objet stat_classif_field_defn
                layer.CreateField(stat_classif_field_defn)
            elif col == 'mean' or col == 'median' or col == 'sum' or col == 'std' or col == 'unique' or col == 'range' or col == 'max' or col == 'min':
                stat_classif_field_defn = ogr.FieldDefn(col, ogr.OFTReal)       # Création du champ (real) dans l'objet stat_classif_field_defn
                # Définition de la largeur du champ
                stat_classif_field_defn.SetWidth(20)
                # Définition de la précision du champ valeur flottante
                stat_classif_field_defn.SetPrecision(2)
                layer.CreateField(stat_classif_field_defn)
            elif col == 'count':
                stat_classif_field_defn = ogr.FieldDefn(col, ogr.OFTInteger)    # Création du champ (int) dans l'objet stat_classif_field_defn
                stat_classif_field_defn.SetWidth(10)
                layer.CreateField(stat_classif_field_defn)  # Ajout du champ
            if debug >= 3:
                print(cyan + "statisticsVectorRaster() : " + endC + "Creation de la colonne : " + str(col))

    # Creation des colonnes reliées au dictionnaire
    if ('all' in col_to_add_list) or ('all_S' in col_to_add_list) :
        for col in class_label_dico:

            # Gestion du nom de la colonne correspondant à la classe
            name_col = class_label_dico[col]
            if len(name_col) > 10:
                name_col = name_col[:10]
                print(cyan + "statisticsVectorRaster() : " + bold + yellow + "Nom de la colonne trop long. Il sera tronque a 10 caracteres en cas d'utilisation: " + endC + name_col)

            # Gestion du nom de la colonne correspondant à la surface de la classe
            name_col_area =  PREFIX_AREA_COLUMN + name_col
            if len(name_col_area) > 10:
                name_col_area = name_col_area[:10]
                if debug >= 3:
                    print(cyan + "statisticsVectorRaster() : " + bold + yellow + "Nom de la colonne trop long. Il sera tronque a 10 caracteres en cas d'utilisation: " + endC + name_col_area)

            # Ajout des colonnes de % de répartition des éléments du raster
            if ('all' in col_to_add_list) :
                if layer_definition.GetFieldIndex(name_col) == -1 :                     # Vérification de l'existence de la colonne name_col (retour = -1 : elle n'existe pas)
                    stat_classif_field_defn = ogr.FieldDefn(name_col, ogr.OFTReal)      # Création du champ (real) dans l'objet stat_classif_field_defn
                    # Définition de la largeur du champ
                    stat_classif_field_defn.SetWidth(20)
                    # Définition de la précision du champ valeur flottante
                    stat_classif_field_defn.SetPrecision(2)
                    if debug >= 3:
                        print(cyan + "statisticsVectorRaster() : " + endC + "Creation de la colonne : " + str(name_col))
                    layer.CreateField(stat_classif_field_defn)                          #

            # Ajout des colonnes de surface des éléments du raster
            if ('all_S' in col_to_add_list) :
                if layer_definition.GetFieldIndex(name_col_area) == -1 :                # Vérification de l'existence de la colonne name_col_area (retour = -1 : elle n'existe pas)
                    stat_classif_field_defn = ogr.FieldDefn(name_col_area, ogr.OFTReal) # Création du nom du champ dans l'objet stat_classif_field_defn
                    # Définition de la largeur du champ
                    stat_classif_field_defn.SetWidth(20)
                    # Définition de la précision du champ valeur flottante
                    stat_classif_field_defn.SetPrecision(2)

                    if debug >= 3:
                        print(cyan + "statisticsVectorRaster() : " + endC + "Creation de la colonne : " + str(name_col_area))
                    layer.CreateField(stat_classif_field_defn)                          # Ajout du champ

    if debug >= 2:
        print(cyan + "statisticsVectorRaster() : " + bold + green + "ETAPE 1/3 : FIN DE LA CREATION DES COLONNES DANS LE FICHIER VECTEUR %s" %(vector_output)+ endC)

    # ETAPE 2/3 : REMPLISSAGE DES COLONNES DU VECTEUR
    if debug >= 2:
        print(cyan + "statisticsVectorRaster() : " + bold + green + "ETAPE 2/3 : DEBUT DU REMPLISSAGE DES COLONNES DU VECTEUR "+ endC)

    # Calcul des statistiques col_to_add_inter02_list = [majority, minority, min, max, mean, median, sum, std, unique, range, all, count, all_S] de croisement images_raster / vecteur
    # Utilisation de la librairie rasterstat
    if debug >= 3:
        print(cyan + "statisticsVectorRaster() : " + bold + green + "Calcul des statistiques " + endC + "Stats : %s" %(col_to_add_inter02_list) + endC)
        print(cyan + "statisticsVectorRaster() : " + bold + green + "Calcul des statistiques " + endC + "Vecteur : %s" %(vector_output) + endC)
        print(cyan + "statisticsVectorRaster() : " + bold + green + "Calcul des statistiques " + endC + "Raster : %s" %(image_input) + endC)
    #stats_info_list = raster_stats(vector_output, image_input, band_num=band_number, stats=col_to_add_inter02_list)
    stats_info_list = zonal_stats(vector_output, image_input, band_num=band_number, stats=col_to_add_inter02_list, all_touched=False, nodata=None)

    # Decompte du nombre de polygones
    num_features = layer.GetFeatureCount()
    if debug >= 3:
        print(cyan + "statisticsVectorRaster() : " +  bold + green + "Remplissage des colonnes polygone par polygone " + endC)
    if debug >= 3:
        print(cyan + "statisticsVectorRaster() : " + endC + "Nombre total de polygones : " + str(num_features))

    polygone_count = 0

    for polygone_stats in stats_info_list : # Pour chaque polygone représenté dans stats_info_list - et il y a autant de polygone que dans le fichier vecteur

        # Extraction de feature
        feature = layer.GetFeature(polygone_stats['__fid__'])

        polygone_count = polygone_count + 1

        if debug >= 3 and polygone_count%10000 == 0:
            print(cyan + "statisticsVectorRaster() : " + endC + "Avancement : %s polygones traites sur %s" %(polygone_count,num_features))
        if debug >= 5:
            print(cyan + "statisticsVectorRaster() : " + endC + "Traitement du polygone : ",  stats_info_list.index(polygone_stats) + 1)

        # Remplissage de l'identifiant unique
        if ("UniqueID" in col_to_add_list) or ("uniqueID" in col_to_add_list) or ("ID" in col_to_add_list):
            feature.SetField('ID', int(stats_info_list.index(polygone_stats)))

        # Initialisation à 0 des colonnes contenant le % de répartition de la classe - Verifier ce qu'il se passe si le nom dépasse 10 caracteres
        if ('all' in col_to_add_list) :
            for element in class_label_dico:
                name_col = class_label_dico[element]
                if len(name_col) > 10:
                    name_col = name_col[:10]
                feature.SetField(name_col,0)

        # Initialisation à 0 des colonnes contenant la surface correspondant à la classe - Verifier ce qu'il se passe si le nom dépasse 10 caracteres
        if ('all_S' in col_to_add_list) :
            for element in class_label_dico:
                name_col = class_label_dico[element]
                name_col_area =  PREFIX_AREA_COLUMN + name_col
                if len(name_col_area) > 10:
                    name_col_area = name_col_area[:10]
                feature.SetField(name_col_area,0)

        # Remplissage des colonnes contenant le % de répartition et la surface des classes
        if ('all' in col_to_add_list) or ('all_S' in col_to_add_list) :
            # 'all' est une liste des couples : (Valeur_du_pixel_sur_le_raster, Nbr_pixel_ayant_cette_valeur) pour le polygone observe.
            # Ex : [(0,183),(803,45),(801,4)] : dans le polygone, il y a 183 pixels de valeur 0, 45 pixels de valeur 803 et 4 pixels de valeur 801
            majority_all = polygone_stats['all']

            # Deux valeurs de pixel peuvent faire référence à une même colonne. Par exemple : les pixels à 201, 202, 203 peuvent correspondre à la BD Topo
            # Regroupement des éléments de majority_all allant dans la même colonne au regard de class_label_dico
            count_for_idx_couple = 0            # Comptage du nombre de modifications (suppression de couple) de majority_all pour adapter la valeur de l'index lors de son parcours

            # test si il existe des points du fichier raster dans le polygone
            if majority_all != None :
                for idx_couple in range(1,len(majority_all)) :  # Inutile d'appliquer le traitement au premier élément (idx_couple == 0)

                    idx_couple = idx_couple - count_for_idx_couple    # Prise en compte dans le parcours de majority_all des couples supprimés
                    couple = majority_all[idx_couple]                 # Ex : couple = (803,45)

                    if (couple is None) or (couple == "") :    # en cas de bug de rasterstats (erreur geometrique du polygone par exemple)
                        if debug >= 3:
                            print(cyan + "statisticsVectorRaster() : " + bold + red + "Probleme detecte dans la gestion du polygone %s" %(polygone_count) + endC, file=sys.stderr)
                        pass
                    else :
                        for idx_verif in range(idx_couple):
                            # Vérification au regard des éléments présents en amont dans majority_all
                            # Cas où le nom correspondant au label a déjà été rencontré dans majority_all
                            # Vérification que les pixels de l'image sont réferncés dans le dico
                            if not couple[0] in class_label_dico:
                                class_label_dico[couple[0]] = str(couple[0])
                                print(cyan + "statisticsVectorRaster() : " + bold + yellow + "The image file (%s) contain pixel value '%d' not identified into class_label_dico" %(image_input, couple[0]) + endC)
                                #raise NameError(cyan + "statisticsVectorRaster() : " + bold + red + "The image file (%s) contain pixel value '%d' not identified into class_label_dico" %(image_input, couple[0]) + endC)

                            if class_label_dico[couple[0]] == class_label_dico[majority_all[idx_verif][0]]:
                                majority_all[idx_verif] = (majority_all[idx_verif][0] , majority_all[idx_verif][1] + couple[1])  # Ajout du nombre de pixels correspondant dans le couple précédent
                                majority_all.remove(couple)                                                                      # Supression du couple présentant le "doublon"
                                count_for_idx_couple = count_for_idx_couple + 1                                                  # Mise à jour du décompte de modifications
                                break

                # Intégration des valeurs de majority all dans les colonnes
                for couple_value_count in majority_all :                             # Parcours de majority_all. Ex : couple_value_count = (803,45)
                    if (couple_value_count is None) or (couple_value_count == "") :  # en cas de bug de rasterstats (erreur geometrique du polygone par exemple)
                        if debug >= 3:
                            print(cyan + "statisticsVectorRaster() : " + bold + red + "Probleme detecte dans la gestion du polygone %s" %(polygone_count) + endC, file=sys.stderr)
                        pass
                    else :
                        nb_pixel_total = polygone_stats['count']       # Nbr de pixels du polygone
                        pixel_value = couple_value_count[0]            # Valeur du pixel
                        value_count = couple_value_count[1]            # Nbr de pixels ayant cette valeur
                        name_col = class_label_dico[pixel_value]       # Transformation de la valeur du pixel en "signification" au regard du dictionnaire. Ex : BD Topo ou 2011
                        name_col_area =  PREFIX_AREA_COLUMN + name_col # Identification du nom de la colonne en surfaces

                        if len(name_col) > 10:
                            name_col = name_col[:10]
                        if len(name_col_area) > 10:
                            name_col_area = name_col_area[:10]

                        value_area = pixel_size * value_count                                    # Calcul de la surface du polygone correspondant à la valeur du pixel
                        if nb_pixel_total != None and nb_pixel_total != 0:
                            percentage = (float(value_count)/float(nb_pixel_total)) * 100  # Conversion de la surface en pourcentages, arondi au pourcent
                        else :
                            if debug >= 3:
                                print(cyan + "statisticsVectorRaster() : " + bold + red + "Probleme dans l'identification du nombre de pixels du polygone %s : le pourcentage de %s est mis à 0" %(polygone_count,name_col)+ endC, file=sys.stderr)
                            percentage = 0.0

                        if ('all' in col_to_add_list) :
                            feature.SetField(name_col, percentage)      # Injection du pourcentage dans la colonne correpondante
                        if ('all_S' in col_to_add_list) :
                            feature.SetField(name_col_area, value_area) # Injection de la surface dans la colonne correpondante
            # Cas ou pas de point dans ce polygone
            else :
                print(cyan + "statisticsVectorRaster() : " + bold + yellow + "Attention ce polygone %s ne comtient pas d'information statistique du raster (info vide!)" %(polygone_count) + endC,)
        else :
            pass

        # Remplissage des colonnes statistiques demandées ( col_to_add_inter01_list = [DateMaj, SrcMaj, count, majority, minority, min, max, mean, median, sum, std, unique, range] )
        for stats in col_to_add_inter01_list :

            if (stats == 'DateMaj') or  (stats == 'SrcMaj') :            # Cas particulier de 'DateMaj' et 'SrcMaj' : le nom de la colonne est DateMaj ou SrcMaj, mais la statistique utilisée est identifiée par majority
                name_col = stats                                         # Nom de la colonne. Ex : 'DateMaj'
                value_statis = polygone_stats['majority']                # Valeur majoritaire. Ex : '203'
                if value_statis == None:
                    value_statis_class = 'nan'
                else :
                    value_statis_class = class_label_dico[value_statis]  # Transformation de la valeur au regard du dictionnaire. Ex : '2011'
                feature.SetField(name_col, value_statis_class)           # Ajout dans la colonne

            elif (stats == 'count') :
                name_col = stats
                feature.SetField(name_col,  polygone_stats['count'])     # Injection du nombre de pixels

            elif (stats is None) or (stats == "") or (polygone_stats[stats] is None) or (polygone_stats[stats]) == "" or (polygone_stats[stats]) == 'nan' :
                # En cas de bug de rasterstats (erreur geometrique du polygone par exemple)
                pass

            else :
                name_col = stats                                         # Nom de la colonne. Ex : 'majority', 'max'
                value_statis = polygone_stats[stats]                     # Valeur à associer à la colonne, par exemple '2011'

                if (name_col == 'majority' or name_col == 'minority') and (class_label_dico != [])  and (value_statis in class_label_dico): # Cas où la colonne fait référence à une valeur du dictionnaire
                    value_statis_class = class_label_dico[value_statis]
                else:
                    value_statis_class = value_statis

                if str(type(value_statis_class)) == "<class 'numpy.uint8'>" :
                    value_statis_class = int(value_statis_class)
                feature.SetField(name_col, value_statis_class)

        layer.SetFeature(feature)
        feature.Destroy()

    # Fermeture du fichier shape
    layer.SyncToDisk()
    layer = None
    data_source.Destroy()

    if debug >= 2:
        print(cyan + "statisticsVectorRaster() : " + bold + green + "ETAPE 2/3 : FIN DU REMPLISSAGE DES COLONNES DU VECTEUR %s" %(vector_output)+ endC)

    # ETAPE 3/3 : SUPRESSION DES COLONNES NON SOUHAITEES
    deleteColumn(vector_output, col_to_delete_list, format_vector)

    # Mise à jour du Log
    ending_event = "statisticsVectorRaster() : Compute statistic crossing ending : "
    timeLine(path_time_log,ending_event)

    return

###########################################################################################################################################
# MISE EN PLACE DU PARSER                                                                                                                 #
###########################################################################################################################################

# Code executé seulement dans le cas ou le script est lancé depuis une ligne de commande
# Il n'est pas executé lors d'un import CrossingVectorRaster.py
# Exemple de lancement en ligne de commande:
# python CrossingVectorRaster.py -i ../ImagesTestChaine/APTV_05/Resultats/APTV_05_classif.tif -v ../ImagesTestChaine/APTV_05/Resultats/APTV_05_classif_reaf_vectorised.shp -cld 0:Nuage 11000:Anthropise 21000:Ligneux -stc -sts -str -log ../ImagesTestChaine/APTV_05/fichierTestLog.txt
#
# python -m CrossingVectorRaster -i /mnt/RAM_disk/Stats_tets/LCZ_SPOT_2022_SICOVAL_emprise_optimisee.tif -v /mnt/RAM_disk/Stats_tets/communes_SICOVAL.shp -o /mnt/RAM_disk/Stats_tets/communes_SICOVAL_stats.shp -stc -cld 0:no_LCZ 1:LCZ_1 2:LCZ_2 3:LCZ_3 4:LCZ_4 5:LCZ_5 6:LCZ_6 7:LCZ_7 8:LCZ_8 9:LCZ_9 10:LCZ_10 11:LCZ_A 12:LCZ_B 13:LCZ_C 14:LCZ_D 15:LCZ_E 16:LCZ_F 17:LCZ_G  -postgis -ndv 0 -epsg 2154 -pe utf-8 -serv localhost -port 5433 -user postgres -pwd postgres -db raster_stats -sch public -d insee_arr insee_col insee_dep insee_reg cl_arrond cl_collter cl_depart cl_region capitale date_rct date_creat date_maj date_app date_conf
#
# python -m CrossingVectorRaster -i /mnt/RAM_disk/Stats_tets/radiance_nocturne_LuoJia1_2018_D31.tif -v /mnt/RAM_disk/Stats_tets/communes_SICOVAL.shp -o /mnt/RAM_disk/Stats_tets/radiance_SICOVAL_stats.shp  -postgis -ndv 100000 -epsg 2154 -pe utf-8 -serv localhost -port 5433 -user postgres -pwd postgres -db raster2_stats -sch public -d insee_arr insee_col insee_dep insee_reg cl_arrond cl_collter cl_depart cl_region capitale date_rct date_creat date_maj date_app date_conf -sav -str

def main(gui=False):

    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, prog="CrossingVectorRaster", description="\
    Info : Computes the statistics of the intersection of a image_input (tif) for each polygon of a set of vectors (shape). \n\
    Objectif : Calcule les statistiques de l'intersection d'un image_input (tif) pour chaque polygones d'un jeu de vecteurs (shape). \n\
    Example : python CrossingVectorRaster.py -i ../ImagesTestChaine/APTV_05/Resultats/APTV_05_classif.tif \n\
                                             -v ../ImagesTestChaine/APTV_05/Resultats/APTV_05_classif_reaf_vectorised.shp \n\
                                             -cld 0:Nuage 11000:Anthropise 21000:Ligneux \n\
                                             -stc -sts -str \n\
                                             -log ../ImagesTestChaine/APTV_05/fichierTestLog.txt")

    parser.add_argument('-i','--image_input',default="",help="Image_raster image to analyze", type=str, required=True)
    parser.add_argument('-v','--vector_input',default="",help="Vector space on which we want to compute statistics", type=str, required=True)
    parser.add_argument('-o','--vector_output',default="",help="Name of the output. If not precised, the output vector is the input_vector", type=str, required=False)
    parser.add_argument('-bn','--band_number',default=1,help="Number of band used to compute from image input", type=int, required=False)
    parser.add_argument('-postgis', '--statistic_postgis', action='store_true', default=False, help="Option : The statistics  rastrer/vector is realized by the tools postgis By default : False", required=False)
    parser.add_argument('-stc', '--stats_all_count', action='store_true',default=False, help="Option : enable compute statistics : 'all','count'. Need to activate class_label_dico", required=False)
    parser.add_argument('-sts', '--stats_columns_str', action='store_true',default=False, help="Option : enable compute statistics : 'majority','minority'. Need to activate class_label_dico.", required=False)
    parser.add_argument('-str', '--stats_columns_real', action='store_true', default=False, help="Option : enable compute statistics : 'min', 'max', 'mean' , 'median','sum', 'std', 'unique', 'range' ", required=False)
    parser.add_argument('-d','--col_to_delete_list',nargs="+",default=[],help="Existing column in attribute table that we want to delete. Ex : 'nbPixels meanB0 varB0'", type=str, required=False)
    parser.add_argument('-a','--col_to_add_list',nargs="+",default=[],help="Column in attribute table that we want to add. Ex : 'UniqueID all count majority minority min max mean median sum std unique range'", type=str, required=False)
    parser.add_argument("-cld", "--class_label_dico",nargs="+",default={}, help = "NB: to inquire if option stats_all_count is enable, dictionary of correspondence class Mandatory if all or count is un col_to_add_list. Ex: 0:Nuage 63:Vegetation 127:Bati 191:Voirie 255:Eau", type=str,required=False)
    parser.add_argument('-csp', '--clean_small_polygons', action='store_true', default=False, help="Clean polygons where area is smaller than 2 times the pixel area (which can introduce NaN values)", required=False)
    parser.add_argument('-epsg','--epsg', default=2154,help="EPSG code projection.", type=int, required=False)
    parser.add_argument('-pe','--project_encoding', default="latin1",help="Project encoding.", type=str, required=False)
    parser.add_argument('-serv','--server_postgis', default="localhost",help="Postgis serveur name or ip.", type=str, required=False)
    parser.add_argument('-port','--port_number', default=5432,help="Postgis port number.", type=int, required=False)
    parser.add_argument('-user','--user_postgis', default="postgres",help="Postgis user name.", type=str, required=False)
    parser.add_argument('-pwd','--password_postgis', default="postgres",help="Postgis password user.", type=str, required=False)
    parser.add_argument('-db','--database_postgis', default="raster_stats",help="Postgis database name.", type=str, required=False)
    parser.add_argument('-sch','--schema_postgis', default="public",help="Postgis schema name.", type=str, required=False)
    parser.add_argument('-ndv','--no_data_value', default=0, help="Option : Value of the pixel no data. By default : 0", type=int, required=False)
    parser.add_argument('-vef','--format_vector', default="ESRI Shapefile",help="Format of the output file.", type=str, required=False)
    parser.add_argument('-log','--path_time_log',default="",help="Name of log", type=str, required=False)
    parser.add_argument('-sav','--save_results_inter',action='store_true',default=False,help="Save or delete intermediate result after the process. By default, False", required=False)
    parser.add_argument('-now','--overwrite',action='store_false',default=True,help="Overwrite files with same names. By default : True", required=False)
    parser.add_argument('-debug','--debug',default=3,help="Option : Value of level debug trace, default : 3 ",type=int, required=False)
    args = displayIHM(gui, parser)

    # Récupération des arguments donnés
    if args.image_input != None:
        image_input = args.image_input
        if not os.path.isfile(image_input):
            raise NameError (cyan + "CrossingVectorRaster : " + bold + red  + "File %s not existe!" %(image_input) + endC)

    if args.vector_input != None:
        vector_input = args.vector_input
        if not os.path.isfile(vector_input):
            raise NameError (cyan + "CrossingVectorRaster : " + bold + red  + "File %s not existe!" %(vector_input) + endC)

    if args.vector_output != None:
        vector_output = args.vector_output

    # Numero de bande du raster d'entrée
    if args.band_number != None:
        band_number = args.band_number

    # Récupération du type d'outil pour les statistques rasterstat/postgis (par defaut rasterstat)
    if args.statistic_postgis != None:
        is_postgis = args.statistic_postgis

    # Options de groupe de colonnes à produire
    if args.stats_all_count != None:
        enable_stats_all_count = args.stats_all_count

    if args.stats_columns_str != None:
        enable_stats_columns_str = args.stats_columns_str

    if args.stats_columns_real != None:
        enable_stats_columns_real = args.stats_columns_real

    # Options listes des colonnes à ajouter et à suprimer
    if args.col_to_delete_list != None:
        col_to_delete_list = args.col_to_delete_list

    if args.col_to_add_list != None:
        col_to_add_list = args.col_to_add_list

    # Creation du dictionaire reliant les classes à leur label
    class_label_dico = {}
    if args.class_label_dico != None and args.class_label_dico != {}:
        for tmp_txt_class in args.class_label_dico:
            class_label_list = tmp_txt_class.split(':')
            class_label_dico[int(class_label_list[0])] = class_label_list[1]

    # Nettoyage des polygones dont surface < 2 fois surface d'un pixel
    if args.clean_small_polygons!= None:
        clean_small_polygons = args.clean_small_polygons

    # Récupération du code EPSG de la projection du shapefile
    if args.epsg != None :
        epsg = args.epsg

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

    # Parametres de valeur du nodata des fichiers d'entrés
    if args.no_data_value!= None:
        no_data_value = args.no_data_value

    # Récupération du format du fichier de sortie
    if args.format_vector != None :
        format_vector = args.format_vector

    # Récupération du nom du fichier log
    if args.path_time_log!= None:
        path_time_log = args.path_time_log

    # Sauvegarde des fichiers intermediaires
    if args.save_results_inter != None:
        save_results_intermediate = args.save_results_inter

    # Ecrasement des fichiers
    if args.overwrite!= None:
        overwrite = args.overwrite

    # Récupération de l'option niveau de debug
    if args.debug!= None:
        global debug
        debug = args.debug

    # Affichage des arguments récupérés
    if debug >= 3:
        print(bold + green + "Variables dans le parser" + endC)
        print(cyan + "CrossingVectorRaster : " + endC + "image_input : " + str(image_input) + endC)
        print(cyan + "CrossingVectorRaster : " + endC + "vector_input : " + str(vector_input) + endC)
        print(cyan + "CrossingVectorRaster : " + endC + "vector_output : " + str(vector_output) + endC)
        print(cyan + "CrossingVectorRaster : " + endC + "band_number : " + str(band_number) + endC)
        print(cyan + "CrossingVectorRaster : " + endC + "is_postgis : " + str(is_postgis) + endC)
        print(cyan + "CrossingVectorRaster : " + endC + "stats_all_count : " + str(enable_stats_all_count) + endC)
        print(cyan + "CrossingVectorRaster : " + endC + "stats_columns_str : " + str(enable_stats_columns_str) + endC)
        print(cyan + "CrossingVectorRaster : " + endC + "stats_columns_real : " + str(enable_stats_columns_real) + endC)
        print(cyan + "CrossingVectorRaster : " + endC + "col_to_delete_list : " + str(col_to_delete_list) + endC)
        print(cyan + "CrossingVectorRaster : " + endC + "col_to_add_list : " + str(col_to_add_list) + endC)
        print(cyan + "CrossingVectorRaster : " + endC + "class_label_dico : " + str(class_label_dico) + endC)
        print(cyan + "CrossingVectorRaster : " + endC + "clean_small_polygons : " + str(clean_small_polygons) + endC)
        print(cyan + "CrossingVectorRaster : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "CrossingVectorRaster : " + endC + "project_encoding : " + str(project_encoding) + endC)
        print(cyan + "CrossingVectorRaster : " + endC + "server_postgis : " + str(server_postgis) + endC)
        print(cyan + "CrossingVectorRaster : " + endC + "port_number : " + str(port_number) + endC)
        print(cyan + "CrossingVectorRaster : " + endC + "user_postgis : " + str(user_postgis) + endC)
        print(cyan + "CrossingVectorRaster : " + endC + "password_postgis : " + str(password_postgis) + endC)
        print(cyan + "CrossingVectorRaster : " + endC + "database_postgis : " + str(database_postgis) + endC)
        print(cyan + "CrossingVectorRaster : " + endC + "schema_postgis : " + str(schema_postgis) + endC)
        print(cyan + "CrossingVectorRaster : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "CrossingVectorRaster : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "CrossingVectorRaster : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "CrossingVectorRaster : " + endC + "save_results_inter : " + str(save_results_intermediate) + endC)
        print(cyan + "CrossingVectorRaster : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "CrossingVectorRaster : " + endC + "debug : " + str(debug) + endC)

    if not enable_stats_all_count and not enable_stats_columns_str and not enable_stats_columns_real and not col_to_add_list :
        print(cyan + "CrossingVectorRaster() : " + bold + red + "You did not fill up properly the parameters, please check before launching." + endC, file=sys.stderr)
        exit(0)

    # Si le dossier de sortie n'existe pas, on le crée
    repertory_output = os.path.dirname(vector_output)
    if not os.path.isdir(repertory_output):
        os.makedirs(repertory_output)

    # Execution de la fonction
    if is_postgis :
        # Statistiques image avec l'outil postgis
        statisticsVectorRaster_sql(image_input, vector_input, vector_output, band_number, enable_stats_all_count, enable_stats_columns_str, enable_stats_columns_real, col_to_delete_list, class_label_dico, no_data_value, epsg, project_encoding, server_postgis, port_number, user_postgis, password_postgis, database_postgis, schema_postgis, path_time_log, format_vector, save_results_intermediate, overwrite)
    else :
        # Statistiques image avec l'outil rasterstat
        statisticsVectorRaster(image_input, vector_input, vector_output, band_number, enable_stats_all_count, enable_stats_columns_str, enable_stats_columns_real, col_to_delete_list, col_to_add_list, class_label_dico, clean_small_polygons, no_data_value, format_vector, path_time_log, save_results_intermediate, overwrite)

# ================================================

if __name__ == '__main__':
  main(gui=False)
