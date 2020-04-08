#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerSO/DALETT/SCGSI  All rights reserved.                                                                            #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT QUI CLASSE UNE COUCHE VECTEUR                                                                                                      #
#                                                                                                                                           #
#############################################################################################################################################
'''
Nom de l'objet : classifyVector.py
Description :
    Objectif : faire une classification d'une couche vector
    Rq : utilisation des OTB Applications : otbcli_ComputeOGRLayersFeaturesStatistics, otbcli_TrainVectorClassifier, otbcli_VectorClassifier

Date de creation : 05/03/2020
----------
Modifications

------------------------------------------------------
A Reflechir/A faire

'''

from __future__ import print_function
import os,sys,glob,string,argparse
from osgeo import ogr,osr
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_log import timeLine
from Lib_file import removeFile, removeVectorFile

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 3

###########################################################################################################################################
# FONCTION classifyVector()                                                                                                               #
###########################################################################################################################################
# ROLE:
#    appliquer une classification à une couche vecteur
#
# ENTREES DE LA FONCTION :
#   vector_input : la couche de vecteur en entrée
#   classif_vector_output : la couche de vecteur avec le champs de classification
#   input_cfield : est le champs qui portent les valeurs des classes objet de classification
#   output_cfield : champs des valeurs de la classification
#   list_feat : sont les champs utilisés pour l'apprentissage de l'algorithme exemple :  feat = [beanB0, beanB2]
#   expression : fait la selection sur le champs des valeurs d'aprentissage exemple : expression = "Ech != '0'"
#   overwrite : supprime ou non les fichiers existants ayant le meme nom, par defaut a True
#   format_vector : format du fichier vecteur. Optionnel, par default : 'ESRI Shapefile'
#   extension_vector : extension du fichier vecteur de sortie, par defaut = '.shp
#   save_results_intermediate : fichiers de sorties intermediaires non nettoyées, par defaut = False
#   extension_model : exetension du model de classification
#   extension_xml : extension du fichier des statistiques claculées

# SORTIES DE LA FONCTION :
#   Couche de classification
#   Eléments générés par le script : un champs ajoutée à la couche vecteur de segmentation qui represente valeurs classes
#

def classifyVector(vector_input, classif_vector_output, list_feat, expression, input_cfield, output_cfield, path_time_log, format_vector='ESRI Shapefile', extension_vector=".shp", extension_xml = ".xml", extension_model = ".model", save_results_intermediate=False, overwrite=True):

    # Constante
    SUFFIX_OUT = "_out"
    SUFFIX_TRAIN = "_train"

    # Mise à jour du Log
    starting_event = "classifyVector() : Classification vecteur starting : "
    timeLine(path_time_log,starting_event)

    print(endC)
    print(bold + green + "## START : classifyVector" + endC)
    print(endC)

    if debug >= 2:
        print(bold + green + "classifyVector() : Variables dans la fonction" + endC)
        print(cyan + "classifyVector() : " + endC + "vector_input : " + str(vector_input) + endC)
        print(cyan + "classifyVector() : " + endC + "classif_vector_output : " + str(classif_vector_output) + endC)
        print(cyan + "classifyVector() : " + endC + "list_feat : " + str(list_feat) + endC)
        print(cyan + "classifyVector() : " + endC + "input_cfield : " + str(input_cfield) + endC)
        print(cyan + "classifyVector() : " + endC + "output_cfield : " + str(output_cfield) + endC)
        print(cyan + "classifyVector() : " + endC + "expression : " + str(expression) + endC)
        print(cyan + "classifyVector() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "classifyVector() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "classifyVector() : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "classifyVector() : " + endC + "extension_xml : " + str(extension_xml) + endC)
        print(cyan + "classifyVector() : " + endC + "extension_model : " + str(extension_model) + endC)
        print(cyan + "classifyVector() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "classifyVector() : " + endC + "overwrite : " + str(overwrite) + endC)

    # Creation des chemins d'enregistrement des calculs:
    repertory_output = os.path.dirname(vector_input)
    name = os.path.splitext(os.path.basename(vector_input))[0]
    layer_name = name
    vector_output_train_tmp = repertory_output + os.sep + name + SUFFIX_TRAIN + extension_vector
    outstats = repertory_output + os.sep + name + extension_xml
    model = repertory_output + os.sep + name + extension_model

    # Vérification si le vecteur de sortie est définie
    if classif_vector_output == "" :
        classif_vector_output = repertory_output + os.sep + name + SUFFIX_OUT + extension_vector

    # Vérification de l'existence d'une couche vecteur classée
        check = os.path.isfile(classif_vector_output)

    # Si oui et si la vérification est activée, passage à l'étape suivante
    if check and not overwrite :
        print(cyan + "classifyVector() : " + bold + green +  "vector already classified" + "." + endC)
    # Si non ou si la vérification est désactivée, application du filtre
    else:
        # Tentative de suppresion du fichier
        try:
            removeVectorFile(classif_vector_output, format_vector=format_vector)
        except Exception:
            # Ignore l'exception levée si le fichier n'existe pas (et ne peut donc pas être supprimé)
            pass

        if debug >= 3:
            print(cyan + "classifyVector() : " + bold + green +  "Applying classified segmenation", "..." , '\n' + endC)

        # Recuperation du driver pour le format shape fichier entrée
        driver_input = ogr.GetDriverByName(format_vector)

        # Ouverture du fichier shape en lecture
        data_source_input = driver_input.Open(vector_input, 1) # 1 means writeable.

        if data_source_input is None:
            print(cyan + "classifyVector() : " + bold + red + "Impossible d'ouvrir le fichier vecteur : " + vector_input + endC, file=sys.stderr)
            sys.exit(1) # exit with an error code

        # Recuperer la couche (une couche contient les segments)
        layer_input = data_source_input.GetLayer(0)

        # Vérification de l'existence de la colonne col (retour = -1 : elle n'existe pas)
        layer_definition = layer_input.GetLayerDefn() # GetLayerDefn => returns the field names of the user defined (created) fields
        id_field = layer_definition.GetFieldIndex(output_cfield)
        if id_field != -1 :
            print(cyan + "classifyVector() : " + bold + yellow + "Attention le champs de classification existe déjà" + output_cfield + endC)
        layer_input.DeleteField(id_field)

        # Fermeture du fichier vector_input
        layer_input.SyncToDisk()
        data_source_input.Destroy()

        # Selection du fichier vecteur d'apprentissage
        if overwrite:
            overwrite_str = "-overwrite"
        command = "ogr2ogr -f '%s' %s %s  %s -where \"%s\" " % (format_vector, overwrite_str, vector_output_train_tmp ,vector_input, expression)
        if debug >= 2:
           print(command)
        exit_code = os.system(command)
        if exitCode!= 0:
            print(command)
            raise NameError (cyan + "classifyVector() : " + bold + red + "ogr2ogr. Selection du fichier vecteur d'apprentissage erreur." + endC)

        # Les champs utilisés pour la calssification
        # Exemple : list_feat = ['meanB0' ,  'meanB1' ,   'meanB2' ,  'meanB3' ,  'varB0' ,  'varB1' ,  'varB2' , 'varB3']
        feat = str ("-feat")
        feat +=  " " +  str(''.join(list_feat))

        # Classification :
        # 1) Calculer les statistiques
        command = "otbcli_ComputeOGRLayersFeaturesStatistics -inshp %s -outstats %s " %(segmented_input, outstats)
        command += "%s" %(feat)
        if debug >= 2:
           print(command)
        exitCode = os.system(command)
        if exitCode!= 0:
            print(command)
            raise NameError (cyan + "classifyVector() : " + bold + red + "otbcli_ComputeOGRLayersFeaturesStatistics. See error message above." + endC)

        # 2) Générer le model
        command = "otbcli_TrainVectorClassifier -io.vd %s -io.stats %s -io.out %s  -cfield %s " %(vector_output_train_tmp, outstats, model, input_cfield)
        command += "%s" %(feat)
        if debug >= 2:
           print(command)
        exitCode = os.system(command)
        if exitCode!= 0:
            print(command)
            raise NameError (cyan + "classifyVector() : " + bold + red + "otbcli_TrainVectorClassifier. See error message above." + endC)

        # 3) Produire la classifictaion
        command = "otbcli_VectorClassifier -in %s -instat  %s  -model %s  -cfield %s  -out %s " %(segmented_input, outstats, model,  output_cfield, classif_vector_output)
        command += "%s" %(feat)
        if debug >= 2:
           print(command)
        exitCode = os.system(command)
        if exitCode!= 0:
            print(command)
            raise NameError (cyan + "classifyVector() : " + bold + red + "otbcli_VectorClassifier. See error message above." + endC)

        # Suppression des données intermédiaires
        if not save_results_intermediate:
            # Supression du fichier temporaire de segmentation
            if os.path.isfile(vector_output_train_tmp) :
                removeFile(vector_output_train_tmp)

    print(endC)
    print(bold + green + "## END :  classifyVector" + endC)
    print(endC)

    # Mise à jour du Log
    ending_event = "classifyVector() : Classifictaion vector  ending : "
    timeLine(path_time_log,ending_event)
    return


###########################################################################################################################################
# MISE EN PLACE DU PARSER                                                                                                                 #
###########################################################################################################################################

# Code executé seulement dans le cas ou le script est lancé depuis une ligne de commande
# Il n'est pas executé lors d'un import ClassificationVector.py
# Exemple de lancement en ligne de commande:
# python3 ClassificationVector.py -v "/mnt/Data/10_Agents_travaux_en_cours/Tassadit/6_CLassif_Test/SENTINEL2A_20190817_cut_Seg_450_25_20.shp" -o "/mnt/Data/10_Agents_travaux_en_cours/Tassadit/6_CLassif_Test/SENTINEL2A_20190817_classif.shp" -f "meanB0 meanB1 meanB2 meanB3 varB0 varB1 varB2  varB3" -ex "Class != '0'" -ocf Pred -icf Class

def main(gui=False):
    # Définition des arguments possibles pour l'appel en ligne de commande
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, prog="ClassificationVector", description="\
    Info : Applying a majority filter on one or several images. \n\
    Objectif : Appliquer un filtre majoritaire a une image (classee ou non). \n\
    Example : python ClassificationVector.py -v ../2016-2019_PyrenEOS/DonneesProduites/5_Sentinel2/6_CLassif_Test/SENTINEL2A_20190817_cut_Seg_450_25_20.shp \n\
                                       -o ../2016-2019_PyrenEOS/DonneesProduites/5_Sentinel2/6_CLassif_Test/SENTINEL2A_20190817_output_450_25_20.shp \n\
                                       -f meanB0 meanB1  meanB2 meanB3 varB0 varB1 varB2 varB3 \n\
                                       -icf  Class \n\
                                       -ocf  Pred \n\
                                       -ex  \"Class != '0'\" \n\
                                       -log ../ImagesTestChaine/APTV_05/fichierTestLog.txt" )

    # Paramètres
    parser.add_argument('-v','--vector_input',default="",help="vector input to treat", type=str, required=True)
    parser.add_argument('-o','--classif_vector_output',default="",help="classified vector output to treat", type=str, required=False)
    parser.add_argument('-f','--list_feat',default=" ",help="List of field used to classification", type=str, required = True)
    parser.add_argument('-exp','--expression',default="",help="Example : class '!=' '0'", type=str, required=True)
    parser.add_argument('-icf','--input_cfield',default="",help=" Learning Field", type=str, required=True)
    parser.add_argument('-ocf','--output_cfield',default="Pred",help="classification field", type=str, required=False)
    parser.add_argument('-vef','--format_vector', default="ESRI Shapefile",help="Format of the output file.", type=str, required=False)
    parser.add_argument('-vee','--extension_vector',default=".shp",help="Option : Extension file for vector. By default : '.shp'", type=str, required=False)
    parser.add_argument('-xee','--extension_xml',default=".xml",help="Option : Extension file for xml. By default : '.xml'", type=str, required=False)
    parser.add_argument('-mee','--extension_model',default=".model",help="Option : Extension file for model. By default : '.model'", type=str, required=False)
    parser.add_argument('-log','--path_time_log',default="",help="Name of log", type=str, required=False)
    parser.add_argument('-now','--overwrite',action='store_false',default=True,help="Overwrite files with same names. By default, True", required=False)
    parser.add_argument('-sav','--save_results_inter',action='store_true',default=False,help="Save or delete original image after the majority filter. By default, False", required=False)
    parser.add_argument('-debug','--debug',default=3,help="Option : Value of level debug trace, default : 3 ",type=int, required=False)
    args = displayIHM(gui, parser)


    # RECUPERATION DES ARGUMENTS

    # Récupération de la segmentation d'entrée
    if args.vector_input != None:
        vector_input = args.vector_input
        if not os.path.isfile(vector_input):
            raise NameError (cyan + "classifyVector : " + bold + red  + "File %s not existe!" %(vector_input) + endC)

    # Récupération les champs
    if args.classif_vector_output != None:
        classif_vector_output = args.classif_vector_output

    # Récupération les champs
    if args.list_feat != None:
        list_feat = args.list_feat

    # Le paramétre d'expression
    if args.expression != None:
        expression = args.expression

    # Le champs des classes d'apprentissage
    if args.input_cfield!= None:
        input_cfield = args.input_cfield

    # Le champs de classification en sortie
    if args.output_cfield!= None:
        output_cfield = args.output_cfield

    # Récupération du format du fichier de sortie
    if args.format_vector != None :
        format_vector = args.format_vector

    # Récupération de l'extension des fichiers vecteurs
    if args.extension_vector != None:
        extension_vector = args.extension_vector

    # Récupération de l'extension des fichier model
    if args.extension_model != None:
        extension_model = args.extension_model

    # Récupération de l'extension des fichier xml
    if args.extension_xml != None:
        extension_xml = args.extension_xml

    # Récupération du nom du fichier log
    if args.path_time_log!= None:
        path_time_log = args.path_time_log

    if args.save_results_inter!= None:
        save_results_intermediate = args.save_results_inter

    if args.overwrite!= None:
        overwrite = args.overwrite

    # Récupération de l'option niveau de debug
    if args.debug!= None:
        global debug
        debug = args.debug

    if debug >= 3:
        print(bold + green + "Variables dans le parser" + endC)
        print(cyan + "ClassificationVector : " + endC + "vector_input : " + str(vector_input) + endC)
        print(cyan + "ClassificationVector : " + endC + "classif_vector_output : " + str(classif_vector_output) + endC)
        print(cyan + "ClassificationVector : " + endC + "feat : " + str(list_feat) + endC)
        print(cyan + "ClassificationVector : " + endC + "expression : " + str(expression) + endC)
        print(cyan + "ClassificationVector : " + endC + "input_cfield : " + str(input_cfield) + endC)
        print(cyan + "ClassificationVector : " + endC + "output_cfield : " + str(output_cfield) + endC)
        print(cyan + "ClassificationVector : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "ClassificationVector : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "ClassificationVector : " + endC + "extension_xml : " + str(extension_xml) + endC)
        print(cyan + "ClassificationVector : " + endC + "extension_model : " + str(extension_model) + endC)
        print(cyan + "ClassificationVector : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "ClassificationVector : " + endC + "save_results_inter : " + str(save_results_intermediate) + endC)
        print(cyan + "ClassificationVector : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "ClassificationVector : " + endC + "debug : " + str(debug) + endC)

    # execution de la fonction pour une couhce de segmentation
    classifyVector(vector_input, classif_vector_output, list_feat, expression, input_cfield, output_cfield, path_time_log, format_vector, extension_vector, extension_xml, extension_model, save_results_intermediate, overwrite)

# ================================================

if __name__ == '__main__':
    main(gui=False)





