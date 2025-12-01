#! /usr/bin/python
# -*- coding: utf-8 -*-

#############################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.               #
#############################################################################

#############################################################################
#                                                                           #
# FONCTIONS DE BASE SUR LES INDICES D'IMAGES                                #
#                                                                           #
#############################################################################
"""
 Ce module défini des fonctions de base de calcul des i,dices sur les images.
 Quelque soit la données capteurs (Spot5, spot6, Pleiades, Sentinel2,...
"""

# IMPORTS  DIVERS
import os,sys,glob,shutil,time
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC
from Lib_grass import convertRGBtoHIS

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 3 : affichage maximum de commentaires lors de l'execution du script. Intermédiaire : affichage intermédiaire

debug = 2
PRECISION = 0.0000001

# Source (OTb RadiometricIndices) : https://www.orfeo-toolbox.org/CookBook/Applications/app_RadiometricIndices.html

#########################################################################
# FONCTION createMNS()                                                  #
#########################################################################
def createMNS(image_input, image_mnt_input, image_elevation, image_mns_output, codage="float"):
    """
    #   Rôle : Cette fonction permet de créer un MNS à partir d'un MNT et d'une image d'élévation de zone
    #   paramètres :
    #       image_input : fichier image de référence
    #       image_mnt_input : fichier image MNT
    #       image_elevation : fichier image d'élévation à ajouter au MNT
    #       image_mns_output : fichier MNS de sortie
    #       codage : type de codage du fichier de sortie
    """

    # creer un fichier image temporaire
    name_file = os.path.splitext(image_mns_output)[0]
    extension_file = os.path.splitext(image_mns_output)[1]
    image_mnt_input_tmp = name_file + "_tmp" + extension_file

    # Recaler le fichier d'entrée a additionner sur l'image de référence
    command = "otbcli_Superimpose -inr %s -inm %s -out %s" %(image_input,image_mnt_input,image_mnt_input_tmp)
    if debug >= 2:
        print(command)
    exitCode = os.system(command)
    if exitCode != 0:
        print(command)
        raise NameError(bold + red + "createMNS() : An error occured during otbcli_Superimpose command. See error message above." + endC)

    # Creer l'expression
    expression = "\"(im1b1 + im2b1)\""

    # Bandmath pour ajouter les valeurs d'élévation au MNT
    command = "otbcli_BandMath -il %s %s -out %s %s -exp %s" %(image_mnt_input_tmp,image_elevation, image_mns_output,codage,expression)
    if debug >= 2:
        print(command)
    exitCode = os.system(command)
    if exitCode != 0:
        raise NameError(bold + red + "createMNS() : An error occured during otbcli_BandMath command. See error message above." + endC)

    # supprimer le fichier temporaire
    if os.path.isfile(image_mnt_input_tmp) :
        os.remove(image_mnt_input_tmp)

    print(cyan + "createMNS() : " + bold + green + "Create MNS file %s complete!" %(image_mns_output) + endC)

    return

#########################################################################
# FONCTION createNDVI()                                                 #
#########################################################################
def createNDVI(image_input, image_NDVI_output, channel_order, codage="float"):
    """
    #   Rôle : Cette fonction permet de créer un fichier NDVI (végétation) à partir d'une image ortho multi bande
    #   paramètres :
    #       image_input : fichier image d'entrée multi bandes
    #       image_NDVI_output : fichier NDVI de sortie une bande
    #       channel_order : liste d'ordre des bandes de l'image (exemple ["Red","Green","Blue","NIR"]
    #       codage : type de codage du fichier de sortie
    # Source : source : http://resources.arcgis.com/en/help/main/10.1/index.html#/Band_Arithmetic_function/009t000001z4000000/
    """

    # Variables
    Red = ""
    NIR = ""

    # Selection des bandes pour le calcul du NDVI
    if "Red" in channel_order:
        num_channel = channel_order.index("Red")+1
        Red = "im1b"+str(num_channel)
    if "NIR" in channel_order:
        num_channel = channel_order.index("NIR")+1
        NIR = "im1b"+str(num_channel)
    if (Red == "" or NIR == ""):
        raise NameError(cyan + "createNDVI() : " + bold + red + "NDVI needs Red and NIR channels to be computed"+ endC)

    # Creer l'expression
    expression = "\"(" + NIR + "==" + Red + ")?(" + Red + "== 0)?0:" + str(PRECISION) + ":" + "(" + NIR + "-" + Red + ")/(" + NIR + "+" + Red + "+" + str(PRECISION) + ")\""

    # Bandmath pour creer l'indice NDVI
    command = "otbcli_BandMath -il %s -out %s %s -exp %s" %(image_input, image_NDVI_output,codage,expression)
    if debug >= 2:
        print(command)
    exitCode = os.system(command)
    if exitCode != 0:
        print(command)
        raise NameError(bold + red + "createNDVI() : An error occured during otbcli_BandMath command. See error message above." + endC)

    print(cyan + "createNDVI() : " + bold + green + "Create NDVI file %s complete!" %(image_NDVI_output) + endC)

    return

#########################################################################
# FONCTION createNDVIMod                                                #
#########################################################################
def createNDVIMod(image_input, image_NDVIMod_output, channel_order, codage="float"):
    """
    #   Rôle : Cette fonction permet de calculer l'indice NDVIMod (végétation) sur une image ortho multi bande
    #   paramètres :
    #       image_input : fichier image d'entrée multi bandes
    #       image_NDVIMod_output : fichier NDVIMod de sortie (une bande)
    #       channel_order : liste d'ordre des bandes de l'image (exemple ["Red","Green","Blue","NIR"])
    #       codage : type de codage du fichier de sortie
    """

    # Variables
    Red = ""
    NIR = ""
    RedEdge = ""

    # Selection des bandes pour le calcul du NDVIMod
    if "Red" in channel_order:
        num_channel = channel_order.index("Red")+1
        Red = "im1b"+str(num_channel)
    if "NIR" in channel_order:
        num_channel = channel_order.index("NIR")+1
        NIR = "im1b"+str(num_channel)
    if "RE" in channel_order:
        num_channel = channel_order.index("RE")+1
        RedEdge = "im1b"+str(num_channel)
    if (Red == "" or NIR == "" or RedEdge == ""):
        raise NameError(cyan + "createNDVIMod() : " + bold + red + "NDVIMod needs Red, NIR and RE channels to be computed"+ endC)

    # Creer l'expression
    expression = "\"(" + NIR + "== 0) and (" + Red + "== 0) and (" + RedEdge  + "== 0)?0:(" + NIR + "-" + Red + "+" + RedEdge + ") == 0 and (" + NIR + "!= 0 or " + Red + "!= 0 or "+ RedEdge + "!= 0 )?" + str(PRECISION) + ":" + "(" + NIR + "-" + Red + "+" + RedEdge + ")/(" + NIR + "+" + Red + "+" + RedEdge + "+" + str(PRECISION) + ")\""

    # Bandmath pour creer l'indice NDVIMod
    command = "otbcli_BandMath -il %s -out %s %s -exp %s" %(image_input, image_NDVIMod_output,codage,expression)
    if debug >= 2:
        print(command)
    exitCode = os.system(command)
    if exitCode != 0:
        print(command)
        raise NameError(bold + red + "createNDVIMod() : An error occured during otbcli_BandMath command. See error message above." + endC)

    print(cyan + "createNDVIMod() : " + bold + green + "Create NDVIMod file %s complete!" %(image_NDVIMod_output) + endC)

    return

#########################################################################
# FONCTION createTNDVI()                                                #
#########################################################################
def createTNDVI(image_input, image_TNDVI_output, channel_order, codage="float"):
    """
    #   Rôle : Cette fonction permet de créer un fichier TNDVI (végétation) à partir d'une image ortho multi bande
    #   paramètres :
    #       image_input : fichier image d'entrée multi bandes
    #       image_TNDVI_output : fichier TNDVI de sortie une bande
    #       channel_order : liste d'ordre des bandes de l'image (exemple ["Red","Green","Blue","NIR"]
    #       codage : type de codage du fichier de sortie
    """

    # Variables
    Red = ""
    NIR = ""

    # Selection des bandes pour le calcul du TNDVI
    if "Red" in channel_order:
        num_channel = channel_order.index("Red")+1
        Red = "im1b"+str(num_channel)
    if "NIR" in channel_order:
        num_channel = channel_order.index("NIR")+1
        NIR = "im1b"+str(num_channel)
    if (Red == "" or NIR == ""):
        raise NameError(cyan + "createTNDVI() : " + bold + red + "TNDVI needs Red and NIR channels to be computed"+ endC)

    # Creer l'expression
    expression = "\"(" +  NIR + " == 0) and (" + Red + " == 0) ? 0 : " + "sqrt((" + NIR + "-" + Red + ")/(" + NIR + "+" + Red + "+" + str(PRECISION) + ")+0.5)\""

    # Bandmath pour creer l'indice TNDVI
    command = "otbcli_BandMath -il %s -out %s %s -exp %s" %(image_input, image_TNDVI_output,codage,expression)
    if debug >= 2:
        print(command)
    exitCode = os.system(command)
    if exitCode != 0:
        print(command)
        raise NameError(bold + red + "createTNDVI() : An error occured during otbcli_BandMath command. See error message above." + endC)

    print(cyan + "createTNDVI() : " + bold + green + "Create TNDVI file %s complete!" %(image_TNDVI_output) + endC)

    return

#########################################################################
# FONCTION createPNDVI()                                                #
#########################################################################
def createPNDVI(image_input, image_PNDVI_output, channel_order, codage="float"):
    """
    #   Rôle : Cette fonction permet de créer un fichier PNDVI (végétation) à partir d'une image ortho multi bande
    #   paramètres :
    #       image_input : fichier image d'entrée multi bandes
    #       image_PNDVI_output : fichier PNDVI de sortie (une bande)
    #       channel_order : liste d'ordre des bandes de l'image (exemple ["Red","Green","Blue","NIR"])
    #       codage : type de codage du fichier de sortie
    """

    # Variables
    NIR = ""
    Red = ""
    Green = ""
    Blue = ""

    # Selection des bandes pour le calcul du PNDVI
    if "NIR" in channel_order:
        num_channel = channel_order.index("NIR")+1
        NIR = "im1b"+str(num_channel)
    if "Red" in channel_order:
        num_channel = channel_order.index("Red")+1
        Red = "im1b"+str(num_channel)
    if "Green" in channel_order:
        num_channel = channel_order.index("Green")+1
        Green = "im1b"+str(num_channel)
    if "Blue" in channel_order:
        num_channel = channel_order.index("Blue")+1
        Blue = "im1b"+str(num_channel)
    if (NIR == "" or Red == "" or Green == "" or Blue == ""):
        raise NameError(cyan + "createPNDVI() : " + bold + red + "PNDVI needs NIR, Red, Green and Blue channels to be computed"+ endC)

    # Creer l'expression
    expression = "\"(" + NIR + "== 0) and (" + Green + "== 0) and (" + Red + "== 0) and (" + Blue  + "== 0)?0:(" + NIR + "-" + Green + "-" + Red + "-" + Blue + ") == 0 and (" + NIR + "!= 0 or " + Green + "!= 0 or "+ Red + "!= 0 or " + Blue + "!= 0 )?" + str(PRECISION) + ":" + "(" + NIR + "-" + Green + "-" + Red + "-" + Blue + ")/(" + NIR + "+" + Green + "+" + Red + "+" + Blue + "+" + str(PRECISION) + ")\""

    # Bandmath pour creer l'indice PNDVI
    command = "otbcli_BandMath -il %s -out %s %s -exp %s" %(image_input, image_PNDVI_output,codage,expression)
    if debug >= 2:
        print(command)
    exitCode = os.system(command)
    if exitCode != 0:
        print(command)
        raise NameError(bold + red + "createPNDVI() : An error occured during otbcli_BandMath command. See error message above." + endC)

    print(cyan + "createPNDVI() : " + bold + green + "Create PNDVI file %s complete!" %(image_PNDVI_output) + endC)

    return

#########################################################################
# FONCTION createNDWI()                                                 #
#########################################################################
def createNDWI(image_input, image_NDWI_output, channel_order, codage="float"):
    """
    #   Rôle : Cette fonction permet de créer un fichier NDWI (eau) à partir d'une image ortho multi bande
    #   paramètres :
    #       image_input : fichier image d'entrée multi bandes
    #       image_NDWI_output : fichier NDWI de sortie (une bande)
    #       channel_order : liste d'ordre des bandes de l'image (exemple ["Red","Green","Blue","NIR"])
    #       codage : type de codage du fichier de sortie
    # Source : https://hal.archives-ouvertes.fr/halshs-01070803/document
    """

    # Variables
    NIR = ""
    MIR = ""

    # Selection des bandes pour le calcul du NDWI
    if "NIR" in channel_order:
        num_channel = channel_order.index("NIR")+1
        NIR = "im1b"+str(num_channel)
    if "MIR" in channel_order:
        num_channel = channel_order.index("MIR")+1
        MIR = "im1b"+str(num_channel)
    if (NIR == "" or MIR == ""):
        raise NameError(cyan + "createNDWI() : " + bold + red + "NDWI needs NIR and MIR channels to be computed"+ endC)

    # Creer l'expression
    expression =  "\"(" + NIR + "==" + MIR + ")?(" + NIR + "== 0)?0:" + str(PRECISION) + ":" + "(" + NIR + "-" + MIR + ")/(" + NIR + "+" + MIR + "+" + str(PRECISION) + ")\""

    # Bandmath pour creer l'indice NDWI
    command = "otbcli_BandMath -il %s -out %s %s -exp %s" %(image_input, image_NDWI_output,codage,expression)
    if debug >= 2:
        print(command)
    exitCode = os.system(command)
    if exitCode != 0:
        print(command)
        raise NameError(bold + red + "createNDWI() : An error occured during otbcli_BandMath command. See error message above." + endC)

    print(cyan + "createNDWI() : " + bold + green + "Create NDWI file %s complete!" %(image_NDWI_output) + endC)

    return

#########################################################################
# FONCTION createNDWI2()                                                #
#########################################################################
def createNDWI2(image_input, image_NDWI2_output, channel_order, codage="float"):
    """
    #   Rôle : Cette fonction permet de créer un fichier NDWI2 (eau) à partir d'une image ortho multi bande
    #   paramètres :
    #       image_input : fichier image d'entrée multi bandes
    #       image_NDWI2_output : fichier NDWI2 de sortie (une bande)
    #       channel_order : liste d'ordre des bandes de l'image (exemple ["Red","Green","Blue","NIR"])
    #       codage : type de codage du fichier de sortie
    # Source : https://hal.archives-ouvertes.fr/halshs-01070803/document
    """

    # Variables
    Green = ""
    NIR = ""

    # Selection des bandes pour le calcul du NDWI2
    if "Green" in channel_order:
        num_channel = channel_order.index("Green")+1
        Green = "im1b"+str(num_channel)
    if "NIR" in channel_order:
        num_channel = channel_order.index("NIR")+1
        NIR = "im1b"+str(num_channel)
    if (Green == "" or NIR == ""):
        raise NameError(cyan + "createNDWI2() : " + bold + red + "NDWI2 needs Green and NIR channels to be computed"+ endC)

    # Creer l'expression
    expression = "\"(" + NIR + "==" + Green + ")?(" + NIR + "== 0)?0:" + str(PRECISION) + ":" + "(" + Green + "-" + NIR + ")/(" + Green + "+" + NIR + "+" + str(PRECISION) + ")\""

    # Bandmath pour creer l'indice NDWI2
    command = "otbcli_BandMath -il %s -out %s %s -exp %s" %(image_input, image_NDWI2_output,codage,expression)
    if debug >= 2:
        print(command)
    exitCode = os.system(command)
    if exitCode != 0:
        print(command)
        raise NameError(bold + red + "createNDWI2() : An error occured during otbcli_BandMath command. See error message above." + endC)

    print(cyan + "createNDWI2() : " + bold + green + "Create NDWI2 file %s complete!" %(image_NDWI2_output) + endC)

    return

#########################################################################
# FONCTION createNDWI2Mod()                                             #
#########################################################################
def createNDWI2Mod(image_input, image_NDWI2Mod_output, channel_order, codage="float"):
    """
    #   Rôle : Cette fonction permet de créer un fichier NDWI2Mod (eau) à partir d'une image ortho multi bande
    #   paramètres :
    #       image_input : fichier image d'entrée multi bandes
    #       image_NDWI2Mod_output : fichier NDWI2Mod de sortie (une bande)
    #       channel_order : liste d'ordre des bandes de l'image (exemple ["Red","Green","Blue","NIR"])
    #       codage : type de codage du fichier de sortie
    """

    # Variables
    Green = ""
    NIR = ""
    RedEdge = ""

    # Selection des bandes pour le calcul du NDWI2Mod
    if "Green" in channel_order:
        num_channel = channel_order.index("Green")+1
        Green = "im1b"+str(num_channel)
    if "NIR" in channel_order:
        num_channel = channel_order.index("NIR")+1
        NIR = "im1b"+str(num_channel)
    if "RE" in channel_order:
        num_channel = channel_order.index("RE")+1
        RedEdge = "im1b"+str(num_channel)
    if (Green == "" or NIR == "" or RedEdge == ""):
        raise NameError(cyan + "createNDWI2Mod() : " + bold + red + "NDWI2Mod needs Green, NIR and RE channels to be computed"+ endC)

    # Creer l'expression
    expression = "\"(" + NIR + "== 0) and (" + Green + "== 0) and (" + RedEdge + "== 0)?0:(" + Green + "-" + NIR + "+" + RedEdge + ") == 0 and (" + Green + "!= 0 or " + NIR + "!= 0 or "+ RedEdge + "!= 0)?" + str(PRECISION) + ":" + "(" + Green + "-" + NIR + "+" + RedEdge + ")/(" + Green + "+" + NIR +  "+" + RedEdge + "+" + str(PRECISION) + ")\""

    # Bandmath pour creer l'indice NDWI2Mod
    command = "otbcli_BandMath -il %s -out %s %s -exp %s" %(image_input, image_NDWI2Mod_output,codage,expression)
    if debug >= 2:
        print(command)
    exitCode = os.system(command)
    if exitCode != 0:
        print(command)
        raise NameError(bold + red + "createNDWI2Mod() : An error occured during otbcli_BandMath command. See error message above." + endC)

    print(cyan + "createNDWI2Mod() : " + bold + green + "Create NDWI2Mod file %s complete!" %(image_NDWI2Mod_output) + endC)

    return

#########################################################################
# FONCTION createMNDWI()                                                #
#########################################################################
def createMNDWI(image_input, image_MNDWI_output, channel_order, codage="float"):
    """
    #   Rôle : Cette fonction permet de créer un fichier MNDWI (eau) à partir d'une image ortho multi bande
    #   paramètres :
    #       image_input : fichier image d'entrée multi bandes
    #       image_MNDWI_output : fichier MNDWI de sortie (une bande)
    #       channel_order : liste d'ordre des bandes de l'image (exemple ["Red","Green","Blue","MIR"])
    #       codage : type de codage du fichier de sortie
    #   Source : https://www.sciencedirect.com/science/article/pii/S0303243419307573?ref=pdf_download&fr=RR-2&rr=7bef09124b03034c
    """

    # Variables
    Green = ""
    MIR_SWIR1 = ""

    # Selection des bandes pour le calcul du MNDWI
    if "Green" in channel_order:
        num_channel = channel_order.index("Green")+1
        Green = "im1b"+str(num_channel)
    if "MIR" in channel_order:
        num_channel = channel_order.index("MIR")+1
        MIR_SWIR1 = "im1b"+str(num_channel)
    if "SWIR1" in channel_order:
        num_channel = channel_order.index("SWIR1")+1
        MIR_SWIR1 = "im1b"+str(num_channel)
    if (Green == "" or MIR_SWIR1 == ""):
        raise NameError(cyan + "createMNDWI() : " + bold + red + "MNDWI needs Green and MIR or (SWIR1 from Sentinel2) channels to be computed"+ endC)

    # Creer l'expression
    expression = "\"(" + MIR_SWIR1 + "==" + Green + ")?(" + MIR_SWIR1 + "== 0)?0:" + str(PRECISION) + ":" + "(" + Green + "-" + MIR_SWIR1 + ")/(" + Green + "+" + MIR_SWIR1 + "+" + str(PRECISION) + ")\""

    # Bandmath pour creer l'indice MNDWI
    command = "otbcli_BandMath -il %s -out %s %s -exp %s" %(image_input, image_MNDWI_output,codage,expression)
    if debug >= 2:
        print(command)
    exitCode = os.system(command)
    if exitCode != 0:
        print(command)
        raise NameError(bold + red + "createMNDWI() : An error occured during otbcli_BandMath command. See error message above." + endC)

    print(cyan + "createMNDWI() : " + bold + green + "Create MNDWI file %s complete!" %(image_MNDWI_output) + endC)

    return

#########################################################################
# FONCTION createNDMI()                                                 #
#########################################################################
def createNDMI(image_input, image_NDMI_output, channel_order, codage="float"):
    """
    #   Rôle : Cette fonction permet de créer un fichier NDMI à partir d'une image ortho multi bande
    #          L'indice d'humidité par différence normalisé (NDMI) est sensible aux niveaux d'humidité dans la végétation.
    #   paramètres :
    #       image_input : fichier image d'entrée multi bandes
    #       image_NDMI_output : fichier NDMI de sortie (une bande)
    #       channel_order : liste d'ordre des bandes de l'image (exemple ["Red","Green","Blue","NIR","SWIR1"])
    #       codage : type de codage du fichier de sortie
    # Source : https://pro.arcgis.com/fr/pro-app/latest/help/data/imagery/indices-gallery.htm#:~:text=NDMI,les%20zones%20sujettes%20aux%20incendies.
    """

    # Variables
    NIR = ""
    SWIR1 = ""

    # Selection des bandes pour le calcul du NDMI
    if "NIR" in channel_order:
        num_channel = channel_order.index("NIR")+1
        NIR = "im1b"+str(num_channel)
    if "SWIR1" in channel_order:
        num_channel = channel_order.index("SWIR1")+1
        SWIR1 = "im1b"+str(num_channel)
    if (NIR == "" or SWIR1 == ""):
        raise NameError(cyan + "createNDMI() : " + bold + red + "NDMI needs NIR and SWIR1 channels to be computed"+ endC)

    # Creer l'expression
    expression = "\"(" + SWIR1 + "==" + NIR + ")?(" + SWIR1 + "== 0)?0:" + str(PRECISION) + ":" + "(" + NIR + "-" + SWIR1 + ")/(" + NIR + "+" + SWIR1 + "+" + str(PRECISION) + ")\""

    # Bandmath pour creer l'indice NDMI
    command = "otbcli_BandMath -il %s -out %s %s -exp %s" %(image_input, image_NDMI_output,codage,expression)
    if debug >= 2:
        print(command)
    exitCode = os.system(command)
    if exitCode != 0:
        print(command)
        raise NameError(bold + red + "createNDMI() : An error occured during otbcli_BandMath command. See error message above." + endC)

    print(cyan + "createNDMI() : " + bold + green + "Create NDMI file %s complete!" %(image_NDMI_output) + endC)

    return

#########################################################################
# FONCTION createISU()                                                  #
#########################################################################
def createISU(image_input, image_ISU_output, channel_order, codage="float"):
    """
    #   Rôle : Cette fonction permet de créer un fichier ISU (bâti) à partir d'une image ortho multi bande
    #   paramètres :
    #       image_input : fichier image d'entrée multi bandes
    #       image_ISU_output : fichier ISU de sortie une bande
    #       channel_order : liste d'ordre des bandes de l'image (exemple ["Red","Green","Blue","NIR"]
    #       codage : type de codage du fichier de sortieMIR
    """

    # Variables
    Red = ""
    NIR = ""

    # Selection des bandes pour le calcul du ISU
    if "Red" in channel_order:
        num_channel = channel_order.index("Red")+1
        Red = "im1b"+str(num_channel)
    if "NIR" in channel_order:
        num_channel = channel_order.index("NIR")+1
        NIR = "im1b"+str(num_channel)
    if (Red == "" or NIR == ""):
        raise NameError(cyan + "createISU() : " + bold + red + "ISU needs Red and NIR channels to be computed"+ endC)

    # Creer l'expression
    expression = "\"" + Red + " == 0 ? 0 : " + "75*(" + Red + "/" + NIR + "+" + str(PRECISION) + ")\""

    # Bandmath pour creer l'indice ISU
    command = "otbcli_BandMath -il %s -out %s %s -exp %s" %(image_input, image_ISU_output,codage,expression)
    if debug >= 2:
        print(command)
    exitCode = os.system(command)
    if exitCode != 0:
        print(command)
        raise NameError(bold + red + "createISU() : An error occured during otbcli_BandMath command. See error message above." + endC)

    print(cyan + "createISU() : " + bold + green + "Create ISU file %s complete!" %(image_ISU_output) + endC)

    return

#########################################################################
# FONCTION createGEMI()                                                 #
#########################################################################
def createGEMI(image_input, image_GEMI_output, channel_order, codage="float"):
    """
    #   Rôle : Cette fonction permet de calculer le fichier GEMI (Végétation) sur une image ortho multi bande
    #   paramètres :
    #       image_input : fichier image d'entrée multi bandes
    #       image_GEMI_output : fichier GEMI de sortie (une bande)
    #       channel_order : liste d'ordre des bandes de l'image (exemple ["Red","Green","Blue","NIR"])
    #       codage : type de codage du fichier de sortie
    # Source : http://resources.arcgis.com/en/help/main/10.1/index.html#/Band_Arithmetic_function/009t000001z4000000/
    """

    # Variables
    Red = ""
    NIR = ""

    # Selection des bandes pour le calcul du GEMI
    if "Red" in channel_order:
        num_channel = channel_order.index("Red")+1
        Red = "im1b"+str(num_channel)
    if "NIR" in channel_order:
        num_channel = channel_order.index("NIR")+1
        NIR = "im1b"+str(num_channel)
    if (Red == "" or NIR == ""):
        raise NameError(cyan + "createGEMI() : " + bold + red + "GEMI needs Red and NIR channels to be computed"+ endC)

    # Creer l'expression
    # source : http://resources.arcgis.com/en/help/main/10.1/index.html#/Band_Arithmetic_function/009t000001z4000000/
    eta = "(2*((" + NIR + "*" + NIR + ")-(" + Red + "*" + Red + ")) + 1.5 *" + NIR + " + 0.5 *" + Red + ")/(" + NIR + "+" + Red + " + 0.5)"
    expression = "\"(" + NIR + " == 0) and (" + Red + " == 0) ? 0 : " + eta + "*(1-  0.25 *" + eta + ")-((" + Red + " - 0.125)/(1-" + Red + "))\""

    # Bandmath pour creer l'indice GEMI
    command = "otbcli_BandMath -il %s -out %s %s -exp %s" %(image_input, image_GEMI_output,codage,expression)
    if debug >= 2:
        print(command)
    exitCode = os.system(command)
    if exitCode != 0:
        print(command)
        raise NameError(bold + red + "createGEMI() : An error occured during otbcli_BandMath command. See error message above." + endC)

    print(cyan + "createGEMI() : " + bold + green + "Create GEMI file %s complete!" %(image_GEMI_output) + endC)

    return

#########################################################################
# FONCTION createBSI()                                                  #
#########################################################################
def createBSI(image_input, image_BSI_output, channel_order, codage="float"):
    """
    #   Rôle : Cette fonction permet de calculer le fichier BSI (Végétation) sur une image ortho multi bande
    #   paramètres :
    #       image_input : fichier image d'entrée multi bandes
    #       image_BSI_output : fichier BSI de sortie (une bande)
    #       channel_order : liste d'ordre des bandes de l'image (exemple ["Red","Green","Blue","NIR"])
    #       codage : type de codage du fichier de sortie
    """

    # Variables
    Blue = ""
    Red = ""
    NIR = ""
    SWIR1 = ""

    # Selection des bandes pour le calcul du BSI
    if "Blue" in channel_order:
        num_channel = channel_order.index("Blue")+1
        Blue = "im1b"+str(num_channel)
    if "Red" in channel_order:
        num_channel = channel_order.index("Red")+1
        Red = "im1b"+str(num_channel)
    if "NIR" in channel_order:
        num_channel = channel_order.index("NIR")+1
        NIR = "im1b"+str(num_channel)
    if "SWIR1" in channel_order:
        num_channel = channel_order.index("SWIR1")+1
        SWIR1 = "im1b"+str(num_channel)
    if (Blue == "" or Red == "" or NIR == "" or SWIR1 == ""):
        raise NameError(cyan + "createBSI() : " + bold + red + "BSI needs Blue, Red NIR and SWIR1 channels to be computed"+ endC)

    # Creer l'expression
    expression = "\"(" + Red + " == 0) and (" + Blue + " == 0) and (" + NIR + " == 0) and (" + SWIR1 + " == 0) ? 0 : " + "((" + SWIR1 + " + " + Red + ") - (" + NIR + " + " + Blue + "))/((" + SWIR1 + " + " + Red + ") + (" + NIR + " + " + Blue + ") +" + str(PRECISION) + ")\""

    # Bandmath pour creer l'indice BSI
    command = "otbcli_BandMath -il %s -out %s %s -exp %s" %(image_input, image_BSI_output,codage,expression)
    if debug >= 2:
        print(command)
    exitCode = os.system(command)
    if exitCode != 0:
        print(command)
        raise NameError(bold + red + "createBSI() : An error occured during otbcli_BandMath command. See error message above." + endC)

    print(cyan + "createBSI() : " + bold + green + "Create BSI file %s complete!" %(image_BSI_output) + endC)

    return

#########################################################################
# FONCTION createNDBI()                                                 #
#########################################################################
def createNDBI(image_input, image_NDBI_output, channel_order, codage="float"):
    """
    #   Rôle : Cette fonction permet de calculer le fichier NDBI (Bâti) sur une image ortho multi bande
    #   paramètres :
    #       image_input : fichier image d'entrée multi bandes
    #       image_NDBI_output : fichier NDBI de sortie (une bande)
    #       channel_order : liste d'ordre des bandes de l'image (exemple ["Red","Green","Blue","NIR"])
    #       codage : type de codage du fichier de sortie
    """

    # Variables
    MIR = ""
    NIR = ""

    # Selection des bandes pour le calcul du NDBI
    if "MIR" in channel_order:
        num_channel = channel_order.index("MIR")+1
        MIR = "im1b"+str(num_channel)
    if "NIR" in channel_order:
        num_channel = channel_order.index("NIR")+1
        NIR = "im1b"+str(num_channel)
    if (MIR == "" or NIR == ""):
        raise NameError(cyan + "createNDBI() : " + bold + red + "NDBI needs MIR and NIR channels to be computed"+ endC)

    # Creer l'expression
    expression = "\"(" + MIR + "==" + NIR + ")?(" + MIR + "== 0)?0:" + str(PRECISION) + ":" + "(" + MIR + "-" + NIR + ")/(" + MIR + "+" + NIR + "+" + str(PRECISION) + ")\""

    # Bandmath pour creer l'indice NDBI
    command = "otbcli_BandMath -il %s -out %s %s -exp %s" %(image_input, image_NDBI_output,codage,expression)
    if debug >= 2:
        print(command)
    exitCode = os.system(command)
    if exitCode != 0:
        print(command)
        raise NameError(bold + red + "createNDBI() : An error occured during otbcli_BandMath command. See error message above." + endC)

    print(cyan + "createNDBI() : " + bold + green + "Create NDBI file %s complete!" %(image_NDBI_output) + endC)

    return

#########################################################################
# FONCTION createNBI()                                                  #
#########################################################################
def createNBI(image_input, image_NBI_output, channel_order, codage="float"):
    """
    #   Rôle : Cette fonction permet de calculer le fichier NBI (Bâti) sur une image ortho multi bande
    #   paramètres :
    #       image_input : fichier image d'entrée multi bandes
    #       image_NBI_output : fichier NBI de sortie (une bande)
    #       channel_order : liste d'ordre des bandes de l'image (exemple ["Red","Green","Blue","NIR"])
    #       codage : type de codage du fichier de sortie
    """

    # Variables
    Red = ""
    MIR = ""
    NIR = ""

    # Selection des bandes pour le calcul du NBI
    if "Red" in channel_order:
        num_channel = channel_order.index("Red")+1
        Red = "im1b"+str(num_channel)
    if "MIR" in channel_order:
        num_channel = channel_order.index("MIR")+1
        MIR = "im1b"+str(num_channel)
    if "NIR" in channel_order:
        num_channel = channel_order.index("NIR")+1
        NIR = "im1b"+str(num_channel)
    if (Red =="" or MIR == "" or NIR == ""):
        raise NameError(cyan + "createNBI() : " + bold + red + "NBI needs Red, MIR and NIR channels to be computed"+ endC)

    # Creer l'expression
    expression =  "\"(" + MIR + "== 0) and (" + NIR + "== 0) and (" + Red + "== 0)?0:(" + Red + "!=" + MIR + " and (" + Red + "== 0 or " + MIR + "== 0))?" + str(PRECISION) + ":" + "(" + Red + "*" + MIR + ")/(" + NIR + "+" + str(PRECISION) + ")\""

    # Bandmath pour creer l'indice NBI
    command = "otbcli_BandMath -il %s -out %s %s -exp %s" %(image_input, image_NBI_output,codage,expression)
    if debug >= 2:
        print(command)
    exitCode = os.system(command)
    if exitCode != 0:
        print(command)
        raise NameError(bold + red + "createNBI() : An error occured during otbcli_BandMath command. See error message above." + endC)

    print(cyan + "createNBI() : " + bold + green + "Create NDBI file %s complete!" %(image_NBI_output) + endC)

    return

#########################################################################
# FONCTION createIR()                                                   #
#########################################################################
def createIR(image_input, image_IR_output, channel_order, codage="float"):
    """
    #   Rôle : Cette fonction permet de créer un fichier IR (sol) à partir d'une image ortho multi bande
    #   paramètres :
    #       image_input : fichier image d'entrée multi bandes
    #       image_IR_output : fichier IR de sortie (une bande)
    #       channel_order : liste d'ordre des bandes de l'image (exemple ["Red","Green","Blue","NIR"])
    #       codage : type de codage du fichier de sortie
    """

    # Variables
    Red = ""
    Green = ""
    Blue = ""

    # Selection des bandes pour le calcul du IR
    if "Red" in channel_order:
        num_channel = channel_order.index("Red")+1
        Red = "im1b"+str(num_channel)
    if "Green" in channel_order:
        num_channel = channel_order.index("Green")+1
        Green = "im1b"+str(num_channel)
    if "Blue" in channel_order:
        num_channel = channel_order.index("Blue")+1
        Blue = "im1b"+str(num_channel)
    if (Red == "" or Green == "" or Blue == ""):
        raise NameError(cyan + "createIR() : " + bold + red + "IR needs Red, Green and Blue channels to be computed"+ endC)

    # Creer l'expression
    expression =  "\"(" + Green + "== 0) and (" + Blue + "== 0) and (" + Red + "== 0)?0:(" + Red + " == 0)?" + str(PRECISION) + ":" + "(" + Red + "*" + Red + ")/(" + str(PRECISION) + " + (" + Blue + "+" + Green + "*" + Green + "*" + Green + "))\""

    # Bandmath pour creer l'indice IR
    command = "otbcli_BandMath -il %s -out %s %s -exp %s" %(image_input, image_IR_output,codage,expression)
    if debug >= 2:
        print(command)
    exitCode = os.system(command)
    if exitCode != 0:
        print(command)
        raise NameError(bold + red + "createIR() : An error occured during otbcli_BandMath command. See error message above." + endC)

    print(cyan + "createIR() : " + bold + green + "Create IR file %s complete!" %(image_IR_output) + endC)

    return

#########################################################################
# FONCTION createCI()                                                   #
#########################################################################
def createCI(image_input, image_CI_output, channel_order, codage="float"):
    """
    #   Rôle : Cette fonction permet de créer un fichier CI (sol) à partir d'une image ortho multi bande
    #   paramètres :
    #       image_input : fichier image d'entrée multi bandes
    #       image_CI_output : fichier CI de sortie (une bande)
    #       channel_order : liste d'ordre des bandes de l'image (exemple ["Red","Green","Blue","NIR"])
    #       codage : type de codage du fichier de sortie
    """

    # Variables
    Red = ""
    Green = ""

    # Selection des bandes pour le calcul du CI
    if "Red" in channel_order:
        num_channel = channel_order.index("Red")+1
        Red = "im1b"+str(num_channel)
    if "Green" in channel_order:
        num_channel = channel_order.index("Green")+1
        Green = "im1b"+str(num_channel)
    if (Red == "" or Green == ""):
        raise NameError(cyan + "createCI() : " + bold + red + "CI needs Red and Green channels to be computed"+ endC)

    # Creer l'expression
    expression = "\"(" + Red + "==" + Green + ")?(" + Red + "== 0)?0:" + str(PRECISION) + ":" + "(" + Red + "-" + Green + ")/(" + Red + "+" + Green + "+" + str(PRECISION) + ")\""

    # Bandmath pour creer l'indice CI
    command = "otbcli_BandMath -il %s -out %s %s -exp %s" %(image_input, image_CI_output,codage,expression)
    if debug >= 2:
        print(command)
    exitCode = os.system(command)
    if exitCode != 0:
        print(command)
        raise NameError(bold + red + "createCI() : An error occured during otbcli_BandMath command. See error message above." + endC)

    print(cyan + "createCI() : " + bold + green + "Create CI file %s complete!" %(image_CI_output) + endC)

    return

#########################################################################
# FONCTION createBI()                                                   #
#########################################################################
def createBI(image_input, image_BI_output, channel_order, codage="float"):
    """
    #   Rôle : Cette fonction permet de calculer l'indice de brillance (BI) sur une image ortho multi bande
    #   paramètres :
    #       image_input : fichier image d'entrée multi bandes
    #       image_BI_output : fichier BI de sortie (une bande)
    #       channel_order : liste d'ordre des bandes de l'image (exemple ["Red","Green","Blue","NIR"])
    #       codage : type de codage du fichier de sortie
    # Source : univ-montp3.fr/ateliermercator/wp-content/uploads/2010/03/TRANSFO_IMAGES.pdf (page 2)
    #          https://georezo.net/forum/viewtopic.php?id=59936
    """

    # Variables
    Red = ""
    NIR = ""

    # Selection des bandes pour le calcul du BI
    if "Red" in channel_order:
        num_channel = channel_order.index("Red")+1
        Red = "im1b"+str(num_channel)
    if "NIR" in channel_order:
        num_channel = channel_order.index("NIR")+1
        NIR = "im1b"+str(num_channel)
    if (Red == "" or NIR == ""):
        raise NameError(cyan + "createBI() : " + bold + red + "BI needs Red and NIR channels to be computed"+ endC)

    # Creer l'expression
    expression = "\"" + "sqrt(("+NIR+"*"+NIR+")+("+Red+"*"+Red+"))\""

    # Bandmath pour creer l'indice BI
    command = "otbcli_BandMath -il %s -out %s %s -exp %s" %(image_input, image_BI_output,codage,expression)
    if debug >= 2:
        print(command)
    exitCode = os.system(command)
    if exitCode != 0:
        print(command)
        raise NameError(bold + red + "createBI() : An error occured during otbcli_BandMath command. See error message above." + endC)

    print(cyan + "createBI() : " + bold + green + "Create BI file %s complete!" %(image_BI_output) + endC)

    return

#########################################################################
# FONCTION createBI2()                                                  #
#########################################################################
def createBI2(image_input, image_BI2_output, channel_order, codage="float"):
    """
    #   Rôle : Cette fonction permet de calculer l'indice de brillance (BI2) sur une image ortho multi bande
    #   paramètres :
    #       image_input : fichier image d'entrée multi bandes
    #       image_BI2_output : fichier BI2 de sortie (une bande)
    #       channel_order : liste d'ordre des bandes de l'image (exemple ["Red","Green","Blue","NIR"])
    #       codage : type de codage du fichier de sortie
    # Source : https://hal.inrae.fr/hal-02602061/document (page 14)
    """

    # Variables
    Red = ""
    Green = ""
    NIR = ""

    # Selection des bandes pour le calcul du BI2
    if "Red" in channel_order:
        num_channel = channel_order.index("Red")+1
        Red = "im1b"+str(num_channel)
    if "Green" in channel_order:
        num_channel = channel_order.index("Green")+1
        Green = "im1b"+str(num_channel)
    if "NIR" in channel_order:
        num_channel = channel_order.index("NIR")+1
        NIR = "im1b"+str(num_channel)
    if (Red == "" or Green == "" or NIR == ""):
        raise NameError(cyan + "createBI2() : " + bold + red + "BI2 needs Red, Green and NIR channels to be computed"+ endC)

    # Creer l'expression
    expression = "\"" + "sqrt((("+NIR+"*"+NIR+")+("+Red+"*"+Red+")+("+Green+"*"+Green+"))/3)\""

    # Bandmath pour creer l'indice BI2
    command = "otbcli_BandMath -il %s -out %s %s -exp %s" %(image_input, image_BI2_output,codage,expression)
    if debug >= 2:
        print(command)
    exitCode = os.system(command)
    if exitCode != 0:
        print(command)
        raise NameError(bold + red + "createBI2() : An error occured during otbcli_BandMath command. See error message above." + endC)

    print(cyan + "createBI2() : " + bold + green + "Create BI2 file %s complete!" %(image_BI2_output) + endC)

    return

#########################################################################
# FONCTION createC3()                                                   #
#########################################################################
def createC3(image_input, image_c3_output, channel_order, codage="float"):
    """
    #   Rôle : Cette fonction permet de créer un fichier d'indice c3 (detection des ombres) à partir d'une image ortho RVB
    #   paramètres :
    #       image_input : fichier image d'entrée multi bandes
    #       image_c3_output : fichier C3 (Ombre) de sortie une bande
    #       channel_order : liste d'ordre des bandes de l'image (exemple ["Red","Green","Blue","NIR"]
    #       codage : type de codage du fichier de sortie
    # Source : source : https://tel.archives-ouvertes.fr/tel-01332681
    #       Shadow/Vegetation and building detection from single optical remote sensing image "Tran Thanh Ngo"
    """

    # Variables
    Red = ""
    Green = ""
    Blue = ""

    # Selection des bandes pour le calcul du C3
    if "Red" in channel_order:
        num_channel = channel_order.index("Red")+1
        Red = "im1b"+str(num_channel)
    if "Green" in channel_order:
        num_channel = channel_order.index("Green")+1
        Green = "im1b"+str(num_channel)
    if "Blue" in channel_order:
        num_channel = channel_order.index("Blue")+1
        Blue = "im1b"+str(num_channel)
    if (Red == "" or Green == "" or Blue == ""):
        raise NameError(cyan + "createC3() : " + bold + red + "c3 needs Red Green and Blue channels to be computed"+ endC)

    # Creer l'expression
    expression = "\"(" + Blue + "== 0)?0:" + "atan(" + Blue + "/(max(" + Red + "," + Green + ")+" + str(PRECISION) + "))\""

    # Bandmath pour creer l'indice C3
    command = "otbcli_BandMath -il %s -out %s %s -exp %s" %(image_input, image_c3_output,codage,expression)
    if debug >= 2:
        print(command)
    exitCode = os.system(command)
    if exitCode != 0:
        print(command)
        raise NameError(bold + red + "createC3() : An error occured during otbcli_BandMath command. See error message above." + endC)

    print(cyan + "createC3() : " + bold + green + "Create c3 file %s complete!" %(image_c3_output) + endC)

    return

#########################################################################
# FONCTION createExG()                                                  #
#########################################################################
def createExG(image_input, image_ExG_output, channel_order, codage="float"):
    """
    #   Rôle : Cette fonction permet de créer un fichier d'indice ExG (detection de la végétation) à partir d'une image ortho RVB
    #   paramètres :
    #       image_input : fichier image d'entrée multi bandes
    #       image_ExG_output : fichier ExG (vegetation) de sortie une bande
    #       channel_order : liste d'ordre des bandes de l'image (exemple ["Red","Green","Blue","NIR"]
    #       codage : type de codage du fichier de sortie
    # Source : source : https://tel.archives-ouvertes.fr/tel-01332681
    #       Shadow/Vegetation and building detection from single optical remote sensing image "Tran Thanh Ngo"
    """

    # Variables
    Red = ""
    Green = ""
    Blue = ""

    # Selection des bandes pour le calcul du ExG
    if "Red" in channel_order:
        num_channel = channel_order.index("Red")+1
        Red = "im1b"+str(num_channel)
    if "Green" in channel_order:
        num_channel = channel_order.index("Green")+1
        Green = "im1b"+str(num_channel)
    if "Blue" in channel_order:
        num_channel = channel_order.index("Blue")+1
        Blue = "im1b"+str(num_channel)
    if (Red == "" or Green == "" or Blue == ""):
        raise NameError(cyan + "createExG() : " + bold + red + "ExG needs Red Green and Blue channels to be computed"+ endC)

    # Creer l'expression
    expression = "\"((" + Green + "-" + Red + "-" + Blue + ")==0)?0:" + "(2*(" + Green + "-" + Red + "-" + Blue + ")/(" + Red + "+" + Green + "+" + Blue + "+" + str(PRECISION) + "))\""

    # Bandmath pour creer l'indice ExG
    command = "otbcli_BandMath -il %s -out %s %s -exp %s" %(image_input, image_ExG_output,codage,expression)
    if debug >= 2:
        print(command)
    exitCode = os.system(command)
    if exitCode != 0:
        print(command)
        raise NameError(bold + red + "createExG() : An error occured during otbcli_BandMath command. See error message above." + endC)

    print(cyan + "createExG() : " + bold + green + "Create ExG file %s complete!" %(image_ExG_output) + endC)

    return

#########################################################################
# FONCTION createL()                                                    #
#########################################################################
def createL(image_input, image_L_output, channel_order, codage="float"):
    """
    #   Rôle : Cette fonction permet de créer un fichier d'indice L (detection de la luminance) à partir d'une image ortho RVB
    #   paramètres :
    #       image_input : fichier image d'entrée multi bandes
    #       image_L_output : fichier L (Luminance) de sortie une bande
    #       channel_order : liste d'ordre des bandes de l'image (exemple ["Red","Green","Blue","NIR"]
    #       codage : type de codage du fichier de sortie
    # Source : source : https://tel.archives-ouvertes.fr/tel-01332681
    #       Shadow/Vegetation and building detection from single optical remote sensing image "Tran Thanh Ngo"
    """

    # Variables
    Red = ""
    Green = ""
    Blue = ""

    # Selection des bandes pour le calcul du L
    if "Red" in channel_order:
        num_channel = channel_order.index("Red")+1
        Red = "im1b"+str(num_channel)
    if "Green" in channel_order:
        num_channel = channel_order.index("Green")+1
        Green = "im1b"+str(num_channel)
    if "Blue" in channel_order:
        num_channel = channel_order.index("Blue")+1
        Blue = "im1b"+str(num_channel)
    if (Red == "" or Green == "" or Blue == ""):
        raise NameError(cyan + "createL() : " + bold + red + "L needs Red Green and Blue channels to be computed"+ endC)

    # Creer l'expression
    expression =  "\"((" + Red + "== 0) and (" + Green + "== 0) and (" + Blue + "== 0))?0:(" + Red + "+" + Green + "+" + Blue + ")/3\""

    # Bandmath pour creer l'indice L
    command = "otbcli_BandMath -il %s -out %s %s -exp %s" %(image_input, image_L_output,codage,expression)
    if debug >= 2:
        print(command)
    exitCode = os.system(command)
    if exitCode != 0:
        print(command)
        raise NameError(bold + red + "createL() : An error occured during otbcli_BandMath command. See error message above." + endC)

    print(cyan + "createL() : " + bold + green + "Create L file %s complete!" %(image_L_output) + endC)

    return

#########################################################################
# FONCTION createMSAVI2()                                               #
#########################################################################
def createMSAVI2(image_input, image_MSAVI2_output, channel_order, codage="float"):
    """
    #   Rôle : Cette fonction permet de créer un fichier MSAVI2 (végétation) à partir d'une image ortho multi bande
    #   paramètres :
    #       image_input : fichier image d'entrée multi bandes
    #       image_MSAVI2_output : fichier MSAVI de sortie une bande
    #       channel_order : liste d'ordre des bandes de l'image (exemple ["Red","Green","Blue","NIR"]
    #       codage : type de codage du fichier de sortie
    # Source : source : http://resources.arcgis.com/en/help/main/10.1/index.html#/Band_Arithmetic_function/009t000001z4000000/
    """

    # Variables
    Red = ""
    NIR = ""

    # Selection des bandes pour le calcul du MSAVI2
    if "Red" in channel_order:
        num_channel = channel_order.index("Red")+1
        Red = "im1b"+str(num_channel)
    if "NIR" in channel_order:
        num_channel = channel_order.index("NIR")+1
        NIR = "im1b"+str(num_channel)
    if (Red == "" or NIR == ""):
        raise NameError(cyan + "createMSAVI2() : " + bold + red + "MSAVI2 needs Red and NIR channels to be computed"+ endC)

    # Creer l'expression
    expression = "\"("+ NIR + " == " + Red + ")and(" + NIR + " == 0)?" + str(PRECISION) +" : (2 * " + NIR + " + 1 - sqrt(( 2 * " + NIR + " + 1 )^2 - 8 *(" + NIR + " - " + Red +"))+" +  str(PRECISION)+")/2 \""


    # Bandmath pour creer l'indice MSAVI2
    command = "otbcli_BandMath -il %s -out %s %s -exp %s" %(image_input, image_MSAVI2_output,codage,expression)
    if debug >= 2:
        print(command)
    exitCode = os.system(command)
    if exitCode != 0:
        print(command)
        raise NameError(bold + red + "createMSAVI2() : An error occured during otbcli_BandMath command. See error message above." + endC)

    print(cyan + "createMSAVI2() : " + bold + green + "Create MSAVI2 file %s complete!" %(image_MSAVI2_output) + endC)

    return

#########################################################################
# FONCTION createSIPI()                                                 #
#########################################################################
def createSIPI(image_input, image_SIPI_output, channel_order, codage="float"):
    """
    #   Rôle : Cette fonction permet de créer un fichier SIPI (végétation) à partir d'une image ortho multi bande
    #   paramètres :
    #       image_input : fichier image d'entrée multi bandes
    #       image_SIPI_output : fichier SIPI de sortie une bande
    #       channel_order : liste d'ordre des bandes de l'image (exemple ["Red","Green","Blue","NIR"])
    #       codage : type de codage du fichier de sortie
    # Source : source : http://resources.arcgis.com/en/help/main/10.1/index.html#/Band_Arithmetic_function/009t000001z4000000/
    """

    # Variables
    Red = ""
    Blue = ""
    NIR = ""

    # Selection des bandes pour le calcul de SIPI
    if "Red" in channel_order:
        num_channel = channel_order.index("Red")+1
        Red = "im1b"+str(num_channel)
    if "Blue" in channel_order:
        num_channel = channel_order.index("Blue")+1
        Blue = "im1b"+str(num_channel)
    if "NIR" in channel_order:
        num_channel = channel_order.index("NIR")+1
        NIR = "im1b"+str(num_channel)
    if (Red == "" or NIR == ""):
        raise NameError(cyan + "createSIPI() : " + bold + red + "SIPI needs Red, Blue and NIR channels to be computed"+ endC)

    # Creer l'expression
    expression = "\"("+ NIR + " == " + Red + ") or ("+ NIR + " == " + Blue + ")and(" + NIR + " == 0)?" + str(PRECISION) +":" + "(" + NIR + "-" + Blue + ")/(" + NIR + "-" + Red + "+" + str(PRECISION) + ")\""

    # Bandmath pour creer l'indice SIPI
    command = "otbcli_BandMath -il %s -out %s %s -exp %s" %(image_input, image_SIPI_output,codage,expression)
    if debug >= 2:
        print(command)
    exitCode = os.system(command)
    if exitCode != 0:
        print(command)
        raise NameError(bold + red + "createSIPI() : An error occured during otbcli_BandMath command. See error message above." + endC)

    print(cyan + "createSIPI() : " + bold + green + "Create SIPI file %s complete!" %(image_SIPI_output) + endC)

    return

#########################################################################
# FONCTION createISI()                                                  #
#########################################################################
def createISI(image_input, image_ISI_output, channel_order, codage="float"):
    """
    #   Rôle : Cette fonction permet de créer un fichier ISI (ombre) à partir d'une image ortho multi bande
    #   paramètres :
    #       image_input : fichier image d'entrée multi bandes
    #       image_ISI_output : fichier ISI de sortie une bande
    #       channel_order : liste d'ordre des bandes de l'image (exemple ["Red","Green","Blue","NIR"]
    #       codage : type de codage du fichier de sortie
    # Source : source : http://resources.arcgis.com/en/help/main/10.1/index.html#/Band_Arithmetic_function/009t000001z4000000/
    """

    cont = 0
    # Variables
    Red = ""
    Green = ""
    Blue = ""
    NIR = ""

    # Selection des bandes pour le calcul de ISI
    if "Red" in channel_order:
        num_channel = channel_order.index("Red")+1
        Red = "im1b"+str(num_channel)
    if "Green" in channel_order:
        num_channel = channel_order.index("Green")+1
        Green = "im1b"+str(num_channel)
    if "Blue" in channel_order:
        num_channel = channel_order.index("Blue")+1
        Blue = "im1b"+str(num_channel)
    if "NIR" in channel_order:
        num_channel = channel_order.index("NIR")+1
        NIR = "im1b"+str(num_channel)
    if (Red == "" or Green == "" or Blue == "" or NIR == ""):
        raise NameError(cyan + "createISI() : " + bold + red + "ISI needs Red and Green and Blue and NIR channels to be computed"+ endC)

    # Repository qui sera a supprimer
    repository = os.path.dirname(image_ISI_output)
    filename = os.path.splitext(os.path.basename(image_input))[0]

    # Creer les images Rouge, Vert, Bleu
    fp_red = repository + os.sepp + filename + "_R.tif"
    fp_green =  repository + os.sep + filename + "_V.tif"
    fp_blue = repository + os.sep + filename + "_B.tif"
    # Rouge
    command_red = "gdal_translate -b 1 %s %s" %(image_input, fp_red)
    os.system(command_red)
    # Vert
    command_green = "gdal_translate -b 2 %s %s" %(image_input, fp_green)
    os.system(command_green)
    # Bleu
    command_blue = "gdal_translate -b 3 %s %s" %(image_input, fp_blue)
    os.system(command_blue)

    # Bandmath pour creer l'indice ISI
    img_H, img_I, img_S = convertRGBtoHIS(image_input, fp_red, fp_green, fp_blue)

    # Bandes Teinte et Intensité
    H = "im2b1"
    I = "im3b1"

    # ManageNodata
    repository_HI = os.path.dirname(img_H)
    filename_H = os.path.splitext(os.path.basename(img_H))[0]
    fp_H = repository_HI + os.sep + filename_H + "_VF.tif"

    filename_I = os.path.splitext(os.path.basename(img_I))[0]
    fp_I = repository_HI + os.sep + filename_I + "_VF.tif"

    managenodata_H = "otbcli_ManageNoData -in %s -out %s -mode changevalue -mode.changevalue.newv  -9999.0" %(img_H,fp_H)
    os.system(managenodata_H)
    managenodata_I = "otbcli_ManageNoData -in %s -out %s -mode changevalue -mode.changevalue.newv  -9999.0" %(img_I,fp_I)
    os.system(managenodata_I)

    # Creer l'expression
    #expression= "\"(" + H + "==" + I + ")?(" + I + "== 0)?0:" + str(PRECISION) + ":" + "(((" + H + "-" + I + ")/(" + H + "+" + I + "+" + str(PRECISION) + "))+(1-" + NIR + "))/(((" + H + "-" + I + ")/(" + H + "+" + I + "+" + str(PRECISION) + "))+(1+" + NIR + "))\""
    expression = "\"("+H+" == -"+I+") and ( "+I+" == 0) ? 0.001 : ((("+H+" -"+I+" )/("+H + " + "+ I +" ))+(1- "+NIR+" ))/((("+H+"-"+I+" )/( "+H+"+ "+I+" ))+(1+ "+NIR+"))\""
    # Bandmath pour creer l'indice ISI
    command = "otbcli_BandMath -il %s %s %s -out %s %s -exp %s" %(image_input, fp_H, fp_I, image_ISI_output, codage, expression)
    if debug >= 2:
        print(command)
    exitCode = os.system(command)
    if exitCode != 0:
        print(command)
        raise NameError(bold + red + "createISI() : An error occured during otbcli_BandMath command. See error message above." + endC)

    print(cyan + "createISI() : " + bold + green + "Create ISI file %s complete!" %(image_ISI_output) + endC)

    os.remove(img_H)
    os.remove(img_I)

    return

#########################################################################
# FONCTION createHIS()                                                  #
#########################################################################
def createHIS(image_input, image_HIS_output, channel_order, codage="float"):
    """
    #   Rôle : Cette fonction permet de créer un fichier ISI (ombre) à partir d'une image ortho multi bande
    #   paramètres :
    #       image_input : fichier image d'entrée multi bandes
    #       image_HIS_output : fichier HIS permettant de localiser le dossier ou les donnees HIS vont etre sauvegardees
    #       channel_order : liste d'ordre des bandes de l'image (exemple ["Red","Green","Blue","NIR"]
    #       codage : type de codage du fichier de sortie
    # Source : source : http://resources.arcgis.com/en/help/main/10.1/index.html#/Band_Arithmetic_function/009t000001z4000000/
    """

    cont = 0
    # Variables
    Red = ""
    Green = ""
    Blue = ""
    NIR = ""

    # Selection des bandes pour le calcul de ISI
    if "Red" in channel_order:
        num_channel = channel_order.index("Red")+1
        Red = "im1b"+str(num_channel)
    if "Green" in channel_order:
        num_channel = channel_order.index("Green")+1
        Green = "im1b"+str(num_channel)
    if "Blue" in channel_order:
        num_channel = channel_order.index("Blue")+1
        Blue = "im1b"+str(num_channel)
    if "NIR" in channel_order:
        num_channel = channel_order.index("NIR")+1
        NIR = "im1b"+str(num_channel)
    if (Red == "" or Green == "" or Blue == "" or NIR == ""):
        raise NameError(cyan + "createHIS() : " + bold + red + "HIS needs Red and Green and Blue and NIR channels to be computed"+ endC)

    # Repository qui sera a supprimer
    repository = os.path.dirname(image_HIS_output)
    filename = os.path.splitext(os.path.basename(image_input))[0]

    # Creer les images Rouge, Vert, Bleu
    fp_red = repository + os.sep + filename + "_R.tif"
    fp_green =  repository + os.sep + filename + "_V.tif"
    fp_blue = repository + os.sep + filename + "_B.tif"
    # Rouge
    command_red = "gdal_translate -b 1 %s %s" %(image_input, fp_red)
    os.system(command_red)
    # Vert
    command_green = "gdal_translate -b 2 %s %s" %(image_input, fp_green)
    os.system(command_green)
    # Bleu
    command_blue = "gdal_translate -b 3 %s %s" %(image_input, fp_blue)
    os.system(command_blue)

    # Bandmath pour creer l'indice ISI
    img_H, img_I, img_S = convertRGBtoHIS(image_input, fp_red, fp_green, fp_blue)

    ##une ligne est à rajouter pour produire l'image HIS contenant les 3 bandes H, I et S (concatenation de bandes)

    print(cyan + "createHIS() : " + bold + green + "Create HIS file %s complete!" %(image_HIS_output) + endC)

    return

#########################################################################
# FONCTION createVSSI()                                                 #
#########################################################################
def createVSSI(image_input, image_VSSI_output, channel_order, codage="float"):
    """
    #   Rôle : Cette fonction permet de calculer l'indice de salinité (VSSI) sur une image ortho multi bande
    #          Évaluation de la salinité du sol à l'aide du canal proche infrarouge et de la végétation du sol
    #   paramètres :
    #       image_input : fichier image d'entrée multi bandes
    #       image_VSSI_output : fichier VSSIde sortie (une bande)
    #       channel_order : liste d'ordre des bandes de l'image (exemple ["Red","Green","Blue","NIR"])
    #       codage : type de codage du fichier de sortie
    # Source : https://progearthplanetsci.springeropen.com/counter/pdf/10.1186/s40645-019-0311-0.pdf?pdf=button%20sticky  (page 8)
    """

    # Variables
    Red = ""
    Green = ""
    NIR = ""

    # Selection des bandes pour le calcul du VSSI
    if "Red" in channel_order:
        num_channel = channel_order.index("Red")+1
        Red = "im1b"+str(num_channel)
    if "Green" in channel_order:
        num_channel = channel_order.index("Green")+1
        Green = "im1b"+str(num_channel)
    if "NIR" in channel_order:
        num_channel = channel_order.index("NIR")+1
        NIR = "im1b"+str(num_channel)
    if (Red == "" or Green == "" or NIR == ""):
        raise NameError(cyan + "createVSSI() : " + bold + red + "VSSI needs Red, Green and NIR channels to be computed"+ endC)

    # Creer l'expression
    expression = "\"" + "((2 * "+Green+") - 5 * ("+Red+" + "+NIR+"))\""

    # Bandmath pour creer l'indice VSSI
    command = "otbcli_BandMath -il %s -out %s %s -exp %s" %(image_input, image_VSSI_output,codage,expression)
    if debug >= 2:
        print(command)
    exitCode = os.system(command)
    if exitCode != 0:
        print(command)
        raise NameError(bold + red + "createVSSI() : An error occured during otbcli_BandMath command. See error message above." + endC)

    print(cyan + "createVSSI() : " + bold + green + "Create VSSIfile %s complete!" %(image_VSSI_output) + endC)

    return

#########################################################################
# FONCTION createBlueI()                                                #
#########################################################################
def createBlueI(image_input, image_BI_output, channel_order, codage="float"):
    """
    #   Rôle : Cette fonction permet de créer un fichier d'indice de bleu (detection des nuages) à partir d'une image ortho RVB
    #   paramètres :
    #       image_input : fichier image d'entrée multi bandes
    #       image_BI_output : fichier BI de sortie une bande
    #       channel_order : liste d'ordre des bandes de l'image (exemple ["Red","Green","Blue","NIR"]
    #       codage : type de codage du fichier de sortie
    # Source : https://www.researchgate.net/publication/342073075_Cloud_detection_method_for_Pleiades_images_using_spectral_indices
    #
    """

    # Variables
    Red = ""
    Green = ""
    Blue = ""

    # Selection des bandes pour le calcul du BlueIndice
    if "Red" in channel_order:
        num_channel = channel_order.index("Red")+1
        Red = "im1b"+str(num_channel)
    if "Green" in channel_order:
        num_channel = channel_order.index("Green")+1
        Green = "im1b"+str(num_channel)
    if "Blue" in channel_order:
        num_channel = channel_order.index("Blue")+1
        Blue = "im1b"+str(num_channel)
    if (Red == "" or Green == "" or Blue == ""):
        raise NameError(cyan + "createBlueI() : " + bold + red + "c3 needs Red Green and Blue channels to be computed"+ endC)

    # Creer l'expression
    expression = "\"(" + Blue + "== 0)?0:" + "" + Blue + "/(" + Red + "+" + Green + "+" + Blue + ")+" + str(PRECISION) + "\""

    # Bandmath pour creer l'indice Blue
    command = "otbcli_BandMath -il %s -out %s %s -exp %s" %(image_input, image_BI_output,codage,expression)
    if debug >= 2:
        print(command)
    exitCode = os.system(command)
    if exitCode != 0:
        print(command)
        raise NameError(bold + red + "createBlueI() : An error occured during otbcli_BandMath command. See error message above." + endC)

    print(cyan + "createBlueI() : " + bold + green + "Create BI file %s complete!" %(image_BI_output) + endC)

    return

#########################################################################
# FONCTION createSCoWI()                                                #
#########################################################################
def createSCoWI(image_input, image_SCoWI_output, channel_order, codage="float"):
    """
    #   Rôle : Cette fonction permet de créer un fichier SCoWI (eau / trait de côte) à partir d'une image ortho multi bande
    #          La création de cet indice entre dans le cadre plus large de développement de l’outil Shoreliner par le CNES,
    #          qui a pour but d’automatiser la détection des traits de côtes. Cet outil repose sur des données Sentinel-2.
    #          L’objectif du stage de Laurine MEUNIER a été d’adapter l’outil Shoreliner à une source de données Pléiades
    #   paramètres :
    #       image_input : fichier image d'entrée multi bandes
    #       image_SCoWI_output : fichier SCoWI de sortie (une bande)
    #       channel_order : liste d'ordre des bandes de l'image (exemple ["Green","Blue","NIR","SWIR1","SWIR2"])
    #       codage : type de codage du fichier de sortie
    #   Source : 30_Stages_Encours/2025/2025_Teledec_Hugo/03_TRAIT_DE_COTE/Intership_report-2023-CNES-MEUNIERLaurine.pdf
    """

    # Variables
    Green = ""
    Blue = ""
    NIR = ""
    SWIR1 = ""
    SWIR2 = ""

    # Selection des bandes pour le calcul du SCoWI
    if "Green" in channel_order:
        num_channel = channel_order.index("Green")+1
        Green = "im1b"+str(num_channel)
    if "Blue" in channel_order:
        num_channel = channel_order.index("Blue")+1
        Blue = "im1b"+str(num_channel)
    if "NIR" in channel_order:
        num_channel = channel_order.index("NIR")+1
        NIR = "im1b"+str(num_channel)
    if "SWIR1" in channel_order:
        num_channel = channel_order.index("SWIR1")+1
        SWIR1 = "im1b"+str(num_channel)
    if "SWIR2" in channel_order:
        num_channel = channel_order.index("SWIR2")+1
        SWIR2 = "im1b"+str(num_channel)
    if (Green == "" or Blue == "" or NIR == ""):
        raise NameError(cyan + "createSCoWI() : " + bold + red + "SCoWI needs Green, Blue and NIR and (SWIR1 and SWIR2 from Sentinel2) channels to be computed"+ endC)

    # Creer l'expression
    if (SWIR1 == "" or SWIR2 == ""):
        expression = "\"(" + Blue + ") + 2 * (" + Green + ") - 2.4 * (" + NIR  + ")\""
    else :
        expression = "\"(" + Blue + ") + 2 * (" + Green + " - " + NIR  + ") - 0.75 * (" + SWIR1  + ") - 0.5 * (" + SWIR2  + ")\""

    # Bandmath pour creer l'indice MNDWI
    command = "otbcli_BandMath -il %s -out %s %s -exp %s" %(image_input, image_SCoWI_output,codage,expression)
    if debug >= 2:
        print(command)
    exitCode = os.system(command)
    if exitCode != 0:
        print(command)
        raise NameError(bold + red + "createSCoWI() : An error occured during otbcli_BandMath command. See error message above." + endC)

    print(cyan + "createSCoWI() : " + bold + green + "Create SCoWI file %s complete!" %(image_SCoWI_output) + endC)

    return
