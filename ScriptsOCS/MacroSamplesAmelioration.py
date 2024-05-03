#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT D'AMELIORATION DES ECHANTILLONS MACRO                                                                                              #
#                                                                                                                                           #
#############################################################################################################################################
"""
Nom de l'objet : MacroSamplesAmelioration.py
Description :
-------------
Objectif : Améliorer la qualité des échantillons de macro classes
Rq : utilisation des OTB Applications :   otbcli_BandMath, otbcli_BinaryMorphologicalOperation

Date de creation : 25/03/2015
----------
Histoire :
----------
Origine : nouveau

-----------------------------------------------------------------------------------------------------
Modifications :
21/05/2015 : simplification des parametres en argument plus de liste d'image en emtrée à traiter uniquement une image
------------------------------------------------------
A Reflechir/A faire :

"""

# Import des bibliothèques python
from __future__ import print_function
import os,sys,glob,shutil,string, argparse
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_log import timeLine
from Lib_file import cleanTempData, deleteDir, removeFile
from Lib_raster import createBinaryMaskThreshold, filterBinaryRaster, applyMaskAnd, applyMaskOr

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 3

###########################################################################################################################################
# FONCTION processMacroSamples()                                                                                                          #
###########################################################################################################################################
def processMacroSamples(image_input, image_output, correction_images_input_list, treatment_mask_list, macro_sample_name, path_time_log, extension_raster=".tif", save_results_intermediate=False, overwrite=True) :
    """
    # ROLE:
    #    Traiter les fichiers d'apprentissage raster
    #
    # ENTREES DE LA FONCTION :
    #    image_input : image du masque d'entrée à traiter
    #    image_output : image de sortie corrigée
    #    correction_images_input_list : liste des images pour la correction
    #    treatment_mask_list : liste contenant parametres des corrections à appliquer pour chaque image de correction
    #    macro_sample_name : nom de l'echantillon macro
    #    path_time_log : le fichier de log de sortie
    #    extension_raster : extension des fichiers raster de sortie, par defaut = '.tif'
    #    save_results_intermediate : fichiers de sorties intermediaires nettoyees, par defaut = False
    #    overwrite : boolen ecrasement ou non des fichiers ayant un nom similaire, par defaut à True
    #
    # SORTIES DE LA FONCTION :
    #    auccun
    #    Eléments générés par la fonction : une image de masque modifiée par les images de correction et les paramètres de correction
    """

    # Mise à jour du Log
    starting_event = "processMacroSamples() : process macro samples starting : "
    timeLine(path_time_log,starting_event)

    if debug >= 3:
        print(bold + green + "processMacroSamples() : Variables dans la fonction" + endC)
        print(cyan + "processMacroSamples() : " + endC + "image_input : " + str(image_input) + endC)
        print(cyan + "processMacroSamples() : " + endC + "image_output : " + str(image_output) + endC)
        print(cyan + "processMacroSamples() : " + endC + "correction_images_input_list : " + str(correction_images_input_list) + endC)
        print(cyan + "processMacroSamples() : " + endC + "treatment_mask_list : " + str(treatment_mask_list) + endC)
        print(cyan + "processMacroSamples() : " + endC + "macro_sample_name : " + str(macro_sample_name) + endC)
        print(cyan + "processMacroSamples() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "processMacroSamples() : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "processMacroSamples() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "processMacroSamples() : " + endC + "overwrite : " + str(overwrite) + endC)

    # Constantes
    FOLDER_MASK_TEMP = 'Mask_'
    CODAGE = "uint8"

    print(cyan + "processMacroSamples() : " + bold + green + "Nettoyage de l'espace de travail..." + endC)

    # Définition du répertoire temporaire
    repertory_samples_output = os.path.dirname(image_output)
    repertory_temp = repertory_samples_output + os.sep + FOLDER_MASK_TEMP + macro_sample_name

    # Création du répertoire temporaire si il n'existe pas
    if not os.path.isdir(repertory_temp):
        os.makedirs(repertory_temp)

    # Nettoyage du répertoire temporaire si il n'est pas vide
    cleanTempData(repertory_temp)

    # Test si le fichier résultat existent déjà et si ils doivent être écrasés
    check = os.path.isfile(image_output)
    if check and not overwrite: # Si les fichiers echantillons existent deja et que overwrite n'est pas activé
        print(bold + yellow + "File output : " + image_output + " already exists and will not be created again." + endC)
    else :
        if check:
            try:
                removeFile(image_output)
            except Exception:
                pass # si le fichier n'existe pas, il ne peut pas être supprimé : cette étape est ignorée

        # Information issue de la liste des paramètres de traitement
        if correction_images_input_list == [] :
            # Pas de traitement à faire simple copie
            if debug >= 1:
                print(cyan + "processMacroSamples() : " + endC + "Copy file" +  image_input + " to " + image_output)
            shutil.copyfile(image_input, image_output)
        else :
            # Liste de tous les traitement à faire
            cpt_treat = 0
            sample_raster_file_output = image_output
            for idx_treatement in range(len(correction_images_input_list)):

                treatement_info_list = treatment_mask_list[idx_treatement]
                file_mask_input = correction_images_input_list[idx_treatement]

                if debug >= 3:
                    print(cyan + "processMacroSamples() : " + endC + "Traitement parametres : " + str(treatement_info_list) + " avec l'image : " + file_mask_input)

                base_mask_name = treatement_info_list[0]
                threshold_min = float(treatement_info_list[1])
                threshold_max = float(treatement_info_list[2])

                if len(treatement_info_list) >= 4:
                    filter_size_zone_0 = int(treatement_info_list[3])
                else :
                    filter_size_zone_0 = 0

                if len(treatement_info_list) >= 5:
                    filter_size_zone_1 = int(treatement_info_list[4])
                else :
                    filter_size_zone_1 = 0

                if len(treatement_info_list) >= 6:
                    mask_operator = str(treatement_info_list[5])
                else :
                    mask_operator = "and"

                if cpt_treat == 0:
                    sample_raster_file_input_temp = image_input

                # Appel de la fonction de traitement
                processingMacroSample(sample_raster_file_input_temp, sample_raster_file_output, file_mask_input, threshold_min, threshold_max, filter_size_zone_0, filter_size_zone_1, mask_operator, repertory_temp, CODAGE, path_time_log)

                cpt_treat+=1

                if cpt_treat != len(correction_images_input_list) :
                    sample_raster_file_input_temp = os.path.splitext(sample_raster_file_output)[0] +str(cpt_treat) + extension_raster
                    os.rename(sample_raster_file_output, sample_raster_file_input_temp)

                # Nettoyage du traitement precedent
                sample_raster_file_input_temp_before = os.path.splitext(sample_raster_file_output)[0] +str(cpt_treat-1) + extension_raster
                if os.path.isfile(sample_raster_file_input_temp_before) :
                    removeFile(sample_raster_file_input_temp_before)

    print(cyan + "processMacroSamples() : " + bold + green + "Fin des traitements" + endC)

    # Suppression des données intermédiaires
    if not save_results_intermediate:

        # Supression des .geom dans le dossier
        for to_delete in glob.glob(repertory_samples_output + os.sep + "*.geom"):
            removeFile(to_delete)

        # Suppression du repertoire temporaire
        deleteDir(repertory_temp)

    # Mise à jour du Log
    ending_event = "processMacroSamples() : process macro samples ending : "
    timeLine(path_time_log,ending_event)

    return

###########################################################################################################################################
# FONCTION processMacroSamples()                                                                                                          #
###########################################################################################################################################
def processingMacroSample(sample_raster_file_input, sample_raster_file_output, file_mask_input, threshold_min, threshold_max, filter_size_zone_0, filter_size_zone_1, mask_operator, repertory_temp, codage, path_time_log) :
    """
    # ROLE:
    #    Traiter fichier d'apprentissage avec le fichier d'amelioration
    #
    # ENTREES DE LA FONCTION :
    #    sample_raster_file_input : fichier d'entrée contenant les echantillons macro à traiter
    #    sample_raster_file_output : fichier de sortie contenant les echantillons macro crées
    #    file_mask_input : le fichier d'entrée d'amélioration servant de base pour le masque
    #    threshold_min : seuil minimal pour la rasterisation en fichier binaire (masque) du fichier d'amélioration
    #    threshold_max : seuil maximal pour la rasterisation en fichier binaire (masque) du fichier d'amélioration
    #    filter_size_zone_0 : parametre de filtrage du masque définie la taille de la feparser.add_argument('-debug','--debug',default=3,help="Option : Value of level debug trace, default : 3 ",type=int, required=False)nêtre pour les zones à 0
    #    filter_size_zone_1 : parametre de filtrage du masque définie la taille de la fenêtre pour les zones à 1
    #    mask_operator : operateur de fusion entre l'image source et le nouveau masque creer : possible :(and, or)
    #    repertory_temp : repertoire temporaire de travail
    #    codage : type de codage du fichier de sortie
    #    path_time_log : le fichier de log de sortie
    #
    # SORTIES DE LA FONCTION :
    #    auccun
    #    Eléments générés par la fonction : raster d'echantillon masquer avec le fichier d'amelioration
    #
    """

    # Mise à jour du Log
    starting_event = "processingMacroSample() : processing macro sample starting : "
    timeLine(path_time_log,starting_event)

    if debug >= 3:
        print(" ")
        print(bold + green + "processingMacroSample() : Variables dans la fonction" + endC)
        print(cyan + "processingMacroSample() : " + endC + "sample_raster_file_input : " + str(sample_raster_file_input) + endC)
        print(cyan + "processingMacroSample() : " + endC + "sample_raster_file_output : " + str(sample_raster_file_output) + endC)
        print(cyan + "processingMacroSample() : " + endC + "file_mask_input : " + str(file_mask_input) + endC)
        print(cyan + "processingMacroSample() : " + endC + "threshold_min : " + str(threshold_min) + endC)
        print(cyan + "processingMacroSample() : " + endC + "threshold_max : " + str(threshold_max) + endC)
        print(cyan + "processingMacroSample() : " + endC + "filter_size_zone_0 : " + str(filter_size_zone_0) + endC)
        print(cyan + "processingMacroSample() : " + endC + "filter_size_zone_1 : " + str(filter_size_zone_1) + endC)
        print(cyan + "processingMacroSample() : " + endC + "mask_operator : " + str(mask_operator) + endC)
        print(cyan + "processingMacroSample() : " + endC + "repertory_temp : " + str(repertory_temp) + endC)
        print(cyan + "processingMacroSample() : " + endC + "codage : " + str(codage) + endC)
        print(cyan + "processingMacroSample() : " + endC + "path_time_log : " + str(path_time_log) + endC)

    print(cyan + "processingMacroSample() : " + bold + green + "Traitement en cours..." + endC)

    # Traitement préparation
    file_mask_output_temp = repertory_temp + os.sep + os.path.splitext(os.path.basename(file_mask_input))[0] + "_mask_tmp" + os.path.splitext(file_mask_input)[1]
    if os.path.isfile(file_mask_output_temp) :
        removeFile(file_mask_output_temp)
    file_mask_filtered_output_temp = repertory_temp + os.sep + os.path.splitext(os.path.basename(file_mask_input))[0] + "_mask_filtered_tmp" + os.path.splitext(file_mask_input)[1]
    if os.path.isfile(file_mask_filtered_output_temp) :
        removeFile(file_mask_filtered_output_temp)

    # Creation masque binaire
    createBinaryMaskThreshold(file_mask_input, file_mask_output_temp, threshold_min, threshold_max)

    # Filtrage binaire
    if filter_size_zone_0 != 0 or filter_size_zone_1 != 0 :
        filterBinaryRaster(file_mask_output_temp, file_mask_filtered_output_temp, filter_size_zone_0, filter_size_zone_1)
    else :
        file_mask_filtered_output_temp = file_mask_output_temp

    # Masquage des zones non retenues
    if mask_operator.lower() == "and" :
        applyMaskAnd(sample_raster_file_input, file_mask_filtered_output_temp, sample_raster_file_output, codage)
    elif mask_operator.lower() == "or" :
        applyMaskOr(sample_raster_file_input, file_mask_filtered_output_temp, sample_raster_file_output, codage)
    else :
        raise NameError (cyan + "processingMacroSample() : " + bold + red  + "Mask operator unknown : " + str(mask_operator) + endC)

    print(cyan + "processingMacroSample() : " + bold + green + "Fin du traitement" + endC)

    # Mise à jour du Log
    ending_event = "processingMacroSample() : processing macro sample ending : "
    timeLine(path_time_log,ending_event)

    return

###########################################################################################################################################
# MISE EN PLACE DU PARSER                                                                                                                 #
###########################################################################################################################################

# Code executé seulement dans le cas ou le script est lancé depuis une ligne de commande
# Il n'est pas executé lors d'un import MacroSamplesAmelioration.py
# Exemple de lancement en ligne de commande:
# python MacroSamplesAmelioration.py -i /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/Macro/CUB_zone_test_NE_Bati_mask.tif -o /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/Macro/CUB_zone_test_NE_Bati_mask_cleaned.tif -cil /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/Neocanaux/CUB_zone_test_NE_MNH.tif /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/Neocanaux/CUB_zone_test_NE_NDVI.tif -treat MNH,2.5,200.0,0,0,and NDVI,0.0,0.3,2,2,and -log /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/fichierTestLog.txt -sav

def main(gui=False):

   # Définition des arguments possibles pour l'appel en ligne de commande
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, prog="MacroSamplesAmelioration",description="\
    Info : Improvement macro samples. \n\
    Objectif : Ameliorer la qualite des echantillons de macro classes. \n\
    Example : python MacroSamplesAmelioration.py -i /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/Macro/CUB_zone_test_NE_Bati_mask.tif \n\
                                                 -o /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/Macro/CUB_zone_test_NE_Bati_mask_cleaned.tif \n\
                                                 -cil /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/Neocanaux/CUB_zone_test_NE_MNH.tif \n\
                                                      /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/Neocanaux/CUB_zone_test_NE_NDVI.tif \n\
                                                 -treat MNH,2.5,200.0,0,0,and NDVI,0.0,0.3,2,2,and \n\
                                                 -log /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/fichierTestLog.txt")

    # Paramètres généraux
    parser.add_argument('-i','--image_input',default="",help="Image input to treat", type=str, required=True)
    parser.add_argument('-o','--image_output',default="",help="Image output result correction of the input image", type=str, required=True)
    parser.add_argument('-cil','--correction_images_input_list',default="",nargs="+",help="List images input to correct the input image ", type=str, required=True)
    parser.add_argument('-treat','--treatment_mask_list',default="",nargs="+",help="Dictionary of treatment containt for each image correction, reference image, threshold min, threshold max, filter size for zero zone, filter size for one zone, logical operator fusion (operator : 'and', 'or') (format : mask_file,threshold_min,threshold_max,filter_size_zero,filter_size_one,operator), ex. MNH,2.5,200.0,2,2,or NDVI,0.0,3.0,0,0,and", type=str, required=True)
    parser.add_argument('-macro','--macro_sample_name',default="",help="Name of macro sample", type=str, required=False)
    parser.add_argument('-rae','--extension_raster', default=".tif", help="Option : Extension file for image raster. By default : '.tif'", type=str, required=False)
    parser.add_argument('-log','--path_time_log',default="",help="Name of log", type=str, required=False)
    parser.add_argument('-sav','--save_results_inter',action='store_true',default=False,help="Save or delete intermediate result after the process. By default, False", required=False)
    parser.add_argument('-now','--overwrite',action='store_false',default=True,help="Overwrite files with same names. By default, True",required=False)
    parser.add_argument('-debug','--debug',default=3,help="Option : Value of level debug trace, default : 3 ",type=int, required=False)
    args = displayIHM(gui, parser)

    # Récupération de l'image d'entrée
    if args.image_input != None:
        image_input = args.image_input
        if not os.path.isfile(image_input):
            raise NameError (cyan + "MacroSamplesAmelioration : " + bold + red  + "File %s not existe!" %(image_input) + endC)

    # Récupération de l'image de sortie
    if args.image_output != None:
        image_output = args.image_output

    # Récupération de la liste des images pour la correction
    if args.correction_images_input_list != None :
        correction_images_input_list = args.correction_images_input_list
        for correction_image in correction_images_input_list :
            if not os.path.isfile(correction_image):
                raise NameError (cyan + "MacroSamplesAmelioration : " + bold + red  + "File %s not existe!" %(correction_image) + endC)

    # Creation du dictionaire contenant les valeurs des traitements pour chaque image de correction
    if args.treatment_mask_list != None:
        tmp_treatment_mask_list = args.treatment_mask_list
        treatment_mask_list = []
        for treatment in tmp_treatment_mask_list:
            info_treatment = []
            for text in treatment.split(','):
                info_treatment.append(text)
            treatment_mask_list.append(info_treatment)

    # macro_sample_name param
    if args.macro_sample_name != None:
        macro_sample_name = args.macro_sample_name

    # Paramètre de l'extension des images rasters
    if args.extension_raster != None:
        extension_raster = args.extension_raster

    # Récupération du nom du fichier log
    if args.path_time_log!= None:
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

    if debug >= 3:
        print(" ")
        print(bold + green + "MacroSamplesAmelioration : Variables dans le parser" + endC)
        print(cyan + "MacroSamplesAmelioration : " + endC + "image_input : " + str(image_input) + endC)
        print(cyan + "MacroSamplesAmelioration : " + endC + "image_output : " + str(image_output) + endC)
        print(cyan + "MacroSamplesAmelioration : " + endC + "correction_images_input_list : " + str(correction_images_input_list) + endC)
        print(cyan + "MacroSamplesAmelioration : " + endC + "treatment_mask_list : " + str(treatment_mask_list) + endC)
        print(cyan + "MacroSamplesAmelioration : " + endC + "macro_sample_name : " + str(macro_sample_name) + endC)
        print(cyan + "MacroSamplesAmelioration : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "MacroSamplesAmelioration : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "MacroSamplesAmelioration : " + endC + "save_results_inter : " + str(save_results_intermediate) + endC)
        print(cyan + "MacroSamplesAmelioration : " + endC + "overwrite: " + str(overwrite) + endC)
        print(cyan + "MacroSamplesAmelioration : " + endC + "debug: " + str(debug) + endC)

    # EXECUTION DE LA FONCTION
    # Si le dossier de sortie n'existe pas, on le crée
    repertory_output = os.path.dirname(image_output)
    if not os.path.isdir(repertory_output):
        os.makedirs(repertory_output)

    # execution de la fonction pour une image
    processMacroSamples(image_input, image_output, correction_images_input_list, treatment_mask_list, macro_sample_name, path_time_log, extension_raster, save_results_intermediate, overwrite)

# ================================================

if __name__ == '__main__':
  main(gui=False)
