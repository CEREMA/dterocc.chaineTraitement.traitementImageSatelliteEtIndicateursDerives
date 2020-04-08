# -*- coding: utf-8 -*-
#!/usr/bin/python

#############################################################################
# Copyright (©) CEREMA/DTerSO/DALETT/SCGSI  All rights reserved.            #
#############################################################################

#############################################################################
#                                                                           #
# FONCTIONS EN LIEN AVEC LA MANIPULATION DE FICHIERS TEXTES OU BINAIRES     #
#                                                                           #
#############################################################################

# IMPORTS UTILES
import sys, os, glob, datetime, re
import six
if six.PY2:
    from dbfpy import dbf
else:
    from dbfpy3 import dbf
import csv
import numpy
import pysal
import pandas
from simpledbf import Dbf5

from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC
from Lib_math import findPositionList

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 3 : affichage maximum de commentaires lors de l'execution du script. Intermédiaire : affichage intermédiaire
debug = 2

#########################################################################
# FONCTION readTextFileBySeparator()                                    #
#########################################################################
#   Role : Fonction qui lit un fichier texte
#   Entrées :
#       text_file_name : Nom du fichier texte que l'on souhaite transformer en liste. Exemple : "Test.txt"
#       separator : Identification du séparateur de découpage du texte. Exemple : separator = " "
#   Sortie :
#       Text_List : Liste de strings tel que Text_List (2,3) = 3ème groupe de mots (au regard du séparateur) de la ligne 2 de text_file_name

def readTextFileBySeparator(text_file_name, separator):

    Text_List = []

    try:
    # Ouverture du fichier
        f = open(text_file_name, 'r')
    # Gestion des cas de base
    except IOError as e:
        print(cyan + "readTextFileBySeparator() : " + bold + red + "IO Erreur (%s) : %s" %(e.errno, e.strerror) + endC)
    except:
        print(cyan + "readTextFileBySeparator() : " +  bold + red + "Erreur non determinee :" +  sys.exc_info()[0] + endC)
        raise
    else:

        while True:
            # Lecture du contenu
            line = f.readline()

            # Gestion de l'arrêt de la lecture a la fin du fichier
            if not line:
                break

            # Intégration du contenu de chaque ligne dans une liste
            composants = []
            list = line.split(separator)

            for s in list:
                if (s != '' and s != "\r\n" and s != '\n'):
                    if s[-1:] == "\n":
                        composants.append(s[:-1])
                    else:
                        composants.append(s)

            # Ajout de la variable finale comme sortie de la fonction
            if composants != []:
                Text_List.append(composants)

        # Fermeture du fichier
        f.close()

    # Retour de la fonction
    return Text_List

#########################################################################
# FONCTION readReallocationTable()                                      #
#########################################################################
#   Role : Fonction qui lit une table de reaffectation en txt et qui en sort la liste des micro-classes àsuprimer,
#          à reaffecter, sous echantilloner, à reaffecter, sous echantilloner et les macroclasses de reaffectation
#   Entrées :
#       reallocation_table : Nom du fichier de la table de réallocation
#   Sortie :
#       supp_class_list : liste des classes supprimées
#       reaff_class_list : liste des classes réaffectées
#       macro_reaff_class_list : liste des macro classes réaffectées
#       sub_sampling_class_list : list des classes à sous echantilloner
#       sub_sampling_number_list : list des valeurs du nombre de sous echantillons pour le cas du sous echantillonage

def readReallocationTable(reallocation_table, sub_sampling_defaut_number = 3) :

    # Définition des variables de sortie
    supp_class_list = []
    reaff_class_list = []
    sub_sampling_class_list = []
    sub_sampling_number_list = []
    macro_reaff_class_list = []

    # Transcription du fichier text en tableau
    data_matrix = readTextFileBySeparator(reallocation_table, ";")

    # Parcours du tableau
    for i in range(1,len(data_matrix)):
        if (data_matrix[i] != []) and (data_matrix[i][1] != "A") and (data_matrix[i][1] != "D"):
            if (int(data_matrix[i][1]) == -1):                   # Cas suppression de classe
                supp_class_list.append(int(data_matrix[i][0]))
            elif (int(data_matrix[i][1]) == -2):                 # Cas sous échantillonage de classe
                sub_sampling_class_list.append(int(data_matrix[i][0]))
                if len (data_matrix[i]) >= 3:
                    sub_sampling_number_list.append(int(data_matrix[i][2]))
                else :
                    sub_sampling_number_list.append(int(sub_sampling_defaut_number))  # Si le nombre de sous classes n'est pas précisé dans la table de reaffectation, il est par défaut mis à sub_sampling_defaut_number
            else:                                               # Autre cas (cas reaffectation)
                reaff_class_list.append(int(data_matrix[i][0]))
                macro_reaff_class_list.append(int(data_matrix[i][1]))

    return supp_class_list, reaff_class_list, macro_reaff_class_list, sub_sampling_class_list, sub_sampling_number_list

#########################################################################
# FONCTION readTextFile()                                               #
#########################################################################
#   Role : Fonction qui lit un fichier texte
#   Entrées :
#       text_file_name :  Nom du fichier texte que l'on souhaite lire. Exemple : "Test.txt"
#   Sortie :
#       le contenu text du fichier

def readTextFile(text_file_name):
    try:
        textFile = open(text_file_name,"r")
    except Exception:
        raise NameError(cyan + "readTextFile() : " + endC + bold + red + "Can't open file : " + text_file_name + '\n' + endC)
    text = textFile.read()
    textFile.close()
    return text

#########################################################################
# FONCTION writeTextFile()                                              #
#########################################################################
#   Role : Fonction qui ecrit un fichier texte
#   Entrées :
#       text_file_name : Nom du fichier texte que l'on souhaite créer. Exemple : "Test.txt". Attention, si le fichier existe déjà, il sera écrasé
#       text : Texte que l'on souhaite inclure dans text_file_name. Exemple : text = "Exemple de Texte"

def writeTextFile(text_file_name, text):
    try:
        textFile = open(text_file_name,"w")
    except Exception:
        raise NameError(cyan + "writeTextFile() : " + endC + bold + red + "Can't create file : " + text_file_name + '\n' + endC)
    textFile.write(text)
    textFile.flush()
    textFile.close()

    return

#########################################################################
# FONCTION appendTextFile()                                             #
#########################################################################
#   Role : Fonction qui concatene du texte a un fichier texte
#   Entrées :
#       text_file_name : Nom du fichier texte. Exemple : "Test.txt". Si le fichier n'existe pas, il sera créé
#       text : Texte que l'on souhaite inclure à la fin de text_file_name. Exemple : text = "Exemple de Texte"

def appendTextFile(text_file_name, text):
    try:
        textFile = open(text_file_name,"a")
    except Exception:
        raise NameError(cyan + "appendTextFile() : " + endC + bold + red + "Can't open/create file : " + text_file_name + '\n' + endC)
    textFile.write(text)
    textFile.flush()
    textFile.close()

    return

#########################################################################
# FONCTION appendTextFileCR()                                           #
#########################################################################
#   Role : Fonction qui concatene du texte a un fichier texte avec CR en fin de ligne
#   Entrées :
#       text_file_name : Nom du fichier texte. Exemple : "Test.txt". Si le fichier n'existe pas, il sera créé
#       text : Texte que l'on souhaite inclure à la fin de text_file_name. Exemple : text = "Exemple de Texte"

def appendTextFileCR(text_file_name, text):
    appendTextFile(text_file_name, text + "\n")

    return

#########################################################################
# FONCTION convertDbf2Csv()                                             #
#########################################################################
#   Role : Conversion de format de fichier DBF en format CSV (passe tous les noms des colonnes en majuscule)
#   Paramètres :
#      dbf_file : Nom du fichier DBF d'entrée
#      csv_file : Nom du fichier CSV de sortie

def convertDbf2Csv(dbf_file, csv_file):

    if os.path.exists(dbf_file):

        in_db = dbf.Dbf(dbf_file)
        fieldnames_list = []
        for field in in_db.header.fields:
            fieldnames_list.append(field.name)

        if six.PY2:
            out_csv = csv.writer(open(csv_file,'wb'))
            out_csv.writerow(fieldnames_list)
            for rec in in_db:
                out_csv.writerow(rec.fieldData)
        else :
            with open(csv_file, 'w', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames_list)
                writer.writeheader()
                for rec in in_db:
                    fieldData_dico = {}
                    for index in range(len(fieldnames_list)):
                        name_col = fieldnames_list[index]
                        value = rec.fieldData[index]
                        fieldData_dico[name_col] = value
                    writer.writerow(fieldData_dico)

        in_db.close()

    else :
        print(cyan + "convertDbf2Csv() : " + endC +bold + yellow + "Impossible de lire le fichier dbf : " + dbf_file + " . Fichier inexistant!" + endC)
    return

#########################################################################
# FONCTION convertDbf2CsvBis()                                          #
#########################################################################
#   Role : Conversion de format de fichier DBF en format CSV en passant par les dataframes
#          AVANTAGE concerve les minuscule majuscule sur les noms des colonnes
#   Paramètres :
#      dbf_file : Nom du fichier DBF d'entrée
#      csv_file : Nom du fichier CSV de sortie
#      sep : caractere sparateur du fichier csv, par defaut : ","

def convertDbf2CsvBis(dbf_file, csv_file, sep=","):

    if os.path.exists(dbf_file):
        dbf_data = Dbf5(dbf_file)
        dataframe_dbf = dbf_data.to_dataframe()
        dataframe_dbf.to_csv(csv_file)

        csv_file_tmp = os.path.splitext(csv_file)[0] +  "_tmp" +  os.path.splitext(csv_file)[1]

        # On va recopier toutes les lignes du CSV
        # dans un nouveau CSV en supprimant la 1ere colonne
        in_file = open(csv_file)
        in_csv = csv.reader(in_file, delimiter=sep)

        out_file = open(csv_file_tmp, 'w+')
        out_csv = csv.writer(out_file, delimiter=sep, quoting=csv.QUOTE_NONNUMERIC)

        for row in in_csv:
            # Ici, petite feinte pk Python copie par référence,
            # donc on prend la valeur de la ligne et non la ligne directement
            current_row = row[:]
            current_row.pop(0)
            out_csv.writerow(current_row)
        in_file.close()
        out_file.close()

        # On supprime le CSV original
        os.remove(csv_file)
        # On renomme le nouveau CSV avec le nom de l'ancien
        os.rename(csv_file_tmp, csv_file)

    else :
        print(cyan + "convertDbf2CsvBis() : " + endC +bold + yellow + "Impossible de lire le fichier dbf : " + dbf_file + " . Fichier inexistant!" + endC)
    return

#########################################################################
# FONCTION saveDataFrame2Dbf()                                             #
#########################################################################
#   Role : Sauve garde une dataframe en fichier au format DBF
#   Paramètres :
#      data_frame_input : La dataframe d'entrée
#      dbf_file : Nom du fichier DBF de sortie
#      sep : caractere sparateur du fichier csv, par defaut : ","

def saveDataFrame2Dbf(data_frame_input, dbf_file, sep=","):

    if six.PY2:
        type2spec = {int: ('N', 20, 0),
                     numpy.int64: ('N', 20, 0),
                     float: ('N', 36, 15),
                     numpy.float64: ('N', 36, 15),
                     str: ('C', 14, 0),
                     unicode: ('C', 14, 0)}
    else :
        type2spec = {int: ('N', 20, 0),
                     numpy.int64: ('N', 20, 0),
                     float: ('N', 36, 15),
                     numpy.float64: ('N', 36, 15),
                     str: ('C', 14, 0) }

    # Ecriture du contenu de la dataframe vers un fichier dbf
    types = [type(data_frame_input[i].iloc[0]) for i in data_frame_input.columns]
    specs = [type2spec[t] for t in types]

    if six.PY2:
        db_desc = pysal.open(dbf_file, 'w')
    else :
        db_desc = pysal.lib.io.fileio.FileIO.open(dbf_file, 'w')
    db_desc.header = list(data_frame_input.columns)
    db_desc.field_spec = specs
    for i, row in data_frame_input.T.iteritems():
        db_desc.write(row)
    db_desc.close()

    return

#########################################################################
# FONCTION convertCsv2Dbf()                                             #
#########################################################################
#   Role : Conversion de format de fichier CSV en format DBF
#   Paramètres :
#      csv_file : Nom du fichier CSV d'entrée
#      dbf_file : Nom du fichier DBF de sortie
#      sep : caractere sparateur du fichier csv, par defaut : ","

def convertCsv2Dbf(csv_file, dbf_file, sep=","):

    if os.path.exists(csv_file):

        if debug >=3:
            print(cyan + "convertCsv2Dbf() : " + endC + bold + green + "Start " + endC)

        # Lecture du fichier csv
        data_frame_csv = pandas.read_csv(csv_file, sep)

        # Ecriture du contenu de la dataframe issu du fichier csv vers un fichier dbf
        saveDataFrame2Dbf(data_frame_csv, dbf_file)

        if debug >=3:
            print(cyan + "convertCsv2Dbf() : " + endC + bold + green + "End " + endC)
    else :
        print(cyan + "convertCsv2Dbf() : " + endC + bold + yellow + "Impossible de lire le fichier csv : " + csv_file + " . Fichier inexistant!" + endC)
    return

#########################################################################
# FONCTION readQueryFile()                                              #
#########################################################################
#   Role : Fonction de lecture de requetes dans un fichier texte
#   Entrées :
#       query_file_name : nom du fichier que l'on souhaite lire

def readQueryFile(query_file_name):
    queryList = []
    try:
        queryFile = open(query_file_name,"r+")
    except Exception:
        raise NameError(cyan + "readQueryFile() : " + endC + bold + red + "Can't open file : " + query_file_name + '\n' + endC)
    currentQuery = ""
    lines = queryFile.readlines()

    for l in lines:
        # Si la ligne ne commence pas par une balise '#' et n'est pas vide
        if l[0] != '#' and len(l) != 1:
            currentQuery += " " + l[:-1]
        elif "#EndQuery" in l:
            queryList.append(currentQuery)
            currentQuery = ""
    queryFile.close()

    return queryList

#########################################################################
# FONCTION readConfusionMatrix()                                        #
#########################################################################
#   Role : Permet de lire un fichier de matrice de confusion
#   Entrées :
#       matrix_file : Nom du fichier de matrice de confusion que l'on souhaite lire
#   Sortie : :
#       matrix : La matrice lu
#       class_ref_list : La liste des micro classes de référence
#       class_pro_list : La liste des micro classes produites

def readConfusionMatrix(matrix_file) :
    if debug >=3:
        print(cyan + "readConfusionMatrix() : " + bold + green + "Confusion matrix reading..." + '\n' + endC)

    try:
        fh = open(matrix_file,"r")
    except Exception:
        raise NameError(cyan + "readConfusionMatrix() : " + endC + bold + red + "Can't open file : " + text_file_name + '\n' + endC)
    lines_list = fh.readlines()
    i = 0
    matrix = []
    class_ref_list = []
    class_pro_list = []
    for line in lines_list:
        if line[0] != '#':
            j = 0
            matrix.append([])
            values_list = line.split(',')
            for value in values_list:
                matrix[i].append(float(value))
                j+=1
            i+=1
        else:
            class_line = line.split(':')
            if class_line[0] == "#Reference labels (rows)":
                class_ref_list = class_line[1].split(',')
            else:
                class_pro_list = class_line[1].split(',')

    # Modifier la derniere classe pour supprimer le charactere "\n"
    nb_classes_pro = len(class_pro_list)
    if nb_classes_pro > 0:
        class_pro_list[nb_classes_pro-1] = class_pro_list[nb_classes_pro-1].split("\n")[0]
        nb_classes_ref = len(class_ref_list)
        class_ref_list[nb_classes_ref-1] = class_ref_list[nb_classes_ref-1].split("\n")[0]

        if debug >=3:
            print(cyan + "readConfusionMatrix() : " + bold + green + "Confusion matrix readed" + '\n' + endC)
    else :
        print(cyan + "readConfusionMatrix() : " + bold + yellow + "Matrice de confusion vide!" + endC)

    return matrix, class_ref_list, class_pro_list

#########################################################################
# FONCTION correctMatrix()                                              #
#########################################################################
# Role : Verifier le nombre de microclasses en entree et le nombre de microclasses en sortie
# Par defaut, l'entree et la sortie sont de même taille. Mais dans les tests,
# on trouve des cas dans lesquel le nombre d'entree et de sortie ne sont pas de même taille.
# Dans certains cas, quelque microclasses ont disparu apres la classification,
# dans ce cas, on ne peut pas calculer les indicateurs de la qualite.
# Il faut alors remplir les donnees pour les microclasses disparues (a zero).
# le nombre d'entree et de sortie sont alors de même taille.
# ENTREES
#     class_ref_list : La liste des micro classes de référence
#     class_pro_list : La liste des micro classes produites
#     matrix : La matrice que l'on souhaite corrigé
#     no_data_value : Valeur de  pixel du no data par défaut = 0
# PARAMETRES DE RETOUR
#     correct_matrix : La matrice corrigé
#     class_missing_list : La liste des micro classes manquantes

def correctMatrix(class_ref_list, class_pro_list, matrix, no_data_value=0):

    if debug >=3:
        print(cyan + "correctMatrix() : " + bold + green + "Confusion matrix correcting..." + '\n' + endC)

    nb_ref = len(class_ref_list)

    index_missing_list = []
    class_missing_list = []

    # Chercher si une ligne no data existe si c'est le cas correction de la matrice
    if str(no_data_value) in class_pro_list :
        pos_col_nodata = class_pro_list.index(str(no_data_value))
        for line in matrix:
            del line[pos_col_nodata]

    # Identifier les micro classes maquantes
    for i in range(nb_ref):
        if findPositionList(class_pro_list, class_ref_list[i]) == -1:
            index_missing_list.append(i)
            class_missing_list.append(class_ref_list[i])

    if debug >=3:
        print(cyan + "correctMatrix() : " + bold + green + "Index missing class : " + str(index_missing_list) + endC)
        print(cyan + "correctMatrix() : " + bold + green + "Missing microclass  : " + str(class_missing_list) + endC)


    # Remplir la nouvelle matrice de confusion corrigé
    nb_line = nb_ref
    nb_col = nb_ref

    correct_matrix = []

    for i in range(nb_line):
        line = []
        col_pos_act = 0
        for j in range(nb_col):
            if findPositionList(index_missing_list, j) != -1:
                if debug >=5:
                    print("[%d:%d] : remplir 0" %(i,j))
                line.append(0)
            else:
                if debug >=5:
                    print("[%d:%d] : remplir %f" %(i,j,matrix[i][col_pos_act]))
                line.append(matrix[i][col_pos_act])
                col_pos_act = col_pos_act + 1
        correct_matrix.append(line)

    if debug >=3:
        print(cyan + "correctMatrix() : " + bold + green + "Confusion matrix corrected" + '\n' + endC)
    return correct_matrix, class_missing_list


#########################################################################
# FONCTION cleanSpaceText()                                             #
#########################################################################
#   Role : Fonction qui nettoye les espaces en debut et fin de chaine
#   Entrées :
#       text_input : le text en entrée pouvant contenir des espaces en début et/ou en fin de chaineExemple : text = "  Exemple de Texte "
#   Sortie : :
#       return text_output : Le texte netoyé des espaces de debut et fin. Exemple : text = "Exemple de Texte"

def cleanSpaceText(text_input):
    text_temp = cleanBeginSpaceText(text_input[::-1])
    text_output = cleanBeginSpaceText(text_temp[::-1])

    return text_output

#########################################################################
# FONCTION cleanBeginSpaceText()                                        #
#########################################################################
#   Role : Fonction qui nettoye les espaces en debut uniquement
#   Entrées :
#       text_input : le text en entrée pouvant contenir des espaces en début et/ou en fin de chaineExemple : text = "  Exemple de Texte"
#   Sortie : :
#       return text_output : Le texte netoyé des espaces de debut et fin. Exemple : text = "Exemple de Texte"

def cleanBeginSpaceText(text_input):
    text_output = ""
    begin = False
    for char in str(text_input) :
        if char != ' ' or begin :
            begin = True
            text_output = text_output + char

    return text_output

#########################################################################
# FONCTION extractDico()                                                #
#########################################################################
#   Role : Fonction particuliere qui transforme une liste en sortie : de parser en dictionaire utilisable
#   Entrées :
#       strings_list : Liste de strings dont le contenu concaténé forme la liste que l'on souhaite récupérer
#   Sortie : :
#       dico_output : dictonaire résultat

def extractDico(strings_list):
    if debug >= 4:
        print("DEBUG_dico_1 : " , strings_list)
    dico_output = {}
    for tmp_txt_class in strings_list:
        if debug >= 4:
            print("DEBUG_dico_2     : " , tmp_txt_class)
        info_text_list = []
        for text_bd in tmp_txt_class.split(':'):
            if debug >= 4:
                print("DEBUG_dico_3         : " , text_bd)
            info_text_list.append(text_bd)
        # Creation du dictionaire (classe macro)  de liste  (BD - size_buffer)
        bds_list = []
        for id_text in range(1, len(info_text_list)):
            data_list = []
            for elem in info_text_list[id_text].split(','):
                if debug >= 4:
                    print("DEBUG_dico_4             : " , elem)
                data_list.append(elem)
            bds_list.append(data_list)
        dico_output[info_text_list[0]] = bds_list

    return dico_output

#########################################################################
# FONCTION replaceEndName()                                             #
#########################################################################
#   Role : Fonction qui modifie la fin d'un string
#          Exemple d'application : modification de la fin du nom d'une image
#   Entrées :
#       text : text (string) que l'on souhaite modifier. Exemple : "Image_01_raw.tif"
#       previous_end : texte que l'on souhaite remplacer dans le string. Exemple : "raw.tif"
#       new_end : texte que l'on souhaite mettre à la place dans le string. Exemple : "merged.tif"
#   Exemple :
#       replaceEndName("Image_01.raw_tif", "raw.tif", "merged.tif") donne "Image_01.merged_tif"

def replaceEndName(text, previous_end, new_end):
    length = len(text)
    if previous_end != None:
        l=len(previous_end)
        text = text[:length-l] + new_end
    else :
        text = text[:length-4] + new_end # On considère qu'on enlève seulement une extension de 3 caractères, par exemple ".tif"

    return text

#########################################################################
# FONCTION regExReplace()                                               #
#########################################################################
#   Rôle : Remplace les caractères spéciaux
#   Entrées :
#       text : chaîne de caractère en entrée, pouvant contenir des caractères spéciaux
#       regex : liste des caractères autorisés (au format re). Par défaut : '[a-zA-Z0-9_]'
#       regex_replace : caractère de remplacement pour les caractères spéciaux non-autorisés. Par défaut : '_'
#   Sortie :
#       text : nouvelle chaîne de caractères, sans caractères spéciaux

def regExReplace(text, regex='[a-zA-Z0-9_]', regex_replace='_'):

    for letter in text:
        if re.match(regex, letter) is None:
            text = re.sub(letter, regex_replace, text)

    return text

