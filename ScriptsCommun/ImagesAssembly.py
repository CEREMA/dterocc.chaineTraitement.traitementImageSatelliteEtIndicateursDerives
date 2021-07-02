#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerSO/DALETT/SCGSI  All rights reserved.                                                                            #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT DE RECHERCHE ET DE DECOUPAGE D'IMAGE RASTER SELON UN MASQUE VECTEUR                                                                #
#                                                                                                                                           #
#############################################################################################################################################

'''
Nom de l'objet : ImagesAssembly.py
Description    :
    Objectif   : Assemble et/ou découpe des images raster

Date de creation : 10/03/2014
----------
Histoire :
----------
Origine : le script originel provient du fichier script_ima_ass.py cree en 2014 scripts annexes
12/05:2014 : Bug nettoyage 0 numpy neutralisé temporairement
             Bug option découpe sur images ortho format ecw : La liste des fichiers de sortie se cree sur le model de la liste des fichiers selectionnés (contenu dans la zone d'intérêt)
             Résultat : on écrit bien des fichiers au format GTiff (commme demandé en entrée) mais avec une extension .ecw. Renomme ecw en GTiff rend le fichier lisible.
01/10/2014 : Transformation en brique elementaire (suppression des liens avec la chaine OCSOL)
-----------------------------------------------------------------------------------------------------
Modifications
01/10/2014 : refonte du fichier harmonisation des règles de qualité des niveaux de boucles et des paramétres dans args
------------------------------------------------------
A Reflechir/A faire
Dans la fonction cutOutImages créer un nom de fichier de sortie tel que si format_raster = GTiff alors extension fichier de sortie = .tif
'''

# Import des bibliothèques python
from __future__ import print_function
import os, sys, glob, copy, string, time, shutil, gdal, ogr, numpy, argparse
from os import chdir
from gdalconst import *
from Lib_log import timeLine
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_operator import getExtensionApplication
from Lib_vector import getEmpriseFile, createEmpriseShapeReduced
from Lib_raster import getPixelWidthXYImage, changeDataValueToOtherValue, getProjectionImage, updateReferenceProjection, roundPixelEmpriseSize, cutImageByVector
from Lib_file import removeVectorFile, removeFile
from Lib_text import appendTextFileCR

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 1

###########################################################################################################################################
# STRUCTURE StructZoneDate                                                                                                                #
###########################################################################################################################################
# Structure contenant une date, une liste de fichier images, et les coordonnees de l'emprise des fichiers images
class StructZoneDate:
    def __init__(self):
        self.date = ''
        self.images_list = []
        self.xmin = 0.0
        self.ymax = 0.0
        self.xmax = 0.0
        self.ymin = 0.0

###########################################################################################################################################
# FONCTION selectAssembyImagesByHold                                                                                                      #
###########################################################################################################################################
# ROLE:
#    Sectionner et Assembler des images raster selon un fichier masque vecteur
#
# ENTREES DE LA FONCTION :
#    emprise_vector : Fichier format shape (.shp) de l'emprise
#    input_repertories_list : Répertoire(s) des fichiers raw (.tif, .ecw, .jp2, .asc) images d'entrées
#    output_file, Fichier image de sortie (.tif) découpé à l'emprise ou répertoire résultat
#    is_not_assembled : Option : Les images contenues dans l'emprise sont découpées mais pas assemblées
#    is_zone_date : Option : Les images sont assemblées par zone de même date de prise de vue, une image resultat par date
#    epsg : Option : Type de projection (EPSG) de l'image de sortie par défaut la même projection que les images d'entrées
#    is_vrtfile : Option : Création d'un fichier VRT pour chaque image assemblée contenant les coordonnées des images sources
#    is_band_stack : Option : Création d'un fichier final concatenation de toutes les couches des images assemblées en un seul fichier
#    is_clean_zero : Option : Nettoyage des pixels à zéro des images (dalles) d'entrées
#    is_clean_zero_output : Option : Nettoyage des pixels à zéro des images de sorties assemblées
#    clean_zero_value : pour les parametres is_clean_zero et is_clean_zero_output valeur de remplacement des pixels à zero
#    pixel_size_x : Option : Define size pixel X of output image
#    pixel_size_y : Option : Define size pixel Y of output image
#    no_data_value : Option : Value pixel of no data
#    separ_name : Paramètre date acquisition dans le nom, séparateur d'information
#    pos_date : Paramètre date acquisition dans le nom, position relatif au séparateur d'information
#    nb_char_date : Paramètre date acquisition dans le nom, nombre de caractères constituant la date
#    separ_date : Paramètre date acquisition dans le nom, séparateur dans l'information date
#    path_time_log : le fichier de log de sortie
#    file_out_suffix_error : suffix fichier error, par default : "_error"
#    file_out_suffix_merge : suffix fichier merge, par default : "_merge"
#    file_out_suffix_clean : suffix fichier clean, par default : "_clean"
#    file_out_suffix_stack : suffix fichier stack, par default : "_stack"
#    format_raster : Format de l'image de sortie par défaut GTiff (GTiff, HFA...)
#    format_vector : format du fichier vecteur. Optionnel, par default : 'ESRI Shapefile'
#    extension_raster : extension des fichiers raster de sortie, par defaut = '.tif'
#    extension_vector : extension du fichier vecteur de sortie, par defaut = '.shp'
#    save_results_intermediate : fichiers de sorties intermediaires non nettoyees, par defaut = False
#    overwrite : supprime ou non les fichiers existants ayant le meme nom
#
# SORTIES DE LA FONCTION :
#    Le(s) fichier(s) image assemblé(s)
#    Eléments modifiés auccun

def selectAssembyImagesByHold(emprise_vector, input_repertories_list, output_file, is_not_assembled, is_zone_date, epsg, is_vrtfile, is_band_stack, is_clean_zero, is_clean_zero_output, clean_zero_value, pixel_size_x, pixel_size_y, no_data_value, separ_name, pos_date, nb_char_date, separ_date, path_time_log, file_out_suffix_error="_error", file_out_suffix_merge="_merge", file_out_suffix_clean="_clean", file_out_suffix_stack="_stack", format_raster='GTiff', format_vector='ESRI Shapefile', extension_raster=".tif", extension_vector=".shp", save_results_intermediate=False, overwrite=True):

    # Affichage des paramètres
    if debug >= 3:
        print(bold + green + "Variables dans le selectAssembyImagesByHold - Variables générales" + endC)
        print(cyan + "selectAssembyImagesByHold() : " + endC + "emprise_vector : " + str(emprise_vector))
        print(cyan + "selectAssembyImagesByHold() : " + endC + "input_repertories_list : " + str(input_repertories_list))
        print(cyan + "selectAssembyImagesByHold() : " + endC + "output_file : " + str(output_file))
        print(cyan + "selectAssembyImagesByHold() : " + endC + "is_not_assembled : " + str(is_not_assembled))
        print(cyan + "selectAssembyImagesByHold() : " + endC + "is_zone_date : " + str(is_zone_date))
        print(cyan + "selectAssembyImagesByHold() : " + endC + "epsg : " + str(epsg))
        print(cyan + "selectAssembyImagesByHold() : " + endC + "is_vrtfile : " + str(is_vrtfile))
        print(cyan + "selectAssembyImagesByHold() : " + endC + "is_band_stack : " + str(is_band_stack))
        print(cyan + "selectAssembyImagesByHold() : " + endC + "is_clean_zero : " + str(is_clean_zero))
        print(cyan + "selectAssembyImagesByHold() : " + endC + "clean_zero_value : " + str(clean_zero_value))
        print(cyan + "selectAssembyImagesByHold() : " + endC + "pixel_size_x : " + str(pixel_size_x))
        print(cyan + "selectAssembyImagesByHold() : " + endC + "pixel_size_y : " + str(pixel_size_y))
        print(cyan + "selectAssembyImagesByHold() : " + endC + "no_data_value : " + str(no_data_value))
        print(cyan + "selectAssembyImagesByHold() : " + endC + "separ_name : " + str(separ_name))
        print(cyan + "selectAssembyImagesByHold() : " + endC + "pos_date : " + str(pos_date))
        print(cyan + "selectAssembyImagesByHold() : " + endC + "nb_char_date : " + str(nb_char_date))
        print(cyan + "selectAssembyImagesByHold() : " + endC + "separ_date : " + str(separ_date))
        print(cyan + "selectAssembyImagesByHold() : " + endC + "path_time_log : " + str(path_time_log))
        print(cyan + "selectAssembyImagesByHold() : " + endC + "file_out_suffix_error : " + str(file_out_suffix_error))
        print(cyan + "selectAssembyImagesByHold() : " + endC + "file_out_suffix_merge : " + str(file_out_suffix_merge))
        print(cyan + "selectAssembyImagesByHold() : " + endC + "file_out_suffix_clean : " + str(file_out_suffix_clean))
        print(cyan + "selectAssembyImagesByHold() : " + endC + "file_out_suffix_stack : " + str(file_out_suffix_stack))
        print(cyan + "selectAssembyImagesByHold() : " + endC + "format_raster : " + str(format_raster))
        print(cyan + "selectAssembyImagesByHold() : " + endC + "format_vector : " + str(format_vector))
        print(cyan + "selectAssembyImagesByHold() : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "selectAssembyImagesByHold() : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "selectAssembyImagesByHold() : " + endC + "save_results_intermediate : " + str(save_results_intermediate))
        print(cyan + "selectAssembyImagesByHold() : " + endC + "overwrite : " + str(overwrite))

    # Constante
    EXT_VRT = ".vrt"
    EXT_LOG = ".log"
    EXT_TEXT = ".txt"

    # Mise à jour du Log
    starting_event = "selectAssembyImagesByHold() : Select assembly images starting : "
    timeLine(path_time_log,starting_event)

    # Variables
    table_images_list = {}
    image_outputs_list = []
    images_error_list = []
    pos_date = pos_date - 1

    # output_file, output_rep
    if os.path.isdir(output_file) :
        output_rep = output_file
        output_file = output_rep + os.sep + "imageRes" + extension_raster
    else :
        output_rep = os.path.dirname(output_file)

    #------------------------------------------------
    # Emprise de la zone selectionnée
    empr_xmin,empr_xmax,empr_ymin,empr_ymax = getEmpriseFile(emprise_vector, format_vector)

    if debug >= 3:
        pos_xmin_km = int(round(empr_xmin/1000.0))
        pos_xmax_km = int(round(empr_xmax/1000.0 + 1))
        pos_ymin_km = int(round(empr_ymin/1000.0))
        pos_ymax_km = int(round(empr_ymax/1000.0 + 1))
        print(bold + green + "Variables dans le selectAssembyImagesByHold - Emprise de la zone selectionnée" + endC)
        print(cyan + "selectAssembyImagesByHold() : " + endC + "Emprise de la zone :")
        print(cyan + "selectAssembyImagesByHold() : " + endC + 'UL:', pos_xmin_km, pos_ymax_km)
        print(cyan + "selectAssembyImagesByHold() : " + endC + 'LR:', pos_xmax_km, pos_ymin_km)

    #-----------------------------------------------
    # Recherche dans tous les répertoires les images correspondant à l'emprise
    if debug >= 4:
         print(cyan + "selectAssembyImagesByHold : " + endC + "table_images_list : " + str(table_images_list) + endC)

    for repertory in input_repertories_list:
        selectImagesFile(table_images_list, images_error_list, repertory, empr_xmin, empr_xmax, empr_ymin, empr_ymax, is_zone_date, separ_name, pos_date, nb_char_date, separ_date)

    if debug >= 4:
         print(cyan + "selectAssembyImagesByHold : " + endC + "table_images_list : " + str(table_images_list) + endC)

    #-----------------------------------------------
    # Liste des images en erreur
    repertory_output = os.path.dirname(output_file)
    file_name = os.path.splitext(os.path.basename(output_file))[0]
    filename_trace_error = repertory_output + os.sep + file_name + file_out_suffix_error + EXT_LOG

    if len(images_error_list) > 0 :
        file_trace_error = open(filename_trace_error,"w")
        cpt_ima = 0
        for image_error in images_error_list:
            cpt_ima +=1
            print(image_error)
            file_trace_error.write(image_error+"\n")
        file_trace_error.close()

        print(cyan + "selectAssembyImagesByHold() : " + bold + red + "Nombre total d'images erronées : " + str(cpt_ima) + endC, file=sys.stderr)

    #-----------------------------------------------
    if debug >= 4:
        print("Liste des fichiers image selectionnés :")

    cpt_ima = 0
    for acquisition_date in table_images_list:

        s_zone_date = table_images_list[acquisition_date]

        if debug >= 4:
            print(cyan + "selectAssembyImagesByHold() : " + endC + "acquisition_date : " + str(acquisition_date))
            print(cyan + "selectAssembyImagesByHold() : " + endC + "table_images_list : " + str(table_images_list))

        for imagefile in s_zone_date.images_list:
            cpt_ima +=1
            if debug >= 4:
                print(cyan + "selectAssembyImagesByHold() : " + endC + "imagefile : " + imagefile)

    print(cyan + "selectAssembyImagesByHold() : Nombre total d'images trouvées total : " + str(cpt_ima) + endC)

    #-----------------------------------------------
    # Si la resolution de l'image de sortie n'est pas spécifié prendre la résolution de la 1ere image
    if pixel_size_x == 0 or pixel_size_y == 0 :
        if table_images_list != {} and table_images_list.keys() != []:
            #datePriseDeVue  = table_images_list.keys()[0]
            datePriseDeVue  = list(table_images_list)[0]
            s_zone_date = table_images_list.get(datePriseDeVue)
            imagefile = s_zone_date.images_list[0]
            if os.path.isfile(imagefile) :
                pixel_size_x, pixel_size_y = getPixelWidthXYImage(imagefile)
        else :
            raise NameError (bold + red + "!!! Fin de l'application auccune images disponibles dans cette emprise " + endC)

    #-----------------------------------------------
    if is_not_assembled :
        # Cas avec decoupe de chaque images par l'emprise individuellement sans assemblage
        for acquisition_date in table_images_list:
            s_zone_date = table_images_list[acquisition_date]
            cutOutImages(s_zone_date.images_list, empr_xmin, empr_xmax, empr_ymin, empr_ymax, emprise_vector, output_rep, pixel_size_x, pixel_size_y, file_out_suffix_clean, is_clean_zero, clean_zero_value, no_data_value, epsg, format_raster, format_vector, extension_vector, save_results_intermediate)

        print(bold + blue + "Les fichiers images ont été découpés" + endC)
    else :
        # Cas avec assemblage des images contenues dans l'emprise et decoupe selon l'emprise pour chaque date d'aquisition
        for acquisition_date in table_images_list:

            s_zone_date = table_images_list[acquisition_date]

            if debug >= 4:
                print(cyan + "selectAssembyImagesByHold : " + endC + "table_images_list : " + str(table_images_list) + endC)
                print(cyan + "selectAssembyImagesByHold : " + endC + "s_zone_date : " + str(s_zone_date) + endC)

            repertory_output = os.path.dirname(output_file)
            file_name = os.path.splitext(os.path.basename(output_file))[0]
            extension = os.path.splitext(output_file)[1]
            if acquisition_date :
                acquisition_date = '_' + acquisition_date
            image_output = repertory_output + os.sep + file_name + acquisition_date + extension
            image_outputs_list.append(image_output)

            # Option vrt file
            if is_vrtfile :
                repertory_output = os.path.dirname(output_file)
                file_name = os.path.splitext(os.path.basename(output_file))[0]
                vrt_file_output = repertory_output + os.sep + file_name + EXT_VRT
                vrtImages(s_zone_date.images_list, empr_xmin, empr_xmax, empr_ymin, empr_ymax, vrt_file_output)
                print(bold + blue + "Le fichier vrt à été crée : " + vrt_file_output + endC)

            # Creation d'un nouveau shape d'emprise corespondant a la zone réelle des images selectionnées pour la date
            if debug >= 4:
                print(cyan + "selectAssembyImagesByHold : " + endC + "s_zone_date.xmin : " + str(s_zone_date.xmin) + endC)
                print(cyan + "selectAssembyImagesByHold : " + endC + "s_zone_date.ymin : " + str(s_zone_date.ymin) + endC)
                print(cyan + "selectAssembyImagesByHold : " + endC + "s_zone_date.xmax : " + str(s_zone_date.xmax) + endC)
                print(cyan + "selectAssembyImagesByHold : " + endC + "s_zone_date.ymax : " + str(s_zone_date.ymax) + endC)

            repertory_output = os.path.dirname(image_output)
            file_name = os.path.splitext(os.path.basename(image_output))[0]
            base_file = repertory_output + os.sep + file_name
            emprise_shape_date = base_file + extension_vector
            createEmpriseShapeReduced(emprise_vector, s_zone_date.xmin, s_zone_date.ymin, s_zone_date.xmax, s_zone_date.ymax, emprise_shape_date, format_vector)

            # Nettoyage des images d'entree des pixels à 0
            images_list = []
            if is_clean_zero :
                if debug >= 2:
                    print(cyan + "selectAssembyImagesByHold() : Début du nettoyage des pixels à 0" + endC)
                for image_file_tmp in s_zone_date.images_list :

                    file_name = os.path.splitext(os.path.basename(image_file_tmp))[0]
                    extension = os.path.splitext(image_file_tmp)[1]
                    clean_file_tmp = output_rep + os.sep + file_name + file_out_suffix_clean + extension_raster
                    changeDataValueToOtherValue(image_file_tmp, clean_file_tmp, 0, clean_zero_value, format_raster)
                    images_list.append(clean_file_tmp)

                if debug >= 2:
                    print(cyan + "selectAssembyImagesByHold() : Fin du nettoyage des pixels à 0 des images d'entree" + endC)

            else :
                if debug >= 2:
                    print(cyan + "selectAssembyImagesByHold() : Pas de nettoyage des pixels à 0 des images d'entree" + endC)
                images_list = s_zone_date.images_list

            # Assemblage des images
            if debug >= 2:
                    print(cyan + "selectAssembyImagesByHold() : Debut de l'assemblage des %s images de la liste : " %(str(len(images_list))) + endC + "%s" %(images_list) + endC)

            assemblyImages(images_list, emprise_shape_date, image_output, pixel_size_x, pixel_size_y, file_out_suffix_merge, file_out_suffix_clean, no_data_value, epsg, format_raster, format_vector, EXT_TEXT, save_results_intermediate)

            if debug >= 2:
                    print(cyan + "selectAssembyImagesByHold() : Fin de l'assemblage des images. Image crée : " + endC + "%s" %(image_output) + endC)

            # Supression des fichiers temporaires
            if is_clean_zero :
                for image_file_tmp in images_list :
                    if os.path.exists(image_file_tmp):
                        removeFile(image_file_tmp)


            # Nettoyage de l'image de sorties des pixels à 0
            if is_clean_zero_output :
                if debug >= 2:
                    print(cyan + "selectAssembyImagesByHold() : Début du nettoyage des pixels à 0 de l'image de sortie" + endC)

                # Creation d'un nom de fichier temporaire
                repertory_output = os.path.dirname(image_output)
                file_name = os.path.splitext(os.path.basename(image_output))[0]
                extension = os.path.splitext(image_output)[1]
                suffix_origine = "_orig"
                suffix_temp = "_temp"

                # Remplacement des pixels à 0 par des pixels à une valeur approchée
                file_name = os.path.splitext(os.path.basename(image_output))[0]
                extension = os.path.splitext(image_output)[1]
                output_file_tmp = repertory_output + os.sep + file_name + file_out_suffix_clean + extension
                changeDataValueToOtherValue(image_output, output_file_tmp, 0, clean_zero_value, format_raster)

                # Renomage des fichiers source et resultat
                image_output_suffix_orig = repertory_output + os.sep + file_name + suffix_origine + extension
                os.rename(image_output, image_output_suffix_orig)
                os.rename(output_file_tmp, image_output)

                if debug >= 2:
                    print(cyan + "selectAssembyImagesByHold() : Fin du nettoyage des pixels à 0 de l'image de sortie" + endC)

            else :
                if debug >= 2:
                    print(cyan + "selectAssembyImagesByHold() : Pas de nettoyage des pixels à 0 de l'image de sortie" + endC)
                images_list = s_zone_date.images_list

        # Option creation d'un fichier résultat multi couche avec les résultats des différentes dates
        if is_band_stack and len(table_images_list) > 1 :

            if debug >= 2:
                print(cyan + "selectAssembyImagesByHold() : " + bold + green + "Création du fichier résultat multicouche avec différentes dates" + endC)

            # Creation du fichier multi couche
            repertory_output = os.path.dirname(image_file)
            file_name = os.path.splitext(os.path.basename(image_file))[0]
            extension = os.path.splitext(image_file)[1]
            stack_file_output = repertory_output + os.sep + file_name + file_out_suffix_stack + extension
            stackImagesDates(image_outputs_list, pixel_size_x, pixel_size_y, stack_file_output, file_out_suffix_merge, no_data_value, format_raster, EXT_TEXT, save_results_intermediate)

            if debug >= 2:
                print(cyan + "selectAssembyImagesByHold() : " + bold + green + "Fin de la création du fichier stacké. Disponible ici : " + endC + stack_file_output + endC)

        else :
            if debug >= 2:
                print(cyan + "selectAssembyImagesByHold() : " + bold + green + "Pas de fichier résultat multicouche avec les différentes dates demandées" + endC)

    # Mise à jour du Log
    ending_event = "selectAssembyImagesByHold() : Select assembly images ending : "
    timeLine(path_time_log,ending_event)

    return

###########################################################################################################################################
# FONCTION selectImagesFile()                                                                                                             #
###########################################################################################################################################
# ROLE:
#     Rechercher dans un repetoire toutes les images qui sont contenues ou qui intersectes l'emprise
#
# ENTREES DE LA FONCTION :
#    table_images_list : Liste des images selectionnées
#    images_error_list : Liste des images en erreur
#    repertory    : Repertoire de recherche
#    empr_xmin    : L'emprise coordonnée xmin
#    empr_xmax    : L'emprise coordonnée xmax
#    empr_ymin    : L'emprise coordonnée ymin
#    empr_ymax    : L'emprise coordonnée ymax
#    is_zone_date : Si vrai, les images sont assemblées par zone de même date de prise de vue
#    separ_name   : Paramètre date acquisition dans le nom, séparateur d'information
#    pos_date     : Paramètre date acquisition dans le nom, position relatif au séparateur d'information
#    nb_char_date : Paramètre date acquisition dans le nom, nombre de caractères constituant la date
#    separ_date   : Paramètre date acquisition dans le nom, séparateur dans l'information date
#
# SORTIES DE LA FONCTION :
#    La liste des images selectionnées dans l'emprise
#    La liste des images en erreur
#
def selectImagesFile(table_images_list, images_error_list, repertory, empr_xmin, empr_xmax, empr_ymin, empr_ymax, is_zone_date, separ_name, pos_date, nb_char_date, separ_date):

    if debug >= 3:
        print(cyan + "selectImagesFile() : Début de la sélection des dossiers images" + endC)

    if debug >= 5:
        print(cyan + "selectImagesFile : " + endC + "empr_xmin : " + str(empr_xmin) + endC)
        print(cyan + "selectImagesFile : " + endC + "empr_xmax : " + str(empr_xmax) + endC)
        print(cyan + "selectImagesFile : " + endC + "empr_ymin : " + str(empr_ymin) + endC)
        print(cyan + "selectImagesFile : " + endC + "empr_ymax : " + str(empr_ymax) + endC)

    EXT_LIST = ['tif','TIF','tiff','TIFF','ecw','ECW','jp2','JP2','asc','ASC']

    for imagefile in glob.glob(repertory + os.sep + '*.*'):
        ok = True
        if imagefile.rsplit('.',1)[1] in EXT_LIST :
            try:
                dataset = gdal.Open(imagefile, GA_ReadOnly)
            except RuntimeError:
                print(cyan + "selectImagesFile : " + bold + red + "Erreur Impossible d'ouvrir le fichier : " + imagefile, file=sys.stderr)
                images_error_list.append(imagefile)
                ok = False
            if ok and dataset is None :
                images_error_list.append(imagefile)
                ok = False
            if ok :
                cols = dataset.RasterXSize
                rows = dataset.RasterYSize
                bands = dataset.RasterCount

                geotransform = dataset.GetGeoTransform()
                pixel_width = geotransform[1]  # w-e pixel resolution
                pixel_height = geotransform[5] # n-s pixel resolution

                imag_xmin = geotransform[0]     # top left x
                imag_ymax = geotransform[3]     # top left y
                imag_xmax = imag_xmin + (cols * pixel_width)
                imag_ymin = imag_ymax + (rows * pixel_height)

                if debug >= 5:
                    print(cyan + "selectImagesFile : " + endC + "imag_xmin : " + str(imag_xmin) + endC)
                    print(cyan + "selectImagesFile : " + endC + "imag_ymax : " + str(imag_ymax) + endC)
                    print(cyan + "selectImagesFile : " + endC + "imag_xmax : " + str(imag_xmax) + endC)
                    print(cyan + "selectImagesFile : " + endC + "imag_ymin : " + str(imag_ymin) + endC)


                # Si l'image et l'emprise sont complement disjointe l'image n'est pas selectionée
                if not ((imag_xmin > empr_xmax) or (imag_xmax < empr_xmin) or (imag_ymin > empr_ymax) or (imag_ymax < empr_ymin)) :

                    datePriseDeVue = ""
                    # Cas ou l'on attend des zones fusionées par date
                    if is_zone_date :
                       metaData = dataset.GetMetadata()
                       fileTest = os.path.basename(imagefile)
                       extension = fileTest.split('.')[1]

                       # Fichiers tif
                       if extension.lower() == 'tif' or extension.lower() == 'tiff' :
                           # tag TIFFTAG_DATETIME pour .tif format "YYYY:MM:DD HH:MM:SS"
                           if 'TIFFTAG_DATETIME' in metaData :
                               infoTag = metaData['TIFFTAG_DATETIME']
                               datePriseDeVue = infoTag.split(' ')[0].replace(":","")

                       # Fichiers ecw
                       elif extension.lower() == 'ecw' :
                           # tag FILE_METADATA_ACQUISITION_DATE pour .ecw format "YYYY-MM-DD"
                           if extension.lower() == 'ecw' and 'FILE_METADATA_ACQUISITION_DATE' in metaData :
                               infoTag = metaData['FILE_METADATA_ACQUISITION_DATE']
                               datePriseDeVue = infoTag.replace("-","")

                       # Fichiers jp2
                       elif extension.lower() == 'jp2':
                           datePriseDeVue == ""

                       # Fichiers asc
                       elif extension.lower() == 'asc':
                           datePriseDeVue == ""

                       # Cas ou les metadata ne sont pas renseignés recherche de la date d'acquisition dans le nom du fichier avec valeurs de la postion passés en paramètres
                       if datePriseDeVue == "" :
                           filename = os.path.basename(imagefile)
                           print(cyan + "selectImagesFile : " + endC + "filename : " + str(filename) + endC)
                           infoDate = filename.split(separ_name)[pos_date]
                           datePriseDeVue = infoDate[:nb_char_date]
                           datePriseDeVue = datePriseDeVue.replace(separ_date,"")

                       if debug >= 4:
                           print(cyan + "selectImagesFile : " + endC + "infoDate : " + str(infoDate) + endC)
                           print(cyan + "selectImagesFile : " + endC + "datePriseDeVue : " + str(datePriseDeVue) + endC)
                           print(cyan + "selectImagesFile : " + endC + "table_images_list : " + str(table_images_list) + endC)

                    # Vérifier dans la hastable si la key correspondante existe sinon creer une nouvelle key
                    if datePriseDeVue not in table_images_list :
                        s_zone_date = StructZoneDate()
                        s_zone_date.date = datePriseDeVue
                        s_zone_date.images_list = []
                        s_zone_date.xmin = 999999999999999.0
                        s_zone_date.ymax = 0.0
                        s_zone_date.xmax = 0.0
                        s_zone_date.ymin = 999999999999999.0
                        table_images_list[datePriseDeVue] = s_zone_date

                        if debug >= 4:
                            print(cyan + "selectImagesFile : " + endC + "s_zone_date.date : " + str(s_zone_date.date) + endC)

                    if debug >= 4:
                        print(cyan + "selectImagesFile : " + endC + "table_images_list : " + str(table_images_list) + endC)

                    # Récuperer dans la hastable la liste d'image correspondant à la date et mettre a jour l'information
                    s_zone_date = table_images_list.get(datePriseDeVue)
                    s_zone_date.images_list.append(imagefile)

                    if imag_xmin < s_zone_date.xmin :
                        s_zone_date.xmin = imag_xmin
                    if imag_ymin < s_zone_date.ymin:
                        s_zone_date.ymin = imag_ymin
                    if imag_xmax > s_zone_date.xmax :
                        s_zone_date.xmax = imag_xmax
                    if imag_ymax > s_zone_date.ymax:
                        s_zone_date.ymax = imag_ymax
                    newSZoneDate = {datePriseDeVue : s_zone_date}
                    table_images_list.update(newSZoneDate)

    if debug >= 3:
        print(cyan + "selectImagesFile : Fin de la sélection des dossiers images" + endC)

    return

###########################################################################################################################################
# FONCTION assemblyImages()                                                                                                               #
###########################################################################################################################################
# ROLE:
#     Assembler une liste d'image selectionnées
#
# ENTREES DE LA FONCTION :
#    images_list : Liste des images à fusionnées
#    empr_file    : Vecteur de découpe de l'image fusionnée
#    output_file  : L'image de sortie fusionnée et découpé
#    pixel_size_x : Taille du pixel en x (en m)
#    pixel_size_y : Taille du pixel en y (en m)
#    file_out_suffix_merge : suffix fichier merge
#    file_out_suffix_clean : suffix fichier clean
#    no_data_value: La valeur du no data de l'image de sortie
#    epsg   : L'EPSG de projection demandé pour l'image de sortie
#    format_raster   : Format de l'image de sortie (GTiff, HFA...)
#    format_vector  : format du vecteur de sortie, par defaut = 'ESRI Shapefile'
#    ext_txt : extension du fichier texte contenant la liste des fichiers a merger
#    save_results_intermediate : Si faux suppresion des fichiers temporaires
#
# SORTIES DE LA FONCTION :
#    L'image fusionnée et découpé
#
def assemblyImages(images_list, empr_file, output_file, pixel_size_x, pixel_size_y, file_out_suffix_merge, file_out_suffix_clean, no_data_value, epsg, format_raster, format_vector, ext_txt, save_results_intermediate):

    if debug >= 3:
        print(cyan + "assemblyImages : Début de l'assemblage des images" + endC)

    # Fichier temporaire mergé
    repertory_output = os.path.dirname(output_file)
    file_name = os.path.splitext(os.path.basename(output_file))[0]
    extension = os.path.splitext(output_file)[1]
    merge_file_tmp = repertory_output + os.sep + file_name + file_out_suffix_merge + extension

    if os.path.exists(merge_file_tmp):
        removeFile(merge_file_tmp)

    if os.path.exists(output_file):
        removeFile(output_file)

    # Fichier txt temporaire liste des fichiers a merger
    list_file_tmp = repertory_output + os.sep + file_name + file_out_suffix_merge + ext_txt
    for imagefile in images_list:
        appendTextFileCR(list_file_tmp, imagefile)

    # Utilisation de la commande gdal_merge pour fusioner les fichiers image source
    # Pour les parties couvertes par plusieurs images, l'image retenue sera la dernière mergée

    cmd_merge = "gdal_merge" + getExtensionApplication() + " -of " + format_raster + " -ps " + str(pixel_size_x) + " " + str(pixel_size_y) + " -n " + str(no_data_value) + " -o "  + merge_file_tmp + " --optfile " + list_file_tmp
    print(cmd_merge)
    exit_code = os.system(cmd_merge)
    if exit_code != 0:
        raise NameError (bold + red + "!!! Une erreur c'est produite au cours du merge des images. Voir message d'erreur."  + endC)

    if debug >= 3:
        print(cyan + "assemblyImages : Fin de l'assemblage des images" + endC)
        print(cyan + "assemblyImages : Début du découpage de l'image assemblée " + endC)

    # Si le fichier de sortie mergé a perdu sa projection on force la projection à la valeur par defaut
    if getProjectionImage(merge_file_tmp) == None or getProjectionImage(merge_file_tmp) == 0:
        if epsg != 0 :
            updateReferenceProjection(None, merge_file_tmp, int(epsg))
        else :
            raise NameError (bold + red + "!!! Erreur les fichiers images d'entrée non pas de projection défini et vous n'avez pas défini de projection (EPSG) en parametre d'entrée."  + endC)

    # Utilisation de la lib_raster pour recouper le fichier image mergé selon l'emprise
    if os.path.exists(merge_file_tmp):
        # Appel à la fonction cutImageByVector pour le découpage du raster
        if not cutImageByVector(empr_file, merge_file_tmp, output_file, pixel_size_x, pixel_size_y, no_data_value, epsg, format_raster, format_vector) :
            print(cyan + "assemblyImages : " + bold + red + "!!! Une erreur c'est produite au cours du découpage de l'image assemblée : " + output_file + ". Voir message d'erreur." + endC, file=sys.stderr)

    else :
        print(cyan + "assemblyImages : " + bold + red + "Il n'y a pas d'image comprise dans l'emprise"  + endC, file=sys.stderr)
        sys.exit(0)

    if debug >= 3:
        print(cyan + "assemblyImages : Fin du découpage de l'image assemblée" + endC)

    # Supression des fichiers temporaires
    if not save_results_intermediate:
        if os.path.exists(merge_file_tmp):
            removeFile(merge_file_tmp)
        if os.path.exists(list_file_tmp):
            removeFile(list_file_tmp)
    return

###########################################################################################################################################
# FONCTION cutOutImages()                                                                                                                 #
###########################################################################################################################################
# ROLE:
#     Découper une liste d'image selon une emprise sans les fusionnées
#
# ENTREES DE LA FONCTION :
#    images_list : Liste des images à decoupées selon l'emprise
#    empr_xmin    : L'emprise coordonnée xmin
#    empr_xmax    : L'emprise coordonnée xmax
#    empr_ymin    : L'emprise coordonnée ymin
#    empr_ymax    : L'emprise coordonnée ymax
#    empr_file   : Le vecteur de decoupe
#    output_rep   : Repertoire contenant les images de sorties
#    pixel_size_x : Taille du pixel en x (en m)
#    pixel_size_y : Taille du pixel en y (en m)
#    file_out_suffix_clean : suffix fichier clean
#    is_clean_zero : Si vrai, nettoyage des pixels à zéro des images, remplacer par clean_zero_value
#    clean_zero_value : pour l'option is_clean_zero valeur de remplacement des 0
#    no_data_value: La valeur du no data de l'image de sortie
#    epsg   : L'EPSG de projection demandé pour les images de sortie
#    format_raster   : Format de l'image de sortie (GTiff, HFA...)
#    format_vector : Format des fichiers vecteurs
#    extension_vector : Extension du fichier vecteur
#    save_results_intermediate : Si faux suppresion des fichiers temporaires
#
# SORTIES DE LA FONCTION :
#    Une liste d'image découpées
#
def cutOutImages(images_list, empr_xmin, empr_xmax, empr_ymin, empr_ymax, empr_file, output_rep, pixel_size_x, pixel_size_y, file_out_suffix_clean, is_clean_zero, clean_zero_value, no_data_value, epsg, format_raster, format_vector, extension_vector, save_results_intermediate):

    if debug >= 3:
        print(cyan + "cutOutImages : Cas où les images sont decoupées selon l'emprise mais pas assemblées" + endC)

    # Calculer l'arrondi pour l'emprise
    round_empr_xmin, round_empr_xmax, round_empr_ymin, round_empr_ymax = roundPixelEmpriseSize(pixel_size_x, pixel_size_y, empr_xmin, empr_xmax, empr_ymin, empr_ymax)

    if debug >= 5:
        print(cyan + "cutOutImages : " + endC + "round_empr_xmin : " + str(round_empr_xmin) + endC)
        print(cyan + "cutOutImages : " + endC + "round_empr_xmax : " + str(round_empr_xmax) + endC)
        print(cyan + "cutOutImages : " + endC + "round_empr_ymin : " + str(round_empr_ymin) + endC)
        print(cyan + "cutOutImages : " + endC + "round_empr_ymax : " + str(round_empr_ymax) + endC)

    # Récuperation du  driver pour le format shape
    driver = ogr.GetDriverByName(format_vector)

    # Pour toutes les images à découper
    for imagefile in images_list:
        outputFileName = os.path.basename(imagefile)
        output_file = output_rep + os.sep + outputFileName
        if os.path.exists(output_file):
            removeFile(output_file)

        # L'emprise de l'image à découper
        dataset = gdal.Open(imagefile, GA_ReadOnly)
        cols = dataset.RasterXSize
        rows = dataset.RasterYSize
        bands = dataset.RasterCount
        geotransform = dataset.GetGeoTransform()
        pixel_width = geotransform[1]
        pixel_height = geotransform[5]

        imag_xmin = geotransform[0]
        imag_ymax = geotransform[3]
        imag_xmax = imag_xmin + (cols * pixel_width)
        imag_ymin = imag_ymax + (rows * pixel_height)

        if debug >= 5:
            print(cyan + "cutOutImages : " + endC + "imag_xmin : " + str(imag_xmin) + endC)
            print(cyan + "cutOutImages : " + endC + "imag_xmax : " + str(imag_xmax) + endC)
            print(cyan + "cutOutImages : " + endC + "imag_ymin : " + str(imag_ymin) + endC)
            print(cyan + "cutOutImages : " + endC + "imag_ymax : " + str(imag_ymax) + endC)

        if (imag_xmin >= round_empr_xmax) or (imag_xmax <= round_empr_xmin) or (imag_ymin >= round_empr_ymax) or (imag_ymax <= round_empr_ymin) :
            print(bold + yellow + "L'image " + imagefile + " est en dehors de l'emprise." + endC)
        else :

            xmin = imag_xmin
            xmax = imag_xmax
            ymin = imag_ymin
            ymax = imag_ymax

            if (imag_xmin < round_empr_xmin) :
                xmin = round_empr_xmin
            if (imag_xmax > round_empr_xmax) :
                xmax = round_empr_xmax
            if (imag_ymin < round_empr_ymin) :
                ymin = round_empr_ymin
            if (imag_ymax > round_empr_ymax) :
                ymax = round_empr_ymax

            if debug >= 5:
                print(cyan + "cutOutImages : " + endC + "xmin : " + str(xmin) + endC)
                print(cyan + "cutOutImages : " + endC + "xmax : " + str(xmax) + endC)
                print(cyan + "cutOutImages : " + endC + "ymin : " + str(ymin) + endC)
                print(cyan + "cutOutImages : " + endC + "ymax : " + str(ymax) + endC)

            # Creation d'un fichier shape d'emprise pour l'image local
            repertory_output = os.path.dirname(imagefile)
            file_name = os.path.splitext(os.path.basename(imagefile))[0]
            base_file = repertory_output + os.sep + file_name
            local_emprise_shape = base_file + extension_vector
            createEmpriseShapeReduced(empr_file, xmin, ymin, xmax, ymax, local_emprise_shape, format_vector)

            # Test si un shape non vide existe
            data_source = driver.Open(local_emprise_shape, 0)
            if data_source is None:
                print(cyan + "cutOutImages : " + bold + red + "Impossible d'ouvrir le fichier d'emprise : " + empr_file  + endC, file=sys.stderr)
                sys.exit(1) #exit with an error code

            # Récuperation des couches de données
            layer = data_source.GetLayer(0)
            num_features = layer.GetFeatureCount()
            data_source.Destroy()

            if is_clean_zero :
                # Nettoyage de l'image des pixels à 0
                file_name = os.path.splitext(os.path.basename(image_file))[0]
                extension = os.path.splitext(image_file)[1]
                clean_file_output = repertory_output + os.sep + file_name + file_out_suffix_clean + extension
                changeDataValueToOtherValue(imagefile, ima_file_output, 0, clean_zero_value, format_raster)

            else :
                clean_file_output = imagefile

            if num_features > 0 :
                # Utilisation de la fonction cutImageByVector pour recouper les images d'entrées selon l'emprise de travail
                if not cutImageByVector(local_emprise_shape, clean_file_output, output_file, pixel_size_x, pixel_size_y, no_data_value, epsg, format_raster, format_vector) :
                    raise NameError (bold + red +"!!! Une erreur c'est produite au cours du decoupage d'une image d'entrée : " + imagefile + ". Voir message d'erreur." + endC)

            # Suppresion du fichier d'emprise local
            if not save_results_intermediate:
                removeVectorFile(local_shape_file)

    if debug >= 3:
        print(cyan + "cutOutImages : Fin de la gestion du cas où les images sont decoupées selon l'emprise mais pas assemblées" + endC)

    return

###########################################################################################################################################
# FONCTION stackImagesDates()                                                                                                             #
###########################################################################################################################################
# ROLE:
#     Assemble par couche (Bande) d'images fusionnées par date
#
# ENTREES DE LA FONCTION :
#    images_list : Liste d'images assemblées par même date
#    pixel_size_x : Taille du pixel en x (en m)
#    pixel_size_y : Taille du pixel en y (en m)
#    stack_file : Le fichier assemblé par couche
#    file_out_suffix_merge : suffix du fichier  temporaire liste des fichiers a merger
#    no_data_value : Option : Value pixel of no data
#    format_raster : Format de l'image de sortie (GTiff, HFA...)
#    ext_txt : extension du fichier texte contenant la liste des fichiers a merger
#    save_results_intermediate : Si faux suppresion des fichiers temporaires
#
# SORTIES DE LA FONCTION :
#    Le fichier de sortie assemblé par couche
#
def stackImagesDates(images_list, pixel_size_x, pixel_size_y, stack_file, file_out_suffix_merge, no_data_value, format_raster, ext_txt, save_results_intermediate):

    # Fichier txt temporaire liste des fichiers a merger
    repertory_output = os.path.dirname(stack_file)
    file_name = os.path.splitext(os.path.basename(stack_file))[0]
    list_file_tmp = repertory_output + os.sep + file_name + file_out_suffix_merge + ext_txt
    for imagefile in images_list:
        appendTextFileCR(list_file_tmp, imagefile)

    # Nettoyage du resultat band stack si le fichier existe déjà
    if os.path.exists(stack_file):
        removeFile(stack_file)

    # Utilisation de la commande gdal_merge pour concatener les couches de toutes les images relatives aux différentes dates de prises de vue en une seule image resultat
    cmd_merge = "gdal_merge" + getExtensionApplication() + " -a_nodata " + str(no_data_value) + " -of " + format_raster + " -ps " + str(pixel_size_x) + " " + str(pixel_size_y) + " -o " + stack_file + " -separate  --optfile " + list_file_tmp
    exit_code = os.system(cmd_merge)
    if exit_code != 0:
        raise NameError (bold + red + " Une erreur c'est produite au cours de la création du fichier band stack : " + stack_file + ". Voir message d'erreur." + endC)

    # Supression des fichiers temporaires
    if not save_results_intermediate:
        if os.path.exists(list_file_tmp):
            removeFile(list_file_tmp)

    return

###########################################################################################################################################
# FONCTION vrtImages()                                                                                                                    #
###########################################################################################################################################
# ROLE:
#     Creation d'un fichier VRT d'une liste d'image
#
# ENTREES DE LA FONCTION :
#    images_list : Liste d'images d'entrées
#    empr_xmin   : L'emprise coordonnée xmin
#    empr_xmax   : L'emprise coordonnée xmax
#    empr_ymin   : L'emprise coordonnée ymin
#    empr_ymax   : L'emprise coordonnée ymax
#    vrt_file    : Le fichier VRT
#
# SORTIES DE LA FONCTION :
#    Le fichier VRT de sortie
#
def vrtImages(images_list, empr_xmin, empr_xmax, empr_ymin, empr_ymax, vrt_file):

    # Fichier vrt
    print(("Les images sont decoupées selon l'emprise pour créer le fichier vrt"))

    if os.path.exists(vrt_file):
        removeFile(vrt_file)

    # Utilisation de la commande gdalbuildvrt pour mosaiquer les images d'entrées
    images_string_list = ''
    for image_file in images_list:
        images_string_list += ' '+image_file
    cmd_vrt = "gdalbuildvrt -te " + str(empr_xmin) + " " + str(empr_ymin) + " " + str(empr_xmax) + " " + str(empr_ymax) + " " + vrt_file + " " + images_string_list
    exit_code = os.system(cmd_vrt)
    if exit_code != 0:
        raise NameError (bold + red + "!!! Une erreur c'est produite au cours de la création du fichier vrt : " + vrt_file + ". Voir message d'erreur." + endC)
    return

###########################################################################################################################################
# MISE EN PLACE DU PARSER                                                                                                                 #
###########################################################################################################################################

# Code executé seulement dans le cas ou le script est lancé depuis une ligne de commande
# Il n'est pas executé lors d'un import ImagesAssembly.py
# Exemple de lancement en ligne de commande:
# python ImagesAssembly.py -e ../ImagesTestChaine/APTV_07.shp -o ../ImagesTestChaine/APTV_07/APTV_07.tif -pathi ../ImagesTestChaine/APTV_01 -raf 'GTiff' -vef 'ESRI Shapefile' -c -sepn '_' -posd 2 -nbcd 8 -log ../ImagesTestChaine/APTV_07/fichierTestLog.txt
# python ImagesAssembly.py -e ../ImagesTestChaine/APTV_BORDEAUX/FV_COMMU_S_L93CUT_CUBE.shp -o ../ImagesTestChaine/APTV_BORDEAUX/APTV_BORDEAUX.tif -pathi /home/scgsi/Data_Saturn/ORT_2013120940341199_LA93  /home/scgsi/Data_Saturn/ORT_2013121039858819_LA93  /home/scgsi/Data_Saturn/ORT_2014030539583319_LA93  /home/scgsi/Data_Saturn/ORT_2014030539611069_LA93 -z -f 'GTiff' -c -sepn '_' -posd 2 -nbcd 8 -log ../ImagesTestChaine/APTV_07/fichierTestLog.txt

def main(gui=False):

    parser = argparse.ArgumentParser(prog="ImagesAssembly", description=" \
    Info : Creating an image from an raw image mosaic (.tif, .ecw, .jp2, .asc) and an emprise file (.shp).\n\
    Objectif : Assembler et/ou découper des images raster. \n\
    Example : python ImagesAssembly.py -e ../ImagesTestChaine/APTV_BORDEAUX/FV_COMMU_S_L93\CUT_CUBE.shp \n\
                                       -o ../ImagesTestChaine/APTV_BORDEAUX/APTV_BORDEAUX.tif \n\
                                       -pathi /home/scgsi/Data_Saturn/ORT_2013120940341199_LA93 \n\
                                              /home/scgsi/Data_Saturn/ORT_2013121039858819_LA93 \n\
                                              /home/scgsi/Data_Saturn/ORT_2014030539583319_LA93 \n\
                                              /home/scgsi/Data_Saturn/ORT_2014030539611069_LA93 \n\
                                       -z -raf 'GTiff' -vef 'ESRI Shapefile' -c -sepn '_' -posd 2 -nbcd 8  \n\
                                       -log ../ImagesTestChaine/APTV_07/fichierTestLog.txt")

    parser.add_argument('-e','--emprise_input', default="",help="Input emprise - Cutting boundaries vector file, format shape (.shp).", type=str, required=True)
    parser.add_argument('-o','--image_output', default="",help="Output image file (.tif) cutout at emprise or result directory if option -d", type=str, required=True)
    parser.add_argument('-pathi','--path_input_dir',default="",nargs="+",help="Liste storage directory of sources raw images (.tif, .ecw, .jp2, .asc), can be several directories",type=str, required=True)
    parser.add_argument('-na', '--not_assembled', action='store_true', default=False, help="Option : The images in the emprise are cut but not assembled. By default : False", required=False)
    parser.add_argument('-z', '--zone_date', action='store_true', default=False, help="Option : The images are assembled by area date shooting, a result picture by date. By default : False", required=False)
    parser.add_argument('-epsg','--epsg', default=2154, help="Option : Type output image projection (EPSG),by default the same projection as the input images", type=int, required=False)
    parser.add_argument('-v', '--vrtfile', action='store_true', default=False, help="Option : Creating a VRT file for each image assembly containing the coordinates of the source images. By default : False", required=False)
    parser.add_argument('-s', '--band_stack', action='store_true', default=False, help="Option : Creating a final file concatenation of all layers of the images assembled into one file. By default : False", required=False)
    parser.add_argument('-c', '--clean_zero', action='store_true', default=False, help="Option : Clean pixel to zero value images input. By default : False", required=False)
    parser.add_argument('-czo', '--clean_zero_output', action='store_true', default=False, help="Option : Clean pixel to zero value images assembly output. By default : False", required=False)
    parser.add_argument('-cval', '--clean_zero_value', default=1.0, help="Option : for option clean_zero and clean_zero_value define the replace value. By default : Nodata replaced by 1", type=float, required=False)
    parser.add_argument('-psx', '--pixel_size_x', default=0, help="Option : Size pixel coordinate X in meter. By default : if 0 use pixel size X of the first image file", type=float, required=False)
    parser.add_argument('-psy', '--pixel_size_y', default=0, help="Option : Size pixel coordinate Y in meter. By default : if 0 use pixel size Y of the first image file", type=float, required=False)
    parser.add_argument('-ndv','--no_data_value', default=0, help="Option : Value of the pixel no data. By default : 0", type=int, required=False)
    parser.add_argument('-sepn','--separname', default="_", help="Acquisition date in the name, information separator (For example : '_'). By default : '_'", type=str, required=False)
    parser.add_argument('-posd','--posdate', default=2, help="Acquisition date in the name, position relative to the information separator (For example : 3). By default : 2", type=int, required=False)
    parser.add_argument('-nbcd','--nbchardate', default=8, help="Acquisition date in the name, number of characters constituting the date (For example : 10). By default : 8", type=int, required=False)
    parser.add_argument('-sepd','--separdate', default="", help="Acquisition date in the name, the date separator in information (For example : '-'). By default : ''", type=str, required=False)
    parser.add_argument('-suferr','--new_suffix_error',default="_error",help="Name suffix to append to the basename image to create error file", type=str, required=False)
    parser.add_argument('-sufmer','--new_suffix_merge',default="_merge",help="Name suffix to append to the basename image to create merge file", type=str, required=False)
    parser.add_argument('-sufcle','--new_suffix_clean',default="_clean",help="Name suffix to append to the basename image to create clean file", type=str, required=False)
    parser.add_argument('-sufsta','--new_suffix_stack',default="_stack",help="Name suffix to append to the basename image to create stack file", type=str, required=False)
    parser.add_argument('-raf','--format_raster', default="GTiff", help="Option : Format output image, by default : GTiff (GTiff, HFA...)", type=str, required=False)
    parser.add_argument('-vef','--format_vector', default="ESRI Shapefile",help="Format of the output file.", type=str, required=False)
    parser.add_argument('-rae','--extension_raster', default=".tif", help="Option : Extension file for image raster. By default : '.tif'", type=str, required=False)
    parser.add_argument('-vee','--extension_vector',default=".shp",help="Option : Extension file for vector. By default : '.shp'", type=str, required=False)
    parser.add_argument('-log','--path_time_log',default="",help="Name of log", type=str, required=False)
    parser.add_argument('-sav','--save_results_inter',action='store_true',default=False,help="Save or delete intermediate result after the process. By default, False", required=False)
    parser.add_argument('-now','--overwrite',action='store_false',default=True,help="Overwrite files with same names. By default : True", required=False)
    parser.add_argument('-debug','--debug',default=3,help="Option : Value of level debug trace, default : 3 ",type=int, required=False)
    args = displayIHM(gui, parser)

    # Définition des variables issues du parser

    # Récupération de l'emprise d'entree
    if args.emprise_input != None :
        emprise_input = args.emprise_input
        if not os.path.isfile(emprise_input):
            raise NameError (cyan + "ImagesAssembly : " + bold + red  + "File %s not existe!" %(emprise_input) + endC)

    # Récupération de l'image de sortie
    if args.image_output != None :
        image_output = args.image_output

    # Paramètres des répertoires d'entrée
    if args.path_input_dir != None:
        repertory_input_list = args.path_input_dir
        for repertory in repertory_input_list :
            if not os.path.isdir(repertory):
                raise NameError (cyan + "ImagesAssembly : " + bold + red  + "Directory %s not existe!" %(repertory) + endC)

    # Paramètres de découpe
    if args.not_assembled != None:
        not_assembled = args.not_assembled

    if args.zone_date != None:
        zone_date = args.zone_date

    # Paramètre valeur de la projection des images de sorties
    if args.epsg != None:
        epsg = args.epsg

    # Option sortie d'un fichier vrt
    if args.vrtfile != None:
        vrtfile = args.vrtfile

    # Option sortie d'un fichier stacké
    if args.band_stack != None:
        band_stack = args.band_stack

    # Parametres de nettoyage des pixels à zero
    if args.clean_zero != None:
        clean_zero = args.clean_zero

    if args.clean_zero_output != None:
        clean_zero_output = args.clean_zero_output

    if args.clean_zero_value != None:
        clean_zero_value = args.clean_zero_value

    # Paramètres de définition de l'image en x et y
    if args.pixel_size_x != None:
        pixel_size_x = args.pixel_size_x

    if args.pixel_size_y != None:
        pixel_size_y = args.pixel_size_y

    # Parametres de valeur du nodata des fichiers de sortie
    if args.no_data_value!= None:
        no_data_value = args.no_data_value

    # Paramètres de la date
    if args.separname != None:
        separname = args.separname

    if args.posdate != None:
        posdate = args.posdate

    if args.nbchardate != None:
        nbchardate = args.nbchardate

    if args.separdate != None:
        separdate = args.separdate

    # Les suffix
    if args.new_suffix_error != None:
        file_out_suffix_error = args.new_suffix_error

    if args.new_suffix_merge != None:
        file_out_suffix_merge = args.new_suffix_merge

    if args.new_suffix_clean != None:
        file_out_suffix_clean = args.new_suffix_clean

    if args.new_suffix_stack != None:
        file_out_suffix_stack = args.new_suffix_stack

    # Paramètre format des images de sortie
    if args.format_raster != None:
        format_raster = args.format_raster

    # Récupération du format des vecteurs de sortie
    if args.format_vector != None :
        format_vector = args.format_vector

    # Paramètre de l'extension des images rasters
    if args.extension_raster != None:
        extension_raster = args.extension_raster

    # Récupération de l'extension des fichiers vecteurs
    if args.extension_vector != None:
        extension_vector = args.extension_vector

    # Récupération du nom du fichier log
    if args.path_time_log != None:
        path_time_log = args.path_time_log

    # Ecrasement et sauvegardes des fichiers
    if args.save_results_inter != None:
        save_results_intermediate = args.save_results_inter

    if args.overwrite != None:
        overwrite = args.overwrite

    # Récupération de l'option niveau de debug
    if args.debug!= None:
        global debug
        debug = args.debug

    # Affichage des arguments récupérés
    if debug >= 3:
        print(bold + green + "Variables dans le parser" + endC)
        print(cyan + "ImagesAssembly : " + endC + "emprise_input : " + str(emprise_input) + endC)
        print(cyan + "ImagesAssembly : " + endC + "image_output : " + str(image_output) + endC)
        print(cyan + "ImagesAssembly : " + endC + "path_input_dir : " + str(repertory_input_list) + endC)
        print(cyan + "ImagesAssembly : " + endC + "not_assembled : " + str(not_assembled) + endC)
        print(cyan + "ImagesAssembly : " + endC + "zone_date : " + str(zone_date) + endC)
        print(cyan + "ImagesAssembly : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "ImagesAssembly : " + endC + "vrtfile : " + str(vrtfile) + endC)
        print(cyan + "ImagesAssembly : " + endC + "band_stack : " + str(band_stack) + endC)
        print(cyan + "ImagesAssembly : " + endC + "clean_zero : " + str(clean_zero) + endC)
        print(cyan + "ImagesAssembly : " + endC + "clean_zero_output : " + str(clean_zero_output) + endC)
        print(cyan + "ImagesAssembly : " + endC + "clean_zero_value : " + str(clean_zero_value) + endC)
        print(cyan + "ImagesAssembly : " + endC + "pixel_size_x : " + str(pixel_size_x) + endC)
        print(cyan + "ImagesAssembly : " + endC + "pixel_size_y : " + str(pixel_size_y) + endC)
        print(cyan + "ImagesAssembly : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "ImagesAssembly : " + endC + "separname : " + str(separname) + endC)
        print(cyan + "ImagesAssembly : " + endC + "posdate : " + str(posdate) + endC)
        print(cyan + "ImagesAssembly : " + endC + "nbchardate : " + str(nbchardate) + endC)
        print(cyan + "ImagesAssembly : " + endC + "separdate : " + str(separdate) + endC)
        print(cyan + "ImagesAssembly : " + endC + "new_suffix_error : " + str(file_out_suffix_error) + endC)
        print(cyan + "ImagesAssembly : " + endC + "new_suffix_merge : " + str(file_out_suffix_merge) + endC)
        print(cyan + "ImagesAssembly : " + endC + "new_suffix_clean : " + str(file_out_suffix_clean) + endC)
        print(cyan + "ImagesAssembly : " + endC + "new_suffix_stack : " + str(file_out_suffix_stack) + endC)
        print(cyan + "ImagesAssembly : " + endC + "format_raster : " + str(format_raster) + endC)
        print(cyan + "ImagesAssembly : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "ImagesAssembly : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "ImagesAssembly : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "ImagesAssembly : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "ImagesAssembly : " + endC + "save_results_inter : " + str(save_results_intermediate) + endC)
        print(cyan + "ImagesAssembly : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "ImagesAssembly : " + endC + "debug : " + str(debug) + endC)

    # EXECUTION DE LA FONCTION
    # Si le dossier de sortie n'existe pas, on le crée
    repertory_output = os.path.dirname(image_output)
    if not os.path.isdir(repertory_output):
        os.makedirs(repertory_output)

    # Fonction générale
    selectAssembyImagesByHold(emprise_input, repertory_input_list, image_output, not_assembled, zone_date, epsg, vrtfile, band_stack, clean_zero, clean_zero_output, clean_zero_value,pixel_size_x, pixel_size_y, no_data_value, separname, posdate, nbchardate, separdate, path_time_log, file_out_suffix_error, file_out_suffix_merge, file_out_suffix_clean, file_out_suffix_stack, format_raster, format_vector, extension_raster, extension_vector, save_results_intermediate, overwrite)

# ================================================

if __name__ == '__main__':
  main(gui=False)
