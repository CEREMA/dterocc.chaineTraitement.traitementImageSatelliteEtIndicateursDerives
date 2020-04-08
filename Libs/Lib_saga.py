# -*- coding: utf-8 -*-
#!/usr/bin/python

#############################################################################
# Copyright (©) CEREMA/DTerSO/DALETT/SCGSI  All rights reserved.            #
#############################################################################

#############################################################################
#                                                                           #
# FONCTIONS POUR L'APPEL À DES FONCTIONS SAGA                               #
#                                                                           #
#############################################################################

import sys,os
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC
from Lib_operator import *
from Lib_file import cleanTempData, deleteDir

# debug = 0 : affichage minimum de commentaires lors de l'exécution du script
# debug = 3 : affichage maximum de commentaires lors de l'exécution du script. Intermédiaire : affichage intermédiaire

debug = 3

# ATTENTION : pour appeler SAGA, il faut avoir installé l'outil SAGA sur la machine hôte

#########################################################################
# FONCTION importGtiff2Sgrd()                                           #
#########################################################################
#   Rôle : cette fonction permet d'importer un fichier Gtiff en fichier SGRD (fichier 'grid' SAGA)
#   Paramètres :
#       input_gtiff : raster d'entrée sous format GTiff (ou autre)
#       output_sgrd : raster de sortie sous format SGRD (SAGA grid)

def importGtiff2Sgrd(input_gtiff, output_sgrd):

    print(bold + "Import SAGA : " + endC + input_gtiff + " vers " + output_sgrd)
    command = "saga_cmd io_gdal 0 -FILES %s -GRIDS %s" % (input_gtiff, output_sgrd)
    exitCode = os.system(command)
    if exitCode != 0 :
        print(command)
        raise NameError(bold + red + "importGtiff2Sgrd(): An error occured during execution SAGA convert GTiff file '%s' to SAGA file '%s'. See error message above." + endC) % (str(input_gtiff), str(output_sgrd))

    return

#########################################################################
# FONCTION exportSgrd2Gtiff()                                           #
#########################################################################
#   Rôle : cette fonction permet d'exporter un fichier SGRD (fichier 'grid' SAGA) en fichier Gtiff
#   Paramètres :
#       input_sgrd : raster d'entrée sous format SGRD (SAGA grid)
#       output_gtiff : raster de sortie sous format GTiff (ou autre)

def exportSgrd2Gtiff(input_sgrd, output_gtiff):

    print(bold + "Export SAGA : " + endC + input_sgrd + " vers " + output_gtiff)
    command = "saga_cmd io_gdal 2 -GRIDS %s -FILE %s" % (input_sgrd, output_gtiff)
    exitCode = os.system(command)
    if exitCode != 0 :
        print(command)
        raise NameError(bold + red + "exportSgrd2Gtiff(): An error occured during execution SAGA convert SAGA file '%s' to GTiff file '%s'. See error message above." + endC) % (str(input_sgrd), str(output_gtiff))

    return

#########################################################################
# FONCTION fillNodata()                                                 #
#########################################################################
#   Rôle : Cette fonction permet de remplir des zones de pixels defini comme nodata par interpolation de pixels voisins
#   Paramètres :
#       image_input : fichier image d'entrée une bande
#       image_mask_input : fichier maske binaire (0 et autre valeur) definissant les zone utiles (optionel peut etre vide dans ce cas pas de masque)
#       image_output : fichier image de sortie avec les zones nodata remplies
#       save_results_intermediate : fichiers de sorties intermediaires nettoyees, par defaut = False

def fillNodata(image_input, image_mask_input, image_output, save_results_intermediate=False):

    if debug >= 2:
        print(cyan + "fillNodata() : " + bold + "Remplissage des valeurs NoData sous SAGA, à partir du fichier : " + endC + image_input)

    # Constantes
    SUFFIX_TMP = "_tmp"
    SUFFIX_SAGA = "_saga"
    EXT_GRID_SAGA = '.sgrd'

    # Variables
    repertory_output = os.path.dirname(image_output)
    basename_image_input = os.path.splitext(os.path.basename(image_input))[0]
    basename_image_output = os.path.splitext(os.path.basename(image_output))[0]

    sub_repertory_temp_saga = repertory_output + os.sep + basename_image_output + SUFFIX_TMP + SUFFIX_SAGA
    image_input_saga = sub_repertory_temp_saga + os.sep + basename_image_input + EXT_GRID_SAGA
    image_output_saga = sub_repertory_temp_saga + os.sep + basename_image_output + EXT_GRID_SAGA

    if image_mask_input != "" :
        basename_image_mask_input = os.path.splitext(os.path.basename(image_mask_input))[0]
        image_mask_input_saga = sub_repertory_temp_saga + os.sep + basename_image_mask_input + EXT_GRID_SAGA

    # Nettoyage du répertoire temporaire
    cleanTempData(sub_repertory_temp_saga)

    # Import de raster(s) sous SAGA
    importGtiff2Sgrd(image_input, image_input_saga)
    if image_mask_input != "":
        importGtiff2Sgrd(image_mask_input, image_mask_input_saga)

    # Utilisation de la fonction "Close Gaps" de SAGA pour boucher les trous de NoData
    if image_mask_input != "":
        command = "saga_cmd grid_tools 7 -INPUT %s -MASK %s -RESULT %s" % (image_input_saga, image_mask_input_saga, image_output_saga)
    else:
        command = "saga_cmd grid_tools 7 -INPUT %s -RESULT %s" % (image_input_saga, image_output_saga)

    exitCode = os.system(command)
    if exitCode != 0 :
        print(command)
        raise NameError(bold + red + "fillNodata(): An error occured during execution SAGA (Close Gaps) command to file '" + str(image_input_saga) + "'. See error message above." + endC)

    # Export de raster sous SAGA
    exportSgrd2Gtiff(image_output_saga, image_output)

    # Suppression des fichiers intermédiaires
    if not save_results_intermediate :
        deleteDir(sub_repertory_temp_saga)

    return

#########################################################################
# FONCTION computeSkyViewFactor()                                       #
#########################################################################
#   Rôle : Cette fonction calcul du ciel visible, du facteur de vue du ciel (Sky View Factor)
#   Paramètres :
#       dem_input : fichier DEM d'entrée une bande
#       image_output : fichier image de sortie contenant les valeurs de sky view factor
#       svf_radius : paramètre 'radius' du Sky View Factor sous SAGA (en mètres)
#       svf_method : paramètre 'method' du Sky View Factor sous SAGA
#       svf_dlevel : paramètre 'dlevel' du Sky View Factor sous SAGA
#       svf_ndirs :  paramètre 'ndirs' du Sky View Factor sous SAGA
#       save_results_intermediate : fichiers de sorties intermediaires nettoyees, par defaut = False

def computeSkyViewFactor(dem_input, image_output, svf_radius, svf_method, svf_dlevel, svf_ndirs, save_results_intermediate=False):

    if debug >= 2:
        print(cyan + "computeSkyViewFactor() : " + bold + "Calcul du Sky View Factor sous SAGA, à partir du fichier : " + endC + dem_input)

    # Constantes
    SUFFIX_TMP = "_tmp"
    SUFFIX_SAGA = "_saga"
    EXT_GRID_SAGA = '.sgrd'

    # Variables
    repertory_output = os.path.dirname(image_output)
    basename_dem_input = os.path.splitext(os.path.basename(dem_input))[0]
    basename_image_output = os.path.splitext(os.path.basename(image_output))[0]

    sub_repertory_temp_saga = repertory_output + os.sep + basename_image_output + SUFFIX_TMP + SUFFIX_SAGA
    dem_input_saga = sub_repertory_temp_saga + os.sep + basename_dem_input + EXT_GRID_SAGA
    image_output_saga = sub_repertory_temp_saga + os.sep + basename_image_output + EXT_GRID_SAGA

    # Nettoyage du répertoire temporaire
    cleanTempData(sub_repertory_temp_saga)

    # Import du DEM sous SAGA
    importGtiff2Sgrd(dem_input, dem_input_saga)

    # Utilisation de la fonction "Sky View Factor" de SAGA
    command = "saga_cmd ta_lighting 3 -DEM %s -SVF %s -RADIUS %s -METHOD %s -DLEVEL %s -NDIRS %s" % (dem_input_saga, image_output_saga, svf_radius, svf_method, svf_dlevel, svf_ndirs)
    exitCode = os.system(command)
    if exitCode != 0 :
        print(command)
        raise NameError(bold + red + "computeSkyViewFactor(): An error occured during execution SAGA (Sky View Factor) command to file '%s'. See error message above." + endC) % (str(dem_input_saga))

    # Export du SVF sous SAGA
    exportSgrd2Gtiff(image_output_saga, image_output)

    # Suppression des fichiers intermédiaires
    if not save_results_intermediate :
        deleteDir(sub_repertory_temp_saga)

    return

#########################################################################
# FONCTION computeCentroid()                                            #
#########################################################################
#   Rôle : Création d'un fichier shape des centroides des polygones d'un fichier shape d'entrée
#   Paramètres :
#       vector_input : fichier vecteur d'entrée
#       vector_output : fichier vecteur de sortie contenant les centroides

def computeCentroid(vector_input, vector_output):

    if debug >= 2:
        print(cyan + "computeCentroid() : " + bold + "Calcul des centroides du fichier vecteur : " + endC + vector_input)

    command = "saga_cmd shapes_polygons 'Polygon Centroids' -POLYGONS "+ vector_input + " -METHOD true -CENTROIDS " + vector_output
    exitCode = os.system(command)
    if exitCode != 0 :
        print(command)
        raise NameError(bold + red + "computeCentroid(): An error occured during execution SAGA (Polygon Centroids) command to file '%s'. See error message above." + endC) % (str(vector_input))

    return

#########################################################################
# FONCTION computeConvex()                                              #
#########################################################################
#   Rôle : Création d'un fichier shape des  polygones convexes d'un fichier shape d'entrée selon le type de traitement demandé
#   Paramètres :
#       vector_input : fichier vecteur d'entrée
#       vector_output : fichier vecteur de sortie contenant les polygones convexes
#       process : option de construction de la convexité valant 0, 1 (défaut) ou 2
#           0 = un polygone convexe à tout les polygones d'entrées
#           1 = un polygone convexe par polygones d'entrées
#           2 = un polygone convexe par partie de polygones d'entrées

def computeConvex(vector_input, vector_output, process = 1):

    if debug >= 2:
        print(cyan + "computeConvex() : " + bold + "Calcul de la convexité du fichier vecteur : " + endC + vector_input)

    if process < 0 or process > 2:
        raise ValueError(bold + red +"computeConvex(): Argument error : 'process' should be between [0,1,2]. Received '%s' instead." + endC) % (str(process))

    command = "saga_cmd shapes_points 'Convex Hull' -SHAPES %s -POLYPOINTS %s -HULLS %s" %(vector_input, str(process), vector_output)
    exitCode = os.system(command)
    if exitCode != 0 :
        print(command)
        raise NameError(bold + red + "computeConvex(): An error occured during execution SAGA (Convex Hull) command to file '%s'. See error message above." + endC) % (str(vector_input))

    return

#########################################################################
# FONCTION triangulationDelaunay()                                      #
#########################################################################
#   Rôle : Triangulation de données points par la méthode de Delaunay
#   Documentation : https://grass.osgeo.org/grass76/manuals/v.sample.html
#   Paramètres :
#       vector_input : vecteur points en entrée
#       grid_output : raster GRID triangulé en sortie
#       field_name : champ du vecteur points sur lequel faire la triangulation
#       cellsize : résolution du raster GRID en sortie (par défaut, 1)

def triangulationDelaunay(vector_input, grid_output, field_name, cellsize=1):

    if debug >= 2:
        print(cyan + "triangulationDelaunay() : " + bold + green + "Triangulation de données points par la méthode de Delaunay : " + endC + vector_input)

    command = "saga_cmd grid_gridding 5 -SHAPES %s -TARGET_OUT_GRID %s -FIELD %s -TARGET_USER_SIZE %s" % (vector_input, grid_output, field_name, cellsize)
    exitCode = os.system(command)
    if exitCode != 0 :
        print(command)
        raise NameError(bold + red + "triangulationDelaunay(): An error occured during execution SAGA (Triangulation) command to file '%s'. See error message above." + endC) % vector_input

    return

