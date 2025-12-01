#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.               #
#############################################################################

#############################################################################
#                                                                           #
#     FONCTIONS EN LIEN AVEC DES REQUETES SQL PostgreSQL / PostGIS          #
#                                                                           #
#############################################################################
"""
 Ce module défini des fonctions en lien avec des requetes SQL vers l'outil PostgreSQL / PostGIS.
 Notes diverses :
 Pour utiliser certains modules (notamment createDatabase() / dropDatabase() / importVectorByOgr2ogr() / exportVectorByOgr2ogr() / importShape() / exportShape() / importRaster()),
 il est préférable d'être déconnecté de la base de données (conflit d'accès).
 Certains modules retournent une information, qui peut être utilisée par d'autres modules, ou traitée comme variable dans des scripts :
 connection = openConnection()
 data_list = getData()
 table_name = importVectorByOgr2ogr()
 table_name = importShape()
 data_read = readTable()
 databases_list = getAllDatabases()
 schemas_list = getAllSchemas()
 tables_list = getAllTables()
 columns_list = getAllColumns()
 postgresql_version = versionPostgreSQL()
 postgis_version = versionPostGIS()
"""

from __future__ import print_function
import os, sys, csv, psycopg2, re, platform
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC
from Lib_text import readTextFile, appendTextFileCR
from Lib_log import timeLine
debug = 3

########################################################################
# FONCTION openConnection()                                            #
########################################################################
def openConnection(database_name, user_name='postgres', password='postgres', ip_host='localhost', num_port='5432', schema_name='public'):
    """
    # Rôle : se connecter à une base de données
    # Paramètres en entrée :
    #   database_name : nom de la base de données à laquelle se connecter
    #   user_name : nom d'utilisateur du serveur PostgreSQL (par défaut : 'postgres')
    #   password : mot de passe du serveur PostgreSQL (par défaut : 'postgres')
    #   ip_host : adresse IP du serveur PostgreSQL (par défaut : 'localhost')
    #   num_port : numéro de port du serveur PostgreSQL (par défaut : '5432')
    #   schema_name : nom du schema à utiliser (par défaut : 'public')
    # Paramètre de retour :
    #   les paramètres de la connexion
    """

    connection = None
    try:
        if schema_name == '' :
            connection = psycopg2.connect(dbname=database_name, user=user_name, password=password, host=ip_host, port=num_port)
        else :
            option_shema = "--search_path=" + "{}".format(schema_name)
            connection = psycopg2.connect(dbname=database_name, user=user_name, password=password, host=ip_host, port=num_port, options=option_shema)
    except psycopg2.DatabaseError as err:
        if connection:
            connection.rollback()
            connection.close()
        e = "OS error: {0}".format(err)
        print(bold + red + "openConnection() : Error %s - Impossible d'ouvrir la connexion à la base de données %s (machine hôte : %s, utilisateur : %s)" %(e, database_name, ip_host, user_name) + endC, file=sys.stderr)
        sys.exit(1)
    return connection

########################################################################
# FONCTION closeConnection()                                           #
########################################################################
def closeConnection(connection):
    """
    # Rôle : se déconnecter d'une une base de données
    # Paramètres en entrée :
    #   connection : laissez tel quel, récupère les informations de connexion à la base de données
    """

    if connection:
        connection.close()
    return

########################################################################
# FONCTION executeQuery()                                              #
########################################################################
def executeQuery(connection, query):
    """
    # Rôle : exécuter une requête SQL
    # Paramètres en entrée :
    #   connection : laissez tel quel, récupère les informations de connexion à la base de données
    #   query : requête SQL à exécuter dans la base de données (par exemple, 'SELECT * FROM table WHERE condition')
    """

    if debug >= 4:
        print("Exécution de la requête '%s'" % (query))
    connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = connection.cursor()
    cursor.execute(query)
    connection.commit()
    cursor.close()
    return

########################################################################
# FONCTION checkPassword()                                             #
########################################################################
def checkPassword(user_name='postgres', password='postgres', ip_host='localhost', num_port='5432'):
    """
    # Rôle : teste l'existence de la ligne contenant les identifiants de connexions dans fichier 'pgpass' (fonction qui utilise psql : importShape et importRaster)
    # Paramètres en entrée :
    #   user_name : nom d'utilisateur du serveur PostgreSQL (par défaut : 'postgres')
    #   password : mot de passe du serveur PostgreSQL (par défaut : 'postgres')
    #   ip_host : adresse IP du serveur PostgreSQL (par défaut : 'localhost')
    #   num_port : numéro de port du serveur PostgreSQL (par défaut : '5432')
    """

    osSystem = platform.system()
    if "Windows" in osSystem:
        file_pgpass = os.path.expanduser('~') + "\\AppData\\Roaming\\postgresql\\pgpass.conf"
    else:
        file_pgpass = os.path.expanduser('~') + "/.pgpass"

    line_pgpass = str(ip_host) + ":" + str(num_port) + ":*:" + str(user_name) + ":" + str(password)

    find = False
    if os.path.isfile(file_pgpass):
        text = readTextFile(file_pgpass)
        for line in text.split('\n'):
            if line_pgpass in line:
                find = True
                break

    if not find:
        appendTextFileCR(file_pgpass, line_pgpass)
        # Le fichier n'aime pas avoir plus de droit d'accès...
        os.chmod(file_pgpass, 0o600)

    return

########################################################################
# FONCTION createDatabase()                                            #
########################################################################
def createDatabase(database_name, user_name='postgres', password='postgres', ip_host='localhost', num_port='5432', schema_name=''):
    """
    # Rôle : créer une nouvelle base de données basée sur le template PostGIS
    # Paramètres en entrée :
    #   database_name : nom de la base de données à créer
    #   user_name : nom d'utilisateur du serveur PostgreSQL (par défaut : 'postgres')
    #   password : mot de passe du serveur PostgreSQL (par défaut : 'postgres')
    #   ip_host : adresse IP du serveur PostgreSQL (par défaut : 'localhost')
    #   num_port : numéro de port du serveur PostgreSQL (par défaut : '5432')
    #   schema_name : nom du schema à utiliser (par défaut : '')
    """

    connection = None
    connection = openConnection('postgres', user_name, password, ip_host, num_port, '')
    query = "CREATE DATABASE %s " % (database_name)
    query += "  WITH ENCODING = 'UTF8' "
    query += "  OWNER = postgres "
    query += "  TEMPLATE 'template_postgis' "
    query += "  CONNECTION LIMIT = -1;"
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM pg_database WHERE datname = '%s'" % (database_name))
    test = cursor.fetchall()
    if test == [] or test == None:
        try:
            connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = connection.cursor()
            cursor.execute(query)
            connection.commit()
            cursor.close()
            connection.close()
        except psycopg2.DatabaseError as err:
            if connection:
                connection.rollback()
                connection.close()
            e = "OS error: {0}".format(err)
            print(bold + red + "createDatabase() : Error %s - Impossible de créer la base de données %s" %(e, database_name) + endC, file=sys.stderr)
    return

########################################################################
# FONCTION dropDatabase()                                              #
########################################################################
def dropDatabase(database_name, user_name='postgres', password='postgres', ip_host='localhost', num_port='5432', schema_name=''):
    """
    # Rôle : supprimer une base de données existante
    # Paramètres en entrée :
    #   database_name : nom de la base de données à supprimer
    #   user_name : nom d'utilisateur du serveur PostgreSQL (par défaut : 'postgres')
    #   password : mot de passe du serveur PostgreSQL (par défaut : 'postgres')
    #   ip_host : adresse IP du serveur PostgreSQL (par défaut : 'localhost')
    #   num_port : numéro de port du serveur PostgreSQL (par défaut : '5432')
    #   schema_name : nom du schema à utiliser (par défaut : '')
    """

    connection = None
    connection = openConnection('postgres', user_name, password, ip_host, num_port, '')
    query = "DROP DATABASE IF EXISTS %s;" % (database_name)
    try:
        connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = connection.cursor()
        cursor.execute(query)
        connection.commit()
        cursor.close()
        connection.close()
    except psycopg2.DatabaseError as err:
        if connection:
            connection.rollback()
            connection.close()
        e = "OS error: {0}".format(err)
        print(bold + red + "dropDatabase() : Error %s - Impossible de supprimer la base de données %s" %(e, database_name) + endC, file=sys.stderr)
    return

########################################################################
# FONCTION createSchema()                                              #
########################################################################
def createSchema(connection, schema_name):
    """
    # Rôle : créer un nouveau schéma
    # Paramètres en entrée :
    #   connection : laissez tel quel, récupère les informations de connexion à la base de données
    #   schema_name : nom du schéma à créer
    """

    try:
        query = "CREATE SCHEMA IF NOT EXISTS %s AUTHORIZATION postgres;" % (schema_name)
        executeQuery(connection, query)
    except psycopg2.DatabaseError as err:
        if connection:
            connection.rollback()
        e = "OS error: {0}".format(err)
        print(bold + red + "createSchema() : Error %s - Impossible de créer le schéma %s" % (e, schema_name) + endC, file=sys.stderr)
        return -1
    return 0

########################################################################
# FONCTION dropSchema()                                                #
########################################################################
def dropSchema(connection, schema_name, cascade=True):
    """
    # Rôle : supprimer un schéma existant
    # Paramètres en entrée :
    #   connection : laissez tel quel, récupère les informations de connexion à la base de données
    #   schema_name : nom du schema à supprimer
    #   cascade : suppression des éléments dépendants du schéma
    """

    try:
        if cascade :
            query = "DROP SCHEMA IF EXISTS %s CASCADE;" % (schema_name)
        else:
            query = "DROP SCHEMA IF EXISTS %s;" % (schema_name)
        executeQuery(connection, query)
    except psycopg2.DatabaseError as err:
        if connection:
            connection.rollback()
        e = "OS error: {0}".format(err)
        print(bold + red + "dropSchema() : Error %s - Impossible de supprimer le schéma %s" % (e, schema_name) + endC, file=sys.stderr)
        return -1
    return 0

########################################################################
# FONCTION createTable()                                               #
########################################################################
def createTable(connection, table_name, columns_table_dico):
    """
    # Rôle : créer une nouvelle table
    # Paramètres en entrée :
    #   connection : laissez tel quel, récupère les informations de connexion à la base de données
    #   table_name : nom de la table à créer
    #   columns_table_dico : dictionnaire des noms de colonnes et du type de données associées (de la forme : [('column1', 'type1'), ('column2', 'type2'), ('column3', 'type3')])
    """

    try:
        dropTable(connection, table_name)
        cpt_column = 0
        query = "CREATE TABLE %s (" % (table_name)
        for column in columns_table_dico:
            name_column = column[0]
            type_column = column[1]
            query += name_column + " " + type_column
            if cpt_column == 0:
                query += " PRIMARY KEY, "
            else :
                query += ", "
            cpt_column += 1
        query = query[:-2]
        query += ");"
        executeQuery(connection, query)
    except psycopg2.DatabaseError as err:
        if connection:
            connection.rollback()
        e = "OS error: {0}".format(err)
        print(bold + red + "createTable() : Error %s - Impossible de créer la table %s" % (e, table_name) + endC, file=sys.stderr)
        return -1
    return 0

########################################################################
# FONCTION dropTable()                                                 #
########################################################################
def dropTable(connection, table_name, cascade=True):
    """
    # Rôle : supprimer une table existante
    # Paramètres en entrée :
    #   connection : laissez tel quel, récupère les informations de connexion à la base de données
    #   table_name : nom de la table à supprimer
    #   cascade : suppression des éléments dépendants de la table
    """

    try:
        if cascade :
            query = "DROP TABLE IF EXISTS %s CASCADE;" % (table_name)
        else:
            query = "DROP TABLE IF EXISTS %s;" % (table_name)
        executeQuery(connection, query)
    except psycopg2.DatabaseError as err:
        if connection:
            connection.rollback()
        e = "OS error: {0}".format(err)
        print(bold + red + "dropTable() : Error %s - Impossible de supprimer la table %s" % (e, table_name) + endC, file=sys.stderr)
        return -1
    return 0

########################################################################
# FONCTION fillTable()                                                 #
########################################################################
def fillTable(connection, table_name, columns_table_dico, data):
    """
    # Rôle : remplir une table
    # Paramètres en entrée :
    #   connection : laissez tel quel, récupère les informations de connexion à la base de données
    #   table_name : nom de la table à remplir
    #   columns_table_dico : dictionnaire des noms de colonnes et du type de données associées (de la forme : [('Id', 'INT'), ('Name', 'TEXT'), ('Price', 'INT')])
    #   data : données à insérer dans la table (de la forme : [(1, 'Audi', 52642),(2, 'Mercedes', 57127),(3, 'Skoda', 9000),(4, 'Volvo', 29000),(5, 'Bentley', 350000),(6, 'Citroen', 21000),(7, 'Hummer', 41400),(8, 'Volkswagen', 21600)])
    """

    try:
        cursor = connection.cursor()
        query = "INSERT INTO %s (" % (table_name)
        for column in columns_table_dico:
            name_column = column[0]
            query += name_column + ", "
        query = query[:-2]
        query += ") VALUES ("
        for column in columns_table_dico:
            query += "%s, "
        query = query[:-2]
        query += ");"
        cursor.executemany(query, data)
        connection.commit()
    except psycopg2.DatabaseError as err:
        if connection:
            connection.rollback()
        e = "OS error: {0}".format(err)
        print(bold + red + "fillTable() : Error %s - Impossible de remplir la table %s" % (e, table_name) + endC, file=sys.stderr)
        return -1
    return 0

########################################################################
# FONCTION renameTable()                                               #
########################################################################
def renameTable(connection, old_table_name, new_table_name):
    """
    # Rôle : renommer une table
    # Paramètres en entrée :
    #   connection : laissez tel quel, récupère les informations de connexion à la base de données
    #   old_table_name : ancien nom de la table (existant)
    #   new_table_name : nouveau nom à donnée à la table
    """

    try:
        query = "ALTER TABLE %s RENAME TO %s;" % (old_table_name, new_table_name)
        executeQuery(connection, query)
    except psycopg2.DatabaseError as err:
        if connection:
            connection.rollback()
        print(bold + red + "renameTable() : Error %s - Impossible de renommer la table %s" % (e, old_table_name) + endC, file=sys.stderr)
        return -1
    return 0

########################################################################
# FONCTION copyTable()                                                 #
########################################################################
def copyTable(connection, table_name_scr, table_name_dst):
    """
    # Rôle : copier une table
    # Paramètres en entrée :
    #   connection : laissez tel quel, récupère les informations de connexion à la base de données
    #   table_name_scr : nom de la table à copier
    #   table_name_dst : nom à donner pour la nouvelle table
    """

    try:
        query = "CREATE TABLE %s AS TABLE %s;" % (table_name_dst, table_name_scr)
        executeQuery(connection, query)
    except psycopg2.DatabaseError as err:
        if connection:
            connection.rollback()
        e = "OS error: {0}".format(err)
        print(bold + red + "copyTable() : Error %s - Impossible de copier la table %s" % (e, table_name_scr) + endC, file=sys.stderr)
        return -1
    return 0

########################################################################
# FONCTION dropColumn()                                                #
########################################################################
def dropColumn(connexion, tablename, columnname):
    """
    Rôle : supprime une colonne d'une table

    Paramètres :
        connexion : connexion à la base donnée et au schéma correspondant
        tablename : nom de la table correspondant aux segments de végétation
        columnname : nom de la colonne à supprimer
    """

    query = """
    ALTER TABLE %s DROP COLUMN IF EXISTS %s;
    """ %(tablename, columnname)

    # Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    return

########################################################################
# FONCTION renameColumn()                                              #
########################################################################
def renameColumn(connexion, tablename, columnname, new_columnname):
    """
    Rôle : renameColumn une colonne d'une table

    Paramètres :
        connexion : connexion à la base donnée et au schéma correspondant
        tablename : nom de la table correspondant aux segments de végétation
        columnname : nom de la colonne à renomer
        new_columnname : nouveau nom de la colonne
    """

    query = """
    ALTER TABLE %s RENAME COLUMN %s TO %s;
    """ %(tablename, columnname, new_columnname)

    # Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    return

########################################################################
# FONCTION addColumn()                                                 #
########################################################################
def addColumn(connexion, tablename, columnname, columntype, debug = 0):
    """
    Rôle : créé un attribut d'une table dans la db

    Paramètres :
        connexion : connexion à la base donnée et au schéma correspondant
        tablename : nom de la table correspondant aux segments de végétation
        attributname : nom de l'attribut ajouté
        columntype : type de l'attribut ex : float, varchar, int, etc ...
    """

    query = """
    ALTER TABLE %s ADD COLUMN IF NOT EXISTS %s %s;
    """ %(tablename, columnname, columntype)

    #Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    return

########################################################################
# FONCTION addUniqId()                                                 #
########################################################################
def addUniqId(connexion, tablename):
    """
    Rôle : créé un identifiant unique fid généré automatiquement

    Paramètres :
        connexion : connexion à la base donnée et au schéma correspondant
        tablename : nom de la table correspondant aux segments de végétation
    """

    query = """
    ALTER TABLE %s ADD COLUMN fid SERIAL PRIMARY KEY;
    """ %(tablename)

    #Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    return

########################################################################
# FONCTION addIndex()                                                  #
########################################################################
def addIndex(connexion, table_name, column_name="fid", name_index=""):
    """
    Rôle : créé un index sur une colonne de la table
    Paramètres :
        connexion : laisser tel quel, récupère les informations de connexion à la base
        table_name : nom de la table
        column_name : nom de la colonne
        name_index : nom de l'index
    """

    if name_index == "":
        name_index = "%s_%s_idx" % (table_name, column_name)
    query = """
    DROP INDEX IF EXISTS %s;
    CREATE INDEX IF NOT EXISTS %s ON %s USING BRIN (%s);
    """ % (name_index, name_index, table_name, column_name)
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    return

########################################################################
# FONCTION addSpatialIndex()                                           #
########################################################################
def addSpatialIndex(connexion, table_name, column_name="geom", name_index="", cluster=True):
    """
    Rôle : créé un index spatial sur une colonne de la table
    Paramètres :
        connexion : laisser tel quel, récupère les informations de connexion à la base
        table_name : nom de la table
        column_name : nom de la colonne
        name_index : nom de l'index
        cluster : réorganise le stockage des données (pour diminuer les temps d'accès en lecture)
    """

    if name_index == "":
        name_index = "%s_%s_gist" % (table_name, column_name)
    query = """
    DROP INDEX IF EXISTS %s;
    CREATE INDEX IF NOT EXISTS %s ON %s USING GIST (%s);
    """ % (name_index, name_index, table_name, column_name)
    if cluster:
        query += "    CLUSTER %s USING %s;" % (table_name, name_index)
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    return

########################################################################
# FONCTION addData()                                                   #
########################################################################
def addData(connection, table_name, data):
    """
    # Rôle : ajouter des données dans une table
    # Paramètres en entrée :
    #   connection : laissez tel quel, récupère les informations de connexion à la base de données
    #   table_name : nom de la table à traiter
    #   data : données à insérer dans la table (de la forme : (9, 'Renault', 15000))
    """

    try:
        query = "INSERT INTO %s VALUES %s;" % (table_name, data)
        executeQuery(connection, query)
    except psycopg2.DatabaseError as err:
        if connection:
            connection.rollback()
        e = "OS error: {0}".format(err)
        print(bold + red + "addData() : Error %s - Impossible d'ajouter la donnée %s à la table %s" % (e, str(data), table_name) + endC, file=sys.stderr)
        return -1
    return 0

########################################################################
# FONCTION deleteData()                                                #
########################################################################
def deleteData(connection, table_name, column_name, data_name):
    """
    # Rôle : supprimer des données d'une table selon condition
    # Paramètres en entrée :
    #   connection : laissez tel quel, récupère les informations de connexion à la base de données
    #   table_name : nom de la table à traiter
    #   column_name : nom de la colonne à traiter
    #   data_name : nom de la donnée à supprimer
    """

    try:
        query = "DELETE FROM %s WHERE %s = '%s';" % (table_name, column_name, data_name)
        executeQuery(connection, query)
    except psycopg2.DatabaseError as err:
        if connection:
            connection.rollback()
        e = "OS error: {0}".format(err)
        print(bold + red + "deleteData() : Error %s - Impossible de supprimer la donnée %s de la table %s" % (e, data_name, table_name) + endC, file=sys.stderr)
        return -1
    return 0

########################################################################
# FONCTION getData()                                                   #
########################################################################
def getData(connection, table_name, column_name, condition=''):
    """
    # Rôle : récupérer des données d'une colonne dans une table
    # Paramètres en entrée :
    #   connection : laissez tel quel, récupère les informations de connexion à la base de données
    #   table_name : nom de la table
    #   column_name : nom de la colonne à récupérer
    #   condition : condition des données à récupérer
    # Paramètre de retour :
    #   la liste des données d'une colonne d'une table
    """

    data_list = None
    try:
        cursor = connection.cursor()
        query = "SELECT %s FROM %s;" % (column_name, table_name)
        if condition != "":
            query = query[:-1] + " WHERE %s;" % condition
        cursor.execute(query)
        data_list = cursor.fetchall()
    except psycopg2.DatabaseError as err:
        if connection:
            connection.rollback()
        e = "OS error: {0}".format(err)
        print(bold + red + "getData() : Error %s - Impossible de récupérer les données de la table %s" % (e, table_name) + endC, file=sys.stderr)
    return data_list

########################################################################
# FONCTION updateData()                                                #
########################################################################
def updateData(connection, table_name, column_name, new_value, condition):
    """
    # Rôle : mettre à jour un champs de la table suivant condition
    # Paramètres en entrée :
    #   connection : laissez tel quel, récupère les informations de connexion à la base de données
    #   table_name : nom de la table à traiter
    #   column_name : nom de la colonne à traiter
    #   new_value : nouvelle valeur à attribuer
    #   condition : condition pour la mise à jour de la table
    """

    try:
        query = "UPDATE %s SET %s = '%s' WHERE %s;" % (table_name, column_name, new_value, condition)
        executeQuery(connection, query)
    except psycopg2.DatabaseError as err:
        if connection:
            connection.rollback()
        e = "OS error: {0}".format(err)
        print(bold + red + "updateData() : Error %s - Impossible de mettre à jour la table %s" % (e, table_name) + endC, file=sys.stderr)
        return -1
    return 0

########################################################################
# FONCTION importVectorByOgr2ogr()                                     #
########################################################################
def importVectorByOgr2ogr(database_name, vector_name, table_name, user_name='postgres', password='postgres', ip_host='localhost', num_port='5432', schema_name='public', epsg='2154', codage='UTF-8', geometry_type='GEOMETRY', geometry_name='geom', fid_name='fid', print_cmd=True):
    """
    # Rôle : importer des données vecteurs dans une base de données PostgreSQL (via ogr2ogr)
    # Paramètres en entrée :
    #   database_name : nom de la base de données
    #   vector_name : nom complet du fichier à importer
    #   table_name : nom à donner à la table
    #   user_name : nom d'utilisateur du serveur PostgreSQL (par défaut : 'postgres')
    #   password : mot de passe du serveur PostgreSQL (par défaut : 'postgres')
    #   ip_host : adresse IP du serveur PostgreSQL (par défaut : 'localhost')
    #   num_port : numéro de port du serveur PostgreSQL (par défaut : '5432')
    #   schema_name : nom du schema à utiliser (par défaut : 'public')
    #   epsg : code EPSG de la projection des données à importer (par défaut : '2154')
    #   codage : encodage de caractères du fichier à importer (par défaut : 'UTF-8')
    #   geometry_type : type de géométrie en entrée (POINT, LINESTRING, POLYGON...) (par défaut : 'GEOMETRY')
    #   geometry_name : nom du champ géométrie dans la table en sortie (par défaut : 'geom')
    #   fid_name : nom du champ de clé primaire qui sera créé dans la table en sortie (par défaut : 'fid')
    # Paramètre de retour :
    #   le nom de la table dans laquelle le fichier a été importé (modifié si ne respecte pas le regexp)
    """

    # Test de la validité du nom de la table (doit commencer par une lettre)
    regexp = "[A-Za-z]"
    if re.match(regexp, table_name[0]) is None:
        table_name = 't' + table_name

    # On efface la table si elle existe precedement
    connection = openConnection(database_name, user_name, password, ip_host, num_port, schema_name)
    dropTable(connection, table_name)
    closeConnection(connection)

    # Commande d'import avec ogr2ogr
    command = ""
    if codage != 'UTF-8':
        command += "PGCLIENTENCODING=%s " % (codage)
    #command += "PG_USE_COPY=YES ogr2ogr -append -a_srs 'EPSG:%s' -f 'PostgreSQL' PG:'host=%s port=%s dbname=%s user=%s password=%s' %s -nln %s.%s -nlt GEOMETRY -lco LAUNDER=yes -lco GEOMETRY_NAME=geom" % (epsg, ip_host, num_port, database_name, user_name, password, vector_name, schema_name, table_name)
    command += "ogr2ogr -overwrite -a_srs 'EPSG:%s' -f PostgreSQL PG:'host=%s port=%s dbname=%s user=%s password=%s' %s -nln %s.%s -nlt %s -lco GEOMETRY_NAME=%s -lco FID=%s --config PG_USE_COPY YES" % (epsg, ip_host, num_port, database_name, user_name, password, vector_name, schema_name, table_name, geometry_type, geometry_name, fid_name)

    try:
        if debug>=3 and print_cmd:
            print(command)
        os.system(command)

    except Exception as err:
        e = "OS error: {0}".format(err)
        print(bold + red + "importVectorByOgr2ogr() : Error %s - Impossible d'importer les données de '%s'" % (e, vector_name) + endC, file=sys.stderr)
        return -1

    return table_name

########################################################################
# FONCTION exportVectorByOgr2ogr()                                     #
########################################################################
def exportVectorByOgr2ogr(database_name, vector_name, table_name, user_name='postgres', password='postgres', ip_host='localhost', num_port='5432', schema_name='public', format_type='ESRI Shapefile', ogr2ogr_more_parameters='', print_cmd=True):
    """
    # Rôle : exporter une table d'une base de données vers un fichier vecteur (via ogr2ogr)
    # Paramètres en entrée :
    #   database_name : nom de la base de données
    #   vector_name : nom du fichier (.csv) complet correspondant à la table exportée
    #   table_name : nom de la table contenant les données à exporter
    #   user_name : nom d'utilisateur du serveur PostgreSQL (par défaut : 'postgres')
    #   password : mot de passe du serveur PostgreSQL (par défaut : 'postgres')
    #   ip_host : adresse IP du serveur PostgreSQL (par défaut : 'localhost')
    #   num_port : numéro de port du serveur PostgreSQL (par défaut : '5432')
    #   schema_name : nom du schema à utiliser (par défaut : 'public')
    #   format_type : format d'export des données (par défaut : 'ESRI Shapefile')
    """

    # Commande d'export avec ogr2ogr
    command = "ogr2ogr -f '%s' %s PG:'host=%s port=%s dbname=%s user=%s password=%s' -sql 'SELECT * FROM %s.%s'" % (format_type, vector_name, ip_host, num_port, database_name, user_name, password, schema_name, table_name)
    if ogr2ogr_more_parameters != '':
        command += " %s" % ogr2ogr_more_parameters

    try:
        if debug>=3 and print_cmd:
            print(command)
        os.system(command)

    except Exception as err:
        e = "OS error: {0}".format(err)
        print(bold + red + "exportVectorByOgr2ogr() : Error %s - Impossible d'exporter la table '%s'" % (e, table_name) + endC, file=sys.stderr)
        return -1

    return 0

########################################################################
# FONCTION importShape()                                               #
########################################################################
def importShape(database_name, vector_name, table_name, user_name='postgres', password='postgres', ip_host='localhost', num_port='5432', schema_name='public', epsg='2154', codage='utf-8'):
    """
    # Rôle : importer un vecteur dans une base de données (via shp2pgsql : https://postgis.net/docs/using_postgis_dbmanagement.html#shp2pgsql_usage)
    # Paramètres en entrée :
    #   database_name : nom de la base de données
    #   vector_name : nom du fichier vecteur à importer
    #   table_name : nom à donner à la table où le shape sera importé
    #   user_name : nom d'utilisateur du serveur PostgreSQL (par défaut : 'postgres')
    #   password : mot de passe du serveur PostgreSQL (par défaut : 'postgres')
    #   ip_host : adresse IP du serveur PostgreSQL (par défaut : 'localhost')
    #   num_port : numéro de port du serveur PostgreSQL (par défaut : '5432')
    #   schema_name : nom du schema à utiliser (par défaut : 'public')
    #   epsg : code EPSG du système de coordonnées du fichier shape à importer (par défaut : '2154')
    #   codage : encodage de caractères du fichier shape à importer (par défaut : 'utf-8')
    # Paramètre de retour :
    #   le nom de la table dans laquelle le fichier a été importé (modifié si ne respecte pas le regexp)
    """

    # Intégrer le mot de passe dans le fichier 'pgpass' si ligne n'existe pas déjà
    checkPassword(user_name=user_name, password=password, ip_host=ip_host, num_port=num_port)

    # Test de la validité du nom de la table (doit commencer par une lettre)
    regexp = "[A-Za-z]"
    if re.match(regexp, table_name[0]) is None:
        table_name = 't' + table_name

    # Commande
    command = "shp2pgsql -D -I -d -s '%s' -W %s %s %s.%s" % (epsg, codage, vector_name, schema_name, table_name)
    command += " | psql -d %s -h %s -p %s -U %s" % (database_name, ip_host, num_port, user_name)

    try:
        if debug>=3:
            print(command)
        os.system(command)
    except Exception as err:
        e = "OS error: {0}".format(err)
        print(bold + red + "importShape() : Error %s - Impossible d'importer les données de '%s'" % (e, vector_name) + endC, file=sys.stderr)
        return -1

    return table_name

########################################################################
# FONCTION exportShape()                                               #
########################################################################
def exportShape(database_name, vector_name, table_name, user_name='postgres', password='postgres', ip_host='localhost', num_port='5432', schema_name='public'):
    """
    # Rôle : exporter un vecteur d'une base de données (via shp2pgsql : http://bostongis.com/pgsql2shp_shp2pgsql_quickguide.bqg)
    # Paramètres en entrée :
    #   database_name : nom de la base de données
    #   vector_name : nom du fichier vecteur qui sera exporté
    #   table_name : nom de la table contenant les données à exporter
    #   user_name : nom d'utilisateur du serveur PostgreSQL (par défaut : 'postgres')
    #   password : mot de passe du serveur PostgreSQL (par défaut : 'postgres')
    #   ip_host : adresse IP du serveur PostgreSQL (par défaut : 'localhost')
    #   num_port : numéro de port du serveur PostgreSQL (par défaut : '5432')
    #   schema_name : nom du schema à utiliser (par défaut : 'public')
    """

    command = "pgsql2shp -h %s -p %s -u %s -P %s -f %s -g 'geom' %s %s.%s" % (ip_host, num_port, user_name, password, vector_name, database_name, schema_name, table_name)

    try:
        if debug>=3:
            print(command)
        os.system(command)
    except Exception as err:
        e = "OS error: {0}".format(err)
        print(bold + red + "exportShape() : Error %s - Impossible d'exporter la table '%s'" % (e, table_name) + endC, file=sys.stderr)
        return -1

    return 0

########################################################################
# FONCTION importRaster()                                              #
########################################################################
def importRaster(database_name, file_name, band_number, table_name, user_name='postgres', password='postgres', ip_host='localhost', num_port='5432', schema_name='public', epsg='2154', nodata_value='0', tile_size='auto'):
    """
    # Rôle : importer un raster dans une base de données (via raster2pgsql : http://postgis.net/docs/manual-dev/using_raster_dataman.html#RT_Raster_Loader)
    # Paramètres en entrée :
    #   database_name : nom de la base de données
    #   file_name : nom du fichier raster à importer
    #   band_number : Numero de bande du fichier image d'entree à utiliser
    #   table_name : nom à donner à la table où le raster sera importé
    #   user_name : nom d'utilisateur du serveur PostgreSQL (par défaut : 'postgres')
    #   password : mot de passe du serveur PostgreSQL (par défaut : 'postgres')
    #   ip_host : adresse IP du serveur PostgreSQL (par défaut : 'localhost')
    #   num_port : numéro de port du serveur PostgreSQL (par défaut : '5432')
    #   schema_name : nom du schema à utiliser (par défaut : 'public')
    #   epsg : code EPSG du système de coordonnées du fichier raster à importer (par défaut : '2154')
    #   nodata_value : valeur NoData du fichier raster à importer (par défaut : '0')
    #   tile_size : taille des tuiles générés lors de l'import, au format "LARGEURxHAUTEUR" sans espace (par défaut : 'auto')
    # Paramètre de retour :
    #   le nom de la table dans laquelle le fichier a été importé (modifié si ne respecte pas le regexp)
    """

    # Intégrer le mot de passe dans le fichier 'pgpass' si ligne n'existe pas déjà
    checkPassword(user_name=user_name, password=password, ip_host=ip_host, num_port=num_port)

    # Test de la validité du nom de la table (doit commencer par une lettre)
    regexp = "[A-Za-z]"
    if re.match(regexp, table_name[0]) is None:
        table_name = 't' + table_name

    # Commande
    command = "raster2pgsql -d -s %s -b %s -t %s -N %s -f rast -I -M -Y %s %s.%s" % (str(epsg), str(band_number), tile_size, str(nodata_value), file_name, schema_name, table_name)
    command += " | psql -X -d %s -h %s -p %s -U %s" % (database_name, ip_host, str(num_port), user_name)
    try:
        if debug>=1:
            print(command)
        os.system(command)
    except Exception as err:
        e = "OS error: {0}".format(err)
        print(bold + red + "importRaster() : Error %s - Impossible d'importer les données de '%s'" % (e, file_name) + endC, file=sys.stderr)
        return -1

    return table_name

########################################################################
# FONCTION exportRaster()                                              #
########################################################################
def exportRaster(database_name, file_name, table_name, user_name='postgres', password='postgres', ip_host='localhost', num_port='5432', schema_name='public'):
    """
    !!! ATTENTION en cours de developpement fonction à terminer apres avoir trouver la fonction pgsql2raster et ses parametres !!!
    # Rôle : exporter un raster d'une base de données(via pgsql2raster : www.cef-cfr.ca/uploads/Membres/WKTRasterSpecifications0.7.pdf)
    # Paramètres en entrée :
    #   database_name : nom de la base de données
    #   file_name : nom du fichier raster qui sera exporté
    #   table_name : nom de la table contenant les données à exporter
    #   user_name : nom d'utilisateur du serveur PostgreSQL (par défaut : 'postgres')
    #   password : mot de passe du serveur PostgreSQL (par défaut : 'postgres')
    #   ip_host : adresse IP du serveur PostgreSQL (par défaut : 'localhost')
    #   num_port : numéro de port du serveur PostgreSQL (par défaut : '5432')
    #   schema_name : nom du schema à utiliser (par défaut : 'public')
    """

    command = "pgsql2raster -f %s -h %s -p %s -u %s -r raster %s.%s" % (file_name, ip_host, password, user_name, schema_name, table_name)
    #"‘SELECT ST_Accum(ST_Band(raster,1)) FROM coverandtemp WHERE prov=‘BC’ GROUP BY prov’"

    try:
        if debug>=3:
            print(command)
        os.system(command)
    except Exception as err:
        e = "OS error: {0}".format(err)
        print(bold + red + "exportRaster() : Error %s - Impossible d'exporter la table '%s'" % (e, table_name) + endC, file=sys.stderr)
        return -1

    return 0

########################################################################
# FONCTION importDataCSV()                                             #
########################################################################
def importDataCSV(connection, csv_name, table_name, columns_table_dico, delimiter=";"):
    """
    # Rôle : importer des données .csv dans une base de données
    # Paramètres en entrée :
    #   connection : laissez tel quel, récupère les informations de connexion à la base de données
    #   csv_name : nom du fichier (.csv) complet à importer
    #   table_name : nom à donner à la table où le csv sera importé
    #   columns_table_dico : dictionnaire des noms de colonnes et du type de données associées [('column1', 'type1'), ('column2', 'type2'), ('column3', 'type3')])
    #   delimiter : séparateur de texte du fichier .csv (par défaut : ';')
    """

    cursor = connection.cursor()
    createTable(connection, table_name, columns_table_dico)
    f = open(csv_name, 'r')
    cursor.copy_from(f, table_name, sep=delimiter)
    f.close()
    connection.commit()
    return

########################################################################
# FONCTION exportDataCSV()                                             #
########################################################################
def exportDataCSV(connection, table_name, csv_name, delimiter=";"):
    """
    # Rôle : exporter des données d'une base de données en .csv
    # Paramètres en entrée :
    #   connection : laissez tel quel, récupère les informations de connexion à la base de données
    #   table_name : nom de la table contenant les données à exporter
    #   csv_name : nom du fichier (.csv) complet qui sera exporté
    #   delimiter : séparateur de texte du fichier .csv (par défaut : ';')
    """

    columns_list = getAllColumns(connection, table_name, print_result=False)
    data_read = readTable(connection, table_name)
    with open(csv_name, 'w') as f:
        writer = csv.writer(f, delimiter=delimiter)
        columns_tuple = ()
        for column in columns_list:
            columns_tuple += (column,)
        writer.writerow(columns_tuple)
        for row in data_read:
            writer.writerow(row)
    return

########################################################################
# FONCTION readTable()                                                 #
########################################################################
def readTable(connection, table_name):
    """
    # Rôle : lire une table
    # Paramètres en entrée :
    #   connection : laissez tel quel, récupère les informations de connexion à la base de données
    #   table_name : nom de la table où récupérer les données à lire
    # Paramètre de retour :
    #   les données de la table
    """

    data_read = None
    try:
        query = "SELECT * FROM %s;" % (table_name)
        cursor = connection.cursor()
        cursor.execute(query)
        data_read = cursor.fetchall()
    except psycopg2.DatabaseError as err:
        e = "OS error: {0}".format(err)
        print(bold + red + "readTable() : Error %s - Impossible de lire la table %s" % (e, table_name) + endC, file=sys.stderr)
        data_read = None
    return data_read

########################################################################
# FONCTION postTable()                                                 #
########################################################################
def postTable(connection, table_name):
    """
    # Rôle : afficher le contenu d'une table dans la console
    # Paramètres en entrée :
    #   connection : laissez tel quel, récupère les informations de connexion à la base de données
    #   table_name : nom de la table où récupérer les données à afficher
    """

    data_read = readTable(connection, table_name)
    for row in data_read:
        print(row)
    return

########################################################################
# FONCTION createExtension()                                           #
########################################################################
def createExtension(connexion, extension_name, debug = 0):
    """
    # Rôle : créer un extension dans la BD
    # Paramètres :
    #   connexion : paramètre unique de connexion à la base de données pgsql
    #   extension_name : nom d'utilisateur du serveur PostgreSQL (par défaut : 'postgres')
    """
    query = """
    CREATE EXTENSION IF NOT EXISTS %s WITH SCHEMA public;
    """ %(extension_name)
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    return

########################################################################
# FONCTION dataBaseExist()                                             #
########################################################################
def dataBaseExist(connexion, dbname):
    """
    # Rôle : renvoie si la base de données existe déjà
    # Paramètre :
    #    connexion : laisser tel quel, récupère les informations de connexion à la base
    #    dbname : nom de la base de données
    # Sortie :
    #    True ou False en fonction de l'existence de la BD
    """
    exist = False

    query = """ SELECT 1 FROM pg_database WHERE datname = '%s';""" %(dbname)

    cursor = connexion.cursor()
    cursor.execute(query)
    result = cursor.fetchone()[0]

    if result == 1 :
        exist = True

    return exist

########################################################################
# FONCTION schemaExist()                                               #
########################################################################
def schemaExist(connexion, schema_name):
    """
    # Rôle : renvoie si le schema existe déjà
    # Paramètre :
    #     connexion : laisser tel quel, récupère les informations de connexion à la base
    #     schema_name : nom du schema
    # Sortie :
    #    True ou False en fonction de l'existence du schéma dans la db
    """
    exist = False
    li_schema = getAllSchemas(connexion)

    if schema_name in li_schema:
        exist = True

    return exist

########################################################################
# FONCTION getAllDatabases()                                           #
########################################################################
def getAllDatabases(user_name='postgres', password='postgres', ip_host='localhost', num_port='5432', schema_name='', print_result=True):
    """
    # Rôle : lister les bases de données d'un serveur
    # Paramètres en entrée :
    #   user_name : nom d'utilisateur du serveur PostgreSQL (par défaut : 'postgres')
    #   password : mot de passe du serveur PostgreSQL (par défaut : 'postgres')
    #   ip_host : adresse IP du serveur PostgreSQL (par défaut : 'localhost')
    #   num_port : numéro de port du serveur PostgreSQL (par défaut : '5432')
    #   schema_name : nom du schema à utiliser (par défaut : '')
    #   print_result : afficher le résultat directement dans la console (par défaut, True)
    # Paramètre de retour :
    #   la liste des bases de données
    """

    connection = psycopg2.connect(dbname='postgres', user=user_name, password=password, host=ip_host, port=num_port)
    cursor = connection.cursor()
    query = "SELECT datname FROM pg_catalog.pg_database;"
    cursor.execute(query)
    databases_raw_list = cursor.fetchall()
    closeConnection(connection)

    if print_result:
        print(bold + "Liste des bases de données du serveur '%s' :" % (ip_host) + endC)
    databases_list = []
    for row in sorted(databases_raw_list):
        if print_result:
            print("    %s" % (row))
        databases_list.append(row[0])

    return databases_list

########################################################################
# FONCTION getAllSchemas()                                             #
########################################################################
def getAllSchemas(connection, print_result=True):
    """
    # Rôle : lister les schémas d'une base de données
    # Paramètres en entrée :
    #   connection : laissez tel quel, récupère les informations de connexion à la base de données
    #   print_result : afficher le résultat directement dans la console (par défaut, True)
    # Paramètre de retour :
    #   la liste des schémas de la base de données
    """

    cursor = connection.cursor()
    query = "SELECT nspname FROM pg_catalog.pg_namespace;"
    cursor.execute(query)
    schemas_raw_list = cursor.fetchall()

    if print_result:
        print(bold + "Liste des schémas de la base de données de connexion" + endC)
    schemas_list = []
    for row in sorted(schemas_raw_list):
        if print_result:
            print("    %s" % (row))
        schemas_list.append(row[0])

    return schemas_list

########################################################################
# FONCTION getAllTables()                                              #
########################################################################
def getAllTables(connection, schema_name, print_result=True):
    """
    # Rôle : lister les tables d'un schéma
    # Paramètres en entrée :
    #   connection : laissez tel quel, récupère les informations de connexion à la base de données
    #   schema_name : nom du schéma dans lequel lister les tables existantes
    #   print_result : afficher le résultat directement dans la console (par défaut, True)
    # Paramètre de retour :
    #   la liste des tables du schéma
    """

    cursor = connection.cursor()
    query = "SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = '%s';" % (schema_name)
    cursor.execute(query)
    tables_raw_list = cursor.fetchall()

    if print_result:
        print(bold + "Liste des tables du schéma '%s' :" % (schema_name) + endC)
    tables_list = []
    for row in sorted(tables_raw_list):
        if print_result:
            print("    %s" % (row))
        tables_list.append(row[0])

    return tables_list

########################################################################
# FONCTION getAllColumns()                                             #
########################################################################
def getAllColumns(connection, table_name, print_result=True):
    """
    # Rôle : lister les colonnes d'une table
    # Paramètres en entrée :
    #   connection : laissez tel quel, récupère les informations de connexion à la base de données
    #   table_name : nom de la table dans laquelle afficher les colonnes
    #   print_result : afficher le résultat directement dans la console (par défaut, True)
    # Paramètre de retour :
    #   la liste des colonnes de la table
    """

    cursor = connection.cursor()
    query = "SELECT attname FROM pg_attribute WHERE attrelid = '%s'::regclass AND attnum > 0 AND NOT attisdropped ORDER BY attnum;" % (table_name)
    cursor.execute(query)
    columns_raw_list = cursor.fetchall()

    if print_result:
        print(bold + "Liste des colonnes de la table '%s' :" % (table_name) + endC)
    columns_list = []
    for row in sorted(columns_raw_list):
        if print_result:
            print("    %s" % (row))
        columns_list.append(row[0])

    return columns_list

########################################################################
# FONCTION versionPostgreSQL()                                         #
########################################################################
def versionPostgreSQL(database_name='postgres', user_name='postgres', password='postgres', ip_host='localhost', num_port='5432', schema_name=''):
    """
    # Rôle : afficher la version de PostgreSQL
    # Paramètres en entrée :
    #   database_name : nom de la base de données
    #   user_name : nom d'utilisateur du serveur PostgreSQL (par défaut : 'postgres')
    #   password : mot de passe du serveur PostgreSQL (par défaut : 'postgres')
    #   ip_host : adresse IP du serveur PostgreSQL (par défaut : 'localhost')
    #   num_port : numéro de port du serveur PostgreSQL (par défaut : '5432')
    #   schema_name : nom du schema à utiliser (par défaut : '')
    # Paramètre de retour :
    #   la version de PostgresSQL
    """

    connection = openConnection(database_name, user_name, password, ip_host, num_port)
    cursor = connection.cursor()
    cursor.execute("SELECT version();")
    postgresql_version = cursor.fetchone()
    closeConnection(connection)
    if debug >= 3:
        print(bold + "Version de PostgreSQL : " + endC + str(postgresql_version))
    return postgresql_version

########################################################################
# FONCTION versionPostGIS()                                            #
########################################################################
def versionPostGIS(database_name='template_postgis', user_name='postgres', password='postgres', ip_host='localhost', num_port='5432', schema_name=''):
    """
    # Rôle : afficher la version de PostGIS
    # Paramètres en entrée :
    #   database_name : nom de la base de données
    #   user_name : nom d'utilisateur du serveur PostgreSQL (par défaut : 'postgres')
    #   password : mot de passe du serveur PostgreSQL (par défaut : 'postgres')
    #   ip_host : adresse IP du serveur PostgreSQL (par défaut : 'localhost')
    #   num_port : numéro de port du serveur PostgreSQL (par défaut : '5432')
    #   schema_name : nom du schema à utiliser (par défaut : '')
    # Paramètre de retour :
    #   la version de PostGIS
    """

    connection = openConnection(database_name, user_name, password, ip_host, num_port)
    cursor = connection.cursor()
    cursor.execute("SELECT PostGIS_Full_Version();")
    postgis_version = cursor.fetchone()
    closeConnection(connection)
    if debug >= 3:
        print(bold + "Version de PostGIS : " + endC + str(postgis_version))
    return postgis_version

######################################################################## Requêtes SQL spécifiques pour traitements particuliers (correction topologique, découpage polygones par lignes...)

########################################################################
# FONCTION topologyCorrections()                                       #
########################################################################
def topologyCorrections(connection, table_name, geom_field='geom'):
    """
    # Rôle : correction des erreurs topologiques
    # Paramètres en entrée :
    #   connection : récupère les informations de connexion à la base de données
    #   table_name : nom de la table à traiter
    #   geom_field : nom du champ de géométrie (par défaut, 'geom')
    """

    try:
        query = "UPDATE %s SET %s = ST_CollectionExtract(ST_ForceCollection(ST_MakeValid(%s)),3) WHERE NOT ST_IsValid(%s);" % (table_name, geom_field, geom_field, geom_field)
        executeQuery(connection, query)
    except psycopg2.DatabaseError as err:
        if connection:
            connection.rollback()
        e = "OS error: {0}".format(err)
        print(bold + red + "topologyCorrections() : Error %s - Impossible de corriger les erreurs topologiques de la table %s" % (e, table_name) + endC, file=sys.stderr)
        return -1
    return 0

########################################################################
# FONCTION cutPolygonesByLines()                                       #
########################################################################
def cutPolygonesByLines(connection, input_polygones_table, input_lines_table, output_polygones_table, geom_field='geom'):
    """
    # Rôle : découpage de (multi)polygones par des (multi)lignes
    # Paramètres en entrée :
    #   connection : récupère les informations de connexion à la base de données
    #   input_polygones_table : nom de la table polygones à découper
    #   input_lines_table : nom de la table lignes de découpe
    #   output_polygones_table : nom de la table polygones découpés
    #   geom_field : nom du champ de géométrie (par défaut, 'geom')
    """

    # Récupération des champs de la table polygones
    fields_list = getAllColumns(connection, input_polygones_table, print_result=False)
    fields_txt = ""
    for field in fields_list:
        if field != geom_field:
            fields_txt += "g.%s, " % field
    fields_txt = fields_txt[:-2]

    try:
        query = "DROP TABLE IF EXISTS %s;\n" % output_polygones_table
        query += "CREATE TABLE %s AS\n" % output_polygones_table
        query += "    SELECT %s, (ST_DUMP(ST_CollectionExtract(ST_Split(g.%s, ST_LineMerge(ST_Collect(l.%s)))))).geom AS %s\n" % (fields_txt, geom_field, geom_field, geom_field)
        query += "    FROM %s AS g, %s AS l\n" % (input_polygones_table, input_lines_table)
        query += "    GROUP BY %s;\n" % fields_txt
        print(query)
        executeQuery(connection, query)
    except psycopg2.DatabaseError as err:
        if connection:
            connection.rollback()
        e = "OS error: {0}".format(err)
        print(bold + red + "cutPolygonesByLines() : Error %s - Impossible de découper la table '%s' par la table '%s'" % (e, input_polygones_table, input_lines_table) + endC, file=sys.stderr)
        return -1
    return 0

########################################################################
# FONCTION cutPolygonesByPolygones()                                   #
########################################################################
def cutPolygonesByPolygones(connection, input_polygones_table, input_polygones_cutting_table, output_polygones_table, geom_field='geom', nb_cpus:int=30):
    """
    # Rôle : découpage de (multi)polygones par des (multi)polygones
    # Paramètres en entrée :
    #   connection : récupère les informations de connexion à la base de données
    #   input_polygones_table : nom de la table polygones à découper
    #   input_polygones_cutting_table : nom de la table de polygones de découpe
    #   output_polygones_table : nom de la table polygones découpés
    #   geom_field : nom du champ de géométrie (par défaut, 'geom')
    """

    # Récupération des champs de la table polygones
    fields_list = getAllColumns(connection, input_polygones_table, print_result=False)
    fields_txt = ""
    for field in fields_list:
        if field != geom_field:
            fields_txt += "p.%s, " % field
    fields_txt = fields_txt[:-2]

    try:
        query = "DROP TABLE IF EXISTS %s;\n" % output_polygones_table
        # création d'index spatiaux par défaut
        query += "CREATE INDEX ON %s USING GIST (%s);\n" % (input_polygones_table, geom_field)
        query += "CREATE INDEX ON %s USING GIST (%s);\n" % (input_polygones_cutting_table, geom_field)
        # définition de paramètres de parallélisation pour encourager le planner a l'envisager
        query += "SET max_parallel_workers_per_gather = %s;" % nb_cpus
        query += "SET parallel_setup_cost = 0;"
        query += "SET parallel_tuple_cost = 0;"
        # requete utilisant au maximum les index spatiaux
        query += "CREATE TABLE %s AS\n" % output_polygones_table
        query += "  WITH candidates AS ("
        query += "      SELECT %s, p.%s AS geom1, p2.%s AS geom2" % (fields_txt, geom_field, geom_field)
        query += "      FROM %s p" % input_polygones_table
        query += "      JOIN %s p2" % input_polygones_cutting_table
        query += "      ON p.%s && p2.%s" % (geom_field, geom_field)
        query += "      AND ST_Intersects(p.%s, p2.%s))" % (geom_field, geom_field)
        query += "  SELECT *, ST_Intersection(c.geom1, c.geom2) AS %s" % geom_field
        query += "  FROM candidates c;"
        print(query)
        executeQuery(connection, query)

    except psycopg2.DatabaseError as err:
        if connection:
            connection.rollback()
        e = "OS error: {0}".format(err)
        print(bold + red + "cutPolygonesByPolygones() : Error %s - Impossible de découper la table '%s' par la table '%s'" % (e, input_polygones_table, input_polygones_cutting_table) + endC, file=sys.stderr)
        return -1
    return 0

########################################################################
# FONCTION removeOverlaps()                                            #
########################################################################
def removeOverlaps(connection, table_name, fid_field="fid", geom_field="geom", min_area=0):
    """
    # Rôle : suppression des recouvrements
    # Doc : https://gist.github.com/Robinini/3395c7f59c749256563b4e082a00d4db
    # Paramètres en entrée :
    #   connection : récupère les informations de connexion à la base de données
    #   table_name : nom de la table à traiter
    #   id_field : champ d'identifiant unique (par défaut, "fid")
    #   geom_field : champ de géométrie (par défaut, "geom")
    #   min_area : taille minimale des polygones qui seront conservés pendant les traitements (par défaut : 0, tous les polygones seront conservés)
    """

    try:

        query = """
        -- Optimisation spatiale
        CREATE INDEX IF NOT EXISTS %s_%s_idx ON %s USING BRIN (%s);
        CREATE INDEX IF NOT EXISTS %s_%s_gist ON %s USING GIST (%s);
        CLUSTER %s USING %s_%s_gist;
        """ % (table_name, fid_field, table_name, fid_field, table_name, geom_field, table_name, geom_field, table_name, table_name, geom_field)

        if debug >= 3:
            print(query)
        executeQuery(connection, query)

        query = """
        -- Step 1/3: Remove Overlaps
        -- Firstly, overlapping geometries are removed. The fid column is used here to set a priority, but other columns or row sequences could be used.
        WITH overlap_removal AS (
            SELECT a.%s, ST_Union(b.%s) AS %s
            FROM %s AS a, %s AS b
            WHERE ST_Intersects(a.%s, b.%s) AND b.%s > a.%s
            GROUP BY a.%s)
        UPDATE %s SET %s =
            CASE
                WHEN overlap_removal.%s IS NOT NULL THEN ST_CollectionExtract(ST_Difference(%s.%s, overlap_removal.%s), 3)
                ELSE %s.%s
            END
        FROM overlap_removal
        WHERE %s.%s = overlap_removal.%s;
        DELETE FROM %s WHERE ST_Area(%s) <= %s;
        """ % (fid_field, geom_field, geom_field, table_name, table_name, geom_field, geom_field, fid_field, fid_field, fid_field,
            table_name, geom_field, fid_field, table_name, geom_field, geom_field, table_name, geom_field, table_name, fid_field, fid_field,
            table_name, geom_field, min_area)

        if debug >= 3:
            print(query)
        executeQuery(connection, query)

        query = """
        -- Optimisation spatiale
        DROP INDEX IF EXISTS %s_%s_idx;
        DROP INDEX IF EXISTS %s_%s_gist;
        CREATE INDEX IF NOT EXISTS %s_%s_idx ON %s USING BRIN (%s);
        CREATE INDEX IF NOT EXISTS %s_%s_gist ON %s USING GIST (%s);
        CLUSTER %s USING %s_%s_gist;
        """ % (table_name, fid_field, table_name, geom_field, table_name, fid_field, table_name, fid_field, table_name, geom_field, table_name, geom_field, table_name, table_name, geom_field)

        if debug >= 3:
            print(query)
        executeQuery(connection, query)

        query = """
        -- Step 2/3: Fill Enclosed Holes
        -- Secondly, the (enclosed) holes are filled by creating the hole geometry and merging with the neighbouring geometry sharing the longest touching border.
        WITH
            poly_union AS (
                SELECT ST_Buffer(ST_Buffer((ST_Dump(ST_Union(%s.%s))).geom, 1, 'join=mitre'), -1, 'join=mitre') AS %s
                FROM %s),
            rings AS (
                SELECT ST_DumpRings(poly_union.%s) AS DUMP
                FROM poly_union),
            inners AS (
                SELECT ROW_NUMBER() OVER () AS %s, (DUMP).geom AS %s
                FROM rings
                WHERE (DUMP).path[1] > 0),
            best_match AS (
                SELECT DISTINCT ON (inners.%s) inners.%s AS inner_id, %s.%s AS %s, ST_Length(ST_Intersection(inners.%s, %s.%s)) AS len, inners.%s AS %s
                FROM inners, %s
                WHERE ST_Intersects(inners.%s, %s.%s)
                ORDER BY inners.%s, len DESC),
            inner_addition AS (
                SELECT %s AS %s, ST_Union(%s) AS %s
                FROM best_match
                GROUP BY %s)
        UPDATE %s SET %s =
            CASE
                WHEN inner_addition.%s IS NOT NULL THEN ST_Union(%s.%s, inner_addition.%s)
                ELSE %s.%s
            END
        FROM inner_addition
        WHERE %s.%s = inner_addition.%s;
        DELETE FROM %s WHERE ST_Area(%s) = 0;
        """ % (table_name, geom_field, geom_field, table_name,
            geom_field,
            fid_field, geom_field,
            fid_field, fid_field, table_name, fid_field, fid_field, geom_field, table_name, geom_field, geom_field, geom_field, table_name, geom_field, table_name, geom_field, fid_field,
            fid_field, fid_field, geom_field, geom_field, fid_field,
            table_name, geom_field, fid_field, table_name, geom_field, geom_field, table_name, geom_field, table_name, fid_field, fid_field,
            table_name, geom_field)

        if debug >= 3:
            print(query)
        executeQuery(connection, query)

        query = """
        -- Optimisation spatiale
        DROP INDEX IF EXISTS %s_%s_idx;
        DROP INDEX IF EXISTS %s_%s_gist;
        CREATE INDEX IF NOT EXISTS %s_%s_idx ON %s USING BRIN (%s);
        CREATE INDEX IF NOT EXISTS %s_%s_gist ON %s USING GIST (%s);
        CLUSTER %s USING %s_%s_gist;
        """ % (table_name, fid_field, table_name, geom_field, table_name, fid_field, table_name, fid_field, table_name, geom_field, table_name, geom_field, table_name, table_name, geom_field)

        if debug >= 3:
            print(query)
        executeQuery(connection, query)

        query = """
        -- Step 3/3: Tidy Geometry
        -- Lastly, in case of geometry imperfections or artefacts along the fill joins, the geometry is tided using a positive and negative buffer.
        UPDATE %s SET %s = ST_Buffer(ST_Buffer(%s, 1, 'join=mitre'), -1, 'join=mitre');
        DELETE FROM %s WHERE ST_Area(%s) = 0;
        """ % (table_name, geom_field, geom_field, table_name, geom_field)

        if debug >= 3:
            print(query)
        executeQuery(connection, query)

    except psycopg2.DatabaseError as err:
        if connection:
            connection.rollback()
        e = "OS error: {0}".format(err)
        print(bold + red + "removeOverlaps() : Error %s - Impossible de supprimer les recouvrements de la table %s" % (e, table_name) + endC, file=sys.stderr)
        return -1

    return 0

########################################################################
# FONCTION coverageSimplify()                                          #
########################################################################
def coverageSimplify(connection, table_name_input, table_name_output, field_list=[], geom_field="geom", tolerance=1):
    """
    !!! ATTENTION en cours de développement : peut supprimer des entités (transformées en trou) ou en ajouter (issues de trou) !!!
    # Rôle : simplification des géométries en conservant les frontières entre polygones
    # Doc : https://trac.osgeo.org/postgis/wiki/UsersWikiSimplifyPreserveTopology
    # Paramètres en entrée :
    #   connection : récupère les informations de connexion à la base de données
    #   table_name_input : nom de la table en entrée
    #   table_name_output : nom de la table en sortie
    #   field_list : liste des champs attributaires à conserver en sortie (par défaut, tous les champs sont conservés)
    #   geom_field : champ de géométrie (par défaut, "geom")
    #   tolerance : niveau de tolérance de simplification, issue de la fonction ST_SimplifyPreserveTopology de PostGIS (par défaut : 1)
    """

    if field_list == []:
        field_list = getAllColumns(connection, table_name_input, print_result=False)
    field_list = [item for item in field_list if item != geom_field]

    field_list_str, field_list_str_bis = "", ""
    for field in field_list:
        field_list_str += "%s, " % field
        field_list_str_bis += "p.%s, " % field

    try:
        query = """
        DROP TABLE IF EXISTS %s CASCADE;
        CREATE TABLE %s AS
            WITH poly AS (
                SELECT %s, (ST_Dump(%s)).*
                FROM %s
            )
            SELECT %s, baz.%s
            FROM (
                SELECT (ST_Dump(ST_Polygonize(DISTINCT %s))).geom AS %s
                FROM (
                    SELECT (ST_Dump(ST_SimplifyPreserveTopology(ST_LineMerge(ST_Union(%s)), %s))).geom AS %s
                    FROM (
                        SELECT ST_ExteriorRing((ST_DumpRings(%s)).geom) AS %s
                        FROM poly
                    ) AS foo
                ) AS bar
            ) AS baz,
            poly AS p
            WHERE ST_Intersects(p.%s, baz.%s)
            AND ST_Area(ST_Intersection(p.%s, baz.%s))/ST_Area(baz.%s) > 0.5;
        """ % (table_name_output, table_name_output, field_list_str[:-2], geom_field, table_name_input, field_list_str_bis[:-2], geom_field, geom_field, geom_field, geom_field, tolerance, geom_field, geom_field, geom_field, geom_field, geom_field, geom_field, geom_field, geom_field)

        if debug >= 3:
            print(query)
        executeQuery(connection, query)

    except psycopg2.DatabaseError as err:
        if connection:
            connection.rollback()
        e = "OS error: {0}".format(err)
        print(bold + red + "coverageSimplify() : Error %s - Impossible de simplifier la géométrie de la table %s" % (e, table_name_input) + endC, file=sys.stderr)
        return -1

    return 0

###########################################################################################################################################
# FONCTION cutPolygonesByLines_Postgis()                                                                                                  #
###########################################################################################################################################
def cutPolygonesByLines_Postgis(vector_lines_input, vector_poly_input, vector_poly_output, epsg=2154, project_encoding="UTF-8", server_postgis="localhost", port_number=5432, user_postgis="postgres", password_postgis="postgres", database_postgis="cutbylines", schema_postgis="public", path_time_log="", format_vector='ESRI Shapefile', save_results_intermediate=False, overwrite=True) :
    """
    # ROLE:
    #     Découper des polygones ou multi-polygones par des lignes ou multi-lignes en traitement sous postgis
    #
    # ENTREES DE LA FONCTION :
    #     vector_lines_input: le vecteur de lignes de découpe d'entrée
    #     vector_poly_input: le vecteur de polygones à découpés d'entrée
    #     vector_poly_output: le vecteur e polygones de sortie découpés
    #     epsg : EPSG code de projection
    #     project_encoding : encodage des fichiers d'entrés
    #     server_postgis : nom du serveur postgis
    #     port_number : numéro du port pour le serveur postgis
    #     user_postgis : le nom de l'utilisateurs postgis
    #     password_postgis : le mot de passe de l'utilisateur postgis
    #     database_postgis : le nom de la base postgis à utiliser
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
    starting_event = "cutPolygonesByLines_Postgis() : Cuting polygons by lines  starting : "
    timeLine(path_time_log,starting_event)

    if debug >= 4:
        print(bold + green + "cutPolygonesByLines_Postgis() : Variables dans la fonction" + endC)
        print(cyan + "cutPolygonesByLines_Postgis() : " + endC + "vector_lines_input : " + str(vector_lines_input) + endC)
        print(cyan + "cutPolygonesByLines_Postgis() : " + endC + "vector_poly_input : " + str(vector_poly_input) + endC)
        print(cyan + "cutPolygonesByLines_Postgis() : " + endC + "vector_poly_output : " + str(vector_poly_output) + endC)
        print(cyan + "cutPolygonesByLines_Postgis() : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "cutPolygonesByLines_Postgis() : " + endC + "project_encoding : " + str(project_encoding) + endC)
        print(cyan + "cutPolygonesByLines_Postgis() : " + endC + "server_postgis : " + str(server_postgis) + endC)
        print(cyan + "cutPolygonesByLines_Postgis() : " + endC + "port_number : " + str(port_number) + endC)
        print(cyan + "cutPolygonesByLines_Postgis() : " + endC + "user_postgis : " + str(user_postgis) + endC)
        print(cyan + "cutPolygonesByLines_Postgis() : " + endC + "password_postgis : " + str(password_postgis) + endC)
        print(cyan + "cutPolygonesByLines_Postgis() : " + endC + "database_postgis : " + str(database_postgis) + endC)
        print(cyan + "cutPolygonesByLines_Postgis() : " + endC + "schema_postgis : " + str(schema_postgis) + endC)
        print(cyan + "cutPolygonesByLines_Postgis() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "cutPolygonesByLines_Postgis() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "cutPolygonesByLines_Postgis() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "cutPolygonesByLines_Postgis() : " + endC + "overwrite : " + str(overwrite) + endC)

    # Création de la base de données
    input_lignes_table=  os.path.splitext(os.path.basename(vector_lines_input))[0].lower()
    input_polygons_table =  os.path.splitext(os.path.basename(vector_poly_input))[0].lower()
    output_polygones_table =  os.path.splitext(os.path.basename(vector_poly_output))[0].lower()

    dropDatabase(database_postgis, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number))
    createDatabase(database_postgis, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number))

    # Import du fichier vecteur lines dans la base
    importVectorByOgr2ogr(database_postgis, vector_lines_input, input_lignes_table, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema_name=schema_postgis, epsg=str(epsg), codage=project_encoding)

    # Import du fichier vecteur polygones dans la base
    importVectorByOgr2ogr(database_postgis, vector_poly_input, input_polygons_table, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema_name=schema_postgis, epsg=str(epsg), codage=project_encoding)

    # Connexion à la base SQL postgis
    connection = openConnection(database_postgis, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema_name=schema_postgis)

    # Decoupage des polgones
    cutPolygonesByLines(connection, input_polygons_table, input_lignes_table, output_polygones_table, geom_field='geom')

    # Déconnexion de la base de données, pour éviter les conflits d'accès
    closeConnection(connection)

    # Récupération de la base du fichier vecteur de sortie
    exportVectorByOgr2ogr(database_postgis, vector_poly_output, output_polygones_table, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema_name=schema_postgis, format_type=format_vector)

    # Suppression des fichiers intermédiaires
    if not save_results_intermediate:
        try :
            dropDatabase(database_postgis, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number))
        except :
            print(cyan + "cutPolygonesByLines_Postgis() : " + bold + yellow + "Attention impossible de supprimer la base de donnée : " + endC + database_postgis)

    # Mise à jour du Log
    ending_event = "cutPolygonesByLines_Postgis() : Cuting polygons by lines ending : "
    timeLine(path_time_log,ending_event)

    return

###########################################################################################################################################
# FONCTION cutPolygonesByPolygones_Postgis()                                                                                              #
###########################################################################################################################################
def cutPolygonesByPolygones_Postgis(vector_poly_cut_input, vector_poly_input, vector_poly_output, epsg=2154, project_encoding="UTF-8", server_postgis="localhost", port_number=5432, user_postgis="postgres", password_postgis="postgres", database_postgis="cutbylines", schema_postgis="public", path_time_log="", format_vector='ESRI Shapefile', save_results_intermediate=False, overwrite=True) :
    """
    # ROLE:
    #     Découper des polygones ou multi-polygones par des polygones ou multi-polygones en traitement sous postgis
    #
    # ENTREES DE LA FONCTION :
    #     vector_poly_cut_input: le vecteur de polygones de découpe d'entrée
    #     vector_poly_input: le vecteur de polygones à découpés d'entrée
    #     vector_poly_output: le vecteur e polygones de sortie découpés
    #     epsg : EPSG code de projection
    #     project_encoding : encodage des fichiers d'entrés
    #     server_postgis : nom du serveur postgis
    #     port_number : numéro du port pour le serveur postgis
    #     user_postgis : le nom de l'utilisateurs postgis
    #     password_postgis : le mot de passe de l'utilisateur postgis
    #     database_postgis : le nom de la base postgis à utiliser
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
    starting_event = "cutPolygonesByPolygones_Postgis() : Cuting polygons by polygons  starting : "
    timeLine(path_time_log,starting_event)

    if debug >= 4:
        print(bold + green + "cutPolygonesByPolygones_Postgis() : Variables dans la fonction" + endC)
        print(cyan + "cutPolygonesByPolygones_Postgis() : " + endC + "vector_poly_cut_input : " + str(vector_poly_cut_input) + endC)
        print(cyan + "cutPolygonesByPolygones_Postgis() : " + endC + "vector_poly_input : " + str(vector_poly_input) + endC)
        print(cyan + "cutPolygonesByPolygones_Postgis() : " + endC + "vector_poly_output : " + str(vector_poly_output) + endC)
        print(cyan + "cutPolygonesByPolygones_Postgis() : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "cutPolygonesByPolygones_Postgis() : " + endC + "project_encoding : " + str(project_encoding) + endC)
        print(cyan + "cutPolygonesByPolygones_Postgis() : " + endC + "server_postgis : " + str(server_postgis) + endC)
        print(cyan + "cutPolygonesByPolygones_Postgis() : " + endC + "port_number : " + str(port_number) + endC)
        print(cyan + "cutPolygonesByPolygones_Postgis() : " + endC + "user_postgis : " + str(user_postgis) + endC)
        print(cyan + "cutPolygonesByPolygones_Postgis() : " + endC + "password_postgis : " + str(password_postgis) + endC)
        print(cyan + "cutPolygonesByPolygones_Postgis() : " + endC + "database_postgis : " + str(database_postgis) + endC)
        print(cyan + "cutPolygonesByPolygones_Postgis() : " + endC + "schema_postgis : " + str(schema_postgis) + endC)
        print(cyan + "cutPolygonesByPolygones_Postgis() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "cutPolygonesByPolygones_Postgis() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "cutPolygonesByPolygones_Postgis() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "cutPolygonesByPolygones_Postgis() : " + endC + "overwrite : " + str(overwrite) + endC)

    # Création de la base de données
    input_poly_cut_table=  os.path.splitext(os.path.basename(vector_poly_cut_input))[0].lower()
    input_polygons_table =  os.path.splitext(os.path.basename(vector_poly_input))[0].lower()
    output_polygones_table =  os.path.splitext(os.path.basename(vector_poly_output))[0].lower()

    dropDatabase(database_postgis, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number))
    createDatabase(database_postgis, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number))

    # Import du fichier vecteur lines dans la base
    importVectorByOgr2ogr(database_postgis, vector_poly_cut_input, input_poly_cut_table, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema_name=schema_postgis, epsg=str(epsg), codage=project_encoding)

    # Import du fichier vecteur polygones dans la base
    importVectorByOgr2ogr(database_postgis, vector_poly_input, input_polygons_table, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema_name=schema_postgis, epsg=str(epsg), codage=project_encoding)

    # Connexion à la base SQL postgis
    connection = openConnection(database_postgis, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema_name=schema_postgis)

    # Decoupage des polgones
    cutPolygonesByPolygones(connection, input_polygons_table, input_poly_cut_table, output_polygones_table, geom_field='geom')

    # Déconnexion de la base de données, pour éviter les conflits d'accès
    closeConnection(connection)

    # Récupération de la base du fichier vecteur de sortie
    exportVectorByOgr2ogr(database_postgis, vector_poly_output, output_polygones_table, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema_name=schema_postgis, format_type=format_vector)

    # Suppression des fichiers intermédiaires
    if not save_results_intermediate:
        try :
            dropDatabase(database_postgis, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number))
        except :
            print(cyan + "cutPolygonesByPolygones_Postgis() : " + bold + yellow + "Attention impossible de supprimer la base de donnée : " + endC + database_postgis)

    # Mise à jour du Log
    ending_event = "cutPolygonesByPolygones_Postgis() : Cuting polygons by polygons ending : "
    timeLine(path_time_log,ending_event)

    return

###########################################################################################################################################
# FUNCTION correctTopology_Postgis                                                                                                        #
###########################################################################################################################################
def correctTopology_Postgis(vector_input, vector_output, epsg=2154, project_encoding="UTF-8", server_postgis="localhost", port_number=5432, user_postgis="postgres", password_postgis="postgres", database_postgis="cutbylines", schema_postgis="public", path_time_log="", format_vector='ESRI Shapefile', save_results_intermediate=False, overwrite=True) :
    """
    # ROLE:
    #     Corriger les erreurs topologiques du fichier vecteur en traitement sous postgis
    #
    # ENTREES DE LA FONCTION :
    #     vector_input: le vecteur d'entrée à corrigé
    #     vector_output: le vecteur de sortie corrigé
    #     epsg : EPSG code de projection
    #     project_encoding : encodage des fichiers d'entrés
    #     server_postgis : nom du serveur postgis
    #     port_number : numéro du port pour le serveur postgis
    #     user_postgis : le nom de l'utilisateurs postgis
    #     password_postgis : le mot de passe de l'utilisateur postgis
    #     database_postgis : le nom de la base postgis à utiliser
    #     schema_postgis : le nom du schéma à utiliser
    #     path_time_log : le fichier de log de sortie
    #     format_vector : format du fichier vecteur. Optionnel, par default : 'ESRI Shapefile'
    #     save_results_intermediate : fichiers de sorties intermediaires nettoyees, par defaut = False
    #     overwrite : écrase si un fichier existant a le même nom qu'un fichier de sortie, par defaut a True
    #
    # SORTIES DE LA FONCTION :
    #     na
    """
    # Mise à jour du Log
    starting_event = "correctTopology_Postgis() : Correct topology  starting : "
    timeLine(path_time_log,starting_event)

    if debug >= 4:
        print(bold + green + "correctTopology_Postgis() : Variables dans la fonction" + endC)
        print(cyan + "correctTopology_Postgis() : " + endC + "vector_input : " + str(vector_input) + endC)
        print(cyan + "correctTopology_Postgis() : " + endC + "vector_output : " + str(vector_output) + endC)
        print(cyan + "correctTopology_Postgis() : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "correctTopology_Postgis() : " + endC + "project_encoding : " + str(project_encoding) + endC)
        print(cyan + "correctTopology_Postgis() : " + endC + "server_postgis : " + str(server_postgis) + endC)
        print(cyan + "correctTopology_Postgis() : " + endC + "port_number : " + str(port_number) + endC)
        print(cyan + "correctTopology_Postgis() : " + endC + "user_postgis : " + str(user_postgis) + endC)
        print(cyan + "correctTopology_Postgis() : " + endC + "password_postgis : " + str(password_postgis) + endC)
        print(cyan + "correctTopology_Postgis() : " + endC + "database_postgis : " + str(database_postgis) + endC)
        print(cyan + "correctTopology_Postgis() : " + endC + "schema_postgis : " + str(schema_postgis) + endC)
        print(cyan + "correctTopology_Postgis() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "correctTopology_Postgis() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "correctTopology_Postgis() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "correctTopology_Postgis() : " + endC + "overwrite : " + str(overwrite) + endC)

    table_correct_name = os.path.splitext(os.path.basename(vector_input))[0].lower()

    # Création de la base de données
    createDatabase(database_postgis, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number))

    # Monter en base du fichier vecteur de référence
    importVectorByOgr2ogr(database_postgis, vector_input, table_correct_name, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema_name=schema_postgis, epsg=str(epsg), codage=project_encoding)

    # Connexion à la base de données
    connection = openConnection(database_postgis, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema_name=schema_postgis) # Connexion à la base de données

    # Correction la géométrie (topologie)
    topologyCorrections(connection, table_correct_name, geom_field='geom')

    # Simplication des géometries
    tolerance = 1.0
    geom_field =' geom'
    query = "SELECT ST_SimplifyPreserveTopology(%s, %s) AS simplified_geom\n" % (geom_field, str(tolerance))
    query += "FROM %s;\n" % table_correct_name
    executeQuery(connection, query)

    # Déconnexion de la base de données (pour éviter les conflits avec les outils d'import de shape)
    closeConnection(connection)

    # Exporter le résutat sous forme de fichier vecteur
    exportVectorByOgr2ogr(database_postgis, vector_output, table_correct_name, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema_name=schema_postgis, format_type=format_vector)

    # Suppression de la base de données
    dropDatabase(database_postgis, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema_name=schema_postgis)

    # Mise à jour du Log
    ending_event = "correctTopology_Postgis() : Correct topology ending : "
    timeLine(path_time_log,ending_event)

    return

###########################################################################################################################################
# FUNCTION removeOverlaps_Postgis                                                                                                         #
###########################################################################################################################################
def removeOverlaps_Postgis(vector_input, vector_output, database_postgis="removeoverlaps", user_postgis="postgres", password_postgis="postgres", server_postgis="localhost", port_number=5432, schema_postgis="public", epsg=2154, project_encoding="UTF-8", geometry_type="GEOMETRY", geometry_name="geom", fid_name="fid", format_vector="ESRI Shapefile", ogr2ogr_more_parameters="", min_area=0, path_time_log=""):
    """
    # ROLE:
    #     Supprimer les recouvrements du fichier vecteur en traitement sous postgis
    #
    # ENTREES DE LA FONCTION :
    #     vector_input: le vecteur d'entrée à corriger
    #     vector_output: le vecteur de sortie corrigé
    #     database_postgis : nom de la base de données (par défaut : 'removeoverlaps')
    #     user_postgis : nom d'utilisateur du serveur PostgreSQL (par défaut : 'postgres')
    #     password_postgis : mot de passe du serveur PostgreSQL (par défaut : 'postgres')
    #     server_postgis : adresse IP du serveur PostgreSQL (par défaut : 'localhost')
    #     port_number : numéro de port du serveur PostgreSQL (par défaut : '5432')
    #     schema_postgis : nom du schema à utiliser (par défaut : 'public')
    #     epsg : code EPSG de la projection des données à importer (par défaut : '2154')
    #     project_encoding : encodage de caractères du fichier à importer (par défaut : 'UTF-8')
    #     geometry_type : type de géométrie en entrée (POINT, LINESTRING, POLYGON...) (par défaut : 'GEOMETRY')
    #     geometry_name : nom du champ géométrie (par défaut : 'geom')
    #     fid_name : nom du champ de clé primaire (par défaut : 'fid')
    #     format_type : format d'export des données (par défaut : 'ESRI Shapefile')
    #     ogr2ogr_more_parameters : paramètres supplémentires pour l'export ogr2ogr (par défaut : '')
    #     min_area : taille minimale des polygones qui seront conservés pendant les traitements (par défaut : 0, tous les polygones seront conservés)
    #     path_time_log : le fichier de log de sortie
    #
    # SORTIES DE LA FONCTION :
    #     NA
    """

    # Mise à jour du Log
    starting_event = "removeOverlaps_Postgis() : Remove overlaps starting : "
    timeLine(path_time_log, starting_event)

    if debug >= 4:
        print(bold + green + "removeOverlaps_Postgis() : Variables dans la fonction" + endC)
        print(cyan + "removeOverlaps_Postgis() : " + endC + "vector_input : " + str(vector_input) + endC)
        print(cyan + "removeOverlaps_Postgis() : " + endC + "vector_output : " + str(vector_output) + endC)
        print(cyan + "removeOverlaps_Postgis() : " + endC + "database_postgis : " + str(database_postgis) + endC)
        print(cyan + "removeOverlaps_Postgis() : " + endC + "user_postgis : " + str(user_postgis) + endC)
        print(cyan + "removeOverlaps_Postgis() : " + endC + "password_postgis : " + str(password_postgis) + endC)
        print(cyan + "removeOverlaps_Postgis() : " + endC + "server_postgis : " + str(server_postgis) + endC)
        print(cyan + "removeOverlaps_Postgis() : " + endC + "port_number : " + str(port_number) + endC)
        print(cyan + "removeOverlaps_Postgis() : " + endC + "schema_postgis : " + str(schema_postgis) + endC)
        print(cyan + "removeOverlaps_Postgis() : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "removeOverlaps_Postgis() : " + endC + "project_encoding : " + str(project_encoding) + endC)
        print(cyan + "removeOverlaps_Postgis() : " + endC + "geometry_type : " + str(geometry_type) + endC)
        print(cyan + "removeOverlaps_Postgis() : " + endC + "geometry_name : " + str(geometry_name) + endC)
        print(cyan + "removeOverlaps_Postgis() : " + endC + "fid_name : " + str(fid_name) + endC)
        print(cyan + "removeOverlaps_Postgis() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "removeOverlaps_Postgis() : " + endC + "ogr2ogr_more_parameters : " + str(ogr2ogr_more_parameters) + endC)
        print(cyan + "removeOverlaps_Postgis() : " + endC + "min_area : " + str(min_area) + endC)
        print(cyan + "removeOverlaps_Postgis() : " + endC + "path_time_log : " + str(path_time_log) + endC)

    table_name = os.path.splitext(os.path.basename(vector_input))[0].lower()

    # Création de la base de données
    createDatabase(database_postgis, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number))

    # Montée en table du fichier vecteur
    importVectorByOgr2ogr(database_postgis, vector_input, table_name, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema_name=schema_postgis, epsg=str(epsg), codage=project_encoding, geometry_type=geometry_type, geometry_name=geometry_name, fid_name=fid_name)

    # Connexion à la base de données
    connection = openConnection(database_postgis, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema_name=schema_postgis)

    # Suppression des recouvrements
    removeOverlaps(connection, table_name, fid_field=fid_name, geom_field=geometry_name, min_area=min_area)

    # Correction topologique
    topologyCorrections(connection, table_name, geom_field=geometry_name)

    # Déconnexion de la base de données
    closeConnection(connection)

    # Descente de la table en fichier vecteur
    exportVectorByOgr2ogr(database_postgis, vector_output, table_name, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema_name=schema_postgis, format_type=format_vector, ogr2ogr_more_parameters=ogr2ogr_more_parameters)

    # Suppression de la base de données
    dropDatabase(database_postgis, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema_name=schema_postgis)

    # Mise à jour du Log
    ending_event = "removeOverlaps_Postgis() : Remove overlaps ending : "
    timeLine(path_time_log, ending_event)

    return

###########################################################################################################################################
# FUNCTION coverageSimplify_Postgis                                                                                                       #
###########################################################################################################################################
def coverageSimplify_Postgis(vector_input, vector_output, database_postgis="coveragesimplify", user_postgis="postgres", password_postgis="postgres", server_postgis="localhost", port_number=5432, schema_postgis="public", epsg=2154, project_encoding="UTF-8", geometry_type="GEOMETRY", geometry_name="geom", fid_name="fid", format_vector="ESRI Shapefile", ogr2ogr_more_parameters="", field_list=[], tolerance=1, path_time_log=""):
    """
    !!! ATTENTION fonction coverageSimplify() en cours de développement !!!
    # ROLE:
    #     Simplifier les géométries en conservant les frontières entre polygones du fichier vecteur en traitement sous postgis
    #
    # ENTREES DE LA FONCTION :
    #     vector_input: le vecteur d'entrée à corriger
    #     vector_output: le vecteur de sortie corrigé
    #     database_postgis : nom de la base de données (par défaut : 'removeoverlaps')
    #     user_postgis : nom d'utilisateur du serveur PostgreSQL (par défaut : 'postgres')
    #     password_postgis : mot de passe du serveur PostgreSQL (par défaut : 'postgres')
    #     server_postgis : adresse IP du serveur PostgreSQL (par défaut : 'localhost')
    #     port_number : numéro de port du serveur PostgreSQL (par défaut : '5432')
    #     schema_postgis : nom du schema à utiliser (par défaut : 'public')
    #     epsg : code EPSG de la projection des données à importer (par défaut : '2154')
    #     project_encoding : encodage de caractères du fichier à importer (par défaut : 'UTF-8')
    #     geometry_type : type de géométrie en entrée (POINT, LINESTRING, POLYGON...) (par défaut : 'GEOMETRY')
    #     geometry_name : nom du champ géométrie (par défaut : 'geom')
    #     fid_name : nom du champ de clé primaire (par défaut : 'fid')
    #     format_type : format d'export des données (par défaut : 'ESRI Shapefile')
    #     ogr2ogr_more_parameters : paramètres supplémentires pour l'export ogr2ogr (par défaut : '')
    #     field_list : liste des champs attributaires à conserver en sortie (par défaut, tous les champs sont conservés)
    #     tolerance : niveau de tolérance de simplification, issue de la fonction ST_SimplifyPreserveTopology de PostGIS (par défaut : 1)
    #     path_time_log : le fichier de log de sortie
    #
    # SORTIES DE LA FONCTION :
    #     NA
    """

    # Mise à jour du Log
    starting_event = "coverageSimplify_Postgis() : Simplify coverage starting : "
    timeLine(path_time_log, starting_event)

    if debug >= 4:
        print(bold + green + "coverageSimplify_Postgis() : Variables dans la fonction" + endC)
        print(cyan + "coverageSimplify_Postgis() : " + endC + "vector_input : " + str(vector_input) + endC)
        print(cyan + "coverageSimplify_Postgis() : " + endC + "vector_output : " + str(vector_output) + endC)
        print(cyan + "coverageSimplify_Postgis() : " + endC + "database_postgis : " + str(database_postgis) + endC)
        print(cyan + "coverageSimplify_Postgis() : " + endC + "user_postgis : " + str(user_postgis) + endC)
        print(cyan + "coverageSimplify_Postgis() : " + endC + "password_postgis : " + str(password_postgis) + endC)
        print(cyan + "coverageSimplify_Postgis() : " + endC + "server_postgis : " + str(server_postgis) + endC)
        print(cyan + "coverageSimplify_Postgis() : " + endC + "port_number : " + str(port_number) + endC)
        print(cyan + "coverageSimplify_Postgis() : " + endC + "schema_postgis : " + str(schema_postgis) + endC)
        print(cyan + "coverageSimplify_Postgis() : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "coverageSimplify_Postgis() : " + endC + "project_encoding : " + str(project_encoding) + endC)
        print(cyan + "coverageSimplify_Postgis() : " + endC + "geometry_type : " + str(geometry_type) + endC)
        print(cyan + "coverageSimplify_Postgis() : " + endC + "geometry_name : " + str(geometry_name) + endC)
        print(cyan + "coverageSimplify_Postgis() : " + endC + "fid_name : " + str(fid_name) + endC)
        print(cyan + "coverageSimplify_Postgis() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "coverageSimplify_Postgis() : " + endC + "ogr2ogr_more_parameters : " + str(ogr2ogr_more_parameters) + endC)
        print(cyan + "coverageSimplify_Postgis() : " + endC + "field_list : " + str(field_list) + endC)
        print(cyan + "coverageSimplify_Postgis() : " + endC + "tolerance : " + str(tolerance) + endC)
        print(cyan + "coverageSimplify_Postgis() : " + endC + "path_time_log : " + str(path_time_log) + endC)

    table_name_input = os.path.splitext(os.path.basename(vector_input))[0].lower()
    table_name_output = os.path.splitext(os.path.basename(vector_output))[0].lower()

    # Création de la base de données
    createDatabase(database_postgis, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number))

    # Montée en table du fichier vecteur
    importVectorByOgr2ogr(database_postgis, vector_input, table_name_input, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema_name=schema_postgis, epsg=str(epsg), codage=project_encoding, geometry_type=geometry_type, geometry_name=geometry_name, fid_name=fid_name)

    # Connexion à la base de données
    connection = openConnection(database_postgis, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema_name=schema_postgis)

    # Simplification de la géométrie
    coverageSimplify(connection, table_name_input, table_name_output, field_list=field_list, geom_field=geometry_name, tolerance=tolerance)

    # Déconnexion de la base de données
    closeConnection(connection)

    # Descente de la table en fichier vecteur
    exportVectorByOgr2ogr(database_postgis, vector_output, table_name_output, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema_name=schema_postgis, format_type=format_vector, ogr2ogr_more_parameters=ogr2ogr_more_parameters)

    # Suppression de la base de données
    dropDatabase(database_postgis, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema_name=schema_postgis)

    # Mise à jour du Log
    ending_event = "coverageSimplify_Postgis() : Simplify coverage ending : "
    timeLine(path_time_log, ending_event)

    return

