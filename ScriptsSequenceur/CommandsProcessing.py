# -*- coding: utf-8 -*-
#!/usr/bin/python

#############################################################################################################################################
# Copyright (©) CEREMA/DTerSO/DALETT/SCGSI  All rights reserved.                                                                            #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# FONCTIONS QUI EXECTUTE DES COMMANDES A PARTIR D'UN FICHIER DE COMMANDES                                                                   #
#                                                                                                                                           #
#############################################################################################################################################

# IMPORTS UTILES
from __future__ import print_function
import os, sys, stat, time, threading, socket, subprocess, psutil
import six
from pexpect import pxssh
from Lib_operator import ping, getLocalIp, switch, case
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC
from Lib_text import writeTextFile,appendTextFileCR, cleanSpaceText
from Settings import *

lock_commands_file = False

#############################################################################################
# FONCTION executeCommands()                                                                #
#############################################################################################
# ROLE :
#   La fonction lit des commandes dans un fichier texte et execute ces commandes en local-direct ou en local-background ou en distant-background
#
# ENTREES :
#   command_doc : fichier dont on lit et execute les commandes
#   debug : niveau de trace log
#   link : le lien etenet utilisé
#   port : le port utiliser pour le serveur gestion des commandes
#
# SORTIES :
#   N.A.

def executeCommands(command_doc, debug, link, port):

    # Variable de lock (semaphore) d'acces sur le fichier de commande : command_doc
    global lock_commands_file
    lock_commands_file = False
    SERV_PROC_NAME = "TaskSequencer"

    print(endC)
    print(bold + green + "####################################################################" + endC)
    print(bold + green + "# DEBUT DE L'EXECUTION DES COMMANDES                               #" + endC)
    print(bold + green + "####################################################################" + endC)
    print(endC)

    # Nettoyage du process si le sequenceur c'est arreter sur un crach
    #~ for proc in psutil.process_iter():
        #~ if SERV_PROC_NAME in proc.name():
            #~ proc.kill()

    # exist_command identifie s'il reste des commandes à effectuer
    exist_command = True

    # Identification de l'IP du PC
    #computer_name  = socket.gethostname()
    #computer_ip = socket.gethostbyname(computer_name)
    computer_ip = getLocalIp(IP_VERSION, link)

    # Prepation d'un nom de base de fichier shell pour l'execution
    base_name_shell_command = os.path.splitext(command_doc)[0]

    # Lancer le thead d'ecoute du retour fin de la commande
    thread = threading.Thread(target=listenReturnCommand, args=(port, command_doc))
    thread.start()

    # Boucler tanqu'il a des commandes a traiter
    while exist_command:
        exist_command = False   # On met exist_command à False. Si exist_command ne repasse pas à True, la boucle d'exécution des commandes va s'arreter

        # Attente du semaphore
        getSemaphoreLockCommands()
        try:
            # Ouverture du fichier de commande et chargement de toutes les lignes
            command_doc_work = open(command_doc,'r+')
        except:
            raise NameError(cyan + "exectuteCommands : " + endC + bold + red + "Can't open file: \"" + command_doc + '\n' + endC)

        # Identification de commands_list comme une liste dont chaque ligne correspond à une commande
        commands_list = command_doc_work.readlines()

        if debug >= 4:
            print(cyan + "exectuteCommands : " + endC + "commands_list : " + str (commands_list) + endC)

        for l in range(len(commands_list)):  # Parcours des différentes lignes de commande
            if debug >= 4:
                print(cyan + "exectuteCommands : " + endC + "l (numero de la ligne de commande) : " + str (l) + endC)

            # Identification de la premiere commande à faire (non vide et commencant par "A Faire : "
            # Mise à jour de exist_command (Il reste une commande à faire, la boucle ne s'arrète pas)
            execute_command = False
            action = ''
            if commands_list[l] != "\n" :
                # gestion des parametres du fichier de commande
                element_command_list = commands_list[l].split(SEPARATOR)
                state = element_command_list[0]
                action = element_command_list[4]
                id_command = element_command_list[1]

                # Gestion du computeur sur lequel sera executé la commande
                error_management = element_command_list[5].lower() == 'true'
                computer_execution = element_command_list[6]
                if computer_execution == '':
                    computer_execution = computer_ip
                login =  element_command_list[7]
                password =  element_command_list[8]

                # Liste des commandes dependantes
                dependency_list = []
                if element_command_list[2] != '':
                    dependency_list = element_command_list[2].split(',')

                # Récupération de la commande à exécuter
                command_to_execute = element_command_list[11]

                if state == TAG_STATE_MAKE or state == TAG_STATE_WAIT:
                    exist_command = True
                    execute_command = True
                    shell_command = ''
                    error_file = ''

                    # Gestion des dependences
                    if  dependency_list != [] :

                        # On test si toutes les commandes dont dépende la commande a traiter, sont à l'état terminé
                        command_depend_on_error = False
                        for id_command_depend in dependency_list:
                            for c in range(len(commands_list)):
                                if commands_list[c] != "\n" :
                                    element_command_c_list = commands_list[c].split(SEPARATOR)
                                    id_command_c = element_command_c_list[1]
                                    state_c = element_command_c_list[0]
                                    if id_command_depend == id_command_c :
                                        if state_c != TAG_STATE_END:
                                            execute_command = False
                                            if state_c == TAG_STATE_ERROR or state_c == TAG_STATE_LOCK :
                                                command_depend_on_error = True
                                                exist_command = False
                                        break
                            # Optimisation temps pour sortie plus vite de la boucle liste des commandes dependantes
                            if not execute_command:
                                break

                        # Si la commande est en attente d'autre commande ou dependant de commande en erreur alors mettre a jour l'etat de la commande
                        if not execute_command:
                            if command_depend_on_error :
                                new_state = TAG_STATE_LOCK
                            else :
                                new_state = TAG_STATE_WAIT

                            # Mise a jour de l'etat de la commande
                            commands_list[l] = new_state + SEPARATOR + str(id_command) + SEPARATOR + element_command_list[2] + SEPARATOR + element_command_list[3] + SEPARATOR + action + SEPARATOR + element_command_list[5] + SEPARATOR + computer_execution + SEPARATOR + login + SEPARATOR + password + SEPARATOR + SEPARATOR + SEPARATOR + command_to_execute

                            if debug >= 4:
                                print("\n" + cyan + "exectuteCommands : " + blue + "commande en attente : " + endC + str (commands_list[l]))

                            # Mise a jour du fichier de commandes
                            command_doc_work.seek(0)                     # On se place a partir du debut du document
                            command_doc_work.truncate()                  # Redimensionne la taille du fichier à vide
                            command_doc_work.writelines(commands_list)   # Réécriture du fichier de commande avec la ligne modifiée
                            command_doc_work.flush()                     # Force l'ecriture sur le fichier

            # Execution d'une nouvelle commande
            if execute_command :

                if debug >= 1:
                    print(cyan + "exectuteCommands : " + endC + "command_to_execute : " + str (command_to_execute) + endC)

                # Ajout d'infos dans la ligne : ordinateur, date...
                commands_list[l] = TAG_STATE_RUN + SEPARATOR + str(id_command) + SEPARATOR + element_command_list[2] + SEPARATOR + element_command_list[3] + SEPARATOR + action + SEPARATOR + element_command_list[5] + SEPARATOR + computer_execution + SEPARATOR + login + SEPARATOR + password + SEPARATOR + time.strftime('%d/%m/%y %H:%M:%S',time.localtime()) +  SEPARATOR + SEPARATOR + command_to_execute
                if debug >= 3:
                    print(cyan + "exectuteCommands : " + endC + "Nouvelle commande : " + str (commands_list[l]))

                # Mise a jour du fichier de commandes
                command_doc_work.seek(0)                     # On se place a partir du debut du document
                command_doc_work.truncate()                  # Redimensionne la taille du fichier à vide
                command_doc_work.writelines(commands_list)   # Réécriture du fichier de commande avec la ligne modifiée
                command_doc_work.flush()                     # Force l'ecriture sur le fichier

                # Execution de la commande
                print(cyan + "exectuteCommands : " + endC + bold + green + "EXECUTION DE LA COMMANDE : " + str (command_to_execute) + endC)
                new_state = executeCommand(computer_ip, port, id_command, command_to_execute, action, error_management, base_name_shell_command, computer_execution, login, password)
                if new_state != '':
                    commands_list = updateEndCommand(commands_list, int(id_command), new_state, debug)
                    # Mise a jour du fichier de commandes
                    # On se place à partir du debut du document
                    command_doc_work.seek(0)
                    # Redimensionne la taille du fichier à vide
                    command_doc_work.truncate()
                    # Réécriture du fichier de commande avec la ligne modifiée
                    command_doc_work.writelines(commands_list)
                    # Force l'ecriture sur le fichier
                    command_doc_work.flush()

                # Arret de la boucle sur les lignes pour reprendre la lecture des commandes depuis le début (d'autres scripts peuvent l'avoir modifié)
                break

        # Boucle while

        # Fermeture du fichier de commandes
        command_doc_work.close()                     # Force l'ecriture sur le fichier et fermeture de command_doc_work
        command_doc_work = None
        lock_commands_file = False                   # Libere le semaphore sur le fichier

        # Attente 1s fermeture du fichier et evite de boucler trop rapidement (attente fin execution de la commande)
        time.sleep(1)

        # Test si toutes les commandes sont terminés
        retContinu = testEndAllCommands(commands_list)
        if not retContinu :
            # Send socket End all commends to stop serveur
            stopServer(computer_ip, port)

    # Fin du thead serveur
    thread.join()

    print(bold + green + "# TOUTES LES COMMANDES ONT ETE TRAITEES" + endC)
    print(endC)
    print(bold + green + "#########################################################################" + endC)
    print(bold + green + "# FIN DE L'EXECUTION DE LA CHAINE                                       #" + endC)
    print(bold + green + "#########################################################################" + endC)
    print(endC)

    return


#############################################################################################
# FONCTION executeCommand()                                                                 #
#############################################################################################
# ROLE :
#   La fonction lance l'execution d'une commande
#
# ENTREES :
#   ip_serveur : adresse ip du serveur
#   port : numero de port d'écoute du serveur
#   id_command : l'identifiant de la commande
#   command_to_execute : la commande de la chage à exécuter
#   type_execution : le type d'execution de la commande
#   error_management : gestion des erreurs
#   base_name_shell_command : path ou l'on va creer les fichiers .sh et .err
#   ip_remote : en mode d'execution remote, contien l'ip de la machine  sur lequel sera executer la commande
#   login  : mode de passe pour le mode d'execution remote
#   password : mode de passe pour le mode d'execution remote
#
# SORTIES :
#   new_state : info sur l'etat de l'execution (correcte ou en erreur)

def executeCommand(ip_serveur, port, id_command, command_to_execute, type_execution, error_management, base_name_shell_command, ip_remote="", login="", password=""):

    EXT_SHELL = '.sh'
    EXT_ERR = '.err'
    EXT_LOG = '.log'
    new_state = ''

    # Preparation du fichier d'execution en background-local ou background-remote
    if type_execution == TAG_ACTION_TO_MAKE_BG or type_execution == TAG_ACTION_TO_MAKE_RE :

        # Pour les executions a faire en background ou en remote preparation des fichiers .sh et .err
        shell_command = base_name_shell_command + str(id_command) + EXT_SHELL
        error_file = base_name_shell_command + str(id_command) + EXT_ERR
        log_file = base_name_shell_command + str(id_command) + EXT_LOG

        # Creation du fichier shell
        error_management_option = ""
        if not error_management :
            error_management_option = " -nem "
        command_to_execute = command_to_execute.replace('\n','')
        if six.PY2:
            cmd_tmp = command_to_execute + " 1> " + log_file.encode("utf-8") + " 2> " + error_file.encode("utf-8") + "\n"
        else :
            cmd_tmp = command_to_execute + " 1> " + log_file + " 2> " + error_file + "\n"
        writeTextFile(shell_command,cmd_tmp)
        appendTextFileCR(shell_command, FUNCTION_PYTHON + "ReplyEndCommand -ip_serveur " + str(ip_serveur) + " -port " +  str(port) + " -id_command " +  str(id_command) + error_management_option + " -err " + error_file)
        appendTextFileCR(shell_command,"rm " + shell_command)
        os.chmod(shell_command, stat.S_IRWXU)

    # Selon le type d'execution
    while switch(type_execution):

        if case(TAG_ACTION_TO_MAKE_NOW):

            # Execution en direct (local)
            exitCode = subprocess.call(command_to_execute, shell=True)
            new_state = TAG_STATE_END
            if exitCode != 0: # Si la commande command_to_execute a eu un probleme
                new_state = TAG_STATE_ERROR
                print(cyan + "executeCommand : " + endC +  bold + red + "ERREUR EXECUTION DE LA COMMANDE : " + str (command_to_execute) + endC, file=sys.stderr)
            break

        if case(TAG_ACTION_TO_MAKE_BG):

            # Execution en back ground (local)
            process = subprocess.Popen(shell_command, shell=True, stderr=subprocess.STDOUT)
            time.sleep(0.1)
            if process == None :
                new_state = TAG_STATE_ERROR
                print(cyan + "executeCommand : " + endC +  bold + red + "ERREUR EXECUTION DE LA COMMANDE EN BACKGROUND : " + str (command_to_execute) + endC, file=sys.stderr)
            else :
                print(cyan + "executeCommand : " + endC + " background pid = " + str(process.pid))
            break

        if case(TAG_ACTION_TO_MAKE_RE):

            # Test si la machine Remote est accesible
            if ping(ip_remote) :

                # Execution en remote execution
                try:
                    s = pxssh.pxssh()
                    s.login(ip_remote, login, password)
                    time.sleep(0.5)
                    s.sendline(shell_command+'&')
                    time.sleep(0.01)
                    s.logout()
                except pxssh.ExceptionPxssh as e:
                    new_state = TAG_STATE_ERROR
                    print(cyan + "executeCommand : " + endC +  bold + red +  "ERREUR EXECUTION DE LA COMMANDE EN REMOTE (login failed) : " + str (command_to_execute) + endC, file=sys.stderr)
                    print(e, file=sys.stderr)

            else :
                new_state = TAG_STATE_ERROR
                print(cyan + "executeCommand : " + endC +  bold + red +  "ERREUR EXECUTION DE LA COMMANDE EN REMOTE (Computeur : " + ip_remote + " non disponible) : " + str (command_to_execute) + endC, file=sys.stderr)
            break

        break # Sortie du while

    return new_state

#############################################################################################
# FONCTION listenReturnCommand()                                                            #
#############################################################################################
# ROLE :
#   La fonction gére la fin des commandes par écoute de socket
#
# ENTREES :
#   port : numero du port d'écoute du serveur
#   command_doc : fichier dont on lit et execute les commandes
#
# SORTIES :
#   N.A.
'''
def listenReturnCommand(port, command_doc):
    socket_serveur = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # connection en mode UDP
    socket_serveur.bind(('', port))
    print(cyan + "listenReturnCommand : " + endC + "Start serveur on port : " + str(port))
    runServeur = True
    while runServeur:
            data, addr = socket_serveur.recvfrom(255)
            if data == STOP_SERVEUR:
                runServeur = False
            else :
                info_list = data.split('=')
                id_command = int(info_list[1])
                new_state = info_list[0]
                runServeur = managementEndCommand(command_doc, id_command, new_state, 0)

    print(cyan + "listenReturnCommand : " + endC +"End serveur close connection socket")
    socket_serveur.close()
    return

'''
def listenReturnCommand(port, command_doc):

    socket_serveur = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # connection en mode TCP
    socket_serveur.bind(('', port))
    print(cyan + "listenReturnCommand : " + endC + "Start serveur on port : " +str(port))
    runServeur = True
    while runServeur:

            socket_serveur.listen(100)
            socket_client, addr = socket_serveur.accept()
            data = socket_client.recv(255)
            if six.PY3:
                data = str(data, 'utf-8')

            if data == STOP_SERVEUR or data == '':
                runServeur = False
            else :
                # Recuperation de id de la chache et de son nouvel etat
                info_list = data.split('=')
                id_command = int(info_list[1])
                new_state = info_list[0]

                runServeur = managementEndCommand(command_doc, id_command, new_state, 3)

    print(cyan + "listenReturnCommand : " + endC +"End serveur close connection socket")
    socket_client.close()
    socket_serveur.close()

    return

#############################################################################################
# FONCTION managementEndCommand()                                                           #
#############################################################################################
# ROLE :
#   La fonction gére le retour de commande terminer (ok ou en erreur)
#
# ENTREES :
#   command_doc : fichier dont on lit et execute les commandes
#   id_command : l'identifiant de la commande
#   new_state : nouvel etat de la commande
#   debug : niveau de trace log
#
# SORTIES :
#   Return "True" pour continuer ou "False" pour arreter le serveur

def managementEndCommand(command_doc, id_command, new_state, debug) :

    # Variable de lock (semaphore) d'acces sur le fichier de commande : command_doc
    global lock_commands_file

    if debug >= 3:
        print(cyan + "managementEndCommand : " + endC + bold + green + "FIN D EXECUTION DE LA COMMANDE id  : " + str (id_command) + endC)

    # Attente du semaphore
    getSemaphoreLockCommands()

    try:
        # Ouverture du fichier de commande et chargement de toutes les lignes
        command_doc_work = open(command_doc,'r+')
    except:
        raise NameError(cyan + "managementEndCommand : " + endC + bold + red + "Can't open file: \"" + command_doc + '\n' + endC)

    # Identification de commands_list comme une liste de textes, chaque ligne correspondant à un élément de la liste
    commands_list = command_doc_work.readlines()

    # Mise a jour de la commande
    commands_list = updateEndCommand(commands_list, id_command, new_state, debug)

    # On se place à partir du debut du document
    command_doc_work.seek(0)
    # Redimensionne la taille du fichier à vide
    command_doc_work.truncate()
    # Réécriture du fichier de commande avec la ligne modifiée
    command_doc_work.writelines(commands_list)
    # Force l'ecriture sur le fichier
    command_doc_work.flush()
    # Fermeture du fichier command_doc_work
    command_doc_work.close()
    command_doc_work = None
    # Libere le semaphore sur le fichier
    lock_commands_file = False

    # Test si toutes les commandes sont terminés
    retContinu = testEndAllCommands(commands_list)

    return retContinu

#############################################################################################
# FONCTION updateEndCommand()                                                           #
#############################################################################################
# ROLE :
#   La fonction gére le retour de commande terminer (ok ou en erreur)
#
# ENTREES :
#   commands_list : la liste des commandes
#   id_command : l'identifiant de la commande
#   new_state : nouvel etat de la commande
#   debug : niveau de trace log
#
# SORTIES :
#   Return commands_list modifié

def updateEndCommand(commands_list, id_command, new_state, debug) :

    if debug >= 3:
        print(cyan + "updateEndCommand : " + endC + bold + green + "FIN D EXECUTION DE LA COMMANDE id  : " + str (id_command) + endC)

    if debug >= 4:
        print(cyan + "updateEndCommand : " + endC + "commands_list : " + str (commands_list))

    # Mise à jour du fichier de commande
    for l in range(len(commands_list)):  # Parcours des différentes lignes de commande

        # Recherche de la commande dans le fichier
        if commands_list[l] != "\n" :
            element_command_list = commands_list[l].split(SEPARATOR)
            state = element_command_list[0]
            id_find = int(element_command_list[1])

            if id_find == id_command:

                # Mise à jour de la commande terminee
                commands_list[l] = new_state + SEPARATOR + str(id_command) + SEPARATOR + element_command_list[2] + SEPARATOR + element_command_list[3] + SEPARATOR + element_command_list[4] + SEPARATOR + element_command_list[5] + SEPARATOR + element_command_list[6] + SEPARATOR + element_command_list[7] + SEPARATOR + element_command_list[8] + SEPARATOR + element_command_list[9] +  SEPARATOR + time.strftime('%d/%m/%y %H:%M:%S',time.localtime()) + SEPARATOR + element_command_list[11]
                if debug >= 4:
                    print(cyan + "updateEndCommand : " + endC + "command completed : "  + str(commands_list[l]))

                # Arret de la boucle sur les lignes
                break

    return commands_list

#############################################################################################
# FONCTION testEndAllCommands()                                                             #
#############################################################################################
# ROLE :
#   La fonction permet de tester si toutes les commandes sont soient termininées normalement ou en erreur ou bloqué
#
# ENTREES :
#   commands_list : la liste des commandes
#
# SORTIES :
#   return True si ce n'est pas terminer False si toutes les commandes sont finies

def testEndAllCommands(commands_list):
    # Test si toutes les commandes sont terminés
    for l in range(len(commands_list)):  # Parcours des différentes lignes de commande
        if commands_list[l] != "\n":
            element_command_list = commands_list[l].split(SEPARATOR)
            state = element_command_list[0]
            if state != TAG_STATE_END and state != TAG_STATE_ERROR and state != TAG_STATE_LOCK:
                return True

    return False

#############################################################################################
# FONCTION stopServer()                                                                    #
#############################################################################################
# ROLE :
#   La fonction permet d'arreter le serveur lorsque toutes les commandes sont termininées
#
# ENTREES :
#   ip_serveur : adresse ip du serveur
#   port : numero du port utilisé
#
# SORTIES :
#   N.A.

def stopServer(ip_serveur, port):
    # Send socket End all commends to stop serveur

    socket_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # connection en mode TCP
    try:
        socket_client.connect((ip_serveur, port))
        socket_client.send(STOP_SERVEUR)
    except:
        pass
    '''
    socket_client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # en UDP
    socket_client.sendto(STOP_SERVEUR,(ip_serveur, port))
    '''
     # Fermeture de la socket
    socket_client.close()

    return

#############################################################################################
# FONCTION getSemaphoreLockCommands()                                                       #
#############################################################################################
# ROLE :
#   La fonction permet de recuperer le semaphore "lock_commands_file" pour securiser l'acces au fichier command_doc.txt
#   si il n'est pas disponible on reste en boucle d'attente de 0.1s jusqu'a ce qu'il soit disponible
#
# ENTREES :
#   N.A.
#
# SORTIES :
#   N.A.

def getSemaphoreLockCommands():
    # Variable de lock (semaphore) d'acces sur le fichier de commande : command_doc
    global lock_commands_file
    while lock_commands_file:
        time.sleep(0.1)

    lock_commands_file = True
    return
