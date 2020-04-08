# -*- coding: utf-8 -*-
#!/usr/bin/python

#############################################################################
# Copyright (©) CEREMA/DTerSO/DALETT/SCGSI  All rights reserved.            #
#############################################################################

#############################################################################
#                                                                           #
# FONCTIONS MATHEMATIQUES DE BASE                                           #
#                                                                           #
#############################################################################

# Doc sur les lists : https://docs.python.org/2/tutorial/datastructures.html

import sys, math
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC

#########################################################################
# FONCTION average()                                                    #
#########################################################################
#   Rôle : Cette fonction permet de calculer la moyenne des valeurs d'une liste (ou tableau)
#   Paramètres en entrée :
#       input_table : liste ou matrice
#   Paramétre de retour : valeur statistique moyenne

def average(table) :
    return sum(table, 0.0) / len(table)

#########################################################################
# FONCTION variance()                                                   #
#########################################################################
#   Rôle : Cette fonction permet de calculer la variance des valeurs d'une liste (ou tableau)
#   Paramètres en entrée :
#       input_table : liste ou matrice
#   Paramétre de retour : valeur statistique variance

def variance(table) :
    m = average(table)
    return average([(x-m)**2 for x in table])

#########################################################################
# FONCTION standardDeviation()                                          #
#########################################################################
#   Rôle : Cette fonction permet de calculer l'ecart type des valeurs d'une liste (ou tableau)
#   Paramètres en entrée :
#       input_table : liste ou matrice
#   Paramétre de retour : valeur ecart type moyenne

def standardDeviation(table) :
    return variance(table)**0.5

#########################################################################
# FONCTION computeDistance()                                            #
#########################################################################
#   Rôle : Cette fonction calcule la distance euclidienne entre des points

def computeDistance(coor1, coor2):
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
#   Rôle : Cette fonction calcule l'index de la plus petite valeur d'une liste

def findMinPosition(list_input):
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
#   Rôle : Cette fonction calcule le centre de gravite d'un vecteur

def findGravityCenter(vector):
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
#   Rôle : Cette fonction calcule l'index de la plus petite valeur d'une liste, hors valeur particuliere

def findMinPositionExceptValue(list_input, lsauf_value):
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
#   Rôle : Cette fonction calcule l'index de la plus grande valeur d'une liste

def findMaxPosition(list_input):
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
#   Rôle : Cette fonction identifie si une valeur est dans une liste

def findMemberList(list_input, value):
    for comp in list_input:
        if comp == value:
            return True
    return False

#########################################################################
# FONCTION sortList()                                                   #
#########################################################################
#   Rôle : Cette fonction trie une liste
#     bType = True : tri par ordre croissant
#     bType = False : tri par ordre décroissant

def sortList(list_input, bType):
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
#   Rôle : Cette fonction trouve la position d'une valeur dans une liste

def findPositionList(list_input, value):
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
#   Rôle : Cette fonction convertit une matrice en liste

def convertMatix2List(matrix):
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
#   Rôle : Cette fonction calcule la valeur moyenne d'une liste

def computeAverageValue(lArray):
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
#   Rôle : Cette fonction calcule l'ecart type d'une liste

def computeStandardDeviation(lArray):
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
#   Rôle : Cette fonction normalise une matrice

# Attention : fonction qui appelle
# - convertMatix2List
# - computeAverageValue
# - computeStandardDeviation

# CODE A VALIDER

def normalizeMatrix(matrix):
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
