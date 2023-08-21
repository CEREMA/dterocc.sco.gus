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
from IndicateursComputation import *

if __name__ == "__main__":

    #Strate arborée
    # connexion = openConnection('etape2', user_name='postgres', password="", ip_host='localhost', num_port='5432', schema_name='donneelidar')

    #Initialisation du dictionnaire contenant les valeurs seuils pour la classification des entités de la strate arborée
    # connexion_fv_dic = {"dbname" : 'etape2', "user_db" : 'postgres', "password_db" : 'postgres', "server_db" : 'localhost', "port_number" : '5432', "schema" : 'donneelidar'}
    # treethresholds = {"seuil_surface" : 30, "seuil_compacite_1" : 0.7, "seuil_compacite_2" : 0.5, "seuil_convexite" : 0.7, "seuil_elongation" : 2.5, "val_largeur_max_alignement" : 7, "val_buffer" : 1}
    # detectInTreeStratum(connexion, 'sgts_veg4',  r'/mnt/RAM_disk/output_vectortree.gpkg', connexion_fv_dic = connexion_fv_dic, thresholds = treethresholds, save_results_as_layer = True, save_results_intermediate = True)
    # shrubthresholds = {"seuil_surface" : 5, "seuil_compacite_1" : 0.7, "seuil_compacite_2" : 0.5, "seuil_convexite" : 0.7, "seuil_elongation" : 2.5, "val_largeur_max_alignement" : 5, "val_buffer" : 1}
    # detectInShrubStratum(connexion, 'sgts_veg4',  r'/mnt/RAM_disk/output_vectorshrub.gpkg', connexion_fv_dic = connexion_fv_dic, thresholds = shrubthresholds, save_results_as_layer = True, save_results_intermediate = True)

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
    connexion_stratev_dic["schema"] = 'zonetest'

    #Création d'une base de donnée
   # createDatabase(connexion_ini_dic["dbname"], user_name=connexion_ini_dic["user_db"], password=connexion_ini_dic["password_db"], ip_host=connexion_ini_dic["server_db"], num_port=connexion_ini_dic["port_number"], schema_name=connexion_ini_dic["schema"])

    #Connexion à la base de donnée
    connexion = openConnection(connexion_ini_dic["dbname"], user_name=connexion_ini_dic["user_db"], password=connexion_ini_dic["password_db"], ip_host=connexion_ini_dic["server_db"], num_port=connexion_ini_dic["port_number"], schema_name=connexion_ini_dic["schema"])

    #Création d'un schema pour la partie classification en strates verticales
   # createSchema(connexion, 'zonetest')

    # #Connexion au schema de classification en strates verticales
    connexion = openConnection(connexion_stratev_dic["dbname"], user_name=connexion_stratev_dic["user_db"], password=connexion_stratev_dic["password_db"], ip_host=connexion_stratev_dic["server_db"], num_port=connexion_stratev_dic["port_number"], schema_name=connexion_stratev_dic["schema"])

    raster_dic = {"MNH" : r'/mnt/RAM_disk/MNH_14062022_CF.tif', "TXT" : r'/mnt/RAM_disk/img_origine_txtSFS.tif'}
   # segmentationImageVegetetation(r'/mnt/RAM_disk/ORT_ZE.tif',r'/mnt/RAM_disk/ZE_segmentation.tif', r'/mnt/RAM_disk/ZE_out_segmentation.gpkg')
    dic_seuil = {"seuil_h1" : 3, "seuil_h2" : 1, "seuil_h3" : 2, "seuil_txt" : 11, "seuil_touch_arbo_vs_herba" : 15, "seuil_ratio_surf", "seuil_arbu_repres" : 20}
    classificationVerticalStratum(connexion, connexion_stratev_dic, r'/mnt/RAM_disk/ZE_out_segmentation.gpkg', raster_dic,dic_seuil,  format_type = 'GPKG', save_intermediate_result = True, overwrite = True)
    
   ## CLASSIFICATION FORMES VEGETALES HORIZONTALES ##
    #Création d'un schema pour la partie classification en formes végétales horizontales
    # createSchema(connexion, 'classification_fv')

    # connexion_fv_dic = connexion_ini_dic
    # connexion_fv_dic["schema"] = 'classification_fv'

    # #Connexion au schema de classification en formes végétales horizontales
    # connexion = openConnection(connexion_fv_dic["dbname"], user_name=connexion_fv_dic["user_db"], password=connexion_fv_dic["password_db"], ip_host=connexion_fv_dic["server_db"], num_port=connexion_fv_dic["port_number"], schema_name=connexion_fv_dic["schema"])

    # #Initialisation du dictionnaire contenant les valeurs seuils pour la classification des entités de la strate arborée
    # treethresholds = {"seuil_surface" : 60, "seuil_compacite_1" : 0.7, "seuil_compacite_2" : 0.5, "seuil_convexite" : 0.7, "seuil_elongation" : 2.5, "val_largeur_max_alignement" : 7, "val_buffer" : 1}
    # output_tree_layer = r'/mnt/RAM_disk/treelayerfv.gpkg'
    # detectInTreeStratum(connexion, 'classification_stratev.segments_vegetation', output_tree_layer, connexion_fv_dic, treethresholds,save_results_as_layer = False, save_intermediate_results = False)
    
    # shrubthresholds = {"seuil_surface" : 5, "seuil_compacite_1" : 0.7, "seuil_compacite_2" : 0.5, "seuil_convexite" : 0.7, "seuil_elongation" : 2.5, "val_largeur_max_alignement" : 5, "val_buffer" : 1}

    # detectInShrubStratum(connexion, 'classification_stratev.segments_vegetation',  r'/mnt/RAM_disk/output_vectorshrub.gpkg', connexion_fv_dic = connexion_fv_dic, thresholds = shrubthresholds, save_results_as_layer = True, save_results_intermediate = True)
    
    ## CALCUL DES INDICATEURS DE VEGETATION ##


    #0. Préparation de la table finale de cartographie qu'on nommera "vegetation" dans un nouveau schema
#     createSchema(connexion, 'data_final')

#     connexion_data_final_dic = connexion_ini_dic
#     connexion_data_final_dic["schema"] = 'data_final'
#     connexion = openConnection(connexion_data_final_dic["dbname"], user_name=connexion_data_final_dic["user_db"], password=connexion_data_final_dic["password_db"], ip_host=connexion_data_final_dic["server_db"], num_port=connexion_data_final_dic["port_number"], schema_name=connexion_data_final_dic["schema"])

# #     query = """
# #     CREATE TABLE vegetation AS
# #         SELECT t1.geom, t1.strate, t1.fv 
# #         FROM classification_fv.strate_arboree AS t1
# #         UNION 
# #         SELECT t2.geom, t2.strate, t2.fv
# #         FROM classification_fv.strate_arbustive AS t2 
# #         UNION 
# #         SELECT t3.geom, t3.strate, t3.fv
# #         FROM classification_fv.strate_herbace AS t3; 
# #     """
# #     executeQuery(connexion, query)
# #     addUniqId(connexion, 'vegetation')

# #     addSpatialIndex(connexion, 'vegetation')
    
# #    # Création des colonnes correspondant aux indicateurs descrptifs de la végétation
# #     addColumn(connexion, 'vegetation', 'surface', 'float')
#     # addColumn(connexion, 'vegetation', 'hauteur_median', 'float')
# #     addColumn(connexion, 'vegetation', 'hauteur_std', 'float')
# #     addColumn(connexion, 'vegetation', 'hauteur_max', 'float')
# #     addColumn(connexion, 'vegetation', 'hauteur_min', 'float')
# #     addColumn(connexion, 'vegetation', 'perc_feuillu', 'float')
# #     addColumn(connexion, 'vegetation', 'perc_conifere', 'float')
# #     addColumn(connexion, 'vegetation', 'perc_persistant', 'float')
# #     addColumn(connexion, 'vegetation', 'perc_caduque', 'float')
# #     addColumn(connexion, 'vegetation', 'type_sol', 'varchar(100)')
#     # addColumn(connexion, 'vegetation', 'hauteur_mean', 'float')
#     # addColumn(connexion, 'vegetation', 'hauteur_std', 'float')
#     # areaIndicator(connexion, 'vegetation', 'surface')
#    # columnnamelist =["hauteur_max", "hauteur_min", "hauteur_mean", "hauteur_median", "hauteur_std"] 
#    # heightIndicators(connexion, connexion_data_final_dic,'vegetation', columnnamelist, r'/mnt/RAM_disk/MNH_14062022_CF.tif', r'/mnt/RAM_disk/test_indicateurs')

#    # indicatorConiferousDeciduous(connexion, connexion_data_final_dic, r'/mnt/RAM_disk/ORT_20220614_NADIR_16B_MGN_V2.tif', 'vegetation', seuil = 1300, columns_indics_name = ['perc_conifere', 'perc_feuillu'], save_intermediate_results = False)

#    # calculateSpringAndWinterNdviImage(r'/mnt/RAM_disk/ORT_20220614_NADIR_16B_MGN_V2.tif', r'/mnt/Data/20_Etudes_Encours/ENVIRONNEMENT/2022_GreenUrbanSat/0-IMAGES_SATELLITES/2021/NANCY/2021_12_21/16Bits/Assemblage_zone_etude_MGN/ORT_20211221_NADIR_16B_MGN.tif')

#    # indicatorEvergreenDeciduous(connexion, connexion_data_final_dic, r'/mnt/RAM_disk/ORT_20220614_NADIR_16B_MGN_V2.tif',r'/mnt/RAM_disk/TMP_CALC_NDVI_IMAGE/img_ndvi_printemps.tif', r'/mnt/RAM_disk/TMP_CALC_NDVI_IMAGE/img_ndvi_hiver.tif', 'vegetation', seuil = 0.10, columns_indics_name = ['perc_persistant', 'perc_caduque'], superimpose_choice = True, save_intermediate_results = False)

#     indicatorTypeofGround(connexion, connexion_data_final_dic, r'/mnt/RAM_disk/ORT_20220614_NADIR_16B_MGN_V2.tif',r'/mnt/RAM_disk/TMP_CALC_NDVI_IMAGE/img_ndvi_hiver.tif', 'vegetation', seuil  = 0.3, column_indic_name = 'type_sol', save_intermediate_results = False)