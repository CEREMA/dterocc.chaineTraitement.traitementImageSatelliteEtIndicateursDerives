#! /usr/bin/python
# -*- coding: utf-8 -*-

#############################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.               #
#############################################################################

#############################################################################
#                                                                           #
# FONCTIONS EN LIEN AVEC LE LOG                                             #
#                                                                           #
#############################################################################
"""
 Ce module défini des fonctions de log utile à la chaîne.
"""

import time
from datetime import datetime
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC

##############################################################
# FONCTION D'AFFICHAGE DE L'HEURE                            #
##############################################################

def timeLine(path_timelog,step):
    """
    #   Role : Fonction pour chronometrer une tache, placer le code DebutTache = datetime.now() avant la tache a chronometrer.
    #   Paramètres en entrée :
    #      path_timelog : nom du chemin et du fichier log
    #      step : texte affiché devant l'heure sauvegardée
    """
    hour = time.strftime('%d/%m/%y %H:%M:%S',time.localtime())
    time_str = step + hour + '\n'
    if path_timelog != "":
        logfile = open(path_timelog, 'a')
        logfile.write(time_str)
        logfile.close()
    else :
        print(blue + time_str + endC)
    return


def TimeLineDuration(path_timelog,step,startingDate_Task):
    """
    #   Role : Fonction pour chronometrer une tache, placer le code DebutTache = datetime.now() avant la tache a chronometrer.
    #          Puis aprés la tache apeller la fonction et lui passer la variable DebutTache en 3eme position : startingDate_Task.
    #   Paramètres en entrée :
    #      path_timelog : nom du chemin et du fichier log
    #      step : texte affiché devant l'heure sauvegardée
    #      startingDate_Task : date de départ
    """
    ####################################
    # CODE A INTEGRER DANS LE SCRIPT   #
    # En début de script               #
    # from datetime import datetime    #
    #                                  #
    # AVANT LE LANCEMENT DE LA TACHE : #
    # DebutTache = datetime.now()      #
    # ##################################

    startingDate_Task_time = str(startingDate_Task.time())[:-7]

    FinTache = datetime.now()
    FinTache_Time = str(FinTache.time())[:-7]

    print("Heure de début de la tache: " + startingDate_Task_time + "       Heure de fin de la tache: " + FinTache_Time)

    duree =  FinTache - startingDate_Task
    duree = str(duree) [:-7]
    print("Duree de la tache : " + duree)

    logfile = open(path_timelog, 'a')
    time_str = step + "," + startingDate_Task_time + "," + FinTache_Time + "," + duree +'\n'
    logfile.write(time_str)
    logfile.close()

    return
