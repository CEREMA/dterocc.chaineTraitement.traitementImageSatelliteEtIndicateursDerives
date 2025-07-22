#!/usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT QUI EXPORTE LES DONNEES BD NB MONTEES DANS UNE BASE POSTGRESQL/POSTGIS                                                           #
#                                                                                                                                           #
#############################################################################################################################################
'''
Nom de l'objet : ExportBdNBFromPostgres.py
Description :
    Objectif : exporter les données BD Natioal Batiment montées en base Postgres, à partir d'un fichier d'emprise
    Remarques :
        - ne gère que les formats SHP et GPKG (fichier unique multi-couches) en sortie (formats de référence IGN) :
            * valeurs possibles pour le paramètre "format_vector" : "ESRI Shapefile" / "GPKG"
            * valeurs possibles pour le paramètre "extension_vector" : ".shp" / ".gpkg"
    Limites :
        - peut ne fonctionne pas pour d'autre BD

-----------------
Outils utilisés :
 - PostgreSQL/PostGIS

------------------------------
Historique des modifications :
 - 24/03/2024 : création

-----------------------
A réfléchir / A faire :
 -
'''

# Import des bibliothèques Python
from __future__ import print_function
import os, argparse
from osgeo import ogr
from Lib_display import *
from Lib_log import timeLine
from Lib_text import readTextFileBySeparator, regExReplace
from Lib_file import removeVectorFile
from Lib_vector import getGeomPolygons, getProjection
from Lib_postgis import exportVectorByOgr2ogr, openConnection, executeQuery, getData, getAllTables, getAllColumns, closeConnection

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 3

########################################################################
# FONCTION exportBdNBFromPostgres()                                    #
########################################################################
def exportBdNBFromPostgres(input_vector, output_directory, buffer_size=0, fields_list=[], format_vector="GPKG", extension_vector=".gpkg", epsg=2154, postgis_ip_host="172.20.220.19", postgis_num_port=5432, postgis_user_name="consultation", postgis_password="consultation", postgis_database_name="e_datacart", postgis_schema_name="e_bdnb_cstb_2024_10", postgis_table_ref="batiment_groupe", path_time_log=""):
    '''
    # ROLE :
    #     Exporter les classes BD NB montées en base Postgres, à partir d'un fichier d'emprise
    #
    # ENTREES DE LA FONCTION :
    #     input_vector : fichier vecteur d'emprise d'étude en entrée
    #     output_directory : répertoire de sortie des fichiers vecteur
    #     buffer_size : taille du tampon (en m) appliqué pour la sélection des entités dans le vecteur d'emprise d'étude en entrée. Par défaut, 0
    #     fields_list : liste des champs précis de la BD NB désirés. Exemple ['TRANSPORT:aerodrome']. Par défaut, tous les champs
    #     format_vector : format des fichiers vecteur. Par défaut : ESRI Shapefile
    #     extension_vector : extension des fichiers vecteur. Par défaut : .shp
    #     epsg : EPSG code de projection. Par défaut : 2154
    #     postgis_ip_host : nom du serveur PostGIS. Par défaut : 172.20.220.19
    #     postgis_num_port : numéro de port du serveur PostGIS. Par défaut : 5432
    #     postgis_user_name : nom d'utilisateur PostGIS. Par défaut : consultation
    #     postgis_password : mot de passe de l'utilisateur PostGIS. Par défaut : consultation
    #     postgis_database_name : nom de la base PostGIS. Par défaut : e_datacart
    #     postgis_schema_name :  nom du shema PostGIS. Par défaut : e_bdnb_cstb_2024_10
    #     postgis_table_ref : nom de la table d'entrée de référence : batiment_groupe
    #     path_time_log : fichier log de sortie, par défaut vide (affichage console)
    #
    # SORTIES DE LA FONCTION :
    #     N.A.
    '''
    if debug >= 3:
        print(bold + green + "Exporter les classes BD NB montées en base Postgres, à partir d'un fichier d'emprise - Variables dans la fonction :" + endC)
        print(cyan + "exportBdNBFromPostgres() : " + endC + "input_vector : " + str(input_vector) + endC)
        print(cyan + "exportBdNBFromPostgres() : " + endC + "output_directory : " + str(output_directory) + endC)
        print(cyan + "exportBdNBFromPostgres() : " + endC + "buffer_size : " + str(buffer_size) + endC)
        print(cyan + "exportBdNBFromPostgres() : " + endC + "fields_list : " + str(fields_list) + endC)
        print(cyan + "exportBdNBFromPostgres() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "exportBdNBFromPostgres() : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "exportBdNBFromPostgres() : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "exportBdNBFromPostgres() : " + endC + "postgis_ip_host : " + str(postgis_ip_host) + endC)
        print(cyan + "exportBdNBFromPostgres() : " + endC + "postgis_num_port : " + str(postgis_num_port) + endC)
        print(cyan + "exportBdNBFromPostgres() : " + endC + "postgis_user_name : " + str(postgis_user_name) + endC)
        print(cyan + "exportBdNBFromPostgres() : " + endC + "postgis_password : " + str(postgis_password) + endC)
        print(cyan + "exportBdNBFromPostgres() : " + endC + "postgis_database_name : " + str(postgis_database_name) + endC)
        print(cyan + "exportBdNBFromPostgres() : " + endC + "postgis_schema_name : " + str(postgis_schema_name) + endC)
        print(cyan + "exportBdNBFromPostgres() : " + endC + "postgis_table_ref : " + str(postgis_table_ref) + endC)
        print(cyan + "exportBdNBFromPostgres() : " + endC + "path_time_log : " + str(path_time_log) + endC)

    # Définition des constantes
    ESRI_SHAPEFILE_DRIVER_NAME, GPKG_DRIVER_NAME = "ESRI Shapefile", "GPKG"
    BD_NB_ENCODING = "UTF-8"
    SQL_GEOM_FIELD, SHP_GEOM_FIELD = "geom_groupe", "GEOM"
    SUFFIX_BDNB = "_BdNB"

    JOINS_AND_TABLES_DICO = {
        'batiment_groupe_adresse':[('batiment_groupe_adresse', 'batiment_groupe_id')],
        'batiment_groupe_argiles':[('batiment_groupe_argiles', 'batiment_groupe_id')],
        'batiment_groupe_bdtopo_bat':[('batiment_groupe_bdtopo_bat', 'batiment_groupe_id')],
        'batiment_groupe_bdtopo_equ':[('batiment_groupe_bdtopo_equ', 'batiment_groupe_id')],
        'batiment_groupe_bdtopo_zoac':[('batiment_groupe_bdtopo_zoac', 'batiment_groupe_id')],
        'batiment_groupe_bpe':[('batiment_groupe_bpe', 'batiment_groupe_id')],
        'batiment_groupe_dle_elec_multimillesime':[('batiment_groupe_dle_elec_multimillesime', 'batiment_groupe_id')],
        'batiment_groupe_dle_gaz_multimillesime':[('batiment_groupe_dle_gaz_multimillesime', 'batiment_groupe_id')],
        'batiment_groupe_dle_reseaux_multimillesime':[('batiment_groupe_dle_reseaux_multimillesime', 'batiment_groupe_id')],
        'batiment_groupe_dpe_representatif_logement':[('batiment_groupe_dpe_representatif_logement', 'batiment_groupe_id')],
        'batiment_groupe_dpe_statistique_logement':[('batiment_groupe_dpe_statistique_logement', 'batiment_groupe_id')],
        'batiment_groupe_dvf_open_representatif':[('batiment_groupe_dvf_open_representatif', 'batiment_groupe_id')],
        'batiment_groupe_dvf_open_statistique':[('batiment_groupe_dvf_open_statistique', 'batiment_groupe_id')],
        'batiment_groupe_ffo_bat':[('batiment_groupe_ffo_bat', 'batiment_groupe_id')],
        'batiment_groupe_geospx':[('batiment_groupe_geospx', 'batiment_groupe_id')],
        'batiment_groupe_hthd':[('batiment_groupe_hthd', 'batiment_groupe_id')],
        'batiment_groupe_indicateur_reseau_chaud_froid':[('batiment_groupe_indicateur_reseau_chaud_froid', 'batiment_groupe_id')],
        'batiment_groupe_merimee':[('batiment_groupe_merimee', 'batiment_groupe_id')],
        'batiment_groupe_qpv':[('batiment_groupe_qpv', 'batiment_groupe_id')],
        'batiment_groupe_radon':[('batiment_groupe_radon', 'batiment_groupe_id')],
        'batiment_groupe_rnc':[('batiment_groupe_rnc', 'batiment_groupe_id')],
        'batiment_groupe_rpls':[('batiment_groupe_rpls', 'batiment_groupe_id')],
        'batiment_groupe_simulations_dpe':[('batiment_groupe_simulations_dpe', 'batiment_groupe_id')],
        'batiment_groupe_simulations_dvf':[('batiment_groupe_simulations_dvf', 'batiment_groupe_id')],
        'batiment_groupe_simulations_isb':[('batiment_groupe_simulations_isb', 'batiment_groupe_id')],
        'batiment_groupe_simulations_valeur_verte':[('batiment_groupe_simulations_valeur_verte', 'batiment_groupe_id')],
        'batiment_groupe_synthese_enveloppe':[('batiment_groupe_synthese_enveloppe', 'batiment_groupe_id')],
        'batiment_groupe_synthese_propriete_usage':[('batiment_groupe_synthese_propriete_usage', 'batiment_groupe_id')],
        'batiment_groupe_synthese_systeme_energetique_logement':[('batiment_groupe_synthese_systeme_energetique_logement', 'batiment_groupe_id')],

        'rel_batiment_groupe_bdtopo_bat':[('rel_batiment_groupe_bdtopo_bat', 'batiment_groupe_id')],
        'rel_batiment_groupe_bdtopo_equ':[('rel_batiment_groupe_bdtopo_equ', 'batiment_groupe_id')],
        'rel_batiment_groupe_bdtopo_zoa':[('rel_batiment_groupe_bdtopo_zoa', 'batiment_groupe_id')],
        'rel_batiment_groupe_bpe':[('rel_batiment_groupe_bpe', 'batiment_groupe_id')],
        'rel_batiment_groupe_dvf_open':[('rel_batiment_groupe_dvf_open', 'batiment_groupe_id')],
        'rel_batiment_groupe_merimee':[('rel_batiment_groupe_merimee', 'batiment_groupe_id')],
        'rel_batiment_groupe_qpv':[('rel_batiment_groupe_qpv', 'batiment_groupe_id')],
        'rel_batiment_groupe_rnc':[('rel_batiment_groupe_rnc', 'batiment_groupe_id')],
        'rel_batiment_construction_adresse':[('rel_batiment_construction_adresse', 'batiment_groupe_id')],

        'iris':[('iris', 'code_iris')],
        'iris_contexte_geographique':[('iris_contexte_geographique', 'code_iris')],
        'iris_simulations_valeur_verte':[('iris_simulations_valeur_verte', 'code_iris')],

        'rel_batiment_groupe_siren':[('rel_batiment_groupe_siren', 'batiment_groupe_id')],
        'siren':[('rel_batiment_groupe_siren', 'batiment_groupe_id'),('siren', 'siren')],

        'rel_batiment_groupe_siret':[('rel_batiment_groupe_siret', 'batiment_groupe_id')],
        'siret':[('rel_batiment_groupe_siret', 'batiment_groupe_id'),('siret', 'siret')],

        'rel_batiment_groupe_adresse':[('rel_batiment_groupe_adresse', 'batiment_groupe_id')],
        'adresse':[('rel_batiment_groupe_adresse', 'batiment_groupe_id'),('adresse', 'cle_interop_adr')],
        'adresse_metrique':[('rel_batiment_groupe_adresse', 'batiment_groupe_id'),('adresse_metrique', 'cle_interop_adr')],

        'batiment_construction':[('batiment_construction', 'batiment_groupe_id')],
        'rel_batiment_construction_rnb':[('batiment_construction', 'batiment_groupe_id'),('rel_batiment_construction_rnb', 'batiment_construction_id')],

        'commune':[('commune', 'code_commune_insee')],
        'departement':[('departement', 'code_departement_insee')],
        'region':[('departement', 'code_departement_insee'), ('region', 'code_region_insee')],

        'rel_batiment_groupe_dpe_logement':[('rel_batiment_groupe_dpe_logement', 'batiment_groupe_id')],
        'dpe_logement':[('rel_batiment_groupe_dpe_logement', 'batiment_groupe_id'),('dpe_logement', 'identifiant_dpe')],
        'local_simulations_dpe':[('local_simulations_dpe', 'batiment_groupe_id')],

        'rel_batiment_groupe_parcelle':[('rel_batiment_groupe_parcelle', 'batiment_groupe_id')],
        'parcelle':[('rel_batiment_groupe_parcelle', 'batiment_groupe_id'),('parcelle', 'parcelle_id')],
        'parcelle_sitadel':[('rel_batiment_groupe_parcelle', 'batiment_groupe_id'),('parcelle_sitadel', 'parcelle_id')],
        'rel_parcelle_sitadel':[('rel_batiment_groupe_parcelle', 'batiment_groupe_id'),('rel_parcelle_sitadel', 'parcelle_id')],
        'sitadel':[('rel_batiment_groupe_parcelle', 'batiment_groupe_id'),('rel_parcelle_sitadel', 'parcelle_id'),('sitadel', 'type_numero_dau')],

        'rel_batiment_groupe_proprietaire':[('rel_batiment_groupe_proprietaire', 'batiment_groupe_id')],
        'proprietaire':[('rel_batiment_groupe_proprietaire', 'batiment_groupe_id'),('proprietaire', 'personne_id')],

        'passage_millesime_batiment_groupe_id':[('passage_millesime_batiment_groupe_id', '???')]
    }

    ####################################################################
    if debug >= 2:
        print(cyan + "exportBdNBFromPostgres() : " + bold + green + "DEBUT DES TRAITEMENTS" + endC)

    # Mise à jour du log
    starting_event = "exportBdNBFromPostgres() : Début du traitement : "
    timeLine(path_time_log, starting_event)

    if debug >= 2:
        print(cyan + "exportBdNBFromPostgres() : " + bold + green + "Début de la préparation des traitements." + endC)

    # Test existence du fichier vecteur d'entrée
    if not os.path.exists(input_vector):
        raise NameError(cyan + "exportBdNBFromPostgres() : " + bold + red + "Error: Input vector file \"%s\" not exists!" % input_vector + endC)

    # Test format vecteur de sortie
    if not format_vector in [ESRI_SHAPEFILE_DRIVER_NAME, GPKG_DRIVER_NAME]:
        raise NameError(cyan + "exportBdNBFromPostgres() : " + bold + red + "Error: Vector format \"%s\" is not recognize (must be \"%s\" or \"%s\")!" % (format_vector, ESRI_SHAPEFILE_DRIVER_NAME, GPKG_DRIVER_NAME) + endC)

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

    # Test concordance EPSG du fichier vecteur d'entrée et de la base Postgres
    epsg_input_vector, projection = getProjection(input_vector, format_vector=input_format_vector)
    if epsg != epsg_input_vector:
        raise NameError(cyan + "exportBdNBFromPostgres() : " + bold + red + "Error: Input vector file EPSG (%s) is not corresponding to requested BD NB database EPSG (%s)!" % (epsg_input_vector, epsg) + endC)

    # Récupération de l'emprise d'étude
    geometry_list = getGeomPolygons(input_vector, col=None, value=None, format_vector=input_format_vector)
    if len(geometry_list) == 0:
        raise NameError(cyan + "exportBdNBFromPostgres() : " + bold + red + "Error: There are no geometry in the input vector file \"%s\"!" % input_vector + endC)
    elif len(geometry_list) > 1:
        raise NameError(cyan + "exportBdNBFromPostgres() : " + bold + red + "Error: There are more than one geometry in the input vector file \"%s\" (%s geometries)!" % (input_vector, len(geometry_list)) + endC)
    else:
        geometry_roi = geometry_list[0].ExportToWkt()
        if buffer_size > 0:
            geometry_roi = geometry_list[0].Buffer(buffer_size).ExportToWkt()

    # Export des toutes les tables et de leurs champs
    fields_and_tables_dico = {}
    connection = openConnection(postgis_database_name, user_name=postgis_user_name, password=postgis_password, ip_host=postgis_ip_host, num_port=postgis_num_port, schema_name=postgis_schema_name)
    tables_list = getAllTables(connection, postgis_schema_name, print_result=False)
    for table_name in tables_list :
        columns_list = getAllColumns(connection, table_name, print_result=False)
        fields_and_tables_dico[table_name] = columns_list
        ##formatted_columns = [col for col in columns_list]
        ##print(f"'{table_name}':{formatted_columns},")
        ##print(f"'{table_name}':[('{table_name}', 'batiment_groupe_id')],")
    closeConnection(connection)

    # Test de conformité des champs sélectionnés
    field_table_dico = {}
    doublon_field_list = []
    field_list = []
    table_to_joint_list = []
    if fields_list:
        for field in fields_list :
            if "." in field :
                table_field = field.split(".")
                if table_field[0] in list(fields_and_tables_dico.keys()) and table_field[1] in fields_and_tables_dico[table_field[0]]:
                    if table_field[1] in field_list :
                        doublon_field_list.append(table_field[1])
                    field_list.append(table_field[1])
                    field_table_dico[field] = table_field[0]
                    if not table_field[0] in table_to_joint_list :
                        table_to_joint_list.append(table_field[0])
                else :
                    if table_field[0] in list(fields_and_tables_dico.keys()) :
                        raise NameError(cyan + "exportBdNBFromPostgres() : " + bold + red + "Error: Field %s does not exist in table %s !" %(table_field[1], table_field[0]) + endC)
                    else :
                        raise NameError(cyan + "exportBdNBFromPostgres() : " + bold + red + "Error: Table %s does not exist!" %(table_field[0]) + endC)
            else :
                for table in fields_and_tables_dico :
                    field_table_dico[field] = None
                    if field in fields_and_tables_dico[table] :
                        if field in field_list :
                            doublon_field_list.append(field)
                        field_list.append(field)
                        field_table_dico[field] = table
                        if not table in table_to_joint_list :
                            table_to_joint_list.append(table)
                        break
                if field_table_dico[field] is None :
                    raise NameError(cyan + "exportBdNBFromPostgres() : " + bold + red + "Error: Field %s does not exist in any tables !" %(field) + endC)

    if debug >= 2:
        print(cyan + "exportBdNBFromPostgres() : " + bold + green + "Fin de la préparation des traitements." + endC)

    ####################################################################
    if debug >= 2:
        print(cyan + "exportBdNBFromPostgres() : " + bold + green + "Début des exports." + endC)

    # Construction du nom du fichier de sortie
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
    base_name = os.path.splitext(os.path.basename(input_vector))[0]
    output_vector_file = output_directory + os.sep + base_name + SUFFIX_BDNB + extension_vector
    if os.path.isfile(output_vector_file) :
        removeVectorFile(output_vector_file, format_vector=format_vector)

    # Construction de la requête d'export #
    #######################################

    # Cas ou auccun champs suplementaire ne sont demandés
    if not fields_list :
        select_query = "*"
        if format_vector == ESRI_SHAPEFILE_DRIVER_NAME :
            if postgis_table_ref in list(fields_and_tables_dico.keys()) :
                select_query = ""
                for field in fields_and_tables_dico.get(postgis_table_ref) :
                    select_query += "b.%s AS %s, " %(field, field[:10])
                select_query += "b.%s AS %s" %(SQL_GEOM_FIELD, SHP_GEOM_FIELD)
        query = "SELECT %s\n" %(select_query)
        query += "FROM %s.%s AS b\n" %(postgis_schema_name, postgis_table_ref)
        query += "WHERE ST_Intersects(b.%s, 'SRID=%s;%s')" %(SQL_GEOM_FIELD, str(epsg), geometry_roi)

    # Cas ou des champs suplementaires sont accessible par jointure simple ou complexe
    else :
        sql_field_list_str = ""
        sql_table_list_str = ""
        for field in fields_list :
            if "." in field :
                table_field = field.split(".")
                if table_field[1] in doublon_field_list :
                    sql_field_list_str += field + " AS " + table_field[1] + "__" + table_field[0] + ", "
                else :
                    sql_field_list_str += field + ", "
            else :
                sql_field_list_str += field_table_dico[field] + "." + field + ", "
        sql_field_list_str = sql_field_list_str[:-2]
        for table in table_to_joint_list :
            sql_table_list_str += postgis_schema_name +  "." + table + ", "
        sql_table_list_str = sql_table_list_str[:-2]
        if debug >= 5:
            print(sql_field_list_str)
            print(sql_table_list_str)

        # Préparation des jointures de tables
        sql_joint_table_dico = {}
        for table in table_to_joint_list :
            len_table = len(JOINS_AND_TABLES_DICO[table])
            if len_table == 1 :
                sql_joint_table_dico[table]=("i." + JOINS_AND_TABLES_DICO[table][0][1] + " = " + table + "." + JOINS_AND_TABLES_DICO[table][0][1])
            else :
                sql_joint_table_dico[JOINS_AND_TABLES_DICO[table][0][0]]=("i." + JOINS_AND_TABLES_DICO[table][0][1] + " = " + JOINS_AND_TABLES_DICO[table][0][0] + "." + JOINS_AND_TABLES_DICO[table][0][1])
                sql_joint_table_dico[JOINS_AND_TABLES_DICO[table][1][0]]=(JOINS_AND_TABLES_DICO[table][0][0] + "." + JOINS_AND_TABLES_DICO[table][1][1] + " = " + JOINS_AND_TABLES_DICO[table][1][0] + "." + JOINS_AND_TABLES_DICO[table][1][1])
                if len_table > 2 :
                    sql_joint_table_dico[JOINS_AND_TABLES_DICO[table][2][0]]=(JOINS_AND_TABLES_DICO[table][1][0] + "." + JOINS_AND_TABLES_DICO[table][2][1] + " = " + JOINS_AND_TABLES_DICO[table][2][0] + "." + JOINS_AND_TABLES_DICO[table][2][1])
        if debug >= 5:
            print(sql_joint_table_dico)

        query = "SELECT DISTINCT ON (batiment_groupe_id) i.*, %s\n" %(sql_field_list_str)
        query += "FROM (\n"
        query += "    SELECT * \n"
        query += "    FROM %s.%s AS b\n" %(postgis_schema_name, postgis_table_ref)
        query += "    WHERE ST_Intersects(b.%s, 'SRID=%s;%s')\n" %(SQL_GEOM_FIELD, str(epsg), geometry_roi)
        query += ") AS i\n"
        for table, jointure_str in list(sql_joint_table_dico.items()):
            query += "LEFT JOIN  %s.%s\n" %(postgis_schema_name, table)
            query += "    ON  %s\n" %(jointure_str)
        query = query[:-1] + ";\n"

    if debug >= 4:
        print(query)

    #  Exécution de la requête d'export à l'emprise d'étude
    if format_vector == GPKG_DRIVER_NAME:
        ogr2ogr_more_parameters = "-nln %s -overwrite" %(postgis_table_ref)
    if format_vector == ESRI_SHAPEFILE_DRIVER_NAME:
        ogr2ogr_more_parameters = "-lco ENCODING=%s" %(BD_NB_ENCODING)

    ogr2ogr_more_parameters += " -sql \"%s\"" % query
    exportVectorByOgr2ogr(postgis_database_name, output_vector_file, postgis_table_ref, user_name=postgis_user_name, password=postgis_password, ip_host=postgis_ip_host, num_port=postgis_num_port, schema_name=postgis_schema_name, format_type=format_vector, ogr2ogr_more_parameters=ogr2ogr_more_parameters)
    # Si la requete n'aboutit pas a cause de l'emprise => à traiter!
    #print(cyan + "exportBdNBFromPostgres() : " + bold + yellow + "L'emprise d'étude n'intersecte pas d'entité pour la classe \"%s\"." % bd_topo_classe)

    if debug >= 2:
        print(cyan + "exportBdNBFromPostgres() : " + bold + green + "Fin des exports." + endC)

    # Mise à jour du log
    ending_event = "exportBdNBFromPostgres() : Fin du traitement : "
    timeLine(path_time_log, ending_event)

    return 0

#############################################################################################################################
################################################## Mise en place du parser ##################################################
#############################################################################################################################

def main(gui=False):
    parser = argparse.ArgumentParser(prog = "ExportBdNBFromPostgres", description = "\
    Exporter les classes BD NB montées en base Postgres, à partir d'un fichier d'emprise. \n\
    Exemple : python3 -m ExportBdNBFromPostgres -in /mnt/RAM_disk/Emprises/Emprise_Aigrefeuille.shp \n\
                                                -out /mnt/RAM_disk/BDdNB \n\
                                                -fields identifiant_dpe surface_mur_deperditif  libelle_iris type_iris \n\
                                                        batiment_groupe_dle_gaz_multimillesime.conso_pro  \n\
                                                        batiment_groupe_dle_elec_multimillesime.conso_pro \n\
                                                        adresse.libelle_adresse")

    parser.add_argument("-in", "--input_vector", default="", type=str, required=True, help="Input vector file.")
    parser.add_argument("-out", "--output_directory", default="", type=str, required=True, help="Output directory.")
    parser.add_argument("-buf", "--buffer_size", default=0, type=float, required=False, help="Buffer size (in meters) applied for feature selection from input vector file. Default: 0")
    parser.add_argument('-fields', '--fields_list', default="", type=str, nargs="+", required=False, help="Fields to extract from the BD NB database. Default: [].")
    parser.add_argument("-vef", "--format_vector", choices=["ESRI Shapefile", "GPKG"], default="GPKG", type=str, required=False, help="Format of vector files. Default: GPKG.")
    parser.add_argument("-vee", "--extension_vector", choices=[".shp", ".gpkg"], default=".gpkg", type=str, required=False, help="Extension file for vector files. Default: .gpkg.")
    parser.add_argument('-epsg','--epsg', default=2154,help="EPSG code projection.", type=int, required=False)
    parser.add_argument("-pgh", "--postgis_ip_host", default="172.20.220.19", type=str, required=False, help="PostGIS server name or IP adress. Default: 172.20.220.19.")
    parser.add_argument("-pgp", "--postgis_num_port", default=5432, type=int, required=False, help="PostGIS port number. Default: 5432.")
    parser.add_argument("-pgu", "--postgis_user_name", default="consultation", type=str, required=False, help="PostGIS user name. Default: consultation.")
    parser.add_argument("-pgw", "--postgis_password", default="consultation", type=str, required=False, help="PostGIS user password. Default: consultation.")
    parser.add_argument("-pgd", "--postgis_database_name", default="e_datacart", type=str, required=False, help="PostGIS database name. Default: e_datacart.")
    parser.add_argument("-pgs", "--postgis_schema_name", default="e_bdnb_cstb_2024_10", type=str, required=False, help="PostGIS shema name. Default: e_bdnb_cstb_2024_10.")
    parser.add_argument("-ptf", "--postgis_table_ref", default="batiment_groupe", type=str, required=False, help="PostGIS table reference name. Default: batiment_groupe.")
    parser.add_argument("-log", "--path_time_log", default="", type=str, required=False, help="Option: Name of log. Default, no log file.")
    parser.add_argument("-debug", "--debug", default=3, type=int, required=False, help="Option: Value of level debug trace. Default, 3.")
    args = displayIHM(gui, parser)

    # Récupération du fichier vecteur d'entrée
    if args.input_vector != None:
        input_vector = args.input_vector
        if not os.path.isfile(input_vector):
            raise NameError (cyan + "ExportBdNBFromPostgres: " + bold + red  + "File \"%s\" not exists (input_vector)." % input_vector + endC)

    # Récupération du répertoire de sortie
    if args.output_directory != None:
        output_directory = args.output_directory

    # Récupération de la taille du tampon de sélection
    if args.buffer_size != None:
        buffer_size = args.buffer_size

    # Récupération des paramètres spécifiques aux champs
    if args.fields_list != None:
        fields_list = args.fields_list

    # Récupération des paramètres fichiers
    if args.format_vector != None:
        format_vector = args.format_vector
    if args.extension_vector != None:
        extension_vector = args.extension_vector

    # Récupération du code EPSG de la projection du shapefile
    if args.epsg != None :
        epsg = args.epsg

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
    if args.postgis_schema_name != None:
        postgis_schema_name = args.postgis_schema_name
    if args.postgis_schema_name != None:
        postgis_table_ref = args.postgis_table_ref

    # Récupération des paramètres généraux
    if args.path_time_log != None:
        path_time_log = args.path_time_log
    if args.debug != None:
        global debug
        debug = args.debug

    if debug >= 3:
        print(bold + green + "Exporter les classes BD NB montées en base Postgres, à partir d'un fichier d'emprise - Variables dans le parser :" + endC)
        print(cyan + "ExportBdNBFromPostgres : " + endC + "input_vector : " + str(input_vector) + endC)
        print(cyan + "ExportBdNBFromPostgres : " + endC + "output_directory : " + str(output_directory) + endC)
        print(cyan + "ExportBdNBFromPostgres : " + endC + "buffer_size : " + str(buffer_size) + endC)
        print(cyan + "ExportBdNBFromPostgres : " + endC + "fields_list : " + str(fields_list) + endC)
        print(cyan + "ExportBdNBFromPostgres : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "ExportBdNBFromPostgres : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "ExportBdNBFromPostgres : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "ExportBdNBFromPostgres : " + endC + "postgis_ip_host : " + str(postgis_ip_host) + endC)
        print(cyan + "ExportBdNBFromPostgres : " + endC + "postgis_num_port : " + str(postgis_num_port) + endC)
        print(cyan + "ExportBdNBFromPostgres : " + endC + "postgis_user_name : " + str(postgis_user_name) + endC)
        print(cyan + "ExportBdNBFromPostgres : " + endC + "postgis_password : " + str(postgis_password) + endC)
        print(cyan + "ExportBdNBFromPostgres : " + endC + "postgis_database_name : " + str(postgis_database_name) + endC)
        print(cyan + "ExportBdNBFromPostgres : " + endC + "postgis_schema_name : " + str(postgis_schema_name) + endC)
        print(cyan + "ExportBdNBFromPostgres : " + endC + "postgis_table_ref : " + str(postgis_table_ref) + endC)
        print(cyan + "ExportBdNBFromPostgres : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "ExportBdNBFromPostgres : " + endC + "debug : " + str(debug) + endC)

    # EXECUTION DE LA FONCTION
    exportBdNBFromPostgres(input_vector, output_directory, buffer_size, fields_list, format_vector, extension_vector, epsg, postgis_ip_host, postgis_num_port, postgis_user_name, postgis_password, postgis_database_name, postgis_schema_name, postgis_table_ref, path_time_log)

if __name__ == "__main__":
    main(gui=False)

