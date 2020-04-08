#!/usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerSO/DALETT/SCGSI  All rights reserved.                                                                            #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# CE SCRIPT PERMET DE CARTOGRAPHIER LES LCZ A PARTIR DE 8 INDICATEURS                                                                       #
#                                                                                                                                           #
#############################################################################################################################################

'''
Nom de l'objet : ClassificationLCZ.py
Description :
    Objectif : Etablir une classification LCZ (sous format vecteur) à partir de divers indicateurs (également sous format vecteurs)

Date de creation : 03/11/2016
----------
Histoire :
----------
Origine : Réécriture d'un ancien script qui faisait la même chose, mais sous PostGIS
03/11/2016 : Création
19/01/2017 : Ajout de l'indicateur 'soil occupation'
23/02/2017 : Tri des valeurs indicateurs suivant ID croissant
16/04/2019 : Adaptation a la V9.2 du Logigramme ajout de info H_moy_Veg, H_max_Veg, Bati, Route, Eau, SolNu, Vegetation
----------------------------------------------------------------------------------------------------

'''

from __future__ import print_function
import os, sys, shutil, argparse
from osgeo import ogr
import pandas as pd
import numpy as np
import openturns as ot
from simpledbf import Dbf5
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GridSearchCV
#from sklearn.externals import joblib
import joblib
from Lib_log import timeLine
from Lib_display import displayIHM, bold, red, green, yellow, blue, magenta, cyan, endC
from Lib_file import removeVectorFile, copyVectorFile, removeFile, renameFile
from Lib_text import saveDataFrame2Dbf, extractDico
from Lib_vector import getAttributeValues, addNewFieldVector, setAttributeIndexValuesList
from Lib_operator import *

debug = 3

####################################################################################################
# FONCTION stackShapeLCZ()                                                                         #
####################################################################################################
# ROLE:
#     Fusionner les données attributaires des indicateurs utilisées pour le calcul des LCZ
#     et sauvegarder ces données dans le fichier vecteur de maillage Urban Atlas de sortie
#
# ENTREES DE LA FONCTION :
#     urban_atlas_input : fichier de maillage Urban Atlas en entrée
#     lcz_output : fichier de maillage Urban Atlas en sortie, avec la valeur LCZ par maille
#     building_surface_fraction_input : fichier Building Surface Fraction en entrée
#     impervious_surface_fraction_input : fichier Impervious Surface Fraction en entrée
#     pervious_surface_fraction_input : fichier Pervious Surface Fraction en entrée
#     sky_view_factor_input : fichier Sky View Factor en entrée
#     height_roughness_elements_input : fichier Height of Roughness Elements en entrée
#     terrain_roughness_class_input : fichier terrain Roughness Class en entrée
#     aspect_ratio_input : fichier Aspect Ratio en entrée
#     soil_occupation_input : fichier occupation du sol en entrée
#     indicator_list : liste des indicateurs utilisés pour l'attribution des LCZ
#     column_list : liste des colonnes contenant chacun des indicateurs précédents
#     abbreviation_list : liste des abréviations utilisées
#     column_id_ua : nom de la colonne 'id' du fichier Urban Atlas en d'entree
#     path_time_log : fichier log de sortie
#     format_vector : format du fichier vecteur. Optionnel, par default : 'ESRI Shapefile'
#     save_results_intermediate : fichiers de sorties intermédiaires nettoyés, par défaut = False
#     overwrite : écrase si un fichier existant a le même nom qu'un fichier de sortie, par défaut = True
#
# SORTIES DE LA FONCTION :
#     N.A.

def stackShapeLCZ(urban_atlas_input, lcz_output, building_surface_fraction_input, impervious_surface_fraction_input, pervious_surface_fraction_input, sky_view_factor_input, height_roughness_elements_input, terrain_roughness_class_input, aspect_ratio_input, soil_occupation_input, indicator_list, column_list, abbreviation_list, column_id_ua, path_time_log, format_vector='ESRI Shapefile', save_results_intermediate=False, overwrite=True):

    print(bold + green + "Début de la fusion des données attributaires des indicateurs." + endC + "\n")
    timeLine(path_time_log, "Début de la fusion des données attributaires des indicateurs : ")

    if debug >= 3:
        print(bold + green + "stackShapeLCZ() : Variables dans la fonction" + endC)
        print(cyan + "stackShapeLCZ() : " + endC + "urban_atlas_input : " + str(urban_atlas_input) + endC)
        print(cyan + "stackShapeLCZ() : " + endC + "lcz_output : " + str(lcz_output) + endC)
        print(cyan + "stackShapeLCZ() : " + endC + "building_surface_fraction_input : " + str(building_surface_fraction_input) + endC)
        print(cyan + "stackShapeLCZ() : " + endC + "impervious_surface_fraction_input : " + str(impervious_surface_fraction_input) + endC)
        print(cyan + "stackShapeLCZ() : " + endC + "pervious_surface_fraction_input : " + str(pervious_surface_fraction_input) + endC)
        print(cyan + "stackShapeLCZ() : " + endC + "sky_view_factor_input : " + str(sky_view_factor_input) + endC)
        print(cyan + "stackShapeLCZ() : " + endC + "height_roughness_elements_input : " + str(height_roughness_elements_input) + endC)
        print(cyan + "stackShapeLCZ() : " + endC + "terrain_roughness_class_input : " + str(terrain_roughness_class_input) + endC)
        print(cyan + "stackShapeLCZ() : " + endC + "aspect_ratio_input : " + str(aspect_ratio_input) + endC)
        print(cyan + "stackShapeLCZ() : " + endC + "soil_occupation_input : " + str(soil_occupation_input) + endC)
        print(cyan + "stackShapeLCZ() : " + endC + "indicator_list : " + str(indicator_list) + endC)
        print(cyan + "stackShapeLCZ() : " + endC + "column_list : " + str(column_list) + endC)
        print(cyan + "stackShapeLCZ() : " + endC + "abbreviation_list : " + str(abbreviation_list) + endC)
        print(cyan + "stackShapeLCZ() : " + endC + "column_id_ua : " + str(column_id_ua) + endC)
        print(cyan + "stackShapeLCZ() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "stackShapeLCZ() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "stackShapeLCZ() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "stackShapeLCZ() : " + endC + "overwrite : " + str(overwrite) + endC)

    # Copie du fichier Urban Atlas d'entrée vers celui en sortie
    if os.path.exists(lcz_output) and not overwrite:
        print(bold + magenta + "Le fichier de sortie '" + lcz_output + "' existe déjà, le traitement ne peut avoir lieu." + endC)
        exit(0)
    else:
        if os.path.exists(lcz_output):
            removeVectorFile(lcz_output)
        copyVectorFile(urban_atlas_input, lcz_output)

    # Création d'un dico
    indiceInfoDico = {}
    for idx in range(len(indicator_list)):
        indice  = indicator_list[idx]
        indiceInfoDico[indice] = []

        while switch(indice):
            if case('BuildingSurfaceFraction'):
                indiceInfoDico[indice].append(building_surface_fraction_input)
                break
            if case('ImperviousSurfaceFraction'):
                indiceInfoDico[indice].append(impervious_surface_fraction_input)
                break
            if case('PerviousSurfaceFraction'):
                indiceInfoDico[indice].append(pervious_surface_fraction_input)
                break
            if case('SkyViewFactor'):
                indiceInfoDico[indice].append(sky_view_factor_input)
                break
            if case('HeightOfRoughnessElements'):
                indiceInfoDico[indice].append(height_roughness_elements_input)
                break
            if case('TerrainRoughnessClass'):
                indiceInfoDico[indice].append(terrain_roughness_class_input)
                break
            if case('AspectRatio'):
                indiceInfoDico[indice].append(aspect_ratio_input)
                break
            if case('SoilOccupation'):
                indiceInfoDico[indice].append(soil_occupation_input)
                break
            if case('BuiltRate'):
                indiceInfoDico[indice].append(soil_occupation_input)
                break
            if case('RoadRate'):
                indiceInfoDico[indice].append(soil_occupation_input)
                break
            if case('WaterRate'):
                indiceInfoDico[indice].append(soil_occupation_input)
                break
            if case('BareSoilRate'):
                indiceInfoDico[indice].append(soil_occupation_input)
                break
            if case('VegetationRate'):
                indiceInfoDico[indice].append(soil_occupation_input)
                break
            if case('AverageVegetationHeight'):
                indiceInfoDico[indice].append(soil_occupation_input)
                break
            if case('MaxVegetationHeight'):
                indiceInfoDico[indice].append(soil_occupation_input)
                break
            break

        # Ajout des noms des colonnes sources et destinations
        indiceInfoDico[indice].append(column_list[idx])
        indiceInfoDico[indice].append(abbreviation_list[idx])

    # Parcours du dico pour gérer tous les fichiers indicateurs
    # ---------------------------------------------------------
    for indice in indiceInfoDico:
        info_list = indiceInfoDico[indice]
        vector_input = info_list[0]
        column_src = info_list[1]
        column_dst = info_list[2]

        # On récupère la liste de données
        attribute_name_dico = {}
        attribute_name_dico[column_id_ua] = ogr.OFTInteger

        # Traiement du cas ou il n'y a pas de fichier d'indice d'entrée
        if vector_input == "" :
           vector_input = urban_atlas_input
        else :
            attribute_name_dico[column_src] = ogr.OFTReal
        res_dico = getAttributeValues(vector_input, None, None, attribute_name_dico, format_vector)

        # Tri de la liste de données (le calcul de certains indicateurs change l'ordre des ID)
        index_list = res_dico[column_id_ua]
        index_sort_list = sorted(index_list)
        value_sort_list = []
        for id_ua in index_sort_list:
            index = index_list.index(id_ua)
            # Si la colonne exite pour traiter le cas ou le fichier d'indice d'entrée n'existe pas...
            if column_src in res_dico :
                value = res_dico[column_src][index]
            else :
                # Dans ce cas les valeurs de la colonnes seront toutes à zéro
                value = 0.0
            value_sort_list.append(value)

        # Nouvelle liste triée suivant l'ID croissant
        res_dico[column_id_ua] = index_sort_list
        res_dico[column_src] = value_sort_list
        indiceInfoDico[indice].append(res_dico)

        # On ajoute la liste de données au fichier de sortie
        field_type = ogr.OFTReal
        if indice in ("TerrainRoughnessClass", "SoilOccupation"):
            field_type = ogr.OFTInteger
        addNewFieldVector(lcz_output, column_dst, field_type, 0, 6, 2, format_vector)

    # Remplissage du fichier de sortie
    field_new_values_dico = {}
    for i in range(len(res_dico[column_src])):
        id_polygon = res_dico[column_id_ua][i]
        field_new_values_dico[id_polygon] = {indiceInfoDico['BuildingSurfaceFraction'][2]:indiceInfoDico['BuildingSurfaceFraction'][3][indiceInfoDico['BuildingSurfaceFraction'][1]][i], \
                                             indiceInfoDico['ImperviousSurfaceFraction'][2]:indiceInfoDico['ImperviousSurfaceFraction'][3][indiceInfoDico['ImperviousSurfaceFraction'][1]][i], \
                                             indiceInfoDico['PerviousSurfaceFraction'][2]:indiceInfoDico['PerviousSurfaceFraction'][3][indiceInfoDico['PerviousSurfaceFraction'][1]][i], \
                                             indiceInfoDico['SkyViewFactor'][2]:indiceInfoDico['SkyViewFactor'][3][indiceInfoDico['SkyViewFactor'][1]][i], \
                                             indiceInfoDico['HeightOfRoughnessElements'][2]:indiceInfoDico['HeightOfRoughnessElements'][3][indiceInfoDico['HeightOfRoughnessElements'][1]][i], \
                                             indiceInfoDico['TerrainRoughnessClass'][2]:indiceInfoDico['TerrainRoughnessClass'][3][indiceInfoDico['TerrainRoughnessClass'][1]][i], \
                                             indiceInfoDico['AspectRatio'][2]:indiceInfoDico['AspectRatio'][3][indiceInfoDico['AspectRatio'][1]][i], \
                                             indiceInfoDico['SoilOccupation'][2]:indiceInfoDico['SoilOccupation'][3][indiceInfoDico['SoilOccupation'][1]][i], \
                                             indiceInfoDico['BuiltRate'][2]:indiceInfoDico['BuiltRate'][3][indiceInfoDico['BuiltRate'][1]][i], \
                                             indiceInfoDico['RoadRate'][2]:indiceInfoDico['RoadRate'][3][indiceInfoDico['RoadRate'][1]][i], \
                                             indiceInfoDico['WaterRate'][2]:indiceInfoDico['WaterRate'][3][indiceInfoDico['WaterRate'][1]][i], \
                                             indiceInfoDico['BareSoilRate'][2]:indiceInfoDico['BareSoilRate'][3][indiceInfoDico['BareSoilRate'][1]][i], \
                                             indiceInfoDico['VegetationRate'][2]:indiceInfoDico['VegetationRate'][3][indiceInfoDico['VegetationRate'][1]][i], \
                                             indiceInfoDico['AverageVegetationHeight'][2]:indiceInfoDico['AverageVegetationHeight'][3][indiceInfoDico['AverageVegetationHeight'][1]][i], \
                                             indiceInfoDico['MaxVegetationHeight'][2]:indiceInfoDico['MaxVegetationHeight'][3][indiceInfoDico['MaxVegetationHeight'][1]][i]}

    # Mise à jour des champs indicateurs
    setAttributeIndexValuesList(lcz_output, column_id_ua, field_new_values_dico, format_vector)

    if debug >= 2:
        print(bold + green + "Fin de la fusion des données attributaires des indicateurs." + endC + "\n")
    timeLine(path_time_log, "Fin de la fusion des données attributaires des indicateurs : ")

    return

####################################################################################################
# FONCTION computeLCZ()                                                                            #
####################################################################################################
# ROLE:
#     Calculer les LCZ à partir des valeurs des différents indicateurs
#     et sauvegarder ces données dans le fichier vecteur de maillage Urban Atlas de sortie
#
# ENTREES DE LA FONCTION :
#     inport_tree : l'arbre de décision
#     lcz_output : fichier de maillage Urban Atlas en sortie, avec la valeur LCZ par maille
#     abbreviation_list : liste des abréviations utilisées
#     column_id_ua : nom de la colonne 'id' du fichier Urban Atlas en d'entree
#     column_code_ua : nom de la colonne 'code' du fichier Urban Atlas en d'entree
#     column_lcz_histo : nom de la colonne contenant la classe LCZ intermédiaire dans le fichier de sortie
#     column_lcz : nom de la colonne contenant la classe LCZ dans le fichier de sortie
#     correspondance_values_dico : dictionaire de correspondance variable et valeur
#     path_time_log : fichier log de sortie
#     format_vector : format du fichier vecteur. Optionnel, par default : 'ESRI Shapefile'
#     save_results_intermediate : fichiers de sorties intermédiaires nettoyés, par défaut = False
#     overwrite : écrase si un fichier existant a le même nom qu'un fichier de sortie, par défaut = True
#
# SORTIES DE LA FONCTION :
#     N.A.

def computeLCZ(inport_tree, lcz_output, abbreviation_list, column_id_ua, column_code_ua, column_lcz_histo, column_lcz, correspondance_values_dico, path_time_log, format_vector='ESRI Shapefile', save_results_intermediate=False, overwrite=True):

    if debug >= 2:
        print(cyan + "computeLCZ() : " + bold + green + "Début du calcul des LCZ à partir des indicateurs." + endC + "\n")
    timeLine(path_time_log, "Début du calcul des LCZ à partir des indicateurs : ")

    if debug >= 3:
        print(bold + green + "computeLCZ() : Variables dans la fonction" + endC)
        print(cyan + "computeLCZ() : " + endC + "lcz_output : " + str(lcz_output) + endC)
        print(cyan + "computeLCZ() : " + endC + "abbreviation_list : " + str(abbreviation_list) + endC)
        print(cyan + "computeLCZ() : " + endC + "column_id_ua : " + str(column_id_ua) + endC)
        print(cyan + "computeLCZ() : " + endC + "column_code_ua : " + str(column_code_ua) + endC)
        print(cyan + "computeLCZ() : " + endC + "column_lcz_histo : " + str(column_lcz_histo) + endC)
        print(cyan + "computeLCZ() : " + endC + "column_lcz : " + str(column_lcz) + endC)
        print(cyan + "computeLCZ() : " + endC + "correspondance_values_dico : " + str(correspondance_values_dico) + endC)
        print(cyan + "computeLCZ() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "computeLCZ() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "computeLCZ() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "computeLCZ() : " + endC + "overwrite : " + str(overwrite) + endC)

    # Lecture des champs de données
    attribute_name_dico = {}
    attribute_name_dico[column_id_ua] = ogr.OFTInteger
    attribute_name_dico[column_code_ua] = ogr.OFTString
    for field_name in abbreviation_list:
        attribute_name_dico[field_name] = ogr.OFTReal
    res_indices_dico = getAttributeValues(lcz_output, None, None, attribute_name_dico)

    # Création des champs LCZ
    addNewFieldVector(lcz_output, column_lcz_histo, ogr.OFTString, 0, 20, None, format_vector)
    addNewFieldVector(lcz_output, column_lcz, ogr.OFTString, 0, 2, None, format_vector)

    # Calcul des LCZ
    field_new_values_dico = {}
    for i in range(len(res_indices_dico[column_id_ua])) :
        historic = "None"
        lcz = "None"
        id_polygon = res_indices_dico[column_id_ua][i]
        code_ua = res_indices_dico[column_code_ua][i]
        bsf = res_indices_dico['BSF'][i]
        isf = res_indices_dico['ISF'][i]
        psf = res_indices_dico['PSF'][i]
        svf = res_indices_dico['SVF'][i]
        hre = res_indices_dico['HRE'][i]
        trc = res_indices_dico['TRC'][i]
        ara = res_indices_dico['ARa'][i]
        ocs = res_indices_dico['OCS'][i]
        bur = res_indices_dico['BUr'][i]
        ror = res_indices_dico['ROr'][i]
        war = res_indices_dico['WAr'][i]
        bsr = res_indices_dico['BSr'][i]
        ver = res_indices_dico['VEr'][i]
        vea = res_indices_dico['VEa'][i]
        vem = res_indices_dico['VEm'][i]

        values_dico = {'HRE':hre, 'BSF':bsf, 'PSF':psf, 'SVF':svf, 'ISF':isf, 'ARa':ara, 'TRC':trc, 'OCS':ocs, 'BUr':bur, 'ROr':ror, 'WAr':war, 'BSr':bsr, 'VEr':ver, 'VEa':vea, 'VEm':vem}

        lcz,lcz_historic = selectTree(code_ua, values_dico, inport_tree, correspondance_values_dico)
        field_new_values_dico[id_polygon] = {column_lcz_histo:lcz_historic, column_lcz:lcz}

    # Mise à jour des champs LCZ
    setAttributeIndexValuesList(lcz_output, column_id_ua, field_new_values_dico, format_vector)

    if debug >= 2:
        print(cyan + "computeLCZ() : " + bold + green + "Fin du calcul des LCZ à partir des indicateurs." + endC + "\n")
    timeLine(path_time_log, "Fin du calcul des LCZ à partir des indicateurs : ")

    return

####################################################################################################
# FONCTION selectTree()                                                                            #
####################################################################################################
# ROLE:
#     Selection de l'arbre de décision LCZ selon l'entree Urban Atlas
#
# ENTREES DE LA FONCTION :
#     code_ua     : identifiant quartier Urban Atlas
#     values_dico : les valeurs des indicateurs pour un polygone sous forme de dico
#     inport_tree : l'arbre de decision
#     correspondance_values_dico : dictionaire de correspondance variable et valeur
#
# SORTIES DE LA FONCTION :
#      la valeur LCZ finale

def selectTree(code_ua, values_dico, inport_tree, correspondance_values_dico={}):

    while switch(int(code_ua)):
        if case(11100) or case(11210) or case(11220) or case(11230) or case(11240) or case(11300) or case(12100):
            historic = runTree(values_dico, getattr(inport_tree, 'tree_A'), correspondance_values_dico)
            break
        if case(12300) or case(12400) or case(13100) or case(13300) or case(13400) or case(14200):
            historic = runTree(values_dico, getattr(inport_tree, 'tree_B'), correspondance_values_dico)
            break
        if case(14100):
            historic = runTree(values_dico, getattr(inport_tree, 'tree_C'), correspondance_values_dico)
            break
        if case(21000):
            historic = runTree(values_dico, getattr(inport_tree, 'tree_D'), correspondance_values_dico)
            break
        if case(22000) or case(23000):
            historic = runTree(values_dico, getattr(inport_tree, 'tree_E'), correspondance_values_dico)
            break
        if case(24000) or case(32000):
            historic = runTree(values_dico, getattr(inport_tree, 'tree_F'), correspondance_values_dico)
            break
        if case(25000):
            historic = runTree(values_dico, getattr(inport_tree, 'tree_G'), correspondance_values_dico)
            break
        if case(31000):
            historic = runTree(values_dico, getattr(inport_tree, 'tree_H'), correspondance_values_dico)
            break
        if case(33000):
            historic = runTree(values_dico, getattr(inport_tree, 'tree_I'), correspondance_values_dico)
            break
        if case(40000):
            historic = runTree(values_dico, getattr(inport_tree, 'tree_J'), correspondance_values_dico)
            break
        if case(12210) or case(12220) or case(12230):
            historic = 'LCZ E_031'
            break
        if case(50000):
            historic = 'LCZ G_041'
            break
        break

    lcz = convertToLCZ(historic)

    return lcz, historic

####################################################################################################
# FONCTION runTree()                                                                               #
####################################################################################################
# ROLE:
#     Parcours de l'arbre de décision LCZ
#
# ENTREES DE LA FONCTION :
#     values_dico : les valeurs des indicateurs pour un polygone sous forme de dico
#     tree : l'arbre de décision
#     correspondance_values_dico : dictionaire de correspondance variable et valeur
#
# SORTIES DE LA FONCTION :
#      la valeur LCZ brute (historic)

def runTree(values_dico, tree, correspondance_values_dico):

    historic = None

    if tree is not []:

        for elem_dico in tree:
            # Récupération de l'indicateur
            index = list(elem_dico)[0]

            # Récupération de la valeur de cet indicateur pour ce polygone
            value_index = values_dico[index]

            # Récupération des infos dans l'arbre
            info_list = elem_dico[index]
            val_min = info_list[0]   # Seuil min
            val_max = info_list[1]   # Seuil max
            next_elem = info_list[2] # Résultat si valeur de l'indicateur dans l'intervalle

            if isinstance(val_min, int) or isinstance(val_min, float):
                threshold_low = val_min
            elif val_min in correspondance_values_dico.keys() :
                threshold_low = float(correspondance_values_dico[val_min][0][0])
            else :
                print(cyan + "runTree() : " + bold + yellow + " Variable non trouver dans le dictionnaire de correspondance de valeur: " + val_min + endC)
                threshold_low = 0

            if isinstance(val_max, int) or isinstance(val_max, float):
                threshold_high = val_max
            elif val_max in correspondance_values_dico.keys() :
                threshold_high = float(correspondance_values_dico[val_max][0][0])
            else :
                print(cyan + "runTree() : " + bold + yellow + " Variable non trouver dans le dictionnaire de correspondance de valeur: " + val_max + endC)
                threshold_high = 0

            # Test si les seuils correspondent à la valeur de l'indicateur
            find = False
            # Cas normal où un seul intervalle dans la classification
            if threshold_high >= threshold_low :
                find = ((threshold_low < value_index) and (value_index <= threshold_high)) or ((threshold_low == threshold_high) and (value_index == threshold_high))

            # Cas particulier où plusieurs intervalles pour une même branche (ex : x<10 or x>=60), mais ne prend pas en compte les cas où au moins 3 intervalles sont présents (ex : x<10 or 30<=x<40 or x>=60)
            # => dans l'arbre de décision, on passe les valeurs min et max que peut prendre l'indicateur (si LCZ pas attribuée avant, on se retrouvera dans cette branche), on repasse dans le cas normal
            else :
                find = (value_index <= threshold_high) or (threshold_low < value_index)

            # Si la valeur est comprise dans les seuils...
            if find :
                # ... on continu si l'arbre n'est pas terminé (appel récursif)...
                if type(next_elem) == list:
                    historic = runTree(values_dico, next_elem, correspondance_values_dico)
                # ... on retourne la valeur LCZ si on est arrivé au bout d'une branche
                else:
                    historic = next_elem
                break

    return historic

####################################################################################################
# FONCTION convertToLCZ()                                                                          #
####################################################################################################
# ROLE:
#     Convertie la valeur LCZ brute en valeur LCZ exploitable
#
# ENTREES DE LA FONCTION :
#     historic : la valeur LCZ calculé brute
#
# SORTIES DE LA FONCTION :
#      la valeur LCZ finale (lcz)

def convertToLCZ(historic):
    lcz = 'None'
    if historic is not None and historic[:3] == "LCZ":
        pos = historic.find('_')
        lcz = historic[4:pos]
    elif historic != 'None' :
        lcz = '0'
    return lcz

####################################################################################################
# FONCTION computeTreeRFmodel()                                                                    #
####################################################################################################
# ROLE:
#     Fabrique le modele Random Forest destiné à supplanter l'arbre en cas d'indecision
#
# ENTREES DE LA FONCTION :
#     inport_tree : l'arbre de décision
#     nb_sample_rf : nombre d'echantillons pour le Randon Forest
#     model_file_rf : nom du fichier contenant le model du Randon Forest
#     types_lcz_list : liste des type de classification LCZ
#     categories_ua_list : liste de categories de classification Urban Atlas
#     correspondance_values_dico : dictionaire de correspondance variable et valeur
#
# SORTIES DE LA FONCTION :
#     le modele RF

def computeTreeRFmodel(inport_tree, nb_sample_rf, model_file_rf, types_lcz_list, categories_ua_list, correspondance_values_dico):

     if debug >= 3:
        print(bold + green + "computeTreeRFmodel() : Variables dans la fonction" + endC)
        print(cyan + "computeTreeRFmodel() : " + endC + "nb_sample_rf : " + str(nb_sample_rf) + endC)
        print(cyan + "computeTreeRFmodel() : " + endC + "model_file_rf : " + str(model_file_rf) + endC)
        print(cyan + "computeTreeRFmodel() : " + endC + "types_lcz_list : " + str(types_lcz_list) + endC)
        print(cyan + "computeTreeRFmodel() : " + endC + "categories_ua_list : " + str(categories_ua_list) + endC)
        print(cyan + "computeTreeRFmodel() : " + endC + "correspondance_values_dico : " + str(correspondance_values_dico) + endC)

     if debug >= 2:
         print(cyan + "computeTreeRFmodel() : " + bold + green  + "Calcul du modele Random Forest " + endC)

     # Definition des plages de variation['code_ua','SVF','TRC','HRE','ISF','BSF','AR','PSF']
     distribution = ot.ComposedDistribution([ot.UserDefined([[i] for i in range(0,27)]),ot.Uniform(0.1, 1),ot.Uniform(1.0, 8.0),ot.Uniform(0.0, 30.0),ot.Uniform(0.0, 100.0),ot.Uniform(0.0, 94.0),ot.Uniform(0.0, 3.0),ot.Uniform(0.0, 100.0),ot.UserDefined([[i] for i in range(0,5)]),ot.Uniform(0.0, 100.0),ot.Uniform(0.0, 50.0)])
     dimension = distribution.getDimension()
     ot.RandomGenerator.SetSeed(0)

     # Fabrication des sequences aleatoires pour les 7 parametres + le code Urban Atlas
     inputDesign = ot.LHSExperiment(distribution, nb_sample_rf, True).generate()
     inputDesign_df = pd.DataFrame(np.array(inputDesign),columns=['code_ua','SVF','TRC','HRE','ISF','BSF','AR','PSF','OCS','VEr','VEa'])

     # Creation des dataframes contenant la base d'apprantissage du modele RF
     df_X_train_RF = pd.DataFrame([])
     df_Y_train_RF = pd.DataFrame([])
     nb_echantillons_retenus = 0

     # Boucle sur le tableau de configurations
     for x in inputDesign_df.itertuples():

        # Creation du code Urban Atlas
        code_ua = categories_ua_list[int(x.code_ua)]

        # Creation du dictionnaire de parametres
        values_dico = {'HRE':x.HRE, 'BSF':x.BSF, 'PSF':x.PSF, 'SVF':x.SVF, 'ISF':x.ISF, 'ARa':x.AR, 'TRC':x.TRC, 'OCS':x.OCS,'VEr':x.VEr,'VEa':x.VEa}

        # Application de l'arbre
        lcz_genere,lcz_historic = selectTree(code_ua, values_dico, inport_tree, correspondance_values_dico)

        # Si la configuration a genere un lcz admissible, on la sauvegarde
        if lcz_genere in types_lcz_list :

            nb_echantillons_retenus = nb_echantillons_retenus+1

            df_ligne_X = pd.DataFrame({'code_ua':x.code_ua,'HRE':x.HRE, 'BSF':x.BSF, 'PSF':x.PSF, 'SVF':x.SVF, 'ISF':x.ISF, 'ARa':x.AR, 'TRC':x.TRC, 'OCS':x.OCS,'VEr':x.VEr,'VEa':x.VEa},index=[str(nb_echantillons_retenus)],columns=['code_ua','HRE','BSF','PSF','SVF','ISF','ARa','TRC','OCS','VEr','VEa'])
            df_X_train_RF = df_X_train_RF.append(df_ligne_X)

            df_ligne_Y = pd.DataFrame({'lcz':types_lcz_list.index(lcz_genere)},index=[str(nb_echantillons_retenus)],columns=['lcz'])
            df_Y_train_RF = df_Y_train_RF.append(df_ligne_Y)


     # Determination du nombre d'echantillons finalement sauvegardes
     nb_samples = len(df_X_train_RF)

     if debug >= 2:
         print(cyan + "computeTreeRFmodel() : " + bold + green  + "Nombre d'echantillons retenus : " + str(nb_samples) + endC)

     # Creation du modele Random Forest
     forest = RandomForestClassifier(n_estimators=300, n_jobs=-1, criterion='gini', max_depth=None, min_samples_split=2, min_samples_leaf=1, max_features=5, max_leaf_nodes=None, bootstrap=True, oob_score=True)

     # Apprentissage du modele Random Forest
     modele_RF = forest.fit(df_X_train_RF,df_Y_train_RF)

     # Sauvegarde du model au format (.pkl)
     if model_file_rf != "" :
         joblib.dump(modele_RF, model_file_rf)

     if debug >= 2:
         print(cyan + "computeTreeRFmodel() : " + bold + green + "Score de classification du modele Random Forest sur les donnees d'apprentissage : " + str(modele_RF.oob_score_) + endC)

     return modele_RF

####################################################################################################
# FONCTION computeLCZbyRF()                                                                        #
####################################################################################################
# ROLE:
#     Calculer les LCZ par classification Randon Forest
#     et sauvegarder ces données dans le fichier vecteur de maillage Urban Atlas de sortie
#
# ENTREES DE LA FONCTION :
#     inport_tree : l'arbre de décision
#     lcz_output : fichier de maillage Urban Atlas en sortie, avec la valeur LCZ par maille
#     nb_sample_rf : nombre d'echantillons pour le Randon Forest
#     model_file_rf : nom du fichier contenant le model du Randon Forest
#     abbreviation_list : liste des abréviations utilisées
#     column_id_ua : nom de la colonne 'id' du fichier Urban Atlas en d'entree
#     column_code_ua : nom de la colonne 'code' du fichier Urban Atlas en d'entree
#     column_lcz_histo : nom de la colonne contenant la classe LCZ intermédiaire dans le fichier de sortie
#     column_lcz : nom de la colonne contenant la classe LCZ dans le fichier de sortie
#     column_lcz_rf : nom de la colonne contenant la classe LCZ par RandonForest dans le fichier de sortie
#     correspondance_values_dico : dictionaire de correspondance variable et valeur
#     path_time_log : fichier log de sortie
#     save_results_intermediate : fichiers de sorties intermédiaires nettoyés, par défaut = False
#     overwrite : écrase si un fichier existant a le même nom qu'un fichier de sortie, par défaut = True
#
# SORTIES DE LA FONCTION :
#     N.A.

def computeLCZbyRF(inport_tree, lcz_output, nb_sample_rf, model_file_rf, abbreviation_list, column_id_ua, column_code_ua, column_lcz_histo, column_lcz, column_lcz_rf, correspondance_values_dico, path_time_log, save_results_intermediate=False, overwrite=True):

    if debug >= 2:
        print(cyan + "computeLCZbyRF() : " + bold + green + "Début du calcul des LCZ par Randon Forest." + endC + "\n")
    timeLine(path_time_log, "Début du calcul des LCZ par RF : ")

    if debug >= 3:
        print(bold + green + "computeLCZbyRF() : Variables dans la fonction" + endC)
        print(cyan + "computeLCZbyRF() : " + endC + "lcz_output : " + str(lcz_output) + endC)
        print(cyan + "computeLCZbyRF() : " + endC + "nb_sample_rf : " + str(nb_sample_rf) + endC)
        print(cyan + "computeLCZbyRF() : " + endC + "model_file_rf : " + str(model_file_rf) + endC)
        print(cyan + "computeLCZbyRF() : " + endC + "abbreviation_list : " + str(abbreviation_list) + endC)
        print(cyan + "computeLCZbyRF() : " + endC + "column_id_ua : " + str(column_id_ua) + endC)
        print(cyan + "computeLCZbyRF() : " + endC + "column_code_ua : " + str(column_code_ua) + endC)
        print(cyan + "computeLCZbyRF() : " + endC + "column_lcz_histo : " + str(column_lcz_histo) + endC)
        print(cyan + "computeLCZbyRF() : " + endC + "column_lcz : " + str(column_lcz) + endC)
        print(cyan + "computeLCZbyRF() : " + endC + "column_lcz_rf : " + str(column_lcz_rf) + endC)
        print(cyan + "computeLCZbyRF() : " + endC + "correspondance_values_dico : " + str(correspondance_values_dico) + endC)
        print(cyan + "computeLCZbyRF() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "computeLCZbyRF() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "computeLCZbyRF() : " + endC + "overwrite : " + str(overwrite) + endC)

    # Les constantes
    SUFFIX_FILE_RF = '_RF'
    EXT_DBF_FILE  = ".dbf"

    TYPES_LCZ = ["1","2","3","4","5","6","7","8","9","10","A","B","C","D","E","F","G"]
    CATEGORIES_UA = [11100,11210,11220,11230,11240,11300,12100,12210,12220,12230,12300,12400,13100,13300,13400,14100,14200,21000,22000,23000,24000,25000,31000,32000,33000,40000,50000]

    # Creation du modele Random Forest pour completer l'arbre en cas d'indecision
    if os.path.exists(model_file_rf):
        tree_RF_model = joblib.load(model_file_rf)
    else :
        if debug >= 2:
            print(cyan + "computeLCZbyRF() : " + bold + green + "Calcul du model pour la classification par Random Forest pour les LCZ" + endC + "\n")
        tree_RF_model = computeTreeRFmodel(inport_tree, nb_sample_rf, model_file_rf, TYPES_LCZ, CATEGORIES_UA, correspondance_values_dico)

    # Conversion d'information du fichier shape d'entrée en fichier csv
    repertory_output = os.path.dirname(lcz_output)
    file_name = os.path.splitext(os.path.basename(lcz_output))[0]

    dbf_file = repertory_output + os.sep + file_name + EXT_DBF_FILE
    dbf_file_result = repertory_output + os.sep + file_name + SUFFIX_FILE_RF + EXT_DBF_FILE

    if debug >= 2:
        print(cyan + "computeLCZbyRF() : " + bold + green + "Lecture des données d'entree mergées du fichier vecteur : " + lcz_output + endC + "\n")

    # Lecture du fichier dbf avec pandas
    dbf_data = Dbf5(dbf_file)
    dataframe_input = dbf_data.to_dataframe()
    dataframe_result = pd.DataFrame([])
    columns_name_input_list =  list(dataframe_input.columns.values)
    columns_name_input_list.append(column_lcz_histo)
    columns_name_input_list.append(column_lcz)
    columns_name_input_list.append(column_lcz_rf)

    # Pour toute les données
    if debug >= 2:
        print(cyan + "computeLCZbyRF() : " + bold + green + "Execution de la classification LCZ par Random Forest" + endC + "\n")

    i = 0
    for x in dataframe_input.itertuples():
        # Recuperation des données pour une ligne
        hre = x.HRE
        bsf = x.BSF
        psf = x.PSF
        svf = x.SVF
        isf = x.ISF
        ara = x.ARa
        trc = x.TRC
        ocs = x.OCS
        bur = x.BUr
        ror = x.ROr
        war = x.WAr
        bsr = x.BSr
        ver = x.VEr
        vea = x.VEa
        vem = x.VEm

        code_ua = dataframe_input.iloc[i][column_code_ua.upper()]
        idx = dataframe_input.iloc[i][column_id_ua.upper()]

        # Recuperation de la partie de l'arbre qui nous interesse
        values_dico = {'HRE':hre, 'BSF':bsf, 'PSF':psf, 'SVF':svf, 'ISF':isf, 'ARa':ara, 'TRC':trc, 'OCS':ocs, 'BUr':bur,' ROr':ror, 'WAr':war, 'BSr':bsr, 'VEr':ver, 'VEa':vea, 'VEm':vem}
        lcz_final,lcz_initial = selectTree(code_ua, values_dico, inport_tree, correspondance_values_dico)

        # Calcul de la classification en RF
        code_ua_num = CATEGORIES_UA.index(int(code_ua))
        df_X_RF = pd.DataFrame({'code_ua':code_ua_num,'HRE':hre, 'BSF':bsf, 'PSF':psf, 'SVF':svf, 'ISF':isf, 'ARa':ara, 'TRC':trc, 'OCS':ocs, 'VEr':ver,'VEa':vea}, index=[idx])
        df_X_RF.columns = ['code_ua','HRE','BSF','PSF','SVF','ISF','ARa','TRC','OCS', 'VEr','VEa']

        prediction = tree_RF_model.predict(df_X_RF)
        prediction_df = pd.DataFrame(prediction,columns=[column_lcz_rf])
        prediction_list = prediction_df.values.tolist()
        lcz_rf = prediction_list[0][0]

        lcz_rf_final = TYPES_LCZ[lcz_rf]
        x_dict = x._asdict()
        x_dict.update({column_id_ua:idx, column_lcz_histo:lcz_initial, column_lcz:lcz_final, column_lcz_rf:lcz_rf_final})
        df_ligne = pd.DataFrame(x_dict, index=[idx])
        dataframe_result = pd.concat([dataframe_result, df_ligne], ignore_index=True, sort=True)
        i += 1

    # Creation du fichier final dbf
    if debug >= 2:
        print(cyan + "computeLCZbyRF() : " + bold + green + "Sauvegarde des donées en fichier (.dbf) : " + endC + "\n")
        print(columns_name_input_list)

    new_dataframe_result = dataframe_result[columns_name_input_list]
    saveDataFrame2Dbf(new_dataframe_result, dbf_file_result)
    removeFile(dbf_file)
    renameFile(dbf_file_result, dbf_file)

    # Suppression des fichiers intermédiaires
    if not save_results_intermediate :
        if debug >= 4:
            print(cyan + "computeLCZbyRF() : " + bold + green +  "Suppression des fichiers temporaires " + endC)

    if debug >= 2:
        print(cyan + "computeLCZbyRF() : " + bold + green + "Fin du calcul des LCZ par Randon Forest." + endC + "\n")
    timeLine(path_time_log, "Fin du calcul des LCZ par RF : ")

    return

#############################################################################################################################
################################################## Mise en place du parser ##################################################
#############################################################################################################################

def main(gui=False):
    parser = argparse.ArgumentParser(prog = "Cartographie LCZ (Local Climate Zones ou Zones Climatiques Locales)",
    description = "Attribution, pour chaque polygone d'un maillage, d'une classe de LCZ, a partir des indicateurs precedemment calcules. \n\
    Exemple : python /home/scgsi/Documents/ChaineTraitement/ScriptsLCZ/ClassificationLCZ.py \n\
                        -corres_dico var1:5 var2:14.2 var3:25 \n\
                        -i /home/scgsi/Documents/ChaineTraitement/ScriptsLCZ/ClassificationLCZ_settings.py \n\
                        -uai /mnt/Donnees_Etudes/10_Agents/Benjamin/LCZ/Nancy/UrbanAtlas_complete.shp \n\
                        -lcz /mnt/Donnees_Etudes/10_Agents/Benjamin/LCZ/Nancy/ClassificationLCZ.shp \n\
                        -bsf /mnt/Donnees_Etudes/10_Agents/Benjamin/LCZ/Nancy/BuildingSurfaceFraction.shp \n\
                        -isf /mnt/Donnees_Etudes/10_Agents/Benjamin/LCZ/Nancy/ImperviousSurfaceFraction.shp \n\
                        -psf /mnt/Donnees_Etudes/10_Agents/Benjamin/LCZ/Nancy/PerviousSurfaceFraction.shp \n\
                        -svf /mnt/Donnees_Etudes/10_Agents/Benjamin/LCZ/Nancy/SkyViewFactor.shp \n\
                        -hre /mnt/Donnees_Etudes/10_Agents/Benjamin/LCZ/Nancy/HeightOfRoughnessElements.shp \n\
                        -trc /mnt/Donnees_Etudes/10_Agents/Benjamin/LCZ/Nancy/TerrainRoughnessClass.shp \n\
                        -ara /mnt/Donnees_Etudes/10_Agents/Benjamin/LCZ/Nancy/AspectRatio.shp \n\
                        -ocs /mnt/Donnees_Etudes/10_Agents/Benjamin/LCZ/Nancy/SoilOccupation.shp",
    epilog = "Pour les parametres-listes -ind_lst, -col_lst, -abb_lst, s'assurer que les elements d'un meme indicateur sont a la meme position dans les 3 listes. \n\
    La modification de ces listes n'a lieu que lorsque un indicateur est ajoute/enleve a la liste de ceux utilises pour l'attribution des classes de LCZ. Les valeurs possibles au 19/01/2017 sont : \n\
        pour -ind_list : 'BuildingSurfaceFraction','ImperviousSurfaceFraction','PerviousSurfaceFraction','SkyViewFactor','HeightOfRoughnessElements','TerrainRoughnessClass','AspectRatio','SoilOccupation' \n\
        pour -col_list : 'Bati','Imperm','Perm','mean','MEAN_H','CL_RUGO','ASP_RATIO','class_OCS' \n\
        pour -abb_list : 'BSF','ISF','PSF','SVF','HRE','TRC','ARa','OCS'")

    parser.add_argument('-i','--file_tree_input',default="",help="File tree py input (python file .py).", type=str, required=True)
    parser.add_argument('-uai', '--urban_atlas_input', default="", type=str, required=True, help="Fichier de maillage Urban Atlas en entree (.shp).")
    parser.add_argument('-lcz', '--lcz_output', default="",type=str, required=True, help="Fichier de maillage Urban Atlas en sortie, avec la valeur LCZ par maille (.shp).")
    parser.add_argument('-bsf', '--building_surface_fraction_input', default="", type=str, required=False, help="Fichier Building Surface Fraction en entree (.shp).")
    parser.add_argument('-isf', '--impervious_surface_fraction_input', default="", type=str, required=False, help="Fichier Impervious Surface Fraction en entree (.shp).")
    parser.add_argument('-psf', '--pervious_surface_fraction_input', default="", type=str, required=False, help="Fichier Pervious Surface Fraction en entree (.shp).")
    parser.add_argument('-svf', '--sky_view_factor_input', default="", type=str, required=False, help="Fichier Sky View Factor en entree (.shp).")
    parser.add_argument('-hre', '--height_roughness_elements_input', default="", type=str, required=False, help="Fichier Height of Roughness Elements en entree (.shp).")
    parser.add_argument('-trc', '--terrain_roughness_class_input', default="", type=str, required=False, help="Fichier Terrain Roughness Class en entree (.shp).")
    parser.add_argument('-ara', '--aspect_ratio_input', default="", type=str, required=False, help="Fichier Aspect Ratio en entree (.shp).")
    parser.add_argument('-ocs', '--soil_occupation_input', default="", type=str, required=False, help="Fichier 'soil occupation' en entree (.shp).")
    parser.add_argument('-crf', '--used_randon_forest', action='store_true', default=False, help="Option : Used classification LCZ by classifier Randon Forest. By default : False", required=False)
    parser.add_argument('-nsrf', '--nb_sample_rf', default=100000, type=int, required=False, help="Number of sample to compute Random Forest model default : 100000")
    parser.add_argument('-mfrf', '--model_file_rf', default="",type=str, required=False, help="File name model Random Forest input or output (.pkl).")
    parser.add_argument('-ind_lst', '--indicator_list', nargs="+", default=['BuildingSurfaceFraction','ImperviousSurfaceFraction','PerviousSurfaceFraction','SkyViewFactor','HeightOfRoughnessElements','TerrainRoughnessClass','AspectRatio','SoilOccupation','BuiltRate','RoadRate','WaterRate','BareSoilRate','VegetationRate','AverageVegetationHeight','MaxVegetationHeight'], type=str, required=False, help="Liste des indicateurs utilises pour l'attribution des LCZ.")
    parser.add_argument('-col_lst', '--column_list', nargs="+", default=['Bati','Imperm','Perm','mean','MEAN_H','CL_RUGO','ASP_RATIO','class_OCS','Bati','Route','Eau','SolNu','Vegetation','H_moy_Veg','H_max_Veg'], type=str, required=False, help="Liste des colonnes contenant chacun des indicateurs precedents.")
    parser.add_argument('-abb_lst', '--abbreviation_list', nargs="+", default=['BSF','ISF','PSF','SVF','HRE','TRC','ARa','OCS','BUr','ROr','WAr','BSr','VEr','VEa','VEm'], type=str, required=False, help="Liste des abreviations utilisees.")
    parser.add_argument('-cid', '--column_id_ua', default="ID", type=str, required=False, help="Nom de la colonne 'id' du fichier Urban Atlas en entree.")
    parser.add_argument('-cco', '--column_code_ua', default="CODE201", type=str, required=False, help="Nom de la colonne 'code' du fichier Urban Atlas en entree.")
    parser.add_argument('-chis', '--column_lcz_histo', default="LCZ_HISTO", type=str, required=False, help="Nom de la colonne contenant la classe LCZ intermediaire dans le fichier de sortie.")
    parser.add_argument('-clcz', '--column_lcz', default="LCZ", type=str, required=False, help="Nom de la colonne contenant la classe LCZ dans le fichier de sortie.")
    parser.add_argument('-clczrf', '--column_lcz_rf', default="LCZ_RF", type=str, required=False, help="Nom de la colonne contenant la classe LCZ_RF dans le fichier de sortie.")
    parser.add_argument('-corres_dico','--correspondance_values_dico',default="",nargs="+",help="Dictionary of variable name and their values used in tree, (format : var1:5 var2:14.2 var3:25 ex.)", type=str, required=False)
    parser.add_argument('-vef','--format_vector',default="ESRI Shapefile",help="Option : Vector format. By default : ESRI Shapefile", type=str, required=False)
    parser.add_argument('-log', '--path_time_log', default="", type=str, required=False, help="Name of log")
    parser.add_argument('-sav', '--save_results_intermediate', action='store_true', default=False, required=False, help="Save or delete intermediate result after the process. By default, False")
    parser.add_argument('-now', '--overwrite', action='store_false', default=True, required=False, help="Overwrite files with same names. By default, True")
    parser.add_argument('-debug', '--debug', default=3, type=int, required=False, help="Option : Value of level debug trace, default : 3")
    args = displayIHM(gui, parser)

    # Récupération du fichier arbre d'entée
    if args.file_tree_input != None:
        file_tree_input=args.file_tree_input

    # Récupération du vecteur Urban Atlas en entrée
    if args.urban_atlas_input != None:
        urban_atlas_input = args.urban_atlas_input

    # Récupération du vecteur LCZ en sortie
    if args.lcz_output != None:
        lcz_output = args.lcz_output

    # Récupération d'utilisation du RF
    if args.used_randon_forest != None:
        used_randon_forest = args.used_randon_forest
    if args.nb_sample_rf != None:
        nb_sample_rf = args.nb_sample_rf
    if args.model_file_rf != None:
        model_file_rf = args.model_file_rf

    # Récupération du vecteur Building Surface Fraction en entrée
    if args.building_surface_fraction_input != None:
        building_surface_fraction_input = args.building_surface_fraction_input

    # Récupération du vecteur Impervious Surface Fraction en entrée
    if args.impervious_surface_fraction_input != None:
        impervious_surface_fraction_input = args.impervious_surface_fraction_input

    # Récupération du vecteur Pervious Surface Fraction en entrée
    if args.pervious_surface_fraction_input != None:
        pervious_surface_fraction_input = args.pervious_surface_fraction_input

    # Récupération du vecteur Sky View Factor en entrée
    if args.sky_view_factor_input != None:
        sky_view_factor_input = args.sky_view_factor_input

    # Récupération du vecteur Height of Roughness Elements en entrée
    if args.height_roughness_elements_input != None:
        height_roughness_elements_input = args.height_roughness_elements_input

    # Récupération du vecteur Terrain Roughness Class en entrée
    if args.terrain_roughness_class_input != None:
        terrain_roughness_class_input = args.terrain_roughness_class_input

    # Récupération du vecteur Aspect Ratio en entrée
    if args.aspect_ratio_input != None:
        aspect_ratio_input = args.aspect_ratio_input

    # Récupération du vecteur 'soil occupation' en entrée
    if args.soil_occupation_input != None:
        soil_occupation_input = args.soil_occupation_input

    # Récupération de la liste des indicateurs
    if args.indicator_list != None:
        indicator_list = args.indicator_list

    # Récupération de la liste des colonnes
    if args.column_list != None:
        column_list = args.column_list

    # Récupération de la liste des abréviations
    if args.abbreviation_list != None:
        abbreviation_list = args.abbreviation_list

    # Récupération des noms des colonnes de l'Urban Atlas
    if args.column_code_ua != None:
        column_code_ua = args.column_code_ua
    if args.column_id_ua != None:
        column_id_ua = args.column_id_ua

    # Récupération du nom des colonnes du fichier LCZ de sortie
    if args.column_lcz_histo != None:
        column_lcz_histo = args.column_lcz_histo
    if args.column_lcz != None:
        column_lcz = args.column_lcz
    if args.column_lcz_rf != None:
        column_lcz_rf = args.column_lcz_rf

    # Récupération du dictionnaire des valeurs en variable de l'arbre
    if args.correspondance_values_dico != None and args.correspondance_values_dico != "":
        correspondance_values_dico = extractDico(args.correspondance_values_dico)
    else :
        correspondance_values_dico = {}

    # Récupération du nom du format des fichiers vecteur
    if args.format_vector != None:
        format_vector = args.format_vector

    # Récupération du nom du fichier log
    if args.path_time_log != None:
        path_time_log = args.path_time_log

    # Récupération de l'option de sauvegarde des fichiers intermédiaires
    if args.save_results_intermediate != None:
        save_results_intermediate = args.save_results_intermediate

    # Récupération de l'option écrasement
    if args.overwrite != None:
        overwrite = args.overwrite

    # Récupération de l'option niveau de debug
    if args.debug != None:
        global debug
        debug = args.debug

    if debug >= 3:
        print(bold + green + "Classification des Zones Climatiques Locales (LCZ) :" + endC)
        print(cyan + "ClassificationLCZ : " + endC + "file_tree_input : " + str(file_tree_input) + endC)
        print(cyan + "ClassificationLCZ : " + endC + "urban_atlas_input : " + str(urban_atlas_input) + endC)
        print(cyan + "ClassificationLCZ : " + endC + "lcz_output : " + str(lcz_output) + endC)
        print(cyan + "ClassificationLCZ : " + endC + "used_randon_forest: " + str(used_randon_forest) + endC)
        print(cyan + "ClassificationLCZ : " + endC + "nb_sample_rf : " + str(nb_sample_rf) + endC)
        print(cyan + "ClassificationLCZ : " + endC + "model_file_rf : " + str(model_file_rf) + endC)
        print(cyan + "ClassificationLCZ : " + endC + "building_surface_fraction_input : " + str(building_surface_fraction_input) + endC)
        print(cyan + "ClassificationLCZ : " + endC + "impervious_surface_fraction_input : " + str(impervious_surface_fraction_input) + endC)
        print(cyan + "ClassificationLCZ : " + endC + "pervious_surface_fraction_input : " + str(pervious_surface_fraction_input) + endC)
        print(cyan + "ClassificationLCZ : " + endC + "sky_view_factor_input : " + str(sky_view_factor_input) + endC)
        print(cyan + "ClassificationLCZ : " + endC + "height_roughness_elements_input : " + str(height_roughness_elements_input) + endC)
        print(cyan + "ClassificationLCZ : " + endC + "terrain_roughness_class_input : " + str(terrain_roughness_class_input) + endC)
        print(cyan + "ClassificationLCZ : " + endC + "aspect_ratio_input : " + str(aspect_ratio_input) + endC)
        print(cyan + "ClassificationLCZ : " + endC + "soil_occupation_input : " + str(soil_occupation_input) + endC)
        print(cyan + "ClassificationLCZ : " + endC + "indicator_list : " + str(indicator_list) + endC)
        print(cyan + "ClassificationLCZ : " + endC + "column_list : " + str(column_list) + endC)
        print(cyan + "ClassificationLCZ : " + endC + "abbreviation_list : " + str(abbreviation_list) + endC)
        print(cyan + "ClassificationLCZ : " + endC + "column_id_ua : " + str(column_id_ua) + endC)
        print(cyan + "ClassificationLCZ : " + endC + "column_code_ua : " + str(column_code_ua) + endC)
        print(cyan + "ClassificationLCZ : " + endC + "column_lcz_histo : " + str(column_lcz_histo) + endC)
        print(cyan + "ClassificationLCZ : " + endC + "column_lcz : " + str(column_lcz) + endC)
        print(cyan + "ClassificationLCZ : " + endC + "column_lcz_rf : " + str(column_lcz_rf) + endC)
        print(cyan + "ClassificationLCZ : " + endC + "correspondance_values_dico : " + str(correspondance_values_dico) + endC)
        print(cyan + "ClassificationLCZ : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "ClassificationLCZ : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "ClassificationLCZ : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "ClassificationLCZ : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "ClassificationLCZ : " + endC + "debug : " + str(debug) + endC)

    if not os.path.exists(os.path.dirname(lcz_output)):
        os.makedirs(os.path.dirname(lcz_output))

    # Importer le fichier python contenant l'arbre
    path_import_file = os.path.dirname(file_tree_input)
    import_file = os.path.splitext(os.path.basename(file_tree_input))[0]
    sys.path.append(path_import_file)
    new_inport_tree = __import__(import_file)

    # Fusion les données attributaires
    stackShapeLCZ(urban_atlas_input, lcz_output, building_surface_fraction_input, impervious_surface_fraction_input, pervious_surface_fraction_input, sky_view_factor_input, height_roughness_elements_input, terrain_roughness_class_input, aspect_ratio_input, soil_occupation_input, indicator_list, column_list, abbreviation_list, column_id_ua, path_time_log, format_vector, save_results_intermediate, overwrite)

    # Calcul des LCZ pour l'arbre
    if used_randon_forest :
        computeLCZbyRF(new_inport_tree, lcz_output, nb_sample_rf, model_file_rf, abbreviation_list, column_id_ua, column_code_ua, column_lcz_histo, column_lcz, column_lcz_rf, correspondance_values_dico, path_time_log, save_results_intermediate, overwrite)
    else :
        computeLCZ(new_inport_tree, lcz_output, abbreviation_list, column_id_ua, column_code_ua, column_lcz_histo, column_lcz, correspondance_values_dico, path_time_log, format_vector, save_results_intermediate, overwrite)

if __name__ == '__main__':
    main(gui=False)
