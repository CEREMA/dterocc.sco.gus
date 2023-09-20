from Lib_postgis import *

#################################################
## Concaténation des trois tables pour obtenir ##
## une unique cartographie                     ##  
#################################################

def cartographyVegetation(connexion, connexion_dic, schem_tab_ref, dic_thresholds, output_layers, save_intermediate_results = False, overwrite = False, debug = 0):
    """
    Rôle : concatène les trois tables arboré, arbustive et herbacée en un unique 
           correspondant à la carotgraphie de la végétation

    Paramètres :
        connexion : connexion à la base donnée et au schéma correspondant
        connexion_dic : dictionnaire des paramètre de connexion
        schem_tab_ref : schema et nom de la table de référence des segments végétation classés en strates verticales
        dic_thresholds : dictionnaire des seuils à attribuer en fonction de la strate verticale
        output_layers : dictionnaire des noms de fichier de sauvegarde
        save_intermediate_results : sauvegarde ou non des fichiers/tables intermédiaires. Par défaut : False
        overwrite : paramètre de ré-écriture des tables. Par défaut False
        debug : niveau de debug pour l'affichage des commentaires. Par défaut : 0

    Sortie :
        nom de la table contenant toutes les formes végétales
    """ 

    #Rappel du paramétrage 
    if debug >= 2 :
        print(cyan + "cartographyVegetation() : Début de la classification en strates verticales végétales" + endC)
        print(cyan + "cartographyVegetation : " + endC + "connexion_dic : " + str(connexion_dic) + endC)
        print(cyan + "cartographyVegetation : " + endC + "schem_tab_ref : " + str(schem_tab_ref) + endC)
        print(cyan + "cartographyVegetation : " + endC + "dic_thresholds : " + str(dic_thresholds) + endC)
        print(cyan + "cartographyVegetation : " + endC + "output_layers : " + str(output_layers) + endC)
        print(cyan + "cartographyVegetation : " + endC + "save_intermediate_result : " + str(save_intermediate_result) + endC)
        print(cyan + "cartographyVegetation : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "cartographyVegetation : " + endC + "debug : " + str(debug) + endC)

    #Nettoyage en base si ré-écriture
    if overwrite == True:
        print(bold + "Choix de remise à zéro du schéma " + str(shem_tab_ref))
        query ="""
        SELECT format('DROP TABLE %s.%s', table_schema, table_name)
        FROM information_schema.tables
        WHERE table_schema = '%s'; 
        """ %('%I', '%I',connexion_stratev_dic["schema"])
        cursor = connexion.cursor()
        cursor.execute(query)
        tables_schema = cursor.fetchall()
        for el in tables_schema:
            executeQuery(connexion, el[0])

    #1# Formes végétales arborées
    if debug >= 2:
        print(bold + "Détection des formes végétales au sein de la strate arborée" + endC)
    tab_arbore = detectInTreeStratum(connexion, connexion_dic, schem_tab_ref, dic_thresholds["tree"], output_layers["tree"], save_intermediate_results = save_intermediate_results, debug = debug)

    #2# Formes végétales arbustives
    if debug >= 2:
        print(bold + "Détection des formes végétales au sein de la strate arbustive" + endC)
    tab_arbustive = detectInShrubStratum(connexion, connexion_dic, schem_tab_ref, dic_thresholds["shrub"], output_layers["schrub"], save_intermediate_results = save_intermediate_results, debug = debug)
    
    #3# Formes végétales herbacées
    if debug >= 2:
        print(bold + "Détection des formes végétales au sein de la strate herbacée" + endC)
    tab_herbace = detectInHerbaceousStratum(connexion, connexion_dic, schem_tab_ref, output_layers["herbaceous"], save_intermediate_results = save_intermediate_results, debug = debug)

    #4# Concaténation des données en une seule table 'végétation'
    tab_name = 'vegetation'
    if debug >= 2:
        print(bold + "Concaténation des données en une seule table " + tab_name + endC)

    query = """
    CREATE TABLE %s AS
    SELECT fid, geom, strate, fv FROM %s
    UNION
    SELECT fid, geom, strate, fv FROM %s
    UNION 
    SELECT fid, geom, strate, fv FROM %s
    """ %(tab_name, tab_arbore, tab_arbustive, tab_herbace)
    
    if debug => 3:
        print(query)
    executeQuery(connexion, query)

    if output_layers["output_fv"] == '':
        print(yellow + bold + "Attention : Il n'y a pas de sauvegarde en couche vecteur du résultat de classification. Vous n'avez pas fournit de chemin de sauvegarde." + endC)
    else:
        exportVectorByOgr2ogr(connexion_dic["dbname"], output_layers["output_fv"], tab_name, user_name = connexion_dic["user_db"], password = connexion_dic["password_db"], ip_host = connexion_dic["server_db"], num_port = connexion_dic["port_number"], schema_name = connexion_dic["schema"], format_type='GPKG')

    return tab_name



################################################
## Classification des FV de la strate arborée ## 
################################################

###########################################################################################################################################
# FONCTION detectInTreeStratum()                                                                                                          #
###########################################################################################################################################
def detectInTreeStratum(connexion, connexion_dic, schem_tab_ref, thresholds = 0, output_layer = '', save_intermediate_results = False, debug = 0):
    """
    Rôle : détecté les formes végétales horizontales au sein de la strate arborée

    Paramètres :
        connexion : connexion à la base donnée et au schéma correspondant
        connexion_dic : dictionnaire contenant les paramètres de connexion (pour la sauvegarde en fin de fonction)
        schem_tab_ref : schema.nom de la table correspondant aux segments de végétation 
        thresholds : dictionnaire des seuils à appliquer, par défaut : {"seuil_surface" : 0, "seuil_compacite_1" : 0, "seuil_compacite_2" : 0, "seuil_convexite" : 0, "seuil_elongation" : 0, "val_largeur_max_alignement" : 0, "val_buffer" : 0}
        output_layer : sauvegarde du résultat final en une couche vectorielle, par défaut ''
        save_intermediate_results : sauvegarde ou non des tables intermédiaires
        debug : niveau de debug pour l'affichage des commentaires. Par défaut : 0 

    Sortie :
        tab_arbore : nom de la table contenant les éléments de la strate arborée classés horizontalement
    """

    #0# Attribution de valeurs par défaut pour les seuils si non renseignés
    if thresholds == 0:
        thresholds = {"seuil_surface" : 30, "seuil_compacite_1" : 0.7, "seuil_compacite_2" : 0.7, "seuil_convexite" : 0.7, "seuil_elongation" : 2.5, "val_largeur_max_alignement" : 7, "val_buffer" : 1}

    ###################################################
    ## Préparation de la couche arborée de référence ## 
    ###################################################

    #1# Récupération de la table composée uniquement des segments arborés
    tab_arb_ini = 'arbore_ini'

    query = """
    CREATE TABLE %s AS
        SELECT *
        FROM %s
        WHERE strate = 'arbore';
    """ %(tab_arb_ini, schem_tab_ref)

    #Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    #Création des indexes 
    addSpatialIndex(connexion, tab_arb_ini)
    addIndex(connexion, tab_arb_ini, 'fid', 'idx_fid_arboreini')

    #2# Regroupement et lissage des segments arborés
    if debug >= 3:
        print(bold + "Regroupement et lissage des segments arborés" + endC)

    tab_arb = 'arbore'

    query = """
    CREATE TABLE %s AS
        SELECT public.ST_CHAIKINSMOOTHING((public.ST_DUMP(public.ST_MULTI(public.ST_UNION(arbore_ini.geom)))).geom) AS geom
        FROM %s;
    """ %(tab_arb, tab_arb_ini)

    #Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    #Création d'un identifiant unique
    addUniqId(connexion, tab_arb)

    #Création d'un index spatial
    addSpatialIndex(connexion, tab_arb)

    #Création de la colonne strate qui correspond à 'arbore' pour tous les polygones et complétion
    addColumn(connexion, tab_arb, 'strate', 'varchar(100)')

    query = """
    UPDATE %s SET strate = 'arbore' WHERE fid = fid;
    """ %(tab_arb)

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    #Création de la colonne fv
    addColumn(connexion, tab_arb, 'fv', 'varchar(100)')

    #Création et calcul de l'indicateur de forme : compacité
    createCompactnessIndicator(connexion, tab_arb, thresholds["val_buffer"], debug = debug)

    #3# Classement des segments en "arbre isole", "tache arboree" et "regroupement arbore"
    # basé sur un critère de surface et de seuil sur l'indice de compacité

    if debug >= 3:
        print(bold + "Classement des segments en 'arbre isole', 'tache arboree' et 'regroupement arbore' basé sur un critère de surface et de seuil sur l'indice de compacité" + endC)

    fst_class = firstClassification(connexion, tab_arb,  thresholds, 'arbore', debug = debug)
    
    #4# Travaux sur les "regroupements arborés"
    if debug >= 3:
        print(bold + "Classement des segments en 'regroupements arborés'" + endC)

    sec_class = secClassification(connexion, tab_arb, 'rgpt_arbore', thresholds, debug = debug)

    #5# Regroupement de l'ensemble des entités de la strate arborée en une seule couche
    if debug >= 3:
        print(bold + "Regroupement de l'ensemble des entités de la strate arborée en une seule couche" + endC)

    tab_arbore = ''
    tab_arbore = createLayerTree(connexion, fst_class, sec_class, debug = debug)

    if tab_arbore == '':
        tab_arbore = 'strate_arboree'

    # SUPPRESSION DES TABLES QUI NE SONT PLUS UTILES ##
    if not save_intermediate_results :
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
        UPDATE %s AS arb SET fv = 'arbre isole' WHERE public.ST_AREA(arb.geom) <= %s AND arb.id_comp > %s;
        """ %(tab_ref, thresholds["seuil_surface"], thresholds["seuil_compacite_1"])

        query += """
        UPDATE %s AS arb SET fv = 'tache arboree' WHERE public.ST_AREA(arb.geom) <= %s AND arb.id_comp <= %s;
        """ %(tab_ref, thresholds["seuil_surface"], thresholds["seuil_compacite_1"])

        query += """
        UPDATE %s AS arb SET fv = 'regroupement arbore' WHERE public.ST_AREA(arb.geom) > %s;
        """ %(tab_ref, thresholds["seuil_surface"])
    else :
        query = """
        UPDATE %s AS arb SET fv = 'arbuste isole' WHERE public.ST_AREA(geom) <= %s AND id_comp > %s;
        """ %(tab_ref, thresholds["seuil_surface"], thresholds["seuil_compacite_1"])

        query += """
        UPDATE %s AS arb SET fv = 'tache arbustive' WHERE public.ST_AREA(geom) <= %s AND id_comp <= %s;
        """ %(tab_ref, thresholds["seuil_surface"], thresholds["seuil_compacite_1"])

        query += """
        UPDATE %s AS arb SET fv = 'regroupement arbustif' WHERE public.ST_AREA(geom) > %s;
        """ %(tab_ref, thresholds["seuil_surface"])

    #Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    return tab_ref

###########################################################################################################################################
# FONCTION secClassification()                                                                                                          #
###########################################################################################################################################
def secClassification(connexion, tab_ref, tab_out, thresholds, debug = 0):
    """
    Rôle : détection et classification du reste des polygones classés "regroupement" lors de la première classification

    Paramètres :
        connexion : connexion à la base donnée et au schéma correspondant
        tab_ref : nom de la table correspondant aux segments de végétation
        tab_out : nom de la table contenant les polygones re-classés initialement labellisés "regroupement arboré" lors de la firstClassification()
        thresholds : dictionnaire des seuil à appliquer
        debug : niveau de debug pour l'affichage des commentaires. Par défaut : 0

    Sortie :
        tab_out : nom de la table où tous les polygones classés initialement "regroupement arboré" sont re-classés
    """

    ## CREATION DE LA TABLE CONTENANT UNIQUEMENT LES ENTITES CLASSÉÉS REGROUPEMENT ##

    query = """
    CREATE TABLE %s AS
        SELECT public.ST_MAKEVALID(public.ST_UNION(geom)) AS geom
        FROM  %s
        WHERE fv LIKE '%s';
    """ %(tab_out, tab_ref, '%regroupement%')

    #Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    ## PREPARATION DES DONNEES ##

    #Création d'un identifiant unique
    addUniqId(connexion, tab_out)

    #Création d'un index spatial
    addSpatialIndex(connexion, tab_out)

    #Ajout de l'attribut fv
    addColumn(connexion, tab_out, 'fv', 'varchar(100)')

    #Suppression des polygones trop petits (artefacts)
    query = """
    DELETE FROM %s AS t WHERE public.ST_AREA(t.geom) <= 1;
    """ %(tab_out)

    #Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    #Création et calcul de l'indicateur de convexité
    createConvexityIndicator(connexion, tab_out, debug = debug)

    #Création et calcul de l'indicateur de compacité
    createCompactnessIndicator(connexion, tab_out, thresholds["val_buffer"], debug = debug)

    #Création et calcul de l'indicateur d'élongation
    createExtensionIndicator(connexion,tab_out)

    if tab_ref == 'arbore' :
        name_algt = 'alignement arbore'
        name_bst = 'boisement arbore'
    else :
        name_algt = 'alignement arbustif'
        name_bst = 'boisement arbustif'

    ## CLASSIFICATION ##

    query = """
    UPDATE %s AS rgt SET fv='%s'
    WHERE  rgt.id_conv >= %s AND rgt.id_elong  >= %s;
    """ %(tab_out, name_algt, thresholds["seuil_convexite"], thresholds["seuil_elongation"])

    query += """
    UPDATE %s AS rgt SET fv='%s'
    WHERE rgt.id_conv >= %s AND rgt.id_elong < %s;
    """ %(tab_out, name_bst, thresholds["seuil_convexite"], thresholds["seuil_elongation"])

    query += """
    UPDATE %s AS rgt SET fv='%s'
    WHERE rgt.id_conv < %s AND rgt.id_comp < %s;
    """ %(tab_out, name_algt, thresholds["seuil_convexite"], thresholds["seuil_compacite_2"])

    query += """
    UPDATE %s AS rgt SET fv='%s'
    WHERE rgt.id_conv < %s AND rgt.id_comp >= %s;
    """ %(tab_out, name_bst, thresholds["seuil_convexite"], thresholds["seuil_compacite_2"])

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
    CREATE TABLE strate_arboree AS
        SELECT strate_arboree.fv as fv, public.ST_MAKEVALID((public.ST_DUMP(public.ST_UNION(strate_arboree.geom))).geom::public.geometry(POLYGON,2154)) as geom
        FROM ((SELECT ab2.geom, ab2.fv
            FROM (SELECT geom, fv
                    FROM %s
                    WHERE fv in ('arbre isole', 'tache arboree')) as ab2)
                    UNION
                    (SELECT geom, fv
                    FROM %s)) AS strate_arboree
        WHERE public.ST_INTERSECTS(strate_arboree.geom, strate_arboree.geom)
        GROUP BY strate_arboree.fv;
    """ %(tab_firstclass, tab_secclass)

    #Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    #Création d'un identifiant unique
    addUniqId(connexion, 'strate_arboree')

    #Création d'un index spatial
    addSpatialIndex(connexion, 'strate_arboree')

    #Création de la colonne strate qui correspond à 'arboree' pour tous les polygones
    addColumn(connexion, 'strate_arboree', 'strate', 'varchar(100)')

    query = """
    UPDATE strate_arboree SET strate='arbore';
    """

    #Exécution de la requête SQL
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
def detectInShrubStratum(connexion, connexion_dic, schem_tab_ref, dic_thresholds, output_layer = '', save_intermediate_results = False, debug = 0):
    """
    Rôle : détecté les formes végétales horizontales au sein de la strate arbustive

    Paramètres :
        connexion : connexion à la base donnée et au schéma correspondant
        connexion_dic : dictionnaire contenant les paramètres de connexion (pour la sauvegarde en fin de fonction)
        schem_tab_ref : schema.nom de la table
        dic_thresholds : dictionnaire des seuils à appliquer, par défaut : {"seuil_surface" : 0, "seuil_compacite_1" : 0, "seuil_compacite_2" : 0, "seuil_convexite" : 0, "seuil_elongation" : 0, "val_largeur_max_alignement" : 0, "val_buffer" : 0}
        output_layer : sauvegarde ou non du résultat final en une couche vectorielle, par défaut ''
        save_intermediate_results : sauvegarde ou non des tables intermédiaires
        debug : niveau de debug pour l'affichage des commentaires. Par défaut : 0

    Sortie :
        tab_arbustive : nom de la table contenant les éléments de la strate arbustive classés horizontalement
    """

    #0# Attribution de valeurs par défaut pour la connexion
    if thresholds == 0:
        thresholds = {"seuil_surface" : 5, "seuil_compacite_1" : 0.7, "seuil_compacite_2" : 0.7, "seuil_convexite" : 0.7, "seuil_elongation" : 2.5, "val_largeur_max_alignement" : 7, "val_buffer" : 1}


    #1# Récupération de la table composée uniquement des segments arbustifs
    tab_arbu_ini = 'arbustif_ini'

    query = """
    CREATE TABLE %s AS
        SELECT *
        FROM %s
        WHERE strate = 'arbustif';
    """ %(tab_arbu_ini, tab_ref)

    #Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)
    
    #Ajout des indexes 
    addSpatialIndex(connexion, tab_arbu_ini)
    addIndex(connexion, tab_arbu_ini, 'fid', 'idx_fid_arbustifini')

    #2# Regroupement et lissage des segments arbustifs
    if debug >= 3:
        print(bold + "Regroupement et lissage des segments arbustifs" + endC)

    tab_arbu = 'arbustif'

    query = """
    CREATE TABLE %s AS
        SELECT public.ST_CHAIKINSMOOTHING((public.ST_DUMP(public.ST_MULTI(public.ST_UNION(t.geom)))).geom) AS geom
        FROM %s AS t;
    """ %(tab_arbu, tab_arbu_ini)

    # #Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # #Création d'un identifiant unique
    addUniqId(connexion, tab_arbu)

    # #Création d'un index spatial
    addSpatialIndex(connexion, tab_arbu)

    # #Création de la colonne strate qui correspond à 'arbustif' pour tous les polygones
    addColumn(connexion, tab_arbu, 'strate', 'varchar(100)')

    #Ajout de la valeur 'arbore' pour toutes les entités de la table arbore
    query = """
    UPDATE %s SET strate = 'arbustif' WHERE fid = fid;
    """ %(tab_arbu)
    
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    # #Création de la colonne fv
    addColumn(connexion, tab_arbu, 'fv', 'varchar(100)')

    # #Création et calcul de l'indicateur de forme : compacité
    createCompactnessIndicator(connexion, tab_arbu, thresholds['val_buffer'], debug = debug)

    #3# Classement des segments en "arbuste isole", "tache arbustive" et "regroupement arbustif"
       # basé sur un critère de surface et de seuil sur l'indice de compacité
    if debug >= 3:
        print(bold + "Classement des segments en 'arbustif isole', 'tache arbustive' et 'regroupement arbustif' basé sur un critère de surface et de seuil sur l'indice de compacité" + endC)

    fst_class = firstClassification(connexion, tab_arbu, thresholds,  'arbustif', debug = debug)
    
    #4# Travaux sur les "regroupements arbustifs"
    if debug >= 3:
        print(bold + "Classement des segments en 'regroupements arbustifs'" + endC)

    sec_class = secClassification(connexion, tab_arbu,'rgpt_arbustif', thresholds, debug = debug)

    #5# Regroupement de l'ensemble des entités de la strate arborée en une seule couche
    if debug >= 3:
        print(bold + "Regroupement de l'ensemble des entités de la strate arbustive en une seule couche" + endC)


    tab_arbustif = ''
    tab_arbustif = createLayerShrub(connexion, fst_class, sec_class, debug = debug)

    if tab_arbustif == '':
        tab_arbustif = 'strate_arbustive'

    ## SUPPRESSION DES TABLES QUI NE SONT PLUS UTILES ##
    if not save_intermediate_results :
        dropTable(connexion, tab_arbu_ini)
        dropTable(connexion, fst_class)
        dropTable(connexion, sec_class)

    # SAUVEGARDE DU RESULTAT EN UNE COUCHE VECTEUR
    if output_layer == '':
        print(yellow + "Attention : Il n'y a pas de sauvegarde en couche vecteur du résultat de classification des FV arbustives. Vous n'avez pas fournit de chemin de sauvegarde." + endC)
    else:
        exportVectorByOgr2ogr(connexion_fv_dic["dbname"], output_layer, tab_arbustif, user_name = connexion_fv_dic["user_db"], password = connexion_fv_dic["password_db"], ip_host = connexion_fv_dic["server_db"], num_port = connexion_fv_dic["port_number"], schema_name = connexion_fv_dic["schema"], format_type='GPKG')
    
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
    CREATE TABLE strate_arbustive AS
        SELECT strate_arbustive.fv as fv, public.ST_MAKEVALID((public.ST_DUMP(public.ST_UNION(strate_arbustive.geom))).geom::public.geometry(POLYGON,2154)) as geom
    FROM ((SELECT ab2.geom, ab2.fv
            FROM (SELECT geom, fv
                    FROM %s
                    WHERE fv in ('arbuste isole', 'tache arbustive')) as ab2)
            UNION
           (SELECT geom, fv
            FROM %s)) AS strate_arbustive
    WHERE public.ST_INTERSECTS(strate_arbustive.geom, strate_arbustive.geom)
    GROUP BY strate_arbustive.fv;
    """ %(tab_firstclass, tab_secclass)

    #Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    #Création d'un identifiant unique
    addUniqId(connexion, 'strate_arbustive')

    #Création d'un index spatial
    addSpatialIndex(connexion, 'strate_arbustive')

    #Création de la colonne strate qui correspond à 'arboree' pour tous les polygones
    addColumn(connexion, 'strate_arbustive', 'strate', 'varchar(100)')

    query = """
    UPDATE strate_arbustive SET strate='arbustif';
    """

    #Exécution de la requête SQL
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
def detectInHerbaceousStratum(connexion, connexion_dic, schem_tab_ref, output_layer = '', save_intermediate_results = False, debug = 0):
    """
    Rôle : détecter les formes végétales horizontales au sein de la strate herbacée

    Paramètres :
        connexion : connexion à la base donnée et au schéma correspondant
        connexion_dic : dictionnaire contenant les paramètres de connexion (pour la sauvegarde en fin de fonction)
        schem_tab_ref : schema.nom de la table
        output_layer : sauvegarde ou non du résultat final en une couche vectorielle, par défaut ''
        save_intermediate_results : sauvegarde ou non des tables intermédiaires
        debug : niveau de debug pour l'affichage des commentaires. Par défaut : 0

    Sortie :
        tab_herbace : nom de la table contenant les éléments de la strate herbace classés horizontalement
    """
    ####################################################
    ## Préparation de la couche herbacée de référence ## 
    ####################################################

    #1# Récupération de la table composée uniquement des segments herbaces
    tab_herb_ini = 'herbace_ini'
    query = """
    CREATE TABLE %s AS
        SELECT *
        FROM %s
        WHERE strate = 'herbace';
    """ %(tab_herb_ini, tab_ref)

    #Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    #Création des indexes 
    addSpatialIndex(connexion, tab_herb_ini)
    addIndex(connexion, tab_herb_ini, 'fid', 'idx_fid_herbeini')

    #2# Regroupement et lissage des segments herbacés
    tab_out = 'herbace'

    query = """
    CREATE TABLE %s AS
        SELECT public.ST_CHAIKINSMOOTHING((public.ST_DUMP(public.ST_MULTI(public.ST_UNION(t.geom)))).geom) AS geom
        FROM %s AS t;
    """ %(tab_out, tab_herb_ini)

    #Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    #Création d'un identifiant unique
    addUniqId(connexion, tab_out)

    #Création d'un index spatial
    addSpatialIndex(connexion, tab_out)

    #Création de la colonne strate qui correspond à 'arbore' pour tous les polygones et complétion
    addColumn(connexion, tab_out, 'strate', 'varchar(100)')

    query = """
    UPDATE %s SET strate = 'herbace' WHERE fid = fid;
    """ %(tab_out)

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    #Création de la colonne fv
    addColumn(connexion, tab_out, 'fv', 'varchar(100)')

    #Pas de complétion de cet attribut pour l'instant
    tab_herbace = ''

    if tab_herbace == '':
        tab_herbace = 'herbace'

    # SUPPRESSION DES TABLES QUI NE SONT PLUS UTILES ##
    if not save_intermediate_results :
        dropTable(connexion, tab_herb_ini)

    ## SAUVEGARDE DU RESULTAT EN UNE COUCHE VECTEUR
    if output_layer == '' :
        print(yellow + "Attention : Il n'y a pas de sauvegarde en couche vecteur du résultat de classification des FV herbacées. Vous n'avez pas fournit de chemin de sauvegarde." + endC)
    else:
        exportVectorByOgr2ogr(connexion_fv_dic["dbname"], output_layer, tab_herbace, user_name = connexion_fv_dic["user_db"], password = connexion_fv_dic["password_db"], ip_host = connexion_fv_dic["server_db"], num_port = connexion_fv_dic["port_number"], schema_name = connexion_fv_dic["schema"], format_type='GPKG')

    return tab_herbace  

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

    #Création et implémentation de l'indicateur de compacité (id_comp)
    query = """
    ALTER TABLE %s ADD id_comp float;

    UPDATE %s AS t SET id_comp = (4*PI()*public.ST_AREA(public.ST_BUFFER(t.geom,%s)))/(public.ST_PERIMETER(public.ST_BUFFER(t.geom,%s))*public.ST_PERIMETER(public.ST_BUFFER(t.geom,%s))) WHERE t.fid = t.fid AND public.ST_PERIMETER(public.ST_BUFFER(t.geom,%s)) <> 0;
    """ %(tab_ref, tab_ref, buffer_value, buffer_value, buffer_value, buffer_value)

    #Exécution de la requête SQL
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

    #Création et implémentation de l'indicateur de convexité (id_conv)
    query = """
    ALTER TABLE %s ADD id_conv float;

    UPDATE %s SET id_conv = (public.ST_AREA(geom)/public.ST_AREA(public.ST_ORIENTEDENVELOPE(geom)))
                        WHERE fid = fid AND public.ST_AREA(public.ST_ORIENTEDENVELOPE(geom)) <> 0;
    """ %(tab_ref, tab_ref)

    #Exécution de la requête SQL
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








