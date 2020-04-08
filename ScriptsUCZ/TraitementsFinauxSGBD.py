#!/usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerSO/DALETT/SCGSI  All rights reserved.                                                                            #
#############################################################################################################################################

from __future__ import print_function
import os
from Lib_log import timeLine
from Lib_postgis import executeQuery,openConnection,closeConnection,createDatabase,createSchema,importShape,exportShape
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 3

############################################################################################################################################################################################################
######################################################################## Définition des seuils pour l'attribution des classes d'UCZ ########################################################################
############################################################################################################################################################################################################

def choixSeuilsUCZ(ucz_method, dbms_choice):

        ### Définition de la variable 'table UCZ' dans la base de données ###

    if dbms_choice == "SpatiaLite":
        ucz_table = "UCZ"
    else:
        ucz_table = ucz_method.lower() + ".ucz"

        ### Définition des seuils suivant la méthode de calcul des UCZ ###

    if ucz_method == "Combinaison_sans_rugosite" or ucz_method == "Combinaison_avec_rugosite":
        query_ucz = """
                UPDATE %s SET UCZ = 0;
                """ % (ucz_table) # Mise à jour des mailles à 0 pour les méthodes combinatoires

        if ucz_method == "Combinaison_sans_rugosite":
            query_ucz += """
                UPDATE %s SET UCZ = 7 WHERE UCZ = 0 AND SI < 10 AND RA >= 0.05;
                UPDATE %s SET UCZ = 6 WHERE UCZ = 0 AND SI < 40 AND RA >= 0.1 AND RA < 0.5;
                UPDATE %s SET UCZ = 5 WHERE UCZ = 0 AND SI >= 35 AND SI < 65 AND RA >= 0.2 AND RA < 0.6;
                UPDATE %s SET UCZ = 4 WHERE UCZ = 0 AND SI >= 70 AND SI < 95 AND RA >= 0.05 AND RA < 0.2;
                UPDATE %s SET UCZ = 3 WHERE UCZ = 0 AND SI >= 70 AND SI < 85 AND RA >= 0.5 AND RA < 1.5;
                UPDATE %s SET UCZ = 2 WHERE UCZ = 0 AND SI >= 85 AND RA >= 1 AND RA < 2.5;
                UPDATE %s SET UCZ = 1 WHERE UCZ = 0 AND SI >= 90 AND RA >= 2;
                """ % (ucz_table, ucz_table, ucz_table, ucz_table, ucz_table, ucz_table, ucz_table) # 1ère passe (seuils bruts de Oke) pour la méthode combinatoire sans indicateur de rugosité

        else:
            query_ucz += """
                UPDATE %s SET UCZ = 7 WHERE UCZ = 0 AND SI < 10 AND RA >= 0.05 AND Rug = 4;
                UPDATE %s SET UCZ = 6 WHERE UCZ = 0 AND SI < 40 AND RA >= 0.1 AND RA < 0.5 AND Rug = 5;
                UPDATE %s SET UCZ = 5 WHERE UCZ = 0 AND SI >= 35 AND SI < 65 AND RA >= 0.2 AND RA < 0.6 AND Rug = 6;
                UPDATE %s SET UCZ = 4 WHERE UCZ = 0 AND SI >= 70 AND SI < 95 AND RA >= 0.05 AND RA < 0.2 AND Rug = 5;
                UPDATE %s SET UCZ = 3 WHERE UCZ = 0 AND SI >= 70 AND SI < 85 AND RA >= 0.5 AND RA < 1.5 AND Rug = 7;
                UPDATE %s SET UCZ = 2 WHERE UCZ = 0 AND SI >= 85 AND RA >= 1 AND RA < 2.5 AND Rug = 7;
                UPDATE %s SET UCZ = 1 WHERE UCZ = 0 AND SI >= 90 AND RA >= 2 AND Rug = 8;
                """ % (ucz_table, ucz_table, ucz_table, ucz_table, ucz_table, ucz_table, ucz_table) # 1ère passe (seuils bruts de Oke) pour la méthode combinatoire avec indicateur de rugosité

        query_ucz += """
                UPDATE %s SET UCZ = 7 WHERE UCZ = 0 AND SI < 15 AND RA < 0.2;
                UPDATE %s SET UCZ = 6 WHERE UCZ = 0 AND SI >= 15 AND SI < 30 AND RA < 0.6;
                UPDATE %s SET UCZ = 5 WHERE UCZ = 0 AND SI >= 30 AND SI < 60 AND RA < 0.6;
                UPDATE %s SET UCZ = 4 WHERE UCZ = 0 AND SI >= 60 AND RA < 0.2;
                UPDATE %s SET UCZ = 3 WHERE UCZ = 0 AND SI >= 60 AND SI < 75 AND RA >= 0.2 AND RA < 2;
                UPDATE %s SET UCZ = 2 WHERE UCZ = 0 AND SI >= 75 AND RA >= 0.6;
                UPDATE %s SET UCZ = 1 WHERE UCZ = 0 AND SI >= 80 AND RA >= 1.5;
                """ % (ucz_table, ucz_table, ucz_table, ucz_table, ucz_table, ucz_table, ucz_table) # 2nde passe (seuils retravaillés) pour les méthodes combinatoires

    else:
        query_ucz = """
                UPDATE %s SET UCZ = 7;
                UPDATE %s SET UCZ = 6 WHERE UCZ = 7 AND SI >= 10 AND SI < 35;
                UPDATE %s SET UCZ = 5 WHERE UCZ = 7 AND SI >= 35 AND SI < 65;
                UPDATE %s SET UCZ = 4 WHERE UCZ = 7 AND SI >= 65;
                UPDATE %s SET UCZ = 3 WHERE UCZ = 4 AND RA >= 0.5 AND RA < 1.5;
                UPDATE %s SET UCZ = 2 WHERE UCZ = 4 AND RA >= 1.5 AND RA < 2.5;
                UPDATE %s SET UCZ = 1 WHERE UCZ = 4 AND RA >= 2.5;
                """ % (ucz_table, ucz_table, ucz_table, ucz_table, ucz_table, ucz_table, ucz_table) # Traitements (avec pourcentage de surfaces imperméables et rapport d'aspect) pour les méthodes hiérarchiques

        if ucz_method == "Hierarchie_avec_rugosite":
            query_ucz += """
                UPDATE %s SET UCZ = 5 WHERE UCZ = 6 AND Rug = 6;
                UPDATE %s SET UCZ = 6 WHERE UCZ = 5 AND Rug = 5;
                """ % (ucz_table, ucz_table) # Post-traitements (avec rugosité, sur classes 5 et 6) pour la méthode hiérarchique avec indicateur de rugosité

    return query_ucz # Récupération de la requête pour l'intégrer dans les traitements suivants

####################################################################################################################################################################################
######################################################################## Traitements finaux sous SpatiaLite ########################################################################
####################################################################################################################################################################################

    ###############################################################
    ### Fin des calculs des indicateurs, à partir de SpatiaLite ###
    ###############################################################

def traitementsSpatiaLite(urbanatlas_input, ucz_output, emprise_file, mask_file, enter_with_mask, image_file, mnh_file, built_files_list, hydrography_file, roads_files_list, rpg_file, indicators_method, ucz_method, dbms_choice, threshold_ndvi, threshold_ndvi_water, threshold_ndwi2, threshold_bi_bottom, threshold_bi_top, path_time_log, temp_directory, extension_vector):

    print(bold + yellow + "Début de l'étape finale de calcul des indicateurs." + endC)
    step = "    Début de l'étape finale de calcul des indicateurs : "
    timeLine(path_time_log,step)

    database = temp_directory + os.sep + "dbSpatiaLite.sqlite" # Base de données SpatiaLite
    grid_ready_cleaned = temp_directory + os.sep + os.path.splitext(os.path.basename(urbanatlas_input))[0] + "_cut_cleaned" # Suppression extension du fichier shape maillage
    built_shape = temp_directory + os.sep + "bati" # Suppression extension du fichier shape bâti

    grid_codage = "ISO-8859-1" # Encodage du fichier shape de maillage. Par défaut : ISO-8859-1 (semble être un compromis entre UTF-8 [testé pour UrbanAtlas] et CP1252 [testé pour IRIS]).
    if indicators_method == "Resultats_classif":
        built_codage = "UTF-8" # Encodage du fichier shape de bâti issu du traitement de la classif supervisée. Par défaut : UTF-8
        built_height = "(mean/100)" # Nom du champ du fichier shape de bâti issu du traitement de la classif supervisée contenant l'information de hauteur. Par défaut : mean ('/100' ajouté pour retrouver une hauteur en mètres dans les calculs)
    else:
        built_codage = "CP1252" # Encodage du fichier shape de bâti issu de la BD TOPO. Par défaut : CP1252
        built_height = "HAUTEUR" # Nom du champ du fichier shape de bâti issu de la BD TOPO contenant l'information de hauteur. Par défaut : HAUTEUR

    ### Mise en place de la base de données SpatiaLite et fin des calculs des indicateurs ###

    print(bold + cyan + "    Création de la base de données et import des données maillage et bâti (cette étape peut être longue suivant le nombre de données à importer) :" + endC)
    os.system("spatialite_tool -i -shp %s -d %s -t maille -c %s -s 2154 -g geometry --type POLYGON" % (grid_ready_cleaned, database, grid_codage)) # Import du shape de maillage dans la base de données (qui est créée en même temps)
    os.system("spatialite_tool -i -shp %s -d %s -t bati -c %s -s 2154 -g geometry --type POLYGON" % (built_shape, database, built_codage)) # Import du shape de bâti dans la base de données

    print(bold + cyan + "    Calcul de la surface de façade de chaque bâtiment, en préparation de la fin du calcul du rapport d'aspect :" + endC)
    query = """ALTER TABLE bati ADD perimeter NUMERIC(10,2);
    UPDATE bati SET perimeter = st_perimeter(geometry);
    ALTER TABLE bati ADD surf_fac NUMERIC(10,2);
    UPDATE bati SET surf_fac = %s * perimeter;""" % (built_height)
    os.system("spatialite %s '%s'" % (database, query))

    print(bold + cyan + "    Création d'une nouvelle table ne contenant que les mailles intersectant le bâti (cette étape peut être longue suivant le nombre de données dans les tables importées) :" + endC)
    query = """CREATE TABLE temp AS
        SELECT M.ID AS ID, M.Imperm AS SI, M.S_NonBati AS surf_nonba, sum(B.surf_fac) AS surf_fac, (M.mean / 100) AS z0, M.geometry AS geometry
        FROM bati AS B, maille AS M
        WHERE st_intersects(B.geometry, M.geometry)
        GROUP BY M.ID;"""
    os.system("spatialite %s '%s'" % (database, query))

    print(bold + cyan + "    Fin des calculs de l'indicateur de rapport d'aspect :" + endC)
    query = """ALTER TABLE temp ADD RA NUMERIC(10,2);
    UPDATE temp SET RA = (0.5 * (surf_fac / (surf_nonba + 0.0001)));"""
    os.system("spatialite %s '%s'" % (database, query))

    print(bold + cyan + "    Fin des calculs de l'indicateur de classe de rugosité :" + endC)
    query = """ALTER TABLE temp ADD Rug INTEGER;
    UPDATE temp SET Rug = 1 WHERE z0 < 0.005;
    UPDATE temp SET Rug = 2 WHERE z0 >= 0.005 AND z0 < 0.03;
    UPDATE temp SET Rug = 3 WHERE z0 >= 0.03 AND z0 < 0.1;
    UPDATE temp SET Rug = 4 WHERE z0 >= 0.1 AND z0 < 0.25;
    UPDATE temp SET Rug = 5 WHERE z0 >= 0.25 AND z0 < 0.5;
    UPDATE temp SET Rug = 6 WHERE z0 >= 0.5 AND z0 < 1;
    UPDATE temp SET Rug = 7 WHERE z0 >= 1 AND z0 < 2;
    UPDATE temp SET Rug = 8 WHERE z0 >= 2;"""
    os.system("spatialite %s '%s'" % (database, query))

    print(bold + cyan + "    Création d'une nouvelle table complémentaire de la précédente, avec les mailles n'intersectant pas le bâti :" + endC)
    query = """CREATE TABLE temp_bis AS
        SELECT DISTINCT ID, Imperm AS SI, geometry
        FROM maille
        WHERE ID NOT IN
            (SELECT DISTINCT ID
            FROM temp);"""
    os.system("spatialite %s '%s'" % (database, query))

    print(bold + cyan + "    Ajout et MAJ des champs 'rapport d'aspect' et 'classe de rugosité' :" + endC)
    query = """ALTER TABLE temp_bis ADD RA NUMERIC(10,2);
    UPDATE temp_bis SET RA = 0;
    ALTER TABLE temp_bis ADD Rug INTEGER;
    UPDATE temp_bis SET Rug = 1;"""
    os.system("spatialite %s '%s'" % (database, query))

    step = "    Fin de l'étape finale de calcul des indicateurs : "
    timeLine(path_time_log,step)
    print(bold + yellow + "Fin de l'étape finale de calcul des indicateurs." + endC)
    print("\n")

    ##########################################################################################
    ### Étape finale de cartographie en Zones Climatiques Urbaines, à partir de SpatiaLite ###
    ##########################################################################################

    print(bold + yellow + "Début de l'étape finale de cartographie en Zones Climatiques Urbaines." + endC)
    step = "    Début de l'étape finale de cartographie en Zones Climatiques Urbaines : "
    timeLine(path_time_log,step)

    carto_temp = temp_directory + os.sep + "UCZ_" + ucz_method

    ### Tous les indicateurs sont calculés dans la base de données : étape finale d'attribution d'une classe d'UCZ à chaque polygone du maillage ###

    print(bold + cyan + "    Création d'une nouvelle table dans laquelle seront attribuées les classes d'UCZ :" + endC)
    query = """DROP TABLE IF EXISTS UCZ;
    CREATE TABLE UCZ AS
        SELECT ID, SI, RA, Rug, geometry
        FROM temp
        UNION
        SELECT ID, SI, RA, Rug, geometry
        FROM temp_bis;
    ALTER TABLE UCZ ADD UCZ INTEGER;"""
    os.system("spatialite %s '%s'" % (database, query))

    print(bold + cyan + "    Exécution des requêtes SQL d'attribution des classes d'UCZ :" + endC)
    query_ucz = choixSeuilsUCZ(ucz_method, 'SpatiaLite')
    os.system("spatialite %s '%s'" % (database, query_ucz))

    print(bold + cyan + "    Export de la table 'UCZ' en fichier shape '%s' :" % (ucz_output) + endC)
    os.system("spatialite_tool -e -shp %s -d %s -t UCZ -g geometry -c UTF-8 --type POLYGON" % (carto_temp, database))
    os.system("ogr2ogr -append -a_srs 'EPSG:2154' %s %s%s" % (ucz_output, carto_temp, extension_vector))

    step = "    Fin de l'étape finale de cartographie en Zones Climatiques Urbaines : "
    timeLine(path_time_log,step)
    print(bold + yellow + "Fin de l'étape finale de cartographie en Zones Climatiques Urbaines." + endC)
    print("\n")

    return

#################################################################################################################################################################################
######################################################################## Traitements finaux sous PostGIS ########################################################################
#################################################################################################################################################################################

def traitementsPostGIS(urbanatlas_input, ucz_output, emprise_file, mask_file, enter_with_mask, image_file, mnh_file, built_files_list, hydrography_file, roads_files_list, rpg_file, indicators_method, ucz_method, dbms_choice, threshold_ndvi, threshold_ndvi_water, threshold_ndwi2, threshold_bi_bottom, threshold_bi_top, path_time_log, temp_directory):

    ############################################################
    ### Fin des calculs des indicateurs, à partir de PostGIS ###
    ############################################################

    print(bold + yellow + "Début de l'étape finale de calcul des indicateurs." + endC)
    step = "    Début de l'étape finale de calcul des indicateurs : "
    timeLine(path_time_log,step)

    database = os.path.splitext(os.path.basename(ucz_output))[0].lower() # Base de données PostGIS
    grid_ready_cleaned = temp_directory + os.sep + os.path.splitext(os.path.basename(urbanatlas_input))[0] + "_cut_cleaned.shp" # Fichier shape maillage
    built_shape = temp_directory + os.sep + "bati.shp" # Fichier shape bâti
    grid_table = ucz_method.lower() + ".maille" # Table PostGIS pour le maillage
    built_table = ucz_method.lower() + ".bati" # Table PostGIS pour le bâti

    grid_codage = "latin1" # Encodage du fichier shape de maillage. Par défaut : latin1.
    if indicators_method == "Resultats_classif":
        built_codage = "utf-8" # Encodage du fichier shape de bâti issu du traitement de la classif supervisée. Par défaut : utf-8
        built_height = "(mean/100)" # Nom du champ du fichier shape de bâti issu du traitement de la classif supervisée contenant l'information de hauteur. Par défaut : mean ('/100' ajouté pour retrouver une hauteur en mètres dans les calculs)
    else:
        built_codage = "latin1" # Encodage du fichier shape de bâti issu de la BD TOPO. Par défaut : latin1
        built_height = "hauteur" # Nom du champ du fichier shape de bâti issu de la BD TOPO contenant l'information de hauteur. Par défaut : hauteur

    ### Mise en place de la base de données PostGIS et fin des calculs des indicateurs ###

    createDatabase(database, user_name='postgres', password='postgres', ip_host='localhost', num_port='5432') # Création de la base de données si elle n'existe pas

    connection = openConnection(database, user_name='postgres', password='postgres', ip_host='localhost', num_port='5432', schema_name='')
    createSchema(connection, ucz_method.lower()) # Création du schéma s'il n'existe pas
    closeConnection(connection)

    print(bold + cyan + "    Import du fichier shape de maillage :" + endC)
    grid_table = importShape(database, grid_ready_cleaned, grid_table, user_name='postgres', password='postgres', ip_host='localhost', num_port='5432', schema_name=ucz_method.lower(), epsg='2154', codage=grid_codage)
    print("\n")
    print(bold + cyan + "    Import du fichier shape du bâti :" + endC)
    built_table = importShape(database, built_shape, built_table, user_name='postgres', password='postgres', ip_host='localhost', num_port='5432', schema_name=ucz_method.lower(), epsg='2154', codage=built_codage)
    print("\n")

    connection = openConnection(database, user_name='postgres', password='postgres', ip_host='localhost', num_port='5432', schema_name=ucz_method.lower()) # Connection à la base de données PostGIS

    # Calcul du périmètre et de la surface de façades de chaque bâtiment
    print(bold + cyan + "    Calcul du périmètre et de la surface de façades de chaque bâtiment :" + endC)
    query = """
        ALTER TABLE %s.bati DROP IF EXISTS perimeter;
        ALTER TABLE %s.bati ADD perimeter NUMERIC(10,2);
        UPDATE %s.bati SET perimeter = st_perimeter(geom);
        ALTER TABLE %s.bati DROP IF EXISTS surf_fac;
        ALTER TABLE %s.bati ADD surf_fac NUMERIC(10,2);
        UPDATE %s.bati SET surf_fac = %s * perimeter;
        """ % (ucz_method.lower(), ucz_method.lower(), ucz_method.lower(), ucz_method.lower(), ucz_method.lower(), ucz_method.lower(), built_height)
    print(query + "\n")
    executeQuery(connection, query)

    # Calcul de la somme de surface de façades des bâtiments par maille
    print(bold + cyan + "    Calcul de la somme de surface de façades des bâtiments par maille :" + endC)
    query = """
        DROP TABLE IF EXISTS %s.temp0;
        CREATE TABLE %s.temp0 AS
            SELECT m.ID AS ID, sum(b.surf_fac) AS surf_fac
            FROM %s.bati AS b, %s.maille AS m
            WHERE st_intersects(b.geom, m.geom)
            GROUP BY m.ID;
        """ % (ucz_method.lower(), ucz_method.lower(), ucz_method.lower(), ucz_method.lower())
    print(query + "\n")
    executeQuery(connection, query)

    # Création d'une nouvelle table avec seulement les mailles qui intersectent du bâti
    print(bold + cyan + "    Création d'une nouvelle table avec seulement les mailles qui intersectent du bâti :" + endC)
    query = """
        DROP TABLE IF EXISTS %s.temp;
        CREATE TABLE %s.temp AS
            SELECT m.ID AS ID, m.imperm AS SI, m.s_nonbati AS surf_nonba, t.surf_fac AS surf_fac, (m.mean / 100) AS z0, m.geom AS geom
            FROM %s.maille AS m, %s.temp0 AS t
            WHERE t.ID = m.ID;
        """ % (ucz_method.lower(), ucz_method.lower(), ucz_method.lower(), ucz_method.lower())
    print(query + "\n")
    executeQuery(connection, query)

    # Fin du calcul du rapport d'aspect
    print(bold + cyan + "    Fin du calcul du rapport d'aspect :" + endC)
    query = """
        ALTER TABLE %s.temp DROP IF EXISTS RA;
        ALTER TABLE %s.temp ADD RA NUMERIC(10,2);
        UPDATE %s.temp SET RA = (0.5 * (surf_fac / (surf_nonba + 0.0001)));
        """ % (ucz_method.lower(), ucz_method.lower(), ucz_method.lower())
    print(query + "\n")
    executeQuery(connection, query)

    # Fin du calcul de la classe de rugosité
    print(bold + cyan + "    Fin du calcul de la classe de rugosité :" + endC)
    query = """
        ALTER TABLE %s.temp DROP IF EXISTS Rug;
        ALTER TABLE %s.temp ADD Rug INTEGER;
        UPDATE %s.temp SET Rug = 1 WHERE z0 < 0.005;
        UPDATE %s.temp SET Rug = 2 WHERE z0 >= 0.005 AND z0 < 0.03;
        UPDATE %s.temp SET Rug = 3 WHERE z0 >= 0.03 AND z0 < 0.1;
        UPDATE %s.temp SET Rug = 4 WHERE z0 >= 0.1 AND z0 < 0.25;
        UPDATE %s.temp SET Rug = 5 WHERE z0 >= 0.25 AND z0 < 0.5;
        UPDATE %s.temp SET Rug = 6 WHERE z0 >= 0.5 AND z0 < 1;
        UPDATE %s.temp SET Rug = 7 WHERE z0 >= 1 AND z0 < 2;
        UPDATE %s.temp SET Rug = 8 WHERE z0 >= 2;
        """ % (ucz_method.lower(), ucz_method.lower(), ucz_method.lower(), ucz_method.lower(), ucz_method.lower(), ucz_method.lower(), ucz_method.lower(), ucz_method.lower(), ucz_method.lower(), ucz_method.lower())
    print(query + "\n")
    executeQuery(connection, query)

    # Création d'une nouvelle table avec les mailles qui n'intersectent pas de bâtiment, complémentaire de la précédente
    print(bold + cyan + "    Création d'une nouvelle table avec les mailles qui n'intersectent pas de bâtiment, complémentaire de la précédente :" + endC)
    query = """
        DROP TABLE IF EXISTS %s.temp_bis;
        CREATE TABLE %s.temp_bis AS
            SELECT DISTINCT ID, imperm AS SI, geom
            FROM %s.maille
            WHERE ID NOT IN
                (SELECT DISTINCT ID
                FROM %s.temp);
        """ % (ucz_method.lower(), ucz_method.lower(), ucz_method.lower(), ucz_method.lower())
    print(query + "\n")
    executeQuery(connection, query)

    # Ajout + MAJ par défaut des champs 'rapport d'aspect' (à 0) et 'classe de rugosité' (à 1) dans cette nouvelle table
    print(bold + cyan + "    Ajout (et MAJ par défaut) des champs 'rapport d'aspect' (à 0) et 'classe de rugosité' (à 1) dans cette nouvelle table :" + endC)
    query = """
        ALTER TABLE %s.temp_bis DROP IF EXISTS RA;
        ALTER TABLE %s.temp_bis ADD RA NUMERIC(10,2);
        UPDATE %s.temp_bis SET RA = 0;
        ALTER TABLE %s.temp_bis DROP IF EXISTS Rug;
        ALTER TABLE %s.temp_bis ADD Rug INTEGER;
        UPDATE %s.temp_bis SET Rug = 1;
        """ % (ucz_method.lower(), ucz_method.lower(), ucz_method.lower(), ucz_method.lower(), ucz_method.lower(), ucz_method.lower())
    print(query + "\n")
    executeQuery(connection, query)

    closeConnection(connection) # Fermeture de la connexion à la base de données PostGIS

    step = "    Fin de l'étape finale de calcul des indicateurs : "
    timeLine(path_time_log,step)
    print(bold + yellow + "Fin de l'étape finale de calcul des indicateurs." + endC)
    print("\n")

    #######################################################################################
    ### Étape finale de cartographie en Zones Climatiques Urbaines, à partir de PostGIS ###
    #######################################################################################

    print(bold + yellow + "Début de l'étape finale de cartographie en Zones Climatiques Urbaines." + endC)
    step = "    Début de l'étape finale de cartographie en Zones Climatiques Urbaines : "
    timeLine(path_time_log,step)

    ucz_table = ucz_method.lower() + ".ucz" # Table PostGIS

    ### Tous les indicateurs sont calculés dans la base de données : étape finale d'attribution d'une classe d'UCZ à chaque polygone du maillage ###

    connection = openConnection(database, user_name='postgres', password='postgres', ip_host='localhost', num_port='5432', schema_name=ucz_method.lower()) # Connection à la base de données PostGIS

    # Création de la table finale où seront attribuées les classes d'UCZ
    print(bold + cyan + "    Création de la table finale où seront attribuées les classes d'UCZ :" + endC)
    query = """
        DROP TABLE IF EXISTS %s.ucz;
        CREATE TABLE %s.ucz AS
            SELECT ID, SI, RA, Rug, geom
            FROM %s.temp
            UNION
            SELECT ID, SI, RA, Rug, geom
            FROM %s.temp_bis;
        ALTER TABLE %s.ucz DROP IF EXISTS UCZ;
        ALTER TABLE %s.ucz ADD UCZ INTEGER;
        ALTER TABLE  %s.ucz ALTER COLUMN ID TYPE INTEGER;
        """ % (ucz_method.lower(), ucz_method.lower(), ucz_method.lower(), ucz_method.lower(), ucz_method.lower(), ucz_method.lower(), ucz_method.lower())
    print(query + "\n")
    executeQuery(connection, query)

    # Exécution des requêtes SQL d'attribution des classes d'UCZ
    print(bold + cyan + "    Exécution des requêtes SQL d'attribution des classes d'UCZ :" + endC)
    query_ucz = choixSeuilsUCZ(ucz_method, 'PostGIS')
    print(query_ucz + "\n")
    executeQuery(connection, query_ucz)

    closeConnection(connection) # Fermeture de la connexion à la base de données PostGIS

    # Export de la table UCZ en fichier shape
    print(bold + cyan + "    Export de la table 'UCZ' en fichier shape '%s' :" % (ucz_output) + endC)
    exportShape(database, ucz_output, ucz_table, user_name='postgres', password='postgres', ip_host='localhost', num_port='5432', schema_name=ucz_method.lower())

    step = "    Fin de l'étape finale de cartographie en Zones Climatiques Urbaines : "
    timeLine(path_time_log,step)
    print(bold + yellow + "Fin de l'étape finale de cartographie en Zones Climatiques Urbaines." + endC)
    print("\n")

    return

