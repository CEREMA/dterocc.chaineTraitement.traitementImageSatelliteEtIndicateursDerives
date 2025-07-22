#! /usr/bin/env pyt/hon
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT QUI CALCULE LA DISTANCE LA PLUS COURTE ENTRE CHAQUE POINT D'UN SHP ET DES LIGNES DANS UN AUTRE SHP                                 #
#                                                                                                                                           #
#############################################################################################################################################
"""
Nom de l'objet : DistanceTDCPointLine.py
Description :
-------------
Objectif : Convertir les polygones raster en vecteur nettoyer les petit polygones et fusion en un seul fichier vecteur

Date de creation : 29/08/2016
"""

from __future__ import print_function
import os, sys, argparse
from osgeo import ogr, osr
import numpy as np
from math import ceil
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_file import copyVectorFile
from Lib_text import writeTextFile, appendTextFile
from Lib_log import timeLine
from EvolvingDirectionTDC import evolvingDirectionTDC

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 3 : affichage maximum de commentaires lors de l'execution du script. Intermédiaire : affichage intermédiaire
debug = 3

###########################################################################################################################################
# FONCTION distanceTDCPointLine()                                                                                                         #
###########################################################################################################################################
def distanceTDCPointLine(input_points_shp, input_tdc_shp, output_dir, input_sea_points, evolution_column_name, path_time_log, server_postgis="localhost", user_postgis="postgres", password_postgis="postgres", database_postgis="db_buffer_tdc", schema_name="directionevolution", port_number=5432, epsg=2154, project_encoding = "UTF-8", format_vector="ESRI Shapefile", save_results_intermediate=True, overwrite=True):
    """
    # ROLE:
    #     calcule la distance la plus courte entre chaque point d'un shapefile et les lignes d'un autre. Résultat dans un fichier texte, et dans une copie du fichier point, avec une colonne "evolution" en plus
    #
    # ENTREES DE LA FONCTION :
    #     input_points_shp : Fichier contenant les points pour le calcul de distance
    #     input_tdc_shp : fichier contenant la ligne/le trait de côte pour le calcul de distance
    #     output_dir : le chemin du dossier de sortie pour les fichiers créés
    #     input_sea_points : shapefile contenant les points dans la mer pour l'identification du côté mer
    #     evolution_column_name : Nom de la colonne du fichier shape contenant l'évolution (distance et sens)
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
    #     Fichier vecteur point recopié avec une colonne distance (valeur absolue) et une colonne évolution (sens de l'évolution et distance) en plus
    #     Fichier texte contenant les points avec la distance et l'évolution
    #
    """

    # Mise à jour du Log
    starting_event = "distanceTDCPointLine() : Distance TDC Point Line starting : "
    timeLine(path_time_log,starting_event)

    if debug >= 3:
        print(bold + green + "Variables dans distanceTDCPointLine - Variables générales" + endC)
        print(cyan + "distanceTDCPointLine() : " + endC + "input_points_shp : " + str(input_points_shp) + endC)
        print(cyan + "distanceTDCPointLine() : " + endC + "input_tdc_shp : " + str(input_tdc_shp) + endC)
        print(cyan + "distanceTDCPointLine() : " + endC + "output_dir : " + str(output_dir) + endC)
        print(cyan + "distanceTDCPointLine() : " + endC + "input_sea_points : " + str(input_sea_points) + endC)
        print(cyan + "distanceTDCPointLine() : " + endC + "evolution_column_name : " + str(evolution_column_name) + endC)
        print(cyan + "distanceTDCPointLine() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "distanceTDCPointLine() : " + endC + "server_postgis : " + str(server_postgis) + endC)
        print(cyan + "distanceTDCPointLine() : " + endC + "user_postgis : " + str(user_postgis) + endC)
        print(cyan + "distanceTDCPointLine() : " + endC + "password_postgis : " + str(password_postgis) + endC)
        print(cyan + "distanceTDCPointLine() : " + endC + "database_postgis : " + str(database_postgis) + endC)
        print(cyan + "distanceTDCPointLine() : " + endC + "schema_name : " + str(schema_name) + endC)
        print(cyan + "distanceTDCPointLine() : " + endC + "port_number : " + str(port_number) + endC)
        print(cyan + "distanceTDCPointLine() : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "distanceTDCPointLine() : " + endC + "project_encoding : " + str(project_encoding) + endC)
        print(cyan + "distanceTDCPointLine() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "distanceTDCPointLine() : " + endC + "save_results_inter : " + str(save_results_intermediate) + endC)
        print(cyan + "distanceTDCPointLine() : " + endC + "overwrite : " + str(overwrite) + endC)

    print(bold + green + "## START : DistanceTDCPointLine" + endC)

    # Initialisation des constantes
    EXT_TEXT = ".txt"

    # Configuration du format vecteur
    driver = ogr.GetDriverByName(format_vector)
    # Création de la référence spatiale
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(epsg)

    # Constitution des noms
    ext_vect = os.path.splitext(os.path.split(input_points_shp)[1])[1]
    input_points_shp_name = os.path.splitext(os.path.split(input_points_shp)[1])[0]
    input_tdc_shp_name = os.path.splitext(os.path.split(input_tdc_shp)[1])[0]
    vector_output_points = output_dir + os.sep + "distance_" + input_points_shp_name + "_" + input_tdc_shp_name + ext_vect
    output_text_file = output_dir + os.sep + "distance_sens_evol_" + input_points_shp_name + "_" + input_tdc_shp_name + EXT_TEXT
    vector_output_points_sens = output_dir + os.sep + "distance_sens_evol_" + input_points_shp_name + "_" + input_tdc_shp_name + ext_vect

    ## Gestion des fichiers
    # Création du répertoire de sortie s'il n'existe pas déjà
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    # Suppression de la couche en sortie si elle existe déjà
    if os.path.exists(vector_output_points):
        driver.DeleteDataSource(vector_output_points)
    # Suppression de la couche en sortie si elle existe déjà
    if os.path.exists(vector_output_points_sens):
        driver.DeleteDataSource(vector_output_points_sens)

    ## Ouverture des fichiers existants
    # Ouverture de la couche points
    data_source_points_ref = driver.Open(input_points_shp, 0)
    input_layer_pts = data_source_points_ref.GetLayer()
    input_layer_pts_defn = input_layer_pts.GetLayerDefn()
    # Ouverture de la couche TDC
    data_source_tdc = driver.Open(input_tdc_shp, 0)
    input_layer_tdc = data_source_tdc.GetLayer(0)

    ## Création des fichiers de sortie
    # Création de la couche en sortie
    output_data_source = driver.CreateDataSource(vector_output_points)
    output_layer = output_data_source.CreateLayer(input_points_shp_name, srs, geom_type=ogr.wkbPoint)
    output_layer_defn = output_layer.GetLayerDefn()

    # Ajouter les champs du fichier d'entrée au shapefile de sortie
    for i in range(0, input_layer_pts_defn.GetFieldCount()):
        field_defn = input_layer_pts_defn.GetFieldDefn(i)
        output_layer.CreateField(field_defn)
    # Ajout du champ "distance" à la couche en sortie
    dist_field = ogr.FieldDefn("distance", ogr.OFTReal)
    output_layer.CreateField(dist_field)

    liste_all_distances = []
    liste_min_distances = []

    # Ajout des valeurs à la couche de sortie
    for i in range(0, input_layer_pts.GetFeatureCount()):
        # Récupération de l'entité de la couche en entrée
        input_feature = input_layer_pts.GetFeature(i)

        # Calcul de la distance du point courant à la ligne la plus proche
        geom_point = input_feature.GetGeometryRef()
        input_layer_tdc.ResetReading()
        liste_distances = []
        for ligne in input_layer_tdc:
            geom_ligne = ligne.GetGeometryRef()
            dist = geom_point.Distance(geom_ligne)
            liste_distances.append(dist)
            liste_all_distances.append(dist)
        dist_min = min(liste_distances)
        liste_min_distances.append(dist_min)

        # Création de l'entité en sortie
        output_feature = ogr.Feature(output_layer_defn)
        # Ajout des champs de la couche d'entrée à la couche de sortie
        if debug >= 4:
            print(cyan + "distanceTDCPointLine : " + endC + green + bold + "POINT " + str(i) + endC)
        for i in range(0, output_layer_defn.GetFieldCount()-1):
            if debug >= 4:
                print(cyan + "distanceTDCPointLine : " + endC + str(output_layer_defn.GetFieldDefn(i).GetNameRef()) + " : " + str(input_feature.GetField(i)))
            output_feature.SetField(output_layer_defn.GetFieldDefn(i).GetNameRef(), input_feature.GetField(i))
            output_feature.SetField("distance", dist_min)
        if debug >= 4:
            print(cyan + "distanceTDCPointLine : " + endC + "Distance à la ligne la plus proche : " + str(dist_min) + "\n")

        # Géométrie de la couche de sortie
        input_geom = input_feature.GetGeometryRef()
        output_feature.SetGeometry(input_geom)

        # Ajout de la nouvelle entité à la couche de sortie
        output_layer.CreateFeature(output_feature)

    ## Calcul du sens de l'évolution
    tdc_reference_buffers_sens = evolvingDirectionTDC(input_tdc_shp, input_sea_points, output_dir, int(ceil(max(liste_min_distances))), path_time_log, server_postgis, user_postgis, password_postgis, database_postgis, schema_name, port_number, epsg, project_encoding, format_vector, save_results_intermediate, overwrite)

    data_source_tdc_ref_buffers_sens = driver.Open(tdc_reference_buffers_sens, 1)
    layer_tdc_ref_buffers_sens = data_source_tdc_ref_buffers_sens.GetLayer(0)

    # Création de l'intersection avec les buffers unilatéraux pour avoir le sens d'évolution
    data_source_intersection_sens = driver.CreateDataSource(vector_output_points_sens)
    intersection_sens_layer = data_source_intersection_sens.CreateLayer(vector_output_points_sens, srs, geom_type=ogr.wkbPoint)
    intersection_sens_layer_defn = intersection_sens_layer.GetLayerDefn()
    intersection_sens = layer_tdc_ref_buffers_sens.Intersection(output_layer, intersection_sens_layer)

    # Ajout champ evolution, multiplication du buffer multiple dans lequel il se trouve avec sens évolution
    evolution_field = ogr.FieldDefn("evolution", ogr.OFTReal)
    intersection_sens_layer.CreateField(evolution_field)

    for i in range(0,intersection_sens_layer.GetFeatureCount()):
        feature = intersection_sens_layer.GetFeature(i)
        distance = feature.GetField("distance")
        evol_direction = feature.GetField("num_side")
        feature.SetField(evolution_column_name, distance*evol_direction)
        intersection_sens_layer.SetFeature(feature)
        feature.Destroy()

    liste_all_evolutions = []

    ## Création du fichier texte en sortie
    writeTextFile(output_text_file, "")

    # Initialisation des colonnes du fichier texte
    for i in range(intersection_sens_layer_defn.GetFieldCount()-1):
        appendTextFile(output_text_file, intersection_sens_layer_defn.GetFieldDefn(i).GetName() + "\t \t")
    appendTextFile(output_text_file, str(evolution_column_name) + " (m)\n")

    for i in range(0, intersection_sens_layer.GetFeatureCount()):
        # Récupération de l'entité de la couche en entrée
        feature = intersection_sens_layer.GetFeature(i)

        for j in range(0, intersection_sens_layer_defn.GetFieldCount()-1):
            appendTextFile(output_text_file, str(feature.GetField(j)) + "\t \t")
        appendTextFile(output_text_file, str(feature.GetField(evolution_column_name)) + "\n")
        liste_all_evolutions.append(feature.GetField(evolution_column_name))

    appendTextFile(output_text_file, "\nDistance min à la ligne (m) : " + str(min(liste_all_evolutions)) + "\n")
    appendTextFile(output_text_file, "Distance max à la ligne (m) : " + str(max(liste_all_evolutions)) + "\n")
    appendTextFile(output_text_file, "Moyenne des distances à la ligne (m) : " + str(np.mean(liste_all_evolutions)) + "\n")
    appendTextFile(output_text_file, "Ecart-type des distances à la ligne (m) : " + str(np.std(liste_all_evolutions)) + "\n")

    if debug >=3 :
        print(cyan + "distanceTDCPointLine() : " + endC + bold + green + "L'évolution a bien été calculée dans le fichier " + endC + bold + green + vector_output_points_sens + " dans la colonne '" + evolution_column_name + "' et la distance en valeur absolue dans la colonne 'distance'" + endC)
        print(cyan + "distanceTDCPointLine() : " + endC + bold + green + "Un résumé est fait dans le fichier texte : " + output_text_file + endC)

    # Mise à jour du Log
    ending_event = "distanceTDCPointLine() : Distance TDC Point Line ending : "
    timeLine(path_time_log,ending_event)

    return

###########################################################################################################################################
# MISE EN PLACE DU PARSER                                                                                                                 #
###########################################################################################################################################

# Code executé seulement dans le cas ou le script est lancé depuis une ligne de commande
# Il n'est pas executé lors d'un import DistanceTDCPointLine.py
# Exemple de lancement en ligne de commande:
# python /home/scgsi/Documents/ChaineTraitement/ScriptsLittoral/DistanceTDCPointLine.py -pts /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Images_test/test_distance/point.shp -tdc /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Images_test/test_distance/tdcs_1_emprise_image_opti_0824_ass_20140222_-0.2.shp -outd /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Tests/Tests_DistancePtsTDC -mer /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Images_test/point_mer_distances_pt_ligne.shp

def main(gui=False):

    # Définition des arguments possibles pour l'appel en ligne de commande
    parser = argparse.ArgumentParser(prog="DistanceTDCPointLine", description=" \
    Info : Calculates the shortest distance from point to lines. \n\
    Objectif : Calcul de la plus courte distance entre chaque point et toutes les lignes. \n\
    Example : python /home/scgsi/Documents/ChaineTraitement/ScriptsLittoral/DistanceTDCPointLine.py -pts /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Images_test/test_distance/point.shp \n\
                                        -tdc /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Images_test/test_distance/tdcs_1_emprise_image_opti_0824_ass_20140222_-0.2.shp \n\
                                        -outd /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Tests/Tests_DistancePtsTDC \n\
                                        -mer /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Images_test/point_mer_distances_pt_ligne.shp")
    # Paramètres
    parser.add_argument('-pts','--input_points_shp',default="",help="Vector file containing the points.", type=str, required=True)
    parser.add_argument('-tdc','--input_tdc_shp',default="",help="Vector file containing the coastline.", type=str, required=True)
    parser.add_argument('-outd','--output_dir',default="",help="Name of the output directory.", type=str, required=True)
    parser.add_argument('-mer','--input_sea_points', default="",help="Input vector file containing points in the sea (.shp).", type=str, required=True)
    parser.add_argument('-col','--evolution_column_name',default="evolution",help="Name of the column to in which the distance is put.", type=str, required=False)
    parser.add_argument('-serv','--server_postgis', default="localhost",help="Postgis serveur name or ip.", type=str, required=False)
    parser.add_argument('-port','--port_number', default=5432,help="Postgis port number.", type=int, required=False)
    parser.add_argument('-user','--user_postgis', default="postgres",help="Postgis user name.", type=str, required=False)
    parser.add_argument('-pwd','--password_postgis', default="postgres",help="Postgis password user.", type=str, required=False)
    parser.add_argument('-db','--database_postgis', default="db_buffer_tdc",help="Postgis database name.", type=str, required=False)
    parser.add_argument('-sch','--schema_name', default="directionevolution",help="Postgis schema name.", type=str, required=False)
    parser.add_argument("-epsg",'--epsg',default=2154,help="Projection parameter of data.", type=int, required=False)
    parser.add_argument('-pe','--project_encoding',default="UTF-8",help="Option : Format for the encoding. By default : UTF-8", type=str, required=False)
    parser.add_argument("-vef",'--format_vector',default='ESRI Shapefile',help="The format of vectors", type=str, required=False)
    parser.add_argument('-log','--path_time_log',default="",help="Name of log", type=str, required=False)
    parser.add_argument('-sav','--save_results_inter',action='store_true',default=False,help="Save or delete intermediate result after the process. By default, False", required=False)
    parser.add_argument('-now','--overwrite',action='store_false',default=True,help="Overwrite files with same names. By default, True", required=False)
    parser.add_argument('-debug','--debug',default=3,help="Option : Value of level debug trace, default : 3 ",type=int, required=False)
    args = displayIHM(gui, parser)

    # RECUPERATION DES ARGUMENTS

    # Récupération du fichier contenant les points
    if args.input_points_shp != None:
        input_points_shp = args.input_points_shp

    # Récupération du fichier contenant la ou les ligne(s)
    if args.input_tdc_shp != None:
        input_tdc_shp = args.input_tdc_shp

    # Récupération du dossier de sortie pour les traitements
    if args.output_dir != None:
        output_dir = args.output_dir

    # Récupération des points dans la mer
    if args.input_sea_points != None :
        input_sea_points = args.input_sea_points

    # Récupération du nom de la colonne distance pour le vecteur de sortie
    if args.evolution_column_name != None:
        evolution_column_name = args.evolution_column_name

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

    # Récupération du code EPSG des fichiers vecteur
    if args.epsg != None:
        epsg = args.epsg

    # Récupération de l'encodage des fichiers
    if args.project_encoding != None:
        project_encoding = args.project_encoding

    # Récupération du format des fichiers vecteur
    if args.format_vector != None:
        format_vector = args.format_vector

    # Récupération du nom du fichier log
    if args.path_time_log!= None:
        path_time_log = args.path_time_log

    # Récupération du booléen pour la sauvegarde des fichiers intermédiaires
    if args.save_results_inter != None:
        save_results_intermediate = args.save_results_inter

    # Récupération du booléen pour l'écrasement des fichiers s'ils existent déjà
    if args.overwrite!= None:
        overwrite = args.overwrite

    # Récupération de l'option niveau de debug
    if args.debug!= None:
        global debug
        debug = args.debug

    # Affichage des arguments récupérés
    if debug >= 3:
        print(bold + green + "Variables dans le parser" + endC)
        print(cyan + "DistanceTDCPointLine : " + endC + "input_points_shp : " + str(input_points_shp) + endC)
        print(cyan + "DistanceTDCPointLine : " + endC + "input_tdc_shp : " + str(input_tdc_shp) + endC)
        print(cyan + "DistanceTDCPointLine : " + endC + "output_dir : " + str(output_dir) + endC)
        print(cyan + "DistanceTDCPointLine : " + endC + "evolution_column_name : " + str(evolution_column_name) + endC)
        print(cyan + "DistanceTDCPointLine : " + endC + "server_postgis : " + str(server_postgis) + endC)
        print(cyan + "DistanceTDCPointLine : " + endC + "port_number : " + str(port_number) + endC)
        print(cyan + "DistanceTDCPointLine : " + endC + "user_postgis : " + str(user_postgis) + endC)
        print(cyan + "DistanceTDCPointLine : " + endC + "password_postgis : " + str(password_postgis) + endC)
        print(cyan + "DistanceTDCPointLine : " + endC + "database_postgis : " + str(database_postgis) + endC)
        print(cyan + "DistanceTDCPointLine : " + endC + "schema_name : " + str(schema_name) + endC)
        print(cyan + "DistanceTDCPointLine : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "DistanceTDCPointLine : " + endC + "project_encoding : " + str(project_encoding) + endC)
        print(cyan + "DistanceTDCPointLine : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "DistanceTDCPointLine : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "DistanceTDCPointLine : " + endC + "save_results_inter : " + str(save_results_intermediate) + endC)
        print(cyan + "DistanceTDCPointLine : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "DistanceTDCPointLine : " + endC + "debug : " + str(debug) + endC)

    # EXECUTION DE LA FONCTION
    distanceTDCPointLine(input_points_shp, input_tdc_shp, output_dir, input_sea_points, evolution_column_name, path_time_log, server_postgis, user_postgis, password_postgis, database_postgis, schema_name, port_number, epsg, project_encoding, format_vector, save_results_intermediate, overwrite)

# ================================================

if __name__ == '__main__':
  main(gui=False)

