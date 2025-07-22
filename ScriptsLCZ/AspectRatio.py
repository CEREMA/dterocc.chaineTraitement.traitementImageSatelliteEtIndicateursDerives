#!/usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

from __future__ import print_function
import os, sys, argparse, shutil, math
from Lib_log import timeLine
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_vector import getEmpriseVector
from Lib_postgis import executeQuery, openConnection, closeConnection, createDatabase, dropDatabase, importVectorByOgr2ogr, exportVectorByOgr2ogr
from Lib_file import removeVectorFile
from Lib_grass import initializeGrass, connectionGrass, cleanGrass, splitGrass

# debug = 1 : affichage requêtes SQL principales + avancement boucles
# debug = 2 : affichage 1 + requêtes SQL de tables temp dans les boucles
# debug = 3 : affichage 2 + valeurs des variables calculées dans chaque boucle (coordonnées, distances, angles...)
debug = 3

####################################################################################################
# FONCTION aspectRatio()                                                                           #
####################################################################################################
def aspectRatio(grid_input, grid_output, roads_input, built_input, seg_dist, seg_length, buffer_size, epsg, project_encoding, server_postgis, port_number, user_postgis, password_postgis, database_postgis, schema_postgis, path_time_log, format_vector='ESRI Shapefile', extension_vector=".shp", save_results_intermediate=False, overwrite=True):
    """
    # ROLE :
    #     Calcul de l'indicateur LCZ rapport d'aspect
    #
    # ENTREES DE LA FONCTION :
    #     grid_input : fichier de maillage en entrée
    #     grid_output : fichier de maillage en sortie
    #     roads_input : fichier de la BD TOPO route en entrée
    #     built_input : fichier de la BD TOPO bâti en entrée
    #     seg_dist : distance entre les segments perpendiculaires aux segments route (en mètres)
    #     seg_length : longueur des segments perpendiculaires aux segments route (en mètres)
    #     buffer_size : taille du buffer appliqué sur les polygones mailles (en mètres)
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
    #     extension_vector : extension du fichier vecteur de sortie, par defaut = '.shp'
    #     save_results_intermediate : fichiers de sorties intermédiaires nettoyés, par défaut = False
    #     overwrite : écrase si un fichier existant a le même nom qu'un fichier de sortie, par défaut = True
    #
    # SORTIES DE LA FONCTION :
    #     N.A
    """

    print(bold + yellow + "Début du calcul de l'indicateur Aspect Ratio." + endC + "\n")
    timeLine(path_time_log, "Début du calcul de l'indicateur Aspect Ratio : ")

    if debug >= 3:
        print(bold + green + "aspectRatio() : Variables dans la fonction" + endC)
        print(cyan + "aspectRatio() : " + endC + "grid_input : " + str(grid_input) + endC)
        print(cyan + "aspectRatio() : " + endC + "grid_output : " + str(grid_output) + endC)
        print(cyan + "aspectRatio() : " + endC + "roads_input : " + str(roads_input) + endC)
        print(cyan + "aspectRatio() : " + endC + "built_input : " + str(built_input) + endC)
        print(cyan + "aspectRatio() : " + endC + "seg_dist : " + str(seg_dist) + endC)
        print(cyan + "aspectRatio() : " + endC + "seg_length : " + str(seg_length) + endC)
        print(cyan + "aspectRatio() : " + endC + "buffer_size : " + str(buffer_size) + endC)
        print(cyan + "aspectRatio() : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "aspectRatio() : " + endC + "project_encoding : " + str(project_encoding) + endC)
        print(cyan + "aspectRatio() : " + endC + "server_postgis : " + str(server_postgis) + endC)
        print(cyan + "aspectRatio() : " + endC + "port_number : " + str(port_number) + endC)
        print(cyan + "aspectRatio() : " + endC + "user_postgis : " + str(user_postgis) + endC)
        print(cyan + "aspectRatio() : " + endC + "password_postgis : " + str(password_postgis) + endC)
        print(cyan + "aspectRatio() : " + endC + "database_postgis : " + str(database_postgis) + endC)
        print(cyan + "aspectRatio() : " + endC + "schema_postgis : " + str(schema_postgis) + endC)
        print(cyan + "aspectRatio() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "aspectRatio() : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "aspectRatio() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "aspectRatio() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "aspectRatio() : " + endC + "overwrite : " + str(overwrite) + endC)

    # Constantes liées aux données PostGIS et GRASS
    LOCATION = "LOCATION"
    MAPSET = "MAPSET"
    SUFFIX_SEGMENTED = "_segmented"

    if not os.path.exists(grid_output) or overwrite:

        ############################################
        ### Préparation générale des traitements ###
        ############################################

        if os.path.exists(grid_output):
            removeVectorFile(grid_output)

        temp_path = os.path.dirname(grid_output) + os.sep + "AspectRatio"
        file_name = os.path.splitext(os.path.basename(roads_input))[0]
        roads_segmented = temp_path + os.sep + file_name + SUFFIX_SEGMENTED + extension_vector

        if os.path.exists(temp_path):
            shutil.rmtree(temp_path)

        # Variables d'environnement spécifiques à GRASS
        gisbase = os.environ['GISBASE']
        gisdb = "GRASS_database"

        # Variables liées à GRASS permettant la construction de 'LOCATION' et 'MAPSET'
        xmin, xmax, ymin, ymax = getEmpriseVector(roads_input, format_vector)
        pixel_size_x, pixel_size_y = 1, 1

        #####################################
        ### Préparation géodatabase GRASS ###
        #####################################

        print(bold + cyan + "Préparation de la géodatabase GRASS :" + endC)
        timeLine(path_time_log, "    Préparation de la géodatabase GRASS : ")

        # Initialisation de la connexion à la géodatabase GRASS
        gisbase, gisdb, location, mapset = initializeGrass(temp_path, xmin, xmax, ymin, ymax, pixel_size_x, pixel_size_y, epsg, gisbase, gisdb, LOCATION, MAPSET, True, overwrite)

        ###################################################
        ### Division des routes en segments de x mètres ###
        ###################################################

        print(bold + cyan + "Segmentation des routes avec GRASS :" + endC)
        timeLine(path_time_log, "    Segmentation des routes avec GRASS : ")

        # Segmentation du jeu de données route en segments de x mètres
        splitGrass(roads_input, roads_segmented, seg_dist, format_vector, overwrite)
        cleanGrass(temp_path, gisdb, save_results_intermediate)

        ###########################################
        ### Préparation base de données PostGIS ###
        ###########################################

        print(bold + cyan + "Préparation de la base de données PostGIS :" + endC)
        timeLine(path_time_log, "    Préparation de la base de données PostGIS : ")

        # Création de la base de données PostGIS
        # ~ dropDatabase(database_postgis, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=port_number, schema_name=schema_postgis) # Conflits avec autres indicateurs (Height of Roughness Elements / Terrain Roughness Class)
        createDatabase(database_postgis, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=port_number, schema_name=schema_postgis)

        # Import des fichiers shapes maille, bati et routes segmentées dans la base de données PostGIS
        table_name_maille = importVectorByOgr2ogr(database_postgis, grid_input, 'ara_maille', user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema_name=schema_postgis, epsg=str(epsg), codage=project_encoding)
        table_name_bati = importVectorByOgr2ogr(database_postgis, built_input, 'ara_bati', user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema_name=schema_postgis, epsg=str(epsg), codage=project_encoding)
        table_name_routes_seg = importVectorByOgr2ogr(database_postgis, roads_segmented, 'ara_routes_seg', user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema_name=schema_postgis, epsg=str(epsg), codage=project_encoding)

        # Connection à la base de données PostGIS et initialisation de 'cursor' (permet de récupérer des résultats de requêtes SQL pour les traiter en Python)
        connection = openConnection(database_postgis, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=port_number, schema_name=schema_postgis)
        cursor = connection.cursor()

        # Requête d'ajout de champ ID segment route dans la table routes_seg et création des index pour les shapes importés
        query_preparation = """
        ALTER TABLE %s ADD COLUMN id_seg serial;
        --CREATE INDEX IF NOT EXISTS routes_seg_geom_gist ON %s USING GIST (geom);
        --CREATE INDEX IF NOT EXISTS bati_geom_gist ON %s USING GIST (geom);
        --CREATE INDEX IF NOT EXISTS maille_geom_gist ON %s USING GIST (geom);
        """ % (table_name_routes_seg, table_name_routes_seg, table_name_bati, table_name_maille)
        if debug >= 2:
            print(query_preparation)
        executeQuery(connection, query_preparation)

        ##############################################################################
        ### Création des segments de y mètres perpendiculaires aux segments routes ###
        ##############################################################################

        print(bold + cyan + "Création des segments perpendiculaires aux routes :" + endC)
        timeLine(path_time_log, "    Création des segments perpendiculaires aux routes : ")

        # Début de la construction de la requête de création des segments perpendiculaires
        query_seg_perp = "DROP TABLE IF EXISTS ara_seg_perp;\n"
        query_seg_perp += "CREATE TABLE ara_seg_perp (id_seg text, id_perp text, xR float, yR float, xP float, yP float, geom geometry);\n"
        query_seg_perp += "INSERT INTO ara_seg_perp VALUES\n"

        # Récupération de la liste des identifiants segments routes
        cursor.execute("SELECT id_seg FROM %s GROUP BY id_seg ORDER BY id_seg;" % table_name_routes_seg)
        id_seg_list = cursor.fetchall()

        # Boucle sur les segments routes
        nb_seg = len(id_seg_list)
        treat_seg = 1
        for id_seg in id_seg_list:
            if debug >= 4:
                print(bold + "    Traitement du segment route : " + endC + str(treat_seg) + "/" + str(nb_seg))

            id_seg = id_seg[0]

            # Table temporaire ne contenant qu'un segment route donné : ST_LineMerge(geom) permet de passer la géométrie de MultiLineString à LineString, pour éviter des problèmes de requêtes spatiales
            query_temp1_seg = "DROP TABLE IF EXISTS ara_temp1_seg;\n"
            query_temp1_seg += "CREATE TABLE ara_temp1_seg AS SELECT id_seg as id_seg, ST_LineMerge(geom) as geom FROM %s WHERE id_seg = %s;\n" % (table_name_routes_seg, id_seg)
            if debug >= 4:
                print(query_temp1_seg)
            executeQuery(connection, query_temp1_seg)

            # Récupération du nombre de sommets du segment route (utile pour les segments routes en courbe, permet de récupérer le dernier point du segment)
            cursor.execute("SELECT ST_NPoints(geom) FROM ara_temp1_seg;")
            nb_points = cursor.fetchone()

            # Récupération des coordonnées X et Y des points extrémités du segment route
            query_xR1 = "SELECT ST_X(geom) as X FROM (SELECT ST_AsText(ST_PointN(geom,1)) as geom FROM ara_temp1_seg) as toto;"
            cursor.execute(query_xR1)
            xR1 = cursor.fetchone()
            query_yR1 = "SELECT ST_Y(geom) as Y FROM (SELECT ST_AsText(ST_PointN(geom,1)) as geom FROM ara_temp1_seg) as toto;"
            cursor.execute(query_yR1)
            yR1 = cursor.fetchone()
            query_xR2 = "SELECT ST_X(geom) as X FROM (SELECT ST_AsText(ST_PointN(geom,%s)) as geom FROM ara_temp1_seg) as toto;" % (nb_points)
            cursor.execute(query_xR2)
            xR2 = cursor.fetchone()
            query_yR2 = "SELECT ST_Y(geom) as Y FROM (SELECT ST_AsText(ST_PointN(geom,%s)) as geom FROM ara_temp1_seg) as toto;" % (nb_points)
            cursor.execute(query_yR2)
            yR2 = cursor.fetchone()

            # Transformation des coordonnées X et Y des points extrémités du segment route en valeurs numériques
            xR1 = float(str(xR1)[1:-2])
            yR1 = float(str(yR1)[1:-2])
            xR2 = float(str(xR2)[1:-2])
            yR2 = float(str(yR2)[1:-2])
            if debug >= 4:
                print("      xR1 = " + str(xR1))
                print("      yR1 = " + str(yR1))
                print("      xR2 = " + str(xR2))
                print("      yR2 = " + str(yR2))

            # Calcul des delta X et Y entre les points extrémités du segment route
            dxR = xR1-xR2
            dyR = yR1-yR2
            if debug >= 4:
                print("      dxR = " + str(dxR))
                print("      dyR = " + str(dyR))
                print("\n")

            # Suppression des cas où le script créé des perpendiculaires tous les cm ! Bug lié à la segmentation des routes
            dist_R1_R2 = math.sqrt((abs(dxR)**2) + (abs(dyR)**2))
            if dist_R1_R2 >= (seg_dist/2):

                # Calcul de l'angle (= gisement) entre le Nord et le segment route
                if dxR == 0 or dyR == 0:
                    if dxR == 0 and dyR > 0:
                        aR = 0
                    elif dxR > 0 and dyR == 0:
                        aR = 90
                    elif dxR == 0 and dyR < 0:
                        aR = 180
                    elif dxR < 0 and dyR == 0:
                        aR = 270
                else:
                    aR = math.degrees(math.atan(dxR/dyR))
                    if aR < 0:
                        aR = aR + 360
                if debug >= 4:
                    print("      aR = " + str(aR))

                # Calcul des angles (= gisements) entre le Nord et les 2 segments perpendiculaires au segment route
                aP1 = aR + 90
                if aP1 < 0 :
                    aP1 = aP1 + 360
                if aP1 >= 360:
                    aP1 = aP1 - 360
                aP2 = aR - 90
                if aP2 < 0 :
                    aP2 = aP2 + 360
                if aP2 >= 360:
                    aP2 = aP2 - 360
                if debug >= 4:
                    print("      aP1 = " + str(aP1))
                    print("      aP2 = " + str(aP2))

                # Calculs des coordonnées des nouveaux points à l'extrémité de chaque segment perpendiculaire pour le segment route sélectionné
                xP1 = xR1 + (seg_length * math.sin(math.radians(aP1)))
                yP1 = yR1 + (seg_length * math.cos(math.radians(aP1)))
                xP2 = xR1 + (seg_length * math.sin(math.radians(aP2)))
                yP2 = yR1 + (seg_length * math.cos(math.radians(aP2)))
                if debug >= 4:
                    print("      xP1 = " + str(xP1))
                    print("      yP1 = " + str(yP1))
                    print("      xP2 = " + str(xP2))
                    print("      yP2 = " + str(yP2))
                    print("\n")

                # Construction de la requête de création des 2 segments perpendiculaires pour le segment route sélectionné
                query_seg_perp += "    ('%s', '%s_perp1', %s, %s, %s, %s, 'LINESTRING(%s %s, %s %s)'),\n" % (str(id_seg), str(id_seg), xR1, yR1, xP1, yP1, xR1, yR1, xP1, yP1)
                query_seg_perp += "    ('%s', '%s_perp2', %s, %s, %s, %s, 'LINESTRING(%s %s, %s %s)'),\n" % (str(id_seg), str(id_seg), xR1, yR1, xP2, yP2, xR1, yR1, xP2, yP2)

            treat_seg += 1

        # Fin de la construction de la requête de création des segments perpendiculaires et exécution de cette requête
        query_seg_perp = query_seg_perp[:-2] + ";\n" # Transformer la virgule de la dernière ligne SQL en point-virgule (pour terminer la requête)
        query_seg_perp += "ALTER TABLE ara_seg_perp ALTER COLUMN geom TYPE geometry(LINESTRING,%s) USING ST_SetSRID(geom,%s);\n" % (epsg,epsg) # Mise à jour du système de coordonnées
        query_seg_perp += "CREATE INDEX IF NOT EXISTS seg_perp_geom_gist ON ara_seg_perp USING GIST (geom);\n"
        if debug >= 2:
            print(query_seg_perp)
        executeQuery(connection, query_seg_perp)

        ###################################################
        ### Intersect segments perpendiculaires et bâti ###
        ###################################################

        print(bold + cyan + "Intersect entre les segments perpendiculaires et les bâtiments :" + endC)
        timeLine(path_time_log, "    Intersect entre les segments perpendiculaires et les bâtiments : ")

        # Requête d'intersect entre les segments perpendiculaires et les bâtiments
        query_intersect = """
        DROP TABLE IF EXISTS ara_intersect_bati;
        CREATE TABLE ara_intersect_bati AS
            SELECT r.id_seg as id_seg, r.id_perp as id_perp, r.xR as xR, r.yR as yR, b.HAUTEUR as haut_bati, ST_Intersection(r.geom, b.geom) as geom
            FROM ara_seg_perp as r, %s as b
            WHERE ST_Intersects(r.geom, b.geom)
                AND b.HAUTEUR IS NOT NULL
                AND b.HAUTEUR > 0;
        ALTER TABLE ara_intersect_bati ADD COLUMN id_intersect serial;
        CREATE INDEX IF NOT EXISTS intersect_bati_geom_gist ON ara_intersect_bati USING GIST (geom);
        """ % table_name_bati
        if debug >= 2:
            print(query_intersect)
        executeQuery(connection, query_intersect)

        ##################################################################################################################
        ### Récupération des demi-largeurs de rue et de la hauteur du 1er bâtiment pour chaque segment perpendiculaire ###
        ##################################################################################################################

        print(bold + cyan + "Récupération des informations nécessaires au calcul du rapport d'aspect :" + endC)
        timeLine(path_time_log, "    Récupération des informations nécessaires au calcul du rapport d'aspect : ")

        # Début de la construction de la requête de création des points route, avec infos de demi-largeurs de rue et hauteurs des bâtiments
        query_pt_route = "DROP TABLE IF EXISTS ara_asp_ratio_by_seg;\n"
        query_pt_route += "CREATE TABLE ara_asp_ratio_by_seg (id_seg text, xR float, yR float, width1 float, height1 float, width2 float, height2 float, geom geometry);\n"
        query_pt_route += "INSERT INTO ara_asp_ratio_by_seg VALUES\n"

        # Récupération de la liste des identifiants segments routes (uniquement ceux qui intersectent du bâti)
        cursor.execute("SELECT id_seg FROM ara_intersect_bati GROUP BY id_seg ORDER BY id_seg;")
        id_seg_list = cursor.fetchall()

        # Boucle sur les segments routes
        nb_seg = len(id_seg_list)
        treat_seg = 1
        for id_seg in id_seg_list:
            if debug >= 4:
                print(bold + "    Traitement du segment route : " + endC + str(treat_seg) + "/" + str(nb_seg))

            id_seg = id_seg[0]

            # Table temporaire ne contenant que les intersects d'un segment route donné
            query_temp2_seg = "DROP TABLE IF EXISTS ara_temp2_seg;\n"
            query_temp2_seg += "CREATE TABLE ara_temp2_seg AS SELECT id_seg, id_perp, xR, yR, haut_bati, id_intersect, geom FROM ara_intersect_bati WHERE id_seg = '%s';\n" % (id_seg)
            if debug >= 4:
                print(query_temp2_seg)
            executeQuery(connection, query_temp2_seg)

            # Récupération des coordonnées X et Y du point route du segment route associé
            cursor.execute("SELECT xR FROM ara_temp2_seg;")
            xR = cursor.fetchone()
            cursor.execute("SELECT yR FROM ara_temp2_seg;")
            yR = cursor.fetchone()

            # Transformation des coordonnées X et Y du point route du segment route associé en valeurs numériques
            xR = float(str(xR)[1:-2])
            yR = float(str(yR)[1:-2])
            if debug >= 4:
                print("      xR = " + str(xR))
                print("      yR = " + str(yR))
                print("\n")

            # Initialisation des variables demi-largeurs de rue et hauteur du 1er bâtiment intersecté
            w1 = 0
            h1 = 0
            w2 = 0
            h2 = 0

            # Récupération de la liste des identifiants segments perpendiculaires de la table temp2_seg
            cursor.execute("SELECT id_perp FROM ara_temp2_seg GROUP BY id_perp ORDER BY id_perp;")
            id_perp_list = cursor.fetchall()

            # Boucle sur les perpendiculaires (max 2) d'un segment route donné
            for id_perp in id_perp_list:

                # Récupération du numéro de perpendiculaire (1 ou 2 ~ droite ou gauche)
                num_seg = float(str(id_perp)[-4:-3])

                # Initialisation de listes contenant les demi-largeurs de rue et les hauteurs des bâtiments intersectés
                length_list = []
                haut_bati_list = []

                # Table temporaire ne contenant que les intersects d'un segment perpendiculaire donné
                query_temp2_perp = "DROP TABLE IF EXISTS ara_temp2_perp;\n"
                query_temp2_perp += "CREATE TABLE ara_temp2_perp AS SELECT id_seg, id_perp, xR, yR, haut_bati, id_intersect, geom FROM ara_temp2_seg WHERE id_perp = '%s';\n" % (id_perp)
                if debug >= 4:
                    print(query_temp2_perp)
                executeQuery(connection, query_temp2_perp)

                # Récupération de la liste des identifiants segments intersects de la table temp2_perp
                cursor.execute("SELECT id_intersect FROM ara_temp2_perp GROUP BY id_intersect ORDER BY id_intersect;")
                id_intersect_list = cursor.fetchall()

                # Boucle sur les intersects d'un segment perpendiculaire donné, d'un segment route donné
                for id_intersect in id_intersect_list:

                    # Récupération des coordonnées X et Y des points extrémités de chaque segment intersect
                    query_xI1 = "SELECT ST_X(geom) as X FROM (SELECT ST_AsText(ST_PointN(geom,1)) as geom FROM ara_temp2_perp WHERE id_intersect = '%s') as toto;" % (id_intersect)
                    cursor.execute(query_xI1)
                    xI1 = cursor.fetchone()
                    query_yI1 = "SELECT ST_Y(geom) as Y FROM (SELECT ST_AsText(ST_PointN(geom,1)) as geom FROM ara_temp2_perp WHERE id_intersect = '%s') as toto;" % (id_intersect)
                    cursor.execute(query_yI1)
                    yI1 = cursor.fetchone()
                    query_xI2 = "SELECT ST_X(geom) as X FROM (SELECT ST_AsText(ST_PointN(geom,2)) as geom FROM ara_temp2_perp WHERE id_intersect = '%s') as toto;" % (id_intersect)
                    cursor.execute(query_xI2)
                    xI2 = cursor.fetchone()
                    query_yI2 = "SELECT ST_Y(geom) as Y FROM (SELECT ST_AsText(ST_PointN(geom,2)) as geom FROM ara_temp2_perp WHERE id_intersect = '%s') as toto;" % (id_intersect)
                    cursor.execute(query_yI2)
                    yI2 = cursor.fetchone()

                    # Transformation des coordonnées X et Y des points extrémités de chaque segment intersect en valeurs numériques
                    try:
                        xI1 = float(str(xI1)[1:-2])
                        yI1 = float(str(yI1)[1:-2])
                        xI2 = float(str(xI2)[1:-2])
                        yI2 = float(str(yI2)[1:-2])
                    except ValueError: # Python renvoie une valeur Null pour les bâtiments en U (= intersectés à plus de 2 points)
                        xI1 = yI1 = xI2 = yI2 = 0
                    if debug >= 4:
                        print("              xI1 = " + str(xI1))
                        print("              yI1 = " + str(yI1))
                        print("              xI2 = " + str(xI2))
                        print("              yI2 = " + str(yI2))

                    # Calcul des distances entre la route et chaque point du segment intersect
                    length_intersect1 = math.sqrt((abs(xR-xI1)**2) + (abs(yR-yI1)**2))
                    length_intersect2 = math.sqrt((abs(xR-xI2)**2) + (abs(yR-yI2)**2))
                    if debug >= 4:
                        print("              length_intersect1 = " + str(length_intersect1))
                        print("              length_intersect2 = " + str(length_intersect2))

                    # Récupération de la valeur de distance entre la route et le point d'intersect le plus proche (+ ajout dans la liste length_list)
                    length = min(length_intersect1, length_intersect2)
                    length_list.append(length)
                    if debug >= 4:
                        print("              length = " + str(length))

                    # Récupération de la hauteur du bâtiment correspondant à l'intersect (+ ajout dans la liste haut_bati_list)
                    query_haut_bati = "SELECT haut_bati FROM ara_temp2_perp WHERE id_intersect = '%s';" % (id_intersect)
                    cursor.execute(query_haut_bati)
                    haut_bati = cursor.fetchone()
                    haut_bati = float(str(haut_bati)[10:-4])
                    haut_bati_list.append(haut_bati)
                    if debug >= 4:
                        print("              haut_bati = " + str(haut_bati))
                        print("\n")

                # Pour un segment perpendiculaire donné, récupération de la distance minimale entre la route et les intersect avec le bâti
                width = min(length_list)
                if debug >= 4:
                    print("          width = " + str(width))

                # Pour un segment perpendiculaire donné, récupération de la hauteur du bâtiment correspondant au segment intersect le plus proche de la route
                height_position = length_list.index(width)
                height = haut_bati_list[height_position]
                if debug >= 4:
                    print("          height = " + str(height))
                    print("\n")

                # MAJ des variables demi-largeurs de rue et hauteur du 1er bâtiment intersecté suivant le côté de la perpendiculaire par rapport à la route
                if num_seg == 1:
                    w1 = width
                    h1 = height
                elif num_seg == 2:
                    w2 = width
                    h2 = height

            # Construction de la requête de création du point route pour le segment route donné
            query_pt_route += "    ('%s', %s, %s, %s, %s, %s, %s, 'POINT(%s %s)'),\n" % (str(id_seg), xR, yR, w1, h1, w2, h2, xR, yR)

            treat_seg += 1

        # Fin de la construction de la requête de création des points route, avec infos de demi-largeurs de rue et hauteurs des bâtiments
        query_pt_route = query_pt_route[:-2] + ";\n" # Transformer la virgule de la dernière ligne SQL en point-virgule (pour terminer la requête)
        query_pt_route += "ALTER TABLE ara_asp_ratio_by_seg ALTER COLUMN geom TYPE geometry(POINT,%s) USING ST_SetSRID(geom,%s);\n" % (epsg,epsg) # Mise à jour du système de coordonnées
        query_pt_route += "CREATE INDEX IF NOT EXISTS asp_ratio_by_seg_geom_gist ON ara_asp_ratio_by_seg USING GIST (geom);\n"
        if debug >= 2:
            print(query_pt_route)
        executeQuery(connection, query_pt_route)


        ###########################################################
        ### Calcul de l'indicateur et export de la table finale ###
        ###########################################################

        print(bold + cyan + "Calculs finaux de l'indicateur de rapport d'aspect :" + endC)
        timeLine(path_time_log, "    Calculs finaux de l'indicateur de rapport d'aspect : ")

        # Requête de calcul d'un rapport d'aspect par segment route
        query_asp_ratio_by_seg = """
        ALTER TABLE ara_asp_ratio_by_seg ADD COLUMN asp_ratio float;
        UPDATE ara_asp_ratio_by_seg SET asp_ratio = 0;
        UPDATE ara_asp_ratio_by_seg SET asp_ratio = ((height1 + height2) / 2) / (width1 + width2) WHERE height1 <> 0 AND height2 <> 0 AND width1 <> 0 AND width2 <> 0;
        """
        if debug >= 2:
            print(query_asp_ratio_by_seg)
        executeQuery(connection, query_asp_ratio_by_seg)

        # Requête de bufferisation du fichier maillage
        query_buffer = """
        DROP TABLE IF EXISTS ara_buffer;
        CREATE TABLE ara_buffer AS
            SELECT ID as ID, ST_Buffer(geom, %s) as geom
            FROM %s;
        CREATE INDEX IF NOT EXISTS buffer_geom_gist ON ara_buffer USING GIST (geom);
        """ % (buffer_size, table_name_maille)
        if debug >= 2:
            print(query_buffer)
        executeQuery(connection, query_buffer)

        # Requête de calcul d'un rapport d'aspect par maille (via un intersect sur le maillage bufferisé)
        query_asp_ratio_temp1 = """
        DROP TABLE IF EXISTS ara_asp_ratio_temp1;
        CREATE TABLE ara_asp_ratio_temp1 AS
            SELECT m.ID as ID, avg(r.asp_ratio) as asp_ratio, m.geom as geom
            FROM %s as m, ara_buffer as b, ara_asp_ratio_by_seg as r
            WHERE ST_Intersects(b.geom, r.geom)
                AND m.ID = b.ID
                AND r.asp_ratio > 0
            GROUP BY m.ID, m.geom;
        CREATE INDEX IF NOT EXISTS asp_ratio_temp1_geom_gist ON ara_asp_ratio_temp1 USING GIST (geom);
        """ % (table_name_maille)
        if debug >= 2:
            print(query_asp_ratio_temp1)
        executeQuery(connection, query_asp_ratio_temp1)

        # Rapport d'aspect pour les mailles n'intersectant pas de points-route avec un rapport d'aspect
        query_asp_ratio_temp2 = """
        DROP TABLE IF EXISTS ara_asp_ratio_temp2;
        CREATE TABLE ara_asp_ratio_temp2 AS
            SELECT DISTINCT ID as ID, geom as geom
            FROM %s
            WHERE ID NOT IN
                (SELECT DISTINCT ID
                FROM ara_asp_ratio_temp1);
        ALTER TABLE ara_asp_ratio_temp2 ADD COLUMN asp_ratio float;
        UPDATE ara_asp_ratio_temp2 SET asp_ratio = 0;
        CREATE INDEX IF NOT EXISTS asp_ratio_temp2_geom_gist ON ara_asp_ratio_temp2 USING GIST (geom);
        """ % table_name_maille
        if debug >= 1:
            print(query_asp_ratio_temp2)
        executeQuery(connection, query_asp_ratio_temp2)

        # Fusion des 2 tables précédentes pour retrouver l'ensemble des mailles de départ
        query_asp_ratio = """
        DROP TABLE IF EXISTS ara_asp_ratio;
        CREATE TABLE ara_asp_ratio AS
            SELECT ID, asp_ratio, geom
            FROM ara_asp_ratio_temp1
            UNION
            SELECT ID, asp_ratio, geom
            FROM ara_asp_ratio_temp2;
        ALTER TABLE ara_asp_ratio ALTER COLUMN ID TYPE INTEGER;
        """
        if debug >= 2:
            print(query_asp_ratio)
        executeQuery(connection, query_asp_ratio)
        closeConnection(connection)
        exportVectorByOgr2ogr(database_postgis, grid_output, 'ara_asp_ratio', user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema_name=schema_postgis, format_type=format_vector)

        ##########################################
        ### Nettoyage des fichiers temporaires ###
        ##########################################

        if not save_results_intermediate:
            if os.path.exists(temp_path):
                shutil.rmtree(temp_path)
            # ~ dropDatabase(database_postgis, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=port_number, schema_name=schema_postgis) # Conflits avec autres indicateurs (Height of Roughness Elements / Terrain Roughness Class)

    else:
        print(bold + magenta + "Le calcul de Aspect Ratio a déjà eu lieu." + endC)

    print(bold + yellow + "Fin du calcul de l'indicateur Aspect Ratio." + endC + "\n")
    timeLine(path_time_log, "Fin du calcul de l'indicateur Aspect Ratio : ")

    return

#############################################################################################################################
################################################## Mise en place du parser ##################################################
#############################################################################################################################

def main(gui=False):
    parser = argparse.ArgumentParser(prog = "Calcul du rapport d'aspect (Aspect Ratio)",
    description = """Calcul de l'indicateur LCZ rapport d'aspect (Aspect Ratio) :
    Exemple : python /home/scgsi/Documents/ChaineTraitement/ScriptsLCZ/AspectRatio.py
                        -in  /mnt/Donnees_Etudes/10_Agents/Benjamin/LCZ/Nancy/UrbanAtlas2012_cleaned.shp
                        -out /mnt/Donnees_Etudes/10_Agents/Benjamin/LCZ/Nancy/AspectRatio.shp
                        -ri  /mnt/Donnees_Etudes/10_Agents/Benjamin/LCZ/Nancy/BDTOPO_route.shp
                        -bi  /mnt/Donnees_Etudes/10_Agents/Benjamin/LCZ/Nancy/BDTOPO_bati.shp
                        -sd 10 -sl 30 -bs 15""")

    parser.add_argument('-in', '--grid_input', default="", type=str, required=True, help="Fichier de maillage en entree (vecteur).")
    parser.add_argument('-out', '--grid_output', default="", type=str, required=True, help="Fichier de maillage en sortie, avec la valeur de Aspect Ratio par maille (vecteur).")
    parser.add_argument('-ri', '--roads_input', default="", type=str, required=True, help="Fichier de la BD TOPO route en entree (vecteur).")
    parser.add_argument('-bi', '--built_input', default="", type=str, required=True, help="Fichier de la BD TOPO bati en entree (vecteur).")
    parser.add_argument('-sd', '--seg_dist', default=10, type=int, required=False, help="Distance entre les segments perpendiculaires aux segments route (en metres), par defaut : 10.")
    parser.add_argument('-sl', '--seg_length', default=30, type=int, required=False, help="Longueur des segments perpendiculaires aux segments route (en metres), par defaut : 30.")
    parser.add_argument('-bs', '--buffer_size', default=15, type=int, required=False, help="Taille du buffer applique sur les polygones mailles (en metres), par defaut : 15.")
    parser.add_argument('-epsg','--epsg', default=2154,help="EPSG code projection.", type=int, required=False)
    parser.add_argument('-pe','--project_encoding', default="latin1",help="Project encoding.", type=str, required=False)
    parser.add_argument('-serv','--server_postgis', default="localhost",help="Postgis serveur name or ip.", type=str, required=False)
    parser.add_argument('-port','--port_number', default=5432,help="Postgis port number.", type=int, required=False)
    parser.add_argument('-user','--user_postgis', default="postgres",help="Postgis user name.", type=str, required=False)
    parser.add_argument('-pwd','--password_postgis', default="postgres",help="Postgis password user.", type=str, required=False)
    parser.add_argument('-db','--database_postgis', default="lcz_ara",help="Postgis database name.", type=str, required=False)
    parser.add_argument('-sch','--schema_postgis', default="public",help="Postgis schema name.", type=str, required=False)
    parser.add_argument('-vef','--format_vector', default="ESRI Shapefile",help="Format of the output vector file.", type=str, required=False)
    parser.add_argument('-vee','--extension_vector',default=".shp",help="Option : Extension file for vector. By default : '.shp'", type=str, required=False)
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

    if args.roads_input != None:
        roads_input = args.roads_input
    if args.built_input != None:
        built_input = args.built_input

    if args.seg_dist != None:
        seg_dist = args.seg_dist
    if args.seg_length != None:
        seg_length = args.seg_length
    if args.buffer_size != None:
        buffer_size = args.buffer_size

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
        print(bold + green + "Calcul du rapport d'aspect :" + endC)
        print(cyan + "AspectRatio : " + endC + "grid_input : " + str(grid_input) + endC)
        print(cyan + "AspectRatio : " + endC + "grid_output : " + str(grid_output) + endC)
        print(cyan + "AspectRatio : " + endC + "roads_input : " + str(roads_input) + endC)
        print(cyan + "AspectRatio : " + endC + "built_input : " + str(built_input) + endC)
        print(cyan + "AspectRatio : " + endC + "seg_dist : " + str(seg_dist) + endC)
        print(cyan + "AspectRatio : " + endC + "seg_length : " + str(seg_length) + endC)
        print(cyan + "AspectRatio : " + endC + "buffer_size : " + str(buffer_size) + endC)
        print(cyan + "AspectRatio : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "AspectRatio : " + endC + "project_encoding : " + str(project_encoding) + endC)
        print(cyan + "AspectRatio : " + endC + "server_postgis : " + str(server_postgis) + endC)
        print(cyan + "AspectRatio : " + endC + "port_number : " + str(port_number) + endC)
        print(cyan + "AspectRatio : " + endC + "user_postgis : " + str(user_postgis) + endC)
        print(cyan + "AspectRatio : " + endC + "password_postgis : " + str(password_postgis) + endC)
        print(cyan + "AspectRatio : " + endC + "database_postgis : " + str(database_postgis) + endC)
        print(cyan + "AspectRatio : " + endC + "schema_postgis : " + str(schema_postgis) + endC)
        print(cyan + "AspectRatio : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "AspectRatio : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "AspectRatio : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "AspectRatio : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "AspectRatio : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "AspectRatio : " + endC + "debug : " + str(debug) + endC)

    if not os.path.exists(os.path.dirname(grid_output)):
        os.makedirs(os.path.dirname(grid_output))

    aspectRatio(grid_input, grid_output, roads_input, built_input, seg_dist, seg_length, buffer_size, epsg, project_encoding, server_postgis, port_number, user_postgis, password_postgis, database_postgis, schema_postgis, path_time_log, format_vector, extension_vector, save_results_intermediate, overwrite)

if __name__ == '__main__':
    main(gui=False)

