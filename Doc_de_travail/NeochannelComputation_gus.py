from __future__ import print_function
import os, sys, glob, argparse, shutil, numpy, time, errno, fnmatch
from os import chdir
from osgeo import gdal, ogr
from osgeo.gdalconst import *
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_operator import getExtensionApplication
from Lib_vector import getEmpriseFile, createEmpriseShapeReduced
from Lib_raster import getPixelWidthXYImage, changeDataValueToOtherValue, getProjectionImage, updateReferenceProjection, roundPixelEmpriseSize, cutImageByVector, getNodataValueImage, getDataTypeImage, getEmpriseImage
from Lib_file import removeVectorFile, removeFile
from Lib_text import appendTextFileCR
from Lib_grass import convertRGBtoHIS

debug = 2
PRECISION = 0.0000001

#########################################################################
# FONCTION createNDVI()                                                 #
#########################################################################
def neochannelComputation(image_input, image_pan_input, file_output, imagechannel_order = ["Red","Green","Blue","NIR"], codage="float"):
    """
    #   Rôle : Cette fonction permet de créer l'ensemble des indices radiométriques
    #   Paramètres :
    #       image_input : fichier image d'entrée multi bandes
    #       image_pan_input : fichier image panchromatique d'entrée monobande
    #       file_output : fichier indiquant le repertoire dans lequel on va sauvegardre les données intermédiaires
    #       channel_order : liste d'ordre des bandes de l'image, par défaut : ["Red","Green","Blue","NIR"]
    #       codage : type de codage du fichier de sortie
    """
    # Utilisation de fichiers temporaires pour produire les indices radiométriques
    repertory_output = os.path.dirname(file_output)
    file_name = os.path.splitext(os.path.basename(file_output))[0]
    extension = os.path.splitext(file_output)[1]

    file_out_suffix_ndvi = "_ndvi"
    ndvi_file_tmp = repertory_output + os.sep + file_name + file_out_suffix_ndvi + extension

    if os.path.exists(ndvi_file_tmp):
        os.remove(ndvi_file_tmp)

    file_out_suffix_msavi2 = "_msavi2"
    msavi2_file_tmp = repertory_output + os.sep + file_name + file_out_suffix_msavi2 + extension

    if os.path.exists(msavi2_file_tmp):
        os.remove(msavi2_file_tmp)

    file_out_suffix_ndwi2 = "_ndwi2"
    ndwi2_file_tmp = repertory_output + os.sep + file_name + file_out_suffix_ndwi2 + extension

    if os.path.exists(ndwi2_file_tmp):
        os.remove(ndwi2_file_tmp)

    file_out_suffix_h = "_h"
    h_file_tmp = repertory_output + os.sep + file_name + file_out_suffix_h + extension

    if os.path.exists(h_file_tmp):
        os.remove(h_file_tmp)

    file_out_suffix_sfs = "_txtSFS"
    sfs_file_tmp = repertory_output + os.sep + file_name + file_out_suffix_sfs + extension

    if os.path.exists(sfs_file_tmp):
        os.remove(sfs_file_tmp)

    # Calcul du NDVI
    #createNDVI(image_input, ndvi_file_tmp)

    # Calcul du MSAVI2
    #createMSAVI2(image_input, msavi2_file_tmp)
    # Calcul du NDWI2
    #createNDWI2(image_input, ndwi2_file_tmp)
    # Calcul de la teinte
    createHIS(image_input, h_file_tmp, li_choice = ["H"])
    # Calcul de la texture SFS
    createSFS(image_pan_input, sfs_file_tmp)

    return ndvi_file_tmp, msavi2_file_tmp, ndwi2_file_tmp, h_file_tmp, sfs_file_tmp



###########################################################################################################################################
# FONCTION concatenateChannels()                                                                                                          #
###########################################################################################################################################
def concatenateChannels(images_input_list, stack_image_output, code="float", save_results_intermediate=False, overwrite=True):
    """
    # ROLE:
    #   Role : ajout de neocanaux (textures et/ou indices) deja calcules ou non a l'image d'origine
    #     Compléments sur la fonction otbcli_HaralickTextureExtraction : http://www.orfeo-toolbox.org/CookBook/CookBooksu98.html#x130-6310005.6.6
    #     Compléments sur la fonction otbcli_SplitImage : http://www.orfeo-toolbox.org/CookBook/CookBooksu68.html#x95-2580005.1.10
    #     Compléments sur la fonction otbcli_BandMath : http://www.orfeo-toolbox.org/CookBook/CookBooksu125.html#x161-9330005.10.1
    #
    # ENTREES DE LA FONCTION :
    #    images_input_list : liste de fichiers a stacker ensemble
    #    stack_image_output : le nom de l'empilement image de sortie
    #    path_time_log : le fichier de log de sortie
    #    code : encodage du fichier de sortie
    #    save_results_intermediate : fichiers de sorties intermediaires non nettoyees, par defaut = False
    #    overwrite : boolen si vrai, ecrase les fichiers existants
    #
    # SORTIES DE LA FONCTION :
    #    le nom complet de l'image de sortie
    #    Elements generes : une image concatenee rangee
    #
    """


    print(endC)
    print(bold + green + "## Début : Concaténation des bandes" + endC)
    print(endC)

    if debug >= 3:
        print(bold + green + "Variables dans la fonction" + endC)
        print(cyan + "concatenateChannels() : " + endC + "images_input_list : " + str(images_input_list) + endC)
        print(cyan + "concatenateChannels() : " + endC + "stack_image_output : " + str(stack_image_output) + endC)
        print(cyan + "concatenateChannels() : " + endC + "code : " + str(code) + endC)
        print(cyan + "concatenateChannels() : " + endC + "path_time_log : " + str(path_time_log) + endC)
        print(cyan + "concatenateChannels() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "concatenateChannels() : " + endC + "overwrite : " + str(overwrite) + endC)

    check = os.path.isfile(stack_image_output)
    if check and not overwrite: # Si l'empilement existe deja et que overwrite n'est pas activé
        print(bold + yellow + "Le fichier " + stack_image_output + " existe déjà et ne sera pas recalculé." + endC)
    else:
        if check:
            try:
                removeFile(stack_image_output)
            except Exception:
                pass # si le fichier n'existe pas, il ne peut pas être supprimé : cette étape est ignorée

        print(bold + green + "Recherche de bandes à ajouter..." + endC)

        elements_to_stack_list_str = ""    # Initialisation de la liste des fichiers autres a empiler

        # Gestion des fichiers a ajouter
        for image_name_other in images_input_list:

            if debug >= 3:
                print(cyan + "concatenateChannels() : " + endC + "image_name_other : " + str(image_name_other) + endC)

            # Verification de l'existence de image_name_other
            if not os.path.isfile(image_name_other) :
                # Si image_name_other n'existe pas, message d'erreur
                raise NameError(cyan + "concatenateChannels() : " + bold + red + "Le fichier %s n'existe pas !"%(image_name_other) + endC)

            # Ajouter l'indice a la liste des indices a empiler
            elements_to_stack_list_str += " " + image_name_other

            if debug >= 1:
                print(cyan + "concatenateChannels() : " + endC + "elements_to_stack_list_str : " + str(elements_to_stack_list_str) + endC)

        # Stack de l'image avec les images additionnelles
        if len(elements_to_stack_list_str) > 0:

            # Assemble la liste d'image en une liste globale de fichiers d'entree
            print(bold + green + "concatenateChannels() : Assemblage des bandes %s ... "%(elements_to_stack_list_str) + endC)

            command = "otbcli_ConcatenateImages -progress true -il %s -out %s %s" %(elements_to_stack_list_str,stack_image_output,code)
            if debug >= 3:
                print(command)
            exitCode = os.system(command)
            if exitCode != 0:
                print(command)
                raise NameError(cyan + "concatenateChannels() : " + bold + red + "An error occured during otbcli_ConcatenateImages command. See error message above." + endC)
            print(bold + green + "concatenateChannels() : Channels successfully assembled" + endC)

    print(endC)
    print(bold + green + "## Fin : Concaténation des bandes " + endC)
    print(endC)


    return

#########################################################################
# FONCTION createNDVI()                                                 #
#########################################################################
def createNDVI(image_input, image_NDVI_output, channel_order = ["Red","Green","Blue","NIR"], codage="float"):
    """
    #   Rôle : Cette fonction permet de créer un fichier NDVI (végétation) à partir d'une image ortho multi bande
    #   paramètres :
    #       image_input : fichier image d'entrée multi bandes
    #       image_NDVI_output : fichier NDVI de sortie une bande
    #       channel_order : liste d'ordre des bandes de l'image, par défaut : ["Red","Green","Blue","NIR"]
    #       codage : type de codage du fichier de sortie
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
def createNDWI2(image_input, image_NDWI2_output, channel_order = ["Red","Green","Blue","NIR"], codage="float"):
    """
    #   Rôle : Cette fonction permet de créer un fichier NDWI2 (eau) à partir d'une image ortho multi bande
    #   paramètres :
    #       image_input : fichier image d'entrée multi bandes
    #       image_NDWI2_output : fichier NDWI2 de sortie (une bande)
    #       channel_order : liste d'ordre des bandes de l'image, par défaut : ["Red","Green","Blue","NIR"]
    #       codage : type de codage du fichier de sortie
    # Source : https://hal.archives-ouvertes.fr/halshs-01070803/document
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
def createMSAVI2(image_input, image_MSAVI2_output, channel_order = ["Red","Green","Blue","NIR"], codage="float"):
    """
    #   Rôle : Cette fonction permet de créer un fichier MSAVI2 (végétation) à partir d'une image ortho multi bande
    #   paramètres :
    #       image_input : fichier image d'entrée multi bandes
    #       image_MSAVI2_output : fichier MSAVI de sortie une bande
    #       channel_order : liste d'ordre des bandes de l'image, par défaut ["Red","Green","Blue","NIR"]
    #       codage : type de codage du fichier de sortie
    #
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
def createHIS(image_input, image_HIS_output, li_choice = ["H","I","S"], channel_order = ["Red","Green","Blue","NIR"], codage="float"):
    """
    #   Rôle : Cette fonction permet de créer un fichier ISI (ombre) à partir d'une image ortho multi bande
    #   paramètres :
    #       image_input : fichier image d'entrée multi bandes
    #       image_HIS_output : fichier HIS permettant de localiser le dossier ou les donnees HIS vont etre sauvegardees
    #       li_choice : liste des images que l'on souhaite garder, par défaut ["H","I","S"]
    #       channel_order : liste d'ordre des bandes de l'image, par défaut : ["Red","Green","Blue","NIR"]
    #       codage : type de codage du fichier de sortie
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
    fp_red = repository+'/'+filename+"_R.tif"
    fp_green =  repository+'/'+filename+"_V.tif"
    fp_blue = repository+'/'+filename+"_B.tif"
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
    img_H, img_I, img_S = convertRGBtoHIS(image_input, fp_red, fp_green, fp_blue)

    ##une ligne est à rajouter pour produire l'image HIS contenant les 3 bandes H, I et S (concatenation de bandes)
    #suppression de une ou plusieurs images produites suivant le choix de sortie li_choice
    if "H" not in li_choice:
        if os.path.exists(img_H):
            removeFile(img_H)
    if "I" not in li_choice:
        if os.path.exists(img_I):
            removeFile(img_I)
    if "S" not in li_choice:
        if os.path.exists(img_S):
            removeFile(img_S)

    print(cyan + "createHIS() : " + bold + green + "Create HIS file %s complete!" %(image_HIS_output) + endC)

    return

#########################################################################
# FONCTION createSFS()                                                  #
#########################################################################
def createSFS(image_pan_input, image_SFS_output, li_choice = [4], codage="float"):
    """
    #   Rôle : Cette fonction permet de créer un fichier de texture Structural Features Set : Lenght (b1), Width (b2), PSI (b3), W-Mean (b4), Ratio (b5) et SD (b6)
    #           à partir d'une fonction de l'otb et d'extraire uniquement la bande qui nous intéresse par la même occacion
    #   Paramètres :
    #       image_pan_input : fichier image d'entrée panchromatique
    #       image_SFS_output : fichier SFS de sortie allant de 1 à 6 bandes
    #       li_choice : liste des bandes à garder, par défaut [4] --> on garde la bande 4
    #       codage : type de codage du fichier de sortie
    #
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
        file_out_suffix_his = "_his"
        his_file_tmp = repertory_output + os.sep + file_name + file_out_suffix_his + extension

        cmd_sfs = "otbcli_SFSTextureExtraction -in %s -channel 1 -out %s" %(image_pan_input, his_file_tmp)
        exitCode = os.system(cmd_sfs)
        if exitCode != 0:
            print(command)
            raise NameError(bold + red + "createSFS() : An error occured during otbcli_SFSTextureExtraction command. See error message above." + endC)

        # Préparation des bandes et donc des paramètres SFS à garder
        cmd_export = "gdal_translate "
        for el in li_choice :
            cmd_export += " -b " + str(el)
        cmd_export += " " + his_file_tmp + " " + image_SFS_output
        exitCode = os.system(cmd_sfs)
        if exitCode != 0:
            print(command)
            raise NameError(bold + red + "createSFS() : An error occured during gdal_translate command. See error message above." + endC)

    print(cyan + "createSFS() : " + bold + green + "Calcul de la texture SFS est terminé"  + endC)

    return
