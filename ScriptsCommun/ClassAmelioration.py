#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerSO/DALETT/SCGSI  All rights reserved.                                                                            #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT D'AMELIORATION DES CLASSES DE LA CLASSIFICATION                                                                                    #
#                                                                                                                                           #
#############################################################################################################################################
'''
Nom de l'objet : ClassAmelioration.py
Description :
    Objectif : Améliorer la qualité des classes du réultat de la classification
    Rq : utilisation des OTB Applications :   otbcli_BandMath, otbcli_BinaryMorphologicalOperation

Date de creation : 17/06/2015
----------
Histoire :
----------
Origine : nouveau

-----------------------------------------------------------------------------------------------------
Modifications

------------------------------------------------------
A Reflechir/A faire
 -
 -
'''
# Import des bibliothèques python
from __future__ import print_function
import os,sys,glob,shutil,string, argparse
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_raster import createBinaryMaskThreshold, applyMaskAnd, reallocateClassRaster, mergeListRaster
from Lib_log import timeLine
from Lib_file import cleanTempData, deleteDir, removeFile
from Lib_text import extractDico

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 3

###########################################################################################################################################
# DEFINITION DE LA FONCTION addCorrectionClass                                                                                               #
###########################################################################################################################################
# ROLE:
#    Ajouter des corrections à la classification grace à des fichiers raster externes traitées
#
# ENTREES DE LA FONCTION :
#    image_input : image d'entrée classifié
#    image_output : image classifié enrichie de sortie
#    class_add_data_dico : dictionaire de classe contenant les images à ajouter ainsi que leurs traitements à appliquer
#    path_time_log : le fichier de log de sortie
#    save_results_intermediate : fichiers de sorties intermediaires nettoyees, par defaut = False
#    overwrite : boolen ecrasement ou non des fichiers ayant un nom similaire, par defaut à True
#
# SORTIES DE LA FONCTION :
#    Aucun

def addCorrectionClass(image_input, image_output, class_add_data_dico, path_time_log, save_results_intermediate=False, overwrite=True) :

    # Mise à jour du Log
    starting_event = "addCorrectionClass() : Add data file treat to classification starting : "
    timeLine(path_time_log,starting_event)

    # print
    if debug >= 3:
        print(bold + green + "Variables dans la fonction" + endC)
        print(cyan + "addCorrectionClass() : " + endC + "image_input : " + str(image_input) + endC)
        print(cyan + "addCorrectionClass() : " + endC + "image_output : " + str(image_output) + endC)
        print(cyan + "addCorrectionClass() : " + endC + "class_add_data_dico : " + str(class_add_data_dico) + endC)
        print(cyan + "addCorrectionClass() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "addCorrectionClass() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "addCorrectionClass() : " + endC + "overwrite : " + str(overwrite) + endC)

    # Constantes
    FOLDER_MASK_TEMP = 'Mask_'
    SUFFIX_MASK = '_mask_'
    SUFFIX_MASK_FUSION = '_mask_fusion_'
    SUFFIX_CLASS_FUSION = '_macro_class_'
    CODAGE = "uint16"
    CODAGE_8B = "uint8"

    # Définition du répertoire temporaire
    name = os.path.splitext(os.path.basename(image_output))[0]
    repertory_samples_output = os.path.dirname(image_output)
    repertory_temp = repertory_samples_output + os.sep + FOLDER_MASK_TEMP + name

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

        image_combined_list = []
        # Parcours du dictionnaire associant les macroclasses aux noms de fichiers et aux traitement associés
        for macroclass_label in class_add_data_dico :
            if debug >= 3:
                print("\nmacroclass_label : " + str(macroclass_label))

            mask_fusion_list = []
            # Parcours des fichiers à ajouter à la macro class
            for treatement_info_list in class_add_data_dico[macroclass_label] :
                input_image_to_treat = treatement_info_list[0]
                threshold_min = float(treatement_info_list[1])
                threshold_max = float(treatement_info_list[2])
                if debug >= 3:
                    print("input_image_to_treat : " + str(input_image_to_treat))
                    print("threshold_min : " + str(threshold_min))
                    print("threshold_max : " + str(threshold_max))

                # Traitement préparation
                file_mask_output_temp = repertory_temp + os.sep + os.path.splitext(os.path.basename(input_image_to_treat))[0] + SUFFIX_MASK + macroclass_label + os.path.splitext(input_image_to_treat)[1]
                if os.path.isfile(file_mask_output_temp) :
                    removeFile(file_mask_output_temp)
                mask_fusion_list.append(file_mask_output_temp)

                # Creation masque binaire
                createBinaryMaskThreshold(input_image_to_treat, file_mask_output_temp, threshold_min, threshold_max)

            # Fusion des masques
            file_mask_output_fusion = repertory_temp + os.sep + os.path.splitext(os.path.basename(image_output))[0] + SUFFIX_MASK_FUSION + macroclass_label + os.path.splitext(image_output)[1]
            file_macroclass_output_fusion = repertory_temp + os.sep + os.path.splitext(os.path.basename(image_output))[0] + SUFFIX_CLASS_FUSION + macroclass_label + os.path.splitext(image_output)[1]
            image_combined_list.append(file_macroclass_output_fusion)

            if len(mask_fusion_list) == 1:
                # Pas de traitement à faire simple copie
                shutil.copyfile(mask_fusion_list[0], file_mask_output_fusion)
            else :
                # Fusionne les images mask en un seul masque
                image_mask_input = mask_fusion_list[0]
                for idx_image in range(1,len(mask_fusion_list)):
                    print(idx_image)
                    if idx_image == len(mask_fusion_list)-1:
                        image_mask_output = file_mask_output_fusion
                    else :
                        image_mask_output = repertory_temp + os.sep + os.path.splitext(os.path.basename(image_output))[0] + SUFFIX_MASK_FUSION + macroclass_label + "_" + str(idx_image) + os.path.splitext(image_output)[1]

                    applyMaskAnd(image_mask_input, mask_fusion_list[idx_image], image_mask_output, CODAGE_8B)
                    image_mask_input = image_mask_output

            # Affectation du label de la macro class associé
            reaff_value_list =[]
            reaff_value_list.append(1)
            change_reaff_value_list = []
            change_reaff_value_list.append(int(macroclass_label))
            reallocateClassRaster(file_mask_output_fusion, file_macroclass_output_fusion, reaff_value_list, change_reaff_value_list, CODAGE)


        # Ajout de l'image de classification a la liste des image bd conbinées
        image_combined_list.append(image_input)
        # Fusionne les images raster et la classification
        mergeListRaster(image_combined_list, image_output, CODAGE)

    # Suppression des données intermédiaires
    if not save_results_intermediate:

        # Supression des .geom dans le dossier
        for to_delete in glob.glob(repertory_samples_output + os.sep + "*.geom"):
            removeFile(to_delete)

        # Suppression du repertoire temporaire
        deleteDir(repertory_temp)

    # Mise à jour du Log
    ending_event = "addCorrectionClass() : Add data file treat to classification ending : "
    timeLine(path_time_log,ending_event)

    return

###########################################################################################################################################
# MISE EN PLACE DU PARSER                                                                                                                 #
###########################################################################################################################################

# Code executé seulement dans le cas ou le script est lancé depuis une ligne de commande
# Il n'est pas executé lors d'un import ClassAmelioration.py
# Exemple de lancement en ligne de commande:
# python ClassAmelioration.py  -i /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/Classification/CUB_zone_test_NE_stack_rf_merged_filtered_chanPIR_rad2_IC2_NDVI_MNH_clean.tif -o /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/Classification/CUB_zone_test_NE_stack_rf_merged_filtered_chanPIR_rad2_IC2_NDVI_MNH_clean2.tif -classAdd 11100:/mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/Neocanaux/CUB_zone_test_NE_MNH.tif,2.5,999.0:/mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/Neocanaux/CUB_zone_test_NE_NDVI.tif,-0.1,0.3 12200:/mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/Neocanaux/CUB_zone_test_NE_NDVI.tif,-2.0,-0.15  20000:/mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/Neocanaux/CUB_zone_test_NE_NDVI.tif,0.4,2.0 -log /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/CUB_zone_test_NE.log
def main(gui=False):

   # Définition des arguments possibles pour l'appel en ligne de commande
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, prog="ClassAmelioration",description="\
    Info : Correction macro class classification. \n\
    Objectif : Améliorer la qualité des classes du réultat de la classification. \n\
    Example : python ClassAmelioration.py  -i /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/Classification/CUB_zone_test_NE_stack_rf_merged_filtered_chanPIR_rad2_IC2_NDVI_MNH_clean.tif \n\
                                           -o /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/Classification/CUB_zone_test_NE_stack_rf_merged_filtered_chanPIR_rad2_IC2_NDVI_MNH_clean2.tif \n\
                                           -classAdd 11100:/mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/Neocanaux/CUB_zone_test_NE_MNH.tif,2.5,999.0:/mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/Neocanaux/CUB_zone_test_NE_NDVI.tif,-0.1,0.3 \n\
                                                     12200:/mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/Neocanaux/CUB_zone_test_NE_NDVI.tif,-2.0,-0.15 \n\
                                                     20000:/mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/Neocanaux/CUB_zone_test_NE_NDVI.tif,0.4,2.0 \n\
                                           -log /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/CUB_zone_test_NE.log")

    # Paramètres généraux
    parser.add_argument('-i','--image_input',default="",help="Image classification input to add data", type=str, required=True)
    parser.add_argument('-o','--image_output',default="",help="Image classification output result additional external file data", type=str, required=True)
    parser.add_argument('-classAdd','--class_add_data_dico',default="",nargs="+",help="Dictionary of class containt file dat to add and their treatments, (format : classeLabel:[image,threshold_min_image1,threshold_max_image1][..]), ex. 11100:../CUB_zone_test_NE_MNH.tif,2.5,999.0:../CUB_zone_test_NE_NDVI.tif,-0.1,0.3 12200:../CUB_zone_test_NE_NDVI.tif,-2.0,-0.15 20000:../CUB_zone_test_NE_NDVI.tif,0.4,2.0", type=str, required=True)
    parser.add_argument('-log','--path_time_log',default="",help="Name of log", type=str, required=False)
    parser.add_argument('-sav','--save_results_inter',action='store_true',default=False,help="Save or delete intermediate result after the process. By default, False", required=False)
    parser.add_argument('-now','--overwrite',action='store_false',default=True,help="Overwrite files with same names. By default, True",required=False)
    parser.add_argument('-debug','--debug',default=3,help="Option : Value of level debug trace, default : 3 ",type=int, required=False)
    args = displayIHM(gui, parser)

    # RECUPERATION DES ARGUMENTS

    # Récupération de l'image d'entrée
    if args.image_input != None:
        image_input = args.image_input
        if not os.path.isfile(image_input):
            raise NameError (cyan + "ClassAmelioration : " + bold + red  + "File %s not existe!" %(image_input) + endC)

    # Récupération de l'image de sortie
    if args.image_output != None:
        image_output = args.image_output

    # creation du dictionaire table macro class contenant les fichiers data à ajouter ainsi que leurs traitements
    if args.class_add_data_dico != None:
        class_add_data_dico = extractDico(args.class_add_data_dico)

    # Récupération du nom du fichier log
    if args.path_time_log!= None:
        path_time_log = args.path_time_log

    if args.save_results_inter != None:
        save_results_intermediate = args.save_results_inter

    if args.overwrite != None:
        overwrite = args.overwrite

    # Récupération de l'option niveau de debug
    if args.debug!= None:
        global debug
        debug = args.debug

    if debug >= 3:
        print(bold + green + "Variables dans le parser" + endC)
        print(cyan + "ClassAmelioration : " + endC + "image_input : " + str(image_input) + endC)
        print(cyan + "ClassAmelioration : " + endC + "image_output : " + str(image_output) + endC)
        print(cyan + "ClassAmelioration : " + endC + "class_add_data_dico : " + str(class_add_data_dico) + endC)
        print(cyan + "ClassAmelioration : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "ClassAmelioration : " + endC + "save_results_inter : " + str(save_results_intermediate) + endC)
        print(cyan + "ClassAmelioration : " + endC + "overwrite: " + str(overwrite) + endC)
        print(cyan + "ClassAmelioration : " + endC + "debug: " + str(debug) + endC)

    # EXECUTION DE LA FONCTION
    # Si le dossier de sortie n'existe pas, on le crée
    repertory_output = os.path.dirname(image_output)
    if not os.path.isdir(repertory_output):
        os.makedirs(repertory_output)

    # execution de la fonction pour une image
    addCorrectionClass(image_input, image_output, class_add_data_dico, path_time_log, save_results_intermediate, overwrite)

# ================================================

if __name__ == '__main__':
  main(gui=False)
