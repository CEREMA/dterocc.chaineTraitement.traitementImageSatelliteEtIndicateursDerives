#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT QUI APPLIQUE UN FILTRE MAJORITAIRE A UNE IMAGE (classee ou non)                                                                    #
#                                                                                                                                           #
#############################################################################################################################################
"""
Nom de l'objet : MajorityFilter.py
Description :
-------------
Objectif : appliquer un filtre majoritaire a une image (classee ou non)
Rq : utilisation des OTB Applications :   otbcli_ClassificationMapRegularization

Date de creation : 29/07/2014
----------
Histoire :
----------
Origine : le script originel provient du fichier Chain8_MapRegularization.py cree en 2013 et utilise par la chaine de traitement OCSOL V1.X
29/07/2013 : Transformation en brique elementaire (suppression des liens avec la chaine OCSOL)
-----------------------------------------------------------------------------------------------------
Modifications :
04/08/2014 : ajout parametre overwrite et mise en forme commentaires parametres, amélioration gestion des listes simples dans args
01/10/2014 : refonte du fichier harmonisation des régles de qualitées des niveaux de boucles et des paramétres dans args
21/05/2015 : simplification des parametres en argument plus de liste d'image en emtrée à traiter uniquement une image
------------------------------------------------------
A Reflechir/A faire :
sauvegarder les résultats dans un autre dossier que le dossier en entree ?
"""

from __future__ import print_function
import os,sys,glob,string,argparse
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_log import timeLine
from Lib_file import removeFile

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 3

###########################################################################################################################################
# FONCTION filterImageMajority()                                                                                                          #
###########################################################################################################################################
def filterImageMajority(image_input, filtered_image_output, filter_mode, radius, umc_pixels, path_time_log, ram_otb=0, save_results_intermediate=False, overwrite=True):
    """
    # ROLE:
    #    appliquer un filtre majoritaire à une image (classée ou non)
    #
    # ENTREES DE LA FONCTION :
    #    image_input : nom image à filtrer
    #    filtered_image_output : nom image filtrée de sortie
    #    filter_mode : mode de filtrage par otb ou par gdal
    #    radius : taille fenêtre du filtre cas traitement otbcli_ClassificationMapRegularization
    #    umc_pixels : taille de l'umc en pixel cas traitement gdal_sieve
    #    path_time_log : le fichier de log de sortie
    #    ram_otb : memoire RAM disponible pour les applications OTB
    #    save_results_intermediate : fichiers de sorties intermediaires non nettoyées, par defaut = False
    #    overwrite : supprime ou non les fichiers existants ayant le meme nom, par defaut a True
    #
    # SORTIES DE LA FONCTION :
    #    aucun
    #   Eléments utilisés par la fonction : image à filtrer présentes dans un dossier spécifique
    #   Eléments générés par le script : image filtree sauvegardee dans le même dossier
    #
    """

    # Mise à jour du Log
    starting_event = "filterImageMajority() : Filter image starting : "
    timeLine(path_time_log,starting_event)

    print(endC)
    print(bold + green + "## START : MAP REGULARIZATION" + endC)
    print(endC)

    CODAGE = "uint16"

    if debug >= 2:
        print(bold + green + "filterImageMajority() : Variables dans la fonction" + endC)
        print(cyan + "filterImageMajority() : " + endC + "image_input : " + str(image_input) + endC)
        print(cyan + "filterImageMajority() : " + endC + "filtered_image_output : " + str(filtered_image_output) + endC)
        print(cyan + "filterImageMajority() : " + endC + "filter_mode : " + str(filter_mode) + endC)
        print(cyan + "filterImageMajority() : " + endC + "radius : " + str(radius) + endC)
        print(cyan + "filterImageMajority() : " + endC + "umc_pixels : " + str(umc_pixels) + endC)
        print(cyan + "filterImageMajority() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "filterImageMajority() : " + endC + "ram_otb : " + str(ram_otb) + endC)
        print(cyan + "filterImageMajority() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "filterImageMajority() : " + endC + "overwrite : " + str(overwrite) + endC)

    # Vérification de l'existence d'une image filtrée
    check = os.path.isfile(filtered_image_output)

    # Si oui et si la vérification est activée, passage à l'étape suivante
    if check and not overwrite :
        print(cyan + "filterImageMajority() : " + bold + green +  "Image already filtered with window size of " + str(radius) + "." + endC)
    # Si non ou si la vérification est désactivée, application du filtre
    else:
        # Tentative de suppresion du fichier
        try:
            removeFile(filtered_image_output)
        except Exception:
            # Ignore l'exception levée si le fichier n'existe pas (et ne peut donc pas être supprimé)
            pass

        if debug >= 3:
            print(cyan + "filterImageMajority() : " + bold + green +  "Applying majority filter with window size " , str(radius) , "..." , '\n' + endC)

        # Selon le mode de filtrage
        if filter_mode.lower() == "otb":
            # Par otbcli_ClassificationMapRegularization
            command = "otbcli_ClassificationMapRegularization -io.in %s -io.out %s %s -ip.radius %d" %(image_input,filtered_image_output,CODAGE,radius)
            if ram_otb > 0:
                command += " -ram %d" %(ram_otb)
        else :
            # Par gdal_sieve
            command = "gdal_sieve.py -st %d -8 %s %s" %(umc_pixels,image_input,filtered_image_output)

        if debug >= 3:
            print(command)
        exitCode = os.system(command)
        if exitCode != 0:
            raise NameError(cyan + "filterImageMajority() : " + bold + red + "An error occured during otbcli_ClassificationMapRegularization command. See error message above.")
        print('\n' + cyan + "filterImageMajority() : " + bold + green + "Filter applied!" + endC)



    # Supression des .geom dans le dossier
    directory_output = os.path.dirname(filtered_image_output)
    for to_delete in glob.glob(directory_output + os.sep + "*.geom"):
        removeFile(to_delete)

    print(endC)
    print(bold + green + "## END :  MAP REGULARIZATION" + endC)
    print(endC)

    # Mise à jour du Log
    ending_event = "filterImageMajority() : Filter image ending : "
    timeLine(path_time_log,ending_event)

    return

###########################################################################################################################################
# MISE EN PLACE DU PARSER                                                                                                                 #
###########################################################################################################################################

# Code executé seulement dans le cas ou le script est lancé depuis une ligne de commande
# Il n'est pas executé lors d'un import MajorityFilter.py
# Exemple de lancement en ligne de commande:
# python MajorityFilter.py -i ../ImagesTestChaine/APTV_05/Micro/APTV_05_stack_raw_merged.tif -o ../ImagesTestChaine/APTV_05/Micro/APTV_05_stack_raw_merged_filtered.tif -m otb -r 2 -log ../ImagesTestChaine/APTV_05/fichierTestLog.txt

def main(gui=False):

    # Définition des arguments possibles pour l'appel en ligne de commande
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, prog="MajorityFilter", description="\
    Info : Applying a majority filter on one or several images. \n\
    Objectif : Appliquer un filtre majoritaire a une image (classee ou non). \n\
    Example : python MajorityFilter.py -i ../ImagesTestChaine/APTV_05/Micro/APTV_05_stack_raw_merged.tif \n\
                                       -o ../ImagesTestChaine/APTV_05/Micro/APTV_05_stack_raw_merged_filtered.tif \n\
                                       -m otb \n\
                                       -r 2 \n\
                                       -log ../ImagesTestChaine/APTV_05/fichierTestLog.txt")

    # Paramètres
    parser.add_argument('-i','--image_input',default="",help="Image input to treat", type=str, required=True)
    parser.add_argument('-o','--image_output',default="",help="Image output result input image filted", type=str, required=True)
    parser.add_argument('-m','--filter_mode',default="otb",help="type of filtrage Majority by OTB or Sieve by GDAL (List of values : otb, gdal). By default : otb.",type=str, required=False)
    parser.add_argument('-r','--fm_radius',default=2,help="Radius of the majority filter",type=int, required=False)
    parser.add_argument('-umc','--umc_pixels',default=2,help="UMC (in number of pixels). Size of pixel polygon to replace by the neigbour majority. By default : 2.", type=int, required=False)
    parser.add_argument('-ram','--ram_otb',default=0,help="Ram available for processing otb applications (in MB)", type=int, required=False)
    parser.add_argument('-log','--path_time_log',default="",help="Name of log", type=str, required=False)
    parser.add_argument('-sav','--save_results_inter',action='store_true',default=False,help="Save or delete original image after the majority filter. By default, False", required=False)
    parser.add_argument('-now','--overwrite',action='store_false',default=True,help="Overwrite files with same names. By default, True", required=False)
    parser.add_argument('-debug','--debug',default=3,help="Option : Value of level debug trace, default : 3 ",type=int, required=False)
    args = displayIHM(gui, parser)

    # RECUPERATION DES ARGUMENTS

    # Récupération de l'image d'entrée
    if args.image_input != None:
        image_input = args.image_input
        if not os.path.isfile(image_input):
            raise NameError (cyan + "MajorityFilter : " + bold + red  + "File %s not existe!" %(image_input) + endC)

    # Récupération de l'image de sortie
    if args.image_output != None:
        image_output = args.image_output

    # Récupération choix du filtre
    if args.filter_mode != None:
        filter_mode = args.filter_mode
        if filter_mode.lower() not in ['otb', 'gdal'] :
            raise NameError(cyan + "MajorityFilter : " + bold + red + "Parameter 'filter_mode' value  is not in list ['otb', 'gdal']." + endC)

    # Le paramétre du rayon pour le filtre majoritaire otb
    if args.fm_radius != None:
        radius = args.fm_radius

    # Le paramétre de l'umc pixel pour le traitement majoritaire gdal
    if args.umc_pixels!= None:
        umc_pixels = args.umc_pixels

    # Récupération du parametre ram
    if args.ram_otb != None:
        ram_otb = args.ram_otb

    # Récupération du nom du fichier log
    if args.path_time_log!= None:
        path_time_log = args.path_time_log

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
        print(cyan + "MajorityFilter : " + endC + "image_input : " + str(image_input) + endC)
        print(cyan + "MajorityFilter : " + endC + "image_output : " + str(image_output) + endC)
        print(cyan + "MajorityFilter : " + endC + "filter_mode : " + str(filter_mode) + endC)
        print(cyan + "MajorityFilter : " + endC + "fm_radius : " + str(radius) + endC)
        print(cyan + "MajorityFilter : " + endC + "umc_pixels : " + str(umc_pixels) + endC)
        print(cyan + "MajorityFilter : " + endC + "ram_otb : " + str(ram_otb) + endC)
        print(cyan + "MajorityFilter : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "MajorityFilter : " + endC + "save_results_inter : " + str(save_results_intermediate) + endC)
        print(cyan + "MajorityFilter : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "MajorityFilter : " + endC + "debug : " + str(debug) + endC)

    # EXECUTION DE LA FONCTION
    # Si le dossier de sortie n'existe pas, on le crée
    repertory_output = os.path.dirname(image_output)
    if not os.path.isdir(repertory_output):
        os.makedirs(repertory_output)

    # execution de la fonction pour une image
    filterImageMajority(image_input, image_output, filter_mode, radius, umc_pixels, path_time_log, ram_otb, save_results_intermediate, overwrite)

# ================================================

if __name__ == '__main__':
  main(gui=False)
