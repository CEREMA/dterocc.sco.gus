#Import des bibliothèques python
import os, sys
from os import chdir
from osgeo import gdal, ogr
from osgeo.gdalconst import *

#Import des librairies de /libs
from libs.Lib_display import bold,red,cyan,endC
from libs.Lib_raster import  getProjectionImage, cutImageByVector, getNodataValueImage
from libs.Lib_file import removeFile

#debug = 3 pour afficher les états de debug

#########################################################################
# FONCTION mnhCreation()                                                #
#########################################################################
def mnhCreation(file_mns, file_mnt, file_out_mnh, empriseVector, img_origine, epsg = 2154,  nivellement = True, format_raster = 'GTiff', format_vector = 'GPKG',  overwrite = True, save_intermediate_results = False):
    """
    Rôle : calculer le MNH à partir d'un MNS et d'un MNT en entrée

    Paramètres :
        file_mns : couche raster du MNS
        file_mnt : couche raster du MNT
        file_out_mnh : couche raster du MNH en sortie
        empriseVector : fichier vecteur emprise de la zone d'étude
        img_origine : image d'origine
        epsg : epsg dans lequel on travaille, par défaut : 2154
        nivellement : réhaussement des valeurs négatives du MNH à 0. Par défaut : True
        format_raster : format de la donnée raster. Par défaut : GTiff
        format_vector : format de la donnée vecteur. Par défaut : GPKG
        overwrite : ré-écriture des fichiers. Par défaut : True
        save_intermediate_results : sauvegarde des résultats intermédiaire. Par défaut : False
    """
    if debug >= 3:
        print(cyan + "MnhCreation() : Début de la sélection des dossiers images" + endC)
        print(cyan + "MnhCreation() : " + endC + "MNS : " + str(file_mns) + endC)
        print(cyan + "MnhCreation() : " + endC + "MNT : " + str(file_mnt) + endC)
        print(cyan + "MnhCreation() : " + endC + "Emprise zone d'étude : " + str(empriseVector) + endC)
        print(cyan + "MnhCreation() : " + endC + "Image en entrée : " + str(img_origine) + endC)
        print(cyan + "MnhCreation() : " + endC + "Nivellement : " + str(nivellement) + endC)
        print(cyan + "MnhCreation() : " + endC + "Format raster : " + str(format_raster) + endC)
        print(cyan + "MnhCreation() : " + endC + "Formar vecteur : " + str(format_vector) + endC)
        print(cyan + "MnhCreation() : " + endC + "Sauvegarde des résultats intermédiaires : " + str(save_intermediate_results) + endC)

    # Récupération de la valeur nodata du mns
    nodatavalue = getNodataValueImage(file_mns)

    repertory_output = os.path.dirname(file_out_mnh)
    file_name = os.path.splitext(os.path.basename(file_mns))[0]
    extension = os.path.splitext(file_out_mnh)[1]

    # Préparation des fichiers temporaires
    #pour le MNS
    file_out_suffix_mns = "_preprocess"
    mns_file_tmp = repertory_output + os.sep + file_name + file_out_suffix_mns + extension

    #pour le MNT
    file_name = os.path.splitext(os.path.basename(file_mnt))[0]
    file_out_suffix_mnt = "_preprocess"
    mnt_file_tmp = repertory_output + os.sep + file_name + file_out_suffix_mnt + extension

    #pour le MNH
    file_name = os.path.splitext(os.path.basename(file_out_mnh))[0]
    file_out_suffix_mnh_ini = "_ini"
    mnhini_file_tmp = repertory_output + os.sep + file_name + file_out_suffix_mnh_ini + extension

    file_name = os.path.splitext(os.path.basename(file_out_mnh))[0]
    file_out_suffix_mnh_cut = "_cut"
    mnh_cut_file_tmp = repertory_output + os.sep + file_name + file_out_suffix_mnh_cut + extension

    file_out_suffix_mnh_si = "_resample"
    mnh_si_file_tmp = repertory_output + os.sep + file_name + file_out_suffix_mnh_si + extension

    file_out_suffix_mnh_fill = "_fill"
    mnh_fill_file_tmp = repertory_output + os.sep + file_name + file_out_suffix_mnh_fill + extension

    # Préparation du MNS
    print(cyan + "MnhCreation : Début du preprocessing du MNS" + endC)
    mnsPrepare(file_mns, mns_file_tmp, epsg, save_intermediate_results = save_intermediate_results)
    print(cyan + "MnhCreation : Fin du preprocessing du MNS" + endC)

    # Préparation du MNT
    print(cyan + "MnhCreation : Début du preprocessing du MNT" + endC)
    mntPrepare(file_mnt, mnt_file_tmp, epsg, mns_file_tmp, save_intermediate_results = save_intermediate_results)
    print(cyan + "MnhCreation : Fin du preprocessing du MNS" + endC)

    # Calcul du MNH
    print(cyan + "MnhCreation : Début calcul du MNH" + endC)
    cmd_mnh = 'otbcli_BandMathX -il %s %s -out %s -exp "im1-im2"' %(mns_file_tmp, mnt_file_tmp, mnhini_file_tmp)
    exit_code = os.system(cmd_mnh)
    if exit_code != 0:
        raise NameError (bold + red + "!!! Une erreur c'est produite au cours du calcul du MNH. Voir message d'erreur."  + endC)

    if debug >= 3:
        print(cyan + "MnhCreation : Fin du calcul du MNH" + endC)


    # Ré-échantillonnage du MNH sur l'image de base
    print(cyan + "MnhCreation : Début du ré-échantillonnage du MNH" + endC)

    cmd_superimpose = 'otbcli_Superimpose -inr %s -inm %s -out %s' %(img_origine, mnhini_file_tmp, mnh_si_file_tmp)
    exit_code = os.system(cmd_superimpose)
    if exit_code != 0:
        raise NameError (bold + red + "!!! Une erreur c'est produite au cours du super impose du MNH. Voir message d'erreur."  + endC)

    if debug >= 3:
        print(cyan + "MnhCreation : Fin du ré-échantillonnage" + endC)

    # Choix du nivellement à 0: oui ou non
    if nivellement:

        print(cyan + "MnhCreation : Début nivellement à 0 des valeurs de hauteurs négatives" + endC)
        # Remplacement des valeurs <0 par 0
        cmd_mnhfinal = 'otbcli_BandMath -il %s -out %s -exp "im1b1<0?0:im1b1"' %(mnh_si_file_tmp, mnh_fill_file_tmp)
        exit_code = os.system(cmd_mnhfinal)
        if exit_code != 0:
            raise NameError (bold + red + "!!! Une erreur c'est produite au cours du remplacement des valeurs négatives du MNH. Voir message d'erreur."  + endC)
        if debug >= 3:
            print(cyan + "MnhCreation : Fin du nivellement et fin de la création du MNH" + endC)

        print(cyan + "MnhCreation : Début du découpage du MNH à partir de l'emprise de la zone d'étude" + endC)
        # Découpe du MNH suivant la zone d'emprise
        cutImageByVector(empriseVector, mnh_fill_file_tmp, file_out_mnh, no_data_value = nodatavalue, epsg = epsg, format_vector = format_vector)
        print(cyan + "MnhCreation : Fin du découpage du MNH à partir de l'emprise de la zone d'étude" + endC)

    else:
        print(cyan + "MnhCreation : Début du découpage du MNH à partir de l'emprise de la zone d'étude" + endC)
        # Découpe du MNH suivant la zone d'emprise
        cutImageByVector(empriseVector, mnh_si_file_tmp, file_out_mnh, no_data_value = nodatavalue, epsg= epsg, format_vector= format_vector)
        print(cyan + "MnhCreation : Fin du découpage du MNH à partir de l'emprise de la zone d'étude" + endC)

    # Suppression des fichiers temporaires
    if not save_intermediate_results:
        if os.path.exists(mns_file_tmp):
            removeFile(mns_file_tmp)

        if os.path.exists(mnt_file_tmp):
            removeFile(mnt_file_tmp)

        if os.path.exists(mnhini_file_tmp):
            removeFile(mnhini_file_tmp)

        if os.path.exists(mnh_si_file_tmp):
            removeFile(mnh_si_file_tmp)

        if os.path.exists(mnh_cut_file_tmp):
            removeFile(mnh_cut_file_tmp)

    print(cyan + "MnhCreation : Création du MNH terminée" + endC)

    return file_out_mnh

#########################################################################
# FONCTION mnsPrepare()                                                 #
#########################################################################
def mnsPrepare(file_mns_in, file_mns_out, epsg, md_value = 100, format_raster = 'GTiff', save_intermediate_results = False):
    """
    Rôle : prépare la donnée MNS

    Paramètres :
        file_mns_in : fichier mns à traiter
        file_mns_out : fichier mns de sortie, après traitements
        epsg : epsg dans lequel on travail
        md_value : paramètre d'interpolation correspondant à la distance maximale avec laquelle l'algorithm va chercher à interpoler ses valeurs. Par défaut : 100
        format_raster : format de la donnée mns. Par défaut : GTiff
        save_intermediate_results : variable si sauvegarde ou non des résultats intermédiaires. Par défaut : False
    """

    if os.path.exists(file_mns_out):
        removeFile(file_mns_out)

    # Utilisation de fichiers temporaires pour  l'interpolation
    repertory_output = os.path.dirname(file_mns_out)
    file_name = os.path.splitext(os.path.basename(file_mns_out))[0]
    extension = os.path.splitext(file_mns_out)[1]
    file_out_suffix_interpol = "_interpol"
    interpol_file_tmp = repertory_output + os.sep + file_name + file_out_suffix_interpol + extension

    if os.path.exists(interpol_file_tmp):
        removeFile(interpol_file_tmp)

    #Interpolation
    cmd_interpol = 'gdal_fillnodata.py -md %s %s %s' %(md_value, file_mns_in, interpol_file_tmp)

    exit_code = os.system(cmd_interpol)
    if exit_code != 0:
        raise NameError (bold + red + "!!! Une erreur c'est produite au cours de l'interpolation du MNS. Voir message d'erreur."  + endC)

    if debug >= 3:
        print(cyan + "mnsPrepare : Fin de l'interpolation" + endC)


    #Reprojection
    cmd_reproj = 'gdalwarp -t_srs EPSG:'+ str(epsg) +' %s %s' %(interpol_file_tmp, file_mns_out)
    print(cmd_reproj)
    exit_code = os.system(cmd_reproj)
    if exit_code != 0:
        raise NameError (bold + red + "!!! Une erreur c'est produite au cours de la reprojection du MNS. Voir message d'erreur."  + endC)

    if debug >= 3:
        print(cyan + "mnsPrepare : Fin de la reprojection et donc de la préparation du MNS" + endC)

    if not save_intermediate_results:
        if os.path.exists(interpol_file_tmp):
            removeFile(interpol_file_tmp)
    return

#########################################################################
# FONCTION mntPrepare()                                                 #
#########################################################################
def mntPrepare(file_mnt_in, file_mnt_out, epsg, file_superimpose, md_value = 100, format_raster = 'GTiff', save_intermediate_results = False):
    """
    Rôle : prépare la donnée MNT

    Paramètres :
        file_mnt_in : fichier MNT à traiter
        file_mnt_out : fichier MNT de sortie, après traitements
        epsg : epsg
        file_superimpose : fichier pour échantillonner et stacker le MNT aux mêmes dimensions que le MNS
        md_value : paramètre d'interpolation correspondant à la distance maximale avec laquelle l'algorithm va chercher à interpoler ses valeurs, par défaut : 100
        format_raster : format de la donnée mns, par défaut : GTiff
        save_intermediate_results : variable si sauvegarde ou non des résultats intermédiaires, par défaut : False
    """

    if os.path.exists(file_mnt_out):
        removeFile(file_mnt_out)

    # Utilisation de fichiers temporaires pour  l'interpolation
    repertory_output = os.path.dirname(file_mnt_out)
    file_name = os.path.splitext(os.path.basename(file_mnt_out))[0]
    extension = os.path.splitext(file_mnt_out)[1]
    file_out_suffix_interpol = "_interpol"
    interpol_file_tmp = repertory_output + os.sep + file_name + file_out_suffix_interpol + extension

    if os.path.exists(interpol_file_tmp):
        removeFile(interpol_file_tmp)

    #Interpolation
    cmd_interpol = 'gdal_fillnodata.py -md %s %s %s' %(md_value, file_mnt_in, interpol_file_tmp)

    exit_code = os.system(cmd_interpol)
    if exit_code != 0:
        raise NameError (bold + red + "!!! Une erreur c'est produite au cours de l'interpolation du MNT. Voir message d'erreur."  + endC)

    if debug >= 3:
        print(cyan + "mntPrepare : Fin de l'interpolation" + endC)


    # Vérification de la projection du fichier MNT
    epsg_mnt = getProjectionImage(interpol_file_tmp)[0]
    if epsg_mnt != epsg :
        # Utilisation de fichiers temporaires pour  la reprojection
        file_out_suffix_reproj = "_reproj_EPSG" + str(epsg)
        reproj_file_tmp = repertory_output + os.sep + file_name + file_out_suffix_reproj + extension

        if os.path.exists(interpol_file_tmp):
            removeFile(reproj_file_tmp)

        #Reprojection
        cmd_reproj = 'gdalwarp -t_srs EPSG:'+ str(epsg) +' %s %s' %(interpol_file_tmp, reproj_file_tmp)

        exit_code = os.system(cmd_reproj)
        if exit_code != 0:
            raise NameError (bold + red + "!!! Une erreur c'est produite au cours de la reprojection du MNT. Voir message d'erreur."  + endC)

        if debug >= 3:
            print(cyan + "mnsPrepare : Fin de la reprojection du MNT" + endC)

    # SuperImpose sur le MNS
    cmd_superimpose = 'otbcli_Superimpose -inr %s -inm %s -out %s' %(file_superimpose, reproj_file_tmp, file_mnt_out)

    exit_code = os.system(cmd_superimpose)
    if exit_code != 0:
        raise NameError (bold + red + "!!! Une erreur c'est produite au cours du super impose du MNT. Voir message d'erreur."  + endC)

    if debug >= 3:
        print(cyan + "mnsPrepare : Fin du superimpose du MNT" + endC)

    if not save_intermediate_results:
        if os.path.exists(interpol_file_tmp):
            removeFile(interpol_file_tmp)
        if os.path.exists(reproj_file_tmp):
            removeFile(reproj_file_tmp)

    return
