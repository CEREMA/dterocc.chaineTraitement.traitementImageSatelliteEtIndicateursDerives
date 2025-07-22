#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.               #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT QUI APPLIQUE UNE DETECTION D'OBJET PAR RESEAU DE NEURONES MASK R-CNN                                                               #
#                                                                                                                                           #
#############################################################################################################################################
"""
Nom de l'objet : MaskRcnnDetection.py
Description :
Objectif : exécute une détéction segmentation, d'objet quelque soit-il, via un réseaux de neurones Mask R6CNN sur des images découpées d'une seule image satellite

Date de creation : 22/03/2023
----------
Histoire :
----------
Origine : le script originel provient du regroupement des fichiers jupyter de Mask R-CNN
https://github.com/matterport/Mask_RCNN
https://github.com/akTwelve/Mask_RCNN
https://github.com/BupyeongHealer/Mask_RCNN_tf_2.x
https://github.com/leekunhee/Mask_RCNN/tree/tensorflow2.0
https://www.aicrowd.com/challenges/mapping-challenge/dataset_files
-----------------------------------------------------------------------------------------------------
Modifications

------------------------------------------------------
"""
# Import Générale
import os
os.environ['USE_PYGEOS'] = '0'
import glob,sys,string,shutil,time,argparse, threading
import random as rd

# Import Image et Geomatique
import numpy as np
import skimage.io
import pandas
import geopandas
import shapely
from osgeo import gdal
from osgeo import ogr
from osgeo.gdalnumeric import *
from osgeo.gdalconst import *
from datetime import datetime

# Import Mask RCNN
import tensorflow as tf
import tensorflow.keras as keras
from mrcnn.evaluate import build_coco_results, evaluate_coco
from mrcnn.dataset import MappingChallengeDataset
from mrcnn.config import Config
from mrcnn import model as modellib, utils
from mrcnn import visualize

# Import Libs OSECC
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_log import timeLine
from Lib_file import moveVectorFile, deleteDir
from Lib_text import writeTextFile
from Lib_raster import getProjectionImage, getEmpriseImage, getPixelWidthXYImage, getGeometryImage, computeStatisticsImage
from Lib_vector import saveVectorFromDataframe, getNumberFeature, getGeomPolygons
from DeepForestDetection import decoupeImageTraining

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 3

###########################################################################################################################################
# STRUCTURE StructMAskRCnnParameter                                                                                                       #
###########################################################################################################################################

class StructMAskRCnnParameter:
    """
    # Structure contenant les parametres utiles au calcul du Reseau de neurones MaskR-CNN
    """
    def __init__(self):

        # Hyperparameters RCNN
        self.neural_network_mode = ""
        self.number_epoch = 0
        self.number_steps_per_epoch = 0
        self.number_validation_steps = 0
        self.learning_rate_factor = 0.0
        self.learning_momentun_factor = 0.0
        self.detection_max_instances = 0
        self.detection_min_confidence = 0.0
        self.detection_mns_threshold = 0.0

###########################################################################################################################################
# STRUCTURE ModelConfig                                                                                                                   #
###########################################################################################################################################
class ModelConfig(Config):
    """
    # Structure contenant les parametres de configurarttion du Reseau de neurones MaskR-CNN
    """
    # Set batch size to 1 since we'll be running inference on
    # one image at a time. Batch size = GPU_COUNT * IMAGES_PER_GPU
    NAME = "Cerema-detect-build"
    GPU_COUNT = 1
    IMAGES_PER_GPU = 2
    BACKBONE = "resnet101"
    NUM_CLASSES = 1 + 1  # 1 Background + 1 Building
    IMAGE_MAX_DIM=320
    IMAGE_MIN_DIM=320
    IMAGE_CHANNEL_COUNT = 4
    MEAN_PIXEL = np.array([408.6, 430.7, 469.7, 837.7])
    BATCH_SIZE = 0
    STEPS_PER_EPOCH=1000
    VALIDATION_STEPS=100
    LEARNING_RATE = 0.001
    LEARNING_MOMENTUM = 0.9
    DETECTION_MAX_INSTANCES = 100
    DETECTION_MIN_CONFIDENCE = 0.7
    DETECTION_NMS_THRESHOLD = 0.3

###########################################################################################################################################
#                                                                                                                                         #
# PARTIE Fonctions utiles pour l'application MaskRcnnDetection                                                                            #
#                                                                                                                                         #
###########################################################################################################################################


###########################################################################################################################################
#                                                                                                                                         #
# PARTIE MODEL GENERATOR (génération des données pour les mettre en entrée du réseau de neurones et entrainement du reseau)               #
#                                                                                                                                         #
###########################################################################################################################################

###########################################################################################################################################
# FONCTION createAnnotationJsonFile()                                                                                                     #
###########################################################################################################################################
def createAnnotationJsonFile(data_imagettes_vector_dico, file_annotation, categorie_id, categorie_name, extension_raster=".tif", extension_vector=".shp", format_raster='GTiff', format_vector='ESRI Shapefile',  overwrite=True):
    """
    # ROLE:
    #    Creer à partir d'images et de shape de contour associer un fichier d'annotation au format coco de type JSON
    #
    # ENTREES DE LA FONCTION :

    #    data_imagettes_vector_dico (dico) : repertoire contenant les imagettes de l'image satellite et le vecteur associer contenant les polygones d'apprentissage
    #    file_annotation (string) : fichier json de sortie contenant les informations d'apprentissage
    #    categorie_id (int) : identifiant indiquant le type de categorie d'objet
    #    categorie_name (string) : nom associer a l'identifiant indiquant le type de categorie d'objet
    #    extension_raster (string) : extension de fichier des imagettes
    #    extension_vector (string) : extension de fichier des vecteurs
    #    format_raster (string) : format des imagettes
    #    format_vector (string) : format des vecteurs
    #    overwrite (bool) : booléen pour écrire ou non par dessus un fichier existant
    #
    # SORTIES DE LA FONCTION :
    #    Renvoie un fichier JSON au format coco contenant les informations d'apprentissage
    """

    CONTRIBUTEUR = "cerema.fr"
    COMMENTAIRE = "Dataset for buid detection"
    DESCRIPTION = "build from bdTopo IGN dataset"
    URL_CEREMA = "https://www.cerema.fr/fr"
    NUM_VERSION = "1.0"

    # Préparartion de la partie images
    images_txt = ""
    image_id = 10000
    for imagette_elem in data_imagettes_vector_dico.keys() :
        # Creation du texte
        image_name = os.path.splitext(os.path.basename(imagette_elem))[0]
        extension = os.path.splitext(imagette_elem)[1]
        width_image, height_image, _ = getGeometryImage(imagette_elem)
        images_txt += '{"id": ' + str(image_id) + ', "file_name": "' + image_name + extension + '", "width": ' + str(width_image) + ', "height": ' + str(height_image) + '}, '
        image_id += 10000
    images_txt = images_txt[:-2]

    # Préparartion de la partie anotations
    annotations_txt = ""
    image_id = 10000
    for imagette_elem, sample_elem in data_imagettes_vector_dico.items() :
        if os.path.isfile(sample_elem):

            # Test si une geometry existe
            nb_feature = getNumberFeature(sample_elem, format_vector)

            if nb_feature > 0 :
                # Info image
                xmin_image, xmax_image, ymin_image, ymax_image = getEmpriseImage(imagette_elem)
                pixel_width, pixel_height = getPixelWidthXYImage(imagette_elem)

                # Info vecteur entrainement
                geometry_list = getGeomPolygons(sample_elem, col=None, value=None, format_vector=format_vector)
                annotation_id = image_id * 200
                geometry_polygon_list = []
                for geometry in geometry_list :
                    geomType = geometry.GetGeometryType()
                    if geometry.GetGeometryType() == ogr.wkbPolygon :
                        geometry_polygon_list.append(geometry)
                    elif geometry.GetGeometryType() == ogr.wkbMultiPolygon :
                        for geometry_part in geometry:
                            geometry_polygon_list.append(geometry_part)

                for geometry in geometry_polygon_list :
                    other_occluded_polygon_list = []
                    STR_OTHER_POLYGON = "),("
                    if STR_OTHER_POLYGON in str(geometry) :
                        geometry_str = str(geometry)[:str(geometry).find(STR_OTHER_POLYGON)] + "))"
                        geometry_other_str = str(geometry)[str(geometry).find(STR_OTHER_POLYGON)+3:-2]
                        other_occluded_polygon_list = geometry_other_str.split(STR_OTHER_POLYGON)
                    else :
                        geometry_str = str(geometry)

                    text_points_list = geometry_str.replace("POLYGON ((", "").replace("))","").split(",")
                    surface_pixel = round(float(geometry.GetArea()) / (float(pixel_width) * float(pixel_height)))
                    points_x_list = []
                    points_y_list = []
                    for text_points in text_points_list :
                        info_list = text_points.split(" ")
                        points_x_list.append((float(info_list[0]) - float(xmin_image)) / pixel_width)
                        points_y_list.append(height_image - ((float(info_list[1]) - float(ymin_image)) / pixel_height))

                    if debug >= 6:
                        print(points_x_list)
                        print(points_y_list)

                    x_min = min(points_x_list)
                    x_max = max(points_x_list)
                    y_min = min(points_y_list)
                    y_max = max(points_y_list)
                    width = float(round(x_max - x_min))
                    height = float(round(y_max - y_min))
                    x = float(round(x_min))
                    y = float(round(y_min))

                    list_point_xy_str = ""
                    for pos in range(len(points_x_list)) :
                        list_point_xy_str += str(float(round(points_x_list[pos]))) + ", " + str(float(round(points_y_list[pos]))) + ", "
                    list_point_xy_str = list_point_xy_str[:-2]

                    list_other_all_point_xy_str = ""
                    if len(other_occluded_polygon_list) != 0 :
                        for polygon_str in other_occluded_polygon_list :
                            text_points_list = polygon_str.split(",")
                            points_x_list = []
                            points_y_list = []
                            for text_points in text_points_list :
                                info_list = text_points.split(" ")
                                points_x_list.append((float(info_list[0]) - float(xmin_image)) / pixel_width)
                                points_y_list.append(height_image - ((float(info_list[1]) - float(ymin_image)) / pixel_height))
                                list_other_point_xy_str = ""
                                for pos in range(len(points_x_list)) :
                                    list_other_point_xy_str += str(float(round(points_x_list[pos]))) + ", " + str(float(round(points_y_list[pos]))) + ", "
                            list_other_point_xy_str = ", [" + list_other_point_xy_str[:-2] + "]"
                            if debug >= 6:
                                print(list_other_point_xy_str)
                            list_other_all_point_xy_str += list_other_point_xy_str


                    # Creation du texte
                    annotations_txt += '{"id": ' + str(annotation_id) + ', "image_id": ' + str(image_id) + ', "segmentation": [['  + list_point_xy_str + ']' + list_other_all_point_xy_str + '], "area": ' + str(surface_pixel) + ', "bbox": [' + str(x) + ', ' + str(y) + ', ' + str(width) + ', ' + str(height) + '], "category_id": ' + str(categorie_id) + ', "iscrowd": 0}, '
                    annotation_id += 1

                image_id += 10000
        else :
           raise NameError (cyan + "CreateAnnotationFile : " + bold + red  + "File %s not existe!" %(sample_elem) + endC)

    if len(annotations_txt) > 1 :
        annotations_txt = annotations_txt[:-2]

    # Composition du text et ecriture dans le fichier
    text = '{"info": {"contributor": "' + CONTRIBUTEUR + '", "about": "' + COMMENTAIRE + '", "date_created": "' + datetime.today().strftime('%d-%m-%Y') + '", "description": "' + DESCRIPTION + '", "url": "' + URL_CEREMA + '", "version": "' + NUM_VERSION + '", "year": ' + datetime.today().strftime('%Y') + '}, "categories": [{"id": ' + str(categorie_id) + ', "name": "' + categorie_name + '", "supercategory": "' + categorie_name + '"}], "images": [' + images_txt + '], "annotations": [' + annotations_txt + ']}'
    writeTextFile(file_annotation, text)

    return

###########################################################################################################################################
# FONCTION sortFileTrainAndValidation()                                                                                                   #
###########################################################################################################################################
def sortFileTrainAndValidation(rep_imagettes_input, rep_samples_input, input_image_path_list, input_sample_vector_path_list, percent_no_data, percent_validation_split, rep_imagettes_train_output, rep_samples_train_output, rep_imagettes_val_output, rep_samples_val_output, extension_vector=".shp", format_vector='ESRI Shapefile', save_results_intermediate=False) :
    """
    # ROLE:
    #    Trie les données d'apprentissage découpées en deux partie une pour l'entrainement et une pour la validation
    #    en fonction du parametre percent_validation_split
    #
    # ENTREES DE LA FONCTION :
    #    rep_imagettes_input (string) : répertoire d'entrée contenant les imagettes de decoupées
    #    rep_samples_input (string) : répertoire d'entrée contenant les vecteurs d'apprentissage
    #    input_image_path_list (list) : la liste des imagettes de decoupées
    #    input_sample_vector_path_list (list) : la liste des vecteurs d'apprentissage correspondanr aux imagettes
    #    percent_no_data (int) : pourcentage de no data
    #    percent_validation_split (int) : pourcentage de donnée validation / entrainement
    #    rep_imagettes_train_output (string) : répertoire de sortie acceuillant les imagettes pour la partie training
    #    rep_samples_train_output (string) : répertoire de sortie acceuillant les echantillons d'apprentissage pour la partie training
    #    rep_imagettes_val_output (string) : répertoire de sortie acceuillant les imagettes pour la partie validation
    #    rep_samples_val_output (string) :  répertoire de sortie acceuillant les echantillons d'apprentissage pour la partie validation
    #    extension_vector (string) : extension de fichier des vecteurs
    #    format_vector (string) : format des vecteurs
    #    save_results_intermediate (bool) : booléen qui determine si on sauvegarde ou non les fichiers temporaires
    #
    # SORTIES DE LA FONCTION :
    #    output_data_path_train_dico : dictonaire contenant le duo imagette - sample(vector) pour le training
    #    output_data_path_val_dico : dictonaire contenant le duo imagette - sample(vector) pour la validation
    #
    """

    # Creation des repertoires de sortie si ils n'existent pas
    if not os.path.isdir(rep_imagettes_train_output):
        os.makedirs(rep_imagettes_train_output)
    if not os.path.isdir(rep_samples_train_output):
        os.makedirs(rep_samples_train_output)
    if not os.path.isdir(rep_imagettes_val_output):
        os.makedirs(rep_imagettes_val_output)
    if not os.path.isdir(rep_samples_val_output):
        os.makedirs(rep_samples_val_output)

    # Parcours des imagettes et creer un dico des données d'apprentissage
    nb_element = len(input_image_path_list)
    if debug >= 4:
       print(cyan + "sortFileTrainAndValidation() : " + bold + green + "Number element data sample to sort is %s" %(str(nb_element)) + endC)
    data_path_dico = {}
    empty_imagette_path_list = []
    for index, imagette_elem in enumerate(input_image_path_list):
        sample_elem = input_sample_vector_path_list[index]
        data_path_dico[imagette_elem] = sample_elem
        # Recherche des imagettes-samples sans données
        if (getNumberFeature(sample_elem, format_vector) == 0) :
            empty_imagette_path_list.append(imagette_elem)

    # Si le nombre d'elemnt vide est trop important en supprimer
    number_nodata_element_max = round(nb_element * (percent_no_data / 100))
    number_empty_element = len(empty_imagette_path_list)
    if number_empty_element > number_nodata_element_max :
        empty_supress_imagette_path_list = rd.sample(empty_imagette_path_list, k=(number_empty_element - number_nodata_element_max))
        [data_path_dico.pop(key) for key in empty_supress_imagette_path_list]

    # Répartition des données de training et de validation selon la valeur de percent_validation_split
    val_image_path_list = rd.sample(list(data_path_dico.keys()), k=round((1 - (percent_validation_split / 100)) * len(data_path_dico)))
    train_image_path_list = list(set(data_path_dico.keys()) - set(val_image_path_list))
    data_path_val_dico = data_path_dico.copy()
    [data_path_val_dico.pop(key) for key in val_image_path_list]
    data_path_train_dico = data_path_dico.copy()
    [data_path_train_dico.pop(key) for key in train_image_path_list]

    # Déplacement des données dans les répetoires appropriées
    #########################################################

    # Répertoire training
    output_data_path_train_dico = {}
    for imagette_elem, sample_elem in data_path_train_dico.items() :
        imagette_elem_out = rep_imagettes_train_output + os.sep + os.path.basename(imagette_elem)
        sample_elem_out  = rep_samples_train_output + os.sep + os.path.basename(sample_elem)
        output_data_path_train_dico[imagette_elem_out] = sample_elem_out
        shutil.move(imagette_elem, imagette_elem_out)
        moveVectorFile(sample_elem, sample_elem_out)

    # Répertoire validation
    output_data_path_val_dico = {}
    for imagette_elem, sample_elem in data_path_val_dico.items() :
        imagette_elem_out = rep_imagettes_val_output  + os.sep + os.path.basename(imagette_elem)
        sample_elem_out  = rep_samples_val_output + os.sep + os.path.basename(sample_elem)
        output_data_path_val_dico[imagette_elem_out] = sample_elem_out
        shutil.move(imagette_elem, imagette_elem_out)
        moveVectorFile(sample_elem, sample_elem_out)

    return output_data_path_train_dico, output_data_path_val_dico

###########################################################################################################################################
# FONCTION prepareTrain()                                                                                                                 #
###########################################################################################################################################
def prepareTrain(training_input, vector_training_input, vector_input, path_working_files_vectors_cuting_output, path_training_files_output, path_validation_files_output, class_label_dico, size_grid, debord, percent_no_data, percent_validation_split, augment_training, extension_raster=".tif", extension_vector=".shp", format_raster='GTiff', format_vector='ESRI Shapefile', rand_seed=0, epsg=2154, save_results_intermediate=False, overwrite=True) :
    """
    # ROLE:
    #    Préparation de des données pour l 'entrainement du réseau : découpage creation des fichier d'apprentissage et creation du fichier format coco JSON pour l'entrainement et la validation
    #    Récupération des résultats des fichiers d'entarinement au format JSON
    #
    # ENTREES DE LA FONCTION :
    #    training_input (string) : l'image satellite d'apprentissage
    #    vector_training_input (string) : les données d'apprentissage au format vecteur
    #    vector_input (string) : vecteur de découpe d'entrée
    #    path_working_files_vectors_cuting_output : répértoire où stocker les données d'apprentissage images et vecteurs à découper selon la grille
    #    path_training_files_output : répértoire des données d'apprentissage images et vecteurs d'entrainement
    #    path_validation_files_output : répértoire des données d'apprentissage images et vecteurs de validation
    #    class_label_dico : dictionaire affectation de label aux classes de classification
    #    size_grid (int) : dimension d'une cellule de la grille de découpe de l'image satellite initiale
    #    debord (int) : utilisé pour éviter les effets de bord. Agrandit artificiellement les imagettes
    #    percent_no_data (int) : pourcentage de no data
    #    percent_validation_split (int) : pourcentage de donnée validation / entrainement
    #    augment_training (int) : booléen pour determiner si on augmente artificiellement le jeu de données par des rotations
    #    extension_raster (string) : extension de fichier des imagettes
    #    extension_vector (string) : extension de fichier des vecteurs
    #    format_raster (string) : format des imagettes
    #    format_vector (string) : format des vecteurs
    #    epsg (int) : Identificateur de SIG
    #    save_results_intermediate (bool) : booléen qui determine si on sauvegarde ou non les fichiers temporaires
    #    overwrite (bool) : booléen pour écrire ou non par dessus un fichier existant
    #
    # SORTIES DE LA FONCTION :
    #    Renvoie les noms des dossiers où sont stockés les vecteurs et imagettes pour l'entrainement
    #
    """

    # Constantes
    IMAGES = "images"
    SAMPLES = "samples"
    ANNOTATION_FILE_NAME = "annotation-small"
    EXT_JSON = ".json"

    # Decoupage
    image_name = os.path.splitext(os.path.basename(training_input))[0]
    folder_imagette = "Imagette_" + image_name
    folder_train = "Train_" + image_name
    folder_grid = "Grid_" + image_name
    output_image_path_list, output_sample_vector_path_list = decoupeImageTraining(training_input, vector_training_input, path_working_files_vectors_cuting_output, size_grid, debord, epsg, folder_imagette, folder_train, folder_grid,extension_raster, extension_vector, format_raster, format_vector, overwrite)

    # Trie train et validation
    rep_imagettes_input = path_working_files_vectors_cuting_output + os.sep + folder_imagette
    rep_samples_input = path_working_files_vectors_cuting_output + os.sep + folder_train

    '''
    output_image_path_list = glob.glob(rep_imagettes_input + os.sep + '*' + extension_raster)
    output_sample_vector_path_list = []
    for image_file in output_image_path_list:
        image_name = os.path.splitext(os.path.basename(image_file))[0]
        extension = os.path.splitext(image_file)[1]
        pos_ligne = image_name.rindex("l")
        pos_colonne = image_name.rindex("c")
        ligne = int(image_name[pos_ligne + 1 : pos_colonne])
        colonne = int(image_name[pos_colonne + 1 : len(image_name)])
        vector_file = rep_samples_input + os.sep + "train_l" + str(ligne) + "c" + str(colonne) + extension_vector
        if not os.path.isfile(vector_file):
            raise NameError (cyan + "prepareTrain : " + bold + red  + "Sort file %s not exist!" %(vector_file) + endC)
        else :
            output_sample_vector_path_list.append(vector_file)
    '''

    rep_imagettes_train_output = path_training_files_output + os.sep + IMAGES
    rep_samples_train_output = path_training_files_output + os.sep + SAMPLES
    rep_imagettes_val_output = path_validation_files_output + os.sep + IMAGES
    rep_samples_val_output = path_validation_files_output + os.sep + SAMPLES

    output_data_path_train_dico, output_data_path_val_dico = sortFileTrainAndValidation(rep_imagettes_input, rep_samples_input, output_image_path_list, output_sample_vector_path_list, percent_no_data, percent_validation_split, rep_imagettes_train_output, rep_samples_train_output, rep_imagettes_val_output, rep_samples_val_output, extension_vector, format_vector, save_results_intermediate)

    '''
    train_image_path_list = glob.glob(rep_imagettes_train_output + os.sep + '*' + extension_raster)
    output_data_path_train_dico = {}
    for image_file in train_image_path_list:
        image_name = os.path.splitext(os.path.basename(image_file))[0]
        extension = os.path.splitext(image_file)[1]
        pos_ligne = image_name.rindex("l")
        pos_colonne = image_name.rindex("c")
        ligne = int(image_name[pos_ligne + 1 : pos_colonne])
        colonne = int(image_name[pos_colonne + 1 : len(image_name)])
        vector_file = rep_samples_train_output + os.sep + "train_l" + str(ligne) + "c" + str(colonne) + extension_vector
        if not os.path.isfile(vector_file):
            raise NameError (cyan + "prepareTrain : " + bold + red  + "Train file %s not exist!" %(vector_file) + endC)
        else :
            output_data_path_train_dico[image_file] = vector_file

    val_image_path_list = glob.glob(rep_imagettes_val_output + os.sep + '*' + extension_raster)
    output_data_path_val_dico = {}
    for image_file in val_image_path_list:
        image_name = os.path.splitext(os.path.basename(image_file))[0]
        extension = os.path.splitext(image_file)[1]
        pos_ligne = image_name.rindex("l")
        pos_colonne = image_name.rindex("c")
        ligne = int(image_name[pos_ligne + 1 : pos_colonne])
        colonne = int(image_name[pos_colonne + 1 : len(image_name)])
        vector_file = rep_samples_val_output + os.sep + "train_l" + str(ligne) + "c" + str(colonne) + extension_vector
        if not os.path.isfile(vector_file):
            raise NameError (cyan + "prepareTrain : " + bold + red  + "Train file %s not exist!" %(vector_file) + endC)
        else :
            output_data_path_val_dico[image_file] = vector_file
    '''

    # Annotation
    file_annotation_train = path_training_files_output + os.sep + ANNOTATION_FILE_NAME + EXT_JSON
    file_annotation_val = path_validation_files_output + os.sep + ANNOTATION_FILE_NAME + EXT_JSON
    class_label_dico.pop(0)
    categorie_id = list(class_label_dico.keys())[0]
    categorie_name = class_label_dico[categorie_id]
    if debug >= 3:
        print(cyan + "prepareTrain() : " + bold + green + "Categorie (name / id) = %s : %s" %(str(categorie_name), str(categorie_id)) + endC)

    createAnnotationJsonFile(output_data_path_train_dico, file_annotation_train, categorie_id, categorie_name)
    createAnnotationJsonFile(output_data_path_val_dico, file_annotation_val, categorie_id, categorie_name)

    return

###########################################################################################################################################
# FONCTION computeTrain()                                                                                                                 #
###########################################################################################################################################
def computeTrain(training_input, path_training_files_input, path_validation_files_input, model_input, model_output, config, number_epoch, augment_training, extension_raster=".tif", extension_vector=".shp", format_raster='GTiff', format_vector='ESRI Shapefile', rand_seed=0, epsg=2154, percent_no_data=10, save_results_intermediate=False, overwrite=True) :
    """
    # ROLE:
    #    Calcul de la matrice de confusion entre le masque de référence et la prédiction avec otbcli_ComputeConfusionMatrix
    #    Récupération des résultats de cette commande dans un fichier .txt
    #
    # ENTREES DE LA FONCTION :
    #    training_input (string) : l'image satellite d'apprentissage
    #    path_training_files_input : répértoire des données d'apprentissage images et vecteurs d'entrainement
    #    path_validation_files_input : répértoire des données d'apprentissage images et vecteurs de validation
    #    model_input (string) : nom du réseau de neurones à utiliser pour classifier
    #    model_output (string) : chemin où stocker le réseau de neurones entrainé
    #    config (structure) : structure contenant tout les paramètres propre au réseau de neurones
    #    number_epoch (int) : nombre d'epoch d'entrainement
    #    augment_training (bool) : booléen qui determine si on procède à l'augmentation artificielle de données sur le jeu de donnée d'entrainement
    #    extension_raster (string) : extension de fichier des imagettes
    #    extension_vector (string) : extension de fichier des vecteurs
    #    format_raster (string) : format des imagettes
    #    format_vector (string) : format des vecteurs
    #    epsg (int) : Identificateur de SIG
    #    save_results_intermediate (bool) : booléen qui determine si on sauvegarde ou non les fichiers temporaires
    #    overwrite (bool) : booléen pour écrire ou non par dessus un fichier existant
    #
    # SORTIES DE LA FONCTION :
    #    Renvoie le modèle de sortie entraîné
    #
    """

    # Desactiver Tensorfow V2
    tf.compat.v1.disable_v2_behavior()
    model = modellib.MaskRCNN(mode="training", config=config, model_dir=model_output)

    # Load pretrained weights
    if model_input != "" :
        model.load_weights(model_input, by_name=True, exclude = ["conv1","mrcnn_bbox_fc","mrcnn_class_logits","mrcnn_mask"])

    # Load training dataset
    dataset_train = MappingChallengeDataset()
    dataset_train.load_dataset(path_training_files_input, load_small=True)
    dataset_train.prepare()

    # Load validation dataset
    dataset_val = MappingChallengeDataset()
    val_coco = dataset_val.load_dataset(path_validation_files_input, load_small=True, return_coco=True)
    dataset_val.prepare()

    # Training
    #model.train(dataset_train, dataset_val, learning_rate=config.LEARNING_RATE, epochs=number_epoch, layers='heads', augmentation=augment_training)
    model.train(dataset_train, dataset_val, learning_rate=config.LEARNING_RATE, epochs=number_epoch, layers='all', augmentation=augment_training)

    return

###########################################################################################################################################
#                                                                                                                                         #
# PARTIE PREDICTION (génération des résultats "Inférence")                                                                                #
#                                                                                                                                         #
###########################################################################################################################################
#########################################################################
# FONCTION saveImageRawMask()                                           #
#########################################################################
def saveImageRawMask(image_ref_input, image_output, matrix_mask, data_value=1, no_data_value=0, format_raster="GTiff", overwrite=True):
    """
    #   Rôle : Cette fonction permet de sauvegarder le masque résultats sortie du reseau de neuronne en format matrice en fichier tiff une bande codage 8bits
    #   Codage : Utilisation de les libs "Gdal"  et numpy"
    #   Paramètres :
    #       image_ref_input : fichier image référente d'entrée
    #       matrix_mask : matrice du masque d'entrée
    #       image_output : fichier de sortie image masque
    #       data_value : valeur uint8 pour les valeur du masque à True
    #       no_data_value : la valeur des pixels nodata peut etre 0 si pas de valeur défini
    #       format_raster : Format de l'image de sortie par défaut GTiff (GTiff, HFA...)
    #       overwrite (bool) : booléen pour écrire ou non par dessus un fichier existant
    #   Paramétres de retour :
    #       le fichier de sortie mask
    """

    # Si le fichier de sortie existe deja
    if os.path.exists(image_output) :
        if overwrite :
            os.remove(image_output)
        else :
            return

    # Open the dataset
    dataset = gdal.Open(image_ref_input, GA_ReadOnly)
    cols = dataset.RasterXSize
    rows = dataset.RasterYSize
    nb_bands = dataset.RasterCount
    band = dataset.GetRasterBand(1)
    numpy_data = np.array(matrix_mask)
    if debug >= 4:
        print(cyan + "saveImageRawMask() : " + bold + green + "Shape = " %(str(numpy_data.shape)) + endC)
        print(numpy_data.shape)
    numpy_data_reduce = np.logical_or.reduce(numpy_data, axis=2).astype(np.uint8)
    numpy_data_reduce[numpy_data_reduce == 1] = data_value
    if debug >= 4:
        print(cyan + "saveImageRawMask() : " + bold + green + "shape reduce = " %(str(numpy_data_reduce.shape)) + endC)

    # Sauvegarde de l'image de sortie
    driver = gdal.GetDriverByName(format_raster)
    dataset_out = driver.Create(image_output, cols, rows, 1, gdal.GDT_Byte)
    dataset_out.SetGeoTransform(dataset.GetGeoTransform()) # sets same geotransform as input
    dataset_out.SetProjection(dataset.GetProjection())     # sets same projection as input
    dataset_out.GetRasterBand(1).WriteArray(numpy_data_reduce)
    dataset_out.GetRasterBand(1).SetNoDataValue(no_data_value)
    dataset_out.FlushCache()                               # remove from memory

    # Close the datasets
    dataset = None
    del dataset_out                                        # delete the data (not the actual geotiff)

    if debug >= 3:
        print(cyan + "saveImageRawMask() : " + bold + green + "Create mask file %s complete!" %(image_output) + endC)

    return

########################################################################
# FONCTION saveVectorBox()                                             #
########################################################################
def saveVectorBox(image_ref_input, vector_output, coordinates_box_list, scores_box_list, class_id_box_list, format_vector='ESRI Shapefile', overwrite=True):
    """
    #   Rôle : Cette fonction permet de sauvegarder le masque résultats sortie du reseau de neuronne en format matrice en fichier tiff une bande codage 8bits
    #   Codage : Utilisation de les libs "Gdal"  et numpy"
    #   Paramètres :
    #       image_ref_input : fichier image référente d'entrée
    #       vector_output : fichier de sortie vecteur des boites englobantes
    #       coordinates_box_list : liste des valeurs coordonnées des boites
    #       scores_box_list : liste des valeurs de scores de prediction
    #       class_id_box_list : liste des identifiants de classe de chaque boite
    #       format_vector : format du fichier vecteur. Optionnel, par default : 'ESRI Shapefile'
    #       overwrite (bool) : booléen pour écrire ou non par dessus un fichier existant
    #   Paramétres de retour :
    #       le fichier vecteur de sortie contenant les boites englobantes
    """

    # Info image ref
    xmin_image, xmax_image, ymin_image, ymax_image = getEmpriseImage(image_ref_input)
    pixel_width, pixel_height = getPixelWidthXYImage(image_ref_input)

    # Initialiser le data frame vide
    df_boxes = pandas.DataFrame()

    # Pour toutes les boites
    for index, coordinates_box in enumerate(coordinates_box_list):
        ymin_box = coordinates_box[0]
        xmin_box = coordinates_box[1]
        ymax_box = coordinates_box[2]
        xmax_box = coordinates_box[3]
        if debug >= 4:
            print(cyan + "saveVectorBox() : " + endC + "Coordonnees box index = " + str(index))
            print(cyan + "saveVectorBox() : " + endC + " xmin = " + str(xmin_box))
            print(cyan + "saveVectorBox() : " + endC + " ymin = " + str(ymin_box))
            print(cyan + "saveVectorBox() : " + endC + " xmax = " + str(xmax_box))
            print(cyan + "saveVectorBox() : " + endC + " ymax = " + str(ymax_box))

        # Calculer les cordonnees geographiques de la prediction
        boxes = pandas.DataFrame({"index":[0], "xmin":[0.0], "xmax":[0.0], "ymin":[0.0], "ymax":[0.0], "class_id":[0], "score":[0.0], "geometry":[None]})
        boxes["index"] = index
        boxes["class_id"] = class_id_box_list[index]
        boxes["score"] = scores_box_list[index]
        boxes["xmin"] = (xmin_box * pixel_width) + xmin_image
        boxes["xmax"] = (xmax_box * pixel_width) + xmin_image
        boxes["ymin"] = ymax_image - (ymin_box * pixel_height)
        boxes["ymax"] = ymax_image - (ymax_box * pixel_height)

        # Combine column to a shapely Box() object, save shapefile
        boxes['geometry'] = boxes.apply(lambda x: shapely.geometry.box(x.xmin,x.ymin,x.xmax,x.ymax), axis=1)

        # Concatene les dataframes
        df_boxes = pandas.concat([df_boxes, boxes], ignore_index=True)

    if debug >= 4:
       print(df_boxes)

    # Sauvegarde de la prediction au format vecteur
    if not df_boxes.empty:
        epsg, srs = getProjectionImage(image_ref_input)
        boxes_geometry = geopandas.GeoDataFrame(df_boxes, geometry='geometry')
        saveVectorFromDataframe(vector_output, boxes_geometry, epsg, srs, overwrite, format_vector)

    if debug >= 3:
        print(cyan + "saveVectorBox() : " + bold + green + "Create vector  file %s complete!" %(vector_output) + endC)

    return
###########################################################################################################################################
# FONCTION computeDetection()                                                                                                             #
###########################################################################################################################################
def computeDetection(image_input, vector_input, image_output, vector_output, model_input, config, class_label_dico, extension_raster=".tif", extension_vector=".shp", format_raster='GTiff', format_vector='ESRI Shapefile', epsg=2154, no_data_value=0, save_results_intermediate=False, overwrite=True):
    """
    # ROLE:
    #    Prediction des différents résultats en imagettes et assemblage en une seule image
    #
    # ENTREES DE LA FONCTION :
    #    image_input (string) : l'image satellite d'entrée
    #    vector_input (string) : vecteur de découpe d'entrée
    #    image_output (string) : chemin où stocker l'image finale détéctée
    #    vector_output (string) : chemin où stocker le vecteur finale détéctée (boites englobantes)
    #    model_input (string) : nom du réseau de neurones à utiliser pour classifier
    #    config (structure) : structure contenant la configurartion du réseau de neurones
    #    class_label_dico : dictionaire affectation de label aux classes de classification
    #    extension_raster (string) : extension de fichier des imagettes
    #    extension_vector (string) : extension de fichier des vecteurs
    #    format_raster (string) : format des imagettes
    #    format_vector (string) : format des vecteurs
    #    epsg (int) : Identificateur de SIG
    #    no_data_value (int) : valeur que prend un pixel qui ne contient pas d'information
    #    save_results_intermediate (bool) : booléen qui determine si on sauvegarde ou non les fichiers temporaires
    #    overwrite (bool) : booléen pour écrire ou non par dessus un fichier existant
    #
    # SORTIES DE LA FONCTION :
    #    Aucune sortie
    #
    """

    # Config parameters model
    model = modellib.MaskRCNN(mode="inference", model_dir=os.path.dirname(model_input), config=config)

    # Load model
    if debug >= 3:
        print(cyan + "computeDetection() : " + bold + green + "Used model file %s" %(model_input) + endC)

    model.load_weights(model_input, by_name=True)

    # Define class name
    class_names = []
    for class_name in class_label_dico.values() :
        class_names.append(class_name)
    if debug >= 3:
        print(cyan + "computeDetection() : " + bold + green + "Classes name %s" %(class_names) + endC)

    # Inference image
    image = skimage.io.imread(image_input)
    predictions = model.detect([image] * config.BATCH_SIZE, verbose=1) # We are replicating the same image to fill up the batch_size
    image8b = np.uint8(skimage.io.imread(image_input) >> 3)
    p = predictions[0]

    if debug >= 6:
        print(cyan + "computeDetection() : " + bold + green + "Result inference :"  + endC)
        print(len(predictions))
        print(type(p))
        for key, value in p.items() :
            print(key)

    # Sauvegarde des résultats
    saveImageRawMask(image_input, image_output, p['masks'], p['class_ids'][0])
    saveVectorBox(image_input, vector_output, p['rois'], p['scores'], p['class_ids'])
    visualize.display_instances(image8b, p['rois'], p['masks'], p['class_ids'], class_names, p['scores'])

    return

###########################################################################################################################################
#                                                                                                                                         #
# PARTIE FONCTION PRINCIPALES  (Train,Test,Pretraitement)                                                                                 #
#                                                                                                                                         #
###########################################################################################################################################


###########################################################################################################################################
# FONCTION computeMaskRCnnDetection()                                                                                                     #
###########################################################################################################################################
def computeMaskRCnnDetection(image_input, training_input, vector_training_input, vector_input, path_working_files_output, image_output, vector_output, model_input, model_output, class_label_dico, size_grid, debord, percent_no_data, percent_validation_split, augment_training, use_graphic_card, id_graphic_card, NN, debug, path_time_log, extension_raster=".tif", extension_vector=".shp", format_raster='GTiff', format_vector='ESRI Shapefile', rand_seed=0, epsg=2154, no_data_value=0, save_results_intermediate=False, overwrite=True):
    """
    # ROLE:
    #    Choix entre une simple classification ou entrainement, ou bien un enchainement des deux
    #
    # ENTREES DE LA FONCTION :
    #    image_input (string) : l'image satellite d'entrée
    #    training_input (string) : l'image satellite d'apprentissage
    #    vector_training_input (string) : les données d'apprentissage au format vecteur
    #    vector_input (string) : vecteur de découpe d'entrée
    #    path_working_files_output : répértoire où stocker les données d'apprentissage
    #    image_output (string) : chemin où stocker l'image finale détéctée
    #    vector_output (string) : chemin où stocker le vecteur finale détéctée (boites englobantes)
    #    model_input (string) : nom du réseau de neurones à utiliser pour classifier
    #    model_output (string) : chemin où stocker le modèle (réseau de neurones) une fois entraîné
    #    class_label_dico : dictionaire affectation de label aux classes de classification
    #    size_grid (int) : dimension d'une cellule de la grille de découpe de l'image satellite initiale
    #    debord (int) : utilisé pour éviter les effets de bord. Agrandit artificiellement les imagettes
    #    percent_no_data (int) : pourcentage de no data
    #    percent_validation_split (int) : pourcentage de donnée validation / entrainement
    #    augment_training (bool) : booléen qui determine si on procède à l'augmentation artificielle de données sur le jeu de donnée d'entrainement
    #    use_graphic_card (bool) : booléen qui determine si on utilise la GPU ou la CPU
    #    id_graphic_card (int) : determine l'identifiant de la carte graphique à utiliser (int)
    #    NN (structure) : structure contenant tout les paramètres propre au réseau de neurones
    #    debug (int) : gère l'affichage dans la console pour aider au débogage
    #    path_time_log (string) : le fichier de log de sortie
    #    extension_raster (string) : extension de fichier des imagettes
    #    extension_vector (string) : extension de fichier des vecteurs
    #    format_raster (string) : format des imagettes
    #    format_vector (string) : format des vecteurs
    #    rand_seed (int): graine pour la partie randon
    #    epsg (int) : Identificateur de SIG
    #    no_data_value (int) : valeur que prend un pixel qui ne contient pas d'information
    #    save_results_intermediate (bool) : booléen qui determine si on sauvegarde ou non les fichiers temporaires
    #    overwrite (bool) : booléen pour écrire ou non par dessus un fichier existant
    #
    # SORTIES DE LA FONCTION :
    #    Aucune sortie
    #
    """

    # Constantes
    REP_TEMP_CUT = "RepTempImagCut"
    TRAIN = "train"
    VAL = "val"

    # Utilisation du GPU
    if use_graphic_card :
        os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
        os.environ["CUDA_VISIBLE_DEVICES"] = str(id_graphic_card)

    # Parametre  random
    if rand_seed != 0:
        tf.random.set_seed(rand_seed)
        np.random.seed(rand_seed)
        rd.seed(rand_seed)

    # Création du fichier de log
    if path_time_log != "" :
        open(path_time_log, 'a').close()

    # Regarde si le fichier de log existe
    check_log = os.path.isfile(path_time_log)

    # Récupération du nombre de classes pour classifier avec le réseau
    number_class = len(class_label_dico)
    if (number_class < 1):
        raise NameError (cyan + "computeMaskRCnnDetection : " + bold + red  + "%i not a correct number of classes!" %(number_class) + endC)

    # Ajoute une classe BG lorsque l'on est dans une classification à une classe
    if number_class == 1 :
        # Ajout de la classe BG
        number_class = number_class + 1
        class_label_dico[0] = "BG"

    # Récupération du nombre de couche des images et moyen pixel de chaque couche
    if (image_input == "" or  not os.path.isfile(image_input)) and (training_input == "" or not os.path.isfile(training_input)) :
        raise NameError (cyan + "computeMaskRCnnDetection : " + bold + red  + "Le fichier image_input %s ou le fichier training_input % doit être défini ou les !" %(image_input, training_input) + endC)

    ref_image = ""
    if os.path.isfile(image_input) :
        ref_image = image_input
    elif os.path.isfile(training_input) :
        ref_image = training_input

    _, _, number_chanels = getGeometryImage(ref_image)
    statistics_dico = computeStatisticsImage(ref_image)
    stat_mean_chanels_list = []
    for stat_chanel in statistics_dico.values() :
        stat_mean_chanels_list.append(stat_chanel[0])

    # Mise à de la configurartion
    ModelConfig.NUM_CLASSES = number_class
    ModelConfig.IMAGE_CHANNEL_COUNT = number_chanels
    ModelConfig.MEAN_PIXEL = np.array(stat_mean_chanels_list)
    ModelConfig.IMAGE_MAX_DIM = size_grid
    ModelConfig.IMAGE_MIN_DIM = size_grid

    # Parametres réseau
    ModelConfig.BACKBONE = NN.neural_network_mode
    if NN.batch > 0 :
        ModelConfig.BATCH_SIZE = NN.batch
    ModelConfig.STEPS_PER_EPOCH = NN.number_steps_per_epoch
    ModelConfig.VALIDATION_STEPS = NN.number_validation_steps
    ModelConfig.LEARNING_RATE = NN.learning_rate_factor
    ModelConfig.LEARNING_MOMENTUM = NN.learning_momentum_factor
    ModelConfig.DETECTION_MAX_INSTANCES = NN.detection_max_instances
    ModelConfig.DETECTION_MIN_CONFIDENCE = NN.detection_min_confidence
    ModelConfig.DETECTION_NMS_THRESHOLD = NN.detection_mns_threshold

    config = ModelConfig()
    if debug >=1:
        config.display()

    ##################################################
    # Choix entre entrainement,inférence ou les deux #
    ##################################################

    # Cas de l'entrainement
    #######################
    path_working_files_vectors_cuting_output = ""
    if training_input != "" and vector_training_input != "" and model_output != "" and path_working_files_output != "":
         if debug >=1:
            print(cyan + "computeMaskRCnnDetection() : " + endC + "Début de la phase de préparation")

         # Mise à jour du Log
         if check_log :
            starting_event = "Starting of prepare data phase : "
            timeLine(path_time_log, starting_event)

         # Préparation
         path_working_files_vectors_cuting_output = path_working_files_output + os.sep + REP_TEMP_CUT
         path_training_files_output = path_working_files_output + os.sep + TRAIN
         path_validation_files_output = path_working_files_output + os.sep + VAL

         prepareTrain(training_input, vector_training_input, vector_input, path_working_files_vectors_cuting_output, path_training_files_output, path_validation_files_output, class_label_dico, size_grid, debord, percent_no_data, percent_validation_split, augment_training, extension_raster, extension_vector, format_raster, format_vector, rand_seed, epsg, save_results_intermediate, overwrite)

         if debug >=1:
            print(cyan + "computeMaskRCnnDetection() : " + endC + "Fin de la préparation")

         # Mise à jour du Log
         if check_log :
            ending_event = "Ending  of prepare data phase : "
            timeLine(path_time_log, ending_event)

         if debug >=1:
            print(cyan + "computeMaskRCnnDetection() : " + endC + "Début de la phase d'entrainement du réseau de neurones")

         # Mise à jour du Log
         if check_log :
            starting_event = "Starting of training phase : "
            timeLine(path_time_log, starting_event)

         # Entrainement
         computeTrain(training_input, path_training_files_output, path_validation_files_output, model_input, model_output, config, NN.number_epoch, augment_training, extension_raster, extension_vector, format_raster, format_vector, rand_seed, epsg, save_results_intermediate, overwrite)

         if debug >=1:
            print(cyan + "computeMaskRCnnDetection() : " + endC + "Fin de l'entrainement du réseau de neurones")

         # Mise à jour du Log
         if check_log :
            ending_event = "Ending  of training phase : "
            timeLine(path_time_log, ending_event)

    # Cas d'une simple detection
    ############################
    if image_output != "" and model_input != "":

         if debug >=1:
            print(cyan + "computeMaskRCnnDetection() : " + endC + "Début de la phase de detection")

         # Mise à jour du Log
         if check_log :
            starting_event = "Starting of detection : "
            timeLine(path_time_log, starting_event)

         # Detection
         computeDetection(image_input, vector_input, image_output, vector_output, model_input, config, class_label_dico, extension_raster, extension_vector, format_raster, format_vector, epsg, no_data_value, save_results_intermediate, overwrite)

         # Mise à jour du Log
         if check_log :
            ending_event = "Ending of detection : "
            timeLine(path_time_log, ending_event)

         if debug >=1:
            print(cyan + "computeMaskRCnnDetection() : " + endC + "Fin de la detection avec reseau de neurones")

    # Nettoyer l'environnement si save_results_intermediate est à False
    ###################################################################

    # Nettoyage du répertoire temporaire
    if not save_results_intermediate:
        if os.path.isdir(path_working_files_vectors_cuting_output) :
            deleteDir(path_working_files_vectors_cuting_output)
            if debug >= 3:
               print(cyan + "computeMaskRCnnDetection() : " + bold + green + "Delete repertory %s complete!" %(path_working_files_vectors_cuting_output) + endC)

    # Clear keras session
    keras.backend.clear_session()

    return

###########################################################################################################################################
# MISE EN PLACE DU PARSER                                                                                                                 #
###########################################################################################################################################

# Code executé seulement dans le cas ou le script est lancé depuis une ligne de commande
# Il n'est pas executé lors d'un import MaskRcnnDetection.py

# Exemple de lancement en ligne de commande pour entrainer un réseau de neurones Mask R-CNN :
#python -m MaskRcnnDetection -ti /mnt/RAM_disk/Images/PleiadesToulouseMetropoleZ3_20180925.tif -vi /mnt/RAM_disk/Bati/sample_bati2018.shp -v /mnt/RAM_disk/Images/Emprise_Z3_Pleiades_20181014.shp  -po /mnt/RAM_disk/WorkTraining -mo /mnt/Data2/10_Agents_travaux_en_cours/Gilles/Reseau_Mask_RCNN/V0/logs -sg 320 -deb 20 -pnd 5 -pvs 20 -cld 0:BG 10:Building -nn.nm resnet101 -nn.ne 20 -log /mnt/RAM_disk/Logs/time_log.txt


# Exemple de lancement en ligne de commande pour tester un réseau de neurones  Mask R-CNN existant:
#python -m MaskRcnnDetection -i /mnt/RAM_disk/ExImages/sat_l150c85.tif -o /mnt/RAM_disk/ExImages/sat_l150c85_mask.tif -vo /mnt/RAM_disk/ExImages/sat_l150c85_box.shp -mi  /mnt/Data2/10_Agents_travaux_en_cours/Gilles/Reseau_Mask_RCNN/V0/logs/cerema-find-build20230315T0848/mask_rcnn_cerema-find-build_0015.h5 -cld 0:BG 10:Building -log /mnt/RAM_disk/Logs/time_log.txt


def main(gui=False):
    # Définition des arguments possibles pour l'appel en ligne de commande
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, prog="MaskRcnnDetection", description="\
    Info : Classification supervisee  a l'aide de reseau de neurones. \n\
    Objectif : Execute une classification supervisee NN sur chaque pixels d'une images. \n\
    Exemple utilisation pour entrainer un reseau : python MaskRcnnDetection.py  \n\
                                                           -ti /mnt/RAM_disk/Images/PleiadesToulouseMetropoleZ3_20180925.tif \n\
                                                           -vi /mnt/RAM_disk/Bati/sample_bati2018.shp \n\
                                                           -v /mnt/RAM_disk/Images/Emprise_Z3_Pleiades_20181014.shp \n\
                                                           -po /mnt/RAM_disk/work_training \n\
                                                           -mo /mnt/Data2/10_Agents_travaux_en_cours/Gilles/Reseau_Mask_RCNN/V0/logs \n\
                                                           -sg 320 \n\
                                                           -deb 20 \n\
                                                           -pnd 5 \n\
                                                           -pvs 20 \n\
                                                           -cld 0:BG 10:Building \n\
                                                           -nm resnet101 \n\
                                                           -nn.ne 20\n\
                                                           -log /mnt/RAM_disk/Logs/time_log.txt \n\
    Exemple utilisation pour detecter avec un reseau : python MaskRcnnDetection.py \n\
                                                           -i /mnt/RAM_disk/ExImages/sat_l150c85.tif  \n\
                                                           -o /mnt/RAM_disk/ExImages/sat_l150c85_mask.tif \n\
                                                           -vo /mnt/RAM_disk/ExImages/sat_l150c85_box.shp \n\
                                                           -mi  /mnt/Data2/10_Agents_travaux_en_cours/Gilles/Reseau_Mask_RCNN/V0/logs/cerema-find-build20230315T0848/mask_rcnn_cerema-find-build_0015.h5 \n\
                                                           -cld 0:BG 10:Building \n\
                                                           -nn.nm resnet101 \n\
                                                           -nn.ne 20\n\
                                                           -log /mnt/RAM_disk/Logs/time_log.txt \n")

    # Paramètres


    # Directory path
    parser.add_argument('-i','--image_input',default="",help="Image input to classify", type=str, required=False)
    parser.add_argument('-ti','--training_input',default="",help="Image training input", type=str, required=False)
    parser.add_argument('-vi','--vector_training_input',default="",help="Vectror training input (groundtruth)", type=str, required=False)
    parser.add_argument('-v','--vector_input',default="",help="Emprise vector of input image", type=str, required=False)
    parser.add_argument('-po','--path_working_files_output',default="",help="Working training directory output", type=str, required=False)
    parser.add_argument('-o','--image_output',default="",help="Image output detected", type=str, required=False)
    parser.add_argument('-vo','--vector_output',default="",help="Image output detected", type=str, required=False)
    parser.add_argument('-mi','--model_input',default="",help="Neural Network already trained", type=str, required=False)
    parser.add_argument('-mo','--model_output',default="",help="Neural Network to train", type=str, required=False)

    # Input image parameters
    parser.add_argument("-cld", "--class_label_dico",nargs="+",default={}, help = "NB: to inquire, dictionary of correspondence class Mandatory Ex: 0:BG 10:Build", type=str,required=False)
    parser.add_argument('-sg','--size_grid',default=320,help="Size of study grid in pixels. Not used, if vector_grid_input is inquired", type=int, required=False)
    parser.add_argument('-deb','--debord',default=0,help="Reduce size of grid cells in pixels. Useful to avoid side effect",type=int, required=False)
    parser.add_argument('-pnd','--percent_no_data',default=5,help="Percentage of no data allowed in an input image", type=float, required=False)
    parser.add_argument('-pvs','--percent_validation_split',default=20,help="Percentage of the dataset dedicated to validation", type=float, required=False)
    parser.add_argument('-at','--augment_training',action='store_true',default=False,help="Modify image and mask to artificially increase the data set", required=False)
    parser.add_argument('-ugc','--use_graphic_card',action='store_true',default=False,help="Use CPU for training phase", required=False)
    parser.add_argument('-igpu','--id_graphic_card',default=0,help="Id of graphic card used to classify", type=int, required=False)

    # Hyperparameters NN
    parser.add_argument('-nn.nm','--neural_network_mode',default="resnet101",help="Type of Neural Network (resnet50 | resnet101)", type=str, required=False)
    parser.add_argument('-nn.b','--batch',default=0,help="Number of samples per gradient update", type=int, required=False)
    parser.add_argument('-nn.ne','--number_epoch',default=20,help="Number of epoch to train the Neural Network", type=int, required=False)
    parser.add_argument('-nn.nspe','--number_steps_per_epoch',default=1000,help="Number of steps par epoch of Neural Network", type=int, required=False)
    parser.add_argument('-nn.nvs','--number_validation_steps',default=50,help="Number of validation steps of Neural Network", type=int, required=False)
    parser.add_argument('-nn.lrf','--learning_rate_factor',default=0.001,help="Factor by which the learning rate will be reduced", type=float, required=False)
    parser.add_argument('-nn.lmf','--learning_momentum_factor',default=0.9,help="Factor by which the learning momentum will be reduced", type=float, required=False)
    parser.add_argument('-nn.dmi','--detection_max_instances',default=100,help="Max number of final detections", type=int, required=False)
    parser.add_argument('-nn.dmc','--detection_min_confidence',default=0.7,help="Minimum probability value to accept a detected instance", type=float, required=False)
    parser.add_argument('-nn.dmt','--detection_mns_threshold',default=0.3,help="Non-maximum suppression threshold for detection", type=float, required=False)

    # A CONSERVER
    parser.add_argument('-rand','--rand_seed',default=0,help="User defined seed for tensorflow random sample", type=int, required=False)
    parser.add_argument('-ram','--ram_otb',default=0,help="Ram available for processing otb applications (in MB)", type=int, required=False)
    parser.add_argument('-ndv','--no_data_value', default=0, help="Option : Value of the pixel no data. By default : 0", type=int, required=False)
    parser.add_argument('-epsg','--epsg', default=2154,help="Projection of the output file.", type=int, required=False)
    parser.add_argument('-raf','--format_raster', default="GTiff", help="Option : Format output image, by default : GTiff (GTiff, HFA...)", type=str, required=False)
    parser.add_argument('-vef','--format_vector', default="ESRI Shapefile",help="Format of the output file.", type=str, required=False)
    parser.add_argument('-rae','--extension_raster', default=".tif", help="Option : Extension file for image raster. By default : '.tif'", type=str, required=False)
    parser.add_argument('-vee','--extension_vector',default=".shp",help="Option : Extension file for vector. By default : '.shp'", type=str, required=False)
    parser.add_argument('-log','--path_time_log',default="",help="Name of log", type=str, required=False)
    parser.add_argument('-sav','--save_results_inter',action='store_true',default=False,help="Save or delete intermediate result after the process. By default, False", required=False)
    parser.add_argument('-now','--overwrite',action='store_false',default=True,help="Overwrite files with same names. By default, True", required=False)
    parser.add_argument('-debug','--debug',default=5,help="Option : Value of level debug trace, default : 3 ",type=int, required=False)
    args = displayIHM(gui, parser)

    # CREATION STRUCTURE
    NN = StructMAskRCnnParameter()

    # RECUPERATION DES ARGUMENTS

    # Récupération du chemin contenant l'image d'entrée
    if args.image_input != None:
        image_input = args.image_input
        if image_input != "" and not os.path.isfile(image_input):
            raise NameError (cyan + "MaskRcnnDetection : " + bold + red  + "File %s not exist!" %(image_input) + endC)

    # Récupération du chemin contenant l'image d'apprentissage
    if args.training_input != None:
        training_input = args.training_input
        if training_input != "" and not os.path.isfile(training_input):
            raise NameError (cyan + "MaskRcnnDetection : " + bold + red  + "File %s not exist!" %(training_input) + endC)

    # Récupération du chemin contenant les données vecteur d'apprentissage
    if args.vector_training_input != None:
        vector_training_input = args.vector_training_input
        if vector_training_input != "" and not os.path.isfile(vector_training_input):
            raise NameError (cyan + "MaskRcnnDetection : " + bold + red  + "File %s not exist!" %(vector_training_input) + endC)

    # Récupération du vecteur d'emprise sous forme de polygone
    if args.vector_input != None:
        vector_input = args.vector_input
        if vector_input != "" and not os.path.isfile(vector_input):
            raise NameError (cyan + "MaskRcnnDetection : " + bold + red  + "File %s not exist!" %(vector_input) + endC)

    # Stockage de travail des données d'apprentissage
    if args.path_working_files_output != None:
        path_working_files_output = args.path_working_files_output
        # Test si le repertoire de sortie existe
        if args.path_working_files_output != "" :
            if not os.path.isdir(path_working_files_output):
                os.makedirs(path_working_files_output)

    # Stockage de l'image détectée
    if args.image_output != None:
        image_output = args.image_output
        # Test si le repertoire de sortie existe
        if image_output != "" :
            repertory_output = os.path.dirname(image_output)
            if not os.path.isdir(repertory_output):
                os.makedirs(repertory_output)

    # Stockage du vecteur détecté
    if args.vector_output != None:
        vector_output = args.vector_output
        # Test si le repertoire de sortie existe
        if vector_output != "" :
            repertory_output = os.path.dirname(vector_output)
            if not os.path.isdir(repertory_output):
                os.makedirs(repertory_output)

    # Récupération du modèle déjà entrainé
    if args.model_input != None:
        model_input = args.model_input
        if model_input != "" and not os.path.isfile(model_input):
            raise NameError (cyan + "MaskRcnnDetection : " + bold + red  + "File %s not exist!" %(model_input) + endC)

    # Récupération du modèle à entrainer
    if args.model_output != None :
        model_output = args.model_output
        # Test si le repertoire de sortie existe
        if args.model_output != "" :
            #repertory_output = os.path.dirname(model_output)
            if not os.path.isdir(model_output):
                os.makedirs(model_output)

    # Creation du dictionaire reliant les classes à leur label
    class_label_dico = {}
    if args.class_label_dico != None and args.class_label_dico != {}:
        for tmp_txt_class in args.class_label_dico:
            class_label_list = tmp_txt_class.split(':')
            class_label_dico[int(class_label_list[0])] = class_label_list[1]

    # Récupération de la taille des images à découper
    if args.size_grid != None :
        size_grid = args.size_grid
        # Doit être une  puissance de 2
        #if not math.log2(size_grid).is_integer() :
            #raise NameError (cyan + "MaskRcnnDetection : " + bold + red  + "%i not a correct size for an image!" %(size_grid) + endC)

    # Récupération du nombre d'échantillons qui passe dans le réseau avant une mise à jour des poids
    if args.debord != None :
        debord = args.debord
        if debord < 0 :
            raise NameError (cyan + "MaskRcnnDetection : " + bold + red  + "0 and negative numbers not allowed!" + endC)

    # Récupération du pourcentage de no data autoriser dans une imagette
    if args.percent_no_data != None :
        percent_no_data = args.percent_no_data
        if (percent_no_data < 0 or percent_no_data > 100):
            raise NameError (cyan + "MaskRcnnDetection : " + bold + red  + "percent %i number must be between 0 and 100!" %(percent_no_data) + endC)

    # Récupération d'un float entre 0 et 1 pour determiner la part de données utilisée pour la validation
    if args.percent_validation_split != None :
        percent_validation_split = args.percent_validation_split
        if (percent_validation_split < 0 or percent_validation_split > 100):
            raise NameError (cyan + "MaskRcnnDetection : " + bold + red  + "percent %i number must be between 0 and 100!" %(percent_validation_split) + endC)

    # Récupération d'un int utilisé comme un booléen pour savoir si on augmente artificiellement les données
    if args.augment_training != None :
        augment_training = args.augment_training
        if type(augment_training) != bool:
            raise NameError (cyan + "MaskRcnnDetection : " + bold + red  + "augment_training takes False or True in input!" + endC)

    # Récupération d'un int utilisé comme un booléen pour savoir si on utilise ou non la CPU pour effectuer les calculs
    use_graphic_card = args.use_graphic_card
    if type(use_graphic_card) != bool:
        raise NameError (cyan + "MaskRcnnDetection : " + bold + red  + "use_cpu takes False or True in input!" + endC)

    # Récupération de l'identifiant de la carte graphique à utiliser
    if args.id_graphic_card != None :
        id_graphic_card = args.id_graphic_card
        if (id_graphic_card < 0):
            raise NameError (cyan + "MaskRcnnDetection : " + bold + red  + "%i not a correct number!" %(id_graphic_card) + endC)

    # Récupération du type de réseau de neurones
    if args.neural_network_mode != None:
        NN.neural_network_mode = args.neural_network_mode
        if NN.neural_network_mode.lower() != "resnet50" and NN.neural_network_mode.lower() != "resnet101" :
            raise NameError (cyan + "MaskRcnnDetection : " + bold + red  + "Not a good name! (Resunet or Unet)" + endC)

    # Récupération du nombre d'échantillons qui passe dans le réseau avant une mise à jour des poids
    if args.batch != None :
        NN.batch = args.batch
        if NN.batch < 0 :
            raise NameError (cyan + "MaskRcnnDetection : " + bold + red  + "batch negative numbers not allowed!" + endC)

    # Récupération du nombre d'époques pour entrainer le réseau
    if args.number_epoch != None :
        NN.number_epoch = args.number_epoch
        if NN.number_epoch <=0 :
            raise NameError (cyan + "MaskRcnnDetection : " + bold + red  + "number_epoch 0 and negative numbers not allowed!" + endC)

    # Récupération du nombre de pas par epoch du réseau
    if args.number_steps_per_epoch != None :
        NN.number_steps_per_epoch = args.number_steps_per_epoch
        if NN.number_steps_per_epoch <= 0 :
            raise NameError (cyan + "MaskRcnnDetection : " + bold + red  + "number_steps_per_epoch 0 and negative numbers not allowed!" + endC)

    # Récupération du nombre de pas de validation du réseau
    if args.number_validation_steps != None :
        NN.number_validation_steps = args.number_validation_steps
        if NN.number_validation_steps <= 0 :
            raise NameError (cyan + "MaskRcnnDetection : " + bold + red  + "number_validation_steps 0 and negative numbers not allowed!" + endC)

    # Récupération du taux d'apprentissage du réseau
    if args.learning_rate_factor != None :
        NN.learning_rate_factor = args.learning_rate_factor
        if NN.learning_rate_factor <= 0 :
            raise NameError (cyan + "MaskRcnnDetection : " + bold + red  + "learning_rate_factor 0 and negative numbers not allowed!" + endC)

    # Récupération du taux de dynamique du réseau
    if args.learning_momentum_factor != None :
        NN.learning_momentum_factor = args.learning_momentum_factor
        if NN.learning_momentum_factor <= 0 :
            raise NameError (cyan + "MaskRcnnDetection : " + bold + red  + "learning_momentum_factor 0 and negative numbers not allowed!" + endC)

    # Récupération du nombre maximal de detection finale
    if args.detection_max_instances != None :
        NN.detection_max_instances = args.detection_max_instances
        if NN.detection_max_instances <= 0 :
            raise NameError (cyan + "MaskRcnnDetection : " + bold + red  + "detection_max_instances 0 and negative numbers not allowed!" + endC)

    # Récupération de la valeur de probalilité minimale pour accepter une instance detecté
    if args.detection_min_confidence != None :
        NN.detection_min_confidence = args.detection_min_confidence
        if NN.detection_min_confidence <= 0 :
            raise NameError (cyan + "MaskRcnnDetection : " + bold + red  + "detection_min_confidence 0 and negative numbers not allowed!" + endC)

    # Récupération de la valeur non-maximal du seui de suppression pour la detection
    if args.detection_mns_threshold!= None :
        NN.detection_mns_threshold = args.detection_mns_threshold
        if NN.detection_mns_threshold <= 0 :
            raise NameError (cyan + "MaskRcnnDetection : " + bold + red  + "detection_mns_threshold 0 and negative numbers not allowed!" + endC)

    # A CONSERVER

    # Récupération du parametre rand
    if args.rand_seed != None:
        rand_seed = args.rand_seed

    # Récupération du parametre ram
    if args.ram_otb != None:
        ram_otb = args.ram_otb

    # Parametres de valeur du nodata
    if args.no_data_value!= None:
        no_data_value = args.no_data_value

    # Récupération de l'indice de projection
    if args.epsg != None:
        epsg = args.epsg

    # Paramètre format des images de sortie
    if args.format_raster != None:
        format_raster = args.format_raster

    # Paramètre format des vecteurs
    if args.format_vector != None:
        format_vector = args.format_vector

    # Récupération de l'extension des fichiers images
    if args.extension_raster != None:
        extension_raster = args.extension_raster

    # Récupération de l'extension des fichiers vecteurs
    if args.extension_vector != None:
        extension_vector = args.extension_vector

    # Récupération du nom du fichier log
    if args.path_time_log!= None:
        path_time_log = args.path_time_log

    # Ecrasement des fichiers
    if args.save_results_inter != None:
        save_results_intermediate = args.save_results_inter

    # Ecrit par dessus un fichier existant
    if args.overwrite!= None:
        overwrite = args.overwrite

    # Récupération de l'option niveau de debug
    if args.debug!= None:
        debug = args.debug

    # Affichage des arguments récupérés
    if debug >= 3:
        print(bold + green + "Variables dans le parser" + endC)

        # Directory path
        print(cyan + "MaskRcnnDetection : " + endC + "image_input : " + image_input + endC)
        print(cyan + "MaskRcnnDetection : " + endC + "training_input : " + training_input + endC)
        print(cyan + "MaskRcnnDetection : " + endC + "vector_training_input : " + vector_training_input + endC)
        print(cyan + "MaskRcnnDetection : " + endC + "vector_input : " + vector_input + endC)
        print(cyan + "MaskRcnnDetection : " + endC + "path_working_files_output : " + path_working_files_output + endC)
        print(cyan + "MaskRcnnDetection : " + endC + "image_output : " + image_output + endC)
        print(cyan + "MaskRcnnDetection : " + endC + "vector_output : " + vector_output + endC)
        print(cyan + "MaskRcnnDetection : " + endC + "model_input : " + model_input + endC)
        print(cyan + "MaskRcnnDetection : " + endC + "model_output : " + model_output + endC)

        print(cyan + "MaskRcnnDetection : " + endC + "class_label_dico : " + str(class_label_dico) + endC)
        print(cyan + "MaskRcnnDetection : " + endC + "size_grid : " + str(size_grid) + endC)
        print(cyan + "MaskRcnnDetection : " + endC + "debord : " + str(debord) + endC)
        print(cyan + "MaskRcnnDetection : " + endC + "percent_no_data : " + str(percent_no_data) + endC)
        print(cyan + "MaskRcnnDetection : " + endC + "percent_validation_split : " + str(percent_validation_split) + endC)
        print(cyan + "MaskRcnnDetection : " + endC + "augment_training : " + str(augment_training) + endC)
        print(cyan + "MaskRcnnDetection : " + endC + "use_graphic_card : " + str(use_graphic_card) + endC)
        print(cyan + "MaskRcnnDetection : " + endC + "id_graphic_card : " + str(id_graphic_card) + endC)

        # Hyperparameters NN
        print(cyan + "MaskRcnnDetection : " + endC + "neural_network_mode : " + NN.neural_network_mode + endC)
        print(cyan + "MaskRcnnDetection : " + endC + "batch : " + str(NN.batch) + endC)
        print(cyan + "MaskRcnnDetection : " + endC + "number_epoch : " + str(NN.number_epoch) + endC)
        print(cyan + "MaskRcnnDetection : " + endC + "number_steps_per_epoch : " + str(NN.number_steps_per_epoch) + endC)
        print(cyan + "MaskRcnnDetection : " + endC + "number_validation_steps : " + str(NN.number_validation_steps) + endC)
        print(cyan + "MaskRcnnDetection : " + endC + "learning_rate_factor : " + str(NN.learning_rate_factor) + endC)
        print(cyan + "MaskRcnnDetection : " + endC + "learning_momentum_factor : " + str(NN.learning_momentum_factor) + endC)
        print(cyan + "MaskRcnnDetection : " + endC + "detection_max_instances : " + str(NN.detection_max_instances) + endC)
        print(cyan + "MaskRcnnDetection : " + endC + "detection_min_confidence : " + str(NN.detection_min_confidence) + endC)
        print(cyan + "MaskRcnnDetection : " + endC + "detection_mns_threshold : " + str(NN.detection_mns_threshold) + endC)

        # A CONSERVER
        print(cyan + "MaskRcnnDetection : " + endC + "rand_seed : " + str(rand_seed) + endC)
        print(cyan + "MaskRcnnDetection : " + endC + "ram_otb : " + str(ram_otb) + endC)
        print(cyan + "MaskRcnnDetection : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "MaskRcnnDetection : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "MaskRcnnDetection : " + endC + "format_raster : " + format_raster + endC)
        print(cyan + "MaskRcnnDetection : " + endC + "format_vector : " + format_vector + endC)
        print(cyan + "MaskRcnnDetection : " + endC + "extension_raster : " + extension_raster + endC)
        print(cyan + "MaskRcnnDetection : " + endC + "extension_vector : " + extension_vector + endC)
        print(cyan + "MaskRcnnDetection : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "MaskRcnnDetection : " + endC + "save_results_inter : " + str(save_results_intermediate) + endC)
        print(cyan + "MaskRcnnDetection : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "MaskRcnnDetection : " + endC + "debug : " + str(debug) + endC)

        # Appel de la fonction principale
        computeMaskRCnnDetection(image_input, training_input, vector_training_input, vector_input, path_working_files_output, image_output, vector_output, model_input, model_output, class_label_dico, size_grid, debord, percent_no_data, percent_validation_split, augment_training, use_graphic_card, id_graphic_card, NN, debug, path_time_log, extension_raster, extension_vector, format_raster, format_vector, rand_seed, epsg, no_data_value, save_results_intermediate, overwrite)

# ================================================

if __name__ == '__main__':
  main(gui=False)
