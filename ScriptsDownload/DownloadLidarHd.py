#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Nom de l'objet : DownloadLidarHd.py
Description :
    Objectif : Télécharger des données LiDAR HD
    Remarque : Gère le téléchargement des nuages de points et/ou des modèles numériques dérivés

-----------------
Outils utilisés :
 -

------------------------------
Historique des modifications :
 - 18/02/2025 : création
 - 06/03/2025 : parallélisation de la fonction downloadLidarHd() avec envoi de 5 requêtes par seconde
 - 02/07/2025 : obtention des liens de téléchargement via requête sur le flux WFS de l'IGN (au lieu du fichier CSV non-maintenu) + choix spécifique des données à télécharger (nuages de point et/ou MNT et/ou MNS et/ou MNH)

-----------------------
A réfléchir / A faire :
'''

# Import des bibliothèques Python
from __future__ import print_function
import os, sys, argparse, math, requests, threading, time, shutil
from datetime import datetime
from osgeo import ogr, gdal
from Lib_display import bold,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_log import timeLine
from Lib_vector import getEmpriseVector, getGeomPolygons, getProjection, createPolygonsFromGeometryList

# Niveau de debug (variable globale)
debug = 3

# Définition des constantes
DATA_CLOUD, DATA_DTM, DATA_DSM, DATA_DHM = "nuages de points classés", "Modèles Numériques de Terrain", "Modèles Numériques de Surface", "Modèles Numériques de Hauteur"
ABRV_CLOUD, ABRV_DTM, ABRV_DSM, ABRV_DHM = "nuages", "MNT", "MNS", "MNH"
URL_WFS = "https://data.geopf.fr/wfs"
WFS_SERVICE, WFS_VERSION, WFS_REQUEST, WFS_FORMAT = "WFS", "2.0.0", "GetFeature", "json"
LAYER_CLOUDS = "IGNF_LIDAR-HD_TA:nuage-dalle"
LAYER_DTM = "IGNF_LIDAR-HD_TA:mnt-dalle"
LAYER_DSM = "IGNF_LIDAR-HD_TA:mns-dalle"
LAYER_DHM = "IGNF_LIDAR-HD_TA:mnh-dalle"
JSON_FEATURES = "features"
JSON_GEOMETRY, JSON_GEOMETRY_TYPE, JSON_BBOX = "geometry", "type", "bbox"
JSON_PROPERTIES, JSON_PROPERTIES_NAME, JSON_PROPERTIES_URL = "properties", "name", "url"
DICO_FID = "fid"
DICO_XMIN, DICO_YMIN, DICO_XMAX, DICO_YMAX = "xmin", "ymin", "xmax", "ymax"
DICO_XXXX, DICO_YYYY, DICO_TILE = "XXXX", "YYYY", "dalle"
LHD_PC_SUFFIX, LHD_DM_SUFFIX = "nuages_de_points", "modeles_numeriques"
LHD_DTM_SUFFIX, LHD_DSM_SUFFIX, LHD_DHM_SUFFIX = "MNT", "MNS", "MNH"
TILE_FILENAME_SUFFIX = "_dalles_LiDAR_HD"
TILE_SIZE = 1000
GPKG_FORMAT, GPKG_EXTENSION = "GPKG", ".gpkg"

########################################################################
# FONCTION requestData()                                               #
########################################################################
def requestData(abrv, layer, copy_ref_if_exists, download_data, temp_dirname, ref_dirname, tile_dictionary, key, value, tile_dictionary_len):
    '''
    # abrv = abréviation de la donnée (cf. ABRV_CLOUD, ABRV_DTM, ABRV_DSM, ABRV_DHM)
    # layer = couche de la donnée (cf. LAYER_CLOUD, LAYER_DTM, LAYER_DSM, LAYER_DHM)
    # copy_ref_if_exists = paramètre de la fonction générale downloadLidarHd()
    # download_data = paramètre de la fonction générale downloadLidarHd()
    # temp_dirname = variable de la fonction générale downloadLidarHd(), répertoire de sortie de la donnée (associé à output_directory)
    # ref_dirname = variable de la fonction générale downloadLidarHd(), répertoire de sortie de la donnée (associé à ref_lidar_hd_directory)
    # tile_dictionary = dictionnaire des tuiles kilométriques IGN intersectant l'emprise d'étude
    # key = clé associée au dictionnaire cité précédemment
    # value = valeur associée à la clé de dictionnaire cité précédemment
    # tile_dictionary_len = nombre de tuiles kilométriques IGN intersectant l'emprise d'étude
    '''

    # Requête pour vérifier l'existance de la dalle LiDAR HD et récupérer les infos
    json_bbox_value = "%s,%s,%s,%s" % (value[1][DICO_XMIN]+1, value[1][DICO_YMIN]+1, value[1][DICO_XMAX]-1, value[1][DICO_YMAX]-1)
    URL_parameters = dict(
        service=WFS_SERVICE,
        version=WFS_VERSION,
        request=WFS_REQUEST,
        typeName=layer,
        outputFormat=WFS_FORMAT,
        bbox=json_bbox_value,
    )
    response_json = requests.get(URL_WFS, params=URL_parameters).json()

    # Si la requête retourne un résultat vide
    if response_json[JSON_FEATURES] == []:
        tile_dictionary[key][1][abrv] = "Donnée non encore disponible pour cette dalle (au %s)." % datetime.now().strftime("%d/%m/%Y")
        tile_name = "%s_%s" % (str(int(value[1][DICO_XMIN]/TILE_SIZE)).zfill(4), str(int(value[1][DICO_YMAX]/TILE_SIZE)).zfill(4))
        if download_data:
            print(red + "    La dalle \"%s\" n'est pas disponible au téléchargement (dalle %s/%s)." % (tile_name, key, tile_dictionary_len) + endC)

    # Sinon, la donnée existe, on poursuit
    else:

        # Traitement des infos de la requête URL
        feature = response_json[JSON_FEATURES][0]
        download_URL = feature[JSON_PROPERTIES][JSON_PROPERTIES_URL]
        file_basename = feature[JSON_PROPERTIES][JSON_PROPERTIES_NAME]
        temp_file = temp_dirname + os.sep + file_basename
        ref_file = ref_dirname + os.sep + file_basename

        # Mise à jour du fichiers des dalles avec l'URL de téléchargement de la donnée
        tile_dictionary[key][1][abrv] = download_URL

        # Récupération de la dalle
        if download_data:
            if not os.path.exists(ref_file):
                if not os.path.exists(temp_file):
                    requests_get = requests.get(download_URL)
                    if requests_get.status_code == 200:
                        print(green + "    Téléchargement de la donnée \"%s\" (dalle %s/%s)..." % (file_basename, key, tile_dictionary_len) + endC)
                        with open(temp_file, "wb") as file:
                            file.write(requests_get.content)
                    else:
                        print(red + "    La donnée \"%s\" n'est pas disponible au téléchargement (dalle %s/%s)." % (file_basename, key, tile_dictionary_len) + endC)
                else:
                    print(yellow + "    La donnée \"%s\" a déjà été téléchargée, en local (dalle %s/%s)." % (file_basename, key, tile_dictionary_len) + endC)
            else:
                print(yellow + "    La donnée \"%s\" a déjà été téléchargée, dans le répertoire de référence (dalle %s/%s)." % (file_basename, key, tile_dictionary_len) + endC)
                if copy_ref_if_exists and not os.path.exists(temp_file):
                    print(green + "    Copie de la donnée \"%s\" vers le répertoire local de sortie." % file_basename + endC)
                    shutil.copy(ref_file, temp_file)

    return

########################################################################
# FONCTION downloadData()                                              #
########################################################################
def downloadData(data, abrv, layer, copy_ref_if_exists, download_data, temp_dirname, ref_dirname, tile_dictionary, tile_dictionary_len, num_step):
    '''
    # data = nom de la donnée (cf. DATA_CLOUD, DATA_DTM, DATA_DSM, DATA_DHM)
    # abrv = abréviation de la donnée (cf. ABRV_CLOUD, ABRV_DTM, ABRV_DSM, ABRV_DHM)
    # layer = couche de la donnée (cf. LAYER_CLOUD, LAYER_DTM, LAYER_DSM, LAYER_DHM)
    # copy_ref_if_exists = paramètre de la fonction générale downloadLidarHd()
    # download_data = paramètre de la fonction générale downloadLidarHd()
    # temp_dirname = variable de la fonction générale downloadLidarHd(), répertoire de sortie de la donnée (associé à output_directory)
    # ref_dirname = variable de la fonction générale downloadLidarHd(), répertoire de sortie de la donnée (associé à ref_lidar_hd_directory)
    # tile_dictionary = dictionnaire des tuiles kilométriques IGN intersectant l'emprise d'étude
    # tile_dictionary_len = nombre de tuiles kilométriques IGN intersectant l'emprise d'étude
    # num_step = numéro d'étape (1 = nuages de points ; 2 = MNT ; 3 = MNS ; 4 = MNH)
    '''

    print("\n" + cyan + "downloadLidarHd() : " + bold + green + "ETAPE %s/4 - Début de la gestion des %s." % (num_step, data) + endC + "\n")

    # Boucle sur les dalles intersectant l'emprise d'étude (avec multithreading)
    threads, t = [], 1
    for key, value in tile_dictionary.items():
        #requestData(abrv, layer, copy_ref_if_exists, download_data, temp_dirname, ref_dirname, tile_dictionary, key, value, tile_dictionary_len)
        if t%100 == 0:
            time.sleep(60)
        elif t%5 == 0:
            time.sleep(5)
        thread = threading.Thread(target=requestData, args=(abrv, layer, copy_ref_if_exists, download_data, temp_dirname, ref_dirname, tile_dictionary, key, value, tile_dictionary_len, ))
        thread.start()
        threads.append(thread)
        t += 1

    for thread in threads:
        thread.join()

    print("\n" + cyan + "downloadLidarHd() : " + bold + green + "ETAPE %s/4 - Fin de la gestion des %s." % (num_step, data) + endC + "\n")

    return

########################################################################
# FONCTION downloadLidarHd()                                           #
########################################################################
def downloadLidarHd(input_vector, output_directory, process_data_list=["nuages", "MNT", "MNS", "MNH"], ref_lidar_hd_directory="/mnt/Geomatique/REF_DTER_OCC/LiDAR_HD", copy_ref_if_exists=True, download_data=True, path_time_log="", save_results_intermediate=False, overwrite=True):
    '''
    # ROLE :
    #     Téléchargement de données LiDAR HD
    #
    # ENTREES DE LA FONCTION :
    #     input_vector : fichier vecteur d'entrée, correpondant à l'emprise de la zone d'étude
    #     output_directory : répertoire de sortie, où seront stockés les données LiDAR HD
    #     process_data_list : liste des données à télécharger (nuages de points classés, modèles numériques)
    #     ref_lidar_hd_directory : répertoire de référence où sont stockés les données LiDAR HD (serveur géomatique)
    #     copy_ref_if_exists : copier les données du répertoire de référence dans le répertoire de sortie, si elles existent
    #     download_data : télécharger les données (si False, ne gènère que le fichier des dalles recensant les liens de téléchargement)
    #     path_time_log : fichier log de sortie, par défaut vide
    #     save_results_intermediate : conserver les fichiers temporaires, par défaut = False
    #     overwrite : écraser si un fichier existant a le même nom qu'un fichier de sortie, par défaut = True
    # SORTIES DE LA FONCTION :
    #     N.A.
    '''
    if debug >= 3:
        print("\n" + bold + green + "Téléchargement de données LiDAR HD - Variables dans la fonction :" + endC)
        print(cyan + "    downloadLidarHd() : " + endC + "input_vector : " + str(input_vector) + endC)
        print(cyan + "    downloadLidarHd() : " + endC + "output_directory : " + str(output_directory) + endC)
        print(cyan + "    downloadLidarHd() : " + endC + "process_data_list : " + str(process_data_list) + endC)
        print(cyan + "    downloadLidarHd() : " + endC + "ref_lidar_hd_directory : " + str(ref_lidar_hd_directory) + endC)
        print(cyan + "    downloadLidarHd() : " + endC + "copy_ref_if_exists : " + str(copy_ref_if_exists) + endC)
        print(cyan + "    downloadLidarHd() : " + endC + "download_data : " + str(download_data) + endC)
        print(cyan + "    downloadLidarHd() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "    downloadLidarHd() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "    downloadLidarHd() : " + endC + "overwrite : " + str(overwrite) + endC + "\n")

    # Mise à jour du log
    starting_event = "downloadLidarHd() : Début du traitement : "
    timeLine(path_time_log, starting_event)

    print(cyan + "downloadLidarHd() : " + bold + green + "DEBUT DES TRAITEMENTS" + endC + "\n")

    # Définition des variables répertoires
    ref_lhd_pc_dirname = ref_lidar_hd_directory + os.sep + LHD_PC_SUFFIX
    ref_lhd_dm_dirname = ref_lidar_hd_directory + os.sep + LHD_DM_SUFFIX
    ref_lhd_dtm_dirname = ref_lhd_dm_dirname + os.sep + LHD_DTM_SUFFIX
    ref_lhd_dsm_dirname = ref_lhd_dm_dirname + os.sep + LHD_DSM_SUFFIX
    ref_lhd_dhm_dirname = ref_lhd_dm_dirname + os.sep + LHD_DHM_SUFFIX
    temp_lhd_pc_dirname = output_directory + os.sep + LHD_PC_SUFFIX
    temp_lhd_dm_dirname = output_directory + os.sep + LHD_DM_SUFFIX
    temp_lhd_dtm_dirname = temp_lhd_dm_dirname + os.sep + LHD_DTM_SUFFIX
    temp_lhd_dsm_dirname = temp_lhd_dm_dirname + os.sep + LHD_DSM_SUFFIX
    temp_lhd_dhm_dirname = temp_lhd_dm_dirname + os.sep + LHD_DHM_SUFFIX

    # Définition des variables fichiers
    input_vector_basename = os.path.basename(os.path.splitext(input_vector)[0])
    tiles_vector_output = output_directory + os.sep + input_vector_basename + TILE_FILENAME_SUFFIX + GPKG_EXTENSION

    for directory in [temp_lhd_pc_dirname, temp_lhd_dtm_dirname, temp_lhd_dsm_dirname, temp_lhd_dhm_dirname]:
        if not os.path.exists(directory):
            os.makedirs(directory)

    ####################################################################

    ###########
    # Etape 0 # Préparation des traitements
    ###########

    # Gestion du format de l'emprise d'étude
    format_vector_list = [ogr.GetDriver(i).GetDescription() for i in range(ogr.GetDriverCount())]
    i = 0
    for format_vector in format_vector_list:
        driver = ogr.GetDriverByName(format_vector)
        data_source_input = driver.Open(input_vector, 0)
        if data_source_input is not None:
            data_source_input.Destroy()
            break
        i += 1
    format_vector = format_vector_list[i]

    # Gestion des données de l'emprise d'étude
    xmin_ROI, xmax_ROI, ymin_ROI, ymax_ROI = getEmpriseVector(input_vector, format_vector=format_vector)
    xmin_ROI_opti_1km, xmax_ROI_opti_1km, ymin_ROI_opti_1km, ymax_ROI_opti_1km = math.floor(xmin_ROI/TILE_SIZE), math.ceil(xmax_ROI/TILE_SIZE), math.floor(ymin_ROI/TILE_SIZE), math.ceil(ymax_ROI/TILE_SIZE)
    geometry_list = getGeomPolygons(input_vector, col=None, value=None, format_vector=format_vector)
    if len(geometry_list) == 0:
        print(cyan + "downloadLidarHd() : " + bold + red + "Error: There are no geometry in the input vector file \"%s\"!" % input_vector + endC, file=sys.stderr)
        exit(-1)
    elif len(geometry_list) > 1:
        print(cyan + "downloadLidarHd() : " + bold + red + "Error: There are more than one geometry in the input vector file \"%s\" (%s geometries)!" % (input_vector, len(geometry_list)) + endC, file=sys.stderr)
        exit(-1)
    else:
        geometry_ROI = ogr.CreateGeometryFromWkt(geometry_list[0].ExportToWkt())
    epsg, projection = getProjection(input_vector, format_vector=format_vector)

    # Gestion des dalles kilométriques intersectant l'emprise d'étude
    attribute_dico, polygons_attr_geom_dico = {DICO_FID:ogr.OFTInteger, DICO_XMIN:ogr.OFTString, DICO_XMAX:ogr.OFTString, DICO_YMIN:ogr.OFTString, DICO_YMAX:ogr.OFTString, DICO_XXXX:ogr.OFTString, DICO_YYYY:ogr.OFTString, DICO_TILE:ogr.OFTString, ABRV_CLOUD:ogr.OFTString, ABRV_DTM:ogr.OFTString, ABRV_DSM:ogr.OFTString, ABRV_DHM:ogr.OFTString}, {}
    i = 1
    for x in range(xmin_ROI_opti_1km, xmax_ROI_opti_1km, 1):
        for y in range(ymin_ROI_opti_1km+1, ymax_ROI_opti_1km+1, 1):
            xmin_tile, xmax_tile, ymin_tile, ymax_tile = (x*TILE_SIZE), (x*TILE_SIZE + TILE_SIZE), (y*TILE_SIZE - TILE_SIZE), (y*TILE_SIZE)
            geometry_tile = ogr.CreateGeometryFromWkt("POLYGON ((%s %s, %s %s, %s %s, %s %s, %s %s))" % (xmin_tile, ymax_tile, xmax_tile, ymax_tile, xmax_tile, ymin_tile, xmin_tile, ymin_tile, xmin_tile, ymax_tile))
            intersect_tile_ROI = geometry_tile.Intersects(geometry_ROI)
            if intersect_tile_ROI:
                tile_name = "%s_%s" % (str(x).zfill(4), str(y).zfill(4))
                polygons_attr_geom_dico[i] = [geometry_tile, {DICO_FID:i, DICO_XMIN:xmin_tile, DICO_XMAX:xmax_tile, DICO_YMIN:ymin_tile, DICO_YMAX:ymax_tile, DICO_XXXX:x, DICO_YYYY:y, DICO_TILE:tile_name, ABRV_CLOUD:"", ABRV_DTM:"", ABRV_DSM:"", ABRV_DHM:""}]
                i += 1
    i -= 1

    if i >= 1000:
        print(bold + yellow + "Il y a plus de 1 000 dalles dans la zones d'étude, le traitement peut être extrêmement long..." + endC)
        user_response = ""
        while user_response.lower() not in ["oui", "non"]:
            user_response = input(bold + yellow + "Voulez-vous tout de même continuer ? [oui, non]" + endC)
        if user_response.lower() == "non":
            print(cyan + "downloadLidarHd() : " + bold + yellow + "Fin d'exécution demandée par l'utilisateur." + endC)
            exit(0)

    #############
    # Etape S/4 # Gestion des données LiDAR HD
    #############

    # Traitement des nuages de points classés
    if ABRV_CLOUD in process_data_list:
        downloadData(DATA_CLOUD, ABRV_CLOUD, LAYER_CLOUDS, copy_ref_if_exists, download_data, temp_lhd_pc_dirname, ref_lhd_pc_dirname, polygons_attr_geom_dico, i, 1)
    else:
        print("\n" + cyan + "downloadLidarHd() : " + bold + yellow + "ETAPE 1/4 - Pas de gestion des %s demandée." % DATA_CLOUD + endC + "\n")

    # Traitement des Modèles Numériques de Terrain
    if ABRV_DTM in process_data_list:
        downloadData(DATA_DTM, ABRV_DTM, LAYER_DTM, copy_ref_if_exists, download_data, temp_lhd_dtm_dirname, ref_lhd_dtm_dirname, polygons_attr_geom_dico, i, 2)
    else:
        print("\n" + cyan + "downloadLidarHd() : " + bold + yellow + "ETAPE 2/4 - Pas de gestion des %s demandée." % DATA_DTM + endC + "\n")

    # Traitement des Modèles Numériques de Surface
    if ABRV_DSM in process_data_list:
        downloadData(DATA_DSM, ABRV_DSM, LAYER_DSM, copy_ref_if_exists, download_data, temp_lhd_dsm_dirname, ref_lhd_dsm_dirname, polygons_attr_geom_dico, i, 3)
    else:
        print("\n" + cyan + "downloadLidarHd() : " + bold + yellow + "ETAPE 3/4 - Pas de gestion des %s demandée." % DATA_DSM + endC + "\n")

    # Traitement des Modèles Numériques de Hauteur
    if ABRV_DHM in process_data_list:
        downloadData(DATA_DHM, ABRV_DHM, LAYER_DHM, copy_ref_if_exists, download_data, temp_lhd_dhm_dirname, ref_lhd_dhm_dirname, polygons_attr_geom_dico, i, 4)
    else:
        print("\n" + cyan + "downloadLidarHd() : " + bold + yellow + "ETAPE 4/4 - Pas de gestion des %s demandée." % DATA_DHM + endC + "\n")

    createPolygonsFromGeometryList(attribute_dico, polygons_attr_geom_dico, tiles_vector_output, projection=epsg, format_vector=GPKG_FORMAT)
    print(blue + "    %s dalles kilométriques ont été trouvées sur la zone d'étude, elles ont été enregistrées sous %s." % (i, tiles_vector_output) + endC)

    ####################################################################

    print("\n" + cyan + "downloadLidarHd() : " + bold + green + "FIN DES TRAITEMENTS" + endC + "\n")

    # Mise à jour du log
    ending_event = "downloadLidarHd() : Fin du traitement : "
    timeLine(path_time_log, ending_event)

    return 0

#############################################################################################################################
################################################## Mise en place du parser ##################################################
#############################################################################################################################

def main(gui=False):
    parser = argparse.ArgumentParser(prog = "DownloadLidarHd", description = "\
    LiDAR HD data downloader (digitals models and/or points clouds). \n\
    Exemple : python -m DownloadLidarHd -in /mnt/RAM_disk/DownloadLidarHd/ROI.shp \n\
                                        -out /mnt/RAM_disk/DownloadLidarHd/data_LiDAR_HD \n\
                                        -data nuages MNH")

    parser.add_argument("-in", "--input_vector", default="", type=str, required=True, help="Input vector, corresponding to the ROI of the study area.")
    parser.add_argument("-out", "--output_directory", default="", type=str, required=True, help="Output directory, where Digitals Models and/or Points Clouds from LiDAR HD will be downloaded.")
    parser.add_argument("-data", "--process_data_list", choices=["nuages", "MNT", "MNS", "MNH"], default=["nuages", "MNT", "MNS", "MNH"], type=str, nargs="+", required=False, help="Specify data to be downloaded (points clouds, DTM, DSM, DHM). Defaut: all data (points clouds and digital models).")
    parser.add_argument("-ref", "--ref_lidar_hd_directory", default="/mnt/Geomatique/REF_DTER_OCC/LiDAR_HD", type=str, required=False, help="Reference directory, where LiDAR HD are already downloaded.")
    parser.add_argument("-nocp", "--copy_ref_if_exists", action="store_false", default=True, required=False, help="If exists in ref_lidar_hd_directory, copy data to output_directory. Defaut: True")
    parser.add_argument("-nodl", "--download_data", action="store_false", default=True, required=False, help="Download requested data (if False, just generates the tile file with download links). Defaut: True")
    parser.add_argument("-log", "--path_time_log", default="", type=str, required=False, help="Option: Name of log. Default, no log file.")
    parser.add_argument("-sav", "--save_results_intermediate", action="store_true", default=False, required=False, help="Option: Save intermediate result after the process. Default, False.")
    parser.add_argument("-now", "--overwrite", action="store_false", default=True, required=False, help="Option: Overwrite files with same names. Default, True.")
    parser.add_argument("-debug", "--debug", default=3, type=int, required=False, help="Option: Value of level debug trace. Default, 3.")
    args = displayIHM(gui, parser)

    # Récupération du fichier d'entrée
    if args.input_vector != None:
        input_vector = args.input_vector
        if not os.path.isfile(input_vector):
            raise NameError ("\n" + cyan + "DownloadLidarHd: " + bold + red  + "File %s not exists (input_vector)." % input_vector + endC)

    # Récupération du fichier de sortie
    if args.output_directory != None:
        output_directory = args.output_directory

    # Récupération des paramètres spécifiques
    if args.process_data_list != None:
        process_data_list = args.process_data_list
    if args.ref_lidar_hd_directory != None:
        ref_lidar_hd_directory = args.ref_lidar_hd_directory
    if args.copy_ref_if_exists != None:
        copy_ref_if_exists = args.copy_ref_if_exists
    if args.download_data != None:
        download_data = args.download_data

    # Récupération des paramètres généraux
    if args.path_time_log != None:
        path_time_log = args.path_time_log
    if args.save_results_intermediate != None:
        save_results_intermediate = args.save_results_intermediate
    if args.overwrite != None:
        overwrite = args.overwrite
    if args.debug != None:
        global debug
        debug = args.debug

    if debug >= 3:
        print("\n" + bold + green + "Téléchargement de données LiDAR HD - Variables dans le parser :" + endC)
        print(cyan + "    DownloadLidarHd : " + endC + "input_vector : " + str(input_vector) + endC)
        print(cyan + "    DownloadLidarHd : " + endC + "output_directory : " + str(output_directory) + endC)
        print(cyan + "    DownloadLidarHd : " + endC + "process_data_list : " + str(process_data_list) + endC)
        print(cyan + "    DownloadLidarHd : " + endC + "ref_lidar_hd_directory : " + str(ref_lidar_hd_directory) + endC)
        print(cyan + "    DownloadLidarHd : " + endC + "copy_ref_if_exists : " + str(copy_ref_if_exists) + endC)
        print(cyan + "    DownloadLidarHd : " + endC + "download_data : " + str(download_data) + endC)
        print(cyan + "    DownloadLidarHd : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "    DownloadLidarHd : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "    DownloadLidarHd : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "    DownloadLidarHd : " + endC + "debug : " + str(debug) + endC + "\n")

    # EXECUTION DES FONCTIONS
    downloadLidarHd(input_vector, output_directory, process_data_list, ref_lidar_hd_directory, copy_ref_if_exists, download_data, path_time_log, save_results_intermediate, overwrite)

if __name__ == "__main__":
    main(gui=False)

