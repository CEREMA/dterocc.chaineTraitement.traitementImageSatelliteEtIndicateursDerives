#! /usr/bin/python
# -*- coding: utf-8 -*-

#############################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.               #
#############################################################################

#############################################################################
#                                                                           #
# FONCTIONS DE BASE GENERAL                                                 #
#                                                                           #
#############################################################################
"""
 Ce module défini des fonctions générales systèmes réseaux et langage.
"""

# IMPORTS DIVERS
import os, subprocess, platform, psutil, multiprocessing, threading ,ctypes, re, inspect
import six
if six.PY2:
    from urllib import urlopen

#########################################################################
# FONCTION ping()                                                       #
#########################################################################
def ping(hostname, timeout=1):
    """
    # ROLE :
    #   La fonction réalise un ping pour verifier si une machine est presente
    # ENTREES :
    #   hostname : adresse ip du calculateur à tester
    #   timeout : temps d'attente de réponse (en secondes)
    # SORTIES :
    #   Return "True" si le calculateur répond "False" sinon
    """

    if platform.system() == "Windows":
        command = "ping " + hostname + " -n 1 -w " + str(timeout*1000)
        command_param_list = ["ping", hostname, "-n", "1", "-w",  str(timeout*1000)]
    else:
        command = "ping -i " + str(timeout) + " -c 1 " + hostname
        command_param_list = ["ping", "-i", str(timeout), "-c", "1", hostname]

    proccess = subprocess.Popen(command_param_list,stdout = subprocess.PIPE)
    log_stdout = proccess.stdout.read()

    if "1 errors, 100% packet loss" in log_stdout :
        return False
    return True

#########################################################################
# FONCTION getPublicIp()                                                #
#########################################################################
if six.PY2:
  def getPublicIp():
    """
    # ROLE :
    #   La fonction retourne l'adresse IP de la machine vue de l'exterieur du site
    # ENTREES :
    # SORTIES :
    #   Return l'adresse IP
    """

    data = str(urlopen('http://checkip.dyndns.com/').read())
    return re.compile(r'Address: (\d+\.\d+\.\d+\.\d+)').search(data).group(1)

#########################################################################
# FONCTION getLocalIp()                                                 #
#########################################################################
def getLocalIp(version = 'IPv4', link = 'eth0'):
    """
    # ROLE :
    #   La fonction retourne l'adresse IP local de la machine pour windows
    # ENTREES :
    #   version : defini le type d'adresse IP ('IPv4' ou 'IPv6')
    #   link : defini le port ethernet ('eth0' ou 'eth1' ou 'lo' ou...)
    # SORTIES :
    #   Return l'adresse IP
    """

    if platform.system() == "Windows":
        my_ip = getWinIp(version)
    else:
        my_ip = getLinuxIp(version, link)

    return my_ip

#########################################################################
# FONCTION getWinIp()                                                   #
#########################################################################
def getWinIp(version = 'IPv4'):
    """
    # ROLE :
    #   La fonction retourne l'adresse IP local de la machine pour windows
    # ENTREES :
    #   version : defini le type d'adresse IP ('IPv4' ou 'IPv6')
    # SORTIES :
    #   Return l'adresse IP
    """

    if version not in ['IPv4', 'IPv6']:
        print('error - protocol version must be "IPv4" or "IPv6"')
        return None

    ipconfig = subprocess.check_output('ipconfig')
    if six.PY3:
        ipconfig = str(ipconfig, 'utf-8')
    my_ip = ""
    for line in ipconfig.split('\n'):
        if 'Address' in line and version in line:
            my_ip = line.split(' : ')[1].strip()
            break
    return my_ip

#########################################################################
# FONCTION getLinuxIp()                                                 #
#########################################################################
def getLinuxIp(version = 'IPv4', link = 'eth0'):
    """
    # ROLE :
    #   La fonction retourne l'adresse IP local de la machine pour linux
    # ENTREES :
    #   version : defini le type d'adresse IP ('IPv4' ou 'IPv6')
    #   link : defini le port ethernet ('eth0' ou 'eth1' ou 'lo' ou...)
    # SORTIES :
    #   Return l'adresse IP
    """

    if version not in ['IPv4', 'IPv6']:
        print('error - protocol version must be "IPv4" or "IPv6"')
        return None

    #ifconfig = subprocess.check_output('ifconfig')
    ifconfig = subprocess.check_output(['ip', 'addr'])

    if six.PY3:
        ifconfig = str(ifconfig, 'utf-8')

    my_ip = ""
    ipconfig_lines_list = ifconfig.split('\n')
    for idx_line in range(len(ipconfig_lines_list)):
        line = ipconfig_lines_list[idx_line]
        if link in line:
            if version == 'IPv4':
                #line_info = ipconfig_lines_list[idx_line + 1]
                line_info = ipconfig_lines_list[idx_line + 2]
                elem_list = line_info.split()
                for idx_elem in range(len(elem_list)):
                    if 'inet' in elem_list[idx_elem]:
                        if ":" in elem_list[idx_elem + 1] :
                            my_ip = elem_list[idx_elem + 1].split(':')[1].strip()
                        elif "/" in elem_list[idx_elem + 1] :
                            my_ip = elem_list[idx_elem + 1].split('/')[0].strip()
                        else :
                            my_ip = elem_list[idx_elem + 1].strip()
                        break
            elif version == 'IPv6':
                #line_info = ipconfig_lines_list[idx_line + 2]
                line_info = ipconfig_lines_list[idx_line + 4]
                elem_list = line_info.split()
                for idx_elem in range(len(elem_list)):
                    if 'inet6' in elem_list[idx_elem]:
                        my_ip = elem_list[idx_elem + 1].split('/')[0].strip()
                        break
            break
    return my_ip

#########################################################################
# FONCTION clearAllMemory()                                             #
#########################################################################
def clearAllMemory():
    """
    # ROLE :
    #   La fonction nettoie les variables pour libérer la memoire utilisée par celles ci
    # ENTREES :
    # SORTIES :
    """

    allMemory = [var for var in globals() if var[0] != "_"]
    for var in allMemory:
        del globals()[var]
    return

#########################################################################
# FONCTION getNumberCPU()                                               #
#########################################################################
def getNumberCPU():
    """
    # ROLE :
    #   La fonction renvoie le nombre de cpu de la machine hote
    # ENTREES :
    # SORTIES :
    """

    nb_cpu = 0
    nb_cpu = multiprocessing.cpu_count()
    return nb_cpu

#########################################################################
# FONCTION killTreeProcess()                                            #
#########################################################################
def killTreeProcess(pid, including_parent=True):
    """
    #   Role : Arret des processus fils
    #   Paramètres :
    #      pid : identité du processus dont on veut arreter les fils
    #      including_parent=True : on arrete le processus en même temps que ses fils
    """

    parent = psutil.Process(pid)
    childrenList = []
    try :
        childrenList = parent.get_children()
    except:
        pass

    for child in childrenList:
        killTreeProcess(child.pid)

    if including_parent == True:
        parent.kill()
    return

#############################################################################################
# FONCTION terminateThread()                                                                #
#############################################################################################
def terminateThread(thread):
    """
    # ROLE :
    #   La fonction stop l'execution d'un thread
    # ENTREES :
    #   thread: Le threading.Thread instance
    # SORTIES :
    #   N.A.
    """

    #if not thread.isAlive():
    if not thread.is_alive():
        return

    exc = ctypes.py_object(SystemExit)
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(
        ctypes.c_long(thread.ident), exc)
    if res == 0:
        raise ValueError("nonexistent thread id")
    elif res > 1:
        # if it returns a number greater than one, you're in trouble,
        # and you should call it again with exc=NULL to revert the effect
        ctypes.pythonapi.PyThreadState_SetAsyncExc(thread.ident, None)
        raise SystemError("PyThreadState_SetAsyncExc failed")
    return

#########################################################################
# FONCTION getExtensionApplication()                                    #
#########################################################################
def getExtensionApplication():
    """
    # ROLE :
    #   La fonction retourne le type d'extension approprier pour certaines applications
    #   en fonction du systeme d'environement
    # ENTREES :
    # SORTIES :
    #   Return l'extension
    """

    extend_cmd = ""
    os_system = platform.system()
    if 'Windows' in os_system :
        extend_cmd = ".bat"
    elif 'Linux' in os_system :
        extend_cmd = ".py"
    else :
        raise NameError ("!!! Erreur le type de systeme n'a pu être déterminer : " + os_system)
    return extend_cmd

#########################################################################
# FONCTION printv()                                                     #
#########################################################################
def printv ( var ):
    """
    # ROLE :
    #   La fonction print le nom d'une variable
    # ENTREES :
    #   var : la variable à printer
    # SORTIES :
    """

    command = str(inspect.stack()[1][4]).split('(')[1].split(')')[0]
    print(command)
    return

#########################################################################
# CLASSE QUI SIMULE UN SWITCH CASE                                      #
#########################################################################
class switch( object ):
    """
    # switch :
    # case :
    # Exemple d'utilisation:
    #       while switch(ident):
    #         if case(0):
    #            print("Autre : ")
    #            break
    #         if case(11000):
    #            print("Antropise : ")
    #            break
    #         if case(12200):
    #            print("Eau : ")
    #            break
    #         if case(21000):
    #            print("Ligneux : ")
    #            break
    #         if case(22000):
    #            print("NonLigneux : ")
    #            break
    #         break
    """

    value = None
    def __new__( class_, value ):
         class_.value = value
         return True

def case( *args ):
    return any( ( arg == switch.value for arg in args ) )
