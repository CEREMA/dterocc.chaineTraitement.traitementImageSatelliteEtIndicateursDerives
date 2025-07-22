
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT QUI INFORME AU SERVEUR LA FIN DE LA COMMANDE PAR COMMUNICATION SOCKET                                                              #
#                                                                                                                                           #
#############################################################################################################################################
"""
 Ce module contient le script qui informe au serveur la fin de la commande par communication socket pour le séquenceur.
"""

import os,argparse,socket

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 2 : affichage maximum de commentaires lors de l'execution du script. Intermédiaire : affichage intermédiaire
debug = 0
TAG_STATE_END = "Termine"
TAG_STATE_ERROR = "En_Erreur"
INFO_WARNING = "warning"
INFO_DEPRECATED = "deprecated"
INFO_FALSE_ERROR = "Error MachineLearningModel Factory did not return an MachineLearningModel"
INFO_PROJ_CREATE_ERROR = "proj_create_from_database"
bold = "\033[1m"
green = "\033[32m"
cyan = "\033[36m"
endC = "\033[0m"

# ================================================
if __name__ == '__main__':
    # Définition des différents paramètres du parser
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,  prog="ReplyEndCommand", description="\
    Info : Send by socket communication the end execution command. \n\
    Objectif : répondre au serveur que la tache dont le numéro est passé en argument est terminée. \n\
    Example : python ReplyEndCommand.py 12")
    parser.add_argument("-ip_serveur",'--ip_serveur',type=str, help="Ip serveur.", required=True)
    parser.add_argument("-port",'--port',type=int, help="Number of port serveur listen socket.", required=True)
    parser.add_argument("-id_command",'--id_command',type=int, help="Id command to report end command", required=True)
    parser.add_argument('-nem','--error_management',action='store_false',default=True,help="Option error management need. By default : True", required=False)
    parser.add_argument("-err",'--file_error',type=str, help="File error return of stderr.", required=True)
    args = parser.parse_args()

    # RECUPERATION DES ARGUMENTS
    # Parametre ip du serveur
    if args.ip_serveur != None:
        ip_serveur = args.ip_serveur

    # Parametre numero du port de la socket
    if args.port != None:
        port = args.port

    # Parametre id de commande
    if args.id_command != None:
        id_command = args.id_command

    # Parametre gestion des erreurs
    if args.error_management != None:
        error_management = args.error_management

    # Parametre fichier erreur
    if args.file_error != None:
        file_error = args.file_error

    # Affichage des arguments récupérés
    if debug >= 3:
        print(bold + green + "Variables dans le parser" + endC)
        print(cyan + "ReplyEndCommand : " + endC + "ip_serveur : " + str(ip_serveur) + endC)
        print(cyan + "ReplyEndCommand : " + endC + "port : " + str(port) + endC)
        print(cyan + "ReplyEndCommand : " + endC + "id_command : " + str(id_command) + endC)
        print(cyan + "ReplyEndCommand : " + endC + "file_error : " + str(file_error) + endC)

    # Par defaut l'etat de retour est terminé Ok
    state = TAG_STATE_END

    # Test si le fichier d'erreur contient quelque chose
    try:
        f = open(file_error, 'r')
        lines_list = f.readlines()
        f.close()
        if lines_list != [] :
            for line in lines_list:
                if line != "\n" and not INFO_WARNING in line.lower() and not INFO_DEPRECATED in line.lower() and not INFO_PROJ_CREATE_ERROR in line.lower() and not INFO_FALSE_ERROR in line and error_management:
                    state = TAG_STATE_ERROR
    except:
        state = TAG_STATE_ERROR

    # Netoyage du fichier d'erreur si execution ok
    if state == TAG_STATE_END:
        os.remove(file_error)

    # Send socket

    socket_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # connection en mode TCP
    socket_client.connect((ip_serveur, port))
    socket_client.send((state + "="+ str(id_command)).encode())
    '''
    socket_client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # en UDP
    socket_client.sendto(state + "="+ str(id_command),(ip_serveur, port))
    '''
    socket_client.close()
    if debug >= 3:
        print(cyan + "ReplyEndCommand : " + endC + "Close socket")


