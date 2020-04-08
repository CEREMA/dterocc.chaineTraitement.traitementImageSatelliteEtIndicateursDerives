# -*- coding: utf-8 -*-
#!/usr/bin/python

#############################################################################
# Copyright (©) CEREMA/DTerSO/DALETT/SCGSI  All rights reserved.            #
#############################################################################

#############################################################################
#                                                                           #
# FONCTIONS POUR L'APPEL À DES FONCTIONS SNAP                               #
#                                                                           #
#############################################################################

import sys,os
import numpy as np
import gc
import snappy
from snappy import ProductIO
from snappy import Product
from snappy import ProductData
from snappy import ProductUtils
from snappy import FlagCoding
from snappy import GPF
from snappy import HashMap
from snappy import jpy
from snappy import String
from snappy import WKTReader
from snappy import ProgressMonitor
from snappy import VectorDataNode
from snappy import PlainFeatureFactory
from snappy import SimpleFeatureBuilder
from snappy import DefaultGeographicCRS
from snappy import ListFeatureCollection
from snappy import FeatureUtils

import matplotlib.pyplot as plt
from Lib_operator import *
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC

# HashMap Key-Value pairs
#HashMap = jpy.get_type('java.util.HashMap')

# Get snappy Operators
#GPF.getDefaultInstance().getOperatorSpiRegistry().loadOperatorSpis()
#gc.enable()

# debug = 0 : affichage minimum de commentaires lors de l'exécution du script
# debug = 3 : affichage maximum de commentaires lors de l'exécution du script. Intermédiaire : affichage intermédiaire

debug = 3

# ATTENTION : pour appeler SNAP, il faut avoir installé l'outil SNAP sur la machine hôte et configué snappy

#########################################################################
# FONCTION testJavaMemory()                                             #
#########################################################################
#   Rôle : outil de test verification de la taille max de ma memoire aloué par la jvm

def testJavaMemory():

    Runtime = jpy.get_type('java.lang.Runtime')
    max_memory = Runtime.getRuntime().maxMemory()
    total_memory = Runtime.getRuntime().totalMemory()
    free_memory = Runtime.getRuntime().freeMemory()
    mb = 1024 * 1024
    print(cyan + "testJavaMemory() : " + bold + green + 'max memory : ' + str(max_memory / mb) + ' MB' + endC)
    print(cyan + "testJavaMemory() : " + bold + green + 'total memory : ' + str(total_memory / mb) + ' MB' + endC)
    print(cyan + "testJavaMemory() : " + bold + green + 'free memory : '+ str(free_memory / mb) + ' MB' + endC)
    return

#########################################################################
# FONCTION readDim()                                                    #
#########################################################################
#   Rôle : import de données rasters (au format .dim) pour extraire des informations
#   Paramètres In:
#       input_dim : entête de fichiers raster à importer
#   Paramètres Out:
#     Return :
#       product : descipteur sur les données charger dans SNAP
#       band_names_list : liste des noms des bandes de la donnée chargée

def readDim(input_dim):

    if debug >= 2:
        print(cyan + "readDim() : " + bold + green + "Import Dim to SNAP : " + endC + str(input_dim ))
    product = ProductIO.readProduct(input_dim)
    band_names_list = list(product.getBandNames())
    return product, band_names_list

#########################################################################
# FONCTION writeDataSnap()                                              #
#########################################################################
#   Rôle : Ecrit dans un fichier des données rasters au format snap en format raster (.dim ou .tif ou ...)
#   Paramètres In:
#       product : données SNAP
#       output_file : fichier de sortie
#       type_file : type du fichier de sortie par default : 'BEAM-DIMAP'  or 'GeoTIFF'
#     Return :

def writeDataSnap(product, output_file, type_file='BEAM-DIMAP'):
    ProductIO.writeProduct(product, output_file, type_file)
    if debug >= 2:
        print(cyan + "writeDataSnap() : " + bold + green + "Writing Done : " + endC + str(output_file))
    return

#########################################################################
# FONCTION convertDim2Tiff()                                            #
#########################################################################
#   Rôle : convertit des données rasters au format snap (.dim) en format raster (.tif)
#   Paramètres In:
#       input_dim : entête de fichiers raster à importer
#       output_file : fichier de sortie
#       name_file : nom du fichier à extraire du .dim
#       format_file : format du fichier de sortie par default : 'float32'
#       type_file : type du fichier de sortie par default : 'GeoTIFF'
#     Return :

def convertDim2Tiff(input_dim, output_file, name_file, format_file='float32', type_file='GeoTIFF'):

    if debug >= 2:
        print(cyan + "convertDim2Tiff() : " + bold + green + "Import Dim to SNAP : " + endC + input_dim )

    # Info input file
    product = ProductIO.readProduct(input_dim)
    band = product.getBand(name_file)

    width = product.getSceneRasterWidth()
    height = product.getSceneRasterHeight()

    # Instance de GPF
    GPF.getDefaultInstance().getOperatorSpiRegistry().loadOperatorSpis()

    # Def operateur SNAP
    operator = 'BandMaths'
    BandDescriptor = jpy.get_type('org.esa.snap.core.gpf.common.BandMathsOp$BandDescriptor')
    targetBands = jpy.array('org.esa.snap.core.gpf.common.BandMathsOp$BandDescriptor', 1)

    # Get des expressions d'entréées
    targetBand = BandDescriptor()
    targetBand.name = 'band_0'
    targetBand.type = format_file
    targetBand.expression = name_file
    targetBands[0] = targetBand

    # Set des parametres
    parameters = HashMap()
    parameters.put('targetBands', targetBands)

    result = GPF.createProduct(operator, parameters, product)
    ProductIO.writeProduct(result, output_file, type_file)

    if debug >= 2:
        print(cyan + "convertDim2Tiff() : " + bold + green + "Writing Done : " + endC + str(output_file))

    return

#########################################################################
# FONCTION topsarSplit()                                                #
#########################################################################
#   Rôle : Split file de données rasters (au format .dim) dans l'outil SNAP
#   Paramètres In:
#       product : donnée snap d'entrée
#   Paramètres Out:
#     Return :
#       result : resultat de l'operation au format data snap

def topsarSplit(product):

    if debug >= 2:
        print(cyan + "applyingOrbitFile() : " + bold + green + "Run to SNAP... " + endC )

    # Instance de GPF
    GPF.getDefaultInstance().getOperatorSpiRegistry().loadOperatorSpis()

    # Def operateur SNAP
    operator = 'TOPSAR-Split'

    # Set des parametres
    parameters = HashMap()
    op_spi = GPF.getDefaultInstance().getOperatorSpiRegistry().getOperatorSpi(operator)
    op_params = op_spi.getOperatorDescriptor().getParameterDescriptors()
    for param in op_params:
        if debug >= 2:
            print(cyan + "topsarSplit() : " + bold + green + str(param.getName()) + " : " + str(param.getDefaultValue()) + endC)
        parameters.put(param.getName(), param.getDefaultValue())
    parameters.put('subswath', 'IW1')
    parameters.put('selectedPolarisations', 'VV')

    if debug >= 2:
        print(parameters)

    # Get snappy Operators
    result = GPF.createProduct(operator, parameters, product)

    if debug >= 2:
        print(cyan + "topsarSplit() : " + bold + green + "Done... " + endC)

    return result

#########################################################################
# FONCTION applyingOrbitFile()                                          #
#########################################################################
#   Rôle : Orbit file de données rasters (au format .dim) dans l'outil SNAP
#   Paramètres In:
#       product : donnée snap d'entrée
#   Paramètres Out:
#     Return :
#       result : resultat de l'operation au format data snap

def applyingOrbitFile(product):

    if debug >= 2:
        print(cyan + "applyingOrbitFile() : " + bold + green + "Run to SNAP... " + endC )

    # Get input file
    #product = ProductIO.readProduct(input_dim)

    # Instance de GPF
    GPF.getDefaultInstance().getOperatorSpiRegistry().loadOperatorSpis()

    # Def operateur SNAP
    operator = 'Apply-Orbit-File'

    # Set des parametres
    parameters = HashMap()

    op_spi = GPF.getDefaultInstance().getOperatorSpiRegistry().getOperatorSpi(operator)
    op_params = op_spi.getOperatorDescriptor().getParameterDescriptors()
    for param in op_params:
        if debug >= 2:
            print(cyan + "applyingOrbitFile() : " + bold + green + str(param.getName()) + " : " + str(param.getDefaultValue()) + endC)
        parameters.put(param.getName(), param.getDefaultValue())

    #parameters.put("Orbit State Vectors", "Sentinel Precise (Auto Download)")
    #parameters.put("Polynomial Degree", 3)

    if debug >= 2:
        print(parameters)

    # Get snappy Operators
    result = GPF.createProduct(operator, parameters, product)
    #ProductIO.writeProduct(result, output_file, 'BEAM-DIMAP')

    if debug >= 2:
        print(cyan + "applyingOrbitFile() : " + bold + green + "Done... " + endC)

    return result

#########################################################################
# FONCTION backGeocoding()                                              #
#########################################################################
#   Rôle : back geocoding de données rasters (au format .dim) dans l'outil SNAP
#   Paramètres In:
#       product : donnée snap d'entrée
#   Paramètres Out:
#     Return :
#       result : resultat de l'operation au format data snap

def backGeocoding(product):

    if debug >= 2:
        print(cyan + "backGeocoding() : " + bold + green + "Run to SNAP... " + endC )

    # Instance de GPF
    GPF.getDefaultInstance().getOperatorSpiRegistry().loadOperatorSpis()

    # Def operateur SNAP
    operator = 'Back-Geocoding'

    # Set des parametres
    parameters = HashMap()

    parameters.put("Digital Elevation Model", "SRTM 1Sec HGT (Auto Download)")
    parameters.put("DEM Resampling Method", "BICUBIC_INTERPOLATION")
    parameters.put("Resampling Type", "BISINC_5_POINT_INTERPOLATION")
    parameters.put("Mask out areas with no elevation", True)
    parameters.put("Output Deramp and Demod Phase", False)

    if debug >= 2:
        print(parameters)

    # Get snappy Operators
    result = GPF.createProduct(operator, parameters, product)

    if debug >= 2:
        print(cyan + "backGeocoding() : " + bold + green + "Done... " + endC)

    return result

#########################################################################
# FONCTION interferogram()                                              #
#########################################################################
#   Rôle : interferogram de données rasters (au format .dim) dans l'outil SNAP
#   Paramètres In:
#       product : donnée snap d'entrée
#   Paramètres Out:
#     Return :
#       result : resultat de l'operation au format data snap

def interferogram(product):

    if debug >= 2:
        print(cyan + "interferogram() : " + bold + green + "Run to SNAP... " + endC )

    # Instance de GPF
    GPF.getDefaultInstance().getOperatorSpiRegistry().loadOperatorSpis()

    # Def operateur SNAP
    operator = 'Interferogram'

    # Set des parametres
    parameters = HashMap()

    parameters.put("Subtract flat-earth phase", True)
    parameters.put("Degree of \"Flat Earth\" polynomial", 5)
    parameters.put("Number of \"Flat Earth\" estimation points", 501)
    parameters.put("Orbit interpolation degree", 3)
    parameters.put("Include coherence estimation", True)
    parameters.put("Square Pixel", False)
    parameters.put("Independent Window Sizes", False)
    parameters.put("Coherence Azimuth Window Size", 10)
    parameters.put("Coherence Range Window Size", 10)

    if debug >= 2:
        print(parameters)

    # Get snappy Operators
    result = GPF.createProduct(operator, parameters, product)

    if debug >= 2:
        print(cyan + "interferogram() : " + bold + green + "Done... " + endC)

    return result

#########################################################################
# FONCTION topsarDeburst()                                              #
#########################################################################
#   Rôle : topsar deburst de données rasters (au format .dim) dans l'outil SNAP
#   Paramètres In:
#       product : donnée snap d'entrée
#   Paramètres Out:
#     Return :
#       result : resultat de l'operation au format data snap

def topsarDeburst(product):

    if debug >= 2:
        print(cyan + "topsarDeburst() : " + bold + green + "Run to SNAP... " + endC )

    # Instance de GPF
    GPF.getDefaultInstance().getOperatorSpiRegistry().loadOperatorSpis()

    # Def operateur SNAP
    operator = 'TOPSAR-Deburst'

    # Set des parametres
    parameters = HashMap()

    parameters.put("Polarisations", "VV")

    if debug >= 2:
        print(parameters)

    # Get snappy Operators
    result = GPF.createProduct(operator, parameters, product)

    if debug >= 2:
        print(cyan + "topsarDeburst() : " + bold + green + "Done... " + endC)

    return result

#########################################################################
# FONCTION topophaseRemoval()                                           #
#########################################################################
#   Rôle : topophase removal de données rasters (au format .dim) dans l'outil SNAP
#   Paramètres In:
#       product : donnée snap d'entrée
#   Paramètres Out:
#     Return :
#       result : resultat de l'operation au format data snap
def topophaseRemoval(product):

    if debug >= 2:
        print(cyan + "topophaseRemoval() : " + bold + green + "Run to SNAP... " + endC )

    # Instance de GPF
    GPF.getDefaultInstance().getOperatorSpiRegistry().loadOperatorSpis()

    # Def operateur SNAP
    operator = 'TopoPhaseRemoval'

    # Set des parametres
    parameters = HashMap()

    parameters.put("Orbit Interpolation Degree", 3)
    parameters.put("Digital Elevation Model", "SRTM 1Sec HGT (Auto Download)")
    parameters.put("Tile Extension[%]", 100)
    parameters.put("Output topographic phase band", True)
    parameters.put("Output elevation band", False)

    if debug >= 2:
        print(parameters)

    # Get snappy Operators
    result = GPF.createProduct(operator, parameters, product)

    if debug >= 2:
        print(cyan + "topophaseRemoval() : " + bold + green + "Done... " + endC)

    return result

#########################################################################
# FONCTION goldsteinPhasefiltering()                                    #
#########################################################################
#   Rôle : goldstein phasefiltering de données rasters (au format .dim) dans l'outil SNAP
#   Paramètres In:
#       product : donnée snap d'entrée
#   Paramètres Out:
#     Return :
#       result : resultat de l'operation au format data snap

def goldsteinPhasefiltering(product):

    if debug >= 2:
        print(cyan + "goldsteinPhasefiltering() : " + bold + green + "Run to SNAP... " + endC )

    # Instance de GPF
    GPF.getDefaultInstance().getOperatorSpiRegistry().loadOperatorSpis()

    # Def operateur SNAP
    operator = 'GoldsteinPhaseFiltering'

    # Set des parametres
    parameters = HashMap()

    parameters.put("Adaptive Filter Exponent in(0,1]:", 1.0)
    parameters.put("FFT Size", 64)
    parameters.put("Window Size", 3)
    parameters.put("Use coherence mask", False)
    parameters.put("Coherence Threshold in[0,1]:", 0.2)

    if debug >= 2:
        print(parameters)

    # Get snappy Operators
    result = GPF.createProduct(operator, parameters, product)

    if debug >= 2:
        print(cyan + "goldsteinPhasefiltering() : " + bold + green + "Done... " + endC)

    return result

#########################################################################
# FONCTION bandMathSnap()                                               #
#########################################################################
#   Rôle : BandMath pour données rasters (au format .dim) dans l'outil SNAP
#   Paramètres In:
#       input_dim : entête de fichiers raster à importer
#       output_file : fichier de sortie
#       expression_list : liste d'expression BandMath à exécuter : exemple ['(radiance_10 - radiance_7) / (radiance_10 + radiance_7)', '(radiance_9 - radiance_6) / (radiance_9 + radiance_6)']
#       format_file : format du fichier de sortie par default : 'float32'

def bandMathSnap(input_dim, output_file, expression_list, format_file='float32'):

    if debug >= 2:
        print(cyan + "bandmathSnap() : " + bold + green + "Import Dim to SNAP : " + endC + input_dim )

    # Info input file
    product = ProductIO.readProduct(input_dim)
    width = product.getSceneRasterWidth()
    height = product.getSceneRasterHeight()
    name = product.getName()
    description = product.getDescription()
    band_names = product.getBandNames()

    if debug >= 2:
        print(cyan + "bandmathSnap() : " + bold + green + "Product: %s, %d x %d pixels, %s" % (name, width, height, description) + endC)
        print(cyan + "bandmathSnap() : " + bold + green + "Bands:   %s" % (list(band_names)) + endC)

    # Instance de GPF
    GPF.getDefaultInstance().getOperatorSpiRegistry().loadOperatorSpis()

    # Def operateur SNAP
    operator = 'BandMaths'
    BandDescriptor = jpy.get_type('org.esa.snap.core.gpf.common.BandMathsOp$BandDescriptor')
    targetBands = jpy.array('org.esa.snap.core.gpf.common.BandMathsOp$BandDescriptor', len(expression_list))

    # Get des expressions d'entréées
    i = 0
    for expression in expression_list :
        targetBand = BandDescriptor()
        targetBand.name = 'band_' + str(i+1)
        targetBand.type = format_file
        targetBand.expression = expression
        targetBands[i] = targetBand
        i += 1

    # Set des parametres
    parameters = HashMap()
    parameters.put('targetBands', targetBands)

    # Get snappy Operators
    result = GPF.createProduct(operator, parameters, product)
    ProductIO.writeProduct(result, output_file, 'BEAM-DIMAP')

    if debug >= 2:
        print(cyan + "bandmathSnap() : " + bold + green + "Writing Done : " + endC + str(output_file))

    return result

#########################################################################
# FONCTION plot2Snap()                                                  #
#########################################################################
#   Rôle : tacer de données rasters (au format .dim) avec mathplotlib
#   Paramètres In:
#       input_dim : entête de fichiers raster à importer
#       name_file : nom du fichier à extraire du .dim
#       output_png_plot : fichier png de sorte

def plot2Snap(input_dim, name_file, output_png_plot):

    if debug >= 2:
        print(cyan + "plot2Snap() : " + bold + green + "Plot band : " + endC + name_file + bold + green + " from Dim file..." + endC)
    product, band_names_list = readDim(input_dim)
    band = product.getBand(name_file)
    w = band.getRasterWidth()
    h = band.getRasterHeight()
    if debug >= 2:
        print(cyan + "plot2Snap() : " + bold + green + "h = " + str(h) + endC)
        print(cyan + "plot2Snap() : " + bold + green + "w = " + str(w) + endC)
    band_data = np.zeros(w * h, np.float32)
    band.readPixels(0, 0, w, h, band_data)
    product.dispose()
    band_data.shape = h, w
    imgplot = plt.imshow(band_data)
    imgplot.write_png(output_png_plot)
    return
