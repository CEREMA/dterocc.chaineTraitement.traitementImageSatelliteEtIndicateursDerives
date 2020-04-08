#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerSO/DALETT/SCGSI  All rights reserved.                                                                            #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# FONCTIONS DE PARSEUR DU FICHIER XML DES SETTINGS                                                                                          #
#                                                                                                                                           #
#############################################################################################################################################

# Import des bibliothèques python
import os, sys
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC
from Lib_text import cleanSpaceText
from Lib_xml import parseDom, findElement, findAllElement, getValueNodeDataDom, getListNodeDataDom, getValueAttributeDom, getListValueAttributeDom
from Settings import *

###########################################################################################################################################
# FONCTION xmlSettingsParser()                                                                                                            #
###########################################################################################################################################
# ROLE:
#    Parser un fichier de setting au format xml contenant les settings de la chaine (parser méthode dom)
#
# ENTREES DE LA FONCTION :
#    settings_file : Fichier d'entrée des settings (.xml)
#
# SORTIES DE LA FONCTION :
#    Une structure contenant tous les paramètres contenu dans le fichier de setting
#

def xmlSettingsParser(settings_file) :

    # Initialisation de la structure
    settings_struct = StructSettings()

    # Lecture du fichier xml
    xmldoc = parseDom(settings_file)

    # Recupération des valeurs
    name_setting = os.path.splitext(os.path.basename(settings_file))[0]

    # General-Version
    settings_struct.general.version = getValueNodeDataDom(xmldoc, 'Version')

    # General-Processing
    settings_struct.general.processing.commandFile = getValueNodeDataDom(xmldoc, 'CommandFile')
    settings_struct.general.processing.logFile = getValueNodeDataDom(xmldoc, 'LogFile')

    # General-Processing-TasksList
    tasks_list = getListNodeDataDom(xmldoc, 'TasksList', 'Task')
    tasks_dependency_list = getListValueAttributeDom(xmldoc, 'TasksList', 'Task', 'dependency', 'Processing')
    tasks_execution_list = getListValueAttributeDom(xmldoc, 'TasksList', 'Task', 'execution', 'Processing')
    tasks_position_list = getListValueAttributeDom(xmldoc, 'TasksList', 'Task', 'position', 'Processing')
    tasks_error_management_list = getListValueAttributeDom(xmldoc, 'TasksList', 'Task', 'error_management', 'Processing')
    settings_struct.general.processing.taskList = []
    for index in range (len(tasks_list)) :
        task_struct = StructTask()
        task_label = cleanSpaceText(tasks_list[index])
        task_execution = tasks_execution_list[index]
        tasks_position = tasks_position_list[index]
        ######################################################
        task_label_list = task_label.split('.')
        if tasks_position == "" and len(task_label_list) == 2:
            task_label = task_label_list[0]
            tasks_position = task_label_list[1]
        ######################################################
        tasks_error_management = tasks_error_management_list[index]
        task_struct.taskLabel = task_label
        task_struct.typeExecution = task_execution
        if tasks_position != "" and tasks_position is not None:
            task_struct.position = int(tasks_position)
        if tasks_error_management != "" and tasks_error_management is not None:
            task_struct.errorManagement = tasks_error_management.lower() == 'true'
        else :
            task_struct.errorManagement = True
        task_struct.settings = name_setting
        dependency_list_string = str(tasks_dependency_list[index])
        dependency_list = dependency_list_string.split(',')
        task_struct.dependencyTaskList = []
        for dependency in dependency_list:
            if dependency != '':
                task_struct.dependencyTaskList.append(dependency)
        settings_struct.general.processing.taskList.append(task_struct)

    # General-Processing-RemoteComputeursList
    remotes_computeurs_list = getListNodeDataDom(xmldoc, 'RemoteComputeursList', 'RemoteComputeur')
    remotes_login_list = getListValueAttributeDom(xmldoc, 'RemoteComputeursList', 'RemoteComputeur', 'login', 'Processing')
    remotes_password_list = getListValueAttributeDom(xmldoc, 'RemoteComputeursList', 'RemoteComputeur', 'password', 'Processing')
    settings_struct.general.processing.remoteComputeurList = []
    for index in range (len(remotes_computeurs_list)) :
        remote_struct = StructRemote()
        ip_adress = remotes_computeurs_list[index]
        login = remotes_login_list[index]
        password = remotes_password_list[index]
        remote_struct.ip_adress = ip_adress
        remote_struct.login = login
        remote_struct.password = password
        settings_struct.general.processing.remoteComputeurList.append(remote_struct)

    # General-Processing
    settings_struct.general.processing.newStudy = getValueNodeDataDom(xmldoc, 'NewStudy').lower() == 'true'
    if getValueNodeDataDom(xmldoc, 'Running') != "" :
        settings_struct.general.processing.running = getValueNodeDataDom(xmldoc, 'Running').lower() == 'true'
    settings_struct.general.processing.overWriting = getValueNodeDataDom(xmldoc, 'OverWriting').lower() == 'true'
    settings_struct.general.processing.saveIntermediateResults = getValueNodeDataDom(xmldoc, 'SaveIntermediateResults').lower() == 'true'
    value = getValueNodeDataDom(xmldoc, 'Debug')
    if value != "" and value is not None:
        settings_struct.general.processing.debug = int(value)
    settings_struct.general.processing.link = getValueNodeDataDom(xmldoc, 'Link')
    value = getValueNodeDataDom(xmldoc, 'Port')
    if value != "" and value is not None:
        settings_struct.general.processing.port = int(value)
    value = getValueNodeDataDom(xmldoc, 'Ram')
    if value != "" and value is not None:
        settings_struct.general.processing.ram = int(value)

    # General-Image
    settings_struct.general.image.channelOrderList = getListNodeDataDom(xmldoc, 'ChannelsOrderList', 'Channel', 'Image')
    value = getValueNodeDataDom(xmldoc, 'Resolution', 'Image')
    if value != "" and value is not None:
        settings_struct.general.image.resolution = float(value)
    value = getValueNodeDataDom(xmldoc, 'Epsg', 'Image')
    if value != "" and value is not None:
        settings_struct.general.image.epsg = int(value)
    value = getValueNodeDataDom(xmldoc, 'NodataValue', 'Image')
    if value != "" and value is not None:
        settings_struct.general.image.nodataValue = int(value)

    # General-Raster
    formatRaster = getValueNodeDataDom(xmldoc, 'FormatRaster','Raster')
    if formatRaster != "" :
        settings_struct.general.raster.formatRaster = formatRaster
    extensionRaster = getValueNodeDataDom(xmldoc, 'ExtensionRaster','Raster')
    if extensionRaster != "" :
        settings_struct.general.raster.extensionRaster = extensionRaster

    # General-Vector
    formatVector = getValueNodeDataDom(xmldoc, 'FormatVector','Vector')
    if formatVector != "" :
        settings_struct.general.vector.formatVector = formatVector
    extensionVector = getValueNodeDataDom(xmldoc, 'ExtensionVector','Vector')
    if extensionVector != "" :
        settings_struct.general.vector.extensionVector = extensionVector

    # General-Classification
    settings_struct.general.classification.columnName = getValueNodeDataDom(xmldoc, 'ColumnName')
    elements_list = findAllElement(xmldoc, 'Class', 'Classification/Classlist')
    settings_struct.general.classification.classList = []
    for element in elements_list:
        class_struct = StructClassification()
        class_struct.name = getValueNodeDataDom(element, 'Name')
        value = getValueNodeDataDom(element, 'Label')
        if value != "" and value is not None:
            class_struct.label = int(value)
        else:
            class_struct.label = 0
        settings_struct.general.classification.classList.append(class_struct)

    # General-Postgis
    settings_struct.general.postgis.encoding = getValueNodeDataDom(xmldoc, 'Encoding', 'Postgis')
    settings_struct.general.postgis.serverName = getValueNodeDataDom(xmldoc, 'ServerName', 'Postgis')
    value = getValueNodeDataDom(xmldoc, 'PortNumber','Postgis')
    if value != "" and value is not None:
        settings_struct.general.postgis.portNumber = int(value)
    settings_struct.general.postgis.userName = getValueNodeDataDom(xmldoc, 'UserName','Postgis')
    settings_struct.general.postgis.password = getValueNodeDataDom(xmldoc, 'Password', 'Postgis')
    settings_struct.general.postgis.databaseName = getValueNodeDataDom(xmldoc, 'DatabaseName','Postgis')
    settings_struct.general.postgis.schemaName = getValueNodeDataDom(xmldoc, 'SchemaName','Postgis')

    # Task1_Print
    task1_Print_elem_list = findAllElement(xmldoc, 'Task1_Print','Tasks/Task1_Print_List')
    for pos in range (len(task1_Print_elem_list)):
        task1_Print_elem = task1_Print_elem_list[pos]
        settings_struct.tasks.task1_Print.append(StructTask1_Print())
        texts_list = getListNodeDataDom(task1_Print_elem, 'CommentList', 'Comment')
        styles_list = getListValueAttributeDom(task1_Print_elem, 'CommentList', 'Comment', 'style')
        settings_struct.tasks.task1_Print[pos].commentsList = []
        for index in range (len(texts_list)) :
            text = texts_list[index]
            style = styles_list[index]
            comment_struct = StructPrint_Comment()
            comment_struct.text = text
            comment_struct.style = style
            settings_struct.tasks.task1_Print[pos].commentsList.append(comment_struct)

    # Task2_Mail
    task2_Mail_elem_list = findAllElement(xmldoc, 'Task2_Mail','Tasks/Task2_Mail_List')
    for pos in range (len(task2_Mail_elem_list)):
        task2_Mail_elem = task2_Mail_elem_list[pos]
        settings_struct.tasks.task2_Mail.append(StructTask2_Mail())
        settings_struct.tasks.task2_Mail[pos].addrMailSender = getValueNodeDataDom(task2_Mail_elem, 'AddrMailSender')
        settings_struct.tasks.task2_Mail[pos].passwordMailSender = getValueNodeDataDom(task2_Mail_elem, 'PasswordMailSender')
        settings_struct.tasks.task2_Mail[pos].addrServerMail = getValueNodeDataDom(task2_Mail_elem, 'AddrServerMail')
        value = getValueNodeDataDom(task2_Mail_elem, 'PortServerMail')
        if value != "" and value is not None:
            settings_struct.tasks.task2_Mail[pos].portServerMail = int(value)
        settings_struct.tasks.task2_Mail[pos].addrMailReceivesList = getListNodeDataDom(task2_Mail_elem, 'AddrMailReceivesList','AddrMailReceive')
        settings_struct.tasks.task2_Mail[pos].subjectOfMessage = getValueNodeDataDom(task2_Mail_elem, 'SubjectOfMessage')
        settings_struct.tasks.task2_Mail[pos].messagesList = getListNodeDataDom(task2_Mail_elem, 'MessagesList','Message')

    # Task3_Delete
    task3_Delete_elem_list = findAllElement(xmldoc, 'Task3_Delete','Tasks/Task3_Delete_List')
    for pos in range (len(task3_Delete_elem_list)):
        task3_Delete_elem = task3_Delete_elem_list[pos]
        settings_struct.tasks.task3_Delete.append(StructTask3_Delete())
        data_list = getListNodeDataDom(task3_Delete_elem, 'DataToCleanList', 'DataToClean')
        settings_struct.tasks.task3_Delete[pos].commentsList = []
        for index in range (len(data_list)) :
            data = data_list[index]
            settings_struct.tasks.task3_Delete[pos].dataToCleanList.append(data)

    # Task4_Copy
    task4_Copy_elem_list = findAllElement(xmldoc, 'Task4_Copy','Tasks/Task4_Copy_List')
    for pos in range (len(task4_Copy_elem_list)):
        task4_Copy_elem = task4_Copy_elem_list[pos]
        settings_struct.tasks.task4_Copy.append(StructTask4_Copy())
        elements_list = findAllElement(task4_Copy_elem, 'DataToCopy', 'DataToCopyList')
        settings_struct.tasks.task4_Copy[pos].dataToCopyList = []
        for element in elements_list:
            copy_src_dest_struct = StructCopy_SrcDest()
            copy_src_dest_struct.source = getValueNodeDataDom(element, 'Source')
            copy_src_dest_struct.destination = getValueNodeDataDom(element, 'Destination')
            settings_struct.tasks.task4_Copy[pos].dataToCopyList.append(copy_src_dest_struct)

    # Task5_ReceiveFTP
    task5_ReceiveFTP_elem_list = findAllElement(xmldoc, 'Task5_ReceiveFTP','Tasks/Task5_ReceiveFTP_List')
    for pos in range (len(task5_ReceiveFTP_elem_list)):
        task5_ReceiveFTP_elem = task5_ReceiveFTP_elem_list[pos]
        settings_struct.tasks.task5_ReceiveFTP.append(StructTask5_ReceiveFTP())
        settings_struct.tasks.task5_ReceiveFTP[pos].serverFtp = getValueNodeDataDom(task5_ReceiveFTP_elem, 'ServerFtp')
        value = getValueNodeDataDom(task5_ReceiveFTP_elem, 'PortFtp')
        if value != "" and value is not None:
            settings_struct.tasks.task5_ReceiveFTP[pos].portFtp = int(value)
        settings_struct.tasks.task5_ReceiveFTP[pos].loginFtp = getValueNodeDataDom(task5_ReceiveFTP_elem, 'LoginFtp')
        settings_struct.tasks.task5_ReceiveFTP[pos].passwordFtp = getValueNodeDataDom(task5_ReceiveFTP_elem, 'PasswordFtp')
        settings_struct.tasks.task5_ReceiveFTP[pos].pathFtp = getValueNodeDataDom(task5_ReceiveFTP_elem, 'PathFtp')
        settings_struct.tasks.task5_ReceiveFTP[pos].localPath = getValueNodeDataDom(task5_ReceiveFTP_elem, 'LocalPath')
        settings_struct.tasks.task5_ReceiveFTP[pos].fileError = getValueNodeDataDom(task5_ReceiveFTP_elem, 'FileError')

    # Task6_GenericCommand
    task6_GenericCommand_elem_list = findAllElement(xmldoc, 'Task6_GenericCommand','Tasks/Task6_GenericCommand_List')
    for pos in range (len(task6_GenericCommand_elem_list)):
        task6_GenericCommand_elem = task6_GenericCommand_elem_list[pos]
        settings_struct.tasks.task6_GenericCommand.append(StructTask6_GenericCommand())
        settings_struct.tasks.task6_GenericCommand[pos].command = getValueNodeDataDom(task6_GenericCommand_elem, 'Command')

    # Task7_GenericSql
    task7_GenericSql_elem_list = findAllElement(xmldoc, 'Task7_GenericSql','Tasks/Task7_GenericSql_List')
    for pos in range (len(task7_GenericSql_elem_list)):
        task7_GenericSql_elem = task7_GenericSql_elem_list[pos]
        settings_struct.tasks.task7_GenericSql.append(StructTask7_GenericSql())
        input_files_list = getListNodeDataDom(task7_GenericSql_elem, 'InputFilesList','InputFile')
        tables_list = getListValueAttributeDom(task7_GenericSql_elem, 'InputFilesList', 'InputFile', 'table')
        encodings_list = getListValueAttributeDom(task7_GenericSql_elem, 'InputFilesList', 'InputFile', 'encoding')
        delimiters_list = getListValueAttributeDom(task7_GenericSql_elem, 'InputFilesList', 'InputFile', 'delimiter')
        columns_list = getListValueAttributeDom(task7_GenericSql_elem, 'InputFilesList', 'InputFile', 'columns')
        tile_size_list = getListValueAttributeDom(task7_GenericSql_elem, 'InputFilesList', 'InputFile', 'tile_size')
        overview_factor_list = getListValueAttributeDom(task7_GenericSql_elem, 'InputFilesList', 'InputFile', 'overview_factor')
        for index in range (len(input_files_list)) :
            input_file = input_files_list[index]
            table_name = tables_list[index]
            encoding = encodings_list[index]
            delimiter = delimiters_list[index]
            column = columns_list[index]
            tile_size = tile_size_list[index]
            overview_factor = overview_factor_list[index]
            input_file_struct = StructSQL_InputFile()
            input_file_struct.inputFile = input_file
            input_file_struct.tableName = table_name
            input_file_struct.encoding = encoding
            input_file_struct.delimiter = delimiter
            input_file_struct.columnsTypeList = column.split(',')
            if input_file_struct.columnsTypeList[0] == '' :
                input_file_struct.columnsTypeList = []
            input_file_struct.tile_size = tile_size
            input_file_struct.overview_factor = overview_factor
            settings_struct.tasks.task7_GenericSql[pos].inputFilesList.append(input_file_struct)
        settings_struct.tasks.task7_GenericSql[pos].commandsSqlList = getListNodeDataDom(task7_GenericSql_elem, 'CommandsSqlList','CommandSql')
        output_files_list = getListNodeDataDom(task7_GenericSql_elem, 'OutputFilesList','OutputFile')
        tables_list = getListValueAttributeDom(task7_GenericSql_elem, 'OutputFilesList', 'OutputFile', 'table')
        for index in range (len(output_files_list)) :
            output_file = output_files_list[index]
            table_name = tables_list[index]
            output_file_struct = StructSQL_outputFile()
            output_file_struct.outputFile = output_file
            output_file_struct.tableName = table_name
            settings_struct.tasks.task7_GenericSql[pos].outputFilesList.append(output_file_struct)

    # Task8_ParametricStudySamples
    settings_struct.tasks.task8_ParametricStudySamples = StructTask8_ParametricStudySamples()
    settings_struct.tasks.task8_ParametricStudySamples.inputVector = getValueNodeDataDom(xmldoc, 'InputVector', 'Task8_ParametricStudySamples')
    settings_struct.tasks.task8_ParametricStudySamples.outputFile = getValueNodeDataDom(xmldoc, 'OutputFile', 'Task8_ParametricStudySamples')
    settings_struct.tasks.task8_ParametricStudySamples.outputMatrix = getValueNodeDataDom(xmldoc, 'OutputMatrix', 'Task8_ParametricStudySamples')
    settings_struct.tasks.task8_ParametricStudySamples.ratesList = getListNodeDataDom(xmldoc, 'RatesList', 'Rate', 'Task8_ParametricStudySamples')

    # Task9_ParametricStudyTexturesIndices
    settings_struct.tasks.task9_parametricStudyTexturesIndices = StructTask9_ParametricStudyTexturesIndices()
    settings_struct.tasks.task9_parametricStudyTexturesIndices.inputVector = getValueNodeDataDom(xmldoc, 'InputVector', 'Task9_ParametricStudyTexturesIndices')
    settings_struct.tasks.task9_parametricStudyTexturesIndices.inputSample = getValueNodeDataDom(xmldoc, 'InputSample', 'Task9_ParametricStudyTexturesIndices')
    settings_struct.tasks.task9_parametricStudyTexturesIndices.outputFile = getValueNodeDataDom(xmldoc, 'OutputFile', 'Task9_ParametricStudyTexturesIndices')
    settings_struct.tasks.task9_parametricStudyTexturesIndices.outputMatrix = getValueNodeDataDom(xmldoc, 'OutputMatrix', 'Task9_ParametricStudyTexturesIndices')
    settings_struct.tasks.task9_parametricStudyTexturesIndices.channelsList = getListNodeDataDom(xmldoc, 'ChannelsList', 'Channel', 'Task9_ParametricStudyTexturesIndices')
    settings_struct.tasks.task9_parametricStudyTexturesIndices.texturesList = getListNodeDataDom(xmldoc, 'TexturesList', 'Texture', 'Task9_ParametricStudyTexturesIndices')
    settings_struct.tasks.task9_parametricStudyTexturesIndices.radiusList = getListNodeDataDom(xmldoc, 'RadiusList', 'Radius', 'Task9_ParametricStudyTexturesIndices')
    settings_struct.tasks.task9_parametricStudyTexturesIndices.indicesList = getListNodeDataDom(xmldoc, 'IndicesList', 'Indice', 'Task9_ParametricStudyTexturesIndices')

    # Task10_ImagesAssembly
    task10_ImagesAssembly_elem_list = findAllElement(xmldoc, 'Task10_ImagesAssembly','Tasks/Task10_ImagesAssembly_List')
    for pos in range (len(task10_ImagesAssembly_elem_list)):
        task10_ImagesAssembly_elem = task10_ImagesAssembly_elem_list[pos]
        settings_struct.tasks.task10_ImagesAssembly.append(StructTask10_ImagesAssembly())
        settings_struct.tasks.task10_ImagesAssembly[pos].empriseFile = getValueNodeDataDom(task10_ImagesAssembly_elem, 'EmpriseFile')
        settings_struct.tasks.task10_ImagesAssembly[pos].sourceImagesDirList = getListNodeDataDom(task10_ImagesAssembly_elem, 'SourceImagesDirList','ImagesDir')
        settings_struct.tasks.task10_ImagesAssembly[pos].outputFile = getValueNodeDataDom(task10_ImagesAssembly_elem, 'OutputFile')
        settings_struct.tasks.task10_ImagesAssembly[pos].changeZero2OtherValueBefore = getValueNodeDataDom(task10_ImagesAssembly_elem, 'ChangeZero2OtherValueBefore').lower() == 'true'
        settings_struct.tasks.task10_ImagesAssembly[pos].changeZero2OtherValueAfter = getValueNodeDataDom(task10_ImagesAssembly_elem, 'ChangeZero2OtherValueAfter').lower() == 'true'
        value = getValueNodeDataDom(task10_ImagesAssembly_elem, 'ChangeOtherValue')
        if value != "" and value is not None:
            settings_struct.tasks.task10_ImagesAssembly[pos].changeOtherValue = float(value)
        settings_struct.tasks.task10_ImagesAssembly[pos].dateSplitter = getValueNodeDataDom(task10_ImagesAssembly_elem, 'DateSplitter')
        value = getValueNodeDataDom(task10_ImagesAssembly_elem, 'DatePosition')
        if value != "" and value is not None:
            settings_struct.tasks.task10_ImagesAssembly[pos].datePosition = int(value)
        value = getValueNodeDataDom(task10_ImagesAssembly_elem, 'DateNumberOfCharacters')
        if value != "" and value is not None:
            settings_struct.tasks.task10_ImagesAssembly[pos].dateNumberOfCharacters = int(value)
        settings_struct.tasks.task10_ImagesAssembly[pos].intraDateSplitter = getValueNodeDataDom(task10_ImagesAssembly_elem, 'IntraDateSplitter')

    # Task12_PansharpeningAssembly
    task12_PansharpeningAssembly_elem_list = findAllElement(xmldoc, 'Task12_PansharpeningAssembly','Tasks/Task12_PansharpeningAssembly_List')
    for pos in range (len(task12_PansharpeningAssembly_elem_list)):
        task12_PansharpeningAssembly_elem = task12_PansharpeningAssembly_elem_list[pos]
        settings_struct.tasks.task12_PansharpeningAssembly.append(StructTask12_PansharpeningAssembly())
        settings_struct.tasks.task12_PansharpeningAssembly[pos].inputPanchroFile = getValueNodeDataDom(task12_PansharpeningAssembly_elem, 'InputPanchroFile')
        settings_struct.tasks.task12_PansharpeningAssembly[pos].inputXsFile = getValueNodeDataDom(task12_PansharpeningAssembly_elem, 'InputXsFile')
        settings_struct.tasks.task12_PansharpeningAssembly[pos].outputFile = getValueNodeDataDom(task12_PansharpeningAssembly_elem, 'OutputFile')
        settings_struct.tasks.task12_PansharpeningAssembly[pos].interpolationMode = getValueNodeDataDom(task12_PansharpeningAssembly_elem, 'InterpolationMode')
        settings_struct.tasks.task12_PansharpeningAssembly[pos].interpolationMethod = getValueNodeDataDom(task12_PansharpeningAssembly_elem, 'InterpolationMethod')
        settings_struct.tasks.task12_PansharpeningAssembly[pos].pansharpeningMethod = getValueNodeDataDom(task12_PansharpeningAssembly_elem, 'PansharpeningMethod')
        value = getValueNodeDataDom(task12_PansharpeningAssembly_elem, 'Radius', 'InterpolationBco')
        if value != "" and value is not None:
            settings_struct.tasks.task12_PansharpeningAssembly[pos].interpolationBco_radius = int(value)
        value = getValueNodeDataDom(task12_PansharpeningAssembly_elem, 'Xradius', 'PansharpeningLmvm')
        if value != "" and value is not None:
            settings_struct.tasks.task12_PansharpeningAssembly[pos].pansharpeningLmvm_xradius = int(value)
        value = getValueNodeDataDom(task12_PansharpeningAssembly_elem, 'Yradius', 'PansharpeningLmvm')
        if value != "" and value is not None:
           settings_struct.tasks.task12_PansharpeningAssembly[pos].pansharpeningLmvm_yradius = int(value)
        value = getValueNodeDataDom(task12_PansharpeningAssembly_elem, 'Lambda', 'PansharpeningBayes')
        if value != "" and value is not None:
            settings_struct.tasks.task12_PansharpeningAssembly[pos].pansharpeningBayes_lambda = float(value)
        value = getValueNodeDataDom(task12_PansharpeningAssembly_elem, 'Scoef', 'PansharpeningBayes')
        if value != "" and value is not None:
            settings_struct.tasks.task12_PansharpeningAssembly[pos].pansharpeningBayes_scoef = float(value)

    # Task20_ImageCompression
    task20_ImageCompression_elem_list = findAllElement(xmldoc, 'Task20_ImageCompression','Tasks/Task20_ImageCompression_List')
    for pos in range (len(task20_ImageCompression_elem_list)):
        task20_ImageCompression_elem = task20_ImageCompression_elem_list[pos]
        settings_struct.tasks.task20_ImageCompression.append(StructTask20_ImageCompression())
        settings_struct.tasks.task20_ImageCompression[pos].inputFile = getValueNodeDataDom(task20_ImageCompression_elem, 'InputFile')
        settings_struct.tasks.task20_ImageCompression[pos].outputFile8b = getValueNodeDataDom(task20_ImageCompression_elem, 'OutputFile8b')
        settings_struct.tasks.task20_ImageCompression[pos].outputFile8bCompress = getValueNodeDataDom(task20_ImageCompression_elem, 'OutputFile8bCompress')
        settings_struct.tasks.task20_ImageCompression[pos].optimize8bits = getValueNodeDataDom(task20_ImageCompression_elem, 'Optimize8bits').lower() == 'true'

    # Task30_NeoChannelsComputation
    task30_NeoChannelsComputation_elem_list = findAllElement(xmldoc, 'Task30_NeoChannelsComputation','Tasks/Task30_NeoChannelsComputation_List')
    for pos in range (len(task30_NeoChannelsComputation_elem_list)):
        task30_NeoChannelsComputation_elem = task30_NeoChannelsComputation_elem_list[pos]
        settings_struct.tasks.task30_NeoChannelsComputation.append(StructTask30_NeoChannelsComputation())
        settings_struct.tasks.task30_NeoChannelsComputation[pos].inputFilesList = getListNodeDataDom(task30_NeoChannelsComputation_elem, 'InputFilesList', 'InputFile')
        settings_struct.tasks.task30_NeoChannelsComputation[pos].outputPath = getValueNodeDataDom(task30_NeoChannelsComputation_elem, 'OutputPath')
        settings_struct.tasks.task30_NeoChannelsComputation[pos].channelsList = getListNodeDataDom(task30_NeoChannelsComputation_elem, 'ChannelsList', 'Channel')
        settings_struct.tasks.task30_NeoChannelsComputation[pos].textureFamilyList = getListNodeDataDom(task30_NeoChannelsComputation_elem, 'TextureFamilyList', 'TextureFamily')
        settings_struct.tasks.task30_NeoChannelsComputation[pos].radiusList = getListNodeDataDom(task30_NeoChannelsComputation_elem, 'RadiusList', 'Radius')
        settings_struct.tasks.task30_NeoChannelsComputation[pos].indicesList = getListNodeDataDom(task30_NeoChannelsComputation_elem, 'IndicesList', 'Indice')
        value = getValueNodeDataDom(task30_NeoChannelsComputation_elem, 'BinNumber')
        if value != "" and value is not None:
            settings_struct.tasks.task30_NeoChannelsComputation[pos].binNumber = int(value)

    # Task35_MnhCreation
    task35_MnhCreation_elem_list = findAllElement(xmldoc, 'Task35_MnhCreation','Tasks/Task35_MnhCreation_List')
    for pos in range (len(task35_MnhCreation_elem_list)):
        task35_MnhCreation_elem = task35_MnhCreation_elem_list[pos]
        settings_struct.tasks.task35_MnhCreation.append(StructTask35_MnhCreation())
        settings_struct.tasks.task35_MnhCreation[pos].inputVector = getValueNodeDataDom(task35_MnhCreation_elem, 'InputVector')
        settings_struct.tasks.task35_MnhCreation[pos].inputMnsFile = getValueNodeDataDom(task35_MnhCreation_elem, 'InputMnsFile')
        settings_struct.tasks.task35_MnhCreation[pos].inputMntFile = getValueNodeDataDom(task35_MnhCreation_elem, 'InputMntFile')
        settings_struct.tasks.task35_MnhCreation[pos].inputFilterFile = getValueNodeDataDom(task35_MnhCreation_elem, 'InputFilterFile')
        settings_struct.tasks.task35_MnhCreation[pos].outputMnhFile = getValueNodeDataDom(task35_MnhCreation_elem, 'OutputMnhFile')
        database_files_list = getListNodeDataDom(task35_MnhCreation_elem, 'DataBaseRoadFilesList', 'DataBaseFile')
        buffers_list = getListValueAttributeDom(task35_MnhCreation_elem, 'DataBaseRoadFilesList', 'DataBaseFile', 'buffer')
        sql_expressions_list = getListValueAttributeDom(task35_MnhCreation_elem, 'DataBaseRoadFilesList', 'DataBaseFile', 'sql')
        for index in range (len(database_files_list)) :
            database_file = database_files_list[index]
            sql_expression = sql_expressions_list[index]
            if buffers_list[index] != "" and buffers_list[index] is not None:
                buffer_value = float(buffers_list[index])
            else:
                buffer_value = 0
            database_file_struct = StructCreation_DatabaseFile()
            database_file_struct.inputVector = database_file
            database_file_struct.bufferValue = buffer_value
            database_file_struct.sqlExpression = sql_expression
            settings_struct.tasks.task35_MnhCreation[pos].dataBaseRoadFileList.append(database_file_struct)
        settings_struct.tasks.task35_MnhCreation[pos].dataBaseBuildFilesList = getListNodeDataDom(task35_MnhCreation_elem, 'DataBaseBuildFilesList', 'DataBaseFile')
        value = getValueNodeDataDom(task35_MnhCreation_elem, 'Bias')
        if value != "" and value is not None:
            settings_struct.tasks.task35_MnhCreation[pos].bias = float(value)
        value = getValueNodeDataDom(task35_MnhCreation_elem, 'ThresholdFilterFile')
        if value != "" and value is not None:
            settings_struct.tasks.task35_MnhCreation[pos].thresholdFilterFile = float(value)
        value = getValueNodeDataDom(task35_MnhCreation_elem, 'ThresholdDeltaH')
        if value != "" and value is not None:
            settings_struct.tasks.task35_MnhCreation[pos].thresholdDeltaH = float(value)
        settings_struct.tasks.task35_MnhCreation[pos].interpolationMode = getValueNodeDataDom(task35_MnhCreation_elem, 'InterpolationMode')
        settings_struct.tasks.task35_MnhCreation[pos].interpolationMethod = getValueNodeDataDom(task35_MnhCreation_elem, 'InterpolationMethod')
        value = getValueNodeDataDom(task35_MnhCreation_elem, 'Radius', 'InterpolationBco')
        if value != "" and value is not None:
            settings_struct.tasks.task35_MnhCreation[pos].interpolationBco_radius = int(value)
        value = getValueNodeDataDom(task35_MnhCreation_elem, 'SimplificationPolygon')
        if value != "" and value is not None:
            settings_struct.tasks.task35_MnhCreation[pos].simplificationPolygon = float(value)

    # Task40_ChannelsConcatenantion
    task40_ChannelsConcatenantion_elem_list = findAllElement(xmldoc, 'Task40_ChannelsConcatenantion','Tasks/Task40_ChannelsConcatenantion_List')
    for pos in range (len(task40_ChannelsConcatenantion_elem_list)):
        task40_ChannelsConcatenantion_elem = task40_ChannelsConcatenantion_elem_list[pos]
        settings_struct.tasks.task40_ChannelsConcatenantion.append(StructTask40_ChannelsConcatenantion())
        settings_struct.tasks.task40_ChannelsConcatenantion[pos].inputFilesList = getListNodeDataDom(task40_ChannelsConcatenantion_elem, 'InputFilesList', 'InputFile')
        settings_struct.tasks.task40_ChannelsConcatenantion[pos].concatenation.stackConcatenation = getValueNodeDataDom(task40_ChannelsConcatenantion_elem, 'StackConcatenation').lower() == 'true'
        settings_struct.tasks.task40_ChannelsConcatenantion[pos].concatenation.outputFile = getValueNodeDataDom(task40_ChannelsConcatenantion_elem, 'OutputFile', 'Concatenation')
        settings_struct.tasks.task40_ChannelsConcatenantion[pos].normalization.stackNormalization = getValueNodeDataDom(task40_ChannelsConcatenantion_elem, 'StackNormalization').lower() == 'true'
        settings_struct.tasks.task40_ChannelsConcatenantion[pos].normalization.outputFile = getValueNodeDataDom(task40_ChannelsConcatenantion_elem, 'OutputFile', 'Normalization')
        settings_struct.tasks.task40_ChannelsConcatenantion[pos].reduction.stackReduction = getValueNodeDataDom(task40_ChannelsConcatenantion_elem, 'StackReduction').lower() == 'true'
        settings_struct.tasks.task40_ChannelsConcatenantion[pos].reduction.outputFile = getValueNodeDataDom(task40_ChannelsConcatenantion_elem, 'OutputFile', 'Reduction')
        settings_struct.tasks.task40_ChannelsConcatenantion[pos].reduction.method  = getValueNodeDataDom(task40_ChannelsConcatenantion_elem, 'Method')
        value = getValueNodeDataDom(task40_ChannelsConcatenantion_elem, 'MaxBandNumber')
        if value != "" and value is not None:
            settings_struct.tasks.task40_ChannelsConcatenantion[pos].reduction.maxBandNumber = int(value)
        settings_struct.tasks.task40_ChannelsConcatenantion[pos].reduction.normalizationReduce = getValueNodeDataDom(task40_ChannelsConcatenantion_elem, 'NormalizationReduce').lower() == 'true'
        value = getValueNodeDataDom(task40_ChannelsConcatenantion_elem, 'NapcaRadius')
        if value != "" and value is not None:
            settings_struct.tasks.task40_ChannelsConcatenantion[pos].reduction.napcaRadius = int(value)
        value = getValueNodeDataDom(task40_ChannelsConcatenantion_elem, 'IcaIterations')
        if value != "" and value is not None:
            settings_struct.tasks.task40_ChannelsConcatenantion[pos].reduction.icaIterations = int(value)
        value = getValueNodeDataDom(task40_ChannelsConcatenantion_elem, 'IcaIncrement')
        if value != "" and value is not None:
            settings_struct.tasks.task40_ChannelsConcatenantion[pos].reduction.icaIncrement = float(value)

    # Task50_MacroSampleCreation
    task50_MacroSampleCreation_elem_list = findAllElement(xmldoc, 'Task50_MacroSampleCreation','Tasks/Task50_MacroSampleCreation_List')
    for pos in range (len(task50_MacroSampleCreation_elem_list)):
        task50_MacroSampleCreation_elem = task50_MacroSampleCreation_elem_list[pos]
        settings_struct.tasks.task50_MacroSampleCreation.append(StructTask50_MacroSampleCreation())
        settings_struct.tasks.task50_MacroSampleCreation[pos].inputFile = getValueNodeDataDom(task50_MacroSampleCreation_elem, 'InputFile')
        settings_struct.tasks.task50_MacroSampleCreation[pos].inputVector = getValueNodeDataDom(task50_MacroSampleCreation_elem, 'InputVector')
        value = getValueNodeDataDom(task50_MacroSampleCreation_elem, 'SimplificationPolygon')
        if value != "" and value is not None:
            settings_struct.tasks.task50_MacroSampleCreation[pos].simplificationPolygon = float(value)
        elements_list = findAllElement(task50_MacroSampleCreation_elem, 'ClassMacroSample', 'ClassMacroSampleList')
        settings_struct.tasks.task50_MacroSampleCreation[pos].classMacroSampleList = []
        for element in elements_list:
            database_files_list = getListNodeDataDom(element, 'DataBaseFilesList', 'DataBaseFile')
            buffers_list = getListValueAttributeDom(element, 'DataBaseFilesList', 'DataBaseFile', 'buffer')
            sql_expressions_list = getListValueAttributeDom(element, 'DataBaseFilesList', 'DataBaseFile', 'sql')
            output_vector = getValueNodeDataDom(element, 'OutputVector')
            output_file = getValueNodeDataDom(element, 'OutputFile')
            macro_name = getValueAttributeDom(element, 'name')
            class_macro_sample_struct = StructMacroSampleCreation_ClassMacro()
            class_macro_sample_struct.dataBaseFileList = []
            class_macro_sample_struct.outputVector = output_vector
            class_macro_sample_struct.outputFile = output_file
            class_macro_sample_struct.name = macro_name
            for index in range (len(database_files_list)) :
                database_file = database_files_list[index]
                sql_expression = sql_expressions_list[index]
                if buffers_list[index] != "" and buffers_list[index] is not None:
                    buffer_value = float(buffers_list[index])
                else:
                    buffer_value = 0
                database_file_struct = StructCreation_DatabaseFile()
                database_file_struct.inputVector = database_file
                database_file_struct.bufferValue = buffer_value
                database_file_struct.sqlExpression = sql_expression
                class_macro_sample_struct.dataBaseFileList.append(database_file_struct)
            settings_struct.tasks.task50_MacroSampleCreation[pos].classMacroSampleList.append(class_macro_sample_struct)

    # Task60_MaskCreation
    task60_MaskCreation_elem_list = findAllElement(xmldoc, 'Task60_MaskCreation','Tasks/Task60_MaskCreation_List')
    for pos in range (len(task60_MaskCreation_elem_list)):
        task60_MaskCreation_elem = task60_MaskCreation_elem_list[pos]
        settings_struct.tasks.task60_MaskCreation.append(StructTask60_MaskCreation())
        settings_struct.tasks.task60_MaskCreation[pos].inputFile = getValueNodeDataDom(task60_MaskCreation_elem, 'InputFile')
        elements_list = findAllElement(task60_MaskCreation_elem, 'ClassMacroSample', 'ClassMacroSampleList')
        settings_struct.tasks.task60_MaskCreation[pos].classMacroSampleList = []
        for element in elements_list:
            class_macro_sample_struct = StructMaskCreation_ClassMacro()
            class_macro_sample_struct.inputVector = getValueNodeDataDom(element, 'InputVector')
            class_macro_sample_struct.outputFile = getValueNodeDataDom(element, 'OutputFile')
            settings_struct.tasks.task60_MaskCreation[pos].classMacroSampleList.append(class_macro_sample_struct)

    # Task70_RA_MacroSampleCutting
    task70_RA_MacroSampleCutting_elem_list = findAllElement(xmldoc, 'Task70_RA_MacroSampleCutting','Tasks/Task70_RA_MacroSampleCutting_List')
    for pos in range (len(task70_RA_MacroSampleCutting_elem_list)):
        task70_RA_MacroSampleCutting_elem = task70_RA_MacroSampleCutting_elem_list[pos]
        settings_struct.tasks.task70_RA_MacroSampleCutting.append(StructTask70_RA_MacroSampleCutting())
        settings_struct.tasks.task70_RA_MacroSampleCutting[pos].inputVector = getValueNodeDataDom(task70_RA_MacroSampleCutting_elem, 'InputVector')
        settings_struct.tasks.task70_RA_MacroSampleCutting[pos].superposition = getValueNodeDataDom(task70_RA_MacroSampleCutting_elem, 'Superposition').lower() == 'true'
        settings_struct.tasks.task70_RA_MacroSampleCutting[pos].referenceImage = getValueNodeDataDom(task70_RA_MacroSampleCutting_elem, 'ReferenceImage')
        elements_list = findAllElement(task70_RA_MacroSampleCutting_elem, 'ClassMacroSample', 'ClassMacroSampleList')
        settings_struct.tasks.task70_RA_MacroSampleCutting[pos].classMacroSampleList = []
        for element in elements_list:
            class_macro_sample_struct = StructMacroSampleCutting_ClassMacro()
            class_macro_sample_struct.inputFile = getValueNodeDataDom(element, 'InputFile')
            class_macro_sample_struct.outputFile = getValueNodeDataDom(element, 'OutputFile')
            settings_struct.tasks.task70_RA_MacroSampleCutting[pos].classMacroSampleList.append(class_macro_sample_struct)

    # Task80_MacroSampleAmelioration
    task80_MacroSampleAmelioration_elem_list = findAllElement(xmldoc, 'Task80_MacroSampleAmelioration','Tasks/Task80_MacroSampleAmelioration_List')
    for pos in range (len(task80_MacroSampleAmelioration_elem_list)):
        task80_MacroSampleAmelioration_elem = task80_MacroSampleAmelioration_elem_list[pos]
        settings_struct.tasks.task80_MacroSampleAmelioration.append(StructTask80_MacroSampleAmelioration())
        elements_list = findAllElement(task80_MacroSampleAmelioration_elem, 'ClassMacroSample', 'ClassMacroSampleList')
        settings_struct.tasks.task80_MacroSampleAmelioration[pos].classMacroSampleList = []
        for element in elements_list:
            correction_files_list = getListNodeDataDom(element, 'CorrectionFilesList', 'CorrectionFile')
            names_list = getListValueAttributeDom(element, 'CorrectionFilesList', 'CorrectionFile', 'name')
            thresholds_min_list = getListValueAttributeDom(element, 'CorrectionFilesList', 'CorrectionFile', 'threshold_min')
            thresholds_max_list = getListValueAttributeDom(element, 'CorrectionFilesList', 'CorrectionFile', 'threshold_max')
            filters_size_for_zero_list = getListValueAttributeDom(element, 'CorrectionFilesList', 'CorrectionFile', 'filter_size_for_zero')
            filters_size_for_one_list = getListValueAttributeDom(element, 'CorrectionFilesList', 'CorrectionFile', 'filter_size_for_one')
            operators_fusion_list = getListValueAttributeDom(element, 'CorrectionFilesList', 'CorrectionFile', 'operator_fusion')
            input_file = getValueNodeDataDom(element, 'InputFile')
            output_file = getValueNodeDataDom(element, 'OutputFile')
            macro_name = getValueAttributeDom(element, 'name')
            class_macro_sample_struct = StructMacroSampleAmelioration()
            class_macro_sample_struct.correctionFilesList = []
            class_macro_sample_struct.inputFile = input_file
            class_macro_sample_struct.outputFile = output_file
            class_macro_sample_struct.name = macro_name
            for index in range (len(correction_files_list)) :
                correction_file_struct = StructMacroSampleAmelioration_CorrectionFile()
                correction_file_struct.name = names_list[index]
                correction_file_struct.correctionFile = correction_files_list[index]
                if thresholds_min_list[index] != "" and thresholds_min_list[index] is not None:
                    correction_file_struct.thresholdMin = float(thresholds_min_list[index])
                else:
                    correction_file_struct.thresholdMin = 0.0
                if thresholds_max_list[index] != "" and thresholds_max_list[index] is not None:
                    correction_file_struct.thresholdMax = float(thresholds_max_list[index])
                else:
                    correction_file_struct.thresholdMax = 0.0
                if filters_size_for_zero_list[index] != "" and filters_size_for_zero_list[index] is not None:
                    correction_file_struct.filterSizeForZero = int(filters_size_for_zero_list[index])
                else:
                    correction_file_struct.filterSizeForZero = 0
                if filters_size_for_one_list[index] != "" and filters_size_for_one_list[index] is not None:
                    correction_file_struct.filterSizeForOne = int(filters_size_for_one_list[index])
                else:
                    correction_file_struct.filterSizeForOne = 0
                correction_file_struct.operatorFusion = operators_fusion_list[index]
                class_macro_sample_struct.correctionFilesList.append(correction_file_struct)
            settings_struct.tasks.task80_MacroSampleAmelioration[pos].classMacroSampleList.append(class_macro_sample_struct)

    # Task90_KmeansMaskApplication
    task90_KmeansMaskApplication_elem_list = findAllElement(xmldoc, 'Task90_KmeansMaskApplication','Tasks/Task90_KmeansMaskApplication_List')
    for pos in range (len(task90_KmeansMaskApplication_elem_list)):
        task90_KmeansMaskApplication_elem = task90_KmeansMaskApplication_elem_list[pos]
        settings_struct.tasks.task90_KmeansMaskApplication.append(StructTask90_KmeansMaskApplication())
        settings_struct.tasks.task90_KmeansMaskApplication[pos].inputFile = getValueNodeDataDom(task90_KmeansMaskApplication_elem, 'InputFile')
        settings_struct.tasks.task90_KmeansMaskApplication[pos].outputFile = getValueNodeDataDom(task90_KmeansMaskApplication_elem, 'OutputFile')
        settings_struct.tasks.task90_KmeansMaskApplication[pos].proposalTable = getValueNodeDataDom(task90_KmeansMaskApplication_elem, 'ProposalTable')
        value = getValueNodeDataDom(task90_KmeansMaskApplication_elem, 'Iterations')
        if value != "" and value is not None:
            settings_struct.tasks.task90_KmeansMaskApplication[pos].iterations = int(value)
        value = getValueNodeDataDom(task90_KmeansMaskApplication_elem, 'PropPixels')
        if value != "" and value is not None:
            settings_struct.tasks.task90_KmeansMaskApplication[pos].propPixels = int(value)
        value = getValueNodeDataDom(task90_KmeansMaskApplication_elem, 'SizeTraining')
        if value != "" and value is not None:
            settings_struct.tasks.task90_KmeansMaskApplication[pos].sizeTraining = int(value)
        value = getValueNodeDataDom(task90_KmeansMaskApplication_elem, 'MinNumberTrainingSize')
        if value != "" and value is not None:
            settings_struct.tasks.task90_KmeansMaskApplication[pos].minNumberTrainingSize = int(value)
        value = getValueNodeDataDom(task90_KmeansMaskApplication_elem, 'RateCleanMicroclass')
        if value != "" and value is not None:
            settings_struct.tasks.task90_KmeansMaskApplication[pos].rateCleanMicroclass = float(value)
        value = getValueNodeDataDom(task90_KmeansMaskApplication_elem, 'Rand')
        if value != "" and value is not None:
            settings_struct.tasks.task90_KmeansMaskApplication[pos].rand = int(value)
        labels_list = getListValueAttributeDom(task90_KmeansMaskApplication_elem, 'ClassMacroSampleList', 'ClassMacroSample', 'label')
        elements_list = findAllElement(task90_KmeansMaskApplication_elem, 'ClassMacroSample', 'ClassMacroSampleList')
        settings_struct.tasks.task90_KmeansMaskApplication[pos].classMacroSampleList = []
        for index in range (len(elements_list)) :
            element = elements_list[index]
            class_macro_sample_struct = StructKmeansMaskApplication_ClassMacro()
            class_macro_sample_struct.inputFile = getValueNodeDataDom(element, 'InputFile')
            class_macro_sample_struct.outputFile = getValueNodeDataDom(element, 'OutputFile')
            class_macro_sample_struct.outputCentroidFile = getValueNodeDataDom(element, 'OutputCentroidFile')
            value = getValueNodeDataDom(element, 'Sampling')
            if value != "" and value is not None:
                class_macro_sample_struct.sampling = int(value)
            else:
                class_macro_sample_struct.sampling = 0
            if labels_list[index] != "" and labels_list[index] is not None:
                class_macro_sample_struct.label = int(labels_list[index])
            else:
                class_macro_sample_struct.label = 0
            settings_struct.tasks.task90_KmeansMaskApplication[pos].classMacroSampleList.append(class_macro_sample_struct)

    # Task100_MicroSamplePolygonization
    task100_MicroSamplePolygonization_elem_list = findAllElement(xmldoc, 'Task100_MicroSamplePolygonization','Tasks/Task100_MicroSamplePolygonization_List')
    for pos in range (len(task100_MicroSamplePolygonization_elem_list)):
        task100_MicroSamplePolygonization_elem = task100_MicroSamplePolygonization_elem_list[pos]
        settings_struct.tasks.task100_MicroSamplePolygonization.append(StructTask100_MicroSamplePolygonization())
        value = getValueNodeDataDom(task100_MicroSamplePolygonization_elem, 'UMC')
        if value != "" and value is not None:
            settings_struct.tasks.task100_MicroSamplePolygonization[pos].umc = int(value)
        value = getValueNodeDataDom(task100_MicroSamplePolygonization_elem, 'TileSize')
        if value != "" and value is not None:
            settings_struct.tasks.task100_MicroSamplePolygonization[pos].tileSize = int(value)
        settings_struct.tasks.task100_MicroSamplePolygonization[pos].outputFile = getValueNodeDataDom(task100_MicroSamplePolygonization_elem, 'OutputFile')
        settings_struct.tasks.task100_MicroSamplePolygonization[pos].proposalTable = getValueNodeDataDom(task100_MicroSamplePolygonization_elem, 'ProposalTable')
        value = getValueNodeDataDom(task100_MicroSamplePolygonization_elem, 'RateCleanMicroclass')
        if value != "" and value is not None:
            settings_struct.tasks.task100_MicroSamplePolygonization[pos].rateCleanMicroclass = float(value)
        settings_struct.tasks.task100_MicroSamplePolygonization[pos].inputFileList = []
        input_files_list = getListNodeDataDom(task100_MicroSamplePolygonization_elem, 'InputFilesList', 'InputFile')
        raster_erode_list = getListValueAttributeDom(task100_MicroSamplePolygonization_elem, 'InputFilesList', 'InputFile', 'raster_erode')
        buffer_size_list = getListValueAttributeDom(task100_MicroSamplePolygonization_elem, 'InputFilesList', 'InputFile', 'buffer_size')
        buffer_approximate_list = getListValueAttributeDom(task100_MicroSamplePolygonization_elem, 'InputFilesList', 'InputFile', 'buffer_approximate')
        minimal_area_list = getListValueAttributeDom(task100_MicroSamplePolygonization_elem, 'InputFilesList', 'InputFile', 'minimal_area')
        simplification_tolerance_list = getListValueAttributeDom(task100_MicroSamplePolygonization_elem, 'InputFilesList', 'InputFile', 'simplification_tolerance')
        for index in range (len(input_files_list)) :
            input_file_struct = StructMicroSamplePolygonization_InputFile()
            input_file_struct.inputFile = input_files_list[index]
            if raster_erode_list[index] != "" and raster_erode_list[index] is not None:
                input_file_struct.rasterErode = int(raster_erode_list[index])
            else:
                input_file_struct.bufferApproximate = 0
            if buffer_size_list[index] != "" and buffer_size_list[index] is not None:
                input_file_struct.bufferSize = float(buffer_size_list[index])
            else:
                input_file_struct.bufferSize = 0.0
            if buffer_approximate_list[index] != "" and buffer_approximate_list[index] is not None:
                input_file_struct.bufferApproximate = int(buffer_approximate_list[index])
            else:
                input_file_struct.bufferApproximate = 0
            if minimal_area_list[index] != "" and minimal_area_list[index] is not None:
                input_file_struct.minimalArea = float(minimal_area_list[index])
            else:
                input_file_struct.minimalArea = 0.0
            if simplification_tolerance_list[index] != "" and simplification_tolerance_list[index] is not None:
                input_file_struct.simplificationTolerance = float(simplification_tolerance_list[index])
            else:
                input_file_struct.simplificationTolerance = 0.0
            settings_struct.tasks.task100_MicroSamplePolygonization[pos].inputFileList.append(input_file_struct)

    # Task110_ClassReallocationVector
    task110_ClassReallocationVector_elem_list = findAllElement(xmldoc, 'Task110_ClassReallocationVector','Tasks/Task110_ClassReallocationVector_List')
    for pos in range (len(task110_ClassReallocationVector_elem_list)):
        task110_ClassReallocationVector_elem = task110_ClassReallocationVector_elem_list[pos]
        settings_struct.tasks.task110_ClassReallocationVector.append(StructTask110_ClassReallocationVector())
        settings_struct.tasks.task110_ClassReallocationVector[pos].inputFile = getValueNodeDataDom(task110_ClassReallocationVector_elem, 'InputFile')
        settings_struct.tasks.task110_ClassReallocationVector[pos].outputFile = getValueNodeDataDom(task110_ClassReallocationVector_elem, 'OutputFile')
        settings_struct.tasks.task110_ClassReallocationVector[pos].proposalTable = getValueNodeDataDom(task110_ClassReallocationVector_elem, 'ProposalTable')

   # Task115_SampleSelectionRaster
    task115_ClassSampleSelectionRaster_elem_list = findAllElement(xmldoc, 'Task115_SampleSelectionRaster','Tasks/Task115_SampleSelectionRaster_List')
    for pos in range (len(task115_ClassSampleSelectionRaster_elem_list)):
        task115_ClassSampleSelectionRaster_elem = task115_ClassSampleSelectionRaster_elem_list[pos]
        settings_struct.tasks.task115_SampleSelectionRaster.append(StructTask115_SampleSelectionRaster())
        settings_struct.tasks.task115_SampleSelectionRaster[pos].inputFilesList = getListNodeDataDom(task115_ClassSampleSelectionRaster_elem, 'InputFilesList', 'InputFile')
        settings_struct.tasks.task115_SampleSelectionRaster[pos].inputSample = getValueNodeDataDom(task115_ClassSampleSelectionRaster_elem, 'InputSample')
        settings_struct.tasks.task115_SampleSelectionRaster[pos].outputVector = getValueNodeDataDom(task115_ClassSampleSelectionRaster_elem, 'OutputVector')
        settings_struct.tasks.task115_SampleSelectionRaster[pos].outputStatisticsTable = getValueNodeDataDom(task115_ClassSampleSelectionRaster_elem, 'OutputStatisticsTable')
        settings_struct.tasks.task115_SampleSelectionRaster[pos].samplerStrategy = getValueNodeDataDom(task115_ClassSampleSelectionRaster_elem, 'SamplerStrategy')
        value = getValueNodeDataDom(task115_ClassSampleSelectionRaster_elem, 'SelectRatioFloor')
        if value != "" and value is not None:
            settings_struct.tasks.task115_SampleSelectionRaster[pos].selectRatioFloor = float(value)
        else:
            settings_struct.tasks.task115_SampleSelectionRaster[pos].selectRatioFloor = 0.0
        labels_list = getListValueAttributeDom(task115_ClassSampleSelectionRaster_elem, 'RatioPerClass_List', 'ClassRatio', 'label')
        class_ratio_list = getListNodeDataDom(task115_ClassSampleSelectionRaster_elem, 'RatioPerClass_List', 'ClassRatio')
        value = getValueNodeDataDom(task115_ClassSampleSelectionRaster_elem, 'Rand')
        if value != "" and value is not None:
            settings_struct.tasks.task115_SampleSelectionRaster[pos].rand = int(value)
        settings_struct.tasks.task115_SampleSelectionRaster[pos].ratioPerClassList = []
        for index in range (len(class_ratio_list)) :
            ratio_class_struct = StructSampleSelectionRaster_RatioPerClass()
            value = class_ratio_list[index]
            if value != "" and value is not None:
                ratio_class_struct.classRatio = float(value)
            else:
                ratio_class_struct.classRatio = 0.0
            value = labels_list[index]
            if value != "" and value is not None:
                ratio_class_struct.label = int(value)
            else:
                ratio_class_struct.label = 0
            settings_struct.tasks.task115_SampleSelectionRaster[pos].ratioPerClassList.append(ratio_class_struct)

    # Task120_SupervisedClassification
    task120_SupervisedClassification_elem_list = findAllElement(xmldoc, 'Task120_SupervisedClassification','Tasks/Task120_SupervisedClassification_List')
    for pos in range (len(task120_SupervisedClassification_elem_list)):
        task120_SupervisedClassification_elem = task120_SupervisedClassification_elem_list[pos]
        settings_struct.tasks.task120_SupervisedClassification.append(StructTask120_SupervisedClassification())
        settings_struct.tasks.task120_SupervisedClassification[pos].inputFilesList = getListNodeDataDom(task120_SupervisedClassification_elem, 'InputFilesList', 'InputFile')
        settings_struct.tasks.task120_SupervisedClassification[pos].inputVector = getValueNodeDataDom(task120_SupervisedClassification_elem, 'InputVector')
        settings_struct.tasks.task120_SupervisedClassification[pos].inputSample = getValueNodeDataDom(task120_SupervisedClassification_elem, 'InputSample')
        settings_struct.tasks.task120_SupervisedClassification[pos].outputFile = getValueNodeDataDom(task120_SupervisedClassification_elem, 'OutputFile')
        settings_struct.tasks.task120_SupervisedClassification[pos].confidenceOutputFile = getValueNodeDataDom(task120_SupervisedClassification_elem, 'ConfidenceOutputFile')
        settings_struct.tasks.task120_SupervisedClassification[pos].outputModelFile = getValueNodeDataDom(task120_SupervisedClassification_elem, 'OutputModelFile')
        settings_struct.tasks.task120_SupervisedClassification[pos].inputModelFile = getValueNodeDataDom(task120_SupervisedClassification_elem, 'InputModelFile')
        settings_struct.tasks.task120_SupervisedClassification[pos].samplerMode = getValueNodeDataDom(task120_SupervisedClassification_elem, 'SamplerMode')

        value = getValueNodeDataDom(task120_SupervisedClassification_elem, 'PeriodicJitter')
        if value != "" and value is not None:
            settings_struct.tasks.task120_SupervisedClassification[pos].periodicJitter = int(value)
        settings_struct.tasks.task120_SupervisedClassification[pos].method = getValueNodeDataDom(task120_SupervisedClassification_elem, 'Method')
        settings_struct.tasks.task120_SupervisedClassification[pos].svn_kernel = getValueNodeDataDom(task120_SupervisedClassification_elem, 'Kernel', 'SVM')
        value = getValueNodeDataDom(task120_SupervisedClassification_elem, 'DephTree', 'RF')
        if value != "" and value is not None:
            settings_struct.tasks.task120_SupervisedClassification[pos].rf_dephTree = int(value)
        value = getValueNodeDataDom(task120_SupervisedClassification_elem, 'NumTree', 'RF')
        if value != "" and value is not None:
            settings_struct.tasks.task120_SupervisedClassification[pos].rf_numTree = int(value)
        value = getValueNodeDataDom(task120_SupervisedClassification_elem, 'SampleMin', 'RF')
        if value != "" and value is not None:
           settings_struct.tasks.task120_SupervisedClassification[pos].rf_sampleMin = int(value)
        value = getValueNodeDataDom(task120_SupervisedClassification_elem, 'TerminCriteria', 'RF')
        if value != "" and value is not None:
            settings_struct.tasks.task120_SupervisedClassification[pos].rf_terminCriteria = float(value)
        value = getValueNodeDataDom(task120_SupervisedClassification_elem, 'Cluster', 'RF')
        if value != "" and value is not None:
            settings_struct.tasks.task120_SupervisedClassification[pos].rf_cluster = int(value)
        value = getValueNodeDataDom(task120_SupervisedClassification_elem, 'SizeFeatures', 'RF')
        if value != "" and value is not None:
            settings_struct.tasks.task120_SupervisedClassification[pos].rf_sizeFeatures = int(value)
        value = getValueNodeDataDom(task120_SupervisedClassification_elem, 'ObbError', 'RF')
        if value != "" and value is not None:
            settings_struct.tasks.task120_SupervisedClassification[pos].rf_obbError = float(value)

    # Task130_PostTraitementsRaster
    task130_PostTraitementsRaster_elem_list = findAllElement(xmldoc, 'Task130_PostTraitementsRaster','Tasks/Task130_PostTraitementsRaster_List')
    for pos in range (len(task130_PostTraitementsRaster_elem_list)):
        task130_PostTraitementsRaster_elem = task130_PostTraitementsRaster_elem_list[pos]
        settings_struct.tasks.task130_PostTraitementsRaster.append(StructTask130_PostTraitementsRaster())
        settings_struct.tasks.task130_PostTraitementsRaster[pos].inputFile = getValueNodeDataDom(task130_PostTraitementsRaster_elem, 'InputFile')
        settings_struct.tasks.task130_PostTraitementsRaster[pos].outputFile = getValueNodeDataDom(task130_PostTraitementsRaster_elem, 'OutputFile')
        settings_struct.tasks.task130_PostTraitementsRaster[pos].inputVector = getValueNodeDataDom(task130_PostTraitementsRaster_elem, 'InputVector')
        settings_struct.tasks.task130_PostTraitementsRaster[pos].inputCorrectionFileList = []
        correction_files_list = getListNodeDataDom(task130_PostTraitementsRaster_elem, 'InputCorrectionFilesList', 'InputFile')
        threshold_min_list = getListValueAttributeDom(task130_PostTraitementsRaster_elem, 'InputCorrectionFilesList', 'InputFile', 'threshold_min')
        threshold_max_list = getListValueAttributeDom(task130_PostTraitementsRaster_elem, 'InputCorrectionFilesList', 'InputFile', 'threshold_max')
        buffer_to_apply_list = getListValueAttributeDom(task130_PostTraitementsRaster_elem, 'InputCorrectionFilesList', 'InputFile', 'buffer_to_apply')
        in_or_out_list = getListValueAttributeDom(task130_PostTraitementsRaster_elem, 'InputCorrectionFilesList', 'InputFile', 'in_or_out')
        class_to_replace_list = getListValueAttributeDom(task130_PostTraitementsRaster_elem, 'InputCorrectionFilesList', 'InputFile', 'class_to_replace')
        replacement_class_list = getListValueAttributeDom(task130_PostTraitementsRaster_elem, 'InputCorrectionFilesList', 'InputFile', 'replacement_class')

        for index in range (len(correction_files_list)) :
            input_file_struct = StructPostTraitementsRaste_InputCorrectionFile()
            input_file_struct.inputFile = correction_files_list[index]
            if threshold_min_list[index] != "" and threshold_min_list[index] is not None:
                input_file_struct.thresholdMin = float(threshold_min_list[index])
            else:
                input_file_struct.thresholdMin = 0.0
            if threshold_max_list[index] != "" and threshold_max_list[index] is not None:
                input_file_struct.thresholdMax = float(threshold_max_list[index])
            else:
                input_file_struct.thresholdMax = 0.0
            if buffer_to_apply_list[index] != "" and buffer_to_apply_list[index] is not None:
                input_file_struct.bufferToApply = int(buffer_to_apply_list[index])
            else:
                input_file_struct.bufferToApply = 0
            input_file_struct.inOrOut = in_or_out_list[index]
            input_file_struct.classToReplace = class_to_replace_list[index]
            if replacement_class_list[index] != "" and replacement_class_list[index] is not None:
                input_file_struct.replacementClass = int(replacement_class_list[index])
            else:
                input_file_struct.replacementClass = 0
            settings_struct.tasks.task130_PostTraitementsRaster[pos].inputCorrectionFileList.append(input_file_struct)

    # Task140_SpecificSubSampling
    task140_SpecificSubSampling_elem_list = findAllElement(xmldoc, 'Task140_SpecificSubSampling','Tasks/Task140_SpecificSubSampling_List')
    for pos in range (len(task140_SpecificSubSampling_elem_list)):
        task140_SpecificSubSampling_elem = task140_SpecificSubSampling_elem_list[pos]
        settings_struct.tasks.task140_SpecificSubSampling.append(StructTask140_SpecificSubSampling())
        settings_struct.tasks.task140_SpecificSubSampling[pos].inputFile = getValueNodeDataDom(task140_SpecificSubSampling_elem, 'InputFile')
        settings_struct.tasks.task140_SpecificSubSampling[pos].inputClassifFile = getValueNodeDataDom(task140_SpecificSubSampling_elem, 'InputClassifFile')
        settings_struct.tasks.task140_SpecificSubSampling[pos].outputFile = getValueNodeDataDom(task140_SpecificSubSampling_elem, 'OutputFile')
        settings_struct.tasks.task140_SpecificSubSampling[pos].proposalTable = getValueNodeDataDom(task140_SpecificSubSampling_elem, 'ProposalTable')
        value = getValueNodeDataDom(task140_SpecificSubSampling_elem, 'SubSamplingNumber')
        if value != "" and value is not None:
            settings_struct.tasks.task140_SpecificSubSampling[pos].subSamplingNumber = int(value)
        value = getValueNodeDataDom(task140_SpecificSubSampling_elem, 'MinNumberTrainingSize')
        if value != "" and value is not None:
            settings_struct.tasks.task140_SpecificSubSampling[pos].minNumberTrainingSize = int(value)
        value = getValueNodeDataDom(task140_SpecificSubSampling_elem, 'Rand')
        if value != "" and value is not None:
            settings_struct.tasks.task140_SpecificSubSampling[pos].rand = int(value)

    # Task150_ClassRealocationRaster
    task150_ClassRealocationRaster_elem_list = findAllElement(xmldoc, 'Task150_ClassRealocationRaster','Tasks/Task150_ClassRealocationRaster_List')
    for pos in range (len(task150_ClassRealocationRaster_elem_list)):
        task150_ClassRealocationRaster_elem = task150_ClassRealocationRaster_elem_list[pos]
        settings_struct.tasks.task150_ClassRealocationRaster.append(StructTask150_ClassRealocationRaster())
        settings_struct.tasks.task150_ClassRealocationRaster[pos].inputFile = getValueNodeDataDom(task150_ClassRealocationRaster_elem, 'InputFile')
        settings_struct.tasks.task150_ClassRealocationRaster[pos].outputFile = getValueNodeDataDom(task150_ClassRealocationRaster_elem, 'OutputFile')
        settings_struct.tasks.task150_ClassRealocationRaster[pos].proposalTable = getValueNodeDataDom(task150_ClassRealocationRaster_elem, 'ProposalTable')

    # Task160_MicroclassFusion
    task160_MicroclassFusion_elem_list = findAllElement(xmldoc, 'Task160_MicroclassFusion','Tasks/Task160_MicroclassFusion_List')
    for pos in range (len(task160_MicroclassFusion_elem_list)):
        task160_MicroclassFusion_elem = task160_MicroclassFusion_elem_list[pos]
        settings_struct.tasks.task160_MicroclassFusion.append(StructTask160_MicroclassFusion())
        settings_struct.tasks.task160_MicroclassFusion[pos].inputFile = getValueNodeDataDom(task160_MicroclassFusion_elem, 'InputFile')
        settings_struct.tasks.task160_MicroclassFusion[pos].outputFile = getValueNodeDataDom(task160_MicroclassFusion_elem, 'OutputFile')
        settings_struct.tasks.task160_MicroclassFusion[pos].expression = getValueNodeDataDom(task160_MicroclassFusion_elem, 'Expression')

    # Task170_MajorityFilter
    task170_MajorityFilter_elem_list = findAllElement(xmldoc, 'Task170_MajorityFilter','Tasks/Task170_MajorityFilter_List')
    for pos in range (len(task170_MajorityFilter_elem_list)):
        task170_MajorityFilter_elem = task170_MajorityFilter_elem_list[pos]
        settings_struct.tasks.task170_MajorityFilter.append(StructTask170_MajorityFilter())
        settings_struct.tasks.task170_MajorityFilter[pos].inputFile = getValueNodeDataDom(task170_MajorityFilter_elem, 'InputFile')
        settings_struct.tasks.task170_MajorityFilter[pos].outputFile = getValueNodeDataDom(task170_MajorityFilter_elem, 'OutputFile')
        settings_struct.tasks.task170_MajorityFilter[pos].filterMode = getValueNodeDataDom(task170_MajorityFilter_elem, 'FilterMode')
        value = getValueNodeDataDom(task170_MajorityFilter_elem, 'RadiusMajority')
        if value != "" and value is not None:
            settings_struct.tasks.task170_MajorityFilter[pos].radiusMajority = int(value)
        value = getValueNodeDataDom(task170_MajorityFilter_elem, 'UmcPixels')
        if value != "" and value is not None:
            settings_struct.tasks.task170_MajorityFilter[pos].umcPixels = int(value)

    # Task180_DataBaseSuperposition
    task180_DataBaseSuperposition_elem_list = findAllElement(xmldoc, 'Task180_DataBaseSuperposition','Tasks/Task180_DataBaseSuperposition_List')
    for pos in range (len(task180_DataBaseSuperposition_elem_list)):
        task180_DataBaseSuperposition_elem = task180_DataBaseSuperposition_elem_list[pos]
        settings_struct.tasks.task180_DataBaseSuperposition.append(StructTask180_DataBaseSuperposition())
        settings_struct.tasks.task180_DataBaseSuperposition[pos].inputFile = getValueNodeDataDom(task180_DataBaseSuperposition_elem, 'InputFile')
        settings_struct.tasks.task180_DataBaseSuperposition[pos].outputFile = getValueNodeDataDom(task180_DataBaseSuperposition_elem, 'OutputFile')
        value = getValueNodeDataDom(task180_DataBaseSuperposition_elem, 'SimplificationPolygon')
        if value != "" and value is not None:
            settings_struct.tasks.task180_DataBaseSuperposition[pos].simplificationPolygon = float(value)
        labels_list = getListValueAttributeDom(task180_DataBaseSuperposition_elem, 'ClassMacroSuperpositionList', 'ClassMacroSuperposition', 'label')
        elements_list = findAllElement(task180_DataBaseSuperposition_elem, 'ClassMacroSuperposition', 'ClassMacroSuperpositionList')
        settings_struct.tasks.task180_DataBaseSuperposition[pos].classMacroSuperpositionList = []
        for index1 in range (len(elements_list)) :
            element = elements_list[index1]
            database_files_list = getListNodeDataDom(element, 'DataBaseFilesList', 'DataBaseFile')
            buffers_list = getListValueAttributeDom(element, 'DataBaseFilesList', 'DataBaseFile', 'buffer')
            sql_expressions_list = getListValueAttributeDom(element, 'DataBaseFilesList', 'DataBaseFile', 'sql')
            class_macro_superposition_struct = StructDataBaseSuperposition_ClassMacro()
            class_macro_superposition_struct.dataBaseFileList = []
            class_macro_superposition_struct.label = labels_list[index1]
            for index2 in range (len(database_files_list)) :
                database_file = database_files_list[index2]
                sql_expression = sql_expressions_list[index2]
                if buffers_list[index2] != "" and buffers_list[index2] is not None:
                    buffer_value = str(buffers_list[index2])
                else:
                    buffer_value = 0
                database_file_struct = StructCreation_DatabaseFile()
                database_file_struct.inputVector = database_file
                database_file_struct.bufferValue = buffer_value
                database_file_struct.sqlExpression = sql_expression
                class_macro_superposition_struct.dataBaseFileList.append(database_file_struct)
            settings_struct.tasks.task180_DataBaseSuperposition[pos].classMacroSuperpositionList.append(class_macro_superposition_struct)

    # Task190_ClassificationRasterAssembly
    task190_ClassificationRasterAssembly_elem_list = findAllElement(xmldoc, 'Task190_ClassificationRasterAssembly','Tasks/Task190_ClassificationRasterAssembly_List')
    for pos in range (len(task190_ClassificationRasterAssembly_elem_list)):
        task190_ClassificationRasterAssembly_elem = task190_ClassificationRasterAssembly_elem_list[pos]
        settings_struct.tasks.task190_ClassificationRasterAssembly.append(StructTask190_ClassificationRasterAssembly())
        settings_struct.tasks.task190_ClassificationRasterAssembly[pos].inputFilesList = getListNodeDataDom(task190_ClassificationRasterAssembly_elem, 'InputFilesList', 'InputFile')
        settings_struct.tasks.task190_ClassificationRasterAssembly[pos].outputFile = getValueNodeDataDom(task190_ClassificationRasterAssembly_elem, 'OutputFile')
        settings_struct.tasks.task190_ClassificationRasterAssembly[pos].inputVector = getValueNodeDataDom(task190_ClassificationRasterAssembly_elem, 'InputVector')
        value = getValueNodeDataDom(task190_ClassificationRasterAssembly_elem, 'Radius')
        if value != "" and value is not None:
            settings_struct.tasks.task190_ClassificationRasterAssembly[pos].radius = int(value)
        value = getValueNodeDataDom(task190_ClassificationRasterAssembly_elem, 'ValueToForce')
        if value != "" and value is not None:
            settings_struct.tasks.task190_ClassificationRasterAssembly[pos].valueToForce = int(value)

    # Task200_ClassificationVectorization
    task200_ClassificationVectorization_elem_list = findAllElement(xmldoc, 'Task200_ClassificationVectorization','Tasks/Task200_ClassificationVectorization_List')
    for pos in range (len(task200_ClassificationVectorization_elem_list)):
        task200_ClassificationVectorization_elem = task200_ClassificationVectorization_elem_list[pos]
        settings_struct.tasks.task200_ClassificationVectorization.append(StructTask200_ClassificationVectorization())
        settings_struct.tasks.task200_ClassificationVectorization[pos].inputFile = getValueNodeDataDom(task200_ClassificationVectorization_elem,'InputFile')
        settings_struct.tasks.task200_ClassificationVectorization[pos].outputFile = getValueNodeDataDom(task200_ClassificationVectorization_elem, 'OutputFile')
        settings_struct.tasks.task200_ClassificationVectorization[pos].inputVector = getValueNodeDataDom(task200_ClassificationVectorization_elem, 'InputVector')
        settings_struct.tasks.task200_ClassificationVectorization[pos].expression = getValueNodeDataDom(task200_ClassificationVectorization_elem, 'Expression')
        settings_struct.tasks.task200_ClassificationVectorization[pos].vectorizationType = getValueNodeDataDom(task200_ClassificationVectorization_elem, 'VectorizationType')
        value = getValueNodeDataDom(task200_ClassificationVectorization_elem, 'UMC')
        if value != "" and value is not None:
            settings_struct.tasks.task200_ClassificationVectorization[pos].umc = int(value)
        value = getValueNodeDataDom(task200_ClassificationVectorization_elem, 'TileSize')
        if value != "" and value is not None:
            settings_struct.tasks.task200_ClassificationVectorization[pos].tileSize = int(value)
        settings_struct.tasks.task200_ClassificationVectorization[pos].topologicalCorrectionSQL = getValueNodeDataDom(task200_ClassificationVectorization_elem, 'TopologicalCorrectionSQL').lower() == 'true'

    # Task210_CrossingVectorRaster
    task210_CrossingVectorRaster_elem_list = findAllElement(xmldoc, 'Task210_CrossingVectorRaster','Tasks/Task210_CrossingVectorRaster_List')
    for pos in range (len(task210_CrossingVectorRaster_elem_list)):
        task210_CrossingVectorRaster_elem = task210_CrossingVectorRaster_elem_list[pos]
        settings_struct.tasks.task210_CrossingVectorRaster.append(StructTask210_CrossingVectorRaster())
        settings_struct.tasks.task210_CrossingVectorRaster[pos].inputFile = getValueNodeDataDom(task210_CrossingVectorRaster_elem,'InputFile')
        settings_struct.tasks.task210_CrossingVectorRaster[pos].outputVector = getValueNodeDataDom(task210_CrossingVectorRaster_elem, 'OutputVector')
        settings_struct.tasks.task210_CrossingVectorRaster[pos].inputVector = getValueNodeDataDom(task210_CrossingVectorRaster_elem, 'InputVector')
        value = getValueNodeDataDom(task210_CrossingVectorRaster_elem, 'BandNumber')
        if value != "" and value is not None:
            settings_struct.tasks.task210_CrossingVectorRaster[pos].bandNumber = int(value)
        settings_struct.tasks.task210_CrossingVectorRaster[pos].statsAllCount = getValueNodeDataDom(task210_CrossingVectorRaster_elem, 'StatsAllCount').lower() == 'true'
        settings_struct.tasks.task210_CrossingVectorRaster[pos].statsColumnsStr = getValueNodeDataDom(task210_CrossingVectorRaster_elem, 'StatsColumnsStr').lower() == 'true'
        settings_struct.tasks.task210_CrossingVectorRaster[pos].statsColumnsReal = getValueNodeDataDom(task210_CrossingVectorRaster_elem, 'StatsColumnsReal').lower() == 'true'

    # Task210_RA_CrossingVectorRaster
    task210_RA_CrossingVectorRaster_elem_list = findAllElement(xmldoc, 'Task210_RA_CrossingVectorRaster','Tasks/Task210_RA_CrossingVectorRaster_List')
    for pos in range (len(task210_RA_CrossingVectorRaster_elem_list)):
        task210_RA_CrossingVectorRaster_elem = task210_RA_CrossingVectorRaster_elem_list[pos]
        settings_struct.tasks.task210_RA_CrossingVectorRaster.append(StructTask210_RA_CrossingVectorRaster())
        settings_struct.tasks.task210_RA_CrossingVectorRaster[pos].inputClassifFile = getValueNodeDataDom(task210_RA_CrossingVectorRaster_elem,'InputClassifFile')
        settings_struct.tasks.task210_RA_CrossingVectorRaster[pos].inputCorrectionFile = getValueNodeDataDom(task210_RA_CrossingVectorRaster_elem,'InputCorrectionFile')
        settings_struct.tasks.task210_RA_CrossingVectorRaster[pos].inputVector = getValueNodeDataDom(task210_RA_CrossingVectorRaster_elem,'InputVector')
        settings_struct.tasks.task210_RA_CrossingVectorRaster[pos].outputVector = getValueNodeDataDom(task210_RA_CrossingVectorRaster_elem,'OutputVector')
        settings_struct.tasks.task210_RA_CrossingVectorRaster[pos].columToAddCouvList = getListNodeDataDom(task210_RA_CrossingVectorRaster_elem, 'ColumToAddCouvList', 'ColumToAddCouv', 'Couverture')
        settings_struct.tasks.task210_RA_CrossingVectorRaster[pos].columToDeleteCouvlist = getListNodeDataDom(task210_RA_CrossingVectorRaster_elem, 'ColumToDeleteCouvlist', 'ColumToDeleteCouv', 'Couverture')
        settings_struct.tasks.task210_RA_CrossingVectorRaster[pos].columToAddDateList = getListNodeDataDom(task210_RA_CrossingVectorRaster_elem, 'ColumToAddDateList', 'ColumToAddDate', 'DateOrigine')
        settings_struct.tasks.task210_RA_CrossingVectorRaster[pos].columToAddSrcList = getListNodeDataDom(task210_RA_CrossingVectorRaster_elem, 'ColumToAddSrcList', 'ColumToAddSrc', 'SourceOrigine')
        settings_struct.tasks.task210_RA_CrossingVectorRaster[pos].classLabelDateDico = getValueNodeDataDom(task210_RA_CrossingVectorRaster_elem,'ClassLabelDateDico', 'DateOrigine')
        settings_struct.tasks.task210_RA_CrossingVectorRaster[pos].classLabelSrcDico = getValueNodeDataDom(task210_RA_CrossingVectorRaster_elem,'ClassLabelSrcDico', 'SourceOrigine')

    # Task220_VectorRasterCutting
    task220_VectorRasterCutting_elem_list = findAllElement(xmldoc, 'Task220_VectorRasterCutting','Tasks/Task220_VectorRasterCutting_List')
    for pos in range (len(task220_VectorRasterCutting_elem_list)):
        task220_VectorRasterCutting_elem = task220_VectorRasterCutting_elem_list[pos]
        settings_struct.tasks.task220_VectorRasterCutting.append(StructTask220_VectorRasterCutting())
        settings_struct.tasks.task220_VectorRasterCutting[pos].inputFilesList = getListNodeDataDom(task220_VectorRasterCutting_elem, 'InputFilesList', 'InputFile')
        settings_struct.tasks.task220_VectorRasterCutting[pos].inputVectorsList = getListNodeDataDom(task220_VectorRasterCutting_elem, 'InputVectorsList', 'InputVector')
        settings_struct.tasks.task220_VectorRasterCutting[pos].outputFilesList = getListNodeDataDom(task220_VectorRasterCutting_elem, 'OutputFilesList', 'OutputFile')
        settings_struct.tasks.task220_VectorRasterCutting[pos].outputVectorsList = getListNodeDataDom(task220_VectorRasterCutting_elem, 'OutputVectorsList', 'OutputVector')
        settings_struct.tasks.task220_VectorRasterCutting[pos].inputCutVector = getValueNodeDataDom(task220_VectorRasterCutting_elem, 'InputCutVector')
        value = getValueNodeDataDom(task220_VectorRasterCutting_elem, 'OverflowNbPixels')
        if value != "" and value is not None:
            settings_struct.tasks.task220_VectorRasterCutting[pos].overflowNbPixels = int(value)
        value = getValueNodeDataDom(task220_VectorRasterCutting_elem, 'RoundPixelSize')
        if value != "" and value is not None:
            settings_struct.tasks.task220_VectorRasterCutting[pos].roundPixelSize = float(value)
        settings_struct.tasks.task220_VectorRasterCutting[pos].resamplingMethode = getValueNodeDataDom(task220_VectorRasterCutting_elem, 'ResamplingMethode')
        settings_struct.tasks.task220_VectorRasterCutting[pos].compression = getValueNodeDataDom(task220_VectorRasterCutting_elem, 'Compression').lower() == 'true'

    # Task230_QualityIndicatorComputation
    task230_QualityIndicatorComputation_elem_list = findAllElement(xmldoc, 'Task230_QualityIndicatorComputation','Tasks/Task230_QualityIndicatorComputation_List')
    for pos in range (len(task230_QualityIndicatorComputation_elem_list)):
        task230_QualityIndicatorComputation_elem = task230_QualityIndicatorComputation_elem_list[pos]
        settings_struct.tasks.task230_QualityIndicatorComputation.append(StructTask230_QualityIndicatorComputation())
        settings_struct.tasks.task230_QualityIndicatorComputation[pos].inputFile = getValueNodeDataDom(task230_QualityIndicatorComputation_elem, 'InputFile')
        settings_struct.tasks.task230_QualityIndicatorComputation[pos].inputVector = getValueNodeDataDom(task230_QualityIndicatorComputation_elem, 'InputVector')
        settings_struct.tasks.task230_QualityIndicatorComputation[pos].inputSample = getValueNodeDataDom(task230_QualityIndicatorComputation_elem, 'InputSample')
        settings_struct.tasks.task230_QualityIndicatorComputation[pos].outputFile = getValueNodeDataDom(task230_QualityIndicatorComputation_elem, 'OutputFile')
        settings_struct.tasks.task230_QualityIndicatorComputation[pos].outputMatrix = getValueNodeDataDom(task230_QualityIndicatorComputation_elem, 'OutputMatrix')

    # Task240_RA_ProductOcsVerificationCorrectionSQL
    task240_RA_ProductOcsVerificationCorrectionSQL_elem_list = findAllElement(xmldoc, 'Task240_RA_ProductOcsVerificationCorrectionSQL','Tasks/Task240_RA_ProductOcsVerificationCorrectionSQL_List')
    for pos in range (len(task240_RA_ProductOcsVerificationCorrectionSQL_elem_list)):
        task240_RA_ProductOcsVerificationCorrectionSQL_elem = task240_RA_ProductOcsVerificationCorrectionSQL_elem_list[pos]
        settings_struct.tasks.task240_RA_ProductOcsVerificationCorrectionSQL.append(StructTask240_RA_ProductOcsVerificationCorrectionSQL())
        settings_struct.tasks.task240_RA_ProductOcsVerificationCorrectionSQL[pos].inputEmpriseVector = getValueNodeDataDom(task240_RA_ProductOcsVerificationCorrectionSQL_elem,'InputEmpriseVector')
        settings_struct.tasks.task240_RA_ProductOcsVerificationCorrectionSQL[pos].inputVectorsList = getListNodeDataDom(task240_RA_ProductOcsVerificationCorrectionSQL_elem, 'InputVectorsList', 'InputVector')
        settings_struct.tasks.task240_RA_ProductOcsVerificationCorrectionSQL[pos].outputVectorsList = getListNodeDataDom(task240_RA_ProductOcsVerificationCorrectionSQL_elem, 'OutputVectorsList', 'OutputVector')

   # Task250_RA_ProductOcsRasterisation
    task250_RA_ProductOcsRasterisation_elem_list = findAllElement(xmldoc, 'Task250_RA_ProductOcsRasterisation','Tasks/Task250_RA_ProductOcsRasterisation_List')
    for pos in range (len(task250_RA_ProductOcsRasterisation_elem_list)):
        task250_RA_ProductOcsRasterisation_elem = task250_RA_ProductOcsRasterisation_elem_list[pos]
        settings_struct.tasks.task250_RA_ProductOcsRasterisation.append(StructTask250_RA_ProductOcsRasterisation())
        settings_struct.tasks.task250_RA_ProductOcsRasterisation[pos].inputVector = getValueNodeDataDom(task250_RA_ProductOcsRasterisation_elem, 'InputVector')
        settings_struct.tasks.task250_RA_ProductOcsRasterisation[pos].inputFile = getValueNodeDataDom(task250_RA_ProductOcsRasterisation_elem, 'InputFile')
        settings_struct.tasks.task250_RA_ProductOcsRasterisation[pos].outputFile = getValueNodeDataDom(task250_RA_ProductOcsRasterisation_elem, 'OutputFile')
        settings_struct.tasks.task250_RA_ProductOcsRasterisation[pos].label = getValueNodeDataDom(task250_RA_ProductOcsRasterisation_elem, 'Label')
        value = getValueNodeDataDom(task250_RA_ProductOcsRasterisation_elem, 'NodataOutput')
        if value != "" and value is not None:
            settings_struct.tasks.task250_RA_ProductOcsRasterisation[pos].nodataOutput = int(value)
        settings_struct.tasks.task250_RA_ProductOcsRasterisation[pos].encodingOutput = getValueNodeDataDom(task250_RA_ProductOcsRasterisation_elem, 'EncodingOutput')

    # Task260_SegmentationImage
    task260_SegmenationImage_elem_list = findAllElement(xmldoc, 'Task260_SegmentationImage','Tasks/Task260_SegmentationImage_List')
    for pos in range (len(task260_SegmenationImage_elem_list)):
        task260_SegmentationImage_elem = task260_SegmenationImage_elem_list[pos]
        settings_struct.tasks.task260_SegmentationImage.append(StructTask260_SegmentationImage())
        settings_struct.tasks.task260_SegmentationImage[pos].inputFile = getValueNodeDataDom(task260_SegmentationImage_elem,'InputFile')
        settings_struct.tasks.task260_SegmentationImage[pos].outputVector = getValueNodeDataDom(task260_SegmentationImage_elem, 'OutputVector')
        settings_struct.tasks.task260_SegmentationImage[pos].segmenationType = getValueNodeDataDom(task260_SegmentationImage_elem, 'SegmenationType')
        value = getValueNodeDataDom(task260_SegmentationImage_elem, 'Spatialr','SMS')
        if value != "" and value is not None:
            settings_struct.tasks.task260_SegmentationImage[pos].sms_spatialr = int(value)
        value = getValueNodeDataDom(task260_SegmentationImage_elem, 'Ranger','SMS')
        if value != "" and value is not None:
            settings_struct.tasks.task260_SegmentationImage[pos].sms_ranger = float(value)
        value = getValueNodeDataDom(task260_SegmentationImage_elem, 'Minsize','SMS')
        if value != "" and value is not None:
            settings_struct.tasks.task260_SegmentationImage[pos].sms_minsize = int(value)
        value = getValueNodeDataDom(task260_SegmentationImage_elem, 'TileSize','SMS')
        if value != "" and value is not None:
            settings_struct.tasks.task260_SegmentationImage[pos].sms_tileSize = int(value)
        settings_struct.tasks.task260_SegmentationImage[pos].srm_homogeneityCriterion = getValueNodeDataDom(task260_SegmentationImage_elem, 'HomogeneityCriterion', 'SRM')
        value = getValueNodeDataDom(task260_SegmentationImage_elem, 'Threshol', 'SRM')
        if value != "" and value is not None:
            settings_struct.tasks.task260_SegmentationImage[pos].srm_threshol = float(value)
        value = getValueNodeDataDom(task260_SegmentationImage_elem, 'NbIter', 'SRM')
        if value != "" and value is not None:
           settings_struct.tasks.task260_SegmentationImage[pos].srm_nbIter = int(value)
        value = getValueNodeDataDom(task260_SegmentationImage_elem, 'Speed', 'SRM')
        if value != "" and value is not None:
            settings_struct.tasks.task260_SegmentationImage[pos].srm_speed = int(value)
        value = getValueNodeDataDom(task260_SegmentationImage_elem, 'WeightSpectral', 'SRM')
        if value != "" and value is not None:
            settings_struct.tasks.task260_SegmentationImage[pos].srm_weightSpectral = float(value)
        value = getValueNodeDataDom(task260_SegmentationImage_elem, 'WeightSpatial', 'SRM')
        if value != "" and value is not None:
            settings_struct.tasks.task260_SegmentationImage[pos].srm_weightSpatial = float(value)

    # Task270_ClassificationVector
    task270_ClassificationVector_elem_list = findAllElement(xmldoc, 'Task270_ClassificationVector','Tasks/Task270_ClassificationVector_List')
    for pos in range (len(task270_ClassificationVector_elem_list)):
        task270_ClassificationVector_elem = task270_ClassificationVector_elem_list[pos]
        settings_struct.tasks.task270_ClassificationVector.append(StructTask270_ClassificationVector())
        settings_struct.tasks.task270_ClassificationVector[pos].inputVector = getValueNodeDataDom(task270_ClassificationVector_elem,'InputVector')
        settings_struct.tasks.task270_ClassificationVector[pos].outputVector = getValueNodeDataDom(task270_ClassificationVector_elem, 'OutputVector')
        settings_struct.tasks.task270_ClassificationVector[pos].fieldList = getListNodeDataDom(task270_ClassificationVector_elem, 'FieldList', 'Field')
        settings_struct.tasks.task270_ClassificationVector[pos].inputCfield = getValueNodeDataDom(task270_ClassificationVector_elem, 'InputCfield')
        settings_struct.tasks.task270_ClassificationVector[pos].outputCfield = getValueNodeDataDom(task270_ClassificationVector_elem, 'OutputCfield')
        settings_struct.tasks.task270_ClassificationVector[pos].expression = getValueNodeDataDom(task270_ClassificationVector_elem, 'Expression')

    # Task5_TDC_CreateEmprise
    task5_TDC_CreateEmprise_elem_list = findAllElement(xmldoc, 'Task5_TDC_CreateEmprise','Tasks/Task5_TDC_CreateEmprise_List')
    for pos in range (len(task5_TDC_CreateEmprise_elem_list)):
        task5_TDC_CreateEmprise_elem = task5_TDC_CreateEmprise_elem_list[pos]
        settings_struct.tasks.task5_TDC_CreateEmprise.append(StructTask5_TDC_CreateEmprise())
        settings_struct.tasks.task5_TDC_CreateEmprise[pos].inputPath = getValueNodeDataDom(task5_TDC_CreateEmprise_elem, 'InputPath')
        settings_struct.tasks.task5_TDC_CreateEmprise[pos].outputVector = getValueNodeDataDom(task5_TDC_CreateEmprise_elem, 'OutputVector')
        settings_struct.tasks.task5_TDC_CreateEmprise[pos].noAssembled = getValueNodeDataDom(task5_TDC_CreateEmprise_elem, 'NoAssembled').lower() == 'true'
        settings_struct.tasks.task5_TDC_CreateEmprise[pos].allPolygon = getValueNodeDataDom(task5_TDC_CreateEmprise_elem, 'AllPolygon').lower() == 'true'
        settings_struct.tasks.task5_TDC_CreateEmprise[pos].noDate = getValueNodeDataDom(task5_TDC_CreateEmprise_elem, 'NoDate').lower() == 'true'
        settings_struct.tasks.task5_TDC_CreateEmprise[pos].optimisationEmprise = getValueNodeDataDom(task5_TDC_CreateEmprise_elem, 'OptimisationEmprise').lower() == 'true'
        settings_struct.tasks.task5_TDC_CreateEmprise[pos].optimisationNoData = getValueNodeDataDom(task5_TDC_CreateEmprise_elem, 'OptimisationNoData').lower() == 'true'
        value = getValueNodeDataDom(task5_TDC_CreateEmprise_elem, 'Erode')
        if value != "" and value is not None:
            settings_struct.tasks.task5_TDC_CreateEmprise[pos].erode = float(value)
        settings_struct.tasks.task5_TDC_CreateEmprise[pos].dateSplitter = getValueNodeDataDom(task5_TDC_CreateEmprise_elem, 'DateSplitter')
        value = getValueNodeDataDom(task5_TDC_CreateEmprise_elem, 'DatePosition')
        if value != "" and value is not None:
            settings_struct.tasks.task5_TDC_CreateEmprise[pos].datePosition = int(value)
        value = getValueNodeDataDom(task5_TDC_CreateEmprise_elem, 'DateNumberOfCharacters')
        if value != "" and value is not None:
            settings_struct.tasks.task5_TDC_CreateEmprise[pos].dateNumberOfCharacters = int(value)
        settings_struct.tasks.task5_TDC_CreateEmprise[pos].intraDateSplitter = getValueNodeDataDom(task5_TDC_CreateEmprise_elem, 'IntraDateSplitter')

    # Task10_TDC_PolygonMerToTDC
    task10_TDC_PolygonMerToTDC_elem_list = findAllElement(xmldoc, 'Task10_TDC_PolygonMerToTDC','Tasks/Task10_TDC_PolygonMerToTDC_List')
    for pos in range (len(task10_TDC_PolygonMerToTDC_elem_list)):
        task10_TDC_PolygonMerToTDC_elem = task10_TDC_PolygonMerToTDC_elem_list[pos]
        settings_struct.tasks.task10_TDC_PolygonMerToTDC.append(StructTask10_TDC_PolygonMerToTDC())
        settings_struct.tasks.task10_TDC_PolygonMerToTDC[pos].inputFile = getValueNodeDataDom(task10_TDC_PolygonMerToTDC_elem, 'InputFile')
        settings_struct.tasks.task10_TDC_PolygonMerToTDC[pos].ndviMaskVectorList = getListNodeDataDom(task10_TDC_PolygonMerToTDC_elem, 'NdviMaskVectorList', 'NdviMaskVector')
        settings_struct.tasks.task10_TDC_PolygonMerToTDC[pos].inputSeaPointsFile = getValueNodeDataDom(task10_TDC_PolygonMerToTDC_elem, 'InputSeaPointsFile')
        settings_struct.tasks.task10_TDC_PolygonMerToTDC[pos].outputPath = getValueNodeDataDom(task10_TDC_PolygonMerToTDC_elem, 'OutputPath')
        settings_struct.tasks.task10_TDC_PolygonMerToTDC[pos].inputCutVector = getValueNodeDataDom(task10_TDC_PolygonMerToTDC_elem, 'InputCutVector')
        settings_struct.tasks.task10_TDC_PolygonMerToTDC[pos].resultBinMaskVectorFunction = getValueNodeDataDom(task10_TDC_PolygonMerToTDC_elem, 'ResultBinMaskVectorFunction').lower() == 'true'
        settings_struct.tasks.task10_TDC_PolygonMerToTDC[pos].simplifParameter = getValueNodeDataDom(task10_TDC_PolygonMerToTDC_elem, 'SimplifParameter')
        settings_struct.tasks.task10_TDC_PolygonMerToTDC[pos].positiveBufferSize = getValueNodeDataDom(task10_TDC_PolygonMerToTDC_elem, 'PositiveBufferSize')
        settings_struct.tasks.task10_TDC_PolygonMerToTDC[pos].negativeBufferSize = getValueNodeDataDom(task10_TDC_PolygonMerToTDC_elem, 'NegativeBufferSize')

    # Task20_TDC_PrepareData
    task20_TDC_PrepareData_elem_list = findAllElement(xmldoc, 'Task20_TDC_PrepareData','Tasks/Task20_TDC_PrepareData_List')
    for pos in range (len(task20_TDC_PrepareData_elem_list)):
        task20_TDC_PrepareData_elem = task20_TDC_PrepareData_elem_list[pos]
        settings_struct.tasks.task20_TDC_PrepareData.append(StructTask20_TDC_PrepareData())
        settings_struct.tasks.task20_TDC_PrepareData[pos].inputBufferTDC = getValueNodeDataDom(task20_TDC_PrepareData_elem, 'InputBufferTDC')
        settings_struct.tasks.task20_TDC_PrepareData[pos].inputVectorPaysage = getValueNodeDataDom(task20_TDC_PrepareData_elem, 'InputVectorPaysage')
        settings_struct.tasks.task20_TDC_PrepareData[pos].outputPath = getValueNodeDataDom(task20_TDC_PrepareData_elem, 'OutputPath')
        settings_struct.tasks.task20_TDC_PrepareData[pos].sourceImagesDirList = getListNodeDataDom(task20_TDC_PrepareData_elem, 'SourceImagesDirList','ImagesDir')
        settings_struct.tasks.task20_TDC_PrepareData[pos].idPaysage = getValueNodeDataDom(task20_TDC_PrepareData_elem, 'IdPaysage')
        settings_struct.tasks.task20_TDC_PrepareData[pos].idNameSubRep = getValueNodeDataDom(task20_TDC_PrepareData_elem, 'IdNameSubRep')
        settings_struct.tasks.task20_TDC_PrepareData[pos].optimisationZone = getValueNodeDataDom(task20_TDC_PrepareData_elem, 'OptimisationZone').lower() == 'true'
        settings_struct.tasks.task20_TDC_PrepareData[pos].zoneDate = getValueNodeDataDom(task20_TDC_PrepareData_elem, 'ZoneDate').lower() == 'true'
        settings_struct.tasks.task20_TDC_PrepareData[pos].noCover = getValueNodeDataDom(task20_TDC_PrepareData_elem, 'NoCover').lower() == 'true'
        settings_struct.tasks.task20_TDC_PrepareData[pos].dateSplitter = getValueNodeDataDom(task20_TDC_PrepareData_elem, 'DateSplitter')
        value = getValueNodeDataDom(task20_TDC_PrepareData_elem, 'DatePosition')
        if value != "" and value is not None:
            settings_struct.tasks.task20_TDC_PrepareData[pos].datePosition = int(value)
        value = getValueNodeDataDom(task20_TDC_PrepareData_elem, 'DateNumberOfCharacters')
        if value != "" and value is not None:
            settings_struct.tasks.task20_TDC_PrepareData[pos].dateNumberOfCharacters = int(value)
        settings_struct.tasks.task20_TDC_PrepareData[pos].intraDateSplitter = getValueNodeDataDom(task20_TDC_PrepareData_elem, 'IntraDateSplitter')

    # Task30_TDC_TDCSeuil
    task30_TDC_TDCSeuil_elem_list = findAllElement(xmldoc, 'Task30_TDC_TDCSeuil','Tasks/Task30_TDC_TDCSeuil_List')
    for pos in range (len(task30_TDC_TDCSeuil_elem_list)):
        task30_TDC_TDCSeuil_elem = task30_TDC_TDCSeuil_elem_list[pos]
        settings_struct.tasks.task30_TDC_TDCSeuil.append(StructTask30_TDC_TDCSeuil())
        settings_struct.tasks.task30_TDC_TDCSeuil[pos].inputFile = getValueNodeDataDom(task30_TDC_TDCSeuil_elem, 'InputFile')
        settings_struct.tasks.task30_TDC_TDCSeuil[pos].sourceIndexImageThresholdsList = getListNodeDataDom(task30_TDC_TDCSeuil_elem, 'SourceIndexImageThresholdsList', 'IndexImageThreshold')
        settings_struct.tasks.task30_TDC_TDCSeuil[pos].outputPath = getValueNodeDataDom(task30_TDC_TDCSeuil_elem, 'OutputPath')
        settings_struct.tasks.task30_TDC_TDCSeuil[pos].inputSeaPointsFile = getValueNodeDataDom(task30_TDC_TDCSeuil_elem, 'InputSeaPointsFile')
        settings_struct.tasks.task30_TDC_TDCSeuil[pos].inputCutVector = getValueNodeDataDom(task30_TDC_TDCSeuil_elem, 'InputCutVector')
        settings_struct.tasks.task30_TDC_TDCSeuil[pos].inputEmpriseVector = getValueNodeDataDom(task30_TDC_TDCSeuil_elem, 'InputEmpriseVector')
        settings_struct.tasks.task30_TDC_TDCSeuil[pos].simplifParameter = getValueNodeDataDom(task30_TDC_TDCSeuil_elem, 'SimplifParameter')
        settings_struct.tasks.task30_TDC_TDCSeuil[pos].calcIndiceImage = getValueNodeDataDom(task30_TDC_TDCSeuil_elem, 'CalcIndiceImage').lower() == 'true'
        settings_struct.tasks.task30_TDC_TDCSeuil[pos].attributeValLimite = getValueNodeDataDom(task30_TDC_TDCSeuil_elem, 'AttributeValLimite')
        settings_struct.tasks.task30_TDC_TDCSeuil[pos].attributeValProced = getValueNodeDataDom(task30_TDC_TDCSeuil_elem, 'AttributeValProced')
        settings_struct.tasks.task30_TDC_TDCSeuil[pos].attributeValDatepr = getValueNodeDataDom(task30_TDC_TDCSeuil_elem, 'AttributeValDatepr')
        settings_struct.tasks.task30_TDC_TDCSeuil[pos].attributeValPrecis = getValueNodeDataDom(task30_TDC_TDCSeuil_elem, 'AttributeValPrecis')
        settings_struct.tasks.task30_TDC_TDCSeuil[pos].attributeValContac = getValueNodeDataDom(task30_TDC_TDCSeuil_elem, 'AttributeValContac')
        settings_struct.tasks.task30_TDC_TDCSeuil[pos].attributeValType = getValueNodeDataDom(task30_TDC_TDCSeuil_elem, 'AttributeValType')

    # Task40_TDC_TDCKmeans
    task40_TDC_TDCKmeans_elem_list = findAllElement(xmldoc, 'Task40_TDC_TDCKmeans','Tasks/Task40_TDC_TDCKmeans_List')
    for pos in range (len(task40_TDC_TDCKmeans_elem_list)):
        task40_TDC_TDCKmeans_elem = task40_TDC_TDCKmeans_elem_list[pos]
        settings_struct.tasks.task40_TDC_TDCKmeans.append(StructTask40_TDC_TDCKmeans())
        settings_struct.tasks.task40_TDC_TDCKmeans[pos].inputFile = getValueNodeDataDom(task40_TDC_TDCKmeans_elem, 'InputFile')
        settings_struct.tasks.task40_TDC_TDCKmeans[pos].outputPath = getValueNodeDataDom(task40_TDC_TDCKmeans_elem, 'OutputPath')
        settings_struct.tasks.task40_TDC_TDCKmeans[pos].classesNumber = getValueNodeDataDom(task40_TDC_TDCKmeans_elem, 'ClassesNumber')
        settings_struct.tasks.task40_TDC_TDCKmeans[pos].inputSeaPointsFile = getValueNodeDataDom(task40_TDC_TDCKmeans_elem, 'InputSeaPointsFile')
        settings_struct.tasks.task40_TDC_TDCKmeans[pos].inputCutVector = getValueNodeDataDom(task40_TDC_TDCKmeans_elem, 'InputCutVector')

    # Task50_TDC_TDCClassif
    task50_TDC_TDCClassif_elem_list = findAllElement(xmldoc, 'Task50_TDC_TDCClassif','Tasks/Task50_TDC_TDCClassif_List')
    for pos in range (len(task50_TDC_TDCClassif_elem_list)):
        task50_TDC_TDCClassif_elem = task50_TDC_TDCClassif_elem_list[pos]
        settings_struct.tasks.task50_TDC_TDCClassif.append(StructTask50_TDC_TDCClassif())
        settings_struct.tasks.task50_TDC_TDCClassif[pos].inputFile = getValueNodeDataDom(task50_TDC_TDCClassif_elem, 'InputFile')
        names_list = getListValueAttributeDom(task50_TDC_TDCClassif_elem, 'ClassSampleList', 'ClassSample', 'name')
        labels_list = getListValueAttributeDom(task50_TDC_TDCClassif_elem, 'ClassSampleList', 'ClassSample', 'label')
        elements_list = findAllElement(task50_TDC_TDCClassif_elem, 'ClassSample', 'ClassSampleList')
        settings_struct.tasks.task50_TDC_TDCClassif[pos].classSampleList = []
        for index in range (len(elements_list)) :
            element = elements_list[index]
            class_sample_struct = StructTDCClassif_ClassSample()
            class_sample_struct.class_properties_list = getListNodeDataDom(element, 'ClassPropertiesList', 'ClassProperty')
            if labels_list[index] != "" and labels_list[index] is not None:
                class_sample_struct.label = int(labels_list[index])
            else:
                class_sample_struct.label = 0
            if names_list[index] != "" and names_list[index] is not None:
                class_sample_struct.name = names_list[index]
            else:
                class_sample_struct.name = ''
            settings_struct.tasks.task50_TDC_TDCClassif[pos].classSampleList.append(class_sample_struct)
        settings_struct.tasks.task50_TDC_TDCClassif[pos].outputPath = getValueNodeDataDom(task50_TDC_TDCClassif_elem, 'OutputPath')
        settings_struct.tasks.task50_TDC_TDCClassif[pos].inputSeaPointsFile = getValueNodeDataDom(task50_TDC_TDCClassif_elem, 'InputSeaPointsFile')
        settings_struct.tasks.task50_TDC_TDCClassif[pos].inputCutVector = getValueNodeDataDom(task50_TDC_TDCClassif_elem, 'InputCutVector')
        settings_struct.tasks.task50_TDC_TDCClassif[pos].useExogenDB = getValueNodeDataDom(task50_TDC_TDCClassif_elem, 'UseExogenDB').lower() == 'true'
        settings_struct.tasks.task50_TDC_TDCClassif[pos].cut = getValueNodeDataDom(task50_TDC_TDCClassif_elem, 'Cut').lower() == 'true'
        settings_struct.tasks.task50_TDC_TDCClassif[pos].radiusMajority = getValueNodeDataDom(task50_TDC_TDCClassif_elem, 'RadiusMajority')
        settings_struct.tasks.task50_TDC_TDCClassif[pos].microClassFusionExpression = getValueNodeDataDom(task50_TDC_TDCClassif_elem, 'MicroClassFusionExpression')
        settings_struct.tasks.task50_TDC_TDCClassif[pos].step1Execution = getValueNodeDataDom(task50_TDC_TDCClassif_elem, 'Step1Execution').lower() == 'true'
        settings_struct.tasks.task50_TDC_TDCClassif[pos].step2Execution = getValueNodeDataDom(task50_TDC_TDCClassif_elem, 'Step2Execution').lower() == 'true'
        settings_struct.tasks.task50_TDC_TDCClassif[pos].step3Execution = getValueNodeDataDom(task50_TDC_TDCClassif_elem, 'Step3Execution').lower() == 'true'
        settings_struct.tasks.task50_TDC_TDCClassif[pos].step4Execution = getValueNodeDataDom(task50_TDC_TDCClassif_elem, 'Step4Execution').lower() == 'true'
        settings_struct.tasks.task50_TDC_TDCClassif[pos].exogenDBSuperp = getValueNodeDataDom(task50_TDC_TDCClassif_elem, 'ExogenDBSuperp').lower() == 'true'
        labels_list = getListValueAttributeDom(task50_TDC_TDCClassif_elem, 'ClassMacroSuperpositionList', 'ClassMacroSuperposition', 'label')
        elements_list = findAllElement(task50_TDC_TDCClassif_elem, 'ClassMacroSuperposition', 'ClassMacroSuperpositionList')
        settings_struct.tasks.task50_TDC_TDCClassif[pos].classMacroSuperpositionList = []
        for index1 in range (len(elements_list)) :
            element = elements_list[index1]
            database_files_list = getListNodeDataDom(element, 'DataBaseFilesList', 'DataBaseFile')
            buffers_list = getListValueAttributeDom(element, 'DataBaseFilesList', 'DataBaseFile', 'buffer')
            class_macro_superposition_struct = StructTDCClassif_ClassMacroSuperposition()
            class_macro_superposition_struct.dataBaseFileDico = {}
            class_macro_superposition_struct.label = labels_list[index1]
            for index2 in range (len(database_files_list)) :
                database_file = database_files_list[index2]
                if buffers_list[index2] != "" and buffers_list[index2] is not None:
                    buffer_value = int(buffers_list[index2])
                else:
                    buffer_value = 0
                class_macro_superposition_struct.dataBaseFileDico[database_file] = buffer_value
            settings_struct.tasks.task50_TDC_TDCClassif[pos].classMacroSuperpositionList.append(class_macro_superposition_struct)

    # Task60_TDC_DetectOuvrages
    task60_TDC_DetectOuvrages_elem_list = findAllElement(xmldoc, 'Task60_TDC_DetectOuvrages','Tasks/Task60_TDC_DetectOuvrages_List')
    for pos in range (len(task60_TDC_DetectOuvrages_elem_list)):
        task60_TDC_DetectOuvrages_elem = task60_TDC_DetectOuvrages_elem_list[pos]
        settings_struct.tasks.task60_TDC_DetectOuvrages.append(StructTask60_TDC_DetectOuvrages())
        settings_struct.tasks.task60_TDC_DetectOuvrages[pos].inputFile = getValueNodeDataDom(task60_TDC_DetectOuvrages_elem, 'InputFile')
        settings_struct.tasks.task60_TDC_DetectOuvrages[pos].sourceBufferSizeThresholdIndexImageList = getListNodeDataDom(task60_TDC_DetectOuvrages_elem, 'SourceBufferSizeThresholdIndexImageList', 'BufferSizeThresholdIndexImage')
        settings_struct.tasks.task60_TDC_DetectOuvrages[pos].outputPath = getValueNodeDataDom(task60_TDC_DetectOuvrages_elem, 'OutputPath')
        settings_struct.tasks.task60_TDC_DetectOuvrages[pos].inputSeaPointsFile = getValueNodeDataDom(task60_TDC_DetectOuvrages_elem, 'InputSeaPointsFile')
        settings_struct.tasks.task60_TDC_DetectOuvrages[pos].inputCutVector = getValueNodeDataDom(task60_TDC_DetectOuvrages_elem, 'InputCutVector')
        settings_struct.tasks.task60_TDC_DetectOuvrages[pos].method = getValueNodeDataDom(task60_TDC_DetectOuvrages_elem, 'Method')
        settings_struct.tasks.task60_TDC_DetectOuvrages[pos].indexImageBuffers = getValueNodeDataDom(task60_TDC_DetectOuvrages_elem, 'IndexImageBuffers').lower() == 'true'
        settings_struct.tasks.task60_TDC_DetectOuvrages[pos].indexImageSobel = getValueNodeDataDom(task60_TDC_DetectOuvrages_elem, 'IndexImageSobel').lower() == 'true'

    # Task70_TDC_DetectOuvragesBuffers
    task70_TDC_DetectOuvragesBuffers_elem_list = findAllElement(xmldoc, 'Task70_TDC_DetectOuvragesBuffers','Tasks/Task70_TDC_DetectOuvragesBuffers_List')
    for pos in range (len(task70_TDC_DetectOuvragesBuffers_elem_list)):
        task70_TDC_DetectOuvragesBuffers_elem = task70_TDC_DetectOuvragesBuffers_elem_list[pos]
        settings_struct.tasks.task70_TDC_DetectOuvragesBuffers.append(StructTask70_TDC_DetectOuvragesBuffers())
        settings_struct.tasks.task70_TDC_DetectOuvragesBuffers[pos].inputFile = getValueNodeDataDom(task70_TDC_DetectOuvragesBuffers_elem, 'InputFile')
        settings_struct.tasks.task70_TDC_DetectOuvragesBuffers[pos].outputPath = getValueNodeDataDom(task70_TDC_DetectOuvragesBuffers_elem, 'OutputPath')
        settings_struct.tasks.task70_TDC_DetectOuvragesBuffers[pos].bufferSizeNeg = getValueNodeDataDom(task70_TDC_DetectOuvragesBuffers_elem, 'BufferSizeNeg')
        settings_struct.tasks.task70_TDC_DetectOuvragesBuffers[pos].bufferSizePos = getValueNodeDataDom(task70_TDC_DetectOuvragesBuffers_elem, 'BufferSizePos')
        settings_struct.tasks.task70_TDC_DetectOuvragesBuffers[pos].inputCutVector = getValueNodeDataDom(task70_TDC_DetectOuvragesBuffers_elem, 'InputCutVector')

    # Task80_TDC_DetectOuvragesEdgeExtraction
    task80_TDC_DetectOuvragesEdgeExtraction_elem_list = findAllElement(xmldoc, 'Task80_TDC_DetectOuvragesEdgeExtraction','Tasks/Task80_TDC_DetectOuvragesEdgeExtraction_List')
    for pos in range (len(task80_TDC_DetectOuvragesEdgeExtraction_elem_list)):
        task80_TDC_DetectOuvragesEdgeExtraction_elem = task80_TDC_DetectOuvragesEdgeExtraction_elem_list[pos]
        settings_struct.tasks.task80_TDC_DetectOuvragesEdgeExtraction.append(StructTask80_TDC_DetectOuvragesEdgeExtraction())
        settings_struct.tasks.task80_TDC_DetectOuvragesEdgeExtraction[pos].inputFile = getValueNodeDataDom(task80_TDC_DetectOuvragesEdgeExtraction_elem, 'InputFile')
        settings_struct.tasks.task80_TDC_DetectOuvragesEdgeExtraction[pos].sourceIndexImageThresholdsList = getListNodeDataDom(task80_TDC_DetectOuvragesEdgeExtraction_elem, 'SourceIndexImageThresholdsList', 'IndexImageThreshold')
        settings_struct.tasks.task80_TDC_DetectOuvragesEdgeExtraction[pos].outputPath = getValueNodeDataDom(task80_TDC_DetectOuvragesEdgeExtraction_elem, 'OutputPath')
        settings_struct.tasks.task80_TDC_DetectOuvragesEdgeExtraction[pos].inputCutVector = getValueNodeDataDom(task80_TDC_DetectOuvragesEdgeExtraction_elem, 'InputCutVector')
        settings_struct.tasks.task80_TDC_DetectOuvragesEdgeExtraction[pos].calcIndexImage = getValueNodeDataDom(task80_TDC_DetectOuvragesEdgeExtraction_elem, 'CalcIndexImage')

    # Task90_TDC_DistanceTDCPointLine
    task90_TDC_DistanceTDCPointLine_elem_list = findAllElement(xmldoc, 'Task90_TDC_DistanceTDCPointLine','Tasks/Task90_TDC_DistanceTDCPointLine_List')
    for pos in range (len(task90_TDC_DistanceTDCPointLine_elem_list)):
        task90_TDC_DistanceTDCPointLine_elem = task90_TDC_DistanceTDCPointLine_elem_list[pos]
        settings_struct.tasks.task90_TDC_DistanceTDCPointLine.append(StructTask90_TDC_DistanceTDCPointLine())
        settings_struct.tasks.task90_TDC_DistanceTDCPointLine[pos].inputPointsFile = getValueNodeDataDom(task90_TDC_DistanceTDCPointLine_elem, 'InputPointsFile')
        settings_struct.tasks.task90_TDC_DistanceTDCPointLine[pos].inputTDCFile = getValueNodeDataDom(task90_TDC_DistanceTDCPointLine_elem, 'InputTDCFile')
        settings_struct.tasks.task90_TDC_DistanceTDCPointLine[pos].outputPath = getValueNodeDataDom(task90_TDC_DistanceTDCPointLine_elem, 'OutputPath')
        settings_struct.tasks.task90_TDC_DistanceTDCPointLine[pos].inputSeaPointsFile = getValueNodeDataDom(task90_TDC_DistanceTDCPointLine_elem, 'InputSeaPointsFile')
        settings_struct.tasks.task90_TDC_DistanceTDCPointLine[pos].evolColumnName = getValueNodeDataDom(task90_TDC_DistanceTDCPointLine_elem, 'EvolColumnName')

    # Task100_TDC_DistanceTDCBuffers
    task100_TDC_DistanceTDCBuffers_elem_list = findAllElement(xmldoc, 'Task100_TDC_DistanceTDCBuffers','Tasks/Task100_TDC_DistanceTDCBuffers_List')
    for pos in range (len(task100_TDC_DistanceTDCBuffers_elem_list)):
        task100_TDC_DistanceTDCBuffers_elem = task100_TDC_DistanceTDCBuffers_elem_list[pos]
        settings_struct.tasks.task100_TDC_DistanceTDCBuffers.append(StructTask100_TDC_DistanceTDCBuffers())
        settings_struct.tasks.task100_TDC_DistanceTDCBuffers[pos].inputReferenceFile = getValueNodeDataDom(task100_TDC_DistanceTDCBuffers_elem, 'InputReferenceFile')
        settings_struct.tasks.task100_TDC_DistanceTDCBuffers[pos].inputCalculatedFile = getValueNodeDataDom(task100_TDC_DistanceTDCBuffers_elem, 'InputCalculatedFile')
        settings_struct.tasks.task100_TDC_DistanceTDCBuffers[pos].inputSeaPointsFile = getValueNodeDataDom(task100_TDC_DistanceTDCBuffers_elem, 'InputSeaPointsFile')
        settings_struct.tasks.task100_TDC_DistanceTDCBuffers[pos].outputPath = getValueNodeDataDom(task100_TDC_DistanceTDCBuffers_elem, 'OutputPath')
        settings_struct.tasks.task100_TDC_DistanceTDCBuffers[pos].bufferSize = getValueNodeDataDom(task100_TDC_DistanceTDCBuffers_elem, 'BufferSize')
        settings_struct.tasks.task100_TDC_DistanceTDCBuffers[pos].buffersNumber = getValueNodeDataDom(task100_TDC_DistanceTDCBuffers_elem, 'BuffersNumber')

    # Task110_TDC_PostTreatmentTDC
    task110_TDC_PostTreatmentTDC_elem_list = findAllElement(xmldoc, 'Task110_TDC_PostTreatmentTDC','Tasks/Task110_TDC_PostTreatmentTDC_List')
    for pos in range (len(task110_TDC_PostTreatmentTDC_elem_list)):
        task110_TDC_PostTreatmentTDC_elem = task110_TDC_PostTreatmentTDC_elem_list[pos]
        settings_struct.tasks.task110_TDC_PostTreatmentTDC.append(StructTask110_TDC_PostTreatmentTDC())
        settings_struct.tasks.task110_TDC_PostTreatmentTDC[pos].inputVectorsList = getListNodeDataDom(task110_TDC_PostTreatmentTDC_elem, 'InputVectorsList', 'InputVector')
        settings_struct.tasks.task110_TDC_PostTreatmentTDC[pos].inputRockyVector = getValueNodeDataDom(task110_TDC_PostTreatmentTDC_elem, 'InputRockyVector')
        settings_struct.tasks.task110_TDC_PostTreatmentTDC[pos].outputVectorTdcAll = getValueNodeDataDom(task110_TDC_PostTreatmentTDC_elem, 'OutputVectorTdcAll')
        settings_struct.tasks.task110_TDC_PostTreatmentTDC[pos].outputVectorTdcWithoutRocky = getValueNodeDataDom(task110_TDC_PostTreatmentTDC_elem, 'OutputVectorTdcWithoutRocky')
        settings_struct.tasks.task110_TDC_PostTreatmentTDC[pos].generalize_method = getValueNodeDataDom(task110_TDC_PostTreatmentTDC_elem, 'Method', 'GrassGeneralize')
        value = getValueNodeDataDom(task110_TDC_PostTreatmentTDC_elem, 'Threshold', 'GrassGeneralize')
        if value != "" and value is not None:
            settings_struct.tasks.task110_TDC_PostTreatmentTDC[pos].generalize_threshold  = int(value)
        settings_struct.tasks.task110_TDC_PostTreatmentTDC[pos].fusionColumnName = getValueNodeDataDom(task110_TDC_PostTreatmentTDC_elem, 'FusionColumnName')

    # TaskUCZ_ClassificationUCZ
    taskUCZ_ClassificationUCZ_elem_list = findAllElement(xmldoc, 'TaskUCZ_ClassificationUCZ','Tasks/TaskUCZ_ClassificationUCZ_List')
    for pos in range (len(taskUCZ_ClassificationUCZ_elem_list)):
        taskUCZ_ClassificationUCZ_elem = taskUCZ_ClassificationUCZ_elem_list[pos]
        settings_struct.tasks.taskUCZ_ClassificationUCZ.append(StructTaskUCZ_ClassificationUCZ())
        settings_struct.tasks.taskUCZ_ClassificationUCZ[pos].inputVector = getValueNodeDataDom(taskUCZ_ClassificationUCZ_elem, 'InputVector')
        settings_struct.tasks.taskUCZ_ClassificationUCZ[pos].outputVector = getValueNodeDataDom(taskUCZ_ClassificationUCZ_elem, 'OutputVector')
        settings_struct.tasks.taskUCZ_ClassificationUCZ[pos].empriseVector = getValueNodeDataDom(taskUCZ_ClassificationUCZ_elem, 'EmpriseVector')
        settings_struct.tasks.taskUCZ_ClassificationUCZ[pos].binaryVegetationMask = getValueNodeDataDom(taskUCZ_ClassificationUCZ_elem, 'BinaryVegetationMask')
        settings_struct.tasks.taskUCZ_ClassificationUCZ[pos].satelliteImage = getValueNodeDataDom(taskUCZ_ClassificationUCZ_elem, 'SatelliteImage')
        settings_struct.tasks.taskUCZ_ClassificationUCZ[pos].digitalHeightModel = getValueNodeDataDom(taskUCZ_ClassificationUCZ_elem, 'DigitalHeightModel')
        settings_struct.tasks.taskUCZ_ClassificationUCZ[pos].builtsVectorList = getListNodeDataDom(taskUCZ_ClassificationUCZ_elem, 'BuiltsVectorList', 'BuiltsVector')
        settings_struct.tasks.taskUCZ_ClassificationUCZ[pos].hydrographyVector = getValueNodeDataDom(taskUCZ_ClassificationUCZ_elem, 'HydrographyVector')
        settings_struct.tasks.taskUCZ_ClassificationUCZ[pos].roadsVectorList = getListNodeDataDom(taskUCZ_ClassificationUCZ_elem, 'RoadsVectorList', 'RoadsVector')
        settings_struct.tasks.taskUCZ_ClassificationUCZ[pos].rpgVector = getValueNodeDataDom(taskUCZ_ClassificationUCZ_elem, 'RpgVector')
        settings_struct.tasks.taskUCZ_ClassificationUCZ[pos].indicatorsTreatmentChoice = getValueNodeDataDom(taskUCZ_ClassificationUCZ_elem, 'IndicatorsTreatmentChoice')
        settings_struct.tasks.taskUCZ_ClassificationUCZ[pos].uczTreatmentChoice = getValueNodeDataDom(taskUCZ_ClassificationUCZ_elem, 'UczTreatmentChoice')
        settings_struct.tasks.taskUCZ_ClassificationUCZ[pos].dbmsChoice = getValueNodeDataDom(taskUCZ_ClassificationUCZ_elem, 'DbmsChoice')
        value = getValueNodeDataDom(taskUCZ_ClassificationUCZ_elem, 'NdviThreshold')
        if value != "" and value is not None:
            settings_struct.tasks.taskUCZ_ClassificationUCZ[pos].ndviThreshold = float(value)
        value = getValueNodeDataDom(taskUCZ_ClassificationUCZ_elem, 'NdviWaterThreshold')
        if value != "" and value is not None:
            settings_struct.tasks.taskUCZ_ClassificationUCZ[pos].ndviWaterThreshold = float(value)
        value = getValueNodeDataDom(taskUCZ_ClassificationUCZ_elem, 'Ndwi2Threshold')
        if value != "" and value is not None:
            settings_struct.tasks.taskUCZ_ClassificationUCZ[pos].ndwi2Threshold = float(value)
        value = getValueNodeDataDom(taskUCZ_ClassificationUCZ_elem, 'BiLowerThreshold')
        if value != "" and value is not None:
            settings_struct.tasks.taskUCZ_ClassificationUCZ[pos].biLowerThreshold = float(value)
        value = getValueNodeDataDom(taskUCZ_ClassificationUCZ_elem, 'BiUpperThreshold')
        if value != "" and value is not None:
            settings_struct.tasks.taskUCZ_ClassificationUCZ[pos].biUpperThreshold = float(value)

    # Task00_LCZ_DataPreparation
    task00_LCZ_DataPreparation_elem_list = findAllElement(xmldoc, 'Task00_LCZ_DataPreparation','Tasks/Task00_LCZ_DataPreparation_List')
    for pos in range (len(task00_LCZ_DataPreparation_elem_list)):
        task00_LCZ_DataPreparation_elem = task00_LCZ_DataPreparation_elem_list[pos]
        settings_struct.tasks.task00_LCZ_DataPreparation.append(StructTask00_LCZ_DataPreparation())
        settings_struct.tasks.task00_LCZ_DataPreparation[pos].empriseFile = getValueNodeDataDom(task00_LCZ_DataPreparation_elem, 'EmpriseFile')
        settings_struct.tasks.task00_LCZ_DataPreparation[pos].gridInput = getValueNodeDataDom(task00_LCZ_DataPreparation_elem, 'GridInput')
        settings_struct.tasks.task00_LCZ_DataPreparation[pos].builtInputList = getListNodeDataDom(task00_LCZ_DataPreparation_elem, 'BuiltInputList', 'BuiltInput')
        settings_struct.tasks.task00_LCZ_DataPreparation[pos].roadsInputList = getListNodeDataDom(task00_LCZ_DataPreparation_elem, 'RoadsInputList', 'RoadsInput')
        settings_struct.tasks.task00_LCZ_DataPreparation[pos].classifInput = getValueNodeDataDom(task00_LCZ_DataPreparation_elem, 'ClassifInput')
        settings_struct.tasks.task00_LCZ_DataPreparation[pos].mnsInput = getValueNodeDataDom(task00_LCZ_DataPreparation_elem, 'MnsInput')
        settings_struct.tasks.task00_LCZ_DataPreparation[pos].mnhInput = getValueNodeDataDom(task00_LCZ_DataPreparation_elem, 'MnhInput')
        settings_struct.tasks.task00_LCZ_DataPreparation[pos].gridOutput = getValueNodeDataDom(task00_LCZ_DataPreparation_elem, 'GridOutput')
        settings_struct.tasks.task00_LCZ_DataPreparation[pos].gridOutputCleaned = getValueNodeDataDom(task00_LCZ_DataPreparation_elem, 'GridOutputCleaned')
        settings_struct.tasks.task00_LCZ_DataPreparation[pos].builtOutput = getValueNodeDataDom(task00_LCZ_DataPreparation_elem, 'BuiltOutput')
        settings_struct.tasks.task00_LCZ_DataPreparation[pos].roadsOutput = getValueNodeDataDom(task00_LCZ_DataPreparation_elem, 'RoadsOutput')
        settings_struct.tasks.task00_LCZ_DataPreparation[pos].classifOutput = getValueNodeDataDom(task00_LCZ_DataPreparation_elem, 'ClassifOutput')
        settings_struct.tasks.task00_LCZ_DataPreparation[pos].mnsOutput = getValueNodeDataDom(task00_LCZ_DataPreparation_elem, 'MnsOutput')
        settings_struct.tasks.task00_LCZ_DataPreparation[pos].mnhOutput = getValueNodeDataDom(task00_LCZ_DataPreparation_elem, 'MnhOutput')
        settings_struct.tasks.task00_LCZ_DataPreparation[pos].colCodeUA = getValueNodeDataDom(task00_LCZ_DataPreparation_elem, 'ColCodeUA')
        settings_struct.tasks.task00_LCZ_DataPreparation[pos].colItemUA = getValueNodeDataDom(task00_LCZ_DataPreparation_elem, 'ColItemUA')

    # Task10_LCZ_BuildingSurfaceFraction
    task10_LCZ_BuildingSurfaceFraction_elem_list = findAllElement(xmldoc, 'Task10_LCZ_BuildingSurfaceFraction','Tasks/Task10_LCZ_BuildingSurfaceFraction_List')
    for pos in range (len(task10_LCZ_BuildingSurfaceFraction_elem_list)):
        task10_LCZ_BuildingSurfaceFraction_elem = task10_LCZ_BuildingSurfaceFraction_elem_list[pos]
        settings_struct.tasks.task10_LCZ_BuildingSurfaceFraction.append(StructTask10_LCZ_BuildingSurfaceFraction())
        settings_struct.tasks.task10_LCZ_BuildingSurfaceFraction[pos].inputGridFile = getValueNodeDataDom(task10_LCZ_BuildingSurfaceFraction_elem, 'InputGridFile')
        settings_struct.tasks.task10_LCZ_BuildingSurfaceFraction[pos].outputGridFile = getValueNodeDataDom(task10_LCZ_BuildingSurfaceFraction_elem, 'OutputGridFile')
        settings_struct.tasks.task10_LCZ_BuildingSurfaceFraction[pos].inputClassifFile = getValueNodeDataDom(task10_LCZ_BuildingSurfaceFraction_elem, 'InputClassifFile')

    # Task20_LCZ_ImperviousSurfaceFraction
    task20_LCZ_ImperviousSurfaceFraction_elem_list = findAllElement(xmldoc, 'Task20_LCZ_ImperviousSurfaceFraction','Tasks/Task20_LCZ_ImperviousSurfaceFraction_List')
    for pos in range (len(task20_LCZ_ImperviousSurfaceFraction_elem_list)):
        task20_LCZ_ImperviousSurfaceFraction_elem = task20_LCZ_ImperviousSurfaceFraction_elem_list[pos]
        settings_struct.tasks.task20_LCZ_ImperviousSurfaceFraction.append(StructTask20_LCZ_ImperviousSurfaceFraction())
        settings_struct.tasks.task20_LCZ_ImperviousSurfaceFraction[pos].inputGridFile = getValueNodeDataDom(task20_LCZ_ImperviousSurfaceFraction_elem, 'InputGridFile')
        settings_struct.tasks.task20_LCZ_ImperviousSurfaceFraction[pos].outputGridFile = getValueNodeDataDom(task20_LCZ_ImperviousSurfaceFraction_elem, 'OutputGridFile')
        settings_struct.tasks.task20_LCZ_ImperviousSurfaceFraction[pos].inputClassifFile = getValueNodeDataDom(task20_LCZ_ImperviousSurfaceFraction_elem, 'InputClassifFile')
        settings_struct.tasks.task20_LCZ_ImperviousSurfaceFraction[pos].imperviousClassLabelList = getListNodeDataDom(task20_LCZ_ImperviousSurfaceFraction_elem, 'ImperviousClassLabelList', 'ClassLabel')

    # Task30_LCZ_PerviousSurfaceFraction
    task30_LCZ_PerviousSurfaceFraction_elem_list = findAllElement(xmldoc, 'Task30_LCZ_PerviousSurfaceFraction','Tasks/Task30_LCZ_PerviousSurfaceFraction_List')
    for pos in range (len(task30_LCZ_PerviousSurfaceFraction_elem_list)):
        task30_LCZ_PerviousSurfaceFraction_elem = task30_LCZ_PerviousSurfaceFraction_elem_list[pos]
        settings_struct.tasks.task30_LCZ_PerviousSurfaceFraction.append(StructTask30_LCZ_PerviousSurfaceFraction())
        settings_struct.tasks.task30_LCZ_PerviousSurfaceFraction[pos].inputGridFile = getValueNodeDataDom(task30_LCZ_PerviousSurfaceFraction_elem, 'InputGridFile')
        settings_struct.tasks.task30_LCZ_PerviousSurfaceFraction[pos].outputGridFile = getValueNodeDataDom(task30_LCZ_PerviousSurfaceFraction_elem, 'OutputGridFile')
        settings_struct.tasks.task30_LCZ_PerviousSurfaceFraction[pos].inputClassifFile = getValueNodeDataDom(task30_LCZ_PerviousSurfaceFraction_elem, 'InputClassifFile')
        settings_struct.tasks.task30_LCZ_PerviousSurfaceFraction[pos].perviousClassLabelList = getListNodeDataDom(task30_LCZ_PerviousSurfaceFraction_elem, 'PerviousClassLabelList', 'ClassLabel')

    # Task40_LCZ_SkyViewFactor
    task40_LCZ_SkyViewFactor_elem_list = findAllElement(xmldoc, 'Task40_LCZ_SkyViewFactor','Tasks/Task40_LCZ_SkyViewFactor_List')
    for pos in range (len(task40_LCZ_SkyViewFactor_elem_list)):
        task40_LCZ_SkyViewFactor_elem = task40_LCZ_SkyViewFactor_elem_list[pos]
        settings_struct.tasks.task40_LCZ_SkyViewFactor.append(StructTask40_LCZ_SkyViewFactor())
        settings_struct.tasks.task40_LCZ_SkyViewFactor[pos].inputGridFile = getValueNodeDataDom(task40_LCZ_SkyViewFactor_elem, 'InputGridFile')
        settings_struct.tasks.task40_LCZ_SkyViewFactor[pos].outputGridFile = getValueNodeDataDom(task40_LCZ_SkyViewFactor_elem, 'OutputGridFile')
        settings_struct.tasks.task40_LCZ_SkyViewFactor[pos].inputMnsFile = getValueNodeDataDom(task40_LCZ_SkyViewFactor_elem, 'InputMnsFile')
        settings_struct.tasks.task40_LCZ_SkyViewFactor[pos].inputClassifFile = getValueNodeDataDom(task40_LCZ_SkyViewFactor_elem, 'InputClassifFile')
        value = getValueNodeDataDom(task40_LCZ_SkyViewFactor_elem, 'DimGridX')
        if value != "" and value is not None:
            settings_struct.tasks.task40_LCZ_SkyViewFactor[pos].dimGridX = int(value)
        value = getValueNodeDataDom(task40_LCZ_SkyViewFactor_elem, 'DimGridY')
        if value != "" and value is not None:
            settings_struct.tasks.task40_LCZ_SkyViewFactor[pos].dimGridY = int(value)
        value = getValueNodeDataDom(task40_LCZ_SkyViewFactor_elem, 'Radius')
        if value != "" and value is not None:
            settings_struct.tasks.task40_LCZ_SkyViewFactor[pos].radius = float(value)
        value = getValueNodeDataDom(task40_LCZ_SkyViewFactor_elem, 'Method')
        if value != "" and value is not None:
            settings_struct.tasks.task40_LCZ_SkyViewFactor[pos].method = int(value)
        value = getValueNodeDataDom(task40_LCZ_SkyViewFactor_elem, 'Dlevel')
        if value != "" and value is not None:
            settings_struct.tasks.task40_LCZ_SkyViewFactor[pos].dlevel = float(value)
        value = getValueNodeDataDom(task40_LCZ_SkyViewFactor_elem, 'Ndirs')
        if value != "" and value is not None:
            settings_struct.tasks.task40_LCZ_SkyViewFactor[pos].ndirs = int(value)

    # Task50_LCZ_HeightOfRoughnessElements
    task50_LCZ_HeightOfRoughnessElements_elem_list = findAllElement(xmldoc, 'Task50_LCZ_HeightOfRoughnessElements','Tasks/Task50_LCZ_HeightOfRoughnessElements_List')
    for pos in range (len(task50_LCZ_HeightOfRoughnessElements_elem_list)):
        task50_LCZ_HeightOfRoughnessElements_elem = task50_LCZ_HeightOfRoughnessElements_elem_list[pos]
        settings_struct.tasks.task50_LCZ_HeightOfRoughnessElements.append(StructTask50_LCZ_HeightOfRoughnessElements())
        settings_struct.tasks.task50_LCZ_HeightOfRoughnessElements[pos].inputGridFile = getValueNodeDataDom(task50_LCZ_HeightOfRoughnessElements_elem, 'InputGridFile')
        settings_struct.tasks.task50_LCZ_HeightOfRoughnessElements[pos].outputGridFile = getValueNodeDataDom(task50_LCZ_HeightOfRoughnessElements_elem, 'OutputGridFile')
        settings_struct.tasks.task50_LCZ_HeightOfRoughnessElements[pos].inputBuiltFile = getValueNodeDataDom(task50_LCZ_HeightOfRoughnessElements_elem, 'InputBuiltFile')

    # Task55_LCZ_RoughnessByOcsAndMnh
    task55_LCZ_RoughnessByOcsAndMnh_elem_list = findAllElement(xmldoc, 'Task55_LCZ_RoughnessByOcsAndMnh','Tasks/Task55_LCZ_RoughnessByOcsAndMnh_List')
    for pos in range (len(task55_LCZ_RoughnessByOcsAndMnh_elem_list)):
        task55_LCZ_RoughnessByOcsAndMnh_elem = task55_LCZ_RoughnessByOcsAndMnh_elem_list[pos]
        settings_struct.tasks.task55_LCZ_RoughnessByOcsAndMnh.append(StructTask55_LCZ_RoughnessByOcsAndMnh())
        settings_struct.tasks.task55_LCZ_RoughnessByOcsAndMnh[pos].inputClassifFile = getValueNodeDataDom(task55_LCZ_RoughnessByOcsAndMnh_elem, 'InputClassifFile')
        settings_struct.tasks.task55_LCZ_RoughnessByOcsAndMnh[pos].inputMnhFile = getValueNodeDataDom(task55_LCZ_RoughnessByOcsAndMnh_elem, 'InputMnhFile')
        settings_struct.tasks.task55_LCZ_RoughnessByOcsAndMnh[pos].inputGridVector = getValueNodeDataDom(task55_LCZ_RoughnessByOcsAndMnh_elem, 'InputGridVector')
        settings_struct.tasks.task55_LCZ_RoughnessByOcsAndMnh[pos].outputGridVector = getValueNodeDataDom(task55_LCZ_RoughnessByOcsAndMnh_elem, 'OutputGridVector')

    # Task60_LCZ_TerrainRoughnessClass
    task60_LCZ_TerrainRoughnessClass_elem_list = findAllElement(xmldoc, 'Task60_LCZ_TerrainRoughnessClass','Tasks/Task60_LCZ_TerrainRoughnessClass_List')
    for pos in range (len(task60_LCZ_TerrainRoughnessClass_elem_list)):
        task60_LCZ_TerrainRoughnessClass_elem = task60_LCZ_TerrainRoughnessClass_elem_list[pos]
        settings_struct.tasks.task60_LCZ_TerrainRoughnessClass.append(StructTask60_LCZ_TerrainRoughnessClass())
        settings_struct.tasks.task60_LCZ_TerrainRoughnessClass[pos].inputGridFile = getValueNodeDataDom(task60_LCZ_TerrainRoughnessClass_elem, 'InputGridFile')
        settings_struct.tasks.task60_LCZ_TerrainRoughnessClass[pos].outputGridFile = getValueNodeDataDom(task60_LCZ_TerrainRoughnessClass_elem, 'OutputGridFile')
        settings_struct.tasks.task60_LCZ_TerrainRoughnessClass[pos].inputBuiltFile = getValueNodeDataDom(task60_LCZ_TerrainRoughnessClass_elem, 'InputBuiltFile')
        value = getValueNodeDataDom(task60_LCZ_TerrainRoughnessClass_elem, 'DistanceLines')
        if value != "" and value is not None:
            settings_struct.tasks.task60_LCZ_TerrainRoughnessClass[pos].distanceLines = int(value)

    # Task70_LCZ_AspectRatio
    task70_LCZ_AspectRatio_elem_list = findAllElement(xmldoc, 'Task70_LCZ_AspectRatio','Tasks/Task70_LCZ_AspectRatio_List')
    for pos in range (len(task70_LCZ_AspectRatio_elem_list)):
        task70_LCZ_AspectRatio_elem = task70_LCZ_AspectRatio_elem_list[pos]
        settings_struct.tasks.task70_LCZ_AspectRatio.append(StructTask70_LCZ_AspectRatio())
        settings_struct.tasks.task70_LCZ_AspectRatio[pos].inputGridFile = getValueNodeDataDom(task70_LCZ_AspectRatio_elem, 'InputGridFile')
        settings_struct.tasks.task70_LCZ_AspectRatio[pos].outputGridFile = getValueNodeDataDom(task70_LCZ_AspectRatio_elem, 'OutputGridFile')
        settings_struct.tasks.task70_LCZ_AspectRatio[pos].inputRoadsFile = getValueNodeDataDom(task70_LCZ_AspectRatio_elem, 'InputRoadsFile')
        settings_struct.tasks.task70_LCZ_AspectRatio[pos].inputBuiltFile = getValueNodeDataDom(task70_LCZ_AspectRatio_elem, 'InputBuiltFile')
        value = getValueNodeDataDom(task70_LCZ_AspectRatio_elem, 'SegDist')
        if value != "" and value is not None:
            settings_struct.tasks.task70_LCZ_AspectRatio[pos].segDist = int(value)
        value = getValueNodeDataDom(task70_LCZ_AspectRatio_elem, 'SegLength')
        if value != "" and value is not None:
            settings_struct.tasks.task70_LCZ_AspectRatio[pos].segLength = int(value)
        value = getValueNodeDataDom(task70_LCZ_AspectRatio_elem, 'BufferSize')
        if value != "" and value is not None:
            settings_struct.tasks.task70_LCZ_AspectRatio[pos].bufferSize = int(value)

    # Task80_LCZ_OcsIndicators
    task80_LCZ_OcsIndicators_elem_list = findAllElement(xmldoc, 'Task80_LCZ_OcsIndicators','Tasks/Task80_LCZ_OcsIndicators_List')
    for pos in range (len(task80_LCZ_OcsIndicators_elem_list)):
        task80_LCZ_OcsIndicators_elem = task80_LCZ_OcsIndicators_elem_list[pos]
        settings_struct.tasks.task80_LCZ_OcsIndicators.append(StructTask80_LCZ_OcsIndicators())
        settings_struct.tasks.task80_LCZ_OcsIndicators[pos].inputClassifFile = getValueNodeDataDom(task80_LCZ_OcsIndicators_elem, 'InputClassifFile')
        settings_struct.tasks.task80_LCZ_OcsIndicators[pos].inputMnhFile = getValueNodeDataDom(task80_LCZ_OcsIndicators_elem, 'InputMnhFile')
        settings_struct.tasks.task80_LCZ_OcsIndicators[pos].inputGridVector = getValueNodeDataDom(task80_LCZ_OcsIndicators_elem, 'InputGridVector')
        settings_struct.tasks.task80_LCZ_OcsIndicators[pos].outputGridVector = getValueNodeDataDom(task80_LCZ_OcsIndicators_elem, 'OutputGridVector')

    # Task90_LCZ_ClassificationLCZ
    task90_LCZ_ClassificationLCZ_elem_list = findAllElement(xmldoc, 'Task90_LCZ_ClassificationLCZ','Tasks/Task90_LCZ_ClassificationLCZ_List')
    for pos in range (len(task90_LCZ_ClassificationLCZ_elem_list)):
        task90_LCZ_ClassificationLCZ_elem = task90_LCZ_ClassificationLCZ_elem_list[pos]
        settings_struct.tasks.task90_LCZ_ClassificationLCZ.append(StructTask90_LCZ_ClassificationLCZ())
        settings_struct.tasks.task90_LCZ_ClassificationLCZ[pos].inputPythonFile = getValueNodeDataDom(task90_LCZ_ClassificationLCZ_elem, 'InputPythonFile')
        settings_struct.tasks.task90_LCZ_ClassificationLCZ[pos].inputFile = getValueNodeDataDom(task90_LCZ_ClassificationLCZ_elem, 'InputFile')
        settings_struct.tasks.task90_LCZ_ClassificationLCZ[pos].outputFile = getValueNodeDataDom(task90_LCZ_ClassificationLCZ_elem, 'OutputFile')
        settings_struct.tasks.task90_LCZ_ClassificationLCZ[pos].variablesValuesTreeList = []
        variables_list = getListValueAttributeDom(task90_LCZ_ClassificationLCZ_elem, 'VariablesValuesTreeList', 'VariableValue', 'name')
        values_list = getListNodeDataDom(task90_LCZ_ClassificationLCZ_elem, 'VariablesValuesTreeList', 'VariableValue')
        for index in range(len(variables_list)) :
            variable_value_struct = StructClassificationLCZ_VariablesValuesTree()
            variable_value_struct.variable = variables_list[index]
            value = values_list[index]
            if value != "" and value is not None:
                variable_value_struct.value = float(value)
            settings_struct.tasks.task90_LCZ_ClassificationLCZ[pos].variablesValuesTreeList.append(variable_value_struct)
        settings_struct.tasks.task90_LCZ_ClassificationLCZ[pos].useClassifRf = getValueNodeDataDom(task90_LCZ_ClassificationLCZ_elem, 'UseClassifRf').lower() == 'true'
        value = getValueNodeDataDom(task90_LCZ_ClassificationLCZ_elem, 'NbSampleRf')
        if value != "" and value is not None:
            settings_struct.tasks.task90_LCZ_ClassificationLCZ[pos].nbSampleRf = int(value)
        settings_struct.tasks.task90_LCZ_ClassificationLCZ[pos].modelRfFile = getValueNodeDataDom(task90_LCZ_ClassificationLCZ_elem, 'ModelRfFile')
        settings_struct.tasks.task90_LCZ_ClassificationLCZ[pos].columnNameId = getValueNodeDataDom(task90_LCZ_ClassificationLCZ_elem, 'ColumnNameId')
        settings_struct.tasks.task90_LCZ_ClassificationLCZ[pos].columnNameUaCode = getValueNodeDataDom(task90_LCZ_ClassificationLCZ_elem, 'ColumnNameUaCode')
        settings_struct.tasks.task90_LCZ_ClassificationLCZ[pos].columnNameLczHisto = getValueNodeDataDom(task90_LCZ_ClassificationLCZ_elem, 'ColumnNameLczHisto')
        settings_struct.tasks.task90_LCZ_ClassificationLCZ[pos].columnNameLcz = getValueNodeDataDom(task90_LCZ_ClassificationLCZ_elem, 'ColumnNameLcz')
        settings_struct.tasks.task90_LCZ_ClassificationLCZ[pos].columnNameLczRf = getValueNodeDataDom(task90_LCZ_ClassificationLCZ_elem, 'ColumnNameLczRf')
        settings_struct.tasks.task90_LCZ_ClassificationLCZ[pos].indiceFilesList = []
        indice_files_list = getListNodeDataDom(task90_LCZ_ClassificationLCZ_elem, 'IndiceFilesList', 'IndiceFile')
        indicator_list = getListValueAttributeDom(task90_LCZ_ClassificationLCZ_elem, 'IndiceFilesList', 'IndiceFile', 'indicator')
        columnSrc_list = getListValueAttributeDom(task90_LCZ_ClassificationLCZ_elem, 'IndiceFilesList', 'IndiceFile', 'columnSrc')
        abbreviation_list = getListValueAttributeDom(task90_LCZ_ClassificationLCZ_elem, 'IndiceFilesList', 'IndiceFile', 'abbreviation')
        for index in range(len(indice_files_list)) :
            indice_file_struct = StructClassificationLCZ_IndiceFile()
            indice_file_struct.indiceFile = indice_files_list[index]
            indice_file_struct.indicator = indicator_list[index]
            indice_file_struct.columnSrc = columnSrc_list[index]
            indice_file_struct.abbreviation = abbreviation_list[index]
            settings_struct.tasks.task90_LCZ_ClassificationLCZ[pos].indiceFilesList.append(indice_file_struct)

    # Task10_RSQ_WaterHeight
    task10_RSQ_WaterHeight_elem_list = findAllElement(xmldoc, 'Task10_RSQ_WaterHeight', 'Tasks/Task10_RSQ_WaterHeight_List')
    for pos in range(len(task10_RSQ_WaterHeight_elem_list)):
        task10_RSQ_WaterHeight_elem = task10_RSQ_WaterHeight_elem_list[pos]
        settings_struct.tasks.task10_RSQ_WaterHeight.append(StructTask10_RSQ_WaterHeight())
        settings_struct.tasks.task10_RSQ_WaterHeight[pos].inputFloodedAreasVector = getValueNodeDataDom(task10_RSQ_WaterHeight_elem, 'InputFloodedAreasVector')
        settings_struct.tasks.task10_RSQ_WaterHeight[pos].inputDigitalElevationModelFile = getValueNodeDataDom(task10_RSQ_WaterHeight_elem, 'InputDigitalElevationModelFile')
        settings_struct.tasks.task10_RSQ_WaterHeight[pos].outputHeightsClassesFile = getValueNodeDataDom(task10_RSQ_WaterHeight_elem, 'OutputHeightsClassesFile')
        settings_struct.tasks.task10_RSQ_WaterHeight[pos].outputHeightsClassesVector = getValueNodeDataDom(task10_RSQ_WaterHeight_elem, 'OutputHeightsClassesVector')
        settings_struct.tasks.task10_RSQ_WaterHeight[pos].heightsClasses = getValueNodeDataDom(task10_RSQ_WaterHeight_elem, 'HeightsClasses')

        value = getValueNodeDataDom(task10_RSQ_WaterHeight_elem, 'EnvironmentVariable', 'Grass')
        if value != "" and value is not None:
            settings_struct.tasks.task10_RSQ_WaterHeight[pos].grass_environmentVariable = os.environ[value]
        settings_struct.tasks.task10_RSQ_WaterHeight[pos].grass_databaseName = getValueNodeDataDom(task10_RSQ_WaterHeight_elem, 'DatabaseName', 'Grass')
        settings_struct.tasks.task10_RSQ_WaterHeight[pos].grass_location = getValueNodeDataDom(task10_RSQ_WaterHeight_elem, 'Location', 'Grass')
        settings_struct.tasks.task10_RSQ_WaterHeight[pos].grass_mapset = getValueNodeDataDom(task10_RSQ_WaterHeight_elem, 'Mapset', 'Grass')

    # Task20_RSQ_AreasUnderUrbanization
    task20_RSQ_AreasUnderUrbanization_elem_list = findAllElement(xmldoc, 'Task20_RSQ_AreasUnderUrbanization', 'Tasks/Task20_RSQ_AreasUnderUrbanization_List')
    for pos in range(len(task20_RSQ_AreasUnderUrbanization_elem_list)):
        task20_RSQ_AreasUnderUrbanization_elem = task20_RSQ_AreasUnderUrbanization_elem_list[pos]
        settings_struct.tasks.task20_RSQ_AreasUnderUrbanization.append(StructTask20_RSQ_AreasUnderUrbanization())
        settings_struct.tasks.task20_RSQ_AreasUnderUrbanization[pos].inputPlotVector = getValueNodeDataDom(task20_RSQ_AreasUnderUrbanization_elem, 'InputPlotVector')
        settings_struct.tasks.task20_RSQ_AreasUnderUrbanization[pos].outputPlotVector = getValueNodeDataDom(task20_RSQ_AreasUnderUrbanization_elem, 'OutputPlotVector')
        settings_struct.tasks.task20_RSQ_AreasUnderUrbanization[pos].footprintVector = getValueNodeDataDom(task20_RSQ_AreasUnderUrbanization_elem, 'FootprintVector')
        settings_struct.tasks.task20_RSQ_AreasUnderUrbanization[pos].inputBuiltFile = getValueNodeDataDom(task20_RSQ_AreasUnderUrbanization_elem, 'InputBuiltFile')
        settings_struct.tasks.task20_RSQ_AreasUnderUrbanization[pos].inputBuiltVectorsList = getListNodeDataDom(task20_RSQ_AreasUnderUrbanization_elem, 'InputBuiltVectorsList', 'InputBuiltVector')
        settings_struct.tasks.task20_RSQ_AreasUnderUrbanization[pos].inputPluVector = getValueNodeDataDom(task20_RSQ_AreasUnderUrbanization_elem, 'InputPluVector')
        settings_struct.tasks.task20_RSQ_AreasUnderUrbanization[pos].inputPprVector = getValueNodeDataDom(task20_RSQ_AreasUnderUrbanization_elem, 'InputPprVector')
        settings_struct.tasks.task20_RSQ_AreasUnderUrbanization[pos].minBuiltSizesList = getListNodeDataDom(task20_RSQ_AreasUnderUrbanization_elem, 'MinBuiltSizesList', 'MinBuiltSize')
        settings_struct.tasks.task20_RSQ_AreasUnderUrbanization[pos].pluField = getValueNodeDataDom(task20_RSQ_AreasUnderUrbanization_elem, 'PluField')
        settings_struct.tasks.task20_RSQ_AreasUnderUrbanization[pos].pluUValuesList = getListNodeDataDom(task20_RSQ_AreasUnderUrbanization_elem, 'PluUValuesList', 'PluUValue')
        settings_struct.tasks.task20_RSQ_AreasUnderUrbanization[pos].pluAuValuesList = getListNodeDataDom(task20_RSQ_AreasUnderUrbanization_elem, 'PluAuValuesList', 'PluAuValue')
        settings_struct.tasks.task20_RSQ_AreasUnderUrbanization[pos].pprField = getValueNodeDataDom(task20_RSQ_AreasUnderUrbanization_elem, 'PprField')
        settings_struct.tasks.task20_RSQ_AreasUnderUrbanization[pos].pprRedValuesList = getListNodeDataDom(task20_RSQ_AreasUnderUrbanization_elem, 'PprRedValuesList', 'PprRedValue')
        settings_struct.tasks.task20_RSQ_AreasUnderUrbanization[pos].pprBlueValuesList = getListNodeDataDom(task20_RSQ_AreasUnderUrbanization_elem, 'PprBlueValuesList', 'PprBlueValue')

    # Task30_RSQ_EvolutionOverTime
    task30_RSQ_EvolutionOverTime_elem_list = findAllElement(xmldoc, 'Task30_RSQ_EvolutionOverTime', 'Tasks/Task30_RSQ_EvolutionOverTime_List')
    for pos in range(len(task30_RSQ_EvolutionOverTime_elem_list)):
        task30_RSQ_EvolutionOverTime_elem = task30_RSQ_EvolutionOverTime_elem_list[pos]
        settings_struct.tasks.task30_RSQ_EvolutionOverTime.append(StructTask30_RSQ_EvolutionOverTime())
        settings_struct.tasks.task30_RSQ_EvolutionOverTime[pos].inputPlotVector = getValueNodeDataDom(task30_RSQ_EvolutionOverTime_elem, 'InputPlotVector')
        settings_struct.tasks.task30_RSQ_EvolutionOverTime[pos].outputPlotVector = getValueNodeDataDom(task30_RSQ_EvolutionOverTime_elem, 'OutputPlotVector')
        settings_struct.tasks.task30_RSQ_EvolutionOverTime[pos].footprintVector = getValueNodeDataDom(task30_RSQ_EvolutionOverTime_elem, 'FootprintVector')
        settings_struct.tasks.task30_RSQ_EvolutionOverTime[pos].inputT0File = getValueNodeDataDom(task30_RSQ_EvolutionOverTime_elem, 'InputT0File')
        settings_struct.tasks.task30_RSQ_EvolutionOverTime[pos].inputTxFilesList = getListNodeDataDom(task30_RSQ_EvolutionOverTime_elem, 'InputTxFilesList', 'InputTxFile')
        settings_struct.tasks.task30_RSQ_EvolutionOverTime[pos].evolutionsList = getListNodeDataDom(task30_RSQ_EvolutionOverTime_elem, 'EvolutionsList', 'Evolution')

    # Retour de la structure remplie
    return settings_struct

