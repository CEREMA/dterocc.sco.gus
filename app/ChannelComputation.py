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
from Lib_display import bold,red,green,blue,cyan,endC
from Lib_vector import getEmpriseVector, createEmpriseShapeReduced
from Lib_file import removeFile
from Lib_grass import convertRGBtoHIS
from Lib_raster import cutImageByVector

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
    file_name_sfs = os.path.splitext(os.path.basename(dic_neochannels["sfs"]))[0]

    extension = os.path.splitext(dic_neochannels["ndvi"])[1]

    # Nettoyage des Fichiers de sortie
    if overwrite:
        if os.path.exists(dic_neochannels["ndvi"]):
            os.remove(dic_neochannels["ndvi"])
        if os.path.exists(dic_neochannels["sfs"]):
            os.remove(dic_neochannels["sfs"])

    # Calcul du NDVI
    createNDVI(image_input, dic_neochannels["ndvi"], debug=debug)

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
        cmd_export += " -a_nodata -1"
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











