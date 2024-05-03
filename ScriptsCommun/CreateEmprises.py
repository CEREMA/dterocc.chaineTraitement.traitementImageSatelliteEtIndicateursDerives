#! /usr/bin/python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT CREANT UN SHAPEFILE CONTENANT LES EMPRISES D'IMAGES SATELITE                                                                       #
#                                                                                                                                           #
#############################################################################################################################################
"""
Nom de l'objet : CreateEmprises.py
Description :
-------------
Objectif   : Création d'emprises d'images Pléiades, sans assemblage

Date de creation : 04/07/2016
----------
Histoire :
----------
Origine : nouveau

-----------------------------------------------------
Modifications :

------------------------------------------------------
A Reflechir/A faire :

"""

# IMPORTS DIVERS
from __future__ import print_function
import sys,os,glob,re,types,shutil,copy, argparse
from time import *
from osgeo import ogr
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_raster import getEmpriseImage, getPixelSizeImage, polygonizeRaster, getNodataValueImage, createBinaryMaskMultiBand, h5ToGtiff
from Lib_vector import createPolygonsFromCoordList, geometries2multigeometries, fusionNeighbourGeometryBySameValue, dissolveVector, getGeomPolygons, createPolygonsFromGeometryList, cleanMiniAreaPolygons, simplifyVector, bufferVector, cleanRingVector
from Lib_file import removeFile, removeVectorFile, copyVectorFile, getSubRepRecursifList

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 3 : affichage maximum de commentaires lors de l'execution du script. Intermédiaire : affichage intermédiaire
debug = 3

#########################################################################
# FONCTION createEmprise()                                              #
#########################################################################
def createEmprise(repertory_input_list, output_vector, is_not_assembled, is_all_polygons_used, is_not_date, is_optimize_emprise, is_optimize_emprise_nodata, no_data_value, size_erode, path_time_log, separ_name="_", pos_date=1, nb_char_date=8, separ_date="", epsg=2154, format_vector='ESRI Shapefile', extension_raster=".tif", extension_vector=".shp", save_results_intermediate=False, overwrite=True):
    """
    #   Rôle : Cette fonction permet de créer une couche vecteur à partir des emprises des imagettes raster de fichiers (sans assembler les imagettes)
    #   paramètres :
    #       repertory_input_list : liste de dossier contenant les différents dossiers d'images (contenant eux-mêmes les imagettes)
    #       output_vector : fichier vecteur de sortie contenant les polygones des emprises des images
    #       is_not_assembled : Option : Les emprises des images ne sont pas assemblées
    #       is_all_polygons_used : Option : Tout les polygones trouvés sont utilisés
    #       is_not_date : Option : Les emprises des images ne gérent pas les dates des images
    #       is_optimize_emprise : Creer une version de l'emprise des images par dossier plus optimisé
    #       is_optimize_emprise_nodata : Creer une version de l'emprise des images sans les no data
    #       no_data_value : Option : Value pixel of no data
    #       size_erode : taille du buffer d'erosion du polygone d'emprise en metre pour l'option is_optimize_emprise_nodata
    #       path_time_log : le fichier de log de sortie
    #       separ_name : Paramètre date acquisition dans le nom, séparateur d'information
    #       pos_date : Paramètre date acquisition dans le nom, position relatif au séparateur d'information
    #       nb_char_date : Paramètre date acquisition dans le nom, nombre de caractères constituant la date
    #       separ_date : Paramètre date acquisition dans le nom, séparateur dans l'information date
    #       epsg : Optionnel : par défaut 2154
    #       format_vector : format du fichier vecteur. Optionnel, par default : 'ESRI Shapefile'
    #       extension_raster : extension des fichiers raster de sortie, par defaut = '.tif'
    #       extension_vector : extension du fichier vecteur de sortie, par defaut = '.shp'
    #       save_results_intermediate : fichiers de sorties intermediaires non nettoyées, par defaut = False
    #       overwrite : supprime ou non les fichiers existants ayant le meme nom
    """

    # Affichage des paramètres
    if debug >= 3:
        print(bold + green + "Variables dans le createEmprise - Variables générales" + endC)
        print(cyan + "createEmprise() : " + endC + "input_dir : " + str(repertory_input_list))
        print(cyan + "createEmprise() : " + endC + "output_vector : " + str(output_vector))
        print(cyan + "createEmprise() : " + endC + "is_not_assembled : " + str(is_not_assembled))
        print(cyan + "createEmprise() : " + endC + "is_all_polygons_used : " + str(is_all_polygons_used))
        print(cyan + "createEmprise() : " + endC + "is_not_date : " + str(is_not_date))
        print(cyan + "createEmprise() : " + endC + "is_optimize_emprise : " + str(is_optimize_emprise))
        print(cyan + "createEmprise() : " + endC + "is_optimize_emprise_nodata : " + str(is_optimize_emprise_nodata))
        print(cyan + "createEmprise() : " + endC + "no_data_value : " + str(no_data_value))
        print(cyan + "createEmprise() : " + endC + "size_erode : " + str(size_erode))
        print(cyan + "createEmprise() : " + endC + "path_time_log : " + str(path_time_log))
        print(cyan + "createEmprise() : " + endC + "separ_name : " + str(separ_name))
        print(cyan + "createEmprise() : " + endC + "pos_date : " + str(pos_date))
        print(cyan + "createEmprise() : " + endC + "nb_char_date : " + str(nb_char_date))
        print(cyan + "createEmprise() : " + endC + "separ_date : " + str(separ_date))
        print(cyan + "createEmprise() : " + endC + "epsg : " + str(epsg))
        print(cyan + "createEmprise() : " + endC + "format_vector : " + str(format_vector))
        print(cyan + "createEmprise() : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "createEmprise() : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "createEmprise() : " + endC + "save_results_intermediate : "+ str(save_results_intermediate))
        print(cyan + "createEmprise() : " + endC + "overwrite : "+ str(overwrite))

   # Constantes
    EXT_LIST_HDF5 = ['h5','H5', 'he5', 'HE5', 'hdf5', 'HDF5']
    EXT_LIST = EXT_LIST_HDF5 + ['tif','TIF','tiff','TIFF','ecw','ECW','jp2','JP2','dim','DIM','asc','ASC']
    SUFFIX_DETAILLEE = "_detail"
    SUFFIX_CLEAN = "_clean"
    SUFFIX_MASK_ZERO = "_mask_zeros"
    SUFFIX_TMP = "_tmp"

    CODAGE_8B = "uint8"
    ATTR_NAME_ID = "Id"
    ATTR_NAME_NOMIMAGE = "NomImage"
    ATTR_NAME_DATEACQUI = "DateAcqui"
    ATTR_NAME_HEUREACQUI = "HeureAcqui"
    ATTR_NAME_REFDOSSIER = "RefDossier"
    SUFFIX_IMGSAT = 'Img_Sat_'
    PREFIX_ASS = '_ass'
    PREFIX_OPT = '_opti_'

    # Variables
    points_list = []
    name_image_list = []
    name_rep_list = []
    ref_dossier_list = []
    date_list = []
    heure_list = []
    optimize_emprise_nodata_shape_list = []
    polygons_attr_coord_dico = {}
    pos_date = pos_date - 1
    size_pixel = 0.0

    repertory_output = os.path.dirname(output_vector)
    file_name = os.path.splitext(os.path.basename(output_vector))[0]
    extension = os.path.splitext(output_vector)[1]
    file_vector_detail = repertory_output + os.sep + file_name + SUFFIX_DETAILLEE + extension
    file_vector_clean = repertory_output + os.sep + file_name + SUFFIX_CLEAN + extension

    # Si un fichier de sortie avec le même nom existe déjà, et si l'option ecrasement est à false, alors passe au masque suivant
    check = os.path.isfile(output_vector)
    if check and not overwrite:
        print(bold + yellow +  "createEmprise() : " + endC + "Le fichier vecteur d'emprise %s existe déjà : pas d'actualisation" % (output_vector) + endC)
    # Si non, ou si la fonction ecrasement est désative, alors on le calcule
    else:
        if check:
            try: # Suppression de l'éventuel fichier existant
                removeVectorFile(output_vector)
                removeVectorFile(file_vector_detail)
            except Exception:
                pass # Si le fichier ne peut pas être supprimé, on suppose qu'il n'existe pas et on passe à la suite

        # Récuperer tous les sous répertoires
        sub_rep_list = []
        for input_dir in repertory_input_list:
            rep_sub_rep_list = getSubRepRecursifList(input_dir)
            sub_rep_list.append(input_dir)
            for sub_repertory in rep_sub_rep_list:
                sub_rep_list.append(sub_repertory)

        # Parcours de chaque dossier image du dossier en entrée
        for repertory in sub_rep_list:
            if os.path.isdir(repertory):

                if debug >= 2:
                    print(cyan + "createEmprises() : " + endC + bold + green  + "Traitement de : " + endC + repertory)

                # Récupération des images du dossier en entrée
                imagettes_jp2_tif_ecw_list = []
                imagettes_list = os.listdir(repertory)

                for elt1 in imagettes_list:
                    path_image = repertory + os.sep + elt1
                    if (os.path.isfile(path_image)) and (len(elt1.rsplit('.',1)) == 2) and (elt1.rsplit('.',1)[1] in EXT_LIST) :
                        if elt1.rsplit('.',1)[1] in EXT_LIST_HDF5:
                            elt1_new = os.path.splitext(elt1)[0] + extension_raster
                            path_image_new = repertory + os.sep + elt1_new
                            h5ToGtiff(path_image, path_image_new)
                            imagettes_jp2_tif_ecw_list.append(elt1_new)
                        else:
                            imagettes_jp2_tif_ecw_list.append(elt1)

                # Pour le cas ou le repertoire contient des fichiers images
                if not imagettes_jp2_tif_ecw_list == []:

                    # Cas ou chaque emprise d'image est un polygone
                    if is_not_assembled or is_optimize_emprise or is_optimize_emprise_nodata:

                        for imagette in imagettes_jp2_tif_ecw_list:
                            # Récupération des emprises de l'image
                            path_image = repertory + os.sep + imagette
                            if size_pixel == 0.0:
                                size_pixel = getPixelSizeImage(path_image)

                            path_info_acquisition = repertory
                            xmin, xmax, ymin, ymax = getEmpriseImage(path_image)
                            coord_list = [xmin,ymax,xmax,ymax,xmax,ymin,xmin,ymin,xmin,ymax]

                            # Saisie des données
                            points_list.append(coord_list)

                            # Récupération du nom de l'image pour la création des champs
                            input_image_name = os.path.splitext(os.path.basename(path_image))[0]
                            name_image_list.append(input_image_name)


                            # Cas optimisation de l'emprise en elevant les nodata
                            if is_optimize_emprise_nodata :

                                path_info_acquisition = path_image
                                optimize_emprise_nodata_shape = repertory_output + os.sep + input_image_name + extension_vector
                                optimize_emprise_tmp1_shape = repertory_output + os.sep + input_image_name + SUFFIX_TMP + str(1) + extension_vector
                                optimize_emprise_tmp2_shape = repertory_output + os.sep + input_image_name + SUFFIX_TMP + str(2) + extension_vector
                                optimize_emprise_tmp3_shape = repertory_output + os.sep + input_image_name + SUFFIX_TMP + str(3) + extension_vector
                                optimize_emprise_tmp4_shape = repertory_output + os.sep + input_image_name + SUFFIX_TMP + str(4) + extension_vector
                                binary_mask_zeros_raster = repertory_output + os.sep + input_image_name + SUFFIX_MASK_ZERO + extension_raster
                                optimize_emprise_nodata_shape_list.append(optimize_emprise_nodata_shape)

                                # Création masque binaire pour séparer les no data des vraies valeurs
                                no_data_value_img = getNodataValueImage(path_image)
                                if no_data_value_img == None :
                                    no_data_value_img = no_data_value
                                createBinaryMaskMultiBand(path_image, binary_mask_zeros_raster, no_data_value_img, CODAGE_8B)

                                # Vectorisation du masque binaire true data/false data -> polygone avec uniquement les vraies valeurs
                                if os.path.exists(optimize_emprise_nodata_shape):
                                    removeVectorFile(optimize_emprise_nodata_shape)

                                polygonizeRaster(binary_mask_zeros_raster, optimize_emprise_tmp1_shape, input_image_name, ATTR_NAME_ID, format_vector)

                                # Nettoyage des polygones parasites pour ne garder que le polygone pricipale si l'option "all" n'est pas demandée
                                if not is_all_polygons_used :
                                    geometry_list = getGeomPolygons(optimize_emprise_tmp1_shape, None, None, format_vector)
                                    geometry_orded_dico = {}
                                    geometry_orded_list = []
                                    for geometry in geometry_list :
                                        area = geometry.GetArea()
                                        geometry_orded_dico[area] = geometry
                                        geometry_orded_list.append(area)
                                    geometry_orded_list.sort()
                                    if len(geometry_orded_list) > 0 :
                                        max_area = geometry_orded_list[len(geometry_orded_list) - 1]
                                        geom_max = geometry_orded_dico[max_area]
                                        attribute_dico = {ATTR_NAME_ID:ogr.OFTInteger}
                                        polygons_attr_geom_dico = {}
                                        polygons_attr_geom_dico[str(1)] = [geom_max,{ATTR_NAME_ID:str(1)}]
                                        createPolygonsFromGeometryList(attribute_dico, polygons_attr_geom_dico, optimize_emprise_tmp2_shape, epsg, format_vector)
                                    else :
                                        print(cyan + "createEmprise() : " + bold + yellow + " Attention!!! Fichier non traite (ne contient pas de polygone): " + optimize_emprise_tmp1_shape + endC)
                                        optimize_emprise_tmp2_shape = optimize_emprise_tmp1_shape
                                else :
                                    optimize_emprise_tmp2_shape = optimize_emprise_tmp1_shape

                                # Nettoyage des polygones simplification et supression des trous
                                cleanRingVector(optimize_emprise_tmp2_shape, optimize_emprise_tmp3_shape, format_vector)
                                simplifyVector(optimize_emprise_tmp3_shape, optimize_emprise_tmp4_shape, 2, format_vector)
                                if size_erode != 0.0 :
                                    bufferVector(optimize_emprise_tmp4_shape, optimize_emprise_nodata_shape, size_erode * -1, "", 1.0, 10, format_vector)
                                else :
                                    copyVectorFile(optimize_emprise_tmp4_shape, optimize_emprise_nodata_shape, format_vector)

                                # Nettoyage des fichier intermediaires
                                if not save_results_intermediate:
                                    removeFile(binary_mask_zeros_raster)
                                    removeVectorFile(optimize_emprise_tmp1_shape)
                                    removeVectorFile(optimize_emprise_tmp2_shape)
                                    removeVectorFile(optimize_emprise_tmp3_shape)
                                    removeVectorFile(optimize_emprise_tmp4_shape)

                            # Recuperation de la date et l'heure d'acquisition
                            # Gestion de l'emprise optimisé nodata on utilise le nom de l'image pour la date d'acquisition sion c'est le nom du repertoire
                            getDataToFiels(path_info_acquisition, is_not_date, is_optimize_emprise or is_optimize_emprise_nodata, separ_name, pos_date, nb_char_date, separ_date, points_list, ref_dossier_list, name_rep_list, date_list, heure_list)


                    # Cas ou l'on prend l'emprise globale des images un seul polygone correspondant a l'emprise globale
                    else :

                        # Récupération des emprises des images du dossier
                        liste_x_l = []
                        liste_y_b = []
                        liste_x_r = []
                        liste_y_t = []

                        for imagette in imagettes_jp2_tif_ecw_list:
                            path_image = repertory + os.sep + imagette
                            xmin, xmax, ymin, ymax = getEmpriseImage(path_image)

                            liste_x_l.append(xmin)
                            liste_x_r.append(xmax)
                            liste_y_b.append(ymin)
                            liste_y_t.append(ymax)

                        # Récupération des min et max de la liste des imagettes
                        # Coin haut gauche
                        xmin_l_t = str(min(liste_x_l))

                        # Coin bas gauche
                        ymin_l_b = str(min(liste_y_b))
                        xmin_l_b = xmin_l_t

                        # Coin bas doite
                        xmax_r_b = str(max(liste_x_r))

                        # Coin haut droite
                        ymax_r_t = str(max(liste_y_t))
                        xmax_r_t = xmax_r_b
                        ymax_r_b = ymin_l_b
                        ymin_l_t = ymax_r_t

                        coord_list = [xmin_l_t,ymin_l_t,xmin_l_b,ymin_l_b,xmax_r_b,ymax_r_b,xmax_r_t,ymax_r_t,xmin_l_t,ymin_l_t]
                        points_list.append(coord_list)

                        # Récupération du nom du répertoire pour création des champs
                        getDataToFiels(repertory, is_not_date, is_optimize_emprise, separ_name, pos_date, nb_char_date, separ_date, points_list, ref_dossier_list, name_rep_list, date_list, heure_list)

        #  Préparation des attribute_dico et polygons_attr_coord_dico
        if is_not_assembled :
            attribute_dico = {ATTR_NAME_ID:ogr.OFTInteger, ATTR_NAME_NOMIMAGE:ogr.OFTString,ATTR_NAME_DATEACQUI:ogr.OFTDate, ATTR_NAME_HEUREACQUI:ogr.OFTString}

            for i in range(len(points_list)):
                polygons_attr_coord_dico[str(i)] = [points_list[i],{ATTR_NAME_ID:i+1,ATTR_NAME_NOMIMAGE:name_image_list[i],ATTR_NAME_DATEACQUI:date_list[i], ATTR_NAME_HEUREACQUI:heure_list[i]}]

        else :
            attribute_dico = {ATTR_NAME_NOMIMAGE:ogr.OFTString,ATTR_NAME_REFDOSSIER:ogr.OFTString,ATTR_NAME_DATEACQUI:ogr.OFTDate, ATTR_NAME_HEUREACQUI:ogr.OFTString}

            for i in range(len(points_list)):
                polygons_attr_coord_dico[str(i)] = [points_list[i],{ATTR_NAME_NOMIMAGE:SUFFIX_IMGSAT + date_list[i] + PREFIX_OPT + ref_dossier_list[i] + PREFIX_ASS + extension_raster, ATTR_NAME_REFDOSSIER:ref_dossier_list[i], ATTR_NAME_DATEACQUI:date_list[i], ATTR_NAME_HEUREACQUI:heure_list[i]}]


        # Cas optimisation de l'emprise en elevant les nodata
        colum = ""
        if is_optimize_emprise_nodata :

            if is_not_assembled :
                file_vector = output_vector
            else :
                file_vector = file_vector_detail

            # Fusion des polygones d'emprises images optimisées sans nodata
            polygons_attr_geom_dico = {}
            i = 0
            for shape_file in optimize_emprise_nodata_shape_list :
                geom_list = getGeomPolygons(shape_file, ATTR_NAME_ID, 1, format_vector)
                if not is_all_polygons_used :
                    if geom_list is not None and len(geom_list) > 0:
                        geom = geom_list[0]
                        polygons_attr_geom_dico[str(i)] = [geom,polygons_attr_coord_dico[str(i)][1]]
                else :
                    j = 1
                    for geom in geom_list:
                        polygons_attr_geom_dico[str(i + 1000000 * j)] = [geom,polygons_attr_coord_dico[str(i)][1]]
                        j += 1
                i += 1

            createPolygonsFromGeometryList(attribute_dico, polygons_attr_geom_dico, file_vector, epsg, format_vector)

            # Suppression des fichiers intermediaires
            if not save_results_intermediate:
                for vector_to_del in optimize_emprise_nodata_shape_list:
                 removeVectorFile(vector_to_del)

        else :
            # Utilisation de createPolygonsFromCoordList()
            if is_optimize_emprise :
                file_vector = file_vector_detail
            else :
                file_vector = output_vector

            # Creation des polygones a partir de la liste des coordonnées des emprises
            createPolygonsFromCoordList(attribute_dico, polygons_attr_coord_dico, file_vector, epsg, format_vector)

        # Cas fusion des polygones pour avoir une emprise constituée d'un seul polygone
        if not is_not_assembled :

            # Supression des polygons de la taille d'un pixel
            cleanMiniAreaPolygons(file_vector, file_vector_clean, size_pixel + 0.00001, "", format_vector)

            # Fusion des polygones
            if is_optimize_emprise or is_optimize_emprise_nodata or is_all_polygons_used :
                column_name = ""
                if is_all_polygons_used :
                    column_name = ATTR_NAME_DATEACQUI
                elif is_optimize_emprise or is_optimize_emprise_nodata :
                    column_name = ATTR_NAME_NOMIMAGE

                # Fusion des polygones
                if is_all_polygons_used and is_not_date :
                    #fusionNeighbourGeometryBySameValue(file_vector_clean, output_vector, column_name, format_vector)
                    dissolveVector(file_vector_clean, output_vector, column_name, format_vector)
                else :
                    if not geometries2multigeometries(file_vector_clean, output_vector, column_name, format_vector) :
                        copyVectorFile(file_vector_detail, output_vector, format_vector)

                # Suppression des fichiers intermediaires
                if not save_results_intermediate :
                    removeVectorFile(file_vector_detail)
                    removeVectorFile(file_vector_clean)
    return

###########################################################################################################################################
# FONCTION getDataToFiels()                                                                                                               #
###########################################################################################################################################
def getDataToFiels(repertory, is_not_date, is_optimize_emprise, separ_name, pos_date, nb_char_date, separ_date, points_list, ref_dossier_list, name_rep_list, date_list, heure_list):
    """
    # ROLE:
    #    Récupération du nom du répertoire pour création des champs
    #
    # ENTREES DE LA FONCTION :
    #    repertory : Le repertoire de recherche des images
    #    is_not_date : Option : Les emprises des images ne gérent pas les dates des images
    #    is_optimize_emprise : Creer une version de l'emprise des images par dossier plus optimisé
    #    separ_name : Paramètre date acquisition dans le nom, séparateur d'information
    #    pos_date : Paramètre date acquisition dans le nom, position relatif au séparateur d'information
    #    nb_char_date : Paramètre date acquisition dans le nom, nombre de caractères constituant la date
    #    separ_date : Paramètre date acquisition dans le nom, séparateur dans l'information date
    #    ref_dossier_list : Paramètre liste de sortie contenant la reference du dossier
    #    name_rep_list : Paramètre liste de sortie contenant le nom du repertoire
    #    date_list : Paramètre liste de sortie contenant la date d'acquisition
    #    heure_list : Paramètre liste de sortie contenant l'heure d'acquisition
    #
    # SORTIES DE LA FONCTION :
    #    Des listes de donnees pour remplir les champs du vecteurs de sortie
    #
    """

    ref_dossier = "None"
    date_format_str = "1900-01-01"
    time_sec = 0
    regexp = "[0-9]"

    if repertory[len(repertory)-1] == os.sep :
        repertory = repertory[0:len(repertory)-1]
    input_rep_name = os.path.splitext(os.path.basename(repertory))[0]

    if not is_not_date :
        if debug >= 3:
            print(cyan + "getDataToFiels() : " + endC + input_rep_name)
        try :
            infoDate = input_rep_name.split(separ_name)[pos_date]
            datePriseDeVue = infoDate[:nb_char_date]
            datePriseDeVue = datePriseDeVue.replace(separ_date,"")
            date_format_str = datePriseDeVue[0:4] + "-" + datePriseDeVue[4:6] + "-" + datePriseDeVue[6:8]

            if nb_char_date + 8 <= len(infoDate) :
                timedate_str = infoDate[nb_char_date:]
                timedate = ""
                # Supression du premier caractere si different d'un caractere nombre
                if re.match(regexp, timedate_str[0]) is None:
                    timedate_str = timedate_str[1:]

                # La reference du dossier correction aux 4 derniers caracteres de l'heure d'acquisition en milliseconde
                ref_dossier = timedate_str[len(timedate_str)-4:]

                # Ne garder que les caracteres numeriques pour extraire l'heure d'acquisition
                for car in timedate_str :
                    if re.match(regexp, car) is not None:
                        timedate += car
                    else :
                        break

                # L'heure d'acquisition en seconde
                time_millisec = int(timedate)
                time_sec = time_millisec / 1000
            else :
                ref_dossier = "0"
                time_sec = 0

        except:
            print(cyan + "getDataToFiels : " + bold + yellow + "WARNING Référence dossier : " + ref_dossier + " Les parametres de saisies de la date ne sont pas correcetes !!! " + endC)

    if (not is_optimize_emprise) and (ref_dossier in ref_dossier_list) :
         print(cyan + "getDataToFiels : " + bold + yellow + "WARNING Référence dossier : " + ref_dossier + " Existe déjà dans la liste des dossiers!!! " + endC)

    # Saisie des données
    ref_dossier_list.append(ref_dossier)
    name_rep_list.append(input_rep_name)
    date_list.append(date_format_str)
    time_str = strftime('%Hh%Mm%Ss', gmtime(time_sec))
    heure_list.append(time_str)

    return

###########################################################################################################################################
# MISE EN PLACE DU PARSER                                                                                                                 #
###########################################################################################################################################

# Code executé seulement dans le cas ou le script est lancé depuis une ligne de commande
# Il n'est pas executé lors d'un import CreateEmprises.py
# Exemple de lancement en ligne de commande:
# python /home/scgsi/Documents/ChaineTraitement/ScriptsLittoral/ScriptsCommunsLittoral/CreateEmprises.py -dir /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/08_Donnees/Orthos -outf /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Tests/Tests_CreateEmprise/Emprise.shp
#createEmprises("/mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/08_Donnees/Orthos", "/mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Tests/test_createEmprises/emprise.shp")

def main(gui=False):

    parser = argparse.ArgumentParser(prog="CreateEmprises", description=" \
    Info : Creating an shapefile (.shp) containing the bounderies of Pleiades images without assembling them.\n\
    Objectif   : Crée le shapefile de l'emprise d'imagettes Pleiades sans les assembler. \n\
    Example : python /home/scgsi/Documents/ChaineTraitement/ScriptsLittoral/ScriptsCommunsLittoral/CreateEmprises.py \n\
                            -dir /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/08_Donnees/Orthos \n\
                            -outf /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Tests/Tests_CreateEmprise/Emprise.shp")

    parser.add_argument('-dir','--input_dir', default="",nargs="+", help="Liste input directory containing the images directories (images .tif, .ecw, .jp2, .dim, .asc), can be several directories.", type=str, required=True)
    parser.add_argument('-outf','--output_vector', default="", help="Output file containing all polygones.", type=str, required=True)
    parser.add_argument('-na', '--not_assembled', action='store_true', default=False, help="Option : The emprise of images are not assembled. By default : False", required=False)
    parser.add_argument('-all','--all_polygons_used',action='store_true',default=False,help="Option : All polygons find are used. By default, False for optimisation", required=False)
    parser.add_argument('-nd', '--not_date', action='store_true', default=False, help="Option : The emprise of images are not managed the date. By default : False", required=False)
    parser.add_argument('-op', '--optimize_emprise', action='store_true', default=False, help="Option : The emprise of images is optimized. By default : False", required=False)
    parser.add_argument('-op_nodata', '--optimize_emprise_nodata', action='store_true', default=False, help="Option : The emprise of images is optimized with no data not include. By default : False", required=False)
    parser.add_argument('-ndv','--no_data_value', default=0, help="Option in option optimize_emprise_nodata  : Value of the pixel no data. By default : 0", type=int, required=False)
    parser.add_argument('-erode','--size_erode', default=0.0, help="Size erode buffer emprise polygon in option optimize_emprise_nodata is used (in meter). By default : 0.0", type=float, required=False)
    parser.add_argument('-sepn','--separname', default="_", help="Acquisition date in the name, information separator (For example : '_'). By default : '_'", type=str, required=False)
    parser.add_argument('-posd','--posdate', default=1, help="Acquisition date in the name, position relative to the information separator (For example : 3). By default : 2", type=int, required=False)
    parser.add_argument('-nbcd','--nbchardate', default=8, help="Acquisition date in the name, number of characters constituting the date (For example : 10). By default : 8", type=int, required=False)
    parser.add_argument('-sepd','--separdate', default="", help="Acquisition date in the name, the date separator in information (For example : '-'). By default : ''", type=str, required=False)
    parser.add_argument('-epsg','--epsg', default=2154,help="Projection of the output file.", type=int, required=False)
    parser.add_argument('-vef','--format_vector', default="ESRI Shapefile",help="Format of the output file.", type=str, required=False)
    parser.add_argument('-rae','--extension_raster', default=".tif", help="Option : Extension file for image raster. By default : '.tif'", type=str, required=False)
    parser.add_argument('-vee','--extension_vector',default=".shp",help="Option : Extension file for vector. By default : '.shp'", type=str, required=False)
    parser.add_argument('-log','--path_time_log',default=os.getcwd()+ os.sep + "log.txt",help="Option : Name of log. By default : log.txt", type=str, required=False)
    parser.add_argument('-sav','--save_results_inter',action='store_true',default=False,help="Option : Save or delete intermediate result after the process. By default, False", required=False)
    parser.add_argument('-now','--overwrite',action='store_false',default=True,help="Option : Overwrite files with same names. By default : True", required=False)
    parser.add_argument('-debug','--debug',default=3,help="Option : Value of level debug trace, default : 3 ",type=int, required=False)
    args = displayIHM(gui, parser)

    # Récupération du dossier contenant les dossiers images
    if args.input_dir != None :
        repertory_input_list = args.input_dir
        for repertory in repertory_input_list :
            if not os.path.isdir(repertory):
                raise NameError (cyan + "CreateEmprises : " + bold + red  + "Directory %s not existe!" %(repertory) + endC)

    # Récupération du fichier de sortie assemblé
    if args.output_vector != None :
        output_vector = args.output_vector

    # Paramètre emprise non assemblé
    if args.not_assembled != None:
        not_assembled = args.not_assembled

    # Paramètre emprise tout les polygones utilisés
    if args.all_polygons_used != None:
        all_polygons_used = args.all_polygons_used

    # Paramètre emprise optimisé no data
    if args.optimize_emprise != None:
        optimize_emprise = args.optimize_emprise

    # Paramètre emprise optimisé
    if args.optimize_emprise_nodata != None:
        optimize_emprise_nodata = args.optimize_emprise_nodata

    # Parametres de valeur du nodata
    if args.no_data_value!= None:
        no_data_value = args.no_data_value

    # Paramètre d'erosion du polygone d'emprise
    if args.size_erode != None:
        size_erode = args.size_erode

    # Paramètre emprise sans date
    if args.not_date != None:
        not_date = args.not_date

    # Paramètres de la date
    if args.separname != None:
        separname = args.separname

    if args.posdate != None:
        posdate = args.posdate

    if args.nbchardate != None:
        nbchardate = args.nbchardate

    if args.separdate != None:
        separdate = args.separdate

    # Récupération de la projection du fichier de sortie
    if args.epsg != None :
        epsg = args.epsg

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
    if args.path_time_log != None:
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

    # Affichage des arguments récupérés
    if debug >= 3:
        print(bold + green + "Variables dans le parser" + endC)
        print(cyan + "CreateEmprises : " + endC + "repertory_input_list : " + str(repertory_input_list) + endC)
        print(cyan + "CreateEmprises : " + endC + "output_vector : " + str(output_vector) + endC)
        print(cyan + "CreateEmprises : " + endC + "not_assembled : " + str(not_assembled) + endC)
        print(cyan + "CreateEmprises : " + endC + "all_polygons_used : " + str(all_polygons_used) + endC)
        print(cyan + "CreateEmprises : " + endC + "not_date : " + str(not_date) + endC)
        print(cyan + "CreateEmprises : " + endC + "optimize_emprise : " + str(optimize_emprise) + endC)
        print(cyan + "CreateEmprises : " + endC + "optimize_emprise_nodata : " + str(optimize_emprise_nodata) + endC)
        print(cyan + "CreateEmprises : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "CreateEmprises : " + endC + "size_erode : " + str(size_erode) + endC)
        print(cyan + "CreateEmprises : " + endC + "separname : " + str(separname) + endC)
        print(cyan + "CreateEmprises : " + endC + "posdate : " + str(posdate) + endC)
        print(cyan + "CreateEmprises : " + endC + "nbchardate : " + str(nbchardate) + endC)
        print(cyan + "CreateEmprises : " + endC + "separdate : " + str(separdate) + endC)
        print(cyan + "CreateEmprises : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "CreateEmprises : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "CreateEmprises : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "CreateEmprises : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "CreateEmprises : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "CreateEmprises : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "CreateEmprises : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "CreateEmprises : " + endC + "debug : " + str(debug) + endC)

    # Si le dossier de sortie n'existe pas, on le crée
    repertory_output = os.path.dirname(output_vector)
    if not os.path.isdir(repertory_output):
        os.makedirs(repertory_output)

    # Fonction générale
    createEmprise(repertory_input_list, output_vector, not_assembled, all_polygons_used, not_date, optimize_emprise, optimize_emprise_nodata, no_data_value, size_erode, path_time_log, separname, posdate, nbchardate, separdate, epsg, format_vector, extension_raster, extension_vector, save_results_intermediate, overwrite)

# ================================================

if __name__ == '__main__':
  main(gui=False)
