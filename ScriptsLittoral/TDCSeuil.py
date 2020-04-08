#! /usr/bin/env pyt/hon
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerSO/DALETT/SCGSI  All rights reserved.                                                                            #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT D'EXTRACTION DU TRAIT DE CÔTE JET DE RIVE PAR SEUILLAGE                                                                            #
#                                                                                                                                           #
#############################################################################################################################################

'''
Nom de l'objet : TDCSeuil.py
Description    :
    Objectif   : Extrait le trait de côte jet de rive par seuillage à partir d'une image satellite

Date de creation : 20/05/2016
'''

from __future__ import print_function
from osgeo import ogr, osr
import os, time, argparse, sys, shutil
import datetime
from Lib_index import createNDVI
from Lib_display import bold, black, red, green, yellow, blue, magenta, cyan, endC, displayIHM
from Lib_log import timeLine
from Lib_file import removeVectorFile, removeFile
from Lib_raster import cutImageByVector, createBinaryMask, polygonizeRaster
from Lib_vector import addNewFieldVector, getAttributeType, getAttributeNameList, getAttributeValues
from PolygonMerToTDC import polygonMerToTDC
from CalculSeuilImage import runCalculSeuil

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 3

###########################################################################################################################################
# STRUCTURE StructAttribute                                                                                                                #
###########################################################################################################################################
# Structure contenant les information utiles à un attribu : Non, le type, la dimension, et la valeur
class StructAttribute:
    def __init__(self):
        self.name = ''
        self.ogrType = None
        self.width = 0
        self.value = ''

    def __init__(self,name,ogrType,width,value):
        self.name = name
        self.ogrType = ogrType
        self.width = width
        self.value = value

###########################################################################################################################################
# FONCTION runTDCSeuil                                                                                                                    #
###########################################################################################################################################
# ROLE:
#    Extraction du trait de côte jet de rive d'une image satellite
#
# ENTREES DE LA FONCTION :
#    input_im_seuils_dico : Dictionnaire des images à traiter pour extraire un trait de côte par image, et des seuils associés pour le masque binaire terre/mer
#    output_dir : Répertoire de sortie pour les traitements
#    input_sea_points : Fichier shp de points dans la mer pour identifier les polygones mer sur le masque terre/mer
#    input_cut_vector : Option : le fichier vecteur pour la découpe du trait de côte en sortie
#    input_emprise_vector : Option : le fichier d'emprise pour remplire automatiquement les valeurs des attributs
#    simplif : Option : valeur de tolérence pour la simplification du trait de côte
#    is_calc_indice_image : Option : Calcul de l'image NDVI (si elle n'est pas donnée en entrée)
#    attribute_val_limite : Valeur de l'attribut TDC_Limite
#    attribute_val_proced : Valeur de l'attribut TDC_proced
#    attribute_val_datepr : Valeur de l'attribut TDC_Datepr
#    attribute_val_precis : Valeur de l'attribut TDC_precis
#    attribute_val_contac : Valeur de l'attribut TDC_Contac
#    attribute_val_type : Valeur de l'attribut Type (de sattelite)
#    no_data_value : Valeur de  pixel du no data
#    path_time_log : le fichier de log de sortie
#    channel_order : identifiant des canaux de l image, exmple : {"Red":1,"Green":2,"Blue":3,"NIR":4}, defaut=[Red,Green,Blue,NIR]
#    epsg : Code EPSG des fichiers
#    format_raster : Format de l'image de sortie, par défaut : GTiff
#    format_vector  : format du vecteur de sortie, par defaut = 'ESRI Shapefile'
#    extension_raster : extension des fichiers raster de sortie, par defaut = '.tif'
#    extension_vector : extension du fichier vecteur de sortie, par defaut = '.shp'
#    save_results_intermediate : fichiers de sorties intermediaires non nettoyées, par defaut = True
#    overwrite : supprime ou non les fichiers existants ayant le meme nom
#
# SORTIES DE LA FONCTION :
#    Le fichier contenant le trait de côte extrait par seuillage
#    Eléments modifiés aucun
#

def runTDCSeuil(input_im_seuils_dico, output_dir, input_sea_points, input_cut_vector, input_emprise_vector, simplif, is_calc_indice_image, attribute_val_limite, attribute_val_proced, attribute_val_datepr, attribute_val_precis, attribute_val_contac, attribute_val_type, no_data_value, path_time_log, channel_order=['Red','Green','Blue','NIR'], epsg=2154, format_raster='GTiff', format_vector="ESRI Shapefile", extension_raster=".tif", extension_vector=".shp", save_results_intermediate=True, overwrite=True):

    # Mise à jour du Log
    starting_event = "runTDCSeuil() : Select TDC Seuil starting : "
    timeLine(path_time_log,starting_event)

    # Affichage des paramètres
    if debug >= 3:
        print(bold + green + "Variables dans runTDCSeuil - Variables générales" + endC)
        print(cyan + "runTDCSeuil() : " + endC + "input_im_seuils_dico : " + str(input_im_seuils_dico) + endC)
        print(cyan + "runTDCSeuil() : " + endC + "output_dir : " + str(output_dir) + endC)
        print(cyan + "runTDCSeuil() : " + endC + "input_sea_points : " + str(input_sea_points) + endC)
        print(cyan + "runTDCSeuil() : " + endC + "input_cut_vector : " + str(input_cut_vector) + endC)
        print(cyan + "runTDCSeuil() : " + endC + "input_emprise_vector : " + str(input_emprise_vector) + endC)
        print(cyan + "runTDCSeuil() : " + endC + "simplif : " + str(simplif) + endC)
        print(cyan + "runTDCSeuil() : " + endC + "is_calc_indice_image : " + str(is_calc_indice_image) + endC)
        print(cyan + "runTDCSeuil() : " + endC + "attribute_val_limite : " + str(attribute_val_limite) + endC)
        print(cyan + "runTDCSeuil() : " + endC + "attribute_val_proced : " + str(attribute_val_proced) + endC)
        print(cyan + "runTDCSeuil() : " + endC + "attribute_val_datepr : " + str(attribute_val_datepr) + endC)
        print(cyan + "runTDCSeuil() : " + endC + "attribute_val_precis : " + str(attribute_val_precis) + endC)
        print(cyan + "runTDCSeuil() : " + endC + "attribute_val_contac : " + str(attribute_val_contac) + endC)
        print(cyan + "runTDCSeuil() : " + endC + "attribute_val_type : " + str(attribute_val_type) + endC)
        print(cyan + "runTDCSeuil() : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "runTDCSeuil() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "runTDCSeuil() : " + endC + "channel_order: " + str(channel_order) + endC)
        print(cyan + "runTDCSeuil() : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "runTDCSeuil() : " + endC + "format_raster : " + str(format_raster) + endC)
        print(cyan + "runTDCSeuil() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "runTDCSeuil() : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "runTDCSeuil() : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "runTDCSeuil() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "runTDCSeuil() : " + endC + "overwrite : " + str(overwrite) + endC)

    # Initialisation des constantes
    AUTO = "auto"
    POS_NUMERO_DOSSIER = 2
    REP_NDVI_TDC_SEUIL = "ndvi_TDCSeuil"
    REP_TEMP_BIN_MASK_V = "Temp_Binary_Mask_Vector_"

    ATTR_NAME_REFDOSSIER = "RefDossier"
    ATTR_NAME_NOMIMAGE = "NomImage"
    ATTR_NAME_DATEACQUI = "DateAcqui"
    ATTR_NAME_HEUREACQUI = "HeureAcqui"
    ATTR_NAME_LIMITE = "TdcLimite"
    ATTR_NAME_PROCED = "TdcProced"
    ATTR_NAME_DATEPR = "TdcDatepro"
    ATTR_NAME_PRECIS = "TdcPrecis"
    ATTR_NAME_CONTAC = "TdcContact"
    ATTR_NAME_TYPE = "Type"

    # Repertoire NDVI à conserver!!!
    repertory_ndvi = output_dir + os.sep + REP_NDVI_TDC_SEUIL
    repertory_temp_list = []

    # Création du répertoire de sortie s'il n'existe pas déjà
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Création du répertoire de sortie temporaire s'il n'existe pas déjà
    if not os.path.exists(repertory_ndvi):
        os.makedirs(repertory_ndvi)

    # Exploitation du fichier emprise pour renseigner les informations des attribues
    res_values_dico = {}
    if input_emprise_vector != "":
        # Lecture des attributs de fichier vecteur
        names_attribut_list = getAttributeNameList(input_emprise_vector, format_vector)
        attribute_name_dico = {}
        for name_attribut in names_attribut_list :
            attribute_name_dico[name_attribut] = getAttributeType(input_emprise_vector, name_attribut, format_vector)
        res_values_dico = getAttributeValues(input_emprise_vector, None, None, attribute_name_dico, format_vector)

    # On calcule plusieurs seuils par image, mais différents selon les images
    bin_mask_list = []
    images_list = []
    nb_images = len(input_im_seuils_dico.split())
    image_first_and_seuils = input_im_seuils_dico.split()[0]

    # Création d'une liste d'image
    for elt in input_im_seuils_dico.split():
        images_list.append(elt.split(":")[0])

    if ":" not in image_first_and_seuils:
            print(cyan + "runTDCSeuil() : " + red + bold + "Aucun seuil spécifié ! (Nécessité d'au moins un pour la 1ère image)" + endC, file=sys.stderr)
            sys.exit(1)
    else :
        seuils_first_image_list = image_first_and_seuils.split(":")[1].split(",")

    for i in range(nb_images):
        # Chaque image + seuils (exemple : /path/image_xx.tif:0.1,0,-0.1)
        image_index_and_seuils = input_im_seuils_dico.split()[i]
        seuils_index_image_list = image_index_and_seuils.split(":")[1].split(",")

        # L'image à traiter
        input_image = image_index_and_seuils.split(":")[0]
        image_name = os.path.splitext(os.path.basename(input_image))[0]

        # Création du répertoire temporaire de calcul
        repertory_temp = output_dir + os.sep + REP_TEMP_BIN_MASK_V + image_name
        if not os.path.exists(repertory_temp):
            os.makedirs(repertory_temp)
        repertory_temp_list.append(repertory_temp)

        # Initialisation des champs des attributs
        num_dossier = image_name.split("_")[POS_NUMERO_DOSSIER]
        attribute_val_refdossier = num_dossier
        attribute_val_nomimage = image_name
        attribute_val_datecqui = " "
        attribute_val_heureacqui = " "

        if attribute_val_limite == "" :
            attribute_val_limite = " "
        if attribute_val_proced == "" :
            attribute_val_proced = " "
        if attribute_val_datepr == "" :
            now = datetime.datetime.now()
            attribute_val_datepr = now.strftime("%Y-%m-%d")
        if attribute_val_precis == "" :
            attribute_val_precis = " "
        if attribute_val_contac == "" :
            attribute_val_contac = " "
        if attribute_val_type == "" :
            attribute_val_type = " "

        # Cas ou un fichier d'emprise contenant des données des attributs est present et contient un champs "RefDossier"
        if ATTR_NAME_REFDOSSIER in res_values_dico :

            if num_dossier in res_values_dico[ATTR_NAME_REFDOSSIER] :
                index_dossier = res_values_dico[ATTR_NAME_REFDOSSIER].index(num_dossier)

                if ATTR_NAME_NOMIMAGE in res_values_dico :
                    attribute_val_nomimage = res_values_dico[ATTR_NAME_NOMIMAGE][index_dossier]
                if ATTR_NAME_DATEACQUI in res_values_dico :
                    datecqui_list = res_values_dico[ATTR_NAME_DATEACQUI][index_dossier]
                    attribute_val_datecqui = str(datecqui_list[0]) + "-" + str(datecqui_list[1]) + "-" + str(datecqui_list[2])
                if ATTR_NAME_HEUREACQUI in res_values_dico :
                   attribute_val_heureacqui = res_values_dico[ATTR_NAME_HEUREACQUI][index_dossier]

        # Initialisation de StructAttribute pour la création des champs
        attributes_list = [StructAttribute(ATTR_NAME_REFDOSSIER, ogr.OFTString, 20, attribute_val_refdossier), \
                           StructAttribute(ATTR_NAME_NOMIMAGE, ogr.OFTString, 20, attribute_val_nomimage), \
                           StructAttribute(ATTR_NAME_DATEACQUI, ogr.OFTDate, None,attribute_val_datecqui), \
                           StructAttribute(ATTR_NAME_HEUREACQUI, ogr.OFTString, 14, attribute_val_heureacqui), \
                           StructAttribute(ATTR_NAME_LIMITE, ogr.OFTString, 20, attribute_val_limite), \
                           StructAttribute(ATTR_NAME_PROCED, ogr.OFTString, 30, attribute_val_proced), \
                           StructAttribute(ATTR_NAME_DATEPR, ogr.OFTString, 14, attribute_val_datepr), \
                           StructAttribute(ATTR_NAME_PRECIS, ogr.OFTString, 20, attribute_val_precis), \
                           StructAttribute(ATTR_NAME_CONTAC, ogr.OFTString, 20, attribute_val_contac), \
                           StructAttribute(ATTR_NAME_TYPE, ogr.OFTString, 14, attribute_val_type)]

        # Calcul de l'image NDVI si is_calc_indice_image est à True
        if is_calc_indice_image:
            image_index = repertory_ndvi + os.sep + "image_NDVI_" + os.path.splitext(os.path.basename(images_list[i]))[0] + extension_raster
            if not os.path.exists(input_image):
                print(cyan + "runTDCSeuil() : " + red + bold + "L'image renseignée en entrée : " + input_image + " n'existe pas. Vérifiez le chemin !" + endC, file=sys.stderr)
                sys.exit(1)

            createNDVI(input_image, image_index, channel_order)

        else:
            image_index = seuils_index_image_list[0]
            if os.path.splitext(image_index)[1] != extension_raster :
                print(cyan + "runTDCSeuil() : " + red + bold + "Si vous choisissez de calculer l'image NDVI, mettre l'option -c. Sinon, le 1er paramètre derrière \":\" dans -isd doit être l'image indice (.tif)" + endC, file=sys.stderr)
                sys.exit(1)

        if ":" not in image_index_and_seuils:
            if is_calc_indice_image:
                for t in seuils_first_image_list:
                    if t == AUTO:
                        seuils_list = runCalculSeuil(image_index, output_dir, save_results_intermediate)
                        # Masque centre classe
                        bin_mask_cc = binaryMaskVect(image_index, repertory_temp, float(seuils_list[0]), input_cut_vector, attributes_list, no_data_value, epsg, format_raster, format_vector,  extension_raster, extension_vector, save_results_intermediate, overwrite)
                        # Masque borne inf
                        bin_mask_bi = binaryMaskVect(image_index, repertory_temp, float(v[1]), input_cut_vector, attributes_list, no_data_value, epsg, format_raster, format_vector,  extension_raster, extension_vector, save_results_intermediate, overwrite)
                        # Ajout des masques à la liste
                        bin_mask_list.append(bin_mask_cc)
                        bin_mask_list.append(bin_mask_bi)
                    else:
                        bin_mask = binaryMaskVect(image_index, repertory_temp, float(t), input_cut_vector, attributes_list, no_data_value, epsg, format_raster, format_vector, extension_raster, extension_vector, save_results_intermediate, overwrite)
                        bin_mask_list.append(bin_mask)
            else:
                print(cyan + "runTDCSeuil() : " + red + + bold +  "Renseignez les images NDVI associées et les seuils !" + endC, file=sys.stderr)
                sys.exit(1)

        else:
            if is_calc_indice_image:
                for t in seuils_index_image_list:
                    if t == AUTO:
                        seuils_list = runCalculSeuil(image_index, output_dir, save_results_intermediate)
                        # Masque centre classe
                        bin_mask_cc = binaryMaskVect(image_index, repertory_temp, float(seuils_list[0]), input_cut_vector, attributes_list, no_data_value, epsg, format_raster, format_vector,  extension_raster, extension_vector, save_results_intermediate, overwrite)
                        # Masque borne inf
                        bin_mask_bi = binaryMaskVect(image_index, repertory_temp, float(seuils_list[1]), input_cut_vector, attributes_list, no_data_value, epsg, format_raster, format_vector,  extension_raster, extension_vector, save_results_intermediate, overwrite)
                        # Ajout des masques à la liste
                        bin_mask_list.append(bin_mask_cc)
                        bin_mask_list.append(bin_mask_bi)
                    else:
                        bin_mask = binaryMaskVect(image_index, repertory_temp, float(t), input_cut_vector, attributes_list, no_data_value, epsg, format_raster, format_vector, extension_raster, extension_vector, save_results_intermediate, overwrite)
                        bin_mask_list.append(bin_mask)
            else:
                for j in range(1,len(seuils_index_image_list)):
                    t = seuils_index_image_list[j]
                    if t == AUTO:
                        seuils_list = runCalculSeuil(image_index, output_dir, save_results_intermediate)
                        # Masque centre classe
                        bin_mask_cc = binaryMaskVect(image_index, repertory_temp, float(seuils_list[0]), input_cut_vector, attributes_list, no_data_value, epsg, format_raster, format_vector,  extension_raster, extension_vector, save_results_intermediate, overwrite)
                        # Masque borne inf
                        bin_mask_bi = binaryMaskVect(image_index, repertory_temp, float(seuils_list[1]), input_cut_vector, attributes_list, no_data_value, epsg, format_raster, format_vector,  extension_raster, extension_vector, save_results_intermediate, overwrite)
                        # Ajout des masques à la liste
                        bin_mask_list.append(bin_mask_cc)
                        bin_mask_list.append(bin_mask_bi)
                    else:
                        bin_mask = binaryMaskVect(image_index, repertory_temp, float(t), input_cut_vector, attributes_list, no_data_value, epsg, format_raster, format_vector, extension_raster, extension_vector, save_results_intermediate, overwrite)
                        bin_mask_list.append(bin_mask)

    # Constitution du dictionnaire associant chaque image aux vecteurs NDVI associés, pour l'entrée dans PolygonMerToTDC
    im_ndvivect_dico = ""
    if is_calc_indice_image:
        ndvi_mask_index = 0
        for i in range(nb_images):
            # Chaque image + seuils (exemple : /path/image_xx.tif:0.1,0,-0.1)
            image_index_and_seuils = input_im_seuils_dico.split()[i]
            input_image = image_index_and_seuils.split(":")[0]
            seuils_index_image_list = image_index_and_seuils.split(":")[1].split(",")
            is_presence_auto = False

            im_ndvivect_dico += input_image + ":"

            # Si des seuils sont renseignés seulement pour la 1ère image
            if ":" not in image_index_and_seuils:
                # Parcours des seuils de la première image
                for seuil in seuils_first_image_list:
                    if seuil == AUTO:
                        is_presence_auto = True

                # S'il y a un seuil à "auto" dans la boucle, on parcourt un tour de plus (auto = borneinf + centre classe)
                if is_presence_auto == True:
                    nb_iter = len(seuils_first_image_list)
                else :
                    nb_iter = len(seuils_first_image_list)-1

                for s in range(nb_iter):
                    im_ndvivect_dico += bin_mask_list[ndvi_mask_index] + ","
                    ndvi_mask_index = ndvi_mask_index + 1
                im_ndvivect_dico += bin_mask_list[ndvi_mask_index] + " "

            # Si au moins un seuil est renseigné pour chacune des autres images
            else :
                # Parcours des seuils de l'image
                for seuil in seuils_index_image_list:
                    if seuil == AUTO:
                        is_presence_auto = True

                # S'il y a un seuil à "auto" dans la boucle, on parcourt un tour de plus (auto = borneinf + centre classe)
                if is_presence_auto :
                    nb_iter = len(seuils_index_image_list)
                else :
                    nb_iter = len(seuils_index_image_list)-1

                for s in range(nb_iter):
                    im_ndvivect_dico += bin_mask_list[ndvi_mask_index] + ","
                    ndvi_mask_index = ndvi_mask_index + 1
                im_ndvivect_dico += bin_mask_list[ndvi_mask_index] + " "
                ndvi_mask_index = ndvi_mask_index + 1
    else:
        ndvi_mask_index = 0
        for i in range(nb_images):
            # Chaque image + seuils (exemple : /path/image_xx.tif:0.1,0,-0.1)
            image_index_and_seuils = input_im_seuils_dico.split()[i]
            input_image = image_index_and_seuils.split(":")[0]
            seuils_index_image_list = image_index_and_seuils.split(":")[1].split(",")
            is_presence_auto = False

            im_ndvivect_dico += input_image + ":"
            if ":" not in image_index_and_seuils:
                print(cyan + "runTDCSeuil() : " + red + bold + "Renseignez les images NDVI associées et les seuils !" + endC, file=sys.stderr)
                sys.exit(1)

            # Si au moins un seuil est renseigné pour chacune des autres images
            else :
                # Parcours des seuils de l'image
                for seuil in seuils_index_image_list:
                    if seuil == AUTO :
                        is_presence_auto = True

                # S'il y a un seuil à "auto" dans la boucle, on parcourt un tour de plus (auto = borneinf + centre classe)
                if is_presence_auto :
                    nb_iter = len(seuils_index_image_list)
                else :
                    nb_iter = len(seuils_index_image_list)-1
                for s in range(1,nb_iter):
                    im_ndvivect_dico += bin_mask_list[ndvi_mask_index] + ","
                    ndvi_mask_index = ndvi_mask_index + 1
                im_ndvivect_dico += bin_mask_list[ndvi_mask_index] + " "
                ndvi_mask_index = ndvi_mask_index + 1

    im_ndvivect_dico = im_ndvivect_dico[:-1]
    tdc_shp = polygonMerToTDC(im_ndvivect_dico, output_dir, input_sea_points, True, simplif, input_cut_vector, 3.5, -3.5, no_data_value, path_time_log, epsg, format_vector, extension_raster, extension_vector, save_results_intermediate, overwrite)

    # Suppression des répertoires temporaires
    for repertory_temp in repertory_temp_list :
        if not save_results_intermediate and os.path.exists(repertory_temp):
            shutil.rmtree(repertory_temp)

    # Mise à jour du Log
    ending_event = "runTDCSeuil() : Select TDC Seuil ending : "
    timeLine(path_time_log,ending_event)

    return tdc_shp

###########################################################################################################################################
# FONCTION binaryMaskVect                                                                                                                 #
###########################################################################################################################################
# ROLE:
#    Création d'un masque binaire vecteur à partir d'une image raster et d'un seuil
#
# ENTREES DE LA FONCTION :
#    input_image : Image à traiter
#    output_dir : Répertoire de sortie pour les traitements
#    threshold : seuil utilisé pour le masque binaire
#    input_cut_vector : fichier de découpe du masque binaire pour réduction de la zone à vectoriser (gain en temps de calcul)
#    attributes_list : liste des noms et formats des champs ansi que leur valeur
#    no_data_value : Valeur de  pixel du no data
#    epsg : Code EPSG des fichiers
#    format_raster  : format des raster de sortie, par defaut = 'GTiff'
#    format_vector  : format des vecteurs de sortie, par defaut = 'ESRI Shapefile'
#    extension_raster : extension des fichiers raster de sortie, par defaut = '.tif'
#    extension_vector : extension du fichier vecteur de sortie, par defaut = '.shp'
#    save_results_intermediate : fichiers de sorties intermediaires non nettoyees, par defaut = False
#    overwrite : supprime ou non les fichiers existants ayant le meme nom
#
# SORTIES DE LA FONCTION :
#    Le fichier contenant le masque binaire terre/mer
#    Eléments modifiés aucun
#

def binaryMaskVect(input_image, output_dir, threshold, input_cut_vector, attributes_list, no_data_value, epsg, format_raster="GTiff", format_vector="ESRI Shapefile", extension_raster=".tif", extension_vector=".shp", save_results_intermediate=False, overwrite=True):

    # Affichage des paramètres
    if debug >= 3:
        print(bold + green + "Variables dans le binaryMaskVect - Variables générales" + endC)
        print(cyan + "binaryMaskVect() : " + endC + "input_image : " + str(input_image) + endC)
        print(cyan + "binaryMaskVect() : " + endC + "output_dir : " + str(output_dir) + endC)
        print(cyan + "binaryMaskVect() : " + endC + "threshold : " + str(threshold) + endC)
        print(cyan + "binaryMaskVect() : " + endC + "input_cut_vector : " + str(input_cut_vector) + endC)
        print(cyan + "binaryMaskVect() : " + endC + "format_raster : " + str(format_raster) + endC)
        print(cyan + "binaryMaskVect() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "binaryMaskVect() : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "binaryMaskVect() : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "binaryMaskVect() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "binaryMaskVect() : " + endC + "overwrite : " + str(overwrite) + endC)


    image_name = os.path.splitext(os.path.basename(input_image))[0]
    binary_mask = output_dir + os.sep + "bin_mask_" + image_name + "_" + str(threshold).replace('.','_') + extension_raster
    binary_mask_decoup = output_dir + os.sep + "bin_mask_decoup_" + image_name + "_" + str(threshold).replace('.','_') + extension_raster
    binary_mask_vector = output_dir + os.sep + "bin_mask_vect_" + image_name + "_" + str(threshold).replace('.','_') + extension_vector

    # Création du répertoire de sortie s'il n'existe pas déjà
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Suppression des fichiers temporaires pour les calculs
    if os.path.exists(binary_mask):
        removeFile(binary_mask)

    if os.path.exists(binary_mask_decoup):
        removeFile(binary_mask_decoup)

    if os.path.exists(binary_mask_vector):
        if overwrite :
            removeVectorFile(binary_mask_vector, format_vector)
        else :
            return binary_mask_vector

    # Création du masque binaire
    createBinaryMask(input_image, binary_mask, threshold, False)

    if input_cut_vector != "":
        # Découpe du raster
        cutImageByVector(input_cut_vector, binary_mask, binary_mask_decoup, None, None, no_data_value, epsg, format_raster, format_vector)
    else:
        binary_mask_decoup = binary_mask

    # Vectorisation du masque binaire découpé
    polygonizeRaster(binary_mask_decoup, binary_mask_vector, image_name, "id", format_vector)

    # Ajout des champs au fichier vecteur créé
    for attribute in attributes_list :
        addNewFieldVector(binary_mask_vector, attribute.name, attribute.ogrType, attribute.value, attribute.width, None, format_vector)

    # Suppresions des fichiers intermediaires inutiles et reperoire temporaire
    if not save_results_intermediate:
        removeFile(binary_mask)
        removeFile(binary_mask_decoup)

    return binary_mask_vector

###########################################################################################################################################
# MISE EN PLACE DU PARSER                                                                                                                 #
###########################################################################################################################################

# Code executé seulement dans le cas ou le script est lancé depuis une ligne de commande
# Il n'est pas executé lors d'un import TDCSeuil.py
# Exemple de lancement en ligne de commande:
# python /home/scgsi/Documents/ChaineTraitement/ScriptsLittoral/TDCSeuil.py -isd "/mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Test_TDCSeuil/image1.tif:0.1,0.2 /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Test_TDCSeuil/image2.tif:-0.1,-0.2" -mer /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Test_TDCSeuil/points_mer.shp -outd /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Tests/Tests_TDCSeuil -d /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/08_Donnees/Histolitt/TCH_simplifie2_buffer270_adapte_mediterranee_simpl200.shp -c -chao Red Green Blue NIR

def main(gui=False):

    parser = argparse.ArgumentParser(prog="TDCSeuil", description=" \
    Info : Creating a shapefile (.shp) containing the coastline jet de rive from a tif image, extracted with a threshold method.\n\
    Objectif   : Cartographie du trait de côte jet de rive par seuillage, à partir d'une image format tif. \n\
    Example : python /home/scgsi/Documents/ChaineTraitement/ScriptsLittoral/TDCSeuil.py \n\
                            -isd \"/mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Test_TDCSeuil/image1.tif:0.1,0,-0.1 /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Test_TDCSeuil/image2.tif\" \n\
                            -outd /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Test_TDCSeuil/Result2 \n\
                            -mer /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Test_TDCSeuil/points_mer.shp \n\
                            -c \n\
                            -chao Red Green Blue NIR \n\
                            -d /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/08_Donnees/Histolitt/TCH_simplifie2_buffer270_adapte_mediterranee_simpl200.shp")

    parser.add_argument('-isd','--input_im_seuils_dico', default="", help="Dictionnary of input images (.tif) and thresholds (float) associated, or if is_calc_indice_image NOT chosen, input images are calculated index images.", type=str, required=True)
    parser.add_argument('-outd','--output_dir', default="",help="Output directory.", type=str, required=True)
    parser.add_argument('-mer','--input_sea_points', default="",help="Input vector file containing points in the sea (.shp).", type=str, required=True)
    parser.add_argument('-d','--input_cut_vector', default="", help="Vector file containing shape of the area to keep (.shp).", type=str, required=False)
    parser.add_argument('-e','--input_emprise_vector', default="", help="Vector file containing shape of the emprise (.shp).", type=str, required=False)
    parser.add_argument('-simp','--simplif', default=1.0, help="Value for simplification of the coastline", type=float, required=False)
    parser.add_argument('-c','--is_calc_indice_image', action='store_true', default=False, help="If True : images in dictionary are raw images, calculate NDVI images from them. If False: images in dictionary are index images.", required=False)
    parser.add_argument('-chao','--channel_order',nargs="+", default=['Red','Green','Blue','NIR'],help="Type of multispectral image : rapideye or spot6 or pleiade. By default : [Red,Green,Blue,NIR]",type=str,required=False)
    parser.add_argument('-at_v_limite','--attribute_val_limite', default="Milieu jet de rive", help="Attribute value of field TDC_Limite.", type=str, required=False)
    parser.add_argument('-at_v_proced','--attribute_val_proced', default="Numerisation semi-automatique", help="Attribute value of field TDC_proced.", type=str, required=False)
    parser.add_argument('-at_v_datepr','--attribute_val_datepr', default="", help="Attribute value of field TDC_Datepr.", type=str, required=False)
    parser.add_argument('-at_v_precis','--attribute_val_precis', default="Metrique", help="Attribute value of field TDC_precis.", type=str, required=False)
    parser.add_argument('-at_v_contac','--attribute_val_contac', default="Cerema", help="Attribute value of field TDC_Contac.", type=str, required=False)
    parser.add_argument('-at_v_type','--attribute_val_type', default="Pleiades", help="Attribute value of satellite type.", type=str, required=False)
    parser.add_argument('-epsg','--epsg',default=2154,help="Option : Projection EPSG for the layers. By default : 2154", type=int, required=False)
    parser.add_argument('-ndv','--no_data_value', default=0, help="Option : Value of the pixel no data. By default : 0", type=int, required=False)
    parser.add_argument('-raf','--format_raster', default="GTiff", help="Option : Format output image raster. By default : GTiff (GTiff, HFA...)", type=str, required=False)
    parser.add_argument('-vef','--format_vector',default="ESRI Shapefile",help="Option : Vector format. By default : ESRI Shapefile", type=str, required=False)
    parser.add_argument('-rae','--extension_raster', default=".tif", help="Option : Extension file for image raster. By default : '.tif'", type=str, required=False)
    parser.add_argument('-vee','--extension_vector',default=".shp",help="Option : Extension file for vector. By default : '.shp'", type=str, required=False)
    parser.add_argument('-log','--path_time_log',default="",help="Name of log", type=str, required=False)
    parser.add_argument('-sav','--save_results_inter',action='store_true',default=False,help="Option : Save or delete intermediate result after the process. By default, False", required=False)
    parser.add_argument('-now','--overwrite',action='store_false',default=True,help="Option : Overwrite files with same names. By default : True", required=False)
    parser.add_argument('-debug','--debug',default=3,help="Option : Value of level debug trace, default : 3 ",type=int, required=False)
    args = displayIHM(gui, parser)

    # Récupération des images à traiter
    if args.input_im_seuils_dico != None :
        input_im_seuils_dico = args.input_im_seuils_dico

    # Récupération du dossier des traitements en sortie
    if args.output_dir != None :
        output_dir = args.output_dir

    # Récupération de la couche points mer
    if args.input_sea_points != None :
        input_sea_points = args.input_sea_points

    # Récupération du shapefile de découpe pour la simplification du trait obtenu
    if args.input_cut_vector != None :
        input_cut_vector = args.input_cut_vector

    # Récupération du shapefile des emprises des images
    if args.input_emprise_vector != None :
        input_emprise_vector = args.input_emprise_vector

    # Récupération de la valeur de tolérance pour la simplification du trait de côte
    if args.simplif != None :
        simplif = args.simplif

    # Récupération de la valeur (vrai/faux) du calcul de l'image indice
    if args.is_calc_indice_image != None :
        is_calc_indice_image = args.is_calc_indice_image

    # Récupération de l'ordre des bandes de l'image pour le calcul de l'indice
    if args.channel_order != None:
        channel_order = args.channel_order

    # Récupération des valeurs des des attributs
    if args.attribute_val_limite != None :
        attribute_val_limite = args.attribute_val_limite
    if args.attribute_val_proced != None :
        attribute_val_proced = args.attribute_val_proced
    if args.attribute_val_datepr != None :
        attribute_val_datepr = args.attribute_val_datepr
    if args.attribute_val_precis != None :
        attribute_val_precis = args.attribute_val_precis
    if args.attribute_val_contac != None :
        attribute_val_contac = args.attribute_val_contac
    if args.attribute_val_type != None :
        attribute_val_type = args.attribute_val_type

    # Récupération de la projection
    if args.epsg != None:
        epsg = args.epsg

    # Récupération du parametre no_data_value
    if args.no_data_value!= None:
        no_data_value = args.no_data_value

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
        print(cyan + "TDCSeuil : " + endC + "input_im_seuils_dico : " + str(input_im_seuils_dico) + endC)
        print(cyan + "TDCSeuil : " + endC + "output_dir : " + str(output_dir) + endC)
        print(cyan + "TDCSeuil : " + endC + "input_sea_points : " + str(input_sea_points) + endC)
        print(cyan + "TDCSeuil : " + endC + "input_cut_vector : " + str(input_cut_vector) + endC)
        print(cyan + "TDCSeuil : " + endC + "input_emprise_vector : " + str(input_emprise_vector) + endC)
        print(cyan + "TDCSeuil : " + endC + "simplif : " + str(simplif) + endC)
        print(cyan + "TDCSeuil : " + endC + "is_calc_indice_image : " + str(is_calc_indice_image) + endC)
        print(cyan + "TDCSeuil : " + endC + "channel_order : " + str(channel_order) + endC)
        print(cyan + "TDCSeuil : " + endC + "attribute_val_limite : " + str(attribute_val_limite) + endC)
        print(cyan + "TDCSeuil : " + endC + "attribute_val_proced : " + str(attribute_val_proced) + endC)
        print(cyan + "TDCSeuil : " + endC + "attribute_val_datepr : " + str(attribute_val_datepr) + endC)
        print(cyan + "TDCSeuil : " + endC + "attribute_val_precis : " + str(attribute_val_precis) + endC)
        print(cyan + "TDCSeuil : " + endC + "attribute_val_contac : " + str(attribute_val_contac) + endC)
        print(cyan + "TDCSeuil : " + endC + "attribute_val_type : " + str(attribute_val_type) + endC)
        print(cyan + "TDCSeuil : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "TDCSeuil : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "TDCSeuil : " + endC + "format_raster : " + str(format_raster) + endC)
        print(cyan + "TDCSeuil : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "TDCSeuil : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "TDCSeuil : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "TDCSeuil : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "TDCSeuil : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "TDCSeuil : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "TDCSeuil : " + endC + "debug : " + str(debug) + endC)

    # Fonction générale
    runTDCSeuil(input_im_seuils_dico, output_dir, input_sea_points, input_cut_vector, input_emprise_vector, simplif, is_calc_indice_image, attribute_val_limite, attribute_val_proced, attribute_val_datepr, attribute_val_precis, attribute_val_contac, attribute_val_type, no_data_value, path_time_log, channel_order, epsg, format_raster, format_vector, extension_raster, extension_vector, save_results_intermediate, overwrite)

# ================================================

if __name__ == '__main__':
  main(gui=False)


