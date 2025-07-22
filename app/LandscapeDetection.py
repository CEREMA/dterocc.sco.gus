#!/usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.               #
#############################################################################

# Import des librairie Python
import math,os

# Import des librairies de /libs
from Lib_postgis import addIndex, addSpatialIndex, addUniqId, addColumn, dropTable, dropColumn,executeQuery, exportVectorByOgr2ogr, importVectorByOgr2ogr, closeConnection, topologyCorrections
from Lib_display import endC, bold, yellow, cyan, red
from CrossingVectorRaster import statisticsVectorRaster
from Lib_file import removeFile, removeVectorFile
from Lib_raster import rasterizeVector, polygonizeRaster
from Lib_vector import cutoutVectors

###########################################################################################################################################
# FONCTION landscapeDetection()                                                                                                           #
###########################################################################################################################################
def landscapeDetection(connexion, connexion_dic ,dic_params, repertory, save_intermediate_result = False,debug = 0):
    """
    Rôle :

    Paramètres :
        connexion : correspond à la variable de connexion à la base de données
        connexion_dic : ictionnaire des paramètres de connexion selon le modèle : {"dbname" : '', "user_db" : '', "password_db" : '', "server_db" : '', "port_number" : '', "schema" : ''}
        dic_params : dictionnaire des paramètres pour calculer les attributs descriptifs des formes végétales
        repertory : repertoire pour sauvegarder les fichiers temporaires produits
        save_intermediate_result : paramètre de sauvegarde des fichiers intermédiaires. Par défaut : False
        debug : niveau de debug pour l'affichage des commentaires. Par défaut : 0
    """
    result = False
    if dic_params["ldsc_information"]["lcz_information"]["lcz_data"] != "":
        ldsc_data = landscapeDetectionLCZEdition(connexion, connexion_dic, dic_params, repertory, save_intermediate_result, debug = debug)
        dic_params["ldsc_information"]["img_landscape"]  = ldsc_data
        result = True

    elif dic_params["ldsc_information"]["img_ocs"] == "" or os.path.exists(dic_params["ldsc_information"]["img_ocs"]):
       # Attention, pour l'instant cette fonction n'est pas opérationnelle, elle sera modifiée et opérationnelle plus tard --> renvoie uniquement un message
       print(bold + yellow + "La fonction landscapeDetectionSateeliteEdition() n'est pas encore opérationnelle. La couche paysage ne peut pas encore être produite à partir de données satellitaires." + endC)
        # ldsc_data = landscapeDetectionSatelliteEdition(connexion, connexion_dic, dic_params, repertory, save_intermediate_result, debug = debug)
        # dic_params["img_landscape"] = ldsc_data
        # result = True

    else :
        print(bold + red + "Il n'y a AUCUNE donnée exploitable pour créer une couche paysage." + endC)

    return result, dic_params

###########################################################################################################################################
# FONCTION landscapeDetectionLCZEdition()                                                                                                 #
###########################################################################################################################################
def landscapeDetectionLCZEdition(connexion, connexion_dic, dic_params, repertory, save_intermediate_result = False, debug = 0):
    """
    Rôle : création d'une couche vecteur et raster "paysage" à partir des données LCZ

    Paramètres :
        connexion : correspond à la variable de connexion à la base de données
        connexion_dic : dictionnaire des paramètres de connexion selon le modèle : {"dbname" : '', "user_db" : '', "password_db" : '', "server_db" : '', "port_number" : '', "schema" : ''}
        dic_params : dictionnaire des paramètres pour calculer les attributs descriptifs des formes végétales
        repertory : repertoire pour sauvegarder les fichiers temporaires produits
        save_intermediate_result : paramètre de sauvegarde des fichiers intermédiaires. Par défaut : False
        debug : niveau de debug pour l'affichage des commentaires. Par défaut : 0
    """

    # Préparation des noms de fichiers intermédiaires
    lcz_data = dic_params["ldsc_information"]["lcz_information"]["lcz_data"]
    extension = os.path.splitext(lcz_data)[1]
    lcz_cut = repertory + os.sep + "lcz_cut_etude" + extension
    if extension == '.shp':
        format_vector = 'ESRI Shapefile'
    else:
        format_vector = 'GPKG'

    # 1# Découper la couche vecteur LCZ selon l'emprise de la zone d'étude
    cutoutVectors(dic_params["shp_zone"] , [lcz_data], [lcz_cut] , overwrite=True, format_vector=format_vector)

    # 2# Import du fichier vecteur LCZ en base
    tab_lcz = 'tab_lcz'
    importVectorByOgr2ogr(connexion_dic["dbname"], lcz_cut, tab_lcz, user_name=connexion_dic["user_db"], password=connexion_dic["password_db"], ip_host=connexion_dic["server_db"], num_port=connexion_dic["port_number"],schema_name=connexion_dic["schema"], epsg=str(2154))

    # 3# Création de la table paysage
    tab_pay = "paysages_lev1"

    query = """
    DROP TABLE IF EXISTS %s;
    CREATE TABLE %s AS
    """  %(tab_pay, tab_pay)

    # 3.1# Regroupement de tous les LCZ appartennant au milieu urbanisé
    if len(dic_params["ldsc_information"]["lcz_information"]["1"]) > 1:
        query += """
        SELECT public.ST_UNION(geom) AS geom, 1 AS dn
        FROM %s
        WHERE %s in %s
        """ %(tab_lcz, dic_params["ldsc_information"]["lcz_information"]["field"], tuple(dic_params["ldsc_information"]["lcz_information"]["1"]))
    else :
        query += """
        SELECT public.ST_UNION(geom) AS geom, 1 AS dn
        FROM %s
        WHERE %s = '%s'
        """ %(tab_lcz, dic_params["ldsc_information"]["lcz_information"]["field"], dic_params["ldsc_information"]["lcz_information"]["1"][0])


    # 3.2# Regroupement de tous les LCZ appartennant aux voiries et infrastructures
    if len(dic_params["ldsc_information"]["lcz_information"]["2"]) > 1:
        query += """
        UNION
        SELECT public.ST_UNION(geom) AS geom, 2 AS dn
        FROM %s
        WHERE %s in %s
        """ %(tab_lcz, dic_params["ldsc_information"]["lcz_information"]["field"], tuple(dic_params["ldsc_information"]["lcz_information"]["2"]))
    else :
        query += """
        UNION
        SELECT public.ST_UNION(geom) AS geom, 2 AS dn
        FROM %s
        WHERE %s = '%s'
        """ %(tab_lcz, dic_params["ldsc_information"]["lcz_information"]["field"], dic_params["ldsc_information"]["lcz_information"]["2"][0])

    # 3.3# Regroupement de tous les LCZ appartennant aux étendues et cours d'eau
    if len(dic_params["ldsc_information"]["lcz_information"]["3"]) > 1:
        query += """
        UNION
        SELECT public.ST_UNION(geom) AS geom, 3 AS dn
        FROM %s
        WHERE %s in %s
        """ %(tab_lcz, dic_params["ldsc_information"]["lcz_information"]["field"], tuple(dic_params["ldsc_information"]["lcz_information"]["3"]))
    else :
        query += """
        UNION
        SELECT public.ST_UNION(geom) AS geom, 3 AS dn
        FROM %s
        WHERE %s = '%s'
        """ %(tab_lcz, dic_params["ldsc_information"]["lcz_information"]["field"], dic_params["ldsc_information"]["lcz_information"]["3"][0])

    # 3.4# Regroupement de tous les LCZ appartennant aux milieux agricoles et forestiers
    if len(dic_params["ldsc_information"]["lcz_information"]["4"]) > 1:
        query += """
        UNION
        SELECT public.ST_UNION(geom) AS geom, 4 AS dn
        FROM %s
        WHERE %s in %s
        """ %(tab_lcz, dic_params["ldsc_information"]["lcz_information"]["field"], tuple(dic_params["ldsc_information"]["lcz_information"]["4"]))
    else :
        query += """
        UNION
        SELECT public.ST_UNION(geom) AS geom, 4 AS dn
        FROM %s
        WHERE %s = '%s'
        """ %(tab_lcz, dic_params["ldsc_information"]["lcz_information"]["field"], dic_params["ldsc_information"]["lcz_information"]["4"][0])

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    buffer_route = 5
    buffer_eau = 5

    tab_route = "lcz_road"
    tab_eau = "lcz_water"
    tab_int = "lcz_inter"
    tab_buff = "paysage_lcz_buffer"

    query = """
    DROP TABLE IF EXISTS %s ;
    CREATE TABLE %s AS
        SELECT public.ST_BUFFER(geom, %s) AS geom, dn
        FROM %s WHERE dn = 2 ;
    """ %(tab_route, tab_route, buffer_route, tab_pay)

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    addSpatialIndex(connexion, tab_route)

    query = """
    DROP TABLE IF EXISTS %s ;
    CREATE TABLE %s AS
        SELECT public.ST_BUFFER(geom, %s) AS geom, dn
        FROM %s WHERE dn = 3 ;
    """ %(tab_eau, tab_eau, buffer_eau, tab_pay)

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    addSpatialIndex(connexion, tab_route)

    query = """
    DROP TABLE IF EXISTS %s ;
    CREATE TABLE %s AS
        SELECT public.ST_Difference(lcz.geom, route.geom) as geom, lcz.dn FROM %s AS route, %s AS lcz WHERE lcz.dn = 1 OR lcz.dn = 4
        UNION
        SELECT geom, dn FROM %s ;
    """ %(tab_int, tab_int, tab_route, tab_pay, tab_route)

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    addSpatialIndex(connexion, tab_int)


    query = """
    DROP TABLE IF EXISTS %s ;
    CREATE TABLE %s AS
        SELECT public.ST_Difference(int.geom, eau.geom) as geom, int.dn FROM %s AS eau, %s AS int
        UNION
        SELECT geom, dn FROM %s ;
    """ %(tab_buff, tab_buff, tab_eau, tab_int, tab_eau)

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)



    query = "UPDATE %s SET %s = public.ST_CollectionExtract(public.ST_ForceCollection(public.ST_MakeValid(%s)),3) WHERE NOT public.ST_IsValid(%s);" % (tab_buff, 'geom', 'geom', 'geom')
    #query = "UPDATE %s SET %s = public.ST_CollectionExtract(public.ST_ForceCollection(public.ST_MakeValid(%s)),3) WHERE NOT public.ST_IsValid(%s);" % (tab_int, 'geom', 'geom', 'geom')
    executeQuery(connexion, query)

    # Création du chemin d'accès pour la sauvegarde de la couche paysage
    landscape_gpkg_file_buff = repertory + os.sep + 'paysages_buff.gpkg'
    landscape_gpkg_file = repertory + os.sep + 'paysages.gpkg'
    landscape_tif_file = repertory + os.sep + 'paysages.tif'

    # 6# Export du résultat au format GPKG
    #exportVectorByOgr2ogr(connexion_dic["dbname"], landscape_gpkg_file_buff, tab_int, user_name = connexion_dic["user_db"], password = connexion_dic["password_db"], ip_host = connexion_dic["server_db"], num_port = connexion_dic["port_number"], schema_name = connexion_dic["schema"], format_type='GPKG')

    exportVectorByOgr2ogr(connexion_dic["dbname"], landscape_gpkg_file_buff, tab_buff, user_name = connexion_dic["user_db"], password = connexion_dic["password_db"], ip_host = connexion_dic["server_db"], num_port = connexion_dic["port_number"], schema_name = connexion_dic["schema"], format_type='GPKG')

    # Préparation des noms de fichiers intermédiaires

    # 1# Découper la couche vecteur LCZ selon l'emprise de la zone d'étude
    command = "ogr2ogr -clipsrc %s %s %s  -nlt POLYGONE -overwrite -f GPKG" %(dic_params["shp_zone"], landscape_gpkg_file, landscape_gpkg_file_buff)
    if debug >=2:
        print(command)
    exit_code = os.system(command)
    if exit_code != 0:
        print(cyan + "Découpage des paysages sur la zone de travail : " + bold + red + "!!! Une erreur c'est produite au cours du découpage du vecteur : " + landscape_gpkg_file_buff + endC, file=sys.stderr)
    if debug >=2:
        print(cyan + "Découpage des paysages sur la zone de travail : " + endC + "Le fichier vecteur " + landscape_gpkg_file_buff + " a ete decoupe resultat : " + landscape_gpkg_file + " type geom = POLYGONE")


    # 7# Conversion au format raster
    rasterizeVector(landscape_gpkg_file, landscape_tif_file, dic_params["img_ref"], 'dn', codage="uint8", ram_otb=10000)

    # Suppression des fichiers et tables inutiles
    if not save_intermediate_result :
        dropTable(connexion, tab_lcz)
        dropTable(connexion, tab_pay)
        dropTable(connexion, tab_route)
        dropTable(connexion, tab_eau)
        dropTable(connexion, tab_int)
        dropTable(connexion, tab_buff)
        removeFile(landscape_gpkg_file_buff)

    return landscape_tif_file

###########################################################################################################################################
# FONCTION landscapeDetectionSatelliteEdition()                                                                                                 #
###########################################################################################################################################
def landscapeDetectionSatelliteEdition(connexion, connexion_dic, dic_params, repertory, num_class = {"bati" : 1, "route" : 2, "solnu" : 3, "eau" : 4, "vegetation" : 5}, save_intermediate_result = False, debug = 0):
    """
    Rôle : création d'une couche vecteur et raster "paysage" à partir des données satellitaires

    Paramètres :
        connexion : correspond à la variable de connexion à la base de données
        connexion_dic : ictionnaire des paramètres de connexion selon le modèle : {"dbname" : '', "user_db" : '', "password_db" : '', "server_db" : '', "port_number" : '', "schema" : ''}
        dic_params : dictionnaire des paramètres pour calculer les attributs descriptifs des formes végétales
        repertory : repertoire pour sauvegarder les fichiers temporaires produits
        num_class : dictionnaire des codes associés aux classes de l'ocs. Par défaut : {"bati" : 1, "route" : 2, "solnu" : 3, "eau" : 4, "vegetation" : 5}
        save_intermediate_result : paramètre de sauvegarde des fichiers intermédiaires. Par féfaut : False
        debug : niveau de debug pour l'affichage des commentaires. Par défaut : 0

    """
    # Paramètres initiaux
    #   expansion = dilatation de x mètres
    #   erosion = erosion de x mètres
    #   surf_min = surface minimale des polygones à traiter
    build_expansion = 40
    build_erosion = -25
    road_expansion = 4
    water_expansion = 4
    build_surf_min = 25
    road_surf_min = 100
    water_surf_min = 100

    # Création du chemin d'accès pour la sauvegarde de la couche paysage
    landscape_gpkg_file = repertory + os.sep + 'paysages.gpkg'
    landscape_tif_file = repertory + os.sep + 'paysages.tif'

    # Création du dossier temporaire où on stocke les fichiers intermédiaires
    repertory_tmp = repertory + os.sep + 'LANDSCAPE_TMP'
    if not os.path.exists(repertory_tmp):
        os.makedirs(repertory_tmp)
    # Decoupe sur la zone étude l'image OCS
    filename = os.path.splitext(os.path.basename(dic_params["ldsc_information"]["img_ocs"]))[0]
    img_ocs_cut = repertory_tmp + os.sep + filename + '_cut.tif'

    # command_cut = "gdalwarp -cutline %s -crop_to_cutline %s %s" %(dic_params["shp_zone"] , dic_params["ldsc_information"]["img_ocs"], img_ocs_cut)
    # exitcode = os.system(command_cut)
    # if exitcode == 0:
    #     print("message d'erreur")


    # Extraction des 3 masques bâti, route et eau de l'ocs
    img_mask_bati = repertory_tmp + os.sep + 'mask_bati.tif'
    img_mask_route = repertory_tmp + os.sep + 'mask_route.tif'
    img_mask_eau = repertory_tmp + os.sep + 'mask_eau.tif'

    command_maskbati = "otbcli_BandMath -il %s -out %s -exp '(im1b1==%s)?1:0'" %(img_ocs_cut, img_mask_bati, dic_params["ldsc_information"]["ocs_classes"]["build"])
    exitcode = os.system(command_maskbati)
    if exitcode == 0:
        print("message")

    command_maskroute = "otbcli_BandMath -il %s -out %s -exp '(im1b1==%s)?1:0'" %(img_ocs_cut, img_mask_route, dic_params["ldsc_information"]["ocs_classes"]["road"])
    exitcode = os.system(command_maskroute)
    if exitcode == 0:
        print("message")

    command_maskeau = "otbcli_BandMath -il %s -out %s -exp '(im1b1==%s)?1:0'" %(img_ocs_cut, img_mask_eau, dic_params["ldsc_information"]["ocs_classes"]["water"])
    exitcode = os.system(command_maskeau)
    if exitcode == 0:
        print("message")

    # Conversion des trois images masques en vecteur
    vect_mask_bati = repertory_tmp + os.sep + 'mask_bati.shp'
    vect_mask_route = repertory_tmp + os.sep + 'mask_route.shp'
    vect_mask_eau = repertory_tmp + os.sep + 'mask_eau.shp'

    polygonizeRaster(img_mask_bati, vect_mask_bati, 'mask_bati', field_name="id", vector_export_format="ESRI Shapefile")
    polygonizeRaster(img_mask_route, vect_mask_route, 'mask_route', field_name="id", vector_export_format="ESRI Shapefile")
    polygonizeRaster(img_mask_eau, vect_mask_eau, 'mask_eau', field_name="id", vector_export_format="ESRI Shapefile")

    # Import en base des trois données vecteurs sous la forme de trois tables
    tab_bati = 'tab_bati'
    tab_route = 'tab_route'
    tab_eau = 'tab_eau'
    importVectorByOgr2ogr(connexion_dic["dbname"], vect_mask_bati, tab_bati, user_name=connexion_dic["user_db"], password=connexion_dic["password_db"], ip_host=connexion_dic["server_db"], num_port=connexion_dic["port_number"],schema_name=connexion_dic["schema"], epsg=str(2154))
    importVectorByOgr2ogr(connexion_dic["dbname"], vect_mask_route, tab_route, user_name=connexion_dic["user_db"], password=connexion_dic["password_db"], ip_host=connexion_dic["server_db"], num_port=connexion_dic["port_number"],schema_name=connexion_dic["schema"], epsg=str(2154))
    importVectorByOgr2ogr(connexion_dic["dbname"], vect_mask_eau, tab_eau, user_name=connexion_dic["user_db"], password=connexion_dic["password_db"], ip_host=connexion_dic["server_db"], num_port=connexion_dic["port_number"],schema_name=connexion_dic["schema"], epsg=str(2154))

    # Suppression des polygones "non bati", "non route" et "non eau"
    #query = """
    #    DELETE FROM %s WHERE id = 0;
    #    DELETE FROM %s WHERE id = 0;
    #    DELETE FROM %s WHERE id = 0;
    #""" %(tab_bati, tab_route, tab_eau)

    #if debug >= 3:
    #    print(query)
    #executeQuery(connexion, query)

    # Ajout des index
    addSpatialIndex(connexion, tab_bati)
    addSpatialIndex(connexion, tab_route)
    addSpatialIndex(connexion, tab_eau)

    # Correction tologiques
    topologyCorrections(connexion, tab_eau)
    topologyCorrections(connexion, tab_route)
    topologyCorrections(connexion, tab_bati)

    ## Travaux sur la couche "eau"##

    query = """
    DROP TABLE IF EXISTS tab_etendueetcoursdeau;
    CREATE TABLE tab_etendueetcoursdeau AS
        SELECT public.ST_UNION(public.ST_BUFFER(geom, %s)) AS geom, 3 AS dn
        FROM %s
        WHERE public.ST_AREA(geom) > %s;
    """ %(water_expansion, tab_eau, water_surf_min)

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Ajout des index
    addSpatialIndex(connexion, 'tab_etendueetcoursdeau')

    ## Travaux sur la couche "route" ##
    query = """
    DROP TABLE IF EXISTS tab_voirieetinfrastructure;
    CREATE TABLE tab_voirieetinfrastructure AS
        SELECT public.ST_UNION(public.ST_DIFFERENCE(route.geom, eau.geom)) AS geom, 2 AS dn
        FROM (SELECT public.ST_BUFFER(geom, %s) AS geom
                FROM %s
                WHERE public.ST_AREA(geom) > %s) AS route, %s AS eau
        WHERE public.ST_INTERSECTS(route.geom, eau.geom);
    """ %(road_expansion, tab_route, road_surf_min, 'tab_etendueetcoursdeau')

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Ajout des index
    addSpatialIndex(connexion, 'tab_voirieetinfrastructure')

    ## Travaux sur la couche "bati" ##

    # Sélection avec filtre
    query = """
    DROP TABLE IF EXISTS tab_milieuurbanise;
    CREATE TABLE tab_milieuurbanise AS
        SELECT public.ST_UNION(public.ST_DIFFERENCE(bati_moins_eau.geom, route.geom)) AS geom, 1 AS dn
            FROM (SELECT public.ST_UNION(public.ST_DIFFERENCE(bati.geom, eau.geom)) AS geom
                    FROM (SELECT public.ST_BUFFER(public.ST_BUFFER(geom, %s), %s) AS geom
                            FROM %s
                            WHERE public.ST_AREA(geom) > %s) AS bati, %s AS eau
                    WHERE public.ST_INTERSECTS(bati.geom, eau.geom)) AS bati_moins_eau, %s AS route
            WHERE public.ST_INTERSECTS(bati_moins_eau.geom, route.geom);
    """ %(build_expansion, build_erosion, tab_bati, build_surf_min, 'tab_etendueetcoursdeau', 'tab_voirieetinfrastructure')

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Ajout des index
    addSpatialIndex(connexion, 'tab_milieuurbanise')

    ## Travaux sur le milieu agricole et forestier ##
    query = """
    DROP TABLE IF EXISTS tab_milieuagrifor;
    CREATE TABLE tab_milieuagrifor AS
        SELECT public.ST_UNION(public.ST_DIFFERENCE(shp.geom, other.geom)) AS geom, 4 AS dn
        FROM (
            SELECT geom, dn
            FROM tab_milieuurbanise
            UNION
            SELECT geom, dn
            FROM tab_voirieetinfrastructure
            UNION
            SELECT geom, dn
            FROM tab_etendueetcoursdeau
            ) AS other, %s AS shp;
    """  %(tab_shp)

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Ajout des index
    addSpatialIndex(connexion, 'tab_milieuagrifor')

    # Avant de faire la suite, vérifier qu'il n'y a pas de superposition des couches
    query = """
    DROP TABLE IF EXISTS paysage_level1;
    CREATE TABLE paysage_level1 AS
        SELECT geom, dn
        FROM tab_milieuurbanise
        UNION
        SELECT geom, dn
        FROM tab_voirieetinfrastructure
        UNION
        SELECT geom, dn
        FROM tab_etendueetcoursdeau
        UNION
        SELECT geom, dn
        FROM tab_milieuagrifor;
    """

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Export de la donnée au format vecteur et raster
    exportVectorByOgr2ogr(connexion_dic["dbname"], landscape_gpkg_file, 'paysage_level1', user_name = connexion_dic["user_db"], password = connexion_dic["password_db"], ip_host = connexion_dic["server_db"], num_port = connexion_dic["port_number"], schema_name = connexion_dic["schema"], format_type='GPKG')

    # Export au format raster
    # Creation du chemin de sauvegarde de la donnée raster
    rasterizeVector(landscape_gpkg_file, landscape_tif_file, dic_params["ldsc_information"]["img_ocs"], 'dn', codage="uint8", ram_otb=10000)

    # Suppression des tables inutiles
    if not save_intermediate_result:
        removeFile(img_ocs_cut)
        removeFile(img_mask_bati)
        removeFile(img_mask_route)
        removeFile(img_mask_eau)
        removeFile(vect_mask_bati)
        removeFile(vect_mask_route)
        removeFile(vect_mask_eau)
        dropTable(connexion, tab_bati)
        dropTable(connexion, tab_eau)
        dropTable(connexion, tab_route)
        dropTable(connexion, 'tab_etendueetcoursdeau')
        dropTable(connexion, 'tab_milieuurbanise')
        dropTable(connexion, 'tab_voirieetinfrastructure')
        dropTable(connexion, 'tab_milieuagrifor')
        dropTable(connexion, 'paysage_level1')

    return landscape_tif_file


###########################################################################################################################################
# FONCTION urbanLandscapeDetection()                                                                                                           #
###########################################################################################################################################
def urbanLandscapeDetection(connexion, connexion_dic ,dic_params, repertory, save_intermediate_result = False,debug = 0):
    """
    Rôle :

    Paramètres :
        connexion : correspond à la variable de connexion à la base de données
        connexion_dic : ictionnaire des paramètres de connexion selon le modèle : {"dbname" : '', "user_db" : '', "password_db" : '', "server_db" : '', "port_number" : '', "schema" : ''}
        dic_params : dictionnaire des paramètres pour calculer les attributs descriptifs des formes végétales
        repertory : repertoire pour sauvegarder les fichiers temporaires produits
        save_intermediate_result : paramètre de sauvegarde des fichiers intermédiaires. Par défaut : False
        debug : niveau de debug pour l'affichage des commentaires. Par défaut : 0
    """

    if dic_params["ldsc_information"]["lcz_information"]["lcz_data"] != "":

        lcz_data = dic_params["ldsc_information"]["lcz_information"]["lcz_data"]
        extension = os.path.splitext(lcz_data)[1]
        lcz_cut = repertory + os.sep + "lcz_cut_etude" + extension
        if extension == '.shp':
            format_vector = 'ESRI Shapefile'
        else:
            format_vector = 'GPKG'

        # 1# Découper la couche vecteur LCZ selon l'emprise de la zone d'étude
        if not os.path.exists(dic_params["ldsc_information"]["img_ocs"]):
            cutoutVectors(dic_params["shp_zone"] , [lcz_data], [lcz_cut] , overwrite=True, format_vector=format_vector)

        # 2# Import du fichier vecteur LCZ en base
        tab_lcz = 'tab_lcz'
        importVectorByOgr2ogr(connexion_dic["dbname"], lcz_cut, tab_lcz, user_name=connexion_dic["user_db"], password=connexion_dic["password_db"], ip_host=connexion_dic["server_db"], num_port=connexion_dic["port_number"],schema_name=connexion_dic["schema"], epsg=str(2154))

        # 3# Création de la table paysage
        tab_urbain = "paysages_urbain"

        query = """
        DROP TABLE IF EXISTS %s;
        CREATE TABLE %s AS
        """  %(tab_urbain, tab_urbain)

        # Regroupement de tous les LCZ appartennant au milieu urbanisé
        if len(dic_params["ldsc_information"]["lcz_information"]["1"]) > 1:
            query += """
            SELECT geom, 1 AS dn
            FROM %s
            WHERE %s in %s
            """ %(tab_lcz, dic_params["ldsc_information"]["lcz_information"]["field"], tuple(dic_params["ldsc_information"]["lcz_information"]["1"]))
        else :
            query += """
            SELECT geom, 1 AS dn
            FROM %s
            WHERE %s = '%s'
            """ %(tab_lcz, dic_params["ldsc_information"]["lcz_information"]["field"], dic_params["ldsc_information"]["lcz_information"]["1"][0])

        if debug >= 3:
            print(query)
        executeQuery(connexion, query)

        boundaryLandscapeDetection(connexion, tab_lcz, debug)

        # Création du chemin d'accès pour la sauvegarde de la couche paysage
        urban_gpkg_file = repertory + os.sep + 'paysages_urbains.gpkg'

        # 6# Export du résultat au format GPKG
        exportVectorByOgr2ogr(connexion_dic["dbname"], urban_gpkg_file, tab_urbain, user_name = connexion_dic["user_db"], password = connexion_dic["password_db"], ip_host = connexion_dic["server_db"], num_port = connexion_dic["port_number"], schema_name = connexion_dic["schema"], format_type='GPKG')

        dic_params["ldsc_information"]["lcz_urbain"]  = urban_gpkg_file

        if not save_intermediate_result :
            #removeFile(lcz_cut)
            dropTable(connexion, tab_lcz)
            dropTable(connexion, tab_urbain)

    else :
        print(bold + red + "Le fichier LCZ n'a pas été fourni. Il n'est pas possible de créé la couche des paysages urbains." + endC)



    return dic_params


###########################################################################################################################################
# FONCTION boundaryLandscapeDetection()                                                                                                           #
###########################################################################################################################################
def boundaryLandscapeDetection(connexion, tab_lcz,debug = 0):

    """
    Rôle :

    Paramètres :
        connexion : correspond à la variable de connexion à la base de données
        connexion_dic : ictionnaire des paramètres de connexion selon le modèle : {"dbname" : '', "user_db" : '', "password_db" : '', "server_db" : '', "port_number" : '', "schema" : ''}
        dic_params : dictionnaire des paramètres pour calculer les attributs descriptifs des formes végétales
        repertory : repertoire pour sauvegarder les fichiers temporaires produits
        save_intermediate_result : paramètre de sauvegarde des fichiers intermédiaires. Par défaut : False
        debug : niveau de debug pour l'affichage des commentaires. Par défaut : 0
    """


    # Récupération des contours urbains pour le découpage des différentes strates

    tab_cut = 'contours_lcz'

    query = """
    DROP TABLE IF EXISTS %s;
    CREATE TABLE %s AS
        SELECT public.ST_UNION(public.ST_Boundary(geom)) as geom
        FROM %s
    """ %(tab_cut, tab_cut, tab_lcz)

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    addSpatialIndex(connexion, tab_cut)



