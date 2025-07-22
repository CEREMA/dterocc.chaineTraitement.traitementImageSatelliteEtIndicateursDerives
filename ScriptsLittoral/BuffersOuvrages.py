#! /usr/bin/env pyt/hon
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT D'EXTRACTION DES OUVRAGES À PARTIR D'UN TRAIT DE CÔTE PAR LA MÉTHODE DES BUFFERS                                                   #
#                                                                                                                                           #
#############################################################################################################################################

"""
Nom de l'objet : BuffersOuvrages.py
Description    :
----------------
Objectif   : Extraction des ouvrages par la méthodes des buffers, à partir d'un trait de côte

Date de creation : 07/06/2016
"""

from __future__ import print_function
import os, sys, shutil, argparse
from osgeo import ogr
from Lib_display import bold, red, cyan, green, endC, displayIHM
from Lib_log import timeLine
from Lib_vector import bufferVector, cutVectorAll

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 3

###########################################################################################################################################
# FONCTION buffersOuvrages                                                                                                                #
###########################################################################################################################################
def buffersOuvrages(input_tdc_shp, output_dir, buf_pos, buf_neg, input_cut_vector, path_time_log, format_vector="ESRI Shapefile", extension_vector=".shp", save_results_intermediate=True, overwrite=True):
    """
    # ROLE:
    #    Extraction des ouvrages en mer à partir du trait de côte, selon la méthode des buffers (buffer positif puis négatif sur le TDC)
    #
    # ENTREES DE LA FONCTION :
    #    input_tdc_shp : shapefile du trait de côte à partir duquel les ouvrages seront extraits
    #    output_dir : Répertoire de sortie pour les traitements
    #    buf_pos : valeur du buffer positif (par défaut, 12m)
    #    buf_neg : Valeur du buffer négatif (par défaut, -14m)
    #    input_cut_vector : Shapefile de découpe de la zone d'intéret pour la suppression des artéfacts
    #    format_vector : Format des fichiers vecteur. Par défaut "ESRI Shapefile"
    #    extension_vector : extension du fichier vecteur de sortie, par defaut = '.shp'
    #    path_time_log : le fichier de log de sortie
    #    save_results_intermediate : fichiers de sorties intermediaires non nettoyées, par defaut = True
    #    overwrite : supprime ou non les fichiers existants ayant le meme nom
    #
    # SORTIES DE LA FONCTION :
    #    Le fichier contenant les ouvrages extraits par la méthode des buffers
    #    Eléments modifiés aucun
    #
    """

    # Mise à jour du Log
    starting_event = "buffersOuvrages() : Select buffers ouvrages starting : "
    timeLine(path_time_log,starting_event)

    # Affichage des paramètres
    if debug >= 3:
        print(bold + green + "Variables dans buffersOuvrages - Variables générales" + endC)
        print(cyan + "buffersOuvrages() : " + endC + "input_tdc_shp : " + str(input_tdc_shp) + endC)
        print(cyan + "buffersOuvrages() : " + endC + "output_dir : " + str(output_dir) + endC)
        print(cyan + "buffersOuvrages() : " + endC + "buf_pos : " + str(buf_pos) + endC)
        print(cyan + "buffersOuvrages() : " + endC + "buf_neg : " + str(buf_neg) + endC)
        print(cyan + "buffersOuvrages() : " + endC + "input_cut_vector : " + str(input_cut_vector) + endC)
        print(cyan + "buffersOuvrages() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "buffersOuvrages() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "buffersOuvrages() : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "buffersOuvrages() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "buffersOuvrages() : " + endC + "overwrite : " + str(overwrite) + endC)

    # Constantes
    REP_TEMP = "temp_buffersOuvrages"

    # Variables
    repertory_temp = output_dir + os.sep + REP_TEMP
    nom_tdc = os.path.splitext(os.path.basename(input_tdc_shp))[0]
    output_vector = output_dir + os.sep + "OuvragesBuffers" + str(buf_pos) + str(buf_neg) + "_" + nom_tdc + extension_vector
    tdc_decoup_vector = repertory_temp + os.sep + "decoup_" + nom_tdc + extension_vector
    temp_buf_vector = repertory_temp + os.sep + "buffer" + str(buf_pos) + "_" + nom_tdc + extension_vector

    # Création du répertoire de sortie s'il n'existe pas déjà
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Création du répertoire de sortie s'il n'existe pas déjà
    if not os.path.exists(repertory_temp):
        os.makedirs(repertory_temp)

    # Vérification de l'existance du fichier tdc en entrée
    driver = ogr.GetDriverByName(format_vector)
    data_source_tdc = driver.Open(input_tdc_shp,0)
    if data_source_tdc is None:
        print(cyan + "buffersOuvrages() : " + bold + red + "Could not open file : " + str(input_tdc_shp) + endC, file=sys.stderr)
        sys.exit(1)

    # Découpe du TDC par le shapefile en entrée pour la suppression des artéfacts
    cutVectorAll(input_cut_vector, input_tdc_shp, tdc_decoup_vector, overwrite, format_vector)

    # Buffer positif puis négatif sur le tdc pour extraire les ouvrages
    bufferVector(input_tdc_shp, temp_buf_vector, str(buf_pos), "", 1.0, 10, format_vector)
    bufferVector(temp_buf_vector, output_vector, buf_neg, "", 1.0, 10, format_vector)

    # Suppression du repertoire temporaire
    if not save_results_intermediate and os.path.exists(repertory_temp):
        shutil.rmtree(repertory_temp)

    # Mise à jour du Log
    ending_event = "buffersOuvrages() : Select buffers ouvrages ending : "
    timeLine(path_time_log,ending_event)

    return output_vector

###########################################################################################################################################
# MISE EN PLACE DU PARSER                                                                                                                 #
###########################################################################################################################################

# Code executé seulement dans le cas ou le script est lancé depuis une ligne de commande
# Il n'est pas executé lors d'un import BuffersOuvrages.py
# Exemple de lancement en ligne de commande:
# python /home/scgsi/Documents/ChaineTraitement/ScriptsLittoral/BuffersOuvrages.py -tdc /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Test_TDCSeuil/2944/tdcsd_1_emprise_image_opti_2944_ass_20140307_-0.1.shp -outd /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Tests/Tests_BuffersOuvrages -d /mnt/Donnees_Etudes/20_Etudes/Mediterranee/2Miseenforme/decoupe_zone_interet.shp

def main(gui=False):

    parser = argparse.ArgumentParser(prog="BuffersOuvrages", description=" \
    Info : Creating an shapefile (.shp) containing the structures from a coastline by the buffers method.\n\
    Objectif   : Extrait les ouvrages à partir d'un fichier vecteur contenant un trait de côte, par la méthode des buffers. \n\
    Example : python /home/scgsi/Documents/ChaineTraitement/ScriptsLittoral/BuffersOuvrages.py \n\
                    -tdc /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Test_TDCSeuil/2944/tdcsd_1_emprise_image_opti_2944_ass_20140307_-0.1.shp \n\
                    -outd /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Tests/Tests_BuffersOuvrages \n\
                    -d /mnt/Donnees_Etudes/20_Etudes/Mediterranee/2Miseenforme/decoupe_zone_interet.shp")

    parser.add_argument('-tdc','--input_tdc_shp', default="", help="Shapefile containing the coastline (.shp).", type=str, required=True)
    parser.add_argument('-outd','--output_dir', default="",help="Output directory.", type=str, required=True)
    parser.add_argument('-bp','--buf_pos', default=12,help="Value for positive buffer (float). Default : 12m.", type=float, required=False)
    parser.add_argument('-bn','--buf_neg', default=-14,help="Value for negative buffer (float). Default : -14m.", type=float, required=False)
    parser.add_argument('-d','--input_cut_vector', default="",help="Cutting file.", type=str, required=True)
    parser.add_argument('-log','--path_time_log',default="",help="Name of log", type=str, required=False)
    parser.add_argument('-vef','--format_vector',default="ESRI Shapefile",help="Option : Vector format. By default : ESRI Shapefile", type=str, required=False)
    parser.add_argument('-vee','--extension_vector',default=".shp",help="Option : Extension file for vector. By default : '.shp'", type=str, required=False)
    parser.add_argument('-sav','--save_results_inter',action='store_true',default=False,help="Option : Save or delete intermediate result after the process. By default, False", required=False)
    parser.add_argument('-now','--overwrite',action='store_false',default=True,help="Option : Overwrite files with same names. By default : True", required=False)
    parser.add_argument('-debug','--debug',default=3,help="Option : Value of level debug trace, default : 3 ",type=int, required=False)
    args = displayIHM(gui, parser)

    # Récupération du shp contenant le trait de côte à traiter
    if args.input_tdc_shp != None :
        input_tdc_shp = args.input_tdc_shp

    # Récupération du dossier des traitements en sortie
    if args.output_dir != None :
        output_dir = args.output_dir

    # Récupération de la valeur du buffer positif
    if args.buf_pos != None :
        buf_pos = args.buf_pos

    # Récupération de la valeur du buffer négatif
    if args.buf_neg != None :
        buf_neg = args.buf_neg

    # Récupération du fichier pour la découpe (suppression des artéfacts)
    if args.input_cut_vector != None :
        input_cut_vector = args.input_cut_vector

    # Récupération du nom du fichier log
    if args.path_time_log != None:
        path_time_log = args.path_time_log

    # Récupération du nom du format des fichiers vecteur
    if args.format_vector != None:
        format_vector = args.format_vector

    # Récupération de l'extension des fichiers vecteurs
    if args.extension_vector != None:
        extension_vector = args.extension_vector

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
        print(cyan + "buffersOuvrages : " + endC + "input_tdc_shp : " + str(input_tdc_shp) + endC)
        print(cyan + "buffersOuvrages : " + endC + "output_dir : " + str(output_dir) + endC)
        print(cyan + "buffersOuvrages : " + endC + "buf_pos : " + str(buf_pos) + endC)
        print(cyan + "buffersOuvrages : " + endC + "buf_neg : " + str(buf_neg) + endC)
        print(cyan + "buffersOuvrages : " + endC + "input_cut_vector : " + str(input_cut_vector) + endC)
        print(cyan + "buffersOuvrages : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "buffersOuvrages : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "buffersOuvrages : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "buffersOuvrages : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "buffersOuvrages : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "buffersOuvrages : " + endC + "debug : " + str(debug) + endC)

    # Fonction générale
    buffersOuvrages(input_tdc_shp, output_dir, buf_pos, buf_neg, input_cut_vector, path_time_log, format_vector, extension_vector, save_results_intermediate, overwrite)

# ================================================

if __name__ == '__main__':
  main(gui=False)
