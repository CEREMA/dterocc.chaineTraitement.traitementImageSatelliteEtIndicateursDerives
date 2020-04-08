#! /usr/bin/env pyt/hon
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerSO/DALETT/SCGSI  All rights reserved.                                                                            #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT DE CALCUL DE SEUILS AUTOMATIQUES SUR UNE LISTE D'IMAGES NDVI                                                                       #
#                                                                                                                                           #
#############################################################################################################################################

'''
Nom de l'objet : CalculSeuilImage.py
Description    :
    Objectif   : Calcule les seuils automatiques d'une liste d'images NDVI

Date de creation : 31/05/2016

Nom de l'objet : runCalculSeuil
Description    :
    Objectif   : Calcule le seuils automatiques d'une image NDVI

Seuillage automatique : Pauline Crombette
Code : Christophe Bez
Adaptation chaîne littoral : Blandine Decherf
Modification : Gilles Fouvet

Date de creation : 12/15/2015
Date de modification : 31/05/2016
'''

from __future__ import print_function
from scipy.signal import argrelextrema
import os, sys, argparse, shutil, numpy, time, errno, fnmatch
import six
import rpy2.robjects as ro
from rpy2.robjects.packages import importr
from Lib_display import bold, black, red, green, yellow, blue, magenta, cyan, endC, displayIHM
from Lib_log import timeLine

debug = 4

###########################################################################################################################################
# FONCTION calculSeuilImage                                                                                                               #
###########################################################################################################################################
# ROLE:
#    Calcul des seuils automatiques d'images NDVI (appel de la fonction runCalculSeuil, sur plusieurs images éventuellement)
#
# ENTREES DE LA FONCTION :
#    input_ndvi_im_list : Liste des images NDVI dont le seuil est à déterminer
#    output_dir : Répertoire de sortie pour les fichiers
#    path_time_log : le fichier de log de sortie
#    save_results_intermediate : fichiers de sorties intermediaires non nettoyées, par defaut = False
#    overwrite : supprime ou non les fichiers existants ayant le meme nom
#
# SORTIES DE LA FONCTION :
#    Les fichiers contenant les seuils calculés automatiquement
#    Eléments modifiés aucun
#

def calculSeuilImage(input_ndvi_im_list, output_dir, path_time_log, save_results_intermediate, overwrite):

    # Mise à jour du Log
    starting_event = "CalculSeuilImage() : Select Calcul seuil image starting : "
    timeLine(path_time_log,starting_event)

    # Affichage des paramètres
    if debug >= 3:
        print(bold + green + "Variables dans le TDCSeuil - Variables générales" + endC)
        print(cyan + "calculSeuilImage : " + endC + "input_ndvi_im_list : " + str(input_ndvi_im_list) + endC)
        print(cyan + "calculSeuilImage : " + endC + "output_dir : " + str(output_dir) + endC)
        print(cyan + "calculSeuilImage : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "calculSeuilImage : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "calculSeuilImage : " + endC + "overwrite : " + str(overwrite) + endC)

    # Initialisation des variables
    seuils_centreclasse_list = []
    seuils_borneinf_list = []

    for ndvi_image in input_ndvi_im_list :
        seuils = runCalculSeuil(ndvi_image, output_dir, save_results_intermediate)
        if debug >= 1:
            print(seuils)
        seuils_centreclasse_list.append(seuils[0])
        seuils_borneinf_list.append(seuils[1])

    if debug >= 1:
        for i in range(len(input_ndvi_im_list)):
            print(cyan + "calculSeuilImage() : " + endC + bold + green + "Image : " + str(input_ndvi_im_list[i]) + "Seuil centre classe : "+ str(seuils_centreclasse_list[i]) + "Seuil borne inf : " + str(seuils_borneinf_list[i]) + endC)

    # Mise à jour du Log
    ending_event = "CalculSeuilImage() : Select Calcul seuil image ending : "
    timeLine(path_time_log,ending_event)

    return

###########################################################################################################################################
# FONCTION runCalculSeuil                                                                                                                 #
###########################################################################################################################################
# ROLE:
#    Calcul des seuils automatiques d'images NDVI
#
# ENTREES DE LA FONCTION :
#    ndviPath : image NDVI dont le seuil est à déterminer
#    output_dir : Répertoire de sortie pour les fichiers
#    save_results_intermediate : fichiers de sorties intermediaires non nettoyées, par defaut = True
#
# SORTIES DE LA FONCTION :
#    Les fichiers contenant les seuils calculés automatiquement
#    Eléments modifiés aucun
#

def runCalculSeuil(ndviPath, output_dir, save_results_intermediate=True):

    # Import des librairies R
    rGdal = importr('rgdal')
    rClassInt = importr('classInt')
    rRaster = importr('raster')

    # Initialisation des constantes
    EXTENSION_TEXT = ".txt"
    METHOD = "fisher"
    NB_ECHANTILLONS = 100000
    NB_CLASS = 30
    NB_FISHER_ITERATION = 5
    REP_INFO = "info_seuils_auto"

    # Initialisation des variables
    indice = 0
    endIteration = False
    centreclass_list = []
    borneinf_list = []
    ndvi_image = os.path.splitext(os.path.basename(ndviPath))[0]
    repertory_info = output_dir + os.sep + REP_INFO

    # Création du répertoire de sortie s'il n'existe pas déjà
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Nettoyage du répertoire info
    if os.path.exists(repertory_info):
        shutil.rmtree(repertory_info)
    os.makedirs(repertory_info)

    if debug >=1 :
        print(cyan + "runCalculSeuil() : " + endC + "Calcul du seuil pour le fichier NDVI: " + ndviPath)
    start_time = time.time()

    try:
        img=rRaster.raster(ndviPath)
    except:
        print(cyan + "runCalculSeuil() : " + endC + bold + red + "Erreur lors du lancement de la fonction: raster." + endC, file=sys.stderr)
        sys.exit(1)

    if debug >=1 :
        print(cyan + "runCalculSeuil() : " + endC + "Création du repertoire: "+output_dir+"\r\n")

    if not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
        except OSError as error:
            if error.errno != errno.EEXIST:
                print(cyan + "runCalculSeuil() : " + endC + bold + red + "Erreur lors de la création de: " + output_dir + endC, file=sys.stderr)
                sys.exit(1)

    if debug >=1 :
        print(bold + green + "Lancement du calcul du seuil" + endC)
    for i in range (20,NB_CLASS+1):
        if debug >=1 :
            print(bold + green + "---> Itération: " + str(i) + "\r\n" + endC)
        try:
            if debug >=1 :
                print(bold + green + "Exécution de sampleRandom" + endC)
            sample = ro.r("na.omit")(rRaster.sampleRandom(img, NB_ECHANTILLONS))
        except:
            print(cyan + "runCalculSeuil() : " + bold + red + "Erreur lors du lancement de la fonction: sampleRandom." + endC, file=sys.stderr)
            sys.exit(1)

        try:
            if debug >=1 :
                print(bold + green + "Exécution de classIntervals" + endC)
            classes = rClassInt.classIntervals(sample,n=i,style=METHOD)
        except:
            print(cyan + "runCalculSeuil() : " + bold + red + "Erreur lors du lancement de la fonction: classIntervals." + endC, file=sys.stderr)
            sys.exit(1)

        try:
            if debug >=1 :
                print(bold + green + "Exécution de jenks_tests" + endC)
            tai = rClassInt.jenks_tests(classes)
        except:
            print(cyan + "runCalculSeuil() : " + bold + red + "Erreur lors du lancement de la fonction: jenks_tests." + endC, file=sys.stderr)
            sys.exit(1)

        if debug >=1 :
            print(bold + green + "---> TAI" + endC)
            print(str(tai))

        fic = repertory_info + os.sep + ndvi_image + "_F_TAI_" + METHOD + EXTENSION_TEXT

        try:
            with open(fic, "a") as f:
                if int(tai[0]) < 10:
                    sep=" "
                else:
                    sep=""
                f.write (sep+str(tai[0])+'   ' + str(round(tai[1],3)) + ' '*(8-len(str(round(tai[1],3)))) + str(round(tai[2]))+'\r\n')
        except:
            print(cyan + "runCalculSeuil() : " + bold + red + "Erreur lors de l'ouverture du fichier: " + fic + endC, file=sys.stderr)
            sys.exit(1)

        if tai[2] < 0.9:
            if debug >= 3 :
                print(cyan + "runCalculSeuil() : " + endC + "TAI inférieur à 0.90: " + str(tai[2]))
                print("")
        else:
            if indice < NB_FISHER_ITERATION:
                brks = ro.r['round'](classes[1],digits=3)
                lenbrks = len(brks)

                intLabels = list(range(0,lenbrks-1))
                for j in range (0,lenbrks-1):
                    # Formatage sommaire pour sortie fichier texte
                    if brks[j] >= 0:
                        sep1 = ' '
                    else:
                        sep1 = ''
                    if brks[j+1] >= 0:
                        sep2 = ' '
                    else:
                        sep2 = ''
                    intLabels[j] = sep1  + str(brks[j]) + ' '*(6-len(str(abs(brks[j])))) + " <->  " + sep2 +str(brks[j+1]) + ' '*(8-len(str(abs(brks[j+1]))))

                tab = ro.r['as.data.frame'](intLabels)

                a = ro.r['hist'](classes[0],breaks=classes[1],xlab="x",main='NDVI')

                tabCount = a[1]

                if debug >=1 :
                    print("    Intervalle             Population")
                    print("")
                    for j in range (0,lenbrks-1):
                        print(intLabels[j]+ '      ' + str(tabCount[j]))
                    print("")


                localmin = argrelextrema(numpy.array(tabCount),numpy.less)[0].tolist()

                if len(localmin)>1:
                    if debug >= 3:
                        print(cyan + "runCalculSeuil() : " + endC + "Nombre de minimum locaux --> " + str(len(localmin)))
                        print("")

                    borneminsup = localmin[1]+1

                    centreclasse = (brks[localmin[1]]+brks[borneminsup])/2
                    borneinf = brks[localmin[0]]
                    if debug >= 1 :
                        print("Centre classe ------> " + str(centreclasse))
                        print("Borne inf     ------> " + str(borneinf))
                        print("")

                    fic = repertory_info + os.sep + ndvi_image + "_F_n" + str(i) + "_Class" + EXTENSION_TEXT
                    try:
                        with open(fic, "a") as f:
                            f.write ('     Intervalle          Population\r\n')
                            f.write ('\r\n')
                            for j in range (0,lenbrks-1):
                                f.write (intLabels[j]+ '      '+str(tabCount[j])+'\r\n')
                    except:
                        print(cyan + "runCalculSeuil() : " + bold + red + "Erreur lors de l'ouverture du fichier: " + fic + endC, file=sys.stderr)
                        sys.exit(1)

                    centreclass_list.append(centreclasse)
                    borneinf_list.append(borneinf)

                    indice += 1
                else:
                    if len(localmin) == 1:
                        if debug >= 3:
                            print(cyan + "runCalculSeuil() : " + endC + "Nombre de minimum locaux --> " + str(len(localmin)))
                            print("")

                        borneminsup = localmin[0]+1
                        centreclasse = (brks[localmin[0]]+brks[borneminsup])/2
                        if debug >=1 :
                            print("Centre classe ---> " + str(centreclasse))
                            print("Borne inf     ---> " + str(brks[localmin[0]]))
                            print("")

                        fic = repertory_info + os.sep + ndvi_image + "_F_n" + str(i) + "_Class" + EXTENSION_TEXT
                        try:
                            with open(fic, "a") as f:
                                f.write ('     Intervalle          Population\r\n')
                                for j in range (0,lenbrks-1):
                                    f.write (intLabels[j]+ '      ' + str(tabCount[j])+'\r\n')
                        except:
                            print(cyan + "runCalculSeuil() : " +  bold + red + "Erreur lors de l'ouverture du fichier: " + fic + endC, file=sys.stderr)
                            sys.exit(1)

                        centreclass_list.append(centreclasse)
                        borneinf_list.append(brks[localmin[0]])

                        indice += 1

                    else:
                        centreclass_list.append(-9999)
                        borneinf_list.append(rGdal-9999)

                fic = repertory_info + os.sep + ndvi_image + "_F_TimeProcess" + EXTENSION_TEXT
                try:
                    with open(fic, "a") as f:
                        f.write ("Temps process, " + ' '*(3-len(str(i)))+str(i)+" classes: " + str(round(time.time() - start_time)) + " secondes.\r\n")
                except:
                    print(cyan + "runCalculSeuil() : " + bold + red + "Erreur lors de l'ouverture du fichier: " + fic + endC, file=sys.stderr)
                    sys.exit(1)
            else:
                endIteration = True
        if endIteration:
            break

    if len(centreclass_list) > 0:
        moyenne_centreclasse_seuil = round(sum(centreclass_list) / float(len(centreclass_list)),3)
        moyenne_borneinf_seuil = round(sum(borneinf_list) / float(len(borneinf_list)),3)
        if debug >= 1 :
            print("Moyenne du seuil (centre classe) : " + str(moyenne_centreclasse_seuil))
            print("Moyenne du seuil (borne inf) : " + str(moyenne_borneinf_seuil))
            print("")
        fic = repertory_info + os.sep + ndvi_image + "_Moyenne" + EXTENSION_TEXT
        try:
            with open(fic, "a") as f:
                if six.PY2:
                    text = unicode(u"\r\nNombre d'échantillons: "+str(NB_ECHANTILLONS)+"\r\n").encode('latin 1')
                else :
                    text = "\r\nNombre d'échantillons: "+str(NB_ECHANTILLONS)+"\r\n"
                f.write (text)
                f.write ("Nombre de classes: "+str(NB_CLASS)+"\r\n")
                if six.PY2:
                    text = unicode(u"Nombre d'itérations avec TAI > 0.9: " + str(NB_FISHER_ITERATION) + "\r\n").encode('latin 1')
                else :
                    text = "Nombre d'itérations avec TAI > 0.9: " + str(NB_FISHER_ITERATION) + "\r\n"
                f.write (text)
                f.write ("\r\nTemps total de traitement:  " + str(round(time.time() - start_time))+" secondes.\r\n")
                f.write ('\r\nMoyenne du seuil (centre classe) : '+ str(moyenne_centreclasse_seuil)+'\r\n')
                f.write ('\r\nMoyenne du seuil (borne inf) : ' + str(moyenne_borneinf_seuil)+'\r\n')
        except:
            print(cyan + "runCalculSeuil() : " + red + bold + "Erreur lors de l'ouverture du fichier: " + fic + endC, file=sys.stderr)
            sys.exit(1)

        fic = repertory_info + os.sep + "Summary_Moyennes" + EXTENSION_TEXT
        try:
            with open(fic, "a") as f:
                f.write ("\r\nImage NDVI : "+str(ndvi_image)+"\r\n")
                if six.PY2:
                    text = unicode(u"\r    Nombre d'échantillons: "+str(NB_ECHANTILLONS)+"\r\n").encode('latin 1')
                else :
                    text = "\r    Nombre d'échantillons: "+str(NB_ECHANTILLONS)+"\r\n"
                f.write (text)
                f.write ("    Nombre de classes: "+str(NB_CLASS)+"\r\n")
                if six.PY2:
                    text = unicode(u"    Nombre d'itérations avec TAI > 0.9: " + str(NB_FISHER_ITERATION )+ "\r\n").encode('latin 1')
                else :
                    text = "    Nombre d'itérations avec TAI > 0.9: " + str(NB_FISHER_ITERATION )+ "\r\n"
                f.write (text)
                f.write ("\r    Temps total de traitement:  "+str(round(time.time() - start_time))+" secondes.\r\n")
                f.write ('\r    Moyenne du seuil (centre classe) : '+str(moyenne_centreclasse_seuil)+'\r\n')
                f.write ('\r    Moyenne du seuil (borne inf) : '+str(moyenne_borneinf_seuil)+'\r\n')
        except:
            print(cyan + "runCalculSeuil() : " + red + bold + "Erreur lors de l'ouverture du fichier: " + fic + endC, file=sys.stderr)
            sys.exit(1)

    fic = repertory_info + os.sep + ndvi_image + "_F_TimeProcess" + EXTENSION_TEXT
    try:
        with open(fic, "a") as f:
            f.write ("\r\nTemps total de traitement:  " + str(round(time.time() - start_time)) + " secondes.\r\n")
    except:
        print(cyan + "runCalculSeuil() : " + red + bold + "Erreur lors de l'ouverture du fichier: " + fic + endC, file=sys.stderr)
        sys.exit(1)

    print(bold + green + "Fin du calcul du seuil.\n" + endC)

    return [moyenne_centreclasse_seuil, moyenne_borneinf_seuil]

###########################################################################################################################################
# MISE EN PLACE DU PARSER                                                                                                                 #
###########################################################################################################################################

# Code executé seulement dans le cas ou le script est lancé depuis une ligne de commande
# Il n'est pas executé lors d'un import CalculSeuilImage.py
# Exemple de lancement en ligne de commande:
# python /home/scgsi/Documents/ChaineTraitement/ScriptsLittoral/CalculSeuilImage.py -i /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Test_TDCSeuil/image1.tif /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Test_TDCSeuil/image2.tif -outd /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Test_TDCSeuil/Result2

def main(gui=False):

    parser = argparse.ArgumentParser(prog="CalculSeuilImage", description=" \
    Info : Creating files containing the threshold automatically calculated (fisher algorith) for each input NDVI image. \n\
    Objectif : Calcul du seuil automatique pour les images NDVI d'une liste en entrée. \n\
    Example : python /home/scgsi/Documents/ChaineTraitement/ScriptsLittoral/CalculSeuilImage.py \n\
                            -i /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Test_TDCSeuil/image1.tif /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Test_TDCSeuil/image2.tif \n\
                            -outd /mnt/Donnees_Etudes/30_Stages/2016/Stage_Littoral_chaine/05_Travail/Test_TDCSeuil/Result2")

    parser.add_argument('-i','--input_ndvi_im_list', default="", nargs="+", help="List of NDVI images to process.", type=str, required=True)
    parser.add_argument('-outd','--output_dir', default="",help="Output directory.", type=str, required=True)
    parser.add_argument('-log','--path_time_log',default=os.getcwd()+ os.sep + "log.txt",help="Option : Name of log. By default : log.txt", type=str, required=False)
    parser.add_argument('-sav','--save_results_inter',action='store_true',default=False,help="Option : Save or delete intermediate result after the process. By default, False", required=False)
    parser.add_argument('-now','--overwrite',action='store_false',default=True,help="Option : Overwrite files with same names. By default : True", required=False)
    parser.add_argument('-debug','--debug',default=3,help="Option : Value of level debug trace, default : 3 ",type=int, required=False)
    args = displayIHM(gui, parser)

    # Récupération des images ndvi à traiter
    if args.input_ndvi_im_list != None :
        input_ndvi_im_list = args.input_ndvi_im_list

    # Récupération du dossier des fichiers en sortie
    if args.output_dir != None :
        output_dir = args.output_dir

    # Récupération du nom du fichier log
    if args.path_time_log != None:
        path_time_log = args.path_time_log

    # Ecrasement des fichiers
    if args.save_results_inter != None:
        save_results_intermediate = args.save_results_inter

    if args.overwrite != None:
        overwrite = args.overwrite

    # Récupération de l'option niveau de debug
    if args.debug!= None:
        global debug
        debug = args.debug

    # Affichage des arguments récupérés
    if debug >= 3:
        print(bold + green + "Variables dans le parser" + endC)
        print(cyan + "CalculSeuilImage : " + endC + "input_ndvi_im_list : " + str(input_ndvi_im_list) + endC)
        print(cyan + "CalculSeuilImage : " + endC + "output_dir : " + str(output_dir) + endC)
        print(cyan + "CalculSeuilImage : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "CalculSeuilImage : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "CalculSeuilImage : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "CalculSeuilImage : " + endC + "debug : " + str(debug) + endC)

    # Fonction générale
    calculSeuilImage(input_ndvi_im_list, output_dir, path_time_log, save_results_intermediate, overwrite)

# ================================================

if __name__ == '__main__':
  main(gui=False)
