#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT QUI FUSIONNE DES IMAGES PANCHRO et XS PAR ASSEMBLAGE PANSHARPENING                                                                 #
#                                                                                                                                           #
#############################################################################################################################################
"""
Nom de l'objet : PansharpeningAssembly.py
Description :
-------------
Objectif : Fusioner les images panchro et XS en une seul image
Rq : utilisation des OTB Applications : otbcli_Superimpose, otbcli_Pansharpening

Date de creation : 22/02/2018
----------
Histoire :
----------
Origine : Nouveau
22/02/2018 : Création
-----------------------------------------------------------------------------------------------------
Modifications :

------------------------------------------------------
A Reflechir/A faire :

"""

from __future__ import print_function
import os,sys,argparse,string
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_log import timeLine
from Lib_raster import getPixelWidthXYImage
from Lib_file import removeFile

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 3

###########################################################################################################################################
# FONCTION assembleImagePansharpening()                                                                                                   #
###########################################################################################################################################
def assembleImagePansharpening(image_panchro_input, image_xs_input, image_output, mode_interpolation, method_interpolation, method_pansharpening, interpolation_bco_radius, pansharpening_lmvm_xradius, pansharpening_lmvm_yradius, pansharpening_bayes_lambda, pansharpening_bayes_s, path_time_log, ram_otb=0, format_raster='GTiff', extension_raster=".tif", save_results_intermediate=False, overwrite=True):
    """
    # ROLE:
    #     Reechantillonne l'image XS en fonction de l'image panchro
    #     et assemble (fusionne) les 2 images XS réechantillonée et panchro par algo de pancharpening
    #
    # ENTREES DE LA FONCTION :
    #     image_panchro_input : l'image d'entrée panchro
    #     image_xs_input: l'image d'entrée XS
    #     image_output : l'image de sortie assemblée
    #     mode_interpolation : mode d'interpollation
    #     method_interpolation : algo d'interpolation utilisé
    #     method_pansharpening : algo de pansharpening utilisé
    #     interpolation_bco_radius : parametre radius pour l'interpolation bicubic
    #     pansharpening_lmvm_xradius : parametre xradius pour le pansharpening lmvm
    #     pansharpening_lmvm_yradius : parametre yradius pour le pansharpening lmvm
    #     pansharpening_bayes_lambda : parametre lambda pour le pansharpening bayes
    #     pansharpening_bayes_s : parametre s pour le pansharpening bayes
    #     path_time_log : le fichier de log de sortie
    #     ram_otb : memoire RAM disponible pour les applications OTB
    #     format_raster : Format de l'image de sortie, par défaut : GTiff
    #     extension_raster : extension des fichiers raster de sortie, par defaut = '.tif'
    #     save_results_intermediate : fichiers de sorties intermediaires nettoyees, par defaut = False
    #     overwrite : écrase si un fichier existant a le même nom qu'un fichier de sortie, par defaut a True
    #
    # SORTIES DE LA FONCTION :
    #    une image résultant de la fusion du panchro et du XS
    #
    """

    # Mise à jour du Log
    starting_event = "assembleImagePansharpening() : Pansharpening assembly starting "
    timeLine(path_time_log,starting_event)

    if debug >= 2:
        print(bold + green + "assembleImagePansharpening() : Variables dans la fonction" + endC)
        print(cyan + "assembleImagePansharpening() : " + endC + "image_panchro_input : " + str(image_panchro_input) + endC)
        print(cyan + "assembleImagePansharpening() : " + endC + "image_xs_input : " + str(image_xs_input) + endC)
        print(cyan + "assembleImagePansharpening() : " + endC + "image_output : " + str(image_output) + endC)
        print(cyan + "assembleImagePansharpening() : " + endC + "mode_interpolation : " + str(mode_interpolation) + endC)
        print(cyan + "assembleImagePansharpening() : " + endC + "method_interpolation : " + str(method_interpolation) + endC)
        print(cyan + "assembleImagePansharpening() : " + endC + "method_pansharpening : " + str(method_pansharpening) + endC)
        print(cyan + "assembleImagePansharpening() : " + endC + "interpolation_bco_radius : " + str(interpolation_bco_radius) + endC)
        print(cyan + "assembleImagePansharpening() : " + endC + "pansharpening_lmvm_xradius : " + str(pansharpening_lmvm_xradius) + endC)
        print(cyan + "assembleImagePansharpening() : " + endC + "pansharpening_lmvm_yradius : " + str(pansharpening_lmvm_yradius) + endC)
        print(cyan + "assembleImagePansharpening() : " + endC + "pansharpening_bayes_lambda : " + str(pansharpening_bayes_lambda) + endC)
        print(cyan + "assembleImagePansharpening() : " + endC + "pansharpening_bayes_s : " + str(pansharpening_bayes_s) + endC)
        print(cyan + "assembleImagePansharpening() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "assembleImagePansharpening() : " + endC + "ram_otb : " + str(ram_otb) + endC)
        print(cyan + "assembleImagePansharpening() : " + endC + "format_raster : " + str(format_raster) + endC)
        print(cyan + "assembleImagePansharpening() : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "assembleImagePansharpening() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "assembleImagePansharpening() : " + endC + "overwrite : " + str(overwrite) + endC)

    # Les constantes
    EXT_GEOM = '.geom'
    XS_RESAMPLE_SUFFIX = "_resample"
    CODAGE = "uint16"

    print(endC)
    print(cyan + "assembleImagePansharpening() : " + bold + green + "## START : PANSHARPENING IMAGE" + endC)
    print(endC)

    # ETAPE 0 : PREPARATION

    # Preparation des fichiers intermediaires
    repertory_output = os.path.dirname(image_output)
    image_xs_resample_tmp = repertory_output + os.sep + os.path.splitext(os.path.basename(image_xs_input))[0] + XS_RESAMPLE_SUFFIX + extension_raster

    # Vérification de l'existence de l'image de sortie
    check = os.path.isfile(image_output)

    # Si oui et si la vérification est activée, passage à l'étape suivante
    if check and not overwrite :
        print(cyan + "assembleImagePansharpening() : " + bold + green +  "Image de sortie existe déja : " + image_output + endC)
    # Si non ou si la vérification est désactivée, assemblage
    else:
        # Tentative de suppresion du fichier
        try:
            removeFile(image_output)
        except Exception:
            # Ignore l'exception levée si le fichier n'existe pas (et ne peut donc pas être supprimé)
            pass


        # ETAPE 1 : REECHANTILLONAGE DU FICHIER XS A LA RESOLUTION DU PANCHRO

        # Commande de mise en place de la geométrie re-echantionage
        command = "otbcli_Superimpose -inr " + image_panchro_input + " -inm " + image_xs_input + " -mode " + mode_interpolation + " -interpolator " + method_interpolation + " -out " + image_xs_resample_tmp

        if method_interpolation.lower() == 'bco' :
            command += " -interpolator.bco.radius " + str(interpolation_bco_radius)

        if ram_otb > 0:
            command += " -ram %d" %(ram_otb)

        if debug >= 4:
            print(cyan + "assembleImagePansharpening() : " + bold + green + "SUPERIMPOSE DU FICHIER %s" %(image_xs_input) + endC)
            print(command)

        exit_code = os.system(command)
        if exit_code != 0:
            print(command)
            raise NameError (cyan + "assembleImagePansharpening() : " + bold + red + "!!! Une erreur c'est produite au cours du superimpose de l'image : " + image_xs_input + ". Voir message d'erreur." + endC)


        # ETAPE 2 : ASSEMBLE DES 2 FICHIERS PANCHRO + XS POUR CREER LE FICHIER DE SORTIE

        # Commande de d'assemnlage pansharpening
        command = "otbcli_Pansharpening -inp " + image_panchro_input + " -inxs " + image_xs_resample_tmp + " -method " + method_pansharpening + " -out " + image_output + " " + CODAGE

        if method_pansharpening.lower() == 'lmvm' :
            command += " -method.lmvm.radiusx " + str(pansharpening_lmvm_xradius) + " -method.lmvm.radiusy " + str(pansharpening_lmvm_yradius)

        if method_pansharpening.lower() == 'bayes' :
            command += " -method.bayes.lambda " + str(pansharpening_bayes_lambda) + " -method.bayes.s " + str(pansharpening_bayes_s)

        if ram_otb > 0:
            command += " -ram %d" %(ram_otb)

        if debug >= 4:
            print(cyan + "assembleImagePansharpening() : " + bold + green + "PANSHARPENING DES FICHIERS %s ET %s" %(image_panchro_input, image_xs_resample_tmp) + endC)
            print(command)

        exit_code = os.system(command)
        if exit_code != 0:
            raise NameError (cyan + "assembleImagePansharpening() : " + bold + red + "!!! Une erreur c'est produite au cours du pansharpening l'image : " + image_output + ". Voir message d'erreur." + endC)


   # ETAPE 3 : SUPPRESIONS FICHIERS INTERMEDIAIRES INUTILES

    # Suppression des données intermédiaires
    if not save_results_intermediate:

        if os.path.isfile(image_xs_resample_tmp) :
            removeFile(image_xs_resample_tmp)
        if os.path.isfile(os.path.splitext(image_xs_resample_tmp)[0] + EXT_GEOM) : # suppression du fichier de géométrie associé
            removeFile(os.path.splitext(image_xs_resample_tmp)[0] + EXT_GEOM)

    print(endC)
    print(cyan + "assembleImagePansharpening() : " + bold + green + "## END : PANSHARPENING IMAGE" + endC)
    print(endC)

    # Mise à jour du Log
    ending_event = "assembleImagePansharpening() : Pansharpening assembly ending "
    timeLine(path_time_log,ending_event)

    return

###########################################################################################################################################
# MISE EN PLACE DU PARSER                                                                                                                 #
###########################################################################################################################################

# Code executé seulement dans le cas ou le script est lancé depuis une ligne de commande
# Il n'est pas executé lors d'un import PansharpeningAssembly.py
# Exemple de lancement en ligne de commande:
# python PansharpeningAssembly.py -ip /mnt/Data/10_Agents_travaux_en_cours/Gilles/Test_appli_PansharpeningAssembly/IMG_S7P_2015092536255065CP.tif  -ixs /mnt/Data/10_Agents_travaux_en_cours/Gilles/Test_appli_PansharpeningAssembly/IMG_S7X_2015092536255066CP.tif -o /mnt/Data/10_Agents_travaux_en_cours/Gilles/Test_appli_PansharpeningAssembly/Image_P_and_XS_assembled.tif -methi bco -methp bayes -log /mnt/Data/10_Agents_travaux_en_cours/Gilles/Test_appli_PansharpeningAssembly/fichierTestLog.txt

def main(gui=False):

    # Définition des différents paramètres du parser
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,  prog="PansharpeningAssembly", description="\
    Info : Assembly panchro image and XS image to one image. \n\
    Objectif : Assembler une image partie panchro et XS separes. \n\
    Example : python PansharpeningAssembly.py -ip /mnt/Data/10_Agents_travaux_en_cours/Gilles/Test_appli_PansharpeningAssembly/IMG_S7P_2015092536255065CP.tif \n\
                                     -ixs /mnt/Data/10_Agents_travaux_en_cours/Gilles/Test_appli_PansharpeningAssembly/IMG_S7X_2015092536255066CP.tif \n\
                                     -o /mnt/Data/10_Agents_travaux_en_cours/Gilles/Test_appli_PansharpeningAssembly/Image_P_and_XS_assembled.tif \n\
                                     -methi bco \n\
                                     -methp bayes \n\
                                     -log /mnt/Data/10_Agents_travaux_en_cours/Gilles/Test_appli_PansharpeningAssembly/fichierTestLog.txt")

    parser.add_argument('-ip','--image_panchro_input',default="",help="Panchro image input.", type=str, required=True)
    parser.add_argument('-ixs','--image_xs_input',default="",help="XS image input.", type=str, required=True)
    parser.add_argument('-o','--image_output',default="",help="Assembly image output.", type=str, required=True)
    parser.add_argument('-modi','--mode_interpolation',default="default",help="Mode interpolation used (Choice of : 'Default mode (default)', 'Pleiades mode (phr)'). By default, 'default'.", type=str, required=False)
    parser.add_argument('-methi','--method_interpolation',default="bco",help="Algo method interpolation used (Choice of : 'Bicubic interpolation (bco)', 'Nearest Neighbor interpolation (nn)', 'Linear interpolation (linear)'). By default, 'bco'.", type=str, required=False)
    parser.add_argument('-methp','--method_pansharpening',default="bayes",help="Algo metode pansharpening used (Choice of : 'Simple RCS (rcs)', 'Local Mean and Variance Matching (lmvm)', 'Bayesian (bayes)'). By default, 'bayes'.", type=str, required=False)
    parser.add_argument('-interp.bco.r','--interpolation_bco_radius',default=2,help="Radius for bicubic interpolation parameter", type=int, required=False)
    parser.add_argument('-pansh.lmvm.rx','--pansharpening_lmvm_xradius',default=3,help="X radius coefficient, methode lmvm pansharpening parameter", type=int, required=False)
    parser.add_argument('-pansh.lmvm.ry','--pansharpening_lmvm_yradius',default=3,help="Y radius coefficient, methode lmvm pansharpening parameter", type=int, required=False)
    parser.add_argument('-pansh.bayes.lb','--pansharpening_bayes_lambda',default=0.9999,help="Weight lambda coefficient, methode bayes pansharpening parameter", type=float, required=False)
    parser.add_argument('-pansh.bayes.s','--pansharpening_bayes_s',default=1.0,help="S coefficient, methode bayes pansharpening parameter", type=float, required=False)
    parser.add_argument('-ram','--ram_otb',default=0,help="Ram available for processing otb applications (in MB)", type=int, required=False)
    parser.add_argument('-raf','--format_raster', default="GTiff", help="Option : Format output image, by default : GTiff (GTiff, HFA...)", type=str, required=False)
    parser.add_argument('-rae','--extension_raster', default=".tif", help="Option : Extension file for image raster. By default : '.tif'", type=str, required=False)
    parser.add_argument('-log','--path_time_log',default="",help="Name of log", type=str, required=False)
    parser.add_argument('-sav','--save_results_inter',action='store_true',default=False,help="Save or delete intermediate result after the process. By default, False", required=False)
    parser.add_argument('-now','--overwrite',action='store_false',default=True,help="Overwrite files with same names. By default, True", required=False)
    parser.add_argument('-debug','--debug',default=3,help="Option : Value of level debug trace, default : 3 ",type=int, required=False)
    args = displayIHM(gui, parser)

    # RECUPERATION DES ARGUMENTS

    # Récupération de l'image panchro d'entrée
    if args.image_panchro_input != None:
        image_panchro_input = args.image_panchro_input
        if not os.path.isfile(image_panchro_input):
            raise NameError (cyan + "PansharpeningAssembly : " + bold + red  + "File %s not existe!" %(image_panchro_input) + endC)

    # Récupération de l'image xs d'entrée
    if args.image_xs_input != None :
        image_xs_input = args.image_xs_input
        if not os.path.isfile(image_xs_input):
            raise NameError (cyan + "PansharpeningAssembly : " + bold + red  + "File %s not existe!" %(image_xs_input) + endC)

    # Récupération du fichier de sortie
    if args.image_output != None:
        image_output = args.image_output

    # Récupération du parametre mode interpolation
    if args.mode_interpolation != None:
        mode_interpolation = args.mode_interpolation

    # Récupération du parametre methode interpolation
    if args.method_interpolation != None:
        method_interpolation = args.method_interpolation

    # Récupération du parametre methode pansharpening
    if args.method_pansharpening != None:
        method_pansharpening = args.method_pansharpening

    # Récupération du parametre radius pour l'interpolation bicubic
    if args.interpolation_bco_radius!= None:
        interpolation_bco_radius = args.interpolation_bco_radius

    # Récupération du parametre x radius pour le pensharpening lmvm
    if args.pansharpening_lmvm_xradius!= None:
        pansharpening_lmvm_xradius = args.pansharpening_lmvm_xradius

    # Récupération du parametre y radius pour le pensharpening lmvm
    if args.pansharpening_lmvm_yradius!= None:
        pansharpening_lmvm_yradius = args.pansharpening_lmvm_yradius

    # Récupération du parametre lambda pour le pensharpening bayes
    if args.pansharpening_bayes_lambda!= None:
        pansharpening_bayes_lambda = args.pansharpening_bayes_lambda

    # Récupération du parametre s pour le pensharpening bayes
    if args.pansharpening_bayes_s!= None:
        pansharpening_bayes_s = args.pansharpening_bayes_s

    # Récupération du parametre ram
    if args.ram_otb != None:
        ram_otb = args.ram_otb

    # Paramètre format des images de sortie
    if args.format_raster != None:
        format_raster = args.format_raster

    # Paramètre de l'extension des images rasters
    if args.extension_raster != None:
        extension_raster = args.extension_raster

    # Récupération du nom du fichier log
    if args.path_time_log!= None:
        path_time_log = args.path_time_log

    # Récupération de l'option écrasement
    if args.save_results_inter != None:
        save_results_intermediate = args.save_results_inter

    if args.overwrite!= None:
        overwrite = args.overwrite

    # Récupération de l'option niveau de debug
    if args.debug!= None:
        global debug
        debug = args.debug

    if debug >= 3:
        print(bold + green + "PansharpeningAssembly : Variables dans le parser" + endC)
        print(cyan + "PansharpeningAssembly : " + endC + "image_panchro_input : " + str(image_panchro_input) + endC)
        print(cyan + "PansharpeningAssembly : " + endC + "image_xs_input : " + str(image_xs_input) + endC)
        print(cyan + "PansharpeningAssembly : " + endC + "image_output : " + str(image_output) + endC)
        print(cyan + "PansharpeningAssembly : " + endC + "mode_interpolation : " + str(mode_interpolation) + endC)
        print(cyan + "PansharpeningAssembly : " + endC + "method_interpolation : " + str(method_interpolation) + endC)
        print(cyan + "PansharpeningAssembly : " + endC + "method_pansharpening : " + str(method_pansharpening) + endC)
        print(cyan + "PansharpeningAssembly : " + endC + "interpolation_bco_radius : " + str(interpolation_bco_radius) + endC)
        print(cyan + "PansharpeningAssembly : " + endC + "pansharpening_lmvm_xradius : " + str(pansharpening_lmvm_xradius) + endC)
        print(cyan + "PansharpeningAssembly : " + endC + "pansharpening_lmvm_yradius : " + str(pansharpening_lmvm_yradius) + endC)
        print(cyan + "PansharpeningAssembly : " + endC + "pansharpening_bayes_lambda : " + str(pansharpening_bayes_lambda) + endC)
        print(cyan + "PansharpeningAssembly : " + endC + "pansharpening_bayes_s : " + str(pansharpening_bayes_s) + endC)
        print(cyan + "PansharpeningAssembly : " + endC + "ram_otb : " + str(ram_otb) + endC)
        print(cyan + "PansharpeningAssembly : " + endC + "format_raster : " + str(format_raster) + endC)
        print(cyan + "PansharpeningAssembly : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "PansharpeningAssembly : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "PansharpeningAssembly : " + endC + "save_results_inter : " + str(save_results_intermediate) + endC)
        print(cyan + "PansharpeningAssembly : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "PansharpeningAssembly : " + endC + "debug : " + str(debug) + endC)

    # EXECUTION DE LA FONCTION
    # Si le dossier de sortie n'existent pas, on le crée
    repertory_output = os.path.dirname(image_output)
    if not os.path.isdir(repertory_output):
        os.makedirs(repertory_output)

    # Execution de la fonction pour une image
    assembleImagePansharpening(image_panchro_input, image_xs_input, image_output, mode_interpolation, method_interpolation, method_pansharpening, interpolation_bco_radius, pansharpening_lmvm_xradius, pansharpening_lmvm_yradius, pansharpening_bayes_lambda, pansharpening_bayes_s, path_time_log, ram_otb, format_raster, extension_raster, save_results_intermediate, overwrite)

# ================================================

if __name__ == '__main__':
  main(gui=False)
