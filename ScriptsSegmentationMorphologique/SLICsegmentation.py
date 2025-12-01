#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT QUI SEGMENTE UNE IMAGE RGB AVEC L'ALGORITHME DE SEGMENTATION SUPERPIXEL SLIC (SIMPLE LINEAR ITERATIVE CLUSTERING)                  #
#                                                                                                                                           #
#############################################################################################################################################

"""
Nom de l'objet : SLICsegmentation.py
Description :
    Objectif : Applique une segmentation morphologique sur une image RGB par superpixels via l’algorithme SLIC.
    Deux modes sont possibles :
        - Mode fixe : exécute la segmentation avec un ensemble de paramètres prédéfinis (compactness, sigma, target_area).
        - Mode optimisé : utilise une méthode d’optimisation MCMC (emcee) pour rechercher automatiquement la meilleure combinaison de paramètres selon un score basé sur plusieurs métriques (dominance, compacité, surface moyenne, écart-type).
    Le script exporte les résultats au format vecteur (.shp), une version lissée de la meilleure segmentation  générée via GRASS.

Date de création : 19/05/2025
----------
Histoire :
----------
Origine : Ce script a été développé dans le cadre du stage de Lisa au CEREMA (2025), sur l’analyse
          morphologique du tissu urbain. Il reprend la structure du script CCMsegmentation.py


Modifications :
    - Adaptation pour l’algorithme SLIC (mai 2025)
    - Intégration de l’optimisation MCMC avec emcee
    - Ajout du calcul de métriques : dominance, compacité, surface moyenne, écart-type

"""

##### Imports #####

# Système
import os, sys, time, random, uuid, shutil
from datetime import datetime
from tqdm import tqdm

# Traitement de données
import numpy as np
import pandas as pd

# Segmentation
from skimage.segmentation import slic

# Optimisation
import emcee

# Raster et vecteur
import rasterio
import geopandas as gpd
from rasterio.features import shapes
from shapely.geometry import shape

# Interne libs
from Lib_display import bold, black, red, green, yellow, blue, magenta, cyan, endC
from Lib_raster import identifyPixelValues
from Lib_vector import bufferVector, cutVectorAll
from Lib_file import removeVectorFile
from Lib_text import appendTextFile

# Librairies internes (lissage GRASS) (Stat rasterstat)
from Lib_grass import initializeGrass, smoothGeomGrass
from CrossingVectorRaster import statisticsVectorRaster

# Paramètre de débogage (0 = silencieux, 3 = très verbeux)
debug = 1

# === Cibles, poids, bornes ===
TARGETS = {
    "surface_mean": 7500, # m2 soit 0.75 ha
    "compacity": 0.55,
    "std_area": 6000,
    "dominance" : 0.90
}
WEIGHTS = {
    "surface_mean": 0.25,
    "compacity": 0.25,
    "std_area": 0.30,
    "dominance" : 0.20
}
# === Paramètres de l'optimisation MCMC ===

# Nom des paramètres SLIC testés :
# - compactness : équilibre forme vs couleur
# - sigma       : flou appliqué à l’image avant clustering
# - target_area : surface moyenne visée d’un superpixel

DEFAULT_PARAMETERS_SLIC = {
    'SLIC': {
        'compactness': [0.85],
        'sigma': [0.7],
        'target_area': [11500]
    }
}
BOUNDS = {
    "compactness": (0.55, 0.85),
    "sigma": (0.5, 0.7),
    "target_area": (10000, 12500)
}
PARAM_NAMES = ["compactness", "sigma", "target_area"]
NDIM = len(BOUNDS)
NWALKERS = 8
NSTEPS = 10

###########################################################################################################################################
# FUNCTION softError()                                                                                                                    #
###########################################################################################################################################
def softError(value, target):
    """
    # ROLE:
    #     Calcule l’erreur quadratique relative entre une valeur mesurée et une valeur cible
    #     Utilisée pour quantifier l’écart d’une métrique par rapport à son objectif dans le calcul du score global
    # PARAMETERS:
    #     value  : valeur mesurée à évaluer
    #     target : valeur cible de référence
    # RETURNS:
    #     erreur (float) : erreur relative au carré
    """
    return ((value - target) / target) ** 2

###########################################################################################################################################
# FUNCTION scoreFunction()                                                                                                                #
###########################################################################################################################################
def scoreFunction(surface_mean, std_area, compacity, dominance):
    """
    # ROLE:
    #     Calcule un score global basé sur les écarts relatifs pondérés entre les métriques calculées
    #     (surface moyenne, écart-type des surfaces, compacité) et leurs cibles définies
    # PARAMETERS:
    #     surface_mean : surface moyenne des polygones
    #     std_area     : écart-type des surfaces des polygones
    #     compacity    : compacité moyenne des polygones
    # RETURNS:
    #     score (float) : score global (à minimiser)
    """
    return (
        WEIGHTS["surface_mean"] * softError(surface_mean, TARGETS["surface_mean"]) +
        WEIGHTS["std_area"] * softError(std_area, TARGETS["std_area"]) +
        WEIGHTS["compacity"] * softError(compacity, TARGETS["compacity"]) +
        WEIGHTS["dominance"] * softError(dominance, TARGETS["dominance"])
    )

###########################################################################################################################################
# FUNCTION computeMetrics()                                                                                                               #
###########################################################################################################################################
def computeMetrics(gdf):
    """
    # ROLE:
    #     Calcule les principales métriques géométriques des polygones :
    #     - Surface moyenne
    #     - Écart-type des surfaces
    #     - Compacité moyenne (forme circulaire idéale = 1)
    # PARAMETERS:
    #     gdf : GeoDataFrame contenant des géométries de type polygone ou multipolygone
    # RETURNS:
    #     surface_mean (float) : surface moyenne des polygones (en m²)
    #     std_area     (float) : écart-type des surfaces
    #     compacity    (float) : compacité moyenne (valeurs comprises entre 0 et 1)
    """
    areas = gdf.geometry.area
    surface_mean = areas.mean()
    std_area = areas.std()
    compacities = 4 * np.pi * areas / (gdf.geometry.length ** 2 + 1e-10)
    compacity = compacities.mean()
    return surface_mean, std_area, compacity

###########################################################################################################################################
# FUNCTION computeDominanceSimplified()                                                                                                   #
###########################################################################################################################################
def computeDominanceSimplified(raster_data_input, gdf_seg, output_dir, epsg=2154, no_data_value=0, format_vector='ESRI Shapefile', extension_vector=".shp", save_results_intermediate=False):
    """
    ROLE :
        Calcule le taux moyen de dominance des classes du raster à l’intérieur d’un ensemble de polygones segmentés.

    PRINCIPE :
        Pour chaque polygone issu d’une segmentation :
            - On identifie la classe majoritaire (valeur la plus fréquente) à partir du raster de classification (ex : OSO).
            - On calcule le rapport entre le nombre de pixels de cette classe majoritaire et le nombre total de pixels du polygone.
            - Ce rapport est appelé "dominance".

    PARAMÈTRES :
         #    raster_data_input : chemin vers le raster de classification utilisé pour le croisement (doit être mono-bande)
         #    gdf_seg            : GeoDataFrame contenant les polygones segmentés
         #    output_dir         : dossier de sortie où seront stockés temporairement les fichiers nécessaires au calcul
         #    epsg               : code EPSG du système de projection (par défaut : 2154 - Lambert 93)
         #    no_data_value      : valeur à considérer comme "NoData" dans le raster
         #    format_vector      : Format for the output vector file (default is 'ESRI Shapefile')
         #    extension_vector   : extension du fichier vecteur de sortie, par defaut = '.shp'
         #    save_results_intermediate : fichiers de sorties intermediaires non nettoyées, par defaut = False

    ÉTAPES :
        1. Sauvegarde des polygones en vector temporaire
        2. Calcul croisé des statistiques raster/vecteur avec `statisticsVectorRaster` (majority + count)
        3. Lecture des statistiques et calcul du taux de dominance pour chaque polygone :
            dominance = pixels_majoritaires / total_pixels
        4. Retourne la moyenne des taux de dominance (dominance_mean)
        5. Nettoyage des fichiers temporaires

    """
    tmp_id = str(uuid.uuid4())[:8]
    tmp_in = os.path.join(output_dir, f"seg_{tmp_id}{extension_vector}")
    tmp_stat = os.path.join(output_dir, f"stat_{tmp_id}{extension_vector}") #création de fichiers temporaires

    #fonction statistic fonctionne avec des fichiers vecteur:sauvegarde geodataframe en fichier
    #gdf_seg.to_file(tmp_in, driver=format_vector, crs=f"EPSG:{epsg}")
    gdf_seg = gdf_seg.set_crs(epsg=epsg, inplace=False)
    gdf_seg.to_file(tmp_in, driver=format_vector)

      # Stat pour les classes OSO
    class_label_dico = {}
    col_to_delete_list = []

      # Pour toutes les valeurs
    image_values_list = identifyPixelValues(raster_data_input)
    if no_data_value in image_values_list :
        del image_values_list[no_data_value]

    class_label_dico[no_data_value] = str(no_data_value)
    col_to_delete_list.append("S_" + str(no_data_value))
    for id_value in image_values_list :
        class_label_dico[id_value] = str(id_value)
        col_to_delete_list.append("S_" + str(id_value))

    statisticsVectorRaster(raster_data_input, tmp_in, tmp_stat, 1, True, True, False, col_to_delete_list, ["count", "majority"], class_label_dico, False, no_data_value, format_vector, "", save_results_intermediate, True)

   # Lecture du fichier statistique et calcul
    gdf_stat = gpd.read_file(tmp_stat)
    if debug >= 1:
        print(cyan + "computeDominanceSimplified() : " + endC + "Colonnes présentes dans le fichier statistique : {}".format(gdf_stat.columns))

    if "majority" not in gdf_stat.columns or "count" not in gdf_stat.columns:
        print(cyan + "computeDominanceSimplified() " + bold + red + "!!! Erreur : le champ 'majority' ou 'count' est manquant dans le fichier statistique." + endC, file=sys.stderr)
        exit()

    else:
        # Calcul du nombre de pixels de la classe majoritaire
        gdf_stat["stat_maj"] = gdf_stat.apply(
            lambda row: row.get(str(int(float(row["majority"]))), 0) if pd.notnull(row["majority"]) else 0,
            axis=1
        )
        gdf_stat["domin"] = gdf_stat["stat_maj"] / gdf_stat["count"].replace(0, np.nan)
        dominance_mean = gdf_stat["domin"].mean(skipna=True)

    # Nettoyage des fichiers temporaires
    if not save_results_intermediate:
        if os.path.isfile(tmp_in):
            removeVectorFile(tmp_in, format_vector)
        if os.path.isfile(tmp_stat):
            removeVectorFile(tmp_stat, format_vector)

    return dominance_mean

###########################################################################################################################################
# FUNCTION slicProcess()                                                                                                                  #
###########################################################################################################################################
def slicProcess(params, img, emprise_vector, vector_segmentation_out, pixel_area, width, height, transform, epsg=2154, format_vector='ESRI Shapefile'):
    """
    # ROLE:
    #     Teste une combinaison de paramètres SLIC, applique la segmentation, vectorise les superpixels,
    #     découpe selon l’emprise, calcule les surfaces, attribue un identifiant (FID),
    #     sauvegarde le vecteur en sortie
    #
    # PARAMETERS:
    #     params                  : liste de paramètres [compactness, sigma, target_area]
    #     img                     : image RGB au format numpy (HxWx3)
    #     emprise_vector          : shapefile d’emprise utilisé pour découper les polygones générés
    #     vector_segmentation_out : chemin de sortie du shapefile de segmentation généré
    #     pixel_area              : surface d’un pixel (en m²), utile pour estimer le nombre de segments
    #     width                   : largeur du raster (en pixels)
    #     height                  : hauteur du raster (en pixels)
    #     transform               : objet Affine (géoréférencement de l’image raster)
    #     epsg (int)              : code EPSG du système de projection (par défaut : 2154)
    #     format_vector (str)     : format du fichier vecteur de sortie (par défaut : 'ESRI Shapefile')
    #
    # RETURNS:
    #     gdf_clip : GeoDataFrame contenant la segmentation vectorisée, découpée, avec champs FID et surface
    #
    # NOTE:
    #     Cette fonction est utilisée pour les tests simples hors MCMC. Elle applique enforce_connectivity=True
    """

    compactness, sigma, area = params
    n_segments = int((width * height * pixel_area) / area)
    segments = slic(img, n_segments=n_segments, compactness=compactness, sigma=sigma, convert2lab=False, start_label=1, enforce_connectivity=True)

    mask = np.ones_like(segments, dtype=np.uint8)
    geoms, values = zip(*[(shape(g), v) for g, v in shapes(segments.astype(np.int32), mask=mask, transform=transform)])

    gdf = gpd.GeoDataFrame({"segment_id": values, "geometry": geoms}, crs="EPSG:" + str(epsg))
    emprise = gpd.read_file(emprise_vector)
    gdf_clip = gpd.overlay(gdf, emprise, how="intersection", keep_geom_type=False)
    gdf_clip = gdf_clip[gdf_clip.geometry.type.isin(["Polygon", "MultiPolygon"])]

    if gdf_clip.empty or gdf_clip["segment_id"].nunique() < 30:
        print(cyan + "slicProcess() : " + bold + red + "!!! La segmentation contient trop peu de polygones valides" + endC, file=sys.stderr)
        exit()

    gdf_clip = gdf_clip[["geometry"]].copy()
    gdf_clip["area"] = gdf_clip.geometry.area
    gdf_clip = gdf_clip.reset_index(drop=True)
    gdf_clip["FID"] = gdf_clip.index + 1
    gdf_clip = gdf_clip[["FID", "area", "geometry"]]

    #gdf_clip.to_file(vector_segmentation_out, driver=format_vector, crs="EPSG:" + str(epsg))
    gdf_clip = gdf_clip.set_crs(epsg=epsg, inplace=False)
    gdf_clip.to_file(vector_segmentation_out, driver=format_vector)
    return gdf_clip

###########################################################################################################################################
# FUNCTION evaluateSegmentationSlic()                                                                                                     #
###########################################################################################################################################
def evaluateSegmentationSlic(params, img, vector_segmentation_out, transform, crs, emprise_vector, pixel_area, width, height, output_dir, raster_oso_input, epsg=2154, no_data_value=0, format_vector='ESRI Shapefile', extension_vector=".shp", save_results_intermediate=False):

    """
    # ROLE:
    #     Teste une combinaison de paramètres SLIC, applique la segmentation, vectorise, découpe selon l’emprise,
    #     calcule les métriques géométriques, sauvegarde le vector et retourne un score à minimiser
    # PARAMETERS:
    #     params      : liste de paramètres [compactness, sigma, target_area]
    #     img         : image RGB (array numpy HxWx3)
    #     vector_segmentation_out : TBD
    #     transform   : objet affine (géoréférencement raster)
    #     crs         : système de projection (ex: EPSG:2154)
    #     emprise_vector  : vector emprise à utiliser pour le découpage
    #     pixel_area  : surface d’un pixel en m² (float)
    #     width       : largeur du raster (int)
    #     height      : hauteur du raster (int)
    #     output_dir  : répertoire de sauvegarde des shapefiles
    #     raster_oso_input : raster de référence (OSO)
    #     no_data_value : Option : Value pixel of no data (par défaut : 0)
    #     epsg (int): EPSG code of the desired projection (default is 2154).
    #     format_vector (str): Format for the output vector file (default is 'ESRI Shapefile')
    #     extension_vector : extension du fichier vecteur de sortie, par defaut = '.shp'
    #     save_results_intermediate : fichiers de sorties intermediaires non nettoyées, par defaut = False
    """
    SUFFIX_TMP = "_tmp"

    # Evite de sortir des plages de paramètres
    params = [max(min(v, BOUNDS[n][1]), BOUNDS[n][0]) for v, n in zip(params, PARAM_NAMES)]

    compactness, sigma, area = params
    if debug >= 1:
        print(cyan + "evaluateSegmentationSlic() : " + endC + "Test SLIC | Compactness={:.3f} | Sigma={:.3f} | Area={}".format(compactness, sigma, int(area)))

    # Appel de la fonction de segmentation SLIC
    gdf_clip = slicProcess(
        params, img, emprise_vector, vector_segmentation_out,
        pixel_area, width, height, transform, epsg, format_vector
    )

    # Vérifie que la segmentation a réussi
    if gdf_clip is None:
        print(cyan + "evaluateSegmentationSlic() : " + bold + red + "!!! La segmentation a échoué : GeoDataFrame = None" + endC, file=sys.stderr)
        exit()

    # Calcul des métriques
    m, s, c = computeMetrics(gdf_clip)

    # Calcul de la dominance
    d = computeDominanceSimplified(
        raster_oso_input, gdf_clip, output_dir, epsg,
        no_data_value, format_vector, extension_vector, save_results_intermediate
    )
    # Calcul du score global
    score = scoreFunction(m, s, c, d)

    # Génère un nom de fichier avec les paramètres
    basename = f"slic_C{compactness:.2f}_S{sigma:.2f}_A{int(area)}_score{score:.4f}".replace('.', 'p')
    out_path = os.path.join(output_dir, basename + extension_vector)

    # Sauvegarde le fichier final
    #gdf_clip.to_file(out_path, driver=format_vector)
    gdf_clip = gdf_clip.set_crs(epsg=epsg, inplace=False)
    gdf_clip.to_file(out_path, driver=format_vector)

    # Stocke les résultats
    RESULTS.append({
        "compactness": compactness,
        "sigma": sigma,
        "target_area": area,
        "score": score,
        "surface_mean": m,
        "std_area": s,
        "compacity": c,
        "dominance": d,
        "vector": out_path
    })

    return -score

###########################################################################################################################################
# FUNCTION smoothingGeometry()                                                                                                            #
###########################################################################################################################################
def smoothingGeometry(emprise_vector, vector_segmentation, vector_file_seg_output, epsg=2154, format_vector='ESRI Shapefile', extension_vector=".shp", save_results_intermediate=False):
    """
    # ROLE:
    #     Lisse les géometries de la ségmentation et rajoute les polygones manquants en bordure d'emprise
    # PARAMETERS:
    #     emprise_vector       : chemin du fichier vector définissant la zone d’étude (emprise)
    #     vector_segmentation  : fichier vecteur sortie de la segmentation SLIC
    #     vector_file_seg_output : fichier vecteur résultat de la segmentation
    #     epsg (int): EPSG code of the desired projection (default is 2154)
    #     format_vector (str): Format for the output vector file (default is 'ESRI Shapefile')
    #     extension_vector : extension du fichier vecteur de sortie, par defaut = '.shp'    #     save_results_intermediate : fichiers de sorties intermediaires non nettoyées, par defaut = False
    # RETURNS:
    #     None
    """
    SUFFIX_TMP = "_tmp"

    # Initialisation de GRASS pour le lissage
    xmin, ymin, xmax, ymax = gpd.read_file(vector_segmentation).total_bounds
    repository = os.path.dirname(vector_file_seg_output)
    initializeGrass(repository, xmin, xmax, ymin, ymax, 1, 1, epsg)

    # Fichier temporaire brut2
    vector_segmentation_tmp2 = os.path.splitext(vector_file_seg_output)[0] + SUFFIX_TMP + "2" + extension_vector

    # Lissage Chaiken
    smoothGeomGrass(
        vector_segmentation,
        vector_segmentation_tmp2,
        {"method": "chaiken", "threshold": 60},
        format_vector,
        True
    )

    # Rajouter les polygones de bord manquants
    gdf_seg_liss   = gpd.read_file(vector_segmentation_tmp2)
    gdf_seg_masked = gdf_seg_liss.dissolve()
    gdf_emprise = gpd.read_file(emprise_vector).to_crs(gdf_seg_masked.crs)

    # 1) Différence emprise segmentation lissée
    gdf_seg_comple = gpd.GeoDataFrame(
        geometry=gdf_emprise.geometry.difference(gdf_seg_masked.unary_union),
        crs=gdf_emprise.crs
    ).explode(index_parts=False).reset_index(drop=True)

    gdf_seg_comple["area"] = gdf_seg_comple.geometry.area
    gdf_seg_comple["FID"]  = gdf_seg_comple.index + 1

    fields_to_get_list = ["FID", "area", "geometry"]

    # 2) Fusion puis intersection avec l’emprise
    gdf_seg_fusion = pd.concat(
        [gdf_seg_liss[fields_to_get_list], gdf_seg_comple[fields_to_get_list]],
        ignore_index=True
    )
    gdf_seg_output = gpd.overlay(
        gdf_seg_fusion, gdf_emprise, how="intersection", keep_geom_type=True
    )

    # 3) Calcul final (une seule fois) après overlay
    gdf_seg_output = gdf_seg_output.to_crs(epsg)
    gdf_seg_output["area"] = gdf_seg_output.geometry.area
    gdf_seg_output["FID"]  = gdf_seg_output.index + 1
    gdf_seg_output = gdf_seg_output[["FID", "area", "geometry"]]

    # 4) Export
    #gdf_seg_output.to_file(vector_file_seg_output, driver=format_vector)
    gdf_seg_output = gdf_seg_output.set_crs(epsg=epsg, inplace=False)
    gdf_seg_output.to_file(vector_file_seg_output, driver=format_vector)

    # 5) Nettoyage
    if not save_results_intermediate:
        if os.path.exists(vector_segmentation_tmp2):
            removeVectorFile(vector_segmentation_tmp2, format_vector)
        tmp_dir = repository + os.sep + "GRASS_database"
        if os.path.isdir(tmp_dir):
            shutil.rmtree(tmp_dir, ignore_errors=True)
    return

###########################################################################################################################################
# FUNCTION processingSLIC()                                                                                                               #
###########################################################################################################################################
def processingSLIC(base_folder, emprise_vector, image_input, raster_oso_input, vector_file_seg_output, optimize=True, fixed_struct_params=None, no_data_value=0, epsg=2154, format_vector='ESRI Shapefile', extension_vector=".shp", path_time_log = "", save_results_intermediate=False, overwrite=True):

    """
    # ROLE:
    #     Applique une segmentation morphologique SLIC sur une image RGB
    #     - Si optimize=True : exécute une recherche des meilleurs paramètres via MCMC et exporte la meilleure segmentation
    #     - Si optimize=False : exécute la segmentation une seule fois avec les paramètres spécifiés dans fixed_struct_params
    #     Dans les deux cas, la meilleure segmentation est lissée avec GRASS et exportée en vector
    # PARAMETERS:
    #     base_folder          : chemin racine du projet (utilisé pour organiser les résultats)
    #     emprise_vector       : chemin du fichier vector définissant la zone d’étude (emprise)
    #     image_input          : raster RGB (image satellite ou pseudo-RGB) à segmenter
    #     raster_oso_input      : raster de référence (OSO) utilisé pour le calcul de la dominance
    #     vector_file_seg_output : dossier de sortie où seront sauvegardés les résultats de la segmentation
    #     optimize             : booléen pour activer (True) ou désactiver (False) l’optimisation MCMC
    #     fixed_struct_params         : liste [compactness, sigma, target_area] utilisée uniquement si optimize=False
    #     no_data_value : Option : Value pixel of no data (par défaut : 0)
    #     epsg (int): EPSG code of the desired projection (default is 2154)
    #     format_vector (str): Format for the output vector file (default is 'ESRI Shapefile')
    #     extension_vector : extension du fichier vecteur de sortie, par defaut = '.shp'
    #     path_time_log : le fichier de log de sortie (par défaut : "")
    #     save_results_intermediate : fichiers de sorties intermediaires non nettoyées, par defaut = False
    #     overwrite : supprime ou non les fichiers existants ayant le meme nom
    """
    # Affichage des paramètres
    if debug >= 3:
        print(bold + green + "Variables dans le processingSLIC - Variables générales" + endC)
        print(cyan + "processingSLIC() : " + endC + "base_folder : " + str(base_folder))
        print(cyan + "processingSLIC() : " + endC + "emprise_vector : " + str(emprise_vector))
        print(cyan + "processingSLIC() : " + endC + "image_input : " + str(image_input))
        print(cyan + "processingSLIC() : " + endC + "raster_oso_input : " + str(raster_oso_input))
        print(cyan + "processingSLIC() : " + endC + "vector_file_seg_output : " + str(vector_file_seg_output))
        print(cyan + "processingSLIC() : " + endC + "optimize : " + str(optimize))
        print(cyan + "processingSLIC() : " + endC + "fixed_struct_params : " + str(fixed_struct_params))
        print(cyan + "processingSLIC() : " + endC + "no_data_value : " + str(no_data_value))
        print(cyan + "processingSLIC() : " + endC + "epsg : " + str(epsg))
        print(cyan + "processingSLIC() : " + endC + "schema_postgis : " + str(schema_postgis) + endC)
        print(cyan + "processingSLIC() : " + endC + "format_vector : " + str(format_vector))
        print(cyan + "processingSLIC() : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "processingSLIC() : " + endC + "path_time_log : " + str(path_time_log))
        print(cyan + "processingSLIC() : " + endC + "save_results_intermediate : "+ str(save_results_intermediate))
        print(cyan + "processingSLIC() : " + endC + "overwrite : "+ str(overwrite))

    SUFFIX_TMP = "_tmp"
    SUFFIX_BUF = "_buf"

    # ------------------------------------------------------------------
    # INITIALISATION DES CHEMINS
    # ------------------------------------------------------------------
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.dirname(vector_file_seg_output)

    # Dossier temporaire où l’on stocke TOUTES les segmentations MCMC
    tmp_dir = os.path.join(output_dir, "tmp")
    os.makedirs(tmp_dir, exist_ok=True)       # tmp/
    os.makedirs(output_dir, exist_ok=True)    # SLIC/test_segmentation/

    # ------------------------------------------------------------------
    # LECTURE DU RASTER RGB
    # ------------------------------------------------------------------
    with rasterio.open(image_input) as src:
        img = src.read()
        transform = src.transform
        crs = src.crs
        pixel_area = abs(transform.a * transform.e)
        width, height = src.width, src.height
        pixel_size = abs(transform.a)

    img = np.transpose(img, (1, 2, 0))

    # Fichier d'emprise
    buffer_dist = 4 * pixel_size
    emprise_vector_tmp = base_folder + os.sep + os.path.splitext(os.path.basename(emprise_vector))[0] + SUFFIX_BUF + extension_vector
    bufferVector(emprise_vector, emprise_vector_tmp, buffer_dist, "", 1.0, 10, format_vector)

    # Fichier temporaire brut
    vector_segmentation_tmp = os.path.splitext(vector_file_seg_output)[0] + SUFFIX_TMP + extension_vector

    # ------------------------------------------------------------------
    # OPTIMISATION MCMC
    # ------------------------------------------------------------------
    global RESULTS
    RESULTS = []

    # ====== MODE OPTIMISÉ ======
    if optimize:
        if debug >= 1:
            print(cyan + "processingSLIC() : " + endC + "Lancement optimisation MCMC...")

        # 1) Marcheurs MCMC
        p0 = [[np.random.uniform(*BOUNDS[name]) for name in PARAM_NAMES]
              for _ in range(NWALKERS)]

        # 2) Shapefile TEMPORAIRE pour l’échantillonneur
        vector_segmentation = os.path.join(
            tmp_dir,  # <-- dossier temporaire !
            os.path.splitext(os.path.basename(vector_file_seg_output))[0]
            + SUFFIX_TMP + extension_vector
        )

        # 3) EnsembleSampler
        sampler = emcee.EnsembleSampler(
            NWALKERS, NDIM, evaluateSegmentationSlic,
            args=[img, vector_segmentation, transform, crs, emprise_vector_tmp,
                  pixel_area, width, height,
                  tmp_dir, raster_oso_input, epsg, no_data_value,
                  format_vector, extension_vector,  # <-- on passe tmp_dir
                  save_results_intermediate]
        )

        # 4) Boucle MCMC
        start = time.time()
        for _ in tqdm(sampler.sample(p0, iterations=NSTEPS), total=NSTEPS):
            pass
        if debug >= 1:
            print(cyan + "processingSLIC() : " + endC + "Durée totale : {} s".format(round(time.time() - start, 2)))

        if not RESULTS:
            if debug >= 1:
                print(cyan + "processingSLIC() : " + endC + "Aucune segmentation valide trouvée.")
            return
        # -------- suite normale

        # RÉCUPÈRE LA MEILLEURE SEGMENTATION
        best = sorted(RESULTS, key=lambda x: x["score"])[0]

        # Sauvegarde des meilleurs paramètres
        text_line = (f"compactness={best['compactness']:.3f}, "
                     f"sigma={best['sigma']:.3f}, "
                     f"area={int(best['target_area'])}, "
                     f"score={best['score']:.4f}\n")
        appendTextFile(os.path.join(output_dir,
                       "meilleures_combinaisons_optimisation_SLIC.txt"),
                       text_line)

        # Fichier vector du meilleur résultat (encore dans tmp/)
        vector_segmentation_tmp = best["vector"]

    # === MODE FIXE (1 seule combinaison testée) ===
    else:
        if debug >= 1:
            print(cyan + "processingSLIC() : " + endC + "Lancement de la segmentation SLIC...")

        compactness = fixed_struct_params["SLIC"]["compactness"][0]
        sigma = fixed_struct_params["SLIC"]["sigma"][0]
        area = fixed_struct_params["SLIC"]["target_area"][0]
        fixed_params_list = [compactness, sigma, area]

        # Vérification des bornes
        for val, param_name in zip(fixed_params_list, PARAM_NAMES):
            low, high = BOUNDS[param_name]
            if not (low <= val <= high):
                print(cyan + "processingSLIC() " + bold + red + "!!! Fin parametre en dehors des clous!!!!" + endC, file=sys.stderr)
                exit()

        # Exécution de SLIC
        slicProcess(
            fixed_params_list,
            img,
            emprise_vector_tmp,
            vector_segmentation_tmp,
            pixel_area,
            width,
            height,
            transform,
            epsg,
            format_vector
        )

    # Post traitement lissage et découpage de la segmentation
    # Lissage de la segmentation bute
    vector_file_seg_tmp = os.path.join(tmp_dir, "segmentation_lissee_tmp.shp")
    smoothingGeometry(emprise_vector_tmp, vector_segmentation_tmp, vector_file_seg_tmp, epsg, format_vector, extension_vector, save_results_intermediate)

    # Découpage sur l'emprise
    cutVectorAll(emprise_vector, vector_file_seg_tmp, vector_file_seg_output, save_results_intermediate, format_vector)

    # Nettoyage du fichier temporaire
    if not save_results_intermediate :
        if os.path.isfile(emprise_vector_tmp) :
            removeVectorFile(emprise_vector_tmp)
        if os.path.isfile(vector_file_seg_tmp) :
            removeVectorFile(vector_file_seg_tmp)
        if os.path.exists(vector_segmentation_tmp):
            removeVectorFile(vector_segmentation_tmp, format_vector)
        if os.path.isdir(tmp_dir):
            shutil.rmtree(tmp_dir, ignore_errors=True)

    if debug >= 1:
        print(cyan + "processingSLIC() : " + endC + "Fichier lissé généré : {}".format(vector_file_seg_output))

    return

###########################################################################################################################################
# MAIN EXECUTION                                                                                                                          #
###########################################################################################################################################
if __name__ == "__main__":

    ##### Paramètres en entrée #####
    """
    BASE_FOLDER = "/mnt/RAM_disk/INTEGRATION"
    emprise_vector = "/mnt/RAM_disk/INTEGRATION/emprise/Emprise_Toulouse.shp"
    rgb_file_input = "/mnt/RAM_disk/INTEGRATION/create_data/result/pseudoRGB_output.tif"
    raster_oso_input = "/mnt/RAM_disk/INTEGRATION/create_data/result/OCS_2023_cut.tif"
    vector_file_seg_output = "/mnt/RAM_disk/INTEGRATION/segmentation_SLIC_Toulouse.shp"
    """
    BASE_FOLDER = "/mnt/RAM_disk/ToulouseMetropole"
    emprise_vector = "/mnt/RAM_disk/ToulouseMetropole/emprise/Emprise_Toulouse.shp"
    rgb_file_input = "/mnt/RAM_disk/ToulouseMetropole/create_data/result/pseudoRGB_seg_res5.tif"
    raster_oso_input = "/mnt/RAM_disk/ToulouseMetropole/create_data/result/pseudoRGB_seg_res5.tif"
    vector_file_seg_output = "/mnt/RAM_disk/ToulouseMetropole/segmentation_SLIC_Toulouse.shp"

    #################################

    processingSLIC(
        base_folder=BASE_FOLDER,
        emprise_vector=emprise_vector,
        image_input=rgb_file_input,
        raster_oso_input=raster_oso_input,
        vector_file_seg_output=vector_file_seg_output,
        optimize=False,
        fixed_struct_params = DEFAULT_PARAMETERS_SLIC,
        no_data_value=0,
        epsg=2154,
        format_vector='ESRI Shapefile',
        extension_vector=".shp",
        path_time_log="",
        save_results_intermediate=False,
        overwrite=True
    )
