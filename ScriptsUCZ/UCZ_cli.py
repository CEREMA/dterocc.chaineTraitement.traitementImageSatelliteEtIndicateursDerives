#!/usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

from __future__ import print_function
import os,argparse,sys,shutil
from Lib_text import appendTextFile
from Lib_file import removeVectorFile
from Lib_display import displayIHM
from PreparationDonnees import *
from PreparationIndicateurs import *
from TraitementsFinauxSGBD import *
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 3

def classificationUCZ(urbanatlas_input, ucz_output, emprise_file, mask_file, enter_with_mask, image_file, mnh_file, built_files_list, hydrography_file, roads_files_list, rpg_file, indicators_method, ucz_method, dbms_choice, threshold_ndvi, threshold_ndvi_water, threshold_ndwi2, threshold_bi_bottom, threshold_bi_top, no_data_value, path_time_log, format_raster='GTiff', format_vector='ESRI Shapefile', extension_raster=".tif",  extension_vector=".shp", save_results_intermediate=False, overwrite=True):

        #######################################
        ### Gestion des éventuelles erreurs ###
        #######################################

    if indicators_method == "BD_exogenes":
        if threshold_ndvi == [] and not enter_with_mask:
            print(bold + red + "Erreur : veuillez renseigner la valeur du seuil nécessaire au calcul d'imperméabilité." + endC, file=sys.stderr)
            exit(1)
        if mask_file == "" and image_file == "":
            print(bold + red + "Erreur : veuillez renseigner un fichier raster à traiter (image sat ou masque végétation)." + endC, file=sys.stderr)
            exit(1)
        if built_files_list == [] or hydrography_file == "" or rpg_file == "":
            print(bold + red + "Erreur : veuillez bien renseigner les fichiers vecteurs à traiter (BD TOPO bati et hydrographie + RPG)." + endC, file=sys.stderr)
            exit(1)

    elif indicators_method == "SI_seuillage":
        if threshold_ndvi == [] or threshold_ndvi_water == [] or threshold_ndwi2 == [] or threshold_bi_bottom == [] or threshold_bi_top == []:
            print(bold + red + "Erreur : veuillez renseigner les valeurs de seuils nécessaires au calcul d'imperméabilité." + endC, file=sys.stderr)
            exit(1)
        if image_file == "":
            print(bold + red + "Erreur : veuillez renseigner l'image satellite à traiter." + endC)
            exit(1)
        if built_files_list == [] or roads_files_list == []:
            print(bold + red + "Erreur : veuillez bien renseigner les fichiers vecteurs à traiter (BD TOPO bati et route)." + endC, file=sys.stderr)
            exit(1)

    elif indicators_method == "SI_classif":
        if image_file == "":
            print(bold + red + "Erreur : veuillez renseigner le fichier raster résultat de la classification OCS." + endC, file=sys.stderr)
            exit(1)
        if built_files_list == []:
            print(bold + red + "Erreur : veuillez renseigner le fichier vecteur BD TOPO bati à traiter." + endC)
            exit(1)

    elif indicators_method == "Resultats_classif":
        if image_file == "":
            print(bold + red + "Erreur : veuillez renseigner le fichier raster résultat de la classification OCS." + endC, file=sys.stderr)
            exit(1)
        if mnh_file == "":
            print(bold + red + "Erreur : veuillez renseigner le fichier raster MNH associé à la classification OCS." + endC, file=sys.stderr)
            exit(1)

        #########################################################
        ### Pas d'erreurs, lancement de la classification UCZ ###
        #########################################################

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

        # Préparation des données
        if not enter_with_mask:
            preparationRasters(urbanatlas_input, ucz_output, emprise_file, mask_file, enter_with_mask, image_file, mnh_file, built_files_list, hydrography_file, roads_files_list, rpg_file, indicators_method, ucz_method, dbms_choice, threshold_ndvi, threshold_ndvi_water, threshold_ndwi2, threshold_bi_bottom, threshold_bi_top, no_data_value, path_time_log, temp_director, format_raster, format_vector, extension_raster)
        preparationVecteurs(urbanatlas_input, ucz_output, emprise_file, mask_file, enter_with_mask, image_file, mnh_file, built_files_list, hydrography_file, roads_files_list, rpg_file, indicators_method, ucz_method, dbms_choice, threshold_ndvi, threshold_ndvi_water, threshold_ndwi2, threshold_bi_bottom, threshold_bi_top, path_time_log, temp_directory, extension_vector)
        if indicators_method == "Resultats_classif":
            preparationBatiOCS(urbanatlas_input, ucz_output, emprise_file, mask_file, enter_with_mask, image_file, mnh_file, built_files_list, hydrography_file, roads_files_list, rpg_file, indicators_method, ucz_method, dbms_choice, threshold_ndvi, threshold_ndvi_water, threshold_ndwi2, threshold_bi_bottom, threshold_bi_top, path_time_log, temp_directory, format_vector, extension_raster, extension_vector)
        text = "    ##########" + "\n"
        appendTextFile(path_time_log,text)

        # Préparation au calcul des indicateurs
        indicateurSI(urbanatlas_input, ucz_output, emprise_file, mask_file, enter_with_mask, image_file, mnh_file, built_files_list, hydrography_file, roads_files_list, rpg_file, indicators_method, ucz_method, dbms_choice, threshold_ndvi, threshold_ndvi_water, threshold_ndwi2, threshold_bi_bottom, threshold_bi_top, path_time_log, temp_directory, extension_raster, extension_vector)
        indicateurRA(urbanatlas_input, ucz_output, emprise_file, mask_file, enter_with_mask, image_file, mnh_file, built_files_list, hydrography_file, roads_files_list, rpg_file, indicators_method, ucz_method, dbms_choice, threshold_ndvi, threshold_ndvi_water, threshold_ndwi2, threshold_bi_bottom, threshold_bi_top, path_time_log, temp_directory, extension_raster, extension_vector)
        if ucz_method == "Combinaison_avec_rugosite" or ucz_method == "Hierarchie_avec_rugosite":
            indicateurRug(urbanatlas_input, ucz_output, emprise_file, mask_file, enter_with_mask, image_file, mnh_file, built_files_list, hydrography_file, roads_files_list, rpg_file, indicators_method, ucz_method, dbms_choice, threshold_ndvi, threshold_ndvi_water, threshold_ndwi2, threshold_bi_bottom, threshold_bi_top, path_time_log, temp_directory, extension_raster, extension_vector)
        text = "    ##########" + "\n"
        appendTextFile(path_time_log,text)

        # Fin du calcul des indicateurs, et étape finale de classification UCZ
        if dbms_choice == "SpatiaLite":
            traitementsSpatiaLite(urbanatlas_input, ucz_output, emprise_file, mask_file, enter_with_mask, image_file, mnh_file, built_files_list, hydrography_file, roads_files_list, rpg_file, indicators_method, ucz_method, dbms_choice, threshold_ndvi, threshold_ndvi_water, threshold_ndwi2, threshold_bi_bottom, threshold_bi_top, path_time_log, temp_directory, extension_vector)
        elif dbms_choice == "PostGIS":
            traitementsPostGIS(urbanatlas_input, ucz_output, emprise_file, mask_file, enter_with_mask, image_file, mnh_file, built_files_list, hydrography_file, roads_files_list, rpg_file, indicators_method, ucz_method, dbms_choice, threshold_ndvi, threshold_ndvi_water, threshold_ndwi2, threshold_bi_bottom, threshold_bi_top, path_time_log, temp_directory)
        text = "    ##########" + "\n" + "\n"
        appendTextFile(path_time_log,text)

        # Nettoyage des données temporaires
        if not save_results_intermediate:
            shutil.rmtree(temp_directory)

        print(green + "Fin de la classification en Zones Climatiques Urbaines : " + endC + ucz_output)

    else:
        print( bold + red + "La classification UCZ '" + ucz_output + "' existe déjà." + endC, file=sys.stderr)

    print("\n")

#############################################################################################################################
################################################## Mise en place du parser ##################################################
#############################################################################################################################

def main(gui=False):
    parser = argparse.ArgumentParser(prog = "Classification des Zones Climatiques Urbaines", formatter_class = argparse.RawTextHelpFormatter, description = """Mise en place d'une classification des Zones Climatiques Urbaines :
    Exemple : python UCZ_cli.py -in /home/scgsi/Bureau/UrbanAtlas.shp -out /home/scgsi/Bureau/CartoUCZ.shp -emp /home/scgsi/Bureau/ZoneEtude.shp -msk /home/scgsi/Bureau/masque_veg.tif
        -bat /home/scgsi/Bureau/bati1.shp /home/scgsi/Bureau/bati2.shp -hyd /home/scgsi/Bureau/hydro.shp -rpg /home/scgsi/Bureau/RPG.shp -methi BD_exogenes -methu Hierarchie_avec_rugosite -sgbd SpatiaLite
    Info : lancer 'python UCZ.py' pour acceder a une interface qui vous guidera pas a pas dans le choix des arguments""", epilog = "Se reporter au tutoriel pour savoir quels parametres renseigner suivant les cas.")

    parser.add_argument('-in', '--urbanatlas_input', default="", type=str, required=True, help="Nom du fichier Urban Atlas en entree (vecteur).")
    parser.add_argument('-out', '--ucz_output', default="", type=str, required=True, help="Nom du fichier classif UCZ en sortie (vecteur).")

    parser.add_argument('-emp', '--emprise_file', default="", type=str, required=True, help="Fichier d'emprise de la zone d'etude (vecteur).")
    parser.add_argument('-msk', '--mask_file', default="", type=str, required=False, help="Masque binaire de la vegetation a traiter (raster).")
    parser.add_argument('-img', '--image_file', default="", type=str, required=False, help="Image satellite a traiter, ou resultat de classification OCS (raster).")
    parser.add_argument('-mnh', '--mnh_file', default="", type=str, required=False, help="Modele Numerique de Hauteur a traiter (raster).")
    parser.add_argument('-bat', '--built_files_list', nargs="+", default=[], type=str, required=False, help="Liste des fichiers bati de la BD TOPO a traiter (vecteur).")
    parser.add_argument('-hyd', '--hydrography_file', default="", type=str, required=False, help="Fichier hydrographie de la BD TOPO a traiter (vecteur).")
    parser.add_argument('-rou', '--roads_files_list', nargs="+", default=[], type=str, required=False, help="Liste des fichiers route de la BD TOPO a traiter (vecteur).")
    parser.add_argument('-rpg', '--rpg_file', default="", type=str, required=False, help="Fichier RPG a traiter (vecteur).")

    parser.add_argument('-methi', '--indicators_method', default="BD_exogenes", type=str, choices=['BD_exogenes','SI_seuillage','SI_classif','Resultats_classif'], required=False, help="Choix de la methode pour le calcul des indicateurs, par defaut BD_exogenes.")
    parser.add_argument('-methu', '--ucz_method', default="Hierarchie_avec_rugosite", type=str, choices=['Combinaison_sans_rugosite','Combinaison_avec_rugosite','Hierarchie_sans_rugosite','Hierarchie_avec_rugosite'], required=False, help="Choix de la methode pour le calcul des UCZ, par defaut Hierarchie_avec_rugosite.")
    parser.add_argument('-sgbd', '--dbms_choice', default='SpatiaLite', type=str, choices=['SpatiaLite','PostGIS'], required=False, help="Choix du SGBD pour les requetes SQL, par defaut SpatiaLite.")

    parser.add_argument('-s1', '--threshold_ndvi', default=[], type=float, required=False, help="Choix du seuil de NDVI pour extraire la vegetation.")
    parser.add_argument('-s2', '--threshold_ndvi_water', default=[], type=float, required=False, help="Choix du seuil de NDVI pour extraire l'eau.")
    parser.add_argument('-s3', '--threshold_ndwi2', default=[], type=float, required=False, help="Choix du seuil de NDWI2 pour extraire l'eau.")
    parser.add_argument('-s4', '--threshold_bi_bottom', default=[], type=float, required=False, help="Choix du seuil inferieur du BI pour extraire le sol nu.")
    parser.add_argument('-s5', '--threshold_bi_top', default=[], type=float, required=False, help="Choix du seuil superieur du BI pour extraire le sol nu.")
    parser.add_argument("-ndv",'--no_data_value',default=0,help="Option pixel value for raster file to no data, default : 0 ", type=int, required=False)
    parser.add_argument('-raf','--format_raster', default="GTiff", help="Option : Format output image raster. By default : GTiff (GTiff, HFA...)", type=str, required=False)
    parser.add_argument('-rae','--extension_raster', default=".tif", help="Option : Extension file for image raster. By default : '.tif'", type=str, required=False)
    parser.add_argument('-vee','--extension_vector',default=".shp",help="Option : Extension file for vector. By default : '.shp'", type=str, required=False)
    parser.add_argument('-log', '--path_time_log', default="/home/scgsi/Bureau/logUCZ.txt", type=str, required=False, help="Name of log")
    parser.add_argument('-sav', '--save_results_intermediate', action='store_true', default=False, required=False, help="Save or delete intermediate result after the process. By default, False")
    parser.add_argument('-now', '--overwrite', action='store_false', default=True, required=False, help="Overwrite files with same names. By default, True")
    parser.add_argument('-debug', '--debug', default=3, type=int, required=False, help="Option : Value of level debug trace, default : 3")

    args = displayIHM(gui, parser)

    # Paramètres d'entrée et de sortie obligatoire (fichiers Urban Atlas et classif UCZ)
    if args.urbanatlas_input != None:
        urbanatlas_input = args.urbanatlas_input
    if args.ucz_output != None:
        ucz_output = args.ucz_output

    # Récupération du fichier d'emprise de la zone d'étude
    if args.emprise_file != None:
        emprise_file = args.emprise_file

    # Récupération du masque binaire des zones végétalisées
    if args.mask_file != None:
        mask_file = args.mask_file
        enter_with_mask = True
    enter_with_mask = mask_file != ""

    # Récupération de l'image satellite, ou du résultat de classification OCS et du MNH associé à traiter
    if args.image_file != None:
        image_file = args.image_file
    if args.mnh_file != None:
        mnh_file = args.mnh_file

    # Récupération des couches vecteurs BD TOPO et RPG à traiter
    if args.built_files_list != None:
        built_files_list = args.built_files_list
    if args.hydrography_file != None:
        hydrography_file = args.hydrography_file
    if args.roads_files_list != None:
        roads_files_list = args.roads_files_list
    if args.rpg_file != None:
        rpg_file = args.rpg_file

    # Récupération des paramètres sur les méthiodes de calcul
    if args.indicators_method != None:
        indicators_method = args.indicators_method
    if args.ucz_method != None:
        ucz_method = args.ucz_method
    if args.dbms_choice != None:
        dbms_choice = args.dbms_choice

    # Récupération des paramètres de seuillage des néocanaux
    if args.threshold_ndvi != None:
        threshold_ndvi = args.threshold_ndvi
    if args.threshold_ndvi_water != None:
        threshold_ndvi_water = args.threshold_ndvi_water
    if args.threshold_ndwi2 != None:
        threshold_ndwi2 = args.threshold_ndwi2
    if args.threshold_bi_bottom != None:
        threshold_bi_bottom = args.threshold_bi_bottom
    if args.threshold_bi_top != None:
        threshold_bi_top = args.threshold_bi_top

    # Paramettre des no data
    if args.no_data_value != None:
        no_data_value = args.no_data_value

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

    # Récupération de l'option de sauvegarde des fichiers intermédiaires
    if args.save_results_intermediate != None:
        save_results_intermediate = args.save_results_intermediate

    # Récupération de l'option écrasement
    if args.overwrite!= None:
        overwrite = args.overwrite

    # Récupération de l'option niveau de debug
    if args.debug!= None:
        global debug
        debug = args.debug

    if not os.path.exists(os.path.dirname(ucz_output)):
        os.makedirs(os.path.dirname(ucz_output))

    classificationUCZ(urbanatlas_input, ucz_output, emprise_file, mask_file, enter_with_mask, image_file, mnh_file, built_files_list, hydrography_file, roads_files_list, rpg_file, indicators_method, ucz_method, dbms_choice, threshold_ndvi, threshold_ndvi_water, threshold_ndwi2, threshold_bi_bottom, threshold_bi_top, no_data_value, path_time_log, format_raster, format_vector, extension_raster, extension_vector, save_results_intermediate, overwrite)

if __name__ == '__main__':
    main(gui=False)

