#!/usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerSO/DALETT/SCGSI  All rights reserved.                                                                            #
#############################################################################################################################################

from __future__ import print_function
import os, sys, argparse
from Lib_log import timeLine
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_postgis import executeQuery, openConnection, closeConnection, createDatabase, dropDatabase, importVectorByOgr2ogr, exportVectorByOgr2ogr
from Lib_file import removeVectorFile

# debug = 1 : affichage requête SQL
debug = 3

####################################################################################################
# FONCTION heightOfRoughnessElements()                                                             #
####################################################################################################
# ROLE :
#     Calcul de l'indicateur LCZ hauteur des élements de rugosité
#
# ENTREES DE LA FONCTION :
#     grid_input : fichier de maillage en entrée
#     grid_output : fichier de maillage en sortie
#     built_input : fichier de la BD TOPO bâti en entrée
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

def heightOfRoughnessElements(grid_input, grid_output, built_input, epsg, project_encoding, server_postgis, port_number, user_postgis, password_postgis, database_postgis, schema_postgis, path_time_log, format_vector='ESRI Shapefile', save_results_intermediate=False, overwrite=True):

    print(bold + yellow + "Début du calcul de l'indicateur Height of Roughness Elements." + endC + "\n")
    timeLine(path_time_log, "Début du calcul de l'indicateur Height of Roughness Elements : ")

    if debug >= 3:
        print(bold + green + "heightOfRoughnessElements() : Variables dans la fonction" + endC)
        print(cyan + "heightOfRoughnessElements() : " + endC + "grid_input : " + str(grid_input) + endC)
        print(cyan + "heightOfRoughnessElements() : " + endC + "grid_output : " + str(grid_output) + endC)
        print(cyan + "heightOfRoughnessElements() : " + endC + "built_input : " + str(built_input) + endC)
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
        # ~ dropDatabase(database_postgis) # Conflits avec autres indicateurs (Aspect Ratio / Terrain Roughness Class)
        createDatabase(database_postgis)

        # Import des fichiers shapes maille et bati dans la base de données PostGIS
        table_name_maille = importVectorByOgr2ogr(database_postgis, grid_input, 'hre_maille', user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema_name=schema_postgis, epsg=str(epsg), codage=project_encoding)
        print("\n")
        table_name_bati = importVectorByOgr2ogr(database_postgis, built_input, 'hre_bati', user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema_name=schema_postgis, epsg=str(epsg), codage=project_encoding)
        print("\n")

        print("\n")

        ###############################################
        ### Calcul de l'indicateur par requêtes SQL ###
        ###############################################

        print(bold + cyan + "Calcul de Height of Roughness Elements :" + endC)
        timeLine(path_time_log, "    Calcul de Height of Roughness Elements : ")

        # Création des index spatiaux (accélère les requêtes spatiales)
        query = """
        --CREATE INDEX IF NOT EXISTS maille_geom_gist ON %s USING GIST (geom);
        --CREATE INDEX IF NOT EXISTS bati_geom_gist ON %s USING GIST (geom);
        """ % (table_name_maille, table_name_bati)

        # Intersect entre les tables maille et bâti (pour chaque maille, on récupère le bâti qui intersect)
        query += """
        DROP TABLE IF EXISTS hre_decoup;
        CREATE TABLE hre_decoup AS
            SELECT b.ID as ID, b.HAUTEUR as hauteur, ST_Intersection(b.geom, m.geom) as geom
            FROM %s as b, %s as m
            WHERE ST_Intersects(b.geom, m.geom);
        CREATE INDEX IF NOT EXISTS decoup_geom_gist ON hre_decoup USING GIST (geom);
        """ % (table_name_bati, table_name_maille)

        # Table intermédiaire de calculs d'indicateurs secondaires
        query += """
        DROP TABLE IF EXISTS hre_temp;
        CREATE TABLE hre_temp AS
            SELECT d.ID, st_area(d.geom) as surface, (st_area(d.geom) * d.hauteur) as volume, d.geom as geom
            FROM hre_decoup as d;
        CREATE INDEX IF NOT EXISTS temp_geom_gist ON hre_temp USING GIST (geom);
        """

        # Table intermédiaire de calcul de mean_h seulement pour les mailles intersectant du bâti
        query += """
        DROP TABLE IF EXISTS hre_maille_bis;
        CREATE TABLE hre_maille_bis AS
            SELECT m.ID as ID, ((sum(t.volume) / count(t.geom)) / (sum(t.surface) / count(t.geom))) as mean_h, m.geom as geom
            FROM %s as m, hre_temp as t
            WHERE ST_Intersects(m.geom, t.geom)
            GROUP BY m.ID, m.geom;
        CREATE INDEX IF NOT EXISTS maille_bis_geom_gist ON hre_maille_bis USING GIST (geom);
        """ % table_name_maille

        # Table intermédiaire seulement pour les mailles n'intersectant pas de bâti (par défaut, mean_h = 0)
        query += """
        DROP TABLE IF EXISTS hre_maille_ter;
        CREATE TABLE hre_maille_ter AS
            SELECT DISTINCT ID as ID, geom as geom
            FROM %s
            WHERE ID NOT IN
                (SELECT DISTINCT ID
                FROM hre_maille_bis);
        ALTER TABLE hre_maille_ter ADD mean_h DOUBLE PRECISION;
        UPDATE hre_maille_ter SET mean_h = 0;
        CREATE INDEX IF NOT EXISTS maille_ter_geom_gist ON hre_maille_ter USING GIST (geom);
        """ % table_name_maille

        # Union des 2 tables précédentes pour récupérer l'ensemble des polygones maille de départ
        query += """
        DROP TABLE IF EXISTS hre_height;
        CREATE TABLE hre_height AS
            SELECT ID, mean_h, geom
            FROM hre_maille_bis
            UNION
            SELECT ID, mean_h, geom
            FROM hre_maille_ter;
        ALTER TABLE hre_height ALTER COLUMN ID TYPE INTEGER;
        """

        # Exécution de la requête SQL
        if debug >= 1:
            print(query)
        connection = openConnection(database_postgis, user_postgis, password_postgis, server_postgis, str(port_number), schema_name=schema_postgis)
        executeQuery(connection, query)
        closeConnection(connection)

        # Export en shape de la table contenant l'indicateur calculé
        exportVectorByOgr2ogr(database_postgis, grid_output, 'hre_height', user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema_name=schema_postgis, format_type=format_vector)
        print("\n")

        ##########################################
        ### Nettoyage des fichiers temporaires ###
        ##########################################

        if not save_results_intermediate:
            # ~ dropDatabase(database_postgis) # Conflits avec autres indicateurs (Aspect Ratio / Terrain Roughness Class)
            pass

    else:
        print(bold + magenta + "Le calcul de Height of Roughness Elements a déjà eu lieu." + endC)
        print("\n")

    print(bold + yellow + "Fin du calcul de l'indicateur Height of Roughness Elements." + endC + "\n")
    timeLine(path_time_log, "Fin du calcul de l'indicateur Height of Roughness Elements : ")

    return

#############################################################################################################################
################################################## Mise en place du parser ##################################################
#############################################################################################################################

def main(gui=False):
    parser = argparse.ArgumentParser(prog = "Calcul de la hauteur des elements de rugosite (Height of Roughness Elements)",
    description = """Calcul de l'indicateur LCZ hauteur des elements de rugosite (Height of Roughness Elements) :
    Exemple : python /home/scgsi/Documents/ChaineTraitement/ScriptsLCZ/PerviousSurfaceFraction.py
                        -in  /mnt/Donnees_Etudes/10_Agents/Benjamin/LCZ/Nancy/UrbanAtlas.shp
                        -out /mnt/Donnees_Etudes/10_Agents/Benjamin/LCZ/Nancy/HeightOfRoughnessElements.shp
                        -bi  /mnt/Donnees_Etudes/10_Agents/Benjamin/LCZ/Nancy/bati.shp""")

    parser.add_argument('-in', '--grid_input', default="", type=str, required=True, help="Fichier de maillage en entree (vecteur).")
    parser.add_argument('-out', '--grid_output', default="", type=str, required=True, help="Fichier de maillage en sortie, avec la valeur de Height of Roughness Elements par maille (vecteur).")
    parser.add_argument('-bi', '--built_input', default="", type=str, required=True, help="Fichier de la BD TOPO bati en entree (vecteur).")
    parser.add_argument('-epsg','--epsg', default=2154,help="EPSG code projection.", type=int, required=False)
    parser.add_argument('-pe','--project_encoding', default="latin1",help="Project encoding.", type=str, required=False)
    parser.add_argument('-serv','--server_postgis', default="localhost",help="Postgis serveur name or ip.", type=str, required=False)
    parser.add_argument('-port','--port_number', default=5432,help="Postgis port number.", type=int, required=False)
    parser.add_argument('-user','--user_postgis', default="postgres",help="Postgis user name.", type=str, required=False)
    parser.add_argument('-pwd','--password_postgis', default="postgres",help="Postgis password user.", type=str, required=False)
    parser.add_argument('-db','--database_postgis', default="lcz_hre",help="Postgis database name.", type=str, required=False)
    parser.add_argument('-sch','--schema_postgis', default="public",help="Postgis schema name.", type=str, required=False)
    parser.add_argument('-vef','--format_vector', default="ESRI Shapefile",help="Format of the output file.", type=str, required=False)
    parser.add_argument('-log', '--path_time_log', default="/home/scgsi/Bureau/logLCZ.txt", type=str, required=False, help="Name of log")
    parser.add_argument('-sav', '--save_results_intermediate', action='store_true', default=False, required=False, help="Save or delete intermediate result after the process. By default, False")
    parser.add_argument('-now', '--overwrite', action='store_false', default=True, required=False, help="Overwrite files with same names. By default, True")
    parser.add_argument('-debug', '--debug', default=3, type=int, required=False, help="Option : Value of level debug trace, default : 3")
    args = displayIHM(gui, parser)

    # Récupération des fichiers d'entrées et de sorties
    if args.grid_input != None:
        grid_input = args.grid_input
    if args.grid_output != None:
        grid_output = args.grid_output
    if args.built_input != None:
        built_input = args.built_input

    # Récupération du code EPSG de la projection du shapefile trait de côte
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

    # Récupération du format du fichier de sortie
    if args.format_vector != None :
        format_vector = args.format_vector

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
        print(cyan + "HeightOfRoughnessElements : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "HeightOfRoughnessElements : " + endC + "project_encoding : " + str(project_encoding) + endC)
        print(cyan + "HeightOfRoughnessElements : " + endC + "server_postgis : " + str(server_postgis) + endC)
        print(cyan + "HeightOfRoughnessElements : " + endC + "port_number : " + str(port_number) + endC)
        print(cyan + "HeightOfRoughnessElements : " + endC + "user_postgis : " + str(user_postgis) + endC)
        print(cyan + "HeightOfRoughnessElements : " + endC + "password_postgis : " + str(password_postgis) + endC)
        print(cyan + "HeightOfRoughnessElements : " + endC + "database_postgis : " + str(database_postgis) + endC)
        print(cyan + "HeightOfRoughnessElements : " + endC + "schema_postgis : " + str(schema_postgis) + endC)
        print(cyan + "HeightOfRoughnessElements : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "HeightOfRoughnessElements : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "HeightOfRoughnessElements : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "HeightOfRoughnessElements : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "HeightOfRoughnessElements : " + endC + "debug : " + str(debug) + endC)

    if not os.path.exists(os.path.dirname(grid_output)):
        os.makedirs(os.path.dirname(grid_output))

    heightOfRoughnessElements(grid_input, grid_output, built_input, epsg, project_encoding, server_postgis, port_number, user_postgis, password_postgis, database_postgis, schema_postgis, path_time_log, format_vector, save_results_intermediate, overwrite)

if __name__ == '__main__':
    main(gui=False)

