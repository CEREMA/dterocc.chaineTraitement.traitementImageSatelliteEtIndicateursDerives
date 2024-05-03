#!/usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

from __future__ import print_function
import os, sys, argparse, shutil
from osgeo import ogr
from Lib_log import timeLine
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_raster import getPixelSizeImage
from Lib_vector import updateProjection, cutVector, cutVectorAll, addNewFieldVector, updateIndexVector, filterSelectDataVector, intersectVector, fusionVectors, bufferVector, cleanMiniAreaPolygons
from Lib_file import removeVectorFile
from VectorRasterCutting import cutRasterImages

debug = 3

####################################################################################################
# FONCTION vectorsPreparation()                                                                    #
####################################################################################################
def vectorsPreparation(emprise_file, classif_input, grid_input, built_input_list, roads_input_list, grid_output, grid_output_cleaned, built_output, roads_output, col_code_ua, col_item_ua, epsg, path_time_log, format_vector='ESRI Shapefile', extension_vector=".shp", save_results_intermediate=False, overwrite=True):
    """
    # ROLE :
    #     Préparation des fichiers vecteurs pour le calcul des indicateurs LCZ
    #
    # ENTREES DE LA FONCTION :
    #     emprise_file : fichier d'emprise de la zone d'étude
    #     classif_input : raster classification OCS en entrée
    #     grid_input : fichier Urban Atlas en entrée, d'origine
    #     built_input_list : liste des fichiers bâti de la BD TOPO en entrée, d'origine
    #     roads_input_list : liste des fichiers routes de la BD TOPO en entrée, d'origine
    #     grid_output : fichier Urban Atlas en sortie, traité et prêt pour le calcul des indicateurs
    #     grid_output_cleaned : fichier Urban Atlas en sortie, traité et prêt pour le calcul des indicateurs, nettoyé des polygones axes de communications et eau
    #     built_output : fichier bâti en sortie, traité et prêt pour le calcul des indicateurs
    #     roads_output : fichier routes en sortie, traité et prêt pour le calcul des indicateurs
    #     epsg : Type de projection (EPSG) de l'image de sortie
    #     path_time_log : fichier log de sortie
    #     format_vector : format du fichier vecteur. Optionnel, par default : 'ESRI Shapefile'
    #     extension_vector : extension du fichier vecteur de sortie, par defaut = '.shp'
    #     save_results_intermediate : fichiers de sorties intermédiaires nettoyés, par défaut = False
    #     overwrite : écrase si un fichier existant a le même nom qu'un fichier de sortie, par défaut = True
    #
    # SORTIES DE LA FONCTION :
    #     N.A
    """

    print(bold + yellow + "Début de la préparation des fichiers vecteurs." + endC + "\n")
    timeLine(path_time_log, "Début de la préparation des fichiers vecteurs : ")

    if debug >= 3 :
        print(bold + green + "vectorsPreparation() : Variables dans la fonction" + endC)
        print(cyan + "vectorsPreparation() : " + endC + "emprise_file : " + str(emprise_file) + endC)
        print(cyan + "vectorsPreparation() : " + endC + "classif_input : " + str(classif_input) + endC)
        print(cyan + "vectorsPreparation() : " + endC + "grid_input : " + str(grid_input) + endC)
        print(cyan + "vectorsPreparation() : " + endC + "built_input_list : " + str(built_input_list) + endC)
        print(cyan + "vectorsPreparation() : " + endC + "roads_input_list : " + str(roads_input_list) + endC)
        print(cyan + "vectorsPreparation() : " + endC + "grid_output : " + str(grid_output) + endC)
        print(cyan + "vectorsPreparation() : " + endC + "grid_output_cleaned : " + str(grid_output_cleaned) + endC)
        print(cyan + "vectorsPreparation() : " + endC + "built_output : " + str(built_output) + endC)
        print(cyan + "vectorsPreparation() : " + endC + "roads_output : " + str(roads_output) + endC)
        print(cyan + "vectorsPreparation() : " + endC + "col_code_ua : " + str(col_code_ua) + endC)
        print(cyan + "vectorsPreparation() : " + endC + "col_item_ua : " + str(col_item_ua) + endC)
        print(cyan + "vectorsPreparation() : " + endC + "epsg : " + str(epsg))
        print(cyan + "vectorsPreparation() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "vectorsPreparation() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "vectorsPreparation() : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "vectorsPreparation() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "vectorsPreparation() : " + endC + "overwrite : " + str(overwrite) + endC)

    FOLDER_TEMP = 'TEMP'
    SUFFIX_VECTOR_REPROJECT = '_reproject'
    SUFFIX_VECTOR_INTERSECT = '_intersect'
    SUFFIX_VECTOR_MERGE = '_merge'
    SUFFIX_VECTOR_SELECT = '_select'

    if not os.path.exists(grid_output) or not os.path.exists(built_output) or not os.path.exists(roads_output) or overwrite:

        ############################################
        ### Préparation générale des traitements ###
        ############################################

        path_grid_temp = os.path.dirname(grid_output) + os.sep + FOLDER_TEMP
        path_built_temp = os.path.dirname(built_output) + os.sep + FOLDER_TEMP
        path_roads_temp = os.path.dirname(roads_output) + os.sep + FOLDER_TEMP

        if os.path.exists(path_grid_temp):
            shutil.rmtree(path_grid_temp)
        if os.path.exists(path_built_temp):
            shutil.rmtree(path_built_temp)
        if os.path.exists(path_roads_temp):
            shutil.rmtree(path_roads_temp)

        if not os.path.exists(path_grid_temp):
            os.mkdir(path_grid_temp)
        if not os.path.exists(path_built_temp):
            os.mkdir(path_built_temp)
        if not os.path.exists(path_roads_temp):
            os.mkdir(path_roads_temp)

        basename_grid = os.path.splitext(os.path.basename(grid_output))[0]
        basename_built = os.path.splitext(os.path.basename(built_output))[0]
        basename_roads = os.path.splitext(os.path.basename(roads_output))[0]

        # Variables pour ajout colonne ID
        field_name = 'ID' # Attention ! Nom fixé en dur dans les scripts indicateurs, pas dans le script final
        field_type = ogr.OFTInteger

        ##############################################
        ### Traitements sur le vecteur Urban Atlas ###
        ##############################################

        if not os.path.exists(grid_output) or overwrite :

            if os.path.exists(grid_output):
                removeVectorFile(grid_output)
            if os.path.exists(grid_output_cleaned):
                removeVectorFile(grid_output_cleaned)

            # MAJ projection
            grid_reproject = path_grid_temp + os.sep + basename_grid + SUFFIX_VECTOR_REPROJECT + extension_vector
            updateProjection(grid_input, grid_reproject, projection=epsg)

            # Découpage du fichier Urban Atlas d'entrée à l'emprise de la zone d'étude
            grid_output_temp = os.path.splitext(grid_output)[0] + "_temp" + extension_vector
            cutVector(emprise_file, grid_reproject, grid_output_temp, overwrite, format_vector)

            # Suppression des très petits polygones qui introduisent des valeurs NaN
            pixel_size = getPixelSizeImage(classif_input)
            min_size_area = pixel_size * 2
            cleanMiniAreaPolygons(grid_output_temp, grid_output, min_size_area, '', format_vector)
            if not save_results_intermediate:
                if os.path.exists(grid_output_temp):
                    removeVectorFile(grid_output_temp, format_vector)

            # Ajout d'un champ ID
            addNewFieldVector(grid_output, field_name, field_type, 0, None, None, format_vector)
            updateIndexVector(grid_output, field_name, format_vector)

            # Suppression des polygones eau et routes (uniquement pour le calcul des indicateurs)
            column = "'%s, %s, %s'" % (field_name, col_code_ua, col_item_ua)
            expression = "%s NOT IN ('12210', '12220', '12230', '50000')" % (col_code_ua)
            ret = filterSelectDataVector(grid_output, grid_output_cleaned, column, expression, format_vector)
            if not ret :
                raise NameError (cyan + "vectorsPreparation : " + bold + red  + "Attention problème lors du filtrage des BD vecteurs l'expression SQL %s est incorrecte" %(expression) + endC)

        #########################################
        ### Traitements sur les vecteurs bâti ###
        #########################################
        if not os.path.exists(built_output) or overwrite :

            if os.path.exists(built_output):
                removeVectorFile(built_output)

            # MAJ projection
            built_reproject_list=[]
            for built_input in built_input_list:
                built_reproject = path_built_temp + os.sep + os.path.splitext(os.path.basename(built_input))[0] + SUFFIX_VECTOR_REPROJECT + extension_vector
                updateProjection(built_input, built_reproject, projection=epsg)
                built_reproject_list.append(built_reproject)

            # Sélection des entités bâti dans l'emprise de l'étude
            built_intersect_list = []
            for built_reproject in built_reproject_list:
                built_intersect = path_built_temp + os.sep + os.path.splitext(os.path.basename(built_reproject))[0] + SUFFIX_VECTOR_INTERSECT + extension_vector
                intersectVector(emprise_file, built_reproject, built_intersect, format_vector)
                built_intersect_list.append(built_intersect)

            # Fusion des couches bâti de la BD TOPO
            built_merge = path_built_temp + os.sep + basename_built + SUFFIX_VECTOR_MERGE + extension_vector
            built_select = path_built_temp + os.sep + basename_built + SUFFIX_VECTOR_SELECT + extension_vector
            fusionVectors(built_intersect_list, built_merge)

            # Suppression des polygones où la hauteur du bâtiment est à 0
            column = "HAUTEUR"
            expression = "HAUTEUR > 0"
            ret = filterSelectDataVector(built_merge, built_select, column, expression, format_vector)
            if not ret :
                raise NameError (cyan + "vectorsPreparation : " + bold + red  + "Attention problème lors du filtrage des BD vecteurs l'expression SQL %s est incorrecte" %(expression) + endC)

            # Découpage des bati d'entrée à l'emprise de la zone d'étude
            cutVector(emprise_file, built_select, built_output, overwrite, format_vector)

            # Ajout d'un champ ID
            addNewFieldVector(built_output, field_name, field_type, 0, None, None, format_vector)
            updateIndexVector(built_output, field_name, format_vector)

        ###########################################
        ### Traitements sur les vecteurs routes ###
        ###########################################

        if not os.path.exists(roads_output) or overwrite :

            if os.path.exists(roads_output):
                removeVectorFile(roads_output)

            # MAJ projection
            roads_reproject_list=[]
            for roads_input in roads_input_list:
                roads_reproject = path_roads_temp + os.sep + os.path.splitext(os.path.basename(roads_input))[0] + SUFFIX_VECTOR_REPROJECT + extension_vector
                updateProjection(roads_input, roads_reproject, projection=epsg)
                roads_reproject_list.append(roads_reproject)

            # Sélection des entités routes dans l'emprise de l'étude
            roads_intersect_list = []
            for roads_reproject in roads_reproject_list:
                roads_intersect = path_roads_temp + os.sep + os.path.splitext(os.path.basename(roads_reproject))[0] + SUFFIX_VECTOR_INTERSECT + extension_vector
                intersectVector(emprise_file, roads_reproject, roads_intersect, format_vector)
                roads_intersect_list.append(roads_intersect)

            # Fusion des couches route de la BD TOPO
            roads_merge = path_roads_temp + os.sep + basename_roads + SUFFIX_VECTOR_MERGE + extension_vector
            roads_select = path_roads_temp + os.sep + basename_roads + SUFFIX_VECTOR_SELECT + extension_vector
            fusionVectors(roads_intersect_list, roads_merge)

            # Sélection des entités suivant la nature de la route dans la couche routes de la BD TOPO
            column = "NATURE"
            expression = "NATURE IN ('Autoroute', 'Bretelle', 'Quasi-autoroute', 'Route  1 chausse', 'Route  2 chausses', 'Route a 1 chaussee', 'Route a 2 chaussees', 'Route à 1 chaussée', 'Route à 2 chaussées')"
            ret = filterSelectDataVector (roads_merge, roads_select, column, expression, format_vector)
            if not ret :
                raise NameError (cyan + "vectorsPreparation : " + bold + red  + "Attention problème lors du filtrage des BD vecteurs l'expression SQL %s est incorrecte" %(expression) + endC)

            # Découpage des routes d'entrée à l'emprise de la zone d'étude
            cutVectorAll(emprise_file, roads_select, roads_output, overwrite, format_vector)

            # Ajout d'un champ ID
            addNewFieldVector(roads_output, field_name, field_type, 0, None, None, format_vector)
            updateIndexVector(roads_output, field_name, format_vector)

        ##########################################
        ### Nettoyage des fichiers temporaires ###
        ##########################################

        if not save_results_intermediate:
            if os.path.exists(path_grid_temp):
                shutil.rmtree(path_grid_temp)
            if os.path.exists(path_built_temp):
                shutil.rmtree(path_built_temp)
            if os.path.exists(path_roads_temp):
                shutil.rmtree(path_roads_temp)

    else:
        print(bold + magenta + "La préparation des fichiers vecteurs a déjà eu lieu.\n" + endC)

    print(bold + yellow + "Fin de la préparation des fichiers vecteurs.\n" + endC)
    timeLine(path_time_log, "Fin de la préparation des fichiers vecteurs : ")

    return

####################################################################################################
# FONCTION rastersPreparation()                                                                    #
####################################################################################################
def rastersPreparation(emprise_file, classif_input, mns_input, mnh_input, classif_output, mns_output, mnh_output, epsg, no_data_value, path_time_log, format_raster='GTiff', format_vector='ESRI Shapefile', extension_raster=".tif", extension_vector=".shp", save_results_intermediate=False, overwrite=True):
    """
    # ROLE :
    #     Préparation des fichiers rasters pour le calcul des indicateurs LCZ
    #
    # ENTREES DE LA FONCTION :
    #     emprise_file : fichier d'emprise de la zone d'étude
    #     classif_input : raster classification OCS en entrée
    #     mns_input : raster modèle numérique de surface en entrée
    #     mnh_input : raster modèle numérique de hauteur en entrée
    #     classif_output : raster classification OCS en sortie, prêt pour le calcul des indicateurs
    #     mns_output : raster modèle numérique de surface en sortie, prêt pour le calcul des indicateurs
    #     mnh_output : raster modèle numérique de hauteur en sortie, prêt pour le calcul des indicateurs
    #     epsg : Type de projection (EPSG) de l'image de sortie
    #     no_data_value : Value pixel des no data
    #     path_time_log : fichier log de sortie
    #     format_raster : Format de l'image de sortie, par défaut : GTiff
    #     format_vector : format du fichier vecteur. Optionnel, par default : 'ESRI Shapefile'
    #     extension_raster : extension des fichiers raster de sortie, par defaut = '.tif'
    #     extension_vector : extension du fichier vecteur de sortie, par defaut = '.shp'
    #     save_results_intermediate : fichiers de sorties intermédiaires nettoyés, par défaut = False
    #     overwrite : écrase si un fichier existant a le même nom qu'un fichier de sortie, par défaut = True
    #
    # SORTIES DE LA FONCTION :
    #     N.A
    """

    print(bold + yellow + "Début de la préparation des fichiers rasters.\n" + endC)
    timeLine(path_time_log, "Début de la préparation des fichiers rasters : ")

    if debug >= 3 :
        print(bold + green + "rastersPreparation() : Variables dans la fonction" + endC)
        print(cyan + "rastersPreparation() : " + endC + "emprise_file : " + str(emprise_file) + endC)
        print(cyan + "rastersPreparation() : " + endC + "classif_input : " + str(classif_input) + endC)
        print(cyan + "rastersPreparation() : " + endC + "mns_input : " + str(mns_input) + endC)
        print(cyan + "rastersPreparation() : " + endC + "mnh_input : " + str(mnh_input) + endC)
        print(cyan + "rastersPreparation() : " + endC + "classif_output : " + str(classif_output) + endC)
        print(cyan + "rastersPreparation() : " + endC + "mns_output : " + str(mns_output) + endC)
        print(cyan + "rastersPreparation() : " + endC + "mnh_output : " + str(mnh_output) + endC)
        print(cyan + "rastersPreparation() : " + endC + "epsg : " + str(epsg))
        print(cyan + "rastersPreparation() : " + endC + "no_data_value : " + str(no_data_value))
        print(cyan + "rastersPreparation() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "rastersPreparation() : " + endC + "format_raster : " + str(format_raster) + endC)
        print(cyan + "rastersPreparation() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "rastersPreparation() : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "rastersPreparation() : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "rastersPreparation() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "rastersPreparation() : " + endC + "overwrite : " + str(overwrite) + endC)

    SUFFIX_VECTOR_BUFF = '_buff'

    if not os.path.exists(classif_output) or not os.path.exists(mns_output) or not os.path.exists(mnh_output) or overwrite:

        ############################################
        ### Préparation générale des traitements ###
        ############################################

        if not os.path.exists(os.path.dirname(classif_output)):
            os.makedirs(os.path.dirname(classif_output))
        if not os.path.exists(os.path.dirname(mns_output)):
            os.makedirs(os.path.dirname(mns_output))
        if not os.path.exists(os.path.dirname(mnh_output)):
            os.makedirs(os.path.dirname(mnh_output))

        emprise_buffer = os.path.splitext(emprise_file)[0] + SUFFIX_VECTOR_BUFF + extension_vector
        buffer_dist = 10
        bufferVector(emprise_file, emprise_buffer, buffer_dist, "", 1.0, 10, format_vector)

        ###################################
        ### Traitements sur les rasters ###
        ###################################

        images_input_list = [classif_input, mns_input, mnh_input]
        images_output_list = [classif_output, mns_output, mnh_output]

        cutRasterImages(images_input_list, emprise_buffer, images_output_list, 0, 0, epsg, no_data_value, "", False, path_time_log, format_raster, format_vector, extension_raster, extension_vector, save_results_intermediate, overwrite)

        ##########################################
        ### Nettoyage des fichiers temporaires ###
        ##########################################

        if not save_results_intermediate:
            if os.path.exists(emprise_buffer):
                removeVectorFile(emprise_buffer)

    else:
        print(bold + magenta + "La préparation des fichiers rasters a déjà eu lieu.\n" + endC)

    print(bold + yellow + "Fin de la préparation des fichiers rasters.\n" + endC)
    timeLine(path_time_log, "Fin de la préparation des fichiers rasters : ")

    return

#############################################################################################################################
################################################## Mise en place du parser ##################################################
#############################################################################################################################

def main(gui=False):
    parser = argparse.ArgumentParser(prog = "Preparation des donnees pour le calcul des indicateurs LCZ",
    description = """Preparation des donnees pour le calcul des indicateurs LCZ :
    Exemple : python /home/scgsi/Documents/ChaineTraitement/ScriptsLCZ/DataPreparation.py
                        -emp  /mnt/Donnees_Etudes/10_Agents/Benjamin/LCZ/Nancy/ZoneTest.shp
                        -in   /mnt/Donnees_Etudes/10_Agents/Benjamin/LCZ/Nancy/source_data/FR016L2_NANCY_UA2012.shp
                        -bil  /mnt/Donnees_Etudes/10_Agents/Benjamin/LCZ/Nancy/source_data/N_BATI_INDIFFERENCIE_BDT_054.SHP
                              /mnt/Donnees_Etudes/10_Agents/Benjamin/LCZ/Nancy/source_data/N_BATI_INDUSTRIEL_BDT_054.SHP
                              /mnt/Donnees_Etudes/10_Agents/Benjamin/LCZ/Nancy/source_data/N_BATI_REMARQUABLE_BDT_054.SHP
                              /mnt/Donnees_Etudes/10_Agents/Benjamin/LCZ/Nancy/source_data/N_CONSTRUCTION_LEGERE_BDT_054.SHP
                              /mnt/Donnees_Etudes/10_Agents/Benjamin/LCZ/Nancy/source_data/N_RESERVOIR_BDT_054.SHP
                        -ri   /mnt/Donnees_Etudes/10_Agents/Benjamin/LCZ/Nancy/source_data/N_TRONCON_ROUTE_BDT_054.SHP
                        -clai /mnt/Donnees_Etudes/10_Agents/Benjamin/LCZ/Nancy/source_data/ClassificationPleiadesOCS.tif
                        -mnsi /mnt/Donnees_Etudes/10_Agents/Benjamin/LCZ/Nancy/source_data/MNS_cleaned.tif
                        -mnhi /mnt/Donnees_Etudes/10_Agents/Benjamin/LCZ/Nancy/source_data/MNH_cleaned.tif
                        -out  /mnt/Donnees_Etudes/10_Agents/Benjamin/LCZ/Nancy/destination_data/UrbanAtlas.shp
                        -uac  /mnt/Donnees_Etudes/10_Agents/Benjamin/LCZ/Nancy/destination_data/UrbanAtlas_cleaned.shp
                        -bo   /mnt/Donnees_Etudes/10_Agents/Benjamin/LCZ/Nancy/destination_data/bati.shp
                        -ro   /mnt/Donnees_Etudes/10_Agents/Benjamin/LCZ/Nancy/destination_data/routes.shp
                        -clao /mnt/Donnees_Etudes/10_Agents/Benjamin/LCZ/Nancy/destination_data/classif.tif
                        -mnso /mnt/Donnees_Etudes/10_Agents/Benjamin/LCZ/Nancy/destination_data/MNS.tif
                        -mnho /mnt/Donnees_Etudes/10_Agents/Benjamin/LCZ/Nancy/destination_data/MNH.tif""")

    parser.add_argument('-emp', '--emprise_file', default="", help="Fichier d'emprise de la zone d'etude (vecteur).", type=str, required=True)
    parser.add_argument('-in', '--grid_input', default="", help="Fichier Urban Atlas d'origine (vecteur).", type=str, required=True)
    parser.add_argument('-bil', '--built_input_list', nargs="+", default=[], help="Liste des fichiers built de la BD TOPO a assembler (vecteurs).", type=str, required=True)
    parser.add_argument('-ril', '--roads_input_list', nargs="+", default=[], help="Liste des fichiers routes de la BD TOPO a traiter (vecteurs).", type=str, required=True)
    parser.add_argument('-clai', '--classif_input', default="", help="Classification OCS en entree (raster).", type=str, required=True)
    parser.add_argument('-mnsi', '--mns_input', default="", help="Modele numerique de surface en entree (raster).", type=str, required=True)
    parser.add_argument('-mnhi', '--mnh_input', default="", help="Modele numerique de hauteur en entree (raster).", type=str, required=True)
    parser.add_argument('-out', '--grid_output', default="", help="Fichier Urban Atlas prepare pour le calcul des indicateurs, complet (vecteur).", type=str, required=True)
    parser.add_argument('-uac', '--grid_output_cleaned', default="", help="Fichier Urban Atlas prepare pour le calcul des indicateurs, nettoye des polygones axes de communications et eau (vecteur).", type=str, required=True)
    parser.add_argument('-bo', '--built_output', default="", help="Fichier built prepare pour le calcul des indicateurs (vecteur).", type=str, required=True)
    parser.add_argument('-ro', '--roads_output', default="", help="Fichier routes prepare pour le calcul des indicateurs (vecteur).", type=str, required=True)
    parser.add_argument('-clao', '--classif_output', default="", help="Classification OCS decoupee (raster).", type=str, required=True)
    parser.add_argument('-mnso', '--mns_output', default="", help="Modele numerique de surface decoupe (raster).", type=str, required=True)
    parser.add_argument('-mnho', '--mnh_output', default="", help="Modele numerique de hauteur decoupe (raster).", type=str, required=True)
    parser.add_argument('-code', '--col_code_ua', default="CODE201", help="Nom de la colonne 'code' du fichier Urban Atlas.", type=str, required=False)
    parser.add_argument('-item', '--col_item_ua', default="ITEM201", help="Nom de la colonne 'item' du fichier Urban Atlas.", type=str, required=False)
    parser.add_argument('-epsg','--epsg', default=2154, help="Option : Type output image projection (EPSG),by default the same projection as the input images", type=int, required=False)
    parser.add_argument('-ndv','--no_data_value', default=-1, help="Option : Value of the pixel no data. By default : -1", type=int, required=False)
    parser.add_argument('-raf','--format_raster', default="GTiff", help="Option : Format output image, by default : GTiff (GTiff, HFA...)", type=str, required=False)
    parser.add_argument('-vef','--format_vector', default="ESRI Shapefile",help="Format of the output file.", type=str, required=False)
    parser.add_argument('-rae','--extension_raster', default=".tif", help="Option : Extension file for image raster. By default : '.tif'", type=str, required=False)
    parser.add_argument('-vee','--extension_vector',default=".shp",help="Option : Extension file for vector. By default : '.shp'", type=str, required=False)
    parser.add_argument('-log', '--path_time_log', default="", help="Name of log", type=str, required=False)
    parser.add_argument('-sav', '--save_results_intermediate', default=False, action='store_true', help="Save or delete intermediate result after the process. By default, False", required=False)
    parser.add_argument('-now', '--overwrite', action='store_false', default=True, help="Overwrite files with same names. By default, True", required=False)
    parser.add_argument('-debug', '--debug', default=3, help="Option : Value of level debug trace, default : 3", type=int, required=False)
    args = displayIHM(gui, parser)

    if args.emprise_file!= None:
        emprise_file = args.emprise_file

    if args.grid_input!= None:
        grid_input = args.grid_input

    if args.built_input_list!= None:
        built_input_list = args.built_input_list
    if args.roads_input_list!= None:
        roads_input_list = args.roads_input_list

    if args.classif_input!= None:
        classif_input = args.classif_input
    if args.mns_input!= None:
        mns_input = args.mns_input
    if args.mnh_input!= None:
        mnh_input = args.mnh_input

    if args.grid_output!= None:
        grid_output = args.grid_output
    if args.grid_output_cleaned!= None:
        grid_output_cleaned = args.grid_output_cleaned

    if args.built_output!= None:
        built_output = args.built_output
    if args.roads_output!= None:
        roads_output = args.roads_output

    if args.classif_output!= None:
        classif_output = args.classif_output
    if args.mns_output!= None:
        mns_output = args.mns_output
    if args.mnh_output!= None:
        mnh_output = args.mnh_output

    if args.col_code_ua!= None:
        col_code_ua = args.col_code_ua
    if args.col_item_ua!= None:
        col_item_ua = args.col_item_ua

    # Paramètre valeur de la projection des images de sorties
    if args.epsg != None:
        epsg = args.epsg

    # Parametres de valeur du nodata des fichiers de sortie
    if args.no_data_value!= None:
        no_data_value = args.no_data_value

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

    # Récupération de l'option de sauvegarde des fichiers intermédiaires
    if args.save_results_intermediate != None:
        save_results_intermediate = args.save_results_intermediate

    # Récupération de l'option écrasement
    if args.overwrite!= None:
        overwrite = args.overwrite

    # Récupération de l'option niveau de debug
    if args.debug!= None:
        global debug
        debug = args.debug

    if debug >= 3:
        print(bold + green + "Calcul du pourcentage de surface bâtie :" + endC)
        print(cyan + "DataPreparation : " + endC + "emprise_file : " + str(emprise_file) + endC)
        print(cyan + "DataPreparation : " + endC + "grid_input : " + str(grid_input) + endC)
        print(cyan + "DataPreparation : " + endC + "built_input_list : " + str(built_input_list) + endC)
        print(cyan + "DataPreparation : " + endC + "roads_input_list : " + str(roads_input_list) + endC)
        print(cyan + "DataPreparation : " + endC + "classif_input : " + str(classif_input) + endC)
        print(cyan + "DataPreparation : " + endC + "mns_input : " + str(mns_input) + endC)
        print(cyan + "DataPreparation : " + endC + "mnh_input : " + str(mnh_input) + endC)
        print(cyan + "DataPreparation : " + endC + "grid_output : " + str(grid_output) + endC)
        print(cyan + "DataPreparation : " + endC + "grid_output_cleaned : " + str(grid_output_cleaned) + endC)
        print(cyan + "DataPreparation : " + endC + "built_output : " + str(built_output) + endC)
        print(cyan + "DataPreparation : " + endC + "roads_output : " + str(roads_output) + endC)
        print(cyan + "DataPreparation : " + endC + "classif_output : " + str(classif_output) + endC)
        print(cyan + "DataPreparation : " + endC + "mns_output : " + str(mns_output) + endC)
        print(cyan + "DataPreparation : " + endC + "mnh_output : " + str(mnh_output) + endC)
        print(cyan + "DataPreparation : " + endC + "col_code_ua : " + str(col_code_ua) + endC)
        print(cyan + "DataPreparation : " + endC + "col_item_ua : " + str(col_item_ua) + endC)
        print(cyan + "DataPreparation : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "DataPreparation : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "DataPreparation : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "DataPreparation : " + endC + "format_raster : " + str(format_raster) + endC)
        print(cyan + "DataPreparation : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "DataPreparation : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "DataPreparation : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "DataPreparation : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "DataPreparation : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "DataPreparation : " + endC + "debug : " + str(debug) + endC)

    if not os.path.exists(os.path.dirname(grid_output)):
        os.makedirs(os.path.dirname(grid_output))
    if not os.path.exists(os.path.dirname(grid_output_cleaned)):
        os.makedirs(os.path.dirname(grid_output_cleaned))
    if not os.path.exists(os.path.dirname(built_output)):
        os.makedirs(os.path.dirname(built_output))
    if not os.path.exists(os.path.dirname(roads_output)):
        os.makedirs(os.path.dirname(roads_output))
    if not os.path.exists(os.path.dirname(classif_output)):
        os.makedirs(os.path.dirname(classif_output))
    if not os.path.exists(os.path.dirname(mns_output)):
        os.makedirs(os.path.dirname(mns_output))
    if not os.path.exists(os.path.dirname(mnh_output)):
        os.makedirs(os.path.dirname(mnh_output))

    vectorsPreparation(emprise_file, classif_input, grid_input, built_input_list, roads_input_list, grid_output, grid_output_cleaned, built_output, roads_output, col_code_ua, col_item_ua, epsg, path_time_log, format_vector, extension_vector, save_results_intermediate, overwrite)
    rastersPreparation(emprise_file, classif_input, mns_input, mnh_input, classif_output, mns_output, mnh_output, epsg, no_data_value, path_time_log, format_raster, format_vector, extension_raster, extension_vector, save_results_intermediate, overwrite)

if __name__ == '__main__':
    main(gui=False)

