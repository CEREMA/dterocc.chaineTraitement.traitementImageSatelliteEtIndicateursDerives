#!/usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

from __future__ import print_function
import os
from osgeo import ogr
from Lib_log import timeLine
from Lib_raster import cutImageByVector
from Lib_vector import updateProjection, bufferVector, cutVector, addNewFieldVector, updateIndexVector, filterSelectDataVector, intersectVector, fusionVectors, cleanMiniAreaPolygons, simplifyVector
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 3

    #######################################
    ### Préparation des données rasters ###
    #######################################

def preparationRasters(urbanatlas_input, ucz_output, emprise_file, mask_file, enter_with_mask, image_file, mnh_file, built_files_list, hydrography_file, roads_files_list, rpg_file, indicators_method, ucz_method, dbms_choice, threshold_ndvi, threshold_ndvi_water, threshold_ndwi2, threshold_bi_bottom, threshold_bi_top, no_data_value, path_time_log, temp_directory, format_raster, format_vector, extension_raster):

    print(bold + yellow + "Début de la préparation des données rasters." + endC)
    step = "    Début de la préparation des données rasters : "
    timeLine(path_time_log,step)

    image_cut = temp_directory + os.sep + os.path.splitext(os.path.basename(image_file))[0] + "_cut" + extension_raster
    print(bold + cyan + "    Découpage de '%s' à l'emprise de '%s' :" % (image_file, emprise_file) + endC)
    # Découpage de l'image en entrée (image sat ou résultat classif)
    cutImageByVector(emprise_file, image_file, image_cut, None, None, False, no_data_value, 0, format_raster, format_vector)

    if indicators_method == "BD_exogenes":
        neochannels = temp_directory + os.sep + os.path.splitext(os.path.basename(image_file))[0] + "_NDVI" + extension_raster
        print(bold + cyan + "    Calcul de NDVI à partir de '%s' :" % (image_cut) + endC)
        os.system("otbcli_RadiometricIndices -in %s -out %s -channels.red 1 -channels.nir 4 -list Vegetation:NDVI" % (image_cut, neochannels)) # Calcul du NDVI pour la 1ère méthode de calcul des indicateurs

    elif indicators_method == "SI_seuillage":
        neochannels = temp_directory + os.sep + os.path.splitext(os.path.basename(image_file))[0] + "_NDVI_NDWI2_BI" + extension_raster
        print(bold + cyan + "    Calcul de NDVI/NDWI2/BI à partir de '%s' :" % (image_cut) + endC)
        os.system("otbcli_RadiometricIndices -in %s -out %s -channels.green 3 -channels.red 1 -channels.nir 4 -list Vegetation:NDVI Water:NDWI2 Soil:BI" % (image_cut, neochannels)) # Calcul des néocanaux pour la 2ème méthode de calcul des indicateurs

    elif indicators_method == "Resultats_classif":
        MNH_cut = temp_directory + os.sep + os.path.splitext(os.path.basename(mnh_file))[0] + "_cut" + extension_raster
        print(bold + cyan + "    Découpage de '%s' à l'emprise de '%s' :" % (mnh_file, emprise_file) + endC)
        # Découpage du MNH pour la 4ème méthode de calcul des indicateurs
        cutImageByVector(emprise_file, mnh_file, MNH_cut, None, None, False, no_data_value, 0, format_raster, format_vector)

    step = "    Fin de la préparation des données rasters : "
    timeLine(path_time_log,step)
    print(bold + yellow + "Fin de la préparation des données rasters." + endC)
    print("\n")

    return

    ########################################
    ### Préparation des données vecteurs ###
    ########################################

def preparationVecteurs(urbanatlas_input, ucz_output, emprise_file, mask_file, enter_with_mask, image_file, mnh_file, built_files_list, hydrography_file, roads_files_list, rpg_file, indicators_method, ucz_method, dbms_choice, threshold_ndvi, threshold_ndvi_water, threshold_ndwi2, threshold_bi_bottom, threshold_bi_top, path_time_log, temp_directory, format_vector, extension_vector):

    print(bold + yellow + "Début de la préparation des données vecteurs." + endC)
    step = "    Début de la préparation des données vecteurs : "
    timeLine(path_time_log,step)

    field_name = 'ID'
    field_type = ogr.OFTInteger

    emprise_erosion = temp_directory + os.sep + os.path.splitext(os.path.basename(emprise_file))[0] + "_eroded" + extension_vector
    print(bold + cyan + "    Érosion de '%s' pour le découpage des autres vecteurs :" % (emprise_file) + endC)
    bufferVector(emprise_file, emprise_erosion, -10, "", 1.0, 10, format_vector) # Création du shape zone d'étude érodée (utile pour la fonction CrossingVectorRaster où shape < raster) - Tampon par défaut : -10

    # Traitements sur l'Urban Atlas
    print(bold + cyan + "    Traitements du fichier Urban Atlas '%s' :" % (urbanatlas_input) + endC)
    basename_grid = os.path.splitext(os.path.basename(urbanatlas_input))[0]
    grid_reproject = temp_directory + os.sep + basename_grid + "_reproject" + extension_vector
    grid_ready = temp_directory + os.sep + basename_grid + "_cut" + extension_vector
    grid_ready_cleaned = temp_directory + os.sep + basename_grid + "_cut_cleaned" + extension_vector
    column = "'%s, CODE2012, ITEM2012'" % (field_name)
    expression = "CODE2012 NOT IN ('12210', '12220', '12230', '50000')"
    updateProjection(urbanatlas_input, grid_reproject, 2154, format_vector) # MAJ projection
    addNewFieldVector(grid_reproject, field_name, field_type, 0, None, None, format_vector) # Ajout d'un champ ID
    updateIndexVector(grid_reproject, index_name=field_name) # Mise à jour du champs ID (incrémentation)
    cutVector(emprise_erosion, grid_reproject, grid_ready, format_vector) # Découpage du fichier Urban Atlas d'entrée à l'emprise de la zone d'étude
    ret = filterSelectDataVector(grid_ready, grid_ready_cleaned, column, expression, format_vector) # Suppression des polygones eau et routes (uniquement pour le calcul des indicateurs)
    if not ret :
        raise NameError (cyan + "preparationVecteurs : " + bold + red  + "Attention problème lors du filtrage des BD vecteurs l'expression SQL %s est incorrecte" %(expression) + endC)

    if indicators_method in ("BD_exogenes", "SI_seuillage", "SI_classif"):
        # Traitements sur les fichiers bâti de la BD TOPO
        print(bold + cyan + "    Traitements des fichiers bâti '%s' :" % str(built_files_list) + endC)
        built_merge = temp_directory + os.sep + "bati_merged" + extension_vector
        built_ready = temp_directory + os.sep + "bati" + extension_vector
        column = "HAUTEUR"
        expression = "HAUTEUR > 0"
        built_intersect_list=[]
        for built_input in built_files_list:
            basename = os.path.splitext(os.path.basename(built_input))[0]
            built_reproject = temp_directory + os.sep + basename + "_reproject" + extension_vector
            built_intersect = temp_directory + os.sep + basename + "_intersect" + extension_vector
            updateProjection(built_input, built_reproject, 2154, format_vector) # MAJ projection
            intersectVector(emprise_file, built_reproject, built_intersect, format_vector) # Sélection des entités bâti dans l'emprise de l'étude
            built_intersect_list.append(built_intersect)
        fusionVectors(built_intersect_list, built_merge, format_vector) # Fusion des couches bâti de la BD TOPO
        ret = filterSelectDataVector(built_merge, built_ready, column, expression) # Suppression des polygones où la hauteur du bâtiment est à 0
        if not ret :
            raise NameError (cyan + "preparationVecteurs : " + bold + red  + "Attention problème lors du filtrage des BD vecteurs l'expression SQL %s est incorrecte" %(expression) + endC)

        addNewFieldVector(built_ready, field_name, field_type, 0, None, None, format_vector) # Ajout d'un champ ID
        updateIndexVector(built_ready, index_name=field_name) # Mise à jour du champs ID (incrémentation)

        if indicators_method == "BD_exogenes":
            # Traitements sur le fichier routes de la BD TOPO
            print(bold + cyan + "    Traitements du fichier hydrographie '%s' :" % (hydrography_file) + endC)
            basename_hydrography = os.path.splitext(os.path.basename(hydrography_file))[0]
            hydrography_reproject = temp_directory + os.sep + basename_hydrography + "_reproject" + extension_vector
            hydrography_intersect = temp_directory + os.sep + basename_hydrography + "_intersect" + extension_vector
            hydrography_ready = temp_directory + os.sep + "eau" + extension_vector
            column = "REGIME"
            expression = "REGIME LIKE 'Permanent'"
            updateProjection(hydrography_file, hydrography_reproject, 2154, format_vector) # MAJ projection
            intersectVector(emprise_file, hydrography_reproject, hydrography_intersect, format_vector) # Sélection des entités routes dans l'emprise de l'étude
            ret = filterSelectDataVector (hydrography_intersect, hydrography_ready, column, expression, format_vector) # Sélection des entités suivant le régime hydrographique (permanent)
            if not ret :
                raise NameError (cyan + "preparationVecteurs : " + bold + red  + "Attention problème lors du filtrage des BD vecteurs l'expression SQL %s est incorrecte" %(expression) + endC)
            addNewFieldVector(hydrography_ready, field_name, field_type, 0, None, None, format_vector) # Ajout d'un champ ID
            updateIndexVector(hydrography_ready, index_name=field_name) # Mise à jour du champs ID (incrémentation)

            # Traitements sur le fichier RPG
            print(bold + cyan + "    Traitements du fichier RPG '%s' :" % (rpg_file) + endC)
            basename_RPG = os.path.splitext(os.path.basename(rpg_file))[0]
            RPG_reproject = temp_directory + os.sep + basename_RPG + "_reproject" + extension_vector
            RPG_ready = temp_directory + os.sep + "RPG" + extension_vector
            updateProjection(rpg_file, RPG_reproject, 2154, format_vector) # MAJ projection
            intersectVector(emprise_file, RPG_reproject, RPG_ready, format_vector) # Sélection des entités RPG dans l'emprise de l'étude
            addNewFieldVector(RPG_ready, field_name, field_type, 0, None, None, format_vector) # Ajout d'un champ ID
            updateIndexVector(RPG_ready, index_name=field_name) # Mise à jour du champs ID (incrémentation)

########################################################################################################################################################################################################
######################################################################## Partie restant à coder : normalement pas nécessaire puisque cette méthode n'a pas été retenue #################################
########################################################################################################################################################################################################
                                                                                                                                                                                                    ####
        if indicators_method == "SI_seuillage":                                                                                                                                                     ####
            # Traitements sur les fichiers routes de la BD TOPO                                                                                                                                     ####
            print(bold + cyan + "    Traitements des fichiers routes '%s' :" % str(roads_files_list) + endC   )                                                                                      ####
                                                                                                                                                                                                    ####
            print(bold + "Le script ne peut continuer, le traitements des fichiers routes n'est pas encore entièrement codé" + endC)                                                                ####
            exit(0)                                                                                                                                                                                 ####
                                                                                                                                                                                                    ####
            #~ En entrée : fichier troncon_route + fichier surface_route                                                                                                                            ####
            #~ 1 - reprojection des fichiers en L93                                                                                                                                                 ####
            #~ 2 - sélection des entités des fichiers compris dans la zone d'étude (intersect et non découpage)                                                                                     ####
            #~ 3 - filtrage des entités de troncon_route suivant la nature                                                                                                                          ####
                #~ ("NATURE IN ('Autoroute', 'Bretelle', 'Quasi-autoroute', 'Route  1 chausse', 'Route  2 chausses',                                                                                ####
                #~ 'Route a 1 chaussee', 'Route a 2 chaussees', 'Route à 1 chaussée', 'Route à 2 chaussées')")                                                                                      ####
            #~ 4 - tampon sur les entités de troncon_route correspondant à 'LARGEUR'/2                                                                                                              ####
            #~ 5 - fusion des fichiers en un seul shape                                                                                                                                             ####
            #~ 6 - ajout d'un nouveau champ ID dans le fichier de fusion                                                                                                                            ####
            #~ 7 - mise à jour de ce champ ID                                                                                                                                                       ####
                                                                                                                                                                                                    ####
########################################################################################################################################################################################################
########################################################################################################################################################################################################
########################################################################################################################################################################################################

    step = "    Fin de la préparation des données vecteurs : "
    timeLine(path_time_log,step)
    print(bold + yellow + "Fin de la préparation des données vecteurs." + endC)
    print("\n")

    return

    ##################################################################
    ### Préparation au calcul du RA à partir du bâti de la classif ###
    ##################################################################

def preparationBatiOCS(urbanatlas_input, ucz_output, emprise_file, mask_file, enter_with_mask, image_file, mnh_file, built_files_list, hydrography_file, roads_files_list, rpg_file, indicators_method, ucz_method, dbms_choice, threshold_ndvi, threshold_ndvi_water, threshold_ndwi2, threshold_bi_bottom, threshold_bi_top, path_time_log, temp_directory, format_vector, extension_raster, extension_vector):

    print(bold + yellow + "Début de la préparation du bâti issu de la classif OCS." + endC)
    step = "    Début de la préparation du bâti issu de la classif OCS : "
    timeLine(path_time_log,step)

    built_classif = temp_directory + os.sep + "bati_classif" + extension_raster
    built_polygonize = temp_directory + os.sep + "bati_polygonize" + extension_vector
    built_clean = temp_directory + os.sep + "bati_clean" + extension_vector
    built_simplify = temp_directory + os.sep + "bati_simplify" + extension_vector
    built_ready = temp_directory + os.sep + "bati" + extension_vector

    print(bold + cyan + "    Extraction du bâti du fichier de classification '%s' :" % (image_file) + endC)
    os.system("otbcli_BandMath -il %s -out %s uint8 -exp 'im1b1==11100 ? 10 : 1'" % (image_file, built_classif)) # Extraction du bâti de la classif
    print(bold + cyan + "    Vectorisation du bâti (attention, cette étape peut être extrêmement longue !) :" + endC)
    os.system("gdal_polygonize.py -mask %s %s -f 'ESRI Shapefile' %s built_classif id" % (built_classif, built_classif, built_polygonize)) # Vectorisation du bâti précédemment extrait
    print(bold + cyan + "    Nettoyage du bâti :" + endC)
    cleanMiniAreaPolygons(built_polygonize, built_clean, 20, format_vector) # Nettoyage du bâti vectorisé (élimination des petits polygones) - Surface de nettoyage par défaut : 20
    print(bold + cyan + "    Simplification du bâti :" + endC)
    simplifyVector(built_clean, built_simplify, 1, format_vector) # Simplification du bâti vectorisé (suppression de l'effet "marches d'escalier" dû aux pixels) - Indice de lissage par défaut : 1
    print(bold + cyan + "    Découpage du bâti final à l'emprise du fichier '%s' :" % (emprise_file) + endC)
    os.system("ogr2ogr -progress -f 'ESRI Shapefile' %s %s -clipsrc %s" % (built_ready, built_simplify, emprise_file)) # Découpage du fichier nettoyé et simplifié à l'emprise érodée de la zone d'étude

    step = "    Fin de la préparation du bâti issu de la classif OCS : "
    timeLine(path_time_log,step)
    print(bold + yellow + "Fin de la préparation du bâti issu de la classif OCS." + endC)
    print("\n")

    return

