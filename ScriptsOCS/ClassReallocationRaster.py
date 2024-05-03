#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT FAIT UNE RE LABELLISATION AUTOMATIQUE SUR UN RASTER A PARTIR D'UNE TABLE DE RELABELLISATION                                        #
#                                                                                                                                           #
#############################################################################################################################################
"""
Nom de l'objet : ClassReallocationRaster.py
Description :
-------------
Objectif :  Relabelliser automatiquement un raster à partir d'une table de relabellisation
Rq : utilisation des OTB Applications :   otbcli_BandMath

Date de creation : 01/10/2014
----------
Histoire :
----------
Origine : le script originel provient du fichier Chain10_PostTraitement.py (creerTableModifier()) cree en 2013 et utilise par la chaine de traitement OCSOL V1.X
01/10/2014 : Transformation en brique elementaire (suppression des liens avec la chaine OCSOL)
06/03/2015 : Extraction de la partie raster du script ClassReallocationRaster
-----------------------------------------------------------------------------------------------------
Modifications :
01/10/2014 : refonte du fichier harmonisation des régles de qualitées des niveaux de boucles et des paramétres dans args
21/05/2015 : simplification des parametres en argument plus de liste d'image en emtrée à traiter uniquement une image
------------------------------------------------------
A Reflechir/A faire :

"""

# Import des bibliothèques python
from __future__ import print_function
import os,sys,glob,string,shutil,time,argparse
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_log import timeLine
from Lib_text import readReallocationTable
from Lib_raster import reallocateClassRaster

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 3

###########################################################################################################################################
# FONCTION reallocClassRaster                                                                                                             #
###########################################################################################################################################
def reallocClassRaster(image_input, image_output, table_reallocation, path_time_log, overwrite=True) :
    """
    # ROLE:
    #     Réaffecter les micro classes du resultat de la classification en fonction de la table de proposition sur un fichier raster
    #
    # ENTREES DE LA FONCTION :
    #     image_input : image classée en plusieurs classes au format.tif
    #     image_output : image re-classée en fonction des info de la table de réallocation au format.tif
    #     table_reallocation : fichier contenant la table de proposition de reaffectation des micro classes (au format texte)
    #     path_time_log : le fichier de log de sortie
    #     overwrite : supprime ou non les fichiers existants ayant le meme nom
    #
    # SORTIES DE LA FONCTION :
    #     aucun
    #     Eléments modifiés l'image de classification micro classes
    """

    # Mise à jour du Log
    starting_event = "reallocClassRaster() : Realocation micro class on classification image starting : "
    timeLine(path_time_log,starting_event)

    CODAGE = "uint16"

    if debug >= 3:
       print(cyan + "reallocClassRaster() : " + endC + "image_input : " +  str(image_input))
       print(cyan + "reallocClassRaster() : " + endC + "image_output : " + str(image_output))
       print(cyan + "reallocClassRaster() : " + endC + "table_reallocation : " + str(table_reallocation))
       print(cyan + "reallocClassRaster() : " + endC + "path_time_log : " + str(path_time_log))
       print(cyan + "reallocClassRaster() : " + endC + "overwrite : " + str(overwrite))

    print(cyan + "reallocClassRaster() : " + bold + green + "START ...\n" + endC)

    # Lecture du fichier table de proposition
    supp_class_list, reaff_class_list, macro_reaff_class_list, sub_sampling_class_list, sub_sampling_number_list = readReallocationTable(table_reallocation)

    if debug >= 3:
        print("supp_class_list : " + str(supp_class_list))
        print("reaff_class_list : " + str(reaff_class_list))
        print("macro_reaff_class_list : " + str(macro_reaff_class_list))

    # Gestion du cas de suppression
    if len(supp_class_list) > 0:
        print(cyan + "reallocClassRaster() : " + bold + yellow + "ATTENTION : Les classes %s vont être supprimees dans le  fichier classification format raster." %(str(supp_class_list))  + endC)
        for supp_class in  supp_class_list :
            reaff_class_list.append(supp_class)
            macro_reaff_class_list.append(0)

    # Gestion du cas de réaffectation
    if len(reaff_class_list) > 0:
        reallocateClassRaster(image_input, image_output, reaff_class_list, macro_reaff_class_list, CODAGE)
    else :
        shutil.copyfile(image_input, image_output)

    print(cyan + "reallocClassRaster() : " + bold + green + "END\n" + endC)

    # Mise à jour du Log
    ending_event = "reallocClassRaster() : Realocation micro class on classification image ending : "
    timeLine(path_time_log,ending_event)
    return

###########################################################################################################################################
# MISE EN PLACE DU PARSER                                                                                                                 #
###########################################################################################################################################

# Code executé seulement dans le cas ou le script est lancé depuis une ligne de commande
# Il n'est pas executé lors d'un import ClassReallocationRaster.py
# Exemple de lancement en ligne de commande:
# python ClassReallocationRaster.py -i ../ImagesTestChaine/APTV_05/Micro/APTV_05_stack_raw.tif -t ../ImagesTestChaine/APTV_05/Micro/APTV_05_prop_tab.txt -o ../ImagesTestChaine/APTV_05/Micro/APTV_05_stack_raw2.tif -log ../ImagesTestChaine/APTV_05/fichierTestLog.txt

def main(gui=False):

    # Définition des arguments possibles pour l'appel en ligne de commande
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,  prog="ClassReallocationRaster", description="\
    Info : Automatic reallocation of class, from raster. \n\
    Objectif : Relabelliser automatiquement un raster a partir d'une table de relabellisation. \n\
    Example : python ClassReallocationRaster.py -i ../ImagesTestChaine/APTV_05/Micro/APTV_05_stack_raw.tif \n\
                                                -t ../ImagesTestChaine/APTV_05/Micro/APTV_05_prop_tab.txt \n\
                                                -o ../ImagesTestChaine/APTV_05/Micro/APTV_05_stack_raw2.tif \n\
                                                -log ../ImagesTestChaine/APTV_05/fichierTestLog.txt")

    # Paramètres
    parser.add_argument('-i','--image_input',default="",help="Image input to treat", type=str, required=True)
    parser.add_argument('-t','--proposal_table_input',default="",help="Proposal table input to realocation micro class", type=str, required=True)
    parser.add_argument('-o','--image_output',default="",help="Image output re-allocated . Warning!!! if is emppty the input image file is modified.", type=str, required=False)
    parser.add_argument('-log','--path_time_log',default="",help="Name of log", type=str, required=False)
    parser.add_argument('-sav','--save_results_inter',action='store_true',default=False,help="Save or delete intermediate result after the process. By default, False", required=False)
    parser.add_argument('-now','--overwrite',action='store_false',default=True,help="Overwrite files with same names. By default, True", required=False)
    parser.add_argument('-debug','--debug',default=3,help="Option : Value of level debug trace, default : 3 ",type=int, required=False)
    args = displayIHM(gui, parser)

    # RECUPERATION DES ARGUMENTS
    # Récupération de l'image d'entrée
    if args.image_input != None:
        image_input = args.image_input
        if not os.path.isfile(image_input):
            raise NameError (cyan + "ClassReallocationRaster : " + bold + red  + "File %s not existe!" %(image_input) + endC)

    # Récupération de la table de proposition d'entrée
    if args.proposal_table_input != None:
        proposal_table_input = args.proposal_table_input
        if not os.path.isfile(proposal_table_input):
            raise NameError (cyan + "ClassReallocationRaster : " + bold + red  + "File %s not existe!" %(proposal_table_input) + endC)

    # Récupération de l'image de sortie
    if args.image_output != None:
        image_output = args.image_output

    # Récupération du nom du fichier log
    if args.path_time_log!= None:
        path_time_log = args.path_time_log

    if args.save_results_inter != None:
        save_results_intermediate = args.save_results_inter

    if args.overwrite!= None:
        overwrite = args.overwrite

    # Récupération de l'option niveau de debug
    if args.debug!= None:
        global debug
        debug = args.debug

    # Affichage des arguments récupérés
    if debug >= 3:
        print(bold + green + "Variables dans le parser" + endC)
        print(cyan + "ClassReallocationRaster : " + endC + "image_input : " + str(image_input) + endC)
        print(cyan + "ClassReallocationRaster : " + endC + "proposal_table_input : " + str(proposal_table_input) + endC)
        print(cyan + "ClassReallocationRaster : " + endC + "image_output : " + str(image_output) + endC)
        print(cyan + "ClassReallocationRaster : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "ClassReallocationRaster : " + endC + "save_results_inter : " + str(save_results_intermediate) + endC)
        print(cyan + "ClassReallocationRaster : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "ClassReallocationRaster : " + endC + "debug : " + str(debug) + endC)

    # EXECUTION DE LA FONCTION
    # Si le dossier de sortie n'existe pas, on le crée
    if image_output != None:
        repertory_output = os.path.dirname(image_output)
        if not os.path.isdir(repertory_output):
            os.makedirs(repertory_output)

    # reallocation
    reallocClassRaster(image_input, image_output, proposal_table_input, path_time_log, overwrite)

# ================================================

if __name__ == '__main__':
  main(gui=False)
