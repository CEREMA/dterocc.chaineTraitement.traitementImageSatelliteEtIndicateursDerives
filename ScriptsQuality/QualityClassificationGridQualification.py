#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# CE SCRIPT PERMET DE FAIRE UNE ESTIMATION DE LA QUALITE D'UNE IMAGE DE CLASSIFICATION PAR GRILLE                                           #
#                                                                                                                                           #
#############################################################################################################################################
"""
Nom de l'objet : QualityClassificationGridQualification.py
Description :
-------------
Objectif : Estimer la qualiter d'une image de classifition par zone d'une grille
Rq : utilisation des OTB Applications : otbcli_BandMath

Date de creation : 04/07/2016
----------
Histoire :
----------
Origine : Nouveau
04/07/2016 : Création
-----------------------------------------------------------------------------------------------------
Modifications

------------------------------------------------------
A Reflechir/A faire
 -
 -
"""

from __future__ import print_function
import os,sys,glob,argparse,string,shutil,copy
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from osgeo import ogr
from Lib_log import timeLine
from Lib_raster import getPixelWidthXYImage, identifyPixelValues, reallocateClassRaster, cutImageByVector, createVectorMask
from Lib_vector import createPolygonsFromGeometryList, createGridVector, updateIndexVector, cutVectorAll, cutVector, cleanMiniAreaPolygons, getGeomPolygons, setAttributeValues, addNewFieldVector, differenceVector, fusionVectors
from QualityIndicatorComputation import computeConfusionMatrix, computeIndicators
from Lib_text import readConfusionMatrix,correctMatrix
from Lib_file import removeVectorFile, copyVectorFile, removeFile

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 1

###########################################################################################################################################
# FONCTION comparareClassificationToReferenceGrid()                                                                                       #
###########################################################################################################################################
def comparareClassificationToReferenceGrid(image_input, vector_cut_input, vector_sample_input, vector_grid_input, vector_grid_output, size_grid, field_value_verif, no_data_value, path_time_log, epsg=2154, format_raster='GTiff', format_vector="ESRI Shapefile", extension_raster=".tif", extension_vector=".shp", save_results_intermediate=False, overwrite=True):
    """
    # ROLE:
    #     Estimer la qualiter d'une image de classifition par zone d'une grille. La grille peut être créer ou donner en fichier d'entrée.
    #     La comparaison se fait avec un fichier shape de référence contant des données de controles (par exemple la bd topo bati de l'IGN).
    #     Le résultat est enregistré dans un ficher grille dans la table attibutaire une valeur de qualité par polygone de la grille.
    #
    # ENTREES DE LA FONCTION :
    #     image_input : l'image d'entrée qui sera découpé
    #     vector_cut_input: le vecteur pour le découpage (zone d'étude)
    #     vector_sample_input : le vecteur d'échantillon de référence
    #     vector_grid_input : le fichier de grille d'entrée vecteur contenant la grille d'étude déja créee
    #     vector_grid_output : le fichier de sortie vecteur contenant les résulats sous forme de grille
    #     size_grid : taille de la grille en mêtre (lignes = colonnes)
    #     field_value_verif : valeur du champs classif à comparer (exemple : 11100 pour le bati)
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
    #    un fichier vecteur grille (polygones) contenant les résulats d'indicateurs de qualité
    #
    """

    # Mise à jour du Log
    starting_event = "comparareClassificationToReferenceGrid() : starting : "
    timeLine(path_time_log,starting_event)

    print(endC)
    print(bold + green + "## START : COMPARE QUALITY FROM CLASSIF IMAGE BY GRID" + endC)
    print(endC)

    if debug >= 2:
        print(bold + green + "comparareClassificationToReferenceGrid() : Variables dans la fonction" + endC)
        print(cyan + "comparareClassificationToReferenceGrid() : " + endC + "image_input : " + str(image_input) + endC)
        print(cyan + "comparareClassificationToReferenceGrid() : " + endC + "vector_cut_input : " + str(vector_cut_input) + endC)
        print(cyan + "comparareClassificationToReferenceGrid() : " + endC + "vector_sample_input : " + str(vector_sample_input) + endC)
        print(cyan + "comparareClassificationToReferenceGrid() : " + endC + "vector_grid_input : " + str(vector_grid_input) + endC)
        print(cyan + "comparareClassificationToReferenceGrid() : " + endC + "vector_grid_output : " + str(vector_grid_output) + endC)
        print(cyan + "comparareClassificationToReferenceGrid() : " + endC + "size_grid : " + str(size_grid) + endC)
        print(cyan + "comparareClassificationToReferenceGrid() : " + endC + "field_value_verif : " + str(field_value_verif))
        print(cyan + "comparareClassificationToReferenceGrid() : " + endC + "no_data_value : " + str(no_data_value))
        print(cyan + "comparareClassificationToReferenceGrid() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "comparareClassificationToReferenceGrid() : " + endC + "epsg  : " + str(epsg) + endC)
        print(cyan + "comparareClassificationToReferenceGrid() : " + endC + "format_raster : " + str(format_raster) + endC)
        print(cyan + "comparareClassificationToReferenceGrid() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "comparareClassificationToReferenceGrid() : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "comparareClassificationToReferenceGrid() : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "comparareClassificationToReferenceGrid() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "comparareClassificationToReferenceGrid() : " + endC + "overwrite : " + str(overwrite) + endC)

    # ETAPE 0 : PREPARATION DES FICHIERS INTERMEDIAIRES'

    CODAGE = "uint16"
    SUFFIX_STUDY = '_study'
    SUFFIX_TEMP = '_temp'
    SUFFIX_FUSION = '_other_fusion'

    NONE_VALUE_QUANTITY = -1.0
    FIELD_VALUE_OTHER = 65535

    FIELD_NAME_ID = "id"
    FIELD_NAME_RATE_BUILD = "rate_build"
    FIELD_NAME_RATE_OTHER = "rate_other"
    FIELD_NAME_SREF_BUILD = "sref_build"
    FIELD_NAME_SCLA_BUILD = "scla_build"
    FIELD_NAME_SREF_OTHER = "sref_other"
    FIELD_NAME_SCLA_OTHER = "scla_other"
    FIELD_NAME_KAPPA = "kappa"
    FIELD_NAME_ACCURACY = "accuracy"

    pixel_size_x, pixel_size_y = getPixelWidthXYImage(image_input)

    repertory_output = os.path.dirname(vector_grid_output)
    base_name = os.path.splitext(os.path.basename(vector_grid_output))[0]

    vector_study = repertory_output + os.sep + base_name + SUFFIX_STUDY + extension_vector
    vector_grid_temp = repertory_output + os.sep + base_name + SUFFIX_TEMP + extension_vector
    image_raster_other_fusion = repertory_output + os.sep + base_name + SUFFIX_FUSION + extension_raster

    # ETAPE 0 : VERIFICATION

    # Verification de la valeur de la nomemclature à verifier
    if field_value_verif >= FIELD_VALUE_OTHER :
        print(cyan + "comparareClassificationToReferenceGrid() : " + bold + red + "Attention de valeur de nomenclature à vérifier  : " + str(field_value_verif) + " doit être inferieur à la valeur de fusion des valeur autre arbitraire de : " + str(FIELD_VALUE_OTHER) + endC, file=sys.stderr)
        sys.exit(1) #exit with an error code

    # ETAPE 1 : DEFINIR UN SHAPE ZONE D'ETUDE

    if (not vector_cut_input is None) and (vector_cut_input != "") and (os.path.isfile(vector_cut_input)) :
        cutting_action = True
        vector_study = vector_cut_input
    else :
        cutting_action = False
        createVectorMask(image_input, vector_study)

    # ETAPE 2 : UNIFORMISATION DE LA ZONE OTHER

    # Réalocation des valeurs de classification pour les valeurs autre que le bati
    change_reaff_value_list = []
    reaff_value_list = identifyPixelValues(image_input)
    if field_value_verif in reaff_value_list :
        reaff_value_list.remove(field_value_verif)
    if no_data_value in reaff_value_list :
        reaff_value_list.remove(no_data_value)
    for elem in reaff_value_list:
        change_reaff_value_list.append(FIELD_VALUE_OTHER)
    reallocateClassRaster(image_input, image_raster_other_fusion, reaff_value_list, change_reaff_value_list)

    # ETAPE 3 : CREATION DE LA GRILLE SUR LA ZONE D'ETUDE

    # Définir les attibuts du fichier
    attribute_dico = {FIELD_NAME_ID:ogr.OFTInteger,FIELD_NAME_RATE_BUILD:ogr.OFTReal,FIELD_NAME_RATE_OTHER:ogr.OFTReal,FIELD_NAME_SREF_BUILD:ogr.OFTReal,FIELD_NAME_SCLA_BUILD:ogr.OFTReal,FIELD_NAME_SREF_OTHER:ogr.OFTReal,FIELD_NAME_SCLA_OTHER:ogr.OFTReal,FIELD_NAME_KAPPA:ogr.OFTReal,FIELD_NAME_ACCURACY:ogr.OFTReal}
    nb_polygon = 0

    if (not vector_grid_input is None) and (vector_grid_input != "") and (os.path.isfile(vector_grid_input)) :
        # Utilisation du fichier grille d'entrée

        # Recopie du fichier grille d'entrée vers le fichier grille de sortie
        copyVectorFile(vector_grid_input, vector_grid_output)

        # Ajout des champs au fichier grille de sortie
        for field_name in attribute_dico :
            addNewFieldVector(vector_grid_output, field_name, attribute_dico[field_name], None, None, None, format_vector)

        # Mettre le champs "id" identifiant du carré de l'élément de la grille
        nb_polygon = updateIndexVector(vector_grid_output, FIELD_NAME_ID, format_vector)

    else :
        # Si il n'existe pas de fichier grille on en créer un avec la valeur de size_grid

        # Creer le fichier grille
        ligne, colonne = createGridVector(vector_study, vector_grid_temp, size_grid, size_grid, attribute_dico, overwrite, epsg, format_vector)
        nb_polygon = (ligne * colonne) + 1

        # Découper la grille avec le shape zone d'étude
        cutVectorAll(vector_study, vector_grid_temp, vector_grid_output, format_vector)

    # ETAPE 4 : CALCUL DE L'INDICATEUR DE QUALITE POUR CHAQUE CASE DE LA GRILLE

    if debug >=2:
        print(bold + "nb_polygon = " + endC + str(nb_polygon) + "\n")

    # Pour chaque polygone existant
    sum_rate_quantity_build = 0
    nb_rate_sum = 0
    size_area_pixel = abs(pixel_size_x * pixel_size_y)

    for id_polygon in range(nb_polygon) :
        geom_list = getGeomPolygons(vector_grid_output, FIELD_NAME_ID, id_polygon, format_vector)
        if geom_list is not None and geom_list != [] : # and (id_polygon == 24 or id_polygon == 30):

            if debug >=1:
                print(cyan + "comparareClassificationToReferenceGrid() : " + bold + green + "Calcul de la matrice pour le polygon n°: " + str(id_polygon) + endC)

            geom = geom_list[0]
            class_ref_list, class_pro_list, rate_quantity_list, kappa, accuracy, matrix  = computeQualityIndiceRateQuantity(image_raster_other_fusion, vector_sample_input, repertory_output, base_name + str(id_polygon), geom, size_grid, pixel_size_x, pixel_size_y, field_value_verif, FIELD_VALUE_OTHER, no_data_value, epsg, format_raster, format_vector, extension_raster, extension_vector, overwrite, save_results_intermediate)

            # Si les calculs indicateurs de qualité sont ok
            if debug >=2:
                print(matrix)
            if matrix != None and matrix != [] and matrix[0] != [] :

                # Récuperer la quantité de bati et calcul de la surface de référence et de la surface de classification (carreau entier ou pas!)
                if len(class_ref_list) == 2 and  len(class_pro_list) == 2 : # Cas ou l'on a des pixels de build et other (en ref et en prod)
                    rate_quantity_build = rate_quantity_list[0]
                    rate_quantity_other = rate_quantity_list[1]
                    size_area_ref_build = (matrix[0][0] + matrix[0][1]) * size_area_pixel
                    size_area_classif_build = (matrix[0][0] + matrix[1][0]) * size_area_pixel
                    size_area_ref_other = (matrix[1][0] + matrix[1][1]) * size_area_pixel
                    size_area_classif_other = (matrix[0][1] + matrix[1][1]) * size_area_pixel
                    sum_rate_quantity_build += rate_quantity_build
                    nb_rate_sum += 1

                else : # Cas ou l'on a uniquement des pixels de build OU uniquement des pixels de other

                    if  class_ref_list[0] == field_value_verif: # Cas ou l'on a uniquement des pixels references build
                        rate_quantity_build = rate_quantity_list[0]
                        rate_quantity_other = NONE_VALUE_QUANTITY
                        size_area_ref_other = 0

                        if len(class_pro_list) == 2 :  # Cas ou l'on a des pixels de prod build et other
                            size_area_ref_build =  (matrix[0][0] + matrix[0][1]) * size_area_pixel
                            size_area_classif_build = matrix[0][0] * size_area_pixel
                            size_area_classif_other = matrix[0][1] * size_area_pixel

                        else :
                            size_area_ref_build = matrix[0][0] * size_area_pixel
                            if class_pro_list[0] == field_value_verif: # Cas ou l'on a uniquement des pixels prod build
                                size_area_classif_build = matrix[0][0] * size_area_pixel
                                size_area_classif_other = 0

                            else : # Cas ou l'on a uniquement des pixels prod other
                                size_area_classif_build = 0
                                size_area_classif_other = matrix[0][0] * size_area_pixel

                    else : # Cas ou l'on a uniquement des pixels references other
                        rate_quantity_build = NONE_VALUE_QUANTITY
                        rate_quantity_other = rate_quantity_list[0]
                        size_area_ref_build = 0

                        if len(class_pro_list) == 2 :  # Cas ou l'on a des pixels de prod build et other
                            size_area_ref_other =  (matrix[0][0] + matrix[0][1]) * size_area_pixel
                            size_area_classif_build = matrix[0][0] * size_area_pixel
                            size_area_classif_other = matrix[0][1] * size_area_pixel

                        else :
                            size_area_ref_other = matrix[0][0] * size_area_pixel
                            if class_pro_list[0] == field_value_verif: # Cas ou l'on a uniquement des pixels prod build
                                size_area_classif_build = matrix[0][0] * size_area_pixel
                                size_area_classif_other = 0

                            else : # Cas ou l'on a uniquement des pixels prod other
                                size_area_classif_build = 0
                                size_area_classif_other = matrix[0][0] * size_area_pixel

                # Mettre à jour ses éléments du carré de la grille
                setAttributeValues(vector_grid_output, FIELD_NAME_ID, id_polygon, {FIELD_NAME_RATE_BUILD:rate_quantity_build,FIELD_NAME_RATE_OTHER:rate_quantity_other,FIELD_NAME_SREF_BUILD:size_area_ref_build,FIELD_NAME_SCLA_BUILD:size_area_classif_build,FIELD_NAME_SREF_OTHER:size_area_ref_other,FIELD_NAME_SCLA_OTHER:size_area_classif_other,FIELD_NAME_KAPPA:kappa,FIELD_NAME_ACCURACY:accuracy}, format_vector)

    # Calcul de la moyenne
    if nb_rate_sum != 0:
        average_quantity_build = sum_rate_quantity_build / nb_rate_sum
    else :
        average_quantity_build = 0
    if debug >=2:
        print(bold + "nb_polygon_used = " + endC + str(nb_rate_sum))
        print(bold + "average_quantity_build = " + endC + str(average_quantity_build) + "\n")

    # ETAPE 5 : SUPPRESIONS FICHIERS INTERMEDIAIRES INUTILES

    # Suppression des données intermédiairess
    if not save_results_intermediate:

        if not cutting_action :
            if os.path.isfile(vector_study) :
                removeVectorFile(vector_study)

        if os.path.isfile(image_raster_other_fusion) :
            removeFile(image_raster_other_fusion)

        if os.path.isfile(vector_grid_temp) :
            removeVectorFile(vector_grid_temp)

    print(endC)
    print(bold + green + "## END : COMPARE QUALITY FROM CLASSIF IMAGE BY GRID" + endC)
    print(endC)

    # Mise à jour du Log
    ending_event = "comparareClassificationToReferenceGrid() :  ending : "
    timeLine(path_time_log,ending_event)

    return average_quantity_build

###########################################################################################################################################
# FONCTION computeQualityIndiceRateQuantity()                                                                                             #
###########################################################################################################################################
def computeQualityIndiceRateQuantity(raster_input, vector_sample_input, repertory_output, base_name, geom, size_grid, pixel_size_x, pixel_size_y, field_value_verif, field_value_other, no_data_value, epsg, format_raster, format_vector, extension_raster, extension_vector, overwrite=True, save_results_intermediate=False) :
    """
    # ROLE:
    #     Calcul la matrice de confusion et les indicateurs de qualitées pour un carreau de la grille
    #
    # ENTREES DE LA FONCTION :
    #     raster_input : l'image d'entrée qui sera verifié
    #     vector_sample_input : le vecteur d'échantillon de référence
    #     vector_grid_input : le fichier de grille d'entrée vecteur contenant la grille d'étude déja créee
    #     repertory_output : répertoire de sortie pour ecrire les fichier temporaire
    #     base_name : le nom de base pour l'ecriture des fichiers temporaires
    #     geom : la géometrie du carreau à étudier
    #     size_grid : taille de la grille en mêtre (lignes = colonnes)
    #     pixel_size_x : taille d'un pixel en X du raster d'entrée
    #     pixel_size_y : taille d'un pixel en Y du raster d'entrée
    #     field_value_verif : valeur du champs classif à comparer (exemple : 11100 pour le bati)
    #     no_data_value : Valeur de  pixel du no data
    #     epsg : Optionnel : par défaut 2154
    #     format_raster :  format des images raster, const : "GTiff"
    #     format_vector  : format du vecteur de sortie, par defaut = 'ESRI Shapefile'
    #     extension_raster : extension des fichiers rasteur , const : '.tif'
    #     extension_vector : extension des fichiers vecteur, const : '.shp'
    #     overwrite : écrase si un fichier existant a le même nom qu'un fichier de sortie, par defaut a True
    #     save_results_intermediate : fichiers de sorties intermediaires nettoyees, par defaut = False
    #
    # SORTIES DE LA FONCTION :
    #      class_ref_list : la liste des valeur de nomenclature des elements de réfrence
    #      class_pro_list : la liste des valeur de nomenclature des elements de produit
    #      rate_quantity_list : la liste des valeurs de taux pour la valeur etudiées et pour le reste
    #      kappa : la valeur de l'indicateur kappa pour carreau étudié
    #      overall_accuracy : la valeur de l'indicateur overall_accuracy pour carreau étudié
    #      matrix : la matrice de confusion pour carreau étudié
    """

    # Définition des constantes
    EXT_TXT = '.txt'
    SUFFIX_STUDY = '_study'
    SUFFIX_CUT = '_cut'
    SUFFIX_BUILD = '_build'
    SUFFIX_OTHER = '_other'
    SUFFIX_LOCAL = '_local'
    SUFFIX_MATRIX = '_matrix'

    FIELD_NAME_CLASSIF = "classif"
    FIELD_TYPE = ogr.OFTInteger

    # Les variables locales
    vector_local_study = repertory_output + os.sep + base_name + SUFFIX_LOCAL + SUFFIX_STUDY + extension_vector
    vector_local_cut_study = repertory_output + os.sep + base_name + SUFFIX_LOCAL + SUFFIX_CUT + SUFFIX_STUDY + extension_vector
    vector_local_cut_build = repertory_output + os.sep + base_name + SUFFIX_LOCAL + SUFFIX_CUT + SUFFIX_BUILD + extension_vector
    vector_local_cut_other = repertory_output + os.sep + base_name + SUFFIX_LOCAL + SUFFIX_CUT + SUFFIX_OTHER + extension_vector
    vector_local_cut = repertory_output + os.sep + base_name + SUFFIX_LOCAL + SUFFIX_CUT + extension_vector
    raster_local_cut = repertory_output + os.sep + base_name + SUFFIX_LOCAL + SUFFIX_CUT + extension_raster
    matrix_local_file = repertory_output + os.sep + base_name + SUFFIX_LOCAL + SUFFIX_CUT + SUFFIX_MATRIX + EXT_TXT

    class_ref_list = None
    class_pro_list = None
    rate_quantity_list = None
    matrix_origine = None
    kappa = 0.0
    overall_accuracy = 0.0

    # Netoyage les fichiers de travail local
    if os.path.isfile(vector_local_study) :
        removeVectorFile(vector_local_study)
    if os.path.isfile(vector_local_cut_study) :
        removeVectorFile(vector_local_cut_study)
    if os.path.isfile(vector_local_cut) :
        removeVectorFile(vector_local_cut)
    if os.path.isfile(vector_local_cut_build) :
        removeVectorFile(vector_local_cut_build)
    if os.path.isfile(vector_local_cut_other) :
        removeVectorFile(vector_local_cut_other)
    if os.path.isfile(raster_local_cut) :
        removeFile(raster_local_cut)
    if os.path.isfile(matrix_local_file) :
        removeFile(matrix_local_file)

    # Creation d'un shape file de travail local
    polygon_attr_geom_dico = {"1":[geom, {}]}
    createPolygonsFromGeometryList({}, polygon_attr_geom_dico, vector_local_study, epsg, format_vector)

    # Découpe sur zone local d'étude du fichier vecteur de référence
    cutVector(vector_local_study, vector_sample_input, vector_local_cut_build, format_vector)
    differenceVector(vector_local_cut_build, vector_local_study, vector_local_cut_other, format_vector)

    addNewFieldVector(vector_local_cut_build, FIELD_NAME_CLASSIF, FIELD_TYPE, field_value_verif, None, None, format_vector)
    addNewFieldVector(vector_local_cut_other, FIELD_NAME_CLASSIF, FIELD_TYPE, field_value_other, None, None, format_vector)
    input_shape_list = [vector_local_cut_build, vector_local_cut_other]
    fusionVectors (input_shape_list, vector_local_cut)

    # Découpe sur zone local d'étude du fichier rasteur de classification
    if not cutImageByVector(vector_local_study, raster_input, raster_local_cut, pixel_size_x, pixel_size_y, False, no_data_value, 0, format_raster, format_vector) :
        return class_ref_list, class_pro_list, rate_quantity_list, kappa, overall_accuracy, matrix_origine

    # Calcul de la matrice de confusion
    computeConfusionMatrix(raster_local_cut, vector_local_cut, "", FIELD_NAME_CLASSIF, matrix_local_file, overwrite)

    # lecture de la matrice de confusion
    matrix,class_ref_list,class_pro_list = readConfusionMatrix(matrix_local_file)
    matrix_origine = copy.deepcopy(matrix)

    if matrix == []:
        print(cyan + "computeQualityIndiceRateQuantity() : " + bold + yellow + "!!! Une erreur c'est produite au cours de la lecture de la matrice de confusion : " + matrix_local_file + ". Voir message d'erreur." + endC)
        matrix_origine = None
        return class_ref_list, class_pro_list, rate_quantity_list, kappa, overall_accuracy, matrix_origine


    # Correction de la matrice de confusion
    # Dans le cas ou le nombre de microclasses des échantillons de controles
    # et le nombre de microclasses de la classification sont différents
    class_missing_list = []
    if class_ref_list != class_pro_list:
        matrix, class_missing_list = correctMatrix(class_ref_list, class_pro_list, matrix, no_data_value)

    class_count = len(matrix[0])- len(class_missing_list)

    # Calcul des indicateurs de qualité : rate_quantity_list
    precision_list, recall_list, fscore_list, performance_list, rate_false_positive_list, rate_false_negative_list, rate_quantity_list, class_list, overall_accuracy, overall_fscore, overall_performance, kappa = computeIndicators(class_count, matrix, class_ref_list, class_missing_list)

    # Chercher si une ligne no data existe si c'est le cas correction de la matrice
    if str(no_data_value) in class_pro_list :
        pos_col_nodata = class_pro_list.index(str(no_data_value))
        for line in matrix_origine:
            del line[pos_col_nodata]

        class_pro_list.remove(str(no_data_value))

    # Suppression des données temporaires locales
    if not save_results_intermediate:
        if os.path.isfile(vector_local_study) :
            removeVectorFile(vector_local_study)

        if os.path.isfile(vector_local_cut_study) :
            removeVectorFile(vector_local_cut_study)

        if os.path.isfile(vector_local_cut) :
            removeVectorFile(vector_local_cut)

        if os.path.isfile(vector_local_cut_build) :
            removeVectorFile(vector_local_cut_build)

        if os.path.isfile(vector_local_cut_other) :
            removeVectorFile(vector_local_cut_other)

        if os.path.isfile(raster_local_cut) :
            removeFile(raster_local_cut)

        if os.path.isfile(matrix_local_file) :
            removeFile(matrix_local_file)

    return class_ref_list, class_pro_list, rate_quantity_list, kappa, overall_accuracy, matrix_origine

###########################################################################################################################################
# MISE EN PLACE DU PARSER                                                                                                                 #
###########################################################################################################################################

# Code executé seulement dans le cas ou le script est lancé depuis une ligne de commande
# Il n'est pas executé lors d'un import QualityClassificationGridQualification.py
# Exemple de lancement en ligne de commande:
# python QualityClassificationGridQualification.py -i /mnt/Data/gilles.fouvet/Saturn/QualiteClassification/02_Classifications/CUB_Classification_2014.tif -v /mnt/Data/gilles.fouvet/Saturn/QualiteClassification/02_Classifications/CUB_Contour_bord_net_cut.shp -p /mnt/Data/gilles.fouvet/Saturn/QualiteClassification/04_BD_Topo_Bati/CUB_BDtopo_bati.shp -o /mnt/Data/gilles.fouvet/Saturn/QualiteClassification/05_Resultats/CUB_quality_control_grid.shp -sg 1000 -log /mnt/Data/gilles.fouvet/Saturn/QualiteClassification/fichierTestLog.txt
# python QualityClassificationGridQualification.py -i /mnt/Data/gilles.fouvet/Saturn/QualiteClassification/02_Classifications/CUB_Classification_2014.tif -v /mnt/Data/gilles.fouvet/Saturn/QualiteClassification/02_Classifications/CUB_Contour_bord_net_cut.shp -p /mnt/Data/gilles.fouvet/Saturn/QualiteClassification/04_BD_Topo_Bati/CUB_BDtopo_bati.shp -g /mnt/Data/gilles.fouvet/Saturn/QualiteClassification/05_Resultats/CUB_quality_grid_ref.shp -o /mnt/Data/gilles.fouvet/Saturn/QualiteClassification/05_Resultats/CUB_quality_control_grid2.shp -log /mnt/Data/gilles.fouvet/Saturn/QualiteClassification/fichierTestLog2.txt

def main(gui=False):

    # Définition des différents paramètres du parser
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,  prog="QualityClassificationGridQualification", description="\
    Info : Estimating the quality of image classification. \n\
    Objectif : Estimer la qualiter d'une image de classifition. \n\
    Example : python QualityClassificationGridQualification.py -i /mnt/Data/gilles.fouvet/Saturn/QualiteClassification/02_Classifications/CUB_Classification_2014.tif \n\
                                     -v /mnt/Data/gilles.fouvet/Saturn/QualiteClassification/02_Classifications/CUB_Contour_bord_net_cut.shp \n\
                                     -p /mnt/Data/gilles.fouvet/Saturn/QualiteClassification/04_BD_Topo_Bati/CUB_BDtopo_bati.shp \n\
                                     -o /mnt/Data/gilles.fouvet/Saturn/QualiteClassification/05_Resultats/CUB_quality_control_grid.shp \n\
                                     -sg 1000 \n\
                                     -log /mnt/Data/gilles.fouvet/Saturn/QualiteClassification/fichierTestLog.txt")

    parser.add_argument('-i','--image_input',default="",help="Image input to qualify", type=str, required=True)
    parser.add_argument('-v','--vector_cut_input',default=None,help="Vector input define the sudy area.", type=str, required=False)
    parser.add_argument('-p','--vector_sample_input',default="",help="Vector input of sample for comparaison.", type=str, required=True)
    parser.add_argument('-g','--vector_grid_input',default=None,help="Vector input of grid created alrread.", type=str, required=False)
    parser.add_argument('-o','--vector_grid_output',default="",help="Vector output contain result of study on area grid.", type=str, required=True)
    parser.add_argument('-sg','--size_grid',default=1000,help="Size of study grid in meters. Not used, if vector_grid_input is inquired", type=int, required=False)
    parser.add_argument('-fvv','--field_value_verif',default=11100,help="The value of field classification exemple for build defaut value 11100: ", type=int, required=False)
    parser.add_argument('-ndv','--no_data_value', default=0, help="Option : Value of the pixel no data. By default : 0", type=int, required=False)
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
            raise NameError (cyan + "QualityClassificationGridQualification : " + bold + red  + "File %s not existe!" %(image_input) + endC)

    # Récupération du vecteur de decoupe
    vector_cut_input = None
    if args.vector_cut_input != None :
        vector_cut_input = args.vector_cut_input
        if vector_cut_input != "" and not os.path.isfile(vector_cut_input):
            raise NameError (cyan + "QualityClassificationGridQualification : " + bold + red  + "File %s not existe!" %(vector_cut_input) + endC)

    # Récupération du vecteur d'échantillonage
    vector_sample_input = None
    if args.vector_sample_input != None :
        vector_sample_input = args.vector_sample_input
        if not os.path.isfile(vector_sample_input):
            raise NameError (cyan + "QualityClassificationGridQualification : " + bold + red  + "File %s not existe!" %(vector_sample_input) + endC)

    # Récupération du fichier grille d'entrée
    vector_grid_input = None
    if args.vector_grid_input != None:
        vector_grid_input = args.vector_grid_input

    # Récupération du fichier de sortie
    if args.vector_grid_output != None:
        vector_grid_output = args.vector_grid_output

    # Récupération du parametre taille de la grille
    if args.size_grid != None:
        size_grid = args.size_grid

    # Récupération du parametre field_value_verif
    if args.field_value_verif!= None:
        field_value_verif = args.field_value_verif

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
        print(bold + green + "QualityClassificationGridQualification : Variables dans le parser" + endC)
        print(cyan + "QualityClassificationGridQualification : " + endC + "image_input : " + str(image_input) + endC)
        print(cyan + "QualityClassificationGridQualification : " + endC + "vector_cut_input : " + str(vector_cut_input) + endC)
        print(cyan + "QualityClassificationGridQualification : " + endC + "vector_sample_input : " + str(vector_sample_input) + endC)
        print(cyan + "QualityClassificationGridQualification : " + endC + "vector_grid_input : " + str(vector_grid_input) + endC)
        print(cyan + "QualityClassificationGridQualification : " + endC + "vector_grid_output : " + str(vector_grid_output) + endC)
        print(cyan + "QualityClassificationGridQualification : " + endC + "size_grid : " + str(size_grid) + endC)
        print(cyan + "QualityClassificationGridQualification : " + endC + "field_value_verif : " + str(field_value_verif) + endC)
        print(cyan + "QualityClassificationGridQualification : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "QualityClassificationGridQualification : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "QualityClassificationGridQualification : " + endC + "format_raster : " + str(format_raster) + endC)
        print(cyan + "QualityClassificationGridQualification : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "QualityClassificationGridQualification : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "QualityClassificationGridQualification : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "QualityClassificationGridQualification : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "QualityClassificationGridQualification : " + endC + "save_results_inter : " + str(save_results_intermediate) + endC)
        print(cyan + "QualityClassificationGridQualification : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "QualityClassificationGridQualification : " + endC + "debug : " + str(debug) + endC)

    # EXECUTION DE LA FONCTION
    # Si le dossier de sortie n'existent pas, on le crée
    repertory_output = os.path.dirname(vector_grid_output)
    if not os.path.isdir(repertory_output):
        os.makedirs(repertory_output)

    # execution de la fonction pour une image
    average_quantity_build = comparareClassificationToReferenceGrid(image_input, vector_cut_input, vector_sample_input, vector_grid_input, vector_grid_output, size_grid, field_value_verif, no_data_value, path_time_log, epsg, format_raster, format_vector, extension_raster, extension_vector, save_results_intermediate, overwrite)

# ================================================

if __name__ == '__main__':
  main(gui=False)
