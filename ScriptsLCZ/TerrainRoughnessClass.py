#!/usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerSO/DALETT/SCGSI  All rights reserved.                                                                            #
#############################################################################################################################################

from __future__ import print_function
import os, sys, argparse
from Lib_log import timeLine
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_vector import getEmpriseFile
from Lib_postgis import executeQuery, openConnection, closeConnection, createDatabase, dropDatabase, importVectorByOgr2ogr, exportVectorByOgr2ogr
from Lib_file import removeVectorFile

# debug = 1 : affichage emprise d'étude + requêtes SQL principales
# debug = 2 : affichage 1 + listes des x et y calculés pour la création des lignes parallèles
debug = 3

####################################################################################################
# FONCTION terrainRoughnessClass()                                                                 #
####################################################################################################
# ROLE :
#     Calcul de l'indicateur LCZ classe de rugosité
#
# ENTREES DE LA FONCTION :
#     grid_input : fichier de maillage en entrée
#     grid_output : fichier de maillage en sortie
#     built_input : fichier de la BD TOPO bâti en entrée
#     distance_lines : distance séparant 2 lignes N-S et 2 lignes W-E (en mètres)
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

def terrainRoughnessClass(grid_input, grid_output, built_input, distance_lines, epsg, project_encoding, server_postgis, port_number, user_postgis, password_postgis, database_postgis, schema_postgis, path_time_log, format_vector='ESRI Shapefile', save_results_intermediate=False, overwrite=True):

    print(bold + yellow + "Début du calcul de l'indicateur Terrain Roughness Class." + endC + "\n")
    timeLine(path_time_log, "Début du calcul de l'indicateur Terrain Roughness Class : ")

    if debug >= 3:
        print(bold + green + "terrainRoughnessClass() : Variables dans la fonction" + endC)
        print(cyan + "terrainRoughnessClass() : " + endC + "grid_input : " + str(grid_input) + endC)
        print(cyan + "terrainRoughnessClass() : " + endC + "grid_output : " + str(grid_output) + endC)
        print(cyan + "terrainRoughnessClass() : " + endC + "built_input : " + str(built_input) + endC)
        print(cyan + "terrainRoughnessClass() : " + endC + "distance_lines : " + str(distance_lines) + endC)
        print(cyan + "terrainRoughnessClass() : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "terrainRoughnessClass() : " + endC + "project_encoding : " + str(project_encoding) + endC)
        print(cyan + "terrainRoughnessClass() : " + endC + "server_postgis : " + str(server_postgis) + endC)
        print(cyan + "terrainRoughnessClass() : " + endC + "port_number : " + str(port_number) + endC)
        print(cyan + "terrainRoughnessClass() : " + endC + "user_postgis : " + str(user_postgis) + endC)
        print(cyan + "terrainRoughnessClass() : " + endC + "password_postgis : " + str(password_postgis) + endC)
        print(cyan + "terrainRoughnessClass() : " + endC + "database_postgis : " + str(database_postgis) + endC)
        print(cyan + "terrainRoughnessClass() : " + endC + "schema_postgis : " + str(schema_postgis) + endC)
        print(cyan + "terrainRoughnessClass() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "terrainRoughnessClass() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "terrainRoughnessClass() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "terrainRoughnessClass() : " + endC + "overwrite : " + str(overwrite) + endC)
        print("\n")

    if not os.path.exists(grid_output) or overwrite:

        ############################################
        ### Préparation générale des traitements ###
        ############################################

        print(bold + cyan + "Préparation au calcul de Terrain Roughness Class :" + endC)
        timeLine(path_time_log, "    Préparation au calcul de Terrain Roughness Class : ")

        if os.path.exists(grid_output):
            removeVectorFile(grid_output)

        # Création de la base de données PostGIS
        # ~ dropDatabase(database_postgis, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=port_number, schema_name=schema_postgis) # Conflits avec autres indicateurs (Aspect Ratio / Height of Roughness Elements)
        createDatabase(database_postgis, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=port_number, schema_name=schema_postgis)

        # Import des fichiers shapes maille et bati dans la base de données PostGIS
        table_name_maille = importVectorByOgr2ogr(database_postgis, grid_input, 'trc_maille', user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema_name=schema_postgis, epsg=str(epsg), codage=project_encoding)
        table_name_bati = importVectorByOgr2ogr(database_postgis, built_input, 'trc_bati', user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema_name=schema_postgis, epsg=str(epsg), codage=project_encoding)

        # Récupération de l'emprise de la zone d'étude, définie par le fichier maillage d'entrée
        xmin,xmax,ymin,ymax = getEmpriseFile(grid_input, format_vector)
        if debug >= 1:
            print(bold + "Emprise du fichier '%s' :" % (grid_input) + endC)
            print("    xmin = " + str(xmin))
            print("    xmax = " + str(xmax))
            print("    ymin = " + str(ymin))
            print("    ymax = " + str(ymax))

        # Création de la liste des valeurs de x à entrer dans la requêtes SQL de création de lignes
        x_list = [xmin] # Initialisation de la liste
        x = xmin # Définition de la valeur du 1er x à entrer dans la boucle
        while x < (xmax - distance_lines): # On boucle tant que la valeur de x ne dépasse pas le xmax du fichier maillage en entrée
            x = x + distance_lines
            x_list.append(x) # Ajout de la nouvelle valeur de x dans la liste
        if debug >= 2:
            print(bold + "x_list : "  + endC + str(x_list) + "\n")

        # Création de la liste des valeurs de y à entrer dans la requêtes SQL de création de lignes
        y_list = [ymax] # Initialisation de la liste
        y = ymax # Définition de la valeur du 1er y à entrer dans la boucle
        while y > (ymin + distance_lines): # On boucle tant que la valeur de y ne descend pas en-dessous du ymin du fichier maillage en entrée
            y = y - distance_lines
            y_list.append(y) # Ajout de la nouvelle valeur de y dans la liste
        if debug >= 2:
            print(bold + "y_list : "  + endC + str(y_list) + "\n")

        #################################################
        ### Création des lignes parallèles N-S et W-E ###
        #################################################

        print(bold + cyan + "Création des lignes parallèles N-S et W-E :" + endC)
        timeLine(path_time_log, "    Création des lignes parallèles N-S et W-E : ")

        connection = openConnection(database_postgis, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=port_number, schema_name=schema_postgis)

        # Construction de la requête de création des lignes parallèles N-S
        query_lines_NS = "DROP TABLE IF EXISTS trc_lines_NS;\n"
        query_lines_NS += "CREATE TABLE trc_lines_NS (line text, geom geometry);\n"
        query_lines_NS += "INSERT INTO trc_lines_NS VALUES\n"

        # Boucle sur les valeurs de x dans la liste associée, pour construire la requête de création des lignes parallèles N-S
        count_NS = 0
        for x in x_list:
            count_NS += 1
            query_lines_NS += "    ('line_NS_%s', 'LINESTRING(%s %s, %s %s)'),\n" % (count_NS, x, ymax, x, ymin)

        # Fin de la requête de création des lignes parallèles N-S et exécution de cette requête
        query_lines_NS = query_lines_NS[:-2] + ";\n" # Transformer la virgule de la dernière ligne SQL en point-virgule (pour terminer la requête)
        query_lines_NS += "ALTER TABLE trc_lines_NS ALTER COLUMN geom TYPE geometry(LINESTRING,%s) USING ST_SetSRID(geom,%s);\n" % (epsg,epsg) # Mise à jour du système de coordonnées
        if debug >= 1:
            print(query_lines_NS)
        executeQuery(connection, query_lines_NS)

        # Construction de la requête de création des lignes parallèles W-E
        query_lines_WE = "DROP TABLE IF EXISTS trc_lines_WE;\n"
        query_lines_WE += "CREATE TABLE trc_lines_WE (line text, geom geometry);\n"
        query_lines_WE += "INSERT INTO trc_lines_WE VALUES\n"

        # Boucle sur les valeurs de y dans la liste associée, pour construire la requête de création des lignes parallèles W-E
        count_WE = 0
        for y in y_list:
            count_WE += 1
            query_lines_WE += "    ('line_WE_%s', 'LINESTRING(%s %s, %s %s)'),\n" % (count_WE, xmin, y, xmax, y)

        # Fin de la requête de création des lignes parallèles W-E et exécution de cette requête
        query_lines_WE = query_lines_WE[:-2] + ";\n" # Transformer la virgule de la dernière ligne SQL en point-virgule (pour terminer la requête)
        query_lines_WE += "ALTER TABLE trc_lines_WE ALTER COLUMN geom TYPE geometry(LINESTRING,%s) USING ST_SetSRID(geom,%s);\n" % (epsg,epsg) # Mise à jour du système de coordonnées

        if debug >= 1:
            print(query_lines_WE)
        executeQuery(connection, query_lines_WE)

        #####################################################################################################
        ### Découpage des bâtiments, et des lignes N-S et W-E à cheval sur plusieurs mailles (intersects) ###
        #####################################################################################################

        print(bold + cyan + "Lancement des requêtes d'intersect :" + endC)
        timeLine(path_time_log, "    Lancement des requêtes d'intersect : ")

        query_intersect = """
        --CREATE INDEX IF NOT EXISTS maille_geom_gist ON %s USING GIST (geom);
        --CREATE INDEX IF NOT EXISTS bati_geom_gist ON %s USING GIST (geom);
        CREATE INDEX IF NOT EXISTS lines_NS_geom_gist ON trc_lines_NS USING GIST (geom);
        CREATE INDEX IF NOT EXISTS lines_WE_geom_gist ON trc_lines_WE USING GIST (geom);

        DROP TABLE IF EXISTS trc_decoup;
        CREATE TABLE trc_decoup AS
            SELECT b.ID as ID, b.HAUTEUR as hauteur, ST_Intersection(b.geom, m.geom) as geom
            FROM %s as b, %s as m
            WHERE ST_Intersects(b.geom, m.geom);
        CREATE INDEX IF NOT EXISTS decoup_geom_gist ON trc_decoup USING GIST (geom);

        DROP TABLE IF EXISTS trc_decoupNS;
        CREATE TABLE trc_decoupNS AS
            SELECT m.ID as ID, l.line as line, ST_Intersection(l.geom, m.geom) as geom
            FROM trc_lines_NS as l, %s as m
            WHERE ST_Intersects(l.geom, m.geom);
        CREATE INDEX IF NOT EXISTS decoupNS_geom_gist ON trc_decoupNS USING GIST (geom);

        DROP TABLE IF EXISTS trc_decoupWE;
        CREATE TABLE trc_decoupWE AS
            SELECT m.ID as ID, l.line as line, ST_Intersection(l.geom, m.geom) as geom
            FROM trc_lines_WE as l, %s as m
            WHERE ST_Intersects(l.geom, m.geom);
        CREATE INDEX IF NOT EXISTS decoupWE_geom_gist ON trc_decoupWE USING GIST (geom);
        """ % (table_name_maille, table_name_bati, table_name_bati, table_name_maille, table_name_maille, table_name_maille)

        if debug >= 1:
            print(query_intersect)
        executeQuery(connection, query_intersect)

        #######################################################################################################################################################
        ### Calculs pour l'obtention des sous-indicateurs liés à l'intersect des bâtiments dans chaque maille :  h, plan area ratio, hauteur de déplacement ###
        #######################################################################################################################################################

        print(bold + cyan + "Calcul des indicateurs secondaires liés aux bâtiments intersectant chaque maille :" + endC)
        timeLine(path_time_log, "    Calcul des indicateurs secondaires liés aux bâtiments intersectant chaque maille : ")

        query_bati = """
        DROP TABLE IF EXISTS trc_temp_a;
        CREATE TABLE trc_temp_a AS
            SELECT ID, hauteur, st_area(geom) as surface, geom
            FROM trc_decoup;
        ALTER TABLE trc_temp_a ADD volume DOUBLE PRECISION;
        UPDATE trc_temp_a SET volume = (surface * hauteur);
        ALTER TABLE trc_temp_a ADD VxH DOUBLE PRECISION;
        UPDATE trc_temp_a SET VxH = (volume * hauteur);
        CREATE INDEX IF NOT EXISTS temp_a_geom_gist ON trc_temp_a USING GIST (geom);

        DROP TABLE IF EXISTS trc_temp_b;
        CREATE TABLE trc_temp_b AS
            SELECT m.ID as ID, (sum(a.VxH) / sum(a.volume)) as h, (sum(a.surface) / st_area(m.geom)) as PAR, m.geom as geom
            FROM %s as m, trc_temp_a as a
            WHERE ST_Intersects(m.geom, a.geom)
            GROUP BY m.ID, m.geom;
        ALTER TABLE trc_temp_b ADD zd DOUBLE PRECISION;
        UPDATE trc_temp_b SET zd = (h * (PAR ^ 0.6));
        CREATE INDEX IF NOT EXISTS temp_b_geom_gist ON trc_temp_b USING GIST (geom);

        DROP TABLE IF EXISTS trc_temp_c;
        CREATE TABLE trc_temp_c AS
            SELECT DISTINCT ID, geom
            FROM %s
            WHERE ID NOT IN
                (SELECT DISTINCT ID
                FROM trc_temp_b);
        ALTER TABLE trc_temp_c ADD h DOUBLE PRECISION;
        UPDATE trc_temp_c SET h = 0;
        ALTER TABLE trc_temp_c ADD PAR DOUBLE PRECISION;
        UPDATE trc_temp_c SET PAR = 0;
        ALTER TABLE trc_temp_c ADD zd DOUBLE PRECISION;
        UPDATE trc_temp_c SET zd = 0;
        CREATE INDEX IF NOT EXISTS temp_c_geom_gist ON trc_temp_c USING GIST (geom);

        DROP TABLE IF EXISTS trc_temp;
        CREATE TABLE trc_temp AS
            SELECT ID, h, PAR, zd, geom
            FROM trc_temp_b
            UNION
            SELECT ID, h, PAR, zd, geom
            FROM trc_temp_c;
        ALTER TABLE trc_temp ALTER COLUMN ID TYPE INTEGER;
        CREATE INDEX IF NOT EXISTS temp_geom_gist ON trc_temp USING GIST (geom);
        """ % (table_name_maille, table_name_maille)

        if debug >= 1:
            print(query_bati)
        executeQuery(connection, query_bati)

        #####################################################################################################################################################
        ### Calculs pour l'obtention des sous-indicateurs liés à l'intersect des bâtiments avec chaque ligne N-S, dans chaque maille : frontal area ratio ###
        #####################################################################################################################################################

        print(bold + cyan + "Calcul des indicateurs secondaires liés aux bâtiments intersectant chaque ligne N-S, intersectant chaque maille :" + endC)
        timeLine(path_time_log, "    Calcul des indicateurs secondaires liés aux bâtiments intersectant chaque ligne N-S, intersectant chaque maille : ")

        query_NS = """
        DROP TABLE IF EXISTS trc_tempNS_a;
        CREATE TABLE trc_tempNS_a AS
            SELECT ns.ID as ID, ns.line as line, max(d.hauteur) as max_haut, (%s * max(d.hauteur)) as FA, ns.geom as geom
            FROM trc_decoup as d, trc_decoupNS as ns
            WHERE ST_Intersects(d.geom, ns.geom)
            GROUP BY ns.ID, ns.line, ns.geom;
        CREATE INDEX IF NOT EXISTS tempNS_a_geom_gist ON trc_tempNS_a USING GIST (geom);

        DROP TABLE IF EXISTS trc_tempNS_b;
        CREATE TABLE trc_tempNS_b AS
            SELECT m.ID as ID, (sum(a.FA) / st_area(m.geom)) as FAR, m.geom as geom
            FROM trc_tempNS_a as a, %s as m
            WHERE ST_Intersects(a.geom, m.geom)
            GROUP BY m.ID, m.geom;
        CREATE INDEX IF NOT EXISTS tempNS_b_geom_gist ON trc_tempNS_b USING GIST (geom);

        DROP TABLE IF EXISTS trc_tempNS_c;
        CREATE TABLE trc_tempNS_c AS
            SELECT DISTINCT ID, geom
            FROM %s
            WHERE ID NOT IN
                (SELECT DISTINCT ID
                FROM trc_tempNS_b);
        ALTER TABLE trc_tempNS_c ADD FAR DOUBLE PRECISION;
        UPDATE trc_tempNS_c SET FAR = 0;
        CREATE INDEX IF NOT EXISTS tempNS_c_geom_gist ON trc_tempNS_c USING GIST (geom);

        DROP TABLE IF EXISTS trc_tempNS;
        CREATE TABLE trc_tempNS AS
            SELECT ID, FAR, geom
            FROM trc_tempNS_b
            UNION
            SELECT ID, FAR, geom
            FROM trc_tempNS_c;
        ALTER TABLE trc_tempNS ALTER COLUMN ID TYPE INTEGER;
        CREATE INDEX IF NOT EXISTS tempNS_geom_gist ON trc_tempNS USING GIST (geom);
        """ % (distance_lines, table_name_maille, table_name_maille)

        if debug >= 1:
            print(query_NS)
        executeQuery(connection, query_NS)

        #####################################################################################################################################################
        ### Calculs pour l'obtention des sous-indicateurs liés à l'intersect des bâtiments avec chaque ligne W-E, dans chaque maille : frontal area ratio ###
        #####################################################################################################################################################

        print(bold + cyan + "Calcul des indicateurs secondaires liés aux bâtiments intersectant chaque ligne W-E, intersectant chaque maille :" + endC)
        timeLine(path_time_log, "    Calcul des indicateurs secondaires liés aux bâtiments intersectant chaque ligne W-E, intersectant chaque maille : ")

        query_WE = """
        DROP TABLE IF EXISTS trc_tempWE_a;
        CREATE TABLE trc_tempWE_a AS
            SELECT we.ID as ID, we.line as line, max(d.hauteur) as max_haut, (%s * max(d.hauteur)) as FA, we.geom as geom
            FROM trc_decoup as d, trc_decoupWE as we
            WHERE ST_Intersects(d.geom, we.geom)
            GROUP BY we.ID, we.line, we.geom;
        CREATE INDEX IF NOT EXISTS tempWE_a_geom_gist ON trc_tempWE_a USING GIST (geom);

        DROP TABLE IF EXISTS trc_tempWE_b;
        CREATE TABLE trc_tempWE_b AS
            SELECT m.ID as ID, (sum(a.FA) / st_area(m.geom)) as FAR, m.geom as geom
            FROM trc_tempWE_a as a, %s as m
            WHERE ST_Intersects(a.geom, m.geom)
            GROUP BY m.ID, m.geom;
        CREATE INDEX IF NOT EXISTS tempWE_b_geom_gist ON trc_tempWE_b USING GIST (geom);

        DROP TABLE IF EXISTS trc_tempWE_c;
        CREATE TABLE trc_tempWE_c AS
            SELECT DISTINCT ID, geom
            FROM %s
            WHERE ID NOT IN
                (SELECT DISTINCT ID
                FROM trc_tempWE_b);
        ALTER TABLE trc_tempWE_c ADD FAR DOUBLE PRECISION;
        UPDATE trc_tempWE_c SET FAR = 0;
        CREATE INDEX IF NOT EXISTS tempWE_c_geom_gist ON trc_tempWE_c USING GIST (geom);

        DROP TABLE IF EXISTS trc_tempWE;
        CREATE TABLE trc_tempWE AS
            SELECT ID, FAR, geom
            FROM trc_tempWE_b
            UNION
            SELECT ID, FAR, geom
            FROM trc_tempWE_c;
        ALTER TABLE trc_tempWE ALTER COLUMN ID TYPE INTEGER;
        CREATE INDEX IF NOT EXISTS tempWE_geom_gist ON trc_tempWE USING GIST (geom);
        """ % (distance_lines, table_name_maille, table_name_maille)

        if debug >= 1:
            print(query_WE)
        executeQuery(connection, query_WE)

        ########################################################################################################################
        ### Calculs finaux pour l'obtention de l'indicateur de classe de rugosité : longueur de rugosité, classe de rugosité ###
        ########################################################################################################################

        print(bold + cyan + "Calculs finaux de l'indicateur de classe de rugosité :" + endC)
        timeLine(path_time_log, "    Calculs finaux de l'indicateur de classe de rugosité : ")

        query_rugo = """
        DROP TABLE IF EXISTS trc_rugo;
        CREATE TABLE trc_rugo AS
            SELECT t.ID as ID, t.h as h, t.PAR as PAR, t.zd as zd, ns.FAR as FAR_NS, we.FAR as FAR_WE, t.geom as geom
            FROM trc_temp as t, trc_tempNS as ns, trc_tempWE as we
            WHERE t.ID = ns.ID and ns.ID = WE.ID;
        ALTER TABLE trc_rugo ALTER COLUMN ID TYPE INTEGER;

        ALTER TABLE trc_rugo ADD COLUMN z0_NS DOUBLE PRECISION;
        UPDATE trc_rugo SET z0_NS = ((h - zd) * exp(-sqrt(0.4 / FAR_NS))) WHERE FAR_NS > 0;
        UPDATE trc_rugo SET z0_NS = 0 WHERE FAR_NS = 0;

        ALTER TABLE trc_rugo ADD COLUMN z0_WE DOUBLE PRECISION;
        UPDATE trc_rugo SET z0_WE = ((h - zd) * exp(-sqrt(0.4 / FAR_WE))) WHERE FAR_WE > 0;
        UPDATE trc_rugo SET z0_WE = 0 WHERE FAR_WE = 0;

        ALTER TABLE trc_rugo ADD COLUMN mean_z0 DOUBLE PRECISION;
        UPDATE trc_rugo SET mean_z0 = (z0_NS + z0_WE) / 2;

        ALTER TABLE trc_rugo ADD COLUMN cl_rugo integer;
        UPDATE trc_rugo SET cl_rugo = 1 WHERE mean_z0 < 0.0025;
        UPDATE trc_rugo SET cl_rugo = 2 WHERE mean_z0 >= 0.0025 and mean_z0 < 0.0175;
        UPDATE trc_rugo SET cl_rugo = 3 WHERE mean_z0 >= 0.0175 and mean_z0 < 0.065;
        UPDATE trc_rugo SET cl_rugo = 4 WHERE mean_z0 >= 0.065 and mean_z0 < 0.175;
        UPDATE trc_rugo SET cl_rugo = 5 WHERE mean_z0 >= 0.175 and mean_z0 < 0.375;
        UPDATE trc_rugo SET cl_rugo = 6 WHERE mean_z0 >= 0.375 and mean_z0 < 0.75;
        UPDATE trc_rugo SET cl_rugo = 7 WHERE mean_z0 >= 0.75 and mean_z0 < 1.5;
        UPDATE trc_rugo SET cl_rugo = 8 WHERE mean_z0 >= 1.5;
        """

        if debug >= 1:
            print(query_rugo)
        executeQuery(connection, query_rugo)
        closeConnection(connection)
        exportVectorByOgr2ogr(database_postgis, grid_output, 'trc_rugo', user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema_name=schema_postgis, format_type=format_vector)

        ##########################################
        ### Nettoyage des fichiers temporaires ###
        ##########################################

        if not save_results_intermediate:
            # ~ dropDatabase(database_postgis, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=port_number, schema_name=schema_postgis) # Conflits avec autres indicateurs (Aspect Ratio / Height of Roughness Elements)
            pass

    else:
        print(bold + magenta + "Le calcul de Terrain Roughness Class a déjà eu lieu." + endC)

    print(bold + yellow + "Fin du calcul de l'indicateur Terrain Roughness Class." + endC + "\n")
    timeLine(path_time_log, "Fin du calcul de l'indicateur Terrain Roughness Class : ")

    return

#############################################################################################################################
################################################## Mise en place du parser ##################################################
#############################################################################################################################

def main(gui=False):
    parser = argparse.ArgumentParser(prog = "Calcul de la classe de rugosite (Terrain Roughness Class)",
    description = """Calcul de l'indicateur LCZ classe de rugosite (Terrain Roughness Class) :
    Exemple : python /home/scgsi/Documents/ChaineTraitement/ScriptsLCZ/PerviousSurfaceFraction.py
                        -in  /mnt/Donnees_Etudes/10_Agents/Benjamin/LCZ/Nancy/UrbanAtlas.shp
                        -out /mnt/Donnees_Etudes/10_Agents/Benjamin/LCZ/Nancy/TerrainRoughnessClass.shp
                        -bi  /mnt/Donnees_Etudes/10_Agents/Benjamin/LCZ/Nancy/bati.shp
                        -dl 5""")

    parser.add_argument('-in', '--grid_input', default="", type=str, required=True, help="Fichier de maillage en entree (.shp).")
    parser.add_argument('-out', '--grid_output', default="", type=str, required=True, help="Fichier de maillage en sortie, avec la valeur de Terrain Roughness Class par maille (.shp).")
    parser.add_argument('-bi', '--built_input', default="", type=str, required=True, help="Fichier de la BD TOPO bati en entree (.shp).")
    parser.add_argument('-dl', '--distance_lines', default=5, type=int, required=False, help="Distance separant 2 lignes N-S et 2 lignes W-E (en metres), par defaut 5.")
    parser.add_argument('-epsg','--epsg', default=2154,help="EPSG code projection.", type=int, required=False)
    parser.add_argument('-pe','--project_encoding', default="latin1",help="Project encoding.", type=str, required=False)
    parser.add_argument('-serv','--server_postgis', default="localhost",help="Postgis serveur name or ip.", type=str, required=False)
    parser.add_argument('-port','--port_number', default=5432,help="Postgis port number.", type=int, required=False)
    parser.add_argument('-user','--user_postgis', default="postgres",help="Postgis user name.", type=str, required=False)
    parser.add_argument('-pwd','--password_postgis', default="postgres",help="Postgis password user.", type=str, required=False)
    parser.add_argument('-db','--database_postgis', default="lcz_trc",help="Postgis database name.", type=str, required=False)
    parser.add_argument('-sch','--schema_postgis', default="public",help="Postgis schema name.", type=str, required=False)
    parser.add_argument('-vef','--format_vector', default="ESRI Shapefile",help="Format of the output file.", type=str, required=False)
    parser.add_argument('-log', '--path_time_log', default="", type=str, required=False, help="Name of log")
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
    if args.distance_lines != None:
        distance_lines = args.distance_lines

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
        print(bold + green + "Calcul de la classe de rugosité :" + endC)
        print(cyan + "TerrainRoughnessClass : " + endC + "grid_input : " + str(grid_input) + endC)
        print(cyan + "TerrainRoughnessClass : " + endC + "grid_output : " + str(grid_output) + endC)
        print(cyan + "TerrainRoughnessClass : " + endC + "built_input : " + str(built_input) + endC)
        print(cyan + "TerrainRoughnessClass : " + endC + "distance_lines : " + str(distance_lines) + endC)
        print(cyan + "TerrainRoughnessClass : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "TerrainRoughnessClass : " + endC + "project_encoding : " + str(project_encoding) + endC)
        print(cyan + "TerrainRoughnessClass : " + endC + "server_postgis : " + str(server_postgis) + endC)
        print(cyan + "TerrainRoughnessClass : " + endC + "port_number : " + str(port_number) + endC)
        print(cyan + "TerrainRoughnessClass : " + endC + "user_postgis : " + str(user_postgis) + endC)
        print(cyan + "TerrainRoughnessClass : " + endC + "password_postgis : " + str(password_postgis) + endC)
        print(cyan + "TerrainRoughnessClass : " + endC + "database_postgis : " + str(database_postgis) + endC)
        print(cyan + "TerrainRoughnessClass : " + endC + "schema_postgis : " + str(schema_postgis) + endC)
        print(cyan + "TerrainRoughnessClass : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "TerrainRoughnessClass : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "TerrainRoughnessClass : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "TerrainRoughnessClass : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "TerrainRoughnessClass : " + endC + "debug : " + str(debug) + endC)

    if not os.path.exists(os.path.dirname(grid_output)):
        os.makedirs(os.path.dirname(grid_output))

    terrainRoughnessClass(grid_input, grid_output, built_input, distance_lines, epsg, project_encoding, server_postgis, port_number, user_postgis, password_postgis, database_postgis, schema_postgis, path_time_log, format_vector, save_results_intermediate, overwrite)

if __name__ == '__main__':
    main(gui=False)

