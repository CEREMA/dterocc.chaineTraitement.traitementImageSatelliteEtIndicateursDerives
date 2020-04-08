#!/usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerSO/DALETT/SCGSI  All rights reserved.                                                                            #
#############################################################################################################################################

from __future__ import print_function
import os,shutil,time
from Lib_log import timeLine
from Lib_raster import getPixelWidthXYImage
from CrossingVectorRaster import statisticsVectorRaster
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 3

    #####################################################################################
    ### Préparation au calcul de l'indicateur de pourcentage de surfaces imperméables ###
    #####################################################################################

def indicateurSI(urbanatlas_input, ucz_output, emprise_file, mask_file, enter_with_mask, image_file, mnh_file, built_files_list, hydrography_file, roads_files_list, rpg_file, indicators_method, ucz_method, dbms_choice, threshold_ndvi, threshold_ndvi_water, threshold_ndwi2, threshold_bi_bottom, threshold_bi_top, path_time_log, temp_directory, extension_raster, extension_vector):

    print(bold + yellow + "Début de la préparation au calcul de l'indicateur de pourcentage de surfaces imperméables." + endC)
    step = "    Début de la préparation au calcul de l'indicateur de pourcentage de surfaces imperméables : "
    timeLine(path_time_log,step)

    grid_ready_cleaned = temp_directory + os.sep + os.path.splitext(os.path.basename(urbanatlas_input))[0] + "_cut_cleaned" + extension_vector
    permeability = temp_directory + os.sep + "permeability" + extension_raster
    logCVR = temp_directory + os.sep + "logCVR.txt"

    if indicators_method == "BD_exogenes": # Élaboration de la carte d'imperméabilité pour la 1ère méthode de calcul des indicateurs

        neochannels = temp_directory + os.sep + os.path.splitext(os.path.basename(image_file))[0] + "_NDVI" + extension_raster
        hydro_shape = temp_directory + os.sep + "eau" + extension_vector
        RPG_shape = temp_directory + os.sep + "RPG" + extension_vector
        hydro_mask = temp_directory + os.sep + "hydro_mask" + extension_raster
        RPG_mask = temp_directory + os.sep + "RPG_mask" + extension_raster
        vegetation_mask = mask_file

        if not enter_with_mask:
            vegetation_mask = temp_directory + os.sep + "vegetation_mask" + extension_raster
            print(bold + cyan + "    Création du masque de végétation :" + endC)
            os.system("otbcli_BandMath -il %s -out %s uint8 -exp 'im1b1>=%s ? 10 : 1'" % (neochannels, vegetation_mask, threshold_ndvi)) # Création du masque de végétation
        print(bold + cyan + "    Création du masque RPG :" + endC)
        os.system("otbcli_Rasterization -in %s -out %s uint8 -im %s -background 1 -mode binary -mode.binary.foreground 10" % (RPG_shape, RPG_mask, vegetation_mask)) # Création du masque RPG (~ sol nu)
        print(bold + cyan + "    Création du masque d'eau :" + endC)
        os.system("otbcli_Rasterization -in %s -out %s uint8 -im %s -background 1 -mode binary -mode.binary.foreground 10" % (hydro_shape, hydro_mask, vegetation_mask)) # Création du masque d'eau
        print(bold + cyan + "    Création de la carte d'imperméabilité :" + endC)
        os.system("otbcli_BandMath -il %s %s %s -out %s uint8 -exp 'im1b1+im2b1+im3b1>=10 ? 10 : 1'" % (vegetation_mask, RPG_mask, hydro_mask, permeability)) # Création de la carte d'imperméabilité

    elif indicators_method == "SI_seuillage": # Élaboration de la carte d'imperméabilité pour la 2ème méthode de calcul des indicateurs

        neochannels = temp_directory + os.sep + os.path.splitext(os.path.basename(image_file))[0] + "_NDVI_NDWI2_BI" + extension_raster
        built_shape = temp_directory + os.sep + "bati" + extension_vector
        roads_shape = temp_directory + os.sep + "route" + extension_vector
        built_mask = temp_directory + os.sep + "built_mask" + extension_raster
        roads_mask = temp_directory + os.sep + "roads_mask" + extension_raster

        print(bold + cyan + "    Création du masque bâti pour nettoyage :" + endC)
        os.system("otbcli_Rasterization -in %s -out %s uint8 -im %s -background 1 -mode binary -mode.binary.foreground 10" % (built_shape, built_mask, neochannels)) # Création du masque bâti pour nettoyage
        print(bold + cyan + "    Création du masque route pour nettoyage :" + endC)
        os.system("otbcli_Rasterization -in %s -out %s uint8 -im %s -background 1 -mode binary -mode.binary.foreground 10" % (roads_shape, roads_mask, neochannels)) # Création du masque route pour nettoyage
        print(bold + cyan + "    Création de la carte d'imperméabilité :" + endC)
        expression = "((im1b1>=%s) or (im1b1<%s and im1b2>=%s) or (im1b1>=%s and im1b1<%s and im1b3>=%s and im1b3<%s)) and (im2b1==1 and im3b1==1) ? 10 : 1" % (threshold_ndvi,threshold_ndvi_water,threshold_ndwi2,threshold_ndvi_water,threshold_ndvi,threshold_bi_bottom,threshold_bi_top)
        os.system("otbcli_BandMath -il %s %s %s -out %s uint8 -exp '%s'" % (neochannels, built_mask, roads_mask, permeability, expression)) # Création de la carte d'imperméabilité

    else: # Élaboration de la carte d'imperméabilité pour les méthodes 3 et 4 de calcul des indicateurs (utilisant la classif)

        image_cut = temp_directory + os.sep + os.path.splitext(os.path.basename(image_file))[0] + "_cut" + extension_raster

        print(bold + cyan + "    Création de la carte d'imperméabilité :" + endC)
        os.system("otbcli_BandMath -il %s -out %s uint8 -exp 'im1b1>=12000 ? 10 : 1'" % (image_cut, permeability)) # Création de la carte d'imperméabilité

    print(bold + cyan + "    Récupération du pourcentage de surfaces imperméables par polygone du maillage :" + endC)
    statisticsVectorRaster(permeability, grid_ready_cleaned, "", 1, True, True, False, [], [], {1:'Imperm', 10:'Perm'}, path_time_log, True, 'ESRI Shapefile', False, True) # Récupération du pourcentage de surfaces imperméables par polygone du maillage
    time.sleep(10) # Pause de 10 secondes pour que le système récupère toute la RAM qui a pu être utilisée pour le CVR

    step = "    Fin de la préparation au calcul de l'indicateur de pourcentage de surfaces imperméables : "
    timeLine(path_time_log,step)
    print(bold + yellow + "Fin de la préparation au calcul de l'indicateur de pourcentage de surfaces imperméables." + endC)
    print("\n")

    return

    #################################################################
    ### Préparation au calcul de l'indicateur de rapport d'aspect ###
    #################################################################

def indicateurRA(urbanatlas_input, ucz_output, emprise_file, mask_file, enter_with_mask, image_file, mnh_file, built_files_list, hydrography_file, roads_files_list, rpg_file, indicators_method, ucz_method, dbms_choice, threshold_ndvi, threshold_ndvi_water, threshold_ndwi2, threshold_bi_bottom, threshold_bi_top, path_time_log, temp_directory, extension_raster, extension_vector):

    print(bold + yellow + "Début de la préparation au calcul de l'indicateur de rapport d'aspect." + endC)
    step = "    Début de la préparation au calcul de l'indicateur de rapport d'aspect : "
    timeLine(path_time_log,step)

    grid_ready_cleaned = temp_directory + os.sep + os.path.splitext(os.path.basename(urbanatlas_input))[0] + "_cut_cleaned" + extension_vector
    permeability = temp_directory + os.sep + "permeability" + extension_raster
    built_shape = temp_directory + os.sep + "bati" + extension_vector
    built_RA = temp_directory + os.sep + "built_RA" + extension_raster
    logCVR = temp_directory + os.sep + "logCVR.txt"

    if indicators_method == "Resultats_classif": # Croisement du bâti vectorisé avec le MNH pour récupérer la hauteur moyenne de chaque bâtiment

        MNH_cut = temp_directory + os.sep + os.path.splitext(os.path.basename(mnh_file))[0] + "_cut" + extension_raster
        MNH_centimeters = temp_directory + os.sep + "MNH_centimeters" + extension_raster

        print(bold + cyan + "    Basculement des valeurs du MNH des mètres aux centimètres :" + endC)
        os.system("otbcli_BandMath -il %s -out %s uint16 -exp 'im1b1*100'" % (MNH_cut, MNH_centimeters)) # Basculement des valeurs du MNH des mètres aux centimètres (pour obtenir un raster codé en entier et non en flottant)
        print(bold + cyan + "    Récupération de l'information de hauteur du bâti à partir du MNH :" + endC)
        statisticsVectorRaster(MNH_centimeters, built_shape, "", 1, False, False, True, [], [], {}, logCVR, True, 'ESRI Shapefile', False, True) # Récupération de l'information de hauteur du bâti à partir du MNH
        time.sleep(10) # Pause de 10 secondes pour que le système récupère toute la RAM qui a pu être utilisée pour le CVR

    print(bold + cyan + "    Rastérisation du bâti :" + endC)
    pixel_size_x, pixel_size_y = getPixelWidthXYImage(permeability)
    os.system("gdal_rasterize -burn 10 -init 1 -tr %s %s %s %s" % (pixel_size_x, pixel_size_y, built_shape, built_RA)) # Rastérisation du bâti via GDAL plutôt qu'OTB : mauvaise gestion des valeurs de background pour l'OTB (devient NoData)
    print(bold + cyan + "    Récupération de la surface non-bâtie par polygone du maillage :" + endC)
    statisticsVectorRaster(built_RA, grid_ready_cleaned, "", 1, True, True, False, [], [], {1:'NonBati', 10:'Bati'}, path_time_log, True, 'ESRI Shapefile', False, True) # Récupération de la surface non-bâtie par polygone du maillage
    time.sleep(10) # Pause de 10 secondes pour que le système récupère toute la RAM qui a pu être utilisée pour le CVR

    step = "    Fin de la préparation au calcul de l'indicateur de rapport d'aspect : "
    timeLine(path_time_log,step)
    print(bold + yellow + "Fin de la préparation au calcul de l'indicateur de rapport d'aspect." + endC)
    print("\n")

    return

    ###################################################################
    ### Préparation au calcul de l'indicateur de classe de rugosité ###
    ###################################################################

def indicateurRug(urbanatlas_input, ucz_output, emprise_file, mask_file, enter_with_mask, image_file, mnh_file, built_files_list, hydrography_file, roads_files_list, rpg_file, indicators_method, ucz_method, dbms_choice, threshold_ndvi, threshold_ndvi_water, threshold_ndwi2, threshold_bi_bottom, threshold_bi_top, path_time_log, temp_directory, extension_raster, extension_vector):

    print(bold + yellow + "Début de la préparation au calcul de l'indicateur de classe de rugosité." + endC)
    step = "    Début de la préparation au calcul de l'indicateur de classe de rugosité : "
    timeLine(path_time_log,step)

    grid_ready_cleaned = temp_directory + os.sep + os.path.splitext(os.path.basename(urbanatlas_input))[0] + "_cut_cleaned" + extension_vector
    long_rugosite = temp_directory + os.sep + "z0" + extension_raster
    logCVR = temp_directory + os.sep + "logCVR.txt"

    if indicators_method == "Resultats_classif": # Élaboration du raster longueur de rugosité pour la 4ème méthode de calcul des indicateurs

        image_cut = temp_directory + os.sep + os.path.splitext(os.path.basename(image_file))[0] + "_cut" + extension_raster
        MNH_cut = temp_directory + os.sep + os.path.splitext(os.path.basename(mnh_file))[0] + "_cut" + extension_raster

        print(bold + cyan + "    Calcul de la longueur de rugosité :" + endC)
        os.system("otbcli_BandMath -il %s %s -out %s -exp 'im1b1==11100 ? (im2b1*0.7)*100 : 0.001'" % (image_cut, MNH_cut, long_rugosite)) # Calcul de la longueur de rugosité

    else: # Élaboration du raster longueur de rugosité pour les 3 premières méthodes de calcul des indicateurs

        permeability = temp_directory + os.sep + "permeability" + extension_raster
        built_shape = temp_directory + os.sep + "bati" + extension_vector
        built_height = temp_directory + os.sep + "built_height" + extension_raster

        print(bold + cyan + "    Rastérisation du bâti issu de la BD TOPO (avec information de hauteur) :" + endC)
        os.system("otbcli_Rasterization -in %s -out %s -im %s -background 0.001 -mode attribute -mode.attribute.field HAUTEUR" % (built_shape, built_height, permeability)) # Rastérisation du bâti issu de la BD TOPO (avec information de hauteur)
        print(bold + cyan + "    Calcul de la longueur de rugosité :" + endC)
        os.system("otbcli_BandMath -il %s -out %s -exp '(im1b1*0.7)*100'" % (built_height, long_rugosite)) # Calcul de la longueur de rugosité

    print(bold + cyan + "    Récupération de la longueur de rugosité moyenne par polygone du maillage :" + endC)
    statisticsVectorRaster(long_rugosite, grid_ready_cleaned, "", 1, False, False, True, [], [], {}, logCVR, True, True) # Récupération de la longueur de rugosité moyenne (~ hauteur de bâti moyenne) par polygone du maillage
    time.sleep(10) # Pause de 10 secondes pour que le système récupère toute la RAM qui a pu être utilisée pour le CVR

    step = "    Fin de la préparation au calcul de l'indicateur de classe de rugosité : "
    timeLine(path_time_log,step)
    print(bold + yellow + "Fin de la préparation au calcul de l'indicateur de classe de rugosité." + endC)
    print("\n")

    return

