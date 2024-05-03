#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT QUI CALCUL LES INDICATEURS DE QUALITE PAR MATRICE DE CONFUSION                                                                     #
#                                                                                                                                           #
#############################################################################################################################################
"""
Nom de l'objet : QualityIndicatorComputation.py
Description :
-------------
Objectif : generer une matrice de confusion et analyser la matrice
Rq : utilisation des OTB Applications :   otbcli_ComputeConfusionMatrix
Documentation sur le kappa : http://theses.ulaval.ca/archimede/fichiers/23448/ape.html
Documentation sur les indicateurs de qualité issus d'une matrice de confusion :
http://en.wikipedia.org/wiki/Confusion_matrix
http://www2.cs.uregina.ca/~dbd/cs831/notes/confusion_matrix/confusion_matrix.html

Date de creation : 31/07/2014
----------
Histoire :
----------
Origine : le script originel provient du fichier Chain9_Confusion_Matrix_Computation.py cree en 2013 et utilise par la chaine de traitement OCSOL V1.X
31/07/2013 : Transformation en brique elementaire (suppression des liens avec la chaine OCSOL)
-----------------------------------------------------------------------------------------------------
Modifications
31/07/2013 : choix > supprimer pathTimelog > remplacer verifActivation par overwrite et mettre a True par defaut
04/08/2014 : amelioration de la gestion des listes dans args
01/10/2014 : refonte du fichier harmonisation des régles de qualitées des niveaux de boucles et des paramétres dans args
21/05/2015 : simplification des parametres en argument plus de liste d'image en emtrée à traiter uniquement une image
------------------------------------------------------
A Reflechir/A faire :
traduire le docstring en anglais
generer un graphique a partir de la matrice obtenue? --> implementer plotResults,plotResultsMulti ? (historiquement importe de Chain_Auxiliaries.py) et ajouter class_list (liste des classes) en paramètres
"""

from __future__ import print_function
import os,sys,glob,string,argparse,getopt
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_text import appendTextFile, readConfusionMatrix, correctMatrix
from Lib_math import findPositionList, findMaxPosition
from Lib_log import timeLine
from Lib_file import removeFile

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 3

###########################################################################################################################################
# FONCTION computeQualityIndicator()                                                                                                      #
###########################################################################################################################################
def computeQualityIndicator(classif_image_file, validation_input_vector, validation_input_raster, matrix_output_file, indicators_output_file, validation_id_field, textures_list, no_data_value, path_time_log, overwrite=True):
    """
    # ROLE:
    #     Generer une matrice de confusion avec l'application otb otbcli_ComputeConfusionMatrix
    #   et analyser cette matrice pour en sortir les indicateurs de qualité
    #
    # ENTREES DE LA FONCTION :
    #     classif_image_file : image classée en plusieurs classes au format.tif
    #     validation_input_vector : echantillons de validation au format.shp
    #     validation_input_raster : echantillons de validation au format.tif
    #     validation_id_field : nom du champ id class (exmple "id")
    #     matrix_output_file : fichier de sortie contenant la matrice de confusuion
    #     indicators_output_file : fichier de sortie contenant les indicateurs de qualité
    #     textures_list : info texture a ecrire en titre des indicateurs de qualités dans le fichier résultat
    #     no_data_value : Valeur de  pixel du no data
    #     path_time_log : le fichier de log de sortie
    #     overwrite : supprime ou non les fichiers existants ayant le meme nom
    #
    # SORTIES DE LA FONCTION :
    #    auccun
    #    Elements utilises par la fonction :
    #        - image classee et idealement avec microclasses fusionnees en macroclasses et sur lequel un filtre majoritaire a aussi ete applique (exmple : "nomImage_merged_filtered.tif"),
    #        - echantillons de validation (exple : "nomImage_validation.shp")
    #    Eléments générés par la fonction : fichiers textes contenant les résultats de la matrice de confusion (exmple : "nomImage_confusion_matrix.txt")
    #
    """

    # Mise à jour du Log
    starting_event = "computeQualityIndicator() : Compute quality indicator starting : "
    timeLine(path_time_log,starting_event)

    print(endC)
    print(bold + green + "## START :CONFUSION MATRIX COMPUTATION" + endC)
    print(endC)

    # Affichage des parametres
    if debug >= 3:
        print(cyan + "computeQualityIndicator() : " + endC + "classif_image_file: ",classif_image_file)
        print(cyan + "computeQualityIndicator() : " + endC + "validation_input_vector: ",validation_input_vector)
        print(cyan + "computeQualityIndicator() : " + endC + "validation_input_raster: ",validation_input_raster)
        print(cyan + "computeQualityIndicator() : " + endC + "matrix_output_file: ",matrix_output_file)
        print(cyan + "computeQualityIndicator() : " + endC + "indicators_output_file: ",indicators_output_file)
        print(cyan + "computeQualityIndicator() : " + endC + "validation_id_field: ",validation_id_field)
        print(cyan + "computeQualityIndicator() : " + endC + "textures_list: ",textures_list)
        print(cyan + "computeQualityIndicator() : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "computeQualityIndicator() : " + endC + "path_time_log: ",path_time_log)
        print(cyan + "computeQualityIndicator() : " + endC + "overwrite: ",overwrite)

    # CALCUL DE LA MATRICE DE CONFUSION
    computeConfusionMatrix(classif_image_file, validation_input_vector, validation_input_raster, validation_id_field, matrix_output_file, no_data_value, overwrite)

    # LECTURE DE LA MATRICE DE CONFUSION
    matrix,class_ref_list,class_pro_list = readConfusionMatrix(matrix_output_file)

    # CORRECTION MATRICE
    # Correction de la matrice de confusion
    # Dans le cas ou le nombre de microclasses des échantillons de controles
    # et le nombre de microclasses de la classification sont différents
    class_missing_list = []
    if class_ref_list != class_pro_list:
        print(cyan + "computeQualityIndicator() : " + bold + yellow + "Classes are different between classification and shapefile!"  + '\n' + endC)
        print(cyan + "computeQualityIndicator() : " + bold + yellow + "Missing micro classes are set to 0"  + '\n' + endC)
        matrix, class_missing_list = correctMatrix(class_ref_list, class_pro_list, matrix)
        print(cyan + "computeQualityIndicator() : " + bold + yellow + "class_missing_list"  + '\n' + endC + str(class_missing_list))

    class_count = len(matrix[0])- len(class_missing_list)

    # CALCUL DES INDICATEURS DE QUALITE : PRECISION, OVERALL_ACCURACY,RAPPEL, KAPPA, F1-SCORE, PERFORMANCE
    precision_list, recall_list, fscore_list, performance_list, rate_false_positive_list, rate_false_negative_list, quantity_rate_list, class_list, overall_accuracy, overall_fscore, overall_performance, kappa = computeIndicators(class_count, matrix, class_ref_list, class_missing_list)

    # Affichage des scores
    if debug >= 2:
        print(cyan + "computeQualityIndicator() : " + endC + "class_count: ",class_count)
        print(cyan + "computeQualityIndicator() : " + endC + "Precision: ",precision_list)
        print(cyan + "computeQualityIndicator() : " + endC + "Rappel: ",recall_list)
        print(cyan + "computeQualityIndicator() : " + endC + "F1-Scores: ",fscore_list)
        print(cyan + "computeQualityIndicator() : " + endC + "Performance: ",performance_list)
        print(cyan + "computeQualityIndicator() : " + endC + "Rate false positive: ",rate_false_positive_list)
        print(cyan + "computeQualityIndicator() : " + endC + "Rate false negative: ",rate_false_negative_list)
        print(cyan + "computeQualityIndicator() : " + endC + "Rate quantity: ",quantity_rate_list)
        print(cyan + "computeQualityIndicator() : " + endC + "class_list: ",class_list)
        print(cyan + "computeQualityIndicator() : " + endC + "Overall F1-Score: ",overall_fscore)
        print(cyan + "computeQualityIndicator() : " + endC + "Overall accuracy: ",overall_accuracy)
        print(cyan + "computeQualityIndicator() : " + endC + "Overall performance: ",overall_performance)
        print(cyan + "computeQualityIndicator() : " + endC + "Kappa: ",kappa)
        print(cyan + "computeQualityIndicator() : " + endC + "Indicators_output_file: ",indicators_output_file)
        print('\n')

    # Ecriture des résultats des indices qualités dans un fichier ".csv"
    writeQualityIndicatorsToCsvFile(class_count, precision_list, recall_list, fscore_list, performance_list, rate_false_positive_list, rate_false_negative_list, quantity_rate_list, class_list, overall_accuracy, overall_fscore, overall_performance, kappa, indicators_output_file, overwrite, textures_list)

    print(cyan + "computeQualityIndicator() : " + bold + green + "Compute quality indicator ending ")

    print(endC)
    print(bold + green + "## END :  CONFUSION MATRIX COMPUTATION" + endC)
    print(endC)

    # Mise à jour du Log
    ending_event = "computeQualityIndicator() : Masks creation ending : "
    timeLine(path_time_log,ending_event)

    return

###########################################################################################################################################
# FONCTION computeConfusionMatrix()                                                                                                       #
###########################################################################################################################################
def computeConfusionMatrix(classif_image_file, validation_input_vector, validation_input_raster, validation_id_field, output, no_data_value, overwrite) :
    """
    # ROLE:
    #   Calcul la matrice de confusion avec l'application otb otbcli_ComputeConfusionMatrix
    #
    # ENTREES DE LA FONCTION :
    #     classif_image_file : image classée en plusieurs classes au format.tif
    #     validation_input_vector : echantillons de validation au format.shp
    #     validation_input_raster : echantillons de validation au format.tif
    #     validation_id_field : nom du champ id class (exmple "id")
    #     output : fichier de sortie contenant la matrice de confusuion
    #     no_data_value : Valeur de  pixel du no data
    #     overwrite : supprime ou non les fichiers existants ayant le meme nom
    #
    # SORTIES DE LA FONCTION :
    #    auccun
    #
    """

    # calcul de la matrice de confusion
    check = os.path.isfile(output)
    if check and not overwrite :
        print(cyan + "computeConfusionMatrix() : " + bold + yellow + "Confusion matrix already exists." + '\n' + endC)
    else:
        # Tente de supprimer le fichier
        try:
            removeFile(output)
        except Exception:
            # Ignore l'exception levee si le fichier n'existe pas (et ne peut donc pas être supprime)
            pass
        if debug >= 2 :
            print(cyan + "computeConfusionMatrix() : " + bold + green + "Assessing quality..." + '\n' + endC)

        # Test si on entre avec des echantillons de controles au format vecteur ou au format raster
        if validation_input_vector != None:
            # Cas d'echantillons vecteur
            command = "otbcli_ComputeConfusionMatrix -in %s -ref vector -ref.vector.in %s -ref.vector.field %s -nodatalabel %s -ref.vector.nodata %s -out %s" %(classif_image_file, validation_input_vector, validation_id_field, str(no_data_value),  str(no_data_value), output)
        else :
            # Cas d'echantillons raster
            command = "otbcli_ComputeConfusionMatrix -in %s -ref raster -ref.raster.in %s -nodatalabel %s -ref.raster.nodata %s -out %s" %(classif_image_file, validation_input_raster, str(no_data_value), str(no_data_value), output)
        if debug >= 3 :
            print(command)
        exitCode = os.system(command)
        if exitCode != 0:
            raise NameError(cyan + "computeConfusionMatrix() : " + bold + red + "An error occured during otbcli_ComputeConfusionMatrix command. See error message above." + endC)
        if debug >= 2 :
            print(cyan + "computeConfusionMatrix() : " + bold + green + "Confusion matrix created" + '\n' + endC)
    return

###########################################################################################################################################
# FONCTION ComputeIndicators()                                                                                                            #
###########################################################################################################################################
def computeIndicators (class_count, matrix, class_ref_list, class_missing_list) :
    """
    # ROLE:
    #    Calcul les indicateurs de qualité :
    #     - rappel
    #     - overall_rappel
    #     - précision
    #     - overall_fscore
    #     - precision globale
    #     - kappa
    #
    # ENTREES DE LA FONCTION :
    #     class_ref_list : liste des classes des échantillons de vérification
    #     class_missing_list : liste des classes qui sont dans les échantillons de vérifications mais pas dans la sortie de classification
    """
    if debug >=2:
        print(cyan + "computeIndicators() : " + bold + green + "Quality indicator computing..." + '\n' + endC)


    # Traitements préliminaire
    # Gestion de la disparition éventuelle de classes lors de la classification
    class_list = []  # Liste des classes qui sont dans la classification et dans les échantillons de vérification
    for i in range(len(class_ref_list)):
        if findPositionList(class_missing_list, class_ref_list[i]) == -1:
            ref_class = class_ref_list[i].strip()
            class_list.append(int(ref_class))

    if debug >= 3 :
        print(cyan + "computeIndicators : " + bold + green + "class_ref_list: " + str(class_ref_list) + endC)
        print(cyan + "computeIndicators : " + bold + green + "class_count: " + str(class_count) + endC)
        print(cyan + "computeIndicators : " + bold + green + "class_missing_list: " + str(class_missing_list) + endC)
        print(cyan + "computeIndicators : " + bold + green + "class_list: " + str(class_list) + endC)


    # Initialisation des variables pour le kappa, l'overall_accuracy et le fscore
    #----------------------------------------------------------------------------
    sum_from_ref = 0                       # Nombre total de pixels utilisés pour l'estimation de la qualité - Correspond à la somme de toutes les valeurs de la matrice de confusion (somme des totaux des colonnes - Produced)
    sum_from_prod = 0                      # Nombre total de pixels utilisés pour l'estimation de la qualité - Correspond à la somme de toutes les valeurs de la matrice de confusion (somme des totaux des lignes - References)
    sum_diag = 0                           # Nombre total de pixels bien classés parmis les échantillons de vérification - Correspond à la sommes de toutes les valeurs sur la diagonale de la matrice de confusion
    sum_marginal_tot = 0                   # Somme des totaux marginaux, définis comme la somme sur toutes les classes des produits des totaux des lignes avec les totaux des colonnes
    total_produced_pixels_count_list = []  # Liste contenant pour chaque classe le nombre de pixels issus de la classification  - Somme des colonnes (autrement dit : pour chaque colonne, somme de l'ensemble de ses lignes)
    total_reference_pixels_count_list = [] # Liste contenant pour chaque classe le nombre de pixels issus des échantillons de controle  - Somme des lignes (autrement dit : pour chaque ligne, somme de l'ensemble de ses colonnes)
    recall_list = []                       # Liste contenant le rappel de chacune des classes
    precision_list = []                    # Liste contenant la précision de chacune des classes
    fscore_list = []                       # Liste contenant le fscore de chacune des classes

    # Construction de total_produced_pixels_count_list
    for col_index in range(len(matrix[0])):
        total_for_column = 0                                                  # Initialisation de la somme de la colonne à zéro
        for lin_index in range(len(matrix)):
            total_for_column += matrix[lin_index][col_index]
        total_produced_pixels_count_list.append(total_for_column)


    # Construction de total_reference_pixels_count_list
    for lin_index in range(len(matrix)):
        total_for_line = 0                                                    # Initialisation de la somme de la ligne à zéro
        for col_index in range(len(matrix)):
            total_for_line += matrix[lin_index][col_index]
        total_reference_pixels_count_list.append(total_for_line)


    if debug >= 3 :
        print(cyan + "computeIndicators : " + bold + green + "total_produced_pixels_count_list: " + str(total_produced_pixels_count_list) + endC)
        print(cyan + "computeIndicators : " + bold + green + "total_reference_pixels_count_list: " + str(total_reference_pixels_count_list) + endC)

    # Calcul du nombre total de pixels - De deux manières différentes
    for val in total_reference_pixels_count_list:
        sum_from_ref += val

    for val in total_produced_pixels_count_list:
        sum_from_prod += val

    if debug >= 3 :
        print(cyan + "computeIndicators : " + bold + green + "sum_from_ref: " + str(sum_from_ref) + endC)
        print(cyan + "computeIndicators : " + bold + green + "sum_from_prod: " + str(sum_from_prod) + endC)


    if sum_from_ref == sum_from_prod:
        all_pixel_count = sum_from_ref
    else :
        raise NameError(cyan + "computeIndicators() : " + bold + red + "Problem with confusion matrix " + endC)

    # Calcul du nombre de pixels bien classés au regard des échantillons de vérification
    for i in range(len(matrix[0])):
        sum_diag += matrix[i][i]

    # Calcul des totaux marginaux de la matrice de confusion
    for i in range(len(matrix[0])):
        sum_marginal_tot += total_produced_pixels_count_list[i] * total_reference_pixels_count_list[i]

    # Calcul du rappel
    #-----------------
    # Définition : rappel d'une classe = nb pixels bien classés de la classe/nombre de pixels de vérification de la classe
    # Attention : les microclasses disparues dans la classification ont un rappel de 0
    for col_index in range(len(matrix[0])):
        if total_reference_pixels_count_list[col_index] != 0:
            recall_list.append(matrix[col_index][col_index]/total_reference_pixels_count_list[col_index])
        else :
            recall_list.append(0)

    # Calcul du overall_rappel
    #-------------------------
    # Définition : overall_rappel = moyenne pondérée des différentes valeurs de rappel
    overall_rappel = 0
    for index in range(len(recall_list)):
        overall_rappel += recall_list[index] * total_reference_pixels_count_list[index]
    if all_pixel_count > 0:
        overall_rappel = overall_rappel / all_pixel_count
    else :
        overall_rappel = 0

    # Calcul de la précision
    #-----------------------
    # Définition : précision d'une classe = nb pixels bien classés de la classe/nombre de pixels classés dans la classe
    # Attention : les microclasses disparues dans la classification ont une précision de 0
    for lin_index in range(len(matrix)):
        if total_produced_pixels_count_list[lin_index] != 0:
            precision_list.append(matrix[lin_index][lin_index]/total_produced_pixels_count_list[lin_index])
        else :
            precision_list.append(0)

    # Calcul du overall_accuracy
    #---------------------------
    # Définition : overall_accuracy = moyenne pondérée des différentes valeurs de précision
    overall_accuracy = 0
    for index in range(len(precision_list)):
        overall_accuracy += precision_list[index] * total_produced_pixels_count_list[index]
    if all_pixel_count > 0:
        overall_accuracy = overall_accuracy / all_pixel_count
    else :
        overall_accuracy = 0

    # Calcul du f_score
    #------------------
    # Définition : F-Score d'une classe = 2*rappel(classe)*précision(classe)/(rappel(classe)+précision(classe))
    # Attention : On ne calcule pas le F-Score pour les microclasses disparues dans la classification
    for lin_index in range(len(matrix)):
        if recall_list[lin_index]+precision_list[lin_index] != 0 :
            fscore_list.append(2*recall_list[lin_index]*precision_list[lin_index]/(recall_list[lin_index]+precision_list[lin_index]))
        else :
            fscore_list.append(0)

    # Calcul du overall_fscore
    #-------------------------
    # Définition : overall_fscore = moyenne pondérée des différentes valeurs de fscore
    overall_fscore = 0
    for index in range(len(fscore_list)):
        overall_fscore += fscore_list[index] * total_reference_pixels_count_list[index]  # Le choix de total_reference_pixels_count_list par rapport à total_produced_pixels_count_list est arbitraire
    if all_pixel_count > 0:
        overall_fscore = overall_fscore / all_pixel_count
    else :
        overall_fscore = 0

    if debug >= 3 :
        print(cyan + "computeIndicators : " + bold + green + "all_pixel_count: " + str(all_pixel_count) + endC)
        print(cyan + "computeIndicators : " + bold + green + "recall_list: " + str(recall_list) + endC)
        print(cyan + "computeIndicators : " + bold + green + "overall_rappel: " + str(overall_rappel) + endC)
        print(cyan + "computeIndicators : " + bold + green + "precision_list: " + str(precision_list) + endC)
        print(cyan + "computeIndicators : " + bold + green + "overall_accuracy: " + str(overall_accuracy) + endC)
        print(cyan + "computeIndicators : " + bold + green + "fscore_list: " + str(fscore_list) + endC)
        print(cyan + "computeIndicators : " + bold + green + "overall_fscore: " + str(overall_fscore) + endC)

    # Calcul de la precision globale
    #-------------------------------
    if sum_from_ref != 0:
        overall_accuracy = sum_diag/sum_from_ref
    else:
        overall_accuracy = 0

    # Calcul du kappa
    #----------------
    if sum_from_ref*sum_from_ref-sum_marginal_tot != 0:
        kappa = (sum_from_ref*sum_diag-sum_marginal_tot)/(sum_from_ref*sum_from_ref-sum_marginal_tot)
    else:
        kappa = 0

    if debug >= 3 :
        print(cyan + "computeIndicators : " + bold + green + "N_ref: " + str(sum_from_ref) + endC)
        print(cyan + "computeIndicators : " + bold + green + "N_prod: " + str(sum_from_prod) + endC)
        print(cyan + "computeIndicators : " + bold + green + "sum_diag: " + str(sum_diag) + endC)
        print(cyan + "computeIndicators : " + bold + green + "sum_marginal_tot: " + str(sum_marginal_tot) + endC)
        print(cyan + "computeIndicators : " + bold + green + "overall_accuracy: " + str(overall_accuracy) + endC)
        print(cyan + "computeIndicators : " + bold + green + "kappa: " + str(kappa) + endC)

    # Initialisation des variables pour le calcul des faux positifs, faux négatifs et performances
    #---------------------------------------------------------------------------------------------

    nb_false_positive_list = []      # Pour chaque classe, le nombre de faux positifs est le nombre de pixels reconnus de cette classe dans la classification mais non présent dans la vérification. En pratique, correspond à la somme de la colonne sans la diagonale, ou autrement dit le nombre total de pixels de la classe dans le résultat de classification moins le nombre de pixel de la classe bien reconnus
    total_false_positive_list = []   # Pour chaque classe, le total de faux positifs est le nombre de pixels de vérification qui ne sont pas dans cette classe. En pratique, c'est le nombre total de pixels moins le nombre de pixels de vérifications de la classe
    rate_false_positive_list = []    # Pour chaque classe, le taux de faux positifs est le rapport entre le nombre de faux positif et le total de faux positifs
    nb_false_negative_list = []      # Pour chaque classe, le nombre de faux négatifs est le nombre de pixels de vérification de cette classe non reconnus par la classification. En pratique, correspond à la somme de la ligne sans la diagonale, ou autrement dit le nombre total de pixels de vérification de la classe moins le nombre de pixel de la classe bien reconnus
    total_false_negative_list = []   # Pour chaque classe, le total de faux négatifs est le nombre de pixels de vérification qui sont dans cette classe.
    rate_false_negative_list = []    # Pour chaque classe, le taux de faux négatifs est le rapport entre le nombre de faux négatifs et le total de faux négatifs
    total_performance_list = []      # Pour chaque classe, le total utilisé pour le calcul de la performance est la somme de faux positifs, faux négatifs et les vrais positifs (diagonale)
    performance_list = []            # Pour chaque classe, la performance est le ratio entre les vrais positifs (diagonale) avec le total associé
    quantity_rate_list = []          # Pour chaque classe, le taux de pixel de la classe en quantité est le rapport entre le nombre pixels de la classif et le nombre de pixel de la référence

    # Gestion des faux positifs
    for col_index in range(len(matrix[0])):
        nb_false_positive_list.append(total_produced_pixels_count_list[col_index]-matrix[col_index][col_index])
        total_false_positive_list.append(all_pixel_count - total_reference_pixels_count_list[col_index])
        if total_false_positive_list[col_index] != 0 :
            rate_false_positive_list.append(nb_false_positive_list[col_index]/total_false_positive_list[col_index])
        else :
            rate_false_positive_list.append(1)

    # Gestion des faux négatifs
    for lin_index in range(len(matrix)):
        nb_false_negative_list.append(total_reference_pixels_count_list[lin_index]-matrix[lin_index][lin_index])
        total_false_negative_list.append(total_reference_pixels_count_list[lin_index])
        if total_false_negative_list[lin_index] != 0 :
            rate_false_negative_list.append(nb_false_negative_list[lin_index]/total_false_negative_list[lin_index])
        else :
            rate_false_negative_list.append(1)

    # Gestion de la performance
    for col_index in range(len(matrix[0])):
        total_performance_list.append(matrix[col_index][col_index]+nb_false_positive_list[col_index]+nb_false_negative_list[col_index])
        if total_performance_list[col_index] != 0 :
            performance_list.append(matrix[col_index][col_index]/total_performance_list[col_index])
        else :
            performance_list.append(0)

    # Gestion du taux de quantité classif / référence
    for col_index in range(len(matrix[0])):
        if total_reference_pixels_count_list[col_index] != 0:
            quantity_rate_list.append(total_produced_pixels_count_list[col_index] / total_reference_pixels_count_list[col_index])
        else :
            quantity_rate_list.append(0)

    # Calcul du overall_performance
    #------------------------------
    # Définition : overall_performance = moyenne pondérée des différentes valeurs de performance
    overall_performance = 0
    sum_total_performance = 0
    for index in range(len(performance_list)):
        overall_performance += performance_list[index] * total_performance_list[index]
        sum_total_performance += total_performance_list[index]
    if sum_total_performance != 0 :
        overall_performance = overall_performance / sum_total_performance
    else :
        overall_performance = 0

    if debug >= 3 :
        print(cyan + "computeIndicators : " + bold + green + "nb_false_positive_list: " + str(nb_false_positive_list) + endC)
        print(cyan + "computeIndicators : " + bold + green + "total_false_positive_list: " + str(total_false_positive_list) + endC)
        print(cyan + "computeIndicators : " + bold + green + "rate_false_positive_list: " + str(rate_false_positive_list) + endC)
        print(cyan + "computeIndicators : " + bold + green + "nb_false_negative_list: " + str(nb_false_negative_list) + endC)
        print(cyan + "computeIndicators : " + bold + green + "total_false_negative_list: " + str(total_false_negative_list) + endC)
        print(cyan + "computeIndicators : " + bold + green + "rate_false_negative_list: " + str(rate_false_negative_list) + endC)
        print(cyan + "computeIndicators : " + bold + green + "quantity_rate_list: " + str(quantity_rate_list) + endC)
        print(cyan + "computeIndicators : " + bold + green + "total_performance_list: " + str(total_performance_list) + endC)
        print(cyan + "computeIndicators : " + bold + green + "performance_list: " + str(performance_list) + endC)
        print(cyan + "computeIndicators : " + bold + green + "overall_performance: " + str(overall_performance) + endC)

    if debug >=2:
        print(cyan + "computeIndicators() : " + bold + green + "Quality indicator computed" + '\n' + endC)

    return precision_list, recall_list, fscore_list, performance_list, rate_false_positive_list, rate_false_negative_list, quantity_rate_list, class_list, overall_accuracy, overall_fscore, overall_performance, kappa


###########################################################################################################################################
# FONCTION writeQualityIndicatorsToCsvFile()                                                                                              #
###########################################################################################################################################
def writeQualityIndicatorsToCsvFile(class_count, precision_list, recall_list, fscore_list, performance_list, TFP_class_list, TFN_class_list, quantity_rate_list, class_list, overall_accuracy, overall_fscore, overall_performance, kappa, indicators_output_file, overwrite, textures_list) :
    """
    # ROLE:
    #  Ecrit le résultat des indicateurs de qualités dans un fichier csv
    #
    # ENTREES DE LA FONCTION :
    #     class_count : nombre de classes
    #     precision_list : liste precision
    #     recall_list : liste recall
    #     fscore_list : liste fscore
    #     performance_list : liste performance
    #     TFP_class_list : liste  de faux positif
    #     TFN_class_list : liste de faux negatif
    #     quantity_rate_list : liste quantity_rate
    #     class_list : liste des classes
    #     overall_accuracy : indicateur de overall accuracy
    #     overall_fscore : indicateur de overall fscore
    #     overall_performance: indicateur de overall performance
    #     kappa : indicateur  kappa
    #     indicators_output_file : non du fichier csv de sortie contenant les indicateurs
    #     overwrite : supprime ou non les fichiers existants ayant le meme nom
    #     textures_list : liste des textures
    #
    # SORTIES DE LA FONCTION :
    #    auccun
    #
    """
    check = os.path.isfile(indicators_output_file)
    if check and not overwrite :
        print(cyan + "writeQualityIndicatorsToCsvFile() : " + bold + yellow + "Result file quality indicators exists." + '\n' + endC)
    else:

        # verifier si les info textures existes
        if textures_list is None :
            # Tente de supprimer le fichier
            try:
                removeFile(indicators_output_file)
            except Exception:
                #Ignore l'exception levee si le fichier n'existe pas (et ne peut donc pas être supprime)
                pass

        else :
            # Ecriture du nom de la texture
            texture_characteristics = textures_list[0]
            texture_name = str(texture_characteristics[0])
            channel = str(texture_characteristics[1])
            radius = str(texture_characteristics[2])
            text_texture = "Name : %s ; Channel : %s ; Radius : %s \n" %(texture_name,channel,radius)
            appendTextFile(indicators_output_file, text_texture)

        print(cyan + "writeQualityIndicatorsToCsvFile() : " + bold + green + "Writing file quality indicators..." + '\n' + endC)

        # contenu texte des indicateurs
        text_indicators = "Overall Accuracy ; Overall F1-Score ; Overall Performance  ;  Kappa  \n  %f  ;  %f  ;  %f  ;  %f  \n\n" %(overall_accuracy, overall_fscore, overall_performance, kappa)
        text_class_list = " Class  "
        text_precision_list = " Precision  "
        text_recall_list = " Recall  "
        text_f_scores_list = " F1-Scores "
        text_performance_list = " Performance "
        text_TFP_class_list = " TFP_class "
        text_TFN_class_list = " TFN_class "
        text_quantity_rate_list = " Quantity_rate "

        for i in range(class_count):
            text_class_list += " ; %d" %(class_list[i])
            text_precision_list += " ; %f" %(precision_list[i])
            text_recall_list += " ; %f" %(recall_list[i])
            text_f_scores_list += " ; %f" %(fscore_list[i])
            text_performance_list += " ; %f" %(performance_list[i])
            text_TFP_class_list += " ; %f" %(TFP_class_list[i])
            text_TFN_class_list += " ; %f" %(TFN_class_list[i])
            text_quantity_rate_list += " ; %f" %(quantity_rate_list[i])


        text_File_list = text_class_list + "\n" \
                       + text_precision_list + "\n" \
                       + text_recall_list + "\n"  \
                       + text_f_scores_list + "\n"  \
                       + text_performance_list + "\n" \
                       + text_TFP_class_list + "\n" \
                       + text_TFN_class_list + "\n" \
                       + text_quantity_rate_list + "\n\n" \
                       + text_indicators + "\n"
        try:
            appendTextFile(indicators_output_file, text_File_list)

        except Exception:
            raise NameError(cyan + "writeQualityIndicatorsToCsvFile() : " + bold + red + "An error occured during writing " + indicators_output_file + " file quality indicators. See error message above." + endC)
    print(cyan + "writeQualityIndicatorsToCsvFile() : " + bold + green + "Quality indicators writed on file" + '\n' + endC)
    return

###########################################################################################################################################
# MISE EN PLACE DU PARSER                                                                                                                 #
###########################################################################################################################################

# Code executé seulement dans le cas ou le script est lancé depuis une ligne de commande
# Il n'est pas executé lors d'un import QualityIndicatorComputation.py
# Exemple de lancement en ligne de commande:
# python QualityIndicatorComputation.py -i ../ImagesTestChaine/APTV_05/Micro/APTV_05_stack_raw.tif -v ../ImagesTestChaine/APTV_05/Micro/APTV_05_cleaned.shp -ocm ../ImagesTestChaine/APTV_05/Micro/APTV_05_confusion_matrix.txt -oqi ../ImagesTestChaine/APTV_05/Micro/APTV_05_quality_indicators.csv -id id -log ../ImagesTestChaine/APTV_05/fichierTestLog.txt


def main(gui=False):

    # Définition des arguments possibles pour l'appel en ligne de commande
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, prog="QualityIndicatorComputation", description="\
    Info : To create a quality indicator file. \n\
    Objectif : Generer une matrice de confusion et analyser la matrice. \n\
    Example : python QualityIndicatorComputation.py -i ../ImagesTestChaine/APTV_05/Micro/APTV_05_stack_raw.tif \n\
                                                    -v ../ImagesTestChaine/APTV_05/Micro/APTV_05_cleaned.shp \n\
                                                    -ocm ../ImagesTestChaine/APTV_05/Micro/APTV_05_confusion_matrix.txt \n\
                                                    -oqi ../ImagesTestChaine/APTV_05/Micro/APTV_05_quality_indicators.csv \n\
                                                    -id id \n\
                                                    -log ../ImagesTestChaine/APTV_05/fichierTestLog.txt")

    # Paramètres
    parser.add_argument('-i','--image_input',default="",help="Image input result classification", type=str, required=True)
    parser.add_argument('-v','--vector_input',default=None,help="Vector input contain the validation samples", type=str, required=False)
    parser.add_argument('-s','--sample_input',default=None,help="Raster input contain the validation samples", type=str, required=False)
    parser.add_argument('-ocm','--conf_matrix_output',default="",help="File output confusion matrix file", type=str, required=True)
    parser.add_argument('-oqi','--quality_indic_output',default="",help="File output quality indicators file", type=str, required=True)
    parser.add_argument('-id','--validation_id',default="id",help="Label to identify the class", type=str, required=False)
    parser.add_argument('-text','--textures_list',nargs="+",default=None,help="List of textures to use or calculate, (format : texture,channel,radius), ex. HaralickCorrelation,PIR,2", type=str, required=False)
    parser.add_argument('-ndv','--no_data_value', default=0, help="Option in option optimize_emprise_nodata  : Value of the pixel no data. By default : 0", type=int, required=False)
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
            raise NameError (cyan + "QualityIndicatorComputation : " + bold + red  + "File %s not existe!" %(image_input) + endC)

    # Récupération du fichier vecteur d'entrée d'echantillons de référence
    vector_input = None
    if args.vector_input != None:
        vector_input = args.vector_input
        if not os.path.isfile(vector_input):
            raise NameError (cyan + "QualityIndicatorComputation : " + bold + red  + "File %s not existe!" %(vector_input) + endC)

    # Récupération du fichier raster d'entrée d'echantillons de référence
    sample_input = None
    if args.sample_input != None:
        sample_input = args.sample_input
        if vector_input != "" and not os.path.isfile(sample_input):
            raise NameError (cyan + "QualityIndicatorComputation : " + bold + red  + "File %s not existe!" %(sample_input) + endC)

    if (vector_input == None or vector_input == "") and (sample_input == None or sample_input == ""):
        raise NameError(cyan + "QualityIndicatorComputation : " + bold + red + "Parameters 'vector_input' is emply and 'sample_input' is emply" + endC)

    # Récupération du fichier de sortie matrice de confusion
    if args.conf_matrix_output != None:
        conf_matrix_output = args.conf_matrix_output

    # Récupération du fichier de sortie indicateur de qualité
    if args.quality_indic_output != None:
        quality_indic_output = args.quality_indic_output

    # Récupération des arguments donnés
    if args.validation_id != None:
        validation_id_field = args.validation_id

    # Les listes textures
    if args.textures_list != None:
        tmp_text_list = args.textures_list
        textures_list = []
        for tmp_txt in tmp_text_list:
            info_text = []
            for text in tmp_txt.split(','):
                info_text.append(text)
            textures_list.append(info_text)
    else :
        textures_list = None


    # Récupération du parametre no_data_value
    if args.no_data_value!= None:
        no_data_value = args.no_data_value

    # Récupération du nom du fichier log
    if args.path_time_log!= None:
        path_time_log = args.path_time_log

    if args.save_results_inter != None:
        save_results_intermediate = args.save_results_inter

    if args.overwrite!= None:
        overwrite = args.overwrite

    # Récupération de l'option niveau de debug
    if args.debug!= None:
        global debug
        debug = args.debug

    # Affichage des arguments récupérés
    if debug >= 3:
        print(bold + green + "Variables dans le parser" + endC)
        print(cyan + "QualityIndicatorComputation : " + endC + "image_input : " + str(image_input) + endC)
        print(cyan + "QualityIndicatorComputation : " + endC + "vector_input : " + str(vector_input) + endC)
        print(cyan + "QualityIndicatorComputation : " + endC + "sample_input : " + str(sample_input) + endC)
        print(cyan + "QualityIndicatorComputation : " + endC + "conf_matrix_output : " + str(conf_matrix_output) + endC)
        print(cyan + "QualityIndicatorComputation : " + endC + "quality_indic_output : " + str(quality_indic_output) + endC)
        print(cyan + "QualityIndicatorComputation : " + endC + "validation_id : " + str(validation_id_field) + endC)
        print(cyan + "QualityIndicatorComputation : " + endC + "textures_list : " + str(textures_list) + endC)
        print(cyan + "QualityIndicatorComputation : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "QualityIndicatorComputation : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "QualityIndicatorComputation : " + endC + "save_results_inter : " + str(save_results_intermediate) + endC)
        print(cyan + "QualityIndicatorComputation : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "QualityIndicatorComputation : " + endC + "debug : " + str(debug) + endC)

    # EXECUTION DE LA FONCTION
    # Si les dossier de sorties n'existent pas, on les crées
    repertory_output = os.path.dirname(conf_matrix_output)
    if not os.path.isdir(repertory_output):
        os.makedirs(repertory_output)

    repertory_output = os.path.dirname(quality_indic_output)
    if not os.path.isdir(repertory_output):
        os.makedirs(repertory_output)

    # Execution du calcul des indicateurs pour une image
    computeQualityIndicator(image_input, vector_input, sample_input, conf_matrix_output, quality_indic_output, validation_id_field, textures_list, no_data_value, path_time_log, overwrite)

# ================================================

if __name__ == '__main__':
  main(gui=False)
