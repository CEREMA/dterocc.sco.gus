#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT DE RECHERCHE ET DE DECOUPAGE D'IMAGE RASTER SELON UN MASQUE VECTEUR                                                                #
#                                                                                                                                           #
#############################################################################################################################################

"""
Nom de l'objet : ImagesAssembly.py
Description    :
-------------
Objectif   : Assemble et/ou découpe des images raster

Date de creation : 07/06/2023
"""
# Import des bibliothèques python
from __future__ import print_function
import os, sys, glob
from os import chdir
from osgeo import gdal, ogr
from osgeo.gdalconst import *
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_vector import getEmpriseFile, createEmpriseShapeReduced
from Lib_raster import getPixelWidthXYImage, changeDataValueToOtherValue, getProjectionImage, updateReferenceProjection, roundPixelEmpriseSize, cutImageByVector, getNodataValueImage, getDataTypeImage, getEmpriseImage
from Lib_file import removeVectorFile, removeFile
from Lib_text import appendTextFileCR


debug = 3

#########################################################################
# FONCTION assembleRasters()                                            #
#########################################################################
def assembleRasters(empriseVector, repRasterAssemblyList, output_rasterAssembly, format_raster = 'GTiff', format_vector = 'GPKG', ext_list = ['tif','TIF','tiff','TIFF','ecw','ECW','jp2','JP2','asc','ASC'], rewrite = True, save_results_intermediate = False):
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
    empr_xmin,empr_xmax,empr_ymin,empr_ymax = getEmpriseFile(empriseVector, format_vector=format_vector)

    repRasterAssembly_str = ""

    # Recherche des images dans l'emprise du vecteur
    for repertory in repRasterAssemblyList:
        images_find_list, images_error_list = findImagesFile(repertory, ext_list, empr_xmin, empr_xmax, empr_ymin, empr_ymax)
        repRasterAssembly_str += str(repertory) + "  "

    # Création d'un dossier temporaire où on va stocker tous les fichiers temporaires
    repertory_assembly_output = os.path.dirname(image_output)
    repertory_temp = repertory_assembly_output + os.sep + FOLDER_ASSEMBLY_TEMP

    # Création du répertoire temporaire si il n'existe pas
    if not os.path.isdir(repertory_temp):
        os.makedirs(repertory_temp)

    # Nettoyage du répertoire temporaire si il n'est pas vide
    cleanTempData(repertory_temp)

    # Utilisation d'un fichier temporaire pour  l'assemblage
    file_name = os.path.splitext(os.path.basename(output_rasterAssembly))[0]
    extension = os.path.splitext(output_rasterAssembly)[1]
    file_out_suffix_merge = "_merge"
    merge_file_tmp = repertory_temp + os.sep + file_name + file_out_suffix_merge + extension

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

    if os.path.exists(merge_file_tmp):
        os.remove(merge_file_tmp)

    if len(images_find_list) > 0 and os.path.isfile(images_find_list[0]) :
        epsg = getProjectionImage(images_find_list[0])[0]
        no_data_value = getNodataValueImage(images_find_list[0])
        data_type = getDataTypeImage(images_find_list[0])
        if no_data_value == None :
            no_data_value = 0
    else :
        print(bold + red + "Erreur il n'y a pas de fichier image correspondant à l'emprise dans le(s) répertoire(s) : %s!!!" %(repRasterAssembly_str) + endC)
        return -1

    # Assembler les images trouvées
    assemblyImages(repertory_temp, images_find_list, merge_file_tmp, no_data_value , epsg , save_results_intermediate, format_raster = format_raster)


    # Découpage du fichier image assemblé par l'emprise
    print(merge_file_tmp)
    if os.path.exists(merge_file_tmp) :
        cutImageByVector(empriseVector, merge_file_tmp, output_rasterAssembly, no_data_value = no_data_value, epsg= epsg, format_vector= format_vector)
    else :
        print(bold + red + "Erreur il n'y a pas de fichier assemblé %s à découper !!!" %(output_rasterAssembly) + endC)
        return -1

    # Suppression du fichier temporaire
    if not save_results_intermediate:
        if os.path.exists(merge_file_tmp):
            removeFile(merge_file_tmp)

    return 0

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
            raise NameError (bold + red + "!!! Erreur les fichiers images d'entrée non pas de projection défini et vous n'avez pas défini de projection (EPSG) en parametre d'entrée."  + endC)

    if not save_results_intermediate:
        if os.path.exists(list_file_tmp):
            removeFile(list_file_tmp)
    return

#########################################################################
# FONCTION cutImageByVector()                                           #
#########################################################################
def cutImageByVector(cut_shape_file ,input_image, output_image, pixel_size_x=None, pixel_size_y=None, no_data_value=0, epsg=0, format_raster="GTiff", format_vector='ESRI Shapefile'):
    """
    Rôle :
        Cette fonction découpe une image (.tif) par un vecteur (.shp)

    Paramètres :
           cut_shape_file : le nom du shapefile de découpage (exple : "/chemin/path_clipper.shp"
           input_image    : le nom de l'image à traiter (exmple : "/users/images/image_raw.tif")
           output_image   : le nom de l'image resultat découpée (exmple : "/users/images/image_cut.tif")
           pixel_size_x   : taille du pixel de sortie en x
           pixel_size_y   : taille du pixel de sortie en y
           no_data_value  : valeur de l'image d'entrée à transformer en NoData dans l'image de sortie
           epsg           : valeur de la projection par défaut 0, si à 0 c'est la valeur de projection du fichier raster d'entrée qui est utilisé automatiquement
           format_raster  : le format du fichier de sortie, par defaut : 'GTiff'
           format_vector  : format du fichier vecteur, par defaut : 'ESRI Shapefile'

    Sortie :
           True si l'operataion c'est bien passé, False sinon
    """

    if debug >= 3:
        print(cyan + "cutImageByVector() : Vecteur de découpe des l'image : " + cut_shape_file + endC)
        print(cyan + "cutImageByVector() : L'image à découper : " + input_image + endC)

    # Constante
    EPSG_DEFAULT = 2154

    ret = True

    # Récupération de la résolution du raster d'entrée
    if pixel_size_x == None or pixel_size_y == None :
        pixel_size_x, pixel_size_y = getPixelWidthXYImage(input_image)


    if debug >= 5:
        print("Taille des pixels : ")
        print("pixel_size_x = " + str(pixel_size_x))
        print("pixel_size_y = " + str(pixel_size_y))
        print("\n")

    # Récuperation de l'emprise de l'image
    ima_xmin, ima_xmax, ima_ymin, ima_ymax = getEmpriseImage(input_image)

    if debug >= 5:
        print("Emprise raster : ")
        print("ima_xmin = " + str(ima_xmin))
        print("ima_xmax = " + str(ima_xmax))
        print("ima_ymin = " + str(ima_ymin))
        print("ima_ymax = " + str(ima_ymax))
        print("\n")

    # Récuperation de la projection de l'image
    if epsg == 0:
        epsg_proj, _ = getProjectionImage(input_image)
    else :
        epsg_proj = epsg
    if epsg_proj == 0:
        epsg_proj = EPSG_DEFAULT

    if debug >= 3:
        print(cyan + "cutImageByVector() : EPSG : " + str(epsg_proj) + endC)

    # Identification de l'emprise de vecteur de découpe
    empr_xmin, empr_xmax, empr_ymin, empr_ymax = getEmpriseFile(cut_shape_file, format_vector)
    if debug >= 5:
        print("Emprise vector : ")
        print("empr_xmin = " + str(empr_xmin))
        print("empr_xmax = " + str(empr_xmax))
        print("empr_ymin = " + str(empr_ymin))
        print("empr_ymax = " + str(empr_ymax))
        print("\n")

    # Calculer l'emprise arrondi
    xmin, xmax, ymin, ymax = roundPixelEmpriseSize(pixel_size_x, pixel_size_y, empr_xmin, empr_xmax, empr_ymin, empr_ymax)

    if debug >= 5:
        print("Emprise vecteur arrondi a la taille du pixel : ")
        print("xmin = " + str(xmin))
        print("xmax = " + str(xmax))
        print("ymin = " + str(ymin))
        print("ymax = " + str(ymax))
        print("\n")

    # Trouver l'emprise optimale
    opt_xmin = xmin
    opt_xmax = xmax
    opt_ymin = ymin
    opt_ymax = ymax

    if ima_xmin > xmin :
        opt_xmin = ima_xmin
    if ima_xmax < xmax :
        opt_xmax = ima_xmax
    if ima_ymin > ymin :
        opt_ymin = ima_ymin
    if ima_ymax < ymax :
        opt_ymax = ima_ymax

    if debug >= 5:
        print("Emprise retenu : ")
        print("opt_xmin = " + str(opt_xmin))
        print("opt_xmax = " + str(opt_xmax))
        print("opt_ymin = " + str(opt_ymin))
        print("opt_ymax = " + str(opt_ymax))
        print("\n")

    # Découpage grace à gdal
    command = 'gdalwarp -t_srs EPSG:%s  -te %s %s %s %s -tap -multi -wo "NUM_THREADS=ALL_CPUS" -tr %s %s -dstnodata %s -cutline %s -overwrite -of %s %s %s' %(str(epsg_proj), opt_xmin, opt_ymin, opt_xmax, opt_ymax, pixel_size_x, pixel_size_y, str(no_data_value), cut_shape_file, format_raster, input_image, output_image)

    if debug >= 4:
        print(command)

    exit_code = os.system(command)
    if exit_code != 0:
        print(command)
        print(cyan + "cutImageByVector() : " + bold + red + "!!! Une erreur c'est produite au cours du decoupage de l'image : " + input_image + ". Voir message d'erreur." + endC, file=sys.stderr)
        ret = False

    else :
        if debug >= 4:
            print(cyan + "cutImageByVector() : L'image résultat découpée : " + output_image + endC)

    return ret

