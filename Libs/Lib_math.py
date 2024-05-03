#! /usr/bin/python
# -*- coding: utf-8 -*-

#############################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.               #
#############################################################################

#############################################################################
#                                                                           #
# FONCTIONS MATHEMATIQUES DE BASE                                           #
#                                                                           #
#############################################################################
"""
 Ce module contient des fonctions mathématique de base.
 Doc sur les lists : https://docs.python.org/2/tutorial/datastructures.html.
"""

import sys, math
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC

#########################################################################
# FONCTION average()                                                    #
#########################################################################
def average(table) :
    """
    #   Rôle : Cette fonction permet de calculer la moyenne des valeurs d'une liste (ou tableau)
    #   Paramètres en entrée :
    #       input_table : liste ou matrice
    #   Paramétre de retour : valeur statistique moyenne
    """

    return sum(table, 0.0) / len(table)

#########################################################################
# FONCTION variance()                                                   #
#########################################################################
def variance(table) :
    """
    #   Rôle : Cette fonction permet de calculer la variance des valeurs d'une liste (ou tableau)
    #   Paramètres en entrée :
    #       input_table : liste ou matrice
    #   Paramétre de retour : valeur statistique variance
    """

    m = average(table)
    return average([(x-m)**2 for x in table])

#########################################################################
# FONCTION standardDeviation()                                          #
#########################################################################
def standardDeviation(table) :
    """
    #   Rôle : Cette fonction permet de calculer l'ecart type des valeurs d'une liste (ou tableau)
    #   Paramètres en entrée :
    #       input_table : liste ou matrice
    #   Paramétre de retour : valeur ecart type moyenne
    """

    return variance(table)**0.5

#########################################################################
# FONCTION computeDistance()                                            #
#########################################################################
def computeDistance(coor1, coor2):
    """
    #   Rôle : Cette fonction calcule la distance euclidienne entre des points
    #   Paramètres en entrée :
    #       coor1 : coordonnée du point 1
    #       coor2 : coordonnée du point 2
    #   Paramétre de retour : valeur de la distance entre les 2 points
    """

    fDistance = -1
    iNb1 = len(coor1)
    iNb2 = len(coor2)
    if (iNb1 == 0 and iNb2 == 0) or (iNb1 != iNb2):
         print(cyan + "\n computeDistance() : " + bold + yellow +" PROBLEME, les lists de point sont incompatibles " + endC)
    else:
        fDistance = 0.0
        for i in range(iNb1):
            fDistance = fDistance + math.pow(float(coor1[i]) - float(coor2[i]), 2)
    fDistance = math.sqrt(fDistance)
    return fDistance

#########################################################################
# FONCTION indMinPosition()                                             #
#########################################################################
def findMinPosition(list_input):
    """
    #   Rôle : Cette fonction calcule l'index de la plus petite valeur d'une liste
    #   Paramètres en entrée :
    #       list_input : liste de valeur d'entrée
    #   Paramétre de retour : l'index de la plus petite valeur
    """

    pos = 0
    list_Lenght = len(list_input)
    iMin = list_input[0]
    i = 1;
    while True:
        if list_input[i] < iMin:
            iMin = list_input[i]
            pos = i
        i = i+1
        if i == list_Lenght:
            break
    return pos

#########################################################################
# FONCTION findGravityCenter()                                          #
#########################################################################
def findGravityCenter(vector):
    """
    #   Rôle : Cette fonction calcule le centre de gravite d'un vecteur
    #   Paramètres en entrée :
    #       vector : le vecteur d'entrée
    #   Paramétre de retour : le centre de gravite du vecteur
    """

    # Structure de la table : [[a1, b1, c1 ... n1], [a2, b2, c2 ... n2], ...[,]]
    # Liste des centres gravites de chaque colonne
    centreGravite = []
    # Calcul du nombre de lignes
    iNombreTotal = len(vector)
    # Calcul du nombre de composant correspondant a chaque ligne
    iNombreTotalSousVecteur = 0

    if iNombreTotal > 0:
        iNombreTotalSousVecteur = len(vector[0])

    # Calcul de la value moyenne de chaque colone a, b, c...
    i = 0
    while True:
        total = 0
        j = 0
        while True:
            # Calculer la somme
            total = total + float(vector[j][i])
            j = j + 1
            if j == iNombreTotal:
                break

        # Obtention de la value moyenne
        total = total / iNombreTotal
        # Ajout à la liste finale
        centreGravite.append(total)

        i = i + 1
        if i == iNombreTotalSousVecteur:
            break

    return centreGravitex

#########################################################################
# FONCTION findMinPositionExceptValue()                                 #
#########################################################################
def findMinPositionExceptValue(list_input, lsauf_value):
    """
    #   Rôle : Cette fonction calcule l'index de la plus petite valeur d'une liste, hors valeur particuliere
    #   Paramètres en entrée :
    #       list_input : liste de valeur d'entrée
    #       lsauf_value : liste du valeur à extraire de la recherche
    #   Paramétre de retour : l'index de la plus petite valeur
    """

    pos = 0
    iMin = 0.0
    iNombre = len(list_input)
    i = 0
    while True:
        bTrouver = False
        for value in lsauf_value:
            if list_input[i] == value:
                bTrouver = True
        if bTrouver == False:
            pos = i
            iMin = list_input[i]
            break
        else:
            i = i+1
            if (i == iNombre):
                break
    i = 0
    while True:
        if list_input[i] < iMin:
            bTrouver = False
            for value in lsauf_value:
                if list_input[i] == value:
                    bTrouver = True
            if bTrouver == False:
                iMin = list_input[i]
                pos = i
        #*****Quitter la boucle*****
        i = i+1
        if(i == iNombre):
            break
    return pos

#########################################################################
# FONCTION findMaxPosition()                                            #
#########################################################################
def findMaxPosition(list_input):
    """
    #   Rôle : Cette fonction calcule l'index de la plus grande valeur d'une liste
    #   Paramètres en entrée :
    #       list_input : liste de valeur d'entrée
    #   Paramétre de retour : l'index de la plus grande valeur
    """

    posMax = -1
    vMax = -9999
    for i in range(0, len(list_input)):
        if list_input[i] > vMax:
            vMax = list_input[i]
            posMax = i

    return posMax

#########################################################################
# FONCTION findMemberList()                                             #
#########################################################################
def findMemberList(list_input, value):
    """
    #   Rôle : Cette fonction identifie si une valeur est dans une liste
    #   Paramètres en entrée :
    #       list_input : liste de valeur d'entrée
    #       value : la valeur à rechercher
    #   Paramétre de retour : vrai ou faux selon que la valeur est trouver ou pas
    """

    for comp in list_input:
        if comp == value:
            return True
    return False

#########################################################################
# FONCTION sortList()                                                   #
#########################################################################
def sortList(list_input, bType):
    """
    #   Rôle : Cette fonction trie une liste
    #   Paramètres en entrée :
    #       list_input : liste de valeur d'entrée
    #       bType = True : tri par ordre croissant
    #       bType = False : tri par ordre décroissant
    #   Paramétre de retour : la liste triée
    """

    retListe = list_input
    iLen = len(list_input)
    for i in range(0, iLen):
        for j in range(i+1, iLen):
            if (bType == True and retListe[j] < retListe[i]) or (bType == False and retListe[j] > retListe[i]):
                temp = retListe[i]
                retListe[i] = retListe[j]
                retListe[j] = temp
    return retListe

#########################################################################
# FONCTION findPositionList()                                           #
#########################################################################
def findPositionList(list_input, value):
    """
    #   Rôle : Cette fonction trouve la position d'une valeur dans une liste
    #   Paramètres en entrée :
    #       list_input : liste de valeur d'entrée
    #       value : la valeur à rechercher
    #   Paramétre de retour : l'index de la valeur recherchée
    """

    iPos = -1
    iNb = len(list_input)
    for i in range(0,iNb):
        if list_input[i] == value:
            iPos = i
            break

    return iPos

#########################################################################
# FONCTION convertMatix2List(()                                         #
#########################################################################
def convertMatix2List(matrix):
    """
    #   Rôle : Cette fonction convertit une matrice en liste
    #   Paramètres en entrée :
    #       matrix : matrice d'entrée
    #   Paramétre de retour : la liste de sortie
    """

    lArray = []
    iNbLigne = len(matrix)
    iNbCol = len(matrix[0])
    for i in range(0,iNbLigne):
        for j in range(0, iNbCol):
            lArray.append(matrix[i][j])
    return lArray

#########################################################################
# FONCTION computeAverageValue()                                        #
#########################################################################
def computeAverageValue(lArray):
    """
    #   Rôle : Cette fonction calcule la valeur moyenne d'une liste
    #   Paramètres en entrée :
    #       lArray : liste de valeur d'entrée
    #   Paramétre de retour : la valeur moyenne de la liste
    """

    moyenne = 0.0
    iNombre = len(lArray)
    i = 0
    while True:
        moyenne = moyenne + lArray[i]
        #*****Quitter la boucle*****
        i = i+1
        if(i == iNombre):
            break

    moyenne = (moyenne / iNombre)

    return moyenne

#########################################################################
# FONCTION computeStandardDeviation()                                   #
#########################################################################
def computeStandardDeviation(lArray):
    """
    #   Rôle : Cette fonction calcule l'ecart type d'une liste
    #   Paramètres en entrée :
    #       lArray : liste de valeur d'entrée
    #   Paramétre de retour : l'ecart type de la liste
    """

    ecartType = 0.0
    moyenne = computeAverageValue(lArray)
    iNombre = len(lArray)
    i = 0
    while True:
        ecartType = ecartType + math.pow((lArray[i] - moyenne), 2)
        i=i+1
        if(i == iNombre):
            break
    ecartType = (ecartType / iNombre)
    ecartType = math.sqrt(ecartType)
    return ecartType

#########################################################################
# FONCTION normalizeMatrix(()                                           #
#########################################################################
def normalizeMatrix(matrix):
    """
    #   Rôle : Cette fonction normalise une matrice
    #     Attention : fonction qui appelle
    #     - convertMatix2List
    #     - computeAverageValue
    #     - computeStandardDeviation
    #   Paramètres en entrée :
    #       matrix : matrice d'entrée
    #   Paramétre de retour : la martrice de sortie normalisée
    """

    matrix_nor = []
    lArray = convertMatix2List(matrix)
    fMoyenne = computeAverageValue(lArray)
    fEcartType = computeStandardDeviation(lArray)
    iNbLigne = len(matrix)
    iNbCol = len(matrix[0])

    for i in range(0, iNbLigne):
        ligne = []
        for j in range(0, iNbCol):
            ligne.append(float(matrix[i][j] + fMoyenne) / fEcartType)
        matrix_nor.append(ligne)
    return matrix_nor
