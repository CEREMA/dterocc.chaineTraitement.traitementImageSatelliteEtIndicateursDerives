#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT POUR CRÉE UN BUFFER DE CHAQUE CÔTÉ DU TRAIT DE CÔTE                                                                                #
#                                                                                                                                           #
#############################################################################################################################################

"""
Nom de l'objet : EvolvingDirectionTDC.py
Description    :
----------------
Objectif   : Creation de buffer autour du trait de côte

Date de creation : 07/06/2016
"""

from __future__ import print_function
import argparse, sys, os, shutil, operator
from osgeo import osr, ogr
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_postgis import executeQuery, openConnection, closeConnection, createDatabase, createSchema, importVectorByOgr2ogr, exportVectorByOgr2ogr, postTable, dropSchema, dropDatabase
from Lib_vector import getAttributeNameList, addNewFieldVector, updateIndexVector, multigeometries2geometries, differenceVector, cutVector
from Lib_file import removeVectorFile, removeFile
from Lib_log import timeLine

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 3

###########################################################################################################################################
# FONCTION evolvingDirectionTDC()                                                                                                         #
###########################################################################################################################################
def evolvingDirectionTDC(input_tdc_shp, input_pts_mer_vector, output_dir, buffer_size, path_time_log, server_postgis="localhost", user_postgis="postgres", password_postgis="postgres", database_postgis="db_buffer_tdc", schema_name="directionevolution", port_number=5432, epsg=2154, project_encoding="UTF-8", format_vector="ESRI Shapefile", save_results_intermediate=True, overwrite=True):
    """
    # ROLE:
    #     Crée 1 buffer de chaque côté du trait de côte donné en entrée. Attribue -1 à ceux côté terre et +1 à ceux côté mer
    #
    # ENTREES DE LA FONCTION :
    #     input_tdc_shp : Fichier contenant le trait de côte de référence autour duquel seront créés les buffers
    #     input_pts_mer_vector : fichier vecteur contenant les points dans la mer pour l'identification du côté mer
    #     output_dir : le chemin du dossier de sortie pour les fichiers créés
    #     buffer_size : la taille du buffer
    #     path_time_log : le fichier de log de sortie
    #     server_postgis : nom du serveur postgis
    #     user_postgis : le nom de l'utilisateurs postgis
    #     password_postgis : le mot de passe de l'utilisateur posgis
    #     database_postgis : le nom de la base posgis à utiliser
    #     schema_postgis : le nom du schéma à utiliser
    #     port_number : numéro du port à utiliser. Uniquement testé avec le 5432 (valeur par défaut)
    #     epsg : Code EPSG des fichiers
    #     project_encoding  : encodage du projet, par défaut = 'UTF-8'
    #     format_vector  : format du vecteur de sortie, par defaut = 'ESRI Shapefile'
    #     save_results_intermediate : fichiers de sorties intermediaires non nettoyees, par defaut = True
    #     overwrite : ecrasement ou non des fichiers existants, par defaut = True
    # SORTIES DE LA FONCTION :
    #     Fichier contenant le buffer autour du trait de côte divisé en 2 par le trait de côte, avec attribut -1 côté terre et +1 côté mer
    #
    """

    # Mise à jour du Log
    starting_event = "evolvingDirectionTDC() : Select evolvingDirectionTDC starting : "
    timeLine(path_time_log,starting_event)

    if debug >= 3:
        print(bold + green + "Variables dans evolvingDirectionTDC - Variables générales" + endC)
        print(cyan + "evolvingDirectionTDC() : " + endC + "input_tdc_shp : " + str(input_tdc_shp) + endC)
        print(cyan + "evolvingDirectionTDC() : " + endC + "output_dir : " + str(output_dir) + endC)
        print(cyan + "evolvingDirectionTDC() : " + endC + "input_pts_mer_vector : " + str(input_pts_mer_vector) + endC)
        print(cyan + "evolvingDirectionTDC() : " + endC + "buffer_size : " + str(buffer_size) + endC)
        print(cyan + "evolvingDirectionTDC() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "evolvingDirectionTDC() : " + endC + "server_postgis : " + str(server_postgis) + endC)
        print(cyan + "evolvingDirectionTDC() : " + endC + "user_postgis : " + str(user_postgis) + endC)
        print(cyan + "evolvingDirectionTDC() : " + endC + "password_postgis : " + str(password_postgis) + endC)
        print(cyan + "evolvingDirectionTDC() : " + endC + "database_postgis : " + str(database_postgis) + endC)
        print(cyan + "evolvingDirectionTDC() : " + endC + "schema_name : " + str(schema_name) + endC)
        print(cyan + "evolvingDirectionTDC() : " + endC + "port_number : " + str(port_number) + endC)
        print(cyan + "evolvingDirectionTDC() : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "evolvingDirectionTDC() : " + endC + "project_encoding : " + str(project_encoding) + endC)
        print(cyan + "evolvingDirectionTDC() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "evolvingDirectionTDC() : " + endC + "save_results_inter : " + str(save_results_intermediate) + endC)
        print(cyan + "evolvingDirectionTDC() : " + endC + "overwrite : " + str(overwrite) + endC)

    print(bold + green + "## START : evolvingDirectionTDC" + endC)

    # Initialisation des constantes
    ID = "id"
    IDP = "idp"
    AREA = "area"
    NUM_SIDE = "num_side"
    LETTER_SID = "letter_sid"
    REP_TEMP = "temp_evolvingDirectionTDC"

    # Initialisation des variables
    repertory_temp = output_dir + os.sep + REP_TEMP
    extension_vector = os.path.splitext(os.path.split(input_tdc_shp)[1])[1]

    # Création du répertoire de sortie temporaire s'il n'existe pas déjà
    if not os.path.exists(repertory_temp):
        os.makedirs(repertory_temp)

    # Initialisation des noms des fichiers en sortie
    name_input_tdc = os.path.splitext(os.path.split(input_tdc_shp)[1])[0]
    name_input_pts_mer = os.path.splitext(os.path.split(input_pts_mer_vector)[1])[0]

    simple_geom_tdc_vector = repertory_temp + os.sep + "simple_linestring_" + name_input_tdc + extension_vector
    pos_offset_tdc_vector = repertory_temp + os.sep + "simple_linestring_pos_offset_" + name_input_tdc + extension_vector
    neg_offset_tdc_vector = repertory_temp + os.sep + "simple_linestring_neg_offset_" + name_input_tdc + extension_vector
    output_buffer_vector = repertory_temp + os.sep + "buffer_" + str(buffer_size) + "_" + name_input_tdc + extension_vector
    output_mini_buffer_vector = repertory_temp + os.sep + "mini_buffer_" + name_input_tdc + extension_vector

    output_divided_buffer_vector = repertory_temp + os.sep + "buffer_" + str(buffer_size) + "_divided_" + name_input_tdc + extension_vector
    output_divided_buffer_polygons_vector = repertory_temp + os.sep + "buffer_" + str(buffer_size) + "_divided_polygons_" + name_input_tdc + extension_vector
    output_divided_buffer_polygons_sens_vector = output_dir + os.sep + "buffer_" + str(buffer_size) + "_divided_polygons_sens_" + name_input_tdc + extension_vector

    #output_divided_buffer_polygons_sens_final_vector = output_dir + os.sep + "buffer_" + str(buffer_size) + "_divided_polygons_sens_final_" + name_input_tdc + extension_vector

    output_difference_vector = repertory_temp + os.sep + "difference_" + name_input_tdc + extension_vector
    output_intersection_vector = repertory_temp + os.sep + "intersection_pt_mer_" + name_input_tdc + "_" + name_input_pts_mer + extension_vector

    # Suppression des shapefiles s'ils existent déjà
    if os.path.exists(output_divided_buffer_vector):
        removeFile(output_divided_buffer_vector)
    if os.path.exists(output_buffer_vector):
        removeFile(output_buffer_vector)
    if os.path.exists(output_divided_buffer_polygons_sens_vector):
        removeFile(output_divided_buffer_polygons_sens_vector)

    #if os.path.exists(output_divided_buffer_polygons_sens_final_vector):
    #    removeFile(output_divided_buffer_polygons_sens_final_vector)

    if os.path.exists(output_intersection_vector):
        removeVectorFile(output_intersection_vector)

    # Initialisations des noms de tables pour la base de donnée
    table_input_tdc = "input_tdc"
    table_tdc_pos_offset = "input_tdc_pos_offset"
    table_tdc_neg_offset = "input_tdc_neg_offset"
    table_output_buffer = "output_buffer"
    table_output_mini_buffer = "output_mini_buffer"
    table_output_divided_buffer = "output_divided_buffer"

    ### Transformation du trait de côte multiligne en lignes simples

    # Remplissage des listes de champs
    fields_list = getAttributeNameList(input_tdc_shp, format_vector)

    # Transformation des multilignes en lignes
    multigeometries2geometries(input_tdc_shp, simple_geom_tdc_vector, fields_list, 'MULTILINESTRING', format_vector)

    # Ajout du champ ID contenant une valeur unique pour chaque feature
    addNewFieldVector(simple_geom_tdc_vector, ID.upper(), ogr.OFTInteger, 0, None, None, format_vector)
    updateIndexVector(simple_geom_tdc_vector, ID.upper(), format_vector)

    # Calcul distance points lignes et buffer positif et négatif pour le sens avec postgis
    computeDistanceAndBufferDirection_SQL(simple_geom_tdc_vector, output_buffer_vector, output_mini_buffer_vector, pos_offset_tdc_vector, neg_offset_tdc_vector, buffer_size, table_input_tdc, table_output_divided_buffer, table_output_buffer, table_output_mini_buffer, table_tdc_pos_offset, table_tdc_neg_offset, server_postgis, user_postgis, password_postgis, database_postgis, schema_name, port_number, epsg, project_encoding)

    # Calcul la difference de vecteurs
    differenceVector(output_mini_buffer_vector, output_buffer_vector, output_difference_vector, format_vector)
    multigeometries2geometries(output_difference_vector, output_divided_buffer_polygons_vector, [ID.upper()], 'MULTIPOLYGON', format_vector)

    # Supression des polygones supperieur à 2 de surface plus faible, pour un un même id
    filterTwoBiggestAreaPolygons(output_divided_buffer_polygons_vector, output_divided_buffer_polygons_sens_vector, ID, IDP, AREA, epsg, format_vector)

    # Definition du sens
    processingDefineDirection(pos_offset_tdc_vector, neg_offset_tdc_vector, input_pts_mer_vector, output_divided_buffer_polygons_sens_vector, output_intersection_vector, IDP, AREA, NUM_SIDE, LETTER_SID, epsg, format_vector)

    # Traitement du sens

    #processingDirectionOrigine(output_divided_buffer_polygons_vector, pos_offset_tdc_vector, neg_offset_tdc_vector, input_pts_mer_vector, output_intersection_vector, output_divided_buffer_polygons_sens_vector, output_divided_buffer_polygons_sens_final_vector, ID, IDP, AREA, NUM_SIDE, LETTER_SID, epsg, format_vector)

    # Suppression du repertoire temporaire
    if not save_results_intermediate and os.path.exists(repertory_temp):
        shutil.rmtree(repertory_temp)

    # Mise à jour du Log
    ending_event = "evolvingDirectionTDC() : evolving direction TDC ending : "
    timeLine(path_time_log,ending_event)

    return output_divided_buffer_polygons_sens_vector

###########################################################################################################################################
# FONCTION computeDistanceAndBufferDirection_SQL                                                                                          #
###########################################################################################################################################
def computeDistanceAndBufferDirection_SQL(input_simple_tdc_vector, output_buffer_vector, output_mini_buffer_vector, pos_offset_tdc_vector, neg_offset_tdc_vector, buffer_size, table_input_tdc, table_output_divided_buffer, table_output_buffer, table_output_mini_buffer, table_tdc_pos_offset, table_tdc_neg_offset, server_postgis, user_postgis, password_postgis, database_postgis, schema_name, port_number, epsg, project_encoding) :
    """
    # ROLE:
    #     Calculer les distances entre des points et les lignes du traits de cote
    #     Calcul des buffers positifs et negatifs utiles à la détermination du signe de la distance
    #
    # ENTREES DE LA FONCTION :
    #     input_simple_tdc_vector : fichier shape d'entrée contenant le trait de cote
    #     output_buffer_vector : fichier shape de sortie contenant le buffer
    #     output_mini_buffer_vector : fichier shape de sortie contenant le mini buffer
    #     pos_offset_tdc_vector : fichier shape de sortie contenant le tdc offset positif
    #     neg_offset_tdc_vector : fichier shape de sortie contenant le tdc offset négatif
    #     buffer_size : la taille du buffer
    #     table_input_tdc : Nom de la table contenant le trait de cote d'entrée
    #     table_output_divided_buffer : Nom de la table contenant le buffer divisé
    #     table_output_buffer : Nom de la table contenant le buffer
    #     table_output_mini_buffer : Nom de la table contenant le mini buffer
    #     table_tdc_pos_offset : Nom de la table contenant le trait de cote offset positif
    #     table_tdc_neg_offset : Nom de la table contenant le trait de cote offset negatif
    #     server_postgis : nom du serveur postgis
    #     user_postgis : le nom de l'utilisateurs postgis
    #     password_postgis : le mot de passe de l'utilisateur posgis
    #     database_postgis : le nom de la base posgis à utiliser
    #     schema_name : le nom du schéma à utiliser
    #     port_number : numéro du port à utiliser. Uniquement testé avec le 5432 (valeur par défaut)
    #     epsg : Code EPSG des fichiers
    #     project_encoding  : encodage du projet, par défaut = 'UTF-8'
    #
    # SORTIES DE LA FONCTION :
    #     les fichiers vecteurs contenant les distances et les fichiers vecteurs des buffers
    #
    """

    # Création de la base de données, du schéma
    createDatabase(database_postgis, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number))
    connection = openConnection(database_postgis, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema_name='')
    createSchema(connection, schema_name.lower()) # Création du schéma s'il n'existe pas
    closeConnection(connection)

    # Import du shapefile trait de côte dans la base de données
    table_input_tdc = importVectorByOgr2ogr(database_postgis, input_simple_tdc_vector, table_input_tdc, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema_name=schema_name, epsg=str(epsg), codage=project_encoding)
    connection = openConnection(database_postgis, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema_name=schema_name)

    # Création des tables
    query = """
        DROP TABLE IF EXISTS %s.%s;
        CREATE TABLE %s.%s (id serial, geom geometry(MULTIPOLYGON, %s));
        """ % (schema_name, table_output_divided_buffer, schema_name, table_output_divided_buffer, str(epsg))
    if debug >= 2:
        print(query + "\n")
    executeQuery(connection, query)

    query = """
        DROP TABLE IF EXISTS %s.%s;
        CREATE TABLE %s.%s (id serial, geom geometry(MULTIPOLYGON,%s));
        """ % (schema_name, table_output_buffer, schema_name, table_output_buffer, str(epsg))
    if debug >= 2:
        print(query + "\n")
    executeQuery(connection, query)

    query = """
        DROP TABLE IF EXISTS %s.%s;
        CREATE TABLE %s.%s (id serial, geom geometry(MULTIPOLYGON,%s));
        """ % (schema_name, table_output_mini_buffer, schema_name, table_output_mini_buffer, str(epsg))
    if debug >= 2:
        print(query + "\n")
    executeQuery(connection, query)

    query = """
        DROP TABLE IF EXISTS %s.%s;
        CREATE TABLE %s.%s (id serial, geom geometry(MULTIPOLYGON,%s));
        """ % (schema_name, table_output_mini_buffer, schema_name, table_output_mini_buffer, str(epsg))
    if debug >= 2:
        print(query + "\n")
    executeQuery(connection, query)

    query = """
        DROP TABLE IF EXISTS %s.%s;
        CREATE TABLE %s.%s (id serial, geom geometry(MULTIPOLYGON,%s));
        """ % (schema_name, table_tdc_pos_offset, schema_name, table_tdc_pos_offset, str(epsg))
    if debug >= 2:
        print(query + "\n")
    executeQuery(connection, query)

    query = """
        DROP TABLE IF EXISTS %s.%s;
        CREATE TABLE %s.%s (id serial, geom geometry(MULTIPOLYGON,%s));
        """ % (schema_name, table_tdc_neg_offset, schema_name, table_tdc_neg_offset, str(epsg))
    if debug >= 2:
        print(query + "\n")
    executeQuery(connection, query)

    # Création du buffer dans la table output_buffer
    query = """
        INSERT INTO %s.%s (geom)
        SELECT ST_GeometryFromText(ST_AsText(ST_Multi(ST_Buffer(line,%s,'endcap=flat join=round'))),%s)
        FROM (
            SELECT l.geom AS line
            FROM %s.%s l
        ) f;
        """ % (schema_name, table_output_buffer, str(buffer_size), str(epsg), schema_name, table_input_tdc)
    if debug >= 2:
        print(query + "\n")
    executeQuery(connection, query)

    # Création du mini buffer dans la table output_mini_buffer
    query = """
        INSERT INTO %s.%s (geom)
        SELECT ST_GeometryFromText(ST_AsText(ST_Multi(ST_Buffer(line,0.005))),%s)
        FROM (
            SELECT l.geom AS line
            FROM %s.%s l
        ) f;
        """ % (schema_name, table_output_mini_buffer, str(epsg), schema_name, table_input_tdc)
    if debug >= 2:
        print(query + "\n")
    executeQuery(connection, query)

    # Création trait de côte décalé en positif
    query = """
        INSERT INTO %s.%s (geom)
        SELECT ST_Multi(ST_Buffer(ST_OffsetCurve(ST_LineMerge(l.geom),0.01),0.005,'endcap=flat join=round'))
        FROM %s.%s AS l
        """ % (schema_name, table_tdc_pos_offset, schema_name, table_input_tdc)
    if debug >= 2:
        print(query + "\n")
    executeQuery(connection, query)

    # Création trait de côte décalé en négatif
    query = """
        INSERT INTO %s.%s (geom)
        SELECT ST_Multi(ST_Buffer(ST_OffsetCurve(ST_LineMerge(l.geom),-0.01),0.005,'endcap=flat join=round'))
        FROM %s.%s AS l
        """ % (schema_name, table_tdc_neg_offset, schema_name, table_input_tdc)
    if debug >= 2:
        print(query + "\n")
    executeQuery(connection, query)

    closeConnection(connection)

    # Export des shapefiles créés (buffer et buffer divisé en pos neg)
    exportVectorByOgr2ogr(database_postgis, output_buffer_vector, table_output_buffer, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema_name=schema_name)
    exportVectorByOgr2ogr(database_postgis, output_mini_buffer_vector, table_output_mini_buffer, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema_name=schema_name)
    exportVectorByOgr2ogr(database_postgis, pos_offset_tdc_vector, table_tdc_pos_offset, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema_name=schema_name)
    exportVectorByOgr2ogr(database_postgis, neg_offset_tdc_vector, table_tdc_neg_offset, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema_name=schema_name)

    return

###########################################################################################################################################
# FONCTION filterTwoBiggestAreaPolygons                                                                                                   #
###########################################################################################################################################
def filterTwoBiggestAreaPolygons(input_divided_buffer_polygons_vector, output_divided_buffer_polygons_sens_vector, ID, IDP, AREA, epsg=2154, format_vector="ESRI Shapefile") :
    """
    # ROLE:
    #     Selection et filtrage des 2 (ou du si seul) polygones ayant la plus grande surfaces avec un id unique
    #
    # ENTREES DE LA FONCTION :
    #     input_divided_buffer_polygons_vector : fichier shape d'entrée contenant les polygones divisés
    #     output_divided_buffer_polygons_sens_vector : fichier shape de sortie contenant les polygones filtrés
    #     ID : Constantes id
    #     IDP : Constantes idp
    #     AREA : Constantes area
    #     epsg : Code EPSG des fichiers
    #     format_vector  : format du vecteur de sortie, par defaut = 'ESRI Shapefile'
    #
    # SORTIES DE LA FONCTION :
    #     le fichier vecteur contenant les polygones filtrés : output_divided_buffer_polygons_sens_vector
    #
    """

    # Configuration du format vecteur
    driver = ogr.GetDriverByName(format_vector)

    # Création de la référence spatiale
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(epsg)

    ## Traitement de la couche buffers divisés pour ne garder que les polygones les plus gros (2 polygones les plus grands par id)

    # Ouverture du fichier vecteur d'entrée
    data_source_divided_buffer_polygons = driver.Open(input_divided_buffer_polygons_vector, 1)
    layer_divided_buffer_polygons = data_source_divided_buffer_polygons.GetLayer(0)

    # Recherche des id
    all_id_geom_dico = dict()
    for i in range(0, layer_divided_buffer_polygons.GetFeatureCount()):
        feature = layer_divided_buffer_polygons.GetFeature(i)
        id_field = feature.GetField(ID.upper())
        geom = feature.GetGeometryRef()
        if not id_field in all_id_geom_dico.keys() :
            all_id_geom_dico[id_field] = []
        all_id_geom_dico[id_field].append([geom.ExportToWkt(), geom.GetArea()])

    # Trie des polygons pour ne garder que les 2 plus grand, par même id
    for id_field_key in all_id_geom_dico.keys():
        polygons_list = all_id_geom_dico[id_field_key]
        polygon_sorted_list = sorted(polygons_list, reverse=True, key=operator.itemgetter(1))
        polygons_list = polygon_sorted_list[:2]
        all_id_geom_dico[id_field_key] = polygons_list

    # Création de la couche output_divided_buffer_polygons_sens_vector
    data_source_divided_buffer_polygons_sens = driver.CreateDataSource(output_divided_buffer_polygons_sens_vector)
    layer_divided_buffer_polygons_sens = data_source_divided_buffer_polygons_sens.CreateLayer(output_divided_buffer_polygons_sens_vector, srs, geom_type=ogr.wkbPolygon)
    defn_layer_output = layer_divided_buffer_polygons_sens.GetLayerDefn()

    # Création du champ id dans la nouvelle couche pour la recopie des id
    id_polygon_field = ogr.FieldDefn(IDP, ogr.OFTInteger)
    layer_divided_buffer_polygons_sens.CreateField(id_polygon_field)
    area_field = ogr.FieldDefn(AREA, ogr.OFTInteger)
    layer_divided_buffer_polygons_sens.CreateField(area_field)

    # Creation des polygones dans output_divided_buffer_polygons_sens_vector
    for id_field_key in all_id_geom_dico.keys():

        polygons_list = all_id_geom_dico[id_field_key]
        for polygon_area in polygons_list :
            # Création de l'élément (du polygone) de sortie selon le modèle
            feature = ogr.Feature(defn_layer_output)
            # Ajout de la valeur du champs ID et AREA à la feature
            feature.SetField(IDP,int(id_field_key))
            feature.SetField(AREA,float(polygon_area[1]))
            # Assignation de la géométrie d'entrée à l'élément de sortie
            geom = ogr.CreateGeometryFromWkt(polygon_area[0])
            feature.SetGeometry(geom)
            # Ajout de la feature au layer
            layer_divided_buffer_polygons_sens.CreateFeature(feature)
            layer_divided_buffer_polygons_sens.SyncToDisk()
            feature.Destroy()

    # Fermeture du fichier shape input_divided_buffer_polygons_vector
    data_source_divided_buffer_polygons.Destroy()

    # Fermeture du fichier shape output_divided_buffer_polygons_sens_vector
    layer_divided_buffer_polygons_sens.SyncToDisk()
    data_source_divided_buffer_polygons_sens.Destroy()

    return

###########################################################################################################################################
# FONCTION processingDefineDirection                                                                                                      #
###########################################################################################################################################
def processingDefineDirection(input_pos_offset_tdc_vector, input_neg_offset_tdc_vector, input_pts_mer_vector, output_divided_buffer_polygons_sens_vector, output_intersection_vector, IDP, AREA, NUM_SIDE, LETTER_SID, epsg=2154, format_vector="ESRI Shapefile") :
    """
    # ROLE:
    #     Identification du côté du trait de côté par rapport au TDC de référence, avec un champ lettre ('A' ou 'B') pour chaque tronçon de buffer
    #     Identification de la valeur du champ lettre correspondant à la mer ou à la terre
    #     Création du champ num_side contenant +1 côté mer et -1 côté mer
    #
    # ENTREES DE LA FONCTION :
    #     input_pos_offset_tdc_vector : fichier shape d'entrée contenant les polygones offset positif
    #     input_neg_offset_tdc_vector : fichier shape d'entrée contenant les polygones offset negatif
    #     input_pts_mer_vector : fichier shape d'entrée contenant les points mer
    #     output_divided_buffer_polygons_sens_vector : fichier shape de sortie contenant les polygones de sens
    #     output_intersection_vector : fichier shape de sortie contenant les polygones d'intersection
    #     IDP : Constantes idp
    #     AREA : Constantes area
    #     NUM_SIDE : Constantes num_side
    #     LETTER_SID : Constantes letter_sid
    #     epsg : Code EPSG des fichiers
    #     format_vector  : format du vecteur de sortie, par defaut = 'ESRI Shapefile'
    #
    # SORTIES DE LA FONCTION
    #
    """

    # Configuration du format vecteur
    driver = ogr.GetDriverByName(format_vector)

    # Création de la référence spatiale
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(epsg)

    ## Récupération des couches
    # Trait de côte décalé positivement
    data_source_pos_offset_tdc = driver.Open(input_pos_offset_tdc_vector, 0)
    layer_pos_offset_tdc = data_source_pos_offset_tdc.GetLayer()

    # Trait de côte décalé négativement
    data_source_neg_offset_tdc = driver.Open(input_neg_offset_tdc_vector, 0)
    layer_neg_offset_tdc = data_source_neg_offset_tdc.GetLayer()

    # Re-ouverure en ecriture du fichier des polygones filtrés
    data_source_divided_buffer_polygons_sens = driver.Open(output_divided_buffer_polygons_sens_vector, 1)
    layer_divided_buffer_polygons_sens = data_source_divided_buffer_polygons_sens.GetLayer()

    # Détermination du côté A ou B du polygone, avec l'intersection entre le buffer et le
    letter_side_field = ogr.FieldDefn(LETTER_SID, ogr.OFTString)
    layer_divided_buffer_polygons_sens.CreateField(letter_side_field)

    # Pour chaque polygone de buffer
    for i in range(layer_divided_buffer_polygons_sens.GetFeatureCount()):
        intersection = "D"
        aire_intersection_pos_list = []
        aire_intersection_neg_list = []
        max_aire_intersection_pos = 0
        max_aire_intersection_neg = 0
        feature_buffer = layer_divided_buffer_polygons_sens.GetFeature(i)
        geom_feature_buffer = feature_buffer.GetGeometryRef()

        # Pour chaque ligne de trait de côte décalée positivement
        for j in range(layer_pos_offset_tdc.GetFeatureCount()):
            # Récupération géométrie
            feature_pos_tdc = layer_pos_offset_tdc.GetFeature(j)
            geom_feature_pos_tdc = feature_pos_tdc.GetGeometryRef()
            if geom_feature_buffer.Intersects(geom_feature_pos_tdc) == 1:
                intersection = "A"
                geom_intersection_pos = geom_feature_buffer.Intersection(geom_feature_pos_tdc)
                aire_intersection_pos_list.append(geom_intersection_pos.GetArea())

        # Pour chaque ligne de trait de côte décalée positivement
        for k in range(layer_neg_offset_tdc.GetFeatureCount()):
            # Récupération géométrie
            feature_neg_tdc = layer_neg_offset_tdc.GetFeature(k)
            geom_feature_neg_tdc = feature_neg_tdc.GetGeometryRef()
            if geom_feature_buffer.Intersects(geom_feature_neg_tdc) == 1:
                geom_intersection_neg = geom_feature_buffer.Intersection(geom_feature_neg_tdc)
                aire_intersection_neg_list.append(geom_intersection_neg.GetArea())

        if aire_intersection_pos_list != []:
            max_aire_intersection_pos = sorted(aire_intersection_pos_list)[-1]
        if aire_intersection_neg_list != []:
            max_aire_intersection_neg = sorted(aire_intersection_neg_list)[-1]

        for k in range(0, layer_neg_offset_tdc.GetFeatureCount()):
            # Si le polygone de buffer intersecte déjà la ligne décalée positivement, on teste la plus grande aire intersectée entre la ligne + et la ligne -
            if intersection == "A":
                if max_aire_intersection_pos > max_aire_intersection_neg:
                    intersection = "A"
                    break
                elif max_aire_intersection_neg > max_aire_intersection_pos:
                    intersection = "B"
                    break
                else:
                    intersection = "C"
            elif max_aire_intersection_pos == 0 and max_aire_intersection_neg == 0:
                intersection = "C"
                break
            else:
                intersection = "B"
                break
        feature_buffer.SetField(LETTER_SID,intersection)
        layer_divided_buffer_polygons_sens.SetFeature(feature_buffer)

    # Récupération de la couche de points dans la mer
    data_source_pts_mer = driver.Open(input_pts_mer_vector, 0)
    layer_pts_mer = data_source_pts_mer.GetLayer(0)

    # Intersection points mer et buffer pour savoir de quel côté du buffer est la mer et attribuer A et B à terre (-1) ou mer (+1)
    data_source_intersection = driver.CreateDataSource(output_intersection_vector)
    layer_intersection = data_source_intersection.CreateLayer(output_intersection_vector, srs, geom_type=ogr.wkbPoint)
    intersection = layer_divided_buffer_polygons_sens.Intersection(layer_pts_mer, layer_intersection)

    # Récupération du côté mer avec l'intersection des points mer
    if layer_intersection.GetFeatureCount() == 0:
        print(cyan + "processingDefineDirection() : " + bold + red + "Attention, les points mer sont en dehors du buffer dans le fichier " + input_pts_mer_vector + ". Impossible de détecter le côté mer du buffer. Modifiez le fichier et relancez le calcul."+ endC, file=sys.stderr)
        print(cyan + "processingDefineDirection() : " + bold + red + "Intersection vide avec  " + output_divided_buffer_polygons_sens_vector + endC, file=sys.stderr)
        sys.exit(1)

    for i in range(0, layer_intersection.GetFeatureCount()):
        first_feature = layer_intersection.GetFeature(0)
        cote_mer = first_feature.GetField(LETTER_SID)
        if i >= 1:
            other_feature = layer_intersection.GetFeature(i)
            if other_feature.GetField(LETTER_SID) != cote_mer:
                print(cyan + "processingDefineDirection() : " + bold + red + str(layer_intersection.GetFeatureCount()) + endC, file=sys.stderr)
                print(cyan + "processingDefineDirection() : " + bold + red + "Attention, il y a un (des) point(s) mer de part et d'autre du trait de côte dans le fichier " + input_pts_mer_vector + ", ou les buffers sont trop gros et s'intersectent, vérifiez alors le fichier" + output_divided_buffer_polygons_sens_vector + ". Impossible de détecter le côté mer des buffers. Modifiez le fichier et relancez le calcul."+ endC, file=sys.stderr)
                sys.exit(1)

    # Création colonne +1 côté mer -1 côté terre
    num_side_field = ogr.FieldDefn(NUM_SIDE, ogr.OFTInteger)
    layer_divided_buffer_polygons_sens.CreateField(num_side_field)

    # Remplissage de la colonne
    for i in range(0, layer_divided_buffer_polygons_sens.GetFeatureCount()):
        feature = layer_divided_buffer_polygons_sens.GetFeature(i)
        if feature.GetField(LETTER_SID) == cote_mer:
            feature.SetField(NUM_SIDE,1)
        else:
            feature.SetField(NUM_SIDE,-1)
        layer_divided_buffer_polygons_sens.SetFeature(feature)


    # Fermeture des fichiers shape : input_pos_offset_tdc_vector, input_neg_offset_tdc_vector, input_pts_mer_vector, output_divided_buffer_polygons_sens_vector, output_intersection_vector
    data_source_pos_offset_tdc.Destroy()
    data_source_neg_offset_tdc.Destroy()
    data_source_pts_mer.Destroy()

    layer_divided_buffer_polygons_sens.SyncToDisk()
    data_source_divided_buffer_polygons_sens.Destroy()

    layer_intersection.SyncToDisk()
    data_source_intersection.Destroy()

    return

###########################################################################################################################################
# FONCTION processingDirectionOrigine                                                                                                     #
###########################################################################################################################################
def processingDirectionOrigine(input_divided_buffer_polygons_vector, input_pos_offset_tdc_vector, input_neg_offset_tdc_vector, input_pts_mer_vector, output_intersection_vector, output_divided_buffer_polygons_sens_vector, output_divided_buffer_polygons_sens_final_vector, ID, IDP, AREA, NUM_SIDE, LETTER_SID, epsg=2154, format_vector="ESRI Shapefile") :
    """
    # ROLE:
    #     Suppression des polygones avec un id unique
    #     Identification du côté du trait de côté par rapport au TDC de référence, avec un champ lettre ('A' ou 'B') pour chaque tronçon de buffer
    #     Identification de la valeur du champ lettre correspondant à la mer ou à la terre
    #     Création du champ num_side contenant +1 côté mer et -1 côté mer
    #
    # ENTREES DE LA FONCTION :
    #     input_divided_buffer_polygons_vector : fichier shape d'entrée contenant les polygones divisés
    #     input_pos_offset_tdc_vector : fichier shape d'entrée contenant les polygones offset positif
    #     input_neg_offset_tdc_vector : fichier shape d'entrée contenant les polygones offset negatif
    #     input_pts_mer_vector : fichier shape d'entrée contenant les points mer
    #     output_intersection_vector : fichier shape de sortie contenant les polygones d'intersection
    #     output_divided_buffer_polygons_sens_vector : fichier shape de sortie contenant les polygones de sens
    #     output_divided_buffer_polygons_sens_final_vector : fichier shape de sortie contenant les polygones  sens final
    #     ID : Constantes id
    #     IDP : Constantes idp
    #     AREA : Constantes area
    #     NUM_SIDE : Constantes num_side
    #     LETTER_SID : Constantes letter_sid
    #     epsg : Code EPSG des fichiers
    #     format_vector  : format du vecteur de sortie, par defaut = 'ESRI Shapefile'
    #
    # SORTIES DE LA FONCTION
    #
    """

    # Configuration du format vecteur
    driver = ogr.GetDriverByName(format_vector)

    # Création de la référence spatiale
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(epsg)

    ## Traitement de la couche buffers divisés pour ne garder que les polygones les plus gros (2 polygones les plus grands par id)
    data_source_divided_buffer_polygons = driver.Open(input_divided_buffer_polygons_vector, 1)
    layer_divided_buffer_polygons = data_source_divided_buffer_polygons.GetLayer(0)
    liste_unique_id = []
    liste_all_id = []

    # Recherche des id n'apparaissant qu'une fois
    for i in range(0, layer_divided_buffer_polygons.GetFeatureCount()):
        feature = layer_divided_buffer_polygons.GetFeature(i)
        liste_all_id.append(feature.GetField(ID.upper()))
        if feature.GetField(ID.upper()) not in liste_unique_id:
            liste_unique_id.append(feature.GetField(ID.upper()))

    # Création de la couche output_divided_buffer_polygons_sens_vector
    data_source_divided_buffer_polygons_sens = driver.CreateDataSource(output_divided_buffer_polygons_sens_vector)
    layer_divided_buffer_polygons_sens = data_source_divided_buffer_polygons_sens.CreateLayer(output_divided_buffer_polygons_sens_vector, srs, geom_type=ogr.wkbPolygon)

    # Création du champ id dans la nouvelle couche pour la recopie des id
    id_polygon_field = ogr.FieldDefn(IDP, ogr.OFTInteger)
    layer_divided_buffer_polygons_sens.CreateField(id_polygon_field)

    # Création de la couche output_divided_buffer_polygons_sens_final_vector
    data_source_divided_buffer_polygons_sens_final = driver.CopyDataSource(data_source_divided_buffer_polygons_sens, output_divided_buffer_polygons_sens_final_vector)
    layer_divided_buffer_polygons_sens_final = data_source_divided_buffer_polygons_sens_final.GetLayer()

    # Copie des polygones de input_divided_buffer_polygons_vector vers output_divided_buffer_polygons_sens_vector seulement si leur id apparaît plus de 2 fois dans layer_divided_buffer_polygons (suppression des polygones superposés)
    for i in range(0, layer_divided_buffer_polygons.GetFeatureCount()):
        feature = layer_divided_buffer_polygons.GetFeature(i)
        if liste_all_id.count(feature.GetField(ID.upper())) >= 2:
            layer_divided_buffer_polygons_sens.CreateFeature(feature)
            feature.SetField(ID,int(feature.GetField(ID.upper())))
            layer_divided_buffer_polygons_sens.SetFeature(feature)

    ## Recherche des 2 polygones de chaque id (max_areas_id_list) qui ont les aires (max_areas_list) les plus grandes dans output_divided_buffer_polygons_sens_vector
    # Création du champ "aire"
    area_field = ogr.FieldDefn(AREA, ogr.OFTInteger)
    layer_divided_buffer_polygons_sens.CreateField(area_field)
    layer_divided_buffer_polygons_sens_final.CreateField(area_field)
    current_idp = -1
    areas_list = []
    max_area_id_list = []
    max_areas_list = []
    for i in range(0, layer_divided_buffer_polygons_sens.GetFeatureCount()-1):
        feature = layer_divided_buffer_polygons_sens.GetFeature(i)
        if current_idp != feature.GetField(IDP):
            areas_list_sorted = sorted(areas_list)
            if areas_list_sorted != []:
                max_area_id_list.append(current_idp)
                max_area_id_list.append(current_idp)
                max_areas_list.append(areas_list_sorted[-1])
                max_areas_list.append(areas_list_sorted[-2])
            areas_list = []
        current_idp = feature.GetField(IDP)
        geom = feature.GetGeometryRef()
        areas_list.append(geom.GetArea())
        feature.SetField(AREA,geom.GetArea())
        layer_divided_buffer_polygons_sens.SetFeature(feature)

    # Remplissage aire du dernier polygone
    i_last_feature = layer_divided_buffer_polygons_sens.GetFeatureCount()-1
    feature = layer_divided_buffer_polygons_sens.GetFeature(i_last_feature)
    if current_idp == feature.GetField(IDP):
        geom = feature.GetGeometryRef()
        areas_list.append(geom.GetArea())
        feature.SetField(AREA,geom.GetArea())
        layer_divided_buffer_polygons_sens.SetFeature(feature)
        areas_list_sorted = sorted(areas_list)
        if len(areas_list_sorted) >= 2:
            max_area_id_list.append(current_idp)
            max_area_id_list.append(current_idp)
            max_areas_list.append(areas_list_sorted[-1])
            max_areas_list.append(areas_list_sorted[-2])

    # Copie des polygones de output_divided_buffer_polygons_sens_vector vers output_divided_buffer_polygons_sens_final_vector seulement pour les deux polygones de chaque id qui ont les aires les plus grandes
    for i in range(0, layer_divided_buffer_polygons_sens.GetFeatureCount()):
        feature = layer_divided_buffer_polygons_sens.GetFeature(i)
        for j in range(len(max_area_id_list)):
            if feature.GetField(IDP) == max_area_id_list[j] and feature.GetField(AREA) == int(max_areas_list[j]):
                layer_divided_buffer_polygons_sens_final.CreateFeature(feature)
                layer_divided_buffer_polygons_sens_final.SetFeature(feature)

    ## Récupération des couches
    # Trait de côte décalé positivement
    data_source_pos_offset_tdc = driver.Open(input_pos_offset_tdc_vector, 0)
    layer_pos_offset_tdc = data_source_pos_offset_tdc.GetLayer()

    # Trait de côte décalé négativement
    data_source_neg_offset_tdc = driver.Open(input_neg_offset_tdc_vector, 0)
    layer_neg_offset_tdc = data_source_neg_offset_tdc.GetLayer()

    # Détermination du côté A ou B du polygone, avec l'intersection entre le buffer et le
    letter_side_field = ogr.FieldDefn(LETTER_SID, ogr.OFTString)
    layer_divided_buffer_polygons_sens_final.CreateField(letter_side_field)

    # Pour chaque polygone de buffer
    for i in range(layer_divided_buffer_polygons_sens_final.GetFeatureCount()):
        intersection = "D"
        aire_intersection_pos_list = []
        aire_intersection_neg_list = []
        max_aire_intersection_pos = 0
        max_aire_intersection_neg = 0
        feature_buffer = layer_divided_buffer_polygons_sens_final.GetFeature(i)
        geom_feature_buffer = feature_buffer.GetGeometryRef()

        # Pour chaque ligne de trait de côte décalée positivement
        for j in range(layer_pos_offset_tdc.GetFeatureCount()):
            # Récupération géométrie
            feature_pos_tdc = layer_pos_offset_tdc.GetFeature(j)
            geom_feature_pos_tdc = feature_pos_tdc.GetGeometryRef()
            if geom_feature_buffer.Intersects(geom_feature_pos_tdc) == 1:
                intersection = "A"
                geom_intersection_pos = geom_feature_buffer.Intersection(geom_feature_pos_tdc)
                aire_intersection_pos_list.append(geom_intersection_pos.GetArea())

        # Pour chaque ligne de trait de côte décalée positivement
        for k in range(layer_neg_offset_tdc.GetFeatureCount()):
            # Récupération géométrie
            feature_neg_tdc = layer_neg_offset_tdc.GetFeature(k)
            geom_feature_neg_tdc = feature_neg_tdc.GetGeometryRef()
            if geom_feature_buffer.Intersects(geom_feature_neg_tdc) == 1:
                geom_intersection_neg = geom_feature_buffer.Intersection(geom_feature_neg_tdc)
                aire_intersection_neg_list.append(geom_intersection_neg.GetArea())

        if aire_intersection_pos_list != []:
            max_aire_intersection_pos = sorted(aire_intersection_pos_list)[-1]
        if aire_intersection_neg_list != []:
            max_aire_intersection_neg = sorted(aire_intersection_neg_list)[-1]

        for k in range(0, layer_neg_offset_tdc.GetFeatureCount()):
            # Si le polygone de buffer intersecte déjà la ligne décalée positivement, on teste la plus grande aire intersectée entre la ligne + et la ligne -
            if intersection == "A":
                if max_aire_intersection_pos > max_aire_intersection_neg:
                    intersection = "A"
                    break
                elif max_aire_intersection_neg > max_aire_intersection_pos:
                    intersection = "B"
                    break
                else:
                    intersection = "C"
            elif max_aire_intersection_pos == 0 and max_aire_intersection_neg == 0:
                intersection = "C"
                break
            else:
                intersection = "B"
                break
        feature_buffer.SetField(LETTER_SID,intersection)
        layer_divided_buffer_polygons_sens_final.SetFeature(feature_buffer)

    # Récupération de la couche de points dans la mer
    data_source_pts_mer = driver.Open(input_pts_mer_vector, 0)
    layer_pts_mer = data_source_pts_mer.GetLayer(0)

    # Intersection points mer et buffer pour savoir de quel côté du buffer est la mer et attribuer A et B à terre (-1) ou mer (+1)
    data_source_intersection = driver.CreateDataSource(output_intersection_vector)
    layer_intersection = data_source_intersection.CreateLayer(output_intersection_vector, srs, geom_type=ogr.wkbPoint)
    intersection = layer_divided_buffer_polygons_sens_final.Intersection(layer_pts_mer, layer_intersection)

    # Récupération du côté mer avec l'intersection des points mer
    if layer_intersection.GetFeatureCount() == 0:
        print(cyan + "processingDefineDirection() : " + bold + red + "Attention, les points mer sont en dehors du buffer dans le fichier " + input_pts_mer_vector + ". Impossible de détecter le côté mer du buffer. Modifiez le fichier et relancez le calcul."+ endC, file=sys.stderr)
        print(cyan + "processingDefineDirection() : " + bold + red + "Intersection vide avec  " + output_divided_buffer_polygons_sens_vector + endC, file=sys.stderr)
        sys.exit(1)

    for i in range(0, layer_intersection.GetFeatureCount()):
        first_feature = layer_intersection.GetFeature(0)
        cote_mer = first_feature.GetField(LETTER_SID)
        if i >= 1:
            other_feature = layer_intersection.GetFeature(i)
            if other_feature.GetField(LETTER_SID) != cote_mer:
                print(cyan + "processingDefineDirection() : " + bold + red + str(layer_intersection.GetFeatureCount()) + endC, file=sys.stderr)
                print(cyan + "processingDefineDirection() : " + bold + red + "Attention, il y a un (des) point(s) mer de part et d'autre du trait de côte dans le fichier " + input_pts_mer_vector + ", ou les buffers sont trop gros et s'intersectent, vérifiez alors le fichier" + output_divided_buffer_polygons_sens_vector + ". Impossible de détecter le côté mer des buffers. Modifiez le fichier et relancez le calcul."+ endC, file=sys.stderr)
                sys.exit(1)

    # Création colonne +1 côté mer -1 côté terre
    num_side_field = ogr.FieldDefn(NUM_SIDE, ogr.OFTInteger)
    layer_divided_buffer_polygons_sens_final.CreateField(num_side_field)

    # Remplissage de la colonne
    for i in range(0, layer_divided_buffer_polygons_sens_final.GetFeatureCount()):
        feature = layer_divided_buffer_polygons_sens_final.GetFeature(i)
        if feature.GetField(LETTER_SID) == cote_mer:
            feature.SetField(NUM_SIDE,1)
        else:
            feature.SetField(NUM_SIDE,-1)
        layer_divided_buffer_polygons_sens_final.SetFeature(feature)

    return

###########################################################################################################################################
# MISE EN PLACE DU PARSER                                                                                                                 #
###########################################################################################################################################

# Code executé seulement dans le cas ou le script est lancé depuis une ligne de commande
# Il n'est pas executé lors d'un import EvolvingDirectionTDC.py
# Exemple de lancement en ligne de commande:
# python /home/scgsi/Documents/ChaineTraitement/ScriptsLittoral/EvolvingDirectionTDC.py -tdc /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/08_Donnees/N_traits_cote_naturels_recents_L_012016_shape_cle2432b6/N_traits_cote_naturels_recents_L_012016/N_traits_cote_naturels_recents_L_zone_interet.shp -outd /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Images_test -mer /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Images_test/point_mer_distances.shp -bs 20

def main(gui=False):

    parser = argparse.ArgumentParser(prog="EvolvingDirectionTDC", description=" \
    Info : Creating a shapefile containing 2 uniside buffers, one on each side of the input coastline.\n\
    Objectif   : Crée un buffer de chaque côté du trait de côte, contenant un champ qui indique +1 côté mer et -1 côté terre. \n\
    Example : python /home/scgsi/Documents/ChaineTraitement/ScriptsLittoral/EvolvingDirectionTDC.py \n\
                    -tdc /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/08_Donnees/N_traits_cote_naturels_recents_L_012016_shape_cle2432b6/N_traits_cote_naturels_recents_L_012016/N_traits_cote_naturels_recents_L_zone_interet.shp \n\
                    -outd /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Images_test \n\
                    -bs 20 \n\
                    -mer /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Images_test/point_mer_distances.shp")

    parser.add_argument('-tdc','--input_tdc_shp', default="", help="Shapefile containing the coastline (.shp).", type=str, required=True)
    parser.add_argument('-mer','--input_pts_mer_vector', default="",help="Input vector file containing points in the sea (.shp).", type=str, required=True)
    parser.add_argument('-outd','--output_dir', default="",help="Output directory.", type=str, required=True)
    parser.add_argument('-bs','--buffer_size', default="",help="Size (meters) of the buffer.", type=int, required=True)
    parser.add_argument('-serv','--server_postgis', default="localhost",help="Postgis serveur name or ip.", type=str, required=False)
    parser.add_argument('-port','--port_number', default=5432,help="Postgis port number.", type=int, required=False)
    parser.add_argument('-user','--user_postgis', default="postgres",help="Postgis user name.", type=str, required=False)
    parser.add_argument('-pwd','--password_postgis', default="postgres",help="Postgis password user.", type=str, required=False)
    parser.add_argument('-db','--database_postgis', default="db_buffer_tdc",help="Postgis database name.", type=str, required=False)
    parser.add_argument('-sch','--schema_name', default="directionevolution",help="Postgis schema name.", type=str, required=False)
    parser.add_argument('-epsg','--epsg', default=2154,help="EPSG code projection.", type=int, required=False)
    parser.add_argument('-pe','--project_encoding', default="UTF-8",help="Project encoding.", type=str, required=False)
    parser.add_argument('-vef','--format_vector',default="ESRI Shapefile",help="Option : Vector format. By default : ESRI Shapefile", type=str, required=False)
    parser.add_argument('-log','--path_time_log',default=os.getcwd()+ os.sep + "log.txt",help="Option : Name of log. By default : log.txt", type=str, required=False)
    parser.add_argument('-sav','--save_results_inter',action='store_true',default=False,help="Option : Save or delete intermediate result after the process. By default, False", required=False)
    parser.add_argument('-now','--overwrite',action='store_false',default=True,help="Option : Overwrite files with same names. By default : True", required=False)
    parser.add_argument('-debug','--debug',default=3,help="Option : Value of level debug trace, default : 3 ",type=int, required=False)
    args = displayIHM(gui, parser)

    # Récupération du trait de côte à traiter
    if args.input_tdc_shp != None :
        input_tdc_shp = args.input_tdc_shp

    # Récupération des points dans la mer
    if args.input_pts_mer_vector != None :
        input_pts_mer_vector = args.input_pts_mer_vector

    # Récupération du fichier de sortie
    if args.output_dir != None :
        output_dir= args.output_dir

    # Récupération du fichier de log
    if args.path_time_log != None :
        path_time_log = args.path_time_log

    # Récupération de la taille du buffer
    if args.buffer_size != None :
        buffer_size= args.buffer_size

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
    if args.schema_name != None :
        schema_name = args.schema_name

    # Récupération du code EPSG de la projection du shapefile trait de côte
    if args.epsg != None :
        epsg = args.epsg

    # Récupération de l'encodage des fichiers
    if args.project_encoding != None :
        project_encoding = args.project_encoding

    # Récupération du nom du format des fichiers vecteur
    if args.format_vector != None:
        format_vector = args.format_vector

    # Récupération du booléen pour la sauvegarde des fichiers intermédiaires
    if args.save_results_inter != None :
        save_results_intermediate = args.save_results_inter

    # Récupération du booléen pour l'écrasement des fichiers s'ils existent déjà
    if args.overwrite != None :
        overwrite = args.overwrite

    # Récupération de l'option niveau de debug
    if args.debug!= None:
        global debug
        debug = args.debug

    # Affichage des arguments récupérés
    if debug >= 3:
        print(bold + green + "Variables dans le parser" + endC)
        print(cyan + "EvolvingDirectionTDC : " + endC + "input_tdc_shp : " + str(input_tdc_shp) + endC)
        print(cyan + "EvolvingDirectionTDC : " + endC + "output_dir : " + str(output_dir) + endC)
        print(cyan + "EvolvingDirectionTDC : " + endC + "input_pts_mer_vector : " + str(input_pts_mer_vector) + endC)
        print(cyan + "EvolvingDirectionTDC : " + endC + "buffer_size : " + str(buffer_size) + endC)
        print(cyan + "EvolvingDirectionTDC : " + endC + "server_postgis : " + str(server_postgis) + endC)
        print(cyan + "EvolvingDirectionTDC : " + endC + "port_number : " + str(port_number) + endC)
        print(cyan + "EvolvingDirectionTDC : " + endC + "user_postgis : " + str(user_postgis) + endC)
        print(cyan + "EvolvingDirectionTDC : " + endC + "password_postgis : " + str(password_postgis) + endC)
        print(cyan + "EvolvingDirectionTDC : " + endC + "database_postgis : " + str(database_postgis) + endC)
        print(cyan + "EvolvingDirectionTDC : " + endC + "schema_name : " + str(schema_name) + endC)
        print(cyan + "EvolvingDirectionTDC : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "EvolvingDirectionTDC : " + endC + "project_encoding : " + str(project_encoding) + endC)
        print(cyan + "EvolvingDirectionTDC : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "EvolvingDirectionTDC : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "EvolvingDirectionTDC : " + endC + "save_results_inter : " + str(save_results_intermediate) + endC)
        print(cyan + "EvolvingDirectionTDC : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "EvolvingDirectionTDC : " + endC + "debug : " + str(debug) + endC)

    # Fonction générale
    evolvingDirectionTDC(input_tdc_shp, input_pts_mer_vector, output_dir, buffer_size, path_time_log, server_postgis, user_postgis, password_postgis, database_postgis, schema_name, port_number, epsg, project_encoding, format_vector, save_results_intermediate, overwrite)

# ================================================

if __name__ == '__main__':
  main(gui=False)
