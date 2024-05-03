#!/usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

from __future__ import print_function
import os, sys, shutil, argparse
from osgeo import ogr
from Lib_log import timeLine
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_postgis import executeQuery, openConnection, closeConnection, createDatabase, dropDatabase, importVectorByOgr2ogr, exportVectorByOgr2ogr
from Lib_vector import renameFieldsVector, addNewFieldVector, getAttributeValues, setAttributeValuesList
from Lib_raster import getProjectionImage, identifyPixelValues
from Lib_file import removeVectorFile
from Lib_vector import getAttributeNameList
from CrossingVectorRaster import statisticsVectorRaster

# debug = 1 : affichage requête SQL
debug = 3

####################################################################################################
# FONCTION heightOfRoughnessElements()                                                             #
####################################################################################################
def heightOfRoughnessElements(grid_input, grid_output, built_input, grid_id_field, built_id_field, built_height_field, epsg, project_encoding, server_postgis, port_number, user_postgis, password_postgis, database_postgis, schema_postgis, path_time_log, format_vector='ESRI Shapefile', save_results_intermediate=False, overwrite=True):
    """
    # ROLE :
    #     Calcul de l'indicateur LCZ hauteur des élements de rugosité
    #
    # ENTREES DE LA FONCTION :
    #     grid_input : fichier de maillage en entrée
    #     grid_output : fichier de maillage en sortie
    #     built_input : fichier de bâti 3D en entrée
    #     grid_id_field : nom du champ contenant l'information id du fichier de maillage en entrée
    #     built_id_field : nom du champ contenant l'information id du fichier de bâti 3D en entrée
    #     built_height_field : nom du champ contenant l'information de hauteur du fichier de bâti 3D en entrée
    #     epsg : EPSG code de projection
    #     project_encoding : encodage des fichiers d'entrés
    #     server_postgis : nom du serveur postgis
    #     port_number : numéro du port pour le serveur postgis
    #     user_postgis : le nom de l'utilisateurs postgis
    #     password_postgis : le mot de passe de l'utilisateur posgis
    #     database_postgis : le nom de la base posgis à utiliser
    #     schema_postgis : le nom du schéma à utiliser
    #     path_time_log : fichier log de sortie
    #     format_vector : format du fichier vecteur. Optionnel, par default : 'ESRI Shapefile'
    #     save_results_intermediate : fichiers de sorties intermédiaires nettoyés, par défaut = False
    #     overwrite : écrase si un fichier existant a le même nom qu'un fichier de sortie, par défaut = True
    #
    # SORTIES DE LA FONCTION :
    #     N.A
    """

    print(bold + yellow + "Début du calcul de l'indicateur Height of Roughness Elements." + endC + "\n")
    timeLine(path_time_log, "Début du calcul de l'indicateur Height of Roughness Elements : ")

    if debug >= 3:
        print(bold + green + "heightOfRoughnessElements() : Variables dans la fonction" + endC)
        print(cyan + "heightOfRoughnessElements() : " + endC + "grid_input : " + str(grid_input) + endC)
        print(cyan + "heightOfRoughnessElements() : " + endC + "grid_output : " + str(grid_output) + endC)
        print(cyan + "heightOfRoughnessElements() : " + endC + "built_input : " + str(built_input) + endC)
        print(cyan + "HeightOfRoughnessElements() : " + endC + "grid_id_field : " + str(grid_id_field) + endC)
        print(cyan + "HeightOfRoughnessElements() : " + endC + "built_id_field : " + str(built_id_field) + endC)
        print(cyan + "HeightOfRoughnessElements() : " + endC + "built_height_field : " + str(built_height_field) + endC)
        print(cyan + "heightOfRoughnessElements() : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "heightOfRoughnessElements() : " + endC + "project_encoding : " + str(project_encoding) + endC)
        print(cyan + "heightOfRoughnessElements() : " + endC + "server_postgis : " + str(server_postgis) + endC)
        print(cyan + "heightOfRoughnessElements() : " + endC + "port_number : " + str(port_number) + endC)
        print(cyan + "heightOfRoughnessElements() : " + endC + "user_postgis : " + str(user_postgis) + endC)
        print(cyan + "heightOfRoughnessElements() : " + endC + "password_postgis : " + str(password_postgis) + endC)
        print(cyan + "heightOfRoughnessElements() : " + endC + "database_postgis : " + str(database_postgis) + endC)
        print(cyan + "heightOfRoughnessElements() : " + endC + "schema_postgis : " + str(schema_postgis) + endC)
        print(cyan + "heightOfRoughnessElements() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "heightOfRoughnessElements() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "heightOfRoughnessElements() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "heightOfRoughnessElements() : " + endC + "overwrite : " + str(overwrite) + endC)
        print("\n")

    if not os.path.exists(grid_output) or overwrite:

        ############################################
        ### Préparation générale des traitements ###
        ############################################

        print(bold + cyan + "Préparation au calcul de Height of Roughness Elements :" + endC)
        timeLine(path_time_log, "    Préparation au calcul de Height of Roughness Elements : ")

        if os.path.exists(grid_output):
            removeVectorFile(grid_output)

        # Création de la base de données PostGIS
        dropDatabase(database_postgis, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=port_number, schema_name=schema_postgis) # Conflits avec autres indicateurs (Aspect Ratio / Terrain Roughness Class)
        createDatabase(database_postgis, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=port_number, schema_name=schema_postgis)

        # Import des fichiers shapes maille et bati dans la base de données PostGIS
        table_name_maille = importVectorByOgr2ogr(database_postgis, grid_input, 'hre_maille', user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema_name=schema_postgis, epsg=str(epsg), codage=project_encoding)
        table_name_bati = importVectorByOgr2ogr(database_postgis, built_input, 'hre_bati', user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema_name=schema_postgis, epsg=str(epsg), codage=project_encoding)

        ###############################################
        ### Calcul de l'indicateur par requêtes SQL ###
        ###############################################

        print(bold + cyan + "Calcul de Height of Roughness Elements :" + endC)
        timeLine(path_time_log, "    Calcul de Height of Roughness Elements : ")

        # Création des index spatiaux (accélère les requêtes spatiales)
        query = """
        CREATE INDEX IF NOT EXISTS maille_geom_gist ON %s USING GIST (geom);
        CREATE INDEX IF NOT EXISTS bati_geom_gist ON %s USING GIST (geom);
        """ % (table_name_maille, table_name_bati)

        # Intersection et découpage de la couche du bâti avec la couche de maillage
        query += """
        DROP TABLE IF EXISTS hre_intersect;
        CREATE TABLE hre_intersect AS
            SELECT m.%s AS id, b.%s AS id_bati, b.%s AS hauteur, ST_Area(ST_Intersection(b.geom, m.geom)) AS surface, ST_Intersection(b.geom, m.geom) AS geom
            FROM %s AS b, %s AS m
            WHERE ST_Intersects(b.geom, m.geom)
                AND (ST_GeometryType(b.geom) = 'ST_Polygon' OR ST_GeometryType(b.geom) = 'ST_MultiPolygon')
                AND (ST_GeometryType(m.geom) = 'ST_Polygon' OR ST_GeometryType(m.geom) = 'ST_MultiPolygon');
        """ % (grid_id_field, built_id_field, built_height_field, table_name_bati, table_name_maille)

        # Calcul des indicateurs de morphologie urbaine dans les polygones du maillge intersectant du bâti
        query += """
        DROP TABLE IF EXISTS hre_notnull;
        CREATE TABLE hre_notnull AS
            SELECT m.%s AS id, avg(i.hauteur) AS mean_h, avg(i.surface) AS mean_a, m.geom AS geom
            FROM %s AS m, hre_intersect AS i
            WHERE m.%s = i.id
            GROUP BY m.%s, m.geom;
        """ % (grid_id_field, table_name_maille, grid_id_field, grid_id_field)

        # Attribution par défaut à 0 des indicateurs de morphologie urbaine dans les polygones du maillage n'intersectant pas du bâti
        query += """
        DROP TABLE IF EXISTS hre_isnull;
        CREATE TABLE hre_isnull AS
            SELECT DISTINCT %s AS id, geom AS geom
            FROM %s
            WHERE %s NOT IN
                (SELECT DISTINCT id
                FROM hre_notnull);
        ALTER TABLE hre_isnull ADD mean_h DOUBLE PRECISION DEFAULT 0;
        ALTER TABLE hre_isnull ADD mean_a DOUBLE PRECISION DEFAULT 0;
        """ % (grid_id_field, table_name_maille, grid_id_field)

        # Union des deux résultats précédents pour récupérer l'entiereté des polygones de maillage de départ (et reformatage des champs)
        query += """
        DROP TABLE IF EXISTS hre;
        CREATE TABLE hre AS
            SELECT id AS %s, mean_h, mean_a, geom
            FROM hre_notnull
            UNION
            SELECT id AS %s, mean_h, mean_a, geom
            FROM hre_isnull;
        ALTER TABLE hre ALTER COLUMN mean_h TYPE NUMERIC(8,2);
        ALTER TABLE hre ALTER COLUMN mean_a TYPE NUMERIC(8,2);
        UPDATE hre SET mean_h = 0 WHERE mean_h IS NULL;
        UPDATE hre SET mean_a = 0 WHERE mean_a IS NULL;
        """ % (grid_id_field, grid_id_field)

        # Exécution de la requête SQL
        connection = openConnection(database_postgis, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=port_number, schema_name=schema_postgis)
        if debug >= 1:
            print(query)
        executeQuery(connection, query)
        closeConnection(connection)

        # Export en shape de la table contenant l'indicateur calculé
        exportVectorByOgr2ogr(database_postgis, grid_output, 'hre', user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema_name=schema_postgis, format_type=format_vector)

        ##########################################
        ### Nettoyage des fichiers temporaires ###
        ##########################################

        if not save_results_intermediate:
            dropDatabase(database_postgis, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=port_number, schema_name=schema_postgis) # Conflits avec autres indicateurs (Aspect Ratio / Terrain Roughness Class)

    else:
        print(bold + magenta + "Le calcul de Height of Roughness Elements a déjà eu lieu." + endC)

    print(bold + yellow + "Fin du calcul de l'indicateur Height of Roughness Elements." + endC + "\n")
    timeLine(path_time_log, "Fin du calcul de l'indicateur Height of Roughness Elements : ")

    return

####################################################################################################
# FONCTION computeRoughnessByOcsMnh()                                                              #
####################################################################################################
def computeRoughnessByOcsMnh( grid_input, grid_output, mnh_input, classif_input, class_build_list, epsg, path_time_log, no_data_value, format_raster='GTiff', format_vector='ESRI Shapefile', extension_raster=".tif", extension_vector=".shp", save_results_intermediate=False, overwrite=True):
    """
    # ROLE :
    #     Calcul de l'indicateur LCZ hauteur des élements de rugosité
    #
    # ENTREES DE LA FONCTION :
    #
    #     grid_input : fichier de maillage en entrée
    #     grid_output : fichier de maillage en sortie
    #     mnh_input : Modèle Numérique de Hauteur en entrée
    #     classif_input : classification OCS en entrée
    #     class_build_list : liste des classes choisis pour definir les zones baties
    #     epsg : EPSG des fichiers de sortie utilisation de la valeur des fichiers d'entrée si la valeur = 0
    #     path_time_log : fichier log de sortie
    #     no_data_value : Valeur des pixels sans données pour les rasters
    #     format_raster : Format de l'image de sortie, par défaut : GTiff
    #     format_vector : format du fichier vecteur. Optionnel, par default : 'ESRI Shapefile'
    #     extension_raster : extension des fichiers raster de sortie, par defaut = '.tif'
    #     extension_vector : extension du fichier vecteur de sortie, par defaut = '.shp'
    #     save_results_intermediate : fichiers de sorties intermédiaires nettoyés, par défaut = False
    #     overwrite : écrase si un fichier existant a le même nom qu'un fichier de sortie, par défaut = True
    #
    # SORTIES DE LA FONCTION :
    #     N.A
    """

    # Constante
    FIELD_H_TYPE = ogr.OFTReal
    FIELD_ID_TYPE = ogr.OFTInteger
    FIELD_NAME_HSUM = "sum_h"
    FIELD_NAME_HRE = "mean_h"
    FIELD_NAME_AREA = "nb_area"
    FIELD_NAME_ID = "id"

    SUFFIX_HEIGHT = '_hauteur'
    SUFFIX_BUILT = '_bati'
    SUFFIX_TEMP = '_temp'
    SUFFIX_MASK = '_mask'

    # Mise à jour du Log
    timeLine(path_time_log, "Début du calcul de l'indicateur Height of Roughness Elements par OCS et MNT starting : ")
    print(cyan + "computeRoughnessByOcsMnh() : " + endC + "Début du calcul de l'indicateur Height of Roughness Elements par OCS et MNT." + endC + "\n")

    if debug >= 3:
        print(bold + green + "computeRoughnessByOcsMnh() : Variables dans la fonction" + endC)
        print(cyan + "computeRoughnessByOcsMnh() : " + endC + "grid_input : " + str(grid_input) + endC)
        print(cyan + "computeRoughnessByOcsMnh() : " + endC + "grid_output : " + str(grid_output) + endC)
        print(cyan + "computeRoughnessByOcsMnh() : " + endC + "mnh_input : " + str(mnh_input) + endC)
        print(cyan + "computeRoughnessByOcsMnh() : " + endC + "classif_input : " + str(classif_input) + endC)
        print(cyan + "computeRoughnessByOcsMnh() : " + endC + "class_build_list : " + str(class_build_list) + endC)
        print(cyan + "computeRoughnessByOcsMnh() : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "computeRoughnessByOcsMnh() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "computeRoughnessByOcsMnh() : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "computeRoughnessByOcsMnh() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "computeRoughnessByOcsMnh() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "computeRoughnessByOcsMnh() : " + endC + "overwrite : " + str(overwrite) + endC)

    # Test si le vecteur de sortie existe déjà et si il doit être écrasés
    check = os.path.isfile(grid_output)

    if check and not overwrite: # Si le fichier de sortie existent deja et que overwrite n'est pas activé
        print(cyan + "computeRoughnessByOcsMnh() : " + bold + yellow + "Le calcul de Roughness par OCS et MNT a déjà eu lieu." + endC + "\n")
        print(cyan + "computeRoughnessByOcsMnh() : " + bold + yellow + "Grid vector output : " + grid_output + " already exists and will not be created again." + endC)
    else :
        if check:
            try:
                removeVectorFile(grid_output)
            except Exception:
                pass # si le fichier n'existe pas, il ne peut pas être supprimé : cette étape est ignorée

        ############################################
        ### Préparation générale des traitements ###
        ############################################

        # Récuperation de la projection de l'image
        epsg_proj, _ = getProjectionImage(classif_input)
        if epsg_proj == 0:
            epsg_proj = epsg

        # Préparation des fichiers temporaires
        temp_path = os.path.dirname(grid_output) + os.sep + "RoughnessByOcsAndMnh"

        # Nettoyage du repertoire temporaire si il existe
        if os.path.exists(temp_path):
            shutil.rmtree(temp_path)
        os.makedirs(temp_path)

        basename = os.path.splitext(os.path.basename(grid_output))[0]
        built_height = temp_path + os.sep + basename + SUFFIX_HEIGHT + SUFFIX_BUILT + extension_raster
        built_height_temp = temp_path + os.sep + basename + SUFFIX_HEIGHT + SUFFIX_BUILT + SUFFIX_TEMP + extension_raster
        classif_built_mask = temp_path + os.sep + basename + SUFFIX_BUILT + SUFFIX_MASK + extension_raster
        grid_output_temp = temp_path + os.sep + basename + SUFFIX_TEMP + extension_vector

        ##############################
        ### Calcul de l'indicateur ###
        ##############################

        # liste des classes de bati a prendre en compte dans l'expression du BandMath
        expression_bati = ""
        for id_class in class_build_list :
            expression_bati += "im1b1==%s or " %(str(id_class))
        expression_bati = expression_bati[:-4]
        expression = "(%s) and (im2b1!=%s) and (im2b1>0)" %(expression_bati, str(no_data_value))

        # Creation d'un masque vecteur des batis pour la surface des zones baties
        command = "otbcli_BandMath -il %s %s -out %s uint8 -exp '%s ? 1 : 0'" %(classif_input, mnh_input, classif_built_mask, expression)
        if debug >= 3:
            print(command)
        exit_code = os.system(command)
        if exit_code != 0:
            print(command)
            print(cyan + "computeRoughnessByOcsMnh() : " + bold + red + "!!! Une erreur c'est produite au cours de la commande otbcli_BandMath : " + command + ". Voir message d'erreur." + endC, file=sys.stderr)
            raise

        # Récupération de la hauteur du bati
        command = "otbcli_BandMath -il %s %s -out %s float -exp '%s ? im2b1 : 0'" %(classif_input, mnh_input, built_height_temp, expression)
        if debug >= 3:
            print(command)
        exit_code = os.system(command)
        if exit_code != 0:
            print(command)
            print(cyan + "computeRoughnessByOcsMnh() : " + bold + red + "!!! Une erreur c'est produite au cours de la commande otbcli_BandMath : " + command + ". Voir message d'erreur." + endC, file=sys.stderr)
            raise

        command = "gdal_translate -a_srs EPSG:%s -a_nodata %s -of %s %s %s" %(str(epsg_proj), str(no_data_value), format_raster, built_height_temp, built_height)
        if debug >= 3:
            print(command)
        exit_code = os.system(command)
        if exit_code != 0:
            print(command)
            print(cyan + "computeRoughnessByOcsMnh() : " + bold + red + "!!! Une erreur c'est produite au cours de la comande : gdal_translate : " + command + ". Voir message d'erreur." + endC, file=sys.stderr)
            raise

        # Récupération du nombre de pixel bati de chaque maille pour definir la surface
        statisticsVectorRaster(classif_built_mask, grid_input, grid_output_temp, 1, False, False, True, ["min", "max", "median", "mean", "std", "unique", "range"], [], {}, True, no_data_value, format_vector, path_time_log, save_results_intermediate, overwrite)

        # Renomer le champ 'sum' en FIELD_NAME_AREA
        renameFieldsVector(grid_output_temp, ['sum'], [FIELD_NAME_AREA], format_vector)

        # Récupération de la hauteur moyenne du bati de chaque maille
        statisticsVectorRaster(built_height, grid_output_temp, grid_output, 1, False, False, True, ["min", "max", "median", 'mean', "std", "unique", "range"], [], {}, True, no_data_value, format_vector, path_time_log,  save_results_intermediate, overwrite)

        # Renomer le champ 'mean' en FIELD_NAME_HRE
        renameFieldsVector(grid_output, ['sum'], [FIELD_NAME_HSUM], format_vector)

        # Calcul de la colonne FIELD_NAME_HRE division de FIELD_NAME_HSUM par FIELD_NAME_AREA
        field_values_list = getAttributeValues(grid_output, None, None, {FIELD_NAME_ID:FIELD_ID_TYPE, FIELD_NAME_HSUM:FIELD_H_TYPE, FIELD_NAME_AREA:FIELD_H_TYPE}, format_vector)

        field_new_values_list = []
        for index in range(0, len(field_values_list[FIELD_NAME_ID])) :
            value_h = 0.0
            if field_values_list[FIELD_NAME_AREA][index] > 0 :
                value_h = field_values_list[FIELD_NAME_HSUM][index] / field_values_list[FIELD_NAME_AREA][index]
            field_new_values_list.append({FIELD_NAME_HRE:value_h})

        # Ajour de la nouvelle colonne calculé FIELD_NAME_HRE
        addNewFieldVector(grid_output, FIELD_NAME_HRE, FIELD_H_TYPE, 0, None, None, format_vector)
        setAttributeValuesList(grid_output, field_new_values_list, format_vector)

        ##########################################
        ### Nettoyage des fichiers temporaires ###
        ##########################################
        if not save_results_intermediate:
            if os.path.exists(temp_path):
                shutil.rmtree(temp_path)

    print(cyan + "computeRoughnessByOcsMnh() : " + endC + "Fin du calcul de l'indicateur Height of Roughness Elements par OCS et MNT." + endC + "\n")
    timeLine(path_time_log, "Fin du calcul de l'indicateur Height of Roughness Elements par OCS et MNT  ending : ")

    return

#############################################################################################################################
################################################## Mise en place du parser ##################################################
#############################################################################################################################

def main(gui=False):
    parser = argparse.ArgumentParser(prog = "Calcul de la hauteur des elements de rugosite (Height of Roughness Elements) a partir d'une bd de bati ou avec les données raster OCS et MNH",
    description = """Calcul de l'indicateur LCZ hauteur des elements de rugosite (Height of Roughness Elements) :
    Exemple1 : python HeightOfRoughnessElements.py
                        -in  ../UrbanAtlas.shp
                        -out ../HeightOfRoughnessElements.shp
                        -bi  ../Nancy/bati.shp
    Example2 : python HeightOfRoughnessElements.py
                        -in  ../UrbanAtlas.shp
                        -out ../HeightOfRoughnessElements.shp
                        -cla ../Classif_OCS.tif
                        -mnh  ../Nancy/MNH.tif
                        -cldb 11100
                        -epsg 2154
                        -log ../fichierTestLog.txt""")

    parser.add_argument('-in', '--grid_input', default="", help="Fichier de maillage en entree (vecteur).", type=str, required=True)
    parser.add_argument('-out', '--grid_output', default="", help="Fichier de maillage en sortie, avec la valeur de Height of Roughness Elements par maille (vecteur).", type=str, required=True)
    parser.add_argument('-bi', '--built_input', default="", help="Fichier de bâti 3D en entree (vecteur).", type=str, required=False)
    parser.add_argument('-id', '--grid_id_field', default="id", help="Nom du champ ID du fichier de maillage en entrée.", type=str, required=False)
    parser.add_argument('-bid', '--built_id_field', default="ID", help="Nom du champ ID du fichier de bâti 3D.", type=str, required=False)
    parser.add_argument('-bhf', '--built_height_field', default="HAUTEUR", help="Nom du champ contenant l'information de hauteur.", type=str, required=False)
    parser.add_argument('-ocs', '--classif_input', default="", help="Input file Modele classification OCS (raster).", type=str, required=False)
    parser.add_argument('-mnh', '--mnh_input', default="", help="Input file Modele Numerique de Hauteur(raster).", type=str, required=False)
    parser.add_argument('-cbl', '--class_build_list', nargs="+", default=[11100], help="Liste des indices de classe de type bati.", type=int, required=False)
    parser.add_argument('-epsg','--epsg', default=2154, help="EPSG code projection.", type=int, required=False)
    parser.add_argument("-ndv",'--no_data_value',default=0, help="Option : Pixel value for raster file to no data, default : 0 ", type=int, required=False)
    parser.add_argument('-pe','--project_encoding', default="latin1", help="Project encoding.", type=str, required=False)
    parser.add_argument('-serv','--server_postgis', default="localhost", help="Postgis serveur name or ip.", type=str, required=False)
    parser.add_argument('-port','--port_number', default=5432, help="Postgis port number.", type=int, required=False)
    parser.add_argument('-user','--user_postgis', default="postgres", help="Postgis user name.", type=str, required=False)
    parser.add_argument('-pwd','--password_postgis', default="postgres", help="Postgis password user.", type=str, required=False)
    parser.add_argument('-db','--database_postgis', default="lcz_hre", help="Postgis database name.", type=str, required=False)
    parser.add_argument('-sch','--schema_postgis', default="public", help="Postgis schema name.", type=str, required=False)
    parser.add_argument('-raf','--format_raster', default="GTiff", help="Option : Format output image, by default : GTiff (GTiff, HFA...)", type=str, required=False)
    parser.add_argument('-vef','--format_vector', default="ESRI Shapefile", help="Format of the output file.", type=str, required=False)
    parser.add_argument('-rae','--extension_raster', default=".tif", help="Option : Extension file for image raster. By default : '.tif'", type=str, required=False)
    parser.add_argument('-vee','--extension_vector',default=".shp", help="Option : Extension file for vector. By default : '.shp'", type=str, required=False)
    parser.add_argument('-log', '--path_time_log', default="", type=str, required=False, help="Name of log")
    parser.add_argument('-sav', '--save_results_intermediate', action='store_true', default=False, required=False, help="Save or delete intermediate result after the process. By default, False")
    parser.add_argument('-now', '--overwrite', action='store_false', default=True, required=False, help="Overwrite files with same names. By default, True")
    parser.add_argument('-debug', '--debug', default=3, type=int, required=False, help="Option : Value of level debug trace, default : 3")
    args = displayIHM(gui, parser)

    # Récupération du vecteur d'entrée de grille
    if args.grid_input != None:
        grid_input = args.grid_input
        if not os.path.isfile(grid_input):
            raise NameError (cyan + "HeightOfRoughnessElements : " + bold + red  + "File %s not existe!" %(grid_input) + endC)

    # Récupération du vecteur de sortie de grille
    if args.grid_output != None:
        grid_output = args.grid_output

     # Récupération du fichier vecteur bati d'entrée
    if args.built_input != None:
        built_input = args.built_input

    # Récupération du nom du champ id du vecteur d'entrée de grille
    if args.grid_id_field != None :
        grid_id_field = args.grid_id_field

    # Récupération du nom du champ id du vecteur d'entrée de bâti 3D
    if args.built_id_field != None :
        built_id_field = args.built_id_field

    # Récupération du nom du champ hauteur du vecteur d'entrée de bâti 3D
    if args.built_height_field != None :
        built_height_field = args.built_height_field

    # Récupération de l'image mnh
    if args.mnh_input != None:
        mnh_input = args.mnh_input

   # Récupération de l'image classif
    if args.classif_input != None:
        classif_input = args.classif_input

    # Récupération de la liste des classes bati
    if args.class_build_list != None:
        class_build_list = args.class_build_list

    # Récupération du code EPSG de la projection du shapefile trait de côte
    if args.epsg != None :
        epsg = args.epsg

    # Paramettre des no data
    if args.no_data_value != None:
        no_data_value = args.no_data_value

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

    # Paramètre format des images de sortie
    if args.format_raster != None:
        format_raster = args.format_raster

    # Récupération du format du fichier de sortie
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

    # Récupération de l'option de sauvegarde des fichiers intermédiaires
    if args.save_results_intermediate != None:
        save_results_intermediate = args.save_results_intermediate

    # Récupération de l'option écrasement
    if args.overwrite!= None:
        overwrite = args.overwrite

    # Récupération de l'option niveau de debug
    if args.debug!= None:
        global debug
        debug = args.debug

    if debug >= 3:
        print(bold + green + "Calcul de la hauteur des élements de rugosité :" + endC)
        print(cyan + "HeightOfRoughnessElements : " + endC + "grid_input : " + str(grid_input) + endC)
        print(cyan + "HeightOfRoughnessElements : " + endC + "grid_output : " + str(grid_output) + endC)
        print(cyan + "HeightOfRoughnessElements : " + endC + "built_input : " + str(built_input) + endC)
        print(cyan + "HeightOfRoughnessElements : " + endC + "grid_id_field : " + str(grid_id_field) + endC)
        print(cyan + "HeightOfRoughnessElements : " + endC + "built_id_field : " + str(built_id_field) + endC)
        print(cyan + "HeightOfRoughnessElements : " + endC + "built_height_field : " + str(built_height_field) + endC)
        print(cyan + "HeightOfRoughnessElements : " + endC + "mnh_input : " + str(mnh_input) + endC)
        print(cyan + "HeightOfRoughnessElements : " + endC + "classif_input : " + str(classif_input) + endC)
        print(cyan + "HeightOfRoughnessElements : " + endC + "class_build_list : " + str(class_build_list) + endC)
        print(cyan + "HeightOfRoughnessElements : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "HeightOfRoughnessElements : " + endC + "project_encoding : " + str(project_encoding) + endC)
        print(cyan + "HeightOfRoughnessElements : " + endC + "server_postgis : " + str(server_postgis) + endC)
        print(cyan + "HeightOfRoughnessElements : " + endC + "port_number : " + str(port_number) + endC)
        print(cyan + "HeightOfRoughnessElements : " + endC + "user_postgis : " + str(user_postgis) + endC)
        print(cyan + "HeightOfRoughnessElements : " + endC + "password_postgis : " + str(password_postgis) + endC)
        print(cyan + "HeightOfRoughnessElements : " + endC + "database_postgis : " + str(database_postgis) + endC)
        print(cyan + "HeightOfRoughnessElements : " + endC + "schema_postgis : " + str(schema_postgis) + endC)
        print(cyan + "HeightOfRoughnessElements : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "HeightOfRoughnessElements : " + endC + "format_raster : " + str(format_raster) + endC)
        print(cyan + "HeightOfRoughnessElements : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "HeightOfRoughnessElements : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "HeightOfRoughnessElements : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "HeightOfRoughnessElements : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "HeightOfRoughnessElements : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "HeightOfRoughnessElements : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "HeightOfRoughnessElements : " + endC + "debug : " + str(debug) + endC)

    if not os.path.exists(os.path.dirname(grid_output)):
        os.makedirs(os.path.dirname(grid_output))

    if os.path.isfile(built_input):
        # Calcul de "Height Of Roughness Elements" par base de données bâti 3D
        heightOfRoughnessElements(grid_input, grid_output, built_input, grid_id_field, built_id_field, built_height_field, epsg, project_encoding, server_postgis, port_number, user_postgis, password_postgis, database_postgis, schema_postgis, path_time_log, format_vector, save_results_intermediate, overwrite)

    else :
        if not os.path.isfile(mnh_input):
            raise NameError (cyan + "HeightOfRoughnessElements : " + bold + red  + "File %s not existe!" %(mnh_input) + endC)
        if not os.path.isfile(classif_input):
            raise NameError (cyan + "HeightOfRoughnessElements : " + bold + red  + "File %s not existe!" %(classif_input) + endC)
        # Calcul de "Height Of Roughness Elements" par données raster OCS et MNH (méthode international)
        computeRoughnessByOcsMnh(grid_input, grid_output, mnh_input, classif_input, class_build_list, epsg, path_time_log, no_data_value, format_raster, format_vector, extension_raster, extension_vector, save_results_intermediate, overwrite)

if __name__ == '__main__':
    main(gui=False)

