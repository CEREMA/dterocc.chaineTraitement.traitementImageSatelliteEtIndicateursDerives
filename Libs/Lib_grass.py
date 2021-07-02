# -*- coding: utf-8 -*-
#!/usr/bin/python

#############################################################################
# Copyright (©) CEREMA/DTerSO/DALETT/SCGSI  All rights reserved.            #
#############################################################################

#############################################################################
#                                                                           #
# FONCTIONS POUR L'APPEL À DES FONCTIONS GRASS                              #
#                                                                           #
#############################################################################

import sys,os,shutil,glob, time, subprocess
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC
from Lib_file import deleteDir
from Lib_operator import switch, case
import grass.script as grass
import grass.script.setup as gsetup

# debug = 0 : affichage minimum de commentaires lors de l'exécution du script
# debug = 3 : affichage maximum de commentaires lors de l'exécution du script. Intermédiaire : affichage intermédiaire

debug = 3

# ATTENTION : pour appeler GRASS, il faut avoir mis à jour le fichier .profile (/home/scgsi/.profile). Ajouter à la fin du fichier (attention au numéro de version de GRASS qui peut changer, ici 7.2) :
'''
# Paramétrages GRASS :
export GISBASE="/usr/lib/grass72"
export PATH="$PATH:$GISBASE/bin:$GISBASE/scripts"
export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:$GISBASE/lib"
export GIS_LOCK=$$
export GISRC="$HOME/.grass7"
export PYTHONPATH="$PYTHONPATH:$GISBASE/etc/python"
'''

#########################################################################
# FONCTION connectionGrass()                                            #
#########################################################################
#   Rôle : Permet l'initialisation si la base GRASS avant création ou la connexion à une base GRASS déjà créer
#   Paramètres :
#       gisbase : variable d'environnement de GRASS. Par défaut, os.environ['GISBASE'].
#       gisdb : nom de la géodatabase, 1er niveau. Par défaut, "GRASS_database".
#       location : nom du secteur de la géodatabase, 2ème niveau. Par défaut, "".
#       mapset : nom du jeu de cartes de la géodatabase, 3ème niveau. Par défaut, "PERMANENT".
#       projection : code EPSG (entier), de l'espace de travail. Par défaut, 2154.

def connectionGrass(gisbase, gisdb, location="", mapset="PERMANENT", projection=2154) :
    if location == "" :
        gsetup.init(gisbase, gisdb)
    else :
        if not os.path.exists(gisdb + os.sep + location):
            grass.core.create_location(gisdb, location, projection)
        gsetup.init(gisbase, gisdb, location, mapset)
    return

#########################################################################
# FONCTION initializeGrass()                                            #
#########################################################################
#   Rôle : Permet la initialisation d'une base GRASS, pour l'appel de fonctions Grass
#   Paramètres :
#       work_dir : dossier de traitement, où seront stockées les données de la géodatabase (généralement, un dossier temporaire)
#       xmin : valeur de l'emprise minimale en X, de l'espace de travail
#       xmax : valeur de l'emprise maximale en X, de l'espace de travail
#       ymin : valeur de l'emprise minimale en Y, de l'espace de travail
#       ymax : valeur de l'emprise maximale en Y, de l'espace de travail
#       pixel_size_x : résolution spatiale en X (largeur), de l'espace de travail
#       pixel_size_y : résolution spatiale en Y (hauteur), de l'espace de travail
#       projection : code EPSG (entier), de l'espace de travail. Par défaut, 2154.
#       gisbase : variable d'environnement de GRASS. Par défaut, os.environ['GISBASE'].
#       gisdb : nom de la géodatabase, 1er niveau. Par défaut, "GRASS_database".
#       location : nom du secteur de la géodatabase, 2ème niveau. Par défaut, "LOCATION".
#       mapset : nom du jeu de cartes de la géodatabase, 3ème niveau. Par défaut, "MAPSET".
#       clean_old : nettoyage de la géodatabase si elle existe déjà. Par défaut, True.
#       overwrite : (option) supprime ou non les fichiers existants ayant le meme nom.

def initializeGrass(work_dir, xmin, xmax, ymin, ymax, pixel_size_x, pixel_size_y, projection=2154, gisbase=os.environ['GISBASE'], gisdb="GRASS_database", location="LOCATION", mapset="MAPSET", clean_old=True, overwrite=True):

    # On récupère le nom du dossier de traitement, dans lequel on rajoute un sous-dossier (1er niveau de la géodatabase)
    gisdb = work_dir + os.sep + gisdb

    if debug >= 2:
        print(cyan + "initializeGrass() : " + bold + green + "Preparation de la geodatabase GRASS dans le dossier : " + endC + work_dir)

    # Nettoyage des données GRASS venant d'un traitement précédent : attention, on repart à 0 !
    if os.path.exists(gisdb) and clean_old:
        deleteDir(gisdb)

    # Création du 1er niveau de la géodatabase : 'gisdb'
    if not os.path.exists(gisdb):
        os.makedirs(gisdb)

    # Initialisation de la connexion à la géodatabase encore vide (pour récupérer les scripts GRASS et créer le 2ème niveau)
    connectionGrass(gisbase, gisdb)

    # Création du 2ème niveau de la géodatabase : 'location', avec un système de coordonnées spécifique
    # Initialisation de la connexion à la géodatabase par défaut (pour créer notre propre 'mapset')
    connectionGrass(gisbase, gisdb, location, 'PERMANENT', projection)

    # Création du 3ème niveau de la géodatabase : 'mapset', avec une emprise et une résolution spatiale spécifiques
    if not os.path.exists(gisdb + os.sep + location + os.sep + mapset):
        os.makedirs(gisdb + os.sep + location + os.sep + mapset)
    grass.run_command('g.region', n=ymax, s=ymin, e=xmax, w=xmin, ewres=abs(pixel_size_x), nsres=abs(pixel_size_y), overwrite=overwrite)

    # Copie des fichiers de paramètres du 'mapset' "PERMANENT" vers le nouveau 'mapset' (pour garder un original, et si on veut travailler dans plusieurs 'mapset')
    for file_to_copy in glob.glob(gisdb + os.sep + location + os.sep + "PERMANENT" + os.sep + "*"):
        shutil.copy(file_to_copy, gisdb + os.sep + location + os.sep + mapset)

    # Initialisation du 'mapset' de travail
    connectionGrass(gisbase, gisdb, location, mapset, projection)

    if debug >= 2:
        print(cyan + "initializeGrass() : " + bold + green + "Geodatabase GRASS prete." + endC)

    # Renvoie les informations de connexion (propres)
    return gisbase, gisdb, location, mapset

#########################################################################
# FONCTION cleanGrass()                                                 #
#########################################################################
#   Rôle : Nettoyage de la géodatabase GRASS
#   Paramètres :
#       work_dir : dossier de traitement, où seront stockées les données de la géodatabase (généralement, un dossier temporaire)
#       gisdb : nom de la géodatabase, 1er niveau. Par défaut, "GRASS_database".
#       save_results_intermediate : (option) fichiers de sorties intermediaires non nettoyées, par defaut = False

def cleanGrass(work_dir, gisdb="GRASS_database", save_results_intermediate=False):
    if not save_results_intermediate :
        shutil.rmtree(os.path.join(work_dir, gisdb))
    return

#########################################################################
# FONCTION importVectorOgr2Grass()                                      #
#########################################################################
#   Rôle : import de données vecteurs (de la librairie OGR) vers la géodatabase GRASS
#   Paramètres :
#       input_vector : fichier vecteur à importer
#       output_name : nom du fichier dans la géodatabase
#       overwrite : (option) supprime ou non les fichiers existants ayant le meme nom.

def importVectorOgr2Grass(input_vector, output_name, overwrite=True):

    if debug >= 2:
        print(cyan + "importVectorOgr2Grass() : " + bold + green + "Import vecteur GRASS : " + endC + input_vector + " vers " + output_name)
    grass.run_command('v.in.ogr', input=input_vector, output=output_name, overwrite=overwrite, stderr=subprocess.PIPE)

    return

#########################################################################
# FONCTION exportVectorOgr2Grass()                                      #
#########################################################################
#   Rôle : export de données vecteurs (de la librairie OGR) depuis la géodatabase GRASS
#   Paramètres :
#       input_name : nom du fichier dans la géodatabase à exporter
#       output_vector : fichier vecteur en sortie
#       format_vector : format du vecteur de sortie (par défaut, 'ESRI_Shapefile')
#       overwrite : (option) supprime ou non les fichiers existants ayant le meme nom.

def exportVectorOgr2Grass(input_name, output_vector, format_vector="ESRI_Shapefile", overwrite=True):

    if debug >= 2:
        print(cyan + "exportVectorOgr2Grass() : " + bold + green + "Export vecteur GRASS : " + endC + input_name + " vers " + output_vector)

    format_vector = format_vector.replace(' ', '_')

    grass.run_command('v.out.ogr', input=input_name, output=output_vector, format=format_vector, overwrite=overwrite, stderr=subprocess.PIPE)

    return

#########################################################################
# FONCTION importRasterGdal2Grass()                                     #
#########################################################################
#   Rôle : import de données rasters (de la librairie GDAL) vers la géodatabase GRASS
#   Paramètres :
#       input_raster : fichier raster à importer
#       output_name : nom du fichier dans la géodatabase
#       overwrite : (option) supprime ou non les fichiers existants ayant le meme nom.

def importRasterGdal2Grass(input_raster, output_name, overwrite=True):

    if debug >= 2:
        print(cyan + "importRasterGdal2Grass() : " + bold + green + "Import raster GRASS : " + endC + input_raster + " vers " + output_name)
    grass.run_command('r.in.gdal', input=input_raster, output=output_name, overwrite=overwrite, stderr=subprocess.PIPE)

    return

#########################################################################
# FONCTION exportRasterGdal2Grass()                                     #
#########################################################################
#   Rôle : export de données rasters (de la librairie GDAL) depuis la géodatabase GRASS
#   Paramètres :
#       input_name : nom du fichier dans la géodatabase à exporter
#       output_raster : fichier raster en sortie
#       format_raster : format du raster en sortie (par défaut, 'GTiff')
#       overwrite : (option) supprime ou non les fichiers existants ayant le meme nom.

def exportRasterGdal2Grass(input_name, output_raster, format_raster="GTiff", overwrite=True):

    if debug >= 2:
        print(cyan + "exportRasterGdal2Grass() : " + bold + green + "Export raster GRASS : " + endC + input_name + " vers " + output_raster)
    grass.run_command('r.out.gdal', input=input_name, output=output_raster, format=format_raster, overwrite=overwrite, stderr=subprocess.PIPE)

    return

#########################################################################
# FONCTION smoothGeomGrass()                                            #
#########################################################################
#   Role : Permet de lisser une géometrie par fonction de GRASS, après connexion à Grass
#   Paramètres :
#       input_vector : fichier vecteur d'entrée contenant les géometrie à lisser
#       output_vector : fichier vecteur de sortie, après traitement GRASS
#       param_generalize_dico : dictionnaire associant le nom du paramètre à sa valeur. Ex : {"method":"chaiken", "threshold":1}
#       format_vector : format du vecteur de sortie (par défaut, 'ESRI_Shapefile')
#       overwrite : (option) supprime ou non les fichiers existants ayant le meme nom.
#
#   # Exemple d'exécution :
#   xmin, xmax, ymin, ymax = getEmpriseFile(input_vector, format_vector)
#   initializeGrass(work_dir, xmin, xmax, ymin, ymax, pixel_size_x, pixel_size_y, projection, gisbase, gisdb, location, mapset, True)
#   param_generalize_dico = {"method":"chaiken", "threshold":1}
#   smoothGeomGrass(input_vector, output_vector, param_generalize_dico, gisbase, gisdb, location, mapset, "ESRI_Shapefile")
#
#  ATTENTION :
#      dans le switch, ajouter les noms des nouveaux paramètres qui n'y sont pas encore

def smoothGeomGrass(input_vector, output_vector, param_generalize_dico, format_vector="ESRI_Shapefile", overwrite=True):
    if debug >= 2:
        print(cyan + "smoothGeomGrass() : " + bold + green + "Lancement de la fonction de lissage par GRASS v.generalize" + endC)

    format_vector = format_vector.replace(' ', '_')

    # Import du vecteur d'entrée
    leng_name_vector_input = len(os.path.splitext(os.path.basename(input_vector))[0])
    if leng_name_vector_input > 16 :
        leng_name_vector_input = 16
    input_name = "VI" + os.path.splitext(os.path.basename(input_vector))[0][0:leng_name_vector_input]
    input_name = input_name.replace('-','_')
    leng_name_vector_output = len(os.path.splitext(os.path.basename(output_vector))[0])
    if leng_name_vector_output > 16 :
        leng_name_vector_output = 16
    output_name = "VO" + os.path.splitext(os.path.basename(output_vector))[0][0:leng_name_vector_output]
    output_name = output_name.replace('-','_')

    importVectorOgr2Grass(input_vector, input_name, overwrite)

    # Traitement avec la fonction v.generalize
    method = None
    threshold = None
    for key in param_generalize_dico:
        while switch(key):
            if case("method"):
                method = param_generalize_dico[key]
                break
            if case("threshold"):
                threshold = param_generalize_dico[key]
                break
    grass.run_command('v.generalize', input=input_name, output=output_name, method=method, threshold=threshold, overwrite=overwrite, stderr=subprocess.PIPE)

    # Export du jeu de données traité
    exportVectorOgr2Grass(output_name, output_vector, format_vector, overwrite)

    return

#########################################################################
# FONCTION splitGrass()                                                 #
#########################################################################
#   Role : Permet de diviser une géometrie par fonction de GRASS, après connexion à Grass
#   Paramètres :
#       input_vector : fichier vecteur d'entrée contenant les géometrie à diviser
#       output_vector : fichier vecteur de sortie, après traitement GRASS
#       param_split_length : distance entre les segments pour la division (en metre)
#       format_vector : format du vecteur de sortie (par défaut, 'ESRI_Shapefile')
#       overwrite : (option) supprime ou non les fichiers existants ayant le meme nom.
#
#   # Exemple d'exécution :
#   xmin, xmax, ymin, ymax = getEmpriseFile(input_vector, format_vector)
#   initializeGrass(work_dir, xmin, xmax, ymin, ymax, pixel_size_x, pixel_size_y, projection, gisbase, gisdb, location, mapset, True)
#   splitGrass(input_vector, output_vector, 10, gisbase, gisdb, location, mapset, "ESRI_Shapefile")
#

def splitGrass(input_vector, output_vector, param_split_length, format_vector="ESRI_Shapefile", overwrite=True):
    if debug >= 2:
        print(cyan + "smoothGeomGrass() : " + bold + green + "Lancement de la fonction de lissage par GRASS v.generalize" + endC)

    format_vector = format_vector.replace(' ', '_')

    # Import du vecteur d'entrée
    leng_name_vector_input = len(os.path.splitext(os.path.basename(input_vector))[0])
    if leng_name_vector_input > 16 :
        leng_name_vector_input = 16
    input_name = "VI" + os.path.splitext(os.path.basename(input_vector))[0][0:leng_name_vector_input]
    leng_name_vector_output = len(os.path.splitext(os.path.basename(output_vector))[0])
    if leng_name_vector_output > 16 :
        leng_name_vector_output = 16
    output_name = "VO" + os.path.splitext(os.path.basename(output_vector))[0][0:leng_name_vector_output]

    importVectorOgr2Grass(input_vector, input_name, overwrite)

    # Traitement avec la fonction v.split
    grass.run_command('v.split', input=input_name, output=output_name, length=param_split_length, overwrite=overwrite, stderr=subprocess.PIPE)

    # Export du jeu de données traité
    exportVectorOgr2Grass(output_name, output_vector, format_vector, overwrite)

    return

#########################################################################
# FONCTION vectorisationGrass()                                         #
#########################################################################
#   Rôle : Permet la vectorisation d'un fichicher raster avec GRASS
#   Paramètres :
#       raster_input : fichier raster à vectoriser
#       vector_output : fichier vecteur en sortie
#       mmu : Mininal Mapping Unit (shapefile area unit) (integer)
#       douglas : option Douglas-Peucker reduction value (integer)
#       hermite : option Hermite smoothing level (integer)
#       angle : Smooth corners of pixels (45°) (boolean) (par défaut, True)
#       format_vector : format du vecteur de sortie (par défaut, 'ESRI_Shapefile')
#       overwrite : (option) supprime ou non les fichiers existants ayant le meme nom.
#
# ATTENTION! (A confirmer!) ne marche que pour des rasters dont le nombre de lignes et de colonnes est limités (max ligne max colonnes à définir)
#
def vectorisationGrass(raster_input, vector_output, mmu, douglas=None, hermite=None, angle=True, format_vector='ESRI_Shapefile', overwrite=True):

    format_vector = format_vector.replace(' ', '_')

    # Import du rasteur d'entrée
    leng_name_raster = len(os.path.splitext(os.path.basename(raster_input))[0])
    if leng_name_raster > 16 :
        leng_name_raster = 16
    name_raster_geobase = "R" + os.path.splitext(os.path.basename(raster_input))[0][0:leng_name_raster]
    leng_name_vector = len(os.path.splitext(os.path.basename(vector_output))[0])
    if leng_name_vector > 16 :
        leng_name_vector = 16
    name_vector_geobase = "V" + os.path.splitext(os.path.basename(vector_output))[0][0:leng_name_vector]

    timeinit = time.time()

    # Import raster dans Grass
    importRasterGdal2Grass(raster_input, name_raster_geobase, overwrite)
    timeimport = time.time()
    if debug >= 2:
        print(cyan + "vectorisationGrass() : " + bold + green + "Importation raster : " + str(timeimport - timeinit) + " seconds" + endC)

    if angle:
        # Vectorization with corners of pixel smoothing
        grass.run_command("r.to.vect", flags = "sv", input=name_raster_geobase, output=name_vector_geobase, type="area", overwrite=overwrite, stderr=subprocess.PIPE)
    else:
        # Vectorization without corners of pixel smoothing
        grass.run_command("r.to.vect", flags = "v",input =name_raster_geobase, output=name_vector_geobase, type="area", overwrite=overwrite, stderr=subprocess.PIPE)
    timevect = time.time()
    if debug >= 2:
        print(cyan + "vectorisationGrass() : " + bold + green + "Vectorization : " + str(timevect - timeimport) + " seconds" + endC)

    inputvector = name_vector_geobase
    # Douglas simplification
    if douglas is not None and not douglas == 0:
        grass.run_command("v.generalize", input = "%s"%(name_vector_geobase), method="douglas", threshold="%s"%(douglas), output=name_vector_geobase+"_Douglas", overwrite=overwrite, stderr=subprocess.PIPE)
        inputvector = name_vector_geobase + "_Douglas"
        timedouglas = time.time()
        if debug >= 2:
            print(cyan + "vectorisationGrass() : " + bold + green + "Douglas simplification : " + str(timedouglas - timevect) + " seconds" + endC)
        timevect = timedouglas

    # Hermine simplification
    if hermite is not None and not hermite == 0:
        grass.run_command("v.generalize", input = "%s"%(inputvector), method="hermite", threshold="%s"%(hermite), output=name_vector_geobase+"_Hermine", overwrite=overwrite, stderr=subprocess.PIPE)
        inputvector = name_vector_geobase + "_Hermine"

        timehermine = time.time()
        if debug >= 2:
            print(cyan + "vectorisationGrass() : " + bold + green + "Hermine smoothing : " + str(timehermine - timevect) + " seconds" + endC)
        timevect = timehermine

    # Delete non class polygons (sea water, nodata and crown entities)
    grass.run_command("v.edit", map="%s"%(inputvector), tool="delete", where="cat < 1", stderr=subprocess.PIPE)

    # Delete under MMU limit
    grass.run_command("v.clean", input="%s"%(inputvector), output=name_vector_geobase+"_Cleanarea", tool="rmarea", thres=mmu, type="area", stderr=subprocess.PIPE)

    # Export vector file
    exportVectorOgr2Grass(name_vector_geobase+"_Cleanarea", vector_output, format_vector, overwrite)

    timeexp = time.time()
    if debug >= 2:
        print(cyan + "vectorisationGrass() : " + bold + green + "Exportation vector : " + str(timeexp - timevect) + "seconds" + endC)

    timeend = time.time()
    if debug >= 2:
        print(cyan + "vectorisationGrass() : " + bold + green + "Global Vectorization and Simplification process : " + str(timeend - timeinit) + " seconds" + endC)

    return

#########################################################################
# FONCTION pointsAlongPolylines()                                       #
#########################################################################
#   Rôle : génération de points le long de polylignes
#   Documentation : https://grass.osgeo.org/grass76/manuals/v.to.points.html
#   Paramètres :
#       vector_input : nom du fichier polylignes en entrée
#       vector_output : nom du fichier points en sortie
#       use : méthode utilisée ['node', 'vertex'] (par défaut, 'node')
#       dmax : distance entre les points (par défaut, 100)
#       percent : utilise 'dmax' comme un pourcentage du polyligne plutôt qu'une distance (par défaut, False)
#       overwrite : (option) supprime ou non les fichiers existants ayant le même nom

def pointsAlongPolylines(vector_input, vector_output, use='node', dmax=100, percent=False, overwrite=True):

    if debug >= 2:
        print(cyan + "pointsAlongPolylines() : " + bold + green + "Génération de points le long de polylignes : " + endC + vector_input + " vers " + vector_output)

    flags = ''
    # Si méthode des sommets
    if use == 'vertex':
        flags += 'i'
    # Si distance en pourcentage
    if percent:
        flags += 'p'

    if flags != '':
        grass.run_command('v.to.points', flags = flags, input = vector_input, output = vector_output, use = use, dmax = dmax, overwrite = overwrite, stderr = subprocess.PIPE)
    else:
        grass.run_command('v.to.points', input = vector_input, output = vector_output, use = use, dmax = dmax, overwrite = overwrite, stderr = subprocess.PIPE)

    return

#########################################################################
# FONCTION sampleRasterUnderPoints()                                    #
#########################################################################
#   Rôle : échantillonnage d'un raster sous un fichier points
#   Documentation : https://grass.osgeo.org/grass76/manuals/v.what.rast.html
#   Paramètres :
#       vector_input : nom du fichier points en entrée (mis à jour en sortie)
#       raster_input : nom du raster en entrée
#       column : colonne du fichier points dans laquelle seront récupérées les valeurs du raster
#       overwrite : (option) supprime ou non les fichiers existants ayant le même nom

def sampleRasterUnderPoints(vector_input, raster_input, column, overwrite=True):

    if debug >= 2:
        print(cyan + "sampleRasterUnderPoints() : " + bold + green + "Echantillonnage d'un raster sous un fichier points : " + endC + vector_input + " à partir de " + raster_input)

    grass.run_command('v.what.rast', map = vector_input, raster = raster_input, column = column, overwrite = overwrite, stderr = subprocess.PIPE)

    return

