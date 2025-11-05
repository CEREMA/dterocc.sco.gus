#!/usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.               #
#############################################################################

# Import des librairie Python
import math,os, sys
import geopandas as gpd

# Import des librairies de /libs
from Lib_postgis import topologyCorrections, addIndex, addSpatialIndex, addUniqId, addColumn, dropTable, dropColumn,executeQuery, exportVectorByOgr2ogr, importVectorByOgr2ogr, closeConnection, topologyCorrections, getAllColumns
from Lib_display import endC, bold, yellow, cyan, red
from Lib_file import removeFile, removeVectorFile, deleteDir
from Lib_raster import rasterizeVector, cutImageByVector
from Lib_vector import getEmpriseVector, differenceVector, cutVectorAll
from Lib_grass import initializeGrass, cleanGrass, simplificationGrass
from CrossingVectorRaster import statisticsVectorRaster
from PolygonsMerging import mergeSmallPolygons, findAdjacentPolygons

#################################################
## Concaténation des trois tables pour obtenir ##
## une unique cartographie                     ##
#################################################

def cartographyVegetation(connexion, connexion_dic, schem_tab_ref, empriseVector, dic_roads, dic_thresholds, raster_dic, output_layers, cleanfv = False, save_intermediate_result = False, overwrite = False, debug = 0):
    """
    Rôle : concatène les trois tables arboré, arbustive et herbacée en un unique
           correspondant à la carotgraphie de la végétation

    Paramètres :
        connexion : connexion à la base donnée et au schéma correspondant
        connexion_dic : dictionnaire des paramètre de connexion
        schem_tab_ref : schema et nom de la table de référence des segments végétation classés en strates verticales
        dic_thresholds : dictionnaire des seuils à attribuer en fonction de la strate verticale
        raster_dic : dictionnaire associant le type de donnée récupéré avec le fichier raster contenant les informations, par exemple : {"mnh" : filename}
        output_layers : dictionnaire des noms de fichier de sauvegarde
        cleanfv : paramètre de nettoyage des formes végétales. Par défaut : False
        save_intermediate_result : sauvegarde ou non des fichiers/tables intermédiaires. Par défaut : False
        overwrite : paramètre de ré-écriture des tables. Par défaut False
        debug : niveau de debug pour l'affichage des commentaires. Par défaut : 0

    Sortie :
        nom de la table contenant toutes les formes végétales
    """

    # Rappel du paramétrage
    if debug >= 2 :
        print(cyan + "cartographyVegetation() : Début de la classification en strates verticales végétales" + endC)
        print(cyan + "cartographyVegetation : " + endC + "connexion_dic : " + str(connexion_dic) + endC)
        print(cyan + "cartographyVegetation : " + endC + "schem_tab_ref : " + str(schem_tab_ref) + endC)
        print(cyan + "cartographyVegetation : " + endC + "dic_thresholds : " + str(dic_thresholds) + endC)
        print(cyan + "cartographyVegetation : " + endC + "raster_dic : " + str(raster_dic) + endC)
        print(cyan + "cartographyVegetation : " + endC + "output_layers : " + str(output_layers) + endC)
        print(cyan + "cartographyVegetation : " + endC + "save_intermediate_result: " + str(save_intermediate_result) + endC)
        print(cyan + "cartographyVegetation : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "cartographyVegetation : " + endC + "debug : " + str(debug) + endC)

    # Nettoyage en base si ré-écriture
    if overwrite and False: # Attention ce nettoyage est dangeureux on n a plus de donnée d'entrée apres!!! sans doute a supprimer cette étape.
        print(bold + "Choix de remise à zéro du schéma " + str(schem_tab_ref))
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

    # Préparation des routes

    repository = os.path.dirname(output_layers["output_fv"])
    clean_roads = repository + os.sep+ "clean_roads.shp"
    roads_vector = dic_roads["roads_file"]
    fields_roads = dic_roads["fields_to_sort_roads"]
    list_fields_roads = dic_roads["list_for_fields_to_sort_roads"]
    cleanRoads(roads_vector, clean_roads, fields_roads, list_fields_roads)
    roads_cut = repository + os.sep+ "roads_cut.shp"
    cutVectorAll(empriseVector, clean_roads, roads_cut)
    table_clean_roads = "roads_to_cut"
    importVectorByOgr2ogr(connexion_dic["dbname"], roads_cut, table_clean_roads, user_name=connexion_dic["user_db"], password=connexion_dic["password_db"], ip_host=connexion_dic["server_db"], num_port=connexion_dic["port_number"], schema_name=connexion_dic["schema"],  epsg=str(2154))
    addSpatialIndex(connexion, table_clean_roads)

    tab_roads_union = "roads_clean_union_for_cut"
    geom_field = "geom"


    query_roads = """
    DROP TABLE IF EXISTS %s ;
    CREATE TABLE %s AS
        SELECT public.ST_LineMerge(public.ST_Collect(l.%s)) as %s FROM %s AS l;
    """%(tab_roads_union, tab_roads_union, geom_field, geom_field, table_clean_roads)
    executeQuery(connexion, query_roads)

    addSpatialIndex(connexion, tab_roads_union)

    tab_roads = tab_roads_union


    # 1# Formes végétales arborées
    tab_arbore = ''
    if debug >= 2:
        print(bold + "Détection des formes végétales au sein de la strate arborée" + endC)
    tab_arbore = detectInTreeStratum(connexion, connexion_dic, schem_tab_ref, tab_roads, dic_thresholds["tree"], output_layers["tree"], save_intermediate_result = save_intermediate_result, debug = debug)
    # 2# Formes végétales arbustives
    tab_arbustive = ''
    if debug >= 2:
        print(bold + "Détection des formes végétales au sein de la strate arbustive" + endC)
    tab_arbustive = detectInShrubStratum(connexion, connexion_dic, schem_tab_ref, tab_roads, dic_thresholds["shrub"], output_layers["shrub"], save_intermediate_result = save_intermediate_result, debug = debug)
    # 3# Formes végétales herbacées
    tab_herbace = ''
    if debug >= 2:
        print(bold + "Détection des formes végétales au sein de la strate herbacée" + endC)
    tab_herbace = detectInHerbaceousStratum(connexion, connexion_dic, schem_tab_ref, empriseVector, tab_roads, dic_thresholds["herbaceous"], output_layers["herbaceous"], save_intermediate_result = save_intermediate_result, debug = debug)
    # 4# Concaténation des données en une seule table 'végétation'
    tab_name = 'vegetation'
    tab_name_clean = 'vegetation_to_clean'

    if tab_arbore == '':
        tab_arbore = 'strate_arboree'
    if tab_arbustive == '':
        tab_arbustive = 'strate_arbustive'
    if tab_herbace == '':
        tab_herbace = 'strate_herbace'
    if debug >= 2:
        print(bold + "Concaténation des données en une seule table " + tab_name + endC)

    query = """
    DROP TABLE IF EXISTS %s ;
    CREATE TABLE %s AS
    SELECT geom, strate, fv FROM %s
    UNION
    SELECT geom, strate, fv FROM %s
    UNION
    SELECT geom, strate, fv FROM %s;
    """ %(tab_name, tab_name, tab_arbore, tab_arbustive, tab_herbace)

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Ajout des clés primaires et index spatiaux
    addUniqId(connexion, tab_name)
    addSpatialIndex(connexion, tab_name)

    # 5# Nettoyage des formes végétales plus poussée ou non, en fonction du choix de l'opérateur (cleanfv)
    tab_name = formStratumCleaning(connexion, connexion_dic, tab_name, tab_name_clean, dic_thresholds, tab_roads, repository, cleanfv, save_intermediate_result, debug)


    # Ajout de la colonne pour la sauvegarde au format raster
    addColumn(connexion, tab_name, 'fv_r', 'int')

    query = """
    UPDATE %s SET fv_r = 11 WHERE fv = 'AI';
    UPDATE %s SET fv_r = 12 WHERE fv = 'AA';
    UPDATE %s SET fv_r = 13 WHERE fv = 'BOA';
    UPDATE %s SET fv_r = 21 WHERE fv = 'AuI';
    UPDATE %s SET fv_r = 22 WHERE fv = 'AAu';
    UPDATE %s SET fv_r = 23 WHERE fv = 'BOAu';
    UPDATE %s SET fv_r = 31 WHERE fv = 'PR';
    UPDATE %s SET fv_r = 32 WHERE fv = 'C';
    UPDATE %s SET fv_r = 33 WHERE fv = 'PE';
    """ %(tab_name, tab_name, tab_name, tab_name, tab_name, tab_name, tab_name, tab_name, tab_name)

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)
    start_smooth = 0

    if not save_intermediate_result :
        removeVectorFile(clean_roads)
        removeVectorFile(roads_cut)
        dropTable(connexion, table_clean_roads)
        dropTable(connexion, tab_roads_union)

    if output_layers["output_fv"] == '':
        print(yellow + bold + "Attention : Il n'y a pas de sauvegarde en couche vecteur du résultat de classification. Vous n'avez pas fournit de chemin de sauvegarde." + endC)
    else:
        # Export au format vecteur
        exportVectorByOgr2ogr(connexion_dic["dbname"], output_layers["output_fv"], tab_name, user_name = connexion_dic["user_db"], password = connexion_dic["password_db"], ip_host = connexion_dic["server_db"], num_port = connexion_dic["port_number"], schema_name = connexion_dic["schema"], format_type='GPKG')

        # Lissage de la donnée vecteur avant de rasteriser
        vector_input_grass = output_layers["output_fv"]
        vector_output_grass = os.path.splitext(vector_input_grass)[0] + "_lis" + os.path.splitext(vector_input_grass)[1]
        repository = os.path.dirname(vector_input_grass) + os.sep
        xmin,xmax,ymin,ymax =  getEmpriseVector(vector_input_grass, format_vector='GPKG')
        epsg = 2154
        pixel_size_x = 1
        pixel_size_y = 1
        initializeGrass(repository, xmin, xmax, ymin, ymax, pixel_size_x, pixel_size_y, projection=epsg)
        simplificationGrass(vector_input_grass, vector_output_grass, threshold=1.0, format_vector='GPKG', overwrite=overwrite)
        cleanGrass(repository)
        output_layers["output_fv"] = vector_output_grass

        # Export au format raster
        # Creation du chemin de sauvegarde de la donnée raster
        repertory_output = os.path.dirname(output_layers["output_fv"])
        filename =  os.path.splitext(os.path.basename(output_layers["output_fv"]))[0]
        raster_output = repertory_output + os.sep + filename  + '.tif'
        rasterizeVector(output_layers["output_fv"], raster_output,  output_layers["img_ref"], 'fv_r', codage="uint8", ram_otb=0)

        # suppression de la colonne non utile "strate_r"
        dropColumn(connexion, tab_name, 'strate_r')


    return tab_name

################################################
## Classification des FV de la strate arborée ##
################################################

###########################################################################################################################################
# FONCTION detectInTreeStratum()                                                                                                          #
###########################################################################################################################################
def detectInTreeStratum(connexion, connexion_dic, schem_tab_ref, table_roads, thresholds = 0, output_layer = '', save_intermediate_result = False, debug = 0):
    """
    Rôle : détecté les formes végétales horizontales au sein de la strate arborée

    Paramètres :
        connexion : connexion à la base donnée et au schéma correspondant
        connexion_dic : dictionnaire contenant les paramètres de connexion (pour la sauvegarde en fin de fonction)
        schem_tab_ref : schema.nom de la table correspondant aux segments de végétation
        thresholds : dictionnaire des seuils à appliquer, par défaut : {"seuil_surface" : 0, "seuil_compacite_1" : 0, "seuil_compacite_2" : 0, "seuil_convexite" : 0, "seuil_elongation" : 0, "val_largeur_max_alignement" : 0, "val_buffer" : 0}
        output_layer : sauvegarde du résultat final en une couche vectorielle, par défaut ''
        save_intermediate_result : sauvegarde ou non des tables intermédiaires. Par défaut : False
        debug : niveau de debug pour l'affichage des commentaires. Par défaut : 0

    Sortie :
        tab_arbore : nom de la table contenant les éléments de la strate arborée classés horizontalement
    """

    # 0# Attribution de valeurs par défaut pour les seuils si non renseignés
    if thresholds == 0:
        thresholds = {
            "isolatedtree_max_surface" : 100,
            "isolatedtree_min_surface" : 12,
            "woodtree_sure_surface" : 5000,
            "buffer_compacity_thr" : 0.5,
            "compacity_1_thr" : 0.7,
            "compacity_2_thr" : 0.2,
            "convexity_1_thr" : 0.65,
            "convexity_2_thr" : 0.5,
            "extension_1_thr" : 4,
            "extension_2_thr" : 2,
            "extension_3_thr" : 2.5
        }
    ###################################################
    ## Préparation de la couche arborée de référence ##
    ###################################################

    # 1# Récupération de la table composée uniquement des segments arborés
    tab_arb_ini = 'arbore_ini'

    query = """
    DROP TABLE IF EXISTS %s;
    CREATE TABLE %s AS
        SELECT *
        FROM %s
        WHERE strate = 'A';
    """ %(tab_arb_ini, tab_arb_ini, schem_tab_ref)

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Création des indexes
    addSpatialIndex(connexion, tab_arb_ini)
    addIndex(connexion, tab_arb_ini, 'fid', 'idx_fid_arboreini')

    # 2# Regroupement et lissage des segments arborés
    if debug >= 3:
        print(bold + "Regroupement et lissage des segments arborés" + endC)

    tab_arb_temp = 'arbore_temp'


    query = """
    DROP TABLE IF EXISTS %s;
    CREATE TABLE %s AS
        SELECT (public.ST_DUMP(public.ST_MULTI(public.ST_UNION(arbore_ini.geom)))).geom AS geom
        FROM %s;
    """ %(tab_arb_temp,tab_arb_temp, tab_arb_ini)

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)


    # Correction topologique
    query = "UPDATE %s SET %s = public.ST_CollectionExtract(public.ST_ForceCollection(public.ST_MakeValid(%s)),3) WHERE NOT public.ST_IsValid(%s);" % (tab_arb_temp, 'geom', 'geom', 'geom')
    executeQuery(connexion, query)

    # Création d'un index spatial
    addSpatialIndex(connexion, tab_arb_temp)

    tab_arb = "arbore"
    cutPolygonesByLines(connexion, tab_arb_temp, table_roads, tab_arb)

    # Création d'un identifiant unique
    addUniqId(connexion, tab_arb)

    # Création d'un index spatial
    addSpatialIndex(connexion, tab_arb)

    # Création de la colonne strate qui correspond à 'A' pour tous les polygones et complétion
    addColumn(connexion, tab_arb, 'strate', 'varchar(100)')

    query = """
    UPDATE %s SET strate = 'A' WHERE fid = fid;
    """ %(tab_arb)

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Création de la colonne fv
    addColumn(connexion, tab_arb, 'fv', 'varchar(100)')

    # Création et calcul de l'indicateur de forme : compacité
    createCompactnessIndicator(connexion, tab_arb, thresholds["buffer_compacity_thr"], debug = debug)

    # 3# Classement des segments en "arbre isole", "tache arboree" et "regroupement arbore"
    # basé sur un critère de surface et de seuil sur l'indice de compacité

    if debug >= 3:
        print(bold + "Classement des segments en 'AI' (arbre isole), 'TA'(tache arboree) et 'RGPTA'(regroupement arbore) basé sur un critère de surface et de seuil sur l'indice de compacité" + endC)

    fst_class = firstClassification(connexion, tab_arb,  thresholds, 'arbore', debug = debug)
    if 'fst_class'not in locals():
        fst_class = tab_arb

    # 4# Travaux sur les "regroupements arborés"
    if debug >= 3:
        print(bold + "Classement des segments en 'regroupements arborés'" + endC)

    sec_class = secClassification(connexion, tab_arb, 'rgpt_arbore', thresholds, save_intermediate_result, debug = debug)

    if 'sec_class' not in locals():
        sec_class = 'rgpt_arbore'
    # 5# Regroupement de l'ensemble des entités de la strate arborée en une seule couche
    if debug >= 3:
        print(bold + "Regroupement de l'ensemble des entités de la strate arborée en une seule couche" + endC)

    tab_arbore_tmp = 'strate_arboree_withlittlepolygons'
    tab_arbore_tmp = createLayerTree(connexion, tab_arbore_tmp, fst_class, sec_class, debug = debug)

    tab_arbore = 'strate_arboree'
    repository = os.path.dirname(output_layer) + os.sep
    smallPolygonsMerging(connexion, connexion_dic, tab_arbore_tmp, tab_arbore, repository, THRESHOLD_SMALL_AREA_POLY = 150, save_intermediate_result = save_intermediate_result, debug = debug)

    if tab_arbore == '':
        tab_arbore = 'strate_arboree'

    # SUPPRESSION DES TABLES QUI NE SONT PLUS UTILES ##
    if not save_intermediate_result :
        dropTable(connexion, tab_arb_ini)
        dropTable(connexion, fst_class)
        dropTable(connexion, sec_class)
        dropTable(connexion, tab_arbore_tmp)
        dropTable(connexion, tab_arb_temp)

    ## SAUVEGARDE DU RESULTAT EN UNE COUCHE VECTEUR
    if output_layer == '':
        print(yellow + bold + "Attention : Il n'y a pas de sauvegarde en couche vecteur du résultat de classification des FV arborées. Vous n'avez pas fournit de chemin de sauvegarde." + endC)
    else:
        exportVectorByOgr2ogr(connexion_dic["dbname"], output_layer, tab_arbore, user_name = connexion_dic["user_db"], password = connexion_dic["password_db"], ip_host = connexion_dic["server_db"], num_port = connexion_dic["port_number"], schema_name = connexion_dic["schema"], format_type='GPKG')

    return tab_arbore

###########################################################################################################################################
# FONCTION getCoordRectEnglValue()                                                                                                        #
###########################################################################################################################################
def getCoordRectEnglValue(connexion, tab_ref, attributname = 'x0', debug = 0):
    """
    Rôle : récupère et créé les coordonnées des 4 sommet du rectangle englobant

    Paramètres :
        connexion : connexion à la base donnée et au schéma correspondant
        tab_ref : nom de la table correspondant aux segments de végétation
        attributname : nom de l'attribut créé, par défaut : 'x0'
        debug :  niveau de debug pour l'affichage des commentaires. Par défaut : 0
    """
    if attributname == 'x0':
        l = [1,1]
    elif attributname == 'y0':
        l = [1,2]
    elif attributname == 'x1':
        l = [2,1]
    elif attributname == 'y1':
        l = [2,2]
    elif attributname == 'x3':
        l = [4,1]
    elif attributname == 'y3' :
        l = [4,2]
    else :
        print("Le nom de l'attribut " + attributname + " n'est pas correcte.")

    query = """
    UPDATE %s SET %s = CAST(SPLIT_PART(SPLIT_PART(SUBSTRING(LEFT(public.ST_ASTEXT(public.ST_ORIENTEDENVELOPE(geom)),-2),10),',',%s),' ',%s) as DECIMAL) WHERE fid = fid;
    """ %(tab_ref, attributname, l[0], l[1])

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    return

###########################################################################################################################################
# FONCTION firstClassification()                                                                                                          #
###########################################################################################################################################
def firstClassification(connexion, tab_ref, thresholds, typeclass = 'arbore', debug = 0):
    """
    Rôle : classification en trois classes basée sur un critère de surface et de compacité

    Paramètres :
        connexion : connexion à la base donnée et au schéma correspondant
        tab_ref : nom de la table dans laquelle on calcule l'indicateur de compacité
        thresholds : dictionnaire des seuils de classification des formes végétales arborées
        typeclass : type de classification : 'arbore' ou 'arbustif', par défaut : 'arbore'
        debug :  niveau de debug pour l'affichage des commentaires. Par défaut : 0

    Sortie :
        tab_ref : nom de la table en sortie (qui est tab_ref du paramètre)
    """

    if typeclass == 'arbore':
        query = """
        UPDATE %s SET fv = 'AI' WHERE public.ST_AREA(geom) <= %s AND public.ST_AREA(geom) >= %s AND id_comp >= %s;
        """ %(tab_ref, thresholds["isolatedtree_max_surface"], thresholds["isolatedtree_min_surface"], thresholds["compacity_1_thr"])

        query += """
        UPDATE %s SET fv = 'TA' WHERE public.ST_AREA(geom) <= %s AND public.ST_AREA(geom) >= %s AND id_comp < %s;
        """ %(tab_ref, thresholds["isolatedtree_max_surface"], thresholds["isolatedtree_min_surface"], thresholds["compacity_1_thr"])

        query += """
        UPDATE %s SET fv = 'TA' WHERE public.ST_AREA(geom) < %s;
        """ %(tab_ref, thresholds["isolatedtree_min_surface"])

        query += """
        UPDATE %s SET fv = 'RGPTA' WHERE public.ST_AREA(geom) > %s;
        """ %(tab_ref, thresholds["isolatedtree_max_surface"])
    else :
        query = """
        UPDATE %s SET fv = 'AuI' WHERE public.ST_AREA(geom) <= %s AND public.ST_AREA(geom) >= %s AND id_comp >= %s;
        """ %(tab_ref, thresholds["isolatedshrub_max_surface"],  thresholds["isolatedshrub_min_surface"], thresholds["compacity_1_thr"])

        query += """
        UPDATE %s SET fv = 'TAu' WHERE public.ST_AREA(geom) <= %s AND public.ST_AREA(geom) >= %s AND id_comp < %s;
        """ %(tab_ref, thresholds["isolatedshrub_max_surface"],  thresholds["isolatedshrub_min_surface"], thresholds["compacity_1_thr"])

        query += """
        UPDATE %s SET fv = 'TAu' WHERE public.ST_AREA(geom) < %s;
        """ %(tab_ref, thresholds["isolatedshrub_min_surface"])

        query += """
        UPDATE %s SET fv = 'RGPTAu' WHERE public.ST_AREA(geom) > %s;
        """ %(tab_ref, thresholds["isolatedshrub_max_surface"])

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    return tab_ref

###########################################################################################################################################
# FONCTION secClassification()                                                                                                          #
###########################################################################################################################################
def secClassification(connexion, tab_ref, tab_out, thresholds, save_intermediate_result = False, debug = 0):
    """
    Rôle : détection et classification du reste des polygones classés "regroupement" lors de la première classification

    Paramètres :
        connexion : connexion à la base donnée et au schéma correspondant
        tab_ref : nom de la table correspondant aux segments de végétation
        tab_out : nom de la table contenant les polygones re-classés initialement labellisés "regroupement arboré" lors de la firstClassification()
        thresholds : dictionnaire des seuil à appliquer
        save_intermediate_result : choix de sauvegarde des tables/fichiers intermédiaires. Par défaut :  False
        debug : niveau de debug pour l'affichage des commentaires. Par défaut : 0

    Sortie :
        tab_out : nom de la table où tous les polygones classés initialement "regroupement arboré" sont re-classés
    """

    ## CREATION DE LA TABLE CONTENANT UNIQUEMENT LES ENTITES CLASSÉÉS REGROUPEMENT ##
    # si la table de sortie exite l'effacer
    dropTable(connexion, tab_out)

    query = """
    CREATE TABLE %s AS
        SELECT geom  AS geom
        FROM  %s
        WHERE fv LIKE '%s';
    """ %(tab_out, tab_ref, '%RGPT%')

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    ## PREPARATION DES DONNEES ##

    # Création d'un identifiant unique
    addUniqId(connexion, tab_out)

    # Création d'un index spatial
    addSpatialIndex(connexion, tab_out)

    # Ajout de l'attribut fv
    addColumn(connexion, tab_out, 'fv', 'varchar(100)')

    # Suppression des polygones trop petits (artefacts)
    query = """
    DELETE FROM %s AS t WHERE public.ST_AREA(t.geom) <= 1;
    """ %(tab_out)

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Création et calcul de l'indicateur de convexité
    createConvexityIndicator(connexion, tab_out, debug = debug)

    # Création et calcul de l'indicateur de compacité
    createCompactnessIndicator(connexion, tab_out, thresholds["buffer_compacity_thr"], debug = debug)

    # Création et calcul de l'indicateur d'élongation
    createExtensionIndicator(connexion,tab_out)

    if tab_ref == 'arbore' :
        name_algt = 'AA'
        name_bst = 'BOA'
        thr_wood_sure = thresholds["woodtree_sure_surface"]
    else :
        name_algt = 'AAu'
        name_bst = 'BOAu'
        thr_wood_sure = thresholds["woodshrub_sure_surface"]

    ## CLASSIFICATION ##

    # 1 : on attribut la classe bst à toutes les FV de regroupement
    query = """
    UPDATE %s AS rgt SET fv='%s' WHERE rgt.fid = rgt.fid;
    """ %(tab_out, name_bst)

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # 2 : on attribut la classe algt aux FV selon les règles suivantes pour toutes les FV dont la surface strictement inférieure à une certaine surface de boisement
    query = """
    UPDATE %s AS rgt SET fv = rgt2.value FROM (SELECT '%s' AS value, fid FROM %s WHERE public.ST_AREA(geom) < %s) AS rgt2 WHERE rgt.fid = rgt2.fid and rgt.id_elong > %s;
    """ %(tab_out, name_algt, tab_out, thr_wood_sure, thresholds["extension_1_thr"])

    query += """
    UPDATE %s AS rgt SET fv = rgt2.value FROM (SELECT '%s' AS value, fid FROM %s WHERE public.ST_AREA(geom) < %s) AS rgt2 WHERE rgt.fid = rgt2.fid and rgt.id_conv > %s and rgt.id_elong > %s;
    """ %(tab_out, name_algt, tab_out, thr_wood_sure, thresholds["convexity_1_thr"], thresholds["extension_2_thr"])

    query += """
    UPDATE %s AS rgt SET fv = rgt2.value FROM (SELECT '%s' AS value, fid FROM %s WHERE public.ST_AREA(geom) < %s) AS rgt2 WHERE rgt.fid = rgt2.fid and rgt.id_conv < %s and rgt.id_comp < %s and rgt.id_elong > %s;
    """ %(tab_out, name_algt, tab_out, thr_wood_sure, thresholds["convexity_2_thr"], thresholds["compacity_2_thr"], thresholds["extension_3_thr"])


    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    return tab_out

###########################################################################################################################################
# FONCTION createLayerTree()                                                                                                          #
###########################################################################################################################################
def createLayerTree(connexion, tab_out, tab_firstclass, tab_secclass, debug = 0):
    """
    Rôle : création de la table/couche contenant les formes végétales arborées

    Paramètres :
        connexion : connexion à la base donnée et au schéma correspondant
        tab_firstclass : table en sortie de la première classification
        tab_secclass : table en sortie de la dernière classification concernant les éléments de regroupements arborés
        debug : niveau de debug pour l'affichage des commentaires. Par défaut : 0

    Sortie :
        nom de la table contenant tous les polygones de formes végétales arborées

    """

    query = """
    DROP TABLE IF EXISTS %s;
    CREATE TABLE %s AS
        SELECT strate_arboree.fv as fv, public.ST_MAKEVALID(strate_arboree.geom::public.geometry(POLYGON,2154)) as geom
        FROM ((SELECT ab2.geom, ab2.fv
            FROM (SELECT geom, fv
                    FROM %s
                    WHERE fv in ('AI', 'TA')) as ab2)
                    UNION
                    (SELECT geom, fv
                    FROM %s)) AS strate_arboree;
    """ %(tab_out, tab_out, tab_firstclass, tab_secclass)

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Création d'un identifiant unique
    addUniqId(connexion, tab_out)

    # Création d'un index spatial
    addSpatialIndex(connexion, tab_out)

    # Création de la colonne strate qui correspond à 'A' pour tous les polygones
    addColumn(connexion, tab_out, 'strate', 'varchar(100)')

    query = """
    UPDATE %s SET strate='A';
    """%(tab_out)

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    return tab_out

##################################################
## Classification des FV de la strate arbustive ##
##################################################

###########################################################################################################################################
# FONCTION detectInShrubStratum()                                                                                                         #
###########################################################################################################################################
def detectInShrubStratum(connexion, connexion_dic, schem_tab_ref, table_roads, thresholds = 0, output_layer = '', save_intermediate_result = False, debug = 0):
    """
    Rôle : détecté les formes végétales horizontales au sein de la strate arbustive

    Paramètres :
        connexion : connexion à la base donnée et au schéma correspondant
        connexion_dic : dictionnaire contenant les paramètres de connexion (pour la sauvegarde en fin de fonction)
        schem_tab_ref : schema.nom de la table
        thresholds : dictionnaire des seuils à appliquer, par défaut : {"seuil_surface" : 0, "seuil_compacite_1" : 0, "seuil_compacite_2" : 0, "seuil_convexite" : 0, "seuil_elongation" : 0, "val_largeur_max_alignement" : 0, "val_buffer" : 0}
        output_layer : sauvegarde ou non du résultat final en une couche vectorielle, par défaut ''
        save_intermediate_result : sauvegarde ou non des tables intermédiaires. Par défaut : False
        debug : niveau de debug pour l'affichage des commentaires. Par défaut : 0

    Sortie :
        tab_arbustive : nom de la table contenant les éléments de la strate arbustive classés horizontalement
    """

    # 0# Attribution de valeurs par défaut pour la connexion
    if thresholds == 0:
        thresholds = {
            "isolatedshrub_max_surface" : 20,
            "isolatedshrub_min_surface" : 3,
            "woodshrub_sure_surface" : 100,
            "buffer_compacity_thr" : 0.5,
            "compacity_1_thr" : 0.7,
            "compacity_2_thr" : 0.2,
            "convexity_1_thr" : 0.65,
            "convexity_2_thr" : 0.5,
            "extension_1_thr" : 4,
            "extension_2_thr" : 2,
            "extension_3_thr" : 2.5
        }


    # 1# Récupération de la table composée uniquement des segments arbustifs
    tab_arbu_ini = 'arbustif_ini'

    query = """
    DROP TABLE IF EXISTS %s;
    CREATE TABLE %s AS
        SELECT *
        FROM %s
        WHERE strate = 'Au';
    """ %(tab_arbu_ini, tab_arbu_ini, schem_tab_ref)

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Ajout des indexes
    addSpatialIndex(connexion, tab_arbu_ini)
    addIndex(connexion, tab_arbu_ini, 'fid', 'idx_fid_arbustifini')

    # 2# Regroupement et lissage des segments arbustifs
    if debug >= 3:
        print(bold + "Regroupement et lissage des segments arbustifs" + endC)

    tab_arbu_temp = 'arbustif_temp'

    query = """
    DROP TABLE IF EXISTS %s;
    CREATE TABLE %s AS
        SELECT (public.ST_DUMP(public.ST_MULTI(public.ST_UNION(t.geom)))).geom AS geom
        FROM %s AS t;
    """ %(tab_arbu_temp, tab_arbu_temp, tab_arbu_ini)

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Correction topologique

    query = "UPDATE %s SET %s = public.ST_CollectionExtract(public.ST_ForceCollection(public.ST_MakeValid(%s)),3) WHERE NOT public.ST_IsValid(%s);" % (tab_arbu_temp, 'geom', 'geom', 'geom')
    executeQuery(connexion, query)

    tab_arbu = 'arbustif'
    cutPolygonesByLines(connexion, tab_arbu_temp, table_roads, tab_arbu)

    # Création d'un identifiant unique
    addUniqId(connexion, tab_arbu)

    # Création d'un index spatial
    addSpatialIndex(connexion, tab_arbu)

    # Création de la colonne strate qui correspond à 'arbustif' pour tous les polygones
    addColumn(connexion, tab_arbu, 'strate', 'varchar(100)')

    # Ajout de la valeur 'arbore' pour toutes les entités de la table arbore
    query = """
    UPDATE %s SET strate = 'Au' WHERE fid = fid;
    """ %(tab_arbu)

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Création de la colonne fv
    addColumn(connexion, tab_arbu, 'fv', 'varchar(100)')

    # Création et calcul de l'indicateur de forme : compacité
    createCompactnessIndicator(connexion, tab_arbu, thresholds['buffer_compacity_thr'], debug = debug)

    # 3# Classement des segments en "arbuste isole", "tache arbustive" et "regroupement arbustif"
    # basé sur un critère de surface et de seuil sur l'indice de compacité
    if debug >= 3:
        print(bold + "Classement des segments en 'AuI' (arbustif isole), 'TAu'(tache arbustive) et 'RGPTAu'(regroupement arbustif) basé sur un critère de surface et de seuil sur l'indice de compacité" + endC)

    fst_class = firstClassification(connexion, tab_arbu, thresholds,  'arbustif', debug = debug)
    if 'fst_class' not in locals():
        fst_class = tab_arbu

    # 4# Travaux sur les "regroupements arbustifs"
    if debug >= 3:
        print(bold + "Classement des segments en 'regroupements arbustifs'" + endC)

    sec_class = secClassification(connexion, tab_arbu,'rgpt_arbustif', thresholds, save_intermediate_result, debug = debug)
    if 'sec_class' not in locals():
        sec_class = 'rgpt_arbustif'

    # 5# Regroupement de l'ensemble des entités de la strate arbustive en une seule couche
    if debug >= 3:
        print(bold + "Regroupement de l'ensemble des entités de la strate arbustive en une seule couche" + endC)


    tab_arbustive_tmp = 'strate_arbustive_withsmallpoly'
    tab_arbustive_tmp = createLayerShrub(connexion, tab_arbustive_tmp, fst_class, sec_class, debug = debug)

    tab_arbustive = 'strate_arbustive'
    repository = os.path.dirname(output_layer) + os.sep
    smallPolygonsMerging(connexion, connexion_dic, tab_arbustive_tmp, tab_arbustive, repository, THRESHOLD_SMALL_AREA_POLY = 150, save_intermediate_result = save_intermediate_result, debug = debug)

    if tab_arbustive == '':
        tab_arbustive = 'strate_arbustive'

    # SUPPRESSION DES TABLES QUI NE SONT PLUS UTILES ##
    if not save_intermediate_result :
        dropTable(connexion, tab_arbu_ini)
        dropTable(connexion, fst_class)
        dropTable(connexion, sec_class)
        dropTable(connexion, tab_arbu_temp)
        dropTable(connexion, tab_arbustive_tmp)

    # SAUVEGARDE DU RESULTAT EN UNE COUCHE VECTEUR
    if output_layer == '':
        print(yellow + "Attention : Il n'y a pas de sauvegarde en couche vecteur du résultat de classification des FV arbustives. Vous n'avez pas fournit de chemin de sauvegarde." + endC)
    else:
        exportVectorByOgr2ogr(connexion_dic["dbname"], output_layer, tab_arbustive, user_name = connexion_dic["user_db"], password = connexion_dic["password_db"], ip_host = connexion_dic["server_db"], num_port = connexion_dic["port_number"], schema_name = connexion_dic["schema"], format_type='GPKG')

    return tab_arbustive

###########################################################################################################################################
# FONCTION createLayerShrub()                                                                                                             #
###########################################################################################################################################
def createLayerShrub(connexion, tab_out, tab_firstclass, tab_secclass, debug = 0):
    """
    Rôle : créer une table 'strate_arbustive' qui contient toutes les FV de la strate arbustive

    Paramètres :
        connexion : connexion à la base de données et au schéma correspondant
        tab_firstclass : table en sortie de la première classification
        tab_secclass : table en sortie de la seconde classification concernant les éléments de regroupements arbustifs
        debug : niveau de debug pour l'affichage des commentaires. Par défaut : 0

    Sortie :
        nom de la table contenant tous les éléments de la strate arbustive en fv
    """

    query = """
    DROP TABLE IF EXISTS %s;
    CREATE TABLE %s AS
        SELECT strate_arbustive.fv as fv, public.ST_MAKEVALID(strate_arbustive.geom::public.geometry(POLYGON,2154)) as geom
        FROM ((SELECT ab2.geom, ab2.fv
            FROM (SELECT geom, fv
                    FROM %s
                    WHERE fv in ('AuI', 'TAu')) as ab2)
            UNION
           (SELECT geom, fv
            FROM %s)) AS strate_arbustive;
    """ %(tab_out, tab_out, tab_firstclass, tab_secclass)

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Création d'un identifiant unique
    addUniqId(connexion, tab_out)

    # Création d'un index spatial
    addSpatialIndex(connexion, tab_out)

    # Création de la colonne strate qui correspond à 'Au' pour tous les polygones
    addColumn(connexion, tab_out, 'strate', 'varchar(100)')

    query = """
    UPDATE %s SET strate='Au';
    """%(tab_out)

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    return tab_out


##################################################
## Classification des FV de la strate herbacée  ##
##################################################

###########################################################################################################################################
# FONCTION detectInHerbaceousStratum()                                                                                                    #
###########################################################################################################################################

def detectInHerbaceousStratum(connexion, connexion_dic, schem_tab_ref, empriseVector, table_roads, thresholds,  output_layer = '', save_intermediate_result = False, debug = 0):
    """
    Rôle : détecter les formes végétales horizontales au sein de la strate herbacée

    Paramètres :
        connexion : connexion à la base donnée et au schéma correspondant
        connexion_dic : dictionnaire contenant les paramètres de connexion (pour la sauvegarde en fin de fonction)
        schem_tab_ref : schema.nom de la table
        output_layer : sauvegarde ou non du résultat final en une couche vectorielle, par défaut ''
        save_intermediate_result : sauvegarde ou non des tables intermédiaires
        debug : niveau de debug pour l'affichage des commentaires. Par défaut : 0

    Sortie :
        tab_herbace : nom de la table contenant les éléments de la strate herbace classés horizontalement
    """
    ####################################################
    ## Préparation de la couche herbacée de référence ##
    ####################################################

    # 1# Récupération de la table composée uniquement des segments herbaces
    tab_herb_ini = 'herbace_ini'
    query = """
    DROP TABLE IF EXISTS %s;
    CREATE TABLE %s AS
        SELECT *
        FROM %s
        WHERE strate = 'H';
    """ %(tab_herb_ini, tab_herb_ini, schem_tab_ref)

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Création des indexes
    addSpatialIndex(connexion, tab_herb_ini)
    addIndex(connexion, tab_herb_ini, 'fid', 'idx_fid_herbeini')

    # 2# Regroupement et lissage des segments herbacés
    tab_in = 'herbace'

    query = """
    DROP TABLE IF EXISTS %s ;
    CREATE TABLE %s AS
        SELECT (public.ST_DUMP(public.ST_MULTI(public.ST_UNION(t.geom)))).geom AS geom
        FROM %s AS t;
    """ %(tab_in, tab_in, tab_herb_ini)

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Correction topologique
    try:
        query = "UPDATE %s SET geom = public.ST_CollectionExtract(public.ST_ForceCollection(public.ST_MakeValid(geom)),3) WHERE NOT public.ST_IsValid(geom);" % (tab_in)
        executeQuery(connexion, query)
    except :
        if connexion:
            connexion.rollback()
        print(bold + red + "Correction topologique : Error - Impossible de corriger les erreurs topologiques de la table %s" % (tab_in) + endC, file=sys.stderr)

    # Création d'un identifiant unique
    addUniqId(connexion, tab_in)

    # Création d'un index spatial
    addSpatialIndex(connexion, tab_in)

    # Création de la colonne strate qui correspond à 'A' pour tous les polygones et complétion
    addColumn(connexion, tab_in, 'strate', 'varchar(100)')

    query = """
    UPDATE %s SET strate = 'H' WHERE fid = fid;
    """ %(tab_in)

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Création de la colonne fv
    addColumn(connexion, tab_in, 'fv', 'varchar(100)')
    # Pas de complétion de cet attribut pour l'instant
    tab_herbace = ''

    # Creation d'un dossier temporaire
    working_rep = os.path.dirname(output_layer) + os.sep + "rep_temp"
    if not os.path.isdir(working_rep):
        os.makedirs(working_rep)

    # Complétion de l'attribut fv
    if thresholds["rpg"] != "" and thresholds["rpg"] != None:

        # Préparation du RPG et RPG complété
        rpg_layer = working_rep + os.sep + "rpg_trie.gpkg"
        prepareRPG(connexion, connexion_dic, thresholds, empriseVector, rpg_layer, working_rep, save_intermediate_result = save_intermediate_result, debug = debug)
        ldsc_urban = thresholds["paysages_urbains"]

        # Classification de l'herbacé avec le RPG
        tab_herbace_tmp = classificationGrassOrCrop(connexion, connexion_dic, tab_in, rpg_layer, ldsc_urban, working_rep, save_intermediate_result = save_intermediate_result, debug = debug)

        tab_herbace_cut = "herbace_cut_by_roads"
        cutPolygonesByLines(connexion, tab_herbace_tmp, table_roads, tab_herbace_cut)

        dropColumn(connexion, tab_herbace_cut, 'fid')
        addUniqId(connexion, tab_herbace_cut)

        # mergeSmallPolygons
        table_out = 'strate_herbace'
        tab_herbace = smallPolygonsMerging(connexion, connexion_dic, tab_herbace_cut, table_out, working_rep, THRESHOLD_SMALL_AREA_POLY = 55, save_intermediate_result = save_intermediate_result, debug = debug)

        if not save_intermediate_result :
            dropTable(connexion, tab_herbace_tmp)
            dropTable(connexion, tab_herbace_cut)
    else :
        tab_herbace = 'strate_herbace'
        tab_herbace_tmp = "herbace_to_cut"
        tab_herbace_cut = "herbace_cut_by_roads"

        query = """
        DROP TABLE IF EXISTS %s;
        CREATE TABLE %s AS
            SELECT *
            FROM %s
            WHERE strate = 'H';
        """ %(tab_herbace_tmp, tab_herbace_tmp, schem_tab_ref)

        cutPolygonesByLines(connexion, tab_herbace_tmp, table_roads, tab_herbace_cut)

        dropColumn(connexion, tab_herbace_cut, 'fid')
        addUniqId(connexion, tab_herbace_cut)

        tab_herbace = smallPolygonsMerging(connexion, connexion_dic, tab_herbace_cut, tab_herbace, working_rep, THRESHOLD_SMALL_AREA_POLY = 55, save_intermediate_result = save_intermediate_result, debug = debug)

        if debug >= 3:
            print(query)
        executeQuery(connexion, query)
        addIndex(connexion, tab_herbace, 'fid', 'fid_veg_idx')
        addSpatialIndex(connexion, tab_herbace)


        addColumn(connexion, tab_herbace, 'fv', 'varchar(100)')

        query = """
        UPDATE %s SET fv = 'H' WHERE fid = fid;
        """ %(tab_herbace)

        if debug >= 3:
            print(query)
        executeQuery(connexion, query)


    # SUPPRESSION DES TABLES QUI NE SONT PLUS UTILES ##
    if not save_intermediate_result :
        dropTable(connexion, tab_herb_ini)
        dropTable(connexion, tab_in)
        deleteDir(working_rep)
        dropTable(connexion, tab_herbace_tmp)
        dropTable(connexion, tab_herbace_cut)

    ## SAUVEGARDE DU RESULTAT EN UNE COUCHE VECTEUR
    if output_layer == '' :
        print(bold + yellow + "Attention : Il n'y a pas de sauvegarde en couche vecteur du résultat de classification des FV herbacées. Vous n'avez pas fournit de chemin de sauvegarde." + endC)
    else:
        exportVectorByOgr2ogr(connexion_dic["dbname"], output_layer, tab_herbace, user_name = connexion_dic["user_db"], password = connexion_dic["password_db"], ip_host = connexion_dic["server_db"], num_port = connexion_dic["port_number"], schema_name = connexion_dic["schema"], format_type='GPKG')

    return tab_herbace

########################################################################
# FONCTION classificationGrassOrCrop()                                #
########################################################################

def classificationGrassOrCrop(connexion, connexion_dic, tab_in, rpg_layer, ldsc_urban, working_rep, save_intermediate_result = False, debug = 0) :
    """
    Rôle : produire les formes végétales herbacée 'Pr' (prairie) ou 'C' (culture)

    Paramètres :
        connexion :
        connexion_dic :
        tab_in : nom de la table contenant les segments de végétation herbacée
        thresholds : dictionnaire des paramètres pour détecter les formes végétales herbacées
        working_rep : répertoire temporaire de travail
        save_intermediate_result : paramètre de sauvegarde des tables et/ou fichiers intermédiaires. Par défaut : False
        debug : paramètre du niveau de debug. Par défaut : 0
    """

    layer_sgts_veg_h = working_rep + os.sep + 'sgts_vegetation_herbace.gpkg'
    vector_grass = working_rep + os.sep + 'sgts_vegetation_herbace_prairie.gpkg'
    vector_crop = working_rep + os.sep + 'sgts_vegetation_herbace_culture.gpkg'

    removeVectorFile(layer_sgts_veg_h, format_vector='GPKG')
    removeVectorFile(vector_grass, format_vector='GPKG')
    removeVectorFile(vector_crop, format_vector='GPKG')

    # Export des le donnée vecteur des segments herbacés en couche GPKG
    exportVectorByOgr2ogr(connexion_dic["dbname"], layer_sgts_veg_h, tab_in, user_name = connexion_dic["user_db"], password = connexion_dic["password_db"], ip_host = connexion_dic["server_db"], num_port = connexion_dic["port_number"], schema_name = connexion_dic["schema"], format_type='GPKG')

    # Découpage des zones herbacées par rapport aux cultures
    command = "ogr2ogr -clipsrc %s %s %s  -nlt POLYGONE -overwrite -f GPKG" %(rpg_layer, vector_crop, layer_sgts_veg_h)
    if debug >=2:
        print(command)
    exit_code = os.system(command)
    if exit_code != 0:
        print(cyan + "Découpage de la zone herbacée sur le RPG : " + bold + red + "!!! Une erreur c'est produite au cours du découpage du vecteur : " + layer_sgts_veg_h + endC, file=sys.stderr)
    if debug >=2:
        print(cyan + "Découpage de la zone herbacée sur le RPG : " + endC + "Le fichier vecteur " + layer_sgts_veg_h  + " a ete decoupe resultat : " + vector_crop + " type geom = POLYGONE")

    # Découpage des zones herbacées pour ne garder que les prairie
    differenceVector(rpg_layer, layer_sgts_veg_h, vector_grass, format_vector='GPKG')

    if ldsc_urban != "" :
        vector_grass_nolawn = working_rep + os.sep + 'sgts_vegetation_herbace_prairie_withoutLawn.gpkg'
        vector_lawn = working_rep + os.sep + 'sgts_vegetation_herbace_pelouse.gpkg'

        # Découpage des zones herbacées par rapport aux cultures
        command = "ogr2ogr -clipsrc %s %s %s  -nlt POLYGONE -overwrite -f GPKG" %(ldsc_urban, vector_lawn, vector_grass)
        if debug >=2:
            print(command)
        exit_code = os.system(command)
        if exit_code != 0:
            print(cyan + "Découpage de la zone prairie sur l'urbain : " + bold + red + "!!! Une erreur c'est produite au cours du découpage du vecteur : " + layer_sgts_veg_h + endC, file=sys.stderr)
        if debug >=2:
            print(cyan + "Découpage de la zone prairie sur l'urbain : " + endC + "Le fichier vecteur " + layer_sgts_veg_h  + " a ete decoupe resultat : " + vector_crop + " type geom = POLYGONE")

        # Découpage des zones herbacées pour ne garder que les prairie
        differenceVector(ldsc_urban, vector_grass, vector_grass_nolawn, format_vector='GPKG')
        vector_grass = vector_grass_nolawn

        # Création de la table des pelouses
        tab_lawn_tmp = 'tab_lawn_tmp'

        importVectorByOgr2ogr(connexion_dic["dbname"], vector_lawn, tab_lawn_tmp, user_name = connexion_dic["user_db"], password = connexion_dic["password_db"], ip_host = connexion_dic["server_db"], num_port = connexion_dic["port_number"], schema_name = connexion_dic["schema"])

        tab_lawn = 'tab_lawn'

        query = """
        DROP TABLE IF EXISTS %s ;
        CREATE TABLE %s AS
            SELECT 'PE' as fv, 'H' as strate, (public.ST_DUMP(public.ST_MULTI(public.ST_UNION(public.ST_MakeValid(geom))))).geom AS geom
            FROM %s ;
        """ %(tab_lawn, tab_lawn, tab_lawn_tmp)

        if debug >= 3:
            print(query)
        executeQuery(connexion, query)

        dropTable(connexion, tab_lawn_tmp)
        if not save_intermediate_result :
            removeFile(ldsc_urban)



    # Création des tables de prairie et de culture
    tab_crop_tmp = 'tab_crops_tmp'
    tab_grass_tmp = 'tab_grass_tmp'

    importVectorByOgr2ogr(connexion_dic["dbname"], vector_crop, tab_crop_tmp, user_name = connexion_dic["user_db"], password = connexion_dic["password_db"], ip_host = connexion_dic["server_db"], num_port = connexion_dic["port_number"], schema_name = connexion_dic["schema"])
    importVectorByOgr2ogr(connexion_dic["dbname"], vector_grass, tab_grass_tmp, user_name = connexion_dic["user_db"], password = connexion_dic["password_db"], ip_host = connexion_dic["server_db"], num_port = connexion_dic["port_number"], schema_name = connexion_dic["schema"])


    tab_crop = 'tab_crops'
    tab_grass = 'tab_grass'

    query = """
    DROP TABLE IF EXISTS %s ;
    CREATE TABLE %s AS
        SELECT 'C' as fv, 'H' as strate, (public.ST_DUMP(public.ST_MULTI(public.ST_UNION(public.ST_MakeValid(geom))))).geom AS geom
        FROM %s ;
    """ %(tab_crop, tab_crop, tab_crop_tmp)

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    query = """
    DROP TABLE IF EXISTS %s ;
    CREATE TABLE %s AS
        SELECT 'PR' as fv, 'H' strate, (public.ST_DUMP(public.ST_MULTI(public.ST_UNION(public.ST_MakeValid(geom))))).geom AS geom
        FROM %s ;
    """ %(tab_grass, tab_grass, tab_grass_tmp)

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    dropTable(connexion, tab_crop_tmp)
    dropTable(connexion, tab_grass_tmp)

    query = """
    UPDATE %s AS t SET fv = 'PR' ;
    UPDATE %s AS t SET fv = 'C' ;
    """  %(tab_grass, tab_crop)

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Création de la table contenant les zones herbacées classifiées
    tab_out = 'strate_herbace_1'

    if ldsc_urban != "" :
        query = """
        DROP TABLE IF EXISTS %s;
        CREATE TABLE %s AS
            SELECT 'PR' AS fv, 'H' AS strate, geom AS geom
            FROM %s
            UNION
            SELECT 'C' AS fv, 'H' AS strate, geom AS geom
            FROM %s
            UNION
            SELECT 'PE' AS fv, 'H' AS strate, geom AS geom
            FROM %s
        """ %(tab_out, tab_out, tab_grass, tab_crop, tab_lawn)

        if debug >= 3:
            print(query)
        executeQuery(connexion, query)

        if not save_intermediate_result :
            dropTable(connexion, tab_lawn)

    else :
        query = """
        DROP TABLE IF EXISTS %s;
        CREATE TABLE %s AS
            SELECT 'PR' AS fv, 'H' AS strate, geom AS geom
            FROM %s
            UNION
            SELECT 'C' AS fv, 'H' AS strate, geom AS geom
            FROM %s
        """ %(tab_out, tab_out, tab_grass, tab_crop)

        if debug >= 3:
            print(query)
        executeQuery(connexion, query)

    # Ajout des index
    addUniqId(connexion, tab_out)
    addSpatialIndex(connexion, tab_out)

    # Suppression des tables et fichiers intermédiaires
    if not save_intermediate_result :
        removeFile(layer_sgts_veg_h)
        removeFile(vector_grass)
        removeFile(vector_crop)
        dropTable(connexion, tab_crop)
        dropTable(connexion, tab_grass)

    return tab_out

########################################################################
# FONCTION prepareRPG()                                                #
########################################################################

def prepareRPG(connexion, connexion_dic, rpg_dic, empriseVector, output_layer, working_rep, save_intermediate_result = False, debug = 0) :
    '''
    Rôle : retire les parcelles qui ne sont pas de la culture dans le RPG et le RPG complété

    Paramètres :
        connexion : connexion à la base donnée et au schéma correspondant
        connexion_dic : informations de connexion
        rpg_dic : contient les chemins des fichiers de RPG et RPG complété
        empriseVector : emprise de la zone d'étude
        output_layer : fichier vecteur des cultures
        working_rep : répertoire de travail
        save_intermediate_result : si les fichiers intermédiaires doivent être conservés ou non. Par défaut : False
        debug : niveau de debug pour l'affichage des commentaires. Par défaut : 0
    '''

    rpg = rpg_dic["rpg"]
    rpg_complete = rpg_dic["rpg_complete"]


    # Création de la table RPG

    tab_rpg = 'rpg'
    importVectorByOgr2ogr(connexion_dic["dbname"], rpg, tab_rpg, user_name = connexion_dic["user_db"], password = connexion_dic["password_db"], ip_host = connexion_dic["server_db"], num_port = connexion_dic["port_number"], schema_name = connexion_dic["schema"])


    # Découpage du RPG complété et création de la table du RPG complété sur l'emprise s'il a été donné

    if rpg_complete != "" and rpg_complete != None :

        tab_rpg_complete = 'rpg_complete'
        importVectorByOgr2ogr(connexion_dic["dbname"], rpg_complete, tab_rpg_complete, user_name = connexion_dic["user_db"], password = connexion_dic["password_db"], ip_host = connexion_dic["server_db"], num_port = connexion_dic["port_number"], schema_name = connexion_dic["schema"])


    # Sélection des parcelles qui ne sont pas des prairies

    tab_rpg_sort = 'rpg_assemble'
    query = ""
    tab_tmp = ""

    if rpg_complete != "" and rpg_complete != None :
        tab_tmp = "rpg_trie"
        query = """
        DROP TABLE IF EXISTS %s;
        CREATE TABLE %s AS
            SELECT geom AS geom
            FROM (SELECT public.ST_MakeValid(geom) as geom FROM %s WHERE code_group NOT LIKE '18')
            UNION
            SELECT geom AS geom
            FROM (SELECT public.ST_MakeValid(geom) as geom FROM %s WHERE gc_rpg NOT LIKE '17' AND gc_rpg NOT LIKE '18' AND gc_rpg NOT LIKE '19' AND gc_rpg NOT LIKE '29')
        """ %(tab_tmp, tab_tmp, tab_rpg, tab_rpg_complete)

        if debug >= 3:
            print(query)
        executeQuery(connexion, query)

        query = """
        DROP TABLE IF EXISTS %s;
        CREATE TABLE %s AS
            SELECT (public.ST_DUMP(public.ST_MULTI(public.ST_UNION(geom)))).geom AS geom
            FROM %s
        """ %(tab_rpg_sort, tab_rpg_sort, tab_tmp)


    else :
        query = """
        DROP TABLE IF EXISTS %s;
        CREATE TABLE %s AS
            SELECT (public.ST_DUMP(public.ST_MULTI(public.ST_UNION(geom)))).geom AS geom
            FROM (SELECT public.ST_MakeValid(geom) as geom FROM %s WHERE code_group NOT LIKE '18')
        """ %(tab_rpg_sort, tab_rpg_sort, tab_rpg)

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Correction topologique
    try:
        query = "UPDATE %s SET geom = public.ST_CollectionExtract(public.ST_ForceCollection(public.ST_MakeValid(geom)),3) WHERE NOT public.ST_IsValid(geom);" % (tab_rpg_sort)
        executeQuery(connexion, query)
    except :
        if connexion:
            connexion.rollback()
        print(bold + red + "Correction topologique : Error - Impossible de corriger les erreurs topologiques de la table %s" % (tab_rpg_sort) + endC, file=sys.stderr)

    # Création de la couche vecteur ne contenant que les cultures du RPG (et RPG complété s'il a été donné) sur la zone d'emprise

    exportVectorByOgr2ogr(connexion_dic["dbname"], output_layer, tab_rpg_sort, user_name = connexion_dic["user_db"], password = connexion_dic["password_db"], ip_host = connexion_dic["server_db"], num_port = connexion_dic["port_number"], schema_name = connexion_dic["schema"], format_type='GPKG')

    if not save_intermediate_result :
        dropTable(connexion, tab_rpg)
        if rpg_complete != "" and rpg_complete != None:
            dropTable(connexion, tab_rpg_complete)
        dropTable(connexion, tab_rpg_sort)
        if tab_tmp != "" :
            dropTable(connexion, tab_tmp)


    return

#####################################
## Fonctions indicateurs de formes ##
#####################################

########################################################################
# FONCTION createCompactnessIndicator()                                #
########################################################################
def createCompactnessIndicator(connexion, tab_ref, buffer_value, debug = 0):
    """
    Rôle : créé et calcul un indice de compacité sur une forme pouvant être dilatée ou erodée

    Paramètres :
        connexion : connexion à la base donnée et au schéma correspondant
        tab_ref : nom de la table dans laquelle on calcule l'indicateur de compacité
        buffer_value : valeur attribuée à la bufferisation
        debug : niveau de debug pour l'affichage des commentaires. Par défaut : 0

    Sortie :
        nom de la colonne créé
    """

    # Création et implémentation de l'indicateur de compacité (id_comp)
    query = """
    ALTER TABLE %s ADD id_comp float;

    UPDATE %s AS t SET id_comp = (4*PI()*public.ST_AREA(public.ST_BUFFER(t.geom,%s)))/(public.ST_PERIMETER(public.ST_BUFFER(t.geom,%s))*public.ST_PERIMETER(public.ST_BUFFER(t.geom,%s))) WHERE t.fid = t.fid AND public.ST_PERIMETER(public.ST_BUFFER(t.geom,%s)) <> 0;
    """ %(tab_ref, tab_ref, buffer_value, buffer_value, buffer_value, buffer_value)

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    return

########################################################################
# FONCTION createConvexityIndicator()                                  #
########################################################################
def createConvexityIndicator(connexion, tab_ref, debug = 0):
    """
    Rôle : créé et calcul un indice de convexité sur une forme pouvant être dilatée ou erodée

    Paramètres :
        connexion : connexion à la base donnée et au schéma correspondant
        tab_ref : nom de la table dans laquelle on calcule l'indicateur de compacité
        debug : niveau de debug pour l'affichage des commentaires. Par défaut : 0
    """

    # Création et implémentation de l'indicateur de convexité (id_conv)
    query = """
    ALTER TABLE %s ADD id_conv float;

    UPDATE %s SET id_conv = (public.ST_AREA(geom)/public.ST_AREA(public.ST_ORIENTEDENVELOPE(geom)))
                        WHERE fid = fid AND public.ST_AREA(public.ST_ORIENTEDENVELOPE(geom)) <> 0;
    """ %(tab_ref, tab_ref)

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    return


########################################################################
# FONCTION createExtensionIndicator()                                  #
########################################################################
def createExtensionIndicator(connexion, tab_ref, debug = 0):
    """
    Rôle : créé et calcul un indice d'élongation sur une forme pouvant être dilatée ou erodée

    Paramètres :
        connexion : connexion à la base donnée et au schéma correspondant
        tab_ref : nom de la table dans laquelle on calcule l'indicateur de compacité
        debug : niveau de debug pour l'affichage des commentaires. Par défaut : 0
    """

    # Calcul des valeurs de longueur et de largeur des rectangles orientés englobant minimaux des polygones
    addColumn(connexion, tab_ref, 'x0', 'float')
    addColumn(connexion, tab_ref, 'y0', 'float')
    addColumn(connexion, tab_ref, 'x1', 'float')
    addColumn(connexion, tab_ref, 'y1', 'float')
    addColumn(connexion, tab_ref, 'x3', 'float')
    addColumn(connexion, tab_ref, 'y3', 'float')

    getCoordRectEnglValue(connexion, tab_ref, 'x0')
    getCoordRectEnglValue(connexion, tab_ref, 'x1')
    getCoordRectEnglValue(connexion, tab_ref, 'x3')
    getCoordRectEnglValue(connexion, tab_ref, 'y0')
    getCoordRectEnglValue(connexion, tab_ref, 'y1')
    getCoordRectEnglValue(connexion, tab_ref, 'y3')

    addColumn(connexion, tab_ref, 'largeur', 'float')
    addColumn(connexion, tab_ref, 'longueur', 'float')

    # Calcul des attributs de largeur et longueur du rectangle englobant orienté
    query = """
    UPDATE %s SET largeur= LEAST(sqrt((x1-x0)^2+(y1-y0)^2), sqrt((x3-x0)^2+(y3-y0)^2)) WHERE fid = fid;
    """ %(tab_ref)

    query += """
    UPDATE %s SET longueur= GREATEST(sqrt((x1-x0)^2+(y1-y0)^2), sqrt((x3-x0)^2+(y3-y0)^2)) WHERE fid = fid;
    """ %(tab_ref)

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Création et implémentation de l'indicateur de convexité (id_conv)
    addColumn(connexion, tab_ref, 'id_elong', 'float')

    query = """
    UPDATE %s AS t SET id_elong = (t.longueur/t.largeur)
                        WHERE t.fid = t.fid AND t.largeur <> 0;
    """ %(tab_ref)

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Suppression des attributs qui ne sont plus utiles
    dropColumn(connexion, tab_ref, 'x0')
    dropColumn(connexion, tab_ref, 'x1')
    dropColumn(connexion, tab_ref, 'x3')
    dropColumn(connexion, tab_ref, 'y0')
    dropColumn(connexion, tab_ref, 'y1')
    dropColumn(connexion, tab_ref, 'y3')
    dropColumn(connexion, tab_ref, 'largeur')
    dropColumn(connexion, tab_ref, 'longueur')

    return

########################################################################
# FONCTION distinctForestLineTreeShrub()                               #
########################################################################
def distinctForestLineTreeShrub(connexion, tab_rgpt, seuil_larg, save_intermediate_result= False, debug = 0):
    """
    Rôle : détecter les aligments d'arbres et les boisements

    Paramètres :
        connexion : connexion à la base donnée et au schéma correspondant
        tab_rgpt : nom de la table de regroupement
        seuil_larg : valeur du seuil de largeur maximale d'un alignement
        save_intermediate_result: choix de sauvegarde ou non des tables/fichiers intermédiaires. Par défaut : False
        debug : niveau de debug pour l'affichage des commentaires. Par défaut : 0
    """
    # Création des squelettes des FVs de regroupements
    tab_sqt = tab_rgpt + '_squelette'
    tab_sqt = 'sql_rgpt_arb2'
    query = """
    CREATE TABLE %s AS
        SELECT fid, fv, public.ST_MAKEVALID(public.ST_APPROXIMATEMEDIALAXIS(geom)) AS geom
        FROM %s
    """ %(tab_sqt, tab_rgpt)

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    addSpatialIndex(connexion, tab_sqt,)
    addIndex(connexion, tab_sqt, 'fid', 'idx_fid')

    # Création de la table des segments de squelettes
    tab_sgt_sqt = tab_rgpt + '_sgt_squelette'
    query = """
    DROP TABLE IF EXISTS %s;
    CREATE TABLE %s AS
        SELECT fid AS id_sqt, public.ST_SUBDIVIDE(public.ST_SEGMENTIZE(geom, public.ST_LENGTH(geom)/11)) AS geom
        FROM %s
    """ %(tab_sgt_sqt, tab_sgt_sqt, tab_sqt)

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    addUniqId(connexion, tab_sgt_sqt)
    addSpatialIndex(connexion, tab_sgt_sqt)

    cursor = connexion.cursor()


    # Début de la construction de la requête de création des segments perpendiculaires
    query_seg_perp = "DROP TABLE IF EXISTS ara_seg_perp;\n"
    query_seg_perp += "CREATE TABLE ara_seg_perp (id_sqt int, id_seg text, id_perp text, xR float, yR float, xP float, yP float, geom GEOMETRY);\n"
    query_seg_perp += "INSERT INTO ara_seg_perp VALUES\n"

    # Récupération de la liste des identifiants segments routes
    cursor.execute("SELECT fid AS id_seg FROM %s GROUP BY id_seg ORDER BY id_seg;" %(tab_sgt_sqt))
    id_seg_list = cursor.fetchall()

    # Boucle sur les segments routes
    nb_seg = len(id_seg_list)
    treat_seg = 1
    for id_seg in id_seg_list:
        if debug >= 3:
            print(bold + "    Traitement du segment route : " + endC + str(treat_seg) + "/" + str(nb_seg))

        id_seg = id_seg[0]

        query = """
        SELECT id_sqt FROM %s WHERE fid = %s;
        """ %(tab_sgt_sqt, id_seg)

        cursor.execute(query)
        id_sqt = cursor.fetchone()[0]


        # Table temporaire ne contenant qu'un segment route donné : ST_LineMerge(geom) permet de passer la géométrie de MultiLineString à LineString, pour éviter des problèmes de requêtes spatiales
        query_temp1_seg = "DROP TABLE IF EXISTS ara_temp1_seg;\n"
        query_temp1_seg += "CREATE TABLE ara_temp1_seg AS SELECT id_sqt, fid as id_seg, public.ST_LineMerge(geom) as geom FROM %s WHERE fid = %s;\n" % (tab_sgt_sqt, id_seg)
        if debug >= 3:
            print(query_temp1_seg)
        executeQuery(connexion, query_temp1_seg)


        # Récupération du nombre de sommets du segment route (utile pour les segments routes en courbe, permet de récupérer le dernier point du segment)
        cursor.execute("SELECT public.ST_NPoints(geom) FROM ara_temp1_seg;")
        nb_points = cursor.fetchone()

        # Récupération des coordonnées X et Y des points extrémités du segment route
        query_xR1 = "SELECT public.ST_X(geom) as X FROM (SELECT public.ST_AsText(public.ST_PointN(geom,1)) as geom FROM ara_temp1_seg) as toto;"
        cursor.execute(query_xR1)
        xR1 = cursor.fetchone()
        query_yR1 = "SELECT public.ST_Y(geom) as Y FROM (SELECT public.ST_AsText(public.ST_PointN(geom,1)) as geom FROM ara_temp1_seg) as toto;"
        cursor.execute(query_yR1)
        yR1 = cursor.fetchone()
        query_xR2 = "SELECT public.ST_X(geom) as X FROM (SELECT public.ST_AsText(public.ST_PointN(geom,%s)) as geom FROM ara_temp1_seg) as toto;" % (nb_points)
        cursor.execute(query_xR2)
        xR2 = cursor.fetchone()
        query_yR2 = "SELECT public.ST_Y(geom) as Y FROM (SELECT public.ST_AsText(public.ST_PointN(geom,%s)) as geom FROM ara_temp1_seg) as toto;" % (nb_points)
        cursor.execute(query_yR2)
        yR2 = cursor.fetchone()

        # Transformation des coordonnées X et Y des points extrémités du segment route en valeurs numériques
        xR1 = float(str(xR1)[1:-2])
        yR1 = float(str(yR1)[1:-2])
        xR2 = float(str(xR2)[1:-2])
        yR2 = float(str(yR2)[1:-2])
        if debug >= 3:
            print("      xR1 = " + str(xR1))
            print("      yR1 = " + str(yR1))
            print("      xR2 = " + str(xR2))
            print("      yR2 = " + str(yR2))

        # Calcul des delta X et Y entre les points extrémités du segment route
        dxR = xR1-xR2
        dyR = yR1-yR2
        if debug >= 3:
            print("      dxR = " + str(dxR))
            print("      dyR = " + str(dyR))
            print("\n")

        # Calcul de l'angle (= gisement) entre le Nord et le segment route
        if dxR == 0 or dyR == 0:
            if dxR == 0 and dyR > 0:
                aR = 0
            elif dxR > 0 and dyR == 0:
                aR = 90
            elif dxR == 0 and dyR < 0:
                aR = 180
            elif dxR < 0 and dyR == 0:
                aR = 270
        else:
            aR = math.degrees(math.atan(dxR/dyR))
            if aR < 0:
                aR = aR + 360
        if debug >= 4:
            print("      aR = " + str(aR))

        # Calcul des angles (= gisements) entre le Nord et les 2 segments perpendiculaires au segment route
        aP1 = aR + 90
        if aP1 < 0 :
            aP1 = aP1 + 360
        if aP1 >= 360:
            aP1 = aP1 - 360
        aP2 = aR - 90
        if aP2 < 0 :
            aP2 = aP2 + 360
        if aP2 >= 360:
            aP2 = aP2 - 360
        if debug >= 4:
            print("      aP1 = " + str(aP1))
            print("      aP2 = " + str(aP2))

        # Calculs des coordonnées des nouveaux points à l'extrémité de chaque segment perpendiculaire pour le segment route sélectionné
        seg_length = seuil_larg
        xP1 = xR1 + (seg_length * math.sin(math.radians(aP1)))
        yP1 = yR1 + (seg_length * math.cos(math.radians(aP1)))
        xP2 = xR1 + (seg_length * math.sin(math.radians(aP2)))
        yP2 = yR1 + (seg_length * math.cos(math.radians(aP2)))
        if debug >= 4:
            print("      xP1 = " + str(xP1))
            print("      yP1 = " + str(yP1))
            print("      xP2 = " + str(xP2))
            print("      yP2 = " + str(yP2))
            print("\n")

        # Construction de la requête de création des 2 segments perpendiculaires pour le segment route sélectionné
        query_seg_perp += "    ('%s', '%s', '%s_perp1', %s, %s, %s, %s, 'LINESTRING(%s %s, %s %s)'),\n" % (str(id_sqt), str(id_seg), str(id_seg), xR1, yR1, xP1, yP1, xR1, yR1, xP1, yP1)
        query_seg_perp += "    ('%s', '%s', '%s_perp2', %s, %s, %s, %s, 'LINESTRING(%s %s, %s %s)'),\n" % (str(id_sqt), str(id_seg), str(id_seg), xR1, yR1, xP2, yP2, xR1, yR1, xP2, yP2)

        treat_seg += 1

    # Fin de la construction de la requête de création des segments perpendiculaires et exécution de cette requête
    query_seg_perp = query_seg_perp[:-2] + ";\n" # Transformer la virgule de la dernière ligne SQL en point-virgule (pour terminer la requête)
    query_seg_perp += "ALTER TABLE ara_seg_perp ALTER COLUMN geom TYPE geometry(LINESTRING,%s) USING public.ST_SetSRID(geom,%s);\n" % ('2154','2154') # Mise à jour du système de coordonnées
    query_seg_perp += "CREATE INDEX IF NOT EXISTS seg_perp_geom_gist ON ara_seg_perp USING GIST (geom);\n"

    if debug >= 3:
        print(query_seg_perp)
    executeQuery(connexion, query_seg_perp)

    addSpatialIndex(connexion, ara_seg_perp)

    if debug >= 3:
        print(bold + "Intersect entre les segments perpendiculaires et les bords de la forme végétale :" + endC)

    # Sélection d'une liste de segments de test avec la bordure d'une FV ( 10 segments perpendiculaires)
    cursor.execute("SELECT DISTINCT id_sqt FROM %s" %(tab_sgt_sqt))
    li_fv = cursor.fetchall()
    for id_sqt in li_fv :
        query = """
        SELECT * FROM %s ORDER BY RANDOM() LIMIT 10;
        """

    # Requête d'intersect entre les segments perpendiculaires et bords de la forme végétale
    query_intersect = """
    DROP TABLE IF EXISTS ara_intersect_bound;
    CREATE TABLE ara_intersect_bound AS
        SELECT r.id as id_fv, r.id_seg as id_seg, r.id_perp as id_perp, ST_Intersects(r.geom, b.geom) as intersect_bound
        FROM ara_seg_perp as r, (select public.ST_BOUNDARY(geom) AS geom FROM %s) as b
        WHERE r.id = b.id;
    ALTER TABLE ara_intersect_bound ADD COLUMN id_intersect serial;
    CREATE INDEX IF NOT EXISTS intersect_bati_geom_gist ON ara_intersect_bound USING GIST (geom);
    """  %(tab_rgpt)

    if debug >= 3:
        print(query_intersect)
    executeQuery(connexion, query_intersect)

    print(bold + cyan + "Calcul les statistiques (longueur, largeur et élongation) des formes végétales pour l'instant classées 'regroupement':" + endC)

    # Requête de récupération de longueur et largeur moyenne des formes végétales
    query = """
    CREATE TABLE long_larg_rgpt AS
        SELECT t1.fid, public.ST_LENGTH(t2.geom) AS long, t1.largeur_moy AS larg
        FROM (
            SELECT t2.fid, AVG(public.ST_LENGTH(t1.geom)) AS largeur_moy
            FROM ara_intersect_bound AS t1, %s AS t2
            WHERE public.ST_INTERSECTS(t2.geom, t1.geom)
            GROUP BY t2.fid
            ) as t1,
            %s AS t2
        WHERE t1.fid = t2.fid;
    """ %(tab_rgpt, tab_sqt)

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Ajout de la colonne de l'indicateur élongation et implémentation
    query = """
    ALTER TABLE %s ADD COLUMN id_elong float;
    """ %(tab_rgpt)

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    query = """
    UPDATE %s AS t1 SET id_elong = (t2.long/t2.larg) FROM long_larg_rgpt AS t2 WHERE t1.fid = t2.fid
    """ %(tab_rgpt)

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    if not save_intermediate_result:
        dropTable(connexion, tab_sqt)
        dropTable(connexion, tab_sgt_sqt)
        dropTable(connexion, 'long_larg_rgpt')
        dropTable(connexion, 'ara_intersect_bound')
        dropTable(connexion, 'ara_seg_perp')
        dropTable(connexion, 'ara_temp1_seg')
    return tab_rgpt

########################################################################
# FONCTION formStratumCleaning()                                       #
########################################################################
def formStratumCleaning(connexion, connexion_dic, tab_ref, tab_ref_clean, dic_thresholds, tab_roads, repertory, clean_option = False, save_intermediate_result = False, debug = 1):
    """
    Rôle : nettoyer les formes végétales horizontales parfois mal classées

    Paramètres :
        connexion : connexion à la base donnée et au schéma correspondant
        connexion_dic : dictionnaire contenant les paramètres de connexion (pour la sauvegarde en fin de fonction)
        tab_ref : nom de la table contenant les formes végétales à nettoyer
        tab_ref_clean : nom de la table contenant les formes végétales nettoyées
        clean_option : option de nettoyage plus poussé. Par défaut : False
        save_intermediate_result : paramètre de sauvegarde des fichiers intermédiaires. Par défaut : False
        debug : paramètre de debugage. Par défaut : 1
     Retun :
        tab_ref_clean : nom de la table contenant les formes végétales nettoyées
    """

    # Pour l'instant tab_ref = 'vegetation' et  tab_ref_clean = 'vegetation_to_clean'

    tab_ref_final = tab_ref_clean
    tab_ref_clean = 'vegetation_to_clean_tmp'

    query = """
    DROP TABLE IF EXISTS %s;
    CREATE TABLE %s AS (SELECT * FROM %s)
    """ %(tab_ref_clean, tab_ref_clean, tab_ref)

    if debug >= 3 :
        print(query)
    executeQuery(connexion, query)

    addSpatialIndex(connexion, tab_ref_clean)
    addIndex(connexion, tab_ref_clean, 'fid', 'fid_veg_to_clean')

    query = "UPDATE %s SET %s = public.ST_CollectionExtract(public.ST_ForceCollection(public.ST_MakeValid(%s)),3) WHERE NOT public.ST_IsValid(%s);" % (tab_ref_clean, 'geom', 'geom', 'geom')
    executeQuery(connexion, query)

    # 1# Suppression des FV dont la surface est strictement inférieure à 1m²
    query = """
    DROP TABLE IF EXISTS fv_arbo_delete;
    CREATE TABLE fv_arbo_delete AS
        SELECT t.fid
        FROM (
            SELECT * FROM %s WHERE strate = 'A'
            ) AS t
        WHERE public.ST_AREA(t.geom) < 1;

    DROP TABLE IF EXISTS fv_arbu_delete;
    CREATE TABLE fv_arbu_delete AS
        SELECT t.fid
        FROM (
            SELECT * FROM %s WHERE strate = 'Au'
            ) AS t
        WHERE public.ST_AREA(t.geom) < 1;

    DROP TABLE IF EXISTS fv_herba_delete;
    CREATE TABLE fv_herba_delete AS
        SELECT t.fid
        FROM (
            SELECT * FROM %s WHERE strate = 'H'
            ) AS t
        WHERE public.ST_AREA(t.geom) < 1;
    """ %(tab_ref_clean, tab_ref_clean, tab_ref_clean)

    if debug >= 3 :
        print(query)
    executeQuery(connexion, query)

    query = """
    DELETE FROM %s AS t1 USING fv_arbo_delete AS t2 WHERE t1.fid = t2.fid;

    DELETE FROM %s AS t1 USING fv_arbu_delete AS t2 WHERE t1.fid = t2.fid;

    DELETE FROM %s AS t1 USING fv_herba_delete AS t2 WHERE t1.fid = t2.fid;
    """ %(tab_ref_clean, tab_ref_clean, tab_ref_clean)

    if debug > 3 :
        print(query)
    executeQuery(connexion, query)

    if not save_intermediate_result :
        dropTable(connexion, 'fv_arbo_delete')
        dropTable(connexion, 'fv_arbu_delete')
        dropTable(connexion, 'fv_herba_delete')

    # 2# Reclassification des taches arborées et arbustives ('TA' et 'TAu') en boisements arborés et arbustifs ('BOA' et 'BOAu')
    query = """
    UPDATE %s SET fv = 'AI' WHERE fv = 'TA';
    UPDATE %s SET fv = 'AuI' WHERE fv = 'TAu';
    """ %(tab_ref_clean, tab_ref_clean)
    #UPDATE %s SET fv = 'BOA' WHERE fv = 'TA';
    #UPDATE %s SET fv = 'BOAu' WHERE fv = 'TAu';

    if debug >= 3 :
        print(query)
    executeQuery(connexion, query)

    # 3# Reclassification des formes végétales arborées et arbustives touchant uniquement de l'arboré et de l'arbustif
    # uniquement si un choix de nettoyage a été formulé par l'opérateur sous la forme d'une option
    if clean_option :
        query = """
        DROP TABLE IF EXISTS fv_arbu_touch_arbo;
        CREATE TABLE fv_arbu_touch_arbo AS
            SELECT t1.fid AS fid_arbu, t1.strate AS strate_arbu, t1.fv AS fv_arbu, t1.geom AS geom_arbu,
                    t2.fid AS fid_arbo, t2.strate AS strate_arbo, t2.fv AS fv_arbo, t2.geom AS geom_arbo
            FROM (SELECT * FROM %s WHERE strate = 'Au') as t1, (SELECT * FROM %s WHERE strate = 'A') AS t2
            WHERE public.ST_INTERSECTS(t1.geom, t2.geom);

        DROP TABLE IF EXISTS fv_arbu_touch_herba;
        CREATE TABLE fv_arbu_touch_herba AS
            SELECT t1.fid AS fid_arbu, t1.strate AS strate_arbu, t1.fv AS fv_arbu, t1.geom AS geom_arbu,
                    t2.fid AS fid_herba, t2.strate AS strate_herba, t2.fv AS fv_herba, t2.geom AS geom_herba
            FROM (SELECT * FROM %s WHERE strate = 'Au') as t1, (SELECT * FROM %s WHERE strate = 'H') AS t2
            WHERE public.ST_INTERSECTS(t1.geom, t2.geom);

        DROP TABLE IF EXISTS fv_arbo_touch_herba;
        CREATE TABLE fv_arbo_touch_herba AS
            SELECT t1.fid AS fid_arbo, t1.strate AS strate_arbo, t1.fv AS fv_arbo, t1.geom AS geom_arbo,
                    t2.fid AS fid_herba, t2.strate AS strate_herba, t2.fv AS fv_herba, t2.geom AS geom_herba
            FROM (SELECT * FROM %s WHERE strate = 'A') as t1, (SELECT * FROM %s WHERE strate = 'H') AS t2
            WHERE public.ST_INTERSECTS(t1.geom, t2.geom);
        """ %(tab_ref_clean, tab_ref_clean, tab_ref_clean, tab_ref_clean, tab_ref_clean, tab_ref_clean)

        if debug >= 3 :
            print(query)
        executeQuery(connexion, query)

        addSpatialIndex(connexion, 'fv_arbu_touch_arbo', 'geom_arbu', 'idx_gist_fv1_arbu')
        addSpatialIndex(connexion, 'fv_arbu_touch_arbo', 'geom_arbo', 'idx_gist_fv1_arbo')
        addSpatialIndex(connexion, 'fv_arbu_touch_herba', 'geom_arbu', 'idx_gist_fv2_arbu')
        addSpatialIndex(connexion, 'fv_arbu_touch_herba', 'geom_herba', 'idx_gist_fv2_herba')
        addSpatialIndex(connexion, 'fv_arbo_touch_herba', 'geom_arbo', 'idx_gist_fv3_arbo')
        addSpatialIndex(connexion, 'fv_arbo_touch_herba', 'geom_herba', 'idx_gist_fv3_herba')

        # 3.1# Les FV arbustives
        # Les fvs arbustives ne touchant qu'une fv arborée
        query = """
        DROP TABLE IF EXISTS fv_arbu_touch_only_1_arbo;
        CREATE TABLE fv_arbu_touch_only_1_arbo AS
            SELECT t1.*
            FROM (
                SELECT *
                FROM fv_arbu_touch_arbo
                WHERE fid_arbu NOT IN (SELECT fid_arbu FROM fv_arbu_touch_herba)
                ) AS t1,
                (
                SELECT fid_arbu, count(fid_arbo) AS c
                FROM fv_arbu_touch_arbo
                GROUP BY fid_arbu
                ) AS t2
            WHERE t1.fid_arbu = t2.fid_arbu AND c = 1 ;
        """

        if debug >= 3 :
            print(query)
        executeQuery(connexion, query)

        addSpatialIndex(connexion, 'fv_arbu_touch_only_1_arbo', 'geom_arbu', 'idx_gist_arbu_touch_on_arbu')
        addSpatialIndex(connexion, 'fv_arbu_touch_only_1_arbo', 'geom_arbo', 'idx_gist_arbu_touch_on_arbo')

        # Ré-attribution de la strate 'A' pour les fvs arbustifs concernés
        query = """
        UPDATE %s AS t1 SET strate = 'A'
            FROM (
                SELECT t1.fid_arbu
                FROM (
                    SELECT fid_arbu, fid_arbo, fv_arbu, fv_arbo, public.ST_AREA(geom_arbu)/public.ST_AREA(geom_arbo) AS ratio_surface
                    FROM fv_arbu_touch_only_1_arbo
                    ) AS t1
                WHERE t1.ratio_surface < 0.5
                ) AS t2
            WHERE t1.fid = t2.fid_arbu AND t1.fv IN ('AAu', 'BOAu');
        """ %(tab_ref_clean)


        if debug >= 3 :
            print(query)
        executeQuery(connexion, query)


        # Ré-attribution de la fv avec laquelle la fv arbustive est en contact
        query = """
        UPDATE %s AS t1 SET fv = t2.fv_arbo
            FROM (
                SELECT t1.fid_arbu, t1.fv_arbo
                FROM (
                    SELECT fid_arbu, fid_arbo, fv_arbu, fv_arbo, public.ST_AREA(geom_arbu)/public.ST_AREA(geom_arbo) AS ratio_surface
                    FROM fv_arbu_touch_only_1_arbo
                    ) AS t1
                WHERE t1.ratio_surface < 0.5
                ) as t2
            WHERE t1.fid = t2.fid_arbu AND t1.fv IN ('AAu', 'BOAu');
        """ %(tab_ref_clean)

        if debug >= 3 :
            print(query)
        executeQuery(connexion, query)

        # Les fvs arbustives touchant plus d'une fv arborée
        query = """
        DROP TABLE IF EXISTS fv_arbu_touch_more_2_arbo;
        CREATE TABLE fv_arbu_touch_more_2_arbo AS
            SELECT t1.*
            FROM (
                SELECT *
                FROM fv_arbu_touch_arbo
                WHERE fid_arbu NOT IN (SELECT fid_arbu FROM fv_arbu_touch_herba)
                ) AS t1,
                (SELECT fid_arbu, count(fid_arbo) AS c
                FROM fv_arbu_touch_arbo
                GROUP BY fid_arbu
                ) AS t2
            WHERE t1.fid_arbu = t2.fid_arbu AND c > 1 ;
        """

        if debug >= 3 :
            print(query)
        executeQuery(connexion, query)

        addSpatialIndex(connexion, 'fv_arbu_touch_more_2_arbo', 'geom_arbu', 'idx_gist_arbu_touch_m_2_arbu')
        addSpatialIndex(connexion, 'fv_arbu_touch_more_2_arbo', 'geom_arbo', 'idx_gist_arbu_touch_m_2_arbo')

        # Ré-attribution de la strate 'A' pour les fvs arbustifs concernés
        query = """
        UPDATE %s AS t1 SET strate = 'A'
        FROM (
            SELECT t1.fid_arbu
            FROM (
                SELECT fid_arbu, fid_arbo, fv_arbu, fv_arbo, public.ST_AREA(geom_arbu)/public.ST_AREA(geom_arbo) AS ratio_surface
                FROM fv_arbu_touch_more_2_arbo
                ) AS t1
            WHERE t1.ratio_surface < 0.5
            ) AS t2
        WHERE t1.fid = t2.fid_arbu AND t1.fv IN ('AAu', 'BOAu');
        """ %(tab_ref_clean)

        if debug >= 3 :
            print(query)
        executeQuery(connexion, query)

        # Ré-attribution de la fv avec laquelle la fv arbustive est en contact avec règle de longueur de frontière partagée
        query = """
        UPDATE %s AS t1 SET fv = t2.fv_arbo
            FROM (
                SELECT t1.fid_arbu, t1.fv_arbo
                FROM (
                    SELECT t1.fid_arbu, t1.fid_arbo, t1.fv_arbu, t1.fv_arbo, public.ST_AREA(t1.geom_arbu)/public.ST_AREA(t1.geom_arbo) AS ratio_surface
                    FROM (
                        SELECT t1.*
                        FROM fv_arbu_touch_more_2_arbo AS t1,
                            (
                            SELECT t1.fid_arbu, max(public.ST_LENGTH(public.ST_INTERSECTION(public.ST_BOUNDARY(t1.geom_arbu), public.ST_INTERSECTION(t1.geom_arbu, t1.geom_arbo)))) AS maxi
                            FROM fv_arbu_touch_more_2_arbo AS t1
                            GROUP BY t1.fid_arbu
                            ) as t2
                        WHERE t1.fid_arbu = t2.fid_arbu AND public.ST_LENGTH(public.ST_INTERSECTION(public.ST_BOUNDARY(t1.geom_arbu), public.ST_INTERSECTION(t1.geom_arbu, t1.geom_arbo))) = t2.maxi
                        ) as t1
                    ) as t1
                WHERE t1.ratio_surface < 0.5
                ) as t2
            WHERE t1.fid = t2.fid_arbu AND t1.fv IN ('AAu', 'BOAu');
        """ %(tab_ref_clean)

        if debug >= 3:
            print(query)
        executeQuery(connexion, query)

        # 3.2# Les FV arborées
        # Les fvs arborées ne touchant qu'une fv arbustive

        query = """
        DROP TABLE IF EXISTS fv_arbo_touch_only_1_arbu;
        CREATE TABLE fv_arbo_touch_only_1_arbu AS
            SELECT t1.*
            FROM (
                SELECT *
                FROM fv_arbu_touch_arbo WHERE fid_arbo NOT IN (SELECT fid_arbo FROM fv_arbo_touch_herba)
                ) AS t1,
                (
                SELECT fid_arbo, count(fid_arbu) AS c
                FROM fv_arbu_touch_arbo
                GROUP BY fid_arbo
                ) AS t2
            WHERE t1.fid_arbo = t2.fid_arbo AND c = 1 ;
        """

        if debug >= 3:
            print(query)
        executeQuery(connexion, query)

        addSpatialIndex(connexion, 'fv_arbo_touch_only_1_arbu', 'geom_arbu', 'idx_gist_arbo_touch_on_arbu')
        addSpatialIndex(connexion, 'fv_arbo_touch_only_1_arbu', 'geom_arbo', 'idx_gist_arbuo_touch_on_arbo')

        # Ré-attribution de la strate 'Au' pour les fvs arbustifs concernées
        query = """
        UPDATE %s AS t1 SET strate = 'Au'
            FROM (
                SELECT t1.fid_arbo
                FROM (
                    SELECT fid_arbo, fid_arbu, fv_arbo, fv_arbu, public.ST_AREA(geom_arbu)/public.ST_AREA(geom_arbo) AS ratio_surface
                    FROM fv_arbo_touch_only_1_arbu
                    ) AS t1
                WHERE t1.ratio_surface > 2
                ) AS t2
            WHERE t1.fid = t2.fid_arbo AND t1.fv IN ('AA', 'BOA');
        """ %(tab_ref_clean)

        if debug >= 3:
            print(query)
        executeQuery(connexion, query)

        # Ré-attribution de la fv avec laquelle la fv arborée est en contact avec règle de longueur de frontière partagée
        query = """
        UPDATE %s AS t1 SET fv = t2.fv_arbu
            FROM (
                SELECT t1.fid_arbo, t1.fv_arbu
                FROM (
                    SELECT fid_arbo, fid_arbu, fv_arbo, fv_arbu, public.ST_AREA(geom_arbu)/public.ST_AREA(geom_arbo) AS ratio_surface
                    FROM fv_arbo_touch_only_1_arbu
                    ) AS t1
                WHERE t1.ratio_surface > 2
                ) AS t2
            WHERE t1.fid = t2.fid_arbo AND t1.fv IN ('AA', 'BOA');
        """ %(tab_ref_clean)

        if debug >= 3:
            print(query)
        executeQuery(connexion, query)

        # Les fvs arborées touchant plus d'une fv arbustive
        query = """
        DROP TABLE IF EXISTS fv_arbo_touch_more_2_arbu;
        CREATE TABLE fv_arbo_touch_more_2_arbu AS
            SELECT t1.*
            FROM (
                SELECT *
                FROM fv_arbu_touch_arbo
                WHERE fid_arbo NOT IN (SELECT fid_arbo FROM fv_arbo_touch_herba)
                ) AS t1,
                (
                    SELECT fid_arbo, count(fid_arbu) AS c
                FROM fv_arbu_touch_arbo
                GROUP BY fid_arbo
                ) AS t2
            WHERE t1.fid_arbo = t2.fid_arbo AND c > 1 ;
        """

        if debug >= 3:
            print(query)
        executeQuery(connexion, query)

        addSpatialIndex(connexion, 'fv_arbo_touch_more_2_arbu', 'geom_arbu', 'idx_gist_arbo_touch_m_2_arbu')
        addSpatialIndex(connexion, 'fv_arbu_touch_more_2_arbo', 'geom_arbo', 'idx_gist_arbo_touch_m_2_arbo')

        # Ré-attribution de la strate 'Au' pour les fvs arborées concernées
        query = """
        UPDATE %s AS t1 SET strate = 'Au'
            FROM (
                SELECT t1.fid_arbo
                FROM (
                    SELECT fid_arbo, fid_arbu, fv_arbo, fv_arbu, public.ST_AREA(geom_arbu)/public.ST_AREA(geom_arbo) AS ratio_surface
                    FROM fv_arbo_touch_more_2_arbu
                    ) AS t1
                WHERE t1.ratio_surface > 2
                ) as t2
            WHERE t1.fid = t2.fid_arbo AND t1.fv IN ('AA', 'BOA');
        """ %(tab_ref_clean)

        if debug >= 3:
            print(query)
        executeQuery(connexion, query)

        # Ré-attribution de la fv avec laquelle la fv arborée est en contact avec règle de longueur de frontière partagée
        query = """
        UPDATE %s AS t1 SET fv = t2.fv_arbu
            FROM (
                SELECT t1.fid_arbo, t1.fv_arbu
                FROM (
                    SELECT t1.fid_arbo, t1.fid_arbu, t1.fv_arbo, t1.fv_arbu, public.ST_AREA(t1.geom_arbu)/public.ST_AREA(t1.geom_arbo) AS ratio_surface
                    FROM (
                        SELECT t1.*
                        FROM fv_arbo_touch_more_2_arbu AS t1,
                            (
                            SELECT t1.fid_arbo, max(public.ST_LENGTH(public.ST_INTERSECTION(public.ST_BOUNDARY(t1.geom_arbo), public.ST_INTERSECTION(t1.geom_arbo, t1.geom_arbu)))) AS maxi
                            FROM fv_arbo_touch_more_2_arbu AS t1
                            GROUP BY t1.fid_arbo
                            ) AS t2
                        WHERE t1.fid_arbo = t2.fid_arbo AND public.ST_LENGTH(public.ST_INTERSECTION(public.ST_BOUNDARY(t1.geom_arbo), public.ST_INTERSECTION(t1.geom_arbo, t1.geom_arbu))) = t2.maxi
                        ) AS t1
                    ) AS t1
                WHERE t1.ratio_surface > 2
            ) AS t2
            WHERE t1.fid = t2.fid_arbo AND t1.fv IN ('AA', 'BOA');
        """ %(tab_ref_clean)

        if debug >= 3:
            print(query)
        executeQuery(connexion, query)

        # Comme certaines classes de FV ont été ré-attribuée --> risque que deux fvs similaires soient disposées dans deux polygones séparés

        touch_road = 'touch_road'

        addSpatialIndex(connexion, tab_ref_clean)
        addColumn(connexion, tab_ref_clean, touch_road, 'integer')

        roads_buff = 'roads_buffer'
        query = """
        DROP TABLE IF EXISTS %s ;
        CREATE TABLE %s AS
            SELECT public.ST_BUFFER(geom, 0.01) AS geom
            FROM %s ;
        """%(roads_buff, roads_buff, tab_roads)

        if debug >= 3:
            print(query)
        executeQuery(connexion, query)

        addSpatialIndex(connexion, roads_buff)

        query = """
        UPDATE %s
        SET %s = road FROM (SELECT veg.fid as fid_veg, veg.strate, veg.fv, veg.geom,
                                CASE
                                WHEN public.ST_INTERSECTS(veg.geom, roads.geom) THEN 1
                                ELSE 0
                                END as road
                                FROM %s as veg, %s as roads)
                            WHERE fid = fid_veg ;
        """ %(tab_ref_clean, touch_road, tab_ref_clean, roads_buff)

        if debug >= 3:
            print(query)
        executeQuery(connexion, query)


        reclassPolygonsMerging(connexion, connexion_dic, tab_ref_clean, tab_ref_final, repertory, save_intermediate_result = save_intermediate_result, debug = debug)

        dropColumn(connexion, tab_ref_final, touch_road)

        if not save_intermediate_result :
            dropTable(connexion, 'fv_arbu_touch_arbo')
            dropTable(connexion, 'fv_arbu_touch_herba')
            dropTable(connexion, 'fv_arbo_touch_herba')
            dropTable(connexion, 'fv_arbu_touch_only_1_arbo')
            dropTable(connexion, 'fv_arbu_touch_more_2_arbo')
            dropTable(connexion, 'fv_arbo_touch_only_1_arbu')
            dropTable(connexion, 'fv_arbo_touch_more_2_arbu')
            dropTable(connexion, roads_buff)
            dropTable(connexion, tab_ref_clean)
            if dic_thresholds["lcz"] != "" or dic_thresholds["lcz"] != None :
                dropTable(connexion, "prairie_final_tmp")
                dropTable(connexion, "pelouse_final_tmp")
                dropTable(connexion, "boisement_arbustif_final_tmp")
                dropTable(connexion, "alignement_arbustif_final_tmp")
                dropTable(connexion, "boisement_arbore_final_tmp")
                dropTable(connexion, "alignement_arbore_final_tmp")

    if not save_intermediate_result :
        dropTable(connexion, 'fveg_h')
        dropTable(connexion, 'fveg_a')
        dropTable(connexion, 'fveg_au')

    return tab_ref_final

########################################################################
# FONCTION smallPolygonsMerging()                                       #
########################################################################
def smallPolygonsMerging(connexion, connexion_dic, table, table_out, repertory, THRESHOLD_SMALL_AREA_POLY = 25, save_intermediate_result = False, debug = 0):

    if debug > 0 :
        print('mergeSmallPolygons start...')

    def convert_to_list(value):
        try:
            # Vérifie si la valeur est une chaîne non vide
            if isinstance(value, str) and value.strip():
                return list(map(int, value.split(',')))
            else:
                return []  # Retourne une liste vide si la valeur est vide ou non valide
        except ValueError:
            return []  # Retourne une liste vide si une erreur de conversion se produit

    col_fid = 'new_fid'
    col_area = 'area'

    query = """
    ALTER TABLE %s
    ADD %s FLOAT ;
    UPDATE %s
    SET %s = public.ST_AREA(geom) ;
    """ %(table, col_area, table, col_area)

    if debug >= 3 :
        print(query)
    executeQuery(connexion, query)

    query = """
    ALTER TABLE %s
    ADD %s INTEGER ;
    UPDATE %s
    SET %s = fid ;
    """ %(table, col_fid, table, col_fid)

    if debug >= 3 :
        print(query)
    executeQuery(connexion, query)

    vector_in = repertory + os.sep + 'herbace_withsmallpolygons.gpkg'
    vector_merge = repertory + os.sep + 'herbace_withoutsmallpolygons.gpkg'


    # Conversion de la table au format vecteur
    exportVectorByOgr2ogr(connexion_dic["dbname"], vector_in, table, user_name=connexion_dic["user_db"], password=connexion_dic["password_db"], ip_host=connexion_dic["server_db"], num_port=connexion_dic["port_number"], schema_name=connexion_dic["schema"], format_type='GPKG', ogr2ogr_more_parameters='')

    # Lecture du fichier vecteur avec geopandas
    gdf_seg = gpd.read_file(vector_in)

    FIELD_ORG_ID_LIST = 'org_id'


    gdf_seg[FIELD_ORG_ID_LIST] = gdf_seg[col_fid].apply(convert_to_list)

    gdf_out = mergeSmallPolygons(gdf_seg, threshold_small_area_poly=THRESHOLD_SMALL_AREA_POLY, fid_column=col_fid, org_id_list_column=FIELD_ORG_ID_LIST , area_column=col_area, clean_ring=False)

    # Sauvegarde des resultats en fichier vecteur
    gdf_out[FIELD_ORG_ID_LIST] = gdf_out[FIELD_ORG_ID_LIST].apply(str)
    #gdf_out.to_file(vector_merge, driver='GPKG', crs="EPSG:2154")
    gdf_out = gdf_out.set_crs(epsg=2154, inplace=False)
    gdf_out.to_file(vector_merge, driver='GPKG')

    # Importation en table dans la base de données

    importVectorByOgr2ogr(connexion_dic["dbname"], vector_merge, table_out, user_name=connexion_dic["user_db"], password=connexion_dic["password_db"], ip_host=connexion_dic["server_db"], num_port=connexion_dic["port_number"], schema_name=connexion_dic["schema"], epsg='2154', codage='UTF-8')

    addSpatialIndex(connexion, table_out)
    addIndex(connexion, table_out, 'fid', 'idx_fid_herb_merge')

    # Correction topologique

    query = "UPDATE %s SET geom = public.ST_CollectionExtract(public.ST_ForceCollection(public.ST_MakeValid(geom)),3) WHERE NOT public.ST_IsValid(geom);" % (table_out)
    executeQuery(connexion, query)

    # Suppression des colonnes qui ne sont plus utiles

    dropColumn(connexion, table_out, col_fid)
    dropColumn(connexion, table_out, col_area)
    dropColumn(connexion, table_out, FIELD_ORG_ID_LIST)

    if not save_intermediate_result :
        removeFile(vector_in)
        removeFile(vector_merge)

    if debug > 0 :
        print('mergeSmallPolygons end.')

    return table_out




###########################################################################################################################################
# FONCTION cleanRoads()                                                                                                                  #
###########################################################################################################################################
def cleanRoads(vector_input, vector_output, fields_roads, list_fields_roads, epsg = 2154) :
    """
    Role : tri d'un fichier vecteur sur des conditions sur les attributs

    vector_input : fichier vecteur en entrée
    vector_output : fichier vecteur trié en sortie
    fields_roads : liste des colonnes
    list_fields_roads : liste des valeurs à garder
    epsg : projection

    """

    gdf_roads = gpd.read_file(vector_input)

    for k in range(len(fields_roads)) :
        field = fields_roads[k]
        list_field = list_fields_roads[k]
        gdf_roads_field = gdf_roads[gdf_roads[field].isin(list_field)]
        gdf_roads = gdf_roads_field

    #gdf_roads.to_file(vector_output, driver='ESRI Shapefile', crs="EPSG:" + str(epsg))
    gdf_roads = gdf_roads.set_crs(epsg=epsg, inplace=False)
    gdf_roads.to_file(vector_output, driver='ESRI Shapefile')

    return




###########################################################################################################################################
# FONCTION cutPolygonesByLines_Postgis()                                                                                                  #
###########################################################################################################################################
def cutPolygonesByLines_Postgis(vector_lines_input, vector_poly_input, vector_poly_output, connection, epsg=2154, project_encoding="UTF-8", server_postgis="localhost", port_number=5432, user_postgis="postgres", password_postgis="postgres", database_postgis="cutbylines", schema_postgis="public", path_time_log="", format_vector='ESRI Shapefile', save_results_intermediate=False, overwrite=True) :
    """
    # ROLE:
    #     Découper des polygones ou multi-polygones par des lignes ou multi-lignes en traitement sous postgis
    #
    # ENTREES DE LA FONCTION :
    #     vector_lines_input: le vecteur de lignes de découpe d'entrée
    #     vector_poly_input: le vecteur de polygones à découpés d'entrée
    #     vector_poly_output: le vecteur e polygones de sortie découpés
    #     epsg : EPSG code de projection
    #     project_encoding : encodage des fichiers d'entrés
    #     server_postgis : nom du serveur postgis
    #     port_number : numéro du port pour le serveur postgis
    #     user_postgis : le nom de l'utilisateurs postgis
    #     password_postgis : le mot de passe de l'utilisateur postgis
    #     database_postgis : le nom de la base postgis à utiliser
    #     schema_postgis : le nom du schéma à utiliser
    #     path_time_log : le fichier de log de sortie
    #     format_vector : format du fichier vecteur. Optionnel, par default : 'ESRI Shapefile'
    #     save_results_intermediate : fichiers de sorties intermediaires nettoyees, par defaut = False
    #     overwrite : écrase si un fichier existant a le même nom qu'un fichier de sortie, par defaut a True
    #
    # SORTIES DE LA FONCTION :
    #     na
    #
    """

    # Création de la base de données
    input_lignes_table=  os.path.splitext(os.path.basename(vector_lines_input))[0].lower()
    input_polygons_table =  os.path.splitext(os.path.basename(vector_poly_input))[0].lower()
    output_polygones_table =  os.path.splitext(os.path.basename(vector_poly_output))[0].lower()

    # Import du fichier vecteur lines dans la base
    importVectorByOgr2ogr(database_postgis, vector_lines_input, input_lignes_table, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema_name=schema_postgis, epsg=str(epsg), codage=project_encoding)

    # Import du fichier vecteur polygones dans la base
    importVectorByOgr2ogr(database_postgis, vector_poly_input, input_polygons_table, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema_name=schema_postgis, epsg=str(epsg), codage=project_encoding)

    # Decoupage des polgones
    cutPolygonesByLines(connection, input_polygons_table, input_lignes_table, output_polygones_table, geom_field='geom')


    # Récupération de la base du fichier vecteur de sortie
    exportVectorByOgr2ogr(database_postgis, vector_poly_output, output_polygones_table, user_name=user_postgis, password=password_postgis, ip_host=server_postgis, num_port=str(port_number), schema_name=schema_postgis, format_type=format_vector)


    return



########################################################################
# FONCTION cutPolygonesByLines()                                       #
########################################################################
def cutPolygonesByLines(connection, input_polygones_table, input_lines_table, output_polygones_table, geom_field='geom'):
    """
    # Rôle : découpage de (multi)polygones par des (multi)lignes
    # Paramètres en entrée :
    #   connection : récupère les informations de connexion à la base de données
    #   input_polygones_table : nom de la table polygones à découper
    #   input_lines_table : nom de la table lignes de découpe
    #   output_polygones_table : nom de la table polygones découpés
    #   geom_field : nom du champ de géométrie (par défaut, 'geom')
    """

    # Récupération des champs de la table polygones
    fields_list = getAllColumns(connection, input_polygones_table, print_result=False)
    fields_txt = ""
    for field in fields_list:
        if field != geom_field:
            fields_txt += "g.%s, " % field
    fields_txt = fields_txt[:-2]

    addSpatialIndex(connection, input_polygones_table)
    addSpatialIndex(connection, input_lines_table)

    if len(fields_list) > 1 :
        query = "DROP TABLE IF EXISTS %s;\n" % output_polygones_table
        query += "CREATE TABLE %s AS\n" % output_polygones_table
        #query += "    SELECT %s, (public.ST_DUMP(public.ST_CollectionExtract(public.ST_Split(g.%s, public.ST_LineMerge(r.%s)), 3))).geom AS %s\n" % (fields_txt, geom_field, geom_field, geom_field)
        #query += "    FROM %s AS g, %s AS r\n" % (input_polygones_table, input_lines_table)
        #query += "      GROUP BY %s, g.%s, r.%s;\n" % (fields_txt, geom_field, geom_field)
        query += "    SELECT %s,\n" % fields_txt
        query += "           (public.ST_DUMP(\n"
        query += "               public.ST_CollectionExtract(\n"
        query += "                   public.ST_Split(\n"
        query += "                       public.ST_CollectionExtract(g.%s, 3),\n" % geom_field
        query += "                       public.ST_LineMerge(r.%s)\n" % geom_field
        query += "                   ), 3\n"
        query += "               )\n"
        query += "           )).geom AS %s\n" % geom_field
        query += "    FROM %s AS g, %s AS r\n" % (input_polygones_table, input_lines_table)
        query += "    WHERE public.ST_GeometryType(g.%s) IN ('ST_Polygon', 'ST_MultiPolygon')\n" % geom_field
        query += "    GROUP BY %s, g.%s, r.%s;\n" % (fields_txt, geom_field, geom_field)
        print(query)
        executeQuery(connection, query)
    else :
        query = "DROP TABLE IF EXISTS %s;\n" % output_polygones_table
        query += "CREATE TABLE %s AS\n" % output_polygones_table
        #query += "  SELECT (public.ST_DUMP(public.ST_CollectionExtract(public.ST_Split(g.%s, public.ST_LineMerge(r.%s)), 3))).geom AS %s\n" % (geom_field, geom_field, geom_field)
        #query += "  FROM %s AS g, %s AS r\n" % (input_polygones_table, input_lines_table)
        #query += "    GROUP BY g.%s, r.%s;\n" %(geom_field, geom_field)
        query += "  SELECT (public.ST_DUMP(\n"
        query += "            public.ST_CollectionExtract(\n"
        query += "              public.ST_Split(\n"
        query += "                public.ST_CollectionExtract(g.%s, 3),\n" % geom_field
        query += "                public.ST_LineMerge(r.%s)\n" % geom_field
        query += "              ), 3\n"
        query += "            )\n"
        query += "          )).geom AS %s\n" % geom_field
        query += "  FROM %s AS g, %s AS r\n" % (input_polygones_table, input_lines_table)
        query += "  WHERE public.ST_GeometryType(g.%s) IN ('ST_Polygon', 'ST_MultiPolygon')\n" % geom_field
        query += "  GROUP BY g.%s, r.%s;\n" % (geom_field, geom_field)
        print(query)
        executeQuery(connection, query)

    return

###########################################################################################################################################
# FUNCTION mergeReclassPolygons()                                                                                                           #
###########################################################################################################################################
def mergeReclassPolygons(gdf,  fid_column='FID', road_column = 'touch_road', strate_column = 'fv',  org_id_list_column='org_id_l', clean_ring=True, debug = 0):
    """
    # ROLE:
    #   Merging des polygones de même strate s'ils ne touchent pas la route
    #
    # PARAMETERS:
    #     gdf : dataframe des polygones à fusionnés d'entrée.
    #     fid_column : nom de la colonne contenant l'identifant du polygones (default : 'FID').
    #     road_column : nom de la première colonne de condition des polygones à fusionner
    #     strate_column : nom de la deuxième colonne de condition des polygones à fusionner
    #     org_id_list_column : nom de a colonne contenant la liste des valeur d'id d'origine (default : 'org_id_l').
    #     clean_ring : nettoyage des anneaux sur les polygones (default : 'True').
    # RETURNS:
    #     dataframe des petis polygones mergés.
    """

    # Récupère les polygones qui ne touchent pas de routes
    gdf['geometry'] = gdf['geometry'].buffer(0)
    gdf_reclass_area = gdf[gdf[road_column] == 0]


    # List of polygons FID to merge
    l_reclass_poly = gdf_reclass_area[fid_column].tolist()

    # Iterate over polygons who do not touch roads
    while len(l_reclass_poly) > 0:

        # Get polygon fields
        FID_reclass_poly = l_reclass_poly.pop(0)
        row_reclass_poly = gdf.loc[gdf[fid_column] == FID_reclass_poly]
        geom_reclass_poly = row_reclass_poly["geometry"].values[0]
        fv_reclass_poly = row_reclass_poly[strate_column].values[0]
        orig_id_l_reclass_poly = row_reclass_poly[org_id_list_column].values[0]

        # Get adjacent polygons
        adj_fid_list = findAdjacentPolygons(gdf, row_reclass_poly, fid_column, org_id_list_column)

        # Case when polygon is isolated (no neighbors)
        if not adj_fid_list:
            if debug >= 2:
                print(cyan + "mergeReclassPolygons() : " + endC + "fid: %s, no adjacent polygons" %(FID_reclass_poly))
            continue

        adj_fid = -1

        for fid_adj in adj_fid_list :
            row_adj_poly = gdf.loc[gdf[fid_column] == fid_adj]
            fv_adj_poly = row_adj_poly[strate_column].values[0]
            if adj_fid < 0 and fv_reclass_poly == fv_adj_poly :
                adj_fid = fid_adj

        if adj_fid < 0 :
            continue

        #adj_fid = adj_fid_list[0]
        if debug >= 3:
            print(cyan + "mergeReclassPolygons() : " + endC + "fid: %s, adjacent %s "%(FID_reclass_poly, adj_fid))
        gdf_adj_select_poly = gdf[gdf[fid_column].isin([adj_fid])].copy()

        # Merge polygons with every of its adjacent polygons
        gdf_adj_select_poly = gdf_adj_select_poly.copy()
        merged_geometries = []
        for geom in gdf_adj_select_poly["geometry"]:
            merged_geometry = geom.union(geom_reclass_poly)
            merged_geometries.append(merged_geometry)
        gdf_adj_select_poly['geom_merged'] = merged_geometries
        if clean_ring :
            gdf_adj_select_poly['geom_merged'] = gdf_adj_select_poly['geom_merged'].apply(removeRing)

        # Fusionner les multi-polygons (ne marche pas!!)
        gdf_adj_select_poly = gdf_adj_select_poly[gdf_adj_select_poly['geom_merged'].apply(lambda geom: geom.geom_type in ['Polygon','MultiPolygon'])]

        if gdf_adj_select_poly.empty :
            if debug >= 1:
                print(cyan + "mergeReclassPolygons() : " + endC + "fid: %s, EMPTY_CASE" %(FID_reclass_poly))
            continue

        new_geom = gdf_adj_select_poly["geom_merged"].values[0]
        new_org_id_list = gdf_adj_select_poly[org_id_list_column].values[0] + orig_id_l_reclass_poly
        new_org_id_list = list(set(new_org_id_list))

        # Récupère le FID du polygone merged et updates des champs de la nouvelle geometrie
        best_fid_geom = gdf_adj_select_poly[fid_column].values[0]

        # Maj fields
        idx_row_to_change = gdf.loc[gdf[fid_column] == best_fid_geom].index[0]
        gdf.at[idx_row_to_change, "geometry"] = new_geom
        gdf.at[idx_row_to_change, org_id_list_column] = new_org_id_list

        # Remove the polygon that have been merged
        gdf = gdf.drop(gdf.loc[gdf[fid_column] == FID_reclass_poly].index[0])
        gdf.reset_index(drop=True, inplace=True)


    if debug >= 1:
        print(cyan + "mergeReclassPolygons() : " + endC +"Fin des traitements des petits polygones nouveaux polygons list:", len(gdf))

    return gdf



########################################################################
# FONCTION reclassPolygonsMerging()                                       #
########################################################################
def reclassPolygonsMerging(connexion, connexion_dic, table, table_out, repertory, save_intermediate_result = False, debug = 0):

    if debug > 0 :
        print('mergeReclassPolygons start...')

    def convert_to_list(value):
        try:
            # Vérifie si la valeur est une chaîne non vide
            if isinstance(value, str) and value.strip():
                return list(map(int, value.split(',')))
            else:
                return []  # Retourne une liste vide si la valeur est vide ou non valide
        except ValueError:
            return []  # Retourne une liste vide si une erreur de conversion se produit

    col_fid = 'new_fid'

    query = """
    ALTER TABLE %s
    ADD COLUMN IF NOT EXISTS %s INTEGER ;
    UPDATE %s
    SET %s = fid ;
    """ %(table, col_fid, table, col_fid)

    if debug >= 3 :
        print(query)
    executeQuery(connexion, query)

    vector_in = repertory + os.sep + 'before_merge.gpkg'
    vector_merge = repertory + os.sep + 'after_merge.gpkg'


    # Conversion de la table au format vecteur
    exportVectorByOgr2ogr(connexion_dic["dbname"], vector_in, table, user_name=connexion_dic["user_db"], password=connexion_dic["password_db"], ip_host=connexion_dic["server_db"], num_port=connexion_dic["port_number"], schema_name=connexion_dic["schema"], format_type='GPKG', ogr2ogr_more_parameters='')

    # Lecture du fichier vecteur avec geopandas
    gdf_seg = gpd.read_file(vector_in)

    FIELD_ORG_ID_LIST = 'org_id'
    gdf_seg[FIELD_ORG_ID_LIST] = gdf_seg[col_fid].apply(convert_to_list)

    gdf_out = mergeReclassPolygons(gdf_seg, fid_column=col_fid, org_id_list_column=FIELD_ORG_ID_LIST, clean_ring=False)

    # Sauvegarde des resultats en fichier vecteur
    gdf_out[FIELD_ORG_ID_LIST] = gdf_out[FIELD_ORG_ID_LIST].apply(str)
    #gdf_out.to_file(vector_merge, driver='GPKG', crs="EPSG:2154")
    gdf_out = gdf_out.set_crs(epsg=2154, inplace=False)
    gdf_out.to_file(vector_merge, driver='GPKG')

    # Importation en table dans la base de données
    importVectorByOgr2ogr(connexion_dic["dbname"], vector_merge, table_out, user_name=connexion_dic["user_db"], password=connexion_dic["password_db"], ip_host=connexion_dic["server_db"], num_port=connexion_dic["port_number"], schema_name=connexion_dic["schema"], epsg='2154', codage='UTF-8')

    addSpatialIndex(connexion, table_out)
    addIndex(connexion, table_out, 'fid', 'idx_fid_herb_merge')

    # Correction topologique

    query = "UPDATE %s SET geom = public.ST_CollectionExtract(public.ST_ForceCollection(public.ST_MakeValid(geom)),3) WHERE NOT public.ST_IsValid(geom);" % (table_out)
    executeQuery(connexion, query)

    # Suppression des colonnes qui ne sont plus utiles

    dropColumn(connexion, table_out, col_fid)
    dropColumn(connexion, table_out, FIELD_ORG_ID_LIST)

    if not save_intermediate_result :
        removeFile(vector_in)
        removeFile(vector_merge)

    if debug > 0 :
        print('mergeReclassPolygons end.')

    return table_out

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




















