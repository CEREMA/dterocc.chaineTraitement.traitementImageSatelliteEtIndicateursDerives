#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT fait un ajout en superposant des donnees issus de BD exogénes au résultat de la classification                                     #
#                                                                                                                                           #
#############################################################################################################################################
"""
Nom de l'objet : DataBaseSuperposition.py
Description :
-------------
Objectif : Permet d'enrichir le résultat de la classification avec une superposition d'element provement de BD Exogènes à fin d'améliorer le résultat final
Rq : utilisation des OTB Applications :   otbcli_BandMath, otbcli_Rasterization

----------
Histoire :
----------
Date de creation : 14/10/2014
-----------------------------------------------------------------------------------------------------
Modifications :

A Reflechir/A faire :

"""

# Import des bibliothèques python
from __future__ import print_function
import os,sys,glob,shutil,string, argparse
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_vector import simplifyVector, cutoutVectors, bufferVector, getAttributeNameList, filterSelectDataVector
from Lib_raster import mergeListRaster, createVectorMask, rasterizeBinaryVector, getNodataValueImage, getGeometryImage
from Lib_log import timeLine
from Lib_file import cleanTempData, deleteDir, removeFile
from Lib_text import extractDico, cleanSpaceText

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 3

###########################################################################################################################################
# DEFINITION DE LA FONCTION addDataBaseExo                                                                                                #
###########################################################################################################################################
def addDataBaseExo(image_input, image_classif_add_output, class_file_dico, class_buffer_dico, class_sql_dico, path_time_log, format_vector='ESRI Shapefile', extension_raster=".tif", extension_vector=".shp", save_results_intermediate=False, overwrite=True, simplifie_param=10.0) :
    """
    # ROLE:
    #    Ajouter des BD exogènes à la classification
    #
    # ENTREES DE LA FONCTION :
    #    image_input : image d'entrée classifié
    #    image_classif_add_output : image classifié enrichie de sortie
    #    class_file_dico : dictionaire de classe contenant les fichiers issu des BD et les buffers à appliquer et la requete sql eventuelle
    #    class_buffer_dico : dictionaire de classe contenant les buffers à appliquer pour chaque fichier de BD
    #    class_sql_dico : dictionaire de classe contenant les requetes sql eventuelle pur la selection dans les fichiers de BD
    #    path_time_log : le fichier de log de sortie
    #    format_vector : format du fichier vecteur. Optionnel, par default : 'ESRI Shapefile'
    #    extension_raster : extension des fichiers raster de sortie, par defaut = '.tif'
    #    extension_vector : extension du fichier vecteur de sortie, par defaut = '.shp'
    #    save_results_intermediate : fichiers de sorties intermediaires nettoyees, par defaut = False
    #    overwrite : boolen ecrasement ou non des fichiers ayant un nom similaire, par defaut à True
    #    simplifie_param : parmetre de simplification des polygones
    #
    # SORTIES DE LA FONCTION :
    #    Aucun
    #    Eléments générés par la fonction : vecteurs echantillons de réference par macro classes
    """

    # Mise à jour du Log
    starting_event = "addDataBaseExo() : Add data base exogene to classification starting : "
    timeLine(path_time_log,starting_event)

    # Print
    if debug >= 3:
        print(bold + green + "Variables dans la fonction" + endC)
        print(cyan + "addDataBaseExo() : " + endC + "image_input : " + str(image_input) + endC)
        print(cyan + "addDataBaseExo() : " + endC + "image_classif_add_output : " + str(image_classif_add_output) + endC)
        print(cyan + "addDataBaseExo() : " + endC + "class_file_dico : " + str(class_file_dico) + endC)
        print(cyan + "addDataBaseExo() : " + endC + "class_buffer_dico : " + str(class_buffer_dico) + endC)
        print(cyan + "addDataBaseExo() : " + endC + "class_sql_dico : " + str(class_sql_dico) + endC)
        print(cyan + "addDataBaseExo() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "addDataBaseExo() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "addDataBaseExo() : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "addDataBaseExo() : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "addDataBaseExo() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "addDataBaseExo() : " + endC + "overwrite : " + str(overwrite) + endC)

    # Constantes
    FOLDER_MASK_TEMP = 'Mask_'
    FOLDER_FILTERING_TEMP = 'Filt_'
    FOLDER_CUTTING_TEMP = 'Cut_'
    FOLDER_BUFF_TEMP = 'Buff_'

    SUFFIX_MASK_CRUDE = '_mcrude'
    SUFFIX_MASK = '_mask'
    SUFFIX_FUSION = '_info'
    SUFFIX_VECTOR_FILTER = "_filt"
    SUFFIX_VECTOR_CUT = '_decoup'
    SUFFIX_VECTOR_BUFF = '_buff'

    CODAGE = "uint16"

    # ETAPE 1 : NETTOYER LES DONNEES EXISTANTES
    if debug >= 2:
        print(cyan + "addDataBaseExo() : " + bold + green + "NETTOYAGE ESPACE DE TRAVAIL..." + endC)

    # Nom de base de l'image
    image_name = os.path.splitext(os.path.basename(image_input))[0]

    # Nettoyage d'anciennes données résultat

    # Si le fichier résultat existent deja et que overwrite n'est pas activé
    check = os.path.isfile(image_classif_add_output)
    if check and not overwrite :
        print(bold + yellow + "addDataBaseExo() : " + endC + image_classif_add_output + " has already added bd exo and will not be added again." + endC)
    else:
        if check :
            try:
                removeFile(image_classif_add_output) # Tentative de suppression du fichier
            except Exception:
                pass            # Si le fichier ne peut pas être supprimé, on suppose qu'il n'existe pas et on passe à la suite

        # Définition des répertoires temporaires
        repertory_output = os.path.dirname(image_classif_add_output)
        repertory_mask_temp = repertory_output + os.sep + FOLDER_MASK_TEMP + image_name
        repertory_samples_filtering_temp = repertory_output + os.sep +  FOLDER_FILTERING_TEMP + image_name
        repertory_samples_cutting_temp = repertory_output + os.sep + FOLDER_CUTTING_TEMP + image_name
        repertory_samples_buff_temp = repertory_output + os.sep + FOLDER_BUFF_TEMP + image_name

        if debug >= 4:
            print(repertory_mask_temp)
            print(repertory_samples_filtering_temp)
            print(repertory_samples_cutting_temp)
            print(repertory_samples_buff_temp)

        # Creer les répertoires temporaire si ils n'existent pas
        if not os.path.isdir(repertory_output):
            os.makedirs(repertory_output)
        if not os.path.isdir(repertory_mask_temp):
            os.makedirs(repertory_mask_temp)
        if not os.path.isdir(repertory_samples_filtering_temp):
            os.makedirs(repertory_samples_filtering_temp)
        if not os.path.isdir(repertory_samples_cutting_temp):
            os.makedirs(repertory_samples_cutting_temp)
        if not os.path.isdir(repertory_samples_buff_temp):
            os.makedirs(repertory_samples_buff_temp)

        # Nettoyer les répertoires temporaire si ils ne sont pas vide
        cleanTempData(repertory_mask_temp)
        cleanTempData(repertory_samples_filtering_temp)
        cleanTempData(repertory_samples_cutting_temp)
        cleanTempData(repertory_samples_buff_temp)

        if debug >= 2:
            print(cyan + "addDataBaseExo() : " + bold + green + "... FIN NETTOYAGE" + endC)

        # ETAPE 2 : CREER UN SHAPE DE DECOUPE

        if debug >= 2:
            print(cyan + "addDataBaseExo() : " + bold + green + "SHAPE DE DECOUPE..." + endC)

        # 2.1 : Création des masques délimitant l'emprise de la zone par image

        vector_mask = repertory_mask_temp + os.sep + image_name + SUFFIX_MASK_CRUDE + extension_vector
        cols, rows, num_band = getGeometryImage(image_input)
        no_data_value = getNodataValueImage(image_input, num_band)
        if no_data_value == None :
            no_data_value = 0
        createVectorMask(image_input, vector_mask, no_data_value, format_vector)

        # 2.2 : Simplification du masque global

        vector_simple_mask_cut = repertory_mask_temp + os.sep + image_name + SUFFIX_MASK + extension_vector
        simplifyVector(vector_mask, vector_simple_mask_cut, simplifie_param, format_vector)

        if debug >= 2:
            print(cyan + "addDataBaseExo() : " + bold + green + "...FIN SHAPE DE DECOUPEE" + endC)

        # ETAPE 3 : DECOUPER BUFFERISER LES VECTEURS ET FUSIONNER

        if debug >= 2:
            print(cyan + "addDataBaseExo() : " + bold + green + "MISE EN PLACE DES TAMPONS..." + endC)

        image_combined_list = []
        # Parcours du dictionnaire associant les macroclasses aux noms de fichiers
        for macroclass_label in class_file_dico :
            vector_fusion_list = []
            for index_info in range(len(class_file_dico[macroclass_label])) :
                input_vector = class_file_dico[macroclass_label][index_info]
                vector_name =  os.path.splitext(os.path.basename(input_vector))[0]
                output_vector_filtered = repertory_samples_filtering_temp + os.sep + vector_name + SUFFIX_VECTOR_FILTER + extension_vector
                output_vector_cut = repertory_samples_cutting_temp + os.sep + vector_name + SUFFIX_VECTOR_CUT + extension_vector
                output_vector_buff = repertory_samples_buff_temp + os.sep + vector_name + SUFFIX_VECTOR_BUFF + extension_vector
                sql_expression = class_sql_dico[macroclass_label][index_info]
                buffer_str = class_buffer_dico[macroclass_label][index_info]
                buff = 0.0
                col_name_buf = ""
                try:
                    buff = float(buffer_str)
                except :
                    col_name_buf = buffer_str
                    print(cyan + "addDataBaseExo() : " + bold + green + "Pas de valeur buffer mais un nom de colonne pour les valeur à bufferiser : " + endC + col_name_buf)

                if os.path.isfile(input_vector):
                    if debug >= 3:
                        print(cyan + "addDataBaseExo() : " + endC + "input_vector : " + str(input_vector) + endC)
                        print(cyan + "addDataBaseExo() : " + endC + "output_vector_filtered : " + str(output_vector_filtered) + endC)
                        print(cyan + "addDataBaseExo() : " + endC + "output_vector_cut : " + str(output_vector_cut) + endC)
                        print(cyan + "addDataBaseExo() : " + endC + "output_vector_buff : " + str(output_vector_buff) + endC)
                        print(cyan + "addDataBaseExo() : " + endC + "buff : " + str(buff) + endC)
                        print(cyan + "addDataBaseExo() : " + endC + "sql : " + str(sql_expression) + endC)

                    # 3.0 : Recuperer les vecteurs d'entrée et filtree selon la requete sql par ogr2ogr
                    if sql_expression != "":
                        names_attribut_list = getAttributeNameList(input_vector, format_vector)
                        column = "'"
                        for name_attribut in names_attribut_list :
                            column += name_attribut + ", "
                        column = column[0:len(column)-2]
                        column += "'"
                        ret = filterSelectDataVector(input_vector, output_vector_filtered, column, sql_expression, format_vector)
                        if not ret :
                            print(cyan + "addDataBaseExo() : " + bold + yellow + "Attention problème lors du filtrage des BD vecteurs l'expression SQL %s est incorrecte" %(sql_expression) + endC)
                            output_vector_filtered = input_vector
                    else :
                        print(cyan + "addDataBaseExo() : " + bold + green + "Pas de filtrage sur le fichier du nom : " + endC + output_vector_filtered)
                        output_vector_filtered = input_vector

                    # 3.1 : Découper le vecteur selon l'empise de l'image d'entrée
                    cutoutVectors(vector_simple_mask_cut, [output_vector_filtered], [output_vector_cut], format_vector)

                    # 3.2 : Bufferiser lesvecteurs découpé avec la valeur défini dans le dico ou trouver dans la base du vecteur lui même si le nom de la colonne est passée dans le dico
                    if os.path.isfile(output_vector_cut) and ((buff != 0) or (col_name_buf != "")) :
                        bufferVector(output_vector_cut, output_vector_buff, buff, col_name_buf, 0.5, 10, format_vector)
                    else :
                        print(cyan + "addDataBaseExo() : " + bold + green + "Pas de buffer sur le fichier du nom : " + endC + output_vector_cut)
                        output_vector_buff = output_vector_cut

                    # 3.3 : Si un shape résulat existe l'ajouté à la liste de fusion
                    if os.path.isfile(output_vector_buff):
                        vector_fusion_list.append(output_vector_buff)
                        if debug >= 3:
                            print("file for fusion : " + output_vector_buff)
                    else :
                        print(bold + yellow + "pas de fichiers avec ce nom : " + endC + output_vector_buff)

                else :
                    print(cyan + "addDataBaseExo() : " + bold + yellow + "Pas de fichier du nom : " + endC + input_vector)

            # 3.4 : Fusionner les shapes transformés d'une même classe, rasterization et labelisations des vecteurs
            # Si une liste de fichier shape existe
            if not vector_fusion_list:
                print(bold + yellow + "Pas de fusion sans donnee a fusionnee" + endC)
            else :
                # Rasterization et BandMath des fichiers shapes
                raster_list = []
                for vector in vector_fusion_list:
                    if debug >= 3:
                        print(cyan + "addDataBaseExo() : " + endC + "Rasterization : " + vector + " label : " + macroclass_label)
                    raster_output = os.path.splitext(vector)[0] + extension_raster

                    # Rasterisation
                    rasterizeBinaryVector(vector, image_input, raster_output, macroclass_label, CODAGE)
                    raster_list.append(raster_output)

                if debug >= 3:
                    print(cyan + "addDataBaseExo() : " + endC + "nombre d'images a combiner : " + str(len(raster_list)))

                # Liste les images raster combined and sample
                image_combined = repertory_output + os.sep + image_name + '_' + str(macroclass_label) + SUFFIX_FUSION + extension_raster
                image_combined_list.append(image_combined)

                # Fusion des images raster en une seule
                mergeListRaster(raster_list, image_combined, CODAGE)

        if debug >= 2:
            print(cyan + "addDataBaseExo() : " + bold + green +  "FIN DE L AFFECTATION DES TAMPONS" + endC)

        # ETAPE 4 : ASSEMBLAGE DE L'IMAGE CLASSEE ET DES BD EXOS
        if debug >= 2:
            print(cyan + "addDataBaseExo() : " + bold + green + "ASSEMBLAGE..." + endC)

        # Ajout de l'image de classification a la liste des image bd conbinées
        image_combined_list.append(image_input)
        # Fusion les images avec la classification
        mergeListRaster(image_combined_list, image_classif_add_output, CODAGE)
        if debug >= 2:
            print(cyan + "addDataBaseExo() : " + bold + green +  "FIN" + endC)

    # ETAPE 5 : SUPPRESIONS FICHIERS INTERMEDIAIRES INUTILES

    # Suppression des données intermédiaires
    if not save_results_intermediate:

        image_combined_list.remove(image_input)
        for to_delete in image_combined_list :
            removeFile(to_delete)

        # Suppression des repertoires temporaires
        deleteDir(repertory_mask_temp)
        deleteDir(repertory_samples_filtering_temp)
        deleteDir(repertory_samples_cutting_temp)
        deleteDir(repertory_samples_buff_temp)

    # Mise à jour du Log
    ending_event = "addDataBaseExo() : Add data base exogene to classification ending : "
    timeLine(path_time_log,ending_event)

    return

###########################################################################################################################################
# MISE EN PLACE DU PARSER                                                                                                                 #
###########################################################################################################################################

# Code executé seulement dans le cas ou le script est lancé depuis une ligne de commande
# Il n'est pas executé lors d'un import DataBaseSuperposition.py
# Exemple de lancement en ligne de commande:
# python DataBaseSuperposition.py -i ../ImagesTestChaine/APTV_06/Resultats/APTV_06_classif.tif -o ../ImagesTestChaine/APTV_06/Resultats/APTV_06_classif_final.tif -classBd 11000:../ImagesTestChaine/APTV_06/BD/ROUTE_74.shp:../ImagesTestChaine/APTV_06/BD/BATI_INDIFFERENCIE_74.shp 12200:../ImagesTestChaine/APTV_06/BD/SURFACE_EAU_74.shp -log ../ImagesTestChaine/APTV_06/fichierTestLog.txt
# python DataBaseSuperposition.py -i /mnt/hgfs/Data_Image_Saturn/CUB_Nord_Ouest/Classification/CUB_Nord_Ouest_stack_rf_merged_filtered.tif -o /mnt/hgfs/Data_Image_Saturn/CUB_Nord_Ouest/Classification/CUB_Nord_Ouest_stack_rf_new_merged_filtered_final2.tif -classBd 11200:/mnt/hgfs/Data_Image_Saturn/BD/ROUTE_PRIMAIRE_033.shp:/mnt/hgfs/Data_Image_Saturn/BD/ROUTE_SECONDAIRE_033.shp 13000:/mnt/hgfs/Data_Image_Saturn/BD/TRONCON_VOIE_FERREE_033.shp:/mnt/hgfs/Data_Image_Saturn/BD/AIRE_TRIAGE_033.shp -log /mnt/hgfs/Data_Image_Saturn/CUB_Nord_Ouest/CUB_Nord_Ouest.log

def main(gui=False):

   # Définition des arguments possibles pour l'appel en ligne de commande
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, prog="DataBaseSuperposition",description="\
    Info : Add BD exo to classification. \n\
    Objectif : Permet d'enrichir le resultat de la classification avec une superposition d'element provement de BD Exogenes a fin d'ameliorer le resultat final. \n\
    Example : python DataBaseSuperposition.py -i ../ImagesTestChaine/APTV_06/Resultats/APTV_06_classif.tif \n\
                                              -o ../ImagesTestChaine/APTV_06/Resultats/APTV_06_classif_final.tif \n\
                                              -classBd 11000:../ImagesTestChaine/APTV_06/BD/ROUTE_74.shp:../ImagesTestChaine/APTV_06/BD/BATI_INDIFFERENCIE_74.shp \n\
                                                       12200:../ImagesTestChaine/APTV_06/BD/SURFACE_EAU_74.shp \n\
                                              -log ../ImagesTestChaine/APTV_06/fichierTestLog.txt")

    # Paramètres généraux
    parser.add_argument('-i','--image_input',default="",help="Image classification input to add data", type=str, required=True)
    parser.add_argument('-o','--image_output',default="",help="Image classification output result additional bd data", type=str, required=True)
    parser.add_argument('-classBd','--class_file_dico',default="",nargs="+",help="Dictionary of class containt bd, (format : classeLabel:[BDfile][..]), ex. 11000:../ImagesTestChaine/APTV_06/BD/ROUTE_74.shp,../ImagesTestChaine/APTV_06/BD/BATI_INDIFFERENCIE_74.shp 12200:../ImagesTestChaine/APTV_06/BD/SURFACE_EAU_74.shp", type=str, required=True)
    parser.add_argument('-classBuf','--class_buffer_dico',default="",nargs="+",help="Dictionary of class containt buffer, (format : classeLabel:[sizeBuffer][..]), ex. 11000:3,5.0,,7 12200:0,", type=str, required=False)
    parser.add_argument('-classSql','--class_sql_dico',default="",nargs="+",help="Dictionary of class containt sql request, (format : classeLabel:[SqlRequest][..]), ex. 11000:NATURE ='Autoroute' OR NATURE ='Route 2 Chausses',NATURE ='Route 2 Chausses' 12200:NATURE = 'Lac naturel'", type=str, required=False)
    parser.add_argument('-simp','--simple_param_vector',default=10.0,help="Parameter of polygons simplification. By default : 10.0", type=float, required=False)
    parser.add_argument('-vef','--format_vector', default="ESRI Shapefile",help="Format of the output file.", type=str, required=False)
    parser.add_argument('-rae','--extension_raster', default=".tif", help="Option : Extension file for image raster. By default : '.tif'", type=str, required=False)
    parser.add_argument('-vee','--extension_vector',default=".shp",help="Option : Extension file for vector. By default : '.shp'", type=str, required=False)
    parser.add_argument('-log','--path_time_log',default="",help="Name of log", type=str, required=False)
    parser.add_argument('-sav','--save_results_inter',action='store_true',default=False,help="Save or delete intermediate result after the process. By default, False", required=False)
    parser.add_argument('-now','--overwrite',action='store_false',default=True,help="Overwrite files with same names. By default, True",required=False)
    parser.add_argument('-debug','--debug',default=3,help="Option : Value of level debug trace, default : 3 ",type=int, required=False)
    args = displayIHM(gui, parser)

    # RECUPERATION DES ARGUMENTS

    # Récupération de l'image d'entrée
    if args.image_input != None:
        image_input = args.image_input
        if not os.path.isfile(image_input):
            raise NameError (cyan + "DataBaseSuperposition : " + bold + red  + "File %s not existe!" %(image_input) + endC)

    # Récupération de l'image de sortie
    if args.image_output != None:
        image_output = args.image_output

    # Creation de dictionaire table macro class contenant les fichiers dela BD
    class_file_dico = {}
    if args.class_file_dico != None:
        class_file_dico_tmp = extractDico(args.class_file_dico)
        for ident_class in class_file_dico_tmp:
            class_file_dico[ident_class] = class_file_dico_tmp[ident_class][0]

    # Creation de dictionaire table macro class contenant les buffers
    class_buffer_dico = {}
    if args.class_buffer_dico != None:
        class_buffer_dico_tmp = extractDico(args.class_buffer_dico)
        for ident_class in class_buffer_dico_tmp:
            class_buffer_dico[ident_class] = class_buffer_dico_tmp[ident_class][0]

    # Creation de dictionaire table macro class contenant les requettes SQL
    if args.class_sql_dico != None:
        class_sql_dico_str = ""
        for str_dico in args.class_sql_dico:
            class_sql_dico_str += str_dico + " "
        class_sql_dico_list = class_sql_dico_str.split(":")
        class_sql_dico = {}
        idex_elem = 0
        while idex_elem < len(class_sql_dico_list):
            class_sql_dico[class_sql_dico_list[idex_elem]] = cleanSpaceText(class_sql_dico_list[idex_elem + 1]).split(",")
            idex_elem += 2

    # Simplifie_param param
    if args.simple_param_vector != None:
        simplifie_param = args.simple_param_vector

    # Récupération du format des vecteurs de sortie
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
        print(cyan + "DataBaseSuperposition : " + endC + "image_input : " + str(image_input) + endC)
        print(cyan + "DataBaseSuperposition : " + endC + "image_output : " + str(image_output) + endC)
        print(cyan + "DataBaseSuperposition : " + endC + "class_file_dico : " + str(class_file_dico) + endC)
        print(cyan + "DataBaseSuperposition : " + endC + "class_buffer_dico : " + str(class_buffer_dico) + endC)
        print(cyan + "DataBaseSuperposition : " + endC + "class_sql_dico : " + str(class_sql_dico) + endC)
        print(cyan + "DataBaseSuperposition : " + endC + "simple_param_vector : " + str(simplifie_param) + endC)
        print(cyan + "DataBaseSuperposition : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "DataBaseSuperposition : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "DataBaseSuperposition : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "DataBaseSuperposition : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "DataBaseSuperposition : " + endC + "save_results_inter : " + str(save_results_intermediate) + endC)
        print(cyan + "DataBaseSuperposition : " + endC + "overwrite: " + str(overwrite) + endC)
        print(cyan + "DataBaseSuperposition : " + endC + "debug: " + str(debug) + endC)

    # EXECUTION DE LA FONCTION
    # Si le dossier de sortie n'existe pas, on le crée
    repertory_output = os.path.dirname(image_output)
    if not os.path.isdir(repertory_output):
        os.makedirs(repertory_output)

    # Execution de la fonction pour une image
    addDataBaseExo(image_input, image_output, class_file_dico, class_buffer_dico, class_sql_dico, path_time_log, format_vector, extension_raster, extension_vector, save_results_intermediate, overwrite,simplifie_param)

# ================================================

if __name__ == '__main__':
  main(gui=False)
