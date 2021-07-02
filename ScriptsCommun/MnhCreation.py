#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerSO/DALETT/SCGSI  All rights reserved.                                                                            #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT QUI CREER UN MNH A PARTIR D'UN MNS (APRES AMELIORATION) D'UN MNT ET DE DONNEES VECTEUR COMME LA BDTOPO ROUTE                       #
#                                                                                                                                           #
#############################################################################################################################################
'''
Nom de l'objet : MnhCreation.py
Description :
    Objectif : Créer un fichier raster de MNH (Model Numerique de Hauteur)
    Rq : utilisation des OTB Applications : otbcli_BandMath, otbcli_Rasterization, otbcli_Superimpose

Date de creation : 1/06/2018
----------
Histoire :
----------

A Reflechir/A faire
 -
 -
'''

from __future__ import print_function
from builtins import input
import os,sys,glob,argparse,string,ogr
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_log import timeLine
from Lib_file import removeFile, removeVectorFile, cleanTempData, deleteDir
from Lib_raster import getNodataValueImage, countPixelsOfValue, cutImageByVector, createBinaryMask, rasterizeBinaryVector, rasterizeVector
from Lib_vector import cutoutVectors, fusionVectors, addNewFieldVector, getAttributeValues, setAttributeIndexValuesList, filterSelectDataVector
from Lib_saga import fillNodata
from MacroSamplesCreation import createMacroSamples
from CrossingVectorRaster import statisticsVectorRaster

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 3

###########################################################################################################################################
# FONCTION createMnh()                                                                                                                   #
###########################################################################################################################################
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

def createMnh(image_mns_input, image_mnt_input, image_threshold_input, vector_emprise_input, image_mnh_output, automatic, bd_road_vector_input_list, bd_road_buff_list, sql_road_expression_list, bd_build_vector_input_list, height_bias, threshold_bd_value, threshold_delta_h, mode_interpolation, method_interpolation, interpolation_bco_radius, simplify_vector_param, epsg, no_data_value, ram_otb, path_time_log, format_raster='GTiff', format_vector='ESRI Shapefile', extension_raster=".tif", extension_vector=".shp", save_results_intermediate=False, overwrite=True):

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
        if not cutImageByVector(vector_emprise_input, image_mns_input, image_mns_cut, None, None, no_data_value, epsg, format_raster, format_vector) :
            raise NameError (cyan + "createMnh() : " + bold + red + "!!! Une erreur c'est produite au cours du decoupage de l'image : " + image_mns_input + ". Voir message d'erreur." + endC)

        # Fonction de découpe du mnt
        if not cutImageByVector(vector_emprise_input, image_mnt_input, image_mnt_cut, None, None, no_data_value, epsg, format_raster, format_vector) :
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
            if not cutImageByVector(vector_emprise_input, image_threshold_input, image_threshold_cut, None, None, no_data_value, epsg, format_raster, format_vector) :
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
        if not cutImageByVector(vector_emprise_input, image_mnh_tmp, image_mnh_road, None, None, no_data_value, epsg, format_raster, format_vector) :
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
            statisticsVectorRaster(image_mnh_road, vector_bd_bati_temp, "", 1, False, False, True, ['PREC_PLANI','PREC_ALTI','ORIGIN_BAT','median','sum','std','unique','range'], [], {}, path_time_log, True, format_vector, save_results_intermediate, overwrite)

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

###########################################################################################################################################
# MISE EN PLACE DU PARSER                                                                                                                 #
###########################################################################################################################################

# Code executé seulement dans le cas ou le script est lancé depuis une ligne de commande
# Il n'est pas executé lors d'un import MnhCreation.py
# Exemple de lancement en ligne de commande:
# python -m MnhCreation -is /mnt/RAM_disk/MNS_50cm.tif -it /mnt/RAM_disk/MNT_1m.tif -ithr /mnt/Data/10_Agents_travaux_en_cours/Gilles/Test_QualityMNS/Bordeaux_Metropole_Est_NDVI.tif -v /mnt/RAM_disk/emprise2.shp -o /mnt/RAM_disk/MNH_zone_test.tif -bias 0.8  -ibdrl /mnt/Geomatique/REF_GEO/BD_Topo/D33/ED16/SHP/1_DONNEES_LIVRAISON/A_VOIES_COMM_ROUTE/N_ROUTE_PRIMAIRE_BDT_033.SHP /mnt/Geomatique/REF_GEO/BD_Topo/D33/ED16/SHP/1_DONNEES_LIVRAISON/A_VOIES_COMM_ROUTE/N_ROUTE_SECONDAIRE_BDT_033.SHP -bufrl 5.0 3.0  -sqlrl "FRANCHISST != 'Tunnel'":"FRANCHISST != 'Tunnel'" -thrval 0.25 -log /mnt/RAM_disk/fichierTestLog.txt

def main(gui=False):

    # Définition des différents paramètres du parser
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,  prog="MnhCreation", description="\
    Info : Transform an image into binary mask under polygons of cutting. \n\
    Objectif : Creer un mnh fichier raster difference du MNS et du mnt. \n\
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
                                    -log /mnt/RAM_disk/fichierTestLog.txt")

    parser.add_argument('-is','--image_mns_input',default="",help="Image MNS input", type=str, required=True)
    parser.add_argument('-it','--image_mnt_input',default="",help="Image MNT input", type=str, required=True)
    parser.add_argument('-ithr','--image_threshold_input',default="",help="Image threshold BD road input", type=str, required=False)
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

    # Récupération de l'image MNS d'entrée
    if args.image_mns_input != None:
        image_mns_input = args.image_mns_input
        if not os.path.isfile(image_mns_input):
            raise NameError (cyan + "MnhCreation : " + bold + red  + "File %s not existe!" %(image_mns_input) + endC)

    # Récupération de l'image MNT d'entrée
    if args.image_mnt_input != None:
        image_mnt_input = args.image_mnt_input
        if not os.path.isfile(image_mnt_input):
            raise NameError (cyan + "MnhCreation : " + bold + red  + "File %s not existe!" %(image_mnt_input) + endC)

    # Récupération de l'image de filtrage d'entrée
    if args.image_threshold_input != None:
        image_threshold_input = args.image_threshold_input

    # Récupération des vecteurs d'entrée
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

    # execution de la fonction pour une image
    createMnh(image_mns_input, image_mnt_input, image_threshold_input, vector_emprise_input, image_mnh_output, automatic, bd_road_vector_input_list, bd_road_buff_list, sql_road_expression_list, bd_build_vector_input_list, height_bias, threshold_bd_value, threshold_delta_h, mode_interpolation, method_interpolation, interpolation_bco_radius, simplify_vector_param, epsg, no_data_value, ram_otb, path_time_log, format_raster, format_vector, extension_raster, extension_vector, save_results_intermediate, overwrite)

# ================================================

if __name__ == '__main__':
  main(gui=False)
