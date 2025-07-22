#! /usr/bin/env pyt/hon
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT DE PREPARATION DE DONNEES QUI ASSEMBLE LES IMAGES D'UN BUFFER CONSTRUIT AUTOUR D'UN LINEAIRE                                       #
#                                                                                                                                           #
#############################################################################################################################################

"""
Nom de l'objet : PrepareData.py
Description    :
----------------
Objectif   : Assemble et découpe des images raster comprises dans l'enveloppe optimale de l'intersection d'un buffer et d'un polygone

Date de creation : 29/04/2016
"""

from __future__ import print_function
import os, sys, shutil, argparse
from osgeo import gdal, ogr
from Lib_log import timeLine
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_vector import splitVector, getAttributeValues, getProjection
from Lib_file import removeVectorFile, getSubRepRecursifList
from ImagesAssembly import selectAssembyImagesByHold

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 3

###########################################################################################################################################
# FONCTION prepareData                                                                                                                    #
###########################################################################################################################################
def prepareData(input_buffer_tdc, input_paysage, output_dir, input_repertories_list, id_paysage, id_name_sub_rep, epsg, optimization_zone, no_cover, zone_date, separ_name, pos_date, nb_char_date, separ_date, path_time_log, format_raster='GTiff', format_vector="ESRI Shapefile", extension_raster=".tif", extension_vector=".shp", save_results_intermediate=True, overwrite=True):
    """
    # ROLE:
    #    Assembler et découper des images raster comprises dans un buffer
    #
    # ENTREES DE LA FONCTION :
    #    input_buffer_tdc : Fichier format shape (.shp) de la ligne autour de laquelle couper les images
    #    input_paysage : Paysage pour la découpe de l'image, qui sera optimisé par le script
    #    output_dir: Répertoire de sortie pour les traitements
    #    input_repertories_list : Répertoire(s) des fichiers raw (.tif, .ecw, .jp2, .asc) images d'entrées
    #    id_paysage : Nom de la colonne dans le shapefile paysage contenant le nom des paysages qu'on veut mettre dans les noms des images assemblées
    #    id_name_sub_rep : Nom de la colonne dans le shapefile paysage contenant le nom du sous repéertoire contenant les imagettes associés au paysage
    #    epsg : Valeur de l'EPSG : par défaut 2154
    #    optimization_zone : True : la zone d'étude est l'intersection de la zone buffer et des zones paysages
    #    no_cover : True : pas de recouvrement entre les images
    #    zone_date : True : les images seront assemblées par date
    #    separ_name : Paramètre date acquisition dans le nom, séparateur d'information
    #    pos_date : Paramètre date acquisition dans le nom, position relatif au séparateur d'information
    #    nb_char_date : Paramètre date acquisition dans le nom, nombre de caractères constituant la date
    #    separ_date : Paramètre date acquisition dans le nom, séparateur dans l'information date
    #    path_time_log : le fichier de log de sortie
    #    format_raster : Format de l'image de sortie, par défaut : GTiff
    #    format_vector  : format du vecteur de sortie, par defaut = 'ESRI Shapefile'
    #    extension_raster : extension des fichiers raster de sortie, par defaut = '.tif'
    #    extension_vector : extension du fichier vecteur de sortie, par defaut = '.shp'
    #    save_results_intermediate : fichiers de sorties intermediaires non nettoyees, par defaut = True
    #    overwrite : supprime ou non les fichiers existants ayant le meme nom
    #
    # SORTIES DE LA FONCTION :
    #    Le(s) fichier(s) image assemblé(s)
    #    Eléments modifiés aucun
    #
    """

    # Mise à jour du Log
    starting_event = "prepareData() : Select prepare data starting : "
    timeLine(path_time_log,starting_event)

    # Affichage des paramètres
    if debug >= 3:
        print(bold + green + "Variables dans le prepareData - Variables générales" + endC)
        print(cyan + "PrepareData() : " + endC + "input_buffer_tdc : " + str(input_buffer_tdc) + endC)
        print(cyan + "PrepareData() : " + endC + "input_paysage : " + str(input_paysage) + endC)
        print(cyan + "PrepareData() : " + endC + "output_dir : " + str(output_dir) + endC)
        print(cyan + "PrepareData() : " + endC + "input_repertories_list : " + str(input_repertories_list) + endC)
        print(cyan + "PrepareData() : " + endC + "id_paysage : " + str(id_paysage) + endC)
        print(cyan + "PrepareData() : " + endC + "id_name_sub_rep : " + str(id_name_sub_rep) + endC)
        print(cyan + "PrepareData() : " + endC + "epsg : " + str(epsg) +endC)
        print(cyan + "PrepareData() : " + endC + "optimization_zone : " + str(optimization_zone) + endC)
        print(cyan + "PrepareData() : " + endC + "no_cover : " + str(no_cover) + endC)
        print(cyan + "PrepareData() : " + endC + "zone_date : " + str(zone_date) + endC)
        print(cyan + "PrepareData() : " + endC + "separ_name : " + str(separ_name) + endC)
        print(cyan + "PrepareData() : " + endC + "pos_date : " + str(pos_date) + endC)
        print(cyan + "PrepareData() : " + endC + "nb_char_date : " + str(nb_char_date) + endC)
        print(cyan + "PrepareData() : " + endC + "separ_date : " + str(separ_date) + endC)
        print(cyan + "PrepareData() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "PrepareData() : " + endC + "format_raster : " + str(format_raster) + endC)
        print(cyan + "PrepareData() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "PrepareData() : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "PrepareData() : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "PrepareData() : " + endC + "save_results_inter : " + str(save_results_intermediate) + endC)
        print(cyan + "PrepareData() : " + endC + "overwrite : " + str(overwrite) + endC)

    REPERTORY_PAYSAGES = "Paysages"
    REPERTORY_IMAGES = "Images"
    ID_P = "id_p"

    SUFFIX_OPTI = "_opti"
    SUFFIX_CUT = "_cut"
    SUFFIX_ERROR = "_error"
    SUFFIX_MERGE = "_merge"
    SUFFIX_CLEAN = "_clean"
    SUFFIX_STACK = "_stack"

    output_dir_paysages = output_dir + os.sep + REPERTORY_PAYSAGES
    output_dir_images = output_dir + os.sep + REPERTORY_IMAGES

    # Création du répertoire de sortie s'il n'existe pas déjà
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Création du répertoire de sortie pour les paysages s'il n'existe pas
    if not os.path.exists(output_dir_paysages):
        os.makedirs(output_dir_paysages)

    # Création du répertoire de sortie pour les images s'il n'existe pas
    if not os.path.exists(output_dir_images):
        os.makedirs(output_dir_images)

    # Recuperer l'epsg du fichier d'emprise
    if epsg == 0 :
        epsg, _ = getProjection(input_paysage, format_vector)

    # Création du paysage optimal
    optimPaysage(input_buffer_tdc, input_paysage, optimization_zone, SUFFIX_OPTI, output_dir_paysages, id_paysage, format_vector)

    # Création un shapefile par polygone
    paysage_opti = output_dir_paysages + os.sep + os.path.splitext(os.path.basename(input_paysage))[0] + SUFFIX_OPTI + os.path.splitext(input_paysage)[1]
    if id_paysage != "" :
        paysages_list = splitVector(paysage_opti, str(output_dir_paysages), str(id_paysage), epsg, format_vector, extension_vector)
    else:
        paysages_list = splitVector(paysage_opti, str(output_dir_paysages), ID_P, epsg, format_vector, extension_vector)

    if debug >= 3:
        print(cyan + "PrepareData() : " + endC + "Liste des fichiers en entrée de imagesAssembly() : " + str(paysages_list))

    # Création du fichier de sortie des images s'il n'existe pas dejà
    if not os.path.exists(output_dir_images):
        os.makedirs(output_dir_images)

    # Assemblage des images dans les paysages optimisés
    # Si on choisit pas de recouvrement entre les images
    if no_cover:

        # Récupération des noms de sortie
        image_output_list = []
        id_paysage_list = []
        for shape in paysages_list :
            attribute_name_dico = {}
            attribute_name_dico[id_name_sub_rep] = ogr.OFTString
            attribute_name_dico[id_paysage] = ogr.OFTInteger
            res_values_dico = getAttributeValues(shape, None, None, attribute_name_dico, format_vector)
            id_name_sub_rep_value = res_values_dico[id_name_sub_rep][0]
            id_paysage_value = res_values_dico[id_paysage][0]
            image_output_list.append(id_name_sub_rep_value)
            id_paysage_list.append(id_paysage_value)
        if debug >= 3:
            print("image_output_list " + str(image_output_list))

        # Récupération de tous les (sous-)répertoires
        repertory_images_sources_list_temp = []
        for input_dir in input_repertories_list:
            sub_rep_list = getSubRepRecursifList(input_dir)
            if sub_rep_list != []:
                for sub_rep in sub_rep_list:
                    repertory_images_sources_list_temp.append(sub_rep)
            else:
                repertory_images_sources_list_temp.append(input_dir)
        # On réorganise pour avoir le même ordre dans les 2 listes 'repertory_images_sources_list' et 'image_output_list'
        repertory_images_sources_list = []
        for paysage in id_paysage_list:
            for repertory_images_source in repertory_images_sources_list_temp:
                if str(paysage) in repertory_images_source.split(os.sep)[-1]:
                    repertory_images_sources_list.append(repertory_images_source)
        if debug >= 3:
            print("repertory_images_sources_list " + str(repertory_images_sources_list))

        if len(repertory_images_sources_list) != len(image_output_list):
            raise Exception(bold + red + "Error: not same number of input repertories and output files." + endC)

        # Commande ImagesAssembly sur les éléments des 2 listes
        for i in range(len(paysages_list)):
            image_output = output_dir_images + os.sep + image_output_list[i]
            if debug >= 3:
                 print(cyan + "PrepareData() : " + endC + bold + green  + "image_output : " + endC + image_output)

            try:
                # ~ selectAssembyImagesByHold(paysages_list[i], [repertory_images_sources_list[i]], image_output, False, True, epsg, False, False, False, False, 0, 0, 0, 0, separ_name, pos_date, nb_char_date, separ_date, path_time_log, SUFFIX_ERROR, SUFFIX_MERGE, SUFFIX_CLEAN, SUFFIX_STACK, format_raster, format_vector, extension_raster, extension_vector, save_results_intermediate, overwrite)
                selectAssembyImagesByHold(paysages_list[i], [repertory_images_sources_list[i]], image_output, False, zone_date, epsg, False, False, False, False, 0, 0, 0, 0, separ_name, pos_date, nb_char_date, separ_date, path_time_log, SUFFIX_ERROR, SUFFIX_MERGE, SUFFIX_CLEAN, SUFFIX_STACK, format_raster, format_vector, extension_raster, extension_vector, save_results_intermediate, overwrite)
            except Exception:
                pass

    else:
        for shape in paysages_list :
            # ~ filename = os.path.basename(shape)
            # ~ info_name = filename.split(separ_name, 2)[POS]
            # ~ name_shape = info_name[:NB_CHAR]
            # ~ image_output = output_dir_images + os.sep + name_shape + SUFFIX_ASS + extension_raster

        # ~ for shape in sub_repertory_images_paysages_list :
            image_output = output_dir_images + os.sep + os.path.splitext(os.path.basename(shape))[0] + extension_raster

            if optimization_zone :
                shape_cut = os.path.splitext(shape)[0] + SUFFIX_CUT + os.path.splitext(shape)[1]
                cutVector(input_buffer_tdc, shape, shape_cut, overwrite, format_vector)
            else :
                shape_cut = shape

            selectAssembyImagesByHold(shape_cut, input_repertories_list, image_output, False, zone_date, epsg, False, False, False, False, 0, 0, 0, 0, separ_name, pos_date, nb_char_date, separ_date, path_time_log, SUFFIX_ERROR, SUFFIX_MERGE, SUFFIX_CLEAN, SUFFIX_STACK, format_raster, format_vector,extension_raster,extension_vector, save_results_intermediate, overwrite)
            if optimization_zone and os.path.exists(shape_cut):
                removeVectorFile(shape_cut, format_vector)

    # Mise à jour du Log
    ending_event = "prepareData() : Select prepare data ending : "
    timeLine(path_time_log,ending_event)

    if debug >= 3:
        print(cyan + "PrepareData() : " + endC + bold + green  + "Fin de traitement")
    return

###########################################################################################################################################
# FONCTION optimPaysage                                                                                                                   #
###########################################################################################################################################
def optimPaysage(input_buffer_tdc, input_paysage, optimization_zone, prefix_opti, output_dir_paysages, id_paysage, format_vector='ESRI Shapefile'):
    """
    # ROLE:
    #    Calculer le fichier shape autour de la zone d'interet
    #
    # ENTREES DE LA FONCTION :
    #    input_buffer_tdc : buffer pour l'intersection avec le paysage (en vue de l'optimisation)
    #    input_paysage : paysage à optimiser avec l'intersection
    #    optimization_zone : True : la zone d'étude est l'intersection de la zone buffer et des zones paysages
    #    prefix_opti : prefixe des noms des shapes optimisés
    #    output_dir_paysages : dossier où sera créé le paysage optimisé en sortie
    #    format_vector : format du vecteur de sortie (par défaut : ESRI Shapefile)
    #
    # SORTIES DE LA FONCTION :
    #    Un nouveau shp contenant le paysage optimisé avec l'intersection du buffer
    #    Eléments modifiés aucun
    #
    # AMELIORATIONS A APPORTER
    #    Si le buffer intersecte le paysage en plusieurs fois (ex : île ou grand virage dans linéaire), le paysage optimisé pourra être en autant de morceaux
    """

    driver = ogr.GetDriverByName(format_vector)
    # Récupération de la couche input_paysage et de ses propriétés
    data_source_input = driver.Open(input_paysage,0)
    layer_input_paysage = data_source_input.GetLayer()
    srs = layer_input_paysage.GetSpatialRef()
    layer_input_defn = layer_input_paysage.GetLayerDefn()

    # Création du fichier de sortie des paysages s'il n'existe pas déjà
    if not os.path.exists(output_dir_paysages):
        os.makedirs(output_dir_paysages)

    # Création du shp du paysage optimisé
    output_paysage = output_dir_paysages + os.sep + os.path.splitext(os.path.basename(input_paysage))[0] + prefix_opti + os.path.splitext(input_paysage)[1]
    if os.path.exists(output_paysage):
        driver.DeleteDataSource(output_paysage)
    data_source_output = driver.CreateDataSource(output_paysage)
    layer_output = data_source_output.CreateLayer(output_paysage, srs, ogr.wkbPolygon)

    # Copie des champs de input_layer dans le shp paysage optimisé
    for i in range(layer_input_defn.GetFieldCount()):
        # Récupération
        field_name =  layer_input_defn.GetFieldDefn(i).GetName()
        field_type_code = layer_input_defn.GetFieldDefn(i).GetType()
        field_width = layer_input_defn.GetFieldDefn(i).GetWidth()
        field_precision = layer_input_defn.GetFieldDefn(i).GetPrecision()
        # Création
        output_field = ogr.FieldDefn(str(field_name), field_type_code)
        output_field.SetWidth(field_width)
        output_field.SetPrecision(field_precision)
        layer_output.CreateField(output_field)

    # Récupération de la géométrie du buffer
    data_source_buffer = ogr.Open(input_buffer_tdc, 0)
    layer_buffer = data_source_buffer.GetLayer()
    for i in range(0, layer_buffer.GetFeatureCount()):
        feature = layer_buffer.GetFeature(i)
    geom_buffer = feature.GetGeometryRef()

    # Récupération des entités de la couche paysage en entrée
    dico_paysages_info_debug = {}

    for feat in layer_input_paysage:
        # Opérations géométrie
        geom_paysage = feat.GetGeometryRef()

        # Si les géométries des éléments des fichiers paysage et de buffer se croisent (=1)
        if geom_paysage.Intersects(geom_buffer) == 1:

            # Recupération de l'intersection des entités de la couche paysage et la couche buffer
            geom_inters = geom_paysage.Intersection(geom_buffer)

            if optimization_zone : # Cas de la découpe
                geom_output = geom_inters

            else : # cas de l'emprise
                # Calcul de l'enveloppe de l'intersection
                env = geom_inters.GetEnvelope()
                # Récupération des coordonnées de l'enveloppe
                xmin = str(env[0])
                ymin = str(env[2])
                xmax = str(env[1])
                ymax = str(env[3])
                area1 = (env[1]-env[0])*(env[3]-env[2])/1000000
                if debug >= 2:
                    if id_paysage != "":
                        dico_paysages_info_debug["Paysage " + str(feat.GetField(id_paysage))] = str(round(area1,3))

                # Création polygone (enveloppe de l'intersection)
                wkt = "POLYGON(("+xmin+" "+ymin+","+xmax+" "+ymin+","+xmax+" "+ymax+","+xmin+" "+ymax+","+xmin+" "+ymin+"))"
                geom_output = ogr.CreateGeometryFromWkt(wkt)

            # Creation de la feature de sortie
            feature_output = ogr.Feature(layer_output.GetLayerDefn())
            feature_output.SetGeometry(geom_output)

            # Opérations sémantiques
            for i in range(layer_input_defn.GetFieldCount()):
                value = feat.GetField(layer_input_defn.GetFieldDefn(i).GetName())
                feature_output.SetField(layer_input_defn.GetFieldDefn(i).GetName(), value)

            # Création de l'entité, avec géométrie et sémantique
            layer_output.CreateFeature(feature_output)
            layer_output.SyncToDisk()
            feature_output.Destroy()

    # Fermeture des fichiers shape
    data_source_input.Destroy()
    data_source_buffer.Destroy()
    data_source_output.Destroy()

    if debug >= 2:
        print(cyan + "optimPaysage() : " + endC + "Aires des paysages (km2) : " + str(dico_paysages_info_debug))
    return

###########################################################################################################################################
# MISE EN PLACE DU PARSER                                                                                                                 #
###########################################################################################################################################

# Code executé seulement dans le cas ou le script est lancé depuis une ligne de commande
# Il n'est pas executé lors d'un import PrepareData.py
# Exemple de lancement en ligne de commande:
# Depuis ScriptsApplication :
# python ../ScriptsLittoral/PrepareData.py -b /mnt/Data/blandine.decherf/TDC_national/buffer_5000.shp -p /mnt/Data/blandine.decherf/paysages/paysages2.shp -outd /mnt/Data/blandine.decherf/Results -pathi /mnt/Data/blandine.decherf/Orthos/ORT_2014022238763074_LA93 -idp nom_poly
# Depuis /mnt/Data/blandine.decherf/Results
# python PrepareData.py -b /mnt/Data/blandine.decherf/TDC_national/buffer_5000.shp -p /mnt/Data/blandine.decherf/paysages/paysages2.shp -outd /mnt/Data/blandine.decherf/Results -pathi /mnt/Data/blandine.decherf/Orthos/ORT_2014022238763074_LA93 -idp nom_poly

def main(gui=False):

    parser = argparse.ArgumentParser(prog="PrepareData", description=" \
    Info : Creating an image from an raw image mosaic (.tif, .ecw, .jp2, .asc), an emprise file (.shp) and a buffer (.shp).\n\
    Objectif   : Assemble et découpe des images raster comprises dans l'enveloppe optimale de l'intersection d'un buffer et d'un polygone. \n\
    Example : python PrepareData.py -b /mnt/Data/blandine.decherf/TDC_national/buffer_5000.shp \n\
                                       -p /mnt/Data/blandine.decherf/paysages/paysages2.shp \n\
                                       -outd /mnt/Data/blandine.decherf/Results \n\
                                       -pathi /mnt/Data/blandine.decherf/Orthos/ORT_2014022238763074_LA93 \n\
                                       -idp nom_poly")

    parser.add_argument('-b','--input_buffer_tdc', default="",help="Input buffer, format shape (.shp).", type=str, required=True)
    parser.add_argument('-p','--input_paysage', default="",help="Input paysage vector, format shape (.shp).", type=str, required=True)
    parser.add_argument('-outd','--output_dir', default="",help="Output directory", type=str, required=True)
    parser.add_argument('-idp','--id_paysage', default="RefDossier",help="Column identifying each paysage", type=str, required=False)
    parser.add_argument('-idn','--id_name_sub_rep', default="NomImage",help="Column identifying each sub repertory contain imagettes", type=str, required=False)
    parser.add_argument('-pathi','--input_repertories_list',default=[], nargs="+", help="Liste storage directory of sources raw images (.tif, .ecw, .jp2, .asc), can be several directories",type=str, required=True)
    parser.add_argument('-opt', '--optimization_zone', action='store_true', default=False, help="Option : The study zone intersecte buffer shape and paysage shape. By default : False", required=False)
    parser.add_argument('-nc', '--no_cover', action='store_true', default=False, help="Option : The images are assembled with no covering between them. By default : False", required=False)
    parser.add_argument('-z', '--zone_date', action='store_true', default=False, help="Option : The images are assembled by area date shooting, a result picture by date. Not used with option no_cover. By default : False", required=False)
    parser.add_argument('-sepn','--separname', default="_", help="Acquisition date in the name, information separator (For example : '_'). By default : '_'", type=str, required=False)
    parser.add_argument('-posd','--posdate', default=2, help="Acquisition date in the name, position relative to the information separator (For example : 3). By default : 2", type=int, required=False)
    parser.add_argument('-nbcd','--nbchardate', default=8, help="Acquisition date in the name, number of characters constituting the date (For example : 10). By default : 8", type=int, required=False)
    parser.add_argument('-sepd','--separdate', default="", help="Acquisition date in the name, the date separator in information (For example : '-'). By default : ''", type=str, required=False)
    parser.add_argument('-epsg','--epsg', default=2154,help="Projection of the output file.", type=int, required=False)
    parser.add_argument('-raf','--format_raster', default="GTiff", help="Option : Format output image, by default : GTiff (GTiff, HFA...)", type=str, required=False)
    parser.add_argument('-vef','--format_vector',default="ESRI Shapefile",help="Option : Vector format. By default : ESRI Shapefile", type=str, required=False)
    parser.add_argument('-rae','--extension_raster', default=".tif", help="Option : Extension file for image raster. By default : '.tif'", type=str, required=False)
    parser.add_argument('-vee','--extension_vector',default=".shp",help="Option : Extension file for vector. By default : '.shp'", type=str, required=False)
    parser.add_argument('-log','--path_time_log',default="",help="Name of log", type=str, required=False)
    parser.add_argument('-sav','--save_results_inter',action='store_true',default=False,help="Option : Save or delete intermediate result after the process. By default, False", required=False)
    parser.add_argument('-now','--overwrite',action='store_false',default=True,help="Option : Overwrite files with same names. By default : True", required=False)
    parser.add_argument('-debug','--debug',default=3,help="Option : Value of level debug trace, default : 3 ",type=int, required=False)
    args = displayIHM(gui, parser)

    # Récupération de la donnée en entrée (ligne)
    if args.input_buffer_tdc != None :
        input_buffer_tdc = args.input_buffer_tdc
        if not os.path.isfile(input_buffer_tdc):
            raise NameError (cyan + "PrepareData : " + bold + red  + "File %s not existe!" %(input_buffer_tdc) + endC)

    # Récupération des paysages en entrée
    if args.input_paysage != None :
        input_paysage = args.input_paysage
        if not os.path.isfile(input_paysage):
            raise NameError (cyan + "PrepareData : " + bold + red  + "File %s not existe!" %(input_paysage) + endC)

    # Récupération du chemin des images en sortie
    if args.output_dir != None :
        output_dir = args.output_dir

    # Récupération de la colonne identifiant le paysage
    if args.id_paysage != None :
        id_paysage = args.id_paysage

    # Récupération de la colonne identifiant le sous repertoire
    if args.id_name_sub_rep != None :
        id_name_sub_rep = args.id_name_sub_rep

    # Paramètres des répertoires d'images d'entrée
    if args.input_repertories_list != None:
        input_repertories_list = args.input_repertories_list

    # Optimization zone buffer et paysage
    if args.optimization_zone != None:
        optimization_zone = args.optimization_zone

    # Assemblage sans recouvrement
    if args.no_cover != None:
        no_cover = args.no_cover

    # Assemblage par date
    if args.zone_date != None:
        zone_date = args.zone_date

    # Paramètres de la date
    if args.separname != None:
        separname = args.separname

    if args.posdate != None:
        posdate = args.posdate

    if args.nbchardate != None:
        nbchardate = args.nbchardate

    if args.separdate != None:
        separdate = args.separdate

    # Récupération du nom du fichier log
    if args.path_time_log != None:
        path_time_log = args.path_time_log

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
        print(cyan + "PrepareData : " + endC + "input_buffer_tdc : " + str(input_buffer_tdc) + endC)
        print(cyan + "PrepareData : " + endC + "input_paysage : " + str(input_paysage) + endC)
        print(cyan + "PrepareData : " + endC + "output_dir : " + str(output_dir) + endC)
        print(cyan + "PrepareData : " + endC + "id_paysage : " + str(id_paysage) + endC)
        print(cyan + "PrepareData : " + endC + "id_name_sub_rep : " + str(id_name_sub_rep) + endC)
        print(cyan + "PrepareData : " + endC + "input_repertories_list : " + str(input_repertories_list) + endC)
        print(cyan + "PrepareData : " + endC + "optimization_zone : " + str(optimization_zone) + endC)
        print(cyan + "PrepareData : " + endC + "no_cover : " + str(no_cover) + endC)
        print(cyan + "PrepareData : " + endC + "zone_date : " + str(zone_date) + endC)
        print(cyan + "PrepareData : " + endC + "separname : " + str(separname) + endC)
        print(cyan + "PrepareData : " + endC + "posdate : " + str(posdate) + endC)
        print(cyan + "PrepareData : " + endC + "nbchardate : " + str(nbchardate) + endC)
        print(cyan + "PrepareData : " + endC + "separdate : " + str(separdate) + endC)
        print(cyan + "PrepareData : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "PrepareData : " + endC + "format_raster : " + str(format_raster) + endC)
        print(cyan + "PrepareData : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "PrepareData : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "PrepareData : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "PrepareData : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "PrepareData : " + endC + "save_results_inter : " + str(save_results_intermediate) + endC)
        print(cyan + "PrepareData : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "PrepareData : " + endC + "debug: " + str(debug) + endC)

    # Fonction générale
    prepareData(input_buffer_tdc, input_paysage, output_dir, input_repertories_list, id_paysage, id_name_sub_rep, epsg, optimization_zone, no_cover, zone_date, separname, posdate, nbchardate, separdate, path_time_log, format_raster, format_vector, extension_raster, extension_vector, save_results_intermediate, overwrite)

# ================================================

if __name__ == '__main__':
  main(gui=False)

