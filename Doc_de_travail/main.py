from MnhCreation import mnhCreation
from NeochannelComputation_gus import neochannelComputation
from DataConcatenation import concatenateData
#from ImagesAssemblyGUS_ok import cutImageByVector
from Lib_postgis import *
from DetectVegetationFormStratum import *
from Lib_vector import *
import sys,os,glob
from osgeo import ogr ,osr
from MacroSampleCreation import *
from VerticalStratumDetection import *

if __name__ == "__main__":

    #Préparation du parser
    #à faire par la suite


    #1# Assemblage des tuiles d'images Pléiades sur l'emprise de la zone d'étude
    #Soit elles sont déjà assemblées et on ne fait que découper avec la fonction suivante


    #cutImageByVector(r'/mnt/RAM_disk/MGN_contours.shp' ,r'/mnt/RAM_disk/ORT_20220614_NADIR_16B_MGN.tif', r'/mnt/RAM_disk/ORT_20220614_NADIR_16B_MGN_V2.tif')
    #Soit elles doivent êtres assemblées

    #images_input_list = [r'/mnt/RAM_disk/ORT_20220614_NADIR_16B_MGN_V2.tif', r'/mnt/RAM_disk/MNHtest.tif', r'/mnt/RAM_disk/img_origine_hue.tif', r'/mnt/RAM_disk/img_origine_msavi2.tif', r'/mnt/RAM_disk/img_origine_ndvi.tif', r'/mnt/RAM_disk/img_origine_ndwi2.tif', r'/mnt/RAM_disk/img_origine_tmp_txtSFS_u.tif']
    #images_input_list = [r'/mnt/RAM_disk/ORT_20220614_NADIR_16B_MGN_V2.tif', r'/mnt/RAM_disk/MNHtest.tif']
    #2# Calcul du MNH
    #mnh = MnhCreation(r'/mnt/RAM_disk/DSM_PRODUITS_RGE.tif', r'/mnt/Data/20_Etudes_Encours/ENVIRONNEMENT/2022_GreenUrbanSat/1-DATAS/1-DONNEES_ELEVATION/MNT/2021/NANCY/MNT_RGEALTI/MNT_RGEALTI_1M_ZONE_DE_NANCY.tif', r'/mnt/RAM_disk/MNHtest.tif', r'/mnt/RAM_disk/MGN_contours.shp', r'/mnt/RAM_disk/ORT_20220614_NADIR_16B_MGN.tif',  epsg=2154, nivellement = True, format_raster = 'GTiff', format_vector = 'ESRI Shapefile',  rewrite = True, save_results_intermediate = True)


    #3# Calcul des néocanaux
    #neochannels = neochannelComputation(r'/mnt/RAM_disk/ORT_20220614_NADIR_16B_MGN_V2.tif', r'/mnt/RAM_disk/ORT_P1AP_MGN.tif', r'/mnt/RAM_disk/img_origine.tif', r'/mnt/RAM_disk/MGN_contours.shp', save_results_intermediate = False)

    #for el in neochannels:
    #    images_input_list.append(el)
    # Phase de test si les emprises correspondent bien

    #4# Concatnéation des néocanaux
    #concatenateData(images_input_list, r'/mnt/RAM_disk/final.tif')

    #5# Création des échantillons d'apprentissage
    #Fournir 5 couches vectorielles
    bati = r'/mnt/RAM_disk/bati.gpkg'
    route = ''
    solnu = ''
    eau = ''
    vegetation = ''


    #6# Préparation des échantillons d'apprentissage
    #macroSamplesPrepare(r'/mnt/RAM_disk/ORT_20220614_NADIR_16B_MGN_V2.tif', bati, r'/mnt/RAM_disk/output_vector.tif', r'/mnt/RAM_disk/MGN_contours.shp', erosionoption = True, format_vector='GPKG')

    #7# Nettoyage des échantillons d'apprentissage : érosion + filtrage avec les néocanaux
    #corr_bati = {"ndvi" : [r'/mnt/RAM_disk/img_origine_ndvi.tif', 0.25, 1]}
    #macroSamplesClean(r'/mnt/RAM_disk/output_vector.tif', r'/mnt/RAM_disk/output_vector_clean.tif', corr_bati)



    # # Segmentation de l'image
    #segmentationImageVegetetation(r'/mnt/RAM_disk/ORT_ZE.tif',r'/mnt/RAM_disk/ZE_segmentation.tif', r'/mnt/RAM_disk/ZE_out_segmentation.gpkg')


    # # Classification en strates verticales
    ## INITIALISATION POUR CONNEXION AU SERVEUR

    dbname = 'projetgus'
    user_db = 'postgres'
    password_db = ''
    server_db = 'localhost'
    port_number = '5432'
    schema = ''

    connexion_ini_dic = {"dbname" : 'projetgus', "user_db" : 'postgres', "password_db" : 'postgres', "server_db" : 'localhost', "port_number" : '5432', "schema" : ''}

    connexion_stratev_dic = connexion_ini_dic
    connexion_stratev_dic["schema"] = 'classification_stratev'

    #connexion_fv_dic = connexion_ini_dic
    #connexion_fv_dic["schema"] = 'classification_fv'

    #Création d'une base de donnée
    #createDatabase(connexion_ini_dic["dbname"], user_name=connexion_ini_dic["user_db"], password=connexion_ini_dic["password_db"], ip_host=connexion_ini_dic["server_db"], num_port=connexion_ini_dic["port_number"], schema_name=connexion_ini_dic["schema"])

    #Connexion à la base de donnée
    #connexion = openConnection(connexion_ini_dic["dbname"], user_name=connexion_ini_dic["user_db"], password=connexion_ini_dic["password_db"], ip_host=connexion_ini_dic["server_db"], num_port=connexion_ini_dic["port_number"], schema_name=connexion_ini_dic["schema"])

    #Création d'un schema pour la partie classification en strates verticales
    #createSchema(connexion, 'classification_stratev')

    #Connexion au schema de classification en strates verticales
    connexion = openConnection(connexion_stratev_dic["dbname"], user_name=connexion_stratev_dic["user_db"], password=connexion_stratev_dic["password_db"], ip_host=connexion_stratev_dic["server_db"], num_port=connexion_stratev_dic["port_number"], schema_name=connexion_stratev_dic["schema"])

    raster_dic = {"MNH" : r'/mnt/RAM_disk/MNH_14062022_CF.tif', "TXT" : r'/mnt/RAM_disk/img_origine_txtSFS.tif'}
    classificationVerticalStratum(connexion, connexion_stratev_dic, r'/mnt/RAM_disk/ZE_out_segmentation.gpkg', raster_dic, format_type = 'GPKG', save_intermediate_result = True, overwrite = True)
    # #Test la version de postgres
    # postgresversion = versionPostgreSQL(database_name='postgres', user_name='postgres', password='postgres', ip_host='localhost', num_port='5432', schema_name='')

    # #Test la version de postgis
    # postgisvesrion = versionPostGIS(database_name='template_postgis', user_name='postgres', password='postgres', ip_host='localhost', num_port='5432', schema_name='')


    # # # Classification en formes végétales horizontales

    #Création d'un schema pour la partie classification en formes végétales horizontales
    #createSchema(connexion, 'classification_fv')

    #Connexion au schema de classification en strates verticales

    #Strate arborée
    #connexion = openConnection('etape2', user_name='postgres', password="", ip_host='localhost', num_port='5432', schema_name='donneelidar')

    # #Initialisation du dictionnaire contenant les valeurs seuils pour la classification des entités de la strate arborée
    #treethresholds = {"seuil_surface" : 5, "seuil_compacite_1" : 0.7, "seuil_compacite_2" : 0.5, "seuil_convexite" : 0.7, "seuil_elongation" : 2.5, "val_largeur_max_alignement" : 5, "val_buffer" : 1}

    #detectInTreeStratum(connexion, tablename, treethresholds, output_tree_layer, connexion_fv_dic, save_results_as_layer = False, save_results_intermediate = False)
    #connexion_fv_dic = {"dbname" : 'etape2', "user_db" : 'postgres', "password_db" : "", "server_db" : 'localhost', "port_number" : '5432', "schema" : 'donneelidar'}
    #detectInShrubStratum(connexion, 'sgts_veg4',  r'/mnt/RAM_disk/output_vectorshrub.gpkg', connexion_fv_dic = connexion_fv_dic, thresholds = treethresholds, save_results_as_layer = True, save_results_intermediate = True)
