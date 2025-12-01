#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT Receive Image from FTP                                                                                                             #
#                                                                                                                                           #
#############################################################################################################################################

"""
Nom de l'objet : ReceiveFTP.py
Description :
-------------
Objectif : Exécuter une reception de donnée par TFP automatique

Date de creation : 15/11/2016
----------
Histoire :
----------
Origine : Nouveau
15/11/2016 : Création
-----------------------------------------------------------------------------------------------------
Modifications :

------------------------------------------------------
A Reflechir/A faire :

"""

# IMPORT DES BIBLIOTHEQUES, VARIABLES ET FONCTIONS UTILES
from __future__ import print_function
import os, sys, glob, time, argparse, string, ftplib
from osgeo import gdal
from osgeo.gdalnumeric import *
from osgeo.gdalconst import *
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_text import appendTextFileCR, readTextFileBySeparator
from Lib_log import timeLine
from Lib_file import removeFile

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 3

###########################################################################################################################################
# FONCTION receiveFtp()                                                                                                                   #
###########################################################################################################################################
def receiveFtp(server_ftp, port_ftp, login_ftp, password_ftp, path_ftp, local_path, file_error, path_time_log, save_results_intermediate=False, overwrite=True):
    """
    # ROLE:
    #     Recevoir des données par FTP
    #
    # ENTREES DE LA FONCTION :
    #     server_ftp : l'adresse du seveur FTP
    #     port_ftp : numero de port du serveur
    #     login_ftp : le login de connexion
    #     password_ftp : le mot de passe de connexion
    #     path_ftp : le chemin de connexion de la données à récuperer
    #     local_path : le chemin local de sauvegarde de la donnée
    #     file_error : le fichier de sortie liste des fichiers en erreur
    #     path_time_log : le fichier de log de sortie
    #     save_results_intermediate : fichiers de sorties intermediaires nettoyees, par defaut = False
    #     overwrite : écrase si un fichier existant a le même nom qu'un fichier de sortie, par defaut a True
    #
    # SORTIES DE LA FONCTION :
    #     N.A
    #
    """

    # Mise à jour du Log
    starting_event = "receiveFtp() : Connection ftp starting : "
    timeLine(path_time_log,starting_event)

    if debug >= 2:
        print(endC)
        print(bold + green + "## START : RECEIVE FTP" + endC)
        print(endC)

    if debug >= 3:
        print(bold + green + "receiveFtp() : Variables dans la fonction" + endC)
        print(cyan + "receiveFtp() : " + endC + "server_ftp : " + str(server_ftp) + endC)
        print(cyan + "receiveFtp() : " + endC + "login_ftp : " + str(login_ftp) + endC)
        print(cyan + "receiveFtp() : " + endC + "port_ftp : " + str(port_ftp) + endC)
        print(cyan + "receiveFtp() : " + endC + "password_ftp : " + str(password_ftp) + endC)
        print(cyan + "receiveFtp() : " + endC + "path_ftp : " + str(path_ftp) + endC)
        print(cyan + "receiveFtp() : " + endC + "local_path : " + str(local_path) + endC)
        print(cyan + "receiveFtp() : " + endC + "file_error : " + str(file_error) + endC)
        print(cyan + "receiveFtp() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "receiveFtp() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "receiveFtp() : " + endC + "overwrite : " + str(overwrite) + endC)

    # FTP connexion
    ftp = connectionFtp(server_ftp, port_ftp, login_ftp, password_ftp)
    if ftp != None :
        getFtp(ftp, path_ftp, local_path + os.sep + path_ftp, path_ftp, file_error)
        if os.path.isfile(file_error) :
            relaunchFtp(ftp, file_error, local_path)
        closeFtp(ftp)

    if debug >= 2:
        print(endC)
        print(bold + green + "## END : RECEIVE FTP" + endC)
        print(endC)

    # Mise à jour du Log
    ending_event = "receiveFtp() : Connection ftp ending : "
    timeLine(path_time_log,ending_event)

    return

###########################################################################################################################################
# FONCTION connectionFtp()                                                                                                                #
###########################################################################################################################################
    """
    # ROLE:
    #     Connexion FTP
    #
    # ENTREES DE LA FONCTION :
    #     server_ftp : l'adresse du seveur FTP
    #     port_ftp : numero de port du serveur
    #     login_ftp : le login de connexion
    #     password_ftp : le mot de passe de connexion
    #
    """

def connectionFtp(server_ftp, port_ftp, login_ftp, password_ftp):
    ftp = None
    if debug >= 2:
        print(cyan + "connectionFtp() : " + endC + "Server Port : " +  str(server_ftp) + " " +  str(port_ftp))
        print(cyan + "connectionFtp() : " + endC + "Login Pwd : " + str(login_ftp) + " " + str(password_ftp))
    try:
        ftp = ftplib.FTP()
        ftp.connect(server_ftp, port_ftp)
        time.sleep( 1 )
        ftp.login(login_ftp, password_ftp)
        time.sleep( 1 )
        ftp.set_pasv(True)

        if debug >= 2:
            print(cyan + "connectionFtp() : " + endC + "OK connected! ")
    except:
        ftp = None
        print(cyan + "connectionFtp() : " + bold + red + "Error connection FTP to server : " + server_ftp  + endC, file=sys.stderr)
    return ftp

###########################################################################################################################################
# FONCTION closeFtp()                                                                                                                     #
###########################################################################################################################################
def closeFtp(ftp):
    """
    # ROLE:
    #     Deconnexion FTP
    #
    # ENTREES DE LA FONCTION :
    #     ftp : le lien ftp
    #
    """

    ftp.quit()
    return

###########################################################################################################################################
# FONCTION getFtp()                                                                                                                       #
###########################################################################################################################################
def getFtp_old(ftp, path_ftp, local_path, all_path, file_error):
    """
    # ROLE:
    #     Chargemnt des données par ftp
    #
    # ENTREES DE LA FONCTION :
    #     ftp : le lien ftp
    #     path_ftp : le répértoire distant
    #     local_path : le répértoire de travail local
    #     all_path : les chemins d'acces
    #     file_error : le fichier d'erreur
    #
    """

    EXT_LIST = ['.tif','.tiff','.ecw','.jp2','.asc']
    data_list = []

    repertory_ftp = os.path.dirname(path_ftp)
    if repertory_ftp != "" :
        ftp.cwd(repertory_ftp)
        data_list.append(os.path.basename(path_ftp))
    elif repertory_ftp == "" and os.path.splitext(os.path.basename(path_ftp))[1] == "" :
        ftp.cwd(path_ftp)
        ftp.retrlines("LIST", data_list.append)
    else :
        data_list.append(path_ftp)

    for data in data_list :

        data_tmp = data.split(' ')
        filename = data_tmp[len(data_tmp)-1]

        if data[0] == 'd' :
            print(cyan + "getFtp() : " + green + "Get directory : " + filename + endC)
            getFtp(ftp, filename, local_path + os.sep + filename, all_path + os.sep + filename, file_error)
            ftp.cwd("..")
        else :
            if debug >= 1:
                print(cyan + "getFtp() : " + green + "Download file : " + filename + endC)
            try:
                local_filename = local_path + os.sep + filename
                filename_error = all_path + os.sep + filename
                if not os.path.isdir(local_path):
                    os.makedirs(local_path)
                ftp.retrbinary("RETR " + filename ,open(local_filename, 'wb').write)
            except:
                print(cyan + "getFtp() : " + bold + red + "Error during download " + filename + " from FTP" + endC, file=sys.stderr)
                appendTextFileCR(file_error, filename_error)
                if os.path.isfile(local_filename) :
                    removeFile(local_filename)

            extent_name = os.path.splitext(os.path.basename(local_filename))[1].lower()

            if extent_name in EXT_LIST :
                test_image = imageControl(local_filename)
                if not test_image :
                    appendTextFileCR(file_error, filename_error)
                    if os.path.isfile(local_filename) :
                        removeFile(local_filename)
    return

def getFtp(ftp, path_ftp, local_path, all_path, file_error):
    """
    # ROLE:
    #     Chargement des données par FTP
    #
    # ENTREES DE LA FONCTION :
    #     ftp : le lien FTP
    #     path_ftp : le répertoire distant
    #     local_path : le répertoire de travail local
    #     all_path : les chemins d'accès
    #     file_error : le fichier d'erreur
    """

    EXT_LIST = ['.tif', '.tiff', '.ecw', '.jp2', '.asc']
    data_list = []

    repertory_ftp = os.path.dirname(path_ftp)
    filename = os.path.basename(path_ftp)

    if repertory_ftp:
        ftp.cwd(repertory_ftp)
        data_list.append(filename)
    else:
        if os.path.splitext(filename)[1] == "":
            ftp.cwd(path_ftp)
            ftp.retrlines("LIST", data_list.append)
        else:
            data_list.append(path_ftp)

    for data in data_list:
        # Ensure data is non-empty and split safely
        if not data.strip():  # Skip empty or invalid data
            continue

        data_tmp = data.split()
        if not data_tmp:  # Skip empty or malformed lines
            continue

        filename = data_tmp[-1]

        # Check if it's a directory (first character of FTP response)
        if data[0] == 'd':
            print(cyan + "getFtp() : " + green + "Get directory: " + filename + endC)
            getFtp(ftp, filename, os.path.join(local_path, filename), os.path.join(all_path, filename), file_error)
            ftp.cwd("..")
        else:  # It's a file
            if debug >= 1:
                print(cyan + "getFtp() : " + green + "Download file: " + filename + endC)
            try:
                local_filename = os.path.join(local_path, filename)
                filename_error = os.path.join(all_path, filename)

                # Create directory if it doesn't exist
                if not os.path.isdir(local_path):
                    os.makedirs(local_path)

                # Download file
                with open(local_filename, 'wb') as local_file:
                    ftp.retrbinary(f"RETR {filename}", local_file.write)

            except Exception as e:
                print(f"Error downloading {filename}: {e}", file=sys.stderr)
                appendTextFileCR(file_error, filename_error)
                if os.path.isfile(local_filename):
                    removeFile(local_filename)

            # Validate image file type
            extent_name = os.path.splitext(filename)[1].lower()
            if extent_name in EXT_LIST:
                test_image = imageControl(local_filename)
                if not test_image:
                    appendTextFileCR(file_error, filename_error)
                    if os.path.isfile(local_filename):
                        removeFile(local_filename)

    return

###########################################################################################################################################
# FONCTION imageControl()                                                                                                                 #
###########################################################################################################################################
def imageControl(filename):
    """
    # ROLE:
    #     Teste sur l'image telechargée
    #
    # ENTREES DE LA FONCTION :
    #     filename : l'image à vérifier
    #
    """

    print(cyan + "imageControl() : " + endC + "Control image file : " + filename + endC)
    ok = True
    try:
        dataset = gdal.Open(filename, GA_ReadOnly)
        if dataset is not None:
            # Get metadata
            metaData = dataset.GetMetadata()
            # Get X and Y size
            cols = dataset.RasterXSize
            rows = dataset.RasterYSize
            # Get band
            bands = dataset.RasterCount
            for num_band in range(bands):
                band = dataset.GetRasterBand(num_band + 1)
                # Read the data into numpy arrays
                data = BandReadAsArray(band)

    except RuntimeError:
        print(cyan + "imageControl() : " + bold + red + "Erreur Impossible d'ouvrir ou de lire le fichier : " + filename + endC, file=sys.stderr)
        ok = False
    if ok and dataset is None :
        ok = False

    return ok

###########################################################################################################################################
# FONCTION relaunchFtp()                                                                                                                  #
###########################################################################################################################################
def relaunchFtp(ftp, file_error, local_path):
    """
    # ROLE:
    #     Recharger les données en erreur
    #
    # ENTREES DE LA FONCTION :
    #     ftp : le lien ftp
    #     file_error : le fichier d'erreur
    #     local_path : le répértoire de travail
    #
    """

    files_list = readTextFileBySeparator(file_error, '\n')
    for files in files_list:
        file_ftp = files[0]
        repertory = os.path.dirname(file_ftp)
        filename = os.path.basename(file_ftp)
        local_filename = local_path + os.sep + file_ftp
        print(cyan + "relaunchFtp() : " + endC + "Tentative de re-chargement de image file : " + file_ftp + endC)
        try:
            ftp.cwd(repertory)
            ftp.retrbinary("RETR " + filename ,open(local_filename, 'wb').write)
            ftp.cwd("/")
        except RuntimeError:
            print(cyan + "relaunchFtp() : " + bold + red + "Rechargement impossible du fichier : " + file_ftp + endC, file=sys.stderr)
            continue
    return

###########################################################################################################################################
# MISE EN PLACE DU PARSER                                                                                                                 #
###########################################################################################################################################

# Code executé seulement dans le cas ou le script est lancé depuis une ligne de commande
# Il n'est pas executé lors d'un import ReceiveFTP.py
# Exemple de lancement en ligne de commande:
# python ReceiveFTP.py -adrs gilles.fouvet@cerema.fr -adrr gilles.fouvet@cerema.fr -serv smtp.m2.e2.rie.gouv.fr -port 25 -pass xxxxxx -subj sujet_du_message -msg Conenu_du_message
def main(gui=False):

    # Définition des différents paramètres du parser
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,  prog="ReceiveFTP", description="\
    Info : Receive data by protocol FTP since address FTP server \n\
    Objectif : Recevoir des données par FTP. \n\
    Example : python ReceiveFTP.py -serv 172.22.128.197 \n\
                                 -port 21 \n\
                                 -login DterMedr \n\
                                 -pass xxxxx \n\
                                 -path DterMed \n\
                                 -files file1.txt file2.txt \n\
                                 -dest /mnt/Data/gilles.fouvet/Test_FTP \n\
                                 -err /mnt/Data/gilles.fouvet/Test_FTP/listFilesDownload.err \n\
                                 -log /mnt/Data/gilles.fouvet/Test_FTP/fileTest.log")

    parser.add_argument('-serv','--server_ftp',default="",help="Address url of the server FTP ex: 172.22.128.197", type=str, required=True)
    parser.add_argument('-port','--port_ftp',default=21,help="Number of port of server mail. By default : '20'", type=int, required=False)
    parser.add_argument('-login','--login_ftp',default="",help="Login ftp of connection", type=str, required=True)
    parser.add_argument('-pass','--password_ftp',default="",help="Password ftp of connection", type=str, required=True)
    parser.add_argument('-path','--path_ftp',default="/",help="The path ftp of data source.  By default, directory of connection", type=str, required=False)
    parser.add_argument('-dest','--local_path',default=".",help="The local path to save data. By default, '.'", type=str, required=False)
    parser.add_argument('-err','--file_error',default="listFiles.err",help="Name of file error", type=str, required=False)
    parser.add_argument('-log','--path_time_log',default="",help="Name of log", type=str, required=False)
    parser.add_argument('-sav','--save_results_inter',action='store_true',default=False,help="Save or delete intermediate result after the process. By default, False", required=False)
    parser.add_argument('-now','--overwrite',action='store_false',default=True,help="Overwrite files with same names. By default, True", required=False)
    parser.add_argument('-debug','--debug',default=3,help="Option : Value of level debug trace, default : 3 ", type=int, required=False)
    args = displayIHM(gui, parser)

    # RECUPERATION DES ARGUMENTS

    # Récupération de l'adresse du sever FTP
    if args.server_ftp!= None:
        server_ftp = args.server_ftp

    # Récupération du port du sever FTP
    if args.port_ftp!= None:
        port_ftp = args.port_ftp

    # Récupération du login de connexion
    if args.login_ftp!= None:
        login_ftp = args.login_ftp

    # Récupération du mot de passe de connexion
    if args.password_ftp!= None:
        password_ftp = args.password_ftp

    # Récupération du chemin du répertoire ou du fichier à récupere
    if args.path_ftp!= None:
        path_ftp = args.path_ftp

    # Récupération du chemin local pour l'écriture des données
    if args.local_path!= None:
        local_path = args.local_path

    # Récupération du nom du fichier d'erreur
    if args.file_error!= None:
        file_error = args.file_error
        if file_error == 'listFiles.err' :
            file_error = local_path + os.sep + file_error

    # Récupération du nom du fichier log
    if args.path_time_log!= None:
        path_time_log = args.path_time_log

    # Récupération de l'option écrasement
    if args.save_results_inter != None:
        save_results_intermediate = args.save_results_inter

    if args.overwrite!= None:
        overwrite = args.overwrite

    # Récupération de l'option niveau de debug
    if args.debug!= None:
        global debug
        debug = args.debug

    if debug >= 3:
        print(bold + green + "ReceiveFTP : Variables dans le parser" + endC)
        print(cyan + "ReceiveFTP : " + endC + "server_ftp : " + str(server_ftp) + endC)
        print(cyan + "ReceiveFTP : " + endC + "port_ftp : " + str(port_ftp) + endC)
        print(cyan + "ReceiveFTP : " + endC + "login_ftp : " + str(login_ftp) + endC)
        print(cyan + "ReceiveFTP : " + endC + "password_ftp : " + str(password_ftp) + endC)
        print(cyan + "ReceiveFTP : " + endC + "path_ftp : " + str(path_ftp) + endC)
        print(cyan + "ReceiveFTP : " + endC + "local_path : " + str(local_path) + endC)
        print(cyan + "ReceiveFTP : " + endC + "file_error : " + str(file_error) + endC)
        print(cyan + "ReceiveFTP : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "ReceiveFTP : " + endC + "save_results_inter : " + str(save_results_intermediate) + endC)
        print(cyan + "ReceiveFTP : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "ReceiveFTP : " + endC + "debug : " + str(debug) + endC)

    # EXECUTION DE LA FONCTION
    # Si le dossier de sortie n'existent pas, on le crée
    if not os.path.isdir(local_path+os.sep+path_ftp):
        os.makedirs(local_path+os.sep+path_ftp)

    # execution de la fonction
    receiveFtp(server_ftp, port_ftp, login_ftp, password_ftp, path_ftp, local_path, file_error, path_time_log, save_results_intermediate, overwrite)

# ================================================

if __name__ == '__main__':
  main(gui=False)
