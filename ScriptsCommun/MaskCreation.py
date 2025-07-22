#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT QUI REMPLACE PAR 0 LES PIXELS D'UNE IMAGE PLACES HORS DE VECTEURS DE DECOUPAGE ET PAR 1 LES PIXELS A L'INTERIEUR DES POLYGONES     #
#                                                                                                                                           #
#############################################################################################################################################
"""
Nom de l'objet : MaskCreation.py
Description :
-------------
Objectif : Créer un masque binaire raster
Rq : utilisation des OTB Applications : otbcli_Rasterization

Date de creation : 31/07/2014
----------
Histoire :
----------
Origine : le script originel provient du fichier Chain2_MasksCreation.py cree en 2013 et utilise par la chaine de traitement OCSOL V1.X
31/07/2014 : Transformation en brique elementaire (suppression des liens avec la chaine OCSOL)
-----------------------------------------------------------------------------------------------------
Modifications :
01/10/2014 : refonte du fichier harmonisation des régles de qualitées des niveaux de boucles et des paramétres dans args
21/05/2015 : simplification des parametres en argument plus de liste d'image en emtrée à traiter uniquement une image
08/03/2017 : simplification de l'application sans la gestion de la superposition et rasterisation pour une seul image (macro classe) à la fois
------------------------------------------------------
A Reflechir/A faire :

"""

from __future__ import print_function
import os,sys,glob,argparse,string
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_raster import rasterizeBinaryVector, bufferBinaryRaster
from Lib_log import timeLine
from Lib_file import removeFile

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 3

###########################################################################################################################################
# FONCTION createMask()                                                                                                                   #
###########################################################################################################################################
def createMask(image_input, vector_samples_input, image_masked, path_time_log, buffer_mask=0, save_results_intermediate=False, overwrite=True):
    """
    # ROLE:
    #     remplace par 0 les pixels d'une image places hors de vecteurs de decoupage et par 1 les pixels a l'interieur des polygones
    #     Compléments sur la fonction rasterization : http://www.orfeo-toolbox.org/CookBook/CookBooksu71.html#x99-2770005.2.2
    #
    # ENTREES DE LA FONCTION :
    #     image_input : l'image d'entrée qui servira de base aux vecteurs masques
    #     vector_samples_input : le vecteur à transformer en image masque
    #     image_masked : l'image de sortie masqué
    #     path_time_log : le fichier de log de sortie
    #     buffer_mask : taille du buffer à appliquer sur le masque, par defaut = 0
    #     save_results_intermediate : fichiers de sorties intermediaires nettoyees, par defaut = False
    #     overwrite : écrase si un fichier existant a le même nom qu'un fichier de sortie, par defaut a True
    #
    # SORTIES DE LA FONCTION :
    #    un masque binaire par vecteur d'entrée compatible avec l'image (hors vectors : pixel = 0, dans le vecteur : pixel = 1)
    #
    """

    # Mise à jour du Log
    starting_event = "createMask() : Masks creation starting : "
    timeLine(path_time_log,starting_event)

    print(endC)
    print(bold + green + "## START : MASQUES CREATION" + endC)
    print(endC)

    CODAGE = "uint8"

    if debug >= 2:
        print(bold + green + "createMask() : Variables dans la fonction" + endC)
        print(cyan + "createMask() : " + endC + "image_input : " + str(image_input) + endC)
        print(cyan + "createMask() : " + endC + "vector_samples_input : " + str(vector_samples_input) + endC)
        print(cyan + "createMask() : " + endC + "image_masked : " + str(image_masked) + endC)
        print(cyan + "createMask() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "createMask() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "createMask() : " + endC + "overwrite : " + str(overwrite) + endC)

    # RASTERIZATION DES VECTEURS D'APPRENTISSAGE

    # VERIFICATION SI LE MASQUE DE SORTIE EXISTE DEJA
    # Si un fichier de sortie avec le même nom existe déjà, et si l'option ecrasement est à false, alors passe au masque suivant
    check = os.path.isfile(image_masked)
    if check and not overwrite:
        print(bold + yellow +  "createMask() : " + endC + "Computing mask from %s with %s already done : no actualisation" % (image_input, vector_samples_input) + endC)
    # Si non, ou si la fonction ecrasement est désative, alors on le calcule
    else:
        if check:
            try: # Suppression de l'éventuel fichier existant
                removeFile(image_masked)
            except Exception:
                pass # Si le fichier ne peut pas être supprimé, on suppose qu'il n'existe pas et on passe à la suite

        # EXTRACTION DU MASQUE
        print(bold + green +  "createMask() : " + endC + "Computing mask from %s with %s " %(image_input, vector_samples_input) + endC)

        rasterizeBinaryVector(vector_samples_input, image_input, image_masked, 1, CODAGE)

        if buffer_mask!=0:
            # bufferisation du masque
            bufferBinaryRaster(image_masked,image_masked,buffer_mask)

        print(bold + green +  "createMask() : " + endC + "Computing mask from %s with %s completed" %(image_input, vector_samples_input) + endC)

    print(endC)
    print(bold + green + "## END : MASQUES CREATION" + endC)
    print(endC)

    # Mise à jour du Log
    ending_event = "createMask() : Masks creation ending : "
    timeLine(path_time_log,ending_event)

    return

###########################################################################################################################################
# MISE EN PLACE DU PARSER                                                                                                                 #
###########################################################################################################################################

# Code executé seulement dans le cas ou le script est lancé depuis une ligne de commande
# Il n'est pas executé lors d'un import MaskCreation.py
# Exemple de lancement en ligne de commande:
# python MaskCreation.py -i /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/CUB_zone_test_NE.tif  -vl /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/Sample_Entrainement/CUB_zone_test_NE_Bati_entrainement.shp /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/Sample_Entrainement/CUB_zone_test_NE_Eau_entrainement.shp /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/Sample_Entrainement/CUB_zone_test_NE_Route_entrainement.shp /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/Sample_Entrainement/CUB_zone_test_NE_Solnu_entrainement.shp /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/Sample_Entrainement/CUB_zone_test_NE_Vegetation_entrainement.shp -ol /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/Macro/CUB_zone_test_NE_Bati_mask.tif /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/Macro/CUB_zone_test_NE_Eau_mask.tif /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/Macro/CUB_zone_test_NE_Route_mask.tif /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/Macro/CUB_zone_test_NE_Solnu_mask.tif /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/Macro/CUB_zone_test_NE_Vegetation_mask.tif -covl -log /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/fichierTestLog.txt
# python MaskCreation.py -i ../ImagesTestChaine/APTV_05/APTV_05.tif  -vl ../ImagesTestChaine/APTV_05/Echantillons/APTV_05_Anthropise_entrainement.shp ../ImagesTestChaine/APTV_05/Echantillons/APTV_05_Eau_entrainement.shp -ol ../ImagesTestChaine/APTV_05/Macro/APTV_05_Anthropise_mask.tif ../ImagesTestChaine/APTV_05/Macro/APTV_05_Eau_mask.tif  -covl -log ../ImagesTestChaine/APTV_05/fichierTestLog.txt

def main(gui=False):

    # Définition des différents paramètres du parser
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,  prog="MaskCreation", description="\
    Info : Transform an image into binary mask under polygons of cutting. \n\
    Documentation : http://orfeo-toolbox.org/Applications/Rasterization.html \n\
    Objectif : Creer un masque binaire raster. \n\
    Example : python MaskCreation.py -i /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/CUB_zone_test_NE.tif \n\
                                     -v /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/Sample_Entrainement/CUB_zone_test_NE_Bati_entrainement.shp \n\
                                     -o /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/Macro/CUB_zone_test_NE_Bati_mask.tif \n\
                                     -log /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/fichierTestLog.txt")

    parser.add_argument('-i','--image_input',default="",help="Image ref input to treat", type=str, required=True)
    parser.add_argument('-v','--vector_samples_input',default="",help="Input samples vector refere to input image.", type=str, required=True)
    parser.add_argument('-o','--image_mask_output',default="",help="Mask image output.", type=str, required=True)
    parser.add_argument('-log','--path_time_log',default="",help="Name of log", type=str, required=False)
    parser.add_argument('-b','--buffer_size',default=0,help="Size of buffer. By default, 0", type=int, required=False)
    parser.add_argument('-sav','--save_results_inter',action='store_true',default=False,help="Save or delete intermediate result after the process. By default, False", required=False)
    parser.add_argument('-now','--overwrite',action='store_false',default=True,help="Overwrite files with same names. By default, True", required=False)
    parser.add_argument('-debug','--debug',default=3,help="Option : Value of level debug trace, default : 3 ",type=int, required=False)
    args = displayIHM(gui, parser)

    # RECUPERATION DES ARGUMENTS

    # Récupération de l'image d'entrée
    if args.image_input != None:
        image_input = args.image_input
        if not os.path.isfile(image_input):
            raise NameError (cyan + "MaskCreation : " + bold + red  + "File %s not existe!" %(image_input) + endC)

    # Récupération des vecteurs d'entrée
    if args.vector_samples_input != None :
        vector_samples_input = args.vector_samples_input
        if not os.path.isfile(vector_samples_input):
            raise NameError (cyan + "MaskCreation : " + bold + red  + "File %s not existe!" %(vector_samples_input) + endC)

    # Récupération des fichiers masque de sortie
    if args.image_mask_output != None:
        image_mask_output=args.image_mask_output

    # Récupération du nom du fichier log
    if args.path_time_log != None:
        path_time_log = args.path_time_log

    # Récupération de la taille du buffer
    if args.buffer_size != None:
        buffer_size = args.buffer_size

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
        print(bold + green + "MaskCreation : Variables dans le parser" + endC)
        print(cyan + "MaskCreation : " + endC + "image_input : " + str(image_input) + endC)
        print(cyan + "MaskCreation : " + endC + "vector_samples_input : " + str(vector_samples_input) + endC)
        print(cyan + "MaskCreation : " + endC + "image_mask_output : " + str(image_mask_output) + endC)
        print(cyan + "MaskCreation : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "MaskCreation : " + endC + "buffer_size : " + str(buffer_size) + endC)
        print(cyan + "MaskCreation : " + endC + "save_results_inter : " + str(save_results_intermediate) + endC)
        print(cyan + "MaskCreation : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "MaskCreation : " + endC + "debug : " + str(debug) + endC)

    # EXECUTION DE LA FONCTION
    # Si les dossiers de sortie n'existent pas, on les crées
    repertory_output = os.path.dirname(image_mask_output)
    if not os.path.isdir(repertory_output):
        os.makedirs(repertory_output)

    # execution de la fonction pour une image
    createMask(image_input, vector_samples_input, image_mask_output, path_time_log, buffer_size, save_results_intermediate, overwrite)

# ================================================

if __name__ == '__main__':
  main(gui=False)
