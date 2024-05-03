#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT QUI CREER UN MNH A PARTIR DE DONNEES MNT ET MNS (FICHIERS OU ARCHIVES)                                                             #
#                                                                                                                                           #
#############################################################################################################################################
"""
Nom de l'objet : MnhCreation.py
Description :
-------------
Objectif : Créer un fichier raster de MNH (Model Numerique de Hauteur)
Rq : utilisation des OTB Applications : otbcli_BandMath, otbcli_Rasterization, otbcli_Superimpose

Date de creation : 1/06/2018
----------
Histoire :
----------
Modifications :
    - 22/04/2024 : ajout fonction createMnhFromMnsCorrel() pour générer un MNH à partir du MNS-Correl (image_mns_input et image_mnt_input sont des répertoires où sont stockées les archives MNS-Correl et RGE ALTI 1M)

A Reflechir/A faire :

"""

# Import des bibliothèques Python
from __future__ import print_function
from builtins import input
import os,sys,glob,argparse,string,math,datetime
from osgeo import ogr
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_log import timeLine
from Lib_file import removeFile, removeVectorFile, cleanTempData, deleteDir, read7zArchiveStructure
from Lib_postgis import openConnection, getData, closeConnection
from Lib_text import readTextFileBySeparator, writeTextFile
from Lib_raster import getNodataValueImage, countPixelsOfValue, cutImageByVector, createBinaryMask, rasterizeBinaryVector, rasterizeVector, getEmpriseImage, getPixelWidthXYImage
from Lib_vector import cutoutVectors, fusionVectors, addNewFieldVector, getAttributeValues, setAttributeIndexValuesList, filterSelectDataVector, getProjection
from Lib_saga import fillNodata
from MacroSamplesCreation import createMacroSamples
from CrossingVectorRaster import statisticsVectorRaster

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 3

###########################################################################################################################################
# FONCTION createMnh()                                                                                                                    #
###########################################################################################################################################
def createMnh(image_mns_input, image_mnt_input, image_threshold_input, vector_emprise_input, image_mnh_output, automatic, bd_road_vector_input_list, bd_road_buff_list, sql_road_expression_list, bd_build_vector_input_list, height_bias, threshold_bd_value, threshold_delta_h, mode_interpolation, method_interpolation, interpolation_bco_radius, simplify_vector_param, epsg, no_data_value, ram_otb, path_time_log, format_raster='GTiff', format_vector='ESRI Shapefile', extension_raster=".tif", extension_vector=".shp", save_results_intermediate=False, overwrite=True):
    """
    # ROLE:
    #     Creation d'un raster de données MNH (Model Numerique de Hauteur)
    #     A partir des rasters MNS et MNT plus données vecteur BDTopo route et bati
    #
    # ENTREES DE LA FONCTION :
    #     image_mns_input : l'image MNS d'entrée qui servira de base pour la resolution et la creation du MNH
    #     image_mnt_input : l'image MNT d'entrée à soustraire au MNS
    #     image_threshold_input : l'image de seuillage d'entrée qui servira de filtre pour la bd route (en generale le NDVI)
    #     vector_emprise_input : le vecteur d'emprise de la zone d'etude
    #     image_mnh_output : l'image MNH raster de sortie
    #     automatic : Selection mode entierement automatique ou verification des polygones par utilisateur en dehors de l'application
    #     bd_road_vector_input_list :  liste des vecteurs de la bd route
    #     bd_road_buff_list : liste des valeurs des buffers associés au traitement à appliquer aux vecteurs de bd routes
    #     sql_road_expression_list : liste d'expression sql pour le filtrage des fichiers vecteur de bd routes
    #     bd_build_vector_input_list : liste des vecteurs de la bd bati
    #     height_bias : valeur du biais pour le calcul du MNH
    #     threshold_bd_value : valeur de seuillage de l'image de filtrage
    #     threshold_delta_h : valeur de seuillage des bati a utilisié delta entre la heuteur des bati et le MNH
    #     mode_interpolation : mode d'interpollation
    #     method_interpolation : algo d'interpolation utilisé
    #     interpolation_bco_radius : parametre radius pour l'interpolation bicubic
    #     simplify_vector_param : parmetre de simplification des polygones
    #     epsg : EPSG des fichiers de sortie utilisation de la valeur des fichiers d'entrée si la valeur = 0
    #     no_data_value : Valeur des pixels sans données pour les rasters
    #     ram_otb : memoire RAM disponible pour les applications OTB
    #     path_time_log : le fichier de log de sortie
    #     format_raster : Format de l'image de sortie, par défaut : GTiff
    #     format_vector : format du fichier vecteur. Optionnel, par default : 'ESRI Shapefile'
    #     extension_raster : extension des fichiers raster de sortie, par defaut = '.tif'
    #     extension_vector : extension du fichier vecteur de sortie, par defaut = '.shp'
    #     save_results_intermediate : fichiers de sorties intermediaires nettoyees, par defaut = False
    #     overwrite : écrase si un fichier existant a le même nom qu'un fichier de sortie, par defaut a True
    #
    # SORTIES DE LA FONCTION :
    #    un raster MNH issu de la difference des fichiers d'entrée MNS par MNT plus des ameliorations
    #
    """

    # Mise à jour du Log
    starting_event = "createMnh() : MNH creation starting : "
    timeLine(path_time_log,starting_event)

    print(endC)
    print(bold + green + "## START : MNH CREATION" + endC)
    print(endC)

    if debug >= 2:
        print(bold + green + "createMnh() : Variables dans la fonction" + endC)
        print(cyan + "createMnh() : " + endC + "image_mns_input : " + str(image_mns_input) + endC)
        print(cyan + "createMnh() : " + endC + "image_mnt_input : " + str(image_mnt_input) + endC)
        print(cyan + "createMnh() : " + endC + "image_threshold_input : " + str(image_threshold_input) + endC)
        print(cyan + "createMnh() : " + endC + "vector_emprise_input : " + str(vector_emprise_input) + endC)
        print(cyan + "createMnh() : " + endC + "image_mnh_output : " + str(image_mnh_output) + endC)
        print(cyan + "createMnh() : " + endC + "automatic : " + str(automatic) + endC)
        print(cyan + "createMnh() : " + endC + "bd_road_vector_input_list : " + str(bd_road_vector_input_list) + endC)
        print(cyan + "createMnh() : " + endC + "bd_road_buff_list : " + str(bd_road_buff_list) + endC)
        print(cyan + "createMnh() : " + endC + "sql_road_expression_list : " + str(sql_road_expression_list) + endC)
        print(cyan + "createMnh() : " + endC + "bd_build_vector_input_list : " + str(bd_build_vector_input_list) + endC)
        print(cyan + "createMnh() : " + endC + "height_bias : " + str(height_bias) + endC)
        print(cyan + "createMnh() : " + endC + "threshold_bd_value : " + str(threshold_bd_value) + endC)
        print(cyan + "createMnh() : " + endC + "threshold_delta_h : " + str(threshold_delta_h) + endC)
        print(cyan + "createMnh() : " + endC + "mode_interpolation : " + str(mode_interpolation) + endC)
        print(cyan + "createMnh() : " + endC + "method_interpolation : " + str(method_interpolation) + endC)
        print(cyan + "createMnh() : " + endC + "interpolation_bco_radius : " + str(interpolation_bco_radius) + endC)
        print(cyan + "createMnh() : " + endC + "simplify_vector_param : " + str(simplify_vector_param) + endC)
        print(cyan + "createMnh() : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "createMnh() : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "createMnh() : " + endC + "ram_otb : " + str(ram_otb) + endC)
        print(cyan + "createMnh() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "createMnh() : " + endC + "format_raster : " + str(format_raster) + endC)
        print(cyan + "createMnh() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "createMnh() : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "createMnh() : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "createMnh() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "createMnh() : " + endC + "overwrite : " + str(overwrite) + endC)

    # LES CONSTANTES
    PRECISION = 0.0000001

    CODAGE_8B = "uint8"
    CODAGE_F = "float"

    SUFFIX_CUT = "_cut"
    SUFFIX_CLEAN = "_clean"
    SUFFIX_SAMPLE = "_sample"
    SUFFIX_MASK = "_mask"
    SUFFIX_TMP = "_tmp"
    SUFFIX_MNS = "_mns"
    SUFFIX_MNT = "_mnt"
    SUFFIX_ROAD = "_road"
    SUFFIX_BUILD = "_build"
    SUFFIX_RASTER = "_raster"
    SUFFIX_VECTOR = "_vector"

    # DEFINIR LES REPERTOIRES ET FICHIERS TEMPORAIRES
    repertory_output = os.path.dirname(image_mnh_output)
    basename_mnh = os.path.splitext(os.path.basename(image_mnh_output))[0]

    sub_repertory_raster_temp = repertory_output + os.sep + basename_mnh + SUFFIX_RASTER + SUFFIX_TMP
    sub_repertory_vector_temp = repertory_output + os.sep + basename_mnh + SUFFIX_VECTOR + SUFFIX_TMP
    cleanTempData(sub_repertory_raster_temp)
    cleanTempData(sub_repertory_vector_temp)

    basename_vector_emprise = os.path.splitext(os.path.basename(vector_emprise_input))[0]
    basename_mns_input = os.path.splitext(os.path.basename(image_mns_input))[0]
    basename_mnt_input = os.path.splitext(os.path.basename(image_mnt_input))[0]

    image_mnh_tmp = sub_repertory_raster_temp + os.sep + basename_mnh + SUFFIX_TMP + extension_raster
    image_mnh_road = sub_repertory_raster_temp + os.sep + basename_mnh + SUFFIX_ROAD + extension_raster

    vector_bd_bati_temp = sub_repertory_vector_temp + os.sep + basename_mnh + SUFFIX_BUILD + SUFFIX_TMP + extension_vector
    vector_bd_bati = repertory_output + os.sep + basename_mnh + SUFFIX_BUILD + extension_vector
    raster_bd_bati = sub_repertory_vector_temp + os.sep + basename_mnh + SUFFIX_BUILD + extension_raster
    removeVectorFile(vector_bd_bati)

    image_emprise_mnt_mask = sub_repertory_raster_temp + os.sep + basename_vector_emprise + SUFFIX_MNT + extension_raster
    image_mnt_cut = sub_repertory_raster_temp + os.sep + basename_mnt_input + SUFFIX_CUT + extension_raster
    image_mnt_clean = sub_repertory_raster_temp + os.sep + basename_mnt_input + SUFFIX_CLEAN + extension_raster
    image_mnt_clean_sample = sub_repertory_raster_temp + os.sep + basename_mnt_input + SUFFIX_CLEAN + SUFFIX_SAMPLE + extension_raster
    image_emprise_mns_mask = sub_repertory_raster_temp + os.sep + basename_vector_emprise + SUFFIX_MNS + extension_raster
    image_mns_cut = sub_repertory_raster_temp + os.sep + basename_mns_input + SUFFIX_CUT + extension_raster
    image_mns_clean = sub_repertory_raster_temp + os.sep + basename_mns_input + SUFFIX_CLEAN + extension_raster

    vector_bd_road_temp = sub_repertory_vector_temp + os.sep + basename_mnh + SUFFIX_ROAD + SUFFIX_TMP + extension_vector
    raster_bd_road_mask = sub_repertory_raster_temp + os.sep + basename_mnh + SUFFIX_ROAD + SUFFIX_MASK + extension_raster

    if image_threshold_input != "" :
        basename_threshold_input = os.path.splitext(os.path.basename(image_threshold_input))[0]
        image_threshold_cut = sub_repertory_raster_temp + os.sep + basename_threshold_input + SUFFIX_CUT + extension_raster
        image_threshold_mask = sub_repertory_raster_temp + os.sep + basename_threshold_input + SUFFIX_MASK + extension_raster

    # VERIFICATION SI LE FICHIER DE SORTIE EXISTE DEJA
    # Si un fichier de sortie avec le même nom existe déjà, et si l'option ecrasement est à false, alors on ne fait rien
    check = os.path.isfile(image_mnh_output)
    if check and not overwrite:
        print(bold + yellow +  "createMnh() : " + endC + "Create mnh %s from %s and %s already done : no actualisation" % (image_mnh_output, image_mns_input, image_mnt_input) + endC)
    # Si non, ou si la fonction ecrasement est désative, alors on le calcule
    else:
        if check:
            try: # Suppression de l'éventuel fichier existant
                removeFile(image_mnh_output)
            except Exception:
                pass # Si le fichier ne peut pas être supprimé, on suppose qu'il n'existe pas et on passe à la suite

        # DECOUPAGE DES FICHIERS MS ET MNT D'ENTREE PAR LE FICHIER D'EMPRISE
        if debug >= 3:
            print(bold + green +  "createMnh() : " + endC + "Decoupage selon l'emprise des fichiers %s et %s " %(image_mns_input, image_mnt_input) + endC)

        # Fonction de découpe du mns
        if not cutImageByVector(vector_emprise_input, image_mns_input, image_mns_cut, None, None, False, no_data_value, epsg, format_raster, format_vector) :
            raise NameError (cyan + "createMnh() : " + bold + red + "!!! Une erreur c'est produite au cours du decoupage de l'image : " + image_mns_input + ". Voir message d'erreur." + endC)

        # Fonction de découpe du mnt
        if not cutImageByVector(vector_emprise_input, image_mnt_input, image_mnt_cut, None, None, False, no_data_value, epsg, format_raster, format_vector) :
            raise NameError (cyan + "createMnh() : " + bold + red + "!!! Une erreur c'est produite au cours du decoupage de l'image : " + image_mnt_input + ". Voir message d'erreur." + endC)

        if debug >= 3:
            print(bold + green +  "createMnh() : " + endC + "Decoupage des fichiers %s et %s complet" %(image_mns_cut, image_mnt_cut) + endC)


        # REBOUCHAGE DES TROUS DANS LE MNT D'ENTREE SI NECESSAIRE

        nodata_mnt = getNodataValueImage(image_mnt_cut)
        pixelNodataCount = countPixelsOfValue(image_mnt_cut, nodata_mnt)

        if pixelNodataCount > 0 :

            if debug >= 3:
                print(bold + green +  "createMnh() : " + endC + "Fill the holes MNT for  %s" %(image_mnt_cut) + endC)

            # Rasterisation du vecteur d'emprise pour creer un masque pour boucher les trous du MNT
            rasterizeBinaryVector(vector_emprise_input, image_mnt_cut, image_emprise_mnt_mask, 1, CODAGE_8B)

            # Utilisation de SAGA pour boucher les trous
            fillNodata(image_mnt_cut, image_emprise_mnt_mask, image_mnt_clean, save_results_intermediate)

            if debug >= 3:
                print(bold + green +  "createMnh() : " + endC + "Fill the holes MNT to %s completed" %(image_mnt_clean) + endC)

        else :
            image_mnt_clean = image_mnt_cut
            if debug >= 3:
                print(bold + green +  "\ncreateMnh() : " + endC + "Fill the holes not necessary MNT for %s" %(image_mnt_cut) + endC)

        # REBOUCHAGE DES TROUS DANS LE MNS D'ENTREE SI NECESSAIRE

        nodata_mns = getNodataValueImage(image_mns_cut)
        pixelNodataCount = countPixelsOfValue(image_mns_cut, nodata_mns)

        if pixelNodataCount > 0 :

            if debug >= 3:
                print(bold + green +  "createMnh() : " + endC + "Fill the holes MNS for  %s" %(image_mns_cut) + endC)

            # Rasterisation du vecteur d'emprise pour creer un masque pour boucher les trous du MNS
            rasterizeBinaryVector(vector_emprise_input, image_mns_cut, image_emprise_mns_mask, 1, CODAGE_8B)

            # Utilisation de SAGA pour boucher les trous
            fillNodata(image_mns_cut, image_emprise_mns_mask, image_mns_clean, save_results_intermediate)

            if debug >= 3:
                print(bold + green +  "\ncreateMnh() : " + endC + "Fill the holes MNS to %s completed" %(image_mns_clean) + endC)

        else :
            image_mns_clean = image_mns_cut
            if debug >= 3:
                print(bold + green +  "createMnh() : " + endC + "Fill the holes not necessary MNS for %s" %(image_mns_cut) + endC)

        # CALLER LE FICHIER MNT AU FORMAT DU FICHIER MNS

        # Commande de mise en place de la geométrie re-echantionage
        command = "otbcli_Superimpose -inr " + image_mns_clean + " -inm " + image_mnt_clean + " -mode " + mode_interpolation + " -interpolator " + method_interpolation + " -out " + image_mnt_clean_sample

        if method_interpolation.lower() == 'bco' :
            command += " -interpolator.bco.radius " + str(interpolation_bco_radius)
        if ram_otb > 0:
            command += " -ram %d" %(ram_otb)

        if debug >= 3:
            print(cyan + "createMnh() : " + bold + green + "Réechantillonage du fichier %s par rapport à la reference %s" %(image_mnt_clean, image_mns_clean) + endC)
            print(command)

        exit_code = os.system(command)
        if exit_code != 0:
            print(command)
            raise NameError (cyan + "createMnh() : " + bold + red + "!!! Une erreur c'est produite au cours du superimpose de l'image : " + image_mnt_input + ". Voir message d'erreur." + endC)

        # INCRUSTATION DANS LE MNH DES DONNEES VECTEURS ROUTES

        if debug >= 3:
            print(bold + green +  "createMnh() : " + endC + "Use BD road to clean MNH"  + endC)

        # Creation d'un masque de filtrage des donnes routes (exemple : le NDVI)
        if image_threshold_input != "" :
            if not cutImageByVector(vector_emprise_input, image_threshold_input, image_threshold_cut, None, None, False, no_data_value, epsg, format_raster, format_vector) :
                raise NameError (cyan + "createMnh() : " + bold + red + "!!! Une erreur c'est produite au cours du decoupage de l'image : " + image_threshold_input + ". Voir message d'erreur." + endC)
            createBinaryMask(image_threshold_cut, image_threshold_mask, threshold_bd_value, False, CODAGE_8B)

        # Execution de la fonction createMacroSamples pour une image correspondant au données routes
        if bd_road_vector_input_list != [] :
            createMacroSamples(image_mns_clean, vector_emprise_input, vector_bd_road_temp, raster_bd_road_mask, bd_road_vector_input_list, bd_road_buff_list, sql_road_expression_list, path_time_log, basename_mnh, simplify_vector_param, format_vector, extension_vector, save_results_intermediate, overwrite)

        if debug >= 3:
            print(bold + green +  "\ncreateMnh() : " + endC + "File raster from BD road is create %s" %(raster_bd_road_mask) + endC)

        # CALCUL DU MNH

        # Calcul par bandMath du MNH definir l'expression qui soustrait le MNT au MNS en introduisant le biais et en mettant les valeurs à 0 à une valeur approcher de 0.0000001
        delta = ""
        if height_bias > 0 :
            delta = "+%s" %(str(height_bias))
        elif height_bias < 0 :
            delta = "-%s" %(str(abs(height_bias)))
        else :
            delta = ""

        # Definition de l'expression
        if bd_road_vector_input_list != [] :
            if image_threshold_input != "" :
                expression = "\"im3b1 > 0 and im4b1 > 0?%s:(im1b1-im2b1%s) > 0.0?im1b1-im2b1%s:%s\"" %(str(PRECISION), delta, delta, str(PRECISION))
                command = "otbcli_BandMath -il %s %s %s %s -out %s %s -exp %s" %(image_mns_clean, image_mnt_clean_sample, raster_bd_road_mask, image_threshold_mask, image_mnh_tmp, CODAGE_F, expression)
            else :
                expression = "\"im3b1 > 0?%s:(im1b1-im2b1%s) > 0.0?im1b1-im2b1%s:%s\"" %(str(PRECISION), delta, delta, str(PRECISION))
                command = "otbcli_BandMath -il %s %s %s -out %s %s -exp %s" %(image_mns_clean, image_mnt_clean_sample, raster_bd_road_mask, image_mnh_tmp, CODAGE_F, expression)
        else :
            expression = "\"(im1b1-im2b1%s) > 0.0?im1b1-im2b1%s:%s\"" %(delta, delta, str(PRECISION))
            command = "otbcli_BandMath -il %s %s -out %s %s -exp %s" %(image_mns_clean, image_mnt_clean_sample, image_mnh_tmp, CODAGE_F, expression)

        if ram_otb > 0:
            command += " -ram %d" %(ram_otb)

        if debug >= 3:
            print(cyan + "createMnh() : " + bold + green + "Calcul du MNH  %s difference du MNS : %s par le MNT :%s" %(image_mnh_tmp, image_mns_clean, image_mnt_clean_sample) + endC)
            print(command)

        exitCode = os.system(command)
        if exitCode != 0:
            print(command)
            raise NameError(cyan + "createMnh() : " + bold + red + "An error occured during otbcli_BandMath command to compute MNH " + image_mnh_tmp + ". See error message above." + endC)

        # DECOUPAGE DU MNH

        if bd_build_vector_input_list == []:
            image_mnh_road = image_mnh_output

        if debug >= 3:
            print(bold + green +  "createMnh() : " + endC + "Decoupage selon l'emprise du fichier mnh %s " %(image_mnh_tmp) + endC)

        # Fonction de découpe du mnh
        if not cutImageByVector(vector_emprise_input, image_mnh_tmp, image_mnh_road, None, None, False, no_data_value, epsg, format_raster, format_vector) :
            raise NameError (cyan + "createMnh() : " + bold + red + "!!! Une erreur c'est produite au cours du decoupage de l'image : " + image_mns_input + ". Voir message d'erreur." + endC)

        if debug >= 3:
            print(bold + green +  "createMnh() : " + endC + "Decoupage du fichier mnh %s complet" %(image_mnh_road) + endC)

        # INCRUSTATION DANS LE MNH DES DONNEES VECTEURS BATIS

        # Si demander => liste de fichier vecteur bati passé en donnée d'entrée
        if bd_build_vector_input_list != []:

            # Découpage des vecteurs de bd bati exogenes avec l'emprise
            vectors_build_cut_list = []
            for vector_build_input in bd_build_vector_input_list :
                vector_name = os.path.splitext(os.path.basename(vector_build_input))[0]
                vector_build_cut = sub_repertory_vector_temp + os.sep + vector_name + SUFFIX_CUT + extension_vector
                vectors_build_cut_list.append(vector_build_cut)
            cutoutVectors(vector_emprise_input, bd_build_vector_input_list, vectors_build_cut_list, format_vector)

            # Fusion des vecteurs batis découpés
            fusionVectors (vectors_build_cut_list, vector_bd_bati_temp)

            # Croisement vecteur rasteur entre le vecteur fusion des batis et le MNH créé precedement
            statisticsVectorRaster(image_mnh_road, vector_bd_bati_temp, "", 1, False, False, True, ['PREC_PLANI','PREC_ALTI','ORIGIN_BAT','median','sum','std','unique','range'], [], {}, True, no_data_value, format_vector, path_time_log, save_results_intermediate, overwrite)

            # Calcul de la colonne delta_H entre les hauteurs des batis et la hauteur moyenne du MNH sous le bati
            COLUMN_ID = "ID"
            COLUMN_H_BUILD = "HAUTEUR"
            COLUMN_H_BUILD_MIN = "Z_MIN"
            COLUMN_H_BUILD_MAX = "Z_MAX"
            COLUMN_H_MNH = "mean"
            COLUMN_H_MNH_MIN = "min"
            COLUMN_H_MNH_MAX = "max"
            COLUMN_H_DIFF = "H_diff"

            field_type = ogr.OFTReal
            field_value = 0.0
            field_width = 20
            field_precision = 2
            attribute_name_dico = {}
            attribute_name_dico[COLUMN_ID] = ogr.OFTString
            attribute_name_dico[COLUMN_H_BUILD] = ogr.OFTReal
            attribute_name_dico[COLUMN_H_MNH] = ogr.OFTReal

            # Ajouter la nouvelle colonne H_diff
            addNewFieldVector(vector_bd_bati_temp, COLUMN_H_DIFF, field_type, field_value, field_width, field_precision, format_vector)

            # Recuperer les valeur de hauteur du bati et du mnt dans le vecteur
            data_z_dico = getAttributeValues(vector_bd_bati_temp, None, None, attribute_name_dico, format_vector)

            # Calculer la difference des Hauteur bati et mnt
            field_new_values_dico = {}
            for index in range(len(data_z_dico[COLUMN_ID])) :
                index_polygon = data_z_dico[COLUMN_ID][index]
                delta_h = abs(data_z_dico[COLUMN_H_BUILD][index] - data_z_dico[COLUMN_H_MNH][index])
                field_new_values_dico[index_polygon] = {COLUMN_H_DIFF:delta_h}

            # Mettre à jour la colonne H_diff dans le vecteur
            setAttributeIndexValuesList(vector_bd_bati_temp, COLUMN_ID, field_new_values_dico, format_vector)

            # Suppression de tous les polygones bati dons la valeur du delat H est inferieur à threshold_delta_h
            column = "'%s, %s, %s, %s, %s, %s, %s, %s'"% (COLUMN_ID, COLUMN_H_BUILD, COLUMN_H_BUILD_MIN, COLUMN_H_BUILD_MAX, COLUMN_H_MNH, COLUMN_H_MNH_MIN, COLUMN_H_MNH_MAX, COLUMN_H_DIFF)
            expression = "%s > %s" % (COLUMN_H_DIFF, threshold_delta_h)
            filterSelectDataVector(vector_bd_bati_temp, vector_bd_bati, column, expression, overwrite, format_vector)

            # Attention!!!! PAUSE pour trie et verification des polygones bati nom deja present dans le MNH ou non
            if not automatic :
                print(bold + blue +  "Application MnhCreation => " + endC + "Vérification manuelle du vecteur bati %s pour ne concerver que les batis non présent dans le MNH courant %s" %(vector_bd_bati_temp, image_mnh_road) + endC)
                input(bold + red + "Appuyez sur entree pour continuer le programme..." + endC)

            # Creation du masque bati avec pour H la hauteur des batiments
            rasterizeVector(vector_bd_bati, raster_bd_bati, image_mnh_road, COLUMN_H_BUILD, codage=CODAGE_F)

            # Fusion du mask des batis et du MNH temporaire
            expression = "\"im1b1 > 0.0?im1b1:im2b1\""
            command = "otbcli_BandMath -il %s %s -out %s %s -exp %s" %(raster_bd_bati, image_mnh_road, image_mnh_output, CODAGE_F, expression)

            if ram_otb > 0:
                command += " -ram %d" %(ram_otb)

            if debug >= 3:
                print(cyan + "createMnh() : " + bold + green + "Amelioration du MNH  %s ajout des hauteurs des batis %s" %(image_mnh_road, raster_bd_bati) + endC)
                print(command)

            exitCode = os.system(command)
            if exitCode != 0:
                print(command)
                raise NameError(cyan + "createMnh() : " + bold + red + "An error occured during otbcli_BandMath command to compute MNH Final" + image_mnh_output + ". See error message above." + endC)

    # SUPPRESIONS FICHIERS INTERMEDIAIRES INUTILES

    # Suppression des fichiers intermédiaires
    if not save_results_intermediate :
        if bd_build_vector_input_list != []:
            removeFile(image_mnh_road)
        if image_threshold_input != "" :
            removeFile(image_threshold_cut)
            removeFile(image_threshold_mask)
        removeFile(raster_bd_bati)
        removeVectorFile(vector_bd_road_temp)
        removeVectorFile(vector_bd_bati_temp)
        removeVectorFile(vector_bd_bati) # A confirmer!!!
        removeFile(raster_bd_road_mask)
        removeFile(image_mnh_tmp)
        deleteDir(sub_repertory_raster_temp)
        deleteDir(sub_repertory_vector_temp)

    print(endC)
    print(bold + green + "## END : MNH CREATION" + endC)
    print(endC)

    # Mise à jour du Log
    ending_event = "createMnh() : MNH creation ending : "
    timeLine(path_time_log,ending_event)

    return

########################################################################
# FONCTION createMnhFromMnsCorrel()                                    #
########################################################################
def createMnhFromMnsCorrel(vector_emprise_input, image_mnh_output, image_reference_input, image_mnt_input, image_mns_input, year=2022, zone="FXX", path_time_log='', save_results_intermediate=False, overwrite=True):
    '''
    # ROLE :
    #     Créer un MNH à partir de données MNS-Correl et RGE ALTI 1M
    #
    # ENTREES DE LA FONCTION :
    #     vector_emprise_input : fichier d'emprise de la zone d'étude (entrée vecteur)
    #     image_mnh_output : fichier MNH (sortie raster)
    #     image_reference_input : fichier de référence pour générer le MNH (entrée raster)
    #     image_mnt_input : répertoire où sont stockées les archives MNT du RGE ALTI 1M
    #     image_mns_input : répertoire où sont stockées les archives MNS du MNS-Correl
    #     year : millésime (ou plus proche millésime) des données MNT/MNS à utiliser. Par défaut, 2022
    #     zone : définition du territoire d'étude. Par défaut, 'FXX'
    #     path_time_log : fichier log de sortie, par défaut vide
    #     save_results_intermediate : fichiers temporaires conservés, par défaut = False
    #     overwrite : écrase si un fichier existant a le même nom qu'un fichier de sortie, par défaut = True
    #
    # SORTIES DE LA FONCTION :
    #     N.A.
    '''
    if debug >= 3:
        print('\n' + bold + green + "Créer un MNH à partir de données MNS-Correl et RGE ALTI 1M - Variables dans la fonction :" + endC)
        print(cyan + "    createMnhFromMnsCorrel() : " + endC + "vector_emprise_input : " + str(vector_emprise_input) + endC)
        print(cyan + "    createMnhFromMnsCorrel() : " + endC + "image_mnh_output : " + str(image_mnh_output) + endC)
        print(cyan + "    createMnhFromMnsCorrel() : " + endC + "image_reference_input : " + str(image_reference_input) + endC)
        print(cyan + "    createMnhFromMnsCorrel() : " + endC + "image_mnt_input : " + str(image_mnt_input) + endC)
        print(cyan + "    createMnhFromMnsCorrel() : " + endC + "image_mns_input : " + str(image_mns_input) + endC)
        print(cyan + "    createMnhFromMnsCorrel() : " + endC + "year : " + str(year) + endC)
        print(cyan + "    createMnhFromMnsCorrel() : " + endC + "zone : " + str(zone) + endC)
        print(cyan + "    createMnhFromMnsCorrel() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "    createMnhFromMnsCorrel() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "    createMnhFromMnsCorrel() : " + endC + "overwrite : " + str(overwrite) + endC)

    # Définition des constantes
    DATABASE_NAME, USER_NAME, PASSWORD, IP_HOST, NUM_PORT, GEOM_FIELD, INSEE_FIELD = "bdtopo_3_3_tousthemes_sql_scr_xxx_2022_12_15", "postgres", "postgres", "172.22.130.99", "5432", "geometrie", "code_insee"
    NOT_AVAILABLE_ZONE_LIST = ["BLM", "MAF"]
    MNT_LENGTH_STRUCTURE, MNT_SEARCH_STRUCTURE_1, MNT_SEARCH_STRUCTURE_2, MNT_SEARCH_STRUCTURE_3, MNT_SPLIT_STRUCTURE = 5, "RGEALTI", "1_DONNEES_LIVRAISON_", "RGEALTI_MNT_", "_"
    MNS_LENGTH_STRUCTURE, MNS_SEARCH_STRUCTURE_1, MNS_SEARCH_STRUCTURE_2, MNS_SEARCH_STRUCTURE_3, MNS_SPLIT_STRUCTURE = 5, "MNS-Correl", "1_DONNEES_LIVRAISON_", "MNS-C_", "-"
    MNS_ARCHIVE_STRUCTURE_FILE, MNS_WRONG_TILE_NAME, MNS_WRONG_TILE_VALUE = "000_Documentation/structure_archives_MNS.csv", "xxx0", "ymin"
    TILE_SIZE = 1000

    # Gestion des variables de sortie
    output_directory = os.path.dirname(image_mnh_output)
    output_MNH_basename = os.path.basename(os.path.splitext(image_mnh_output)[0])
    output_MNH_extension = os.path.splitext(image_mnh_output)[1]
    output_MNT_raster = output_directory + os.sep + output_MNH_basename + "_-_MNT_RGE_ALTI_1M" + output_MNH_extension
    output_MNS_raster = output_directory + os.sep + output_MNH_basename + "_-_MNS_MNS-Correl" + output_MNH_extension

    # Gestion des variables temporaires
    temp_directory = output_directory + os.sep + "MNH_temp"
    temp_MNT_directory = temp_directory + os.sep + "RGE_ALTI_1M"
    if not os.path.exists(temp_MNT_directory):
        os.makedirs(temp_MNT_directory)
    MNT_vrt = temp_directory + os.sep + "RGE_ALTI_1M.vrt"
    MNT_to_vrt_files = temp_directory + os.sep + "RGE_ALTI_1M_files.txt"
    temp_MNS_directory = temp_directory + os.sep + "MNS-Correl"
    if not os.path.exists(temp_MNS_directory):
        os.makedirs(temp_MNS_directory)
    MNS_vrt = temp_directory + os.sep + "MNS-Correl.vrt"
    MNS_to_vrt_files = temp_directory + os.sep + "MNS-Correl_files.txt"

    # Nettoyage des traitements précédents
    if overwrite:
        if debug >= 3:
            print('\n' + cyan + "createMnhFromMnsCorrel() : " + endC + "Nettoyage des traitements précédents." + endC)
        removeFile(image_mnh_output)
        removeFile(output_MNT_raster)
        removeFile(output_MNS_raster)
        cleanTempData(temp_directory)
    else:
        if os.path.exists(image_mnh_output):
            print('\n' + cyan + "createMnhFromMnsCorrel() : " + bold + yellow + "Le fichier de sortie existe déjà et ne sera pas regénéré." + endC)
            raise
        pass

    ####################################################################

    print('\n' + cyan + "createMnhFromMnsCorrel() : " + bold + green + "DEBUT DES TRAITEMENTS" + endC)

    # Mise à jour du log
    starting_event = "createMnhFromMnsCorrel() : Début du traitement : "
    timeLine(path_time_log, starting_event)

    print('\n' + cyan + "createMnhFromMnsCorrel() : " + bold + green + "Début de la préparation des traitements." + endC)

    # Test existence du fichier vecteur d'emprise
    if not os.path.exists(vector_emprise_input):
        print('\n' + bold + red + "Error: Input vector file '%s' not exists!" % vector_emprise_input + endC)
        exit(-1)
    # Gestion des variables du fichier vecteur d'emprise
    format_vector_list = [ogr.GetDriver(i).GetDescription() for i in range(ogr.GetDriverCount())]
    i = 0
    for input_format_vector in format_vector_list:
        driver = ogr.GetDriverByName(input_format_vector)
        data_source_input = driver.Open(vector_emprise_input, 0)
        if data_source_input is not None:
            data_source_input.Destroy()
            break
        i += 1
    input_format_vector = format_vector_list[i]
    input_epsg_vector, input_projection_vector = getProjection(vector_emprise_input, format_vector = input_format_vector)

    # Test existence du fichier raster de référence
    if not os.path.exists(image_reference_input):
        print('\n' + bold + red + "Error: Input raster file '%s' not exists!" % image_reference_input + endC)
        exit(-1)
    # Gestion des variables du fichier raster de référence
    xmin_img, xmax_img, ymin_img, ymax_img = getEmpriseImage(image_reference_input)
    pixel_width, pixel_height = getPixelWidthXYImage(image_reference_input)

    # Test existence du répertoire MNT d'entrée
    if not os.path.isdir(image_mnt_input):
        print('\n' + bold + red + "Error: Input MNT directory '%s' is empty!" % image_mnt_input + endC)
        exit(-1)
    # Gestion des archives MNT
    MNT_zip_files_list = [input_file for input_file in glob.glob(image_mnt_input + os.sep + "D*/*/*.7z")]
    MNT_zip_files_list += [input_file for input_file in glob.glob(image_mnt_input + os.sep + "D*/*/*.7z.001")]
    MNT_zip_files_list.sort()

    # Test existence du répertoire MNS d'entrée
    if not os.path.isdir(image_mns_input):
        print('\n' + bold + red + "Error: Input MNS directory '%s' is empty!" % image_mns_input + endC)
        exit(-1)
    # Gestion des archives MNS
    MNS_zip_files_list = [input_file for input_file in glob.glob(image_mns_input + os.sep + "D*/*/*.7z")]
    MNS_zip_files_list += [input_file for input_file in glob.glob(image_mns_input + os.sep + "D*/*/*.7z.001")]
    MNS_zip_files_list.sort()
    # Test existence du fichier de structure des archives/dalles MNS
    input_MNS_structure_file = image_mns_input + os.sep + MNS_ARCHIVE_STRUCTURE_FILE
    if not os.path.isfile(input_MNS_structure_file):
        print('\n' + bold + red + "Error: MNS archive/tile structure file '%s' not exists!" % input_MNS_structure_file + endC)
        exit(-1)
    MNS_tile_structure = readTextFileBySeparator(input_MNS_structure_file, ';')

    # Gestion des numéros de départements
    if zone == "FXX":
        dpts_list = ["D00" + str(i) for i in range(1, 10)]
        dpts_list += ["D0" + str(i) for i in range(10, 20)]
        dpts_list += ["D02A", "D02B"]
        dpts_list += ["D0" + str(i) for i in range(21, 96)]
        epsg, schema_name, table_name = 2154, "fxx_lamb93", "departement"
    elif zone == "GLP":
        dpts_list, epsg, schema_name, table_name = ["D971"], 5490, "glp_rgaf09utm20", "departement"
    elif zone == "MTQ":
        dpts_list, epsg, schema_name, table_name = ["D972"], 5490, "mtq_rgaf09utm20", "departement"
    elif zone == "GUF":
        dpts_list, epsg, schema_name, table_name = ["D973"], 2972, "guf_utm22rgfg95", "departement"
    elif zone == "REU":
        dpts_list, epsg, schema_name, table_name = ["D974"], 2975, "reu_rgr92utm40s", "departement"
    elif zone == "MYT":
        dpts_list, epsg, schema_name, table_name = ["D975"], 4471, "myt_rgm04utm38s", "departement"
    elif zone == "SPM":
        dpts_list, epsg, schema_name, table_name = ["D976"], 4467, "spm_rgspm06u21", "collectivite_territoriale"
    elif zone == "BLM":
        dpts_list, epsg, schema_name, table_name = ["D977"], 5490, "blm_rgaf09utm20", "collectivite_territoriale"
    elif zone == "MAF":
        dpts_list, epsg, schema_name, table_name = ["D978"], 5490, "maf_rgaf09utm20", "collectivite_territoriale"
    else:
        print('\n' + bold + red + "Error: Zone '%s' is not in the available zones (FXX, GLP, MTQ, GUF, REU, MYT, SPM, BLM, MAF)!" % zone + endC)
        exit(-1)
    if input_epsg_vector != epsg:
        print('\n' + bold + red + "Error: Input vector EPSG (%s) is not the same as reference EPSG (%s) for this zone ('%s')!" % (input_epsg_vector, epsg, zone) + endC)
        exit(-1)

    print('\n' + cyan + "createMnhFromMnsCorrel() : " + bold + green + "Fin de la préparation des traitements." + endC)

    #############################################
    # Gestion des dalles 1 km par département ###
    #############################################

    if (not os.path.exists(output_MNT_raster) or not os.path.exists(output_MNS_raster)) and (not os.path.exists(MNT_vrt) or not os.path.exists(MNS_vrt)):
        print('\n' + cyan + "createMnhFromMnsCorrel() : " + bold + green + "Début de la gestion des dalles 1 km des départements intersectant la zone d'étude." + endC)

        connection = openConnection(DATABASE_NAME, user_name=USER_NAME, password=PASSWORD, ip_host=IP_HOST, num_port=NUM_PORT, schema_name='public')
        data_source_ROI = driver.Open(vector_emprise_input, 0)
        layer_ROI = data_source_ROI.GetLayer(0)
        feature_ROI = layer_ROI.GetFeature(0)
        geometry_ROI = feature_ROI.GetGeometryRef()
        tiles_dpt_ROI_dico = {}
        for dpt in dpts_list:
            select_get_data, where_get_data = "ST_XMin(%s), ST_XMax(%s), ST_YMin(%s), ST_YMax(%s), ST_AsText(%s)" % (GEOM_FIELD, GEOM_FIELD, GEOM_FIELD, GEOM_FIELD, GEOM_FIELD), "%s = '%s'" % (INSEE_FIELD, dpt[2:])
            if zone in (NOT_AVAILABLE_ZONE_LIST):
                schema_name, select_get_data = "fra_wgs84g", "ST_XMin(ST_Transform(%s, %s)), ST_XMax(ST_Transform(%s, %s)), ST_YMin(ST_Transform(%s, %s)), ST_YMax(ST_Transform(%s, %s)), ST_AsText(ST_Transform(%s, %s))" % (GEOM_FIELD, epsg, GEOM_FIELD, epsg, GEOM_FIELD, epsg, GEOM_FIELD, epsg, GEOM_FIELD, epsg)
            get_data_dpt = getData(connection, "%s.%s" % (schema_name, table_name), select_get_data, condition=where_get_data)
            xmin_dpt, xmax_dpt, ymin_dpt, ymax_dpt = math.floor(get_data_dpt[0][0]/TILE_SIZE), math.ceil(get_data_dpt[0][1]/TILE_SIZE), math.floor(get_data_dpt[0][2]/TILE_SIZE), math.ceil(get_data_dpt[0][3]/TILE_SIZE)
            geometry_dpt = ogr.CreateGeometryFromWkt(get_data_dpt[0][4])
            intersect_dpt_ROI = geometry_dpt.Intersects(geometry_ROI.Buffer(-TILE_SIZE/2))
            if intersect_dpt_ROI:
                tiles_list = []
                for x in range(xmin_dpt, xmax_dpt, 1):
                    for y in range(ymin_dpt, ymax_dpt, 1):
                        xmin_tile, xmax_tile, ymin_tile, ymax_tile = x*TILE_SIZE, (x+1)*TILE_SIZE, y*TILE_SIZE, (y+1)*TILE_SIZE
                        geometry_tile = ogr.CreateGeometryFromWkt("POLYGON ((%s %s, %s %s, %s %s, %s %s, %s %s))" % (xmin_tile, ymax_tile, xmax_tile, ymax_tile, xmax_tile, ymin_tile, xmin_tile, ymin_tile, xmin_tile, ymax_tile))
                        intersect_tile_dpt = geometry_tile.Intersects(geometry_dpt)
                        intersect_tile_ROI = geometry_tile.Intersects(geometry_ROI)
                        if intersect_tile_dpt and intersect_tile_ROI:
                            tiles_list.append([int(xmin_tile/TILE_SIZE), int(xmax_tile/TILE_SIZE), int(ymin_tile/TILE_SIZE), int(ymax_tile/TILE_SIZE)])
                tiles_dpt_ROI_dico[dpt] = tiles_list
        data_source_ROI.Destroy()
        closeConnection(connection)

        print('\n' + cyan + "createMnhFromMnsCorrel() : " + bold + green + "Fin de la gestion des dalles 1 km des départements intersectant la zone d'étude." + endC)

    #######################
    ### Création du MNT ###
    #######################

    if not os.path.exists(output_MNT_raster):
        print('\n' + cyan + "createMnhFromMnsCorrel() : " + bold + green + "Début de la création du MNT à partir des données RGE ALTI 1M." + endC)

        if not os.path.exists(MNT_vrt):

            for dpt, tiles_list in tiles_dpt_ROI_dico.items():

                # Gestion de l'archive
                MNT_zip_files_list_selection = [zip_file for zip_file in MNT_zip_files_list if dpt in zip_file]
                if len(MNT_zip_files_list_selection) == 0:
                    raise NameError("Error: There are no MNT archive to treat for the department '%s'!" % dpt)
                elif len(MNT_zip_files_list_selection) == 1:
                    MNT_zip_file = MNT_zip_files_list_selection[0]
                else:
                    MNT_date_list = [datetime.datetime(int(MNT_zip_file.split(os.sep)[-2:-1][0].split('-')[0]), int(MNT_zip_file.split(os.sep)[-2:-1][0].split('-')[1]), int(MNT_zip_file.split(os.sep)[-2:-1][0].split('-')[2])) for MNT_zip_file in MNT_zip_files_list_selection]
                    MNT_date_to_keep = min(MNT_date_list, key = lambda i: abs(i - datetime.datetime(year, 6, 1))).strftime("%Y-%m-%d")
                    MNT_zip_file = [zip_file for zip_file in MNT_zip_files_list_selection if MNT_date_to_keep in zip_file][0]
                MNT_zip_file_structure = read7zArchiveStructure(MNT_zip_file)
                for zip_file_structure in MNT_zip_file_structure:
                    zip_file_structure_split = zip_file_structure.split(os.sep)
                    if len(zip_file_structure_split) == MNT_LENGTH_STRUCTURE and MNT_SEARCH_STRUCTURE_1 in zip_file_structure_split[1] and MNT_SEARCH_STRUCTURE_2 in zip_file_structure_split[2] and MNT_SEARCH_STRUCTURE_3 in zip_file_structure_split[3]:
                        MNT_structure = zip_file_structure
                        break
                MNT_dir_structure = MNT_structure.split(os.sep)
                MNT_file_structure = MNT_dir_structure[4].split(MNT_SPLIT_STRUCTURE)

                # Export des dalles
                for tile in tiles_list:
                    xmin_tile, xmax_tile, ymin_tile, ymax_tile = tile[0], tile[1], tile[2], tile[3]
                    MNT_tile = "0%s%s%s" % (xmin_tile, MNT_SPLIT_STRUCTURE, ymax_tile)
                    if xmin_tile >= 1000:#D004 / D005 / D006 / D02A / D02B / D025 / D054 / D057 / D067 / D068 / D073 / D074 / D083 / D088 / D090
                        MNT_tile = "%s%s%s" % (xmin_tile, MNT_SPLIT_STRUCTURE, ymax_tile)
                    elif xmin_tile < 100:#D029
                        MNT_tile = "00%s%s%s" % (xmin_tile, MNT_SPLIT_STRUCTURE, ymax_tile)
                    MNT_tile_directory = MNT_dir_structure[0] + os.sep + MNT_dir_structure[1] + os.sep + MNT_dir_structure[2] + os.sep + MNT_dir_structure[3]
                    MNT_tile_basename = MNT_file_structure[0] + MNT_SPLIT_STRUCTURE + MNT_file_structure[1] + MNT_SPLIT_STRUCTURE + MNT_tile + MNT_SPLIT_STRUCTURE + MNT_file_structure[4] + MNT_SPLIT_STRUCTURE + MNT_file_structure[5] + MNT_SPLIT_STRUCTURE + MNT_file_structure[6]
                    MNT_tile_file = MNT_tile_directory + os.sep + MNT_tile_basename
                    MNT_new_file = temp_MNT_directory + os.sep + MNT_tile_basename
                    if not os.path.exists(MNT_new_file):
                        os.system("7z e -aos %s -o%s %s" % (MNT_zip_file, temp_MNT_directory, MNT_tile_file))

            # Création du raster virtuel
            vrt_files_list = ""
            for input_MNT in glob.glob(temp_MNT_directory + os.sep + "*"):
                vrt_files_list += input_MNT + '\n'
            writeTextFile(MNT_to_vrt_files, vrt_files_list)
            os.system("gdalbuildvrt -a_srs EPSG:%s -input_file_list %s %s" % (epsg, MNT_to_vrt_files, MNT_vrt))

        # Découpage du MNT
        os.system("gdalwarp -te %s %s %s %s -tr %s %s -cutline %s %s %s" % (xmin_img, ymin_img, xmax_img, ymax_img, pixel_width, pixel_height, vector_emprise_input, MNT_vrt, output_MNT_raster))

        print('\n' + cyan + "createMnhFromMnsCorrel() : " + bold + green + "Fin de la création du MNT à partir des données RGE ALTI 1M." + endC)

    #######################
    ### Création du MNS ###
    #######################

    if not os.path.exists(output_MNS_raster):
        print('\n' + cyan + "createMnhFromMnsCorrel() : " + bold + green + "Début de la création du MNS à partir des données MNS-Correl." + endC)

        if not os.path.exists(MNS_vrt):

            for dpt, tiles_list in tiles_dpt_ROI_dico.items():

                # Gestion de l'archive
                MNS_tile_structure_selection = [structure for structure in MNS_tile_structure if dpt in structure]
                MNS_zip_files_list_selection = [zip_file for zip_file in MNS_zip_files_list if dpt in zip_file]
                if len(MNS_zip_files_list_selection) == 0:
                    raise NameError("Error: There are no MNS archive to treat for the department '%s'!" % dpt)
                elif len(MNS_zip_files_list_selection) == 1:
                    MNS_zip_file = MNS_zip_files_list_selection[0]
                    MNS_tile_structure_selected = MNS_tile_structure_selection[0]
                else:
                    MNS_years_list = [int(MNS_zip_file.split(os.sep)[-2:-1][0]) for MNS_zip_file in MNS_zip_files_list_selection]
                    MNS_year_to_keep = str(MNS_years_list[min(range(len(MNS_years_list)), key = lambda i: abs(MNS_years_list[i] - year))])
                    if str(selected_year-1) in str(MNS_years_list) and str(year+1) in str(MNS_years_list):
                        MNS_year_to_keep = str(year+1)
                    MNS_zip_file = [zip_file for zip_file in MNS_zip_files_list_selection if MNS_year_to_keep in zip_file][0]
                    MNS_tile_structure_selected = [structure for structure in MNS_tile_structure_selection if MNS_year_to_keep in structure][0]
                MNS_zip_file_structure = read7zArchiveStructure(MNS_zip_file)
                for zip_file_structure in MNS_zip_file_structure:
                    zip_file_structure_split = zip_file_structure.split(os.sep)
                    if len(zip_file_structure_split) == MNS_LENGTH_STRUCTURE and MNS_SEARCH_STRUCTURE_1 in zip_file_structure_split[1] and MNS_SEARCH_STRUCTURE_2 in zip_file_structure_split[2] and MNS_SEARCH_STRUCTURE_3 in zip_file_structure_split[3]:
                        MNS_structure = zip_file_structure
                        break
                MNS_dir_structure = MNS_structure.split(os.sep)
                MNS_file_structure = MNS_dir_structure[4].split(MNS_SPLIT_STRUCTURE)

                # Export des dalles
                for tile in tiles_list:
                    xmin_tile, xmax_tile, ymin_tile, ymax_tile = tile[0], tile[1], tile[2], tile[3]
                    ymax_tile = ymax_tile-1 if MNS_tile_structure_selected[5] == MNS_WRONG_TILE_VALUE else ymax_tile
                    MNS_tile = "%s0%s%s" % (xmin_tile, MNS_SPLIT_STRUCTURE, ymax_tile) if MNS_tile_structure_selected[2] == MNS_WRONG_TILE_NAME else "0%s%s%s" % (xmin_tile, MNS_SPLIT_STRUCTURE, ymax_tile)
                    if xmin_tile >= 1000:#D004 / D005 / D006 / D02A / D02B / D025 / D054 / D057 / D067 / D068 / D073 / D074 / D083 / D088 / D090
                        MNS_tile = "%s%s%s" % (xmin_tile, MNS_SPLIT_STRUCTURE, ymax_tile)
                    elif xmin_tile < 100:#D029
                        MNS_tile = "00%s%s%s" % (xmin_tile, MNS_SPLIT_STRUCTURE, ymax_tile)
                    MNS_tile_directory = MNS_dir_structure[0] + os.sep + MNS_dir_structure[1] + os.sep + MNS_dir_structure[2] + os.sep + MNS_dir_structure[3]
                    MNS_tile_basename = MNS_file_structure[0] + MNS_SPLIT_STRUCTURE + MNS_file_structure[1] + MNS_SPLIT_STRUCTURE + MNS_tile + MNS_SPLIT_STRUCTURE + MNS_file_structure[4] + MNS_SPLIT_STRUCTURE + MNS_file_structure[5]
                    MNS_tile_file = MNS_tile_directory + os.sep + MNS_tile_basename
                    MNS_new_file = temp_MNS_directory + os.sep + MNS_tile_basename
                    if not os.path.exists(MNS_new_file):
                        os.system("7z e -aos %s -o%s %s" % (MNS_zip_file, temp_MNS_directory, MNS_tile_file))

            # Création du raster virtuel
            vrt_files_list = ""
            for input_MNS in glob.glob(temp_MNS_directory + os.sep + "*"):
                vrt_files_list += input_MNS + '\n'
            writeTextFile(MNS_to_vrt_files, vrt_files_list)
            os.system("gdalbuildvrt -input_file_list %s %s" % (MNS_to_vrt_files, MNS_vrt))

        # Découpage du MNS
        os.system("gdalwarp -te %s %s %s %s -tr %s %s -dstnodata 0 -cutline %s %s %s" % (xmin_img, ymin_img, xmax_img, ymax_img, pixel_width, pixel_height, vector_emprise_input, MNS_vrt, output_MNS_raster))

        print('\n' + cyan + "createMnhFromMnsCorrel() : " + bold + green + "Fin de la création du MNS à partir des données MNS-Correl." + endC)

    #####################
    ### Calcul du MNH ###
    #####################

    print('\n' + cyan + "createMnhFromMnsCorrel() : " + bold + green + "Début du calcul du MNH à partir du MNT RGE ALTI 1M et du MNS MNS-Correl." + endC)

    expression = "im1b1<=-9999 or im1b1>=9999 or im2b1<=-9999 or im2b1>=9999 ? -1 : (im1b1-im2b1<0 ? 0 : im1b1-im2b1)"
    os.system("otbcli_BandMath -il %s %s -out '%s?&nodata=-1' -exp '%s'" % (output_MNS_raster, output_MNT_raster, image_mnh_output, expression))

    print('\n' + cyan + "createMnhFromMnsCorrel() : " + bold + green + "Fin du calcul du MNH à partir du MNT RGE ALTI 1M et du MNS MNS-Correl." + endC)

    ####################################################################

    # Suppression des fichiers temporaires
    if not save_results_intermediate:
        if debug >= 3:
            print('\n' + cyan + "createMnhFromMnsCorrel() : " + endC + "Suppression des fichiers temporaires." + endC)
        deleteDir(temp_directory)

    print('\n' + cyan + "createMnhFromMnsCorrel() : " + bold + green + "FIN DES TRAITEMENTS" + endC)

    # Mise à jour du log
    ending_event = "createMnhFromMnsCorrel() : Fin du traitement : "
    timeLine(path_time_log, ending_event)

    return 0

###########################################################################################################################################
# MISE EN PLACE DU PARSER                                                                                                                 #
###########################################################################################################################################

# Code executé seulement dans le cas ou le script est lancé depuis une ligne de commande
# Il n'est pas executé lors d'un import MnhCreation.py
# Exemples de lancement en ligne de commande :
# python -m MnhCreation -is /mnt/RAM_disk/MNS_50cm.tif -it /mnt/RAM_disk/MNT_1m.tif -ithr /mnt/Data/10_Agents_travaux_en_cours/Gilles/Test_QualityMNS/Bordeaux_Metropole_Est_NDVI.tif -v /mnt/RAM_disk/emprise2.shp -o /mnt/RAM_disk/MNH_zone_test.tif -bias 0.8  -ibdrl /mnt/Geomatique/REF_GEO/BD_Topo/D33/ED16/SHP/1_DONNEES_LIVRAISON/A_VOIES_COMM_ROUTE/N_ROUTE_PRIMAIRE_BDT_033.SHP /mnt/Geomatique/REF_GEO/BD_Topo/D33/ED16/SHP/1_DONNEES_LIVRAISON/A_VOIES_COMM_ROUTE/N_ROUTE_SECONDAIRE_BDT_033.SHP -bufrl 5.0 3.0  -sqlrl "FRANCHISST != 'Tunnel'":"FRANCHISST != 'Tunnel'" -thrval 0.25 -log /mnt/RAM_disk/fichierTestLog.txt
# python -m MnhCreation -is /mnt/Geomatique/REF_DTER_OCC/MNS_Correl -it /mnt/Geomatique/REF_DTER_OCC/RGE_ALTI/RGE_ALTI_1M -iref /mnt/RAM_disk/MnhCreationFromMnsCorrel/reference.tif -v /mnt/RAM_disk/MnhCreationFromMnsCorrel/ROI.shp -o /mnt/RAM_disk/MnhCreationFromMnsCorrel/MNH.tif -year 2022 -zone FXX

def main(gui=False):

    # Définition des différents paramètres du parser
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,  prog="MnhCreation", description="\
    Info : Create MNH raster file from difference between MNS et MNT. \n\
    Objectif : Creer un MNH fichier raster difference du MNS et du MNT. \n\
    Example : python -m MnhCreation -is /mnt/RAM_disk/MNS_50cm.tif  \n\
                                    -it /mnt/RAM_disk/MNT_1m.tif  \n\
                                    -ithr /mnt/Data/10_Agents_travaux_en_cours/Gilles/Test_QualityMNS/Bordeaux_Metropole_Est_NDVI.tif  \n\
                                    -v /mnt/RAM_disk/emprise2.shp  \n\
                                    -o /mnt/RAM_disk/MNH_zone_test.tif  \n\
                                    -bias 0.8   \n\
                                    -ibdrl /mnt/Geomatique/REF_GEO/BD_Topo/D33/ED16/SHP/1_DONNEES_LIVRAISON/A_VOIES_COMM_ROUTE/N_ROUTE_PRIMAIRE_BDT_033.SHP  \n\
                                           /mnt/Geomatique/REF_GEO/BD_Topo/D33/ED16/SHP/1_DONNEES_LIVRAISON/A_VOIES_COMM_ROUTE/N_ROUTE_SECONDAIRE_BDT_033.SHP  \n\
                                    -bufrl 5.0 3.0   \n\
                                    -thrval 0.25  \n\
                                    -ibdbl /mnt/Geomatique/REF_GEO/BD_Topo/D33/ED16/SHP/1_DONNEES_LIVRAISON/E_BATI/N_BATI_INDIFFERENCIE_BDT_033.SHP \n\
                                           /mnt/Geomatique/REF_GEO/BD_Topo/D33/ED16/SHP/1_DONNEES_LIVRAISON/E_BATI/N_BATI_INDUSTRIEL_BDT_033.SHP \n\
                                           /mnt/Geomatique/REF_GEO/BD_Topo/D33/ED16/SHP/1_DONNEES_LIVRAISON/E_BATI/N_BATI_REMARQUABLE_BDT_033.SHP \n\
                                    -deltah 2.0  \n\
                                    -log /mnt/RAM_disk/fichierTestLog.txt \n\
              python -m MnhCreation -is /mnt/Geomatique/REF_DTER_OCC/MNS_Correl \n\
                                    -it /mnt/Geomatique/REF_DTER_OCC/RGE_ALTI/RGE_ALTI_1M \n\
                                    -iref /mnt/RAM_disk/MnhCreationFromMnsCorrel/reference.tif \n\
                                    -v /mnt/RAM_disk/MnhCreationFromMnsCorrel/ROI.shp \n\
                                    -o /mnt/RAM_disk/MnhCreationFromMnsCorrel/MNH.tif \n\
                                    -year 2022 \n\
                                    -zone FXX")

    parser.add_argument('-is','--image_mns_input',default="",help="Image MNS input, or Input MNS archives directory for MNH creation with MNS-Correl.", type=str, required=True)
    parser.add_argument('-it','--image_mnt_input',default="",help="Image MNT input, or Input MNT archives directory for MNH creation with MNS-Correl.", type=str, required=True)
    parser.add_argument('-ithr','--image_threshold_input',default="",help="Image threshold BD road input", type=str, required=False)
    parser.add_argument('-iref','--image_reference_input',default="",help="Input reference image for MNH creation with MNS-Correl.", type=str, required=False)
    parser.add_argument('-v','--vector_emprise_input',default="",help="Input emprise vector study.", type=str, required=True)
    parser.add_argument('-o','--image_mnh_output',default="",help="MNH (Model Numerique de Hauteur) image output.", type=str, required=True)
    parser.add_argument('-auto','--automatic',action='store_true',default=False,help="Select mode automatic with out user. By default, False", required=False)
    parser.add_argument('-ibdrl','--bd_road_vector_input_list',default=None,nargs="+",help="List containt road bd vector input concatened to create vector road", type=str, required=False)
    parser.add_argument('-bufrl','--bd_road_buff_list',default=None,nargs='+',help="List containt value buffer for road bd vector input.ex 1.0 2.0 5.3", type=float, required=False)
    parser.add_argument('-sqlrl','--sql_road_expression_list',default=None,help="List containt sql expression to filter road db input (separator is ':' and not used \" for string value)", type=str, required=False)
    parser.add_argument('-ibdbl','--bd_build_vector_input_list',default=None,nargs="+",help="List containt build bd vector input concatened to create vector sample", type=str, required=False)
    parser.add_argument('-bias','--height_bias',default=0.0,help="Value of height bias to compute MNH : 0 ",type=float, required=False)
    parser.add_argument('-thrval','--threshold_bd_value',default=0.25,help="Parameter value of threshold  BD road file. By default : 0.25", type=float, required=False)
    parser.add_argument('-deltah','--threshold_delta_h',default=2.0,help="Value of threshold compute delta H between BUILD and MNH, Default : 2.0 m ",type=float, required=False)
    parser.add_argument('-modi','--mode_interpolation',default="default",help="Option : Mode interpolation used (Choice of : 'Default mode (default)', 'Pleiades mode (phr)'). By default, 'default'.", type=str, required=False)
    parser.add_argument('-methi','--method_interpolation',default="bco",help="Option : Algo method interpolation used (Choice of : 'Bicubic interpolation (bco)', 'Nearest Neighbor interpolation (nn)', 'Linear interpolation (linear)'). By default, 'bco'.", type=str, required=False)
    parser.add_argument('-interp.bco.r','--interpolation_bco_radius',default=2,help="Option : Radius for bicubic interpolation parameter", type=int, required=False)
    parser.add_argument('-simp','--simplify_vector_param',default=10.0,help="Parameter of polygons simplification. By default : 10.0", type=float, required=False)
    parser.add_argument('-year', '--year', choices=range(2000,2050), default=2022, type=int, required=False, help="Year to be treated to produce MNH with MNS-Correl. Default: 2022.")
    parser.add_argument('-zone', '--zone', choices=["FXX","GLP","MTQ","GUF","REU","MYT","SPM","BLM","MAF"], default="FXX", type=str, required=False, help="Zone to be treated to produce MNH with MNS-Correl. Default: 'FXX'.")
    parser.add_argument("-epsg",'--epsg',default=0,help="Option : Projection parameter of data if 0 used projection of raster file", type=int, required=False)
    parser.add_argument("-ndv",'--no_data_value',default=0,help="Option : Pixel value for raster file to no data, default : 0 ", type=int, required=False)
    parser.add_argument('-ram','--ram_otb',default=0,help="Ram available for processing otb applications (in MB)", type=int, required=False)
    parser.add_argument('-raf','--format_raster', default="GTiff", help="Option : Format output image, by default : GTiff (GTiff, HFA...)", type=str, required=False)
    parser.add_argument('-vef','--format_vector', default="ESRI Shapefile",help="Format of the output file.", type=str, required=False)
    parser.add_argument('-rae','--extension_raster', default=".tif", help="Option : Extension file for image raster. By default : '.tif'", type=str, required=False)
    parser.add_argument('-vee','--extension_vector',default=".shp",help="Option : Extension file for vector. By default : '.shp'", type=str, required=False)
    parser.add_argument('-log','--path_time_log',default="",help="Name of log", type=str, required=False)
    parser.add_argument('-sav','--save_results_inter',action='store_true',default=False,help="Save or delete intermediate result after the process. By default, False", required=False)
    parser.add_argument('-now','--overwrite',action='store_false',default=True,help="Overwrite files with same names. By default, True", required=False)
    parser.add_argument('-debug','--debug',default=3,help="Option : Value of level debug trace, default : 3 ",type=int, required=False)
    args = displayIHM(gui, parser)

    # RECUPERATION DES ARGUMENTS

    # Récupération de l'image MNS d'entrée/du répertoire de stockage des archives MNS-Correl
    if args.image_mns_input != None:
        image_mns_input = args.image_mns_input
        if not os.path.exists(image_mns_input):
            raise NameError (cyan + "MnhCreation : " + bold + red  + "File/Directory %s not existe!" %(image_mns_input) + endC)

    # Récupération de l'image MNT d'entrée/du répertoire de stockage des archives RGE ALTI 1M
    if args.image_mnt_input != None:
        image_mnt_input = args.image_mnt_input
        if not os.path.exists(image_mnt_input):
            raise NameError (cyan + "MnhCreation : " + bold + red  + "File/Directory %s not existe!" %(image_mnt_input) + endC)

    # Récupération de l'image de filtrage d'entrée
    if args.image_threshold_input != None:
        image_threshold_input = args.image_threshold_input

    # Récupération de l'image de référence d'entrée
    if args.image_reference_input != None:
        image_reference_input = args.image_reference_input

    # Récupération du vecteur d'entrée
    if args.vector_emprise_input != None :
        vector_emprise_input = args.vector_emprise_input
        if not os.path.isfile(vector_emprise_input):
            raise NameError (cyan + "MnhCreation : " + bold + red  + "File %s not existe!" %(vector_emprise_input) + endC)

    # Récupération de l'image MNT de sortie
    if args.image_mnh_output!= None:
        image_mnh_output=args.image_mnh_output

    # Récupération de la valeur du mode automatique
    if args.automatic!= None:
        automatic = args.automatic

    # Récupération des vecteurs de bd routes
    if args.bd_road_vector_input_list != None :
        bd_road_vector_input_list = args.bd_road_vector_input_list
    else :
        bd_road_vector_input_list = []

    # liste des valeurs des buffers associés au traitement des vecteurs de bd routes
    if args.bd_road_buff_list != None:
        bd_road_buff_list = args.bd_road_buff_list
        if len(bd_road_buff_list) != len(bd_road_vector_input_list) :
             raise NameError (cyan + "MacroSamplesCreation : " + bold + red  + "List buffer value  size %d is differente at size bd road vector input list!" %(len(bd_road_buff_list)) + endC)
    else :
        bd_road_buff_list = []

    # liste des expression sql pour filtrer les vecteurs de bd routes
    if args.sql_road_expression_list != None:
        sql_road_expression_list = args.sql_road_expression_list.replace('"','').split(":")
        if len(sql_road_expression_list) != len(bd_road_vector_input_list) :
             raise NameError (cyan + "MacroSamplesCreation : " + bold + red  + "List sql expression size %d is differente at size bd road vector input list!" %(len(sql_road_expression_list)) + endC)
    else :
        sql_road_expression_list = []

    # Récupération des vecteurs de bd bati
    if args.bd_build_vector_input_list != None :
        bd_build_vector_input_list = args.bd_build_vector_input_list
    else :
        bd_build_vector_input_list = []

    # Récupération de la valeur du biais en hauteur
    if args.height_bias != None:
        height_bias = args.height_bias

    # Paramettre valeur de seuillage de la BD route
    if args.threshold_bd_value != None:
        threshold_bd_value = args.threshold_bd_value

    # Récupération de la valeur de seuillage du delta H
    if args.threshold_delta_h != None:
        threshold_delta_h = args.threshold_delta_h

    # Récupération du parametre mode interpolation
    if args.mode_interpolation != None:
        mode_interpolation = args.mode_interpolation

    # Récupération du parametre methode interpolation
    if args.method_interpolation != None:
        method_interpolation = args.method_interpolation

    # Récupération du parametre radius pour l'interpolation bicubic
    if args.interpolation_bco_radius!= None:
        interpolation_bco_radius = args.interpolation_bco_radius

    # Récupération du parametre simplify_vector_param
    if args.simplify_vector_param != None:
        simplify_vector_param = args.simplify_vector_param

    # Récupération des paramètres liés à la production MNH à partir de MNS-Correl
    if args.year != None:
        year = args.year
    if args.zone != None:
        zone = args.zone

    # Paramettre de projection
    if args.epsg != None:
        epsg = args.epsg

    # Paramettre des no data
    if args.no_data_value != None:
        no_data_value = args.no_data_value

    # Récupération du parametre ram
    if args.ram_otb != None:
        ram_otb = args.ram_otb

    # Paramètre format des images de sortie
    if args.format_raster != None:
        format_raster = args.format_raster

    # Récupération du format du fichier de sortie
    if args.format_vector != None :
        format_vector = args.format_vector

    # Paramètre de l'extension des images rasters
    if args.extension_raster != None:
        extension_raster = args.extension_raster

    # Récupération de l'extension des fichiers vecteurs
    if args.extension_vector != None:
        extension_vector = args.extension_vector

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
        print(bold + green + "MnhCreation : Variables dans le parser" + endC)
        print(cyan + "MnhCreation : " + endC + "image_mns_input : " + str(image_mns_input) + endC)
        print(cyan + "MnhCreation : " + endC + "image_mnt_input : " + str(image_mnt_input) + endC)
        print(cyan + "MnhCreation : " + endC + "image_threshold_input : " + str(image_threshold_input) + endC)
        print(cyan + "MnhCreation : " + endC + "image_reference_input : " + str(image_reference_input) + endC)
        print(cyan + "MnhCreation : " + endC + "vector_emprise_input : " + str(vector_emprise_input) + endC)
        print(cyan + "MnhCreation : " + endC + "image_mnh_output : " + str(image_mnh_output) + endC)
        print(cyan + "MnhCreation : " + endC + "automatic : " + str(automatic) + endC)
        print(cyan + "MnhCreation : " + endC + "bd_road_vector_input_list : " + str(bd_road_vector_input_list) + endC)
        print(cyan + "MnhCreation : " + endC + "bd_road_buff_list : " + str(bd_road_buff_list) + endC)
        print(cyan + "MnhCreation : " + endC + "sql_road_expression_list : " + str(sql_road_expression_list) + endC)
        print(cyan + "MnhCreation : " + endC + "bd_build_vector_input_list : " + str(bd_build_vector_input_list) + endC)
        print(cyan + "MnhCreation : " + endC + "height_bias : " + str(height_bias) + endC)
        print(cyan + "MnhCreation : " + endC + "threshold_bd_value : " + str(threshold_bd_value) + endC)
        print(cyan + "MnhCreation : " + endC + "threshold_delta_h : " + str(threshold_delta_h) + endC)
        print(cyan + "MnhCreation : " + endC + "mode_interpolation : " + str(mode_interpolation) + endC)
        print(cyan + "MnhCreation : " + endC + "method_interpolation : " + str(method_interpolation) + endC)
        print(cyan + "MnhCreation : " + endC + "interpolation_bco_radius : " + str(interpolation_bco_radius) + endC)
        print(cyan + "MnhCreation : " + endC + "simplify_vector_param : " + str(simplify_vector_param) + endC)
        print(cyan + "MnhCreation : " + endC + "year : " + str(year) + endC)
        print(cyan + "MnhCreation : " + endC + "zone : " + str(zone) + endC)
        print(cyan + "MnhCreation : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "MnhCreation : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "MnhCreation : " + endC + "ram_otb : " + str(ram_otb) + endC)
        print(cyan + "MnhCreation : " + endC + "format_raster : " + str(format_raster) + endC)
        print(cyan + "MnhCreation : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "MnhCreation : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "MnhCreation : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "MnhCreation : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "MnhCreation : " + endC + "save_results_inter : " + str(save_results_intermediate) + endC)
        print(cyan + "MnhCreation : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "MnhCreation : " + endC + "debug : " + str(debug) + endC)

    # EXECUTION DE LA FONCTION
    # Si les dossiers de sortie n'existent pas, on les crées
    repertory_output = os.path.dirname(image_mnh_output)
    if not os.path.isdir(repertory_output):
        os.makedirs(repertory_output)

    # Exécution si création du MNH à partir de MNT et MNS déjà créés (fichiers en entrée)
    if os.path.isfile(image_mns_input) and os.path.isfile(image_mnt_input):
        createMnh(image_mns_input, image_mnt_input, image_threshold_input, vector_emprise_input, image_mnh_output, automatic, bd_road_vector_input_list, bd_road_buff_list, sql_road_expression_list, bd_build_vector_input_list, height_bias, threshold_bd_value, threshold_delta_h, mode_interpolation, method_interpolation, interpolation_bco_radius, simplify_vector_param, epsg, no_data_value, ram_otb, path_time_log, format_raster, format_vector, extension_raster, extension_vector, save_results_intermediate, overwrite)

    # Exécution si création du MNH à partir du MNS-Correl (image_mnt_input et image_mns_input sont des répertoires et non des fichiers)
    else:
        createMnhFromMnsCorrel(vector_emprise_input, image_mnh_output, image_reference_input, image_mnt_input, image_mns_input, year, zone, path_time_log, save_results_intermediate, overwrite)

# ================================================

if __name__ == '__main__':
  main(gui=False)
