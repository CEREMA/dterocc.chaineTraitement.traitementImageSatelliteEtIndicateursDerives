#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT QUI APPLIQUE UNE SEGMENTATION A UNE IMAGE                                                                                          #
#                                                                                                                                           #
#############################################################################################################################################
"""
Nom de l'objet : Segmentation.py
Description :
-------------
Objectif : appliquer un filtre majoritaire a une image (classee ou non)
Rq : utilisation des OTB Applications : otbcli_ClassificationMapRegularization, otbcli_GenericRegionMerging

Date de creation : 11/02/2020
----------
Modifications :
Ajout de la fonction otbcli_Segmentation avec la methode MeanShift (MathildeS, mai 2023)
------------------------------------------------------
A Reflechir/A faire :

"""

from __future__ import print_function
import os,sys,glob,string,argparse
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_log import timeLine
from Lib_file import removeFile, removeVectorFile

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 3

###########################################################################################################################################
# STRUCTURE StructSMSarameter                                                                                                             #
#####################P######################################################################################################################
class StructSMS2Parameter:
    """
    # Structure contenant les parametres utiles a la segmentation methode Segmentation Meanshift
    """
    def __init__(self):
        self.spatial_radius = 5
        self.range_radius = 15
        self.number_iteration = 100
        self.min_region_size = 100
        self.minsize = 1
        self.tilesize = 1024
        #il y a d'autres parametres non utiles pour l'instant que l'on pourra ajouter

###########################################################################################################################################
# STRUCTURE StructSMSarameter                                                                                                             #
###########################################################################################################################################
class StructSMSParameter:
    """
    # Structure contenant les parametres utiles a la segmentation methode MeanShift
    """
    def __init__(self):
        self.spatial_radius = 0
        self.range_radius = 0.0
        self.min_segement_size = 0
        self.tile_size = 0
###########################################################################################################################################
# STRUCTURE StructRFParameter                                                                                                             #
###########################################################################################################################################
class StructSRMParameter:
    """
    # Structure contenant les parametres utiles a la segmentation methode fusion des régions
    """
    def __init__(self):
        self.homogeneity_criterion = ''
        self.threshol_criterion = 0.0
        self.number_iteration = 0
        self.segmentation_speed = 0
        self.weight_spectral_homogeneity = 0.0
        self.weight_spatial_homogeneity = 0.0

###########################################################################################################################################
# FONCTION segmentImage()                                                                                                                 #
###########################################################################################################################################
def segmentImage(image_input, mask_input, segmented_raster_output, segmented_vector_output, segmentation_mode, sms_parametres_struct, sms2_parametres_struct, srm_parametres_struct, path_time_log, ram_otb=0, format_vector='ESRI Shapefile', format_raster='GTiff', extension_vector=".shp",extension_raster=".tif", save_results_intermediate=False, overwrite=True):
    """
    # ROLE:
    #    appliquer une segmentation à une image
    #
    # ENTREES DE LA FONCTION :
    #    image_input : nom image à segmenter
    #    mask_input : nom image masque
    #    segmented_vector_output : nom du vecteur segmenté de sortie
    #    segmented_raster_output : nom du raster segmenté de sortie
    #    segmentation_mode : mode de segmentation utiliser
    #    sms_parametres_struct : les paramètres du seuillage par MeanShift
    #    sms2_parametres_struct : les paramètres du seuillage par Meanshift (version 2)
    #    srm_parametres_struct : les paramètres du seuillage par Region Mergées
    #    ram_otb : memoire RAM disponible pour les applications OTB
    #    format_vector : format du fichier vecteur. Optionnel, par default : 'ESRI Shapefile'
    #    format_raster : format du fichier raster, par default : 'GTiff'.
    #    extension_vector : extension du fichier vecteur de sortie, par defaut = '.shp'
    #    extension_raster : extension du fichier raster de sortie, par defaut = '.tif'
    #    save_results_intermediate : fichiers de sorties intermediaires non nettoyées, par defaut = False
    #    overwrite : supprime ou non les fichiers existants ayant le meme nom, par defaut a True
    #
    # SORTIES DE LA FONCTION :
    #    aucun
    #   Eléments générés par le script : image segmentée
    #
    """

    # Mise à jour du Log
    starting_event = "segmentImage() : Segment image starting : "
    timeLine(path_time_log,starting_event)

    print(endC)
    print(bold + green + "## START : SEGMENTATION" + endC)
    print(endC)

    CODAGE = "uint16"

    if debug >= 2:
        print(bold + green + "segmentImage() : Variables dans la fonction" + endC)
        print(cyan + "segmentImage() : " + endC + "image_input : " + str(image_input) + endC)
        print(cyan + "segmentImage() : " + endC + "mask_input : " + str(mask_input) + endC)
        print(cyan + "segmentImage() : " + endC + "segmented_vector_output : " + str(segmented_vector_output) + endC)
        print(cyan + "segmentImage() : " + endC + "segmented_raster_output : " + str(segmented_raster_output) + endC)
        print(cyan + "segmentImage() : " + endC + "segmentation_mode : " + str(segmentation_mode) + endC)
        print(cyan + "segmentImage() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "segmentImage() : " + endC + "ram_otb : " + str(ram_otb) + endC)
        print(cyan + "segmentImage() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "segmentImage() : " + endC + "format_raster : " + str(format_raster) + endC)
        print(cyan + "segmentImage() : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "segmentImage() : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "segmentImage() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "segmentImage() : " + endC + "overwrite : " + str(overwrite) + endC)

    output_raster = False
    output_vector = False
    # Verification de l'implementation de valeurs pour les deux formats de sortie possibles
    # Seule la sortie raster est demandée
    if segmented_raster_output != '' and segmented_vector_output == '':
        check = os.path.isfile(segmented_raster_output)
        output_raster = True
        output_vector = False
        if check and not overwrite :
            print(cyan + "segmentImage() : " + bold + green +  "Image already segmented" + "." + endC)
        else :
            # Tentative de suppresion du fichier
            try:
                removeFile(segmented_raster_output)
            except Exception:
                # Ignore l'exception levée si le fichier n'existe pas (et ne peut donc pas être supprimé)
                pass

            if debug >= 3:
                print(cyan + "segmentImage() : " + bold + green +  "Applying segmented image", "..." , '\n' + endC)

    # Seule la sortie vecteur est demandée
    if segmented_vector_output != '' and segmented_raster_output == '':
        output_vector = True
        output_raster = False
        check = os.path.isfile(segmented_vector_output)
        if check and not overwrite :
            print(cyan + "segmentImage() : " + bold + green +  "Image already segmented" + "." + endC)
        else :
            # Tentative de suppresion du fichier
            try:
                removeVectorFile(segmented_vector_output, format_vector=format_vector)
            except Exception:
                # Ignore l'exception levée si le fichier n'existe pas (et ne peut donc pas être supprimé)
                pass

            if debug >= 3:
                print(cyan + "segmentImage() : " + bold + green +  "Applying segmented image", "..." , '\n' + endC)

    # Les deux sorties sont demandées
    if segmented_vector_output != '' and segmented_raster_output != '':
        check = os.path.isfile(segmented_vector_output)
        check2 = os.path.isfile(segmented_raster_output)
        output_raster = True
        output_vector = True

        if check and not overwrite :
            print(cyan + "segmentImage() : " + bold + green +  "Image already segmented in vector version" + "." + endC)
        else :
            # Tentative de suppresion du fichier
            try:
                removeVectorFile(segmented_vector_output, format_vector=format_vector)
            except Exception:
                # Ignore l'exception levée si le fichier n'existe pas (et ne peut donc pas être supprimé)
                pass

            if debug >= 3:
                print(cyan + "segmentImage() : " + bold + green +  "Applying segmented image", "..." , '\n' + endC)
                #sortie_double.append(31) #une sortie raster et vecteur est demandée, le fichier vecteur seulement est vérifié
        if check2 and not overwrite :
            print(cyan + "segmentImage() : " + bold + green +  "Image already segmented in raster version" + "." + endC)
        else :
            # Tentative de suppresion du fichier
            try:
                removeFile(segmented_raster_output)
            except Exception:
                # Ignore l'exception levée si le fichier n'existe pas (et ne peut donc pas être supprimé)
                pass

            if debug >= 3:
                print(cyan + "segmentImage() : " + bold + green +  "Applying segmented image", "..." , '\n' + endC)
                #sortie_double.append(32) #une sortie raster est demandée, le fichier vecteur

    # Segmentation :
    # Par otbcli_LargeScaleMeanShift
    if segmentation_mode.lower() == "sms" :

        if not output_vector :
            raise NameError(cyan + "segmentImage() : " + bold + red + "An error occured during otbcli_LargeScaleMeanShift command : you can't have a vector exit.")

        if output_vector :
            command = "otbcli_LargeScaleMeanShift -in %s  -spatialr %d -ranger %f -minsize %d -tilesizex %d -tilesizey %d -mode.vector.out %s" %(image_input, sms_parametres_struct.spatial_radius, sms_parametres_struct.range_radius, sms_parametres_struct.min_segement_size, sms_parametres_struct.tile_size, sms_parametres_struct.tile_size, segmented_vector_output)

        if ram_otb > 0:
            command += " -ram %d" %(ram_otb)

        if debug >=2:
            print(cyan + "segmentImage() : " + bold + green + "Debut de la segmentation de l'image" + endC)
            print(command)

        exitCode = os.system(command)
        if exitCode != 0:
            print(command)
            raise NameError(cyan + "segmentImage() : " + bold + red + "An error occured during otbcli_LSMSSegmentation command. See error message above.")
        print('\n' + cyan + "segmentImage() : " + bold + green + "Segmentation applied!" + endC)

    # Par otbcli_Segmentation
    if segmentation_mode.lower() == "sms2":
        if output_raster :
            command = "otbcli_Segmentation -in %s -mode raster -mode.raster.out %s -filter meanshift "  %(image_input, segmented_raster_output)
            if debug >=2:
                print(cyan + "segmentImage() : " + bold + green + "Debut de la segmentation de l'image" + endC)
                print(command)
            exitCode = os.system(command)
            if exitCode != 0:
                print(command)
                raise NameError(cyan + "segmentImage() : " + bold + red + "An error occured during otbcli_Segmentation  command. See error message above.")

        if output_vector :
            if mask_input != '':
                command = "otbcli_Segmentation -in %s -mode vector -mode.vector.out %s -mode.vector.inmask %s -filter meanshift -filter.meanshift.minsize %s" %(image_input, segmented_vector_output, mask_input, sms2_parametres_struct.min_region_size)
            else :
                command = "otbcli_Segmentation -in %s -mode vector -mode.vector.out %s -filter meanshift -filter.meanshift.minsize %s" %(image_input, segmented_vector_output, sms2_parametres_struct.min_region_size)
            if debug >=2:
                print(cyan + "segmentImage() : " + bold + green + "Debut de la segmentation de l'image" + endC)
                print(command)
            exitCode = os.system(command)
            if exitCode != 0:
                print(command)
                raise NameError(cyan + "segmentImage() : " + bold + red + "An error occured during otbcli_Segmentation Meanshift command. See error message above.")
        print('\n' + cyan + "segmentImage() : " + bold + green + "Segmentation applied!" + endC)

    # Par otbcli_GenericRegionMerging
    if segmentation_mode.lower() == "srm" :

        if not output_vector :
            raise NameError(cyan + "segmentImage() : " + bold + red + "An error occured during otbcli_GenericRegionMerging command : you can't have a vector exit.")

        if output_vector:
            repertory_output = os.path.dirname(segmented_vector_output)
            layer_name = os.path.splitext(os.path.basename(segmented_vector_output))[0]
            segmented_raster_tmp = repertory_output + os.sep + os.path.splitext(os.path.basename(segmented_vector_output))[0] + os.path.splitext(os.path.basename(image_input))[1]

            command = "otbcli_GenericRegionMerging -in %s -criterion %s -threshold %f -niter %d -speed %d  -cw %f -sw %f -out %s %s" %(image_input, srm_parametres_struct.homogeneity_criterion, srm_parametres_struct.threshol_criterion, srm_parametres_struct.number_iteration, srm_parametres_struct.segmentation_speed, srm_parametres_struct.weight_spectral_homogeneity, srm_parametres_struct.weight_spatial_homogeneity, segmented_raster_tmp, CODAGE)

        if ram_otb > 0:
            command += " -ram %d" %(ram_otb)

        if debug >=2:
            print(cyan + "segmentImage() : " + bold + green + "Debut de la segmentation de l'image" + endC)
            print(command)

        exitCode = os.system(command)
        if exitCode != 0:
            print(command)
            raise NameError(cyan + "segmentImage() : " + bold + red + "An error occured during otbcli_LSMSSegmentation command. See error message above.")
        print('\n' + cyan + "segmentImage() : " + bold + green + "Segmentation applied!" + endC)

        # Vectorisation du resultat de segmentation par gdal
        command = "gdal_polygonize.py %s -f \"%s\" %s %s ID" %(segmented_raster_tmp, format_vector, segmented_vector_output, layer_name)

        if debug >=2:
            print(command)

        exitCode = os.system(command)
        if exitCode != 0:
            print(command)
            raise NameError(cyan + "segmentImage() : " + bold + red + "An error occured during gdal_polygonize command. See error message above.")

        print('\n' + cyan + "segmentImage() : " + bold + green + "Filter applied!" + endC)

        # Suppression des données intermédiaires
        if not save_results_intermediate:
            # Supression du fichier temporaire de segmentation
            if os.path.isfile(segmented_raster_tmp) :
                removeFile(segmented_raster_tmp)

    print(endC)
    print(bold + green + "## END :  SEGMENTATION" + endC)
    print(endC)

    # Mise à jour du Log
    ending_event = "segmentImage() : Segment image ending : "
    timeLine(path_time_log,ending_event)

    return


###########################################################################################################################################
# MISE EN PLACE DU PARSER                                                                                                                 #
###########################################################################################################################################

# Code executé seulement dans le cas ou le script est lancé depuis une ligne de commande
# Il n'est pas executé lors d'un import Segmentation.py
# Exemple de lancement en ligne de commande:
# python Segmentation.py -i ../ImagesTestChaine/APTV_05/Micro/APTV_05_stack_raw_merged.tif -o ../ImagesTestChaine/APTV_05/Micro/APTV_05_stack_raw_merged_filtered.tif -m otb -r 2 -log ../ImagesTestChaine/APTV_05/fichierTestLog.txt

def main(gui=False):

    # Définition des arguments possibles pour l'appel en ligne de commande
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, prog="Segmentation", description="\
    Info : Applying a majority filter on one or several images. \n\
    Objectif : Appliquer un filtre majoritaire a une image (classee ou non). \n\
    Example : python Segmentation.py -i ../ImagesTestChaine/APTV_05/Micro/APTV_05_image.tif \n\
                                       -o ../ImagesTestChaine/APTV_05/Micro/APTV_05_vector_segmented.shp \n\
                                       -sr 2 \n\
                                       -log ../ImagesTestChaine/APTV_05/fichierTestLog.txt")

    # Paramètres
    parser.add_argument('-i','--image_input',default="",help="Image input to treat", type=str, required=True)
    parser.add_argument('-m','--mask_input',default="",help="Image input to mask", type=str, required=False)
    parser.add_argument('-ov','--vector_output',default="",help="Vector output result input image segmented", type=str, required=False)
    parser.add_argument('-o','--raster_output',default="",help="Raster output result input image segmented", type=str, required=False)
    parser.add_argument('-sm','--segmentation_mode',default="sms2",help="Choice type of algo classification (Choice of : 'sms2' : MeanShift, 'sms' : Large Scale MeanShift or 'srm' : Region Merging). By default, 'sms2'", type=str, required=False)
    parser.add_argument('-sms.sr','--spatialr',default=5,help="Radius of the spatial neighborhood for averaging. ",type=int, required=False)
    parser.add_argument('-sms.rs','--ranger',default=10.0,help="Threshold on spectral signature euclidean distance to consider neighborhood pixel for averaging", type=float, required=False)
    parser.add_argument('-sms.ms','--minsize',default=50,help="Minimum Segment Size (during vectorization)",type=int, required=False)
    parser.add_argument('-sms.ts','--tilesize',default=2000,help="Option : Size of the working windows in x and y. By default : 2000.", type=int, required=False)
    parser.add_argument('-sms2.sr','--spatialr2',default=5,help="Radius of the spatial neighborhood for averaging. ",type=int, required=False)
    parser.add_argument('-sms2.rs','--ranger2',default=15.0,help="Threshold on spectral signature euclidean distance to consider neighborhood pixel for averaging", type=float, required=False)
    parser.add_argument('-sms2.ni','--number_iteration2',default=100,help="Number of iterations", type=int, required=False)
    parser.add_argument('-sms2.mrs','--minregsize2',default=50,help="Minimum size of a segment during Meanhsift segmentation (not vectorization)",type=int, required=False)
    parser.add_argument('-sms2.ms','--minsize2',default=1,help="Minimum Segment Size (during vectorization)",type=int, required=False)
    parser.add_argument('-sms2.ts','--tilesize2',default=1024,help="Option : Size of the working windows in x and y. By default : 2000.", type=int, required=False)
    parser.add_argument('-srm.hc.','--homogeneity_criterion',default="bs",help="Choice type of homogeneity criterion (Choice of : 'bs' : Baatz & Schape or 'ed' : Euclidean Distance or 'fls' : Full Lambda Schedule). By default, 'bs'", type=str, required=False)
    parser.add_argument('-srm.th','--threshol',default=60.0,help="Threshold for the criterion",type=float, required=False)
    parser.add_argument('-srm.ni','--number_iteration',default=0,help="Number of iterations", type=int, required=False)
    parser.add_argument('-srm.sp','--speed',default=0,help="Activate it to boost the segmentation speed",type=int, required=False)
    parser.add_argument('-srm.wsr','--weight_spectral',default=0.7,help=", typWeight for the spectral homogeneity", type=float, required=False)
    parser.add_argument('-srm.wsi','--weight_spatial',default=0.3,help="Weight for the spatial homogeneity", type=float, required=False)
    parser.add_argument('-ram','--ram_otb',default=0,help="Ram available for processing otb applications (in MB)", type=int, required=False)
    parser.add_argument('-vef','--format_vector', default="ESRI Shapefile",help="Format of the output file.", type=str, required=False)
    parser.add_argument('-ref','--format_raster', default="GTiff",help="Format of the output file.", type=str, required=False)
    parser.add_argument('-vee','--extension_vector',default=".shp",help="Option : Extension file for vector. By default : '.shp'", type=str, required=False)
    parser.add_argument('-ree','--extension_raster',default=".tif",help="Option : Extension file for Raster. By default : '.tif'", type=str, required=False)
    parser.add_argument('-log','--path_time_log',default="",help="Name of log", type=str, required=False)
    parser.add_argument('-sav','--save_results_inter',action='store_true',default=False,help="Save or delete original image after the majority filter. By default, False", required=False)
    parser.add_argument('-now','--overwrite',action='store_false',default=True,help="Overwrite files with same names. By default, True", required=False)
    parser.add_argument('-debug','--debug',default=3,help="Option : Value of level debug trace, default : 3 ",type=int, required=False)
    args = displayIHM(gui, parser)

    # RECUPERATION DES ARGUMENTS

    # Récupération de l'image d'entrée
    if args.image_input != None:
        image_input = args.image_input
        if not os.path.isfile(image_input):
            raise NameError (cyan + "Segmentation : " + bold + red  + "File %s not existe!" %(image_input) + endC)

    # Récupération de l'image masque
    if args.mask_input != None:
        mask_input = args.mask_input


    # Récupération de l'image de sortie
    if args.raster_output != None:
        raster_output = args.raster_output

    # Récupération de l'image de sortie
    if args.vector_output != None:
        vector_output = args.vector_output

    # Récupération choix de l'algo de segmentation
    if args.segmentation_mode != None:
        segmentation_mode = args.segmentation_mode
        if segmentation_mode.lower() not in ['sms', 'sms2', 'srm'] :
            raise NameError(cyan + "Segmentation : " + bold + red + "Parameter 'segmentation_mode' value  is not in list ['sms2','sms', 'srm']." + endC)

    # Récupération des parametres de l'algo de Large Scale MeanShift 'sms'

    # Le paramétre du rayon de voisinage spatial pour lea moyen
    if args.spatialr != None:
        spatialr = args.spatialr

    # Le paramétre du seuil de distance euclidienne
    if args.range != None:
        ranger = args.ranger

    # Le paramétre du seuil de taille minimale du segment
    if args.minsize != None:
        minsize = args.minsize

    # Taille de la grille de travail
    if args.tilesize!= None:
        tilesize = args.tilesize

    # Récupération des parametres de l'algo de MeanShift 'sms2'
    # Le paramétre du rayon de voisinage spatial pour lea moyen
    if args.spatialr2 != None:
        spatialr2 = args.spatialr2

    # Le paramétre du seuil de distance euclidienne
    if args.ranger2 != None:
        ranger2 = args.ranger2

    # Le paramétre du nombre d'iterations
    if args.number_iteration2 != None:
        number_iteration2 = args.number_iteration2

    # Le paramétre du seuil de taille minimale du segment lors de la segmentation
    if args.minregsize2 != None:
        minregsize2 = args.minregsize2

    # Le paramétre du seuil de taille minimale du segment
    if args.minsize2 != None:
        minsize2 = args.minsize2

    # Taille de la grille de travail
    if args.tilesize2!= None:
        tilesize2 = args.tilesize2

    # Récupération des parametres de l'algo de Region Merging 'srm'
    # Le paramétre du ctritère
    if args.homogeneity_criterion != None:
        homogeneity_criterion = args.homogeneity_criterion
        if homogeneity_criterion.lower() not in ['bs', 'ed', 'fls'] :
            raise NameError(cyan + "SupervisedClassification : " + bold + red + "Parameter 'homogeneity_criterion' value  is not in list ['bs', 'ed', 'fls']." + endC)

    # Le paramétre du seuil du critère d'homogénéité
    if args.threshol != None:
        threshol = args.threshol

    # Le paramétre du nombre d'itération
    if args.number_iteration != None:
        number_iteration = args.number_iteration

    # Le paramétre d'augmentation la vitesse de segmentation
    if args.speed != None:
        speed = args.speed

    # Le paramétre du poids pour l'homogénéité spectrale
    if args.weight_spectral != None:
        weight_spectral = args.weight_spectral

    # Le paramétre du poids pour l'homogénéité spatial
    if args.weight_spatial != None:
        weight_spatial = args.weight_spatial

    # Récupération du parametre ram
    if args.ram_otb != None:
        ram_otb = args.ram_otb

    # Récupération du format du fichier de sortie
    if args.format_vector != None :
        format_vector = args.format_vector

    # Récupération du format du fichier de sortie
    if args.format_raster != None :
        format_raster = args.format_raster

    # Récupération de l'extension des fichiers vecteurs
    if args.extension_vector != None:
        extension_vector = args.extension_vector

    # Récupération de l'extension des fichiers vecteurs
    if args.extension_raster != None:
        extension_raster = args.extension_raster

    # Récupération du nom du fichier log
    if args.path_time_log!= None:
        path_time_log = args.path_time_log

    if args.save_results_inter!= None:
        save_results_intermediate = args.save_results_inter

    if args.overwrite!= None:
        overwrite = args.overwrite

    # Récupération de l'option niveau de debug
    if args.debug!= None:
        global debug
        debug = args.debug

    if debug >= 3:
        print(bold + green + "Variables dans le parser" + endC)
        print(cyan + "Segmentation : " + endC + "image_input : " + str(image_input) + endC)
        print(cyan + "Segmentation : " + endC + "mask_input : " + str(mask_input) + endC)
        print(cyan + "Segmentation : " + endC + "vector_output : " + str(vector_output) + endC)
        print(cyan + "Segmentation : " + endC + "raster_output : " + str(raster_output) + endC)
        print(cyan + "Segmentation : " + endC + "segmentation_mode : " + str(segmentation_mode) + endC)
        print(cyan + "Segmentation : " + endC + "spatialr : " + str(spatialr) + endC)
        print(cyan + "Segmentation : " + endC + "ranger : " + str(ranger) + endC)
        print(cyan + "Segmentation : " + endC + "minsize : " + str(minsize) + endC)
        print(cyan + "Segmentation : " + endC + "tilesize : " + str(tilesize) + endC)
        print(cyan + "Segmentation : " + endC + "minregsize : " + str(minregsize) + endC)
        print(cyan + "Segmentation : " + endC + "homogeneity_criterion : " + str(homogeneity_criterion) + endC)
        print(cyan + "Segmentation : " + endC + "threshol : " + str(threshol) + endC)
        print(cyan + "Segmentation : " + endC + "number_iteration : " + str(number_iteration) + endC)
        print(cyan + "Segmentation : " + endC + "speed : " + str(speed) + endC)
        print(cyan + "Segmentation : " + endC + "weight_spectral : " + str(weight_spectral) + endC)
        print(cyan + "Segmentation : " + endC + "weight_spatial : " + str(weight_spatial) + endC)
        print(cyan + "Segmentation : " + endC + "ram_otb : " + str(ram_otb) + endC)
        print(cyan + "Segmentation : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "Segmentation : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "Segmentation : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "Segmentation : " + endC + "save_results_inter : " + str(save_results_intermediate) + endC)
        print(cyan + "Segmentation : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "Segmentation : " + endC + "debug : " + str(debug) + endC)

    # EXECUTION DE LA FONCTION
    # Si le dossier de sortie n'existe pas, on le crée
    if vector_output != "":
        repertory_output = os.path.dirname(vector_output)
    else :
        repertory_output = os.path.dirname(raster_output)
    if not os.path.isdir(repertory_output):
        os.makedirs(repertory_output)

    # Regroupement des parametres du SMS dans une structure
    sms_parametres_struct = StructSMSParameter()
    sms_parametres_struct.spatial_radius = spatialr
    sms_parametres_struct.range_radius = ranger
    sms_parametres_struct.min_segement_size = minsize
    sms_parametres_struct.tile_size = tilesize

    # Regroupement des parametres du SMS2 dans une structure
    sms2_parametres_struct = StructSMS2Parameter()
    sms2_parametres_struct.spatial_radius = spatialr2
    sms2_parametres_struct.range_radius = ranger2
    sms2_parametres_struct.number_iteration = number_iteration2
    sms2_parametres_struct.min_region_size = minregsize2
    sms2_parametres_struct.minsize = minsize2
    sms2_parametres_struct.tile_size = tilesize2

    # Regroupement des parametres du SRM dans une structure
    srm_parametres_struct = StructSRMParameter()
    srm_parametres_struct.homogeneity_criterion = homogeneity_criterion
    srm_parametres_struct.threshol_criterion = threshol
    srm_parametres_struct.number_iteration = number_iteration
    srm_parametres_struct.segmentation_speed = speed
    srm_parametres_struct.weight_spectral_homogeneity = weight_spectral
    srm_parametres_struct.weight_spatial_homogeneity = weight_spatial

    # execution de la fonction pour une image
    segmentImage(image_input, mask_input, raster_output, vector_output, segmentation_mode, sms_parametres_struct,sms2_parametres_struct, srm_parametres_struct, path_time_log, ram_otb, format_vector, format_raster, extension_vector, extension_raster,save_results_intermediate, overwrite)

# ================================================

if __name__ == '__main__':
  main(gui=False)
