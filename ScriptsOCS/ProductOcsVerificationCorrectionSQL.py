#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerSO/DALETT/SCGSI  All rights reserved.                                                                            #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT QUI PERMET DE VERIFIER ET CORRIGER (PB TOPOLOGIQUE) LES RESULTATS ISSUES DE PRODUDCTION OCS                                        #
#                                                                                                                                           #
#############################################################################################################################################
'''
Nom de l'objet : ProductOcsVerificationCorrectionSQL.py
Description :
    Objectif : Verifier et corriger pb topologique modification des colonnes, les resultats issues de produdction OCS
    Rq : utilisation des OTB Applications : na
    Appel de routines SQL

Date de creation : 18/01/2017
----------
Histoire :
----------
Origine : Nouveau
18/01/2017 : Création
-----------------------------------------------------------------------------------------------------
Modifications

------------------------------------------------------
A Reflechir/A faire
 -
 -
'''

from __future__ import print_function
import os,sys,glob,argparse,string
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_log import timeLine
from Lib_postgis import executeQuery, openConnection, closeConnection, getData, dropDatabase, createDatabase, createSchema, importVectorByOgr2ogr, exportVectorByOgr2ogr, topologyCorrections

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 3

###########################################################################################################################################
# FONCTION verificationCorrection()                                                                                                       #
###########################################################################################################################################
# ROLE:
#     Verifier et corrige des vecteurs resultats de classifications OCS en traitement sous postgis
#
# ENTREES DE LA FONCTION :
#     vector_ref: le vecteur d'emprise de référence des vecteurs
#     vectors_input_list : les vecteurs d'entrée qui seront découpés
#     vectors_output_list : les vecteurs de sorties découpées
#     epsg : EPSG code de projection
#     project_encoding : encodage des fichiers d'entrés
#     server_postgis : nom du serveur postgis
#     port_number : numéro du port pour le serveur postgis
#     user_postgis : le nom de l'utilisateurs postgis
#     password_postgis : le mot de passe de l'utilisateur posgis
#     database_postgis : le nom de la base posgis à utiliser
#     schema_postgis : le nom du schéma à utiliser
#     path_time_log : le fichier de log de sortie
#     save_results_intermediate : fichiers de sorties intermediaires nettoyees, par defaut = False
#     overwrite : écrase si un fichier existant a le même nom qu'un fichier de sortie, par defaut a True
#
# SORTIES DE LA FONCTION :
#     na
#

def verificationCorrection(vector_ref, vectors_input_list, vectors_output_list, epsg, project_encoding, server_postgis, port_number, user_postgis, password_postgis, database_postgis, schema_postgis, path_time_log, save_results_intermediate=False, overwrite=True) :

    # Mise à jour du Log
    starting_event = "verificationCorrection() : Verifie and correct vector starting : "
    timeLine(path_time_log,starting_event)

    print(endC)
    print(bold + green + "## START : VERIFIE CORRECT VECTORS" + endC)
    print(endC)

    if debug >= 2:
        print(bold + green + "verificationCorrection() : Variables dans la fonction" + endC)
        print(cyan + "verificationCorrection() : " + endC + "vector_ref : " + str(vector_ref) + endC)
        print(cyan + "verificationCorrection() : " + endC + "vectors_input_list : " + str(vectors_input_list) + endC)
        print(cyan + "verificationCorrection() : " + endC + "vectors_output_list : " + str(vectors_output_list) + endC)
        print(cyan + "verificationCorrection() : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "verificationCorrection() : " + endC + "project_encoding : " + str(project_encoding) + endC)
        print(cyan + "verificationCorrection() : " + endC + "server_postgis : " + str(server_postgis) + endC)
        print(cyan + "verificationCorrection() : " + endC + "port_number : " + str(port_number) + endC)
        print(cyan + "verificationCorrection() : " + endC + "user_postgis : " + str(user_postgis) + endC)
        print(cyan + "verificationCorrection() : " + endC + "password_postgis : " + str(password_postgis) + endC)
        print(cyan + "verificationCorrection() : " + endC + "database_postgis : " + str(database_postgis) + endC)
        print(cyan + "verificationCorrection() : " + endC + "schema_postgis : " + str(schema_postgis) + endC)
        print(cyan + "verificationCorrection() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "verificationCorrection() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "verificationCorrection() : " + endC + "overwrite : " + str(overwrite) + endC)

    # Constante suffix des tables de contrôle en SQL
    SUFFIX_SUM = '_sum'
    SUFFIX_100 = '_100'
    SUFFIX_SURF = '_surf'
    COLUMN_SUM = "sum"

    schema_postgis = schema_postgis.lower()
    table_reference_name = os.path.splitext(os.path.basename(vector_ref))[0].lower()
    table_reference_complete_name = schema_postgis + '.' + table_reference_name

    # Préparation de la base de données
    dropDatabase(database_postgis,  user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number)) # Suppression de la base de données (si elle existe d'un traitement précédent)
    createDatabase(database_postgis, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number)) # Création de la base de données
    connection = openConnection(database_postgis, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema='') # Connexion à la base de données
    createSchema(connection, schema_postgis) # Création du schéma, s'il n'existe pas
    closeConnection(connection) # Déconnexion de la base de données (pour éviter les conflits avec les outils d'import de shape)

    # Monter en base du fichier vecteur de référence
    table_reference_complete_name = importVectorByOgr2ogr(database_postgis, vector_ref, table_reference_complete_name, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema=schema_postgis, epsg=str(epsg), codage=project_encoding)

    # Pour tous les fichiers à traiter
    for idx_vector in range(len(vectors_input_list)):

        vector_input = vectors_input_list[idx_vector]
        vector_output = vectors_output_list[idx_vector]
        table_input_name = schema_postgis + '.' + os.path.splitext(os.path.basename(vector_input))[0].lower()
        table_output_name = schema_postgis + '.' + os.path.splitext(os.path.basename(vector_output))[0].lower()

        # Test si le vecteur de sortie existe déjà et si il doit être écrasés
        check = os.path.isfile(vector_output)
        if check and not overwrite: # Si le fichier existe déjà et que overwrite n'est pas activé
            print(bold + yellow + "File vector output : " + vector_output + " already exists and will not be created again." + endC)
        else :
            if check:
                try:
                    removeVectorFile(vector_output)
                except Exception:
                    pass # si le fichier n'existe pas, il ne peut pas être supprimé : cette étape est ignorée

        # Monter en base du fichier vecteur d'entrée
        table_input_name = importVectorByOgr2ogr(database_postgis, vector_input, table_input_name, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema=schema_postgis, epsg=str(epsg), codage=project_encoding)

        # Traitements SQL
        #################

        connection = openConnection(database_postgis, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema=schema_postgis)

        # Création de la nouvelle table corrigée
        query_create_table = """
        CREATE TABLE %s AS
            SELECT
                CAST(id AS INTEGER) AS id,
                CAST(label AS INTEGER) AS label,
                CAST(datemaj AS TEXT) AS datemaj,
                CAST(srcmaj AS TEXT) AS srcmaj,
                CAST(round(img_sat) AS INTEGER) AS img_sat,
                CAST(round(bd_carto) AS INTEGER) AS bd_carto,
                CAST(round(bd_topo) AS INTEGER) AS bd_topo,
                CAST(round(bd_foret) AS INTEGER) AS bd_foret,
                CAST(round(clc) AS INTEGER) AS clc,
                CAST(round(cvi) AS INTEGER) AS cvi,
                CAST(round(rpg) AS INTEGER) AS rpg,
                CAST(round(vrgprunus) AS INTEGER) AS vrgprunus,
                CAST(round(oss_ign) AS INTEGER) AS oss_ign,
                geom
            FROM %s;
        """ % (table_output_name, table_input_name)
        executeQuery(connection, query_create_table)

        # Mise à jour des colonne de la nouvelle table
        query_update_colum = """
        UPDATE %s SET img_sat = 100 - (bd_carto + bd_topo + bd_foret + clc + cvi + rpg + vrgprunus + oss_ign);
        UPDATE %s SET bd_carto = bd_carto-1, img_sat = 0 WHERE (img_sat=-1) AND (bd_carto = GREATEST(bd_carto, bd_topo, bd_foret, clc, cvi, rpg, vrgprunus, oss_ign));
        UPDATE %s SET bd_topo = bd_topo-1, img_sat = 0 WHERE (img_sat=-1) AND (bd_topo = GREATEST(bd_carto, bd_topo, bd_foret, clc, cvi, rpg, vrgprunus, oss_ign));
        UPDATE %s SET bd_foret = bd_foret-1, img_sat = 0 WHERE (img_sat=-1) AND (bd_foret = GREATEST(bd_carto, bd_topo, bd_foret, clc, cvi, rpg, vrgprunus, oss_ign));
        UPDATE %s SET clc = clc-1, img_sat = 0 WHERE (img_sat=-1) AND (clc = GREATEST(bd_carto, bd_topo, bd_foret, clc, cvi, rpg, vrgprunus, oss_ign));
        UPDATE %s SET cvi = cvi-1, img_sat = 0 WHERE (img_sat=-1) AND (cvi = GREATEST(bd_carto, bd_topo, bd_foret, clc, cvi, rpg, vrgprunus, oss_ign));
        UPDATE %s SET rpg = rpg-1, img_sat = 0 WHERE (img_sat=-1) AND (rpg = GREATEST(bd_carto, bd_topo, bd_foret, clc, cvi, rpg, vrgprunus, oss_ign));
        UPDATE %s SET vrgprunus = vrgprunus-1, img_sat = 0 WHERE (img_sat=-1) AND (vrgprunus = GREATEST(bd_carto, bd_topo, bd_foret, clc, cvi, rpg, vrgprunus, oss_ign));
        UPDATE %s SET oss_ign = oss_ign-1, img_sat = 0  WHERE (img_sat=-1) AND (oss_ign = GREATEST(bd_carto, bd_topo, bd_foret, clc, cvi, rpg, vrgprunus, oss_ign));
        """ % (table_output_name, table_output_name, table_output_name, table_output_name, table_output_name, table_output_name, table_output_name, table_output_name, table_output_name)
        executeQuery(connection, query_update_colum)

        # Vérification de la somme des colonnes
        pos = table_output_name.find("m2_") - 3
        resolution = table_output_name[pos:pos+3]
        table_name = schema_postgis + '.' + "controle_" + table_reference_name + "_" + resolution + "m_cor"
        table_verif_sum_name = table_name + SUFFIX_SUM
        table_verif_sum100_name = table_name + SUFFIX_SUM + SUFFIX_100
        table_verif_surf_name = table_name + SUFFIX_SURF

        query_verif_sum = """
        CREATE TABLE %s AS
        SELECT id, img_sat, bd_carto + bd_topo + bd_foret + clc + cvi + rpg + vrgprunus + oss_ign AS sum
        FROM %s;
        """ % (table_verif_sum_name, table_output_name)
        executeQuery(connection, query_verif_sum)

        query_verif_sum100 = """
        CREATE TABLE %s AS
        SELECT id, sum
        FROM %s
        WHERE sum != 100 OR img_sat = -1;
        """ % (table_verif_sum100_name, table_verif_sum_name)
        executeQuery(connection, query_verif_sum100)

        data_list = getData(connection, table_verif_sum100_name, COLUMN_SUM)
        if len(data_list) > 0:
            print(cyan + "verificationCorrection() : " + bold + red + "Error column sum 100 not empty = " + str(len(data_list)) +  endC, file=sys.stderr)

        # Vérification des aires
        query_verif_surf = """
        CREATE TABLE %s AS
        SELECT 'OCS_SAT', SUM(st_area(geom))
        FROM %s;

        INSERT INTO %s
        SELECT '%s', st_area(geom)
        FROM %s;
        """ % (table_verif_surf_name, table_output_name, table_verif_surf_name, table_reference_complete_name, table_reference_complete_name)
        executeQuery(connection, query_verif_surf)

        delta = 1
        data_list = getData(connection, table_verif_surf_name, COLUMN_SUM)
        data_list0 = float(str(data_list[0])[1:-2])
        for data in data_list:
            data = float(str(data)[1:-2])
            data_ref_min = int(data_list0) - delta
            data_ref_max = int(data_list0) + delta
            if int(data) < data_ref_min or int(data) > data_ref_max:
                print(cyan + "verificationCorrection() : " + bold + red + "Error area comparaison, ref = " + str(data_list0) + "m², data = " + str(data) + "m²" + endC, file=sys.stderr)

        # Correction la géométrie (topologie)
        topologyCorrections(connection, table_output_name)

        # Récupération de la base du fichier vecteur de sortie (et déconnexion de la base de données, pour éviter les conflits d'accès)
        closeConnection(connection)
        exportVectorByOgr2ogr(database_postgis, vector_output, table_output_name, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema=schema_postgis, format_type='ESRI Shapefile')

    # Suppression des fichiers intermédiaires
    if not save_results_intermediate:
        dropDatabase(database_postgis, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number))

    print(endC)
    print(bold + green + "## END : VERIFIE CORRECT VECTORS" + endC)
    print(endC)

    # Mise à jour du Log
    ending_event = "verificationCorrection() :  Verifie and correct vector ending : "
    timeLine(path_time_log,ending_event)

    return

###########################################################################################################################################
# MISE EN PLACE DU PARSER                                                                                                                 #
###########################################################################################################################################

# Code executé seulement dans le cas ou le script est lancé depuis une ligne de commande
# Il n'est pas executé lors d'un import ProductOcsVerificationCorrectionSQL.py
# Exemple de lancement en ligne de commande:
# python ProductOcsVerificationCorrectionSQL.py -c /mnt/Data/gilles.fouvet/RA/Haute-Savoie/Global/Preparation/Study_Boundaries/DEP74.SHP -vl /mnt/Data/gilles.fouvet/RA/Haute-Savoie_500m/Global/Resultats/Vecteur/Sauvegarde_500m2/Haute-Savoie_Couverture_Apres_PT_Directs_et_Indirects_clnd_500m2_cut.shp /mnt/Data/gilles.fouvet/RA/Haute-Savoie_200m/Global/Resultats/Vecteur/Sauvegarde_200m2/Haute-Savoie_Couverture_Apres_PT_Directs_et_Indirects_clnd_200m2_cut.shp -vol /mnt/Data/gilles.fouvet/RA/Haute-Savoie_500m/Global/Resultats/Vecteur/Sauvegarde_500m2/Haute-Savoie_Couverture_Apres_PT_Directs_et_Indirects_clnd_500m2_clean.shp /mnt/Data/gilles.fouvet/RA/Haute-Savoie_200m/Global/Resultats/Vecteur/Sauvegarde_200m2/Haute-Savoie_Couverture_Apres_PT_Directs_et_Indirects_clnd_200m2_clean.shp -log /mnt/Data/gilles.fouvet/RA/Haute-Savoie_SansTunnel/FichierHaute-Savoie.log -sav
def main(gui=False):

    # Définition des différents paramètres du parser
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,  prog="ProductOcsVerificationCorrectionSQL", description="\
    Info : Cutting list of raster and vector file by vector file. \n\
    Objectif : Découper des fichiers raster et vecteurs. \n\
    Example : python ProductOcsVerificationCorrectionSQL.py \n\
                                            -c  /mnt/Data/gilles.fouvet/RA/Haute-Savoie/Global/Preparation/Study_Boundaries/DEP74.SHP \n\
                                            -vl /mnt/Data/gilles.fouvet/RA/Haute-Savoie_500m/Global/Resultats/Vecteur/Sauvegarde_500m2/Haute-Savoie_Couverture_Apres_PT_Directs_et_Indirects_clnd_500m2_cut.shp \n\
                                                /mnt/Data/gilles.fouvet/RA/Haute-Savoie_200m/Global/Resultats/Vecteur/Sauvegarde_200m2/Haute-Savoie_Couverture_Apres_PT_Directs_et_Indirects_clnd_200m2_cut.shp \n\
                                            -vol /mnt/Data/gilles.fouvet/RA/Haute-Savoie_500m/Global/Resultats/Vecteur/Sauvegarde_500m2/Haute-Savoie_Couverture_Apres_PT_Directs_et_Indirects_clnd_500m2_clean.shp \n\
                                                /mnt/Data/gilles.fouvet/RA/Haute-Savoie_200m/Global/Resultats/Vecteur/Sauvegarde_200m2/Haute-Savoie_Couverture_Apres_PT_Directs_et_Indirects_clnd_200m2_clean.shp \n\
                                            -log /mnt/Data/gilles.fouvet/RA/Haute-Savoie_SansTunnel/FichierHaute-Savoie.log")
    parser.add_argument('-c','--vector_ref',default="",help="Vector input contain the vector emprise reference.", type=str, required=True)
    parser.add_argument('-vl','--vectors_input_list',default="",nargs="+",help="List input vectors to verifie.", type=str, required=True)
    parser.add_argument('-vol','--vectors_output_list',default="",nargs="+",help="List output clean vectors.", type=str, required=True)
    parser.add_argument('-epsg','--epsg', default=2154,help="EPSG code projection.", type=int, required=False)
    parser.add_argument('-pe','--project_encoding', default="latin1",help="Project encoding.", type=str, required=False)
    parser.add_argument('-serv','--server_postgis', default="localhost",help="Postgis serveur name or ip.", type=str, required=False)
    parser.add_argument('-port','--port_number', default=5432,help="Postgis port number.", type=int, required=False)
    parser.add_argument('-user','--user_postgis', default="postgres",help="Postgis user name.", type=str, required=False)
    parser.add_argument('-pwd','--password_postgis', default="postgres",help="Postgis password user.", type=str, required=False)
    parser.add_argument('-db','--database_postgis', default="ocs_verification",help="Postgis database name.", type=str, required=False)
    parser.add_argument('-sch','--schema_postgis', default="public",help="Postgis schema name.", type=str, required=False)
    parser.add_argument('-log','--path_time_log',default="",help="Name of log", type=str, required=False)
    parser.add_argument('-sav','--save_results_inter',action='store_true',default=False,help="Save or delete intermediate result after the process. By default, False", required=False)
    parser.add_argument('-now','--overwrite',action='store_false',default=True,help="Overwrite files with same names. By default, True", required=False)
    parser.add_argument('-debug','--debug',default=3,help="Option : Value of level debug trace, default : 3 ",type=int, required=False)
    args = displayIHM(gui, parser)

    # RECUPERATION DES ARGUMENTS

    # Récupération du vecteur de référence
    if args.vector_ref != None :
        vector_ref = args.vector_ref
        if not os.path.isfile(vector_ref):
            raise NameError (cyan + "ProductOcsVerificationCorrectionSQL : " + bold + red  + "File %s not existe!" %(vector_ref) + endC)

    # Récupération des vecteurs d'entrées
    if args.vectors_input_list != None:
        vectors_input_list = args.vectors_input_list
        for vector_input in vectors_input_list :
            if not os.path.isfile(vector_input):
                raise NameError (cyan + "ProductOcsVerificationCorrectionSQL : " + bold + red  + "File %s not existe!" %(vector_input) + endC)

    # Récupération des vecteurs de sorties
    if args.vectors_output_list != None:
        vectors_output_list = args.vectors_output_list

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

    # Récupération du nom du fichier log
    if args.path_time_log!= None:
        path_time_log = args.path_time_log

    # Récupération de l'option de sauvegarde des fichiers temporaires
    if args.save_results_inter != None:
        save_results_intermediate = args.save_results_inter

    # Récupération de l'option écrasement
    if args.overwrite!= None:
        overwrite = args.overwrite

    # Récupération de l'option niveau de debug
    if args.debug!= None:
        global debug
        debug = args.debug

    if debug >= 3:
        print(bold + green + "ProductOcsVerificationCorrectionSQL : Variables dans le parser" + endC)
        print(cyan + "ProductOcsVerificationCorrectionSQL : " + endC + "vector_ref : " + str(vector_ref) + endC)
        print(cyan + "ProductOcsVerificationCorrectionSQL : " + endC + "vectors_input_list : " + str(vectors_input_list) + endC)
        print(cyan + "ProductOcsVerificationCorrectionSQL : " + endC + "vectors_output_list : " + str(vectors_output_list) + endC)
        print(cyan + "ProductOcsVerificationCorrectionSQL : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "ProductOcsVerificationCorrectionSQL : " + endC + "project_encoding : " + str(project_encoding) + endC)
        print(cyan + "ProductOcsVerificationCorrectionSQL : " + endC + "server_postgis : " + str(server_postgis) + endC)
        print(cyan + "ProductOcsVerificationCorrectionSQL : " + endC + "port_number : " + str(port_number) + endC)
        print(cyan + "ProductOcsVerificationCorrectionSQL : " + endC + "user_postgis : " + str(user_postgis) + endC)
        print(cyan + "ProductOcsVerificationCorrectionSQL : " + endC + "password_postgis : " + str(password_postgis) + endC)
        print(cyan + "ProductOcsVerificationCorrectionSQL : " + endC + "database_postgis : " + str(database_postgis) + endC)
        print(cyan + "ProductOcsVerificationCorrectionSQL : " + endC + "schema_postgis : " + str(schema_postgis) + endC)
        print(cyan + "ProductOcsVerificationCorrectionSQL : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "ProductOcsVerificationCorrectionSQL : " + endC + "save_results_inter : " + str(save_results_intermediate) + endC)
        print(cyan + "ProductOcsVerificationCorrectionSQL : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "ProductOcsVerificationCorrectionSQL : " + endC + "debug : " + str(debug) + endC)

    # EXECUTION DE LA FONCTION
    # Si les dossiers de sorties n'existent pas, on les crées
    for vector_output in vectors_output_list:
        if not os.path.isdir(os.path.dirname(vector_output)):
            os.makedirs(os.path.dirname(vector_output))

    # execution de la fonction pour une image
    verificationCorrection(vector_ref, vectors_input_list, vectors_output_list, epsg, project_encoding, server_postgis, port_number, user_postgis, password_postgis, database_postgis, schema_postgis, path_time_log, save_results_intermediate, overwrite)

# ================================================

if __name__ == '__main__':
  main(gui=False)
