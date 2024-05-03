# -*- coding: utf-8 -*-
#!/usr/bin/python

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# FONCTIONS QUI AFFICHE L'ETATS DES COMMANDES A PARTIR DU FICHIER DE COMMANDES                                                              #
#                                                                                                                                           #
#############################################################################################################################################
"""
 Ce module contient les fonctions qui affichent l'état des commandes a partir du fichier de commandes pour séquenceur.
"""

# IMPORTS UTILES
import os, sys, time, threading, subprocess
import six
from datetime import datetime
import warnings
import pygraphviz as pgv

from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC, displayImage, endDisplayImage
from Lib_text import writeTextFile,appendTextFileCR, cleanSpaceText
from Lib_file import removeFile
from Lib_operator import switch, case
from Settings import *

#############################################################################################
# FONCTION readCommands()                                                                   #
#############################################################################################
def readCommands(command_doc, debug):
    """
    # ROLE :
    #   La fonction lit des commandes dans un fichier texte et convertie en dico
    #
    # ENTREES :
    #   command_doc : fichier dont on lit et execute les commandes
    #   debug : niveau de trace log
    #
    # SORTIES :
    #   structure contenant les commandes et leur état
    """

    struct_cmd_dico = {}
    try:
        # Ouverture du fichier de commande et chargement de toutes les lignes
        command_doc_work = open(command_doc,'r')
        commands_list = command_doc_work.readlines()
    except:
        return None
        #raise NameError(cyan + "readCommands : " + endC + bold + red + "Can't open file: \"" + command_doc + '\n' + endC)

    # Identification de commands_list comme une liste dont chaque ligne correspond à une commande
    for command in commands_list :

        element_command_list = command.split(SEPARATOR)
        if len(element_command_list) < 11 :
            return None

        state = element_command_list[0]
        name_task = element_command_list[3]
        action = element_command_list[4]
        id_command = element_command_list[1]

        # Liste des commandes dependantes
        dependency_list = []
        if element_command_list[2] != '':
            dependency_list = element_command_list[2].split(',')

        # Récupération de la commande à exécuter
        command_to_execute = element_command_list[11]
        if six.PY2:
            if FUNCTION_PYTHON in command_to_execute:
                command_to_execute =  command_to_execute.replace(FUNCTION_PYTHON,'')
        else :
            if FUNCTION_PYTHON3 in command_to_execute:
                command_to_execute =  command_to_execute.replace(FUNCTION_PYTHON3,'')
        name_cmd = command_to_execute.split(' ')[0]

        # Récupération de l'heure de début et de fin
        start_date = element_command_list[9]
        end_date = element_command_list[10]


        # Creation d'une structure contenant les données des commandes
        struct_cmd_dico[id_command] = []
        struct_cmd_dico[id_command].append(state)
        struct_cmd_dico[id_command].append(dependency_list)
        struct_cmd_dico[id_command].append(name_cmd)
        struct_cmd_dico[id_command].append(start_date)
        struct_cmd_dico[id_command].append(end_date)
        struct_cmd_dico[id_command].append(name_task)

    return struct_cmd_dico

#############################################################################################
# FONCTION convert2dot()                                                                    #
#############################################################################################
def convert2dot(command_doc, struct_cmd_dico, graph_name, dot_file, debug):
    """
    # ROLE :
    #   La fonction convertie les infos des commandes en un fichier .dot
    #
    # ENTREES :
    #   command_doc : nom du fichier commande
    #   struct_cmd_dico : structure contenant les infos des commandes
    #   graph_name : le nom du graphe
    #   dot_file : le fichier .dot resultat en sortie
    #   debug : niveau de trace log
    #
    # SORTIES :
    #   N.A.
    """

    EXT_ERR = '.err'

    # Definie les parametrres du graph
    graph = pgv.AGraph(name=graph_name, directed=True)

    graph.graph_attr['outputorder']='edgesfirst'
    graph.graph_attr['label']=command_doc
    #graph.graph_attr['ratio']='1.0'
    graph.graph_attr['ratio']='compress'
    graph.graph_attr['rankdir']='TB'

    graph.node_attr['shape']='ellipse'
    graph.node_attr['fixedsize']='false'
    graph.node_attr['fontsize']='8'
    graph.node_attr['style']='filled'

    graph.edge_attr['color']='lightslategray'
    graph.edge_attr['style']='setlinewidth(2)'
    graph.edge_attr['arrowhead']='open'
    graph.edge_attr.update(arrowhead='vee', arrowsize='2')

    # Parcours du dictionaire de facon ordonnée
    id_command_list = struct_cmd_dico.keys()
    id_command_sorted_list = sorted(id_command_list)

    # Pour toutes les lignes du fichier commande
    for id_cmd in id_command_sorted_list:

        # Recuperer les valeurs des coordonnees
        info_cmd_list = struct_cmd_dico[id_cmd]
        state = info_cmd_list[0]
        dependency_list = info_cmd_list[1]
        name_cmd = info_cmd_list[2]
        start_date = info_cmd_list[3]
        end_date = info_cmd_list[4]
        name_task_list = info_cmd_list[5].split('.')
        name_task = name_task_list[1] + '.' + name_task_list[2]

        # Creation du graph
        if debug >=4 :
            print(cyan + "convert2dot() : " + endC + "Id Cmd = " + str(id_cmd) + ", state : " + state)

        graph.add_node(id_cmd)
        node = graph.get_node(id_cmd)

        # Dependances
        for dependency in dependency_list :
            graph.add_edge(id_cmd,dependency)

        # Definir la couleur selon l'etat de la commande
        value_color = 'white'
        info = ""
        while switch(state):

            if case(TAG_STATE_MAKE):
                # Etat A_Faire
                value_color = 'lightgray'
                break

            if case(TAG_STATE_WAIT):
                # Etat En_Attente
                value_color = 'gray52'
                break

            if case(TAG_STATE_LOCK):
                # Etat Bloqué
                value_color = 'darkorange'
                break

            if case(TAG_STATE_RUN):
                # Etat En_Cours
                value_color = 'deepskyblue1'
                info = "\n" + start_date
                break

            if case(TAG_STATE_END):
                # Etat Termine
                value_color = 'chartreuse'
                start_date_time = datetime.strptime(start_date,'%d/%m/%y %H:%M:%S')
                end_date_time = datetime.strptime(end_date,'%d/%m/%y %H:%M:%S')
                during_time = end_date_time - start_date_time
                info = "\n" + str(during_time)
                break

            if case(TAG_STATE_ERROR):
                # Etat En_Erreur"
                value_color = 'deeppink'

                # Definir la boite du fichier d'erreur
                error_file_name = os.path.splitext(os.path.basename(command_doc))[0] + str(id_cmd) + EXT_ERR
                id_err = str(int(id_cmd) + 10000)
                graph.add_node(id_err)
                graph.graph_attr['label']=''
                graph.edge_attr['label']=''
                node_err = graph.get_node(id_err)
                graph.add_edge(id_err,id_cmd)
                edge_err = graph.get_edge(id_err,id_cmd)
                node_err.attr['shape']='rectangle'
                node_err.attr['fillcolor']='red' #'lightpink'
                node_err.attr['label']=error_file_name
                edge_err.attr['label']="See error file!"
                edge_err.attr['color']='black'
                edge_err.attr['fontcolor']='red'
                edge_err.attr['style']='dotted'
                edge_err.attr['arrowhead']='open'
                break

            break # Sortie du while

        # Assign node color
        node.attr['fillcolor'] = value_color

        # Empty labels
        node.attr['label'] = name_task + " - " + name_cmd + info + '\n' + str(id_cmd)

    # Ecriture dans le fichier
    graph_reverse = graph.reverse()
    graph_reverse.write(dot_file)

    return

#############################################################################################
# FONCTION displayCommands()                                                                #
#############################################################################################
def displayCommands(command_doc, debug):
    """
    # ROLE :
    #   La fonction affiche les commandes sous forme de graph de type workflow
    #
    # ENTREES :
    #   command_doc : le fichier des commandes
    #   debug : niveau de trace log
    #
    # SORTIES :
    #   N.A.
    """

    # Constantes
    EXT_DOT = ".dot"
    EXT_PNG = ".png"
    GRAPH_NAME = "workflows_commandes"
    process = None

    while not getEndDisplay() :
        # Define dot file
        dot_file = os.path.splitext(command_doc)[0] + EXT_DOT
        if os.path.isfile(dot_file) :
            removeFile(dot_file)
        png_file = os.path.splitext(command_doc)[0] + EXT_PNG


        # Processing file .dot
        struct_cmd_dico = readCommands(command_doc, debug)

        if struct_cmd_dico is not None and struct_cmd_dico != {} :
            convert2dot(command_doc, struct_cmd_dico, GRAPH_NAME, dot_file, debug)
            # Ignore Graphviz warning messages
            warnings.simplefilter('ignore', RuntimeWarning)
            graph = pgv.AGraph(name=GRAPH_NAME)
            # Convert file .dot
            graph.read(dot_file)
            graph.layout(prog='dot') # layout with default (neato)
            png_draw = graph.draw(png_file, format='png', prog='dot' )
            # Affichage image PNG
            process, root = displayImage(process, png_file, GRAPH_NAME, debug)

        # Attente avant boucle
        time.sleep(1)

    # Fin arret de l'affichage de l'image
    endDisplayImage(process, root)

    return

#############################################################################################
# FONCTION supervisionCommands()                                                            #
#############################################################################################
def supervisionCommands(command_doc, debug):
    """
    # ROLE :
    #   La fonction affiche les commandes en boucle
    #
    # ENTREES :
    #   command_doc : le fichier des commandes
    #   debug : niveau de trace log
    #
    # SORTIES :
    #   N.A.
    """

    # Display image en thread indepandant => displayCommands(command_doc, debug)
    thread = threading.Thread(target=displayCommands, args=(command_doc, debug))

    return thread
