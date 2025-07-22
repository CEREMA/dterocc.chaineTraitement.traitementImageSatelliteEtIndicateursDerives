#! /usr/bin/python
# -*- coding: utf-8 -*-

#############################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.               #
#############################################################################

#############################################################################
#                                                                           #
# FONCTIONS DE BASE PARSE DE XML (fichier .xml)                             #
#                                                                           #
#############################################################################
"""
  Ce module contient un certain nombre de fonctions de bases pour réaliser des récupération d'informations dans un fichier de format XML,
  quelques fonctions basés sut la lib lxml, mais majoritairement les fonctions de cette librairie sont basées sur dom.
"""

# IMPORTS DIVERS
import sys,os
import six
from lxml import etree
from xml.dom import minidom
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 3 : affichage maximum de commentaires lors de l'execution du script. Intermédiaire : affichage intermédiaire
debug = 3

#########################################################################
# FONCTION parseLxml()                                                  #
#########################################################################
def parseLxml(xml_file):
    """
    # Role : Fonction qui retourne le contenu d'un fichier xml (parser méthode lxml)
    #   Paramètres en entrée :
    #       xml_file : nom du fichier xml d'entrée
    #   Paramétre de retour :
    #        tree : le contenu du fichier xml
    """

    # Lecture du fichier xml
    tree = None
    try:
        tree = etree.parse(xml_file)
    except Exception:
        if not os.sep in xml_file:
            xml_file =  os.getcwd() + os.sep + xml_file
        raise NameError (cyan + "parseLxml() : " + bold + red  + "Erreur lors du parse (en lxml) du fichier : " + xml_file + " => " + str(sys.exc_info()[1]) + endC)
    return tree

#########################################################################
# FONCTION getValueNodeDataLxml()                                       #
#########################################################################
def getValueNodeDataLxml(tree, path_element):
    """
    #   Role : Fonction qui retourne le valeur d'un noeud
    #   Paramètres en entrée :
    #       tree : le contenu xml au format lxml
    #       path_element : le chemin + nom du noeud recherché
    #   Paramétre de retour :
    #        la valeur
    """
    element_list = tree.xpath(path_element)
    value = str(element_list[0].text)
    return value

#########################################################################
# FONCTION getValueAttributeLxml()                                      #
#########################################################################
def getValueAttributeLxml(tree, path_element, attribute_name):
    """
    #   Role : Fonction qui retourne le valeur d'un attibut d'un noeud
    #   Paramètres en entrée :
    #       tree : le contenu xml au format lxml
    #       path_element : le chemin + nom du noeud recherché
    #       attribute_name : le nom de l'attribut rechercher pour le noeud
    #   Paramétre de retour :
    #        la valeur
    """

    element_list = tree.xpath(path_element)
    value = str(element_list[0].get(attribute_name))
    return value

#########################################################################
# FONCTION parseDom()                                                   #
#########################################################################
def parseDom(xml_file):
    """
    #   Role : Fonction qui retourne le contenu d'un fichier xml (parser méthode dom)
    #   Paramètres en entrée :
    #       xml_file : nom du fichier xml d'entrée
    #   Paramétre de retour :
    #        xmldoc : le contenu du fichier xml
    """

    # Lecture du fichier xml
    xmldoc = None
    try:
        xmldoc = minidom.parse(xml_file)
    except Exception:
        if not os.sep in xml_file:
            xml_file =  os.getcwd() + os.sep + xml_file
        raise NameError (cyan + "parseDom() : " + bold + red  + "Erreur lors du parse (en dom) du fichier : " + xml_file + " => " + str(sys.exc_info()[1]) + endC)
    return xmldoc

#########################################################################
# FONCTION findElement()                                                #
#########################################################################
def findElement(xmldoc, element_name, element_path=''):
    """
    #   Role : Fonction qui retourne élement d'un noeud
    #   Paramètres en entrée :
    #       xmldoc : le contenu xml au format dom
    #       element_name : le nom du noeud recherché
    #       element_path : le chemin du noeud recherché (complet ou partiel), par défaut vide
    #   Paramétre de retour :
    #        l'élement
    """

    find_element = None

    if xmldoc is not None:

        if element_path == '' :
            element_list = xmldoc.getElementsByTagName(element_name)
            if element_list != [] :
                find_element = element_list[0]
        else:
            elem_str_list = element_path.split('/')
            if '' in elem_str_list:
                elem_str_list.remove('')
            element_list = xmldoc.getElementsByTagName(elem_str_list[0])
            if element_list != [] :
                element_parent = element_list[0]
                del elem_str_list[0]
                # Parcourir les différent noeud
                for elem_str in elem_str_list:
                    for element_child in element_parent.childNodes:
                        if element_child.nodeName == elem_str:
                            element_parent = element_child
                            break

                # Rechercher l'élement dans le noeud le plus profond
                for element_child in element_parent.childNodes:
                    if element_child.nodeName == element_name:
                        find_element = element_child
                        break

    return find_element

#########################################################################
# FONCTION findAllElement()                                             #
#########################################################################
def findAllElement(xmldoc, element_name, element_path=''):
    """
    #   Role : Fonction qui retourne tous les élements identique d'un noeud
    #   Paramètres en entrée :
    #       xmldoc : le contenu xml au format dom
    #       element_name : le nom du noeud recherché
    #       element_path : le chemin du noeud recherché (complet ou partiel), par défaut vide
    #   Paramétre de retour :
    #        la liste l'élement trouvés
    """

    find_elements_list = []

    if xmldoc is not None:

        if element_path == '' :
            element_list = xmldoc.getElementsByTagName(element_name)
            find_elements_list = element_list
        else:
            elem_str_list = element_path.split('/')
            if '' in elem_str_list:
                elem_str_list.remove('')
            element_list = xmldoc.getElementsByTagName(elem_str_list[0])
            if element_list != [] :
                element_parent = element_list[0]
                del elem_str_list[0]
                # Parcourir les différent noeud
                for elem_str in elem_str_list:
                    for element_child in element_parent.childNodes:
                        if element_child.nodeName == elem_str:
                            element_parent = element_child
                            break

                # Rechercher l'élement dans le noeud le plus profond
                for element_child in element_parent.childNodes:
                    if element_child.nodeName == element_name:
                        find_elements_list.append(element_child)

    return find_elements_list

#########################################################################
# FONCTION getValueNodeDataDom()                                        #
#########################################################################
def getValueNodeDataDom(xmldoc, element_name, element_path=''):
    """
    #   Role : Fonction qui retourne le valeur d'un noeud
    #   Paramètres en entrée :
    #       xmldoc : le contenu xml au format dom
    #       element_name : le nom du noeud recherché
    #       element_path : le chemin du noeud recherché (complet ou partiel), par défaut vide
    #   Paramétre de retour :
    #        la valeur
    """

    value = ""

    if xmldoc is not None:

        # Recherche de l'élement
        find_element = findElement(xmldoc, element_name, element_path)

        # Recuperer la valeur de l'élémént
        if find_element is not None:
            if find_element.firstChild != None:
                value = str(find_element.firstChild.data)

    return value

#########################################################################
# FONCTION getListNodeDataDom()                                         #
#########################################################################
def getListNodeDataDom(xmldoc, element_parent_name, element_name, element_path=''):
    """
    #   Role : Fonction qui retourne une liste de valeur de sous noeuds identiques
    #   Paramètres en entrée :
    #       xmldoc : le contenu xml au format dom
    #       element_parent_name : le nom du noeud parent recherché
    #       element_name : le nom des noeuds fils identiques
    #       element_path : le chemin du noeud parent recherché (complet ou partiel), par défaut vide
    #   Paramétre de retour :
    #        la liste de valeur
    """

    value_list = []

    if xmldoc is not None:

        # Recherche de l'élement
        find_element = findElement(xmldoc, element_parent_name, element_path)

        # Recuperer toutes les valeurs de la liste d'éléménts
        if find_element is not None:
            for element_child in find_element.childNodes:
                if element_child.nodeName == element_name:
                    if element_child.firstChild != None:
                        value = str(element_child.firstChild.data)
                        if six.PY2:
                            value = value.encode('cp1252')
                        value_list.append(value)
                    else:
                        value_list.append("")
    return value_list

#########################################################################
# FONCTION getValueAttributeDom()                                       #
#########################################################################
def getValueAttributeDom(xmldoc, attribute_name, element_name='',  element_path=''):
    """
    #   Role : Fonction qui retourne le valeur d'un attibut d'un noeud
    #   Paramètres en entrée :
    #       xmldoc : le contenu xml au format dom
    #       attribute_name : le nom de l'attribut rechercher pour le noeud
    #       element_name : le nom du noeud recherché
    #       element_path : le chemin du noeud recherché (complet ou partiel), par défaut vide
    #   Paramétre de retour :
    #        la valeur
    """

    value = ""

    if xmldoc is not None:
        if element_name != '':
            # Recherche de l'élement
            find_element = findElement(xmldoc, element_name, element_path)
        else :
            find_element = xmldoc

        # Recuperer la valeur de l'attribut de l'élémént
        if find_element is not None:
            value = str(find_element.attributes[attribute_name].value)

    return value

#########################################################################
# FONCTION getListValueAttributeDom()                                   #
#########################################################################
def getListValueAttributeDom(xmldoc, element_parent_name, element_name, attribute_name, element_path=''):
    """
    #   Role : Fonction qui retourne une liste de valeur d'attributs (identiques) de sous noeuds identiques
    #   Paramètres en entrée :
    #       xmldoc : le contenu xml au format dom
    #       element_parent_name : le nom du noeud parent recherché
    #       element_name : le nom des noeuds fils identiques
    #       attribute_name : le nom de l'attribut rechercher pour les noeuds identiques
    #       element_path : le chemin du noeud parent recherché (complet ou partiel), par défaut vide
    #   Paramétre de retour :
    #        la liste de valeur
    """

    value_list = []

    if xmldoc is not None:

        # Recherche de l'élement
        find_element = findElement(xmldoc, element_parent_name, element_path)

        # Recuperer toute les valeurs d'attribut de la liste d'éléménts
        if find_element is not None:
            for element_child in find_element.childNodes:
                if element_child.nodeName == element_name:
                    if attribute_name in element_child.attributes.keys():
                        if six.PY2:
                            attribute = element_child.attributes[attribute_name].value.encode('cp1252')
                        else :
                            attribute = str(element_child.attributes[attribute_name].value)
                    else:
                        attribute = ''
                    value_list.append(attribute)

    return value_list
