#! /usr/bin/python
# -*- coding: utf-8 -*-

#############################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.               #
#############################################################################

#############################################################################
#                                                                           #
# FONCTIONS DE MODIFICATION DE FICHIERS OU DE REPERTOIRES                   #
#                                                                           #
#############################################################################
"""
 Ce module défini des fonctions de manipulation, modification de fichiers et de répertoires.
"""

import filecmp, os, sys, shutil, copy, glob, time, subprocess
from osgeo import ogr
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC

debug = 1

#########################################################################
# FONCTION cleanTempData()                                              #
#########################################################################
def cleanTempData(rep_name):
    """
    #   Role : Suppression de l'arborescence d'un repertoire temporaire
    #   Paramètres en entrée :
    #              rep_name : répertoire temporaire à nettoyer
    """

    if os.path.exists(rep_name):
        shutil.rmtree(rep_name)
        time.sleep(1)  # Ajout d'un temps de latence d'une seconde pour eviter des bugs dus à la mise à jour des dossiers
    if not os.path.isdir(rep_name):
        os.makedirs(rep_name)
    return

#########################################################################
# FONCTION removeDir()                                                  #
#########################################################################
def removeDir(rep_name):
    """
    #   Role : Suppression d'un repertoire et sous repertoire (vide!)
    #   Paramètres :
    #      rep_name : Nom du repertoire à supprimer
    """

    # Supression du repertoire
    if os.path.exists(rep_name):
        os.removedirs(rep_name)
    return

#########################################################################
# FONCTION deleteDir()                                                  #
#########################################################################
def deleteDir(rep_name):
    """
    #   Role : Suppression d'un repertoire même plein et recursif
    #   Paramètres :
    #      rep_name : Nom du repertoire à supprimer
    """

    # Supression du repertoire
    if os.path.exists(rep_name):
        shutil.rmtree(rep_name, ignore_errors=True)
    return

#########################################################################
# FONCTION copyDir()                                                    #
#########################################################################
def copyDir(rep_name_input, rep_name_output):
    """
    #   Role : copie d'un repertoire
    #   Paramètres :
    #      rep_name_input : Nom du repertoire source
    #      rep_name_output : Nom du repertoire destination
    """

    # copie du repertoire
    if os.path.exists(rep_name_input):
        shutil.copytree(rep_name_input, rep_name_output)
    return

#########################################################################
# FONCTION renameFile()                                                 #
#########################################################################
def renameFile(old_filename, new_filename):
    """
    #   Role : Renommage de fichiers
    #   Paramètres :
    #      old_filename : Ancien nom
    #      new_filename : Nouveau nom
    """

    # Renomage du fichier
    if os.path.exists(old_filename):
        os.rename(old_filename, new_filename)
    else :
        print(bold + yellow + "Impossible de renomer le fichier : " + old_filename + " . Fichier inexistant!" + endC)
    return

#########################################################################
# FONCTION removeFile()                                                 #
#########################################################################
def removeFile(del_filename):
    """
    #   Role : Suppression de fichier
    #   Paramètres :
    #      filename : Nom du fichier à supprimer
    """

    # Supression du fichier
    if os.path.exists(del_filename):
        os.remove(del_filename)
    return

#########################################################################
# FONCTION moveFile()                                                   #
#########################################################################
def moveFile(input_file_name, output_file_name):
    """
    #   Role : Deplacement de fichier
    #   Paramètres :
    #      input_file_name : Nom du fichier à déplacer
    #      output_file_name : Nom du fichier de sortie déplacé
    """

    # Déplacer le fichier
    if os.path.exists(input_file_name):
        shutil.move(input_file_name, output_file_name)
    else :
        print(bold + yellow + "Impossible de déplacer le fichier : " + input_file_name + " . Fichier inexistant!" + endC)
    return

#########################################################################
# FONCTION copyFile()                                                   #
#########################################################################
def copyFile(input_file_name, output_file_name):
    """
    #   Role : copie de fichier
    #   Paramètres :
    #      input_file_name : Nom du fichier à copier
    #      output_file_name : Nom du fichier de sortie copié
    """

    # Copier le fichier
    if os.path.exists(input_file_name):
        shutil.copy2(input_file_name, output_file_name)
    else :
        print(bold + yellow + "Impossible de copier le fichier : " + input_file_name + " . Fichier inexistant!" + endC)
    return

#########################################################################
# FONCTION removeVectorFile()                                           #
#########################################################################
def removeVectorFile(del_vector_name, format_vector='ESRI Shapefile'):
    """
    #   Role : Suppression de fichier vecteur
    #   Paramètres :
    #      del_vector_name : Nom du fichier vecteur à supprimer
    #      format_vector : format du fichier vecteur (par defaut : format shapefile)
    """

    # Récupération du driver
    driver = ogr.GetDriverByName(format_vector)
    # Supression du vecteur
    if os.path.exists(del_vector_name):
        driver.DeleteDataSource(del_vector_name)
    return

#########################################################################
# FONCTION copyVectorFile()                                             #
#########################################################################
def copyVectorFile(input_vector_name, output_vector_name, format_vector='ESRI Shapefile'):
    """
    #   Role : Copy de fichier vecteur
    #   Paramètres :
    #      input_vector_name : Nom du fichier vecteur à copier
    #      output_vector_name : Nom du fichier vecteur de sortie recopié
    #      format_vector : format du fichier vecteur (par defaut : format shapefile)
    """

    # Récupération du driver
    driver = ogr.GetDriverByName(format_vector)
    # Copie du vecteur
    if os.path.exists(input_vector_name):
        data_source = driver.Open(input_vector_name, 0)  # en lecture
        if os.path.exists(output_vector_name):
            driver.DeleteDataSource(output_vector_name)
        driver.CopyDataSource(data_source,output_vector_name)
        data_source.Destroy()
    else :
        print(bold + yellow + "Impossible de copier le fichier : " + input_vector_name + " . Fichier inexistant!" + endC)
    return

#########################################################################
# FONCTION renameVectorFile()                                           #
#########################################################################
def renameVectorFile(input_vector_name, output_vector_name):
    """
    #   Role : Renomage de fichier vecteur
    #   Paramètres :
    #      input_vector_name : Nom du fichier vecteur à copier
    #      output_vector_name : Nom du fichier vecteur de sortie renomé
    """

    # Renomage du fichier
    if os.path.exists(input_vector_name):
        base_name_input = os.path.splitext(input_vector_name)[0]
        base_name_output = os.path.splitext(output_vector_name)[0]
        os.rename(base_name_input + ".dbf", base_name_output + ".dbf")
        os.rename(base_name_input + ".prj", base_name_output + ".prj")
        os.rename(base_name_input + ".shx", base_name_output + ".shx")
        os.rename(base_name_input + ".shp", base_name_output + ".shp")
    else :
        print(bold + yellow + "Impossible de renomer le fichier : " + input_vector_name + " . Fichier inexistant!" + endC)
    return

#########################################################################
# FONCTION moveVectorFile()                                             #
#########################################################################
def moveVectorFile(input_vector_name, output_vector_name):
    """
    #   Role : Deplacementy de fichier vecteur
    #   Paramètres :
    #      input_vector_name : Nom du fichier vecteur à déplacer
    #      output_vector_name : Nom du fichier vecteur de sortie déplacé
    """

    # Déplacer le fichier
    if os.path.exists(input_vector_name):
        base_name_input = os.path.splitext(input_vector_name)[0]
        base_name_output = os.path.splitext(output_vector_name)[0]
        shutil.move(base_name_input + ".dbf", base_name_output + ".dbf")
        shutil.move(base_name_input + ".prj", base_name_output + ".prj")
        shutil.move(base_name_input + ".shx", base_name_output + ".shx")
        shutil.move(base_name_input + ".shp", base_name_output + ".shp")
    else :
        print(bold + yellow + "Impossible de déplacer le fichier : " + input_vector_name + " . Fichier inexistant!" + endC)
    return

#########################################################################
# FONCTION getSubRepRecursifList()                                      #
#########################################################################
def getSubRepRecursifList(input_rep):
    """
    #   Role : Fournir dla liste de tous les sous répertoire en recursif d'un repertoire d'entrée
    #   Paramètres :
    #      input_rep : Nom du répertoir d'entrée
    #   Return le liste de tout les sous répertoir
    """

    # Variable
    sub_rep = [] # Recevra les noms des sous-répertoires

    # Trouver le contenu du répertoire input_rep
    for repertory in os.listdir(input_rep):
        path_rep = os.path.join(input_rep, repertory)
        if os.path.isdir(path_rep):
            temp_sub_list = getSubRepRecursifList(path_rep)
            if not temp_sub_list == []:
                sub_rep.extend(temp_sub_list)
            sub_rep.append(path_rep)

    # La liste des sous répertoire en sortie
    return sub_rep

########################################################################
# FONCTION read7zArchiveStructure()                                    #
########################################################################
def find_header(split_line):
    return 'Name' in split_line and 'Date' in split_line
def all_hyphens(line):
    return set(line) == set('-')

def read7zArchiveStructure(input_archive):
    """
    #   Rôle : Fournir la liste des répertoires et fichiers contenu dans une archive en entrée
    #   Info : Issu d'une question Stack Overflow (https://stackoverflow.com/questions/32797851/how-to-read-contents-of-7z-file-using-python)
    #   Paramètres :
    #      input_archive : Nom de l'archive en entrée
    #   Retourne la liste des répertoires et fichiers contenu dans une archive
    """

    byte_result = subprocess.check_output('7z l %s' % input_archive, shell=True)
    str_result = byte_result.decode('utf-8')
    line_result = str_result.splitlines()

    found_header = False
    found_first_hyphens = False
    files = []
    for line in line_result:

        # After the header is a row of hyphens
        # and the data ends with a row of hyphens
        if found_header:
            is_hyphen = all_hyphens(''.join(line.split()))

            if not found_first_hyphens:
                found_first_hyphens = True
                # now the data starts
                continue

            # Finding a second row of hyphens means we're done
            if found_first_hyphens and is_hyphen:
                return files

        split_line = line.split()

        # Check for the column headers
        if find_header(split_line):
            found_header=True
            continue

        if found_header and found_first_hyphens:
            files.append(split_line[-1])
            continue

    raise ValueError("We parsed this zipfile without finding a second row of hyphens")
