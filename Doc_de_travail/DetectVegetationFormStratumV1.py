from Lib_postgis import *

#################################################
## Concaténation des trois tables pour obtenir ##
## une unique cartographie                     ##  
#################################################

def cartographyVegetation(connexion, connexion_dic, schem_tab_ref, dic_thresholds, output_layers, save_intermediate_results = False,  save_final_result = False):
    """
    Rôle : concatène les trois tables arboré, arbustive et herbacée en un unique 
           correspondant à la carotgraphie de la végétation

    Paramètres :
        connexion : connexion à la base donnée et au schéma correspondant
        connexion_dic : dictionnaire des paramètre de connexion
        schem_tab_ref : schema et nom de la tabel de référence des segments végétation classés en strates verticales
        dic_thresholds : dictionnaire des seuils à attribuer en fonction de la strate verticale
        output_layers : ditctionnaire des noms de fichier de sauvegarde
        save_final_result : choix de sauvegarde ou non du résultat final. Par défaut : False

    Sortie :
        nom de la table contenant tous 
    """ 
    #1# Formes végétales arborées
    tab_arbore = detectInTreeStratum(connexion, connexion_dic, schem_tab_ref, dic_thresholds["tree"], output_layers["tree"], save_intermediate_results = save_intermediate_results)

    #2# Formes végétales arbustives
    tab_arbustive = detectInShrubStratum(connexion, connexion_dic, schem_tab_ref, dic_thresholds["shrub"], output_layers["schrub"], save_intermediate_results = save_intermediate_results)
    
    #3# Formes végétales herbacées
    tab_herbace = detectInHerbaceousStratum(connexion, connexion_dic, schem_tab_ref, output_layers["herbaceous"], save_intermediate_results = save_intermediate_results)

    #4# Concaténation des données en une seule table 'végétation'
    tab_name = 'vegetation'
    query = """
    CREATE TABLE %s AS
    SELECT fid, geom, strate, fv FROM %s
    UNION
    SELECT fid, geom, strate, fv FROM %s
    UNION 
    SELECT fid, geom, strate, fv FROM %s
    """ %(tab_name, tab_arbore, tab_arbustive, tab_herbace)
    
    executeQuery(connexion, query)

    if save_final_result:
        if output_layers["output_fv"] == '':
           #envoyer un message qu'il n'y aura pas de sauvegarde du résultat final puisque le chemin de sauvegarde n'est pas fournit 
        exportVectorByOgr2ogr(connexion_dic["dbname"], output_layers["output_fv"], tab_name, user_name = connexion_dic["user_db"], password = connexion_dic["password_db"], ip_host = connexion_dic["server_db"], num_port = connexion_dic["port_number"], schema_name = connexion_dic["schema"], format_type='GPKG')

    return tab_name



################################################
## Classification des FV de la strate arborée ## 
################################################

###########################################################################################################################################
# FONCTION detectInTreeStratum()                                                                                                          #
###########################################################################################################################################
def detectInTreeStratum(connexion, connexion_dic, schem_tab_ref, thresholds = 0, output_layer = '', save_intermediate_results = False):
    """
    Rôle : détecté les formes végétales horizontales au sein de la strate arborée

    Paramètres :
        connexion : connexion à la base donnée et au schéma correspondant
        connexion_dic : dictionnaire contenant les paramètres de connexion (pour la sauvegarde en fin de fonction)
        schem_tab_ref : schema.nom de la table correspondant aux segments de végétation 
        thresholds : dictionnaire des seuils à appliquer, par défaut : {"seuil_surface" : 0, "seuil_compacite_1" : 0, "seuil_compacite_2" : 0, "seuil_convexite" : 0, "seuil_elongation" : 0, "val_largeur_max_alignement" : 0, "val_buffer" : 0}
        output_layer : sauvegarde du résultat final en une couche vectorielle, par défaut ''
        save_intermediate_results : sauvegarde ou non des tables intermédiaires

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
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    #Création des indexes 
    addSpatialIndex(connexion, tab_arb_ini)
    addIndex(connexion, tab_arb_ini, 'fid', 'idx_fid_arboreini')

    #2# Regroupement et lissage des segments arborés
    tab_arb = 'arbore'

    query = """
    CREATE TABLE %s AS
        SELECT public.ST_CHAIKINSMOOTHING((public.ST_DUMP(public.ST_MULTI(public.ST_UNION(arbore_ini.geom)))).geom) AS geom
        FROM %s;
    """ %(tab_arb, tab_arb_ini)

    #Exécution de la requête SQL
    if debug >= 1:
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
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    #Création de la colonne fv
    addColumn(connexion, tab_arb, 'fv', 'varchar(100)')

    #Création et calcul de l'indicateur de forme : compacité
    createCompactnessIndicator(connexion, tab_arb, thresholds["val_buffer"])

    #3# Classement des segments en "arbre isole", "tache arboree" et "regroupement arbore"
    # basé sur un critère de surface et de seuil sur l'indice de compacité
    fst_class = firstClassification(connexion, tab_arb,  thresholds, 'arbore')
    
    #4# Travaux sur les "regroupements arborés"
    sec_class = secClassification(connexion, tab_arb, 'rgpt_arbore', thresholds)

    #5# Regroupement de l'ensemble des entités de la strate arborée en une seule couche
    tab_arbore = createLayerTree(connexion, fst_class, sec_class)

    if tab_arbore == '':
        tab_arbore = 'strate_arboree'

    # SUPPRESSION DES TABLES QUI NE SONT PLUS UTILES ##
    if not save_intermediate_results :
        dropTable(connexion, tab_arb_ini)
        dropTable(connexion, fst_class)
        dropTable(connexion, sec_class)

    ## SAUVEGARDE DU RESULTAT EN UNE COUCHE VECTEUR
    if save_results_as_layer :
       exportVectorByOgr2ogr(connexion_dic["dbname"], output_layer, tab_arbore, user_name = connexion_dic["user_db"], password = connexion_dic["password_db"], ip_host = connexion_dic["server_db"], num_port = connexion_dic["port_number"], schema_name = connexion_dic["schema"], format_type='GPKG')

    return tab_arbore




###########################################################################################################################################
# FONCTION getCoordRectEnglValue()                                                                                                        #
###########################################################################################################################################
def getCoordRectEnglValue(connexion, tab_ref, attributname = 'x0'):
    """
    Rôle : récupère et créé les coordonnées des 4 sommet du rectangle englobant

    Paramètres :
        connexion : connexion à la base donnée et au schéma correspondant
        tab_ref : nom de la table correspondant aux segments de végétation
        attributname : nom de l'attribut créé, par défaut : 'x0'
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
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    return


###########################################################################################################################################
# FONCTION firstClassification()                                                                                                          #
###########################################################################################################################################
def firstClassification(connexion, tab_ref, thresholds, typeclass = 'arbore'):
    """
    Rôle : classification en trois classes basée sur un critère de surface et de compacité

    Paramètres :
        connexion : connexion à la base donnée et au schéma correspondant
        tab_ref : nom de la table dans laquelle on calcule l'indicateur de compacité
        thresholds : dictionnaire des seuils de classification des formes végétales arborées
        typeclass : type de classification : 'arbore' ou 'arbustif', par défaut : 'arbore'

    Sortie :
        tab_out : nom de la table en sortie (qui est tab_ref du paramètre)
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
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    return tab_ref

###########################################################################################################################################
# FONCTION secClassification()                                                                                                          #
###########################################################################################################################################
def secClassification(connexion, tab_ref, tab_out, thresholds):
    """
    Rôle : détection et classification du reste des polygones classés "regroupement" lors de la première classification

    Paramètres :
        connexion : connexion à la base donnée et au schéma correspondant
        tab_ref : nom de la table correspondant aux segments de végétation
        tab_out : nom de la table contenant les polygones re-classés initialement labellisés "regroupement arboré" lors de la firstClassification()
        thresholds : dictionnaire des seuil à appliquer

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
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    ## PREPARATION DES DONNEES ##

    #Création d'un identifiant unique
    addUniqId(connexion, tab_out)

    #Création d'un index spatial
    addSpatialIndex(connexion, tab_out)

    #Ajout de l'attribut fv
    addColumn(connexion,tab_out, 'fv', 'varchar(100)')

    #Suppression des polygones trop petits (artefacts)
    query = """
    DELETE FROM %s AS t WHERE public.ST_AREA(t.geom) <= 1;
    """ %(tab_out)

    #Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    #Création et calcul de l'indicateur de convexité
    createConvexityIndicator(connexion, tab_out)

    #Création et calcul de l'indicateur de compacité
    createCompactnessIndicator(connexion, tab_out, thresholds["val_buffer"])

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
    UPDATE %s as rgt SET fv='%s'
    WHERE  rgt.id_conv >= %s AND rgt.id_elong  >= %s;
    """ %(tab_out, name_algt, thresholds["seuil_convexite"], thresholds["seuil_elongation"])

    query += """
    UPDATE %s as rgt SET fv='%s'
    WHERE rgt.id_conv >= %s AND rgt.id_elong < %s;
    """ %(tab_out, name_bst, thresholds["seuil_convexite"], thresholds["seuil_elongation"])

    query += """
    UPDATE %s as rgt SET fv='%s'
    WHERE rgt.id_conv < %s AND rgt.id_comp < %s;
    """ %(tab_out, name_algt, thresholds["seuil_convexite"], thresholds["seuil_compacite_2"])

    query += """
    UPDATE %s as rgt SET fv='%s'
    WHERE rgt.id_conv < %s AND rgt.id_comp >= %s;
    """ %(tab_out, name_bst, thresholds["seuil_convexite"], thresholds["seuil_compacite_2"])

    # Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    return tab_out



###########################################################################################################################################
# FONCTION classTreeWoodStrict()                                                                                                          #
###########################################################################################################################################
def createLayerTree(connexion, tab_firstclass, tab_secclass):
    """
    Rôle :

    Paramètres :
        connexion :
        tab_firstclass : table en sortie de la première classification
        tab_secclass : table en sortie de la dernière classification concernant les éléments de regroupements arborés

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
    if debug >= 1:
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
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    return 'strate_arboree'




##################################################
## Classification des FV de la strate arbustive ## 
##################################################

###########################################################################################################################################
# FONCTION detectInShrubStratum()                                                                                                         #
###########################################################################################################################################
def detectInShrubStratum(connexion, connexion_dic, schem_tab_ref, dic_thresholds, output_layer = '', save_intermediate_results = False):
    """
    Rôle : détecté les formes végétales horizontales au sein de la strate arbustive

    Paramètres :
        connexion : connexion à la base donnée et au schéma correspondant
        connexion_dic : dictionnaire contenant les paramètres de connexion (pour la sauvegarde en fin de fonction)
        schem_tab_ref : schema.nom de la table
        dic_thresholds : dictionnaire des seuils à appliquer, par défaut : {"seuil_surface" : 0, "seuil_compacite_1" : 0, "seuil_compacite_2" : 0, "seuil_convexite" : 0, "seuil_elongation" : 0, "val_largeur_max_alignement" : 0, "val_buffer" : 0}
        output_layer : sauvegarde ou non du résultat final en une couche vectorielle, par défaut ''
        save_intermediate_results : sauvegarde ou non des tables intermédiaires

    Sortie :
        tab_arbustive : nom de la table contenant les éléments de la strate arbustive classés horizontalement
    """

    # #0# Attribution de valeurs par défaut pour la connexion
    # if thresholds == 0:
    #     thresholds = {"seuil_surface" : 30, "seuil_compacite_1" : 0.7, "seuil_compacite_2" : 0.7, "seuil_convexite" : 0.7, "seuil_elongation" : 2.5, "val_largeur_max_alignement" : 7, "val_buffer" : 2}

    # print(cyan + "findImagesFile : Fin de la recherche dans le repertoire des images contenues ou intersectant l'emprise" + endC)

    # #1# Récupération de la table composée uniquement des segments arbustifs
    # query = """
    # CREATE TABLE arbustif_ini AS
    #     SELECT *
    #     FROM %s
    #     WHERE strate = 'arbustif';
    # """ %(tab_ref)

    # #Exécution de la requête SQL
    # if debug >= 1:
    #     print(query)
    # executeQuery(connexion, query)

    # addSpatialIndex(connexion, 'arbustif_ini')
    # addIndex(connexion, 'arbustif_ini', 'fid', 'idx_fid_arbustifini')

    # #2# Regroupement et lissage des segments arbustifs
    # query = """
    # CREATE TABLE arbustif AS
    #     SELECT public.ST_CHAIKINSMOOTHING((public.ST_DUMP(public.ST_MULTI(public.ST_UNION(arbustif_ini.geom)))).geom) AS geom
    #     FROM arbustif_ini;
    # """

    # # #Exécution de la requête SQL
    # if debug >= 1:
    #     print(query)
    # executeQuery(connexion, query)

    # # #Création d'un identifiant unique
    # addUniqId(connexion, 'arbustif')

    # # #Création d'un index spatial
    # addSpatialIndex(connexion, 'arbustif')

    # # #Création de la colonne strate qui correspond à 'arbustif' pour tous les polygones
    # addColumn(connexion, 'arbustif', 'strate', 'varchar(100)')

    # #Ajout de la valeur 'arbore' pour toutes les entités de la table arbore
    # query = """
    # UPDATE arbustif SET strate = 'arbustif' WHERE fid = fid;
    # """ 
    
    # executeQuery(connexion, query)

    # # #Création de la colonne fv
    # addColumn(connexion, 'arbustif', 'fv', 'varchar(100)')

    # # #Création et calcul de l'indicateur de forme : compacité
    # createCompactnessIndicator(connexion, 'arbustif', thresholds['val_buffer'])

    #3# Classement des segments en "arbuste isole", "tache arbustive" et "regroupement arbustif"
       # basé sur un critère de surface et de seuil sur l'indice de compacité
   # fst_class = firstClassification(connexion, 'arbustif', thresholds["seuil_compacite_1"], thresholds["seuil_surface"],  'arbustif')
    fst_class = 'arbustif'
    #4# Travaux sur les "regroupements arborés"
   # sec_class = secClassification(connexion, 'arbustif','rgpt_arbustif', thresholds["seuil_convexite"], thresholds["seuil_elongation"], thresholds["seuil_surface"], thresholds["seuil_compacite_1"], thresholds["seuil_compacite_2"], thresholds["val_buffer"])
    sec_class = 'rgpt_arbustif'
    #5# Regroupement de l'ensemble des entités de la strate arborée en une seule couche
    tab_arbustive = ''
    tab_arbustive = createLayerShrub(connexion, fst_class, sec_class)

    if tab_arbustive == '':
        tab_arbustive = 'strate_arbustive'

    ## SUPPRESSION DES TABLES QUI NE SONT PLUS UTILES ##
    if not save_intermediate_results :
        dropTable(connexion, 'arbustif_ini')
        dropTable(connexion, fst_class)
        dropTable(connexion, sec_class)

    # SAUVEGARDE DU RESULTAT EN UNE COUCHE VECTEUR
    if save_results_as_layer :
        exportVectorByOgr2ogr(connexion_fv_dic["dbname"], output_shrub_layer, tab_arbustive, user_name = connexion_fv_dic["user_db"], password = connexion_fv_dic["password_db"], ip_host = connexion_fv_dic["server_db"], num_port = connexion_fv_dic["port_number"], schema_name = connexion_fv_dic["schema"], format_type='GPKG')

    closeConnection(connexion)
    
    return tab_arbustive


###########################################################################################################################################
# FONCTION createLayerShrub()                                                                                                             #
###########################################################################################################################################
def createLayerShrub(connexion, tab_firstclass, tab_secclass):
    """
    Rôle :

    Paramètres :
        connexion :
        tab_firstclass : table en sortie de la première classification
        tab_secclass : table en sortie de la seconde classification concernant les éléments de regroupements arbustifs

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
    if debug >= 1:
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
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    return 'strate_arbustive'


##################################################
## Classification des FV de la strate herbacée  ## 
##################################################

###########################################################################################################################################
# FONCTION detectInHerbaceousStratum()                                                                                                    #
###########################################################################################################################################
def detectInHerbaceousStratum(connexion, connexion_dic, schem_tab_ref, output_layer, save_intermediate_results = False):
    """
    Rôle : détecté les formes végétales horizontales au sein de la strate arborée

    Paramètres :
        connexion : connexion à la base donnée et au schéma correspondant
        tab_ref : nom de la table correspondant aux segments de végétation (inclure le nom du schema si la table appartient à un autre schema)
        output_herbe_layer : couche vectorielle de sortie composée de la strate herbacée classée en strate verticale ET horizontale
        connexion_fv_dic : dictionnaire contenant les paramètres de connexion (pour la sauvegarde en fin de fonction)
        save_result_as_layer : sauvegarde ou non du résultat final en une couche vectorielle, par défaut False
        save_intermediate_results : sauvegarde ou non des tables intermédiaires

    Sortie :
        tab_herbace : nom de la table contenant les éléments de la strate herbace classés horizontalement
    """
    ####################################################
    ## Préparation de la couche herbacée de référence ## 
    ####################################################

    #1# Récupération de la table composée uniquement des segments herbaces
    query = """
    CREATE TABLE herbace_ini AS
        SELECT *
        FROM %s
        WHERE strate = 'herbace';
    """ %(tab_ref)

    #Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    #Création des indexes 
    addSpatialIndex(connexion, 'herbace_ini')
    addIndex(connexion, 'herbace_ini', 'fid', 'idx_fid_herbeini')

    #2# Regroupement et lissage des segments herbacés
    tab_out = 'herbace'
    query = """
    CREATE TABLE %s AS
        SELECT public.ST_CHAIKINSMOOTHING((public.ST_DUMP(public.ST_MULTI(public.ST_UNION(herbace_ini.geom)))).geom) AS geom
        FROM herbace_ini;
    """ %(tab_out)

    #Exécution de la requête SQL
    if debug >= 1:
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
    executeQuery(connexion, query)

    #Création de la colonne fv
    addColumn(connexion, tab_out, 'fv', 'varchar(100)')

    #Pas de complétion de cet attribut pour l'instant
    tab_herbace = ''

    if tab_herbace == '':
        tab_herbace = 'herbace'

    # SUPPRESSION DES TABLES QUI NE SONT PLUS UTILES ##
    if not save_intermediate_results :
        dropTable(connexion, 'herbace_ini')

    ## SAUVEGARDE DU RESULTAT EN UNE COUCHE VECTEUR
    if save_results_as_layer :
       exportVectorByOgr2ogr(connexion_fv_dic["dbname"], output_herbe_layer, tab_herbace, user_name = connexion_fv_dic["user_db"], password = connexion_fv_dic["password_db"], ip_host = connexion_fv_dic["server_db"], num_port = connexion_fv_dic["port_number"], schema_name = connexion_fv_dic["schema"], format_type='GPKG')

    closeConnection(connexion)

    return tab_herbace  

#####################################
## Fonctions indicateurs de formes ## 
#####################################

########################################################################
# FONCTION createCompactnessIndicator()                                #
########################################################################
def createCompactnessIndicator(connexion, tab_ref, buffer_value):
    """
    Rôle : créé et calcul un indice de compacité sur une forme pouvant être dilatée ou erodée

    Paramètres :
        connexion : connexion à la base donnée et au schéma correspondant
        tab_ref : nom de la table dans laquelle on calcule l'indicateur de compacité
        buffer_value : valeur attribuée à la bufferisation

    Sortie :
        nom de la colonne créé
    """

    #Création et implémentation de l'indicateur de compacité (id_comp)
    query = """
    ALTER TABLE %s ADD id_comp float;

    UPDATE %s AS t SET id_comp = (4*PI()*public.ST_AREA(public.ST_BUFFER(t.geom,%s)))/(public.ST_PERIMETER(public.ST_BUFFER(t.geom,%s))*public.ST_PERIMETER(public.ST_BUFFER(t.geom,%s))) WHERE t.fid = t.fid AND public.ST_PERIMETER(public.ST_BUFFER(t.geom,%s)) <> 0;
    """ %(tab_ref, tab_ref, buffer_value, buffer_value, buffer_value, buffer_value)

    #Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    return

########################################################################
# FONCTION createConvexityIndicator()                                  #
########################################################################
def createConvexityIndicator(connexion, tab_ref):
    """
    Rôle : créé et calcul un indice de convexité sur une forme pouvant être dilatée ou erodée

    Paramètres :
        connexion : connexion à la base donnée et au schéma correspondant
        tab_ref : nom de la table dans laquelle on calcule l'indicateur de compacité
    """

    #Création et implémentation de l'indicateur de convexité (id_conv)
    query = """
    ALTER TABLE %s ADD id_conv float;

    UPDATE %s SET id_conv = (public.ST_AREA(geom)/public.ST_AREA(public.ST_ORIENTEDENVELOPE(geom)))
                        WHERE fid = fid AND public.ST_AREA(public.ST_ORIENTEDENVELOPE(geom)) <> 0;
    """ %(tab_ref, tab_ref)

    #Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    return


########################################################################
# FONCTION createExtensionIndicator()                                  #
########################################################################
def createExtensionIndicator(connexion, tab_ref):
    """
    Rôle : créé et calcul un indice d'élongation sur une forme pouvant être dilatée ou erodée

    Paramètres :
        connexion : connexion à la base donnée et au schéma correspondant
        tab_ref : nom de la table dans laquelle on calcule l'indicateur de compacité
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
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    # Création et implémentation de l'indicateur de convexité (id_conv)
    addColumn(connexion, tab_ref, 'id_elong', 'float')

    query = """
    UPDATE %s AS t SET id_elong = (t.longueur/t.largeur)
                        WHERE t.fid = t.fid AND t.largeur <> 0;
    """ %(tab_ref)

    # Exécution de la requête SQL
    if debug >= 1:
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








