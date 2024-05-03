#!/usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

from __future__ import print_function
import os, sys, argparse, shutil, time
from Lib_log import timeLine
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_raster import getPixelWidthXYImage, cutImageByVector, createVectorMask
from Lib_vector import createGridVector, splitVector, bufferVector, cutVector, renameFieldsVector
from Lib_file import removeVectorFile, cleanTempData, deleteDir
from Lib_saga import computeSkyViewFactor
from ImagesAssembly import selectAssembyImagesByHold
from CrossingVectorRaster import statisticsVectorRaster

debug = 3

####################################################################################################
# FONCTION skyViewFactor()                                                                         #
####################################################################################################
def skyViewFactor(grid_input, grid_output, mns_input, classif_input, class_build_list, dim_grid_x, dim_grid_y, svf_radius, svf_method, svf_dlevel, svf_ndirs, epsg, no_data_value, path_time_log, format_raster='GTiff', format_vector='ESRI Shapefile', extension_raster=".tif", extension_vector=".shp", save_results_intermediate=False, overwrite=True):
    """
    # ROLE :
    #     Calcul de l'indicateur LCZ facteur de vue du ciel
    #
    # ENTREES DE LA FONCTION :
    #     grid_input : fichier Urban Atlas en entrée
    #     grid_output : fichier Urban Atlas en sortie
    #     mns_input : modèle numérique de surface en entrée
    #     classif_input : classification de l'occupation du sol en entrée
    #     class_build_list : liste des classes choisis pour definir les zones baties
    #     dim_grid_x : largeur des carreaux du quadrillage (en mètres)
    #     dim_grid_y : hauteur des carreaux du quadrillage (en mètres)
    #     svf_radius : paramètre 'radius' du Sky View Factor sous SAGA (en mètres)
    #     svf_method : paramètre 'method' du Sky View Factor sous SAGA
    #     svf_dlevel : paramètre 'dlevel' du Sky View Factor sous SAGA
    #     svf_ndirs :  paramètre 'ndirs' du Sky View Factor sous SAGA
    #     epsg : EPSG code de projection
    #     no_data_value : Valeur des pixels sans données pour les rasters
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

    print(bold + yellow + "Début du calcul de l'indicateur Sky View Factor." + endC + "\n")
    timeLine(path_time_log, "Début du calcul de l'indicateur Sky View Factor : ")

    if debug >= 3 :
        print(bold + green + "skyViewFactor() : Variables dans la fonction" + endC)
        print(cyan + "skyViewFactor() : " + endC + "grid_input : " + str(grid_input) + endC)
        print(cyan + "skyViewFactor() : " + endC + "grid_output : " + str(grid_output) + endC)
        print(cyan + "skyViewFactor() : " + endC + "mns_input : " + str(mns_input) + endC)
        print(cyan + "skyViewFactor() : " + endC + "class_build_list : " + str(class_build_list) + endC)
        print(cyan + "skyViewFactor() : " + endC + "classif_input : " + str(classif_input) + endC)
        print(cyan + "skyViewFactor() : " + endC + "dim_grid_x : " + str(dim_grid_x) + endC)
        print(cyan + "skyViewFactor() : " + endC + "dim_grid_y : " + str(dim_grid_y) + endC)
        print(cyan + "skyViewFactor() : " + endC + "svf_radius : " + str(svf_radius) + endC)
        print(cyan + "skyViewFactor() : " + endC + "svf_method : " + str(svf_method) + endC)
        print(cyan + "skyViewFactor() : " + endC + "svf_dlevel : " + str(svf_dlevel) + endC)
        print(cyan + "skyViewFactor() : " + endC + "svf_ndirs : " + str(svf_ndirs) + endC)
        print(cyan + "skyViewFactor() : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "skyViewFactor() : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "skyViewFactor() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "skyViewFactor() : " + endC + "format_raster : " + str(format_raster) + endC)
        print(cyan + "skyViewFactor() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "skyViewFactor() : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "skyViewFactor() : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "skyViewFactor() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "skyViewFactor() : " + endC + "overwrite : " + str(overwrite) + endC)

    # Constantes liées aux fichiers
    SKY_VIEW_FIELD = 'SkyView'

    BASE_FILE_TILE = 'tile_'
    BASE_FILE_POLY = 'poly_'
    SUFFIX_VECTOR_BUFF = '_buff'
    SUFFIX_VECTOR_TEMP = '_temp'

    # Constantes liées à l'arborescence
    FOLDER_SHP = 'SHP'
    FOLDER_SGRD = 'SGRD'
    FOLDER_TIF = 'TIF'
    SUB_FOLDER_DEM = 'DEM'
    SUB_FOLDER_SVF = 'SVF'
    SUB_SUB_FOLDER_BUF = 'BUF'

    if not os.path.exists(grid_output) or overwrite:

        ############################################
        ### Préparation générale des traitements ###
        ############################################

        if os.path.exists(grid_output):
            removeVectorFile(grid_output)

        temp_path = os.path.dirname(grid_output) + os.sep + "SkyViewFactor"
        sky_view_factor_raster = temp_path + os.sep + "sky_view_factor" + extension_raster

        cleanTempData(temp_path)
        os.makedirs(temp_path + os.sep + FOLDER_SHP)
        os.makedirs(temp_path + os.sep + FOLDER_SGRD + os.sep + SUB_FOLDER_DEM)
        os.makedirs(temp_path + os.sep + FOLDER_SGRD + os.sep + SUB_FOLDER_SVF)
        os.makedirs(temp_path + os.sep + FOLDER_TIF + os.sep + SUB_FOLDER_DEM)
        os.makedirs(temp_path + os.sep + FOLDER_TIF + os.sep + SUB_FOLDER_SVF)
        os.makedirs(temp_path + os.sep + FOLDER_TIF + os.sep + SUB_FOLDER_SVF + os.sep + SUB_SUB_FOLDER_BUF)

        # Récupération de la résolution du raster d'entrée
        pixel_size_x, pixel_size_y = getPixelWidthXYImage(mns_input)
        print(bold + "Taille de pixel du fichier '%s' :" % (mns_input) + endC)
        print("    pixel_size_x = " + str(pixel_size_x))
        print("    pixel_size_y = " + str(pixel_size_y) + "\n")

        ###############################################
        ### Création des fichiers emprise et grille ###
        ###############################################

        print(bold + cyan + "Création des fichiers emprise et grille :" + endC)
        timeLine(path_time_log, "    Création des fichiers emprise et grille : ")

        emprise_file = temp_path + os.sep + "emprise" + extension_vector
        quadrillage_file = temp_path + os.sep + "quadrillage" + extension_vector

        # Création du fichier d'emprise
        createVectorMask(mns_input, emprise_file, no_data_value, format_vector)

        # Création du fichier grille
        createGridVector(emprise_file, quadrillage_file, dim_grid_x, dim_grid_y, None, overwrite, epsg, format_vector)

        #############################################################
        ### Extraction des carreaux de découpage et bufferisation ###
        #############################################################

        print(bold + cyan + "Extraction des carreaux de découpage :" + endC)
        timeLine(path_time_log, "    Extraction des carreaux de découpage : ")

        split_tile_vector_list = splitVector(quadrillage_file, temp_path + os.sep + FOLDER_SHP, "", epsg, format_vector, extension_vector)

        split_tile_vector_buff_list = []

        # Boucle sur les fichiers polygones quadrillage
        for split_tile_vector in split_tile_vector_list:
            repertory_temp_output = os.path.dirname(split_tile_vector)
            base_name = os.path.splitext(os.path.basename(split_tile_vector))[0]
            split_tile_buff_vector = repertory_temp_output + os.sep + base_name + SUFFIX_VECTOR_BUFF + extension_vector
            split_tile_buff_vector_temp = repertory_temp_output + os.sep + base_name + SUFFIX_VECTOR_BUFF + SUFFIX_VECTOR_TEMP + extension_vector

            # Bufferisation
            bufferVector(split_tile_vector, split_tile_buff_vector_temp, svf_radius, "", 1.0, 10, format_vector)

            # Re-découpage avec l'emprise si la taille intersecte avec l'emprise
            if cutVector(emprise_file, split_tile_buff_vector_temp, split_tile_buff_vector, overwrite, format_vector) :
                split_tile_vector_buff_list.append(split_tile_buff_vector)

        ##########################################################
        ### Découpage du MNS/MNH à l'emprise de chaque carreau ###
        ##########################################################

        print(bold + cyan + "Découpage du raster en tuiles :" + endC)
        timeLine(path_time_log, "    Découpage du raster en tuiles : ")

        # Boucle sur les fichiers polygones quadrillage bufferisés
        for i in range(len(split_tile_vector_list)):
            print("Traitement de la tuile " + str(int(i)+1) + str(len(split_tile_vector_list)) + "...")

            split_tile_vector = split_tile_vector_list[i]
            repertory_temp_output = os.path.dirname(split_tile_vector)
            base_name = os.path.splitext(os.path.basename(split_tile_vector))[0]
            split_tile_buff_vector = repertory_temp_output + os.sep + base_name + SUFFIX_VECTOR_BUFF + extension_vector
            dem_tif_file = temp_path + os.sep + FOLDER_TIF + os.sep + SUB_FOLDER_DEM + os.sep + BASE_FILE_TILE + str(i) + extension_raster

            if os.path.exists(split_tile_buff_vector):
                cutImageByVector(split_tile_buff_vector, mns_input, dem_tif_file, pixel_size_x, pixel_size_y, False, no_data_value, epsg, format_raster, format_vector)

        ##################################################
        ### Calcul du SVF pour chaque dalle du MNS/MNH ###
        ##################################################

        print(bold + cyan + "Calcul du SVF pour chaque tuile via SAGA :" + endC)
        timeLine(path_time_log, "    Calcul du SVF pour chaque tuile via SAGA : ")

        svf_buf_tif_file_list = []

        # Boucle sur les tuiles du raster d'entrée créées par chaque polygone quadrillage
        for i in range(len(split_tile_vector_list)):
            # Calcul de Sky View Factor par SAGA
            dem_tif_file = temp_path + os.sep + FOLDER_TIF + os.sep + SUB_FOLDER_DEM + os.sep + BASE_FILE_TILE + str(i) + extension_raster
            svf_buf_tif_file = temp_path + os.sep + FOLDER_TIF + os.sep + SUB_FOLDER_SVF + os.sep + SUB_SUB_FOLDER_BUF + os.sep + BASE_FILE_TILE + str(i) + extension_raster

            if os.path.exists(dem_tif_file):
                computeSkyViewFactor(dem_tif_file, svf_buf_tif_file, svf_radius, svf_method, svf_dlevel, svf_ndirs, save_results_intermediate)
                svf_buf_tif_file_list.append(svf_buf_tif_file)

        ###################################################################
        ### Re-découpage des tuiles du SVF avec les tuilles sans tampon ###
        ###################################################################

        print(bold + cyan + "Re-découpage des tuiles du SVF avec les tuilles sans tampon :" + endC)
        timeLine(path_time_log, "    Re-découpage des tuiles du SVF avec les tuilles sans tampon : ")

        folder_output_svf = temp_path + os.sep + FOLDER_TIF + os.sep + SUB_FOLDER_SVF + os.sep

        # Boucle sur les tuiles du SVF bufferisées
        for i in range(len(split_tile_vector_list)):
            print("Traitement de la tuile " + str(int(i)+1) + "/" + str(len(split_tile_vector_list)) + "...")

            split_tile_vector = split_tile_vector_list[i]
            svf_buf_tif_file = temp_path + os.sep + FOLDER_TIF + os.sep + SUB_FOLDER_SVF + os.sep + SUB_SUB_FOLDER_BUF + os.sep + BASE_FILE_TILE + str(i) + extension_raster
            base_name = os.path.splitext(os.path.basename(svf_buf_tif_file))[0]
            svf_tif_file = folder_output_svf + os.sep + base_name + extension_raster
            if os.path.exists(svf_buf_tif_file):
                cutImageByVector(split_tile_vector, svf_buf_tif_file, svf_tif_file, pixel_size_x, pixel_size_y, False, no_data_value, epsg, format_raster, format_vector)

        ####################################################################
        ### Assemblage des tuiles du SVF et calcul de l'indicateur final ###
        ####################################################################

        print(bold + cyan + "Assemblage des tuiles du SVF et calcul de l'indicateur final :" + endC)
        timeLine(path_time_log, "    Assemblage des tuiles du SVF et calcul de l'indicateur final : ")

        classif_input_temp = temp_path + os.sep + FOLDER_TIF + os.sep + "classif_input" + SUFFIX_VECTOR_TEMP + extension_raster
        sky_view_factor_temp = temp_path + os.sep + FOLDER_TIF + os.sep + "sky_view_factor" + SUFFIX_VECTOR_TEMP + extension_raster # Issu de l'assemblage des dalles
        sky_view_factor_temp_temp = temp_path + os.sep + FOLDER_TIF + os.sep + "sky_view_factor" + SUFFIX_VECTOR_TEMP + SUFFIX_VECTOR_TEMP + extension_raster # Issu du redécoupage pour entrer correctement dans le BandMath

        # Assemblage des tuiles du SVF créées précédemment pour ne former qu'un seul raster SVF
        selectAssembyImagesByHold(emprise_file, [folder_output_svf], sky_view_factor_temp, False, False, epsg, False, False, False, False, 1.0, pixel_size_x, pixel_size_y, no_data_value, "_", 2, 8, "", path_time_log, "_error", "_merge", "_clean", "_stack", format_raster, format_vector, extension_raster, extension_vector, save_results_intermediate, overwrite)

        # Redécoupage de l'OCS et du SVF pour la superposition nécessaire au BandMath
        cutImageByVector(emprise_file, classif_input, classif_input_temp, pixel_size_x, pixel_size_y, True, no_data_value, epsg, format_raster, format_vector)
        cutImageByVector(emprise_file, sky_view_factor_temp, sky_view_factor_temp_temp, pixel_size_x, pixel_size_y, True, no_data_value, epsg, format_raster, format_vector)

        # Suppression des valeurs de SVF pour les classes OCS non-pertinentes (bâtiments + arbres, voire surfaces en eau)
        expression = ""
        for id_class in class_build_list :
            expression += "im1b1==%s or " %(str(id_class))
        command = "otbcli_BandMath -il %s %s -out \"%s?&nodata=-1\" float -exp '%s ? -1 : (im2b1<=0 ? -1 : im2b1)'" % (classif_input_temp, sky_view_factor_temp_temp, sky_view_factor_raster, expression[:-4])
        if debug >= 3 :
            print(command)
        exit_code = os.system(command)
        if exit_code != 0:
            print(command)
            print(cyan + "skyViewFactor() : " + bold + red + "!!! Une erreur c'est produite au cours de la commande otbcli_BandMath : " + command + ". Voir message d'erreur." + endC, file=sys.stderr)
            raise

        # Croisement vecteur-raster pour récupérer la moyenne de SVF par polygone du fichier maillage d'entrée
        col_to_delete_list = ["min", "max", "median", "sum", "std", "unique", "range"]
        statisticsVectorRaster(sky_view_factor_raster, grid_input, grid_output, 1, False, False, True, col_to_delete_list, [], {}, True, no_data_value, format_vector, path_time_log, save_results_intermediate, overwrite)

        renameFieldsVector(grid_output, ['mean'], [SKY_VIEW_FIELD], format_vector)

        ##########################################
        ### Nettoyage des fichiers temporaires ###
        ##########################################

        if not save_results_intermediate:
            deleteDir(temp_path)

    else:
        print(bold + magenta + "Le calcul du Sky View Factor a déjà eu lieu." + endC + "\n")

    print(bold + yellow + "Fin du calcul de l'indicateur Sky View Factor." + endC + "\n")
    timeLine(path_time_log, "Fin du calcul de l'indicateur Sky View Factor : ")

    return

#############################################################################################################################
################################################## Mise en place du parser ##################################################
#############################################################################################################################

def main(gui=False):
    parser = argparse.ArgumentParser(prog = "Calcul du facteur de vue du ciel (Sky View Factor)",
    description = """Calcul de l'indicateur LCZ facteur de vue du ciel (Sky View Factor) :
    Exemple : python /home/scgsi/Documents/ChaineTraitement/ScriptsLCZ/SkyViewFactor.py
                        -in  /mnt/Donnees_Etudes/10_Agents/Benjamin/LCZ/Nancy/UrbanAtlas.shp
                        -out /mnt/Donnees_Etudes/10_Agents/Benjamin/LCZ/Nancy/SkyViewFactor.shp
                        -dem /mnt/Donnees_Etudes/10_Agents/Benjamin/LCZ/Nancy/MNS.tif
                        -cla /mnt/Donnees_Etudes/10_Agents/Benjamin/LCZ/Nancy/Classif.tif
                        -dx 1000 -dy 1000 -rad 50.0 -met 1 -snd 3""",
    epilog = "Pour les parametres specifiques a SAGA, se reporter a la documentation associee (http://www.saga-gis.org/saga_module_doc/2.2.0/ta_lighting_3.html)")

    parser.add_argument('-in', '--grid_input', default="", type=str, required=True, help="Fichier Urban Atlas en entree (vecteur).")
    parser.add_argument('-out', '--grid_output', default="", type=str, required=True, help="Fichier Urban Atlas en sortie, avec la valeur moyenne du Sky View Factor par maille (vecteur).")
    parser.add_argument('-mns', '--mns_input', default="", type=str, required=True, help="Modele numerique de surface en entree (raster).")
    parser.add_argument('-cla', '--classif_input', default="", type=str, required=True, help="Classification de l'occupation du sol en entree (raster).")
    parser.add_argument('-cbl', '--class_build_list', nargs="+", default=[11100], type=int, required=False, help="Liste des indices de classe de type bati.")
    parser.add_argument('-dx', '--dim_grid_x', default=1000, type=int, required=False, help="Largeur des carreaux du quadrillage (en metres), par defaut 1000.")
    parser.add_argument('-dy', '--dim_grid_y', default=1000, type=int, required=False, help="Hauteur des carreaux du quadrillage (en metres), par defaut 1000.")
    parser.add_argument('-rad', '--svf_radius', default=50.0, type=float, required=False, help="Parametre du Sky View Factor sous SAGA, par defaut 50.")
    parser.add_argument('-met', '--svf_method', default=1, type=int, required=False, help="Parametre du Sky View Factor sous SAGA, par defaut 1.")
    parser.add_argument('-sdl', '--svf_dlevel', default=3.0, type=float, required=False, help="Parametre du Sky View Factor sous SAGA, par defaut 3.")
    parser.add_argument('-snd', '--svf_ndirs', default=3, type=int, required=False, help="Parametre du Sky View Factor sous SAGA, par defaut 3.")
    parser.add_argument('-epsg','--epsg', default=2154,help="EPSG code projection.", type=int, required=False)
    parser.add_argument("-ndv",'--no_data_value',default=0,help="Option : Pixel value for raster file to no data, default : 0 ", type=int, required=False)
    parser.add_argument('-raf','--format_raster', default="GTiff", help="Option : Format output image, by default : GTiff (GTiff, HFA...)", type=str, required=False)
    parser.add_argument('-vef','--format_vector',default="ESRI Shapefile",help="Option : Vector format. By default : ESRI Shapefile", type=str, required=False)
    parser.add_argument('-rae','--extension_raster', default=".tif", help="Option : Extension file for image raster. By default : '.tif'", type=str, required=False)
    parser.add_argument('-vee','--extension_vector',default=".shp",help="Option : Extension file for vector. By default : '.shp'", type=str, required=False)
    parser.add_argument('-log', '--path_time_log', default="", type=str, required=False, help="Name of log")
    parser.add_argument('-sav', '--save_results_intermediate', action='store_true', default=False, required=False, help="Save or delete intermediate result after the process. By default, False")
    parser.add_argument('-now', '--overwrite', action='store_false', default=True, required=False, help="Overwrite files with same names. By default, True")
    parser.add_argument('-debug', '--debug', default=3, type=int, required=False, help="Option : Value of level debug trace, default : 3")
    args = displayIHM(gui, parser)

    # Récupération du vecteur grille d'entrée
    if args.grid_input != None:
        grid_input = args.grid_input

    # Récupération du vecteur grille de sortie
    if args.grid_output != None:
        grid_output = args.grid_output

    # Récupération du fichier raster mms
    if args.mns_input != None:
        mns_input = args.mns_input

    # Récupération du fichier raster ocs
    if args.classif_input != None:
        classif_input = args.classif_input

    # Récupération de la liste des classes bati
    if args.class_build_list != None:
        class_build_list = args.class_build_list

    # Récupération des parametres du calcul de skyview
    if args.dim_grid_x != None:
        dim_grid_x = args.dim_grid_x
    if args.dim_grid_y != None:
        dim_grid_y = args.dim_grid_y

    if args.svf_radius != None:
        svf_radius = args.svf_radius
    if args.svf_method != None:
        svf_method = args.svf_method
    if args.svf_dlevel != None:
        svf_dlevel = args.svf_dlevel
    if args.svf_ndirs != None:
        svf_ndirs = args.svf_ndirs

    # Paramettre de projection
    if args.epsg != None:
        epsg = args.epsg

    # Paramettre des no data
    if args.no_data_value != None:
        no_data_value = args.no_data_value

    # Paramètre format des images de sortie
    if args.format_raster != None:
        format_raster = args.format_raster

    # Récupération du nom du format des fichiers vecteur
    if args.format_vector != None:
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
        print(bold + green + "Calcul du facteur de vue du ciel :" + endC)
        print(cyan + "SkyViewFactor : " + endC + "grid_input : " + str(grid_input) + endC)
        print(cyan + "SkyViewFactor : " + endC + "grid_output : " + str(grid_output) + endC)
        print(cyan + "SkyViewFactor : " + endC + "mns_input : " + str(mns_input) + endC)
        print(cyan + "SkyViewFactor : " + endC + "classif_input : " + str(classif_input) + endC)
        print(cyan + "SkyViewFactor : " + endC + "class_build_list : " + str(class_build_list) + endC)
        print(cyan + "SkyViewFactor : " + endC + "dim_grid_x : " + str(dim_grid_x) + endC)
        print(cyan + "SkyViewFactor : " + endC + "dim_grid_y : " + str(dim_grid_y) + endC)
        print(cyan + "SkyViewFactor : " + endC + "svf_radius : " + str(svf_radius) + endC)
        print(cyan + "SkyViewFactor : " + endC + "svf_method : " + str(svf_method) + endC)
        print(cyan + "SkyViewFactor : " + endC + "svf_dlevel : " + str(svf_dlevel) + endC)
        print(cyan + "SkyViewFactor : " + endC + "svf_ndirs : " + str(svf_ndirs) + endC)
        print(cyan + "SkyViewFactor : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "SkyViewFactor : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "SkyViewFactor : " + endC + "format_raster : " + str(format_raster) + endC)
        print(cyan + "SkyViewFactor : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "SkyViewFactor : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "SkyViewFactor : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "SkyViewFactor : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "SkyViewFactor : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "SkyViewFactor : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "SkyViewFactor : " + endC + "debug : " + str(debug) + endC)
        print("\n")

    if not os.path.exists(os.path.dirname(grid_output)):
        os.makedirs(os.path.dirname(grid_output))

    skyViewFactor(grid_input, grid_output, mns_input, classif_input, class_build_list, dim_grid_x, dim_grid_y, svf_radius, svf_method, svf_dlevel, svf_ndirs, epsg, no_data_value, path_time_log, format_raster, format_vector, extension_raster, extension_vector, save_results_intermediate, overwrite)

if __name__ == '__main__':
    main(gui=False)

