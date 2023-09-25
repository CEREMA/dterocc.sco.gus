# -*- coding: utf-8 -*-
#!/usr/bin/python

#############################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.               #
#############################################################################

#############################################################################
#                                                                           #
# FONCTIONS EN LIEN AVEC L'AFFICHAGE D'INFORMATIONS                         #
#                                                                           #
#############################################################################
"""
Ce module défini des fonctions d'affichage utiles a la chaine.
"""

import os, platform

import six
if six.PY2:
    from PyQt4 import QtGui
    from Tkinter import *
    import argparseui
else :
    from PyQt5 import QtGui
    from tkinter import *

##############################################################
# MISE EN FORME DES MESSAGES DANS LA CONSOLE                 #
##############################################################

# Pour y accéder dans un script : from fcts_Affichage import bold,black,red,green,yellow,blue,magenta,cyan,endC
osSystem = platform.system()
if 'Windows' in osSystem :
    # EFFETS
    bold = ""
    talic = ""
    underline = ""
    blink = ""
    rapidblink = ""
    beep = ""

    # COULEURS DE TEXTE
    black = ""
    red = ""
    green = ""
    yellow = ""
    blue = ""
    magenta = ""
    cyan = ""
    white = ""

    # COULEUR DE FOND
    BGblack = ""
    BGred = ""
    BGgreen = ""
    BGyellow = ""
    BGblue = ""
    BGmagenta = ""
    BGcyan = ""
    BGwhite = ""

    endC = ""

elif 'Linux' in osSystem :
    # EFFETS
    bold = "\033[1m"
    italic = "\033[3m"
    underline = "\033[4m"
    blink = "\033[5m"
    rapidblink = "\033[6m"
    beep = "\007"

    # COULEURS DE TEXTE
    black = "\033[30m"
    red = "\033[31m"
    green = "\033[32m"
    yellow = "\033[33m"
    blue = "\033[34m"
    magenta = "\033[35m"
    cyan = "\033[36m"
    white = "\033[37m"

    # COULEUR DE FOND
    BGblack = "\033[40m"
    BGred = "\033[41m"
    BGgreen = "\033[42m"
    BGyellow = "\033[43m"
    BGblue = "\033[44m"
    BGmagenta = "\033[45m"
    BGcyan = "\033[46m"
    BGwhite = "\033[47m"

    endC = "\033[0m"


#########################################################################
# FONCTION displayIHM()                                                 #
#########################################################################
def displayIHM(gui, parser):
    """
    #   Rôle : Cette fonction permet d'appeler les applications version IHM plutôt qu'en ligne de commande
    #   Paramètres :
    #       gui : boolen active ou desactive la version IHM (activé = True)
    #       parser : le parseur argpase
    #   Retour : args (les arguments)
    """

    args = None
    if gui and six.PY2 :
        app = QtGui.QApplication(sys.argv)
        a = argparseui.ArgparseUi(parser, window_title=parser.prog, use_save_load_button=True)
        a.show()
        app.exec_()
        if a.result() == 1: # Ok pressed
            args = a.parse_args() # ask argparse to parse the options
        else:
            sys.exit(0) # Cancel exit app
    else :
        args = parser.parse_args()
    return args