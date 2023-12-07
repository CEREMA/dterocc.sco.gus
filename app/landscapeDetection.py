#Import des librairie Python
import math,os

#Import des librairies de /libs
from libs.Lib_postgis import addIndex, addSpatialIndex, addUniqId, addColumn, dropTable, dropColumn,executeQuery, exportVectorByOgr2ogr, importVectorByOgr2ogr, closeConnection, topologyCorrections
from libs.Lib_display import endC, bold, yellow, cyan, red
from libs.CrossingVectorRaster import statisticsVectorRaster
from libs.Lib_file import removeFile
from libs.Lib_raster import rasterizeVector

def landscapeDetection(connexion, connexion_dic, lds_repertory, shp_etude, img_ocs, num_class = ["bati" : 1, "route" : 2, "solnu" : 3, "eau" : 4, "vegetation" : 5]):
    """
    Rôle : création d'une couche vecteur "paysage"

    Paramètres :
        connexion :
        connexion_dic :
        lds_repertory : répertoire de travail pour la détection des paysages
        shp_etude : couche vecteur de l'emprise de la zone d'étude
        img_ocs : image raster ocs
        num_class : dictionnaire des classes attribuées. Par défaut :["bati" : 1, "route" : 2, "solnu" : 3, "eau" : 4, "vegetation" : 5] 
    """

    #Decoupe sur la zone étude l'image OCS
    filename = os.path.splitext(os.path.basename(img_ocs))[0]
    img_ocs_cut = lds_repertory + os.sep + filename + '_cut.tif'

    command_cut = "gdalwarp -cutline %s -crop_to_cutline %s %s" %(shp_etude, img_ocs, img_ocs_cut) 
    os.system(command_cut)

    #Extraction des 3 masques bâti, route et eau de l'ocs
    img_mask_bati = lds_repertory + os.sep + 'mask_bati.tif'
    img_mask_route = lds_repertory + os.sep + 'mask_route.tif'
    img_mask_eau = lds_repertory + os.sep + 'mask_eau.tif'

    command_maskbati = "otbcli_BandMath -il %s -out %s -exp '(im1b1==1)?1:0'" %(img_ocs_cut, img_mask_bati) 
    os.system(command_maskbati)

    command_maskroute = "otbcli_BandMath -il %s -out %s -exp '(im1b1==1)?1:0'" %(img_ocs_cut, img_mask_route) 
    os.system(command_maskroute)

    command_maskeau = "otbcli_BandMath -il %s -out %s -exp '(im1b1==1)?1:0'" %(img_ocs_cut, img_mask_eau) 
    os.system(command_maskeau)

    #Conversion des trois images masques en vecteur
    vect_mask_bati = lds_repertory + os.sep + 'mask_bati.shp'
    vect_mask_route = lds_repertory + os.sep + 'mask_route.shp'
    vect_mask_eau = lds_repertory + os.sep + 'mask_eau.shp'

    polygonizeRaster(img_mask_bati, vect_mask_bati, 'mask_bati', field_name="id", vector_export_format="ESRI Shapefile")
    polygonizeRaster(img_mask_route, vect_mask_route, 'mask_route', field_name="id", vector_export_format="ESRI Shapefile")
    polygonizeRaster(img_mask_eau, vect_mask_eau, 'mask_eau', field_name="id", vector_export_format="ESRI Shapefile")

    #Import en base des trois données vecteurs sous la forme de trois tables
    tab_bati = 'tab_bati'
    tab_route = 'tab_route'
    tab_eau = 'tab_eau'
    importVectorByOgr2ogr(connexion_dic["dbname"], vect_mask_bati, tab_bati, user_name=connexion_dic["user_db"], password=connexion_dic["password_db"], ip_host=connexion_dic["server_db"], num_port=connexion_dic["port_number"],schema_name=connexion_dic["schema"], epsg=str(2154))
    importVectorByOgr2ogr(connexion_dic["dbname"], vect_mask_route, tab_route, user_name=connexion_dic["user_db"], password=connexion_dic["password_db"], ip_host=connexion_dic["server_db"], num_port=connexion_dic["port_number"],schema_name=connexion_dic["schema"], epsg=str(2154))
    importVectorByOgr2ogr(connexion_dic["dbname"], vect_mask_eau, tab_eau, user_name=connexion_dic["user_db"], password=connexion_dic["password_db"], ip_host=connexion_dic["server_db"], num_port=connexion_dic["port_number"],schema_name=connexion_dic["schema"], epsg=str(2154))

    #Suppression des polygones "non bati", "non route" et "non eau" 
    query = """
        DELETE FROM %s WHERE dn = 0;
        DELETE FROM %s WHERE dn = 0;
        DELETE FROM %s WHERE dn = 0;
    """ %(tab_bati, tab_route, tab_eau)

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    #Ajout des index
    addSpatialIndex(connexion, tab_bati) 
    addSpatialIndex(connexion, tab_route) 
    addSpatialIndex(connexion, tab_eau) 

    ##Travaux sur la couche "eau"##  

    query = """
    DROP TABLE IF EXISTS tab_etendueetcoursdeau;
    CREATE TABLE tab_etendueetcoursdeau AS
        SELECT public.ST_UNION(public.ST_BUFFER(geom, 4)) AS geom, '3' AS dn
        FROM %s
        WHERE public.ST_AREA(geom) > 100;
    """ %(tab_eau)

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    ##Travaux sur la couche "route"##  

    query = """
    DROP TABLE IF EXISTS tab_voirieetinfrastructure;
    CREATE TABLE tab_voirieetinfrastructure AS
        SELECT public.ST_UNION(public.ST_DIFFERENCE(route.geom, eau.geom)) AS geom
        FROM (SELECT public.ST_UNION(public.ST_BUFFER(geom, 4)) AS geom, '2' AS dn
                FROM %s
                WHERE public.ST_AREA(geom) > 100) AS route, %s AS eau;
    """ %(tab_route, tab_eau)

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    ##Travaux sur la couche "bati"##  

    #Sélection avec filtre 
    query = """
    DROP TABLE IF EXISTS tab_milieuurbanise;
    CREATE TABLE tab_milieuurbanise AS
        SELECT public.ST_UNION(public.ST_DIFFERENCE(bati_moins_eau.geom, route.geom)) AS geom, '1' AS dn
            FROM (SELECT public.ST_UNION(public.ST_DIFFERENCE(bati.geom, eau.geom)) AS geom
                    FROM (SELECT public.ST_UNION(public.ST_BUFFER(public.ST_BUFFER(geom, 40), -25)) AS geom
                            FROM %s 
                            WHERE public.ST_AREA(geom) > 100) AS bati, %s AS eau
                ) AS bati_moins_eau, %s AS route;  
    """ %(tab_bati, tab_eau, tab_route)

    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    ##Travaux sur le milieu agricole et forestier##
    query = """
    DROP TABLE IF EXISTS tab_milieuagrifor;
    CREATE TABLE tab_milieuagrifor AS
        SELECT public.ST_UNION(public.ST_DIFFERENCE(shp.geom, other.geom)) AS geom, '4' AS dn
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

    #avant de faire la suite, vérifier qu'il n'y a pas de superposition des couches

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

    #Export de la donnée au format vecteur et raster

    #Suppression des tables inutiles
    dropTable(connexion, tab_bati)
    dropTable(connexion, tab_eau)
    dropTable(connexion, tab_route)
    dropTable(connexion, 'tab_etendueetcoursdeau')
    dropTable(connexion, 'tab_milieuurbanise')  
    dropTable(connexion, 'tab_voirieetinfrastructure')
    dropTable(connexion, 'tab_milieuagrifor')

    return
