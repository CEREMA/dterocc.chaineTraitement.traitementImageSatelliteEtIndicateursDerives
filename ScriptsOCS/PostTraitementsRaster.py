#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT fait un ajout en superposant des donnees issus de BD exogénes au résultat de la classification                                     #
#                                                                                                                                           #
#############################################################################################################################################
"""
Nom de l'objet : PostTraitementsRaster.py
Description :
-------------
Objectif : Permet d'enrichir le résultat de la classification avec une superposition d'element provement de BD Exogènes à fin d'améliorer le résultat final
Rq : utilisation des OTB Applications :   otbcli_BandMath, otbcli_BinaryMorphologicalOperation

Date de creation : 17/06/2015
----------
Histoire :
----------
Origine : nouveau
-----------------------------------------------------------------------------------------------------
Modifications :

------------------------------------------------------
A Reflechir/A faire :

"""
# Import des bibliothèques python
from __future__ import print_function
import os,sys,glob,shutil,string, argparse, time
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_log import timeLine
from Lib_file import cleanTempData, deleteDir, removeFile
from Lib_text import extractDico
from Lib_raster import getPixelWidthXYImage, roundPixelEmpriseSize, createBinaryMaskThreshold, bufferBinaryRaster, createBinaryMask, cutImageByVector

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 3

###########################################################################################################################################
# FONCTION postTraitementsRaster                                                                                                          #
###########################################################################################################################################
def postTraitementsRaster(image_input, image_output, vector_input, enable_cutting_ask, post_treatment_raster_dico, no_data_value, path_time_log, format_raster='GTiff', format_vector='ESRI Shapefile', extension_raster=".tif", save_results_intermediate=False, overwrite=True) :
    """
    # ROLE:
    #    Ajouter des BD exogènes à la classification
    #
    # ENTREES DE LA FONCTION :
    #    image_input : image d'entrée classifié
    #    image_output : image classifié enrichie de sortie
    #    vector_input : vecteur de découpe du raster de sortie
    #    enable_cutting_ask : Booleen si True une découpe du raster de sortie est demander le paramètre vector_input doit être rempli sinon pas de découpe demander
    #    post_treatment_raster_dico : dictionaire de classe contenant les BD et les buffers à appliquer
    #    no_data_value : Valeur des pixels sans données pour les rasters de sortie
    #    path_time_log : le fichier de log de sortie
    #    format_raster : Format de l'image de sortie, par défaut : GTiff
    #    extension_raster : extension des fichiers raster de sortie, par defaut = '.tif'
    #    format_vector : format du fichier vecteur. Optionnel, par default : 'ESRI Shapefile'
    #    save_results_intermediate : fichiers de sorties intermediaires nettoyees, par defaut = False
    #    overwrite : boolen ecrasement ou non des fichiers ayant un nom similaire, par defaut à True
    #
    # SORTIES DE LA FONCTION :
    #    Aucun
    #    Eléments générés par la fonction : vecteurs echantillons de réference par macro classes
    """

    # Print
    if debug >= 3:
        print(bold + green + "Variables dans la fonction" + endC)
        print(cyan + "postTraitementsRaster() : " + endC + "image_input : " + str(image_input) + endC)
        print(cyan + "postTraitementsRaster() : " + endC + "image_output : " + str(image_output) + endC)
        print(cyan + "postTraitementsRaster() : " + endC + "vector_input : " + str(vector_input) + endC)
        print(cyan + "postTraitementsRaster() : " + endC + "enable_cutting_ask : " + str(enable_cutting_ask) + endC)
        print(cyan + "postTraitementsRaster() : " + endC + "post_treatment_raster_dico : " + str(post_treatment_raster_dico) + endC)
        print(cyan + "postTraitementsRaster() : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "postTraitementsRaster() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "postTraitementsRaster() : " + endC + "format_raster : " + str(format_raster) + endC)
        print(cyan + "postTraitementsRaster() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "postTraitementsRaster() : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "postTraitementsRaster() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "postTraitementsRaster() : " + endC + "overwrite : " + str(overwrite) + endC)

    # Mise à jour du Log
    starting_event = "postTraitementsRaster() : Past traitements raster starting : "
    timeLine(path_time_log,starting_event)

    # Constantes
    CODAGE = "uint16"

    FOLDER_TEMP = "TempPtRaster_"
    SUFFIX_TEMP = "_tmp"
    SUFFIX_MASK = '_mask'
    SUFFIX_DILATED = '_dilated'
    SUFFIX_TOAPPLY = '_to_apply'

    # ETAPE 1 : NETTOYAGE DES DONNEES EXISTANTES

    print(cyan + "postTraitementsRaster() : " + bold + green + "NETTOYAGE DE L ESPACE DE TRAVAIL..." + endC)

    # Nom de base de l'image
    image_name = os.path.splitext(os.path.basename(image_input))[0]

    # Nettoyage d'anciennes données résultat
    check = os.path.isfile(image_output)
    if check and not overwrite :        # Si le fichier résultat existe deja et que overwrite n'est pas activéptrd
        print(bold + yellow + "postTraitementsRaster() : " + endC + image_output + " already exists and will not be calculated again." + endC)
    else:                               # Cas où le fichier résultat n'existe pas au lancement
        if check :                      # Si overwrite est activé
            try:
                removeFile(image_output) # Tentative de suppression du fichier
            except Exception:
                pass                    # Si le fichier ne peut pas être supprimé, on suppose qu'il n'existe pas et on passe à la suite

        # Définition des répertoires temporaires
        repertory_output = os.path.dirname(image_output)           # Ex : D2_Par_Zone\Paysage_01\Corr_3\Resultats
        basename_output = os.path.splitext(os.path.basename(image_output))[0]  # Ex : Paysage_01_merged_filtred_pt
        extension = os.path.splitext(image_output)[1]
        image_output_temp = repertory_output + os.sep + basename_output + SUFFIX_TEMP + extension # Ex : D2_Par_Zone\Paysage_01\Corr_3\Resultats\Paysage_01_merged_filtred_pt_tmp.tif
        repertory_temp = repertory_output + os.sep + FOLDER_TEMP + image_name                     # Ex : D2_Par_Zone\Paysage_01\Corr_3\Resultats\Temp_pt_raster

        if debug >= 3:
            print(cyan + "postTraitementsRaster() : " + endC + "repertory_temp : " + str(repertory_temp) + endC)

        # Creation du repertoire de sortie s'il n'existe pas
        if not os.path.isdir(repertory_output):
            os.makedirs(repertory_output)

        # Nettoyage et creation du fichier temporaire:
        cleanTempData(repertory_temp)

        print(cyan + "postTraitementsRaster() : " + bold + green + "... FIN NETTOYAGE" + endC)

        # ETAPE 2 : TRAITEMENTS
        nb_treatments = len(post_treatment_raster_dico)
        idx = 0
        key_traitement_list = list(post_treatment_raster_dico.keys())

        for key_traitement in sorted(key_traitement_list):

            # Noms des fichiers temporaires
            binary_mask = repertory_temp + os.sep + basename_output + SUFFIX_MASK + key_traitement + extension_raster  # Ex : D2_Par_Zone\Paysage_01\Corr_3\Resultats\Temp_pt_raster\Paysage_01_merged_filtred_pt_mask.tif
            dilated_binary_mask = repertory_temp + os.sep + basename_output + SUFFIX_DILATED + SUFFIX_MASK + key_traitement + extension_raster  # Ex : D2_Par_Zone\Paysage_01\Corr_3\Resultats\Temp_pt_raster\Paysage_01_merged_filtred_pt_dilated_mask.tif
            mask_to_apply = repertory_temp + os.sep + basename_output + SUFFIX_TOAPPLY + SUFFIX_MASK + key_traitement + extension_raster  # Ex : D2_Par_Zone\Paysage_01\Corr_3\Resultats\Temp_pt_raster\Paysage_01_merged_filtred_pt_to_apply_mask.tif

            # Extraction des informations du dictionnaire
            treatement_info_list = post_treatment_raster_dico[key_traitement][0]
            image_to_use = treatement_info_list[0]
            threshold_min = float(treatement_info_list[1])
            threshold_max = float(treatement_info_list[2])
            buffer_to_apply = int(treatement_info_list[3])
            in_or_out = treatement_info_list[4]
            class_to_replace = str(treatement_info_list[5])
            if class_to_replace.lower() != "all":
                class_to_replace = int(class_to_replace)
            replacement_class = int(treatement_info_list[6])

            # ETAPE 2-1 CREATION DU MASQUE BINAIRE
            if debug >=2:
                print(cyan + "postTraitementsRaster() : " + bold + green + "TRAITEMENT %s/%s - Etape 1/4 : CREATION DU MASQUE BINAIRE POUR %s " %(str(idx+1), str(nb_treatments), image_to_use) + endC)

            createBinaryMaskThreshold(image_to_use, binary_mask, threshold_min, threshold_max, CODAGE)

            # ETAPE 2-2 CREATION DU MASQUE DILATE
            if buffer_to_apply == 0: # Si le buffer est nul, alors on copie juste le masque binaire
                if debug >=2:
                    print(cyan + "postTraitementsRaster() : " + bold + green + "TRAITEMENT %s/%s - Etape 2/4 : CREATION PAR RENOMMAGE DU MASQUE DILATE POUR %s" %(str(idx+1), str(nb_treatments), image_to_use) + endC)
                os.rename(binary_mask,dilated_binary_mask)
            else :
                if debug >=2:
                    print(cyan + "postTraitementsRaster() : " + bold + green + "TRAITEMENT %s/%s - Etape 2/4 : CREATION DU MASQUE DILATE POUR %s " %(str(idx+1), str(nb_treatments), image_to_use) + endC)

                # Creation d'un mask binaire bufferisé
                bufferBinaryRaster(binary_mask, dilated_binary_mask, buffer_to_apply, CODAGE)

                if not save_results_intermediate:
                    if debug >=3:
                        print(cyan + "postTraitementsRaster() : " + bold + green + "TRAITEMENT %s/%s - Etape 2/4 : SUPRESSION DE %s QUI NE SERVIRA PLUS" %(str(idx+1), str(nb_treatments), binary_mask) + endC)
                    # Suppression du masque binaire de base
                    removeFile(binary_mask)

            # ETAPE 2-3 CREATION DU MASQUE COMPLEMENTAIRE
            if in_or_out.lower() == "in":
                if debug >=2:
                    print(cyan + "postTraitementsRaster() : " + bold + green + "TRAITEMENT %s/%s - Etape 3/4 : CREATION PAR RENOMMAGE DU MASQUE COMPLEMENTAIRE A APPLIQUER POUR %s" %(str(idx+1), str(nb_treatments), image_to_use) + endC)
                os.rename(dilated_binary_mask,mask_to_apply)

            else:
                if debug >=2:
                    print(cyan + "postTraitementsRaster() : " + bold + green + "TRAITEMENT %s/%s - Etape 3/4 : CREATION DU MASQUE COMPLEMENTAIRE POUR %s" %(str(idx+1), str(nb_treatments), image_to_use) + endC)

                # Creation d'un mask binaire negatif
                createBinaryMask(dilated_binary_mask, mask_to_apply, 0.5, False, CODAGE)

                if not save_results_intermediate:
                    if debug >=3:
                        print(cyan + "postTraitementsRaster() : " + bold + green + "TRAITEMENT %s/%s - Etape 3/4 : SUPRESSION DE %s QUI NE SERVIRA PLUS" %(str(idx+1), str(nb_treatments),dilated_binary_mask) + endC)
                    # Suppression du masque dilate
                    removeFile(dilated_binary_mask)

            # ETAPE 2-4 APPLICATION DU MASQUE
            if str(class_to_replace).lower() == "all" :
                expression = "\"(im1b1 == 1 ? %d : im2b1)\""%(int(replacement_class))
            else :
                expression = "\"(im1b1 == 1 ? ( im2b1 == %d ? %d : im2b1) : im2b1)\""%(class_to_replace,replacement_class)

            if nb_treatments <= 1:
                input_for_command = image_input
                output_for_command = image_output_temp
            elif idx == 0 :
                input_for_command = image_input
                output_for_command = repertory_temp + os.sep + basename_output + str(idx+1) + extension_raster
            elif idx == nb_treatments-1:
                input_for_command = repertory_temp + os.sep + basename_output + str(idx) + extension_raster
                output_for_command = image_output_temp
            else:
                input_for_command = repertory_temp + os.sep + basename_output + str(idx) + extension_raster
                output_for_command = repertory_temp + os.sep + basename_output + str(idx+1) + extension_raster

            command = "otbcli_BandMath -il %s %s -exp %s -out %s %s" %(mask_to_apply, input_for_command, expression, output_for_command, CODAGE)

            if debug >=2:
                print(cyan + "postTraitementsRaster() : " + bold + green + "TRAITEMENT %s/%s - Etape 4/4 : APPLICATION DU POST TRAITEMENT AVEC %s" %(str(idx+1), str(nb_treatments), mask_to_apply) + endC)
                print(command)

            exitCode = os.system(command)
            if exitCode != 0:
                print(command)
                raise NameError(bold + red + "postTraitementsRaster() : An error occured during otbcli_BandMath command. See error message above." + endC)

            if not save_results_intermediate:
                if debug >=3:
                    print(cyan + "postTraitementsRaster() : " + bold + green + "TRAITEMENT %s/%s - Etape 4/4 : SUPRESSION DE %s QUI NE SERVIRA PLUS" %(str(idx+1), str(nb_treatments), mask_to_apply ) + endC)
                # Suppression du masque à appliquer
                removeFile(mask_to_apply)

            # mise a jour de l'index
            idx+=1

    # ETAPE 5 : DECOUPAGE DU RASTER DE SORTIE
    if enable_cutting_ask :

        # Decoupe du raster
        if not cutImageByVector(vector_input, image_output_temp, image_output, None, None, False, no_data_value, 0, format_raster, format_vector) :
            print(cyan + "postTraitementsRaster() : " + bold + red + "!!! Une erreur c'est produite au cours du decoupage de l'image : " + image_output_temp + ". Voir message d'erreur." + endC, file=sys.stderr)
            raise

        if debug >=2:
            print(cyan + "postTraitementsRaster() : " + bold + green + "TRAITEMENT %s/%s - Etape 5 : REDECOUPAGE DU RASTER DE SORTIE AVEC LE VECTEUR %s" %(str(idx+1), str(nb_treatments), vector_input) + endC)

        if not save_results_intermediate:
            # Suppression du fichier intermediaire
            removeFile(image_output_temp)
    else :
        # Pas de redécoupage du fichier raster de sortie demander le fichier est juste renomé
        shutil.move(image_output_temp, image_output)

    # ETAPE 6 : SUPPRESSION DES FICHIERS INTERMEDIAIRES
    # Suppression des données intermédiaires
    if not save_results_intermediate:
        if debug >=2:
            print(cyan + "postTraitementsRaster() : " + bold + green + "TRAITEMENT %s/%s - SUPRESSION DES DONNEES INTERMEDIAIRE CONTENUES DANS : %s" %(str(idx+1), str(nb_treatments), repertory_temp) + endC)

        # Suppression du repertoire temporaire
        deleteDir(repertory_temp)

    # Mise à jour du Log
    ending_event = "postTraitementsRaster() : Add data base exogene to classification ending : "
    timeLine(path_time_log,ending_event)

    return

###########################################################################################################################################
# MISE EN PLACE DU PARSER                                                                                                                 #
###########################################################################################################################################

# Code executé seulement dans le cas ou le script est lancé depuis une ligne de commande
# Il n'est pas executé lors d'un import PostTraitementRaster.py
# Exemple de lancement en ligne de commande:
# python PostTraitementsRaster.py -i /mnt/hgfs/PartageVM2/D2_Par_Zone/Paysage_01/Corr_3/Resultats/Paysage_01_merged_filtred.tif -o /mnt/hgfs/PartageVM2/D2_Par_Zone/Paysage_01/Corr_3/Resultats/Paysage_01_merged_filtred_pt.tif -ptrd /mnt/hgfs/PartageVM2/D2_Par_Zone/Paysage_01/Neocanaux/Paysage_01_20110508T113726_NDVI.tif:-2,-0.2,0,in,all,11000 /mnt/hgfs/PartageVM2/D2_Par_Zone/Paysage_01/Corr_1/Macro/Paysage_01_11000_artificialises_mask_cleaned.tif:0.5,1.5,1,in,all,11000 /mnt/hgfs/PartageVM2/D2_Par_Zone/Paysage_01/Corr_1/Macro/Paysage_01_11100_infrastructure_mask_cleaned.tif:0.5,1.5,0,in,all,11100 /mnt/hgfs/PartageVM2/D2_Par_Zone/Paysage_01/Corr_1/Macro/Paysage_01_12200_eau_mask_cleaned.tif:0.5,1.5,1,in,all,12200 -sav

def main(gui=False) :
    """
    # Regles de post traitement à partir des masques d'apprentissage raster
    # post_treatment_raster_dico = "traitement_01 Traitement_02 Traitement_03..."
    # avec Traitement_0i = label_de_macroclass/indice/texture:seuilmin,seuilmax,dilation,interieur_ou_exterieur_du_masque,classe_à_remplacer/all,classe_de_remplacement"
    # Exemple : post_treatment_raster_dico = "11000:0.5,1.5,1,in,all,11000 NDVI:-2,-0.2,0,in,all,11000 11000:0.5,1.5,100,out,11000,12100" vérifie
    # - On prend les valeurs du masque 11000 comprises entre 0.5 et 1.5, on les dilate de 1 pixel, on selectionne les zones de pixel à 1, et pour toute les classes, on impose la classe 11 000
    # - Puis on prend les valeurs de NDVI comprises entre -2 et -0.2, on ne fait pas de dilatation, on selectionne les zones de pixel à 1, et pour toute les classes, on impose la classe 11 000
    # - Puis on prend les valeurs du masque 11000 comprises entre 0.5 et 1.5, on les dilate de 100 pixels, on selectionne les zones de pixel à 0, et dans cette zone, on transforme le bati en sol nu
    #
    #  Pour les explications des paramètres :
    #   -image_output (-i) : L'image d'entrée résultat de classification en micro classe (marche aussi en macro classe)
    #   -image_output (-o) : L'image de sortie résultat du poste traitement (classification corrigé)
    #   -vector_input (-v): Vecteur de redecoupe de l'image final optionel si pas de vecteur specifier la découpe ne se fera pas
    #   -post_treatment_raster_dico (-ptrd) : C'est un dictionaire, c'est le paramètre le plus compliquer
    #                                         car il contient tout le traitement a faire en chaine de caractère je vais le détailler :
    #  Par exemple je passe : "pt1:/mnt/Data/gilles.fouvet/RA/Rhone/Global/Resultats/Livraison_Rhone/Rhone_PT_Indirects_To_Apply.tif,0.5,1.5,40,out,11000,12100
    #                          pt2:/mnt/Data/gilles.fouvet/RA/Rhone/Global/Resultats/Livraison_Rhone/Rhone_PT_Indirects_To_Apply.tif,0.5,1.5,40,out,11100,12100":
    #
    #  il s’agit de 2 traitement à faire l'espace est le caractère séparateur (l'ordre dans le dico est l'ordre des traitements). On peut faire un nombre infini de traitement...
    #
    #  ensuite pour chaque traitement chaque partie est séparée par une virgule :
    #  paramètre  la clé de dico avant les ":" sert d'identifiant du poste traitement peut etre n'importe quoi mais unique entre les différents traitements
    #  1er paramètre)(ex: /mnt/Data/gilles.fouvet/RA/Rhone/Global/Resultats/Livraison_Rhone/Rhone_PT_Indirects_To_Apply.tif)  le non du fichier avec son chemin complet contenant les informations a rajouter au fichier d'entrée "image_input"
    #  2éme et 3éme paramètres) (ex: 0.5,1.5) les valeurs min et max qui vont être prise en compte dans ce fichier (du paramètre 1)
    #  4éme paramètre) (ex: 40) est la valeur du buffer à appliquer en nombre de pixels sur le resultat du seuillage des parametres 2 et 3
    #  5ème paramètre) (ex: out)valeur "in" ou "out", la valeur "in" on ne modifie que les valeurs à l’intérieur du groupe de pixel masque (ce serait des polygones si c'était du vecteur),
    #                                              la valeur "out" on ne modifie que les valeurs à l'extérieur du groupe de pixel masque (ce serait des polygones si c'était du vecteur)
    #  6ème paramètre) (ex: 11000) c'est la valeur à traiter dans l'image d'entrée "image_input"
    #  7ème paramètre) (ex: 12100) c'est la valeur de remplacement (du paramètre 6) que l'on retrouvera dans l'image de sortie "image_output"
    """

   # Définition des arguments possibles pour l'appel en ligne de commande
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, prog="PostTraitementsRasterSuperposition",description="\
    Title : Post treat with exogene data in raster format. \n\
    Objectif : Permet d'enrichir le resultat de la classification avec une superposition d'element provenant d autres rasters. \n\
    Structure de ptrd - post_treatment_raster_dico : label_de_macroclass/indice/texture:seuilmin,seuilmax,dilation_en_pixels,interieur_ou_exterieur_du_masque,classe_à_remplacer/all,classe_de_remplacement \n\
    Example : python PostTraitementsRaster.py -i /mnt/hgfs/PartageVM2/D2_Par_Zone/Paysage_01/Corr_3/Resultats/Paysage_01_merged_filtred.tif \n\
                                              -o /mnt/hgfs/PartageVM2/D2_Par_Zone/Paysage_01/Corr_3/Resultats/Paysage_01_merged_filtred_pt.tif \n\
                                              -v /mnt/Data/gilles.fouvet/RA/Rhone/Global/Preparation/Landscapes_Boundaries/Paysage_01.shp \n\
                                              -ptrd pt1:/mnt/hgfs/PartageVM2/D2_Par_Zone/Paysage_01/Neocanaux/Paysage_01_20110508T113726_NDVI.tif,-2,-0.2,0,in,all,11000 \n\
                                                    pt2:/mnt/hgfs/PartageVM2/D2_Par_Zone/Paysage_01//mnt/hgfs/PartageVM2/D2_Par_Zone/Paysage_01/Corr_1/Macro/Paysage_01_11000_artificialises_mask_cleaned.tif,0.5,1.5,1,in,all,11000 \n\
                                                    pt3:/mnt/hgfs/PartageVM2/D2_Par_Zone/Paysage_01/Corr_1/Macro/Paysage_01_11100_infrastructure_mask_cleaned.tif,0.5,1.5,0,in,all,11100 \n\
                                                    pt4:/mnt/hgfs/PartageVM2/D2_Par_Zone/Paysage_01/Corr_1/Macro/Paysage_01_12200_eau_mask_cleaned.tif,0.5,1.5,1,in,all,12200 \n\
                                              -log /mnt/hgfs/PartageVM2/D2_Par_Zone/Paysage_01/APTV_05/fichierTestLog.txt -sav")

    # Paramètres généraux
    parser.add_argument('-i','--image_input',help="Input : classified image on which we will add data", type=str, required=True)
    parser.add_argument('-o','--image_output',help="Output : post traited classif", type=str, required=True)
    parser.add_argument('-v','--vector_input',default="",help="Vector input contain the vector to cut image output. If empty no cutting", type=str, required=False)
    parser.add_argument('-ptrd','--post_treatment_raster_dico',default="",nargs="+",help="Dictionnaire for post traitements rasters", type=str, required=True)
    parser.add_argument("-ndv",'--no_data_value',default=0,help="Option pixel value for raster file to no data, default : 0 ", type=int, required=False)
    parser.add_argument('-raf','--format_raster', default="GTiff", help="Option : Format output image, by default : GTiff (GTiff, HFA...)", type=str, required=False)
    parser.add_argument('-vef','--format_vector', default="ESRI Shapefile",help="Format of the output file.", type=str, required=False)
    parser.add_argument('-rae','--extension_raster', default=".tif", help="Option : Extension file for image raster. By default : '.tif'", type=str, required=False)
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
            raise NameError (cyan + "PostTraitementsRaster : " + bold + red  + "File %s not existe!" %(image_input) + endC)

    # Récupération de l'image de sortie
    if args.image_output != None:
        image_output = args.image_output

    # Récupération du fichier vecteur de découpe
    enable_cutting_ask = False
    if args.vector_input != None :
        vector_input = args.vector_input
        if vector_input != "" :
            enable_cutting_ask = True
            if not os.path.isfile(vector_input):
                raise NameError (cyan + "PostTraitementsRaster : " + bold + red  + "File %s not existe!" %(vector_input) + endC)

    # Creation du dictionaire contenant les valeurs des traitements pour chaque image de correction
    if args.post_treatment_raster_dico != None:
        post_treatment_raster_dico = extractDico(args.post_treatment_raster_dico)

    # Paramettre des no data
    if args.no_data_value != None:
        no_data_value = args.no_data_value

    # Paramètre format des images de sortie
    if args.format_raster != None:
        format_raster = args.format_raster

    # Récupération du format des vecteurs de sortie
    if args.format_vector != None :
        format_vector = args.format_vector

    # Paramètre de l'extension des images rasters
    if args.extension_raster != None:
        extension_raster = args.extension_raster

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
        print(cyan + "PostTraitementsRaster : " + endC + "image_input : " + str(image_input) + endC)
        print(cyan + "PostTraitementsRaster : " + endC + "image_output : " + str(image_output) + endC)
        print(cyan + "PostTraitementsRaster : " + endC + "vector_input : " + str(vector_input) + endC)
        print(cyan + "PostTraitementsRaster : " + endC + "post_treatment_raster_dico : " + str(post_treatment_raster_dico) + endC)
        print(cyan + "PostTraitementsRaster : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "PostTraitementsRaster : " + endC + "format_raster : " + str(format_raster) + endC)
        print(cyan + "PostTraitementsRaster : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "PostTraitementsRaster : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "PostTraitementsRaster : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "PostTraitementsRaster : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "PostTraitementsRaster : " + endC + "overwrite: " + str(overwrite) + endC)
        print(cyan + "PostTraitementsRaster : " + endC + "debug: " + str(debug) + endC)

    # EXECUTION DE LA FONCTION
    # Si le dossier de sortie n'existe pas, on le crée
    repertory_output = os.path.dirname(image_output)
    if not os.path.isdir(repertory_output):
        os.makedirs(repertory_output)

    # Execution de la fonction pour une image
    if post_treatment_raster_dico != {}:
        postTraitementsRaster(image_input, image_output, vector_input, enable_cutting_ask, post_treatment_raster_dico, no_data_value, path_time_log, format_raster, format_vector, extension_raster, save_results_intermediate, overwrite)

# ================================================
if __name__ == '__main__':
  main(gui=False)
