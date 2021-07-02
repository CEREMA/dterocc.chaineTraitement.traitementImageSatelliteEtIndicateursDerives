# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerSO/DALETT/SCGSI  All rights reserved.                                                                            #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT QUI TRANSFORME UN LABEL DE TACHE EN COMMANDE                                                                                       #
#                                                                                                                                           #
#############################################################################################################################################

import os,glob, time, shutil, platform
import six
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC
from Lib_operator import *
from Lib_text import appendTextFile, appendTextFileCR, cleanSpaceText
from Lib_file import removeFile
from Settings import *

#################################################################################
# FONCTION endCommandUpdate()                                                   #
#################################################################################
# ROLE :
#    Fonction mutualisé pour la creation de certaines commandes, realise la fin de la commande
#
# ENTREES :
#   settings_struct : La structure contenant des settings
#   command_doc : le fichier contenant les commandes
#   command : la commande courante à modifier
#   debug : niveau de trace log
#   call_python : Utilise PYTHON pour s'executer

def endCommandUpdate(settings_struct, command_doc, command, debug, call_python=True):

    # Gestion des option de sauvegarde des resultats intermediaires et ecrassement des fichiers existants
    if call_python :
        if settings_struct.general.processing.logFile != "":
            if six.PY2:
                command += " -log " + settings_struct.general.processing.logFile.encode("utf-8")
            else :
                command += " -log " + settings_struct.general.processing.logFile

        if not settings_struct.general.processing.overWriting:
            command += " -now"

        if settings_struct.general.processing.saveIntermediateResults :
            command += " -sav"

        command += " -debug " + str(debug)

    # Ajout de la commande au fichier
    appendTextFileCR(command_doc,command)

    # Trace de la commande
    if debug >= 2:
        print(cyan + "writeCommands() : " + endC + "command : " + str(command))

    return

#################################################################################
# FONCTION getCallPythonActionToMake()                                          #
#################################################################################
# ROLE :
#   Fonction mutualisé pour la creation de certaines commandes, realise le début de la commande
#
# ENTREES :
#   settings_struct : La structure contenant des settings
#   name_setting : nom du fichier contenant les settings
#   task_label : label de la tâche que l'on souhaite transformer en ligne de commande
#   task_position : postion de la tache si plusieurs même tache
#   mode_execution_command : Le mode d'execution choisi
#   error_management : Type gestion des erreurs
#   dependency_commands_list_string : La liste des dépendences de taches
#   id_command : compteur d'id de commande
#   index_remote_ip : index sur la machine remote disponible courante
#   id_task_commands_list : liste des id des commandes dont dépend la tache
#   call_python : Utilise PYTHON pour s'executer
#
# SORTIES :
#   id_command : compte de commande incrementé
#   index_remote_ip : index sur la machine remote disponible incrementer
#   id_task_commands_list : liste des id des commandes dont dépend la tache mis à jour avec la nouvelle tache

def getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list, call_python=True):

    # Si execution en remote
    remote_ip = ''
    login = ''
    password = ''
    if mode_execution_command == TAG_ACTION_TO_MAKE_RE :
        remote_ip = settings_struct.general.processing.remoteComputeurList[index_remote_ip].ip_adress
        login = settings_struct.general.processing.remoteComputeurList[index_remote_ip].login
        password = settings_struct.general.processing.remoteComputeurList[index_remote_ip].password

    # Preparation de l'entête ligne
    # Ex : "A_Faire # 801 # 800 # 30_RA #  Background  # True #  #  #  #  # python /home/scgsi/Documents/ChaineTraitement/ScriptsApplications/"
    call_python_action_to_make = TAG_STATE_MAKE + SEPARATOR + str(id_command) + SEPARATOR + dependency_commands_list_string + SEPARATOR + name_setting + "." + task_label + "." + str(task_position) + SEPARATOR + mode_execution_command + SEPARATOR + str(error_management) + SEPARATOR  + remote_ip + SEPARATOR + login + SEPARATOR + password + SEPARATOR + SEPARATOR + SEPARATOR

    if call_python :
        if six.PY2:
            call_python_action_to_make += FUNCTION_PYTHON
        else :
            call_python_action_to_make += FUNCTION_PYTHON3

    # Gestion de l'index des machines remotes selection par buffer circulaire
    index_remote_ip += 1
    if index_remote_ip >= len(settings_struct.general.processing.remoteComputeurList) :
        index_remote_ip = 0

    # Gestion des id des commandes
    id_task_commands_list.append(id_command)
    id_command += 1

    return  call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list

#################################################################################
# FONCTION createDependencyList()                                               #
#################################################################################
# ROLE :
#   Fonction pour la creation de liste de id de commandes dont va dépendre la tache
#
# ENTREES :
#   settings_struct_dico : La structure dico contenant tout les settings
#   dependency_task_list : La liste des dépendences de taches
#   name_setting : nom du fichier contenant les settings
#
# SORTIES :
#   dependency_commands_list_string : La liste des dépendances (commandes) dont la tache va dépendre

def createDependencyList(settings_struct_dico, dependency_task_list, name_setting) :

    # Creation des dépendences
    dependency_commands_list_string = ''
    for dependency_task in dependency_task_list :
        find_dependency = False
        dependency_part_list = dependency_task.split('.')
        # Cas exemple : "220"
        if len(dependency_part_list) == 1 :
            dependency_label_task = dependency_part_list[0]
            dependency_position_task = ''
            dependency_settings_task = ''
        # Cas exemple : "220.1"
        elif len(dependency_part_list) == 2 :
            dependency_label_task = dependency_part_list[0]
            dependency_position_task = dependency_part_list[1]
            dependency_settings_task = ''
        # Cas exemple : "Settings.220.1"
        else :
            dependency_label_task = dependency_part_list[1]
            dependency_position_task = dependency_part_list[2]
            dependency_settings_task = dependency_part_list[0]

        if dependency_settings_task  == '' : # Cas simple sans nom de fichier de setting dans la dépendence
            for task in settings_struct_dico[name_setting].general.processing.taskList :
                if ((dependency_position_task == '') and (task.taskLabel == dependency_label_task)) or \
                   ((dependency_position_task != '') and (task.taskLabel == dependency_label_task) and (str(task.position) == dependency_position_task)) :
                    for taskIdTaskCommands in task.taskIdTaskCommandsList:
                        dependency_commands_list_string += str(taskIdTaskCommands) + ','
                        find_dependency = True
                    break
        else : # Cas complexe recherche dans toutes les structures settings

            for key in settings_struct_dico.keys():
                for task in settings_struct_dico[key].general.processing.taskList :
                    if ((task.taskLabel == dependency_label_task) and (str(task.position) == dependency_position_task) and (task.settings == dependency_settings_task)) :
                        for taskIdTaskCommands in task.taskIdTaskCommandsList:
                            dependency_commands_list_string += str(taskIdTaskCommands) + ','
                            find_dependency = True
                        break

        # Si auccune correspondance de dépendance n'est trouvé la dépendance doit correspondre à un fichier setting non encore traiter
        if not find_dependency :
            # Dans ce cas  on remet "dependency_task" dans la liste "dependency_commands_list_string" tel quel
            dependency_commands_list_string += "@" + dependency_task + ','

    # Supression de la virgure ',' en fin de chaine
    if dependency_commands_list_string != '':
        dependency_commands_list_string = dependency_commands_list_string[0:len(dependency_commands_list_string)-1]

    return  dependency_commands_list_string

#################################################################################
# FONCTION updateCommandsError()                                                #
#################################################################################
# ROLE :
#   Mettre à jour le fichier de commande, passer toutes les commande en erreur en cours et bloqué à faire
#
# ENTREES :
#   command_doc : le fichier contenant les commandes
#   debug : niveau de trace log

def updateCommandsError(command_doc, debug):

    try:
        # Ouverture du fichier de commande et chargement de toutes les lignes
        command_doc_work = open(command_doc,'r+')
    except NameError:
        raise NameError(cyan + "updateCommandsError : " + endC + bold + red + "Can't open file: \"" + command_doc + '\n' + endC)

    # Identification de commands comme une liste dont chaque ligne correspond à une commande
    commands_list = command_doc_work.readlines()
    command_doc_work.close()                     # Fermeture de command_doc_work

    for l in range(len(commands_list)):  # Parcours des différentes lignes de commande

        if commands_list[l] != "\n" :

            # Gestion des parametres du fichier de commande
            element_command_list = commands_list[l].split(SEPARATOR)
            state = element_command_list[0]
            id_command = element_command_list[1]
            command_to_execute = element_command_list[11]

            if state == TAG_STATE_ERROR or state == TAG_STATE_LOCK or state == TAG_STATE_RUN :
                # Modification de la ligne de commande l'etat "En_Erreur" ou "Bloque" ou "En_Cours" passe à "A_Faire"
                commands_list[l] = TAG_STATE_MAKE + SEPARATOR + str(id_command) + SEPARATOR + element_command_list[2] + SEPARATOR + element_command_list[3] + SEPARATOR + element_command_list[4] + SEPARATOR + element_command_list[5] + SEPARATOR + element_command_list[6] + SEPARATOR + element_command_list[7] + SEPARATOR + element_command_list[8] + SEPARATOR + SEPARATOR + SEPARATOR + command_to_execute

    # Supression du fichier command_doc
    removeFile(command_doc)

    # Creation d'un nouveau fichier command_doc
    for command in commands_list:  # Parcours des différentes lignes de commande
        if  command != "\n" :
            appendTextFile(command_doc, command)  # Ajout de la ligne de commande si non vide

    return

###########################################################################################################################################
# FONCTION writeCommands()                                                                                                                #
###########################################################################################################################################
# ROLE :
#   Ecriture de liste de tache python dans un fichier texte
#   Liste exhaustive des tâches disponibles ici : # https://docs.google.com/spreadsheets/d/1YKAz5VQNchUrCNuIQslcgEEn0FZRId9HK6hYbm8XRU0/edit#gid=1374414977
#
# ENTREES :
#   settings_struct_dico : La structure dico contenant tout les settings
#   id_command : compteur de commande à éxecuter
#   index_remote_ip : index courant sur la liste des machines remotes disponibles
#   task_label : label de la tâche que l'on souhaite transformer en ligne de commande
#   task_position : postion de la tache si plusieurs même tache
#   dependency_task_list : La liste des taches dont dépend la tache à exécuter
#   type_execution : défini le type d'execution immediat ou backgroud ou remote
#   error_management : Type gestion des erreurs
#   name_setting : nom du fichier contenant les settings
#   debug : niveau de trace log
#
# SORTIES :
#   id_command : incrementer du nombre de tache à executer
#   index_remote_ip : incrementer l'index de la machine remote à utiliser
#   id_task_commands_list : liste des id des commandes qui seront reelement executé
#
# INFOS :
# Les tâches sont écrites dans le fichier Commands_File.txt
#   Lorsque la ligne commence par "A_Faire"    : Commande à Faire sans conditions
#   Lorsque la ligne commence par "En_Cours"   : Commande en cours d'éxécution
#   Lorsque la ligne commence par "En_Attente" : Commande en attente d'éxécution attend la fin d'éxécution de (ou des) tache(s) dont elle dépend
#   Lorsque la ligne commence par "Bloque"     : Commande bloqué car en attente d'une tache en erreur
#   Lorsque la ligne commence par "Termine"    : Commande Terminée sans erreur
#   Lorsque la ligne commence par "En_Erreur"  : Commande fini en erreur ou dependante d'une tache en erreur

def writeCommands(settings_struct_dico, id_command, index_remote_ip, task_label, task_position, dependency_task_list, type_execution, error_management, name_setting, debug):

    # Recuper la structure courante
    settings_struct = settings_struct_dico[name_setting]

    # Mise en place des variables specifiques à writeCommands
    command_doc = settings_struct.general.processing.commandFile

    # Liste des id des commandes qui seront executés
    id_task_commands_list = []

    # Le mode d'execution de la commande
    if type_execution == '':
        mode_execution_command = TAG_ACTION_TO_MAKE_BG
    else :
        while switch(cleanSpaceText(type_execution).lower()):
           if case('immediat'):
              mode_execution_command = TAG_ACTION_TO_MAKE_NOW
              break
           if case('background'):
              mode_execution_command = TAG_ACTION_TO_MAKE_BG
              break
           if case('remote'):
              mode_execution_command = TAG_ACTION_TO_MAKE_RE
              break
           break

    # Création de la liste des dépendences
    dependency_commands_list_string = createDependencyList(settings_struct_dico, dependency_task_list, name_setting)

    # Selection de la tache à éxécuter
    while switch(task_label):

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('0'): # Tache de pause manuelle

            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list, False)

            command = call_python_action_to_make + 'read -p "Press [Enter] key to continue..." -r variable'

            endCommandUpdate(settings_struct, command_doc, command, debug, False)

            if debug >= 4:
                print(cyan + "writeCommands() : " + endC + "command : " + str(command))

            print(cyan + "writeCommands() : " + bold + green + "Pause de l'execution de la chaine de traitment" + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('1'): # Tache de print

            for comment in settings_struct.tasks.task1_Print[task_position].commentsList:
                chaine = ""
                chaine += comment.style
                chaine += comment.text

                call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list, False)

                command = call_python_action_to_make + 'echo ' + chaine

                endCommandUpdate(settings_struct, command_doc, command, debug, False)

                if debug >= 4:
                    print(cyan + "writeCommands() : " + endC + "command : " + str(command))

            print(cyan + "writeCommands() : " + bold + green + "Print de la chaine de traitment" + endC)
            break


        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('2'): # Send mail

            message = ""
            for msg in settings_struct.tasks.task2_Mail[task_position].messagesList:
                message += msg + ". "

            for receiver in settings_struct.tasks.task2_Mail[task_position].addrMailReceivesList:

                call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)

                command = call_python_action_to_make + "SendMail -adrs " + settings_struct.tasks.task2_Mail[task_position].addrMailSender + " -adrr " + receiver + " -serv " + settings_struct.tasks.task2_Mail[task_position].addrServerMail + " -port " + str(settings_struct.tasks.task2_Mail[task_position].portServerMail) + ' -subj "' + settings_struct.tasks.task2_Mail[task_position].subjectOfMessage + '" -msg "' + message + '"'

                if settings_struct.tasks.task2_Mail[task_position].passwordMailSender != "":
                    command += " -pass " + settings_struct.tasks.task2_Mail[task_position].passwordMailSender

                endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Envoi de mail" + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('3'): # Tache de delete

            for data in settings_struct.tasks.task3_Delete[task_position].dataToCleanList:

                call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list, False)

                command = call_python_action_to_make + 'rm -r ' + data

                endCommandUpdate(settings_struct, command_doc, command, debug, False)

                if debug >= 4:
                    print(cyan + "writeCommands() : " + endC + "command : " + str(command))

            print(cyan + "writeCommands() : " + bold + green + "Delete de la donnée" + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('4'): # Tache de copy

            for data_struck in settings_struct.tasks.task4_Copy[task_position].dataToCopyList:

                call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list, False)

                command = call_python_action_to_make + 'cp -Rf ' + data_struck.source + " " + data_struck.destination

                endCommandUpdate(settings_struct, command_doc, command, debug, False)

                if debug >= 4:
                    print(cyan + "writeCommands() : " + endC + "command : " + str(command))

            print(cyan + "writeCommands() : " + bold + green + "Copie de la donnée" + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('5'): # Receive FTP

            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)
            command = call_python_action_to_make + "ReceiveFTP -serv " + settings_struct.tasks.task5_ReceiveFTP[task_position].serverFtp + " -port " + str(settings_struct.tasks.task5_ReceiveFTP[task_position].portFtp) + " -login " + settings_struct.tasks.task5_ReceiveFTP[task_position].loginFtp + " -pass " + settings_struct.tasks.task5_ReceiveFTP[task_position].passwordFtp + " -path " + settings_struct.tasks.task5_ReceiveFTP[task_position].pathFtp + " -dest " + settings_struct.tasks.task5_ReceiveFTP[task_position].localPath + " -err " + settings_struct.tasks.task5_ReceiveFTP[task_position].fileError

            endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Reception par FTP" + endC)
            break


        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('6'): # Commande Shell Générique

            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list, False)

            command = call_python_action_to_make + settings_struct.tasks.task6_GenericCommand[task_position].command

            endCommandUpdate(settings_struct, command_doc, command, debug, False)

            print(cyan + "writeCommands() : " + bold + green + "Commande Generique" + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('7'): # Commande SQL Générique

            epsg =  settings_struct.general.image.epsg
            nodata_value =  settings_struct.general.image.nodataValue
            parametes_connection = "user_name='%s', password='%s', ip_host='%s', num_port='%s', schema_name='%s'"%(settings_struct.general.postgis.userName, settings_struct.general.postgis.password, settings_struct.general.postgis.serverName, str(settings_struct.general.postgis.portNumber), settings_struct.general.postgis.schemaName)

            database_name = settings_struct.general.postgis.databaseName
            encoding_file = settings_struct.general.postgis.encoding

            file_sql_python = os.path.splitext(settings_struct.general.processing.commandFile)[0] + "_GenericSql" +  str(task_position) + ".py"
            removeFile(file_sql_python)
            appendTextFileCR(file_sql_python, "#! /usr/bin/env python")
            appendTextFileCR(file_sql_python, "# -*- coding: utf-8 -*-")
            appendTextFileCR(file_sql_python, "from Lib_postgis import openConnection, closeConnection, dropDatabase, createDatabase, executeQuery, importVectorByOgr2ogr, exportVectorByOgr2ogr, importDataCSV, exportDataCSV, importRaster, exportRaster")
            appendTextFileCR(file_sql_python, "print('SQL Execution...')")

            # Les fichiers d'entrées
            for index in range (len(settings_struct.tasks.task7_GenericSql[task_position].inputFilesList)) :
                input_file = settings_struct.tasks.task7_GenericSql[task_position].inputFilesList[index].inputFile
                table_name = settings_struct.tasks.task7_GenericSql[task_position].inputFilesList[index].tableName
                #create_table = settings_struct.tasks.task7_GenericSql[task_position].inputFilesList[index].createTable
                encoding = settings_struct.tasks.task7_GenericSql[task_position].inputFilesList[index].encoding
                delimiter = "'" + settings_struct.tasks.task7_GenericSql[task_position].inputFilesList[index].delimiter + "'"
                tile_size = settings_struct.tasks.task7_GenericSql[task_position].inputFilesList[index].tile_size
                overview_factor = settings_struct.tasks.task7_GenericSql[task_position].inputFilesList[index].overview_factor
                columns_type_table_list = []
                for column_type in settings_struct.tasks.task7_GenericSql[task_position].inputFilesList[index].columnsTypeList :
                    column_type_list = column_type.split(':')
                    column_type_list[0] = cleanSpaceText(column_type_list[0])
                    column_type_list[1] = cleanSpaceText(column_type_list[1])
                    columns_type_table_list.append(column_type_list)
                if encoding == '':
                    encoding = encoding_file
                if os.path.splitext(input_file)[1].lower() == ".shp" :
                    cmd_line = "importVectorByOgr2ogr('%s', '%s', '%s', %s, epsg='%s', codage='%s')"%(database_name, input_file, table_name, parametes_connection, str(epsg), encoding)
                    appendTextFileCR(file_sql_python, cmd_line)
                elif os.path.splitext(input_file)[1].lower() == ".csv" :
                    cmd_line = "connection = openConnection('%s', %s)"%(database_name, parametes_connection)
                    appendTextFileCR(file_sql_python, cmd_line)
                    cmd_line = "importDataCSV(connection, '%s', '%s', %s, delimiter=%s)"%(input_file, table_name, columns_type_table_list, delimiter)
                    appendTextFileCR(file_sql_python, cmd_line)
                    cmd_line = "closeConnection(connection)"
                    appendTextFileCR(file_sql_python, cmd_line)
                elif os.path.splitext(input_file)[1].lower() == ".tif" :
                    cmd_line = "importRaster('%s', '%s', '%s', %s, epsg='%s', nodata_value='%s', tile_size='%s', overview_factor='%s')"%(database_name, input_file, table_name, parametes_connection, str(epsg), str(nodata_value),tile_size, overview_factor)
                    appendTextFileCR(file_sql_python, cmd_line)

            # Execution d'une sequence SQL
            if settings_struct.tasks.task7_GenericSql[task_position].commandsSqlList != [] :
                # Ouverure de la connexion postgis
                cmd_line = "connection = openConnection('%s', %s)"%(database_name, parametes_connection)
                appendTextFileCR(file_sql_python, cmd_line)

                # Les lignes de codes SQL
                for sql_line in settings_struct.tasks.task7_GenericSql[task_position].commandsSqlList:
                    cmd_line = 'executeQuery(connection, "%s")'%(sql_line)
                    appendTextFileCR(file_sql_python, cmd_line)

                # Fermeture de la connexion postgis
                cmd_line = "closeConnection(connection)"
                appendTextFileCR(file_sql_python, cmd_line)

            # Les exports de la base
            for index in range (len(settings_struct.tasks.task7_GenericSql[task_position].outputFilesList)) :
                output_file = settings_struct.tasks.task7_GenericSql[task_position].outputFilesList[index].outputFile
                table_name = settings_struct.tasks.task7_GenericSql[task_position].outputFilesList[index].tableName
                #delete_table = settings_struct.tasks.task7_GenericSql[task_position].outputFilesList[index].deleteTable
                if os.path.splitext(output_file)[1].lower() == ".shp" :
                    cmd_line = "exportVectorByOgr2ogr('%s', '%s', '%s', %s, format_type=%s)"%(database_name, output_file, table_name, parametes_connection, settings_struct.general.vector.formatVector)
                    appendTextFileCR(file_sql_python, cmd_line)
                elif os.path.splitext(output_file)[1].lower() == ".csv" :
                    cmd_line = "connection = openConnection('%s', %s)"%(database_name, parametes_connection)
                    appendTextFileCR(file_sql_python, cmd_line)
                    cmd_line = "exportDataCSV(connection, '%s', '%s', delimiter=';')"%(table_name, output_file)
                    appendTextFileCR(file_sql_python, cmd_line)
                    cmd_line = "closeConnection(connection)"
                    appendTextFileCR(file_sql_python, cmd_line)
                elif os.path.splitext(output_file)[1].lower() == ".tif" :
                    cmd_line = "exportRaster('%s', '%s', '%s', %s, format_type='%s')"%(database_name, output_file, table_name, parametes_connection)
                    appendTextFileCR(file_sql_python, cmd_line)

            # Commande
            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)
            command = call_python_action_to_make[:-3] + file_sql_python

            endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Commande Generique" + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('8'): # Etude parametrage des échantillons

            id_command, index_remote_ip, id_task_commands_list = parametricStudySamples(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, command_doc, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list, debug)

            print(cyan + "writeCommands() : " + bold + green + "Etude parametrique echantillons" + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('9'): # Etude parametrique des textures et indices

            id_command, index_remote_ip, id_task_commands_list = parametricStudyTexturesIndices(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, command_doc, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list, debug)

            print(cyan + "writeCommands() : " + bold + green + "Etude parametrique textures indices" + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('10'): # Mosaïquage et découpage selon le vecteur d'emprise de l'étude

            if settings_struct.tasks.task10_ImagesAssembly[task_position].dateSplitter == '':
                date_splitter_option  = ''
            else :
                date_splitter_option  = " -sepn " + settings_struct.tasks.task10_ImagesAssembly[task_position].dateSplitter

            if settings_struct.tasks.task10_ImagesAssembly[task_position].intraDateSplitter != '':
                date_splitter_option  += " -sepd " + settings_struct.tasks.task10_ImagesAssembly[task_position].intraDateSplitter

            if settings_struct.tasks.task10_ImagesAssembly[task_position].dateSplitter != '' and \
               settings_struct.tasks.task10_ImagesAssembly[task_position].dateNumberOfCharacters != 0 :
                date_splitter_option  += ' -z '

            dir_source_images_str = ''
            for dir_source in settings_struct.tasks.task10_ImagesAssembly[task_position].sourceImagesDirList:
                dir_source_images_str += dir_source + ' '

            # Commande
            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)
            command = call_python_action_to_make + "ImagesAssembly -pathi " + dir_source_images_str + " -e " + str(settings_struct.tasks.task10_ImagesAssembly[task_position].empriseFile) + " -o " +  str(settings_struct.tasks.task10_ImagesAssembly[task_position].outputFile) + " -posd " + str(settings_struct.tasks.task10_ImagesAssembly[task_position].datePosition) + " -nbcd " + str (settings_struct.tasks.task10_ImagesAssembly[task_position].dateNumberOfCharacters) + date_splitter_option + " -epsg " + str(settings_struct.general.image.epsg) + " -ndv " + str(settings_struct.general.image.nodataValue) +  " -raf " + settings_struct.general.raster.formatRaster + " -vef " + settings_struct.general.vector.formatVector + " -rae " + settings_struct.general.raster.extensionRaster + " -vee " + settings_struct.general.vector.extensionVector

            if settings_struct.tasks.task10_ImagesAssembly[task_position].changeZero2OtherValueBefore :
                command += " -c"

            if settings_struct.tasks.task10_ImagesAssembly[task_position].changeZero2OtherValueAfter :
                command += " -czo"

            if settings_struct.tasks.task10_ImagesAssembly[task_position].changeZero2OtherValueBefore or settings_struct.tasks.task10_ImagesAssembly[task_position].changeZero2OtherValueAfter:
                command += " -cval " + str(settings_struct.tasks.task10_ImagesAssembly[task_position].changeOtherValue)

            endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Création avec succes de la commande %s (Mosaique et decoupage) aux images de %s" %(task_label, dir_source_images_str) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('12'): # Application d'assemblage pansharpening

            # Commande
            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)
            command = call_python_action_to_make + "PansharpeningAssembly -ip " + settings_struct.tasks.task12_PansharpeningAssembly[task_position].inputPanchroFile + " -ixs " + settings_struct.tasks.task12_PansharpeningAssembly[task_position].inputXsFile + " -o " + settings_struct.tasks.task12_PansharpeningAssembly[task_position].outputFile + " -raf " + settings_struct.general.raster.formatRaster + " -rae " + settings_struct.general.raster.extensionRaster

            if settings_struct.tasks.task12_PansharpeningAssembly[task_position].interpolationMode != "":
                command += " -modi " + str(settings_struct.tasks.task12_PansharpeningAssembly[task_position].interpolationMode).lower()

            if settings_struct.tasks.task12_PansharpeningAssembly[task_position].interpolationMethod != "":
                command += " -methi " + str(settings_struct.tasks.task12_PansharpeningAssembly[task_position].interpolationMethod).lower()

            if settings_struct.tasks.task12_PansharpeningAssembly[task_position].pansharpeningMethod != "":
                command += " -methp " + str(settings_struct.tasks.task12_PansharpeningAssembly[task_position].pansharpeningMethod).lower()

            if settings_struct.tasks.task12_PansharpeningAssembly[task_position].interpolationMethod.lower() == "bco" and settings_struct.tasks.task12_PansharpeningAssembly[task_position].interpolationBco_radius != 0:
                command += " -interp.bco.r " + str(settings_struct.tasks.task12_PansharpeningAssembly[task_position].interpolationBco_radius)

            if settings_struct.tasks.task12_PansharpeningAssembly[task_position].pansharpeningMethod.lower() == "lmvm":
                if settings_struct.tasks.task12_PansharpeningAssembly[task_position].pansharpeningLmvm_xradius != 0 :
                    command += " -pansh.lmvm.rx " + str(settings_struct.tasks.task12_PansharpeningAssembly[task_position].pansharpeningLmvm_xradius)
                if settings_struct.tasks.task12_PansharpeningAssembly[task_position].pansharpeningLmvm_yradius != 0 :
                    command += " -pansh.lmvm.ry " + str(settings_struct.tasks.task12_PansharpeningAssembly[task_position].pansharpeningLmvm_yradius)

            if settings_struct.tasks.task12_PansharpeningAssembly[task_position].pansharpeningMethod.lower() == "bayes":
                if settings_struct.tasks.task12_PansharpeningAssembly[task_position].pansharpeningBayes_lambda != 0.0 :
                    command += " -pansh.bayes.lb " + str(settings_struct.tasks.task12_PansharpeningAssembly[task_position].pansharpeningBayes_lambda)
                if settings_struct.tasks.task12_PansharpeningAssembly[task_position].pansharpeningBayes_scoef != 0.0 :
                    command += " -pansh.bayes.s " + str(settings_struct.tasks.task12_PansharpeningAssembly[task_position].pansharpeningBayes_scoef)

            if settings_struct.general.processing.ram != 0:
                command += " -ram " + str(settings_struct.general.processing.ram)

            endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Création avec succes de la commande %s (Application d'assemblage pansharpening) pour l'image %s" %(task_label, str(settings_struct.tasks.task12_PansharpeningAssembly[task_position].outputFile)) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('20'): # Compression d'image

            # Commande
            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)
            command = call_python_action_to_make + "ImageCompression -i " + settings_struct.tasks.task20_ImageCompression[task_position].inputFile + " -cp DEFLATE -pr 2 -zl 2 -mn 0 -mx 0.1 " +  " -raf " + settings_struct.general.raster.formatRaster + " -rae " + settings_struct.general.raster.extensionRaster

            if settings_struct.tasks.task20_ImageCompression[task_position].outputFile8b != "" :
                command += " -o8b " + settings_struct.tasks.task20_ImageCompression[task_position].outputFile8b

            if settings_struct.tasks.task20_ImageCompression[task_position].outputFile8bCompress != "" :
                command += " -ocp " + settings_struct.tasks.task20_ImageCompression[task_position].outputFile8bCompress

            if settings_struct.tasks.task20_ImageCompression[task_position].optimize8bits :
                command += " -opt8b"

            endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Creation avec succes de la commande %s compression d'image %s" %(task_label, settings_struct.tasks.task20_ImageCompression[task_position].inputFile) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('30'): # Calcul de textures et indices

            # Preparation des listes de strings
            channel_order_list_str = ""
            for channel_order in settings_struct.general.image.channelOrderList:
                channel_order_list_str += channel_order + ' '

            indices_list_str = ""
            for indice in settings_struct.tasks.task30_NeoChannelsComputation[task_position].indicesList:
                indices_list_str += indice + ' '

            # Pour chaque image temporelle
            images_for_neochannel_computation_list_str = ""
            for image_for_neochannel_computation in settings_struct.tasks.task30_NeoChannelsComputation[task_position].inputFilesList:
                images_for_neochannel_computation_list_str += image_for_neochannel_computation + ' '

                # Calcul des textures

                # Pour chaque cannal demandé de l'image
                for channel in settings_struct.tasks.task30_NeoChannelsComputation[task_position].channelsList:

                    # Pour Chaque famille de texture
                    for texture in settings_struct.tasks.task30_NeoChannelsComputation[task_position].textureFamilyList:

                        # Pour chaque valeur de rayon
                        for radius in settings_struct.tasks.task30_NeoChannelsComputation[task_position].radiusList:

                            # Commande
                            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)
                            command = call_python_action_to_make +  "NeoChannelsComputation -i " + image_for_neochannel_computation + " -patho " + settings_struct.tasks.task30_NeoChannelsComputation[task_position].outputPath + " -chan " + channel + " -fam " + texture + " -rad " + radius + " -rae " + settings_struct.general.raster.extensionRaster

                            if channel_order_list_str != "" :
                                command += " -chao " + channel_order_list_str

                            if settings_struct.tasks.task30_NeoChannelsComputation[task_position].binNumber != 0 :
                                command += " -bin " + str(settings_struct.tasks.task30_NeoChannelsComputation[task_position].binNumber)

                            endCommandUpdate(settings_struct, command_doc, command, debug)

                # Calcul des indices
                if indices_list_str != "" :
                    call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)
                    command = call_python_action_to_make +  "NeoChannelsComputation -i " + image_for_neochannel_computation + " -patho " + settings_struct.tasks.task30_NeoChannelsComputation[task_position].outputPath + " -ind " + indices_list_str

                    if channel_order_list_str != "" :
                        command += " -chao " + channel_order_list_str

                    endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Création avec succes de la commande %s (calcul de neocanaux) aux images %s" %(task_label, images_for_neochannel_computation_list_str) + endC)
            break


       # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('35'): # Application creation de MNH

            # Preparation des listes des fichiers bd
            bd_vector_input_build_list_str = ""
            bd_vector_input_road_list_str = ""
            bd_buff_list_str = ""
            bd_sql_list_str = ""
            sql_expression = False

            for database_file_struct in settings_struct.tasks.task35_MnhCreation[task_position].dataBaseRoadFileList :
                bd_vector_input_road_list_str += database_file_struct.inputVector + " "
                bd_buff_list_str += str(database_file_struct.bufferValue) + " "
                if database_file_struct.sqlExpression != "" :
                    sql_expression = True
                bd_sql_list_str += '"' + database_file_struct.sqlExpression + '"' + ":"
            bd_sql_list_str = bd_sql_list_str[0:len(bd_sql_list_str)-1]

            for database_file in settings_struct.tasks.task35_MnhCreation[task_position].dataBaseBuildFilesList :
                bd_vector_input_build_list_str += database_file + " "

            # Commande
            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)
            command = call_python_action_to_make + "MnhCreation -is " + settings_struct.tasks.task35_MnhCreation[task_position].inputMnsFile + " -it " + settings_struct.tasks.task35_MnhCreation[task_position].inputMntFile + " -v " + settings_struct.tasks.task35_MnhCreation[task_position].inputVector + " -o " + settings_struct.tasks.task35_MnhCreation[task_position].outputMnhFile + " -auto -epsg " + str(settings_struct.general.image.epsg) + " -ndv " + str(settings_struct.general.image.nodataValue) + " -bias " + str(settings_struct.tasks.task35_MnhCreation[task_position].bias) + " -simp " + str(settings_struct.tasks.task35_MnhCreation[task_position].simplificationPolygon) + " -raf " + settings_struct.general.raster.formatRaster + " -vef " + settings_struct.general.vector.formatVector + " -rae " + settings_struct.general.raster.extensionRaster + " -vee " + settings_struct.general.vector.extensionVector

            if settings_struct.tasks.task35_MnhCreation[task_position].inputFilterFile != "":
                command += " -ithr " + settings_struct.tasks.task35_MnhCreation[task_position].inputFilterFile + " -thrval " + str(settings_struct.tasks.task35_MnhCreation[task_position].thresholdFilterFile)

            if settings_struct.tasks.task35_MnhCreation[task_position].interpolationMode != "":
                command += " -modi " + str(settings_struct.tasks.task35_MnhCreation[task_position].interpolationMode).lower()

            if settings_struct.tasks.task35_MnhCreation[task_position].interpolationMethod != "":
                command += " -methi " + str(settings_struct.tasks.task35_MnhCreation[task_position].interpolationMethod).lower()

            if settings_struct.tasks.task35_MnhCreation[task_position].interpolationMethod.lower() == "bco" and settings_struct.tasks.task35_MnhCreation[task_position].interpolationBco_radius != 0:
                command += " -interp.bco.r " + str(settings_struct.tasks.task35_MnhCreation[task_position].interpolationBco_radius)

            if bd_vector_input_road_list_str != "":
                command += " -ibdrl " + bd_vector_input_road_list_str

            if bd_buff_list_str != "":
                command += " -bufrl " + bd_buff_list_str

            if sql_expression:
                if six.PY2:
                    command += " -sqlrl " + bd_sql_list_str.decode("latin1")
                    command = command.encode("utf-8")
                else :
                    command += " -sqlrl " + bd_sql_list_str

            if bd_vector_input_build_list_str != "":
                command += " -ibdbl " + bd_vector_input_build_list_str + " -deltah " + str(settings_struct.tasks.task35_MnhCreation[task_position].thresholdDeltaH)

            if settings_struct.general.processing.ram != 0:
                command += " -ram " + str(settings_struct.general.processing.ram)

            endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Création avec succes de la commande %s (Application creation de MNH) pour l'image Mnh %s" %(task_label, str(settings_struct.tasks.task35_MnhCreation[task_position].outputMnhFile)) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('40'): # Concatenation de differents canaux, normalisation éventuelle, réduction de dimension éventuelle.

            # Preparation des listes de strings
            image_for_concatenation_input_str = ""
            for image_for_concatenation in settings_struct.tasks.task40_ChannelsConcatenantion[task_position].inputFilesList:
                image_for_concatenation_input_str += image_for_concatenation + ' '

            # Commande
            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)
            command = call_python_action_to_make + "ChannelsConcatenation -il " + image_for_concatenation_input_str

            if settings_struct.tasks.task40_ChannelsConcatenantion[task_position].concatenation.stackConcatenation :
                command += " -os " + settings_struct.tasks.task40_ChannelsConcatenantion[task_position].concatenation.outputFile

            if settings_struct.tasks.task40_ChannelsConcatenantion[task_position].normalization.stackNormalization :
                command += " -on " + settings_struct.tasks.task40_ChannelsConcatenantion[task_position].normalization.outputFile

            if settings_struct.tasks.task40_ChannelsConcatenantion[task_position].reduction.stackReduction :
                command += " -oa " + settings_struct.tasks.task40_ChannelsConcatenantion[task_position].reduction.outputFile

                if settings_struct.tasks.task40_ChannelsConcatenantion[task_position].reduction.method.lower() == "pca":
                    command += " -redce.meth PCA -redce.nbcp " + str(settings_struct.tasks.task40_ChannelsConcatenantion[task_position].reduction.maxBandNumber)

                if settings_struct.tasks.task40_ChannelsConcatenantion[task_position].reduction.method.lower() == "napca":
                    command += " -redce.meth NAPCA -redce.nbcp " + str(settings_struct.tasks.task40_ChannelsConcatenantion[task_position].reduction.maxBandNumber) + " -redce.radi " + str(settings_struct.tasks.task40_ChannelsConcatenantion[task_position].reduction.napcaRadius)

                if settings_struct.tasks.task40_ChannelsConcatenantion[task_position].reduction.method.lower() == "maf":
                    command += " -redce.meth MAF -redce.nbcp " + str(settings_struct.tasks.task40_ChannelsConcatenantion[task_position].reduction.maxBandNumber)

                if settings_struct.tasks.task40_ChannelsConcatenantion[task_position].reduction.method.lower() == "ica":
                    command += " -redce.meth ICA -redce.nbcp " + str(settings_struct.tasks.task40_ChannelsConcatenantion[task_position].reduction.maxBandNumber) + " -redce.iter " + str(settings_struct.tasks.task40_ChannelsConcatenantion[task_position].reduction.icaIterations) + " -redce.incr " + str(settings_struct.tasks.task40_ChannelsConcatenantion[task_position].reduction.icaIncrement)

                if settings_struct.tasks.task40_ChannelsConcatenantion[task_position].reduction.normalizationReduce :
                    command += " -redce.norm "

            endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Création avec succes de la commande %s (concatenation neocanaux) des image %s" %(task_label, image_for_concatenation_input_str) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('50'): # Creation d'échantillons d'apprentissage à partir de BD exogènes

            for class_macro_sample_struct in settings_struct.tasks.task50_MacroSampleCreation[task_position].classMacroSampleList:

                bd_vector_input_list_str = ""
                bd_buff_list_str = ""
                bd_sql_list_str = ""
                sql_expression = False

                for database_file_struct in class_macro_sample_struct.dataBaseFileList:
                    bd_vector_input_list_str += database_file_struct.inputVector + " "
                    bd_buff_list_str += str(database_file_struct.bufferValue) + " "
                    if database_file_struct.sqlExpression != "" :
                        sql_expression = True
                    bd_sql_list_str += '"' + database_file_struct.sqlExpression + '"' + ":"
                bd_sql_list_str = bd_sql_list_str[0:len(bd_sql_list_str)-1]

                # Commande
                call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)
                command = call_python_action_to_make + "MacroSamplesCreation " + " -ibdl " + bd_vector_input_list_str + " -bufl " + bd_buff_list_str + " -macro " + class_macro_sample_struct.name + " -simp " + str(settings_struct.tasks.task50_MacroSampleCreation[task_position].simplificationPolygon) + " -vef " + settings_struct.general.vector.formatVector + " -vee " + settings_struct.general.vector.extensionVector

                if settings_struct.tasks.task50_MacroSampleCreation[task_position].inputFile != "":
                    command += " -i " + settings_struct.tasks.task50_MacroSampleCreation[task_position].inputFile
                if settings_struct.tasks.task50_MacroSampleCreation[task_position].inputVector != "":
                    command += " -v " + settings_struct.tasks.task50_MacroSampleCreation[task_position].inputVector
                if class_macro_sample_struct.outputVector != "":
                    command += " -ov " + class_macro_sample_struct.outputVector
                if class_macro_sample_struct.outputFile != "":
                    command += " -or " + class_macro_sample_struct.outputFile
                if sql_expression:
                    if six.PY2:
                        command += " -sql " + bd_sql_list_str.decode("latin1")
                        command = command.encode("utf-8")
                    else :
                        command += " -sql " + bd_sql_list_str

                endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Création avec succes de la commande %s (création d'échantillons d'apprentissage) à l'image %s" %(task_label, str(settings_struct.tasks.task50_MacroSampleCreation[task_position].inputFile)) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('60'): # Création d'un masque binaire à partir des vecteurs d'apprentissage macro au regard de l'emprise d'une image

            for class_macro_sample_struct in settings_struct.tasks.task60_MaskCreation[task_position].classMacroSampleList:

                # Commande
                call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)
                command = call_python_action_to_make + "MaskCreation -i " + settings_struct.tasks.task60_MaskCreation[task_position].inputFile + " -v " + class_macro_sample_struct.inputVector + " -o " + class_macro_sample_struct.outputFile

                endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Création avec succes de la commande %s (creation d'un masque binaire) à l'image %s" %(task_label, str(settings_struct.tasks.task60_MaskCreation[task_position].inputFile)) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('70_RA'): # Extraction sur la zone d echantillons d'apprentissages calcules sur un territoire global (Utilisation production RA)

            for class_macro_sample_struct in settings_struct.tasks.task70_RA_MacroSampleCutting[task_position].classMacroSampleList:

                # Commande
                call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)
                command = call_python_action_to_make + "MacroSamplesCutting -i " + class_macro_sample_struct.inputFile + " -v " +  settings_struct.tasks.task70_RA_MacroSampleCutting[task_position].inputVector + " -o " + class_macro_sample_struct.outputFile + " -epsg " + str(settings_struct.general.image.epsg) + " -ndv " + str(settings_struct.general.image.nodataValue) +  " -raf " + settings_struct.general.raster.formatRaster + " -vef " + settings_struct.general.vector.formatVector + " -rae " + settings_struct.general.raster.extensionRaster

                if settings_struct.tasks.task70_RA_MacroSampleCutting[task_position].superposition: # Cas où on vérifie la superposition géométrique avec l'image satellite
                   command += " -spos"
                   command += " -r "
                   command += settings_struct.tasks.task70_RA_MacroSampleCutting[task_position].referenceImage

                endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Création avec succes de la commande %s (Decoupage des echantillons d'apprentissage par l emprise %s" %(task_label, str(settings_struct.tasks.task70_RA_MacroSampleCutting[task_position].inputVector)) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('80'): # Nettoyage d'echantillons d'apprentissage au regard de seuils sur neocanaux

            for class_macro_sample_struct in settings_struct.tasks.task80_MacroSampleAmelioration[task_position].classMacroSampleList:

                correction_images_input_list_str = ''
                treatment_rules_for_the_macroclasse_str = ''

                for correction_file_struct in class_macro_sample_struct.correctionFilesList:
                    correction_images_input_list_str += correction_file_struct.correctionFile + ' '
                    treatment_rules_for_the_macroclasse_str += correction_file_struct.name + ',' + str(correction_file_struct.thresholdMin) + ',' + str(correction_file_struct.thresholdMax) + ',' + str(correction_file_struct.filterSizeForZero) + ',' + str(correction_file_struct.filterSizeForOne) + ',' + str(correction_file_struct.operatorFusion) + ' '

                # Commande
                call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)
                command = call_python_action_to_make + "MacroSamplesAmelioration -i " + class_macro_sample_struct.inputFile + " -o " +  class_macro_sample_struct.outputFile + " -cil " + correction_images_input_list_str + " -treat " + treatment_rules_for_the_macroclasse_str + " -macro " + class_macro_sample_struct.name  + " -rae " + settings_struct.general.raster.extensionRaster

                endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Création avec succes de la commande %s (Nettoyages des echantillons d'apprentissage selon les regles) " %(task_label) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('90'): # Sous echantillonage via un kmeans

            macro_classes_cleaned_mask_list_str = ""
            micro_classes_mask_list_str = ""
            centroids_list_str = ""
            macroclass_sampling_list_str = ""
            macroclass_labels_list_str = ""

            for class_macro_sample_struct in settings_struct.tasks.task90_KmeansMaskApplication[task_position].classMacroSampleList:
                macro_classes_cleaned_mask_list_str += class_macro_sample_struct.inputFile + ' '
                micro_classes_mask_list_str += class_macro_sample_struct.outputFile + ' '
                centroids_list_str += class_macro_sample_struct.outputCentroidFile + ' '
                macroclass_sampling_list_str += str(class_macro_sample_struct.sampling) + ' '
                macroclass_labels_list_str += str(class_macro_sample_struct.label) + ' '

            # Commande
            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)
            command = call_python_action_to_make + "KmeansMaskApplication -i " +  settings_struct.tasks.task90_KmeansMaskApplication[task_position].inputFile + " -o " + settings_struct.tasks.task90_KmeansMaskApplication[task_position].outputFile + " -t " + settings_struct.tasks.task90_KmeansMaskApplication[task_position].proposalTable + " -ml " + macro_classes_cleaned_mask_list_str + " -ol " + micro_classes_mask_list_str + " -cl " + centroids_list_str + " -msl " + macroclass_sampling_list_str + " -mll " + macroclass_labels_list_str + " -kmp.it " + str(settings_struct.tasks.task90_KmeansMaskApplication[task_position].iterations) + " -kmp.pr " + str(settings_struct.tasks.task90_KmeansMaskApplication[task_position].propPixels) + " -kmp.sz " + str(settings_struct.tasks.task90_KmeansMaskApplication[task_position].sizeTraining) + " -npt " + str(settings_struct.tasks.task90_KmeansMaskApplication[task_position].minNumberTrainingSize) + " -rcmc " + str(settings_struct.tasks.task90_KmeansMaskApplication[task_position].rateCleanMicroclass) + " -ndv " + str(settings_struct.general.image.nodataValue) + " -rae " + settings_struct.general.raster.extensionRaster

            if settings_struct.tasks.task90_KmeansMaskApplication[task_position].rand > 0:
                command += " -rand " + str(settings_struct.tasks.task90_KmeansMaskApplication[task_position].rand)

            if settings_struct.general.processing.ram != 0:
                command += " -ram " + str(settings_struct.general.processing.ram)

            endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Création avec succes de la commande %s (Application du kmeans) à l'image %s pour les macroclasses %s" %(task_label, str(settings_struct.tasks.task90_KmeansMaskApplication[task_position].inputFile), macroclass_labels_list_str) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('100'): # Vectorisation et nettoyage des polygones d'apprentissage

            micro_classes_mask_list_str = ""
            raster_erode_list_str = ""
            buffer_size_list_str = ""
            buffer_approximate_list_str = ""
            minimal_area_list_str = ""
            simplification_tolerance_list_str = ""

            for input_file_struct in settings_struct.tasks.task100_MicroSamplePolygonization[task_position].inputFileList:
                micro_classes_mask_list_str += input_file_struct.inputFile + ' '
                raster_erode_list_str += str(input_file_struct.rasterErode) + ' '
                buffer_size_list_str += str(input_file_struct.bufferSize) + ' '
                buffer_approximate_list_str += str(input_file_struct.bufferApproximate) + ' '
                minimal_area_list_str += str(input_file_struct.minimalArea) + ' '
                simplification_tolerance_list_str += str(input_file_struct.simplificationTolerance) + ' '

            # Commande
            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)
            command = call_python_action_to_make + "MicroSamplePolygonization -il " + micro_classes_mask_list_str + " -o " + settings_struct.tasks.task100_MicroSamplePolygonization[task_position].outputFile + " -t " + settings_struct.tasks.task100_MicroSamplePolygonization[task_position].proposalTable + " -ero " + raster_erode_list_str + " -umc " + str(settings_struct.tasks.task100_MicroSamplePolygonization[task_position].umc) + " -ts " + str(settings_struct.tasks.task100_MicroSamplePolygonization[task_position].tileSize) + " -bsl " + buffer_size_list_str + " -bal " + buffer_approximate_list_str + " -mal " + minimal_area_list_str + " -stl " + simplification_tolerance_list_str + " -rcmc " + str(settings_struct.tasks.task100_MicroSamplePolygonization[task_position].rateCleanMicroclass) + " -sgf GEOMETRY -vgt POLYGON " + " -pe UTF-8 -epsg " + str(settings_struct.general.image.epsg) + " -col " + str(settings_struct.general.classification.columnName) + " -vef " + settings_struct.general.vector.formatVector + " -rae " + settings_struct.general.raster.extensionRaster + " -vee " + settings_struct.general.vector.extensionVector

            endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Création avec succes de la commande %s (Vectorisation et nettoyage des polygones) au fichier vecteur %s" %(task_label, str(settings_struct.tasks.task100_MicroSamplePolygonization[task_position].outputFile)) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('110'): # Réaffectation des micro classes vecteur d'apprentissage en fonction de la table de proposition

            # Commande
            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)
            command = call_python_action_to_make + "ClassReallocationVector -v " + settings_struct.tasks.task110_ClassReallocationVector[task_position].inputFile + " -t " + settings_struct.tasks.task110_ClassReallocationVector[task_position].proposalTable + " -o " + settings_struct.tasks.task110_ClassReallocationVector[task_position].outputFile + " -id " + str(settings_struct.general.classification.columnName) + " -vef " + settings_struct.general.vector.formatVector

            endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Création avec succes de la commande %s (proposition de réaffectation des micro classes) au fichier vecteur %s" %(task_label, str(settings_struct.tasks.task110_ClassReallocationVector[task_position].outputFile)) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('115'): # Sélection des échantillons points par micro classes

            ratio_per_class_dico_str = ""
            for ratio_class_struct in settings_struct.tasks.task115_SampleSelectionRaster[task_position].ratioPerClassList:
                ratio_per_class_dico_str += str(ratio_class_struct.label) + "," + str(ratio_class_struct.classRatio) + " "

            input_file_list_str = ""
            for inputFile in settings_struct.tasks.task115_SampleSelectionRaster[task_position].inputFilesList:
                input_file_list_str += inputFile + " "

            # Commande
            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)
            command = call_python_action_to_make + "SampleSelectionRaster -il " + input_file_list_str + " -s " + settings_struct.tasks.task115_SampleSelectionRaster[task_position].inputSample + " -o " + settings_struct.tasks.task115_SampleSelectionRaster[task_position].outputVector + " -t " + settings_struct.tasks.task115_SampleSelectionRaster[task_position].outputStatisticsTable + " -st " + settings_struct.tasks.task115_SampleSelectionRaster[task_position].samplerStrategy + " -srf " + str(settings_struct.tasks.task115_SampleSelectionRaster[task_position].selectRatioFloor) + " -col " + str(settings_struct.general.classification.columnName) + " -epsg " + str(settings_struct.general.image.epsg) + " -ndv " + str(settings_struct.general.image.nodataValue) + " -vef " + settings_struct.general.vector.formatVector + " -vee " + settings_struct.general.vector.extensionVector

            if ratio_per_class_dico_str != "":
                command += " -rpc " + ratio_per_class_dico_str

            if settings_struct.tasks.task115_SampleSelectionRaster[task_position].rand > 0:
                command += " -rand " + str(settings_struct.tasks.task115_SampleSelectionRaster[task_position].rand)

            if settings_struct.general.processing.ram != 0:
                command += " -ram " + str(settings_struct.general.processing.ram)

            endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Création avec succes de la commande %s (échantillons points des micro classes) au fichier vecteur %s" %(task_label, str(settings_struct.tasks.task115_SampleSelectionRaster[task_position].outputVector)) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('120'): # Application d'une classification supervisee

            input_file_list_str = ""
            for inputFile in settings_struct.tasks.task120_SupervisedClassification[task_position].inputFilesList:
                input_file_list_str += inputFile + " "

            # Commande
            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)
            command = call_python_action_to_make + "SupervisedClassification -il " + input_file_list_str + " -o " + settings_struct.tasks.task120_SupervisedClassification[task_position].outputFile + " -c " + settings_struct.tasks.task120_SupervisedClassification[task_position].confidenceOutputFile + " -sm " + str(settings_struct.tasks.task120_SupervisedClassification[task_position].samplerMode) + " -per " + str(settings_struct.tasks.task120_SupervisedClassification[task_position].periodicJitter) + " -fc " + str(settings_struct.general.classification.columnName) + " -cm " + settings_struct.tasks.task120_SupervisedClassification[task_position].method.lower() + " -ndv " + str(settings_struct.general.image.nodataValue) + " -raf " + settings_struct.general.raster.formatRaster + " -vee " + settings_struct.general.vector.extensionVector

            if settings_struct.tasks.task120_SupervisedClassification[task_position].inputVector != "":
                command += " -v " + str(settings_struct.tasks.task120_SupervisedClassification[task_position].inputVector)

            if settings_struct.tasks.task120_SupervisedClassification[task_position].inputSample != "":
                command += " -s " + str(settings_struct.tasks.task120_SupervisedClassification[task_position].inputSample)

            if settings_struct.tasks.task120_SupervisedClassification[task_position].outputModelFile != "":
                command += " -mo " + str(settings_struct.tasks.task120_SupervisedClassification[task_position].outputModelFile)

            if settings_struct.tasks.task120_SupervisedClassification[task_position].inputModelFile != "":
                command += " -mi " + str(settings_struct.tasks.task120_SupervisedClassification[task_position].inputModelFile)

            if settings_struct.tasks.task120_SupervisedClassification[task_position].method.lower() == "svm":
                command += " -svm.k " + str(settings_struct.tasks.task120_SupervisedClassification[task_position].svn_kernel)

            if settings_struct.tasks.task120_SupervisedClassification[task_position].method.lower() == "rf":
                command += " -rf.depth " + str(settings_struct.tasks.task120_SupervisedClassification[task_position].rf_dephTree) + " -rf.min " + str(settings_struct.tasks.task120_SupervisedClassification[task_position].rf_sampleMin) + " -rf.crit " + str(settings_struct.tasks.task120_SupervisedClassification[task_position].rf_terminCriteria) + " -rf.clust " + str(settings_struct.tasks.task120_SupervisedClassification[task_position].rf_cluster) + " -rf.size " + str(settings_struct.tasks.task120_SupervisedClassification[task_position].rf_sizeFeatures) + " -rf.num " + str(settings_struct.tasks.task120_SupervisedClassification[task_position].rf_numTree) + " -rf.obb " + str(settings_struct.tasks.task120_SupervisedClassification[task_position].rf_obbError)

            if settings_struct.general.processing.ram != 0:
                command += " -ram " + str(settings_struct.general.processing.ram)

            endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Création avec succes de la commande %s (Application d'une classification supervisee) à l'image %s" %(task_label, input_file_list_str) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('125'): # Application d'une classification par reseu de neurone


            # Commande
            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)

            command = call_python_action_to_make + "NeuralNetworkClassification -i " + settings_struct.tasks.task125_DeepLearningClassification[task_position].inputFile + " -sg " + str(settings_struct.tasks.task125_DeepLearningClassification[task_position].gridSize) + " -nc " + str(settings_struct.tasks.task125_DeepLearningClassification[task_position].numberClass) + " -nm " + settings_struct.tasks.task125_DeepLearningClassification[task_position].networkType.lower() + " -nn.b " + str(settings_struct.tasks.task125_DeepLearningClassification[task_position].nn_batch) + " -nn.ncf " + str(settings_struct.tasks.task125_DeepLearningClassification[task_position].nn_numberConvFilter) + " -nn.ks " + str(settings_struct.tasks.task125_DeepLearningClassification[task_position].nn_kernelSize) + " -nn.tiob " + str(settings_struct.tasks.task125_DeepLearningClassification[task_position].nn_inOneBlock) + " -nn.vs " + str(settings_struct.tasks.task125_DeepLearningClassification[task_position].nn_rateValidation) + " -nn.ne " + str(settings_struct.tasks.task125_DeepLearningClassification[task_position].nn_numberEpoch) + " -nn.esm " + settings_struct.tasks.task125_DeepLearningClassification[task_position].nn_earlyStoppingMonitor + " -nn.esp " + str(settings_struct.tasks.task125_DeepLearningClassification[task_position].nn_earlyStoppingPatience) + " -nn.esmd " + str(settings_struct.tasks.task125_DeepLearningClassification[task_position].nn_earlyStoppingMinDelta) + " -nn.rlrm " + settings_struct.tasks.task125_DeepLearningClassification[task_position].nn_reduceLearningRateMonitor + " -nn.rlrf " + str(settings_struct.tasks.task125_DeepLearningClassification[task_position].nn_reduceLearningRateFactor) + " -nn.rlrp " + str(settings_struct.tasks.task125_DeepLearningClassification[task_position].nn_reduceLearningRatePatience) + " -nn.rlrmlr " + str(settings_struct.tasks.task125_DeepLearningClassification[task_position].nn_reduceLearningRateMinLR) + " -ndv " + str(settings_struct.general.image.nodataValue) + " -epsg " + str(settings_struct.general.image.epsg) +  " -raf " + settings_struct.general.raster.formatRaster + " -vef " + settings_struct.general.vector.formatVector + " -rae " + settings_struct.general.raster.extensionRaster + " -vee " + settings_struct.general.vector.extensionVector

            if settings_struct.tasks.task125_DeepLearningClassification[task_position].outputFile != "":
                command += " -o " + str(settings_struct.tasks.task125_DeepLearningClassification[task_position].outputFile)

            if settings_struct.tasks.task125_DeepLearningClassification[task_position].inputVector != "":
                command += " -v " + str(settings_struct.tasks.task125_DeepLearningClassification[task_position].inputVector)

            if settings_struct.tasks.task125_DeepLearningClassification[task_position].inputSample != "":
                command += " -ti " + str(settings_struct.tasks.task125_DeepLearningClassification[task_position].inputSample)

            if settings_struct.tasks.task125_DeepLearningClassification[task_position].outputModelFile != "":
                command += " -mo " + str(settings_struct.tasks.task125_DeepLearningClassification[task_position].outputModelFile)

            if settings_struct.tasks.task125_DeepLearningClassification[task_position].inputModelFile != "":
                command += " -mi " + str(settings_struct.tasks.task125_DeepLearningClassification[task_position].inputModelFile)

            if settings_struct.tasks.task125_DeepLearningClassification[task_position].overflowSize > 0:
                command += " -deb " + str(settings_struct.tasks.task125_DeepLearningClassification[task_position].overflowSize)

            if settings_struct.tasks.task125_DeepLearningClassification[task_position].increaseSample :
                command += " -at "

            if settings_struct.tasks.task125_DeepLearningClassification[task_position].computeMode.lower() == "gpu" :
                command += " -ugc  -igpu " + str(settings_struct.tasks.task125_DeepLearningClassification[task_position].idGpuCard)

            if settings_struct.tasks.task125_DeepLearningClassification[task_position].rand > 0:
                command += " -rand " + str(settings_struct.tasks.task125_DeepLearningClassification[task_position].rand)

            if settings_struct.general.processing.ram != 0:
                command += " -ram " + str(settings_struct.general.processing.ram)

            endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Création avec succes de la commande %s (Application d'une classification neuronale) à l'image %s" %(task_label, str(settings_struct.tasks.task125_DeepLearningClassification[task_position].inputFile)) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('130'): # Post traitements des micro-classes de la classification à partir de donnees raster deja traités par ailleurs

            # Preparation des parametres
            pt_micro_class_list_str = ""
            idx = 1
            for input_file_struct in settings_struct.tasks.task130_PostTraitementsRaster[task_position].inputCorrectionFileList:
                input_file_str = input_file_struct.inputFile
                threshold_min_str = str(input_file_struct.thresholdMin)
                threshold_max_str = str(input_file_struct.thresholdMax)
                buffer_to_apply_str = str(input_file_struct.bufferToApply)
                in_or_out_str = input_file_struct.inOrOut
                class_to_replace_str = str(input_file_struct.classToReplace)
                replacement_class_str = str(input_file_struct.replacementClass)
                pt_micro_class_list_str += 'pt' + str(idx) + ':' + input_file_str + ',' + threshold_min_str + ',' + threshold_max_str + ',' + buffer_to_apply_str + ',' + in_or_out_str + ',' + class_to_replace_str + ',' + replacement_class_str + ' '
                idx+=1

            # Commande
            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)
            command = call_python_action_to_make + "PostTraitementsRaster -i " + settings_struct.tasks.task130_PostTraitementsRaster[task_position].inputFile + " -o " + settings_struct.tasks.task130_PostTraitementsRaster[task_position].outputFile + " -ptrd " + pt_micro_class_list_str + " -raf " + settings_struct.general.raster.formatRaster + " -vef " + settings_struct.general.vector.formatVector + " -rae " + settings_struct.general.raster.extensionRaster

            if settings_struct.tasks.task130_PostTraitementsRaster[task_position].inputVector != "":
                command += " -v " + str(settings_struct.tasks.task130_PostTraitementsRaster[task_position].inputVector)

            endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Création avec succes de la commande %s (proposition de réaffectation des micro classes) à l'image %s" %(task_label, str(settings_struct.tasks.task130_PostTraitementsRaster[task_position].inputFile)) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('140'): # Sous echantillonnage des micro-classes

            # Commande
            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)
            command = call_python_action_to_make + "SpecificSubSampling -i " + settings_struct.tasks.task140_SpecificSubSampling[task_position].inputFile + " -c " + settings_struct.tasks.task140_SpecificSubSampling[task_position].inputClassifFile + " -o " + settings_struct.tasks.task140_SpecificSubSampling[task_position].outputFile  +  " -t " + settings_struct.tasks.task140_SpecificSubSampling[task_position].proposalTable + " -nss " + str(settings_struct.tasks.task140_SpecificSubSampling[task_position].subSamplingNumber) + " -npt " + str(settings_struct.tasks.task140_SpecificSubSampling[task_position].minNumberTrainingSize) + " -ndv " + str(settings_struct.general.image.nodataValue) + " -rae " + settings_struct.general.raster.extensionRaster

            if settings_struct.tasks.task140_SpecificSubSampling[task_position].rand > 0:
                command += " -rand " + str(settings_struct.tasks.task140_SpecificSubSampling[task_position].rand)

            if settings_struct.general.processing.ram != 0:
                command += " -ram " + str(settings_struct.general.processing.ram)

            endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Création avec succes de la commande %s (Sous echantillonnage des micro-classes) à l'image %s" %(task_label, str(settings_struct.tasks.task140_SpecificSubSampling[task_position].inputClassifFile)) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('150'): # Réaffectation des micro classes raster en fonction de la table de proposition

            # Commande
            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)
            command = call_python_action_to_make + "ClassReallocationRaster -i " + settings_struct.tasks.task150_ClassRealocationRaster[task_position].inputFile + " -t " + settings_struct.tasks.task150_ClassRealocationRaster[task_position].proposalTable + " -o " + settings_struct.tasks.task150_ClassRealocationRaster[task_position].outputFile

            endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Création avec succes de la commande %s (proposition de réaffectation des micro classes) à l'image %s" %(task_label, str(settings_struct.tasks.task150_ClassRealocationRaster[task_position].inputFile)) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('160'): # Fusion de classes de classification

            # Commande
            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)
            command = call_python_action_to_make + "MicroClassesFusion -i " + settings_struct.tasks.task160_MicroclassFusion[task_position].inputFile + " -o " + settings_struct.tasks.task160_MicroclassFusion[task_position].outputFile + " -exp " + '"' + settings_struct.tasks.task160_MicroclassFusion[task_position].expression + '"'

            endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Création avec succes de la commande %s (Fusion des micro-classes) à l'image %s" %(task_label, str(settings_struct.tasks.task160_MicroclassFusion[task_position].inputFile)) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('170'): # Filtre majoritaire de la classification

            # Commande
            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)
            command = call_python_action_to_make + "MajorityFilter -i " + settings_struct.tasks.task170_MajorityFilter[task_position].inputFile + " -o " + settings_struct.tasks.task170_MajorityFilter[task_position].outputFile + " -m " + settings_struct.tasks.task170_MajorityFilter[task_position].filterMode + " -r " + str(settings_struct.tasks.task170_MajorityFilter[task_position].radiusMajority) + " -umc " + str(settings_struct.tasks.task170_MajorityFilter[task_position].umcPixels)

            if settings_struct.general.processing.ram != 0:
                command += " -ram " + str(settings_struct.general.processing.ram)

            endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Création avec succes de la commande %s (Filtre majoritaire) à l'image %s" %(task_label, str(settings_struct.tasks.task170_MajorityFilter[task_position].inputFile)) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('180'): # Ajour de données exogénes à la classification par superposition

            # Preparation des parametres
            post_traitement_raster_fileBD_dico_str = ""
            post_traitement_raster_buffer_dico_str = ""
            post_traitement_raster_sql_dico_str = ""
            for classMacroSuperposition in settings_struct.tasks.task180_DataBaseSuperposition[task_position].classMacroSuperpositionList :
                post_traitement_raster_fileBD_dico_str +=  " " + str(classMacroSuperposition.label) + ":"
                post_traitement_raster_buffer_dico_str +=  " " + str(classMacroSuperposition.label) + ":"
                post_traitement_raster_sql_dico_str +=  " :" + str(classMacroSuperposition.label) + ":"
                for database_file_struct in classMacroSuperposition.dataBaseFileList:
                    post_traitement_raster_fileBD_dico_str += str(database_file_struct.inputVector) + ","
                    post_traitement_raster_buffer_dico_str += str(database_file_struct.bufferValue) + ","
                    post_traitement_raster_sql_dico_str += str(database_file_struct.sqlExpression) + ","
                post_traitement_raster_fileBD_dico_str = post_traitement_raster_fileBD_dico_str[:-1]
                post_traitement_raster_buffer_dico_str = post_traitement_raster_buffer_dico_str[:-1]
                post_traitement_raster_sql_dico_str = post_traitement_raster_sql_dico_str[:-1]

            post_traitement_raster_fileBD_dico_str = post_traitement_raster_fileBD_dico_str[1:]
            post_traitement_raster_buffer_dico_str = post_traitement_raster_buffer_dico_str[1:]
            post_traitement_raster_sql_dico_str = post_traitement_raster_sql_dico_str[2:]
            post_traitement_raster_sql_dico_str = post_traitement_raster_sql_dico_str.replace("'","\\'")
            if six.PY2:
                post_traitement_raster_sql_dico_str = post_traitement_raster_sql_dico_str.decode("latin1")
                post_traitement_raster_sql_dico_str = post_traitement_raster_sql_dico_str.encode("utf-8")

            # Commande
            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)
            command = call_python_action_to_make + "DataBaseSuperposition -i " + settings_struct.tasks.task180_DataBaseSuperposition[task_position].inputFile + " -o " + settings_struct.tasks.task180_DataBaseSuperposition[task_position].outputFile + " -classBd " + post_traitement_raster_fileBD_dico_str + " -classBuf " + post_traitement_raster_buffer_dico_str + " -classSql " + post_traitement_raster_sql_dico_str + " -simp " + str(settings_struct.tasks.task180_DataBaseSuperposition[task_position].simplificationPolygon) + " -vef " + settings_struct.general.vector.formatVector + " -rae " + settings_struct.general.raster.extensionRaster + " -vee " + settings_struct.general.vector.extensionVector

            endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Création avec succes de la commande %s (superposition de bases de données) à l'image %s" %(task_label, str(settings_struct.tasks.task180_DataBaseSuperposition[task_position].inputFile)) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('190'): # Assemblage des résultats de classifications, application éventuelle d'un bandmath et découpage au regard de la zone d'étude

            # Preparation des parametres
            ocs_raster_per_zone_list = ""
            for image_for_assembly in settings_struct.tasks.task190_ClassificationRasterAssembly[task_position].inputFilesList:
                ocs_raster_per_zone_list += image_for_assembly + ' '

            # Commande
            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)
            command = call_python_action_to_make + "RasterAssembly -il " + ocs_raster_per_zone_list + " -o " +  settings_struct.tasks.task190_ClassificationRasterAssembly[task_position].outputFile + " -v " + str(settings_struct.tasks.task190_ClassificationRasterAssembly[task_position].valueToForce) + " -r " + str(settings_struct.tasks.task190_ClassificationRasterAssembly[task_position].radius) + " -raf " + settings_struct.general.raster.formatRaster + " -vef " + settings_struct.general.vector.formatVector + " -rae " + settings_struct.general.raster.extensionRaster

            if settings_struct.tasks.task190_ClassificationRasterAssembly[task_position].inputVector != "":
                command += " -b " + str(settings_struct.tasks.task190_ClassificationRasterAssembly[task_position].inputVector)

            endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Création avec succes de la commande %s (Assemblage des résultats de classifications et passage d'un filtre majoritaire. Sortie : %s)" %(task_label,  str(settings_struct.tasks.task190_ClassificationRasterAssembly[task_position].outputFile)) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('200'): # Vectorisation globale de la classification

            # Commande de la vectorisation
            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)
            command = call_python_action_to_make + "Vectorization -i " + settings_struct.tasks.task200_ClassificationVectorization[task_position].inputFile + " -o " + settings_struct.tasks.task200_ClassificationVectorization[task_position].outputFile + " -col " + settings_struct.general.classification.columnName + " -umc " + str(settings_struct.tasks.task200_ClassificationVectorization[task_position].umc) + " -ts " + str(settings_struct.tasks.task200_ClassificationVectorization[task_position].tileSize) + " -vef " + settings_struct.general.vector.formatVector + " -rae " + settings_struct.general.raster.extensionRaster + " -vee " + settings_struct.general.vector.extensionVector

            if settings_struct.tasks.task200_ClassificationVectorization[task_position].expression != "" :
                command += " -reafrast -exp " + settings_struct.tasks.task200_ClassificationVectorization[task_position].expression

            if settings_struct.tasks.task200_ClassificationVectorization[task_position].inputVector != "" :
                command += " -boundvect " + settings_struct.tasks.task200_ClassificationVectorization[task_position].inputVector
            else :
                command += " -boundari "

            if settings_struct.tasks.task200_ClassificationVectorization[task_position].vectorizationType == "" :
                command += " -vectoriz "
            elif settings_struct.tasks.task200_ClassificationVectorization[task_position].vectorizationType == "GRASS" :
                command += " -grass "

            if settings_struct.tasks.task200_ClassificationVectorization[task_position].topologicalCorrectionSQL :
                command += " -csql" + " -epsg " + str(settings_struct.general.image.epsg) + " -pe " + settings_struct.general.postgis.encoding + " -serv " + settings_struct.general.postgis.serverName + " -port " + str(settings_struct.general.postgis.portNumber) + " -user " + settings_struct.general.postgis.userName + " -pwd " + settings_struct.general.postgis.password + " -db " + settings_struct.general.postgis.databaseName + " -sch " + settings_struct.general.postgis.schemaName

            if settings_struct.general.processing.ram != 0:
                command += " -ram " + str(settings_struct.general.processing.ram)

            endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Création avec succes de la commande %s (Vectorisation à %s pixels de %s. Sortie : %s)" %(task_label, str(settings_struct.tasks.task200_ClassificationVectorization[task_position].umc), str(settings_struct.tasks.task200_ClassificationVectorization[task_position].inputFile), str(settings_struct.tasks.task200_ClassificationVectorization[task_position].outputFile)) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('210'): # Croisement Vecteur - Raster et creation des colonnes de statistiques

            # Commande
            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)
            command = call_python_action_to_make + "CrossingVectorRaster -i " + settings_struct.tasks.task210_CrossingVectorRaster[task_position].inputFile + " -o " + settings_struct.tasks.task210_CrossingVectorRaster[task_position].outputVector + " -v " + settings_struct.tasks.task210_CrossingVectorRaster[task_position].inputVector + " -bn " + str(settings_struct.tasks.task210_CrossingVectorRaster[task_position].bandNumber) + " -csp" + " -vef " + settings_struct.general.vector.formatVector

            if settings_struct.tasks.task210_CrossingVectorRaster[task_position].statsAllCount :
                command += " -stc "

            if settings_struct.tasks.task210_CrossingVectorRaster[task_position].statsColumnsStr :
                command += " -sts "

            if settings_struct.tasks.task210_CrossingVectorRaster[task_position].statsAllCount or settings_struct.tasks.task210_CrossingVectorRaster[task_position].statsColumnsStr :
                class_label_dico = ""
                for class_classification in settings_struct.general.classification.classList:
                    class_label_dico += str(class_classification.label) + ":" + class_classification.name + " "

                command += " -cld " + class_label_dico

            if settings_struct.tasks.task210_CrossingVectorRaster[task_position].statsColumnsReal :
                command += " -str "

            endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Création avec succes de la commande %s (Croisement %s avec %s)" %(task_label, str(settings_struct.tasks.task210_CrossingVectorRaster[task_position].inputFile), str(settings_struct.tasks.task210_CrossingVectorRaster[task_position].inputVector)) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('210_RA'): # Croisement Vecteur - Raster (Utilisation production RA)

            id_command, index_remote_ip, id_task_commands_list = crossingVectorRasterRA(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, command_doc, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list, debug)

            print(cyan + "writeCommands() : " + bold + green + "Création avec succes de la commande %s (Croisement %s avec %s)" %(task_label, str(settings_struct.tasks.task210_RA_CrossingVectorRaster[task_position].inputClassifFile), str(settings_struct.tasks.task210_RA_CrossingVectorRaster[task_position].inputVector)) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('220'): # Découpage automatique des images et vecteurs finaux

            # Préparation de la liste des rasteurs à découper
            rasters_to_cut_list_str = ""
            for raster_file in settings_struct.tasks.task220_VectorRasterCutting[task_position].inputFilesList :
                rasters_to_cut_list_str += raster_file + " "

            rasters_cut_list_str = ""
            for raster_file in settings_struct.tasks.task220_VectorRasterCutting[task_position].outputFilesList :
                rasters_cut_list_str += raster_file + " "

            # Préparation de la liste des vecteurs à découper
            vectors_to_cut_list_str = ""
            for vector_file in settings_struct.tasks.task220_VectorRasterCutting[task_position].inputVectorsList :
                 vectors_to_cut_list_str += vector_file + " "

            vectors_cut_list_str = ""
            for vector_file in settings_struct.tasks.task220_VectorRasterCutting[task_position].outputVectorsList :
                 vectors_cut_list_str += vector_file + " "

            # Commande
            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)
            command = call_python_action_to_make + "VectorRasterCutting -c " + settings_struct.tasks.task220_VectorRasterCutting[task_position].inputCutVector + " -b " + str(settings_struct.tasks.task220_VectorRasterCutting[task_position].overflowNbPixels * settings_struct.general.image.resolution) + " -epsg " + str(settings_struct.general.image.epsg) + " -ndv " + str(settings_struct.general.image.nodataValue) + " -raf " + settings_struct.general.raster.formatRaster + " -vef " + settings_struct.general.vector.formatVector + " -rae " + settings_struct.general.raster.extensionRaster + " -vee " + settings_struct.general.vector.extensionVector

            if rasters_to_cut_list_str != "" :
                command += " -il " + rasters_to_cut_list_str

            if rasters_cut_list_str != "" :
                command += " -iol " + rasters_cut_list_str

            if vectors_to_cut_list_str != "" :
                command += " -vl " + vectors_to_cut_list_str

            if vectors_cut_list_str != "" :
                command += " -vol " + vectors_cut_list_str

            if  settings_struct.tasks.task220_VectorRasterCutting[task_position].roundPixelSize != 0.0 :
                command += " -r " + str(settings_struct.tasks.task220_VectorRasterCutting[task_position].roundPixelSize)

            if  settings_struct.tasks.task220_VectorRasterCutting[task_position].resamplingMethode != "" :
                command += " -rm " + settings_struct.tasks.task220_VectorRasterCutting[task_position].resamplingMethode

            if settings_struct.tasks.task220_VectorRasterCutting[task_position].compression and rasters_cut_list_str != "" :
                command += " -z "

            endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Création avec succes de la commande %s (Decoupage des rasteurs et vecteurs de sortie par le vecteur %s" %(task_label, str(settings_struct.tasks.task220_VectorRasterCutting[task_position].inputCutVector)) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('230'): # Calcul de la matrice de confusion et des indicateurs de qualité

            # Commande
            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)
            command = call_python_action_to_make + "QualityIndicatorComputation -i " + settings_struct.tasks.task230_QualityIndicatorComputation[task_position].inputFile + " -ocm " +  settings_struct.tasks.task230_QualityIndicatorComputation[task_position].outputMatrix + " -oqi " + settings_struct.tasks.task230_QualityIndicatorComputation[task_position].outputFile + " -id " + settings_struct.general.classification.columnName

            if settings_struct.tasks.task230_QualityIndicatorComputation[task_position].inputVector != "" :
                command += " -v " + settings_struct.tasks.task230_QualityIndicatorComputation[task_position].inputVector

            if settings_struct.tasks.task230_QualityIndicatorComputation[task_position].inputSample != "" :
                command += " -s " + settings_struct.tasks.task230_QualityIndicatorComputation[task_position].inputSample

            endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Création avec succes de la commande %s. Calcul de la matrice de confusion %s et des indicateurs de qualité %s" %(task_label, str(settings_struct.tasks.task230_QualityIndicatorComputation[task_position].outputMatrix), str(settings_struct.tasks.task230_QualityIndicatorComputation[task_position].outputFile)) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('240_RA'): # Verification et correction des résultats de production en sql (Utilisation production RA)

            # Préparation de la liste des vecteurs à découper
            vectors_input_list_str = ""
            for vector_input_file in settings_struct.tasks.task240_RA_ProductOcsVerificationCorrectionSQL[task_position].inputVectorsList :
                 vectors_input_list_str += vector_input_file + " "

            vectors_output_list_str = ""
            for vector_output_file in settings_struct.tasks.task240_RA_ProductOcsVerificationCorrectionSQL[task_position].outputVectorsList :
                 vectors_output_list_str += vector_output_file + " "

            # Commande
            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)

            command = call_python_action_to_make + "ProductOcsVerificationCorrectionSQL -c " + settings_struct.tasks.task240_RA_ProductOcsVerificationCorrectionSQL[task_position].inputEmpriseVector + " -vl " + vectors_input_list_str + " -vol " +  vectors_output_list_str + " -epsg " + str(settings_struct.general.image.epsg) + " -pe " + settings_struct.general.postgis.encoding + " -serv " + settings_struct.general.postgis.serverName + " -port " + str(settings_struct.general.postgis.portNumber) + " -user " + settings_struct.general.postgis.userName + " -pwd " + settings_struct.general.postgis.password + " -db " + settings_struct.general.postgis.databaseName + " -sch " + settings_struct.general.postgis.schemaName

            endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Création avec succes de la commande %s. Traitements des vecteurs de livraisons %s" %(task_label, vectors_output_list_str) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('250_RA'): # Rasterisation des fichiers OCS vecteurisés avec UMC (Utilisation production RA)

            # Commande
            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list, False)

            command = call_python_action_to_make + "otbcli_Rasterization -in " + settings_struct.tasks.task250_RA_ProductOcsRasterisation[task_position].inputVector + " -out " + settings_struct.tasks.task250_RA_ProductOcsRasterisation[task_position].outputFile + " " + settings_struct.tasks.task250_RA_ProductOcsRasterisation[task_position].encodingOutput.lower() + " -im " + settings_struct.tasks.task250_RA_ProductOcsRasterisation[task_position].inputFile + " -background " + str(settings_struct.tasks.task250_RA_ProductOcsRasterisation[task_position].nodataOutput) + " -mode attribute -mode.attribute.field " + settings_struct.tasks.task250_RA_ProductOcsRasterisation[task_position].label

            if settings_struct.general.processing.ram != 0:
                command += " -ram " + str(settings_struct.general.processing.ram)

            endCommandUpdate(settings_struct, command_doc, command, debug, False)

            print(cyan + "writeCommands() : " + bold + green + "Création avec succes de la commande %s. Rasterisation du vecteur de livraison %s" %(task_label, str(settings_struct.tasks.task250_RA_ProductOcsRasterisation[task_position].inputVector)) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('260'): # Segmentation d'une image

            # Commande de la segmentation
            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)
            command = call_python_action_to_make + "Segmentation -i " + settings_struct.tasks.task260_SegmentationImage[task_position].inputFile + " -o " + settings_struct.tasks.task260_SegmentationImage[task_position].outputVector + " -sm " + settings_struct.tasks.task260_SegmentationImage[task_position].segmenationType.lower() + " -vef " + settings_struct.general.vector.formatVector + " -vee " + settings_struct.general.vector.extensionVector

            if settings_struct.tasks.task260_SegmentationImage[task_position].segmenationType.lower() == "sms":
                command += " -sms.sr " + str(settings_struct.tasks.task260_SegmentationImage[task_position].sms_spatialr) + " -sms.rs " + str(settings_struct.tasks.task260_SegmentationImage[task_position].sms_ranger) + " -sms.ms " + str(settings_struct.tasks.task260_SegmentationImage[task_position].sms_minsize)+ " -sms.ts " + str(settings_struct.tasks.task260_SegmentationImage[task_position].sms_tileSize)

            if settings_struct.tasks.task260_SegmentationImage[task_position].segmenationType.lower() == "srm":
                command += " -srm.hc " + settings_struct.tasks.task260_SegmentationImage[task_position].srm_homogeneityCriterion + " -srm.th " + str(settings_struct.tasks.task260_SegmentationImage[task_position].srm_threshol) + " -srm.ni " + str(settings_struct.tasks.task260_SegmentationImage[task_position].srm_nbIter) + " -srm.sp " + str(settings_struct.tasks.task260_SegmentationImage[task_position].srm_speed) + " -srm.wsr " + str(settings_struct.tasks.task260_SegmentationImage[task_position].srm_weightSpectral) + " -srm.wsi " + str(settings_struct.tasks.task260_SegmentationImage[task_position].srm_weightSpatial)

            if settings_struct.general.processing.ram != 0:
                command += " -ram " + str(settings_struct.general.processing.ram)

            endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Création avec succes de la commande %s (Segmentation de %s. Sortie : %s)" %(task_label, str(settings_struct.tasks.task260_SegmentationImage[task_position].inputFile), str(settings_struct.tasks.task260_SegmentationImage[task_position].outputVector)) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('270'): # Classification vecteur

            # Préparation de la liste des champs d'apprentissage
            field_list_str = ""
            for field in settings_struct.tasks.task270_ClassificationVector[task_position].fieldList :
                 field_list_str += field + " "

            # Commande de la classification
            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)
            command = call_python_action_to_make + "ClassificationVector -v " + settings_struct.tasks.task270_ClassificationVector[task_position].inputVector + " -o " + settings_struct.tasks.task270_ClassificationVector[task_position].outputVector + " -icf " + settings_struct.tasks.task270_ClassificationVector[task_position].inputCfield + " -ocf " + settings_struct.tasks.task270_ClassificationVector[task_position].outputCfield + " -exp " + '"' + settings_struct.tasks.task270_ClassificationVector[task_position].expression + '"' + " -f " + '"' + field_list_str + '"' + "-vef " + settings_struct.general.vector.formatVector + " -vee " + settings_struct.general.vector.extensionVector

            endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Création avec succes de la commande %s (Classification vecteur de %s. Sortie : %s)" %(task_label, str(settings_struct.tasks.task270_ClassificationVector[task_position].inputVector), str(settings_struct.tasks.task270_ClassificationVector[task_position].outputVector)) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('280'): # OCS raster à partir d'une liste de vecteurs

            # Initialisation de la commande
            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)
            command = call_python_action_to_make + "GenerateOcsWithVectors"
            # Paramètres spécifiques à l'appli
            command += " -in " + settings_struct.tasks.task280_GenerateOcsWithVectors[task_position].inputText + " -out " + settings_struct.tasks.task280_GenerateOcsWithVectors[task_position].outputRaster + " -fpt " + settings_struct.tasks.task280_GenerateOcsWithVectors[task_position].footprintVector + " -ref " + settings_struct.tasks.task280_GenerateOcsWithVectors[task_position].referenceRaster + " -cod " + settings_struct.tasks.task280_GenerateOcsWithVectors[task_position].codage
            # Paramètres liés aux fichiers
            command += " -epsg " + str(settings_struct.general.image.epsg) + " -ndv " + str(settings_struct.general.image.nodataValue) + " -raf " + settings_struct.general.raster.formatRaster + " -vef " + settings_struct.general.vector.formatVector + " -rae " + settings_struct.general.raster.extensionRaster + " -vee " + settings_struct.general.vector.extensionVector
            # Finalisation de la commande
            endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Création avec succès de la commande %s de production d'OCS raster à partir d'une liste de vecteurs." % (task_label) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('290'): # Calcul raster BandMathX (Utilisation de l'OTB)


            # Préparation de la liste des rasteurs d'entrée
            rasters_input_list_str = ""
            for raster_file in settings_struct.tasks.task290_RasterBandMathX[task_position].inputFilesList :
                rasters_input_list_str += raster_file + " "

            # Commande
            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list, False)

            command = call_python_action_to_make + "otbcli_BandMathX -il " + rasters_input_list_str + " -out " + settings_struct.tasks.task290_RasterBandMathX[task_position].outputFile + " " + settings_struct.tasks.task290_RasterBandMathX[task_position].encodingOutput.lower() + " -exp " + '"' + settings_struct.tasks.task290_RasterBandMathX[task_position].expression + '"'

            if settings_struct.general.processing.ram != 0:
                command += " -ram " + str(settings_struct.general.processing.ram)

            endCommandUpdate(settings_struct, command_doc, command, debug, False)

            print(cyan + "writeCommands() : " + bold + green + "Création avec succes de la commande %s. Resultat du calcul raster %s" %(task_label, str(settings_struct.tasks.task290_RasterBandMathX[task_position].outputFile)) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('5_TDC'): # Creation d'un vecteur d'emprise sur les images du trait de côte

            if settings_struct.tasks.task5_TDC_CreateEmprise[task_position].dateSplitter == '':
                date_splitter_option  = ''
            else :
                date_splitter_option  = " -sepn " + settings_struct.tasks.task5_TDC_CreateEmprise[task_position].dateSplitter

            if settings_struct.tasks.task5_TDC_CreateEmprise[task_position].intraDateSplitter != '':
                date_splitter_option  += " -sepd " + settings_struct.tasks.task5_TDC_CreateEmprise[task_position].intraDateSplitter

            # Commande
            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)

            command = call_python_action_to_make + "CreateEmprises -dir " + settings_struct.tasks.task5_TDC_CreateEmprise[task_position].inputPath + " -outf " + settings_struct.tasks.task5_TDC_CreateEmprise[task_position].outputVector  + " -epsg " + str(settings_struct.general.image.epsg)
            command += " -posd " + str(settings_struct.tasks.task5_TDC_CreateEmprise[task_position].datePosition) + " -nbcd " + str (settings_struct.tasks.task5_TDC_CreateEmprise[task_position].dateNumberOfCharacters) + date_splitter_option + " -vef " + settings_struct.general.vector.formatVector + " -rae " + settings_struct.general.raster.extensionRaster + " -vee " + settings_struct.general.vector.extensionVector

            if settings_struct.tasks.task5_TDC_CreateEmprise[task_position].noAssembled:
                command += " -na"
            if settings_struct.tasks.task5_TDC_CreateEmprise[task_position].allPolygon:
                command += " -all"
            if settings_struct.tasks.task5_TDC_CreateEmprise[task_position].noDate:
                command += " -nd"
            if settings_struct.tasks.task5_TDC_CreateEmprise[task_position].optimisationEmprise:
                command += " -op"
            if settings_struct.tasks.task5_TDC_CreateEmprise[task_position].optimisationNoData:
                command += " -op_nodata -erode " + str(settings_struct.tasks.task5_TDC_CreateEmprise[task_position].erode) + " -ndv " + str(settings_struct.general.image.nodataValue)
            endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Création avec succes de la commande %s (Creation d'un vecteur d'emprise sur les images du trait de côte %s)" %(task_label, str(settings_struct.tasks.task5_TDC_CreateEmprise[task_position].outputVector)) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('10_TDC'): # Passage automatique de l'image vectorisée au trait de côte

            # Préparation du dictionnaire contenant l'image en entrée associée au(x) binary mask(s) vecteur
            image_binary_mask_vect_dico_str = settings_struct.tasks.task10_TDC_PolygonMerToTDC[task_position].inputFile + ":"
            for binary_mask_vect in settings_struct.tasks.task10_TDC_PolygonMerToTDC[task_position].ndviMaskVectorList :
                image_binary_mask_vect_dico_str += binary_mask_vect + ","
            image_binary_mask_vect_dico_str = image_binary_mask_vect_dico_str[:-1]

            # Commande
            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)

            command = call_python_action_to_make + "PolygonMerToTDC -ind " + image_binary_mask_vect_dico_str + " -outd " + settings_struct.tasks.task10_TDC_PolygonMerToTDC[task_position].outputPath + " -mer " + settings_struct.tasks.task10_TDC_PolygonMerToTDC[task_position].inputSeaPointsFile + " -simp " + str(settings_struct.tasks.task10_TDC_PolygonMerToTDC[task_position].simplifParameter) + " -d " + settings_struct.tasks.task10_TDC_PolygonMerToTDC[task_position].inputCutVector + " -bp " + str(settings_struct.tasks.task10_TDC_PolygonMerToTDC[task_position].positiveBufferSize) + " -bn " + str(settings_struct.tasks.task10_TDC_PolygonMerToTDC[task_position].negativeBufferSize) + " -epsg " + str(settings_struct.general.image.epsg) + " -vef " + settings_struct.general.vector.formatVector + " -rae " + settings_struct.general.raster.extensionRaster + " -vee " + settings_struct.general.vector.extensionVector

            if settings_struct.tasks.task10_TDC_PolygonMerToTDC[task_position].resultBinMaskVectorFunction:
                command += " -fctbmv"
            endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Création avec succes de la commande %s (Extraction du trait de côte à partir de l'image vectorisée %s)" %(task_label, str(settings_struct.tasks.task10_TDC_PolygonMerToTDC[task_position].inputFile)) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('20_TDC'): # Préparation des images à partir de 'paysages' optimisés par rapport à une zone d'intérêt

            dir_source_images_str = ''
            for dir_source in settings_struct.tasks.task20_TDC_PrepareData[task_position].sourceImagesDirList:
                dir_source_images_str += dir_source + ' '

            if settings_struct.tasks.task20_TDC_PrepareData[task_position].dateSplitter == '':
                date_splitter_option  = ''
            else :
                date_splitter_option  = " -sepn " + settings_struct.tasks.task20_TDC_PrepareData[task_position].dateSplitter

            if settings_struct.tasks.task20_TDC_PrepareData[task_position].intraDateSplitter != '':
                date_splitter_option  += " -sepd " + settings_struct.tasks.task20_TDC_PrepareData[task_position].intraDateSplitter

            # Commande
            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)

            command = call_python_action_to_make + "PrepareData -b " + settings_struct.tasks.task20_TDC_PrepareData[task_position].inputBufferTDC + " -p " + settings_struct.tasks.task20_TDC_PrepareData[task_position].inputVectorPaysage + " -outd " + settings_struct.tasks.task20_TDC_PrepareData[task_position].outputPath + " -pathi " + dir_source_images_str + " -idp " + settings_struct.tasks.task20_TDC_PrepareData[task_position].idPaysage + " -idn " + settings_struct.tasks.task20_TDC_PrepareData[task_position].idNameSubRep + " -epsg " + str(settings_struct.general.image.epsg)
            command += " -posd " + str(settings_struct.tasks.task20_TDC_PrepareData[task_position].datePosition) + " -nbcd " + str (settings_struct.tasks.task20_TDC_PrepareData[task_position].dateNumberOfCharacters) + date_splitter_option + " -raf " + settings_struct.general.raster.formatRaster + " -vef " + settings_struct.general.vector.formatVector + " -rae " + settings_struct.general.raster.extensionRaster + " -vee " + settings_struct.general.vector.extensionVector

            if settings_struct.tasks.task20_TDC_PrepareData[task_position].optimisationZone:
                command += " -opt"
            if settings_struct.tasks.task20_TDC_PrepareData[task_position].zoneDate:
                command += " -z"
            if settings_struct.tasks.task20_TDC_PrepareData[task_position].noCover:
                command += " -nc"
            endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Création avec succes de la commande %s (Preparation des images à partir du fichier paysage %s)" %(task_label, str(settings_struct.tasks.task20_TDC_PrepareData[task_position].inputVectorPaysage)) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('30_TDC'): # Extraction du trait de côte par seuillage

            # Preparation de la liste ordre des bandes de l'image
            channel_order_list_str = ""
            for channel_order in settings_struct.general.image.channelOrderList:
                channel_order_list_str += channel_order + ' '

            # Préparation du dictionnaire contenant l'image en entrée associée au(x) seuil(s) à appliquer, et éventuellement à l'image indice
            image_seuils_dico_str = ''
            image_seuils_dico_str = settings_struct.tasks.task30_TDC_TDCSeuil[task_position].inputFile + ":"
            for threshold in settings_struct.tasks.task30_TDC_TDCSeuil[task_position].sourceIndexImageThresholdsList :
                image_seuils_dico_str += threshold + ","
            image_seuils_dico_str = image_seuils_dico_str[:-1]

            # Commande
            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)

            command = call_python_action_to_make + "TDCSeuil -isd " + image_seuils_dico_str + " -outd " + settings_struct.tasks.task30_TDC_TDCSeuil[task_position].outputPath + " -mer " + settings_struct.tasks.task30_TDC_TDCSeuil[task_position].inputSeaPointsFile + " -simp " + str(settings_struct.tasks.task30_TDC_TDCSeuil[task_position].simplifParameter) + " -epsg " + str(settings_struct.general.image.epsg) + " -ndv " + str(settings_struct.general.image.nodataValue) + " -raf " + settings_struct.general.raster.formatRaster + " -vef " + settings_struct.general.vector.formatVector + " -rae " + settings_struct.general.raster.extensionRaster + " -vee " + settings_struct.general.vector.extensionVector

            if settings_struct.tasks.task30_TDC_TDCSeuil[task_position].inputCutVector != "":
                command += " -d " + str(settings_struct.tasks.task30_TDC_TDCSeuil[task_position].inputCutVector)

            if settings_struct.tasks.task30_TDC_TDCSeuil[task_position].inputEmpriseVector != "":
                command += " -e " + str(settings_struct.tasks.task30_TDC_TDCSeuil[task_position].inputEmpriseVector)

            if settings_struct.tasks.task30_TDC_TDCSeuil[task_position].attributeValLimite != "":
                command += " -at_v_limite '" + str(settings_struct.tasks.task30_TDC_TDCSeuil[task_position].attributeValLimite) + "'"
            if settings_struct.tasks.task30_TDC_TDCSeuil[task_position].attributeValProced != "":
                command += " -at_v_proced '" + str(settings_struct.tasks.task30_TDC_TDCSeuil[task_position].attributeValProced) + "'"
            if settings_struct.tasks.task30_TDC_TDCSeuil[task_position].attributeValDatepr != "":
                command += " -at_v_datepr " + str(settings_struct.tasks.task30_TDC_TDCSeuil[task_position].attributeValDatepr)
            if settings_struct.tasks.task30_TDC_TDCSeuil[task_position].attributeValPrecis != "":
                command += " -at_v_precis " + str(settings_struct.tasks.task30_TDC_TDCSeuil[task_position].attributeValPrecis)
            if settings_struct.tasks.task30_TDC_TDCSeuil[task_position].attributeValContac != "":
                command += " -at_v_contac " + str(settings_struct.tasks.task30_TDC_TDCSeuil[task_position].attributeValContac)
            if settings_struct.tasks.task30_TDC_TDCSeuil[task_position].attributeValType != "":
                command += " -at_v_type " + str(settings_struct.tasks.task30_TDC_TDCSeuil[task_position].attributeValType)
            if settings_struct.tasks.task30_TDC_TDCSeuil[task_position].attributeValReal != "":
                command += " -at_v_real " + str(settings_struct.tasks.task30_TDC_TDCSeuil[task_position].attributeValReal)

            if settings_struct.tasks.task30_TDC_TDCSeuil[task_position].calcIndiceImage:
                command += " -c"
                if channel_order_list_str != "" :
                    command += " -chao " + channel_order_list_str

            endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Création avec succes de la commande %s (Extraction du trait de côte par seuillage à partir de l'image %s)" %(task_label, str(settings_struct.tasks.task30_TDC_TDCSeuil[task_position].inputFile)) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('40_TDC'): # Extraction du trait de côte par classification non supervisée K-means

            # Commande
            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)

            command = call_python_action_to_make + "TDCKmeans -pathi " + settings_struct.tasks.task40_TDC_TDCKmeans[task_position].inputFile + " -outd " + settings_struct.tasks.task40_TDC_TDCKmeans[task_position].outputPath + " -mer " + settings_struct.tasks.task40_TDC_TDCKmeans[task_position].inputSeaPointsFile + " -d " + settings_struct.tasks.task40_TDC_TDCKmeans[task_position].inputCutVector + " -nbc " + str(settings_struct.tasks.task40_TDC_TDCKmeans[task_position].classesNumber) + " -epsg " + str(settings_struct.general.image.epsg) + " -ndv " + str(settings_struct.general.image.nodataValue) + " -raf " + settings_struct.general.raster.formatRaster + " -vef " + settings_struct.general.vector.formatVector + " -rae " + settings_struct.general.raster.extensionRaster + " -vee " + settings_struct.general.vector.extensionVector

            endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Création avec succes de la commande %s (Extraction du trait de côte à partir de l'image %s)" %(task_label, str(settings_struct.tasks.task40_TDC_TDCKmeans[task_position].inputFile)) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('50_TDC'): # Extraction du trait de côte par classification supervisée

            input_im_app_dico_str = settings_struct.tasks.task50_TDC_TDCClassif[task_position].inputFile + ':'
            if settings_struct.tasks.task50_TDC_TDCClassif[task_position].useExogenDB:
                for class_sample_struct in settings_struct.tasks.task50_TDC_TDCClassif[task_position].classSampleList:
                    input_im_app_dico_str += '[' + class_sample_struct.name + ':' + str(class_sample_struct.label) + ','
                    for prop in class_sample_struct.class_properties_list:
                        input_im_app_dico_str += prop + ','
                    input_im_app_dico_str = input_im_app_dico_str[:-1]
                    input_im_app_dico_str += '],'
            else:
                for class_sample_struct in settings_struct.tasks.task50_TDC_TDCClassif[task_position].classSampleList:
                    for prop in class_sample_struct.class_properties_list:
                        input_im_app_dico_str += prop + ','
            input_im_app_dico_str = input_im_app_dico_str[:-1]

            if settings_struct.tasks.task50_TDC_TDCClassif[task_position].exogenDBSuperp:
                # Récupération du dictionnaire
                post_traitement_raster_complete_dico_str = ""
                for classMacroSuperposition in settings_struct.tasks.task50_TDC_TDCClassif[task_position].classMacroSuperpositionList :
                    post_traitement_raster_complete_dico_str +=  str(classMacroSuperposition.label)
                    for database_file in classMacroSuperposition.dataBaseFileDico :
                        post_traitement_raster_complete_dico_str +=  ":" + str(database_file) + "," + str(classMacroSuperposition.dataBaseFileDico[database_file])
                    post_traitement_raster_complete_dico_str += ' '
                post_traitement_raster_complete_dico_str = post_traitement_raster_complete_dico_str[:-1]

            # Commande
            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)

            command = call_python_action_to_make + "TDCClassif -dico " + input_im_app_dico_str + " -outd " + settings_struct.tasks.task50_TDC_TDCClassif[task_position].outputPath + " -mer " + settings_struct.tasks.task50_TDC_TDCClassif[task_position].inputSeaPointsFile + " -d " + settings_struct.tasks.task50_TDC_TDCClassif[task_position].inputCutVector + " -radiusmf " + str(settings_struct.tasks.task50_TDC_TDCClassif[task_position].radiusMajority) + " -exp " + '"' + settings_struct.tasks.task50_TDC_TDCClassif[task_position].microClassFusionExpression + '"' + " -pe UTF-8 -epsg " + str(settings_struct.general.image.epsg) + " -ndv " + str(settings_struct.general.image.nodataValue) + " -raf " + settings_struct.general.raster.formatRaster + " -vef " + settings_struct.general.vector.formatVector  + " -rae " + settings_struct.general.raster.extensionRaster + " -vee " + settings_struct.general.vector.extensionVector

            if settings_struct.tasks.task50_TDC_TDCClassif[task_position].useExogenDB:
                command += " -bdext"
            if settings_struct.tasks.task50_TDC_TDCClassif[task_position].cut:
                command += " -cut"
            if settings_struct.tasks.task50_TDC_TDCClassif[task_position].step1Execution:
                command += " -st1"
            if settings_struct.tasks.task50_TDC_TDCClassif[task_position].step2Execution:
                command += " -st2"
            if settings_struct.tasks.task50_TDC_TDCClassif[task_position].step3Execution:
                command += " -st3"
            if settings_struct.tasks.task50_TDC_TDCClassif[task_position].step4Execution:
                command += " -st4"
            if settings_struct.tasks.task50_TDC_TDCClassif[task_position].exogenDBSuperp:
                command += " -superp " + post_traitement_raster_complete_dico_str
            endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Création avec succes de la commande %s (superposition de bases de données) à l'image %s" %(task_label, str(settings_struct.tasks.task50_TDC_TDCClassif[task_position].inputFile)) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('60_TDC'): # Extraction des ouvrages avec la méthode des buffers, de Sobel ou les deux combinées

            # Preparation de la liste ordre des bandes de l'image
            channel_order_list_str = ""
            for channel_order in settings_struct.general.image.channelOrderList:
                channel_order_list_str += channel_order + ' '

            # Préparation du dictionnaire input_dico
            input_dico_str = ''
            input_dico_str = settings_struct.tasks.task60_TDC_DetectOuvrages[task_position].inputFile + ":"
            for bufferSizeThresholdIndexImage in settings_struct.tasks.task60_TDC_DetectOuvrages[task_position].sourceBufferSizeThresholdIndexImageList :
                input_dico_str += str(bufferSizeThresholdIndexImage) + ","
            input_dico_str = input_dico_str[:-1]

            # Commande
            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)

            command = call_python_action_to_make + "DetectionOuvrages -dico " + input_dico_str + " -outd " + settings_struct.tasks.task60_TDC_DetectOuvrages[task_position].outputPath + " -mer " + settings_struct.tasks.task60_TDC_DetectOuvrages[task_position].inputSeaPointsFile + " -d " + settings_struct.tasks.task60_TDC_DetectOuvrages[task_position].inputCutVector + " -meth " + settings_struct.tasks.task60_TDC_DetectOuvrages[task_position].method + " -epsg " + str(settings_struct.general.image.epsg) + " -ndv " + str(settings_struct.general.image.nodataValue) + " -raf " + settings_struct.general.raster.formatRaster + " -vef " + settings_struct.general.vector.formatVector + " -rae " + settings_struct.general.raster.extensionRaster + " -vee " + settings_struct.general.vector.extensionVector

            if settings_struct.tasks.task60_TDC_DetectOuvrages[task_position].indexImageBuffers:
                command += " -indb"
            if settings_struct.tasks.task60_TDC_DetectOuvrages[task_position].indexImageSobel:
                command += " -inds"
            if channel_order_list_str != "" :
                command += " -chao " + channel_order_list_str

            endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Création avec succes de la commande %s (Extraction des ouvrages à partir du fichier %s)" %(task_label, str(settings_struct.tasks.task60_TDC_DetectOuvrages[task_position].inputFile)) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('70_TDC'): # Extraction des ouvrages à partir d'un trait de côte par la méthode des buffers

            # Commande
            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)

            command = call_python_action_to_make + "BuffersOuvrages -tdc " + settings_struct.tasks.task70_TDC_DetectOuvragesBuffers[task_position].inputFile + " -outd " + settings_struct.tasks.task70_TDC_DetectOuvragesBuffers[task_position].outputPath + " -d " + settings_struct.tasks.task70_TDC_DetectOuvragesBuffers[task_position].inputCutVector + " -bp " + str(settings_struct.tasks.task70_TDC_DetectOuvragesBuffers[task_position].bufferSizePos) + " -bn " + str(settings_struct.tasks.task70_TDC_DetectOuvragesBuffers[task_position].bufferSizeNeg) + " -vef " + settings_struct.general.vector.formatVector + " -vee " + settings_struct.general.vector.extensionVector

            endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Création avec succes de la commande %s (Extraction des ouvrages par la méthode des buffers à partir du trait de côte %s)" %(task_label, str(settings_struct.tasks.task70_TDC_DetectOuvragesBuffers[task_position].inputFile)) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('80_TDC'): # Extraction des ouvrages par détection de contours (filtre de Sobel)

            # Préparation du dictionnaire contenant le seuil et éventuellement l'image indice
            input_im_seuils_dico_str = ''
            input_im_seuils_dico_str = settings_struct.tasks.task80_TDC_DetectOuvragesEdgeExtraction[task_position].inputFile + ":"
            for indexImageThreshold in settings_struct.tasks.task80_TDC_DetectOuvragesEdgeExtraction[task_position].sourceIndexImageThresholdsList :
                input_im_seuils_dico_str += str(indexImageThreshold) + ","
            input_im_seuils_dico_str = input_im_seuils_dico_str[:-1]

            # Commande
            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)

            command = call_python_action_to_make + "EdgeExtractionOuvrages -isd " + input_im_seuils_dico_str + " -outd " + settings_struct.tasks.task80_TDC_DetectOuvragesEdgeExtraction[task_position].outputPath + " -d " + settings_struct.tasks.task80_TDC_DetectOuvragesEdgeExtraction[task_position].inputCutVector + " -ndv " + str(settings_struct.general.image.nodataValue) + " -raf " + settings_struct.general.raster.formatRaster + " -vef " + settings_struct.general.vector.formatVector + " -rae " + settings_struct.general.raster.extensionRaster + " -vee " + settings_struct.general.vector.extensionVector

            if settings_struct.tasks.task80_TDC_DetectOuvragesEdgeExtraction[task_position].calcIndexImage:
                command += " -c"
            endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Création avec succes de la commande %s (Extraction des ouvrages par détection de contours (filtre de Sobel) à partir de l'image %s)" %(task_label, str(settings_struct.tasks.task80_TDC_DetectOuvragesEdgeExtraction[task_position].inputFile)) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('90_TDC'): # Calcul de distance entre des points et un trait de côte

            # Commande
            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)

            command = call_python_action_to_make + "DistanceTDCPointLine -tdc " + settings_struct.tasks.task90_TDC_DistanceTDCPointLine[task_position].inputTDCFile + " -pts " + settings_struct.tasks.task90_TDC_DistanceTDCPointLine[task_position].inputPointsFile + " -outd " + settings_struct.tasks.task90_TDC_DistanceTDCPointLine[task_position].outputPath + " -mer " + settings_struct.tasks.task90_TDC_DistanceTDCPointLine[task_position].inputSeaPointsFile + " -col " + settings_struct.tasks.task90_TDC_DistanceTDCPointLine[task_position].evolColumnName + " -vef " + settings_struct.general.vector.formatVector + " -epsg " + str(settings_struct.general.image.epsg) + " -pe " + settings_struct.general.postgis.encoding + " -serv " + settings_struct.general.postgis.serverName + " -port " + str(settings_struct.general.postgis.portNumber) + " -user " + settings_struct.general.postgis.userName + " -pwd " + settings_struct.general.postgis.password + " -db " + settings_struct.general.postgis.databaseName + " -sch " + settings_struct.general.postgis.schemaName

            endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Création avec succes de la commande %s (Calcul de la distance entre les points %s et le trait de côte %s)" %(task_label, str(settings_struct.tasks.task90_TDC_DistanceTDCPointLine[task_position].inputPointsFile), str(settings_struct.tasks.task90_TDC_DistanceTDCPointLine[task_position].inputTDCFile)) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('100_TDC'): # Calcul de distance entre deux traits de côte

            # Commande
            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)

            command = call_python_action_to_make + "DistanceTDCBuffers -tdcref " + settings_struct.tasks.task100_TDC_DistanceTDCBuffers[task_position].inputReferenceFile + " -tdccalc " + settings_struct.tasks.task100_TDC_DistanceTDCBuffers[task_position].inputCalculatedFile + " -outd " + settings_struct.tasks.task100_TDC_DistanceTDCBuffers[task_position].outputPath + " -mer " + settings_struct.tasks.task100_TDC_DistanceTDCBuffers[task_position].inputSeaPointsFile + " -bs " + str(settings_struct.tasks.task100_TDC_DistanceTDCBuffers[task_position].bufferSize) + " -nb " + str(settings_struct.tasks.task100_TDC_DistanceTDCBuffers[task_position].buffersNumber) + " -vef " + settings_struct.general.vector.formatVector + " -epsg " + str(settings_struct.general.image.epsg) + " -pe " + settings_struct.general.postgis.encoding + " -serv " + settings_struct.general.postgis.serverName + " -port " + str(settings_struct.general.postgis.portNumber) + " -user " + settings_struct.general.postgis.userName + " -pwd " + settings_struct.general.postgis.password + " -db " + settings_struct.general.postgis.databaseName + " -sch " + settings_struct.general.postgis.schemaName

            endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Création avec succes de la commande %s (Calcul de la distance entre les traits de côte %s et %s)" %(task_label, str(settings_struct.tasks.task100_TDC_DistanceTDCBuffers[task_position].inputReferenceFile), str(settings_struct.tasks.task100_TDC_DistanceTDCBuffers[task_position].inputCalculatedFile)) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('110_TDC'): # Post traitement de lissage et fusion des traits de côte

            # Preparation de la liste des vecteurs des traits de côte d'entrées
            vectors_input_list_str = ""
            for vector_input_file in settings_struct.tasks. task110_TDC_PostTreatmentTDC[task_position].inputVectorsList :
                 vectors_input_list_str += vector_input_file + " "

            # Commande
            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)

            command = call_python_action_to_make + "PostTreatmentTDC -cvil " + vectors_input_list_str + " -v " + settings_struct.tasks.task110_TDC_PostTreatmentTDC[task_position].inputRockyVector + " -ova " + settings_struct.tasks.task110_TDC_PostTreatmentTDC[task_position].outputVectorTdcAll + " -ovw " + settings_struct.tasks.task110_TDC_PostTreatmentTDC[task_position].outputVectorTdcWithoutRocky + " -gpm " + settings_struct.tasks.task110_TDC_PostTreatmentTDC[task_position].generalize_method + " -gpt " + str(settings_struct.tasks.task110_TDC_PostTreatmentTDC[task_position].generalize_threshold) + " -ncf " + settings_struct.tasks.task110_TDC_PostTreatmentTDC[task_position].fusionColumnName  + " -epsg " + str(settings_struct.general.image.epsg) + " -vef " + settings_struct.general.vector.formatVector + " -vee " + settings_struct.general.vector.extensionVector

            endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Post traitement commande %s de lissage et fusion des traits de côte pour générer les vecteurs %s et %s)" %(task_label, str(settings_struct.tasks.task110_TDC_PostTreatmentTDC[task_position].outputVectorTdcAll), str(settings_struct.tasks.task110_TDC_PostTreatmentTDC[task_position].outputVectorTdcWithoutRocky)) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('UCZ'): # Classification UCZ (chaîne complète)

            # Commande
            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)

            built_vector_list_str = ""
            roads_vector_list_str = ""
            for built_vector in settings_struct.tasks.taskUCZ_ClassificationUCZ[task_position].builtsVectorList:
                built_vector_list_str += built_vector + ' '
            for roads_vector in settings_struct.tasks.taskUCZ_ClassificationUCZ[task_position].roadsVectorList:
                roads_vector_list_str += roads_vector + ' '

            command = call_python_action_to_make + "UCZ_cli -in " + settings_struct.tasks.taskUCZ_ClassificationUCZ[task_position].inputVector + " -out " + settings_struct.tasks.taskUCZ_ClassificationUCZ[task_position].outputVector + " -emp " + settings_struct.tasks.taskUCZ_ClassificationUCZ[task_position].empriseVector + " -raf " + settings_struct.general.raster.formatRaster + " -vef " + settings_struct.general.vector.formatVector + " -rae " + settings_struct.general.raster.extensionRaster + " -vee " + settings_struct.general.vector.extensionVector

            if settings_struct.tasks.taskUCZ_ClassificationUCZ[task_position].indicatorsTreatmentChoice == "BD_exogenes":
                if settings_struct.tasks.taskUCZ_ClassificationUCZ[task_position].binaryVegetationMask != '':
                    command += " -msk " + settings_struct.tasks.taskUCZ_ClassificationUCZ[task_position].binaryVegetationMask
                else:
                    command += " -img " + settings_struct.tasks.taskUCZ_ClassificationUCZ[task_position].satelliteImage
                command += " -bat " + built_vector_list_str + "-hyd " + settings_struct.tasks.taskUCZ_ClassificationUCZ[task_position].hydrographyVector + " -rpg " + settings_struct.tasks.taskUCZ_ClassificationUCZ[task_position].rpgVector

            elif settings_struct.tasks.taskUCZ_ClassificationUCZ[task_position].indicatorsTreatmentChoice == "SI_seuillage":
                command += " -img " + settings_struct.tasks.taskUCZ_ClassificationUCZ[task_position].satelliteImage
                command += " -bat " + built_vector_list_str + " -rou " + roads_vector_list_str

            elif settings_struct.tasks.taskUCZ_ClassificationUCZ[task_position].indicatorsTreatmentChoice == "SI_classif":
                command += " -img " + settings_struct.tasks.taskUCZ_ClassificationUCZ[task_position].satelliteImage
                command += " -bat " + built_vector_list_str

            elif settings_struct.tasks.taskUCZ_ClassificationUCZ[task_position].indicatorsTreatmentChoice == "Resultats_classif":
                command += " -img " + settings_struct.tasks.taskUCZ_ClassificationUCZ[task_position].satelliteImage + " -mnh " + settings_struct.tasks.taskUCZ_ClassificationUCZ[task_position].digitalHeightModel

            command += " -methi " + settings_struct.tasks.taskUCZ_ClassificationUCZ[task_position].indicatorsTreatmentChoice + " -methu " + settings_struct.tasks.taskUCZ_ClassificationUCZ[task_position].uczTreatmentChoice + " -sgbd " + settings_struct.tasks.taskUCZ_ClassificationUCZ[task_position].dbmsChoice

            if settings_struct.tasks.taskUCZ_ClassificationUCZ[task_position].indicatorsTreatmentChoice == "BD_exogenes" and settings_struct.tasks.taskUCZ_ClassificationUCZ[task_position].binaryVegetationMask == '':
                command += " -s1 " + str(settings_struct.tasks.taskUCZ_ClassificationUCZ[task_position].ndviThreshold)

            elif settings_struct.tasks.taskUCZ_ClassificationUCZ[task_position].indicatorsTreatmentChoice == "SI_seuillage":
                command += " -s1 " + str(settings_struct.tasks.taskUCZ_ClassificationUCZ[task_position].ndviThreshold) + " -s2 " + str(settings_struct.tasks.taskUCZ_ClassificationUCZ[task_position].ndviWaterThreshold) + " -s3 " + str(settings_struct.tasks.taskUCZ_ClassificationUCZ[task_position].ndwi2Threshold) + " -s4 " + str(settings_struct.tasks.taskUCZ_ClassificationUCZ[task_position].biLowerThreshold) + " -s5 " + str(settings_struct.tasks.taskUCZ_ClassificationUCZ[task_position].biUpperThreshold)

            endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Création avec succès de la commande %s de classification UCZ" % (task_label) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('00_LCZ'): # Préparation des données en vue du calcul des indicateurs LCZ

            # Préparation de la liste des vecteurs de bati
            built_input_list_str = ""
            for built_input in settings_struct.tasks.task00_LCZ_DataPreparation[task_position].builtInputList:
                built_input_list_str += built_input + ' '

            # Préparation de la liste des vecteurs des routes
            roads_input_list_str = ""
            for roads_input in settings_struct.tasks.task00_LCZ_DataPreparation[task_position].roadsInputList:
                roads_input_list_str += roads_input + ' '

            # Commande
            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)
            command = call_python_action_to_make + "DataPreparation -emp " + settings_struct.tasks.task00_LCZ_DataPreparation[task_position].empriseFile + " -in " + settings_struct.tasks.task00_LCZ_DataPreparation[task_position].gridInput + " -bil " + built_input_list_str + "-ril " + roads_input_list_str + " -clai " + settings_struct.tasks.task00_LCZ_DataPreparation[task_position].classifInput + " -mnsi " + settings_struct.tasks.task00_LCZ_DataPreparation[task_position].mnsInput + " -mnhi " + settings_struct.tasks.task00_LCZ_DataPreparation[task_position].mnhInput + " -out " + settings_struct.tasks.task00_LCZ_DataPreparation[task_position].gridOutput + " -uac " + settings_struct.tasks.task00_LCZ_DataPreparation[task_position].gridOutputCleaned + " -bo " + settings_struct.tasks.task00_LCZ_DataPreparation[task_position].builtOutput + " -ro " + settings_struct.tasks.task00_LCZ_DataPreparation[task_position].roadsOutput + " -clao " + settings_struct.tasks.task00_LCZ_DataPreparation[task_position].classifOutput + " -mnso " + settings_struct.tasks.task00_LCZ_DataPreparation[task_position].mnsOutput + " -mnho " + settings_struct.tasks.task00_LCZ_DataPreparation[task_position].mnhOutput + " -code " + settings_struct.tasks.task00_LCZ_DataPreparation[task_position].colCodeUA + " -item " + settings_struct.tasks.task00_LCZ_DataPreparation[task_position].colItemUA + " -epsg " + str(settings_struct.general.image.epsg) + " -ndv " + str(settings_struct.general.image.nodataValue) + " -raf " + settings_struct.general.raster.formatRaster + " -vef " + settings_struct.general.vector.formatVector + " -rae " + settings_struct.general.raster.extensionRaster + " -vee " + settings_struct.general.vector.extensionVector

            endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Création avec succès de la commande %s de préparation au calcul des indicateurs LCZ" % (task_label) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('10_LCZ'): # Calcul de l'indicateur LCZ pourcentage de surface bâtie

            # Préparation de la liste des classes baties
            building_class_list_str = ""
            for building_class in settings_struct.tasks.task10_LCZ_BuildingSurfaceFraction[task_position].buildingClassLabelList:
                building_class_list_str += str(building_class) + ' '

            # Commande
            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)
            command = call_python_action_to_make + "BuildingSurfaceFraction -in " +  settings_struct.tasks.task10_LCZ_BuildingSurfaceFraction[task_position].inputGridFile + " -out " + settings_struct.tasks.task10_LCZ_BuildingSurfaceFraction[task_position].outputGridFile + " -cla " + settings_struct.tasks.task10_LCZ_BuildingSurfaceFraction[task_position].inputClassifFile + " -cbl " + building_class_list_str + " -vef " + settings_struct.general.vector.formatVector + " -rae " + settings_struct.general.raster.extensionRaster

            endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Création avec succès de la commande %s de l'indicateur LCZ pourcentage de surface bâtie" % (task_label) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('20_LCZ'): # Calcul de l'indicateur LCZ pourcentage de surface imperméable

            # Préparation de la liste des classes imperméables
            impervious_class_list_str = ""
            for impervious_class in settings_struct.tasks.task20_LCZ_ImperviousSurfaceFraction[task_position].imperviousClassLabelList:
                impervious_class_list_str += str(impervious_class) + ' '

            # Commande
            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)
            command = call_python_action_to_make + "ImperviousSurfaceFraction -in " + settings_struct.tasks.task20_LCZ_ImperviousSurfaceFraction[task_position].inputGridFile + " -out " + settings_struct.tasks.task20_LCZ_ImperviousSurfaceFraction[task_position].outputGridFile + " -cla " + settings_struct.tasks.task20_LCZ_ImperviousSurfaceFraction[task_position].inputClassifFile + " -cil " + impervious_class_list_str + " -vef " + settings_struct.general.vector.formatVector + " -rae " + settings_struct.general.raster.extensionRaster

            endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Création avec succès de la commande %s de l'indicateur LCZ pourcentage de surface imperméable" % (task_label) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('30_LCZ'): # Calcul de l'indicateur LCZ pourcentage de surface perméable

            # Préparation de la liste des classes perméable
            pervious_class_list_str = ""
            for pervious_class in settings_struct.tasks.task30_LCZ_PerviousSurfaceFraction[task_position].perviousClassLabelList:
                pervious_class_list_str += str(pervious_class) + ' '

            # Commande
            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)
            command = call_python_action_to_make + "PerviousSurfaceFraction -in " + settings_struct.tasks.task30_LCZ_PerviousSurfaceFraction[task_position].inputGridFile + " -out " + settings_struct.tasks.task30_LCZ_PerviousSurfaceFraction[task_position].outputGridFile + " -cla " + settings_struct.tasks.task30_LCZ_PerviousSurfaceFraction[task_position].inputClassifFile + " -cpl " + pervious_class_list_str + " -vef " + settings_struct.general.vector.formatVector + " -rae " + settings_struct.general.raster.extensionRaster

            endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Création avec succès de la commande %s de l'indicateur LCZ pourcentage de surface perméable" % (task_label) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('40_LCZ'): # Calcul de l'indicateur LCZ facteur de vue du ciel

            # Préparation de la liste des classes baties
            building_class_list_str = ""
            for building_class in settings_struct.tasks.task40_LCZ_SkyViewFactor[task_position].buildingClassLabelList:
                building_class_list_str += str(building_class) + ' '

            # Commande
            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)
            command = call_python_action_to_make + "SkyViewFactor -in " + settings_struct.tasks.task40_LCZ_SkyViewFactor[task_position].inputGridFile + " -out " + settings_struct.tasks.task40_LCZ_SkyViewFactor[task_position].outputGridFile + " -mns " + settings_struct.tasks.task40_LCZ_SkyViewFactor[task_position].inputMnsFile + " -cla " + settings_struct.tasks.task40_LCZ_SkyViewFactor[task_position].inputClassifFile + " -cbl " + building_class_list_str + " -epsg " + str(settings_struct.general.image.epsg) + " -ndv " + str(settings_struct.general.image.nodataValue) + " -dx " + str(settings_struct.tasks.task40_LCZ_SkyViewFactor[task_position].dimGridX) + " -dy " + str(settings_struct.tasks.task40_LCZ_SkyViewFactor[task_position].dimGridY) + " -rad " + str(settings_struct.tasks.task40_LCZ_SkyViewFactor[task_position].radius) + " -met " + str(settings_struct.tasks.task40_LCZ_SkyViewFactor[task_position].method) + " -sdl " + str(settings_struct.tasks.task40_LCZ_SkyViewFactor[task_position].dlevel) + " -snd " + str(settings_struct.tasks.task40_LCZ_SkyViewFactor[task_position].ndirs) + " -raf " + settings_struct.general.raster.formatRaster + " -vef " + settings_struct.general.vector.formatVector + " -rae " + settings_struct.general.raster.extensionRaster + " -vee " + settings_struct.general.vector.extensionVector

            endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Création avec succès de la commande %s de l'indicateur LCZ facteur de vue du ciel" % (task_label) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('50_LCZ'): # Calcul de l'indicateur LCZ hauteur des éléments de rugosité par base de données bati ou par données OCS et MNS (Méthode Internationalisation)

            # Préparation de la liste des classes baties
            building_class_list_str = ""
            for building_class in settings_struct.tasks.task50_LCZ_HeightOfRoughnessElements[task_position].buildingClassLabelList:
                building_class_list_str += str(building_class) + ' '

            # Commande
            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)
            command = call_python_action_to_make + "HeightOfRoughnessElements -in " + settings_struct.tasks.task50_LCZ_HeightOfRoughnessElements[task_position].inputGridFile + " -out " + settings_struct.tasks.task50_LCZ_HeightOfRoughnessElements[task_position].outputGridFile + " -epsg " + str(settings_struct.general.image.epsg) + " -ndv " + str(settings_struct.general.image.nodataValue) + " -raf " + settings_struct.general.raster.formatRaster + " -vef " + settings_struct.general.vector.formatVector + " -rae " + settings_struct.general.raster.extensionRaster + " -vee " + settings_struct.general.vector.extensionVector + " -pe " + settings_struct.general.postgis.encoding + " -serv " + settings_struct.general.postgis.serverName + " -port " + str(settings_struct.general.postgis.portNumber) + " -user " + settings_struct.general.postgis.userName + " -pwd " + settings_struct.general.postgis.password + " -db " + settings_struct.general.postgis.databaseName + " -sch " + settings_struct.general.postgis.schemaName

            if settings_struct.tasks.task50_LCZ_HeightOfRoughnessElements[task_position].inputBuiltFile != "":
                command += " -bi " + settings_struct.tasks.task50_LCZ_HeightOfRoughnessElements[task_position].inputBuiltFile
            if settings_struct.tasks.task50_LCZ_HeightOfRoughnessElements[task_position].heightField != "":
                command += " -hf " + settings_struct.tasks.task50_LCZ_HeightOfRoughnessElements[task_position].heightField
            if settings_struct.tasks.task50_LCZ_HeightOfRoughnessElements[task_position].idField != "":
                command += " -id " + settings_struct.tasks.task50_LCZ_HeightOfRoughnessElements[task_position].idField
            if settings_struct.tasks.task50_LCZ_HeightOfRoughnessElements[task_position].inputMnhFile != "":
                command += " -mnh " + settings_struct.tasks.task50_LCZ_HeightOfRoughnessElements[task_position].inputMnhFile
            if settings_struct.tasks.task50_LCZ_HeightOfRoughnessElements[task_position].inputClassifFile != "":
                command += " -ocs " + settings_struct.tasks.task50_LCZ_HeightOfRoughnessElements[task_position].inputClassifFile
            if building_class_list_str != "":
                command += " -cbl " + building_class_list_str

            endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Création avec succès de la commande %s de l'indicateur LCZ hauteur des éléments de rugosité" % (task_label) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('60_LCZ'): # Calcul de l'indicateur LCZ classe de rugosité

            # Commande
            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)
            command = call_python_action_to_make + "TerrainRoughnessClass -in " + settings_struct.tasks.task60_LCZ_TerrainRoughnessClass[task_position].inputGridFile + " -out " + settings_struct.tasks.task60_LCZ_TerrainRoughnessClass[task_position].outputGridFile + " -bi " + settings_struct.tasks.task60_LCZ_TerrainRoughnessClass[task_position].inputBuiltFile + " -dl " + str(settings_struct.tasks.task60_LCZ_TerrainRoughnessClass[task_position].distanceLines) + " -epsg " + str(settings_struct.general.image.epsg) + " -pe " + settings_struct.general.postgis.encoding + " -serv " + settings_struct.general.postgis.serverName + " -port " + str(settings_struct.general.postgis.portNumber) + " -user " + settings_struct.general.postgis.userName + " -pwd " + settings_struct.general.postgis.password + " -db " + settings_struct.general.postgis.databaseName + " -sch " + settings_struct.general.postgis.schemaName + " -vef " + settings_struct.general.vector.formatVector

            endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Création avec succès de la commande %s de l'indicateur LCZ classe de rugosité" % (task_label) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('70_LCZ'): #  Calcul de l'indicateur LCZ rapport d'aspect

            # Commande
            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)
            command = call_python_action_to_make + "AspectRatio -in " +  settings_struct.tasks.task70_LCZ_AspectRatio[task_position].inputGridFile + " -out " + settings_struct.tasks.task70_LCZ_AspectRatio[task_position].outputGridFile + " -ri " + settings_struct.tasks.task70_LCZ_AspectRatio[task_position].inputRoadsFile + " -bi " + settings_struct.tasks.task70_LCZ_AspectRatio[task_position].inputBuiltFile + " -sd " + str(settings_struct.tasks.task70_LCZ_AspectRatio[task_position].segDist) + " -sl " + str(settings_struct.tasks.task70_LCZ_AspectRatio[task_position].segLength) + " -bs " + str(settings_struct.tasks.task70_LCZ_AspectRatio[task_position].bufferSize) + " -epsg " + str(settings_struct.general.image.epsg) + " -pe " + settings_struct.general.postgis.encoding + " -serv " + settings_struct.general.postgis.serverName + " -port " + str(settings_struct.general.postgis.portNumber) + " -user " + settings_struct.general.postgis.userName + " -pwd " + settings_struct.general.postgis.password + " -db " + settings_struct.general.postgis.databaseName + " -sch " + settings_struct.general.postgis.schemaName + " -vef " + settings_struct.general.vector.formatVector + " -vee " + settings_struct.general.vector.extensionVector

            endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Création avec succès de la commande %s de l'indicateur LCZ rapport d'aspect" % (task_label) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('80_LCZ'): # Calcul d'indicateurs OCS (non-compris dans la classification LCZ d'origine)

            # Préparation de la liste des classes baties
            building_class_list_str = ""
            for building_class in settings_struct.tasks.task80_LCZ_OcsIndicators[task_position].buildingClassLabelList:
                building_class_list_str += str(building_class) + ' '

            # Préparation de la liste des classes route
            road_class_list_str = ""
            for road_class in settings_struct.tasks.task80_LCZ_OcsIndicators[task_position].roadClassLabelList:
                road_class_list_str += str(road_class) + ' '

            # Préparation de la liste des classes sol-nu
            baresoil_class_list_str = ""
            for baresoil_class in settings_struct.tasks.task80_LCZ_OcsIndicators[task_position].baresoilClassLabelList:
                baresoil_class_list_str += str(baresoil_class) + ' '

            # Préparation de la liste des classes eau
            water_class_list_str = ""
            for water_class in settings_struct.tasks.task80_LCZ_OcsIndicators[task_position].waterClassLabelList:
                water_class_list_str += str(water_class) + ' '

            # Commande
            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)
            command = call_python_action_to_make + "OcsIndicators -in " + settings_struct.tasks.task80_LCZ_OcsIndicators[task_position].inputGridVector + " -out " + settings_struct.tasks.task80_LCZ_OcsIndicators[task_position].outputGridVector + " -ocs " + settings_struct.tasks.task80_LCZ_OcsIndicators[task_position].inputClassifFile + " -cbl " + building_class_list_str + " -crl " + road_class_list_str + " -csl " + baresoil_class_list_str + " -cwl " + water_class_list_str + " -epsg " + str(settings_struct.general.image.epsg) + " -ndv " + str(settings_struct.general.image.nodataValue) + " -raf " + settings_struct.general.raster.formatRaster + " -vef " + settings_struct.general.vector.formatVector + " -rae " + settings_struct.general.raster.extensionRaster + " -vee " + settings_struct.general.vector.extensionVector

            if settings_struct.tasks.task80_LCZ_OcsIndicators[task_position].inputClassifVector != "":
                command += " -cla " + settings_struct.tasks.task80_LCZ_OcsIndicators[task_position].inputClassifVector + " -fcn " + settings_struct.tasks.task80_LCZ_OcsIndicators[task_position].fieldClassifName

            if settings_struct.tasks.task80_LCZ_OcsIndicators[task_position].inputMnhFile != "":
                command += " -mnh " + settings_struct.tasks.task80_LCZ_OcsIndicators[task_position].inputMnhFile

            if settings_struct.tasks.task80_LCZ_OcsIndicators[task_position].vegetationClassLabelList != []:
                # Préparation de la liste des classes vegetation
                vegetation_class_list_str = ""
                for vegetation_class in settings_struct.tasks.task80_LCZ_OcsIndicators[task_position].vegetationClassLabelList:
                    vegetation_class_list_str += str(vegetation_class) + ' '
                command += " -cvl " + vegetation_class_list_str

            if settings_struct.tasks.task80_LCZ_OcsIndicators[task_position].hightVegetationClassLabelList != []:
                # Préparation de la liste des classes vegetation haute
                hight_vegetation_class_list_str = ""
                for hight_vegetation_class in settings_struct.tasks.task80_LCZ_OcsIndicators[task_position].hightVegetationClassLabelList:
                    hight_vegetation_class_list_str += str(hight_vegetation_class) + ' '
                command += " -chvl " + hight_vegetation_class_list_str

            if settings_struct.tasks.task80_LCZ_OcsIndicators[task_position].lowVegetationClassLabelList != []:
                # Préparation de la liste des classes vegetation basse
                low_vegetation_class_list_str = ""
                for low_vegetation_class in settings_struct.tasks.task80_LCZ_OcsIndicators[task_position].lowVegetationClassLabelList:
                    low_vegetation_class_list_str += str(low_vegetation_class) + ' '
                command += " -clvl " + low_vegetation_class_list_str

            endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Création avec succès de la commande %s des indicateurs LCZ supplémentaires" % (task_label) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('90_LCZ'): # Récupération des indicateurs et classification LCZ

            # Préparation des paramètres
            indicator_list_str = ""
            column_list_str = ""
            abbreviation_list_str = ""
            indices_files_lst_str = " "
            is_soil_occupation_include = False
            for indice_file in settings_struct.tasks.task90_LCZ_ClassificationLCZ[task_position].indiceFilesList :
                indice_file.indiceFile
                indice_file.indicator
                indice_file.columnSrc
                indice_file.abbreviation
                indicator_list_str += indice_file.indicator + ' '
                column_list_str += indice_file.columnSrc + ' '
                abbreviation_list_str += indice_file.abbreviation + ' '

                if indice_file.indiceFile != "" :
                    while switch(indice_file.indicator):
                        if case('BuildingSurfaceFraction'):
                            indices_files_lst_str += ' -bsf ' + indice_file.indiceFile
                            break
                        if case('ImperviousSurfaceFraction'):
                            indices_files_lst_str += ' -isf ' + indice_file.indiceFile
                            break
                        if case('PerviousSurfaceFraction'):
                            indices_files_lst_str += ' -psf ' + indice_file.indiceFile
                            break
                        if case('SkyViewFactor'):
                            indices_files_lst_str += ' -svf ' + indice_file.indiceFile
                            break
                        if case('HeightOfRoughnessElements'):
                            indices_files_lst_str += ' -hre ' + indice_file.indiceFile
                            break
                        if case('TerrainRoughnessClass'):
                            indices_files_lst_str += ' -trc ' + indice_file.indiceFile
                            break
                        if case('AspectRatio'):
                            indices_files_lst_str += ' -ara ' + indice_file.indiceFile
                            break
                        if case('SoilOccupation'):
                            if is_soil_occupation_include == False :
                                indices_files_lst_str += ' -ocs ' + indice_file.indiceFile
                                is_soil_occupation_include = True
                            break
                        if case('BuiltRate'):
                            if is_soil_occupation_include == False :
                                indices_files_lst_str += ' -ocs ' + indice_file.indiceFile
                                is_soil_occupation_include = True
                            break
                        if case('RoadRate'):
                            if is_soil_occupation_include == False :
                                indices_files_lst_str += ' -ocs ' + indice_file.indiceFile
                                is_soil_occupation_include = True
                            break
                        if case('WaterRate'):
                            if is_soil_occupation_include == False :
                                indices_files_lst_str += ' -ocs ' + indice_file.indiceFile
                                is_soil_occupation_include = True
                            break
                        if case('BareSoilRate'):
                            if is_soil_occupation_include == False :
                                indices_files_lst_str += ' -ocs ' + indice_file.indiceFile
                                is_soil_occupation_include = True
                            break
                        if case('VegetationRate'):
                            if is_soil_occupation_include == False :
                                indices_files_lst_str += ' -ocs ' + indice_file.indiceFile
                                is_soil_occupation_include = True
                            break
                        if case('AverageVegetationHeight'):
                            if is_soil_occupation_include == False :
                                indices_files_lst_str += ' -ocs ' + indice_file.indiceFile
                                is_soil_occupation_include = True
                            break
                        if case('MaxVegetationHeight'):
                            if is_soil_occupation_include == False :
                                indices_files_lst_str += ' -ocs ' + indice_file.indiceFile
                                is_soil_occupation_include = True
                            break
                        if case('HighVegetationRate'):
                            if is_soil_occupation_include == False :
                                indices_files_lst_str += ' -ocs ' + indice_file.indiceFile
                                is_soil_occupation_include = True
                            break
                        break

            # Commande
            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)
            command = call_python_action_to_make + "ClassificationLCZ -i " + settings_struct.tasks.task90_LCZ_ClassificationLCZ[task_position].inputPythonFile + " -uai " + settings_struct.tasks.task90_LCZ_ClassificationLCZ[task_position].inputFile + " -lcz " + settings_struct.tasks.task90_LCZ_ClassificationLCZ[task_position].outputFile + indices_files_lst_str + " -ind_lst " + str(indicator_list_str) + "-col_lst " + str(column_list_str) + "-abb_lst " + str(abbreviation_list_str) + "-cid " + settings_struct.tasks.task90_LCZ_ClassificationLCZ[task_position].columnNameId + " -chis " + settings_struct.tasks.task90_LCZ_ClassificationLCZ[task_position].columnNameLczHisto + " -clcz " + settings_struct.tasks.task90_LCZ_ClassificationLCZ[task_position].columnNameLcz + " -vef " + settings_struct.general.vector.formatVector

            if settings_struct.tasks.task90_LCZ_ClassificationLCZ[task_position].columnNameUaCode != "":
                command += " -cco " + settings_struct.tasks.task90_LCZ_ClassificationLCZ[task_position].columnNameUaCode

            if settings_struct.tasks.task90_LCZ_ClassificationLCZ[task_position].useClassifRf:
                command += " -crf -nsrf " + str(settings_struct.tasks.task90_LCZ_ClassificationLCZ[task_position].nbSampleRf) + " -mfrf " + settings_struct.tasks.task90_LCZ_ClassificationLCZ[task_position].modelRfFile + " -clczrf " + settings_struct.tasks.task90_LCZ_ClassificationLCZ[task_position].columnNameLczRf

            # Preparation du parametre dico variables-values
            correspondance_values_dico_str = ""
            for variablesValuesTree in settings_struct.tasks.task90_LCZ_ClassificationLCZ[task_position].variablesValuesTreeList :
                correspondance_values_dico_str += variablesValuesTree.variable + ":" + str(variablesValuesTree.value) + ' '

            if correspondance_values_dico_str != "":
                command += " -corres_dico " + correspondance_values_dico_str

            endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Création avec succès de la commande %s de classification LCZ" % (task_label) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('95_LCZ'): # Classification LCZ en mode opérationnel

            # Initialisation de la commande
            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)
            # Paramètres spécifiques à l'appli
            command = call_python_action_to_make + "ClassificationLczOperational -in " + settings_struct.tasks.task95_LCZ_ClassificationLczOperational[task_position].inputDivisionFile + " -hre " + settings_struct.tasks.task95_LCZ_ClassificationLczOperational[task_position].inputHreFile + " -ocs " + settings_struct.tasks.task95_LCZ_ClassificationLczOperational[task_position].inputOcsFile + " -out " + settings_struct.tasks.task95_LCZ_ClassificationLczOperational[task_position].outputLczFile + " -id " + settings_struct.tasks.task95_LCZ_ClassificationLczOperational[task_position].columnNameId
            # Paramètres liés aux fichiers
            command += " -epsg " + str(settings_struct.general.image.epsg) + " -vef " + settings_struct.general.vector.formatVector
            # Paramètres liés à PostGIS
            command += " -pgh " + settings_struct.general.postgis.serverName + " -pgp " + str(settings_struct.general.postgis.portNumber) + " -pgu " + settings_struct.general.postgis.userName + " -pgw " + settings_struct.general.postgis.password + " -pgd " + settings_struct.general.postgis.databaseName + " -pgs " + settings_struct.general.postgis.schemaName + " -pge " + settings_struct.general.postgis.encoding
            # Finalisation de la commande
            endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Création avec succès de la commande %s de classification LCZ en mode opérationnel." % (task_label) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('10_RSQ'): # Cartographie des classes de hauteurs d'eau

            # Initialisation de la commande
            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)
            # Paramètres spécifiques à l'appli
            command = call_python_action_to_make + "WaterHeight -infld " + settings_struct.tasks.task10_RSQ_WaterHeight[task_position].inputFloodedAreasVector + " -indem " + settings_struct.tasks.task10_RSQ_WaterHeight[task_position].inputDigitalElevationModelFile + " -outr " + settings_struct.tasks.task10_RSQ_WaterHeight[task_position].outputHeightsClassesFile + " -outv " + settings_struct.tasks.task10_RSQ_WaterHeight[task_position].outputHeightsClassesVector + " -hcla " + settings_struct.tasks.task10_RSQ_WaterHeight[task_position].heightsClasses
            # Paramètres liés aux fichiers
            command += " -epsg " + str(settings_struct.general.image.epsg) + " -ndv " + str(settings_struct.general.image.nodataValue) + " -raf " + settings_struct.general.raster.formatRaster + " -vef " + settings_struct.general.vector.formatVector + " -rae " + settings_struct.general.raster.extensionRaster + " -vee " + settings_struct.general.vector.extensionVector
            # Paramètres liés à GRASS
            command += " -ggis " + settings_struct.tasks.task10_RSQ_WaterHeight[task_position].grass_environmentVariable + " -gdbn " + settings_struct.tasks.task10_RSQ_WaterHeight[task_position].grass_databaseName + " -gloc " + settings_struct.tasks.task10_RSQ_WaterHeight[task_position].grass_location + " -gmap " + settings_struct.tasks.task10_RSQ_WaterHeight[task_position].grass_mapset
            # Finalisation de la commande
            endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Création avec succès de la commande %s de cartographie des classes de hauteurs d'eau." % (task_label) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('20_RSQ'): # Cartographie des parcelles disponibles et constructibles

            # Gestion des paramètres liste
            min_built_sizes_list_str = ""
            for min_built_size in settings_struct.tasks.task20_RSQ_AreasUnderUrbanization[task_position].minBuiltSizesList:
                min_built_sizes_list_str += min_built_size + ' '
            input_built_vectors_list_str = ""
            for input_built_vector in settings_struct.tasks.task20_RSQ_AreasUnderUrbanization[task_position].inputBuiltVectorsList:
                input_built_vectors_list_str += input_built_vector + ' '
            plu_u_values_list_str = ""
            for plu_u_values in settings_struct.tasks.task20_RSQ_AreasUnderUrbanization[task_position].pluUValuesList:
                plu_u_values_list_str += plu_u_values + ' '
            plu_au_values_list_str = ""
            for plu_au_values in settings_struct.tasks.task20_RSQ_AreasUnderUrbanization[task_position].pluAuValuesList:
                plu_au_values_list_str += plu_au_values + ' '
            ppr_red_values_list_str = ""
            for ppr_red_values in settings_struct.tasks.task20_RSQ_AreasUnderUrbanization[task_position].pprRedValuesList:
                ppr_red_values_list_str += ppr_red_values + ' '
            ppr_blue_values_list_str = ""
            for ppr_blue_values in settings_struct.tasks.task20_RSQ_AreasUnderUrbanization[task_position].pprBlueValuesList:
                ppr_blue_values_list_str += ppr_blue_values + ' '

            # Initialisation de la commande
            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)
            # Paramètres spécifiques à l'appli
            command = call_python_action_to_make + "AreasUnderUrbanization -in " + settings_struct.tasks.task20_RSQ_AreasUnderUrbanization[task_position].inputPlotVector + " -out " + settings_struct.tasks.task20_RSQ_AreasUnderUrbanization[task_position].outputPlotVector + " -emp " + settings_struct.tasks.task20_RSQ_AreasUnderUrbanization[task_position].footprintVector + " -mbsl " + min_built_sizes_list_str[:-1]
            if settings_struct.tasks.task20_RSQ_AreasUnderUrbanization[task_position].inputBuiltFile != "":
                command += " -ibr " + settings_struct.tasks.task20_RSQ_AreasUnderUrbanization[task_position].inputBuiltFile
            if settings_struct.tasks.task20_RSQ_AreasUnderUrbanization[task_position].inputBuiltVectorsList != []:
                command += " -ibvl " + input_built_vectors_list_str[:-1]
            if settings_struct.tasks.task20_RSQ_AreasUnderUrbanization[task_position].inputPluVector != "":
                command += " -iplu " + settings_struct.tasks.task20_RSQ_AreasUnderUrbanization[task_position].inputPluVector + " -pluf " + settings_struct.tasks.task20_RSQ_AreasUnderUrbanization[task_position].pluField + " -pluu " + plu_u_values_list_str[:-1] + " -plua " + plu_au_values_list_str[:-1]
            if settings_struct.tasks.task20_RSQ_AreasUnderUrbanization[task_position].inputPprVector != "":
                command += " -ippr " + settings_struct.tasks.task20_RSQ_AreasUnderUrbanization[task_position].inputPprVector + " -pprf " + settings_struct.tasks.task20_RSQ_AreasUnderUrbanization[task_position].pprField + " -pprr " + ppr_red_values_list_str[:-1] + " -pprb " + ppr_blue_values_list_str[:-1]
            # Paramètres liés aux fichiers
            command += " -epsg " + str(settings_struct.general.image.epsg) + " -ndv " + str(settings_struct.general.image.nodataValue) + " -raf " + settings_struct.general.raster.formatRaster + " -vef " + settings_struct.general.vector.formatVector + " -rae " + settings_struct.general.raster.extensionRaster + " -vee " + settings_struct.general.vector.extensionVector
            # Paramètres liés à PostGIS
            command += " -pgh " + settings_struct.general.postgis.serverName + " -pgp " + str(settings_struct.general.postgis.portNumber) + " -pgu " + settings_struct.general.postgis.userName + " -pgw " + settings_struct.general.postgis.password + " -pgd " + settings_struct.general.postgis.databaseName + " -pgs " + settings_struct.general.postgis.schemaName + " -pge " + settings_struct.general.postgis.encoding
            # Finalisation de la commande
            endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Création avec succès de la commande %s de cartographie des parcelles disponibles et constructibles." % (task_label) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('30_RSQ'): # Cartographie des évolutions d'OCS à la parcelle

            # Gestion des paramètres liste
            input_tx_files_list_str = ""
            for input_tx_file in settings_struct.tasks.task30_RSQ_EvolutionOverTime[task_position].inputTxFilesList:
                input_tx_files_list_str += input_tx_file + ' '
            evolutions_list_str = ""
            for evolution in settings_struct.tasks.task30_RSQ_EvolutionOverTime[task_position].evolutionsList:
                evolutions_list_str += evolution + ' '

            # Préparation du dictionnaire class_label_dico
            class_label_dico_str = ""
            for class_classification in settings_struct.general.classification.classList:
                class_label_dico_str += str(class_classification.label) + ':' + class_classification.name + ' '

            # Initialisation de la commande
            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)
            # Paramètres spécifiques à l'appli
            command = call_python_action_to_make + "EvolutionOverTime -in " + settings_struct.tasks.task30_RSQ_EvolutionOverTime[task_position].inputPlotVector + " -out " + settings_struct.tasks.task30_RSQ_EvolutionOverTime[task_position].outputPlotVector + " -emp " + settings_struct.tasks.task30_RSQ_EvolutionOverTime[task_position].footprintVector + " -itxl " + input_tx_files_list_str[:-1] + " -evol " + evolutions_list_str[:-1] + " -cld " + class_label_dico_str[:-1]
            # Paramètres liés aux fichiers
            command += " -epsg " + str(settings_struct.general.image.epsg) + " -ndv " + str(settings_struct.general.image.nodataValue) + " -raf " + settings_struct.general.raster.formatRaster + " -vef " + settings_struct.general.vector.formatVector + " -rae " + settings_struct.general.raster.extensionRaster + " -vee " + settings_struct.general.vector.extensionVector
            # Paramètres liés à PostGIS
            command += " -pgh " + settings_struct.general.postgis.serverName + " -pgp " + str(settings_struct.general.postgis.portNumber) + " -pgu " + settings_struct.general.postgis.userName + " -pgw " + settings_struct.general.postgis.password + " -pgd " + settings_struct.general.postgis.databaseName + " -pgs " + settings_struct.general.postgis.schemaName + " -pge " + settings_struct.general.postgis.encoding
            # Finalisation de la commande
            endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Création avec succès de la commande %s de cartographie des évolutions d'OCS à la parcelle." % (task_label) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
        if case('40_RSQ'): # Cartographie des vulnérabilités aux ICU

            # Gestion des paramètres liste
            health_vuln_fields_list_str = ""
            for health_vuln_field in settings_struct.tasks.task40_RSQ_UhiVulnerability[task_position].healthVulnFieldsList:
                health_vuln_fields_list_str += health_vuln_field + ' '
            social_vuln_fields_list_str = ""
            for social_vuln_field in settings_struct.tasks.task40_RSQ_UhiVulnerability[task_position].socialVulnFieldsList:
                social_vuln_fields_list_str += social_vuln_field + ' '

            # Initialisation de la commande
            call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)
            # Paramètres spécifiques à l'appli
            command = call_python_action_to_make + "UhiVulnerability -div " + settings_struct.tasks.task40_RSQ_UhiVulnerability[task_position].inputDivisionVector + " -ftp " + settings_struct.tasks.task40_RSQ_UhiVulnerability[task_position].footprintVector + " -pop " + settings_struct.tasks.task40_RSQ_UhiVulnerability[task_position].populationVector + " -blt " + settings_struct.tasks.task40_RSQ_UhiVulnerability[task_position].builtVector + " -out " + settings_struct.tasks.task40_RSQ_UhiVulnerability[task_position].outputVulnerabilityVector + " -idd " + settings_struct.tasks.task40_RSQ_UhiVulnerability[task_position].idDivisionField + " -idp " + settings_struct.tasks.task40_RSQ_UhiVulnerability[task_position].idPopulationField + " -idb " + settings_struct.tasks.task40_RSQ_UhiVulnerability[task_position].idBuiltField + " -sta " + settings_struct.tasks.task40_RSQ_UhiVulnerability[task_position].stakeField + " -hevl " + health_vuln_fields_list_str[:-1] + " -sovl " + social_vuln_fields_list_str[:-1] + " -hei " + settings_struct.tasks.task40_RSQ_UhiVulnerability[task_position].heightField + " -bsf " + '"' + settings_struct.tasks.task40_RSQ_UhiVulnerability[task_position].builtSqlFilter + '"'
            # Paramètres liés aux fichiers
            command += " -epsg " + str(settings_struct.general.image.epsg) + " -vef " + settings_struct.general.vector.formatVector
            # Paramètres liés à PostGIS
            command += " -pgh " + settings_struct.general.postgis.serverName + " -pgp " + str(settings_struct.general.postgis.portNumber) + " -pgu " + settings_struct.general.postgis.userName + " -pgw " + settings_struct.general.postgis.password + " -pgd " + settings_struct.general.postgis.databaseName + " -pgs " + settings_struct.general.postgis.schemaName + " -pge " + settings_struct.general.postgis.encoding
            # Finalisation de la commande
            endCommandUpdate(settings_struct, command_doc, command, debug)

            print(cyan + "writeCommands() : " + bold + green + "Création avec succès de la commande %s de cartographie des vulnérabilités aux ICU." % (task_label) + endC)
            break

        # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

        break

    # CLOTURE DE LA FONCTION WriteCommands()
    return id_command, index_remote_ip, id_task_commands_list


#################################################################################
# FONCTION crossingVectorRasterRA()                                             #
#################################################################################
# ROLE :
#   Fonction permettant de creer le fichier de sortie vecteur de l'étude RhoneAlpe par 3 croisements vecteur-rasteur
#
# ENTREES :
#   settings_struct : La structure contenant des settings
#   name_setting : nom du fichier contenant les settings
#   task_label : label de la tâche que l'on souhaite transformer en ligne de commande
#   mode_execution_command : Le mode d'execution choisi
#   error_management : Type gestion des erreurs
#   command_doc : le fichier contenant les commandes
#   dependency_commands_list_string : La liste des dépendences de taches
#   id_command : compteur d'id de commande
#   index_remote_ip : index sur la machine remote disponible courante
#   id_task_commands_list : liste des id des commandes dont dépend la tache
#   debug : niveau de trace log
#
# SORTIES :
#   id_command : compte de commande incrementé
#   index_remote_ip : index sur la machine remote disponible incrementer
#   id_task_commands_list : liste des id des commandes dont dépend la tache mis à jour avec la nouvelle tache

def crossingVectorRasterRA(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, command_doc, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list, debug):

    # Gestion de la couverture des polygones et l'identifiant unique
    #---------------------------------------------------------------

    # Preparation des parametres
    col_to_delete_couv_list_str = ""
    for colum_to_delete_couv in settings_struct.tasks.task210_RA_CrossingVectorRaster[task_position].columToDeleteCouvlist :
        col_to_delete_couv_list_str += colum_to_delete_couv + " "

    col_to_add_couv_list_str = ""
    for colum_to_add_couv in settings_struct.tasks.task210_RA_CrossingVectorRaster[task_position].columToAddCouvList:
        col_to_add_couv_list_str += colum_to_add_couv + " "

    call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list)
    command = call_python_action_to_make + "CrossingVectorRaster -i " + settings_struct.tasks.task210_RA_CrossingVectorRaster[task_position].inputClassifFile + " -v " + settings_struct.tasks.task210_RA_CrossingVectorRaster[task_position].inputVector + " -o " + settings_struct.tasks.task210_RA_CrossingVectorRaster[task_position].outputVector + " -a " + col_to_add_couv_list_str + " -d " + col_to_delete_couv_list_str + " -vef " + settings_struct.general.vector.formatVector

    endCommandUpdate(settings_struct, command_doc, command, debug)

    # Gestion de l'information d'origine et de l'information ossature
    #----------------------------------------------------------------

    # Preparation des parametres
    col_to_add_date_list_str = ""
    for colum_to_add_date in settings_struct.tasks.task210_RA_CrossingVectorRaster[task_position].columToAddDateList :
        col_to_add_date_list_str += colum_to_add_date + " "

    # Creation d'une liste pour identifier les colonnes date à supprimer
    class_label_tmp_list = settings_struct.tasks.task210_RA_CrossingVectorRaster[task_position].classLabelDateDico.split(' ')

    class_date_suppress_list = []
    col_to_del_date_list_str = ''
    for tmp_txt_class in class_label_tmp_list:
        class_label_list = tmp_txt_class.split(':')
        if class_label_list[1] not in class_date_suppress_list :
            class_date_suppress_list.append(class_label_list[1])
            col_to_del_date_list_str  += class_label_list[1] + ' '

    # Dependence local de la commande précedente
    if dependency_commands_list_string == "":
        dependency_commands_list_string_temp = str(id_command - 1)
    else :
        dependency_commands_list_string_temp = dependency_commands_list_string + "," + str(id_command - 1)

    call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string_temp, id_command, index_remote_ip, id_task_commands_list)
    command = call_python_action_to_make + "CrossingVectorRaster -i " + settings_struct.tasks.task210_RA_CrossingVectorRaster[task_position].inputCorrectionFile + " -v " + settings_struct.tasks.task210_RA_CrossingVectorRaster[task_position].outputVector + " -a " + col_to_add_date_list_str + " -d " + col_to_del_date_list_str + " -cld " + settings_struct.tasks.task210_RA_CrossingVectorRaster[task_position].classLabelDateDico + " -vef " + settings_struct.general.vector.formatVector

    endCommandUpdate(settings_struct, command_doc, command, debug)

    # Gestion de la date de l'information d'origine
    #----------------------------------------------

    # Preparation des parametres
    col_to_add_src_list_str = ""
    for colum_to_add_src in settings_struct.tasks.task210_RA_CrossingVectorRaster[task_position].columToAddSrcList :
        col_to_add_src_list_str += colum_to_add_src + " "

    # Dependence local de la commande précedente
    if dependency_commands_list_string == "":
        dependency_commands_list_string_temp = str(id_command - 1)
    else :
        dependency_commands_list_string_temp = dependency_commands_list_string + "," + str(id_command - 1)

    call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string_temp, id_command, index_remote_ip, id_task_commands_list)
    command = call_python_action_to_make + "CrossingVectorRaster -i " + settings_struct.tasks.task210_RA_CrossingVectorRaster[task_position].inputCorrectionFile + " -v " + settings_struct.tasks.task210_RA_CrossingVectorRaster[task_position].outputVector + " -a " + col_to_add_src_list_str + " -cld " + settings_struct.tasks.task210_RA_CrossingVectorRaster[task_position].classLabelSrcDico + " -vef " + settings_struct.general.vector.formatVector

    endCommandUpdate(settings_struct, command_doc, command, debug)

    return  id_command, index_remote_ip, id_task_commands_list

#################################################################################
# FONCTION parametricStudyTexturesIndices()                                       #
#################################################################################
# ROLE :
#   Fonction permettant d'enchainer une étude parametrique pour le choix des textures et des indices
#
# ENTREES :
#   settings_struct : La structure contenant des settings
#   name_setting : nom du fichier contenant les settings
#   task_label : label de la tâche que l'on souhaite transformer en ligne de commande
#   mode_execution_command : Le mode d'execution choisi
#   error_management : Type gestion des erreurs
#   command_doc : le fichier contenant les commandes
#   dependency_commands_list_string : La liste des dépendences de taches
#   id_command : compteur d'id de commande
#   index_remote_ip : index sur la machine remote disponible courante
#   id_task_commands_list : liste des id des commandes dont dépend la tache
#   debug : niveau de trace log
#
# SORTIES :
#   id_command : compte de commande incrementé
#   index_remote_ip : index sur la machine remote disponible incrementer
#   id_task_commands_list : liste des id des commandes dont dépend la tache mis à jour avec la nouvelle tache

def parametricStudyTexturesIndices(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, command_doc, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list, debug):

    study_list = []
    # Pour chaque cannal demandé
    for channel in settings_struct.tasks.task9_parametricStudyTexturesIndices.channelsList:

        # Pour chaque texture ou indice
        for texture in settings_struct.tasks.task9_parametricStudyTexturesIndices.texturesList:

            # Pour chaque valeur de rayon
            for radius in settings_struct.tasks.task9_parametricStudyTexturesIndices.radiusList:
                study_list.append([texture, channel, radius])

    # Pour indice
    for indice in settings_struct.tasks.task9_parametricStudyTexturesIndices.indicesList:
        study_list.append([indice, '', 0])

    # Pour toutes les conbinaisons d'étude paramétrique
    start = True
    for param_list in study_list:

        # Création du suffix
        texture = param_list[0]
        channel = param_list[1]
        radius = param_list[2]
        if channel == '' and  radius == 0 :
            suffix = "_" + str(texture)
        else :
            suffix = "_chan" + str(channel) + "_rad" + str(radius) + "_" + str(texture)

        # ChannelsConcatenation

        image_study_neochannel = settings_struct.tasks.task30_NeoChannelsComputation[task_position].outputPath + os.sep + os.path.splitext(os.path.basename(settings_struct.tasks.task30_NeoChannelsComputation[task_position].inputFilesList[0]))[0] + suffix + os.path.splitext(settings_struct.tasks.task30_NeoChannelsComputation[task_position].inputFilesList[0])[1]
        print(blue + image_study_neochannel + endC)

        image_for_concatenation_input_str = ""
        for image_for_concatenation in settings_struct.tasks.task40_ChannelsConcatenantion[task_position].inputFilesList:
            image_for_concatenation_input_str += image_for_concatenation + ' '
        # Ajout de l'image de texture ou d'indice
        image_for_concatenation_input_str += image_study_neochannel

        if start :
            dependency_commands_list_string_temp = dependency_commands_list_string
            start = False
        else :
            if dependency_commands_list_string == "":
                dependency_commands_list_string_temp = str(id_command - 1)
            else :
                dependency_commands_list_string_temp = dependency_commands_list_string + "," + str(id_command - 1)

        call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string_temp, id_command, index_remote_ip, id_task_commands_list)
        command = call_python_action_to_make + "ChannelsConcatenation -il " + image_for_concatenation_input_str

        if settings_struct.tasks.task40_ChannelsConcatenantion[task_position].concatenation.stackConcatenation :
            command += " -os " + os.path.splitext(settings_struct.tasks.task40_ChannelsConcatenantion[task_position].concatenation.outputFile)[0] + suffix + os.path.splitext(settings_struct.tasks.task40_ChannelsConcatenantion[task_position].concatenation.outputFile)[1]

        if settings_struct.tasks.task40_ChannelsConcatenantion[task_position].normalization.stackNormalization :
            command += " -on " + os.path.splitext(settings_struct.tasks.task40_ChannelsConcatenantion[task_position].normalization.outputFile)[0] + suffix + os.path.splitext(settings_struct.tasks.task40_ChannelsConcatenantion[task_position].normalization.outputFile)[1]

        if settings_struct.tasks.task40_ChannelsConcatenantion[task_position].reduction.stackReduction :
            command += " -oa " + os.path.splitext(settings_struct.tasks.task40_ChannelsConcatenantion[task_position].reduction.outputFile)[0] + suffix + os.path.splitext(settings_struct.tasks.task40_ChannelsConcatenantion[task_position].reduction.outputFile)[1]

            if settings_struct.tasks.task40_ChannelsConcatenantion[task_position].reduction.method.lower() == "pca":
                command += " -redce.meth PCA -redce.nbcp " + str(settings_struct.tasks.task40_ChannelsConcatenantion[task_position].reduction.maxBandNumber)

            if settings_struct.tasks.task40_ChannelsConcatenantion[task_position].reduction.method.lower() == "napca":
                command += " -redce.meth NAPCA -redce.nbcp " + str(settings_struct.tasks.task40_ChannelsConcatenantion[task_position].reduction.maxBandNumber) + " -redce.radi " + str(settings_struct.tasks.task40_ChannelsConcatenantion[task_position].reduction.napcaRadius)

            if settings_struct.tasks.task40_ChannelsConcatenantion[task_position].reduction.method.lower() == "maf":
                command += " -redce.meth MAF -redce.nbcp " + str(settings_struct.tasks.task40_ChannelsConcatenantion[task_position].reduction.maxBandNumber)

            if settings_struct.tasks.task40_ChannelsConcatenantion[task_position].reduction.method.lower() == "ica":
                command += " -redce.meth ICA -redce.nbcp " + str(settings_struct.tasks.task40_ChannelsConcatenantion[task_position].reduction.maxBandNumber) + " -redce.iter " + str(settings_struct.tasks.task40_ChannelsConcatenantion[task_position].reduction.icaIterations) + " -redce.incr " + str(settings_struct.tasks.task40_ChannelsConcatenantion[task_position].reduction.icaIncrement)

            if settings_struct.tasks.task40_ChannelsConcatenantion[task_position].reduction.normalizationReduce :
                command += " -redce.norm "

        endCommandUpdate(settings_struct, command_doc, command, debug)
        """
        # KmeansMaskApplication

        macro_classes_cleaned_mask_list_str = ""
        micro_classes_mask_list_str = ""
        centroids_list_str = ""
        macroclass_sampling_list_str = ""
        macroclass_labels_list_str = ""

        for class_macro_sample_struct in settings_struct.tasks.task90_KmeansMaskApplication[task_position].classMacroSampleList:
            macro_classes_cleaned_mask_list_str += class_macro_sample_struct.inputFile + ' '
            micro_classes_mask_list_str += os.path.splitext(class_macro_sample_struct.outputFile)[0] + suffix + os.path.splitext(class_macro_sample_struct.outputFile)[1] + ' '
            centroids_list_str += os.path.splitext(class_macro_sample_struct.outputCentroidFile)[0] + suffix + os.path.splitext(class_macro_sample_struct.outputCentroidFile)[1] + ' '
            macroclass_sampling_list_str += str(class_macro_sample_struct.sampling) + ' '
            macroclass_labels_list_str += str(class_macro_sample_struct.label) + ' '

        if dependency_commands_list_string == "":
            dependency_commands_list_string_temp = str(id_command - 1)
        else :
            dependency_commands_list_string_temp = dependency_commands_list_string + "," + str(id_command - 1)

        call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string_temp, id_command, index_remote_ip, id_task_commands_list)

        command = call_python_action_to_make + "KmeansMaskApplication -i " + os.path.splitext(settings_struct.tasks.task90_KmeansMaskApplication[task_position].inputFile)[0] + suffix + os.path.splitext(settings_struct.tasks.task90_KmeansMaskApplication[task_position].inputFile)[1] + " -o " + os.path.splitext(settings_struct.tasks.task90_KmeansMaskApplication[task_position].outputFile)[0] + suffix + os.path.splitext(settings_struct.tasks.task90_KmeansMaskApplication[task_position].outputFile)[1] + " -t " + os.path.splitext(settings_struct.tasks.task90_KmeansMaskApplication[task_position].proposalTable)[0] + suffix + os.path.splitext(settings_struct.tasks.task90_KmeansMaskApplication[task_position].proposalTable)[1] + " -ml " + macro_classes_cleaned_mask_list_str + " -ol " + micro_classes_mask_list_str + " -cl " + centroids_list_str + " -msl " + macroclass_sampling_list_str + " -mll " + macroclass_labels_list_str + " -kmp.it " + str(settings_struct.tasks.task90_KmeansMaskApplication[task_position].iterations) + " -kmp.th " + str(settings_struct.tasks.task90_KmeansMaskApplication[task_position].threshold) + " -kmp.pr " + str(settings_struct.tasks.task90_KmeansMaskApplication[task_position].propPixels) + " -kmp.sz " + str(settings_struct.tasks.task90_KmeansMaskApplication[task_position].sizeTraining) + " -npt " + str(settings_struct.tasks.task90_KmeansMaskApplication[task_position].minNumberTrainingSize) + " -rcmc " + str(settings_struct.tasks.task90_KmeansMaskApplication[task_position].rateCleanMicroclass)

        if settings_struct.general.processing.ram != 0:
            command += " -ram " + str(settings_struct.general.processing.ram)

        endCommandUpdate(settings_struct, command_doc, command, debug)

        # MicroSamplePolygonization

        micro_classes_mask_list_str = ""
        raster_erode_list_str = ""
        buffer_size_list_str = ""
        buffer_approximate_list_str = ""
        minimal_area_list_str = ""
        simplification_tolerance_list_str = ""

        for input_file_struct in settings_struct.tasks.task100_MicroSamplePolygonization[task_position].inputFileList:
            micro_classes_mask_list_str += os.path.splitext(input_file_struct.inputFile)[0] + suffix + os.path.splitext(input_file_struct.inputFile)[1] + ' '
            raster_erode_list_str += str(input_file_struct.rasterErode) + ' '
            buffer_size_list_str += str(input_file_struct.bufferSize) + ' '
            buffer_approximate_list_str += str(input_file_struct.bufferApproximate) + ' '
            minimal_area_list_str += str(input_file_struct.minimalArea) + ' '
            simplification_tolerance_list_str += str(input_file_struct.simplificationTolerance) + ' '

        if dependency_commands_list_string == "":
            dependency_commands_list_string_temp = str(id_command - 1)
        else :
            dependency_commands_list_string_temp = dependency_commands_list_string + "," + str(id_command - 1)

        call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string_temp, id_command, index_remote_ip, id_task_commands_list)

        command = call_python_action_to_make + "MicroSamplePolygonization -il " + micro_classes_mask_list_str + " -o " + os.path.splitext(settings_struct.tasks.task100_MicroSamplePolygonization[task_position].outputFile)[0] + suffix + os.path.splitext(settings_struct.tasks.task100_MicroSamplePolygonization[task_position].outputFile)[1] + " -t " + os.path.splitext(settings_struct.tasks.task100_MicroSamplePolygonization[task_position].proposalTable)[0] + suffix + os.path.splitext(settings_struct.tasks.task100_MicroSamplePolygonization[task_position].proposalTable)[1] + " -ero " + raster_erode_list_str + " -umc " + str(settings_struct.tasks.task100_MicroSamplePolygonization[task_position].umc) + " -ts " + str(settings_struct.tasks.task100_MicroSamplePolygonization[task_position].tileSize) + " -bsl " + buffer_size_list_str + " -bal " + buffer_approximate_list_str + " -mal " + minimal_area_list_str + " -stl " + simplification_tolerance_list_str + " -rcmc " + str(settings_struct.tasks.task100_MicroSamplePolygonization[task_position].rateCleanMicroclass) + " -sgf GEOMETRY -vgt POLYGON -vef " + settings_struct.general.vector.formatVector + " -pe UTF-8 -epsg " + str(settings_struct.general.image.epsg) + " -col " + str(settings_struct.general.classification.columnName)

        endCommandUpdate(settings_struct, command_doc, command, debug)
        """

        # SupervisedClassification

        if dependency_commands_list_string == "":
            dependency_commands_list_string_temp = str(id_command - 1)
        else :
            dependency_commands_list_string_temp = dependency_commands_list_string + "," + str(id_command - 1)

        call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string_temp, id_command, index_remote_ip, id_task_commands_list)

        """
        command = call_python_action_to_make + "SupervisedClassification -i " + os.path.splitext(settings_struct.tasks.task120_SupervisedClassification[task_position].inputFile)[0] + suffix + os.path.splitext(settings_struct.tasks.task120_SupervisedClassification[task_position].inputFile)[1] + " -v " + os.path.splitext(settings_struct.tasks.task120_SupervisedClassification[task_position].inputVector)[0] + suffix + os.path.splitext(settings_struct.tasks.task120_SupervisedClassification[task_position].inputVector)[1] + " -o " + os.path.splitext(settings_struct.tasks.task120_SupervisedClassification[task_position].outputFile)[0] + suffix + os.path.splitext(settings_struct.tasks.task120_SupervisedClassification[task_position].outputFile)[1] + " -c " + os.path.splitext(settings_struct.tasks.task120_SupervisedClassification[task_position].confidenceOutputFile)[0] + suffix + os.path.splitext(settings_struct.tasks.task120_SupervisedClassification[task_position].confidenceOutputFile)[1] + " -sm " + str(settings_struct.tasks.task120_SupervisedClassification[task_position].samplerMode) + " -per " + str(settings_struct.tasks.task120_SupervisedClassification[task_position].periodicJitter) + " -fc " +str(settings_struct.general.classification.columnName) + " -cm " + settings_struct.tasks.task120_SupervisedClassification[task_position].method.lower()
        """

        command = call_python_action_to_make + "SupervisedClassification -i " + os.path.splitext(settings_struct.tasks.task40_ChannelsConcatenantion[task_position].concatenation.outputFile)[0] + suffix + os.path.splitext(settings_struct.tasks.task40_ChannelsConcatenantion[task_position].concatenation.outputFile)[1] + " -se " + settings_struct.tasks.task9_parametricStudyTexturesIndices.inputSample + " -o " + os.path.splitext(settings_struct.tasks.task120_SupervisedClassification[task_position].outputFile)[0] + suffix + os.path.splitext(settings_struct.tasks.task120_SupervisedClassification[task_position].outputFile)[1] + " -c " + os.path.splitext(settings_struct.tasks.task120_SupervisedClassification[task_position].confidenceOutputFile)[0] + suffix + os.path.splitext(settings_struct.tasks.task120_SupervisedClassification[task_position].confidenceOutputFile)[1] + " -sm " + str(settings_struct.tasks.task120_SupervisedClassification[task_position].samplerMode) + " -per " + str(settings_struct.tasks.task120_SupervisedClassification[task_position].periodicJitter) + " -fc " +str(settings_struct.general.classification.columnName) + " -cm " + settings_struct.tasks.task120_SupervisedClassification[task_position].method.lower()

        if settings_struct.tasks.task120_SupervisedClassification[task_position].method.lower() == "svm":
            command += " -k " + str(settings_struct.tasks.task120_SupervisedClassification[task_position].svn_kernel)

        if settings_struct.tasks.task120_SupervisedClassification[task_position].method.lower() == "rf":
            command += " -depth " + str(settings_struct.tasks.task120_SupervisedClassification[task_position].rf_dephTree) + " -min " + str(settings_struct.tasks.task120_SupervisedClassification[task_position].rf_sampleMin) + " -crit " + str(settings_struct.tasks.task120_SupervisedClassification[task_position].rf_terminCriteria) + " -clust " + str(settings_struct.tasks.task120_SupervisedClassification[task_position].rf_cluster) + " -size " + str(settings_struct.tasks.task120_SupervisedClassification[task_position].rf_sizeFeatures) + " -num " + str(settings_struct.tasks.task120_SupervisedClassification[task_position].rf_numTree) + " -obb " + str(settings_struct.tasks.task120_SupervisedClassification[task_position].rf_obbError)

        if settings_struct.general.processing.ram != 0:
            command += " -ram " + str(settings_struct.general.processing.ram)

        endCommandUpdate(settings_struct, command_doc, command, debug)

        # MicroClassesFusion

        if dependency_commands_list_string == "":
            dependency_commands_list_string_temp = str(id_command - 1)
        else :
            dependency_commands_list_string_temp = dependency_commands_list_string + "," + str(id_command - 1)

        call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string_temp, id_command, index_remote_ip, id_task_commands_list)

        command = call_python_action_to_make + "MicroClassesFusion -i " + os.path.splitext(settings_struct.tasks.task120_SupervisedClassification[task_position].outputFile)[0] + suffix + os.path.splitext(settings_struct.tasks.task120_SupervisedClassification[task_position].outputFile)[1] + " -o " + os.path.splitext(settings_struct.tasks.task160_MicroclassFusion[task_position].outputFile)[0] + suffix + os.path.splitext(settings_struct.tasks.task160_MicroclassFusion[task_position].outputFile)[1] + " -exp " + '"' + settings_struct.tasks.task160_MicroclassFusion[task_position].expression + '"'

        endCommandUpdate(settings_struct, command_doc, command, debug)

        # MajorityFilter

        if dependency_commands_list_string == "":
            dependency_commands_list_string_temp = str(id_command - 1)
        else :
            dependency_commands_list_string_temp = dependency_commands_list_string + "," + str(id_command - 1)

        call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string_temp, id_command, index_remote_ip, id_task_commands_list)

        command = call_python_action_to_make + "MajorityFilter -i " + os.path.splitext(settings_struct.tasks.task160_MicroclassFusion[task_position].outputFile)[0] + suffix + os.path.splitext(settings_struct.tasks.task160_MicroclassFusion[task_position].outputFile)[1] + " -o " + os.path.splitext(settings_struct.tasks.task170_MajorityFilter[task_position].outputFile)[0] + suffix + os.path.splitext(settings_struct.tasks.task170_MajorityFilter[task_position].outputFile)[1] + " -m " + settings_struct.tasks.task170_MajorityFilter[task_position].filterMode + " -r " + str(settings_struct.tasks.task170_MajorityFilter[task_position].radiusMajority) + " -umc " + str(settings_struct.tasks.task170_MajorityFilter[task_position].umcPixels)

        endCommandUpdate(settings_struct, command_doc, command, debug)

        # QualityIndicatorComputation

        if dependency_commands_list_string == "":
            dependency_commands_list_string_temp = str(id_command - 1)
        else :
            dependency_commands_list_string_temp = dependency_commands_list_string + "," + str(id_command - 1)

        call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string_temp, id_command, index_remote_ip, id_task_commands_list)

        command = call_python_action_to_make + "QualityIndicatorComputation -i " + os.path.splitext(settings_struct.tasks.task170_MajorityFilter[task_position].outputFile)[0] + suffix + os.path.splitext(settings_struct.tasks.task170_MajorityFilter[task_position].outputFile)[1] + " -v " + settings_struct.tasks.task9_parametricStudyTexturesIndices.inputVector + " -ocm " + os.path.splitext(settings_struct.tasks.task9_parametricStudyTexturesIndices.outputMatrix)[0] + suffix + os.path.splitext(settings_struct.tasks.task9_parametricStudyTexturesIndices.outputMatrix)[1] + " -oqi " + settings_struct.tasks.task9_parametricStudyTexturesIndices.outputFile + " -id " + settings_struct.general.classification.columnName + " -text " + texture + "," + channel + "," + str(radius)

        endCommandUpdate(settings_struct, command_doc, command, debug)


    return  id_command, index_remote_ip, id_task_commands_list

#################################################################################
# FONCTION parametricStudySamples()                                             #
#################################################################################
# ROLE :
#   Fonction permettant d'enchainer une étude parametrique pour le choix du taux d'echantillons
#
# ENTREES :
#   settings_struct : La structure contenant des settings
#   name_setting : nom du fichier contenant les settings
#   task_label : label de la tâche que l'on souhaite transformer en ligne de commande
#   mode_execution_command : Le mode d'execution choisi
#   error_management : Type gestion des erreurs
#   command_doc : le fichier contenant les commandes
#   dependency_commands_list_string : La liste des dépendences de taches
#   id_command : compteur d'id de commande
#   index_remote_ip : index sur la machine remote disponible courante
#   id_task_commands_list : liste des id des commandes dont dépend la tache
#   debug : niveau de trace log
#
# SORTIES :
#   id_command : compte de commande incrementé
#   index_remote_ip : index sur la machine remote disponible incrementer
#   id_task_commands_list : liste des id des commandes dont dépend la tache mis à jour avec la nouvelle tache

def parametricStudySamples(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, command_doc, dependency_commands_list_string, id_command, index_remote_ip, id_task_commands_list, debug):

    study_rate_list = []

    # Pour indice
    for rate in settings_struct.tasks.task8_ParametricStudySamples.ratesList:
        study_rate_list.append(rate)

    # Pour toutes les conbinaisons d'étude paramétrique
    start = True
    for rate in study_rate_list:

        # Création du suffix
        suffix =  "_" + rate.replace('.','_')

        vector_samples_study = os.path.splitext(settings_struct.tasks.task115_SampleSelectionRaster[task_position].outputVector)[0] + suffix + os.path.splitext(settings_struct.tasks.task115_SampleSelectionRaster[task_position].outputVector)[1]

        table_statistics_study = os.path.splitext(settings_struct.tasks.task115_SampleSelectionRaster[task_position].outputStatisticsTable)[0] + suffix + os.path.splitext(settings_struct.tasks.task115_SampleSelectionRaster[task_position].outputStatisticsTable)[1]

        # Sélection des échantillons points par micro classes

        ratio_per_class_dico_str = ""
        for ratio_class_struct in settings_struct.tasks.task115_SampleSelectionRaster[task_position].ratioPerClassList:
            ratio_per_class_dico_str += str(ratio_class_struct.label) + "," + str(rate) + " "

        if start :
            dependency_commands_list_string_temp = dependency_commands_list_string
            start = False
        else :
            if dependency_commands_list_string == "":
                dependency_commands_list_string_temp = str(id_command - 1)
            else :
                dependency_commands_list_string_temp = dependency_commands_list_string + "," + str(id_command - 1)

        call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string_temp, id_command, index_remote_ip, id_task_commands_list)

        command = call_python_action_to_make + "SampleSelectionRaster -i " + settings_struct.tasks.task115_SampleSelectionRaster[task_position].inputFile + " -s " + settings_struct.tasks.task115_SampleSelectionRaster[task_position].inputSample + " -o " + vector_samples_study + " -t " + table_statistics_study + " -st percent " + " -col " + str(settings_struct.general.classification.columnName)

        if ratio_per_class_dico_str != "":
            command += " -rpc " + ratio_per_class_dico_str

        endCommandUpdate(settings_struct, command_doc, command, debug)

        # SupervisedClassification

        if dependency_commands_list_string == "":
            dependency_commands_list_string_temp = str(id_command - 1)
        else :
            dependency_commands_list_string_temp = dependency_commands_list_string + "," + str(id_command - 1)

        call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string_temp, id_command, index_remote_ip, id_task_commands_list)

        command = call_python_action_to_make + "SupervisedClassification -i " + settings_struct.tasks.task120_SupervisedClassification[task_position].inputFile + " -s " + vector_samples_study + " -o " + os.path.splitext(settings_struct.tasks.task120_SupervisedClassification[task_position].outputFile)[0] + suffix + os.path.splitext(settings_struct.tasks.task120_SupervisedClassification[task_position].outputFile)[1] + " -c " + os.path.splitext(settings_struct.tasks.task120_SupervisedClassification[task_position].confidenceOutputFile)[0] + suffix + os.path.splitext(settings_struct.tasks.task120_SupervisedClassification[task_position].confidenceOutputFile)[1] + " -sm " + str(settings_struct.tasks.task120_SupervisedClassification[task_position].samplerMode) + " -per " + str(settings_struct.tasks.task120_SupervisedClassification[task_position].periodicJitter) + " -fc " +str(settings_struct.general.classification.columnName) + " -cm " + settings_struct.tasks.task120_SupervisedClassification[task_position].method.lower()

        if settings_struct.tasks.task120_SupervisedClassification[task_position].method.lower() == "svm":
            command += " -k " + str(settings_struct.tasks.task120_SupervisedClassification[task_position].svn_kernel)

        if settings_struct.tasks.task120_SupervisedClassification[task_position].method.lower() == "rf":
            command += " -depth " + str(settings_struct.tasks.task120_SupervisedClassification[task_position].rf_dephTree) + " -min " + str(settings_struct.tasks.task120_SupervisedClassification[task_position].rf_sampleMin) + " -crit " + str(settings_struct.tasks.task120_SupervisedClassification[task_position].rf_terminCriteria) + " -clust " + str(settings_struct.tasks.task120_SupervisedClassification[task_position].rf_cluster) + " -size " + str(settings_struct.tasks.task120_SupervisedClassification[task_position].rf_sizeFeatures) + " -num " + str(settings_struct.tasks.task120_SupervisedClassification[task_position].rf_numTree) + " -obb " + str(settings_struct.tasks.task120_SupervisedClassification[task_position].rf_obbError)

        if settings_struct.general.processing.ram != 0:
            command += " -ram " + str(settings_struct.general.processing.ram)

        endCommandUpdate(settings_struct, command_doc, command, debug)

        # MicroClassesFusion

        if dependency_commands_list_string == "":
            dependency_commands_list_string_temp = str(id_command - 1)
        else :
            dependency_commands_list_string_temp = dependency_commands_list_string + "," + str(id_command - 1)

        call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string_temp, id_command, index_remote_ip, id_task_commands_list)

        command = call_python_action_to_make + "MicroClassesFusion -i " + os.path.splitext(settings_struct.tasks.task120_SupervisedClassification[task_position].outputFile)[0] + suffix + os.path.splitext(settings_struct.tasks.task120_SupervisedClassification[task_position].outputFile)[1] + " -o " + os.path.splitext(settings_struct.tasks.task160_MicroclassFusion[task_position].outputFile)[0] + suffix + os.path.splitext(settings_struct.tasks.task160_MicroclassFusion[task_position].outputFile)[1] + " -exp " + '"' + settings_struct.tasks.task160_MicroclassFusion[task_position].expression + '"'

        endCommandUpdate(settings_struct, command_doc, command, debug)

        # MajorityFilter

        if dependency_commands_list_string == "":
            dependency_commands_list_string_temp = str(id_command - 1)
        else :
            dependency_commands_list_string_temp = dependency_commands_list_string + "," + str(id_command - 1)

        call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string_temp, id_command, index_remote_ip, id_task_commands_list)

        command = call_python_action_to_make + "MajorityFilter -i " + os.path.splitext(settings_struct.tasks.task160_MicroclassFusion[task_position].outputFile)[0] + suffix + os.path.splitext(settings_struct.tasks.task160_MicroclassFusion[task_position].outputFile)[1] + " -o " + os.path.splitext(settings_struct.tasks.task170_MajorityFilter[task_position].outputFile)[0] + suffix + os.path.splitext(settings_struct.tasks.task170_MajorityFilter[task_position].outputFile)[1] + " -r " + str(settings_struct.tasks.task170_MajorityFilter[task_position].radiusMajority)

        endCommandUpdate(settings_struct, command_doc, command, debug)

        # QualityIndicatorComputation

        if dependency_commands_list_string == "":
            dependency_commands_list_string_temp = str(id_command - 1)
        else :
            dependency_commands_list_string_temp = dependency_commands_list_string + "," + str(id_command - 1)

        call_python_action_to_make, id_command, index_remote_ip, id_task_commands_list = getCallPythonActionToMake(settings_struct, name_setting, task_label, task_position, mode_execution_command, error_management, dependency_commands_list_string_temp, id_command, index_remote_ip, id_task_commands_list)

        command = call_python_action_to_make + "QualityIndicatorComputation -i " + os.path.splitext(settings_struct.tasks.task170_MajorityFilter[task_position].outputFile)[0] + suffix + os.path.splitext(settings_struct.tasks.task170_MajorityFilter[task_position].outputFile)[1] + " -v " + settings_struct.tasks.task8_ParametricStudySamples.inputVector + " -ocm " + os.path.splitext(settings_struct.tasks.task8_ParametricStudySamples.outputMatrix)[0] + suffix + os.path.splitext(settings_struct.tasks.task8_ParametricStudySamples.outputMatrix)[1] + " -oqi " + settings_struct.tasks.task8_ParametricStudySamples.outputFile + " -id " + settings_struct.general.classification.columnName + " -text Rate" + suffix + ",, "

        endCommandUpdate(settings_struct, command_doc, command, debug)

    return  id_command, index_remote_ip, id_task_commands_list
