#!/usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.               #
#############################################################################

# Import des librairies Python
import os,sys,glob, time,  multiprocessing
from osgeo import ogr

# Import des librairies de /libs
from Lib_display import bold,red,yellow,cyan,endC
from CrossingVectorRaster import statisticsVectorRaster
from Lib_operator import getNumberCPU
from Lib_raster import rasterizeVector, filterBinaryRaster, rasterizeBinaryVector, polygonizeRaster, cutImageByVector
from Lib_file import removeFile, removeVectorFile
from Lib_vector import createPolygonsFromGeometryList, fusionVectors, getEmpriseVector, createEmpriseVector, getProjection
from Lib_postgis import readTable, executeQuery, addColumn, addUniqId, addIndex, addSpatialIndex, dropTable, dropColumn, exportVectorByOgr2ogr, importVectorByOgr2ogr, closeConnection, topologyCorrections

###########################################################################################################################################
# FONCTION vegetationMask()                                                                                                               #
###########################################################################################################################################
def vegetationMask(dic_ndvi, img_ref, img_output, dic_ndvi_threshold , overwrite = False, save_intermediate_result = False):
    """
    Rôle : créé un masque de végétation à partir d'une image classifiée

    Paramètres :
        img_input : dictionnaire des images NDVI
        img_output : image binaire : 1 pour la végétation et -1 pour non végétation
        ndvi_threshold : seuil ndvi pour détecter la végétation
        overwrite : paramètre de ré-écriture, par défaut : False
    """

    ndvi_summer = dic_ndvi["ndvi_summer"]
    ndvi_winter = dic_ndvi["ndvi_winter"]

    ndvi_threshold_summer = dic_ndvi_threshold["threshold_summer"]
    ndvi_threshold_winter = dic_ndvi_threshold["threshold_winter"]
    #ndvi_threshold_min_veg_summer = dic_ndvi_threshold["threshold_min_vegetation_summer"]
    #ndvi_threshold_min_veg_winter = dic_ndvi_threshold["threshold_min_vegetation_winter"]
    umc_pixels = dic_ndvi_threshold["umc_pixels"]

    vegetation = os.path.splitext(img_output)[0] + '_tmp' + os.path.splitext(img_output)[1]
    #vegetation_remplie = os.path.splitext(img_output)[0] + 'gdal_tmp' + os.path.splitext(img_output)[1]
    #mask_rpg = os.path.splitext(img_output)[0] + '_rpg_tmp' + os.path.splitext(img_output)[1]
    mask_ndvi = os.path.splitext(img_output)[0] + '_ndvi_tmp' + os.path.splitext(img_output)[1]
    #non_vegetation = os.path.splitext(img_output)[0] + '_non_veg_tmp' + os.path.splitext(img_output)[1]

    # Verification de la non existence du fichier de sortie
    if overwrite == True and os.path.exists(img_output):
        os.remove(img_output)
    elif overwrite == False and os.path.exists(img_output):
        raise NameError(bold + red + "vegetationMaskNdvi() : le fichier %s existe déjà" %(img_output)+ endC)

    # Calculs à l'aide de l'otb

    # Création du masque avec un seuil sur les deux NDVI
    exp = '"(im1b1>=' + str(ndvi_threshold_summer) + ' || im2b1>=' + str(ndvi_threshold_winter) + ' ?1:0)"'
    cmd_mask = "otbcli_BandMath -il %s %s -out %s -exp %s" %(ndvi_summer, ndvi_winter, mask_ndvi, exp)

    exitCode = os.system(cmd_mask)

    if exitCode != 0:
        print(cmd_mask)
        raise NameError(bold + red + "vegetationMask() : une erreur est apparue lors de la création du masque de végétation (commande otbcli_BandMath)" + endC)
    '''
    # Création d'un masque sur le seuil en dessous duquel ce n'est forcément pas de la végétation
    exp = '"(im1b1>=' + str(ndvi_threshold_min_veg_summer) + ' && im2b1>=' + str(ndvi_threshold_min_veg_winter) + ' ?1:0)"'
    cmd_mask = "otbcli_BandMath -il %s %s -out %s -exp %s" %(ndvi_summer, ndvi_winter, non_vegetation, exp)

    exitCode = os.system(cmd_mask)

    if exitCode != 0:
        print(cmd_mask)
        raise NameError(bold + red + "vegetationMask() : une erreur est apparue lors de la création du masque de végétation (commande otbcli_BandMath)" + endC)
    '''

    # Création du masque du RPG
    #vegetationMaskRPG(dic_rpg, mask_rpg, img_ref, non_vegetation, overwrite, save_intermediate_result)

    # Somme du masque NDVI et du masque RPG pour compléter la détection de la végétation
    '''
    exp = '"(im1b1 + im2b1 >= 1 ? 1 : 0)"'
    cmd_mask = "otbcli_BandMath -il %s %s -out %s -exp %s" %(mask_ndvi, mask_rpg, vegetation, exp)

    exitCode = os.system(cmd_mask)

    if exitCode != 0:
        print(cmd_mask)
        raise NameError("une erreur est apparue lors de la création du masque de végétation (commande otbcli_BandMath)")
    '''

    #Remplissage des trous dans le masques
    command = "gdal_sieve.py -st %d -8 %s %s" %(umc_pixels, mask_ndvi, vegetation)

    exitCode = os.system(command)
    if exitCode != 0:
        raise NameError("Une erreur est apparue lors de la création du masque de végétation (commande gdal_sieve).")

    # On ne garde les trous remplis que dans la zone de végétation
    exp = '"(im1b1 + im2b1 >= 1 ? 1 : 0)"'
    cmd_mask = "otbcli_BandMath -il %s %s -out %s -exp %s" %(mask_ndvi, vegetation, img_output, exp)

    exitCode = os.system(cmd_mask)

    if exitCode != 0:
        print(cmd_mask)
        raise NameError("une erreur est apparue lors de la création du masque de végétation (commande otbcli_BandMath)")

    if not save_intermediate_result :
        removeFile(vegetation)
        removeFile(mask_ndvi)

    return

###########################################################################################################################################
# FONCTION vegetationMaskRPG()                                                                                                            #
###########################################################################################################################################
def vegetationMaskRPG(dic_rpg, raster_output, img_ref, mask_non_vegetation, overwrite = False, save_intermediate_result = False) :
    """
    Rôle : transforme le RPG (et le RPG complété si donné) en un raster binaire

    Paramètre :
        dic_rpg : dictionnaire contenant le rpg et le rpg complété
        raster_output : fichier raster de sortie binaire correspondant au RPG
        img_ref : image de référence Pléiades rvbpir
        mask_non_vegetation : image binaire avec à 0 les zones que l'on veut conserver en non végétation
        overwrite : paramètre de ré-écriture des fichiers. Par défaut : False
        save_intermediate_result : paramètre de sauvegarde des fichiers intermédiaire, par défaut : False
    """


    rpg = dic_rpg["rpg"]
    rpg_complete = dic_rpg["rpg_complete"]

    raster_rpg = os.path.splitext(raster_output)[0] + '_rasterRPG' + os.path.splitext(raster_output)[1]

    if overwrite == True and os.path.exists(raster_output):
        os.remove(raster_output)
    elif overwrite == False and os.path.exists(raster_output):
        raise NameError(bold + red + "rasterizeRPG() : le fichier %s existe déjà" %(raster_output)+ endC)


    if rpg_complete != "" and rpg_complete != None :

        output_rpg = os.path.splitext(raster_output)[0] + '_rpg' + os.path.splitext(raster_output)[1]
        output_rpg_complete = os.path.splitext(raster_output)[0] + '_rpg_complete' + os.path.splitext(raster_output)[1]

        rasterizeBinaryVector(rpg, img_ref, output_rpg, label=1, codage="uint8", ram_otb=0)
        rasterizeBinaryVector(rpg_complete, img_ref, output_rpg_complete, label=1, codage="uint8", ram_otb=0)

        exp = '"(im1b1 + im2b1 >= 1 ? 1 : 0)"'
        cmd_mask = "otbcli_BandMath -il %s %s -out %s -exp %s" %(output_rpg, output_rpg_complete, raster_rpg, exp)

        exitCode = os.system(cmd_mask)

        if exitCode != 0:
            print(cmd_mask)
            raise NameError("une erreur est apparue lors de la création du masque de végétation avec le RPG (commande otbcli_BandMath)")

        if not save_intermediate_result :
            removeFile(output_rpg)
            removeFile(output_rpg_complete)

    else :
        rasterizeBinaryVector(rpg, img_ref, raster_rpg, label=1, codage="uint8", ram_otb=0)

        # On retire les zones de non végétation au cas où le RPG en contient

    exp = '"(im1b1 * im2b1)"'
    cmd_mask = "otbcli_BandMath -il %s %s -out %s -exp %s" %(raster_rpg, mask_non_vegetation, raster_output, exp)

    exitCode = os.system(cmd_mask)

    if exitCode != 0:
        print(cmd_mask)
        raise NameError("une erreur est apparue lors de la création du masque de végétation (commande otbcli_BandMath)")

    if not save_intermediate_result :
        removeFile(raster_rpg)


###########################################################################################################################################
# FONCTION mnhTreeThreshold()                                                                                                             #
###########################################################################################################################################
def mnhTreeThreshold(mnh, mask_veg, mask_output, file_output, threshold = 10, umc_pixels = 2, save_intermediate_result = True, overwrite = True):
    """
    Rôle : applique un seuillage sur le MNH pour faire une première détection des arbres, créer un masque et un fichier vecteur

    Paramètre :
        mnh : image mnh
        mask_veg : masque de végétation
        mask_output : masque du seuillage
        file_output : fichier vecteur correspondant aux arbres détectés
        threshold : seuil pour détecter les arbres
        umc_pixels : taille des "trous" à remplir dans le masque
        save_intermediate_result : paramètre de sauvegarde des fichiers intermédiaire, par défaut : True
        overwrite : paramètre de ré-écriture des fichiers. Par défaut : False
    """

    repertory_output = os.path.dirname(mask_output)
    file_name = os.path.splitext(os.path.basename(mask_output))[0]
    extension = os.path.splitext(mask_output)[1]

    mask_mnh = repertory_output + os.sep + file_name + "_tmp" + extension
    mask_mnh_filled = repertory_output + os.sep + file_name + "_filled_tmp" + extension

    # Verification de la non existence du fichier de sortie
    if overwrite == True and os.path.exists(mask_output):
        os.remove(mask_output)
    elif overwrite == False and os.path.exists(mask_output):
        raise NameError(bold + red + "mnhTreeThreshold() : le fichier %s existe déjà" %(mask_output)+ endC)

    if overwrite == True and os.path.exists(file_output):
        os.remove(file_output)
    elif overwrite == False and os.path.exists(file_output):
        raise NameError(bold + red + "mnhTreeThreshold() : le fichier %s existe déjà" %(file_output)+ endC)

    # Calcul à l'aide de l'otb
    exp = '"(im1b1>=' + str(threshold) + ' ?1:0)"'
    cmd_mask = "otbcli_BandMath -il %s -out %s -exp %s" %(mnh, mask_mnh, exp)

    exitCode = os.system(cmd_mask)


    #Remplissage des trous dans le masques
    command = "gdal_sieve.py -st %d -8 %s %s" %(umc_pixels, mask_mnh, mask_mnh_filled)

    exitCode = os.system(command)
    if exitCode != 0:
        raise NameError("Une erreur est apparue lors de la création du masque de végétation (commande gdal_sieve).")


    if exitCode != 0:
        print(cmd_mask)
        raise NameError(bold + red + "mnhTreeThreshold() : une erreur est apparue lors de la création du masque du MNH (commande otbcli_BandMath)" + endC)

    exp = '"(im1b1 * im2b1)"'
    cmd_mask = "otbcli_BandMath -il %s %s -out %s -exp %s" %(mask_mnh_filled, mask_veg, mask_output, exp)

    exitCode = os.system(cmd_mask)

    if exitCode != 0:
        print(cmd_mask)
        raise NameError(bold + red + "mnhTreeThreshold() : une erreur est apparue lors de la création du masque du MNH (commande otbcli_BandMath)" + endC)

    polygonizeRaster(mask_output, file_output, 'arbore', field_name="id", vector_export_format="GPKG")

    if not save_intermediate_result :
        removeFile(mask_mnh)
        removeFile(mask_mnh_filled)



###########################################################################################################################################
# FONCTION segmentationImageVegetetation()                                                                                                #
###########################################################################################################################################
def segmentationImageVegetetation(img_ref, dic_ndvi, file_output, file_mnh, dic_ndvi_threshold, param_minsize = 10, format_vector='GPKG', save_intermediate_result = True, overwrite = True):
    """
    Rôle : segmente l'image en entrée à partir d'une fonction OTB_Segmentation MEANSHIFT

    Paramètre :
        img_ref : image de référence Pléiades rvbpir
        dic_ndvi : dictionnaire contenant les images ndvi
        file_output : fichier vecteur de sortie correspondant au résultat de segmentation
        param_minsize : paramètre de la segmentation : taille minimale des segments, par défaut : 10
        ndvi_threshold : seuil NDVI pour détecter la végétation
        format_vector : format du fichier vecteur de sortie, par défaut : GPKG
        save_intermediate_result : paramètre de sauvegarde des fichiers intermédiaire, par défaut : True
        overwrite : paramètre de ré-écriture des fichiers. Par défaut : False

    Sortie :
        file_output : couche vecteur de sortie correspondant au résultat de segmentation
    """

    # Utilisation d'un fichier temporaire pour la couche masque
    repertory_output = os.path.dirname(file_output)
    file_name = os.path.splitext(os.path.basename(img_ref))[0]
    extension = os.path.splitext(img_ref)[1]

    mask_veg = repertory_output + os.sep + file_name + "_mask_veg" + extension
    mask_ndvi = repertory_output + os.sep + file_name + "_mask_ndvi" + extension
    img_masked = repertory_output + os.sep + file_name + "_masked" + extension
    mask_mnh = repertory_output + os.sep + file_name + "_mnh_masked" + extension

    mnh_threshold_tree = 10

    if overwrite:
        if os.path.exists(mask_veg):
            os.remove(mask_veg)
        if os.path.exists(file_output):
            os.remove(file_output)

    # Création du masque de végétation
    vegetationMask(dic_ndvi, img_ref, mask_ndvi, dic_ndvi_threshold, overwrite, save_intermediate_result)

    # Création du masque MNH
    mnhTreeThreshold(dic_ndvi["mnh"], mask_ndvi, mask_mnh, file_mnh, mnh_threshold_tree, save_intermediate_result = True, overwrite = True)
    # Ajustement du masque de végétation

    exp = '"(im1b1 - im2b1)"'
    cmd_mask = "otbcli_BandMath -il %s %s -out %s -exp %s" %(mask_ndvi, mask_mnh, mask_veg, exp)

    exitCode = os.system(cmd_mask)

    if exitCode != 0:
        print(cmd_mask)
        raise NameError(bold + red + "segmentationImageVegetation() : une erreur est apparue lors de la création du masque de végétation (commande otbcli_BandMath)" + endC)

    cmd = "otbcli_BandMathX -il %s %s -out %s -exp 'im1 * im2b1'" %(img_ref, mask_veg, img_masked)

    exitCode = os.system(cmd)

    if exitCode != 0:
        print(cmd)
        raise NameError(bold + red + "segmentationVegetation() : une erreur est apparue lors de la création du masque de végétation (commande otbcli_BandMathX)." + endC)
    # Calcul de la segmentation Meanshift
    sgt_cmd = "otbcli_Segmentation -in %s -mode vector -mode.vector.out %s -mode.vector.inmask %s -filter meanshift  -filter.meanshift.minsize %s" %(img_masked, file_output, mask_veg, param_minsize)

    exitCode = os.system(sgt_cmd)

    if exitCode != 0:
        print(sgt_cmd)
        raise NameError(bold + red + "segmentationVegetation() : une erreur est apparue lors de la segmentation de l'image (commande otbcli_Segmentation)." + endC)

    if not save_intermediate_result:
        removeFile(mask_veg)
        removeFile(img_masked)
        removeFile(mask_ndvi)
        removeFile(mask_mnh)

    return

###########################################################################################################################################
# FONCTION classificationVerticalStratum()                                                                                                #
###########################################################################################################################################
def classificationVerticalStratum(connexion, connexion_dic, img_ref, output_layers, sgts_input, sgts_tree, raster_dic, tab_ref = 'segments_vegetation',dic_seuil = {"seuil_h1" : 3, "seuil_h2" : 1, "seuil_h3" : 2, "seuil_txt" : 11, "seuil_touch_arbo_vs_herba" : 15, "seuil_ratio_surf" : 25, "seuil_arbu_repres" : 20}, format_type = 'GPKG', save_intermediate_result = True, overwrite = False, debug = 0):
    """
    Rôle : classe les segments en trois strates : arborée, arbustive et herbacée

    Paramètres :

        connexion : correspond à la variable de connexion à la base de données
        connexion_dic : dictionnaire des paramètres de connexion selon le modèle : {"dbname" : 'projetgus', "user_db" : 'postgres', "password_db" : 'postgres', "server_db" : 'localhost', "port_number" : '5432', "schema" : ''}
        img_ref : image de référence Pléiades rvbpir
        output_layers : dictionnaire des couches vectorielles de sortie composé de quatres chemins : une pour chaque strate et un contenant toutes les strates
        sgts_input : fichier vecteur de segmentation
        raster_dic : dictionnaire associant le type de donnée récupéré avec le fichier raster contenant les informations, par exemple : {"mnh" : filename}
        tab_ref : nom de la table principale. Par défaut : 'segments_vegetation'
        dic_seuil : dictionnaire des seuils de hauteur, de texture, de surface. Le format {"seuil_h1" : 3, "seuil_h2" : 1, "seuil_h3" : 2, "seuil_txt" : 11, "seuil_touch_arbo_vs_herba" : 15, "seuil_ratio_surf" : 25, "seuil_arbu_repres" : 20}
        format_type : format de la donnée vecteur en entrée, par défaut : GPKG
        save_intermediate_result : paramètre de sauvegarde des fichiers intermédiaire. Par défaut : False
        overwrite : paramètre de ré-écriture des tables. Par défaut False
        debug : niveau de debug pour l'affichage des commentaires

    Sortie :
        file_output : couche vecteur de sortie correspondant au résultat de segmentation
    """

    # Rappel du paramétrage
    if debug >= 2 :
        print(cyan + "classificationVerticalStratum() : Début de la classification en strates verticales végétales" + endC)
        print(cyan + "classificationVerticalStratum : " + endC + "connexion_dic : " + str(connexion_dic) + endC)
        print(cyan + "classificationVerticalStratum : " + endC + "output_layers : " + str(output_layers) + endC)
        print(cyan + "classificationVerticalStratum : " + endC + "sgts_input : " + str(sgts_input) + endC)
        print(cyan + "classificationVerticalStratum : " + endC + "raster_dic : " + str(raster_dic) + endC)
        print(cyan + "classificationVerticalStratum : " + endC + "dic_seuil : " + str(dic_seuil) + endC)
        print(cyan + "classificationVerticalStratum : " + endC + "format_type : " + str(format_type) + endC)
        print(cyan + "classificationVerticalStratum : " + endC + "save_intermediate_result : " + str(save_intermediate_result) + endC)
        print(cyan + "classificationVerticalStratum : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "classificationVerticalStratum : " + endC + "files_output : " + str(output_layers) + endC)

    #####################################################################
    ## Création et export en base de la couche des segments végétation ##
    #####################################################################

    '''
    # Nettoyage en base si ré-écriture
    if overwrite == True:
        query ="""
        SELECT format('DROP TABLE %s.%s', table_schema, table_name)
        FROM information_schema.tables
        WHERE table_schema = '%s';
        """ %('%I', '%I',connexion_dic["schema"])
        cursor = connexion.cursor()
        cursor.execute(query)
        tables_schema = cursor.fetchall()
        for el in tables_schema:
            executeQuery(connexion, el[0])
    '''
    # Fichiers intermédiaires
    repertory_output = os.path.dirname(output_layers["output_stratesv"])
    file_name = os.path.splitext(os.path.basename(sgts_input))[0]
    extension_vecteur = os.path.splitext(output_layers["output_stratesv"])[1]

    #####################################################################
    ##    Collect des statistiques de hauteur et texture pour chaque   ##
    ##                             segment                             ##
    #####################################################################

    if debug >= 1:
        if dic_seuil["height_or_texture"] == "texture":
            print(bold + "Collecte des valeurs médianes de hauteur et de texture pour chaque segment." + endC)
        else :
            print(bold + "Collecte des valeurs médianes de hauteur pour chaque segment." + endC)

    start_time = time.time()

    sgts_tree_out = repertory_output + os.sep + file_name + "MNH_tree" + extension_vecteur
    list_vector_file_mnh = diviseVectorFile(sgts_tree, 'GPKG')
    calc_statMedian_multiprocessing(list_vector_file_mnh, raster_dic["MNH"], sgts_tree_out)
    #calc_statMedian(sgts_tree, raster_dic["MNH"], sgts_tree_out)
    tablename_tree = "mnhthreshold_trees"
    importVectorByOgr2ogr(connexion_dic["dbname"], sgts_tree_out, tablename_tree, user_name=connexion_dic["user_db"], password=connexion_dic["password_db"], ip_host=connexion_dic["server_db"], num_port=connexion_dic["port_number"], schema_name=connexion_dic["schema"],  epsg=str(2154))


    ## Collecte données de hauteur pour chaque segment
    file_mnh_out = repertory_output + os.sep + file_name + "MNH" + extension_vecteur

    if os.path.exists(file_mnh_out) and overwrite == True:
        os.remove(file_mnh_out)

    list_vector_file = diviseVectorFile(sgts_input, 'GPKG')

    # Calcul de la valeur médiane de hauteur pour chaque segment de végétation
    start_mnh = time.time()
    #calc_statMedian(sgts_input, raster_dic["MNH"], file_mnh_out)
    calc_statMedian_multiprocessing(list_vector_file, raster_dic["MNH"], file_mnh_out)
    time_mnh = time.time() - start_mnh

    # Export du fichier vecteur des segments végétation avec une valeur médiane de hauteur dans la BD
    tablename_mnh = "table_sgts_mnh"
    importVectorByOgr2ogr(connexion_dic["dbname"], file_mnh_out, tablename_mnh, user_name=connexion_dic["user_db"], password=connexion_dic["password_db"], ip_host=connexion_dic["server_db"], num_port=connexion_dic["port_number"], schema_name=connexion_dic["schema"], epsg=str(2154))

    ## Collecte données de texture pour chaque segment
    file_txt_out = repertory_output + os.sep + file_name + "TXT" + extension_vecteur

    if os.path.exists(file_txt_out) and overwrite == True:
        os.remove(file_txt_out)

    start_median = time.time()
    # Calcul de la valeur médiane de texture pour chaque segment de végétation
    tablename_txt = ''
    if dic_seuil["height_or_texture"] == "texture":
        #calc_statMedian(sgts_input, raster_dic["TXT"], file_txt_out)
        calc_statMedian_multiprocessing(list_vector_file, raster_dic["TXT"], file_txt_out)

        # Export du fichier vecteur des segments végétation avec une valeur médiane de texture dans la BD
        tablename_txt = "table_sgts_txt"
        importVectorByOgr2ogr(connexion_dic["dbname"], file_txt_out, tablename_txt, user_name=connexion_dic["user_db"], password=connexion_dic["password_db"], ip_host=connexion_dic["server_db"], num_port=connexion_dic["port_number"], schema_name=connexion_dic["schema"],  epsg=str(2154))
    time_median = time.time() - start_median

    # Supprimer le fichier si on ne veut pas les sauvegarder
    if len(list_vector_file) > 1 :
        for file_tmp in list_vector_file :
            removeVectorFile(file_tmp, 'ESRI Shapefile')

    if len(list_vector_file_mnh) > 1 :
        for file_tmp_mnh in list_vector_file_mnh :
            removeVectorFile(file_tmp_mnh, 'ESRI Shapefile')

    if not save_intermediate_result :
        os.remove(file_mnh_out)
        if dic_seuil["height_or_texture"] == "texture":
            os.remove(file_txt_out)


    # Merge des colonnes de statistiques en une seule table "segments_vegetation_ini"

    tab_sgt_ini = 'segments_vegetation_ini_t0'
    dropTable(connexion, tab_sgt_ini)

    if dic_seuil["height_or_texture"] == "texture":
        query = """
        CREATE TABLE %s AS
            SELECT t2.dn, t2.geom, t2.median AS mnh, t1.median AS txt
            FROM %s AS t1, %s AS t2
            WHERE t1.dn = t2.dn;
        """ %(tab_sgt_ini, tablename_txt, tablename_mnh)

    else :
        query = """
        CREATE TABLE %s AS
            SELECT t2.dn, t2.geom, t2.median AS mnh
            FROM  %s AS t2;
        """ %(tab_sgt_ini, tablename_mnh)

    # Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    # Traitement des artefacts au reflet blanc
    #tab_sgt_txt_val0 = 'segments_txt_val0'
    #query = """
    #CREATE TABLE %s AS
    #    SELECT *
    #    FROM %s
    #    WHERE txt = 0;
    #DELETE FROM %s WHERE txt = 0;
    #""" %(tab_sgt_txt_val0, tab_sgt_ini, tab_sgt_ini)
    # Exécution de la requête SQL
    #if debug >= 3:
    #    print(query)
    #executeQuery(connexion, query)

    # Suppression des deux tables txt et mnh
    if tablename_txt != '' :
        dropTable(connexion, tablename_txt)
    if tablename_mnh != '':
        dropTable(connexion, tablename_mnh)

    ######################################################################
    ## Prétraitements : transformation de l'ensemble des multipolygones ##
    ##                  en simples polygones ET suppression des         ##
    ##                  artefacts au reflet blanc                       ##
    ######################################################################

    if debug >= 2:
        print(bold + "Prétraitements : transformation de l'ensemble des multipolygones en simples polygones ET suppression des artefacts au reflet blanc" + endC)

    # Conversion en simples polygones
    tab_ref0 = tab_ref + "_ini"

    if dic_seuil["height_or_texture"] == "texture":
        query = """
        CREATE TABLE %s AS
            SELECT public.ST_MAKEVALID((public.ST_DUMP(t.geom)).geom::public.geometry(Polygon,2154)) as geom, t.mnh, t.txt
            FROM %s as t
        """ %(tab_ref0, tab_sgt_ini)

    else :
        query = """
        CREATE TABLE %s AS
            SELECT public.ST_MAKEVALID((public.ST_DUMP(t.geom)).geom::public.geometry(Polygon,2154)) as geom, t.mnh
            FROM %s as t
        """ %(tab_ref0, tab_sgt_ini)

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Ajout d'un identifiant unique
    #addUniqId(connexion, tab_ref0)

    # Ajout d'un index spatial
    addSpatialIndex(connexion, tab_ref0)

    #addIndex(connexion, tab_ref0, 'fid', 'idx_fid_'+tab_ref)

    # Ajout de l'attribut "strate"
    addColumn(connexion, tab_ref0, 'strate', 'varchar(100)')

    time_prepare = time.time() - start_time

    #if not save_intermediate_result:
    #    dropTable(connexion, tab_sgt_txt_val0)

    #####################################################################
    ## Première étape : classification générale, à partir de règles de ##
    ##                  hauteur et de texture                          ##
    #####################################################################

    start_time = time.time()

    if debug >= 2:
        print(bold + "Première étape : classification générale, à partir de règles de hauteur et de texture" + endC)

    if dic_seuil["height_or_texture"] == "height":
            query = """
            UPDATE %s as t SET strate = 'A' WHERE t.mnh  > %s;
            """ %(tab_ref0, dic_seuil["height_treeshrub_thr"])

            query += """
            UPDATE %s as t SET strate = 'Au' WHERE t.mnh  <= %s AND t.mnh > %s;
            """ %(tab_ref0, dic_seuil["height_treeshrub_thr"], dic_seuil["height_shrubgrass_thr"])

            query += """
            UPDATE %s as t SET strate = 'H' WHERE t.mnh <= %s;
            """ %(tab_ref0, dic_seuil["height_shrubgrass_thr"])


    else :
        query = """
        UPDATE %s as t SET strate = 'A' WHERE t.txt < %s AND t.mnh  > %s;
        """ %(tab_ref0, dic_seuil["texture_thr"],dic_seuil["height_treeshrub_thr"])

        query += """
        UPDATE %s as t SET strate = 'Au' WHERE t.txt < %s AND  t.mnh  <= %s;
        """ %(tab_ref0, dic_seuil["texture_thr"],dic_seuil["height_treeshrub_thr"])

        query += """
        UPDATE %s as t SET strate = 'H' WHERE t.txt  >= %s;
        """ %(tab_ref0, dic_seuil["texture_thr"])

    # query += """
    # UPDATE %s as t SET strate = 'H' WHERE t.txt < %s AND t.mnh <= %s;
    # """ %(tab_ref, dic_seuil["texture_thr"], dic_seuil["height_shrubgrass_thr"])

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)


    query = '''
    DROP TABLE IF EXISTS %s ;
    CREATE TABLE %s AS
        SELECT geom, mnh, txt, strate FROM %s
        UNION
        SELECT public.ST_MAKEVALID((public.ST_DUMP(geom)).geom::public.geometry(Polygon,2154)) as geom, median as mnh, 0 as txt, 'A' as strate FROM %s
    '''%(tab_ref, tab_ref, tab_ref0, tablename_tree)

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Ajout d'un identifiant unique
    addUniqId(connexion, tab_ref)

    # Ajout d'un index spatial
    addSpatialIndex(connexion, tab_ref)

    addIndex(connexion, tab_ref, 'fid', 'idx_fid_'+tab_ref)

    # Ajout de l'attribut "strate"
    # addColumn(connexion, tab_ref, 'strate', 'varchar(100)')

    if not save_intermediate_result :
        dropTable(connexion, tablename_tree)
        dropTable(connexion, tab_ref0)

    output_classif = repertory_output + os.sep + file_name + "_classif" + extension_vecteur
    exportVectorByOgr2ogr(connexion_dic["dbname"], output_classif, tab_ref, user_name = connexion_dic["user_db"], password = connexion_dic["password_db"], ip_host = connexion_dic["server_db"], num_port = connexion_dic["port_number"], schema_name = connexion_dic["schema"], format_type='GPKG')

    ##############################################################################
    ### ajout EB 01/11/24 : enregistrement fic intermediaires resultats 1ere etape = > a supprimer apres le test
    '''
    query = """
    DROP TABLE IF EXISTS sgts_strate_arboree;
    CREATE TABLE sgts_strate_arboree AS
        SELECT *
        FROM %s
        WHERE strate = 'A';
    """ %(tab_ref)
    executeQuery(connexion, query)
    exportVectorByOgr2ogr(connexion_dic["dbname"], '/mnt/RAM_disk/ProjetGUS/2-DistinctionStratesV/sgts_strate_arboree_1ere_etape.gpkg', 'sgts_strate_arboree', user_name = connexion_dic["user_db"], password = connexion_dic["password_db"], ip_host = connexion_dic["server_db"], num_port = connexion_dic["port_number"], schema_name = connexion_dic["schema"], format_type='GPKG')
    dropTable(connexion, 'sgts_strate_arboree')

    query = """
    DROP TABLE IF EXISTS sgts_strate_arbustive;
    CREATE TABLE sgts_strate_arbustive AS
        SELECT *
        FROM %s
        WHERE strate = 'Au';
    """ %(tab_ref)
    executeQuery(connexion, query)
    exportVectorByOgr2ogr(connexion_dic["dbname"], '/mnt/RAM_disk/ProjetGUS/2-DistinctionStratesV/sgts_strate_arbustive_1ere_etape.gpkg', 'sgts_strate_arbustive', user_name = connexion_dic["user_db"], password = connexion_dic["password_db"], ip_host = connexion_dic["server_db"], num_port = connexion_dic["port_number"], schema_name = connexion_dic["schema"], format_type='GPKG')
    dropTable(connexion, 'sgts_strate_arbustive')

    query = """
    DROP TABLE IF EXISTS sgts_strate_herbace;
    CREATE TABLE sgts_strate_herbace AS
        SELECT *
        FROM %s
        WHERE strate = 'H';
    """ %(tab_ref)
    executeQuery(connexion, query)
    exportVectorByOgr2ogr(connexion_dic["dbname"], '/mnt/RAM_disk/ProjetGUS/2-DistinctionStratesV/sgts_strate_herbacee_1ere_etape.gpkg', 'sgts_strate_herbace', user_name = connexion_dic["user_db"], password = connexion_dic["password_db"], ip_host = connexion_dic["server_db"], num_port = connexion_dic["port_number"], schema_name = connexion_dic["schema"], format_type='GPKG')
    dropTable(connexion, 'sgts_strate_herbace')
    '''

    time_1etape = time.time() - start_time
    ##############################################################################

    #####################################################################
    ## Deuxième étape : reclassification des segments arbustifs        ##
    #####################################################################
    if debug >= 2:
        print(bold + "Deuxième étape : reclassification des segments arbustifs" + endC)

    start_time = time.time()
    ###
    #0# Extraction de deux catégories de segments arbustifs :
    ###
      # - les segments "isolés" (ne touchant pas d'autres segments arbustifs)
      # - les segments  de "regroupement" (en contact avec d'autres segments arbustifs)

    if debug >= 2:
        print(bold + "Deuxième étape :\n0-Extraction des segments 'isolés' et des segments de 'regroupement'" + endC)

    # Préparation de trois tables : rgpt_arbu, arbu_de_rgpt, arbu_uniq
    tab_rgpt_arbu, tab_arbu_de_rgpt, tab_arbu_uniq = pretreatment_arbu(connexion, tab_ref, save_intermediate_result, debug)


    ###
    #1# Première phase de reclassification
    ###

    # 1.0# Reclassification des arbustes isolés selon leur hauteur
    if debug >= 2:
        print(bold + "Deuxième étape :\n1.0-Reclassification des arbustes isolés selon leur hauteur" + endC)

    tab_ref = reclassIsolatedSgtsByHeight(connexion, tab_ref, dic_seuil, save_intermediate_result, debug)

    tab_arbu_de_rgpt = 'arbu_de_rgpt'
    tab_arbu_uniq = 'arbu_uniq'
    tab_rgpt_arbu = 'rgpt_arbu'
    # il nous reste les segments arbustifs isolés qui n'ont pas pu être retraités par la hauteur

    # 1.1# Reclassification des segments arbustes "regroupés"
    if debug >= 2:
        print(bold + "Deuxième étape :\n1.1-Reclassification des segments arbustes 'regroupés'" + endC)

    reclassGroupSegments(connexion, tab_ref, tab_rgpt_arbu, dic_seuil, save_intermediate_result, debug)
    output_reclass1 = repertory_output + os.sep + file_name + "_reclass1" + extension_vecteur
    exportVectorByOgr2ogr(connexion_dic["dbname"], output_reclass1, tab_ref, user_name = connexion_dic["user_db"], password = connexion_dic["password_db"], ip_host = connexion_dic["server_db"], num_port = connexion_dic["port_number"], schema_name = connexion_dic["schema"], format_type='GPKG')

    # il nous reste les segments arbustifs de rgpts qui n'ont pas été reclassés par leur configuration
    # Suppression des tables intermédiaires
    dropTable(connexion, tab_rgpt_arbu)
    dropTable(connexion, tab_arbu_de_rgpt)
    dropTable(connexion, tab_arbu_uniq)

    tab_rgpt_arbu, tab_arbu_de_rgpt, tab_arbu_uniq = pretreatment_arbu(connexion, tab_ref, save_intermediate_result, debug)

    ###
    # 2# Deuxième phase de reclassification
    ###

    # 2.0# Reclassification des arbustes "isolés" selon un rapport de surface
    if debug >= 2:
        print(bold + "Deuxième étape :\n2.0-Reclassification des arbustes 'isolés' selon un rapport de surface" + endC)

    reclassIsolatedSgtsByAreaRatio(connexion,  tab_ref, tab_arbu_uniq, dic_seuil, save_intermediate_result, debug)

    # #2.1# Reclassification des arbustes "regroupés" entourés uniquement d'arboré selon un rapport de surface
    if debug >= 2:
        print(bold + "Deuxième étape :\n2.1-Reclassification des arbustes 'regroupés' entourés uniquement d'arboré selon un rapport de surface" + endC)

    tab_ref = reclassGroupSgtsByAreaRatio(connexion, tab_ref, tab_rgpt_arbu, tab_arbu_de_rgpt,  dic_seuil, save_intermediate_result, debug)
    output_reclass2 = repertory_output + os.sep + file_name + "_reclass2" + extension_vecteur
    exportVectorByOgr2ogr(connexion_dic["dbname"], output_reclass2, tab_ref, user_name = connexion_dic["user_db"], password = connexion_dic["password_db"], ip_host = connexion_dic["server_db"], num_port = connexion_dic["port_number"], schema_name = connexion_dic["schema"], format_type='GPKG')


    if not save_intermediate_result :
        dropTable(connexion, tab_rgpt_arbu)
        dropTable(connexion, tab_arbu_de_rgpt)
        dropTable(connexion, tab_arbu_uniq)

    # Ajout de la colonne pour la sauvegarde au format raster
    addColumn(connexion, tab_ref, 'strate_r', 'int')

    query = """
    UPDATE %s SET strate_r = 1 WHERE strate = 'A';
    UPDATE %s SET strate_r = 2 WHERE strate = 'Au';
    UPDATE %s SET strate_r = 3 WHERE strate = 'H';
    """ %(tab_ref, tab_ref, tab_ref)

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    ## Traitement des surfaces herbacé < à 20m2 et entouré de polygones de type arboré ou arbustif,
    ## si le MNH moyen est < à 1 on ne change rien si entre 1m et 3m on passe en arbustif et si > à 3m on passe en arboré
    '''
    # Calcul des surfaces herbacées < à 20m2
    query = """
    UPDATE %s
    SET
        strate =
            CASE
                WHEN mnh BETWEEN 1 AND 3 THEN 'Au'
                WHEN mnh > 3 THEN 'A'
                ELSE strate
            END
    WHERE
        strate = 'H' AND
        public.ST_Area(geom) < 20 AND
        (
            SELECT COUNT(*) FROM %s AS t
            WHERE
                public.ST_Touches(t.geom, %s.geom) AND
                t.strate IN ('Au', 'A')
        ) = (
            SELECT COUNT(*) FROM %s AS t
            WHERE
                public.ST_Touches(t.geom, %s.geom)
        );
    """ %(tab_ref, tab_ref, tab_ref, tab_ref, tab_ref)
    '''

    reclassificationOmbres(connexion, tab_ref, save_intermediate_result, debug)


    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    time_2etape = time.time() - start_time

    #############################################################
    ## Sauvegarde des résultats en tant que couche vectorielle ##
    #############################################################
    if output_layers == {}  :
        print(yellow + bold + "Attention : Il n'y a pas de sauvegarde en couche vecteur du résultat de classification. Vous n'avez pas fourni de chemin de sauvegarde." + endC)
    if output_layers["tree"] != '' :
        query = """
        DROP TABLE IF EXISTS sgts_strate_arboree;
        CREATE TABLE sgts_strate_arboree AS
            SELECT *
            FROM %s
            WHERE strate = 'A';
        """ %(tab_ref)
        executeQuery(connexion, query)
        exportVectorByOgr2ogr(connexion_dic["dbname"], output_layers["tree"], 'sgts_strate_arboree', user_name = connexion_dic["user_db"], password = connexion_dic["password_db"], ip_host = connexion_dic["server_db"], num_port = connexion_dic["port_number"], schema_name = connexion_dic["schema"], format_type='GPKG')
        dropTable(connexion, 'sgts_strate_arboree')

    if output_layers["shrub"] != '' :
        query = """
        DROP TABLE IF EXISTS sgts_strate_arbustive;
        CREATE TABLE sgts_strate_arbustive AS
            SELECT *
            FROM %s
            WHERE strate = 'Au';
        """ %(tab_ref)
        executeQuery(connexion, query)
        exportVectorByOgr2ogr(connexion_dic["dbname"], output_layers["shrub"], 'sgts_strate_arbustive', user_name = connexion_dic["user_db"], password = connexion_dic["password_db"], ip_host = connexion_dic["server_db"], num_port = connexion_dic["port_number"], schema_name = connexion_dic["schema"], format_type='GPKG')
        dropTable(connexion, 'sgts_strate_arbustive')

    if output_layers["herbaceous"] != '' :
        query = """
        DROP TABLE IF EXISTS sgts_strate_herbace;
        CREATE TABLE sgts_strate_herbace AS
            SELECT *
            FROM %s
            WHERE strate = 'H';
        """ %(tab_ref)
        executeQuery(connexion, query)
        exportVectorByOgr2ogr(connexion_dic["dbname"], output_layers["herbaceous"], 'sgts_strate_herbace', user_name = connexion_dic["user_db"], password = connexion_dic["password_db"], ip_host = connexion_dic["server_db"], num_port = connexion_dic["port_number"], schema_name = connexion_dic["schema"], format_type='GPKG')
        dropTable(connexion, 'sgts_strate_herbace')

    if output_layers["output_stratesv"] != '' :
        exportVectorByOgr2ogr(connexion_dic["dbname"], output_layers["output_stratesv"], tab_ref, user_name = connexion_dic["user_db"], password = connexion_dic["password_db"], ip_host = connexion_dic["server_db"], num_port = connexion_dic["port_number"], schema_name = connexion_dic["schema"], format_type='GPKG')
        # export au format raster
        # creation du chemin de sauvegarde de la donnée raster
        repertory_output = os.path.dirname(output_layers["output_stratesv"])
        filename =  os.path.splitext(os.path.basename(output_layers["output_stratesv"]))[0]
        raster_output = repertory_output + os.sep + filename  + '.tif'
        rasterizeVector(output_layers["output_stratesv"], raster_output,  img_ref, 'fv_r', codage="uint8", ram_otb=0)
        # suppression de la colonne non utile "strate_r"
        dropColumn(connexion, tab_ref, 'strate_r')

    temps_prep = "Temps de l'étape de préparation de la classification verticales : %s secondes, avec le calcul des valeurs médianes de texture qui prend : %s secondes et le calcul des valeurs médianes de hauteur qui prend : %s secondes."%(time_prepare, time_median, time_mnh)
    temps_etape1 = "Temps de l'étape 1 de la classification verticales : %s secondes"%(time_1etape)
    temps_etape2 = "Temps de l'étape 2 de la classification verticales : %s secondes"%(time_2etape)

    print(bold + temps_prep + endC)
    print(bold + temps_etape1 + endC)
    print(bold + temps_etape2 + endC)

    return tab_ref

###########################################################################################################################################
# FONCTION pretreatment_arbu()                                                                                                            #
###########################################################################################################################################
def pretreatment_arbu(connexion, tab_ref, save_intermediate_result = False, debug = 0):
    """
    Rôle : calculer et créer des tables intermédiaires pour la strate arbustive à traiter :
            - une table constituée des géométries de regroupements arbustifs et du nombre de segments les composants (rgpt_arbu)
            - une table constituée des segments appartennant à un regroupement de plus de 1 segment arbustif (arbu_de_rgpt)
            - une table constituée des segments appartennant à un regroupement d'UN seul segment (arbu_uniq)

    Paramètres :
        connexion : paramètres de connexion
        tab_ref : nom de la table contenant tous les semgents végétation d'origine avec l'attribut 'strate' en prime
        save_intermediate_result : choix sauvegarde ou non des résultats intermédiaires. Par défaut : False
        debug : niveau de debug pour l'affichage des commentaires

    Sortie :
        liste des noms des tables créée
    """
    tab_rgpt_arbu = 'rgpt_arbu'
    ###
    # 1# Création de la table "rgpt_arbu"(geom) contenant les polygones des regroupements
    ###
    query = """
    DROP TABLE IF EXISTS %s;
    CREATE TABLE %s AS
        SELECT public.ST_MAKEVALID((public.ST_DUMP(public.ST_UNION(t.geom))).geom) AS geom
        FROM %s AS t
        WHERE t.strate = 'Au';
    """ %(tab_rgpt_arbu, tab_rgpt_arbu, tab_ref)

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Suppression de rgpt_arbuste trop petits --> surface <= 1m
    query = """
    DELETE FROM %s WHERE public.ST_AREA(geom) <= 1;
    """ %(tab_rgpt_arbu)

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Création d'un nouvel attribut nb_sgt
    addColumn(connexion, tab_rgpt_arbu, 'nb_sgt', 'int')

    # Création d'un identifiant unique
    addUniqId(connexion, tab_rgpt_arbu)

    # Création d'un index spatial
    addSpatialIndex(connexion, tab_rgpt_arbu)

    ###
    # 2# Création de la table "arbu_de_rgpt" contenant les segments appartennant aux regroupements
    ###

    # Creation d'une table intermediaire de segments arbustes dont les géométries correspondent à un point au centre du segment
    query = """
    DROP TABLE IF EXISTS tab_interm_arbuste;
    CREATE TABLE IF NOT EXISTS tab_interm_arbuste AS
        SELECT fid, public.st_pointonsurface(geom) AS geom
        FROM %s
        WHERE strate = 'Au';
    """ %(tab_ref)

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Création d'un index spatial
    addSpatialIndex(connexion, 'tab_interm_arbuste')

    addColumn(connexion, 'tab_interm_arbuste', 'fid_rgpt', 'integer')

    # A présent, nous sommes obligés de passer par python pour lancer les requêtes car les requêtes spatiales globales sont TRES couteuses

    cursor = connexion.cursor()
    data = readTable(connexion, tab_rgpt_arbu)
    tab_rgpt_sgt =[]
    for el in data :
        # Compte le nombre de segments arbustifs dans chaque regroupement
        fid_rgpt = el[2]
        print("Compte le nombre de segments dans le regroupement "+str(fid_rgpt))
        query = """
        SELECT rgpt_arbu.fid, COUNT(rgpt_arbu.fid)
        FROM %s AS rgpt_arbu, tab_interm_arbuste
        WHERE rgpt_arbu.fid = %s AND public.ST_INTERSECTS(tab_interm_arbuste.geom, rgpt_arbu.geom)
        GROUP BY rgpt_arbu.fid;
        """ %(tab_rgpt_arbu, fid_rgpt)
        if debug >= 3:
            print(query)
        cursor.execute(query)
        rgpt_count = cursor.fetchall()

        # Update de l'attribut nb_sgt dans la table rgpt_arbuste
        print("Met à jour la valeur du nombre de segment dans la table rgpt_arbu")
        query = """
        UPDATE %s AS rgpt_arbu SET nb_sgt = %s where rgpt_arbu.fid = %s;
        """ %(tab_rgpt_arbu, rgpt_count[0][1],rgpt_count[0][0])

        # Exécution de la requête SQL
        if debug >= 3:
            print(query)
        executeQuery(connexion, query)


    # Création d'une table intermédiaire pour la requête suivante

    tab_sgtsup = "tab_nb_sgmts_sup_1"
    query = """
    DROP TABLE IF EXISTS %s ;
    CREATE TABLE %s AS
        SELECT * FROM %s
        WHERE nb_sgt>1;
    """ %(tab_sgtsup, tab_sgtsup, tab_rgpt_arbu)

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    addSpatialIndex(connexion, tab_sgtsup)

    # Création table "arbu_de_rgpt"(fid, geom, fid_rgpt) correspondant aux arbustes "regroupés" qui touchent d'autres segments arbustifs
    tab_arbu_rgpt = 'arbu_de_rgpt'
    query = """
    DROP TABLE IF EXISTS %s;
    CREATE TABLE %s AS
        SELECT t1.fid, t1.geom, t4.fid_rgpt
                        FROM (SELECT * FROM %s WHERE strate='Au') AS t1,
                             (SELECT t3.fid AS fid, t2.fid as fid_rgpt
                                FROM %s as t2,
                                tab_interm_arbuste as t3
                                WHERE public.ST_INTERSECTS(t3.geom, t2.geom)) as t4
                        WHERE t1.fid = t4.fid;
    """ %(tab_arbu_rgpt,tab_arbu_rgpt, tab_ref, tab_sgtsup)

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Création index spatial
    addSpatialIndex(connexion, tab_arbu_rgpt)

    # Création d'un index sur une colonne
    addIndex(connexion, tab_arbu_rgpt, 'fid', 'idx_arbu_de_rgpt')

    dropTable(connexion, tab_sgtsup)

    # Création table intermédiaire

    # Création d'une table intermédiaire pour la requête suivante

    tab_sgtinf = "tab_nb_sgmts_inf_1"
    query = """
    DROP TABLE IF EXISTS %s ;
    CREATE TABLE %s AS
        SELECT * FROM %s
        WHERE nb_sgt<=1;
    """ %(tab_sgtinf, tab_sgtinf, tab_rgpt_arbu)

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    addSpatialIndex(connexion, tab_sgtinf)

    ###
    # 3# Création de la table "arbuste_uniq"(fid, geom, fid_rgpt) correspondant aux arbustes "isolés" qui ne touchent aucun autre segment arbustif
    ###


    tab_arbu_uniq = 'arbu_uniq'
    query = """
    DROP TABLE IF EXISTS %s;
    CREATE TABLE %s AS
        SELECT t1.fid, t1.geom, t4.fid_rgpt
            FROM (SELECT fid, geom FROM %s WHERE strate='Au') AS t1,
                    (SELECT t2.fid AS fid, t3.fid as fid_rgpt
                        FROM %s as t3, tab_interm_arbuste AS t2
                    WHERE public.ST_INTERSECTS(t2.geom,t3.geom)) as t4
                        WHERE t1.fid = t4.fid;
    """ %(tab_arbu_uniq, tab_arbu_uniq, tab_ref, tab_sgtinf)

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Création index spatial
    addSpatialIndex(connexion, tab_arbu_uniq)
    # Création d'un index sur une colonne
    addIndex(connexion, tab_arbu_uniq, 'fid', 'idx_arbu_uniq')

    dropTable(connexion, tab_sgtinf)

    if not save_intermediate_result :
        dropTable(connexion, 'tab_interm_arbuste')

    return tab_rgpt_arbu, tab_arbu_rgpt, tab_arbu_uniq

###########################################################################################################################################
# FONCTION reclassIsolatedSgtsByHeight()                                                                                                  #
###########################################################################################################################################
def reclassIsolatedSgtsByHeight(connexion, tab_ref, dic_seuil, save_intermediate_result = False, debug = 0):
    """
    Rôle : reclasse les segments arbustifs isolés selon leurs différences de hauteur avec les segments arborés et arbustifs les entourant

    Paramètres :
        connexion : paramètres de connexion à la BD
        tab_ref : nom de la table contenant tous les segments végétation d'origine
        dic_seuil : dictionnaire des seuils à appliquer
        save_intermediate_result : choix sauvegarde ou non des résultats intermédiaires. Par défaut : False
        debug : niveau de debug pour l'affichage des commentaires

    """

    # Création de tables temporaires arbres et herbacées

    tab_arbre = "tab_arbreforabuisole_tmp"
    query = """
    DROP TABLE IF EXISTS %s ;
    CREATE TABLE %s AS
        SELECT * FROM %s WHERE strate = 'A';
    """ %(tab_arbre, tab_arbre, tab_ref)

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    addSpatialIndex(connexion, tab_arbre)

    tab_herbe = "tab_herbeforabuisole_tmp"
    query = """
    DROP TABLE IF EXISTS %s ;
    CREATE TABLE %s AS
        SELECT * FROM %s WHERE strate = 'H';
    """ %(tab_herbe, tab_herbe, tab_ref)

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    addSpatialIndex(connexion, tab_herbe)


    # Table contenant les identifiants des segments arbustifs isolés, la longueur de sa frontière et la longueur de sa frontière en contact avec segments arborés

    query = """
    CREATE TABLE arbu_isole_touch_arbo AS
        SELECT t1.fid, t1.geom, public.ST_PERIMETER(t1.geom) AS long_bound_arbu, t2.long_bound_inters_arbo AS long_bound_inters_arbo
        FROM (SELECT t3.fid, SUM(public.ST_LENGTH(t3.geom_bound_inters_arbo)) AS long_bound_inters_arbo
                FROM (SELECT t1.fid, t1.geom, arbre.fid AS fid_arbo, public.ST_INTERSECTION(public.ST_BOUNDARY(t1.geom), public.ST_INTERSECTION(t1.geom, arbre.geom)) AS geom_bound_inters_arbo
                        FROM  arbu_uniq AS t1, %s as arbre
                        WHERE public.ST_INTERSECTS(t1.geom,arbre.geom) and t1.fid not in (SELECT t1.fid
                                                                                    FROM %s AS herbe, arbu_uniq as t1
                                                                                    WHERE public.ST_INTERSECTS(herbe.geom, t1.geom)
                                                                                    GROUP BY t1.fid)) AS t3
                GROUP BY t3.fid) AS t2, arbu_uniq AS t1
    WHERE t1.fid = t2.fid;
    """ %(tab_arbre, tab_herbe)

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Table contenant les identifiants des segments arbustifs isolés, la longueur de sa frontière et la longueur de sa frontière en contact avec segments herbacés
    query = """
    CREATE TABLE arbu_isole_touch_herbe AS
        SELECT t1.fid, t1.geom, public.ST_PERIMETER(t1.geom) AS long_bound_arbu, t3.long_bound_inters_herbe AS long_bound_inters_herbe
        FROM (
             SELECT t2.fid, SUM(public.ST_LENGTH(t2.geom_bound_inters_herbe)) AS long_bound_inters_herbe
             FROM (
                    SELECT t1.fid, t1.geom, herbe.fid AS fid_arbo, public.ST_INTERSECTION(public.ST_BOUNDARY(t1.geom),public.ST_INTERSECTION(t1.geom, herbe.geom)) AS geom_bound_inters_herbe
                    FROM  arbu_uniq AS t1, %s AS herbe
                    WHERE public.ST_INTERSECTS(t1.geom,herbe.geom) AND t1.fid not in (SELECT t1.fid
                                                                                FROM %s AS arbre, arbu_uniq AS t1
                                                                                WHERE public.ST_INTERSECTS(arbre.geom, t1.geom)
                                                                                GROUP BY t1.fid)
                    ) AS t2
             GROUP BY t2.fid
             ) AS t3, arbu_uniq AS t1
        WHERE t1.fid = t3.fid;
    """ %(tab_herbe, tab_arbre)

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    dropTable(connexion, tab_herbe)
    dropTable(connexion, tab_arbre)

   # Création de la table ne contenant que les arbustes qui touchent à la fois de l'arboré et de l'herbacé et que de l'arboré
    query = """
    CREATE TABLE arbu_touch_herb_arbo_and_only_arbo AS (
        SELECT t1.*
        FROM arbu_uniq as t1
        WHERE t1.fid not in (SELECT fid FROM arbu_isole_touch_herbe));
    """

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Création d'une table temporaire pour les segments arborés et herbacés, et une pour les arbustes

    tab_herbarbo = "tab_sgmts_herbarbo_tmp"
    query = """
    DROP TABLE IF EXISTS %s ;
    CREATE TABLE %s AS
        SELECT * FROM %s
        WHERE strate in ('A', 'H') ;
    """ %(tab_herbarbo, tab_herbarbo, tab_ref)

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    addSpatialIndex(connexion, tab_herbarbo)

    tab_arbuste = "tab_sgmts_arbusteformatable_tmp"
    query = """
    DROP TABLE IF EXISTS %s ;
    CREATE TABLE %s AS
        SELECT t1.*
        FROM %s AS t1, arbu_touch_herb_arbo_and_only_arbo AS t2
        WHERE t1.fid = t2.fid ;
    """ %(tab_arbuste, tab_arbuste, tab_ref)

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    addSpatialIndex(connexion, tab_arbuste)

   # Création de la table "matable" contenant l'identifiant du segment arboré ou herbacé avec lequel le segment arbustif intersecte
    query = """
    CREATE TABLE matable AS (SELECT arbuste.fid AS id_arbu, sgt_herbarbo.fid AS id_sgt_t, sgt_herbarbo.strate AS strate_touch, abs(arbuste.mnh-sgt_herbarbo.mnh) AS diff_h
                                FROM %s AS arbuste,
                                    %s AS sgt_herbarbo
                                WHERE public.ST_INTERSECTS(arbuste.geom, sgt_herbarbo.geom));
    """ %(tab_arbuste, tab_herbarbo)

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    dropTable(connexion, tab_arbuste)
    dropTable(connexion, tab_herbarbo)

    query = """
    CREATE TABLE sgt_touch_herbarbo AS (
                                        SELECT matable.*
                                        FROM matable
                                        INNER JOIN
                                        (SELECT matable.id_arbu AS id_arbu, min(matable.diff_h) AS min_diff_h
                                        FROM matable
                                        GROUP BY id_arbu) AS t
                                        ON matable.id_arbu = t.id_arbu AND matable.diff_h = t.min_diff_h);
    """

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Reclassification pour chaque segment arbustif isolé en herbacé ou arboré ou arbustif suivant la valeur minimale de différence de hauteur avec le segment le plus proche
    query = """
    UPDATE %s SET strate = sgt_touch_herbarbo.strate_touch FROM sgt_touch_herbarbo
                                                            WHERE %s.fid = sgt_touch_herbarbo.id_arbu AND sgt_touch_herbarbo.diff_h <= %s;
    """ %(tab_ref, tab_ref, dic_seuil["height_max_difference"])

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    if not save_intermediate_result:
        dropTable(connexion, 'arbu_isole_touch_arbo')
        dropTable(connexion, 'arbu_isole_touch_herbe')
        dropTable(connexion, 'arbu_touch_herb_arbo_and_only_arbo')
        dropTable(connexion, 'matable')
        dropTable(connexion, 'sgt_touch_herbarbo')

    return tab_ref

###########################################################################################################################################
# FONCTION reclassIsolatedSgtsByAreaRatio()                                                                                               #
###########################################################################################################################################
def reclassIsolatedSgtsByAreaRatio(connexion, tab_ref, arbu_uniq, dic_seuil, save_intermediate_result = False, debug = 0):
    """
    Rôle : reclasse les différents segments arbustifs "isolés" selon un rapport de surface avec les segments arborés ou arborés ET herbacés environnants

    Paramètres :
        connexion : variable correspondant à la connexion à la base de données
        tab_ref : nom de la table contenant tous les segments végétation d'origine
        arbu_uniq : nom de la table contenant tous les segments arbustifs isolés
        dic_seuil : dictionnaire des seuils pour la reclassification
        save_intermediate_result : choix sauvegarde ou non des résultats intermédiaires. Par défaut : False
        debug : niveau de debug pour l'affichage des commentaires

    """

    # Création de tables temporaires arbres et herbacées

    tab_arbre = "tab_arbreforabuisole_tmp"
    query = """
    DROP TABLE IF EXISTS %s ;
    CREATE TABLE %s AS
        SELECT * FROM %s WHERE strate = 'A';
    """ %(tab_arbre, tab_arbre, tab_ref)

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    addSpatialIndex(connexion, tab_arbre)

    tab_herbe = "tab_herbeforabuisole_tmp"
    query = """
    DROP TABLE IF EXISTS %s ;
    CREATE TABLE %s AS
        SELECT * FROM %s WHERE strate = 'H';
    """ %(tab_herbe, tab_herbe, tab_ref)

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    addSpatialIndex(connexion, tab_herbe)

    # Table contenant les identifiants des segments arbustifs isolés, la longueur de sa frontière et la longueur de sa frontière en contact avec segments arborés

    query = """
    DROP TABLE IF EXISTS arbu_isole_touch_arbo;
    CREATE TABLE arbu_isole_touch_arbo AS
        SELECT t1.fid, t1.geom
        FROM (SELECT t3.fid
                FROM (SELECT t1.fid, t1.geom, arbre.fid as fid_arbo, public.ST_INTERSECTION(public.ST_BOUNDARY(t1.geom),public.ST_INTERSECTION(t1.geom, arbre.geom)) AS geom_bound_inters_arbo
                        FROM  %s AS t1, %s as arbre
                        WHERE public.ST_INTERSECTS(t1.geom,arbre.geom) and t1.fid not in (SELECT t1.fid
                                                                                    FROM %s AS herbe, %s as t1
                                                                                    WHERE public.ST_INTERSECTS(herbe.geom, t1.geom)
                                                                                    GROUP BY t1.fid)) AS t3
                GROUP BY t3.fid) AS t2, %s AS t1
        WHERE t1.fid = t2.fid;
    """ %(arbu_uniq, tab_arbre, tab_herbe, arbu_uniq, arbu_uniq)

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Table contenant les identifiants des segments arbustifs isolés, la longueur de sa frontière et la longueur de sa frontière en contact avec segments herbacés
    query = """
    DROP TABLE IF EXISTS arbu_isole_touch_herbe;
    CREATE TABLE arbu_isole_touch_herbe AS
        SELECT t1.fid, t1.geom
        FROM (
             SELECT t2.fid
             FROM (
                    SELECT t1.fid, t1.geom, herbe.fid AS fid_herba, public.ST_INTERSECTION(public.ST_BOUNDARY(t1.geom),public.ST_INTERSECTION(t1.geom, herbe.geom)) AS geom_bound_inters_herbe
                    FROM  %s AS t1, %s as herbe
                    WHERE public.ST_INTERSECTS(t1.geom,herbe.geom) and t1.fid not in (SELECT t1.fid
                                                                                FROM %s AS arbre, %s AS t1
                                                                                WHERE public.ST_INTERSECTS(arbre.geom, t1.geom)
                                                                                GROUP BY t1.fid)
                    ) AS t2
             GROUP BY t2.fid
             ) AS t3, %s AS t1
        WHERE t1.fid = t3.fid;
    """ %(arbu_uniq, tab_herbe, tab_arbre, arbu_uniq, arbu_uniq)

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)


    ###
    # 1# Reclassification des arbustes isolés touchant de l arbore uniquement
    ###

    #C reation de la table arbu_uniq_surf_stats contenant pour chaque segment arbustif isolé son identifiant, sa surface et la surface totale des segments arborés le touchant
    query = """
    DROP TABLE IF EXISTS arbu_uniq_surf_stats;
    CREATE TABLE arbu_uniq_surf_stats AS
        SELECT t1.fid AS fid_sgt, public.ST_AREA(t1.geom) AS surf_sgt, public.ST_AREA(public.ST_UNION(t2.geom)) AS surf_touch_arbo
        FROM arbu_isole_touch_arbo AS t1, %s AS t2
        WHERE public.ST_INTERSECTS(t1.geom, t2.geom)
        GROUP BY t1.fid, public.ST_AREA(t1.geom);
    """ %(tab_arbre)

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Création d'une table temporaire pour la requête suivante

    tab_tmp = "tab_ref_arbuunisurfstats_tmp"
    query = """
    DROP TABLE IF EXISTS %s ;
    CREATE TABLE %s AS
        SELECT t1.* FROM %s AS t1, arbu_uniq_surf_stats AS t2
        WHERE t1.fid = t2.fid_sgt;
    """ %(tab_tmp, tab_tmp, tab_ref)

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    addSpatialIndex(connexion, tab_tmp)


    # Creation de la table arbu_uniq_diffh listant la différence de hauteur entre chaque segment arbustif isolé et les segments arborés collés
    query = """
    DROP TABLE IF EXISTS arbu_uniq_diffh;
    CREATE TABLE arbu_uniq_diffh AS
        SELECT t.fid AS fid_sgt, abs(t.mnh-t3.mnh) AS diff_mnh
        FROM %s AS t,
        %s AS t3
        WHERE public.ST_INTERSECTS(t.geom, t3.geom);
    """ %(tab_tmp, tab_arbre)

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    dropTable(connexion, tab_tmp)

    # Creation de la table arbu_uniq_mindiffh faisant le lien entre les deux tables
    query = """
    DROP TABLE IF EXISTS arbu_uniq_mindiffh_surfstats;
    CREATE TABLE arbu_uniq_mindiffh_surfstats AS
        SELECT r.fid_sgt, r.surf_sgt, r.surf_touch_arbo, t.min_diffh
        FROM arbu_uniq_surf_stats AS r, (SELECT r2.fid_sgt, min(r2.diff_mnh) AS min_diffh FROM arbu_uniq_diffh AS r2 GROUP BY r2.fid_sgt) AS t
        WHERE r.fid_sgt = t.fid_sgt;
    """

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    dropTable(connexion, tab_arbre)
    dropTable(connexion, tab_herbe)


   # Reclassification en arboré des segments arbustifs dont la surface n'est pas représentative par rapport à la surface d'arboré qui l'entoure
   # OU lorsque la différence de hauteur est inférieure à un certain seuil
    query = """
    UPDATE %s SET strate = 'A'
            FROM (  SELECT *
                    FROM arbu_uniq_mindiffh_surfstats AS r3
                    WHERE r3.surf_sgt/r3.surf_touch_arbo <= %s
                    UNION
                    SELECT *
                    FROM arbu_uniq_mindiffh_surfstats AS r3
                    WHERE r3.surf_sgt/r3.surf_touch_arbo > %s AND r3.min_diffh <= %s) AS t
            WHERE fid = t.fid_sgt ;
    """ %(tab_ref, dic_seuil["surface_rate"], dic_seuil["surface_rate"], dic_seuil["height_max_difference"])

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    ###
    # 2# Reclassification des arbustes isolés touchant de l arbore et de l'herbace
    ###


    query = """
    DROP TABLE IF EXISTS arbu_touch_herb_arbo;
    CREATE TABLE arbu_touch_herb_arbo AS (
        SELECT t1.*
        FROM %s as t1
        WHERE t1.fid not in (SELECT fid
                                    FROM arbu_isole_touch_arbo
                                    UNION
                                    SELECT fid
                                    FROM arbu_isole_touch_herbe));
    """ %(arbu_uniq)

    query += """
    CREATE INDEX idx_geom_arbu_touch_herbarbo ON arbu_touch_herb_arbo USING gist(geom);
    CREATE INDEX idx_key_arbutouchherbarbo ON arbu_touch_herb_arbo(fid);
    """

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)


    # Création d'une table temporaire pour les segments arborés et herbacés

    tab_herbarbo = "tab_sgmts_herbarbo_tmp"
    query = """
    DROP TABLE IF EXISTS %s ;
    CREATE TABLE %s AS
        SELECT * FROM %s
        WHERE strate in ('A', 'H') ;
    """ %(tab_herbarbo, tab_herbarbo, tab_ref)

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    addSpatialIndex(connexion, tab_herbarbo)

    # Création de la table arbu_uniq_surf_stats2 listant pour chaque segment sa surface et la surface globale des segments autres qui le colle
    query = """
    DROP TABLE IF EXISTS arbu_uniq_surf_stats2 ;
    CREATE TABLE arbu_uniq_surf_stats2 AS
        SELECT t1.fid AS fid_sgt, public.ST_AREA(t1.geom) AS surf_sgt, public.ST_AREA(public.ST_UNION(t2.geom)) AS surf_touch
        FROM arbu_touch_herb_arbo AS t1, %s AS t2
        WHERE public.ST_INTERSECTS(t1.geom, t2.geom)
        GROUP BY t1.fid, public.ST_AREA(t1.geom);
    """ %(tab_herbarbo)

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Création d'une table temporaire pour la requête suivante

    tab_arbuuniq = "tab_arbuuniqsurstats_tmp"
    query = """
    DROP TABLE IF EXISTS %s ;
    CREATE TABLE %s AS
        SELECT t1.* FROM %s AS t1, arbu_uniq_surf_stats2 AS t2
        WHERE t1.fid = t2.fid_sgt ;
    """ %(tab_arbuuniq, tab_arbuuniq, tab_ref)

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    addSpatialIndex(connexion, tab_arbuuniq)


    # Creation de la table arbu_uniq_diffh listant la différence de hauteur entre chaque segment arbustif isolé et les segments arborés et herbacés collés
    query = """
    DROP TABLE IF EXISTS arbu_uniq_diffh2;
    CREATE TABLE arbu_uniq_diffh2 AS
        SELECT t.fid AS fid_sgt, t3.fid AS fid_touch, abs(t.mnh-t3.mnh) AS diff_mnh
        FROM %s AS t,
            %s AS t3
        WHERE public.ST_INTERSECTS(t.geom, t3.geom);
    """ %(tab_arbuuniq, tab_herbarbo)

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    dropTable(connexion, tab_arbuuniq)
    dropTable(connexion, tab_herbarbo)

    # Creation de la table arbu_uniq_mindiffh_surfstats2 faisant le lien entre les deux tables
    query = """
    DROP TABLE IF EXISTS arbu_uniq_mindiffh_surfstats2;
    CREATE TABLE arbu_uniq_mindiffh_surfstats2 AS
        SELECT r.fid_sgt, r.surf_sgt, r.surf_touch, t.fid_touch, t.min_diffh
        FROM arbu_uniq_surf_stats2 AS r,
                (SELECT t2.fid_sgt, t2.fid_touch, t.min_diffh
                    FROM arbu_uniq_diffh2 AS t2,
                        (SELECT r2.fid_sgt, r2.fid_touch, min(r2.diff_mnh) AS min_diffh FROM arbu_uniq_diffh2 AS r2 GROUP BY r2.fid_sgt, r2.fid_touch) AS t
                    WHERE t2.fid_sgt = t.fid_sgt AND t2.diff_mnh = t.min_diffh) AS t
        WHERE r.fid_sgt = t.fid_sgt;
    """

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)


    #  update
    query = """
    UPDATE %s SET strate = t.strate
    FROM (SELECT t.fid_sgt, s.strate
            FROM (  SELECT *
                    FROM arbu_uniq_mindiffh_surfstats2 AS r3
                    WHERE r3.surf_sgt/r3.surf_touch <= %s
                    UNION
                    SELECT *
                    FROM arbu_uniq_mindiffh_surfstats2 AS r3
                    WHERE r3.surf_sgt/r3.surf_touch > %s and r3.min_diffh <= %s ) AS t,
                %s AS s
            WHERE t.fid_touch = s.fid) AS t
    WHERE fid = t.fid_sgt ;
    """ %(tab_ref, dic_seuil["surface_rate"], dic_seuil["surface_rate"], dic_seuil["height_max_difference"], tab_ref)

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    if not save_intermediate_result:
        dropTable(connexion, 'arbu_isole_touch_arbo')
        dropTable(connexion, 'arbu_isole_touch_herbe')
        dropTable(connexion, 'arbu_uniq_surf_stats')
        dropTable(connexion, 'arbu_uniq_diffh')
        dropTable(connexion, 'arbu_uniq_mindiffh_surfstats')
        dropTable(connexion, 'arbu_touch_herb_arbo')
        dropTable(connexion, 'arbu_uniq_surf_stats2')
        dropTable(connexion, 'arbu_uniq_diffh2')
        dropTable(connexion, 'arbu_uniq_mindiffh_surfstats2')


    return


###########################################################################################################################################
# FONCTION reclassGroupSgtsByAreaRatio()                                                                                                  #
###########################################################################################################################################
def reclassGroupSgtsByAreaRatio(connexion, tab_ref, tab_rgpt_arbu, arbu_de_rgpt,  dic_seuil, save_intermediate_result = False, debug = 0):
    """
    Rôle : classe les différents segments arbustifs regroupés selon le rapport de surface
    NB : pour l'instant, on ne se charge que des regroupements entourés QUE d'arboré

    Paramètres :
        connexion : variable correspondant à la connexion à la base de données
        tab_ref : nom de la table contenant tous les segments végétation d'origine
        rgpt_arbu : nom de la table contenant les regroupements arbustifs
        arbu_de_rgpt : nom de la table contenant les segments arbustifs appartennants à des regroupements
        save_intermediate_result : choix sauvegarde ou non des résultats intermédiaires. Par défaut : False
        debug : niveau de debug pour l'affichage des commentaires
    """

    ###
    # 0# Pour diminuer le temps de calcul, nous créons deux tables intermédiaires de regroupements des segments herbacés et arborés
    ###

    query = """
    DROP TABLE IF EXISTS herbace;
    CREATE TABLE herbace AS
        SELECT public.ST_CHAIKINSMOOTHING((public.ST_DUMP(public.ST_MULTI(public.ST_UNION(t1.geom)))).geom) AS geom
        FROM (SELECT geom FROM %s WHERE strate='H') AS t1;
    """ %(tab_ref)

    query += """
    DROP TABLE IF EXISTS arbore;
    CREATE TABLE arbore AS
        SELECT public.ST_CHAIKINSMOOTHING((public.ST_DUMP(public.ST_MULTI(public.ST_UNION(t1.geom)))).geom) AS geom
        FROM (SELECT geom FROM %s WHERE strate='A') AS t1;
    """ %(tab_ref)

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Index spatiaux
    addSpatialIndex(connexion, 'herbace')
    addSpatialIndex(connexion, 'arbore')

    ###
    # 1# Filtrage des regroupements de segment à traiter. Si le regroupement de segment est représentatif (constitué d'au moins 5 arbustes)
    ###
    tab_rgpt_to_treat = 'rgpt_to_treat'
    query = """
    DROP TABLE IF EXISTS %s;
    CREATE TABLE %s AS
        SELECT * FROM %s WHERE public.ST_AREA(geom) < %s;
    """ %(tab_rgpt_to_treat, tab_rgpt_to_treat, tab_rgpt_arbu, dic_seuil["shrub_sign"])

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    addIndex(connexion, tab_rgpt_to_treat, 'fid', 'idx_fid_rgpt_treat')
    addSpatialIndex(connexion, tab_rgpt_to_treat)

    ###
    # 2# Trois grands types de segments arbustifs appartennant à des regroupements :
    ###
     # - regroupements intersectant que des arbres --> traitement itératif
     # - regroupements intersectant que de l'herbe --> non traités
     # - regroupements intersectant de l'herbe et des arbres --> pré-traitement puis traitement itératif

    # Création d'une table intermédiaire contenant les rgpt_arbustifs qui intersectent des segments arborés
    query = """
    DROP TABLE IF EXISTS tab_interm_rgptarbu_touch_arbo;
    CREATE TABLE tab_interm_rgptarbu_touch_arbo AS
        SELECT DISTINCT t.fid, t.geom
        FROM %s AS t, arbore
        WHERE public.ST_INTERSECTS(arbore.geom, t.geom) and t.nb_sgt > 1;
    """ %(tab_rgpt_to_treat)

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Création des indexes
    addIndex(connexion, 'tab_interm_rgptarbu_touch_arbo', 'fid', 'indx_fid_1')
    addSpatialIndex(connexion, 'tab_interm_rgptarbu_touch_arbo')


    # Création d'une table intermédiaire contenant les rgpt_arbustifs qui intersectent des segments herbacés
    query = """
    DROP TABLE IF EXISTS tab_interm_rgptarbu_touch_herbo;
    CREATE TABLE tab_interm_rgptarbu_touch_herbo AS
        SELECT DISTINCT t.fid, t.geom
        FROM %s AS t, herbace
        WHERE public.ST_INTERSECTS(herbace.geom, t.geom) and t.nb_sgt > 1;
    """  %(tab_rgpt_to_treat)

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Création des indexes
    addIndex(connexion, 'tab_interm_rgptarbu_touch_herbo', 'fid', 'indx_fid_3')
    addSpatialIndex(connexion, 'tab_interm_rgptarbu_touch_herbo')


    # Création d'une table intermédiaire contenant les regroupements n'intersectant QUE des segments arborés
    query = """
    DROP TABLE IF EXISTS tab_interm_rgptarbu_touchonlyarbo;
    CREATE TABLE tab_interm_rgptarbu_touchonlyarbo AS
        SELECT t2.fid, t2.geom
        FROM tab_interm_rgptarbu_touch_arbo AS t2
        WHERE t2.fid not in (select fid from tab_interm_rgptarbu_touch_herbo);
    """

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Création des indexes
    addIndex(connexion, 'tab_interm_rgptarbu_touchonlyarbo', 'fid', 'indx_fid_4')
    addSpatialIndex(connexion, 'tab_interm_rgptarbu_touchonlyarbo')

    # Création d'une table intermédiaire contenant les rgpt intersectants des segments arborés ET herbacés
    query = """
    DROP TABLE IF EXISTS tab_interm_rgptarbu_toucharboetherbo;
    CREATE TABLE tab_interm_rgptarbu_toucharboetherbo AS
        SELECT t2.fid, t2.geom
        FROM tab_interm_rgptarbu_touch_arbo AS t2
        WHERE t2.fid in (select fid from tab_interm_rgptarbu_touch_herbo);
    """

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)


    # Création des indexes
    addIndex(connexion, 'tab_interm_rgptarbu_toucharboetherbo', 'fid', 'indx_fid_5')
    addSpatialIndex(connexion, 'tab_interm_rgptarbu_toucharboetherbo')

    ###
    # 3# Reclassification des arbustes de regroupement touchant de l arbore uniquement
    ###

    # Creation de la table rgpt_arbu_surf_stats contenant pour chaque regroupement arbustif son identifiant, sa surface et la surface totale des segments arborés le touchant
    query = """
    DROP TABLE IF EXISTS rgpt_arbu_surf_stats3;
    CREATE TABLE rgpt_arbu_surf_stats3 AS
        SELECT t1.fid AS fid_rgpt, public.ST_AREA(t1.geom) AS surf_rgpt, public.ST_AREA(public.ST_UNION(t2.geom)) AS surf_touch_arbo
        FROM tab_interm_rgptarbu_touchonlyarbo AS t1, arbore AS t2
        WHERE public.ST_INTERSECTS(t1.geom, t2.geom)
        GROUP BY t1.fid, public.ST_AREA(t1.geom);
    """
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)


   # Mise à jour du statut "strate" du segment arbustif rentrant dans les conditions
    query = """
    UPDATE %s AS t1 SET strate = 'A'
            FROM (SELECT t1.fid
                    FROM %s AS t1, (SELECT * FROM rgpt_arbu_surf_stats3 AS r WHERE r.surf_rgpt/r.surf_touch_arbo <= %s) AS t2
                    WHERE t1.fid_rgpt = t2.fid_rgpt) AS t2
            WHERE t1.fid = t2.fid ;
    """ %(tab_ref, arbu_de_rgpt, dic_seuil["surface_rate"])

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    ###
    # 4# Reclassification des arbustes de regroupement touchant de l arbore et de l'herbace
    ###

    # 4.1 # Filtre les regroupements touchant très peu d'arboré mais beaucoup d'herbacé
    # Création d'une table intermédiaire qui contient les regroupements et la longueur de leur frontière en contact avec des arbres et de l'herbe
    query = """
    DROP TABLE IF EXISTS rgpt_herbarbotouch_longbound;
    CREATE TABLE rgpt_herbarbotouch_longbound AS
        SELECT t1.fid, t1.geom, public.ST_PERIMETER(t1.geom) AS long_bound_arbu, t3.long_bound_inters_herbe AS long_bound_inters_herbe, t4.long_bound_inters_arbo AS long_bound_inters_arbo
        FROM (
                SELECT t2.fid, SUM(public.ST_LENGTH(t2.geom_bound_inters_herbe)) AS long_bound_inters_herbe
                FROM (SELECT t1.fid, t1.geom, 'H' AS strate, public.ST_INTERSECTION(public.ST_BOUNDARY(t1.geom),public.ST_INTERSECTION(t1.geom, herbe.geom)) AS geom_bound_inters_herbe
                        FROM  tab_interm_rgptarbu_toucharboetherbo AS t1, herbace as herbe
                        WHERE public.ST_INTERSECTS(t1.geom,herbe.geom)
                     ) AS t2
                GROUP BY t2.fid
              ) AS t3,
              (
                SELECT t2.fid,SUM(public.ST_LENGTH(t2.geom_bound_inters_arbo)) AS long_bound_inters_arbo
                FROM (SELECT t1.fid, t1.geom, 'A' AS strate, public.ST_INTERSECTION(public.ST_BOUNDARY(t1.geom),public.ST_INTERSECTION(t1.geom, arbore.geom)) AS geom_bound_inters_arbo
                        FROM  tab_interm_rgptarbu_toucharboetherbo AS t1, arbore
                        WHERE public.ST_INTERSECTS(t1.geom,arbore.geom)
                     ) AS t2
                GROUP BY t2.fid
              ) AS t4,
              tab_interm_rgptarbu_toucharboetherbo AS t1
        WHERE t1.fid = t3.fid and t1.fid = t4.fid;
    """

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    addIndex(connexion, 'rgpt_herbarbotouch_longbound', 'fid','idx_fid_rgpt_herbarbotouch_longbound')
    addSpatialIndex(connexion, 'rgpt_herbarbotouch_longbound')

    tab_herba_cond_tmp = 'herbabotouch_longbound_cond_tmp'

    query = """
    DROP TABLE IF EXISTS %s;
    CREATE TABLE %s AS
        SELECT *
        FROM rgpt_herbarbotouch_longbound AS t
        WHERE t.long_bound_inters_arbo * 100 / t.long_bound_arbu < %s AND t.long_bound_inters_herbe * 100 / t.long_bound_arbu >= %s ;
    """ %(tab_herba_cond_tmp, tab_herba_cond_tmp, dic_seuil["shrub_touch_treevsgrass_perc"], dic_seuil["shrub_touch_grassvstree_perc"])

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    addIndex(connexion, tab_herba_cond_tmp, 'fid','idx_fid_herbabotouch_longbound_cond_tmp')
    addSpatialIndex(connexion,  tab_herba_cond_tmp)

    table_tmp = 'reclassarbu_herba_tmp'

    query = """
    DROP TABLE IF EXISTS %s;
    CREATE TABLE %s AS
        SELECT t3.*
        FROM %s AS t3, (SELECT t2.*
            FROM %s AS t1,
                arbu_de_rgpt AS t2, arbore AS t3
            WHERE t2.fid_rgpt = t1.fid AND public.ST_INTERSECTS(t2.geom, t3.geom)) AS t4
        WHERE t3.fid = t4.fid ;
    """ %(table_tmp, table_tmp, tab_ref, tab_herba_cond_tmp)

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    addIndex(connexion, table_tmp, 'fid','idx_fid_reclassarbu_herba_tmp')
    addSpatialIndex(connexion, table_tmp)

    dropTable(connexion, tab_herba_cond_tmp)

    # Création de tables intermédiaires

    tab_arbre = "tab_arbreforabuisole_tmp"
    query = """
    DROP TABLE IF EXISTS %s ;
    CREATE TABLE %s AS
        SELECT * FROM %s WHERE strate = 'A' ;
    """ %(tab_arbre, tab_arbre, tab_ref)

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    addSpatialIndex(connexion, tab_arbre)


    # Mise à jour du statut des segments arbustifs appartennant à un regroupement touchant peu d'arboré et bcp d'herbacé
    query = """
    UPDATE %s AS t1 SET strate = 'A'
            FROM (SELECT t1.fid AS fid_arbu, t2.fid AS fid_arbo, abs(t1.mnh - t2.mnh) AS diff_h
                    FROM %s AS t1,
                        %s AS t2
                    WHERE public.ST_INTERSECTS(t1.geom, t2.geom)) AS t2
            WHERE t1.fid = t2.fid_arbu AND t2.diff_h <= %s;
    """ %(tab_ref, table_tmp, tab_arbre, dic_seuil["height_max_difference"])

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    dropTable(connexion, tab_arbre)
    dropTable(connexion, table_tmp)
    # Suppression des regroupements de la liste à traiter avec itération si le regroupement partage une plus grande longueur de frontière avec l'herbacé que l'arbore
    query = """
    DELETE FROM tab_interm_rgptarbu_toucharboetherbo AS t1 USING (SELECT * FROM rgpt_herbarbotouch_longbound AS t WHERE t.long_bound_inters_arbo * 100 / t.long_bound_arbu < %s AND t.long_bound_inters_herbe * 100 / t.long_bound_arbu > %s) AS t2 WHERE t1.fid = t2.fid;
    """ %(dic_seuil["shrub_touch_treevsgrass_perc"], dic_seuil["shrub_touch_grassvstree_perc"])

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # 4.2 # Reclassification des segments de regroupement touchant très peu d'herbacé

    # Création table contenant les valeurs de surface des regroupements arborés et herbacés acolés aux regroupements arbustifs
    query = """
    DROP TABLE IF EXISTS surface_rgpts;
    CREATE TABLE surface_rgpts AS
        SELECT t3.fid_rgpt_arbu, t3.s_rgpt_arbu, t3.s_rgpt_arbo_touch, t4.s_rgpt_herba_touch
        FROM ( SELECT t1.fid AS fid_rgpt_arbu, public.ST_AREA(t1.geom) AS s_rgpt_arbu, SUM(public.ST_AREA(t2.geom)) AS s_rgpt_arbo_touch
                FROM tab_interm_rgptarbu_toucharboetherbo AS t1, %s AS t2
                WHERE public.ST_INTERSECTS(t1.geom, t2.geom)
                GROUP BY fid_rgpt_arbu, s_rgpt_arbu
            ) AS t3,
            ( SELECT t1.fid AS fid_rgpt_arbu, SUM(public.ST_AREA(t2.geom)) AS s_rgpt_herba_touch
                FROM tab_interm_rgptarbu_toucharboetherbo AS t1, %s AS t2
                WHERE public.ST_INTERSECTS(t1.geom, t2.geom)
                GROUP BY fid_rgpt_arbu
            ) AS t4
        WHERE t3.fid_rgpt_arbu = t4.fid_rgpt_arbu;
    """ %('arbore','herbace')

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Suppression des regroupements arbustifs qui ne seront pas reclassifiés à partir d'une première règle de surface
    query = """
    DELETE FROM tab_interm_rgptarbu_toucharboetherbo AS t1 USING (SELECT fid_rgpt_arbu AS fid FROM surface_rgpts WHERE (s_rgpt_arbu/(s_rgpt_arbo_touch+s_rgpt_herba_touch)) >= %s) AS t2
                        WHERE t1.fid = t2.fid;
    """ %(dic_seuil["surface_rate"])

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Création table contenant les valeurs de hauteur moyenne des segments arborés et herbacés accolés aux regroupements arbustifs
    query = """
    DROP TABLE IF EXISTS h_moys;
    CREATE TABLE h_moys AS
        SELECT t1.fid AS fid_rgpt, t1.h_arbu_moy, 0 AS h_arbo_moy, 0 AS h_herbo_moy
        FROM ( SELECT t4.fid, t5.h_arbu_moy
                FROM tab_interm_rgptarbu_toucharboetherbo as t4,
                    (SELECT t1.fid_rgpt, AVG(t2.mnh) AS h_arbu_moy
                    FROM %s AS t1, %s AS t2
                    WHERE t1.fid = t2.fid
                    GROUP BY t1.fid_rgpt) AS t5
                WHERE t4.fid = t5.fid_rgpt
              ) AS t1
    """ %(arbu_de_rgpt, tab_ref)

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    tab_tmp_a = 'tab_ref_reduce_a_tmp'

    query = """
    DROP TABLE IF EXISTS %s;
    CREATE TABLE %s AS
        SELECT fid, geom, mnh
        FROM %s
        WHERE strate = 'A' ;
    """ %(tab_tmp_a, tab_tmp_a, tab_ref)

    executeQuery(connexion, query)

    addIndex(connexion, tab_tmp_a, 'fid','idx_fid_tab_ref_reduce_a_tmp')
    addSpatialIndex(connexion, tab_tmp_a)

    tab_tmp_h = 'tab_ref_reduce_h_tmp'

    query = """
    DROP TABLE IF EXISTS %s;
    CREATE TABLE %s AS
        SELECT fid, geom, mnh
        FROM %s
        WHERE strate = 'H' ;
    """ %(tab_tmp_h, tab_tmp_h, tab_ref)

    executeQuery(connexion, query)

    addIndex(connexion, tab_tmp_h, 'fid','idx_fid_tab_ref_reduce_h_tmp')
    addSpatialIndex(connexion, tab_tmp_h)


    query = """
    UPDATE h_moys AS t1 SET h_arbo_moy = t2.h_arbo_moy FROM (SELECT t4.fid, AVG(t5.mnh) AS h_arbo_moy
                                                            FROM tab_interm_rgptarbu_toucharboetherbo AS t4,
                                                                %s AS t5
                                                                WHERE public.ST_INTERSECTS(t4.geom, t5.geom)
                                                                GROUP BY t4.fid) AS t2
                                                        WHERE t1.fid_rgpt = t2.fid;
    """ %(tab_tmp_a)

    query += """
    UPDATE h_moys AS t1 SET h_herbo_moy = t2.h_herbo_moy FROM (SELECT t4.fid, AVG(t5.mnh) AS h_herbo_moy
                                                            FROM tab_interm_rgptarbu_toucharboetherbo AS t4,
                                                                %s AS t5
                                                            WHERE public.ST_INTERSECTS(t4.geom, t5.geom)
                                                            GROUP BY t4.fid) AS t2
                                                        WHERE t1.fid_rgpt = t2.fid;
    """ %(tab_tmp_h)

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    dropTable(connexion, tab_tmp_a)
    dropTable(connexion, tab_tmp_h)

    # Attribution à chaque regroupement arbustif de sa nouvelle classe selon une règle de hauteur
    addColumn(connexion, 'h_moys', 'label', 'varchar(100)')

    query = """
    UPDATE h_moys SET label = 'A' WHERE  abs(h_arbu_moy-h_arbo_moy) > abs(h_arbu_moy-h_herbo_moy);
    UPDATE h_moys SET label = 'H' WHERE  abs(h_arbu_moy-h_arbo_moy) < abs(h_arbu_moy-h_herbo_moy);
    """

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Attribution de la nouvelle classe aux segments des regroupements arbustifs
    query = """
    DROP TABLE IF EXISTS arbu_rgpt_treat;
    CREATE TABLE arbu_rgpt_treat AS
        SELECT t1.fid, t2.label
        FROM %s AS t1, h_moys AS t2
        WHERE t1.fid_rgpt = t2.fid_rgpt;
    """ %(arbu_de_rgpt)

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    query = """
    UPDATE %s AS t1 SET strate = t2.label FROM arbu_rgpt_treat AS t2 WHERE t1.fid = t2.fid;
    """ %(tab_ref)

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    if not save_intermediate_result :
        dropTable(connexion, 'herbace')
        dropTable(connexion, 'arbore')
        dropTable(connexion, 'tab_interm_rgptarbu_touch_arbo')
        dropTable(connexion, 'tab_interm_rgptarbu_touch_herbo')
        dropTable(connexion, 'tab_interm_rgptarbu_touchonlyarbo')
        dropTable(connexion, 'tab_interm_rgptarbu_toucharboetherbo')
        dropTable(connexion, 'rgpt_arbu_surf_stats3')
        dropTable(connexion, 'surface_rgpts')
        dropTable(connexion, 'h_moys')
        dropTable(connexion, 'arbu_rgpt_treat')


    return tab_ref

###########################################################################################################################################
# FONCTION reclassGroupSegments()                                                                                                         #
###########################################################################################################################################
def reclassGroupSegments(connexion, tab_ref, rgpt_arbu, dic_seuil, save_intermediate_result = False, debug = 0):
    """
    Rôle : reclasse les segments arbustifs regroupés

    Paramètre :
        connexion : paramètres de connexion à la BD
        tab_ref : nom de la table contenant tous les segments végétation d'origine
        rgpt_arbu : nom de la table contenant les regroupements arbustifs
        dic_seuil : dictionnaire contenant les seuils à prendre en compte lors de différentes classifications
        save_intermediate_result : choix sauvegarde ou non des résultats intermédiaires. Par défaut : False
        debug : niveau de debug pour l'affichage des commentaires

    """
    ###
    # 0# Pour diminuer le temps de calcul, nous créons deux tables intermédiaires de regroupements des segments herbacés et arborés
    ###

    query = """
    DROP TABLE IF EXISTS herbace;
    CREATE TABLE herbace AS
        SELECT public.ST_MakeValid(public.ST_CHAIKINSMOOTHING((public.ST_DUMP(public.ST_MULTI(public.ST_UNION(t1.geom)))).geom)) AS geom
        FROM (SELECT geom FROM %s WHERE strate='H') AS t1;
    """ %(tab_ref)

    query += """
    DROP TABLE IF EXISTS arbore;
    CREATE TABLE arbore AS
        SELECT public.ST_MakeValid(public.ST_CHAIKINSMOOTHING((public.ST_DUMP(public.ST_MULTI(public.ST_UNION(t1.geom)))).geom)) AS geom
        FROM (SELECT geom FROM %s WHERE strate='A') AS t1;
    """ %(tab_ref)

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Index spatiaux
    addSpatialIndex(connexion, 'herbace')
    addSpatialIndex(connexion, 'arbore')


   ###
   # 1# Trois grands types de segments arbustifs appartennant à des regroupements :
   ###
     # - regroupements intersectant que des arbres --> traitement itératif
     # - regroupements intersectant que de l'herbe --> non traités
     # - regroupements intersectant de l'herbe et des arbres --> pré-traitement puis traitement itératif

    # Création d'une table intermédiaire contenant les rgpt_arbustifs qui intersectent des segments arborés
    query = """
    DROP TABLE IF EXISTS tab_interm_rgptarbu_touch_arbo;
    CREATE TABLE tab_interm_rgptarbu_touch_arbo AS
        SELECT DISTINCT t.fid, t.geom
        FROM %s AS t, arbore
        WHERE public.ST_INTERSECTS(arbore.geom, t.geom) and t.nb_sgt > 1;
    """ %(rgpt_arbu)

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Création des indexes
    addIndex(connexion, 'tab_interm_rgptarbu_touch_arbo', 'fid', 'indx_fid_1')
    addSpatialIndex(connexion, 'tab_interm_rgptarbu_touch_arbo')


    # Création d'une table intermédiaire contenant les rgpt_arbustifs qui intersectent des segments herbacés
    query = """
    DROP TABLE IF EXISTS tab_interm_rgptarbu_touch_herbo;
    CREATE TABLE tab_interm_rgptarbu_touch_herbo AS
        SELECT DISTINCT t.fid, t.geom
        FROM %s AS t, herbace
        WHERE public.ST_INTERSECTS(herbace.geom, t.geom) and t.nb_sgt > 1;
    """  %(rgpt_arbu)

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Création des indexes
    addIndex(connexion, 'tab_interm_rgptarbu_touch_herbo', 'fid', 'indx_fid_3')
    addSpatialIndex(connexion, 'tab_interm_rgptarbu_touch_herbo')


    # Création d'une table intermédiaire contenant les regroupements n'intersectant QUE des segments arborés
    query = """
    DROP TABLE IF EXISTS tab_interm_rgptarbu_touchonlyarbo;
    CREATE TABLE tab_interm_rgptarbu_touchonlyarbo AS
        SELECT t2.fid, t2.geom
        FROM tab_interm_rgptarbu_touch_arbo AS t2
        WHERE t2.fid not in (select fid from tab_interm_rgptarbu_touch_herbo);
    """

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Création des indexes
    addIndex(connexion, 'tab_interm_rgptarbu_touchonlyarbo', 'fid', 'indx_fid_4')
    addSpatialIndex(connexion, 'tab_interm_rgptarbu_touchonlyarbo')

    # Création d'une table intermédiaire contenant les rgpt intersectants des segments arborés ET herbacés
    query = """
    DROP TABLE IF EXISTS tab_interm_rgptarbu_toucharboetherbo;
    CREATE TABLE tab_interm_rgptarbu_toucharboetherbo AS
        SELECT t2.fid, t2.geom
        FROM tab_interm_rgptarbu_touch_arbo AS t2
        WHERE t2.fid in (select fid from tab_interm_rgptarbu_touch_herbo);
    """

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)


    #Création des indexes
    addIndex(connexion, 'tab_interm_rgptarbu_toucharboetherbo', 'fid', 'indx_fid_5')
    addSpatialIndex(connexion, 'tab_interm_rgptarbu_toucharboetherbo')

    ###
    # 2# Pré-traitements : regroupements arbustifs touchant en majorité de l'herbacé
    ###
    query = """
    DELETE FROM tab_interm_rgptarbu_toucharboetherbo WHERE public.ST_AREA(geom) <  1;
    DELETE FROM herbace WHERE public.ST_AREA(geom) <  1;
    DELETE FROM arbore WHERE public.ST_AREA(geom) <  1;
    """
    executeQuery(connexion, query)


    query = "UPDATE %s SET %s = public.ST_CollectionExtract(public.ST_ForceCollection(public.ST_MakeValid(%s)),3) WHERE NOT public.ST_IsValid(%s);" % ('tab_interm_rgptarbu_toucharboetherbo', 'geom', 'geom', 'geom')
    executeQuery(connexion, query)
    query = "UPDATE %s SET %s = public.ST_CollectionExtract(public.ST_ForceCollection(public.ST_MakeValid(%s)),3) WHERE NOT public.ST_IsValid(%s);" % ('herbace', 'geom', 'geom', 'geom')
    executeQuery(connexion, query)
    query = "UPDATE %s SET %s = public.ST_CollectionExtract(public.ST_ForceCollection(public.ST_MakeValid(%s)),3) WHERE NOT public.ST_IsValid(%s);" % ('arbore', 'geom', 'geom', 'geom')
    executeQuery(connexion, query)



    # Création d'une table intermédiaire qui contient les regroupements et la longueur de leur frontière en contact avec des arbres et de l'herbe
    query = """
    DROP TABLE IF EXISTS rgpt_herbarbotouch_longbound;
    CREATE TABLE rgpt_herbarbotouch_longbound AS
        SELECT t1.fid, t1.geom, public.ST_PERIMETER(t1.geom) AS long_bound_arbu, t3.long_bound_inters_herbe AS long_bound_inters_herbe, t4.long_bound_inters_arbo AS long_bound_inters_arbo
        FROM (
                SELECT t2.fid, SUM(public.ST_LENGTH(t2.geom_bound_inters_herbe)) AS long_bound_inters_herbe
                FROM (SELECT t1.fid, t1.geom, 'H' AS strate, public.ST_INTERSECTION(public.ST_BOUNDARY(t1.geom),public.ST_INTERSECTION(t1.geom, herbe.geom)) AS geom_bound_inters_herbe
                        FROM  tab_interm_rgptarbu_toucharboetherbo AS t1, herbace as herbe
                        WHERE public.ST_INTERSECTS(t1.geom,herbe.geom)
                     ) AS t2
                GROUP BY t2.fid
              ) AS t3,
              (
                SELECT t2.fid,SUM(public.ST_LENGTH(t2.geom_bound_inters_arbo)) AS long_bound_inters_arbo
                FROM (SELECT t1.fid, t1.geom, 'A' AS strate, public.ST_INTERSECTION(public.ST_BOUNDARY(t1.geom),public.ST_INTERSECTION(t1.geom, arbore.geom)) AS geom_bound_inters_arbo
                        FROM  tab_interm_rgptarbu_toucharboetherbo AS t1, arbore
                        WHERE public.ST_INTERSECTS(t1.geom,arbore.geom)
                     ) AS t2
                GROUP BY t2.fid
              ) AS t4,
              tab_interm_rgptarbu_toucharboetherbo AS t1
        WHERE t1.fid = t3.fid and t1.fid = t4.fid;
    """

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    addIndex(connexion, 'rgpt_herbarbotouch_longbound', 'fid','idx_fid_rgpt_herbarbotouch_longbound')
    addSpatialIndex(connexion, 'rgpt_herbarbotouch_longbound')

    tab_herba_cond_tmp = 'herbabotouch_longbound_cond_tmp'

    query = """
    DROP TABLE IF EXISTS %s;
    CREATE TABLE %s AS
        SELECT *
        FROM rgpt_herbarbotouch_longbound AS t
        WHERE t.long_bound_inters_arbo * 100 / t.long_bound_arbu < %s AND t.long_bound_inters_herbe * 100 / t.long_bound_arbu >= %s ;
    """ %(tab_herba_cond_tmp, tab_herba_cond_tmp, dic_seuil["shrub_touch_treevsgrass_perc"], dic_seuil["shrub_touch_grassvstree_perc"])

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    addIndex(connexion, tab_herba_cond_tmp, 'fid','idx_fid_herbabotouch_longbound_cond_tmp')
    addSpatialIndex(connexion,  tab_herba_cond_tmp)

    table_tmp = 'reclassarbu_herba_tmp'

    query = """
    DROP TABLE IF EXISTS %s;
    CREATE TABLE %s AS
        SELECT t3.*
        FROM %s AS t3, (SELECT t2.*
            FROM %s AS t1,
                arbu_de_rgpt AS t2, arbore AS t3
            WHERE t2.fid_rgpt = t1.fid AND public.ST_INTERSECTS(t2.geom, t3.geom)) AS t4
        WHERE t3.fid = t4.fid ;
    """ %(table_tmp, table_tmp, tab_ref, tab_herba_cond_tmp)

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    addIndex(connexion, table_tmp, 'fid','idx_fid_reclassarbu_herba_tmp')
    addSpatialIndex(connexion, table_tmp)

    dropTable(connexion, tab_herba_cond_tmp)

    # Création de tables intermédiaires

    tab_arbre = "tab_arbreforabuisole_tmp"
    query = """
    DROP TABLE IF EXISTS %s ;
    CREATE TABLE %s AS
        SELECT * FROM %s WHERE strate = 'A' ;
    """ %(tab_arbre, tab_arbre, tab_ref)

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    addSpatialIndex(connexion, tab_arbre)

    # Mise à jour du statut des segments arbustifs appartennant à un regroupement touchant peu d'arboré et bcp d'herbacé
    query = """
    UPDATE %s AS t1 SET strate = 'A'
            FROM (SELECT t1.fid AS fid_arbu, t2.fid AS fid_arbo, abs(t1.mnh - t2.mnh) AS diff_h
                    FROM %s AS t1, %s AS t2
                    WHERE public.ST_INTERSECTS(t1.geom, t2.geom)) AS t2
            WHERE t1.fid = t2.fid_arbu AND t2.diff_h <= %s;
    """ %(tab_ref, table_tmp, tab_arbre, dic_seuil["height_max_difference"])

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    dropTable(connexion, table_tmp)
    dropTable(connexion, tab_arbre)

    # Suppression des regroupements de la liste à traiter avec itération si le regroupement partage une plus grande longueur de frontière avec l'herbacé que l'arbore
    query = """
    DELETE FROM tab_interm_rgptarbu_toucharboetherbo AS t1 USING (SELECT * FROM rgpt_herbarbotouch_longbound AS t WHERE t.long_bound_inters_arbo * 100 / t.long_bound_arbu < %s AND t.long_bound_inters_herbe * 100 / t.long_bound_arbu > %s) AS t2 WHERE t1.fid = t2.fid;
    """ %(dic_seuil["shrub_touch_treevsgrass_perc"], dic_seuil["shrub_touch_grassvstree_perc"])

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)



    ###
    # 3# Lancement du traitement itératif
    ###

    # Création de la table contenant les regroupements de segments nécessitants un traitement itératif
    query = """
    CREATE TABLE rgpt_arbu_to_treat AS (SELECT * FROM tab_interm_rgptarbu_toucharboetherbo UNION SELECT * FROM tab_interm_rgptarbu_touchonlyarbo);
    """

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    #  Création de la table contenant les segments arbustifs appartennant à des regroupements en contact avec des segments herbacés ET des segments arborés
    query = """
    CREATE TABLE sgt_rgpt_arbu_to_treat AS (SELECT t1.fid, t1.geom, t1.fid_rgpt
                                             FROM arbu_de_rgpt AS t1
                                             WHERE t1.fid_rgpt in (SELECT fid FROM rgpt_arbu_to_treat));
    """

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Création des indexes
    addIndex(connexion, 'sgt_rgpt_arbu_to_treat', 'fid','idx_fid_sgt_rgpt_arbu_to_treat')
    addSpatialIndex(connexion, 'sgt_rgpt_arbu_to_treat')


    # Récupération du nombre de lignes
    cursor = connexion.cursor()
    cursor.execute("SELECT count(*) FROM sgt_rgpt_arbu_to_treat;")
    nb_line_avt = cursor.fetchall()

    # V0 en dehors de la boucle

    # Création de la table contenant les arbustes en bordure des regroupements qui touchent d'autres segments arborés et/ou herbacés
    table_tmp_arbu = 'reclassarbu_tmp'

    query = """
    DROP TABLE IF EXISTS %s;
    CREATE TABLE %s AS
        SELECT t1.*
        FROM %s AS t1, sgt_rgpt_arbu_to_treat as t2
        WHERE t1.fid = t2.fid;
    """ %(table_tmp_arbu, table_tmp_arbu, tab_ref)

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    addIndex(connexion, table_tmp_arbu, 'fid','idx_fid_reclassarbu_tmp')
    addSpatialIndex(connexion, table_tmp_arbu)

    table_tmp_sgt = 'sgt_touch_tmp'

    query = """
    DROP TABLE IF EXISTS %s;
    CREATE TABLE %s AS
        SELECT *
        FROM %s
        WHERE strate in ('A', 'H');
    """ %(table_tmp_sgt, table_tmp_sgt, tab_ref)

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    addIndex(connexion, table_tmp_sgt, 'fid','idx_fid_sgt_touch_tmp')
    addSpatialIndex(connexion, table_tmp_sgt)

    query = """
    DROP TABLE IF EXISTS sgt_rgpt_bordure;
    CREATE  TABLE sgt_rgpt_bordure AS
        SELECT t3.*
        FROM (
            SELECT arbuste.fid as id_arbu, sgt_touch.fid as id_sgt_t, sgt_touch.strate as strate_touch, abs(arbuste.mnh - sgt_touch.mnh) as diff_h
            FROM %s as arbuste, %s AS sgt_touch
            WHERE public.ST_INTERSECTS(arbuste.geom, sgt_touch.geom)
            )
            AS t3
        INNER JOIN
        (SELECT t4.id_arbu as id_arbu, min(t4.diff_h) as min_diff_h
        FROM (
            SELECT arbuste.fid as id_arbu, sgt_touch.fid as id_sgt_t, sgt_touch.strate as strate_touch, abs(arbuste.mnh - sgt_touch.mnh) as diff_h
            FROM %s AS arbuste, %s AS sgt_touch
            WHERE public.ST_INTERSECTS(arbuste.geom, sgt_touch.geom)
            )
            as t4
        GROUP BY id_arbu)
        AS t5
        ON t3.id_arbu = t5.id_arbu AND t3.diff_h = t5.min_diff_h;
    """ %(table_tmp_arbu, table_tmp_sgt, table_tmp_arbu, table_tmp_sgt)

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    dropTable(connexion, table_tmp_arbu)
    dropTable(connexion, table_tmp_sgt)

    # Récupération des identificants arbustifs qui connaissent une modification de leur statut 'strate'

    cursor.execute("SELECT sgt_rgpt_bordure.id_arbu FROM sgt_rgpt_bordure WHERE sgt_rgpt_bordure.diff_h <= 0.5;")
    li_id_arbu = cursor.fetchall()

    # Reclassification des segments situés en bordure de regroupement via le critère de hauteur
    query = """
    UPDATE %s AS t SET
        strate = sgt_rgpt_bordure.strate_touch
        FROM sgt_rgpt_bordure
        WHERE t.fid = sgt_rgpt_bordure.id_arbu AND sgt_rgpt_bordure.diff_h <= %s;
    """ %(tab_ref, dic_seuil["height_max_difference"])

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Suppression dans la table "sgt_rgpt_arbu_to_treat" des segments arbustifs traités précédemment
    query = """
    DELETE FROM sgt_rgpt_arbu_to_treat USING sgt_rgpt_bordure WHERE sgt_rgpt_arbu_to_treat.fid = sgt_rgpt_bordure.id_arbu AND sgt_rgpt_bordure.diff_h <= %s;
    """ %(dic_seuil["height_max_difference"])

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Récupération du nombre de lignes
    # Récupération de la liste des identifiants segments routes
    cursor.execute("SELECT count(*) FROM sgt_rgpt_arbu_to_treat;")
    nb_line = cursor.fetchall()

    query= """
    DROP TABLE IF EXISTS sgt_rgpt_bordure
    """
    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    while nb_line != nb_line_avt:

        nb_line_avt = nb_line
        print("nb_line_avt :",nb_line_avt)

        # Création de la table contenant les arbustes en bordure des regroupements qui touchent d'autres segments arborés et/ou herbacés

        table_tmp_arbu = 'reclassarbu_tmp'

        query = """
        DROP TABLE IF EXISTS %s;
        CREATE TABLE %s AS
            SELECT t1.*
            FROM %s AS t1, sgt_rgpt_arbu_to_treat as t2
            WHERE t1.fid = t2.fid;
        """ %(table_tmp_arbu, table_tmp_arbu, tab_ref)

        # Exécution de la requête SQL
        if debug >= 3:
            print(query)
        executeQuery(connexion, query)

        addIndex(connexion, table_tmp_arbu, 'fid','idx_fid_reclassarbu_tmp')
        addSpatialIndex(connexion, table_tmp_arbu)

        table_tmp_sgt = 'sgt_touch_tmp'

        query = """
        DROP TABLE IF EXISTS %s;
        CREATE TABLE %s AS
            SELECT *
            FROM %s
            WHERE strate in ('A', 'H');
        """ %(table_tmp_sgt, table_tmp_sgt, tab_ref)

        # Exécution de la requête SQL
        if debug >= 3:
            print(query)
        executeQuery(connexion, query)

        addIndex(connexion, table_tmp_sgt, 'fid','idx_fid_sgt_touch_tmp')
        addSpatialIndex(connexion, table_tmp_sgt)

        query = """
        DROP TABLE IF EXISTS sgt_rgpt_bordure;
        CREATE  TABLE sgt_rgpt_bordure AS
            SELECT t3.*
            FROM (
                SELECT arbuste.fid as id_arbu, sgt_touch.fid as id_sgt_t, sgt_touch.strate as strate_touch, abs(arbuste.mnh - sgt_touch.mnh) as diff_h
                FROM %s as arbuste, %s AS sgt_touch
                WHERE public.ST_INTERSECTS(arbuste.geom, sgt_touch.geom)
                )
                AS t3
            INNER JOIN
            (SELECT t4.id_arbu as id_arbu, min(t4.diff_h) as min_diff_h
            FROM (
                SELECT arbuste.fid as id_arbu, sgt_touch.fid as id_sgt_t, sgt_touch.strate as strate_touch, abs(arbuste.mnh - sgt_touch.mnh) as diff_h
                FROM %s AS arbuste, %s AS sgt_touch
                WHERE public.ST_INTERSECTS(arbuste.geom, sgt_touch.geom)
                )
                as t4
            GROUP BY id_arbu)
            AS t5
            ON t3.id_arbu = t5.id_arbu AND t3.diff_h = t5.min_diff_h;
        """ %(table_tmp_arbu, table_tmp_sgt, table_tmp_arbu, table_tmp_sgt)

        # Exécution de la requête SQL
        if debug >= 3:
            print(query)
        executeQuery(connexion, query)

        dropTable(connexion, table_tmp_arbu)
        dropTable(connexion, table_tmp_sgt)

        # Reclassification des segments situés en bordure de regroupement via le critère de hauteur

        query= """
        UPDATE %s SET
            strate = sgt_rgpt_bordure.strate_touch
            FROM sgt_rgpt_bordure
            WHERE %s.fid = sgt_rgpt_bordure.id_arbu and sgt_rgpt_bordure.diff_h <= %s;
        """ %(tab_ref, tab_ref, dic_seuil["height_max_difference"])

         # Exécution de la requête SQL
        if debug >= 3:
            print(query)
        executeQuery(connexion, query)


        # Suppression dans la table "sgt_rgpt_touch_arbo_herbe" des segments arbustifs traités précédemment
        query = """
        DELETE FROM sgt_rgpt_arbu_to_treat USING sgt_rgpt_bordure WHERE sgt_rgpt_arbu_to_treat.fid = sgt_rgpt_bordure.id_arbu AND sgt_rgpt_bordure.diff_h <= %s;
        """ %( dic_seuil["height_max_difference"])

        # Exécution de la requête SQL
        if debug >= 3:
            print(query)
        executeQuery(connexion, query)

        # Récupération du nombre de lignes
        # Récupération de la liste des identifiants segments routes
        cursor.execute("SELECT count(*) FROM sgt_rgpt_arbu_to_treat;")
        nb_line = cursor.fetchall()
        print(nb_line)

        query= """
        DROP TABLE IF EXISTS sgt_rgpt_bordure
        """
        # Exécution de la requête SQL
        if debug >= 3:
            print(query)
        executeQuery(connexion, query)

    # il nous reste les segments qui sont restés ici classés arbustifs à traiter à présent selon le rapport de surface par rapport à ce qui les entoure
    # refondre tous les segments arbustifs en sortie de ce traitement et décomposer en segments arbustifs isolés et segments arbustifs regroupés

    if not save_intermediate_result :
        dropTable(connexion, 'herbace')
        dropTable(connexion, 'arbore')
        dropTable(connexion, 'tab_interm_rgptarbu_touch_arbo')
        dropTable(connexion, 'tab_interm_rgptarbu_touch_herbo')
        dropTable(connexion, 'tab_interm_rgptarbu_touchonlyarbo')
        dropTable(connexion, 'tab_interm_rgptarbu_toucharboetherbo')
        dropTable(connexion, 'rgpt_herbarbotouch_longbound')
        dropTable(connexion, 'rgpt_arbu_to_treat')
        dropTable(connexion, 'sgt_rgpt_arbu_to_treat')

    return

###########################################################################################################################################
# FONCTION calc_statMedian()                                                                                                              #
###########################################################################################################################################
def calc_statMedian(vector_input, image_input, vector_output):
    """
    Rôle : croisement raster/vecteur où on va calculer la médiane du raster sur l'emprise des entités vecteurs

    Paramètres :
        vector_input : fichier vecteur des segments végétation
        image_input : fichier raster
        vector_output : fichier vecteur en sortie pour lequelle on a calculé les statistiques
    """

    col_to_add_list = ["median"]
    col_to_delete_list = ["min", "max", "mean", "unique", "sum", "std", "range"]
    class_label_dico = { }
    statisticsVectorRaster(image_input, vector_input, vector_output, band_number=1,enable_stats_all_count = False, enable_stats_columns_str = False, enable_stats_columns_real = True, col_to_delete_list = col_to_delete_list, col_to_add_list = col_to_add_list, class_label_dico = class_label_dico, path_time_log = "", clean_small_polygons = False, format_vector = 'GPKG',  save_results_intermediate= False, overwrite= True)

    return



###########################################################################################################################################
# FONCTION diviseVectorFile()                                                                                                              #
###########################################################################################################################################

def diviseVectorFile(vector_input, format_vector) :

    """
    Rôle : divise en plusieurs fichiers un fichier vecteur

    Paramètres :
        vector_input : fichier vecteur à diviser
        format_vector : format du fichier vecteur d'entrée
        nb_files : nombre de fichiers souhaités en sortie

    Sortie :
        file_list : liste des fichiers vecteurs (au format ESRI Shapefile) obtenus en découpant le fichier d'entrée
    """
    epsg = 2154
    field = ""

    nb_files = getNumberCPU() - 2

    dir_output = os.path.dirname(vector_input)
    filename =  os.path.splitext(os.path.basename(vector_input))[0]

    driver = ogr.GetDriverByName(format_vector)
    data_source_input = driver.Open(vector_input, 0)
    input_layer = data_source_input.GetLayer()
    input_layer_definition = input_layer.GetLayerDefn()

    nb_polygons = len(input_layer)

    if nb_polygons > nb_files :
        # Récupération des champs de input_layer dans une liste
        attribute_dico = {}

        for i in range(input_layer_definition.GetFieldCount()):
            field_defn = input_layer_definition.GetFieldDefn(i)
            name_attribute = field_defn.GetName()
            attribute_type = field_defn.GetType()
            attribute_dico[name_attribute] = attribute_type

        index = 0
        path_list = []


        nb_poly = len(input_layer)
        nb_poly_in_file = nb_poly // nb_files
        too_much = nb_poly % nb_files

        polygons_attr_geom_dico = {}
        file_list = []

        for k in range(nb_files) :
            file_name = dir_output + os.sep + filename + "_" + str(k) + '.shp'
            file_list.append(file_name)

        file_nb = 0

        # Parcours des entités de input_layer
        for feature_input in input_layer:

            entite = index

            # Récupération de la géométrie de l'élément du fichier d'entrée
            geometry = feature_input.GetGeometryRef()


            # Création d'un shape par entité de input_layer

            # Récupération des valeur des champs du fichier d'entrée
            poly_attr_dico = {}
            for i in range(input_layer_definition.GetFieldCount()):
                field_defn = input_layer_definition.GetFieldDefn(i)
                name_attribute = field_defn.GetName()
                attribute_value = feature_input.GetField(i)
                poly_attr_dico[name_attribute] = attribute_value

            # Create shape
            poly_info_list = [geometry.Clone(), poly_attr_dico]
            polygons_attr_geom_dico[str(entite)] = poly_info_list

            if index % nb_poly_in_file == 0 and index != 0 and (nb_poly - index) > too_much :
                entite = str(entite).replace("-", "_").replace("â", "a").replace("î", "i").replace("ê", "e").replace("è", "e").replace("é", "e").replace("ç", "c")
                new_shape = file_list[file_nb]
                path_list.append(str(new_shape))
                createPolygonsFromGeometryList(attribute_dico, polygons_attr_geom_dico, new_shape, epsg, 'ESRI Shapefile')
                polygons_attr_geom_dico = {}
                file_nb += 1
                print(new_shape)

            if index == nb_poly -1 :
                entite = str(entite).replace("-", "_").replace("â", "a").replace("î", "i").replace("ê", "e").replace("è", "e").replace("é", "e").replace("ç", "c")
                new_shape = file_list[file_nb]
                path_list.append(str(new_shape))
                createPolygonsFromGeometryList(attribute_dico, polygons_attr_geom_dico, new_shape, epsg, 'ESRI Shapefile')

            # Mise a jour de l'index
            index += 1

        # Fermeture du fichier shape entrée
        data_source_input.Destroy()

        return file_list
    else :
        data_source_input.Destroy()
        return [vector_input]

###########################################################################################################################################
# FONCTION calc_statMedian_multiprocessing()                                                                                              #
###########################################################################################################################################

def calc_statMedian_multiprocessing(vector_list, image_input, vector_output) :

    """
    Rôle : croisement raster/vecteur où on va calculer la médiane du raster sur l'emprise des entités vecteurs en utilisant du multiprocessing pour accélérer les calculs

    Paramètres :
        vector_list : liste des fichiers vecteurs dont les statistiques sont à calculer
        image_input : fichier raster
        vector_output : fichier vecteur en sortie pour lequelle on a calculé les statistiques
    """

    dir_output = os.path.dirname(vector_list[0])

    col_to_add_list = ["median"]
    col_to_delete_list = ["min", "max", "mean", "unique", "sum", "std", "range"]
    class_label_dico = { }

    proc_list = []
    output_list = []
    emprise_list = []
    raster_list = []

    extension_vector_gpkg = '.gpkg'
    extension_raster = '.tif'
    extension_vector_shp = '.shp'
    format_vector_gpkg = 'GPKG'
    format_vector_shp = 'ESRI Shapefile'

    for name_file in vector_list :

        vector_emprise = dir_output + os.sep + os.path.splitext(os.path.basename(name_file))[0] + "_emprise" + extension_vector_gpkg
        output_image = dir_output + os.sep + os.path.splitext(os.path.basename(name_file))[0] + "_raster" + extension_raster
        emprise_list.append(vector_emprise)
        raster_list.append(output_image)

        xmin,xmax,ymin,ymax = getEmpriseVector(name_file, format_vector_shp)
        createEmpriseVector(xmin, ymin, xmax, ymax, vector_emprise, projection=2154, format_vector=format_vector_gpkg)

        cutImageByVector(vector_emprise ,image_input, output_image, format_vector=format_vector_gpkg)

        vector_int = dir_output + os.sep + os.path.splitext(os.path.basename(name_file))[0] + "_output" + extension_vector_shp
        output_list.append(vector_int)

        proc = multiprocessing.Process(target = statisticsVectorRaster, args = (output_image, name_file, vector_int, 1, False, False, True, col_to_delete_list,col_to_add_list, class_label_dico, False, 0, format_vector_shp, "", False, True))
        proc.start()
        proc_list.append(proc)

    for proc in proc_list :
        proc.join()

    vector_final = file_name = dir_output + os.sep + os.path.splitext(os.path.basename(vector_output))[0] + "_int" + extension_vector_shp
    fusionVectors(output_list, vector_final, format_vector_shp)

    cmd = "ogr2ogr -f GPKG %s %s"%(vector_output, vector_final)
    os.system(cmd)

    for name_file in output_list :
        removeVectorFile(name_file, format_vector_shp)
    for name_file in emprise_list :
        removeFile(name_file)
    for name_file in raster_list :
        removeFile(name_file)
    removeVectorFile(vector_final, format_vector_shp)


###########################################################################################################################################
# FONCTION reclassificationOmbres()                                                                                                       #
###########################################################################################################################################
def reclassificationOmbres(connexion, tab_ref, save_intermediate_result = False, debug = 0) :

    """
    Rôle : reclassification des segments d'ombres dans les arbres qui ont pu être détectés comme étant de l'herbacé

    Paramètres :
        connexion : paramètres de connexion à la BD
        tab_ref : nom de la table contenant les segments classifié en arboré, arbustif et herbacé
    """

    # Création d'une table ne contenant que les segments herbacés qui ne touchent que de l'arboré et/ou de l'arbustif

    tab_herb_only_arb = "herb_touch_only_arb"
    query = """
    DROP TABLE IF EXISTS %s ;
    CREATE TABLE %s AS
        SELECT *
        FROM %s
        WHERE strate = 'H' AND
        (
            SELECT COUNT(*) FROM %s AS t
            WHERE
                public.ST_Touches(t.geom, %s.geom) AND
                t.strate IN ('Au', 'A')
        ) = (
            SELECT COUNT(*) FROM %s AS t
            WHERE
                public.ST_Touches(t.geom, %s.geom)
        ); """ %(tab_herb_only_arb, tab_herb_only_arb, tab_ref, tab_ref, tab_ref, tab_ref, tab_ref)

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    addSpatialIndex(connexion, tab_herb_only_arb)

    # Création d'une table qui calcule le périmètre du segment et la longueur de la frontière des segments voisins qui le touchent pour les segments concernés

    tab_herb_inters_long = "herb_touch_only_arb_inters_long"
    query = """
    DROP TABLE IF EXISTS %s ;
    CREATE TABLE %s AS
        SELECT t1.fid, 'H' as strate, t1.mnh, t1.geom, public.ST_PERIMETER(t1.geom) AS long_bound_arbu, t2.long_bound_inters_arbo AS long_bound_inters
            FROM (SELECT t3.fid, AVG(t3.mnh), SUM(public.ST_LENGTH(t3.geom_bound_inters_arbo)) AS long_bound_inters_arbo
                FROM (SELECT t1.fid, t1.strate, t1.mnh, t1.geom, seg.fid AS fid_arbo, public.ST_INTERSECTION(public.ST_BOUNDARY(t1.geom), public.ST_INTERSECTION(t1.geom, seg.geom)) AS geom_bound_inters_arbo
                    FROM  %s AS t1, %s as seg
                    WHERE public.ST_INTERSECTS(t1.geom,seg.geom) and t1.fid != seg.fid ) AS t3
                    GROUP BY t3.fid) AS t2, %s AS t1
        WHERE t1.fid = t2.fid;
    """ %(tab_herb_inters_long, tab_herb_inters_long, tab_herb_only_arb, tab_ref, tab_ref)

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Création d'une table ne contenant que les segments concernés ayant une surface inférieure à 20m²

    tab_herb_sorted =  "herb_touch_only_arb_inters_long_surf"
    query = """
    DROP TABLE IF EXISTS %s ;
    CREATE TABLE %s AS
        SELECT * from %s WHERE long_bound_arbu = long_bound_inters and public.ST_AREA(geom) < 20;
    """ %(tab_herb_sorted, tab_herb_sorted, tab_herb_inters_long)

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Mise à jour de la strate pour les segments concernés

    query = """
    UPDATE %s
        SET
            strate =
                CASE
                    WHEN mnh BETWEEN 1 AND 3 THEN 'Au'
                    WHEN mnh > 3 THEN 'A'
                    ELSE strate
                END;
    """%(tab_herb_sorted)


    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Mise à jour de la strate pour les segments concernés dans la table en entrée

    query = """
    UPDATE %s as seg
        SET
            strate = herb.strate
        FROM %s as herb
        WHERE
            seg.fid = herb.fid
    """%(tab_ref, tab_herb_sorted)


    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    if not save_intermediate_result :
        dropTable(connexion, tab_herb_only_arb)
        dropTable(connexion, tab_herb_inters_long)
        dropTable(connexion, tab_herb_sorted)

    return

