#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

"""
Nom de l'objet : GenerateOcsWithVectors.py
Description :
-------------
Objectif : génère un raster d'occupation du sol (OCS) à partir d'une liste de vecteurs, renseignés dans un fichier texte
Remarque : se base sur la fonction createMacroSamples() de l'appli MacroSamplesCreation (gère donc les buffers et le filtrage SQL)
chaque ligne du fichier txt se présente de la façon suivante : label_OCS:fichier_a_traiter:decoupage:buffer:filtrage_SQL (ex : 11000:/mnt/RAM_disk/BD_Topo/bati.shp:True:0:HAUTEUR != 0)

-----------------
Outils utilisés :

------------------------------
Historique des modifications :
11/01/2021 : création

-----------------------
A réfléchir / A faire :

"""

# Import des bibliothèques Python
from __future__ import print_function
import os, sys, shutil, argparse
from Lib_display import bold,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_file import cleanTempData, deleteDir, removeFile
from Lib_log import timeLine
from Lib_raster import getEmpriseImage, rasterizeBinaryVector, rasterCalculator
from Lib_text import readTextFileBySeparator
from Lib_vector import getEmpriseVector, cutVectorAll, getAttributeNameList, filterSelectDataVector, bufferVector

# Niveau de debug (variable globale)
debug = 3

########################################################################
# FONCTION vectorsListToOcs()                                          #
########################################################################
def vectorsListToOcs(input_text, output_raster, footprint_vector, reference_raster, codage_raster='uint8', epsg=2154, no_data_value=0, format_raster='GTiff', format_vector='ESRI Shapefile', extension_raster='.tif', extension_vector='.shp', path_time_log='', save_results_intermediate=False, overwrite=True):
    """
    # ROLE :
    #     transforme une liste de vecteurs en classification OCS raster
    #
    # ENTREES DE LA FONCTION :
    #     input_text : fichier texte en entrée (qui contient la liste des vecteurs à traiter)
    #     output_raster : fichier raster de sortie (qui correspond à l'OCS générée à partir des vecteurs)
    #     footprint_vector : fichier vecteur d'emprise (qui délimite la zone d'étude)
    #     reference_raster : fichier raster de référence (pour la rastérisation des vecteurs)
    #     codage_raster : encodage du raster de sortie. Par défaut : uint8 [uint8/uint16/int16/uint32/int32/float/double/cint16/cint32/cfloat/cdouble]
    #     epsg : code epsg du système de projection. Par défaut : 2154
    #     no_data_value : valeur NoData des pixels des fichiers raster. Par défaut : 0
    #     format_raster : format des fichiers raster. Par défaut : 'GTiff'
    #     format_vector : format des fichiers vecteur. Par défaut : 'ESRI Shapefile'
    #     extension_raster : extension des fichiers raster. Par défaut : '.tif'
    #     extension_vector : extension des fichiers vecteur. Par défaut : '.shp'
    #     path_time_log : fichier log de sortie, par défaut vide
    #     save_results_intermediate : fichiers temporaires conservés, par défaut = False
    #     overwrite : écrase si un fichier existant a le même nom qu'un fichier de sortie, par défaut = True
    #
    # SORTIES DE LA FONCTION :
    #     N.A.
    """

    if debug >= 3:
        print('\n' + bold + green + "OCS raster à partir d'une liste de vecteurs - Variables dans la fonction :" + endC)
        print(cyan + "    vectorsListToOcs() : " + endC + "input_text : " + str(input_text) + endC)
        print(cyan + "    vectorsListToOcs() : " + endC + "output_raster : " + str(output_raster) + endC)
        print(cyan + "    vectorsListToOcs() : " + endC + "footprint_vector : " + str(footprint_vector) + endC)
        print(cyan + "    vectorsListToOcs() : " + endC + "reference_raster : " + str(reference_raster) + endC)
        print(cyan + "    vectorsListToOcs() : " + endC + "codage_raster : " + str(codage_raster) + endC)
        print(cyan + "    vectorsListToOcs() : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "    vectorsListToOcs() : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "    vectorsListToOcs() : " + endC + "format_raster : " + str(format_raster) + endC)
        print(cyan + "    vectorsListToOcs() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "    vectorsListToOcs() : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "    vectorsListToOcs() : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "    vectorsListToOcs() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "    vectorsListToOcs() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "    vectorsListToOcs() : " + endC + "overwrite : " + str(overwrite) + endC + '\n')

    # Définition des constantes
    SUFFIX_TEMP = '_temp'
    SUFFIX_CUT = '_cut'
    SUFFIX_FILTER = '_filter'
    SUFFIX_BUFFER = '_buffer'
    TEXT_SEPARATOR = ':'

    # Mise à jour du log
    starting_event = "vectorsListToOcs() : Début du traitement : "
    timeLine(path_time_log, starting_event)

    print(cyan + "vectorsListToOcs() : " + bold + green + "DEBUT DES TRAITEMENTS" + endC + '\n')

    # Définition des variables 'basename'
    output_raster_basename = os.path.basename(os.path.splitext(output_raster)[0])
    output_raster_dirname = os.path.dirname(output_raster)

    # Définition des variables temp
    temp_directory = output_raster_dirname + os.sep + output_raster_basename + SUFFIX_TEMP
    temp_raster = temp_directory + os.sep + output_raster_basename + SUFFIX_TEMP + extension_raster

    # Nettoyage des traitements précédents
    if overwrite:
        if debug >= 3:
            print(cyan + "vectorsListToOcs() : " + endC + "Nettoyage des traitements précédents." + '\n')
        removeFile(output_raster)
        cleanTempData(temp_directory)
    else:
        if os.path.exists(output_raster):
            print(cyan + "vectorsListToOcs() : " + bold + yellow + "Le fichier de sortie existe déjà et ne sera pas regénéré." + endC)
            raise
        if not os.path.exixts(temp_directory):
            os.makedirs(temp_directory)
        pass

    # Test de l'emprise des fichiers vecteur d'emprise et raster de référence (le raster doit être de même taille ou plus grand que le vecteur)
    xmin_fpt, xmax_fpt, ymin_fpt, ymax_fpt = getEmpriseVector(footprint_vector, format_vector=format_vector)
    xmin_ref, xmax_ref, ymin_ref, ymax_ref = getEmpriseImage(reference_raster)
    if round(xmin_fpt,4) < round(xmin_ref,4) or round(xmax_fpt,4) > round(xmax_ref,4) or round(ymin_fpt,4) < round(ymin_ref,4) or round(ymax_fpt,4) > round(ymax_ref,4) :
        print(cyan + "vectorsListToOcs() : " + bold + red + "xmin_fpt, xmax_fpt, ymin_fpt, ymax_fpt" + endC, xmin_fpt, xmax_fpt, ymin_fpt, ymax_fpt, file = sys.stderr)
        print(cyan + "vectorsListToOcs() : " + bold + red + "xmin_ref, xmax_ref, ymin_ref, ymax_ref" + endC, xmin_ref, xmax_ref, ymin_ref, ymax_ref, file = sys.stderr)
        raise NameError(cyan + "vectorsListToOcs() : " + bold + red + "The extend of the footprint vector (%s) is greater than the reference raster (%s)." % (footprint_vector, reference_raster) + endC)

    # Récupération des traitements à faire dans le fichier texte d'entrée
    text_list = readTextFileBySeparator(input_text, TEXT_SEPARATOR)

    ####################################################################

    print(cyan + "vectorsListToOcs() : " + bold + green + "Début de la génération de l'OCS raster à partir de vecteurs." + endC + '\n')

    # Boucle sur les traitements à réaliser
    for text in text_list:
        idx = text_list.index(text)+1
        class_label = int(text[0])
        vector_file = text[1]
        if debug >= 3:
            print(cyan + "vectorsListToOcs() : " + endC + bold + "Génération %s/%s : " % (idx, len(text_list)) + endC + "traitement du fichier %s (label %s)." % (vector_file, str(class_label)) + '\n')

        # Gestion des noms des fichiers temporaires
        vector_file_basename = os.path.basename(os.path.splitext(vector_file)[0])
        vector_file_cut = temp_directory + os.sep + vector_file_basename + SUFFIX_CUT + extension_vector
        vector_file_filter = temp_directory + os.sep + vector_file_basename + SUFFIX_FILTER + extension_vector
        vector_file_buffer = temp_directory + os.sep + vector_file_basename + SUFFIX_BUFFER + extension_vector
        vector_file_raster = temp_directory + os.sep + vector_file_basename + extension_raster

        # Gestion des variables de traitement (découpage, tampon et filtrage SQL)
        try:
            make_cut = text[2]
        except Exception:
            make_cut = "True"
        try:
            buffer_len = float(text[3])
        except ValueError:
            buffer_len = text[3]
        except Exception:
            buffer_len = ''
        try:
            sql_filter = text[4]
        except Exception:
            sql_filter = ''

        # Découpage à l'emprise de la zone d'étude
        if make_cut.lower() == 'true':
            if debug >= 3:
                print(cyan + "vectorsListToOcs() : " + endC + "Découpage à l'emprise de la zone d'étude." + '\n')
            cutVectorAll(footprint_vector, vector_file, vector_file_cut, overwrite=overwrite, format_vector=format_vector)
        else:
            vector_file_cut = vector_file

        # Filtrage SQL (facultatif)
        if sql_filter != '':
            if debug >= 3:
                print(cyan + "vectorsListToOcs() : " + endC + "Application du filtrage SQL : %s." % sql_filter + '\n')
            attr_names_list = getAttributeNameList(vector_file_cut, format_vector=format_vector)
            column = "'"
            for attr_name in attr_names_list :
                column += attr_name + ", "
            column = column[:-2]
            column += "'"
            filterSelectDataVector (vector_file_cut, vector_file_filter, column, sql_filter, overwrite=overwrite, format_vector=format_vector)
        else:
            vector_file_filter = vector_file_cut

        # Application d'un tampon (facultatif)
        if buffer_len != '' and buffer_len != 0:
            if debug >= 3:
                print(cyan + "vectorsListToOcs() : " + endC + "Application d'un buffer : %s." % buffer_len + '\n')
            if type(buffer_len) is float:
                bufferVector(vector_file_filter, vector_file_buffer, buffer_len, col_name_buf = '', fact_buf=1.0, quadsecs=10, format_vector=format_vector)
            else:
                bufferVector(vector_file_filter, vector_file_buffer, 0, col_name_buf = buffer_len, fact_buf=1.0, quadsecs=10, format_vector=format_vector)
        else:
            vector_file_buffer = vector_file_filter

        # Rastérisation du vecteur préparé
        if debug >= 3:
            print(cyan + "vectorsListToOcs() : " + endC + "Rastérisation du vecteur préparé." + '\n')
        rasterizeBinaryVector(vector_file_buffer, reference_raster, vector_file_raster, label=class_label, codage=codage_raster)

        # Ajout de l'information dans le raster de sortie
        if debug >= 3:
            print(cyan + "vectorsListToOcs() : " + endC + "Ajout de l'information dans le raster de sortie." + '\n')
        if idx == 1:
            shutil.copy(vector_file_raster, output_raster)
        else:
            removeFile(temp_raster)
            shutil.copy(output_raster, temp_raster)
            removeFile(output_raster)
            expression = "im1b1!=%s ? im1b1 : im2b1" % no_data_value
            rasterCalculator([temp_raster, vector_file_raster], output_raster, expression, codage=codage_raster)

    print(cyan + "vectorsListToOcs() : " + bold + green + "Fin de la génération de l'OCS raster à partir de vecteurs." + endC + '\n')

    ####################################################################

    # Suppression des fichiers temporaires
    if not save_results_intermediate:
        if debug >= 3:
            print(cyan + "vectorsListToOcs() : " + endC + "Suppression des fichiers temporaires." + '\n')
        deleteDir(temp_directory)

    print(cyan + "vectorsListToOcs() : " + bold + green + "FIN DES TRAITEMENTS" + endC + '\n')

    # Mise à jour du log
    ending_event = "vectorsListToOcs() : Fin du traitement : "
    timeLine(path_time_log, ending_event)

    return 0

#############################################################################################################################
################################################## Mise en place du parser ##################################################
#############################################################################################################################

def main(gui=False):
    parser = argparse.ArgumentParser(prog = "Génération OCS raster à partir de vecteurs", description = "\
    Génère un raster d'occupation du sol (OCS) à partir d'une liste de vecteurs, renseignés dans un fichier texte. \n\
    Exemple : python3 -m GenerateOcsWithVectors -in /mnt/RAM_disk/vectors_list.txt \n\
                                                -out /mnt/RAM_disk/OCS_from_vectors.tif \n\
                                                -fpt /mnt/RAM_disk/study_area.shp \n\
                                                -ref /mnt/RAM_disk/reference_image.tif")

    parser.add_argument('-in', '--input_text', default="", type=str, required=True, help="Input text file: contains vectors list to treat.")
    parser.add_argument('-out', '--output_raster', default="", type=str, required=True, help="Output raster file: soil occupation from vectors.")
    parser.add_argument('-fpt', '--footprint_vector', default="", type=str, required=True, help="Footprint vector file: delimits the study area.")
    parser.add_argument('-ref', '--reference_raster', default="", type=str, required=True, help="Reference raster file: for vectors rasterization.")
    parser.add_argument('-cod', '--codage_raster', default="uint8", type=str, required=False, help="Data type of the output raster file. Default: 'uint8' [uint8/uint16/int16/uint32/int32/float/double/cint16/cint32/cfloat/cdouble].")
    parser.add_argument('-epsg', '--epsg', default=2154, type=int, required=False, help="Projection of the output file. Default: 2154.")
    parser.add_argument('-ndv', '--no_data_value', default=0, type=int, required=False, help="Value of the NoData pixel. Default: 0.")
    parser.add_argument('-raf', '--format_raster', default="GTiff", type=str, required=False, help="Format of raster file. Default: 'GTiff'.")
    parser.add_argument('-vef', '--format_vector', default="ESRI Shapefile", type=str, required=False, help="Format of vector file. Default: 'ESRI Shapefile'.")
    parser.add_argument('-rae', '--extension_raster', default=".tif", type=str, required=False, help="Extension file for raster file. Default: '.tif'.")
    parser.add_argument('-vee', '--extension_vector', default=".shp", type=str, required=False, help="Extension file for vector file. Default: '.shp'.")
    parser.add_argument('-log', '--path_time_log', default="", type=str, required=False, help="Option: Name of log. Default, no log file.")
    parser.add_argument('-sav', '--save_results_intermediate', action='store_true', default=False, required=False, help="Option: Save intermediate result after the process. Default, False.")
    parser.add_argument('-now', '--overwrite', action='store_false', default=True, required=False, help="Option: Overwrite files with same names. Default, True.")
    parser.add_argument('-debug', '--debug', default=3, type=int, required=False, help="Option: Value of level debug trace. Default, 3.")
    args = displayIHM(gui, parser)

    # Récupération du fichier texte d'entrée
    if args.input_text != None:
        input_text = args.input_text
        if not os.path.isfile(input_text):
            raise NameError (cyan + "GenerateOcsWithVectors: " + bold + red  + "File %s not exists (input_text)." % input_text + endC)

    # Récupération du fichier raster de sortie
    if args.output_raster != None:
        output_raster = args.output_raster

    # Récupération du fichier vecteur d'emprise
    if args.footprint_vector != None:
        footprint_vector = args.footprint_vector
        if not os.path.isfile(footprint_vector):
            raise NameError (cyan + "GenerateOcsWithVectors: " + bold + red  + "File %s not exists (footprint_vector)." % footprint_vector + endC)

    # Récupération du fichier raster de référence
    if args.reference_raster != None:
        reference_raster = args.reference_raster
        if not os.path.isfile(reference_raster):
            raise NameError (cyan + "GenerateOcsWithVectors: " + bold + red  + "File %s not exists (reference_raster)." % reference_raster + endC)

    # Récupération du codage du raster de sortie
    if args.codage_raster != None:
        codage_raster = args.codage_raster

    # Récupération des paramètres fichiers
    if args.epsg != None:
        epsg = args.epsg
    if args.no_data_value != None:
        no_data_value = args.no_data_value
    if args.format_raster != None:
        format_raster = args.format_raster
    if args.format_vector != None:
        format_vector = args.format_vector
    if args.extension_raster != None:
        extension_raster = args.extension_raster
    if args.extension_vector != None:
        extension_vector = args.extension_vector

    # Récupération des paramètres généraux
    if args.path_time_log != None:
        path_time_log = args.path_time_log
    if args.save_results_intermediate != None:
        save_results_intermediate = args.save_results_intermediate
    if args.overwrite != None:
        overwrite = args.overwrite
    if args.debug != None:
        global debug
        debug = args.debug

    if os.path.isfile(output_raster) and not overwrite:
        raise NameError (cyan + "GenerateOcsWithVectors: " + bold + red  + "File %s already exists, and overwrite is not activated." % output_raster + endC)

    if debug >= 3:
        print('\n' + bold + green + "Génération OCS raster à partir de vecteurs - Variables dans le parser :" + endC)
        print(cyan + "    GenerateOcsWithVectors : " + endC + "input_text : " + str(input_text) + endC)
        print(cyan + "    GenerateOcsWithVectors : " + endC + "output_raster : " + str(output_raster) + endC)
        print(cyan + "    GenerateOcsWithVectors : " + endC + "footprint_vector : " + str(footprint_vector) + endC)
        print(cyan + "    GenerateOcsWithVectors : " + endC + "reference_raster : " + str(reference_raster) + endC)
        print(cyan + "    GenerateOcsWithVectors : " + endC + "codage_raster : " + str(codage_raster) + endC)
        print(cyan + "    GenerateOcsWithVectors : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "    GenerateOcsWithVectors : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "    GenerateOcsWithVectors : " + endC + "format_raster : " + str(format_raster) + endC)
        print(cyan + "    GenerateOcsWithVectors : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "    GenerateOcsWithVectors : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "    GenerateOcsWithVectors : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "    GenerateOcsWithVectors : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "    GenerateOcsWithVectors : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "    GenerateOcsWithVectors : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "    GenerateOcsWithVectors : " + endC + "debug : " + str(debug) + endC + '\n')

    # Création du dossier de sortie, s'il n'existe pas
    if not os.path.isdir(os.path.dirname(output_raster)):
        os.makedirs(os.path.dirname(output_raster))

    # EXECUTION DES FONCTIONS
    vectorsListToOcs(input_text, output_raster, footprint_vector, reference_raster, codage_raster, epsg, no_data_value, format_raster, format_vector, extension_raster, extension_vector, path_time_log, save_results_intermediate, overwrite)

if __name__ == '__main__':
    main(gui=False)

