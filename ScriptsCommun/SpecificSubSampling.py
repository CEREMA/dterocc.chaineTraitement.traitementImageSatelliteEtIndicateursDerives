#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerSO/DALETT/SCGSI  All rights reserved.                                                                            #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT FAIT UNE RE LABELLISATION AUTOMATIQUE SUR UN RASTER A PARTIR D'UNE TABLE DE RELABELLISATION                                        #
#                                                                                                                                           #
#############################################################################################################################################
'''
Nom de l'objet : SpecificSubSampling.py
Description :
    Objectif :  Sous echantilloner certaines classes d'une OSC raster identifiées par le label -2 d'une table de reaffectation
    Rq : utilisation des OTB Applications :   otbcli_BandMath

Date de creation : 12/08/2015
----------
Histoire :
----------
Origine : nouveau
-----------------------------------------------------------------------------------------------------
Modifications

------------------------------------------------------
A Reflechir/A faire

'''

# Import des bibliothèques python
from __future__ import print_function
import os,sys,glob,string,shutil,time,argparse
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from KmeansMaskApplication import applyKmeansMasks
from Lib_log import timeLine
from Lib_text import readTextFileBySeparator, readReallocationTable, writeTextFile
from Lib_raster import countPixelsOfValue, identifyPixelValues
from Lib_file import removeFile

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 3

###########################################################################################################################################
# FONCTION classRasterSubSampling                                                                                                         #
###########################################################################################################################################
# ROLE:
#     Sous echantilloner certaines classes d'une OSC raster identifiées par le label -2 d'une table de reaffectation
#
# ENTREES DE LA FONCTION :
#     satellite_image_input : image satelite brute au format.tif
#     classified_image_input : image classée en plusieurs classes au format.tif
#     image_output : image re-classée en fonction des info de la table de réallocation au format.tif
#     table_reallocation : fichier contenant la table de proposition de reaffectation des micro classes (au format texte)
#     sub_sampling_number : nombre de sous echantillon de la classe à réaliser
#     no_data_value : Valeur de  pixel du no data
#     path_time_log : le fichier de log de sortie
#     rand_otb : graine pour la partie randon de l'ago de KMeans
#     ram_otb : memoire RAM disponible pour les applications OTB
#     number_of_actives_pixels_threshold : Nombre minimum de pixels de formation pour le kmeans. Par défaut = 8000
#     format_raster : Format de l'image de sortie, par défaut : GTiff
#     extension_raster : extension des fichiers raster de sortie, par defaut = '.tif'
#     save_results_intermediate : liste des sorties intermediaires nettoyees, par defaut = False
#     overwrite : supprime ou non les fichiers existants ayant le meme nom
#
# SORTIES DE LA FONCTION :
#     aucun
#     Eléments modifiés l'image de classification micro classes

def classRasterSubSampling(satellite_image_input, classified_image_input, image_output, table_reallocation, sub_sampling_number, no_data_value, path_time_log, rand_otb=0, ram_otb=0, number_of_actives_pixels_threshold=8000, format_raster='GTiff', extension_raster=".tif", save_results_intermediate=False, overwrite=True) :

    # Mise à jour du Log
    starting_event = "classRasterSubSampling() : Micro class subsampling on classification image starting : "
    timeLine(path_time_log,starting_event)

    if debug >= 3:
       print(cyan + "classRasterSubSampling() : " + endC + "satellite_image_input : " +  str(satellite_image_input) + endC)
       print(cyan + "classRasterSubSampling() : " + endC + "classified_image_input : " +  str(classified_image_input) + endC)
       print(cyan + "classRasterSubSampling() : " + endC + "image_output : " + str(image_output) + endC)
       print(cyan + "classRasterSubSampling() : " + endC + "table_reallocation : " + str(table_reallocation) + endC)
       print(cyan + "classRasterSubSampling() : " + endC + "sub_sampling_number : " + str(sub_sampling_number) + endC)
       print(cyan + "classRasterSubSampling() : " + endC + "no_data_value : " + str(no_data_value) + endC)
       print(cyan + "classRasterSubSampling() : " + endC + "path_time_log : " + str(path_time_log) + endC)
       print(cyan + "classRasterSubSampling() : " + endC + "rand_otb : " + str(rand_otb) + endC)
       print(cyan + "classRasterSubSampling() : " + endC + "ram_otb : " + str(ram_otb) + endC)
       print(cyan + "classRasterSubSampling() : " + endC + "number_of_actives_pixels_threshold : " + str(number_of_actives_pixels_threshold) + endC)
       print(cyan + "classRasterSubSampling() : " + endC + "format_raster : " + str(format_raster) + endC)
       print(cyan + "classRasterSubSampling() : " + endC + "extension_raster : " + str(extension_raster) + endC)
       print(cyan + "classRasterSubSampling() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
       print(cyan + "classRasterSubSampling() : " + endC + "overwrite : " + str(overwrite) + endC)

    # Constantes
    CODAGE = "uint16"
    CODAGE_8B = "uint8"
    TEMP = "TempSubSampling_"
    MASK_SUF = "_Mask"
    SUB_SAMPLE_SUF = "_SubSampled"
    CENTROID_SUF = "_Centroids"
    TEMP_OUT = "_temp_out"
    EXTENSION_TXT = ".txt"

    # Contenu de la nouvelle table
    text_new_table = ""

    # CREATION DES NOMS DE CHEMINS UTILES
    name = os.path.splitext(os.path.basename(image_output))[0]
    input_classified_image_path = os.path.dirname(classified_image_input)                      # Ex : D2_Par_Zone/Paysage_01/Corr_2/Resultats/Temp/
    temp_sub_sampling_path = input_classified_image_path + os.sep + TEMP + name + os.sep       # Dossier contenant les fichiers temporaires de cette brique. Ex : D2_Par_Zone/Paysage_01/Corr_2/Resultats/Temp/Temp_Sub_Sampling/
    input_classified_image_complete_name = os.path.basename(classified_image_input)            # Ex : Paysage_01_raw.tif
    input_classified_image_name = os.path.splitext(input_classified_image_complete_name)[0]    # Ex : Paysage_01_raw
    input_classified_image_extend = os.path.splitext(input_classified_image_complete_name)[1]  # Ex : .tif
    image_output_temp = os.path.splitext(image_output)[0] + TEMP_OUT + extension_raster        # Ex : D2_Par_Zone/Paysage_01/Corr_2/Resultats/Temp/Temp_Sub_Sampling/Paysage_01_raw_temp.tif

    # Création de temp_sub_sampling_path s'il n'existe pas
    if not os.path.isdir(os.path.dirname(temp_sub_sampling_path)) :
        os.makedirs(os.path.dirname(temp_sub_sampling_path))

    print(cyan + "classRasterSubSampling() : " + bold + green + "START ...\n" + endC)

    # Lecture du fichier table de proposition
    supp_class_list, reaff_class_list, macro_reaff_class_list, sub_sampling_class_list, sub_sampling_number_list = readReallocationTable(table_reallocation, sub_sampling_number)      # Fonction de Lib_text
    info_table_list = readTextFileBySeparator(table_reallocation, "\n")

    # Recherche de la liste des micro classes contenu dans le fichier de classification d'entrée
    class_values_list = identifyPixelValues(classified_image_input)

    # Supression dans la table des lignes correspondant aux actions "-2"
    for ligne_table in info_table_list:
        if not "-2" in ligne_table[0]:
            text_new_table += str(ligne_table[0]) + "\n"

    if debug >= 3:
        print("supp_class_list : " + str(supp_class_list))
        print("reaff_class_list : " + str(reaff_class_list))
        print("macro_reaff_class_list : " + str(macro_reaff_class_list))
        print("sub_sampling_class_list : " + str(sub_sampling_class_list))
        print("sub_sampling_number_list : " + str(sub_sampling_number_list))

    # Dans cettre brique, on ne s'intéresse qu'à la partie sous echantillonage
    # Gestion du cas de suppression
    if len(supp_class_list) > 0:
        print(cyan + "classRasterSubSampling() : " + bold + yellow + "ATTENTION : Les classes ne sont pas supprimees pour le fichier classification format raster." + '\n' + endC)

    # Gestion du cas de réaffectation
    if len(reaff_class_list) > 0:
         print(cyan + "classRasterSubSampling() : " + bold + yellow + "ATTENTION : la brique SpecificSubSampling ne traite pas les reaffectation. A l'issue de cette brique, verifier la table de reallocation et executer la brique de reallocation." + '\n' + endC)

    if len(sub_sampling_class_list) > 0 :

        if debug >= 3:
           print(cyan + "classRasterSubSampling() : " + bold + green + "DEBUT DU SOUS ECHANTILLONAGE DES CLASSES %s " %(sub_sampling_class_list) + endC)

        # Parcours des classes à sous échantilloner
        processing_pass_first = False
        for idx_class in range(len(sub_sampling_class_list)) :

            # INITIALISATION DU TRAITEMENT DE LA CLASSE

            # Classe à sous échantilloner. Ex : 21008
            class_to_sub_sample = sub_sampling_class_list[idx_class]
            if idx_class == 0 or not processing_pass_first :
                # Image à reclassifier : classified_image_input au premier tour
                image_to_sub_sample = classified_image_input
            else :
                # Image à reclassifier : la sortie de la boucle précédente ensuite
                image_to_sub_sample = image_output

            # determiner le label disponible de la classe
            base_subclass_label = int(class_to_sub_sample/100)*100
            subclass_label = base_subclass_label
            for class_value in class_values_list:
                if (class_value > subclass_label) and (class_value < base_subclass_label + 100) :
                    subclass_label = class_value
            subclass_label += 1
            # subclass_label = int(class_to_sub_sample/100)*100 + 20 + class_to_sub_sample%20 * 5
            # Label de départ des sous classes. Formule proposée : 3 premiers chiffres de class_to_sub_sample puis ajout de 20 + 5 * class_to_sub_sample modulo 20. Ex : 21000 -> 21020, 21001-> 21025, 21002-> 21030 etc...
            # Part du principe qu'il y a moins de 20 micro classes et que chacune est sous échantillonnée au maximum en 5 sous parties. Si ce n'est pas le cas : A ADAPTER

            number_of_sub_samples = sub_sampling_number_list[idx_class]    # Nombre de sous classes demandées pour le sous échantillonage de class_to_sub_sample. Ex : 4
            class_mask_raster = temp_sub_sampling_path + input_classified_image_name + "_" + str(class_to_sub_sample) + MASK_SUF + input_classified_image_extend    # Ex : D2_Par_Zone/Paysage_01/Corr_2/Resultats/Temp/Temp_Sub_Sampling/Paysage_01_raw_21008_Mask.tif
            class_subsampled_raster = temp_sub_sampling_path + input_classified_image_name + "_" + str(class_to_sub_sample) + SUB_SAMPLE_SUF + input_classified_image_extend  # Ex : D2_Par_Zone/Paysage_01/Corr_2/Resultats/Temp/Temp_Sub_Sampling/Paysage_01_raw_21008_SubSampled.tif
            centroid_file = temp_sub_sampling_path + input_classified_image_name + "_" + str(class_to_sub_sample) + CENTROID_SUF + EXTENSION_TXT  # Ex : D2_Par_Zone/Paysage_01/Corr_2/Resultats/Temp/Temp_Sub_Sampling/Paysage_01_raw_21008_Centroid.txt

            if debug >= 5:
                print(cyan + "classRasterSubSampling() : " + endC + "class_to_sub_sample :" , class_to_sub_sample)
                print(cyan + "classRasterSubSampling() : " + endC + "subclass_label :" , subclass_label)
                print(cyan + "classRasterSubSampling() : " + endC + "number_of_sub_samples :" , number_of_sub_samples)
                print(cyan + "classRasterSubSampling() : " + endC + "class_mask_raster :" , class_mask_raster)
                print(cyan + "classRasterSubSampling() : " + endC + "class_subsampled_raster :" , class_subsampled_raster)
                print(cyan + "classRasterSubSampling() : " + endC + "centroid_file :" , centroid_file)

            if debug >= 3:
                print(cyan + "classRasterSubSampling() : " + bold + green + "CLASSE %s/%s : SOUS ECHANTILLONAGE DE %s EN %s CLASSES " %(idx_class+1, len(sub_sampling_class_list), class_to_sub_sample, number_of_sub_samples) + endC)

            # ETAPE 1/5 : EXTRACTION DU MASQUE BINAIRE DES PIXELS CORRESPONDANT A LA CLASSE
            expression_masque = "\"im1b1 == %s? 1 : 0\"" %(class_to_sub_sample)
            command = "otbcli_BandMath -il %s -out %s %s -exp %s" %(classified_image_input, class_mask_raster, CODAGE_8B, expression_masque)

            if debug >=2:
                print("\n" + cyan + "classRasterSubSampling() : " + bold + green + "CLASSE %s/%s - ETAPE 1/5 : Debut de l extraction du masque binaire de la classe %s" %(idx_class+1, len(sub_sampling_class_list),class_to_sub_sample) + endC)
                print(command)

            os.system(command)

            if debug >=2:
                print(cyan + "classRasterSubSampling() : " + bold + green + "CLASSE %s/%s - ETAPE 1/5 : Fin de l extraction du masque binaire de la classe %s, disponible ici : %s" %(idx_class+1, len(sub_sampling_class_list),class_to_sub_sample, class_mask_raster) + endC)

            # TEST POUR SAVOIR SI ON EST EN CAPACITE D'EFFECTUER LE KMEANS
            number_of_actives_pixels = countPixelsOfValue(class_mask_raster, 1)  # Comptage du nombre de pixels disponibles pour effectuer le kmeans
            if number_of_actives_pixels > (number_of_sub_samples * number_of_actives_pixels_threshold) :    # Cas où il y a plus de pixels disponibles pour effectuer le kmeans que le seuil

                # ETAPE 2/5 : CLASSIFICATION NON SUPERVISEE DES PIXELS CORRESPONDANT A LA CLASSE
                if debug >= 3:
                    print("\n" + cyan + "classRasterSubSampling() : " + bold + green + "CLASSE %s/%s - ETAPE 2/5 : Il y a assez de pixels pour faire le sous echantillonage :  %s sur %s requis au minimum " %(idx_class+1, len(sub_sampling_class_list), number_of_actives_pixels, int(number_of_sub_samples) * number_of_actives_pixels_threshold) + endC)
                if debug >=2:
                    print("\n" + cyan + "classRasterSubSampling() : " + bold + green + "CLASSE %s/%s - ETAPE 2/5 : Debut du sous echantillonage par classification non supervisee en %s classes " %(idx_class+1, len(sub_sampling_class_list), number_of_sub_samples) + endC)

                # appel du kmeans
                input_mask_list = []
                input_mask_list.append(class_mask_raster)
                output_masked_image_list = []
                output_masked_image_list.append(class_subsampled_raster)
                output_centroids_files_list = []
                output_centroids_files_list.append(centroid_file)
                macroclass_sampling_list = []
                macroclass_sampling_list.append(number_of_sub_samples)
                macroclass_labels_list = []
                macroclass_labels_list.append(subclass_label)
                applyKmeansMasks(satellite_image_input, input_mask_list, "", "", output_masked_image_list, output_centroids_files_list, macroclass_sampling_list, macroclass_labels_list, no_data_value, path_time_log, 200, 1, -1, 0.0, rand_otb, ram_otb, number_of_actives_pixels_threshold, format_raster, extension_raster, save_results_intermediate, overwrite)

                if debug >=2:
                    print(cyan + "classRasterSubSampling() : " + bold + green + "CLASSE %s/%s - ETAPE 2/5 : Fin du sous echantillonage par classification non supervisee en %s classes, disponible ici %s : " %(idx_class+1, len(sub_sampling_class_list), number_of_sub_samples, class_subsampled_raster) + endC)

                # ETAPE 3/5 : INTEGRATION DES NOUVELLES SOUS CLASSES DANS LA TABLE DE REALLOCATION
                # Ouveture du fichier table de proposition pour re-ecriture

                for i in range(number_of_sub_samples):
                    class_values_list.append(subclass_label + i)
                    text_new_table += str(subclass_label + i) + ";" + str(subclass_label + i) + "; METTRE A JOUR MANUELLEMENT (origine : " +  str(class_to_sub_sample) + ")" + "\n"

                # ETAPE 4/5 : APPLICATION DU SOUS ECHANTILLONAGE AU RESULTAT DE CLASSIFICATION
                expression_application_sous_echantillonage = "\"im1b1 == %s? im2b1 : im1b1\"" %(class_to_sub_sample)
                command = "otbcli_BandMath -il %s %s -out %s %s -exp %s" %(image_to_sub_sample, class_subsampled_raster, image_output_temp, CODAGE, expression_application_sous_echantillonage)

                if debug >=2:
                    print("\n" + cyan + "classRasterSubSampling() : " + bold + green + "CLASSE %s/%s - ETAPE 4/5 : Debut de l application du sous echantillonage present dans %s sur %s" %(idx_class+1, len(sub_sampling_class_list), class_subsampled_raster, classified_image_input) + endC)
                    print(command)

                os.system(command)

                if debug >=2:
                    print(cyan + "classRasterSubSampling() : " + bold + green + "CLASSE %s/%s - ETAPE 4/5 : Fin de l application du sous echantillonage present dans %s sur %s, sortie disponible ici : %s" %(idx_class+1, len(sub_sampling_class_list), class_subsampled_raster, classified_image_input, image_output_temp) + endC)

                # ETAPE 5/5 : GESTION DES RENOMMAGES ET SUPPRESSIONS
                if debug >=2:
                    print("\n" + cyan + "classRasterSubSampling() : " + bold + green + "CLASSE %s/%s - ETAPE 5/5 : Debut du renommage et suppression des dossiers intermediaires" %(idx_class+1, len(sub_sampling_class_list)) + endC)

                if debug >=3 :
                    print("\n" + green + "classified image input: %s" %(classified_image_input) + endC)
                    print("\n" + green + "image to sub sample: %s" %(image_to_sub_sample) + endC)
                    print("\n" + green + "image temp : %s" %(image_output_temp) + endC)
                    print("\n" + green + "image output : %s" %(image_output) + endC)

                # Si l'image d'entrée et l'image de sorte sont le même fichier on efface le fichier d'entrée pour le re-creer avec le fichier re-travaillé
                if image_output == classified_image_input and os.path.isfile(classified_image_input) :
                    removeFile(classified_image_input)
                os.rename(image_output_temp,image_output)
                processing_pass_first = True

                # SUPPRESSION DES FICHIERS TEMPORAIRES
                if not save_results_intermediate :
                    if os.path.isfile(class_mask_raster) :
                        removeFile(class_mask_raster)
                    if os.path.isfile(class_subsampled_raster) :
                        removeFile(class_subsampled_raster)
                    if os.path.isfile(centroid_file) :
                        removeFile(centroid_file)

                if debug >=2:
                    print(cyan + "classRasterSubSampling() : " + bold + green + "CLASSE %s/%s - ETAPE 5/5 : Fin du renommage et suppression des dossiers intermediaires" %(idx_class+1, len(sub_sampling_class_list)) + endC)

            else:  # Cas où il n'y a pas assez de pixels pour effectuer le kmeans

                if debug >=2:
                    print("\n" + cyan + "classRasterSubSampling() : " + bold + yellow + "CLASSE %s/%s - ETAPE 2/5 : Nombre insuffisant de pixels disponibles pour appliquer le kmeans : %s sur %s requis au minimum " %(idx_class+1, len(sub_sampling_class_list), number_of_actives_pixels, int(number_of_sub_samples) * number_of_actives_pixels_threshold) + endC)
                    print(cyan + "classRasterSubSampling() : " + bold + yellow + "CLASSE %s/%s - ETAPE 2/5 : SOUS ECHANTILLONAGE NON APPLIQUE A LA CLASSE %s" %(idx_class+1, len(sub_sampling_class_list), class_to_sub_sample) + endC + "\n")

                # MISE A JOUR DU FICHIER image_to_sub_sample
                if idx_class == 0:
                    processing_pass_first = False

                # MISE A JOUR DE LA TABLE DE REALLOCATION
                text_new_table += str(class_to_sub_sample) + ";" + str(class_to_sub_sample) + ";CLASSE TROP PETITE POUR SOUS ECHANTILLONAGE" + "\n"

                # SUPPRESSION DU MASQUE
                if not save_results_intermediate and os.path.isfile(class_mask_raster) :
                    removeFile(class_mask_raster)

    else:
        shutil.copy2(classified_image_input, image_output) # Copie du raster d'entree si pas de sous-echantillonnage

    # Ecriture de la nouvelle table dans le fichier
    writeTextFile(table_reallocation, text_new_table)

    # SUPPRESSION DU DOSSIER ET DES FICHIERS TEMPORAIRES
    if not save_results_intermediate and os.path.isdir(os.path.dirname(temp_sub_sampling_path)) :
        shutil.rmtree(os.path.dirname(temp_sub_sampling_path))

    print(cyan + "classRasterSubSampling() : " + bold + green + "END\n" + endC)

    # Mise à jour du Log
    ending_event = "classRasterSubSampling() : Micro class subsampling on classification image ending : "
    timeLine(path_time_log,ending_event)
    return

###########################################################################################################################################
# MISE EN PLACE DU PARSER                                                                                                                 #
###########################################################################################################################################

# Code executé seulement dans le cas ou le script est lancé depuis une ligne de commande
# Il n'est pas executé lors d'un import SpecificSubSampling.py
# Exemple de lancement en ligne de commande:
# python SpecificSubSampling.py -i ../ImagesTestChaine/APTV_05/Micro/APTV_05_stack_raw.tif -c ../ImagesTestChaine/APTV_05/Micro/APTV_05_classif.tif -t ../ImagesTestChaine/APTV_05/Micro/APTV_05_prop_tab.txt -o ../ImagesTestChaine/APTV_05/Micro/APTV_05_stack_raw2.tif -log ../ImagesTestChaine/APTV_05/fichierTestLog.txt


def main(gui=False):

    # Définition des arguments possibles pour l'appel en ligne de commande
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,  prog="SpecificSubSampling", description="\
    Info : Automatic subsampling of class, from raster. \n\
    Objectif : Sous echantillonage de certaines classes d'une OSC raster identifiées par le label -2 d'une table de reaffectation. \n\
    Example : python SpecificSubSampling.py -i ../ImagesTestChaine/APTV_05/Micro/APTV_05_stack_raw.tif \n\
                                            -c ../ImagesTestChaine/APTV_05/Micro/APTV_05_classif.tif \n\
                                            -t ../ImagesTestChaine/APTV_05/Micro/APTV_05_prop_tab.txt \n\
                                            -o ../ImagesTestChaine/APTV_05/Micro/APTV_05_stack_raw2.tif \n\
                                            -log ../ImagesTestChaine/APTV_05/fichierTestLog.txt")

    # Paramètres
    parser.add_argument('-i','--satellite_image_input',help="Satellite Image input to treat", type=str, required=True)
    parser.add_argument('-c','--classified_image_input',help="Classified Image input to treat", type=str, required=True)
    parser.add_argument('-t','--table_reallocation',help="Proposal table input to realocation micro class", type=str, required=True)
    parser.add_argument('-o','--image_output',default="",help="Image output re-allocated . Warning!!! if is empty the classified input image file is modified.", type=str, required=False)
    parser.add_argument('-nss','--sub_sampling_number',default=3,help="Defaut number of sub sampling class. Default = 3", type=int, required=False)
    parser.add_argument('-npt','--number_of_actives_pixels_threshold',default=8000,help="Number of minimum training size for kmeans. Default = 8000 * Nb de sous classes", type=int, required=False)
    parser.add_argument('-rand','--rand_otb',default=0,help="User defined seed for random KMeans", type=int, required=False)
    parser.add_argument('-ram','--ram_otb',default=0,help="Ram available for processing otb applications (in MB)", type=int, required=False)
    parser.add_argument('-ndv','--no_data_value', default=0, help="Option in option optimize_emprise_nodata  : Value of the pixel no data. By default : 0", type=int, required=False)
    parser.add_argument('-raf','--format_raster', default="GTiff", help="Option : Format output image raster. By default : GTiff (GTiff, HFA...)", type=str, required=False)
    parser.add_argument('-rae','--extension_raster', default=".tif", help="Option : Extension file for image raster. By default : '.tif'", type=str, required=False)
    parser.add_argument('-log','--path_time_log',default="",help="Name of log", type=str, required=False)
    parser.add_argument('-sav','--save_results_inter',action='store_true',default=False,help="Save or delete intermediate result after the process. By default, False", required=False)
    parser.add_argument('-now','--overwrite',action='store_false',default=True,help="Overwrite files with same names. By default, True", required=False)
    parser.add_argument('-debug','--debug',default=3,help="Option : Value of level debug trace, default : 3 ",type=int, required=False)
    args = displayIHM(gui, parser)

    # RECUPERATION DES ARGUMENTS
    # Récupération de l'image satellite d'entrée
    if args.satellite_image_input != None:
        satellite_image_input = args.satellite_image_input
        if not os.path.isfile(satellite_image_input):
            raise NameError (cyan + "SpecificSubSampling : " + bold + red  + "File %s not existe!" %(satellite_image_input) + endC)

    # Récupération de l'image classifiée d'entrée
    if args.classified_image_input != None:
        classified_image_input = args.classified_image_input
        if not os.path.isfile(classified_image_input):
            raise NameError (cyan + "SpecificSubSampling : " + bold + red  + "File %s not existe!" %(classified_image_input) + endC)

    # Récupération de la table de proposition d'entrée
    if args.table_reallocation != None:
        table_reallocation = args.table_reallocation
        if not os.path.isfile(table_reallocation):
            raise NameError (cyan + "SpecificSubSampling : " + bold + red  + "File %s not existe!" %(table_reallocation) + endC)

    # Récupération de l'image de sortie
    if args.image_output != None:
        image_output = args.image_output
        if image_output == "":
            image_output = classified_image_input

    # Récupération du nombre de sous echantions à effectuer
    if args.sub_sampling_number != None:
        sub_sampling_number = args.sub_sampling_number

    # Récupération du nombre minimum de pixels pour effectuer le kmeans
    if args.number_of_actives_pixels_threshold != None:
        number_of_actives_pixels_threshold = args.number_of_actives_pixels_threshold

    # Récupération du parametre no_data_value
    if args.no_data_value!= None:
        no_data_value = args.no_data_value

    # Récupération du parametre rand
    if args.rand_otb != None:
        rand_otb = args.rand_otb

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
        print(cyan + "SpecificSubSampling : " + endC + "satellite_image_input : " + str(satellite_image_input) + endC)
        print(cyan + "SpecificSubSampling : " + endC + "classified_image_input : " + str(classified_image_input) + endC)
        print(cyan + "SpecificSubSampling : " + endC + "table_reallocation : " + str(table_reallocation) + endC)
        print(cyan + "SpecificSubSampling : " + endC + "image_output : " + str(image_output) + endC)
        print(cyan + "SpecificSubSampling : " + endC + "sub_sampling_number : " + str(sub_sampling_number) + endC)
        print(cyan + "SpecificSubSampling : " + endC + "number_of_actives_pixels_threshold : " + str(number_of_actives_pixels_threshold) + endC)
        print(cyan + "SpecificSubSampling : " + endC + "rand_otb : " + str(rand_otb) + endC)
        print(cyan + "SpecificSubSampling : " + endC + "ram_otb : " + str(ram_otb) + endC)
        print(cyan + "SpecificSubSampling : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "SpecificSubSampling : " + endC + "format_raster : " + str(format_raster) + endC)
        print(cyan + "SpecificSubSampling : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "SpecificSubSampling : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "SpecificSubSampling : " + endC + "save_results_inter : " + str(save_results_intermediate) + endC)
        print(cyan + "SpecificSubSampling : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "SpecificSubSampling : " + endC + "debug : " + str(debug) + endC)

    # EXECUTION DE LA FONCTION
    # Si le dossier de sortie n'existe pas, on le crée
    if image_output != None:
        repertory_output = os.path.dirname(image_output)
        if not os.path.isdir(repertory_output):
            os.makedirs(repertory_output)

    # reallocation
    classRasterSubSampling(satellite_image_input, classified_image_input, image_output, table_reallocation, sub_sampling_number, no_data_value, path_time_log, rand_otb, ram_otb, number_of_actives_pixels_threshold, format_raster, extension_raster, save_results_intermediate, overwrite)

# ================================================

if __name__ == '__main__':
  main(gui=False)
