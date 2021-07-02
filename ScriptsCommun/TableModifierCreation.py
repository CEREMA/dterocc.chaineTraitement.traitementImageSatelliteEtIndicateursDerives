#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerSO/DALETT/SCGSI  All rights reserved.                                                                            #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT CREER UNE TABLE DE PROPOSITION  DE REAFFECTATION DES MICRO CLASSES                                                                 #
#                                                                                                                                           #
#############################################################################################################################################
'''
Nom de l'objet : TableModifierCreation.py
Description :
    Objectif : creer une table de proposition de réafectation des micro classes a partir des indicateurs de qualité


Date de creation : 01/10/2014
----------
Histoire :
----------
Origine : le script originel provient du fichier Chain10_PostTraitement.py (creerTableModifier()) cree en 2013 et utilise par la chaine de traitement OCSOL V1.X
01/10/2014 : Transformation en brique elementaire (suppression des liens avec la chaine OCSOL)
-----------------------------------------------------------------------------------------------------
Modifications
01/10/2014 : refonte du fichier harmonisation des régles de qualitées des niveaux de boucles et des paramétres dans args
21/05/2015 : simplification des parametres en argument plus de liste d'image en emtrée à traiter uniquement une image
------------------------------------------------------
A Reflechir/A faire
'''
# Import des bibliothèques python
from __future__ import print_function
import os,sys,glob,string,shutil,time,argparse
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_log import timeLine
from Lib_text import readTextFileBySeparator, writeTextFile, cleanSpaceText, readConfusionMatrix, correctMatrix
from Lib_math import computeDistance, findMinPositionExceptValue, findPositionList, findMaxPosition
from Lib_spatialite import sqlInsertTable, sqlSurfaceAverageMacro, sqlSurfaceMicro
from Lib_vector import getAreaPolygon, getAverageAreaClass
from Lib_file import removeFile

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 3

###########################################################################################################################################
# FONCTION createTableModifier                                                                                                            #
###########################################################################################################################################
# ROLE:
#     Proposition de réaffectation des micro classes
#
# ENTREES DE LA FONCTION :
#    centroids_input_files_list : liste des fichiers (par macroclasse) contenant les centroides (au format texte)
#    indicators_input_file : fichier d'entrée contenant les indicateurs de qualité (au format texte)
#    matrix_input_file : fichier d'entrée contenant la matrice de confusuion
#    validation_input_vector : echantillons de validation au format.shp
#    label_macro_list : liste des label de chaque macro classes
#    table_output_file : fichier contenant la table de proposition de reaffectation des micro classes (au format texte)
#    path_time_log : le fichier de log de sortie
#    rate_area_min : Seuil de suppression des micro-classes comprenant trop peu de pixels  (en % de la surface moyenne des microclasses d'une même macro-classe)
#    threshold_delete_perf : Seuil de suppression des micro-classes trop mauvaises (valeur minimale de l'indice de performance de la classe)
#    threshold_alert_perf : Seuil de vérification des micro-classes mauvaises (valeur minimale de l'indice de performance de la classe)
#    format_vector : format du fichier vecteur. Optionnel, par default : 'ESRI Shapefile'
#    save_results_intermediate : fichiers de sorties intermediaires non nettoyees, par defaut = False
#    overwrite : supprime ou non les fichiers existants ayant le meme nom
#
# SORTIES DE LA FONCTION :
#    Eléments générés la table de proposition de réafectation des micro classes

def createTableModifier(centroids_input_files_list, indicators_input_file, matrix_input_file, validation_input_vector, label_macro_list, table_output_file, path_time_log, rate_area_min, threshold_delete_perf, threshold_alert_perf, format_vector='ESRI Shapefile', save_results_intermediate=False, overwrite=True) :
    # Mise à jour du Log
    starting_event = "createTableModifier() : Create table modifier starting : "
    timeLine(path_time_log,starting_event)

    print(cyan + "createTableModifier() : " + bold + green + "START ...\n" + endC)

    # Affichage des parametres
    if debug >= 3:
        print(cyan + "createTableModifier() : " + endC + "centroids_input_files_list: "+ str(centroids_input_files_list))
        print(cyan + "createTableModifier() : " + endC + "indicators_input_file: "+ str(indicators_input_file))
        print(cyan + "createTableModifier() : " + endC + "matrix_input_file: "+ str(matrix_input_file))
        print(cyan + "createTableModifier() : " + endC + "validation_input_vector: "+ str(validation_input_vector))
        print(cyan + "createTableModifier() : " + endC + "label_macro_list: "+ str(label_macro_list))
        print(cyan + "createTableModifier() : " + endC + "table_output_file: "+ str(table_output_file))
        print(cyan + "createTableModifier() : " + endC + "path_time_log: " + str(path_time_log))
        print(cyan + "createTableModifier() : " + endC + "rate_area_min: " + str(rate_area_min))
        print(cyan + "createTableModifier() : " + endC + "threshold_delete_perf: " + str(threshold_delete_perf))
        print(cyan + "createTableModifier() : " + endC + "threshold_alert_perf: " + str(threshold_alert_perf))
        print(cyan + "createTableModifier() : " + endC + "format_vector: " + str(format_vector))
        print(cyan + "createTableModifier() : " + endC + "save_results_intermediate: "+ str(save_results_intermediate))
        print(cyan + "createTableModifier() : " + endC + "overwrite: "+ str(overwrite))

    # Test si ecrassement de la table précédemment créée
    check = os.path.isfile(table_output_file)
    if check and not overwrite :
        print(cyan + "createTableModifier() : " + bold + yellow + "Modifier table already exists." + '\n' + endC)
    else:
        # Tenter de supprimer le fichier
        try:
            removeFile(table_output_file)
        except Exception:
            # Ignore l'exception levee si le fichier n'existe pas (et ne peut donc pas être supprime)
            pass

        # lecture des fichiers centroides
        microclass_centroides_list = readCentroidsFiles(centroids_input_files_list)

        # lecture du fichier indicateurs de qualité
        indicator_macro_dico,indicator_general_dico = readQualityIndicatorsFile(indicators_input_file)

        # lecture de la matrice de confusion
        matrix,class_ref_list,class_pro_list = readConfusionMatrix(matrix_input_file)

        # correction de la matrice de confision pour identifier les micro classes manquantes
        missed_micro_list = []
        if class_ref_list != class_pro_list:
            matrix, missed_micro_list = correctMatrix(class_ref_list, class_pro_list, matrix)

        # creer la liste de microclasse en de 'int'
        class_labels_list =[]
        for class_elem in class_pro_list:
            class_labels_list.append(int(class_elem))

        if debug >= 3:
           print(cyan + "createTableModifier() : " + endC + "indicator_macro_dico : " +  str(indicator_macro_dico) + "\n")
           print(cyan + "createTableModifier() : " + endC + "indicator_general_dico : " + str(indicator_general_dico) + "\n")
           print(cyan + "createTableModifier() : " + endC + "microclass_centroides_list = " + str(microclass_centroides_list))
           print(cyan + "createTableModifier() : " + endC + "missed_micro_list : " + str(missed_micro_list))
           print(cyan + "createTableModifier() : " + endC + "class_ref_list : " + str(class_ref_list))
           print(cyan + "createTableModifier() : " + endC + "class_pro_list : " + str(class_pro_list))
           print(cyan + "createTableModifier() : " + endC + "class_labels_list : " + str(class_labels_list))

        # indentifier les microclasses suspectes
        s_suspect_microclass1,s_suspect_microclass2 = findSuspiciousMicroClass(label_macro_list, microclass_centroides_list)

        # detecter les micro classes suspectes
        suspect_micro_list,s_performance_list = detectSuspiciousMicroclass(indicator_macro_dico, class_labels_list, threshold_alert_perf)

        if debug >= 3:
            print(cyan + "createTableModifier() : " + endC + "s_suspect_microclass1 = " + str(s_suspect_microclass1))
            print(cyan + "createTableModifier() : " + endC + "s_suspect_microclass2 = "  + str(s_suspect_microclass2))
            print(cyan + "createTableModifier() : " + endC + "suspect_micro_list = " + str(suspect_micro_list))
            print(cyan + "createTableModifier() : " + endC + "s_performance_list = "  + str(s_performance_list))

        # creation de la liste de proposition de réaffectation des micro classes
        proposal_text = proposeReallocationMicroClass(validation_input_vector, s_suspect_microclass1, s_suspect_microclass2, s_performance_list, missed_micro_list, suspect_micro_list, table_output_file, label_macro_list, rate_area_min, threshold_delete_perf, threshold_alert_perf, format_vector)

        # ecriture du fichier proposition de réaffectation
        writeTextFile(table_output_file, proposal_text)

    print(cyan + "createTableModifier() : " + bold + green + "END\n" + endC)

    # Mise à jour du Log
    ending_event = "createTableModifier() : Create table modifier ending : "
    timeLine(path_time_log,ending_event)
    return

###########################################################################################################################################
# FONCTION detectSuspiciousMicroclass()                                                                                                   #
###########################################################################################################################################
def detectSuspiciousMicroclass(indicator_macro_dico, class_pro_list, threshold_alert_perf):
    #
    # Seuillage
    # trop faible : 0 <= threshold_alert_perf <= 1 : tres bonne
    #

    # Constantes
    TAG_PERFORMANCE = 'Performance'

    # Varirables
    performance_list = []

    # Re-creation des listes de performance, à partir de indicator_macro_dico
    for indicators in indicator_macro_dico:
        performance  = indicators[TAG_PERFORMANCE]
        performance_list.append(performance)

    # Detection
    suspect_micro_list = []
    s_performance_list = []

    for i in range(len(class_pro_list)):
        if float(performance_list[i]) < float(threshold_alert_perf):
            suspect_micro_list.append(int(class_pro_list[i]))
            s_performance_list.append(float(performance_list[i]))

    return suspect_micro_list,s_performance_list

###########################################################################################################################################
# FONCTION proposeReallocationMicroClass()                                                                                                #
###########################################################################################################################################
def proposeReallocationMicroClass(shape_file_input, s_suspect_microclass1, s_suspect_microclass2, s_performance_list, missed_micro_list, suspect_micro_list, table_output_file, class_labels_list, rate_area_min, threshold_delete_perf, threshold_alert_perf, format_vector):

    print(cyan + "proposeReallocationMicroClass() : " + bold + green + "Start propose reallocation microclass ...\n" + endC)

    is_spatialite = False

    if debug >= 3:
        print(cyan + "proposeReallocationMicroClass() : " + endC + "shape_file_input : " +  str(shape_file_input))
        print(cyan + "proposeReallocationMicroClass() : " + endC + "s_suspect_microclass1 : " +  str(s_suspect_microclass1))
        print(cyan + "proposeReallocationMicroClass() : " + endC + "s_suspect_microclass2 : " +  str(s_suspect_microclass2))
        print(cyan + "proposeReallocationMicroClass() : " + endC + "suspect_micro_list : " + str(suspect_micro_list))
        print(cyan + "proposeReallocationMicroClass() : " + endC + "s_performance_list : " + str(s_performance_list))
        print(cyan + "proposeReallocationMicroClass() : " + endC + "format_vector : " + str(format_vector))

    # constantes
    HEADER_TABLEAU_MODIF = "MICROCLASSE;TRAITEMENT\n"
    EXT_SQLITE = ".sqlite"

    # variables
    text_output = HEADER_TABLEAU_MODIF
    suspect_micro_end_list = []

    if is_spatialite :
        # Creer une base de donnees qui contient une table des echantillons d'apprentissage
        repertory_output = os.path.dirname(table_output_file)
        table_input_name = os.path.splitext(os.path.basename(table_output_file))[0]
        bd_name = repertory_output + os.sep + table_input_name + EXT_SQLITE

        # Supprimer la base de donnees temporaire si elle existe encore
        try:
            removeFile(bd_name)
        except Exception:
            # Ignore l'exception levee si le fichier n'existe pas (et ne peut donc pas être supprime)
            pass

        createBDtableModify(shape_file_input, table_input_name, bd_name)

        average_area_list = computeAverageAreaMacro(repertory_output, class_labels_list, table_input_name, bd_name)
    else :
        average_area_list = []
        for class_label in class_labels_list:
            average_area = getAverageAreaClass(shape_file_input, "ID", class_label, format_vector)
            average_area_list.append(average_area)
    if debug >= 1:
        print(cyan + "proposeReallocationMicroClass() : " + endC + "average_area_list : " +  str(average_area_list))

    # calcul la surface min autorisée
    area_authorized_macro_list = []
    for area in average_area_list:
        area_authorized_macro_list.append(rate_area_min * area)
    if debug >= 1:
        print(cyan + "proposeReallocationMicroClass() : " + endC + "area_authorized_macro_list : " +  str(area_authorized_macro_list))

    # Recuperer les donnees de centroids
    micro_suspect1_list, micro_pp1_list, micro_suspect2_list, micro_pp2_list = getDataCentroids(s_suspect_microclass1, s_suspect_microclass2, class_labels_list)

    # Proposer les traitements correspondant a chaque microclasse suspect
    # 1er fois, traiter les informations obtenues par la matrice de confusion en prenant en compte l'analyse de centroids
    for i in range(len(s_performance_list)):

        if is_spatialite :
            area_micro = computeAreaMicro(repertory_output, table_input_name, bd_name, suspect_micro_list[i])
        else :
            area_micro = getAreaPolygon(shape_file_input,"ID", suspect_micro_list[i],format_vector )
        if debug >= 1:
            print("Traiter %d, surface %f" %(suspect_micro_list[i], area_micro))

        if area_micro < area_authorized_macro_list[findPositionList(class_labels_list, (suspect_micro_list[i]/100)*100)]: #Regle 1
            if debug >= 1:
                print("Regle 1 - Supprimer : %d Surf : %d" %(suspect_micro_list[i], area_micro))
            text_output += "%d;-1\n" %(suspect_micro_list[i])
            suspect_micro_end_list.append(suspect_micro_list[i])
        else:
            if s_performance_list[i] < threshold_delete_perf: #Regle 2.1
                if debug >= 1:
                    print("Regle 2.1 - Supprimer : %d Seuil : %f" %(suspect_micro_list[i], s_performance_list[i]))
                text_output += "%d;-1\n" %(suspect_micro_list[i])
                suspect_micro_end_list.append(suspect_micro_list[i])
            elif s_performance_list[i] < threshold_alert_perf:
                pos1 = findPositionList(micro_suspect1_list, suspect_micro_list[i])
                pos2 = findPositionList(micro_suspect2_list, suspect_micro_list[i])
                if (pos1 == -1 or pos2 == -1) and pos1 != pos2: #Regle 2.1.2
                    if debug >= 1:
                        print("Regle 2.1.2 - Supprimer : %d pos1 : %d pos2 : %d" %(suspect_micro_list[i], pos1, pos2))
                    text_output += "%d;-1\n" %(suspect_micro_list[i])
                    suspect_micro_end_list.append(suspect_micro_list[i])
                if pos1 != -1 and pos2 != -1:
                    if(micro_pp1_list[pos1]/100) == (micro_pp2_list[pos2]/100): #Regle 2.1.1
                        if debug >= 1:
                            print("Regle 2.1.1 - Reaffecter : %d %d" %(suspect_micro_list[i], (micro_pp1_list[pos1]/100) * 100))
                        text_output += "%d;%d\n" %(suspect_micro_list[i], (micro_pp1_list[pos1]/100)*100)
                        suspect_micro_end_list.append(suspect_micro_list[i])
                    else: #Regle 2.1.2
                        if debug >= 1:
                            print("Regle 2.1.2 - Supprimer : %d" %(suspect_micro_list[i]))
                        text_output += "%d;-1\n" %(suspect_micro_list[i])
                        suspect_micro_end_list.append(suspect_micro_list[i])
    # 2eme fois, traiter encore l'analyse de centroids pour les microclasses ayant la bonne performance mais plus proche d'autre microclasse issue par une autre macroclasse
    for i in range(len(micro_suspect1_list)):
        position = findPositionList(suspect_micro_end_list, micro_suspect1_list[i])
        if position == -1:
            pos = findPositionList(micro_suspect2_list, micro_suspect1_list[i])
            if pos != -1:
                if (micro_pp1_list[i]/100)*100 == (micro_pp2_list[pos]/100)*100: #Regle 3.1
                    if debug >= 1:
                        print("Regle 3.1 - Alert : %d" %(micro_suspect1_list[i]))
                    text_output += "%d;A\n" %(micro_suspect1_list[i])
                else: #Regle 3.2
                    if debug >= 1:
                        print("Regle 3.2 - Alert : %d" %(micro_suspect1_list[i]))
                    text_output += "%d;A\n" %(micro_suspect1_list[i])
                suspect_micro_end_list.append(micro_suspect1_list[i])
            else: #Regle 3.2
                if debug >= 1:
                    print("Regle 3.2 - Alert : %d" %(micro_suspect1_list[i]))
                text_output += "%d;A\n" %(micro_suspect1_list[i])
                suspect_micro_end_list.append(micro_suspect1_list[i])

    for i in range(len(micro_suspect2_list)):
        position = findPositionList(suspect_micro_end_list, micro_suspect2_list[i])
        if position == -1: #Regle 3.2
            if debug >= 1:
                print("Regle 3.2 - Alert : %d" %(micro_suspect2_list[i]))
            text_output += "%d;A\n" %(micro_suspect2_list[i])
            suspect_micro_end_list.append(micro_suspect2_list[i])

    # Annoncer pour les microclasses qui sont disparues (presenter en entree mais disparaitre en sortie)
    for missed in missed_micro_list:
        text_output += "%s;D\n" %(missed)

    if is_spatialite :
        # Enlever la base de donnees temporaire
        removeFile(bd_name)

    print(cyan + "proposeReallocationMicroClass() : " + bold + green + "End propose reallocation  microclass \n" + endC)
    return text_output

###########################################################################################################################################
# FONCTION createBDtableModify()                                                                                                          #
###########################################################################################################################################
def createBDtableModify(shape_file_input, table_input_name, data_base_name):

    input_shape = os.path.splitext(shape_file_input)[0]
    requete_spat_insert = sqlInsertTable(input_shape, table_input_name, data_base_name)
    # Lancer le script
    exitCode = os.system(requete_spat_insert)
    if exitCode != 0:
        raise NameError(cyan + "createBDtableModify() : " + bold + red + "An error occured during spatialite command. See error message above." + endC)
    return

###########################################################################################################################################
# FONCTION computeAverageAreaMacro()                                                                                                      #
###########################################################################################################################################
def computeAverageAreaMacro(repertory_output, class_labels_list, table_input_name, data_base_name):

    average_area_macro_list = []
    sql_temporary_file = repertory_output + os.sep + "spatialiteTemp.txt"

    for class_label in class_labels_list:
        requete = sqlSurfaceAverageMacro(table_input_name, "ID", class_label, data_base_name)
        exitCode = os.system("%s > %s"%(requete,sql_temporary_file))
        if exitCode != 0:
            raise NameError(cyan + "computeAverageAreaMacro() : " + bold + red + "An error occured during file creation. See error message above." + endC)
        requete_result = readTextFileBySeparator(sql_temporary_file, " ")
        print(requete_result)
        if requete_result == []:
            average_area_macro_list.append(0)
        else:
            average_area_macro_list.append(float(requete_result[0][0]))
        removeFile(sql_temporary_file)

    return average_area_macro_list

###########################################################################################################################################
# FONCTION computeAreaMicro()                                                                                                             #
###########################################################################################################################################
def computeAreaMicro(repertory_output, table_input_name, data_base_name, micro):
    sql_temporary_file = repertory_output + os.sep + "spatialiteTemp.txt"

    requete = sqlSurfaceMicro(table_input_name, "ID", micro, data_base_name)
    exitCode = os.system("%s > %s"%(requete,sql_temporary_file))
    if exitCode != 0:
        raise NameError(cyan + "computeAreaMicro() : " + bold + red + "An error occured during fileCreation command. See error message above." + endC)
    # Calculer la surface de la microclasse
    area_micro = float(readTextFileBySeparator(sql_temporary_file, " ")[0][0])
    removeFile(sql_temporary_file)

    return area_micro

###########################################################################################################################################
# FONCTION findSuspiciousMicroClass()                                                                                                     #
###########################################################################################################################################
def findSuspiciousMicroClass(label_macro_list, microclass_centroides_list) :
    print(cyan + "findSuspiciousMicroClass() : " + bold + green + "Start find suspicious microclass ...\n" + endC)

    #-------------------------------------------------------#
    # Calculer les distances_list entre les microclasses
    #-------------------------------------------------------#

    # Une variable string qui contient le resultat de calcule et aussi de recherche
    s_microclass_pp1 = []
    s_microclass_pp2 = []

    # Pour chaque macroclasse correspondant au nombre de fichier d'entree
    for id_macroclasse in range(len(label_macro_list)) :
    # begin
        # Pour chaque microclasse <id_microclasse> dans macroclasse <id_macroclasse>
        # C'est aussi la microclasse de requete
        for id_microclasse in range(len(microclass_centroides_list[id_macroclasse])) :
        # begin
            micro1 = microclass_centroides_list[id_macroclasse][id_microclasse]
            # Les variables temporaire contiennent la valeur de recherche pour une microclasse
            f_distance_min1 = 0.0 # la distance minimum
            i_microclass_pp1 = 0 # la microclasse plus proche
            i_macroclass_pp1 = 0 # la macroclasse contient la microclasse plus proche

            f_distance_min2 = 0.0 # la distance minimum
            i_microclass_pp2 = 0 # la microclasse plus proche
            i_macroclasse_pp2 = 0 # la macroclasse contient la microclasse plus proche

            # Calculer la distance entre la microclasse <id_microclasse> et les autres macroclasses dans l'espace de calcul

            # Prendre toutes les macroclasses de comparaison...
            for id_macroclasse_compare in range(len(label_macro_list)) :
            # begin
                # Creer une variable qui contient les distances_list aux microclasses de la macroclasse <id_macroclasse_compare>
                distances_list = []

                # Pour chaque microclasse de comparaison dans la liste de macroclasse de comparaison
                for micro2 in microclass_centroides_list[id_macroclasse_compare]:
                # begin
                    # La distance entre microclasse <id_microclasse> et microclasses de la macroclasse <id_macroclasse_compare>
                    distance = computeDistance(micro1, micro2)
                    # Ajouter la distance dans une liste
                    distances_list.append(distance)
                # end

                # Trouver la microclasse plus proche de microclasse <id_microclasse>
                pos_min1 = findMinPositionExceptValue(distances_list, [0.0])
                pos_min2 = findMinPositionExceptValue(distances_list, [0.0, distances_list[pos_min1]])

                #----------------------------------------------------------------------#
                # Comparer le resultat de recherche actuel avec les resultats precedents
                #----------------------------------------------------------------------#
                if(f_distance_min1 == 0.0): # Si le premier cas
                    f_distance_min1 = distances_list[pos_min1]
                    i_microclass_pp1 = pos_min1
                    i_macroclass_pp1 = id_macroclasse_compare
                else: # Sinon
                    if(distances_list[pos_min1] < f_distance_min1):
                        f_distance_min1 = distances_list[pos_min1]
                        i_microclass_pp1 = pos_min1
                        i_macroclass_pp1 = id_macroclasse_compare

                if(f_distance_min2 == 0.0): # Si le premier cas
                    f_distance_min2 = distances_list[pos_min2]
                    i_microclass_pp2 = pos_min2
                    i_macroclasse_pp2 = id_macroclasse_compare
                else: # Sinon
                    if(distances_list[pos_min2] < f_distance_min2):
                        f_distance_min2 = distances_list[pos_min2]
                        i_microclass_pp2 = pos_min2
                        i_macroclasse_pp2 = id_macroclasse_compare

                # Afficher a l'ecran le resultat correspondant a chaque macroclasse
                if debug >= 4:
                    print("[%d-%d plus proche %d-%d]" %(id_macroclasse, id_microclasse, id_macroclasse_compare, pos_min1))
                    print("     Verifier :")
                    print(distances_list)
            # end

            # Afficher la microclasse plus proche de la microclasse de requete <id_microclasse>
            if debug >= 4:
                print("Correspondant a microclasse %d" %(id_microclasse))
                print("Microclasse plus proche [%d-%d] avec distance %f" %(i_macroclass_pp1, i_microclass_pp1, f_distance_min1))

            # Apres calculer avec toutes les macroclasses, on a une microclasse plus proche de la microclasse de requete <id_microclasse>.
            # Alors, sauvegarder le resultat dans une chaine de charactere (string) pour verifier et pour les traitements apres
            s_result1 = "%d-%d-%d-%d-%f" %(id_macroclasse, id_microclasse, i_macroclass_pp1, i_microclass_pp1, f_distance_min1)
            s_result2 = "%d-%d-%d-%d-%f" %(id_macroclasse, id_microclasse, i_macroclasse_pp2, i_microclass_pp2, f_distance_min2)

            s_microclass_pp1.append(s_result1)
            s_microclass_pp2.append(s_result2)
        #end
    #end

    if debug >= 4:
        print("s_microclass_pp1 : " + str(s_microclass_pp1))
        print("s_microclass_pp2 : " + str(s_microclass_pp2))

    # ne garder que les microclasses qui peuvent etre emplacer par une autre microclasse
    s_suspect_microclass1 = warmIdentificationMicroClass(s_microclass_pp1, 1)
    s_suspect_microclass2 = warmIdentificationMicroClass(s_microclass_pp2, 2)

    print(cyan + "findSuspiciousMicroClass() : " + bold + green + "End find suspicious microclass \n" + endC)
    return s_suspect_microclass1, s_suspect_microclass2

###########################################################################################################################################
# FONCTION getDataCentroids()                                                                                                             #
###########################################################################################################################################
def getDataCentroids(s_suspect_microclass1, s_suspect_microclass2, macro_labels_list):
    micro_suspect1_list = []
    micro_pp1_list = []
    micro_suspect2_list = []
    micro_pp2_list = []
    for chain in s_suspect_microclass1:
        composants = chain.split("-")
        macro1 = int(composants[0])
        micro1 = int(composants[1])
        macro2 = int(composants[2])
        micro2 = int(composants[3])
        micro_suspect1_list.append(macro_labels_list[macro1] + micro1)
        micro_pp1_list.append(macro_labels_list[macro2] + micro2)
    for chain in s_suspect_microclass2:
        composants = chain.split("-")
        macro1 = int(composants[0])
        micro1 = int(composants[1])
        macro2 = int(composants[2])
        micro2 = int(composants[3])
        micro_suspect2_list.append(macro_labels_list[macro1] + micro1)
        micro_pp2_list.append(macro_labels_list[macro2] + micro2)

    return micro_suspect1_list, micro_pp1_list, micro_suspect2_list, micro_pp2_list

###########################################################################################################################################
# FONCTION warmIdentificationMicroClass()                                                                                                 #
###########################################################################################################################################
def warmIdentificationMicroClass(s_microclass_pp, case):
    print(cyan + "warmIdentificationMicroClass() : " + bold + green + "Start warm microclass identified...\n" + endC)

    # identifier les microclasses suspectes
    results = []
    for info_warm_microclass in s_microclass_pp:
        composants = info_warm_microclass.split("-")
        macro1 = int(composants[0])
        micro1 = int(composants[1])
        macro2 = int(composants[2])
        micro2 = int(composants[3])
        if(macro1 != macro2):
            results.append(info_warm_microclass)

    print(cyan + "warmIdentificationMicroClass() : " + bold + green + "End warm microclass identified\n" + endC)

    return results

###########################################################################################################################################
# FONCTION readCentroidsFiles()                                                                                                           #
###########################################################################################################################################
def readCentroidsFiles(centroids_input_files_list) :
    print(cyan + "readCentroidsFile() : " + bold + green + "Centroids file reading...\n" + endC)

    microclass_centroides_list = []
    for centroids_file in centroids_input_files_list:
        if debug >= 4:
            print("file centroides : " + centroids_file)
        composants_list = readTextFileBySeparator(centroids_file, " ")
        microclass_centroides_list.append(composants_list)
        for composant in composants_list :
           if debug >= 4:
               print(composant)

    print(cyan + "readCentroidsFile() : " + bold + green + "Centroids file readed \n" + endC)

    return microclass_centroides_list

###########################################################################################################################################
# FONCTION readQualityIndicatorsFile()                                                                                                    #
###########################################################################################################################################
def readQualityIndicatorsFile(indicators_input_file) :
    print(cyan + "readQualityIndicatorsFile() : " + bold + green + "Indicators quality file reading... \n" + endC)

    # creer un dictionaire contenant tous les indicateurs de classes et un dictionaire des indicateurs généraux contenu dans le fichier
    indicator_macro_dico = []
    indicator_general_dico = {}
    indicator_general_label = []
    indicator_general_value = []

    indicators_list = []
    composants_list = readTextFileBySeparator(indicators_input_file, ";")

    for idx_line in range(len(composants_list)) :
       composant = composants_list[idx_line]
       # cas des indicateurs pour chaque macro classes
       if idx_line < len(composants_list)-2 :
           if debug >= 4:
               print(composant)
           if idx_line == 0 :
               line_zero_list = composant
               for id_elem in range(1, len(line_zero_list)):
                   class_elm = cleanSpaceText(line_zero_list[id_elem])
                   class_dico = {}
                   class_dico[cleanSpaceText(line_zero_list[0])] = class_elm
                   indicator_macro_dico.append(class_dico)
           else :
               line_list = composant
               for id_elem in range(1, len(line_list)):
                   indic_elm = cleanSpaceText(line_list[id_elem])
                   indicator_macro_dico[id_elem-1][cleanSpaceText(line_list[0])] = indic_elm

       # liste (labels) des indicateurs generaux
       elif idx_line == len(composants_list)-1 :
           if debug >= 4:
               print(composant)
           for elem in composant :
               indicator_general_value.append(cleanSpaceText(elem))
       # Valeurs des indicateurs generaux
       else :
           if debug >= 4:
               print(composant)
           for elem in composant :
               indicator_general_label.append(cleanSpaceText(elem))

    # creation dico indicateurs generaux

    for indicator_idx in range(len(indicator_general_label)) :
        indicator_general_dico[indicator_general_label[indicator_idx]] = indicator_general_value[indicator_idx]

    print(cyan + "readQualityIndicatorsFile() : " + bold + green + "Indicators quality file readed \n" + endC)

    # retourne les deux dictionaires
    return indicator_macro_dico,indicator_general_dico

###########################################################################################################################################
# MISE EN PLACE DU PARSER                                                                                                                 #
###########################################################################################################################################

# Code executé seulement dans le cas ou le script est lancé depuis une ligne de commande
# Il n'est pas executé lors d'un import TableModifierCreation.py
# Exemple de lancement en ligne de commande:
# python TableModifierCreation.py -cl ../ImagesTestChaine/APTV_05/Micro/APTV_05_Anthropise_centroid.txt ../ImagesTestChaine/APTV_05/Micro/APTV_05_Ligneux_centroid.txt -v ../ImagesTestChaine/APTV_05/Micro/APTV_05_cleaned.shp -icm ../ImagesTestChaine/APTV_05/Micro/APTV_05_confusion_matrix.txt -iqi ../ImagesTestChaine/APTV_05/Micro/APTV_05_quality_indicators.csv -t ../ImagesTestChaine/APTV_05/Micro/APTV_05_prop_tab.txt -label 11000 21000 -ram 0.1 -tdp 0.2 -tap 0.5 -log ../ImagesTestChaine/APTV_05/fichierTestLog.txt

def main(gui=False):

    # Définition des arguments possibles pour l'appel en ligne de commande
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, prog="TableModifierCreation", description="\
    Info : Create table modification macro class. \n\
    Objectif : Creer une table de proposition de reafectation des micro classes a partir des indicateurs de qualite. \n\
    Example : python TableModifierCreation.py -cl ../ImagesTestChaine/APTV_05/Micro/APTV_05_Anthropise_centroid.txt \n\
                                                  ../ImagesTestChaine/APTV_05/Micro/APTV_05_Ligneux_centroid.txt \n\
                                              -v ../ImagesTestChaine/APTV_05/Micro/APTV_05_cleaned.shp \n\
                                              -icm ../ImagesTestChaine/APTV_05/Micro/APTV_05_confusion_matrix.txt \n\
                                              -iqi ../ImagesTestChaine/APTV_05/Micro/APTV_05_quality_indicators.csv \n\
                                              -t ../ImagesTestChaine/APTV_05/Micro/APTV_05_prop_tab.txt \n\
                                              -label 11000 21000 \n\
                                              -ram 0.1 -tdp 0.2 -tap 0.5 \n\
                                              -log ../ImagesTestChaine/APTV_05/fichierTestLog.txt")

    # Paramètres
    parser.add_argument('-cl','--centroid_input_list',default=[],nargs="+",help="List of input centroid file of micro class entrainement.", type=str, required=False)
    parser.add_argument('-v','--vector_input',default="",help="Vector input contain the entrainement sample", type=str, required=True)
    parser.add_argument('-icm','--conf_matrix_input',default="",help="File input confusion matrix file", type=str, required=True)
    parser.add_argument('-iqi','--quality_indic_input',default="",help="File intput quality indicators file", type=str, required=True)
    parser.add_argument('-t','--proposal_table_output',default="",help="Proposal table output to realocation micro class", type=str, required=True)
    parser.add_argument('-label','--class_label_list',default="",nargs="+",help="List containt label class, ex. 11000 12200", type=int, required=True)
    parser.add_argument('-ram','--rate_area_min',default=0.1,help="Suppression threshold microclass comprising too few pixels (in percentage of the average area of the same macro microclass). By default : 0.1", type=float, required=False)
    parser.add_argument('-tdp','--threshold_delete_perf',default=0.2,help="Suppression threshold too bad microclass (minimum value of the performance index of the class). By default : 0.2", type=float, required=False)
    parser.add_argument('-tap','--threshold_alert_perf',default=0.5,help="Verification threshold of bad microclass (minimum value of the performance index of the class). By default : 0.5", type=float, required=False)
    parser.add_argument('-vef','--format_vector', default="ESRI Shapefile",help="Format of the output file.", type=str, required=False)
    parser.add_argument('-log','--path_time_log',default="",help="Name of log", type=str, required=False)
    parser.add_argument('-sav','--save_results_inter',action='store_true',default=False,help="Save or delete intermediate result after the process. By default, False", required=False)
    parser.add_argument('-now','--overwrite',action='store_false',default=True,help="Overwrite files with same names. By default, True", required=False)
    parser.add_argument('-debug','--debug',default=3,help="Option : Value of level debug trace, default : 3 ",type=int, required=False)
    args = displayIHM(gui, parser)

    # RECUPERATION DES ARGUMENTS

    # Récupération des fichiers centroides de sortie
    if args.centroid_input_list!= None:
        centroid_input_list=args.centroid_input_list
        for centroid_input in centroid_input_list :
            if not os.path.isfile(centroid_input):
                raise NameError (cyan + "TableModifierCreation : " + bold + red  + "File %s not existe!" %(centroid_input) + endC)


    # Récupération du fichier vecteur d'entrée
    if args.vector_input != None:
        vector_input = args.vector_input
        if not os.path.isfile(vector_input):
            raise NameError (cyan + "TableModifierCreation : " + bold + red  + "File %s not existe!" %(vector_input) + endC)

     # Récupération du fichier de sortie matrice de confusion
    if args.conf_matrix_input != None:
        conf_matrix_input = args.conf_matrix_input
        if not os.path.isfile(conf_matrix_input):
            raise NameError (cyan + "TableModifierCreation : " + bold + red  + "File %s not existe!" %(conf_matrix_input) + endC)

    # Récupération du fichier de sortie indicateur de qualité
    if args.quality_indic_input != None:
        quality_indic_input = args.quality_indic_input
        if not os.path.isfile(quality_indic_input):
            raise NameError (cyan + "TableModifierCreation : " + bold + red  + "File %s not existe!" %(quality_indic_input) + endC)

    # Récupération de la table de proposition de sortie
    if args.proposal_table_output != None:
        proposal_table_output = args.proposal_table_output

    # Recuperation des infos sur les macroclasses
    # creation de la liste macro class - label
    if args.class_label_list != None:
        class_label_list = args.class_label_list

    # Recuperation des seuils
    if args.rate_area_min != None:
       rate_area_min = args.rate_area_min

    if args.threshold_delete_perf != None:
       threshold_delete_perf = args.threshold_delete_perf

    if args.threshold_alert_perf != None:
        threshold_alert_perf = args.threshold_alert_perf

    # Récupération du format des vecteurs de sortie
    if args.format_vector != None :
        format_vector = args.format_vector

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

    # Affichage des arguments récupérés
    if debug >= 3:
        print(bold + green + "Variables dans le parser" + endC)
        print(cyan + "TableModifierCreation : " + endC + "centroid_input_list : " + str(centroid_input_list) + endC)
        print(cyan + "TableModifierCreation : " + endC + "vector_input : " + str(vector_input) + endC)
        print(cyan + "TableModifierCreation : " + endC + "conf_matrix_input : " + str(conf_matrix_input) + endC)
        print(cyan + "TableModifierCreation : " + endC + "quality_indic_input : " + str(quality_indic_input) + endC)
        print(cyan + "TableModifierCreation : " + endC + "proposal_table_output : " + str(proposal_table_output) + endC)
        print(cyan + "TableModifierCreation : " + endC + "class_label_list : " + str(class_label_list) + endC)
        print(cyan + "TableModifierCreation : " + endC + "rate_area_min : " + str(rate_area_min) + endC)
        print(cyan + "TableModifierCreation : " + endC + "threshold_delete_perf : " + str(threshold_delete_perf) + endC)
        print(cyan + "TableModifierCreation : " + endC + "threshold_alert_perf : " + str(threshold_alert_perf) + endC)
        print(cyan + "TableModifierCreation : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "TableModifierCreation : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "TableModifierCreation : " + endC + "save_results_inter : " + str(save_results_intermediate) + endC)
        print(cyan + "TableModifierCreation : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "TableModifierCreation : " + endC + "debug : " + str(debug) + endC)

    # EXECUTION DE LA FONCTION

    # Si le dossier de sortie n'existe pas, on le crée
    repertory_output = os.path.dirname(proposal_table_output)
    if not os.path.isdir(repertory_output):
        os.makedirs(repertory_output)

    # creer la table de proposition
    createTableModifier(centroid_input_list, quality_indic_input, conf_matrix_input, vector_input, class_label_list, proposal_table_output, path_time_log, rate_area_min, threshold_delete_perf, threshold_alert_perf, format_vector, save_results_intermediate, overwrite)

# ================================================

if __name__ == '__main__':
  main(gui=False)
