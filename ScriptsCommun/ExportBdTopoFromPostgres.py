#!/usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT QUI EXPORTE LES DONNEES BD TOPO MONTEES DANS UNE BASE POSTGRESQL/POSTGIS                                                           #
#                                                                                                                                           #
#############################################################################################################################################
'''
Nom de l'objet : ExportBdTopoFromPostgres.py
Description :
    Objectif : exporter les données BD TOPO montées en base Postgres, à partir d'un fichier d'emprise
    Remarques :
        - les valeurs possibles pour le paramètre "zone" sont : "FRA" / "FXX" / "GLP" / "GUF" / "MTQ" / "MYT" / "REU" / "SPM" / "BLM" / "MAF"
            correspondant respectivement à : France entière (EPSG 4326) / France Métropolitaine (EPSG 2154) / Guadeloupe (EPSG 5490) / Guyane (EPSG 2972) / Martinique (EPSG 5490) / Mayotte (EPSG 4471) / Réunion (EPSG 2975) / Saint-Pierre-et-Miquelon (EPSG 4467) / Saint-Barthélemy (EPSG 5490) / Saint-Martin (EPSG 5490)
        - ne gère que les formats SHP et GPKG (fichier unique multi-couches) en sortie (formats de référence IGN) :
            * valeurs possibles pour le paramètre "format_vector" : "ESRI Shapefile" / "GPKG"
            * valeurs possibles pour le paramètre "extension_vector" : ".shp" / ".gpkg"
    Limites :
        - peut ne pas fonctionner correctement pour des versions de la BD TOPO autres que v3.3 (surtout en export "ESRI Shapefile") --> lié au paramètre "input_metadata"

-----------------
Outils utilisés :
 - PostgreSQL/PostGIS

------------------------------
Historique des modifications :
 - 29/02/2024 : création
 - 02/05/2024 : ajout des territoires de Saint-Barthélemy et Saint-Martin
 - 04/07/2024 : correspondance automatique des champs SQL -> SHP, à partir d'un fichier métadonnées de l'IGN (paramètre "input_metadata")
 - 16/12/2024 : ajout d'un paramètre "buffer_size" pour exporter les entités dans ce périmètre élargi et non dans le périmètre strict de "input_vector" (utile pour certains cas de figure)
 - 31/01/2025 : ajout de l'export d'un projet carto QGIS de référence de l'IGN pour visualisation des données (uniquement dans le cas d'un export BD TOPO en SHP -> chemins relatifs)
 - 12/02/2025 : ajout d'un paramètre "classes" pour choisir les classes exportés
-----------------------
A réfléchir / A faire :
 -
'''

# Import des bibliothèques Python
from __future__ import print_function
import os, argparse
from random import randint
from osgeo import ogr
from Lib_display import *
from Lib_log import timeLine
from Lib_text import readTextFileBySeparator, regExReplace
from Lib_file import removeVectorFile
from Lib_vector import getGeomPolygons, getProjection
from Lib_postgis import openConnection, executeQuery, getData, closeConnection, exportVectorByOgr2ogr

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 3

########################################################################
# FONCTION exportBdTopoFromPostgres()                                  #
########################################################################
def exportBdTopoFromPostgres(input_vector, output_directory, buffer_size=1000, input_metadata="/mnt/Geomatique/REF_DTER_OCC/BD_TOPO/000_Documentation/BD TOPO-Classes.csv", zone="FXX", classes=[], format_vector="ESRI Shapefile", extension_vector=".shp", postgis_ip_host="172.22.130.99", postgis_num_port=5435, postgis_user_name="postgres", postgis_password="postgres", postgis_database_name="bdtopo_v33_20221215", path_time_log=""):
    '''
    # ROLE :
    #     Exporter les classes BD TOPO montées en base Postgres, à partir d'un fichier d'emprise
    #
    # ENTREES DE LA FONCTION :
    #     input_vector : fichier vecteur d'emprise d'étude en entrée
    #     output_directory : répertoire de sortie des fichiers vecteur
    #     buffer_size : taille du tampon (en m) appliqué pour la sélection des entités dans le vecteur d'emprise d'étude en entrée. Par défaut, 1000
    #     input_metadata : fichier de métadonnées BD TOPO faisant la correspondance des noms de champs SQL-SHP
    #     zone : définition du territoire d'étude. Par défaut, FXX
    #     classes : liste des classes précises de la BD TOPO désirées (exemple : ["BATI:batiment", "TRANSPORT:troncon_de_route", "TRANSPORT:troncon_de_voie_ferree", "TRANSPORT:equipement_de_transport", "HYDROGRAPHIE:troncon_hydrographique", "HYDROGRAPHIE:surface_hydrographique"]). Par défaut, toutes les classes
    #     format_vector : format des fichiers vecteur. Par défaut : ESRI Shapefile
    #     extension_vector : extension des fichiers vecteur. Par défaut : .shp
    #     postgis_ip_host : nom du serveur PostGIS. Par défaut : 172.22.130.99
    #     postgis_num_port : numéro de port du serveur PostGIS. Par défaut : 5435
    #     postgis_user_name : nom d'utilisateur PostGIS. Par défaut : postgres
    #     postgis_password : mot de passe de l'utilisateur PostGIS. Par défaut : postgres
    #     postgis_database_name : nom de la base PostGIS. Par défaut : bdtopo_v33_20221215
    #     path_time_log : fichier log de sortie, par défaut vide (affichage console)
    #
    # SORTIES DE LA FONCTION :
    #     N.A.
    '''
    if debug >= 3:
        print(bold + green + "Exporter les classes BD TOPO montées en base Postgres, à partir d'un fichier d'emprise - Variables dans la fonction :" + endC)
        print(cyan + "    exportBdTopoFromPostgres() : " + endC + "input_vector : " + str(input_vector) + endC)
        print(cyan + "    exportBdTopoFromPostgres() : " + endC + "output_directory : " + str(output_directory) + endC)
        print(cyan + "    exportBdTopoFromPostgres() : " + endC + "buffer_size : " + str(buffer_size) + endC)
        print(cyan + "    exportBdTopoFromPostgres() : " + endC + "input_metadata : " + str(input_metadata) + endC)
        print(cyan + "    exportBdTopoFromPostgres() : " + endC + "zone : " + str(zone) + endC)
        print(cyan + "    exportBdTopoFromPostgres() : " + endC + "classes : " + str(classes) + endC)
        print(cyan + "    exportBdTopoFromPostgres() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "    exportBdTopoFromPostgres() : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "    exportBdTopoFromPostgres() : " + endC + "postgis_ip_host : " + str(postgis_ip_host) + endC)
        print(cyan + "    exportBdTopoFromPostgres() : " + endC + "postgis_num_port : " + str(postgis_num_port) + endC)
        print(cyan + "    exportBdTopoFromPostgres() : " + endC + "postgis_user_name : " + str(postgis_user_name) + endC)
        print(cyan + "    exportBdTopoFromPostgres() : " + endC + "postgis_password : " + str(postgis_password) + endC)
        print(cyan + "    exportBdTopoFromPostgres() : " + endC + "postgis_database_name : " + str(postgis_database_name) + endC)
        print(cyan + "    exportBdTopoFromPostgres() : " + endC + "path_time_log : " + str(path_time_log) + endC)

    # Définition des constantes
    ESRI_SHAPEFILE_DRIVER_NAME, GPKG_DRIVER_NAME = "ESRI Shapefile", "GPKG"
    PUBLIC_SCHEMA_NAME, BD_TOPO_ENCODING = "public", "UTF-8"
    SQL_GEOM_FIELD, SHP_GEOM_FIELD = "geometrie", "GEOM"
    QGIS_PROJECT_BASENAME = "Projets_Carto_BDT_3-3" + os.sep + "Projet_Carto_BDT_3-3_"

    CHECK_BD_TOPO_DICO = {"FRA":["fra_wgs84g",      4326, ["TRANSPORT:aerodrome", "ADMINISTRATIF:arrondissement", "ADMINISTRATIF:arrondissement_municipal", "HYDROGRAPHIE:bassin_versant_topographique", "BATI:batiment", "SERVICES_ET_ACTIVITES:canalisation", "BATI:cimetiere", "ADMINISTRATIF:collectivite_territoriale", "ADMINISTRATIF:commune", "ADMINISTRATIF:commune_associee_ou_deleguee", "ADMINISTRATIF:condominium", "BATI:construction_lineaire", "BATI:construction_ponctuelle", "BATI:construction_surfacique", "HYDROGRAPHIE:cours_d_eau", "ADMINISTRATIF:departement", "HYDROGRAPHIE:detail_hydrographique", "LIEUX_NOMMES:detail_orographique", "ADMINISTRATIF:epci", "TRANSPORT:equipement_de_transport", "SERVICES_ET_ACTIVITES:erp", "ZONES_REGLEMENTEES:foret_publique", "OCCUPATION_DU_SOL:haie", "TRANSPORT:itineraire_autre", "LIEUX_NOMMES:lieu_dit_non_habite", "SERVICES_ET_ACTIVITES:ligne_electrique", "BATI:ligne_orographique", "HYDROGRAPHIE:limite_terre_mer", "HYDROGRAPHIE:noeud_hydrographique", "TRANSPORT:non_communication", "ZONES_REGLEMENTEES:parc_ou_reserve", "TRANSPORT:piste_d_aerodrome", "HYDROGRAPHIE:plan_d_eau", "TRANSPORT:point_d_acces", "TRANSPORT:point_de_repere", "TRANSPORT:point_du_reseau", "SERVICES_ET_ACTIVITES:poste_de_transformation", "BATI:pylone", "ADMINISTRATIF:region", "BATI:reservoir", "TRANSPORT:route_numerotee_ou_nommee", "TRANSPORT:section_de_points_de_repere", "HYDROGRAPHIE:surface_hydrographique", "BATI:terrain_de_sport", "BATI:toponymie_bati", "HYDROGRAPHIE:toponymie_hydrographie", "LIEUX_NOMMES:toponymie_lieux_nommes", "SERVICES_ET_ACTIVITES:toponymie_services_et_activites", "TRANSPORT:toponymie_transport", "ZONES_REGLEMENTEES:toponymie_zones_reglementees", "TRANSPORT:transport_par_cable", "TRANSPORT:troncon_de_route", "TRANSPORT:troncon_de_voie_ferree", "HYDROGRAPHIE:troncon_hydrographique", "TRANSPORT:voie_ferree_nommee", "TRANSPORT:voie_nommee", "SERVICES_ET_ACTIVITES:zone_d_activite_ou_d_interet", "OCCUPATION_DU_SOL:zone_d_estran", "LIEUX_NOMMES:zone_d_habitation", "OCCUPATION_DU_SOL:zone_de_vegetation"]],
                          "FXX":["fxx_lamb93",      2154, ["TRANSPORT:aerodrome", "ADMINISTRATIF:arrondissement", "ADMINISTRATIF:arrondissement_municipal", "HYDROGRAPHIE:bassin_versant_topographique", "BATI:batiment", "SERVICES_ET_ACTIVITES:canalisation", "BATI:cimetiere", "ADMINISTRATIF:collectivite_territoriale", "ADMINISTRATIF:commune", "ADMINISTRATIF:commune_associee_ou_deleguee", "ADMINISTRATIF:condominium", "BATI:construction_lineaire", "BATI:construction_ponctuelle", "BATI:construction_surfacique", "HYDROGRAPHIE:cours_d_eau", "ADMINISTRATIF:departement", "HYDROGRAPHIE:detail_hydrographique", "LIEUX_NOMMES:detail_orographique", "ADMINISTRATIF:epci", "TRANSPORT:equipement_de_transport", "SERVICES_ET_ACTIVITES:erp", "ZONES_REGLEMENTEES:foret_publique", "OCCUPATION_DU_SOL:haie", "TRANSPORT:itineraire_autre", "LIEUX_NOMMES:lieu_dit_non_habite", "SERVICES_ET_ACTIVITES:ligne_electrique", "BATI:ligne_orographique", "HYDROGRAPHIE:limite_terre_mer", "HYDROGRAPHIE:noeud_hydrographique", "TRANSPORT:non_communication", "ZONES_REGLEMENTEES:parc_ou_reserve", "TRANSPORT:piste_d_aerodrome", "HYDROGRAPHIE:plan_d_eau", "TRANSPORT:point_d_acces", "TRANSPORT:point_de_repere", "TRANSPORT:point_du_reseau", "SERVICES_ET_ACTIVITES:poste_de_transformation", "BATI:pylone", "ADMINISTRATIF:region", "BATI:reservoir", "TRANSPORT:route_numerotee_ou_nommee", "TRANSPORT:section_de_points_de_repere", "HYDROGRAPHIE:surface_hydrographique", "BATI:terrain_de_sport", "BATI:toponymie_bati", "HYDROGRAPHIE:toponymie_hydrographie", "LIEUX_NOMMES:toponymie_lieux_nommes", "SERVICES_ET_ACTIVITES:toponymie_services_et_activites", "TRANSPORT:toponymie_transport", "ZONES_REGLEMENTEES:toponymie_zones_reglementees", "TRANSPORT:transport_par_cable", "TRANSPORT:troncon_de_route", "TRANSPORT:troncon_de_voie_ferree", "HYDROGRAPHIE:troncon_hydrographique", "TRANSPORT:voie_ferree_nommee", "TRANSPORT:voie_nommee", "SERVICES_ET_ACTIVITES:zone_d_activite_ou_d_interet", "OCCUPATION_DU_SOL:zone_d_estran", "LIEUX_NOMMES:zone_d_habitation", "OCCUPATION_DU_SOL:zone_de_vegetation"]],
                          "GLP":["glp_rgaf09utm20", 5490, ["TRANSPORT:aerodrome", "ADMINISTRATIF:arrondissement", "BATI:batiment", "SERVICES_ET_ACTIVITES:canalisation", "BATI:cimetiere", "ADMINISTRATIF:collectivite_territoriale", "ADMINISTRATIF:commune", "BATI:construction_lineaire", "BATI:construction_ponctuelle", "BATI:construction_surfacique", "HYDROGRAPHIE:cours_d_eau", "ADMINISTRATIF:departement", "HYDROGRAPHIE:detail_hydrographique", "LIEUX_NOMMES:detail_orographique", "ADMINISTRATIF:epci", "TRANSPORT:equipement_de_transport", "ZONES_REGLEMENTEES:foret_publique", "TRANSPORT:itineraire_autre", "LIEUX_NOMMES:lieu_dit_non_habite", "SERVICES_ET_ACTIVITES:ligne_electrique", "BATI:ligne_orographique", "HYDROGRAPHIE:limite_terre_mer", "HYDROGRAPHIE:noeud_hydrographique", "TRANSPORT:non_communication", "ZONES_REGLEMENTEES:parc_ou_reserve", "TRANSPORT:piste_d_aerodrome", "HYDROGRAPHIE:plan_d_eau", "TRANSPORT:point_du_reseau", "SERVICES_ET_ACTIVITES:poste_de_transformation", "BATI:pylone", "ADMINISTRATIF:region", "BATI:reservoir", "TRANSPORT:route_numerotee_ou_nommee", "HYDROGRAPHIE:surface_hydrographique", "BATI:terrain_de_sport", "BATI:toponymie_bati", "HYDROGRAPHIE:toponymie_hydrographie", "LIEUX_NOMMES:toponymie_lieux_nommes", "SERVICES_ET_ACTIVITES:toponymie_services_et_activites", "TRANSPORT:toponymie_transport", "ZONES_REGLEMENTEES:toponymie_zones_reglementees", "TRANSPORT:troncon_de_route", "TRANSPORT:troncon_de_voie_ferree", "HYDROGRAPHIE:troncon_hydrographique", "TRANSPORT:voie_nommee", "SERVICES_ET_ACTIVITES:zone_d_activite_ou_d_interet", "OCCUPATION_DU_SOL:zone_d_estran", "LIEUX_NOMMES:zone_d_habitation", "OCCUPATION_DU_SOL:zone_de_vegetation"]],
                          "GUF":["guf_utm22rgfg95", 2972, ["TRANSPORT:aerodrome", "ADMINISTRATIF:arrondissement", "HYDROGRAPHIE:bassin_versant_topographique", "BATI:batiment", "SERVICES_ET_ACTIVITES:canalisation", "BATI:cimetiere", "ADMINISTRATIF:collectivite_territoriale", "ADMINISTRATIF:commune", "BATI:construction_lineaire", "BATI:construction_ponctuelle", "BATI:construction_surfacique", "HYDROGRAPHIE:cours_d_eau", "ADMINISTRATIF:departement", "HYDROGRAPHIE:detail_hydrographique", "LIEUX_NOMMES:detail_orographique", "ADMINISTRATIF:epci", "TRANSPORT:equipement_de_transport", "SERVICES_ET_ACTIVITES:erp", "ZONES_REGLEMENTEES:foret_publique", "TRANSPORT:itineraire_autre", "LIEUX_NOMMES:lieu_dit_non_habite", "SERVICES_ET_ACTIVITES:ligne_electrique", "BATI:ligne_orographique", "HYDROGRAPHIE:limite_terre_mer", "HYDROGRAPHIE:noeud_hydrographique", "TRANSPORT:non_communication", "ZONES_REGLEMENTEES:parc_ou_reserve", "TRANSPORT:piste_d_aerodrome", "HYDROGRAPHIE:plan_d_eau", "TRANSPORT:point_du_reseau", "SERVICES_ET_ACTIVITES:poste_de_transformation", "BATI:pylone", "ADMINISTRATIF:region", "BATI:reservoir", "TRANSPORT:route_numerotee_ou_nommee", "HYDROGRAPHIE:surface_hydrographique", "BATI:terrain_de_sport", "BATI:toponymie_bati", "HYDROGRAPHIE:toponymie_hydrographie", "LIEUX_NOMMES:toponymie_lieux_nommes", "SERVICES_ET_ACTIVITES:toponymie_services_et_activites", "TRANSPORT:toponymie_transport", "ZONES_REGLEMENTEES:toponymie_zones_reglementees", "TRANSPORT:troncon_de_route", "TRANSPORT:troncon_de_voie_ferree", "HYDROGRAPHIE:troncon_hydrographique", "TRANSPORT:voie_ferree_nommee", "TRANSPORT:voie_nommee", "SERVICES_ET_ACTIVITES:zone_d_activite_ou_d_interet", "OCCUPATION_DU_SOL:zone_d_estran", "LIEUX_NOMMES:zone_d_habitation", "OCCUPATION_DU_SOL:zone_de_vegetation"]],
                          "MTQ":["mtq_rgaf09utm20", 5490, ["TRANSPORT:aerodrome", "ADMINISTRATIF:arrondissement", "BATI:batiment", "SERVICES_ET_ACTIVITES:canalisation", "BATI:cimetiere", "ADMINISTRATIF:collectivite_territoriale", "ADMINISTRATIF:commune", "BATI:construction_lineaire", "BATI:construction_ponctuelle", "BATI:construction_surfacique", "HYDROGRAPHIE:cours_d_eau", "ADMINISTRATIF:departement", "HYDROGRAPHIE:detail_hydrographique", "LIEUX_NOMMES:detail_orographique", "ADMINISTRATIF:epci", "TRANSPORT:equipement_de_transport", "ZONES_REGLEMENTEES:foret_publique", "TRANSPORT:itineraire_autre", "LIEUX_NOMMES:lieu_dit_non_habite", "SERVICES_ET_ACTIVITES:ligne_electrique", "BATI:ligne_orographique", "HYDROGRAPHIE:limite_terre_mer", "HYDROGRAPHIE:noeud_hydrographique", "TRANSPORT:non_communication", "ZONES_REGLEMENTEES:parc_ou_reserve", "TRANSPORT:piste_d_aerodrome", "HYDROGRAPHIE:plan_d_eau", "TRANSPORT:point_de_repere", "TRANSPORT:point_du_reseau", "SERVICES_ET_ACTIVITES:poste_de_transformation", "BATI:pylone", "ADMINISTRATIF:region", "BATI:reservoir", "TRANSPORT:route_numerotee_ou_nommee", "TRANSPORT:section_de_points_de_repere", "HYDROGRAPHIE:surface_hydrographique", "BATI:terrain_de_sport", "BATI:toponymie_bati", "HYDROGRAPHIE:toponymie_hydrographie", "LIEUX_NOMMES:toponymie_lieux_nommes", "SERVICES_ET_ACTIVITES:toponymie_services_et_activites", "TRANSPORT:toponymie_transport", "ZONES_REGLEMENTEES:toponymie_zones_reglementees", "TRANSPORT:troncon_de_route", "TRANSPORT:troncon_de_voie_ferree", "HYDROGRAPHIE:troncon_hydrographique", "TRANSPORT:voie_ferree_nommee", "TRANSPORT:voie_nommee", "SERVICES_ET_ACTIVITES:zone_d_activite_ou_d_interet", "OCCUPATION_DU_SOL:zone_d_estran", "LIEUX_NOMMES:zone_d_habitation", "OCCUPATION_DU_SOL:zone_de_vegetation"]],
                          "MYT":["myt_rgm04utm38s", 4471, ["TRANSPORT:aerodrome", "HYDROGRAPHIE:bassin_versant_topographique", "BATI:batiment", "BATI:cimetiere", "ADMINISTRATIF:collectivite_territoriale", "ADMINISTRATIF:commune", "BATI:construction_lineaire", "BATI:construction_ponctuelle", "BATI:construction_surfacique", "HYDROGRAPHIE:cours_d_eau", "ADMINISTRATIF:departement", "HYDROGRAPHIE:detail_hydrographique", "LIEUX_NOMMES:detail_orographique", "ADMINISTRATIF:epci", "TRANSPORT:equipement_de_transport", "ZONES_REGLEMENTEES:foret_publique", "TRANSPORT:itineraire_autre", "LIEUX_NOMMES:lieu_dit_non_habite", "SERVICES_ET_ACTIVITES:ligne_electrique", "BATI:ligne_orographique", "HYDROGRAPHIE:limite_terre_mer", "HYDROGRAPHIE:noeud_hydrographique", "ZONES_REGLEMENTEES:parc_ou_reserve", "TRANSPORT:piste_d_aerodrome", "HYDROGRAPHIE:plan_d_eau", "TRANSPORT:point_du_reseau", "SERVICES_ET_ACTIVITES:poste_de_transformation", "BATI:pylone", "ADMINISTRATIF:region", "BATI:reservoir", "TRANSPORT:route_numerotee_ou_nommee", "HYDROGRAPHIE:surface_hydrographique", "BATI:terrain_de_sport", "BATI:toponymie_bati", "HYDROGRAPHIE:toponymie_hydrographie", "LIEUX_NOMMES:toponymie_lieux_nommes", "SERVICES_ET_ACTIVITES:toponymie_services_et_activites", "TRANSPORT:toponymie_transport", "ZONES_REGLEMENTEES:toponymie_zones_reglementees", "TRANSPORT:transport_par_cable", "TRANSPORT:troncon_de_route", "HYDROGRAPHIE:troncon_hydrographique", "TRANSPORT:voie_nommee", "SERVICES_ET_ACTIVITES:zone_d_activite_ou_d_interet", "OCCUPATION_DU_SOL:zone_d_estran", "LIEUX_NOMMES:zone_d_habitation", "OCCUPATION_DU_SOL:zone_de_vegetation"]],
                          "REU":["reu_rgr92utm40s", 2975, ["TRANSPORT:aerodrome", "ADMINISTRATIF:arrondissement", "HYDROGRAPHIE:bassin_versant_topographique", "BATI:batiment", "SERVICES_ET_ACTIVITES:canalisation", "BATI:cimetiere", "ADMINISTRATIF:collectivite_territoriale", "ADMINISTRATIF:commune", "BATI:construction_lineaire", "BATI:construction_ponctuelle", "BATI:construction_surfacique", "HYDROGRAPHIE:cours_d_eau", "ADMINISTRATIF:departement", "HYDROGRAPHIE:detail_hydrographique", "LIEUX_NOMMES:detail_orographique", "ADMINISTRATIF:epci", "TRANSPORT:equipement_de_transport", "ZONES_REGLEMENTEES:foret_publique", "TRANSPORT:itineraire_autre", "LIEUX_NOMMES:lieu_dit_non_habite", "SERVICES_ET_ACTIVITES:ligne_electrique", "BATI:ligne_orographique", "HYDROGRAPHIE:limite_terre_mer", "HYDROGRAPHIE:noeud_hydrographique", "TRANSPORT:non_communication", "ZONES_REGLEMENTEES:parc_ou_reserve", "TRANSPORT:piste_d_aerodrome", "HYDROGRAPHIE:plan_d_eau", "TRANSPORT:point_de_repere", "TRANSPORT:point_du_reseau", "SERVICES_ET_ACTIVITES:poste_de_transformation", "BATI:pylone", "ADMINISTRATIF:region", "BATI:reservoir", "TRANSPORT:route_numerotee_ou_nommee", "TRANSPORT:section_de_points_de_repere", "HYDROGRAPHIE:surface_hydrographique", "BATI:terrain_de_sport", "BATI:toponymie_bati", "HYDROGRAPHIE:toponymie_hydrographie", "LIEUX_NOMMES:toponymie_lieux_nommes", "SERVICES_ET_ACTIVITES:toponymie_services_et_activites", "TRANSPORT:toponymie_transport", "ZONES_REGLEMENTEES:toponymie_zones_reglementees", "TRANSPORT:transport_par_cable", "TRANSPORT:troncon_de_route", "TRANSPORT:troncon_de_voie_ferree", "HYDROGRAPHIE:troncon_hydrographique", "TRANSPORT:voie_nommee", "SERVICES_ET_ACTIVITES:zone_d_activite_ou_d_interet", "OCCUPATION_DU_SOL:zone_d_estran", "LIEUX_NOMMES:zone_d_habitation", "OCCUPATION_DU_SOL:zone_de_vegetation"]],
                          "BLM":["sba_rgaf09utm20", 5490, ["TRANSPORT:aerodrome", "BATI:batiment", "BATI:cimetiere", "ADMINISTRATIF:collectivite_territoriale", "BATI:construction_lineaire", "BATI:construction_ponctuelle", "HYDROGRAPHIE:cours_d_eau", "HYDROGRAPHIE:detail_hydrographique", "LIEUX_NOMMES:detail_orographique", "TRANSPORT:equipement_de_transport", "TRANSPORT:itineraire_autre", "BATI:ligne_orographique", "HYDROGRAPHIE:limite_terre_mer", "HYDROGRAPHIE:noeud_hydrographique", "ZONES_REGLEMENTEES:parc_ou_reserve", "TRANSPORT:piste_d_aerodrome", "HYDROGRAPHIE:plan_d_eau", "TRANSPORT:point_du_reseau", "BATI:reservoir", "TRANSPORT:route_numerotee_ou_nommee", "HYDROGRAPHIE:surface_hydrographique", "BATI:terrain_de_sport", "BATI:toponymie_bati", "HYDROGRAPHIE:toponymie_hydrographie", "LIEUX_NOMMES:toponymie_lieux_nommes", "SERVICES_ET_ACTIVITES:toponymie_services_et_activites", "TRANSPORT:toponymie_transport", "ZONES_REGLEMENTEES:toponymie_zones_reglementees", "TRANSPORT:troncon_de_route", "HYDROGRAPHIE:troncon_hydrographique", "TRANSPORT:voie_nommee", "SERVICES_ET_ACTIVITES:zone_d_activite_ou_d_interet", "OCCUPATION_DU_SOL:zone_d_estran", "LIEUX_NOMMES:zone_d_habitation", "OCCUPATION_DU_SOL:zone_de_vegetation"]],
                          "MAF":["sma_rgaf09utm20", 5490, ["TRANSPORT:aerodrome", "BATI:batiment", "BATI:cimetiere", "ADMINISTRATIF:collectivite_territoriale", "BATI:construction_lineaire", "BATI:construction_ponctuelle", "HYDROGRAPHIE:cours_d_eau", "HYDROGRAPHIE:detail_hydrographique", "LIEUX_NOMMES:detail_orographique", "TRANSPORT:equipement_de_transport", "TRANSPORT:itineraire_autre", "LIEUX_NOMMES:lieu_dit_non_habite", "SERVICES_ET_ACTIVITES:ligne_electrique", "BATI:ligne_orographique", "HYDROGRAPHIE:limite_terre_mer", "HYDROGRAPHIE:noeud_hydrographique", "ZONES_REGLEMENTEES:parc_ou_reserve", "TRANSPORT:piste_d_aerodrome", "HYDROGRAPHIE:plan_d_eau", "TRANSPORT:point_du_reseau", "BATI:pylone", "BATI:reservoir", "TRANSPORT:route_numerotee_ou_nommee", "HYDROGRAPHIE:surface_hydrographique", "BATI:terrain_de_sport", "BATI:toponymie_bati", "HYDROGRAPHIE:toponymie_hydrographie", "LIEUX_NOMMES:toponymie_lieux_nommes", "SERVICES_ET_ACTIVITES:toponymie_services_et_activites", "TRANSPORT:toponymie_transport", "ZONES_REGLEMENTEES:toponymie_zones_reglementees", "TRANSPORT:troncon_de_route", "HYDROGRAPHIE:troncon_hydrographique", "TRANSPORT:voie_nommee", "SERVICES_ET_ACTIVITES:zone_d_activite_ou_d_interet", "OCCUPATION_DU_SOL:zone_d_estran", "LIEUX_NOMMES:zone_d_habitation", "OCCUPATION_DU_SOL:zone_de_vegetation"]],
                          "SPM":["spm_rgspm06u21",  4467, ["TRANSPORT:aerodrome", "BATI:batiment", "BATI:cimetiere", "ADMINISTRATIF:collectivite_territoriale", "ADMINISTRATIF:commune", "BATI:construction_lineaire", "BATI:construction_ponctuelle", "HYDROGRAPHIE:cours_d_eau", "HYDROGRAPHIE:detail_hydrographique", "LIEUX_NOMMES:detail_orographique", "TRANSPORT:equipement_de_transport", "TRANSPORT:itineraire_autre", "LIEUX_NOMMES:lieu_dit_non_habite", "BATI:ligne_orographique", "HYDROGRAPHIE:limite_terre_mer", "HYDROGRAPHIE:noeud_hydrographique", "TRANSPORT:piste_d_aerodrome", "HYDROGRAPHIE:plan_d_eau", "TRANSPORT:point_du_reseau", "BATI:reservoir", "TRANSPORT:route_numerotee_ou_nommee", "HYDROGRAPHIE:surface_hydrographique", "BATI:terrain_de_sport", "BATI:toponymie_bati", "HYDROGRAPHIE:toponymie_hydrographie", "LIEUX_NOMMES:toponymie_lieux_nommes", "SERVICES_ET_ACTIVITES:toponymie_services_et_activites", "TRANSPORT:toponymie_transport", "TRANSPORT:troncon_de_route", "HYDROGRAPHIE:troncon_hydrographique", "TRANSPORT:voie_nommee", "SERVICES_ET_ACTIVITES:zone_d_activite_ou_d_interet", "OCCUPATION_DU_SOL:zone_d_estran", "LIEUX_NOMMES:zone_d_habitation", "OCCUPATION_DU_SOL:zone_de_vegetation"]]}
    AVAILABLE_ZONE_LIST = list(CHECK_BD_TOPO_DICO.keys())

    # Définition des variables
    postgis_schema_name = CHECK_BD_TOPO_DICO[zone][0]
    epsg = CHECK_BD_TOPO_DICO[zone][1]
    if not classes:
        available_classes_list = CHECK_BD_TOPO_DICO[zone][2]
    else:
        available_classes_list = classes
    rand_nb = randint(111111111111, 999999999999)

    ####################################################################

    if debug >= 2:
        print(cyan + "exportBdTopoFromPostgres() : " + bold + green + "DEBUT DES TRAITEMENTS" + endC)

    # Mise à jour du log
    starting_event = "exportBdTopoFromPostgres() : Début du traitement : "
    timeLine(path_time_log, starting_event)

    # Test existence du fichier vecteur d'entrée
    if not os.path.exists(input_vector):
        print(cyan + "exportBdTopoFromPostgres() : " + bold + red + "Error: Input vector file \"%s\" not exists!" % input_vector + endC, file=sys.stderr)
        exit(-1)

    # Définition du format du fichier vecteur d'emprise d'étude en entrée
    format_vector_list = [ogr.GetDriver(i).GetDescription() for i in range(ogr.GetDriverCount())]
    i = 0
    for input_format_vector in format_vector_list:
        driver = ogr.GetDriverByName(input_format_vector)
        data_source_input = driver.Open(input_vector, 0)
        if data_source_input is not None:
            data_source_input.Destroy()
            break
        i += 1
    input_format_vector = format_vector_list[i]

    # Test format vecteur de sortie
    if not format_vector in [ESRI_SHAPEFILE_DRIVER_NAME, GPKG_DRIVER_NAME]:
        print(cyan + "exportBdTopoFromPostgres() : " + bold + red + "Error: Vector format \"%s\" is not recognize (must be \"%s\" or \"%s\")!" % (format_vector, ESRI_SHAPEFILE_DRIVER_NAME, GPKG_DRIVER_NAME) + endC, file=sys.stderr)
        exit(-1)

    # Test zone d'étude
    if not zone in AVAILABLE_ZONE_LIST:
        print(cyan + "exportBdTopoFromPostgres() : " + bold + red + "Error: Zone \"%s\" is not in the available zones (%s)!" % (zone, str(AVAILABLE_ZONE_LIST)) + endC, file=sys.stderr)
        exit(-1)

    # Test de conformité des classes sélectionnés
    if classes:
        bool_list = [classe in CHECK_BD_TOPO_DICO[zone][2] for classe in classes]
        if not all(bool_list):
            print(cyan + "exportBdTopoFromPostgres() : " + bold + red + "Error: Class %s are not availables for zone '%s'!" % ([x for x, m in zip(classes, bool_list) if not m],zone) + endC, file=sys.stderr)
            exit(-1)

    # Test concordance EPSG du fichier vecteur d'entrée et de la base Postgres
    epsg_input_vector, projection = getProjection(input_vector, format_vector=input_format_vector)
    if epsg != epsg_input_vector:
        print(cyan + "exportBdTopoFromPostgres() : " + bold + red + "Error: Input vector file EPSG (%s) is not corresponding to requested BD TOPO database EPSG (%s)!" % (epsg_input_vector, epsg) + endC, file=sys.stderr)
        exit(-1)

    # Récupération de l'emprise d'étude
    geometry_list = getGeomPolygons(input_vector, col=None, value=None, format_vector=input_format_vector)
    if len(geometry_list) == 0:
        print(cyan + "exportBdTopoFromPostgres() : " + bold + red + "Error: There are no geometry in the input vector file \"%s\"!" % input_vector + endC, file=sys.stderr)
        exit(-1)
    elif len(geometry_list) > 1:
        print(cyan + "exportBdTopoFromPostgres() : " + bold + red + "Error: There are more than one geometry in the input vector file \"%s\" (%s geometries)!" % (input_vector, len(geometry_list)) + endC, file=sys.stderr)
        exit(-1)
    else:
        geometry_roi = geometry_list[0].ExportToWkt()
        if buffer_size > 0:
            geometry_roi = geometry_list[0].Buffer(buffer_size).ExportToWkt()

    # Récupération des métadonnées BD TOPO (correspondance des noms de champs SQL-SHP)
    if format_vector == ESRI_SHAPEFILE_DRIVER_NAME:
        if not os.path.exists(input_metadata):
            print(cyan + "exportBdTopoFromPostgres() : " + bold + red + "Error: Input metadata file \"%s\" not exists!" % input_metadata + endC, file=sys.stderr)
            exit(-1)
        else:
            metadata_bd_topo = readTextFileBySeparator(input_metadata, "#")

    ####################################################################
    if debug >= 2:
        print(cyan + "exportBdTopoFromPostgres() : " + bold + green + "Début des exports." + endC)

    # Boucle sur les classes à exporter
    idx = 1
    tables_to_clean_list = []
    for theme_classe in available_classes_list:
        bd_topo_theme = theme_classe.split(":")[0]
        bd_topo_classe = theme_classe.split(":")[1]
        table_to_extract_select = "%s_select%s" % (bd_topo_classe, str(rand_nb))
        if debug >= 3:
            print(cyan + "exportBdTopoFromPostgres() : " + bold + green + "Traitement de la classe \"%s\" (%s/%s)..." % (bd_topo_classe, str(idx), str(len(available_classes_list))) + endC)

        # Construction du nom du fichier de sortie
        if format_vector == GPKG_DRIVER_NAME:
            if not os.path.exists(output_directory):
                os.makedirs(output_directory)
            database_name_split, schema_name_split = postgis_database_name.split("_"), postgis_schema_name.split("_")
            aoi_name = regExReplace(os.path.basename(os.path.splitext(input_vector)[0]), regex="[a-zA-Z0-9]", regex_replace="")
            bd_topo_version = "%s-%s" % (database_name_split[1], database_name_split[2])
            bd_topo_format = extension_vector[1:]
            bd_topo_rig = schema_name_split[1]
            bd_topo_info = "%s-ED%s-%s-%s" % (aoi_name, database_name_split[7], database_name_split[8], database_name_split[9])
            output_basename = "BDT_%s_%s_%s_%s" % (bd_topo_version, bd_topo_format, bd_topo_rig, bd_topo_info)
            output_vector_file = output_directory + os.sep + output_basename.upper() + extension_vector
        else:
            output_theme_directory = output_directory + os.sep + bd_topo_theme
            if not os.path.exists(output_theme_directory):
                os.makedirs(output_theme_directory)
            output_vector_file = output_theme_directory + os.sep + bd_topo_classe.upper() + extension_vector
            removeVectorFile(output_vector_file, format_vector=format_vector)

        # Construction de la requête d'export
        select_query = "*"
        if format_vector == ESRI_SHAPEFILE_DRIVER_NAME:
            select_query = ""
            for text in metadata_bd_topo:
                if text[0] == bd_topo_classe:
                    select_query += "b.%s AS %s, " % (text[2], text[1])
            select_query += "b.%s AS %s" % (SQL_GEOM_FIELD, SHP_GEOM_FIELD)
        query = "DROP TABLE IF EXISTS %s;\n" % table_to_extract_select
        query += "CREATE TABLE %s AS\n" % table_to_extract_select
        query += "    SELECT %s\n" % select_query
        query += "    FROM %s.%s AS b\n" % (postgis_schema_name, bd_topo_classe)
        query += "    WHERE ST_Intersects(b.%s, 'SRID=%s;%s');\n" % (SQL_GEOM_FIELD, str(epsg), geometry_roi)

        # Exécution de la requête d'export
        connection = openConnection(postgis_database_name, user_name=postgis_user_name, password=postgis_password, ip_host=postgis_ip_host, num_port=postgis_num_port, schema_name=PUBLIC_SCHEMA_NAME)
        if debug >= 4:
            print(query)
        executeQuery(connection, query)
        row_number = getData(connection, table_to_extract_select, "COUNT(*)", condition="")[0][0]
        closeConnection(connection)

        # Export de la table intersectée à l'emprise d'étude
        if row_number > 0:
            if format_vector == GPKG_DRIVER_NAME:
                ogr2ogr_more_parameters = "-nln %s -overwrite" % bd_topo_classe
            if format_vector == ESRI_SHAPEFILE_DRIVER_NAME:
                ogr2ogr_more_parameters = "-lco ENCODING=%s" % BD_TOPO_ENCODING
            exportVectorByOgr2ogr(postgis_database_name, output_vector_file, table_to_extract_select, user_name=postgis_user_name, password=postgis_password, ip_host=postgis_ip_host, num_port=postgis_num_port, schema_name=PUBLIC_SCHEMA_NAME, format_type=format_vector, ogr2ogr_more_parameters=ogr2ogr_more_parameters)
        else:
            print(cyan + "exportBdTopoFromPostgres() : " + bold + yellow + "L'emprise d'étude n'intersecte pas d'entités pour la classe \"%s\"." % bd_topo_classe + endC)

        tables_to_clean_list.append(table_to_extract_select)
        idx += 1

    # Copie du projet carto QGIS
    if format_vector == ESRI_SHAPEFILE_DRIVER_NAME:
        input_project = os.path.dirname(input_metadata) + os.sep + QGIS_PROJECT_BASENAME + zone + ".qgs"
        output_project = output_directory + os.sep + os.path.basename(input_project)
        if os.path.exists(input_project):
            os.system("cp -ruv \"%s\" \"%s\"" % (input_project, output_project))

    if debug >= 2:
        print(cyan + "exportBdTopoFromPostgres() : " + bold + green + "Fin des exports." + endC)

    ####################################################################

    # Suppression des tables temporaires
    query_clean = ""
    for table_to_clean in tables_to_clean_list:
        query_clean += "DROP TABLE IF EXISTS %s;\n" % table_to_clean
    connection = openConnection(postgis_database_name, user_name=postgis_user_name, password=postgis_password, ip_host=postgis_ip_host, num_port=postgis_num_port, schema_name=PUBLIC_SCHEMA_NAME)
    if debug >= 4:
        print(cyan + "exportBdTopoFromPostgres() : " + bold + green + "Nettoyage des tables temporaires dans la base Postgres..." + endC)
        print(query_clean)
    executeQuery(connection, query_clean)
    closeConnection(connection)

    # Mise à jour du log
    ending_event = "exportBdTopoFromPostgres() : Fin du traitement : "
    timeLine(path_time_log, ending_event)

    if debug >= 2:
        print(cyan + "exportBdTopoFromPostgres() : " + bold + green + "FIN DES TRAITEMENTS" + endC)

    return 0

#############################################################################################################################
################################################## Mise en place du parser ##################################################
#############################################################################################################################

def main(gui=False):
    parser = argparse.ArgumentParser(prog = "ExportBdTopoFromPostgres", description = "\
    Exporter les classes BD TOPO montées en base Postgres, à partir d'un fichier d'emprise. \n\
    Exemple : python3 -m ExportBdTopoFromPostgres -in /mnt/RAM_disk/emprise_etude.shp \n\
                                                  -out /mnt/RAM_disk/BD_TOPO \n\
                                                  -buf 1000 \n\
                                                  -imd /mnt/Data/10_Agents_travaux_en_cours/Benjamin/data/a_copier/geomatique/REF_DTER_OCC/BD_TOPO/000_Documentation/BD TOPO-Classes.csv \n\
                                                  -zone FXX")

    parser.add_argument("-in", "--input_vector", default="", type=str, required=True, help="Input vector file.")
    parser.add_argument("-out", "--output_directory", default="", type=str, required=True, help="Output directory.")
    parser.add_argument("-buf", "--buffer_size", default=1000, type=float, required=False, help="Buffer size (in meters) applied for feature selection from input vector file. Default: 1000")
    parser.add_argument("-imd", "--input_metadata", default="/mnt/Geomatique/REF_DTER_OCC/BD_TOPO/000_Documentation/BD TOPO-Classes.csv", type=str, required=False, help="Input BD TOPO metadata file mapping SQL-SHP fields names.")
    parser.add_argument("-zone", "--zone", choices=["FRA","FXX","GLP","MTQ","GUF","REU","MYT","SPM","BLM","MAF"], default="FXX", type=str, required=False, help="Zone to be treated to extract BD TOPO. Default: FXX.")
    parser.add_argument('-classes', '--classes_list', default="", type=str, nargs="+", required=False, help="Classes to extract from the BD TOPO database. Default: [].")
    parser.add_argument("-vef", "--format_vector", choices=["ESRI Shapefile", "GPKG"], default="ESRI Shapefile", type=str, required=False, help="Format of vector files. Default: ESRI Shapefile.")
    parser.add_argument("-vee", "--extension_vector", choices=[".shp", ".gpkg"], default=".shp", type=str, required=False, help="Extension file for vector files. Default: .shp.")
    parser.add_argument("-pgh", "--postgis_ip_host", default="172.22.130.99", type=str, required=False, help="PostGIS server name or IP adress. Default: 172.22.130.99.")
    parser.add_argument("-pgp", "--postgis_num_port", default=5435, type=int, required=False, help="PostGIS port number. Default: 5435.")
    parser.add_argument("-pgu", "--postgis_user_name", default="postgres", type=str, required=False, help="PostGIS user name. Default: postgres.")
    parser.add_argument("-pgw", "--postgis_password", default="postgres", type=str, required=False, help="PostGIS user password. Default: postgres.")
    parser.add_argument("-pgd", "--postgis_database_name", default="bdtopo_v33_20221215", type=str, required=False, help="PostGIS database name. Default: bdtopo_v33_20221215.")
    parser.add_argument("-log", "--path_time_log", default="", type=str, required=False, help="Option: Name of log. Default, no log file.")
    parser.add_argument("-debug", "--debug", default=3, type=int, required=False, help="Option: Value of level debug trace. Default, 3.")
    args = displayIHM(gui, parser)

    # Récupération du fichier vecteur d'entrée
    if args.input_vector != None:
        input_vector = args.input_vector
        if not os.path.isfile(input_vector):
            raise NameError (cyan + "ExportBdTopoFromPostgres: " + bold + red  + "File \"%s\" not exists (input_vector)." % input_vector + endC)

    # Récupération du répertoire de sortie
    if args.output_directory != None:
        output_directory = args.output_directory

    # Récupération de la taille du tampon de sélection
    if args.buffer_size != None:
        buffer_size = args.buffer_size

    # Récupération du fichier des métadonnées BD TOPO
    if args.input_metadata != None:
        input_metadata = args.input_metadata

    # Récupération des paramètres spécifiques à la zone
    if args.zone != None:
        zone = args.zone

    # Récupération des paramètres spécifiques aux champs
    if args.classes_list != None:
        classes = args.classes_list

    # Récupération des paramètres fichiers
    if args.format_vector != None:
        format_vector = args.format_vector
    if args.extension_vector != None:
        extension_vector = args.extension_vector

    # Récupération des paramètres PostGIS
    if args.postgis_ip_host != None:
        postgis_ip_host = args.postgis_ip_host
    if args.postgis_num_port != None:
        postgis_num_port = args.postgis_num_port
    if args.postgis_user_name != None:
        postgis_user_name = args.postgis_user_name
    if args.postgis_password != None:
        postgis_password = args.postgis_password
    if args.postgis_database_name != None:
        postgis_database_name = args.postgis_database_name

    # Récupération des paramètres généraux
    if args.path_time_log != None:
        path_time_log = args.path_time_log
    if args.debug != None:
        global debug
        debug = args.debug

    if debug >= 3:
        print(bold + green + "Exporter les classes BD TOPO montées en base Postgres, à partir d'un fichier d'emprise - Variables dans le parser :" + endC)
        print(cyan + "    ExportBdTopoFromPostgres : " + endC + "input_vector : " + str(input_vector) + endC)
        print(cyan + "    ExportBdTopoFromPostgres : " + endC + "output_directory : " + str(output_directory) + endC)
        print(cyan + "    ExportBdTopoFromPostgres : " + endC + "buffer_size : " + str(buffer_size) + endC)
        print(cyan + "    ExportBdTopoFromPostgres : " + endC + "input_metadata : " + str(input_metadata) + endC)
        print(cyan + "    ExportBdTopoFromPostgres : " + endC + "zone : " + str(zone) + endC)
        print(cyan + "    ExportBdTopoFromPostgres : " + endC + "classes : " + str(classes) + endC)
        print(cyan + "    ExportBdTopoFromPostgres : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "    ExportBdTopoFromPostgres : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "    ExportBdTopoFromPostgres : " + endC + "postgis_ip_host : " + str(postgis_ip_host) + endC)
        print(cyan + "    ExportBdTopoFromPostgres : " + endC + "postgis_num_port : " + str(postgis_num_port) + endC)
        print(cyan + "    ExportBdTopoFromPostgres : " + endC + "postgis_user_name : " + str(postgis_user_name) + endC)
        print(cyan + "    ExportBdTopoFromPostgres : " + endC + "postgis_password : " + str(postgis_password) + endC)
        print(cyan + "    ExportBdTopoFromPostgres : " + endC + "postgis_database_name : " + str(postgis_database_name) + endC)
        print(cyan + "    ExportBdTopoFromPostgres : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "    ExportBdTopoFromPostgres : " + endC + "debug : " + str(debug) + endC)

    # EXECUTION DE LA FONCTION
    exportBdTopoFromPostgres(input_vector, output_directory, buffer_size, input_metadata, zone, classes, format_vector, extension_vector, postgis_ip_host, postgis_num_port, postgis_user_name, postgis_password, postgis_database_name, path_time_log)

if __name__ == "__main__":
    main(gui=False)

