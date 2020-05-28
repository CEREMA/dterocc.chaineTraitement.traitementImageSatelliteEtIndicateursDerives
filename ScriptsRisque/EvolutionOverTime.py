#!/usr/bin/env python
# -*- coding: utf-8 -*-

########################################################################
#                                                                      #
#    Copyright (©) CEREMA/DTerSO/DALETT/SCGSI - All rights reserved    #
#                                                                      #
########################################################################

'''
Nom de l'objet : EvolutionOverTime.py
Description :
    Objectif : étudier l'évolution d'un territoire dans le temps
    Remarque : compare l'état à t0 avec autant de t0+x que l'on souhaite, en terme de surface et/ou de taux d'évolution

-----------------
Outils utilisés :
 -

------------------------------
Historique des modifications :
 - 06/06/2019 : création

-----------------------
A réfléchir / A faire :
 -
'''

# Import des bibliothèques Python
from __future__ import print_function
import os, argparse
from Lib_display import bold,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_file import cleanTempData, deleteDir, removeFile, removeVectorFile
from Lib_log import timeLine
from Lib_postgis import createDatabase, openConnection, importVectorByOgr2ogr, executeQuery, exportVectorByOgr2ogr, closeConnection, dropDatabase
from Lib_text import appendTextFileCR
from Lib_vector import cutVector, getAttributeNameList, renameFieldsVector
from CrossingVectorRaster import statisticsVectorRaster

# Niveau de debug (variable globale)
debug = 3

########################################################################
# FONCTION soilOccupationChange()                                      #
########################################################################
# ROLE :
#     Cartographie des évolutions (positives et négatives) de l'OCS par parcelle
#
# ENTREES DE LA FONCTION :
#     input_plot_vector : fichier parcellaire en entrée (en format vecteur)
#     output_plot_vector : fichier parcellaire en sortie (en format vecteur)
#     footprint_vector : fichier emprise en entrée (en format vecteur)
#     input_t0_file : fichier OCS à t0 en entrée (en format raster)
#     input_tx_files_list : liste des fichier OCS à t0+x en entrée (en format raster)
#     evolutions_list : liste des évolutions à quantifier (taux et/ou surface d'une classe). Par défaut : ['11000:10:50:and', '12000:10:50:and', '21000:10:50:and', '22000:10:50:and', '23000:10:50:and']
#     class_label_dico : dictionnaire des classes OCS. Par défaut : {11000:'Bati', 12000:'Route', 21000:'SolNu', 22000:'Eau', 23000:'Vegetation'}
#     epsg : code epsg du système de projection. Par défaut : 2154
#     no_data_value : valeur NoData des pixels des fichiers raster. Par défaut : 0
#     format_raster : format des fichiers raster. Par défaut : 'GTiff'
#     format_vector : format des fichiers vecteur. Par défaut : 'ESRI Shapefile'
#     extension_raster : extension des fichiers raster. Par défaut : '.tif'
#     extension_vector : extension des fichiers vecteur. Par défaut : '.shp'
#     postgis_ip_host : nom du serveur PostGIS. Par défaut : 'localhost'
#     postgis_num_port : numéro de port du serveur PostGIS. Par défaut : 5432
#     postgis_user_name : nom d'utilisateur PostGIS. Par défaut : 'postgres'
#     postgis_password : mot de passe de l'utilisateur PostGIS. Par défaut : 'postgres'
#     postgis_database_name : nom de la base PostGIS. Par défaut : 'database'
#     postgis_schema_name : nom du schéma dans la base PostGIS. Par défaut : 'public'
#     postgis_encoding : l'encodage des fichiers pour l'import de vecteurs dans PostGIS. Par défaut : 'latin1'
#     path_time_log : fichier log de sortie, par défaut vide
#     save_results_intermediate : fichiers temporaires conservés, par défaut = False
#     overwrite : écrase si un fichier existant a le même nom qu'un fichier de sortie, par défaut = True
#
# SORTIES DE LA FONCTION :
#     N.A.

def soilOccupationChange(input_plot_vector, output_plot_vector, footprint_vector, input_t0_file, input_tx_files_list, evolutions_list=['11000:10:50:and', '12000:10:50:and', '21000:10:50:and', '22000:10:50:and', '23000:10:50:and'], class_label_dico={11000:'Bati', 12000:'Route', 21000:'SolNu', 22000:'Eau', 23000:'Vegetation'}, epsg=2154, no_data_value=0, format_raster='GTiff', format_vector='ESRI Shapefile', extension_raster='.tif', extension_vector='.shp', postgis_ip_host='localhost', postgis_num_port=5432, postgis_user_name='postgres', postgis_password='postgres', postgis_database_name='database', postgis_schema_name='public', postgis_encoding='latin1', path_time_log='', save_results_intermediate=False, overwrite=True):

    if debug >= 3:
        print('\n' + bold + green + "Evolution de l'OCS par parcelle - Variables dans la fonction :" + endC)
        print(cyan + "    soilOccupationChange() : " + endC + "input_plot_vector : " + str(input_plot_vector) + endC)
        print(cyan + "    soilOccupationChange() : " + endC + "output_plot_vector : " + str(output_plot_vector) + endC)
        print(cyan + "    soilOccupationChange() : " + endC + "footprint_vector : " + str(footprint_vector) + endC)
        print(cyan + "    soilOccupationChange() : " + endC + "input_t0_file : " + str(input_t0_file) + endC)
        print(cyan + "    soilOccupationChange() : " + endC + "input_tx_files_list : " + str(input_tx_files_list) + endC)
        print(cyan + "    soilOccupationChange() : " + endC + "evolutions_list : " + str(evolutions_list) + endC)
        print(cyan + "    soilOccupationChange() : " + endC + "class_label_dico : " + str(class_label_dico) + endC)
        print(cyan + "    soilOccupationChange() : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "    soilOccupationChange() : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "    soilOccupationChange() : " + endC + "format_raster : " + str(format_raster) + endC)
        print(cyan + "    soilOccupationChange() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "    soilOccupationChange() : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "    soilOccupationChange() : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "    soilOccupationChange() : " + endC + "postgis_ip_host : " + str(postgis_ip_host) + endC)
        print(cyan + "    soilOccupationChange() : " + endC + "postgis_num_port : " + str(postgis_num_port) + endC)
        print(cyan + "    soilOccupationChange() : " + endC + "postgis_user_name : " + str(postgis_user_name) + endC)
        print(cyan + "    soilOccupationChange() : " + endC + "postgis_password : " + str(postgis_password) + endC)
        print(cyan + "    soilOccupationChange() : " + endC + "postgis_database_name : " + str(postgis_database_name) + endC)
        print(cyan + "    soilOccupationChange() : " + endC + "postgis_schema_name : " + str(postgis_schema_name) + endC)
        print(cyan + "    soilOccupationChange() : " + endC + "postgis_encoding : " + str(postgis_encoding) + endC)
        print(cyan + "    soilOccupationChange() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "    soilOccupationChange() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "    soilOccupationChange() : " + endC + "overwrite : " + str(overwrite) + endC + '\n')

    # Définition des constantes
    EXTENSION_TEXT = '.txt'
    SUFFIX_TEMP = '_temp'
    SUFFIX_CUT = '_cut'
    AREA_FIELD = 'st_area'
    GEOM_FIELD = 'geom'

    # Mise à jour du log
    starting_event = "soilOccupationChange() : Début du traitement : "
    timeLine(path_time_log, starting_event)

    print(cyan + "soilOccupationChange() : " + bold + green + "DEBUT DES TRAITEMENTS" + endC + '\n')

    # Définition des variables 'basename'
    output_plot_basename = os.path.splitext(os.path.basename(output_plot_vector))[0]

    # Définition des variables temp
    temp_directory = os.path.dirname(output_plot_vector) + os.sep + output_plot_basename + SUFFIX_TEMP
    plot_vector_cut = temp_directory + os.sep + output_plot_basename + SUFFIX_CUT + extension_vector

    # Définition des variables PostGIS
    plot_table = output_plot_basename.lower()

    # Fichier .txt associé au fichier vecteur de sortie, sur la liste des évolutions quantifiées
    output_evolution_text_file = os.path.splitext(output_plot_vector)[0] + EXTENSION_TEXT

    # Nettoyage des traitements précédents
    if debug >= 3:
        print(cyan + "soilOccupationChange() : " + endC + "Nettoyage des traitements précédents." + endC + '\n')
    removeVectorFile(output_plot_vector, format_vector=format_vector)
    removeFile(output_evolution_text_file)
    cleanTempData(temp_directory)
    dropDatabase(postgis_database_name, user_name=postgis_user_name, password=postgis_password, ip_host=postgis_ip_host, num_port=postgis_num_port, schema_name=postgis_schema_name)

    #############
    # Etape 0/3 # Préparation des traitements
    #############

    print(cyan + "soilOccupationChange() : " + bold + green + "ETAPE 0/3 - Début de la préparation des traitements." + endC + '\n')

    # Découpage du parcellaire à la zone d'étude
    cutVector(footprint_vector, input_plot_vector, plot_vector_cut, overwrite=overwrite, format_vector=format_vector)

    # Récupération du nom des champs dans le fichier source (pour isoler les champs nouvellement créés par la suite, et les renommer)
    attr_names_list_origin = getAttributeNameList(plot_vector_cut, format_vector=format_vector)
    new_attr_names_list_origin = attr_names_list_origin

    # Préparation de PostGIS
    createDatabase(postgis_database_name, user_name=postgis_user_name, password=postgis_password, ip_host=postgis_ip_host, num_port=postgis_num_port, schema_name=postgis_schema_name)

    print(cyan + "soilOccupationChange() : " + bold + green + "ETAPE 0/3 - Fin de la préparation des traitements." + endC + '\n')

    #############
    # Etape 1/3 # Calcul des statistiques à t0
    #############

    print(cyan + "soilOccupationChange() : " + bold + green + "ETAPE 1/3 - Début du calcul des statistiques à t0." + endC + '\n')

    # Statistiques OCS par parcelle
    statisticsVectorRaster(input_t0_file, plot_vector_cut, "", 1, True, False, False, [], [], class_label_dico, path_time_log, clean_small_polygons=True, format_vector=format_vector, save_results_intermediate=save_results_intermediate, overwrite=overwrite)

    # Récupération du nom des champs dans le fichier parcellaire (avec les champs créés précédemment dans CVR)
    attr_names_list_t0 = getAttributeNameList(plot_vector_cut, format_vector=format_vector)

    # Isolement des nouveaux champs issus du CVR
    fields_name_list  = []
    for attr_name in attr_names_list_t0:
        if attr_name not in attr_names_list_origin:
            fields_name_list.append(attr_name)

    # Gestion des nouveaux noms des champs issus du CVR
    new_fields_name_list  = []
    for field_name in fields_name_list:
        new_field_name = 't0_' + field_name
        new_field_name = new_field_name[:10]
        new_fields_name_list.append(new_field_name)
        new_attr_names_list_origin.append(new_field_name)

    # Renommage des champs issus du CVR, pour le relancer par la suite sur d'autres dates
    renameFieldsVector(plot_vector_cut, fields_name_list, new_fields_name_list, format_vector=format_vector)

    print(cyan + "soilOccupationChange() : " + bold + green + "ETAPE 1/3 - Fin du calcul des statistiques à t0." + endC + '\n')

    #############
    # Etape 2/3 # Calculs des statistiques à t0+x
    #############

    print(cyan + "soilOccupationChange() : " + bold + green + "ETAPE 2/3 - Début des calculs des statistiques à t0+x." + endC + '\n')

    len_tx = len(input_tx_files_list)
    tx = 1

    # Boucle sur les fichiers d'entrés à t0+x
    for input_tx_file in input_tx_files_list:
        if debug >= 3:
            print(cyan + "soilOccupationChange() : " + endC + bold + "Calcul des statistiques à t%s / %s." % (tx, len_tx) + endC + '\n')

        # Statistiques OCS par parcelle
        statisticsVectorRaster(input_tx_file, plot_vector_cut, "", 1, True, False, False, [], [], class_label_dico, path_time_log, clean_small_polygons=True, format_vector=format_vector, save_results_intermediate=save_results_intermediate, overwrite=overwrite)

        # Récupération du nom des champs dans le fichier parcellaire (avec les champs créés précédemment dans CVR)
        attr_names_list_tx = getAttributeNameList(plot_vector_cut, format_vector=format_vector)

        # Isolement des nouveaux champs issus du CVR
        fields_name_list  = []
        for attr_name in attr_names_list_tx:
            if attr_name not in new_attr_names_list_origin:
                fields_name_list.append(attr_name)

        # Gestion des nouveaux noms des champs issus du CVR
        new_fields_name_list  = []
        for field_name in fields_name_list:
            new_field_name = 't%s_' % tx + field_name
            new_field_name = new_field_name[:10]
            new_fields_name_list.append(new_field_name)
            new_attr_names_list_origin.append(new_field_name)

        # Renommage des champs issus du CVR, pour le relancer par la suite sur d'autres dates
        renameFieldsVector(plot_vector_cut, fields_name_list, new_fields_name_list, format_vector=format_vector)

        tx += 1

    print(cyan + "soilOccupationChange() : " + bold + green + "ETAPE 2/3 - Fin des calculs des statistiques à t0+x." + endC + '\n')

    #############
    # Etape 3/3 # Caractérisation des changements
    #############

    print(cyan + "soilOccupationChange() : " + bold + green + "ETAPE 3/3 - Début de la caractérisation des changements." + endC + '\n')

    len_tx = len(input_tx_files_list)

    # Pré-traitements dans PostGIS
    plot_table = importVectorByOgr2ogr(postgis_database_name, plot_vector_cut, plot_table, user_name=postgis_user_name, password=postgis_password, ip_host=postgis_ip_host, num_port=postgis_num_port, schema_name=postgis_schema_name, epsg=epsg, codage=postgis_encoding)
    connection = openConnection(postgis_database_name, user_name=postgis_user_name, password=postgis_password, ip_host=postgis_ip_host, num_port=postgis_num_port, schema_name=postgis_schema_name)

    # Requête SQL pour le calcul de la surface des parcelles
    sql_query = "ALTER TABLE %s ADD COLUMN %s REAL;\n" % (plot_table, AREA_FIELD)
    sql_query += "UPDATE %s SET %s = ST_Area(%s);\n" % (plot_table, AREA_FIELD, GEOM_FIELD)

    # Boucle sur les dates à comparer (t vs t+1)
    temp_field = 1
    for idx in range(0, len_tx):
        idx_bef = str(idx)
        idx_aft = str(idx+1)

        # Boucle sur les évolutions à quantifier
        for evolution in evolutions_list:
            evolution_split = evolution.split(':')
            label = int(evolution_split[0])
            evol = abs(int(evolution_split[1]))
            evol_s = abs(int(evolution_split[2]))
            combi = evolution_split[3]
            class_name = class_label_dico[label]
            def_evo_field = "def_evo_%s" % str(temp_field)
            if evol != 0 or evol_s != 0:

                # Gestion de l'évolution via le taux
                evol_str = str(evol) + ' %'
                evo_field = "evo_%s" % str(temp_field)
                t0_field = 't%s_' % idx_bef + class_name.lower()[:7]
                t1_field = 't%s_' % idx_aft + class_name.lower()[:7]

                # Gestion de l'évolution via la surface
                evol_s_str = str(evol_s) + ' m²'
                evo_s_field = "evo_s_%s" % str(temp_field)
                t0_s_field = 't%s_s_' % idx_bef + class_name.lower()[:5]
                t1_s_field = 't%s_s_' % idx_aft + class_name.lower()[:5]

                # Requête SQL pour le calcul brut de l'évolution
                sql_query += "ALTER TABLE %s ADD COLUMN %s REAL;\n" % (plot_table, evo_field)
                sql_query += "UPDATE %s SET %s = %s - %s;\n" % (plot_table, evo_field, t1_field, t0_field)
                sql_query += "ALTER TABLE %s ADD COLUMN %s REAL;\n" % (plot_table, evo_s_field)
                sql_query += "UPDATE %s SET %s = %s - %s;\n" % (plot_table, evo_s_field, t1_s_field, t0_s_field)
                sql_query += "ALTER TABLE %s ADD COLUMN %s VARCHAR;\n" % (plot_table, def_evo_field)
                sql_query += "UPDATE %s SET %s = 't%s a t%s - %s - aucune evolution';\n" % (plot_table, def_evo_field, idx_bef, idx_aft, class_name)

                # Si évolution à la fois via taux et via surface
                if evol != 0 and evol_s != 0:
                    text_evol = "taux à %s" % evol_str
                    if combi == 'and':
                        text_evol += " ET "
                        sql_query += "UPDATE %s SET %s = 't%s a t%s - %s - evolution positive' WHERE %s >= %s AND %s >= %s;\n" % (plot_table, def_evo_field, idx_bef, idx_aft, class_name, evo_field, evol, evo_s_field, evol_s)
                        sql_query += "UPDATE %s SET %s = 't%s a t%s - %s - evolution negative' WHERE %s <= -%s AND %s <= -%s;\n" % (plot_table, def_evo_field, idx_bef, idx_aft, class_name, evo_field, evol, evo_s_field, evol_s)
                    elif combi == 'or':
                        text_evol += " OU "
                        sql_query += "UPDATE %s SET %s = 't%s a t%s - %s - evolution positive' WHERE %s >= %s OR %s >= %s;\n" % (plot_table, def_evo_field, idx_bef, idx_aft, class_name, evo_field, evol, evo_s_field, evol_s)
                        sql_query += "UPDATE %s SET %s = 't%s a t%s - %s - evolution negative' WHERE %s <= -%s OR %s <= -%s;\n" % (plot_table, def_evo_field, idx_bef, idx_aft, class_name, evo_field, evol, evo_s_field, evol_s)
                    text_evol += "surface à %s" % evol_s_str

                # Si évolution uniquement via taux
                elif evol != 0:
                    text_evol = "taux à %s" % evol_str
                    sql_query += "UPDATE %s SET %s = 't%s a t%s - %s - evolution positive' WHERE %s >= %s;\n" % (plot_table, def_evo_field, idx_bef, idx_aft, class_name, evo_field, evol)
                    sql_query += "UPDATE %s SET %s = 't%s a t%s - %s - evolution negative' WHERE %s <= -%s;\n" % (plot_table, def_evo_field, idx_bef, idx_aft, class_name, evo_field, evol)

                # Si évolution uniquement via surface
                elif evol_s != 0:
                    text_evol = "surface à %s" % evol_s_str
                    sql_query += "UPDATE %s SET %s = 't%s a t%s - %s - evolution positive' WHERE %s >= %s;\n" % (plot_table, def_evo_field, idx_bef, idx_aft, class_name, evo_s_field, evol_s)
                    sql_query += "UPDATE %s SET %s = 't%s a t%s - %s - evolution negative' WHERE %s <= -%s;\n" % (plot_table, def_evo_field, idx_bef, idx_aft, class_name, evo_s_field, evol_s)

                # Ajout des paramètres de l'évolution quantifiée (temporalités, classe, taux/surface) au fichier texte de sortie
                text = "%s --> évolution entre t%s et t%s, pour la classe '%s' (label %s) :\n" % (def_evo_field, idx_bef, idx_aft, class_name, label)
                text += "    %s --> taux d'évolution brut" % evo_field + " (%)\n"
                text += "    %s --> surface d'évolution brute" % evo_s_field + " (m²)\n"
                text += "Evolution quantifiée : %s\n" % text_evol
                appendTextFileCR(output_evolution_text_file, text)
                temp_field += 1

    # Traitements SQL de l'évolution des classes OCS
    executeQuery(connection, sql_query)
    closeConnection(connection)
    exportVectorByOgr2ogr(postgis_database_name, output_plot_vector, plot_table, user_name=postgis_user_name, password=postgis_password, ip_host=postgis_ip_host, num_port=postgis_num_port, schema_name=postgis_schema_name, format_type=format_vector)

    print(cyan + "soilOccupationChange() : " + bold + green + "ETAPE 3/3 - Fin de la caractérisation des changements." + endC + '\n')

    # Suppression des fichiers temporaires
    if not save_results_intermediate:
        if debug >= 3:
            print(cyan + "soilOccupationChange() : " + endC + "Suppression des fichiers temporaires." + endC + '\n')
        deleteDir(temp_directory)
        dropDatabase(postgis_database_name, user_name=postgis_user_name, password=postgis_password, ip_host=postgis_ip_host, num_port=postgis_num_port, schema_name=postgis_schema_name)

    print(cyan + "soilOccupationChange() : " + bold + green + "FIN DES TRAITEMENTS" + endC + '\n')

    # Mise à jour du log
    ending_event = "soilOccupationChange() : Fin du traitement : "
    timeLine(path_time_log, ending_event)

    return

#############################################################################################################################
################################################## Mise en place du parser ##################################################
#############################################################################################################################

def main(gui=False):
    parser = argparse.ArgumentParser(prog = "Evolution du territoire dans le temps", description = "\
    Etude de l'évolution d'un territoire entre différentes dates (évolution de l'OCS). \n\
    Exemple : python3 -m EvolutionOverTime.py -in /mnt/RAM_disk/BD_Parcellaire.shp \n\
                                              -out /mnt/RAM_disk/EvolutionOverTime.shp \n\
                                              -emp /mnt/RAM_disk/zone_etude.shp \n\
                                              -it0 /mnt/RAM_disk/OCS_sat_t0.tif \n\
                                              -itxl /mnt/RAM_disk/OCS_sat_t1.tif /mnt/RAM_disk/OCS_sat_t2.tif /mnt/RAM_disk/OCS_sat_t3.tif")

    parser.add_argument('-in', '--input_plot_vector', default="", type=str, required=True, help="Input plot vector file.")
    parser.add_argument('-out', '--output_plot_vector', default="", type=str, required=True, help="Output plot vector file.")
    parser.add_argument('-emp', '--footprint_vector', default="", type=str, required=True, help="Input footprint vector file.")
    parser.add_argument('-it0', '--input_t0_file', default="", type=str, required=True, help="Input soil occupation mapping raster file, at t0.")
    parser.add_argument('-itxl', '--input_tx_files_list', nargs="+", default=[], type=str, required=True, help="List of input soil occupation mapping raster(s) file(s), at t0+x.")
    parser.add_argument('-evol', '--evolutions_list', nargs="+", default=['11000:10:50:and', '12000:10:50:and', '21000:10:50:and', '22000:10:50:and', '23000:10:50:and'], type=str, required=False, help="List of rates and/or surfaces evolutions for a specific soil occupation class (class_label:rate_evolution:surface_evolution:rate_surface_combination). If 0 for 'rate_evolution' or 'surface_evolution', rate or surface no taking into consideration. 'rate_surface_combination' must be and/or (use if 'rate_evolution' and 'surface_evolution' not 0). Default: '11000:10:50:and 12000:10:50:and 21000:10:50:and 22000:10:50:and 23000:10:50:and'.")
    parser.add_argument('-cld', '--class_label_dico', nargs="+", default=['11000:Bati', '12000:Route', '21000:SolNu', '22000:Eau', '23000:Vegetation'], type=str, required=False, help="List of pixel values with their related soil occupation class (label:class). Default: '11000:Bati 12000:Route 21000:SolNu 22000:Eau 23000:Vegetation'.")
    parser.add_argument('-epsg', '--epsg', default=2154, type=int, required=False, help="Projection of the output file. Default: 2154.")
    parser.add_argument('-ndv', '--no_data_value', default=0, type=int, required=False, help="Value of the NoData pixel. Default: 0.")
    parser.add_argument('-raf', '--format_raster', default="GTiff", type=str, required=False, help="Format of raster file. Default: 'GTiff'.")
    parser.add_argument('-vef', '--format_vector', default="ESRI Shapefile", type=str, required=False, help="Format of vector file. Default: 'ESRI Shapefile'.")
    parser.add_argument('-rae', '--extension_raster', default=".tif", type=str, required=False, help="Extension file for raster file. Default: '.tif'.")
    parser.add_argument('-vee', '--extension_vector', default=".shp", type=str, required=False, help="Extension file for vector file. Default: '.shp'.")
    parser.add_argument('-pgh', '--postgis_ip_host', default="localhost", type=str, required=False, help="PostGIS server name or IP adress. Default: 'localhost'.")
    parser.add_argument('-pgp', '--postgis_num_port', default=5432, type=int, required=False, help="PostGIS port number. Default: '5432'.")
    parser.add_argument('-pgu', '--postgis_user_name', default="postgres", type=str, required=False, help="PostGIS user name. Default: 'postgres'.")
    parser.add_argument('-pgw', '--postgis_password', default="postgres", type=str, required=False, help="PostGIS user password. Default: 'postgres'.")
    parser.add_argument('-pgd', '--postgis_database_name', default="database", type=str, required=False, help="PostGIS database name. Default: 'database'.")
    parser.add_argument('-pgs', '--postgis_schema_name', default="public", type=str, required=False, help="PostGIS schema name. Default: 'public'.")
    parser.add_argument('-pge', '--postgis_encoding', default="latin1", type=str, required=False, help="PostGIS encoding for vector import. Default: 'latin1'.")
    parser.add_argument('-log', '--path_time_log', default="", type=str, required=False, help="Option: Name of log. Default, no log file.")
    parser.add_argument('-sav', '--save_results_intermediate', action='store_true', default=False, required=False, help="Option: Save intermediate result after the process. Default, False.")
    parser.add_argument('-now', '--overwrite', action='store_false', default=True, required=False, help="Option: Overwrite files with same names. Default, True.")
    parser.add_argument('-debug', '--debug', default=3, type=int, required=False, help="Option: Value of level debug trace. Default, 3.")
    args = displayIHM(gui, parser)

    # Récupération du fichier parcellaire d'entrée
    if args.input_plot_vector != None:
        input_plot_vector = args.input_plot_vector
        if not os.path.isfile(input_plot_vector):
            raise NameError (cyan + "EvolutionOverTime: " + bold + red  + "File %s not exists (input_plot_vector)." % input_plot_vector + endC)

    # Récupération du fichier parcellaire de sortie
    if args.output_plot_vector != None:
        output_plot_vector = args.output_plot_vector

    # Récupération du fichier d'emprise
    if args.footprint_vector != None:
        footprint_vector = args.footprint_vector
        if not os.path.isfile(footprint_vector):
            raise NameError (cyan + "EvolutionOverTime: " + bold + red  + "File %s not exists (footprint_vector)." % footprint_vector + endC)

    # Récupération de la classif OCS à t0
    if args.input_t0_file != None:
        input_t0_file = args.input_t0_file
        if not os.path.isfile(input_t0_file):
            raise NameError (cyan + "EvolutionOverTime: " + bold + red  + "File %s not exists (input_t0_file)." % input_t0_file + endC)

    # Récupération de la liste des classif OCS à t0+x
    if args.input_tx_files_list != None:
        input_tx_files_list = args.input_tx_files_list
        if input_tx_files_list != []:
            for input_tx_file in input_tx_files_list:
                if not os.path.isfile(input_tx_file):
                    raise NameError (cyan + "EvolutionOverTime: " + bold + red  + "File %s not exists (input_tx_files_list)." % input_tx_file + endC)

    # Récupération du paramètre des évolutions à quantifier
    if args.evolutions_list != None:
        evolutions_list = args.evolutions_list

    # Création du dictionaire reliant les classes OCS à leur label
    class_label_dico = {}
    if args.class_label_dico != None and args.class_label_dico != {}:
        for class_label in args.class_label_dico:
            key = class_label.split(':')[0]
            value = class_label.split(':')[1]
            class_label_dico[int(key)] = value

    # Récupération des paramètres fichiers
    if args.epsg != None:
        epsg = args.epsg
    if args.no_data_value != None:
        no_data_value = args.no_data_value
    if args.format_raster != None:
        format_raster = args.format_raster
    if args.format_vector != None:
        format_vector = args.format_vector
    if args.extension_raster != None:
        extension_raster = args.extension_raster
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

    if os.path.isfile(output_plot_vector) and not overwrite:
        raise NameError (cyan + "EvolutionOverTime: " + bold + red  + "File %s already exists, and overwrite is not activated." % output_plot_vector + endC)

    if debug >= 3:
        print('\n' + bold + green + "Evolution du territoire dans le temps - Variables dans le parser :" + endC)
        print(cyan + "    EvolutionOverTime : " + endC + "input_plot_vector : " + str(input_plot_vector) + endC)
        print(cyan + "    EvolutionOverTime : " + endC + "output_plot_vector : " + str(output_plot_vector) + endC)
        print(cyan + "    EvolutionOverTime : " + endC + "footprint_vector : " + str(footprint_vector) + endC)
        print(cyan + "    EvolutionOverTime : " + endC + "input_t0_file : " + str(input_t0_file) + endC)
        print(cyan + "    EvolutionOverTime : " + endC + "input_tx_files_list : " + str(input_tx_files_list) + endC)
        print(cyan + "    EvolutionOverTime : " + endC + "evolutions_list : " + str(evolutions_list) + endC)
        print(cyan + "    EvolutionOverTime : " + endC + "class_label_dico : " + str(class_label_dico) + endC)
        print(cyan + "    EvolutionOverTime : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "    EvolutionOverTime : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "    EvolutionOverTime : " + endC + "format_raster : " + str(format_raster) + endC)
        print(cyan + "    EvolutionOverTime : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "    EvolutionOverTime : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "    EvolutionOverTime : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "    EvolutionOverTime : " + endC + "postgis_ip_host : " + str(postgis_ip_host) + endC)
        print(cyan + "    EvolutionOverTime : " + endC + "postgis_num_port : " + str(postgis_num_port) + endC)
        print(cyan + "    EvolutionOverTime : " + endC + "postgis_user_name : " + str(postgis_user_name) + endC)
        print(cyan + "    EvolutionOverTime : " + endC + "postgis_password : " + str(postgis_password) + endC)
        print(cyan + "    EvolutionOverTime : " + endC + "postgis_database_name : " + str(postgis_database_name) + endC)
        print(cyan + "    EvolutionOverTime : " + endC + "postgis_schema_name : " + str(postgis_schema_name) + endC)
        print(cyan + "    EvolutionOverTime : " + endC + "postgis_encoding : " + str(postgis_encoding) + endC)
        print(cyan + "    EvolutionOverTime : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "    EvolutionOverTime : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "    EvolutionOverTime : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "    EvolutionOverTime : " + endC + "debug : " + str(debug) + endC + '\n')

    # Création du dossier de sortie, s'il n'existe pas
    if not os.path.isdir(os.path.dirname(output_plot_vector)):
        os.makedirs(os.path.dirname(output_plot_vector))

    # EXECUTION DE LA FONCTION
    soilOccupationChange(input_plot_vector, output_plot_vector, footprint_vector, input_t0_file, input_tx_files_list, evolutions_list, class_label_dico, epsg, no_data_value, format_raster, format_vector, extension_raster, extension_vector, postgis_ip_host, postgis_num_port, postgis_user_name, postgis_password, postgis_database_name, postgis_schema_name, postgis_encoding, path_time_log, save_results_intermediate, overwrite)

if __name__ == '__main__':
    main(gui=False)

