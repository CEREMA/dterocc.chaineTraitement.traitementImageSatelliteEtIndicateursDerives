# -*- coding: utf-8 -*-
#!/usr/bin/python

#############################################################################
# Copyright (©) CEREMA/DTerSO/DALETT/SCGSI  All rights reserved.            #
#############################################################################

#############################################################################
#                                                                           #
# FONCTIONS EN LIEN AVEC DES REQUETES SQL SPATIALITE                        #
#                                                                           #
#############################################################################

# IMPORTS UTILES
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC
import sqlite3
import os

#########################################################################
# FONCTION sqlInsertTable()                                             #
#########################################################################
def sqlInsertTable(file_imput_name, table_name_db, data_base_name, epsg=2154, geometry='GEOMETRY', encoding='UTF-8',type_geom='POLYGON'):
    requete_cmd = "spatialite_tool -i -shp %s -d %s -t %s -g %s -c %s -s %d --type %s" %(file_imput_name, data_base_name, table_name_db, geometry, encoding, epsg, type_geom)

    return requete_cmd


#########################################################################
# FONCTION sqlExportShape()                                             #
#########################################################################
def sqlExportShape(file_output_name, table_name_db, data_base_name, epsg=2154, geometry='GEOMETRY', encoding='UTF-8',type_geom='POLYGON'):
    requete_cmd = "spatialite_tool -e -shp %s -d %s -t %s -g %s -c %s -s %d --type %s" %(file_output_name, data_base_name, table_name_db, geometry, encoding, epsg, type_geom)

    return requete_cmd


#########################################################################
# FONCTION sqlExecuteQuery()                                             #
#########################################################################
def sqlExecuteQuery(data_base_name, query):
    requete_cmd = "spatialite %s %s" %(data_base_name, query)

    return requete_cmd


#########################################################################
# FONCTION sqlDeleteOneLine()                                           #
#########################################################################
def sqlDeleteOneLine(table_name, field_name, value, data_base_name):
    requete = "\"DELETE FROM "
    requete += table_name
    requete += " WHERE "
    requete += "%s = %d " %(field_name, value) + "\""
    displaySQL(requete)
    requete_spat = "spatialite %s %s" %(data_base_name, requete)

    return requete_spat


#########################################################################
# FONCTION sqlMaxValue()                                                #
#########################################################################
def sqlMaxValue(table_input_name, field_name_cond, exp_cond, value_cond, data_base_name):
    requete = "\"SELECT MAX(%s) AS NOMBRE" %(field_name_cond)
    requete += " FROM %s" %(table_input_name)
    requete += " WHERE %s = %d" %(exp_cond, value_cond)
    requete += "\""
    requete_spat = "spatialite %s %s" %(data_base_name, requete)

    return requete_spat


#########################################################################
# FONCTION sqlModifyOneLine()                                           #
#########################################################################
def sqlModifyOneLine(table_input_name, field_name_cond, value_cond, field_name_mo, value_mo, data_base_name):
    requete = "\"UPDATE "
    requete += table_input_name
    requete += " SET %s = %s " %(field_name_mo, value_mo)
    requete += " WHERE %s = %d" %(field_name_cond, value_cond)
    requete += "\""
    displaySQL(requete)
    requete_spat = "spatialite %s %s" %(data_base_name, requete)

    return requete_spat


#########################################################################
# FONCTION sqlCreateTable()                                             #
#########################################################################
def sqlCreateTable(table_input_name, table_output_name, field_name, value_cond, data_base_name):
    requete = "\"CREATE TABLE %s AS" %(table_output_name)
    requete += " SELECT * FROM %s " %(table_input_name)
    requete += " WHERE %s = %d" %(field_name, value_cond)
    requete += "\""
    displaySQL(requete)
    requete_spat = "spatialite %s %s" %(data_base_name, requete)

    return requete_spat


#########################################################################
# FONCTION sqlComputeNumberOfField()                                    #
#########################################################################
def sqlComputeNumberOfField(table_input_name, field_name, value, data_base_name):
    requete = "\"SELECT COUNT(*) AS NOMBRE "
    requete += " FROM %s" %(table_input_name)
    requete += " WHERE %s = %d" %(field_name, value)
    requete += "\""
    displaySQL(requete)
    requete_spat = "spatialite %s %s" %(data_base_name, requete)

    return requete_spat


#########################################################################
# FONCTION sqlGroupGeometry()                                           #
#########################################################################
def sqlGroupGeometry(table_inprogress_name, table_micro_name, table_output_name, data_base_name):
    requete = "\"CREATE TABLE %s AS" %(table_output_name)
    requete += " SELECT SUPP.PK_UID AS PK_UID, SUPP.ID AS ID, ORIG.GEOMETRY AS METRY, GUNION(SUPP.GEOMETRY) AS GEOMETRY"
    requete += " FROM %s AS SUPP, %s AS ORIG" %(table_micro_name, table_inprogress_name)
    requete += " WHERE INTERSECTS(SUPP.GEOMETRY, ORIG.GEOMETRY)"
    requete += " GROUP BY ORIG.GEOMETRY"
    requete += " ORDER BY SUPP.PK_UID"
    requete += "\""
    displaySQL(requete)
    requete_spat = "spatialite %s %s" %(data_base_name, requete)

    return requete_spat


#########################################################################
# FONCTION sqlDeleteGeometry()                                          #
#########################################################################
def sqlDeleteGeometry(table_inprogress_name, table_group_name, table_diff_name, data_base_name):
    requete = "\"CREATE TABLE %s AS" %(table_diff_name)
    requete += " SELECT ORIG.PK_UID AS PK_UID, ORIG.ID AS ID, DIFFERENCE(ORIG.GEOMETRY, GRP.GEOMETRY) AS GEOMETRY"
    requete += " FROM %s ORIG, %s GRP" %(table_inprogress_name, table_group_name)
    requete += " WHERE INTERSECTS(ORIG.GEOMETRY, GRP.GEOMETRY)"
    requete += "\""
    displaySQL(requete)
    requete_spat = "spatialite %s %s" %(data_base_name, requete)

    return requete_spat


#########################################################################
# FONCTION sqlCreateMaskEnd()                                           #
#########################################################################
def sqlCreateMaskEnd(table_inprogress_name, table_supp_name, table_end_name, data_base_name):
    requete = "\"CREATE TABLE %s AS" %(table_end_name)
    requete += " SELECT DIFF.PK_UID AS PK_UID, DIFF.ID AS ID, DIFF.GEOMETRY AS GEOMETRY"
    requete += " FROM %s AS ORIG, %s AS DIFF" %(table_inprogress_name, table_supp_name)
    requete += " WHERE DIFF.PK_UID = ORIG.PK_UID"
    requete += " UNION"
    requete += " SELECT ORIG.PK_UID AS PK_UID, ORIG.ID AS ID, ORIG.GEOMETRY AS GEOMETRY"
    requete += " FROM %s AS ORIG" %(table_inprogress_name)
    requete += " WHERE ORIG.PK_UID NOT IN (SELECT DIFF.PK_UID FROM %s AS DIFF)" %(table_supp_name)
    requete += "\""
    displaySQL(requete)
    requete_spat = "spatialite %s %s" %(data_base_name, requete)

    return requete_spat


#########################################################################
# FONCTION sqlCreateTableGeometryEmpty()                                #
#########################################################################
def sqlCreateTableGeometryEmpty(table_new_name, data_base_name):
    requete = "\"CREATE TABLE %s (" %(table_new_name)
    requete += " ID INT,"
    requete += " GEOMETRY)"
    requete += "\""
    requete_spat = "spatialite %s %s" %(data_base_name, requete)
    displaySQL(requete_spat)

    return requete_spat


#########################################################################
# FONCTION sqlFillTableGeometry()                                       #
#########################################################################
def sqlFillTableGeometry(table_orig_name, table_dest_name, data_base_name):
    requete = "\"INSERT INTO %s (" %(table_dest_name)
    requete += " ID, GEOMETRY)"
    requete += " SELECT ID, GEOMETRY"
    requete += " FROM %s" %(table_orig_name)
    requete += "\""
    requete_spat = "spatialite %s %s" %(data_base_name, requete)
    displaySQL(requete_spat)

    return requete_spat


#########################################################################
# FONCTION sqlDeleteTable()                                             #
#########################################################################
def sqlDeleteTable(table_name, data_base_name):
    requete = "\"DROP TABLE %s \"" %(table_name)
    requete_spat = "spatialite %s %s" %(data_base_name, requete)
    displaySQL(requete_spat)

    return requete_spat


#########################################################################
# FONCTION sqlRenameTable()                                             #
#########################################################################
def sqlRenameTable(table_name, table_new_name, data_base_name):
    requete = "\"ALTER TABLE %s RENAME TO %s \"" %(table_name, table_new_name)
    requete_spat = "spatialite %s %s" %(data_base_name, requete)
    displaySQL(requete_spat)

    return requete_spat


#########################################################################
# FONCTION sqlRemoveMinSurface()                                        #
#########################################################################
def sqlRemoveMinSurface(table_name, table_new_name, fSurf, data_base_name):
    requete = "\"CREATE TABLE %s AS" %(table_new_name)
    requete += " SELECT * "
    requete += " FROM %s" %(table_name)
    requete += " WHERE AREA(GEOMETRY) >= %f" %(fSurf)
    requete += "\""
    requete_spat = "spatialite %s %s" %(data_base_name, requete)
    displaySQL(requete_spat)

    return requete_spat


#########################################################################
# FONCTION sqlJoinTables()                                              #
#########################################################################
def sqlJoinTables(table_name1, table_name2, table_new_name, data_base_name):
    requete = "\"CREATE TABLE %s AS" %(table_new_name)
    requete += " SELECT ID, GEOMETRY FROM %s " %(table_name1)
    requete += " UNION"
    requete += " SELECT ID, GEOMETRY FROM %s" %(table_name2)
    requete += "\""
    requete_spat = "spatialite %s %s" %(data_base_name, requete)
    displaySQL(requete_spat)

    return requete_spat


#########################################################################
# FONCTION sqlSurfaceAverageMacro()                                     #
#########################################################################
def sqlSurfaceAverageMacro(table_name, field_name, macro, data_base_name):
    requete = "\"SELECT SUM(TB.SURFACE) / COUNT(TB.ID) AS MOYENNE"
    requete += " FROM(SELECT %s, SUM(AREA(GEOMETRY)) AS SURFACE" %(field_name)
    requete += " FROM %s" %(table_name)
    requete += " WHERE (ID/100)*100 = %d" %(macro)
    requete += " GROUP BY %s) AS TB" %(field_name)
    requete += "\""
    requete_spat = "spatialite %s %s" %(data_base_name, requete)
    displaySQL(requete_spat)

    return requete_spat


#########################################################################
# FONCTION sqlSurfaceMicro()                                            #
#########################################################################
def sqlSurfaceMicro(table_name, field_name, micro, data_base_name):
    requete = "\"SELECT SUM(AREA(GEOMETRY)) AS SURFACE"
    requete += " FROM %s" %(table_name)
    requete += " WHERE %s = %d" %(field_name, micro)
    requete += "\""
    requete_spat = "spatialite %s %s" %(data_base_name, requete)
    displaySQL(requete_spat)

    return requete_spat


#########################################################################
# FONCTION sqlCreatetableQuery()                                        #
#########################################################################
def sqlCreatetableQuery(table_output_name):
    query = "\"CREATE TABLE %s AS"%(table_output_name)
    displaySQL(query)

    return query


#########################################################################
# FONCTION sqlSimplifyBufferPolyQuery()                                 #
#########################################################################
def sqlSimplifyBufferPolyQuery(query_input, input_table, buffer_size, simplification_tolerance):
    query = " SELECT id,simplify(buffer(GEOMETRY,%d),%d) AS GEOMETRY FROM %s WHERE simplify(buffer(GEOMETRY,%d),%d) IS NOT NULL"%(buffer_size, simplification_tolerance,input_table,buffer_size,simplification_tolerance)
    query_output = query_input + query + " UNION"

    return query_output


#########################################################################
# FONCTION sqlSingleSidedBuffer()                                       #
#########################################################################
def sqlSingleSidedBuffer(query_input, input_table, buffer_size, buffer_side, id_column):
    query = " SELECT singleSidedBuffer(geometry,%d,%d) AS GEOMETRY FROM %s WHERE singleSidedBuffer(GEOMETRY,%d,%d) IS NOT NULL"%(buffer_size, buffer_side, input_table, buffer_size, buffer_side)
    query_output = query_input + query + " UNION"

    return query_output


#########################################################################
# FONCTION displaySQL()                                                 #
#########################################################################
def displaySQL(requete):
    print(bold + yellow + "Requete : " + requete + endC)

    return

#########################################################################
# FONCTION CopyTableStrucureTypeAndCreateTable()                        #
#########################################################################

#   cette fonction :
#  1 se connecte à une base sqlite de reference
#    Recupere informations relatives aux colonnes de la table : name, types, notnull, default value
#
#  2 ouvre la base destination dans laquelle on souhaite creer une nouvelle table a l'identique
#    ou
#    !!!! Reste a faire !!!!
#    ouvre la base reference dans laquelle on souhaite creer une nouvelle table a l'identique.
#    NB Dans ce cas il faut proposer un nom pour la nouvelle table
#
#  3 crée une table et les colonnes associées et renseigne les name, types, notnull, default value conformement a la table de reference

def CopyTableStrucureTypeAndCreateTable ( example_database , Table, DestDatabase ):

    # Connection a la base de reference
    # Recuperation des donnees relatives a la table de reference sous forme de CREATE TABLE AS ...

    conn = sqlite3.connect(example_database)
    c = conn.cursor()

  # On recupere les informations relatives aux colonnes de la table : name, types, notnull, default value
    for row in c.execute("SELECT * FROM sqlite_master;"):
        if row[1] == Table :
      # on selectionne la requête de création des colonnes
            requete_creation_table = row[4]

    c.close
    conn.close()

    # Connection a la base destinataire de la nouvelle table
    conn = sqlite3.connect(DestDatabase)
    c = conn.cursor()

    # On verifie que la table n'existe pas deja dans la base de destination

    requete = "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='%s';" %( Table )
    for check in c.execute("%s" % (requete)) :
        check = check [0]

    DestDatabaseName = os.path.basename(DestDatabase)
    if check == 0:
        # si elle n exsite pas on la crée

        print("creation de la table " , Table, " dans la base " , DestDatabaseName)
        c.execute("%s" % (requete_creation_table))
    else:
        print(" la table " , Table , " exite deja dans la base" , DestDatabaseName)

    c.close
    conn.close()

    return


#########################################################################
# FONCTION listTableCondition()                                         #
#########################################################################

#    Cette fonction se connecte à une base sqlite, et retourne une liste de lignes d'une table en fonction des champs selectionnes et d'une condition
#    la fonction retourne une liste comprenant toute les lignes repondant au criteres de condition
#    Exemples de paramétrage :
#    base_de_donne = "/base_test/Base.db"
#    Table = "Temperature"
#    Champs = 'DeviceRowID , Temperature , Date'
#    Condition = ' Temperature < 0 '

def listTableCondition ( database , Table , Fields , Condition = "") :


    conn = sqlite3.connect( database)
    c = conn.cursor()
    List = []
    if Condition != "" :
        for row in c.execute('SELECT %s FROM %s WHERE %s;' %( Fields , Table , Condition )):
            List.append(row)
    else :
        for row in c.execute('SELECT %s FROM %s ;' %( Fields , Table )):
            List.append(row)

    conn.close()
    return List


#########################################################################
# FONCTION lister_table()                                               #
#########################################################################

#    Cette fonction se connecte à une base sqlite, puis liste les lignes d'une table en fonction des champs selectionnes
#    la fonction retourne une liste comprenant toute les lignes de la table
#    exemples :
#    base_de_donne = "/base_test/Base.db"
#    Table = "Temperature"
#    Champs = 'DeviceRowID , Temperature , Date'
#    Champs = '*'

def lister_table ( database , Table , Fields ):


    conn = sqlite3.connect(database)
    c = conn.cursor()

    List = []
    for row in c.execute('SELECT %s FROM %s' %(Fields,Table)):
        List.append(row)

    conn.close()
    return List


#########################################################################
# FONCTION listFieldsTable()                                            #
#########################################################################

#    Cette fonction se connecte à une base sqlite, puis liste les champs d'une table
#    la fonction retourne une liste comprenant toute les champs de la table, leur type etc..
#    exemples :
#    base_de_donne = "/base_test/Base.db"
#    Table = "Temperature"

def listFieldsTable( database , Table ):

    conn = sqlite3.connect(database)
    c = conn.cursor()
    List = []


    for row in c.execute("PRAGMA table_info(%s);" % (Table)):
        List.append(row)

    c.close
    conn.close()
    return List


#########################################################################
# FONCTION PopulateTableFromList()                                      #
#########################################################################

#    Cette fonction se connecte à une base sqlite, puis injecte les valeur d'une liste
#    La liste doit être compatible avec la table destination nombre champs et type (en particulier s'il y a une contrainte sur le champ

def PopulateTableFromList ( database , Table , List ):

    conn = sqlite3.connect(database)
    c = conn.cursor()

    # on prepare la variable nbr de champs à inserer dans la requette
    # Exemple : (?,?,?) pour trois champs par exemple
    NbrFields = len(List[0])
    NbrFields2 = "(?"

    for i in range(1, NbrFields):
        NbrFields2 = NbrFields2 + ",?"
    NbrFields2 = NbrFields2 + ")"

    # on insere chaque element de la liste dans la table

    c.executemany('INSERT INTO %s VALUES %s' %( Table , NbrFields2 ) , List)

    conn.commit()
    conn.close()
    return

#########################################################################
# FONCTION EraseDuplicate()                                             #
#########################################################################

#    Cette fonction se connecte à une base sqlite, puis efface tous les enregistrements en double

def EraseDuplicate ( database , Table ):

    TableTemp = ""

    conn = sqlite3.connect(database)
    c = conn.cursor()

    c.execute('CREATE TABLE "TableTemp" as SELECT distinct * FROM %s' %(Table))
    print("table temporaire ecrite sans les doublons")
    c.execute('DROP TABLE %s' %(Table))
    print("effacement de la table : " , Table)
    c.execute('ALTER TABLE TableTemp RENAME TO %s' %(Table))
    print("procedure d effacement des enregistrements en double terminee")

    conn.close()
    return


#########################################################################
# FONCTION ExportQueryToCsv()                                           #
#########################################################################
'''
En chantier fonction a valider
'''
def ExportQueryToCsv ( database , Table , Fields , File , Condition ):

    if os.path.isfile(File):
        os.remove(File)

    # On cree et on ouvre le fichier
    fichier = open(File, "a")
    # open a file to write to
    conn = sqlite3.connect(database)
    # connect to your database
    c = conn.cursor()

    # comptage du nombre de colonnes & et preparation en tete du csv aevc les noms de colones
    nbrCol = 0
    Entete = ""
    for row in c.execute("PRAGMA table_info(%s);" % (Table)):
        nbrCol = nbrCol + 1
        Entete = Entete + str (row [1]) + ","
    Entete = Entete [:-1] + '\n'
    fichier.write(Entete)

    Line = ""
    print('SELECT %s FROM %s WHERE %s ;' %( Fields , Table , Condition ))
    for row in c.execute('SELECT %s FROM %s WHERE %s ;' %( Fields , Table , Condition )):
        for column in range (0,nbrCol) :
            rown = str(row [column]) + ","
            Line = Line + rown

        Line = Line [:-1] + '\n'
        fichier.write(Line)
        Line = ""

    fichier.close()
    return
