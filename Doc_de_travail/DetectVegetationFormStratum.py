from Lib_postgis import *

def createCompactnessIndicator(connexion, tablename, buffer_value):
    """
    Rôle : créé et calcul un indice de compacité sur une forme pouvant être dilatée ou erodée

    Paramètres :
        connexion : connexion à la base donnée et au schéma correspondant
        tablename : nom de la table dans laquelle on calcule l'indicateur de compacité
        buffer_value : valeur attribuée à la bufferisation

    Sortie :
        nom de la colonne créé
    """

    #Création et implémentation de l'indicateur de compacité (id_comp)
    query = """
    ALTER TABLE %s ADD id_comp float;

    UPDATE %s AS t SET id_comp = (4*PI()*public.ST_AREA(public.ST_BUFFER(t.geom,%s)))/(public.ST_PERIMETER(public.ST_BUFFER(t.geom,%s))*public.ST_PERIMETER(public.ST_BUFFER(t.geom,%s))) WHERE t.fid = t.fid AND public.ST_PERIMETER(public.ST_BUFFER(t.geom,%s)) <> 0;
    """ %(tablename, tablename, buffer_value, buffer_value, buffer_value, buffer_value)

    #Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    return

def createConvexityIndicator(connexion, tablename):
    """
    Rôle : créé et calcul un indice de convexité sur une forme pouvant être dilatée ou erodée

    Paramètres :
        connexion : connexion à la base donnée et au schéma correspondant
        tablename : nom de la table dans laquelle on calcule l'indicateur de compacité
    """

    #Création et implémentation de l'indicateur de convexité (id_conv)
    query = """
    ALTER TABLE %s ADD id_conv float;

    UPDATE %s SET id_conv = (public.ST_AREA(geom)/public.ST_AREA(public.ST_ORIENTEDENVELOPE(geom)))
                        WHERE fid = fid AND public.ST_AREA(public.ST_ORIENTEDENVELOPE(geom)) <> 0;
    """ %(tablename, tablename)

    #Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    return


def createExtensionIndicator(connexion, tablename):
    """
    Rôle : créé et calcul un indice d'élongation sur une forme pouvant être dilatée ou erodée

    Paramètres :
        connexion : connexion à la base donnée et au schéma correspondant
        tablename : nom de la table dans laquelle on calcule l'indicateur de compacité
    """

    # Calcul des valeurs de longueur et de largeur des rectangles orientés englobant minimaux des polygones
    addColumn(connexion, tablename, 'x0', 'float')
    addColumn(connexion, tablename, 'y0', 'float')
    addColumn(connexion, tablename, 'x1', 'float')
    addColumn(connexion, tablename, 'y1', 'float')
    addColumn(connexion, tablename, 'x3', 'float')
    addColumn(connexion, tablename, 'y3', 'float')

    getCoordRectEnglValue(connexion, tablename, 'x0')
    getCoordRectEnglValue(connexion, tablename, 'x1')
    getCoordRectEnglValue(connexion, tablename, 'x3')
    getCoordRectEnglValue(connexion, tablename, 'y0')
    getCoordRectEnglValue(connexion, tablename, 'y1')
    getCoordRectEnglValue(connexion, tablename, 'y3')

    addColumn(connexion, tablename, 'largeur', 'float')
    addColumn(connexion, tablename, 'longueur', 'float')

    # Calcul des attributs de largeur et longueur du rectangle englobant orienté
    query = """
    UPDATE %s SET largeur= LEAST(sqrt((x1-x0)^2+(y1-y0)^2), sqrt((x3-x0)^2+(y3-y0)^2)) WHERE fid = fid;
    """ %(tablename)

    query += """
    UPDATE %s SET longueur= GREATEST(sqrt((x1-x0)^2+(y1-y0)^2), sqrt((x3-x0)^2+(y3-y0)^2)) WHERE fid = fid;
    """ %(tablename)

    # Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    # Création et implémentation de l'indicateur de convexité (id_conv)
    addColumn(connexion, tablename, 'id_elong', 'float')

    query = """
    UPDATE %s AS t SET id_elong = (t.longueur/t.largeur)
                        WHERE t.fid = t.fid AND t.largeur <> 0;
    """ %(tablename)

    # Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    # Suppression des attributs qui ne sont plus utiles
    dropColumn(connexion, tablename, 'x0')
    dropColumn(connexion, tablename, 'x1')
    dropColumn(connexion, tablename, 'x3')
    dropColumn(connexion, tablename, 'y0')
    dropColumn(connexion, tablename, 'y1')
    dropColumn(connexion, tablename, 'y3')
    dropColumn(connexion, tablename, 'largeur')
    dropColumn(connexion, tablename, 'longueur')

    return

def addUniqId(connexion, tablename):
    """
    Rôle : créé un identifiant unique fid généré automatiquement

    Paramètres :
        connexion : connexion à la base donnée et au schéma correspondant
        tablename : nom de la table correspondant aux segments de végétation
    """

    query = """
    ALTER TABLE %s ADD COLUMN fid SERIAL PRIMARY KEY;
    """ %(tablename)

    #Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    return

def addSpatialIndex(connexion, tablename, geomcolumn = 'geom'):
    """
    Rôle : créé un index spatial associé à la colonne géometrie

    Paramètres :
        connexion : connexion à la base donnée et au schéma correspondant
        tablename : nom de la table correspondant aux segments de végétation
        geomcolumn : nom de la colonne géometrie, par défaut : 'geom'
    """

    nameindex = 'idx_gist_' + tablename
    query = """
    CREATE INDEX %s ON %s USING gist(%s);
    """ %(nameindex, tablename, geomcolumn)

    #Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    return

def addColumn(connexion, tablename, columnname, columntype):
    """
    Rôle : créé un attribut d'une table dans la db

    Paramètres :
        connexion : connexion à la base donnée et au schéma correspondant
        tablename : nom de la table correspondant aux segments de végétation
        attributname : nom de l'attribut ajouté
        columntype : type de l'attribut ex : float, varchar, int, etc ...
    """

    query = """
    ALTER TABLE %s ADD COLUMN %s %s;
    """ %(tablename, columnname, columntype)

    #Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    return

def dropColumn(connexion, tablename, columnname):
    """
    Rôle : supprime une colonne d'une table

    Paramètres :
        connexion : connexion à la base donnée et au schéma correspondant
        tablename : nom de la table correspondant aux segments de végétation
        columnname : nom de la colonne à supprimer
    """

    query = """
    ALTER TABLE %s DROP COLUMN IF EXISTS %s;
    """ %(tablename, columnname)

    # Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    return

def getCoordRectEnglValue(connexion, tablename, attributname = 'x0'):
    """
    Rôle : récupère et créé les coordonnées des 4 sommet du rectangle englobant

    Paramètres :
        connexion : connexion à la base donnée et au schéma correspondant
        tablename : nom de la table correspondant aux segments de végétation
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
    UPDATE %s SET %s = cast(split_part(split_part(substring(left(public.st_astext(public.st_orientedenvelope(geom)),-2),10),',',%s),' ',%s) as DECIMAL) WHERE fid = fid;
    """ %(tablename, attributname, l[0], l[1])

    # Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    return

def firstClassification(connexion, tablename, compacthreshold = 0.7, areathreshold = 30, typeclass = 'arbore'):
    """
    Rôle : classification en trois classes basée sur un critère de surface et de compacité

    Paramètres :
        connexion : connexion à la base donnée et au schéma correspondant
        tablename : nom de la table dans laquelle on calcule l'indicateur de compacité
        compacthreshold : valeur du seuil de compacité, par défaut : 0.7
        areathreshold : valeur du seuil de surface, par défaut : 30
        typeclass : type de classification : 'arbore' ou 'arbustif', par défaut : 'arbore'
    """

    if typeclass == 'arbore':
        query = """
        UPDATE %s AS arb SET fv = 'arbre isole' WHERE public.ST_AREA(arb.geom) <= %s AND arb.id_comp > %s;
        """ %(tablename, areathreshold, compacthreshold)

        query += """
        UPDATE %s AS arb SET fv = 'tache arboree' WHERE public.ST_AREA(arb.geom) <= %s AND arb.id_comp <= %s;
        """ %(tablename, areathreshold, compacthreshold)

        query += """
        UPDATE %s AS arb SET fv = 'regroupement arbore' WHERE public.ST_AREA(arb.geom) > %s;
        """ %(tablename, areathreshold)
    else :
        query = """
        UPDATE %s AS arb SET fv = 'arbuste isole' WHERE public.ST_AREA(geom) <= %s AND id_comp > %s;
        """ %(tablename, areathreshold, compacthreshold)

        query += """
        UPDATE %s AS arb SET fv = 'tache arbustive' WHERE public.ST_AREA(geom) <= %s AND id_comp <= %s;
        """ %(tablename, areathreshold, compacthreshold)

        query += """
        UPDATE %s AS arb SET fv = 'regroupement arbustif' WHERE public.ST_AREA(geom) > %s;
        """ %(tablename, areathreshold)

    #Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    return

def classTreeWoodStrict(connexion, tablename, thresholdTreeLine):
    """
    Rôle : détection et classification des polygones de boisement arborés

    Paramètres :
        connexion : connexion à la base donnée et au schéma correspondant
        tablename : nom de la table correspondant aux segments de végétation
        thresholdTreeLine : valeur seuil de largeur d'un alignement d'arbres
    """

    query = """
    CREATE TABLE arbore_bststr AS
        SELECT public.ST_UNION(sgt_bst_strict.geom) AS geom
        FROM (SELECT geom
                FROM (SELECT public.ST_MAKEVALID((public.ST_DUMP(public.ST_DIFFERENCE(arb.geom, boisement.geom))).geom::public.geometry(Polygon,2154)) AS geom
                        FROM %s as arb, (SELECT public.ST_MAKEVALID((public.ST_DUMP(public.ST_BUFFER(public.ST_BUFFER(arb.geom,-%s),%s))).geom::public.geometry(Polygon,2154)) AS geom
                                        FROM %s as arb
                                        WHERE arb.fv='regroupement arbore') AS boisement
                        WHERE arb.fv = 'regroupement arbore' AND public.ST_INTERSECTS(arb.geom, boisement.geom)) AS arbre
                WHERE public.ST_AREA(arbre.geom)<200) AS sgt_bst_strict
        UNION
        SELECT t.geom
            FROM (SELECT public.ST_MakeValid((public.ST_DUMP(public.ST_BUFFER(public.ST_BUFFER(arb.geom,-%s),%s))).geom::public.geometry(Polygon,2154)) AS geom
                    FROM arbore as arb
                    WHERE arb.fv='regroupement arbore') AS t;
    """ %(tablename, thresholdTreeLine, thresholdTreeLine, tablename, thresholdTreeLine, thresholdTreeLine)

    #Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    #Création index spatial
    addSpatialIndex(connexion, 'arbore_bststr')

    #Création d'une table avec uniquement les boisements
    query = """
    CREATE TABLE arbore_bststr_uniq AS (SELECT public.ST_MAKEVALID((public.ST_DUMP(public.ST_UNION(geom))).geom::public.geometry(Polygon,2154)) AS geom FROM arbore_bststr);
    """

    #Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    #Création d'un identifiant unique
    addUniqId(connexion, 'arbore_bststr_uniq')

    #Création d'un index spatial
    addSpatialIndex(connexion, 'arbore_bststr_uniq')

    #Ajout de l'attribut fv
    addColumn(connexion, 'arbore_bststr_uniq', 'fv', 'varchar(100)')

    #Implémentation de la valeur unique 'boisement arbore' pour tous les polygones de végétation dont on est sûr que ce sont des boisements
    query = """
    UPDATE arbore_bststr_uniq SET fv='boisement arbore';
    """

    #Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    return

def lastTreeClassification(connexion, tablename, convexthreshold, extensiontreshold, areathreshold, compacthreshold, compacthreshold_V2, valbuffer):
    """
    Rôle : détection et classification du reste des polygones classés "regroupement arboré" lors de la première classification

    Paramètres :
        connexion : connexion à la base donnée et au schéma correspondant
        tablename : nom de la table correspondant aux segments de végétation
        convexthreshold : seuil à appliquer sur l'indice de convexité
        extensionthreshold : seuil à appliquer sur l'indice d'élongation
        areathreshold : seuil à appliquer sur la surface des polygones
        compacthreshold : version 1 du seuil à appliquer sur l'indice de compacité
        compacthreshold_V2 :version 2 du seuil à appliquer sur l'indice de compacité
        valbuffer : valeur du buffer appliqué sur la géométrie avant de calculer l'indice de commpacité

    """
    ## CREATION DE LA TABLE CONTENANT UNIQUEMENT LES ENTITES QUI NE SONT PAS DES BOISEMENTS STRICTES ##
    query = """
    CREATE TABLE rgpt_arbore AS
        SELECT public.ST_MAKEVALID((public.ST_DUMP(public.ST_DIFFERENCE(rgt.geom, ou.geom))).geom::public.geometry(Polygon, 2154)) AS geom
        FROM (SELECT public.ST_MAKEVALID(public.ST_UNION(geom)) as geom
                FROM %s
                WHERE fv = 'regroupement arbore') AS rgt, (SELECT public.ST_MAKEVALID(public.ST_UNION(geom)) as geom from donneelidar.arbore_bststr_uniq) as ou;
    """ %(tablename)

    #Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    tablename = 'rgpt_arbore'

    ## PREPARATION DES DONNEES ##

    #Création d'un identifiant unique
    addUniqId(connexion, 'rgpt_arbore')

    #Création d'un index spatial
    addSpatialIndex(connexion, 'rgpt_arbore')

    #Ajout de l'attribut fv
    addColumn(connexion, 'rgpt_arbore', 'fv', 'varchar(100)')

    #Suppression des polygones trop petits (artefacts)
    query = """
    DELETE FROM rgpt_arbore WHERE public.ST_AREA(rgpt_arbore.geom) <= 1;
    """
    #Exécution de la requête SQL
    if debug >= 1:
        print(query)
    #executeQuery(connexion, query)

    #Création et calcul de l'indicateur de convexité
    createConvexityIndicator(connexion, 'rgpt_arbore')

    #Création et calcul de l'indicateur de compacité
    createCompactnessIndicator(connexion, 'rgpt_arbore', valbuffer)

    #Création et calcul de l'indicateur d'élongation
    createExtensionIndicator(connexion, 'rgpt_arbore')

    ## CLASSIFICATION ##
    # si la surface est inférieure à 30, que ça ne touche pas un boisement stricte ET que son id_comp >= 0.7 --> arbre isole
    query = """
    UPDATE %s as rgt SET fv = 'arbre isole'
    FROM arbore_bststr_uniq
    WHERE  public.ST_AREA(rgt.geom) <= %s AND rgt.id_comp  >= %s AND public.ST_INTERSECTS(rgt.geom, arbore_bststr_uniq.geom) is false;
    """ %(tablename, areathreshold, compacthreshold)

    # si la surface est inférieure à 30, que ça ne touche pas un boisement stricte ET que son id_comp <0.7 --> tâche verte
    query += """
    UPDATE %s as rgt SET fv = 'tache arbore'
    FROM arbore_bststr_uniq
    WHERE  public.ST_AREA(rgt.geom) <= %s AND rgt.id_comp  < %s AND public.ST_INTERSECTS(rgt.geom, arbore_bststr_uniq.geom) is false;
    """ %(tablename, areathreshold, compacthreshold)

    # si la surface est inférieure à 30 et que ça touche un boisement stricte --> ça appartient au boisement
    query += """
    UPDATE %s as rgt SET fv = 'boisement arbore'
    FROM arbore_bststr_uniq
    WHERE public.ST_AREA(rgt.geom)<= %s AND public.ST_INTERSECTS(rgt.geom, arbore_bststr_uniq.geom);
    """ %(tablename, areathreshold)

    # si la surface est supérieure à 30
    # --> classification à partir d'indices de formes du reste des polygones appartennant aux regroupements
    query += """
    UPDATE %s as rgt SET fv='alignement arbore'
    WHERE  rgt.id_conv >= %s AND rgt.id_elong  >= %s AND public.ST_AREA(rgt.geom) > %s;
    """ %(tablename, convexthreshold, extensiontreshold, areathreshold)

    query += """
    UPDATE %s as rgt SET fv='boisement arbore'
    WHERE rgt.id_conv >= %s AND rgt.id_elong < %s AND public.ST_AREA(rgt.geom) > %s;
    """ %(tablename, convexthreshold, extensiontreshold, areathreshold)

    query += """
    UPDATE %s as rgt SET fv='alignement arbore'
    WHERE rgt.id_conv < %s AND rgt.id_comp < %s AND public.ST_AREA(rgt.geom) > %s;
    """ %(tablename, convexthreshold, compacthreshold_V2, areathreshold)

    query += """
    UPDATE %s as rgt SET fv='boisement arbore'
    WHERE rgt.id_conv < %s AND rgt.id_comp >= %s AND public.ST_AREA(rgt.geom) > %s;
    """ %(tablename, convexthreshold, compacthreshold_V2, areathreshold)

    # Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    return

def createLayerTree(connexion, tab_firstclass, tab_woodstrict, tab_lastclass):
    """
    Rôle :

    Paramètres :
        connexion :
        tab_firstclass : table en sortie de la première classification
        tab_woodstrict : table en sortie de l'extraction des boisements strictes arborés
        tab_lastclass : table en sortie de la dernière classification concernant les éléments de regroupements arborés
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
            FROM %s)
            UNION
           (SELECT geom, fv
            FROM %s)) AS strate_arboree
    WHERE public.ST_INTERSECTS(strate_arboree.geom, strate_arboree.geom)
    GROUP BY strate_arboree.fv;
    """ %(tab_firstclass, tab_woodstrict, tab_lastclass)

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



def detectInTreeStratum(connexion, tablename, output_tree_layer, connexion_fv_dic, thresholds = 0, save_results_as_layer = False, save_results_intermediate = False):
    """
    Rôle : détecté les formes végétales horizontales au sein de la
    strate arborée

    Paramètres :
        connexion : connexion à la base donnée et au schéma correspondant
        tablename : nom de la table correspondant aux segments de végétation
        output_tree_layer : couche vectorielle de sortie composée de la strate arborée classée en strate verticale ET horizontale
        connexion_fv_dic : dictionnaire contenant les paramètres de connexion (pour la sauvegarde en fin de fonction)
        thresholds : dictionnaire des seuils à appliquer, par défaut : {"seuil_surface" : 0, "seuil_compacite_1" : 0, "seuil_compacite_2" : 0, "seuil_convexite" : 0, "seuil_elongation" : 0, "val_largeur_max_alignement" : 0, "val_buffer" : 0}
        save_result_as_layer : sauvegarde ou non du résultat final en une couche vectorielle, par défaut False
        save_results_intermediate : sauvegarde ou non des tables intermédiaires

    Sortie :
        tablename : nom de la table contenant les éléments de la strate arborée classés horizontalement
    """
    #0# Attribution de valeurs par défaut pou
    if thresholds == 0:
        thresholds = {"seuil_surface" : 30, "seuil_compacite_1" : 0.7, "seuil_compacite_2" : 0.7, "seuil_convexite" : 0.7, "seuil_elongation" : 2.5, "val_largeur_max_alignement" : 7, "val_buffer" : 1}

    print(cyan + "findImagesFile : Fin de la recherche dans le repertoire des images contenues ou intersectant l'emprise" + endC)

    #1# Récupération de la table composée uniquement des segments arborés
    query = """
    CREATE TABLE arbore_ini AS
        SELECT *
        FROM %s
        WHERE strate = 'arbore';
    """ %(tablename)

    #Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    #2# Regroupement et lissage des segments arborés
    query = """
    CREATE TABLE arbore AS
        SELECT public.ST_CHAIKINSMOOTHING((public.ST_DUMP(public.ST_MULTI(public.ST_UNION(arbore_ini.geom)))).geom) AS geom
        FROM arbore_ini;
    """

    #Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    #Création d'un identifiant unique
    addUniqId(connexion, 'arbore')

    #Création d'un index spatial
    addSpatialIndex(connexion, 'arbore')

    #Création de la colonne strate qui correspond à 'arboree' pour tous les polygones
    addColumn(connexion, 'arbore', 'strate', 'varchar(100)')

    #Création de la colonne fv
    addColumn(connexion, 'arbore', 'fv', 'varchar(100)')

    #Création et calcul de l'indicateur de forme : compacité
    createCompactnessIndicator(connexion, 'arbore', thresholds["val_buffer"])

    #3# Classement des segments en "arbre isole", "tache arboree" et "regroupement arbore"
    #basé sur un critère de surface et de seuil sur l'indice de compacité
    firstClassification(connexion, 'arbore',  thresholds["seuil_compacite_1"], thresholds["seuil_surface"], 'arbore')

    #4# Travaux sur les "regroupements arborés"
    #Extraction des polygones correspondants aux boisements strictes ET tous les petits segments en contact avec les boisements strictes
    classTreeWoodStrict(connexion, 'arbore', thresholds["val_largeur_max_alignement"])

    #5# Travaux sur les autres polygones de regroupements arborés qui ne sont pas des boisements strictes
    lastTreeClassification(connexion, 'arbore', thresholds["seuil_convexite"], thresholds["seuil_elongation"], thresholds["seuil_surface"], thresholds["seuil_compacite_1"], thresholds["seuil_compacite_2"], thresholds["val_buffer"])

    #6# Regroupement de l'ensemble des entités de la strate arborée en une seule couche
    tablename = createLayerTree(connexion, 'arbore', 'arbore_bststr_uniq', 'rgpt_arbore')

    ## SUPPRESSION DES TABLES QUI NE SONT PLUS UTILES ##
    if not save_results_intermediate :
        dropTable(connexion, 'arbore_ini')
        dropTable(connexion, 'arbore')
        dropTable(connexion, 'arbore_bststr')
        dropTable(connexion, 'arbore_bststr_uniq')
        dropTable(connexion, 'rgpt_arbore')

    ## SAUVEGARDE DU RESULTAT EN UNE COUCHE VECTEUR
    if save_results_as_layer :
        exportVectorByOgr2ogr(connexion_fv_dic["dbname"], output_tree_layer, tablename, user_name = connexion_fv_dic["user_db"], password = connexion_fv_dic["password_db"], ip_host = connexion_fv_dic["server_db"], num_port = connexion_fv_dic["port_number"], schema_name = connexion_fv_dic["schema"], format_type='GPKG')

    return tablename



def classShrubWoodStrict(connexion, tablename, thresholdShrubLine):
    """
    Rôle : détection et classification des polygones de boisement arborés

    Paramètres :
        connexion : connexion à la base donnée et au schéma correspondant
        tablename : nom de la table correspondant aux segments de végétation
        thresholdShrubLine : valeur seuil de largeur d'un alignement d'arbres
    """

    query = """
    CREATE TABLE arbustif_bststr AS
        SELECT public.ST_UNION(sgt_bst_strict.geom) AS geom
        FROM (SELECT geom
                FROM (SELECT public.ST_MAKEVALID((public.ST_DUMP(public.ST_DIFFERENCE(arb.geom, boisement.geom))).geom::public.geometry(Polygon,2154)) AS geom
                        FROM %s as arb, (SELECT public.ST_MAKEVALID((public.ST_DUMP(public.ST_BUFFER(public.ST_BUFFER(arb.geom,-%s),%s))).geom::public.geometry(Polygon,2154)) AS geom
                                        FROM %s as arb
                                        WHERE arb.fv='regroupement arbustif') AS boisement
                        WHERE arb.fv = 'regroupement arbustif' AND public.ST_INTERSECTS(arb.geom, boisement.geom)) AS arbre
                WHERE public.ST_AREA(arbre.geom)<5) AS sgt_bst_strict
        UNION
        SELECT t.geom
            FROM (SELECT public.ST_MakeValid((public.ST_DUMP(public.ST_BUFFER(public.ST_BUFFER(arb.geom,-%s),%s))).geom::public.geometry(Polygon,2154)) AS geom
                    FROM %s as arb
                    WHERE arb.fv='regroupement arbustif') AS t;
    """ %(tablename, thresholdShrubLine, thresholdShrubLine, tablename, thresholdShrubLine, thresholdShrubLine, tablename)

    #Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    #Création index spatial
    addSpatialIndex(connexion, 'arbustif_bststr')

    #Création d'une table avec uniquement les boisements
    query = """
    CREATE TABLE arbustif_bststr_uniq AS (SELECT public.ST_MAKEVALID((public.ST_DUMP(public.ST_UNION(geom))).geom::public.geometry(Polygon,2154)) AS geom FROM arbustif_bststr);
    """

    #Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    #Création d'un identifiant unique
    addUniqId(connexion, 'arbustif_bststr_uniq')

    #Création d'un index spatial
    addSpatialIndex(connexion, 'arbustif_bststr_uniq')

    #Ajout de l'attribut fv
    addColumn(connexion, 'arbustif_bststr_uniq', 'fv', 'varchar(100)')

    #Implémentation de la valeur unique 'boisement arbore' pour tous les polygones de végétation dont on est sûr que ce sont des boisements
    query = """
    UPDATE arbustif_bststr_uniq SET fv='boisement arbustif';
    """

    #Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    return

def lastShrubClassification(connexion, tablename, convexthreshold, extensiontreshold, areathreshold, compacthreshold, compacthreshold_V2, valbuffer):
    """
    Rôle : détection et classification du reste des polygones classés "regroupement arbustif" lors de la première classification

    Paramètres :
        connexion : connexion à la base donnée et au schéma correspondant
        tablename : nom de la table correspondant aux segments de végétation
        convexthreshold : seuil à appliquer sur l'indice de convexité
        extensionthreshold : seuil à appliquer sur l'indice d'élongation
        areathreshold : seuil à appliquer sur la surface des polygones
        compacthreshold : version 1 du seuil à appliquer sur l'indice de compacité
        compacthreshold_V2 :version 2 du seuil à appliquer sur l'indice de compacité
        valbuffer : valeur du buffer appliqué sur la géométrie avant de calculer l'indice de commpacité


    """
    ## CREATION DE LA TABLE CONTENANT UNIQUEMENT LES ENTITES QUI NE SONT PAS DES BOISEMENTS STRICTES ##
    query = """
    CREATE TABLE rgpt_arbustif AS
        SELECT public.ST_MAKEVALID((public.ST_DUMP(public.ST_DIFFERENCE(rgt.geom, ou.geom))).geom::public.geometry(Polygon, 2154)) AS geom
        FROM (SELECT public.ST_MAKEVALID(public.ST_UNION(geom)) as geom
                FROM %s
                WHERE fv = 'regroupement arbustif') AS rgt, (SELECT public.ST_MAKEVALID(public.ST_UNION(geom)) as geom from arbustif_bststr_uniq) as ou;
    """ %(tablename)

    #Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    ## PREPARATION DES DONNEES ##

    #Création d'un identifiant unique
    addUniqId(connexion, 'rgpt_arbustif')

    #Création d'un index spatial
    addSpatialIndex(connexion, 'rgpt_arbustif')

    #Ajout de l'attribut fv
    addColumn(connexion, 'rgpt_arbustif', 'fv', 'varchar(100)')

    #Suppression des polygones trop petits (artefacts)
    query = """
    DELETE FROM rgpt_arbustif WHERE public.ST_AREA(rgpt_arbustif.geom) <= 1;
    """
    #Exécution de la requête SQL
    if debug >= 1:
        print(query)
    #executeQuery(connexion, query)

    #Création et calcul de l'indicateur de convexité
    createConvexityIndicator(connexion, 'rgpt_arbustif')

    #Création et calcul de l'indicateur de compacité
    createCompactnessIndicator(connexion, 'rgpt_arbustif', valbuffer)

    #Création et calcul de l'indicateur d'élongation
    createExtensionIndicator(connexion, 'rgpt_arbustif')

    tablename = 'rgpt_arbustif'

    ## CLASSIFICATION ##
    # si la surface est inférieure à 30, que ça ne touche pas un boisement stricte ET que son id_comp >= 0.7 --> arbuste isole
    query = """
    UPDATE %s as rgt SET fv = 'arbuste isole'
    FROM arbustif_bststr_uniq
    WHERE  public.ST_AREA(rgt.geom) <= %s AND rgt.id_comp  >= %s AND public.ST_INTERSECTS(rgt.geom, arbustif_bststr_uniq.geom) is false;
    """ %(tablename, areathreshold, compacthreshold)

    # si la surface est inférieure à 30, que ça ne touche pas un boisement stricte ET que son id_comp <0.7 --> tâche verte
    query += """
    UPDATE %s as rgt SET fv = 'tache arbustive'
    FROM arbustif_bststr_uniq
    WHERE  public.ST_AREA(rgt.geom) <= %s AND rgt.id_comp  < %s AND public.ST_INTERSECTS(rgt.geom, arbustif_bststr_uniq.geom) is false;
    """ %(tablename, areathreshold, compacthreshold)

    # si la surface est inférieure à 30 et que ça touche un boisement stricte --> ça appartient au boisement
    query += """
    UPDATE %s as rgt SET fv = 'boisement arbustif'
    FROM arbustif_bststr_uniq
    WHERE public.ST_AREA(rgt.geom)<= %s AND public.ST_INTERSECTS(rgt.geom, arbustif_bststr_uniq.geom);
    """ %(tablename, areathreshold)

    # si la surface est supérieure à 30
    # --> classification à partir d'indices de formes du reste des polygones appartennant aux regroupements
    query += """
    UPDATE %s as rgt SET fv='alignement arbustif'
    WHERE  rgt.id_conv >= %s AND rgt.id_elong  >= %s AND public.ST_AREA(rgt.geom) > %s;
    """ %(tablename, convexthreshold, extensiontreshold, areathreshold)

    query += """
    UPDATE %s as rgt SET fv='boisement arbustif'
    WHERE rgt.id_conv >= %s AND rgt.id_elong < %s AND public.ST_AREA(rgt.geom) > %s;
    """ %(tablename, convexthreshold, extensiontreshold, areathreshold)

    query += """
    UPDATE %s as rgt SET fv='alignement arbustif'
    WHERE rgt.id_conv < %s AND rgt.id_comp < %s AND public.ST_AREA(rgt.geom) > %s;
    """ %(tablename, convexthreshold, compacthreshold_V2, areathreshold)

    query += """
    UPDATE %s as rgt SET fv='boisement arbustif'
    WHERE rgt.id_conv < %s AND rgt.id_comp >= %s AND public.ST_AREA(rgt.geom) > %s;
    """ %(tablename, convexthreshold, compacthreshold_V2, areathreshold)

    # Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    return

def createLayerShrub(connexion, tab_firstclass, tab_woodstrict, tab_lastclass):
    """
    Rôle :

    Paramètres :
        connexion :
        tab_firstclass : table en sortie de la première classification
        tab_woodstrict : table en sortie de l'extraction des boisements strictes arbustifs
        tab_lastclass : table en sortie de la dernière classification concernant les éléments de regroupements arbustifs
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
            FROM %s)
            UNION
           (SELECT geom, fv
            FROM %s)) AS strate_arbustive
    WHERE public.ST_INTERSECTS(strate_arbustive.geom, strate_arbustive.geom)
    GROUP BY strate_arbustive.fv;
    """ %(tab_firstclass, tab_woodstrict, tab_lastclass)

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

def detectInShrubStratum(connexion, tablename, output_shrub_layer, connexion_fv_dic, thresholds = 0, save_results_as_layer = False, save_results_intermediate = False):
    """
    Rôle : détecté les formes végétales horizontales au sein de la
    strate arbustive

    Paramètres :
        connexion : connexion à la base donnée et au schéma correspondant
        tablename : nom de la table correspondant aux segments de végétation
        output_shrub_layer : couche vectorielle de sortie composée de la strate arbustive classée en strate verticale ET horizontale
        connexion_fv_dic : dictionnaire contenant les paramètres de connexion (pour la sauvegarde en fin de fonction)
        thresholds : dictionnaire des seuils à appliquer, par défaut : {"seuil_surface" : 0, "seuil_compacite_1" : 0, "seuil_compacite_2" : 0, "seuil_convexite" : 0, "seuil_elongation" : 0, "val_largeur_max_alignement" : 0, "val_buffer" : 0}
        save_result_as_layer : sauvegarde ou non du résultat final en une couche vectorielle, par défaut False
        save_results_intermediate : sauvegarde ou non des tables intermédiaires

    Sortie :
        tablename : nom de la table contenant les éléments de la strate arbustive classés horizontalement
    """

    #0# Attribution de valeurs par défaut pour la connexion
    if thresholds == 0:
        thresholds = {"seuil_surface" : 30, "seuil_compacite_1" : 0.7, "seuil_compacite_2" : 0.7, "seuil_convexite" : 0.7, "seuil_elongation" : 2.5, "val_largeur_max_alignement" : 7, "val_buffer" : 2}

    print(cyan + "findImagesFile : Fin de la recherche dans le repertoire des images contenues ou intersectant l'emprise" + endC)

    # #1# Récupération de la table composée uniquement des segments arbustifs
    query = """
    CREATE TABLE arbustif_ini AS
        SELECT *
        FROM %s
        WHERE strate = 'arbustif';
    """ %(tablename)

    #Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    #2# Regroupement et lissage des segments arbustifs
    query = """
    CREATE TABLE arbustif AS
        SELECT public.ST_CHAIKINSMOOTHING((public.ST_DUMP(public.ST_MULTI(public.ST_UNION(arbustif_ini.geom)))).geom) AS geom
        FROM arbustif_ini;
    """

    # #Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    # #Création d'un identifiant unique
    addUniqId(connexion, 'arbustif')

    # #Création d'un index spatial
    addSpatialIndex(connexion, 'arbustif')

    # #Création de la colonne strate qui correspond à 'arbustif' pour tous les polygones
    addColumn(connexion, 'arbustif', 'strate', 'varchar(100)')

    # #Création de la colonne fv
    addColumn(connexion, 'arbustif', 'fv', 'varchar(100)')

    # #Création et calcul de l'indicateur de forme : compacité
    createCompactnessIndicator(connexion, 'arbustif', thresholds['val_buffer'])

    # #3# Classement des segments en "arbuste isole", "tache arbustive" et "regroupement arbustif"
    # #basé sur un critère de surface et de seuil sur l'indice de compacité
    firstClassification(connexion, 'arbustif', thresholds["seuil_compacite_1"], thresholds["seuil_surface"],  'arbustif')

    # #4# Travaux sur les "regroupements arborés"
    # #Extraction des polygones correspondants aux boisements strictes ET tous les petits segments en contact avec les boisements strictes
    classShrubWoodStrict(connexion, 'arbustif', thresholds["val_largeur_max_alignement"])

    # #5# Travaux sur les autres polygones de regroupements arborés qui ne sont pas des boisements strictes
    lastShrubClassification(connexion, 'arbustif', thresholds["seuil_convexite"], thresholds["seuil_elongation"], thresholds["seuil_surface"], thresholds["seuil_compacite_1"], thresholds["seuil_compacite_2"], thresholds["val_buffer"])

    # #6# Regroupement de l'ensemble des entités de la strate arborée en une seule couche
    tablename = createLayerShrub(connexion, 'arbustif', 'arbustif_bststr_uniq', 'rgpt_arbustif')

    # ## SUPPRESSION DES TABLES QUI NE SONT PLUS UTILES ##
    if not save_results_intermediate :
        dropTable(connexion, 'arbustif_ini')
        dropTable(connexion, 'arbustif')
        dropTable(connexion, 'arbustif_bststr')
        dropTable(connexion, 'arbustif_bststr_uniq')
        dropTable(connexion, 'rgpt_arbustif')

    ## SAUVEGARDE DU RESULTAT EN UNE COUCHE VECTEUR
    if save_results_as_layer :
        exportVectorByOgr2ogr(connexion_fv_dic["dbname"], output_shrub_layer,tablename, user_name='postgres', password='postgres', ip_host='localhost', num_port='5432', schema_name='donneelidar', format_type='GPKG')

    return tablename



