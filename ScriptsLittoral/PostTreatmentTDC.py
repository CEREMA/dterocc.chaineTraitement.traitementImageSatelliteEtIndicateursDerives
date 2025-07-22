#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT QUI MET EN FORME LES FICHIERS RESULTATS ISSUS DU TRAITEMENT TDC POUR LIVRAISON FINAL                                               #
#                                                                                                                                           #
#############################################################################################################################################
"""
Nom de l'objet : PostTreatmentTDC.py
Description :
-------------
Objectif : creation d'un fichier trait de côte generale issu de la fusion d'une liste de fichier de partie de trait après un lissage par interpolation de type courbe
Rq : utilisation des OTB Applications :  NA

Date de creation : 16/05/2019
----------
Histoire :
----------
Origine : nouvelle application pour livraison du TDC final

-----------------------------------------------------------------------------------------------------
Modifications

------------------------------------------------------
A Reflechir/A faire
TBD
"""

from __future__ import print_function
import os,sys,glob,shutil,string,argparse
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_log import timeLine
from Lib_file import removeVectorFile
from Lib_grass import initializeGrass, cleanGrass, smoothGeomGrass
from Lib_vector import getEmpriseVector, getProjection, geometries2multigeometries, fusionVectors, deleteFieldsVector, updateIndexVector, differenceVector

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 3

###########################################################################################################################################
# FONCTION processTDCfilesSmoothAndFusion()                                                                                               #
###########################################################################################################################################
def processTDCfilesSmoothAndFusion(coastline_vectors_input_list, vector_rocky_input, vector_all_output, vector_withrocky_output, generalize_param_method, generalize_param_threshold, name_column_fusion, path_time_log, epsg=2154, format_vector='ESRI Shapefile', extension_vector='.shp', save_results_intermediate=False, overwrite=True):
    """
    # ROLE:
    #    appliquer un traitement de lissage (imterpolation par une courbe) des fichiers vecteurs de traits de côte et fusion des resultats en un seul fichier vecteur
    #
    # ENTREES DE LA FONCTION :
    #    coastline_vectors_input_list : liste des vecteurs d'entrée des lignes de traits de côte
    #    vector_rocky_input : fichier vecteur d'entrée contenent les zones rocheuses
    #    vector_all_output : fichier vecteur de sortie resultat general de la fusion et lissage des vecteurs d'entrée
    #    vector_withrocky_output : fichier vecteur de sortie resultat fusion et sans les zones rocheuses
    #    generalize_param_method :  parametre de generalize de Grass type de methode à utiliser
    #    generalize_param_threshold : parametre de generalize de Grass valeur du seuil
    #    name_column_fusion : nom de la colonne pour fusionner les segements ligne sen multilignes
    #    path_time_log : le fichier de log de sortie
    #    epsg : Optionnel : par défaut 2154
    #    format_vector : format du fichier vecteur. Optionnel, par default : 'ESRI Shapefile'
    #    extension_vector : extension du fichier vecteur de sortie, par defaut = '.shp'
    #    save_results_intermediate : fichiers de sorties intermediaires non nettoyées, par defaut = False
    #    overwrite : supprime ou non les fichiers existants ayant le meme nom
    #
    # SORTIES DE LA FONCTION :
    #    aucun
    #   Fichier vecteur unique contenent tout les traits de cote
    #
    """

    # Mise à jour du Log
    starting_event = "processTDCfilesSmoothAndFusion() : Create final coastline starting : "
    timeLine(path_time_log,starting_event)

    print(endC)
    print(bold + green + "## START : POST TRAITEMENT TDC" + endC)
    print(endC)

    if debug >= 2:
        print(bold + green + "processTDCfilesSmoothAndFusion() : Variables dans la fonction" + endC)
        print(cyan + "processTDCfilesSmoothAndFusion() : " + endC + "coastline_vectors_input_list : " + str(coastline_vectors_input_list) + endC)
        print(cyan + "processTDCfilesSmoothAndFusion() : " + endC + "vector_rocky_input : " + str(vector_rocky_input) + endC)
        print(cyan + "processTDCfilesSmoothAndFusion() : " + endC + "vector_all_output : " + str(vector_all_output) + endC)
        print(cyan + "processTDCfilesSmoothAndFusion() : " + endC + "vector_withrocky_output : " + str(vector_withrocky_output) + endC)
        print(cyan + "processTDCfilesSmoothAndFusion() : " + endC + "generalize_param_method : " + str(generalize_param_method) + endC)
        print(cyan + "processTDCfilesSmoothAndFusion() : " + endC + "generalize_param_threshold : " + str(generalize_param_threshold) + endC)
        print(cyan + "processTDCfilesSmoothAndFusion() : " + endC + "name_column_fusion : " + str(name_column_fusion) + endC)
        print(cyan + "processTDCfilesSmoothAndFusion() : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "processTDCfilesSmoothAndFusion() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "processTDCfilesSmoothAndFusion() : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "processTDCfilesSmoothAndFusion() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "processTDCfilesSmoothAndFusion() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "processTDCfilesSmoothAndFusion() : " + endC + "overwrite : " + str(overwrite) + endC)

    SUFFIX_SMOOTH = "_smooth"
    SUFFIX_TMP = "_tmp"
    SUFFIX_SMOOTH = "_smooth"
    SUFFIX_FUSION = "_fusion"

    repertory_output = os.path.dirname(vector_all_output)
    file_name = os.path.splitext(os.path.basename(vector_all_output))[0]
    vector_fusion = repertory_output + os.sep + file_name + SUFFIX_FUSION + extension_vector

    repertory_temp = repertory_output + os.sep + file_name + SUFFIX_TMP
    if not os.path.exists(repertory_temp):
        os.makedirs(repertory_temp)

    # Vérification de l'existence du vecteur de sortie
    check = os.path.isfile(vector_all_output)

    # Si oui et si la vérification est activée, passage à l'étape suivante
    if check and not overwrite :
        print(cyan + "processTDCfilesSmoothAndFusion() : " + bold + green +  "Vector general coastline already existe : " + str(vector_all_output) + "." + endC)
    # Si non ou si la vérification est désactivée, application des traitements de lissage et de la fusion
    else:
        # Tentative de suppresion des fichiers
        try:
            removeVectorFile(vector_all_output)
            removeVectorFile(vector_withrocky_output)
        except Exception:
            # Ignore l'exception levée si le fichier n'existe pas (et ne peut donc pas être supprimé)
            pass

        # Pour tous les fichiers vecteurs d'entrée appliquer le traitement de lissage par GRASS
        param_generalize_dico = {"method":generalize_param_method, "threshold":generalize_param_threshold}
        vectors_temp_output_list = []

        for input_vector in coastline_vectors_input_list :
            vector_name = os.path.splitext(os.path.basename(input_vector))[0]
            output_temp_vector = repertory_temp + os.sep + vector_name + SUFFIX_TMP + extension_vector
            output_smooth_vector = repertory_temp + os.sep + vector_name + SUFFIX_SMOOTH + extension_vector

            vectors_temp_output_list.append(output_temp_vector)
            xmin, xmax, ymin, ymax = getEmpriseVector(input_vector, format_vector)
            projection, _ = getProjection(input_vector, format_vector)
            if projection is None:
                projection = epsg

            # Init GRASS
            if debug >= 3:
                print(cyan + "processTDCfilesSmoothAndFusion() : " + bold + green +  "Initialisation de GRASS " + endC)
            initializeGrass(repertory_temp, xmin, xmax, ymin, ymax, 1, 1, projection)

            # Generalize GRASS
            if debug >= 3:
                print(cyan + "processTDCfilesSmoothAndFusion() : " + bold + green +  "Applying smooth GRASS for vector : " + str(input_vector) + endC)
            smoothGeomGrass(input_vector, output_smooth_vector, param_generalize_dico, format_vector, overwrite)
            geometries2multigeometries(output_smooth_vector, output_temp_vector, name_column_fusion, format_vector)

            # Init GRASS
            if debug >= 3:
                print(cyan + "processTDCfilesSmoothAndFusion() : " + bold + green +  "Cloture de GRASS " + endC)
            cleanGrass(repertory_temp)

        if debug >= 3:
            print(cyan + "processTDCfilesSmoothAndFusion() : " + bold + green +  "Fusion de tous les vecteurs lissés : " + str(vectors_temp_output_list) + endC)

        # Fusion de tous les fichiers vecteurs temp
        fusionVectors(vectors_temp_output_list, vector_fusion, format_vector)

        # Suppression du champ "cat" introduit par l'application GRASS
        deleteFieldsVector(vector_fusion, vector_all_output, ["cat"], format_vector)

        # Re-met à jour le champ id avec un increment
        updateIndexVector(vector_all_output, "id", format_vector)

        # Nettoyage des zones rocheuses sur la ligne de trait de côte
        if vector_rocky_input != "" and vector_withrocky_output != "":
            if debug >= 3:
                print("\n" + cyan + "processTDCfilesSmoothAndFusion() : " + bold + green +  "Creation d'un trait de côte generale sans les zones rocheuses : " + str(vector_withrocky_output) + endC)
            differenceVector(vector_rocky_input, vector_all_output, vector_withrocky_output, overwrite, format_vector)

    # Suppression des fichiers intermédiaires
    if not save_results_intermediate :
        if debug >= 3:
            print(cyan + "processTDCfilesSmoothAndFusion() : " + bold + green +  "Suppression des fichiers temporaires " + endC)
        if os.path.exists(repertory_temp):
            shutil.rmtree(repertory_temp)
        removeVectorFile(vector_fusion)

    print(endC)
    print(bold + green + "## END :  POST TRAITEMENT TDC" + endC)
    print(endC)

    # Mise à jour du Log
    ending_event = "processTDCfilesSmoothAndFusion() : Create final coastline ending : "
    timeLine(path_time_log,ending_event)

    return

###########################################################################################################################################
# MISE EN PLACE DU PARSER                                                                                                                 #
###########################################################################################################################################

# Code executé seulement dans le cas ou le script est lancé depuis une ligne de commande
# Il n'est pas executé lors d'un import PostTreatmentTDC..py
# Exemple de lancement en ligne de commande:
# python PostTreatmentTDC.py -cvil ../ImagesTestChaine/TDC/vectorCoastline1.shp ../ImagesTestChaine/TDC/vectorCoastline2.shp ../ImagesTestChaine/TDC/vectorCoastline3.shp  -v ../ImagesTestChaine/TDC/vectorCutRockyZone.shp -ova ../ImagesTestChaine/TDC/generalCoastlineComplet.shp -ovw ../ImagesTestChaine/TDC/generalCoastlineWithoutRockyPart.shp -log ../ImagesTestChaine/TDC/fichierTestLog.txt
def main(gui=False):

    # Définition des arguments possibles pour l'appel en ligne de commande
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, prog="PostTreatmentTDC.", description="\
    Info : Create a side-by-side file resulting from the merge of a line part file list after a curve-type interpolation smoothing. \n\
    Objectif : Créer dun fichier trait de côte generale issu de la fusion d'une liste de fichier de partie de trait après un lissage par interpolation de type courbe. \n\
    Example : python PostTreatmentTDC.py -cvil ../ImagesTestChaine/TDC/vectorCoastline1.shp ../ImagesTestChaine/TDC/vectorCoastline2.shp ../ImagesTestChaine/TDC/vectorCoastline3.shp \n\
                                         -v ../ImagesTestChaine/TDC/vectorCutRockyZone.shp \n\
                                         -ova ../ImagesTestChaine/TDC/generalCoastlineFull.shp \n\
                                         -ovw ../ImagesTestChaine/TDC/generalCoastlineWithoutRockyPart.shp \n\
                                         -log ../ImagesTestChaine/TDC/fichierTestLog.txt")

    # Paramètres
    parser.add_argument('-cvil','--coastline_vectors_input_list',default=None,nargs="+",help="List containt vector input to concatened to create general coastline vector", type=str, required=True)
    parser.add_argument('-v','--vector_rocky_input',default="",help="Input rocky zone vector.", type=str, required=False)
    parser.add_argument('-ova','--vector_all_output',default="",help="Vector output result full fusion coastline", type=str, required=True)
    parser.add_argument('-ovw','--vector_withrocky_output',default="",help="Vector output with rocky fusion coastline", type=str, required=False)
    parser.add_argument('-gpm','--generalize_param_method',default="chaiken",help="Param of Grass generalize : methode to use. By default, 'chaiken'", type=str, required=False)
    parser.add_argument('-gpt','--generalize_param_threshold', default=1,help="Param of Grass generalize : volue of threshold . By default, 1", type=int, required=False)
    parser.add_argument('-ncf','--name_column_fusion',default="id",help="Column name used to fusion of lines to polylines. By default, 'id'", type=str, required=False)
    parser.add_argument('-epsg','--epsg', default=2154,help="Projection of the output file.", type=int, required=False)
    parser.add_argument('-vef','--format_vector', default="ESRI Shapefile",help="Format of the output vector file.", type=str, required=False)
    parser.add_argument('-vee','--extension_vector',default=".shp",help="Option : Extension file for vector. By default : '.shp'", type=str, required=False)
    parser.add_argument('-log','--path_time_log',default="",help="Name of log", type=str, required=False)
    parser.add_argument('-sav','--save_results_inter',action='store_true',default=False,help="Save or delete original image after the majority filter. By default, False", required=False)
    parser.add_argument('-now','--overwrite',action='store_false',default=True,help="Overwrite files with same names. By default, True", required=False)
    parser.add_argument('-debug','--debug',default=3,help="Option : Value of level debug trace, default : 3 ",type=int, required=False)
    args = displayIHM(gui, parser)

    # RECUPERATION DES ARGUMENTS
    # Récupération de la liste des fichiers vecteurs d'entrée des traits de côte
    if args.coastline_vectors_input_list != None and args.coastline_vectors_input_list != "":
        coastline_vectors_input_list = args.coastline_vectors_input_list
    else :
        raise NameError (cyan + "PostTreatmentTDC : " + bold + red  + "No coastline vectors found!" + endC)

    # Récupération du fichier vecteur contenant les zones rocheuses
    if args.vector_rocky_input != None:
        vector_rocky_input = args.vector_rocky_input

    # Récupération des vecteurs résultats de sortie
    if args.vector_all_output != None:
        vector_all_output = args.vector_all_output

    if args.vector_withrocky_output != None:
        vector_withrocky_output = args.vector_withrocky_output

    # Récupération des parametres de la fonction generalize de Grass
    if args.generalize_param_method != None :
        generalize_param_method = args.generalize_param_method

    if args.generalize_param_threshold != None :
        generalize_param_threshold = args.generalize_param_threshold

    # Récupération du nom de la colonne pour la fusion
    if args.name_column_fusion != None :
        name_column_fusion = args.name_column_fusion

    # Récupération de la projection du fichier de sortie
    if args.epsg != None :
        epsg = args.epsg

    # Récupération du format du fichier de sortie
    if args.format_vector != None :
        format_vector = args.format_vector

    # Récupération de l'extension des fichiers vecteurs
    if args.extension_vector != None:
        extension_vector = args.extension_vector

    # Récupération du nom du fichier log
    if args.path_time_log!= None:
        path_time_log = args.path_time_log

    # Ecrasement des fichiers
    if args.save_results_inter!= None:
        save_results_intermediate = args.save_results_inter

    if args.overwrite!= None:
        overwrite = args.overwrite

    # Récupération de l'option niveau de debug
    if args.debug!= None:
        global debug
        debug = args.debug

    if debug >= 3:
        print(bold + green + "Variables dans le parser" + endC)
        print(cyan + "PostTreatmentTDC : " + endC + "coastline_vectors_input_list : " + str(coastline_vectors_input_list) + endC)
        print(cyan + "PostTreatmentTDC : " + endC + "vector_rocky_input : " + str(vector_rocky_input) + endC)
        print(cyan + "PostTreatmentTDC : " + endC + "vector_all_output : " + str(vector_all_output) + endC)
        print(cyan + "PostTreatmentTDC : " + endC + "vector_withrocky_output : " + str(vector_withrocky_output) + endC)
        print(cyan + "PostTreatmentTDC : " + endC + "generalize_param_method : " + str(generalize_param_method) + endC)
        print(cyan + "PostTreatmentTDC : " + endC + "generalize_param_threshold : " + str(generalize_param_threshold) + endC)
        print(cyan + "PostTreatmentTDC : " + endC + "name_column_fusion : " + str(name_column_fusion) + endC)
        print(cyan + "PostTreatmentTDC : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "PostTreatmentTDC : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "PostTreatmentTDC : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "PostTreatmentTDC : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "PostTreatmentTDC : " + endC + "save_results_inter : " + str(save_results_intermediate) + endC)
        print(cyan + "PostTreatmentTDC : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "PostTreatmentTDC : " + endC + "debug : " + str(debug) + endC)

    # EXECUTION DE LA FONCTION
    # Si le dossier de sortie n'existe pas, on le crée
    repertory_output = os.path.dirname(vector_all_output)
    if not os.path.isdir(repertory_output):
        os.makedirs(repertory_output)
    if os.path.isfile(vector_withrocky_output):
        repertory_output = os.path.dirname(vector_withrocky_output)
        if not os.path.isdir(repertory_output):
            os.makedirs(repertory_output)

    # Execution de la fonction
    processTDCfilesSmoothAndFusion(coastline_vectors_input_list, vector_rocky_input, vector_all_output, vector_withrocky_output, generalize_param_method, generalize_param_threshold, name_column_fusion, path_time_log, epsg, format_vector, extension_vector, save_results_intermediate, overwrite)

# ================================================

if __name__ == '__main__':
  main(gui=False)
