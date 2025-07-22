#!/usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# CE SCRIPT PERMET D'AFFICHER LES GRAPHES LES LCZ A PARTIR DU GRAPHE PHTHON                                                                 #
#                                                                                                                                           #
#############################################################################################################################################

"""
Nom de l'objet : DisplayTreeLCZ.py
Description :
-------------
Objectif : Tester et afficher graphiquement l'arbre LCZ

Date de creation : 29/04/2019

"""

from __future__ import print_function
import os, sys, shutil, argparse
import warnings
import pygraphviz as pgv
from Lib_display import displayIHM, bold, red, green, yellow, blue, magenta, cyan, endC,displayIHM
from Lib_log import timeLine
from Lib_file import removeFile


debug = 3

####################################################################################################
# FONCTION displayTree()                                                                           #
####################################################################################################
def displayTree(origin_tree, origin_name, name_file_graph, path_time_log, save_results_intermediate, overwrite):
    """
    # ROLE:
    #     Affiche de facon graphique l'arbre LCZ
    #
    # ENTREES DE LA FONCTION :
    #     origin_tree : l'arbre de décision à tracer
    #     origin_name : le nom du premier noeud
    #     name_file_graph : le nom et chemin du fichier resutat du graphe
    #     path_time_log : le fichier de log de sortie
    #     save_results_intermediate : fichiers de sorties intermediaires nettoyees, par defaut = False
    #     overwrite : écrase si un fichier existant a le même nom qu'un fichier de sortie, par defaut a True
    #
    # SORTIES DE LA FONCTION :
    #      le fichier graphe
    """

    # Constantes
    EXT_DOT = ".dot"
    EXT_PNG = ".png"
    GRAPH_NAME = "graph_LCZ"

    # Mise à jour du Log
    starting_event = "displayTree() : Graph creation starting : "
    timeLine(path_time_log,starting_event)

    label_graph = os.path.splitext(os.path.basename(name_file_graph))[0]
    path_file = os.path.dirname(name_file_graph)

    dot_file = path_file +  os.sep + label_graph + EXT_DOT
    if os.path.isfile(dot_file) :
        removeFile(dot_file)
    png_file = path_file +  os.sep + label_graph + EXT_PNG

    # VERIFICATION SI LE MASQUE DE SORTIE EXISTE DEJA
    # Si un fichier de sortie avec le même nom existe déjà, et si l'option ecrasement est à false, alors passe au masque suivant
    check = os.path.isfile(png_file)
    if check and not overwrite:
        print(bold + yellow +  "displayTree() : " + endC + "Output png file %s already done : no actualisation" % (png_file) + endC)
        return
    # Si non, ou si la fonction ecrasement est désative, alors on le calcule
    else:
        if check:
            try: # Suppression de l'éventuel fichier existant
                removeFile(png_file)
            except Exception:
                pass # Si le fichier ne peut pas être supprimé, on suppose qu'il n'existe pas et on passe à la suite

    # Definie les parametres du graphe
    graph = pgv.AGraph(name=GRAPH_NAME, directed=True)

    graph.graph_attr['outputorder']='edgesfirst'
    graph.graph_attr['label']= label_graph
    #graph.graph_attr['ratio']='1.0'
    graph.graph_attr['ratio']='compress'
    graph.graph_attr['rankdir']='TB'
    graph.node_attr['shape']='ellipse'
    graph.node_attr['fixedsize']='false'
    graph.node_attr['fontsize']='8'
    graph.node_attr['style']='filled'

    graph.edge_attr['color']='lightslategray'
    graph.edge_attr['style']='etlinewidth(2)'
    graph.edge_attr['arrowhead']='open'
    graph.edge_attr.update(arrowhead='vee', arrowsize='2')

    # Definir la couleur selon le noeud ou feuille
    value_color = 'gray52'

    # Creation du 1er noeud
    id_node = 0
    graph.add_node(id_node)
    node = graph.get_node(id_node)

    # Assign node color
    node.attr['fillcolor'] = value_color

    # Empty labels
    node.attr['label'] = origin_name + '\n'

    # Start parcours de l'arbre
    graph = createDisplayGraph(origin_tree, id_node, graph, debug)

    # Ecriture dans le fichier
    graph_reverse = graph.reverse()
    graph_reverse.write(dot_file)

    # Ignore Graphviz warning messages
    warnings.simplefilter('ignore', RuntimeWarning)
    graph = pgv.AGraph(name=GRAPH_NAME)

    # Convert file .dot
    graph.read(dot_file)
    graph.layout(prog='dot') # layout with default (neato)
    png_draw = graph.draw(png_file, format='png', prog='dot' )

    # Suppression des données intermédiaires
    if not save_results_intermediate:
        #removeFile(dot_file)
        pass

    # Mise à jour du Log
    ending_event = "displayTree() : Graph creation ending : "
    timeLine(path_time_log,ending_event)

    return

####################################################################################################
# FONCTION createDisplayGraph()                                                                    #
####################################################################################################
def createDisplayGraph(tree, id_node_parent, graph, debug):
    """
    # ROLE:
    #     Creer une version graphiquement l'arbre de décision LCZ
    #
    # ENTREES DE LA FONCTION :
    #     tree : l'arbre de décision
    #     graph : graph pygraphviz à construire
    #     debug : niveau de trace log
    #
    # SORTIES DE LA FONCTION :
    #      le fichier graphe créé
    """

    for i in range(len(tree)):
        item = tree[i]
        if isinstance(item,dict):
            if debug >= 4 :
                print("DICO : " + str(id_node_parent) + " " + str(item))
            key = list(item.keys())[0]
            values = list(item.values())[0]
            value_color = 'deepskyblue1'
            end_value = ""
            if debug >= 4 :
                print("key = " +  str(key))
                print("value1 = " + str(values[0]))
                print("value2 = " + str(values[1]))
            if not isinstance(values[2],list) :
                if debug >= 4 :
                    print("value3 = " + str(values[2]))
                value_color = 'chartreuse'
                end_value = str(values[2])
            id_node = (id_node_parent * 10) + (i + 1)
            graph.add_node(id_node)
            node = graph.get_node(id_node)
            node.attr['fillcolor'] = value_color
            node.attr['label'] = key + '\n' + str(values[0]) + " < val <= " + str(values[1]) + '\n' + end_value
            graph.add_edge(id_node, id_node_parent)

            graph = createDisplayGraph(item[key], id_node, graph, debug)
        elif isinstance(item,list):
            if debug >= 4 :
                print("LIST : " + str(item))
            graph = createDisplayGraph(item, id_node_parent, graph, debug)
        else:
            if debug >= 4 :
                print("END : " + str(item))
            pass

    return graph

###########################################################################################################################################
# MISE EN PLACE DU PARSER                                                                                                                 #
###########################################################################################################################################

# Code executé seulement dans le cas ou le script est lancé depuis une ligne de commande
# Il n'est pas executé lors d'un import DisplayTreeLCZ.py
# Exemple de lancement en ligne de commande:
# python DisplayTreeLCZ.py -i /mnt/Data/10_Agents_travaux_en_cours/Romain/Gilles_graphique/Classification_LCZ_settings_v9_2.py -o /mnt/Data/10_Agents_travaux_en_cours/Romain/Gilles_graphique/Classification_LCZ_settings_v9_2.png -n tree_A -log ./fichierTestLog.txt

def main(gui=False):

    # Définition des différents paramètres du parser
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,  prog="DisplayTreeLCZ", description="\
    Info : Transform a tree LCZ to a graph. \n\
    Objectif : Creer un graphe de l'arbre LCZ. \n\
    Example : python DisplayTreeLCZ.py -i /mnt/Data/10_Agents_travaux_en_cours/Romain/Gilles_graphique/Classification_LCZ_settings_v9_2.py \n\
                                     -o /mnt/Data/10_Agents_travaux_en_cours/Romain/Gilles_graphique/Classification_LCZ_settings_v9_2.png \n\
                                     -n tree_A \n\
                                     -log ./fichierTestLog.txt")

    parser.add_argument('-i','--file_tree_input',default="",help="File tree py input.", type=str, required=True)
    parser.add_argument('-o','--file_graph_output',default="",help="File graphe png output.", type=str, required=True)
    parser.add_argument('-n','--origin_name',default="",help="Name first node of graph.", type=str, required=True)
    parser.add_argument('-log','--path_time_log',default="",help="Name of log", type=str, required=False)
    parser.add_argument('-sav','--save_results_inter',action='store_true',default=False,help="Save or delete intermediate result after the process. By default, False", required=False)
    parser.add_argument('-now','--overwrite',action='store_false',default=True,help="Overwrite files with same names. By default, True", required=False)
    parser.add_argument('-debug','--debug',default=3,help="Option : Value of level debug trace, default : 3 ",type=int, required=False)
    args = displayIHM(gui, parser)

    # RECUPERATION DES ARGUMENTS

    # Récupération du fichier arbre d'entée
    if args.file_tree_input!= None:
        file_tree_input=args.file_tree_input

    # Récupération du fichier graphe de sortie
    if args.file_graph_output!= None:
        file_graph_output=args.file_graph_output

    # Récupération du nom du premier noeud du graphe
    if args.origin_name!= None:
        origin_name=args.origin_name

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
        print(bold + green + "DisplayTreeLCZ : Variables dans le parser" + endC)
        print(cyan + "DisplayTreeLCZ : " + endC + "file_tree_input : " + str(file_tree_input) + endC)
        print(cyan + "DisplayTreeLCZ : " + endC + "file_graph_output : " + str(file_graph_output) + endC)
        print(cyan + "DisplayTreeLCZ : " + endC + "origin_name : " + str(origin_name) + endC)
        print(cyan + "DisplayTreeLCZ : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "DisplayTreeLCZ : " + endC + "save_results_inter : " + str(save_results_intermediate) + endC)
        print(cyan + "DisplayTreeLCZ : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "DisplayTreeLCZ : " + endC + "debug : " + str(debug) + endC)

    # EXECUTION DE LA FONCTION
    # Si les dossiers de sortie n'existent pas, on les crées
    repertory_output = os.path.dirname(file_graph_output)
    if not os.path.isdir(repertory_output):
        os.makedirs(repertory_output)

    # Importer le fichier python contenant l'arbre
    path_import_file = os.path.dirname(file_tree_input)
    import_file = os.path.splitext(os.path.basename(file_tree_input))[0]
    sys.path.append(path_import_file)
    new_inport_tree = __import__(import_file)
    # Récuperer le contenu de la variable arbre
    origin_tree = getattr(new_inport_tree, origin_name)
    #origin_tree = globals()[origin_name]

    # Execution de la fonction pour un arbre
    displayTree(origin_tree, origin_name, file_graph_output, path_time_log, save_results_intermediate, overwrite)

# ================================================

if __name__ == '__main__':
  main(gui=False)
