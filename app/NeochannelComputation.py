#!/usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.               #
#############################################################################

# Import des librairies Python
import os, sys
from os import chdir
from osgeo import gdal, ogr
from osgeo.gdalconst import *
# Import des librairies de /libs
from libs.Lib_display import bold,red,green,blue,cyan,endC
from libs.Lib_vector import getEmpriseFile, createEmpriseShapeReduced
from libs.Lib_file import removeFile
from libs.Lib_grass import convertRGBtoHIS

# debug = 2
PRECISION = 0.0000001

#########################################################################
# FONCTION neochannelComputation()                                      #
#########################################################################
def neochannelComputation(image_input, image_pan_input, dic_neochannels, empriseVector, imagechannel_order = ["Red","Green","Blue","NIR"], codage="float",save_intermediate_result = False, overwrite = False, debug = 0):
    """
    Rôle : Cette fonction permet de créer l'ensemble des indices radiométriques

    Paramètres :
           image_input : fichier image d'entrée multi bandes
           image_pan_input : fichier image panchromatique d'entrée monobande
           dic_neochannels : dictionnaire des fichiers de sauvegarde de chacun des néocanaux
           empriseVector : fichier vecteur emprise de la zone d'étude
           channel_order : liste d'ordre des bandes de l'image. Par défaut : ["Red","Green","Blue","NIR"]
           codage : type de codage du fichier de sortie. Par défaut : float
           save_intermediate_result : sauvegarde des résultats intermédiaire. Par défaut : False
           overwrite : paramètre de ré-écriture des fichiers. Par défaut : False
           debug : niveau de debug pour l'affichage des commentaires

    Sortie :
        liste des fichiers d'indices radiométriques
    """
    # Utilisation de fichiers temporaires pour produire les indices radiométriques
    repertory = os.path.dirname(dic_neochannels["ndvi"])
    file_name_ndvi = os.path.splitext(os.path.basename(dic_neochannels["ndvi"]))[0]
    file_name_ndwi = os.path.splitext(os.path.basename(dic_neochannels["ndwi"]))[0]
    file_name_msavi = os.path.splitext(os.path.basename(dic_neochannels["msavi"]))[0]
    file_name_sfs = os.path.splitext(os.path.basename(dic_neochannels["sfs"]))[0]
    file_name_teinte = os.path.splitext(os.path.basename(dic_neochannels["teinte"]))[0]

    extension = os.path.splitext(dic_neochannels["ndvi"])[1]

    # Nettoyage des Fichiers de sortis
    if overwrite:
        if os.path.exists(dic_neochannels["ndvi"]):
            os.remove(dic_neochannels["ndvi"])
        if os.path.exists(dic_neochannels["msavi"]):
            os.remove(dic_neochannels["msavi"])
        if os.path.exists(dic_neochannels["ndwi"]):
            os.remove(dic_neochannels["ndwi"])
        if os.path.exists(dic_neochannels["teinte"]):
            os.remove(dic_neochannels["teinte"])
        if os.path.exists(dic_neochannels["sfs"]):
            os.remove(dic_neochannels["sfs"])

    # Calcul du NDVI
    createNDVI(image_input, dic_neochannels["ndvi"], debug=debug)

    # Calcul du MSAVI2
    createMSAVI2(image_input, dic_neochannels["msavi"], debug=debug)

    # Calcul du NDWI2
    createNDWI2(image_input, dic_neochannels["ndwi"], debug=debug)

    # Calcul de la teinte
    createHIS(image_input, dic_neochannels["teinte"], li_choice = ["H"], debug=debug)
    dic_neochannels["teinte"] = os.path.splitext(dic_neochannels["teinte"])[0]  + "_H" + os.path.splitext(dic_neochannels["teinte"])[1]

    # Calcul de la texture SFS
    createSFS(image_pan_input, dic_neochannels["sfs"], debug=debug)

    return

#########################################################################
# FONCTION createNDVI()                                                 #
#########################################################################
def createNDVI(image_input, image_NDVI_output, channel_order = ["Red","Green","Blue","NIR"], codage="float", debug = 0):
    """
    #   Rôle : Cette fonction permet de créer un fichier NDVI (végétation) à partir d'une image ortho multi bande
    #   paramètres :
    #       image_input : fichier image d'entrée multi bandes
    #       image_NDVI_output : fichier NDVI de sortie une bande
    #       channel_order : liste d'ordre des bandes de l'image, par défaut : ["Red","Green","Blue","NIR"]
    #       codage : type de codage du fichier de sortie
    #       debug : niveau de debug pour l'affichage des commentaires
    """

    # Variables
    Red = ""
    NIR = ""

    # Selection des bandes pour le calcul du NDVI
    if "Red" in channel_order:
        num_channel = channel_order.index("Red")+1
        Red = "im1b"+str(num_channel)
    if "NIR" in channel_order:
        num_channel = channel_order.index("NIR")+1
        NIR = "im1b"+str(num_channel)
    if (Red == "" or NIR == ""):
        raise NameError(cyan + "createNDVI() : " + bold + red + "NDVI needs Red and NIR channels to be computed"+ endC)

    # Creer l'expression
    expression = "\"(" + NIR + "==" + Red + ")?(" + Red + "== 0)?0:" + str(PRECISION) + ":" + "(" + NIR + "-" + Red + ")/(" + NIR + "+" + Red + "+" + str(PRECISION) + ")\""

    # Bandmath pour creer l'indice NDVI
    command = "otbcli_BandMath -il %s -out %s %s -exp %s" %(image_input, image_NDVI_output,codage,expression)
    if debug >= 2:
        print(command)
    exitCode = os.system(command)
    if exitCode != 0:
        print(command)
        raise NameError(bold + red + "createNDVI() : An error occured during otbcli_BandMath command. See error message above." + endC)

    print(cyan + "createNDVI() : " + bold + green + "Create NDVI file %s complete!" %(image_NDVI_output) + endC)

    return

#########################################################################
# FONCTION createNDWI2()                                                #
#########################################################################
def createNDWI2(image_input, image_NDWI2_output, channel_order = ["Red","Green","Blue","NIR"], codage="float", debug = 0):
    """
    Rôle : Créé une image NDWI2 (indice d'eau) à partir d'une image ortho multi bande

    Paramètres :
           image_input : fichier image d'entrée multi bandes
           image_NDWI2_output : fichier NDWI2 de sortie (une bande)
           channel_order : liste d'ordre des bandes de l'image, par défaut : ["Red","Green","Blue","NIR"]
           codage : type de codage du fichier de sortie
           debug : niveau de debug pour l'affichage des commentaires
    """

    # Variables
    Green = ""
    NIR = ""

    # Selection des bandes pour le calcul du NDWI2
    if "Green" in channel_order:
        num_channel = channel_order.index("Green")+1
        Green = "im1b"+str(num_channel)
    if "NIR" in channel_order:
        num_channel = channel_order.index("NIR")+1
        NIR = "im1b"+str(num_channel)
    if (Green == "" or NIR == ""):
        raise NameError(cyan + "createNDWI2() : " + bold + red + "NDWI2 needs Green and NIR channels to be computed"+ endC)

    # Creer l'expression
    expression = "\"(" + NIR + "==" + Green + ")?(" + NIR + "== 0)?0:" + str(PRECISION) + ":" + "(" + Green + "-" + NIR + ")/(" + Green + "+" + NIR + "+" + str(PRECISION) + ")\""

    # Bandmath pour creer l'indice NDWI2
    command = "otbcli_BandMath -il %s -out %s %s -exp %s" %(image_input, image_NDWI2_output,codage,expression)
    if debug >= 2:
        print(command)
    exitCode = os.system(command)
    if exitCode != 0:
        print(command)
        raise NameError(bold + red + "createNDWI2() : An error occured during otbcli_BandMath command. See error message above." + endC)

    print(cyan + "createNDWI2() : " + bold + green + "Create NDWI2 file %s complete!" %(image_NDWI2_output) + endC)

    return

#########################################################################
# FONCTION createMSAVI2()                                               #
#########################################################################
def createMSAVI2(image_input, image_MSAVI2_output, channel_order = ["Red","Green","Blue","NIR"], codage="float", debug = 0):
    """
    Rôle : calcul l'image MSAVI2 (indice de végétation) à partir d'une image ortho multi bande

    Paramètres :
           image_input : fichier image d'entrée multi bandes
           image_MSAVI2_output : fichier MSAVI de sortie une bande
           channel_order : liste d'ordre des bandes de l'image, par défaut ["Red","Green","Blue","NIR"]
           codage : type de codage du fichier de sortie
           debug : niveau de debug pour l'affichage des commentaires
    """

    # Variables
    Red = ""
    NIR = ""

    # Selection des bandes pour le calcul du MSAVI2
    if "Red" in channel_order:
        num_channel = channel_order.index("Red")+1
        Red = "im1b"+str(num_channel)
    if "NIR" in channel_order:
        num_channel = channel_order.index("NIR")+1
        NIR = "im1b"+str(num_channel)
    if (Red == "" or NIR == ""):
        raise NameError(cyan + "createMSAVI2() : " + bold + red + "MSAVI2 needs Red and NIR channels to be computed"+ endC)

    # Creer l'expression
    expression = "\"("+ NIR + " == " + Red + ")and(" + NIR + " == 0)?" + str(PRECISION) +" : (2 * " + NIR + " + 1 - sqrt(( 2 * " + NIR + " + 1 )^2 - 8 *(" + NIR + " - " + Red +"))+" +  str(PRECISION)+")/2 \""


    # Bandmath pour creer l'indice MSAVI2
    command = "otbcli_BandMath -il %s -out %s %s -exp %s" %(image_input, image_MSAVI2_output,codage,expression)
    if debug >= 2:
        print(command)
    exitCode = os.system(command)
    if exitCode != 0:
        print(command)
        raise NameError(bold + red + "createMSAVI2() : An error occured during otbcli_BandMath command. See error message above." + endC)

    print(cyan + "createMSAVI2() : " + bold + green + "Create MSAVI2 file %s complete!" %(image_MSAVI2_output) + endC)

    return

#########################################################################
# FONCTION createHIS()                                                  #
#########################################################################
def createHIS(image_input, image_HIS_output, li_choice = ["H","I","S"], channel_order = ["Red","Green","Blue","NIR"], codage="float", debug = 0):
    """
    Rôle : converti l'image RVBPIR en image H(teinte)I(intensite)S(saturation). Il y a possibilité de choisir la(es)quelle(s) des trois on garde.

    Paramètres :
           image_input : fichier image d'entrée multi bandes
           image_HIS_output : fichier HIS permettant de localiser le dossier ou les donnees HIS vont etre sauvegardees
           li_choice : liste des images que l'on souhaite garder, par défaut ["H","I","S"]
           channel_order : liste d'ordre des bandes de l'image, par défaut : ["Red","Green","Blue","NIR"]
           codage : type de codage du fichier de sortie
           debug : niveau de debug pour l'affichage des commentaires
    """

    cont = 0
    # Variables
    Red = ""
    Green = ""
    Blue = ""
    NIR = ""

    # Selection des bandes pour le calcul de ISI
    if "Red" in channel_order:
        num_channel = channel_order.index("Red")+1
        Red = "im1b"+str(num_channel)
    if "Green" in channel_order:
        num_channel = channel_order.index("Green")+1
        Green = "im1b"+str(num_channel)
    if "Blue" in channel_order:
        num_channel = channel_order.index("Blue")+1
        Blue = "im1b"+str(num_channel)
    if "NIR" in channel_order:
        num_channel = channel_order.index("NIR")+1
        NIR = "im1b"+str(num_channel)
    if (Red == "" or Green == "" or Blue == "" or NIR == ""):
        raise NameError(cyan + "createHIS() : " + bold + red + "HIS needs Red and Green and Blue and NIR channels to be computed"+ endC)

    # Repository qui sera a supprimer
    repository = os.path.dirname(image_HIS_output)
    filename = os.path.splitext(os.path.basename(image_input))[0]

    # Creer les images Rouge, Vert, Bleu
    fp_red = repository + os.sep + filename + "_R.tif"
    fp_green =  repository + os.sep + filename + "_V.tif"
    fp_blue = repository + os.sep + filename + "_B.tif"
    # Rouge
    command_red = "gdal_translate -b 1 %s %s" %(image_input, fp_red)
    os.system(command_red)
    # Vert
    command_green = "gdal_translate -b 2 %s %s" %(image_input, fp_green)
    os.system(command_green)
    # Bleu
    command_blue = "gdal_translate -b 3 %s %s" %(image_input, fp_blue)
    os.system(command_blue)

    # Bandmath pour creer l'indice ISI
    img_H, img_I, img_S = convertRGBtoHIS(image_input, image_HIS_output, fp_red, fp_green, fp_blue)

    l = [img_H, img_I, img_S]
    # une ligne est à rajouter pour produire l'image HIS contenant les 3 bandes H, I et S (concatenation de bandes)
    # suppression de une ou plusieurs images produites suivant le choix de sortie li_choice
    if "H" not in li_choice:
        if os.path.exists(img_H):
            removeFile(img_H)
        l.remove(img_H)
    if "I" not in li_choice:
        if os.path.exists(img_I):
            removeFile(img_I)
        l.remove(img_I)
    if "S" not in li_choice:
        if os.path.exists(img_S):
            removeFile(img_S)
        l.remove(img_S)

    print(cyan + "createHIS() : " + bold + green + "Create HIS file %s complete!" %(image_HIS_output) + endC)

    return l

#########################################################################
# FONCTION createSFS()                                                  #
#########################################################################
def createSFS(image_pan_input, image_SFS_output, li_choice = [4], codage="float", debug = 0):
    """
    Rôle : créé un fichier de texture Structural Features Set : Lenght (b1), Width (b2), PSI (b3), W-Mean (b4), Ratio (b5) et SD (b6)
               à partir d'une fonction de l'otb et d'extraire uniquement la bande qui nous intéresse par la même occasion
    Paramètres :
           image_pan_input : fichier image d'entrée panchromatique
           image_SFS_output : fichier SFS de sortie allant de 1 à 6 bandes
           li_choice : liste des bandes à garder. Par défaut [4] --> on garde la bande 4
           codage : type de codage du fichier de sortie
           debug : niveau de debug pour l'affichage des commentaires
    """

    print(cyan + "createSFS() : " + bold + green + "Début du calcul de texture SFS" + endC)
    if len(li_choice) == 6 :
        cmd_sfs = "otbcli_SFSTextureExtraction -in %s -channel 1 -out %s" %(image_pan_input, image_SFS_output)
        exitCode = os.system(cmd_sfs)
        if exitCode != 0:
            print(command)
            raise NameError(bold + red + "createSFS() : An error occured during otbcli_SFSTextureExtraction command. See error message above." + endC)
    else :

        # Utilisation d'un fichier temporaire pour le calcul de l'image SFS
        repertory_output = os.path.dirname(image_SFS_output)
        file_name = os.path.splitext(os.path.basename(image_SFS_output))[0]
        extension = os.path.splitext(image_SFS_output)[1]
        file_out_suffix_l = "_u"
        l_file_tmp = repertory_output + os.sep + file_name + file_out_suffix_l + extension

        cmd_sfs = "otbcli_SFSTextureExtraction -in %s -channel 1 -out %s" %(image_pan_input, l_file_tmp)
        exitCode = os.system(cmd_sfs)
        if exitCode != 0:
            print(cmd_sfs)
            raise NameError(bold + red + "createSFS() : An error occured during otbcli_SFSTextureExtraction command. See error message above." + endC)

        # Préparation des bandes et donc des paramètres SFS à garder
        cmd_export = "gdal_translate "
        for el in li_choice :
            cmd_export += " -b " + str(el)
        cmd_export += " " + l_file_tmp + " " + image_SFS_output
        exitCode = os.system(cmd_export)
        if exitCode != 0:
            print(cmd_export)
            raise NameError(bold + red + "createSFS() : An error occured during gdal_translate command. See error message above." + endC)

        # Suppression du fichier temporaire
        if os.path.exists(l_file_tmp):
            removeFile(l_file_tmp)

    print(cyan + "createSFS() : " + bold + green + "Calcul de la texture SFS est terminé"  + endC)

    return
