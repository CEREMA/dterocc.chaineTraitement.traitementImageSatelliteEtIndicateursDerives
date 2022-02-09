# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerSO/DALETT/SCGSI  All rights reserved.                                                                            #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT GENERAL D'EXECUTION DE LA CHAINE                                                                                                   #
#                                                                                                                                           #
#############################################################################################################################################

'''
Nom de l'objet : TaskSequencer.py
Description :
    Objectif : Exécuter une chaine de traitement complète composée d'une liste de tache à éxécuter
               la configuration de la chaine est définie dans un fichier de settings (en .xml) à passer en paramètre

Date de creation : 08/08/2016
----------
Histoire :
----------
Origine : Nouveau
08/08/2016 : Création
-----------------------------------------------------------------------------------------------------
Modifications

------------------------------------------------------
A Reflechir/A faire
 -
 -
'''

# IMPORT DES BIBLIOTHEQUES, VARIABLES ET FONCTIONS UTILES

import os,glob,time,argparse,string,shutil
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_operator import terminateThread
from Lib_file import removeFile
from Lib_text import readTextFile, writeTextFile
from Settings import StructSettings, setEndDisplay
from ParserXml import xmlSettingsParser
from CommandsWriting  import writeCommands, updateCommandsError
from CommandsProcessing  import executeCommands
from SupervisionWorkflow  import supervisionCommands

# le compteur de commandes et selection du remote valeurs initiales
ID_COMMAND_INIT = 100
INDEX_REMOTE_IP = 0

#################################################################################
# FONCTION commandsWritingManagement()                                          #
#################################################################################
# ROLE :
#    Gestion de la mise en place des commandes
#
# ENTREES DE LA FONCTION :
#    name_setting : le nom du setting utilisé
#    settings_struct_dico : La structure dico contenant tout les settings
#    command_doc_pres : le nom du fichier de commande deja creer par un setting precedant
#    setting_file : nom du fichier contenant les settings
#    id_command : compteur de commande à éxecuter
#    correspondence_task_process_dico : table de correspondance entre le nom de la la tache et la liste d'id process correspondant
#
# SORTIES DE LA FONCTION :
#    command_doc : Nom du fichier contenant les commandes à éxécuter
#

def commandsWritingManagement (name_setting, settings_struct_dico, correspondence_task_process_dico, setting_file, id_command, command_doc_pres):
    print(bold + green + "####################################################################" + endC)
    print(bold + green + "# GESTION DE LA MISE EN PLACE DES COMMANDES                        #" + endC)
    print(bold + green + "####################################################################" + endC)
    print(endC)

    global index_remote_ip
    index_remote_ip = INDEX_REMOTE_IP

    command_doc = settings_struct_dico[name_setting].general.processing.commandFile
    debug = settings_struct_dico[name_setting].general.processing.debug

    # Si le fichier de commande ne doit pas être changé par rapport au fichier existant
    if not settings_struct_dico[name_setting].general.processing.newStudy:
        print(bold + green + "# LE FICHIER DE COMMANDE EST INCHANGE PAR RAPPORT AU FICHIER EXISTANT REPRISE APRES BUG : " + str(command_doc) + endC)

        # Modification du fichier command_doc les taches à l'état "En_Erreur" sont passées à l'état "A_Faire"
        if not os.path.isfile(command_doc):
            raise NameError(cyan + "commandsWritingManagement() : " + bold + red + "File command %s not yet exist.\n" %(command_doc) + endC)
        updateCommandsError(command_doc, debug)

    else: # Le fichier de commande actuel supprimé et remplacé par les valeurs du setting
        print(bold + green + "# DEBUT DE LA CONVERSION DES SETTINGS EN COMMANDES" + endC)

        # Si si le fichier command_doc est nouveau
        if command_doc != command_doc_pres and os.path.isfile(command_doc) :
            removeFile(command_doc) # Nettoyage du fichier de commande existant

        # Si l'on demande un fichier log
        if settings_struct_dico[name_setting].general.processing.logFile != "":
            # Nettoyage du logFile
            if os.path.isfile(settings_struct_dico[name_setting].general.processing.logFile):
                removeFile(settings_struct_dico[name_setting].general.processing.logFile)
            # Creation d'un nouveau logFile
            logFile = open(settings_struct_dico[name_setting].general.processing.logFile, 'a')
            logFile.close()
            # Donner tout les droits d'acces au fichier
            os.chmod(settings_struct_dico[name_setting].general.processing.logFile, 0o0777)

        if debug >= 1:
            task_list = []
            for task in settings_struct_dico[name_setting].general.processing.taskList:
                task_list.append(str(task.taskLabel) +  "." + str(task.position))
            print(cyan + "TaskSequencer : " + endC + " Liste des tâches : " + str(task_list) + endC)

        if debug >= 2:
            print(cyan + "TaskSequencer : " + endC + "command_doc : " + str (command_doc))
            print(cyan + "TaskSequencer : " + endC + "timelog : " + str (settings_struct_dico[name_setting].general.processing.logFile))

        # Parcours des tâches des settings pour les transformer en commandes dans le fichier command_doc
        for task in settings_struct_dico[name_setting].general.processing.taskList :
            if debug >=1:
                print(" ")
                print(cyan + "TaskSequencer : " + bold + green + "Début de la conversion en commande de la tache %s" %(str(task.taskLabel) +  "." + str(task.position)) + endC)

            # Ecriture dans command_doc de la commande correspondant à la tache task_label appliqué à l'ensemble des images de préparation
            id_command_temp, index_remote_ip_temp, task.taskIdTaskCommandsList = writeCommands(settings_struct_dico, id_command, index_remote_ip, task.taskLabel, task.position, task.dependencyTaskList, task.typeExecution, task.errorManagement, name_setting, debug)
            id_command = id_command_temp
            index_remote_ip = index_remote_ip_temp
            taskIdTaskCommandsList_str = ''
            for depend in task.taskIdTaskCommandsList :
                taskIdTaskCommandsList_str += str(depend) + ","
            if taskIdTaskCommandsList_str != '' :
                taskIdTaskCommandsList_str = taskIdTaskCommandsList_str[:-1]
            correspondence_task_process_dico["@" + name_setting + "." + str(task.taskLabel) + "." + str(task.position)]  = taskIdTaskCommandsList_str

        print(endC)
        print(cyan + "TaskSequencer : " + endC + bold + green + "Les commandes à effectuer sont visualisables ici : " + str (command_doc)  + endC)

    print(endC)
    print(bold + green + "####################################################################" + endC)
    print(bold + green + "# FIN DE LA CONVERSION DES SETTINGS EN COMMANDES                   #" + endC)
    print(bold + green + "####################################################################" + endC)
    print(endC)

    return command_doc, id_command

########################################################################################################################################################################
# EXECUTION DE LA CHAINE                                                                                                                                               #
########################################################################################################################################################################

# Code executé depuis une ligne de commande
# Exemple de lancement en ligne de commande:
# python TaskSequencer.py -i setting.xml

def main(gui=False):
    print(endC)
    print(bold + green + "#######################################################################################################" + endC)
    print(bold + green + "# DEBUT DE L'EXECUTION GENERALE DE LA CHAINE                                                          #" + endC)
    print(bold + green + "#######################################################################################################" + endC)
    print(endC)

    # Définition des différents paramètres du parser
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,  prog="TaskSequencer", description="\
    Info : Run a complete processing chain consting of a task list. \n\
    Objectif : exécuter une chaine de traitement complète composée d'une luste de tache. \n\
    Example : python TaskSequencer.py Settings.xml")
    parser.add_argument('setting_file',nargs="+",type=str, help="Settings file contain configuration of chain execution")
    args = displayIHM(gui, parser)

    # Récupération du fichier de setting d'entrée
    if args.setting_file != None:
        setting_file_list = args.setting_file

    print(bold + green + "TaskSequencer : Variables dans le parser" + endC)
    print(cyan + "TaskSequencer : " + endC + "setting_file_list : " + str(setting_file_list) + endC)

    # EXECUTION DE LA CHAINE
    command_doc = ''
    global id_command
    id_command = ID_COMMAND_INIT
    settings_struct_dico = {}
    correspondence_task_process_dico = {}
    for setting_file in setting_file_list:

        # nom du settting
        name_setting = os.path.splitext(os.path.basename(setting_file))[0]

        # Parser le fichier xml de settings
        settings_struct_dico[name_setting] = xmlSettingsParser(setting_file)

        # Ecriture des commandes
        command_doc,id_command = commandsWritingManagement(name_setting, settings_struct_dico, correspondence_task_process_dico, setting_file, id_command, command_doc)

    # Correction du fichier command_doc pour traiter les dépendances croisées nom encore traitées
    command_txt = readTextFile(command_doc)
    for correspondence_task in correspondence_task_process_dico :
        command_txt = command_txt.replace(correspondence_task, correspondence_task_process_dico[correspondence_task])
    writeTextFile(command_doc, command_txt)

    # Definition du niveau de debug pour toute la chaine
    debug = settings_struct_dico[list(settings_struct_dico)[0]].general.processing.debug

    # Lancement de la supervison du fichier commande
    setEndDisplay(False)
    threadSupervision = supervisionCommands(command_doc, debug)
    threadSupervision.start()

    # Execution des commandes
    link = settings_struct_dico[list(settings_struct_dico)[0]].general.processing.link
    port = settings_struct_dico[list(settings_struct_dico)[0]].general.processing.port
    if settings_struct_dico[list(settings_struct_dico)[0]].general.processing.running :
        executeCommands(command_doc, debug, link, port)
    else :
        time.sleep(5)

    # Arret de la supervision
    time.sleep(1)
    setEndDisplay(True)
    time.sleep(1)
    terminateThread(threadSupervision)

# ================================================

if __name__ == '__main__':
  main(gui=False)
