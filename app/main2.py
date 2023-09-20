# from MnhCreation import mnhCreation
# from NeochannelComputation_gus import neochannelComputation
# from DataConcatenation import concatenateData
# #from ImagesAssemblyGUS_ok import cutImageByVector
from Lib_postgis import *
# from DetectVegetationFormStratumV1 import *
# from Lib_vector import *
import sys,os,glob
# from osgeo import ogr ,osr
# from MacroSampleCreation import *
from VerticalStratumDetection import *
from DetectVegetationFormStratumV1 import *
from IndicateursComputation import *

if __name__ == "__main__":
    
   #Lancer sur zone test : classification 
   ## DISTINCTION DES STRATES VERTICALES DE VÉGÉTATION ##

#     img_classif_filtered = r'/mnt/RAM_disk/ZoneTest/img_classifiee.tif'

#     img_ref = r'/mnt/RAM_disk/ZoneTest/img_ref.tif'

#     img_segt_veg = r'/mnt/RAM_disk/ZoneTest/img_sgt_vegetation.gpkg' 

#     img_stratesV = r'/mnt/RAM_disk/ZoneTest/img_stratesV.gpkg' 

    
#     #1# Segmentation de l'image
#     #Paramétrage
#     num_class = {"bati" : 1, "route" : 2, "sol nu" : 3, "eau" : 4, "vegetation" : 5}  
#     minsize = 10
#    # segmentationImageVegetetation(img_ref, img_classif_filtered, img_segt_veg, param_minsize = minsize, num_class = num_class, format_vector='GPKG', save_intermediate_result = True, overwrite = False)

    #2# Classification en strates verticales
    ## INITIALISATION POUR CONNEXION AU SERVEUR

    #Paramètres de connexion de base  
    dbname = 'projetgus'
    user_db = 'postgres'
    password_db = ''
    server_db = 'localhost'
    port_number = '5432'
    schema = ''

    connexion_ini_dic = {"dbname" : 'projetgus', "user_db" : 'postgres', "password_db" : 'postgres', "server_db" : 'localhost', "port_number" : '5432', "schema" : ''}

#     #Paramètres de connexion au schema de distinction des strates verticales de végétation 
#     connexion_stratev_dic = connexion_ini_dic
#     connexion_stratev_dic["schema"] = 'test_classv'

#     #connexion_fv_dic = connexion_ini_dic
#     #connexion_fv_dic["schema"] = 'classification_fv'

#     #Création d'une base de donnée
#     #createDatabase(connexion_ini_dic["dbname"], user_name=connexion_ini_dic["user_db"], password=connexion_ini_dic["password_db"], ip_host=connexion_ini_dic["server_db"], num_port=connexion_ini_dic["port_number"], schema_name=connexion_ini_dic["schema"])

#     #Connexion à la base de donnée
    # connexion = openConnection(connexion_ini_dic["dbname"], user_name=connexion_ini_dic["user_db"], password=connexion_ini_dic["password_db"], ip_host=connexion_ini_dic["server_db"], num_port=connexion_ini_dic["port_number"], schema_name=connexion_ini_dic["schema"])
    
#     #Création d'un schema pour la partie classification en strates verticales
#     createSchema(connexion, 'test_classv')

#     closeConnection(connexion)

#     #Connexion au schema de classification en strates verticales
#     connexion = openConnection(connexion_stratev_dic["dbname"], user_name=connexion_stratev_dic["user_db"], password=connexion_stratev_dic["password_db"], ip_host=connexion_stratev_dic["server_db"], num_port=connexion_stratev_dic["port_number"], schema_name=connexion_stratev_dic["schema"])

#     img_txt_SFS = r'/mnt/RAM_disk/ProjetGUS/0-Data/01-DonneesProduites/ORT_20220614_NADIR_16B_MGN_V2_txtSFS.tif'
#     img_MNH = r'/mnt/RAM_disk/ProjetGUS/0-Data/01-DonneesProduites/mnh.tif'

#     raster_dic = {"MNH" : img_MNH, "TXT" : img_txt_SFS}
#     classificationVerticalStratum(connexion, connexion_stratev_dic, img_stratesV, img_segt_veg, raster_dic, tab_ref = 'segments_vegetation',dic_seuil = {"seuil_h1" : 3, "seuil_h2" : 1, "seuil_h3" : 2, "seuil_txt" : 11, "seuil_touch_arbo_vs_herba" : 15, "seuil_ratio_surf" : 25, "seuil_arbu_repres" : 20}, format_type = 'GPKG', save_results_as_layer = True, save_intermediate_result = False, overwrite = True)
     

    ## CLASSIFICATION FORMES VEGETALES HORIZONTALES ##

    #Connexion à la base de donnée
   # connexion = openConnection(connexion_ini_dic["dbname"], user_name=connexion_ini_dic["user_db"], password=connexion_ini_dic["password_db"], ip_host=connexion_ini_dic["server_db"], num_port=connexion_ini_dic["port_number"], schema_name=connexion_ini_dic["schema"])
    

    #Création d'un schema pour la partie classification en formes végétales horizontales
   # createSchema(connexion, 'test_classfv')

    connexion_fv_dic = connexion_ini_dic
    connexion_fv_dic["schema"] = 'test_classfv'

    #Connexion au schema de classification en formes végétales horizontales
  #  connexion = openConnection(connexion_fv_dic["dbname"], user_name=connexion_fv_dic["user_db"], password=connexion_fv_dic["password_db"], ip_host=connexion_fv_dic["server_db"], num_port=connexion_fv_dic["port_number"], schema_name=connexion_fv_dic["schema"])

    #Initialisation du dictionnaire contenant les valeurs seuils pour la classification des entités de la strate arborée
    # treethresholds = {"seuil_surface" : 60, "seuil_compacite_1" : 0.7, "seuil_compacite_2" : 0.5, "seuil_convexite" : 0.7, "seuil_elongation" : 2.5, "val_largeur_max_alignement" : 7, "val_buffer" : 1}
    # output_tree_layer = r'/mnt/RAM_disk/treelayerfv.gpkg'
    # detectInTreeStratum(connexion, 'test_classv.segments_vegetation', output_tree_layer, connexion_fv_dic, treethresholds,save_results_as_layer = False, save_intermediate_results = False)
    # shrubthresholds = {"seuil_surface" : 5, "seuil_compacite_1" : 0.7, "seuil_compacite_2" : 0.5, "seuil_convexite" : 0.7, "seuil_elongation" : 2.5, "val_largeur_max_alignement" : 5, "val_buffer" : 1}

    # detectInShrubStratum(connexion, 'test_classv.segments_vegetation',  r'/mnt/RAM_disk/output_vectorshrub.gpkg', connexion_fv_dic = connexion_fv_dic, thresholds = shrubthresholds, save_results_as_layer = True, save_intermediate_results = False)
    
   # detectInHerbaceousStratum(connexion, 'test_classv.segments_vegetation', r'/mnt/RAM_disk/output_vectorherbaceous.gpkg', connexion_fv_dic = connexion_fv_dic, save_results_as_layer = False, save_intermediate_results = False)
   # connexion = openConnection(connexion_ini_dic["dbname"], user_name=connexion_ini_dic["user_db"], password=connexion_ini_dic["password_db"], ip_host=connexion_ini_dic["server_db"], num_port=connexion_ini_dic["port_number"], schema_name=connexion_ini_dic["schema"])

   # createSchema(connexion, 'test_data_final')

    connexion_data_final_dic = connexion_ini_dic
    connexion_data_final_dic["schema"] = 'test_data_final'
    connexion = openConnection(connexion_data_final_dic["dbname"], user_name=connexion_data_final_dic["user_db"], password=connexion_data_final_dic["password_db"], ip_host=connexion_data_final_dic["server_db"], num_port=connexion_data_final_dic["port_number"], schema_name=connexion_data_final_dic["schema"])

    #cartographyVegetation(connexion, 'test_classfv.strate_arboree', 'test_classfv.strate_arbustive', 'test_classfv.herbace', r'/mnt/RAM_disk/output_dataFV.gpkg', connexion_data_final_dic)
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

    # addSpatialIndex(connexion, 'vegetation')

    # # Création des colonnes correspondant aux indicateurs descrptifs de la végétation
    # addColumn(connexion, 'vegetation', 'paysage', 'varchar(100)')
    # addColumn(connexion, 'vegetation', 'surface', 'float')
    # addColumn(connexion, 'vegetation', 'h_moy', 'float')
    # addColumn(connexion, 'vegetation', 'h_med', 'float')
    # addColumn(connexion, 'vegetation', 'h_et', 'float')
    # addColumn(connexion, 'vegetation', 'h_min', 'float')
    # addColumn(connexion, 'vegetation', 'h_max', 'float')
    # addColumn(connexion, 'vegetation', 'perc_feuillu', 'float')
    # addColumn(connexion, 'vegetation', 'perc_conifere', 'float')
    # addColumn(connexion, 'vegetation', 'perc_persistant', 'float')
    # addColumn(connexion, 'vegetation', 'perc_caduque', 'float')
    # addColumn(connexion, 'vegetation', 'type_sol', 'varchar(100)')
    # addColumn(connexion, 'vegetation', 'idc_surface', 'float')
    # addColumn(connexion, 'vegetation', 'idc_h', 'float')
    # addColumn(connexion, 'vegetation', 'idc_percfeuilluconifere', 'float')
    # addColumn(connexion, 'vegetation', 'idc_persistantcaduque', 'float')
    # addColumn(connexion, 'vegetation', 'idc_typesol', 'float')
    
    # Calcul des attributs 

    repertory = r'/mnt/RAM_disk/ProjetGUS/5-Cartographie_finale'

    if not os.path.exists(repertory):
        os.makedirs(repertory)

    img_mnh = r'/mnt/RAM_disk/ProjetGUS/0-Data/01-DonneesProduites/mnh.tif'
    img_spg = r'/mnt/RAM_disk/ProjetGUS/0-Data/00-DonneesEntrees/ORT_20220614_NADIR_16B_MGN_V2.tif'
    img_wtr = r'/mnt/Data/20_Etudes_Encours/ENVIRONNEMENT/2022_GreenUrbanSat/0-IMAGES_SATELLITES/2021/NANCY/2021_12_21/16Bits/Assemblage_zone_etude_MGN/ORT_20211221_NADIR_16B_MGN.tif'
    
   # areaIndicator(connexion, 'vegetation', 'surface')

   # columnnamelist =["h_moy", "h_med", "h_et", "h_min", "h_max"] 
   # dropColumn(connexion, 'vegetation', 'fid')
   # addUniqId(connexion, 'vegetation')
   # heightIndicators(connexion, connexion_data_final_dic, 'vegetation', columnnamelist, img_mnh, repertory = repertory, save_intermediate_result = False)

    indicatorConiferousDeciduous(connexion, connexion_data_final_dic, img_spg, 'vegetation', seuil = 1300, columns_indics_name = ['perc_conifere', 'perc_feuillu'], repertory = repertory,save_intermediate_results = False)
    
    img_ndvi_spg, img_ndvi_wtr = calculateSpringAndWinterNdviImage(img_spg, img_wtr, repertory = repertory)
    
    indicatorEvergreenDeciduous(connexion, connexion_data_final_dic, img_spg,img_ndvi_spg, img_ndvi_wtr, 'vegetation', seuil = 0.10, columns_indics_name = ['perc_persistant', 'perc_caduque'], superimpose_choice = True, repertory = repertory, save_intermediate_results = False)

    indicatorTypeofGround(connexion, connexion_data_final_dic, img_spg, img_ndvi_wtr, 'vegetation', seuil  = 0.3, column_indic_name = 'type_sol', repertory = repertory, save_intermediate_results = False)
    # indicatorTypeofGround(connexion, connexion_data_final_dic, r'/mnt/RAM_disk/ORT_20220614_NADIR_16B_MGN_V2.tif',r'/mnt/RAM_disk/TMP_CALC_NDVI_IMAGE/img_ndvi_hiver.tif', 'vegetation', seuil  = 0.3, column_indic_name = 'type_sol', save_intermediate_results = False)



