#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerSO/DALETT/SCGSI  All rights reserved.                                                                            #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT QUI FUSIONNE LES MICRO CLASSES EN MACRO CLASSES                                                                                    #
#                                                                                                                                           #
#############################################################################################################################################
'''
Nom de l'objet : MicroClassesFusion.py
Description :
    Objectif : fusionner des classes
    Rq : utilisation des OTB Applications :   otbcli_BandMath

Date de creation : 30/07/2014
----------
Histoire :
----------
Origine : le script originel provient du fichier Chain7_FusionOfMicroclasses.py cree en 2013 et utilise par la chaine de traitement OCSOL V1.X
30/07/2013 : Transformation en brique elementaire (suppression des liens avec la chaine OCSOL)
-----------------------------------------------------------------------------------------------------
Modifications
30/07/2013 : choix > supprimer pathTimelog > remplacer verifActivation par overwrite et mettre a True par defaut
04/08/2014 : amélioration de la gestion des listes dans args
01/10/2014 : refonte du fichier harmonisation des régles de qualitées des niveaux de boucles et des paramétres dans args
21/05/2015 : simplification des parametres en argument plus de liste d'image en emtrée à traiter uniquement une image
------------------------------------------------------
A Reflechir/A faire
- traduire le docstring en anglais
'''

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
# FONCTION mergeMicroclasses()                                                                                                            #
###########################################################################################################################################
# ROLE:
#    Fusionner des microclasses dans une macroclasse hierarchiquement supérieure
#
# ENTREES DE LA FONCTION :
#    image_input : image avec des classes à fusionner par un BandMath
#    fusioned_image_output : image resultat de la fusion
#    path_time_log : le fichier de log de sortie
#    expression : par defaut pour des microclasses avec des valeurs de type 11001,11002,12001,12002... et des macroclasses de type 11000,12000...
#    save_microclasses_intput_image : sauvegarde ou suppression des images utilisee en entree, par defaut à False
#    overwrite : boolen ecrasement ou non des fichiers ayant un nom similaire, par defaut a True
#
# SORTIES DE LA FONCTION :
#    auccun
#    Eléments utilisés par la fonction : images avec microclasses à fusionner
#    Eléments générés par la fonction : images avec microclasses fusionnees sauvegardees dans le meme dossier
#
def mergeMicroclasses(image_input, fusioned_image_output, path_time_log, expression="rint(im1b1/100)*100", save_microclasses_intput_image=False, overwrite=True):

    # Mise à jour du Log
    starting_event = "mergeMicroclasses() : Merge micro class starting : "
    timeLine(path_time_log,starting_event),displayIHM

    print(endC)
    print(bold + green + "## START :  FUSION OF MICROCLASSES" + endC)
    print(endC)

    CODAGE = "uint16"

    if debug >= 3:
        print(bold + green + "Variables dans le parser" + endC)
        print(cyan + "mergeMicroclasses() : " + endC + "image_input : " + str(image_input) + endC)
        print(cyan + "mergeMicroclasses() : " + endC + "fusioned_image_output : " + str(fusioned_image_output) + endC)
        print(cyan + "mergeMicroclasses() : " + endC + "expression : " + str(expression) + endC)
        print(cyan + "mergeMicroclasses() : " + endC + "save_microclasses_intput_image : " + str(save_microclasses_intput_image) + endC)
        print(cyan + "mergeMicroclasses() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "mergeMicroclasses() : " + endC + "overwrite : " + str(overwrite) + endC)

    check_input = os.path.isfile(image_input)
    if check_input:
        # Vérifie si l'image de sortie existe déjà
        check = os.path.isfile(fusioned_image_output)

        #Si oui et si la vérification est activée, passe à l'étape suivante
        if check and not overwrite :
            print(cyan + "mergeMicroclasses() : " + bold + yellow + "Microclasses have already been merged." + endC)
        else:
            #Tente de supprimer le fichier
            try:
                removeFile(fusioned_image_output)
            except Exception:
                #Ignore l'exception levée si le fichier n'existe pas (et ne peut donc pas être supprimé)
                pass

            print(cyan + "mergeMicroclasses() : " + bold + green + "Merging microclasses..." + '\n' + endC)

            command = "otbcli_BandMath -il %s -out %s %s -exp \"%s\"" %(image_input,fusioned_image_output,CODAGE,expression)
            exit_code = os.system(command)
            if exit_code != 0:
                print(command)
                raise NameError(cyan + "mergeMicroclasses() : " + bold + red +  + "An error occured during otbcli_BandMath command. See error message above." + endC)

            print('\n' + cyan + "mergeMicroclasses() : " + bold + green + "Merging complete!" + endC)
    else:
        raise NameError(cyan + "mergeMicroclasses() : " + bold + red + "No classified file %s found!" %(image_input) + endC)

    # Supression des .geom dans le dossier
    directory_output = os.path.dirname(fusioned_image_output)
    for to_delete in glob.glob(directory_output + os.sep + "*.geom"):
        removeFile(to_delete)

    print(endC)
    print(bold + green + "## END :  FUSION OF MICROCLASSES" + endC)
    print(endC)

    # Mise à jour du Log
    ending_event = "mergeMicroclasses() : Merge micro class ending : "
    timeLine(path_time_log,ending_event)

    return

###########################################################################################################################################
# MISE EN PLACE DU PARSER                                                                                                                 #
###########################################################################################################################################

# Code executé seulement dans le cas ou le script est lancé depuis une ligne de commande
# Il n'est pas executé lors d'un import MicroClassesFusion.py
# Exemple de lancement en ligne de commande:
# python MicroClassesFusion.py -i ../ImagesTestChaine/APTV_05/Micro/APTV_05_stack_raw.tif -o ../ImagesTestChaine/APTV_05/Micro/APTV_05_stack_raw_merged.tif -log ../ImagesTestChaine/APTV_05/fichierTestLog.txt

def main(gui=False):

    # Définition des arguments possibles pour l'appel en ligne de commande
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, prog="MicroClassesFusion", description="\
    Info : Fusion of several microclasses in macroclasses. \n\
    Objectif : Fusionner les micro classes de chaque macro classe. \n\
    Example : python MicroClassesFusion.py -i ../ImagesTestChaine/APTV_05/Micro/APTV_05_stack_raw.tif \n\
                                           -o ../ImagesTestChaine/APTV_05/Micro/APTV_05_stack_raw_merged.tif \n\
                                           -log ../ImagesTestChaine/APTV_05/fichierTestLog.txt")

    # Paramètres
    parser.add_argument('-i','--image_input',default="",help="Image input to treat", type=str, required=True)
    parser.add_argument('-o','--image_output',default="",help="Image output result fusion of micro class classification", type=str, required=True)
    parser.add_argument('-exp','--expression',default="rint(im1b1/100)*100",help="Expression for identify microclasses to merge together", type=str, required=False)
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
            raise NameError (cyan + "MicroClassesFusion : " + bold + red  + "File %s not existe!" %(image_input) + endC)

    # Récupération de l'image de sortie
    if args.image_output != None:
        image_output = args.image_output

    # Expression de fusion des micro classes
    if args.expression!= None:
        expression = args.expression

    # Récupération du nom du fichier log
    if args.path_time_log!= None:
        path_time_log = args.path_time_log

    if args.save_results_inter!= None:
        save_microclasses_intput_image = args.save_results_inter

    if args.overwrite!= None:
        overwrite = args.overwrite

    # Récupération de l'option niveau de debug
    if args.debug!= None:
        global debug
        debug = args.debug

    if debug >= 3:
        print(bold + green + "Variables dans le parser" + endC)
        print(cyan + "MicroClassesFusion : " + endC + "image_input : " + str(image_input) + endC)
        print(cyan + "MicroClassesFusion : " + endC + "image_output : " + str(image_output) + endC)
        print(cyan + "MicroClassesFusion : " + endC + "expression : " + str(expression) + endC)
        print(cyan + "MicroClassesFusion : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "MicroClassesFusion : " + endC + "save_results_inter : " + str(save_microclasses_intput_image) + endC)
        print(cyan + "MicroClassesFusion : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "MicroClassesFusion : " + endC + "debug : " + str(debug) + endC)

    # EXECUTION DE LA FONCTION
    # Si le dossier de sortie n'existe pas, on le crée
    repertory_output = os.path.dirname(image_output)
    if not os.path.isdir(repertory_output):
        os.makedirs(repertory_output)

    # execution de la fonction pour une image
    mergeMicroclasses(image_input, image_output, path_time_log, expression, save_microclasses_intput_image, overwrite)

# ================================================

if __name__ == '__main__':
  main(gui=False)


