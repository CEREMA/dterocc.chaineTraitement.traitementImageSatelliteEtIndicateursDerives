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
        - les valeurs possibles pour le paramètre 'zone' sont : "FRA" / "FXX" / "GLP" / "GUF" / "MTQ" / "MYT" / "REU" / "SPM"
            correspondant respectivement à : France entière (EPSG 4326) / France Métropolitaine (EPSG 2154) / Guadeloupe (EPSG 5490) / Guyane (EPSG 2972) / Martinique (EPSG 5490) / Mayotte (EPSG 4471) / Réunion (EPSG 2975) / Saint-Pierre-et-Miquelon (EPSG 4467)
        - ne gère que les formats SHP et GPKG (fichier unique multi-couches) en sortie (formats de référence IGN) :
            * valeurs possibles pour le paramètre 'format_vector' : "ESRI Shapefile" / "GPKG"
            * valeurs possibles pour le paramètre 'extension_vector' : ".shp" / ".gpkg"
    Limites :
        - peut ne pas fonctionner correctement pour des versions de la BD TOPO autres que v3.3 (surtout en export "ESRI Shapefile")
        - les données pour Saint-Barthélemy ("BLM" / EPSG 5490) et Saint-Martin ("MAF" / EPSG 5490) ne sont pas encore disponibles à l'export (mais disponibles en téléchargement direct sur le site de l'IGN)

-----------------
Outils utilisés :
 - PostgreSQL/PostGIS

------------------------------
Historique des modifications :
 - 29/02/2024 : création

-----------------------
A réfléchir / A faire :
 -
'''

# Import des bibliothèques Python
from __future__ import print_function
import os, sys, argparse
from Lib_display import *
from Lib_log import timeLine
from Lib_text import regExReplace
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
def exportBdTopoFromPostgres(input_vector, output_directory, zone="FXX", format_vector="ESRI Shapefile", extension_vector=".shp", postgis_ip_host="172.22.130.99", postgis_num_port=5432, postgis_user_name="postgres", postgis_password="postgres", postgis_database_name="bdtopo_3_3_tousthemes_sql_scr_xxx_2022_12_15", path_time_log=""):
    '''
    # ROLE :
    #     Exporter les classes BD TOPO montées en base Postgres, à partir d'un fichier d'emprise
    #
    # ENTREES DE LA FONCTION :
    #     input_vector : fichier vecteur d'emprise d'étude en entrée
    #     output_directory : répertoire de sortie des fichiers vecteur
    #     zone : définition du territoire d'étude. Par défaut, 'FXX'
    #     format_vector : format des fichiers vecteur. Par défaut : 'ESRI Shapefile'
    #     extension_vector : extension des fichiers vecteur. Par défaut : '.shp'
    #     postgis_ip_host : nom du serveur PostGIS. Par défaut : '172.22.130.99'
    #     postgis_num_port : numéro de port du serveur PostGIS. Par défaut : 5432
    #     postgis_user_name : nom d'utilisateur PostGIS. Par défaut : 'postgres'
    #     postgis_password : mot de passe de l'utilisateur PostGIS. Par défaut : 'postgres'
    #     postgis_database_name : nom de la base PostGIS. Par défaut : 'bdtopo_3_3_tousthemes_sql_scr_xxx_2022_12_15'
    #     path_time_log : fichier log de sortie, par défaut vide (affichage console)
    #
    # SORTIES DE LA FONCTION :
    #     N.A.
    '''
    if debug >= 3:
        print('\n' + bold + green + "Exporter les classes BD TOPO montées en base Postgres, à partir d'un fichier d'emprise - Variables dans la fonction :" + endC)
        print(cyan + "    exportBdTopoFromPostgres() : " + endC + "input_vector : " + str(input_vector) + endC)
        print(cyan + "    exportBdTopoFromPostgres() : " + endC + "output_directory : " + str(output_directory) + endC)
        print(cyan + "    exportBdTopoFromPostgres() : " + endC + "zone : " + str(zone) + endC)
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
    AVAILABLE_ZONE_LIST = ["FRA","FXX","GLP","MTQ","GUF","REU","MYT","SPM"]#,"BLM","MAF"]
    PUBLIC_SCHEMA_NAME, TOPONYMY_TABLE_NAME, BD_TOPO_ENCODING = "public", "toponymie", "UTF-8"
    SQL_IDENTIFIER_FIELD, SQL_IDENTIFIER_TOPONYMY_FIELD, SQL_GEOM_FIELD = "cleabs", "cleabs_de_l_objet", "geometrie"
    SHP_IDENTIFIER_FIELD, SHP_IDENTIFIER_TOPONYMY_FIELD, SHP_GEOM_FIELD = "ID", "ID", "GEOM"

    CHECK_BD_TOPO_DICO = {"FRA":["fra_wgs84g",      4326, ["aerodrome", "arrondissement", "arrondissement_municipal", "bassin_versant_topographique", "batiment", "canalisation", "cimetiere", "collectivite_territoriale", "commune", "commune_associee_ou_deleguee", "condominium", "construction_lineaire", "construction_ponctuelle", "construction_surfacique", "cours_d_eau", "departement", "detail_hydrographique", "detail_orographique", "epci", "equipement_de_transport", "erp", "foret_publique", "haie", "itineraire_autre", "lieu_dit_non_habite", "ligne_electrique", "ligne_orographique", "limite_terre_mer", "noeud_hydrographique", "non_communication", "parc_ou_reserve", "piste_d_aerodrome", "plan_d_eau", "point_d_acces", "point_de_repere", "point_du_reseau", "poste_de_transformation", "pylone", "region", "reservoir", "route_numerotee_ou_nommee", "section_de_points_de_repere", "surface_hydrographique", "terrain_de_sport", "toponymie_bati", "toponymie_hydrographie", "toponymie_lieux_nommes", "toponymie_services_et_activites", "toponymie_transport", "toponymie_zones_reglementees", "transport_par_cable", "troncon_de_route", "troncon_de_voie_ferree", "troncon_hydrographique", "voie_ferree_nommee", "voie_nommee", "zone_d_activite_ou_d_interet", "zone_d_estran", "zone_d_habitation", "zone_de_vegetation"]],
                          "FXX":["fxx_lamb93",      2154, ["aerodrome", "arrondissement", "arrondissement_municipal", "bassin_versant_topographique", "batiment", "canalisation", "cimetiere", "collectivite_territoriale", "commune", "commune_associee_ou_deleguee", "condominium", "construction_lineaire", "construction_ponctuelle", "construction_surfacique", "cours_d_eau", "departement", "detail_hydrographique", "detail_orographique", "epci", "equipement_de_transport", "erp", "foret_publique", "haie", "itineraire_autre", "lieu_dit_non_habite", "ligne_electrique", "ligne_orographique", "limite_terre_mer", "noeud_hydrographique", "non_communication", "parc_ou_reserve", "piste_d_aerodrome", "plan_d_eau", "point_d_acces", "point_de_repere", "point_du_reseau", "poste_de_transformation", "pylone", "region", "reservoir", "route_numerotee_ou_nommee", "section_de_points_de_repere", "surface_hydrographique", "terrain_de_sport", "toponymie_bati", "toponymie_hydrographie", "toponymie_lieux_nommes", "toponymie_services_et_activites", "toponymie_transport", "toponymie_zones_reglementees", "transport_par_cable", "troncon_de_route", "troncon_de_voie_ferree", "troncon_hydrographique", "voie_ferree_nommee", "voie_nommee", "zone_d_activite_ou_d_interet", "zone_d_estran", "zone_d_habitation", "zone_de_vegetation"]],
                          "GLP":["glp_rgaf09utm20", 5490, ["aerodrome", "arrondissement", "batiment", "canalisation", "cimetiere", "collectivite_territoriale", "commune", "construction_lineaire", "construction_ponctuelle", "construction_surfacique", "cours_d_eau", "departement", "detail_hydrographique", "detail_orographique", "epci", "equipement_de_transport", "foret_publique", "itineraire_autre", "lieu_dit_non_habite", "ligne_electrique", "ligne_orographique", "limite_terre_mer", "noeud_hydrographique", "non_communication", "parc_ou_reserve", "piste_d_aerodrome", "plan_d_eau", "point_du_reseau", "poste_de_transformation", "pylone", "region", "reservoir", "route_numerotee_ou_nommee", "surface_hydrographique", "terrain_de_sport", "toponymie_bati", "toponymie_hydrographie", "toponymie_lieux_nommes", "toponymie_services_et_activites", "toponymie_transport", "toponymie_zones_reglementees", "troncon_de_route", "troncon_de_voie_ferree", "troncon_hydrographique", "voie_nommee", "zone_d_activite_ou_d_interet", "zone_d_estran", "zone_d_habitation", "zone_de_vegetation"]],
                          "GUF":["guf_utm22rgfg95", 2972, ["aerodrome", "arrondissement", "bassin_versant_topographique", "batiment", "canalisation", "cimetiere", "collectivite_territoriale", "commune", "construction_lineaire", "construction_ponctuelle", "construction_surfacique", "cours_d_eau", "departement", "detail_hydrographique", "detail_orographique", "epci", "equipement_de_transport", "erp", "foret_publique", "itineraire_autre", "lieu_dit_non_habite", "ligne_electrique", "ligne_orographique", "limite_terre_mer", "noeud_hydrographique", "non_communication", "parc_ou_reserve", "piste_d_aerodrome", "plan_d_eau", "point_du_reseau", "poste_de_transformation", "pylone", "region", "reservoir", "route_numerotee_ou_nommee", "surface_hydrographique", "terrain_de_sport", "toponymie_bati", "toponymie_hydrographie", "toponymie_lieux_nommes", "toponymie_services_et_activites", "toponymie_transport", "toponymie_zones_reglementees", "troncon_de_route", "troncon_de_voie_ferree", "troncon_hydrographique", "voie_ferree_nommee", "voie_nommee", "zone_d_activite_ou_d_interet", "zone_d_estran", "zone_d_habitation", "zone_de_vegetation"]],
                          "MTQ":["mtq_rgaf09utm20", 5490, ["aerodrome", "arrondissement", "batiment", "canalisation", "cimetiere", "collectivite_territoriale", "commune", "construction_lineaire", "construction_ponctuelle", "construction_surfacique", "cours_d_eau", "departement", "detail_hydrographique", "detail_orographique", "epci", "equipement_de_transport", "foret_publique", "itineraire_autre", "lieu_dit_non_habite", "ligne_electrique", "ligne_orographique", "limite_terre_mer", "noeud_hydrographique", "non_communication", "parc_ou_reserve", "piste_d_aerodrome", "plan_d_eau", "point_de_repere", "point_du_reseau", "poste_de_transformation", "pylone", "region", "reservoir", "route_numerotee_ou_nommee", "section_de_points_de_repere", "surface_hydrographique", "terrain_de_sport", "toponymie_bati", "toponymie_hydrographie", "toponymie_lieux_nommes", "toponymie_services_et_activites", "toponymie_transport", "toponymie_zones_reglementees", "troncon_de_route", "troncon_de_voie_ferree", "troncon_hydrographique", "voie_ferree_nommee", "voie_nommee", "zone_d_activite_ou_d_interet", "zone_d_estran", "zone_d_habitation", "zone_de_vegetation"]],
                          "MYT":["myt_rgm04utm38s", 4471, ["aerodrome", "bassin_versant_topographique", "batiment", "cimetiere", "collectivite_territoriale", "commune", "construction_lineaire", "construction_ponctuelle", "construction_surfacique", "cours_d_eau", "departement", "detail_hydrographique", "detail_orographique", "epci", "equipement_de_transport", "foret_publique", "itineraire_autre", "lieu_dit_non_habite", "ligne_electrique", "ligne_orographique", "limite_terre_mer", "noeud_hydrographique", "parc_ou_reserve", "piste_d_aerodrome", "plan_d_eau", "point_du_reseau", "poste_de_transformation", "pylone", "region", "reservoir", "route_numerotee_ou_nommee", "surface_hydrographique", "terrain_de_sport", "toponymie_bati", "toponymie_hydrographie", "toponymie_lieux_nommes", "toponymie_services_et_activites", "toponymie_transport", "toponymie_zones_reglementees", "transport_par_cable", "troncon_de_route", "troncon_hydrographique", "voie_nommee", "zone_d_activite_ou_d_interet", "zone_d_estran", "zone_d_habitation", "zone_de_vegetation"]],
                          "REU":["reu_rgr92utm40s", 2975, ["aerodrome", "arrondissement", "bassin_versant_topographique", "batiment", "canalisation", "cimetiere", "collectivite_territoriale", "commune", "construction_lineaire", "construction_ponctuelle", "construction_surfacique", "cours_d_eau", "departement", "detail_hydrographique", "detail_orographique", "epci", "equipement_de_transport", "foret_publique", "itineraire_autre", "lieu_dit_non_habite", "ligne_electrique", "ligne_orographique", "limite_terre_mer", "noeud_hydrographique", "non_communication", "parc_ou_reserve", "piste_d_aerodrome", "plan_d_eau", "point_de_repere", "point_du_reseau", "poste_de_transformation", "pylone", "region", "reservoir", "route_numerotee_ou_nommee", "section_de_points_de_repere", "surface_hydrographique", "terrain_de_sport", "toponymie_bati", "toponymie_hydrographie", "toponymie_lieux_nommes", "toponymie_services_et_activites", "toponymie_transport", "toponymie_zones_reglementees", "transport_par_cable", "troncon_de_route", "troncon_de_voie_ferree", "troncon_hydrographique", "voie_nommee", "zone_d_activite_ou_d_interet", "zone_d_estran", "zone_d_habitation", "zone_de_vegetation"]],
                          "SPM":["spm_rgspm06u21",  4467, ["aerodrome", "batiment", "cimetiere", "collectivite_territoriale", "commune", "construction_lineaire", "construction_ponctuelle", "cours_d_eau", "detail_hydrographique", "detail_orographique", "equipement_de_transport", "itineraire_autre", "lieu_dit_non_habite", "ligne_orographique", "limite_terre_mer", "noeud_hydrographique", "piste_d_aerodrome", "plan_d_eau", "point_du_reseau", "reservoir", "route_numerotee_ou_nommee", "surface_hydrographique", "terrain_de_sport", "toponymie_bati", "toponymie_hydrographie", "toponymie_lieux_nommes", "toponymie_services_et_activites", "toponymie_transport", "troncon_de_route", "troncon_hydrographique", "voie_nommee", "zone_d_activite_ou_d_interet", "zone_d_estran", "zone_d_habitation", "zone_de_vegetation"]]}

    BD_TOPO_THEMES_LIST = ["ADMINISTRATIF", "ADMINISTRATIF", "ADMINISTRATIF", "ADMINISTRATIF", "ADMINISTRATIF", "ADMINISTRATIF", "ADMINISTRATIF", "ADMINISTRATIF", "ADMINISTRATIF",
                           "BATI", "BATI", "BATI", "BATI", "BATI", "BATI", "BATI", "BATI", "BATI", "BATI",
                           "HYDROGRAPHIE", "HYDROGRAPHIE", "HYDROGRAPHIE", "HYDROGRAPHIE", "HYDROGRAPHIE", "HYDROGRAPHIE", "HYDROGRAPHIE", "HYDROGRAPHIE", "HYDROGRAPHIE",
                           "LIEUX_NOMMES", "LIEUX_NOMMES", "LIEUX_NOMMES", "LIEUX_NOMMES",
                           "OCCUPATION_DU_SOL","OCCUPATION_DU_SOL", "OCCUPATION_DU_SOL",
                           "SERVICES_ET_ACTIVITES", "SERVICES_ET_ACTIVITES", "SERVICES_ET_ACTIVITES", "SERVICES_ET_ACTIVITES", "SERVICES_ET_ACTIVITES", "SERVICES_ET_ACTIVITES",
                           "TRANSPORT", "TRANSPORT", "TRANSPORT", "TRANSPORT", "TRANSPORT", "TRANSPORT", "TRANSPORT", "TRANSPORT", "TRANSPORT", "TRANSPORT", "TRANSPORT", "TRANSPORT", "TRANSPORT", "TRANSPORT", "TRANSPORT", "TRANSPORT",
                           "ZONES_REGLEMENTEES", "ZONES_REGLEMENTEES", "ZONES_REGLEMENTEES"]

    BD_TOPO_CLASSES_LIST = ["arrondissement", "arrondissement_municipal", "collectivite_territoriale", "commune", "commune_associee_ou_deleguee", "condominium", "departement", "epci", "region",
                            "batiment", "cimetiere", "construction_lineaire", "construction_ponctuelle", "construction_surfacique", "ligne_orographique", "pylone", "reservoir", "terrain_de_sport", "toponymie_bati",
                            "bassin_versant_topographique", "cours_d_eau", "detail_hydrographique", "limite_terre_mer", "noeud_hydrographique", "plan_d_eau", "surface_hydrographique", "toponymie_hydrographie", "troncon_hydrographique",
                            "detail_orographique", "lieu_dit_non_habite", "toponymie_lieux_nommes", "zone_d_habitation",
                            "haie", "zone_d_estran", "zone_de_vegetation",
                            "canalisation", "erp", "ligne_electrique", "poste_de_transformation", "toponymie_services_et_activites", "zone_d_activite_ou_d_interet",
                            "aerodrome", "equipement_de_transport", "itineraire_autre", "non_communication", "piste_d_aerodrome", "point_d_acces", "point_de_repere", "point_du_reseau", "route_numerotee_ou_nommee", "section_de_points_de_repere", "toponymie_transport", "transport_par_cable", "troncon_de_route", "troncon_de_voie_ferree", "voie_ferree_nommee", "voie_nommee",
                            "foret_publique", "parc_ou_reserve", "toponymie_zones_reglementees"]

    BD_TOPO_SQL_FIELDS_LIST = [["nom_officiel", "code_insee_de_l_arrondissement", "code_insee_du_departement", "code_insee_de_la_region", "liens_vers_autorite_administrative", "date_creation", "date_modification", "date_d_apparition", "date_de_confirmation"],
                               ["code_insee", "code_insee_de_la_commune_de_rattach", "nom_officiel", "date_creation", "date_modification", "date_d_apparition", "date_de_confirmation", "lien_vers_chef_lieu", "liens_vers_autorite_administrative", "code_postal", "population"],
                               ["code_siren", "liens_vers_autorite_administrative", "date_de_confirmation", "date_d_apparition", "date_modification", "date_creation", "nom_officiel", "code_insee_de_la_region", "code_insee"],
                               ["code_insee", "code_insee_de_l_arrondissement", "code_insee_de_la_collectivite_terr", "code_insee_du_departement", "code_insee_de_la_region", "population", "surface_en_ha", "date_creation", "date_modification", "date_d_apparition", "date_de_confirmation", "code_postal", "nom_officiel", "chef_lieu_d_arrondissement", "chef_lieu_de_collectivite_terr", "chef_lieu_de_departement", "chef_lieu_de_region", "capitale_d_etat", "date_du_recensement", "organisme_recenseur", "codes_siren_des_epci", "lien_vers_chef_lieu", "liens_vers_autorite_administrative", "code_siren"],
                               ["liens_vers_autorite_administrative", "code_siren", "lien_vers_chef_lieu", "population", "code_postal", "date_de_confirmation", "date_d_apparition", "date_modification", "date_creation", "nom_officiel", "nature", "code_insee_de_la_commune_de_rattach", "code_insee"],
                               ["unites_administratives_souveraines", "date_creation", "date_modification", "date_d_apparition", "date_de_confirmation", "lien_vers_lieu_dit"],
                               ["code_siren", "liens_vers_autorite_administrative", "date_creation", "date_modification", "date_d_apparition", "date_de_confirmation", "nom_officiel", "code_insee_de_la_region", "code_insee"],
                               ["code_siren", "nature", "nom_officiel", "date_creation", "date_modification", "date_d_apparition", "date_de_confirmation", "liens_vers_autorite_administrative"],
                               ["code_siren", "liens_vers_autorite_administrative", "date_creation", "date_modification", "date_d_apparition", "date_de_confirmation", "nom_officiel", "code_insee"],
                               ["nature", "usage_1", "usage_2", "construction_legere", "etat_de_l_objet", "date_creation", "date_modification", "date_d_apparition", "date_de_confirmation", "sources", "identifiants_sources", "methode_d_acquisition_planimetrique", "precision_planimetrique", "methode_d_acquisition_altimetrique", "precision_altimetrique", "nombre_de_logements", "nombre_d_etages", "materiaux_des_murs", "materiaux_de_la_toiture", "hauteur", "altitude_minimale_sol", "altitude_minimale_toit", "altitude_maximale_toit", "altitude_maximale_sol", "origine_du_batiment", "appariement_fichiers_fonciers"],
                               ["nature", "nature_detaillee", "toponyme", "statut_du_toponyme", "importance", "etat_de_l_objet", "date_creation", "date_modification", "date_d_apparition", "date_de_confirmation", "sources", "identifiants_sources", "methode_d_acquisition_planimetrique", "precision_planimetrique", "methode_d_acquisition_altimetrique", "precision_altimetrique"],
                               ["nature", "nature_detaillee", "toponyme", "statut_du_toponyme", "importance", "etat_de_l_objet", "date_creation", "date_modification", "date_d_apparition", "date_de_confirmation", "sources", "identifiants_sources", "methode_d_acquisition_planimetrique", "precision_planimetrique", "methode_d_acquisition_altimetrique", "precision_altimetrique"],
                               ["nature", "nature_detaillee", "toponyme", "statut_du_toponyme", "importance", "etat_de_l_objet", "date_creation", "date_modification", "date_d_apparition", "date_de_confirmation", "sources", "identifiants_sources", "methode_d_acquisition_planimetrique", "precision_planimetrique", "methode_d_acquisition_altimetrique", "precision_altimetrique", "hauteur"],
                               ["nature", "nature_detaillee", "toponyme", "statut_du_toponyme", "importance", "etat_de_l_objet", "date_creation", "date_modification", "date_d_apparition", "date_de_confirmation", "sources", "identifiants_sources", "methode_d_acquisition_planimetrique", "precision_planimetrique", "methode_d_acquisition_altimetrique", "precision_altimetrique"],
                               ["nature", "etat_de_l_objet", "date_creation", "date_modification", "date_d_apparition", "date_de_confirmation", "toponyme", "statut_du_toponyme", "sources", "identifiants_sources", "methode_d_acquisition_planimetrique", "precision_planimetrique", "methode_d_acquisition_altimetrique", "precision_altimetrique"],
                               ["etat_de_l_objet", "date_creation", "date_modification", "date_d_apparition", "date_de_confirmation", "sources", "identifiants_sources", "methode_d_acquisition_planimetrique", "precision_planimetrique", "methode_d_acquisition_altimetrique", "precision_altimetrique", "hauteur"],
                               ["nature", "etat_de_l_objet", "date_creation", "date_modification", "date_d_apparition", "date_de_confirmation", "sources", "identifiants_sources", "methode_d_acquisition_planimetrique", "precision_planimetrique", "methode_d_acquisition_altimetrique", "precision_altimetrique", "altitude_minimale_sol", "altitude_minimale_toit", "hauteur", "altitude_maximale_toit", "altitude_maximale_sol", "origine_du_batiment", "volume"],
                               ["nature", "nature_detaillee", "etat_de_l_objet", "date_creation", "date_modification", "date_d_apparition", "date_de_confirmation", "sources", "identifiants_sources", "methode_d_acquisition_planimetrique", "precision_planimetrique", "methode_d_acquisition_altimetrique", "precision_altimetrique"],
                               ["classe_de_l_objet", "nature_de_l_objet", "graphie_du_toponyme", "source_du_toponyme", "statut_du_toponyme", "date_du_toponyme", "langue_du_toponyme"],
                               ["liens_vers_cours_d_eau_principal", "code_bdcarthage", "code_du_bassin_hydrographique", "commentaire_sur_l_objet_hydro", "origine", "bassin_fluvial", "statut", "mode_d_obtention_des_coordonnees", "precision_planimetrique", "methode_d_acquisition_planimetrique", "identifiants_sources", "sources", "date_de_confirmation", "date_d_apparition", "date_modification", "date_creation", "libelle_du_bassin_hydrographique", "toponyme", "code_hydrographique"],
                               ["commentaire_sur_l_objet_hydro", "caractere_permanent", "influence_de_la_maree", "statut", "identifiants_sources", "sources", "date_de_confirmation", "date_d_apparition", "date_modification", "date_creation", "importance", "statut_du_toponyme", "toponyme", "code_hydrographique"],
                               ["nature", "nature_detaillee", "persistance", "toponyme", "statut_du_toponyme", "importance", "etat_de_l_objet", "date_creation", "date_modification", "date_d_apparition", "date_de_confirmation", "sources", "identifiants_sources", "methode_d_acquisition_planimetrique", "precision_planimetrique", "identifiant_voie_ban"],
                               ["code_hydrographique", "code_du_pays", "type_de_limite", "niveau", "date_creation", "date_modification", "date_d_apparition", "date_de_confirmation", "sources", "identifiants_sources", "methode_d_acquisition_planimetrique", "precision_planimetrique", "mode_d_obtention_des_coordonnees", "statut", "origine", "commentaire_sur_l_objet_hydro"],
                               ["code_hydrographique", "code_du_pays", "categorie", "toponyme", "statut_du_toponyme", "date_creation", "date_modification", "date_d_apparition", "date_de_confirmation", "sources", "identifiants_sources", "methode_d_acquisition_planimetrique", "precision_planimetrique", "methode_d_acquisition_altimetrique", "precision_altimetrique", "mode_d_obtention_des_coordonnees", "mode_d_obtention_de_l_altitude", "statut", "commentaire_sur_l_objet_hydro", "liens_vers_cours_d_eau_amont", "liens_vers_cours_d_eau_aval"],
                               ["code_hydrographique", "nature", "toponyme", "statut_du_toponyme", "importance", "date_creation", "date_modification", "date_d_apparition", "date_de_confirmation", "sources", "identifiants_sources", "statut", "influence_de_la_maree", "caractere_permanent", "altitude_moyenne", "referentiel_de_l_altitude_moyenne", "mode_d_obtention_de_l_altitude_moy", "precision_de_l_altitude_moyenne", "hauteur_d_eau_maximale", "mode_d_obtention_de_la_hauteur", "commentaire_sur_l_objet_hydro"],
                               ["code_hydrographique", "code_du_pays", "nature", "position_par_rapport_au_sol", "etat_de_l_objet", "date_creation", "date_modification", "date_d_apparition", "date_de_confirmation", "sources", "identifiants_sources", "methode_d_acquisition_planimetrique", "precision_planimetrique", "methode_d_acquisition_altimetrique", "precision_altimetrique", "mode_d_obtention_des_coordonnees", "mode_d_obtention_de_l_altitude", "statut", "persistance", "salinite", "origine", "commentaire_sur_l_objet_hydro", "liens_vers_plan_d_eau", "liens_vers_cours_d_eau", "lien_vers_entite_de_transition", "cpx_toponyme_de_plan_d_eau", "cpx_toponyme_de_cours_d_eau", "cpx_toponyme_d_entite_de_transition"],
                               ["classe_de_l_objet", "nature_de_l_objet", "graphie_du_toponyme", "source_du_toponyme", "statut_du_toponyme", "date_du_toponyme", "langue_du_toponyme"],
                               ["cpx_toponyme_d_entite_de_transition", "cpx_toponyme_de_cours_d_eau", "lien_vers_entite_de_transition", "liens_vers_surface_hydrographique", "liens_vers_cours_d_eau", "code_du_cours_d_eau_bdcarthage", "commentaire_sur_l_objet_hydro", "type_de_bras", "classe_de_largeur", "delimitation", "reseau_principal_coulant", "sens_de_l_ecoulement", "perimetre_d_utilisation_ou_origine", "origine", "strategie_de_classement", "numero_d_ordre", "salinite", "navigabilite", "fosse", "persistance", "statut", "mode_d_obtention_de_l_altitude", "mode_d_obtention_des_coordonnees", "precision_altimetrique", "methode_d_acquisition_altimetrique", "precision_planimetrique", "methode_d_acquisition_planimetrique", "identifiants_sources", "sources", "date_de_confirmation", "date_d_apparition", "date_modification", "date_creation", "etat_de_l_objet", "position_par_rapport_au_sol", "fictif", "nature", "code_du_pays", "code_hydrographique"],
                               ["nature", "nature_detaillee", "toponyme", "statut_du_toponyme", "importance", "date_creation", "date_modification", "date_d_apparition", "date_de_confirmation", "sources", "identifiants_sources", "methode_d_acquisition_planimetrique", "precision_planimetrique", "identifiant_voie_ban"],
                               ["nature", "toponyme", "statut_du_toponyme", "importance", "date_creation", "date_modification", "date_d_apparition", "date_de_confirmation", "sources", "identifiants_sources", "methode_d_acquisition_planimetrique", "precision_planimetrique", "identifiant_voie_ban"],
                               ["classe_de_l_objet", "nature_de_l_objet", "graphie_du_toponyme", "source_du_toponyme", "statut_du_toponyme", "date_du_toponyme", "langue_du_toponyme"],
                               ["nature", "nature_detaillee", "toponyme", "statut_du_toponyme", "importance", "fictif", "etat_de_l_objet", "date_creation", "date_modification", "date_d_apparition", "date_de_confirmation", "sources", "identifiants_sources", "methode_d_acquisition_planimetrique", "precision_planimetrique", "identifiant_voie_ban"],
                               ["date_creation", "date_modification", "date_d_apparition", "date_de_confirmation", "hauteur", "largeur", "sources", "identifiants_sources", "methode_d_acquisition_planimetrique", "precision_planimetrique"],
                               ["nature", "date_creation", "date_modification", "date_d_apparition", "date_de_confirmation", "sources", "identifiants_sources", "methode_d_acquisition_planimetrique", "precision_planimetrique"],
                               ["nature", "date_creation", "date_modification", "date_d_apparition", "date_de_confirmation", "methode_d_acquisition_planimetrique", "precision_planimetrique", "sources", "identifiants_sources"],
                               ["nature", "position_par_rapport_au_sol", "etat_de_l_objet", "date_creation", "date_modification", "date_d_apparition", "date_de_confirmation", "sources", "identifiants_sources", "methode_d_acquisition_planimetrique", "precision_planimetrique", "methode_d_acquisition_altimetrique", "precision_altimetrique"],
                               ["id_reference", "categorie", "type_principal", "types_secondaires", "activite_principale", "activites_secondaires", "libelle", "etat_de_l_objet", "date_creation", "date_modification", "date_d_apparition", "date_de_confirmation", "sources", "identifiants_sources", "methode_d_acquisition_planimetrique", "precision_planimetrique", "public", "ouvert", "capacite_d_accueil_du_public", "capacite_d_hebergement", "origine_de_la_geometrie", "type_de_localisation", "validation_ign", "insee_commune", "numero_siret", "adresse_numero", "adresse_indice_de_repetition", "adresse_designation_de_l_entree", "adresse_nom_1", "adresse_nom_2", "code_postal", "liens_vers_batiment", "liens_vers_enceinte"],
                               ["voltage", "etat_de_l_objet", "date_creation", "date_modification", "date_d_apparition", "date_de_confirmation", "sources", "identifiants_sources", "methode_d_acquisition_planimetrique", "precision_planimetrique", "methode_d_acquisition_altimetrique", "precision_altimetrique"],
                               ["toponyme", "statut_du_toponyme", "importance", "etat_de_l_objet", "date_creation", "date_modification", "date_d_apparition", "date_de_confirmation", "sources", "identifiants_sources", "methode_d_acquisition_planimetrique", "precision_planimetrique", "methode_d_acquisition_altimetrique", "precision_altimetrique"],
                               ["classe_de_l_objet", "nature_de_l_objet", "graphie_du_toponyme", "source_du_toponyme", "statut_du_toponyme", "date_du_toponyme", "langue_du_toponyme"],
                               ["categorie", "nature", "nature_detaillee", "toponyme", "statut_du_toponyme", "importance", "fictif", "etat_de_l_objet", "date_creation", "date_modification", "date_d_apparition", "date_de_confirmation", "sources", "identifiants_sources", "methode_d_acquisition_planimetrique", "precision_planimetrique", "identifiant_voie_ban", "nom_commercial"],
                               ["categorie", "nature", "usage", "toponyme", "statut_du_toponyme", "fictif", "etat_de_l_objet", "date_creation", "date_modification", "date_d_apparition", "date_de_confirmation", "sources", "identifiants_sources", "methode_d_acquisition_planimetrique", "precision_planimetrique", "altitude", "code_icao", "code_iata"],
                               ["nature", "nature_detaillee", "toponyme", "statut_du_toponyme", "importance", "fictif", "etat_de_l_objet", "date_creation", "date_modification", "date_d_apparition", "date_de_confirmation", "sources", "identifiants_sources", "methode_d_acquisition_planimetrique", "precision_planimetrique", "methode_d_acquisition_altimetrique", "precision_altimetrique", "identifiant_voie_ban"],
                               ["nature", "nature_detaillee", "date_creation", "date_modification", "date_d_apparition", "date_de_confirmation", "sources", "identifiants_sources"],
                               ["date_creation", "date_modification", "date_d_apparition", "date_de_confirmation", "lien_vers_troncon_entree", "liens_vers_troncon_sortie"],
                               ["nature", "fonction", "etat_de_l_objet", "date_creation", "date_modification", "date_d_apparition", "date_de_confirmation", "sources", "identifiants_sources", "methode_d_acquisition_planimetrique", "precision_planimetrique", "methode_d_acquisition_altimetrique", "precision_altimetrique"],
                               ["date_creation", "date_modification", "date_d_apparition", "date_de_confirmation", "methode_d_acquisition_planimetrique", "precision_planimetrique", "sens", "mode", "lien_vers_point_d_interet"],
                               ["date_creation", "date_modification", "date_d_apparition", "date_de_confirmation", "sources", "identifiants_sources", "route", "numero", "abscisse", "ordre", "cote", "statut", "type_de_pr", "libelle", "identifiant_de_section", "code_insee_du_departement", "lien_vers_route_nommee", "gestionnaire"],
                               ["nature", "nature_detaillee", "toponyme", "statut_du_toponyme", "etat_de_l_objet", "date_creation", "date_modification", "date_d_apparition", "date_de_confirmation", "sources", "identifiants_sources", "methode_d_acquisition_planimetrique", "precision_planimetrique", "methode_d_acquisition_altimetrique", "precision_altimetrique", "identifiant_voie_ban"],
                               ["type_de_route", "numero", "toponyme", "statut_du_toponyme", "date_creation", "date_modification", "date_d_apparition", "date_de_confirmation", "sources", "identifiants_sources", "gestionnaire"],
                               ["identifiant_de_section", "numero_de_route", "gestionnaire", "lien_vers_route_nommee", "code_insee_du_departement", "cote", "sources", "date_de_confirmation", "date_creation", "date_modification"],
                               ["classe_de_l_objet", "nature_de_l_objet", "graphie_du_toponyme", "source_du_toponyme", "statut_du_toponyme", "date_du_toponyme", "langue_du_toponyme"],
                               ["nature", "toponyme", "statut_du_toponyme", "importance", "etat_de_l_objet", "date_creation", "date_modification", "date_d_apparition", "date_de_confirmation", "sources", "identifiants_sources", "methode_d_acquisition_planimetrique", "precision_planimetrique", "methode_d_acquisition_altimetrique", "precision_altimetrique"],
                               ["delestage", "source_voie_ban_gauche", "source_voie_ban_droite", "nom_voie_ban_gauche", "nom_voie_ban_droite", "lieux_dits_ban_gauche", "lieux_dits_ban_droite", "identifiant_voie_ban_gauche", "identifiant_voie_ban_droite", "cpx_toponyme_itineraire_autre", "cpx_nature_itineraire_autre", "cpx_toponyme_voie_verte", "cpx_toponyme_itineraire_cyclable", "cpx_toponyme_route_nommee", "cpx_gestionnaire", "cpx_classement_administratif", "cpx_numero_route_europeenne", "cpx_numero", "liens_vers_itineraire_autre", "liens_vers_route_nommee", "identifiant_voie_1_droite", "identifiant_voie_1_gauche", "date_de_mise_en_service", "alias_droit", "alias_gauche", "insee_commune_droite", "insee_commune_gauche", "borne_fin_droite", "borne_fin_gauche", "borne_debut_droite", "borne_debut_gauche", "matieres_dangereuses_interdites", "restriction_de_longueur", "restriction_de_largeur", "restriction_de_poids_par_essieu", "restriction_de_poids_total", "restriction_de_hauteur", "nature_de_la_restriction", "sens_amenagement_cyclable_gauche", "sens_amenagement_cyclable_droit", "amenagement_cyclable_gauche", "amenagement_cyclable_droit", "periode_de_fermeture", "acces_pieton", "acces_vehicule_leger", "vitesse_moyenne_vl", "urbain", "reserve_aux_bus", "sens_de_circulation", "prive", "itineraire_vert", "largeur_de_chaussee", "nombre_de_voies", "precision_altimetrique", "methode_d_acquisition_altimetrique", "precision_planimetrique", "methode_d_acquisition_planimetrique", "identifiants_sources", "sources", "date_de_confirmation", "date_d_apparition", "date_modification", "date_creation", "etat_de_l_objet", "position_par_rapport_au_sol", "fictif", "importance", "nom_collaboratif_droite", "nom_collaboratif_gauche", "nature"],
                               ["nature", "position_par_rapport_au_sol", "etat_de_l_objet", "date_creation", "date_modification", "date_d_apparition", "date_de_confirmation", "sources", "identifiants_sources", "methode_d_acquisition_planimetrique", "precision_planimetrique", "methode_d_acquisition_altimetrique", "precision_altimetrique", "electrifie", "largeur", "nombre_de_voies", "usage", "vitesse_maximale", "liens_vers_voie_ferree_nommee", "cpx_toponyme"],
                               ["toponyme", "statut_du_toponyme", "date_creation", "date_modification", "date_d_apparition", "date_de_confirmation", "sources", "identifiants_sources"],
                               ["id_pseudo_fpb", "type_voie", "type_d_adressage", "nom_minuscule", "nom_initial_troncon", "mot_directeur", "validite", "date_creation", "date_modification", "code_insee", "code_postal", "alias_initial_troncon", "alias_minuscule", "type_liaison", "qualite_passage_maj_min", "fiabilite"],
                               ["nature", "toponyme", "statut_du_toponyme", "importance", "date_creation", "date_modification", "date_d_apparition", "date_de_confirmation", "sources", "identifiants_sources", "methode_d_acquisition_planimetrique", "precision_planimetrique"],
                               ["nature", "nature_detaillee", "toponyme", "statut_du_toponyme", "fictif", "etat_de_l_objet", "date_creation", "date_modification", "date_d_apparition", "date_de_confirmation", "sources", "identifiants_sources", "methode_d_acquisition_planimetrique", "precision_planimetrique"],
                               ["classe_de_l_objet", "nature_de_l_objet", "graphie_du_toponyme", "source_du_toponyme", "statut_du_toponyme", "date_du_toponyme", "langue_du_toponyme"]]

    BD_TOPO_SHP_FIELDS_LIST = [["NOM", "INSEE_ARR", "INSEE_DEP", "INSEE_REG", "ID_AUT_ADM", "DATE_CREAT", "DATE_MAJ", "DATE_APP", "DATE_CONF"],
                               ["INSEE_ARM", "INSEE_COM", "NOM", "DATE_CREAT", "DATE_MAJ", "DATE_APP", "DATE_CONF", "ID_CH_LIEU", "ID_AUT_ADM", "CODE_POST", "POPULATION"],
                               ["CODE_SIREN", "ID_AUT_ADM", "DATE_CONF", "DATE_APP", "DATE_MAJ", "DATE_CREAT", "NOM", "INSEE_REG", "INSEE_COL"],
                               ["INSEE_COM", "INSEE_ARR", "INSEE_COL", "INSEE_DEP", "INSEE_REG", "POPULATION", "SURFACE_HA", "DATE_CREAT", "DATE_MAJ", "DATE_APP", "DATE_CONF", "CODE_POST", "NOM", "CL_ARROND", "CL_COLLTER", "CL_DEPART", "CL_REGION", "CAPITALE", "DATE_RCT", "RECENSEUR", "SIREN_EPCI", "ID_CH_LIEU", "ID_AUT_ADM", "CODE_SIREN"],
                               ["ID_AUT_ADM", "CODE_SIREN", "ID_CH_LIEU", "POPULATION", "CODE_POST", "DATE_CONF", "DATE_APP", "DATE_MAJ", "DATE_CREAT", "NOM", "NATURE", "INSEE_COM", "INSEE_CAD"],
                               ["PAYS_SOUVE", "DATE_CREAT", "DATE_MAJ", "DATE_APP", "DATE_CONF", "ID_LIEUDIT"],
                               ["CODE_SIREN", "ID_AUT_ADM", "DATE_CREAT", "DATE_MAJ", "DATE_APP", "DATE_CONF", "NOM", "INSEE_REG", "INSEE_DEP"],
                               ["CODE_SIREN", "NATURE", "NOM", "DATE_CREAT", "DATE_MAJ", "DATE_APP", "DATE_CONF", "ID_AUT_ADM"],
                               ["CODE_SIREN", "ID_AUT_ADM", "DATE_CREAT", "DATE_MAJ", "DATE_APP", "DATE_CONF", "NOM", "INSEE_REG"],
                               ["NATURE", "USAGE1", "USAGE2", "LEGER", "ETAT", "DATE_CREAT", "DATE_MAJ", "DATE_APP", "DATE_CONF", "SOURCE", "ID_SOURCE", "ACQU_PLANI", "PREC_PLANI", "ACQU_ALTI", "PREC_ALTI", "NB_LOGTS", "NB_ETAGES", "MAT_MURS", "MAT_TOITS", "HAUTEUR", "Z_MIN_SOL", "Z_MIN_TOIT", "Z_MAX_TOIT", "Z_MAX_SOL", "ORIGIN_BAT", "APP_FF"],
                               ["NATURE", "NAT_DETAIL", "TOPONYME", "STATUT_TOP", "IMPORTANCE", "ETAT", "DATE_CREAT", "DATE_MAJ", "DATE_APP", "DATE_CONF", "SOURCE", "ID_SOURCE", "ACQU_PLANI", "PREC_PLANI", "ACQU_ALTI", "PREC_ALTI"],
                               ["NATURE", "NAT_DETAIL", "TOPONYME", "STATUT_TOP", "IMPORTANCE", "ETAT", "DATE_CREAT", "DATE_MAJ", "DATE_APP", "DATE_CONF", "SOURCE", "ID_SOURCE", "ACQU_PLANI", "PREC_PLANI", "ACQU_ALTI", "PREC_ALTI"],
                               ["NATURE", "NAT_DETAIL", "TOPONYME", "STATUT_TOP", "IMPORTANCE", "ETAT", "DATE_CREAT", "DATE_MAJ", "DATE_APP", "DATE_CONF", "SOURCE", "ID_SOURCE", "ACQU_PLANI", "PREC_PLANI", "ACQU_ALTI", "PREC_ALTI", "HAUTEUR"],
                               ["NATURE", "NAT_DETAIL", "TOPONYME", "STATUT_TOP", "IMPORTANCE", "ETAT", "DATE_CREAT", "DATE_MAJ", "DATE_APP", "DATE_CONF", "SOURCE", "ID_SOURCE", "ACQU_PLANI", "PREC_PLANI", "ACQU_ALTI", "PREC_ALTI"],
                               ["NATURE", "ETAT", "DATE_CREAT", "DATE_MAJ", "DATE_APP", "DATE_CONF", "TOPONYME", "STATUT_TOP", "SOURCE", "ID_SOURCE", "ACQU_PLANI", "PREC_PLANI", "ACQU_ALTI", "PREC_ALTI"],
                               ["ETAT", "DATE_CREAT", "DATE_MAJ", "DATE_APP", "DATE_CONF", "SOURCE", "ID_SOURCE", "ACQU_PLANI", "PREC_PLANI", "ACQU_ALTI", "PREC_ALTI", "HAUTEUR"],
                               ["NATURE", "ETAT", "DATE_CREAT", "DATE_MAJ", "DATE_APP", "DATE_CONF", "SOURCE", "ID_SOURCE", "ACQU_PLANI", "PREC_PLANI", "ACQU_ALTI", "PREC_ALTI", "Z_MIN_SOL", "Z_MIN_TOIT", "HAUTEUR", "Z_MAX_TOIT", "Z_MAX_SOL", "ORIGIN_BAT", "VOLUME"],
                               ["NATURE", "NAT_DETAIL", "ETAT", "DATE_CREAT", "DATE_MAJ", "DATE_APP", "DATE_CONF", "SOURCE", "ID_SOURCE", "ACQU_PLANI", "PREC_PLANI", "ACQU_ALTI", "PREC_ALTI"],
                               ["CLASSE", "NATURE", "GRAPHIE", "SOURCE", "STATUT_TOP", "DATE_TOP", "LANGUE"],
                               ["ID_C_EAU", "CODE_CARTH", "CODE_BH", "COMMENT", "ORIGINE", "B_FLUVIAL", "STATUT", "SRC_COORD", "PREC_PLANI", "ACQU_PLANI", "ID_SOURCE", "SOURCE", "DATE_CONF", "DATE_APP", "DATE_MAJ", "DATE_CREAT", "BASS_HYDRO", "TOPONYME", "CODE_HYDRO"],
                               ["COMMENT", "PERMANENT", "MAREE", "STATUT", "ID_SOURCE", "SOURCE", "DATE_CONF", "DATE_APP", "DATE_MAJ", "DATE_CREAT", "IMPORTANCE", "STATUT_TOP", "TOPONYME", "CODE_HYDRO"],
                               ["NATURE", "NAT_DETAIL", "PERSISTANC", "TOPONYME", "STATUT_TOP", "IMPORTANCE", "ETAT", "DATE_CREAT", "DATE_MAJ", "DATE_APP", "DATE_CONF", "SOURCE", "ID_SOURCE", "ACQU_PLANI", "PREC_PLANI", "ID_BAN"],
                               ["CODE_HYDRO", "CODE_PAYS", "TYPE_LIMIT", "NIVEAU", "DATE_CREAT", "DATE_MAJ", "DATE_APP", "DATE_CONF", "SOURCE", "ID_SOURCE", "ACQU_PLANI", "PREC_PLANI", "SRC_COORD", "STATUT", "ORIGINE", "COMMENT"],
                               ["CODE_HYDRO", "CODE_PAYS", "CATEGORIE", "TOPONYME", "STATUT_TOP", "DATE_CREAT", "DATE_MAJ", "DATE_APP", "DATE_CONF", "SOURCE", "ID_SOURCE", "ACQU_PLANI", "PREC_PLANI", "ACQU_ALTI", "PREC_ALTI", "SRC_COORD", "SRC_ALTI", "STATUT", "COMMENT", "ID_CE_AMON", "ID_CE_AVAL"],
                               ["CODE_HYDRO", "NATURE", "TOPONYME", "STATUT_TOP", "IMPORTANCE", "DATE_CREAT", "DATE_MAJ", "DATE_APP", "DATE_CONF", "SOURCE", "ID_SOURCE", "STATUT", "MAREE", "PERMANENT", "Z_MOY", "REF_Z_MOY", "MODE_Z_MOY", "PREC_Z_MOY", "HAUT_MAX", "OBT_HT_MAX", "COMMENT"],
                               ["CODE_HYDRO", "CODE_PAYS", "NATURE", "POS_SOL", "ETAT", "DATE_CREAT", "DATE_MAJ", "DATE_APP", "DATE_CONF", "SOURCE", "ID_SOURCE", "ACQU_PLANI", "PREC_PLANI", "ACQU_ALTI", "PREC_ALTI", "SRC_COORD", "SRC_ALTI", "STATUT", "PERSISTANC", "SALINITE", "ORIGINE", "COMMENT", "ID_P_EAU", "ID_C_EAU", "ID_ENT_TR", "NOM_P_EAU", "NOM_C_EAU", "NOM_ENT_TR"],
                               ["CLASSE", "NATURE", "GRAPHIE", "SOURCE", "STATUT_TOP", "DATE_TOP", "LANGUE"],
                               ["NOM_ENT_TR", "NOM_C_EAU", "ID_ENT_TR", "ID_S_HYDRO", "ID_C_EAU", "CODE_CARTH", "COMMENT", "BRAS", "LARGEUR", "DELIMIT", "RES_COULAN", "SENS_ECOUL", "PER_ORDRE", "ORIGINE", "CLA_ORDRE", "NUM_ORDRE", "SALINITE", "NAVIGABL", "FOSSE", "PERSISTANC", "STATUT", "SRC_ALTI", "SRC_COORD", "PREC_ALTI", "ACQU_ALTI", "PREC_PLANI", "ACQU_PLANI", "ID_SOURCE", "SOURCE", "DATE_CONF", "DATE_APP", "DATE_MAJ", "DATE_CREAT", "ETAT", "POS_SOL", "FICTIF", "NATURE", "CODE_PAYS", "CODE_HYDRO"],
                               ["NATURE", "NAT_DETAIL", "TOPONYME", "STATUT_TOP", "IMPORTANCE", "DATE_CREAT", "DATE_MAJ", "DATE_APP", "DATE_CONF", "SOURCE", "ID_SOURCE", "ACQU_PLANI", "PREC_PLANI", "ID_BAN"],
                               ["NATURE", "TOPONYME", "STATUT_TOP", "IMPORTANCE", "DATE_CREAT", "DATE_MAJ", "DATE_APP", "DATE_CONF", "SOURCE", "ID_SOURCE", "ACQU_PLANI", "PREC_PLANI", "ID_BAN"],
                               ["CLASSE", "NATURE", "GRAPHIE", "SOURCE", "STATUT_TOP", "DATE_TOP", "LANGUE"],
                               ["NATURE", "NAT_DETAIL", "TOPONYME", "STATUT_TOP", "IMPORTANCE", "FICTIF", "ETAT", "DATE_CREAT", "DATE_MAJ", "DATE_APP", "DATE_CONF", "SOURCE", "ID_SOURCE", "ACQU_PLANI", "PREC_PLANI", "ID_BAN"],
                               ["DATE_CREAT", "DATE_MAJ", "DATE_APP", "DATE_CONF", "HAUTEUR", "LARGEUR", "SOURCE", "ID_SOURCE", "ACQU_PLANI", "PREC_PLANI"],
                               ["NATURE", "DATE_CREAT", "DATE_MAJ", "DATE_APP", "DATE_CONF", "SOURCE", "ID_SOURCE", "ACQU_PLANI", "PREC_PLANI"],
                               ["NATURE", "DATE_CREAT", "DATE_MAJ", "DATE_APP", "DATE_CONF", "ACQU_PLANI", "PREC_PLANI", "SOURCE", "ID_SOURCE"],
                               ["NATURE", "POS_SOL", "ETAT", "DATE_CREAT", "DATE_MAJ", "DATE_APP", "DATE_CONF", "SOURCE", "ID_SOURCE", "ACQU_PLANI", "PREC_PLANI", "ACQU_ALTI", "PREC_ALTI"],
                               ["ID_REF", "CATEGORIE", "TYPE_1", "TYPE_2", "ACTIV_1", "ACTIV_2", "LIBELLE", "ETAT", "DATE_CREAT", "DATE_MAJ", "DATE_APP", "DATE_CONF", "SOURCE", "ID_SOURCE", "ACQU_PLANI", "PREC_PLANI", "PUBLIC", "OUVERT", "CAP_ACC", "CAP_HEBERG", "ORIGIN_GEO", "TYPE_LOC", "VALID_IGN", "CODE_INSEE", "SIRET", "ADR_NUMERO", "ADR_REP", "ADR_COMPL", "ADR_NOM_1", "ADR_NOM_2", "CODE_POST", "ID_BATI", "ID_ENCEINT"],
                               ["VOLTAGE", "ETAT", "DATE_CREAT", "DATE_MAJ", "DATE_APP", "DATE_CONF", "SOURCE", "ID_SOURCE", "ACQU_PLANI", "PREC_PLANI", "ACQU_ALTI", "PREC_ALTI"],
                               ["TOPONYME", "STATUT_TOP", "IMPORTANCE", "ETAT", "DATE_CREAT", "DATE_MAJ", "DATE_APP", "DATE_CONF", "SOURCE", "ID_SOURCE", "ACQU_PLANI", "PREC_PLANI", "ACQU_ALTI", "PREC_ALTI"],
                               ["CLASSE", "NATURE", "GRAPHIE", "SOURCE", "STATUT_TOP", "DATE_TOP", "LANGUE"],
                               ["CATEGORIE", "NATURE", "NAT_DETAIL", "TOPONYME", "STATUT_TOP", "IMPORTANCE", "FICTIF", "ETAT", "DATE_CREAT", "DATE_MAJ", "DATE_APP", "DATE_CONF", "SOURCE", "ID_SOURCE", "ACQU_PLANI", "PREC_PLANI", "ID_BAN", "NOMCOMMERC"],
                               ["CATEGORIE", "NATURE", "USAGE", "TOPONYME", "STATUT_TOP", "FICTIF", "ETAT", "DATE_CREAT", "DATE_MAJ", "DATE_APP", "DATE_CONF", "SOURCE", "ID_SOURCE", "ACQU_PLANI", "PREC_PLANI", "ALTITUDE", "CODE_ICAO", "CODE_IATA"],
                               ["NATURE", "NAT_DETAIL", "TOPONYME", "STATUT_TOP", "IMPORTANCE", "FICTIF", "ETAT", "DATE_CREAT", "DATE_MAJ", "DATE_APP", "DATE_CONF", "SOURCE", "ID_SOURCE", "ACQU_PLANI", "PREC_PLANI", "ACQU_ALTI", "PREC_ALTI", "ID_BAN"],
                               ["NATURE", "NAT_DETAIL", "DATE_CREAT", "DATE_MAJ", "DATE_APP", "DATE_CONF", "SOURCE", "ID_SOURCE"],
                               ["DATE_CREAT", "DATE_MAJ", "DATE_APP", "DATE_CONF", "ID_TR_ENT", "ID_TR_SOR"],
                               ["NATURE", "FONCTION", "ETAT", "DATE_CREAT", "DATE_MAJ", "DATE_APP", "DATE_CONF", "SOURCE", "ID_SOURCE", "ACQU_PLANI", "PREC_PLANI", "ACQU_ALTI", "PREC_ALTI"],
                               ["DATE_CREAT", "DATE_MAJ", "DATE_APP", "DATE_CONF", "ACQU_PLANI", "PREC_PLANI", "SENS", "MODE", "ID_POI"],
                               ["DATE_CREAT", "DATE_MAJ", "DATE_APP", "DATE_CONF", "SOURCE", "ID_SOURCE", "ROUTE", "NUMERO", "ABSCISSE", "ORDRE", "COTE", "STATUT", "TYPE_DE_PR", "LIBELLE", "ID_SECTION", "INSEE_DEP", "ID_ROUTE", "GESTION"],
                               ["NATURE", "NAT_DETAIL", "TOPONYME", "STATUT_TOP", "ETAT", "DATE_CREAT", "DATE_MAJ", "DATE_APP", "DATE_CONF", "SOURCE", "ID_SOURCE", "ACQU_PLANI", "PREC_PLANI", "ACQU_ALTI", "PREC_ALTI", "ID_BAN"],
                               ["TYPE_ROUTE", "NUMERO", "TOPONYME", "STATUT_TOP", "DATE_CREAT", "DATE_MAJ", "DATE_APP", "DATE_CONF", "SOURCE", "ID_SOURCE", "GESTION"],
                               ["ID_SECTION", "NUM_ROUTE", "GESTION", "ID_ROUTE", "INSEE_DEP", "COTE", "SOURCE", "DATE_CONF", "DATE_CREAT", "DATE_MAJ"],
                               ["CLASSE", "NATURE", "GRAPHIE", "SOURCE", "STATUT_TOP", "DATE_TOP", "LANGUE"],
                               ["NATURE", "TOPONYME", "STATUT_TOP", "IMPORTANCE", "ETAT", "DATE_CREAT", "DATE_MAJ", "DATE_APP", "DATE_CONF", "SOURCE", "ID_SOURCE", "ACQU_PLANI", "PREC_PLANI", "ACQU_ALTI", "PREC_ALTI"],
                               ["DELESTAGE", "SRC_BAN_G", "SRC_BAN_D", "NOM_BAN_G", "NOM_BAN_D", "LD_BAN_G", "LD_BAN_D", "ID_BAN_G", "ID_BAN_D", "NOM_ITI", "NATURE_ITI", "VOIE_VERTE", "ITI_CYCL", "TOPONYME", "GESTION", "CL_ADMIN", "NUM_EUROP", "NUMERO", "ID_ITI", "ID_RN", "ID_VOIE_D", "ID_VOIE_G", "DATE_SERV", "ALIAS_D", "ALIAS_G", "INSEECOM_D", "INSEECOM_G", "BORNEFIN_D", "BORNEFIN_G", "BORNEDEB_D", "BORNEDEB_G", "RESTR_MAT", "RESTR_LON", "RESTR_LAR", "RESTR_PPE", "RESTR_P", "RESTR_H", "NAT_RESTR", "SENS_CYC_G", "SENS_CYC_D", "CYCLABLE_G", "CYCLABLE_D", "FERMETURE", "ACCES_PED", "ACCES_VL", "VIT_MOY_VL", "URBAIN", "BUS", "SENS", "PRIVE", "IT_VERT", "LARGEUR", "NB_VOIES", "PREC_ALTI", "ACQU_ALTI", "PREC_PLANI", "ACQU_PLANI", "ID_SOURCE", "SOURCE", "DATE_CONF", "DATE_APP", "DATE_MAJ", "DATE_CREAT", "ETAT", "POS_SOL", "FICTIF", "IMPORTANCE", "NOM_COLL_D", "NOM_COLL_G", "NATURE"],
                               ["NATURE", "POS_SOL", "ETAT", "DATE_CREAT", "DATE_MAJ", "DATE_APP", "DATE_CONF", "SOURCE", "ID_SOURCE", "ACQU_PLANI", "PREC_PLANI", "ACQU_ALTI", "PREC_ALTI", "ELECTRIFIE", "LARGEUR", "NB_VOIES", "USAGE", "VITES_MAX", "ID_VFN", "TOPONYME"],
                               ["TOPONYME", "STATUT_TOP", "DATE_CREAT", "DATE_MAJ", "DATE_APP", "DATE_CONF", "SOURCE", "ID_SOURCE"],
                               ["ID_VOIE", "TYPE_VOIE", "TYP_ADRES", "NOM_MIN", "NOM_INIT", "MOT_DIR", "VALIDITE", "DATE_CREAT", "DATE_MAJ", "CODE_INSEE", "CODE_POST", "ALIAS_INI", "ALIAS_MIN", "TYPE_LIAIS", "Q_MAJ_MIN", "FIABILITE"],
                               ["NATURE", "TOPONYME", "STATUT_TOP", "IMPORTANCE", "DATE_CREAT", "DATE_MAJ", "DATE_APP", "DATE_CONF", "SOURCE", "ID_SOURCE", "ACQU_PLANI", "PREC_PLANI"],
                               ["NATURE", "NAT_DETAIL", "TOPONYME", "STATUT_TOP", "FICTIF", "ETAT", "DATE_CREAT", "DATE_MAJ", "DATE_APP", "DATE_CONF", "SOURCE", "ID_SOURCE", "ACQU_PLANI", "PREC_PLANI"],
                               ["CLASSE", "NATURE", "GRAPHIE", "SOURCE", "STATUT_TOP", "DATE_TOP", "LANGUE"]]

    # Définition des variables
    postgis_schema_name = CHECK_BD_TOPO_DICO[zone][0]
    epsg = CHECK_BD_TOPO_DICO[zone][1]
    available_classes_list = CHECK_BD_TOPO_DICO[zone][2]

    ####################################################################

    print('\n' + cyan + "exportBdTopoFromPostgres() : " + bold + green + "DEBUT DES TRAITEMENTS" + endC)

    # Mise à jour du log
    starting_event = "exportBdTopoFromPostgres() : Début du traitement : "
    timeLine(path_time_log, starting_event)

    print('\n' + cyan + "exportBdTopoFromPostgres() : " + bold + green + "Début de la préparation des traitements." + endC)

    # Test existence du fichier vecteur d'entrée
    if not os.path.exists(input_vector):
        print('\n' + bold + red + "Error: Input vector file '%s' not exists!" % input_vector + endC)
        exit(-1)

    # Test format vecteur de sortie
    if not format_vector in [ESRI_SHAPEFILE_DRIVER_NAME, GPKG_DRIVER_NAME]:
        print('\n' + bold + red + "Error: Vector format '%s' is not recognize (must be '%s' or '%s')!" % (format_vector, ESRI_SHAPEFILE_DRIVER_NAME, GPKG_DRIVER_NAME) + endC)
        exit(-1)

    # Test zone d'étude
    if not zone in AVAILABLE_ZONE_LIST:
        print('\n' + bold + red + "Error: Zone '%s' is not in the available zones (%s)!" % (zone, str(AVAILABLE_ZONE_LIST)) + endC)
        exit(-1)

    # Test concordance EPSG du fichier vecteur d'entrée et de la base Postgres
    epsg_input_vector, projection = getProjection(input_vector, format_vector=input_format_vector)
    if epsg != epsg_input_vector:
        print('\n' + bold + red + "Error: Input vector file EPSG (%s) is not corresponding to requested BD TOPO database EPSG (%s)!" % (epsg_input_vector, epsg) + endC)
        exit(-1)

    # Récupération de l'emprise d'étude
    geometry_list = getGeomPolygons(input_vector, col=None, value=None, format_vector=input_format_vector)
    if len(geometry_list) == 0:
        print('\n' + bold + red + "Error: There are no geometry in the input vector file '%s'!" % input_vector + endC)
        exit(-1)
    elif len(geometry_list) > 1:
        print('\n' + bold + red + "Error: There are more than one geometry in the input vector file '%s' (%s geometries)!" % (input_vector, len(geometry_list)) + endC)
        exit(-1)
    else:
        geometry_roi = geometry_list[0].ExportToWkt()

    print('\n' + cyan + "exportBdTopoFromPostgres() : " + bold + green + "Fin de la préparation des traitements." + endC)

    ####################################################################

    print('\n' + cyan + "exportBdTopoFromPostgres() : " + bold + green + "Début des exports." + endC)

    # Boucle sur les classes à exporter
    bd_topo_empty_classe_list, idx = [], 1
    for bd_topo_classe in available_classes_list:
        print('\n' + bold + "Traitement de la classe '%s' (%s/%s)..." % (bd_topo_classe, str(idx), str(len(available_classes_list))) + endC)

        # Récupération des variables thème et champs
        bd_topo_index = BD_TOPO_CLASSES_LIST.index(bd_topo_classe)
        bd_topo_theme = BD_TOPO_THEMES_LIST[bd_topo_index]
        bd_topo_sql_fields = BD_TOPO_SQL_FIELDS_LIST[bd_topo_index]
        bd_topo_shp_fields = BD_TOPO_SHP_FIELDS_LIST[bd_topo_index]
        table_to_extract_select = '%s_select' % bd_topo_classe
        input_identifier_field = SQL_IDENTIFIER_TOPONYMY_FIELD if TOPONYMY_TABLE_NAME in bd_topo_classe else SQL_IDENTIFIER_FIELD
        if format_vector == ESRI_SHAPEFILE_DRIVER_NAME:
            output_identifier_field = SHP_IDENTIFIER_TOPONYMY_FIELD if TOPONYMY_TABLE_NAME in bd_topo_classe else SHP_IDENTIFIER_FIELD
            output_geom_field = SHP_GEOM_FIELD
        else:
            output_identifier_field = SQL_IDENTIFIER_TOPONYMY_FIELD if TOPONYMY_TABLE_NAME in bd_topo_classe else SQL_IDENTIFIER_FIELD
            output_geom_field = SQL_GEOM_FIELD

        # Construction du nom du fichier de sortie
        if format_vector == GPKG_DRIVER_NAME:
            if not os.path.exists(output_directory):
                os.makedirs(output_directory)
            database_name_split, schema_name_split = postgis_database_name.split('_'), postgis_schema_name.split('_')
            aoi_name = regExReplace(os.path.basename(os.path.splitext(input_vector)[0]), regex='[a-zA-Z0-9]', regex_replace='')
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
        query = "DROP TABLE IF EXISTS %s;\n" % table_to_extract_select
        query += "CREATE TABLE %s AS\n" % table_to_extract_select
        query += "    SELECT b.%s AS %s,\n" % (input_identifier_field, output_identifier_field)
        for bd_topo_sql_field in bd_topo_sql_fields:
            bd_topo_shp_field = bd_topo_shp_fields[bd_topo_sql_fields.index(bd_topo_sql_field)] if format_vector == ESRI_SHAPEFILE_DRIVER_NAME else bd_topo_sql_field
            query += "        b.%s AS %s,\n" % (bd_topo_sql_field, bd_topo_shp_field)
        query += "        b.%s AS %s\n" % (SQL_GEOM_FIELD, output_geom_field)
        query += "    FROM %s.%s AS b\n" % (postgis_schema_name, bd_topo_classe)
        query += "    WHERE ST_Intersects(b.%s, 'SRID=%s;%s');\n" % (SQL_GEOM_FIELD, str(epsg), geometry_roi)

        # Exécution de la requête d'export
        connection = openConnection(postgis_database_name, user_name=postgis_user_name, password=postgis_password, ip_host=postgis_ip_host, num_port=postgis_num_port, schema_name=PUBLIC_SCHEMA_NAME)
        if debug >= 4:
            print('\n' + query)
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

        idx += 1

    print('\n' + cyan + "exportBdTopoFromPostgres() : " + bold + green + "Fin des exports." + endC)

    ####################################################################

    # Suppression des tables temporaires
    query_clean = ""
    for bd_topo_classe in available_classes_list:
        table_to_extract_select = '%s_select' % bd_topo_classe
        query_clean += "DROP TABLE IF EXISTS %s;\n" % table_to_extract_select
    connection = openConnection(postgis_database_name, user_name=postgis_user_name, password=postgis_password, ip_host=postgis_ip_host, num_port=postgis_num_port, schema_name=PUBLIC_SCHEMA_NAME)
    if debug >= 4:
        print('\n' + bold + "Nettoyage des tables temporaires dans la base Postgres..." + endC)
        print(query_clean)
    executeQuery(connection, query_clean)
    closeConnection(connection)

    print('\n' + cyan + "exportBdTopoFromPostgres() : " + bold + green + "FIN DES TRAITEMENTS" + endC)

    # Mise à jour du log
    ending_event = "exportBdTopoFromPostgres() : Fin du traitement : "
    timeLine(path_time_log, ending_event)

    return 0

#############################################################################################################################
################################################## Mise en place du parser ##################################################
#############################################################################################################################

def main(gui=False):
    parser = argparse.ArgumentParser(prog = "ExportBdTopoFromPostgres", description = "\
    Exporter les classes BD TOPO montées en base Postgres, à partir d'un fichier d'emprise. \n\
    Exemple : python3 -m ExportBdTopoFromPostgres -in /mnt/RAM_disk/emprise_etude.shp \n\
                                                  -out /mnt/RAM_disk/BD_TOPO \n\
                                                  -zone FXX")

    parser.add_argument('-in', '--input_vector', default="", type=str, required=True, help="Input vector file.")
    parser.add_argument('-out', '--output_directory', default="", type=str, required=True, help="Output directory.")
    parser.add_argument('-zone', '--zone', choices=["FRA","FXX","GLP","MTQ","GUF","REU","MYT","SPM"], default="FXX", type=str, required=False, help="Zone to be treated to extract BD TOPO. Default: 'FXX'.")
    parser.add_argument('-vef', '--format_vector', choices=["ESRI Shapefile", "GPKG"], default="ESRI Shapefile", type=str, required=False, help="Format of vector files. Default: 'ESRI Shapefile'.")
    parser.add_argument('-vee', '--extension_vector', choices=[".shp", ".gpkg"], default=".shp", type=str, required=False, help="Extension file for vector files. Default: '.shp'.")
    parser.add_argument('-pgh', '--postgis_ip_host', default="172.22.130.99", type=str, required=False, help="PostGIS server name or IP adress. Default: '172.22.130.99'.")
    parser.add_argument('-pgp', '--postgis_num_port', default=5432, type=int, required=False, help="PostGIS port number. Default: '5432'.")
    parser.add_argument('-pgu', '--postgis_user_name', default="postgres", type=str, required=False, help="PostGIS user name. Default: 'postgres'.")
    parser.add_argument('-pgw', '--postgis_password', default="postgres", type=str, required=False, help="PostGIS user password. Default: 'postgres'.")
    parser.add_argument('-pgd', '--postgis_database_name', default="bdtopo_3_3_tousthemes_sql_scr_xxx_2022_12_15", type=str, required=False, help="PostGIS database name. Default: 'bdtopo_3_3_tousthemes_sql_scr_xxx_2022_12_15'.")
    parser.add_argument('-log', '--path_time_log', default="", type=str, required=False, help="Option: Name of log. Default, no log file.")
    parser.add_argument('-debug', '--debug', default=3, type=int, required=False, help="Option: Value of level debug trace. Default, 3.")
    args = displayIHM(gui, parser)

    # Récupération du fichier vecteur d'entrée
    if args.input_vector != None:
        input_vector = args.input_vector
        if not os.path.isfile(input_vector):
            raise NameError (cyan + "ExportBdTopoFromPostgres: " + bold + red  + "File %s not exists (input_vector)." % input_vector + endC)

    # Récupération du répertoire de sortie
    if args.output_directory != None:
        output_directory = args.output_directory

    # Récupération des paramètres spécifiques
    if args.zone != None:
        zone = args.zone

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
        print('\n' + bold + green + "Exporter les classes BD TOPO montées en base Postgres, à partir d'un fichier d'emprise - Variables dans le parser :" + endC)
        print(cyan + "    ExportBdTopoFromPostgres : " + endC + "input_vector : " + str(input_vector) + endC)
        print(cyan + "    ExportBdTopoFromPostgres : " + endC + "output_directory : " + str(output_directory) + endC)
        print(cyan + "    ExportBdTopoFromPostgres : " + endC + "zone : " + str(zone) + endC)
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
    exportBdTopoFromPostgres(input_vector, output_directory, zone, format_vector, extension_vector, postgis_ip_host, postgis_num_port, postgis_user_name, postgis_password, postgis_database_name, path_time_log)

if __name__ == '__main__':
    main(gui=False)

