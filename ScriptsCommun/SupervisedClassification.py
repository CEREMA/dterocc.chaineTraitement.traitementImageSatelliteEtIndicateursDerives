#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerSO/DALETT/SCGSI  All rights reserved.                                                                            #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT QUI APPLIQUE UNE CLASSIFICATION SUPERVISEE                                                                                         #
#                                                                                                                                           #
#############################################################################################################################################
'''
Nom de l'objet : SupervisedClassification.py
Description :
    Objectif : exécute une classification supervisée SVM sur des images (brutes ou avec neocanaux) en se basant sur des échantillons d'entrainement vectorisés
    Rq : utilisation des OTB Applications : otbcli_ComputeImagesStatistics, otbcli_ImageClassifier, otbcli_PolygonClassStatistics, otbcli_SampleExtraction, otbcli_TrainVectorClassifier

Date de creation : 29/07/2014
----------
Histoire :
----------
Origine : le script originel provient du fichier Chain6_SupervisedClassification.py cree en 2013 et utilise par la chaine de traitement OCSOL V1.X
30/07/2013 : Transformation en brique elementaire (suppression des liens avec la chaine OCSOL)
-----------------------------------------------------------------------------------------------------
Modifications
4/08/2014 : ajout overwrite
01/10/2014 : refonte du fichier harmonisation des régles de qualitées des niveaux de boucles et des paramétres dans args
21/05/2015 : simplification des parametres en argument plus de liste d'image en emtrée à traiter uniquement une image
09/03/2017 : refonte de l'application et éclatement de l'application otbcli_TrainImagesClassifier en 4 applis : PolygonClassStatistics, otbcli_SampleSelection,SampleSelection,SampleExtraction,TrainVectorClassifier

------------------------------------------------------
A Reflechir/A faire

'''

from __future__ import print_function
import os,sys,glob,string,shutil,time,argparse
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_log import timeLine
from Lib_operator import getExtensionApplication
from Lib_raster import updateReferenceProjection, getGeometryImage, computeStatisticsImage
from Lib_file import removeVectorFile, removeFile
from Lib_text import appendTextFileCR

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 3

###########################################################################################################################################
# STRUCTURE StructRFParameter                                                                                                             #
###########################################################################################################################################
# Structure contenant les parametres utiles au calcul du model RF
class StructRFParameter:
    def __init__(self):
        self.max_depth_tree = 0
        self.min_sample = 0
        self.ra_termin_criteria = 0.0
        self.cat_clusters = 0
        self.var_size_features = 0
        self.nbtrees_max = 0
        self.acc_obb_erreur = 0.0

###########################################################################################################################################
# FONCTION computeModelSVM()                                                                                                              #
###########################################################################################################################################
# ROLE:
#    Calcul le model utile à la creation de la classification selon l'algorithme SVM
#
# ENTREES DE LA FONCTION :
#    sample_values_input : fichier de valeur d'echantillons points au format .shp
#    statistics_image_input : fichier statistique .xml
#    model_file_output : fichier model résultat
#    matrix_file_output : fichier matrice de confusion
#    field_class : label (colonne) pour distinguer les classes exemple : "id"
#    feat_list : liste des noms des champs à prendre en compte pour le model
#    kernel : paramètre du SVM choix de l'algo ("linear")
#
# SORTIES DE LA FONCTION :
#    auccun
#    Eléments générés par la fonction : un fichier model ("*_model.txt")
#
def computeModelSVM(sample_values_input, statistics_image_input, model_file_output, matrix_file_output, field_class, feat_list, kernel) :

    feat_list_str = ""
    for feat in feat_list:
        feat_list_str += feat + ' '

    # Calcul du model
    command = "otbcli_TrainVectorClassifier -io.vd %s -io.stats %s -io.out %s -io.confmatout %s -cfield %s -feat %s -classifier libsvm -classifier.libsvm.k %s" %(sample_values_input,statistics_image_input,model_file_output,matrix_file_output,field_class,feat_list_str,kernel)

    if debug >= 3:
        print(command)

    exitCode = os.system(command)
    if exitCode != 0:
        raise NameError(cyan + "computeModelSVM() : " + bold + red + "An error occured during otbcli_TrainVectorClassifier command. See error message above." + endC)

    #fd = os.open( model_file_output, os.O_RDWR|os.O_CREAT )
    #os.fsync(fd)
    #os.close(fd)

    return

###########################################################################################################################################
# FONCTION computeModelRF()                                                                                                              #
###########################################################################################################################################
# ROLE:
#    Calcul le model utile à la creation de la classification selon l'algorithme RF
#
# ENTREES DE LA FONCTION :
#    sample_values_input : fichier de valeur d'echantillons points au format .shp
#    statistics_image_input : fichier statistique .xml
#    model_file_output : fichier model résultat
#    matrix_file_output : fichier matrice de confusion
#    field_class : label (colonne) pour distinguer les classes exemple : "id"
#    feat_list : liste des noms des champs à prendre en compte pour le model
#    rf_parametres_struct : les paramètres du RF
#
# SORTIES DE LA FONCTION :
#    auccun
#    Eléments générés par la fonction : un fichier model ("*_model.txt")
#
def computeModelRF(sample_values_input, statistics_image_input, model_file_output, matrix_file_output, field_class, feat_list, rf_parametres_struct) :

    feat_list_str = ""
    for feat in feat_list:
        feat_list_str += feat + ' '

    # Calcul du model
    command = "otbcli_TrainVectorClassifier -io.vd %s -io.stats %s -io.out %s -io.confmatout %s -cfield %s -feat %s -classifier rf -classifier.rf.max %d -classifier.rf.min %d -classifier.rf.ra %f -classifier.rf.cat %d -classifier.rf.var %d -classifier.rf.nbtrees %d -classifier.rf.acc %f" %(sample_values_input,statistics_image_input,model_file_output,matrix_file_output,field_class,feat_list_str,rf_parametres_struct.max_depth_tree,rf_parametres_struct.min_sample,rf_parametres_struct.ra_termin_criteria,rf_parametres_struct.cat_clusters,rf_parametres_struct.var_size_features,rf_parametres_struct.nbtrees_max,rf_parametres_struct.acc_obb_erreur)

    if debug >= 3:
        print(command)

    exitCode = os.system(command)
    if exitCode != 0:
        raise NameError(cyan + "computeModelRF() : " + bold + red + "An error occured during otbcli_TrainVectorClassifier command. See error message above." + endC)

    #fd = os.open( model_file_output, os.O_RDWR|os.O_CREAT )
    #os.fsync(fd)
    #os.close(fd)

    return

###########################################################################################################################################
# FONCTION classifySupervised()                                                                                                          #
###########################################################################################################################################
# ROLE:
#     Execute une classification supervisee sur des images (brutes ou avec neocanaux) en se basant sur des echantillons d'entrainement vectorises dans un shapefile.
#    La classification se déroule en 6 etapes :
#       1) calcul des statistiques de l'image,
#       2) calcul des statistiques des polygones des échantillons,
#       3) selection des échantillons à partir de l'image des polygones d'échantillon et des statistiques des polygones des échantillons,
#       4) extraction des échantillons seléctionés à partir l'image et des échantillons points selectionés,
#       5) creation du model a partir des echantillons points et des statistiques image,
#       6) classification a partir des statistiques et du model
#
# ENTREES DE LA FONCTION :
#    image_input_list : liste d'image d'entrée stacké au format .tif
#    vector_input : fichier echantillons entrainement au format .shp
#    sample_points_values_input : fichier de points d'échantillons en entrée au format .shp
#    sample_emply_input : fichier de points d'échantillons sans valeurs en entrée au format .shp
#    classification_file_output : fichier resultat de la classification
#    confidence_file_output : fichier contenant la carte de confiance associer à la classification
#    model_output : fichier model sauvegarder en sortie avec se nom
#    model_input : fichier model d'entrée, il ne sera pas regénérer mais utilisé directement
#    field_class : label (colonne) pour distinguer les classes exemple : "id"
#    sampler_mode : mode du choix des échantillons ("periodic" ou "random")
#    periodic_value : si le mode de choix d'échantillons est "periodic" divinie la valeur de la periode
#    classifier_mode : definie le choix du type de classification ("svm" ou "rf")
#    kernel : paramètre du SVM choix de l'algo ("linear")
#    rf_parametres_struct : les paramètres du RF
#    no_data_value : Option : Value pixel of no data
#    path_time_log : le fichier de log de sortie
#    ram_otb : memoire RAM disponible pour les applications OTB
#    format_raster : Format de l'image de sortie par défaut GTiff (GTiff, HFA...)
#    extension_vector : extension du fichier vecteur de sortie, par defaut = '.shp'
#    save_results_intermediate : fichiers de sorties intermediaires nettoyees, par defaut = False
#    overwrite : supprime ou non les fichiers existants ayant le meme nom
#
# SORTIES DE LA FONCTION :
#    auccun
#    Eléments générés par la fonction : deux fichiers statistics ("*_statistics.xml"), un fichier model ("*_model.txt"), une image classee("*_raw.tif")
#
def classifySupervised(image_input_list, vector_input, sample_points_values_input, sample_emply_input, classification_file_output, confidence_file_output, model_output, model_input, field_class, sampler_mode, periodic_value, classifier_mode, kernel, rf_parametres_struct, no_data_value, path_time_log, ram_otb=0,  format_raster='GTiff', extension_vector=".shp", save_results_intermediate=False, overwrite=True):

    # Mise à jour du Log
    starting_event = "classifySupervised() : Classifiy supervised starting : "
    timeLine(path_time_log,starting_event)

    print(endC)
    print(bold + green + "## START :  SUPERVISED CLASSIFICATION" + endC)
    print(endC)

    if debug >= 3:
        print(cyan + "classifySupervised() : " + endC + "image_input_list : " + str(image_input_list) + endC)
        print(cyan + "classifySupervised() : " + endC + "vector_input : " + str(vector_input) + endC)
        print(cyan + "classifySupervised() : " + endC + "sample_points_values_input : " + str(sample_points_values_input) + endC)
        print(cyan + "classifySupervised() : " + endC + "sample_emply_input : " + str(sample_emply_input) + endC)
        print(cyan + "classifySupervised() : " + endC + "classification_file_output : " + str(classification_file_output) + endC)
        print(cyan + "classifySupervised() : " + endC + "confidence_file_output : " + str(confidence_file_output) + endC)
        print(cyan + "classifySupervised() : " + endC + "model_output : " + str(model_output) + endC)
        print(cyan + "classifySupervised() : " + endC + "model_input : " + str(model_input) + endC)
        print(cyan + "classifySupervised() : " + endC + "field_class : " + str(field_class) + endC)
        print(cyan + "classifySupervised() : " + endC + "sampler_mode : " + str(sampler_mode) + endC)
        print(cyan + "classifySupervised() : " + endC + "periodic_value : " + str(periodic_value) + endC)
        print(cyan + "classifySupervised() : " + endC + "classifier_mode : " + str(classifier_mode) + endC)
        print(cyan + "classifySupervised() : " + endC + "kernel : " + str(kernel) + endC)
        print(cyan + "classifySupervised() : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "classifySupervised() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "classifySupervised() : " + endC + "ram_otb : " + str(ram_otb) + endC)
        print(cyan + "classifySupervised() : " + endC + "format_raster : " + str(format_raster) + endC)
        print(cyan + "classifySupervised() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "classifySupervised() : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "classifySupervised() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "classifySupervised() : " + endC + "overwrite : " + str(overwrite) + endC)

    # Constantes
    CODAGE_16B = "uint16"
    CODAGE_F = "float"

    EXT_XML = ".xml"
    EXT_TEXT = ".txt"

    SUFFIX_STATISTICS = "_statistics"
    SUFFIX_IMAGE = "_image"
    SUFFIX_POLYGON = "_polygon"
    SUFFIX_SAMPLE = "_sample"
    SUFFIX_POINTS = "_points"
    SUFFIX_VALUES = "_values"
    SUFFIX_MODEL = "_model"
    SUFFIX_MATRIX = "_matrix"
    SUFFIX_MERGE = "_merge"

    BAND_NAME = "band_"

    # 0. PREPARATION DES FICHIERS TEMPORAIRES
    #----------------------------------------

    # Définir les fichiers de sortie temporaire (statistiques image / statistiques polygone / model)
    image_input = image_input_list[0]
    nb_input_images = len(image_input_list)
    name = os.path.splitext(os.path.basename(image_input))[0]
    repertory_output = os.path.dirname(classification_file_output)
    statistics_image_output = repertory_output + os.sep + name + SUFFIX_IMAGE + SUFFIX_STATISTICS + EXT_XML
    statistics_sample_polygon_output = repertory_output + os.sep + name + SUFFIX_POLYGON + SUFFIX_STATISTICS + EXT_XML
    sample_points_resample_polygons_output = repertory_output + os.sep + name + SUFFIX_SAMPLE + SUFFIX_POINTS + extension_vector
    sample_points_values_output = repertory_output + os.sep + name +  SUFFIX_SAMPLE + SUFFIX_VALUES + extension_vector
    matrix_file_output = repertory_output + os.sep + name + SUFFIX_MATRIX + EXT_TEXT

    pass_compute_model = False
    if model_input != "" :
        model_file_output = model_input
        pass_compute_model = True
    elif model_output != "" :
        model_file_output = model_output
    else :
        model_file_output = repertory_output + os.sep + name + SUFFIX_MODEL + EXT_TEXT

    # Test l'existance d'un fichier d'échantions points en entrée
    sample_points_existe = False
    sample_emply_existe = False
    if  sample_points_values_input is not None and os.path.isfile(sample_points_values_input) :
        sample_points_existe = True
        sample_points_values_output = sample_points_values_input

    if  sample_emply_input is not None and os.path.isfile(sample_emply_input) :
        sample_points_existe = False
        sample_emply_existe = True
        sample_points_resample_polygons_output = sample_emply_input

    # 1. CALCUL DES STATISTIQUES DE L'IMAGE SAT
    #------------------------------------------

    print(cyan + "classifySupervised() : " + bold + green + "Statistics computation for input images ..." + endC)

    # Vérification de l'existence des images pour calculer les statistiques
    list_image_input_str = ""
    for image_input_tmp in image_input_list :
        list_image_input_str = image_input_tmp + " "
        if not os.path.isfile(image_input_tmp):
            raise NameError(cyan + "classifySupervised() : " + bold + red + "No image %s available.\n" %(image_input_tmp) + endC)

    # Si les statistiques existent deja et que overwrite n'est pas activé
    check = os.path.isfile(statistics_image_output)
    if check and not overwrite:
        print(bold + yellow + "Statistics computation %s already done for image and will not be calculated again." %(statistics_image_output) + endC)
    else:   # Si non ou si la vérification est désactivée : calcul des statistiques de l'image

        # Suppression de l'éventuel fichier existant
        if check:
            try:
                removeFile(statistics_image_output)
            except Exception:
                pass # Si le fichier ne peut pas être supprimé, on suppose qu'il n'existe pas et on passe à la suite

        # Calcul statistique
        if nb_input_images == 1:
            computeStatisticsImage(image_input, statistics_image_output)

        else :
            command = "otbcli_ComputeImagesStatistics -il %s -out %s" %(list_image_input_str, statistics_image_output)
            if ram_otb > 0:
                    command += " -ram %d" %(ram_otb)

            if debug >= 3:
                print(command)

            exitCode = os.system(command)
            if exitCode != 0:
                raise NameError(cyan + "classifySupervised() : " + bold + red + "An error occured during otbcli_ComputeImagesStatistics command. See error message above." + endC)

        print(cyan + "classifySupervised() : " + bold + green + "Statistics image are ready." + endC)

    # Si le fichier d'échantions points en entrée existe, on saute les étapes 2 - 3 et 4 si on a un fichier model en entrée on passe les etapes 2 - 3 - 4 et 5
    if not sample_points_existe and not sample_emply_existe and not pass_compute_model and nb_input_images==1 :

        # 2. CALCUL DES STATISTIQUES DES POLYGONES DES ECHANTILLONS D'APPRENTISSAGE
        #--------------------------------------------------------------------------

        print(cyan + "classifySupervised() : " + bold + green + "Statistics computation for samples polygones %s ..." %(vector_input) + endC)

        # Vérification de l'existence du vecteur d'entrainement pour calculer les statistiques
        if not os.path.isfile(vector_input):
            raise NameError(cyan + "classifySupervised() : " + bold + red + "No training vector %s available.\n" %(vector_input) + endC)

        # Si les statistiques polygones existent deja et que overwrite n'est pas activé
        check = os.path.isfile(statistics_sample_polygon_output)
        if check and not overwrite:
            print(cyan + "classifySupervised() : " + bold + yellow + "Statistics computation %s already done for sample polygon and will not be calculated again." %(statistics_sample_polygon_output) + endC)
        else:   # Si non ou si la vérification est désactivée : calcul des statistiques des polygones

            # Suppression de l'éventuel fichier existant
            if check:
                try:
                    removeFile(statistics_sample_polygon_output)
                except Exception:
                    pass # Si le fichier ne peut pas être supprimé, on suppose qu'il n'existe pas et on passe à la suite

            # Calcul statistique
            command = "otbcli_PolygonClassStatistics -in %s -vec %s -out %s -field %s" %(image_input, vector_input, statistics_sample_polygon_output, field_class)
            if ram_otb > 0:
                command += " -ram %d" %(ram_otb)

            if debug >= 3:
                print(command)

            exitCode = os.system(command)
            if exitCode != 0:
                raise NameError(cyan + "classifySupervised() : " + bold + red + "An error occured during otbcli_ComputeImagesStatistics command. See error message above." + endC)

            print(cyan + "classifySupervised() : " + bold + green + "Statistics sample polygon are ready." + endC)

        # 3. SELECTION DES POINTS D'ECHANTILLONS
        #---------------------------------------

        print(cyan + "classifySupervised() : " + bold + green + "Points samples selection for samples polygones %s ..." %(vector_input) + endC)

        # Vérification de l'existence du fichier statistique pour selectionner les points
        if not os.path.isfile(statistics_sample_polygon_output):
            raise NameError(cyan + "classifySupervised() : " + bold + red + "No statistics file %s available.\n" %(statistics_sample_polygon_output) + endC)

        # Si le fichier points d'echantillons existe deja et que overwrite n'est pas activé
        check = os.path.isfile(sample_points_resample_polygons_output)
        if check and not overwrite:
            print(bold + yellow + "Selection samples %s already done for sample polygon and will not be calculated again." %(sample_points_resample_polygons_output) + endC)
        else:   # Si non ou si la vérification est désactivée : selection des échantillons points

            # Suppression de l'éventuel fichier existant
            if check:
                try:
                    removeFile(sample_points_resample_polygons_output)
                except Exception:
                    pass # Si le fichier ne peut pas être supprimé, on suppose qu'il n'existe pas et on passe à la suite

            # Select sample
            command = "otbcli_SampleSelection -in %s -vec %s -instats %s -out %s -field %s -sampler %s" %(image_input, vector_input, statistics_sample_polygon_output, sample_points_resample_polygons_output, field_class, sampler_mode.lower())
            if ram_otb > 0:
                command += " -ram %d" %(ram_otb)

            if sampler_mode.lower() == "periodic" :
                command += " -sampler.periodic.jitter %d "%(periodic_value)

            if debug >= 3:
                print(command)

            exitCode = os.system(command)
            if exitCode != 0:
                raise NameError(cyan + "classifySupervised() : " + bold + red + "An error occured during otbcli_SampleSelection command. See error message above." + endC)

            print(cyan + "classifySupervised() : " + bold + green + "Points samples are selected." + endC)

    # Test si on execute l'etape 4
    if not sample_points_existe and not pass_compute_model and nb_input_images==1 :

        # 4. EXTRACTION DES POINTS D'ECHANTILLONS
        #----------------------------------------

        print(cyan + "classifySupervised() : " + bold + green + "Extract values on samples points from image %s  ..." %(image_input) + endC)

        # Vérification de l'existence du vecteur de points selectionés pour extraire les valeurs
        if not os.path.isfile(sample_points_resample_polygons_output):
            raise NameError(cyan + "classifySupervised() : " + bold + red + "No sample points %s available.\n" %(sample_points_resample_polygons_output) + endC)

        # Si le fichier points d'echantillons valeurs existe deja et que overwrite n'est pas activé
        check = os.path.isfile(sample_points_values_output)
        if check and not overwrite:
            print(bold + yellow + "Extracted values samples already done for file %s and will not be calculated again." %(sample_points_values_output) + endC)
        else:   # Si non ou si la vérification est désactivée : extraction des valeurs des échantillons

            # Suppression de l'éventuel fichier existant
            if check:
                try:
                    removeFile(sample_points_values_output)
                except Exception:
                    pass # Si le fichier ne peut pas être supprimé, on suppose qu'il n'existe pas et on passe à la suite

            # Extract sample
            command = "otbcli_SampleExtraction -in %s -vec %s -outfield prefix -outfield.prefix.name %s -out %s -field %s" %(image_input, sample_points_resample_polygons_output, BAND_NAME, sample_points_values_output, field_class)
            if ram_otb > 0:
                command += " -ram %d" %(ram_otb)

            if debug >= 3:
                print(command)

            exitCode = os.system(command)
            if exitCode != 0:
                raise NameError(cyan + "classifySupervised() : " + bold + red + "An error occured during otbcli_SampleExtraction command. See error message above." + endC)

            print(cyan + "classifySupervised() : " + bold + green + "Values samples are extracted." + endC)

    # Test si on execute l'etape 5
    if not pass_compute_model:

        # 5.CREATION DU MODEL
        #--------------------

        print(cyan + "classifySupervised() : " + bold + green + "Classification model computation for input images ..." + endC)

        # Vérification de l'existence du vecteur de valeurs d'entrainement pour creer le modèle de classification
        if not os.path.isfile(sample_points_values_output):
            raise NameError(cyan + "classifySupervised() : " + bold + red + "No training vector %s available.\n" %(sample_points_values_output) + endC)

        # Vérification de l'existence du fichier statistique pour creer le modèle de classification
        if not os.path.isfile(statistics_image_output):
            raise NameError(cyan + "classifySupervised() : " + bold + red + "No statistics file %s available.\n" %(statistics_image_output) + endC)

        # Si modèle de classification associé à l'image existe deja et que overwrite n'est pas activé
        check = os.path.isfile(model_file_output)
        if check and not overwrite:
            print(cyan + "classifySupervised() : " + bold + yellow + "Model %s already computed and will not be calculated again." %(model_file_output) + endC)
        else: # Si non ou si la vérification est désactivée : calcul du model pour la classification

            # Suppression de l'éventuel fichier existant
            if check:
                try:
                    removeFile(model_file_output)
                except Exception:
                    pass # Si le fichier ne peut pas être supprimé, on suppose qu'il n'existe pas et on passe à la suite

            # Récupération des champs utiles pour le calcul du model
            cols, rows, bands = getGeometryImage(image_input)
            feat_list = []
            for i in range(bands) :
                feat_list.append(BAND_NAME + str(i))

            # Calcul du model en fonction de l'algo choisi
            if classifier_mode.lower() == "rf" :
                computeModelRF(sample_points_values_output, statistics_image_output, model_file_output, matrix_file_output, field_class, feat_list, rf_parametres_struct)
            else :
                computeModelSVM(sample_points_values_output, statistics_image_output, model_file_output, matrix_file_output, field_class, feat_list, kernel.lower())

            print(cyan + "classifySupervised() : " + bold + green + "Model are ready." + endC)

    # 6. CLASSIFICATION DE L'IMAGE
    #-----------------------------

    print(cyan + "classifySupervised() : " + bold + green + "Classification image creation for input images with model %s ..." %(model_file_output) + endC)

    # Vérification de l'existence du fichier modèle pour faire la classification
    if not os.path.isfile(model_file_output):
        raise NameError (cyan + "classifySupervised() : " + bold + red + '\n' + "No classification model %s available." %(model_file_output) + endC)

    # Si la classification existe deja et que overwrite n'est pas activé
    check = os.path.isfile(classification_file_output)
    if check and not overwrite:
        print(cyan + "classifySupervised() : " + bold + yellow + "Classification image %s already computed and will not be create again."  %(classification_file_output) + endC)
    else: # Si non ou si la vérification est désactivée : création de la classification

        # Suppression de l'éventuel fichier existant
        if check:
            try:
                removeFile(classification_file_output)
            except Exception:
                pass # Si le fichier ne peut pas être supprimé, on suppose qu'il n'existe pas et on passe à la suite

        # Tempo attente fin d'ecriture du model sur le disque
        time.sleep(5)

        # Pour toutes les images d'entrée à classer
        classification_file_output_list = []
        for image_input_tmp in image_input_list :
            if nb_input_images == 1 :
                classification_file_output_tmp = classification_file_output
            else :
                 image_name =  os.path.splitext(os.path.basename(image_input_tmp))[0]
                 classification_file_output_tmp = os.path.splitext(classification_file_output)[0] + "_" + image_name + os.path.splitext(classification_file_output)[1]
                 classification_file_output_list.append(classification_file_output_tmp)

            # Création de la classification
            command = "otbcli_ImageClassifier -in %s -imstat %s -model %s -out %s %s" %(image_input_tmp, statistics_image_output, model_file_output, classification_file_output_tmp, CODAGE_16B)

            if confidence_file_output != "" :
                command += " -confmap %s %s" %(confidence_file_output, CODAGE_F)

            if ram_otb > 0:
                command += " -ram %d" %(ram_otb)

            if debug >= 3:
                print(command)

            exitCode = os.system(command)
            if exitCode != 0:
                raise NameError(cyan + "classifySupervised() : " + bold + red + "An error occured during otbcli_ImageClassifier command. See error message above." + endC)

            # Bug OTB mise a jour de la projection du résultat de la classification
            updateReferenceProjection(image_input_tmp, classification_file_output_tmp)

        # Si plusieurs images demander fusion des classifications
        if nb_input_images > 1 :

            file_name = os.path.splitext(os.path.basename(classification_file_output))[0]
            pixel_size_x, pixel_size_y = getPixelWidthXYImage(image_input)

            # Fichier txt temporaire liste des fichiers a merger
            list_file_tmp = repertory_output + os.sep + file_name + SUFFIX_MERGE + EXT_TEXT

            for classification_file_output_tmp in classification_file_output_list:
                appendTextFileCR(list_file_tmp, classification_file_output_tmp)

            cmd_merge = "gdal_merge" + getExtensionApplication() + " -of " + format_raster + " -ps " + str(pixel_size_x) + " " + str(pixel_size_y) + " -n " + str(no_data_value) + " -o "  + classification_file_output + " --optfile " + list_file_tmp
            print(cmd_merge)
            exit_code = os.system(cmd_merge)
            if exit_code != 0:
                raise NameError(cyan + "classifySupervised() : " + bold + red + "!!! Une erreur c'est produite au cours du merge des classification. Voir message d'erreur."  + endC)

        print(cyan + "classifySupervised() : " + bold + green + "Classification complete." + endC)


    # 7. SUPPRESSION DES FICHIERS INTERMEDIAIRES
    #-------------------------------------------

    # Suppression des données intermédiaires
    if not save_results_intermediate:
        if model_output == "" and model_input == "" and os.path.isfile(model_file_output) :
            removeFile(model_file_output)
        removeVectorFile(sample_points_resample_polygons_output)

        if nb_input_images > 1 :
            removeFile(list_file_tmp)
            for classification_file_output_tmp in classification_file_output_list :
                removeFile(classification_file_output_tmp)

    print(endC)
    print(bold + green + "## END :  SUPERVISED CLASSIFICATION" + endC)
    print(endC)

    # Mise à jour du Log
    ending_event = "classifySupervised() : Classifiy supervised ending : "
    timeLine(path_time_log,ending_event)

    return

###########################################################################################################################################
# MISE EN PLACE DU PARSER                                                                                                                 #
###########################################################################################################################################

# Code executé seulement dans le cas ou le script est lancé depuis une ligne de commande
# Il n'est pas executé lors d'un import SupervisedClassification.py
# Exemple de lancement en ligne de commande:
# python SupervisedClassification.py -il ../ImagesTestChaine/APTV_05/Stacks/APTV_05_stack.tif -v ../ImagesTestChaine/APTV_05/Micro/APTV_05_cleaned.shp -o ../ImagesTestChaine/APTV_05/Micro/APTV_05_stack_raw.tif -mt -1 -mv 0 -vtr 0 -vfn id -k linear -log ../ImagesTestChaine/APTV_05/fichierTestLog.txt
# python SupervisedClassification.py -il ../ImagesTestChaine/APTV_05/Stacks/APTV_05_stack.tif -v ../ImagesTestChaine/APTV_05/Micro/APTV_05_cleaned.shp -o ../ImagesTestChaine/APTV_05/Micro/APTV_05_stack_raw.tif -rf -mt -1 -mv 0 -vtr 0 -vfn id -depth 50 -min 20 -crit 0.0 -clust 30 -size 2 -num 50 -obb 0.001 -log ../ImagesTestChaine/APTV_05/fichierTestLog.txt
# python SupervisedClassification.py -il /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/Stacks/CUB_zone_test_NE_stack.tif -v /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/Micro/CUB_zone_test_NE_cleaned.shp  -o /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_2/Micro/CUB_zone_test_NE_stack_rf.tif -rf -mt -1 -mv 0 -vtr 0 -vfn id -depth 50 -min 20 -crit 0.0 -clust 30 -size 2 -num 50 -obb 0.001 -log /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_2/fichierTestLog.txt

def main(gui=False):

    # Définition des arguments possibles pour l'appel en ligne de commande
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, prog="SupervisedClassification", description="\
    Info : Supervised classification. \n\
    Objectif : Execute une classification supervisee SVM sur des images (brutes ou avec neocanaux) en se basant sur des echantillons d'entrainement vectorises. \n\
    Example svn : python SupervisedClassification.py -il ../ImagesTestChaine/APTV_05/Stacks/APTV_05_stack.tif \n\
                                                     -v ../ImagesTestChaine/APTV_05/Micro/APTV_05_cleaned.shp \n\
                                                     -o ../ImagesTestChaine/APTV_05/Micro/APTV_05_stack_raw.tif \n\
                                                     -c ../ImagesTestChaine/APTV_05/Micro/APTV_05_stack_confidence.tif \n\
                                                     -cm svm -fc id \n\
                                                     -svm.k linear \n\
                                                     -log ../ImagesTestChaine/APTV_05/fichierTestLog.txt \n\
    Example rf  : python SupervisedClassification.py -il ../ImagesTestChaine/APTV_05/Stacks/APTV_05_stack.tif \n\
                                                     -v ../ImagesTestChaine/APTV_05/Micro/APTV_05_cleaned.shp \n\
                                                     -o ../ImagesTestChaine/APTV_05/Micro/APTV_05_stack_raw.tif \n\
                                                     -c ../ImagesTestChaine/APTV_05/Micro/APTV_05_stack_confidence.tif \n\
                                                     -cm rf -fc id \n\
                                                     -rf.depth 50 -rf.min 20 -rf.crit 0.0 -rf.clust 30 -rf.size 2 -rf.num 50 -rf.obb 0.001 \n\
                                                     -log ../ImagesTestChaine/APTV_05/fichierTestLog.txt")

    # Paramètres
    parser.add_argument('-il','--image_input_list',default=[],nargs="+",help="List images input to classify", type=str, required=True)
    parser.add_argument('-v','--vector_input',default="",help="Vector input contain the samples polygons", type=str, required=False)
    parser.add_argument('-s','--sample_input',default="",help="Vector input contain the samples points with values", type=str, required=False)
    parser.add_argument('-se','--sample_emply_input',default="",help="Vector input contain the samples points without values", type=str, required=False)
    parser.add_argument('-o','--image_output',default="",help="Image output result of classification in micro class", type=str, required=True)
    parser.add_argument('-c','--confidence_file_output',default="",help="Image output confidence of classification, if empty not generate ", type=str, required=False)
    parser.add_argument('-mo','--model_output',default="",help="Save model output result of classification algorithm", type=str, required=False)
    parser.add_argument('-mi','--model_input',default="",help="Use model imput to create classification map, in this case the model is not generated", type=str, required=False)
    parser.add_argument('-fc','--field_class',default="id",help="Name of the field contain the id class", type=str, required=False)
    parser.add_argument('-sm','--sampler_mode',default="random",help="Choice mode of select sample (Choice of : 'periodic' or 'random'). By default, 'random'", type=str, required=False)
    parser.add_argument('-per','--periodic_value',default=0,help="Parameter of sampler mode 'periodic'", type=int, required=False)
    parser.add_argument('-cm','--classifier_mode',default="rf",help="Choice type of algo classification (Choice of : 'svm' or 'rf'). By default, 'rf' (random forest)", type=str, required=False)
    parser.add_argument('-svm.k','--kernel',default="linear",help="kernel, svm parameter algo (Choice of : 'linear', 'rbf', 'poly', 'sigmoid'). By default, 'linear'", type=str, required=False)
    parser.add_argument('-rf.depth','--depth_tree',default=50,help="depth_tree, random forest parameter", type=int, required=False)
    parser.add_argument('-rf.min','--sample_min',default=20,help="sample_min, random forest parameter", type=int, required=False)
    parser.add_argument('-rf.crit','--termin_criteria',default=0.0,help="termin_criteria, random forest parameter", type=float, required=False)
    parser.add_argument('-rf.clust','--cluster',default=30,help="cluster, random forest parameter", type=int, required=False)
    parser.add_argument('-rf.size','--size_features',default=2,help="size_features, random forest parameter", type=int, required=False)
    parser.add_argument('-rf.num','--num_tree',default=50,help="num_tree, random forest parameter", type=int, required=False)
    parser.add_argument('-rf.obb','--obb_erreur',default=0.001,help="obb_erreur, random forest parameter", type=float, required=False)
    parser.add_argument('-ram','--ram_otb',default=0,help="Ram available for processing otb applications (in MB)", type=int, required=False)
    parser.add_argument('-ndv','--no_data_value', default=0, help="Option : Value of the pixel no data. By default : 0", type=int, required=False)
    parser.add_argument('-raf','--format_raster', default="GTiff", help="Option : Format output image, by default : GTiff (GTiff, HFA...)", type=str, required=False)
    parser.add_argument('-vee','--extension_vector',default=".shp",help="Option : Extension file for vector. By default : '.shp'", type=str, required=False)
    parser.add_argument('-log','--path_time_log',default="",help="Name of log", type=str, required=False)
    parser.add_argument('-sav','--save_results_inter',action='store_true',default=False,help="Save or delete intermediate result after the process. By default, False", required=False)
    parser.add_argument('-now','--overwrite',action='store_false',default=True,help="Overwrite files with same names. By default, True", required=False)
    parser.add_argument('-debug','--debug',default=3,help="Option : Value of level debug trace, default : 3 ",type=int, required=False)
    args = displayIHM(gui, parser)

    # RECUPERATION DES ARGUMENTS
    # Récupération de l'image d'entrée
    if args.image_input_list != None:
        image_input_list = args.image_input_list
        for image_input in image_input_list :
            if not os.path.isfile(image_input):
                raise NameError (cyan + "SupervisedClassification : " + bold + red  + "File %s not existe!" %(image_input) + endC)

    # Récupération du fichier vecteur d'entrée
    vector_input = None
    if args.vector_input != "":
        vector_input = args.vector_input
        if vector_input != "" and not os.path.isfile(vector_input):
            raise NameError (cyan + "SupervisedClassification : " + bold + red  + "File %s not existe!" %(vector_input) + endC)

    # Récupération du fichier d'échantillons points d'entrée
    sample_input = None
    if args.sample_input != "":
        sample_input = args.sample_input
        if vector_input != "" and not os.path.isfile(sample_input):
            raise NameError (cyan + "SupervisedClassification : " + bold + red  + "File %s not existe!" %(sample_input) + endC)

    # Récupération du fichier d'échantillons points d'entrée vides
    sample_emply_input = None
    if args.sample_emply_input != "":
        sample_emply_input = args.sample_emply_input
        if vector_input != "" and not os.path.isfile(sample_emply_input):
            raise NameError (cyan + "SupervisedClassification : " + bold + red  + "File %s not existe!" %(sample_emply_input) + endC)

    if (vector_input == None or vector_input == "") and (sample_input == None or sample_input == ""):
        raise NameError(cyan + "SupervisedClassification : " + bold + red + "Parameters 'vector_input' is emply and 'sample_input' is emply" + endC)

    if (sample_input != "") and (sample_emply_input != ""):
        print(cyan + "SupervisedClassification : " + bold + yellow + "WARNING Parameters 'sample_input' is not emply and 'sample_emply_input' is not emply => sample_input not used!!! " + endC)

    # Récupération des images de classificassion et de confiance de sortie
    if args.image_output != None:
        image_output = args.image_output

    if args.confidence_file_output != None:
        confidence_file_output = args.confidence_file_output

    # Récupération des parametres du mon du model input et output
    if args.model_output != None:
        model_output = args.model_output

    if args.model_input != None:
        model_input = args.model_input

    # Récupération des parametres
    if args.field_class != None:
        field_class = args.field_class

    # Récupération des parametres selection des échantillons
    if args.sampler_mode != None:
        sampler_mode = args.sampler_mode
        if sampler_mode.lower() not in ['periodic', 'random'] :
            raise NameError(cyan + "SupervisedClassification : " + bold + red + "Parameter 'sampler_mode' value  is not in list ['periodic', 'random']." + endC)

    if args.periodic_value != None:
        periodic_value = args.periodic_value

    # Récupération choix du classifieur
    if args.classifier_mode != None:
        classifier_mode = args.classifier_mode
        if classifier_mode.lower() not in ['svm', 'rf'] :
            raise NameError(cyan + "SupervisedClassification : " + bold + red + "Parameter 'classifier_mode' value  is not in list ['svm', 'rf']." + endC)

    # Récupération des parametres du SVM
    if args.kernel != None:
        kernel = args.kernel
        if kernel.lower() not in ['linear', 'rbf', 'poly', 'sigmoid'] :
            raise NameError(cyan + "SupervisedClassification : " + bold + red + "Parameter 'kernel' value  is not in list ['linear', 'rbf', 'poly', 'sigmoid']." + endC)

    # Récupération des parametres du random forest
    if args.depth_tree != None:
        depth_tree = args.depth_tree

    if args.sample_min != None:
        sample_min = args.sample_min

    if args.termin_criteria != None:
        termin_criteria = args.termin_criteria

    if args.cluster != None:
        cluster = args.cluster

    if args.size_features != None:
        size_features = args.size_features

    if args.num_tree != None:
        num_tree = args.num_tree

    if args.obb_erreur != None:
        obb_erreur = args.obb_erreur

    # Récupération du parametre ram
    if args.ram_otb != None:
        ram_otb = args.ram_otb

    # Parametres de valeur du nodata
    if args.no_data_value!= None:
        no_data_value = args.no_data_value

    # Paramètre format des images de sortie
    if args.format_raster != None:
        format_raster = args.format_raster

    # Récupération de l'extension des fichiers vecteurs
    if args.extension_vector != None:
        extension_vector = args.extension_vector

    # Récupération du nom du fichier log
    if args.path_time_log!= None:
        path_time_log = args.path_time_log

    # Ecrasement des fichiers
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
        print(cyan + "SupervisedClassification : " + endC + "image_input_list : " + str(image_input_list) + endC)
        print(cyan + "SupervisedClassification : " + endC + "vector_input : " + str(vector_input) + endC)
        print(cyan + "SupervisedClassification : " + endC + "sample_input : " + str(sample_input) + endC)
        print(cyan + "SupervisedClassification : " + endC + "sample_emply_input : " + str(sample_emply_input) + endC)
        print(cyan + "SupervisedClassification : " + endC + "image_output : " + str(image_output) + endC)
        print(cyan + "SupervisedClassification : " + endC + "confidence_file_output : " + str(confidence_file_output) + endC)
        print(cyan + "SupervisedClassification : " + endC + "model_output : " + str(model_output) + endC)
        print(cyan + "SupervisedClassification : " + endC + "model_input : " + str(model_input) + endC)
        print(cyan + "SupervisedClassification : " + endC + "field_class : " + str(field_class) + endC)
        print(cyan + "SupervisedClassification : " + endC + "sampler_mode : " + str(sampler_mode) + endC)
        print(cyan + "SupervisedClassification : " + endC + "periodic_value : " + str(periodic_value) + endC)
        print(cyan + "SupervisedClassification : " + endC + "classifier_mode : " + str(classifier_mode) + endC)
        print(cyan + "SupervisedClassification : " + endC + "kernel : " + str(kernel) + endC)
        print(cyan + "SupervisedClassification : " + endC + "depth_tree : " + str(depth_tree) + endC)
        print(cyan + "SupervisedClassification : " + endC + "sample_min : " + str(sample_min) + endC)
        print(cyan + "SupervisedClassification : " + endC + "termin_criteria : " + str(termin_criteria) + endC)
        print(cyan + "SupervisedClassification : " + endC + "cluster : " + str(cluster) + endC)
        print(cyan + "SupervisedClassification : " + endC + "size_features : " + str(size_features) + endC)
        print(cyan + "SupervisedClassification : " + endC + "num_tree : " + str(num_tree) + endC)
        print(cyan + "SupervisedClassification : " + endC + "obb_erreur : " + str(obb_erreur) + endC)
        print(cyan + "SupervisedClassification : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "SupervisedClassification : " + endC + "ram_otb : " + str(ram_otb) + endC)
        print(cyan + "SupervisedClassification : " + endC + "format_raster : " + str(format_raster) + endC)
        print(cyan + "SupervisedClassification : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "SupervisedClassification : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "SupervisedClassification : " + endC + "save_results_inter : " + str(save_results_intermediate) + endC)
        print(cyan + "SupervisedClassification : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "SupervisedClassification : " + endC + "debug : " + str(debug) + endC)

    # EXECUTION DE LA FONCTION
    # Si le dossier de sortie n'existe pas, on le crée
    repertory_output = os.path.dirname(image_output)
    if not os.path.isdir(repertory_output):
        os.makedirs(repertory_output)
    repertory_output = os.path.dirname(confidence_file_output)
    if repertory_output != "" and not os.path.isdir(repertory_output):
        os.makedirs(repertory_output)
    repertory_output = os.path.dirname(model_output)
    if repertory_output != "" and not os.path.isdir(repertory_output):
        os.makedirs(repertory_output)

    # Regroupement des parametres du RF dans une structure
    rf_parametres_struct = StructRFParameter()
    rf_parametres_struct.max_depth_tree = depth_tree
    rf_parametres_struct.min_sample = sample_min
    rf_parametres_struct.ra_termin_criteria = termin_criteria
    rf_parametres_struct.cat_clusters = cluster
    rf_parametres_struct.var_size_features = size_features
    rf_parametres_struct.nbtrees_max =  num_tree
    rf_parametres_struct.acc_obb_erreur = obb_erreur

    # Execution de la fonction pour une image
    classifySupervised(image_input_list, vector_input, sample_input, sample_emply_input, image_output, confidence_file_output, model_output, model_input, field_class, sampler_mode, periodic_value, classifier_mode, kernel, rf_parametres_struct, no_data_value, path_time_log, ram_otb, format_raster, extension_vector, save_results_intermediate, overwrite)

# ================================================

if __name__ == '__main__':
  main(gui=False)
