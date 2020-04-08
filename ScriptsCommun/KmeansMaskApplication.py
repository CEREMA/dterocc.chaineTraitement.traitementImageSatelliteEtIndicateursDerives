#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerSO/DALETT/SCGSI  All rights reserved.                                                                            #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT QUI APPLIQUE UNE CLASSIFICATION NON SUPERVISEE KMEANS                                                                              #
#                                                                                                                                           #
#############################################################################################################################################
'''
Nom de l'objet : KmeansMaskApplication.py
Description :
    Objectif : Gérer les superpositions des fichiers rasters de classes macro d'entrées
               Puis réaliser une classification non supervisé par algorithme de kmeans
    Rq : utilisation des OTB Applications : otbcli_KMeansClassification, otbcli_BandMath

Date de creation : 31/07/2014
----------
Histoire :
----------
Origine : le script originel provient du fichier Chain4_MicroclassesComputation.py cree en 2013 et utilise par la chaine de traitement OCSOL V1.X
31/07/2014 : Transformation en brique elementaire (suppression des liens avec la chaine OCSOL)
-----------------------------------------------------------------------------------------------------
Modifications
01/10/2014 : refonte du fichier harmonisation des régles de qualitées des niveaux de boucles et des paramétres dans args
21/05/2015 : simplification des parametres en argument plus de liste d'image en emtrée à traiter uniquement une image
------------------------------------------------------
A Reflechir/A faire
 -
 -
'''

from __future__ import print_function
import os,sys,glob,argparse,string,shutil,threading
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_text import writeTextFile, appendTextFileCR
from Lib_file import removeFile, removeDir
from Lib_log import timeLine
from Lib_raster import countPixelsOfValue, updateReferenceProjection, reallocateClassRaster, deletePixelsSuperpositionMasks, mergeListRaster, identifyPixelValues, updateReferenceProjection

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 3

# Les parametres de la fonction OTB otbcli_KMeansClassification a changé à partir de la version 7.0 de l'OTB
IS_VERSION_UPPER_OTB_7_0 = True
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

###########################################################################################################################################
# FONCTION applyKmeansMasks()                                                                                                             #
###########################################################################################################################################
# ROLE:
#     classification non supervisee par algorithme de Kmeans
#     Compléments sur la fonction KMeans : http://www.orfeo-toolbox.org/SoftwareGuide/SoftwareGuidech19.html
#     Compléments sur la fonction KMeans : http://www.orfeo-toolbox.org/CookBook/CookBooksu116.html#x150-8480005.8.6
#
# ENTREES DE LA FONCTION :
#     image_input : Image d'entree pour laquelle on va faire un kmeans
#     mask_samples_macro_input_list : Liste des images d'entrées contenant les echantillons macro
#     image_samples_merged_output : image de sortie resultat de la fusion de toutes les echantillons micro de toutes les micro classes
#     proposal_table_output : fichier texte de proposition de realocation (suppression)
#     micro_samples_images_output_list : Liste des images de sortie masquées
#     centroids_files_output_list : Liste des fichier contenant les coordonnées des centroides
#     macroclass_sampling_list: Liste du nombre de classes par masque défini par mask_list. Exemple :  [3, 5]
#     macroclass_labels_list : Liste des labels de classes associées à chaque masque. Exemple : [11000, 12000]
#     no_data_value : Valeur de  pixel du no data
#     path_time_log : le fichier de log de sortie
#     kmeans_parameters : Parametres du kmeans = [nb_iterations, seuil convergence, prop pixels du masque retenus, taille jeu entrainement]. Par exemple : kmeans_parameters = [2000,0.0001,1,-1]
#     kmeans_param_maximum_iterations : Parametre du kmeans, nombre maximal d'itérations du KMeans, defaut=2000
#     kmeans_param_training_set_size_weight : Parametre du kmeans, proportion de pixels du masque retenus pour le KMeans, defaut=1
#     kmeans_param_minimum_training_set_size : Parametre du kmeans, taille en pixels du jeu d'entrainement pris à chaque itération, defaut=-1
#     rate_clean_micro_class : ratio pour le nettoyage des micro classes dont la somme total des surfaces est trop petites
#     rand_otb : graine pour la partie randon de l'ago de KMeans
#     ram_otb : memoire RAM disponible pour les applications OTB
#     number_of_actives_pixels_threshold : Nombre minimum de pixels de formation pour le kmeans. Par défaut = 7000
#     extension_raster : extension des fichiers raster de sortie, par defaut = '.tif'
#     save_results_intermediate : liste des sorties intermediaires nettoyees, par defaut = False
#     overwrite : écrase si un fichier existant a le même nom qu'un fichier de sortie, par defaut a True
#
# SORTIES DE LA FONCTION :
#     Les images issues du kmeans sont dans path_output_kmeans
#
def applyKmeansMasks(image_input, mask_samples_macro_input_list, image_samples_merged_output, proposal_table_output, micro_samples_images_output_list, centroids_files_output_list, macroclass_sampling_list, macroclass_labels_list, no_data_value, path_time_log, kmeans_param_maximum_iterations=200, kmeans_param_training_set_size_weight=1, kmeans_param_minimum_training_set_size=-1, rate_clean_micro_class=0.0, rand_otb=0, ram_otb=0, number_of_actives_pixels_threshold=200, extension_raster=".tif", save_results_intermediate=False, overwrite=True):

    # Mise à jour du Log
    starting_event = "applyKmeansMasks() : Kmeans and mask starting : "
    timeLine(path_time_log,starting_event)

    print(endC)
    print(cyan + "applyKmeansMasks() : " + bold + green + "## START : SUBSAMPLING OF " + str(macroclass_labels_list) + endC)
    print(endC)

    if debug >= 2:
        print(cyan + "applyKmeansMasks() : variables dans la fonction" + endC)
        print(cyan + "applyKmeansMasks() : " + endC + "image_input : " + str(image_input) + endC)
        print(cyan + "applyKmeansMasks() : " + endC + "image_samples_merged_output : " + str(image_samples_merged_output) + endC)
        print(cyan + "applyKmeansMasks() : " + endC + "proposal_table_output : " + str(proposal_table_output) + endC)
        print(cyan + "applyKmeansMasks() : " + endC + "mask_samples_macro_input_list : " + str(mask_samples_macro_input_list) + endC)
        print(cyan + "applyKmeansMasks() : " + endC + "micro_samples_images_output_list : " + str(micro_samples_images_output_list) + endC)
        print(cyan + "applyKmeansMasks() : " + endC + "centroids_files_output_list : " + str(centroids_files_output_list) + endC)
        print(cyan + "applyKmeansMasks() : " + endC + "macroclass_sampling_list : " + str(macroclass_sampling_list) + endC)
        print(cyan + "applyKmeansMasks() : " + endC + "macroclass_labels_list : " + str(macroclass_labels_list) + endC)
        print(cyan + "applyKmeansMasks() : " + endC + "kmeans_param_maximum_iterations : " + str(kmeans_param_maximum_iterations) + endC)
        print(cyan + "applyKmeansMasks() : " + endC + "kmeans_param_training_set_size_weight : " + str(kmeans_param_training_set_size_weight) + endC)
        print(cyan + "applyKmeansMasks() : " + endC + "kmeans_param_minimum_training_set_size : " + str(kmeans_param_minimum_training_set_size) + endC)
        print(cyan + "applyKmeansMasks() : " + endC + "rate_clean_micro_class : " + str(rate_clean_micro_class))
        print(cyan + "applyKmeansMasks() : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "applyKmeansMasks() : " + endC + "rand_otb : " + str(rand_otb) + endC)
        print(cyan + "applyKmeansMasks() : " + endC + "ram_otb : " + str(ram_otb) + endC)
        print(cyan + "applyKmeansMasks() : " + endC + "number_of_actives_pixels_threshold : " + str(number_of_actives_pixels_threshold))
        print(cyan + "applyKmeansMasks() : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "applyKmeansMasks() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "applyKmeansMasks() : " + endC + "overwrite : " + str(overwrite) + endC)

    # constantes
    HEADER_TABLEAU_MODIF = "MICROCLASSE;TRAITEMENT\n"

    CODAGE_16B = "uint16"
    CODAGE_8B = "uint8"
    EXT_XML = ".xml"

    SUFFIX_MASK_CLEAN = "_clean"
    SUFFIX_SAMPLE_MICRO = "_sample_micro"
    SUFFIX_STATISTICS = "_statistics"
    SUFFIX_CENTROID = "_centroid"
    SUFFIX_MASK_TEMP = "_tmp"

   # Creation des fichiers temporaires de sortie si ils ne sont pas spécifier
   #-------------------------------------------------------------------------

    length_mask = len(mask_samples_macro_input_list)
    images_mask_cleaned_list = []
    temporary_files_list = []
    micro_samples_images_list = []
    centroids_files_list = []
    repertory_output_tmp_list = []

    if image_samples_merged_output != "" :
        repertory_base_output = os.path.dirname(image_samples_merged_output)
        filename = os.path.splitext(os.path.basename(image_samples_merged_output))[0]
    else :
        repertory_base_output = os.path.dirname(micro_samples_images_output_list[0])
        filename = os.path.splitext(os.path.basename(micro_samples_images_output_list[0]))[0]

    file_statistic_points = repertory_base_output + os.sep + filename + SUFFIX_STATISTICS + EXT_XML

    for macroclass_id in range(length_mask):

        repertory_output = repertory_base_output + os.sep + str(macroclass_labels_list[macroclass_id])
        if not os.path.isdir(repertory_output):
            os.makedirs(repertory_output)
        repertory_output_tmp_list.append(repertory_output)
        samples_image_input = mask_samples_macro_input_list[macroclass_id]
        filename = os.path.splitext(os.path.basename(samples_image_input))[0]
        image_mask_cleaned =  repertory_output + os.sep + filename + SUFFIX_MASK_CLEAN + extension_raster
        images_mask_cleaned_list.append(image_mask_cleaned)
        image_tmp =  repertory_output + os.sep + filename + SUFFIX_MASK_TEMP + extension_raster
        temporary_files_list.append(image_tmp)
        if micro_samples_images_output_list == [] :
            micro_samples_image = repertory_output + os.sep + filename + SUFFIX_SAMPLE_MICRO + extension_raster
        else :
            micro_samples_image = micro_samples_images_output_list[macroclass_id]
        micro_samples_images_list.append(micro_samples_image)
        if centroids_files_output_list == [] :
            centroids_file = repertory_output + os.sep + filename + SUFFIX_CENTROID + extension_raster
        else :
            centroids_file = centroids_files_output_list[macroclass_id]
        centroids_files_list.append(centroids_file)

    # Nettoyage des pixels superposés sur plusieurs images
    #-----------------------------------------------------

    if length_mask > 1:
        image_name = os.path.splitext(os.path.basename(image_input))[0]
        deletePixelsSuperpositionMasks(mask_samples_macro_input_list, images_mask_cleaned_list, image_name, CODAGE_8B)
    else:
        images_mask_cleaned_list = mask_samples_macro_input_list

    # Execution du kmeans pour chaque macroclasse
    #--------------------------------------------

    # Initialisation de la liste pour le multi-threading
    thread_list = []

    for macroclass_id in range(length_mask):

        mask_sample_input = images_mask_cleaned_list[macroclass_id]
        micro_samples_image = micro_samples_images_list[macroclass_id]
        image_tmp = temporary_files_list[macroclass_id]
        centroids_file = centroids_files_list[macroclass_id]
        check = os.path.isfile(micro_samples_image)

        if check and not overwrite : # Si un fichier de sortie avec le même nom existe déjà, et si l'option ecrasement est à false, alors passe à la classification suivante
            print(cyan + "applyKmeansMasks() : " + bold + yellow +  "Computing kmeans from %s with %s already done : no actualisation" % (image_input, mask_sample_input) + endC)

        else:            # Si non, on applique un kmeans

            if check :
                removeFile(micro_samples_image)   # Suppression de l'éventuel fichier existant

            print(cyan + "applyKmeansMasks() : " + bold + green + "Computing kmeans from %s with %s ; output image is %s" %(image_input, mask_sample_input,micro_samples_image) + endC)

            # Obtention du nombre de microclasses
            number_of_classes = macroclass_sampling_list[macroclass_id]   # Nombre de microclasses
            label = macroclass_labels_list[macroclass_id]                 # Label de la macroclasse Ex : 11000

            # Gestion du multi threading pour l'appel du calcul du kmeans
            thread = threading.Thread(target=computeKmeans, args=(image_input, mask_sample_input, image_tmp, micro_samples_image, centroids_file, label, number_of_classes, macroclass_id, number_of_actives_pixels_threshold, kmeans_param_minimum_training_set_size, kmeans_param_maximum_iterations, length_mask, no_data_value, rand_otb, int(ram_otb/length_mask), CODAGE_8B, CODAGE_16B, save_results_intermediate, overwrite))
            thread.start()
            thread_list.append(thread)

    # Start Kmeans all macro classes
    try:
        for thread in thread_list:
            thread.join()
    except:
        print(cyan + "applyKmeansMasks() : " + bold + red + "applyKmeansMasks() : " + endC + "Erreur lors du calcul du kmeans : impossible de demarrer le thread" + endC, file=sys.stderr)

    # Fusion des echantillons micro
    #------------------------------
    if image_samples_merged_output != "" :

        mergeListRaster(micro_samples_images_list, image_samples_merged_output, CODAGE_16B)
        updateReferenceProjection(image_input, image_samples_merged_output)

        # Creation de la table de proposition et le fichier statistique
        #--------------------------------------------------------------
        if proposal_table_output != "" :

            suppress_micro_class_list = []
            info_micoclass_nbpoints_dico = {}
            nb_points_total = 0
            nb_points_medium = 0

            # Liste des identifants des micro classes disponibles
            id_micro_list = identifyPixelValues(image_samples_merged_output)
            if 0 in id_micro_list :
                id_micro_list.remove(0)
            nb_micr_class = len(id_micro_list)

            # Pour toutes les micro classes
            for id_micro in id_micro_list :
                nb_pixels = countPixelsOfValue(image_samples_merged_output, id_micro)

                info_micoclass_nbpoints_dico[id_micro] = nb_pixels
                nb_points_total += nb_pixels

            # Valeur moyenne de nombre de points
            if nb_micr_class != 0 :
                nb_points_medium = int(nb_points_total / nb_micr_class)
            nb_points_min = int((nb_points_medium * rate_clean_micro_class) / 100)

            # Identifier les micro classes trop petites
            if debug >= 4:
                print("rate_clean_micro_class = " + str(rate_clean_micro_class))
                print("nb_points_medium = " + str(nb_points_medium))
                print("nb_points_min = " + str(nb_points_min))

            # Preparation du fichier statistique
            writeTextFile(file_statistic_points, '<?xml version="1.0" ?>\n')
            appendTextFileCR(file_statistic_points, '<GeneralStatistics>')
            appendTextFileCR(file_statistic_points, '    <Statistic name="pointsPerClassRaw">')

            for micro_class_id in info_micoclass_nbpoints_dico :
                nb_points = info_micoclass_nbpoints_dico[micro_class_id]
                if debug >= 4:
                    print("micro_class_id = " + str(micro_class_id) + ", nb_points = " + str(nb_points))
                appendTextFileCR(file_statistic_points, '        <StatisticPoints class="%d" value="%d" />' %(micro_class_id, nb_points))

                if nb_points < nb_points_min :
                    # Micro_class à proposer en effacement
                    suppress_micro_class_list.append(micro_class_id)

            # Fin du fichier statistique
            appendTextFileCR(file_statistic_points, '    </Statistic>')
            appendTextFileCR(file_statistic_points, '</GeneralStatistics>')

            # Test si ecrassement de la table précédemment créée
            check = os.path.isfile(proposal_table_output)
            if check and not overwrite :
                print(cyan + "applyKmeansMasks() : " + bold + yellow + "Modifier table already exists." + '\n' + endC)
            else:
                # Tenter de supprimer le fichier
                try:
                    removeFile(proposal_table_output)
                except Exception:
                    pass   # Ignore l'exception levee si le fichier n'existe pas (et ne peut donc pas être supprime)
                # lister les micro classes à supprimer
                text_output = HEADER_TABLEAU_MODIF

                for micro_class_del in suppress_micro_class_list:
                    text_output += "%d;-1\n" %(micro_class_del)

                # Ecriture du fichier proposition de réaffectation
                writeTextFile(proposal_table_output, text_output)

    # Suppresions fichiers intermediaires inutiles
    #---------------------------------------------

    if not save_results_intermediate:
        for macroclass_id in range(length_mask):
            if (os.path.isfile(temporary_files_list[macroclass_id])) :
                removeFile(temporary_files_list[macroclass_id])

            if (length_mask > 1) and (os.path.isfile(images_mask_cleaned_list[macroclass_id])) :
                removeFile(images_mask_cleaned_list[macroclass_id])

            if (micro_samples_images_output_list == []) and (os.path.isfile(micro_samples_images_list[macroclass_id])) :
                removeFile(micro_samples_images_list[macroclass_id])

            if (centroids_files_output_list == []) and (os.path.isfile(centroids_files_list[macroclass_id])) :
                removeFile(centroids_files_list[macroclass_id])

            if os.path.isdir(repertory_output_tmp_list[macroclass_id]) :
                removeDir(repertory_output_tmp_list[macroclass_id])

    print(cyan + "applyKmeansMasks() : " + bold + green + "## END : KMEANS CLASSIFICATION" + endC)
    print(endC)

    # Mise à jour du Log
    ending_event = "applyKmeansMasks() : Kmeans and mask ending : "
    timeLine(path_time_log,ending_event)

    return

###########################################################################################################################################
# FONCTION computeKmeans()                                                                                                                #
###########################################################################################################################################
# ROLE:
#     Calcul le kmeans sur une image macro
#
# ENTREES DE LA FONCTION :
#     image_input : image de macroclasse d'entrée .tif
#     mask_sample_input : masque echantillons macro
#     image_output : image de sortie en micro classes
#     micro_samples_image_out : sample micro de sortie
#     centroids_file_output : fichier des centroides de sortie
#     label : label de la classs
#     number_of_classes : nombre de micro classe demandées
#     macroclass_id : identifiant de la macro classe
#     number_of_actives_pixels_threshold : seuil du nombre de pixels actifs
#     kmeans_param_minimum_training_set_size : parametre training size du kmeans
#     kmeans_param_maximum_iterations : parametre maximum iterations du kmeans
#     length_mask : nombre de masque macro
#     no_data_value : Valeur de  pixel du no data
#     rand_otb : graine pour la partie randon de l'ago de KMeans
#     ram_otb : memoire RAM disponible pour les applications OTB
#     codage_8b : codage application otb sortie en 8bits
#     codage_16b : codage application otb sortie en 16bits
#     save_results_intermediate : fichiers de sorties intermediaires nettoyees, par defaut = False
#     overwrite : écrase si un fichier existant a le même nom qu'un fichier de sortie, par defaut a True

# SORTIES DE LA FONCTION :
#     Vecteur polygonisé
#
def computeKmeans(image_input, mask_sample_input, image_output, micro_samples_image_out, centroids_file_output, label, number_of_classes, macroclass_id, number_of_actives_pixels_threshold, kmeans_param_minimum_training_set_size, kmeans_param_maximum_iterations, length_mask, no_data_value, rand_otb, ram_otb, codage_8b, codage_16b, save_results_intermediate=False, overwrite=True):

    # ETAPE 0 : PREPARATION


    if debug >= 4:
        print(cyan + "computeKmeans() : " + endC + "image : " + str(image_input) + endC)
        print(cyan + "computeKmeans() : " + endC + "label : " + str(label) + endC)
        print(cyan + "computeKmeans() : " + endC + "number_of_classes : " + str(number_of_classes) + endC)
        print(cyan + "computeKmeans() : " + endC + "macroclass_id : " + str(macroclass_id) + endC)
        print(cyan + "computeKmeans() : " + endC + "mask_sample_input : " + str(mask_sample_input) + endC)
        print(cyan + "computeKmeans() : " + endC + "image_output : " + str(image_output) + endC)
        print(cyan + "computeKmeans() : " + endC + "micro_samples_image_out : " + str(micro_samples_image_out) + endC)
        print(cyan + "computeKmeans() : " + endC + "centroids_file_output : " + str(centroids_file_output) + endC)
        print(cyan + "computeKmeans() : " + endC + "kmeans_param_minimum_training_set_size : " + str(training_set_size) + endC)
        print(cyan + "computeKmeans() : " + endC + "number_of_classes : " + str(number_of_classes) + endC)
        print(cyan + "computeKmeans() : " + endC + "kmeans_param_maximum_iterations : " + str(kmeans_param_maximum_iterations) + endC)
        print(cyan + "computeKmeans() : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "computeKmeans() : " + endC + "rand_otb : " + str(rand_otb) + endC)
        print(cyan + "computeKmeans() : " + endC + "ram_otb : " + str(ram_otb) + endC)
        print(cyan + "computeKmeans() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "computeKmeans() : " + endC + "overwrite : " + str(overwrite) + endC)

    # kmeans_param_minimum_training_set_size ?
    if kmeans_param_minimum_training_set_size == -1:
        # Le nombre de pixels d'apprentissage correspond au nombre de pixels à 1 du masque "mask_sample_input"
        training_set_size = countPixelsOfValue(mask_sample_input, 1)
    else :
        training_set_size = kmeans_param_minimum_training_set_size


    # ETAPE 1 : CLASSIFICATION NON SUPERVISEE

    # Cas où il y a moins de pixels disponibles pour effectuer le kmeans que le seuil
    if training_set_size < (number_of_classes * number_of_actives_pixels_threshold) :

        print(cyan + "computeKmeans() : " + bold + yellow + "MACROCLASSE %s / %s (%s): Nombre insuffisant de pixels disponibles pour appliquer le kmeans : %s sur %s requis au minimum " %(macroclass_id, length_mask, label, training_set_size, number_of_classes * number_of_actives_pixels_threshold) + endC)
        if debug >= 2:
            print(cyan + "computeKmeans() : " + bold + yellow + "MACROCLASSE %s / %s : SOUS ECHANTILLONAGE NON APPLIQUE A LA CLASSE %s" %(macroclass_id + 1, length_mask, label) + endC)
            print(cyan + "computeKmeans() : " + bold + yellow + "MACROCLASSE %s / %s : COPIE DE %s A %s" %(macroclass_id + 1, length_mask, mask_sample_input, micro_samples_image_out) + endC + "\n")

        # Recopie de fichier d'entré mask
        shutil.copy2(mask_sample_input, image_output)

    else: # Cas où il y a suffisamment de pixels pour effectuer le kmeans

        if centroids_file_output != None: # Distinction des cas avec et sans coordonnees des centroides

            command = "otbcli_KMeansClassification -in %s -out %s %s -vm %s -ts %s -nc %s -maxit %s" %(image_input, image_output, codage_8b, mask_sample_input, training_set_size, number_of_classes, kmeans_param_maximum_iterations)

            if IS_VERSION_UPPER_OTB_7_0 :
                command += " -centroids.out %s " %(centroids_file_output)
            else :
                command += " -outmeans %s " %(centroids_file_output)

            if no_data_value != 0:
                command += " -nodatalabel %d" %(no_data_value)
            if rand_otb > 0:
                command += " -rand %d" %(rand_otb)
            if ram_otb > 0:
                command += " -ram %d" %(ram_otb)

            if debug >=3:
                print(cyan + "computeKmeans() : " + bold + green + "MACROCLASSE %s / %s (%s): ETAPE 1 : Nombre suffisant de pixels disponibles  %s sur %s requis au minimum " %(macroclass_id + 1, length_mask, label, training_set_size, number_of_classes * number_of_actives_pixels_threshold) + endC)
            if debug >=2:
                print(cyan + "computeKmeans() : " + bold + green + "MACROCLASSE %s / %s (%s): ETAPE 1 : Computing kmeans from %s " %(macroclass_id + 1, length_mask, label, image_input) + endC)
                print(cyan + "computeKmeans() : " + bold + green + "Mask : %s " %(mask_sample_input) + endC)
                print(cyan + "computeKmeans() : " + bold + green + "Output image : %s" %(micro_samples_image_out) + endC)
                print(command)

            exitCode = os.system(command)

            if exitCode != 0:
                raise NameError(cyan + "computeKmeans() : " + bold + red + "An error occured during otbcli_KMeansClassification command. See error message above." + endC)

        else :

            command = "otbcli_KMeansClassification -in %s -out %s %s -vm %s -ts %s -nc %s -maxit %s" %(image_input, image_output, codage_8b, mask_sample_input, str(training_set_size), str(number_of_classes), str(kmeans_param_maximum_iterations))

            if no_data_value != 0:
                command += " -nodatalabel %d" %(no_data_value)
            if rand_otb > 0:
                command += " -rand %d" %(rand_otb)
            if ram_otb > 0:
                command += " -ram %d" %(ram_otb)

            if debug >=2:
                print(cyan + "computeKmeans() : " + bold + green + "MACROCLASSE %s / %s (%s): ETAPE 1 : Computing kmeans from %s with %s ; output image is %s" %(macroclass_id + 1, length_mask,label,image_input, mask_sample_input,micro_samples_image_out) + endC)
                print(command)

            exitCode = os.system(command)

            if exitCode != 0:
                raise NameError(cyan + "computeKmeans() : " + bold + red + "An error occured during otbcli_KMeansClassification command. See error message above." + endC)

    # ETAPE 2 : GESTION DU SYSTEME DE PROJECTION
    if debug >=2:
        print(cyan + "computeKmeans() : " + bold + green + "MACROCLASSE %s / %s (%s): ETAPE 2 : GESTION DU SYSTEME DE PROJECTION" %(macroclass_id + 1, length_mask, label) + endC)

    updateReferenceProjection (image_input, image_output)

    # ETAPE 3 : APPLICATION DU MASQUE ET LABELLISATION EN MICROCLASSES
    expression = "\"(im1b1+%s)*im2b1\"" %(str(label)) # Expression qui passe à 0 les pixels masqués et qui labelise à macroclass_label+classe du computeKmeans

    command = "otbcli_BandMath -il %s %s -out %s %s -exp %s" %(image_output, mask_sample_input, micro_samples_image_out, codage_16b, expression)

    if ram_otb > 0:
                command += " -ram %d" %(ram_otb)

    if debug >=2:
        print(cyan + "computeKmeans() : " + bold + green + "MACROCLASSE %s / %s (%s): ETAPE 3 : APPLICATION DU MASQUE ET LABELLISATION EN MICROCLASSES" %(macroclass_id + 1, length_mask,label) + endC)
        print(command)

    exitCode = os.system(command)

    if exitCode != 0:
        print(command)
        raise NameError(cyan + "computeKmeans() : " + bold + red + "An error occured during otbcli_BandMath command. See error message above." + endC)

    return

###########################################################################################################################################
# MISE EN PLACE DU PARSER                                                                                                                 #
###########################################################################################################################################

# Code executé seulement dans le cas ou le script est lancé depuis une ligne de commande, il n'est pas executé lors d'un import KmeansMaskApplication.py
# Exemple de lancement en ligne de commande:
# python KmeansMaskApplication.py -i ../ImagesTestChaine/APTV_05/Stacks/APTV_05_stack_N.tif -o ../ImagesTestChaine/APTV_05/Micro/APTV_05_micro_merge.tif -t ../ImagesTestChaine/APTV_05/Micro/APTV_05_prop_tab.txt -ml ../ImagesTestChaine/APTV_05/Macro/APTV_05_Anthropise_mask_cleaned.tif ../ImagesTestChaine/APTV_05/Macro/APTV_05_Eau_mask_cleaned.tif ../ImagesTestChaine/APTV_05/Macro/APTV_05_Ligneux_mask_cleaned.tif -ol ../ImagesTestChaine/APTV_05/Micro/APTV_05_Anthropise_masqued_micro.tif ../ImagesTestChaine/APTV_05/Micro/APTV_05_Eau_masqued_micro.tif ../ImagesTestChaine/APTV_05/Micro/APTV_05_Ligneux_masqued_micro.tif -cl ../ImagesTestChaine/APTV_05/Micro/APTV_05_Anthropise_micro_centroid.txt ../ImagesTestChaine/APTV_05/Micro/APTV_05_Eau_micro_centroid.txt ../ImagesTestChaine/APTV_05/Micro/APTV_05_Ligneux_micro_centroid.txt -msl 3 5 5 -mll 11000 12200 21000 -log ../ImagesTestChaine/APTV_05/fichierTestLog.log -sav
# python KmeansMaskApplication.py -i /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/Stacks/CUB_zone_test_NE_stack_N.tif -o /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/Micro/APTV_05_micro_merge.tif -t ../ImagesTestChaine/APTV_05/Micro/APTV_05_prop_tab.txt -ml /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/Macro/CUB_zone_test_NE_Bati_mask_cleaned.tif /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/Macro/CUB_zone_test_NE_Route_mask_cleaned.tif /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/Macro/CUB_zone_test_NE_Eau_mask_cleaned.tif /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/Macro/CUB_zone_test_NE_Solnu_mask_cleaned.tif /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/Macro/CUB_zone_test_NE_Vegetation_mask_cleaned.tif -ol /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/Micro/CUB_zone_test_NE_Bati_masqued_micro.tif /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/Micro/CUB_zone_test_NE_Route_masqued_micro.tif /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/Micro/CUB_zone_test_NE_Eau_masqued_micro.tif /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/Micro/CUB_zone_test_NE_Solnu_masqued_micro.tif /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/Micro/CUB_zone_test_NE_Vegetation_masqued_micro.tif -cl /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/Micro/CUB_zone_test_NE_Bati_centroid.txt /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/Micro/CUB_zone_test_NE_Route_centroid.txt /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/Micro/CUB_zone_test_NE_Eau_centroid.txt /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/Micro/CUB_zone_test_NE_Solnu_centroid.txt /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/Micro/CUB_zone_test_NE_Vegetation_centroid.txt -msl 10 10 6 6 10 -mll 11100 11200 12200 13000 20000 -log /mnt/hgfs/Data_Image_Saturn/CUB_zone_test_NE_1/CUB_zone_test_NE_1.log -sav


def main(gui=False):

    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, prog="KmeansMaskApplication", description="\
    Info : Apply a not supervised classification KMeans. \n\
    Documentation : http://www.orfeo-toolbox.org/SoftwareGuide/SoftwareGuidech19.html \n\
    Objectif : Realiser une classification non supervise par algorithme de kmeans. \n\
    Example : python KmeansMaskApplication.py -i ../ImagesTestChaine/APTV_05/Stacks/APTV_05_stack_N.tif \n\
                                              -o ../ImagesTestChaine/APTV_05/Micro/APTV_05_micro_merge.tif \n\
                                              -t ../ImagesTestChaine/APTV_05/Micro/APTV_05_prop_tab.txt \n\
                                              -ml ../ImagesTestChaine/APTV_05/Macro/APTV_05_Anthropise_mask_cleaned.tif \n\
                                                  ../ImagesTestChaine/APTV_05/Macro/APTV_05_Eau_mask_cleaned.tif \n\
                                                  ../ImagesTestChaine/APTV_05/Macro/APTV_05_Ligneux_mask_cleaned.tif \n\
                                              -ol ../ImagesTestChaine/APTV_05/Micro/APTV_05_Anthropise_masqued_micro.tif \n\
                                                  ../ImagesTestChaine/APTV_05/Micro/APTV_05_Eau_masqued_micro.tif \n\
                                                  ../ImagesTestChaine/APTV_05/Micro/APTV_05_Ligneux_masqued_micro.tif \n\
                                              -cl ../ImagesTestChaine/APTV_05/Micro/APTV_05_Anthropise_micro_centroid.txt \n\
                                                  ../ImagesTestChaine/APTV_05/Micro/APTV_05_Eau_micro_centroid.txt \n\
                                                  ../ImagesTestChaine/APTV_05/Micro/APTV_05_Ligneux_micro_centroid.txt \n\
                                              -msl 3 5 5 \n\
                                              -mll 11000 12200 21000 \n\
                                              -log ../ImagesTestChaine/APTV_05/fichierTestLog.log -sav")

    parser.add_argument('-i','--image_input',default="",help="Image input to treat", type=str, required=True)
    parser.add_argument('-o','--samples_merge_output',default="",help="Image output merge sample micro", type=str, required=True)
    parser.add_argument('-t','--proposal_table_output',default="",help="Proposal table output to realocation micro class", type=str, required=True)
    parser.add_argument('-ml','--mask_input_list',default=[],nargs="+",help="List of input mask refere to input image.", type=str, required=False)
    parser.add_argument('-ol','--mask_micro_output_list',default=[],nargs="+",help="List of output mask image of micro class.", type=str, required=False)
    parser.add_argument('-cl','--centroid_output_list',default=[],nargs="+",help="List of output centroid file of micro class.", type=str, required=False)
    parser.add_argument('-msl','--macroclass_sampling_list',nargs='+',help="List number of requested micro class in output kmeans.", type=int, required=True)
    parser.add_argument('-mll','--macroclass_labels_list',nargs='+',help="List numeric labels of macroclass.", type=int, required=True)
    parser.add_argument('-kmp.it','--kmeans_param_iterations',default=2000,help="Kmeans Parameter : number iterations. By default : '2000'", type=int, required=False)
    parser.add_argument('-kmp.pr','--kmeans_param_prop',default=1,help="Kmeans Parameter : prop pixels of retained mask. By default : '1'", type=int, required=False)
    parser.add_argument('-kmp.sz','--kmeans_param_size',default=-1,help="Kmeans Parameter : size of training set. By default : '-1'", type=int, required=False)
    parser.add_argument('-npt','--number_of_actives_pixels_threshold',default=200,help="Number of minimum training size for kmeans. Default = 200 * Nb de sous classes", type=int, required=False)
    parser.add_argument("-rcmc",'--rate_clean_micro_class',default=0.0,help="ratio for cleaning micro classes, the total sum of the surfaces is too small, in percentage, example : 20 percent)", type=float, required=False)
    parser.add_argument('-rand','--rand_otb',default=0,help="User defined seed for random KMeans", type=int, required=False)
    parser.add_argument('-ram','--ram_otb',default=0,help="Ram available for processing otb applications (in MB)", type=int, required=False)
    parser.add_argument('-ndv','--no_data_value', default=0, help="Option in option optimize_emprise_nodata  : Value of the pixel no data. By default : 0", type=int, required=False)
    parser.add_argument('-rae','--extension_raster', default=".tif", help="Option : Extension file for image raster. By default : '.tif'", type=str, required=False)
    parser.add_argument('-log','--path_time_log',default="",help="Name of log", type=str, required=False)
    parser.add_argument('-sav','--save_results_inter',action='store_true',default=False,help="Save or delete intermediate result after the process. By default, False", required=False)
    parser.add_argument('-now','--overwrite',action='store_false',default=True,help="Overwrite files with same names. By default, True", required=False)
    parser.add_argument('-debug','--debug',default=3,help="Option : Value of level debug trace, default : 3 ",type=int, required=False)
    args = displayIHM(gui, parser)

    # RECUPERATION DES ARGUMENTS

    # Récupération de l'image d'entrée
    if args.image_input != None:
        image_input = args.image_input
        if not os.path.isfile(image_input):
            raise NameError (cyan + "KmeansMaskApplication : " + bold + red  + "File %s not existe!" %(image_input) + endC)

    # Récupération des masques d'entrée
    if args.mask_input_list != None :
        mask_input_list = args.mask_input_list
        for mask_input in mask_input_list :
            if not os.path.isfile(mask_input):
                raise NameError (cyan + "KmeansMaskApplication : " + bold + red  + "File %s not existe!" %(mask_input) + endC)

    # Récupération du fichier sample micro merge de sortie
    if args.samples_merge_output!= None:
        samples_merge_output=args.samples_merge_output

    # Récupération de la table de proposition de sortie
    if args.proposal_table_output != None:
        proposal_table_output = args.proposal_table_output

    # Récupération des fichiers masque micro de sortie
    if args.mask_micro_output_list!= None:
        mask_micro_output_list=args.mask_micro_output_list

    # Récupération des fichiers centroides de sortie
    if args.centroid_output_list!= None:
        centroid_output_list=args.centroid_output_list

    # Recuperation des infos sur les macroclasses
    if args.macroclass_sampling_list != None:
        macroclass_sampling_list = args.macroclass_sampling_list
    if args.macroclass_labels_list != None:
        macroclass_labels_list = args.macroclass_labels_list

    # Recuperation des parametres generaux du kmeans
    if args.kmeans_param_iterations != None:
        kmeans_parameter_iterations = args.kmeans_param_iterations
    if args.kmeans_param_prop != None:
        kmeans_parameter_prop = args.kmeans_param_prop
    if args.kmeans_param_size != None:
        kmeans_parameter_size = args.kmeans_param_size

    # Récupération du nombre minimum de pixels pour effectuer le kmeans
    if args.number_of_actives_pixels_threshold != None:
        number_of_actives_pixels_threshold = args.number_of_actives_pixels_threshold

    # Récupération du parametre taux minimun tail micro classe pour proposition a la suppression
    if args.rate_clean_micro_class != None:
        rate_clean_micro_class = args.rate_clean_micro_class

    # Récupération du parametre rand
    if args.rand_otb != None:
        rand_otb = args.rand_otb

    # Récupération du parametre ram
    if args.ram_otb != None:
        ram_otb = args.ram_otb

    # Récupération du parametre no_data_value
    if args.no_data_value!= None:
        no_data_value = args.no_data_value

    # Paramètre de l'extension des images rasters
    if args.extension_raster != None:
        extension_raster = args.extension_raster

    # Récupération du nom du fichier log
    if args.path_time_log!= None:
        path_time_log = args.path_time_log

    if args.save_results_inter != None:
        save_results_intermediate = args.save_results_inter

    # Fonction d'écrasement des fichiers
    if args.overwrite!= None:
        overwrite = args.overwrite

    # Récupération de l'option niveau de debug
    if args.debug!= None:
        global debug
        debug = args.debug

    if debug >= 3:
        print(bold + green + "KmeansMaskApplication : variables dans l'appel de la fonction kmeans" + endC)
        print(cyan + "KmeansMaskApplication : " + endC + "image_input : " + str(image_input) + endC)
        print(cyan + "KmeansMaskApplication : " + endC + "samples_merge_output : " + str(samples_merge_output) + endC)
        print(cyan + "KmeansMaskApplication : " + endC + "mask_input_list : " + str(mask_input_list) + endC)
        print(cyan + "KmeansMaskApplication : " + endC + "proposal_table_output : " + str(proposal_table_output) + endC)
        print(cyan + "KmeansMaskApplication : " + endC + "mask_micro_output_list : " + str(mask_micro_output_list) + endC)
        print(cyan + "KmeansMaskApplication : " + endC + "centroid_output_list : " + str(centroid_output_list) + endC)
        print(cyan + "KmeansMaskApplication : " + endC + "macroclass_sampling_list : " + str(macroclass_sampling_list) + endC)
        print(cyan + "KmeansMaskApplication : " + endC + "macroclass_labels_list : " + str(macroclass_labels_list) + endC)
        print(cyan + "KmeansMaskApplication : " + endC + "kmeans_param_iterations : " + str(kmeans_parameter_iterations) + endC)
        print(cyan + "KmeansMaskApplication : " + endC + "kmeans_param_prop : " + str(kmeans_parameter_prop) + endC)
        print(cyan + "KmeansMaskApplication : " + endC + "kmeans_param_size : " + str(kmeans_parameter_size) + endC)
        print(cyan + "KmeansMaskApplication : " + endC + "number_of_actives_pixels_threshold : " + str(number_of_actives_pixels_threshold) + endC)
        print(cyan + "KmeansMaskApplication : " + endC + "rate_clean_micro_class : " + str(rate_clean_micro_class) + endC)
        print(cyan + "KmeansMaskApplication : " + endC + "rand_otb : " + str(rand_otb) + endC)
        print(cyan + "KmeansMaskApplication : " + endC + "ram_otb : " + str(ram_otb) + endC)
        print(cyan + "KmeansMaskApplication : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "KmeansMaskApplication : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "KmeansMaskApplication : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "KmeansMaskApplication : " + endC + "save_results_inter : " + str(save_results_intermediate) + endC)
        print(cyan + "KmeansMaskApplication : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "KmeansMaskApplication : " + endC + "debug : " + str(debug) + endC)

    # EXECUTION DE LA FONCTION
    # Si le dossier de sortie n'existe pas, on le crée
    repertory_output = os.path.dirname(samples_merge_output)
    if not os.path.isdir(repertory_output):
        os.makedirs(repertory_output)

    # Si le dossier de sortie n'existe pas, on le crée
    repertory_output = os.path.dirname(proposal_table_output)
    if not os.path.isdir(repertory_output):
        os.makedirs(repertory_output)

    # A confirmer!
    for image_mask in mask_micro_output_list:
        repertory_output = os.path.dirname(image_mask)
        if not os.path.isdir(repertory_output):
            os.makedirs(repertory_output)
    # A confirmer!
    for centroid_file in centroid_output_list:
        repertory_output = os.path.dirname(centroid_file)
        if not os.path.isdir(repertory_output):
            os.makedirs(repertory_output)

    # execution le kmean pour une image
    applyKmeansMasks(image_input, mask_input_list, samples_merge_output, proposal_table_output, mask_micro_output_list, centroid_output_list,  macroclass_sampling_list, macroclass_labels_list, no_data_value, path_time_log, kmeans_parameter_iterations, kmeans_parameter_prop, kmeans_parameter_size, rate_clean_micro_class, rand_otb, ram_otb, number_of_actives_pixels_threshold, extension_raster, save_results_intermediate, overwrite)

# ================================================

if __name__ == '__main__':
  main(gui=False)
