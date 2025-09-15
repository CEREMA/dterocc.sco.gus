#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT DE RECHERCHE ET DE DECOUPAGE D'IMAGE RASTER SELON UN MASQUE VECTEUR                                                                #
                                                                                                                                       #
# Import des bibliothèques python
import os, sys, glob
from os import chdir
from osgeo import gdal, ogr
from osgeo.gdalconst import *

# Import des librairies de /libs
from Lib_display import bold,black,red,cyan,endC
from Lib_vector import getEmpriseVector, createEmpriseShapeReduced
from Lib_raster import getPixelWidthXYImage, getProjectionImage, updateReferenceProjection, cutImageByVector, getNodataValueImage, getDataTypeImage
from Lib_file import removeFile, cleanTempData
from Lib_text import appendTextFileCR
from Lib_operator import getExtensionApplication

#########################################################################
# FONCTION assemblyRasters()                                            #
#########################################################################
def assemblyRasters(empriseVector, repRasterAssemblyList, output_rasterAssembly, format_raster = 'GTiff', format_vector = 'GPKG', ext_list = ['tif','TIF','tiff','TIFF','ecw','ECW','jp2','JP2','asc','ASC'], rewrite = True, save_results_intermediate = False):
    """
    Rôle :
         Rechercher dans un repertoire toutes les images qui sont contenues ou qui intersectent l'emprise

    Paramètres :
        empriseVector            : Fichier vecteur de l'emprise de la zone d'étude
        repRasterAssemblyList    : Repertoire de recherche des images
        output_rasterAssembly           : Fichier de l'image assemblée
        format_raster            : Format du fichier image, par défaut : GTiff
        format_vector            : Format du fichier vecteur, par défaut : GPKG
        ext_list                 : Liste des extensions d'images, par défaut : ['tif','TIF','tiff','TIFF','ecw','ECW','jp2','JP2','asc','ASC']
        rewrite                  : Ré-écriture ou pas, par défaut True ie ré-ecriture
        save_result_intermediate : True si on sauvegarde les résultats intermédiaire, sinon False, par défaut : False
    """
    # Emprise de la zone selectionnée
    empr_xmin,empr_xmax,empr_ymin,empr_ymax = getEmpriseVector(empriseVector, format_vector=format_vector)

    repRasterAssembly_str = ""

    # Recherche des images dans l'emprise du vecteur
    for repertory in repRasterAssemblyList:
        images_find_list, images_error_list = findImagesFile(repertory, ext_list, empr_xmin, empr_xmax, empr_ymin, empr_ymax)
        repRasterAssembly_str += str(repertory) + "  "

    # Création d'un dossier temporaire où on va stocker tous les fichiers temporaires
    FOLDER_ASSEMBLY_TEMP = "tmp"
    repertory_assembly_output = os.path.dirname(output_rasterAssembly)
    repertory_temp = repertory_assembly_output + os.sep + FOLDER_ASSEMBLY_TEMP

    # Création du répertoire temporaire si il n'existe pas
    if not os.path.isdir(repertory_temp):
        os.makedirs(repertory_temp)

    # Nettoyage du répertoire temporaire si il n'est pas vide
    cleanTempData(repertory_temp)

    # Suppression du fichier assemblé
    if os.path.exists(output_rasterAssembly):
        if rewrite == True :
            try:
                os.remove(output_rasterAssembly)
            except:
                print(bold + red + "!!! Erreur le fichier raster %s ne peut pas être écrasé il est utilisé par un autre processus ou en lecture seul !!!" %(output_rasterAssembly) + endC)
                return -1
        else :
           return -1


    if len(images_find_list) > 0 and os.path.isfile(images_find_list[0]) :
        epsg = getProjectionImage(images_find_list[0])[0]
        no_data_value = getNodataValueImage(images_find_list[0])
        data_type = getDataTypeImage(images_find_list[0])
        if no_data_value == None :
            no_data_value = 0
    else :
        print(bold + red + "Erreur il n'y a pas de fichier image correspondant à l'emprise dans le(s) répertoire(s) : %s!!!" %(repRasterAssembly_str) + endC)
        return -1


    # Si une seule image contient la zone d'étude, pas d'assemblage

    if len(images_find_list) == 1 :
        img = images_find_list[0]
        output_rasterAssembly = img

    # Sinon assembler les images trouvées

    else :
        assemblyImages(repertory_temp, images_find_list, output_rasterAssembly, no_data_value , epsg , save_results_intermediate, format_raster = format_raster)

    '''
    # Découpage du fichier image assemblé par l'emprise

    if os.path.exists(output_rasterAssembly) :
        cutImageByVector(empriseVector, output_rasterAssembly, output_rasterAssembly_cut, no_data_value = no_data_value, epsg= epsg, format_vector= format_vector)
    else :
        print(bold + red + "Erreur il n'y a pas de fichier assemblé %s à découper !!!" %(output_rasterAssembly) + endC)
        return -1
    '''

    return output_rasterAssembly

#########################################################################
# FONCTION findImagesFile()                                             #
#########################################################################
def findImagesFile(repertory, extension_list, empr_xmin, empr_xmax, empr_ymin, empr_ymax):
    """
    Rôle :
        Rechercher dans un repertoire toutes les images qui sont contenues ou qui intersectent l'emprise

    Paramètres :
        repertory      : Repertoire de recherche
        extension_list : Liste des extensions d'images, par défaut : ['tif','TIF','tiff','TIFF','ecw','ECW','jp2','JP2','asc','ASC']
        empr_xmin      : L'emprise coordonnée xmin
        empr_xmax      : L'emprise coordonnée xmax
        empr_ymin      : L'emprise coordonnée ymin
        empr_ymax      : L'emprise coordonnée ymax

     Sortie :
        La liste des images selectionnées dans l'emprise
        La liste des images en erreur

    """
    debug = 1
    images_find_list = []
    images_error_list = []
    print(cyan + "findImagesFile : Début de la recherche dans le repertoire des images contenues ou intersectant l'emprise" + endC)
    if debug >= 3:
        print(cyan + "selectImagesFile() : Début de la sélection des dossiers images" + endC)
        print(cyan + "selectImagesFile : " + endC + "repertoire : " + str(repertory) + endC)
        print(cyan + "selectImagesFile : " + endC + "empr_xmin : " + str(empr_xmin) + endC)
        print(cyan + "selectImagesFile : " + endC + "empr_xmax : " + str(empr_xmax) + endC)
        print(cyan + "selectImagesFile : " + endC + "empr_ymin : " + str(empr_ymin) + endC)
        print(cyan + "selectImagesFile : " + endC + "empr_ymax : " + str(empr_ymax) + endC)

    # Recherche des fichier correspondant à l'extension dans le repertoire de recherche
    print(glob.glob(repertory + os.sep + '*/*'))
    for imagefile in glob.glob(repertory + os.sep + '*.*'):
        ok = True
        if imagefile.rsplit('.',1)[1] in extension_list :
            try:
                dataset = gdal.Open(imagefile, GA_ReadOnly)
            except :
                print(bold + red + "Erreur Impossible d'ouvrir le fichier : %s !!!"%(imagefile) + endC)
                images_error_list.append(imagefile)
                ok = False
            if ok and dataset is None :
                images_error_list.append(imagefile)
                ok = False
                print("image en erreur")
            if ok :
                cols = dataset.RasterXSize
                rows = dataset.RasterYSize
                bands = dataset.RasterCount

                geotransform = dataset.GetGeoTransform()
                pixel_width = geotransform[1]  # w-e pixel resolution
                pixel_height = geotransform[5] # n-s pixel resolution

                imag_xmin = geotransform[0]     # top left x
                imag_ymax = geotransform[3]     # top left y
                imag_xmax = imag_xmin + (cols * pixel_width)
                imag_ymin = imag_ymax + (rows * pixel_height)
                print( imag_xmin, imag_xmax, imag_ymin, imag_ymax)
                # Si l'image et l'emprise sont complement disjointe l'image n'est pas selectionée
                if not ((imag_xmin > empr_xmax) or (imag_xmax < empr_xmin) or (imag_ymin > empr_ymax) or (imag_ymax < empr_ymin)) :
                    images_find_list.append(imagefile)

    print(cyan + "findImagesFile : Fin de la recherche dans le repertoire des images contenues ou intersectant l'emprise" + endC)
    return images_find_list, images_error_list

###########################################################################################################################################
# FONCTION assemblyImages()                                                                                                               #
###########################################################################################################################################
def assemblyImages(repertory, images_list, output_file, no_data_value, epsg, save_results_intermediate = False, ext_txt = '.txt',  format_raster = 'GTiff'):
    """
    Rôle :
        Assembler une liste d'image selectionnées

    Paramètres :
        images_list               : Liste des images à fusionnées
        output_file               : L'image de sortie fusionnée et découpé
        no_data_value             : La valeur du no data de l'image de sortie
        epsg                      : L'EPSG de projection demandé pour l'image de sortie
        save_results_intermediate : Si faux suppresion des fichiers temporaires, par défaut False
        format_raster             : Format de l'image de sortie (GTiff, HFA...), par défaut GTiff
        ext_txt                   : extension du fichier texte contenant la liste des fichiers a merger

     Sortie :
        L'image fusionnée et découpée

    """
    debug = 1
    if debug >= 3:
        print(cyan + "assemblyImages() : Début de l'assemblage des images" + endC)
        print(cyan + "assemblyImages : " + endC + "image de sortie : " + str(output_file) + endC)
        print(cyan + "assemblyImages : " + endC + "valeur de nodata : " + str(no_data_value) + endC)
        print(cyan + "assemblyImages : " + endC + "epsg : " + str(epsg) + endC)

    # Fichier temporaire mergé
    file_name = os.path.splitext(os.path.basename(output_file))[0]
    merge_file_tmp = output_file

    if os.path.exists(merge_file_tmp):
        removeFile(merge_file_tmp)

    if os.path.exists(output_file):
        removeFile(output_file)

    repertory_temp = os.path.dirname(output_file)

    # Fichier txt temporaire liste des fichiers a merger
    list_file_tmp = repertory_temp + os.sep + file_name + ext_txt
    for imagefile in images_list:
        appendTextFileCR(list_file_tmp, imagefile)

    # Récupération de la résolution du raster d'entrée
    pixel_size_x, pixel_size_y = getPixelWidthXYImage(images_list[0])

    # Utilisation de la commande gdal_merge pour fusioner les fichiers image source
    # Pour les parties couvertes par plusieurs images, l'image retenue sera la dernière mergée

    cmd_merge = "gdal_merge" + getExtensionApplication() + " -of " + format_raster + " -ps " + str(pixel_size_x) + " " + str(pixel_size_y) + " -n " + str(no_data_value) + " -o "  + merge_file_tmp + " --optfile " + list_file_tmp
    print(cmd_merge)
    exit_code = os.system(cmd_merge)
    if exit_code != 0:
        raise NameError (bold + red + "!!! Une erreur c'est produite au cours du merge des images. Voir message d'erreur."  + endC)

    if debug >= 3:
        print(cyan + "assemblyImages : Fin de l'assemblage des images" + endC)

    # Si le fichier de sortie mergé a perdu sa projection on force la projection à la valeur par defaut
    epsg_ima, _ = getProjectionImage(merge_file_tmp)
    if epsg_ima == None or epsg_ima == 0:
        if epsg != 0 :
            updateReferenceProjection(None, merge_file_tmp, int(epsg))
        else :
            raise NameError (bold + red + "!!! Erreur les fichiers images d'entrée n'ont pas de projection défini et vous n'avez pas défini de projection (EPSG) en parametre d'entrée."  + endC)

    if not save_results_intermediate:
        if os.path.exists(list_file_tmp):
            removeFile(list_file_tmp)
    return

