#! /usr/bin/env pyt/hon
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerSO/DALETT/SCGSI  All rights reserved.                                                                            #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT DE CALCUL D'ÉVOLUTION ENTRE 2 TRAITS DE CÔTE PAR LA MÉTHODE DES BUFFERS                                                            #
#                                                                                                                                           #
#############################################################################################################################################

'''
Nom de l'objet : DistanceTDCBuffers.py
Description    :
    Objectif   : Calcule la distance entre deux traits de côte par la méthode des buffers

Date de creation : 08/08/2016
'''

from __future__ import print_function
import os, sys, ogr, osr, sys, argparse
from Lib_display import bold, black, red, green, yellow, blue, magenta, cyan, endC, displayIHM
from Lib_vector import bufferVector, differenceVector, fusionVectors
from Lib_file import copyVectorFile
from Lib_log import timeLine
from EvolvingDirectionTDC import evolvingDirectionTDC
debug = 3

###########################################################################################################################################
# FONCTION distanceTDCBuffers                                                                                                             #
###########################################################################################################################################
# ROLE:
#    Calcul de distance entre un trait de côte calculé et un de référence
#
# ENTREES DE LA FONCTION :
#    tdc_reference : Fichier vecteur contenant le trait de côte de référence pour le calcul de la distance
#    tdc_calcule : Fichier vecteur contenant le trait de côte calculé, pour lequel on veut calculer la distance à un TDC de référence
#    input_sea_points : Fichier vecteur de point(s) dans la mer, pour identifier le buffer côté mer et celui côté terre (Attention : points doivent être contenus dans le buffer)
#    output_dir : Répertoire de sortie pour les traitements
#    buffer_size : Taille des buffers (en mètres), qui modulera la précision avec laquelle on veut obtenir cette différence
#    nb_buffers : Nombre de buffers à calculer (même nombre de chaque côte du TDC)
#    path_time_log : le fichier de log de sortie
#    server_postgis : nom du serveur postgis
#    user_postgis : le nom de l'utilisateurs postgis
#    password_postgis : le mot de passe de l'utilisateur posgis
#    database_postgis : le nom de la base posgis à utiliser
#    schema_postgis : le nom du schéma à utiliser
#    port_number : numéro du port à utiliser. Uniquement testé avec le 5432 (valeur par défaut)
#    epsg : Code EPSG de la projection de la couche finale. Par défaut : 2154
#    project_encoding : Système d'encodage des fichiers. Par défaut : "UTF-8"
#    format_vector : Format des fichiers vecteurs. Par défaut : "ESRI Shapefile"
#    save_results_intermediate : fichiers de sorties intermediaires non nettoyées, par defaut = True
#    overwrite : Supprime ou non les fichiers existants ayant le meme nom. Par défaut : True
#
# SORTIES DE LA FONCTION :
#    Le fichier contenant le trait de côte (tdc_calcule), avec un champ "evolution" (évolution par rapport au trait de côte de référence)
#    Eléments modifiés aucun
#

def distanceTDCBuffers(tdc_reference, tdc_calcule, input_sea_points, output_dir, buffer_size, nb_buffers, path_time_log, server_postgis="localhost", user_postgis="postgres", password_postgis="postgres", database_postgis="db_buffer_tdc", schema_name="directionevolution", port_number=5432, epsg=2154, project_encoding="UTF-8", format_vector="ESRI Shapefile", save_results_intermediate=True, overwrite=True):

    # Mise à jour du Log
    starting_event = "distanceTDCBuffers() : Select distance TDC buffers starting : "
    timeLine(path_time_log,starting_event)

    if debug >= 3:
        print(bold + green + "Variables dans distanceTDCBuffers - Variables générales" + endC)
        print(cyan + "distanceTDCBuffers() : " + endC + "tdc_reference : " + str(tdc_reference) + endC)
        print(cyan + "distanceTDCBuffers() : " + endC + "tdc_calcule : " + str(tdc_calcule) + endC)
        print(cyan + "distanceTDCBuffers() : " + endC + "input_sea_points : " + str(input_sea_points) + endC)
        print(cyan + "distanceTDCBuffers() : " + endC + "output_dir : " + str(output_dir) + endC)
        print(cyan + "distanceTDCBuffers() : " + endC + "buffer_size : " + str(buffer_size) + endC)
        print(cyan + "distanceTDCBuffers() : " + endC + "nb_buffers : " + str(nb_buffers) + endC)
        print(cyan + "distanceTDCBuffers() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "distanceTDCBuffers() : " + endC + "server_postgis : " + str(server_postgis) + endC)
        print(cyan + "distanceTDCBuffers() : " + endC + "user_postgis : " + str(user_postgis) + endC)
        print(cyan + "distanceTDCBuffers() : " + endC + "password_postgis : " + str(password_postgis) + endC)
        print(cyan + "distanceTDCBuffers() : " + endC + "database_postgis : " + str(database_postgis) + endC)
        print(cyan + "distanceTDCBuffers() : " + endC + "schema_name : " + str(schema_name) + endC)
        print(cyan + "distanceTDCBuffers() : " + endC + "port_number : " + str(port_number) + endC)
        print(cyan + "distanceTDCBuffers() : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "distanceTDCBuffers() : " + endC + "project_encoding : " + str(project_encoding) + endC)
        print(cyan + "distanceTDCBuffers() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "distanceTDCBuffers() : " + endC + "save_results_inter : " + str(save_results_intermediate) + endC)
        print(cyan + "distanceTDCBuffers() : " + endC + "overwrite : " + str(overwrite) + endC)

    print(bold + green + "## START : distanceTDCBuffers" + endC)

    # Initialisation des constantes
    REP_TEMP = "temp_distanceTDCBuffers"

    # Initialisation des variables
    repertory_temp = output_dir + os.sep + REP_TEMP
    extension_vector = os.path.splitext(os.path.split(tdc_reference)[1])[1]
    nom_tdc_reference = os.path.splitext(os.path.split(tdc_reference)[1])[0]
    nom_tdc_calcule = os.path.splitext(os.path.split(tdc_calcule)[1])[0]


    # Configuration du format vecteur
    driver = ogr.GetDriverByName(format_vector)

    # Création de la référence spatiale
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(epsg)

    # Création du répertoire de sortie s'il n'existe pas déjà
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Création du répertoire de sortie temporaire s'il n'existe pas déjà
    if not os.path.exists(repertory_temp):
        os.makedirs(repertory_temp)

    # Vérification de l'existence du trait de côte de référence
    if not os.path.exists(tdc_reference):
        print(cyan + "distanceTDCBuffers() : " + bold + red + "Le shapefile du trait de côte de référence " + tdc_reference + " n'existe pas." + endC, file=sys.stderr)
        sys.exit(1)

    # Vérification de l'existence du trait de côte calculé
    if not os.path.exists(tdc_calcule):
        print(cyan + "distanceTDCBuffers() : " + bold + red + "Le shapefile du trait de côte calculé " + tdc_calcule + " n'existe pas." + endC, file=sys.stderr)
        sys.exit(1)

    # Vérification de l'existence du shapefile de points dans la mer
    if not os.path.exists(input_sea_points):
        print(cyan + "distanceTDCBuffers() : " + bold + red + "Le shapefile du trait de points dans la mer " + input_sea_points + " n'existe pas." + endC, file=sys.stderr)
        sys.exit(1)

    # Initialisations
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(epsg)

    # Création de l'intersection avec les buffers distance
    intersection_shp = repertory_temp + os.sep + "distance_" + nom_tdc_reference + "_" + nom_tdc_calcule + extension_vector
    if os.path.exists(intersection_shp):
        driver.DeleteDataSource(intersection_shp)

    # Création de l'intersection avec les buffers unilatéraux pour avoir le sens de l'évolution
    intersection_sens_shp = output_dir + os.sep + "distance_sens_evol_" + nom_tdc_reference + "_" + nom_tdc_calcule + extension_vector
    if os.path.exists(intersection_sens_shp):
        driver.DeleteDataSource(intersection_sens_shp)

    # Création des multi-buffers autour du trait de côte de référence
    tdc_reference_buffers = multiBuffersVector(tdc_reference,repertory_temp, buffer_size, nb_buffers, path_time_log, epsg, format_vector, project_encoding, overwrite)

    # Récupération des couches
    data_source_tdc_calcule = driver.Open(tdc_calcule, 1)
    layer_tdc_calcule = data_source_tdc_calcule.GetLayer(0)

    data_source_tdc_ref_buffers = driver.Open(tdc_reference_buffers, 1)
    layer_tdc_ref_buffers = data_source_tdc_ref_buffers.GetLayer(0)

    # Création de l'intersection avec les buffers distance
    data_source_intersection = driver.CreateDataSource(intersection_shp)
    intersection_layer = data_source_intersection.CreateLayer(intersection_shp, srs, geom_type=ogr.wkbLineString)
    intersection = layer_tdc_ref_buffers.Intersection(layer_tdc_calcule, intersection_layer)

    # Récupération de la couche buffers unilatéraux pour avoir le sens d'évolution
    tdc_reference_buffers_sens = evolvingDirectionTDC(tdc_reference, input_sea_points, output_dir, nb_buffers*buffer_size, path_time_log, server_postgis, user_postgis, password_postgis, database_postgis, schema_name, port_number, epsg, project_encoding, format_vector, save_results_intermediate, overwrite)

    data_source_tdc_ref_buffers_sens = driver.Open(tdc_reference_buffers_sens, 1)
    layer_tdc_ref_buffers_sens = data_source_tdc_ref_buffers_sens.GetLayer(0)

    # Création de l'intersection avec les buffers unilatéraux pour avoir le sens de l'évolution
    data_source_intersection_sens = driver.CreateDataSource(intersection_sens_shp)
    intersection_sens_layer = data_source_intersection_sens.CreateLayer(intersection_sens_shp, srs, geom_type=ogr.wkbLineString)
    intersection_sens = layer_tdc_ref_buffers_sens.Intersection(intersection_layer, intersection_sens_layer)

    # Ajout champ evolution, multiplication du buffer multiple dans lequel il se trouve avec sens évolution
    evolution_field = ogr.FieldDefn("evolution", ogr.OFTReal)
    intersection_sens_layer.CreateField(evolution_field)

    for i in range(0,intersection_sens_layer.GetFeatureCount()):
        feature = intersection_sens_layer.GetFeature(i)
        size_buff = feature.GetField("size_buff")
        #evol_direction = feature.GetField("evolution")
        evol_direction = feature.GetField("num_side")
        feature.SetField("evolution", size_buff*evol_direction)
        intersection_sens_layer.SetFeature(feature)
        feature.Destroy()

    if debug >=3 :
        print(cyan + "distanceTDCBuffers() : " + endC + bold + green + "La distance a été bien calculée dans le fichier " + intersection_sens_shp + " et l'évolution entre les deux traits de côte est indiquée dans le champ 'evolution'." + endC)

    # Suppression du repertoire temporaire
    if not save_results_intermediate and os.path.exists(repertory_temp):
        shutil.rmtree(repertory_temp)

    ending_event = "distanceTDCBuffers() : distance TDC buffers ending : "
    timeLine(path_time_log,ending_event)

    return

###########################################################################################################################################
# FONCTION multiBuffersVector                                                                                                             #
###########################################################################################################################################
# ROLE:
#    Création de buffers multiples en taille et nombre paramétrables. Le buffer de la taille du dessous est évidé dans le buffer du dessus. Possibilité de buffers unilatéraux (traitement très long)
#
# ENTREES DE LA FONCTION :
#    input_file : Fichier vecteur en entrée
#    output_dir : Répertoire de sortie pour les traitements
#    buffer_size : Taille pour les buffers (ils sont tous de même taille)
#    nb_buffers : Nombre de buffers
#    path_time_log : Fichier de log de sortie
#    epsg : Code EPSG de la projection de la couche finale. Par défaut : 2154
#    format_vector : Format des fichiers vecteur. Par défaut "ESRI Shapefile"
#    project_encoding : Système d'encodage des fichiers. Par défaut : "UTF-8"
#    overwrite : Supprime ou non les fichiers existants ayant le meme nom
#
# SORTIES DE LA FONCTION :
#    Le fichier contenant les buffers multiples
#    Eléments modifiés aucun
#

def multiBuffersVector(input_file, output_dir, buffer_size, nb_buffers, path_time_log, epsg=2154, format_vector="ESRI Shapefile", project_encoding="UTF-8", overwrite=True):
    # Mise à jour du Log
    starting_event = "multiBuffersVector() : Select multi buffers vector starting : "
    timeLine(path_time_log,starting_event)

    # Configuration du format vecteur
    driver = ogr.GetDriverByName(format_vector)

    # Création de la référence spatiale
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(epsg)

    result_list = []

    extension_vector = os.path.splitext(os.path.split(input_file)[1])[1]
    nom_input_file = os.path.splitext(os.path.split(input_file)[1])[0]
    output_repertory = output_dir + os.sep + "multi_ring_buffers_" + nom_input_file + extension_vector

    for i in range(1, nb_buffers+1):

        # Création du buffer
        output_temp_buffer = output_dir + os.sep + os.path.splitext(os.path.split(input_file)[1])[0] + "_buffer_" + str(i*buffer_size) + extension_vector
        bufferVector(input_file, output_temp_buffer, i*buffer_size, "", 1.0, 10, format_vector)

        # Ajout d'un champ taille de buffer
        data_source_buffer = driver.Open(output_temp_buffer, 1)
        buffer_layer = data_source_buffer.GetLayer(0)
        buff_size_field = ogr.FieldDefn("size_buff", ogr.OFTReal)
        buffer_layer.CreateField(buff_size_field)

        for feature in buffer_layer:
            feature.SetField("size_buff",i*buffer_size)
            buffer_layer.SetFeature(feature)

        # Ajout du premier buffer à la liste finale
        if i == 1:
            result_list.append(output_temp_buffer)

        # Transformation des buffers en anneaux
        if i>1:
            i_preced = i-1
            output_temp_buffer_preced = output_dir + os.sep + nom_input_file + "_buffer_" + str(i_preced*buffer_size) + extension_vector
            output_temp_ring = output_dir + os.sep + nom_input_file + "_ring_" + str(i*buffer_size) + extension_vector
            differenceVector(output_temp_buffer_preced, output_temp_buffer, output_temp_ring, format_vector)

            # Remplissage du champ taille du buffer
            data_source_ring = driver.Open(output_temp_ring, 1)
            ring_layer = data_source_ring.GetLayer(0)
            for ring in ring_layer:
                ring.SetField("size_buff",i*buffer_size)
                ring_layer.SetFeature(ring)

            # Ajout de l'anneau à la liste finale
            result_list.append(output_temp_ring)

        fusionVectors(result_list, output_repertory, format_vector)

    # Mise à jour du Log
    ending_event = "multiBuffersVector() : multi buffers vector ending : "
    timeLine(path_time_log,ending_event)

    return output_repertory

###########################################################################################################################################
# MISE EN PLACE DU PARSER                                                                                                                 #
###########################################################################################################################################

# Code executé seulement dans le cas ou le script est lancé depuis une ligne de commande
# Il n'est pas executé lors d'un import DistanceTDCBuffers.py
# Exemple de lancement en ligne de commande:
# python /home/scgsi/Documents/ChaineTraitement/ScriptsLittoral/DistanceTDCBuffers.py -tdcref /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/08_Donnees/N_traits_cote_naturels_recents_L_012016_shape_cle2432b6/N_traits_cote_naturels_recents_L_012016/N_traits_cote_naturels_recents_L_zone_interet.shp -tdccalc /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Images_test/test_distance/tdcs_1_emprise_image_opti_0824_ass_20140222_-0.2.shp -outd /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Tests/Distance_buffers -bs 1 -nb 20 -mer /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Images_test/point_mer_distances.shp

def main(gui=False):

    parser = argparse.ArgumentParser(prog="DistanceTDCBuffers", description=" \
    Info : Copying the shapefile of the tdc_calcule and creating a field 'evolution' in which the evolution compared to the tdc_reference is calculated.\n\
    Objectif   : Calcule l'évolution d'un trait de côte par rapport à un trait de côte de référence. \n\
    Example : python /home/scgsi/Documents/ChaineTraitement/ScriptsLittoral/DistanceTDCBuffers.py \n\
                -tdcref /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/08_Donnees/N_traits_cote_naturels_recents_L_012016_shape_cle2432b6/N_traits_cote_naturels_recents_L_012016/N_traits_cote_naturels_recents_L_zone_interet.shp \n\
                -tdccalc /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Images_test/test_distance/tdcs_1_emprise_image_opti_0824_ass_20140222_-0.2.shp \n\
                -outd /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Tests/Distance_buffers \n\
                -bs 1 -nb 20 \n\
                -mer /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Images_test/point_mer_distances.shp")

    parser.add_argument('-tdcref','--tdc_reference', default="",help="Reference coastline.", type=str, required=True)
    parser.add_argument('-tdccalc','--tdc_calcule', default="",help="Calculated coastline, which is to compare to tthe reference one.", type=str, required=True)
    parser.add_argument('-mer','--input_sea_points', default="",help="Input vector file containing points in the sea (.shp).", type=str, required=True)
    parser.add_argument('-outd','--output_dir', default="",help="Output directory.", type=str, required=True)
    parser.add_argument('-bs','--buffer_size', default="",help="Size (meters) for the buffers.", type=int, required=True)
    parser.add_argument('-nb','--nb_buffers', default="",help="Number of buffers on each side of the coastline.", type=int, required=True)
    parser.add_argument('-serv','--server_postgis', default="localhost",help="Postgis serveur name or ip.", type=str, required=False)
    parser.add_argument('-port','--port_number', default=5432,help="Postgis port number.", type=int, required=False)
    parser.add_argument('-user','--user_postgis', default="postgres",help="Postgis user name.", type=str, required=False)
    parser.add_argument('-pwd','--password_postgis', default="postgres",help="Postgis password user.", type=str, required=False)
    parser.add_argument('-db','--database_postgis', default="db_buffer_tdc",help="Postgis database name.", type=str, required=False)
    parser.add_argument('-sch','--schema_name', default="directionevolution",help="Postgis schema name.", type=str, required=False)
    parser.add_argument('-epsg','--epsg',default=2154,help="Option : Projection EPSG for the layers. By default : 2154", type=int, required=False)
    parser.add_argument('-pe','--project_encoding',default="UTF-8",help="Option : Format for the encoding. By default : UTF-8", type=str, required=False)
    parser.add_argument('-vef','--format_vector',default="ESRI Shapefile",help="Option : Vector format. By default : ESRI Shapefile", type=str, required=False)
    parser.add_argument('-log','--path_time_log',default="",help="Name of log", type=str, required=False)
    parser.add_argument('-sav','--save_results_inter',action='store_true',default=False,help="Option : Save or delete intermediate result after the process. By default, False", required=False)
    parser.add_argument('-now','--overwrite',action='store_false',default=True,help="Option : Overwrite files with same names. By default : True", required=False)
    parser.add_argument('-debug','--debug',default=3,help="Option : Value of level debug trace, default : 3 ",type=int, required=False)
    args = displayIHM(gui, parser)

    # Récupération du trait de côte de référence
    if args.tdc_reference != None :
        tdc_reference = args.tdc_reference

    # Récupération du trait de côte calculé
    if args.tdc_calcule != None :
        tdc_calcule = args.tdc_calcule

    # Récupération des points dans la mer
    if args.input_sea_points != None :
        input_sea_points = args.input_sea_points

    # Récupération du dossier des traitements en sortie
    if args.output_dir != None :
        output_dir = args.output_dir

    # Récupération de la taille des buffers
    if args.buffer_size != None :
        buffer_size = args.buffer_size

    # Récupération du nombre de buffers
    if args.nb_buffers != None :
        nb_buffers = args.nb_buffers

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

    # Récupération de la projection
    if args.epsg != None:
        epsg = args.epsg

    # Récupération de l'encodage des fichiers
    if args.project_encoding != None:
        project_encoding = args.project_encoding

    # Récupération du nom du format des fichiers vecteur
    if args.format_vector != None:
        format_vector = args.format_vector

    # Récupération du nom du fichier log
    if args.path_time_log != None:
        path_time_log = args.path_time_log

    # Ecrasement des fichiers
    if args.save_results_inter != None:
        save_results_intermediate = args.save_results_inter

    if args.overwrite != None:
        overwrite = args.overwrite

    # Récupération de l'option niveau de debug
    if args.debug!= None:
        global debug
        debug = args.debug

    # Affichage des arguments récupérés
    if debug >= 3:
        print(bold + green + "Variables dans le parser" + endC)
        print(cyan + "DistanceTDCBuffers : " + endC + "tdc_reference : " + str(tdc_reference) + endC)
        print(cyan + "DistanceTDCBuffers : " + endC + "tdc_calcule : " + str(tdc_calcule) + endC)
        print(cyan + "DistanceTDCBuffers : " + endC + "input_sea_points : " + str(input_sea_points) + endC)
        print(cyan + "DistanceTDCBuffers : " + endC + "output_dir : " + str(output_dir) + endC)
        print(cyan + "DistanceTDCBuffers : " + endC + "buffer_size : " + str(buffer_size) + endC)
        print(cyan + "DistanceTDCBuffers : " + endC + "nb_buffers : " + str(nb_buffers) + endC)
        print(cyan + "DistanceTDCBuffers : " + endC + "server_postgis : " + str(server_postgis) + endC)
        print(cyan + "DistanceTDCBuffers : " + endC + "port_number : " + str(port_number) + endC)
        print(cyan + "DistanceTDCBuffers : " + endC + "user_postgis : " + str(user_postgis) + endC)
        print(cyan + "DistanceTDCBuffers : " + endC + "password_postgis : " + str(password_postgis) + endC)
        print(cyan + "DistanceTDCBuffers : " + endC + "database_postgis : " + str(database_postgis) + endC)
        print(cyan + "DistanceTDCBuffers : " + endC + "schema_name : " + str(schema_name) + endC)
        print(cyan + "DistanceTDCBuffers : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "DistanceTDCBuffers : " + endC + "project_encoding : " + str(project_encoding) + endC)
        print(cyan + "DistanceTDCBuffers : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "DistanceTDCBuffers : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "DistanceTDCBuffers : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "DistanceTDCBuffers : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "DistanceTDCBuffers : " + endC + "debug : " + str(debug) + endC)


    # Fonction générale
    distanceTDCBuffers(tdc_reference, tdc_calcule, input_sea_points, output_dir, buffer_size, nb_buffers, path_time_log, server_postgis, user_postgis, password_postgis, database_postgis, schema_name, port_number, epsg, project_encoding, format_vector, save_results_intermediate, overwrite)

# ================================================

if __name__ == '__main__':
  main(gui=False)
