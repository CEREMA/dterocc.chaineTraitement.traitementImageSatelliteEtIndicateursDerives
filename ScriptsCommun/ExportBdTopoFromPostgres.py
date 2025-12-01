#!/usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT QUI EXPORTE LES DONNEES BD TOPO MONTEES DANS UNE BASE POSTGRESQL/POSTGIS                                                           #
#                                                                                                                                           #
#############################################################################################################################################
'''
Nom de l'objet : ExportBdTopoFromPostgres.py
Description :
    Objectif : exporter les données BD TOPO montées en base Postgres, à partir d'un fichier d'emprise
    Remarques :
        - les valeurs possibles pour le paramètre "year" sont : 2020 / 2021 / 2022 / 2023 / 2024 (de nouveaux millésimes pourront être ajoutés à la demande, mais uniquement des versions 3.X, soit depuis 2019)
        - les valeurs possibles pour le paramètre "zone" sont : "FXX" / "GLP" / "GUF" / "MTQ" / "MYT" / "REU" / "SPM" / "BLM" / "MAF"
            correspondant respectivement à : France Métropolitaine (EPSG 2154) / Guadeloupe (EPSG 5490) / Guyane (EPSG 2972) / Martinique (EPSG 5490) / Mayotte (EPSG 4471) / La Réunion (EPSG 2975) / Saint-Pierre-et-Miquelon (EPSG 4467) / Saint-Barthélemy (EPSG 5490) / Saint-Martin (EPSG 5490)
        - ne gère que les formats SHP et GPKG (fichier unique multi-couches) en sortie (formats de référence IGN) :
            * valeurs possibles pour le paramètre "format_vector" : "ESRI Shapefile" / "GPKG"
            * valeurs possibles pour le paramètre "extension_vector" : ".shp" / ".gpkg"
    Limites :
        - peut ne pas fonctionner correctement pour des versions de la BD TOPO autres que v3 (surtout en export "ESRI Shapefile") --> lié au paramètre "input_metadata"

-----------------
Outils utilisés :
 - PostgreSQL/PostGIS

------------------------------
Historique des modifications :
 - 29/02/2024 : création
 - 02/05/2024 : ajout des territoires de Saint-Barthélemy et Saint-Martin
 - 04/07/2024 : correspondance automatique des champs SQL -> SHP, à partir d'un fichier métadonnées de l'IGN (paramètre "input_metadata")
 - 16/12/2024 : ajout d'un paramètre "buffer_size" pour exporter les entités dans ce périmètre élargi et non dans le périmètre strict de "input_vector" (utile pour certains cas de figure)
 - 31/01/2025 : ajout de l'export d'un projet carto QGIS de référence de l'IGN pour visualisation des données (uniquement dans le cas d'un export BD TOPO en SHP -> chemins relatifs)
 - 12/02/2025 : ajout d'un paramètre "classes" pour choisir les classes exportés
 - 24/07/2025 : ajout d'un paramètre "year" pour le choix du millésime BD TOPO (et donc, suppression du paramètre "postgis_database_name" qui est géré dans le script) + suppression export projet carto QGIS (MAJ 31/01/2025)
 - 29/10/2025 : export direct des entités intersectées, sans créer de tables temporaires (évite de remplir la BDD en cas de plantage) + gestion des champs SHP en majuscules (référence IGN) + ajout des millésimes 2020 et 2021
 - 25/11/2025 : ajout de la possibilité d'export du dernier millésime depuis DataCart (paramètre -datacart)
-----------------------
A réfléchir / A faire :
 -
'''

# Import des bibliothèques Python
from __future__ import print_function
import os, argparse
from random import randint
from osgeo import ogr
from Lib_display import *
from Lib_log import timeLine
from Lib_text import readTextFile, readTextFileBySeparator, regExReplace
from Lib_file import removeVectorFile
from Lib_vector import getGeomPolygons, getProjection, getAttributeNameList, renameFieldsVector
from Lib_postgis import openConnection, executeQuery, getData, getAllTables, getAllColumns, closeConnection, exportVectorByOgr2ogr

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 3

########################################################################
# FONCTION exportBdTopoFromPostgres()                                  #
########################################################################
def exportBdTopoFromPostgres(input_vector, output_directory, buffer_size=1000, year=2022, zone="FXX", classes=[], input_metadata="/mnt/Data/10_Agents_travaux_en_cours/Benjamin/BD_TOPO_Classes.csv", format_vector="ESRI Shapefile", extension_vector=".shp", postgis_ip_host="172.22.130.99", postgis_num_port=5435, postgis_user_name="postgres", postgis_password="postgres", path_time_log=""):
    '''
    # ROLE :
    #     Exporter les classes BD TOPO montées en base Postgres, sur serveur interne OSECC, à partir d'un fichier d'emprise
    #
    # ENTREES DE LA FONCTION :
    #     input_vector : fichier vecteur d'emprise d'étude en entrée
    #     output_directory : répertoire de sortie des fichiers vecteur
    #     buffer_size : taille du tampon (en m) appliqué pour la sélection des entités dans le vecteur d'emprise d'étude en entrée. Par défaut, 1000
    #     year : définition du millésime d'étude. Par défaut, 2022
    #     zone : définition du territoire d'étude. Par défaut, FXX
    #     classes : liste des classes précises de la BD TOPO désirées (exemple : ["batiment", "troncon_de_route", "troncon_de_voie_ferree", "equipement_de_transport", "troncon_hydrographique", "surface_hydrographique"]). Par défaut, toutes les classes
    #     input_metadata : fichier de métadonnées BD TOPO faisant la correspondance des noms de champs SQL-SHP
    #     format_vector : format des fichiers vecteur. Par défaut : ESRI Shapefile
    #     extension_vector : extension des fichiers vecteur. Par défaut : .shp
    #     postgis_ip_host : nom du serveur PostGIS. Par défaut : 172.22.130.99
    #     postgis_num_port : numéro de port du serveur PostGIS. Par défaut : 5435
    #     postgis_user_name : nom d'utilisateur PostGIS. Par défaut : postgres
    #     postgis_password : mot de passe de l'utilisateur PostGIS. Par défaut : postgres
    #     path_time_log : fichier log de sortie, par défaut vide (affichage console)
    #
    # SORTIES DE LA FONCTION :
    #     N.A.
    '''
    if debug >= 3:
        print(bold + green + "Exporter les classes BD TOPO montées en base Postgres, sur serveur interne OSECC, à partir d'un fichier d'emprise - Variables dans la fonction :" + endC)
        print(cyan + "    exportBdTopoFromPostgres() : " + endC + "input_vector : " + str(input_vector) + endC)
        print(cyan + "    exportBdTopoFromPostgres() : " + endC + "output_directory : " + str(output_directory) + endC)
        print(cyan + "    exportBdTopoFromPostgres() : " + endC + "buffer_size : " + str(buffer_size) + endC)
        print(cyan + "    exportBdTopoFromPostgres() : " + endC + "year : " + str(year) + endC)
        print(cyan + "    exportBdTopoFromPostgres() : " + endC + "zone : " + str(zone) + endC)
        print(cyan + "    exportBdTopoFromPostgres() : " + endC + "classes : " + str(classes) + endC)
        print(cyan + "    exportBdTopoFromPostgres() : " + endC + "input_metadata : " + str(input_metadata) + endC)
        print(cyan + "    exportBdTopoFromPostgres() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "    exportBdTopoFromPostgres() : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "    exportBdTopoFromPostgres() : " + endC + "postgis_ip_host : " + str(postgis_ip_host) + endC)
        print(cyan + "    exportBdTopoFromPostgres() : " + endC + "postgis_num_port : " + str(postgis_num_port) + endC)
        print(cyan + "    exportBdTopoFromPostgres() : " + endC + "postgis_user_name : " + str(postgis_user_name) + endC)
        print(cyan + "    exportBdTopoFromPostgres() : " + endC + "postgis_password : " + str(postgis_password) + endC)
        print(cyan + "    exportBdTopoFromPostgres() : " + endC + "path_time_log : " + str(path_time_log) + endC)

    # Définition des constantes
    ESRI_SHAPEFILE_DRIVER_NAME, GPKG_DRIVER_NAME = "ESRI Shapefile", "GPKG"
    PUBLIC_SCHEMA_NAME, BD_TOPO_ENCODING = "public", "UTF-8"
    SQL_GEOM_FIELD, SHP_GEOM_FIELD = "geometrie", "GEOM"
    AVAILABLE_YEAR_LIST = [2020, 2021, 2022, 2023, 2024]
    AVAILABLE_ZONE_LIST = ["FXX", "GLP", "MTQ", "GUF", "REU", "MYT", "SPM", "BLM", "MAF"]

    # Gestion des paramètres BD TOPO
    PG_DATABASE_NAME = "bdtopo_v33_20221215" if year == 2022 else "bdtopo_v33_20231215" if year == 2023 else "bdtopo_v34_20241215" if year == 2024 else "bdtopo_v30_20211215" if year == 2021 else "bdtopo_v30_20201215"
    PG_BD_TOPO_DICO = {"FXX":["fxx_lamb93",      2154],
                       "GLP":["glp_rgaf09utm20", 5490],
                       "GUF":["guf_utm22rgfg95", 2972],
                       "MTQ":["mtq_rgaf09utm20", 5490],
                       "MYT":["myt_rgm04utm38s", 4471],
                       "REU":["reu_rgr92utm40s", 2975],
                       "SPM":["spm_rgspm06u21",  4467],
                       "BLM":["sba_rgaf09utm20" if year in [2020, 2021, 2022] else "blm_rgaf09utm20", 5490],
                       "MAF":["sma_rgaf09utm20" if year in [2020, 2021, 2022] else "maf_rgaf09utm20", 5490]}
    CLASSE_THEME_DICO = {"adresse": "ADRESSES","adresse_ban":"ADRESSES","aerodrome":"TRANSPORT","arrondissement":"ADMINISTRATIF","arrondissement_municipal":"ADMINISTRATIF","bassin_versant_topographique":"HYDROGRAPHIE","batiment":"BATI","batiment_rnb_lien_bdtopo":"BATI","canalisation":"SERVICES_ET_ACTIVITES","cimetiere":"BATI","collectivite_territoriale":"ADMINISTRATIF","commune":"ADMINISTRATIF","commune_associee_ou_deleguee":"ADMINISTRATIF","condominium":"ADMINISTRATIF","construction_lineaire":"BATI","construction_ponctuelle":"BATI","construction_surfacique":"BATI","cours_d_eau":"HYDROGRAPHIE","departement":"ADMINISTRATIF","detail_hydrographique":"HYDROGRAPHIE","detail_orographique":"LIEUX_NOMMES","epci":"ADMINISTRATIF","equipement_de_transport":"TRANSPORT","erp":"SERVICES_ET_ACTIVITES","foret_publique":"ZONES_REGLEMENTEES","haie":"OCCUPATION_DU_SOL","itineraire_autre":"TRANSPORT","lien_adresse_vers_bdtopo":"ADRESSES","lieu_dit_non_habite":"LIEUX_NOMMES","ligne_electrique":"SERVICES_ET_ACTIVITES","ligne_orographique":"BATI","limite_terre_mer":"HYDROGRAPHIE","noeud_hydrographique":"HYDROGRAPHIE","non_communication":"TRANSPORT","parc_ou_reserve":"ZONES_REGLEMENTEES","piste_d_aerodrome":"TRANSPORT","plan_d_eau":"HYDROGRAPHIE","point_d_acces":"TRANSPORT","point_de_repere":"TRANSPORT","point_du_reseau":"TRANSPORT","poste_de_transformation":"SERVICES_ET_ACTIVITES","pylone":"BATI","region":"ADMINISTRATIF","reservoir":"BATI","route_numerotee_ou_nommee":"TRANSPORT","section_de_points_de_repere":"TRANSPORT","surface_hydrographique":"HYDROGRAPHIE","terrain_de_sport":"BATI","toponymie_bati":"BATI","toponymie_hydrographie":"HYDROGRAPHIE","toponymie_lieux_nommes":"LIEUX_NOMMES","toponymie_services_et_activites":"SERVICES_ET_ACTIVITES","toponymie_transport":"TRANSPORT","toponymie_zones_reglementees":"ZONES_REGLEMENTEES","transport_par_cable":"TRANSPORT","troncon_de_route":"TRANSPORT","troncon_de_voie_ferree":"TRANSPORT","troncon_hydrographique":"HYDROGRAPHIE","voie_ferree_nommee":"TRANSPORT","voie_nommee":"TRANSPORT","voie_nommee_beta":"TRANSPORT","zone_d_activite_ou_d_interet":"SERVICES_ET_ACTIVITES","zone_d_estran":"OCCUPATION_DU_SOL","zone_d_habitation":"LIEUX_NOMMES","zone_de_vegetation":"OCCUPATION_DU_SOL"}
    if year in [2020, 2021, 2024]:
        CLASSE_THEME_DICO.update({"voie_nommee":"ADRESSES"})

    # Définition des variables
    postgis_schema_name = PG_BD_TOPO_DICO[zone][0]
    epsg = PG_BD_TOPO_DICO[zone][1]
    connection = openConnection(PG_DATABASE_NAME, user_name=postgis_user_name, password=postgis_password, ip_host=postgis_ip_host, num_port=postgis_num_port, schema_name=postgis_schema_name)
    available_classes_list = getAllTables(connection, postgis_schema_name, print_result=False)
    closeConnection(connection)

    ####################################################################

    if debug >= 2:
        print(cyan + "exportBdTopoFromPostgres() : " + bold + green + "DEBUT DES TRAITEMENTS" + endC)

    # Mise à jour du log
    starting_event = "exportBdTopoFromPostgres() : Début du traitement : "
    timeLine(path_time_log, starting_event)

    # Test existence du fichier vecteur d'entrée
    if not os.path.exists(input_vector):
        print(cyan + "exportBdTopoFromPostgres() : " + bold + red + "Error: Input vector file \"%s\" not exists!" % input_vector + endC, file=sys.stderr)
        exit(-1)

    # Définition du format du fichier vecteur d'emprise d'étude en entrée
    format_vector_list = [ogr.GetDriver(i).GetDescription() for i in range(ogr.GetDriverCount())]
    i = 0
    for input_format_vector in format_vector_list:
        driver = ogr.GetDriverByName(input_format_vector)
        data_source_input = driver.Open(input_vector, 0)
        if data_source_input is not None:
            data_source_input.Destroy()
            break
        i += 1
    input_format_vector = format_vector_list[i]

    # Test format vecteur de sortie
    if not format_vector in [ESRI_SHAPEFILE_DRIVER_NAME, GPKG_DRIVER_NAME]:
        print(cyan + "exportBdTopoFromPostgres() : " + bold + red + "Error: Vector format \"%s\" is not recognize (must be \"%s\" or \"%s\")!" % (format_vector, ESRI_SHAPEFILE_DRIVER_NAME, GPKG_DRIVER_NAME) + endC, file=sys.stderr)
        exit(-1)

    # Test millésime d'étude
    if not year in AVAILABLE_YEAR_LIST:
        print(cyan + "exportBdTopoFromPostgres() : " + bold + red + "Error: Year \"%s\" is not in the available year (%s)!" % (year, str(AVAILABLE_YEAR_LIST)) + endC, file=sys.stderr)
        exit(-1)

    # Test zone d'étude
    if not zone in AVAILABLE_ZONE_LIST:
        print(cyan + "exportBdTopoFromPostgres() : " + bold + red + "Error: Zone \"%s\" is not in the available zones (%s)!" % (zone, str(AVAILABLE_ZONE_LIST)) + endC, file=sys.stderr)
        exit(-1)

    # Test de conformité des classes sélectionnés
    if classes:
        bool_list = [classe in available_classes_list for classe in classes]
        if not all(bool_list):
            print(cyan + "exportBdTopoFromPostgres() : " + bold + red + "Error: Class %s are not availables!" % [x for x, m in zip(classes, bool_list) if not m] + endC, file=sys.stderr)
            exit(-1)
    else:
        classes = available_classes_list

    # Test concordance EPSG du fichier vecteur d'entrée et de la base Postgres
    epsg_input_vector, projection = getProjection(input_vector, format_vector=input_format_vector)
    if epsg != epsg_input_vector:
        print(cyan + "exportBdTopoFromPostgres() : " + bold + red + "Error: Input vector file EPSG (%s) is not corresponding to requested BD TOPO database EPSG (%s)!" % (epsg_input_vector, epsg) + endC, file=sys.stderr)
        exit(-1)

    # Récupération de l'emprise d'étude
    geometry_list = getGeomPolygons(input_vector, col=None, value=None, format_vector=input_format_vector)
    if len(geometry_list) == 0:
        print(cyan + "exportBdTopoFromPostgres() : " + bold + red + "Error: There are no geometry in the input vector file \"%s\"!" % input_vector + endC, file=sys.stderr)
        exit(-1)
    elif len(geometry_list) > 1:
        print(cyan + "exportBdTopoFromPostgres() : " + bold + red + "Error: There are more than one geometry in the input vector file \"%s\" (%s geometries)!" % (input_vector, len(geometry_list)) + endC, file=sys.stderr)
        exit(-1)
    else:
        geometry_roi = geometry_list[0].ExportToWkt()
        if buffer_size > 0:
            geometry_roi = geometry_list[0].Buffer(buffer_size).ExportToWkt()

    # Vérification de la compléxité de la géométrie
    temp_file = "n_vertices.txt"
    basename = os.path.basename(os.path.splitext(input_vector)[0]).lower()
    if buffer_size == 0:
        os.system("ogrinfo -q -dialect SQLite -sql 'SELECT SUM(ST_NPoints(geometry)) AS n_vertices FROM %s' %s > %s" % (basename, input_vector, temp_file))
    else:
        os.system("ogrinfo -q -dialect SQLite -sql 'SELECT SUM(ST_NPoints(ST_Buffer(geometry, %s))) AS n_vertices FROM %s' %s > %s" % (buffer_size, basename, input_vector, temp_file))
    n_vertices = int(readTextFile(temp_file).split(" ")[-1].split("\n")[0])
    os.remove(temp_file)
    if n_vertices >= 10000:
        print(cyan + "exportBdTopoFromPostgres() : " + bold + red + "Error: Input geometry is too complex (%s vertices)! Please simplify it (< 10000 vertices)." % n_vertices + endC, file=sys.stderr)
        exit(-1)

    # Récupération des métadonnées BD TOPO (correspondance des noms de champs SQL-SHP)
    if format_vector == ESRI_SHAPEFILE_DRIVER_NAME:
        if not os.path.exists(input_metadata):
            print(cyan + "exportBdTopoFromPostgres() : " + bold + red + "Error: Input metadata file \"%s\" not exists!" % input_metadata + endC, file=sys.stderr)
            exit(-1)
        else:
            metadata_bd_topo = readTextFileBySeparator(input_metadata, "#")

    ####################################################################
    if debug >= 2:
        print(cyan + "exportBdTopoFromPostgres() : " + bold + green + "Début des exports." + endC)

    # Boucle sur les classes à exporter
    idx = 1
    for bd_topo_classe in classes:
        bd_topo_theme = CLASSE_THEME_DICO[bd_topo_classe]
        if debug >= 3:
            print(cyan + "exportBdTopoFromPostgres() : " + bold + green + "Traitement de la classe \"%s\" (%s/%s)..." % (bd_topo_classe, str(idx), str(len(classes))) + endC)

        # Construction du nom du fichier de sortie
        if format_vector == GPKG_DRIVER_NAME:
            if not os.path.exists(output_directory):
                os.makedirs(output_directory)
            database_name_split, schema_name_split = PG_DATABASE_NAME.split("_"), postgis_schema_name.split("_")
            aoi_name = regExReplace(os.path.basename(os.path.splitext(input_vector)[0]), regex="[a-zA-Z0-9]", regex_replace="")
            bd_topo_version = "%s-%s" % (database_name_split[1][1], database_name_split[1][2])
            bd_topo_rig = schema_name_split[1]
            bd_topo_info = "%s-ED%s-%s-%s" % (aoi_name.upper(), database_name_split[2][:4], database_name_split[2][4:6], database_name_split[2][6:8])
            output_basename = "BDT_%s_%s_%s_%s" % (bd_topo_version, GPKG_DRIVER_NAME, bd_topo_rig.upper(), bd_topo_info)
            output_vector_file = output_directory + os.sep + output_basename.upper() + extension_vector
        else:
            output_theme_directory = output_directory + os.sep + bd_topo_theme
            if not os.path.exists(output_theme_directory):
                os.makedirs(output_theme_directory)
            output_vector_file = output_theme_directory + os.sep + bd_topo_classe.upper() + extension_vector
            removeVectorFile(output_vector_file, format_vector=format_vector)

        # Construction de la requête d'export
        select_query = "*"
        if format_vector == ESRI_SHAPEFILE_DRIVER_NAME:
            connection = openConnection(PG_DATABASE_NAME, user_name=postgis_user_name, password=postgis_password, ip_host=postgis_ip_host, num_port=postgis_num_port, schema_name=postgis_schema_name)
            columns_list = getAllColumns(connection, bd_topo_classe, print_result=False)
            closeConnection(connection)
            select_query = ""
            for text in metadata_bd_topo:
                if text[0] == bd_topo_classe and text[2] in columns_list:
                    select_query += "b.%s AS %s, " % (text[2], text[1])
            select_query += "b.%s AS %s" % (SQL_GEOM_FIELD, SHP_GEOM_FIELD)
        from_query = "%s.%s AS b" % (postgis_schema_name, bd_topo_classe)
        where_query = "ST_Intersects(b.%s, 'SRID=%s;%s')" % (SQL_GEOM_FIELD, str(epsg), geometry_roi)

        # Test de l'existence d'entités intersectant la ROI
        connection = openConnection(PG_DATABASE_NAME, user_name=postgis_user_name, password=postgis_password, ip_host=postgis_ip_host, num_port=postgis_num_port, schema_name=PUBLIC_SCHEMA_NAME)
        row_number = getData(connection, from_query, "COUNT(b.%s)" % SQL_GEOM_FIELD, condition=where_query)[0][0]
        closeConnection(connection)

        # Export des entités intersectant la ROI
        if row_number > 0:
            ogr2ogr_more_parameters = "-sql \"SELECT %s FROM %s WHERE %s\"" % (select_query, from_query, where_query)
            if format_vector == GPKG_DRIVER_NAME:
                ogr2ogr_more_parameters += " -nln %s -overwrite" % bd_topo_classe
            if format_vector == ESRI_SHAPEFILE_DRIVER_NAME:
                ogr2ogr_more_parameters += " -mapFieldType DateTime=String -lco ENCODING=%s" % BD_TOPO_ENCODING
            exportVectorByOgr2ogr(PG_DATABASE_NAME, output_vector_file, bd_topo_classe, user_name=postgis_user_name, password=postgis_password, ip_host=postgis_ip_host, num_port=postgis_num_port, schema_name=PUBLIC_SCHEMA_NAME, format_type=format_vector, ogr2ogr_more_parameters=ogr2ogr_more_parameters, print_cmd=False)
            if format_vector == ESRI_SHAPEFILE_DRIVER_NAME:
                attr_names_list = getAttributeNameList(output_vector_file, format_vector=ESRI_SHAPEFILE_DRIVER_NAME)
                new_attr_names_list = [attr_name.upper() for attr_name in attr_names_list]
                renameFieldsVector(output_vector_file, attr_names_list, new_attr_names_list, format_vector=ESRI_SHAPEFILE_DRIVER_NAME)
        else:
            print(cyan + "exportBdTopoFromPostgres() : " + bold + yellow + "L'emprise d'étude n'intersecte pas d'entités pour la classe \"%s\"." % bd_topo_classe + endC)

        idx += 1

    if debug >= 2:
        print(cyan + "exportBdTopoFromPostgres() : " + bold + green + "Fin des exports." + endC)

    ####################################################################

    # Mise à jour du log
    ending_event = "exportBdTopoFromPostgres() : Fin du traitement : "
    timeLine(path_time_log, ending_event)

    if debug >= 2:
        print(cyan + "exportBdTopoFromPostgres() : " + bold + green + "FIN DES TRAITEMENTS" + endC)

    return 0

########################################################################
# FONCTION exportBdTopoFromPostgresDatacart()                          #
########################################################################
def exportBdTopoFromPostgresDatacart(input_vector, output_directory, buffer_size=1000, zone="FXX", classes=[], input_metadata="/mnt/Data/10_Agents_travaux_en_cours/Benjamin/BD_TOPO_Classes.csv", format_vector="ESRI Shapefile", extension_vector=".shp", path_time_log=""):
    '''
    # ROLE :
    #     Exporter les classes BD TOPO montées en base Postgres, sur serveur DataCart (dernier millésime), à partir d'un fichier d'emprise
    #
    # ENTREES DE LA FONCTION :
    #     input_vector : fichier vecteur d'emprise d'étude en entrée
    #     output_directory : répertoire de sortie des fichiers vecteur
    #     buffer_size : taille du tampon (en m) appliqué pour la sélection des entités dans le vecteur d'emprise d'étude en entrée. Par défaut, 1000
    #     zone : définition du territoire d'étude. Par défaut, FXX
    #     classes : liste des classes précises de la BD TOPO désirées (exemple : ["batiment", "troncon_de_route", "troncon_de_voie_ferree", "equipement_de_transport", "troncon_hydrographique", "surface_hydrographique"]). Par défaut, toutes les classes
    #     input_metadata : fichier de métadonnées BD TOPO faisant la correspondance des noms de champs SQL-SHP
    #     format_vector : format des fichiers vecteur. Par défaut : ESRI Shapefile
    #     extension_vector : extension des fichiers vecteur. Par défaut : .shp
    #     path_time_log : fichier log de sortie, par défaut vide (affichage console)
    #
    # SORTIES DE LA FONCTION :
    #     N.A.
    '''
    if debug >= 3:
        print(bold + green + "Exporter les classes BD TOPO montées en base Postgres, sur serveur DataCart (dernier millésime), à partir d'un fichier d'emprise - Variables dans la fonction :" + endC)
        print(cyan + "    exportBdTopoFromPostgresDatacart() : " + endC + "input_vector : " + str(input_vector) + endC)
        print(cyan + "    exportBdTopoFromPostgresDatacart() : " + endC + "output_directory : " + str(output_directory) + endC)
        print(cyan + "    exportBdTopoFromPostgresDatacart() : " + endC + "buffer_size : " + str(buffer_size) + endC)
        print(cyan + "    exportBdTopoFromPostgresDatacart() : " + endC + "zone : " + str(zone) + endC)
        print(cyan + "    exportBdTopoFromPostgresDatacart() : " + endC + "classes : " + str(classes) + endC)
        print(cyan + "    exportBdTopoFromPostgresDatacart() : " + endC + "input_metadata : " + str(input_metadata) + endC)
        print(cyan + "    exportBdTopoFromPostgresDatacart() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "    exportBdTopoFromPostgresDatacart() : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "    exportBdTopoFromPostgresDatacart() : " + endC + "path_time_log : " + str(path_time_log) + endC)

    # Définition des constantes
    PG_IP_HOST = "172.20.220.19"
    PG_NUM_PORT = 5432
    PG_USER_NAME = "consultation"
    PG_PASSWORD = "consultation"
    PG_DATABASE_NAME = "r_datacart"
    PG_SCHEMA_NAME = "r_bdtopo"
    ESRI_SHAPEFILE_DRIVER_NAME, GPKG_DRIVER_NAME = "ESRI Shapefile", "GPKG"
    AVAILABLE_ZONE_LIST = ["FXX", "GLP", "MTQ", "GUF", "REU", "MYT", "SPM", "BLM", "MAF"]
    PUBLIC_SCHEMA_NAME, BD_TOPO_ENCODING = "public", "UTF-8"
    SQL_GEOM_FIELD, SHP_GEOM_FIELD, ID_CEREMA_FIELD = "geom", "GEOM", "id_cerema"
    BD_TOPO_TABLE_PREFIX, BD_TOPO_TABLE_SUFFIX,  = "n_", "_bdt_"
    BD_TOPO_VERSION, BD_TOPO_DATE = "3-5", "2025-06-15"

    # Gestion des paramètres BD TOPO
    PG_BD_TOPO_DICO = {"FXX":["000", 2154, "lamb93"],
                       "GLP":["971", 5490, "rgaf09utm20"],
                       "MTQ":["972", 5490, "utm22rgfg95"],
                       "GUF":["973", 2972, "rgaf09utm20"],
                       "REU":["974", 2975, "rgm04utm38s"],
                       "SPM":["975", 4467, "rgr92utm40s"],
                       "MYT":["976", 4471, "rgspm06u21"],
                       "BLM":["977", 5490, "rgaf09utm20"],
                       "MAF":["978", 5490, "rgaf09utm20"]}
    CLASSE_THEME_DICO = {"adresse_ban":"ADRESSES","aerodrome":"TRANSPORT","arrondissement":"ADMINISTRATIF","arrondissement_municipal":"ADMINISTRATIF","bassin_versant_topographique":"HYDROGRAPHIE","batiment":"BATI","batiment_rnb_lien_bdtopo":"BATI","canalisation":"SERVICES_ET_ACTIVITES","canton":"ADMINISTRATIF","cimetiere":"BATI","collectivite_territoriale":"ADMINISTRATIF","commune":"ADMINISTRATIF","commune_associee_ou_deleguee":"ADMINISTRATIF","condominium":"ADMINISTRATIF","construction_lineaire":"BATI","construction_ponctuelle":"BATI","construction_surfacique":"BATI","cours_d_eau":"HYDROGRAPHIE","departement":"ADMINISTRATIF","detail_hydrographique":"HYDROGRAPHIE","detail_orographique":"LIEUX_NOMMES","epci":"ADMINISTRATIF","equipement_de_transport":"TRANSPORT","erp":"SERVICES_ET_ACTIVITES","foret_publique":"ZONES_REGLEMENTEES","haie":"OCCUPATION_DU_SOL","itineraire_autre":"TRANSPORT","lien_adresse_vers_bdtopo":"ADRESSES","lieu_dit_non_habite":"LIEUX_NOMMES","ligne_electrique":"SERVICES_ET_ACTIVITES","ligne_orographique":"BATI","limite_terre_mer":"HYDROGRAPHIE","noeud_hydrographique":"HYDROGRAPHIE","non_communication":"TRANSPORT","parc_ou_reserve":"ZONES_REGLEMENTEES","piste_d_aerodrome":"TRANSPORT","plan_d_eau":"HYDROGRAPHIE","point_d_acces":"TRANSPORT","point_de_repere":"TRANSPORT","point_du_reseau":"TRANSPORT","poste_de_transformation":"SERVICES_ET_ACTIVITES","pylone":"BATI","region":"ADMINISTRATIF","reservoir":"BATI","route_numerotee_ou_nommee":"TRANSPORT","section_de_points_de_repere":"TRANSPORT","surface_hydrographique":"HYDROGRAPHIE","terrain_de_sport":"BATI","toponymie":"LIEUX_NOMMES","transport_par_cable":"TRANSPORT","troncon_de_route":"TRANSPORT","troncon_de_voie_ferree":"TRANSPORT","troncon_hydrographique":"HYDROGRAPHIE","voie_ferree_nommee":"TRANSPORT","voie_nommee":"ADRESSES","zone_d_activite_ou_d_interet":"SERVICES_ET_ACTIVITES","zone_d_estran":"OCCUPATION_DU_SOL","zone_d_habitation":"LIEUX_NOMMES","zone_de_vegetation":"OCCUPATION_DU_SOL"}#"entite_de_transition":"HYDROGRAPHIE"

    # Définition des variables
    zone_bis = PG_BD_TOPO_DICO[zone][0]
    epsg = PG_BD_TOPO_DICO[zone][1]
    rig = PG_BD_TOPO_DICO[zone][2]
    connection = openConnection(PG_DATABASE_NAME, user_name=PG_USER_NAME, password=PG_PASSWORD, ip_host=PG_IP_HOST, num_port=PG_NUM_PORT, schema_name=PG_SCHEMA_NAME)
    available_classes_list = getAllTables(connection, PG_SCHEMA_NAME, print_result=False)
    closeConnection(connection)
    available_classes_list = [classe[2:-8] for classe in available_classes_list if classe.split("_")[-1] == zone_bis]

    ####################################################################

    if debug >= 2:
        print(cyan + "exportBdTopoFromPostgresDatacart() : " + bold + green + "DEBUT DES TRAITEMENTS" + endC)

    # Mise à jour du log
    starting_event = "exportBdTopoFromPostgresDatacart() : Début du traitement : "
    timeLine(path_time_log, starting_event)

    # Test existence du fichier vecteur d'entrée
    if not os.path.exists(input_vector):
        print(cyan + "exportBdTopoFromPostgresDatacart() : " + bold + red + "Error: Input vector file \"%s\" not exists!" % input_vector + endC, file=sys.stderr)
        exit(-1)

    # Définition du format du fichier vecteur d'emprise d'étude en entrée
    format_vector_list = [ogr.GetDriver(i).GetDescription() for i in range(ogr.GetDriverCount())]
    i = 0
    for input_format_vector in format_vector_list:
        driver = ogr.GetDriverByName(input_format_vector)
        data_source_input = driver.Open(input_vector, 0)
        if data_source_input is not None:
            data_source_input.Destroy()
            break
        i += 1
    input_format_vector = format_vector_list[i]

    # Test format vecteur de sortie
    if not format_vector in [ESRI_SHAPEFILE_DRIVER_NAME, GPKG_DRIVER_NAME]:
        print(cyan + "exportBdTopoFromPostgresDatacart() : " + bold + red + "Error: Vector format \"%s\" is not recognize (must be \"%s\" or \"%s\")!" % (format_vector, ESRI_SHAPEFILE_DRIVER_NAME, GPKG_DRIVER_NAME) + endC, file=sys.stderr)
        exit(-1)

    # Test zone d'étude
    if not zone in AVAILABLE_ZONE_LIST:
        print(cyan + "exportBdTopoFromPostgresDatacart() : " + bold + red + "Error: Zone \"%s\" is not in the available zones (%s)!" % (zone, str(AVAILABLE_ZONE_LIST)) + endC, file=sys.stderr)
        exit(-1)

    # Test de conformité des classes sélectionnés
    if classes:
        bool_list = [classe in available_classes_list for classe in classes]
        if not all(bool_list):
            print(cyan + "exportBdTopoFromPostgresDatacart() : " + bold + red + "Error: Class %s are not availables!" % [x for x, m in zip(classes, bool_list) if not m] + endC, file=sys.stderr)
            exit(-1)
    else:
        classes = available_classes_list

    # Test concordance EPSG du fichier vecteur d'entrée et de la base Postgres
    epsg_input_vector, projection = getProjection(input_vector, format_vector=input_format_vector)
    if epsg != epsg_input_vector:
        print(cyan + "exportBdTopoFromPostgresDatacart() : " + bold + red + "Error: Input vector file EPSG (%s) is not corresponding to requested BD TOPO database EPSG (%s)!" % (epsg_input_vector, epsg) + endC, file=sys.stderr)
        exit(-1)

    # Récupération de l'emprise d'étude
    geometry_list = getGeomPolygons(input_vector, col=None, value=None, format_vector=input_format_vector)
    if len(geometry_list) == 0:
        print(cyan + "exportBdTopoFromPostgresDatacart() : " + bold + red + "Error: There are no geometry in the input vector file \"%s\"!" % input_vector + endC, file=sys.stderr)
        exit(-1)
    elif len(geometry_list) > 1:
        print(cyan + "exportBdTopoFromPostgresDatacart() : " + bold + red + "Error: There are more than one geometry in the input vector file \"%s\" (%s geometries)!" % (input_vector, len(geometry_list)) + endC, file=sys.stderr)
        exit(-1)
    else:
        geometry_roi = geometry_list[0].ExportToWkt()
        if buffer_size > 0:
            geometry_roi = geometry_list[0].Buffer(buffer_size).ExportToWkt()

    # Vérification de la compléxité de la géométrie
    temp_file = "n_vertices.txt"
    basename = os.path.basename(os.path.splitext(input_vector)[0]).lower()
    if buffer_size == 0:
        os.system("ogrinfo -q -dialect SQLite -sql 'SELECT SUM(ST_NPoints(geometry)) AS n_vertices FROM %s' %s > %s" % (basename, input_vector, temp_file))
    else:
        os.system("ogrinfo -q -dialect SQLite -sql 'SELECT SUM(ST_NPoints(ST_Buffer(geometry, %s))) AS n_vertices FROM %s' %s > %s" % (buffer_size, basename, input_vector, temp_file))
    n_vertices = int(readTextFile(temp_file).split(" ")[-1].split("\n")[0])
    os.remove(temp_file)
    if n_vertices >= 10000:
        print(cyan + "exportBdTopoFromPostgresDatacart() : " + bold + red + "Error: Input geometry is too complex (%s vertices)! Please simplify it (< 10000 vertices)." % n_vertices + endC, file=sys.stderr)
        exit(-1)

    # Récupération des métadonnées BD TOPO (correspondance des noms de champs SQL-SHP)
    if format_vector == ESRI_SHAPEFILE_DRIVER_NAME:
        if not os.path.exists(input_metadata):
            print(cyan + "exportBdTopoFromPostgresDatacart() : " + bold + red + "Error: Input metadata file \"%s\" not exists!" % input_metadata + endC, file=sys.stderr)
            exit(-1)
        else:
            metadata_bd_topo = readTextFileBySeparator(input_metadata, "#")

    ####################################################################

    if debug >= 2:
        print(cyan + "exportBdTopoFromPostgresDatacart() : " + bold + green + "Début des exports." + endC)

    # Boucle sur les classes à exporter
    idx = 1
    for bd_topo_classe in classes:
        bd_topo_classe_datacart = BD_TOPO_TABLE_PREFIX + bd_topo_classe + BD_TOPO_TABLE_SUFFIX + zone_bis
        bd_topo_theme = CLASSE_THEME_DICO[bd_topo_classe]
        if debug >= 3:
            print(cyan + "exportBdTopoFromPostgresDatacart() : " + bold + green + "Traitement de la classe \"%s\" (%s/%s)..." % (bd_topo_classe, str(idx), str(len(classes))) + endC)

        # Construction du nom du fichier de sortie
        if format_vector == GPKG_DRIVER_NAME:
            if not os.path.exists(output_directory):
                os.makedirs(output_directory)
            aoi_name = regExReplace(os.path.basename(os.path.splitext(input_vector)[0]), regex="[a-zA-Z0-9]", regex_replace="")
            bd_topo_info = "%s-ED%s" % (aoi_name.upper(), BD_TOPO_DATE)
            output_basename = "BDT_%s_%s_%s_%s" % (BD_TOPO_VERSION, GPKG_DRIVER_NAME, rig.upper(), bd_topo_info)
            output_vector_file = output_directory + os.sep + output_basename.upper() + extension_vector
        else:
            output_theme_directory = output_directory + os.sep + bd_topo_theme
            if not os.path.exists(output_theme_directory):
                os.makedirs(output_theme_directory)
            output_vector_file = output_theme_directory + os.sep + bd_topo_classe.upper() + extension_vector
            removeVectorFile(output_vector_file, format_vector=format_vector)

        # Construction de la requête d'export
        select_query = "*"
        if format_vector == ESRI_SHAPEFILE_DRIVER_NAME:
            connection = openConnection(PG_DATABASE_NAME, user_name=PG_USER_NAME, password=PG_PASSWORD, ip_host=PG_IP_HOST, num_port=PG_NUM_PORT, schema_name=PG_SCHEMA_NAME)
            columns_list = getAllColumns(connection, bd_topo_classe_datacart, print_result=False)
            closeConnection(connection)
            select_query = ""
            for text in metadata_bd_topo:
                if text[0] == bd_topo_classe and text[2] in columns_list:
                    select_query += "b.%s AS %s, " % (text[2], text[1])
            select_query += "b.%s AS %s, " % (ID_CEREMA_FIELD, ID_CEREMA_FIELD)
            select_query += "b.%s AS %s" % (SQL_GEOM_FIELD, SHP_GEOM_FIELD)
        from_query = "%s.%s AS b" % (PG_SCHEMA_NAME, bd_topo_classe_datacart)
        where_query = "ST_Intersects(b.%s, 'SRID=%s;%s')" % (SQL_GEOM_FIELD, str(epsg), geometry_roi)

        # Test de l'existence d'entités intersectant la ROI
        connection = openConnection(PG_DATABASE_NAME, user_name=PG_USER_NAME, password=PG_PASSWORD, ip_host=PG_IP_HOST, num_port=PG_NUM_PORT, schema_name=PUBLIC_SCHEMA_NAME)
        row_number = getData(connection, from_query, "COUNT(b.%s)" % SQL_GEOM_FIELD, condition=where_query)[0][0]
        closeConnection(connection)

        # Export des entités intersectant la ROI
        if row_number > 0:
            ogr2ogr_more_parameters = "-sql \"SELECT %s FROM %s WHERE %s\"" % (select_query, from_query, where_query)
            if format_vector == GPKG_DRIVER_NAME:
                ogr2ogr_more_parameters += " -nln %s -overwrite" % bd_topo_classe
            if format_vector == ESRI_SHAPEFILE_DRIVER_NAME:
                ogr2ogr_more_parameters += " -mapFieldType DateTime=String -lco ENCODING=%s" % BD_TOPO_ENCODING
            exportVectorByOgr2ogr(PG_DATABASE_NAME, output_vector_file, bd_topo_classe_datacart, user_name=PG_USER_NAME, password=PG_PASSWORD, ip_host=PG_IP_HOST, num_port=PG_NUM_PORT, schema_name=PUBLIC_SCHEMA_NAME, format_type=format_vector, ogr2ogr_more_parameters=ogr2ogr_more_parameters, print_cmd=False)
            if format_vector == ESRI_SHAPEFILE_DRIVER_NAME:
                attr_names_list = getAttributeNameList(output_vector_file, format_vector=ESRI_SHAPEFILE_DRIVER_NAME)
                new_attr_names_list = [attr_name.upper() for attr_name in attr_names_list]
                renameFieldsVector(output_vector_file, attr_names_list, new_attr_names_list, format_vector=ESRI_SHAPEFILE_DRIVER_NAME)
        else:
            print(cyan + "exportBdTopoFromPostgresDatacart() : " + bold + yellow + "L'emprise d'étude n'intersecte pas d'entités pour la classe \"%s\"." % bd_topo_classe + endC)

        idx += 1

    if debug >= 2:
        print(cyan + "exportBdTopoFromPostgresDatacart() : " + bold + green + "Fin des exports." + endC)

    ####################################################################

    # Mise à jour du log
    ending_event = "exportBdTopoFromPostgresDatacart() : Fin du traitement : "
    timeLine(path_time_log, ending_event)

    if debug >= 2:
        print(cyan + "exportBdTopoFromPostgresDatacart() : " + bold + green + "FIN DES TRAITEMENTS" + endC)

    return 0

#############################################################################################################################
################################################## Mise en place du parser ##################################################
#############################################################################################################################

def main(gui=False):
    parser = argparse.ArgumentParser(prog = "ExportBdTopoFromPostgres", description = "\
    Exporter les classes BD TOPO montées en base Postgres, à partir d'un fichier d'emprise. \n\
    Exemple 1 (serveur interne OSECC) : python3 -m ExportBdTopoFromPostgres -in /mnt/RAM_disk/emprise_etude.shp \n\
                                                                            -out /mnt/RAM_disk/BD_TOPO \n\
                                                                            -year 2022 \n\
                                                                            -zone FXX \n\
    Exemple 2 (serveur DataCart Cerema) : python3 -m ExportBdTopoFromPostgres -in /mnt/RAM_disk/emprise_etude.shp \n\
                                                                              -out /mnt/RAM_disk/BD_TOPO \n\
                                                                              -zone FXX \n\
                                                                              -datacart")

    parser.add_argument("-in", "--input_vector", default="", type=str, required=True, help="Input vector file.")
    parser.add_argument("-out", "--output_directory", default="", type=str, required=True, help="Output directory.")
    parser.add_argument("-buf", "--buffer_size", default=1000, type=float, required=False, help="Buffer size (in meters) applied for feature selection from input vector file. Default: 1000")
    parser.add_argument("-year", "--year", choices=[2020, 2021, 2022, 2023, 2024], default=2022, type=int, required=False, help="Year to be treated to extract BD TOPO. Default: 2022.")
    parser.add_argument("-zone", "--zone", choices=["FXX", "GLP", "MTQ", "GUF", "REU", "MYT", "SPM", "BLM", "MAF"], default="FXX", type=str, required=False, help="Zone to be treated to extract BD TOPO. Default: FXX.")
    parser.add_argument('-classes', '--classes_list', default="", type=str, nargs="+", required=False, help="Classes to extract from the BD TOPO database. Default: all classes.")
    parser.add_argument("-imd", "--input_metadata", default="/mnt/Data/10_Agents_travaux_en_cours/Benjamin/BD_TOPO_Classes.csv", type=str, required=False, help="Input BD TOPO metadata file mapping SQL-SHP fields names.")
    parser.add_argument("-datacart", "--datacart", action="store_true", default=False, required=False, help="Retrieve the latest year of BD TOPO data on DataCart server. Defaut: False")
    parser.add_argument("-vef", "--format_vector", choices=["ESRI Shapefile", "GPKG"], default="ESRI Shapefile", type=str, required=False, help="Format of vector files. Default: ESRI Shapefile.")
    parser.add_argument("-vee", "--extension_vector", choices=[".shp", ".gpkg"], default=".shp", type=str, required=False, help="Extension file for vector files. Default: .shp.")
    parser.add_argument("-pgh", "--postgis_ip_host", default="172.22.130.99", type=str, required=False, help="PostGIS server name or IP adress. Default: 172.22.130.99.")
    parser.add_argument("-pgp", "--postgis_num_port", default=5435, type=int, required=False, help="PostGIS port number. Default: 5435.")
    parser.add_argument("-pgu", "--postgis_user_name", default="postgres", type=str, required=False, help="PostGIS user name. Default: postgres.")
    parser.add_argument("-pgw", "--postgis_password", default="postgres", type=str, required=False, help="PostGIS user password. Default: postgres.")
    parser.add_argument("-log", "--path_time_log", default="", type=str, required=False, help="Option: Name of log. Default, no log file.")
    parser.add_argument("-debug", "--debug", default=3, type=int, required=False, help="Option: Value of level debug trace. Default, 3.")
    args = displayIHM(gui, parser)

    # Récupération du fichier vecteur d'entrée
    if args.input_vector != None:
        input_vector = args.input_vector
        if not os.path.isfile(input_vector):
            raise NameError (cyan + "ExportBdTopoFromPostgres: " + bold + red  + "File \"%s\" not exists (input_vector)." % input_vector + endC)

    # Récupération du répertoire de sortie
    if args.output_directory != None:
        output_directory = args.output_directory

    # Récupération des paramètres spécifiques
    if args.buffer_size != None:
        buffer_size = args.buffer_size
    if args.year != None:
        year = args.year
    if args.zone != None:
        zone = args.zone
    if args.classes_list != None:
        classes = args.classes_list
    if args.input_metadata != None:
        input_metadata = args.input_metadata
    if args.datacart != None:
        datacart = args.datacart

    # Récupération des paramètres fichiers
    if args.format_vector != None:
        format_vector = args.format_vector
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

    # Récupération des paramètres généraux
    if args.path_time_log != None:
        path_time_log = args.path_time_log
    if args.debug != None:
        global debug
        debug = args.debug

    if debug >= 3:
        print(bold + green + "Exporter les classes BD TOPO montées en base Postgres, à partir d'un fichier d'emprise - Variables dans le parser :" + endC)
        print(cyan + "    ExportBdTopoFromPostgres : " + endC + "input_vector : " + str(input_vector) + endC)
        print(cyan + "    ExportBdTopoFromPostgres : " + endC + "output_directory : " + str(output_directory) + endC)
        print(cyan + "    ExportBdTopoFromPostgres : " + endC + "buffer_size : " + str(buffer_size) + endC)
        print(cyan + "    ExportBdTopoFromPostgres : " + endC + "year : " + str(year) + endC)
        print(cyan + "    ExportBdTopoFromPostgres : " + endC + "zone : " + str(zone) + endC)
        print(cyan + "    ExportBdTopoFromPostgres : " + endC + "classes : " + str(classes) + endC)
        print(cyan + "    ExportBdTopoFromPostgres : " + endC + "input_metadata : " + str(input_metadata) + endC)
        print(cyan + "    ExportBdTopoFromPostgres : " + endC + "datacart : " + str(datacart) + endC)
        print(cyan + "    ExportBdTopoFromPostgres : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "    ExportBdTopoFromPostgres : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "    ExportBdTopoFromPostgres : " + endC + "postgis_ip_host : " + str(postgis_ip_host) + endC)
        print(cyan + "    ExportBdTopoFromPostgres : " + endC + "postgis_num_port : " + str(postgis_num_port) + endC)
        print(cyan + "    ExportBdTopoFromPostgres : " + endC + "postgis_user_name : " + str(postgis_user_name) + endC)
        print(cyan + "    ExportBdTopoFromPostgres : " + endC + "postgis_password : " + str(postgis_password) + endC)
        print(cyan + "    ExportBdTopoFromPostgres : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "    ExportBdTopoFromPostgres : " + endC + "debug : " + str(debug) + endC)

    # EXECUTION DE LA FONCTION
    if datacart:
        exportBdTopoFromPostgresDatacart(input_vector, output_directory, buffer_size, zone, classes, input_metadata, format_vector, extension_vector, path_time_log)
    else:
        exportBdTopoFromPostgres(input_vector, output_directory, buffer_size, year, zone, classes, input_metadata, format_vector, extension_vector, postgis_ip_host, postgis_num_port, postgis_user_name, postgis_password, path_time_log)

if __name__ == "__main__":
    main(gui=False)

