#!/usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.               #
#############################################################################

# Import des librairies Python
import os,sys,glob

# Import des librairies de /libs
from libs.Lib_display import bold,red,yellow,cyan,endC
from libs.CrossingVectorRaster import statisticsVectorRaster
from libs.Lib_raster import rasterizeVector
from libs.Lib_postgis import readTable, executeQuery, addColumn, addUniqId, addIndex, addSpatialIndex, dropTable, dropColumn, exportVectorByOgr2ogr, importVectorByOgr2ogr, closeConnection, topologyCorrections

###########################################################################################################################################
# FONCTION vegetationMask()                                                                                                               #
###########################################################################################################################################
def vegetationMask(img_input, img_output, num_class = {"bati" : 1, "route" : 2, "sol nu" : 3, "eau" : 4, "vegetation" : 5}, overwrite = False):
    """
    Rôle : créé un masque de végétation à partir d'une image classifiée

    Paramètres :
        img_input : image classée en 5 classes
        img_output : image binaire : 1 pour la végétation et -1 pour non végétation
        num_class : dictionnaire reliant le nom de la classe au label, par défaut : {"bati" : 1, "route" : 2, "sol nu" : 3, "eau" : 4, "vegetation" : 5}
        overwrite : paramètre de ré-écriture, par défaut : False
    """

    # Verification de la non existence du fichier de sortie
    if overwrite == True and os.path.exists(img_output):
        os.remove(img_output)
    elif overwrite == False and os.path.exists(img_output):
        raise NameError(bold + red + "vegetationMask() : le fichier %s existe déjà" %(img_output)+ endC)

    # Calcul à l'aide de l'otb
    exp = '"(im1b1==' + str(num_class["vegetation"]) + '?1:-1)"'

    cmd_mask = "otbcli_BandMath -il %s -out %s -exp %s" %(img_input, img_output, exp)

    exitCode = os.system(cmd_mask)

    if exitCode != 0:
        print(cmd_mask)
        raise NameError(bold + red + "vegetationMask() : une erreur est apparue lors de la création du masque de végétation (commande otbcli_BandMath)" + endC)

    return

###########################################################################################################################################
# FONCTION segmentationImageVegetetation()                                                                                                #
###########################################################################################################################################
def segmentationImageVegetetation(img_ref, img_input, file_output, param_minsize = 10, num_class = {"bati" : 1, "route" : 2, "sol nu" : 3, "eau" : 4, "vegetation" : 5}, format_vector='GPKG', save_intermediate_result = True, overwrite = True):
    """
    Rôle : segmente l'image en entrée à partir d'une fonction OTB_Segmentation MEANSHIFT

    Paramètre :
        img_ref : image de référence Pléiades rvbpir
        img_input : image classée en 5 classes
        file_output : fichier vecteur de sortie correspondant au résultat de segmentation
        param_minsize : paramètre de la segmentation : taille minimale des segments, par défaut : 10
        num_class : dictionnaire reliant le nom de la classe au label, par défaut : {"bati" : 1, "route" : 2, "sol nu" : 3, "eau" : 4, "vegetation" : 5}
        format_vector : format du fichier vecteur de sortie, par défaut : GPKG
        save_intermediate_result : paramètre de sauvegarde des fichiers intermédiaire, par défaut : True
        overwrite : paramètre de ré-écriture des fichiers. Par défaut : False

    Sortie :
        file_output : couche vecteur de sortie correspondant au résultat de segmentation
    """

    # Utilisation d'un fichier temporaire pour la couche masque
    repertory_output = os.path.dirname(file_output)
    file_name = os.path.splitext(os.path.basename(file_output))[0]
    file_name = file_name.replace("vect", "img")
    extension = os.path.splitext(img_input)[1]

    SUFFIX_MASK_VEG = "_mask_veg"
    mask_veg = repertory_output + os.sep + file_name + SUFFIX_MASK_VEG + extension

    if overwrite:
        if os.path.exists(mask_veg):
            os.remove(mask_veg)
        if os.path.exists(file_output):
            os.remove(file_output)

    # Création du masque de végétation
    vegetationMask(img_input, mask_veg, num_class)

    # Calcul de la segmentation Meanshift
    sgt_cmd = "otbcli_Segmentation -in %s -mode vector -mode.vector.out %s -mode.vector.inmask %s -filter meanshift  -filter.meanshift.minsize %s" %(img_ref, file_output, mask_veg, param_minsize)

    exitCode = os.system(sgt_cmd)

    if exitCode != 0:
        print(sgt_cmd)
        raise NameError(bold + red + "segmentationVegetation() : une erreur est apparue lors de la segmentation de l'image (commande otbcli_Segmentation)." + endC)

    if not save_intermediate_result:
        removeFile(mask_veg)

    return

###########################################################################################################################################
# FONCTION classificationVerticalStratum()                                                                                                #
###########################################################################################################################################
def classificationVerticalStratum(connexion, connexion_dic, img_ref, output_layers, sgts_input, raster_dic, tab_ref = 'segments_vegetation',dic_seuil = {"seuil_h1" : 3, "seuil_h2" : 1, "seuil_h3" : 2, "seuil_txt" : 11, "seuil_touch_arbo_vs_herba" : 15, "seuil_ratio_surf" : 25, "seuil_arbu_repres" : 20}, format_type = 'GPKG', save_intermediate_result = True, overwrite = False, debug = 0):
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

    # Fichiers intermédiaires
    repertory_output = os.path.dirname(output_layers["output_stratesv"])
    file_name = os.path.splitext(os.path.basename(sgts_input))[0]
    extension_vecteur = os.path.splitext(output_layers["output_stratesv"])[1]

    #####################################################################
    ##    Collect des statistiques de hauteur et texture pour chaque   ##
    ##                             segment                             ##
    #####################################################################

    if debug >= 1:
        print(bold + "Collecte des valeurs médianes de hauteur et de texture pour chaque segment." + endC)

    ## Collecte données de hauteur pour chaque segment
    file_mnh_out = repertory_output + os.sep + file_name + "MNH" + extension_vecteur

    if os.path.exists(file_mnh_out) and overwrite == True:
        os.remove(file_mnh_out)

    # Calcul de la valeur médiane de hauteur pour chaque segment de végétation
    calc_statMedian(sgts_input, raster_dic["MNH"], file_mnh_out)

    # Export du fichier vecteur des segments végétation avec une valeur médiane de hauteur dans la BD
    tablename_mnh = "table_sgts_mnh"
    importVectorByOgr2ogr(connexion_dic["dbname"], file_mnh_out, tablename_mnh, user_name=connexion_dic["user_db"], password=connexion_dic["password_db"], ip_host=connexion_dic["server_db"], num_port=connexion_dic["port_number"], schema_name=connexion_dic["schema"], epsg=str(2154))

    ## Collecte données de texture pour chaque segment
    file_txt_out = repertory_output + os.sep + file_name + "TXT" + extension_vecteur

    if os.path.exists(file_txt_out) and overwrite == True:
        os.remove(file_txt_out)

    # Calcul de la valeur médiane de texture pour chaque segment de végétation
    calc_statMedian(sgts_input, raster_dic["TXT"], file_txt_out)

    # Export du fichier vecteur des segments végétation avec une valeur médiane de texture dans la BD
    tablename_txt = "table_sgts_txt"
    importVectorByOgr2ogr(connexion_dic["dbname"], file_txt_out, tablename_txt, user_name=connexion_dic["user_db"], password=connexion_dic["password_db"], ip_host=connexion_dic["server_db"], num_port=connexion_dic["port_number"], schema_name=connexion_dic["schema"],  epsg=str(2154))


    # Supprimer le fichier si on ne veut pas les sauvegarder
    if not save_intermediate_result :
        os.remove(file_mnh_out)
        os.remove(file_txt_out)


    # Merge des colonnes de statistiques en une seule table "segments_vegetation_ini"
    tab_sgt_ini = 'segments_vegetation_ini_t0'
    dropTable(connexion, tab_sgt_ini)
    query = """
    CREATE TABLE %s AS
        SELECT t2.dn, t2.geom, t2.median AS mnh, t1.median AS txt
        FROM %s AS t1, %s AS t2
        WHERE t1.dn = t2.dn;
    """ %(tab_sgt_ini, tablename_txt, tablename_mnh)

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
    query = """
    CREATE TABLE %s AS
        SELECT public.ST_MAKEVALID((public.ST_DUMP(t.geom)).geom::public.geometry(Polygon,2154)) as geom, t.mnh, t.txt
        FROM %s as t
    """ %(tab_ref, tab_sgt_ini)

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
    addColumn(connexion, tab_ref, 'strate', 'varchar(100)')

    #if not save_intermediate_result:
    #    dropTable(connexion, tab_sgt_txt_val0)

    #####################################################################
    ## Première étape : classification générale, à partir de règles de ##
    ##                  hauteur et de texture                          ##
    #####################################################################

    if debug >= 2:
        print(bold + "Première étape : classification générale, à partir de règles de hauteur et de texture" + endC)

    if dic_seuil["height_or_texture"] == "height":
        if dic_seuil["texture_option"] == False :
            query = """
            UPDATE %s as t SET strate = 'A' WHERE t.mnh  > %s;
            """ %(tab_ref, dic_seuil["height_treeshrub_thr"])

            query += """
            UPDATE %s as t SET strate = 'Au' WHERE t.mnh  <= %s AND t.mnh > %s;
            """ %(tab_ref, dic_seuil["height_treeshrub_thr"], dic_seuil["height_shrubgrass_thr"])

            query += """
            UPDATE %s as t SET strate = 'H' WHERE t.mnh <= %s;
            """ %(tab_ref, dic_seuil["height_shrubgrass_thr"])


    else :
        query = """
        UPDATE %s as t SET strate = 'A' WHERE t.txt < %s AND t.mnh  > %s;
        """ %(tab_ref, dic_seuil["texture_thr"],dic_seuil["height_treeshrub_thr"])

        query += """
        UPDATE %s as t SET strate = 'Au' WHERE t.txt < %s AND  t.mnh  <= %s;
        """ %(tab_ref, dic_seuil["texture_thr"],dic_seuil["height_treeshrub_thr"])

        query += """
        UPDATE %s as t SET strate = 'H' WHERE t.txt  >= %s;
        """ %(tab_ref, dic_seuil["texture_thr"])

    # query += """
    # UPDATE %s as t SET strate = 'H' WHERE t.txt < %s AND t.mnh <= %s;
    # """ %(tab_ref, dic_seuil["texture_thr"], dic_seuil["height_shrubgrass_thr"])

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    ##############################################################################
    ### ajout EB 01/11/24 : enregistrement fic intermediaires resultats 1ere etape = > a supprimer apres le test
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
    ##############################################################################

    #####################################################################
    ## Deuxième étape : reclassification des segments arbustifs        ##
    #####################################################################
    if debug >= 2:
        print(bold + "Deuxième étape : reclassification des segments arbustifs" + endC)

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


    # Création table "arbu_de_rgpt"(fid, geom, fid_rgpt) correspondant aux arbustes "regroupés" qui touchent d'autres segments arbustifs
    tab_arbu_rgpt = 'arbu_de_rgpt'
    query = """
    DROP TABLE IF EXISTS %s;
    CREATE TABLE %s AS
        SELECT t1.fid, t1.geom, t4.fid_rgpt
                        FROM (SELECT * FROM %s WHERE strate='Au') AS t1,
                             (SELECT t3.fid AS fid, t2.fid as fid_rgpt
                                FROM (SELECT * FROM %s WHERE nb_sgt>1) as t2,
                                tab_interm_arbuste as t3
                                WHERE public.ST_INTERSECTS(t3.geom, t2.geom)) as t4
                        WHERE t1.fid = t4.fid;
    """ %(tab_arbu_rgpt,tab_arbu_rgpt, tab_ref, tab_rgpt_arbu)

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Création index spatial
    addSpatialIndex(connexion, tab_arbu_rgpt)

    # Création d'un index sur une colonne
    addIndex(connexion, tab_arbu_rgpt, 'fid', 'idx_arbu_de_rgpt')

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
                        FROM (SELECT * FROM %s WHERE nb_sgt<=1) as t3, tab_interm_arbuste AS t2
                    WHERE public.ST_INTERSECTS(t2.geom,t3.geom)) as t4
                        WHERE t1.fid = t4.fid;
    """ %(tab_arbu_uniq, tab_arbu_uniq, tab_ref, tab_rgpt_arbu)

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Création index spatial
    addSpatialIndex(connexion, tab_arbu_uniq)
    # Création d'un index sur une colonne
    addIndex(connexion, tab_arbu_uniq, 'fid', 'idx_arbu_uniq')

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

    # Table contenant les identifiants des segments arbustifs isolés, la longueur de sa frontière et la longueur de sa frontière en contact avec segments arborés

    query = """
    CREATE TABLE arbu_isole_touch_arbo AS
        SELECT t1.fid, t1.geom, public.ST_PERIMETER(t1.geom) AS long_bound_arbu, t2.long_bound_inters_arbo AS long_bound_inters_arbo
        FROM (SELECT t3.fid, SUM(public.ST_LENGTH(t3.geom_bound_inters_arbo)) AS long_bound_inters_arbo
                FROM (SELECT t1.fid, t1.geom, arbre.fid AS fid_arbo, public.ST_INTERSECTION(public.ST_BOUNDARY(t1.geom), public.ST_INTERSECTION(t1.geom, arbre.geom)) AS geom_bound_inters_arbo
                        FROM  arbu_uniq AS t1, (SELECT fid, geom FROM %s WHERE strate = 'A') as arbre
                        WHERE public.ST_INTERSECTS(t1.geom,arbre.geom) and t1.fid not in (SELECT t1.fid
                                                                                    FROM (SELECT geom FROM %s WHERE strate = 'H') AS herbe, arbu_uniq as t1
                                                                                    WHERE public.ST_INTERSECTS(herbe.geom, t1.geom)
                                                                                    GROUP BY t1.fid)) AS t3
                GROUP BY t3.fid) AS t2, arbu_uniq AS t1
    WHERE t1.fid = t2.fid;
    """ %(tab_ref, tab_ref)

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
                    FROM  arbu_uniq AS t1, (SELECT fid, geom FROM %s WHERE strate = 'H') AS herbe
                    WHERE public.ST_INTERSECTS(t1.geom,herbe.geom) AND t1.fid not in (SELECT t1.fid
                                                                                FROM (SELECT geom FROM %s WHERE strate = 'A') AS arbre, arbu_uniq AS t1
                                                                                WHERE public.ST_INTERSECTS(arbre.geom, t1.geom)
                                                                                GROUP BY t1.fid)
                    ) AS t2
             GROUP BY t2.fid
             ) AS t3, arbu_uniq AS t1
        WHERE t1.fid = t3.fid;
    """ %(tab_ref, tab_ref)

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

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

   # Création de la table "matable" contenant l'identifiant du segment arboré ou herbacé avec lequel le segment arbustif intersecte
    query = """
    CREATE TABLE matable AS (SELECT arbuste.fid AS id_arbu, sgt_herbarbo.fid AS id_sgt_t, sgt_herbarbo.strate AS strate_touch, abs(arbuste.mnh-sgt_herbarbo.mnh) AS diff_h
                                FROM (
                                    SELECT t1.*
                                    FROM %s AS t1, arbu_touch_herb_arbo_and_only_arbo AS t2
                                    WHERE t1.fid = t2.fid
                                    ) AS arbuste,
                                    (SELECT * FROM %s WHERE strate in ('A', 'H')) AS sgt_herbarbo
                                WHERE public.ST_INTERSECTS(arbuste.geom, sgt_herbarbo.geom));
    """ %(tab_ref, tab_ref)

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

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

    # Table contenant les identifiants des segments arbustifs isolés, la longueur de sa frontière et la longueur de sa frontière en contact avec segments arborés

    query = """
    DROP TABLE IF EXISTS arbu_isole_touch_arbo;
    CREATE TABLE arbu_isole_touch_arbo AS
        SELECT t1.fid, t1.geom
        FROM (SELECT t3.fid
                FROM (SELECT t1.fid, t1.geom, arbre.fid as fid_arbo, public.ST_INTERSECTION(public.ST_BOUNDARY(t1.geom),public.ST_INTERSECTION(t1.geom, arbre.geom)) AS geom_bound_inters_arbo
                        FROM  %s AS t1, (SELECT fid, geom FROM %s WHERE strate = 'A') as arbre
                        WHERE public.ST_INTERSECTS(t1.geom,arbre.geom) and t1.fid not in (SELECT t1.fid
                                                                                    FROM (SELECT geom FROM %s WHERE strate = 'H') AS herbe, %s as t1
                                                                                    WHERE public.ST_INTERSECTS(herbe.geom, t1.geom)
                                                                                    GROUP BY t1.fid)) AS t3
                GROUP BY t3.fid) AS t2, %s AS t1
        WHERE t1.fid = t2.fid;
    """ %(arbu_uniq, tab_ref, tab_ref, arbu_uniq, arbu_uniq)

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
                    FROM  %s AS t1, (SELECT fid, geom FROM %s WHERE strate = 'H') as herbe
                    WHERE public.ST_INTERSECTS(t1.geom,herbe.geom) and t1.fid not in (SELECT t1.fid
                                                                                FROM (SELECT geom FROM %s WHERE strate = 'A') AS arbre, %s AS t1
                                                                                WHERE public.ST_INTERSECTS(arbre.geom, t1.geom)
                                                                                GROUP BY t1.fid)
                    ) AS t2
             GROUP BY t2.fid
             ) AS t3, %s AS t1
        WHERE t1.fid = t3.fid;
    """ %(arbu_uniq, tab_ref, tab_ref, arbu_uniq, arbu_uniq)

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
        FROM arbu_isole_touch_arbo AS t1, (SELECT * FROM %s WHERE strate = 'A') AS t2
        WHERE public.ST_INTERSECTS(t1.geom, t2.geom)
        GROUP BY t1.fid, public.ST_AREA(t1.geom);
    """ %(tab_ref)

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)


    # Creation de la table arbu_uniq_diffh listant la différence de hauteur entre chaque segment arbustif isolé et les segments arborés collés
    query = """
    DROP TABLE IF EXISTS arbu_uniq_diffh;
    CREATE TABLE arbu_uniq_diffh AS
        SELECT t.fid AS fid_sgt, abs(t.mnh-t3.mnh) AS diff_mnh
        FROM (SELECT t1.* FROM %s AS t1, arbu_uniq_surf_stats AS t2 WHERE t1.fid = t2.fid_sgt) AS t,
        (SELECT * FROM %s WHERE strate = 'A') AS t3
        WHERE public.ST_INTERSECTS(t.geom, t3.geom);
    """ %(tab_ref, tab_ref)

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)


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


    # Création de la table arbu_uniq_surf_stats2 listant pour chaque segment sa surface et la surface globale des segments autres qui le colle
    query = """
    DROP TABLE IF EXISTS arbu_uniq_surf_stats2 ;
    CREATE TABLE arbu_uniq_surf_stats2 AS
        SELECT t1.fid AS fid_sgt, public.ST_AREA(t1.geom) AS surf_sgt, public.ST_AREA(public.ST_UNION(t2.geom)) AS surf_touch
        FROM arbu_touch_herb_arbo AS t1, (SELECT * FROM %s WHERE strate in ('A', 'H')) AS t2
        WHERE public.ST_INTERSECTS(t1.geom, t2.geom)
        GROUP BY t1.fid, public.ST_AREA(t1.geom);
    """ %(tab_ref)

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)


    # Creation de la table arbu_uniq_diffh listant la différence de hauteur entre chaque segment arbustif isolé et les segments arborés et herbacés collés
    query = """
    DROP TABLE IF EXISTS arbu_uniq_diffh2;
    CREATE TABLE arbu_uniq_diffh2 AS
        SELECT t.fid AS fid_sgt, t3.fid AS fid_touch, abs(t.mnh-t3.mnh) AS diff_mnh
        FROM (SELECT t1.* FROM %s AS t1, arbu_uniq_surf_stats2 AS t2 WHERE t1.fid = t2.fid_sgt) AS t,
            (SELECT * FROM %s WHERE strate in ('A', 'H')) AS t3
        WHERE public.ST_INTERSECTS(t.geom, t3.geom);
    """ %(tab_ref, tab_ref)

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)


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

    # Mise à jour du statut des segments arbustifs appartennant à un regroupement touchant peu d'arboré et bcp d'herbacé
    query = """
    UPDATE %s AS t1 SET strate = 'A'
            FROM (SELECT t1.fid AS fid_arbu, t2.fid AS fid_arbo, abs(t1.mnh - t2.mnh) AS diff_h
                    FROM (
                            SELECT t3.*
                            FROM %s AS t3, (SELECT t2.*
                                            FROM (SELECT *
                                                    FROM rgpt_herbarbotouch_longbound AS t
                                                    WHERE t.long_bound_inters_arbo * 100 / t.long_bound_arbu < %s AND t.long_bound_inters_herbe * 100 / t.long_bound_arbu >= %s
                                                ) AS t1,
                                                  arbu_de_rgpt AS t2, arbore AS t3
                                            WHERE t2.fid_rgpt = t1.fid AND public.ST_INTERSECTS(t2.geom, t3.geom)) AS t4
                            WHERE t3.fid = t4.fid) AS t1,
                        (SELECT * FROM %s WHERE strate = 'A') AS t2
                    WHERE public.ST_INTERSECTS(t1.geom, t2.geom)) AS t2
            WHERE t1.fid = t2.fid_arbu AND t2.diff_h <= %s;
    """ %(tab_ref, tab_ref, dic_seuil["shrub_touch_treevsgrass_perc"], dic_seuil["shrub_touch_grassvstree_perc"], tab_ref, dic_seuil["height_max_difference"])

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

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

    query = """
    UPDATE h_moys AS t1 SET h_arbo_moy = t2.h_arbo_moy FROM (SELECT t4.fid, AVG(t5.mnh) AS h_arbo_moy
                                                            FROM tab_interm_rgptarbu_toucharboetherbo AS t4,
                                                                (SELECT fid, geom, mnh FROM %s WHERE strate = 'A') AS t5
                                                                WHERE public.ST_INTERSECTS(t4.geom, t5.geom)
                                                                GROUP BY t4.fid) AS t2
                                                        WHERE t1.fid_rgpt = t2.fid;
    """ %(tab_ref)

    query += """
    UPDATE h_moys AS t1 SET h_herbo_moy = t2.h_herbo_moy FROM (SELECT t4.fid, AVG(t5.mnh) AS h_herbo_moy
                                                            FROM tab_interm_rgptarbu_toucharboetherbo AS t4,
                                                                (SELECT fid, geom, mnh FROM %s WHERE strate = 'H') AS t5
                                                            WHERE public.ST_INTERSECTS(t4.geom, t5.geom)
                                                            GROUP BY t4.fid) AS t2
                                                        WHERE t1.fid_rgpt = t2.fid;
    """ %(tab_ref)

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

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
    CREATE TABLE herbace AS
        SELECT public.ST_CHAIKINSMOOTHING((public.ST_DUMP(public.ST_MULTI(public.ST_UNION(t1.geom)))).geom) AS geom
        FROM (SELECT geom FROM %s WHERE strate='H') AS t1;
    """ %(tab_ref)

    query += """
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
   # 1# Trois grands types de segments arbustifs appartennant à des regroupements :
   ###
     # - regroupements intersectant que des arbres --> traitement itératif
     # - regroupements intersectant que de l'herbe --> non traités
     # - regroupements intersectant de l'herbe et des arbres --> pré-traitement puis traitement itératif

    # Création d'une table intermédiaire contenant les rgpt_arbustifs qui intersectent des segments arborés
    query = """
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

    topologyCorrections(connexion, 'tab_interm_rgptarbu_toucharboetherbo', geometry_column='geom')
    topologyCorrections(connexion, 'herbace', geometry_column='geom')
    topologyCorrections(connexion, 'arbore', geometry_column='geom')


    # Création d'une table intermédiaire qui contient les regroupements et la longueur de leur frontière en contact avec des arbres et de l'herbe
    query = """
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

    # Mise à jour du statut des segments arbustifs appartennant à un regroupement touchant peu d'arboré et bcp d'herbacé
    query = """
    UPDATE %s AS t1 SET strate = 'A'
            FROM (SELECT t1.fid AS fid_arbu, t2.fid AS fid_arbo, abs(t1.mnh - t2.mnh) AS diff_h
                    FROM (
                            SELECT t3.*
                            FROM %s AS t3, (SELECT t2.*
                                            FROM (SELECT *
                                                    FROM rgpt_herbarbotouch_longbound AS t
                                                    WHERE t.long_bound_inters_arbo * 100 / t.long_bound_arbu < %s AND t.long_bound_inters_herbe * 100 / t.long_bound_arbu >= %s
                                                ) AS t1,
                                                  arbu_de_rgpt AS t2, arbore AS t3
                                            WHERE t2.fid_rgpt = t1.fid AND public.ST_INTERSECTS(t2.geom, t3.geom)) AS t4
                            WHERE t3.fid = t4.fid) AS t1,
                        (SELECT * FROM %s WHERE strate = 'A') AS t2
                    WHERE public.ST_INTERSECTS(t1.geom, t2.geom)) AS t2
            WHERE t1.fid = t2.fid_arbu AND t2.diff_h <= %s;
    """ %(tab_ref, tab_ref, dic_seuil["shrub_touch_treevsgrass_perc"], dic_seuil["shrub_touch_grassvstree_perc"], tab_ref, dic_seuil["height_max_difference"])

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

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

    #  Création de la table contant les segments arbustifs appartennant à des regroupements en contact avec des segments herbacés ET des segments arborés
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
    query = """
    CREATE  TABLE sgt_rgpt_bordure AS
        SELECT t3.*
        FROM (
            SELECT arbuste.fid AS id_arbu, sgt_touch.fid AS id_sgt_t, sgt_touch.strate AS strate_touch, abs(arbuste.mnh-sgt_touch.mnh) AS diff_h
            FROM (
                SELECT t1.*
                FROM %s AS t1, sgt_rgpt_arbu_to_treat AS t2
                WHERE t1.fid = t2.fid
                )
                AS arbuste, (
                        SELECT *
                        FROM %s
                        WHERE strate in ('A', 'H')
                        )
                        AS sgt_touch
            WHERE public.ST_INTERSECTS(arbuste.geom, sgt_touch.geom)
            )
            AS t3
        INNER JOIN
        (SELECT t4.id_arbu AS id_arbu, min(t4.diff_h) AS min_diff_h
        FROM (
            SELECT arbuste.fid AS id_arbu, sgt_touch.fid AS id_sgt_t, sgt_touch.strate AS strate_touch, abs(arbuste.mnh - sgt_touch.mnh) AS diff_h
            FROM (
                SELECT t1.*
                FROM %s AS t1, sgt_rgpt_arbu_to_treat AS t2
                WHERE t1.fid = t2.fid
                )
                AS arbuste,
                (
                SELECT *
                FROM %s
                WHERE strate in ('A', 'H')
                )
                AS sgt_touch
            WHERE public.ST_INTERSECTS(arbuste.geom, sgt_touch.geom)
            )
            AS t4
        GROUP BY id_arbu)
        AS t5
        ON t3.id_arbu = t5.id_arbu AND t3.diff_h = t5.min_diff_h;
    """ %(tab_ref, tab_ref, tab_ref, tab_ref)


    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

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
        query = """
        CREATE  TABLE sgt_rgpt_bordure AS
            SELECT t3.*
            FROM (
                SELECT arbuste.fid as id_arbu, sgt_touch.fid as id_sgt_t, sgt_touch.strate as strate_touch, abs(arbuste.mnh - sgt_touch.mnh) as diff_h
                FROM (
                    SELECT t1.*
                    FROM %s AS t1, sgt_rgpt_arbu_to_treat as t2
                    WHERE t1.fid = t2.fid
                    )
                    as arbuste, (
                            SELECT *
                            FROM %s
                            WHERE strate in ('A', 'H')
                            )
                            AS sgt_touch
                WHERE public.ST_INTERSECTS(arbuste.geom, sgt_touch.geom)
                )
                AS t3
            INNER JOIN
            (SELECT t4.id_arbu as id_arbu, min(t4.diff_h) as min_diff_h
            FROM (
                SELECT arbuste.fid as id_arbu, sgt_touch.fid as id_sgt_t, sgt_touch.strate as strate_touch, abs(arbuste.mnh - sgt_touch.mnh) as diff_h
                FROM (
                    SELECT t1.*
                    FROM %s AS t1, sgt_rgpt_arbu_to_treat AS t2
                    WHERE t1.fid = t2.fid
                    )
                    AS arbuste,
                    (
                    SELECT *
                    FROM %s
                    WHERE strate in ('A', 'H')
                    )
                    AS sgt_touch
                WHERE public.ST_INTERSECTS(arbuste.geom, sgt_touch.geom)
                )
                as t4
            GROUP BY id_arbu)
            AS t5
            ON t3.id_arbu = t5.id_arbu AND t3.diff_h = t5.min_diff_h;
        """ %(tab_ref, tab_ref, tab_ref, tab_ref)

        # Exécution de la requête SQL
        if debug >= 3:
            print(query)
        executeQuery(connexion, query)


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
