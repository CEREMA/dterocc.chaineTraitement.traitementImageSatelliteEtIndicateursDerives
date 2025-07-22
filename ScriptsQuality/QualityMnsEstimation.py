#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# CE SCRIPT PERMET DE FAIRE UNE ESTIMATION DE LA QUALITE D'UN MNS PAR COMPARAISON AVEC DES DONNEES DE LA BD TOPO                            #
#                                                                                                                                           #
#############################################################################################################################################
"""
Nom de l'objet : QualityMnsEstimation.py
Description :
-------------
Objectif : Estimer la qualiter d'une image de MNS par comparaison à des données de la BD topo
Rq : utilisation des OTB Applications : none

Date de creation : 30/11/2016
----------
Histoire :
----------
Origine : Nouveau
30/11/2016 : Création
-----------------------------------------------------------------------------------------------------
Modifications

------------------------------------------------------
A Reflechir/A faire
 -
 -
"""

from __future__ import print_function
import os,sys,glob,argparse,string,csv
from osgeo import ogr
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_log import timeLine
from Lib_raster import getPixelWidthXYImage, cutImageByVector, getGeometryImage, getEmpriseImage, getPixelsValueListImage, createVectorMask
from Lib_vector import cutoutVectors, cutVectorAll, fusionVectors, bufferVector, multigeometries2geometries, readVectorFileLinesExtractTeminalsPoints, readVectorFilePoints, createPointsFromCoordList
from Lib_file import removeVectorFile, removeFile
from Lib_text import convertDbf2Csv, extractDico

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 3

###########################################################################################################################################
# FONCTION estimateQualityMns()                                                                                                           #
###########################################################################################################################################
def estimateQualityMns(image_input, vector_cut_input, vector_sample_input_list, vector_sample_points_input, raster_input_dico, vector_output, no_data_value, path_time_log, format_raster='GTiff', epsg=2154, format_vector='ESRI Shapefile', extension_raster=".tif", extension_vector=".shp", save_results_intermediate=False, overwrite=True):
    """
    # ROLE:
    #     Estimer la qualiter d'un MNS valeur de hauteur en comparaison à des données issue de la BD TOPO de l'IGN
    #
    # ENTREES DE LA FONCTION :
    #     image_input : l'image MNS d'entrée qui sera estimé
    #     vector_cut_input: le vecteur pour le découpage (zone d'étude)
    #     vector_sample_input_list : Liste des vecteurs d'échantillon de référence
    #     vector_sample_points_input : le vecteur d'échantillon de points !!! si non null remplace vector_sample_input_list
    #     raster_input_dico : Dico  contenant les fichiers raster d'autres données et les valeurs min et max de filtrage
    #     vector_output : le fichier de sortie contenant les points de controle
    #     no_data_value : Valeur de  pixel du no data
    #     path_time_log : le fichier de log de sortie
    #     epsg : Optionnel : par défaut 2154
    #     format_raster : Format de l'image de sortie, par défaut : GTiff
    #     format_vector : format du fichier vecteur. Optionnel, par default : 'ESRI Shapefile'
    #     extension_raster : extension des fichiers raster de sortie, par defaut = '.tif'
    #     extension_vector : extension du fichier vecteur de sortie, par defaut = '.shp'
    #     save_results_intermediate : fichiers de sorties intermediaires nettoyees, par defaut = False
    #     overwrite : écrase si un fichier existant a le même nom qu'un fichier de sortie, par defaut a True
    #
    # SORTIES DE LA FONCTION :
    #    un fichier vecteur contenant les points de controles avec en attributs la valeurs de références (issu de la BD) et la valeur du MNS
    #
    """

    # Mise à jour du Log
    starting_event = "estimateQualityMns() : Masks creation starting : "
    timeLine(path_time_log,starting_event)

    print(endC)
    print(bold + green + "## START : CREATE HEIGHT POINTS FILE FROM MNS" + endC)
    print(endC)

    if debug >= 2:
        print(bold + green + "estimateQualityMns() : Variables dans la fonction" + endC)
        print(cyan + "estimateQualityMns() : " + endC + "image_input : " + str(image_input) + endC)
        print(cyan + "estimateQualityMns() : " + endC + "vector_cut_input : " + str(vector_cut_input) + endC)
        print(cyan + "estimateQualityMns() : " + endC + "vector_sample_input_list : " + str(vector_sample_input_list) + endC)
        print(cyan + "estimateQualityMns() : " + endC + "vector_sample_points_input : " + str(vector_sample_points_input) + endC)
        print(cyan + "estimateQualityMns() : " + endC + "raster_input_dico : " + str(raster_input_dico) + endC)
        print(cyan + "estimateQualityMns() : " + endC + "vector_output : " + str(vector_output) + endC)
        print(cyan + "estimateQualityMns() : " + endC + "no_data_value : " + str(no_data_value))
        print(cyan + "estimateQualityMns() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "estimateQualityMns() : " + endC + "epsg  : " + str(epsg) + endC)
        print(cyan + "estimateQualityMns() : " + endC + "format_raster : " + str(format_raster) + endC)
        print(cyan + "estimateQualityMns() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "estimateQualityMns() : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "estimateQualityMns() : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "estimateQualityMns() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "estimateQualityMns() : " + endC + "overwrite : " + str(overwrite) + endC)

    # Définion des constantes
    EXT_DBF = '.dbf'
    EXT_CSV = '.csv'

    CODAGE = "uint16"

    SUFFIX_STUDY = '_study'
    SUFFIX_CUT = '_cut'
    SUFFIX_TEMP = '_temp'
    SUFFIX_CLEAN = '_clean'
    SUFFIX_SAMPLE = '_sample'

    ATTRIBUTE_ID = "ID"
    ATTRIBUTE_Z_INI = "Z_INI"
    ATTRIBUTE_Z_FIN = "Z_FIN"
    ATTRIBUTE_PREC_ALTI = "PREC_ALTI"
    ATTRIBUTE_Z_REF = "Z_Ref"
    ATTRIBUTE_Z_MNS = "Z_Mns"
    ATTRIBUTE_Z_DELTA = "Z_Delta"

    ERODE_EDGE_POINTS = -1.0

    ERROR_VALUE = -99.0
    ERROR_MIN_VALUE = -9999
    ERROR_MAX_VALUE = 9999

    # ETAPE 0 : PREPARATION DES FICHIERS INTERMEDIAIRES

    # Si le fichier de sortie existe on ecrase
    check = os.path.isfile(vector_output)
    if check and not overwrite : # Si un fichier de sortie avec le même nom existe déjà, et si l'option ecrasement est à false, alors FIN
        print(cyan + "estimateQualityMns() : " + bold + yellow +  "Create  file %s already exist : no actualisation" % (vector_output) + endC)
        return

    if os.path.isfile(os.path.splitext(vector_output)[0] + EXT_CSV) :
        removeFile(os.path.splitext(vector_output)[0] + EXT_CSV)

    repertory_output = os.path.dirname(vector_output)
    base_name = os.path.splitext(os.path.basename(vector_output))[0]

    vector_output_temp = repertory_output + os.sep + base_name + SUFFIX_TEMP + extension_vector
    raster_study = repertory_output + os.sep + base_name + SUFFIX_STUDY + extension_raster
    vector_study = repertory_output + os.sep + base_name + SUFFIX_STUDY + extension_vector
    vector_study_clean = repertory_output + os.sep + base_name + SUFFIX_STUDY + SUFFIX_CLEAN + extension_vector
    image_cut = repertory_output + os.sep + base_name + SUFFIX_CUT + extension_raster
    vector_sample_temp = repertory_output + os.sep + base_name + SUFFIX_SAMPLE + SUFFIX_TEMP + extension_vector
    vector_sample_temp_clean = repertory_output + os.sep + base_name + SUFFIX_SAMPLE + SUFFIX_TEMP + SUFFIX_CLEAN + extension_vector

    # Utilisation des données raster externes
    raster_cut_dico = {}
    for raster_input in raster_input_dico :
        base_name_raster = os.path.splitext(os.path.basename(raster_input))[0]
        raster_cut = repertory_output + os.sep + base_name_raster + SUFFIX_CUT + extension_raster
        raster_cut_dico[raster_input] = raster_cut
        if os.path.exists(raster_cut) :
            removeFile(raster_cut)

    # ETAPE 1 : DEFINIR UN SHAPE ZONE D'ETUDE

    if (not vector_cut_input is None) and (vector_cut_input != "") and (os.path.isfile(vector_cut_input)) :
        cutting_action = True
        vector_study = vector_cut_input

    else :
        cutting_action = False
        createVectorMask(image_input, vector_study)

    # ETAPE 2 : DECOUPAGE DU RASTEUR PAR LE VECTEUR D'ETUDE SI BESOIN ET REECHANTILLONAGE SI BESOIN

    if cutting_action :
        # Identification de la tailles de pixels en x et en y du fichier MNS de reference
        pixel_size_x, pixel_size_y = getPixelWidthXYImage(image_input)

        # Si le fichier de sortie existe deja le supprimer
        if os.path.exists(image_cut) :
            removeFile(image_cut)

        # Commande de découpe
        if not cutImageByVector(vector_study, image_input, image_cut, pixel_size_x, pixel_size_y, False, no_data_value, 0, format_raster, format_vector) :
            print(cyan + "estimateQualityMns() : " + bold + red + "Une erreur c'est produite au cours du decoupage de l'image : " + image_input + endC, file=sys.stderr)
            raise

        if debug >=2:
            print(cyan + "estimateQualityMns() : " + bold + green + "DECOUPAGE DU RASTER %s AVEC LE VECTEUR %s" %(image_input, vector_study) + endC)
    else :
        image_cut = image_input

    # Definir l'emprise du fichier MNS de reference

    # Decoupage de chaque raster de la liste des rasters
    for raster_input in raster_input_dico :
        raster_cut = raster_cut_dico[raster_input]
        if not cutImageByVector(vector_study, raster_input, raster_cut, pixel_size_x, pixel_size_y, False, no_data_value, 0, format_raster, format_vector) :
            raise NameError(cyan + "estimateQualityMns() : " + bold + red + "Une erreur c'est produite au cours du decoupage du raster : " + raster_input + endC)

    # Gémotrie de l'image
    pixel_size_x, pixel_size_y = getPixelWidthXYImage(image_cut)
    cols, rows, bands = getGeometryImage(image_cut)
    xmin, xmax, ymin, ymax = getEmpriseImage(image_cut)

    if debug >= 3:
        print("Geometrie Image : ")
        print("  cols = " + str(cols))
        print("  rows = " + str(rows))
        print("  xmin = " + str(xmin))
        print("  xmax = " + str(xmax))
        print("  ymin = " + str(ymin))
        print("  ymax = " + str(ymax))
        print("  pixel_size_x = " + str(pixel_size_x))
        print("  pixel_size_y = " + str(pixel_size_y))
        print("\n")

    # Création du dico coordonnées des points en systeme cartographique
    points_random_value_dico = {}
    # liste coordonnées des points au format matrice image brute
    points_coordonnees_image_list = []

    # Selon que l'on utilise le fichier de points d'echantillons ou que l'on recréé a partir des sommets des vecteurs lignes
    if (vector_sample_points_input is None) or (vector_sample_points_input == "")  :

        # ETAPE 3 : DECOUPAGES DES VECTEURS DE REFERENCE D'ENTREE PAR LE VECTEUR D'ETUDE ET LEUR FUSION ET
        #           LECTURE D'UN VECTEUR DE LIGNES ET SAUVEGARDE DES COORDONNEES POINTS DES EXTREMITEES ET LEUR HAUTEUR

        # Découpage des vecteurs de bd réference avec le vecteur zone d'étude
        vector_sample_input_cut_list  = []
        for vector_sample in vector_sample_input_list :
            vector_name = os.path.splitext(os.path.basename(vector_sample))[0]
            vector_sample_cut = repertory_output + os.sep + vector_name + SUFFIX_CUT + extension_vector
            vector_sample_input_cut_list.append(vector_sample_cut)
        cutoutVectors(vector_study, vector_sample_input_list, vector_sample_input_cut_list, format_vector)

        # Fusion des vecteurs de bd réference découpés
        fusionVectors(vector_sample_input_cut_list, vector_sample_temp, format_vector)

        # Preparation des colonnes
        names_column_start_point_list = [ATTRIBUTE_ID, ATTRIBUTE_Z_INI, ATTRIBUTE_PREC_ALTI]
        names_column_end_point_list = [ATTRIBUTE_ID, ATTRIBUTE_Z_FIN, ATTRIBUTE_PREC_ALTI]
        fields_list = [ATTRIBUTE_ID, ATTRIBUTE_PREC_ALTI, ATTRIBUTE_Z_INI, ATTRIBUTE_Z_FIN]

        multigeometries2geometries(vector_sample_temp, vector_sample_temp_clean, fields_list, "MULTILINESTRING", format_vector)
        points_coordinates_dico = readVectorFileLinesExtractTeminalsPoints(vector_sample_temp_clean, names_column_start_point_list, names_column_end_point_list, format_vector)

    else :
        # ETAPE 3_BIS : DECOUPAGE DE VECTEURS D'ECHANTILLONS POINTS PAR LE VECTEUR D'EMPRISE ET
        #               LECTURE DES COORDONNES D'ECHANTILLONS DURECTEMENT DANS LE FICHIER VECTEUR POINTS

        # Liste coordonnées des points au format matrice image brute
        cutVectorAll(vector_study, vector_sample_points_input, vector_sample_temp, format_vector)
        points_coordinates_dico = readVectorFilePoints(vector_sample_temp, format_vector)

    # ETAPE 4 : PREPARATION DU VECTEUR DE POINTS

    for index_key in points_coordinates_dico:
        # Recuperer les valeurs des coordonnees
        coord_info_list = points_coordinates_dico[index_key]
        coor_x = coord_info_list[0]
        coor_y = coord_info_list[1]
        attribut_dico = coord_info_list[2]

        # Coordonnées des points au format matrice image
        pos_x = int(round((coor_x - xmin) / abs(pixel_size_x)) -1)
        pos_y = int(round((ymax - coor_y) / abs(pixel_size_y)) -1)

        if pos_x < 0:
            pos_x = 0
        if pos_x >= cols:
            pos_x = cols - 1
        if  pos_y < 0:
            pos_y = 0
        if pos_y >= rows:
            pos_y = rows - 1

        coordonnees_list = [pos_x, pos_y]
        points_coordonnees_image_list.append(coordonnees_list)

        value_ref = 0.0
        if ATTRIBUTE_Z_INI in attribut_dico.keys() :
            value_ref = float(attribut_dico[ATTRIBUTE_Z_INI])
        if ATTRIBUTE_Z_FIN in attribut_dico.keys() :
            value_ref = float(attribut_dico[ATTRIBUTE_Z_FIN])

        precision_alti = 0.0
        if ATTRIBUTE_PREC_ALTI in attribut_dico.keys() :
            precision_alti = float(attribut_dico[ATTRIBUTE_PREC_ALTI])

        point_attr_dico = {ATTRIBUTE_ID:index_key, ATTRIBUTE_Z_REF:value_ref, ATTRIBUTE_PREC_ALTI:precision_alti, ATTRIBUTE_Z_MNS:0.0, ATTRIBUTE_Z_DELTA:0.0}

        for raster_input in raster_input_dico :
            field_name = raster_input_dico[raster_input][0][0]
            point_attr_dico[field_name] = 0.0

        points_random_value_dico[index_key] = [[coor_x, coor_y], point_attr_dico]

    # ETAPE 5 : LECTURE DES DONNEES DE HAUTEURS ISSU DU MNS et autre raster

    # Lecture dans le fichier raster des valeurs
    values_height_list = getPixelsValueListImage(image_cut, points_coordonnees_image_list)
    values_others_dico = {}
    for raster_input in raster_input_dico :
        raster_cut = raster_cut_dico[raster_input]
        values_list = getPixelsValueListImage(raster_cut, points_coordonnees_image_list)
        values_others_dico[raster_input] = values_list

    for i in range( len(points_random_value_dico)):
        value_mns = values_height_list[i]
        value_ref = points_random_value_dico[i][1][ATTRIBUTE_Z_REF]

        points_random_value_dico[i][1][ATTRIBUTE_Z_MNS] = float(value_mns)
        precision_alti = points_random_value_dico[i][1][ATTRIBUTE_PREC_ALTI]
        points_random_value_dico[i][1][ATTRIBUTE_PREC_ALTI] = float(precision_alti)
        value_diff = value_ref - value_mns
        points_random_value_dico[i][1][ATTRIBUTE_Z_DELTA] = float(value_diff)

        for raster_input in raster_input_dico :
            field_name = raster_input_dico[raster_input][0][0]
            value_other = values_others_dico[raster_input][i]
            points_random_value_dico[i][1][field_name] = float(value_other)


    # ETAPE 6 : CREATION D'UN VECTEUR DE POINTS AVEC DONNEE COORDONNES POINT ET HAUTEUR REFERENCE ET MNS

    # Suppression des points contenant des valeurs en erreur et en dehors du filtrage
    points_random_value_dico_clean = {}
    for i in range( len(points_random_value_dico)):
        value_ref = points_random_value_dico[i][1][ATTRIBUTE_Z_REF]
        if value_ref != ERROR_VALUE and value_ref > ERROR_MIN_VALUE and value_ref < ERROR_MAX_VALUE :

            points_is_valid = True
            for raster_input in raster_input_dico :
                if len(raster_input_dico[raster_input]) > 1 and len(raster_input_dico[raster_input][1]) > 1 :
                    threshold_min = float(raster_input_dico[raster_input][1][0])
                    threshold_max = float(raster_input_dico[raster_input][1][1])
                    field_name = raster_input_dico[raster_input][0][0]
                    value_raster = float(points_random_value_dico[i][1][field_name])
                    if value_raster < threshold_min or value_raster > threshold_max :
                        points_is_valid = False

            if points_is_valid :
                points_random_value_dico_clean[i] = points_random_value_dico[i]

    # Définir les attibuts du fichier résultat
    attribute_dico = {ATTRIBUTE_ID:ogr.OFTInteger, ATTRIBUTE_PREC_ALTI:ogr.OFTReal, ATTRIBUTE_Z_REF:ogr.OFTReal, ATTRIBUTE_Z_MNS:ogr.OFTReal, ATTRIBUTE_Z_DELTA:ogr.OFTReal}

    for raster_input in raster_input_dico :
        field_name = raster_input_dico[raster_input][0][0]
        attribute_dico[field_name] = ogr.OFTReal

    createPointsFromCoordList(attribute_dico, points_random_value_dico_clean, vector_output_temp, epsg, format_vector)

    # Suppression des points en bord de zone d'étude
    bufferVector(vector_study, vector_study_clean, ERODE_EDGE_POINTS, "", 1.0, 10, format_vector)
    cutVectorAll(vector_study_clean, vector_output_temp, vector_output, True, format_vector)

    # ETAPE 7 : TRANSFORMATION DU FICHIER .DBF EN .CSV
    dbf_file = repertory_output + os.sep + base_name + EXT_DBF
    csv_file = repertory_output + os.sep + base_name + EXT_CSV

    if debug >=2:
        print(cyan + "estimateQualityMns() : " + bold + green + "Conversion du fichier DBF %s en fichier CSV %s" %(dbf_file, csv_file) + endC)

    convertDbf2Csv(dbf_file, csv_file)

    # ETAPE 8 : SUPPRESIONS FICHIERS INTERMEDIAIRES INUTILES

    # Suppression des données intermédiaires
    if not save_results_intermediate:
        if cutting_action :
            if os.path.isfile(image_cut) :
                removeFile(image_cut)
        else :
            if os.path.isfile(vector_study) :
                removeVectorFile(vector_study)

        for raster_input in raster_input_dico :
            raster_cut = raster_cut_dico[raster_input]
            if os.path.isfile(raster_cut) :
                removeFile(raster_cut)

        if os.path.isfile(vector_output_temp) :
            removeVectorFile(vector_output_temp)

        if os.path.isfile(vector_study_clean) :
            removeVectorFile(vector_study_clean)

        if os.path.isfile(vector_sample_temp) :
            removeVectorFile(vector_sample_temp)

        if os.path.isfile(vector_sample_temp_clean) :
            removeVectorFile(vector_sample_temp_clean)

        for vector_file in vector_sample_input_cut_list:
            if os.path.isfile(vector_file) :
                removeVectorFile(vector_file)

    print(bold + green + "## END : CREATE HEIGHT POINTS FILE FROM MNSE" + endC)

    # Mise à jour du Log
    ending_event = "estimateQualityMns() : Masks creation ending : "
    timeLine(path_time_log,ending_event)

    return

###########################################################################################################################################
# MISE EN PLACE DU PARSER                                                                                                                 #
###########################################################################################################################################

# Code executé seulement dans le cas ou le script est lancé depuis une ligne de commande
# Il n'est pas executé lors d'un import QualityMnsEstimation.py
# Exemple de lancement en ligne de commande:
# python -m QualityMnsEstimation -i /mnt/RAM_disk/MNS_50cm.tif -v /mnt/Data/10_Agents_travaux_en_cours/Gilles/Test_QualityMNS/emprise.shp -pl /mnt/Geomatique/REF_GEO/BD_Topo/D33/ED16/SHP/1_DONNEES_LIVRAISON/A_VOIES_COMM_ROUTE/N_ROUTE_PRIMAIRE_BDT_033.SHP /mnt/Geomatique/REF_GEO/BD_Topo/D33/ED16/SHP/1_DONNEES_LIVRAISON/A_VOIES_COMM_ROUTE/N_ROUTE_SECONDAIRE_BDT_033.SHP -al /mnt/RAM_disk/Bordeaux_Metropole_Est_NDVI.tif:NDVI:-1.0,0.3 /mnt/RAM_disk/MNT_1m.tif:Z_Mnt -o /mnt/RAM_disk/CUB_zone_test.shp -log /mnt/RAM_disk/fichierTestLog.txt

def main(gui=False):

    # Définition des différents paramètres du parser
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,  prog="QualityMnsEstimation", description="\
    Info : Estimating the quality of mns image by bd réference. \n\
    Objectif : Estimer la qualiter d'une image de MNS en comparaison à des données issue de BD. \n\
    vector_cut_input : si ce parametre est absent alors on decoupe faite sur la base de l'emprise du MNS \n\
    Example : python QualityMnsEstimation.py -i /mnt/Data/gilles.fouvet/QualiteMNS/MNS/CUB_Nord_Est_MNS.tif \n\
                                     -v /mnt/Data/gilles.fouvet/QualiteMNS/Emprise/Emprise_CUB_zone_test_NE.shp \n\
                                     -pl /mnt/Data/gilles.fouvet/QualiteMNS/BD_Topo/ROUTE_PRIMAIRE_033.shp /mnt/Data/gilles.fouvet/QualiteMNS/BD_Topo/ROUTE_SECONDAIRE_033.shp \n\
                                     -al /mnt/Data/gilles.fouvet/QualiteMNS/Resultats/CUB_zone_test_NE_NDVI.tif:NDVI,-1.0,0.3 /mnt/Data/gilles.fouvet/QualiteMNS/Resultats/CUB_zone_test_NE_NDWI2.tif:NDWI2 \n\
                                     -o /mnt/Data/gilles.fouvet/QualiteMNS/Resultats/CUB_zone_test_NE_QualityMNS.shp \n\
                                     -log /mnt/Data/gilles.fouvet/QualiteMNS/fichierTestLog.txt")

    parser.add_argument('-i','--image_input',default="",help="Image MNS input to qualify", type=str, required=True)
    parser.add_argument('-v','--vector_cut_input',default=None,help="Vector input define the sudy area.", type=str, required=False)
    parser.add_argument('-pl','--vector_sample_input_list', nargs="+",default="",help="list of vector input of sample for comparaison.", type=str, required=False)
    parser.add_argument('-p','--vector_sample_points_input',default=None,help="Vector input of sample points (Warning! replace vector_sample_input_list).", type=str, required=False)
    parser.add_argument('-al','--raster_input_dico', nargs="+", default="",help="List of other raster input get value into vector output and colum name, threshold values min max. Exemple ndvi file and ndwi file", type=str, required=False)
    parser.add_argument('-o','--vector_output',default="",help="Vector output contain dots from the random draw into study area.", type=str, required=True)
    parser.add_argument('-ndv','--no_data_value', default=0, help="Option : Value of the pixel no data. By default : 0", type=int, required=False)
    parser.add_argument('-epsg','--epsg', default=2154,help="Projection of the output file.", type=int, required=False)
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

    # Récupération de l'image d'entrée
    if args.image_input != None:
        image_input = args.image_input
        if not os.path.isfile(image_input):
            raise NameError (cyan + "QualityMnsEstimation : " + bold + red  + "File %s not existe!" %(image_input) + endC)

    # Récupération du vecteur de decoupe
    vector_cut_input = None
    if args.vector_cut_input != None :
        vector_cut_input = args.vector_cut_input
        if vector_cut_input != "" and not os.path.isfile(vector_cut_input):
            raise NameError (cyan + "QualityMnsEstimation : " + bold + red  + "File %s not existe!" %(vector_cut_input) + endC)

    # Récupération de la liste des vecteurs d'échantillonage
    if args.vector_sample_input_list != None :
        vector_sample_input_list = args.vector_sample_input_list
        for vector_sample_input in vector_sample_input_list :
            if not os.path.isfile(vector_sample_input):
                raise NameError (cyan + "QualityMnsEstimation : " + bold + red  + "File %s not existe!" %(vector_sample_input) + endC)

    # Récupération du vecteur d'échantillonage points
    vector_sample_points_input = None
    if args.vector_sample_points_input != None :
        vector_sample_points_input = args.vector_sample_points_input
        if vector_sample_points_input != "" and not os.path.isfile(vector_sample_points_input):
            raise NameError (cyan + "QualityMnsEstimation : " + bold + red  + "File %s not existe!" %(vector_sample_points_input) + endC)

    # Récupération des fichiers d'entrése autres et de leur valeur de seuil
    if args.raster_input_dico != None:
        raster_input_dico = extractDico(args.raster_input_dico)
        for raster_input in raster_input_dico :
            if not os.path.isfile(raster_input):
                raise NameError (cyan + "QualityMnsEstimation : " + bold + red  + "File %s not existe!" %(raster_input) + endC)
            field_name = raster_input_dico[raster_input][0][0]
            if field_name == "" or len(field_name) > 10 :
                raise NameError (cyan + "QualityMnsEstimation : " + bold + red  + "Field name %s not valide!" %(field_name) + endC)

    # Récupération du fichier de sortie
    if args.vector_output != None:
        vector_output = args.vector_output

    # Récupération du parametre no_data_value
    if args.no_data_value!= None:
        no_data_value = args.no_data_value

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
        print(bold + green + "QualityMnsEstimation : Variables dans le parser" + endC)
        print(cyan + "QualityMnsEstimation : " + endC + "image_input : " + str(image_input) + endC)
        print(cyan + "QualityMnsEstimation : " + endC + "vector_cut_input : " + str(vector_cut_input) + endC)
        print(cyan + "QualityMnsEstimation : " + endC + "vector_sample_input_list : " + str(vector_sample_input_list) + endC)
        print(cyan + "QualityMnsEstimation : " + endC + "vector_sample_points_input : " + str(vector_sample_points_input) + endC)
        print(cyan + "QualityMnsEstimation : " + endC + "raster_input_dico : " + str(raster_input_dico) + endC)
        print(cyan + "QualityMnsEstimation : " + endC + "vector_output : " + str(vector_output) + endC)
        print(cyan + "QualityMnsEstimation : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "QualityMnsEstimation : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "QualityMnsEstimation : " + endC + "format_raster : " + str(format_raster) + endC)
        print(cyan + "QualityMnsEstimation : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "QualityMnsEstimation : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "QualityMnsEstimation : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "QualityMnsEstimation : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "QualityMnsEstimation : " + endC + "save_results_inter : " + str(save_results_intermediate) + endC)
        print(cyan + "QualityMnsEstimation : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "QualityMnsEstimation : " + endC + "debug : " + str(debug) + endC)

    # EXECUTION DE LA FONCTION
    # Si le dossier de sortie n'existent pas, on le crée
    repertory_output = os.path.dirname(vector_output)
    if not os.path.isdir(repertory_output):
        os.makedirs(repertory_output)

    # execution de la fonction pour une image
    estimateQualityMns(image_input, vector_cut_input, vector_sample_input_list, vector_sample_points_input, raster_input_dico, vector_output, no_data_value, path_time_log, format_raster, epsg, format_vector, extension_raster, extension_vector, save_results_intermediate, overwrite)

# ================================================

if __name__ == '__main__':
  main(gui=False)
