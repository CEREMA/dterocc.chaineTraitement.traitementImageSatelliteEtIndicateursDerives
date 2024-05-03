#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT QUI PERMET D'ENCHAINER LE CALCUL DE DIFFERENTES TEXTURES DE DIFFERENTS PARAMETRES DE DIFFERENTS CANAUX DE DIFFERENTES IMAGES       #
#                                                                                                                                           #
#############################################################################################################################################
"""
Nom de l'objet : NeoChannelsComputation.py
Description :
-------------
Objectif : calculer les textures et indices d une image donnee
Rq : utilisation des OTB Applications : otbcli_HaralickTextureExtraction, otbcli_SplitImage, otbcli_BandMath

Date de creation : 05/08/2014
----------
Histoire :
----------
Origine : le script originel provient du fichier TextureExtraction.py cree en 2013 et utilise par la chaine de traitement OCSOL V1.X
05/08/2013 : Transformation en brique elementaire (suppression des liens avec la chaine OCSOL), ajout du GEMI(erreur syntax), arguments "-channel_order" pour modifier le channel_order selon le type d images (rapideye, spot...)
-----------------------------------------------------------------------------------------------------
Modifications :
06/08/2013 : intégration dans la chaine globale
01/10/2014 : refonte du fichier harmonisation des régles de qualitées des niveaux de boucles et des paramétres dans args
21/05/2015 : simplification des parametres en argument plus de liste d'image en emtrée à traiter uniquement une image
01/07/2016 : modification des formules pour NDWI (Green-PIR/Green+PIR devenu PIR-MIR/PIR+MIR) et NDWI2 (Green-PIR+RE/Green+PIR+RE devenu Green-PIR/Green+PIR) d'après doc indiquée dans les 2 codes
------------------------------------------------------
A Reflechir/A faire :
traduire le docstring en anglais
importer la lib avec les fcts_text pour gérer le passage des listes dans args
correction erreur syntax dans la variable "eta"(bandmath) necessaire au calcul du GEMI
"""

from __future__ import print_function
import os, sys, glob ,string, math, argparse, shutil, time, platform, ast
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_log import timeLine
from Lib_file import removeFile
from Lib_raster import getMinMaxValueBandImage
from Lib_index import createNDVI, createNDVIMod, createTNDVI, createPNDVI, createNDWI, createNDWI2, createNDWI2Mod, createNDMI, createMNDWI, createISU, createGEMI, createBSI, createNDBI, createNBI, createIR, createCI, createBI, createBI2, createMSAVI2, createSIPI, createISI, createHIS, createVSSI, createBlueI

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 3
sys.dont_write_bytecode = True

# Les sorties de la fonction OTB otbcli_HaralickTextureExtraction a changé à partir de la version 7.x??? de l'OTB
pythonpath = os.environ["PYTHONPATH"]
print ("Identifier la version d'OTB : ")
pythonpath_list = pythonpath.split(os.sep)
otb_info = ""
for info in pythonpath_list :
    if info.find("OTB") > -1:
        otb_info = info.split("-")[1]
        break
print (otb_info)
if int(otb_info.split(".")[0]) >= 7 :
    IS_VERSION_UPPER_OTB_7_0 = True
else :
    IS_VERSION_UPPER_OTB_7_0 = False

###########################################################################################################################################
# FONCTION extractTexture()                                                                                                               #
###########################################################################################################################################
def extractTexture(image_input, repertory_neochannels_output, path_time_log, channels_list, texture_families_list, radius_list, indices_to_compute_list=[], channel_order=['Red','Green','Blue','NIR'], extension_raster=".tif", save_results_intermediate=False, overwrite=True, bin_number=64):
    """
    # ROLE:
    # calculer les textures et indices definis d'une image donnee
    # Compléments sur la fonction otbcli_HaralickTextureExtraction : https://www.orfeo-toolbox.org//CookBook/CookBooksu101.html
    # Compléments sur la fonction otbcli_SplitImage : http://www.orfeo-toolbox.org/CookBook/CookBooksu68.html#x95-2580005.1.10
    # Compléments sur la fonction otbcli_BandMath : http://www.orfeo-toolbox.org/CookBook/CookBooksu125.html#x161-9330005.10.1
    #
    # ENTREES DE LA FONCTION :
    #    image_input  : image a laquelle on souhaite calculer des neocanaux). Exemple : '/home/Travail/D3_Global/Images/Images_01.tif'
    #    repertory_neochannels_output : chemin vers repertoire ou ranger les neocanaux calcules, Attention besoin de bcp de place
    #    path_time_log : le fichier de log de sortie
    #    channels_list : Liste des canaux sur lesquels on veut calculer les textures. Exemple : channels_list = ['Red','Green','Blue','NIR','RE']
    #    texture_families_list : Liste des familles de textures que l'on veut calculer. Exemple: texture_families_list = ["simple","advanced","higher"]
    #    radius_list : Taille de la fenêtre que l'on veut utiliser pour le calcul des textures. Exemple : radius_list = [1,2,3,4,5,6,7...]
    #    indices_to_compute_list : indicesToComputeList = ["NDVI","NDVImod","TNDVI","NDWI","ISU","GEMI", "MSAVI2"], defaut=[]
    #    channel_order : identifiant des canaux de l image, exmple : {"Red":1,"Green":2,"Blue":3,"RE":4,"NIR":5}, defaut=[Red,Green,Blue,NIR]
    #    extension_raster : extension des fichiers raster de sortie, par defaut = '.tif'
    #    save_results_intermediate : fichiers de sorties intermediaires nettoyees, par defaut = False
    #    overwrite : supprime ou non les fichiers existants ayant le meme nom, defaut=True
    #    bin_number : Nombre de subdivisions prises en compte pour le calcul des tectures. Choix entre 4,8,32 et 64, defaut=64
    #
    # SORTIES DE LA FONCTION :
    #     Les images neocannaux
    #
    """

    # Mise à jour du Log
    starting_event = "extractTexture() : Extract texture starting : "
    timeLine(path_time_log,starting_event)

    # Affichage des parametres
    if debug >= 3:
        print(cyan + "extractTexture() : " + endC + "image_input: " + str(image_input) + endC)
        print(cyan + "extractTexture() : " + endC + "repertory_neochannels_output: " + str(repertory_neochannels_output) + endC)
        print(cyan + "extractTexture() : " + endC + "path_time_log: " + str(path_time_log) + endC)
        print(cyan + "extractTexture() : " + endC + "channels_list: " + str(channels_list) + endC)
        print(cyan + "extractTexture() : " + endC + "texture_families_list: " + str(texture_families_list) + endC)
        print(cyan + "extractTexture() : " + endC + "radius_list: " + str(radius_list) + endC)
        print(cyan + "extractTexture() : " + endC + "indices_to_compute_list: " + str(indices_to_compute_list) + endC)
        print(cyan + "extractTexture() : " + endC + "channel_order: " + str(channel_order) + endC)
        print(cyan + "extractTexture() : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "extractTexture() : " + endC + "overwrite: " + str(overwrite) + endC)
        print(cyan + "extractTexture() : " + endC + "bin_number: " + str(bin_number) + endC)

    # Constantes
    CODAGE = "float"

    # MISE EN PLACE DE VARIABLES UTILES POUR LE CALCUL DES INDICES ET VERIFICATION DE DONNEES
    # Récupération des bandes de couleurs

    Red = ""
    Blue = ""
    Green = ""
    RedEdge = ""
    NIR = ""
    MIR = ""
    SWIR1 = ""
    SWIR2 = ""
    DeepBlue = ""

    channels_number_dico ={"Red":0,"Green":0,"Blue":0,"NIR":0,"RE":0,"MIR":0,"SWIR1":0,"SWIR2":0,"DeepBlue":0}

    if "Red" in channel_order:
        num_channel = channel_order.index("Red")+1
        channels_number_dico["Red"] = num_channel
        Red = "im1b"+str(num_channel)
    if "Blue" in channel_order:
        num_channel = channel_order.index("Blue")+1
        channels_number_dico["Blue"] = num_channel
        Blue = "im1b"+str(num_channel)
    if "Green" in channel_order:
        num_channel = channel_order.index("Green")+1
        channels_number_dico["Green"] = num_channel
        Green = "im1b"+str(num_channel)
    if "RE" in channel_order :
        num_channel = channel_order.index("RE")+1
        channels_number_dico["RE"] = num_channel
        RedEdge = "im1b"+str(num_channel)
    if "NIR" in channel_order:
        num_channel = channel_order.index("NIR")+1
        channels_number_dico["NIR"] = num_channel
        NIR = "im1b"+str(num_channel)
    if "MIR" in channel_order:
        num_channel = channel_order.index("MIR")+1
        channels_number_dico["MIR"] = num_channel
        MIR = "im1b"+str(num_channel)
    if "SWIR1" in channel_order:
        num_channel = channel_order.index("SWIR1")+1
        channels_number_dico["SWIR1"] = num_channel
        SWIR1 = "im1b"+str(num_channel)
    if "SWIR2" in channel_order:
        num_channel = channel_order.index("SWIR2")+1
        channels_number_dico["SWIR2"] = num_channel
        SWIR1 = "im1b"+str(num_channel)
    if "DeepBlue" in channel_order:
        num_channel = channel_order.index("DeepBlue")+1
        channels_number_dico["DeepBlue"] = num_channel
        DeepBlue = "im1b"+str(num_channel)

    if "NDVI" in indices_to_compute_list and (Red == "" or NIR == ""):
        raise NameError(cyan + "extractTexture() : " + bold + red + "NDVI needs Red and NIR channels to be computed, and at least one is not specify in \"channel_order\""+ endC)
    if "MSAVI2" in indices_to_compute_list and (Red == "" or NIR == ""):
        raise NameError(cyan + "extractTexture() : " + bold + red + "MSAVI2 needs Red and NIR channels to be computed, and at least one is not specify in \"channel_order\""+ endC)
    if "NDVIMod" in indices_to_compute_list and (Red == "" or NIR == "" or RedEdge == ""):
        raise NameError(cyan + "extractTexture() : " + bold + red + "NDVIMod needs Red,NIR and RedEdge channels to be computed, and at least one is not specify in \"channel_order\""+ endC)
    if "TNDVI" in indices_to_compute_list and (Red == "" or NIR == ""):
        raise NameError(cyan + "extractTexture() : " + bold + red + "TNDVI needs Red and NIR channels to be computed, and at least one is not specify in \"channel_order\""+ endC)
    if "NDWI" in indices_to_compute_list and (MIR == "" or NIR == ""):
        raise NameError(cyan + "extractTexture() : " + bold + red + "NDWI needs NIR and MIR channels to be computed, and at least one is not specify in \"channel_order\""+ endC)
    if "ISU" in indices_to_compute_list and (Red == "" or NIR == ""):
        raise NameError(cyan + "extractTexture() : " + bold + red + "ISU needs Red and NIR channels to be computed, and at least one is not specify in \"channel_order\""+ endC)
    if "GEMI" in indices_to_compute_list and (Red == "" or NIR == ""):
        raise NameError(cyan + "extractTexture() : " + bold + red + "GEMI needs Red and NIR channels to be computed, and at least one is not specify in \"channel_order\""+ endC)
    if "BSI" in indices_to_compute_list and (Red == "" or NIR == ""):
        raise NameError(cyan + "extractTexture() : " + bold + red + "BSI needs Red and NIR channels to be computed, and at least one is not specify in \"channel_order\""+ endC)
    if "NDBI" in indices_to_compute_list and (MIR == "" or NIR == ""):
        raise NameError(cyan + "extractTexture() : " + bold + red + "NDBI needs MIR and NIR channels to be computed, and at least one is not specify in \"channel_order\""+ endC)
    if "NDWI2" in indices_to_compute_list and (Green == "" or NIR == ""):
        raise NameError(cyan + "extractTexture() : " + bold + red + "NDWI2 needs Green and NIR channels to be computed, and at least one is not specify in \"channel_order\""+ endC)
    if "NDWI2Mod" in indices_to_compute_list and (Green == "" or NIR == ""):
        raise NameError(cyan + "extractTexture() : " + bold + red + "NDWI2Mod needs Green, NIR and RedEdge channels to be computed, and at least one is not specify in \"channel_order\""+ endC)
    if "MNDWI" in indices_to_compute_list and (Green == "" or MIR == ""):
        raise NameError(cyan + "extractTexture() : " + bold + red + "MNDWI needs Green and MIR channels to be computed, and at least one is not specify in \"channel_order\""+ endC)
    if "IR" in indices_to_compute_list and  (Green == "" or Blue == "" or Red == ""):
        raise NameError(cyan + "extractTexture() : " + bold + red + "IR needs Green and Blue and Red channels to be computed, and at least one is not specify in \"channel_order\""+ endC)
    if "NBI" in indices_to_compute_list and (Red == "" or NIR == "" or MIR == ""):
        raise NameError(cyan + "extractTexture() : " + bold + red + "NBI needs Red and NIR and MIR channels to be computed, and at least one is not specify in \"channel_order\""+ endC)
    if "PNDVI" in indices_to_compute_list and (Red == "" or Green == "" or Blue == "" or NIR == ""):
        raise NameError(cyan + "extractTexture() : " + bold + red + "PNDVI needs Red and Green and Blue and NIRchannels to be computed, and at least one is not specify in \"channel_order\""+ endC)
    if "CI" in indices_to_compute_list and (Red == "" or Green == ""):
        raise NameError(cyan + "extractTexture() : " + bold + red + "CI needs Red and Green channels to be computed, and at least one is not specify in \"channel_order\""+ endC)
    if "BI" in indices_to_compute_list and (Red == "" or Green == "" or Blue == ""):
        raise NameError(cyan + "extractTexture() : " + bold + red + "BI needs Red and Green and Blue channels to be computed, and at least one is not specify in \"channel_order\""+ endC)
    if "SIPI" in indices_to_compute_list and (Red == "" or Blue == "" or NIR == ""):
        raise NameError(cyan + "extractTexture() : " + bold + red + "SIPI needs Red and Blue and NIR channels to be computed, and at least one is not specify in \"channel_order\""+ endC)
    if "ISI" in indices_to_compute_list and (Red == "" or Green == "" or Blue == "" or NIR == ""):
        raise NameError(cyan + "extractTexture() : " + bold + red + "ISI needs Red and Green and Blue and NIR channels to be computed, and at least one is not specify in \"channel_order\""+ endC)
    if "HIS" in indices_to_compute_list and (Red == "" or Green == "" or Blue == "" or NIR == ""):
        raise NameError(cyan + "extractTexture() : " + bold + red + "HIS needs Red and Green and Blue and NIR channels to be computed, and at least one is not specify in \"channel_order\""+ endC)
    if "VSSI" in indices_to_compute_list and (Red == "" or Green == "" or NIR == ""):
        raise NameError(cyan + "extractTexture() : " + bold + red + "VSSI needs Red and Green and NIR channels to be computed, and at least one is not specify in \"channel_order\""+ endC)
    if "BLUEI" in indices_to_compute_list and (Red == "" or Green == "" or Blue == ""):
        raise NameError(cyan + "extractTexture() : " + bold + red + "BlueI needs Red and Green and Blue channels to be computed, and at least one is not specify in \"channel_order\""+ endC)

    # CALCUL DES TEXTURES - sur image, bande et famille de texture (autres paramètres fixés)

    image_name = os.path.splitext(os.path.basename(image_input))[0] # Récupération du nom simple de l'image (sans le tif). Exemple : image_name = Image_01
    repertory_neochannels_output += os.sep

    print(cyan + "extractTexture() : " + bold + green + "DEBUT DU CALCUL DE IMAGE : %s , BANDES(S) : %s , TEXTURE(S) : %s, RAYON(S) : %s " %(image_input,channels_list,texture_families_list,radius_list) + endC)

    for channel in channels_list: # Rappel : channels_list --> Liste des canaux sur lesquels on veut calculer les textures. Exemple : channels_list = ['Red','Green','Blue','NIR','RE']
        print(cyan + "extractTexture() : " + bold + green + "Debut du calcul de image(s) : %s , bande(s) : %s , texture(s) : %s, rayon(s) : %s " %(image_input,channel,texture_families_list,radius_list) + endC)
        channel_num = channels_number_dico[channel] # Transformation du caractère de canal en numéro de canal

        if debug >= 2:
            print(cyan + "extractTexture() : " + endC + "image : " + str(image_input) + endC)
            print(cyan + "extractTexture() : " + endC + "channel : " + str(channel) + endC)

        # Récupération de la valeur minimale et maximale du canal
        image_max_band, image_mini_band = getMinMaxValueBandImage(image_input, channel_num)

        # Valeur maximale des pixels sur la bande
        image_maximum = str(int(image_max_band))
        # Valeur minimale des pixels sur la bande
        image_minimum = str(int(image_mini_band))

        if debug >= 2:
            print(cyan + "extractTexture() : " + bold + green + "Statistiques du canal %s de l'image %s" %(channel,image_input) + endC)
            print(cyan + "extractTexture() : " + endC + "image_maximum : " + image_maximum + endC)
            print(cyan + "extractTexture() : " + endC + "image_minimum : " + image_minimum + endC)

        for texture in texture_families_list: # Rappel : texture_families_list = liste des familles de textures que l'on veut calculer. Exemple: texture_families_list = ["simple","advanced","higher"]
            print(cyan + "extractTexture() : " + bold + green + "Debut du calcul de image(s) : %s , bande(s) : %s , texture(s) : %s, rayon(s) : %s " %(image_input,channel,texture,radius_list) + endC)

            for radius in radius_list: # Rappel : Taille des fenêtres que l'on veut utiliser pour le calcul des textures. Exemple : radius_list = [1,2,3,4,5,6,7...]
                print(cyan + "extractTexture() : " + bold + green + "Debut du calcul de image(s) : %s , bande(s) : %s , texture(s) : %s, rayon(s) : %s " %(image_input,channel,texture,radius) + endC)

                output_textures_base_name = repertory_neochannels_output + image_name + "_chan" + channel + "_rad" + str(radius) # Exemple : /home/scgsi/Desktop/Jacques/TravailV2/ImagesTestChaine/APTV_01/NeoCanaux/Image_01_chan1_rad3
                output_textures_image_name = output_textures_base_name + "_" + texture
                output_textures = output_textures_image_name + extension_raster                                                  # Exemple : /home/scgsi/Desktop/Jacques/TravailV2/ImagesTestChaine/APTV_01/NeoCanaux/Image_01_chan1_rad3_simple.tif
                output_textures_split =  output_textures_image_name + "_band" + extension_raster                                 # Exemple : /home/scgsi/Desktop/Jacques/TravailV2/ImagesTestChaine/APTV_01/NeoCanaux/Image_01_chan1_rad3_simple_band.tif

                if debug >= 4:
                    print(cyan + "extractTexture() : " + bold + green + "Nom des textures en sortie" + endC)
                    print(cyan + "extractTexture() : " + endC + "repertory_neochannels_output : " + str(repertory_neochannels_output) + endC)
                    print(cyan + "extractTexture() : " + endC + "image_name                   : " + str(image_name) + endC)
                    print(cyan + "extractTexture() : " + endC + "channel                      : " + str(channel) + endC)
                    print(cyan + "extractTexture() : " + endC + "texture                      : " + str(texture) + endC)
                    print(cyan + "extractTexture() : " + endC + "radius                       : " + str(radius) + endC)
                    print(cyan + "extractTexture() : " + endC + "output_textures              : " + str(output_textures) + endC)
                    print(cyan + "extractTexture() : " + endC + "output_textures_split        : " + str(output_textures_split) + endC)

                # Test si les fichiers resultats existent deja
                files_exist = False
                files_name_texture_list = []

                if (texture == "simple") :
                    files_name_texture_list = [''] * 8
                    files_name_texture_list[0] = output_textures_base_name + "_" + 'Energy' + extension_raster
                    files_name_texture_list[1] = output_textures_base_name + "_" + 'Entropy' + extension_raster
                    files_name_texture_list[2] = output_textures_base_name + "_" + 'Correlation' + extension_raster
                    files_name_texture_list[3] = output_textures_base_name + "_" + 'InverseDifferenceMoment' + extension_raster
                    files_name_texture_list[4] = output_textures_base_name + "_" + 'Inertia' + extension_raster
                    files_name_texture_list[5] = output_textures_base_name + "_" + 'ClusterShade' + extension_raster
                    files_name_texture_list[6] = output_textures_base_name + "_" + 'ClusterProminence' + extension_raster
                    files_name_texture_list[7] = output_textures_base_name + "_" + 'HaralickCorrelation' + extension_raster
                    files_exist = True
                    for file_texture in files_name_texture_list :
                        if not os.path.isfile(file_texture) :
                            files_exist = False
                            break


                if (texture == "advanced") :
                    files_name_texture_list = [''] * 10
                    files_name_texture_list[0] = output_textures_base_name + "_" + 'Mean' + extension_raster
                    files_name_texture_list[1] = output_textures_base_name + "_" + 'Variance' + extension_raster
                    files_name_texture_list[2] = output_textures_base_name + "_" + 'SumAverage' + extension_raster
                    files_name_texture_list[3] = output_textures_base_name + "_" + 'SumVariance' + extension_raster
                    files_name_texture_list[4] = output_textures_base_name + "_" + 'SumEntropy' + extension_raster
                    files_name_texture_list[5] = output_textures_base_name + "_" + 'DifferenceOfEntropies' + extension_raster
                    files_name_texture_list[6] = output_textures_base_name + "_" + 'DifferenceOfVariances' + extension_raster
                    files_name_texture_list[7] = output_textures_base_name + "_" + 'IC1' + extension_raster
                    files_name_texture_list[8] = output_textures_base_name + "_" + 'IC2' + extension_raster
                    files_name_texture_list[9] = output_textures_base_name + "_" + 'Dissimilarity' + extension_raster
                    files_exist = True
                    for file_texture in files_name_texture_list :
                        if not os.path.isfile(file_texture) :
                            files_exist = False
                            break

                if (texture == "higher") :
                    if IS_VERSION_UPPER_OTB_7_0 :
                        files_name_texture_list = [''] * 10
                    else :
                        files_name_texture_list = [''] * 11
                        files_name_texture_list[10] = output_textures_base_name + "_" + 'LongRunHighGreyLevelEmphasis' + extension_raster

                    files_name_texture_list[0] = output_textures_base_name + "_" + 'ShortRunEmphasis' + extension_raster
                    files_name_texture_list[1] = output_textures_base_name + "_" + 'LongRunEmphasis' + extension_raster
                    files_name_texture_list[2] = output_textures_base_name + "_" + 'GreyLevelNonUniformity' + extension_raster
                    files_name_texture_list[3] = output_textures_base_name + "_" + 'RunLengthNonUniformity' + extension_raster
                    files_name_texture_list[4] = output_textures_base_name + "_" + 'RunPercentage' + extension_raster
                    files_name_texture_list[5] = output_textures_base_name + "_" + 'LowGreyLevelRunEmphasis' + extension_raster
                    files_name_texture_list[6] = output_textures_base_name + "_" + 'HighGreyLevelRunEmphasis' + extension_raster
                    files_name_texture_list[7] = output_textures_base_name + "_" + 'ShortRunLowGreyLevelEmphasis' + extension_raster
                    files_name_texture_list[8] = output_textures_base_name + "_" + 'ShortRunHighGreyLevelEmphasis' + extension_raster
                    files_name_texture_list[9] = output_textures_base_name + "_" + 'LongRunLowGreyLevelEmphasis' + extension_raster

                    files_exist = True
                    for file_texture in files_name_texture_list :
                        if not os.path.isfile(file_texture) :
                            files_exist = False
                            break

                if not overwrite and files_exist:
                    print( cyan + "extractTexture() : " + endC + "Textures %s have already been calculated for image %s , channel %s and radius %s. not overwrite : they will not be calculated again." %(texture,image_input,channel,radius) + endC)
                else:
                    # sinon (option écrasement activée ou configuration non calculée) : lancement du calcul de la texture
                    if debug >= 2:
                        print(cyan + "extractTexture() : " + bold + green + "Parametres d entree de otbcli_HaralickTextureExtraction" + endC)
                        print(cyan + "extractTexture() : " + endC + "image_input     : " + str(image_input) + endC)
                        print(cyan + "extractTexture() : " + endC + "channel         : " + str(channel) + endC)
                        print(cyan + "extractTexture() : " + endC + "radius          : " + str(radius) + endC)
                        print(cyan + "extractTexture() : " + endC + "image_minimum   : " + str(image_minimum) + endC)
                        print(cyan + "extractTexture() : " + endC + "image_maximum   : " + str(image_maximum) + endC)
                        print(cyan + "extractTexture() : " + endC + "bin_number      : " + str(bin_number) + endC)
                        print(cyan + "extractTexture() : " + endC + "texture         : " + str(texture) + endC)
                        print(cyan + "extractTexture() : " + endC + "output_textures : " + str(output_textures) + endC)

                    # Nettoyage des fichiers de texture
                    for file_texture in files_name_texture_list :
                        removeFile(file_texture)

                    try: # Suppression de l'éventuel fichier existant
                        removeFile(output_textures)
                    except Exception:
                        pass # Si le fichier ne peut pas être supprimé, on suppose qu'il n'existe pas et on passe à la suite

                    ########################################
                    # CALCUL DES TEXTURES                  #
                    ########################################

                    command = "otbcli_HaralickTextureExtraction -in %s -channel %s -parameters.xrad %s -parameters.yrad %s -parameters.min %s -parameters.max %s -parameters.nbbin %s -texture %s -out %s %s" %(image_input, channel_num , str(radius), str(radius), image_minimum, image_maximum, bin_number, texture, output_textures, CODAGE)

                    if debug >= 2:
                            print(cyan + "extractTexture() : " + endC + "command otbcli_HaralickTextureExtraction : %s " %(command)+ endC)

                    exitCode = os.system(command) # Execution de la commande
                    if exitCode != 0:
                        raise NameError(cyan + "extractTexture() : " + bold + red + "An error occured during otbcli_HaralickTextureExtraction command. See error message above." + endC)

                    if debug >= 2:
                        print(cyan + "extractTexture() : " + endC + bold + green + "Parametres d entree de otbcli_SplitImage" + endC)
                        print(cyan + "extractTexture() : " + endC + "output_textures : " + str(output_textures) + endC)
                        print(cyan + "extractTexture() : " + endC + "output_textures_split   : " + str(output_textures_split) + endC)

                    # Découpage de l'image avec 8 ou 9 bandes de texture en 8 ou 9 images-textures. Atribution automatique des noms par otbcli_SplitImage
                    command = "otbcli_SplitImage -in %s -out %s" %(output_textures, output_textures_split)

                    if debug >= 2:
                        print(cyan + "extractTexture() : " + endC + "command otbcli_SplitImage : %s " %(command)+ endC)

                    exitCode = os.system(command)
                    if exitCode != 0:
                        raise NameError(cyan + "extractTexture() : " + bold + red + "An error occured during otbcli_SplitImage command. See error message above."  + endC)

                    # Nettoyage du fichier intermediaire
                    if  not  save_results_intermediate :
                        removeFile(output_textures)

                    ################################################################################################
                    # RENOMAGE DES NOMS DE TEXTURE                                                                 #
                    # Supression du nom de la famille et transformation du numéro de bande en nom de texture       #
                    ################################################################################################

                    print(cyan + "extractTexture() : " + endC + bold + green + "Debut du renomage des textures de l'image " + str(image_input)  + endC)

                    # Réecriture des nom de textures simples ou advanced ou higher
                    for i in range (len(files_name_texture_list)) :
                        texture_name_final = files_name_texture_list[i]
                        texture_name = output_textures_base_name + "_" + texture + "_band" + "_" + str(i) + extension_raster
                        os.rename(texture_name, texture_name_final)

                    print(cyan + "extractTexture() : " + endC + bold + green + "Fin du renomage des textures de l'image " + str(image_input)  + endC)

                print(cyan + "extractTexture() : " + endC + bold + green + "Fin du calcul de image : %s , bande(s) : %s , texture(s) : %s, rayon(s) : %s " %(image_input,channel,texture,radius) + endC)
            print(cyan + "extractTexture() : " + endC + bold + green + "Fin du calcul de image : %s , bande(s) : %s , texture(s) : %s, rayon(s) : %s " %(image_input,channel,texture,radius_list) + endC)
        print(cyan + "extractTexture() : " + endC + bold + green + "Fin du calcul de image : %s , bande(s) : %s , texture(s) : %s, rayon(s) : %s " %(image_input,channel,texture_families_list,radius_list) + endC)
    print(bold + green + "FIN DU CALCUL DE IMAGE : %s , BANDE(S) : %s , TEXTURE(S) : %s, RAYON(S) : %s " %(image_input,channels_list,texture_families_list,radius_list) + endC)

    ########################################
    # CALCUL DES INDICES                   #
    ########################################

    print(bold + green + "DEBUT DU CALCUL DES INDICES %s DE L'IMAGE %s" %(indices_to_compute_list,image_input) + endC)

    for indice in indices_to_compute_list:
        # NDVI (Vegetation)
        if indice == "NDVI" :
            output_NDVI = repertory_neochannels_output + image_name + "_NDVI" + extension_raster
            check_NDVI = os.path.isfile(output_NDVI)

            if check_NDVI and not overwrite:
                print(cyan + "extractTexture() : " + endC + "File " + output_NDVI + " already exists and will not be calculated again.")
            else:
                createNDVI(image_input, output_NDVI, channel_order, CODAGE)

        # NDVIMod (Vegetation)
        if indice == "NDVIMod":
            output_NDVImod = repertory_neochannels_output + image_name + "_NDVImod" + extension_raster
            check_NDVImod = os.path.isfile(output_NDVImod)

            if check_NDVImod and not overwrite:
                print(cyan + "extractTexture() : " + endC + "File " + output_NDVImod + " already exists and will not be calculated again.")
            else:
                createNDVIMod(image_input, output_NDVImod, channel_order, CODAGE)

        # NDMI (Humidité)
        if indice == "NDMI":
            output_NDMI = repertory_neochannels_output + image_name + "_NDMI" + extension_raster
            check_NDMI = os.path.isfile(output_NDMI)

            if check_NDMI and not overwrite:
                print(cyan + "extractTexture() : " + endC + "File " + output_NDMI + " already exists and will not be calculated again.")
            else:
                createNDMI(image_input, output_NDMI, channel_order, CODAGE)

        # TNDVI (Vegetation)
        if indice == "TNDVI":
            output_TNDVI = repertory_neochannels_output + image_name + "_TNDVI" + extension_raster
            check_TNDVI = os.path.isfile(output_TNDVI)

            if check_TNDVI and not overwrite:
                print(cyan + "extractTexture() : " + endC + "File " + output_TNDVI + " already exists and will not be calculated again.")
            else:
                createTNDVI(image_input, output_TNDVI, channel_order, CODAGE)

        # NDWI (Eau)
        if indice == "NDWI":
            output_NDWI = repertory_neochannels_output + image_name + "_NDWI" + extension_raster
            check_NDWI = os.path.isfile(output_NDWI)

            if check_NDWI and not overwrite:
                print(cyan + "extractTexture() : " + endC + "File " + output_NDWI + " already exists and will not be calculated again.")
            else:
                createNDWI(image_input, output_NDWI, channel_order, CODAGE)

        # ISU (Bati)
        if indice == "ISU":
            output_ISU = repertory_neochannels_output + image_name + "_ISU" + extension_raster
            check_ISU = os.path.isfile(output_ISU)

            if check_ISU and not overwrite:
                print(cyan + "extractTexture() : " + endC + "File " + output_ISU + " already exists and will not be calculated again.")
            else:
                createISU(image_input, output_ISU, channel_order, CODAGE)

        # GEMI (Vegetation)
        if indice == "GEMI":
            output_GEMI = repertory_neochannels_output + image_name + "_GEMI" + extension_raster
            check_GEMI = os.path.isfile(output_GEMI)

            if check_GEMI and not overwrite:
                print(cyan + "extractTexture() : " + endC + "File " + output_GEMI + " already exists and will not be calculated again.")
            else:
                createGEMI(image_input, output_GEMI, channel_order, CODAGE)

        # BSI (Vegetation)
        if indice == "BSI":
            output_BSI = repertory_neochannels_output + image_name + "_BSI" + extension_raster
            check_BSI = os.path.isfile(output_BSI)

            if check_BSI and not overwrite:
                print(cyan + "extractTexture() : " + endC + "File " + output_BSI + " already exists and will not be calculated again.")
            else:
                createBSI(image_input, output_BSI, channel_order, CODAGE)

        # NDBI (Bati)
        if indice == "NDBI":
            output_NDBI = repertory_neochannels_output + image_name + "_NDBI" + extension_raster
            check_NDBI = os.path.isfile(output_NDBI)

            if check_NDBI and not overwrite:
                print(cyan + "extractTexture() : " + endC + "File " + output_NDBI + " already exists and will not be calculated again.")
            else:
                createNDBI(image_input, output_NDBI, channel_order, CODAGE)

        # NDWI2 (Eau)
        if indice == "NDWI2":
            output_NDWI2 = repertory_neochannels_output + image_name + "_NDWI2" + extension_raster
            check_NDWI2 = os.path.isfile(output_NDWI2)

            if check_NDWI2 and not overwrite:
                print(cyan + "extractTexture() : " + endC + "File " + output_NDWI2 + " already exists and will not be calculated again.")
            else:
                createNDWI2(image_input, output_NDWI2, channel_order, CODAGE)

        # NDWI2Mod (Eau)
        if indice == "NDWI2Mod":
            output_NDWI2Mod = repertory_neochannels_output + image_name + "_NDWI2Mod" + extension_raster
            check_NDWI2Mod = os.path.isfile(output_NDWI2Mod)

            if check_NDWI2Mod and not overwrite:
                print(cyan + "extractTexture() : " + endC + "File " + output_NDWI2Mod + " already exists and will not be calculated again.")
            else:
                createNDWI2Mod(image_input, output_NDWI2Mod, channel_order, CODAGE)

        # MNDWI (Eau)
        if indice == "MNDWI":
            output_MNDWI = repertory_neochannels_output + image_name + "_MNDWI" + extension_raster
            check_MNDWI = os.path.isfile(output_MNDWI)

            if check_MNDWI and not overwrite:
                print(cyan + "extractTexture() : " + endC + "File " + output_MNDWI + " already exists and will not be calculated again.")
            else:
                createMNDWI(image_input, output_MNDWI, channel_order, CODAGE)

        # IR (Sol)
        if indice == "IR":
            output_IR = repertory_neochannels_output + image_name + "_IR" + extension_raster
            check_IR = os.path.isfile(output_IR)

            if check_IR and not overwrite:
                print(cyan + "extractTexture() : " + endC + "File " + output_IR + " already exists and will not be calculated again.")
            else:
                createIR(image_input, output_IR, channel_order, CODAGE)

        # NBI (Bati)
        if indice == "NBI":
            output_NBI = repertory_neochannels_output + image_name + "_NBI" + extension_raster
            check_NBI = os.path.isfile(output_NBI)

            if check_NBI and not overwrite:
                print(cyan + "extractTexture() : " + endC + "File " + output_NBI + " already exists and will not be calculated again.")
            else:
                createNBI(image_input, output_NBI, channel_order, CODAGE)

        # PNDVI (Vegetation)
        if indice == "PNDVI":
            output_PNDVI = repertory_neochannels_output + image_name + "_PNDVI" + extension_raster
            check_PNDVI = os.path.isfile(output_PNDVI)

            if check_PNDVI and not overwrite:
                print(cyan + "extractTexture() : " + endC + "File " + output_PNDVI + " already exists and will not be calculated again.")
            else:
                createPNDVI(image_input, output_PNDVI, channel_order, CODAGE)

        # CI (Sol)
        if indice == "CI":
            output_CI = repertory_neochannels_output + image_name + "_CI" + extension_raster
            check_CI = os.path.isfile(output_CI)

            if check_CI and not overwrite:
                print(cyan + "extractTexture() : " + endC + "File " + output_CI + " already exists and will not be calculated again.")
            else:
                createCI(image_input, output_CI, channel_order, CODAGE)

        # BI (Brillance)
        if indice == "BI":
            output_BI = repertory_neochannels_output + image_name + "_BI" + extension_raster
            check_BI = os.path.isfile(output_BI)

            if check_BI and not overwrite:
                print(cyan + "extractTexture() : " + endC + "File " + output_BI + " already exists and will not be calculated again.")
            else:
                createBI(image_input, output_BI, channel_order, CODAGE)

        # BI2 (Brillance)
        if indice == "BI2":
            output_BI2 = repertory_neochannels_output + image_name + "_BI2" + extension_raster
            check_BI2 = os.path.isfile(output_BI2)

            if check_BI2 and not overwrite:
                print(cyan + "extractTexture() : " + endC + "File " + output_BI2 + " already exists and will not be calculated again.")
            else:
                createBI2(image_input, output_BI2, channel_order, CODAGE)

        # MSAVI2 (Vegetation)
        if indice == "MSAVI2" :
            output_MSAVI2 = repertory_neochannels_output + image_name + "_MSAVI2" + extension_raster
            check_MSAVI2 = os.path.isfile(output_MSAVI2)

            if check_MSAVI2 and not overwrite:
                print(cyan + "extractTexture() : " + endC + "File " + output_MSAVI2 + " already exists and will not be calculated again.")
            else:
                createMSAVI2(image_input, output_MSAVI2, channel_order, CODAGE)

        # SIPI (Vegetation)
        if indice == "SIPI" :
            output_SIPI = repertory_neochannels_output + image_name + "_SIPI" + extension_raster
            check_SIPI = os.path.isfile(output_SIPI)

            if check_SIPI and not overwrite:
                print(cyan + "extractTexture() : " + endC + "File " + output_SIPI + " already exists and will not be calculated again.")
            else:
                createSIPI(image_input, output_SIPI, channel_order, CODAGE)

        # ISI (Ombre)
        if indice == "ISI" :
            output_ISI = repertory_neochannels_output + image_name + "_ISI" + extension_raster
            check_ISI = os.path.isfile(output_ISI)

            if check_ISI and not overwrite:
                print(cyan + "extractTexture() : " + endC + "File " + output_ISI + " already exists and will not be calculated again.")
            else:
                createISI(image_input, output_ISI, channel_order, CODAGE)

        # HIS (Image teinte, intensite, saturation)
        if indice == "HIS" :
            output_HIS = repertory_neochannels_output + image_name + "_HIS" + extension_raster
            check_HIS = os.path.isfile(output_HIS)

            if check_HIS and not overwrite:
                print(cyan + "extractTexture() : " + endC + "File " + output_HIS + " already exists and will not be calculated again.")
            else:
                createHIS(image_input, output_HIS, channel_order, CODAGE)

        # VSSI (Salinité)
        if indice == "VSSI" :
            output_VSSI = repertory_neochannels_output + image_name + "_VSSI" + extension_raster
            check_VSSI = os.path.isfile(output_VSSI)

            if check_VSSI and not overwrite:
                print(cyan + "extractTexture() : " + endC + "File " + output_VSSI + " already exists and will not be calculated again.")
            else:
                createVSSI(image_input, output_VSSI, channel_order, CODAGE)

        # BlueI (Nuage)
        if indice == "BLUEI" :
            output_BLUEI = repertory_neochannels_output + image_name + "_BLUEI" + extension_raster
            check_BLUEI = os.path.isfile(output_BLUEI)

            if check_BLUEI and not overwrite:
                print(cyan + "extractTexture() : " + endC + "File " + output_BLUEI + " already exists and will not be calculated again.")
            else:
                createBlueI(image_input, output_BLUEI, channel_order, CODAGE)

    # Supression des .geom des fichiers d'indices - A GARDER?
    for file_to_remove in glob.glob(repertory_neochannels_output + os.sep + "*.geom"):
        removeFile(file_to_remove)

    print(bold + green + "FIN DU CALCUL DES INDICES %s DE L'IMAGE %s " %(indices_to_compute_list,image_input) + endC)

    # Mise à jour du Log
    ending_event = "extractTexture() : Extract texture ending : "
    timeLine(path_time_log,ending_event)

    return

###########################################################################################################################################
# MISE EN PLACE DU PARSER                                                                                                                 #
###########################################################################################################################################

# Code executé seulement dans le cas ou le script est lancé depuis une ligne de commande
# Il n'est pas executé lors d'un import NeoChannelsComputation.py
# Exemple de lancement en ligne de commande:
# python NeoChannelsComputation.py -i ../ImagesTestChaine/APTV_05/APTV_05.tif -patho ../ImagesTestChaine/APTV_05/Neocanaux -chan Green NIR -fam simple -rad 3 6 -chao Red Green Blue NIR -ind NDVI TNDVI -log ../ImagesTestChaine/APTV_01/fichierTestLog.txt

def main(gui=False):

    # Définition des arguments possibles pour l'appel en ligne de commande
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,  prog="NeoChannelsComputation",description="\
    Info : Compute textures. \n\
    Objectif : Calculer les textures et indices d une image donnee. \n\
    Example : python NeoChannelsComputation.py -i ../ImagesTestChaine/APTV_05/APTV_05.tif \n\
                                               -patho ../ImagesTestChaine/APTV_05/Neocanaux \n\
                                               -chan Green NIR \n\
                                               -fam simple \n\
                                               -rad 3 6 \n\
                                               -chao Red Green Blue NIR \n\
                                               -ind NDVI TNDVI -log \n\
                                               ../ImagesTestChaine/APTV_01/fichierTestLog.txt ")

    # Paramètres généraux
    parser.add_argument('-i','--image_input',default="",help="Image input to treat", type=str, required=True)
    parser.add_argument('-patho','--path_output',default=os.getcwd()+os.sep ,help="Storage directory of textures and indices products. By default, current directory",type=str, required=False)
    parser.add_argument('-chan','--channels_list',nargs="+", default=[],help="List of channels to process. Available channels are [Red, Green, Blue, RE, NIR]",type=str,required=False)
    parser.add_argument('-fam','--texture_families_list',nargs="+", default=[],help="List of texture families to process. Available texture are [simple, advanced, higher]",type=str, required=False)
    parser.add_argument('-rad','--radius_list',nargs="+", default=[],help="List of radius to process. Available  radius values are [1, 2, 3 ,4, 5, 7 ...]",type=int,required=False)
    parser.add_argument('-chao','--channel_order',nargs="+", default=['Red','Green','Blue','NIR'],help="Type of multispectral image : rapideye or spot6 or pleiade. By default : [Red,Green,Blue,NIR]",type=str,required=False)
    parser.add_argument('-bin','--bin_number',default=64,help="Number of subdivisions considered for the  computing textures. Chose between 4,8,32 and 64", type=int, required=False)
    parser.add_argument('-ind','--indices_list',nargs="+", default=[], help="List of indices to process. Available indices are [NDVI, NDVIMod, TNDVI, NDWI, ISU, GEMI, BSI, NDBI, NDWI2, NDWI2Mod, MNDWI, IR, NBI, PNDVI, CI, BI]. By default, none indice",type=str, required=False)
    parser.add_argument('-rae','--extension_raster', default=".tif", help="Option : Extension file for image raster. By default : '.tif'", type=str, required=False)
    parser.add_argument('-log','--path_time_log',default="",help="Name of log", type=str, required=False)
    parser.add_argument('-sav','--save_results_inter',action='store_true',default=False,help="Save or delete intermediate result after the process. By default, False", required=False)
    parser.add_argument('-now','--overwrite',action='store_false',default=True,help="Overwrite files with same names. By default, True",required=False)
    parser.add_argument('-debug','--debug',default=3,help="Option : Value of level debug trace, default : 3 ",type=int, required=False)
    args = displayIHM(gui, parser)

    # RECUPERATION DES ARGUMENTS

    # Récupération des arguments du parser
    if args.image_input != None:
        image_input = args.image_input
        if not os.path.isfile(image_input):
            raise NameError (cyan + "NeoChannelsComputation : " + bold + red  + "File %s not existe!" %(image_input) + endC)

    # Récupération du répertoires de sortie
    if args.path_output != None:
        repertory_neochannels_output = args.path_output

    # Récupération des parametres utile à la creation des neocannaux
    if args.channels_list != None:
        channels_list = args.channels_list

    if args.texture_families_list != None:
        texture_families_list = args.texture_families_list

    if args.radius_list != None:
        radius_list = args.radius_list

    if args.channel_order != None:
        channel_order = args.channel_order

    if args.bin_number != None:
        bin_number = args.bin_number

    if args.indices_list != None:
        indices_to_compute_list = args.indices_list

    # Paramètre de l'extension des images rasters
    if args.extension_raster != None:
        extension_raster = args.extension_raster

    # Récupération du nom du fichier log
    if args.path_time_log!= None:
        path_time_log = args.path_time_log

    if args.save_results_inter != None:
        save_results_intermediate = args.save_results_inter

    if args.overwrite != None:
        overwrite = args.overwrite

    # Récupération de l'option niveau de debug
    if args.debug!= None:
        global debug
        debug = args.debug

    if debug >= 3:
        print(bold + green + "Variables dans le parser" + endC)
        print(cyan + "NeoChannelsComputation : " + endC + "image_input : " + str(image_input) + endC)
        print(cyan + "NeoChannelsComputation : " + endC + "path_output : " + str(repertory_neochannels_output) + endC)
        print(cyan + "NeoChannelsComputation : " + endC + "channels_list : " + str(channels_list) + endC)
        print(cyan + "NeoChannelsComputation : " + endC + "texture_families_list : " + str(texture_families_list) + endC)
        print(cyan + "NeoChannelsComputation : " + endC + "radius_list : " + str(radius_list) + endC)
        print(cyan + "NeoChannelsComputation : " + endC + "channel_order : " + str(channel_order) + endC)
        print(cyan + "NeoChannelsComputation : " + endC + "bin_number : " + str(bin_number) + endC)
        print(cyan + "NeoChannelsComputation : " + endC + "indices_list : " + str(indices_to_compute_list) + endC)
        print(cyan + "NeoChannelsComputation : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "NeoChannelsComputation : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "NeoChannelsComputation : " + endC + "save_results_inter : " + str(save_results_intermediate) + endC)
        print(cyan + "NeoChannelsComputation : " + endC + "overwrite: " + str(overwrite) + endC)
        print(cyan + "NeoChannelsComputation : " + endC + "debug: " + str(debug) + endC)

    # EXECUTION DE LA FONCTION
    # Si le dossier contenant les neocanaux n'existe pas, on le crée
    if not os.path.isdir(repertory_neochannels_output):
        os.makedirs(repertory_neochannels_output)

    # execution de la fonction pour une image
    extractTexture(image_input, repertory_neochannels_output, path_time_log, channels_list, texture_families_list, radius_list, indices_to_compute_list, channel_order, extension_raster, save_results_intermediate, overwrite, bin_number)

# ================================================

if __name__ == '__main__':
  main(gui=False)
