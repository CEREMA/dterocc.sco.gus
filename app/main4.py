import os, math
from Lib_grass import *
from Lib_postgis import *
from VerticalStratumDetection import *

if __name__=='__main__':
    connexion_ini_dic = {
      "dbname" : 'projetgus',
      "user_db" : 'postgres',
      "password_db" : 'postgres',
      "server_db" : 'localhost',
      "port_number" : '5432',
      "schema" : ''
    }
    debug = 5

    #Dictionnaire des paramètres BD de classification en strates verticales 
    connexion_stratev_dic = connexion_ini_dic
    connexion_stratev_dic["schema"] = "public"
    connexion = openConnection(connexion_stratev_dic["dbname"], user_name=connexion_stratev_dic["user_db"], password=connexion_stratev_dic["password_db"], ip_host=connexion_stratev_dic["server_db"], num_port=connexion_stratev_dic["port_number"], schema_name=connexion_stratev_dic["schema"])
    cursor = connexion.cursor()
    # Début de la construction de la requête de création des segments perpendiculaires
    query_seg_perp = "DROP TABLE IF EXISTS ara_seg_perp;\n"
    query_seg_perp += "CREATE TABLE ara_seg_perp (id int, id_seg text, id_perp text, xR float, yR float, xP float, yP float, geom geometry);\n"
    query_seg_perp += "INSERT INTO ara_seg_perp VALUES\n"

    # Récupération de la liste des identifiants segments routes
    cursor.execute("SELECT id_seg FROM squelette2 GROUP BY id_seg ORDER BY id_seg;")
    id_seg_list = cursor.fetchall()
    print(id_seg_list)

    seg_dist = 0.02

    # Boucle sur les segments routes
    nb_seg = len(id_seg_list)
    treat_seg = 1
    for id_seg in id_seg_list:
        if debug >= 4:
            print(bold + "    Traitement du segment route : " + endC + str(treat_seg) + "/" + str(nb_seg))

        id_seg = id_seg[0]
        
        query = """
        SELECT id FROM squelette2 WHERE id_seg = %s;
        """ %(id_seg)
        
        cursor.execute(query)
        id = cursor.fetchone()[0]

        # Table temporaire ne contenant qu'un segment route donné : ST_LineMerge(geom) permet de passer la géométrie de MultiLineString à LineString, pour éviter des problèmes de requêtes spatiales
        query_temp1_seg = "DROP TABLE IF EXISTS ara_temp1_seg;\n"
        query_temp1_seg += "CREATE TABLE ara_temp1_seg AS SELECT id as id, id_seg as id_seg, ST_LineMerge(geom) as geom FROM %s WHERE id_seg = %s;\n" % ('squelette2', id_seg)
        if debug >= 4:
            print(query_temp1_seg)
        executeQuery(connexion, query_temp1_seg)


        # Récupération du nombre de sommets du segment route (utile pour les segments routes en courbe, permet de récupérer le dernier point du segment)
        cursor.execute("SELECT ST_NPoints(geom) FROM ara_temp1_seg;")
        nb_points = cursor.fetchone()

        # Récupération des coordonnées X et Y des points extrémités du segment route
        query_xR1 = "SELECT ST_X(geom) as X FROM (SELECT ST_AsText(ST_PointN(geom,1)) as geom FROM ara_temp1_seg) as toto;"
        cursor.execute(query_xR1)
        xR1 = cursor.fetchone()
        query_yR1 = "SELECT ST_Y(geom) as Y FROM (SELECT ST_AsText(ST_PointN(geom,1)) as geom FROM ara_temp1_seg) as toto;"
        cursor.execute(query_yR1)
        yR1 = cursor.fetchone()
        query_xR2 = "SELECT ST_X(geom) as X FROM (SELECT ST_AsText(ST_PointN(geom,%s)) as geom FROM ara_temp1_seg) as toto;" % (nb_points)
        cursor.execute(query_xR2)
        xR2 = cursor.fetchone()
        query_yR2 = "SELECT ST_Y(geom) as Y FROM (SELECT ST_AsText(ST_PointN(geom,%s)) as geom FROM ara_temp1_seg) as toto;" % (nb_points)
        cursor.execute(query_yR2)
        yR2 = cursor.fetchone()

        # Transformation des coordonnées X et Y des points extrémités du segment route en valeurs numériques
        xR1 = float(str(xR1)[1:-2])
        yR1 = float(str(yR1)[1:-2])
        xR2 = float(str(xR2)[1:-2])
        yR2 = float(str(yR2)[1:-2])
        if debug >= 4:
            print("      xR1 = " + str(xR1))
            print("      yR1 = " + str(yR1))
            print("      xR2 = " + str(xR2))
            print("      yR2 = " + str(yR2))

        # Calcul des delta X et Y entre les points extrémités du segment route
        dxR = xR1-xR2
        dyR = yR1-yR2
        if debug >= 4:
            print("      dxR = " + str(dxR))
            print("      dyR = " + str(dyR))
            print("\n")

        # Suppression des cas où le script créé des perpendiculaires tous les cm ! Bug lié à la segmentation des routes
        dist_R1_R2 = math.sqrt((abs(dxR)**2) + (abs(dyR)**2))
       # if dist_R1_R2 >= (seg_dist/2):

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
        seg_length = 40
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
        query_seg_perp += "    (%s, '%s', '%s_perp1', %s, %s, %s, %s, 'LINESTRING(%s %s, %s %s)'),\n" % (str(id), str(id_seg), str(id_seg), xR1, yR1, xP1, yP1, xR1, yR1, xP1, yP1)
        query_seg_perp += "    (%s, '%s', '%s_perp2', %s, %s, %s, %s, 'LINESTRING(%s %s, %s %s)'),\n" % (str(id), str(id_seg), str(id_seg), xR1, yR1, xP2, yP2, xR1, yR1, xP2, yP2)

        treat_seg += 1

    # Fin de la construction de la requête de création des segments perpendiculaires et exécution de cette requête
    query_seg_perp = query_seg_perp[:-2] + ";\n" # Transformer la virgule de la dernière ligne SQL en point-virgule (pour terminer la requête)
    query_seg_perp += "ALTER TABLE ara_seg_perp ALTER COLUMN geom TYPE geometry(LINESTRING,%s) USING ST_SetSRID(geom,%s);\n" % ('2154','2154') # Mise à jour du système de coordonnées
    query_seg_perp += "CREATE INDEX IF NOT EXISTS seg_perp_geom_gist ON ara_seg_perp USING GIST (geom);\n"
    if debug >= 2:
        print(query_seg_perp)
    executeQuery(connexion, query_seg_perp)

    print(bold + cyan + "Intersect entre les segments perpendiculaires et les bâtiments :" + endC)

    # Requête d'intersect entre les segments perpendiculaires et les bâtiments
    query_intersect = """
    DROP TABLE IF EXISTS ara_intersect_bati;
    CREATE TABLE ara_intersect_bati AS
        SELECT r.id_seg as id_seg, r.id_perp as id_perp, r.xR as xR, r.yR as yR, ST_Intersection(r.geom, b.geom) as geom
        FROM ara_seg_perp as r, poly_h as b
        WHERE ST_Intersects(r.geom, b.geom) and r.id = b.id;
    ALTER TABLE ara_intersect_bati ADD COLUMN id_intersect serial;
    CREATE INDEX IF NOT EXISTS intersect_bati_geom_gist ON ara_intersect_bati USING GIST (geom);
    """ 
    if debug >= 2:
        print(query_intersect)
    executeQuery(connexion, query_intersect)


    query = """
    CREATE TABLE statslonglat_poly_h AS
        SELECT t1.id, public.ST_LENGTH(t2.geom) AS long, t1.largeur_moy AS larg 
        FROM (
            SELECT t2.id, AVG(public.ST_LENGTH(t1.geom)) AS largeur_moy 
            FROM ara_intersect_bati AS t1, poly_h AS t2 
            WHERE public.ST_INTERSECTS(t2.geom, t1.geom) 
            GROUP BY t2.id
            ) as t1,
            squelette3 AS t2 
        WHERE t1.id = t2.id;
    """
    executeQuery(connexion, query)

    query = """
    ALTER TABLE statslonglat_poly_h ADD COLUMN elong float;
    """
    executeQuery(connexion, query)

    query = """
    UPDATE statslonglat_poly_h AS t1 SET elong = (t2.long/t2.larg) FROM statslonglat_poly_h AS t2 WHERE t1.id = t2.id
    """
    executeQuery(connexion, query)




    
    closeConnection(connexion)