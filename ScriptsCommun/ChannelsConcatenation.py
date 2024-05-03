#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT QUI CONCATENE DES IMAGES D'UNE BANDE ET CALCULE LES BANDES MANQUANTES SI BESOIN                                                    #
#                                                                                                                                           #
#############################################################################################################################################
"""
Nom de l'objet : ChannelsConcatenation.py
Description :
-------------
Objectif   : concatener des bandes d'une image
Rq         : utilisation des OTB Applications : otbcli_ConcatenateImages, otbcli_ComputeImagesStatistics, otbcli_BandMath, otbcli_DimensionalityReduction

Date de creation : 31/07/2014
----------
Histoire :
----------
Origine : le script originel provient du fichier Chain3_Channel_Concatenation.py cree en 2013 et utilise par la chaine de traitement OCSOL V1.X
31/07/2014 : Transformation en brique elementaire (suppression des liens avec la chaine OCSOL)
-----------------------------------------------------------------------------------------------------
Modifications :
31/07/2014 : choix > supprimer pathTimelog > remplacer verifActivation par overwrite et mettre a True par defaut
06/08/2014 : recupere par defaut le chemin vers le dossier courant pour trouver et lancer le script NeoChannelsComputation.py
01/10/2014 : refonte du fichier harmonisation des régles de qualitées des niveaux de boucles et des paramétres dans args <w
25/03/2015 : supression de la connction avec le module NeoChannelsComputation
21/05/2015 : simplification des parametres en argument plus de liste d'image en emtrée à traiter uniquement une image
------------------------------------------------------
A Reflechir/A faire :
traduire le docstring en anglais
gestion du calcul des textures si elles n'ont pas ete creees :
> sol1 : quitter le code et demander de les creer separement
> sol2 : donner le chemin vers le script TextureExtraction.py via le parametre path_neochannels_computation)
> sol3 : fixer le chemin vers le script TextureExtraction.py en dur dans le code (necessite d'avoir arrete l'architecture des dossiers)
pouvoir aussi gérer l'ajout de néocnaux directement en choisisant ceux-ci dans un repertoire / logique différente de textures_list = [["HaralickCorrelation",4,2],["HaralickCorrelation",2,2]]
"""

from __future__ import print_function
import os, sys, glob, argparse, string, getopt
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_log import timeLine
from Lib_operator import *
from Lib_file import removeFile
from Lib_raster import computeStatisticsImage
from Lib_xml import parseDom

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 4

# Les parametres de la fonction OTB otbcli_KMeansClassification a changé à partir de la version 7.0 de l'OTB
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
# FONCTION concatenateChannels()                                                                                                          #
###########################################################################################################################################
def concatenateChannels(images_input_list, stack_image_output, path_time_log, code="float", save_results_intermediate=False, overwrite=True):
    """
    # ROLE:
    #   Role : ajout de neocanaux (textures et/ou indices) deja calcules ou non a l'image d'origine
    #     Compléments sur la fonction otbcli_HaralickTextureExtraction : http://www.orfeo-toolbox.org/CookBook/CookBooksu98.html#x130-6310005.6.6
    #     Compléments sur la fonction otbcli_SplitImage : http://www.orfeo-toolbox.org/CookBook/CookBooksu68.html#x95-2580005.1.10
    #     Compléments sur la fonction otbcli_BandMath : http://www.orfeo-toolbox.org/CookBook/CookBooksu125.html#x161-9330005.10.1
    #
    # ENTREES DE LA FONCTION :
    #    images_input_list : liste de fichiers a stacker ensemble
    #    stack_image_output : le nom de l'empilement image de sortie
    #    path_time_log : le fichier de log de sortie
    #    code : encodage du fichier de sortie
    #    save_results_intermediate : fichiers de sorties intermediaires non nettoyees, par defaut = False
    #    overwrite : boolen si vrai, ecrase les fichiers existants
    #
    # SORTIES DE LA FONCTION :
    #    le nom complet de l'image de sortie
    #    Elements generes : une image concatenee rangee
    #
    """

    # Mise à jour du Log
    starting_event = "concatenateChannels() : Concatenate channels starting : "
    timeLine(path_time_log,starting_event)

    print(endC)
    print(bold + green + "## START : CHANNELS CONCATENATION" + endC)
    print(endC)

    if debug >= 3:
        print(bold + green + "Variables dans la fonction" + endC)
        print(cyan + "concatenateChannels() : " + endC + "images_input_list : " + str(images_input_list) + endC)
        print(cyan + "concatenateChannels() : " + endC + "stack_image_output : " + str(stack_image_output) + endC)
        print(cyan + "concatenateChannels() : " + endC + "code : " + str(code) + endC)
        print(cyan + "concatenateChannels() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "concatenateChannels() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "concatenateChannels() : " + endC + "overwrite : " + str(overwrite) + endC)

    check = os.path.isfile(stack_image_output)
    if check and not overwrite: # Si l'empilement existe deja et que overwrite n'est pas activé
        print(bold + yellow + "File " + stack_image_output + " already exists and will not be calculated again." + endC)
    else:
        if check:
            try:
                removeFile(stack_image_output)
            except Exception:
                pass # si le fichier n'existe pas, il ne peut pas être supprimé : cette étape est ignorée

        print(bold + green + "Searching for channels to add..." + endC)

        elements_to_stack_list_str = ""    # Initialisation de la liste des fichiers autres a empiler

        # Gestion des fichiers a ajouter
        for image_name_other in images_input_list:

            if debug >= 3:
                print(cyan + "concatenateChannels() : " + endC + "image_name_other : " + str(image_name_other) + endC)

            # Verification de l'existence de image_name_other
            if not os.path.isfile(image_name_other) :
                # Si image_name_other n'existe pas, message d'erreur
                raise NameError(cyan + "concatenateChannels() : " + bold + red + "The file %s not existe!"%(image_name_other) + endC)

            # Ajouter l'indice a la liste des indices a empiler
            elements_to_stack_list_str += " " + image_name_other

            if debug >= 1:
                print(cyan + "concatenateChannels() : " + endC + "elements_to_stack_list_str : " + str(elements_to_stack_list_str) + endC)

        # Stack de l'image avec les images additionnelles
        if len(elements_to_stack_list_str) > 0:

            # Assemble la liste d'image en une liste globale de fichiers d'entree
            print(bold + green + "concatenateChannels() : Assembling channels %s ... "%(elements_to_stack_list_str) + endC)

            command = "otbcli_ConcatenateImages -progress true -il %s -out %s %s" %(elements_to_stack_list_str,stack_image_output,code)
            if debug >= 3:
                print(command)
            exitCode = os.system(command)
            if exitCode != 0:
                print(command)
                raise NameError(cyan + "concatenateChannels() : " + bold + red + "An error occured during otbcli_ConcatenateImages command. See error message above." + endC)
            print(bold + green + "concatenateChannels() : Channels successfully assembled" + endC)

    print(endC)
    print(bold + green + "## END : CHANNELS CONCATENATION" + endC)
    print(endC)

    # Mise à jour du Log
    ending_event = "concatenateChannels() : Concatenate channels ending : "
    timeLine(path_time_log,ending_event)

    return

###########################################################################################################################################
# FONCTION normalizeChannels()                                                                                                            #
###########################################################################################################################################
def normalizeChannels(image_stack_input, image_normalised_stack_output, path_time_log, save_results_intermediate=False, overwrite=True):
    """
    # ROLE:
    #   Role : Normalise les differents canneaux de l'image passée en entrée
    #
    # ENTREES DE LA FONCTION :
    #    image_stack_input : image staké qui doit être normaliser
    #    image_normalised_stack_output : image normalisé résultat
    #    path_time_log : le fichier de log de sortie
    #    save_results_intermediate : fichiers de sorties intermediaires non nettoyees, par defaut = False
    #    overwrite : boolen si vrai, ecrase les fichiers existants
    #
    # SORTIES DE LA FONCTION :
    #   Elements generes : une image normalisée rangee et un fichier statistique
    #
    """

    # Mise à jour du Log
    starting_event = "normalizeChannels() : Normalize channels starting : "
    timeLine(path_time_log,starting_event)

    print(endC)
    print(bold + green + "## START : CHANNELS NORMALIZATION" + endC)
    print(endC)

    # Constantes
    CODAGE = "float"

    # Nom de l'image en entrée
    repertory_stacks_output = os.path.dirname(image_normalised_stack_output)
    image_name = os.path.splitext(os.path.basename(image_stack_input))[0]
    extension_file = os.path.splitext(os.path.basename(image_stack_input))[1]
    statistics_image_normalize_output = os.path.splitext(image_normalised_stack_output)[0] + "_statistics.xml"

    if debug >= 3:
        print(bold + green + "Variables dans la fonction" + endC)
        print(cyan + "normalizeChannels() : " + endC + "image_stack_input : " + str(image_stack_input) + endC)
        print(cyan + "normalizeChannels() : " + endC + "image_normalised_stack_output : " + str(image_normalised_stack_output) + endC)
        print(cyan + "normalizeChannels() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "normalizeChannels() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "normalizeChannels() : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "normalizeChannels() : " + endC + "image_name : " + str(image_name) + endC)
        print(cyan + "normalizeChannels() : " + endC + "extension_file : " + str(extension_file) + endC)
        print(cyan + "normalizeChannels() : " + endC + "repertory_stacks_output : " + str(repertory_stacks_output) + endC)

    # Si l'empilement existe deja et que overwrite n'est pas activé
    check = os.path.isfile(image_normalised_stack_output)
    if check and not overwrite:
        print(bold + yellow + "Stack normalized already exists and will not be calculated again." + endC)
    else:
        if check :
            try:
                removeFile(image_normalised_stack_output)
            except Exception:
                pass # si le fichier n'existe pas, il ne peut pas être supprimé : cette étape est ignorée

        # Calcul des statistiques de l'empilement
        # Les statistiques sont dans un fichier xml presentant un paragraphe pour la moyenne et un autre pour l'ecart-type. Chaque paragraphe contient une ligne par bande dont l'ordre correspond à celui de l'empilement
        print(bold + green + "Calcul des statistiques de %s " %(image_stack_input) + endC)
        computeStatisticsImage(image_stack_input, statistics_image_normalize_output)
        statistics_file_parser = parseDom(statistics_image_normalize_output)
        statistics_nodes_list = statistics_file_parser.getElementsByTagName('Statistic')

        # Initialise les listes des moyennes et des ecart-types des bandes de l'empilement
        mins_list = []
        maxs_list = []
        means_list = []
        stddevs_list = []

        # Parcours du fichier de statistiques pour recuperer les valeur de moyenne et d'ecart-type associees a chaque bande
        if debug >= 1:
            print(cyan + "normalizeChannels() : " + endC + bold + green + "Parsing statistics file ..." + endC)

        for statistic in statistics_nodes_list:

            statistics_list = []
            nodes_values_list = statistic.getElementsByTagName('StatisticVector')

            for node in nodes_values_list:

                value = node.attributes['value'].value

                # Si la ligne comporte la balise "min", ajoute la valeur associee a la liste des minimums
                if statistic.attributes['name'].value == "min":
                    value = node.attributes['value'].value
                    mins_list.append(value)

                # Si la ligne comporte la balise "max", ajoute la valeur associee a la liste des maximums
                elif statistic.attributes['name'].value == "max":
                    value = node.attributes['value'].value
                    maxs_list.append(value)

                # Si la ligne comporte la balise "mean", ajoute la valeur associee a la liste des moyennes
                elif statistic.attributes['name'].value == "mean":
                    value = node.attributes['value'].value
                    means_list.append(value)

                # Si la ligne comporte la balise "stddev", ajoute la valeur associee a la liste des ecart-types
                elif statistic.attributes['name'].value == "stddev":
                    value = node.attributes['value'].value
                    stddevs_list.append(value)

        if debug >= 1:
            print(cyan + "normalizeChannels() : " + endC + bold + green + "Parsing statistics complete." + endC)
            print(cyan + "normalizeChannels() : " + endC + "mins_list : " + str(mins_list) + endC)
            print(cyan + "normalizeChannels() : " + endC + "maxs_list : " + str(maxs_list) + endC)
            print(cyan + "normalizeChannels() : " + endC + "means_list : " + str(means_list) + endC)
            print(cyan + "normalizeChannels() : " + endC + "stddevs_list : " + str(stddevs_list) + endC)


        number_of_bands = len(mins_list)   # Nombre de bandes a empiler (= nombre de valeurs dans la liste des moyennes par exemple)
        bands_to_concatenate_list = ""      # Initialisation de la liste des bandes extraites de l'empilement
        files_to_delete_list = []           # Initialisation de la liste de ces mêmes bandes pour la supression (format different de celui necessaire pour les applications OTB)

        # Parcours des bandes de l'empilement, en utilisant la place de leur moyenne dans la liste des moyennes pour conserver le même ordre que dans l'empilement
        for band in range (number_of_bands):

            min_value = mins_list[band]
            max_value = maxs_list[band]
            mean_value = means_list[band]
            stddev_value = stddevs_list[band]

            normalised_band = repertory_stacks_output + os.sep + image_name + "_b" + str(band) + extension_file
            #expression = "\"(im1b" + str(band+1) + "-(" + str(mean_value) + "))/" + str(stddev_value) + "\""
            expression = "\"(im1b" + str(band+1) + "-" + str(min_value) + ")/(" + str(max_value) + "-" + str(min_value) + ")\""

            if debug >= 1:
                print(cyan + "normalizeChannels() : " + endC + "Normalizing band %s" %(band)+ endC)
            if debug >= 2:
                print(cyan + "normalizeChannels() : " + endC + "min_value : " + str(min_value) + endC)
                print(cyan + "normalizeChannels() : " + endC + "max_value : " + str(max_value) + endC)
                print(cyan + "normalizeChannels() : " + endC + "mean_value : " + str(mean_value) + endC)
                print(cyan + "normalizeChannels() : " + endC + "stddev_value : " + str(stddev_value) + endC)
                print(cyan + "normalizeChannels() : " + endC + "normalised_band : " + str(normalised_band) + endC)

            command = "otbcli_BandMath -il %s -out %s %s -exp %s" %(image_stack_input,normalised_band,CODAGE,expression)

            if debug >= 3:
                print(command)

            exitCode = os.system(command)
            if exitCode != 0:
                print(command)
                raise NameError(cyan + "normalizeChannels() : " + bold + red + "An error occured during otbcli_BandMath command. See error message above." + endC)

            if debug >= 1:
                print(cyan + "normalizeChannels() : " + endC + bold + green + "Band %s normalized." %(band)+ endC)
                print(endC)

            # Mise à jour de bands_to_concatenate_list et files_to_delete_list
            bands_to_concatenate_list += " " + normalised_band
            files_to_delete_list.append(normalised_band)

        if debug >= 1:
            print(cyan + "normalizeChannels() : " + endC + bold + green + "Stacking bands ..."+ endC)
        if debug >= 2:
            print(cyan + "normalizeChannels() : " + endC + bold + green + "Debut de la concatenation de "+ endC + " %s ..." %(bands_to_concatenate_list)+ endC)
            print(endC)

        # Empile les bandes dans un nouveau fichier
        exitCode = os.system("otbcli_ConcatenateImages -progress true -il %s -out %s %s" %(bands_to_concatenate_list, image_normalised_stack_output, CODAGE))
        if exitCode != 0:
            raise NameError(cyan + "normalizeChannels() : " + bold + red + "An error occured during otbcli_ConcatenateImages command. See error message above." + endC)

        # Suppression des bandes normalisees seulles - Possibilitée de passer cette activation en parametre
        if not save_results_intermediate:
            for file_del in files_to_delete_list:
                removeFile(file_del) # Suppression des bandes

    print(endC)
    print(bold + green + "## END : CHANNELS NORMALIZATION" + endC)
    print(endC)

    # Mise à jour du Log
    ending_event = "normalizeChannels() : Normalize channels ending : "
    timeLine(path_time_log,ending_event)

    return

###########################################################################################################################################
# FONCTION reduceChannelsImage()                                                                                                          #
###########################################################################################################################################
def reduceChannelsImage(image_stack_input, image_acp_output, path_time_log, method_reduce, nb_components=0, normalize=True, napca_radius=1, ica_iterations=20, ica_increment=1.0, save_results_intermediate=False, overwrite=True):
    """
    # ROLE:
    #   Role : Exécuter un algorithme de type acp sur une image stacké
    #
    # ENTREES DE LA FONCTION :
    #    image_stack_input : image staké sur laquelle on exécute un algorithme acp
    #    image_acp_output : image résultat de l'acp
    #    path_time_log : le fichier de log de sortie
    #    method_reduce : choix du type de methode [PCA/NAPCA/MAF/ICA]
    #    nb_components : Nombre de composants pertinents conservés. Par défaut, tous les composants sont maintenus.
    #    normalize : Normalise, centre et réduire données avant réduction dimensionnelle, par defaut : True
    #    napca_radius : paramètre de l'algo napca, regle le rayon de la fenêtre glissante, par defaut : 1
    #    ica_iterations : paramètre de l'algo ica, nombre d'itérations, par defaut : 20
    #    ica_increment : paramètre de l'algo ica, indique le poids de l'incrément de W dans [0, 1], par defaut : 1.0
    #    save_results_intermediate : fichiers de sorties intermediaires non nettoyees, par defaut = False
    #    overwrite : boolen si vrai, ecrase les fichiers existants
    #
    # SORTIES DE LA FONCTION :
    #   Elements generes : une image
    """

    # Mise à jour du Log
    starting_event = "reduceChannelsImage() : Reduction channels starting : "
    timeLine(path_time_log,starting_event)

    print(endC)
    print(bold + green + "## START : CHANNELS REDUCTION ALGO" + endC)
    print(endC)

    # Constantes
    EXT_XML = ".xml"
    EXT_CSV = ".csv"

    # Variables locales
    output_min_value = 1
    output_max_value = 65536

    # Nom de l'image en entrée
    image_name = os.path.splitext(os.path.basename(image_acp_output))[0]
    repertory_output = os.path.dirname(image_acp_output)
    parameters_output = repertory_output + os.sep + image_name + EXT_XML
    matrix_output = repertory_output + os.sep + image_name + EXT_CSV

    if debug >= 3:
        print(bold + green + "Variables dans la fonction" + endC)
        print(cyan + "reduceChannelsImage() : " + endC + "image_stack_input : " + str(image_stack_input) + endC)
        print(cyan + "reduceChannelsImage() : " + endC + "image_acp_output : " + str(image_acp_output) + endC)
        print(cyan + "reduceChannelsImage() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "reduceChannelsImage() : " + endC + "method_reduce : " + str(method_reduce) + endC)
        print(cyan + "reduceChannelsImage() : " + endC + "nb_components : " + str(nb_components) + endC)
        print(cyan + "reduceChannelsImage() : " + endC + "normalize : " + str(normalize) + endC)
        print(cyan + "reduceChannelsImage() : " + endC + "napca_radius : " + str(napca_radius) + endC)
        print(cyan + "reduceChannelsImage() : " + endC + "ica_iterations : " + str(ica_iterations) + endC)
        print(cyan + "reduceChannelsImage() : " + endC + "ica_increment : " + str(ica_increment) + endC)
        print(cyan + "reduceChannelsImage() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "reduceChannelsImage() : " + endC + "overwrite : " + str(overwrite) + endC)

    # Si l'image acp existe deja et que overwrite n'est pas activé
    check = os.path.isfile(image_acp_output)
    if check and not overwrite:
        print(bold + yellow + "ACP image already exists and will not be calculated again." + endC)
    else:
        if check :
            try:
                removeFile(image_acp_output)
            except Exception:
                pass # si le fichier n'existe pas, il ne peut pas être supprimé : cette étape est ignorée

        # Execution de l'acp  [PCA/NAPCA/MAF/ICA]
        method_and_parametres = ""
        while switch(method_reduce):
            if case("PCA"):
                method_and_parametres = "pca"
                break
            if case("NAPCA"):
                method_and_parametres = "napca -method.napca.radiusx %d -method.napca.radiusy %d "%(napca_radius,napca_radius)
                break
            if case("MAF"):
                method_and_parametres = "maf"
                break
            if case("ICA"):
                method_and_parametres = "ica -method.ica.iter %d -method.ica.mu %f "%(ica_iterations,ica_increment)
                break
            break

        if debug >= 1:
            print(cyan + "reduceChannelsImage() : " + bold + green + "Debut de la reduction de dimension avec l'algorithme " + method_and_parametres + endC)

        if IS_VERSION_UPPER_OTB_7_0 :
            command = "otbcli_DimensionalityReduction -in %s -out %s -rescale.minmax.outmax %d -rescale.minmax.outmin %d -method %s -nbcomp %d -normalize %s -outmatrix %s" %(image_stack_input, image_acp_output, output_max_value, output_min_value, method_and_parametres, nb_components, str(normalize).lower(), matrix_output)
        else :
            command = "otbcli_DimensionalityReduction -in %s -out %s -rescale.outmax %d -rescale.outmin %d -method %s -nbcomp %d -normalize %s -outmatrix %s -outxml %s" %(image_stack_input, image_acp_output, output_max_value, output_min_value, method_and_parametres, nb_components, str(normalize).lower(), matrix_output, parameters_output)

        if debug >= 4:
            print("Execution de la commande : %s " %(command))

        exitCode = os.system(command)

        if exitCode != 0:
            print(command)
            raise NameError(cyan + "reduceChannelsImage() : " + bold + red + "An error occured during otbcli_DimensionalityReduction command. See error message above." + endC)
        if debug >= 1:
            print(cyan + "reduceChannelsImage() : " + bold + green + "Reduction de dimension terminée." + endC)

    # Nettoyage des fichiers parameters_output et matrix_output
    if not save_results_intermediate:
        if os.path.isfile(parameters_output) :
            removeFile(parameters_output)
        if os.path.isfile(matrix_output) :
            removeFile(matrix_output)

    print(endC)
    print(bold + green + "## END : CHANNELS REDUCTION ALGO" + endC)
    print(endC)

    # Mise à jour du Log
    ending_event = "reduceChannelsImage() : Reduction channels ending : "
    timeLine(path_time_log,ending_event)

    return

###########################################################################################################################################
# MISE EN PLACE DU PARSER                                                                                                                 #
###########################################################################################################################################

# Code executé seulement dans le cas ou le script est lancé depuis une ligne de commande
# Il n'est pas executé lors d'un import ChannelsConcatenation.py
# Exemple de lancement en ligne de commande:
# python ChannelsConcatenation.py -il  ../ImagesTestChaine/APTV_05/APTV_05.tif ../ImagesTestChaine/APTV_05/Neocanaux/APTV_05_chanNIR_rad6_HaralickCorrelation.tif ../ImagesTestChaine/APTV_05/Neocanaux/APTV_05_chanG_rad5_Inertia.tif ../ImagesTestChaine/APTV_05/Neocanaux/APTV_05_NDVI.tif ../ImagesTestChaine/APTV_05/Neocanaux/APTV_05_NDWI.tif -os ../ImagesTestChaine/APTV_05/Stacks/APTV_05_stack.tif -on ../ImagesTestChaine/APTV_05/Stacks/APTV_05_stack_N.tif -oa ../ImagesTestChaine/APTV_05/Stacks/APTV_05_stack_N_acp.tif -log ../ImagesTestChaine/APTV_05/fichierTestLog.txt

def main(gui=False):

    # Définition des arguments possibles pour l'appel en ligne de commande
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,  prog="ChannelsConcatenation", description="\
    Info : Concatenate one image with their neochannel. \n\
    Objectif : Concatener plusieurs bandes d'image en une seule image.\n\
    Example : python ChannelsConcatenation.py -il  ../ImagesTestChaine/APTV_05/APTV_05.tif \n\
                                                   ../ImagesTestChaine/APTV_05/Neocanaux/APTV_05_chanNIR_rad6_HaralickCorrelation.tif \n\
                                                   ../ImagesTestChaine/APTV_05/Neocanaux/APTV_05_chanG_rad5_Inertia.tif \n\
                                                   ../ImagesTestChaine/APTV_05/Neocanaux/APTV_05_NDVI.tif \n\
                                                   ../ImagesTestChaine/APTV_05/Neocanaux/APTV_05_NDWI.tif \n\
                                               -os ../ImagesTestChaine/APTV_05/Stacks/APTV_05_stack.tif \n\
                                               -on ../ImagesTestChaine/APTV_05/Stacks/APTV_05_stack_N.tif \n\
                                               -oa ../ImagesTestChaine/APTV_05/Stacks/APTV_05_stack_N_acp.tif \n\
                                               -log ../ImagesTestChaine/APTV_05/fichierTestLog.txt")

    # Paramètres
    parser.add_argument('-il','--images_input_list',default="",nargs="*",help="List images input to stack", type=str, required=True)
    parser.add_argument('-os','--image_stack_output',default="",help="Image output of stack image", type=str, required=False)
    parser.add_argument('-code','--code',default="",help="Encoding image output of stack image", type=str, required=False)
    parser.add_argument('-on','--image_normalize_output',default="",help="Image output of normalize image", type=str, required=False)
    parser.add_argument('-oa','--image_acp_output',default="",help="Image output of reduce acp image", type=str, required=False)
    parser.add_argument('-redce.meth','--method_reduce',default="PCA",help="Parameter reduction, name methode to reduce concatened image (choice : [PCA/NAPCA/MAF/ICA]). By default : PCA", type=str, required=False)
    parser.add_argument('-redce.nbcp','--nb_components',default=0,help="Parameter reduction, number of components. By default : all components", type=int, required=False)
    parser.add_argument('-redce.radi','--napca_radius',default=1,help="Parameter reduction, algo napca the x and y radius of the sliding window. By default : 1", type=int, required=False)
    parser.add_argument('-redce.iter','--ica_iterations',default=20,help="Parameter reduction, algo ica number of iterations. By default : 20", type=int, required=False)
    parser.add_argument('-redce.incr','--ica_increment',default=1.0,help="Parameter reduction, algo ica the increment weight of W in [0, 1]. By default : 1.0", type=float, required=False)
    parser.add_argument('-redce.norm','--normalization_reduce',action='store_true',default=False,help="Apply normalization or not to reduced image. By default, False", required=False)
    parser.add_argument('-log','--path_time_log',default="",help="Name of log", type=str, required=False)
    parser.add_argument('-sav','--save_results_inter',action='store_true',default=False,help="Save or delete intermediate result after the process. By default, False", required=False)
    parser.add_argument('-now','--overwrite',action='store_false',default=True,help="Overwrite files with same names. By default, True", required=False)
    parser.add_argument('-debug','--debug',default=3,help="Option : Value of level debug trace, default : 3 ",type=int, required=False)
    args = displayIHM(gui, parser)

    # RECUPERATION DES ARGUMENTS

    # Récupération de la liste des images à stacker
    if args.images_input_list != None :
        images_input_list = args.images_input_list
        for image_input in images_input_list :
            if not os.path.isfile(image_input):
                raise NameError (cyan + "ChannelsConcatenation : " + bold + red  + "File %s not existe!" %(image_input) + endC)

    # Récupération des images de sortie
    if args.image_stack_output != None:
        image_stack_output = args.image_stack_output

    if args.code != None:
        code = args.code

    if args.image_normalize_output != None:
        image_normalize_output = args.image_normalize_output

    if args.image_acp_output != None:
        image_acp_output = args.image_acp_output

    # Les paramètres des acp
    if args.method_reduce != None:
        method_reduce = args.method_reduce
        if method_reduce.upper() not in ['PCA', 'NAPCA', 'MAF', 'ICA', ''] :
            raise NameError(cyan + "ChannelsConcatenation : " + bold + red + "Parameter 'method_reduce' value  is not in list ['PCA', 'NAPCA', 'MAF', 'ICA', '']." + endC)

    if args.nb_components != None:
        nb_components = args.nb_components

    if args.napca_radius != None:
        napca_radius = args.napca_radius

    if args.ica_iterations != None:
        ica_iterations = args.ica_iterations

    if args.ica_increment != None:
        ica_increment = args.ica_increment

    if args.normalization_reduce!= None:
        normalization_reduce = args.normalization_reduce

    # Récupération du nom du fichier log
    if args.path_time_log!= None:
        path_time_log = args.path_time_log

    if args.save_results_inter != None:
        save_results_intermediate = args.save_results_inter

    if args.overwrite!= None:
        overwrite = args.overwrite

    # Récupération de l'option niveau de debug
    if args.debug!= None:
        global debug
        debug = args.debug

    if debug >= 3:
        print(cyan + "ChannelsConcatenation : " + bold + green + "Variables dans le parser" + endC)
        print(cyan + "ChannelsConcatenation : " + endC + "images_input_list : " + str(images_input_list) + endC)
        print(cyan + "ChannelsConcatenation : " + endC + "image_stack_output : " + str(image_stack_output) + endC)
        print(cyan + "ChannelsConcatenation : " + endC + "code : " + str(code) + endC)
        print(cyan + "ChannelsConcatenation : " + endC + "image_normalize_output : " + str(image_normalize_output) + endC)
        print(cyan + "ChannelsConcatenation : " + endC + "image_acp_output : " + str(image_acp_output) + endC)
        print(cyan + "ChannelsConcatenation : " + endC + "method_reduce : " + str(method_reduce) + endC)
        print(cyan + "ChannelsConcatenation : " + endC + "nb_components : " + str(nb_components) + endC)
        print(cyan + "ChannelsConcatenation : " + endC + "napca_radius : " + str(napca_radius) + endC)
        print(cyan + "ChannelsConcatenation : " + endC + "ica_iterations : " + str(ica_iterations) + endC)
        print(cyan + "ChannelsConcatenation : " + endC + "ica_increment : " + str(ica_increment) + endC)
        print(cyan + "ChannelsConcatenation : " + endC + "normalization_reduce : " + str(normalization_reduce) + endC)
        print(cyan + "ChannelsConcatenation : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "ChannelsConcatenation : " + endC + "save_results_inter : " + str(save_results_intermediate) + endC)
        print(cyan + "ChannelsConcatenation : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "ChannelsConcatenation : " + endC + "debug : " + str(debug) + endC)

    # EXECUTION DE LA FONCTION
    concatenation = False
    normalization = False
    reduction = False

    # Si les dossiers de sortie n'existent pas, on les crées
    if image_stack_output != "":
        concatenation = True
        repertory_output = os.path.dirname(image_stack_output)
        if not os.path.isdir(repertory_output):
            os.makedirs(repertory_output)

    if image_normalize_output != "":
        normalization = True
        repertory_output = os.path.dirname(image_normalize_output)
        if not os.path.isdir(repertory_output):
            os.makedirs(repertory_output)

    if image_acp_output != "":
        reduction = True
        repertory_output = os.path.dirname(image_acp_output)
        if not os.path.isdir(repertory_output):
            os.makedirs(repertory_output)

    # Exécution de la concatenation pour une image
    if concatenation :
        concatenateChannels(images_input_list, image_stack_output, path_time_log, code, save_results_intermediate, overwrite)
    else :
        image_stack_output = images_input_list[0]

    # Si la normalisation de l'empilement est activee on enchaine directement avec la fonction normalizeChannels
    if normalization :
        normalizeChannels(image_stack_output, image_normalize_output, path_time_log, save_results_intermediate, overwrite)
    else :
        image_normalize_output = image_stack_output

    # Si la réduction de l'image stacké est activee
    if reduction :
        reduceChannelsImage(image_normalize_output, image_acp_output, path_time_log, method_reduce, nb_components, normalization_reduce, napca_radius, ica_iterations, ica_increment, save_results_intermediate, overwrite)

# ================================================

if __name__ == '__main__':
  main(gui=False)
