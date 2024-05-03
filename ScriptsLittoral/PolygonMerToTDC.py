#! /usr/bin/env pyt/hon
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT D'EXTRACTION DU TRAIT DE CÔTE À PARTIR D'UN MASQUE BINAIRE TERRE/MER                                                               #
#                                                                                                                                           #
#############################################################################################################################################

"""
Nom de l'objet : PolygonMerToTDC.py
Description    :
----------------
Objectif   : Extrait le trait de côte jet de rive à partir d'un masque binaire terre/mer et de l'identification des polygones mer

Date de creation : 25/05/2016
"""

from __future__ import print_function
import os, argparse, shutil, sys
from osgeo import gdal
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC, displayIHM
from Lib_log import timeLine
from Lib_raster import polygonizeRaster, createBinaryMaskMultiBand, getNodataValueImage
from Lib_vector import bufferVector, simplifyVector, cutVectorAll, convertePolygon2Polylines, withinPolygons
from Lib_file import removeVectorFile

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 3

###########################################################################################################################################
# FONCTION PolygonMerToTDC                                                                                                                #
###########################################################################################################################################
def polygonMerToTDC(input_im_ndvi_dico, output_dir, input_sea_points, fct_bin_mask_vect, simplif, input_cut_vector, buf_pos, buf_neg, no_data_value, path_time_log, epsg=2154, format_vector="ESRI Shapefile", extension_raster=".tif", extension_vector=".shp", save_results_intermediate=True, overwrite=True):
    """
    # ROLE:
    #    Extraction du trait de côte jet de rive à partir d'un masque binaire terre/mer
    #
    # ENTREES DE LA FONCTION :
    #    input_im_ndvi_dico : Dictionnaire associant les images à traiter pour extraire le trait de côte avec le(s) masque(s) vecteur(s) binaire(s) terre/mer associé(s)
    #    output_dir : Répertoire de sortie pour les fichiers issus du traitement
    #    input_sea_points : Fichier shp de points dans la mer pour identifier les polygones mer sur le masque binaire vecteur terre/mer
    #    fct_bin_mask_vect : Option : les masques binaires sont calculés précedement (pris en compte pour les noms des fichiers de sortie)
    #    simplif : Option : Valeur de tolérance pour la simplification du trait de côte obtenu
    #    input_cut_vector : Option : le fichier vecteur pour la découpe du trait de côte en sortie
    #    buf_pos : Taille du buffer pour la dilatation, en vue de la suppression des trous (bâteaux, ...) dans le polygone mer. Par défaut 3.5
    #    buf_neg : Taille du buffer pour l'érosion, en vue de la suppression des trous (bâteaux, ...) dans le polygone mer. Par défaut -3.5
    #    no_data_value : Valeur de  pixel du no data
    #    path_time_log : le fichier de log de sortie
    #    epsg : Valeur de la projection. Par défaut 2154
    #    format_vector  : format des vecteurs de sortie, par defaut = 'ESRI Shapefile'
    #    extension_raster : extension des fichiers raster de sortie, par defaut = '.tif'
    #    extension_vector : extension du fichier vecteur de sortie, par defaut = '.shp'
    #    save_results_intermediate : fichiers de sorties intermediaires non nettoyees, par defaut = True
    #    overwrite : supprime ou non les fichiers existants ayant le meme nom
    #
    # SORTIES DE LA FONCTION :
    #    Le fichier contenant le trait de côte
    #    Eléments modifiés aucun
    #
    """

    # Mise à jour du Log
    starting_event = "PolygonMerToTDC() : Select PolygonMerToTDC starting : "
    timeLine(path_time_log,starting_event)

    # Affichage des paramètres
    if debug >= 3:
        print(bold + green + "Variables dans PolygonMerToTDC - Variables générales" + endC)
        print(cyan + "polygonMerToTDC() : " + endC + "input_im_ndvi_dico : " + str(input_im_ndvi_dico) + endC)
        print(cyan + "polygonMerToTDC() : " + endC + "output_dir : " + str(output_dir) + endC)
        print(cyan + "polygonMerToTDC() : " + endC + "input_sea_points : " + str(input_sea_points) + endC)
        print(cyan + "polygonMerToTDC() : " + endC + "fct_bin_mask_vect : " + str(fct_bin_mask_vect) + endC)
        print(cyan + "polygonMerToTDC() : " + endC + "simplif : " + str(simplif) + endC)
        print(cyan + "polygonMerToTDC() : " + endC + "input_cut_vector : " + str(input_cut_vector) + endC)
        print(cyan + "polygonMerToTDC() : " + endC + "buf_pos : " + str(buf_pos) + endC)
        print(cyan + "polygonMerToTDC() : " + endC + "buf_neg : " + str(buf_neg) + endC)
        print(cyan + "polygonMerToTDC() : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "polygonMerToTDC() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "polygonMerToTDC() : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "polygonMerToTDC() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "polygonMerToTDC() : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "polygonMerToTDC() : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "polygonMerToTDC() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "polygonMerToTDC() : " + endC + "overwrite : " + str(overwrite) + endC)

    # Constantes
    REP_TEMP_POLY_MER = "Temp_PolygonMerToTDC_"
    CODAGE_8B = "uint8"

    # Création du répertoire de sortie s'il n'existe pas déjà
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Pour toutes les images à traiter
    for r in range(len(input_im_ndvi_dico.split())):
        # L'image à traiter
        input_image = input_im_ndvi_dico.split()[r].split(":")[0]
        image_name = os.path.splitext(os.path.basename(input_image))[0]

        # Création du répertoire temporaire de calcul
        repertory_temp = output_dir + os.sep + REP_TEMP_POLY_MER + image_name
        if not os.path.exists(repertory_temp):
            os.makedirs(repertory_temp)

        if not os.path.exists(input_image):
            print(cyan + "polygonMerToTDC() : " + bold + red + "L'image en entrée : " + input_image + " n'existe pas. Vérifiez le chemin !" + endC, file=sys.stderr)
            sys.exit(1)

        src_input_im = gdal.Open(input_image)
        if src_input_im is None:
            print(cyan + "polygonMerToTDC() : " + bold + red + "Impossible d'ouvrir l'image raster : " + input_image + endC, file=sys.stderr)
            sys.exit(1)
        try :
            srcband = src_input_im.GetRasterBand(2)
        except RuntimeError as err:
            print(cyan + "polygonMerToTDC() : " + bold + red + "Pas de bande 2 trouvée sur : " + input_image + endC, file=sys.stderr)
            e = "OS error: {0}".format(err)
            print(e, file=sys.stderr)
            sys.exit(1)

        # Traiter le cas où pas de NDVI derrière
        if ":" not in input_im_ndvi_dico.split()[r]:
            print(cyan + "polygonMerToTDC() : " + red + bold + "Aucun masque binaire vectorisé spécifié ! Nécessité d'au moins un par image." + endC, file=sys.stderr)
            sys.exit(1)

        # Parcours de toutes les images NDVI correspondant à chaque image
        for ndvi_mask_vect in input_im_ndvi_dico.split()[r].split(":")[1].split(","):
            if debug > 2 :
                print(cyan + "polygonMerToTDC() : " + endC + "Traitement de : " + ndvi_mask_vect)

            # Initialisation des noms des fichiers de sortie
            binary_mask_zeros = repertory_temp + os.sep +  "b_mask_zeros_" + os.path.splitext(os.path.basename(input_image))[0] + extension_raster
            binary_mask_zeros_vector = "b_mask_zeros_vect_" + os.path.splitext(os.path.basename(input_image))[0]
            path_binary_mask_zeros_vector = repertory_temp + os.sep +  binary_mask_zeros_vector + extension_vector
            true_values_buffneg = repertory_temp + os.sep + "true_values_buffneg_" + os.path.splitext(os.path.basename(input_image))[0] + extension_vector
            decoup_buffneg = repertory_temp + os.sep + "decoupe_buffneg_" + os.path.splitext(os.path.basename(input_cut_vector))[0] + extension_vector

            if fct_bin_mask_vect :
                threshold = os.path.splitext(os.path.basename(ndvi_mask_vect))[0].split("_")[-2] + "_" + os.path.splitext(os.path.basename(ndvi_mask_vect))[0].split("_")[-1]
                poly_mer_shp = repertory_temp + os.sep + "poly_mer_" + os.path.splitext(os.path.basename(input_image))[0] + "_" + str(threshold) + extension_vector
                poly_mer_shp_dilat = repertory_temp + os.sep + "poly_mer_dilat_" + os.path.splitext(os.path.basename(input_image))[0] + "_" + str(threshold) + extension_vector
                poly_mer_shp_ferm = repertory_temp + os.sep + "poly_mer_ferm_" + os.path.splitext(os.path.basename(input_image))[0] + "_" + str(threshold) + extension_vector
                polyline_mer = repertory_temp + os.sep + "polyline_mer_" + os.path.splitext(os.path.basename(input_image))[0] + "_" + str(threshold) + extension_vector
                polyline_tdc = repertory_temp + os.sep + "tdc_" + os.path.splitext(os.path.basename(input_image))[0] + "_" + str(threshold) + extension_vector
                polyline_tdc_simplif = repertory_temp + os.sep + "tdcs_" + os.path.splitext(os.path.basename(input_image))[0] + "_" + str(threshold) + extension_vector
                polyline_tdc_simplif_decoup = output_dir + os.sep + "tdcsd_" + os.path.splitext(os.path.basename(input_image))[0] + "_" + str(threshold) + extension_vector
            else :
                poly_mer_shp = repertory_temp + os.sep + "poly_mer_" + os.path.splitext(os.path.basename(ndvi_mask_vect))[0] + extension_vector
                poly_mer_shp_dilat = repertory_temp + os.sep + "poly_mer_dilat_" + os.path.splitext(os.path.basename(input_image))[0] + extension_vector
                poly_mer_shp_ferm = repertory_temp + os.sep + "poly_mer_ferm_" + os.path.splitext(os.path.basename(input_image))[0] + extension_vector
                polyline_mer = repertory_temp + os.sep + "polyline_mer_" + os.path.splitext(os.path.basename(ndvi_mask_vect))[0] + extension_vector
                polyline_tdc = repertory_temp + os.sep + "tdc_" + os.path.splitext(os.path.basename(ndvi_mask_vect))[0] + extension_vector
                polyline_tdc_simplif = repertory_temp + os.sep + "tdcs_" + os.path.splitext(os.path.basename(ndvi_mask_vect))[0] + extension_vector
                polyline_tdc_simplif_decoup = output_dir + os.sep + "tdcsd_" + os.path.splitext(os.path.basename(ndvi_mask_vect))[0] + extension_vector

            # Création shp poly_mer_shp contenant uniquement les polygones mer
            if os.path.exists(poly_mer_shp):
                removeVectorFile(poly_mer_shp)

            # Sélection des polygones qui sont de la mer, dans la liste poly_mer
            withinPolygons(input_sea_points, ndvi_mask_vect, poly_mer_shp, overwrite, format_vector)

            # Fermeture (dilatation - érosion) sur les polygones mer obtenus pour supprimer les petits trous dans les polygones (bateaux, ...) et rassembler les polygones proches
            bufferVector(poly_mer_shp, poly_mer_shp_dilat, buf_pos, "", 1.0, 10, format_vector)
            bufferVector(poly_mer_shp_dilat, poly_mer_shp_ferm, buf_neg, "", 1.0, 10, format_vector)

            # Création masque binaire pour séparer les no data des vraies valeurs
            no_data_ima = getNodataValueImage(input_image)
            if no_data_ima == None :
                no_data_ima = no_data_value
            createBinaryMaskMultiBand(input_image, binary_mask_zeros, no_data_ima, CODAGE_8B)

            # Vectorisation du masque binaire true data/false data -> polygone avec uniquement les vraies valeurs
            if os.path.exists(path_binary_mask_zeros_vector):
                removeVectorFile(path_binary_mask_zeros_vector)
            polygonizeRaster(binary_mask_zeros, path_binary_mask_zeros_vector, binary_mask_zeros_vector)

            # Buffer négatif sur ce polygone
            bufferVector(path_binary_mask_zeros_vector, true_values_buffneg, -2, "", 1.0, 10, format_vector)

            # Transformation des polygones de la couche poly_mer_shp_ferm en polyligne
            convertePolygon2Polylines(poly_mer_shp_ferm, polyline_mer, overwrite, format_vector)

            # Découpe du TDC polyline_mer avec le polygone négatif
            cutVectorAll(true_values_buffneg, polyline_mer, polyline_tdc, overwrite, format_vector)

            # Simplification du TDC
            simplifyVector(polyline_tdc, polyline_tdc_simplif, simplif, format_vector)

            # Buffer négatif autour de input_cut_vector
            bufferVector(input_cut_vector, decoup_buffneg, -1, "", 1.0, 10, format_vector)

            # Découpe du TDC polyline_mer avec le buffer négatif du polygone mer
            cutVectorAll(decoup_buffneg, polyline_tdc_simplif, polyline_tdc_simplif_decoup, overwrite, format_vector)

            tdc_final = polyline_tdc_simplif_decoup

        # Suppression du repertoire temporaire
        if not save_results_intermediate and os.path.exists(repertory_temp):
            shutil.rmtree(repertory_temp)

    # Mise à jour du Log
    ending_event = "PolygonMerToTDC() : Select PolygonMerToTDC ending: "
    timeLine(path_time_log,ending_event)

    return tdc_final

###########################################################################################################################################
# MISE EN PLACE DU PARSER                                                                                                                 #
###########################################################################################################################################

# Code executé seulement dans le cas ou le script est lancé depuis une ligne de commande
# Il n'est pas executé lors d'un import PolygonMerToTDC.py
# Exemple de lancement en ligne de commande:
# python /home/scgsi/Documents/ChaineTraitement/ScriptsLittoral/PolygonMerToTDC.py -ind "/mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Test_TDCSeuil/image1.tif:/mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Test_TDCSeuil/Result2/temp_PolygonMerToTDC/bin_mask_vect_image1_-0.415.shp /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Test_TDCSeuil/image2.tif:/mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Test_TDCSeuil/Result2/temp_PolygonMerToTDC/bin_mask_vect_image2_-0.211.shp,/mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Test_TDCSeuil/Result2/temp_PolygonMerToTDC/bin_mask_vect_image2_-0.421.shp" -outd /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Tests/Tests_PolygonMerToTDC -mer /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Test_TDCSeuil/points_mer.shp" -d /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/08_Donnees/Histolitt/TCH_simplifie2_buffer270_adapte_mediterranee_simpl200.shp -fctbmv

def main(gui=False):

    parser = argparse.ArgumentParser(prog="PolygonMerToTDC", description=" \
    Info : Creating an shapefile (.shp) containing the coastline jet de rive from sea identification (points) and vectorized binary mask terre/mer, extracted with a threshold method.\n\
    Objectif   : Extrait le trait de côte jet de rive à partir d'un masque binaire terre/mer et de l'identification des polygones mer. \n\
    Example : python /home/scgsi/Documents/ChaineTraitement/ScriptsLittoral/PolygonMerToTDC.py \n\
                    -ind \"/mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Test_TDCSeuil/image1.tif:/mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Test_TDCSeuil/Result2/temp_PolygonMerToTDC/bin_mask_vect_image1_-0.415.shp /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Test_TDCSeuil/image2.tif:/mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Test_TDCSeuil/Result2/temp_PolygonMerToTDC/bin_mask_vect_image2_-0.211.shp,/mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Test_TDCSeuil/Result2/temp_PolygonMerToTDC/bin_mask_vect_image2_-0.421.shp\" \n\
                    -outd /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Tests/Tests_PolygonMerToTDC \n\
                    -mer /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Test_TDCSeuil/points_mer.shp \n\
                    -d /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/08_Donnees/Histolitt/TCH_simplifie2_buffer270_adapte_mediterranee_simpl200.shp \n\
                    -fctbmv")

    parser.add_argument('-ind','--input_im_ndvi_dico', default="", help="Dictionnary of input images (.tif) and binary mask vectors (terre/mer) associated.", type=str, required=True)
    parser.add_argument('-outd','--output_dir', default="",help="Output directory.", type=str, required=True)
    parser.add_argument('-mer','--input_sea_points', default="",help="Input vector file containing points in the sea (.shp).", type=str, required=True)
    parser.add_argument('-fctbmv','--fct_bin_mask_vect', action='store_true', default=False, help="True if binary mask calculated thanks to binary Mask Vect (a first process has been done with TDCSeuil for example).", required=False)
    parser.add_argument('-simp','--simplif', default=1, help="Value for simplification of the coastline", type=float, required=False)
    parser.add_argument('-d','--input_cut_vector', default="", help="Vector file containing shape of the area to keep (.shp).", type=str, required=True)
    parser.add_argument('-bp','--buf_pos', default=3.5, help="Value (meters) for the positive buffer (float).", type=float, required=False)
    parser.add_argument('-bn','--buf_neg', default=-3.5, help="Value (meters) for the negative buffer (float).", type=float, required=False)
    parser.add_argument('-epsg','--epsg',default=2154,help="Option : Projection EPSG for the layers. By default : 2154", type=int, required=False)
    parser.add_argument('-ndv','--no_data_value', default=0, help="Option : Value of the pixel no data. By default : 0", type=int, required=False)
    parser.add_argument('-vef','--format_vector',default="ESRI Shapefile",help="Option : Vector format. By default : ESRI Shapefile", type=str, required=False)
    parser.add_argument('-rae','--extension_raster', default=".tif", help="Option : Extension file for image raster. By default : '.tif'", type=str, required=False)
    parser.add_argument('-vee','--extension_vector',default=".shp",help="Option : Extension file for vector. By default : '.shp'", type=str, required=False)
    parser.add_argument('-log','--path_time_log',default="",help="Name of log", type=str, required=False)
    parser.add_argument('-sav','--save_results_inter',action='store_true',default=False,help="Option : Save or delete intermediate result after the process. By default, False", required=False)
    parser.add_argument('-now','--overwrite',action='store_false',default=True,help="Option : Overwrite files with same names. By default : True", required=False)
    parser.add_argument('-debug','--debug',default=3,help="Option : Value of level debug trace, default : 3 ",type=int, required=False)
    args = displayIHM(gui, parser)

    # Récupération du dictionnaire images/seuils à traiter
    if args.input_im_ndvi_dico != None :
        input_im_ndvi_dico = args.input_im_ndvi_dico

    # Récupération du dossier des traitements en sortie
    if args.output_dir != None :
        output_dir = args.output_dir

    # Récupération de la couche points mer
    if args.input_sea_points != None :
        input_sea_points = args.input_sea_points

    # Récupération de la valeur de fct_bin_mask_vect
    if args.fct_bin_mask_vect != None :
        fct_bin_mask_vect = args.fct_bin_mask_vect

    # Récupération de la valeur de tolérence pour la simplifiaction du trait de côte obtenu
    if args.simplif != None :
        simplif = args.simplif

    # Récupération du shapefile de découpe
    if args.input_cut_vector != None :
        input_cut_vector = args.input_cut_vector

    # Récupération de la valeur (m) pour le buffer positif
    if args.buf_pos != None :
        buf_pos = args.buf_pos

    # Récupération de la valeur (m) pour le buffer négatif
    if args.buf_neg != None :
        buf_neg = args.buf_neg

    # Récupération du nom du format des fichiers vecteur
    if args.format_vector != None:
        format_vector = args.format_vector

    # Paramètre de l'extension des images rasters
    if args.extension_raster != None:
        extension_raster = args.extension_raster

    # Récupération de l'extension des fichiers vecteurs
    if args.extension_vector != None:
        extension_vector = args.extension_vector

    # Récupération de la projection
    if args.epsg != None:
        epsg = args.epsg

    # Récupération du parametre no_data_value
    if args.no_data_value!= None:
        no_data_value = args.no_data_value

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
        print(cyan + "polygonMerToTDC : " + endC + "input_im_ndvi_dico : " + str(input_im_ndvi_dico) + endC)
        print(cyan + "polygonMerToTDC : " + endC + "output_dir : " + str(output_dir) + endC)
        print(cyan + "polygonMerToTDC : " + endC + "input_sea_points : " + str(input_sea_points) + endC)
        print(cyan + "polygonMerToTDC : " + endC + "fct_bin_mask_vect : " + str(fct_bin_mask_vect) + endC)
        print(cyan + "polygonMerToTDC : " + endC + "simplif : " + str(simplif) + endC)
        print(cyan + "polygonMerToTDC : " + endC + "input_cut_vector : " + str(input_cut_vector) + endC)
        print(cyan + "polygonMerToTDC : " + endC + "buf_pos : " + str(buf_pos) + endC)
        print(cyan + "polygonMerToTDC : " + endC + "buf_neg : " + str(buf_neg) + endC)
        print(cyan + "polygonMerToTDC : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "polygonMerToTDC : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "polygonMerToTDC : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "polygonMerToTDC : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "polygonMerToTDC : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "polygonMerToTDC : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "polygonMerToTDC : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "polygonMerToTDC : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "polygonMerToTDC : " + endC + "debug : " + str(debug) + endC)

    # Fonction générale
    polygonMerToTDC(input_im_ndvi_dico, output_dir, input_sea_points, fct_bin_mask_vect, simplif, input_cut_vector, buf_pos, buf_neg, no_data_value, path_time_log, epsg, format_vector, extension_raster, extension_vector, save_results_intermediate, overwrite)

# ================================================

if __name__ == '__main__':
  main(gui=False)

