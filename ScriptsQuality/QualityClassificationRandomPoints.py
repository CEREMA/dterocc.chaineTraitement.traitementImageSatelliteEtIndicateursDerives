#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# CE SCRIPT PERMET DE FAIRE UNE ESTIMATION DE LA QUALITE D'UNE IMAGE DE CLASSIFICATION PAR TIRAGE DE POINTS ALEATOIRES                      #
#                                                                                                                                           #
#############################################################################################################################################
"""
Nom de l'objet : QualityClassificationRandomPoints.py
Description :
-------------
Objectif : Estimer la qualiter d'une image de classifition par tirage aléatoire de points
Rq : utilisation des OTB Applications : ...

Date de creation : 04/07/2016
----------
Histoire :
----------
Origine : Nouveau
04/07/2016 : Création
-----------------------------------------------------------------------------------------------------
Modifications
15/03/2019 : Ajout de la possibilité de nommer les champs en sortie (et de récupérer l'information d'un champ particulier du fichier points d'entrée, si validation a priori)
------------------------------------------------------
A Reflechir/A faire
 -
 -
"""

from __future__ import print_function
import os,sys,glob,argparse,string,random
from scipy.stats import chi2
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_log import timeLine
from osgeo import ogr
from Lib_raster import getPixelWidthXYImage, getGeometryImage, getEmpriseImage, getPixelsValueListImage, cutImageByVector, createVectorMask
from Lib_vector import createPointsFromCoordList, cutVectorAll, readVectorFilePoints, addNewFieldVector, setAttributeValuesList
from Lib_file import removeVectorFile, copyVectorFile, removeFile, renameVectorFile

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 3

###########################################################################################################################################
# FONCTION computeNumberPointsToShoot()                                                                                                   #
###########################################################################################################################################
def computeNumberPointsToShoot(k_class, percent_class_near_fifty, l_khi=1, alpha=0.05, error=0.05) :
    """
    # ROLE:
    #     Permet de donne le chiffre de point à tirer pour échantilloner les points de controle.
    #
    # ENTREES DE LA FONCTION :
    #     k_class (int) : Nombre de classes
    #     percent_class_near_fifty (float) : Proportion de la classe la plus proche de 50 %
    #     l_khi (int) : Loi de khi deux à un degré de liberté, (par défaut : 1)
    #     alpha (float) : Seuil d'erreur choisi, (par défaut : 0.05)
    #     error (float) : Erreur maximale tolérée, (par défaut : 0.05)
    #
    # SORTIES DE LA FONCTION :
    #    number_random_points : le nombre de points aléatoires à tirer
    #
    """

    # Définir les paramètres initiaux (exemple)
    # k_class = 9                      # Nombre de classes
    # percent_class_near_fifty = 33.27 # Proportion de la classe la plus proche de 50 %
    # l_khi = 1                        # Loi de khi deux à un degré de liberté
    # alpha = 0.05                     # Seuil d'erreur choisi
    # error = 0.05                     # Erreur maximale tolérée


    # Calculer le chi carré en utilisant la fonction chi2.ppf
    # Cette fonction retourne la valeur de chi carré correspondant au seuil de confiance spécifié et au nombre de dégrés de liberté
    chi_square = chi2.ppf(1 - alpha / k_class, l_khi)

    # Afficher le chi carré calculé
    print(cyan + "computeNumberPointsToShoot() : " + endC +"Chi carré calculé :", chi_square)

    # Pourcentage de la classe qui se rapproche le plus de 50%
    percent_class_near_fifty = percent_class_near_fifty / 100 # Convertir en décimal

    # Calcul du nombre de points aléatoires à tirer en utilisant la formule spécifiée
    number_random_points = (chi_square * percent_class_near_fifty * (1 - percent_class_near_fifty)) / (error * error)

    # Afficher le nombre de points aléatoires à tirer
    print(cyan + "computeNumberPointsToShoot() : " + endC + "Nombre de points aléatoires à tirer :", number_random_points)

    return number_random_points

###########################################################################################################################################
# FONCTION estimateQualityClassification()                                                                                                #
###########################################################################################################################################
def estimateQualityClassification(image_input, vector_cut_input, vector_sample_input, vector_output, nb_dot, no_data_value, column_name_vector, column_name_ref, column_name_class, path_time_log, epsg=2154, format_raster='GTiff', format_vector="ESRI Shapefile", extension_raster=".tif", extension_vector=".shp", save_results_intermediate=False, overwrite=True):
    """
    # ROLE:
    #     Estimer la qualiter d'une image de classifition par tirage aléatoire de points dans une zone d'étude d'une image de classification
    #     et récupération de valeur des points de test dans l'image de classification
    #
    # ENTREES DE LA FONCTION :
    #     image_input : l'image d'entrée qui sera découpé
    #     vector_cut_input: le vecteur pour le découpage (zone d'étude)
    #     vector_sample_input : le vecteur d'échantillon de points
    #     vector_output : le fichier de sortie contenant les points du tirage aléatoire, ou issus du vecteur d'échantillon
    #     nb_dot : nombre de points du tirage aléatoire
    #     no_data_value : Valeur de  pixel du no data
    #     column_name_vector : champ du fichier vecteur d'entrée contenant l'information de classe (= référence)
    #     column_name_ref : champ du fichier vecteur de sortie contenant l'information de classe de référence (issu du fichier d'entrée, ou pour validation a posteriori)
    #     column_name_class : champ du fichier vecteur de sortie contenant l'information de classe issue du raster d'entrée
    #     path_time_log : le fichier de log de sortie
    #     epsg : Optionnel : par défaut 2154
    #     format_raster : Format de l'image de sortie, par défaut : GTiff
    #     format_vector  : format du vecteur de sortie, par defaut = 'ESRI Shapefile'
    #     extension_raster : extension des fichiers raster de sortie, par defaut = '.tif'
    #     extension_vector : extension du fichier vecteur de sortie, par defaut = '.shp'
    #     save_results_intermediate : fichiers de sorties intermediaires nettoyees, par defaut = False
    #     overwrite : écrase si un fichier existant a le même nom qu'un fichier de sortie, par defaut a True
    #
    # SORTIES DE LA FONCTION :
    #    un fichier vecteur contenant les points de controles avec en attributs la valeurs de références (par photo interpretation) et la valeur de la classification
    #
    """

    # Mise à jour du Log
    starting_event = "estimateQualityClassification() : Masks creation starting : "
    timeLine(path_time_log,starting_event)

    print(endC)
    print(bold + green + "## START : CREATE PRINT POINTS FILE FROM CLASSIF IMAGE" + endC)
    print(endC)

    if debug >= 2:
        print(bold + green + "estimateQualityClassification() : Variables dans la fonction" + endC)
        print(cyan + "estimateQualityClassification() : " + endC + "image_input : " + str(image_input) + endC)
        print(cyan + "estimateQualityClassification() : " + endC + "vector_cut_input : " + str(vector_cut_input) + endC)
        print(cyan + "estimateQualityClassification() : " + endC + "vector_sample_input : " + str(vector_sample_input) + endC)
        print(cyan + "estimateQualityClassification() : " + endC + "vector_output : " + str(vector_output) + endC)
        print(cyan + "estimateQualityClassification() : " + endC + "nb_dot : " + str(nb_dot) + endC)
        print(cyan + "estimateQualityClassification() : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "estimateQualityClassification() : " + endC + "column_name_vector : " + str(column_name_vector) + endC)
        print(cyan + "estimateQualityClassification() : " + endC + "column_name_ref : " + str(column_name_ref) + endC)
        print(cyan + "estimateQualityClassification() : " + endC + "column_name_class : " + str(column_name_class) + endC)
        print(cyan + "estimateQualityClassification() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "estimateQualityClassification() : " + endC + "epsg  : " + str(epsg) + endC)
        print(cyan + "estimateQualityClassification() : " + endC + "format_raster : " + str(format_raster) + endC)
        print(cyan + "estimateQualityClassification() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "estimateQualityClassification() : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "estimateQualityClassification() : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "estimateQualityClassification() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "estimateQualityClassification() : " + endC + "overwrite : " + str(overwrite) + endC)

    # ETAPE 0 : PREPARATION DES FICHIERS INTERMEDIAIRES

    CODAGE = "uint16"

    SUFFIX_STUDY = '_study'
    SUFFIX_CUT = '_cut'
    SUFFIX_TEMP = '_temp'
    SUFFIX_SAMPLE = '_sample'

    repertory_output = os.path.dirname(vector_output)
    base_name = os.path.splitext(os.path.basename(vector_output))[0]

    vector_output_temp = repertory_output + os.sep + base_name + SUFFIX_TEMP + extension_vector
    raster_study = repertory_output + os.sep + base_name + SUFFIX_STUDY + extension_raster
    vector_study = repertory_output + os.sep + base_name + SUFFIX_STUDY + extension_vector
    raster_cut = repertory_output + os.sep + base_name + SUFFIX_CUT + extension_raster
    vector_sample_temp = repertory_output + os.sep + base_name + SUFFIX_SAMPLE + SUFFIX_TEMP + extension_vector

    # Mise à jour des noms de champs
    input_ref_col = ""
    val_ref = 0
    if (column_name_vector != "") and (not column_name_vector is None):
        input_ref_col = column_name_vector
    if (column_name_ref != "") and (not column_name_ref is None):
        val_ref_col = column_name_ref
    if (column_name_class != "") and (not column_name_class is None):
        val_class_col = column_name_class

    # ETAPE 1 : DEFINIR UN SHAPE ZONE D'ETUDE

    if (not vector_cut_input is None) and (vector_cut_input != "") and (os.path.isfile(vector_cut_input)) :
        cutting_action = True
        vector_study = vector_cut_input

    else :
        cutting_action = False
        createVectorMask(image_input, vector_study)

    # ETAPE 2 : DECOUPAGE DU RASTEUR PAR LE VECTEUR D'EMPRISE SI BESOIN

    if cutting_action :
        # Identification de la tailles de pixels en x et en y
        pixel_size_x, pixel_size_y = getPixelWidthXYImage(image_input)

        # Si le fichier de sortie existe deja le supprimer
        if os.path.exists(raster_cut) :
            removeFile(raster_cut)

        # Commande de découpe
        if not cutImageByVector(vector_study, image_input, raster_cut, pixel_size_x, pixel_size_y, False, no_data_value, 0, format_raster, format_vector) :
            raise NameError(cyan + "estimateQualityClassification() : " + bold + red + "Une erreur c'est produite au cours du decoupage de l'image : " + image_input + endC)
        if debug >=2:
            print(cyan + "estimateQualityClassification() : " + bold + green + "DECOUPAGE DU RASTER %s AVEC LE VECTEUR %s" %(image_input, vector_study) + endC)
    else :
        raster_cut = image_input

    # ETAPE 3 : CREATION DE LISTE POINTS AVEC DONNEE ISSU D'UN FICHIER RASTER

    # Gémotrie de l'image
    cols, rows, bands = getGeometryImage(raster_cut)
    xmin, xmax, ymin, ymax = getEmpriseImage(raster_cut)
    pixel_width, pixel_height = getPixelWidthXYImage(raster_cut)

    if debug >=2:
        print("cols : " + str(cols))
        print("rows : " + str(rows))
        print("bands : " + str(bands))
        print("xmin : " + str(xmin))
        print("ymin : " + str(ymin))
        print("xmax : " + str(xmax))
        print("ymax : " + str(ymax))
        print("pixel_width : " + str(pixel_width))
        print("pixel_height : " + str(pixel_height))

    # ETAPE 3-1 : CAS CREATION D'UN FICHIER DE POINTS PAR TIRAGE ALEATOIRE DANS LA MATRICE IMAGE
    if (vector_sample_input is None) or (vector_sample_input == "")  :
        is_sample_file = False

        # Les dimensions de l'image
        nb_pixels = abs(cols * rows)

        # Tirage aléatoire des points
        drawn_dot_list = []
        while len(drawn_dot_list) < nb_dot :
            val = random.randint(0,nb_pixels)
            if not val in drawn_dot_list :
                drawn_dot_list.append(val)

        # Creation d'un dico index valeur du tirage et attibuts pos_x, pos_y et value pixel
        points_random_value_dico = {}

        points_coordonnees_list = []
        for point in drawn_dot_list:
            pos_y = point // cols
            pos_x = point % cols
            coordonnees_list = [pos_x, pos_y]
            points_coordonnees_list.append(coordonnees_list)

        # Lecture dans le fichier raster des valeurs
        values_list = getPixelsValueListImage(raster_cut, points_coordonnees_list)
        print(values_list)
        for idx_point in range (len(drawn_dot_list)):
            val_class = values_list[idx_point]
            coordonnees_list = points_coordonnees_list[idx_point]
            pos_x = coordonnees_list[0]
            pos_y = coordonnees_list[1]
            coor_x = xmin + (pos_x * abs(pixel_width))
            coor_y = ymax - (pos_y * abs(pixel_height))
            point_attr_dico = {"Ident":idx_point, val_ref_col:int(val_ref), val_class_col:int(val_class)}
            points_random_value_dico[idx_point] = [[coor_x, coor_y], point_attr_dico]

            if debug >=4:
                print("idx_point : " + str(idx_point))
                print("pos_x : " + str(pos_x))
                print("pos_y : " + str(pos_y))
                print("coor_x : " + str(coor_x))
                print("coor_y : " + str(coor_y))
                print("val_class : " + str(val_class))
                print("")

    # ETAPE 3-2 : CAS D'UN FICHIER DE POINTS DEJA EXISTANT MISE A JOUR DE LA DONNEE ISSU Du RASTER
    else :
        # Le fichier de points d'analyses existe
        is_sample_file = True
        cutVectorAll(vector_study, vector_sample_input, vector_sample_temp, format_vector)
        if input_ref_col != "":
            points_coordinates_dico = readVectorFilePoints(vector_sample_temp, [input_ref_col], format_vector)
        else:
            points_coordinates_dico = readVectorFilePoints(vector_sample_temp, [], format_vector)

        # Création du dico
        points_random_value_dico = {}

        points_coordonnees_list = []
        for index_key in points_coordinates_dico:
            # Recuperer les valeurs des coordonnees
            coord_info_list = points_coordinates_dico[index_key]
            coor_x = coord_info_list[0]
            coor_y = coord_info_list[1]
            pos_x = int(round((coor_x - xmin) / abs(pixel_width)))
            pos_y = int(round((ymax - coor_y) / abs(pixel_height)))
            coordonnees_list = [pos_x, pos_y]
            points_coordonnees_list.append(coordonnees_list)

        # Lecture dans le fichier raster des valeurs
        values_list = getPixelsValueListImage(raster_cut, points_coordonnees_list)

        for index_key in points_coordinates_dico:
            # Récuperer les valeurs des coordonnees
            coord_info_list = points_coordinates_dico[index_key]
            coor_x = coord_info_list[0]
            coor_y = coord_info_list[1]
            # Récupérer la classe de référence dans le vecteur d'entrée
            if input_ref_col != "":
                label = coord_info_list[2]
                val_ref = label.get(input_ref_col)
            # Récupérer la classe issue du raster d'entrée
            val_class = values_list[index_key]
            # Création du dico contenant identifiant du point, valeur de référence, valeur du raster d'entrée
            point_attr_dico = {"Ident":index_key, val_ref_col:int(val_ref), val_class_col:int(val_class)}
            if debug >= 4:
                print("point_attr_dico: " + str(point_attr_dico))
            points_random_value_dico[index_key] = [[coor_x, coor_y], point_attr_dico]

    # ETAPE 4 : CREATION ET DECOUPAGE DU FICHIER VECTEUR RESULTAT PAR LE SHAPE D'ETUDE

    # Creer le fichier de points
    if is_sample_file and os.path.exists(vector_sample_temp) :

        attribute_dico = {val_class_col:ogr.OFTInteger}
        # Recopie du fichier
        removeVectorFile(vector_output_temp)
        copyVectorFile(vector_sample_temp, vector_output_temp)

        # Ajout des champs au fichier de sortie
        for field_name in attribute_dico :
            addNewFieldVector(vector_output_temp, field_name, attribute_dico[field_name], 0, None, None, format_vector)

        # Préparation des donnees
        field_new_values_list = []
        for index_key in points_random_value_dico:
            point_attr_dico = points_random_value_dico[index_key][1]
            point_attr_dico.pop(val_ref_col, None)
            field_new_values_list.append(point_attr_dico)

        # Ajout des donnees
        setAttributeValuesList(vector_output_temp, field_new_values_list, format_vector)

    else :
        # Définir les attibuts du fichier résultat
        attribute_dico = {"Ident":ogr.OFTInteger, val_ref_col:ogr.OFTInteger, val_class_col:ogr.OFTInteger}

        createPointsFromCoordList(attribute_dico, points_random_value_dico, vector_output_temp, epsg, format_vector)

    # Découpage du fichier de points d'echantillons
    cutVectorAll(vector_study, vector_output_temp, vector_output, format_vector)

    # ETAPE 5 : SUPPRESIONS FICHIERS INTERMEDIAIRES INUTILES

    # Suppression des données intermédiaires
    if not save_results_intermediate:
        if cutting_action :
            removeFile(raster_cut)
        else :
            removeVectorFile(vector_study)
            removeFile(raster_study)
        if is_sample_file :
            removeVectorFile(vector_sample_temp)
        removeVectorFile(vector_output_temp)

    print(endC)
    print(bold + green + "## END : CREATE PRINT POINTS FILE FROM CLASSIF IMAGE" + endC)
    print(endC)

    # Mise à jour du Log
    ending_event = "estimateQualityClassification() : Masks creation ending : "
    timeLine(path_time_log,ending_event)

    return

###########################################################################################################################################
# MISE EN PLACE DU PARSER                                                                                                                 #
###########################################################################################################################################

# Code executé seulement dans le cas ou le script est lancé depuis une ligne de commande
# Il n'est pas executé lors d'un import QualityClassificationRandomPoints.py
# Exemple de lancement en ligne de commande:
# python QualityClassificationRandomPoints.py -i /mnt/Data/gilles.fouvet/Saturn/QualiteClassification/temp/CUB_Classification_2014.tif -v /mnt/Data/gilles.fouvet/Saturn/QualiteClassification/temp/CUB_Contour_bord_net_cut.shp -o /mnt/Data/gilles.fouvet/Saturn/QualiteClassification/temp/CUB_zone_gril.shp -nb 100 -log /mnt/Data/gilles.fouvet/Saturn/QualiteClassification/temp/fichierTestLog.txt

def main(gui=False):

    # Définition des différents paramètres du parser
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,  prog="QualityClassificationRandomPoints", description="\
    Info : Estimating the quality of image classification by random drawing points. \n\
    Objectif : Estimer la qualiter d'une image de classifition par tirage de points aléatoires. \n\
    Example : python QualityClassificationRandomPoints.py -i /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/Macro/CUB_zone_test_NE_Bati.tif \n\
                                                          -v /mnt/Data/gilles.fouvet/RA/Rhone/Global/Preparation/Landscapes_Boundaries/Paysage_01.shp \n\
                                                          -o /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/Macro/CUB_zone_test_NE_Bati_mask.shp \n\
                                                          -log /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/fichierTestLog.txt")

    parser.add_argument('-i','--image_input',default="", help="Image input to qualify", type=str, required=True)
    parser.add_argument('-v','--vector_cut_input',default=None, help="Vector input define the study area.", type=str, required=False)
    parser.add_argument('-p','--vector_sample_input',default=None, help="Vector input of sample for comparaison.", type=str, required=False)
    parser.add_argument('-o','--vector_output',default="", help="Vector output contain dots from the random draw, or from input sample vector, into study area.", type=str, required=True)
    parser.add_argument('-nc','--nb_class',default=0, help="Number of class.", type=int, required=False)
    parser.add_argument('-cnf','--class_near_fifty',default=0.0, help="Value of class near fifty in percent.", type=float, required=False)
    parser.add_argument('-nb','--nb_dot',default=1000, help="Number of points drawn randomly.", type=int, required=False)
    parser.add_argument('-ndv','--no_data_value', default=0, help="Option: Value of the pixel no data. By default : 0", type=int, required=False)
    parser.add_argument('-col','--column_name_vector', default="ValRef", help="Option: Column name in the input vector with the reference information.", type=str, required=False)
    parser.add_argument('-colr','--column_name_ref', default="ValRef", help="Option: Output column name for the reference information (from the input sample vector, or to check after if no input sample vector).", type=str, required=False)
    parser.add_argument('-colc','--column_name_class', default="ValClass", help="Option: Output column name for the classification information from the input raster.", type=str, required=False)
    parser.add_argument('-epsg','--epsg', default=2154,help="Projection of the output file.", type=int, required=False)
    parser.add_argument('-raf','--format_raster', default="GTiff", help="Option : Format output image, by default : GTiff (GTiff, HFA...)", type=str, required=False)
    parser.add_argument('-vef','--format_vector',default="ESRI Shapefile",help="Option : Vector format. By default : ESRI Shapefile", type=str, required=False)
    parser.add_argument('-rae','--extension_raster', default=".tif", help="Option : Extension file for image raster. By default : '.tif'", type=str, required=False)
    parser.add_argument('-vee','--extension_vector',default=".shp",help="Option : Extension file for vector. By default : '.shp'", type=str, required=False)
    parser.add_argument('-log','--path_time_log',default="",help="Name of log", type=str, required=False)
    parser.add_argument('-sav','--save_results_inter',action='store_true',default=False,help="Save or delete intermediate result after the process. By default, False", required=False)
    parser.add_argument('-now','--overwrite',action='store_false',default=True,help="Overwrite files with same names. By default, True", required=False)
    parser.add_argument('-debug','--debug',default=3,help="Option : Value of level debug trace, default : 3 ",type=int, required=False)
    args = displayIHM(gui, parser)

    # RECUPERATION DES ARGUMENTS

    # Récupération de l'image d'entrée
    if args.image_input != None:
        image_input = args.image_input
        if not os.path.isfile(image_input):
            raise NameError (cyan + "QualityClassificationRandomPoints : " + bold + red  + "File %s not existe!" %(image_input) + endC)

    # Récupération du vecteur de decoupe
    vector_cut_input = None
    if args.vector_cut_input != None :
        vector_cut_input = args.vector_cut_input
        if vector_cut_input != "" and not os.path.isfile(vector_cut_input):
            raise NameError (cyan + "QualityClassificationRandomPoints : " + bold + red  + "File %s not existe!" %(vector_cut_input) + endC)

    # Récupération du vecteur d'échantillonage
    vector_sample_input = None
    if args.vector_sample_input != None :
        vector_sample_input = args.vector_sample_input
        if vector_sample_input != "" and not os.path.isfile(vector_sample_input):
            raise NameError (cyan + "QualityClassificationRandomPoints : " + bold + red  + "File %s not existe!" %(vector_sample_input) + endC)

    # Récupération du fichier de sortie
    if args.vector_output != None:
        vector_output = args.vector_output

    # Récupération du parametre de nombre de tirage aléatoire
    if args.nb_class != None:
        nb_class = args.nb_class
    if args.class_near_fifty != None:
        class_near_fifty = args.class_near_fifty

    if args.nb_dot != None:
        nb_dot = args.nb_dot

    # Récupération du parametre no_data_value
    if args.no_data_value != None:
        no_data_value = args.no_data_value

    # Récupération du parametre column_name_vector
    if args.column_name_vector != None:
        column_name_vector = args.column_name_vector

    # Récupération du parametre column_name_ref
    if args.column_name_ref != None:
        column_name_ref = args.column_name_ref

    # Récupération du parametre column_name_class
    if args.column_name_class != None:
        column_name_class = args.column_name_class

    # Récupération de la projection du fichier de sortie
    if args.epsg != None :
        epsg = args.epsg

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
    if args.path_time_log != None:
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
        print(bold + green + "QualityClassificationRandomPoints : Variables dans le parser" + endC)
        print(cyan + "QualityClassificationRandomPoints : " + endC + "image_input : " + str(image_input) + endC)
        print(cyan + "QualityClassificationRandomPoints : " + endC + "vector_cut_input : " + str(vector_cut_input) + endC)
        print(cyan + "QualityClassificationRandomPoints : " + endC + "vector_sample_input : " + str(vector_sample_input) + endC)
        print(cyan + "QualityClassificationRandomPoints : " + endC + "vector_output : " + str(vector_output) + endC)
        print(cyan + "QualityClassificationRandomPoints : " + endC + "nb_class : " + str(nb_class) + endC)
        print(cyan + "QualityClassificationRandomPoints : " + endC + "class_near_fifty : " + str(class_near_fifty) + endC)
        print(cyan + "QualityClassificationRandomPoints : " + endC + "nb_dot : " + str(nb_dot) + endC)
        print(cyan + "QualityClassificationRandomPoints : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "QualityClassificationRandomPoints : " + endC + "column_name_vector : " + str(column_name_vector) + endC)
        print(cyan + "QualityClassificationRandomPoints : " + endC + "column_name_ref : " + str(column_name_ref) + endC)
        print(cyan + "QualityClassificationRandomPoints : " + endC + "column_name_class : " + str(column_name_class) + endC)
        print(cyan + "QualityClassificationRandomPoints : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "QualityClassificationRandomPoints : " + endC + "format_raster : " + str(format_raster) + endC)
        print(cyan + "QualityClassificationRandomPoints : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "QualityClassificationRandomPoints : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "QualityClassificationRandomPoints : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "QualityClassificationRandomPoints : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "QualityClassificationRandomPoints : " + endC + "save_results_inter : " + str(save_results_intermediate) + endC)
        print(cyan + "QualityClassificationRandomPoints : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "QualityClassificationRandomPoints : " + endC + "debug : " + str(debug) + endC)

    # EXECUTION DE LA FONCTION
    # Si le dossier de sortie n'existent pas, on le crée
    repertory_output = os.path.dirname(vector_output)
    if not os.path.isdir(repertory_output):
        os.makedirs(repertory_output)

    # Execution de la fonction pour calculer le nombre de point
    if nb_class != 0:
        nb_dot = computeNumberPointsToShoot(nb_class, class_near_fifty)
    # Execution de la fonction pour une image
    estimateQualityClassification(image_input, vector_cut_input, vector_sample_input, vector_output, nb_dot, no_data_value, column_name_vector, column_name_ref, column_name_class, path_time_log, epsg, format_raster, format_vector, extension_raster, extension_vector, save_results_intermediate, overwrite)

# ================================================

if __name__ == '__main__':
  main(gui=False)
