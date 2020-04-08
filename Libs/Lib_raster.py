# -*- coding: utf-8 -*-
#!/usr/bin/python

#############################################################################
# Copyright (©) CEREMA/DTerSO/DALETT/SCGSI  All rights reserved.            #
#############################################################################

#############################################################################
#                                                                           #
# FONCTIONS DE BASE SUR LES RASTERS                                         #
#                                                                           #
#############################################################################
#
# Ce module contient un certain nombre de fonctions de bases pour réaliser des traitement sur les images raster, ils reposent tous sur les bibliothèques GDAL et OTB
#


# IMPORTS DIVERS
from __future__ import print_function
import os,glob,sys,shutil,time
import gdal,osr,numpy, gdalnumeric
from gdalconst import *
from PIL import Image
from pylab import *
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC
from Lib_vector import getEmpriseFile
from Lib_text import writeTextFile, appendTextFileCR
from Lib_file import renameFile, removeFile
from Lib_xml import parseDom, getListNodeDataDom, getListValueAttributeDom
#import otbApplication

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 3 : affichage maximum de commentaires lors de l'execution du script. Intermédiaire : affichage intermédiaire

debug = 2

#########################################################################
# FONCTION computeHistogram ()                                          #
#########################################################################
#   Rôle : Cette fonction calcul l'histogramme d'une image.
#   Paramètres :
#       image_raster : fichier image d'entrée
#       hist_file : image de l'histogramme en sortie (formats supportés : eps, jpeg, jpg, pdf, pgf, png, ps, raw, rgba, svg, svgz, tif, tiff)
#       plot_title : titre du graphique. Par défaut, "Histogramme raster"
#       x_title : titre de l'axe X. Par défaut, "Valeur de pixels"
#       y_title : titre de l'axe Y. Par défaut, "Fréquence"
#       x_axe : plage de valeurs X à afficher, au format [x_min, x_max, pas]. Par défaut, [1,4095,1]
#       buckets : nombre de classes pour générer l'histogramme (si 0, générer automatiquement suivant paramètre 'x_axe'). Par défaut, 0
#       figsize : taille du graphique, au format [largeur, hauteur]. Par défaut, [20,10]
#       fontsize : taille des caractères du graphique. Par défaut, 20
#       show_plot : affiche le graphique dans une fenêtre matplotlib à la fin de la fonction. Par défaut, False
#       colors_bands_list : liste des couleurs affectées à chaque bande. Par défaut, ['red','green','blue','magenta']
#   Paramétres de retour :
#       histogram_list : l'histogramme de chaque bande
#
#   Exemples d'utilisation du paramètre 'colors_bands_list' :
#       - ['red','green','blue','magenta'] pour une image 4 bandes R-V-B-PIR : Pléiades, SPOT-6/7
#       - ['grey'] pour une image 1 bande : radar, MNH, NDVI
#       - ['red','green','blue','darkred','magenta'] pour une image 5 bandes R-V-B-RE-PIR : RapidEye
#       - ['magenta','red','green','purple'] pour une image 4 bandes PIR-R-V-MIR : SPOT-5
#       - ['cyan','blue','green','red','darkred','brown','salmon','magenta','orchid','violet','blueviolet','purple','indigo'] pour une image multispectrale type Sentinel-2 (si l'ordre des 13 bandes est respecté dans l'image d'entrée)
#   La liste des couleurs est disponible ici : https://matplotlib.org/_images/sphx_glr_named_colors_003.png

def computeHistogram(image_raster, hist_file, plot_title="Histogramme raster", x_title="Valeur de pixel", y_title="Fréquence", x_axe=[1,4095,1], buckets=0, figsize=[20,10], fontsize=20, show_plot=False, colors_bands_list = ['red','green','blue','magenta']):
    if debug >= 3:
         print(cyan + "computeHistogram(): Identification des pixels de l'image." + endC)

    # Gestion du raster d'entrée (ouverture et récup nb bandes))
    dataset = gdal.Open(image_raster, GA_ReadOnly)
    if dataset is None:
        return None

    nb_bands = dataset.RasterCount
    nb_colors_bands = len(colors_bands_list)
    if nb_colors_bands != nb_bands:
        print(red + bold + "computeHistogram(): Il y a " + str(nb_bands) + " bandes dans le raster pour " + str(nb_colors_bands) + " couleurs renseignées (dans 'colors_bands_list')." + endC)
        return None

    # Gestion de l'axe des X (min, max, et nb classes)
    x_min, x_max, x_step = x_axe[0], x_axe[1], x_axe[2]
    if buckets > 0:
        x_step = (x_max - x_min) / buckets
    x_list = np.arange(x_min, x_max+x_step, x_step)
    buckets = len(x_list)

    # Initialisation du graph
    plt.rcParams.update({'font.size': fontsize})
    plt.figure(figsize=(figsize[0], figsize[1]))
    plt.grid(True)
    plt.title(plot_title)
    plt.xlabel(x_title)
    plt.ylabel(y_title)

    # Génération du graph bande par bande
    histogram_dico = {}
    for number_band in range(1,nb_bands+1):
        band = dataset.GetRasterBand(number_band)
        legend = "Bande " + str(number_band)
        color = colors_bands_list[number_band-1]
        histogram = band.GetHistogram(min=x_min, max=x_max, buckets=buckets, approx_ok=0)
        plt.plot(x_list, histogram, "-", linewidth=2, label=legend, c=color)
        histogram_dico[number_band] = histogram

    # Finalisation du graph
    plt.legend()
    plt.tight_layout()
    plt.savefig(hist_file)

    if debug >=3:
        print(cyan + "computeHistogram(): Sauvegarde de l'histogramme en fichier : " + hist_file + endC)

    if show_plot:
        plt.show()

    return histogram_dico

#########################################################################
# FONCTION computeStatisticsImage ()                                    #
#########################################################################
#   Rôle : Cette fonction calcul les statisiques d'une image la moyenne et ecart type  pour chaque bande
#   Utilité : Resultat sous forme de fichier xml identique à la fonction OTB ComputeImagesStatistics qui ne fonctionne pas avec des images trop importante
#   Paramètres :
#       image_raster : fichier image d'entrée
#       statistic_file : image du resulatt statistique en sortie (en .xml)
#   Paramétres de retour :
#       none

def computeStatisticsImage(image_raster, statistic_file):
    if debug >= 3:
         print(cyan + "computeHistogram() : Calcul des statistiques de l'image" +  image_raster + endC)

    bands = 0
    dataset = gdal.Open(image_raster, GA_ReadOnly) # Ouverture de l'image en lecture
    if dataset is not None:
        bands = dataset.RasterCount

    # Calcul de  la moyenne et ecart type avec numpy
    staistic_dico = {}
    for i in range (1, bands+1) :
        image = dataset.GetRasterBand(i)
        image_array = image.ReadAsArray()
        image_mean = numpy.mean(image_array)
        image_std = numpy.std(image_array)
        staistic_dico[i] = [image_mean, image_std]

    # Ecriture des resultats dans un fichier xml
    writeTextFile(statistic_file, '<?xml version="1.0" ?>\n')
    appendTextFileCR(statistic_file, '<FeatureStatistics>')
    appendTextFileCR(statistic_file, '    <Statistic name="mean">')
    for i in range (1, bands+1) :
         appendTextFileCR(statistic_file, '        <StatisticVector value="%s" />' %(staistic_dico[i][0]))
    appendTextFileCR(statistic_file, '    </Statistic>')
    appendTextFileCR(statistic_file, '    <Statistic name="stddev">')
    for i in range (1, bands+1) :
        appendTextFileCR(statistic_file, '        <StatisticVector value="%s" />' %(staistic_dico[i][1]))
    appendTextFileCR(statistic_file, '    </Statistic>')
    appendTextFileCR(statistic_file, '</FeatureStatistics>')

    if debug >=3:
        print(cyan + "computeStatisticsImage() : Fin du calcul statistique ecriture du fichier statistique : " + statistic_file + endC)
    return

#########################################################################
# FONCTION identifyPixelValues ()                                       #
#########################################################################
#   Rôle : Cette fonction identifie les valeurs présentes dans une image
#   Paramètres :
#       image_raster : fichier image d'entrée
#   Paramétres de retour :
#       image_values_list : liste des differentes valeurs des pixels
#
#   Exemple d'utilisation: image_values_list = identifyPixelValues(image_raster)

def identifyPixelValues(image_raster):

    if debug >= 3:
        print(cyan + "identifyPixelValues() : Début de l'identification des pixels de l'image" + endC)

    image_values_list = []
    image_open = gdal.Open(image_raster)                  # Ouverture de l'image
    if image_open != None :
        image = image_open.GetRasterBand(1)                   # Extraction de la premiere bande
        image_array = image.ReadAsArray()                     # Transformation de la bande en tableau
        image_values_nparray = numpy.unique(image_array)      # Extraction des valeurs uniques dans un tableau numpy
        image_values_list = image_values_nparray.tolist()     # Transformation du tableau en liste
        image_open = None

    if debug >= 3:
        print(cyan + "identifyPixelValues() : Fin de l'identification des pixels de l'image" + endC)

    return image_values_list

#########################################################################
# FONCTION countPixelsOfValueBis()                                      #
#########################################################################
#   Rôle : Cette fonction compte le nombre de pixels d'une valeur donnée
#   Codage : Utilisation de la lib "Image"
#   Paramètres :
#       image_raster : fichier image d'entrée
#       value : valeur du pixel dont on recherche l'occurence dans l'image
#   Paramétres de retour :
#       pixelCount : le nombre de pixel correspondant à la valeur recherché
#
#   Exemple d'utilisation: trainingSetSize = countPixelsOfValue("testMask.tif",10)

def countPixelsOfValueBis(image_raster, value):

    if debug >= 3:
        print(cyan + "countPixelsOfValueBis() : " + bold + green + "Image input to count pixel : "  + endC + image_raster)

    # Ouverture de l'image
    image = Image.open(image_raster)

    #matrice_image = image.load()
    #haut,larg = image.size

    # Intialisation
    pixelCount = 0

    # Test nombre de pixel
    value_f = value + 0.0
    infoPixel = image.getcolors()
    for info in infoPixel:

        if info[1] == value_f:
            pixelCount = info[0]

    # Fermeture de l'image
    image.close()

    if debug >= 3:
        print(bold + green + "countPixelsOfValueBis() : NumberBandReadAsArray of pixel with value " + str(value) + " : " + str(pixelCount) + endC)

    return pixelCount

#########################################################################
# FONCTION countPixelsOfValue()                                         #
#########################################################################
#   Rôle : Cette fonction compte le nombre de pixels d'une valeur donnée
#   Codage : Utilisation de la lib "numpy"
#   Paramètres :
#       image_raster : fichier image binaire d'entrée
#       value : valeur du pixel dont on recherche l'occurence dans l'image
#       num_band : la valeur de la bande choisi par defaut bande 1
#   Paramétres de retour :
#       pixelCount : le nombre de pixel correspondant à la valeur recherché
#
#   Exemple d'utilisation: trainingSetSize = countPixelsOfValue("testMask.tif",1)

def countPixelsOfValue(image_raster, value, num_band=1):

    if debug >= 3:
        print(cyan + "countPixelsOfValue() : " + bold + green + "Image input to count pixel : "  + endC + image_raster)

    # Ouverture de l'image

    dataset = gdal.Open(image_raster, GA_ReadOnly)

    # Intialisation
    pixelCount = 0

    if dataset is not None:
        cols = dataset.RasterXSize
        rows = dataset.RasterYSize
        # Get band
        band = dataset.GetRasterBand(num_band)
        # Read the data into arrays
        data = gdalnumeric.BandReadAsArray(band)

        unique, counts = numpy.unique(data, return_counts=True)
        unique_list = unique.tolist()
        if value in unique_list :
            counts_list = counts.tolist()
            index = unique_list.index(value)
            pixelCount = counts_list[index]

    dataset = None

    if debug >= 3:
        print(cyan + "countPixelsOfValue() : " + bold + green + "Number of pixel with value1 " + str(value) + " : " + str(pixelCount) + endC)

    return pixelCount

#########################################################################
# FONCTION getPixelSizeImage()                                          #
#########################################################################
#   Rôle : Cette fonction permet de retourner la taille d'un pixel de l'image
#   Paramètres :
#       image_raster : fichier image d'entrée
#   Paramétres de retour :
#       pixel_size : la taille d'un pixel de l'image (surface)

def getPixelSizeImage(image_raster):

    pixel_size = 0.0
    dataset = gdal.Open(image_raster, GA_ReadOnly)
    if dataset is not None:
        geotransform = dataset.GetGeoTransform()
        pixel_width = geotransform[1]  # w-e pixel resolution
        pixel_height = geotransform[5] # n-s pixel resolution
        pixel_size = pixel_width * pixel_height
    dataset = None

    return abs(pixel_size)

#########################################################################
# FONCTION getPixelWidthXYImage()                                       #
#########################################################################
#   Rôle : Cette fonction permet de retourner les dimensions d'un pixel de l'image en X et en Y
#   Paramètres :
#       image_raster : fichier image d'entrée
#   Paramétres de retour :
#       pixel_width : la dimension d'un pixel en largeur
#       pixel_height : la dimension d'un pixel en hauteur

def getPixelWidthXYImage(image_raster):

    pixel_width = 0.0
    pixel_height = 0.0
    dataset = gdal.Open(image_raster, GA_ReadOnly)
    if dataset is not None:
        geotransform = dataset.GetGeoTransform()
        pixel_width = geotransform[1]  # w-e pixel resolution
        pixel_height = geotransform[5] # n-s pixel resolution
    dataset = None

    return pixel_width, pixel_height

#########################################################################
# FONCTION getPixelValueImageGeographical()                             #
#########################################################################
#   Rôle : Cette fonction permet de retourner la valeur d'un pixel de l'image défini par ses coordonnées X et Y geographiques
#   Paramètres :
#       image_raster : fichier image d'entrée
#       coor_x   : coordonnée géographique du pixel en X
#       coor_y   : coordonnée géographique du pixel en Y
#       num_band : la valeur de la bande choisi par defaut bande 1
#   Paramétres de retour :
#       value_pixel : la valeur un pixel dont les coordonnees sont defini en x et en y

def getPixelValueImageGeographical(image_raster, coor_x, coor_y, num_band=1):

    cols, rows, bands = getGeometryImage(image_raster)
    xmin, xmax, ymin, ymax = getEmpriseImage(image_raster)
    pixel_width, pixel_height = getPixelWidthXYImage(image_raster)

    pos_x = int(round((coor_x - xmin) / abs(pixel_width)))
    pos_y = int(round((coor_y - ymin) / abs(pixel_height)))

    return getPixelValueImage(image_raster, pos_x, pos_y, num_band)

#########################################################################
# FONCTION getPixelValueImage()                                         #
#########################################################################
#   Rôle : Cette fonction permet de retourner la valeur d'un pixel de l'image défini par ses postions X et Y dans la matrice image
#   Paramètres :
#       image_raster : fichier image d'entrée
#       pos_x   : position du pixel en X
#       pos_y   : position du pixel en Y
#       num_band : la valeur de la bande choisi par defaut bande 1
#   Paramétres de retour :
#       value_pixel : la valeur un pixel dont la position est defini en x et en y

def getPixelValueImage(image_raster, pos_x, pos_y, num_band=1):

    value_pixel = None
    dataset = gdal.Open(image_raster, GA_ReadOnly)
    if dataset is not None:
        # Get band
        band = dataset.GetRasterBand(num_band)
        # Read the data into arrays
        data = gdalnumeric.BandReadAsArray(band)
        value_pixel = data[pos_y, pos_x]
    dataset = None

    return value_pixel

#########################################################################
# FONCTION getDataTypeImage()                                           #
#########################################################################
#   Rôle : Cette fonction permet de retourner le type de data de l'image (UInt8, Uint16, Float32...)
#   Paramètres :
#       image_raster : fichier image d'entrée
#       num_band     : la valeur de la bande choisi par defaut bande 1
#   Paramétres de retour :
#       data_type : le type des data si defini None sinon

def getDataTypeImage(image_raster, num_band=1):

    data_type = None

    dataset = gdal.Open(image_raster, GA_ReadOnly)
    if dataset is not None:
        # Get band
        band = dataset.GetRasterBand(num_band)
        if band != None :
            # Read the nodata band
            data_type =  gdal.GetDataTypeName(band.DataType)
            band = None

    dataset = None

    return data_type

#########################################################################
# FONCTION getNodataValueImage()                                        #
#########################################################################
#   Rôle : Cette fonction permet de retourner la valeur du nodata defini pour l'image ou None si le nodata n'est pas défini
#   Paramètres :
#       image_raster : fichier image d'entrée
#       num_band     : la valeur de la bande choisi par defaut bande 1
#   Paramétres de retour :
#       no_data_value : la valeur des pixels nodata si defini None sinon

def getNodataValueImage(image_raster, num_band=1):

    no_data_value = None

    dataset = gdal.Open(image_raster, GA_ReadOnly)
    if dataset is not None:
        # Get band
        band = dataset.GetRasterBand(num_band)
        if band != None :
            # Read the nodata band
            no_data_value = band.GetNoDataValue()
            band = None

    dataset = None

    return no_data_value

#########################################################################
# FONCTION SetNodataValueImage()                                        #
#########################################################################
#   Rôle : Cette fonction permet de d'affecter une même valeur de nodata pour toutes les bandes de l'image
#   Paramètres :
#       image_raster : fichier image d'entrée
#       no_data_value : la valeur des pixels nodata peut etre None si pas de valeur défini
#   Paramétres de retour :
#       le fichier d'entrée modifier


def setNodataValueImage(image_raster, no_data_value):

    dataset = gdal.Open(image_raster, GA_Update)
    if dataset is not None:
        # Get nb bands
        nb_bands = dataset.RasterCount
        for num_band in range(1,nb_bands+1) :
            # Get band
            band = dataset.GetRasterBand(num_band)
            # Write the nodata band
            if no_data_value == None:
                band.DeleteNoDataValue()
            else :
                band.SetNoDataValue(no_data_value)
            band.FlushCache()
            band = None

    dataset = None

    return

#########################################################################
# FONCTION getPixelsValueListImage()                                    #
#########################################################################
#   Rôle : Cette fonction permet de retourner la valeur d'un pixel de l'image défini par ses postions X et Y dans la matrice image
#   Paramètres :
#       image_raster : fichier image d'entrée
#       points_coordonnees_list : contenant une liste de coordonnes de point [[pos1_x, pos1_y], [pos2_x, pos2_y],...]
#                                   pos_x   : position du pixel en X
#                                   pos_y   : position du pixel en Y
#       num_band     : la valeur de la bande choisi par defaut bande 1
#   Paramétres de retour :
#       value_pixel_list : liste des valeurs des pixels dont les coordonnees sont defini en x et en y

def getPixelsValueListImage(image_raster, points_coordonnees_list, num_band=1):

    value_pixel_list = []

    dataset = gdal.Open(image_raster, GA_ReadOnly)
    if dataset is not None:
        # Get band
        band = dataset.GetRasterBand(num_band)
        # Read the data into arrays
        data = gdalnumeric.BandReadAsArray(band)
        # Pour tout les points recuperer leur valeur
        for coordonnees in points_coordonnees_list:
            value_pixel_list.append(data[coordonnees[1], coordonnees[0]])
    dataset = None

    return value_pixel_list

#########################################################################
# FONCTION getRawDataImage()                                            #
#########################################################################
#   Rôle : Cette fonction permet de retourner une matrice contenant des données brutes de l'image
#   Paramètres :
#       image_raster : fichier image d'entrée
#       num_band     : la valeur de la bande choisi par defaut bande 1
# Paramétres de retour :
#       data : la matrice brute de pixels de l'image

def getRawDataImage(image_raster, num_band=1):

    data = None

    # Ouverture de l'image
    dataset = gdal.Open(image_raster, GA_ReadOnly)

    if dataset is not None:
        # Get band
        band = dataset.GetRasterBand(num_band)
        # Read the data into arrays
        data = gdalnumeric.BandReadAsArray(band)

    return data

#########################################################################
# FONCTION getEmpriseImage()                                            #
#########################################################################
#   Rôle : Cette fonction permet de retourner les coordonnées xmin,xmax,ymin,ymax de l'emprise de l'image
#   Paramètres :
#       image_raster : fichier image d'entrée
#   Paramétres de retour :
#       xmin : valeur xmin de l'emprise de l'image
#       xmax : valeur xmax de l'emprise de l'image
#       ymin : valeur ymin de l'emprise de l'image
#       ymax : valeur ymax de l'emprise de l'image

def getEmpriseImage(image_raster):

    if debug >= 3:
        print(cyan + "getEmpriseImage() : Début de la récupération de l'emprise de l'image" + endC)

    xmin = 0
    xmax = 0
    ymin = 0
    ymax = 0
    if not os.path.isfile(image_raster) :
        raise NameError(bold + red + "getEmpriseImage() : File " + image_raster + " does not exist" + endC)

    dataset = gdal.Open(image_raster, GA_ReadOnly)
    if dataset is not None:
        cols = dataset.RasterXSize
        rows = dataset.RasterYSize
        geotransform = dataset.GetGeoTransform()
        pixel_width = geotransform[1]  # w-e pixel resolution
        pixel_height = geotransform[5] # n-s pixel resolution
        xmin = geotransform[0]     # top left x
        ymax = geotransform[3]     # top left y
        xmax = xmin + (cols * pixel_width)
        ymin = ymax + (rows * pixel_height)

    dataset = None
    if debug >= 3:
        print(cyan + "getEmpriseImage() : Fin de la récupération de l'emprise de l'image" + endC)

    return xmin, xmax, ymin, ymax

#########################################################################
# FONCTION roundPixelEmpriseSize()                                      #
#########################################################################
#   Rôle : Calcul des valeur arrondis d'une emprise arrondi à la taille du pixel de l'image
#   Paramètres :
#       pixel_size_x : Taille du pixel en x (en m)
#       pixel_size_y : Taille du pixel en y (en m)
#       empr_xmin    : L'emprise brute d'entrée coordonnée xmin
#       empr_xmax    : L'emprise brute d'entrée coordonnée xmax
#       empr_ymin    : L'emprise brute d'entrée coordonnée ymin
#       empr_ymax    : L'emprise brute d'entrée coordonnée ymax
#   Paramétres de retour :
#       round_xmin    : L'emprise corrigée de sortie coordonnée xmin
#       round_xmax    : L'emprise corrigée de sortie coordonnée xmax
#       round_ymin    : L'emprise corrigée de sortie coordonnée ymin
#       round_ymax    : L'emprise corrigée de sortie coordonnée ymax
#
def roundPixelEmpriseSize(pixel_size_x, pixel_size_y, empr_xmin, empr_xmax, empr_ymin, empr_ymax):

    # Calculer l'arrondi pour une emprise à la taille d'un pixel pres (+/-)
    val_round = abs(pixel_size_x)

    pos_xmin = int(floor(empr_xmin))
    round_xmin = pos_xmin - pos_xmin % val_round
    pos_xmax = int(ceil(empr_xmax))
    round_xmax = pos_xmax - pos_xmax % val_round
    if round_xmax < pos_xmax :
        round_xmax = round_xmax + val_round
    pos_ymin = int(floor(empr_ymin))
    round_ymin = pos_ymin - pos_ymin % val_round
    pos_ymax = int(ceil(empr_ymax))
    round_ymax = pos_ymax - pos_ymax % val_round
    if round_ymax < pos_ymax :
        round_ymax = round_ymax + val_round

    if debug >= 3:
        print(cyan + "roundPixelEmpriseSize : " + endC + "Emprise arrondi : " + endC)
        print("round_xmin : " + str(round_xmin) + endC)
        print("round_xmax : " + str(round_xmax) + endC)
        print("round_ymin : " + str(round_ymin) + endC)
        print("round_ymax : " + str(round_ymax) + endC)

    return round_xmin, round_xmax, round_ymin, round_ymax

#########################################################################
# FONCTION getMinMaxValueBandImage()                                    #
#########################################################################
#   Rôle : Cette fonction permet de récupérer la valeur minimale et maximale d'un canal d'une l'image
#   Paramètres :
#       image_raster : fichier image d'entrée
#       channel : Le numéro de bande de l'image
#   Paramétres de retour :
#       image_max_band : la valeur pixel minimale d'une bande de l'image
#       image_mini_band : la valeur pixel maximale d'une bande de l'image

def getMinMaxValueBandImage(image_raster, channel):

    dataset = gdal.Open(image_raster, GA_ReadOnly)
    band = dataset.GetRasterBand(channel)
    a = band.ComputeRasterMinMax()

    maximum = -65535.0
    minimum = 65535.0
    if maximum < a[1]:
        maximum =a [1]
    if minimum > a[0]:
        minimum = a[0]
    dataset = None

    # Valeur maximale des pixels sur la bande
    image_max_band = maximum
    # Valeur minimale des pixels sur la bande
    image_mini_band = minimum

    return image_max_band, image_mini_band

#########################################################################
# FONCTION getGeometryImage()                                           #
#########################################################################
#   Rôle : Cette fonction permet de retourner le nombre de colonne, le nombre de ligne et le nombre de bande de l'image
#   Paramètres :
#       image_raster : fichier image d'entrée
#   Paramétres de retour :
#       cols : le nombre de colonnes de l'image
#       rows : le nombre de lignes de l'image
#       bands : le nombre de bandes de l'image

def getGeometryImage(image_raster):

    cols = 0
    rows = 0
    bands = 0
    dataset = gdal.Open(image_raster, GA_ReadOnly)
    if dataset is not None:
        cols = dataset.RasterXSize
        rows = dataset.RasterYSize
        bands = dataset.RasterCount
    dataset = None

    return cols, rows, bands

#########################################################################
# FONCTION getProjectionImage()                                         #
#########################################################################
#   Rôle : Cette fonction permet de retourner la valeur de la projection de l'image
#   Paramètres :
#       image_raster : fichier image d'entrée
#   Paramétres de retour :
#       epsg : la valeur de la projection de l'image

def getProjectionImage(image_raster):

    epsg = 0
    dataset = gdal.Open(image_raster, GA_ReadOnly)
    if dataset is not None:

        srs = osr.SpatialReference()
        srs.ImportFromWkt(dataset.GetProjection())
        epsg = srs.GetAttrValue('AUTHORITY',1)
    dataset = None

    return epsg

#########################################################################
# FONCTION updateReferenceProjection()                                  #
#########################################################################
#   Rôle : Cette fonction permet de mettre a jour la projection d'un fichier avec un fichier de référence
#   Paramètres :
#       ref_image : fichier image donnant la projection de référence. Si aucune, mettre None
#       output_image : fichier image à modifier
#       epsg : choix du système de projection que l'on veut appliquer à l'image. Par exemple : epsg = 2154

def updateReferenceProjection (ref_image, output_image, epsg = 2154):

    # Ouverture du fichier a modifier
    try:
        dataset_output = gdal.Open(output_image, GA_Update)
    except RuntimeError as err:
        print(bold + red + "Erreur impossible d'ouvrir le fichier a modifier : " + output_image + endC, file=sys.stderr)
        e = "OS error: {0}".format(err)
        print(e, file=sys.stderr)

    srs = osr.SpatialReference()

    # Récupération du système de projection de l'image de référence
    if not ref_image == "" and not ref_image is None :
        try:
            dataset_input = gdal.Open(ref_image, GA_ReadOnly)
            projection = dataset_input.GetProjection()
            srs.ImportFromWkt(projection)
            epsg = srs.GetAttrValue('AUTHORITY',1)
            #new_geo = dataset_input.GetGeoTransform()
            #metaData = dataset_input.GetMetadata()

            if debug >= 3:
                print("epsg : " + str(epsg))

        except RuntimeError as err:
            print(bold + red + "Erreur impossible d'ouvrir le fichier de reference : " + ref_image + endC, file=sys.stderr)
            e = "OS error: {0}".format(err)
            print(e, file=sys.stderr)
    else :
        # Récupération du système du fichier origine
        srs.ImportFromWkt(dataset_output.GetProjectionRef())
        srs.ImportFromEPSG(int(epsg))
        projection = srs.ExportToWkt()
        #new_geo = dataset_output.GetGeoTransform()

    if debug >= 3:
        print("Spatial Reference projection : " + str(projection))
        srs=osr.SpatialReference(wkt=projection)
        if srs.IsProjected:
            print("projcs : " + str(srs.GetAttrValue('projcs')))
        print("geogcs : " +str(srs.GetAttrValue('geogcs')))

    # Mise a jour de la nouvelle projection  pour le fichier à mettre à jour
    #dataset_output.SetGeoTransform(new_geo)
    dataset_output.SetProjection(projection)

    # Close dataset
    dataset_input = None
    dataset_output = None

    return

#########################################################################
# FONCTION changeDataValueToOtherValue()                                #
#########################################################################
#   Rôle : Cette fonction permet de changer les pixels d'une image à une valeur donnée par une autre valeur résultat en fichier de sortie
#   Codage : Utilisation de la lib "gdal et numpy"
#   Paramètres :
#       image_input : fichier image d'entrée
#       image_output : fichier de sortie avec les pixels changés
#       value_to_change : valeur des pixels à changer
#       new_value : nouvel valeur des pixels
#       format_raster : Format de l'image de sortie par défaut GTiff (GTiff, HFA...)
#   Paramétres de retour :
#       le fichier de sortie avec les pixels changés

def changeDataValueToOtherValue(image_input, image_output, value_to_change,  new_value, format_raster="GTiff"):

    # Si le fichier de sortie existe deja
    if os.path.exists(image_output):
        os.remove(image_output)

    # Open the dataset
    dataset = gdal.Open(image_input, GA_ReadOnly)
    cols = dataset.RasterXSize
    rows = dataset.RasterYSize
    nb_bands = dataset.RasterCount
    band = dataset.GetRasterBand(1)

    # Write the out file
    driver = gdal.GetDriverByName(format_raster)
    dataset_out = driver.Create(image_output, cols, rows, nb_bands, band.DataType)
    gdalnumeric.CopyDatasetInfo(dataset, dataset_out)

    # For all bands
    for num_band in range(nb_bands) :
        num_band += 1

        # Get band
        band = dataset.GetRasterBand(num_band)

        # Read the data into numpy arrays
        data = gdalnumeric.BandReadAsArray(band)

        # Replace pixel value_to_change by new_value
        numpy_data = numpy.array(data)
        numpy_data[numpy_data == value_to_change] = new_value

        # Save new image
        band_out = dataset_out.GetRasterBand(num_band)
        band_out.WriteArray(numpy_data)

        band_out.FlushCache()
        band = None
        band_out = None

    # Close the datasets
    dataset = None
    dataset_out = None

    if debug >= 3:
        print(cyan + "changeDataValueToOtherValue() : " + bold + green + "Create file %s clean to % pixels complete!" %(image_output, str(value_to_change)) + endC)

    return

#########################################################################
# FONCTION changeDataValueToOtherValueBis()                             #
#########################################################################
#   Rôle : Cette fonction permet de changer les pixels d'une image à une valeur donnée par une autre valeur résultat en fichier de sortie
#   Codage : Utilisation de l'outil "OTB"
#   Paramètres :
#       image_input : fichier image d'entrée
#       image_output : fichier de sortie avec les pixels changés
#       value_to_change : valeur des pixels à changer
#       new_value : nouvel valeur des pixels
#       codage : type de codage du fichier de sortie
#   Paramétres de retour :
#       le fichier de sortie avec les pixels changés

def changeDataValueToOtherValueBis(image_input, image_output, value_to_change,  new_value, codage="uint16"):

    # Définir le nombre de bande de l'image d'entréé
    cols, rows, bands = getGeometryImage(image_input)

    # Création de l'expression
    # Exemple : "\"(im1=={0,0,0,0,0}?{1,1,1,1,1}:im1)\""

    expression = "\"(im1=={%s" %(str(value_to_change))
    for num_band in range(bands-1) :
        expression = expression + ",%s" %(str(value_to_change))

    expression = expression + "}?{%s" %(str(new_value))

    for num_band in range(bands) :
        expression = expression + ",%s" %(str(new_value))

    expression = expression + "}:im1)\""

    # BandmathX pour application de l'expression
    command = "otbcli_BandMathX -il %s -out %s %s -exp %s" %(image_input,image_output,codage,expression)
    if debug >= 3:
        print(command)
    exitCode = os.system(command)
    if exitCode != 0:
        print(command)
        raise NameError(bold + red + "changeDataValueToOtherValueBis() : An error occured during otbcli_BandMathX command. See error message above." + endC)

    if debug >= 3:
        print(cyan + "changeDataValueToOtherValueBis() : " + bold + green + "Create file %s clean to % pixels complete!" %(image_output, str(value_to_change)) + endC)

    return

#########################################################################
# FONCTION cutImageByVector()                                           #
#########################################################################
#   Rôle : Cette fonction découpe une image (.tif) par un vecteur (.shp)
#   Paramètres :
#       cut_shape_file : le nom du shapefile de découpage (exple : "/chemin/path_clipper.shp"
#       input_image : le nom de l'image à traiter (exmple : "/users/images/image_raw.tif")
#       output_image : le nom de l'image resultat découpée (exmple : "/users/images/image_cut.tif")
#       pixel_size_x : taille du pixel de sortie en x
#       pixel_size_y : taille du pixel de sortie en y
#       no_data_value : valeur de l'image d'entrée à transformer en NoData dans l'image de sortie
#       epsg : Valeur de la projection par défaut 0, si à 0 c'est la valeur de projection du fichier raster d'entrée qui est utilisé automatiquement
#       format_raster : le format du fichier de sortie, par defaut : 'GTiff'
#       format_vector : format du fichier vecteur, par defaut : 'ESRI Shapefile'
#
#   Return True si l'operataion c'est bien passé, False sinon

def cutImageByVector(cut_shape_file ,input_image, output_image, pixel_size_x=None, pixel_size_y=None, no_data_value=0, epsg=0, format_raster="GTiff", format_vector='ESRI Shapefile'):

    if debug >= 3:
        print(cyan + "cutImageByVector() : Vecteur de découpe des l'image : " + cut_shape_file + endC)
        print(cyan + "cutImageByVector() : L'image à découper : " + input_image + endC)

    # Constante
    EPSG_DEFAULT = 2154

    ret = True

    # Récupération de la résolution du raster d'entrée
    if pixel_size_x == None or pixel_size_y == None :
        pixel_size_x, pixel_size_y = getPixelWidthXYImage(input_image)

    if debug >= 5:
        print("Taille des pixels : ")
        print("pixel_size_x = " + str(pixel_size_x))
        print("pixel_size_y = " + str(pixel_size_y))
        print("\n")

    # Récuperation de l'emprise de l'image
    ima_xmin, ima_xmax, ima_ymin, ima_ymax = getEmpriseImage(input_image)

    if debug >= 5:
        print("Emprise raster : ")
        print("ima_xmin = " + str(ima_xmin))
        print("ima_xmax = " + str(ima_xmax))
        print("ima_ymin = " + str(ima_ymin))
        print("ima_ymax = " + str(ima_ymax))
        print("\n")

    # Récuperation de la projection de l'image
    if epsg == 0:
        epsg_proj = getProjectionImage(input_image)
    else :
        epsg_proj = epsg
    if epsg_proj == 0:
        epsg_proj = EPSG_DEFAULT

    if debug >= 3:
        print(cyan + "cutImageByVector() : EPSG : " + str(epsg_proj) + endC)

    # Identification de l'emprise de vecteur de découpe
    empr_xmin, empr_xmax, empr_ymin, empr_ymax = getEmpriseFile(cut_shape_file, format_vector)

    if debug >= 5:
        print("Emprise vector : ")
        print("empr_xmin = " + str(empr_xmin))
        print("empr_xmax = " + str(empr_xmax))
        print("empr_ymin = " + str(empr_ymin))
        print("empr_ymax = " + str(empr_ymax))
        print("\n")

    # Calculer l'emprise arrondi
    xmin, xmax, ymin, ymax = roundPixelEmpriseSize(pixel_size_x, pixel_size_y, empr_xmin, empr_xmax, empr_ymin, empr_ymax)

    if debug >= 5:
        print("Emprise vecteur arrondi a la taille du pixel : ")
        print("xmin = " + str(xmin))
        print("xmax = " + str(xmax))
        print("ymin = " + str(ymin))
        print("ymax = " + str(ymax))
        print("\n")

    # Trouver l'emprise optimale
    opt_xmin = xmin
    opt_xmax = xmax
    opt_ymin = ymin
    opt_ymax = ymax

    if ima_xmin > xmin :
        opt_xmin = ima_xmin
    if ima_xmax < xmax :
        opt_xmax = ima_xmax
    if ima_ymin > ymin :
        opt_ymin = ima_ymin
    if ima_ymax < ymax :
        opt_ymax = ima_ymax

    if debug >= 5:
        print("Emprise retenu : ")
        print("opt_xmin = " + str(opt_xmin))
        print("opt_xmax = " + str(opt_xmax))
        print("opt_ymin = " + str(opt_ymin))
        print("opt_ymax = " + str(opt_ymax))
        print("\n")

    # Découpage grace à gdal
    command = 'gdalwarp -t_srs EPSG:%s  -te %s %s %s %s -tap -multi -co "NUM_THREADS=ALL_CPUS" -tr %s %s -dstnodata %s -cutline %s -overwrite -of %s %s %s' %(epsg_proj, opt_xmin, opt_ymin, opt_xmax, opt_ymax, pixel_size_x, pixel_size_y, no_data_value, cut_shape_file, format_raster, input_image, output_image)

    if debug >= 4:
        print(command)

    exit_code = os.system(command)
    if exit_code != 0:
        print(command)
        print(cyan + "cutImageByVector() : " + bold + red + "!!! Une erreur c'est produite au cours du decoupage de l'image : " + input_image + ". Voir message d'erreur." + endC, file=sys.stderr)
        ret = False

    else :
        if debug >= 4:
            print(cyan + "cutImageByVector() : L'image résultat découpée : " + output_image + endC)

    return ret

#########################################################################
# FONCTION reallocateClassRaster()                                      #
#########################################################################
#   Rôle : Cette fonction permet de réaffecter des valeurs de pixels par d'autre valeurs
#   Paramètres :
#       input_image : fichier image à réaffecter
#       output_image : fichier image de sortie
#       reaff_value_list : liste des valeurs à réaffecter
#       change_reaff_value_list : liste des valeurs de réaffectation
#       codage : type de codage du fichier de sortie

def reallocateClassRaster(input_image, output_image, reaff_value_list, change_reaff_value_list, codage="uint16"):

    if not reaff_value_list == []:

        # Creation du fichier image de sortie
        name_file = os.path.splitext(input_image)[0]
        extension_file = os.path.splitext(input_image)[1]
        if output_image is None :
            image_output_tmp = name_file + "_tmp" + extension_file
        else :
            image_output_tmp = output_image

        # Creation de l'expression
        expression = "\""

        # Pour toute les classes à reallouer
        for idx_class in range(len(reaff_value_list)):
            class_to_realloc = reaff_value_list[idx_class]
            new_realloc_class = change_reaff_value_list[idx_class]
            expression = expression + "(im1b1==%d?%d:" %(class_to_realloc,new_realloc_class)

        # Fermeture des parenthèse de l'expression
        expression = expression + "im1b1"
        for idx_class in range(len(reaff_value_list)):
            expression = expression + ")"
        final_expression = expression + "\""

        if debug >= 3:
            print(cyan + "reallocateClassRaster() : " + endC + "input_image = " + input_image)
            print(cyan + "reallocateClassRaster() : " + endC + "image_output = " + image_output_tmp)
            print(cyan + "reallocateClassRaster() : " + endC + "final_expression = " + final_expression)

        command = "otbcli_BandMath -il %s -out %s %s -exp %s" %(input_image,image_output_tmp,codage,final_expression)

        # Application du BandMath
        if debug >= 3:
            print(cyan + "reallocateClassRaster() : " + endC + "command : " +  str(command))

        print(cyan + "reallocateClassRaster() : " + bold + green + "Reallocation of %s : START" %(input_image) + endC)

        exitCode = os.system(command)
        if exitCode != 0:
            print(command)
            raise NameError(bold + red + "reallocateClassRaster() : An error occured during otbcli_BandMath command. See error message above." + endC)

        # Renommage du fichier d'entrée avec le fichier modifié temporaire dans le cas où aucun fichier de sortie n'est donné
        if output_image is None:
            os.remove(input_image)
            os.rename(image_output_tmp, input_image)

        print(cyan + "reallocateClassRaster() : " + bold + green + "Reallocation of %s : COMPLETE" %(input_image) + endC)

    else :
        print(cyan + "reallocateClassRaster() : " + bold + yellow + "Not class to realloc, file %s not change!" %(input_image) + endC)

    return

#########################################################################
# FONCTION mergeListRaster()                                            #
#########################################################################
#   Rôle : Cette fonction permet de merger plusieurs fichier raster en un seul fichier raster
#          La priorité des pixels est l'ordre de position dans la liste (le premier est le plus prioritaire sur les autres et ainsi de suite))
#   Paramètres :
#       input_images_list :liste des fichiers images à merger
#       output_merge_image : fichier image de sortie fusionné
#       codage : type de codage du fichier de sortie

def mergeListRaster(input_images_list, output_merge_image, codage="uint16"):

    if debug >= 3:
        print(cyan + "mergeListRaster() : " + endC + "Fusion de plusieurs images raster en une seule")
        print("input_images_list = " + str(input_images_list))
        print("output_merge_image = " + str(output_merge_image))
        print("codage = " + str(codage))

    MIN_NB_IMAGES = 1

    # Début de la fonction BandMath
    command = "otbcli_BandMath -il "

    # Début et milieu de l'expression BandMath
    expression = "\"("

    length_input = len(input_images_list)

    if length_input > MIN_NB_IMAGES:

        # Récupération des images d'entrées
        for image_info in input_images_list :
            command = command + "%s " %(image_info)

        # Le ficher de sortie
        command = command + "-out %s %s " %(output_merge_image, codage)

        # Pour toutes les images
        num_image = 1
        while num_image <=  length_input :
            expression = expression + "im%db1!=0?im%db1:" %(num_image,num_image)
            num_image = num_image + 1

        # Assemblage de l'expression
        final_expression = expression + "0)\""

        if debug >= 3:
            print("Expression = " + final_expression)

        # Fin de la fonction BandMath
        command = command + " -exp %s " %(final_expression)

        if debug >= 2:
            print(command)

        exitCode = os.system(command)
        if exitCode != 0:
            print(command)
            raise NameError(bold + red + "mergeListRaster() : An error occured during otbcli_BandMath command. See error message above." + endC)

        print(cyan + "mergeListRaster() : " + endC + "Les images d'entrées ont ete mergées")
    else :
        if length_input == 1:
            shutil.copy2(input_images_list[0], output_merge_image)
        print(cyan + "mergeListRaster() : " + bold + yellow + "Pas d'images à merger" + endC)

    return

#########################################################################
# FONCTION deletePixelsSuperpositionMasks()                             #
#########################################################################
#   Rôle : Cette fonction permet de reperer les pixels ayant de l'information binaire sur plusieurs images (0 et 1) et de les supprimer sur toutes ces images
#   Paramètres :
#       images_input_list : liste des images à nettoyer les pixels superposés
#       images_output_list :  liste des images résultats du nettoyage
#       image_name : nom de l'image de référence pour l'image de nettoyage
#       codage : type de codage du fichier de sortie

def deletePixelsSuperpositionMasks(images_input_list, images_output_list, image_name='image', codage="uint16"):

    if debug >= 3:
        print(cyan + "deletePixelsSuperpositionMasks() : " + endC + "Nettoyage des pixels superposer sur plusieurs images masques")
        print("images_input_list = " + str(images_input_list))
        print("images_output_list = " + str(images_output_list))
        print("image_name = " + str(image_name))
        print("codage = " + str(codage))

    MIN_NB_IMAGES = 2

    # Début de la fonction BandMath
    command = "otbcli_BandMath -il "

    # Début et milieu de l'expression BandMath
    expression = "\"(sum(im1b1"

    length_input = len(images_input_list)
    length_output = len(images_output_list)

    num_image = MIN_NB_IMAGES

    # Image de nettoyage
    if length_input != length_output:
        raise NameError(bold + red + "deletePixelsSuperpositionMasks() : Error le nombre d'images d'entrée est différents du nombre d'image de sortie" + endC)

    elif length_input > MIN_NB_IMAGES:

        repertory_output = os.path.dirname(images_output_list[0])
        extension_file = os.path.splitext(os.path.basename(images_input_list[0]))[1]
        cleaning_image = repertory_output + os.sep + image_name + "_cleaning" + extension_file

        # Etape 1 : Repérage des superpositions et création du fichier de nettoyage

        # Récupération des images et écriture de l'expression du BandMath
        for image_info in images_input_list :
            command = command + "%s " %(image_info)
            if num_image <= length_input :
                expression = expression + ",im%db1" %(num_image)
                num_image = num_image + 1

        # Assemblage de l'expression
        final_expression = expression + ")>1?1:0)\""

        if debug >= 2:
            print("Expression = " + final_expression)

        # Fin de la fonction BandMath
        command = command + "-out %s " %(cleaning_image)
        command = command + "%s -exp %s " %(codage,final_expression)

        if debug >= 3:
            print("Reperage et creation du fichier de nettoyage")
            print(command)

        exitCode = os.system(command)
        if exitCode != 0:
            print(command)
            raise NameError(bold + red + "deletePixelsSuperpositionMasks() : An error occured during otbcli_BandMath command. See error message above." + endC)

        # Etape 2 : Création d'images nettoyées
        for idx_image in range (len(images_input_list)) :
            # Récupération du nom des images
            image_origin = images_input_list[idx_image]

            # Attribution du nom de l image nettoyée en sortie
            image_cleaned = images_output_list[idx_image]

            # Expression
            expression = "\"(im1b1!=0 and im2b1!=0?0:im1b1)\""
            command = "otbcli_BandMath -il %s %s -out %s %s -exp %s" %(image_origin,cleaning_image,image_cleaned,codage,expression)

            if debug >= 3:
                print("Expression2 = " + expression)
                print(command)

            exitCode = os.system(command)
            if exitCode != 0:
                print(command)
                raise NameError(bold + red + "deletePixelsSuperpositionMasks() : An error occured during otbcli_BandMath command. See error message above." + endC)

        #  Etape 3 : Suprimer l'image temporaire de nettoyage
        try:
            os.remove(cleaning_image)
        except Exception:
            pass # Si le fichier ne peut pas être supprimé, on suppose qu'il n'existe pas

        if debug >= 3:
            print(cyan + "deletePixelsSuperpositionMasks() : " + endC + "Les images masques ont ete nettoyees")
    else :
        if debug >= 3:
            print(cyan + "deletePixelsSuperpositionMasks() : " + bold + yellow + "Pas d'images masques a nettoyer!" + endC)

    return

#########################################################################
# FONCTION createEdgeExtractionImage()                                  #
#########################################################################
#   Rôle : Cette fonction permet de créer un raster issu de la détection de contours
#   Paramètres :
#       image_input : fichier image
#       image_output : fichier image sortie
#       filtre : nom de l'algortihme pour la détection de contours (parmi 'gradient', 'sobel', 'touzi')
#       channel : numéro de la bande à traiter dans l'image (défaut = 1)
#       xradius : si filtre=touzi : nombre de pixels dans le voisinage à prendre en compte (défaut=1)
#       yradius : si filtre=touzi : nombre de pixels dans le voisinage à prendre en compte (défaut=1)

def createEdgeExtractionImage(image_input, image_output, filtre, channel=1, xradius=1, yradius=1):

    if filtre == "touzi":
        command = "otbcli_EdgeExtraction -in %s -channel %s -filter %s -filter.touzi.xradius %s -filter.touzi.yradius %s -out %s" %(image_input, channel, filtre, xradius, yradius, image_output)
    else:
        command = "otbcli_EdgeExtraction -in %s -channel %s -filter %s -out %s" %(image_input, channel, filtre, image_output)

    if debug >=3:
        print(command)

    exit_code = os.system(command)
    if exitCode != 0:
        print(command)
        print(cyan + "createEdgeExtractionImage() : " + endC + bold + red + "!!! Une erreur s'est produite à la création du fichier : " + image_output + ". Voir message d'erreur." + endC, file=sys.stderr)
        sys.exit(1)

    if debug >= 3:
        print(cyan + "createEdgeExtractionImage() : " + endC + bold + green + "La détection de contours a été appliquée au fichier " + image_input  + " Résultat : " + image_output + endC)

    return

#########################################################################
# FONCTION createBinaryMask()                                           #
#########################################################################
#   Rôle : Cette fonction permet de créer un masque binaire par seuillage d'une image raster à une seul bande
#   Paramètres :
#       image_input : fichier image d'entrée une bande
#       image_output : fichier binaire seuillé en sortie
#       threshold : valeur du seuillage
#       positif : codage de l'information 1 sur 0 (positif) si vrai sinon 0 sur 1 (negatif)
#       codage : type de codage du fichier de sortie

def createBinaryMask(image_input, image_output, threshold, positif, codage="uint8"):

    # Création de l'expression
    if positif:
        expression = "\"(im1b1 > %f?1:0)\""%(threshold)
    else :
        expression = "\"(im1b1 > %f?0:1)\""%(threshold)

    # bandmath pour seuiller l'image d'entrée et creer une image binaire
    command = "otbcli_BandMath -il %s -out %s %s -exp %s" %(image_input,image_output,codage,expression)

    if debug >= 3:
        print(command)

    exitCode = os.system(command)
    if exitCode != 0:
        print(command)
        raise NameError(bold + red + "createBinaryMask() : An error occured during otbcli_BandMath command. See error message above." + endC)

    if debug >= 3:
        print(cyan + "createBinaryMask() : " + bold + green + "Create binary file %s complete!" %(image_output) + endC)

    return

#########################################################################
# FONCTION createBinaryMaskThreshold()                                  #
#########################################################################
#   Rôle : Cette fonction permet de créer un masque binaire par seuillage min et max d'une image raster à une seul bande
#   Paramètres :
#       image_input : fichier image d'entrée une bande
#       image_output : fichier binaire seuillé en sortie
#       threshold_min : valeur du seuillage min
#       threshold_max : valeur du seuillage max
#       codage : type de codage du fichier de sortie

def createBinaryMaskThreshold(image_input, image_output, threshold_min, threshold_max, codage="uint8"):

    # Creer l'expression
    expression = "\"(im1b1 >= %f and im1b1 <= %f ?1:0)\""%(threshold_min, threshold_max)

    # bandmath pour seuiller l'image d'entrée est creer une image binaire
    command = "otbcli_BandMath -il %s -out %s %s -exp %s" %(image_input,image_output,codage,expression)

    if debug >= 3:
        print(command)

    exitCode = os.system(command)
    if exitCode != 0:
        print(command)
        raise NameError(bold + red + "createBinaryMaskThreshold() : An error occured during otbcli_BandMath command. See error message above." + endC)

    if debug >= 3:
        print(cyan + "createBinaryMaskThreshold() : " + bold + green + "Create binary file %s complete!" %(image_output) + endC)

    return

#########################################################################
# FONCTION createBinaryMaskMultiBand()                                  #
#########################################################################
#   Rôle : Cette fonction permet de créer un masque binaire d'une image raster à plusieurs bandes les pixels nodata ou à zéro -> 0, sinon -> 1
#   Paramètres :
#       image_input : fichier image d'entrée multi bandes
#       image_output : fichier binaire en sortie
#       no_data_value : valeur du no data à zéro par défaut
#       codage : type de codage du fichier de sortie

def createBinaryMaskMultiBand(image_input, image_output, no_data_value=0, codage="uint8"):

    # Recuperer le nombre de bande du fichier
    cols, rows, nb_bands = getGeometryImage(image_input)

    # Creer l'expression en fonction du nombre de bande
    expression = "\"("
    for id_bande in range(nb_bands):
       expression += "im1b%s != %s && "%(str(id_bande + 1), str(no_data_value))
    expression = expression[0:len(expression)-3]
    expression += "?1:0)\""

    # Bandmath pour creer une image binaire pixels avec valeur different de nodata ou valeurs à zéro
    command = "otbcli_BandMath -il %s -out %s %s -exp %s" %(image_input,image_output,codage,expression)

    if debug >= 3:
        print(command)

    exitCode = os.system(command)
    if exitCode != 0:
        print(command)
        raise NameError(bold + red + "createBinaryMaskMultiBand() : An error occured during otbcli_BandMath command. See error message above." + endC)

    if debug >= 3:
        print(cyan + "createBinaryMaskMultiBand() : " + bold + green + "Create binary file %s complete!" %(image_output) + endC)

    return

#########################################################################
# FONCTION applyMaskAnd()                                               #
#########################################################################
#   Rôle : Cette fonction permet d'appliquer un masque binaire logique "and" à un fichier d'entrée résultat en fichier de sortie
#   Paramètres :
#       image_input : fichier image d'entrée une bande
#       image_mask_input : fichier masque binaire
#       image_output : fichier de sortie masqué
#       codage : type de codage du fichier de sortie

def applyMaskAnd(image_input, image_mask_input, image_output, codage="float") :

    # Creer l'expression
    expression = "\"(im2b1==1?im1b1:0)\""

    # bandmath pour application du masque binaire
    command = "otbcli_BandMath -il %s %s -out %s %s -exp %s" %(image_input,image_mask_input,image_output,codage,expression)

    if debug >= 3:
        print(command)

    exitCode = os.system(command)
    if exitCode != 0:
        print(command)
        raise NameError(bold + red + "applyMaskAnd() : An error occured during otbcli_BandMath command. See error message above." + endC)

    if debug >= 3:
        print(cyan + "applyMaskAnd() : " + bold + green + "Apply mask to file %s with operator 'and' complete!" %(image_output) + endC)

    return

#########################################################################
# FONCTION applyMaskOr()                                                #
#########################################################################
#   Rôle : Cette fonction permet d'appliquer un masque binaire logique "or" à un fichier d'entrée résultat en fichier de sortie
#   Paramètres :
#       image_input : fichier image d'entrée une bande
#       image_mask_input : fichier masque binaire
#       image_output : fichier de sortie masqué
#       codage : type de codage du fichier de sortie

def applyMaskOr(image_input, image_mask_input, image_output, codage="float"):

    # Creer l'expression
    expression = "\"(im2b1==1||im1b1==1?1:0)\""

    # bandmath pour application du masque binaire
    command = "otbcli_BandMath -il %s %s -out %s %s -exp %s" %(image_input,image_mask_input,image_output,codage,expression)

    if debug >= 3:
        print(command)
    exitCode = os.system(command)

    if exitCode != 0:
        print(command)
        raise NameError(bold + red + "applyMaskOr() : An error occured during otbcli_BandMath command. See error message above." + endC)

    if debug >= 3:
        print(cyan + "applyMaskOr() : " + bold + green + "Apply mask to file %s with operator 'or' complete!" %(image_output) + endC)

    return

#########################################################################
# FONCTION createDifferenceFile()                                       #
#########################################################################
#   Rôle : Cette fonction permet de créer un fichier de différence de deux images raster à une seul bande conditionner à un masque
#   Paramètres :
#       image1_input : fichier image1 d'entrée une bande
#       image2_input : fichier image2 d'entrée une bande
#       image_mask_input : fichier masque ou sera fait la différence
#       image_output : fichier de différence
#       image_mns_output : fichier MNS de sortie
#       codage : type de codage du fichier de sortie

def createDifferenceFile(image1_input, image2_input, image_mask_input, image_output, codage="float"):

    # Creer l'expression
    expression = "\"(im3b1==1?sqrt((im1b1 - im2b1) * (im1b1 - im2b1)):0)\""

    # bandmath pour faire la différence de deux fichiers d'entrée contionner par un fichier masque
    command = "otbcli_BandMath -il %s %s %s -out %s %s -exp %s" %(image1_input,image2_input,image_mask_input,image_output,codage,expression)

    if debug >= 3:
        print(command)

    exitCode = os.system(command)
    if exitCode != 0:
        print(command)
        raise NameError(bold + red + "createDifferenceFile() : An error occured during otbcli_BandMath command. See error message above." + endC)

    if debug >= 3:
        print(cyan + "createDifferenceFile() : " + bold + green + "Create difference file %s complete!" %(image_output) + endC)

    return

#########################################################################
# FONCTION filterBinaryRaster()                                         #
#########################################################################
#   Rôle : Cette fonction permet de filtrer une image binaire raster à une seul bande
#   Paramètres :
#       image_input : fichier image binaire d'entrée à filtrer à une bande
#       image_output : fichier de sortie filtré
#       param_filter_0 : parametre de filtrage définie la taille de la fenêtre pour les zones à 0
#       param_filter_1 : parametre de filtrage définie la taille de la fenêtre pour les zones à 1
#       codage : type de codage du fichier de sortie (défaut=uint8)

def filterBinaryRaster(image_input, image_output, param_filter_0, param_filter_1, codage="uint8"):

    # Creer un fichier image temporaire
    name_file = os.path.splitext(image_output)[0]
    extension_file = os.path.splitext(image_output)[1]
    image_filter_input_tmp = name_file + "_tmp" + extension_file
    clean_temp = True

    if param_filter_0 > 0 :
        # otbcli_BinaryMorphologicalOperation pour faire un filtre morphologique de type "ouverture" sur valeur à 0
        command = "otbcli_BinaryMorphologicalOperation -in %s -channel 1 -structype ball -structype.ball.xradius %d -structype.ball.yradius %d -filter opening -filter.opening.foreval 0 -filter.opening.backval 1 -out %s %s" %(image_input,param_filter_0,param_filter_1,image_filter_input_tmp,codage)

        if debug >= 3:
            print(command)

        exitCode = os.system(command)
        if exitCode != 0:
            print(command)
            raise NameError(bold + red + "filterBinaryRaster() : An error occured during otbcli_BinaryMorphologicalOperation command. See error message above." + endC)
    else :
        image_filter_input_tmp = image_input
        clean_temp = False

    if param_filter_1 > 0 :
        # otbcli_BinaryMorphologicalOperation pour faire un filtre morphologique de type "ouverture" sur valeur à 1
        command = "otbcli_BinaryMorphologicalOperation -in %s -channel 1 -structype ball -structype.ball.xradius %d -structype.ball.yradius %d -filter opening -filter.opening.foreval 1 -filter.opening.backval 0 -out %s %s" %(image_filter_input_tmp,param_filter_1,param_filter_1,image_output,codage)

        if debug >= 3:
            print(command)

        exitCode = os.system(command)
        if exitCode != 0:
            print(command)
            raise NameError(bold + red + "filterBinaryRaster() : An error occured during otbcli_BinaryMorphologicalOperation command. See error message above." + endC)
    else :
        shutil.copy(image_filter_input_tmp, image_output)

    # Supprimer le fichier temporaire
    if clean_temp and os.path.isfile(image_filter_input_tmp) :
        os.remove(image_filter_input_tmp)

    if debug >= 1:
        print(cyan + "filterBinaryRaster() : " + bold + green + "Create filter binary file %s complete!" %(image_output) + endC)

    return

#########################################################################
# FONCTION bufferBinaryRaster()                                         #
#########################################################################
#   Rôle : Cette fonction permet de bufferiser/eroder une image binaire raster à une seul bande
#   Paramètres :
#       image_input : fichier image binaire d'entrée à bufferiser à une bande
#       image_output : fichier de sortie buffurisé
#       buffer_to_apply : parametre taille du buffer en pixel (positif => buffer, negatif => erosion)
#       codage : type de codage du fichier de sortie (défaut=uint8)
#       foreground_value: La valeur des pixels à traiter (défaut=1)
#       background_value: La valeur des pixels de fonds no data (défaut=0)

def bufferBinaryRaster(image_input, image_output, buffer_to_apply, codage="uint8", foreground_value=1, background_value=0):

    # Si le buffer est nul, alors on copie juste le masque binaire
    if buffer_to_apply == 0:
        shutil.copy(image_input,image_output)
    else :

        if buffer_to_apply > 0:
            command = "otbcli_BinaryMorphologicalOperation -in %s -channel 1 -structype ball -structype.ball.xradius %d -structype.ball.yradius %d -filter dilate -filter.dilate.foreval %d -filter.dilate.backval %d -out %s %s" %(image_input,abs(buffer_to_apply),abs(buffer_to_apply),foreground_value,background_value,image_output,codage)
        else :
            command = "otbcli_BinaryMorphologicalOperation -in %s -channel 1 -structype ball -structype.ball.xradius %d -structype.ball.yradius %d -filter erode -filter.erode.foreval %d -filter.erode.backval %d -out %s %s" %(image_input,abs(buffer_to_apply),abs(buffer_to_apply),foreground_value,background_value,image_output,codage)

        if debug >= 3:
            print(command)

        exitCode = os.system(command)
        if exitCode != 0:
            print(command)
            raise NameError(bold + red + "bufferBinaryRaster() : An error occured during otbcli_BinaryMorphologicalOperation command. See error message above." + endC)

    if debug >= 3:
        print(cyan + "bufferBinaryRaster() : " + bold + green + "Create buffer binary file %s complete!" %(image_output) + endC)
    return

#########################################################################
# FONCTION createVectorMask()                                           #
#########################################################################
#   Role : Création d'un masque binaire à partir d'une image sat (0 pour les zones non renseignées et 1 pour les zones ayant de l'information)
#          puis vectorisation de celui-ci, pour céer un masque vecteur
#   Paramètres en entrée :
#       input_image : image raw source
#       vector_mask : masque vecteur correspondant à l'image d'entrée
#       format_vector : format du fichier vecteur par defaut = 'ESRI Shapefile'

def createVectorMask(input_image, vector_mask, format_vector='ESRI Shapefile'):

    if debug >=3:
        print(cyan + "createVectorMask() : " + endC + "Creation d'un masque de decoupage avec l'image : " + str(input_image))

    # Indiquer le nom de masque a creer
    extension = os.path.splitext(os.path.basename(input_image))[1]
    raster_mask = os.path.splitext(vector_mask)[0] + extension
    mask_layer = os.path.splitext(os.path.basename(vector_mask))[0]

    # Formule de calcul
    cols, rows, bands = getGeometryImage(input_image)
    if bands < 3:
        expression = "\"im1b1 == 0?0:1\""
    else :
        expression = "\"im1b1+im1b2+im1b3 == 0?0:1\""

    # Creation du masque d'image

    #~ # The following line creates an instance of the BandMath application
    #~ bandMath_app = otbApplication.Registry.CreateApplication("BandMath")
    #~ # The following lines set all the application parameters:
    #~ bandMath_app.SetParameterStringList("il", [input_image])
    #~ bandMath_app.SetParameterString("out", raster_mask)
    #~ bandMath_app.SetParameterOutputImagePixelType("out", otbApplication.ImagePixelType_uint8)
    #~ bandMath_app.SetParameterString("exp", expression)
    #~ # The following line execute the application
    #~ try:
        #~ bandMath_app.ExecuteAndWriteOutput()
    #~ except Exception:
        #~ raise NameError(bold + red + "An error occured during execution otb BandMath command. See error message above." + endC)

    command = "otbcli_BandMath -il %s -out %s %s -exp %s" %(input_image,raster_mask,"uint8",expression)

    if debug >=3:
        print(command)

    exit_code = os.system(command)
    if exit_code != 0:
        print(command)
        raise NameError(bold + red + "An error occured during otbcli_BandMath command. See error message above." + endC)

    # Creer le shape file
    command = "gdal_polygonize.py -mask \"%s\" \"%s\" -f \"%s\" \"%s\" \"%s\" id" %(raster_mask,raster_mask,format_vector,vector_mask,mask_layer)
    if debug >=3:
        print(command)
    exit_code = os.system(command)
    if exit_code != 0:
        raise NameError(bold + red + "An error occured during gdal_polygonize command. See error message above." + endC)

    if debug >=3:
        print(cyan + "createVectorMask() : " + endC + "Masque de découpage crée : " + str(vector_mask))
    return

#########################################################################
# FONCTION h5ToGtiff()                                                  #
#########################################################################
#   Role : Transforme un conteneur de fichiers HDF5 en fichier GTiff
#   Paramètres :
#       hdf5_input : fichier HDF5 d'origine
#       gtiff_output : fichier GTiff resultat

def h5ToGtiff(hdf5_input, gtiff_output):
    if debug >=3:
        print(cyan + "h5ToGtiff() : " + endC + "Le fichier HDF5 à traiter : " + str(hdf5_input))

    # On considère que tous les fichiers HDF5 ont la même structure :
    #     - un groupe de 1er niveau 'S01' existe
    #     - dans ce groupe, il y a un jeu de données 'SBI', qui correspond à l'image

    gtiff_output_temp = os.path.splitext(gtiff_output)[0] + "_temp" + os.path.splitext(gtiff_output)[1]
    command = "gdal_translate HDF5:'%s'://S01/SBI %s" % (hdf5_input, gtiff_output_temp)
    if debug >=3:
        print(command)
    exit_code = os.system(command)
    if exit_code != 0:
        print(command)
        raise NameError(cyan + "h5ToGtiff() : " + bold + red + "An error occured during gdal_translate command. See error message above." + endC)

    gtiff_output_temp_xml = gtiff_output_temp + ".aux.xml"
    if os.path.exists(gtiff_output_temp_xml):
        xmldoc = parseDom(gtiff_output_temp_xml)
        node_data_list = getListNodeDataDom(xmldoc, 'Metadata', 'MDI', element_path='PAMDataset/PAMRasterBand')
        value_attribute_list = getListValueAttributeDom(xmldoc, 'Metadata', 'MDI', 'key', element_path='PAMDataset/PAMRasterBand')

        for value_attribute in value_attribute_list:
            index = value_attribute_list.index(value_attribute)
            node_data = node_data_list[index]
            if value_attribute == "S01_SBI_Bottom_Left_Geodetic_Coordinates":
                x_B_L = node_data.split(' ')[1]
                y_B_L = node_data.split(' ')[0]
            elif value_attribute == "S01_SBI_Bottom_Right_Geodetic_Coordinates":
                x_B_R = node_data.split(' ')[1]
                y_B_R = node_data.split(' ')[0]
            elif value_attribute == "S01_SBI_Top_Left_Geodetic_Coordinates":
                x_T_L = node_data.split(' ')[1]
                y_T_L = node_data.split(' ')[0]
            elif value_attribute == "S01_SBI_Top_Right_Geodetic_Coordinates":
                x_T_R = node_data.split(' ')[1]
                y_T_R = node_data.split(' ')[0]

        xmin = min(x_T_L, x_T_R, x_B_R, x_B_L)
        ymin = min(y_T_L, y_T_R, y_B_R, y_B_L)
        xmax = max(x_T_L, x_T_R, x_B_R, x_B_L)
        ymax = max(y_T_L, y_T_R, y_B_R, y_B_L)
        coordinates = xmin + " " + ymin + " " + xmax + " " + ymax

        command = "gdalwarp -te %s %s %s -overwrite" % (coordinates, gtiff_output_temp, gtiff_output)
        if debug >=3:
            print(command)
        exit_code = os.system(command)
        if exit_code != 0:
            print(command)
            raise NameError(cyan + "h5ToGtiff() : " + bold + red + "An error occured during gdalwarp command. See error message above." + endC)

        removeFile(gtiff_output_temp)
        removeFile(gtiff_output_temp_xml)
        removeFile(gtiff_output + ".aux.xml")

    else:
        renameFile(gtiff_output_temp, gtiff_output)

    if debug >=3:
        print(cyan + "h5ToGtiff() : " + endC + "Le fichier GTiff resultat : " +  str(gtiff_output))
    return

#########################################################################
# FONCTION polygonizeRaster()                                           #
#########################################################################
# Lien vers la documentation GDAL : http://www.gdal.org/gdal_polygonize.html
#
#   Rôle : Cette fonction permet de polygoniser un fichier raster
#   Paramètres :
#       raster_file_input : Nom du fichier raster d'entrée à polygoniser (servannt aussi de masque masque)
#       vector_file_output : Nom du fichier vecteur de sortie
#       layer_name : nom de la couche de sortie vecteur
#       field_name : nom du champs de sortie vecteur
#       vector_export_format : Format ogr de sortie du vecteur. Exemple : vector_export_format="ESRI Shapefile"

def polygonizeRaster(raster_file_input, vector_file_output, layer_name, field_name="id", vector_export_format="ESRI Shapefile"):

    if debug >= 3:
        print(bold + green + '\n' + "Polygonizing " + raster_file_input + "..." + "\n" + endC)

    # Commande gdal polygonize
    command = "gdal_polygonize.py -mask %s %s -f \"%s\" %s %s %s" %(raster_file_input, raster_file_input, vector_export_format, vector_file_output, layer_name, field_name)

    if debug >= 3:
        print(command)

    exitCode = os.system(command)
    if exitCode != 0:
        print(command)
        raise NameError(bold + red + "An error occured during gdal_polygonize command. See error message above." + endC)

    if debug >= 3:
        print(bold + green + '\n' + "polygonizeRaster() : Polygonization of %s complete!" %(vector_file_output) + endC)

    return

#########################################################################
# FONCTION rasterizeBinaryVector()                                      #
#########################################################################
#   Role : Rasterise un fichier shape resultat du fichier raster binaire
#   Paramètres :
#       vector_input : fichier shape d'origine
#       image_ref : image de référence (projection reference system information)
#       raster_output : fichier raster resultat
#       label : valeur pour la zone non a zero (labelisation)
#       codage : type de codage du fichier de sortie

def rasterizeBinaryVector(vector_input, image_ref, raster_output, label=1, codage="uint8"):
    if debug >=3:
        print(cyan + "rasterizeBinaryVector() : " + endC + "Le fichier vecteur à rasteriser : " + str(vector_input))

    #~ # The following line creates an instance of the Rasterization application
    #~ rasterization_app = otbApplication.Registry.CreateApplication("Rasterization")
    #~ # The following lines set all the application parameters:
    #~ rasterization_app.SetParameterString("in", vector_input)
    #~ rasterization_app.SetParameterString("out", raster_output)
    #~ rasterization_app.SetParameterOutputImagePixelType("out", otbApplication.ImagePixelType_uint8)
    #~ rasterization_app.SetParameterString("im", image_ref)
    #~ rasterization_app.SetParameterFloat("background", 0.)
    #~ rasterization_app.SetParameterString("mode", "binary")
    #~ rasterization_app.SetParameterFloat("mode.binary.foreground", label)
    #~ # The following line execute the application
    #~ try:
        #~ rasterization_app.ExecuteAndWriteOutput()
    #~ except Exception:
        #~ raise NameError(cyan + "rasterizeBinaryVector() : " + bold + red + "An error occured during execution otb Rasterization command. See error message above." + endC)

    command = "otbcli_Rasterization -in %s -out %s %s -im %s -background 0 -mode binary -mode.binary.foreground %s" %(vector_input,raster_output,codage,image_ref,str(label))

    if debug >=3:
        print(command)

    exit_code = os.system(command)
    if exit_code != 0:
        print(command)
        raise NameError(cyan + "rasterizeBinaryVector() : " + bold + red + "An error occured during otbcli_Rasterization command. See error message above." + endC)

    if debug >=3:
        print(cyan + "rasterizeBinaryVector() : " + endC + "Le fichier raster resultat : " +  str(raster_output))
    return

#########################################################################
# FONCTION rasterizeVector()                                            #
#########################################################################
#   Role : Rasterise un fichier shape resultat du fichier raster contenant un champ de valeurs
#   Paramètres :
#       vector_input : fichier shape d'origine
#       raster_output : fichier raster resultat
#       image_ref : image de référence (projection reference system information)
#       field : champ du fichier shape qui definira la valeur pour le raster

def rasterizeVector(vector_input, raster_output, image_ref, field):
    if debug >=3:
        print(cyan + "rasterizeVector() : " + endC + "Le fichier vecteur à rasteriser : " + str(vector_input))

    #~ # The following line creates an instance of the Rasterization application
    #~ rasterization_app = otbApplication.Registry.CreateApplication("Rasterization")
    #~ # The following lines set all the application parameters:
    #~ rasterization_app.SetParameterString("in", vector_input)
    #~ rasterization_app.SetParameterString("out", raster_output)
    #~ rasterization_app.SetParameterOutputImagePixelType("out", otbApplication.ImagePixelType_uint16)
    #~ rasterization_app.SetParameterString("im", image_ref)
    #~ rasterization_app.SetParameterFloat("background", 0.)
    #~ rasterization_app.SetParameterString("mode", "attribute")
    #~ rasterization_app.SetParameterFloat("mode.attribute.field", field)
    #~ # The following line execute the application
    #~ try:
        #~ rasterization_app.ExecuteAndWriteOutput()
    #~ except Exception:
        #~ raise NameError(cyan + "rasterizeVector() : " + bold + red + "An error occured during execution otb Rasterization command. See error message above." + endC)

    command = "otbcli_Rasterization -in %s -out %s -im %s -background 0 -mode attribute -mode.attribute.field %s" %(vector_input,raster_output,image_ref,field)

    if debug >=3:
        print(command)

    exit_code = os.system(command)
    if exit_code != 0:
        print(command)
        raise NameError(cyan + "rasterizeVector() : " + bold + red + "An error occured during otbcli_Rasterization command. See error message above." + endC)

    if debug >=3:
        print(cyan + "rasterizeVector() : " + endC + "Le fichier raster resultat : " +  str(raster_output))
    return

#########################################################################
# FONCTION rasterizeBinaryVectorWithoutReference()                      #
#########################################################################
#   Rôle : Rastérise un vecteur en raster binaire, sans image de référence (on renseigne manuellement l'emprise et la résolution)
#   Paramètres :
#       vector_input : fichier shape d'origine
#       raster_output : fichier raster resultat
#       xmin : valeur Xmin de l'emprise (ouest)
#       ymin : valeur Ymin de l'emprise (sud)
#       xmax : valeur Xmax de l'emprise (est)
#       ymax : valeur Ymax de l'emprise (nord)
#       pixel_width : résolution en X
#       pixel_height : résolution en Y
#       burn_value : valeur à appliquer sur le raster de sortie (défaut : 1)
#       nodata_value : valeur NoData du raster de sortie (défaut : 0)
#       format_raster : format du raster de sortie (défault : 'GTiff')
#       codage : codage du raster de sortie (défault : 'Byte')

def rasterizeBinaryVectorWithoutReference(vector_input, raster_output, xmin, ymin, xmax, ymax, pixel_width, pixel_height, burn_value=1, nodata_value=0, format_raster="GTiff", codage="Byte"):
    if debug >= 3:
        print(cyan + "rasterizeBinaryVectorWithoutReference() : " + endC + "Le fichier vecteur à rastériser : " + str(vector_input))

    command = "gdal_rasterize -burn %s -of %s -a_nodata %s -init 0 -te %s %s %s %s -tr %s %s -ot %s %s %s" % (burn_value, format_raster, nodata_value, xmin, ymin, xmax, ymax, pixel_width, pixel_height, codage, vector_input, raster_output)

    if debug >= 3:
        print(command)

    exit_code = os.system(command)
    if exit_code != 0:
        print(command)
        raise NameError(cyan + "rasterizeBinaryVectorWithoutReference() : " + bold + red + "An error occured during gdal_rasterize command. See error message above." + endC)

    if debug >= 3:
        print(cyan + "rasterizeBinaryVectorWithoutReference() : " + endC + "Le fichier raster résultat : " +  str(raster_output))
    return

#########################################################################
# FONCTION rasterCalculator()                                           #
#########################################################################
#   Rôle : Calculatrice raster OTB BandMath
#   Paramètres :
#       raster_input_list : liste de fichiers raster en entrée
#       raster_output : fichier raster en sortie
#       expression : calcul à réaliser
#       codage : type de codage du raster de sortie (défaut : 'float') [uint8/uint16/int16/uint32/int32/float/double/cint16/cint32/cfloat/cdouble]
#   Remarques :
#       - attention à l'ordre des rasters dans la liste en entrée, et leur appel dans l'expression (imXbY)
#       - tous les rasters en entrée doivent être parfaitement superposable (même emprise et même résolution spatiale)

def rasterCalculator(raster_input_list, raster_output, expression, codage='float'):

    # Gestion de la liste des raster en entrée
    raster_input_list_str = ""
    for raster_input in raster_input_list:
        raster_input_list_str += raster_input + ' '

    command = "otbcli_BandMath -il %s -out %s %s -exp '%s'" %(raster_input_list_str[:-1], raster_output, codage, expression)

    if debug >= 3:
        print(command)

    exitCode = os.system(command)
    if exitCode != 0:
        print(command)
        raise NameError(bold + red + "rasterCalculator() : An error occured during otbcli_BandMath command. See error message above." + endC)

    return

