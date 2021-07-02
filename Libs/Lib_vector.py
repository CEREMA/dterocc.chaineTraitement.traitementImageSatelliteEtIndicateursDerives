# -*- coding: utf-8 -*-
#!/usr/bin/python

#############################################################################
# Copyright (©) CEREMA/DTerSO/DALETT/SCGSI  All rights reserved.            #
#############################################################################

#############################################################################
#                                                                           #
# FONCTIONS DE BASE SUR LES VECTEURS (fichier shapefile)                    #
#                                                                           #
#############################################################################
#
# Ce module contient un certain nombre de fonctions de bases pour réaliser des géotraitements sur les shapefiles, ils reposent tous sur les bibliothèques OGR GDAL et OTB
#

# IMPORTS DIVERS
from __future__ import print_function
import sys,os,glob
from osgeo import ogr ,osr
from rasterstats2 import raster_stats
from Lib_operator import *
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC
from Lib_file import renameVectorFile, removeVectorFile

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 3 : affichage maximum de commentaires lors de l'execution du script. Intermédiaire : affichage intermédiaire
debug = 1

########################################################################
# FONCTION updateProjection()                                          #
########################################################################
# Rôle : cette fonction met à jour la projection d'un fichier shape, peu importe sa projection d'origine.
# Paramètres en entrée :
#       vector_input : vecteur d'entrée, celui à qui on veut changer la projection
#       vector_output : vecteur de sortie, celui avec la nouvelle projection
#       projection : projection à appliquer, code EPSG (par défaut : 2154)
#       format_vector : format du vecteur de sortie (par défaut : ESRI Shapefile)
# Paramètres en sortie :
#       N.A.

def updateProjection(vector_input, vector_output, projection=2154, format_vector='ESRI Shapefile'):

    if debug >=2:
        print(cyan + "updateProjection() : " + endC + "mise à jour de la projection du fichier " + vector_input + " (code EPSG : " + str(projection) + ")." + endC)

    command = "ogr2ogr -f '%s' -t_srs EPSG:%s %s %s" % (format_vector, projection, vector_output, vector_input)
    if debug >=2:
        print(command)
    exit_code = os.system(command)
    if exit_code != 0:
        print(cyan + "updateProjection() : " + bold + red + "!!! Une erreur c'est produite au cours de la mise a jour de la projection du vecteur : " + vector_input + endC, file=sys.stderr)

    if debug >=2:
        print(cyan + "updateProjection() : " + endC + "le fichier " + vector_input + " a été mis à jour vers " + vector_output + "." + endC)

    return

########################################################################
# FONCTION getProjection()                                             #
########################################################################
# Rôle : cette fonction retourne la valeur de la projection la projection d'un fichier shape.
# Paramètres en entrée :
#       vector_input : vecteur d'entrée, celui à qui on veut recupere la projection
#       format_vector : format du vecteur d'entrée (par défaut : ESRI Shapefile)
# Paramètres en sortie :
#       N.A.

def getProjection(vector_input, format_vector='ESRI Shapefile'):

    if debug >=2:
        print(cyan + "getProjection() : Récupération de la projection du vecteur : " + vector_input + endC)

    projection = None

     # Recuperation du  driver pour le format shape
    driver = ogr.GetDriverByName(format_vector)

    # Ouverture du fichier d'emprise
    data_source = driver.Open(vector_input, 0)
    if data_source is None:
        print(cyan + "getProjection() : " + bold + red + "Impossible d'ouvrir le fichier d'emprise : " + vector_input + endC, file=sys.stderr)
        sys.exit(1) #exit with an error code

    # Recuperation des couches de donnees
    layer = data_source.GetLayer()
    spatialRef = layer.GetSpatialRef()

    # Recuperation de la projection
    feature_input = layer.GetNextFeature()
    geometry = feature_input.GetGeometryRef()
    projectio_txt = geometry.GetSpatialReference().ExportToWkt()
    len_index = len(projectio_txt)
    last_index = projectio_txt.rfind('AUTHORITY["EPSG"')
    if last_index >= 0 :
        projectio_txt_bis = projectio_txt[last_index:]
        projection_txt = projectio_txt_bis.split('"')[3]
        projection = int(projection_txt)

    return projection

###########################################################################################################################################
# FONCTION getEmpriseFile()                                                                                                               #
###########################################################################################################################################
#   Role : Cette fonction permet de retourner les coordonnées xmin,xmax,ymin,ymax de l'emprise d'un fichier shape
#   Parametres :
#       vector_input : nom du fichier vecteur d'entrée
#       format_vector : format du fichier vecteur
#   Paramétres de retour :
#       xmin, xmax, ymin, ymax

def getEmpriseFile(vector_input, format_vector='ESRI Shapefile'):

    if debug >=2:
        print(cyan + "getEmpriseFile() : Début de la récupération des emprises" + endC)

    # Recuperation du  driver pour le format shape
    driver = ogr.GetDriverByName(format_vector)

    # Ouverture du fichier d'emprise
    data_source = driver.Open(vector_input, 0)
    if data_source is None:
        print(cyan + "getEmpriseFile() : " + bold + red + "Impossible d'ouvrir le fichier d'emprise : " + vector_input + endC, file=sys.stderr)
        sys.exit(1) #exit with an error code

    # Recuperation des couches de donnees
    layer = data_source.GetLayer(0)
    num_features = layer.GetFeatureCount()
    extent = layer.GetExtent()

    # Fermeture du fichier d'emprise
    data_source.Destroy()

    xmin = extent[0]
    xmax = extent[1]
    ymin = extent[2]
    ymax = extent[3]

    if debug >=2:
        print(cyan + "getEmpriseFile() : " + bold + green + "Fin de la récupération des emprises" + endC)

    return xmin,xmax,ymin,ymax

#########################################################################
# FONCTION getAreaPolygon()                                             #
#########################################################################
#   Role : Fonction qui retourne la somme des surfaces de polygones défini par un champs et une valeur
#   Paramètres en entrée :
#       vector_input : nom du fichier vecteur d'entrée
#       col : nom du champs (colonne) à regarder
#       value : valeur du champs pour identifier le polygone ou les polygones
#       format_vector : format d'entrée du fichier vecteur. Par default : 'ESRI Shapefile'
#   Paramétre de retour :
#        sum_area : la somme des surface

def getAreaPolygon(vector_input, col, value, format_vector='ESRI Shapefile'):
    # Variable de retour
    sum_area = 0.0
    if debug >=2:
       print(cyan + "getAreaPolygon() : " + endC + "Lecture de la surface des polygones de l'image : " + str(vector_input))

    # Recuperation du driver pour le format shape fichier entrée
    driver_input = ogr.GetDriverByName(format_vector)

    # Ouverture du fichier shape en lecture
    data_source_input = driver_input.Open(vector_input, 0) # 0 means read-only.
    if data_source_input is None:
        print(cyan + "getAreaPolygon() : " + bold + red + "Impossible d'ouvrir le fichier shape : " + vector_input + endC, file=sys.stderr)
        return -1.0

    # Recuperer la couche (une couche contient les polygones)
    layer_input = data_source_input.GetLayer(0)

    # Recuperer le nombre de champs du fichier d'entrée
    defn_layer_input = layer_input.GetLayerDefn()
    nb_fields = defn_layer_input.GetFieldCount()

    # Pour chaque polygones
    for i in range(0, layer_input.GetFeatureCount()):
         # Get the input Feature
         feature_input = layer_input.GetFeature(i)

         # Si le polygone correspond au polygone rechercher
         field_label = feature_input.GetFieldAsString(col)
         if field_label == str(value) :
             # Get polygon area
             geometry = feature_input.GetGeometryRef()
             if not geometry is None :
                 sum_area += geometry.GetArea()

    # Fermeture du fichier shape
    data_source_input.Destroy()
    if debug >=2:
       print(cyan + "getAreaPolygon() : " + bold + green + "Recuperation de la surface polygone fichier %s, surface = %f" %(vector_input, sum_area) + endC)
    return sum_area

#########################################################################
# FONCTION getNumberFeature()                                           #
#########################################################################
#   Role : Fonction qui retourne le nombre d'element geometrique (point ou ligne ou polygone) dans un fichier vecteur
#   Paramètres en entrée :
#       vector_input : nom du fichier vecteur d'entrée
#       format_vector : format d'entrée du fichier vecteur. Par default : 'ESRI Shapefile'
#   Paramétre de retour :
#        number_polygon : le nombre de polygones trouvé

def getNumberFeature(vector_input, format_vector='ESRI Shapefile'):
    # Variable de retour
    number_feature = 0
    if debug >=2:
       print(cyan + "getNumberFeature() : " + endC + "Lecture du nombre de polygones du vecteur : " + str(vector_input))

    # Recuperation du driver pour le format shape fichier entrée
    driver_input = ogr.GetDriverByName(format_vector)

    # Ouverture du fichier shape en lecture
    data_source_input = driver_input.Open(vector_input, 0) # 0 means read-only.
    if data_source_input is None:
        print(cyan + "getNumberFeature() : " + bold + red + "Impossible d'ouvrir le fichier vecteur : " + vector_input + endC, file=sys.stderr)
        return -1.0

    # Recuperer la couche (une couche contient les polygones)
    layer_input = data_source_input.GetLayer(0)

    # Get the feature count
    number_feature = layer_input.GetFeatureCount()

    # Fermeture du fichier shape
    data_source_input.Destroy()
    if debug >=2:
       print(cyan + "getNumberFeature() : " + bold + green + "Recuperation du nombre de feature  du fichier %s, elements = %d" %(vector_input, number_feature) + endC)
    return number_feature

#########################################################################
# FONCTION getGeomPolygons()                                            #
#########################################################################
#   Role : Fonction qui retourne la liste de géometrie des polygones défini par un champs et une valeur
#   Paramètres en entrée :
#       vector_input : nom du fichier vecteur d'entrée
#       col : nom du champs (colonne) à regarder si None tous les polygonnes sont retournés (valeur par defaut)
#       value : valeur du champs pour identifier le polygone si None tous les polygonnes sont retournés (valeur par defaut)
#       format_vector : format d'entrée du fichier vecteur. Par default : 'ESRI Shapefile'
#   Paramétre de retour :
#        geometry_list : la liste de géometrie de polygone

def getGeomPolygons(vector_input, col=None, value=None, format_vector='ESRI Shapefile'):
    # Variable de retour
    geometry_list = []
    if debug >=2:
       print(cyan + "getGeomPolygons() : " + endC + "Recherche les polygones valeur: " + str(value) + " champs : " + str(col) + " du fichier : " + str(vector_input))

    # Recuperation du driver pour le format shape fichier entrée
    driver_input = ogr.GetDriverByName(format_vector)

    # Ouverture du fichier shape en lecture
    data_source_input = driver_input.Open(vector_input, 0) # 0 means read-only.
    if data_source_input is None:
        print(cyan + "getGeomPolygons() : " + bold + red + "Impossible d'ouvrir le fichier shape : " + vector_input + endC, file=sys.stderr)
        return None

    # Recuperer la couche (une couche contient les polygones)
    layer_input = data_source_input.GetLayer(0)

    # Recuperer le nombre de champs du fichier d'entrée
    defn_layer_input = layer_input.GetLayerDefn()
    nb_fields = defn_layer_input.GetFieldCount()

    # Pour chaque polygones
    for i in range(0, layer_input.GetFeatureCount()):
         # Get the input Feature
         feature_input = layer_input.GetFeature(i)

         # Si le polygone correspond au polygone rechercher
         if (not col == None) or (not value == None) :
             field_label = feature_input.GetFieldAsString(col)
             if field_label == str(value) :
                 # Get polygon geometry
                 geometry_list.append(feature_input.GetGeometryRef().Clone())
         else : # On recupere tous les polygones
             geometry_list.append(feature_input.GetGeometryRef().Clone())

    # Fermeture du fichier shape
    data_source_input.Destroy()
    if debug >=2:
       print(cyan + "getGeomPolygons() : " + bold + green + "Recuperation de la liste de géométrie de polygone fichier %s" %(vector_input) + endC)
    return geometry_list


#########################################################################
# FONCTION getGeometryType()                                            #
#########################################################################
#   Role : Fonction qui retourne le type de  géometrie d'un fichier vecteur
#   Paramètres en entrée :
#       vector_input : nom du fichier vecteur d'entrée
#       format_vector : format d'entrée du fichier vecteur. Par default : 'ESRI Shapefile'
#   Paramétre de retour :
#        geometry_type : le type de  géometrie

def getGeometryType(vector_input, format_vector='ESRI Shapefile'):
    # Variable de retour
    geometry_type = None
    if debug >=2:
       print(cyan + "getGeometryType() : " + endC + "Recherche le type de geometrie du fichier : " + str(vector_input))

    # Recuperation du driver pour le format shape fichier entrée
    driver_input = ogr.GetDriverByName(format_vector)

    # Ouverture du fichier shape en lecture
    data_source_input = driver_input.Open(vector_input, 0) # 0 means read-only.
    if data_source_input is not None:
        # Recuperer la couche
        layer_input = data_source_input.GetLayer(0)

        # Get the input Feature
        if layer_input.GetFeatureCount() > 0 :
            feature_input = layer_input.GetFeature(0)

            # Get polygon geometry
            geometry = feature_input.GetGeometryRef()
            if geometry != None :
                geometry_type = geometry.GetGeometryName()
            elif layer_input.GetFeatureCount() > 1 :
                for idFeature in range(1,layer_input.GetFeatureCount()) :
                    feature_input = layer_input.GetFeature(idFeature)
                    geometry = feature_input.GetGeometryRef()
                    if geometry != None :
                        geometry_type = geometry.GetGeometryName()
                        break

        # Fermeture du fichier shape
        data_source_input.Destroy()

    if debug >=2:
        print(cyan + "getGeometryType() : %s " %(str(geometry_type)) + bold + green + "Recuperation du type de géométrie du fichier %s : " %(vector_input) + endC)

    if geometry_type == None :
        print(cyan + "getGeometryType() : " + bold + yellow + "Impossible d'ouvrir le fichier shape ou de definir le type de géométrie : " + vector_input + endC)

    return geometry_type

#########################################################################
# FONCTION getAttributeNameList()                                       #
#########################################################################
#   Role : Fonction qui retourne la liste des noms  des attributs constituant le vecteur
#   Paramètres en entrée :
#       vector_input : nom du fichier vecteur d'entrée
#       format_vector : format d'entrée du fichier vecteur. Par default : 'ESRI Shapefile'
#   Paramétre de retour : attr_nanes_list : listes des noms des attributs

def getAttributeNameList(vector_input, format_vector='ESRI Shapefile') :

    if debug >=2:
       print(cyan + "getAttributeNameList() : " + endC + "Recuperation des noms des champs du fichier vecteur : " + str(vector_input))

    # Variable de retour liste des noms des champs
    attr_names_list = []

    # Recuperation du driver pour le format shape fichier entrée
    driver_input = ogr.GetDriverByName(format_vector)

    # Ouverture du fichier shape en lecture
    data_source_input = driver_input.Open(vector_input, 0) # 0 means read-only.
    if data_source_input is None:
        print(cyan + "getAttributeNameList() : " + bold + red + "Impossible d'ouvrir le fichier shape : " + vector_input + endC, file=sys.stderr)
        return attr_names_list

    # Récupération des cractéristiques du fichier en entrée
    layer_input = data_source_input.GetLayer()

    # Ajouter les champs du fichier d'entrée à la liste de sortie
    defn_layer_input = layer_input.GetLayerDefn()
    nb_fields = defn_layer_input.GetFieldCount()
    for i in range(0, nb_fields):
        field_defn = defn_layer_input.GetFieldDefn(i)
        attr_names_list.append(field_defn.GetNameRef())

    if debug >=2:
       print(cyan + "getAttributeNameList() : " + bold + green + "Recuperation des noms des champs du vecteur %s : " %(vector_input) + endC)
    return attr_names_list

#########################################################################
# FONCTION getAttributeType()                                           #
#########################################################################
#   Role : Fonction qui retourne le type d'un attribut défini dans par son un identifiant
#   Paramètres en entrée :
#       vector_input : nom du fichier vecteur d'entrée
#       attribute_name_id : nom du champs d'identification de l'élement
#       format_vector : format d'entrée du fichier vecteur. Par default : 'ESRI Shapefile'
#   Paramétre de retour : attr_type : type ogr d'attribut exemple  : (gr.OFTInteger, ogr.OFTReal, OFTString ...)

def getAttributeType(vector_input, attribute_name_id, format_vector='ESRI Shapefile') :

    if debug >=2:
       print(cyan + "getAttributeType() : " + endC + "Recuperation des valeurs d'un champs du fichier vecteur : " + str(vector_input))

    # Variable de retour liste des valeurs
    attribute_type = None

    # Recuperation du driver pour le format shape fichier entrée
    driver_input = ogr.GetDriverByName(format_vector)

    # Ouverture du fichier shape en lecture
    data_source_input = driver_input.Open(vector_input, 0) # 0 means read-only.
    if data_source_input is None:
        print(cyan + "getAttributeType() : " + bold + red + "Impossible d'ouvrir le fichier shape : " + vector_input + endC, file=sys.stderr)
        return attribute_type

    # Recuperer la couche (couche contenant les élements)
    layer_input = data_source_input.GetLayer(0)
    defn_layer_input = layer_input.GetLayerDefn()

    # Pour chaque champs
    for i in range(defn_layer_input.GetFieldCount()):
        field_defn = defn_layer_input.GetFieldDefn(i)

        if field_defn.GetName() == attribute_name_id :
            attribute_type = field_defn.GetType()

    # Fermeture du fichier shape
    data_source_input.Destroy()

    if debug >=2:
       print(cyan + "getAttributeType() : " + bold + green + "Recuperation du type du champs %s du vecteur %s : " %(attribute_name_id, vector_input) + endC)
    return attribute_type

#########################################################################
# FONCTION getAttributeValues()                                         #
#########################################################################
#   Role : Fonction qui retourne une liste (dico) de valeur d'attribut défini dans une liste pour un identifiant d'élement
#   Paramètres en entrée :
#       vector_input : nom du fichier vecteur d'entrée
#       attribute_name_id : nom du champs d'identification de l'élement si None retourne toutes les valeurs (et id_element = None)
#       id_element : la valeur d'identifiant de l'élement si None retourne toutes les valeurs (et attribute_name_id = None)
#       attribute_name_dico : dico des champs à récuperer et leur type
#       format_vector : format d'entrée du fichier vecteur. Par default : 'ESRI Shapefile'
#   Paramétre de retour : attr_values_dico : dictionaire des valeurs des attributs demander pour l'élement cherché

def getAttributeValues(vector_input, attribute_name_id, id_element, attribute_name_dico, format_vector='ESRI Shapefile') :

    if debug >=2:
       print(cyan + "getAttributeValues() : " + endC + "Recuperation des valeurs d'un champs du fichier vecteur : " + str(vector_input))

    # Variable de retour liste des valeurs
    attr_values_dico = None

    # Recuperation du driver pour le format shape fichier entrée
    driver_input = ogr.GetDriverByName(format_vector)

    # Ouverture du fichier shape en lecture
    data_source_input = driver_input.Open(vector_input, 0) # 0 means read-only.
    if data_source_input is None:
        print(cyan + "getAttributeValues() : " + bold + red + "Impossible d'ouvrir le fichier shape : " + vector_input + endC, file=sys.stderr)
        return attr_values_dico

    # Recuperer la couche (couche contenant les élements)
    layer_input = data_source_input.GetLayer(0)

    # Pour chaque élement
    attr_values_dico = {}
    for attr_name in attribute_name_dico :
        attr_type = attribute_name_dico[attr_name]

        value_list = []
        for i in range(0, layer_input.GetFeatureCount()):
             # Get the input Feature
             feature_input = layer_input.GetFeature(i)

             # Si l'élement correspond à élement rechercher
             if (attribute_name_id == None and id_element == None) or (str(feature_input.GetFieldAsString(attribute_name_id)) == str(id_element)) :

                 value = None
                 while switch(attr_type):
                     if case(ogr.OFTInteger):
                        value =  feature_input.GetFieldAsInteger(attr_name)
                        break
                     if case(ogr.OFTReal):
                        value = feature_input.GetFieldAsDouble(attr_name)
                        break
                     if case(ogr.OFTString):
                        value = feature_input.GetFieldAsString(attr_name)
                        break
                     if case(ogr.OFTIntegerList):
                        value = feature_input.GetFieldAsIntegerList(attr_name)
                        break
                     '''
                     if case(ogr.OFTInteger64):
                        value = feature_input.GetFieldAsInteger64(attr_name)
                        break
                     if case(ogr.OFTInteger64List):
                        value = feature_input.GetFieldAsInteger64List(attr_name)
                        break
                     '''
                     if case(ogr.OFTRealList):
                        value = feature_input.GetFieldAsDoubleList(attr_name)
                        break
                     if case(ogr.OFTStringList):
                        value = feature_input.GetFieldAsStringList(attr_name)
                        break
                     if case(ogr.OFTDate):
                        value = feature_input.GetFieldAsDateTime(attr_name)
                        break
                     if case(ogr.OFTTime):
                        value = feature_input.GetFieldAsDateTime(attr_name)
                        break
                     if case(ogr.OFTDateTime):
                        value = feature_input.GetFieldAsDateTime(attr_name)
                        break
                     break

                 # Ajout de la valeur à la liste de sortie
                 value_list.append(value)

        attr_values_dico[attr_name] = value_list

    # Fermeture du fichier shape
    data_source_input.Destroy()

    if debug >=2:
       print(cyan + "getAttributeValues() : " + bold + green + "Recuperation des valeurs d'un champs du vecteur %s : " %(vector_input) + endC)
    return attr_values_dico

#########################################################################
# FONCTION setAttributeValues()                                         #
#########################################################################
#   Role : Fonction qui met à jour des valeurs d'attribut défini dans une liste (dico) pour un identifiant d'élement
#   Paramètres en entrée :
#       vector_input : nom du fichier vecteur d'entrée
#       attribute_name_id : nom du champs d'identification de l'élement
#       id_element : la valeur d'identifiant de l'élement
#       attribute_name_dico : dico des champs à mettre à jour et leur valeur
#       format_vector : format d'entrée du fichier vecteur. Par default : 'ESRI Shapefile'
#   Paramétre de retour : 0 si ok -1 sinon

def setAttributeValues(vector_input, attribute_name_id, id_element, attribute_name_dico, format_vector='ESRI Shapefile') :

    if debug >=2:
       print(cyan + "setAttributeValues() : " + endC + "mise à jour des valeurs d'un champs du fichier vecteur : " + str(vector_input))

    # Recuperation du driver pour le format shape fichier entrée
    driver_input = ogr.GetDriverByName(format_vector)

    # Ouverture du fichier shape en lecture
    data_source_input = driver_input.Open(vector_input, 1) # 1 means read-write.
    if data_source_input is None:
        print(cyan + "setAttributeValues() : " + bold + red + "Impossible d'ouvrir le fichier shape : " + vector_input + endC, file=sys.stderr)
        return  -1.0

    # Recuperer la couche (couche contenant les élements)
    layer_input = data_source_input.GetLayer(0)

    # Pour chaque élement
    for i in range(0, layer_input.GetFeatureCount()):
         # Get the input Feature
         feature_input = layer_input.GetFeature(i)

         # Si l'élement correspond à élement rechercher
         field_id = feature_input.GetFieldAsString(attribute_name_id)
         if str(field_id) == str(id_element) :

             # Pour tous les champs à mettre à jour
             for attr_name in attribute_name_dico :
                 attr_value = attribute_name_dico[attr_name]
                 # Ajouter la valeur au champ
                 feature_input.SetField(attr_name, attr_value)

             layer_input.SetFeature(feature_input)
             feature_input.Destroy()
             break

    # Fermeture du fichier shape
    layer_input.SyncToDisk()
    data_source_input.Destroy()

    if debug >=2:
       print(cyan + "setAttributeValues() : " + bold + green + "Mise à jour des valeurs d'un champs du vecteur %s : " %(vector_input) + endC)
    return 0

#########################################################################
# FONCTION setAttributeIndexValuesList()                                #
#########################################################################
#   Role : Fonction qui met à jour des valeurs d'attribut défini dans un dico (de dico de champs) pour un identifiant d'élement
#   Paramètres en entrée :
#       vector_input : nom du fichier vecteur d'entrée
#       attribute_name_id : nom du champs d'identification de l'élement
#       field_new_values_dico : dico des valeurs index par id de polygones (sur dico de champs à mettre à jour et leur valeur)
#       format_vector : format d'entrée du fichier vecteur. Par default : 'ESRI Shapefile'
#   Paramétre de retour : 0 si ok -1 sinon

def setAttributeIndexValuesList(vector_input, attribute_name_id, field_new_values_dico, format_vector='ESRI Shapefile') :

    if debug >=2:
       print(cyan + "setAttributeIndexValuesList() : " + endC + "mise à jour des valeurs des champs du fichier vecteur : " + str(vector_input))

    # Recuperation du driver pour le format shape fichier entrée
    driver_input = ogr.GetDriverByName(format_vector)

    # Ouverture du fichier shape en lecture
    data_source_input = driver_input.Open(vector_input, 1) # 1 means read-write.
    if data_source_input is None:
        print(cyan + "setAttributeIndexValuesList() : " + bold + red + "Impossible d'ouvrir le fichier shape : " + vector_input + endC, file=sys.stderr)
        return  -1.0

    # Recuperer la couche (couche contenant les élements)
    layer_input = data_source_input.GetLayer(0)

    # Pour chaque élement
    # Creation d'un dico d'index id sur les features
    features_index_dico = {}
    for i in range(0, layer_input.GetFeatureCount()):
         # Get the input Feature
         feature_input = layer_input.GetFeature(i)
         field_id = feature_input.GetFieldAsString(attribute_name_id)
         features_index_dico[field_id] = feature_input

    # Pour chaque élement à mettre à jour
    for index_id in field_new_values_dico :
        attribute_name_dico = field_new_values_dico[index_id]
        feature = features_index_dico[str(index_id)]

        # Pour tous les champs à mettre à jour
        for attr_name in attribute_name_dico :
            attr_value = attribute_name_dico[attr_name]

            # Ajouter la valeur au champ
            feature.SetField(attr_name, attr_value)

        layer_input.SetFeature(feature)
        feature.Destroy()

    # Fermeture du fichier shape
    layer_input.SyncToDisk()
    data_source_input.Destroy()

    if debug >=2:
       print(cyan + "setAttributeIndexValuesList() : " + bold + green + "Mise à jour des valeurs des champs du vecteur %s : " %(vector_input) + endC)
    return 0

#########################################################################
# FONCTION setAttributeValuesList()                                     #
#########################################################################
#   Role : Fonction qui met à jour des valeurs de liste d'attribut défini dans une liste de dico
#   Paramètres en entrée :
#       vector_input : nom du fichier vecteur d'entrée
#       field_new_values_list : liste de dico de champs à mettre à jour et leur valeur pour tous les elements du fichier
#       format_vector : format d'entrée du fichier vecteur. Par default : 'ESRI Shapefile'
#   Paramétre de retour : 0 si ok -1 sinon

def setAttributeValuesList(vector_input, field_new_values_list, format_vector='ESRI Shapefile') :

    if debug >=2:
       print(cyan + "setAttributeValuesList() : " + endC + "mise à jour des valeurs des champs du fichier vecteur : " + str(vector_input))

    # Recuperation du driver pour le format shape fichier entrée
    driver_input = ogr.GetDriverByName(format_vector)

    # Ouverture du fichier shape en lecture
    data_source_input = driver_input.Open(vector_input, 1) # 1 means read-write.
    if data_source_input is None:
        print(cyan + "setAttributeValuesList() : " + bold + red + "Impossible d'ouvrir le fichier shape : " + vector_input + endC, file=sys.stderr)
        return  -1.0

    # Recuperer la couche (couche contenant les élements)
    layer_input = data_source_input.GetLayer(0)

    # Pour chaque élement
    for i in range(0, layer_input.GetFeatureCount()):

         # Get the input Feature
         feature_input = layer_input.GetFeature(i)

         # Pour tous les champs à mettre à jour
         for attr_name in field_new_values_list[i] :
             attr_value = field_new_values_list[i][attr_name]

             # Ajouter la valeur au champ
             feature_input.SetField(attr_name, attr_value)

         layer_input.SetFeature(feature_input)
         feature_input.Destroy()

    # Fermeture du fichier shape
    layer_input.SyncToDisk()
    data_source_input.Destroy()

    if debug >=2:
       print(cyan + "setAttributeValuesList() : " + bold + green + "Mise à jour des valeurs des champs du vecteur %s : " %(vector_input) + endC)
    return 0

#########################################################################
# FONCTION updateIndexVector()                                          #
#########################################################################
#   Role : Fonction qui remets a jour les index des élements du fichier vecteur dans un champs défini par son nom
#   Paramètres en entrée :
#       vector_input : nom du fichier vecteur d'entrée
#       index_name : nom du champs (colonne) contenant la valeur de l'index par defaut à "id"
#       format_vector : format d'entrée du fichier vecteur. Par default : 'ESRI Shapefile'
#   Paramétre de retour : le nombre d'élement (index valeur max)

def updateIndexVector(vector_input, index_name="id", format_vector='ESRI Shapefile'):
    # Variable de retour
    index_max = 0

    if debug >=2:
       print(cyan + "updateIndexVector() : " + endC + "mise à jour des index du fichier vecteur : " + str(vector_input))

    # Recuperation du driver pour le format shape fichier entrée
    driver_input = ogr.GetDriverByName(format_vector)

    # Ouverture du fichier shape en lecture
    data_source_input = driver_input.Open(vector_input, 1) # 1 means read-write
    if data_source_input is None:
        print(cyan + "updateIndexVector() : " + bold + red + "Impossible d'ouvrir le fichier shape : " + vector_input + endC, file=sys.stderr)
        return -1.0

    # Recuperer la couche contenant les éléments
    layer_input = data_source_input.GetLayer(0)

    # Pour chaque polygones
    index_max = layer_input.GetFeatureCount()
    for i in range(0, index_max):

         # Update index of the input Feature
         feature_input = layer_input.GetFeature(i)
         feature_input.SetField(index_name, i+1)
         layer_input.SetFeature(feature_input)
         feature_input.Destroy()

    # Fermeture du fichier shape
    layer_input.SyncToDisk()
    data_source_input.Destroy()

    if debug >=2:
       print(cyan + "updateIndexVector() : " + bold + green + "Les index sont mis à jour pour fichier vecteur %s" %(vector_input) + endC)
    return index_max

########################################################################
# FONCTION updateFieldVector()                                         #
########################################################################
#   Role : Fonction qui met à jour (avec la même valeur partout) le champ d'un fichier vecteur
#   Paramètres en entrée :
#       vector_input : nom du fichier vecteur d'entrée
#       field_name : nom du champs (colonne) à mettre à jour. Par défaut : "id"
#       value : valeur à mettre à jour dans le champ (peut-être de tout type, pour peu que le type du champ corresponde). Par défaut : 0
#       format_vector : format d'entrée du fichier vecteur. Par défaut : 'ESRI Shapefile'
#   Paramètre de retour

def updateFieldVector(vector_input, field_name="id", value=0, format_vector='ESRI Shapefile'):
    if debug >=2:
       print(cyan + "updateFieldVector() : " + endC + "mise à jour du champ '" + field_name + "' du fichier vecteur " + vector_input + " avec la valeur de " + value)

    # Récuperation du driver pour le format shape du fichier d'entrée
    driver_input = ogr.GetDriverByName(format_vector)

    # Ouverture du fichier shape en écriture
    data_source_input = driver_input.Open(vector_input, 1)
    if data_source_input is None:
        print(cyan + "updateFieldVector() : " + bold + red + "Impossible d'ouvrir le fichier shape : " + vector_input + endC, file=sys.stderr)
        return -1.0

    # Récupérer la couche contenant les éléments
    layer_input = data_source_input.GetLayer(0)

    # Pour chaque polygone
    features_nb = layer_input.GetFeatureCount()
    for i in range(0, features_nb):

        # Mise à jour du champ pour le feature sélectionné
        feature_input = layer_input.GetFeature(i)
        feature_input.SetField(field_name, value)
        layer_input.SetFeature(feature_input)
        feature_input.Destroy()

    # Fermeture du fichier shape
    layer_input.SyncToDisk()
    data_source_input.Destroy()

    if debug >=2:
       print(cyan + "updateFieldVector() : " + bold + green + "Le champ a été mis à jour pour fichier vecteur " + vector_input + endC)

    return 0

#########################################################################
# FONCTION addNewFieldVector()                                          #
#########################################################################
#   Role : Cette fonction permet de rajouter un nouveau champ à un fichier vecteur
#          Si le champ existe déjà, il est effacé puis recréé
#   Parametres :
#       vector_input : fichier vecteur a modifier
#       field_name : le nom du nouveau champs à ajouter
#       field_type : le type du nouveau champs à ajouter
#       field_value : la valeur à donnéer au nouveau champs pour chaque éléments
#       field_width : la largeur du champs (par defaut à None)
#       field_precision : la précision pour le type ogr.OFTReal (par defaut à None)
#       format_vector : format du fichier vecteur (par defaut 'ESRI Shapefile')

def addNewFieldVector(vector_input, field_name, field_type, field_value=None, field_width=None, field_precision=None, format_vector='ESRI Shapefile') :

    if debug >=2:
        print(cyan + "addNewFieldVector() : " + endC + "Ajout d'un champs au vecteur : " + str(vector_input))
    if debug >=4:
        print(cyan + "addNewFieldVector() : " + endC + "field_name : " + str(field_name))
        print(cyan + "addNewFieldVector() : " + endC + "field_type : " + str(field_type))
        print(cyan + "addNewFieldVector() : " + endC + "field_value : " + str(field_value))
        print(cyan + "addNewFieldVector() : " + endC + "field_width: " + str(field_width))
        print(cyan + "addNewFieldVector() : " + endC + "field_precision : " + str(field_precision))

    # Recuperation du driver pour le format shape fichier entrée
    driver_input = ogr.GetDriverByName(format_vector)

    # Ouverture du fichier shape en lecture-ecriture
    data_source_input = driver_input.Open(vector_input, 1) # 1 means writeable.
    if data_source_input is None:
        print(cyan + "addNewFieldVector() : " + bold + red + "Impossible d'ouvrir le fichier shape : " + vector_input + endC, file=sys.stderr)
        sys.exit(1) # exit with an error code

    # Recuperer la couche (une couche contient les polygones)
    layer_input = data_source_input.GetLayer(0)

    # Vérification de l'existence de la colonne col (retour = -1 : elle n'existe pas)
    layer_definition = layer_input.GetLayerDefn() # GetLayerDefn => returns the field names of the user defined (created) fields
    id_field = layer_definition.GetFieldIndex(field_name)
    if id_field != -1 :
        print(cyan + "addNewFieldVector() : " + bold + yellow +"Attention le champs existe déjà, il est recréé : " + field_name + endC)
        layer_input.DeleteField(id_field)

    # Création du nouveau champs dans le fichier
    field = ogr.FieldDefn(field_name, field_type)
    if field_width is not None :
        field.SetWidth(field_width)
    if field_precision is not None and field_type == ogr.OFTReal:
        field.SetPrecision(field_precision)
    layer_input.CreateField(field)

    # Pour chaque polygones
    for i in range(0, layer_input.GetFeatureCount()):
         # Get the input Feature
         feature_input = layer_input.GetFeature(i)

         # Ajouter la valeur au nouveau champ
         feature_input.SetField(field_name, field_value)
         layer_input.SetFeature(feature_input)
         feature_input.Destroy()

    # Fermeture du fichier shape
    layer_input.SyncToDisk()
    data_source_input.Destroy()

    if debug >=2:
       print(cyan + "addNewFieldVector() : " + bold + green + "Add new field %s to file %s complete!" %(field_name, vector_input) + endC)
    return

########################################################################
# FONCTION cloneFieldDefn()                                            #
########################################################################
#   Role : Fonction qui duplique des champs
#   Paramètres en entrée :
#       src_def : le champs d'entrée à dupliqué
#   Paramètre de retour
#       dest_def : une copie du champs

def cloneFieldDefn(src_def):
    dest_def = ogr.FieldDefn(src_def.GetName(), src_def.GetType())
    dest_def.SetWidth(src_def.GetWidth())
    dest_def.SetPrecision(src_def.GetPrecision())
    return dest_def

########################################################################
# FONCTION renameFieldsVector()                                        #
########################################################################
#   Role : Fonction qui renome les champs d'un fichier vecteur
#   Paramètres en entrée :
#       vector_input : nom du fichier vecteur d'entrée
#       field_sname_list : liste des noms de champs (colonne) à mettre à renomer.
#       new_fields_name_list : valeur des nouveaux noms des champs à renomer
#       format_vector : format d'entrée du fichier vecteur. Par défaut : 'ESRI Shapefile'
#   Paramètre de retour

def renameFieldsVector(vector_input, fields_name_list, new_fields_name_list, format_vector='ESRI Shapefile'):
    if debug >=2:
       print(cyan + "renameFieldsVector() : " + endC + "renomage des noms des champs " + str(field_name_list) + " du fichier vecteur " + vector_input )

    # Récuperation du driver pour le format shape du fichier d'entrée
    driver_input = ogr.GetDriverByName(format_vector)

    # Ouverture du fichier shape en écriture
    data_source_input = driver_input.Open(vector_input, 1)
    if data_source_input is None:
        print(cyan + "renameFieldsVector() : " + bold + red + "Impossible d'ouvrir le fichier shape : " + vector_input + endC, file=sys.stderr)
        return -1.0

    # Récupérer la couche contenant les éléments
    layer_input = data_source_input.GetLayer(0)
    layer_definition = layer_input.GetLayerDefn()


    # Vérification de l'existence de chaque nom de colonne
    for index_field_name in range(len(fields_name_list)):
        field_name = fields_name_list[index_field_name]
        new_field_name = new_fields_name_list[index_field_name]
        id_field = layer_definition.GetFieldIndex(field_name)

        if id_field == -1 :
            print(cyan + "renameFieldsVector() : " + bold + yellow + "Attention le champs n'existe pas, il ne sera pas renomer : " + field_name + endC)
        else :
            # Rename Field
            src_field = layer_definition.GetFieldDefn(id_field)
            field_def = cloneFieldDefn(src_field)
            field_def.SetName(new_field_name)
            field_def.SetType(src_field.GetType())
            layer_input.AlterFieldDefn(id_field, field_def, ogr.ALTER_NAME_FLAG)

    # Fermeture du fichier shape
    layer_input.SyncToDisk()
    data_source_input.Destroy()

    if debug >=2:
       print(cyan + "renameFieldsVector() : " + bold + green + "Les noms des champ ont été renomer pour fichier vecteur " + vector_input + endC)

    return 0

#########################################################################
# FONCTION deleteFieldsVector()                                         #
#########################################################################
#   Role : Cette fonction permet de supprimer des champs d'un fichier vecteur
#          Les champs sont définis dans une liste
#   Parametres :
#       vector_input : fichier vecteur en entrée
#       vector_output : fichier vecteur en sortie
#       fields_name_list : liste des noms des champs à supprimer
#       format_vector : format du fichier vecteur (par defaut 'ESRI Shapefile')

def deleteFieldsVector(vector_input, vector_output, fields_name_list, format_vector='ESRI Shapefile') :

    if debug >=2:
        print(cyan + "deleteFieldsVector() : " + endC + "Suppression de champs du vecteur : " + str(vector_input))

    # Recuperation du driver pour le format shape fichier entrée
    driver = ogr.GetDriverByName(format_vector)

    # Ouverture du fichier shape en lecture-ecriture
    data_source_input = driver.Open(vector_input, 1) # 1 means writeable.
    if data_source_input is None:
        print(cyan + "deleteFieldsVector() : " + bold + red + "Impossible d'ouvrir le fichier shape : " + vector_input + endC, file=sys.stderr)
        sys.exit(1) # exit with an error code

    # Recuperer la couche (une couche contient les polygones)
    layer_input = data_source_input.GetLayer(0)

    # Vérification de l'existence de la colonne col
    layer_definition = layer_input.GetLayerDefn() # GetLayerDefn => returns the field names of the user defined (created) fields
    for field_name in fields_name_list:
        id_field = layer_definition.GetFieldIndex(field_name)

        if id_field == -1 :
            print(cyan + "deleteFieldsVector() : " + bold + yellow + "Attention le champs n'existe pas, il ne sera pas supprimer : " + field_name + endC)

    # Récupération des cractéristiques du fichier en entrée (type de géométrie, projection...)
    feature_input = layer_input.GetNextFeature()

    if feature_input is None:  # Cas où il n'y a aucun polygone à simplifier
        return

    geometry = feature_input.GetGeometryRef()
    geomType = geometry.GetGeometryType()

    # Creation du fichier de sortie
    #------------------------------
    if os.path.exists(vector_output):
        driver.DeleteDataSource(vector_output)

    try:
        # Création du fichier Datasource
        data_source_output = driver.CreateDataSource(vector_output)
    except:
        print(cyan + "deleteFieldsVector() : " + endC + bold + red + "Could not create output file : " + str(vector_output) + endC, file=sys.stderr)
        sys.exit(1)

    # Création du fichier "couche" avec les mêmes caractéristiques que celui du fichier en entrée
    layer_output = data_source_output.CreateLayer(os.path.splitext(os.path.basename(vector_output))[0], srs=layer_input.GetSpatialRef(), geom_type=geomType)
    if layer_output is None:
        print(cyan + "deleteFieldsVector() : " + endC + bold + red + "Could not create layer in output file." + endC)
        sys.exit(1)

    # Création du modèle
    defn_layer_output = layer_output.GetLayerDefn()

    # Ajouter les champs qui ne sont pas dans la liste de suppression du fichier de sortie
    defn_layer_input = layer_input.GetLayerDefn()
    nb_fields = defn_layer_input.GetFieldCount()
    for i in range(0, nb_fields):
        field = defn_layer_input.GetFieldDefn(i)
        field_name = field.GetName()
        if field_name not in fields_name_list:
            layer_output.CreateField(field)

    # Initialisation des ID des éléments de la couche
    featureID = 0

    # Pour chaque polygones
    for i in range(0, layer_input.GetFeatureCount()):
        # Get the input Feature
        feature_input = layer_input.GetFeature(i)

        # Récupération de la géométrie de l'éléments
        geometry = feature_input.GetGeometryRef()

        # Assignation du modèle de "couche" un nouvel élément (copie de l'élement d'origine)
        feature_output = ogr.Feature(defn_layer_output)
        # Assignation de la géométrie à ce nouvel élément
        feature_output.SetGeometry(geometry)
        # Assignation d'un numéro de FID à ce nouvel élément
        feature_output.SetFID(featureID)

        # Pour tous les Champs
        k=0
        for j in range(0, nb_fields):

            field = feature_input.GetFieldDefnRef(j)
            field_name = field.GetName()

            if field_name not in fields_name_list:
                field_value = feature_input.GetFieldAsString(j)
                feature_output.SetField(k, field_value)
                k+=1

        # Création de ce nouvel élément
        layer_output.CreateFeature(feature_output)

        # Fermeture des feature d'netrée et de sortie
        feature_output.Destroy()
        feature_input.Destroy()
        feature_input = layer_input.GetNextFeature()
        featureID += 1

    #------------------------------

    data_source_input.Destroy()
    data_source_output.Destroy()

    if debug >=2:
       print(cyan + "deleteFieldsVector() : " + bold + green + "Delete fields %s to file %s complete!" %(fields_name_list, vector_input) + endC)
    return

#########################################################################
# FONCTION readVectorFilePoints()                                       #
#########################################################################
#   Role : Fonction qui retourne la liste des coordonnées d'un fichier shapes de points
#   Paramètres en entrée :
#       vector_input : nom du fichier vecteur d'entrée (contenant uniquement des géometries points)
#       names_column_point_list : Liste des attributs a récuperer avec le point
#       format_vector : format d'entrée du fichier vecteur. Par default : 'ESRI Shapefile'

def readVectorFilePoints(vector_input, names_column_point_list=[], format_vector='ESRI Shapefile'):
    # Variable de retour dico liste de points
    points_coordinates_dico = {}

    if debug >=2:
        print(cyan + "readVectorFilePoints() : " + endC + "Lecture des points du fichier : " + str(vector_input))

    # Recuperation du driver pour le format shape fichier entrée
    driver_input = ogr.GetDriverByName(format_vector)

    # Ouverture du fichier shape en lecture
    data_source_input = driver_input.Open(vector_input, 0) # 0 means read-only.
    if data_source_input is None:
        print(cyan + "readVectorFilePoints() : " + bold + red + "Impossible d'ouvrir le fichier shape : " + vector_input + endC, file=sys.stderr)
        return points_coordinates_dico

    # Recuperer la couche (une couche contient les points)
    layer_input = data_source_input.GetLayer(0)

    # Pour chaque points du fichier
    index_point = 0
    for i in range(0, layer_input.GetFeatureCount()):
         # Get the input Feature
         feature_input = layer_input.GetFeature(i)

         # Si le feature est de type geometrie point
         geometry = feature_input.GetGeometryRef()
         if (not geometry is None) and (geometry.GetGeometryName() == 'POINT'):
             coor_x = geometry.GetX()
             coor_y = geometry.GetY()
             points_coordinates_dico[index_point] = [coor_x, coor_y]
             attribute_values_point_dico = {}
             for column_name in names_column_point_list :
                 value = feature_input.GetFieldAsString(column_name)
                 attribute_values_point_dico[column_name] = value
             points_coordinates_dico[index_point].append(attribute_values_point_dico)
             index_point+=1

    # Fermeture du fichier shape
    data_source_input.Destroy()

    if debug >=2:
        print(cyan + "readVectorFilePoints() : " + bold + green + "Recuperation des coordonnées des points du fichier : " + str(vector_input) + endC)
    return points_coordinates_dico

#########################################################################
# FONCTION readVectorFileLinesExtractTeminalsPoints()                   #
#########################################################################
#   Role : Fonction qui retourne la liste des coordonnées points début et fin d'un fichier shapes de lignes
#   Paramètres en entrée :
#       vector_input : nom du fichier vecteur d'entrée (contenant uniquement des géometries points)
#       names_column_start_point_list : Liste des attributs a récuperer avec le point de début
#       names_column_end_point_list : Liste des attributs a récuperer avec le point de fin
#       format_vector : format d'entrée du fichier vecteur. Par default : 'ESRI Shapefile'

def readVectorFileLinesExtractTeminalsPoints(vector_input, names_column_start_point_list=[], names_column_end_point_list=[], format_vector='ESRI Shapefile'):
    # Variable de retour dico liste de points
    points_coordinates_dico = {}

    if debug >=2:
        print(cyan + "readVectorFileLinesExtractTeminalsPoints() : " + endC + "Lecture des lignes du fichier : " + str(vector_input))

    # Recuperation du driver pour le format shape fichier entrée
    driver_input = ogr.GetDriverByName(format_vector)

    # Ouverture du fichier shape en lecture
    data_source_input = driver_input.Open(vector_input, 0) # 0 means read-only.
    if data_source_input is None:
        print(cyan + "readVectorFileLinesExtractTeminalsPoints() : " + bold + red + "Impossible d'ouvrir le fichier shape : " + vector_input + endC, file=sys.stderr)
        return points_coordinates_dico

    # Recuperer la couche (une couche contient les lignes)
    layer_input = data_source_input.GetLayer(0)

    # Pour chaque lignes du fichier
    index_line = 0
    for i in range(0, layer_input.GetFeatureCount()):
         # Get the input Feature
         feature_input = layer_input.GetFeature(i)

         # Si le feature est de type geometrie point
         geometry = feature_input.GetGeometryRef()
         if (not geometry is None) and ((geometry.GetGeometryName() == 'LINESTRING')):

             start_coor_x = geometry.GetX(0)
             start_coor_y = geometry.GetY(0)
             end_coor_x = geometry.GetX(geometry.GetPointCount() - 1)
             end_coor_y = geometry.GetY(geometry.GetPointCount() - 1)

             if debug >= 4:
                print("start_coor_x = " + str(start_coor_x))
                print("start_coor_y = " + str(start_coor_y))
                print("end_coor_x = " + str(end_coor_x))
                print("end_coor_y = " + str(end_coor_y))

             attribute_values_start_point_dico = {}
             points_coordinates_dico[index_line] = [start_coor_x, start_coor_y]
             for column_name in names_column_start_point_list :
                 value = feature_input.GetFieldAsString(column_name)
                 attribute_values_start_point_dico[column_name] = value
             points_coordinates_dico[index_line].append(attribute_values_start_point_dico)

             attribute_values_end_point_dico = {}
             points_coordinates_dico[index_line + 1] = [end_coor_x, end_coor_y]
             for column_name in names_column_end_point_list :
                 value = feature_input.GetFieldAsString(column_name)
                 attribute_values_end_point_dico[column_name] = value
             points_coordinates_dico[index_line + 1].append(attribute_values_end_point_dico)

             index_line+=2

    # Fermeture du fichier shape
    data_source_input.Destroy()

    if debug >=2:
        print(cyan + "readVectorFileLinesExtractTeminalsPoints() : " + bold + green + "Recuperation des coordonnées des points du fichier : " + str(vector_input) + endC)
    return points_coordinates_dico

#########################################################################
# FONCTION getAverageAreaClass()                                        #
#########################################################################
#   Role : Fonction qui retourne la valeur moyenne les surfaces de polygones d'une même classe
#   Paramètres en entrée :
#       vector_input : nom du fichier vecteur d'entrée
#       col : nom du champs (colonne) à regarder
#       class_id : valeur du champs pour identifier le polygone
#       format_vector : format d'entrée du fichier vecteur. Par default : 'ESRI Shapefile'

def getAverageAreaClass(vector_input, col, class_id, format_vector='ESRI Shapefile'):
    # Variable de retour
    sum_area = 0.0
    compt_class = 0
    class_list =[]

    if debug >=2:
        print(cyan + "getAverageAreaClass() : " + endC + "Lecture de la surface des polygones de l'image : " + str(vector_input))

    # Recuperation du driver pour le format shape fichier entrée
    driver_input = ogr.GetDriverByName(format_vector)

    # Ouverture du fichier shape en lecture
    data_source_input = driver_input.Open(vector_input, 0) # 0 means read-only.
    if data_source_input is None:
        print(cyan + "getAverageAreaClass() : " + bold + red + "Impossible d'ouvrir le fichier shape : " + vector_input + endC, file=sys.stderr)
        return -1.0

    # Recuperer la couche (une couche contient les polygones)
    layer_input = data_source_input.GetLayer(0)

    # Recuperer le nombre de champs du fichier d'entrée
    defn_layer_input = layer_input.GetLayerDefn()
    nb_fields = defn_layer_input.GetFieldCount()

    # Pour chaque polygones
    for i in range(0, layer_input.GetFeatureCount()):
         # Get the input Feature
         feature_input = layer_input.GetFeature(i)

         # Si le polygone correspond au polygone rechercher
         field_label = feature_input.GetFieldAsString(col)
         ident_class = int(int(field_label) / 100) * 100
         if str(ident_class) == str(class_id) :
             # Get polygon area
             geometry = feature_input.GetGeometryRef()
             if not geometry is None :
                 sum_area += geometry.GetArea()
                 if not field_label in class_list :
                     class_list.append(field_label)
                     compt_class += 1

    # Fermeture du fichier shape
    data_source_input.Destroy()
    average_area = 0.0
    if compt_class != 0 :
        average_area = sum_area/compt_class

    if debug >=2:
        print(cyan + "getAverageAreaClass() : " + bold + green + "Recuperation de la surface polygone du %s fichier, surface = %f" %(vector_input, average_area) + endC)
    return average_area

#########################################################################
# FONCTION roundHoldVector()                                            #
#########################################################################
#   Role : Redefinir un vecteur avec une emprise correspondant au valeur d'emprise xmin, xmax, ymin, ymax données
#   Paramètres :
#       vector_input : fichier shape d'origine
#       vector_output :  fichier shape avec emprise arrondie
#       round_xmin : L'emprise à corrigée de sortie coordonnée xmin
#       round_xmax: L'emprise à corrigée de sortie coordonnée xmax
#       round_ymin: L'emprise à corrigée de sortie coordonnée ymin
#       round_ymax : L'emprise à corrigée de sortie coordonnée ymax
#       format_vector : format du fichier vecteur, default : ESRI Shapefile

def roundHoldVector(vector_input, vector_output, round_xmin, round_xmax, round_ymin, round_ymax, format_vector='ESRI Shapefile'):

    if debug >=2:
        print(cyan + "roundHoldVector() : " + endC + "Arrondi de l'emprise géométrie du vecteur : " + str(vector_input))

    # Lecture du fichier en entrée
    data_source_input = ogr.Open(vector_input)  # Lecture du fichier en entrée
    if data_source_input is None:               # Cas où le fichier est vide
        return

    layer_input = data_source_input.GetLayer()  # Récupération de la couche en entrée
    name_layer_input = layer_input.GetName()

    extent_input = layer_input.GetExtent() # Recuperer l'emprise du vecteur d'entrée
    empr_xmin = extent_input[0]
    empr_xmax = extent_input[1]
    empr_ymin = extent_input[2]
    empr_ymax = extent_input[3]

    # Récupération du driver
    driver = ogr.GetDriverByName(format_vector)

    round_xmin_str = "%.1f" %(round_xmin)
    round_xmax_str = "%.1f" %(round_xmax)
    round_ymin_str = "%.1f" %(round_ymin)
    round_ymax_str = "%.1f" %(round_ymax)

    empr_xmin_str = "%.9f" %(empr_xmin)
    empr_xmax_str = "%.9f" %(empr_xmax)
    empr_ymin_str = "%.8f" %(empr_ymin)
    empr_ymax_str = "%.8f" %(empr_ymax)

    if debug >=5:
        print("round_xmin_str : " + round_xmin_str)
        print("round_xmax_str : " + round_xmax_str)
        print("round_ymin_str : " + round_ymin_str)
        print("round_ymax_str : " + round_ymax_str)

        print("empr_xmin_str : " + empr_xmin_str)
        print("empr_xmax_str : " + empr_xmax_str)
        print("empr_ymin_str : " + empr_ymin_str)
        print("empr_ymax_str : " + empr_ymax_str)

    # CREATION DU FICHIER DE SORTIE

    # Assignation du système de projection du fichier en sortie
    # Recupération du srs de la couche en entrée
    output_srs=layer_input.GetSpatialRef()

    # Verification si le le fichier de sortie existe déjà (si oui le supprimer)
    if os.path.exists(vector_output):
        driver.DeleteDataSource(vector_output)

    # Création du fichier "DataSource"
    data_source_output = driver.CreateDataSource(vector_output)

    layer_output = data_source_output.CreateLayer(name_layer_input, output_srs, geom_type=ogr.wkbPolygon) # Création du fichier "couche"(nom,projection, type de géométrie)
    defn_layer_output = layer_output.GetLayerDefn()                                                    # Creation du modèle d'"éléments" à partir des caractéristiques de la couche (type de géométrie : polygone...)

    # Ajout des champs du fichier d'entrée au fichier de sortie
    defn_layer_input = layer_input.GetLayerDefn()
    nb_fields = defn_layer_input.GetFieldCount()
    for i in range(0, nb_fields):
        field_defn = defn_layer_input.GetFieldDefn(i)
        layer_output.CreateField(field_defn)

    # Réinitialiser la lecture des géométries
    layer_input.ResetReading()

    # Parcours des éléments présents dans la couche du fichier d'origine
    for feature_input in layer_input:
        # Récupération de la géométrie d'un élément (polygone)
        geometry = feature_input.GetGeometryRef()
        if not geometry is None :

            # Création de l'élément (du polygone) de sortie selon le modèle
            feature_output = ogr.Feature(defn_layer_output)

            # Pour tous les Champs
            for j in range(0, nb_fields):
                field_label = feature_input.GetFieldAsString(j)
                feature_output.SetField(j, field_label)

            poly_wkt_in = geometry.ExportToWkt()

            # Control et nettoyage de la géometrie
            poly_wkt_tmp1 = poly_wkt_in.replace(empr_xmin_str, round_xmin_str)
            poly_wkt_tmp2 = poly_wkt_tmp1.replace(empr_xmax_str, round_xmax_str)
            poly_wkt_tmp3 = poly_wkt_tmp2.replace(empr_ymin_str, round_ymin_str)
            poly_wkt_out = poly_wkt_tmp3.replace(empr_ymax_str, round_ymax_str)

            if debug >=5:
                print("poly_wkt_in : ")
                print(poly_wkt_in)
                print("poly_wkt_out : ")
                print(poly_wkt_out)

            geom_out = ogr.CreateGeometryFromWkt(poly_wkt_out)

            # Assignation de la géométrie nettoyée à l'élément de sortie
            feature_output.SetGeometry(geom_out)

            # Création de l'élement de sortie dans la couche de sortie
            layer_output.CreateFeature(feature_output)

            # Femeture
            feature_output.Destroy()
            feature_input.Destroy()

    ##########################################################

    layer_output.SyncToDisk()
    data_source_input.Destroy()
    data_source_output.Destroy()

    if debug >=2:
        print(cyan + "roundHoldVector() : " + endC + "Fichier vecteur arrondi : " + str(vector_output))
    return

#########################################################################
# FONCTION simplifyVector()                                             #
#########################################################################
#   Role : Simplifier ou lisser la géométrie d'une couche vecteur
#   Paramètres :
#       vector_input : fichier shape d'origine
#       vector_output :  fichier shape simplifié
#       tolerance : indice de lissage en float : entre 2.0 et 0.05 pour un shape d'origine très pixelisé
#       format_vector : format du fichier vecteur

def simplifyVector(vector_input ,vector_output, tolerance, format_vector='ESRI Shapefile'):

    if debug >=2:
        print(cyan + "simplifyVector() : " + endC + "Simplification de la géométrie d'une couche vecteur : " + str(vector_input))

    # Lecture du fichier en entrée
    driver = ogr.GetDriverByName(format_vector)
    data_source_input = driver.Open(vector_input, 0)

    if data_source_input is None:
        print(cyan + "simplifyVector() : " + endC + "Could not open file : " + str(vector_input))
        sys.exit(1)

    # Récupération des cractéristiques du fichier en entrée (type de géométrie, projection...)
    layer_input = data_source_input.GetLayer()
    name_layer_input = layer_input.GetName()
    feature_input = layer_input.GetNextFeature()

    if feature_input is None:  # Cas où il n'y a aucun polygone à simplifier
        return

    geometry = feature_input.GetGeometryRef()
    geomType = geometry.GetGeometryType()

    ########CREATION DU FICHIER DE SORTIE ############
    if os.path.exists(vector_output):
        driver.DeleteDataSource(vector_output)

    try:
        # Création du fichier Datasource
        data_source_output = driver.CreateDataSource(vector_output)
    except:
        print(cyan + "simplifyVector() : " + endC + bold + red + "Could not create output file : " + str(vector_output) + endC, file=sys.stderr)
        sys.exit(1)

    # Création du fichier "couche" avec les mêmes caractéristiques que celui du fichier en entrée
    layer_output = data_source_output.CreateLayer(name_layer_input, srs=layer_input.GetSpatialRef(), geom_type=geomType)
    if layer_output is None:
        print(cyan + "simplifyVector() : " + endC + bold + red + "Could not create layer for simplify in output file." + endC, file=sys.stderr)
        sys.exit(1)

    # Création du modèle
    defn_layer_output = layer_output.GetLayerDefn()

    # Initialisation des ID des éléments de la couche
    featureID = 0

    # Ajouter les champs du fichier d'entrée au fichier de sortie
    defn_layer_input = layer_input.GetLayerDefn()
    nb_fields = defn_layer_input.GetFieldCount()
    for i in range(0, nb_fields):
        field_defn = defn_layer_input.GetFieldDefn(i)
        layer_output.CreateField(field_defn)

    # Simplifie la geometrie et ajoute au fichier de sortie

    # Réinitialiser la lecture des géométries
    layer_input.ResetReading()
    feature_input = layer_input.GetNextFeature()

    # Parcours des éléments du fichier en entrée
    while feature_input:
        # Récupération de la géométrie de l'éléments
        geometry = feature_input.GetGeometryRef()
        # Simplification de loa géométrie de l'élément
        simplifiedGeom = geometry.SimplifyPreserveTopology(tolerance)

        if not simplifiedGeom is None :
            try:
                # Assignation du modèle de "couche" un nouvel élément (copie de l'élement d'origine)
                feature_output = ogr.Feature(defn_layer_output)
                # Assignation de la géométrie simplifie à ce nouvel élément
                feature_output.SetGeometry(simplifiedGeom)
                # Assignation d'un numéro de FID à ce nouvel élément
                feature_output.SetFID(featureID)

                # Pour tous les Champs
                for j in range(0, nb_fields):
                    field_label = feature_input.GetFieldAsString(j)
                    feature_output.SetField(j, field_label)

                # Création de ce nouvel élément
                layer_output.CreateFeature(feature_output)
            except:
                print(cyan + "simplifyVector() : " + endC + bold + red + "Error performing simplify." + endC, file=sys.stderr)

        # Fermeture des feature d'entrée et de sortie
        feature_output.Destroy()
        feature_input.Destroy()
        feature_input = layer_input.GetNextFeature()
        featureID += 1

    # Fermeture des fichiers
    layer_output.SyncToDisk()
    data_source_input.Destroy()
    data_source_output.Destroy()

    if debug >=2:
        print(cyan + "simplifyVector() : " + endC + "Fichier vecteur simplifie : " + str(vector_output))
    return


#########################################################################
# FONCTION bufferVector()                                               #
#########################################################################
#   Role : Créer un tampon d'une distance donné autour des entités d'un fichier shape
#   Paramètres :
#      vector_input : fichier shape d'origine
#      vector_output : fichier shape comprenent le buffer
#      buffer_dist : taille du buffer en float
#      col_name_buf : nom de la colonne contenant la valeur du buffer
#      fact_buf : facteur de la valeur du buffer par defaut à 1
#      quadsecs : indice de lissage en entier : entre 1 et 30 (max) pour un shape d'origine très pixelisé
#      format_vector : format du fichier vecteur

def bufferVector(vector_input, vector_output, buffer_dist, col_name_buf = "", fact_buf=1.0, quadsecs=10, format_vector='ESRI Shapefile'):

    if debug >=2:
        print(cyan + "bufferVector() : " + endC + "Creation d'un buffer de " + str(buffer_dist) + " autour du fichier " + str(vector_input))

    data_source_input = ogr.Open(vector_input)  # Lecture du fichier en entrée

    if data_source_input is None:               # Cas où le fichier est vide
        return

    layer_input = data_source_input.GetLayer()  # Récupération de la couche en entrée
    name_layer_input = layer_input.GetName()

    # Récupération du driver
    driver = ogr.GetDriverByName(format_vector)

    # CREATION DU FICHIER DE SORTIE

    # Assignation du système de projection du fichier en sortie
    # Recupération du srs de la couche en entrée
    output_srs=layer_input.GetSpatialRef()

    # Verification si le le fichier de sortie existe déjà (si oui le supprimer)
    if os.path.exists(vector_output):
        driver.DeleteDataSource(vector_output)
    data_source_output = driver.CreateDataSource(vector_output)                                          # Création du fichier "DataSource"
    layer_output = data_source_output.CreateLayer(name_layer_input, output_srs, geom_type=ogr.wkbPolygon) # Création du fichier "couche"(nom,projection, type de géométrie)
    defn_layer_output = layer_output.GetLayerDefn()                                                    # Creation du modèle d'"éléments" à partir des caractéristiques de la couche (type de géométrie : polygone...)

    # Ajout des champs du fichier d'entrée au fichier de sortie
    defn_layer_input = layer_input.GetLayerDefn()
    nb_fields = defn_layer_input.GetFieldCount()
    for i in range(0, nb_fields):
        field_defn = defn_layer_input.GetFieldDefn(i)
        layer_output.CreateField(field_defn)

    # Réinitialiser la lecture des géométries
    layer_input.ResetReading()

    # Parcours des éléments présents dans la couche du fichier d'origine
    for feature_input in layer_input:
        # Récupération de la géométrie d'un élément (polygone)
        geometry = feature_input.GetGeometryRef()

        if not geometry is None :

            # Création de l'élément (du polygone) de sortie selon le modèle
            feature_output = ogr.Feature(defn_layer_output)
            # Pour tous les Champs
            for j in range(0, nb_fields):
                field_label = feature_input.GetFieldAsString(j)
                feature_output.SetField(j, field_label)

            # Recuperer la valeur du buffer
            if col_name_buf != "" :
                value =  feature_output.GetFieldAsDouble(col_name_buf)
                size_buf = float(value)
                if size_buf == 0.0 :
                    size_buf = float(buffer_dist)
            else :
                size_buf = float(buffer_dist)

            # Transformation de la géométrie précédente en une géométrie "bufferisée"
            geomBuffer = geometry.Buffer(size_buf * fact_buf, int(quadsecs))

            # Assignation de la géométrie bufferisée à l'élément de sortie
            feature_output.SetGeometry(geomBuffer)
            # Création de l'élement de sortie dans la couche de sortie
            layer_output.CreateFeature(feature_output)
            # Femeture
            feature_output.Destroy()
            feature_input.Destroy()

    # Fermeture des fichiers
    layer_output.SyncToDisk()
    data_source_input.Destroy()
    data_source_output.Destroy()

    if debug >=2:
        print(cyan + "bufferVector() : " + endC + "Le fichier vecteur " + str(vector_output)  + " a ete bufferise")
    return


#########################################################################
# FONCTION cleanRingVector()                                            #
#########################################################################
#   Role : Nettoye les polygones d'un fichier shape contenant des trous (ring)
#   Paramètres :
#      vector_input : fichier shape d'origine
#      vector_output : fichier shape nettoyé
#      format_vector : format du fichier vecteur

def cleanRingVector(vector_input, vector_output, format_vector='ESRI Shapefile'):

    if debug >=2:
        print(cyan + "cleanRingVector() : " + endC + "Nettoyage des rings du fichier vecteur : " + str(vector_input))

    data_source_input = ogr.Open(vector_input)  # Lecture du fichier en entrée
    if data_source_input is None:               # Cas où le fichier est vide
        return

    layer_input = data_source_input.GetLayer()  # Récupération de la couche en entrée
    name_layer_input = layer_input.GetName()

    # Récupération du driver
    driver = ogr.GetDriverByName(format_vector)

    # CREATION DU FICHIER DE SORTIE

    # Assignation du système de projection du fichier en sortie
    # Recupération du srs de la couche en entrée
    output_srs=layer_input.GetSpatialRef()

    # Verification si le le fichier de sortie existe déjà (si oui le supprimer)
    if os.path.exists(vector_output):
        driver.DeleteDataSource(vector_output)

    # Création du fichier "DataSource"
    data_source_output = driver.CreateDataSource(vector_output)

    layer_output = data_source_output.CreateLayer(name_layer_input, output_srs, geom_type=ogr.wkbPolygon) # Création du fichier "couche"(nom,projection, type de géométrie)
    defn_layer_output = layer_output.GetLayerDefn()                                              # Creation du modèle d'"éléments" à partir des caractéristiques de la couche (type de géométrie : polygone...)

    # Ajout des champs du fichier d'entrée au fichier de sortie
    defn_layer_input = layer_input.GetLayerDefn()
    nb_fields = defn_layer_input.GetFieldCount()
    for i in range(0, nb_fields):
        field_defn = defn_layer_input.GetFieldDefn(i)
        layer_output.CreateField(field_defn)

    # Réinitialiser la lecture des géométries
    layer_input.ResetReading()

    # Parcours des éléments présents dans la couche du fichier d'origine
    for feature_input in layer_input:
        # Récupération de la géométrie d'un élément (polygone)
        geometry = feature_input.GetGeometryRef()
        if not geometry is None :

            # Création de l'élément (du polygone) de sortie selon le modèle
            feature_output = ogr.Feature(defn_layer_output)

            # Pour tous les Champs
            for j in range(0, nb_fields):
                field_label = feature_input.GetFieldAsString(j)
                feature_output.SetField(j, field_label)

            # Transformation de la géométrie d'entré en une géométrie "nettoyée"
            for geom_part in geometry:
                geom_out = ogr.Geometry(ogr.wkbPolygon)
                geom_out.AddGeometry(geom_part)
                break

            # Assignation de la géométrie nettoyée à l'élément de sortie
            feature_output.SetGeometry(geom_out)

            # Création de l'élement de sortie dans la couche de sortie
            layer_output.CreateFeature(feature_output)

            # Femeture
            feature_output.Destroy()
            feature_input.Destroy()

    # Fermeture des fichiers
    layer_output.SyncToDisk()
    data_source_input.Destroy()
    data_source_output.Destroy()

    if debug >=2:
        print(cyan + "cleanRingVector() : " + endC + "Le fichier vecteur " + str(vector_output)  + " a ete nettyoyé")
    return

#########################################################################
# FONCTION cleanMiniAreaPolygons()                                      #
#########################################################################
#   Role : Fonction qui supprime les polygones de surfaces minimales d'un shapefile
#   Paramètres :
#       vector_input : nom du fichier vecteur d'entrée
#       vector_output : nom du fichier vecteur de sortie
#       min_size_area : valeur de la taille minimale de surface des polygones à nettoyer
#       col : nom du champs (colonne) à regarder
#       format_vector : format d'entrée et de sortie des fichiers vecteurs. Par default : 'ESRI Shapefile'
#  Exemple d'utilisation: cleanMiniAreaPolygons("vectorInput.shape","vectorOutput.shape",0.45,'ESRI Shapefile')

def cleanMiniAreaPolygons(vector_input, vector_output, min_size_area, col='id', format_vector='ESRI Shapefile'):

    if debug >=2:
        print(cyan + "cleanMiniAreaPolygons() : " + endC + "Supression des polygones de surfaces minimales du vecteur " + vector_input)

    # Initialisation du dictionaire de surface par classe
    size_area_by_class_dico = {}

    # Recuperation du driver pour le format shape fichier entrée
    driver_input = ogr.GetDriverByName(format_vector)

    # Ouverture du fichier shape en lecture
    data_source_input = driver_input.Open(vector_input, 0) # 0 means read-only. 1 means writeable.
    if data_source_input is None:
        print(cyan + "cleanMiniAreaPolygons() : " + bold + yellow + " Fichier non traite (ouverture impossible): " + vector_input + endC)
        return size_area_by_class_dico
        # Précedement à la place du return : sys.exit(1) # exit with an error code

    # Récupération des cractéristiques du fichier en entrée (type de géométrie, projection...)
    layer_input = data_source_input.GetLayer()
    feature_input = layer_input.GetNextFeature()

    # Cas ou le fichier est vide on recopie juste le fichier d'entrée
    if feature_input is None:
        print(cyan + "cleanMiniAreaPolygons() : " + bold + yellow  + "Attention! le fichier d'entrée est vide donc non traite il est juste recopier en sortie : " + str(vector_input) + endC)
        # Copy vector_output
        driver_input.CopyDataSource(data_source_input,vector_output)
        data_source_input.Destroy()
        return size_area_by_class_dico

    # Lecture des infos de la couche
    name_layer_input = layer_input.GetName()
    output_srs = layer_input.GetSpatialRef ()
    geom_type_input = layer_input.GetGeomType()

    # Recuperation du driver pour le format shape fichier de sortie
    driver_output = ogr.GetDriverByName(format_vector)

    # Si le fichier destination existe deja on l ecrase
    if os.path.exists(vector_output) :
        print(cyan + "cleanMiniAreaPolygons() : " + bold + red +"Le fichier shape  existe deja il sera ecrase : " + vector_output + endC)
        driver_output.DeleteDataSource(vector_output)

    # Creation du fichier shape de sortie en écriture
    data_source_output = driver_output.CreateDataSource(vector_output)
    layer_output = data_source_output.CreateLayer(name_layer_input, output_srs, geom_type=geom_type_input)

    # Ajouter les champs du fichier d'entrée au fichier de sortie
    defn_layer_input = layer_input.GetLayerDefn()
    for i in range(0, defn_layer_input.GetFieldCount()):
        field_defn = defn_layer_input.GetFieldDefn(i)
        layer_output.CreateField(field_defn)

    # Recupère le output Layer's Feature Definition
    defn_layer_output = layer_output.GetLayerDefn()

    # Comptage du nombre de polygones sources
    num_features = layer_input.GetFeatureCount()

    if debug >= 1:
        print(cyan + "cleanMiniAreaPolygons() : " +  bold + green + "Nombre de polygones sources : " + str(num_features) + endC)

    # Réinitialiser la lecture des géométries
    layer_input.ResetReading()

    # Pour chaque polygone
    # Add features to the ouput Layer
    for i in range(0, layer_input.GetFeatureCount()):

         feature_input = layer_input.GetFeature(i)  # Get the input Feature
         geometry = feature_input.GetGeometryRef() # Calculating the actual area

         # Si la geometry est non nulle
         if not geometry is None :
            idfeat = feature_input.GetFID()
            polygonArea = geometry.GetArea()

            # Si la surface est superieur a min_size_area, on copie le polygone
            if polygonArea >= min_size_area :
                if debug >= 4:
                    print('surface %s superieur a %s'%(str(polygonArea) , str(min_size_area)))
                    print("id conserver", idfeat)

                # Add new feature to output Layer
                layer_output.CreateFeature(feature_input)

                # Mettre a jour information du dictionaire surface total par classe
                if col != "":
                    class_label = int(feature_input.GetFieldAsString(col))

                    if class_label not in size_area_by_class_dico :
                        size_area_by_class_dico[class_label] = polygonArea
                    else :
                        size_area_by_class_dico[class_label] += polygonArea

    # Comptage du nombre de polygones destinations
    num_features = layer_output.GetFeatureCount()
    if debug >= 1:
        print(cyan + "cleanMiniAreaPolygons() : " + bold + green + "Nombre de polygones destination : " + str(num_features) + endC)

    # Fermeture des fichiers shape
    layer_output.SyncToDisk()
    data_source_input.Destroy()
    data_source_output.Destroy()

    if debug >=2:
        print(cyan + "cleanMiniAreaPolygons() : " + bold + green + "Clean min area polygons of %s to %s complete! \n" %(vector_input, vector_output) + endC)
    return size_area_by_class_dico

#########################################################################
# FONCTION addGeometryToLayer()                                         #
#########################################################################
#   Role : Ajout d'une geometrie à une couche (feature) de sortie
#   Paramètres :
#       simpleGeometryWkb : la geometrie à ajouter au format Wkb
#       layer_output : la couche layer de sortie
#       fields_list : liste des noms de champs à ajouter
#       values_list : liste de valeurs de champs correspondant à ajouter

def addGeometryToLayer(simpleGeometryWkb, layer_output, fields_list=[], values_list=[]):
    if len(fields_list) != len(values_list):
        print(cyan + "addGeometryToLayer() : " + bold + red  + "La liste de valeurs et celle des champs ne font pas la même taille" + endC, file=sys.stderr)
        sys.exit(1)
    featureDefn = layer_output.GetLayerDefn()
    geometry = ogr.CreateGeometryFromWkb(simpleGeometryWkb)
    out_feat = ogr.Feature(featureDefn)
    out_feat.SetGeometry(geometry)
    for i in range(len(fields_list)):
        out_feat.SetField(fields_list[i],values_list[i])
    layer_output.CreateFeature(out_feat)
    return

#########################################################################
# FONCTION addFields()                                                  #
#########################################################################
#   Role : Ajouter les champs de la couche (layer) d'entrée à la couche (layer) de sortie
#   Paramètres :
#       layer_input : la couche layer d'entrée
#       layer_output : la couche layer de sortie
#       field_name : le nom du champs à ajouter

def addFields(layer_input, layer_output, field_name = ""):
    defn_layer_input = layer_input.GetLayerDefn()
    for i in range(0, defn_layer_input.GetFieldCount()):
        field_defn = defn_layer_input.GetFieldDefn(i)
        if (field_name == "") or (field_name == field_defn.GetNameRef()) :
            layer_output.CreateField(field_defn)
    return

#########################################################################
# FONCTION multigeometries2geometries()                                 #
#########################################################################
#   Role : Remplacer les multi-géométries du fichier vecteur d'entrée en géométries simples
#   Paramètres :
#       vector_input : fichier shape d'origine avec des muti-géométries
#       vector_output : fichier shape avec multi-géométries transformées en géométries simples
#       fields_list : liste des champs à copier dans le fichier de sortie
#       input_geom_type : le type des multi-géométries à transformer
#       format_vector : format du fichier vecteur

def multigeometries2geometries(vector_input, vector_output, fields_list=[], input_geom_type='MULTIPOLYGON', format_vector='ESRI Shapefile'):

    if debug >=2:
        print(cyan + "multigeometries2geometries() : " + endC + "Transformation des geometries de type multi-géometrie en géometrie simple du vecteur " + vector_input)

    # Lecture du fichier en entrée
    driver = ogr.GetDriverByName(format_vector)
    data_source_input = driver.Open(vector_input, 0) # 0 means read-only. 1 means writeable.

    if data_source_input is None:
        print(cyan + "multigeometries2geometries() : " + bold + yellow  + "Fichier non traite! (ouverture impossible) : " + str(vector_input) + endC)
        return

    # Récupération des cractéristiques du fichier en entrée (type de géométrie, projection...)
    layer_input = data_source_input.GetLayer()
    feature_input = layer_input.GetNextFeature()

    # Cas ou le fichier est vide on recopie juste le fichier d'entrée
    if feature_input is None:
        print(cyan + "multigeometries2geometries() : " + bold + yellow  + "Attention! le fichier d'entrée est vide donc non traite il est juste recopier en sortie : " + str(vector_input) + endC)
        # Copy vector_output
        driver.CopyDataSource(data_source_input,vector_output)
        data_source_input.Destroy()
        return

    # Lecture des infos de la couche
    name_layer_input = layer_input.GetName()
    output_srs = layer_input.GetSpatialRef ()
    geometry = feature_input.GetGeometryRef()

    if input_geom_type == 'MULTIPOLYGON':
        output_geom_type = ogr.wkbPolygon
    elif input_geom_type == 'MULTILINESTRING':
        output_geom_type = ogr.wkbLineString
    elif input_geom_type == 'MULTIPOINT':
        output_geom_type = ogr.wkbPoint

    # Si le fichier vecteur de sortie existe on le supprime
    if os.path.exists(vector_output):
        driver.DeleteDataSource(vector_output)

    # Creation du fichier shape de sortie en écriture
    data_source_output = driver.CreateDataSource(vector_output)
    layer_output = data_source_output.CreateLayer(name_layer_input, srs=output_srs, geom_type=output_geom_type)

    # Ajout des champs du fichier d'entrée au fichier de sortie
    addFields(layer_input, layer_output)

    # Réinitialiser la lecture des géométries
    data_source_input.Destroy()
    data_source_input = driver.Open(vector_input, 0)
    layer_input = data_source_input.GetLayer()

    # Parcours de tous les polygones
    for feature_input in layer_input:
        values_list = []
        geometry = feature_input.GetGeometryRef()
        if geometry is not None :
            # Récuper la valeur du champ de classification
            for field in fields_list:
                values_list.append(feature_input.GetField(field))
            if geometry.GetGeometryName() == input_geom_type:
                for geom_part in geometry:
                    addGeometryToLayer(geom_part.ExportToWkb(), layer_output, fields_list, values_list)
            else:
                addGeometryToLayer(geometry.ExportToWkb(), layer_output, fields_list, values_list)

    # Fermeture des fichiers shape
    layer_output.SyncToDisk()
    data_source_input.Destroy()
    data_source_output.Destroy()

    if debug >=2:
        print(cyan + "multigeometries2geometries() : " + endC + "Fichier vecteur tranformé en géométries simples : " + str(vector_output))
    return


#########################################################################
# FONCTION geometries2multigeometries()                                 #
#########################################################################
#   Role : Fusionner de geometries de même valeur d'un champs donnée (ou sans condition si auccune colone n'est specifiée) du fichier vecteur d'entrée en geometries multiples
#   Paramètres :
#       vector_input : fichier vecteur d'origine avec des geometries à fusionner
#       vector_output :  fichier vecteur avec geometries simples transformées en geometries fusionnées
#       column : colonne contenant l'information de valeur à comparer. Par defaut si column est vide toutes les geometries sont fusionnés sans condition
#       format_vector : format du fichier vecteur
#   Retour : ret
def geometries2multigeometries(vector_input, vector_output, column ="", format_vector='ESRI Shapefile'):

    if debug >=2:
        print(cyan + "geometries2multigeometries() : " + endC + "Fusion des geometries de même valeur de %s du fichier %s" %(str(column), str(vector_input)))

    # Lecture du fichier en entrée
    ret = True
    driver = ogr.GetDriverByName(format_vector)
    data_source_input = driver.Open(vector_input, 0) # 0 means read-only. 1 means writeable.

    if data_source_input is None:
        print(cyan  + "geometries2multigeometries() : " + bold + red + "Could not open file : " + str(vector_input), file=sys.stderr)
        sys.exit(1)

    # Récupération des cractéristiques du fichier en entrée (type de géométrie, projection...)
    layer_input = data_source_input.GetLayer()
    name_layer_input = layer_input.GetName()
    geometryType = layer_input.GetGeomType()
    feature_input = layer_input.GetNextFeature()
    geometry_input = feature_input.GetGeometryRef()
    test_geom_input = geometry_input.GetGeometryName()
    output_srs = layer_input.GetSpatialRef()
    type_geom_output = None
    if test_geom_input == 'POLYGON' or test_geom_input == 'MULTIPOLYGON':
        type_geom_output = ogr.wkbMultiPolygon
    elif test_geom_input == 'LINESTRING' or test_geom_input == 'MULTILINESTRING':
        type_geom_output = ogr.wkbMultiLineString
    elif test_geom_input == 'POINT' or test_geom_input == 'MULTIPOINT':
        type_geom_output = ogr.wkbMultiPoint

    # Réinitialiser la lecture des géométries
    layer_input.ResetReading()

    # Si le fichier vecteur de sortie existe on le supprime
    if os.path.exists(vector_output):
        driver.DeleteDataSource(vector_output)

    # Creation du fichier shape de sortie en écriture
    data_source_output = driver.CreateDataSource(vector_output)
    layer_output = data_source_output.CreateLayer(name_layer_input, srs=output_srs, geom_type=geometryType)

    # Ajout des champs du fichier d'entrée au fichier de sortie
    defn_layer_input = layer_input.GetLayerDefn()
    nb_fields = defn_layer_input.GetFieldCount()
    for i in range(0, nb_fields):
        field_defn = defn_layer_input.GetFieldDefn(i)
        layer_output.CreateField(field_defn)

    # Créer une liste d'identificateur de valeur unique pour être en mesure de boucler à travers eux plus tard
    elements_list = []

    # Si le nom de la colonne n'est pas vide
    if column != "":
        for i in range(0, layer_input.GetFeatureCount()) :
            feature_input = layer_input.GetFeature(i)
            statefp = feature_input.GetField(column)
            elements_list.append(statefp)
        # Suppression des valeurs à None
        elements_list = set(elements_list)
        if 'None' in elements_list:
            elements_list.remove('None')
    else :
        elements_list.append("All")

    if debug >=3:
        print("Liste des valeurs des elements : " + str(elements_list))

    # Créer une liste de geometries fusionnées à écrire dans le fichier de sortie
    geometries_dico = {}
    geometries_field_dico = {}

    if debug >=3:
        print("Nombre total de geometries : " + str(layer_input.GetFeatureCount()))

    # Faites la dissolution réelle basée sur la colonne et ajouter des geometries
    # Pour chaque element à creer
    if type_geom_output is not None :
        for ident_element in elements_list :
            if debug >=4:
                print("Element = " + str(ident_element))
            geometries_dico[ident_element] = ogr.Geometry(type_geom_output)

    # Pour chaque geometrie
    for feature_input in layer_input:
        if column != "":
            ident_element = feature_input.GetField(column)
        else :
            ident_element = "All"

        geometry = feature_input.GetGeometryRef()
        if (not geometry is None) and (str(ident_element) != 'None') :
            geometry_multigeom = geometries_dico[ident_element]
            if geometry.GetGeometryType() == ogr.wkbPolygon or geometry.GetGeometryType() == ogr.wkbLineString or geometry.GetGeometryType() == ogr.wkbPoint:
                geometry_multigeom.AddGeometry(geometry)
            else:
                for geometry_part in geometry:
                    geometry_multigeom.AddGeometry(geometry_part)
            geometries_dico[ident_element] = geometry_multigeom

            # Pour tous les Champs
            field_dico = {}
            for j in range(0, nb_fields):
                field = feature_input.GetFieldDefnRef(j)
                field_name = field.GetName()
                field_value = feature_input.GetFieldAsString(j)
                field_dico[field_name] = field_value
            geometries_field_dico[ident_element] = field_dico


    # Ajout des geometries multiples au fichier de sortie
    for label_element,geometry in geometries_dico.items() :
        if debug >=4:
            print("add geometry id value : " + str(label_element))

        if geometry is not None :
            fields_list = []
            values_list = []
            if label_element is not None :
                field_dico = geometries_field_dico[label_element]
                for field_name in field_dico :
                    fields_list.append(field_name)
                    values_list.append(field_dico[field_name])
            else :
                ret = False
            addGeometryToLayer(geometry.ExportToWkb(), layer_output, fields_list, values_list)

    # Fermeture des fichiers shape
    layer_output.SyncToDisk()
    data_source_input.Destroy()
    data_source_output.Destroy()

    if debug >=2:
        print(cyan + "geometries2multigeometries() : " + endC + "Fichier vecteur geometries fusionnes : " + str(vector_output))
    return ret

#########################################################################
# FONCTION fusionNeighbourPolygonsBySameValue()                         #
#########################################################################
#   Role : Fusionner de polygones voisin de même valeur défini par un champs donnée du fichier vecteur d'entrée
#   Paramètres :
#       vector_input : fichier vecteur d'origine avec des polygones à fusionner
#       vector_output :  fichier vecteur avec polygones simples transformées en polygones fusionnées
#       column : colonne contenant l'information de valeur à comparer.
#       format_vector : format du fichier vecteur

def fusionNeighbourPolygonsBySameValue(vector_input, vector_output, column, format_vector='ESRI Shapefile'):

    if debug >=2:
        print(cyan + "fusionNeighbourPolygonsBySameValue() : " + endC + "Fusion des geometries de même valeur de %s du fichier %s" %(str(column), str(vector_input)))

    # Lecture du fichier en entrée
    driver = ogr.GetDriverByName(format_vector)
    data_source_input = driver.Open(vector_input, 0) # 0 means read-only. 1 means writeable.

    if data_source_input is None:
        print(cyan  + "fusionNeighbourPolygonsBySameValue() : " + bold + red + "Could not open file : " + str(vector_input), file=sys.stderr)
        sys.exit(1)

    # Récupération des cractéristiques du fichier en entrée (type de géométrie, projection...)
    layer_input = data_source_input.GetLayer()
    name_layer_input = layer_input.GetName()
    output_srs = layer_input.GetSpatialRef()

    # Réinitialiser la lecture des géométries
    layer_input.ResetReading()

    # Si le fichier vecteur de sortie existe on le supprime
    if os.path.exists(vector_output):
        driver.DeleteDataSource(vector_output)

    # Creation du fichier shape de sortie en écriture
    data_source_output = driver.CreateDataSource(vector_output)
    layer_output = data_source_output.CreateLayer(name_layer_input, srs=output_srs, geom_type=ogr.wkbPolygon)

    # Ajout des champs du fichier d'entrée au fichier de sortie
    defn_layer_input = layer_input.GetLayerDefn()
    nb_fields = defn_layer_input.GetFieldCount()
    for i in range(0, nb_fields):
        field_defn = defn_layer_input.GetFieldDefn(i)
        layer_output.CreateField(field_defn)

    # Créer une liste d'identificateur de valeur unique pour être en mesure de boucler à travers eux plus tard
    elements_list = []
    for i in range(0, layer_input.GetFeatureCount()) :
        feature_input = layer_input.GetFeature(i)
        statefp = feature_input.GetField(column)
        elements_list.append(statefp)
    elements_list = set(elements_list)

    # Suppression des polygones de valeur None
    if 'None' in elements_list:
        elements_list.remove('None')

    if debug >=3:
        print("Liste des valeurs des elements : " + str(elements_list))

    # Créer une liste de geometries fusionnées à écrire dans le fichier de sortie
    geometries_dico = {}
    geometries_field_dico = {}

    if debug >=3:
        print("Nombre total de polygones : " + str(layer_input.GetFeatureCount()))

    # Faites la dissolution réelle basée sur la colonne et ajouter des polygones
    # Pour chaque element
    for ident_element in elements_list :
        if debug >=4:
            print("Element = " + str(ident_element))
        geometries_dico[ident_element] = ogr.Geometry(ogr.wkbMultiPolygon)

    # Pour chaque geometrie
    for feature_input in layer_input:
        ident_element = feature_input.GetField(column)
        geometry = feature_input.GetGeometryRef()
        if (not geometry is None) and (str(ident_element) != 'None') :
            geometry_multigeom = geometries_dico[ident_element]
            if geometry.GetGeometryType() == ogr.wkbPolygon :
                geometry_multigeom.AddGeometry(geometry)
            else:
                for geometry_part in geometry:
                    geometry_multigeom.AddGeometry(geometry_part)
            geometries_dico[ident_element] = geometry_multigeom

            # Pour tous les Champs
            field_dico = {}
            for j in range(0, nb_fields):
                field = feature_input.GetFieldDefnRef(j)
                field_name = field.GetName()
                field_value = feature_input.GetFieldAsString(j)
                field_dico[field_name] = field_value
            geometries_field_dico[ident_element] = field_dico

    # Pour chaque element
    for ident_element in elements_list :
        geometry_multigeom = geometries_dico[ident_element]
        geometry_union = geometry_multigeom.UnionCascaded()
        geometries_dico[ident_element] = geometry_union

    # Ajout des geometries simple (simplifiées) au fichier de sortie
    for label_element,geometry in geometries_dico.items() :
        if debug >=4:
            print("add polygon id value : " + str(label_element))

        if geometry is not None:
            field_dico = geometries_field_dico[label_element]
            fields_list = []
            values_list = []
            for field_name in field_dico :
                fields_list.append(field_name)
                values_list.append(field_dico[field_name])
            if geometry.GetGeometryName() == 'MULTIPOLYGON' :
                for geometry_part in geometry:
                    addGeometryToLayer(geometry_part.ExportToWkb(), layer_output, fields_list, values_list)
            else:
                addGeometryToLayer(ogr.ForceToPolygon(geometry).ExportToWkb(), layer_output, fields_list, values_list)

    # Fermeture des fichiers shape
    layer_output.SyncToDisk()
    data_source_input.Destroy()
    data_source_output.Destroy()

    if debug >=2:
        print(cyan + "fusionNeighbourPolygonsBySameValue() : " + endC + "Fichier vecteur polygones fusionnes : " + str(vector_output))
    return

#########################################################################
# FONCTION dissolveVector()                                             #
#########################################################################
#   Role : La fonction a pour but de fusionner les polygones voisins (connexion) de même valeur
#   Paramètres :
#       vector_input : nom du fichier vecteur en entrée
#       vector_output : nom du fichier vecteur en sortie
#       column : colonne contenant l'information de valeur a comparer
#       format_vector : format du fichier vecteur

def dissolveVector(vector_input, vector_output, column, format_vector='ESRI Shapefile'):

    if debug >=2:
        print(cyan + "dissolveVector() : " + endC + "Fusion des polygones adjacents de meme %s du fichier %s" %(str(column), str(vector_input)))

    # Create driver ogr
    driver = ogr.GetDriverByName(format_vector)

    # Gestion des noms
    basename = os.path.basename(vector_input)
    filename = os.path.splitext(basename)[0]
    tmp_file = os.path.splitext(vector_output)[0] + "_tmp" + os.path.splitext(vector_output)[1]
    basename_tmp = os.path.basename(tmp_file)
    filename_tmp = os.path.splitext(basename_tmp)[0]

    if os.path.exists(vector_output):
        driver.DeleteDataSource(vector_output)
    if os.path.exists(filename_tmp):
        driver.DeleteDataSource(tmp_file)

    # ETAPE 1 : Fusion de tous les polygones d'une meme valeur en un polygone multiple

    # ogr2ogr ATTENTION cette version ne marche pas correctement
    command = "ogr2ogr -f \"%s\" -overwrite %s %s -dialect SQLITE -sql \"SELECT ST_Union(geometry), %s FROM %s GROUP BY %s\"" %(format_vector, tmp_file, vector_input, column, filename, column)
    if debug >=2:
        print(command)
    exit_code = os.system(command)
    if exit_code != 0:
        print(cyan + "dissolveVector() : " + bold + red + "!!! Une erreur c'est produite au cours de la fusion des polygones du vecteur : " + vector_input + endC, file=sys.stderr)

    # ETAPE 2 : Decoupage d'un multipolygones en plusieurs polygones simples
    multigeometries2geometries(tmp_file, vector_output, [column], 'MULTIPOLYGON', format_vector)

    # Nettoyage du fichier temporaire
    if os.path.exists(tmp_file):
        driver.DeleteDataSource(tmp_file)

    if debug >=2:
        print(cyan + "dissolveVector() : " + endC + "Le fichier vecteur " + str(vector_output)  + " est fusionne")
    return

#########################################################################
# FONCTION filterGeometryVector()                                       #
#########################################################################
#   Role : Filter un shape en ne gardant que les élément de type POLYGON (élimination POINT, MULTIPOINT... si ces élémnt existent)
#   Paramètres :
#       vector_input : le fichier shape à découper
#       vector_output:  le fichiers shape résultat découpé
#       overwrite: si le fichier existe il est ecrasé (cas par défaut)
#       format_vector : format du fichier vecteur

def filterGeometryVector(vector_input, vector_output, overwrite=True, format_vector='ESRI Shapefile'):

    if debug >=2:
        print(cyan + "filterGeometryVector() : " + endC + "Filtrage du fichier shape (Polygones) : " + str(vector_input))

    # Nettoyage du shape d'entrée ne garder que les geometries de type POLYGON

    overwrite_str = ""
    if overwrite:
        overwrite_str = "-overwrite"

    # Lecture des infos de la couche du shape d'entrée
    driver = ogr.GetDriverByName(format_vector)
    data_source_input = driver.Open(vector_input, 0) # 0 means read-only. 1 means writeable.
    if data_source_input is None :
         print(cyan + "filterGeometryVector() : " +  bold + red + "No file for " + vector_input + endC, file=sys.stderr)
         sys.exit(1) # exit with an error code
    else :
        layer_input = data_source_input.GetLayer()
        feature_input = layer_input.GetNextFeature()
        name_layer_input = layer_input.GetName()
        data_source_input.Destroy()

    # Filtrage des objets de type non polygone
    command = "ogr2ogr -f \"%s\" %s %s %s -sql \"SELECT * FROM %s WHERE OGR_GEOMETRY = 'POLYGON'\"" %(format_vector, overwrite_str, vector_output, vector_input, name_layer_input)
    if debug >=2:
        print(command)
    exit_code = os.system(command)
    if exit_code != 0:
        print(cyan + "filterGeometryVector() : " + bold + red + "!!! Une erreur c'est produite au cours du filtrage des polygones du vecteur : " + vector_input + endC, file=sys.stderr)

    if debug >=2:
        print(cyan + "filterGeometryVector() : " + endC + "Le fichier vecteur " + vector_input  + " a ete filtré resultat : " + vector_output)
    return

#########################################################################
# FONCTION filterSelectDataVector()                                     #
#########################################################################
#   Role : Lit un fichier vecteur et filtre les données à récupérer (colonnes et attributs) selon une expresion donnée pour crée un nouveau vecteur
#   Paramètres :
#       vector_input : nom du fichier vecteur en entrée
#       vector_output : nom du fichier vecteur en sortie
#       column : colonne à conserver en sortie
#       expression : exemple "ID = 11000" ou "Type ='AUTOROUTE'"
#       overwrite: si le fichier existe il est ecrasé (cas par défaut)
#       format_vector : format du fichier vecteur
#   Paramétres de retour :
#       Return True si l'operataion c'est bien passé, False sinon

def filterSelectDataVector (vector_input, vector_output, column, expression, overwrite=True, format_vector='ESRI Shapefile'):

    if debug >=2:
        print(cyan + "filterSelectDataVector() : " + endC + "Filtrage des donnees du fichier " + str(vector_input))

    ret = True
    overwrite_str = ""
    if overwrite:
        overwrite_str = "-overwrite"

    # Create driver ogr
    driver = ogr.GetDriverByName(format_vector)

    if os.path.exists(vector_output):
        driver.DeleteDataSource(vector_output)

    # Fonction de filtrage de la blibli OGR
    command = "ogr2ogr -f '%s' %s %s -select %s -where \"%s\" %s" % (format_vector, overwrite_str, vector_output, column, expression, vector_input)
    if debug >=2:
        print(command)
    exit_code = os.system(command)
    if exit_code != 0:
        print(cyan + "filterSelectDataVector() : " + bold + red + "!!! Une erreur c'est produite au cours du filtrage des colonnes du vecteur %s par l'expression %s " %(vector_input, expression) + endC, file=sys.stderr)
        ret = False

    if debug >=2:
        print(cyan + "filterSelectDataVector() : " + endC + "Le fichier vecteur " + str(vector_output)  + " filtre")
    return ret

#########################################################################
# FONCTION intersectDeletePolygons()                                    #
#########################################################################
#   Role : Supprimer les polygones qui s'intersectent entre les deux fichiers vecteurs (suppression dans les 2 fichiers)
#   Parametres :
#       vector_input1 : fichier d'entrée et de sortie 1
#       vector_input2 : fichier d'entrée et de sortie 2
#       format_vector : format du fichier vecteur

def intersectDeletePolygons(vector_input1, vector_input2, format_vector='ESRI Shapefile'):

    if debug >=2:
        print(cyan + "intersectDeletePolygons() : " + endC + "Supression des polygones qui s'intersectent des fichiers, vector_input1 =  " + str(vector_input1) + " vector_input2 = " + str(vector_input2))

    # Récupération du driver
    driver = ogr.GetDriverByName(format_vector)

    # Ouverture en mode écriture du fichier (vector_input1, 1)
    data_source_input1 = driver.Open(vector_input1, 1)
    if data_source_input1 is None:
        print(cyan + "intersectDeletePolygons() : " + bold + red + "intersectDeletePolygons() : Could not open file " + str(vector_input1), file=sys.stderr)
        sys.exit(1)
    layer1 = data_source_input1.GetLayer()
    feature1 = layer1.GetNextFeature()

    # Ouverture en mode écriture du fichier 2(vector_input2, 1)
    data_source_input2 = driver.Open(vector_input2, 1)
    if data_source_input2 is None:
        print(cyan + "intersectDeletePolygons() : " + bold + red + "intersectDeletePolygons() : Could not open file " + str(vector_input2), file=sys.stderr)
        sys.exit(1)
    layer2 = data_source_input2.GetLayer()

    # Parcours des éléments du fichier 1
    while feature1:

        layer2.ResetReading()
        # Récupération de la géométrie de l'élément du fichier 1
        geometry1 = feature1.GetGeometryRef()
        feature2 = layer2.GetNextFeature()

        # Parcours des éléments du fichier 2
        while feature2:
            # Récupération de la géométrie de l'élément du fichier 2
            geometry2 = feature2.GetGeometryRef()

            # Si les géométries des éléments des fichiers 1 et 2 se croisent (=1)
            if geometry1.Intersects(geometry2) == 1: #Variante possible avec Overlaps
                # Suprresion de l'élément du fichier 1 grace à son numéro de FID
                featureID1 = feature1.GetFID()
                try:
                    layer1.DeleteFeature(featureID1)
                except :
                    print(cyan + "intersectDeletePolygons() : " + bold + yellow + "Le polygonne est deja detruit " + endC)
                # Suprresion de l'élément du fichier 2 grace à son numéro de FID
                featureID2 = feature2.GetFID()
                try:
                    layer2.DeleteFeature(featureID2)
                except :
                    print(cyan + "intersectDeletePolygons() : " + bold + yellow + "Le polygonne est deja detruit " + endC)
            feature2.Destroy()
            feature2 = layer2.GetNextFeature()

        feature1.Destroy()
        feature1 = layer1.GetNextFeature()


    data_source_input1.Destroy()
    data_source_input2.Destroy()

    if debug >=2:
        print(cyan + "intersectDeletePolygons() : " + endC + "Les fichiers vecteurs ont ete nettoyes ")
    return

#########################################################################
# FONCTION withinPolygons()                                             #
#########################################################################
#   Role : Filtre un fichier vecteur de polygones par rapport à un fichier vecteur de points ou de lignes
#          ne sont garder uniquement les polygones contenant des points ou des lignes
#   Paramètres :
#       vector_contain : fichier vecteur contenant les points ou lignes
#       vector_input : le fichier vecteur de polygones à filtrer
#       vector_output :  le fichiers vecteur résultat filtré
#       overwrite: si le fichier existe il est ecrasé (cas par défaut)
#       format_vector : format du fichier vecteur (par défaut)

def withinPolygons(vector_contain, vector_input, vector_output, overwrite=True, format_vector='ESRI Shapefile'):

    if debug >=2:
        print(cyan + "withinPolygons() : " + endC + "Filtrage par le fichier vecteur contenant : " + str(vector_contain))

    check = os.path.isfile(vector_output)
    if check and not overwrite :
        print(cyan + "withinPolygons() : " + bold + yellow + "Output file " + str(vector_output) + " already exists." + '\n' + endC)
    else:
        # Récupération du driver
        driver = ogr.GetDriverByName(format_vector)

        # Tenter de supprimer le fichier
        try:
            driver.DeleteDataSource(vector_output)
        except Exception:
            # Ignore l'exception levee si le fichier n'existe pas (et ne peut donc pas être supprime)
            pass

        # Ouverture en mode lecture du fichier d'entrée (vector_input, 0)
        data_source_input = driver.Open(vector_input, 0)
        if data_source_input is None:
            print(cyan + "withinPolygons() : " + bold + red + "Could not open file " + str(vector_input), file=sys.stderr)
            sys.exit(1)
        layer_input = data_source_input.GetLayer()
        feature_input = layer_input.GetNextFeature()
        name_layer_input = layer_input.GetName()

        # Ouverture en mode lecture du fichier différencié (vector_contain, 0)
        data_source_contain = driver.Open(vector_contain, 0)
        if data_source_contain is None:
            print(cyan + "withinPolygons() : " + bold + red + "Could not open file " + str(vector_contain), file=sys.stderr)
            sys.exit(1)
        layer_contain = data_source_contain.GetLayer()

        # CREATION DU FICHIER DE SORTIE
        # Recupération du srs de la couche en entrée et assignation du système de projection du fichier en sortie
        output_srs=layer_input.GetSpatialRef()

        # Verification si le le fichier de sortie existe déjà (si oui le supprimer)
        if os.path.exists(vector_output):
            driver.DeleteDataSource(vector_output)
        data_source_output = driver.CreateDataSource(vector_output)                                        # Création du fichier "DataSource"
        layer_output = data_source_output.CreateLayer(name_layer_input, output_srs, geom_type=ogr.wkbPolygon) # Création du fichier "couche"(nom,projection, type de géométrie)
        defn_layer_output = layer_output.GetLayerDefn()                                                    # Creation du modèle d'"éléments" à partir des caractéristiques de la couche (type de géométrie : polygone...)

        # Ajout des champs du fichier d'entrée au fichier de sortie
        featureID = 0
        defn_layer_input = layer_input.GetLayerDefn()
        nb_fields = defn_layer_input.GetFieldCount()
        for i in range(0, nb_fields):
            field_defn = defn_layer_input.GetFieldDefn(i)
            layer_output.CreateField(field_defn)

        # Parcours des éléments du fichier d'entrée
        while feature_input:

            layer_contain.ResetReading()
            # Récupération de la géométrie de l'élément du fichier d'entrée
            geometry_input = feature_input.GetGeometryRef()
            feature_contain = layer_contain.GetNextFeature()

            # Parcours des éléments du fichier de découpage
            while feature_contain:
                # Récupération de la géométrie de l'élément du fichier de découpage
                geometry_contain = feature_contain.GetGeometryRef()

                # Si les géométries des éléments des fichiers d'entrée sont contenus dans les géometries polygones contenant on les gardes
                if geometry_contain.Within(geometry_input):

                    # Création de l'élément (du polygone) de sortie selon le modèle
                    feature_output = ogr.Feature(defn_layer_output)

                    # Assignation d'un numéro de FID à ce nouvel élément
                    feature_output.SetFID(featureID)
                    featureID += 1

                    # Pour tous les Champs
                    for j in range(0, nb_fields):
                        field_label = feature_input.GetFieldAsString(j)
                        feature_output.SetField(j, field_label)

                    # Assignation de la géométrie d'entrée à l'élément de sortie
                    feature_output.SetGeometry(geometry_input)

                    # Création de ce nouvel élément
                    layer_output.CreateFeature(feature_output)
                    layer_output.SyncToDisk()
                    feature_output.Destroy()

                    # Le polygon a été selectionner passer au suivant
                    feature_contain.Destroy()
                    break

                feature_contain.Destroy()
                feature_contain = layer_contain.GetNextFeature()

            # Passer à l'élément d'entrée suivant
            feature_input.Destroy()
            feature_input = layer_input.GetNextFeature()

        # Fermeture des fichiers shape
        data_source_input.Destroy()
        data_source_contain.Destroy()
        data_source_output.Destroy()

    if debug >=2:
        print(cyan + "withinPolygons() : " + endC + "Le fichier vecteur " + vector_input  + " a ete filtré resultat : " + vector_output)
    return

#########################################################################
# FONCTION deleteClassVector()                                          #
#########################################################################
#   Role : Cette fonction permet de supprimer des classes de polygonnes selon une valeur
#   Parametres :
#       supp_class_list : liste des valeurs de classes à supprimer
#       vector_input : fichier vecteur a modifier
#       field : le champs contenant le label de classe
#       format_vector : format du fichier vecteur

def deleteClassVector(supp_class_list, vector_input, field, format_vector='ESRI Shapefile') :

    if debug >=2:
        print(cyan + "deleteClassVector() : " + endC + "Suression de classes du vecteur " + vector_input)

    # Creer un fichier vecteur de sortie
    name_file = os.path.splitext(vector_input)[0]
    extension_file = os.path.splitext(vector_input)[1]
    vector_output = name_file + "_tmp" + extension_file

    # Recuperation du driver pour le format shape fichier entrée
    driver_input = ogr.GetDriverByName(format_vector)

    # Ouverture du fichier shape en lecture
    data_source_input = driver_input.Open(vector_input, 0) # 0 means read-only. 1 means writeable.
    if data_source_input is None:
        print(cyan + "deleteClassVector() : " + bold + red + "Impossible d'ouvrir le fichier shape : " + vector_input + endC, file=sys.stderr)
        sys.exit(1) # exit with an error code

    # Recuperer la couche (une couche contient les polygones)
    layer_input = data_source_input.GetLayer(0)
    name_layer_input = layer_input.GetName()
    output_srs = layer_input.GetSpatialRef ()
    geom_type_input = layer_input.GetGeomType()

    # Recuperation du driver pour le format shape fichier de sortie
    driver_output = ogr.GetDriverByName(format_vector)

    # Si le fichier destination existe deja on l ecrase
    if os.path.exists(vector_output) :
        print(cyan + "deleteClassVector() : " + bold + red + "Le fichier shape  existe deja il sera ecrase : " + vector_output + endC)
        driver_output.DeleteDataSource(vector_output)

    # Creation du fichier shape de sortie en écriture
    data_source_output = driver_output.CreateDataSource(vector_output)
    layer_output = data_source_output.CreateLayer(name_layer_input, output_srs, geom_type=geom_type_input)

    # Ajouter les champs du fichier d'entrée au fichier de sortie
    defn_layer_input = layer_input.GetLayerDefn()
    for i in range(0, defn_layer_input.GetFieldCount()):
        field_defn = defn_layer_input.GetFieldDefn(i)
        layer_output.CreateField(field_defn)

    # Recupere le output Layer's Feature Definition
    defn_layer_output = layer_output.GetLayerDefn()

    #  Comptage du nombre de polygones sources
    num_features = layer_input.GetFeatureCount()
    if debug >= 1:
        print(cyan + "deleteClassVector() : " + bold + green + "Nombre de polygones sources : " + str(num_features) + endC)

    # Pour chaque polygones
    # Add features to the ouput Layer
    for i in range(0, layer_input.GetFeatureCount()):
         # Get the input Feature
         try:
             feature_input = layer_input.GetFeature(i)
         except RuntimeError:
             print(cyan + "deleteClassVector() : " + bold + yellow + "Le fichier shape est corrompu " + endC)
         else:
             # Recuper la valeur du champ de classification
             label_classif = feature_input.GetField(field)

             # Si l'identifiant de classification n'appartient pas a la liste supp_class_list, on copie le polygone
             if not label_classif in supp_class_list:
                 if debug >= 4:
                     print("identifant a %s" %(str(label_classif)))

                 # Add new feature to output Layer
                 layer_output.CreateFeature(feature_input)

    # Comptage du nombre de polygones destinations
    num_features = layer_output.GetFeatureCount()
    if debug >= 1:
        print(cyan + "deleteClassVector() : " + bold + green + "Nombre de polygones destination : " + str(num_features) + endC)

    # Fermeture des fichiers shape
    layer_output.SyncToDisk()
    data_source_input.Destroy()
    data_source_output.Destroy()

    # Renomer le fichier d'entrée avec le fichier modifié temporaire
    driver_output.DeleteDataSource(vector_input)
    renameVectorFile(vector_output, vector_input)

    if debug >=2:
        print(cyan + "deleteClassVector() : " + bold + green + "Delete class of %s complete!" %(vector_input) + endC)
    return

#########################################################################
# FONCTION reallocateClassVector()                                      #
#########################################################################
#   Role : Cette fonction permet de réaffecter des valeurs de classes de polygonnes par d'autre valeurs
#   Parametres :
#       reaff_class_list : liste des valeurs de classes à réaffecter
#       macro_reaff_class_list : liste des valeurs de classes de réaffectation
#       vector_input : fichier vecteur a modifier
#       field : le champs contenant le label de classe
#       format_vector : format du fichier vecteur

def reallocateClassVector(reaff_class_list, macro_reaff_class_list, vector_input, field, format_vector='ESRI Shapefile') :

    if debug >=2:
        print(cyan + "reallocateClassVector() : " + endC + "Reafectation des classes de polygones du vecteur " + vector_input)

    # Recuperation du driver pour le format shape fichier entrée
    driver_input = ogr.GetDriverByName(format_vector)

    # Ouverture du fichier shape en lecture-ecriture
    data_source_input = driver_input.Open(vector_input, 1) # 1 means writeable.
    if data_source_input is None:
        print(cyan + "reallocateClassVector() : " + bold + red + "Impossible d'ouvrir le fichier shape : " + vector_input + endC, file=sys.stderr)
        sys.exit(1) # exit with an error code

    # Recuperer la couche (une couche contient les polygones)
    layer_input = data_source_input.GetLayer(0)

    # Pour chaque polygones
    for i in range(0, layer_input.GetFeatureCount()):
         # Get the input Feature
         feature_input = layer_input.GetFeature(i)

         # Recuper la valeur du champ de classification
         label_classif = feature_input.GetField(field)

         # Si l'identifiant de classification n'appartient pas a la liste supp_class_list, on copie le polygone
         if label_classif in reaff_class_list:
             idx_class = reaff_class_list.index(label_classif)
             new_label_classif = macro_reaff_class_list[idx_class]
             feature_input.SetField(field, new_label_classif)
             layer_input.SetFeature(feature_input)
             if debug >= 4:
                 print("identifant : " + (str(label_classif)))
                 print("new label : " + str(new_label_classif))

         feature_input.Destroy()

    # Fermeture du fichier shape
    layer_input.SyncToDisk()
    data_source_input.Destroy()

    if debug >=2:
        print(cyan + "reallocateClassVector() : " + bold + green + "Reallocate class of %s complete!" %(vector_input) + endC)
    return

#########################################################################
# FONCTION cleanLabelPolygons()                                         #
#########################################################################
#   Role : Fonction qui modifie le label de polygones pour une certaine valeur en fonction du label du polygone le plus proche
#   Paramètres :
#       vector_input : nom du fichier vecteur d'entrée
#       vector_output : nom du fichier vecteur de sortie
#       col : nom du champs (colonne) à regarder
#       wrongval_list : listes des valeurs du label à enlever
#       tol : tolerance pour l'optimisation en mètre
#       format_vector : format d'entrée et de sortie des fichiers vecteurs. Optionnel, par default : 'ESRI Shapefile'
#       extension_vector : valeur de l'extention du fichier vecteur en fonction du format, par defaut : '.shp'
#   En sortie :
#       retour True si ok
#  Exemple d'utilisation: cleanLabelPolygons("vectorInput.shape","vectorOutput.shape",65536,'ESRI Shapefile')

def cleanLabelPolygons(vector_input, vector_output, col='label', wrongval_list=[0,65535], tol = 1.0, format_vector='ESRI Shapefile', extension_vector='.shp'):

    if debug >=2:
        print(cyan + "cleanLabelPolygons() : " + endC + "Modification des polygones de label %s par attribution du label le plus proche du fichier %s" %(str(wrongval_list), str(vector_input)))

    # Lecture du fichier en entrée
    driver = ogr.GetDriverByName(format_vector)
    data_source_input = driver.Open(vector_input, 0)

    if data_source_input is None:
        print(cyan  + "cleanLabelPolygons() : " + bold + red + "Could not open file : " + str(vector_input), file=sys.stderr)
        sys.exit(1)

    # Récupération des caractéristiques du fichier en entrée (type de géométrie, projection...)
    layer_input = data_source_input.GetLayer()
    name_layer_input = layer_input.GetName()
    output_srs = layer_input.GetSpatialRef()
    out_geom_type = ogr.wkbPolygon
    defn_layer_input = layer_input.GetLayerDefn()
    nb_fields = defn_layer_input.GetFieldCount()

    if debug >=3:
        print("Nombre total de polygones du fichier d'entrée : " + str(layer_input.GetFeatureCount()))

    # Transformation des multipolygones en polygones pour layer_input
    repository = os.path.dirname(vector_input)
    filename = os.path.splitext(os.path.basename(vector_input))[0]
    vector_temp_simplepoly = repository + os.sep + filename + "_spoly" + extension_vector
    multigeometries2geometries(vector_input, vector_temp_simplepoly, [col])

    data_source_temp_simplepoly = driver.Open(vector_temp_simplepoly, 0)
    if data_source_temp_simplepoly is None:
        print(cyan  + "cleanLabelPolygons() : " + bold + red  +  "Could not open file : " + str(vector_temp_simplepoly), file=sys.stderr)
        sys.exit(1)

    layer_temp_simplepoly = data_source_temp_simplepoly.GetLayer()
    defn_layer_temp_simplepoly = layer_temp_simplepoly.GetLayerDefn()
    nb_fields_temp_simplepoly = defn_layer_temp_simplepoly.GetFieldCount()

    # Si le fichier vecteur de sortie existe on le supprime
    if os.path.exists(vector_output):
        driver.DeleteDataSource(vector_output)

    # Creation du fichier shape de sortie en écriture
    data_source_output = driver.CreateDataSource(vector_output)
    layer_output = data_source_output.CreateLayer(name_layer_input, srs=output_srs, geom_type=out_geom_type)
    for i in range(0, nb_fields_temp_simplepoly):
        field_defn = defn_layer_input.GetFieldDefn(i)
        layer_output.CreateField(field_defn)

    nb_poly_modif=0
    # Correction des polygone de label wrongval_list
    for i in range(0,layer_temp_simplepoly.GetFeatureCount()):
        feature_temp_simplepoly = layer_temp_simplepoly.GetFeature(i)
        geometry = feature_temp_simplepoly.GetGeometryRef()
        label_classif = feature_temp_simplepoly.GetField(col)
        list_label_classif = []
        compt_list_label_classif = 0

        if label_classif in wrongval_list :
            nb_poly_modif += 1
            # Parcours des polygones à tester
            geom_buffer_temp = geometry.Buffer(tol)
            layer_input.SetSpatialFilter(geom_buffer_temp)
            feature_input_select = layer_input.GetNextFeature()
            while feature_input_select is not None:
                geometry_input_select = feature_input_select.GetGeometryRef()
                if geometry_input_select.Touches(geometry) :
                    list_label_classif.append(feature_input_select.GetField(col)) #Il peut y avoir plusieurs polygones qui touchent le polygone à corriger
                    compt_list_label_classif += 1
                feature_input_select.Destroy()
                feature_input_select = layer_input.GetNextFeature()

        # Assignation du modèle de "couche" un nouvel élément (copie de l'élement d'origine)
        feature_output = ogr.Feature(layer_output.GetLayerDefn())
        # Assignation de la géométrie simplifie à ce nouvel élément
        feature_output.SetGeometry(geometry)

        # Pour tous les Champs
        for j in range(0, nb_fields_temp_simplepoly):
            field_label = feature_temp_simplepoly.GetFieldAsString(j)
            feature_output.SetField(j, field_label)

        if compt_list_label_classif == 0: # Pas de correction du polygone
            if debug >=4:
                print("Pas de traitement pour le polygone " + str(i) + "/" + str(layer_temp_simplepoly.GetFeatureCount()) + " de label : " + str(label_classif), file=sys.stderr)
            list_label_classif.append(label_classif)

        list_label_classif.sort(reverse=True) # S'il y a plusieurs label possibles (pls polygones qui touchent le polygones à corriger), on choisit de garder le label le plus élevé
        feature_output.SetField(col, list_label_classif[0])
        if compt_list_label_classif !=0: # Le polygone a été corrigé
            if debug >=4:
                print("Traitement du polygone " + str(i) + "/" + str(layer_temp_simplepoly.GetFeatureCount()) + " de label : " + str(label_classif) + " par le label : " + str(list_label_classif[0]), file=sys.stderr)

        # Création de ce nouvel élément
        layer_output.CreateFeature(feature_output)

    # Fermeture des fichiers shape
    layer_output.SyncToDisk()
    data_source_input.Destroy()
    data_source_output.Destroy()

    # Suppression du fichier temporaire
    if os.path.exists(vector_temp_simplepoly):
        driver.DeleteDataSource(vector_temp_simplepoly)

    if debug >=3:
        print("Nombre total de polygones corrigés : " + str(nb_poly_modif))

    if debug >=2:
        print(cyan + "cleanLabelPolygons() : " + endC + "Fichier vecteur nettoyé : " + str(vector_output))

    return True

#########################################################################
# FONCTION relabelVectorFromMajorityPixelsRaster()                      #
#########################################################################
#   Role : Cette fonction permet de relabeliser un fichier vecteur en fonction de la valeur majoritaire des pixels du fichier raster inclus dans les polygonnes
#   Parametres :
#       vector_input : nom du fichier vecteur d'entrée et de sortie
#       image_raster_input : nom du fichier raster d'entrée
#       name_column : nom de la colonne à modifier
#       format_vector : format du fichier vecteur

def relabelVectorFromMajorityPixelsRaster(vector_input, image_raster_input, name_column, format_vector='ESRI Shapefile') :

    if debug >=2:
        print(cyan + "relabelVectorFromMajorityPixelsRaster() : " + endC + "Relabelisation du vecteur par valeur majoritaire " + vector_input)

    # Recuperation du driver pour le format shape
    driver = ogr.GetDriverByName(format_vector)
    # Ouverture du fichier shape en lecture-écriture
    data_source = driver.Open(vector_input, 1) # 1 means writeable
    if data_source is None:
        print(cyan + "relabelVectorFromMajorityPixelsRaster() : " + bold + red + "Impossible d'ouvrir le fichier shape : " + vector_input + endC, file=sys.stderr)
        sys.exit(1) # exit with an error code

    layer_input = data_source.GetLayer(0)
    layer_definition = layer_input.GetLayerDefn()
    if layer_definition.GetFieldIndex(name_column) == -1 :
        stat_classif_field_defn = ogr.FieldDefn(name_column, ogr.OFTString)
        stat_classif_field_defn.SetWidth(10)
        layer_input.CreateField(stat_classif_field_defn)

    num_features = layer_input.GetFeatureCount()
    if debug >=2:
        print("Nombre de polygones : " + str(num_features))

    # Lib stats pour récuperer la valeur majoritaire
    stats = raster_stats(vector_input, image_raster_input, stats=['majority'])

    # Pour tous les polygones
    for elem in stats :
        feature_input = layer_input.GetFeature(elem['__fid__'])

        # Valeur majoritaire de la lib raster_stats
        value_classif = elem['majority']

        # Sauvegarde du résultat de statistique dans le fichier source shape
        feature_input.SetField(name_column, str(value_classif))
        layer_input.SetFeature(feature_input)
        feature_input.Destroy()

    # Fermeture du fichier shape
    layer_input.SyncToDisk()
    layer_input = None
    data_source.Destroy()

    if debug >=2:
        print(cyan + "relabelVectorFromMajorityPixelsRaster() : " + endC + "Labellisation of %s complete from %s!" %(vector_input, image_raster_input) + endC)
    return

#########################################################################
# FONCTION mergeVectors()                                               #
#########################################################################
#   ATTENTION !!! OBSOLETE utiliser de preference la fonction fusionVectors() beaucoup plus rapide...
#   Role : Concatener des shapefiles dont les noms sont présents dans une liste
#   Paramètres :
#       vectors_input_list : noms des shapefiles à fusionner
#       vector_output : nom du fichier shape final
#       format_vector : format du fichier vecteur
#       projection : code EPSG du fichier en sortie
#   Ressources :
#       http://gistncase.blogspot.fr/2012/05/python-shapefile-merger-utility.html
#       http://eomwandho.wordpress.com/2012/02/25/bash-script-to-merge-shapefiles-in-a-directory-into-one-shapefile/
#       http://darrencope.com/2010/05/07/merge-a-directory-of-shapefiles-using-ogr/

def mergeVectors(vectors_input_list, vector_output, format_vector='ESRI Shapefile', projection=None):

    if debug >=2:
        print(cyan + "mergeVectors() : " + endC + "Fusion des fichiers vecteurs...")

    # Définition du nom du fichier de sortie et de ses craractéristiques
    geometryType = ogr.wkbPolygon #ogr.wkbLineString

    if vectors_input_list != []:
        data_source_input = ogr.Open(vectors_input_list[0])
        layer_input = data_source_input.GetLayer(0)
        geometryType = layer_input.GetGeomType()
        if projection == None :
            projection = getProjection(vectors_input_list[0], format_vector)
            if projection == None :
                projection = 2154

    # CREATION DU FICHIER DE SORTIE
    # Create driver ogr
    driver_output = ogr.GetDriverByName(format_vector)
    if os.path.exists(vector_output):
        driver_output.DeleteDataSource(vector_output)
    data_source_output = driver_output.CreateDataSource(vector_output)  # Création du fichier Datasource

    # Assignation du système de projection du fichier en sortie
    output_srs = osr.SpatialReference()
    output_srs.ImportFromEPSG(projection)
    layer_output = data_source_output.CreateLayer(os.path.splitext(os.path.basename(vector_output))[0], output_srs, geom_type=geometryType)

    for file_input in vectors_input_list:

        data_source_input = ogr.Open(file_input)

        if data_source_input is None :
             print(bold + yellow + "No file for " + file_input + endC)
        else :
            layer_input = data_source_input.GetLayer()
            defn_layer_input = layer_input.GetLayerDefn() # Ajout des champs du fichier d'entrée au fichier de sortie
            nb_fields = defn_layer_input.GetFieldCount()
            for i in range(0, nb_fields):
                field_defn = defn_layer_input.GetFieldDefn(i)
                defn_layer_output = layer_output.GetLayerDefn()
                nb_fields_output = defn_layer_output.GetFieldCount()
                is_field_exist = False
                for m in range(0, nb_fields_output):
                    field_output = defn_layer_output.GetFieldDefn(m)
                    if field_output.GetNameRef() == field_defn.GetNameRef():
                        is_field_exist = True
                if not is_field_exist:
                    layer_output.CreateField(field_defn)

            for feature_input in layer_input:
                feature_output = ogr.Feature(layer_output.GetLayerDefn())

                for j in range(0, nb_fields):    # Pour tous les Champs
                    field_label = feature_input.GetFieldAsString(j)
                    feature_output.SetField(j, field_label)

                feature_output.SetGeometry(feature_input.GetGeometryRef())
                layer_output.CreateFeature(feature_output)
                layer_output.SyncToDisk()

    if debug >=2:
        print(cyan + "mergeVectors() : " + endC + "Le fichier vecteur " + str(vector_output)  + " resultat du merge des fichiers vecteurs")
    return

#########################################################################
# FONCTION fusionVectors()                                              #
#########################################################################
#   Role : Fusionner une liste de vecteurs en un nouveau fichier vecteur
#   Paramètres :
#       vectors_input_list : noms des shapefiles à fusionner
#       vector_output : nom du fichier vecteur en sortie
#       format_vector : format du fichier vecteur

def fusionVectors(vectors_input_list, vector_output, format_vector='ESRI Shapefile'):

    if debug >=2:
        print(cyan + "fusionVectors() : " + endC + "Fusion des fichiers vecteurs " + str(vectors_input_list))

    # Fonction de fusion de la blibli OGR
    for shapefile in vectors_input_list:
        geom_type = getGeometryType(shapefile, format_vector)

        if geom_type != None :

            if os.path.isfile(vector_output) :
                cmd_append = "-update -append"
            else :
                cmd_append = ""

            command = "ogr2ogr -skipfailures -f \"%s\" %s %s %s -nlt %s"%(format_vector, cmd_append, vector_output, shapefile, geom_type)

            if debug >=2:
                print(command)

            exit_code = os.system(command)
            if exit_code != 0:
                print(cyan + "fusionVectors() : " + bold + red + "!!! Une erreur c'est produite au cours de la fusion des vecteurs : " + str(vectors_input_list) + endC, file=sys.stderr)

    if debug >=2:
        print(cyan + "fusionVectors() : " + endC + "Le fichier vecteur fusionne " + str(vector_output))
    return

########################################################################
# FONCTION convertePolygon2Polylines()                                 #
########################################################################
# Rôle : cette fonction permet de convertirun fichier shape conenant des polygones, en un fichier shape contenant des polylignes.
# Paramètres en entrée :
#       vector_input : vecteur d'entrée, qui contient des les polygones
#       vector_output : vecteur de sortie, qui sera converti en geometrie MultiLignes
#       overwrite: si le fichiers existe il est ecrasé (cas par défaut)
#       format_vector : format du fichier vecteur
# Paramètres en sortie :
#       N.A.

def convertePolygon2Polylines(vector_input, vector_output, overwrite=True, format_vector='ESRI Shapefile'):

    if debug >=2:
        print(cyan + "convertePolygon2Polylines() : " + endC + "conversion du fichier polygones " + vector_input + " en fichier vecteur polylignes : " + vector_output + endC)

    # Si option d'écrasement
    overwrite_str = ""
    if overwrite:
        overwrite_str = "-overwrite"

    command = "ogr2ogr -f '%s' -nlt MULTILINESTRING %s %s %s" % (format_vector, overwrite_str, vector_output, vector_input)
    if debug >=2:
        print(command)
    exit_code = os.system(command)
    if exit_code != 0:
        print(cyan + "convertePolygon2Polylines() : " + bold + red + "!!! Une erreur s'est produite à la création du fichier multiligne : " + vector_input + ". Voir message d'erreur." + endC, file=sys.stderr)
        sys.exit(1)

    if debug >=2:
        print(cyan + "convertePolygon2Polylines() : " + endC + "le fichier " + vector_input + " a été converti en  vecteur MULTILINESTRING " + vector_output + "." + endC)

    return

#########################################################################
# FONCTION mergeAndNewLabel()                                           #
#########################################################################
#   Role : Fusionner des shapefiles dont les noms sont présents dans une liste
#   Paramètres :
#       vectors_input_list : noms des shapefiles à fusionner
#       vector_output : nom du fichier shape final
#       col : nom de la colonne à créer
#       label : attribut à placer dans le champ ID
#       projection : code EPSG du fichier en sortie
#       format_vector : format du fichier vecteur
#   Ressources :
#       ftp://ftp.remotesensing.org/pub/gdal/presentations/OpenSource_Weds_Andre_CUGOS.pdf
#       http://www.forumsig.org/showthread.php/28688-Python-OGR-Ajouter-des-donn%C3%A9es-et-g%C3%A9om%C3%A9trie-a-un-shapefile-vide

def mergeAndNewLabel(vectors_input_list, vector_output, col, label, projection=2154, format_vector='ESRI Shapefile'):
    if debug >=2:
       print(cyan + "mergeAndNewLabel() : " + endC + "Creation du nouveau vecteur merge et du nouveau champ ...")

    # Céation du fichier de sortie
    driver_output = ogr.GetDriverByName(format_vector)
    if os.path.exists(vector_output):
        driver_output.DeleteDataSource(vector_output)
    data_source_output = driver_output.CreateDataSource(vector_output)

    # Assignation du système de projection du fichier en sortie
    output_srs = osr.SpatialReference()
    output_srs.ImportFromEPSG(projection)

    # Creation de la couche
    layer_output = data_source_output.CreateLayer(os.path.splitext(os.path.basename(vector_output))[0], output_srs, ogr.wkbPolygon)

    # Creation du nouveau champs
    fd = ogr.FieldDefn(col, ogr.OFTInteger)
    layer_output.CreateField(fd)

    print("Fusion des vecteurs et assignation du nouveau label...")

    # Lecture de chaque fichiers et ecriture d'un nouveau champ dans le fichier (merge) de sortie
    for vector in vectors_input_list:
        if debug >=4:
            print(vector)

        # Recuperation du driver
        driver_input = ogr.GetDriverByName(format_vector)
        # Ouverture du fichier
        data_source_input = driver_input.Open(vector)
        # Lecture de la couche vecteur
        layer_input = data_source_input.GetLayer(0)
        # Lecture des entites de la couche
        feature_input = layer_input.GetNextFeature()

        # Boucle sur toutes les entites de la couche pour récupérer
        while feature_input is not None:
            feature_output = ogr.Feature(layer_output.GetLayerDefn())
            feature_output.SetField(col, label)
            feature_output.SetGeometry(feature_input.GetGeometryRef().Clone())
            layer_output.CreateFeature(feature_output)
            layer_output.SyncToDisk()
            feature_output.Destroy()
            feature_input.Destroy()
            feature_input = layer_input.GetNextFeature()

    # Fermeture des fichiers
    data_source_output.Destroy()

    if debug >=2:
       print(cyan + "mergeAndNewLabel() : " + endC + "Le fichier vecteur " + str(vector_output)  + " resultat du merge des fichiers polygons")
    return

#########################################################################
# FONCTION createEmpriseShapeReduced()                                  #
#########################################################################
#   Role : Creation d'un vecteur d'emprise pour une image en fonction d'une emprise globale
#
# Paramètres en entrée :
#    vector_input : Fichier vecteur d'emprise globale
#    empr_xmin    : L'emprise coordonnée empr_xmin de l'image, rectifié
#    empr_xmax    : L'emprise coordonnée empr_xmax de l'image, rectifié
#    empr_ymin    : L'emprise coordonnée empr_ymin de l'image, rectifié
#    empr_ymax    : L'emprise coordonnée empr_ymax de l'image, rectifié
#    local_emprise_shape : Le fichier vecteur d'emprise crée
#    format_vector : Format du fichier vecteur, par default : 'ESRI Shapefile'
#
# Paramètres en sortie :
#    local_emprise_shape : Le fictier vecteur d'emprise de sortie
#
def createEmpriseShapeReduced(vector_input, empr_xmin, empr_ymin, empr_xmax, empr_ymax, local_emprise_shape, format_vector='ESRI Shapefile'):

    # Supression du fichier shape local si il existe déjà
    removeVectorFile(local_emprise_shape)

    # Creation d'un shape file d'emprise local
    command = "ogr2ogr -f " + "\"" + format_vector + "\"" + " -skipfailures -clipsrc " + str(empr_xmin) + " " + str(empr_ymin) + " " + str(empr_xmax) + " " + str(empr_ymax) + " " + local_emprise_shape + " " + vector_input

    if debug >= 4:
        print(cyan + "createEmpriseShapeReduced : " + endC + "command : " + str(command) + endC)

    exit_code = os.system(command)
    if exit_code != 0:
        print(command)
        raise NameError (bold + red + "createEmpriseShapeReduced : Une erreur c'est produite à la création du fichier shape d'emprise local : " + local_emprise_shape + ". Voir message d'erreur." + endC)

    return

#########################################################################
# FONCTION cutoutVectors()                                              #
#########################################################################
#   Role : Découper des fichiers shape par l'emprise d'un autre fichier shape
#   Paramètres :
#       vector_cut : fichier shape de découpage
#       vectors_input_list : liste des fichiers shape à découper
#       vectors_output_list:  liste des fichiers shape découpés
#       overwrite: si les fichiers existent ils sont ecrasés (cas par défaut)
#       format_vector : format du fichier vecteur

def cutoutVectors(vector_cut, vectors_input_list, vectors_output_list, overwrite=True, format_vector='ESRI Shapefile'):
    if debug >=2:
        print(cyan + "cutoutVectors() : " + endC + "Decoupage des echantillons par le masque : " + str(vector_cut))

    for index_vector in range (len(vectors_input_list)) :

        # Récupération des vecteurs
        vector_input = vectors_input_list[index_vector]
        vector_output = vectors_output_list[index_vector]

        if debug >=3:
            print("Fichier vecteur d'entree : " + str(vector_input))
            print("Fichier vecteur de sortie : " + str(vector_output))

        # Découpage unitaire du vecteur
        cutVectorAll(vector_cut, vector_input, vector_output, overwrite, format_vector)

        if debug >=3:
            print("Fichier vecteur découpé de sortie  : " + str(vector_output) + "\n")

    if debug >=2:
       print(cyan + "cutoutVectors() : " + endC + "Les fichiers vecteurs du repertoire  " + str(os.path.dirname(vectors_input_list[0]))  + " ont ete decoupe")
    return

#########################################################################
# FONCTION cutVectorAll()                                               #
#########################################################################
#   Role : Découper un fichier shape par l'emprise d'un autre fichier shape de tout type de geometrie
#   Paramètres :
#       vector_cut : fichier shape de découpage
#       vector_input : le fichier shape à découper
#       vector_output:  le fichiers shape résultat découpé
#       overwrite: si le fichier existe il est ecrasé (cas par défaut)
#       format_vector : format du fichier vecteur

def cutVectorAll(vector_cut, vector_input, vector_output, overwrite=True, format_vector='ESRI Shapefile'):

    if debug >=2:
        print(cyan + "cutVectorAll() : " + endC + "Decoupage par le fichier shape : " + str(vector_cut))

    # Si option d'écrasement
    overwrite_str = ""
    if overwrite:
        overwrite_str = "-overwrite"

    # Récuperer la géometry du fichier
    geom_type = getGeometryType(vector_input, format_vector)

    # Fonction de découpage de la bibli OGR
    command = "ogr2ogr -clipsrc %s %s %s -nlt %s %s -f \"%s\" -skipfailures" %(vector_cut, vector_output, vector_input, geom_type, overwrite_str, format_vector)
    if debug >=2:
        print(command)
    exit_code = os.system(command)
    if exit_code != 0:
        print(cyan + "cutVectorAll() : " + bold + red + "!!! Une erreur c'est produite au cours du découpage du vecteur : " + vector_input + endC, file=sys.stderr)

    if debug >=2:
        print(cyan + "cutVectorAll() : " + endC + "Le fichier vecteur " + vector_input  + " a ete decoupe resultat : " + vector_output + " type geom = " +geom_type)
    return

#########################################################################
# FONCTION cutVector()                                                  #
#########################################################################
#   Role : Découper un fichier shape par l'emprise d'un autre fichier shape (polygone)
#   Paramètres :
#       vector_cut : fichier shape de découpage
#       vector_input : le fichier shape à découper
#       vector_output:  le fichier shape résultat découpé
#       overwrite: si le fichier existe il est ecrasé (cas par défaut)
#       format_vector : format du fichier vecteur
#   Paramétre de retour :
#       Return True si au moins un polygon du fichier vector_output à intersecter avec le fichier vector_cut, False sinon

def cutVector(vector_cut, vector_input, vector_output, overwrite=True, format_vector='ESRI Shapefile'):

    if debug >=2:
        print(cyan + "cutVector() : " + endC + "Decoupage par le fichier shape : " + str(vector_cut))

    ret = False
    check = os.path.isfile(vector_output)
    if check and not overwrite :
        print(cyan + "cutVector() : " + bold + yellow + "Output file " + str(vector_output) + " already exists." + '\n' + endC)
    else:
        # Récupération du driver
        driver = ogr.GetDriverByName(format_vector)

        # Tenter de supprimer le fichier
        try:
            driver.DeleteDataSource(vector_output)
        except Exception:
            # Ignore l'exception levee si le fichier n'existe pas (et ne peut donc pas être supprime)
            pass

        # Ouverture en mode lecture du fichier d'entrée (vector_input, 0)
        data_source_input = driver.Open(vector_input, 0)
        if data_source_input is None:
            print(cyan + "cutVector() : " + bold + red + "Could not open file " + str(vector_input), file=sys.stderr)
            sys.exit(1)
        layer_input = data_source_input.GetLayer()
        name_layer_input = layer_input.GetName()
        feature_input = layer_input.GetNextFeature()

        # Ouverture en mode lecture du fichier différencié (vector_cut, 0)
        data_source_cut = driver.Open(vector_cut, 0)
        if data_source_cut is None:
            print(cyan + "cutVector() : " + bold + red + "Could not open file " + str(vector_cut), file=sys.stderr)
            sys.exit(1)
        layer_cut = data_source_cut.GetLayer()

        # CREATION DU FICHIER DE SORTIE
        # Recupération du srs de la couche en entrée et assignation du système de projection du fichier en sortie
        output_srs=layer_input.GetSpatialRef()

        # Verification si le le fichier de sortie existe déjà (si oui le supprimer)
        if os.path.exists(vector_output):
            driver.DeleteDataSource(vector_output)
        data_source_output = driver.CreateDataSource(vector_output)                                          # Création du fichier "DataSource"
        layer_output = data_source_output.CreateLayer(name_layer_input,output_srs, geom_type=ogr.wkbPolygon) # Création du fichier "couche"(nom,projection, type de géométrie)
        defn_layer_output = layer_output.GetLayerDefn()                                                      # Creation du modèle d'"éléments" à partir des caractéristiques de la couche (type de géométrie : polygone...)

        # Ajout des champs du fichier d'entrée au fichier de sortie
        featureID = 0
        defn_layer_input = layer_input.GetLayerDefn()
        nb_fields = defn_layer_input.GetFieldCount()
        for i in range(0, nb_fields):
            field_defn = defn_layer_input.GetFieldDefn(i)
            layer_output.CreateField(field_defn)

        # Parcours des éléments du fichier d'entrée
        while feature_input:

            layer_cut.ResetReading()
            # Récupération de la géométrie de l'élément du fichier d'entrée
            geometry_input = feature_input.GetGeometryRef()
            feature_cut = layer_cut.GetNextFeature()

            # Parcours des éléments du fichier de découpage
            while feature_cut:
                # Récupération de la géométrie de l'élément du fichier de découpage
                geometry_cut = feature_cut.GetGeometryRef()

                # Si les géométries des éléments des fichiers d'entrée et de découpage se croisent (=1)
                if geometry_input.Intersects(geometry_cut) == 1: # Variante possible avec Overlaps
                    # Il y a au moins un polygone qui intersects
                    ret = True
                    # Découper geometry_input par geometry_cut
                    geom_output = geometry_input.Intersection(geometry_cut)

                    if geom_output.GetGeometryName() == 'POLYGON' or geom_output.GetGeometryName() == 'MULTIPOLYGON' or geom_output.GetGeometryName() == 'GEOMETRYCOLLECTION':

                        # Si c'est une GEOMETRYCOLLECTION
                        if geom_output.GetGeometryName() == 'GEOMETRYCOLLECTION' :
                            # Nettoyage de la géometrie
                            geom_wkt = geom_output.ExportToWkt()
                            poly_wkt_out = geom_wkt[geom_wkt.find('POLYGON'):-1]
                            geom_output = ogr.CreateGeometryFromWkt(poly_wkt_out)

                        # Création de l'élément (du polygone) de sortie selon le modèle
                        feature_output = ogr.Feature(defn_layer_output)

                        # Assignation d'un numéro de FID à ce nouvel élément
                        feature_output.SetFID(featureID)
                        featureID += 1

                        # Pour tous les Champs
                        for j in range(0, nb_fields):
                            field_label = feature_input.GetFieldAsString(j)
                            feature_output.SetField(j, field_label)

                        # Assignation de la géométrie de découpage à l'élément de sortie
                        feature_output.SetGeometry(geom_output)

                        # Création de ce nouvel élément
                        layer_output.CreateFeature(feature_output)
                        layer_output.SyncToDisk()
                        feature_output.Destroy()

                feature_cut.Destroy()
                feature_cut = layer_cut.GetNextFeature()

            # Passer à l'élément d'entrée suivant
            feature_input.Destroy()
            feature_input = layer_input.GetNextFeature()

        # Fermeture des fichiers shape
        data_source_input.Destroy()
        data_source_cut.Destroy()
        data_source_output.Destroy()

    if debug >=2:
        print(cyan + "cutVector() : " + endC + "Le fichier vecteur " + vector_input  + " a ete decoupe resultat : " + vector_output)
    return ret

#########################################################################
# FONCTION intersectVector()                                                  #
#########################################################################
#   Role : Récupère les entités d'un fichier shape dans l'emprise d'un autre fichier shape (polygone)
#   Paramètres :
#       vector_emprise : fichier shape d'emprise
#       vector_input : le fichier shape à intersecter
#       vector_output:  le fichiers shape résultat intersecté
#       overwrite: si le fichier existe il est ecrasé (cas par défaut)
#       format_vector : format du fichier vecteur

def intersectVector(vector_emprise, vector_input, vector_output, overwrite=True, format_vector='ESRI Shapefile'):

    if debug >=2:
        print(cyan + "intersectVector() : " + endC + "Intersect par le fichier shape : " + str(vector_emprise))

    check = os.path.isfile(vector_output)
    if check and not overwrite :
        print(cyan + "intersectVector() : " + bold + yellow + "Output file " + str(vector_output) + " already exists." + '\n' + endC)
    else:
        # Récupération du driver
        driver = ogr.GetDriverByName(format_vector)

        # Tenter de supprimer le fichier
        try:
            driver.DeleteDataSource(vector_output)
        except Exception:
            # Ignore l'exception levee si le fichier n'existe pas (et ne peut donc pas être supprime)
            pass

        # Ouverture en mode lecture du fichier d'entrée (vector_input, 0)
        data_source_input = driver.Open(vector_input, 0)
        if data_source_input is None:
            print(cyan + "intersectVector() : " + bold + red + "Could not open file " + str(vector_input) + endC, file=sys.stderr)
            sys.exit(1)
        layer_input = data_source_input.GetLayer()
        name_layer_input = layer_input.GetName()
        feature_input = layer_input.GetNextFeature()

        # Ouverture en mode lecture du fichier différencié (vector_emprise, 0)
        data_source_intersect = driver.Open(vector_emprise, 0)
        if data_source_intersect is None:
            print(cyan + "intersectVector() : " + bold + red + "Could not open file " + str(vector_emprise) + endC, file=sys.stderr)
            sys.exit(1)
        layer_intersect = data_source_intersect.GetLayer()

        # CREATION DU FICHIER DE SORTIE
        # Recupération du srs de la couche en entrée et assignation du système de projection du fichier en sortie
        output_srs=layer_input.GetSpatialRef()

        # Verification si le le fichier de sortie existe déjà (si oui le supprimer)
        if os.path.exists(vector_output):
            driver.DeleteDataSource(vector_output)

        # Création du fichier "DataSource"
        data_source_output = driver.CreateDataSource(vector_output)

        # Création du fichier "couche"(nom, projection, type de géométrie)
        geometry_input = feature_input.GetGeometryRef()
        test_geom_input = geometry_input.GetGeometryName()
        if test_geom_input == 'POLYGON' or test_geom_input == 'MULTIPOLYGON':
            layer_output = data_source_output.CreateLayer(name_layer_input, output_srs, geom_type=ogr.wkbPolygon)
        elif test_geom_input == 'LINESTRING' or test_geom_input == 'MULTILINESTRING':
            layer_output = data_source_output.CreateLayer(name_layer_input, output_srs, geom_type=ogr.wkbLineString)
        elif test_geom_input == 'POINT' or test_geom_input == 'MULTIPOINT':
            layer_output = data_source_output.CreateLayer(name_layer_input, output_srs, geom_type=ogr.wkbPoint)

        # Création du modèle d'"éléments" à partir des caractéristiques de la couche (type de géométrie : polygone...)
        defn_layer_output = layer_output.GetLayerDefn()

        # Ajout des champs du fichier d'entrée au fichier de sortie
        featureID = 0
        defn_layer_input = layer_input.GetLayerDefn()
        nb_fields = defn_layer_input.GetFieldCount()
        for i in range(0, nb_fields):
            field_defn = defn_layer_input.GetFieldDefn(i)
            layer_output.CreateField(field_defn)

        # Parcours des éléments du fichier d'entrée
        while feature_input:

            layer_intersect.ResetReading()
            # Récupération de la géométrie de l'élément du fichier d'entrée
            geometry_input = feature_input.GetGeometryRef()
            feature_intersect = layer_intersect.GetNextFeature()

            # Parcours des éléments du fichier d'intersect
            while feature_intersect:
                # Récupération de la géométrie de l'élément du fichier d'intersect
                geometry_intersect = feature_intersect.GetGeometryRef()

                # Si les géométries des éléments des fichiers d'entrée et d'intersect se croisent (=1)
                if geometry_input.Intersects(geometry_intersect) == 1: # Variante possible avec Overlaps
                    # Différence avec la fonction cutVector : on garde le polygone sélectionné entier, on ne le découpe pas à l'emprise !
                    geom_output = geometry_input
                    test_geom_output = geom_output.GetGeometryName()

                    if test_geom_input == test_geom_output:

                        # Création de l'élément de sortie selon le modèle
                        feature_output = ogr.Feature(defn_layer_output)

                        # Assignation d'un numéro de FID à ce nouvel élément
                        feature_output.SetFID(featureID)
                        featureID += 1

                        # Pour tous les Champs
                        for j in range(0, nb_fields):
                            field_label = feature_input.GetFieldAsString(j)
                            feature_output.SetField(j, field_label)

                        # Assignation de la géométrie de découpage à l'élément de sortie
                        feature_output.SetGeometry(geom_output)

                        # Création de ce nouvel élément
                        layer_output.CreateFeature(feature_output)
                        layer_output.SyncToDisk()
                        feature_output.Destroy()

                feature_intersect.Destroy()
                feature_intersect = layer_intersect.GetNextFeature()

            # Passer à l'élément d'entrée suivant
            feature_input.Destroy()
            feature_input = layer_input.GetNextFeature()

        # Fermeture des fichiers shape
        data_source_input.Destroy()
        data_source_intersect.Destroy()
        data_source_output.Destroy()

    if debug >=2:
        print(cyan + "intersectVector() : " + endC + "Le fichier vecteur " + vector_input  + " a ete intersecte resultat : " + vector_output)
    return

#########################################################################
# FONCTION differenceVector()                                           #
#########################################################################
#   Role : Différencier un fichier shape par un autre fichier shape (polygone)
#   Paramètres :
#       vector_diff : fichier shape de différenciation
#       vector_input : le fichier shape à découper
#       vector_output:  le fichiers shape résultat découpé
#       overwrite: si le fichier existe il est ecrasé (cas par défaut)
#       format_vector : format du fichier vecteur

def differenceVector(vector_diff, vector_input, vector_output, overwrite=True, format_vector='ESRI Shapefile'):

    if debug >=2:
        print(cyan + "differenceVector() : " + endC + "Difference par le fichier shape : " + str(vector_diff))

    check = os.path.isfile(vector_output)
    if check and not overwrite :
        print(cyan + "differenceVector() : " + bold + yellow + "Output file " + str(vector_output) + " already exists." + '\n' + endC)
    else:
        # Récupération du driver
        driver = ogr.GetDriverByName(format_vector)

        # Tenter de supprimer le fichier
        try:
            driver.DeleteDataSource(vector_output)
        except Exception:
            # Ignore l'exception levee si le fichier n'existe pas (et ne peut donc pas être supprime)
            pass

        # Ouverture en mode lecture du fichier d'entrée (vector_input, 0)
        data_source_input = driver.Open(vector_input, 0)
        if data_source_input is None:
            print(cyan + "differenceVector() : " + bold + red  + "Could not open file " + str(vector_input) + endC, file=sys.stderr)
            sys.exit(1)
        layer_input = data_source_input.GetLayer()
        name_layer_input = layer_input.GetName()
        feature_input = layer_input.GetNextFeature()

        # Ouverture en mode lecture du fichier différencié (vector_diff, 0)
        data_source_diff = driver.Open(vector_diff, 0)
        if data_source_diff is None:
            print(cyan + "differenceVector() : " + bold + red  + "Could not open file " + str(vector_diff) + endC, file=sys.stderr)
            sys.exit(1)
        layer_diff = data_source_diff.GetLayer()

        # CREATION DU FICHIER DE SORTIE
        # Recupération du srs de la couche en entrée et assignation du système de projection du fichier en sortie
        output_srs=layer_input.GetSpatialRef()

        # Verification si le le fichier de sortie existe déjà (si oui le supprimer)
        if os.path.exists(vector_output):
            driver.DeleteDataSource(vector_output)
        data_source_output = driver.CreateDataSource(vector_output)   # Création du fichier "DataSource"

        # Création du fichier "couche"(nom, projection, type de géométrie)
        geometry_input = feature_input.GetGeometryRef()
        test_geom_input = geometry_input.GetGeometryName()
        if test_geom_input == 'POLYGON' or test_geom_input == 'MULTIPOLYGON':
            layer_output = data_source_output.CreateLayer(name_layer_input, output_srs, geom_type=ogr.wkbPolygon)
        elif test_geom_input == 'LINESTRING' or test_geom_input == 'MULTILINESTRING':
            layer_output = data_source_output.CreateLayer(name_layer_input, output_srs, geom_type=ogr.wkbLineString)
        elif test_geom_input == 'POINT' or test_geom_input == 'MULTIPOINT':
            layer_output = data_source_output.CreateLayer(name_layer_input, output_srs, geom_type=ogr.wkbPoint)

        # Creation du modèle d'"éléments" à partir des caractéristiques de la couche (type de géométrie : polygone...)
        defn_layer_output = layer_output.GetLayerDefn()

        # Ajout des champs du fichier d'entrée au fichier de sortie
        featureID = 0
        defn_layer_input = layer_input.GetLayerDefn()
        nb_fields = defn_layer_input.GetFieldCount()
        for i in range(0, nb_fields):
            field_defn = defn_layer_input.GetFieldDefn(i)
            layer_output.CreateField(field_defn)

        # Parcours des éléments du fichier d'entrée
        while feature_input:

            layer_diff.ResetReading()
            # Récupération de la géométrie de l'élément du fichier d'entrée
            geometry_input = feature_input.GetGeometryRef()
            geometry_output = geometry_input.Clone()
            feature_diff = layer_diff.GetNextFeature()

            # Parcours des éléments du fichier différencié
            while feature_diff:
                # Récupération de la géométrie de l'élément du fichier différencié
                geometry_diff = feature_diff.GetGeometryRef()

                # Si les géométries des éléments des fichiers d'entrée et différencié se croisent (=1)
                if geometry_input.Intersects(geometry_diff) == 1: # Variante possible avec Overlaps

                    # Différencier geometry_input de geometry_diff
                    geometry_output = geometry_output.Difference(geometry_diff)

                feature_diff.Destroy()
                feature_diff = layer_diff.GetNextFeature()

            # Création de l'élément (du polygone) de sortie selon le modèle
            feature_output = ogr.Feature(defn_layer_output)

            # Assignation d'un numéro de FID à ce nouvel élément
            feature_output.SetFID(featureID)
            featureID += 1

            # Pour tous les Champs
            for j in range(0, nb_fields):
                field_label = feature_input.GetFieldAsString(j)
                feature_output.SetField(j, field_label)

            # Assignation de la géométrie différenciée à l'élément de sortie
            feature_output.SetGeometry(geometry_output)

            # Création de ce nouvel élément
            layer_output.CreateFeature(feature_output)
            layer_output.SyncToDisk()
            feature_output.Destroy()

            feature_input.Destroy()
            feature_input = layer_input.GetNextFeature()

        # Fermeture des fichiers shape
        data_source_input.Destroy()
        data_source_diff.Destroy()
        data_source_output.Destroy()

    if debug >=2:
        print(cyan + "differenceVector() : " + endC + "Le fichier vecteur " + vector_input  + " a ete différencie resultat : " + vector_output)
    return

#########################################################################
# FONCTION splitVector()                                                #
#########################################################################
#   Role : créer un nouveau vecteur pour chaque objet du vecteur en entrée
#   Paramètres en entrée :
#       vector_input : vecteur à diviser
#       dir_output : repertoire dans lequel mettre les nouveaux vecteurs
#       field : optionnel : nom du champ dont on veut recupérer la valeur dans chaque nom de vecteur créé
#               si non renseigné, il prendra comme valeur les premiers entiers (0, 1, 2, ...)
#       projection : code EPSG du fichier en sortie
#       format_vector : format du fichier vecteur. Optionnel, par default : 'ESRI Shapefile'
#       extension_vector : valeur de l'extention du fichier vecteur en fonction du format, par defaut : '.shp'
#   En sortie :
#       retour la liste des chemins des fichiers shapes créés

def splitVector(vector_input, dir_output, field="", projection=2154, format_vector='ESRI Shapefile', extension_vector='.shp') :

    if debug >=2:
        print(cyan + "splitVector() : " + endC + "Vecteur à diviser pour chaque polygones: " + vector_input)

    # Récupération dela input_layer et de ses propriétés
    driver = ogr.GetDriverByName(format_vector)
    data_source_input = driver.Open(vector_input, 0)
    input_layer = data_source_input.GetLayer()
    input_layer_definition = input_layer.GetLayerDefn()

    if not os.path.exists(dir_output):
        os.makedirs(dir_output)

    # Récupération des champs de input_layer dans une liste
    attribute_dico = {}

    for i in range(input_layer_definition.GetFieldCount()):
        field_defn = input_layer_definition.GetFieldDefn(i)
        name_attribute = field_defn.GetName()
        attribute_type = field_defn.GetType()
        attribute_dico[name_attribute] = attribute_type

    index = 0
    path_list = []

    # Parcours des entités de input_layer
    for feature_input in input_layer:
        if field == "" :
            entite = index
        elif field != "":
            try :
                feature_input.GetField(field)
            except ValueError:
                print(cyan + "splitVector() : " + bold + red  + "Pas de champ portant ce nom : " + str(field) + endC, file=sys.stderr)
                sys.exit(1)
            entite = feature_input.GetField(field)

        # Récupération de la géométrie de l'élément du fichier d'entrée
        geometry = feature_input.GetGeometryRef()

        # Création d'un shape par entité de input_layer
        new_shape = dir_output + os.sep + os.path.splitext(os.path.basename(vector_input))[0] + "_" + str(entite) + extension_vector
        path_list.append(str(new_shape))

        # Récupération des valeur des champs du fichier d'entrée
        poly_attr_dico = {}
        for i in range(input_layer_definition.GetFieldCount()):
            field_defn = input_layer_definition.GetFieldDefn(i)
            name_attribute = field_defn.GetName()
            attribute_value = feature_input.GetField(i)
            poly_attr_dico[name_attribute] = attribute_value

        # Create shape
        polygons_attr_geom_dico = {}
        poly_info_list = [geometry.Clone(), poly_attr_dico]
        polygons_attr_geom_dico[str(entite)] = poly_info_list
        createPolygonsFromGeometryList(attribute_dico, polygons_attr_geom_dico, new_shape, projection, format_vector)

        # Mise a jour de l'index
        index += 1

    # Fermeture du fichier shape entrée
    data_source_input.Destroy()

    if debug >=2:
        print(cyan + "splitVector() : " + endC + "Le fichier vecteur " + vector_input  + " a ete divise resultats dans le dodssier : " + dir_output)

    return path_list

#########################################################################
# FONCTION createGridVector()                                           #
#########################################################################
#   Rôle : Cette fonction permet de créer une couche vecteur de type grille contenant des polygones dont les coordonnées sont spécifiées dans une liste
#   paramètres :
#       vector_input : fichier vecteur définissant la zone de travail
#       vector_output : fichier vecteur de sortie contenant la grille de polygones
#       dim_grid_x : taille en x de la grille en mêtre (colonnes)
#       dim_grid_y : taille en y de la grille en mêtre (lignes)
#       attribute_dico : dictionaire contenent la liste des noms des attributs et leur type sous forme ogr.OFTString, ogr.OFTInterger, ogr.OFTReal..., par defaut a None
#       overwrite : écrase si un fichier existant a le même nom qu'un fichier de sortie, par defaut a True
#       projection : Optionnel : par défaut 2154
#       format_vector : format du fichier vecteur. Optionnel, par default : 'ESRI Shapefile'
#   Paramétres de retour :
#       le nombre de polygone créer
#

def createGridVector(vector_input, vector_output, dim_grid_x, dim_grid_y, attribute_dico=None, overwrite=True, projection=2154, format_vector='ESRI Shapefile') :

    if debug >=2:
        print(cyan + "createGridVector() : " + endC + "Création d'un vecteur grille à partir de coordonnées sur la zone du vecteur : " + vector_input)

    poly_index = 0

    # Certains champs sont obligatoires
    if attribute_dico is None:
        attribute_dico = {}
    attribute_dico["id"] = ogr.OFTInteger
    attribute_dico["x_origin"] = ogr.OFTReal
    attribute_dico["y_origin"] = ogr.OFTReal
    attribute_dico["id_ligne"] = ogr.OFTInteger
    attribute_dico["id_colonne"] = ogr.OFTInteger
    attribute_dico["sub_name"] = ogr.OFTString

    # Calcul de la grille
    check = os.path.isfile(vector_output)
    if check and not overwrite :
        print(cyan + "createGridVector() : " + bold + yellow + "Vector grid " + str(vector_output) + " already exists." + '\n' + endC)
    else:
        # Create driver ogr
        driver = ogr.GetDriverByName(format_vector)

        # Tenter de supprimer le fichier
        try:
            driver.DeleteDataSource(vector_output)
        except Exception:
            # Ignore l'exception levee si le fichier n'existe pas (et ne peut donc pas être supprime)
            pass

        print(cyan + "createGridVector() : " + bold + green + "Create grid vector..." + '\n' + endC)

        # Récupération de l'emprise du vecteur de la d'étude
        xmin, xmax, ymin, ymax = getEmpriseFile(vector_input, format_vector)

        if debug >= 4:
            print(bold + "Emprise du fichier '%s' :" % (vector_input) + endC)
            print("    xmin = " + str(xmin))
            print("    xmax = " + str(xmax))
            print("    ymin = " + str(ymin))
            print("    ymax = " + str(ymax))
            print("\n")

        # Création de la liste des valeurs de x pour la mise en place de la grille
        x_list = [xmin] # Initialisation de la liste
        x = xmin # Définition de la valeur du 1er x à entrer dans la boucle
        while x < (xmax - dim_grid_x): # On boucle tant que la valeur de x ne dépasse pas le xmax du fichier raster en entrée
            x = x + dim_grid_x
            x_list.append(x) # Ajout de la nouvelle valeur de x dans la liste
        x_list.append(xmax) # Ajout du dernier inferieur au pas de la grille
        if debug >= 4:
            print(bold + "x_list : "  + endC + str(x_list) + "\n")

        # Création de la liste des valeurs de y pour la mise en place de la grille
        y_list = [ymax] # Initialisation de la liste
        y = ymax # Définition de la valeur du 1er y à entrer dans la boucle
        while y > (ymin + dim_grid_y): # On boucle tant que la valeur de y ne descend pas en-dessous du ymin du fichier raster en entrée
            y = y - dim_grid_y
            y_list.append(y) # Ajout de la nouvelle valeur de y dans la liste
        y_list.append(ymin) # Ajout du dernier inferieur au pas de la grille
        if debug >= 4:
            print(bold + "y_list : " + endC + str(y_list) + "\n")

        # Creation de la liste de coordonnées des polygones
        polygons_attr_coord_dico = {}
        id_colonne = 0
        for i in range(len(x_list)-1):
            id_colonne+=1
            id_ligne = 0
            for j in range(len(y_list)-1):
                id_ligne+=1
                sub_name = "l" + str(id_ligne) + "c" + str(id_colonne)
                x = x_list[i]
                y = y_list[j]
                x_next = x_list[i+1]
                y_next = y_list[j+1]
                x1 = x                                         # x1,y1          x2,y2
                y1 = y                                         #    ---------------
                x2 = x_next                                    #    |             |
                y2 = y                                         #    |             |
                x3 = x_next                                    #    |             |
                y3 = y_next                                    #    |             |
                x4 = x                                         #    ---------------
                y4 = y_next                                    # x4,y4          x3,y3
                coord_list = [x1,y1,x2,y2,x3,y3,x4,y4]
                poly_index = i + (j * (len(x_list)-1)) + 1
                poly_attr_dico = {"id":poly_index,"x_origin":x1,"y_origin":y1,"id_ligne":id_ligne,"id_colonne":id_colonne,"sub_name":sub_name}
                poly_info_list = [coord_list, poly_attr_dico]
                polygons_attr_coord_dico[str(poly_index)] = poly_info_list

        # Create file
        createPolygonsFromCoordList(attribute_dico, polygons_attr_coord_dico, vector_output, projection=projection, format_vector=format_vector)

        if debug >=2:
            print(cyan + "createGridVector() : " + endC + "Le fichier grille vecteur " + vector_output  + " a ete creer sur la zone : " + vector_input)
    if poly_index > 0 :
        poly_index += 1
    return poly_index

#########################################################################
# FONCTION createPolygonsFromCoordList()                                #
#########################################################################
#   Rôle : Cette fonction permet de créer une couche vecteur contenant des polygones dont les coordonnées sont spécifiées dans une liste
#   paramètres :
#       attribute_dico : dictionaire contenent la liste des noms des attributs et leur type sous forme ogr.OFTString, ogr.OFTInteger, ogr.OFTReal...
#       polygons_attr_coord_dico : dictionaire contenent pour chaque polygonne la liste des valeurs des attributs et la de liste des coordonnées x, y
#                                  de la forme {1:[[x1,y1,x2,y2,x3,y3,...],{attr11:val11,attr12:val12,...}],2:[[x1,y1,x2,y2,x3,y3,...],{attr21:val21,attr22:val22,...}],...} (pas nécessaire de "fermer" les polygones)
#       vector_output : fichier vecteur de sortie contenant les polygones
#       projection : Optionnel : par défaut 2154
#       format_vector : format du fichier vecteur. Optionnel, par default : 'ESRI Shapefile'
#

def createPolygonsFromCoordList(attribute_dico, polygons_attr_coord_dico, vector_output, projection=2154, format_vector='ESRI Shapefile'):

    if debug >=2:
        print(cyan + "createPolygonsFromCoordList() : " + endC + "Creation d'une couche de polygones à partir d'une liste de coordonnées")

    # Initialisation du fichier de sortie
    driver = ogr.GetDriverByName(format_vector)

    # Création du dossier de sortie s'il n'existe pas
    if not os.path.exists(os.path.split(vector_output)[0]):
        os.makedirs(os.path.split(vector_output)[0])

    # Suppression du fichier s'il existe déjà
    if os.path.exists(vector_output):
        driver.DeleteDataSource(vector_output)

    # Initialisations pour la création du fichier de sortie
    data_source_output = driver.CreateDataSource(vector_output)
    name_layer_output = os.path.splitext(os.path.basename(vector_output))[0]
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(projection)
    layer_output = data_source_output.CreateLayer(name_layer_output, srs, ogr.wkbPolygon)

    # Création des champs du fichier de sortie
    for name_attribute in attribute_dico:
        # recuperer le type du champs
        if debug >= 4 :
           print(cyan + "createPolygonFromCoordList() : " + endC + "Attribut créé : " + name_attribute)
        attribute_type = attribute_dico[name_attribute]
        field = ogr.FieldDefn(name_attribute, attribute_type)
        layer_output.CreateField(field)

    # Pour tous les polygones à créer
    for poly_index in polygons_attr_coord_dico:
        coord_list = polygons_attr_coord_dico[poly_index][0]
        poly_attr_dico = polygons_attr_coord_dico[poly_index][1]

        if len(coord_list) % 2 != 0:
            print(cyan + "createPolygonFromCoordList() : " + endC + bold + yellow + "Erreur : pas autant de x que de y dans la liste" + endC)
        else:

            # Création de la géométrie
            coord = ""
            for i in range(len(coord_list)):
                if i%2 == 0:
                    coord += str(coord_list[i])+" "
                else:
                    coord += str(coord_list[i])+","
            coord += str(coord_list[0])+" "+str(coord_list[1])
            wkt = "POLYGON(("+coord+"))"
            if debug >= 5 :
                print(cyan + "createPolygonFromCoordList() : " + endC + "Polygone créé : " + wkt)
            geom_output = ogr.CreateGeometryFromWkt(wkt)

            # Ajout de la géométrie dans la couche de sortie
            feature_output = ogr.Feature(layer_output.GetLayerDefn())
            feature_output.SetGeometry(geom_output)

            # Ajout des valeurs d'attribut au polygone
            for attr in poly_attr_dico :
                feature_output.SetField(attr, poly_attr_dico[attr])

            # Creation de la feature de sortie
            layer_output.CreateFeature(feature_output)

    # Fermeture du fichier shape
    layer_output.SyncToDisk()
    data_source_output.Destroy()

    if debug >=2:
        print(cyan + "createPolygonsFromCoordList() : " + endC + "Le fichier vecteur resultat : " +  str(vector_output))

    return

#########################################################################
# FONCTION createPolygonsFromGeometryList()                             #
#########################################################################
#   Rôle : Cette fonction permet de créer une couche vecteur contenant des polygones dont les géometries sont spécifiées dans une liste
#   paramètres :
#       attribute_dico : dictionaire contenent la liste des noms des attributs et leur type sous forme ogr.OFTString, ogr.OFTInteger, ogr.OFTReal...
#       polygons_attr_geom_dico : dictionaire contenent pour chaque polygonne la liste des valeurs des attributs et la de liste des géometries
#                                 de la forme {1:[geom1,{attr11:val11,attr12:val12,...}],2:[geom2,{attr21:val21,attr22:val22,...}],...}
#       vector_output : fichier vecteur de sortie contenant les polygones
#       projection : Optionnel : par défaut 2154
#       format_vector : format du fichier vecteur. Optionnel, par default : 'ESRI Shapefile'
#

def createPolygonsFromGeometryList(attribute_dico, polygons_attr_geom_dico, vector_output, projection=2154, format_vector='ESRI Shapefile'):

    if debug >=2:
        print(cyan + "createPolygonsFromGeometryList() : " + endC + "Creation d'une couche de polygones à partir d'une liste de géometrie")

    # Initialisation du fichier de sortie
    driver = ogr.GetDriverByName(format_vector)

    # Création du dossier de sortie s'il n'existe pas
    if not os.path.exists(os.path.split(vector_output)[0]):
        os.makedirs(os.path.split(vector_output)[0])

    # Suppression du fichier s'il existe déjà
    if os.path.exists(vector_output):
        driver.DeleteDataSource(vector_output)

    # Initialisations pour la création du fichier de sortie
    data_source_output = driver.CreateDataSource(vector_output)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(projection)
    layer_output = data_source_output.CreateLayer(os.path.splitext(os.path.basename(vector_output))[0], srs, ogr.wkbPolygon)

    # Création des champs du fichier de sortie
    for name_attribute in attribute_dico:
        # recuperer le type du champs
        if debug >= 4 :
           print(cyan + "createPolygonsFromGeometryList() : " + endC + "Attribut créé : " + name_attribute)
        attribute_type = attribute_dico[name_attribute]
        field = ogr.FieldDefn(name_attribute, attribute_type)
        layer_output.CreateField(field)

    # Pour tous les polygones à créer
    for poly_index in polygons_attr_geom_dico:
        geom = polygons_attr_geom_dico[poly_index][0]
        poly_attr_dico = polygons_attr_geom_dico[poly_index][1]
        if geom.GetGeometryName() != 'POLYGON' and geom.GetGeometryName() != 'MULTIPOLYGON' :
            print(cyan + "createPolygonsFromGeometryList() : " + endC + bold + yellow + "Erreur : geometrie type non valide : " + str(geom.GetGeometryName()) + endC)
            print(geom)
        else:

            # Création de la géométrie de sortie
            geom_output = geom.Clone()
            feature_output = ogr.Feature(layer_output.GetLayerDefn())
            feature_output.SetGeometry(geom_output)

            # Ajout des valeurs d'attribut au polygone
            for attr in poly_attr_dico :
                feature_output.SetField(attr, poly_attr_dico[attr])

            # Creation de la feature de sortie
            layer_output.CreateFeature(feature_output)

    # Fermeture du fichier shape
    layer_output.SyncToDisk()
    data_source_output.Destroy()

    if debug >=2:
        print(cyan + "createPolygonsFromGeometryList() : " + endC + "Le fichier vecteur resultat : " +  str(vector_output))

    return

#########################################################################
# FONCTION createPointsFromCoordList()                                  #
#########################################################################
#   Rôle : Cette fonction permet de créer une couche vecteur contenant des points dont les coordonnées et leurs valeurs sont spécifiées dans une liste de type dico
#   paramètres :
#       attribute_dico : dictionaire contenent la liste des noms des attributs et leur type sous forme ogr.OFTString, ogr.OFTInteger, ogr.OFTReal...
#       points_attr_coord_dico : dictionaire contenent pour chaque point la liste des coordonnées x, y et la liste des valeurs de chaque attributs de la forme {1:[x1,y1],{"ValClass:val1},2:[[x2,y2],{"ValClass:val2}],3:[[x3,y3],{"ValClass:val3}]...}
#       vector_output : fichier vecteur de sortie contenant les points
#       projection : Optionnel : par défaut 2154
#       format_vector : format du fichier vecteur. Optionnel, par default : 'ESRI Shapefile'
#

def createPointsFromCoordList(attribute_dico, points_attr_coord_dico, vector_output, projection=2154, format_vector='ESRI Shapefile'):

    if debug >=2:
        print(cyan + "createPointsFromCoordList() : " + endC + "Creation d'une couche de points à partir d'une liste de coordonnées")

    # Create driver ogr
    driver = ogr.GetDriverByName(format_vector)

    # Création du dossier de sortie s'il n'existe pas
    if not os.path.exists(os.path.split(vector_output)[0]):
        os.makedirs(os.path.split(vector_output)[0])

    # Suppression du fichier s'il existe déjà
    if os.path.exists(vector_output):
        driver.DeleteDataSource(vector_output)

    # Initialisations pour la création du fichier de sortie
    data_source_output = driver.CreateDataSource(vector_output)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(projection)
    layer_output = data_source_output.CreateLayer(vector_output, srs, ogr.wkbPoint)

    # Création des champs du fichier de sortie
    for name_attribute in attribute_dico:
        # recuperer le type du champs
        if debug >= 4 :
           print(cyan + "createPointsFromCoordList() : " + endC + "Attribut créé : " + name_attribute)
        attribute_type = attribute_dico[name_attribute]
        field = ogr.FieldDefn(name_attribute, attribute_type)
        layer_output.CreateField(field)

    # Création des points
    for index_key in points_attr_coord_dico:
        # Recuperer les valeurs des coordonnees
        coord_list = points_attr_coord_dico[index_key][0]
        point_attr_dico = points_attr_coord_dico[index_key][1]
        pos_x = coord_list[0]
        pos_y = coord_list[1]

        # Création de la géometrie point
        wkt = "POINT(" + str(pos_x) + " " + str(pos_y) + ")"
        geom_output = ogr.CreateGeometryFromWkt(wkt)

        # Ajout de la géométrie
        feature_output = ogr.Feature(layer_output.GetLayerDefn())
        feature_output.SetGeometry(geom_output)

        # Ajout des valeurs d'attribut du point
        for attr in point_attr_dico :
            feature_output.SetField(attr, point_attr_dico[attr])

        # Ajout de toutes données du point dans la couche de sortie
        layer_output.CreateFeature(feature_output)

    # Fermeture du fichier shape
    layer_output.SyncToDisk()
    data_source_output.Destroy()

    if debug >=2:
        print(cyan + "createPointsFromCoordList() : " + endC + "Le fichier vecteur resultat : " +  str(vector_output))

    return
