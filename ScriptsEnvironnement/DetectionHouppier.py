#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT QUI APPLIQUE LA DETECTION DES HOUPPIERS DES ARBRES                                                                                 #
#                                                                                                                                           #
#############################################################################################################################################
"""
Nom de l'objet : DetectionHouppier.py
Description :
-------------
Objectif : appliquer la recherche des houppiers des arbres
Rq : utilisation des OTB Applications :  otbcli_BandMath, otbcli_BandMathX, otbcli_RadiometricIndices, otbcli_Segmentation

Date de creation : 04/08/2028
----------
Histoire :
----------
Origine :
methode basee sur papier de l ONERA :
   « Individual Tree Crown Delineation Method Based on Multi-Criteria Graph Using Geometric and Spectral Information:
   Application to Several Temperate Forest Sites », Deluzet et al., 2022
   https://doi.org/10.3390/rs14051083
auteur : Mathilde Segaud, 2023, Cerema groupe OSECC
adapte par Emma Bousquet, 2023, Cerema groupe OSECC
formatage code par Gilles Fouvet, 2023, Cerema groupe OSECC
-----------------------------------------------------------------------------------------------------
Modifications :

------------------------------------------------------
A Reflechir/A faire :

"""

import os,sys,glob, time, string, argparse, shutil, platform, math
import numpy as np
from PIL import Image
from skimage import io
from osgeo import gdal, ogr
import networkx as nx

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 3

###################### FONCTIONS ########################################
# Pour y accéder dans un script : from fcts_Affichage import bold,black,red,green,yellow,blue,magenta,cyan,endC
osSystem = platform.system()
if 'Windows' in osSystem :
    # EFFETS
    bold = ""
    talic = ""
    underline = ""
    blink = ""
    rapidblink = ""
    beep = ""

    # COULEURS DE TEXTE
    black = ""
    red = ""
    green = ""
    yellow = ""
    blue = ""
    magenta = ""
    cyan = ""
    white = ""

    # COULEUR DE FOND
    BGblack = ""
    BGred = ""
    BGgreen = ""
    BGyellow = ""
    BGblue = ""
    BGmagenta = ""
    BGcyan = ""
    BGwhite = ""

    endC = ""

elif 'Linux' in osSystem :
    # EFFETS
    bold = "\033[1m"
    italic = "\033[3m"
    underline = "\033[4m"
    blink = "\033[5m"
    rapidblink = "\033[6m"
    beep = "\007"

    # COULEURS DE TEXTE
    black = "\033[30m"
    red = "\033[31m"
    green = "\033[32m"
    yellow = "\033[33m"
    blue = "\033[34m"
    magenta = "\033[35m"
    cyan = "\033[36m"
    white = "\033[37m"

    # COULEUR DE FOND
    BGblack = "\033[40m"
    BGred = "\033[41m"
    BGgreen = "\033[42m"
    BGyellow = "\033[43m"
    BGblue = "\033[44m"
    BGmagenta = "\033[45m"
    BGcyan = "\033[46m"
    BGwhite = "\033[47m"

    endC = "\033[0m"

#########################################################################
# FONCTION timeLine()                                                   #
#########################################################################
def timeLine(path_timelog,step):
    """
    #   Role : Fonction pour chronometrer une tache, placer le code DebutTache = datetime.now() avant la tache a chronometrer.
    #   Paramètres en entrée :
    #      path_timelog : nom du chemin et du fichier log
    #      step : texte affiché devant l'heure sauvegardée
    """
    hour = time.strftime('%d/%m/%y %H:%M:%S',time.localtime())
    time_str = step + hour + '\n'
    if path_timelog != "":
        logfile = open(path_timelog, 'a')
        logfile.write(time_str)
        logfile.close()
    else :
        print(blue + time_str + endC)
    return

#########################################################################
# FONCTION giveListCoordsSgtsImg()                                      #
#########################################################################
def giveListCoordsSgtsImg(img_sgts):
    """
        Rôle :
            Fonction qui recupere la liste des coordonnées x et y des pixels par segments
            ie ensemble des pixels appartennant au même segment
        Entree :
            img_sgts : matrice de l'image segments
        Sortie :
            x_list : liste des coordonnées x des pixels appartenant a chaque segment
            y_list : liste des coordonnées y des pixels appartenant a chaque segment
    """
    x_list = []
    y_list = []
    li_uni_sgts = np.unique(img_sgts) #copie de l'image segmentée végétation
    for el in li_uni_sgts:
        # Renvoie la liste des coords de pixels qui
        # Appartiennent au même segment dont le label est la valeur el
        li_pxl_sgt = np.where(img_sgts == el)
        x_list.append(li_pxl_sgt[0])
        y_list.append(li_pxl_sgt[1])
    return x_list, y_list

#########################################################################
# FONCTION giveCoordsMaxSGTS()                                          #
#########################################################################
def giveCoordsMaxSGTS(x_list, y_list, img_mnh):
    """
        Rôle :
            Fonction qui renvoie les valeurs de hauteur max et les coordonnées
            de ces pixel dans la matrice de l'image segmentée
            (une valeur max. par segment)
        Entree :
            x_list : liste des coordonnées x des pixels appartenant a chaque segment
            y_list : liste des coordonnées y des pixels appartenant a chaque segment
            img_mnh : matrice de l'image mnh
        Sortie :
            pts_list : liste des points [xhmax, yhmax]
    """
    pts_list = []
    for sgt in range(len(x_list)): # On rentre dans chaque segment sgt
        valx = x_list[sgt][0]
        valy = y_list[sgt][0]
        if valx<np.shape(img_mnh)[0] and valy<np.shape(img_mnh)[1]: #pour ne pas aller au-dela de la taille du MNH
            hmax = img_mnh[valx,valy] # Valeur de hauteur du pixel du segment z
            coords_max = [valx,valy]  # Coords du pixel
            for pxl in range(1,len(x_list[sgt])): # Dans le segment z, on parcourt tous les pixels et on cherche le hmax et les coords max
                x = x_list[sgt][pxl]
                y = y_list[sgt][pxl]
                if x<np.shape(img_mnh)[0] and y<np.shape(img_mnh)[1]:
                    if img_mnh[x,y] > hmax:
                        hmax = img_mnh[x,y]
                        coords_max = [x,y]
            pts_list.append(coords_max)

    return pts_list

#########################################################################
# FONCTION searchLinksPts()                                             #
#########################################################################
def searchLinksPts(pt, pts_list, links):
    """
        Rôle :
            Fonction qui crée une liste de tuple (u,v) qui correspondent aux
            liens entre un point max d'origine et tous les autres points max de la matrice
            selon un critère de distance
            u --> point d'origine et v --> point de chute
        Entree :
            pt : valeur du point d'origine traité
            pts_list : liste des coordonnées des points max
            l_droites : liste des liens
        Sortie :
            l_droites : liste des liens remplie en partant du point d'origine
    """
    x1 = pts_list[pt][0]
    y1 = pts_list[pt][1]
    for i in range(len(pts_list)):
        if pts_list[i] != pts_list[pt]:
            x2 = pts_list[i][0]
            y2 = pts_list[i][1]
            dh = math.sqrt((x1-x2)**2+(y1-y2)**2)
            if dh <= 10 :
                links.append((pt,i))
    return links

#########################################################################
# FONCTION createAllLinks()                                             #
#########################################################################
def createAllLinks(pts_list):
    """
        Rôle :
            Fonction qui créé la liste des liens à représenter sur le graphe
        Entree :
            pts_list : liste des coordonnées de points max
        Sortie :
            pos : dictionnaire {valeur point : (coordx,coordy)}
            links : liste des tuples de liens de l'image
    """
    pos = {}
    links = []
    links = searchLinksPts(0, pts_list, links)
    pos[0]= (pts_list[0][0],pts_list[0][1])
    for el in range(1,len(pts_list)):
        pos[el]=(pts_list[el][0],pts_list[el][1])
        links = searchLinksPts(el, pts_list, links)

    return pos, links

#########################################################################
# FONCTION cleanGraph()                                                 #
#########################################################################
def cleanGraph(graph, pos, links, mat_mnh):
    """
        Rôle :
            Fonction qui supprime les liens entre points ne rentrants pas dans les conditions
            de distance et de hauteur
        Entree :
            graph : graphe
            pos : dictionnaire {valeur point : (coordx,coordy)}
            links : liste des tuples de liens de l'image
            mat_mnh : matrice de l'image MNH
        Sortie :
            aucune
    """
    for el in links:
        el1 = el[0]
        el2 = el[1]
        coords_el1 = pos.get(el1)
        coords_el2 = pos.get(el2)
        if abs(mat_mnh[coords_el1[0]][coords_el1[1]]-mat_mnh[coords_el2[0]][coords_el2[1]])>1.1 and graph.has_edge(el1,el2) == True:
            graph.remove_edge(el1,el2)

    return

#########################################################################
# FONCTION clustSgtOneNode()                                            #
#########################################################################
def clustSgtOneNode(node, li_node, sgts, pos):
    """
        Rôle :
            Fonction qui regroupe les segments en un super-segment pour un point max donné
        Entrée :
            node : valeur du point max d'origine
            li_node : liste des points max rattachés au point lax d'origine
            sgts : matrice de l'image segmentée
            pos : dictionnaire des points du graphes contenant la valeur des points et leur position dans le graphe et dans la matrice d'image segmentée
        Sortie :
            sgts : matrice d'image segmentée où les segments doivent correspondrent aux houppiers
    """
    num_sgt_origin = sgts[pos.get(node)[0], pos.get(node)[1]] # Label du segment d'origine
    for key in li_node.keys():
        coord_img = pos.get(key)
        num_sgt = sgts[coord_img[0], coord_img[1]]
        if num_sgt != num_sgt_origin : # Si le pixel accroché au noeud d'origine n'appartient pas déjà au même segment
            sgts[sgts==num_sgt]=num_sgt_origin  # On attribut le nouveau label au point lié dans la matrice de l'image segmentée

    return sgts

#########################################################################
# FONCTION clustSgtInCrown()                                            #
#########################################################################
def clustSgtInCrown(graph, sgts_c, pos):
    """
        Rôle :
            Fonction qui attribue les mêmes valeurs aux pixels appartenants au même segment de houppier dans une matrice image segmentée
        Entree :
            G : graphe
            sgts_c : copie de la matrice de l'image segmentée
            pos : dictionnaire des
        Sortie :
            sgts :
    """
    nodes = list(graph.nodes) # Liste les points du graphe
    edges = list(graph.edges) # Liste les droites reliants les points du graphe
    for node in nodes:
        li_node = graph[node] # Recupere liste des points reliésau point "node"
        sgts = clustSgtOneNode(node,li_node, sgts_c, pos)

    return sgts

#########################################################################
# FONCTION writeImage1B()                                               #
#########################################################################
def writeImage1B(filename, arr, dataset_input, format_raster="GTiff"):
    """
        Rôle :
            Fonction d'écrite d'une image Geotiff
        Entree :
            filename : chemin absolu de l'image que l'on souhaite creer
            arr : image en array que l'on souhaite creer
            dataset_input : image a partir de laquelle on va recuperer les infos pour le georeferencement
    """
    if arr.dtype == np.float32:
        arr_type = gdal.GDT_Float32
    else:
        arr_type = gdal.GDT_Int32

    driver = gdal.GetDriverByName(format_raster)
    dataset_out = driver.Create(filename, arr.shape[1], arr.shape[0], 1, arr_type)
    dataset_out.SetProjection(dataset_input.GetProjection())
    dataset_out.SetGeoTransform(dataset_input.GetGeoTransform())
    band = dataset_out.GetRasterBand(1)
    band.WriteArray(arr[:,:])
    band.FlushCache()
    band.ComputeStatistics(False)
    dataset_out = None

    return

###########################################################################################################################################
# FONCTION detecterHouppier()                                                                                                             #
###########################################################################################################################################
def detecterHouppier(image_input, image_mnh_input, houppier_image_output, houppier_vector_output, threshold_mnh_value, threshold_ndvi_value,  path_time_log, ram_otb=0, format_raster='GTiff', format_vector='ESRI Shapefile', extension_raster=".tif", extension_vector=".shp", save_results_intermediate=False, overwrite=True):
    """
        ROLE:
            detecter les houppiers des arbres dans une image

        ENTREES DE LA FONCTION :
            image_input : image à traiter
            image_mnh_input : fichier MNH d'entrée
            houppier_image_output : image des houppiers de sortie
            houppier_vector_output : vecteur des houppiers de sortie
            threshold_mnh_value : seuil du fichier MNH
            threshold_ndvi_value : seuil du fichier NDVI
            path_time_log : le fichier de log de sortie
            ram_otb : memoire RAM disponible pour les applications OTB
            format_raster : Format de l'image de sortie, par défaut : GTiff
            format_vector : format du fichier vecteur. Optionnel, par default : 'ESRI Shapefile'
            extension_raster : extension des fichiers raster de sortie, par defaut = '.tif'
            extension_vector : extension du fichier vecteur de sortie, par defaut = '.shp'
            save_results_intermediate : fichiers de sorties intermediaires non nettoyées, par defaut = False
            overwrite : supprime ou non les fichiers existants ayant le meme nom, par defaut a True

        SORTIES DE LA FONCTION :
            aucun

    """

    # Mise à jour du Log
    starting_event = "detecterHouppier() : detect houppier on image starting : "
    timeLine(path_time_log,starting_event)

    if debug >= 2:
        print(bold + green + "detecterHouppier() : Variables dans la fonction" + endC)
        print(cyan + "detecterHouppier() : " + endC + "image_input : " + str(image_input) + endC)
        print(cyan + "detecterHouppier() : " + endC + "image_mnh_input : " + str(image_mnh_input) + endC)
        print(cyan + "detecterHouppier() : " + endC + "houppier_image_output : " + str(houppier_image_output) + endC)
        print(cyan + "detecterHouppier() : " + endC + "houppier_vector_output : " + str(houppier_vector_output) + endC)
        print(cyan + "detecterHouppier() : " + endC + "threshold_mnh_value : " + str(threshold_mnh_value) + endC)
        print(cyan + "detecterHouppier() : " + endC + "threshold_ndvi_value : " + str(threshold_ndvi_value) + endC)
        print(cyan + "detecterHouppier() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "detecterHouppier() : " + endC + "ram_otb : " + str(ram_otb) + endC)
        print(cyan + "detecterHouppier() : " + endC + "format_raster : " + str(format_raster) + endC)
        print(cyan + "detecterHouppier() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "detecterHouppier() : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "detecterHouppier() : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "detecterHouppier() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "detecterHouppier() : " + endC + "overwrite : " + str(overwrite) + endC)

    # CONSTANTES
    CODAGE_8B = "uint8"
    CODAGE_16B = "uint16"
    PREFIX_TMP = "tmp_"
    SUFFIX_NDVI = "_ndvi"
    SUFFIX_THRESHOLD = "_seuil"
    SUFFIX_HIGH_VEGETATION = "_veghaute"
    SUFFIX_MASK = "_masque"
    SUFFIX_SEGMENTS = "_segments"
    SUFFIX_SIMPLE = "_simple"

    # Vérification de l'existence d'une image des houppiers et des repertoires
    check = os.path.isfile(houppier_image_output)
    directory_output = os.path.dirname(houppier_image_output)
    base_name_input = os.path.splitext(os.path.basename(image_input))[0]
    base_name_output = os.path.splitext(os.path.basename(houppier_image_output))[0]

    # Si oui et si la vérification est activée, passage à l'étape suivante
    if check and not overwrite :
        print(cyan + "detecterHouppier() : " + bold + green +  "Image already traited : " + str(houppier_image_output) + "." + endC)
    # Si non ou si la vérification est désactivée, application du filtre
    else :
        # Tentative de suppresion du fichier
        try:
            if os.path.isfile(houppier_image_output) :
                os.remove(houppier_image_output)
            # Supression du vecteur
            if os.path.isfile(houppier_vector_output) :
                driver = ogr.GetDriverByName(format_vector)
                driver.DeleteDataSource(houppier_vector_output)
            # Supression du repertoire temporaire
            if os.path.isdir(directory_tmp) :
               shutil.rmtree(directory_tmp)

        except Exception:
            # Ignore l'exception levée si le fichier n'existe pas (et ne peut donc pas être supprimé)
            pass

        ################ ETAPE 0 : CREATION DES  REPERTOIRES ###############
        if not os.path.isdir(directory_output):
            os.makedirs(directory_output)
        directory_tmp = directory_output + os.sep + PREFIX_TMP + base_name_output
        if not os.path.isdir(directory_tmp):
            os.makedirs(directory_tmp)

        ################ ETAPE 1 : EXTRACTION DE LA  VEGETATION ###############
        if debug >= 2:
            print(cyan + "detecterHouppier() : " + bold + green + "################ EXTRACTION DE LA VEGETATION ###############" + endC)

        # Création du ndvi
        ndvi_file_output = directory_tmp + os.sep + base_name_input + SUFFIX_NDVI + extension_raster
        command = "otbcli_RadiometricIndices -in " + image_input + " -list Vegetation:NDVI -channels.red 1 -channels.nir 4 " + " -out " + ndvi_file_output
        if ram_otb > 0:
            command += " -ram %d" %(ram_otb)
        exit_code = os.system(command)
        if exit_code != 0:
            print(command)
            raise NameError (cyan + "detecterHouppier() : " + bold + red + "!!! Une erreur c'est produite au cours du traitement de l'image : " + image_input + ". Voir message d'erreur." + endC)

        # Seuillage du ndvi
        threshold_ndvi_file_output = directory_tmp + os.sep + base_name_input + SUFFIX_NDVI + SUFFIX_THRESHOLD + extension_raster
        expression = "\"im1b1 > %s?1:0\"" %(str(threshold_ndvi_value))
        command = "otbcli_BandMath -il %s -out %s %s -exp %s" %(ndvi_file_output, threshold_ndvi_file_output, CODAGE_8B, expression)
        if ram_otb > 0:
            command += " -ram %d" %(ram_otb)
        exit_code = os.system(command)
        if exit_code != 0:
            print(command)
            raise NameError (cyan + "detecterHouppier() : " + bold + red + "!!! Une erreur c'est produite au cours du traitement de l'image : " + ndvi_file_output + ". Voir message d'erreur." + endC)

        ################ ETAPE 2 : SUPPRESSION DE LA VEGETATION BASSE ###############
        if debug >= 2:
            print(cyan + "detecterHouppier() : " + bold + green + "################ SUPPRESSION DE LA VEGETATION BASSE ###############" + endC)

        # Seuillage de la végétation haute
        threshold_ndvi_high_vegetation_file_output = directory_tmp + os.sep + base_name_input + SUFFIX_NDVI + SUFFIX_THRESHOLD + SUFFIX_HIGH_VEGETATION + extension_raster
        expression = "\"im1b1*(im2b1>%s)\"" %(str(threshold_mnh_value))
        command = "otbcli_BandMath -il %s %s -out %s %s -exp %s" %(threshold_ndvi_file_output, image_mnh_input, threshold_ndvi_high_vegetation_file_output, CODAGE_8B, expression)
        if ram_otb > 0:
            command += " -ram %d" %(ram_otb)
        exit_code = os.system(command)
        if exit_code != 0:
            print(command)
            raise NameError (cyan + "detecterHouppier() : " + bold + red + "!!! Une erreur c'est produite au cours du traitement de l'image : " + threshold_ndvi_file_output + ". Voir message d'erreur." + endC)

        # Masque de la végétation haute
        mask_high_vegetation_file_output = directory_tmp + os.sep + base_name_input + SUFFIX_MASK + SUFFIX_HIGH_VEGETATION + extension_raster
        expression = "\"im1*im2b1\""
        command = "otbcli_BandMathX -il %s %s -out %s %s -exp %s" %(image_input, threshold_ndvi_high_vegetation_file_output, mask_high_vegetation_file_output, CODAGE_16B, expression)
        if ram_otb > 0:
            command += " -ram %d" %(ram_otb)
        exit_code = os.system(command)
        if exit_code != 0:
            print(command)
            raise NameError (cyan + "detecterHouppier() : " + bold + red + "!!! Une erreur c'est produite au cours du traitement de l'image : " + threshold_ndvi_high_vegetation_file_output + ". Voir message d'erreur." + endC)

        ################ ETAPE 3 : SEGMENTATION ###############
        if debug >= 2:
            print(cyan + "detecterHouppier() : " + bold + green + "################ SEGMENTATION ###############" + endC)

        # Taille minimale des arbres d interet : 10 pix (peut etre modifiee)
        segments_high_vegetation_raster_output = directory_tmp + os.sep + base_name_input + SUFFIX_SEGMENTS + SUFFIX_HIGH_VEGETATION + extension_raster
        command = "otbcli_Segmentation -in " + mask_high_vegetation_file_output + " -filter meanshift -filter.meanshift.minsize 10  -mode raster -mode.raster.out " + segments_high_vegetation_raster_output + " " + CODAGE_16B
        if ram_otb > 0:
            command += " -ram %d" %(ram_otb)
        exit_code = os.system(command)
        if exit_code != 0:
            print(command)
            raise NameError (cyan + "detecterHouppier() : " + bold + red + "!!! Une erreur c'est produite au cours du traitement de l'image : " + mask_high_vegetation_file_output + ". Voir message d'erreur." + endC)

        segments_high_vegetation_vector_output = directory_tmp + os.sep + base_name_input + SUFFIX_SEGMENTS + SUFFIX_HIGH_VEGETATION + extension_vector
        command = "otbcli_Segmentation -in " + mask_high_vegetation_file_output + " -filter meanshift -filter.meanshift.minsize 10 -mode vector -mode.vector.minsize 10 -mode.vector.outmode ovw -mode.vector.inmask" + mask_high_vegetation_file_output + " -mode.vector.out " + segments_high_vegetation_vector_output
        if ram_otb > 0:
            command += " -ram %d" %(ram_otb)
        exit_code = os.system(command)
        if exit_code != 0:
            print(command)
            raise NameError (cyan + "detecterHouppier() : " + bold + red + "!!! Une erreur c'est produite au cours du traitement de l'image : " + mask_high_vegetation_file_output + ". Voir message d'erreur." + endC)

        # Simplification des geometries
        segments_high_vegetation_simple_vector_output = directory_tmp + os.sep + base_name_input + SUFFIX_SEGMENTS + SUFFIX_HIGH_VEGETATION + SUFFIX_SIMPLE + extension_vector
        name_file = os.path.splitext(os.path.basename(segments_high_vegetation_vector_output))[0]

        command = "ogr2ogr -f '%s' -overwrite %s %s -dialect SQLITE -sql \"SELECT ST_buffer(geometry, 0) as geometry FROM %s\"" % (format_vector, segments_high_vegetation_simple_vector_output, segments_high_vegetation_vector_output, name_file)

        exit_code = os.system(command)
        if exit_code != 0:
            print(cyan + "detecterHouppier() : " + bold + red + "!!! Une erreur c'est produite au cours de la simplification du vecteur : " + segments_high_vegetation_vector_output + endC, file=sys.stderr)

        ################ ETAPE 4 : REGROUPEMENT SEGMENTS ###############
        if debug >= 2:
            print(cyan + "detecterHouppier() : " + bold + green + "################ REGROUPEMENT SEGMENTS ###############" + endC)

        # Application du masque vecteur au raster segmente
        segments_high_vegetation_mask_raster_output = directory_tmp + os.sep + base_name_input + SUFFIX_SEGMENTS + SUFFIX_HIGH_VEGETATION + SUFFIX_MASK + extension_raster
        command = 'gdalwarp -cutline  %s -crop_to_cutline  %s %s' %(segments_high_vegetation_simple_vector_output, segments_high_vegetation_raster_output, segments_high_vegetation_mask_raster_output)
        exit_code = os.system(command)
        if exit_code != 0:
            print(command)
            print(cyan + "detecterHouppier() : " + bold + red + "!!! Une erreur c'est produite au cours du decoupage de l'image : " + segments_high_vegetation_raster_output + ". Voir message d'erreur." + endC, file=sys.stderr)

        ################ ETAPE 5 : TRAITEMENT DES SEGMENTS ###############
        if debug >= 2:
            print(cyan + "detecterHouppier() : " + bold + green + "################ TRAITEMENT DES SEGMENTS ###############" + endC)

        # Conversion image en matrice
        segments_arbo_matrix = io.imread(segments_high_vegetation_mask_raster_output)
        mnh_matrix = io.imread(image_mnh_input)

        # Lecture des parametres de l'image
        dataset_sgts_arbore = gdal.Open(segments_high_vegetation_mask_raster_output)

        # Recupere les coords des valeurs uniques des segments
        if debug >= 3:
            print(cyan + "detecterHouppier() : " + bold + green + "Debut Recuperation des coordonnees des valeurs uniques des segments" + endC)
        x_coords_sgts_arbo, y_coords_sgts_arbo = giveListCoordsSgtsImg(segments_arbo_matrix)

        if debug >= 3:
            print(cyan + "detecterHouppier() : " + bold + green + "Fin Recuperation des coordonnees des valeurs uniques des segments" + endC)

        # Recupere les coords de la val max pour chaque segment
        if debug >= 3:
            print(cyan + "detecterHouppier() : " + bold + green + "Debut Recuperation des coordonnees de la valeur max pour chaque segment" + endC)
        coords_pts_max_arbo_list = giveCoordsMaxSGTS(x_coords_sgts_arbo, y_coords_sgts_arbo, mnh_matrix)

        if debug >= 3:
            print(cyan + "detecterHouppier() : " + bold + green + "Fin Recuperation des coordonnees de la valeur max pour chaque segment" + endC)

        # Creation liens de connexion
        if debug >= 3:
            print(cyan + "detecterHouppier() : " + bold + green + "Debut Création des liens de connexion entre les points max de hauteur" + endC)
        pos_arbo, lali_arbo = createAllLinks(coords_pts_max_arbo_list)

        if debug >= 3:
            print(cyan + "detecterHouppier() : " + bold + green + "Fin Création des liens de connexion entre les points max de hauteur" + endC)

        # Creation Graphe
        if debug >= 3:
            print(cyan + "detecterHouppier() : " + bold + green + "Création du graphe" + endC)
        gp = nx.Graph()
        gp.add_nodes_from([valeur for valeur in pos_arbo.keys()])
        gp.add_edges_from([valeur for valeur in lali_arbo])

        if debug >= 3:
            print(cyan + "detecterHouppier() : " + bold + green + "Nettoyage du graphe" + endC)
        cleanGraph(gp, pos_arbo, lali_arbo, mnh_matrix)

        if debug >= 3:
            print(cyan + "detecterHouppier() : " + bold + green + "Sauvegarde de la donnee houppiers" + endC)
        sgts_c_arbo = np.copy(segments_arbo_matrix)
        sgts_final_arbo = clustSgtInCrown(gp, sgts_c_arbo, pos_arbo)
        writeImage1B(houppier_image_output, sgts_final_arbo, dataset_sgts_arbore, format_raster)
        dataset_sgts_arbore = None

        ################ ETAPE 6 : VECTORISATION DES SEGMENTS ###############
        if debug >= 2:
            print(cyan + "detecterHouppier() : " + bold + green + "################ VECTORISATION DES SEGMENTS ###############" + endC)

        # Commande gdal polygonize
        layer_name = os.path.splitext(os.path.basename(houppier_vector_output))[0]
        field_name = "id"
        command = "gdal_polygonize.py  -mask %s %s -f \"%s\" %s %s %s" %(mask_high_vegetation_file_output, houppier_image_output, format_vector, houppier_vector_output, layer_name, field_name)

        if debug >= 3:
            print(command)

        exitCode = os.system(command)
        if exitCode != 0:
            print(command)
            raise NameError(bold + red + "An error occured during gdal_polygonize command. See error message above." + endC)
            print(cyan + "detecterHouppier() : " + bold + red + "!!! Une erreur c'est produite au cours de la vectorisation du raster : " + houppier_image_output + endC, file=sys.stderr)

    # Supression du dossier temporaire
    if not save_results_intermediate :
        shutil.rmtree(directory_tmp, ignore_errors=True)

    # Mise à jour du Log
    ending_event = "detecterHouppier() :  detect houppier on image ending : "
    timeLine(path_time_log,ending_event)

    return

###########################################################################################################################################
# MISE EN PLACE DU PARSER                                                                                                                 #
###########################################################################################################################################

# Code executé seulement dans le cas ou le script est lancé depuis une ligne de commande
# Il n'est pas executé lors d'un import DetectionHouppier.py
# Exemple de lancement en ligne de commande:
# python DetectionHouppier.py -i ./rep_test/image_Pleiades_Nancy_20220614_nadir.tif -ih ./rep_test/MNH_Pleiades_Nancy.tif -io ./rep_test/RESULTATS_HOUPPIERS/houppiers.tif -vo ./rep_test/RESULTATS_HOUPPIERS/houppiers.shp -thrmnh 2.0 -thrndvi 0.35

def main(gui=False):

    # Définition des arguments possibles pour l'appel en ligne de commande
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, prog="DetectionHouppier", description="\
    Info : Detect houppier of tree on raster image four bands. \n\
    Objectif : Detecter les houppiers de arbres dans une image raster 4 bandes. \n\
    Example : python DetectionHouppier.py -i ./rep_test/image_Pleiades_Nancy_20220614_nadir.tif \n\
                                       -ih ./rep_test/MNH_Pleiades_Nancy.tif \n\
                                       -io ./rep_test/RESULTATS_HOUPPIERS/houppiers.tif \n\
                                       -vo ./rep_test/RESULTATS_HOUPPIERS/houppiers.shp \n\
                                       -thrmnh 2.0 \n\
                                       -thrndvi 0.35")

    # Paramètres
    parser.add_argument('-i','--image_input',default="",help="Image input to treat", type=str, required=True)
    parser.add_argument('-ih','--image_mnh_input',default="",help="Image MNH input", type=str, required=True)
    parser.add_argument('-io','--image_output',default="",help="Image output result of houppier", type=str, required=True)
    parser.add_argument('-vo','--vector_output',default="",help="Vector output vectorisation of image output houppier", type=str, required=False)
    parser.add_argument('-thrmnh','--threshold_mnh_value',default=2.0,help="Parameter value of threshold MNH file. By default : 2.0", type=float, required=False)
    parser.add_argument('-thrndvi','--threshold_ndvi_value',default=0.35,help="Parameter value of threshold  NDVI file. By default : 3.25", type=float, required=False)
    parser.add_argument('-ram','--ram_otb',default=0,help="Ram available for processing otb applications (in MB)", type=int, required=False)
    parser.add_argument('-raf','--format_raster', default="GTiff", help="Option : Format output image, by default : GTiff (GTiff, HFA...)", type=str, required=False)
    parser.add_argument('-vef','--format_vector', default="ESRI Shapefile",help="Format of the output file.", type=str, required=False)
    parser.add_argument('-rae','--extension_raster', default=".tif", help="Option : Extension file for image raster. By default : '.tif'", type=str, required=False)
    parser.add_argument('-vee','--extension_vector',default=".shp",help="Option : Extension file for vector. By default : '.shp'", type=str, required=False)
    parser.add_argument('-log','--path_time_log',default="",help="Name of log", type=str, required=False)
    parser.add_argument('-sav','--save_results_inter',action='store_true',default=False,help="Save or delete original image after the majority filter. By default, False", required=False)
    parser.add_argument('-now','--overwrite',action='store_false',default=True,help="Overwrite files with same names. By default, True", required=False)
    parser.add_argument('-debug','--debug',default=3,help="Option : Value of level debug trace, default : 3 ",type=int, required=False)
    args = parser.parse_args()

    # RECUPERATION DES ARGUMENTS

    # Récupération de l'image d'entrée
    if args.image_input != None:
        image_input = args.image_input
        if not os.path.isfile(image_input):
            raise NameError (cyan + "DetectionHouppier : " + bold + red  + "File %s not existe!" %(image_input) + endC)

    # Récupération du MNH d'entrée
    if args.image_mnh_input != None:
        image_mnh_input = args.image_mnh_input
        if not os.path.isfile(image_mnh_input):
            raise NameError (cyan + "DetectionHouppier : " + bold + red  + "File %s not existe!" %(image_mnh_input) + endC)

    # Récupération de l'image de sortie
    if args.image_output != None:
        image_output = args.image_output

    # Récupération du vecteur de sortie
    if args.vector_output != None:
        vector_output = args.vector_output

    # Paramettre valeur de seuillage du MNH
    if args.threshold_mnh_value != None:
        threshold_mnh_value = args.threshold_mnh_value

    # Récupération de la valeur du NDVI
    if args.threshold_ndvi_value != None:
        threshold_ndvi_value = args.threshold_ndvi_value

    # Récupération du parametre ram
    if args.ram_otb != None:
        ram_otb = args.ram_otb

    # Paramètre format des images de sortie
    if args.format_raster != None:
        format_raster = args.format_raster

    # Récupération du format du fichier de sortie
    if args.format_vector != None :
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
        print(cyan + "DetectionHouppier : " + endC + "image_input : " + str(image_input) + endC)
        print(cyan + "DetectionHouppier : " + endC + "image_mnh_input : " + str(image_mnh_input) + endC)
        print(cyan + "DetectionHouppier : " + endC + "image_output : " + str(image_output) + endC)
        print(cyan + "DetectionHouppier : " + endC + "vector_output : " + str(vector_output) + endC)
        print(cyan + "DetectionHouppier : " + endC + "threshold_mnh_value : " + str(threshold_mnh_value) + endC)
        print(cyan + "DetectionHouppier : " + endC + "threshold_ndvi_value : " + str(threshold_ndvi_value) + endC)
        print(cyan + "DetectionHouppier : " + endC + "ram_otb : " + str(ram_otb) + endC)
        print(cyan + "DetectionHouppier : " + endC + "format_raster : " + str(format_raster) + endC)
        print(cyan + "DetectionHouppier : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "DetectionHouppier : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "DetectionHouppier : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "DetectionHouppier : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "DetectionHouppier : " + endC + "save_results_inter : " + str(save_results_intermediate) + endC)
        print(cyan + "DetectionHouppier : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "DetectionHouppier : " + endC + "debug : " + str(debug) + endC)

    # EXECUTION DE LA FONCTION
    # Si le dossier de sortie n'existe pas, on le crée
    repertory_output = os.path.dirname(image_output)
    if not os.path.isdir(repertory_output):
        os.makedirs(repertory_output)

    # execution de la fonction pour une image
    detecterHouppier(image_input, image_mnh_input, image_output, vector_output, threshold_mnh_value, threshold_ndvi_value, path_time_log, ram_otb, format_raster, format_vector, extension_raster, extension_vector, save_results_intermediate, overwrite)

# ================================================

if __name__ == '__main__':
  main(gui=False)
