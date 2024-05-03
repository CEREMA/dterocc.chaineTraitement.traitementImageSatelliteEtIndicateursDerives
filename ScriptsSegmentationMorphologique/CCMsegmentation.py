#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT QUI SEGMENTE UNE IMAGE RGB AVEC L'ALGORITHME DE SEGMENTATION SUPERPIXEL CCM (CONVEX CONSTRAINED MESH)                              #
#                                                                                                                                           #
#############################################################################################################################################

"""
Nom de l'objet : CCMsegmentation.py
Description :
    Objectif : Créer un maillage de polygones au format vecteur réprésentant la segmentation morphologique de l'image pseudo RGB d'entrée

Date de creation : 02/10/2023
----------
Histoire :
----------
Origine : Ce script a été réalisé par Levis Antonetti dans le cadre de son stage sur la segmentation morphologique du tissu urbain (Tuteurs: Aurélien Mure, Gilles Fouvet).
          Ce script est le résultat de la synthèse du développement effectué sur des notebooks disponibles dans le répertoire /mnt/Data2/30_Stages_Encours/2023/MorphologieUrbaine_Levis/03_scripts
-----------------------------------------------------------------------------------------------------
Modifications

------------------------------------------------------
"""

##### Import #####

# System
import os, subprocess, shutil, math

# Data processing
import numpy as np
import pandas as pd
from skimage import io

import openmesh as om

# Geomatique
import geopandas as gpd
import shapely.geometry as shg

# Intern libs
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC
from Lib_raster import getEmpriseImage

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 3 : affichage maximum de commentaires lors de l'execution du script. Intermédiaire : affichage intermédiaire
debug = 1

# paramètres par défaut de la segmentation CCM
DICT_CCM_DEFAULT_PAPER_PARAMETERS = {
    'CCM': {
        'epsilon': [3.0],
        'min_angle': [20]
    },
    'LSD': {
        'sigma_scale': [0.7],
        'quant': [2.0],
        'ang_th': [45],
        'log_eps': [0.0],
        'density_th': [0.7],
        'n_bins': [1024]
    }
}

# For Grid search on Toulouse Métropole !!!
DICT_CCM_BEST_PARAMETERS = {
    'CCM': {
        'epsilon': [3.0],
        'min_angle': [40]
    },
    'LSD': {
        'sigma_scale': [0.9],
        'quant': [4.0],
        'ang_th': [45],
        'log_eps': [0.1],
        'density_th': [0.3],
        'n_bins': [1024]
    }
}

###########################################################################################################################################
#                                                                                                                                         #
# UTILS                                                                                                                                   #
#                                                                                                                                         #
###########################################################################################################################################

###########################################################################################################################################
# FUNCTION getFileByExtensionList()                                                                                                       #
###########################################################################################################################################
def getFileByExtensionList(directory_path, extensions_list):
    """
    # ROLE:
    #     retrieve file names with specific extensions in a directory and return them in a list.
    #
    # PARAMETERS:
    #     directory_path (str): path to the directory where files will be searched.
    #     extensions_list (list of str): list of file extensions to filter by (e.g., [".txt", ".shp"]).
    #
    # RETURNS:
    #     file_list (list of str): list of file names that match the specified extensions.
    #
    # EXAMPLE:
    #     file_list = getFileByExtensionList("/path/to/directory", [".txt", ".shp"])
    #
    """

    file_list = []
    for file_tmp in os.listdir(directory_path):
        for extension in extensions_list:
            if file_tmp.endswith(extension): #### TO COMPLETE
                file_list.append(directory_path + os.sep + file_tmp)
    return file_list

###########################################################################################################################################
# FUNCTION cutShapefileByExtent()                                                                                                         #
###########################################################################################################################################
def cutShapefileByExtent(vector_cut, vector_input, vector_output, epsg=2154, format_vector='ESRI Shapefile'):
    """
    # ROLE:
    #     Cut a shapefile by the extent of another shapefile and save the result.
    #
    # PARAMETERS:
    #     vector_cut (str): the vector file used for cutting.
    #     vector_input (str): the input vector file  to be cut.
    #     vector_output (str): the output vector file  containing the clipped features.
    #     epsg (int): EPSG code of the desired projection (default is 2154).
    #     format_vector (str): Format for the output vector file (default is 'ESRI Shapefile').
    #
    # RETURNS:
    #     None
    #
    # EXAMPLE:
    #     cut_shapefile_by_extent('input.shp', 'extent.shp', 'output.shp', 2154)
    #
    """

    crs = "EPSG:" + str(epsg)
    input_gdf = gpd.read_file(vector_input)
    extent_gdf = gpd.read_file(vector_cut).to_crs(crs)
    extent_gdf = extent_gdf.drop(columns=extent_gdf.columns.difference(['geometry']))

    # Clip the input shapefile by the extent shapefile
    clipped_gdf = gpd.overlay(input_gdf, extent_gdf, how='intersection', keep_geom_type=True)

    # Save the clipped shapefile to the output file
    clipped_gdf.to_file(vector_output, crs=crs, driver=format_vector)
    return

###########################################################################################################################################
# FUNCTION ConvertImage2png()                                                                                                             #
###########################################################################################################################################
def ConvertImage2png(file_image_input, png_image_output):
    """
    # ROLE:
    #     Convert an image to PNG format.
    #
    # PARAMETERS:
    #     file_image_input (str): path to the image file to be converted.
    #     png_image_output (str): path to the converted PNG image file.
    #
    # RETURNS:
    #     NA.
    #
    # EXAMPLE:
    #     path_png = ConvertImage2png("/path/input_image.tif", "/path/input_image.png")
    #
    """

    img_input = io.imread(file_image_input)
    if debug >= 1:
        print(cyan + "ConvertImage2png() : " + endC + "image shape {}".format(img_input.shape))
    io.imsave(png_image_output, img_input)

    if debug >= 1:
        print(cyan + "ConvertImage2png() : " + endC + 'image {} converted to png into {}'.format(file_image_input, png_image_output))
    return

###########################################################################################################################################
#                                                                                                                                         #
# Segmentation CONVEX CONSTRAINED MESH                                                                                                    #
#                                                                                                                                         #
###########################################################################################################################################

###########################################################################################################################################
# FUNCTION processSegmentationCCM()                                                                                                       #
###########################################################################################################################################
def processSegmentationCCM(CCM_repository, img_png_file, dict_ccm_parameters, path_folder_output):
    """
    # ROLE:
    #     Perform image segmentation using the CCM algorithm.
    #
    # PARAMETERS:
    #     CCM_repository (str): path to the CCM repository containing CCM source code.
    #     img_png_file (str): the input PNG image file for segmentation.
    #     dict_ccm_parameters (dict): dictionary containing CCM algorithm parameters.
    #     path_folder_output (str): path to the folder where CCM segmentation results will be saved.
    #
    # RETURNS:
    #     None
    #
    # EXAMPLE:
    #     processSegmentationCCM("/CCM_repository",
    #                   "input_image.png",
    #                   {"CCM": {"min_angle": [5, 10], "epsilon": [0.1, 0.2]},
    #                   "LSD": {"sigma_scale": [0.6, 0.8], "quant": [0.4, 0.5],
    #                            "ang_th": [22.5, 30.0], "log_eps": [1e-6, 1e-5],
    #                            "density_th": [300, 400], "n_bins": [16, 32]}},
    #                   "/CCM_output_folder")
    #
    """
    # Constantes extensions
    PNG_EXT = ".png"
    OFF_EXT = ".off"

    if debug >= 1:
     print(cyan + "processSegmentationCCM() : " + endC + "build and compile CCM project from {} ...".format(CCM_repository))

    # Build and compile CCM project to use CCM c++ script
    CCM_build_directory = os.path.join(CCM_repository, "build")
    if debug >= 1:
        print(cyan + "processSegmentationCCM() : " + endC + "CMAKE ...")
    subprocess.run(["cmake", ".."], cwd=CCM_build_directory, check=True)
    if debug >= 1:
        print(cyan + "processSegmentationCCM() : " + endC + "CMAKE done successfully\n")
        print(cyan + "processSegmentationCCM() : " + endC + "MAKE")
    subprocess.run(["make"], cwd=CCM_build_directory, check=True)
    if debug >= 1:
        print(cyan + "processSegmentationCCM() : " + endC + "MAKE done successfully\n")
        print(cyan + "processSegmentationCCM() : " + endC + "execution of CCM segmentation...")
    for min_angle in dict_ccm_parameters["CCM"]["min_angle"]:
        for epsilon in dict_ccm_parameters["CCM"]["epsilon"]:
            for sigma_scale in dict_ccm_parameters["LSD"]["sigma_scale"]:
                for quant in dict_ccm_parameters["LSD"]["quant"]:
                    for ang_th in dict_ccm_parameters["LSD"]["ang_th"]:
                        for log_eps in dict_ccm_parameters["LSD"]["log_eps"]:
                            for density_th in dict_ccm_parameters["LSD"]["density_th"]:
                                for n_bins in dict_ccm_parameters["LSD"]["n_bins"]:
                                    seg_command = ["CCM",
                                    img_png_file,
                                    str(math.radians(min_angle)),
                                    str(epsilon), str(sigma_scale),
                                    str(quant), str(ang_th),
                                    str(log_eps), str(density_th),
                                    str(n_bins), path_folder_output + os.sep]
                                    # Command qui effectue la segmentation
                                    if debug >= 3:
                                        print(cyan + "processSegmentationCCM() : " + endC + "CCM COMMAND:", " ".join(seg_command))
                                    subprocess.run(seg_command, cwd=CCM_build_directory, check=True, text=True)

    # récupération des fichiers de sorties .png et .off
    png_files_list = getFileByExtensionList(path_folder_output, [PNG_EXT])
    off_files_list = getFileByExtensionList(path_folder_output, [OFF_EXT])

    if debug >= 1:
        print(cyan + "processSegmentationCCM() : " + endC + "CCM segmentation done to {}\n".format(path_folder_output))
    return png_files_list[0], off_files_list[0]

###########################################################################################################################################
# FUNCTION mesh2Gdf()                                                                                                                     #
###########################################################################################################################################
def mesh2Gdf(mesh, image_input, file_vector_out, scale=5, epsg=2154, format_vector='ESRI Shapefile'):
    """
    # ROLE:
    #     Convert a mesh into a GeoDataFrame and save it as a shapefile.
    #
    # PARAMETERS:
    #     mesh: input mesh object to convert.
    #     image_input (str): path to the input image used to define the extent.
    #     file_vector_out (str output vector file where the GeoDataFrame will be saved.
    #     scale (int): scaling factor to apply to mesh coordinates (default is 5).
    #     epsg (int): EPSG code of the desired projection (default is 2154).
    #     format_vector (str): Format for the output vector file (default is 'ESRI Shapefile').
    #
    # RETURNS:
    #     None
    #
    # EXAMPLE:
    #     mesh2Gdf(mesh_object, "input_image.png", "output_shapefile.shp", scale=10, epsg=4326, format_vector="GPKG")
    #
    """

    # Récupération de l'emprise de l'image d'origine
    xmin, xmax, ymin, ymax = getEmpriseImage(image_input)
    raw_img = io.imread(image_input)

    # Create list of polygons from mesh
    list_polygon_geom = []
    for face in mesh.faces():
        all_face_coords = []
        for vh in mesh.fv(face):
            face_coords = mesh.point(vh)[0], -mesh.point(vh)[1] + raw_img.shape[0]
            face_coords = (xmin + (face_coords[0]*scale), ymin + (face_coords[1]*scale))
            all_face_coords.append(face_coords)
        all_face_coords = np.array(all_face_coords)

        polygon_geom = shg.Polygon(all_face_coords)
        list_polygon_geom.append(polygon_geom)
    crs = "EPSG:" + str(epsg)
    df = gpd.GeoDataFrame(crs=crs, geometry=list_polygon_geom)
    df.to_file(file_vector_out, driver=format_vector, crs=crs)
    return

###########################################################################################################################################
# FUNCTION offFile2vectorFile()                                                                                                            #
###########################################################################################################################################
def offFile2vectorFile(off_file_input, rgb_file_input, vector_file_output, resolution=5, epsg=2154, format_vector='ESRI Shapefile', extension_vector=".shp"):
    """
    # ROLE:
    #     Export objects in .off format to vector file.
    #
    # PARAMETERS:
    #     off_file_input (str): the off file representing objects.
    #     rgb_file_input (str): the input RGB image used to define the extent.
    #     vector_file_output (str): the vector file output.
    #     resolution( int): resolution forcé des rasters de travail (par défaut : 5).
    #     epsg (int): EPSG code of the desired projection (default is 2154).
    #     format_vector (str): Format for the output vector file (default is 'ESRI Shapefile').
    #     extension_vector : extension du fichier vecteur de sortie, par defaut = ".shp".
    #
    # RETURNS:
    #    None
    #
    # EXAMPLE:
    #     offFile2vectorFile(["object1.off", "object2.off"], "input_image.png", "output_shapefiles_folder/")
    #
    """

    if debug >= 1:
        print(cyan + "offFile2vectorFile() : " + endC + "exporting .off objects from {} to vector file...".format(off_file_input))

    # Get mesh object
    mesh = om.read_polymesh(off_file_input)

    # Print mesh info
    if debug >= 3:
        print(cyan + "offFile2vectorFile() : " + endC + "{}\t-->\t{}".format(off_file_input, "{} edges | {} faces | {} vertices | {} halfedges".format(mesh.n_edges(), mesh.n_faces(), mesh.n_vertices(), mesh.n_halfedges())))

    # Export mesh to geodataframe
    mesh2Gdf(mesh, rgb_file_input, vector_file_output, scale=resolution, epsg=epsg, format_vector=format_vector)

    if debug >= 1:
        print(cyan + "offFile2vectorFile() : " + endC + "exporting .off objects to vector file into {} done".format(vector_file_output))
    return

###########################################################################################################################################
# FUNCTION processingCCM()                                                                                                                #
###########################################################################################################################################
def processingCCM(path_base_folder, emprise_vector, rgb_file_input, vector_file_seg_output, CCM_repository, dict_ccm_parameters, resolution=5, no_data_value=0, epsg=2154, format_raster="GTiff", format_vector='ESRI Shapefile', extension_raster=".tif", extension_vector=".shp", path_time_log = "", save_results_intermediate=False, overwrite=True):
    """
    # ROLE:
    #     Perform CCM segmentation on an input RGB image and export the results to a specified folder.
    #
    # PARAMETERS:
    #     path_base_folder (str): base directory where the CCM process and results will be stored.
    #     emprise_vector (str): fichier d'emprise.
    #     rgb_file_input (str): the input RGB image to be segmented.
    #     vector_file_seg_output (str): the output vector result of segmentation.
    #     CCM_repository (str): path to the CCM repository containing the CCM C++ script.
    #     dict_ccm_parameters (dict): dictionary containing CCM segmentation parameters.
    #     resolution( int): resolution forcé des rasters de travail (par défaut : 5).
    #     no_data_value : Option : Value pixel of no data (par défaut : 0).
    #     epsg (int): EPSG code of the desired projection (default is 2154).
    #     format_raster (str): Format de l'image de sortie (déeaut GTiff)
    #     format_vector (str): Format for the output vector file (default is 'ESRI Shapefile').
    #     extension_raster : extension des fichiers raster de sortie, par defaut = '.tif'
    #     extension_vector : extension du fichier vecteur de sortie, par defaut = '.shp'
    #     path_time_log : le fichier de log de sortie (par défaut : "").
    #     save_results_intermediate : fichiers de sorties intermediaires non nettoyées, par defaut = False
    #     overwrite : supprime ou non les fichiers existants ayant le meme nom
    #
    # RETURNS:
    #     None
    #
    # EXAMPLE:
    #     processingCCM("/base_folder/", "input_image.png", "/CCM_repository/", {"CCM": {"min_angle": [30], "epsilon": [0.02]},
    #                   "LSD": {"sigma_scale": [0.8], "quant": [2], "ang_th": [22.5], "log_eps": [0.0], "density_th": [500], "n_bins": [1024]}}, "/result_folder/")
    #
    """

    # Affichage des paramètres
    if debug >= 3:
        print(bold + green + "Variables dans le processingCCM - Variables générales" + endC)
        print(cyan + "processingCCM() : " + endC + "path_base_folder : " + str(path_base_folder))
        print(cyan + "processingCCM() : " + endC + "emprise_vector : " + str(emprise_vector))
        print(cyan + "processingCCM() : " + endC + "rgb_file_input : " + str(rgb_file_input))
        print(cyan + "processingCCM() : " + endC + "vector_file_seg_output : " + str(vector_file_seg_output))
        print(cyan + "processingCCM() : " + endC + "CCM_repository : " + str(CCM_repository))
        print(cyan + "processingCCM() : " + endC + "dict_ccm_parameters : " + str(dict_ccm_parameters))
        print(cyan + "processingCCM() : " + endC + "resolution : " + str(resolution))
        print(cyan + "processingCCM() : " + endC + "no_data_value : " + str(no_data_value))
        print(cyan + "processingCCM() : " + endC + "epsg : " + str(epsg))
        print(cyan + "processingCCM() : " + endC + "format_raster : " + str(format_raster))
        print(cyan + "processingCCM() : " + endC + "format_vector : " + str(format_vector))
        print(cyan + "processingCCM() : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "processingCCM() : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "processingCCM() : " + endC + "path_time_log : " + str(path_time_log))
        print(cyan + "processingCCM() : " + endC + "save_results_intermediate : "+ str(save_results_intermediate))
        print(cyan + "processingCCM() : " + endC + "overwrite : "+ str(overwrite))

    # Constantes pour la création automatique de fichiers temporaires et provisoires
    FOLDER_CCM = "ccm"
    FOLDER_INPUT = "input"
    FOLDER_OUTPUT = "output"
    FOLDER_RESULT = "result"

    # Constantes
    PNG_EXT = ".png"

    # Create folders
    path_folder_input = path_base_folder + os.sep+ FOLDER_CCM + os.sep + FOLDER_INPUT
    if not os.path.exists(path_folder_input):
        os.makedirs(path_folder_input)

    path_folder_output = path_base_folder + os.sep+ FOLDER_CCM + os.sep + FOLDER_OUTPUT
    if not os.path.exists(path_folder_output):
        os.makedirs(path_folder_output)

    path_folder_result = path_base_folder + os.sep+ FOLDER_CCM + os.sep + FOLDER_RESULT
    if not os.path.exists(path_folder_result):
        os.makedirs(path_folder_result)

    if debug >= 1:
        print(cyan + "processingCCM() : " + endC + "copy of file {} to {} done".format(rgb_file_input, rgb_file_input))

    # Convert input file .tif to .png
    file_image_png = path_folder_input + os.sep + os.path.splitext(os.path.basename(rgb_file_input))[0] + PNG_EXT
    ConvertImage2png(rgb_file_input, file_image_png)

    # Application de l'algo de traitement CCM et récupération des fichiers .png et .off dans le répertoire de sortie
    image_png_output, file_off_output = processSegmentationCCM(CCM_repository, file_image_png, dict_ccm_parameters, path_folder_output)

    # Convertir le fichier .off en fichier vecteur .shp avec l'object mesh (la segmentation de polygones)
    vector_file_tmp = path_folder_output + os.sep + os.path.splitext(os.path.basename(image_png_output))[0] + extension_vector
    offFile2vectorFile(file_off_output, rgb_file_input, vector_file_tmp, resolution, epsg, format_vector, extension_vector)

    # Cut vector file by emprise
    if debug >= 1:
        print(cyan + "processingCCM() : " + endC + "cutting result file  {} by emprise...".format(vector_file_tmp))

    cutShapefileByExtent(emprise_vector, vector_file_tmp, vector_file_seg_output, epsg, format_vector)

    if debug >= 1:
        print(cyan + "processingCCM() : " + endC + "cutting done to {}\n".format(vector_file_seg_output))

    return

# ==================================================================================================================================================

if __name__ == '__main__':

    ##### paramètres en entrées #####
    # Il est recommandé de prendre un répertoire avec accès rapide en lecture et écriture pour accélérer les traitements
    BASE_FOLDER = "/mnt/RAM_disk/INTEGRATION"
    emprise_vector = "/mnt/RAM_disk/INTEGRATION/emprise/Emprise_Toulouse_Metropole.shp"
    rgb_file_input = "/mnt/RAM_disk/INTEGRATION/create_data/result/pseudoRGB_input_seg_res5.tif"
    vector_file_seg_output = "/mnt/RAM_disk/INTEGRATION/ccm/result/segmentation_result.shp"
    CCM_repository = "/home/scgsi/CCM"

    # Example dictionnaire de paramètres pour une recherche paramétrique
    ##dict_ccm_parameters = DICT_CCM_DEFAULT_PAPER_PARAMETERS
    dict_ccm_parameters = DICT_CCM_BEST_PARAMETERS # TODO modify if needed

    # Exec
    processingCCM(
        BASE_FOLDER,
        emprise_vector,
        rgb_file_input,
        vector_file_seg_output,
        CCM_repository,
        dict_ccm_parameters,
        resolution=5,
        no_data_value=0,
        epsg=2154,
        format_raster="GTiff",
        format_vector='ESRI Shapefile',
        extension_raster=".tif",
        extension_vector=".shp",
        path_time_log="",
        save_results_intermediate=False,
        overwrite=True
    )
