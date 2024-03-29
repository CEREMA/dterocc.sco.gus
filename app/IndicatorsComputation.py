#!/usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.               #
#############################################################################

# Import des librairies python
import os,sys, shutil

# Import des librairies de /libs
from libs.Lib_display import bold, yellow, red, green,endC
from libs.Lib_file import removeFile
from libs.CrossingVectorRaster import statisticsVectorRaster
from libs.Lib_postgis import addColumn, dropColumn, dropTable,executeQuery, exportVectorByOgr2ogr, importVectorByOgr2ogr, closeConnection, topologyCorrections, addSpatialIndex, addUniqId

# Import des applications de /app
from app.LandscapeDetection import landscapeDetection

###########################################################################################################################################
# FONCTION createFeatures()                                                                                                               #
###########################################################################################################################################
def createFeatures(connexion, connexion_dic, tab_ref, dic_attributs):
    """
    Rôle : Créé les champs attributaires dans la table des formes végétalisées.

    Paramètres :
        connexion : paramètres de connexion à la base de données
        tab_ref : nom de la table
        dic_attributs : dictionnaire des attributs desciptifs à ajouter et implémenter
    """
    dic_columname ={}
    for attr in dic_attributs.keys():
        col = []
        for i in range(len(dic_attributs[attr])):
            addColumn(connexion, tab_ref, dic_attributs[attr][i][0], dic_attributs[attr][i][1])
            col.append(dic_attributs[attr][i][0])
        dic_columname[attr] = col

    return dic_columname

###########################################################################################################################################
# FONCTION createAndImplementFeatures()                                                                                                   #
###########################################################################################################################################
def createAndImplementFeatures(connexion, connexion_dic, tab_ref, dic_attributs, dic_params, repertory, output_layer = '',  save_intermediate_result = False, debug = 0):
    """
    Rôle : Créé et rempli les champs attributaires des formes végétalisées

    Paramètres :
        connexion : paramètres de connexion à la base de données
        connexion_dic : dictionnaire des paramètres de connexion à la BD
        tab_ref : nom de la table
        dic_attributs : dictionnaire des attributs desciptifs à ajouter et implémenter
        dic_params : dictionnaire des paramètres utiles au calcul des attributs
        repertory : répertoire de calcul des attributs descriptifs
        output_layer : chemin de sauvegarde du fichier final de la cartographie. Par défaut : ''
        save_intermediate_result : choix de sauvegarde des fichiers intermédiaires. Par défaut : False
        debug : niveau de debug pour l'affichage des commentaires. Par défaut : 0
    """
    # Création du répertoire temporaire dans le dossier de travail
    repertory_tmp = repertory + os.sep + 'TMP_FEATURES_IMPLEMENTATION'
    if not os.path.isdir(repertory_tmp):
        os.makedirs(repertory_tmp)

    # Calcul des images temporaires de NDVI
    dic_params["img_ndvi_spg"],dic_params["img_ndvi_wtr"] = calculateSpringAndWinterNdviImage(dic_params["img_ref"], dic_params["img_wtr"], repertory = repertory_tmp)

    # Ajout des attributs descriptifs à la table principale + création d'un dictionnaire de nom des colonnes par indicateur
    dic_columname = createFeatures(connexion, connexion_dic, tab_ref, dic_attributs)

    # Implémentation de la surface de la FV
    areaIndicator(connexion, tab_ref, dic_columname["area_indicator"][0], debug = debug)

    # Implémentation des attributs de hauteur des FV
    heightIndicators(connexion, connexion_dic, tab_ref, dic_columname["height_indicators"], dic_params["img_mnh"], repertory = repertory_tmp, save_intermediate_result = save_intermediate_result, debug = debug)

    # Implémentation du type "persistant" ou "caduc" des FV
    evergreenDeciduousIndicators(connexion, connexion_dic, dic_params["img_ref"],dic_params["img_ndvi_spg"], dic_params["img_ndvi_wtr"], tab_ref, seuil = dic_params["ndvi_difference_everdecid_thr"], columns_indics_name = dic_columname["evergreendeciduous_indicators"], superimpose_choice = dic_params["superimpose_choice"], repertory = repertory_tmp, save_intermediate_result = save_intermediate_result, debug = debug)

    # Implémentation du type "conifère" ou "feuillu" des FV
    coniferousDeciduousIndicators(connexion, connexion_dic, dic_params["img_ref"], tab_ref, seuil = dic_params["pir_difference_thr"], columns_indics_name = dic_columname["coniferousdeciduous_indicators"], repertory = repertory_tmp,save_intermediate_result = save_intermediate_result, debug = debug)

    # Implémentation du type de sol support des FV
    typeOfGroundIndicator(connexion, connexion_dic, dic_params["img_ref"], dic_params["img_ndvi_wtr"], tab_ref, seuil  = dic_params["ndvi_difference_groundtype_thr"], column_indic_name = dic_columname["typeofground_indicator"][0], column_indic_persistant = dic_columname["evergreendeciduous_indicators"][0], repertory = repertory_tmp, save_intermediate_result = save_intermediate_result, debug = debug)

    # Implémentation du paysage
    result = True
    if dic_params["ldsc_information"]["img_landscape"] == "":
        result, dic_params = landscapeDetection(connexion, connexion_dic, dic_params, repertory = dic_params["ldsc_information"]["dirname"] , save_intermediate_result = save_intermediate_result, debug = debug)
    if not result :
        print(bold + yellow + "Faute de données paysage, l'attribut 'paysage' ne sera pas implémenté pour l'ensemble des formes végétales." + endC)
    else:
        landscapeIndicator(connexion, connexion_dic, dic_params["ldsc_information"]["img_landscape"], tab_ref, column_indic_name = dic_columname["landscape_indicator"][0], dic_ldsc_class = dic_params["ldsc_information"]["ldsc_class"], repertory = repertory_tmp, debug = debug)

    closeConnection(connexion)

    # Export résultat au format GPKG
    if output_layer == '':
        print(yellow + bold + "Attention : Il n'y a pas de sauvegarde en couche vecteur de la cartographie finale de la végétation (détaillée). Vous n'avez pas fournit de chemin de sauvegarde." + endC)
    else :
        # Export au format vecteur
        exportVectorByOgr2ogr(connexion_dic["dbname"], output_layer, tab_ref, user_name = connexion_dic["user_db"], password = connexion_dic["password_db"], ip_host = connexion_dic["server_db"], num_port = connexion_dic["port_number"], schema_name = connexion_dic["schema"], format_type='GPKG')

        # # export au format raster --> pour l'instant l'export au format tif n'est pas opérationnel.
        # # creation du chemin de sauvegarde de la donnée raster
        # repertory_output = os.path.dirname(output_layer["output_fv"])
        # filename =  os.path.splitext(os.path.basename(output_layer["output_fv"]))[0]
        # raster_output = repertory_output + os.sep + filename  + '.tif'
        # rasterizeVector(output_layer["output_fv"], raster_output,  output_layer["img_ref"], 'fv_r', codage="uint8", ram_otb=0)

        # # suppression de la colonne non utile "strate_r"
        # dropColumn(connexion, tab_name, 'strate_r')

    # Suppression des fichiers intermédiaires
    if not save_intermediate_result :
        removeFile(dic_params["img_ndvi_spg"])
        removeFile(dic_params["img_ndvi_wtr"])
        if os.path.exists(repertory_tmp):
            shutil.rmtree(repertory_tmp)

    return

###########################################################################################################################################
# FONCTION areaIndicator()                                                                                                                #
###########################################################################################################################################
def areaIndicator(connexion, tab_ref, columnname, debug = 0):
    """
    Rôle : calcul l'attribut de surface

    Paramètres :
        connexion : connexion à la base donnée et au schéma correspondant
        tab_ref : nom de la table de référence contenant les formes végétalisées
        columnname : nom de l'attribut de surface
        debug : niveau de debug pour l'affichage des commentaires. Par défaut : 0
    """

    query = """
    UPDATE %s as t SET %s = public.ST_AREA(t.geom) WHERE t.fid = t.fid;
    """ %(tab_ref, columnname)

    # Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    return

###########################################################################################################################################
# FONCTION heightIndicators()                                                                                                             #
###########################################################################################################################################
def heightIndicators(connexion, connexion_dic, tab_ref, columnnamelist, img_mnh, repertory = '', save_intermediate_result = False, debug = 0):

    """
    Rôle : calcul les attributs de hauteur

    Paramètres :
        connexion : connexion à la base donnée et au schéma correspondant
        connexion_dic : dictionnaire des paramètres des connexion à la base
        tab_ref : nom de la table de référence contenant les formes végétalisées
        columnnamelist : liste des noms de colonne des attributs de hauteur
        img_mnh : image MNH
        repertory : repertoire temporaire dans lequel on sauvegarde les données intermédiaires; Par défaut : ''
        save_intermediate_result : sauvegarde des résultat intermédiaires. Par défaut : False
        debug : niveau de debug pour l'affichage des commentaires. Par défaut : 0
    """
    # Création d'un fichier vecteur temporaire
    filetablevegin = repertory + os.sep + 'couche_vegetation_bis.gpkg'
    filetablevegout = repertory + os.sep + 'couche_vegetation_stats_mnh.gpkg'

    # Export de la table vegetation
    exportVectorByOgr2ogr(connexion_dic["dbname"], filetablevegin, tab_ref, user_name=connexion_dic["user_db"], password=connexion_dic["password_db"], ip_host=connexion_dic["server_db"], num_port=connexion_dic["port_number"],schema_name=connexion_dic["schema"], format_type='GPKG')

    # Calcul des statistiques de hauteur : min, max, mediane et écart-type
    col_to_add_list = ["min", "max", "median", "mean","std"]
    col_to_delete_list = ["unique", "range"]
    class_label_dico = {}
    statisticsVectorRaster(img_mnh, filetablevegin, filetablevegout, band_number=1,enable_stats_all_count = False, enable_stats_columns_str = False, enable_stats_columns_real = True, col_to_delete_list = col_to_delete_list, col_to_add_list = col_to_add_list, class_label_dico = class_label_dico, path_time_log = "", clean_small_polygons = False, format_vector = 'GPKG',  save_results_intermediate= False, overwrite= True)

    tab_refout = 'tab_stats_hauteur_vegetation'

    # Import de la couche vecteur avec les statistiques en tant que table intermédiaire dans la bd
    importVectorByOgr2ogr(connexion_dic["dbname"], filetablevegout, tab_refout, user_name=connexion_dic["user_db"], password=connexion_dic["password_db"], ip_host=connexion_dic["server_db"], num_port=connexion_dic["port_number"], schema_name=connexion_dic["schema"], epsg=str(2154))

    # Implémentation des attributs
    for id in range(len(columnnamelist)):
        if "h_max" in columnnamelist[id] :
            query = """
            UPDATE %s as t1 SET %s = t2.max FROM %s AS t2 WHERE t2.ogc_fid = t1.fid;
            """ %(tab_ref, columnnamelist[id], tab_refout)
        elif "h_min" in columnnamelist[id] :
            query = """
            UPDATE %s as t1 SET %s = t2.min FROM %s AS t2 WHERE t2.ogc_fid = t1.fid;
            """ %(tab_ref,columnnamelist[id], tab_refout)
        elif "h_moy" in columnnamelist[id] :
            query = """
            UPDATE %s as t1 SET %s = t2.mean FROM %s AS t2 WHERE t2.ogc_fid = t1.fid;
            """ %(tab_ref,columnnamelist[id], tab_refout)
        elif "h_med" in columnnamelist[id] :
            query = """
            UPDATE %s as t1 SET %s = t2.median FROM %s AS t2 WHERE t2.ogc_fid = t1.fid;
            """ %(tab_ref,columnnamelist[id], tab_refout)
        elif "h_et" in columnnamelist[id] :
            query = """
            UPDATE %s as t1 SET %s = t2.std FROM %s AS t2 WHERE t2.ogc_fid = t1.fid;
            """ %(tab_ref,columnnamelist[id], tab_refout)

        # Exécution de la requête SQL
        if debug >= 1:
            print(query)
        executeQuery(connexion, query)

    # Suppression du dossier temporaire
    if not save_intermediate_result:
        if os.path.exists(filetablevegin):
            removeFile(filetablevegin)
        if os.path.exists(filetablevegout):
            removeFile(filetablevegout)

        dropTable(connexion, tab_refout)

    return

###########################################################################################################################################
# FONCTION calculateSpringAndWinterNdviImage()                                                                                            #
###########################################################################################################################################
def calculateSpringAndWinterNdviImage(img_spg_input, img_wtr_input, repertory = ''):
    """
    Rôle : calcul les images de NDVI d'hiver et de printemps

    Paramètres :
        img_spg_input : image Pléiades printemps/été
        img_wtr_input : image Pléiades hiver
        repertory : repertoire de sauvegarde des fichiers. Par défaut : ''
        debug : niveau de debug pour l'affichage des commentaires. Par défaut : 0

    Sortie :
        img_ndvi_spg : le chemin du fichier de sauvegarde de l'image NDVI de printemps/été
        img_ndvi_wtr : le chemin du fichier de sauvegarde de l'image NDVI d'hiver
    """

    # Préparation des fichiers de sauvegarde des images NDVI
    extension = os.path.splitext(img_spg_input)[1]
    img_ndvi_spg = repertory + os.sep + 'img_ndvi_printemps' + extension
    img_ndvi_wtr = repertory + os.sep + 'img_ndvi_hiver' + extension

    # Calcul des images ndvi de printemps_été et d'hiver
    cmd_ndvi_spg = "otbcli_BandMath -il %s -out %s -exp '(im1b4-im1b1)/(im1b4+im1b1)'" %(img_spg_input, img_ndvi_spg)
    os.system(cmd_ndvi_spg)

    cmd_ndvi_wtr = "otbcli_BandMath -il %s -out %s -exp '(im1b4-im1b1)/(im1b4+im1b1)'" %(img_wtr_input, img_ndvi_wtr)
    os.system(cmd_ndvi_wtr)

    return img_ndvi_spg, img_ndvi_wtr

###########################################################################################################################################
# FONCTION evergreenDeciduousIndicators()                                                                                                  #
###########################################################################################################################################
def evergreenDeciduousIndicators(connexion, connexion_dic, img_ref,img_ndvi_spg, img_ndvi_wtr, tab_ref, seuil = 0.10, columns_indics_name = ['perc_persistant', 'perc_caduque'], superimpose_choice = False, repertory = '', save_intermediate_result = False, debug = 0):
    """
    Rôle : calcul le pourçentage de persistants et de caduques sur les polygones en entrée

    Paramètres :
        connexion : connexion à la base donnée et au schéma correspondant
        connexion_dic : dictionnaire des paramètres de connexion à la base de données
        img_ref : image Pléiades de référence
        img_ndvi_spg : image ndvi printemps/été
        img_ndvi_wtr : image ndvi hiver
        tab_ref : nom de la  table contenant les polygones de végétation détaillés de type nomduschema.nomdelatable
        seuil : valeur du seuil de PIR pour distinguer les conifères des feuillus. Par défaut : 0.10
        columns_indics_name : liste des noms de colonne des indicateurs à implémenter. Par défaut :['perc_persistant', 'perc_caduque']
        superimpose_choice : choix d'appliquer un superimpose sur une des deux images ndvi produites pour qu'elles se superposent parfaitement. Par défaut : False
        repertory : répertoire de sauvegarde des fichiers intermédiaires. Par défaut : ''
        save_intermediate_result : garder ou non les fichiers temporaires. Par défaut : False
        debug : niveau de debug pour l'affichage des commentaires. Par défaut : 0

    """

    # Création des fichiers temporaires
    extension = os.path.splitext(img_ref)[1]
    image_pers_out = repertory + os.sep + 'img_mask_persistants' + extension
    image_cadu_out = repertory + os.sep + 'img_mask_caduques' + extension

    vect_fv_pers_out = repertory + os.sep + 'vect_fv_stats_pers.gpkg'
    vect_fv_cadu_out = repertory + os.sep + 'vect_fv_stats_cadu.gpkg'

    filetablevegin = repertory + os.sep + 'couche_vegetation_bis.gpkg'

    # Export de la table vegetation en couche vecteur
    exportVectorByOgr2ogr(connexion_dic["dbname"], filetablevegin, tab_ref, user_name=connexion_dic["user_db"], password=connexion_dic["password_db"], ip_host=connexion_dic["server_db"], num_port=connexion_dic["port_number"],schema_name=connexion_dic["schema"], format_type='GPKG')

    # Superimpose si souhaité
    if superimpose_choice :
        img_ndvi_si_wtr = repertory + os.sep + 'img_ndvi_si_hiver' + extension
        cmd_superimpose = "otbcli_Superimpose -inr %s -inm %s -out %s" %(img_ndvi_spg,img_ndvi_wtr, img_ndvi_si_wtr)
        try:
            os.system(cmd_superimpose)
            img_ndvi_wtr = img_ndvi_si_wtr
        except :
            raise Exception("La fonction Superimpose s'est mal déroulée.")

    # Calcul du masque de caduques
    cmd_mask_cadu = "otbcli_BandMath -il %s %s -out '%s?&nodata=-99' uint8 -exp '(abs(im2b1-im1b1)>%s)?1:0'" %(img_ndvi_spg, img_ndvi_wtr, image_cadu_out, seuil)
    try:
        os.system(cmd_mask_cadu)
    except :
        raise Exception("Les deux images NDVI n'ont pas la même emprise. Veuillez relancer le programme en sélectionnant l'option de Superimpose")

    # Calcul du masque de persistants
    cmd_mask_pers = "otbcli_BandMath -il %s %s -out '%s?&nodata=-99' uint8 -exp '(abs(im2b1-im1b1)<=%s)?1:0'" %(img_ndvi_spg, img_ndvi_wtr, image_pers_out, seuil)
    os.system(cmd_mask_pers)


    # Statistiques zonales sur les polygones de formes végétales concernées : tous les segments appartennant à la strate arborée et arbustive
    col_to_add_list = ["count"]
    col_to_delete_list = ["unique", "range", "max", "median", "mean","std", "sum"]
    class_label_dico = {0:'non', 1:'oui'}
    statisticsVectorRaster(image_cadu_out, filetablevegin, vect_fv_cadu_out, band_number=1,enable_stats_all_count = False, enable_stats_columns_str = False, enable_stats_columns_real = True, col_to_delete_list = col_to_delete_list, col_to_add_list = col_to_add_list, class_label_dico = class_label_dico, path_time_log = "", clean_small_polygons = False, format_vector = 'GPKG',  save_results_intermediate= False, overwrite= True)

    statisticsVectorRaster(image_pers_out, filetablevegin, vect_fv_pers_out, band_number=1,enable_stats_all_count = False, enable_stats_columns_str = False, enable_stats_columns_real = True, col_to_delete_list = col_to_delete_list, col_to_add_list = col_to_add_list, class_label_dico = class_label_dico, path_time_log = "", clean_small_polygons = False, format_vector = 'GPKG',  save_results_intermediate= False, overwrite= True)

    # Import des données dans la BD et concaténation des colonnes

    table_cadu = 'tab_fv_cadu'
    importVectorByOgr2ogr(connexion_dic["dbname"], vect_fv_cadu_out, table_cadu, user_name=connexion_dic["user_db"], password=connexion_dic["password_db"], ip_host=connexion_dic["server_db"], num_port=connexion_dic["port_number"],schema_name=connexion_dic["schema"], epsg = str(2154))

    table_pers = 'tab_fv_pers'
    importVectorByOgr2ogr(connexion_dic["dbname"], vect_fv_pers_out, table_pers, user_name=connexion_dic["user_db"], password=connexion_dic["password_db"], ip_host=connexion_dic["server_db"], num_port=connexion_dic["port_number"],schema_name=connexion_dic["schema"], epsg = str(2154))

    query = """
    DROP TABLE IF EXISTS tab_indic_pers_cadu;
    CREATE TABLE tab_indic_pers_cadu AS
        SELECT t1.ogc_fid AS fid, t1.oui AS pers_count, t2.oui AS cadu_count
        FROM %s AS t1, %s AS t2
        WHERE t1.ogc_fid = t2.ogc_fid;
    """ %(table_pers,table_cadu)

    # Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    # Update de l'attribut perc_caduque et perc_persistant

    query = """
    UPDATE %s AS t SET %s = t2.pers_count FROM tab_indic_pers_cadu AS t2 WHERE t.fid = t2.fid and t.strate in ('A', 'Au');
    """ %(tab_ref, columns_indics_name[0])

    query += """
    UPDATE %s AS t SET %s = t2.cadu_count FROM tab_indic_pers_cadu AS t2 WHERE t.fid = t2.fid and t.strate in ('A', 'Au');
    """ %(tab_ref, columns_indics_name[1])

    # Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    # Suppression du dossier temporaire
    if not save_intermediate_result:
        if os.path.exists(image_pers_out):
            removeFile(image_pers_out)
        if os.path.exists(image_cadu_out):
            removeFile(image_cadu_out)
        if os.path.exists(vect_fv_pers_out):
            removeFile(vect_fv_pers_out)
        if os.path.exists(vect_fv_cadu_out):
            removeFile(vect_fv_cadu_out)
        if os.path.exists(filetablevegin):
            removeFile(filetablevegin)
        if os.path.exists(img_ndvi_si_wtr):
            removeFile(img_ndvi_si_wtr)

    # Suppression des tables intermédiaires
    dropTable(connexion,table_cadu)
    dropTable(connexion,table_pers)
    dropTable(connexion, 'tab_indic_pers_cadu')

    return

###########################################################################################################################################
# FONCTION coniferousDeciduousIndicators()                                                                                                #
###########################################################################################################################################
def coniferousDeciduousIndicators(connexion, connexion_dic, img_ref, tab_ref, seuil = 1300, columns_indics_name = ['perc_conifere', 'perc_feuillu'], repertory = '',save_intermediate_result = False, debug = 0):
    """
    Rôle : cette fonction permet de calculer le pourçentage de feuillus et de conifères sur les polygones en entrée

    Paramètres :
        connexion : connexion à la base donnée et au schéma correspondant
        connexion_dic : dictionnaire des paramètres de connexion à la base de données
        img_ref : image Pléiades d'entrée
        tab_ref : nom de la  table contenant les polygones de végétation détaillés de type nomduschema.nomdelatable
        seuil : valeur du seuil de PIR pour distinguer les conifères des feuillus. Par défaut : 1300
        columns_indics_name : liste des noms de colonne des indicateurs à implémenter. Par défaut :['perc_conifere', 'perc_feuillu']
        repertory : repertoire de sauvegarde des fichiers intermédiaire. Par défaut : ''
        save_intermediate_result : garder ou non les fichiers temporaires
        debug : niveau de debug pour l'affichage des commentaires. Par défaut : 0

    """
    # Création du dossier temporaire et des fichiers temporaires
    if repertory == '':
        repertory = os.path.dirname(img_ref) + os.sep + 'TMP_CALC_INDICATEURS_CONFEUI'
        if not os.path.isdir(repertory):
            os.makedirs(repertory)
    extension = os.path.splitext(img_ref)[1]

    image_conif_out = repertory + os.sep + 'img_mask_coniferous' + extension
    image_feuill_out = repertory + os.sep + 'img_mask_feuillus' + extension

    vect_fv_conif_out = repertory + os.sep + 'vect_fv_stats_conif.gpkg'
    vect_fv_feuill_out = repertory + os.sep + 'vect_fv_stats_feuil.gpkg'

    # Calcul du masque de conifères
    cmd_mask_conif = "otbcli_BandMath -il %s -out %s -exp '(im1b4<%s)?1:0'" %(img_ref, image_conif_out, seuil)
    os.system(cmd_mask_conif)

    # Calcul du masque de feuillus
    cmd_mask_decid = "otbcli_BandMath -il %s -out %s -exp '(im1b4>=%s)?1:0'" %(img_ref, image_feuill_out, seuil)
    os.system(cmd_mask_decid)

    # Export de la table vegetation en couche vecteur
    filetablevegin = repertory + os.sep + 'couche_vegetation_bis.gpkg'

    exportVectorByOgr2ogr(connexion_dic["dbname"], filetablevegin, tab_ref, user_name=connexion_dic["user_db"], password=connexion_dic["password_db"], ip_host=connexion_dic["server_db"], num_port=connexion_dic["port_number"],schema_name=connexion_dic["schema"], format_type='GPKG')

    # Statistiques zonales sur les polygones de formes végétales concernées : tous les segments appartennant à la strate arborée et arbustive
    col_to_add_list = ["count"]
    col_to_delete_list = ["unique", "range", "max", "median", "mean","std", "sum"]
    class_label_dico = {0:'non', 1:'oui'}
    statisticsVectorRaster(image_conif_out, filetablevegin, vect_fv_conif_out, band_number=1,enable_stats_all_count = False, enable_stats_columns_str = False, enable_stats_columns_real = True, col_to_delete_list = col_to_delete_list, col_to_add_list = col_to_add_list, class_label_dico = class_label_dico, path_time_log = "", clean_small_polygons = False, format_vector = 'GPKG',  save_results_intermediate= False, overwrite= True)

    statisticsVectorRaster(image_feuill_out, filetablevegin, vect_fv_feuill_out, band_number=1,enable_stats_all_count = False, enable_stats_columns_str = False, enable_stats_columns_real = True, col_to_delete_list = col_to_delete_list, col_to_add_list = col_to_add_list, class_label_dico = class_label_dico, path_time_log = "", clean_small_polygons = False, format_vector = 'GPKG',  save_results_intermediate= False, overwrite= True)

    # Import des données dans la BD et concaténation des colonnes

    table_conif = 'tab_fv_conif'
    importVectorByOgr2ogr(connexion_dic["dbname"], vect_fv_conif_out, table_conif, user_name=connexion_dic["user_db"], password=connexion_dic["password_db"], ip_host=connexion_dic["server_db"], num_port=connexion_dic["port_number"],schema_name=connexion_dic["schema"], epsg=str(2154))

    table_feuill = 'tab_fv_feuill'
    importVectorByOgr2ogr(connexion_dic["dbname"], vect_fv_feuill_out, table_feuill, user_name=connexion_dic["user_db"], password=connexion_dic["password_db"], ip_host=connexion_dic["server_db"], num_port=connexion_dic["port_number"],schema_name=connexion_dic["schema"], epsg=str(2154))

    query = """
    DROP TABLE IF EXISTS tab_indic_conif_decid;
    CREATE TABLE tab_indic_conif_decid AS
        SELECT t1.ogc_fid as fid, t1.oui AS conif_perc, t2.oui AS decid_perc
        FROM %s AS t1, %s AS t2
        WHERE t1.ogc_fid = t2.ogc_fid;
    """ %(table_conif, table_feuill)

    # Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    # Update de l'attribut perc_conif et perc_decid

    query = """
    UPDATE %s AS t SET %s = t2.conif_perc FROM tab_indic_conif_decid AS t2 WHERE t.fid = t2.fid and t.strate in ('A', 'Au');
    """ %(tab_ref, columns_indics_name[0])

    query += """
    UPDATE %s AS t SET %s = t2.decid_perc FROM tab_indic_conif_decid AS t2 WHERE t.fid = t2.fid and t.strate in ('A', 'Au');
    """ %(tab_ref, columns_indics_name[1])

    # Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    # Suppression du dossier temporaire
    if not save_intermediate_result:
        if os.path.exists(image_conif_out):
            removeFile(image_conif_out)
        if os.path.exists(image_feuill_out):
            removeFile(image_feuill_out)
        if os.path.exists(vect_fv_conif_out):
            removeFile(vect_fv_conif_out)
        if os.path.exists(vect_fv_feuill_out):
            removeFile(vect_fv_feuill_out)
        if os.path.exists(filetablevegin):
            removeFile(filetablevegin)

    # Suppression des tables intermédiaires
    dropTable(connexion, table_conif)
    dropTable(connexion, table_feuill)
    dropTable(connexion, 'tab_indic_conif_decid')

    return

###########################################################################################################################################
# FONCTION typeOfGroundIndicator()                                                                                                        #
###########################################################################################################################################
def typeOfGroundIndicator(connexion, connexion_dic, img_ref, img_ndvi_wtr, tab_ref, seuil  = 0.3, column_indic_name = 'type_sol', column_indic_persistant = 'perc_persistant', repertory = '', save_intermediate_result = False, debug = 0):
    """
    Rôle : cette fonction permet d'indiquer si le sol sous-jacent à la végétation est de type perméable ou imperméable

    Paramètres :
        connexion : connexion à la base donnée et au schéma correspondant
        connexion_dic : dictionnaire des paramètres de connexion à la base de données et au schéma correspondant
        image_ref : image Pléiades de référence
        tab_ref : nom de la  table contenant les polygones de végétation détaillés de type nomduschema.nomdelatable
        seuil : valeur du seuil de NDVI pour distinguer les surfaces perméables d'imperméables. Par défaut : 0.3
        column_indic_name : nom de la colonne de l'indicateur de type de sol. Par défaut : 'type_sol'
        repertory : repertoire de sauvegarde des fichiers intermédiaires. Par défaut : ''
        save_intermediate_result : garder ou non les fichiers temporaires
        debug : niveau de debug pour l'affichage des commentaires. Par défaut : 0

    """
    # Création du dossier temporaire et des fichiers temporaires
    if repertory == '':
        repertory = os.path.dirname(img_ref) + os.sep + 'TMP_CALC_INDICATEURS_TYPESOL'
        if not os.path.isdir(repertory):
            os.makedirs(repertory)
    extension = os.path.splitext(img_ref)[1]
    img_surf_veg = repertory + os.sep + 'img_mask_surfacevegetalisee' + extension
    img_surf_nonveg = repertory + os.sep + 'img_mask_surfacenonvegetalisee' + extension

    vect_fv_surfveg_out = repertory + os.sep + 'vect_fv_stats_surfacevegetalisee.gpkg'
    vect_fv_surfnonveg_out = repertory + os.sep + 'vect_fv_stats_surfacenonvegetalisee.gpkg'

    # Export de la table vegetation en couche vecteur gpkg
    filetablevegin = repertory + os.sep + 'couche_vegetation_bis.gpkg'

    exportVectorByOgr2ogr(connexion_dic["dbname"], filetablevegin, tab_ref, user_name=connexion_dic["user_db"], password=connexion_dic["password_db"], ip_host=connexion_dic["server_db"], num_port=connexion_dic["port_number"],schema_name=connexion_dic["schema"], format_type='GPKG')

    # Calcul du masque perméable
    cmd_mask_surfveg = "otbcli_BandMath -il %s -out '%s?&nodata=-99' uint8 -exp '(im1b1>=%s)?1:0'" %(img_ndvi_wtr, img_surf_veg, seuil)
    os.system(cmd_mask_surfveg)

    # Calcul du masque imperméable
    cmd_mask_surfnonveg = "otbcli_BandMath -il %s -out '%s?&nodata=-99' uint8 -exp '(im1b1<%s)?1:0'" %(img_ndvi_wtr, img_surf_nonveg, seuil)
    os.system(cmd_mask_surfnonveg)

    # Statistiques zonales sur les polygones de formes végétales concernées : tous les segments appartennant à la strate arborée et arbustive
    col_to_add_list = ["count"]
    col_to_delete_list = ["unique", "range", "max", "median", "mean","std", "sum"]
    class_label_dico = {0:'non', 1:'oui'}
    statisticsVectorRaster(img_surf_veg, filetablevegin, vect_fv_surfveg_out, band_number=1,enable_stats_all_count = False, enable_stats_columns_str = False, enable_stats_columns_real = True, col_to_delete_list = col_to_delete_list, col_to_add_list = col_to_add_list, class_label_dico = class_label_dico, path_time_log = "", clean_small_polygons = False, format_vector = 'GPKG',  save_results_intermediate= False, overwrite= True)

    statisticsVectorRaster(img_surf_nonveg, filetablevegin, vect_fv_surfnonveg_out, band_number=1,enable_stats_all_count = False, enable_stats_columns_str = False, enable_stats_columns_real = True, col_to_delete_list = col_to_delete_list, col_to_add_list = col_to_add_list, class_label_dico = class_label_dico, path_time_log = "", clean_small_polygons = False, format_vector = 'GPKG',  save_results_intermediate= False, overwrite= True)

    # Import des données dans la BD et concaténation des colonnes
    table_surfveg = 'tab_fv_surfveg'
    importVectorByOgr2ogr(connexion_dic["dbname"], vect_fv_surfveg_out, table_surfveg, user_name=connexion_dic["user_db"], password=connexion_dic["password_db"], ip_host=connexion_dic["server_db"], num_port=connexion_dic["port_number"],schema_name=connexion_dic["schema"], epsg=str(2154))

    table_surfnonveg = 'tab_fv_surfnonveg'
    importVectorByOgr2ogr(connexion_dic["dbname"], vect_fv_surfnonveg_out, table_surfnonveg, user_name=connexion_dic["user_db"], password=connexion_dic["password_db"], ip_host=connexion_dic["server_db"], num_port=connexion_dic["port_number"],schema_name=connexion_dic["schema"], epsg=str(2154))

    query = """
    DROP TABLE IF EXISTS tab_indic_surfveg_nonveg;
    CREATE TABLE tab_indic_surfveg_nonveg AS
        SELECT t1.ogc_fid AS fid, t1.oui AS surfveg_count, t2.oui AS surfnonveg_count
        FROM %s AS t1, %s AS t2
        WHERE t1.ogc_fid = t2.ogc_fid;
    """ %(table_surfveg,table_surfnonveg)

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Update de l'attribut perc_caduque et perc_persistant
    query = """
     UPDATE %s AS t SET %s = 'surface vegetalisee' FROM tab_indic_surfveg_nonveg AS t2 WHERE t.fid = t2.fid AND t2.surfveg_count >= 50.0;
    """ %(tab_ref, column_indic_name)

    query += """
     UPDATE %s AS t SET %s = 'surface non vegetalisee' FROM tab_indic_surfveg_nonveg AS t2 WHERE t.fid = t2.fid AND t2.surfveg_count < 50.0;
    """ %(tab_ref, column_indic_name)

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Correction pour les boisements et la strate herbacée --> hypothèse que ce n'est que du sol végétalisé sous-jacent
    # La détection des boisements n'est pas encore optimisée étant donné que les tâches arborées et arbustives sont pour l'instant classées en "boisement"
    query = """
    UPDATE %s AS t SET %s = 'surface vegetalisee' WHERE t.fv in ('BOA', 'BOAu', 'PR', 'C');
    """ %(tab_ref, column_indic_name)

    #query = """
    #UPDATE %s AS t SET %s = 'surface vegetalisee' WHERE t.fv in ('H', 'C');
    #""" %(tab_ref, column_indic_name)

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Correction pour les couverts persistants --> on ne fournit aucune information
    query = """
    UPDATE %s AS t SET %s = '' WHERE t.%s >= 80.0;
    """ %(tab_ref, column_indic_name, column_indic_persistant)

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Suppression du dossier temporaire
    if not save_intermediate_result:
        pass

    # Suppression des tables intermédiaires
    dropTable(connexion, 'tab_indic_surfveg_nonveg')
    dropTable(connexion, table_surfveg)
    dropTable(connexion, table_surfnonveg)

    return

###########################################################################################################################################
# FONCTION landscapeIndicator()                                                                                                           #
###########################################################################################################################################
def landscapeIndicator(connexion, connexion_dic, img_landscape, tab_fv, column_indic_name = 'paysage', dic_ldsc_class = {"milieu_urbanise" : 1, "voirie_et_infrastructure" : 2, "etendue_et_cours_eau" : 3, "milieu_agricole_et_forestier" : 4}, repertory = '', save_intermediate_result = False, debug = 0):
    """
    Rôle : attribut la classe du paysage dans lequel s'inscrit la forme végétale

    Paramètres :
        connexion : connexion à la base donnée et au schéma correspondant
        connexion_dic : dictionnaire des paramètres de connexion à la base de données et au schéma correspondant
        img_landscape : couche raster des paysages
        tab_fv : nom de la table contenant les formes végétalisées
        dic_ldsc_class : dictionnaire des codes attribués aux quatres classes de premier niveau des paysages. Par défaut : {"milieu_urbanise" : 1, "voirie_et_infrastructure" : 2, "etendue_et_cours_eau" : 3, "milieu_agricole_et_forestier" : 4}
        repertory : repertoire de sauvegarde des fichiers intermédiaires. Par défaut : ''
        save_intermediate_result : choix de sauvegarde des données intermédiaires. Par défaut : False
        debug : niveau de débug pour afficher les message. Par défaut : 0

    """

    # Création du dossier temporaire et des fichiers temporaires
    if repertory == '':
        repertory = os.path.dirname(img_landscape) + os.sep + 'TMP_CALC_CALC_PAYSAGES'
        if not os.path.isdir(repertory):
            os.makedirs(repertory)
    extension = os.path.splitext(img_landscape)[1]

    # Export de la table vegetation en couche vecteur gpkg
    filetablevegin = repertory + os.sep + 'couche_vegetation_bis.gpkg'

    exportVectorByOgr2ogr(connexion_dic["dbname"], filetablevegin, tab_fv, user_name=connexion_dic["user_db"], password=connexion_dic["password_db"], ip_host=connexion_dic["server_db"], num_port=connexion_dic["port_number"],schema_name=connexion_dic["schema"], format_type='GPKG')

    vector_output = repertory + os.sep + 'sgts_vegetation_cross_landscape.gpkg'

    # Calcul de la classe majoritaire par segments herbacé
    col_to_add_list = ["majority"]
    col_to_delete_list = ["min", "max", "mean", "unique", "sum", "std", "range", "median", "minority" ]
    class_label_dico = {}
    statisticsVectorRaster(img_landscape, filetablevegin, vector_output, band_number=1, enable_stats_all_count = False, enable_stats_columns_str = True, enable_stats_columns_real = False, col_to_delete_list = col_to_delete_list, col_to_add_list = col_to_add_list, class_label_dico = class_label_dico, path_time_log = "", clean_small_polygons = False, format_vector = 'GPKG',  save_results_intermediate= False, overwrite= True)

    # Import en base de la ocuche vecteur
    tab_cross = 'tab_cross_land'
    importVectorByOgr2ogr(connexion_dic["dbname"], vector_output, tab_cross, user_name=connexion_dic["user_db"], password=connexion_dic["password_db"], ip_host=connexion_dic["server_db"], num_port=connexion_dic["port_number"], schema_name=connexion_dic["schema"], epsg=str(2154))

    # Attribution du label 'PR' (prairie) ou 'C' (culture)
    query = """
    UPDATE %s AS t1 SET paysage = '1' FROM %s AS t2 WHERE t2.majority = '%s' AND t1.fid = t2.ogc_fid;
    """  %(tab_fv, tab_cross, dic_ldsc_class["milieu_urbanise"])

    query += """
    UPDATE %s AS t1 SET paysage = '2' FROM %s AS t2 WHERE t2.majority = '%s' AND t1.fid = t2.ogc_fid;
    """  %(tab_fv, tab_cross, dic_ldsc_class["voirie_et_infrastructure"])

    query += """
    UPDATE %s AS t1 SET paysage = '3' FROM %s AS t2 WHERE t2.majority = '%s' AND t1.fid = t2.ogc_fid;
    """  %(tab_fv, tab_cross, dic_ldsc_class["etendue_et_cours_eau"])

    query += """
    UPDATE %s AS t1 SET paysage = '4' FROM %s AS t2 WHERE t2.majority = '%s' AND t1.fid = t2.ogc_fid;
    """  %(tab_fv, tab_cross, dic_ldsc_class["milieu_agricole_et_forestier"])

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Suppression du dossier temporaire
    if not save_intermediate_result:
        pass

    # Suppression des tables intermédiaires
    dropTable(connexion, tab_cross)

    return
