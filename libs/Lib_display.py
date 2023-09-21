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