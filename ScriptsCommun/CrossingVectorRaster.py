#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerSO/DALETT/SCGSI  All rights reserved.                                                                            #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT FAIT UN CROISEMENT DES DONNEES VECTEUR VERS UN FICHIER RASTER POUR EN EXTRAIRE DES STATISTIQUES                                    #
#                                                                                                                                           #
#############################################################################################################################################
'''
Nom de l'objet : CrossingVectorRaster.py
Description :
    Objectif : Calcule les statstiques de l'intersection d'un image_input (tif) pour chaque polygones d'un jeu de vecteurs (shape)

Date de creation : 01/10/2014

'''
# Import des bibliothèques python
from __future__ import print_function
import os,sys,glob,argparse,ogr, shutil
from rasterstats2 import raster_stats
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_log import timeLine
from Lib_raster import getPixelSizeImage, getEmpriseImage, identifyPixelValues
from Lib_vector import getEmpriseFile, cleanMiniAreaPolygons
from Lib_file import copyVectorFile, removeVectorFile, renameVectorFile

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 2

###########################################################################################################################################
# DEFINITION DE LA FONCTION statisticsVectorRaster                                                                                        #
###########################################################################################################################################
# ROLE:
#     Fonction qui calcule pour chaque polygone d'un fichier vecteur (shape) les statistiques associées de l'intersection avec une image raster (tif)
#
# ENTREES DE LA FONCTION :
#    image_input : Fichier image raster de la classification information pour le calcul des statistiques
#    vector_input : Fichier vecteur d'entrée defini les zones de polygones pour le calcul des statistiques
#    vector_output : Fichier vecteur de sortie
#    band_number : Numero de bande du fichier image d'entree à utiliser
#    enable_stats_all_count : Active le calcul statistique 'all','count' sur les pixels de l'image raster
#    enable_stats_columns_str : Active le calcul statistique 'majority','minority' sur les pixels de l'image raster
#    enable_stats_columns_real : Active le calcul statistique 'min', 'max', 'mean' , 'median','sum', 'std', 'unique', 'range' sur les pixels de l'image raster.
#    col_to_delete_list : liste des colonnes a suprimer
#    col_to_add_list : liste des colonnes à ajouter
#         NB: ce parametre n a de sens que sur une image rvb ou un MNT par exemple
#    class_label_dico : dictionaire affectation de label aux classes de classification
#    path_time_log : le fichier de log de sortie
#    clean_small_polygons : Nettoyage des petits polygones , par defaut = False
#    format_vector : format du fichier vecteur. Optionnel, par default : 'ESRI Shapefile'
#    save_results_intermediate : fichiers de sorties intermediaires nettoyees, par defaut = False
#    overwrite : supprime ou non les fichiers existants ayant le meme nom
#
# SORTIES DE LA FONCTION :
#    Eléments modifiés le fichier shape d'entrée
#
def statisticsVectorRaster(image_input, vector_input, vector_output, band_number, enable_stats_all_count, enable_stats_columns_str, enable_stats_columns_real, col_to_delete_list, col_to_add_list, class_label_dico, path_time_log, clean_small_polygons=False, format_vector='ESRI Shapefile', save_results_intermediate=False, overwrite=True) :


    # INITIALISATION
    if debug >= 3:
        print(cyan + "statisticsVectorRaster() : " + endC + "image_input : " + str(image_input) + endC)
        print(cyan + "statisticsVectorRaster() : " + endC + "vector_input : " + str(vector_input) + endC)
        print(cyan + "statisticsVectorRaster() : " + endC + "vector_output : " + str(vector_output) + endC)
        print(cyan + "statisticsVectorRaster() : " + endC + "band_number : " + str(band_number) + endC)
        print(cyan + "statisticsVectorRaster() : " + endC + "enable_stats_all_count : " + str(enable_stats_all_count) + endC)
        print(cyan + "statisticsVectorRaster() : " + endC + "enable_stats_columns_str : " + str(enable_stats_columns_str) + endC)
        print(cyan + "statisticsVectorRaster() : " + endC + "enable_stats_columns_real : " + str(enable_stats_columns_real) + endC)
        print(cyan + "statisticsVectorRaster() : " + endC + "col_to_delete_list : " + str(col_to_delete_list) + endC)
        print(cyan + "statisticsVectorRaster() : " + endC + "col_to_add_list : " + str(col_to_add_list) + endC)
        print(cyan + "statisticsVectorRaster() : " + endC + "class_label_dico : " + str(class_label_dico) + endC)
        print(cyan + "statisticsVectorRaster() : " + endC + "clean_small_polygons : " + str(clean_small_polygons) + endC)
        print(cyan + "statisticsVectorRaster() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "statisticsVectorRaster() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "statisticsVectorRaster() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "statisticsVectorRaster() : " + endC + "overwrite : " + str(overwrite) + endC)

    # Constantes
    PREFIX_AREA_COLUMN = "S_"

    # Mise à jour du Log
    starting_event = "statisticsVectorRaster() : Compute statistic crossing starting : "
    timeLine(path_time_log,starting_event)

    # creation du fichier vecteur de sortie
    if vector_output == "":
        vector_output = vector_input # Précisé uniquement pour l'affichage
    else :
        # Copy vector_output
        copyVectorFile(vector_input, vector_output, format_vector)

    # Vérifications
    image_xmin, image_xmax, image_ymin, image_ymax = getEmpriseImage(image_input)
    vector_xmin, vector_xmax, vector_ymin, vector_ymax = getEmpriseFile(vector_output, format_vector)
    extension_vector = os.path.splitext(vector_output)[1]

    if round(vector_xmin,4) < round(image_xmin,4) or round(vector_xmax,4) > round(image_xmax,4) or round(vector_ymin,4) < round(image_ymin,4) or round(vector_ymax,4) > round(image_ymax,4) :
        print(cyan + "statisticsVectorRaster() : " + bold + red + "image_xmin, image_xmax, image_ymin, image_ymax" + endC, image_xmin, image_xmax, image_ymin, image_ymax, file=sys.stderr)
        print(cyan + "statisticsVectorRaster() : " + bold + red + "vector_xmin, vector_xmax, vector_ymin, vector_ymax" + endC, vector_xmin, vector_xmax, vector_ymin, vector_ymax, file=sys.stderr)
        raise NameError(cyan + "statisticsVectorRaster() : " + bold + red + "The extend of the vector file (%s) is greater than the image file (%s)" %(vector_output,image_input) + endC)

    pixel_size = getPixelSizeImage(image_input)

    # Suppression des très petits polygones qui introduisent des valeurs NaN
    if clean_small_polygons:
        min_size_area = pixel_size * 2
        vector_temp = os.path.splitext(vector_output)[0] + "_temp" + extension_vector

        cleanMiniAreaPolygons(vector_output, vector_temp, min_size_area, '', format_vector)
        removeVectorFile(vector_output, format_vector)
        renameVectorFile(vector_temp, vector_output)

    # Récuperation du driver pour le format shape
    driver = ogr.GetDriverByName(format_vector)

    # Ouverture du fichier shape en lecture-écriture
    data_source = driver.Open(vector_output, 1) # 0 means read-only - 1 means writeable.
    if data_source is None:
        print(cyan + "statisticsVectorRaster() : " + bold + red + "Impossible d'ouvrir le fichier shape : " + vector_output + endC, file=sys.stderr)
        sys.exit(1) # exit with an error code

    # Récupération du vecteur
    layer = data_source.GetLayer(0)         # Recuperation de la couche (une couche contient les polygones)
    layer_definition = layer.GetLayerDefn() # GetLayerDefn => returns the field names of the user defined (created) fields

    # ETAPE 1/4 : CREATION AUTOMATIQUE DU DICO DE VALEUR SI IL N'EXISTE PAS
    if enable_stats_all_count and class_label_dico == {}:
        image_values_list = identifyPixelValues(image_input)
        # Pour toutes les valeurs
        for id_value in image_values_list :
            class_label_dico[id_value] = str(id_value)
        # Suppression de la valeur no date à 0
        if 0 in class_label_dico :
            del class_label_dico[0]
    if debug >= 2:
        print(class_label_dico)

    # ETAPE 2/4 : CREATION DES COLONNES DANS LE FICHIER SHAPE
    if debug >= 2:
        print(cyan + "statisticsVectorRaster() : " + bold + green + "ETAPE 1/3 : DEBUT DE LA CREATION DES COLONNES DANS LE FICHIER VECTEUR %s" %(vector_output)+ endC)

    # En entrée :
    # col_to_add_list = [UniqueID, majority/DateMaj/SrcMaj, minority, min, max, mean, median, sum, std, unique, range, all, count, all_S, count_S] - all traduisant le class_label_dico en autant de colonnes
    # Sous_listes de col_to_add_list à identifier pour des facilités de manipulations ultérieures:
    # col_to_add_inter01_list = [majority/DateMaj/SrcMaj, minority, min, max, mean, median, sum, std, unique, range]
    # col_to_add_inter02_list = [majority, minority, min, max, mean, median, sum, std, unique, range, all, count, all_S, count_S]
    # Construction des listes intermédiaires
    col_to_add_inter01_list = []

    # Valeurs à injecter dans des colonnes - Format String
    if enable_stats_columns_str :
        stats_columns_str_list = ['majority','minority']
        for e in stats_columns_str_list :
            col_to_add_list.append(e)

    # Valeurs à injecter dans des colonnes - Format Nbr
    if enable_stats_columns_real :
        stats_columns_real_list = ['min', 'max', 'mean' , 'median','sum', 'std', 'unique', 'range']
        for e in stats_columns_real_list :
            col_to_add_list.append(e)

    # Valeurs à injecter dans des colonnes - Format Nbr
    if enable_stats_all_count :
        stats_all_count_list = ['all','count']
        for e in stats_all_count_list :
            col_to_add_list.append(e)

    # Valeurs à injecter dans des colonnes - si class_label_dico est non vide
    if class_label_dico != {}:
        stats_all_count_list = ['all','count']
        for e in stats_all_count_list :
            if not e in col_to_add_list :
                col_to_add_list.append(e)

    # Ajout colonne par colonne
    if "majority" in col_to_add_list:
        col_to_add_inter01_list.append("majority")
    if "DateMaj" in col_to_add_list:
        col_to_add_inter01_list.append("DateMaj")
    if "SrcMaj" in col_to_add_list:
        col_to_add_inter01_list.append("SrcMaj")
    if "minority" in col_to_add_list:
        col_to_add_inter01_list.append("minority")
    if "min" in col_to_add_list:
        col_to_add_inter01_list.append("min")
    if "max" in col_to_add_list:
        col_to_add_inter01_list.append("max")
    if "mean" in col_to_add_list:
        col_to_add_inter01_list.append("mean")
    if "median" in col_to_add_list:
        col_to_add_inter01_list.append("median")
    if "sum" in col_to_add_list:
        col_to_add_inter01_list.append("sum")
    if "std" in col_to_add_list:
        col_to_add_inter01_list.append("std")
    if "unique" in col_to_add_list:
        col_to_add_inter01_list.append("unique")
    if "range" in col_to_add_list:
        col_to_add_inter01_list.append("range")

    # Copy de col_to_add_inter01_list dans col_to_add_inter02_list
    col_to_add_inter02_list = list(col_to_add_inter01_list)

    if "all" in col_to_add_list:
        col_to_add_inter02_list.append("all")
    if "count" in col_to_add_list:
        col_to_add_inter02_list.append("count")
    if "all_S" in col_to_add_list:
        col_to_add_inter02_list.append("all_S")
    if "count_S" in col_to_add_list:
        col_to_add_inter02_list.append("count_S")
    if "DateMaj" in col_to_add_inter02_list:
        col_to_add_inter02_list.remove("DateMaj")
        col_to_add_inter02_list.insert(0,"majority")
    if "SrcMaj" in col_to_add_inter02_list:
        col_to_add_inter02_list.remove("SrcMaj")
        col_to_add_inter02_list.insert(0,"majority")

    # Valeurs à injecter dans des colonnes - Format Nbr
    if enable_stats_all_count :
        stats_all_count_list = ['all_S', 'count_S']
        for e in stats_all_count_list :
            col_to_add_list.append(e)

    # Creation de la colonne de l'identifiant unique
    if ("UniqueID" in col_to_add_list) or ("uniqueID" in col_to_add_list) or ("ID" in col_to_add_list):
        field_defn = ogr.FieldDefn("ID", ogr.OFTInteger)    # Création du nom du champ dans l'objet stat_classif_field_defn
        layer.CreateField(field_defn)
        if debug >= 3:
            print(cyan + "statisticsVectorRaster() : " + endC + "Creation de la colonne : ID")

    # Creation des colonnes de col_to_add_inter01_list ([majority/DateMaj/SrcMaj, minority, min, max, mean, median, sum, std, unique, range])
    for col in col_to_add_list:
        if layer_definition.GetFieldIndex(col) == -1 :                          # Vérification de l'existence de la colonne col (retour = -1 : elle n'existe pas)
            if col == 'majority' or col == 'DateMaj' or col == 'SrcMaj' or col == 'minority':  # Identification de toutes les colonnes remplies en string
                stat_classif_field_defn = ogr.FieldDefn(col, ogr.OFTString)     # Création du champ (string) dans l'objet stat_classif_field_defn
                layer.CreateField(stat_classif_field_defn)
            elif col == 'mean' or col == 'median' or col == 'sum' or col == 'std' or col == 'unique' or col == 'range' or col == 'max' or col == 'min':
                stat_classif_field_defn = ogr.FieldDefn(col, ogr.OFTReal)       # Création du champ (real) dans l'objet stat_classif_field_defn
                # Définition de la largeur du champ
                stat_classif_field_defn.SetWidth(20)
                # Définition de la précision du champ valeur flottante
                stat_classif_field_defn.SetPrecision(2)
                layer.CreateField(stat_classif_field_defn)
            if debug >= 3:
                print(cyan + "statisticsVectorRaster() : " + endC + "Creation de la colonne : " + str(col))

    # Creation des colonnes reliées au dictionnaire
    if ('all' in col_to_add_list) or ('count' in col_to_add_list) or ('all_S' in col_to_add_list) or ('count_S' in col_to_add_list):
        for col in class_label_dico:

            # Gestion du nom de la colonne correspondant à la classe
            name_col = class_label_dico[col]
            if len(name_col) > 10:
                name_col = name_col[:10]
                print(cyan + "statisticsVectorRaster() : " + bold + yellow + "Nom de la colonne trop long. Il sera tronque a 10 caracteres en cas d'utilisation: " + endC + name_col)

            # Gestion du nom de la colonne correspondant à la surface de la classe
            name_col_area =  PREFIX_AREA_COLUMN + name_col
            if len(name_col_area) > 10:
                name_col_area = name_col_area[:10]
                if debug >= 3:
                    print(cyan + "statisticsVectorRaster() : " + bold + yellow + "Nom de la colonne trop long. Il sera tronque a 10 caracteres en cas d'utilisation: " + endC + name_col_area)

            # Ajout des colonnes de % de répartition des éléments du raster
            if ('all' in col_to_add_list) or ('count' in col_to_add_list):
                if layer_definition.GetFieldIndex(name_col) == -1 :                     # Vérification de l'existence de la colonne name_col (retour = -1 : elle n'existe pas)
                    stat_classif_field_defn = ogr.FieldDefn(name_col, ogr.OFTReal)      # Création du champ (real) dans l'objet stat_classif_field_defn
                    # Définition de la largeur du champ
                    stat_classif_field_defn.SetWidth(20)
                    # Définition de la précision du champ valeur flottante
                    stat_classif_field_defn.SetPrecision(2)
                    if debug >= 3:
                        print(cyan + "statisticsVectorRaster() : " + endC + "Creation de la colonne : " + str(name_col))
                    layer.CreateField(stat_classif_field_defn)                          # Ajout du champ

            # Ajout des colonnes de surface des éléments du raster
            if ('all_S' in col_to_add_list) or ('count_S' in col_to_add_list):
                if layer_definition.GetFieldIndex(name_col_area) == -1 :                # Vérification de l'existence de la colonne name_col_area (retour = -1 : elle n'existe pas)
                    stat_classif_field_defn = ogr.FieldDefn(name_col_area, ogr.OFTReal) # Création du nom du champ dans l'objet stat_classif_field_defn
                    # Définition de la largeur du champ
                    stat_classif_field_defn.SetWidth(20)
                    # Définition de la précision du champ valeur flottante
                    stat_classif_field_defn.SetPrecision(2)

                    if debug >= 3:
                        print(cyan + "statisticsVectorRaster() : " + endC + "Creation de la colonne : " + str(name_col_area))
                    layer.CreateField(stat_classif_field_defn)                          # Ajout du champ

    if debug >= 2:
        print(cyan + "statisticsVectorRaster() : " + bold + green + "ETAPE 1/3 : FIN DE LA CREATION DES COLONNES DANS LE FICHIER VECTEUR %s" %(vector_output)+ endC)

    # ETAPE 3/4 : REMPLISSAGE DES COLONNES DU VECTEUR
    if debug >= 2:
        print(cyan + "statisticsVectorRaster() : " + bold + green + "ETAPE 2/3 : DEBUT DU REMPLISSAGE DES COLONNES DU VECTEUR "+ endC)

    # Calcul des statistiques col_to_add_inter02_list = [majority, minority, min, max, mean, median, sum, std, unique, range, all, count, all_S, count_S] de croisement images_raster / vecteur
    # Utilisation de la librairie rasterstat
    if debug >= 3:
        print(cyan + "statisticsVectorRaster() : " + bold + green + "Calcul des statistiques " + endC +"Stats : %s - Vecteur : %s - Raster : %s" %(col_to_add_inter02_list, vector_output, image_input) + endC)
    stats_info_list = raster_stats(vector_output, image_input, band_num=band_number, stats=col_to_add_inter02_list)

    # Decompte du nombre de polygones
    num_features = layer.GetFeatureCount()
    if debug >= 3:
        print(cyan + "statisticsVectorRaster() : " +  bold + green + "Remplissage des colonnes polygone par polygone " + endC)
    if debug >= 3:
        print(cyan + "statisticsVectorRaster() : " + endC + "Nombre total de polygones : " + str(num_features))

    polygone_count = 0

    for polygone_stats in stats_info_list : # Pour chaque polygone représenté dans stats_info_list - et il y a autant de polygone que dans le fichier vecteur

        # Extraction de feature
        feature = layer.GetFeature(polygone_stats['__fid__'])

        polygone_count = polygone_count + 1

        if debug >= 3 and polygone_count%10000 == 0:
            print(cyan + "statisticsVectorRaster() : " + endC + "Avancement : %s polygones traites sur %s" %(polygone_count,num_features))
        if debug >= 5:
            print(cyan + "statisticsVectorRaster() : " + endC + "Traitement du polygone : ",  stats_info_list.index(polygone_stats) + 1)

        # Remplissage de l'identifiant unique
        if ("UniqueID" in col_to_add_list) or ("uniqueID" in col_to_add_list) or ("ID" in col_to_add_list):
            feature.SetField('ID', int(stats_info_list.index(polygone_stats)))

        # Initialisation à 0 des colonnes contenant le % de répartition de la classe - Verifier ce qu'il se passe si le nom dépasse 10 caracteres
        if ('all' in col_to_add_list) or ('count' in col_to_add_list):
            for element in class_label_dico:
                name_col = class_label_dico[element]
                if len(name_col) > 10:
                    name_col = name_col[:10]
                feature.SetField(name_col,0)

        # Initialisation à 0 des colonnes contenant la surface correspondant à la classe - Verifier ce qu'il se passe si le nom dépasse 10 caracteres
        if ('all_S' in col_to_add_list) or ('count_S' in col_to_add_list):
            for element in class_label_dico:
                name_col = class_label_dico[element]
                name_col_area =  PREFIX_AREA_COLUMN + name_col
                if len(name_col_area) > 10:
                    name_col_area = name_col_area[:10]
                feature.SetField(name_col_area,0)

        # Remplissage des colonnes contenant le % de répartition et la surface des classes
        if ('all' in col_to_add_list) or ('count' in col_to_add_list) or ('all_S' in col_to_add_list) or ('count_S' in col_to_add_list):
            # 'all' est une liste des couples : (Valeur_du_pixel_sur_le_raster, Nbr_pixel_ayant_cette_valeur) pour le polygone observe.
            # Ex : [(0,183),(803,45),(801,4)] : dans le polygone, il y a 183 pixels de valeur 0, 45 pixels de valeur 803 et 4 pixels de valeur 801
            majority_all = polygone_stats['all']

            # Deux valeurs de pixel peuvent faire référence à une même colonne. Par exemple : les pixels à 201, 202, 203 peuvent correspondre à la BD Topo
            # Regroupement des éléments de majority_all allant dans la même colonne au regard de class_label_dico
            count_for_idx_couple = 0            # Comptage du nombre de modifications (suppression de couple) de majority_all pour adapter la valeur de l'index lors de son parcours

            for idx_couple in range(1,len(majority_all)) :  # Inutile d'appliquer le traitement au premier élément (idx_couple == 0)

                idx_couple = idx_couple - count_for_idx_couple    # Prise en compte dans le parcours de majority_all des couples supprimés
                couple = majority_all[idx_couple]                 # Ex : couple = (803,45)

                if (couple is None) or (couple == "") :    # en cas de bug de rasterstats (erreur geometrique du polygone par exemple)
                    if debug >= 3:
                        print(cyan + "statisticsVectorRaster() : " + bold + red + "Probleme detecte dans la gestion du polygone %s" %(polygone_count) + endC, file=sys.stderr)
                    pass
                else :
                    for idx_verif in range(idx_couple):
                        # Vérification au regard des éléments présents en amont dans majority_all
                        # Cas où le nom correspondant au label a déjà été rencontré dans majority_all
                        # Vérification que les pixels de l'image sont réferncés dans le dico
                        if couple[0] in class_label_dico:

                            if class_label_dico[couple[0]] == class_label_dico[majority_all[idx_verif][0]]:
                                majority_all[idx_verif] = (majority_all[idx_verif][0] , majority_all[idx_verif][1] + couple[1])  # Ajout du nombre de pixels correspondant dans le couple précédent
                                majority_all.remove(couple)                                                                      # Supression du couple présentant le "doublon"
                                count_for_idx_couple = count_for_idx_couple + 1                                                  # Mise à jour du décompte de modifications
                                break
                        else:
                           raise NameError(cyan + "statisticsVectorRaster() : " + bold + red + "The image file (%s) contain pixel value '%d' not identified into class_label_dico" %(image_input, couple[0]) + endC)

            # Intégration des valeurs de majority all dans les colonnes
            for couple_value_count in majority_all :                             # Parcours de majority_all. Ex : couple_value_count = (803,45)
                if (couple_value_count is None) or (couple_value_count == "") :  # en cas de bug de rasterstats (erreur geometrique du polygone par exemple)
                    if debug >= 3:
                        print(cyan + "statisticsVectorRaster() : " + bold + red + "Probleme detecte dans la gestion du polygone %s" %(polygone_count) + endC, file=sys.stderr)
                    pass
                else :
                    nb_pixel_total = polygone_stats['count']       # Nbr de pixels du polygone
                    pixel_value = couple_value_count[0]            # Valeur du pixel
                    value_count = couple_value_count[1]            # Nbr de pixels ayant cette valeur
                    name_col = class_label_dico[pixel_value]       # Transformation de la valeur du pixel en "signification" au regard du dictionnaire. Ex : BD Topo ou 2011
                    name_col_area =  PREFIX_AREA_COLUMN + name_col # Identification du nom de la colonne en surfaces

                    if len(name_col) > 10:
                        name_col = name_col[:10]
                    if len(name_col_area) > 10:
                        name_col_area = name_col_area[:10]

                    value_area = pixel_size * value_count                                    # Calcul de la surface du polygone correspondant à la valeur du pixel
                    if nb_pixel_total != None and nb_pixel_total != 0:
                        percentage = (float(value_count)/float(nb_pixel_total)) * 100  # Conversion de la surface en pourcentages, arondi au pourcent
                    else :
                        if debug >= 3:
                            print(cyan + "statisticsVectorRaster() : " + bold + red + "Probleme dans l'identification du nombre de pixels du polygone %s : le pourcentage de %s est mis à 0" %(polygone_count,name_col)+ endC, file=sys.stderr)
                        percentage = 0.0

                    if ('all' in col_to_add_list) or ('count' in col_to_add_list):
                        feature.SetField(name_col, percentage)      # Injection du pourcentage dans la colonne correpondante
                    if ('all_S' in col_to_add_list) or ('count_S' in col_to_add_list):
                        feature.SetField(name_col_area, value_area) # Injection de la surface dans la colonne correpondante
        else :
            pass

        # Remplissage des colonnes statistiques demandées ( col_to_add_inter01_list = [majority/DateMaj/SrcMaj, minority, min, max, mean, median, sum, std, unique, range] )
        for stats in col_to_add_inter01_list :

            if stats == 'DateMaj' or  stats == 'SrcMaj' :                # Cas particulier de 'DateMaj' et 'SrcMaj' : le nom de la colonne est DateMaj ou SrcMaj, mais la statistique utilisée est identifiée par majority
                name_col = stats                                         # Nom de la colonne. Ex : 'DateMaj'
                value_statis = polygone_stats['majority']                # Valeur majoritaire. Ex : '203'
                if value_statis == None:
                    value_statis_class = 'nan'
                else :
                    value_statis_class = class_label_dico[value_statis]  # Transformation de la valeur au regard du dictionnaire. Ex : '2011'
                feature.SetField(name_col, value_statis_class)           # Ajout dans la colonne

            elif (stats is None) or (stats == "") or (polygone_stats[stats] is None) or (polygone_stats[stats]) == "" or (polygone_stats[stats]) == 'nan' :
                # En cas de bug de rasterstats (erreur geometrique du polygone par exemple)
                pass

            else :
                name_col = stats                                         # Nom de la colonne. Ex : 'majority', 'max'
                value_statis = polygone_stats[stats]                     # Valeur à associer à la colonne, par exemple '2011'

                if (name_col == 'majority' or name_col == 'minority') and class_label_dico != [] : # Cas où la colonne fait référence à une valeur du dictionnaire
                    value_statis_class = class_label_dico[value_statis]
                else:
                    value_statis_class = value_statis

                feature.SetField(name_col, value_statis_class)

        layer.SetFeature(feature)
        feature.Destroy()

    if debug >= 2:
        print(cyan + "statisticsVectorRaster() : " + bold + green + "ETAPE 2/3 : FIN DU REMPLISSAGE DES COLONNES DU VECTEUR %s" %(vector_output)+ endC)

    # ETAPE 4/4 : SUPRESSION DES COLONNES NON SOUHAITEES
    if col_to_delete_list != []:

        if debug >= 2:
            print(cyan + "statisticsVectorRaster() : " + bold + green + "ETAPE 3/3 : DEBUT DES SUPPRESSIONS DES COLONNES %s" %(col_to_delete_list) + endC)

        for col_to_delete in col_to_delete_list :

            if layer_definition.GetFieldIndex(col_to_delete) != -1 :                   # Vérification de l'existence de la colonne col (retour = -1 : elle n'existe pas)

                layer.DeleteField(layer_definition.GetFieldIndex(col_to_delete))       # Suppression de la colonne

                if debug >= 3:
                    print(cyan + "statisticsVectorRaster() : " + endC + "Suppression de %s" %(col_to_delete) + endC)

        if debug >= 2:
            print(cyan + "statisticsVectorRaster() : " + bold + green + "ETAPE 3/3 : FIN DE LA SUPPRESSION DES COLONNES" + endC)

    else:
        print(cyan + "statisticsVectorRaster() : " + bold + yellow + "ETAPE 3/3 : AUCUNE SUPPRESSION DE COLONNE DEMANDEE" + endC)

    # Fermeture du fichier shape
    layer.SyncToDisk()
    layer = None
    data_source.Destroy()

    # Mise à jour du Log
    ending_event = "statisticsVectorRaster() : Compute statistic crossing ending : "
    timeLine(path_time_log,ending_event)

    return

###########################################################################################################################################
# MISE EN PLACE DU PARSER                                                                                                                 #
###########################################################################################################################################

# Code executé seulement dans le cas ou le script est lancé depuis une ligne de commande
# Il n'est pas executé lors d'un import CrossingVectorRaster.py
# Exemple de lancement en ligne de commande:
# python CrossingVectorRaster.py -i ../ImagesTestChaine/APTV_05/Resultats/APTV_05_classif.tif -v ../ImagesTestChaine/APTV_05/Resultats/APTV_05_classif_reaf_vectorised.shp -cld 0:Nuage 11000:Anthropise 21000:Ligneux -stc -sts -str -log ../ImagesTestChaine/APTV_05/fichierTestLog.txt

def main(gui=False):

    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, prog="CrossingVectorRaster", description="\
    Info : Computes the statistics of the intersection of a image_input (tif) for each polygon of a set of vectors (shape). \n\
    Objectif : Calcule les statistiques de l'intersection d'un image_input (tif) pour chaque polygones d'un jeu de vecteurs (shape). \n\
    Example : python CrossingVectorRaster.py -i ../ImagesTestChaine/APTV_05/Resultats/APTV_05_classif.tif \n\
                                             -v ../ImagesTestChaine/APTV_05/Resultats/APTV_05_classif_reaf_vectorised.shp \n\
                                             -cld 0:Nuage 11000:Anthropise 21000:Ligneux \n\
                                             -stc -sts -str \n\
                                             -log ../ImagesTestChaine/APTV_05/fichierTestLog.txt")

    parser.add_argument('-i','--image_input',default="",help="Image_raster image to analyze", type=str, required=True)
    parser.add_argument('-v','--vector_input',default="",help="Vector space on which we want to compute statistics", type=str, required=True)
    parser.add_argument('-o','--vector_output',default="",help="Name of the output. If not precised, the output vector is the input_vector", type=str, required=False)
    parser.add_argument('-bn','--band_number',default=1,help="Number of band used to compute from image input", type=int, required=False)
    parser.add_argument('-stc', '--stats_all_count', action='store_true',default=False, help="Option : enable compute statistics : 'all','count'. Need to activate class_label_dico", required=False)
    parser.add_argument('-sts', '--stats_columns_str', action='store_true',default=False, help="Option : enable compute statistics : 'majority','minority'. Need to activate class_label_dico.", required=False)
    parser.add_argument('-str', '--stats_columns_real', action='store_true', default=False, help="Option : enable compute statistics : 'min', 'max', 'mean' , 'median','sum', 'std', 'unique', 'range' ", required=False)
    parser.add_argument('-d','--col_to_delete_list',nargs="+",default=[],help="Existing column in attribute table that we want to delete. Ex : 'nbPixels meanB0 varB0'", type=str, required=False)
    parser.add_argument('-a','--col_to_add_list',nargs="+",default=[],help="Column in attribute table that we want to add. Ex : 'UniqueID all count majority minority min max mean median sum std unique range'", type=str, required=False)
    parser.add_argument("-cld", "--class_label_dico",nargs="+",default={}, help = "NB: to inquire if option stats_all_count is enable, dictionary of correspondence class Mandatory if all or count is un col_to_add_list. Ex: 0:Nuage 63:Vegetation 127:Bati 191:Voirie 255:Eau", type=str,required=False)
    parser.add_argument('-csp', '--clean_small_polygons', action='store_true', default=False, help="Clean polygons where area is smaller than 2 times the pixel area (which can introduce NaN values)", required=False)
    parser.add_argument('-vef','--format_vector', default="ESRI Shapefile",help="Format of the output file.", type=str, required=False)
    parser.add_argument('-log','--path_time_log',default="",help="Name of log", type=str, required=False)
    parser.add_argument('-sav','--save_results_inter',action='store_true',default=False,help="Save or delete intermediate result after the process. By default, False", required=False)
    parser.add_argument('-now','--overwrite',action='store_false',default=True,help="Overwrite files with same names. By default : True", required=False)
    parser.add_argument('-debug','--debug',default=3,help="Option : Value of level debug trace, default : 3 ",type=int, required=False)
    args = displayIHM(gui, parser)

    # Récupération des arguments donnés
    if args.image_input != None:
        image_input = args.image_input
        if not os.path.isfile(image_input):
            raise NameError (cyan + "CrossingVectorRaster : " + bold + red  + "File %s not existe!" %(image_input) + endC)

    if args.vector_input != None:
        vector_input = args.vector_input
        if not os.path.isfile(vector_input):
            raise NameError (cyan + "CrossingVectorRaster : " + bold + red  + "File %s not existe!" %(vector_input) + endC)

    if args.vector_output != None:
        vector_output = args.vector_output

    # Numero de bande du raster d'entrée
    if args.band_number != None:
        band_number = args.band_number

    # Options de groupe de colonnes à produire
    if args.stats_all_count != None:
        enable_stats_all_count = args.stats_all_count

    if args.stats_columns_str != None:
        enable_stats_columns_str = args.stats_columns_str

    if args.stats_columns_real != None:
        enable_stats_columns_real = args.stats_columns_real

    # Options listes des colonnes à ajouter et à suprimer
    if args.col_to_delete_list != None:
        col_to_delete_list = args.col_to_delete_list

    if args.col_to_add_list != None:
        col_to_add_list = args.col_to_add_list

    # Creation du dictionaire reliant les classes à leur label
    class_label_dico = {}
    if args.class_label_dico != None and args.class_label_dico != {}:
        for tmp_txt_class in args.class_label_dico:
            class_label_list = tmp_txt_class.split(':')
            class_label_dico[int(class_label_list[0])] = class_label_list[1]

    # Nettoyage des polygones dont surface < 2 fois surface d'un pixel
    if args.clean_small_polygons!= None:
        clean_small_polygons = args.clean_small_polygons

    # Récupération du format du fichier de sortie
    if args.format_vector != None :
        format_vector = args.format_vector

    # Récupération du nom du fichier log
    if args.path_time_log!= None:
        path_time_log = args.path_time_log

    # Sauvegarde des fichiers intermediaires
    if args.save_results_inter != None:
        save_results_intermediate = args.save_results_inter

    # Ecrasement des fichiers
    if args.overwrite!= None:
        overwrite = args.overwrite

    # Récupération de l'option niveau de debug
    if args.debug!= None:
        global debug
        debug = args.debug

    # Affichage des arguments récupérés
    if debug >= 3:
        print(bold + green + "Variables dans le parser" + endC)
        print(cyan + "CrossingVectorRaster : " + endC + "image_input : " + str(image_input) + endC)
        print(cyan + "CrossingVectorRaster : " + endC + "vector_input : " + str(vector_input) + endC)
        print(cyan + "CrossingVectorRaster : " + endC + "vector_output : " + str(vector_output) + endC)
        print(cyan + "CrossingVectorRaster : " + endC + "band_number : " + str(band_number) + endC)
        print(cyan + "CrossingVectorRaster : " + endC + "stats_all_count : " + str(enable_stats_all_count) + endC)
        print(cyan + "CrossingVectorRaster : " + endC + "stats_columns_str : " + str(enable_stats_columns_str) + endC)
        print(cyan + "CrossingVectorRaster : " + endC + "stats_columns_real : " + str(enable_stats_columns_real) + endC)
        print(cyan + "CrossingVectorRaster : " + endC + "col_to_delete_list : " + str(col_to_delete_list) + endC)
        print(cyan + "CrossingVectorRaster : " + endC + "col_to_add_list : " + str(col_to_add_list) + endC)
        print(cyan + "CrossingVectorRaster : " + endC + "class_label_dico : " + str(class_label_dico) + endC)
        print(cyan + "CrossingVectorRaster : " + endC + "clean_small_polygons : " + str(clean_small_polygons) + endC)
        print(cyan + "CrossingVectorRaster : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "CrossingVectorRaster : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "CrossingVectorRaster : " + endC + "save_results_inter : " + str(save_results_intermediate) + endC)
        print(cyan + "CrossingVectorRaster : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "CrossingVectorRaster : " + endC + "debug : " + str(debug) + endC)

    if not enable_stats_all_count and not enable_stats_columns_str and not enable_stats_columns_real and not col_to_add_list :
        print(cyan + "CrossingVectorRaster() : " + bold + red + "You did not fill up properly the parameters, please check before launching." + endC, file=sys.stderr)
        exit(0)

    # Si le dossier de sortie n'existe pas, on le crée
    repertory_output = os.path.dirname(vector_output)
    if not os.path.isdir(repertory_output):
        os.makedirs(repertory_output)

    # Execution de la fonction
    statisticsVectorRaster(image_input, vector_input, vector_output, band_number, enable_stats_all_count, enable_stats_columns_str, enable_stats_columns_real, col_to_delete_list, col_to_add_list, class_label_dico, path_time_log, clean_small_polygons, format_vector, save_results_intermediate, overwrite)

# ================================================

if __name__ == '__main__':
  main(gui=False)
