#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT FAIT UNE RE LABELLISATION AUTOMATIQUE SUR UN RASTER A PARTIR D'UNE TABLE DE RELABELLISATION                                        #
#                                                                                                                                           #
#############################################################################################################################################
"""
Nom de l'objet : RasterAssembly.py
Description :
-------------
Objectif : Fusionner des raster entre eux et gérer les frontières qui les séparent
Rq : utilisation des OTB Applications :   otbcli_BandMath, otbcli_ClassificationMapRegularization

Date de creation : 29/06/2015
----------
Histoire :
----------
Origine : nouveau
-----------------------------------------------------------------------------------------------------
Modifications :

------------------------------------------------------
A Reflechir/A faire ;

"""
# Import des bibliothèques python
from __future__ import print_function
import os,sys,glob,string,shutil,time,argparse, platform
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_log import timeLine
from Lib_raster import cutImageByVector
from Lib_file import deleteDir, removeFile

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 3

###########################################################################################################################################
# FONCTION rasterAssembly                                                                                                                 #
###########################################################################################################################################
def rasterAssembly(input_images_list, output_image, radius, value_to_force, boundaries_shape, no_data_value, path_time_log, format_raster='GTiff', format_vector='ESRI Shapefile', extension_raster=".tif", save_results_inter = False, overwrite=True) :
    """
    # ROLE:
    #     Assembler plusieurs fichiers raster .tif en un seul fichier raster et découpage du résultat suivant une emprise
    #
    # ENTREES DE LA FONCTION :
    #     input_images_list : liste d'images classées en plusieurs classes au format.tif
    #     output_image : image re-classée en fonction des info de la table de réallocation au format.tif
    #     radius : paremetres rayon pour le filtre majoritaire
    #     value_to_force : Rayon de filtre appliqué à la majorité traité de limites
    #     boundaries_shape : fichier vecteur de découpe du fichier resultat
    #     no_data_value : Valeur des pixels sans données pour les rasters de sortie
    #     path_time_log : le fichier de log de sortie
    #     format_raster : Format de l'image de sortie, par défaut : GTiff
    #     format_vector : format du fichier vecteur. Optionnel, par default : 'ESRI Shapefile'
    #     extension_raster : extension des fichiers raster de sortie, par defaut = '.tif'
    #     save_results_intermediate : fichiers de sorties intermediaires nettoyees, par defaut = False
    #     overwrite : supprime ou non les fichiers existants ayant le meme nom
    #
    # SORTIES DE LA FONCTION :
    #     aucun
    """

    # Mise à jour du Log
    starting_event = "rasterAssembly() : Assemblage d'images raster starting "
    timeLine(path_time_log,starting_event)

    if debug >= 3:
       print(cyan + "rasterAssembly() : " + endC + "input_images_list : " +  str(input_images_list))
       print(cyan + "rasterAssembly() : " + endC + "output_image : " + str(output_image))
       print(cyan + "rasterAssembly() : " + endC + "radius : " + str(radius))
       print(cyan + "rasterAssembly() : " + endC + "value_to_force : " + str(value_to_force))
       print(cyan + "rasterAssembly() : " + endC + "boundaries_shape : " + str(boundaries_shape))
       print(cyan + "rasterAssembly() : " + endC + "no_data_value : " + str(no_data_value) + endC)
       print(cyan + "rasterAssembly() : " + endC + "path_time_log : " + str(path_time_log))
       print(cyan + "rasterAssembly() : " + endC + "format_raster : " + str(format_raster) + endC)
       print(cyan + "rasterAssembly() : " + endC + "format_vector : " + str(format_vector) + endC)
       print(cyan + "rasterAssembly() : " + endC + "extension_raster : " + str(extension_raster) + endC)
       print(cyan + "rasterAssembly() : " + endC + "save_results_inter : " + str(save_results_inter))
       print(cyan + "rasterAssembly() : " + endC + "overwrite : " + str(overwrite))

    print(cyan + "rasterAssembly() : " + bold + green + "START ...\n" + endC)

    # Gestion des noms de variables
    CODAGE = "uint16"

    images_input_list_str = " "
    for input_image in input_images_list:
        images_input_list_str += input_image + " "

    output_dir = os.path.dirname(output_image)
    output_name = os.path.splitext(os.path.basename(output_image))[0]

    temp_directory = output_dir + os.sep + "Temp"
    vrt_image = temp_directory + os.sep + output_name + '_vrt' + extension_raster
    assembled_image = temp_directory + os.sep + output_name + '_assembled' + extension_raster
    assembled_smoothed_image = temp_directory + os.sep + output_name + '_assembled_smoothed' + extension_raster
    assembled_cleaned_with_smooth_image = temp_directory + os.sep + output_name + '_assembled_cleaned_with_smooth' + extension_raster
    assembled_cleaned_with_smooth_and_value_to_force_image = temp_directory + os.sep + output_name + '_assembled_cleaned_with_smooth_and_value_to_force' + extension_raster
    assembled_cleaned_cutted_image = temp_directory + os.sep + output_name + '_assembled_cleaned_cutted' + extension_raster

    # ETAPE 1/5 : CREATION DU RASTER VIRTUEL

    if not os.path.exists(temp_directory):
        os.makedirs(temp_directory)

    command = "gdalbuildvrt -srcnodata %s %s %s" %(str(no_data_value), vrt_image, images_input_list_str)
    if debug >=2:
        print('\n' + cyan + "rasterAssembly() : " + bold + green + "ETAPE 1/5 : DEBUT DE LA CREATION DU RASTER VIRTUEL. Sortie : %s - Entrees : %s" %(vrt_image, images_input_list_str) + endC)
        print(command)

    exitCode = os.system(command)

    if exitCode != 0:
        raise NameError(cyan + "rasterAssembly() : " + bold + red + "An error occured during the virtual raster construction. See error message above.")
    else:
        if debug >=2:
            print('\n' + cyan + "rasterAssembly() : " + bold + green + "ETAPE 1/5 : FIN DE LA CREATION DU RASTER VIRTUEL" + endC)

    # ETAPE 2/5 : DEBUT DE LA CONVERSION DU RASTER VIRTUEL EN .tif
    command = "gdal_translate -a_nodata %s -of %s %s %s" %(str(no_data_value), format_raster, vrt_image, assembled_image)
    if debug >=2:
        print('\n' + cyan + "rasterAssembly() : " + bold + green + "ETAPE 2/5 : DEBUT DE LA CONVERSION DU RASTER VIRTUEL EN .tif. Entree : %s - Sortie : %s" %(vrt_image,assembled_image) + endC)
        print(command)

    exitCode = os.system(command)

    if exitCode != 0:
        raise NameError(cyan + "rasterAssembly() : " + bold + red + "An error occured during the virtual raster conversion. See error message above.")
    else:
        if debug >=2:
            print('\n' + cyan + "rasterAssembly() : " + bold + green + "ETAPE 2/5 : FIN DE LA CONVERSION DU RASTER VIRTUEL EN .tif. " + endC)

    # ETAPE 3/5 : SUPPRESSION EVENTUELLE DU RASTER VIRTUEL
    if not save_results_inter:
        if debug >=2:
            print('\n' + cyan + "rasterAssembly() : " + bold + green + "ETAPE 3/5 : DEBUT DE LA SUPRESSION DU RASTER VIRTUEL %s" %(vrt_image) + endC)
        try:
            removeFile(vrt_image) # Tentative de suppression du fichier
        except Exception:
            pass                 # Si le fichier ne peut pas être supprimé, on suppose qu'il n'existe pas et on passe à la suite
        if debug >=2:
            print(cyan + "rasterAssembly() : " + bold + green + "ETAPE 3/5 : FIN DE LA SUPRESSION DU RASTER VIRTUEL" + endC)
    else :
        if debug >=2:
            print(cyan + "rasterAssembly() : " + bold + yellow + "ETAPE 3/5 : PAS DE SUPPRESSION DU RASTER VIRTUEL %s" %(vrt_image) + endC)

    # ETAPE 4/5 et 5/5 : SI DEMANDE : CALCUL ET APPLICATION DU FILTRE MAJORITAIRE
    if radius > 0 :

        # ETAPE 4/5 : Calcul du fichier filtre majoritaire
        command = "otbcli_ClassificationMapRegularization -io.in %s -io.out %s %s -ip.radius %d" %(assembled_image, assembled_smoothed_image, CODAGE, radius)
        if debug >=2:
            print('\n' + cyan + "rasterAssembly() : " + bold + green + "ETAPE 4/5 : DEBUT DU CALCUL DU FILTRE MAJORITAIRE DE RAYON %s. Entree : %s - Sortie : %s" %(radius, assembled_image,assembled_smoothed_image) + endC)
            print(command)

        exitCode = os.system(command)

        if exitCode != 0:
            raise NameError(cyan + "rasterAssembly() : " + bold + red + "An error occured during otbcli_ClassificationMapRegularization command. See error message above.")
        else :
            if debug >=2:
                print(cyan + "rasterAssembly() : " + bold + green + "ETAPE 4/5 : FIN DU CALCUL DU FILTRE MAJORITAIRE" + endC)

        # ETAPE 5/5 : Utilisation du fichier raster filtre majoritaire pour boucher les trous eventuels entre les images assemblées
        expression = "\"(im1b1 == 0? im2b1 : im1b1)\""
        command = "otbcli_BandMath -il %s %s -exp %s -out %s %s" %(assembled_image, assembled_smoothed_image, expression, assembled_cleaned_with_smooth_image, CODAGE)
        if debug >=2:
            print('\n' + cyan + "rasterAssembly() : " + bold + green + "ETAPE 5/5 : DEBUT DE L'APPLICATION DU FILTRE MAJORITAIRE. Sortie : %s - Entree : %s et %s" %(assembled_cleaned_with_smooth_image, assembled_image, assembled_smoothed_image) + endC)
            print(command)

        exitCode = os.system(command)

        if exitCode != 0:
            raise NameError(cyan + "rasterAssembly() : " + bold + red + "An error occured during otbcli_BandMath command. See error message above.")
        else :
            if debug >=2:
                print(cyan + "rasterAssembly() : " + bold + green + "ETAPE 5/5 : FIN DE L'APPLICATION DU FILTRE MAJORITAIRE" + endC)

        # Supression éventuelle du filtre majoritaire et de l'image non nettoyée
        if not save_results_inter:
            if debug >=2:
                print(cyan + "rasterAssembly() : " + bold + green + "SUPRESSION DU FILTRE MAJORITAIRE %s ET DE L'IMAGE NON NETTOYEE %s" %(assembled_smoothed_image, assembled_image) + endC)
            try:
                removeFile(assembled_smoothed_image) # Tentative de suppression du fichier
            except Exception:
                pass                       # Si le fichier ne peut pas être supprimé, on suppose qu'il n'existe pas et on passe à la suite

            try:
                removeFile(assembled_image) # Tentative de suppression du fichier
            except Exception:
                pass                       # Si le fichier ne peut pas être supprimé, on suppose qu'il n'existe pas et on passe à la suite

    else : # Cas où le filtre majoritaire n'est pas demandé
        assembled_cleaned_with_smooth_image = assembled_image
        if debug >=2:
            print('\n' + cyan + "rasterAssembly() : " + bold + yellow + "ETAPE 4/5 : PAS DE CALCUL DU FILTRE MAJORITAIRE DEMANDE" + endC)
            print('\n' + cyan + "rasterAssembly() : " + bold + yellow + "ETAPE 5/5 : PAS D'APPLICATION DU FILTRE MAJORITAIRE DEMANDE" + endC)

    # ETAPE 6/5 : SI DEMANDE : ON IMPOSE UNE VALEUR "value_to_force" POUR LES 0 RESTANTS
    if value_to_force > 0 :
        expression = "\"(im1b1 == 0? %d : im1b1)\"" %(value_to_force)
        command = "otbcli_BandMath -il %s -exp %s -out %s %s" %(assembled_cleaned_with_smooth_image, expression, assembled_cleaned_with_smooth_and_value_to_force_image, CODAGE)
        if debug >=2:
            print('\n' + cyan + "rasterAssembly() : " + bold + green + "ETAPE 6/5 : DEBUT DU NETTOYAGE DES ZEROS RESTANTS, TRANSFORMES EN %s. SORTIE : %s" %(value_to_force, assembled_cleaned_with_smooth_and_value_to_force_image) + endC)
            print(command)

        exitCode = os.system(command)

        if exitCode != 0:
            raise NameError(cyan + "rasterAssembly() : " + bold + red + "An error occured during the otbcli_BandMath command. See error message above.")
        else:
            if debug >=2:
                print(cyan + "rasterAssembly() : " + bold + green + "ETAPE 6/5 : FIN DU NETTOYAGE DES ZEROS RESTANTS" + endC)

        # Supression éventuelle de l'image non nettoyée
        if not save_results_inter:
            if debug >=2:
                print(cyan + "rasterAssembly() : " + bold + green + "SUPRESSION DE L'IMAGE NON NETTOYEE %s" %(assembled_cleaned_with_smooth_image) + endC)
            try:
                removeFile(assembled_cleaned_with_smooth_image) # Tentative de suppression du fichier
            except Exception:
                pass                       # Si le fichier ne peut pas être supprimé, on suppose qu'il n'existe pas et on passe à la suite

    else:  # Cas où le forcage d'une valeur n'est pas demandé
        assembled_cleaned_with_smooth_and_value_to_force_image = assembled_cleaned_with_smooth_image
        if debug >=2:
            print('\n' + cyan + "rasterAssembly() : " + bold + yellow + "ETAPE 6/5 : AUCUNE VALEUR IMPOSEE POUR LES 0" + endC)

    # ETAPE 7/5 : SI DEMANDE : DECOUPAGE AU REGARD DE L'EMPRISE
    if boundaries_shape != "" :

        if debug >=2:
            print('\n' + cyan + "rasterAssembly() : " + bold + green + "ETAPE 7/5 : DEBUT DU DECOUPAGE AU REGARD DE L EMPRISE GLOBALE %s" %(boundaries_shape) + endC)

        if not cutImageByVector(boundaries_shape, assembled_cleaned_with_smooth_and_value_to_force_image, output_image, None, None, False, no_data_value, 0, format_raster, format_vector) :
            raise NameError(cyan + "rasterAssembly() : " + bold + red + "An error occured during the cutting. See error message above.")
        else:
            if debug >=2:
                print(cyan + "rasterAssembly() : " + bold + green + "ETAPE 7/5 : FIN DU DECOUPAGE AU REGARD DE L'EMPRISE GLOBALE" + endC)

        # Supression éventuelle de l'image non découpée
        if not save_results_inter:
            if debug >=2:
                print(cyan + "rasterAssembly() : " + bold + green + "SUPRESSION DE L'IMAGE NON DECOUPEE %s" %(assembled_cleaned_with_smooth_and_value_to_force_image) + endC)
            try:
                removeFile(assembled_cleaned_with_smooth_and_value_to_force_image) # Tentative de suppression du fichier
            except Exception:
                pass                  # Si le fichier ne peut pas être supprimé, on suppose qu'il n'existe pas et on passe à la suite

    else :
        os.rename(assembled_cleaned_with_smooth_and_value_to_force_image, output_image)  # Dans ce cas, l'image finale est assembled_cleaned_with_smooth_and_value_to_force_image, qu'il faut renommer
        if debug >=2:
            print('\n' + cyan + "rasterAssembly() : " + bold + yellow + "ETAPE 7/5 : AUCUN DECOUPAGE FINAL DEMANDE" + endC)

    # SUPPRESSION DU DOSSIER TEMP
    if not save_results_inter and os.path.exists(temp_directory):
        deleteDir(temp_directory)

    if debug >=2:
        print(cyan + "rasterAssembly() : " + bold + green + "FIN DE L'ASSEMBLAGE DES RASTERS. Sortie : %s" %(output_image) + endC)

    # Mise à jour du Log
    ending_event = "rasterAssembly() : Realocation micro class on classification image ending : "
    timeLine(path_time_log,ending_event)
    return

###########################################################################################################################################
# MISE EN PLACE DU PARSER                                                                                                                 #
###########################################################################################################################################

# Code executé seulement dans le cas ou le script est lancé depuis une ligne de commande
# Il n'est pas executé lors d'un import ClassReallocationRaster.py
# Exemple de lancement en ligne de commande:
# python python RasterAssembly.py -il /mnt/hgfs/PartageVM2/D3_Global/Resultats/Raster/Temp/Paysage_01.tif /mnt/hgfs/PartageVM2/D3_Global/Resultats/Raster/Temp/Paysage_02.tif /mnt/hgfs/PartageVM2/D3_Global/Resultats/Raster/Temp/Paysage_03.tif -o /mnt/hgfs/PartageVM2/D3_Global/Resultats/Raster/Ardeche_Test.tif -v 22000 -b /mnt/hgfs/PartageVM2/D3_Global/Preparation/Study_Boundaries/DEP07.shp

def main(gui=False):

    # Définition des arguments possibles pour l'appel en ligne de commande
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,  prog="RasterAssembly", description="\
    Info : Assembly of different rasters. \n\
    Objectif : Assembler différents rasters. \n\
    Example : python RasterAssembly.py -il /mnt/hgfs/PartageVM2/D3_Global/Resultats/Raster/Temp/Paysage_01.tif \n\
                                           /mnt/hgfs/PartageVM2/D3_Global/Resultats/Raster/Temp/Paysage_02.tif \n\
                                           /mnt/hgfs/PartageVM2/D3_Global/Resultats/Raster/Temp/Paysage_03.tif \n\
                                       -o /mnt/hgfs/PartageVM2/D3_Global/Resultats/Raster/Ardeche_Test.tif \n\
                                       -v 22000 \n\
                                       -r 4 \n\
                                       -b /mnt/hgfs/PartageVM2/D3_Global/Preparation/Study_Boundaries/DEP07.shp")

    # Paramètres
    parser.add_argument('-il','--input_images_list', nargs="*", default="", help="List of raster to assembly", type=str, required=True)
    parser.add_argument('-o','--output_image', default=os.getcwd() + os.sep + "Output_Assembly.tif",help="Name of final raste.", type=str, required=False)
    parser.add_argument('-b','--boundaries_shape', default = "", help="Cutout vector of global result.", required=False)
    parser.add_argument('-r','--radius', default=0, help="Radius of majority filter applied to deals with boundaries. By default, radius = 0. If radius = 0 : no filter", type=int, required=False)
    parser.add_argument('-v','--value_to_force', default=0, help="Value to apply when pixels at 0 at the end. By default, value_to_force = 0 : no value forced", type=int, required=False)
    parser.add_argument("-ndv",'--no_data_value',default=0,help="Option pixel value for raster file to no data, default : 0 ", type=int, required=False)
    parser.add_argument('-raf','--format_raster', default="GTiff", help="Option : Format output image, by default : GTiff (GTiff, HFA...)", type=str, required=False)
    parser.add_argument('-vef','--format_vector', default="ESRI Shapefile",help="Format of the output file.", type=str, required=False)
    parser.add_argument('-rae','--extension_raster', default=".tif", help="Option : Extension file for image raster. By default : '.tif'", type=str, required=False)
    parser.add_argument('-log','--path_time_log', default="",help="Name of log", type=str, required=False)
    parser.add_argument('-sav','--save_results_inter', action='store_true', default=False,help="Save or delete intermediate result after the process. By default, False", required=False)
    parser.add_argument('-now','--overwrite', action='store_false', default=True,help="Overwrite files with same names. By default, True", required=False)
    parser.add_argument('-debug','--debug',default=3,help="Option : Value of level debug trace, default : 3 ",type=int, required=False)
    args = displayIHM(gui, parser)

    # RECUPERATION DES ARGUMENTS
    # Récupération de l'image d'entrée
    if args.input_images_list != None:
        input_images_list = args.input_images_list
        for input_image in input_images_list :
            if not os.path.isfile(input_image):
                raise NameError (cyan + "MacroSamplesAmelioration : " + bold + red  + "File %s not existe!" %(input_image) + endC)

    # Récupération de l'image de sortie
    if args.output_image != None:
        output_image = args.output_image

    # Récupération du vecteur de découpe final
    if args.boundaries_shape != None:
        boundaries_shape = args.boundaries_shape

    # Récupération de rayon du filtre majoritaire
    if args.radius != None:
        radius = args.radius

    # Récupération de la valeur à imposer
    if args.value_to_force != None:
        value_to_force = args.value_to_force

    # Paramettre des no data
    if args.no_data_value != None:
        no_data_value = args.no_data_value

    # Paramètre format des images de sortie
    if args.format_raster != None:
        format_raster = args.format_raster

    # Paramètre de l'extension des images rasters
    if args.extension_raster != None:
        extension_raster = args.extension_raster

    # Récupération du format des vecteurs de sortie
    if args.format_vector != None :
        format_vector = args.format_vector

    # Récupération du nom du fichier log
    if args.path_time_log!= None:
        path_time_log = args.path_time_log

    # Récupération de l'information de sauvegarde des fichiers intermédiaires
    if args.save_results_inter != None:
        save_results_inter = args.save_results_inter

    # Récupération de l'information d'ecrasement des fichiers existants
    if args.overwrite!= None:
        overwrite = args.overwrite

    # Récupération de l'option niveau de debug
    if args.debug!= None:
        global debug
        debug = args.debug

    # Affichage des arguments récupérés
    if debug >= 3:
        print(bold + green + "Variables dans le parser" + endC)
        print(cyan + "RasterAssembly : " + endC + "input_images_list : " + str(input_images_list) + endC)
        print(cyan + "RasterAssembly : " + endC + "output_image : " + str(output_image) + endC)
        print(cyan + "RasterAssembly : " + endC + "radius : " + str(radius) + endC)
        print(cyan + "RasterAssembly : " + endC + "boundaries_shape : " + str(boundaries_shape) + endC)
        print(cyan + "RasterAssembly : " + endC + "value_to_force : " + str(value_to_force) + endC)
        print(cyan + "RasterAssembly : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "RasterAssembly : " + endC + "format_raster : " + str(format_raster) + endC)
        print(cyan + "RasterAssembly : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "RasterAssembly : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "RasterAssembly : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "RasterAssembly : " + endC + "save_results_inter : " + str(save_results_inter) + endC)
        print(cyan + "RasterAssembly : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "RasterAssembly : " + endC + "debug : " + str(debug) + endC)

    # EXECUTION DE LA FONCTION
    # Si le dossier de sortie n'existe pas, on le crée
    if output_image != None:
        repertory_output = os.path.dirname(output_image)
        if not os.path.isdir(repertory_output):
            os.makedirs(repertory_output)

    # Assemblage
    rasterAssembly(input_images_list, output_image, radius, value_to_force, boundaries_shape, no_data_value, path_time_log, format_raster, format_vector, extension_raster, save_results_inter, overwrite)

# ================================================

if __name__ == '__main__':
  main(gui=False)
