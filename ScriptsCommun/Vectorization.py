#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT FAIT UNE VECTORISATION DU FICHIER RASTER DE CLASSIFICATION EN FICHIER VECTEUR                                                      #
#                                                                                                                                           #
#############################################################################################################################################
"""
Nom de l'objet : Vectorization.py
Description :
-------------
Objectif : Créer un fichier vecteur a partir d'un fichier raster
Rq : utilisation des OTB Applications :  otbcli_BandMath, otbcli_MeanShiftSmoothing, otbcli_LSMSSegmentation, otbcli_LSMSSmallRegionsMerging, otbcli_LSMSVectorization

Date de creation : 01/10/2014
----------
Histoire :
----------
Origine : le script originel provient du fichier script_vectorisation.py cree en 2014 scripts annexes
01/10/2014 : Transformation en brique elementaire (suppression des liens avec la chaine OCSOL)
-----------------------------------------------------------------------------------------------------
Modifications :
01/10/2014 : refonte du fichier harmonisation des régles de qualitées des niveaux de boucles et des paramétres dans args
21/05/2015 : simplification des parametres en argument plus de liste d'image en entrée à traiter uniquement une image
30/04/2024 : changement du processus de vectorisation : si correction topologique souhaitée en post-traitement alors correction en postgis + découpage en postgis après vectorisation sinon découpage classique (otb) avant vectorisation
------------------------------------------------------
A Reflechir/A faire :

"""

# Import des bibliothèques python
from __future__ import print_function
import os,sys,glob,argparse
from osgeo import gdal,ogr
from Lib_raster import getPixelSizeImage, getProjectionImage, getEmpriseImage, getPixelWidthXYImage, createBinaryMask, polygonizeRaster
from Lib_vector import relabelVectorFromMajorityPixelsRaster,fusionNeighbourGeometryBySameValue, cutVectorAll, multigeometries2geometries, cleanLabelPolygons, renameFieldsVector
from Lib_grass import initializeGrass, vectorisationGrass, cleanGrass
from Lib_log import timeLine
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_file import removeFile, removeVectorFile, renameVectorFile
from Lib_postgis import openConnection, closeConnection, dropDatabase, createDatabase, importVectorByOgr2ogr, exportVectorByOgr2ogr, topologyCorrections, cutPolygonesByPolygones

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 3

###########################################################################################################################################
# FONCTION vectorizeClassification                                                                                                        #
###########################################################################################################################################
def vectorizeClassification(image_input, vector_output, name_column, umc_list, tilesize, enable_reaffectation_raster, enable_meanshift_filtering, enable_segmentation, enable_small_region_merging, enable_vectorization, enable_boundaries, boundaries_vector, enable_dissolve, enable_reaffectation_vector, enable_cor_bord, wrongval_list, path_time_log, expression="(im1b1==11000?400:(im1b1==12200?100:(im1b1==21000?300:(im1b1==22000?200:im1b1))))", ram_otb=0, format_vector='ESRI Shapefile',  extension_raster=".tif", extension_vector=".shp", save_results_intermediate=False, overwrite=True) :
    """
    # ROLE:
    #     fonction de vectorisation et renseignement des valeurs de classification
    #
    # ENTREES DE LA FONCTION :
    #    image_input : fichier image raster de la classification à vectoriser
    #    vector_output : fichier vecteur résultat de la vectorisation de la classification
    #    name_column : nom de la colonne du fichier shape contenant l'information de classification
    #    umc_list : liste des UMC voulues (en m²). Exemple : umc_list = [200,100,50,20,10]. Mettre un multiple de la surface du pixel
    #               Conversion des UMC en pixels  umc_list[:]=[x/area_pixel for x in umc_list]
    #    tilesize : taille des carreaux minimal de traitement en x et y
    #    enable_reaffectation_raster : activation de la réaffectation du raster
    #    enable_meanshift_filtering : activation du filtre MeanShift
    #    enable_segmentation : activation de la segmentation
    #    enable_small_region_merging : activation du merge des petites régions.
    #    enable_vectorization : activation de la vectorisation
    #    enable_boundaries : activation du decoupage
    #    boundaries_vector : vecteur de découpe
    #    enable_dissolve : activation de la fusion des polygones voisin
    #    enable_reaffectation_vector : activation de la réaffectation du vecteur
    #    enable_cor_bord : activation de la correction des pixels en bord de zone
    #    wrongval_list : liste des valeurs de la colonne name_colonne à enlever
    #    path_time_log : le fichier de log de sortie
    #    expression : expression utilisée pour la réaffectation des labels du raster
    #    ram_otb : memoire RAM disponible pour les applications OTB
    #    format_vector : format du fichier vecteur. Optionnel, par default : 'ESRI Shapefile'
    #    extension_raster : extension des fichiers raster de sortie, par defaut = '.tif'
    #    extension_vector : extension du fichier vecteur de sortie, par defaut = '.shp'
    #    save_results_intermediate : liste des sorties intermediaires nettoyees, par defaut = False
    #    overwrite : supprime ou non les fichiers existants ayant le meme nom
    #
    # SORTIES DE LA FONCTION :
    #    Le fichier vecteur de classification
    #    Eléments modifiés aucun
    #
    """

    # Mise à jour du Log
    starting_event = "vectorizeClassification() : Vectorize classification class starting : "
    timeLine(path_time_log, starting_event)

    if debug >= 3:
        print(cyan + "vectorizeClassification() : " + endC + "image_input : " + str(image_input) + endC)
        print(cyan + "vectorizeClassification() : " + endC + "vector_output : " + str(vector_output) + endC)
        print(cyan + "vectorizeClassification() : " + endC + "name_column : " + str(name_column) + endC)
        print(cyan + "vectorizeClassification() : " + endC + "umc_list : " + str(umc_list) + endC)
        print(cyan + "vectorizeClassification() : " + endC + "tilesize : " + str(tilesize) + endC)
        print(cyan + "vectorizeClassification() : " + endC + "enable_reaffectation_raster : " + str(enable_reaffectation_raster) + endC)
        print(cyan + "vectorizeClassification() : " + endC + "enable_meanshift_filtering : " + str(enable_meanshift_filtering) + endC)
        print(cyan + "vectorizeClassification() : " + endC + "enable_segmentation : " + str(enable_segmentation) + endC)
        print(cyan + "vectorizeClassification() : " + endC + "enable_small_region_merging : " + str(enable_small_region_merging) + endC)
        print(cyan + "vectorizeClassification() : " + endC + "enable_vectorization : " + str(enable_vectorization) + endC)
        print(cyan + "vectorizeClassification() : " + endC + "enable_boundaries : " + str(enable_boundaries) + endC)
        print(cyan + "vectorizeClassification() : " + endC + "boundaries_vector : " + str(boundaries_vector) + endC)
        print(cyan + "vectorizeClassification() : " + endC + "enable_dissolve : " + str(enable_dissolve) + endC)
        print(cyan + "vectorizeClassification() : " + endC + "enable_reaffectation_vector : " + str(enable_reaffectation_vector) + endC)
        print(cyan + "vectorizeClassification() : " + endC + "enable_cor_bord : " + str(enable_cor_bord) + endC)
        print(cyan + "vectorizeClassification() : " + endC + "wrongval_list : " + str(wrongval_list) + endC)
        print(cyan + "vectorizeClassification() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "vectorizeClassification() : " + endC + "expression : " + str(expression) + endC)
        print(cyan + "vectorizeClassification() : " + endC + "ram_otb : " + str(ram_otb) + endC)
        print(cyan + "vectorizeClassification() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "vectorizeClassification() : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "vectorizeClassification() : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "vectorizeClassification() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "vectorizeClassification() : " + endC + "overwrite : " + str(overwrite) + endC)


    # Constantes
    CODAGE = 'uint16'
    SUF_FILTERED = '_filtred'
    SUF_RANGE = '_range'
    SUF_SPAT = '_spat'
    SUF_MASK = '_mask'
    SUF_REAFFECTED = '_reaffected'
    SUF_SEGMENTED = '_segmented'
    SUF_MERGED = '_merged'
    SUF_VECTORISED = '_vectorised'
    SUF_CUTTED = '_cutted'
    SUF_COR = '_cor'
    SUF_MPOLY = '_mpoly'
    SUF_LABELED = '_labeled'
    SUF_DISSOLVED = '_dissolved'
    SUF_M2 = '_m2'

    print(cyan + "\nvectorizeClassification() : " + bold + green + "DEBUT DE LA VECTORISATION" + endC)

    # Definition variables et chemins
    repository = os.path.dirname(vector_output)                                                    # Répertoire temporaire. Ex : repository = D3_Global/Resultats/Vecteurs
    filename = os.path.splitext(os.path.basename(vector_output))[0]                                # Nom de l'etude. Ex : filename = "Ardeche"
    image_raster_mask = repository + os.sep + filename + SUF_MASK + extension_raster                     # Ex : image_raster_mask =      D3_Global/Resultats/Vecteurs/Ardeche_mask.tif
    vector_boundaries_mask = repository + os.sep + filename + SUF_MASK + extension_vector                 # Ex : vector_boundaries_mask = D3_Global/Resultats/Vecteurs/Ardeche_mask.shp
    image_raster = repository + os.sep + filename + SUF_REAFFECTED + extension_raster                                     # Ex : image_raster =           D3_Global/Resultats/Vecteurs/Ardeche.tif
    image_filtered_range = repository + os.sep + filename + SUF_FILTERED + SUF_RANGE + extension_raster  # Ex : image_filtered_range =   D3_Global/Resultats/Vecteurs/Ardeche_filtred_range.tif
    image_filtered_spat = repository + os.sep + filename + SUF_FILTERED + SUF_SPAT + extension_raster    # Ex : image_filtered_spat  =   D3_Global/Resultats/Vecteurs/Ardeche_filtred_spat.tif
    image_segmented = repository + os.sep + filename + SUF_SEGMENTED + extension_raster                  # Ex : image_segmented =        D3_Global/Resultats/Vecteurs/Ardeche_segmented.tif

    area_pixel =  getPixelSizeImage(image_input) # Superficie, en m d'un pixel de l'image. Exemple pour une image à 5m : area_pixel = 25

    print(cyan + "vectorizeClassification() : " + endC + "Surface d'un pixel : ", area_pixel)

    # ETAPE X : PREPARATION DU VECTEUR DE DECOUPE SI IL N'EXISTE PAS
    if enable_boundaries and boundaries_vector == "":
        createBinaryMask(image_input, image_raster_mask, 0, True)
        polygonizeRaster(image_raster_mask, vector_boundaries_mask, filename)
        boundaries_vector = vector_boundaries_mask

    # ETAPE 0 : REAFFECTATION DU RASTEUR
    # Etape (facultative, et déconseillée) de relabellisation des classes
    if enable_reaffectation_raster :

        command = "otbcli_BandMath -il \"%s\" -out %s  %s -exp \"%s\"" %(image_input,image_raster,CODAGE,expression)
        if ram_otb > 0:
            command += " -ram %d" %(ram_otb)

        if debug >=2:
            print(cyan + "vectorizeClassification() : " + bold + green + "ETAPE 0/9 : Debut de la réaffectation raster \n" + endC)
            print(command)

        os.system(command)

        print(cyan + "vectorizeClassification() : " + bold + green + "ETAPE 0/9 : Fin de la reaffectation raster \n" + endC)

    else :
        print(cyan + "vectorizeClassification() : " + bold + yellow + "ETAPE 0/9 : Pas de reaffectation raster - Non demande" + endC)
        image_raster = image_input

    # ETAPE 1 : MEAN SHIFT FILTERING
    if enable_meanshift_filtering :

        command = "otbcli_MeanShiftSmoothing -in %s -fout %s -foutpos %s -spatialr 1 -ranger 1 -thres 0.1 -maxiter 100 -modesearch 0" %(image_raster,image_filtered_range,image_filtered_spat)
        if ram_otb > 0:
            command += " -ram %d" %(ram_otb)

        if debug >=2:
            print(cyan + "vectorizeClassification() : " + bold + green + "ETAPE 1/9 : Debut du lissage de l'image" + endC)
            print(command)

        os.system(command)

        print(cyan + "vectorizeClassification() : " + bold + green + "ETAPE 1/9 : Fin du lissage de l'image \n" + endC)

    else :
        print(cyan + "vectorizeClassification() : " + bold + yellow + "ETAPE 1/9 : Pas de lissage de l image - Non demande" + endC)
        image_filtered_range = image_raster


    # ETAPE 2 : SEGMENTATION
    if enable_segmentation :
        command = "otbcli_LSMSSegmentation -in %s -inpos %s -out %s -ranger 1 -spatialr 1 -minsize 0 -tilesizex %s -tilesizey %s -cleanup 1" %(image_filtered_range,image_filtered_spat,image_segmented, tilesize, tilesize)

        #if ram_otb > 0:
        #    command += " -ram %d" %(ram_otb)

        if debug >=2:
            print(cyan + "vectorizeClassification() : " + bold + green + "ETAPE 2/9 : Debut de la segmentation de l'image" + endC)
            print(command)

        os.system(command)

        print(cyan + "vectorizeClassification() : " + bold + green + "ETAPE 2/9 : Fin de la segmentation de l'image \n" + endC)
    else :
        print(cyan + "vectorizeClassification() : " + bold + yellow + "ETAPE 2/9 : Pas de segmentation de l image - Non demande" + endC)

    # POUR TOUTES LES UMC DEMANDEES
    for umc in umc_list :

        uml_label = str(int(round((umc * area_pixel)/2)))
        uml_label2 = uml_label.replace(".","_")

        # Ex : image_segmented_merged = D3_Global/Resultats/Vecteurs/Ardeche_segmented_merged_500_m2.tif
        image_segmented_merged = repository + os.sep + filename + SUF_SEGMENTED + SUF_MERGED + "_" + uml_label2 + SUF_M2 + extension_raster

        # Ex : vector_segmented_merged = D3_Global/Resultats/Vecteurs/Ardeche_vectorised_500_m2.shp
        vector_segmented_merged = repository + os.sep + filename + SUF_VECTORISED + "_" + uml_label2 + SUF_M2 + extension_vector

        # Ex : vector_segmented_merged_cuted = D3_Global/Resultats/Vecteurs/Ardeche_vectorised_cuted_labeled_500_m2.shp
        vector_segmented_merged_cuted = repository + os.sep + filename + SUF_VECTORISED + SUF_CUTTED + SUF_LABELED + "_" + uml_label2 + SUF_M2 + extension_vector

        # Ex : vector_segmented_merged_cuted_cor = D3_Global/Resultats/Vecteurs/Ardeche_vectorised_cuted_labeled_cor_500_m2.shp
        vector_segmented_merged_cuted_cor = repository + os.sep + filename + SUF_VECTORISED + SUF_CUTTED + SUF_LABELED  + SUF_COR + "_" + uml_label2 + SUF_M2 + extension_vector

        # Ex : vector_segmented_merged_cuted_mpoly = D3_Global/Resultats/Vecteurs/Ardeche_vectorised_cuted_labeled_cor_mpoly_500_m2.shp
        vector_segmented_merged_cuted_mpoly = repository + os.sep + filename + SUF_VECTORISED + SUF_CUTTED + SUF_LABELED  + SUF_COR + SUF_MPOLY + "_" + uml_label2 + SUF_M2 + extension_vector

        # Ex : vector_segmented_merged_cuted_dissolved = D3_Global/Resultats/Vecteurs/Ardeche_vectorised_cuted_labeled_dissolved_500_m2.shp
        vector_segmented_merged_cuted_dissolved = repository + os.sep + filename + SUF_VECTORISED + SUF_CUTTED + SUF_LABELED  + SUF_DISSOLVED + "_" + uml_label2 + SUF_M2 + extension_vector

        # ETAPE 3 : SMALL REGIONS MERGING
        if enable_small_region_merging :

            command = "otbcli_LSMSSmallRegionsMerging -in %s -inseg %s -out %s -minsize %d -tilesizex %s -tilesizey %s" %(image_filtered_range, image_segmented, image_segmented_merged, umc, tilesize, tilesize)
            if ram_otb > 0:
                command += " -ram %d" %(ram_otb)

            if debug >=2:
                print(cyan + "vectorizeClassification() : " + bold + green + "ETAPE 3/9 : Debut de la fusion des petits polygones - UMC = " + uml_label + " m2" + endC)
                print(command)

            os.system(command)

            print(cyan + "vectorizeClassification() : " + bold + green + "ETAPE 3/9 : Fin de la fusion des petits polygones - UMC = " + uml_label + " m2 \n" + endC)

        else :
            print(cyan + "vectorizeClassification() : " + bold + yellow + "ETAPE 3/9 : Pas de fusion des polygones de superficie inferieure a un seuil - Non demande" + endC)
            image_segmented_merged = image_filtered_range

        # ETAPE 4 : VECTORISATION
        if enable_vectorization :
            command = "otbcli_LSMSVectorization -in %s -inseg %s -out %s -tilesizex %s -tilesizey %s" %(image_raster, image_segmented_merged, vector_segmented_merged, tilesize, tilesize)
            if ram_otb > 0:
                command += " -ram %d" %(ram_otb)

            if debug >=2:
                print(cyan + "vectorizeClassification() : " + bold + green + "ETAPE 4/9 : Debut de la vectorisation " + endC)
                print(command)

            os.system(command)

            if not save_results_intermediate:
                if os.path.isfile(image_segmented_merged) :
                    removeFile(image_segmented_merged)

            print(cyan + "vectorizeClassification() : " + bold + green + "ETAPE 4/9 : Fin de la vectorisation \n" + endC)

        else :

            print(cyan + "vectorizeClassification() : " + bold + yellow + "ETAPE 4/9 : Pas de vectorisation - Non demande" + endC)

        # ETAPE 5 : DECOUPAGE DU VECTEUR AU REGARD DE L'EMPRISE POUR GERER CERTAINS BUGS ISSUS DE LA FUSION!= None and args.method_smoothing != ""
        if enable_boundaries :

            if debug >=2:
                print(cyan + "vectorizeClassification() : " + bold + green + "ETAPE 5/9 : Debut du re-decoupage du resultat de vectorisation\n" + endC)

            cutVectorAll(boundaries_vector, vector_segmented_merged, vector_segmented_merged_cuted, format_vector)

            print(cyan + "vectorizeClassification() : " + bold + green + "ETAPE 5/9 : Fin du re-decoupage du resultat de vectorisation\n" + endC)

        else :
            print(cyan + "vectorizeClassification() : " + bold + yellow + "ETAPE 5/9 : Pas de decoupage du vecteur - Non demande" + endC)
            vector_segmented_merged_cuted = vector_segmented_merged

        # ETAPE 6 : LABELLISATION DES VECTEURS EN FONCTION DE LA VALEUR MAJORITAIRE DES PIXELS RASTER ASSOCIES
        if enable_reaffectation_vector :

            print(cyan + "vectorizeClassification() : " + bold + green + "ETAPE 6/9 : Debut de la relabellisation des polygones " + endC)

            # Relabelisation
            if debug >= 3:
                print(cyan + "vectorizeClassification() : " + endC + "vector_segmented_merged_cuted : ", vector_segmented_merged_cuted)
                print(cyan + "vectorizeClassification() : " + endC + "image_raster : ", image_raster)

            relabelVectorFromMajorityPixelsRaster(vector_segmented_merged_cuted, image_raster, name_column, format_vector)  # fonction de Lib_vector

            print(cyan + "vectorizeClassification() : " + bold + green + "ETAPE 6/9 : Fin de la relabellisation des polygones \n" + endC)

        else :
            print(cyan + "vectorizeClassification() : " + bold + yellow + "ETAPE 6/9 : Pas de relabellisation des polygones - Non demande" + endC)

        # ETAPE 7 : CORRECTION DES POLYGONES DE BORD
        if enable_cor_bord :
            print(cyan + "vectorizeClassification() : " + bold + green + "ETAPE 7/9 : Debut de la correction des polygones de bord " + endC)

            if debug >= 3:
                print(cyan + "vectorizeClassification() : " + endC + "vector_segmented_merged_cuted : ", vector_segmented_merged_cuted)
                print(cyan + "vectorizeClassification() : " + endC + "vector_segmented_merged_cuted_cor : ", vector_segmented_merged_cuted_cor)

            if not cleanLabelPolygons(vector_segmented_merged_cuted, vector_segmented_merged_cuted_cor, name_column, wrongval_list, 1.0, format_vector, extension_vector) :
                vector_segmented_merged_cuted_cor = vector_segmented_merged_cuted
        else:
            print(cyan + "vectorizeClassification() : " + bold + yellow + "ETAPE 7/9 : Pas de correction des polygones de bord" + endC)
            vector_segmented_merged_cuted_cor = vector_segmented_merged_cuted

        # ETAPE 8 : UNION DES POLYGONES ADJACENTS DE MEME VALEUR
        if enable_dissolve : # Si cette gestion des polygones adjacents de même valeur pose problème, utiliser la brique 21 de la chaine (rasterisation puis nouvelle vectorisation)
            print(cyan + "vectorizeClassification() : " + bold + green + "ETAPE 8/9 : Debut de la fusion des polygones adjacents de meme valeurs " + endC)

            # Transformation des multi-polygones en polygones simples
            multigeometries2geometries(vector_segmented_merged_cuted_cor, vector_segmented_merged_cuted_mpoly, [name_column], format_vector=format_vector)

            # Fusion des polygones voisins
            fusionNeighbourGeometryBySameValue(vector_segmented_merged_cuted_mpoly, vector_segmented_merged_cuted_dissolved, name_column, format_vector)

            print(cyan + "vectorizeClassification() : " + bold + green + "ETAPE 8/9 : Fin de la fusion des polygones adjacents de meme valeurs \n" + endC)

        else:
            print(cyan + "vectorizeClassification() : " + bold + yellow + "ETAPE 8/9 : Pas de fusion des polygones adjacents de meme label - Non demande" + endC)
            vector_segmented_merged_cuted_dissolved = vector_segmented_merged_cuted_cor

        # ETAPE 9 : RENOMMAGE ET SUPPRESSION DES FICHIERS INTRMEDIAIRES UMC
        print(cyan + "vectorizeClassification() : " + bold + green + "ETAPE 9/9 : Debut du renommage " + endC)

        # Renommage pour correspondre au nom de fichier de sortie demandé
        if debug >= 3:
            print(cyan + "vectorizeClassification() : " + endC + "ETAPE 9/9 : Renommage de %s en %s " %(vector_segmented_merged_cuted_dissolved,vector_output) + endC)

        renameVectorFile(vector_segmented_merged_cuted_dissolved, vector_output)
        print(cyan + "vectorizeClassification() : " + bold + green + "ETAPE 9/9 : Fin du renommage pour %s M2" %(umc)+ endC)

        # Suppression des fichiers
        if not save_results_intermediate:

            if os.path.isfile(image_segmented_merged) :
                removeFile(image_segmented_merged)

            if enable_vectorization :
                if debug >= 3:
                    print(cyan + "vectorizeClassification() : " + endC + "ETAPE 9/9 : Suppression de %s " %(vector_segmented_merged) + endC)
                removeVectorFile(vector_segmented_merged, format_vector)

            if enable_boundaries :
                if debug >= 3:
                    print(cyan + "vectorizeClassification() : " + endC + "ETAPE 9/9 : Suppression de %s " %(vector_segmented_merged_cuted) + endC)
                removeVectorFile(vector_segmented_merged_cuted, format_vector)

            if enable_cor_bord :
                if debug >= 3:
                    print(cyan + "vectorizeClassification() : " + endC + "ETAPE 9/9 : Suppression de %s " %(vector_segmented_merged_cuted_cor) + endC)
                removeVectorFile(vector_segmented_merged_cuted_cor, format_vector)

            if enable_dissolve :
                if debug >= 3:
                    print(cyan + "vectorizeClassification() : " + endC + "ETAPE 9/9 : Suppression de %s " %(vector_segmented_merged_cuted_mpoly) + endC)
                removeVectorFile(vector_segmented_merged_cuted_mpoly, format_vector)

        print(cyan + "vectorizeClassification() : " + bold + green + "ETAPE 9/8 : Fin des suppressions pour %s M2" %(umc)+ endC)
        print(cyan + "vectorizeClassification() : " + bold + green + "IMAGE VECTORISEE A %s M2 DISPONIBLE \n" %(umc) + endC)

    # SUPRESSION DES FICHIERS INTERMEDIAIRES INDEPENDANTS DE L'UMC
    if not save_results_intermediate:
        if debug >= 3:
            print(cyan + "vectorizeClassification() : " + endC + "Finalisation : Supression de %s, %s, %s, %s " %(image_raster, image_filtered_range, image_filtered_spat, image_segmented) + endC)

        if enable_reaffectation_raster and os.path.isfile(image_raster) :
            removeFile(image_raster)
        if os.path.isfile(image_raster_mask) :
            removeFile(image_raster_mask)
        if os.path.isfile(vector_boundaries_mask) :
            removeVectorFile(vector_boundaries_mask)
        if os.path.isfile(image_filtered_range) :
            removeFile(image_filtered_range)
        if os.path.isfile(image_filtered_spat) :
            removeFile(image_filtered_spat)
        if os.path.isfile(image_segmented) :
            removeFile(image_segmented)

    print(cyan + "vectorizeClassification() : " + bold + green + "FIN DES DIFFERENTES VECTORISATIONS" + endC)

    # Mise à jour du Log
    ending_event = "vectorizeClassification() : Vectorize classification class ending : "
    timeLine(path_time_log,ending_event)

    return

###########################################################################################################################################
# FONCTION vectorizeGrassClassification                                                                                                   #
###########################################################################################################################################
def vectorizeGrassClassification(image_input, vector_output, name_column, umc_list, enable_reaffectation_raster, enable_vectorization, enable_boundaries, boundaries_vector, method_smoothing, enable_dissolve, path_time_log, expression="(im1b1==11000?400:(im1b1==12200?100:(im1b1==21000?300:(im1b1==22000?200:im1b1))))", format_vector='ESRI Shapefile',  extension_raster=".tif", extension_vector=".shp", save_results_intermediate=False, overwrite=True) :
    """
    # ROLE:
    #     fonction de vectorisation des valeurs de classification par GRASS
    #
    # ENTREES DE LA FONCTION :
    #    image_input : fichier image raster de la classification à vectoriser
    #    vector_output : fichier vecteur résultat de la vectorisation de la classification
    #    name_column : nom de la colonne du fichier shape contenant l'information de classification
    #    umc_list : liste des UMC voulues (en m²). Exemple : umc_list = [200,100,50,20,10]. Mettre un multiple de la surface du pixel
    #               Conversion des UMC en pixels  umc_list[:]=[x/area_pixel for x in umc_list]
    #    enable_reaffectation_raster : activation de la réaffectation du raster
    #    enable_vectorization : activation de la vectorisation
    #    enable_boundaries : activation du decoupage
    #    boundaries_vector : vecteur de découpe
    #    method_smoothing : méthode de lissage (douglas,hermite ou chaiken)
    #    enable_dissolve : activation de la fusion des polygones voisin
    #    path_time_log : le fichier de log de sortie
    #    expression : expression utilisée pour la réaffectation des labels du raster
    #    format_vector : format du fichier vecteur. Optionnel, par default : 'ESRI Shapefile'
    #    extension_raster : extension des fichiers raster de sortie, par defaut = '.tif'
    #    extension_vector : extension du fichier vecteur de sortie, par defaut = '.shp'
    #    save_results_intermediate : liste des sorties intermediaires nettoyees, par defaut = False
    #    overwrite : supprime ou non les fichiers existants ayant le meme nom
    #
    # SORTIES DE LA FONCTION :
    #    Le fichier vecteur de classification
    #    Eléments modifiés aucun
    #
    """

    # Mise à jour du Log
    starting_event = "vectorizeGrassClassification() : Vectorize GRASS classification class starting : "
    timeLine(path_time_log, starting_event)

    if debug >= 3:
        print(cyan + "vectorizeGrassClassification() : " + endC + "image_input : " + str(image_input) + endC)
        print(cyan + "vectorizeGrassClassification() : " + endC + "vector_output : " + str(vector_output) + endC)
        print(cyan + "vectorizeGrassClassification() : " + endC + "name_column : " + str(name_column) + endC)
        print(cyan + "vectorizeGrassClassification() : " + endC + "umc_list : " + str(umc_list) + endC)
        print(cyan + "vectorizeGrassClassification() : " + endC + "enable_reaffectation_raster : " + str(enable_reaffectation_raster) + endC)
        print(cyan + "vectorizeGrassClassification() : " + endC + "enable_vectorization : " + str(enable_vectorization) + endC)
        print(cyan + "vectorizeGrassClassification() : " + endC + "enable_boundaries : " + str(enable_boundaries) + endC)
        print(cyan + "vectorizeGrassClassification() : " + endC + "boundaries_vector : " + str(boundaries_vector) + endC)
        print(cyan + "vectorizeGrassClassification() : " + endC + "method_smoothing : " + str(method_smoothing) + endC)
        print(cyan + "vectorizeGrassClassification() : " + endC + "enable_dissolve : " + str(enable_dissolve) + endC)
        print(cyan + "vectorizeGrassClassification() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "vectorizeGrassClassification() : " + endC + "expression : " + str(expression) + endC)
        print(cyan + "vectorizeGrassClassification() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "vectorizeGrassClassification() : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "vectorizeGrassClassification() : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "vectorizeGrassClassification() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "vectorizeGrassClassification() : " + endC + "overwrite : " + str(overwrite) + endC)

    # Constantes
    CODAGE = 'uint16'

    SUF_FILTERED = '_filtred'
    SUF_RANGE = '_range'
    SUF_SPAT = '_spat'
    SUF_MASK = '_mask'

    SUF_REAFFECTED = '_reaffected'
    SUF_VECTORISED = '_vectorised'
    SUF_CUTTED = '_cutted'
    SUF_MPOLY = '_mpoly'
    SUF_LABELED = '_labeled'
    SUF_DISSOLVED = '_dissolved'
    SUF_M2 = '_m2'

    print(cyan + "\nvectorizeGrassClassification() : " + bold + green + "DEBUT DE LA VECTORISATION" + endC)

    # Definition variables et chemins
    repository = os.path.dirname(vector_output)                                                    # Répertoire temporaire. Ex : repository = D3_Global/Resultats/Vecteurs
    filename = os.path.splitext(os.path.basename(vector_output))[0]                                # Nom de l'etude. Ex : filename = "Ardeche"

    image_raster_mask = repository + os.sep + filename + SUF_MASK + extension_raster                     # Ex : image_raster_mask =      D3_Global/Resultats/Vecteurs/Ardeche_mask.tif
    vector_boundaries_mask = repository + os.sep + filename + SUF_MASK + extension_vector                # Ex : vector_boundaries_mask = D3_Global/Resultats/Vecteurs/Ardeche_mask.shp
    image_raster = repository + os.sep + filename + SUF_REAFFECTED + extension_raster                    # Ex : image_raster =           D3_Global/Resultats/Vecteurs/Ardeche.tif
    image_filtered_range = repository + os.sep + filename + SUF_FILTERED + SUF_RANGE + extension_raster  # Ex : image_filtered_range =   D3_Global/Resultats/Vecteurs/Ardeche_filtred_range.tif
    image_filtered_spat = repository + os.sep + filename + SUF_FILTERED + SUF_SPAT + extension_raster    # Ex : image_filtered_spat  =   D3_Global/Resultats/Vecteurs/Ardeche_filtred_spat.tif

    area_pixel =  getPixelSizeImage(image_input)                   # Superficie, en m d'un pixel de l'image. Exemple pour une image à 5m : area_pixel = 25
    pixel_size_x, pixel_size_y = getPixelWidthXYImage(image_input) # taille d'un pixel
    epsg, _ = getProjectionImage(image_input)                      # Recuperation de la valeur de la projection du rasteur d'entrée
    xmin, xmax, ymin, ymax = getEmpriseImage(image_input)          # Recuperation de l'emprise du rasteur d'entrée

    print(cyan + "vectorizeGrassClassification() : " + endC + "Surface d'un pixel : ", area_pixel)

    # ETAPE X : PREPARATION DU VECTEUR DE DECOUPE SI IL N'EXISTE PAS
    if enable_boundaries and boundaries_vector == "":
        createBinaryMask(image_input, image_raster_mask, 0, True)
        polygonizeRaster(image_raster_mask, vector_boundaries_mask, filename)
        boundaries_vector = vector_boundaries_mask

    # ETAPE 0 : REAFFECTATION DU RASTEUR
    # Etape (facultative, et déconseillée) de relabellisation des classes
    if enable_reaffectation_raster :

        command = "otbcli_BandMath -il \"%s\" -out %s  %s -exp \"%s\"" %(image_input,image_raster,CODAGE,expression)

        if debug >=2:
            print(cyan + "vectorizeGrassClassification() : " + bold + green + "ETAPE 0/4 : Debut de la réaffectation raster \n" + endC)
            print(command)

        os.system(command)
        print(cyan + "vectorizeGrassClassification() : " + bold + green + "ETAPE 0/4 : Fin de la reaffectation raster \n" + endC)

    else :
        print(cyan + "vectorizeGrassClassification() : " + bold + yellow + "ETAPE 0/4 : Pas de reaffectation raster - Non demande" + endC)
        image_raster = image_input

    # INITIALISATION DE GRASS
    initializeGrass(repository, xmin, xmax, ymin, ymax, pixel_size_x, pixel_size_y, projection=epsg)

    # POUR TOUTES LES UMC DEMANDEES
    for umc in umc_list :

        uml_label = round((umc * area_pixel)/2)
        uml_label2 = str(int(uml_label)).replace(".","_")

        # Ex : vector_vectorised = D3_Global/Resultats/Vecteurs/Ardeche_vectorised_500_m2.shp
        vector_vectorised = repository + os.sep + filename + SUF_VECTORISED + "_" + uml_label2 + SUF_M2 + extension_vector

        # Ex : vector_vectorised_cuted = D3_Global/Resultats/Vecteurs/Ardeche_vectorised_cuted_500_m2.shp
        vector_vectorised_cuted = repository + os.sep + filename + SUF_VECTORISED + SUF_CUTTED + "_" + uml_label2 + SUF_M2 + extension_vector

        # Ex : vector_vectorised_cuted_mpoly = D3_Global/Resultats/Vecteurs/Ardeche_vectorised_cuted_mpoly_500_m2.shp
        vector_vectorised_cuted_mpoly = repository + os.sep + filename + SUF_VECTORISED + SUF_CUTTED  + SUF_MPOLY + "_" + uml_label2 + SUF_M2 + extension_vector

        # Ex : vector_vectorised_cuted_dissolved = D3_Global/Resultats/Vecteurs/Ardeche_vectorised_cuted_dissolved_500_m2.shp
        vector_vectorised_cuted_dissolved = repository + os.sep + filename + SUF_VECTORISED + SUF_CUTTED  + SUF_DISSOLVED + "_" + uml_label2 + SUF_M2 + extension_vector

        # ETAPE 1 : VECTORISATION
        if enable_vectorization :

            is_smooth = [None]*3
            if method_smoothing=="douglas":
                is_smooth[0]=uml_label
            elif method_smoothing=="hermite":
                is_smooth[1]=uml_label
            elif method_smoothing=="chaiken":
                is_smooth[2]=uml_label
            else:
                print(cyan + "vectorizeGrassClassification() : " + bold + yellow + "ETAPE 1/4 : la methode de lissage Grass est mal specifiée. Par défaut : douglas." + endC)
                is_smooth[0]=uml_label


            if debug >=2:
                print(cyan + "vectorizeGrassClassification() : " + bold + green + "ETAPE 1/4 : Debut de la vectorisation " + endC)

            vectorisationGrass(image_raster, vector_vectorised, area_pixel, *is_smooth, True, format_vector, overwrite)

            # Changement du nom de la colonne
            if name_column != 'cat' :
                renameFieldsVector(vector_vectorised, ['cat'], [name_column], format_vector)

            print(cyan + "vectorizeGrassClassification() : " + bold + green + "ETAPE 1/4 : Fin de la vectorisation \n" + endC)

        else :

            print(cyan + "vectorizeGrassClassification() : " + bold + yellow + "ETAPE 1/4 : Pas de vectorisation - Non demande" + endC)

        # ETAPE 2 : DECOUPAGE DU VECTEUR AU REGARD DE L'EMPRISE S'IL N'Y A PAS DE CORRECTION TOPOLOGIQUE
        if enable_boundaries :

            if debug >=2:
                print(cyan + "vectorizeGrassClassification() : " + bold + green + "ETAPE 2/4 : Debut du re-decoupage du resultat de vectorisation\n" + endC)

            cutVectorAll(boundaries_vector, vector_vectorised, vector_vectorised_cuted, format_vector)
            print(cyan + "vectorizeGrassClassification() : " + bold + green + "ETAPE 2/4 : Fin du re-decoupage du resultat de vectorisation\n" + endC)

        else :
            print(cyan + "vectorizeGrassClassification() : " + bold + yellow + "ETAPE 2/4 : Pas de decoupage du vecteur - Non demande" + endC)
            vector_vectorised_cuted = vector_vectorised

        # ETAPE 3 : UNION DES POLYGONES ADJACENTS DE MEME VALEUR
        if enable_dissolve :
            print(cyan + "vectorizeGrassClassification() : " + bold + green + "ETAPE 3/4 : Debut de la fusion des polygones adjacents de meme valeurs " + endC)

            # Transformation des multi-polygones en polygones simples
            multigeometries2geometries(vector_vectorised_cuted, vector_vectorised_cuted_mpoly, [name_column], format_vector=format_vector)

            # Fusion des polygones voisins
            fusionNeighbourGeometryBySameValue(vector_vectorised_cuted_mpoly, vector_vectorised_cuted_dissolved, name_column, format_vector)

            print(cyan + "vectorizeGrassClassification() : " + bold + green + "ETAPE 3/4 : Fin de la fusion des polygones adjacents de meme valeurs \n" + endC)

        else:
            print(cyan + "vectorizeGrassClassification() : " + bold + yellow + "ETAPE 3/4 : Pas de fusion des polygones adjacents de meme label - Non demande" + endC)
            vector_vectorised_cuted_dissolved = vector_vectorised_cuted

        # ETAPE 4 : RENOMAGE ET SUPRESSION DES FICHIERS INTERMEDIAIRES UMC
        print(cyan + "vectorizeGrassClassification() : " + bold + green + "ETAPE 4/4 : Debut du renommage " + endC)

        # Renommage pour correspondre au nom de fichier de sortie demandé
        if debug >= 3:
            print(cyan + "vectorizeGrassClassification() : " + endC + "ETAPE 4/4 : Renommage de %s en %s " %(vector_vectorised_cuted_dissolved,vector_output) + endC)
        renameVectorFile(vector_vectorised_cuted_dissolved, vector_output)
        print(cyan + "vectorizeGrassClassification() : " + bold + green + "ETAPE 4/4 : Fin du renommage pour %s M2" %(umc)+ endC)

        # Suppression des fichiers
        if not save_results_intermediate:

            if enable_vectorization :
                if debug >= 3:
                    print(cyan + "vectorizeGrassClassification() : " + endC + "ETAPE 4/4 : Suppression de %s " %(vector_vectorised) + endC)
                removeVectorFile(vector_vectorised, format_vector)

            if enable_boundaries :
                if debug >= 3:
                    print(cyan + "vectorizeGrassClassification() : " + endC + "ETAPE 4/4 : Suppression de %s " %(vector_vectorised_cuted) + endC)
                removeVectorFile(vector_vectorised_cuted, format_vector)

            if enable_dissolve :
                if debug >= 3:
                    print(cyan + "vectorizeGrassClassification() : " + endC + "ETAPE 4/4 : Suppression de %s " %(vector_vectorised_cuted_mpoly) + endC)
                removeVectorFile(vector_vectorised_cuted_mpoly, format_vector)

        print(cyan + "vectorizeGrassClassification() : " + bold + green + "ETAPE 4/4 : Fin des suppressions pour %s M2" %(umc)+ endC)
        print(cyan + "vectorizeGrassClassification() : " + bold + green + "IMAGE VECTORISEE A %s M2 DISPONIBLE \n" %(umc) + endC)

    # SUPRESSION DES FICHIERS INTERMEDIAIRES
    if not save_results_intermediate:
        if debug >= 3:
            print(cyan + "vectorizeGrassClassification() : " + endC + "Finalisation : Supression des fichiers temporaires" + endC)
        cleanGrass(repository)

    print(cyan + "vectorizeGrassClassification() : " + bold + green + "FIN DES DIFFERENTES VECTORISATIONS" + endC)

    # Mise à jour du Log
    ending_event = "vectorizeGrassClassification() : Vectorize GRASS classification class ending : "
    timeLine(path_time_log,ending_event)

    return

###########################################################################################################################################
# FONCTION topologicalCorrection()                                                                                                        #
###########################################################################################################################################
def topologicalCorrection(vector_output, enable_boundaries, boundaries_vector, epsg, project_encoding, server_postgis, port_number, user_postgis, password_postgis, database_postgis, schema_postgis, path_time_log, format_vector, save_results_intermediate=False, overwrite=True) :
    """
    # ROLE:
    #     Verifier et corrige des vecteurs resultats de classifications OCS en traitement sous postgis
    #
    # ENTREES DE LA FONCTION :
    #     vector_output: le vecteur de sortie à corriger
    #     enable_boundaries : activation du découpage
    #     boundaries_vector : vecteur de découpe
    #     epsg : EPSG code de projection
    #     project_encoding : encodage des fichiers d'entrés
    #     server_postgis : nom du serveur postgis
    #     port_number : numéro du port pour le serveur postgis
    #     user_postgis : le nom de l'utilisateurs postgis
    #     password_postgis : le mot de passe de l'utilisateur posgis
    #     database_postgis : le nom de la base posgis à utiliser
    #     schema_postgis : le nom du schéma à utiliser
    #     path_time_log : le fichier de log de sortie
    #     format_vector : format du fichier vecteur. Optionnel, par default : 'ESRI Shapefile'
    #     save_results_intermediate : fichiers de sorties intermediaires nettoyees, par defaut = False
    #     overwrite : écrase si un fichier existant a le même nom qu'un fichier de sortie, par defaut a True
    #
    # SORTIES DE LA FONCTION :
    #     na
    #
    """

    # Mise à jour du Log
    starting_event = "topologicalCorrection() : Correct topolog vector starting : "
    timeLine(path_time_log,starting_event)

    print(endC)
    print(bold + green + "## START : SQL CORRECT VECTORS" + endC)
    print(endC)

    if debug >= 2:
        print(bold + green + "topologicalCorrection() : Variables dans la fonction" + endC)
        print(cyan + "topologicalCorrection() : " + endC + "vector_output : " + str(vector_output) + endC)
        print(cyan + "topologicalCorrection() : " + endC + "enable_boundaries : " + str(enable_boundaries) + endC)
        print(cyan + "topologicalCorrection() : " + endC + "boundaries_vector : " + str(boundaries_vector) + endC)
        print(cyan + "topologicalCorrection() : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "topologicalCorrection() : " + endC + "project_encoding : " + str(project_encoding) + endC)
        print(cyan + "topologicalCorrection() : " + endC + "server_postgis : " + str(server_postgis) + endC)
        print(cyan + "topologicalCorrection() : " + endC + "port_number : " + str(port_number) + endC)
        print(cyan + "topologicalCorrection() : " + endC + "user_postgis : " + str(user_postgis) + endC)
        print(cyan + "topologicalCorrection() : " + endC + "password_postgis : " + str(password_postgis) + endC)
        print(cyan + "topologicalCorrection() : " + endC + "database_postgis : " + str(database_postgis) + endC)
        print(cyan + "topologicalCorrection() : " + endC + "schema_postgis : " + str(schema_postgis) + endC)
        print(cyan + "topologicalCorrection() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "topologicalCorrection() : " + endC + "path_time_log : " + str(format_vector) + endC)
        print(cyan + "topologicalCorrection() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "topologicalCorrection() : " + endC + "overwrite : " + str(overwrite) + endC)

    # Création de la base de données
    table_correct_name = os.path.splitext(os.path.basename(vector_output))[0].lower()
    createDatabase(database_postgis, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number))

    # Import du fichier vecteur dans la base
    importVectorByOgr2ogr(database_postgis, vector_output, table_correct_name, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema_name=schema_postgis, epsg=str(epsg), codage=project_encoding)

    if enable_boundaries:
        # Création de la table vecteurs de decoupe et import dans la base
        table_polygones_cutting = os.path.splitext(os.path.basename(boundaries_vector))[0].lower()
        importVectorByOgr2ogr(database_postgis, boundaries_vector, table_polygones_cutting, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema_name=schema_postgis, epsg=str(epsg), codage=project_encoding)

    # Connexion à la base SQL postgis
    connection = openConnection(database_postgis, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema_name=schema_postgis)

    # Correction la géométrie (topologie)
    topologyCorrections(connection, table_correct_name, geom_field='geom')

    # Decoupage des polygones
    if enable_boundaries :
        # Découpage des polygones sur l'emprise d'étude
        # Découpe avec Postgis
        cutPolygonesByPolygones(connection, table_correct_name, table_polygones_cutting, table_correct_name+'_cut', geom_field='geom')
        table_correct_name = table_correct_name+'_cut'

    # Déconnexion de la base de données, pour éviter les conflits d'accès
    closeConnection(connection)

    # Récupération de la base du fichier vecteur de sortie
    exportVectorByOgr2ogr(database_postgis, vector_output, table_correct_name, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema_name=schema_postgis, format_type=format_vector)

    # Suppression des fichiers intermédiaires
    if not save_results_intermediate:
        try :
            dropDatabase(database_postgis, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number))
        except :
            print(cyan + "topologicalCorrection() : " + bold + yellow + "Attention impossible de supprimer la base de donnée : " + endC + database_postgis)

    print(endC)
    print(bold + green + "## END : SQL CORRECT VECTORS" + endC)
    print(endC)

    # Mise à jour du Log
    ending_event = "topologicalCorrection() :  Correct topolog vector ending : "
    timeLine(path_time_log,ending_event)

    return

###########################################################################################################################################
# MISE EN PLACE DU PARSER                                                                                                                 #
###########################################################################################################################################

# Code executé seulement dans le cas ou le script est lancé depuis une ligne de commande
# Il n'est pas executé lors d'un import Vectorization.py
# Exemple de lancement en ligne de commande:
# python Vectorization.py -i ../D2_Par_Image/APTV_05/Resultats/APTV_05_classif.tif -o ../D2_Par_Image/APTV_05/Resultats/APTV_05_classif.shp -col classif -exp "(im1b1==11000?400:(im1b1==12200?100:(im1b1==21000?300:(im1b1==22000?200:im1b1))))" -umc 200 100 50 20 10 -log ../D2_Par_Image/APTV_05/fichierTestLog.txt
#
# python3 -m Vectorization -i /mnt/Data/10_Agents_travaux_en_cours/Gilles/Test_Vectorisation/Classif2018BordeauxRaster.tif -o /mnt/Data/10_Agents_travaux_en_cours/Gilles/Test_Vectorisation/Classif2018BordeauxVectorBis.shp -grass -col cat -umc 100 -log /mnt/Data/10_Agents_travaux_en_cours/Gilles/Test_Vectorisation/fichierTestLog.txt

# Expression utilisée pour la réaffectation des labels du raster
# expression = "if(im1b1==110,400,if(im1b1==122,100,if(im1b1==210,300,if(im1b1==220,200,im1b1))))"
# expression = "if(im1b1==11000,400,if(im1b1==12200,100,if(im1b1==21000,300,if(im1b1==22000,200,im1b1))))"
# expression = "im1b1"

def main(gui=False):

    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, prog="Vectorization", description='\
    Info : Vectoring function of a tiff image classification result shapefile. \n\
    Objectif : Creer un fichier vecteur a partir d un fichier raster. \n\
    Example : python Vectorization.py -i ../D2_Par_Image/APTV_05/Resultats/APTV_05_classif.tif \n\
                                      -o ../D2_Par_Image/APTV_05/Resultats/APTV_05_classif.shp \n\
                                      -col classif \n\
                                      -exp (im1b1==11000?400:(im1b1==12200?100:(im1b1==21000?300:(im1b1==22000?200:im1b1)))) \n\
                                      -umc 200 100 50 20 10 \n\
                                      -log ../D2_Par_Image/APTV_05/fichierTestLog.txt')

    parser.add_argument('-i','--image_input',default="",help="Classification image to vectorize", type=str, required=True)
    parser.add_argument('-o','--vector_output',default="",help="Vector output result of vectorisation classification image", type=str, required=True)
    parser.add_argument('-col','--name_col', default="",help="Name of the column containing the shapefile classification of information", type=str, required=True)
    parser.add_argument('-grass', '--vectorisation_grass', action='store_true', default=False, help="Option : The vectorization is realized by the tools grass By default : False", required=False)
    parser.add_argument('-exp','--expression',default="(im1b1==11000?400:(im1b1==12200?100:(im1b1==21000?300:(im1b1==22000?200:im1b1))))",help="Expression for the reallocation of raster labels", type=str, required=False)
    parser.add_argument('-umc','--l_umc',default=[20],nargs="+",help="Option : List of appropriate UMC (in number of pixels). Put a multiple of the pixel. By default : 200 100 50 20 10.", type=int, required=False)
    parser.add_argument('-ts','--tilesize',default=2000,help="Option : Size of the working windows in x and y. By default : 2000.", type=int, required=False)
    parser.add_argument('-csql', '--correction_sql', action='store_true', default=False, help="Option : Topological SQL correction by postgres vector output input. By default : False", required=False)
    parser.add_argument('-reafrast', '--enable_reaffectation_raster', action='store_true', default=False, help="Option : Activation the reallocation of raster. By default : False", required=False)
    parser.add_argument('-meashifi', '--enable_meanshift_filtering', action='store_false', default=True, help="Option : Activation MeanShift filter. By default : True", required=False)
    parser.add_argument('-segmenta', '--enable_segmentation', action='store_false', default=True, help="Option : Activation segmentation. By default : True", required=False)
    parser.add_argument('-smalreme', '--enable_small_region_merging', action='store_false', default=True, help="Option : Activation of the merge small regions. By default : True", required=False)
    parser.add_argument('-vectoriz', '--enable_vectorization', action='store_false', default=True, help="Option : Activation vectorisation. By default : True", required=False)
    parser.add_argument('-boundari', '--enable_boundaries', action='store_false', default=False, help="Option : Activation cut out boundaries. By default : True", required=False)
    parser.add_argument('-boundvect', '--boundaries_vector', default="", help="Boundaries for vector cutting after the vectorisation. If no arguments, no vector cutting, else, give the complete name of the cutting shape", required=False)
    parser.add_argument('-smooth','--method_smoothing',default="douglas",help="Grass method for smoothing vector. By default : douglas. Choose : douglas, hermite, chaiken", type=str, required=False)
    parser.add_argument('-reafvect', '--enable_reaffectation_vector', action='store_false', default=True, help="Option : Activation of the reallocation of vector. By default : True", required=False)
    parser.add_argument('-corbord', '--enable_corbord', action='store_true', default=False, help="Option : Activation de la correction des bords. By default : False", required=False)
    parser.add_argument('-wrongval','--l_wrong_values',default=[0,65535],nargs="+",help="Option : List of wrong values to remove in the column name_col", type=int, required=False)
    parser.add_argument('-dissolve', '--enable_dissolve', action='store_false', default=True, help="Option : Activation dissolve polygones. By default : True", required=False)
    parser.add_argument('-epsg','--epsg', default=2154,help="EPSG code projection.", type=int, required=False)
    parser.add_argument('-pe','--project_encoding', default="latin1",help="Project encoding.", type=str, required=False)
    parser.add_argument('-serv','--server_postgis', default="localhost",help="Postgis serveur name or ip.", type=str, required=False)
    parser.add_argument('-port','--port_number', default=5432,help="Postgis port number.", type=int, required=False)
    parser.add_argument('-user','--user_postgis', default="postgres",help="Postgis user name.", type=str, required=False)
    parser.add_argument('-pwd','--password_postgis', default="postgres",help="Postgis password user.", type=str, required=False)
    parser.add_argument('-db','--database_postgis', default="ocs_verification",help="Postgis database name.", type=str, required=False)
    parser.add_argument('-sch','--schema_postgis', default="public",help="Postgis schema name.", type=str, required=False)
    parser.add_argument('-ram','--ram_otb',default=0,help="Ram available for processing otb applications (in MB)", type=int, required=False)
    parser.add_argument('-vef','--format_vector', default="ESRI Shapefile",help="Format of the output vector file.", type=str, required=False)
    parser.add_argument('-rae','--extension_raster', default=".tif", help="Option : Extension file for image raster. By default : '.tif'", type=str, required=False)
    parser.add_argument('-vee','--extension_vector',default=".shp",help="Option : Extension file for vector. By default : '.shp'", type=str, required=False)
    parser.add_argument('-log','--path_time_log',default="",help="Name of log", type=str, required=False)
    parser.add_argument('-sav','--save_results_inter',action='store_true',default=False,help="Save or delete intermediate result after the process. By default, False", required=False)
    parser.add_argument('-now','--overwrite',action='store_false',default=True,help="Overwrite files with same names. By default : True", required=False)
    parser.add_argument('-debug','--debug',default=3,help="Option : Value of level debug trace, default : 3 ",type=int, required=False)
    args = displayIHM(gui, parser)

    # Récupération de l'image d'entrée
    if args.image_input != None:
        image_input = args.image_input
        if not os.path.isfile(image_input):
            raise NameError (cyan + "Vectorization : " + bold + red  + "File %s not existe!" %(image_input) + endC)

    # Récupération de l'image de sortie
    if args.vector_output != None:
        vector_output = args.vector_output

    # Récupération des noms liés aux polygones
    if args.name_col != None:
        name_column = args.name_col

    # Récupération du type d'outil pour la vectorisation OTB/GRASS (par defaut OTB)
    if args.vectorisation_grass != None:
        is_grass = args.vectorisation_grass

    # L'expression de reafectation des valeurs de pixels
    if args.expression!= None:
        expression = args.expression

    # L'UMC Unité Minimal de Collecte
    if args.l_umc!= None:
        umc_list = args.l_umc

    # Taille de la grille de travail pour OTB
    if args.tilesize!= None:
        tilesize = args.tilesize

    # Recuperartion de la demende post traitement topologique sql
    if args.correction_sql!= None:
        correction_sql = args.correction_sql

    # Options
    if args.enable_reaffectation_raster != None:
        enable_reaffectation_raster = args.enable_reaffectation_raster

    if args.enable_meanshift_filtering!= None:
        enable_meanshift_filtering = args.enable_meanshift_filtering

    if args.enable_segmentation != None:
        enable_segmentation = args.enable_segmentation

    if args.enable_small_region_merging != None:
        enable_small_region_merging = args.enable_small_region_merging

    if args.enable_vectorization != None:
        enable_vectorization = args.enable_vectorization

    if args.enable_boundaries != None:
        enable_boundaries = args.enable_boundaries

    if args.boundaries_vector != "":
        boundaries_vector = args.boundaries_vector
    else:
        boundaries_vector = ""  # No cutting of the vectors after the vectorisation

    if args.method_smoothing != None:
        method_smoothing = args.method_smoothing

    if args.enable_dissolve != None:
        enable_dissolve = args.enable_dissolve

    if args.enable_reaffectation_vector != None:
        enable_reaffectation_vector = args.enable_reaffectation_vector

    if args.enable_corbord != None:
        enable_corbord = args.enable_corbord

    if args.l_wrong_values!= None:
        wrongval_list = args.l_wrong_values

    # Récupération du code EPSG de la projection du shapefile trait de côte
    if args.epsg != None :
        epsg = args.epsg

    # Récupération de l'encodage des fichiers
    if args.project_encoding != None :
        project_encoding = args.project_encoding

    # Récupération du serveur de Postgis
    if args.server_postgis != None :
        server_postgis = args.server_postgis

    # Récupération du numéro du port
    if args.port_number != None :
        port_number = args.port_number

    # Récupération du nom de l'utilisateur postgis
    if args.user_postgis != None :
        user_postgis = args.user_postgis

    # Récupération du mot de passe de l'utilisateur
    if args.password_postgis != None :
        password_postgis = args.password_postgis

    # Récupération du nom de la base postgis
    if args.database_postgis != None :
        database_postgis = args.database_postgis

    # Récupération du nom du schéma
    if args.schema_postgis != None :
        schema_postgis = args.schema_postgis

    # Récupération du parametre ram
    if args.ram_otb != None:
        ram_otb = args.ram_otb

    # Récupération du format du fichier de sortie
    if args.format_vector != None :
        format_vector = args.format_vector

    # Paramètre de l'extension des images rasters
    if args.extension_raster != None:
        extension_raster = args.extension_raster

    # Récupération de l'extension des fichiers vecteurs
    if args.extension_vector != None:
        extension_vector = args.extension_vector

    # Récupération du nom du fichier log
    if args.path_time_log!= None:
        path_time_log = args.path_time_log

    # Ecrasement des fichiers
    if args.save_results_inter != None:
        save_results_intermediate = args.save_results_inter

    if args.overwrite!= None:
        overwrite = args.overwrite

    # Récupération de l'option niveau de debug
    if args.debug!= None:
        global debug
        debug = args.debug

    # Affichage des arguments récupérés
    if debug >= 3:
        print(bold + green + "Variables dans le parser" + endC)
        print(cyan + "Vectorization : " + endC + "image_input : " + str(image_input) + endC)
        print(cyan + "Vectorization : " + endC + "vector_output : " + str(vector_output) + endC)
        print(cyan + "Vectorization : " + endC + "name_col : " + str(name_column) + endC)
        print(cyan + "Vectorization : " + endC + "expression : " + str(expression) + endC)
        print(cyan + "Vectorization : " + endC + "l_umc : " + str(umc_list) + endC)
        print(cyan + "Vectorization : " + endC + "tilesize : " + str(tilesize) + endC)
        print(cyan + "Vectorization : " + endC + "correction_sql : " + str(correction_sql) + endC)
        print(cyan + "Vectorization : " + endC + "vectorisation_grass : " + str(is_grass) + endC)
        print(cyan + "Vectorization : " + endC + "enable_reaffectation_raster : " + str(enable_reaffectation_raster) + endC)
        print(cyan + "Vectorization : " + endC + "enable_meanshift_filtering : " + str(enable_meanshift_filtering) + endC)
        print(cyan + "Vectorization : " + endC + "enable_segmentation : " + str(enable_segmentation) + endC)
        print(cyan + "Vectorization : " + endC + "enable_small_region_merging : " + str(enable_small_region_merging) + endC)
        print(cyan + "Vectorization : " + endC + "enable_vectorization : " + str(enable_vectorization) + endC)
        print(cyan + "Vectorization : " + endC + "enable_boundaries : " + str(enable_boundaries) + endC)
        print(cyan + "Vectorization : " + endC + "boundaries_vector : " + str(boundaries_vector) + endC)
        print(cyan + "Vectorization : " + endC + "method_smoothing : " + str(method_smoothing) + endC)
        print(cyan + "Vectorization : " + endC + "enable_dissolve : " + str(enable_dissolve) + endC)
        print(cyan + "Vectorization : " + endC + "enable_reaffectation_vector : " + str(enable_reaffectation_vector) + endC)
        print(cyan + "Vectorization : " + endC + "enable_cor_bord : " + str(enable_corbord) + endC)
        print(cyan + "Vectorization : " + endC + "l_wrong_values : " + str(wrongval_list) + endC)
        print(cyan + "Vectorization : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "Vectorization : " + endC + "project_encoding : " + str(project_encoding) + endC)
        print(cyan + "Vectorization : " + endC + "server_postgis : " + str(server_postgis) + endC)
        print(cyan + "Vectorization : " + endC + "port_number : " + str(port_number) + endC)
        print(cyan + "Vectorization : " + endC + "user_postgis : " + str(user_postgis) + endC)
        print(cyan + "Vectorization : " + endC + "password_postgis : " + str(password_postgis) + endC)
        print(cyan + "Vectorization : " + endC + "database_postgis : " + str(database_postgis) + endC)
        print(cyan + "Vectorization : " + endC + "schema_postgis : " + str(schema_postgis) + endC)
        print(cyan + "Vectorization : " + endC + "ram_otb : " + str(ram_otb) + endC)
        print(cyan + "Vectorization : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "Vectorization : " + endC + "extension_raster : " + str(extension_raster) + endC)
        print(cyan + "Vectorization : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "Vectorization : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "Vectorization : " + endC + "save_results_inter : " + str(save_results_intermediate) + endC)
        print(cyan + "Vectorization : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "Vectorization : " + endC + "debug : " + str(debug) + endC)

    # Si le dossier de sortie n'existe pas, on le crée
    repertory_output = os.path.dirname(vector_output)
    if not os.path.isdir(repertory_output):
        os.makedirs(repertory_output)

    # EXECUTION DE LA FONCTION
    if is_grass :
        # Traitement image à vectoriser par outil GRASS
        vectorizeGrassClassification(image_input, vector_output, name_column, umc_list, enable_reaffectation_raster, enable_vectorization, enable_boundaries and not correction_sql, boundaries_vector, method_smoothing, enable_dissolve, path_time_log, expression, format_vector, extension_raster, extension_vector, save_results_intermediate, overwrite)
    else :
        # Traitement image à vectoriser par outil OTB
        vectorizeClassification(image_input, vector_output, name_column, umc_list, tilesize, enable_reaffectation_raster, enable_meanshift_filtering, enable_segmentation, enable_small_region_merging, enable_vectorization, enable_boundaries and not correction_sql, boundaries_vector, enable_dissolve, enable_reaffectation_vector, enable_corbord, wrongval_list, path_time_log, expression, ram_otb, format_vector, extension_raster, extension_vector, save_results_intermediate, overwrite)

    # POST TRAITEMENT TOPOLOGIQUE ET DECOUPAGE SQL
    if correction_sql :
        topologicalCorrection(vector_output, enable_boundaries, boundaries_vector, epsg, project_encoding, server_postgis, port_number, user_postgis, password_postgis, database_postgis, schema_postgis, path_time_log, format_vector, save_results_intermediate, overwrite)


# ================================================

if __name__ == '__main__':
  main(gui=False)
