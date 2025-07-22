#! /usr/bin/python
# -*- coding: utf-8 -*-

#############################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.               #
#############################################################################

#############################################################################
#                                                                           #
# FONCTIONS EN LIEN AVEC L'AFFICHAGE D'INFORMATIONS                         #
#                                                                           #
#############################################################################
"""
Ce module défini des fonctions d'affichage utiles a la chaine.
"""

import os, platform, subprocess, threading
from Lib_operator import terminateThread, killTreeProcess
import PIL
from PIL import Image, ImageTk
import matplotlib as mpl
import matplotlib.pyplot as plt
from pylab import *
import pandas as pd

import six
if six.PY2:
    from PyQt4 import QtGui
    from Tkinter import *
    import argparseui
else :
    from PyQt5 import QtGui
    from tkinter import *

debug = 1

##############################################################
# MISE EN FORME DES MESSAGES DANS LA CONSOLE                 #
##############################################################

# Pour y accéder dans un script : from fcts_Affichage import bold,black,red,green,yellow,blue,magenta,cyan,endC
osSystem = platform.system()
if 'Windows' in osSystem :
    # EFFETS
    bold = ""
    talic = ""
    underline = ""
    blink = ""
    rapidblink = ""
    beep = ""

    # COULEURS DE TEXTE
    black = ""
    red = ""
    green = ""
    yellow = ""
    blue = ""
    magenta = ""
    cyan = ""
    white = ""

    # COULEUR DE FOND
    BGblack = ""
    BGred = ""
    BGgreen = ""
    BGyellow = ""
    BGblue = ""
    BGmagenta = ""
    BGcyan = ""
    BGwhite = ""

    endC = ""

elif 'Linux' in osSystem :
    # EFFETS
    bold = "\033[1m"
    italic = "\033[3m"
    underline = "\033[4m"
    blink = "\033[5m"
    rapidblink = "\033[6m"
    beep = "\007"

    # COULEURS DE TEXTE
    black = "\033[30m"
    red = "\033[31m"
    green = "\033[32m"
    yellow = "\033[33m"
    blue = "\033[34m"
    magenta = "\033[35m"
    cyan = "\033[36m"
    white = "\033[37m"

    # COULEUR DE FOND
    BGblack = "\033[40m"
    BGred = "\033[41m"
    BGgreen = "\033[42m"
    BGyellow = "\033[43m"
    BGblue = "\033[44m"
    BGmagenta = "\033[45m"
    BGcyan = "\033[46m"
    BGwhite = "\033[47m"

    endC = "\033[0m"

########################################################################
# FONCTION matplotlibGraphic()                                         #
########################################################################
def matplotlibGraphic(input_csv_file, output_png_file, graph_title, x_col, x_title, y_col_list, y_title, y_legend_list, encoding_file='latin-1', separator_file=';', label_col="", y_col_list_bis=[], y_title_bis="", y_legend_list_bis=[], axhline=None, axvline=None, fontsize=20):
    """
    #   Rôle : Cette fonction de génération d'un graphique à partir de données csv.
    #   Paramètres :
    #       input_csv_file : fichier CSV en entrée
    #       output_png_file : fichier PNG en sortie
    #       graph_title : titre du graphique
    #       x_col : nom du champ X
    #       x_title : titre de l'axe X
    #       y_col_list : nom du (des) champ(s) Y
    #       y_title : titre de l'axe Y
    #       y_legend_list : légende(s) du (des) champ(s) Y
    #       encoding_file : encodage du fichier CSV en entrée. Par défaut : 'latin-1'
    #       separator_file : séparateur de champ du fichier CSV en entrée. Par défaut : ';'
    #       label_col : nom du champ contenant les étiquettes. Par défaut : ""
    #       y_col_list_bis : nom du (des) champ(s) Y de l'axe secondaire. Par défaut : []
    #       y_title_bis : titre de l'axe Y secondaire. Par défaut : ""
    #       y_legend_list_bis : légende(s) du (des) champ(s) Y de l'axe secondaire. Par défaut : []
    #       axhline : affiche une ligne horizontale sur le graphique. Par défaut : None
    #       axvline : affiche une ligne verticale sur le graphique. Par défaut : None
    #       fontsize : taille de police générale du graphique (fontsize*1.5 pour le titre, fontsize/1.5 pour les étiquettes). Par défaut : 20
    #   Retour : 0 si tout ok
    """
    if debug >= 3:
        print(cyan + "Variables dans la fonction :" + endC)
        print(cyan + "matplotlibGraphic() : " + endC + "input_csv_file : " + str(input_csv_file))
        print(cyan + "matplotlibGraphic() : " + endC + "output_png_file : " + str(output_png_file))
        print(cyan + "matplotlibGraphic() : " + endC + "graph_title : " + str(graph_title))
        print(cyan + "matplotlibGraphic() : " + endC + "x_col : " + str(x_col))
        print(cyan + "matplotlibGraphic() : " + endC + "x_title : " + str(x_title))
        print(cyan + "matplotlibGraphic() : " + endC + "y_col_list : " + str(y_col_list))
        print(cyan + "matplotlibGraphic() : " + endC + "y_title : " + str(y_title))
        print(cyan + "matplotlibGraphic() : " + endC + "y_legend_list : " + str(y_legend_list))
        print(cyan + "matplotlibGraphic() : " + endC + "encoding_file : " + str(encoding_file))
        print(cyan + "matplotlibGraphic() : " + endC + "separator_file : " + str(separator_file))
        print(cyan + "matplotlibGraphic() : " + endC + "label_col : " + str(label_col))
        print(cyan + "matplotlibGraphic() : " + endC + "y_col_list_bis : " + str(y_col_list_bis))
        print(cyan + "matplotlibGraphic() : " + endC + "y_title_bis : " + str(y_title_bis))
        print(cyan + "matplotlibGraphic() : " + endC + "y_legend_list_bis : " + str(y_legend_list_bis))
        print(cyan + "matplotlibGraphic() : " + endC + "axhline : " + str(axhline))
        print(cyan + "matplotlibGraphic() : " + endC + "axvline : " + str(axvline))
        print(cyan + "matplotlibGraphic() : " + endC + "fontsize : " + str(fontsize))
        print("\n")

    COLOURS_LIST = ['red','green','blue','cyan','magenta','yellow']
    fontsize_max = fontsize*1.5
    fontsize_min = fontsize/1.5

    if len(y_col_list) != len(y_legend_list):
        print(bold + red  + "matplotlibGraphic() : Error: y_col_list and y_legend_list parameters must have same lenght." + endC)
        return -1
    elif len(y_col_list) > 6:
        print(bold + red + "matplotlibGraphic() : Error: The maximun of Y data to display is 6." + endC)
        return -1
    elif len(y_col_list_bis) != len(y_legend_list_bis):
        print(bold + red  + "matplotlibGraphic() : Error: y_col_list_bis and y_legend_list_bis parameters must have same lenght." + endC)
        return -1
    elif len(y_col_list_bis) > 6:
        print(bold + red  + "matplotlibGraphic() : Error: The maximun of Y data to display to the secondary axis is 6." + endC)
        return -1

    # Création du DataFrame Pandas et tri croissant sur le champ X
    if debug >= 3:
        print(cyan + "matplotlibGraphic() : " + bold + green + "Création du DataFrame Pandas et tri croissant sur le champ X" + endC)

    data = pd.read_csv(input_csv_file, encoding=encoding_file, sep=separator_file)
    data_index = data.sort_values(by = [x_col])
    data_index.reset_index(drop = True, inplace = True)

    # Renommage des champs nécessaires au graphique (Pandas ne fonctionne qu'avec des noms en constante, et non en variable)
    if debug >= 3:
        print(cyan + "matplotlibGraphic() : " + bold + green + "Renommage des champs nécessaires au graphique" + endC)

    data_columns_list = data.columns
    y_col_new_list = []
    y_col_new_list_bis = []
    y_count = 0
    y_count_bis = 0
    for old_name_column in data_columns_list:
        new_name_column = old_name_column
        if old_name_column == x_col:
            new_name_column = "x_col"
        for y_col in y_col_list:
            if old_name_column == y_col:
                new_name_column = "y_col_%s" % y_count
                y_col_new_list.append(new_name_column)
                y_count += 1
        for y_col_bis in y_col_list_bis:
            if old_name_column == y_col_bis:
                new_name_column = "y_col_%s_bis" % y_count_bis
                y_col_new_list_bis.append(new_name_column)
                y_count_bis += 1
        if label_col != "":
            if old_name_column == label_col:
                new_name_column = "label_col"
        data.rename(columns={old_name_column:new_name_column}, inplace = True)

    # Mise en place des éléments principaux du graphique (fenêtre, grille, titre général, titres des axes...)
    if debug >= 3:
        print(cyan + "matplotlibGraphic() : " + bold + green + "Mise en place des éléments principaux du graphique" + endC)

    window = plt.figure(graph_title, figsize=(18, 9))
    figure = window.add_subplot(111)
    plt.grid(True)
    plt.title(graph_title, fontsize=fontsize_max)
    figure.set_xlabel(x_title, fontsize=fontsize)
    figure.set_ylabel(y_title, fontsize=fontsize)
    figure.tick_params(axis='x', labelsize=fontsize)
    figure.tick_params(axis='y', labelsize=fontsize)

    # Définition des nouvelles variables liées au champ X et au champ 'étiquettes'
    data_x = data.x_col
    if label_col != "":
        data_label = data.label_col

    # Définition des nouvelles variables liées au(x) champ(s) Y
    for data_y in y_col_new_list:
        data_y_list = []
        data_y_0 = data.y_col_0
        data_y_list.append(data_y_0)
        if len(y_col_new_list) >= 2:
            data_y_1 = data.y_col_1
            data_y_list.append(data_y_1)
            if len(y_col_new_list) >= 3:
                data_y_2 = data.y_col_2
                data_y_list.append(data_y_2)
                if len(y_col_new_list) >= 4:
                    data_y_3 = data.y_col_3
                    data_y_list.append(data_y_3)
                    if len(y_col_new_list) >= 5:
                        data_y_4 = data.y_col_4
                        data_y_list.append(data_y_4)
                        if len(y_col_new_list) >= 6:
                            data_y_5 = data.y_col_5
                            data_y_list.append(data_y_5)

    # Ajout de la (des) donnée(s) Y
    if debug >= 3:
        print(cyan + "matplotlibGraphic() : " + bold + green + "Ajout de la (des) donnée(s) Y" + endC)
    final_plot = []
    index = 0
    for data_y in data_y_list:
        colour = COLOURS_LIST[index]
        legend = y_legend_list[index]
        plot = figure.plot(data_x, data_y, "-", c=colour, linewidth=2, label=legend)
        figure.scatter(data_x, data_y, marker='+', c=colour)

        # Ajout des étiquettes associées à chaque point
        if label_col != "":
            plt.rcParams.update({'font.size': fontsize_min})
            for i, txt in enumerate(data_label):
                figure.annotate(txt, (data_x[i], data_y[i]))
            plt.rcParams.update({'font.size': fontsize})

        final_plot += plot
        index += 1

    # Dans le cas où on veut ajouter des données avec un axe des Y à droite
    if y_col_list_bis != [] and y_title_bis != "" and y_legend_list_bis != []:
        if debug >= 3:
            print(cyan + "matplotlibGraphic() : " + bold + green + "Ajout de donnée(s) sur un axe Y secondaire" + endC)
        # Mise à jour générale du graphique (ajout axe Y secondaire, ajout titre d'axe Y...)
        figure_bis = figure.twinx()
        figure_bis.set_ylabel(y_title_bis, fontsize=fontsize)
        figure_bis.tick_params(axis='y', labelsize=fontsize)

        # Définition des nouvelles variables liées au(x) champ(s) Y_bis
        for data_y_bis in y_col_new_list_bis:
            data_y_list_bis = []
            data_y_0_bis = data.y_col_0_bis
            data_y_list_bis.append(data_y_0_bis)
            if len(y_col_new_list_bis) >= 2:
                data_y_1_bis = data.y_col_1_bis
                data_y_list_bis.append(data_y_1_bis)
                if len(y_col_new_list_bis) >= 3:
                    data_y_2_bis = data.y_col_2_bis
                    data_y_list_bis.append(data_y_2_bis)
                    if len(y_col_new_list_bis) >= 4:
                        data_y_3_bis = data.y_col_3_bis
                        data_y_list_bis.append(data_y_3_bis)
                        if len(y_col_new_list_bis) >= 5:
                            data_y_4_bis = data.y_col_4_bis
                            data_y_list_bis.append(data_y_4_bis)
                            if len(y_col_new_list_bis) >= 6:
                                data_y_5_bis = data.y_col_5_bis
                                data_y_list_bis.append(data_y_5_bis)

        # Ajout de la (des) donnée(s) Y_bis
        index = 0
        for data_y_bis in data_y_list_bis:
            colour = COLOURS_LIST[index]
            legend = y_legend_list_bis[index]
            plot_bis = figure.plot(data_x, data_y_bis, "--", c=colour, linewidth=2, label=legend)
            figure.scatter(data_x, data_y_bis, marker='+', c=colour)

            # Ajout des étiquettes associées à chaque point
            if label_col != "":
                plt.rcParams.update({'font.size': fontsize_min})
                for i, txt in enumerate(data_label):
                    figure.annotate(txt, (data_x[i], data_y_bis[i]))
                plt.rcParams.update({'font.size': fontsize})

            final_plot += plot_bis
            index += 1

    # Ajout de la légende
    if debug >= 3:
        print(cyan + "matplotlibGraphic() : " + bold + green + "Ajout de la légende" + endC)
    label = [i.get_label() for i in final_plot]
    figure.legend(final_plot, label, loc=1, fontsize=fontsize)

    # Ajout d'une ligne horizontale au graphique
    if not axhline is None:
        if debug >= 3:
            print(cyan + "matplotlibGraphic() : " + bold + green + "Ajout d'une ligne horizontale au graphique" + endC)
        figure.axhline(axhline, linewidth=2, color='grey')

    # Ajout d'une ligne verticale au graphique
    if not axvline is None:
        if debug >= 3:
            print(cyan + "matplotlibGraphic() : " + bold + green + "Ajout d'une ligne verticale au graphique" + endC)
        figure.axvline(axvline, linewidth=2, color='grey')

    # Réajustement du graphique et sauvegarde du fichier
    if debug >= 3:
        print(cyan + "matplotlibGraphic() : " + bold + green + "Réajustement du graphique et sauvegarde du fichier" + endC)

    window.tight_layout()
    plt.savefig(output_png_file)

    return 0

##############################################################
# FONCTION progressBar()                                     #
##############################################################
def progressBar(current_value,max_value,text = "Progression: ",line_count = 1):
    """
    #   Rôle : Cette fonction met à jour l'affichage de l'avancement d'une barre de chargement, sur la même ligne
    #   Paramètres :
    #       current_value : valeur courante de la progression
    #       max_value : valeur maximale de la progression
    #       ext : texte affiché avant la barre de progression
    #       line_count : Indique la ligne ou sera affichée la barre de progression
    #          si  =0 : nouvelle ligne
    #          si  =1 : ligne courante
    #          si  >1 : lignes précédentes
    #   Retour : N.A.
    """

    # Calcul de la progression sur une echelle de 50 (dans le but d'afficher 50 étoiles dans la barre de progression)
    percentage = int(100*float(current_value)/max_value)
    perfiftyage = int(percentage/2)
    # Remonte à la line_count'ème ligne précédente du terminal et l'efface
    sys.stdout.write("%s" %("\033[A"*(line_count)) + "\r")
    # Ecrit la nouvelle barre de progression
    sys.stdout.write(text +" "+ str(percentage) + "%"+" [%s%s]" % ("*" * perfiftyage," " * (50-perfiftyage)))
    # Redescend à la ligne courante
    sys.stdout.write("%s" %("\033[B"*(line_count)))
    # Force la mise à jour de l'affichage
    sys.stdout.flush()

#####################################################################
# FONCTION plotResults()                                            #
#####################################################################
def plotResults(class_list,global_precision,precision_list):
    """
    #   Rôle : Cette fonction qui affiche un graphe en barre pour visualiser les résultats des calculs de la qualité de une ou plusieurs classifications (une barre par classification)
    #   Paramètres :
    #       class_list : Liste des classes présentes
    #       global_precision : Liste de la precision globale pour chaque classification différente
    #       precision_list : Liste où chaque élément est une liste du score de précision de chaque classe pour une classification
    #   Retour : Pas de retour boucle infinie sur l'affichage!
    """

    class_count = len(class_list)
    precision_listScale = []
    xaxis = []
    xaxis_stdev = []
    stdev_list = []
    #available_color_list = [[1,0,0],[0,1,0],[0,0,1],[1,0,1],[1,1,0],[0,1,1],[0.2,0.2,0.2],[1,0.5,0.5],[0.5,1,0.5],[0.5,0.5,1],[0,0.5,1],[1,0.5,0],[0.8,0.4,1],[0.5,1,0.2],[0.8,0.4,0.5]]
    available_color_list = [[1,1,0.5],[0.43,1,0],[0,0.67,1],[0.53,0.4,0.30],[0.83,0,0],[0,1,1],[0.2,0.2,0.2],[1,0.5,0.5],[0.5,1,0.5],[0.5,0.5,1],[0,0,1],[1,0.5,0],[0.8,0.4,1],[0,1,0],[0.8,0.4,0.5]]

    # Pour chaque classification
    for i in range(len(precision_list)):
        color_list = []
        color_count = 0
        percentage_offset_count = 0.0
        # Calcul de la moyenne des precision des classes
        precisions_sum = sum(precision_list[i])
        precisionMean = precisions_sum / class_count
        stdev = 0
        # Pour chaque classe
        for j in range(class_count):
            # Ajout d'une barre (toutes les barres d'une même classification se superposent)
            xaxis.append(i)
            # Calcul de l'écart au carré entre la précision de la classe et la moyenne de la précision
            stdev += (float(precision_list[i][j])-precisionMean)*(float(precision_list[i][j])-precisionMean)
            # Calcul de la taille de la barre (précision / somme des precision)
            barValue = (float(precision_list[i][j])*float(global_precision[i]))/float(precisions_sum)
            # Ajout à la liste des valeurs des barres, en rajoutant l'offset pour que la barre courante s'affiche au dessus des
            # barres précédentes
            precision_listScale.append(barValue + percentage_offset_count)
            # Ajout de la précision courante à l'offset pour la prochaine barre
            percentage_offset_count += barValue
            # Ajout d'une couleur pour la barre courante
            color_list.append(available_color_list[color_count])
            #color_list.append(cm.jet(1.*j/class_count))
            color_count += 1
            color_count %= len(available_color_list)
        # Calcul de l'écart type et ajout à la liste des écart types
        stdev /= class_count
        stdev = sqrt(stdev)
        stdev_list.append(stdev)
        # Décalage de 0.4 pour qu'il soit affiché au milieu de la barre correspondante
        xaxis_stdev.append(i+0.4)
    # Tri sur les barres de précision pour que l'affichage soit lisible
    precision_list_scale_reordered = []
    for i in range(len(precision_list)):
        for j in range(class_count):
            precision_list_scale_reordered.append(precision_listScale[i*class_count+(class_count-1-j)])
    # Création du graphique
    bar_plot = bar(xaxis,precision_list_scale_reordered,color = color_list,zorder=1)
    # Création de la légende
    class_list_reversed = class_list[::-1]
    legend(bar_plot, class_list_reversed)
    # Création des écarts types
    scatter_plot = scatter(xaxis_stdev,stdev_list,marker='*',s=500,color="black",edgecolors="red",zorder=2)
    # Affichage
    show()

#############################################################################################################
# FONCTION D'AFFICHAGE D'UN GRAPHIQUE DE QUALITE DE CLASSIFICATIONS : QUALITE GLOBALE ET QUALITE PAR CLASSE #
#############################################################################################################
def plotResultsMulti(class_list,global_precision,precision_list):
    """
    #   Rôle : Cette fonction d'affichage d'un graphique de qualite de classifications : qualite globale et qualite par classe.
    #   Paramètres :
    #       class_list : Liste des classes présentes
    #       global_precision : Liste de la precision globale pour chaque classification différente
    #       precision_list : Liste où chaque élément est une liste du score de précision de chaque classe pour une classification
    #   Retour : Pas de retour boucle infinie sur l'affichage!
    #
    #   Exemples :
    #       plotResultsMulti([1,2,3,4,5,6,7,8,9,10,11,12,13,14,15],[60,80,95,50,50,50,50,50,50,50,50,50,50,50,50],[[30,20,40,20,20,30,50,10,30,20,30,50,10,30,20]])
    #       plotResultsMulti(["Urbain","Sols nus","Eau","Vegetation ligneuse","Herbaces"],[60,90,80],[[30,60,96,50,65],[95,75,98,93,90],[65,80,95,90,45]])
    """

    class_count = len(class_list)
    precision_listScale = []
    xaxis = []
    xaxis_stdev = []
    stdev_list = []
    available_color_list = [[1,1,0.5],[0.43,1,0],[0,0.67,1],[0.53,0.4,0.30],[0.83,0,0],[0,1,1],[0.2,0.2,0.2],[1,0.5,0.5],[0.5,1,0.5],[0.5,0.5,1],[0,0,1],[1,0.5,0],[0.8,0.4,1],[0,1,0],[0.8,0.4,0.5]]

    # Pour chaque classification
    for i in range(len(precision_list)):
        color_list = []
        color_count = 0
        percentage_offset_count = 0.0
        # Calcul de la moyenne des precision des classes
        precisions_sum = sum(precision_list[i])
        precisionMean = precisions_sum / class_count
        stdev = 0
        xaxis.append(i*(class_count+2))
        precision_listScale.append(global_precision[i])
        color_list.append([0,0,0])

        # Pour chaque classe
        for j in range(class_count):
            # Ajout d'une barre avec les décalages qui vont bien
            xaxis.append(i*(class_count+2)+j+1)
            # Calcul de l'écart au carré entre la précision de la classe et la moyenne de la précision
            stdev += (float(precision_list[i][j])-precisionMean)*(float(precision_list[i][j])-precisionMean)
            # Calcul de la taille de la barre (précision / somme des precision)
            barValue = float(precision_list[i][j])
            # Ajout à la liste des valeurs des barres
            precision_listScale.append(barValue)
            # Ajout d'une couleur pour la barre courante
            color_list.append(available_color_list[color_count])
            #color_list.append(cm.jet(1.*j/class_count))
            color_count += 1
            color_count %= len(available_color_list)

        # Calcul de l'écart type et ajout à la liste des écart types
        stdev /= class_count
        stdev = sqrt(stdev)
        stdev_list.append(stdev)
        # Décalage de l'écart type pour qu'il soit affiché au milieu des barres de la classification correspondante
        xaxis_stdev.append(i*(class_count+2)+0.9+class_count/2)

    # Triage des barres de précision pour que l'affichage soit lisible
    precision_list_scale_reordered = []
    for i in range(len(precision_list)):
        precision_list_scale_reordered.append(precision_listScale[i*(class_count+1)])

        for j in range(class_count):
            precision_list_scale_reordered.append(precision_listScale[i*(class_count+1)+(class_count-j)])

    # Création du graphique
    bar_plot = bar(xaxis,precision_list_scale_reordered,color = color_list,zorder=1)
    # Création de la légende
    class_list_reversed = ["Global"] + class_list[::-1]
    legend(bar_plot, class_list_reversed)
    # Création des écarts types
    scatter(xaxis_stdev,stdev_list,marker='h',s=500,color="black",edgecolors="red",zorder=2)
    # Affichage
    show()

#########################################################################
# FONCTION displayImage()                                               #
#########################################################################
def displayImage(process, imageFile, commentImage, debug):
    """
    #   Rôle : Cette fonction permet d'afficher dans une fenetre indepandante une image
    #   Paramètres :
    #       imageFile : le chemin complet du fichier contenant l'image
    #       commentImage : le commantaire de titre de la fenetre
    #       debug : niveau de debug
    #   Retour : N.A.
    """

    process, root = displayImage1(process, imageFile, commentImage, debug)
    #process, root = displayImage2(process, imageFile, commentImage, debug)

    return process, root

#########################################################################
# FONCTION endDisplayImage()                                            #
#########################################################################
def endDisplayImage(process, root):
    """
    #   Rôle : Cette fonction permet d'arreter afficher d'une fenetre indepandante une image
    #   Paramètres :
    #       process : le process ou le thread a arreter
    #       root : ihm de la fenetre d'affichage
    #   Retour : N.A.
    """

    if root == None : # si c'est un process => cas displayImage2
        try :
            killTreeProcess(process.pid + 1)
            process.terminate()
        except :
            time.sleep(1)
            terminateThread(process)
            return

    else: # si c'est un thread => cas displayImage1
        try :
            root.quit()
            #root.destroy()
            time.sleep(1)
        except :
            sys.exit()
            #pid = os.getpid()
            #killTreeProcess(pid)
        terminateThread(process)

    return

#########################################################################
# FONCTION displayImage1()                                              #
#########################################################################
def displayImage1(process, imageFile, commentImage, debug):
    """
    #   Rôle : Cette fonction permet d'afficher une image
    #   Paramètres :
    #       process : le process ou le thread utilisé (retour)
    #       imageFile : le chemin complet du fichier contenant l'image
    #       commentImage : le commantaire de titre de la fenetre
    #       debug : niveau de debug
    #
    #   Retour : N.A.
    """

    global root

    if process == None :
        process = threading.Thread(target=displayImageRoot, args=(imageFile, commentImage, debug))
        process.start()
    else :
       if debug >= 4:
           print(cyan + "displayImage1() : " + endC + "img : " + imageFile + endC)
       displayImageUpdate(imageFile, commentImage, debug)

    return process, root

#########################################################################
# FONCTION displayImage2()                                              #
#########################################################################
def displayImage2(process, imageFile, commentImage, debug):
    """
    #   Rôle : Cette fonction permet d'afficher une image
    #   Paramètres :
    #       process : le process ou le thread utilisé (retour)
    #       imageFile : le chemin complet du fichier contenant l'image
    #       commentImage : le commantaire de titre de la fenetre
    #       debug : niveau de debug
    #
    #   Retour : N.A.
    """

    if process == None :
        command = "eog %s" %(imageFile)
        if debug >= 4:
           print(cyan + "displayImage2() : " + endC + "img : " + imageFile + endC)
        process = subprocess.Popen([command], shell=True)

    return process, None

#########################################################################
# FONCTION displayImageRoot()                                           #
#########################################################################
root = None
mainframe = None
img_widget = None
def displayImageRoot(imageFile, commentImage, debug):
    """
    #   Rôle : Cette fonction permet d'afficher dans une fenetre indepandante une image premier lancement
    #   Paramètres :
    #       imageFile : le chemin complet du fichier contenant l'image
    #       commentImage : le commantaire de titre de la fenetre
    #       debug : niveau de debug
    #   Retour : pas de retour la fonction reste en boucle sur l'affichage!!!
    """

    global root
    global mainframe
    global img_widget

    # Initialisation de la fenetre
    root = Tk()
    root.title(commentImage)
    root.configure(background='#000000')
    mainframe = Frame(root)
    mainframe.pack(fill=BOTH, expand=True, padx=15, pady=15)

    # Chargement de l'image
    image = PIL.Image.open(imageFile)

    # Marge par rapport aux bords de l'écran
    gap = 100
    screen_width = root.winfo_screenwidth() - gap
    screen_height = root.winfo_screenheight() - gap

    # Dimensions de l'écran
    if image.width > screen_width :
        image = image.resize((screen_width, int(image.height * screen_width / image.width)), PIL.Image.LANCZOS)
    if image.height > screen_height :
        image = image.resize((int(image.width * screen_height / image.height), screen_height), PIL.Image.LANCZOS)

    # Affiche de l'image
    photo = PIL.ImageTk.PhotoImage(image)
    image.close()
    img_widget = Label(mainframe, image=photo)
    img_widget.pack()
    root.mainloop()

#########################################################################
# FONCTION displayImageUpdate()                                         #
#########################################################################
def displayImageUpdate(imageFile, commentImage, debug):
    """
    #   Rôle : Cette fonction permet de mettre a jour l'affichage d'une image dans la fenetre
    #   Paramètres :
    #       imageFile : le chemin complet du fichier contenant l'image
    #       commentImage : le commantaire de titre de la fenetre
    #       debug : niveau de debug
    #   Retour : N.A.
    """

    global root
    global mainframe
    global img_widget

    try :
        # Chargement de l'image
        image = PIL.Image.open(imageFile)

        # Marge par rapport aux bords de l'écran
        gap = 100
        screen_width = root.winfo_screenwidth() - gap
        screen_height = root.winfo_screenheight() - gap

        # Dimensions de l'écran
        if image.width > screen_width :
            image = image.resize((screen_width, int(image.height * screen_width / image.width)), PIL.Image.LANCZOS)
        if image.height > screen_height :
            image = image.resize((int(image.width * screen_height / image.height), screen_height), PIL.Image.LANCZOS)

        # Affiche de l'image
        photo = PIL.ImageTk.PhotoImage(image)
        image.close()

        img_widget.configure(image=photo)
        img_widget.image = photo
    except :
        return

    return

#########################################################################
# FONCTION displayIHM()                                                 #
#########################################################################
def displayIHM(gui, parser):
    """
    #   Rôle : Cette fonction permet d'appeler les applications version IHM plutôt qu'en ligne de commande
    #   Paramètres :
    #       gui : boolen active ou desactive la version IHM (activé = True)
    #       parser : le parseur argpase
    #   Retour : args (les arguments)
    """

    args = None
    if gui and six.PY2 :
        app = QtGui.QApplication(sys.argv)
        a = argparseui.ArgparseUi(parser, window_title=parser.prog, use_save_load_button=True)
        a.show()
        app.exec_()
        if a.result() == 1: # Ok pressed
            args = a.parse_args() # ask argparse to parse the options
        else:
            sys.exit(0) # Cancel exit app
    else :
        args = parser.parse_args()
    return args
