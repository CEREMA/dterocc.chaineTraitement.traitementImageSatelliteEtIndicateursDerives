#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerSO/DALETT/SCGSI  All rights reserved.                                                                            #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT DE CREATION DES ECHANTILLONS MACRO                                                                                                 #
#                                                                                                                                           #
#############################################################################################################################################
'''
Nom de l'objet : MacroSamplesCreation.py
Description :
    Objectif : Réaliser des échantillons de macro classes
    Cela permet de préparer (copier, découper, bufferiser, labelliser) des shapefiles(.shp) issues des BD Exogènes à fin de creer des echantillons d'apprentissage pour la classification
    Rq : utilisation des OTB Applications :  otbcli_BandMath

Date de creation : 14/10/2014
----------
Histoire :
----------
Origine : le script originel provient du fichier Chain4_MicroclassesComputation.py cree en 2013 et utilise par la chaine de traitement OCSOL V1.X
31/07/2014 : Transformation en brique elementaire (suppression des liens avec la chaine OCSOL)
-----------------------------------------------------------------------------------------------------
Modifications
01/10/2014 : refonte du fichier harmonisation des régles de qualitées, des niveaux de boucles et des paramétres dans args
21/05/2015 : simplification des parametres en argument plus de liste d'image en emtrée à traiter uniquement une image
------------------------------------------------------
A Reflechir/A faire
 -
 -
'''
# Import des bibliothèques python
from __future__ import print_function
import os,sys,glob,shutil,string, argparse
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_vector import simplifyVector, cutoutVectors, bufferVector, fusionVectors, filterSelectDataVector, getAttributeNameList, getNumberFeature, getGeometryType
from Lib_raster import createVectorMask, rasterizeBinaryVector, getNodataValueImage, getGeometryImage
from Lib_log import timeLine
from Lib_file import cleanTempData, deleteDir, removeVectorFile, copyVectorFile, removeFile

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 4

###########################################################################################################################################
# FONCTION createMacroSamples()                                                                                                           #
###########################################################################################################################################
# ROLE:
#    Traiter les BD exogènes
#
# ENTREES DE LA FONCTION :
#    image_input : image d'entrée brute
#    vector_to_cut_input : le vecteur pour le découpage (zone d'étude)
#    vector_sample_output : fichier vecteur au format shape de sortie contenant l'echantillon
#    raster_sample_output : optionel fichier raster au format GTiff de sortie contenant l'echantillon
#    bd_vector_input_list : liste des vecteurs de la bd exogene pour créer l'échantillon
#    bd_buff_list : liste des valeurs des buffers associés au traitement à appliquer aux vecteurs de bd exogenes
#    sql_expression_list : liste d'expression sql pour le filtrage des fichiers vecteur de bd exogenes
#    path_time_log : le fichier de log de sortie
#    macro_sample_name : nom de l'echantillon macro
#    simplify_vector_param : parmetre de simplification des polygones
#    format_vector : format du fichier vecteur. Optionnel, par default : 'ESRI Shapefile'
#    extension_vector : extension du fichier vecteur de sortie, par defaut = '.shp'
#    save_results_intermediate : fichiers de sorties intermediaires nettoyees, par defaut = False
#    overwrite : boolen ecrasement ou non des fichiers ayant un nom similaire, par defaut à True
#
# SORTIES DE LA FONCTION :
#    auccun
#    Eléments générés par la fonction : vecteurs echantillons de réference par macro classes
#

def createMacroSamples(image_input, vector_to_cut_input, vector_sample_output, raster_sample_output, bd_vector_input_list, bd_buff_list, sql_expression_list, path_time_log, macro_sample_name="", simplify_vector_param=10.0, format_vector='ESRI Shapefile', extension_vector=".shp", save_results_intermediate=False, overwrite=True) :

    # Mise à jour du Log
    starting_event = "createMacroSamples() : create macro samples starting : "
    timeLine(path_time_log,starting_event)

    if debug >= 3:
        print(bold + green + "createMacroSamples() : Variables dans la fonction" + endC)
        print(cyan + "createMacroSamples() : " + endC + "image_input : " + str(image_input) + endC)
        print(cyan + "createMacroSamples() : " + endC + "vector_to_cut_input : " + str(vector_to_cut_input) + endC)
        print(cyan + "createMacroSamples() : " + endC + "vector_sample_output : " + str(vector_sample_output) + endC)
        print(cyan + "createMacroSamples() : " + endC + "raster_sample_output : " + str(raster_sample_output) + endC)
        print(cyan + "createMacroSamples() : " + endC + "bd_vector_input_list : " + str(bd_vector_input_list) + endC)
        print(cyan + "createMacroSamples() : " + endC + "bd_buff_list : " + str(bd_buff_list) + endC)
        print(cyan + "createMacroSamples() : " + endC + "sql_expression_list : " + str(sql_expression_list) + endC)
        print(cyan + "createMacroSamples() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "createMacroSamples() : " + endC + "macro_sample_name : " + str(macro_sample_name) + endC)
        print(cyan + "createMacroSamples() : " + endC + "simplify_vector_param : " + str(simplify_vector_param) + endC)
        print(cyan + "createMacroSamples() : " + endC + "format_vector : " + str(format_vector))
        print(cyan + "createMacroSamples() : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "createMacroSamples() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "createMacroSamples() : " + endC + "overwrite : " + str(overwrite) + endC)

    # Constantes
    FOLDER_MASK_TEMP = "Mask_"
    FOLDER_CUTTING_TEMP = "Cut_"
    FOLDER_FILTERING_TEMP = "Filter_"
    FOLDER_BUFF_TEMP = "Buff_"

    SUFFIX_MASK_CRUDE = "_crude"
    SUFFIX_MASK = "_mask"
    SUFFIX_VECTOR_CUT = "_cut"
    SUFFIX_VECTOR_FILTER = "_filt"
    SUFFIX_VECTOR_BUFF = "_buff"

    CODAGE = "uint8"

    # ETAPE 1 : NETTOYER LES DONNEES EXISTANTES

    print(cyan + "createMacroSamples() : " + bold + green + "Nettoyage de l'espace de travail..." + endC)

    # Nom du repertoire de calcul
    repertory_macrosamples_output = os.path.dirname(vector_sample_output)

    # Test si le vecteur echantillon existe déjà et si il doit être écrasés
    check = os.path.isfile(vector_sample_output) or os.path.isfile(raster_sample_output)

    if check and not overwrite: # Si les fichiers echantillons existent deja et que overwrite n'est pas activé
        print(bold + yellow + "File sample : " + vector_sample_output + " already exists and will not be created again." + endC)
    else :
        if check:
            try:
                removeVectorFile(vector_sample_output)
                removeFile(raster_sample_output)
            except Exception:
                pass # si le fichier n'existe pas, il ne peut pas être supprimé : cette étape est ignorée

        # Définition des répertoires temporaires
        repertory_mask_temp = repertory_macrosamples_output + os.sep + FOLDER_MASK_TEMP + macro_sample_name
        repertory_samples_cutting_temp = repertory_macrosamples_output + os.sep + FOLDER_CUTTING_TEMP + macro_sample_name
        repertory_samples_filtering_temp = repertory_macrosamples_output + os.sep + FOLDER_FILTERING_TEMP + macro_sample_name
        repertory_samples_buff_temp = repertory_macrosamples_output + os.sep + FOLDER_BUFF_TEMP + macro_sample_name

        if debug >= 4:
            print(cyan + "createMacroSamples() : " + endC + "Création du répertoire : " + str(repertory_mask_temp))
            print(cyan + "createMacroSamples() : " + endC + "Création du répertoire : " + str(repertory_samples_cutting_temp))
            print(cyan + "createMacroSamples() : " + endC + "Création du répertoire : " + str(repertory_samples_buff_temp))

        # Création des répertoires temporaire qui n'existent pas
        if not os.path.isdir(repertory_macrosamples_output):
            os.makedirs(repertory_macrosamples_output)
        if not os.path.isdir(repertory_mask_temp):
            os.makedirs(repertory_mask_temp)
        if not os.path.isdir(repertory_samples_cutting_temp):
            os.makedirs(repertory_samples_cutting_temp)
        if not os.path.isdir(repertory_samples_filtering_temp):
            os.makedirs(repertory_samples_filtering_temp)
        if not os.path.isdir(repertory_samples_buff_temp):
            os.makedirs(repertory_samples_buff_temp)

        # Nettoyage des répertoires temporaire qui ne sont pas vide
        cleanTempData(repertory_mask_temp)
        cleanTempData(repertory_samples_cutting_temp)
        cleanTempData(repertory_samples_filtering_temp)
        cleanTempData(repertory_samples_buff_temp)

        print(cyan + "createMacroSamples() : " + bold + green + "... fin du nettoyage" + endC)

        # ETAPE 2 : DECOUPAGE DES VECTEURS

        print(cyan + "createMacroSamples() : " + bold + green + "Decoupage des echantillons ..." + endC)

        if vector_to_cut_input == None :
            # 2.1 : Création du masque délimitant l'emprise de la zone par image
            image_name = os.path.splitext(os.path.basename(image_input))[0]
            vector_mask = repertory_mask_temp + os.sep + image_name + SUFFIX_MASK_CRUDE + extension_vector
            cols, rows, num_band = getGeometryImage(image_input)
            no_data_value = getNodataValueImage(image_input, num_band)
            if no_data_value == None :
                no_data_value = 0
            createVectorMask(image_input, vector_mask, no_data_value, format_vector)

            # 2.2 : Simplification du masque
            vector_simple_mask = repertory_mask_temp + os.sep + image_name + SUFFIX_MASK + extension_vector
            simplifyVector(vector_mask, vector_simple_mask, simplify_vector_param, format_vector)
        else :
            vector_simple_mask = vector_to_cut_input

        # 2.3 : Découpage des vecteurs de bd exogenes avec le masque
        vectors_cut_list = []
        for vector_input in bd_vector_input_list :
            vector_name = os.path.splitext(os.path.basename(vector_input))[0]
            vector_cut = repertory_samples_cutting_temp + os.sep + vector_name + SUFFIX_VECTOR_CUT + extension_vector
            vectors_cut_list.append(vector_cut)
        cutoutVectors(vector_simple_mask, bd_vector_input_list, vectors_cut_list, format_vector)

        print(cyan + "createMacroSamples() : " + bold + green + "... fin du decoupage" + endC)

        # ETAPE 3 : FILTRAGE DES VECTEURS

        print(cyan + "createMacroSamples() : " + bold + green + "Filtrage des echantillons ..." + endC)

        vectors_filtered_list = []
        if sql_expression_list != [] :
            for idx_vector in range (len(bd_vector_input_list)):
                vector_name = os.path.splitext(os.path.basename(bd_vector_input_list[idx_vector]))[0]
                vector_cut = vectors_cut_list[idx_vector]
                if idx_vector < len(sql_expression_list) :
                    sql_expression = sql_expression_list[idx_vector]
                else :
                    sql_expression = ""
                vector_filtered = repertory_samples_filtering_temp + os.sep + vector_name + SUFFIX_VECTOR_FILTER + extension_vector
                vectors_filtered_list.append(vector_filtered)

                # Filtrage par ogr2ogr
                if sql_expression != "":
                    names_attribut_list = getAttributeNameList(vector_cut, format_vector)
                    column = "'"
                    for name_attribut in names_attribut_list :
                        column += name_attribut + ", "
                    column = column[0:len(column)-2]
                    column += "'"
                    ret = filterSelectDataVector(vector_cut, vector_filtered, column, sql_expression, format_vector)
                    if not ret :
                        print(cyan + "createMacroSamples() : " + bold + yellow + "Attention problème lors du filtrage des BD vecteurs l'expression SQL %s est incorrecte" %(sql_expression) + endC)
                        copyVectorFile(vector_cut, vector_filtered)
                else :
                    print(cyan + "createMacroSamples() : " + bold + yellow + "Pas de filtrage sur le fichier du nom : " + endC + vector_filtered)
                    copyVectorFile(vector_cut, vector_filtered)

        else :
            print(cyan + "createMacroSamples() : " + bold + yellow + "Pas de filtrage demandé" + endC)
            for idx_vector in range (len(bd_vector_input_list)):
                vector_cut = vectors_cut_list[idx_vector]
                vectors_filtered_list.append(vector_cut)

        print(cyan + "createMacroSamples() : " + bold + green + "... fin du filtrage" + endC)

        # ETAPE 4 : BUFFERISATION DES VECTEURS

        print(cyan + "createMacroSamples() : " + bold + green + "Mise en place des tampons..." + endC)

        vectors_buffered_list = []
        if bd_buff_list != [] :
            # Parcours des vecteurs d'entrée
            for idx_vector in range (len(bd_vector_input_list)):
                vector_name = os.path.splitext(os.path.basename(bd_vector_input_list[idx_vector]))[0]
                buff = bd_buff_list[idx_vector]
                vector_filtered = vectors_filtered_list[idx_vector]
                vector_buffered = repertory_samples_buff_temp + os.sep + vector_name + SUFFIX_VECTOR_BUFF + extension_vector

                if buff != 0:
                    if os.path.isfile(vector_filtered):
                        if debug >= 3:
                            print(cyan + "createMacroSamples() : " + endC + "vector_filtered : " + str(vector_filtered) + endC)
                            print(cyan + "createMacroSamples() : " + endC + "vector_buffered : " + str(vector_buffered) + endC)
                            print(cyan + "createMacroSamples() : " + endC + "buff : " + str(buff) + endC)
                        bufferVector(vector_filtered, vector_buffered, buff, "", 1.0, 10, format_vector)
                    else :
                        print(cyan + "createMacroSamples() : " + bold + yellow + "Pas de fichier du nom : " + endC + vector_filtered)

                else :
                    print(cyan + "createMacroSamples() : " + bold + yellow + "Pas de tampon sur le fichier du nom : " + endC + vector_filtered)
                    copyVectorFile(vector_filtered, vector_buffered)

                vectors_buffered_list.append(vector_buffered)

        else :
            print(cyan + "createMacroSamples() : " + bold + yellow + "Pas de tampon demandé" + endC)
            for idx_vector in range (len(bd_vector_input_list)):
                vector_filtered = vectors_filtered_list[idx_vector]
                vectors_buffered_list.append(vector_filtered)

        print(cyan + "createMacroSamples() : " + bold + green + "... fin de la mise en place des tampons" + endC)

        # ETAPE 5 : FUSION DES SHAPES

        print(cyan + "createMacroSamples() : " + bold + green + "Fusion par macroclasse ..." + endC)

        # si une liste de fichier shape à fusionner existe
        if not vectors_buffered_list:
            print(cyan + "createMacroSamples() : " + bold + yellow + "Pas de fusion sans donnee à fusionner" + endC)
        # s'il n'y a qu'un fichier shape en entrée
        elif len(vectors_buffered_list) == 1:
            print(cyan + "createMacroSamples() : " + bold + yellow + "Pas de fusion pour une seule donnee à fusionner" + endC)
            copyVectorFile(vectors_buffered_list[0], vector_sample_output)
        else :
            # Fusion des fichiers shape
            vectors_buffered_controled_list = []
            for vector_buffered in vectors_buffered_list :
                if os.path.isfile(vector_buffered) and (getGeometryType(vector_buffered, format_vector) in ('POLYGON', 'MULTIPOLYGON')) and (getNumberFeature(vector_buffered, format_vector) > 0):
                    vectors_buffered_controled_list.append(vector_buffered)
                else :
                    print(cyan + "createMacroSamples() : " + bold + red + "Attention fichier bufferisé est vide il ne sera pas fusionné : " + endC + vector_buffered, file=sys.stderr)

            fusionVectors(vectors_buffered_controled_list, vector_sample_output, format_vector)

        print(cyan + "createMacroSamples() : " + bold + green + "... fin de la fusion" + endC)

    # ETAPE 6 : CREATION DU FICHIER RASTER RESULTAT SI DEMANDE

    # Creation d'un masque binaire
    if raster_sample_output != "" and image_input != "" :
        repertory_output = os.path.dirname(raster_sample_output)
        if not os.path.isdir(repertory_output):
            os.makedirs(repertory_output)
        rasterizeBinaryVector(vector_sample_output, image_input, raster_sample_output, 1, CODAGE)

    # ETAPE 7 : SUPPRESIONS FICHIERS INTERMEDIAIRES INUTILES

    # Suppression des données intermédiaires
    if not save_results_intermediate:

        # Supression du fichier de decoupe si celui ci a été créer
        if vector_simple_mask != vector_to_cut_input :
            if os.path.isfile(vector_simple_mask) :
                removeVectorFile(vector_simple_mask)

        # Suppression des repertoires temporaires
        deleteDir(repertory_mask_temp)
        deleteDir(repertory_samples_cutting_temp)
        deleteDir(repertory_samples_filtering_temp)
        deleteDir(repertory_samples_buff_temp)

    # Mise à jour du Log
    ending_event = "createMacroSamples() : create macro samples ending : "
    timeLine(path_time_log,ending_event)

    return

###########################################################################################################################################
# MISE EN PLACE DU PARSER                                                                                                                 #
###########################################################################################################################################

# Code executé seulement dans le cas ou le script est lancé depuis une ligne de commande
# Il n'est pas executé lors d'un import MacroSamplesCreation.py
# Exemple de lancement en ligne de commande:
# python MacroSamplesCreation.py -i ../ImagesTestChaine/APTV_06/APTV_06.tif -ov ../ImagesTestChaine/APTV_06/Echantillons/APTV_06_Anthropise_entrainement.shp -ibdl ../ImagesTestChaine/APTV_06/BD/ROUTE_74.shp ../ImagesTestChaine/APTV_06/BD/ROUTE_001.shp ../ImagesTestChaine/APTV_06/BD/BATI_INDIFFERENCIE_74.shp ../ImagesTestChaine/APTV_06/BD/BATI_INDIFFERENCIE_001.shp -bufl 3 3 5 5 -log ../ImagesTestChaine/APTV_06/fichierTestLog.txt
# python -m MacroSamplesCreation  -ov /mnt/Data/10_Agents_travaux_en_cours/Gilles/Test_chaine_classif_methodo/40_ECHANTILLONS/41_MACRO/route/route.shp -ibdl /mnt/Data/10_Agents_travaux_en_cours/Gilles/Test_chaine_classif_methodo/00_DATA/BD_TOPO/D33/ED16/SHP/1_DONNEES_LIVRAISON/A_VOIES_COMM_ROUTE/N_ROUTE_PRIMAIRE_BDT_033.SHP /mnt/Data/10_Agents_travaux_en_cours/Gilles/Test_chaine_classif_methodo/00_DATA/BD_TOPO/D33/ED16/SHP/1_DONNEES_LIVRAISON/A_VOIES_COMM_ROUTE/N_ROUTE_SECONDAIRE_BDT_033.SHP /mnt/Data/10_Agents_travaux_en_cours/Gilles/Test_chaine_classif_methodo/00_DATA/BD_TOPO/D33/ED16/SHP/1_DONNEES_LIVRAISON/A_VOIES_COMM_ROUTE/N_SURFACE_ROUTE_BDT_033.SHP  -bufl 5.0 3.0 -2.0  -macro route -simp 10.0 -i /mnt/Data/10_Agents_travaux_en_cours/Gilles/Test_chaine_classif_methodo/10_IMAGE/ZoneTest.tif -v /mnt/Data/10_Agents_travaux_en_cours/Gilles/Test_chaine_classif_methodo/emprise_ZoneTest_Bordeaux_Metropole.shp -sql "NATURE IN ('Autoroute', 'Bretelle', 'Quasi-autoroute', 'Route à 1 chaussée', 'Route à 2 chaussées')":"":"" -sav -debug 3

def main(gui=False):

   # Définition des arguments possibles pour l'appel en ligne de commande
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,  prog="MacroSamplesCreation",description="\
    Info : Create macro samples. \n\
    Objectif : Realiser des echantillons de macro classes. \n\
    Example : python MacroSamplesCreation.py -i ../ImagesTestChaine/APTV_06/APTV_06.tif \n\
                                             -ov ../ImagesTestChaine/APTV_06/Echantillons/APTV_06_Anthropise_entrainement.shp \n\
                                             -or ../ImagesTestChaine/APTV_06/Echantillons/APTV_06_Anthropise_entrainement.tiff \n\
                                             -ibdl ../ImagesTestChaine/APTV_06/BD/ROUTE_74.shp \n\
                                                   ../ImagesTestChaine/APTV_06/BD/ROUTE_001.shp \n\
                                                   ../ImagesTestChaine/APTV_06/BD/BATI_INDIFFERENCIE_74.shp \n\
                                                   ../ImagesTestChaine/APTV_06/BD/BATI_INDIFFERENCIE_001.shp \n\
                                             -bufl 3.0 3.0 5.0 5.0 \n\
                                             -sql \"NATURE ='Autoroute' AND NATURE ='Route 2 Chausses'\":\"\":\"\":\"\" \n\
                                             -log ../ImagesTestChaine/APTV_06/fichierTestLog.txt")

    # Paramètres généraux
    parser.add_argument('-i','--image_input',default=None,help="Image input to treat", type=str, required=False)
    parser.add_argument('-v','--vector_cut_input',default=None,help="Vector input define the sudy area.", type=str, required=False)
    parser.add_argument('-ov','--vector_sample_output',default="",help="Vector sample output", type=str, required=False)
    parser.add_argument('-or','--raster_sample_output',default="",help="Raster sample output", type=str, required=False)
    parser.add_argument('-ibdl','--bd_vector_input_list',default="",nargs="+",help="List containt bd vector input concatened to create vector sample", type=str, required=True)
    parser.add_argument('-bufl','--bd_buff_list',default="",nargs='+',help="List containt value buffer for each bd vector input.ex 1.0 2.0 5.3", type=float, required=True)
    parser.add_argument('-sql','--sql_expression_list',default=None,help="List containt sql expression to filter each db input (separator is ':' and not used \" for string value)", type=str, required=False)
    parser.add_argument('-macro','--macro_sample_name',default="",help="Name of macro sample", type=str, required=False)
    parser.add_argument('-simp','--simplify_vector_param',default=10.0,help="Parameter of polygons simplification. By default : 10.0", type=float, required=False)
    parser.add_argument('-vef','--format_vector', default="ESRI Shapefile",help="Format of the output file.", type=str, required=False)
    parser.add_argument('-vee','--extension_vector',default=".shp",help="Option : Extension file for vector. By default : '.shp'", type=str, required=False)
    parser.add_argument('-log','--path_time_log',default="",help="Name of log", type=str, required=False)
    parser.add_argument('-sav','--save_results_inter',action='store_true',default=False,help="Save or delete intermediate result after the process. By default, False", required=False)
    parser.add_argument('-now','--overwrite',action='store_false',default=True,help="Overwrite files with same names. By default, True",required=False)
    parser.add_argument('-debug','--debug',default=3,help="Option : Value of level debug trace, default : 3 ",type=int, required=False)
    args = displayIHM(gui, parser)

    # RECUPERATION DES ARGUMENTS
    # Récupération de l'image d'entrée
    image_input = None
    if args.image_input != None:
        image_input = args.image_input
        if image_input != "" and not os.path.isfile(image_input):
            raise NameError (cyan + "MacroSamplesCreation : " + bold + red  + "File %s not existe!" %(image_input) + endC)

    # Récupération du vecteur de decoupe
    vector_cut_input = None
    if args.vector_cut_input != None :
        vector_cut_input = args.vector_cut_input
        if vector_cut_input != "" and not os.path.isfile(vector_cut_input):
            raise NameError (cyan + "MacroSamplesCreation : " + bold + red  + "File %s not existe!" %(vector_cut_input) + endC)

    # Récupération du vecteur de sortie
    if args.vector_sample_output != None:
        vector_sample_output = args.vector_sample_output

    # Récupération du raster de sortie
    if args.raster_sample_output != None:
        raster_sample_output = args.raster_sample_output

        if vector_sample_output == "" and raster_sample_output == "" :
            raise NameError (cyan + "MacroSamplesCreation : " + bold + red  + "At least one ouput file must be defined vector or raster" + endC)

        if vector_sample_output == "" :
            vector_sample_output = os.path.splitext(raster_sample_output)[0] + extension_vector

    # Récupération des vecteurs de bd exogenes
    if args.bd_vector_input_list != None :
        bd_vector_input_list = args.bd_vector_input_list

    # liste des valeurs des buffers associés au traitement des vecteurs de bd exogenes
    if args.bd_buff_list != None:
        bd_buff_list = args.bd_buff_list
        if len(bd_buff_list) != len(bd_vector_input_list) :
             raise NameError (cyan + "MacroSamplesCreation : " + bold + red  + "List buffer value  size %d is differente at size bd vector input list!" %(len(bd_buff_list)) + endC)

    # liste des expression sql pour filtrer les vecteurs de bd exogenes
    if args.sql_expression_list != None:
        sql_expression_list = args.sql_expression_list.replace('"','').split(":")
        if len(sql_expression_list) != len(bd_vector_input_list) :
             raise NameError (cyan + "MacroSamplesCreation : " + bold + red  + "List sql expression size %d is differente at size bd vector input list!" %(len(sql_expression_list)) + endC)
    else :
        sql_expression_list = []

    # macro_sample_name param
    if args.macro_sample_name != None:
        macro_sample_name = args.macro_sample_name

    # simplify_vector_param param
    if args.simplify_vector_param != None:
        simplify_vector_param = args.simplify_vector_param

    # Récupération du format des vecteurs de sortie
    if args.format_vector != None :
        format_vector = args.format_vector

    # Récupération de l'extension des fichiers vecteurs
    if args.extension_vector != None:
        extension_vector = args.extension_vector

    # Récupération du nom du fichier log
    if args.path_time_log!= None:
        path_time_log = args.path_time_log

    # Sauvegarde des résultats intermédiaires
    if args.save_results_inter != None:
        save_results_intermediate = args.save_results_inter

    # Ecrasement des fichiers
    if args.overwrite != None:
        overwrite = args.overwrite

    # Récupération de l'option niveau de debug
    if args.debug!= None:
        global debug
        debug = args.debug

    if debug >= 3:
        print(bold + green + "MacroSamplesCreation : Variables dans le parser" + endC)
        print(cyan + "MacroSamplesCreation : " + endC + "image_input : " + str(image_input) + endC)
        print(cyan + "MacroSamplesCreation : " + endC + "vector_cut_input : " + str(vector_cut_input) + endC)
        print(cyan + "MacroSamplesCreation : " + endC + "vector_sample_output : " + str(vector_sample_output) + endC)
        print(cyan + "MacroSamplesCreation : " + endC + "raster_sample_output : " + str(raster_sample_output) + endC)
        print(cyan + "MacroSamplesCreation : " + endC + "bd_vector_input_list : " + str(bd_vector_input_list) + endC)
        print(cyan + "MacroSamplesCreation : " + endC + "sql_expression_list : " + str(sql_expression_list) + endC)
        print(cyan + "MacroSamplesCreation : " + endC + "bd_buff_list : " + str(bd_buff_list) + endC)
        print(cyan + "MacroSamplesCreation : " + endC + "macro_sample_name : " + str(macro_sample_name) + endC)
        print(cyan + "MacroSamplesCreation : " + endC + "simplify_vector_param : " + str(simplify_vector_param) + endC)
        print(cyan + "MacroSamplesCreation : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "MacroSamplesCreation : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "MacroSamplesCreation : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "MacroSamplesCreation : " + endC + "save_results_inter : " + str(save_results_intermediate) + endC)
        print(cyan + "MacroSamplesCreation : " + endC + "overwrite: " + str(overwrite) + endC)
        print(cyan + "MacroSamplesCreation : " + endC + "debug: " + str(debug) + endC)

    # Test si les entrees image_input et vector_cut_input sont a None
    if image_input == None and vector_cut_input == None:
        raise NameError (cyan + "MacroSamplesCreation() : " + bold + red + "Les entrées image_input et vector_cut_input ne peuvent être toutes les deux à vide! " + endC)

    # EXECUTION DE LA FONCTION
    # Si le dossier de sortie n'existe pas, on le crée
    repertory_output = os.path.dirname(vector_sample_output)
    if not os.path.isdir(repertory_output):
        os.makedirs(repertory_output)

    # execution de la fonction pour une image
    createMacroSamples(image_input, vector_cut_input, vector_sample_output, raster_sample_output, bd_vector_input_list, bd_buff_list, sql_expression_list, path_time_log, macro_sample_name, simplify_vector_param, format_vector, extension_vector, save_results_intermediate, overwrite)

# ================================================

if __name__ == '__main__':
  main(gui=False)
