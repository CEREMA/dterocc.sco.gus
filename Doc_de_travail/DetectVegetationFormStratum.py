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

    UPDATE %s SET id_comp = (4*PI()*public.ST_AREA(public.ST_BUFFER(geom,%s)))/(public.ST_PERIMETER(public.ST_BUFFER(geom,%s))*public.ST_PERIMETER(public.ST_BUFFER(geom,%s)))
                        WHERE fid = fid AND public.ST_PERIMETER(public.ST_BUFFER(geom,%s)) <> 0;
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
    #Calcul des valeurs de longueur et de largeur des rectangles orientés englobant minimaux des polygones
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

    query = """
    UPDATE %s SET largeur= LEAST(sqrt((x1-x0)^2+(y1-y0)^2), sqrt((x3-x0)^2+(y3-y0)^2)) WHERE fid = fid;
    """ %(tablename)

    query += """
    UPDATE %s SET longueur= GREATEST(sqrt((x1-x0)^2+(y1-y0)^2), sqrt((x3-x0)^2+(y3-y0)^2)) WHERE fid = fid;
    """ %(tablename)

    #Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    #Création et implémentation de l'indicateur de convexité (id_conv)
    addColumn(connexion, tablename, 'id_elong', 'float')
    query = """
    UPDATE %s SET id_elong = (longueur/largeur)
                        WHERE fid = fid AND largeur <> 0;
    """ %(tablename)

    #Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

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
        connexion
        tablename
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
        connexion
        tablename
        geomcolumn : nom de la colonne géometrie, par défaut : 'geom'
    """

    nameindex = 'idx_gist_' + tablename
    query = """
    CREATE INDEX %s ON %s USING gist(%s);
;
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
        connexion :
        tablename : nom de la table
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
        connexion :
        tablename : nom de la table
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


def firstClassification(connexion, tablename, compacthreshold = 0.7, areathreshold = 30, typeclass = 'arbore'):
    """
    Rôle : classification en trois classes basée sur un critère de surface et de compacité

    Paramètres :
        connexion : connexion à la base donnée et au schéma correspondant
        tablename : nom de la table dans laquelle on calcule l'indicateur de compacité
        name_col_comp : nom de la colonne correspondant à l'indice de compacité
        compacthreshold : valeur du seuil de compacité, par défaut : 0.7
        areathreshold : valeur du seuil de surface, par défaut : 30
        typeclass : type de classification : 'arboree' ou 'arbustive', par défaut : 'arboree'

    Sortie :
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

def getCoordRectEnglValue(connexion, tablename, attributname):
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


def classWoodStrictWooded(connexion, tablename, thresholdTreeLine):
    """
    Rôle

    Paramètres :

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

    #Création index spatial
    query += """
    CREATE INDEX idx_arbore_bststr ON arbore_bststr USING gist(geom);
    """
    #Création d'une table avec uniquement les boisements
    query += """
    CREATE TABLE arbore_bststr_uniq AS (SELECT public.ST_MAKEVALID((public.ST_DUMP(geom)).geom::public.geometry(Polygon,2154)) AS geom FROM arbore_bststr);
    """

    #Création d'un identifiant unique
    query += """
    ALTER TABLE arbore_bststr_uniq ADD COLUMN fid SERIAL PRIMARY key;
    """

    #Création d'un index spatial
    query += """
    CREATE INDEX idx_arbore_bststr_uniq ON arbore_bststr_uniq USING gist(geom);
    """

    #Ajout de l'attribut fv
    query += """
    ALTER TABLE arbore_bststr_uniq ADD COLUMN fv varchar(100);
    """

    #Implémentation de la valeur unique 'boisement arbore' pour tous les polygones de végétation dont on est sûr que ce sont des boisements
    query += """
    UPDATE arbore_bststr_uniq SET fv='boisement arbore';
    """

    #Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    return

def classRemainsWooded(connexion, tablename, convexthreshold, extensiontreshold, areathreshold, compacthreshold, compacthreshold_V2):
    """
    Rôle :

    Paramètres :

    Sortie :

    """

    query = """
    CREATE TABLE rgpt_arbore AS
        SELECT public.ST_MAKEVALID((public.ST_DUMP(public.ST_DIFFERENCE(rgt.geom, arbore_bststr.geom))).geom::public.geometry(Polygon, 2154)) AS geom
        FROM (SELECT geom
                FROM %s
                WHERE fv = 'regroupement arbore') AS rgt, arbore_bststr;
    """ %(tablename)

    #Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    tablename = 'rgpt_arbore'

    #Création d'un identifiant unique
    addUniqId(connexion, tablename)

    #Création d'un index spatial
    addSpatialIndex(connexion, tablename)

    #Ajout de l'attribut fv
    addColumn(connexion, tablename, 'fv', 'varchar(100)')



    #Suppression des polygones trop petits (artefacts)
    query = """
    DELETE FROM rgpt_arbore WHERE public.ST_AREA(rgpt_arbore.geom) <= 1;
    """
    #Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    #Création et calcul de l'indicateur de convexité
    createConvexityIndicator(connexion, tablename)

    #Création et calcul de l'indicateur de compacité
    createCompactnessIndicator(connexion, tablename, 2)

    #Création et calcul de l'indicateur d'élongation
    createExtensionIndicator(connexion, tablename)

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

def detectInTreeStratum(connexion, tablename):
    """
    Rôle : détecté les formes végétales horizontales au sein de la
    strate arborée

    Paramètres :
        connexion :
        tablename :

    """
    #Récupération de la table composée uniquement des segments arborés
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

    # Regroupement et lissage des segments arborés
    query = """
    CREATE TABLE arbore AS
        SELECT public.ST_CHAIKINSMOOTHING((public.ST_DUMP(public.ST_MULTI(public.ST_UNION(arbore_ini.geom)))).geom) AS geom
        FROM arbore_ini;
    """
    #Création index spatial
    query += """
    CREATE INDEX idx_arbore ON arbore USING gist(geom);
    """
    #Suppression de la table arbore_ini (n'est plus utile)
    query += """
    DROP TABLE IF EXISTS arbore_ini;
    """
    tablename = 'arbore'
    #Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    #Création d'un identifiant unique
    addUniqId(connexion, tablename)

    #Création d'un index spatial
    addSpatialIndex(connexion, tablename)

    #Création de la colonne strate qui correspond à 'arboree' pour tous les polygones
    addColumn(connexion, tablename, 'strate', 'varchar(100)')

    #Création de la colonne fv
    addColumn(connexion, tablename, 'fv', 'varchar(100)')

    #Création et calcul de l'indicateur de forme : compacité
    createCompactnessIndicator(connexion, tablename, 2)

    #Classement des segments en "arbre isole", "tache arboree" et "regroupement arbore"
    #basé sur un critère de surface et de seuil sur l'indice de compacité
    firstClassification(connexion, tablename)

    #Travaux sur les "regroupements arborés"

    #Extraction des polygones correspondants aux boisements strictes ET tous les petits segments en contact avec les boisements strictes
    classWoodStrictWooded(connexion, tablename, 7)

    #Travaux sur des autres polygones de regroupements arborés qui ne sont pas des boisements strictes
    classRemainsWooded(connexion, tablename, 0.7, 2.5, 30, 0.7, 0.5)

    query = """
    ALTER TABLE rgpt_arbore DROP COLUMN IF EXISTS id_comp, DROP COLUMN IF EXISTS id, DROP COLUMN IF EXISTS id_conv, DROP COLUMN IF EXISTS id_elong;

    CREATE TABLE strate_arboree AS
        SELECT strate_arboree.fv as fv, public.ST_MAKEVALID((public.ST_DUMP(public.ST_UNION(strate_arboree.geom))).geom::public.geometry(POLYGON,2154)) as geom
    FROM ((SELECT ab2.geom, ab2.fv
            FROM (SELECT geom, fv
                    FROM arbore
                    WHERE fv in ('arbre isole', 'tache arboree')) as ab2)
            UNION
           (SELECT geom, fv
            FROM arbore_bststr_uniq)
            UNION
           (SELECT geom, fv
            FROM rgpt_arbore)) AS strate_arboree
    WHERE public.ST_INTERSECTS(strate_arboree.geom, strate_arboree.geom)
    GROUP BY strate_arboree.fv;


    ALTER TABLE strate_arboree ADD COLUMN fid serial PRIMARY KEY;

    ALTER TABLE strate_arboree ADD COLUMN strate varchar(100);

    UPDATE strate_arboree SET strate='arbore';

    CREATE index idx_geom_sarbo ON strate_arboree USING gist(geom);
    """

    #Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    return






