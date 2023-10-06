from __future__ import print_function
import os,sys,glob,shutil,string, argparse
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_file import cleanTempData, deleteDir, removeFile
from CrossingVectorRaster import *
import pandas as pd
import geopandas as gpd
from rasterstats import *
from Lib_postgis import *
from DetectVegetationFormStratum import *

def vegetationMask(img_input, img_output, num_class = {"bati" : 1, "route" : 2, "sol nu" : 3, "eau" : 4, "vegetation" : 5}, overwrite = False):
    """
    Rôle : créé un masque de végétation à partir d'une image classifiée

    Paramètres :
        img_input : image classée en 5 classes
        img_output : image binaire : 1 pour la végétation et -1 pour non végétation
        num_class : dictionnaire reliant le nom de la classe au label, par défaut : {"bati" : 1, "route" : 2, "sol nu" : 3, "eau" : 4, "vegetation" : 5}
        overwrite : paramètre de ré-écriture, par défaut : False
    """

    #Verification de la non existence du fichier de sortie
    if overwrite == True and os.path.exists(img_output):
        os.remove(img_output)
    elif overwrite == False and os.path.exists(img_output):
        raise NameError(bold + red + "vegetationMask() : le fichier %s existe déjà" %(img_output)+ endC)

    #Calcul à l'aide de l'otb 
    exp = '"(im1b1==' + str(num_class["vegetation"]) + '?1:-1)"'

    cmd_mask = "otbcli_BandMath -il %s -out %s -exp %s" %(img_input, img_output, exp)

    exitCode = os.system(cmd_mask)

    if exitCode != 0:
        print(cmd_mask)
        raise NameError(bold + red + "vegetationMask() : une erreur est apparue lors de la création du masque de végétation (commande otbcli_BandMath)" + endC)

    return

def segmentationImageVegetetation(img_ref, img_input, file_output, param_minsize = 10, num_class = {"bati" : 1, "route" : 2, "sol nu" : 3, "eau" : 4, "vegetation" : 5}, format_vector='GPKG', save_intermediate_result = True, overwrite = False):
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
    extension = os.path.splitext(img_input)[1]

    file_out_suffix_mask_veg= "_mask_veg"
    mask_veg = repertory_output + os.sep + file_name + file_out_suffix_mask_veg + extension

    if os.path.exists(mask_veg):
        os.remove(mask_veg)

    #Création du masque de végétation
    vegetationMask(img_input, mask_veg, num_class)

    #Calcul de la segmentation Meanshift
    sgt_cmd = "otbcli_Segmentation -in %s -mode vector -mode.vector.out %s -mode.vector.inmask %s -filter meanshift  -filter.meanshift.minsize %s" %(img_original, file_output, mask_veg, param_minsize)

    exitCode = os.system(sgt_cmd)

    if exitCode != 0:
        print(sgt_cmd)
        raise NameError(bold + red + "segmentationVegetation() : une erreur est apparue lors de la segmentation de l'image (commande otbcli_Segmentation)." + endC)

    return

def classificationVerticalStratum(connexion, connexion_dic, sgts_input, raster_dic, format_type = 'GPKG', save_intermediate_result = False, overwrite = True):
    """
    Rôle : classe les segments en trois strates : arborée, arbustive et herbacée

    Paramètres :
        connexion : laissé tel quel, correspond à la variable de connexion à la base de données
        connexion_dic : dictionnaire des paramètres de connexion selon le modèle : {"dbname" : 'projetgus', "user_db" : 'postgres', "password_db" : 'postgres', "server_db" : 'localhost', "port_number" : '5432', "schema" : ''}
        sgts_input : fichier vecteur de segmentation
        raster_dic : dictionnaire associant le type de donnée récupéré avec le fichier raster contenant les informations, par exemple : {"mnh" : filename}
        format_type : format de la donnée vecteur en entrée, par défaut : GPKG
        save_intermediate_result : paramètre de sauvegarde des fichiers intermédiaire. Par défaut : False
        overwrite : paramètre de ré-écriture des fichiers. Par défaut False

    Sortie :
        file_output : couche vecteur de sortie correspondant au résultat de segmentation
    """
    li_tablename = []

    #Création d'une nouvelle couche avec les valeurs médianes de chaque image
    #Création du fichier
    repertory_output = os.path.dirname(sgts_input)
    file_name = os.path.splitext(os.path.basename(sgts_input))[0]
    extension_vecteur = os.path.splitext(sgts_input)[1]

    # file_mnh_out = repertory_output + os.sep + file_name + "MNH" + extension_vecteur
    # calc_statMedian(sgts_input, raster_dic["MNH"], file_mnh_out)

    #Export de la donnée dans la BD
    tablename_mnh = "table_sgts_mnh"
    # importVectorByOgr2ogr(connexion_dic["dbname"], file_mnh_out, tablename_mnh, user_name=connexion_dic["user_db"], password=connexion_dic["password_db"], ip_host=connexion_dic["server_db"], num_port=connexion_dic["port_number"], schema_name=connexion_dic["schema"], epsg=str(2154))

    # file_txt_out = repertory_output + os.sep + file_name + "TXT" + extension_vecteur
    # calc_statMedian(sgts_input, raster_dic["TXT"], file_txt_out)

    # #Export de la donnée dans la BD
    tablename_txt = "table_sgts_txt"
    # importVectorByOgr2ogr(connexion_dic["dbname"], file_txt_out, tablename_txt, user_name=connexion_dic["user_db"], password=connexion_dic["password_db"], ip_host=connexion_dic["server_db"], num_port=connexion_dic["port_number"], schema_name=connexion_dic["schema"],  epsg=str(2154))


    # #Supprimer le fichier si on ne veut pas le sauvegarder
    # if not save_intermediate_result :
    #     os.remove(file_mnh_out)
    #     os.remove(file_txt_out)


    # #Merge des colonnes de statistiques en une seule table "segments_vegetation" : deux tables à merger normalement
    # query = """
    # CREATE TABLE segments_vegetation_ini AS
    #     SELECT t2.dn, t2.geom, t2.median AS mnh, t1.median AS txt
    #     FROM %s AS t1, %s AS t2
    #     WHERE t1.dn = t2.dn;
    # """ %(tablename_txt, tablename_mnh)

    # #Exécution de la requête SQL
    # if debug >= 1:
    #     print(query)
    # executeQuery(connexion, query)

    #Prétraitements : transformation de l'ensemble des multipolygones en symples polygones
    query = """
    CREATE TABLE segments_vegetation_bis2 AS
        SELECT public.ST_MAKEVALID((public.ST_DUMP(t.geom)).geom::public.geometry(Polygon,2154)) as geom, t.mnh, t.txt
        FROM segments_vegetation_ini as t
    """

    #Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    #Traitement des artefacts au reflet blanc
    query = """
    CREATE TABLE segments_txt_val0_bis2 AS
        SELECT * 
        FROM segments_vegetation_bis2
        WHERE txt = 0;

    DELETE FROM segments_vegetation_bis2 WHERE txt = 0;
    """ 

    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    #Ajout d'un identifiant unique
    addUniqId(connexion, 'segments_vegetation_bis2')

    #Ajout d'un index spatial 
    addSpatialIndex(connexion, 'segments_vegetation_bis2')

    #Ajout de l'attribut "strate"
    addColumn(connexion, 'segments_vegetation_bis2', 'strate', 'varchar(100)')

    #Première phase : classification générale, à partir de règles de hauteur et de texture
    query = """
    UPDATE %s as t SET strate = 'arbore' WHERE t.txt < %s AND t.mnh  > %s;
    """ %('segments_vegetation_bis2', 11,3)

    query += """
    UPDATE %s as t SET strate = 'arbustif' WHERE t.txt < %s AND  t.mnh  <= %s;
    """ %('segments_vegetation_bis2', 11, 3)

    query += """
    UPDATE %s as t SET strate = 'herbace' WHERE t.txt  >= %s;
    """ %('segments_vegetation_bis2', 11)

    #Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    #Deuxième phase : reclassification des segments arbustifs

    #0# Extraction de deux catégories de segments arbustifs : 
      # les segments "isolés" (ne touchant pas d'autres segments arbustifs)
      # et les segments  de "regroupement"
    #Création table "rgpt_arbuste"(geom) contenant les polygones des regroupements 
    query = """
    CREATE TABLE rgpt_arbuste AS
        SELECT public.ST_MAKEVALID((public.ST_DUMP(public.ST_UNION(t.geom))).geom) AS geom
        FROM (SELECT geom FROM segments_vegetation WHERE strate='arbustif') AS t;
    """
        
    #Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    #Suppression de rgpt_arbuste trop petits --> surface <= 1m 
    query = """
    DELETE FROM rgpt_arbuste WHERE public.ST_AREA(geom) <= 1;
    """

    #Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    #Création d'un nouvel attribut nb_sgt
    addColumn(connexion, 'rgpt_arbuste', 'nb_sgt', 'int')

    #Création d'un identifiant unique 
        addUniqId(connexion, 'rgpt_arbuste')

    #Création d'un index spatial 
    addSpatialIndex(connexion, 'rgpt_arbuste')  

    #Creation d'une table intermediaire de segments arbustes dont les géométries correspondent à un point au centre du segment
    query = """
    CREATE TABLE tab_interm_arbuste AS
        SELECT fid, public.st_pointonsurface(geom) AS geom 
        FROM segments_vegetation
        WHERE strate = 'arbustif';
    """

    #Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    #Création d'un index spatial 
    addSpatialIndex(connexion, 'tab_interm_arbuste')

    addColumn(connexion, 'tab_interm_arbuste', 'fid_rgpt', 'integer')  

    #A présent, nous sommes obligés de passer par python pour lancer les requêtes car les requêtes spatiales globales sont TRES couteuses 
    
    cursor = connexion.cursor()
    data = readTable(connexion, 'rgpt_arbuste')
    tab_rgpt_sgt =[] 
    for el in data :
        #Compte le nombre de segments arbustifs dans chaque regroupement
        fid_rgpt = el[2]
        print("Compte le nombre de segments dans le regroupement "+str(fid_rgpt))
        query = """
        SELECT rgpt_arbuste.fid, count(rgpt_arbuste.fid) 
        FROM rgpt_arbuste, tab_interm_arbuste 
        WHERE rgpt_arbuste.fid = %s AND public.st_intersects(tab_interm_arbuste.geom, rgpt_arbuste.geom) 
        GROUP BY rgpt_arbuste.fid;
        """ %(fid_rgpt)
        cursor.execute(query)
        rgpt_count = cursor.fetchall()

        #Update de l'attribut nb_sgt dans la table rgpt_arbuste
        print("Met à jour la valeur du nombre de segment dans la table rgpt_arbuste")
        query = """
        UPDATE rgpt_arbuste SET nb_sgt = %s where rgpt_arbuste.fid = %s;
        """ %(rgpt_count[0][1],rgpt_count[0][0])  

        #Exécution de la requête SQL
        executeQuery(connexion, query)

        #Récupère chaque duo fid_rgpt - fid_sgt pour chaque croisement regroupement-segment 
        print("Récupère duo rgpt - sgt")
        query = """
        SELECT rgpt_arbuste.fid AS fid_rgpt, tab_interm_arbuste.fid AS fid_sgt 
        from rgpt_arbuste, tab_interm_arbuste 
        WHERE rgpt_arbuste.fid = %s AND public.st_intersects(tab_interm_arbuste.geom, rgpt_arbuste.geom) ;
        """ %(fid_rgpt)
        cursor.execute(query)
        duo_rgpt_sgt = cursor.fetchall()
        tab_rgpt_sgt.append(duo_rgpt_sgt)

    for el in tab_rgpt_sgt :
        for el2 in el :
            print(el2[0],el2[1])
            #Update de l'attribut fid_rgpt dans la table tab_interm_arbuste
            print("Met à jour l'identifiant du regroupement est rattaché  dans la table rgpt_arbuste")
            query = """
            UPDATE tab_interm_arbuste SET fid_rgpt = %s where tab_interm_arbuste.fid = %s;
            """ %(el2[0],el2[1])  
            print(query)
            executeQuery(connexion, query)

        


    
    #Création table "arbuste_uniq"(fid, geom, fid_rgpt) correspondant aux arbustes "isolés" qui ne touchent aucun autre segment arbustif
    query = """
    CREATE TABLE arbuste_uniq AS
        SELECT t1.fid, t1.geom, t4.fid_rgpt AS fid_rgpt
            FROM (SELECT fid, geom FROM segments_vegetation WHERE strate='arbustif') AS t1,
                    (SELECT t2.fid AS fid, t2.fid_rgpt
						FROM (SELECT fid FROM rgpt_arbuste WHERE nb_sgt<=1) as t3, tab_interm_arbuste AS t2
					WHERE t2.fid_rgpt = t3.fid) as t4
                        WHERE t1.fid = t4.fid;
    """
    #Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)
    
    #Création index spatial
    addSpatialIndex(connexion, 'arbuste_uniq')
    #Création d'un index sur une colonne 
    addIndex(connexion, 'arbuste_uniq', 'fid', 'idx_arbuste_uniq')

    #Création table "arbu_de_rgpt"(fid, geom, fid_rgpt) correspondant aux arbustes "regroupés" qui touchent d'autres segments arbustifs 
    query = """
    CREATE TABLE arbu_de_rgpt AS 
	    SELECT t1.fid, t1.geom, t4.fid_rgpt AS fid_rgpt
                        FROM (SELECT fid, geom FROM segments_vegetation WHERE strate='arbustif') AS t1,
                             (SELECT t3.fid AS fid, t3.fid_rgpt
								FROM (SELECT fid FROM rgpt_arbuste WHERE nb_sgt>1) as t2, 
								tab_interm_arbuste as t3
								WHERE t3.fid_rgpt = t2.fid) as t4
                        WHERE t1.fid = t4.fid;
    """
    #Exécution de la requête SQL
    executeQuery(connexion, query)

    #Création index spatial
    addSpatialIndex(connexion, 'arbu_de_rgpt')

    #Création d'un index sur une colonne 
    addIndex(connexion, 'arbu_de_rgpt', 'fid', 'idx_arbu_de_rgpt')
    

    #1# Reclassification des segments arbustes "isolés" 
    reclassIsolatedSegments(connexion)

    #2# Reclassification des segments arbustes "regroupés"
    reclassGroupSegments(connexion)
    closeConnection(connexion)


    return



def reclassIsolatedSegments(connexion):
    """
    Rôle : classe les différents segments arbustifs "isolés" 

    Paramètres :
        connexion : variable correspondant à la connexion à la base de données

    """

   #Récupération des segments herbacés 
    query = """
    CREATE TABLE rgpt_herbace AS
        SELECT public.ST_MAKEVALID((public.ST_DUMP(public.ST_UNION(t.geom))).geom) AS geom
        FROM (SELECT geom 
                FROM segments_vegetation
                WHERE strate='herbace') AS t;
    """         

    #Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)              

    #A. Reclassification des tous les segments arbustes isolés entourés de segments arborés et/ou de "vide"

    #Table contenant les identifiants des segments arbustifs isolés, la longueur de sa frontière et la longueur de sa frontière en contact avec segments arborés

    query = """
    CREATE TABLE arbu_isole_touch_arbo AS 
	    SELECT t1.fid, t1.geom, public.st_perimeter(t1.geom) AS long_bound_arbu, t2.long_bound_inters_arbo AS long_bound_inters_arbo
	    FROM (SELECT t3.fid, SUM(public.ST_LENGTH(t3.geom_bound_inters_arbo)) AS long_bound_inters_arbo
			    FROM (SELECT t1.fid, t1.geom, arbre.fid as fid_arbo, public.ST_INTERSECTION(public.ST_BOUNDARY(t1.geom),public.ST_INTERSECTION(t1.geom, arbre.geom)) AS geom_bound_inters_arbo 
					    FROM  arbuste_uniq AS t1, (SELECT fid, geom FROM segments_vegetation WHERE strate = 'arbore') as arbre
					    WHERE public.ST_INTERSECTS(t1.geom,arbre.geom) and t1.fid not in (SELECT t1.fid
																				    FROM (SELECT geom FROM segments_vegetation WHERE strate = 'herbace') AS herbe, arbuste_uniq as t1
																				    WHERE public.ST_INTERSECTS(herbe.geom, t1.geom)
																				    GROUP BY t1.fid)) AS t3
			    GROUP BY t3.fid) AS t2, arbuste_uniq AS t1
	WHERE t1.fid = t2.fid;
    """

    #Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)
                       
    # B. Reclassification des segments "arbustifs" en classe "arbore" entourés UNIQUEMENT d'arboré (frontière en contact avec arboré = frontière totale du segment)

    query = """
    UPDATE segments_vegetation SET strate = 'arbore' FROM (
											SELECT t1.fid
											FROM arbu_isole_touch_arbo AS t1
											WHERE t1.long_bound_inters_arbo = t1.long_bound_arbu) AS arbuste_entoure_arbre 
									  WHERE segments_vegetation.fid = arbuste_entoure_arbre.fid ;
    """
    #Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

   #C. Reclassification du segment "arbustif" en classe "arbore" ou suppression du segment s'il est entouré d'arboré ET de vide

   # si la différence de hauteur entre le segment arbustif et les segments arborés est inférieure ou égale à 1m --> reclassification en 'arbore'
    query = """
    UPDATE segments_vegetation SET strate = 'arbore' FROM (SELECT arbuste.fid FROM (SELECT t1.* 
																			            FROM (
																					        SELECT t3.fid, t3.geom  
																					        FROM arbu_isole_touch_arbo AS t3 
																					        WHERE t3.long_bound_inters_arbo < t3.long_bound_arbu
                                                                                            ) as arbuste,
																				            segments_vegetation AS t1
																			            WHERE t1.fid = arbuste.fid
                                                                                      ) AS arbuste,
																		              (SELECT * FROM segments_vegetation WHERE strate = 'arbore') AS arbre
																	            WHERE public.ST_INTERSECTS(arbuste.geom, arbre.geom) AND abs(arbuste.mnh-arbre.mnh)<=1 
																	            GROUP BY arbuste.fid) AS t2
										               WHERE segments_vegetation.fid = t2.fid;
    """
    #Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

   # si la différence de hauteur entre le segment arbustif et les segments arborés est supérieure stricte à 1m --> suppression
    query = """
    DELETE FROM segments_vegetation USING (SELECT arbuste.fid FROM (
                                                                    SELECT t1.* 
														            FROM (
															            SELECT t3.fid, t3.geom  
															            FROM arbu_isole_touch_arbo AS t3
															            WHERE t3.long_bound_inters_arbo < t3.long_bound_arbu
                                                                        ) as arbuste,
															            segments_vegetation as t1
														            WHERE t1.fid = arbuste.fid
                                                                    ) AS arbuste,
													                (SELECT * FROM segments_vegetation WHERE strate = 'arbore') AS arbre
													          WHERE public.ST_INTERSECTS(arbuste.geom, arbre.geom) AND abs(arbuste.mnh-arbre.mnh)>1 
													          GROUP BY arbuste.fid
                                           ) AS t2
										   WHERE segments_vegetation.fid = t2.fid;
    """
    #Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

   # D. Reclassification de tous les segments arbustifs isolés entourés de segments arborés ET herbacés

   # Table contenant les identifiants des segments arbustifs isolés, la longueur de sa frontière et la longueur de sa frontière en contact avec segments herbacés
    query = """
    CREATE TABLE arbu_isole_touch_herbe AS 
	    SELECT t1.fid, t1.geom, public.st_perimeter(t1.geom) AS long_bound_arbu, t3.long_bound_inters_herbe AS long_bound_inters_herbe
	    FROM (
             SELECT t2.fid, SUM(public.ST_LENGTH(t2.geom_bound_inters_herbe)) AS long_bound_inters_herbe
			 FROM (
                    SELECT t1.fid, t1.geom, herbe.fid AS fid_arbo, public.ST_INTERSECTION(public.ST_BOUNDARY(t1.geom),public.ST_INTERSECTION(t1.geom, herbe.geom)) AS geom_bound_inters_herbe
					FROM  arbuste_uniq AS t1, (SELECT fid, geom FROM segments_vegetation WHERE strate = 'herbace') as herbe
					WHERE public.ST_INTERSECTS(t1.geom,herbe.geom) and t1.fid not in (SELECT t1.fid
																				FROM (SELECT geom FROM segments_vegetation WHERE strate = 'arbore') AS arbre, arbuste_uniq AS t1
																				WHERE public.ST_INTERSECTS(arbre.geom, t1.geom)
																				GROUP BY t1.fid)
                    ) AS t2
			 GROUP BY t2.fid
             ) AS t3, arbuste_uniq AS t1
	    WHERE t1.fid = t3.fid;
    """

    #Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

   # Création de la table ne contenant que les arbustes qui touchent à la fois de l'arboré et de l'herbacé
    query = """
    CREATE TABLE arbu_touch_herb_arbo AS (
	    SELECT t1.* 
	    FROM arbuste_uniq as t1, (SELECT fid 
						            FROM arbu_isole_touch_arbo AS t2
						            UNION
						            SELECT fid 
						            FROM arbu_isole_touch_herbe AS t3) AS t4 
	    WHERE t1.fid != t4.fid);
    """

    #Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

   # Création de la table "matable" contenant l'identifiant du segment arboré ou herbacé avec lequel le segment arbustif intersecte 
    query = """
    CREATE TABLE matable AS (
                                        SELECT arbuste.fid AS id_arbu, sgt_herbarbo.fid AS id_sgt_t, sgt_herbarbo.strate AS strate_touch, abs(arbuste.mnh-sgt_herbarbo.mnh) AS diff_h
							            FROM (
                                              SELECT t1.* 
                                              FROM segments_vegetation AS t1, arbuste_uniq AS t2 
                                              WHERE t1.fid = t2.fid
                                              ) AS arbuste, 
								              (SELECT * FROM segments_vegetation WHERE strate in ('arbore', 'herbace')) AS sgt_herbarbo
							            WHERE public.ST_INTERSECTS(arbuste.geom, sgt_herbarbo.geom));
    """

    #Exécution de la requête SQL
    if debug >= 1:
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
	
    #Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

   # Reclassification pour chaque segment arbustif isolé en herbacé ou arboré ou arbustif suivant la valeur minimale de différence de hauteur avec le segment le plus proche
    query = """
    UPDATE segments_vegetation SET strate = sgt_touch_herbarbo.strate_touch FROM sgt_touch_herbarbo AS sgt_touch_herbarbo
                                                                            WHERE segments_vegetation.fid = sgt_touch_herbarbo.id_arbu AND sgt_touch_herbarbo.diff_h <= 1;
    """

    #Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    return 


def reclassGroupSegments(connexion):
    """
    Rôle : classe les segments arbustes regroupés

    Paramètre :
        connexion :

    """

    # Pour diminuer le temps de calcul, je propose de créer deux tables intermédiaires de gros segments herbacés et arborés
    query = """ 
    CREATE TABLE herbace AS
        SELECT public.ST_CHAIKINSMOOTHING((public.ST_DUMP(public.ST_MULTI(public.ST_UNION(t1.geom)))).geom) AS geom
        FROM (SELECT geom FROM segments_vegetation WHERE strate='herbace') AS t1;
    """

    query += """ 
    CREATE TABLE arbore AS
        SELECT public.ST_CHAIKINSMOOTHING((public.ST_DUMP(public.ST_MULTI(public.ST_UNION(t1.geom)))).geom) AS geom
        FROM (SELECT geom FROM segments_vegetation WHERE strate='arbore') AS t1;
    """
    # Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    # Index spatiaux 
    addSpatialIndex(connexion, 'herbace')
    addSpatialIndex(connexion, 'arbore')

      


    # Calcul la nouvelle table contenant les segments arbustifs appartennant à des regroupements
    ## Initialisation de trois grands types de segments arbustifs appartennant à des regroupements ##

    # Création d'une table intermédiaire contenant les rgpt_arbustifs qui intersectent des segments arborés
    query = """
    CREATE TABLE tab_interm_rgptarbu_touch_arbo AS
        SELECT DISTINCT t.fid, t.geom
        FROM rgpt_arbuste AS t, arbore
        WHERE public.st_intersects(arbore.geom, t.geom);
    """ 
    executeQuery(connexion, query)

   #  Ajout des indexs
    addIndex(connexion, 'tab_interm_rgptarbu_touch_arbo', 'fid', 'indx_fid_1') 
    addSpatialIndex(connexion, 'tab_interm_rgptarbu_touch_arbo')

    # Création d'une table intermédiaire contenant les rgpt n'intersectants QUE des segments herbacés 
    query = """
    CREATE TABLE tab_interm_rgptarbu_touchonlyherb AS
        SELECT t2.fid, t2.geom
        FROM tab_interm_rgptarbu_touch_herbo AS t2
        WHERE t2.fid not in (select fid from tab_interm_rgptarbu_touch_arbo);                                                               
    """
    executeQuery(connexion, query)


    # Ajout des indexs
    addIndex(connexion, 'tab_interm_rgptarbu_touchonlyherb', 'fid', 'indx_fid_2') 
    addSpatialIndex(connexion, 'tab_interm_rgptarbu_touchonlyherb')

    # Création d'une table intermédiaire contenant les rgpt_arbustifs qui intersectent des segments herbacés
    query = """
    CREATE TABLE tab_interm_rgptarbu_touch_herbo AS
        SELECT DISTINCT t.fid, t.geom
        FROM rgpt_arbuste AS t, herbace
        WHERE public.st_intersects(herbace.geom, t.geom);
    """ 
    executeQuery(connexion, query)

    # Ajout des indexs
    addIndex(connexion, 'tab_interm_rgptarbu_touch_herbo', 'fid', 'indx_fid_3') 
    addSpatialIndex(connexion, 'tab_interm_rgptarbu_touch_herbo')

    # Création d'une table intermédiaire contenant les rgpt n'intersectants QUE des segments arborés 
    query = """     
    CREATE TABLE tab_interm_rgptarbu_touchonlyarbo AS
        SELECT t2.fid, t2.geom
        FROM tab_interm_rgptarbu_touch_arbo AS t2
        WHERE t2.fid not in (select fid from tab_interm_rgptarbu_touch_herbo);                                                          
    """
    executeQuery(connexion, query)


    # Ajout des indexs
    addIndex(connexion, 'tab_interm_rgptarbu_touchonlyarbo', 'fid', 'indx_fid_4') 
    addSpatialIndex(connexion, 'tab_interm_rgptarbu_touchonlyarbo')


    # Création de la table contenant les segments arbustifs appartennant à des regroupements en contact avec des segments herbacés uniquement
    query = """
    CREATE TABLE sgt_rgpt_onlyherba AS
        SELECT DISTINCT t1.fid, t1.geom, t1.fid_rgpt
        FROM arbu_de_rgpt AS t1, tab_interm_rgptarbu_touchonlyherb as t2
        WHERE  t1.fid_rgpt = t2.fid;
    """

    # Création de la table contenant les segments arbustifs appartennant à des regroupements en contact avec des segments arborés uniquement
    query += """
    CREATE TABLE sgt_rgpt_onlyarbo AS
        SELECT DISTINCT t1.fid, t1.geom, t1.fid_rgpt
        FROM arbu_de_rgpt AS t1, tab_interm_rgptarbu_touchonlyarbo as t2
        WHERE  t1.fid_rgpt = t2.fid;
    """
    # Exécution de la requête SQL
    print(query)
    executeQuery(connexion, query)

    addSpatialIndex(connexion, 'sgt_rgpt_onlyherba')
    addSpatialIndex(connexion, 'sgt_rgpt_onlyarbo')
    addIndex(connexion, 'sgt_rgpt_onlyherba', 'fid', 'indx_sgtrgpt_onlyherba') 
    addIndex(connexion, 'sgt_rgpt_onlyarbo', 'fid', 'indx_sgtrgpt_onlyarbo') 




    #  Création de la table contant les segments arbustifs appartennant à des regroupements en contact avec des segments herbacés ET des segments arborés
    query = """
    CREATE TABLE sgt_rgpt_touch_arbo_herbe AS
                                            SELECT t1.fid, t1.geom, t1.fid_rgpt
                                            FROM arbu_de_rgpt AS t1
                                            WHERE t1.fid not in (select t2.fid from sgt_rgpt_onlyherba as t2 union select t3.fid from sgt_rgpt_onlyarbo as t3)
    """


    # Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    addIndex(connexion, 'sgt_rgpt_touch_arbo_herbe', 'fid','idx_fid_sgt_touch_both')
    addSpatialIndex(connexion, 'sgt_rgpt_touch_arbo_herbe')


    #Récupération du nombre de lignes
    #Récupération de la liste des identifiants segments routes
    cursor = connexion.cursor()
    cursor.execute("SELECT count(*) FROM sgt_rgpt_touch_arbo_herbe;")
    nb_line_avt = cursor.fetchall()
    print(nb_line_avt)

    #La V0 se fait en dehors de la boucle

    # Création de la table contenant les arbustes en bordure des regroupements qui touchent d'autres segments arborés et/ou herbacés
    query = """
    CREATE  TABLE sgt_rgpt_bordure AS
        SELECT t3.*
        FROM (
            SELECT arbuste.fid as id_arbu, sgt_touch.fid as id_sgt_t, sgt_touch.strate as strate_touch, abs(arbuste.mnh-sgt_touch.mnh) as diff_h
            FROM (
                SELECT t1.*
                FROM segments_vegetation AS t1, sgt_rgpt_touch_arbo_herbe as t2
                WHERE t1.fid = t2.fid
                )
                as arbuste, (
                        SELECT *
                        FROM segments_vegetation
                        WHERE strate in ('arbore', 'herbace')
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
                FROM segments_vegetation AS t1, sgt_rgpt_touch_arbo_herbe AS t2
                WHERE t1.fid = t2.fid
                )
                AS arbuste,
                (
                SELECT *
                FROM segments_vegetation
                WHERE strate in ('arbore', 'herbace')
                )
                AS sgt_touch
            WHERE public.st_intersects(arbuste.geom, sgt_touch.geom)
            ) 
            as t4
        GROUP BY id_arbu)
        AS t5 
        ON t3.id_arbu = t5.id_arbu AND t3.diff_h = t5.min_diff_h;
    """

    
    # Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    # Reclassification des segments situés en bordure de regroupement via le critère de hauteur
    query = """
    UPDATE segments_vegetation SET
        strate = sgt_rgpt_bordure.strate_touch
        FROM sgt_rgpt_bordure
        WHERE segments_vegetation.fid = sgt_rgpt_bordure.id_arbu and sgt_rgpt_bordure.diff_h <= 1;
    """

    # Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    # Suppression dans la table "sgt_rgpt_touch_arbo_herbe" des segments arbustifs traités précédemment
    query = """
    DELETE FROM sgt_rgpt_touch_arbo_herbe USING sgt_rgpt_bordure WHERE sgt_rgpt_touch_arbo_herbe.fid = sgt_rgpt_bordure.id_arbu;
    """
   
    # Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    # Récupération du nombre de lignes
    # Récupération de la liste des identifiants segments routes
    cursor.execute("SELECT count(*) FROM sgt_rgpt_touch_arbo_herbe;")
    nb_line = cursor.fetchall()
    print(nb_line)


    query= """
    DROP TABLE IF EXISTS sgt_rgpt_bordure
    """
    # Exécution de la requête SQL
    if debug >= 1:
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
                    FROM segments_vegetation AS t1, sgt_rgpt_touch_arbo_herbe as t2
                    WHERE t1.fid = t2.fid
                    )
                    as arbuste, (
                            SELECT *
                            FROM segments_vegetation
                            WHERE strate in ('arbore', 'herbace')
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
                    FROM segments_vegetation AS t1, sgt_rgpt_touch_arbo_herbe AS t2
                    WHERE t1.fid = t2.fid
                    )
                    AS arbuste,
                    (
                    SELECT *
                    FROM segments_vegetation
                    WHERE strate in ('arbore', 'herbace')
                    )
                    AS sgt_touch
                WHERE public.st_intersects(arbuste.geom, sgt_touch.geom)
                ) 
                as t4
            GROUP BY id_arbu)
            AS t5 
            ON t3.id_arbu = t5.id_arbu AND t3.diff_h = t5.min_diff_h;
        """
        # Exécution de la requête SQL
        if debug >= 1:
            print(query)
        executeQuery(connexion, query)


        # Reclassification des segments situés en bordure de regroupement via le critère de hauteur

        query= """
        UPDATE segments_vegetation SET
            strate = sgt_rgpt_bordure.strate_touch
            FROM sgt_rgpt_bordure
            WHERE segments_vegetation.fid = sgt_rgpt_bordure.id_arbu and sgt_rgpt_bordure.diff_h <= 1;
        """

         # Exécution de la requête SQL
        if debug >= 1:
            print(query)
        executeQuery(connexion, query)

       
        # Suppression dans la table "sgt_rgpt_touch_arbo_herbe" des segments arbustifs traités précédemment
        query = """
        DELETE FROM sgt_rgpt_touch_arbo_herbe USING sgt_rgpt_bordure WHERE sgt_rgpt_touch_arbo_herbe.fid = sgt_rgpt_bordure.id_arbu;
        """
        
        # Exécution de la requête SQL
        if debug >= 1:
            print(query)
        executeQuery(connexion, query)

         # Récupération du nombre de lignes
        # Récupération de la liste des identifiants segments routes
        cursor.execute("SELECT count(*) FROM sgt_rgpt_touch_arbo_herbe;")
        nb_line = cursor.fetchall()
        print(nb_line)


        query= """
        DROP TABLE IF EXISTS sgt_rgpt_bordure
        """
        # Exécution de la requête SQL
        if debug >= 1:
            print(query)
        executeQuery(connexion, query)

    closeConnection(connexion)
    return

def calc_statMedian(vector_input, image_input, vector_output):
    """
    Rôle : croisement raster/vecteur où on va calculer la médiane du raster sur l'emprise des entités vecteurs

    Paramètres :
        vector_input : couche vecteur sur laquelle on vient calculer la médiane du raster input
        image_input : couche raster
        vector_output : couche vecteur en sortie pour lequelle on a calculé les statistiques
    """
    #data = gpd.read_file(vector_input)
    #for el in data :
    #    print(zonal_stats(data[1],image_input, stats=['median']))
    #med = zonal_stats(vector_input, image_input, stats=['median'])
    #print(med)
    #On utilise rasterStats
    col_to_add_list = ["median"]
    col_to_delete_list = ["min", "max", "mean", "unique", "sum", "std", "range"]
    class_label_dico = {}
    statisticsVectorRaster(image_input, vector_input, vector_output, band_number=1,enable_stats_all_count = False, enable_stats_columns_str = False, enable_stats_columns_real = True, col_to_delete_list = col_to_delete_list, col_to_add_list = col_to_add_list, class_label_dico = class_label_dico, path_time_log = "", clean_small_polygons = False, format_vector = 'GPKG',  save_results_intermediate= False, overwrite= True)
    return

