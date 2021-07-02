#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerSO/DALETT/SCGSI  All rights reserved.                                                                            #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT DE COMPRESSION D'IMAGES                                                                                                            #
#                                                                                                                                           #
#############################################################################################################################################
'''
Nom de l'objet : ImageCompression.py
Description :
    Objectif : Compresse des image raster (.tif) codé en 16bits en codage 8bits
    Rq : utilisation des OTB Applications :  otbcli_BandMath, otbcli_ConcatenateImages

Date de creation : 01/10/2014
'''

from __future__ import print_function
import os, sys, glob, argparse, time, shutil, gdal, platform
from gdalconst import *
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_operator import switch, case
from Lib_log import timeLine
from Lib_file import removeFile, renameFile
from Lib_raster import getGeometryImage

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 3

###########################################################################################################################################
# FONCTION convertImage()                                                                                                                 #
###########################################################################################################################################
# ROLE :
# Conversion d'une image en 8bits et/ou compression
#
# ENTREES DE LA FONCTION :
#    image_input : nom de l'image .tif a traiter
#    image_output_8bits : nom de l'image 8 bits
#    image_output_compress : non de l'image de sortie compressée
#    need_8bits : booleen si vrai, l'image d'entrée sera convertie en 8 bits
#    need_compress : booleen si vrai, l'image d'entrée sera compressée ou l'image 8bits si la converion 8bits est demandée
#    compress_type : Type d algorithme disponibles de compression. Choix entre DEFLATE, LZW ou...
#    predictor : réglage du predicteur pour compression LZW ou DEFLATE
#    zlevel : reglage du taux de compression pour la compression DEFLATE
#    suppr_min : Pourcentage des valeurs qui seront tronquees pour les valeurs minimales
#    suppr_max : Pourcentage des valeurs qui seront tronquees pour les valeurs minimales
#    need_optimize8b: booleen si vrai, le passage en 8bits sera optimisé centrer sur l'histograme
#    need_rvb : booleen si vrai, la sortie sera en RVB, sinon, la sortie aura le meme nombre de bandes que l'image initiale
#    need_irc : booleen si vrai, la sortie sera en IRC, sinon, la sortie aura le meme nombre de bandes que l'image initiale (RVB prioritaire sur IRC, si les 2 sont True)
#    path_time_log : le fichier de log de sortie
#    channel_order : identifiant des canaux de l'image, exemple : {"Red":1,"Green":2,"Blue":3,"RE":4,"NIR":5}, defaut=[Red,Green,Blue,NIR]
#    format_raster : Format de l'image de sortie, par défaut : GTiff
#    extension_raster : extension des fichiers raster de sortie, par defaut = '.tif'
#    save_results_intermediate : sauvegarde ou suppression des images résultats, par defaut à False
#    overwrite : boolen si vrai, ecrase les fichiers existants
# SORTIES DE LA FONCTION :
#    Image convertie
#
def convertImage(image_input, image_output_8bits, image_output_compress, need_8bits, need_compress, compress_type, predictor, zlevel, suppr_min, suppr_max, need_optimize8b, need_rvb, need_irc, path_time_log, channel_order=['Red','Green','Blue','NIR'], format_raster='GTiff', extension_raster=".tif", save_results_intermediate=False, overwrite=True):

    # Mise à jour du Log
    starting_event = "convertImage() : conversion image starting : "
    timeLine(path_time_log,starting_event)

    # Affichage des parametres
    if debug >= 3:
        print(cyan + "convertImage() : " + endC + "image_input: ",image_input)
        print(cyan + "convertImage() : " + endC + "image_output_8bits: ",image_output_8bits)
        print(cyan + "convertImage() : " + endC + "image_output_compress: ",image_output_compress)
        print(cyan + "convertImage() : " + endC + "need_8bits: ",need_8bits)
        print(cyan + "convertImage() : " + endC + "need_compress: ",need_compress)
        print(cyan + "convertImage() : " + endC + "compress_type: ",compress_type)
        print(cyan + "convertImage() : " + endC + "predictor: ",predictor)
        print(cyan + "convertImage() : " + endC + "zlevel: ",zlevel)
        print(cyan + "convertImage() : " + endC + "suppr_min: ",suppr_min)
        print(cyan + "convertImage() : " + endC + "suppr_max: ",suppr_max)
        print(cyan + "convertImage() : " + endC + "need_rvb: ",need_rvb)
        print(cyan + "convertImage() : " + endC + "need_irc: ",need_irc)
        print(cyan + "convertImage() : " + endC + "path_time_log: ",path_time_log)
        print(cyan + "convertImage() : " + endC + "channel_order : " + str(channel_order) + endC)
        print(cyan + "convertImage() : " + endC + "format_raster : " + str(format_raster) + endC)
        print(cyan + "convertImage() : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "convertImage() : " + endC + "save_results_intermediate: ",save_results_intermediate)
        print(cyan + "convertImage() : " + endC + "overwrite: ",overwrite)

    # Constantes
    FOLDER_TEMP = 'Tmp_'

    # Definition des dossiers de travail
    image_name = os.path.splitext(os.path.basename(image_input))[0]

    # Definir le nombre de bande de l'image d'entrée
    cols, rows, bands = getGeometryImage(image_input)
    inputBand4Found = False
    if bands >= 4 and not need_rvb and not need_irc:
        inputBand4Found = True

    if not need_compress:
        image_output_compress = image_output_8bits

    repertory_tmp = os.path.dirname(image_output_compress) + os.sep + FOLDER_TEMP + image_name # repertory_tmp : Dossier dans lequel on va placer les images temporaires
    if not os.path.isdir(repertory_tmp):
        os.makedirs(repertory_tmp)

    print(cyan + "ImageCompression : " + endC + "Dossier de travail temporaire: ",repertory_tmp)

    # Impression des informations d'execution
    print(endC)
    print(bold + green + "# DEBUT DE LA CONVERSION DE L'IMAGE %s" %(image_input) + endC)
    print(endC)

    if debug >= 1:
        print(cyan + "convertImage() : " + endC + "%s pourcents des petites valeurs initiales et %s pourcents des grandes valeurs initiales seront supprimees" %(suppr_min,suppr_max))

    # VERIFICATION SI L'IMAGE DE SORTIE EXISTE DEJA
    check = os.path.isfile(image_output_compress)

    # Si oui et si la vérification est activée, passe à l'étape suivante
    if check and not overwrite :
        print(cyan + "convertImage() : " + bold + yellow + "Image have already been converted." + endC)
    else:
        # Tente de supprimer le fichier
        try:
            removeFile(image_output_compress)
        except Exception:
            # Ignore l'exception levée si le fichier n'existe pas (et ne peut donc pas être supprimé)
            pass

        ###########################################################
        #   Conversion du fichier en 8bits                        #
        ###########################################################
        if need_8bits:
            convertion8Bits(image_input, image_output_8bits, repertory_tmp, inputBand4Found, need_optimize8b, need_rvb, need_irc, channel_order, suppr_min, suppr_max, format_raster, extension_raster, save_results_intermediate)
            image_to_compress = image_output_8bits
        else :
            image_to_compress = image_input

        ###########################################################
        #   Compression du fichier                                #
        ###########################################################
        if need_compress:
            compressImage(image_to_compress, image_output_compress, inputBand4Found, compress_type, predictor, zlevel, format_raster)

    ###########################################################
    #   nettoyage du repertoire temporaire                    #
    ###########################################################
    if not save_results_intermediate:
        shutil.rmtree(repertory_tmp)
        if debug >= 1:
            print(bold + green + "Suppression du dossier temporaire : " + repertory_tmp + endC)

    if debug >= 1:
        print(cyan + "convertImage() : " + endC + "Fin de la conversion de %s" %(image_input))

    print(endC)
    if need_compress:
        print(bold + green + "# FIN DE LA CONVERSION DE L'IMAGE %s" %(image_input) + endC)
    print(endC)

    # Mise à jour du Log
    ending_event = "convertImage() : conversion image ending : "
    timeLine(path_time_log,ending_event)
    return

###########################################################################################################################################
# FONCTION convertion8Bits()                                                                                                              #
###########################################################################################################################################
# ROLE :
# Conversion d'une image 16 bits en 8 bits
#
# ENTREES DE LA FONCTION :
#    image_input : nom de l'image .tif a traiter
#    image_output_compress : non de l'image de sortie compressée
#    image_output_8bits : nom de l'image 8 bits
#    repertory_tmp : repertoire temporaire de travail
#    inputBand4Found : il existe une band 4 qui ne doit pas etre la transparence
#    need_optimize8b: booleen si vrai, le passage en 8bits sera optimiser centrer sur l'histograme
#    need_rvb : booleen si vrai, la sortie sera en RVB, sinon, la sortie aura le meme nombre de bandes que l'image initiale
#    need_irc : booleen si vrai, la sortie sera en IRC, sinon, la sortie aura le meme nombre de bandes que l'image initiale
#    channel_order : identifiant des canaux de l'image
#    suppr_min : Pourcentage des valeurs qui seront tronquees pour les valeurs minimales
#    suppr_max : Pourcentage des valeurs qui seront tronquees pour les valeurs minimales
#    format_raster : format de l'image de sortie
#    extension_raster : extension des fichiers raster de sortie, par defaut = '.tif'
#    save_results_intermediate : sauvegarde ou suppression des images résultats, par defaut à False
# SORTIES DE LA FONCTION :
#    Image 8bits
#
def convertion8Bits(image_input, image_output_8bits, repertory_tmp, inputBand4Found, need_optimize8b, need_rvb, need_irc, channel_order, suppr_min, suppr_max, format_raster, extension_raster=".tif", save_results_intermediate=False):

    # Constantes diverses
    NBR_COL_HISTO = 256
    CODAGE = "uint8"

    ###############################################################
    # Echantillonage en 8 bits de toutes les bandes de l'image    #
    ###############################################################

    print(bold + green + "DEBUT DU REECHANTILLONAGE 8 BITS DE %s" %(image_input) + endC)
    if debug >= 2:
        print(cyan + "convertion8Bits() : " + endC + bold + green + "Informations sur l image " + endC)

    # Chargement de l'image en dataset
    dataset = gdal.Open(image_input, GA_ReadOnly)
    nbr_bandes_entree = dataset.RasterCount

    # Calcul du nombre de bandes dans l'image
    nbr_bandes = nbr_bandes_entree
    if need_rvb or need_irc:
        nbr_bandes = 3

    if debug >= 2:
        print(cyan + "convertion8Bits() : " + endC + "nbr_bandes en entree = " + str(nbr_bandes_entree))
        print(cyan + "convertion8Bits() : " + endC + "nbr_bandes en sortie = " + str(nbr_bandes))

    # Gestion des numéros de bandes (fonction sortie classique, RVB, IRC)
    if need_rvb:
        num_bands = [channel_order.index("Red")+1, channel_order.index("Green")+1, channel_order.index("Blue")+1]
    elif need_irc:
        num_bands = [channel_order.index("NIR")+1, channel_order.index("Red")+1, channel_order.index("Green")+1]
    else:
        num_bands = [num_band for num_band in range(1,nbr_bandes+1)]

    ###########################################################
    # Compression en 8 bits pour chaque bandes                #
    ###########################################################
    if debug >= 1:
        print(cyan + "convertion8Bits() : " + endC + "Debut du passage en 8 bits bandes par bandes de %s" %(image_input))


    ###########################################################
    # Chaque bande est compréssée en 8 bits                   #
    ###########################################################

    for bande in num_bands:

        ###########################################################
        # Si l'optimisation par calcul d'histograme est demandée  #
        # les extrémités de l'histogramme sont supprimées         #
        # avant d'être rééchantilonné en bits                     #
        ###########################################################
        if need_optimize8b:

            # Chargement des données de la bandes
            band = dataset.GetRasterBand(bande)

            # Calcul des valeurs minimales et maximales de la bande
            a=band.ComputeRasterMinMax()
            min_Bande=a[0]
            max_Bande=a[1]

            # Extraction de l'histogramme de la bande
            b=band.GetHistogram(min=a[0],max=a[1],buckets=NBR_COL_HISTO,approx_ok=0)

            if debug >= 2:
                print(cyan + "convertion8Bits() : " + endC + "Statistiques de la bande " + str(bande) + " : " + str(a))
                print(cyan + "convertion8Bits() : " + endC + "[min , max] de la bande " + str(bande) + " : [" + str(min_Bande) + " , " + str(max_Bande) + "]")
                print(cyan + "convertion8Bits() : " + endC + "Histogramme de la bande " + str(bande))

            # Calcul du nombre total de pixels et de l'histogramme cumulé
            cum_hist=[]
            total = 0
            for bucket in b:
                cum_hist.append(total + bucket)
                total = total + bucket

            if debug >= 2:
                print(cyan + "convertion8Bits() : " + endC + "Histogramme cumule de la bande " + str(bande))
                print(cum_hist)

            # Determination des numeros de colonne dans l'histogramme (entre 0 et 255) du min,max de la bande
            index_val_min = 0
            index_val_max = NBR_COL_HISTO

            for j in range(0,256):
                if cum_hist[j-1]<=0 and cum_hist[j]>0 :
                    index_val_min=max(0,j-1)
                elif cum_hist[j-1]<total and cum_hist[j]>=total :
                    index_val_max=min(j,NBR_COL_HISTO)
                    break

            if debug >= 2:
                print(cyan + "convertion8Bits() : " + endC + "Numero de colonne de l histogramme de la valeur minimale = " + str(index_val_min) + endC)
                print(cyan + "convertion8Bits() : " + endC + "Numero de colonne de l histogramme de la valeur maximale = " + str(index_val_max) + endC)

            # On ne garde que les valeurs comprises entre suppr_min % et suppr_max %
            val_cum_min_garde = total*float(suppr_min)/100
            val_cum_max_garde = total*(1-float(suppr_max)/100)

            if debug >= 2:
                print(cyan + "convertion8Bits() : " + endC + "Valeur cumulee minimale gardee : "+ str(val_cum_min_garde) + endC)
                print(cyan + "convertion8Bits() : " + endC + "Valeur cumulee maximale gardee : "+ str(val_cum_max_garde) + endC)

            # Determination des numeros de colonne dans l'histogramme (entre 0 et 255) du min,max que l'on va garder après suppression des valeurs en bordure
            index_val_min_garde = 0
            index_val_max_garde = NBR_COL_HISTO

            for j in range(0,256):
                if cum_hist[j-1]<=val_cum_min_garde and cum_hist[j]>val_cum_min_garde :
                    index_val_min_garde=max(0,j-1)
                elif cum_hist[j-1]<val_cum_max_garde and cum_hist[j]>=val_cum_max_garde :
                    index_val_max_garde=min(j,NBR_COL_HISTO)
                    break

            if debug >= 2:
                print(cyan + "convertion8Bits() : " + endC + "Numero de colonne de l histogramme de la valeur minimale gardee = "+ str(index_val_min_garde) + endC)
                print(cyan + "convertion8Bits() : " + endC + "Numero de colonne de l histogramme de la valeur maximale gardee = "+ str(index_val_max_garde) + endC)

            # Calcul des valeurs extremes des pixels gardes apres tronquage
            val_min_garde = index_val_min_garde*a[1]/index_val_max
            val_max_garde = index_val_max_garde*a[1]/index_val_max

            if debug >= 2:
                print(cyan + "convertion8Bits() : " + endC + "Valeur minimale des pixels gardes = "+ str(val_min_garde) + endC)
                print(cyan + "convertion8Bits() : " + endC + "Valeur maximale des pixels gardes = "+ str(val_max_garde) + endC)

            # Expression
            expression = "\"(im1b" + str(bande)+"<"+str(val_min_garde)+")?1:(im1b" + str(bande)+">"+str(val_max_garde)+")?255:(im1b" + str(bande) + "-" + str( val_min_garde) +")*255/(" + str(val_max_garde) + "-" + str( val_min_garde) +")\""


        ###########################################################
        # Pas l'optimisation demandée                             #
        # Tout l'histogramme est rééchantilonné en bits           #
        ###########################################################
        else :
            # Expression
            expression = "\"(im1b" + str(bande) + "/16)\""

        # Passage en 8 bits : redistribution des valeurs entre 0 et 255
        if debug >= 1:
            print(cyan + "convertion8Bits() : " + endC + bold + green + "Codage en 8 bits de la bande : " + str(bande) + endC)

        image_output = repertory_tmp + os.sep + os.path.splitext(os.path.basename(image_input))[0] + "_band_" + str(bande) + extension_raster

        if debug >= 2:
            print("Expression : " + str(expression))
            print("image_input : " + image_input)
            print("image_output : " + image_output)

        if os.path.isfile(image_output):
            print("le fichier " + image_output + " est deja traite")
        else :
            exitCode = os.system("otbcli_BandMath -il %s -out %s %s -exp %s" %(image_input, image_output, CODAGE, expression))
            if exitCode != 0:
                raise NameError(bold + red + "convertion8Bits() : An error occured during otbcli_BandMath command. See error message above." + endC)
        # end for bande

    if debug >= 1:
        print(cyan + "convertion8Bits() : " + endC + "Debut du passage en 8 bits bandes par bandes de %s" %(image_input))

    ###########################################################
    # Concatenation des bandes                                #
    ###########################################################

    if debug >= 1:
        print(cyan + "convertion8Bits() : " + endC + "Debut de la concatenation des bandes en 8 bits de %s" %(image_input))

    # Creation de la liste des n bandes a concatener
    bands_to_concatenate_list = []
    bands_to_concatenate_list_str = ''
    for bande in num_bands:
        band_name = repertory_tmp + os.sep +  os.path.splitext(os.path.basename(image_input))[0] + "_band_" + str(bande) + extension_raster
        bands_to_concatenate_list.append(band_name)
        bands_to_concatenate_list_str += band_name + " "

    if os.path.isfile(image_output_8bits):
        print(bold + yellow + "ATTENTION : un fichier concatene existe deja dans " + image_output_8bits + endC)
        print(bold + yellow + "L'image en 8 bits n est pas mise a jour " + endC)
    else :
        print( bold + green + "Concatenation des bandes codees en 8 bits : " + image_output_8bits + endC)
        huit_bits_image_tmp = repertory_tmp + os.sep +  os.path.splitext(os.path.basename(image_input))[0] + "_tmp" + extension_raster
        comand = "otbcli_ConcatenateImages -il %s -out %s %s " %(bands_to_concatenate_list_str, huit_bits_image_tmp, CODAGE)
        exitCode = os.system(comand)
        if exitCode != 0:
            print(comand)
            raise NameError(bold + red + "convertion8Bits() : An error occured during otbcli_ConcatenateImages command. See error message above." + endC)

        ###########################################################
        # La bande 4 ne doit pas etre la transparence             #
        ###########################################################
        if inputBand4Found :
            command = "gdal_translate -of %s -colorinterp_4 undefined %s %s" %(format_raster, huit_bits_image_tmp, image_output_8bits)
            exitCode = os.system(command)
            if exitCode != 0:
                print(command)
                raise NameError(bold + red + "convertion8Bits() : An error occured during gdal_translate command. See error message above." + endC)

            if not save_results_intermediate :
                removeFile(huit_bits_image_tmp)
        else :
            renameFile(huit_bits_image_tmp, image_output_8bits)

    if debug >= 1:
        print(cyan + "convertion8Bits() : " + endC + "Fin de la concatenation des bandes en 8 bits de %s" %(image_input) + endC)

    print(bold + green + "FIN DU CODAGE EN 8 BITS DE " + image_input + endC)

    return

###########################################################################################################################################
# FONCTION compressImage()                                                                                                                #
###########################################################################################################################################
# ROLE :
# Compression d'une image Tiff
#
# ENTREES DE LA FONCTION :
#    image_input : nom de l'image .tif a traiter
#    image_output_compress : non de l'image de sortie compressée
#    inputBand4Found : il existe une band 4 qui ne doit pas etre la transparence
#    compress_type : Type d algorithme disponibles de compression. Choix entre DEFLATE, LZW ou...
#    predictor : réglage du predicteur pour compression LZW ou DEFLATEgdal_translate
#    zlevel : reglage du taux de compression pour la compression DEFLATE
#    format_raster : format de l'image compressée
# SORTIES DE LA FONCTION :
#    Image compressé
#
def compressImage(image_input, image_output_compress, inputBand4Found, compress_type, predictor, zlevel, format_raster):

    if debug >= 1:
        print(cyan + "compressImage() : " + endC + "Debut de la compression de %s" %(image_input))

    # Preparation de la commande
    command = ""
    caseBand4 = ""
    if inputBand4Found :
        caseBand4 = "-colorinterp_4 undefined"
    # Selon le type de compression
    while switch(compress_type.upper()):
        if case("DEFLATE"):
            if debug >= 2:
                print("Compression DEFLATE : ")
            command = "gdal_translate -of %s %s -co TILED=YES -co COMPRESS=%s -co PREDICTOR=%s -co ZLEVEL=%s %s %s" %(format_raster, caseBand4, compress_type, predictor, zlevel, image_input, image_output_compress)
            break
        if case("LZW"):
            if debug >= 2:
                print("Compression LZW : ")
            command = "gdal_translate -of %s %s -co TILED=YES -co COMPRESS=%s -co ZLEVEL=%s %s %s" %(format_raster, caseBand4, compress_type, zlevel, image_input, image_output_compress)
            break
        break
    if command =="":
        raise NameError (bold + red + "compressImage() : Le type de compression n'est pas reconu : "  + str(compress_type + endC))

    if debug >= 1:
        print(cyan + "compressImage() : " + endC + "Algorithme de compressions : " + str(compress_type) + endC)
        print(cyan + "compressImage() : " + endC + "Predicteur : " + str(predictor) + endC)
        if compress_type == "DEFLATE" :
            print(cyan + "compressImage() : " + endC + "Taux de compression : " + str(zlevel) + endC)
        print(cyan + "compressImage() : " + endC + "Fichier de sortie : " + image_output_compress + endC)

    exitCode = os.system(command)
    if exitCode != 0:
        print(command)
        raise NameError(bold + red + "compressImage() : An error occured during gdal_translate command. See error message above." + endC)

    print(bold + green + "FIN DE LA COMPRESSION DE " + image_input + endC)

    return
###########################################################################################################################################
# MISE EN PLACE DU PARSER                                                                                                                 #
###########################################################################################################################################

# Code executé seulement dans le cas ou le script est lancé depuis une ligne de commande
# Il n'est pas executé lors d'un import ImageCompression.py
# Exemple de lancement en ligne de commande:
# python ImageCompression.py -i ../ImagesTestChaine/APTV_05/APTV_05.tif -ocp ../ImagesTestChaine/APTV_05/Compression/APTV_05_8Bits_compressed.tif -o8b ../ImagesTestChaine/APTV_05/Compression/APTV_05_8Bits.tif -cp DEFLATE -pr 2 -zl 3 -mn 0 -mx 0.1 -rvb -dt -log ../ImagesTestChaine/APTV_05/fichierTestLog.txt

def main(gui=False):

    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, prog="ImageCompression", description=" \
    Info : Encoding image in GeoTIFF format 16bits into 8 bits and compression algorithms DEFLATE or LZW, allows to reduce the size of an image jusqua 10% of its original size. \n\
    DEFLATE algorithm, lossy compression. \n\
    LZW algorithm, lossless compression. \n\
    Detailed documentation of the parameters of GeoTiff here:  http://www.gdal.org/frmt_gtiff.html. \n\
    Objectif : Compresse des image raster (.tif) code en 16bits en codage 8bits. \n\
    Example : python ImageCompression.py -i ../ImagesTestChaine/APTV_05/APTV_05.tif \n\
                                         -o8b ../ImagesTestChaine/APTV_05/Compression/APTV_05_8Bits.tif \n\
                                         -ocp ../ImagesTestChaine/APTV_05/Compression/APTV_05_8Bits_compressed.tif \n\
                                         -cp DEFLATE -pr 2 -zl 3 -mn 0 -mx 0.1 -rvb -dt \n\
                                         -log ../ImagesTestChaine/APTV_05/fichierTestLog.txt")

    parser.add_argument('-i','--image_input',default="",help="Images to treat.", type=str, required=True)
    parser.add_argument('-o8b','--image_output_8bits',default="",help="Image output of 8bits file need", type=str, required=False)
    parser.add_argument('-ocp','--image_output_compress',default="",help="Image output of compression file need, if image output of 8bits need, it is the 8bits image compresed", type=str, required=False)
    parser.add_argument('-cp','--compress', default="", help="By default no compression is done. If you enter the algorithm, you trigger the compression process. Type of compression algorithm. Chose between DEFLATE or LZW.", type=str, required=False)
    parser.add_argument('-pr','--predictor', default=2,help="Adjustment of the compression predictor LZW or DEFLATE. By default : 2 ", type=int, required=False)
    parser.add_argument('-zl','--zlevel', default=3, help="Adjustment of the compression ratio for compression DEFLATE. By default : 3 ", type=int, required=False)
    parser.add_argument('-mn','--min_val', default=0, help="Percentage gains that will be truncated for minimum values. By default : 0", type=float, required=False)
    parser.add_argument('-mx','--max_val', default=0.1, help="Percentage values that will be truncated for maximum values. By default: 0.1", type=float, required=False)
    parser.add_argument('-opt8b','--optimize_8bits', action='store_true', default=False, help="If active, optimize the used of 8 bits preserved histogram calculation. By default : False", required=False)
    parser.add_argument('-rvb','--rvb', action='store_true', default=False, help="If active, the output will be in RGB, otherwise the output will have the same number of bands that initial image. By default : False", required=False)
    parser.add_argument('-irc','--irc', action='store_true', default=False, help="If active, the output will be in IRC, otherwise the output will have the same number of bands that initial image. If -rvb and -irc are True, -rvb have priority. By default : False", required=False)
    parser.add_argument('-chao','--channel_order',nargs="+", default=['Red','Green','Blue','NIR'],help="Type of multispectral image : rapideye or spot6 or pleiade. By default : [Red,Green,Blue,NIR]",type=str,required=False)
    parser.add_argument('-raf','--format_raster', default="GTiff", help="Option : Format output image, by default : GTiff (GTiff, HFA...)", type=str, required=False)
    parser.add_argument('-rae','--extension_raster', default=".tif", help="Option : Extension file for image raster. By default : '.tif'", type=str, required=False)
    parser.add_argument('-log','--path_time_log',default="",help="Name of log", type=str, required=False)
    parser.add_argument('-sav','--save_results_inter',action='store_true',default=False,help="Save or delete intermediate result after the process. By default, False", required=False)
    parser.add_argument('-now','--overwrite',action='store_false',default=True,help="Overwrite files with same names. By default : True", required=False)
    parser.add_argument('-debug','--debug',default=3,help="Option : Value of level debug trace, default : 3 ",type=int, required=False)
    args = displayIHM(gui, parser)

    # Definition des variables issues du parser

     # Récupération des images d'entrée
    if args.image_input != None :
        image_input = args.image_input
        if not os.path.isfile(image_input):
            raise NameError (cyan + "ImagesAssembly : " + bold + red  + "File %s not existe!" %(image_input) + endC)

    # Récupération des images de sortie
    need_8bits = False
    if args.image_output_8bits != None:
        image_output_8bits = args.image_output_8bits
        need_8bits = True
    need_8bits = image_output_8bits != ""

    need_compress = False
    if args.image_output_compress != None:
        image_output_compress = args.image_output_compress
        need_compress = True
    need_compress = image_output_compress != ""

    # Paramètres de compression
    compress_type = None
    if args.compress!= None:
        compress_type = args.compress
        if compress_type.upper() not in ['DEFLATE', 'LZW', ''] :
            raise NameError(cyan + "ImagesAssembly : " + bold + red + "Parameter 'compress_type' value  is not in list ['DEFLATE', 'LZW', '']." + endC)

    if args.predictor!= None:
        predictor = args.predictor

    if args.zlevel!= None:
        zlevel = args.zlevel

    if args.min_val!= None:
        suppr_min = args.min_val

    if args.max_val!= None:
        suppr_max = args.max_val

    # Paramètres d'optimization
    if args.optimize_8bits!= None:
        need_optimize8b = args.optimize_8bits

    if args.rvb!= None:
        need_rvb = args.rvb
    if args.irc!= None:
        need_irc = args.irc
    if args.channel_order != None:
        channel_order = args.channel_order

    # Paramètre format des images de sortie
    if args.format_raster != None:
        format_raster = args.format_raster

    # Paramètre de l'extension des images rasters
    if args.extension_raster != None:
        extension_raster = args.extension_raster

    # Récupération du nom du fichier log
    if args.path_time_log!= None:
        path_time_log = args.path_time_log

    # Ecrasement nettoyage des fichiers
    if args.save_results_inter != None:
        save_results_intermediate = args.save_results_inter

    if args.overwrite!= None:
        overwrite = args.overwrite

    # Récupération de l'option niveau de debug
    if args.debug!= None:
        global debug
        debug = args.debug

    # Affichage des arguments récupérés
    if debug >= 3:
        print(bold + green + "Variables dans le parser" + endC)
        print(cyan + "ImageCompression : " + endC + "image_input : " + str(image_input) + endC)
        print(cyan + "ImageCompression : " + endC + "image_output_8bits : " + str(image_output_8bits) + endC)
        print(cyan + "ImageCompression : " + endC + "image_output_compress : " + str(image_output_compress) + endC)
        print(cyan + "ImageCompression : " + endC + "need_8bits : " + str(need_8bits) + endC)
        print(cyan + "ImageCompression : " + endC + "need_compress : " + str(need_compress) + endC)
        print(cyan + "ImageCompression : " + endC + "compress : " + str(compress_type) + endC)
        print(cyan + "ImageCompression : " + endC + "predictor : " + str(predictor) + endC)
        print(cyan + "ImageCompression : " + endC + "zlevel : " + str(zlevel) + endC)
        print(cyan + "ImageCompression : " + endC + "suppr_min : " + str(suppr_min) + endC)
        print(cyan + "ImageCompression : " + endC + "suppr_max : " + str(suppr_max) + endC)
        print(cyan + "ImageCompression : " + endC + "optimize_8bits : " + str(need_optimize8b) + endC)
        print(cyan + "ImageCompression : " + endC + "rvb : " + str(need_rvb) + endC)
        print(cyan + "ImageCompression : " + endC + "irc : " + str(need_irc) + endC)
        print(cyan + "ImageCompression : " + endC + "channel_order : " + str(channel_order) + endC)
        print(cyan + "ImageCompression : " + endC + "format_raster : " + str(format_raster) + endC)
        print(cyan + "ImageCompression : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "ImageCompression : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "ImageCompression : " + endC + "save_results_inter : " + str(save_results_intermediate) + endC)
        print(cyan + "ImageCompression : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "ImageCompression : " + endC + "debug : " + str(debug) + endC)

    # EXECUTION DE LA FONCTION
    # Si les dossiers de sortie n'existent pas, on les crées
    if need_compress:
        repertory_output = os.path.dirname(image_output_compress)
        if not os.path.isdir(repertory_output):
            os.makedirs(repertory_output)
    if need_8bits:
        repertory_output = os.path.dirname(image_output_8bits)
        if not os.path.isdir(repertory_output):
            os.makedirs(repertory_output)

    # Lancement de la fonction compression d'image
    if need_8bits or need_compress:
        convertImage(image_input, image_output_8bits, image_output_compress, need_8bits, need_compress, compress_type, predictor, zlevel, suppr_min, suppr_max, need_optimize8b, need_rvb, need_irc, path_time_log, channel_order, format_raster, extension_raster, save_results_intermediate, overwrite)

# ================================================

if __name__ == '__main__':
  main(gui=False)
