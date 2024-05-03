#!/usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

"""
Nom de l'objet : ClassificationLczOperational.py
Description :
-------------
Objectif : établir une classification LCZ (sous format vecteur) à partir de divers indicateurs (également sous format vecteurs)
Remarque : version opérationnelle de l'application ClassificationLCZ, avec utilisation du SQL pour établir la classification LCZ

-----------------
Outils utilisés :

------------------------------
Historique des modifications :
15/04/2021 : création

-----------------------
A réfléchir / A faire :

"""

# Import des bibliothèques Python
from __future__ import print_function
import os, sys, argparse
from Lib_display import bold,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_file import removeVectorFile
from Lib_log import timeLine
from Lib_postgis import createDatabase, importVectorByOgr2ogr, openConnection, executeQuery, closeConnection, exportVectorByOgr2ogr, dropDatabase

# Niveau de debug (variable globale)
debug = 3

########################################################################
# FONCTION classificationLczSql()                                      #
########################################################################
def classificationLczSql(input_division, input_hre, input_ocs, output_lcz, id_field='id', epsg=2154, format_vector='ESRI Shapefile', postgis_ip_host='localhost', postgis_num_port=5432, postgis_user_name='postgres', postgis_password='postgres', postgis_database_name='lcz_db', postgis_schema_name='public', postgis_encoding='UTF-8', path_time_log='', save_results_intermediate=False, overwrite=True):
    """
    # ROLE :
    #     établie une classification LCZ via SQL, en utilisant la méthode dite opérationnelle
    #
    # ENTREES DE LA FONCTION :
    #     input_division : fichier de découpage morphologique (entrée vecteur)
    #     input_hre : fichier de l'indicateur HRE (entrée vecteur)
    #     input_ocs : fichier des indicateurs OCS (entrée vecteur)
    #     output_lcz : fichier de cartographie LCZ (sortie vecteur)
    #     id_field : champ ID du fichier de découpage morphologique. Par défaut : 'id'
    #     epsg : code epsg du système de projection. Par défaut : 2154
    #     format_vector : format des fichiers vecteur. Par défaut : 'ESRI Shapefile'
    #     postgis_ip_host : nom du serveur PostGIS. Par défaut : 'localhost'
    #     postgis_num_port : numéro de port du serveur PostGIS. Par défaut : 5432
    #     postgis_user_name : nom d'utilisateur PostGIS. Par défaut : 'postgres'
    #     postgis_password : mot de passe de l'utilisateur PostGIS. Par défaut : 'postgres'
    #     postgis_database_name : nom de la base PostGIS. Par défaut : 'lcz_db'
    #     postgis_schema_name : nom du schéma dans la base PostGIS. Par défaut : 'public'
    #     postgis_encoding : l'encodage des fichiers pour l'import de vecteurs dans PostGIS. Par défaut : 'UTF-8'
    #     path_time_log : fichier log de sortie, par défaut vide
    #     save_results_intermediate : fichiers temporaires conservés, par défaut = False
    #     overwrite : écrase si un fichier existant a le même nom qu'un fichier de sortie, par défaut = True
    #
    # SORTIES DE LA FONCTION :
    #     N.A.
    """

    if debug >= 3:
        print('\n' + bold + green + "Classification LCZ via SQL - Variables dans la fonction :" + endC)
        print(cyan + "    classificationLczSql() : " + endC + "input_division : " + str(input_division) + endC)
        print(cyan + "    classificationLczSql() : " + endC + "input_hre : " + str(input_hre) + endC)
        print(cyan + "    classificationLczSql() : " + endC + "input_ocs : " + str(input_ocs) + endC)
        print(cyan + "    classificationLczSql() : " + endC + "output_lcz : " + str(output_lcz) + endC)
        print(cyan + "    classificationLczSql() : " + endC + "id_field : " + str(id_field) + endC)
        print(cyan + "    classificationLczSql() : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "    classificationLczSql() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "    classificationLczSql() : " + endC + "postgis_ip_host : " + str(postgis_ip_host) + endC)
        print(cyan + "    classificationLczSql() : " + endC + "postgis_num_port : " + str(postgis_num_port) + endC)
        print(cyan + "    classificationLczSql() : " + endC + "postgis_user_name : " + str(postgis_user_name) + endC)
        print(cyan + "    classificationLczSql() : " + endC + "postgis_password : " + str(postgis_password) + endC)
        print(cyan + "    classificationLczSql() : " + endC + "postgis_database_name : " + str(postgis_database_name) + endC)
        print(cyan + "    classificationLczSql() : " + endC + "postgis_schema_name : " + str(postgis_schema_name) + endC)
        print(cyan + "    classificationLczSql() : " + endC + "postgis_encoding : " + str(postgis_encoding) + endC)
        print(cyan + "    classificationLczSql() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "    classificationLczSql() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "    classificationLczSql() : " + endC + "overwrite : " + str(overwrite) + endC + '\n')

    # Définition des constantes
    SUFFIX_TEMP = '_temp'

    # Mise à jour du log
    starting_event = "classificationLczSql() : Début du traitement : "
    timeLine(path_time_log, starting_event)

    print(cyan + "classificationLczSql() : " + bold + green + "DEBUT DES TRAITEMENTS" + endC + '\n')

    # Définition des variables
    hre_field = 'mean_h'
    are_field = 'mean_a'
    bur_field = 'built'
    ror_field = 'mineral'
    bsr_field = 'baresoil'
    war_field = 'water'
    ver_field = 'veget'
    vhr_field = 'veg_h_rate'
    lcz_field = 'lcz'
    lcz_int_field = 'lcz_int'
    div_table = 'i_div'
    hre_table = 'i_hre'
    ocs_table = 'i_ocs'
    lcz_table = 'o_lcz'

    # Nettoyage des traitements précédents
    if overwrite:
        if debug >= 3:
            print(cyan + "classificationLczSql() : " + endC + "Nettoyage des traitements précédents." + endC + '\n')
        removeVectorFile(output_lcz)
        dropDatabase(postgis_database_name, user_name=postgis_user_name, password=postgis_password, ip_host=postgis_ip_host, num_port=postgis_num_port, schema_name=postgis_schema_name)
    else:
        if os.path.exists(output_lcz):
            print(cyan + "classificationLczSql() : " + bold + yellow + "Le fichier de sortie existe déjà et ne sera pas regénéré." + endC + '\n')
            raise
        pass

    ####################################################################

    createDatabase(postgis_database_name, user_name=postgis_user_name, password=postgis_password, ip_host=postgis_ip_host, num_port=postgis_num_port, schema_name=postgis_schema_name)
    div_table = importVectorByOgr2ogr(postgis_database_name, input_division, div_table, user_name=postgis_user_name, password=postgis_password, ip_host=postgis_ip_host, num_port=postgis_num_port, schema_name=postgis_schema_name, epsg=epsg, codage=postgis_encoding)
    hre_table = importVectorByOgr2ogr(postgis_database_name, input_hre, hre_table, user_name=postgis_user_name, password=postgis_password, ip_host=postgis_ip_host, num_port=postgis_num_port, schema_name=postgis_schema_name, epsg=epsg, codage=postgis_encoding)
    ocs_table = importVectorByOgr2ogr(postgis_database_name, input_ocs, ocs_table, user_name=postgis_user_name, password=postgis_password, ip_host=postgis_ip_host, num_port=postgis_num_port, schema_name=postgis_schema_name, epsg=epsg, codage=postgis_encoding)
    connection = openConnection(postgis_database_name, user_name=postgis_user_name, password=postgis_password, ip_host=postgis_ip_host, num_port=postgis_num_port, schema_name=postgis_schema_name)

    query = "DROP TABLE IF EXISTS %s;\n" % lcz_table
    query += "CREATE TABLE %s AS\n" % lcz_table
    query += "    SELECT d.%s AS %s, h.%s AS hre, h.%s AS are, o.%s AS bur, o.%s AS ror, o.%s AS bsr, o.%s AS war, o.%s AS ver, o.%s AS vhr, d.geom AS geom\n" % (id_field, id_field, hre_field, are_field, bur_field, ror_field, bsr_field, war_field, ver_field, vhr_field)
    query += "    FROM %s AS d, %s AS h, %s AS o\n" % (div_table, hre_table, ocs_table)
    query += "    WHERE d.%s = h.%s AND d.%s = o.%s;\n" % (id_field, id_field, id_field, id_field)

    query += "ALTER TABLE %s ADD COLUMN %s VARCHAR(8);\n" % (lcz_table, lcz_field)
    query += "ALTER TABLE %s ADD COLUMN %s SMALLINT;\n" % (lcz_table, lcz_int_field)
    query += "UPDATE %s SET %s = 'urban' WHERE bur > 5;\n" % (lcz_table, lcz_field)
    query += "UPDATE %s SET %s = 'natural' WHERE bur <= 5;\n" % (lcz_table, lcz_field)
    query += "UPDATE %s SET %s = 'low_ocs' WHERE %s = 'natural' AND (bur + ror + bsr + war + ver) <= 60;\n" % (lcz_table, lcz_field, lcz_field)

    query += "UPDATE %s SET %s = '1', %s = 1 WHERE %s = 'urban' AND (hre > 30);\n" % (lcz_table, lcz_field, lcz_int_field, lcz_field)
    query += "UPDATE %s SET %s = '2', %s = 2 WHERE %s = 'urban' AND (hre > 9 AND hre <= 30);\n" % (lcz_table, lcz_field, lcz_int_field, lcz_field)
    query += "UPDATE %s SET %s = '3', %s = 3 WHERE %s = 'urban' AND (hre <= 9);\n" % (lcz_table, lcz_field, lcz_int_field, lcz_field)
    query += "UPDATE %s SET %s = '4', %s = 4 WHERE %s = '1' AND ((bur <= 40) OR (bur + ror <= 50) OR (bsr + war + ver > 60));\n" % (lcz_table, lcz_field, lcz_int_field, lcz_field)
    query += "UPDATE %s SET %s = '5', %s = 5 WHERE %s = '2' AND ((bur <= 40) OR (bur + ror <= 50) OR (bsr + war + ver > 60));\n" % (lcz_table, lcz_field, lcz_int_field, lcz_field)
    query += "UPDATE %s SET %s = '6', %s = 6 WHERE %s = '3' AND ((bur <= 40) OR (bur + ror <= 50) OR (bsr + war + ver > 60));\n" % (lcz_table, lcz_field, lcz_int_field, lcz_field)
    query += "UPDATE %s SET %s = '7', %s = 7 WHERE %s IN ('3', '6') AND (bur > 60) AND (bsr > ror + war + ver);\n" % (lcz_table, lcz_field, lcz_int_field, lcz_field)
    query += "UPDATE %s SET %s = '8', %s = 8 WHERE %s IN ('2', '3', '5', '6') AND (hre <= 20) AND (bur + ror > 30) AND (are > 1000);\n" % (lcz_table, lcz_field, lcz_int_field, lcz_field)
    query += "UPDATE %s SET %s = '9', %s = 9 WHERE %s = '6' AND ((bur <= 20) OR (bur + ror <= 30) OR (bsr + war + ver > 80));\n" % (lcz_table, lcz_field, lcz_int_field, lcz_field)

    query += "UPDATE %s SET %s = 'A', %s = 11 WHERE %s = 'natural' AND ((ver >= ror) AND (ver >= bsr) AND (ver >= war)) AND (vhr > 50);\n" % (lcz_table, lcz_field, lcz_int_field, lcz_field)
    query += "UPDATE %s SET %s = 'B', %s = 12 WHERE %s = 'natural' AND ((ver >= ror) AND (ver >= bsr) AND (ver >= war)) AND (vhr > 25 AND vhr <= 50);\n" % (lcz_table, lcz_field, lcz_int_field, lcz_field)
    query += "UPDATE %s SET %s = 'C', %s = 13 WHERE %s = 'natural' AND ((ver >= ror) AND (ver >= bsr) AND (ver >= war)) AND (vhr > 10 AND vhr <= 25);\n" % (lcz_table, lcz_field, lcz_int_field, lcz_field)
    query += "UPDATE %s SET %s = 'D', %s = 14 WHERE %s = 'natural' AND ((ver >= ror) AND (ver >= bsr) AND (ver >= war)) AND (vhr <= 10);\n" % (lcz_table, lcz_field, lcz_int_field, lcz_field)
    query += "UPDATE %s SET %s = 'E', %s = 15 WHERE %s = 'natural' AND ((ror >= bsr) AND (ror >= war) AND (ror >= ver));\n" % (lcz_table, lcz_field, lcz_int_field, lcz_field)
    query += "UPDATE %s SET %s = 'F', %s = 16 WHERE %s = 'natural' AND ((bsr >= ror) AND (bsr >= war) AND (bsr >= ver));\n" % (lcz_table, lcz_field, lcz_int_field, lcz_field)
    query += "UPDATE %s SET %s = 'G', %s = 17 WHERE %s = 'natural' AND ((war >= ror) AND (war >= bsr) AND (war >= ver));\n" % (lcz_table, lcz_field, lcz_int_field, lcz_field)

    #query += "ALTER TABLE %s ALTER COLUMN %s TYPE INTEGER;\n" % (lcz_table, id_field)
    query += "ALTER TABLE %s ALTER COLUMN hre TYPE NUMERIC(12,2);\n" % lcz_table
    query += "ALTER TABLE %s ALTER COLUMN are TYPE NUMERIC(12,2);\n" % lcz_table
    query += "ALTER TABLE %s ALTER COLUMN bur TYPE NUMERIC(6,2);\n" % lcz_table
    query += "ALTER TABLE %s ALTER COLUMN ror TYPE NUMERIC(6,2);\n" % lcz_table
    query += "ALTER TABLE %s ALTER COLUMN bsr TYPE NUMERIC(6,2);\n" % lcz_table
    query += "ALTER TABLE %s ALTER COLUMN war TYPE NUMERIC(6,2);\n" % lcz_table
    query += "ALTER TABLE %s ALTER COLUMN ver TYPE NUMERIC(6,2);\n" % lcz_table
    query += "ALTER TABLE %s ALTER COLUMN vhr TYPE NUMERIC(6,2);\n" % lcz_table

    if debug >= 3:
        print('\n' + query)
    executeQuery(connection, query)

    closeConnection(connection)
    exportVectorByOgr2ogr(postgis_database_name, output_lcz, lcz_table, user_name=postgis_user_name, password=postgis_password, ip_host=postgis_ip_host, num_port=postgis_num_port, schema_name=postgis_schema_name, format_type=format_vector)

    ####################################################################

    # Suppression des fichiers temporaires
    if not save_results_intermediate:
        if debug >= 3:
            print('\n' + cyan + "classificationLczSql() : " + endC + "Suppression des fichiers temporaires." + endC + '\n')
        dropDatabase(postgis_database_name, user_name=postgis_user_name, password=postgis_password, ip_host=postgis_ip_host, num_port=postgis_num_port, schema_name=postgis_schema_name)

    print(cyan + "classificationLczSql() : " + bold + green + "FIN DES TRAITEMENTS" + endC + '\n')

    # Mise à jour du log
    ending_event = "classificationLczSql() : Fin du traitement : "
    timeLine(path_time_log, ending_event)

    return 0

#############################################################################################################################
################################################## Mise en place du parser ##################################################
#############################################################################################################################

def main(gui=False):
    parser = argparse.ArgumentParser(prog = "Classification LCZ Cerema", description = "\
    Méthode opérationnelle de classification LCZ à partir de données satellite. \n\
    Exemple : python3 -m ClassificationLczOperational -in  /mnt/RAM_disk/LCZ/segmentation_urbaine.shp \n\
                                                      -hre /mnt/RAM_disk/LCZ/indicateur_HRE.shp \n\
                                                      -ocs /mnt/RAM_disk/LCZ/indicateurs_OCS.shp \n\
                                                      -out /mnt/RAM_disk/LCZ/classification_LCZ.shp")

    parser.add_argument('-in', '--input_division', default="", type=str, required=True, help="Input morphological division vector file.")
    parser.add_argument('-hre', '--input_hre', default="", type=str, required=True, help="Input HRE indicator vector file.")
    parser.add_argument('-ocs', '--input_ocs', default="", type=str, required=True, help="Input OCS indicators vector file.")
    parser.add_argument('-out', '--output_lcz', default="", type=str, required=True, help="Output LCZ classification vector file.")
    parser.add_argument('-id', '--id_field', default="id", type=str, required=False, help="Name of the ID field in the input morphological division vector file. Default: 'id'.")
    parser.add_argument('-epsg', '--epsg', default=2154, type=int, required=False, help="Projection of the output file. Default: 2154.")
    parser.add_argument('-vef', '--format_vector', default="ESRI Shapefile", type=str, required=False, help="Format of vector files. Default: 'ESRI Shapefile'.")
    parser.add_argument('-pgh', '--postgis_ip_host', default="localhost", type=str, required=False, help="PostGIS server name or IP adress. Default: 'localhost'.")
    parser.add_argument('-pgp', '--postgis_num_port', default=5432, type=int, required=False, help="PostGIS port number. Default: '5432'.")
    parser.add_argument('-pgu', '--postgis_user_name', default="postgres", type=str, required=False, help="PostGIS user name. Default: 'postgres'.")
    parser.add_argument('-pgw', '--postgis_password', default="postgres", type=str, required=False, help="PostGIS user password. Default: 'postgres'.")
    parser.add_argument('-pgd', '--postgis_database_name', default="lcz_db", type=str, required=False, help="PostGIS database name. Default: 'lcz_db'.")
    parser.add_argument('-pgs', '--postgis_schema_name', default="public", type=str, required=False, help="PostGIS schema name. Default: 'public'.")
    parser.add_argument('-pge', '--postgis_encoding', default="UTF-8", type=str, required=False, help="PostGIS encoding for vector import. Default: 'UTF-8'.")
    parser.add_argument('-log', '--path_time_log', default="", type=str, required=False, help="Option: Name of log. Default, no log file.")
    parser.add_argument('-sav', '--save_results_intermediate', action='store_true', default=False, required=False, help="Option: Save intermediate result after the process. Default, False.")
    parser.add_argument('-now', '--overwrite', action='store_false', default=True, required=False, help="Option: Overwrite files with same names. Default, True.")
    parser.add_argument('-debug', '--debug', default=3, type=int, required=False, help="Option: Value of level debug trace. Default, 3.")
    args = displayIHM(gui, parser)

    # Récupération des fichiers d'entrée
    if args.input_division != None:
        input_division = args.input_division
        if not os.path.isfile(input_division):
            raise NameError (cyan + "ClassificationLczOperational: " + bold + red  + "File %s not exists (input_division)." % input_division + endC)
    if args.input_hre != None:
        input_hre = args.input_hre
        if not os.path.isfile(input_hre):
            raise NameError (cyan + "ClassificationLczOperational: " + bold + red  + "File %s not exists (input_hre)." % input_hre + endC)
    if args.input_ocs != None:
        input_ocs = args.input_ocs
        if not os.path.isfile(input_ocs):
            raise NameError (cyan + "ClassificationLczOperational: " + bold + red  + "File %s not exists (input_ocs)." % input_ocs + endC)

    # Récupération du fichier de sortie
    if args.output_lcz != None:
        output_lcz = args.output_lcz

    # Récupération du paramètre ID
    if args.id_field != None:
        id_field = args.id_field

    # Récupération des paramètres fichiers
    if args.epsg != None:
        epsg = args.epsg
    if args.format_vector != None:
        format_vector = args.format_vector

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

    if os.path.isfile(output_lcz) and not overwrite:
        raise NameError (cyan + "ClassificationLczOperational: " + bold + red  + "File %s already exists, and overwrite is not activated." % output_lcz + endC)

    if debug >= 3:
        print('\n' + bold + green + "Classification LCZ Cerema - Variables dans le parser :" + endC)
        print(cyan + "    ClassificationLczOperational : " + endC + "input_division : " + str(input_division) + endC)
        print(cyan + "    ClassificationLczOperational : " + endC + "input_hre : " + str(input_hre) + endC)
        print(cyan + "    ClassificationLczOperational : " + endC + "input_ocs : " + str(input_ocs) + endC)
        print(cyan + "    ClassificationLczOperational : " + endC + "output_lcz : " + str(output_lcz) + endC)
        print(cyan + "    ClassificationLczOperational : " + endC + "id_field : " + str(id_field) + endC)
        print(cyan + "    ClassificationLczOperational : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "    ClassificationLczOperational : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "    ClassificationLczOperational : " + endC + "postgis_ip_host : " + str(postgis_ip_host) + endC)
        print(cyan + "    ClassificationLczOperational : " + endC + "postgis_num_port : " + str(postgis_num_port) + endC)
        print(cyan + "    ClassificationLczOperational : " + endC + "postgis_user_name : " + str(postgis_user_name) + endC)
        print(cyan + "    ClassificationLczOperational : " + endC + "postgis_password : " + str(postgis_password) + endC)
        print(cyan + "    ClassificationLczOperational : " + endC + "postgis_database_name : " + str(postgis_database_name) + endC)
        print(cyan + "    ClassificationLczOperational : " + endC + "postgis_schema_name : " + str(postgis_schema_name) + endC)
        print(cyan + "    ClassificationLczOperational : " + endC + "postgis_encoding : " + str(postgis_encoding) + endC)
        print(cyan + "    ClassificationLczOperational : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "    ClassificationLczOperational : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "    ClassificationLczOperational : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "    ClassificationLczOperational : " + endC + "debug : " + str(debug) + endC + '\n')

    # Création du dossier de sortie, s'il n'existe pas
    if not os.path.isdir(os.path.dirname(output_lcz)):
        os.makedirs(os.path.dirname(output_lcz))

    # EXECUTION DES FONCTIONS
    classificationLczSql(input_division, input_hre, input_ocs, output_lcz, id_field, epsg, format_vector, postgis_ip_host, postgis_num_port, postgis_user_name, postgis_password, postgis_database_name, postgis_schema_name, postgis_encoding, path_time_log, save_results_intermediate, overwrite)

if __name__ == '__main__':
    main(gui=False)

