#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT FAIT UNE REALLOCATION AUTOMATIQUE DE CLASSES                                                                                       #
#                                                                                                                                           #
#############################################################################################################################################
"""
Nom de l'objet : ClassReallocationVector.py
Description :
-------------
Objectif :  Gérer la re affectation de classes
en réaffectant sur les vecteurs d'apprentissage en micro-classe de la classification supervisée - Suppressions et réaffectations possibles

Date de creation : 01/10/2014
----------
Histoire :
----------
Origine : le script originel provient du fichier Chain10_PostTraitement.py (creerTableModifier()) cree en 2013 et utilise par la chaine de traitement OCSOL V1.X
01/10/2014 : Transformation en brique elementaire (suppression des liens avec la chaine OCSOL)
-----------------------------------------------------------------------------------------------------
Modifications :
01/10/2014 : refonte du fichier harmonisation des régles de qualitées des niveaux de boucles et des paramétres dans args
11/03/2015 : separation de ClassReallocation.py en ClassReallocationVector.py et ClassReallocationRaster.py
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
from Lib_file import copyVectorFile
from Lib_vector import deleteClassVector,reallocateClassVector

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 3

###########################################################################################################################################
# FONCTION reallocClassVector                                                                                                             #
###########################################################################################################################################
def reallocClassVector(validation_vector_file, table_reallocation, path_time_log, field="id", format_vector='ESRI Shapefile', save_results_intermediate=False, overwrite=True) :
    """
    # ROLE:
    #     Réaffecter les micro classes des echantillons en fonction de la table de proposition
    #
    # ENTREES DE LA FONCTION :
    #    validation_vector_file : echantillons de validation au format.shp
    #    table_reallocation : fichier contenant la table de proposition de reaffectation des micro classes (au format texte)
    #    path_time_log : le fichier de log de sortie
    #    field : le champs contenant le label de classe, par defaut = "id"
    #    format_vector : format du fichier vecteur. Optionnel, par default : 'ESRI Shapefile'
    #    save_results_intermediate : fichiers de sorties intermediaires non nettoyées, par defaut = False
    #    overwrite : supprime ou non les fichiers existants ayant le meme nom
    #
    # SORTIES DE LA FONCTION :
    #    auccun
    #    Eléments modifiés les vecteurs des échantillons de micro classes
    #
    """

    # Mise à jour du Log
    starting_event = "reallocClassVector() : Realocation micro class on samples vector starting : "
    timeLine(path_time_log,starting_event)

    if debug >= 3:
       print(cyan + "reallocClassVector() : " + endC + "validation_vector_file : " +  str(validation_vector_file))
       print(cyan + "reallocClassVector() : " + endC + "table_reallocation : " + str(table_reallocation))
       print(cyan + "reallocClassVector() : " + endC + "path_time_log : " + str(path_time_log))
       print(cyan + "reallocClassVector() : " + endC + "field : " + str(field))
       print(cyan + "reallocClassVector() : " + endC + "format_vector : " + str(format_vector))
       print(cyan + "reallocClassVector() : " + endC + "save_results_inter : " + str(save_results_intermediate) + endC)
       print(cyan + "reallocClassVector() : " + endC + "overwrite : " + str(overwrite))

    print("")
    print(cyan + "reallocClassVector() : " + bold + green + "START ..." + endC)

    # Lecture du fichier table de proposition
    supp_class_list, reaff_class_list, macro_reaff_class_list, sub_sampling_class_list, sub_sampling_number_list = readReallocationTable(table_reallocation)
    if debug >= 3:
        print(cyan + "reallocClassVector() : " + endC + "supp_class_list : " + str(supp_class_list))
        print(cyan + "reallocClassVector() : " + endC + "reaff_class_list : " + str(reaff_class_list))
        print(cyan + "reallocClassVector() : " + endC + "macro_reaff_class_list : " + str(macro_reaff_class_list))

    # Cas de suppression
    if len(supp_class_list) > 0:
        deleteClassVector(supp_class_list, validation_vector_file, field, format_vector)
    # Cas de réaffectation
    if len(reaff_class_list) > 0:
        reallocateClassVector(reaff_class_list, macro_reaff_class_list, validation_vector_file, field, format_vector)

    print(cyan + "reallocClassVector() : " + bold + green + "END\n" + endC)

    # Mise à jour du Log
    ending_event = "reallocClassVector() : Realocation micro class on samples vector ending : "
    timeLine(path_time_log,ending_event)
    return

###########################################################################################################################################
# MISE EN PLACE DU PARSER                                                                                                                 #
###########################################################################################################################################

# Code executé seulement dans le cas ou le script est lancé depuis une ligne de commande
# Il n'est pas executé lors d'un import ClassReallocationVector.py
# Exemple de lancement en ligne de commande:
# python ClassReallocationVector.py -v ../ImagesTestChaine/APTV_05/Micro/APTV_05_cleaned.shp -t ../ImagesTestChaine/APTV_05/Micro/APTV_05_prop_tab.txt -id id -log ../ImagesTestChaine/APTV_05/fichierTestLog.txt

def main(gui=False):

    # Définition des arguments possibles pour l'appel en ligne de commande
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,  prog="ClassReallocationVector", description="\
    Info : Automatic reallocation of class, from vector. \n\
    Objectif : Gerer la re affectation de classes en reaffectant sur les vecteurs d'apprentissage en micro-classe de la classification supervisee, \n\
    suppressions et reaffectations possibles. \n\
    Example : python ClassReallocationVector.py -v ../ImagesTestChaine/APTV_05/Micro/APTV_05_cleaned.shp \n\
                                                -t ../ImagesTestChaine/APTV_05/Micro/APTV_05_prop_tab.txt \n\
                                                -id id \n\
                                                -log ../ImagesTestChaine/APTV_05/fichierTestLog.txt")

    # Paramètres
    parser.add_argument('-v','--vector_input',default="",help="Vector input contain the validation sample", type=str, required=True)
    parser.add_argument('-t','--proposal_table_input',default="",help="Proposal table input to realocation micro class", type=str, required=True)
    parser.add_argument('-o','--vector_output',default="",help="Vector output re-allocated . Warning!!! if is emppty the input vector file is modified.", type=str, required=False)
    parser.add_argument('-id','--validation_id',default="id",help="Label to identify the class", type=str, required=False)
    parser.add_argument('-vef','--format_vector', default="ESRI Shapefile",help="Format of the output file.", type=str, required=False)
    parser.add_argument('-log','--path_time_log',default="",help="Name of log", type=str, required=False)
    parser.add_argument('-sav','--save_results_inter',action='store_true',default=False,help="Save or delete intermediate result after the process. By default, False", required=False)
    parser.add_argument('-now','--overwrite',action='store_false',default=True,help="Overwrite files with same names. By default, True", required=False)
    parser.add_argument('-debug','--debug',default=3,help="Option : Value of level debug trace, default : 3 ",type=int, required=False)
    args = displayIHM(gui, parser)

    # RECUPERATION DES ARGUMENTS

    # Récupération du fichier vecteur d'entrée
    if args.vector_input != None:
        vector_input = args.vector_input
        if not os.path.isfile(vector_input):
            raise NameError (cyan + "ClassReallocationVector : " + bold + red  + "File %s not existe!" %(vector_input) + endC)

    # Récupération de la table de proposition d'entrée
    if args.proposal_table_input != None:
        proposal_table_input = args.proposal_table_input
        if not os.path.isfile(proposal_table_input):
            raise NameError (cyan + "ClassReallocationVector : " + bold + red  + "File %s not existe!" %(proposal_table_input) + endC)

    # Récupération du vecteur de sortie
    if args.vector_output != None and args.vector_output != "":
        vector_output = args.vector_output
    else :
        vector_output = None

    # field validation
    if args.validation_id != None:
        validation_id_field = args.validation_id

    # Récupération du format du fichier de sortie
    if args.format_vector != None :
        format_vector = args.format_vector

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
        print(cyan + "ClassReallocationVector : " + endC + "vector_input : " + str(vector_input) + endC)
        print(cyan + "ClassReallocationVector : " + endC + "proposal_table_input : " + str(proposal_table_input) + endC)
        print(cyan + "ClassReallocationRaster : " + endC + "vector_output : " + str(vector_output) + endC)
        print(cyan + "ClassReallocationVector : " + endC + "validation_id : " + str(validation_id_field) + endC)
        print(cyan + "ClassReallocationVector : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "ClassReallocationVector : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "ClassReallocationVector : " + endC + "save_results_inter : " + str(save_results_intermediate) + endC)
        print(cyan + "ClassReallocationVector : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "ClassReallocationVector : " + endC + "debug : " + str(debug) + endC)

    # EXECUTION DE LA FONCTION
    vector_file = vector_input

    if vector_output != None :
        repertory_output = os.path.dirname(vector_output)
        if not os.path.isdir(repertory_output):
            os.makedirs(repertory_output)
        try:
            copyVectorFile(vector_input, vector_output, format_vector)
        except RuntimeError:
            raise NameError(cyan + "ClassReallocationVector() : " + bold + red + "An error occured during copy file : " + vector_input + " See error message above." + endC)
        vector_file = vector_output

    # reallocation
    reallocClassVector(vector_file, proposal_table_input, path_time_log, validation_id_field, format_vector, save_results_intermediate, overwrite)

# ================================================

if __name__ == '__main__':
  main(gui=False)
