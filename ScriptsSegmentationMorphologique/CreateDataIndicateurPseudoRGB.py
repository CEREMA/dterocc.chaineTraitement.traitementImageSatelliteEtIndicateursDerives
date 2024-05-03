#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT QUI CREER UNE PSEUDO IMAGE RGB À PARTIR D'INDICATEURS SPECIFIES                                                                    #
#                                                                                                                                           #
#############################################################################################################################################

"""
Nom de l'objet : CreateDataIndicateurPseudoRGB.py
Description :
    Objectif : Créer une image pseudo-RGB à partir d'indicateurs d'impermeabilités, de végétations et de routes qui servira ensuite comme image d'entrée pour la segmentation morphologique du tissu urbain

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
import os, sys, subprocess, shutil

# Data processing
import pandas as pd
import geopandas as gpd
from PIL import Image

# Geomatique
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.crs import CRS

# Intern libs
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC
from Lib_raster import cutImageByVector, getProjectionImage, rasterizeBinaryVector, rasterizeVector, mergeListRaster, getEmpriseImage, setNodataValueImage
from Lib_vector import fusionVectors, bufferVector, filterSelectDataVector, getAttributeNameList
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan, endC
from Lib_file import deleteDir, copyVectorFile, copyFile
from ChannelsConcatenation import concatenateChannels

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 3 : affichage maximum de commentaires lors de l'execution du script. Intermédiaire : affichage intermédiaire
debug = 1

###########################################################################################################################################
#                                                                                                                                         #
# UTILS                                                                                                                                   #
#                                                                                                                                         #
###########################################################################################################################################

###########################################################################################################################################
# FUNCTION reprojectRaster()                                                                                                              #
###########################################################################################################################################
def reprojectRaster(input_file, output_file, src_epsg, dst_epsg):
    """
    # ROLE:
    #     Reprojects a GeoTIFF file from the source coordinate reference system (CRS) to the destination CRS.
    #
    # PARAMETERS:
    #     input_file (str): Path to the input GeoTIFF file to be reprojected.
    #     output_file (str): Path to the output GeoTIFF file where the reprojected data will be saved.
    #     src_epsg (int): EPSG code or the source CRS of the input GeoTIFF.
    #     dst_epsg (int): EPSG code or the destination CRS to which the input GeoTIFF will be reprojected.
    #
    # RETURNS:
    #     None
    #
    # EXAMPLE:
    #     reprojectRaster('input.tif', 'output.tif', 4326, 2154)
    #
    """

    src_crs = CRS.from_epsg(src_epsg)
    dst_crs = CRS.from_epsg(dst_epsg)

    with rasterio.open(input_file) as src:
        transform, width, height = calculate_default_transform(src_crs, dst_crs, src.width, src.height, *src.bounds)

        kwargs = src.meta.copy()
        kwargs.update({
            'crs': dst_crs,
            'transform': transform,
            'width': width,
            'height': height
        })

        with rasterio.open(output_file, 'w', **kwargs) as dst:
            reproject(
                source=rasterio.band(src, 1),
                destination=rasterio.band(dst, 1),
                src_transform=src.transform,
                src_crs=src_crs,
                dst_transform=transform,
                dst_crs=dst_crs,
                resampling=Resampling.nearest
            )
    return

###########################################################################################################################################
# FUNCTION reprojectVector()                                                                                                              #
###########################################################################################################################################
def reprojectVector(vector_input, vector_output, epsg=2154, format_vector='ESRI Shapefile'):
    """
    # ROLE:
    #     Update the projection of a GeoDataFrame and save it to a new file.
    #
    # PARAMETERS:
    #     vector_input (str): Path to the input GeoDataFrame file.
    #     vector_output (str): Path to the output GeoDataFrame file with the updated projection.
    #     epsg (int): EPSG code of the desired projection (default is 2154).
    #     format_vector (str): Format for the output vector file (default is 'ESRI Shapefile').
    #
    # RETURNS:
    #     None
    #
    # EXAMPLE:
    #     reprojectVector('input.shp', 'output.shp', 4326, 'ESRI Shapefile')
    #
    """

    gdf = gpd.read_file(vector_input)
    # Sauvegardez le GeoDataFrame avec la nouvelle projection dans un fichier de sortie
    gdf.to_file(vector_output, crs="EPSG:" + str(epsg), driver=format_vector)
    return

###########################################################################################################################################
# FUNCTION cutShapefileByExtent()                                                                                                         #
###########################################################################################################################################
def cutShapefileByExtent(emprise_vector, input_shapefile, output_shapefile, epsg=2154, format_vector='ESRI Shapefile'):
    """
    # ROLE:
    #     Cut a shapefile by the extent of another shapefile and save the result.
    #
    # PARAMETERS:
    #     extent_shapefile (str): Path to the extent shapefile used for cutting.
    #     input_shapefile (str): Path to the input shapefile to be cut.
    #     output_shapefile (str): Path to the output shapefile containing the clipped features.
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
    input_gdf = gpd.read_file(input_shapefile)
    extent_gdf = gpd.read_file(emprise_vector).to_crs(crs)

    # Clip the input shapefile by the extent shapefile
    clipped_gdf = gpd.overlay(input_gdf, extent_gdf, how='intersection', keep_geom_type=True)

    # Save the clipped shapefile to the output file
    clipped_gdf.to_file(output_shapefile, crs=crs, driver=format_vector)

    return

###########################################################################################################################################
# FUNCTION gdfFusionVectors()                                                                                                             #
###########################################################################################################################################
def gdfFusionVectors(vectors_list, vector_all, format_vector, epsg=2154):
    """
    # ROLE:
    #    Fusion d'une fiste de vecteur avec geoPandas.
    #
    # PARAMETERS:
    #     vectors_list : liste des vecteur à fusionnés.
    #     vector_all : le vecteur fusionné.
    #     epsg (int): EPSG code of the desired projection (default is 2154).
    # RETURNS:
    #     le vecteur fusionné
    """

    gdf_vector_list = [gpd.read_file(vector_tmp) for vector_tmp in vectors_list]
    gdf_vector_all = gpd.GeoDataFrame(pd.concat(gdf_vector_list))
    gdf_vector_all.to_file(vector_all, driver=format_vector, crs="EPSG:"+str(epsg))

    return vector_all

###########################################################################################################################################
# FUNCTION filterVectorsSql()                                                                                                             #
###########################################################################################################################################
def filterVectorSql(vector_input_list, vector_output_list, sql_expression_list, format_vector='ESRI Shapefile'):
    """
    # ROLE:
    #     Reprojects a GeoTIFF file from the source coordinate reference system (CRS) to the destination CRS.
    #
    # PARAMETERS:
    #     vector_input (list): Liste de fichier vecteur d'entrée à filtrer.
    #     vector_outpout (list): Liste de fichier vecteur de sortie filtré par l'expression sql.
    #     sql_expression_list (list): Liste d'expression sql pour le filtrage des fichiers vecteur de bd exogenes.
    #     format_vector (str): Format for the output vector file (default is 'ESRI Shapefile').
    #
    # RETURNS:
    #     None
    #
    """

    if debug >= 1:
        print(cyan + "filterVectorSql() : " + endC + "Filtrage SQL BD input...")

    if sql_expression_list != [] :
        for idx_vector in range (len(vector_input_list)):
            vector_input = vector_input_list[idx_vector]
            vector_filtered = vector_output_list[idx_vector]

            if idx_vector < len(sql_expression_list) :
                sql_expression = sql_expression_list[idx_vector]
            else :
                sql_expression = ""

            # Filtrage par ogr2ogr
            if sql_expression != "":
                names_attribut_list = getAttributeNameList(vector_input, format_vector)
                column = "'"
                for name_attribut in names_attribut_list :
                    column += name_attribut + ", "
                column = column[0:len(column)-2]
                column += "'"
                ret = filterSelectDataVector(vector_input, vector_filtered, column, sql_expression, format_vector)
                if not ret :
                    print(cyan + "filterVectorSql() : " + bold + yellow + "Attention problème lors du filtrage des BD vecteurs l'expression SQL %s est incorrecte" %(sql_expression) + endC)
                    copyVectorFile(vector_input, vector_filtered)
            else :
                print(cyan + "filterVectorSql() : " + bold + yellow + "Pas de filtrage sur le fichier du nom : " + endC + vector_filtered)
                copyVectorFile(vector_input, vector_filtered)

    return

###########################################################################################################################################
#                                                                                                                                         #
# CREATE IMAGE PSEUDO RGB WITH INDICATEURS DATA                                                                                           #
#                                                                                                                                         #
###########################################################################################################################################

###########################################################################################################################################
# FONCTION reprojectAndCutRaster()                                                                                                        #
###########################################################################################################################################
def reprojectAndCutRaster(emprise_vector, file_raster_input, file_raster_output, resolution, no_data_value=0, epsg=2154, format_raster='GTiff', format_vector='ESRI Shapefile', save_results_intermediate=False):
    """
    # ROLE:
    #     Reprojects and cuts raster files in a given folder based on a specified extent.
    #
    # PARAMETERS:
    #     emprise_vector (str): vector file representing the geographic extent for cutting.
    #     file_raster_input (str): path to the raster to be processed.
    #     file_raster_output (str): path to the raster output reproj and cut.
    #     resolution( int): resolution forcé des rasters de travail.
    #     no_data_value : Option : Value pixel of no data (par défaut : 0).
    #     epsg (int): EPSG code of the desired projection (default is 2154).
    #     format_raster (str): Format de l'image de sortie (défaut GTiff)
    #     format_vector (str): Format for the output vector file (default is 'ESRI Shapefile').
    #     save_results_intermediate : (boolean): supprime les fichiers temporaires si True, (defaut = False).
    #
    # RETURNS:
    #     NA
    #
    # EXAMPLE:
    #     reprojectAndCutRaster(emprise_vector, path_file_raster_input, path_file_raster_output, epsg=2154)
    #
    """

    # Constante
    FOLDER_TMP = "temp"

    # Create projection and cut results folder if not exist
    path_folder_raster = os.path.dirname(file_raster_output)
    path_folder_tmp = path_folder_raster + os.sep + FOLDER_TMP
    filename_raster = os.path.splitext(os.path.basename(file_raster_input))[0]
    raster_proj = path_folder_tmp +  os.sep + filename_raster +  "_" + str(epsg) + os.path.splitext(file_raster_output)[1].lower()
    if not os.path.exists(path_folder_tmp):
        os.makedirs(path_folder_tmp)

    if debug >= 1:
        print(cyan + "reprojectAndCutRaster() : " + endC + "reprojecting and cutting raster file...")

    # Reprojection
    proj_src,_ = getProjectionImage(file_raster_input)
    reprojectRaster(file_raster_input, raster_proj, proj_src, epsg)

    # Cut
    cutImageByVector(emprise_vector, raster_proj, file_raster_output, pixel_size_x=resolution, pixel_size_y=resolution, in_line=False, no_data_value=no_data_value, epsg=epsg, format_raster=format_raster, format_vector=format_vector)

    # Supression des fichiers temporaires
    if not save_results_intermediate:
        if os.path.exists(path_folder_tmp):
            deleteDir(path_folder_tmp)

    # End
    if debug >= 1:
        print()
        print(cyan + "reprojectAndCutRaster() : " + endC + "reprojecting and cutting done to {} and {}\n".format(file_raster_input, file_raster_output))

    return

###########################################################################################################################################
# FONCTION reprojectAndCutVector()                                                                                                       #
###########################################################################################################################################
def reprojectAndCutVector(emprise_vector, vector_input, vector_output, epsg=2154, format_vector='ESRI Shapefile', save_results_intermediate=False):
    """
    # ROLE:
    #     Reprojects and cuts vector files in a given folder based on a specified extent.
    #
    # PARAMETERS:
    #     path_folder_vectors (str): path to the folder containing the vector files to be processed.
    #     emprise_vector (str): vector file representing the geographic extent for cutting.
    #     vector_input (str): path to the vector file to be processed.
    #     vector_output (str): path to the vector file output reproj and cut.
    #     epsg (int): projection to use for vector reprojection (default is 2154).
    #     save_results_intermediate (boolean): supprime ou non les fichiers temporaires si True (default=False).
    #
    # RETURNS:
    #     NA
    #
    # EXAMPLE:
    #     reprojectAndCutVector(emprise_vector, path_file_vector_input, path_file_vector_output, epsg=2154)
    #
    """

    # Constante
    FOLDER_TMP = "temp"

    # Create projection and cut results folder if not exist
    path_folder_vector = os.path.dirname(vector_output)
    path_folder_tmp = path_folder_vector + os.sep + FOLDER_TMP
    filename_vector = os.path.splitext(os.path.basename(vector_input))[0]
    vector_proj = path_folder_tmp + os.sep + filename_vector +  "_" + str(epsg) + os.path.splitext(vector_output)[1].lower()
    if not os.path.exists(path_folder_tmp):
        os.makedirs(path_folder_tmp)

    if debug >= 1:
        print(cyan + "reprojectAndCutVector() : " + endC + "reprojecting and cutting vector file...")

    # Reprojection
    reprojectVector(vector_input, vector_proj, epsg, format_vector)

    # Cut
    cutShapefileByExtent(emprise_vector, vector_proj, vector_output, epsg, format_vector)

    # Supression des fichiers temporaires
    if not save_results_intermediate:
        if os.path.exists(path_folder_tmp):
            deleteDir(path_folder_tmp)

    # End
    if debug >= 1:
        print(cyan + "reprojectAndCutVector() : " + endC + "reprojecting and cutting done to {} and {}\n".format(vector_input, vector_output))

    return

###########################################################################################################################################
# FUNCTION minMaxScalingChannels()                                                                                                        #
###########################################################################################################################################
def minMaxScalingChannels(raster_files_to_scale_list, raster_files_norm_list, new_min=0, new_max=255):
    """
    # ROLE:
    #     Applies Min-Max scaling to image channels in liste file and saves the results in output list file.
    #
    # PARAMETERS:
    #     raster_files_to_scale_list (list (str)): List of file to the input images to be scaled.
    #     raster_files_norm_list ((list (str)): Liste of output file naramlized
    #     new_min (int): Target minimum value after scaling (default: 0).
    #     new_max (int): Target maximum value after scaling (default: 255).
    #
    # RETURNS:
    #     NA.
    #
    # EXAMPLE:
    #     minMaxScalingChannels(["/path/to/input/folder/file_input.tif"], ["/path/to/output/folder/file_output.tif"], new_min=0, new_max=255)
    #
    """

    def getMinMaxValuesOfFirstChannel(image_path):
        image = Image.open(image_path).convert("L")
        pixel_values = list(image.getdata())
        return min(pixel_values), max(pixel_values)

    if debug >= 1:
        print(cyan + "minMaxScalingChannels() : " + endC + "MinMax Scaling files {} ...".format(raster_files_to_scale_list))

    # Create normamalize file raster
    for index in range (len(raster_files_to_scale_list)) :
        raster_to_scale = raster_files_to_scale_list[index]
        path_raster_norm = raster_files_norm_list[index]
        base_min, base_max = getMinMaxValuesOfFirstChannel(raster_to_scale)

        # Moramlise grace à gdal
        command = "gdal_translate -scale %s %s %s %s  %s %s" %(str(base_min), str(base_max), str(new_min), str(new_max), raster_to_scale, path_raster_norm)
        if debug >= 4:
            print(command)

        exit_code = os.system(command)
        if exit_code != 0:
            print(command)
            print(cyan + "minMaxScalingChannels() : " + bold + red + "!!! Une erreur c'est produite au cours de la mormailsation de l'image : " + raster_to_scale + ". Voir message d'erreur." + endC, file=sys.stderr)

    if debug >= 1:
        print(cyan + "minMaxScalingChannels() : " + endC + "MinMax scaling to list file {} done\n".format(raster_files_norm_list))

    return

###########################################################################################################################################
# FUNCTION mergeChannels()                                                                                                                #
###########################################################################################################################################
def mergeChannels(monochannel_file_list, file_merged, init_value=0):
    """
    # ROLE:
    #     Merge multiple indicator monochannel raster files into a single channel raster file.
    #
    # PARAMETERS:
    #     monochannel_file_list (list * (str)): List of file paths to the indicator monochannel raster files to be merged.
    #     file_merged (str): Name of the raster file containing the result of the merging.
    #     init_value (int): Initial value for uninitialized pixels in the merged raster (default: 0).
    #
    # RETURNS:
    #     NA.
    #
    # EXAMPLE:
    #     mergeChannels(["/path/to/indicator1.tif", "/path/to/indicator2.tif"], "/output/folder/ind1_ind2_merged.tif", init_value=0)
    #
    """

    if debug >= 1:
        print(cyan + "mergeChannels() : " + endC + "Merging indicator monochannels...")

    # Fusion d'images grace à gdal
    list_file_txt = ""
    for path_monochannel_file in monochannel_file_list :
        list_file_txt += " " + path_monochannel_file

    command = "gdal_merge.py -init %s -o %s %s" %(str(init_value), file_merged, list_file_txt)
    if debug >= 4:
        print(command)

    exit_code = os.system(command)
    if exit_code != 0:
        print(command)
        print(cyan + "mergeChannels() : " + bold + red + "!!! Une erreur c'est produite au cours de la fusion de l'image : " + file_merged + ". Voir message d'erreur." + endC, file=sys.stderr)

    if debug >= 1:
        print(cyan + "mergeChannels() : " + endC + "Merging of indicator channels to {} done.\n".format(file_merged))

    return

###########################################################################################################################################
# FUNCTION concatRasterChannelsWithPrio()                                                                                                 #
###########################################################################################################################################
def concatRasterChannelsWithPrio(rasters_input_list, concat_rvf_file_output, channel_prio="blue", codage="uint8", no_data_value=0, extension_raster=".tif", path_time_log="", save_results_intermediate=False, overwrite=True):
    """
    # ROLE:
    #     Concatenates raster channel files with a specified priority channel.
    #
    # PARAMETERS:
    #     rasters_input_list (str): Liste files containing the cut indicator raster files.
    #     concat_rvf_file_output (str): the ouput file concatenated raster file to be created.
    #     channel_prio (str): priority channel for the concatenation, (default: "blue").
    #     codage (str): encodage du fichier raster de sortie, (default="uint8").
    #     no_data_value : value pixel of no data (par défaut : 0).
    #     extension_raster : extension des fichiers raster de sortie, (par defaut = '.tif)'.
    #     path_time_log : fichier de log de sortie, par defaut = "".
    #     save_results_intermediate (boolean): supprime ou non les fichiers temporaires si True, (default=False).
    #     overwrite : supprime ou non les fichiers existants ayant le meme nom, (par defaut = True).
    #
    # RETURNS:
    #     NA.
    #
    # EXAMPLE:
    #     concatRasterChannelsWithPrio(".../path_folder_rasters_in/file.tif", "/path_folder_rasters_out/file_concat.tif")
    #
    """

    SUFFIX_PRIO_BAND = "_prioBand"
    FOLDER_PRIO = "prio"

    if debug >= 1:
        print(cyan + "concatRasterChannelsWithPrio() : " + endC + "concatenating channels from {} ...".format(rasters_input_list))

    # Allowed channel values
    bands = {'red': 1, 'green': 2, 'blue': 3}
    bands_values = list(bands.keys())
    if channel_prio not in bands_values:
        raise ValueError(cyan + "concatRasterChannelsWithPrio() : " + bold + red +"'channel_prio' parameter must be one of: " + ", ".join(bands_values) + endC)

    # Create concat folder
    path_folder_rasters_out = os.path.dirname(rasters_input_list[0])

    # Répertoire temp
    path_folder_rasters_out_prio = path_folder_rasters_out + os.sep + FOLDER_PRIO
    if not os.path.exists(path_folder_rasters_out_prio):
        os.makedirs(path_folder_rasters_out_prio)

    # Supprimer le fichier de sortie si il existe déjà
    if os.path.exists(concat_rvf_file_output) :
        if overwrite :
            os.remove(concat_rvf_file_output)
        else :
            return

    # Priority to the band number (input parameter)
    file_prio = rasters_input_list[bands[channel_prio]-1]
    if debug >= 1:
        print(cyan + "concatRasterChannelsWithPrio() : " + endC + "file_prio {}".format(file_prio))

    files_channels_in_prio_list = []
    for i, file_tmp in enumerate(rasters_input_list):
        if os.path.isfile(file_tmp):
            file_channel_output = path_folder_rasters_out_prio + os.sep + os.path.splitext(os.path.basename(file_tmp))[0] + SUFFIX_PRIO_BAND + extension_raster

            if (i+1 != bands[channel_prio]):
                expression = "im2b1!=0?0:im1b1"
                command = "otbcli_BandMathX -il %s %s -out '%s?&nodata=%s' %s -exp %s" %(file_tmp ,file_prio, file_channel_output, no_data_value, codage, expression)

                if debug >= 4:
                    print(command)

                exit_code = os.system(command)
                if exit_code != 0:
                    print(command)
                    print(cyan + "concatRasterChannelsWithPrio() : " + bold + red + "!!! Une erreur c'est produite au cours de la priorisation de : " + file_tmp + ". Voir message d'erreur." + endC, file=sys.stderr)

            else:
                file_channel_output = file_tmp

            files_channels_in_prio_list.append(file_channel_output)

        else :
            print(cyan + "concatRasterChannelsWithPrio() : " + bold + red + "Error: file to concatene not exist! " + endC + file_tmp, file=sys.stderr)
            exit(1)

    # Concatenantion des 3 bandes RVB
    concatenateChannels(files_channels_in_prio_list, concat_rvf_file_output, path_time_log, code=codage, save_results_intermediate=save_results_intermediate, overwrite=overwrite)
    setNodataValueImage(concat_rvf_file_output, no_data_value)

    # Supression des fichiers temporaires
    if not save_results_intermediate:
        if os.path.exists(path_folder_rasters_out_prio):
            deleteDir(path_folder_rasters_out_prio)

    if debug >= 1:
        print(cyan + "concatRasterChannelsWithPrio() : " + endC + "concatenation channels to {} done\n".format(concat_rvf_file_output))

    return

###########################################################################################################################################
# FONCTION createDataIndicateurPseudoRGB()                                                                                                #
###########################################################################################################################################
def createDataIndicateurPseudoRGB(path_base_folder, emprise_vector, GRA_file_input, TCD_file_input, IMD_file_input, vectors_road_input_list, vectors_build_input_list, vector_water_area_input_list, sql_exp_road_list, sql_exp_build_list, sql_exp_water_list, pseudoRGB_file_output, raster_road_width_output, raster_build_height_output, vector_roads_output,  vector_waters_area_output, roads_width_field = "LARGEUR", road_importance_field="IMPORTANCE", road_importance_threshold=4, resolution=5, no_data_value=0, epsg=2154, format_raster="GTiff", format_vector='ESRI Shapefile', extension_raster=".tif", extension_vector=".shp", path_time_log="", save_results_intermediate=False, overwrite=True):
    """
    # ROLE:
    #     Creates pseudo-RGB image data from various indicators and input files.
    #
    # PARAMETERS:
    #     path_base_folder, (str): le répertoire de base de travail.
    #     emprise_vector (str): le fichier vecteur d'emprise de la zone d'étude.
    #     GRA_file_input (str) : chemin vers le fichier raster d'entrée GRA (Grassland).
    #     TCD_file_input (str) :chemin vers le fichier raster d'entrée TCD (Tree Cover Density).
    #     IMD_file_input (str) : chemin vers lefichier raster d'entrée IMD (Imperviousness Density) .
    #     vectors_road_input_list (list) : list of paths to road files (routes primaires et secondaires).
    #     vectors_build_input_list (list) : liste des fichiers contenant les batis d'entrées.
    #     vector_water_area_input_list (list) : liste des fichiers contenant les surface en eau d'entrées.
    #     sql_exp_road_list (list) : liste d'expression sql pour le filtrage des fichiers vecteur de bd exogenes routes.
    #     sql_exp_build_list (list) : liste d'expression sql pour le filtrage des fichiers vecteur de bd exogenes batis.
    #     sql_exp_water_list (list) : liste d'expression sql pour le filtrage des fichiers vecteur de bd exogenes surfaces en eau.
    #     pseudoRGB_file_output (str) : fichier de pseudo-RGB image resultat en sortie.
    #     raster_road_width_output (str) :  fichier de sortie rasteur largeur de routes.
    #     raster_build_height_output (str) :  fichier de sortie rasteur des batis.
    #     vector_roads_output (str) : fichier de sortie vecteur contenant toutes les routes.
    #     vector_waters_area_output (str) : fichier de sortie vecteur contenant toutes les surfaces en eau.
    #     roads_width_field (str) : name of the column containing road width data (default: "LARGEUR").
    #     road_importance_field (str) : champs importance des routes (par defaut : "IMPORTANCE").
    #     road_importance_threshold (int) : valeur du seuil d'importance (par défaut : 4).
    #     resolution (int): resolution forcé des rasters de travail (par défaut : 5).
    #     no_data_value  (int) : Option : Value pixel of no data (par défaut : 0).
    #     epsg (int):  EPSG code of the desired projection (default is 2154).
    #     format_raster (str) : Format de l'image de sortie (déeaut GTiff)
    #     format_vector (str) : Format for the output vector file (default is 'ESRI Shapefile').
    #     extension_raster (str) : extension des fichiers raster de sortie, par defaut = '.tif'
    #     extension_vector (str) : extension du fichier vecteur de sortie, par defaut = '.shp'
    #     path_time_log (str) : fichier de log de sortie, par defaut = ""
    #     save_results_intermediate (Bool) : fichiers de sorties intermediaires non nettoyées, par defaut = False
    #     overwrite (Bool) : supprime ou non les fichiers existants ayant le meme nom, par defaut = True
    #
    # RETURNS:
    #     None
    #
    # EXAMPLE:
    #     createDataIndicateurPseudoRGB("/data_folder", "emprise.shp", ["primary_routes.shp","secondary_routes.shp"], "surfaces_eau.shp", "GRA.tif", "TCD.tif", "IMD.tif", "resolution_ref.tif")
    """

    # Affichage des paramètres
    if debug >= 3:
        print(bold + green + "Variables dans le createDataIndicateurPseudoRGB - Variables générales" + endC)
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "path_base_folder : " + str(path_base_folder))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "emprise_vector : " + str(emprise_vector))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "GRA_file_input : " + str(GRA_file_input))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "TCD_file_input : " + str(TCD_file_input))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "IMD_file_input : " + str(IMD_file_input))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "vectors_road_input_list : " + str(vectors_road_input_list))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "vectors_build_input_list : " + str(vectors_build_input_list))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "vector_water_area_input_list : " + str(vector_water_area_input_list))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "sql_exp_road_list : " + str(sql_exp_road_list))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "sql_exp_build_list : " + str(sql_exp_build_list))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "sql_exp_water_list : " + str(sql_exp_water_list))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "pseudoRGB_file_output : " + str(pseudoRGB_file_output))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "raster_road_width_output : " + str(raster_road_width_output))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "raster_build_height_output : " + str(raster_build_height_output))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "vector_roads_output : " + str(vector_roads_output))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "vector_waters_area_output : " + str(vector_waters_area_output))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "roads_width_field : " + str(roads_width_field))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "road_importance_field : " + str(road_importance_field))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "road_importance_threshold : " + str(road_importance_threshold))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "resolution : " + str(resolution))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "no_data_value : " + str(no_data_value))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "epsg : " + str(epsg))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "format_raster : " + str(format_raster))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "format_vector : " + str(format_vector))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "path_time_log : " + str(path_time_log))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "save_results_intermediate : "+ str(save_results_intermediate))
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "overwrite : "+ str(overwrite))

    # Répertoires
    FOLDER_CREATE_DATA = "create_data"
    FOLDER_VECTOR = "vecteur"
    FOLDER_RASTER = "raster"
    FOLDER_RESULT = "result"
    FOLDER_CUT = "cut"
    FOLDER_NORM = "norm"

    # Constantes
    SUFFIX_CUT = "_cut"
    SUFFIX_BUF = "_buf"
    SUFFIX_NORM = "_norm"
    SUFFIX_SECOND = "_second"
    SUFFIX_FILTER = "_filt"

    BASE_NAME_ALL_ROAD = "all_roads_"
    BASE_NAME_ALL_BUILT = "all_build_"
    BASE_NAME_ROAD_WIDTH = "roads_width_"
    BASE_NAME_ROAD_AND_WATER = "roads_and_water_surfaces_"
    BASE_NAME_VEGETATION = "vegetation_indicator_"

    CODAGE_8BITS = 'uint8'
    CHANEL_PRIO = "blue"

    # Creation du répertoire de sortie si il n'existe pas
    if not os.path.exists(path_base_folder):
        os.makedirs(path_base_folder)

    path_folder_output = os.path.dirname(vector_roads_output)
    if not os.path.exists(path_folder_output):
        os.makedirs(path_folder_output)
    path_folder_output = os.path.dirname(vector_waters_area_output)
    if not os.path.exists(path_folder_output):
        os.makedirs(path_folder_output)
    path_folder_output = os.path.dirname(raster_road_width_output)
    if not os.path.exists(path_folder_output):
        os.makedirs(path_folder_output)
    path_folder_output = os.path.dirname(raster_build_height_output)
    if not os.path.exists(path_folder_output):
        os.makedirs(path_folder_output)
    path_folder_output = os.path.dirname(pseudoRGB_file_output)
    if not os.path.exists(path_folder_output):
        os.makedirs(path_folder_output)

    # Creation des répertoires temporaires
    #  Vecteur
    path_folder_base_vector = path_base_folder + os.sep + FOLDER_CREATE_DATA + os.sep + FOLDER_VECTOR
    if not os.path.exists(path_folder_base_vector):
        os.makedirs(path_folder_base_vector)
    #  Raster
    path_folder_base_raster = path_base_folder + os.sep + FOLDER_CREATE_DATA + os.sep + FOLDER_RASTER
    if not os.path.exists(path_folder_base_raster):
        os.makedirs(path_folder_base_raster)

    path_folder_base_raster_cut = path_folder_base_raster + os.sep + FOLDER_CUT
    if not os.path.exists(path_folder_base_raster_cut):
        os.makedirs(path_folder_base_raster_cut)

    path_folder_base_raster_norm = path_folder_base_raster + os.sep  + FOLDER_NORM
    if not os.path.exists(path_folder_base_raster_norm):
        os.makedirs(path_folder_base_raster_norm)

    #  Result
    path_folder_base_result = path_base_folder + os.sep + FOLDER_CREATE_DATA + os.sep + FOLDER_RESULT
    if not os.path.exists(path_folder_base_result):
        os.makedirs(path_folder_base_result)

    # RASTER
    # Reproject (2154) and cut with emprise raster files
    path_folder_cut_raster = ""
    path_folder_cut_raster_ref_img = ""
    GRA_file_epsg_cut = path_folder_base_raster_cut + os.sep + os.path.splitext(os.path.basename(GRA_file_input))[0] + "_" +  str(epsg) + SUFFIX_CUT + extension_raster
    reprojectAndCutRaster(emprise_vector, GRA_file_input, GRA_file_epsg_cut, resolution, no_data_value, epsg, format_raster, format_vector, save_results_intermediate)
    TCD_file_epsg_cut = path_folder_base_raster_cut + os.sep + os.path.splitext(os.path.basename(TCD_file_input))[0] + "_" + str(epsg) + SUFFIX_CUT + extension_raster
    reprojectAndCutRaster(emprise_vector, TCD_file_input, TCD_file_epsg_cut, resolution, no_data_value, epsg, format_raster, format_vector, save_results_intermediate)
    IMD_file_epsg_cut = path_folder_base_raster_cut + os.sep + os.path.splitext(os.path.basename(IMD_file_input))[0] + "_" + str(epsg) + SUFFIX_CUT + extension_raster
    reprojectAndCutRaster(emprise_vector, IMD_file_input, IMD_file_epsg_cut, resolution, no_data_value, epsg, format_raster, format_vector, save_results_intermediate)

    ## Vecteurs Routes ##

    # Filtrage SQL Routes
    if sql_exp_road_list != None and  sql_exp_road_list != [] :
        vectors_road_filtered_list = []
        for vector_road in vectors_road_input_list :
            vector_road_filtered = path_folder_base_vector + os.sep + os.path.splitext(os.path.basename(vector_road))[0] + SUFFIX_FILTER + extension_vector
            vectors_road_filtered_list.append(vector_road_filtered)
        filterVectorSql(vectors_road_input_list, vectors_road_filtered_list, sql_exp_road_list, format_vector)
    else :
       vectors_road_filtered_list = vectors_road_input_list

    # Concatenantion des routes files
    vectors_road_cut_list = []
    for vector_road in vectors_road_filtered_list :
        vector_road_cut = path_folder_base_vector + os.sep + os.path.splitext(os.path.basename(vector_road))[0] + "_" +  str(epsg) + SUFFIX_CUT + extension_vector
        reprojectAndCutVector(emprise_vector, vector_road, vector_road_cut, epsg, format_vector, save_results_intermediate)
        vectors_road_cut_list.append(vector_road_cut)

    # Fusionner routes_primaires et secondaires sauf grande routes principales  > à road_importance_threshold
    vector_all_road_cut_second = path_folder_base_vector + os.sep + BASE_NAME_ALL_ROAD + str(epsg) + SUFFIX_CUT + SUFFIX_SECOND + extension_vector
    if len(vectors_road_cut_list) > 1 :
        ##fusionVectors(vectors_road_cut_list, vector_roads_output)
        gdfFusionVectors(vectors_road_cut_list, vector_roads_output, format_vector, epsg) # version avec geopandas
    else :
        copyVectorFile(vectors_road_cut_list[0], vector_roads_output, format_vector)

    # Suprimer les routes importantes
    gdf_roads = gpd.read_file(vector_roads_output)
    gdf_roads[road_importance_field] = gdf_roads[road_importance_field].replace("NC", 6).astype(int)
    gdf_roads_select = gdf_roads[gdf_roads[road_importance_field] > road_importance_threshold]
    gdf_roads_select.to_file(vector_all_road_cut_second, driver=format_vector, crs="EPSG:" + str(epsg))

    # Définir une image de référence à partir d'une image raster pour établir la résolution de la rasterisation
    file_img_ref = TCD_file_epsg_cut

    # Creation du fichier raster contenant les informations de largeurs de route
    if debug >= 1:
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "creating raster file containing roads width informations")

    vector_all_road_buff = path_folder_base_vector + os.sep + BASE_NAME_ALL_ROAD + str(epsg) + SUFFIX_BUF + extension_vector
    vector_all_road_buff_second = path_folder_base_vector + os.sep + BASE_NAME_ALL_ROAD + str(epsg) + SUFFIX_BUF + SUFFIX_SECOND + extension_vector
    raster_roads_width_second = path_folder_base_raster_cut  + os.sep + BASE_NAME_ROAD_WIDTH + str(epsg) + SUFFIX_CUT + SUFFIX_SECOND + extension_raster
    bufferVector(vector_roads_output, vector_all_road_buff, buffer_dist=1.0, col_name_buf=roads_width_field, fact_buf=1.5, quadsecs=10, format_vector=format_vector)
    rasterizeVector(vector_all_road_buff, raster_road_width_output, file_img_ref, field=road_importance_field, codage=CODAGE_8BITS, ram_otb=0)
    bufferVector(vector_all_road_cut_second, vector_all_road_buff_second, buffer_dist=1.0, col_name_buf=roads_width_field, fact_buf=1.5, quadsecs=10, format_vector=format_vector)
    ##rasterizeVector(vector_all_road_buff_second, raster_roads_width_second, file_img_ref, field=road_importance_field, codage=CODAGE_8BITS, ram_otb=0)
    rasterizeBinaryVector(vector_all_road_buff_second, file_img_ref, raster_roads_width_second, label=1, codage=CODAGE_8BITS, ram_otb=0)

    if debug >= 1:
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "creation of raster file containing roads width informations done to {}".format(raster_road_width_output))

    ## Vecteurs Batis ##

    # Filtrage SQL Batis
    if sql_exp_build_list != None and  sql_exp_build_list != [] :
        vectors_build_filtered_list = []
        for vector_build in vectors_build_input_list :
            vector_build_filtered = path_folder_base_vector + os.sep + os.path.splitext(os.path.basename(vector_build))[0] + SUFFIX_FILTER + extension_vector
            vectors_build_filtered_list.append(vector_build_filtered)
        filterVectorSql(vectors_build_input_list, vectors_build_filtered_list, sql_exp_build_list, format_vector)
    else :
       vectors_build_filtered_list = vectors_build_input_list

    # Concatenantion des batis files
    vectors_build_cut_list = []
    for vector_build in vectors_build_filtered_list:
        # Cut shapefiles with emprise
        vector_build_cut = path_folder_base_vector + os.sep + os.path.splitext(os.path.basename(vector_build))[0] + "_" +  str(epsg) + SUFFIX_CUT + extension_vector
        reprojectAndCutVector(emprise_vector, vector_build, vector_build_cut, epsg, format_vector, save_results_intermediate)
        vectors_build_cut_list.append(vector_build_cut)

    vector_all_build = path_folder_base_vector + os.sep + BASE_NAME_ALL_BUILT + str(epsg) + SUFFIX_CUT + extension_vector
    if len(vectors_build_cut_list) > 1 :
        ##fusionVectors(vectors_build_cut_list, vector_all_build, format_vector)
        gdfFusionVectors(vectors_build_cut_list, vector_all_build, format_vector, epsg) # version avec geopandas
    else :
        copyVectorFile(vectors_build_cut_list[0], vector_all_build, format_vector)

    # Rasterise building vector to raster building height
    rasterizeVector(vector_all_build, raster_build_height_output, file_img_ref, field="HAUTEUR")

    if debug >= 1:
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "creation of raster file containing builds width informations done to {}".format(raster_build_height_output))

    ## Vecteurs Eaux ##

    # Filtrage SQL Routes
    if sql_exp_water_list != None and  sql_exp_water_list != [] :
        vectors_water_filtered_list = []
        for vector_water in vector_water_area_input_list :
            vector_water_filtered = path_folder_base_vector + os.sep + os.path.splitext(os.path.basename(vector_water))[0] + SUFFIX_FILTER + extension_vector
            vectors_water_filtered_list.append(vector_water_filtered)
        filterVectorSql(vector_water_area_input_list, vectors_water_filtered_list, sql_exp_water_list, format_vector)
    else :
       vectors_water_filtered_list = vector_water_area_input_list

    # Concatenantion des surfaces en eau files
    vectors_water_area_cut_list = []
    for vector_water in vectors_water_filtered_list:
        # Cut shapefiles with emprise
        vector_water_cut = path_folder_base_vector + os.sep + os.path.splitext(os.path.basename(vector_water))[0] + "_" +  str(epsg) + SUFFIX_CUT + extension_vector
        reprojectAndCutVector(emprise_vector, vector_water, vector_water_cut, epsg, format_vector, save_results_intermediate)
        vectors_water_area_cut_list.append(vector_water_cut)

    if len(vectors_water_area_cut_list) > 1 :
        ##fusionVectors(vectors_water_area_cut_list, vector_waters_area_output, format_vector)
        gdfFusionVectors(vectors_water_area_cut_list, vector_waters_area_output, format_vector, epsg) # version avec geopandas
    else :
        copyVectorFile(vectors_water_area_cut_list[0], vector_waters_area_output, format_vector)

    # Rasterisation water surfaces
    raster_water_area = path_folder_base_raster_cut  + os.sep + os.path.splitext(os.path.basename(vector_waters_area_output))[0] + "_" +  str(epsg) + SUFFIX_CUT + extension_raster
    rasterizeBinaryVector(vector_waters_area_output, file_img_ref, raster_water_area, label=1, codage=CODAGE_8BITS, ram_otb=0)

    if debug >= 1:
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "creation of raster file containing water area width informations done to {}".format(raster_water_area))

    # Merge vecteurs roads and water surfaces
    raster_files_merged = path_folder_base_raster_cut + os.sep +  BASE_NAME_ROAD_AND_WATER + str(epsg) + SUFFIX_CUT + extension_raster
    binary_raster_files_list = [raster_roads_width_second, raster_water_area]
    mergeListRaster(binary_raster_files_list, raster_files_merged)

    # Recupération des fichiers à normaliser dans une liste
    raster_files_to_scale_list = [GRA_file_epsg_cut, TCD_file_epsg_cut, IMD_file_epsg_cut, raster_files_merged]

    # MinMax scaling indicators and roads/water_surface files define list file to normalize
    raster_files_norm_list = []
    for file_tmp in raster_files_to_scale_list:
        file_norm =  path_folder_base_raster_norm + os.sep + os.path.splitext(os.path.basename(file_tmp))[0] + SUFFIX_NORM + extension_raster
        raster_files_norm_list.append(file_norm)

    # Normalisation 0 -> 255 des fichiers rasters
    minMaxScalingChannels(raster_files_to_scale_list, raster_files_norm_list, new_min=0, new_max=255)

    # Merge vegetation indicator channels
    raster_vegetation_indicator_list = raster_files_norm_list[:2]
    if debug >= 3:
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "raster_vegetation_indicator_list : {}".format(raster_vegetation_indicator_list))
    merge_raster_vegetation_indicator = path_folder_base_raster_norm + os.sep + BASE_NAME_VEGETATION + str(epsg) + SUFFIX_CUT + SUFFIX_NORM + extension_raster
    mergeChannels(raster_vegetation_indicator_list, merge_raster_vegetation_indicator, no_data_value)

    # Concat channels + channels with priority on a band
    file_band_rvb_sorted_list = [raster_files_norm_list[2], merge_raster_vegetation_indicator, raster_files_norm_list[3]]
    concatRasterChannelsWithPrio(file_band_rvb_sorted_list, pseudoRGB_file_output, channel_prio=CHANEL_PRIO, codage=CODAGE_8BITS, no_data_value=no_data_value, extension_raster=extension_raster, path_time_log=path_time_log, save_results_intermediate=save_results_intermediate, overwrite=overwrite)

    # Supression des repertoirtes temporaires
    if not save_results_intermediate :
        if os.path.exists(path_folder_base_vector):
            deleteDir(path_folder_base_vector)
        if os.path.exists(path_folder_base_raster):
            deleteDir(path_folder_base_raster)

    if debug >= 1:
        print(cyan + "createDataIndicateurPseudoRGB() : " + endC + "Ending result : " + pseudoRGB_file_output)

    return

# ==================================================================================================================================================

if __name__ == '__main__':

    ##### paramètres en entrées #####
    #################################
    # Pl est recommandé de prendre un répertoire avec accès rapide en lecture et écriture pour accélérer les traitements
    BASE_FOLDER = "/mnt/RAM_disk/INTEGRATION"

    # Fichiers vecteurs
    emprise_vector =  "/mnt/RAM_disk/INTEGRATION/emprise/Emprise_Toulouse_Metropole.shp"
    vector_water_area_input_list = ["/mnt/RAM_disk/INTEGRATION/bd_topo/N_SURFACE_EAU_BDT_031.shp"]
    vectors_road_input_list = ["/mnt/RAM_disk/INTEGRATION/bd_topo/N_ROUTE_PRIMAIRE_BDT_031.SHP",
                               "/mnt/RAM_disk/INTEGRATION/bd_topo/N_ROUTE_SECONDAIRE_BDT_031.SHP"]
    vectors_build_input_list = ["/mnt/RAM_disk/INTEGRATION/bd_topo/N_BATI_INDIFFERENCIE_BDT_031.shp",
                                "/mnt/RAM_disk/INTEGRATION/bd_topo/N_BATI_INDUSTRIEL_BDT_031.shp",
                                "/mnt/RAM_disk/INTEGRATION/bd_topo/N_BATI_REMARQUABLE_BDT_031.shp"]

    # Fichiers rasters
    GRA_file_input = "/mnt/RAM_disk/INTEGRATION/GRA_2018_010m_E36N23_03035_v010.tif"
    TCD_file_input = "/mnt/RAM_disk/INTEGRATION/TCD_2018_010m_E36N23_03035_v020.tif"
    IMD_file_input = "/mnt/RAM_disk/INTEGRATION/IMD_2018_010m_E36N23_03035_v020.tif"

    # Fichiers resultats de sortie
    pseudoRGB_file_output = "/mnt/RAM_disk/INTEGRATION/create_data/result/pseudoRGB_input_seg_res5.tif"
    raster_road_width_output = "/mnt/RAM_disk/INTEGRATION/create_data/result/roads_width.tif"
    raster_build_height_output = "/mnt/RAM_disk/INTEGRATION/create_data/result/builds_height.tif"
    vector_roads_output = "/mnt/RAM_disk/INTEGRATION/create_data/result/all_roads.shp"
    vector_waters_area_output = "/mnt/RAM_disk/INTEGRATION/create_data/result/all_waters.shp"

    #################################

    # Exec
    createDataIndicateurPseudoRGB(BASE_FOLDER,
                                  emprise_vector,
                                  GRA_file_input,
                                  TCD_file_input,
                                  IMD_file_input,
                                  vectors_road_input_list,
                                  vectors_build_input_list,
                                  vector_water_area_input,
                                  [],[],[],
                                  pseudoRGB_file_output,
                                  raster_road_width_output,
                                  raster_build_height_output,
                                  vector_roads_output,
                                  vector_waters_area_output,
                                  roads_width_field = "LARGEUR",
                                  road_importance_field="IMPORTANCE",
                                  road_importance_threshold=4,
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
