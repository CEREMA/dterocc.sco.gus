#!/usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.               #
#############################################################################

# Import des librairie Python
import math,os

# Import des librairies de /libs
from libs.Lib_postgis import topologyCorrections, addIndex, addSpatialIndex, addUniqId, addColumn, dropTable, dropColumn,executeQuery, exportVectorByOgr2ogr, importVectorByOgr2ogr, closeConnection, topologyCorrections
from libs.Lib_display import endC, bold, yellow, cyan, red
from libs.CrossingVectorRaster import statisticsVectorRaster
from libs.Lib_file import removeFile, removeVectorFile, deleteDir
from libs.Lib_raster import rasterizeVector
# Import des applications de /app
from app.VerticalStratumDetection import calc_statMedian

#################################################
## Concaténation des trois tables pour obtenir ##
## une unique cartographie                     ##
#################################################

def cartographyVegetation(connexion, connexion_dic, schem_tab_ref, dic_thresholds, raster_dic, output_layers, cleanfv = False, save_intermediate_result = False, overwrite = False, debug = 0):
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
    if overwrite and False:
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

    # 1# Formes végétales arborées
    tab_arbore = ''
    if debug >= 2:
        print(bold + "Détection des formes végétales au sein de la strate arborée" + endC)
    tab_arbore = detectInTreeStratum(connexion, connexion_dic, schem_tab_ref, dic_thresholds["tree"], output_layers["tree"], save_intermediate_result = save_intermediate_result, debug = debug)

    # 2# Formes végétales arbustives
    tab_arbustive = ''
    if debug >= 2:
        print(bold + "Détection des formes végétales au sein de la strate arbustive" + endC)
    tab_arbustive = detectInShrubStratum(connexion, connexion_dic, schem_tab_ref, dic_thresholds["shrub"], output_layers["shrub"], save_intermediate_result = save_intermediate_result, debug = debug)

    # 3# Formes végétales herbacées
    tab_herbace = ''
    if debug >= 2:
        print(bold + "Détection des formes végétales au sein de la strate herbacée" + endC)
    tab_herbace = detectInHerbaceousStratum(connexion, connexion_dic, schem_tab_ref,  dic_thresholds["herbaceous"], output_layers["herbaceous"], save_intermediate_result = save_intermediate_result, debug = debug)

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
    vector_mnh_clean_tmp = os.path.dirname(output_layers["output_fv"]) + os.sep + 'vegetation_tmp.gpkg'
    tab_name = formStratumCleaning(connexion, connexion_dic, tab_name, tab_name_clean, raster_dic["MNH"], vector_mnh_clean_tmp, cleanfv, save_intermediate_result, debug)

    # Lissage de la donnée finale
    #query = """
    #UPDATE %s
    #    SET geom = public.ST_SimplifyPreserveTopology(t.geom, 10)
    #    FROM %s AS t;
    #""" %(tab_name, tab_name)
    #SELECT public.ST_CHAIKINSMOOTHING(t.geom) AS geom

    # Exécution de la requête SQL
    #if debug >= 3:
    #    print(query)
    #executeQuery(connexion, query)

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
    UPDATE %s SET fv_r = 33 WHERE fv = 'H';
    """ %(tab_name, tab_name, tab_name, tab_name, tab_name, tab_name, tab_name, tab_name, tab_name)

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    if output_layers["output_fv"] == '':
        print(yellow + bold + "Attention : Il n'y a pas de sauvegarde en couche vecteur du résultat de classification. Vous n'avez pas fournit de chemin de sauvegarde." + endC)
    else:
        # export au format vecteur
        exportVectorByOgr2ogr(connexion_dic["dbname"], output_layers["output_fv"], tab_name, user_name = connexion_dic["user_db"], password = connexion_dic["password_db"], ip_host = connexion_dic["server_db"], num_port = connexion_dic["port_number"], schema_name = connexion_dic["schema"], format_type='GPKG')
        # export au format raster
        # creation du chemin de sauvegarde de la donnée raster
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
def detectInTreeStratum(connexion, connexion_dic, schem_tab_ref, thresholds = 0, output_layer = '', save_intermediate_result = False, debug = 0):
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

    tab_arb = 'arbore'

    query = """
    DROP TABLE IF EXISTS %s;
    CREATE TABLE %s AS
        SELECT (public.ST_DUMP(public.ST_MULTI(public.ST_UNION(arbore_ini.geom)))).geom AS geom
        FROM %s;
    """ %(tab_arb,tab_arb, tab_arb_ini)
    #SELECT public.ST_CHAIKINSMOOTHING((public.ST_DUMP(public.ST_MULTI(public.ST_UNION(arbore_ini.geom)))).geom) AS geom

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Correction topologique
    topologyCorrections(connexion, tab_arb)

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

    tab_arbore = ''
    tab_arbore = createLayerTree(connexion, fst_class, sec_class, debug = debug)

    if tab_arbore == '':
        tab_arbore = 'strate_arboree'

    # SUPPRESSION DES TABLES QUI NE SONT PLUS UTILES ##
    if not save_intermediate_result :
        dropTable(connexion, tab_arb_ini)
        dropTable(connexion, fst_class)
        dropTable(connexion, sec_class)

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
        SELECT (public.ST_DUMP(public.ST_MULTI(public.ST_UNION(geom)))).geom  AS geom
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

    #Création et calcul de l'indicateur de compacité
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
# FONCTION classTreeWoodStrict()                                                                                                          #
###########################################################################################################################################
def createLayerTree(connexion, tab_firstclass, tab_secclass, debug = 0):
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
    DROP TABLE IF EXISTS strate_arboree;
    CREATE TABLE strate_arboree AS
        SELECT strate_arboree.fv as fv, public.ST_MAKEVALID((public.ST_DUMP(public.ST_UNION(strate_arboree.geom))).geom::public.geometry(POLYGON,2154)) as geom
        FROM ((SELECT ab2.geom, ab2.fv
            FROM (SELECT geom, fv
                    FROM %s
                    WHERE fv in ('AI', 'TA')) as ab2)
                    UNION
                    (SELECT geom, fv
                    FROM %s)) AS strate_arboree
        WHERE public.ST_INTERSECTS(strate_arboree.geom, strate_arboree.geom)
        GROUP BY strate_arboree.fv;
    """ %(tab_firstclass, tab_secclass)

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Création d'un identifiant unique
    addUniqId(connexion, 'strate_arboree')

    # Création d'un index spatial
    addSpatialIndex(connexion, 'strate_arboree')

    # Création de la colonne strate qui correspond à 'A' pour tous les polygones
    addColumn(connexion, 'strate_arboree', 'strate', 'varchar(100)')

    query = """
    UPDATE strate_arboree SET strate='A';
    """

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    return 'strate_arboree'

##################################################
## Classification des FV de la strate arbustive ##
##################################################

###########################################################################################################################################
# FONCTION detectInShrubStratum()                                                                                                         #
###########################################################################################################################################
def detectInShrubStratum(connexion, connexion_dic, schem_tab_ref, thresholds = 0, output_layer = '', save_intermediate_result = False, debug = 0):
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

    tab_arbu = 'arbustif'

    query = """
    DROP TABLE IF EXISTS %s;
    CREATE TABLE %s AS
        SELECT (public.ST_DUMP(public.ST_MULTI(public.ST_UNION(t.geom)))).geom AS geom
        FROM %s AS t;
    """ %(tab_arbu, tab_arbu, tab_arbu_ini)
    #SELECT public.ST_CHAIKINSMOOTHING((public.ST_DUMP(public.ST_MULTI(public.ST_UNION(t.geom)))).geom) AS geom

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Correction topologique
    topologyCorrections(connexion, tab_arbu)

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


    tab_arbustif = ''
    tab_arbustif = createLayerShrub(connexion, fst_class, sec_class, debug = debug)

    if tab_arbustif == '':
        tab_arbustif = 'strate_arbustive'

    # SUPPRESSION DES TABLES QUI NE SONT PLUS UTILES ##
    if not save_intermediate_result :
        dropTable(connexion, tab_arbu_ini)
        dropTable(connexion, fst_class)
        dropTable(connexion, sec_class)

    # SAUVEGARDE DU RESULTAT EN UNE COUCHE VECTEUR
    if output_layer == '':
        print(yellow + "Attention : Il n'y a pas de sauvegarde en couche vecteur du résultat de classification des FV arbustives. Vous n'avez pas fournit de chemin de sauvegarde." + endC)
    else:
        exportVectorByOgr2ogr(connexion_dic["dbname"], output_layer, tab_arbustif, user_name = connexion_dic["user_db"], password = connexion_dic["password_db"], ip_host = connexion_dic["server_db"], num_port = connexion_dic["port_number"], schema_name = connexion_dic["schema"], format_type='GPKG')

    return tab_arbustif

###########################################################################################################################################
# FONCTION createLayerShrub()                                                                                                             #
###########################################################################################################################################
def createLayerShrub(connexion, tab_firstclass, tab_secclass, debug = 0):
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
    DROP TABLE IF EXISTS strate_arbustive;
    CREATE TABLE strate_arbustive AS
        SELECT strate_arbustive.fv as fv, public.ST_MAKEVALID((public.ST_DUMP(public.ST_UNION(strate_arbustive.geom))).geom::public.geometry(POLYGON,2154)) as geom
        FROM ((SELECT ab2.geom, ab2.fv
            FROM (SELECT geom, fv
                    FROM %s
                    WHERE fv in ('AuI', 'TAu')) as ab2)
            UNION
           (SELECT geom, fv
            FROM %s)) AS strate_arbustive
    WHERE public.ST_INTERSECTS(strate_arbustive.geom, strate_arbustive.geom)
    GROUP BY strate_arbustive.fv;
    """ %(tab_firstclass, tab_secclass)

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Création d'un identifiant unique
    addUniqId(connexion, 'strate_arbustive')

    # Création d'un index spatial
    addSpatialIndex(connexion, 'strate_arbustive')

    # Création de la colonne strate qui correspond à 'Au' pour tous les polygones
    addColumn(connexion, 'strate_arbustive', 'strate', 'varchar(100)')

    query = """
    UPDATE strate_arbustive SET strate='Au';
    """

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    return 'strate_arbustive'


##################################################
## Classification des FV de la strate herbacée  ##
##################################################

###########################################################################################################################################
# FONCTION detectInHerbaceousStratum()                                                                                                    #
###########################################################################################################################################
def detectInHerbaceousStratum(connexion, connexion_dic, schem_tab_ref, thresholds,  output_layer = '', save_intermediate_result = False, debug = 0):
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
    #SELECT public.ST_CHAIKINSMOOTHING((public.ST_DUMP(public.ST_MULTI(public.ST_UNION(t.geom)))).geom) AS geom

    # Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Correction topologique
    topologyCorrections(connexion, tab_in)

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
    if thresholds["img_grasscrops"] != "" or thresholds["img_grasscrops"] != None:
        tab_herbace = classificationGrassOrCrop(connexion, connexion_dic, tab_in, thresholds, working_rep, save_intermediate_result = save_intermediate_result, debug = debug)
    else :
        tab_herbace = 'strate_herbace'
        query = """
        DROP TABLE IF EXISTS %s;
        CREATE TABLE %s AS
            SELECT *
            FROM %s;

        UPDATE %s SET fv = 'H';
        """ %(tab_herbace, tab_herbace, tab_herbace, tab_herbace)

        if debug >= 3:
            print(query)
        executeQuery(connexion, query)
        addIndex(connexion, tab_herbace, 'fid', 'fid_veg_idx')
        addSpatialIndex(connexion, tab_herbace)

    # SUPPRESSION DES TABLES QUI NE SONT PLUS UTILES ##
    if not save_intermediate_result :
        dropTable(connexion, tab_herb_ini)
        dropTable(connexion, tab_in)

    ## SAUVEGARDE DU RESULTAT EN UNE COUCHE VECTEUR
    if output_layer == '' :
        print(bold + yellow + "Attention : Il n'y a pas de sauvegarde en couche vecteur du résultat de classification des FV herbacées. Vous n'avez pas fournit de chemin de sauvegarde." + endC)
    else:
        exportVectorByOgr2ogr(connexion_dic["dbname"], output_layer, tab_herbace, user_name = connexion_dic["user_db"], password = connexion_dic["password_db"], ip_host = connexion_dic["server_db"], num_port = connexion_dic["port_number"], schema_name = connexion_dic["schema"], format_type='GPKG')

    return tab_herbace

########################################################################
# FONCTION classificationGrassOrCrop()                                #
########################################################################
def classificationGrassOrCrop(connexion, connexion_dic, tab_in, thresholds, working_rep, save_intermediate_result = False, debug = 0) :
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
    vector_output = working_rep + os.sep + 'sgts_vegetation_hebace_plus_maj.gpkg'

    removeVectorFile(layer_sgts_veg_h, format_vector='GPKG')
    removeVectorFile(vector_output, format_vector='GPKG')

    # Export des le donnée vecteur des segments herbacés en couche GPKG
    exportVectorByOgr2ogr(connexion_dic["dbname"], layer_sgts_veg_h, tab_in, user_name = connexion_dic["user_db"], password = connexion_dic["password_db"], ip_host = connexion_dic["server_db"], num_port = connexion_dic["port_number"], schema_name = connexion_dic["schema"], format_type='GPKG')

    # Calcul de la classe majoritaire par segments herbacé
    col_to_add_list = ["majority"]
    col_to_delete_list = ["min", "max", "mean", "unique", "sum", "std", "range", "median", "minority" ]
    class_label_dico = {}
    statisticsVectorRaster(thresholds["img_grasscrops"], layer_sgts_veg_h, vector_output, band_number=1, enable_stats_all_count = False, enable_stats_columns_str = True, enable_stats_columns_real = False, col_to_delete_list = col_to_delete_list, col_to_add_list = col_to_add_list, class_label_dico = class_label_dico, path_time_log = "", clean_small_polygons = False, format_vector = 'GPKG',  save_results_intermediate= False, overwrite= True)

    # Import en base de la couche vecteur
    tab_cross = 'tab_cross_h_classif'
    importVectorByOgr2ogr(connexion_dic["dbname"], vector_output, tab_cross, user_name=connexion_dic["user_db"], password=connexion_dic["password_db"], ip_host=connexion_dic["server_db"], num_port=connexion_dic["port_number"], schema_name=connexion_dic["schema"], epsg=str(2154))

    # Attribution du label 'PR' (prairie) ou 'C' (culture)
    query = """
    UPDATE %s AS t1 SET fv = 'PR' FROM %s AS t2 WHERE t2.majority = '%s' AND t1.fid = t2.ogc_fid;
    UPDATE %s AS t1 SET fv = 'C' FROM %s AS t2 WHERE t2.majority = '%s' AND t1.fid = t2.ogc_fid;
    """  %(tab_in, tab_cross, thresholds["label_prairie"],tab_in,tab_cross, thresholds["label_culture"])

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # Regroupe par localisation et par label (fv) les semgents de végétation herbacés
    tab_crop = 'tab_crops'
    tab_grass = 'tab_grass'

    # Correction topologique
    topologyCorrections(connexion, tab_in)

    query = """
    DROP TABLE IF EXISTS %s;
    CREATE TABLE %s AS
        SELECT (public.ST_DUMP(public.ST_MULTI(public.ST_UNION(t1.geom)))).geom AS geom
        FROM (SELECT geom FROM %s WHERE fv = 'PR') AS t1;
    """ %(tab_grass, tab_grass, tab_in)
    #SELECT public.ST_CHAIKINSMOOTHING((public.ST_DUMP(public.ST_MULTI(public.ST_UNION(t1.geom)))).geom) AS geom

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)


    query = """
    DROP TABLE IF EXISTS %s;
    CREATE TABLE %s AS
        SELECT (public.ST_DUMP(public.ST_MULTI(public.ST_UNION(t1.geom)))).geom AS geom
        FROM (SELECT geom FROM %s WHERE fv = 'C') AS t1;
    """ %(tab_crop, tab_crop, tab_in)
    #SELECT public.ST_CHAIKINSMOOTHING((public.ST_DUMP(public.ST_MULTI(public.ST_UNION(t1.geom)))).geom) AS geom

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    tab_out = 'strate_herbace'

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
        removeFile(vector_output)
        deleteDir(working_rep)
        dropTable(connexion, tab_cross)
        dropTable(connexion, tab_crop)
        dropTable(connexion, tab_grass)

    return tab_out

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
def formStratumCleaning(connexion, connexion_dic, tab_ref, tab_ref_clean, mnh_raster, vector_mnh_clean_tmp, clean_option = False, save_intermediate_result = False, debug = 1):
    """
    Rôle : nettoyer les formes végétales horizontales parfois mal classées

    Paramètres :
        connexion : connexion à la base donnée et au schéma correspondant
        connexion_dic : dictionnaire contenant les paramètres de connexion (pour la sauvegarde en fin de fonction)
        tab_ref : nom de la table contenant les formes végétales à nettoyer
        tab_ref_clean : nom de la table contenant les formes végétales nettoyées
        mnh_raster : nom du raster contanant le mnh
        vector_mnh_clean_tmp : nom du vecteur contanant l'information du mnh moyen
        clean_option : option de nettoyage plus poussé. Par défaut : False
        save_intermediate_result : paramètre de sauvegarde des fichiers intermédiaires. Par défaut : False
        debug : paramètre de debugage. Par défaut : 1
     Retun :
        tab_ref_clean : nom de la table contenant les formes végétales nettoyées
    """

    # Pour l'instant tab_ref = 'vegetation' et  tab_ref_clean = 'vegetation_to_clean'
    query = """
    DROP TABLE IF EXISTS %s;
    CREATE TABLE %s AS (SELECT * FROM %s)
    """ %(tab_ref_clean, tab_ref_clean, tab_ref)

    if debug >= 3 :
        print(query)
    executeQuery(connexion, query)

    addSpatialIndex(connexion, tab_ref_clean)
    addIndex(connexion, tab_ref_clean, 'fid', 'fid_veg_to_clean')

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

        ## Traitement des surfaces herbacé < à 20m2 et entouré de polygones de type arboré ou arbustif, si le MNH moyen est < à 1 on ne chanche rien si entre 1m et 3m on passe en arbustif et si > à 3m on passé en arboré

        # Sauvegarde de tab_ref_clean en fichier temporaire
        vector_mnh_clean_tmp_in = os.path.splitext(vector_mnh_clean_tmp)[0] + "_in" +  os.path.splitext(vector_mnh_clean_tmp)[1]
        vector_mnh_clean_tmp_out = os.path.splitext(vector_mnh_clean_tmp)[0] + "_out" +  os.path.splitext(vector_mnh_clean_tmp)[1]
        exportVectorByOgr2ogr(connexion_dic["dbname"], vector_mnh_clean_tmp_in, tab_ref_clean, user_name=connexion_dic["user_db"], password=connexion_dic["password_db"], ip_host=connexion_dic["server_db"], num_port=connexion_dic["port_number"], schema_name=connexion_dic["schema"], format_type='GPKG')

        # Calcul de la valeur médiane de hauteur pour chaque segment de végétation
        calc_statMedian(vector_mnh_clean_tmp_in, mnh_raster, vector_mnh_clean_tmp_out)

        # Recharger tab_ref_clean en fonction du fichier vecteur contenant la hauteur moyenne
        dropTable(connexion, tab_ref_clean)
        importVectorByOgr2ogr(connexion_dic["dbname"], vector_mnh_clean_tmp_out, tab_ref_clean, user_name=connexion_dic["user_db"], password=connexion_dic["password_db"], ip_host=connexion_dic["server_db"], num_port=connexion_dic["port_number"], schema_name=connexion_dic["schema"], epsg=str(2154))

        # Calcul des surfaces herbacé < à 20m2
        query = """
        CREATE TABLE tab_out AS
            SELECT t1.*
            FROM (SELECT * FROM %s WHERE public.ST_AREA(geom) > 20) as t1, (SELECT * FROM %s WHERE strate = 'A' OR strate = 'Au') AS t2
            WHERE public.ST_INTERSECTS(t1.geom, t2.geom);




        UPDATE %s AS t SET strate = 'A'
        FROM (
            SELECT t1.fid
            FROM (
                SELECT fid
                FROM %s
                ) AS t2,
                WHERE (
                SELECT fid
                FROM %s
                WHERE public.ST_INTERSECTS(t1.geom, t2.geom)


public.ST_INTERSECTS(t1.geom, t2.geom);
                SELECT fid, strate
                FROM %s WHERE strate = 'A' OR strate = 'Au'
                ) AS t1,
                (
                SELECT fid, strate
                FROM %s
                ) AS t2,
            WHERE public.ST_INTERSECTS(t1.geom, t2.geom)
            GROUP BY t1.fid;
            )
        WHERE public.ST_AREA(geom) < 20) AND strate = 'H';

        """ %(tab_ref_clean, tab_ref_clean)

        if debug >= 3:
            print(query)
        executeQuery(connexion, query)

        # Supprimer la colonne "median" inutile
        dropColumn(connexion, tab_ref_clean, 'median')

        # Comme certaines classes de FV ont été ré-attribuée --> risque que deux fvs similaires soient disposées dans deux polygones séparés
        query = """
        DROP TABLE IF EXISTS fveg_h;
        CREATE TABLE fveg_h AS
            SELECT 'H' AS strate, 'PR' AS fv, (public.ST_DUMP(public.ST_MULTI(public.ST_UNION(geom)))).geom AS geom
            FROM %s
            WHERE fv = 'PR'
            UNION
            SELECT 'H' AS strate, 'C' AS fv, (public.ST_DUMP(public.ST_MULTI(public.ST_UNION(geom)))).geom AS geom
            FROM %s
            WHERE fv = 'C';

        DROP TABLE IF EXISTS fveg_a;
        CREATE TABLE fveg_a AS
            SELECT 'A' AS strate, 'AI' AS fv, (public.ST_DUMP(public.ST_MULTI(public.ST_UNION(geom)))).geom AS geom
            FROM %s
            WHERE fv = 'AI'
            UNION
            SELECT 'A' AS strate, 'AA' AS fv, (public.ST_DUMP(public.ST_MULTI(public.ST_UNION(geom)))).geom AS geom
            FROM %s
            WHERE fv = 'AA'
            UNION
            SELECT 'A' AS strate, 'BOA' AS fv, (public.ST_DUMP(public.ST_MULTI(public.ST_UNION(geom)))).geom AS geom
            FROM %s
            WHERE fv = 'BOA';

        DROP TABLE IF EXISTS fveg_au;
        CREATE TABLE fveg_au AS
            SELECT 'Au' AS strate, 'AuI' AS fv, (public.ST_DUMP(public.ST_MULTI(public.ST_UNION(geom)))).geom AS geom
            FROM %s
            WHERE fv = 'AuI'
            UNION
            SELECT 'Au' AS strate, 'AAu' AS fv, (public.ST_DUMP(public.ST_MULTI(public.ST_UNION(geom)))).geom AS geom
            FROM %s
            WHERE fv = 'AAu'
            UNION
            SELECT 'Au' AS strate, 'BOAu' AS fv, (public.ST_DUMP(public.ST_MULTI(public.ST_UNION(geom)))).geom AS geom
            FROM %s
            WHERE fv = 'BOAu';
        """ %(tab_ref_clean,tab_ref_clean,tab_ref_clean,tab_ref_clean,tab_ref_clean, tab_ref_clean, tab_ref_clean, tab_ref_clean)

        if debug >= 3:
            print(query)
        executeQuery(connexion, query)

        query = """
        DROP TABLE IF EXISTS %s;
        CREATE TABLE %s AS
            SELECT strate, fv, geom
            FROM fveg_h
            UNION
            SELECT strate, fv, geom
            FROM fveg_a
            UNION
            SELECT strate, fv, geom
            FROM fveg_au;
        """ %(tab_ref_clean,tab_ref_clean)

        if debug >= 3:
            print(query)
        executeQuery(connexion, query)

        addUniqId(connexion, tab_ref_clean)

        if not save_intermediate_result :
            dropTable(connexion, 'fv_arbu_touch_arbo')
            dropTable(connexion, 'fv_arbu_touch_herba')
            dropTable(connexion, 'fv_arbo_touch_herba')
            dropTable(connexion, 'fv_arbu_touch_only_1_arbo')
            dropTable(connexion, 'fv_arbu_touch_more_2_arbo')
            dropTable(connexion, 'fv_arbo_touch_only_1_arbu')
            dropTable(connexion, 'fv_arbo_touch_more_2_arbu')

    if not save_intermediate_result :
        dropTable(connexion, 'fveg_h')
        dropTable(connexion, 'fveg_a')
        dropTable(connexion, 'fveg_au')
        removeFile(vector_mnh_clean_tmp_in)
        removeFile(vector_mnh_clean_tmp_out)

    return tab_ref_clean
