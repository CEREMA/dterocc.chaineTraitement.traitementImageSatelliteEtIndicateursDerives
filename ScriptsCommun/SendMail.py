#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
##############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT ENVOI DE MAIL                                                                                                                      #
#                                                                                                                                           #
#############################################################################################################################################

"""
Nom de l'objet : SendMail.py
Description :
-------------
Objectif : Exécuter l'envoi d'un message par mail

Date de creation : 29/09/2016
----------
Histoire :
----------
Origine : Nouveau
29/09/2016 : Création
-----------------------------------------------------------------------------------------------------
Modifications :

------------------------------------------------------
A Reflechir/A faire :

"""

# IMPORT DES BIBLIOTHEQUES, VARIABLES ET FONCTIONS UTILES
from __future__ import print_function
import os,sys,glob,argparse,smtplib,string
import six
if six.PY2:
    from email.MIMEMultipart import MIMEMultipart
    from email.MIMEText import MIMEText
else:
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_log import timeLine

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 3


###########################################################################################################################################
# FONCTION sendMail()                                                                                                                     #
###########################################################################################################################################
def sendMail(address_mail_sender, address_mail_receiver, server_mail, port_server, password_mail_sender, subject_of_message, message_to_send, path_time_log, save_results_intermediate=False, overwrite=True):
    """
    # ROLE:
    #     Envoyer un message par e-mail
    #
    # ENTREES DE LA FONCTION :
    #     address_mail_sender : l'adresse mail d'envoi
    #     address_mail_receiver : l'adresse mail du receveur
    #     server_mail : l'adresse du seveur SNMP
    #     port_server : numero de port du serveur
    #     password_mail_sender : le mot de passe de connexion
    #     subject_of_message : le sujet du message
    #     message_to_send : le message à envoyer
    #     path_time_log : le fichier de log de sortie
    #     save_results_intermediate : fichiers de sorties intermediaires nettoyees, par defaut = False
    #     overwrite : écrase si un fichier existant a le même nom qu'un fichier de sortie, par defaut a True
    #
    # SORTIES DE LA FONCTION :
    #     N.A
    #
    """

    # Mise à jour du Log
    starting_event = "sendMail() : Send mail starting : "
    timeLine(path_time_log,starting_event)

    if debug >= 2:
        print(endC)
        print(bold + green + "## START : SEND MAIL" + endC)
        print(endC)

    if debug >= 3:
        print(bold + green + "sendMail() : Variables dans la fonction" + endC)
        print(cyan + "sendMail() : " + endC + "address_mail_sender : " + str(address_mail_sender) + endC)
        print(cyan + "sendMail() : " + endC + "address_mail_receiver : " + str(address_mail_receiver) + endC)
        print(cyan + "sendMail() : " + endC + "server_mail : " + str(server_mail) + endC)
        print(cyan + "sendMail() : " + endC + "port_server : " + str(port_server) + endC)
        print(cyan + "sendMail() : " + endC + "password_mail_sender : " + str(password_mail_sender) + endC)
        print(cyan + "sendMail() : " + endC + "subject_of_message : " + str(subject_of_message) + endC)
        print(cyan + "sendMail() : " + endC + "message_to_send : " + str(message_to_send) + endC)
        print(cyan + "sendMail() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "sendMail() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "sendMail() : " + endC + "overwrite : " + str(overwrite) + endC)

    # Preparation connexion

    msg = MIMEMultipart()
    msg['From'] = address_mail_sender
    msg['To'] = address_mail_receiver
    msg['Subject'] = subject_of_message
    msg.attach(MIMEText(message_to_send))

    # Envoi message
    mailserver = smtplib.SMTP(server_mail, port_server)
    mailserver.ehlo()
    mailserver.starttls()
    mailserver.ehlo()
    if password_mail_sender != "":
        mailserver.login(address_mail_sender, password_mail_sender)
    mailserver.sendmail(address_mail_sender, address_mail_receiver, msg.as_string())
    mailserver.quit()

    if debug >= 2:
        print(endC)
        print(bold + green + "## END : SEND MAIL" + endC)
        print(endC)

    # Mise à jour du Log
    ending_event = "sendMail() : Send mail ending : "
    timeLine(path_time_log,ending_event)

    return

###########################################################################################################################################
# MISE EN PLACE DU PARSER                                                                                                                 #
###########################################################################################################################################

# Code executé seulement dans le cas ou le script est lancé depuis une ligne de commande
# Il n'est pas executé lors d'un import SendMail.py
# Exemple de lancement en ligne de commande:
# python SendMail.py -adrs gilles.fouvet@cerema.fr -adrr gilles.fouvet@cerema.fr -serv smtp.m2.e2.rie.gouv.fr -port 25 -pass xxxxxx -subj sujet_du_message -msg Conenu_du_message
def main(gui=False):

    # Définition des différents paramètres du parser
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,  prog="SendMail", description="\
    Info : Send a message by mail since address sender to address receiver. \n\
    Objectif : Envoyer un message par e mail. \n\
    Example : python SendMail.py -adrs gilles.fouvet@cerema.fr \n\
                                 -adrr gilles.fouvet@cerema.fr \n\
                                 -serv smtp.m2.e2.rie.gouv.fr \n\
                                 -port 25 \n\
                                 -pass xxxxx \n\
                                 -subj sujet_du_message \n\
                                 -msg Conenu_du_message \n\
                                 -log /mnt/hgfs/Data_Image_Saturn/fichierTestLog.txt")

    parser.add_argument('-adrs','--address_mail_sender',default="",help="Address mail of the sender", type=str, required=True)
    parser.add_argument('-adrr','--address_mail_receiver',default="",help="Address mail of the receiver", type=str, required=True)
    parser.add_argument('-serv','--server_mail',default="",help="Address url of the server SNMP ex: smtp.gmail.com", type=str, required=True)
    parser.add_argument('-port','--port_server',default=0,help="Number of port of server mail. By default : '0'", type=int, required=True)
    parser.add_argument('-pass','--password_mail_sender',default="",help="Password mail of the sender", type=str, required=False)
    parser.add_argument('-subj','--subject_of_message',default="",help="The subject of message", type=str, required=True)
    parser.add_argument('-msg','--message_to_send',default="",help="The message to send", type=str, required=True)
    parser.add_argument('-log','--path_time_log',default="",help="Name of log", type=str, required=False)
    parser.add_argument('-sav','--save_results_inter',action='store_true',default=False, help="Save or delete intermediate result after the process. By default, False", required=False)
    parser.add_argument('-now','--overwrite',action='store_false',default=True, help="Overwrite files with same names. By default, True", required=False)
    parser.add_argument('-debug','--debug',default=3,help="Option : Value of level debug trace, default : 3 ", type=int, required=False)
    args = displayIHM(gui, parser)

    # RECUPERATION DES ARGUMENTS

    # Récupération de l'adresse mail d'envoi
    if args.address_mail_sender != None:
        address_mail_sender = args.address_mail_sender

    # Récupération de l'adresse mail du receveur
    if args.address_mail_receiver != None :
        address_mail_receiver = args.address_mail_receiver

    # Récupération de l'adresse du sever SNMP
    if args.server_mail!= None:
        server_mail = args.server_mail

    # Récupération du port du sever SNMP
    if args.port_server!= None:
        port_server = args.port_server

    # Récupération du mot de passe de connexion
    if args.password_mail_sender!= None:
        password_mail_sender = args.password_mail_sender

    # Récupération du sujet du message
    if args.message_to_send!= None:
        message_to_send = args.message_to_send

    # Récupération du message à envoyer
    if args.subject_of_message!= None:
        subject_of_message = args.subject_of_message

    # Récupération du nom du fichier log
    if args.path_time_log!= None:
        path_time_log = args.path_time_log

    # Récupération de l'option écrasement
    if args.save_results_inter != None:
        save_results_intermediate = args.save_results_inter

    if args.overwrite!= None:
        overwrite = args.overwrite

    # Récupération de l'option niveau de debug
    if args.debug!= None:
        global debug
        debug = args.debug

    if debug >= 3:
        print(bold + green + "SendMail : Variables dans le parser" + endC)
        print(cyan + "SendMail : " + endC + "address_mail_sender : " + str(address_mail_sender) + endC)
        print(cyan + "SendMail : " + endC + "address_mail_receiver : " + str(address_mail_receiver) + endC)
        print(cyan + "SendMail : " + endC + "server_mail : " + str(server_mail) + endC)
        print(cyan + "SendMail : " + endC + "port_server : " + str(port_server) + endC)
        print(cyan + "SendMail : " + endC + "password_mail_sender : " + str(password_mail_sender) + endC)
        print(cyan + "SendMail : " + endC + "message_to_send : " + str(message_to_send) + endC)
        print(cyan + "SendMail : " + endC + "subject_of_message : " + str(subject_of_message) + endC)
        print(cyan + "SendMail : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "SendMail : " + endC + "save_results_inter : " + str(save_results_intermediate) + endC)
        print(cyan + "SendMail : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "SendMail : " + endC + "debug : " + str(debug) + endC)

    # EXECUTION DE LA FONCTION

    # execution de la fonction
    sendMail(address_mail_sender, address_mail_receiver, server_mail, port_server, password_mail_sender, subject_of_message, message_to_send, path_time_log, save_results_intermediate, overwrite)

# ================================================

if __name__ == '__main__':
  main(gui=False)
