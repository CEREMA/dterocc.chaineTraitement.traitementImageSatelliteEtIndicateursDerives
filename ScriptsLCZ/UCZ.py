#!/usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

from __future__ import print_function
import os,sys
import six
from Lib_text import appendTextFile
from Lib_file import removeVectorFile
from PreparationDonnees import *
from PreparationIndicateurs import *
from TraitementsFinauxSGBD import *
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 3

FORMAT_RASTER = 'GTiff'
FORMAT_VECTOR = 'ESRI Shapefile'
EXTENSION_RASTER = '.tif'
EXTENSION_VECTOR = '.shp'

classification = True
while classification:

    parametrage = True
    while parametrage:

    ##################################################################################################################################
    ################################################## Mise en place des paramètres ##################################################
    ##################################################################################################################################

        ############################################
        ### Nom du fichier Urban Atlas en entrée ###
        ############################################

        urbanatlas_input = input(bold + blue + "Nom du fichier Urban Atlas en entrée (exemple : /home/scgsi/Bureau/UrbanAtlas.shp) :" + endC + " ")
        while not os.path.exists(urbanatlas_input):
            print(bold + red + "Erreur : le fichier Urban Atlas ne peut être trouvé à cet emplacement." + endC, file=sys.stderr)
            urbanatlas_input = input(bold + blue + "Nom du fichier Urban Atlas en entrée (exemple : /home/scgsi/Bureau/UrbanAtlas.shp) :" + endC + " ")
        print("\n")

        ############################################
        ### Nom du fichier classif UCZ en sortie ###
        ############################################

        ucz_output = input(bold + blue + "Nom du fichier classif UCZ en sortie (exemple : /home/scgsi/Bureau/CartoUCZ.shp) :" + endC + " ")
        while ucz_output == "" or os.path.splitext(ucz_output)[1] != EXTENSION_VECTOR:
            print(bold + red + "Erreur : veuillez bien renseigner le fichier classif UCZ en sortie." + endC, file=sys.stderr)
            ucz_output = input(bold + blue + "Nom du fichier classif UCZ en sortie (exemple : /home/scgsi/Bureau/CartoUCZ.shp) :" + endC + " ")
        print("\n")

        ###################################################
        ### Nom du fichier d'emprise de la zone d'étude ###
        ###################################################

        emprise_file = input(bold + blue + "Nom du fichier d'emprise de la zone d'étude (exemple : /home/scgsi/Bureau/ZoneEtude.shp) :" + endC + " ")
        while not os.path.exists(emprise_file):
            print(bold + red + "Erreur : le fichier d'emprise ne peut être trouvé à cet emplacement." + endC, file=sys.stderr)
            emprise_file = input(bold + blue + "Nom du fichier d'emprise de la zone d'étude (exemple : /home/scgsi/Bureau/ZoneEtude.shp) :" + endC + " ")
        print("\n")

        #####################################################
        ### Choix de la méthode de calcul des indicateurs ###
        #####################################################

        print(bold + blue + "Quelle méthode utiliser pour le calcul des indicateurs ? (1/2/3/4)" + endC)
        print("    1 = Projet étudiant - BD exogènes")
        print("    2 = SI par méthode de seuillage")
        print("    3 = SI par méthode de classification")
        print("    4 = Résultats issus d'une classification")
        print(bold + "Méthode de calcul des indicateurs par défaut : " + endC + methi)
        print(italic + yellow + "'help' pour avoir plus d'informations sur les différentes méthodes." + endC)
        methi = input(bold + blue + "Modifier le choix de la méthode (appuyer sur 'Entrée' pour laisser par défaut) :" + endC + " ")

        while methi not in ("1","2","3","4"):
            if methi == "":
                methi = "1"
            elif methi == "help":
                print(bold + "Projet étudiant - BD exogènes (1) :" + endC)
                print("    Imperméabilité = masques NDVI (végétation) + RPG (sol nu) + BD TOPO® hydrographie (eau)")
                print("    Rapport d'aspect = à partir de la BD TOPO® bâti")
                print("    Rugosité = à partir de la BD TOPO® bâti")
                print(bold + "SI par méthode de seuillage (2) :" + endC)
                print("    Imperméabilité = obtenue par seuillage d'indices radiométriques (NDVI, NDWI, BI)")
                print("    Rapport d'aspect = à partir de la BD TOPO® bâti")
                print("    Rugosité = à partir de la BD TOPO® bâti")
                print(bold + "SI par méthode de classification (3) :" + endC)
                print("    Imperméabilité = obtenues par classification supervisée")
                print("    Rapport d'aspect = à partir de la BD TOPO® bâti")
                print("    Rugosité = à partir de la BD TOPO® bâti")
                print(bold + "Résultats issus d'une classification (4) :" + endC)
                print("    Imperméabilité = obtenue par classification supervisée")
                print("    Rapport d'aspect = bâti obtenue par classification supervisée")
                print("    Rugosité = bâti obtenue par classification supervisée")
                print(italic + yellow + "Pour des informations plus détaillées, se reporter au tutoriel d'utilisation de la chaine de traitement UCZ." + endC)
                methi = input(bold + blue + "Quelle méthode utiliser pour le calcul des indicateurs ? (1/2/3/4) :" + endC + " ")
            else:
                print(bold + yellow + "Attention : veuillez sélectionner un chiffre (1/2/3/4)." + endC)
                methi = input(bold + blue + "Quelle méthode utiliser pour le calcul des indicateurs ? (1/2/3/4) :" + endC + " ")

        if methi == "1":
            indicators_method = "BD_exogenes"
        elif methi == "2":
            indicators_method = "SI_seuillage"
        elif methi == "3":
            indicators_method = "SI_classif"
        else:
            indicators_method = "Resultats_classif"
        print("\n")

        #############################################
        ### Choix de la méthode de calcul des UCZ ###
        #############################################

        print(bold + blue + "Quelle méthode utiliser pour le calcul des UCZ ? (1/2/3/4)" + endC)
        print("    1 = Méthode combinatoire sans l'indicateur de classe de rugosité")
        print("    2 = Méthode combinatoire avec l'indicateur de classe de rugosité")
        print("    3 = Méthode hiérarchique sans l'indicateur de classe de rugosité")
        print("    4 = Méthode hiérarchique avec l'indicateur de classe de rugosité")
        print(bold + "Méthode de calcul des UCZ par défaut : " + endC + methu)
        print(italic + green + "'help' pour avoir plus d'informations sur les différentes méthodes." + endC)
        methu = input(bold + blue + "Modifier le choix de la méthode (appuyer sur 'Entrée' pour laisser par défaut) :" + endC + " ")

        while methu not in ("1","2","3","4"):
            if methu == "":
                methu = "4"
            elif methu == "help":
                print(bold + "Méthode combinatoire sans l'indicateur de classe de rugosité (1) :" + endC)
                print("    SI et RA sont utilisés en même temps (requêtes SQL de type AND) pour établir les classes d'UCZ")
                print(bold + "Méthode combinatoire avec l'indicateur de classe de rugosité (2) :" + endC)
                print("    Les 3 indicateurs sont utilisés en même temps (requêtes SQL de type AND) pour établir les classes d'UCZ")
                print(bold + "Méthode hiérarchique sans l'indicateur de classe de rugosité (3) :" + endC)
                print("    Utilisation du SI pour discriminer les UCZ 5/6/7, puis du RA pour discriminer les UCZ 1/2/3/4")
                print(bold + "Méthode hiérarchique avec l'indicateur de classe de rugosité (4) :" + endC)
                print("    Utilisation du SI pour discriminer les UCZ 5/6/7, puis du RA pour discriminer les UCZ 1/2/3/4 + post-traitements avec la rugosité sur les UCZ 5/6")
                print(italic + green + "Pour des informations plus détaillées, se reporter au tutoriel d'utilisation de la chaine de traitement UCZ." + endC)
                methu = input(bold + blue + "Quelle méthode utiliser pour le calcul des UCZ ? (1/2/3/4) :" + endC + " ")
            else:
                print(bold + yellow + "Attention : veuillez sélectionner un chiffre (1/2/3/4)." + endC)
                methu = input(bold + blue + "Quelle méthode utiliser pour le calcul des UCZ ? (1/2/3/4) :" + endC + " ")

        if methu == "1":
            ucz_method = "Combinaison_sans_rugosite"
        elif methu == "2":
            ucz_method = "Combinaison_avec_rugosite"
        elif methu == "3":
            ucz_method = "Hierarchie_sans_rugosite"
        else:
            ucz_method = "Hierarchie_avec_rugosite"
        print("\n")

        #############################################################
        ### Choix du système de gestion de base de données (SGBD) ###
        #############################################################

        dbms_choice = input(bold + blue + "Quel SGBD utiliser pour les traitements ? (SpatiaLite/PostGIS) :" + endC + " ")
        while dbms_choice not in ("SpatiaLite","PostGIS"):
            print(italic + yellow + "Attention : veuillez faire un choix entre SpatiaLite et PostGIS." + endC)
            dbms_choice = input(bold + blue + "Quel SGBD utiliser pour les traitements ? (SpatiaLite/PostGIS) :" + endC + " ")
        print("\n")

        ############################################################
        ### Noms des fichiers raster nécessaires aux traitements ###
        ############################################################

        enter_with_mask = False
        mask_file = ""
        image_file = ""
        mnh_file = ""

        if indicators_method == "BD_exogenes":

            enter_with_mask = input(bold + blue + "Entrer dans la chaîne avec un masque binaire de la végétation déjà prêt ? (Y/N) :" + endC + " ")
            while enter_with_mask not in ("Y","N"):
                print(italic + yellow + "Attention : veuillez répondre par Y ou N." + endC)
                enter_with_mask = input(bold + blue + "Entrer dans la chaîne avec un masque binaire de la végétation déjà prêt ? (Y/N) :" + endC + " ")
            print("\n")

            if enter_with_mask == "Y":

                enter_with_mask = True
                mask_file = input(bold + blue + "Masque binaire de la végétation à traiter (exemple : /home/scgsi/Bureau/masque_veg.tif) :" + endC + " ")
                while not os.path.exists(mask_file):
                    print(bold + yellow + "Attention : le fichier raster ne peut être trouvé à cet emplacement." + endC)
                    mask_file = input(bold + blue + "Masque binaire de la végétation à traiter (exemple : /home/scgsi/Bureau/masque_veg.tif) :" + endC + " ")
                print("\n")

            else:

                enter_with_mask = False

        if (indicators_method == "BD_exogenes" and enter_with_mask == False) or indicators_method == "SI_seuillage":

            image_file = input(bold + blue + "Image satellite à traiter (exemple : /home/scgsi/Bureau/Pleiades.tif) :" + endC + " ")
            while not os.path.exists(image_file):
                print(bold + yellow + "Attention : le fichier raster ne peut être trouvé à cet emplacement." + endC)
                image_file = input(bold + blue + "Image satellite à traiter (exemple : /home/scgsi/Bureau/Pleiades.tif) :" + endC + " ")
            print("\n")

        elif indicators_method == "SI_classif" or indicators_method == "Resultats_classif":

            image_file = input(bold + blue + "Résultat de classification OCS à traiter (exemple : /home/scgsi/Bureau/classif_OCS_Pleiades.tif) :" + endC + " ")
            while not os.path.exists(image_file):
                print(bold + yellow + "Attention : le fichier raster ne peut être trouvé à cet emplacement." + endC)
                image_file = input(bold + blue + "Résultat de classification OCS à traiter (exemple : /home/scgsi/Bureau/classif_OCS_Pleiades.tif) :" + endC + " ")
            print("\n")

            if indicators_method == "Resultats_classif":

                mnh_file = input(bold + blue + "Modèle Numérique de Hauteur à traiter (exemple : /home/scgsi/Bureau/MNH_Pleiades.tif) :" + endC + " ")
                while not os.path.exists(mnh_file):
                    print(bold + yellow + "Attention : le fichier raster ne peut être trouvé à cet emplacement." + endC)
                    mnh_file = input(bold + blue + "Modèle Numérique de Hauteur à traiter (exemple : /home/scgsi/Bureau/MNH_Pleiades.tif) :" + endC + " ")
                print("\n")

        #############################################################
        ### Noms des fichiers vecteur nécessaires aux traitements ###
        #############################################################

        built_files_list = []
        hydrography_file = ""
        roads_files_list = []
        rpg_file = ""

        if indicators_method == "BD_exogenes" or indicators_method == "SI_seuillage" or indicators_method == "SI_classif":

            bati_files_list = []

            # Bâti indifférencié
            bati_file = input(bold + blue + "Fichier bati indifférencié de la BD TOPO à traiter (exemple : /home/scgsi/Bureau/bati_indifferencie.shp) :" + endC + " ")
            while not os.path.exists(bati_file):
                print(bold + yellow + "Attention : le fichier vecteur ne peut être trouvé à cet emplacement." + endC)
                bati_file = input(bold + blue + "Fichier bati indifférencié de la BD TOPO à traiter (exemple : /home/scgsi/Bureau/bati_indifferencie.shp) :" + endC + " ")
            bati_files_list.append(bati_file)

            # Bâti industriel
            bati_file = input(bold + blue + "Fichier bati industriel de la BD TOPO à traiter (exemple : /home/scgsi/Bureau/bati_industriel.shp) :" + endC + " ")
            while not os.path.exists(bati_file):
                print(bold + yellow + "Attention : le fichier vecteur ne peut être trouvé à cet emplacement." + endC)
                bati_file = input(bold + blue + "Fichier bati industriel de la BD TOPO à traiter (exemple : /home/scgsi/Bureau/bati_industriel.shp) :" + endC + " ")
            bati_files_list.append(bati_file)

            # Bâti remarquable
            bati_file = input(bold + blue + "Fichier bati remarquable de la BD TOPO à traiter (exemple : /home/scgsi/Bureau/bati_remarquable.shp) :" + endC + " ")
            while not os.path.exists(bati_file):
                print(bold + yellow + "Attention : le fichier vecteur ne peut être trouvé à cet emplacement." + endC)
                bati_file = input(bold + blue + "Fichier bati remarquable de la BD TOPO à traiter (exemple : /home/scgsi/Bureau/bati_remarquable.shp) :" + endC + " ")
            bati_files_list.append(bati_file)

            # Bâti constructions légères
            bati_file = input(bold + blue + "Fichier bati constructions légères de la BD TOPO à traiter (exemple : /home/scgsi/Bureau/bati_constructions_legeres.shp) :" + endC + " ")
            while not os.path.exists(bati_file):
                print(bold + yellow + "Attention : le fichier vecteur ne peut être trouvé à cet emplacement." + endC)
                bati_file = input(bold + blue + "Fichier bati constructions légères de la BD TOPO à traiter (exemple : /home/scgsi/Bureau/bati_constructions_legeres.shp) :" + endC + " ")
            bati_files_list.append(bati_file)

            # Bâti réservoirs
            bati_file = input(bold + blue + "Fichier bati réservoirs de la BD TOPO à traiter (exemple : /home/scgsi/Bureau/bati_reservoirs.shp) :" + endC + " ")
            while not os.path.exists(bati_file):
                print(bold + yellow + "Attention : le fichier vecteur ne peut être trouvé à cet emplacement." + endC)
                bati_file = input(bold + blue + "Fichier bati réservoirs de la BD TOPO à traiter (exemple : /home/scgsi/Bureau/bati_reservoirs.shp) :" + endC + " ")
            bati_files_list.append(bati_file)
            print("\n")

            if indicators_method == "BD_exogenes" :

                hydrography_file = input(bold + blue + "Fichier hydrographie de la BD TOPO à traiter (exemple : /home/scgsi/Bureau/hydro.shp) :" + endC + " ")
                while not os.path.exists(hydrography_file):
                    print(bold + yellow + "Attention : le fichier vecteur ne peut être trouvé à cet emplacement." + endC)
                    hydrography_file = input(bold + blue + "Fichier hydrographie de la BD TOPO à traiter (exemple : /home/scgsi/Bureau/hydro.shp) :" + endC + " ")
                print("\n")

                rpg_file = input(bold + blue + "Fichier RPG à traiter (exemple : /home/scgsi/Bureau/RPG.shp) :" + endC + " ")
                while not os.path.exists(rpg_file):
                    print(bold + yellow + "Attention : le fichier vecteur ne peut être trouvé à cet emplacement." + endC)
                    rpg_file = input(bold + blue + "Fichier RPG à traiter (exemple : /home/scgsi/Bureau/RPG.shp) :" + endC + " ")
                print("\n")

            elif indicators_method == "SI_seuillage":

                roads_files_list = []

                # Tronçons routes
                roads_file = input(bold + blue + "Fichier tronçons route de la BD TOPO à traiter (exemple : /home/scgsi/Bureau/troncon_route.shp) :" + endC + " ")
                while not os.path.exists(roads_file):
                    print(bold + yellow + "Attention : le fichier vecteur ne peut être trouvé à cet emplacement." + endC)
                    roads_file = input(bold + blue + "Fichier tronçons route de la BD TOPO à traiter (exemple : /home/scgsi/Bureau/troncon_route.shp) :" + endC + " ")
                roads_files_list.append(roads_file)

                # Surfaces routes
                roads_file = input(bold + blue + "Fichier surfaces route de la BD TOPO à traiter (exemple : /home/scgsi/Bureau/surface_route.shp) :" + endC + " ")
                while not os.path.exists(roads_file):
                    print(bold + yellow + "Attention : le fichier vecteur ne peut être trouvé à cet emplacement." + endC)
                    roads_file = input(bold + blue + "Fichier surfaces route de la BD TOPO à traiter (exemple : /home/scgsi/Bureau/surface_route.shp) :" + endC + " ")
                roads_files_list.append(roads_file)
                print("\n")

        ##############################################################
        ### Choix des seuils pour la cartographie d'imperméabilité ###
        ##############################################################

        threshold_ndvi = []
        threshold_ndvi_water = []
        threshold_ndwi2 = []
        threshold_bi_bottom = []
        threshold_bi_top = []

        if not enter_with_mask:

            if indicators_method == "BD_exogenes" or indicators_method == "SI_seuillage":

                test_threshold_ndvi = True
                threshold_ndvi = input(bold + blue + "Choix du seuil de NDVI pour l'extraction de la végétation :" + endC + " ")
                while test_threshold_ndvi:
                    try:
                        threshold_ndvi = float(threshold_ndvi)
                        test_threshold_ndvi = False
                    except ValueError:
                        print(bold + yellow + "Attention : le paramètre n'est pas valide, entrez un nombre (séparateur décimal '.')." + endC)
                        threshold_ndvi = input(bold + blue + "Choix du seuil de NDVI pour l'extraction de la végétation :" + endC + " ")

                if indicators_method == "SI_seuillage":

                    test_threshold_ndvi_water = True
                    threshold_ndvi_water = input(bold + blue + "Choix du seuil de NDVI pour l'extraction de l'eau :" + endC + " ")
                    while test_threshold_ndvi_water:
                        try:
                            threshold_ndvi_water = float(threshold_ndvi_water)
                            test_threshold_ndvi_water = False
                        except ValueError:
                            print(bold + yellow + "Attention : le paramètre n'est pas valide, entrez un nombre (séparateur décimal '.')." + endC)
                            threshold_ndvi_water = input(bold + blue + "Choix du seuil de NDVI pour l'extraction de l'eau :" + endC + " ")

                    test_threshold_ndwi2 = True
                    threshold_ndwi2 = input(bold + blue + "Choix du seuil de NDWI2 pour l'extraction de l'eau :" + endC + " ")
                    while test_threshold_ndwi2:
                        try:
                            threshold_ndwi2 = float(threshold_ndwi2)
                            test_threshold_ndwi2 = False
                        except ValueError:
                            print(bold + yellow + "Attention : le paramètre n'est pas valide, entrez un nombre (séparateur décimal '.')." + endC)
                            threshold_ndwi2 = input(bold + blue + "Choix du seuil de NDWI2 pour l'extraction de l'eau :" + endC + " ")

                    test_threshold_bi_bottom = True
                    threshold_bi_bottom = input(bold + blue + "Choix du seuil inférieur du BI pour l'extraction du sol nu :" + endC + " ")
                    while test_threshold_bi_bottom:
                        try:
                            threshold_bi_bottom = float(threshold_bi_bottom)
                            test_threshold_bi_bottom = False
                        except ValueError:
                            print(bold + yellow + "Attention : le paramètre n'est pas valide, entrez un nombre (séparateur décimal '.')." + endC)
                            threshold_bi_bottom = input(bold + blue + "Choix du seuil inférieur du BI pour l'extraction du sol nu :" + endC + " ")

                    test_threshold_bi_top = True
                    threshold_bi_top = input(bold + blue + "Choix du seuil supérieur du BI pour l'extraction du sol nu :" + endC + " ")
                    while test_threshold_bi_top:
                        try:
                            threshold_bi_top = float(threshold_bi_top)
                            test_threshold_bi_top = False
                        except ValueError:
                            print(bold + yellow + "Attention : le paramètre n'est pas valide, entrez un nombre (séparateur décimal '.')." + endC)
                            threshold_bi_top = input(bold + blue + "Choix du seuil supérieur du BI pour l'extraction du sol nu :" + endC + " ")

                print("\n")

        ###################################
        ### Confirmation des paramètres ###
        ###################################

        print(underline + "Nom du fichier Urban Atlas en entrée :" + endC + " " + green + str(urbanatlas_input) + endC)
        print(underline + "Nom du fichier classif UCZ en sortie :" + endC + " " + green + str(ucz_output) + endC)
        print(underline + "Fichier d'emprise de la zone d'étude :" + endC + " " + green + str(emprise_file) + endC)

        if indicators_method == "BD_exogenes" or indicators_method == "SI_seuillage":
            if enter_with_mask:
                print(underline + "Masque binaire de la végétation :" + endC + " " + green + str(mask_file) + endC)
            else:
                print(underline + "Image satellite :" + endC + " " + green + str(image_file) + endC)
        elif indicators_method == "SI_classif" or indicators_method == "Resultats_classif":
            print(underline + "Résultat de classification OCS :" + endC + " " + green + str(image_file) + endC)
            if indicators_method == "Resultats_classif":
                print(underline + "Modèle Numérique de Hauteur :" + endC + " " + green + str(mnh_file) + endC)

        if indicators_method in ("BD_exogenes", "SI_seuillage", "SI_classif"):
            print(underline + "Fichiers bâti de la BD TOPO :" + endC + " " + green + str(built_files_list) + endC)
            if indicators_method == "BD_exogenes":
                print(underline + "Fichier hydrographie de la BD TOPO :" + endC + " " + green + str(hydrography_file) + endC)
                print(underline + "Fichier RPG :" + endC + " " + green + str(rpg_file) + endC)
            elif indicators_method == "SI_seuillage":
                print(underline + "Fichiers route de la BD TOPO :" + endC + " " + green + str(roads_files_list) + endC)

        print(underline + "Méthode de calcul des indicateurs :" + endC + " " + green + str(indicators_method) + endC)
        print(underline + "Méthode de calcul des UCZ :" + endC + " " + green + str(ucz_method) + endC)
        print(underline + "Système de gestion de base de données (SGBD) :" + endC + " " + green + str(dbms_choice) + endC)

        if not enter_with_mask and (indicators_method == "BD_exogenes" or indicators_method == "SI_seuillage"):
            print(underline + "Seuil de NDVI pour l'extraction de la végétation :" + endC + " " + green + str(threshold_ndvi) + endC)
            if indicators_method == "SI_seuillage":
                print(underline + "Seuil de NDVI pour l'extraction de l'eau :" + endC + " " + green + str(threshold_ndvi_water) + endC)
                print(underline + "Seuil de NDWI2 pour l'extraction de l'eau :" + endC + " " + green + str(threshold_ndwi2) + endC)
                print(underline + "Seuil inférieur du BI pour l'extraction du sol nu :" + endC + " " + green + str(threshold_bi_bottom) + endC)
                print(underline + "Seuil supérieur du BI pour l'extraction du sol nu :" + endC + " " + green + str(threshold_bi_top) + endC)

        print("\n")

        confirmation = input(bold + blue + "Confirmer ces paramètres ? (Y/N) :" + endC + " ")
        while confirmation not in ("Y","N"):
            print(bold + yellow + "Attention : veuillez répondre par Y ou N." + endC)
            confirmation = input(bold + blue + "Confirmer ces paramètres ? (Y/N) :" + endC + " ")
        if confirmation == "Y":
            parametrage = False
        print("\n")

        #########################
        ### Paramètres divers ###
        #########################

        # Emplacement du fichier log
        path_time_log = os.path.dirname(ucz_output) + os.sep + "log.txt"

        # Sauvegarde des fichiers intermédiaires
        save_results_intermediate = True

        # Ecrasement des fichiers déjà existants
        overwrite = False

        # Niveau de debug
        debug = 3

    ##################################################################################################################################################################
    ################################################## Lancement de la classification en Zones Climatiques Urbaines ##################################################
    ##################################################################################################################################################################

    if not os.path.exists(ucz_output) or overwrite:
        print(green + "Début de la classification en Zones Climatiques Urbaines :" + endC)

        print(bold + "    Nom du fichier Urban Atlas en entrée : " + endC + str(urbanatlas_input))
        print(bold + "    Nom du fichier classif UCZ en sortie : " + endC + str(ucz_output))
        print(bold + "    Fichier d'emprise de la zone d'étude : " + endC + str(emprise_file))

        if indicators_method == "BD_exogenes" or indicators_method == "SI_seuillage":
            if enter_with_mask:
                print(bold + "    Masque binaire de la végétation : " + endC + str(mask_file))
            else:
                print(bold + "    Image satellite : " + endC + str(image_file))
        elif indicators_method == "SI_classif" or indicators_method == "Resultats_classif":
            print(bold + "    Résultat de classification OCS : " + endC + str(image_file))
            if indicators_method == "Resultats_classif":
                print(bold + "    Modèle Numérique de Hauteur : " + endC + str(mnh_file))

        if indicators_method in ("BD_exogenes", "SI_seuillage", "SI_classif"):
            print(bold + "    Fichiers bâti de la BD TOPO : " + endC + str(built_files_list))
            if indicators_method == "BD_exogenes":
                print(bold + "    Fichier hydrographie de la BD TOPO : " + endC + str(hydrography_file))
                print(bold + "    Fichier RPG : " + endC + str(rpg_file))
            elif indicators_method == "SI_seuillage":
                print(bold + "    Fichiers route de la BD TOPO : " + endC + str(roads_files_list))

        print(bold + "    Méthode de calcul des indicateurs : " + endC + str(indicators_method))
        print(bold + "    Méthode de calcul des UCZ : " + endC + str(ucz_method))
        print(bold + "    Système de gestion de base de données (SGBD) : " + endC + str(dbms_choice))

        if not enter_with_mask and (indicators_method == "BD_exogenes" or indicators_method == "SI_seuillage"):
            print(bold + "    Seuil de NDVI pour l'extraction de la végétation : " + endC + str(threshold_ndvi))
            if indicators_method == "SI_seuillage":
                print(bold + "    Seuil de NDVI pour l'extraction de l'eau : " + endC + str(threshold_ndvi_water))
                print(bold + "    Seuil de NDWI2 pour l'extraction de l'eau : " + endC + str(threshold_ndwi2))
                print(bold + "    Seuil inférieur du BI pour l'extraction du sol nu : " + endC + str(threshold_bi_bottom))
                print(bold + "    Seuil supérieur du BI pour l'extraction du sol nu : " + endC + str(threshold_bi_top))

        print("\n")

        ######################################################
        ### Préparations diverses en amont des traitements ###
        ######################################################

        if os.path.exists(ucz_output):
            removeVectorFile(ucz_output)

        temp_directory = os.path.dirname(ucz_output) + os.sep + "TEMP"

        if os.path.exists(temp_directory):
            print(bold + "Des données temporaires existent, veillez à les conserver si vous reprenez un traitement en cours..." + endC)
            clean_temp = input(bold + blue + "Nettoyer le dossier temporaire ? (Y/N) :" + endC + " ")
            while clean_temp not in ("Y","N"):
                print(bold + yellow + "Attention : veuillez répondre par Y ou N." + endC)
                clean_temp = input(bold + blue + "Nettoyer le dossier temporaire ? (Y/N) :" + endC + " ")
            print("\n")
            if clean_temp == "Y":
                shutil.rmtree(temp_directory)

        if not os.path.exists(temp_directory):
            try:
                os.makedirs(temp_directory)
            except Exception as err:
                e = "OS error: {0}".format(err)
                print(e, file=sys.stderr)
                print(bold + red + "Une erreur est apparue à la création des sous-dossiers de traitements, voir ci-dessus." + endC, file=sys.stderr)
                sys.exit(2)

        #########################################################################
        ### Préparation du fichier log, écriture des paramètres du traitement ###
        #########################################################################

        text = "Lancement d'une classification en Zones Climatiques Urbaines :" + "\n"

        text += "  - Nom du fichier Urban Atlas en entrée : " + str(urbanatlas_input) + "\n"
        text += "  - Nom du fichier classif UCZ en sortie : " + str(ucz_output) + "\n"

        text += "  - Fichier d'emprise de la zone d'étude : " + str(emprise_file) + "\n"

        if indicators_method == "BD_exogenes" or indicators_method == "SI_seuillage":
            if enter_with_mask:
                text += "  - Masque binaire de la végétation : " + str(mask_file) + "\n"
            else:
                text += "  - Image satellite : " + str(image_file) + "\n"
        elif indicators_method == "SI_classif" or indicators_method == "Resultats_classif":
            text += "  - Résultat de classification OCS : " + str(image_file) + "\n"
            if indicators_method == "Resultats_classif":
                text += "  - Modèle Numérique de Hauteur : " + str(mnh_file) + "\n"

        if indicators_method in ("BD_exogenes", "SI_seuillage", "SI_classif"):
            text += "  - Fichiers bâti de la BD TOPO : " + str(built_files_list) + "\n"
            if indicators_method == "BD_exogenes":
                text += "  - Fichier hydrographie de la BD TOPO : " + str(hydrography_file) + "\n"
                text += "  - Fichier RPG : " + str(rpg_file) + "\n"
            elif indicators_method == "SI_seuillage":
                text += "  - Fichiers route de la BD TOPO : " + str(roads_files_list) + "\n"

        text += "  - Méthode de calcul des indicateurs : " + str(indicators_method) + "\n"
        text += "  - Méthode de calcul des UCZ : " + str(ucz_method) + "\n"
        text += "  - Système de gestion de base de données (SGBD) : " + str(dbms_choice) + "\n"

        if not enter_with_mask and (indicators_method == "BD_exogenes" or indicators_method == "SI_seuillage"):
            text += "  - Seuil de NDVI pour l'extraction de la végétation : " + str(threshold_ndvi) + "\n"
            if indicators_method == "SI_seuillage":
                text += "  - Seuil de NDVI pour l'extraction de l'eau : " + str(threshold_ndvi_water) + "\n"
                text += "  - Seuil de NDWI2 pour l'extraction de l'eau : " + str(threshold_ndwi2) + "\n"
                text += "  - Seuil inférieur du BI pour l'extraction du sol nu : " + str(threshold_bi_bottom) + "\n"
                text += "  - Seuil supérieur du BI pour l'extraction du sol nu : " + str(threshold_bi_top) + "\n"

        text += "    ##########" + "\n"
        appendTextFile(path_time_log,text)

        ##################################################
        ### Lancement des calculs, appel des fonctions ###
        ##################################################

        etape1 = input(bold + blue + "Lancer la préparation des données ? (Y/N) :" + endC + " ")
        while etape1 not in ("Y","N"):
            print(bold + yellow + "Attention : veuillez répondre par Y ou N." + endC)
            etape1 = input(bold + blue + "Lancer la préparation des données ? (Y/N) :" + endC + " ")
        print("\n")

        if etape1 == "Y":
            if not enter_with_mask:
                preparationRasters(urbanatlas_input, ucz_output, emprise_file, mask_file, enter_with_mask, image_file, mnh_file, built_files_list, hydrography_file, roads_files_list, rpg_file, indicators_method, ucz_method, dbms_choice, threshold_ndvi, threshold_ndvi_water, threshold_ndwi2, threshold_bi_bottom, threshold_bi_top, 0, path_time_log, temp_directory, FORMAT_RASTER, FORMAT_VECTOR, EXTENSION_RASTER)
            preparationVecteurs(urbanatlas_input, ucz_output, emprise_file, mask_file, enter_with_mask, image_file, mnh_file, built_files_list, hydrography_file, roads_files_list, rpg_file, indicators_method, ucz_method, dbms_choice, threshold_ndvi, threshold_ndvi_water, threshold_ndwi2, threshold_bi_bottom, threshold_bi_top, path_time_log, temp_directory, FORMAT_VECTOR, EXTENSION_VECTOR)
            if indicators_method == "Resultats_classif":
                preparationBatiOCS(urbanatlas_input, ucz_output, emprise_file, mask_file, enter_with_mask, image_file, mnh_file, built_files_list, hydrography_file, roads_files_list, rpg_file, indicators_method, ucz_method, dbms_choice, threshold_ndvi, threshold_ndvi_water, threshold_ndwi2, threshold_bi_bottom, threshold_bi_top, path_time_log, temp_directory, FORMAT_VECTOR, EXTENSION_RASTER, EXTENSION_VECTOR)
            text = "    ##########" + "\n"
            appendTextFile(path_time_log,text)
        print("\n")

            ###

        etape2 = input(bold + blue + "Lancer la préparation des indicateurs ? (Y/N) :" + endC + " ")
        while etape2 not in ("Y","N"):
            print(bold + yellow + "Attention : veuillez répondre par Y ou N." + endC)
            etape2 = input(bold + blue + "Lancer la préparation des indicateurs ? (Y/N) :" + endC + " ")
        print("\n")

        if etape2 == "Y":
            indicateurSI(urbanatlas_input, ucz_output, emprise_file, mask_file, enter_with_mask, image_file, mnh_file, built_files_list, hydrography_file, roads_files_list, rpg_file, indicators_method, ucz_method, dbms_choice, threshold_ndvi, threshold_ndvi_water, threshold_ndwi2, threshold_bi_bottom, threshold_bi_top, path_time_log, temp_directory, EXTENSION_RASTER, EXTENSION_VECTOR)
            indicateurRA(urbanatlas_input, ucz_output, emprise_file, mask_file, enter_with_mask, image_file, mnh_file, built_files_list, hydrography_file, roads_files_list, rpg_file, indicators_method, ucz_method, dbms_choice, threshold_ndvi, threshold_ndvi_water, threshold_ndwi2, threshold_bi_bottom, threshold_bi_top, path_time_log, temp_directory, EXTENSION_RASTER, EXTENSION_VECTOR)
            if ucz_method == "Combinaison_avec_rugosite" or ucz_method == "Hierarchie_avec_rugosite":
                indicateurRug(urbanatlas_input, ucz_output, emprise_file, mask_file, enter_with_mask, image_file, mnh_file, built_files_list, hydrography_file, roads_files_list, rpg_file, indicators_method, ucz_method, dbms_choice, threshold_ndvi, threshold_ndvi_water, threshold_ndwi2, threshold_bi_bottom, threshold_bi_top, path_time_log, temp_directory, EXTENSION_RASTER, EXTENSION_VECTOR)
            text = "    ##########" + "\n"
            appendTextFile(path_time_log,text)
        print("\n")

            ###

        etape3 = input(bold + blue + "Lancer le calcul final des indicateurs et UCZ ? (Y/N) :" + endC + " ")
        while etape3 not in ("Y","N"):
            print(bold + yellow + "Attention : veuillez répondre par Y ou N." + endC)
            etape3 = input(bold + blue + "Lancer le calcul final des indicateurs et UCZ ? (Y/N) :" + endC + " ")
        print("\n")

        if etape3 == "Y":
            if dbms_choice == "SpatiaLite":
                traitementsSpatiaLite(urbanatlas_input, ucz_output, emprise_file, mask_file, enter_with_mask, image_file, mnh_file, built_files_list, hydrography_file, roads_files_list, rpg_file, indicators_method, ucz_method, dbms_choice, threshold_ndvi, threshold_ndvi_water, threshold_ndwi2, threshold_bi_bottom, threshold_bi_top, path_time_log, temp_directory, EXTENSION_VECTOR)
            elif dbms_choice == "PostGIS":
                traitementsPostGIS(urbanatlas_input, ucz_output, emprise_file, mask_file, enter_with_mask, image_file, mnh_file, built_files_list, hydrography_file, roads_files_list, rpg_file, indicators_method, ucz_method, dbms_choice, threshold_ndvi, threshold_ndvi_water, threshold_ndwi2, threshold_bi_bottom, threshold_bi_top, path_time_log, temp_directory)
            text = "    ##########" + "\n" + "\n"
            appendTextFile(path_time_log,text)
        print("\n")

            ###

        # Nettoyage des données temporaires
        if os.path.exists(ucz_output):
            if not save_results_intermediate:
                shutil.rmtree(temp_directory)

        print(green + "Fin de la classification en Zones Climatiques Urbaines : " + endC + ucz_output)

    else:
        print(bold + yellow + "La classification UCZ '" + ucz_output + "' existe déjà." + endC)

    print("\n")

    relance = input(bold + blue + "Relancer une nouvelle classification ? (Y/N) :" + endC + " ")
    while relance not in ("Y","N"):
        print(bold + yellow + "Attention : veuillez répondre par Y ou N." + endC)
        relance = input(bold + blue + "Relancer une nouvelle classification ? (Y/N) :" + endC + " ")
    if relance == "N":
        classification = False
    print("\n")

