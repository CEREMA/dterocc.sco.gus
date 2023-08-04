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
from CleanCoverClasses import * 
from SampleSelectionRaster import *
from SupervisedClassification import *
from MajorityFilter import *
# from VerticalStratumDetection import *

if __name__ == "__main__":


    #Préparation du parser
    #à faire par la suite

    #Structurer un dossier qui stockera toutes les données
    
    #Création du repertoire du projet 
    repertory_prj = r'/mnt/Data/10_Agents_travaux_en_cours/Mathilde/RAMDISKDU11072023'
    path_prj = repertory_prj + os.sep + 'ProjetGUS'
    if  not os.path.exists(path_prj):
      os.makedirs(path_prj)

    #Dossier de stockage des datas
    path_data = path_prj + os.sep + '0-Data'  
    path_data_entry = path_data + os.sep + '00-DonneesEntrees'
    path_data_prod = path_data + os.sep + '01-DonneesProduites'

    if not os.path.exists(path_data):
      os.makedirs(path_data)

    if not os.path.exists(path_data_entry):
      os.makedirs(path_data_entry)

    if not os.path.exists(path_data_prod):
      os.makedirs(path_data_prod)

    # DATAS
    img_tiles_repertory = ''
    img_ref = path_data_entry + os.sep + 'img_pleiades_ref.tif'

    img_ref = r'/mnt/Data/10_Agents_travaux_en_cours/Mathilde/RAMDISKDU11072023/ProjetGUS/0-Data/00-DonneesEntrees/ORT_20220614_NADIR_16B_MGN_V2.tif'
    shp_zone = r'/mnt/Data/10_Agents_travaux_en_cours/Mathilde/RAMDISKDU11072023/ProjetGUS/0-Data/00-DonneesEntrees/MGN_contours.shp'
    
   ## PRE-TRAITEMENTS ##  
    # IMAGES ASSEMBLY
   #NB pour l'instant repertory n'est pas utilisé dans le code --> à revoir 
   # assemblyImages(repertory, img_tiles_repertory, img_ref, no_data_value, epsg, save_results_intermediate = False, ext_txt = '.txt',  format_raster = 'GTiff')

    # MNH CREATION  

   # mnh = mnhCreation(r'/mnt/RAM_disk/DSM_PRODUITS_RGE.tif', r'/mnt/Data/20_Etudes_Encours/ENVIRONNEMENT/2022_GreenUrbanSat/1-DATAS/1-DONNEES_ELEVATION/MNT/2021/NANCY/MNT_RGEALTI/MNT_RGEALTI_1M_ZONE_DE_NANCY.tif', r'/mnt/RAM_disk/MNHtest.tif', r'/mnt/RAM_disk/MGN_contours.shp', r'/mnt/RAM_disk/ORT_20220614_NADIR_16B_MGN_V2.tif',  epsg=2154, nivellement = True, format_raster = 'GTiff', format_vector = 'ESRI Shapefile',  overwrite = True, save_intermediate_results = True)

    # Stockage des données d'entrée dans un dossier : /  

    img_spring = img_ref

    # img_winter = 

   # NB : l'image PAN doit aussi être découpée à la même emprise que l'image de référence --> pour que la superposition des résultats suivant puisse se faire correctement 
    img_ref_PAN = r'/mnt/Data/10_Agents_travaux_en_cours/Mathilde/RAMDISKDU11072023/ProjetGUS/0-Data/00-DonneesEntrees/ORT_P1AP_MGN.tif'

    # img_MNS = 

    # img_MNT = 

    # CALCUL DES NEOCANAUX

   # img_neocanaux = path_data_prod + os.sep + 'img_neocanaux.tif'

    neochannels = neochannelComputation(img_ref, img_ref_PAN, path_data_prod, shp_zone, save_intermediate_results = False)
    img_MNH_ini = r'/mnt/RAM_disk/ProjetGUS/0-Data/01-DonneesProduites/MNH_14062022_CF.tif'
    img_MNH_si = r'/mnt/RAM_disk/ProjetGUS/0-Data/01-DonneesProduites/MNH_14062022_SI.tif'
    img_MNH = r'/mnt/Data/10_Agents_travaux_en_cours/Mathilde/RAMDISKDU11072023/ProjetGUS/0-Data/01-DonneesProduites/MNH_14062022.tif'

    # Si la concaténation renvoie une erreur -->il va falloir superimpose le mnh 
    # cmd_superimpose = 'otbcli_Superimpose -inr %s -inm %s -out %s' %(img_ref, img_MNH_ini, img_MNH_si)
    # exit_code = os.system(cmd_superimpose)
    # cutImageByVector(shp_zone ,img_MNH_si, img_MNH)

   # img_to_concatenate =[ img_ref, img_MNH, neochannels["ndvi"], neochannels["msavi"],neochannels["ndwi"], neochannels["hue"],neochannels["sfs"]]
   # print(img_to_concatenate) 
    
    # CONCATENATION DES NEOCANAUX
    img_stack = path_data_prod + os.sep + 'img_stack.tif'

  
   # concatenateData(img_to_concatenate, img_stack)

    ## EXTRACTION DE LA VEGETATION PAR CLASSIFICATION SUPERVISEE ## 
     #Dossier de stockage des datas
    path_extractveg = path_prj + os.sep + '1-ExtractionVegetation'  

    if not os.path.exists(path_extractveg):
      os.makedirs(path_extractveg)

    path_tmp_preparesamples = path_extractveg + os.sep + 'TMP_PREPARE_SAMPLE'

    if not os.path.exists(path_tmp_preparesamples):
      os.makedirs(path_tmp_preparesamples)

    path_tmp_cleansamples = path_extractveg + os.sep + 'TMP_CLEAN_SAMPLE'

    if not os.path.exists(path_tmp_cleansamples):
      os.makedirs(path_tmp_cleansamples)

    path_tmp_selectsamples = path_extractveg + os.sep + 'TMP_SELECT_SAMPLE'

    if not os.path.exists(path_tmp_selectsamples):
      os.makedirs(path_tmp_selectsamples)

    #1# Création des échantillons d'apprentissage
    #Fournir 5 couches vectorielles
    bati = path_data_entry + os.sep + 'bati_vector.shp'
    route =  path_data_entry + os.sep + 'route_vector.shp'
    solnu =  path_data_entry + os.sep + 'solnu_vector.shp'
    eau =  path_data_entry + os.sep + 'eau_vector.shp'
    vegetation =  path_data_entry + os.sep + 'vegetation_vector.shp'

    bati_prepare = path_tmp_preparesamples + os.sep + 'bati_vector_prepare.tif'
    route_prepare = path_tmp_preparesamples + os.sep + 'route_vector_prepare.tif'
    solnu_prepare = path_tmp_preparesamples + os.sep + 'solnu_vector_prepare.tif'
    eau_prepare = path_tmp_preparesamples + os.sep + 'eau_vector_prepare.tif'
    vegetation_prepare = path_tmp_preparesamples + os.sep + 'vegetation_vector_prepare.tif'

    bati_clean = path_tmp_cleansamples + os.sep + 'bati_vector_clean.tif'
    route_clean = path_tmp_cleansamples + os.sep + 'route_vector_clean.tif'
    solnu_clean = path_tmp_cleansamples + os.sep + 'solnu_vector_clean.tif'
    eau_clean = path_tmp_cleansamples + os.sep + 'eau_vector_clean.tif'
    vegetation_clean = path_tmp_cleansamples + os.sep + 'vegetation_vector_clean.tif'

    image_samples_merged_output = path_tmp_cleansamples + os.sep + 'img_samples_merged.tif'

    samplevector = path_tmp_selectsamples + os.sep + 'sample_vector_selected.shp'
    table_statistics_output = path_tmp_selectsamples + os.sep + 'statistics_sample_vector_selected.csv'

    img_classif = path_extractveg + os.sep + 'img_classification.tif'
    img_classif_confid = path_extractveg + os.sep + 'img_classification_confidence.tif'

    img_classif_filtered = path_extractveg + os.sep + 'img_classification_filtered.tif'

    #2# Préparation des échantillons d'apprentissage
    # macroSamplesPrepare(img_ref, bati, bati_prepare, shp_zone, erosionoption = True, format_vector='ESRI Shapefile')
    # macroSamplesPrepare(img_ref, route, route_prepare, shp_zone, erosionoption = False, format_vector='ESRI Shapefile')
    # macroSamplesPrepare(img_ref, solnu, solnu_prepare, shp_zone, erosionoption = True, format_vector='ESRI Shapefile')
    # macroSamplesPrepare(img_ref, eau, eau_prepare, shp_zone, erosionoption = True, format_vector='ESRI Shapefile')
    # macroSamplesPrepare(img_ref, vegetation, vegetation_prepare, shp_zone, erosionoption = True, format_vector='ESRI Shapefile')
    
    #3# Nettoyage des échantillons d'apprentissage : érosion + filtrage avec les néocanaux
    # corr_bati = {"ndvi" : [neochannels["ndvi"] ,0, 0.35]}
    # macroSamplesClean(bati_prepare, bati_clean, corr_bati)

    # corr_route = {"ndvi":  [neochannels["ndvi"], 0, 0.35]}
    # macroSamplesClean(route_prepare,route_clean, corr_route)

    # corr_solnu = {"ndvi" : [neochannels["ndvi"], 0, 0.2], "hue" :[neochannels["hue"],0,50] }
    # macroSamplesClean(solnu_prepare, solnu_clean, corr_solnu)

    # corr_eau = {"ndwi" :[neochannels["ndwi"],-500,1] }
    # macroSamplesClean(eau_prepare, eau_clean, corr_eau)

    # corr_vegetation = {"ndvi" : [neochannels["ndvi"], 0.35, 1], "msavi" : [neochannels["msavi"],0.4,1] }
    # macroSamplesClean(vegetation_prepare , vegetation_clean, corr_vegetation)

   # mask_samples_macro_input_list = [bati_clean, route_clean, solnu_clean, eau_clean, vegetation_clean]
    
    #4# Nettoyage recouvrement des échantillons d'apprentissage
   # cleanCoverClasses(img_ref, mask_samples_macro_input_list, image_samples_merged_output)
    
    #5# Sélection des échantillons

   # selectSamples([img_stack], image_samples_merged_output, samplevector, table_statistics_output, sampler_strategy="percent", select_ratio_floor = 10, ratio_per_class_dico = {1:1.37,2:3.40,3:100,4:0.37,5:0.84}, name_column = 'ROI', no_data_value = 0)
    

    #6# Classification supervisée RF
    depth_tree = 50
    sample_min = 20
    termin_criteria = 0.0
    cluster = 30
    size_features = 2
    num_tree = 50
    obb_erreur = 0.001

    rf_parametres_struct = StructRFParameter()
    rf_parametres_struct.max_depth_tree = depth_tree
    rf_parametres_struct.min_sample = sample_min
    rf_parametres_struct.ra_termin_criteria = termin_criteria
    rf_parametres_struct.cat_clusters = cluster
    rf_parametres_struct.var_size_features = size_features
    rf_parametres_struct.nbtrees_max =  num_tree
    rf_parametres_struct.acc_obb_erreur = obb_erreur

   # classifySupervised([img_stack], samplevector, img_classif, img_classif_confid, model_output = '', model_input = '', field_class = 'ROI', classifier_mode = "rf", rf_parametres_struct = rf_parametres_struct,no_data_value = 0, ram_otb=0,  format_raster='GTiff', extension_vector=".shp")
    
    #7# Application du filtre majoritaire   
    filterImageMajority(img_classif, img_classif_filtered, umc_pixels = 8) 
    
    #Suppression des dossiers temporaires si souhaité
    # if os.path.exists():
    #   remove() 
    
    # # Segmentation de l'image
    # segmentationImageVegetetation(r'/mnt/RAM_disk/ORT_ZE.tif',r'/mnt/RAM_disk/ZE_segmentation.tif', r'/mnt/RAM_disk/ZE_out_segmentation.gpkg')


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
    # connexion = openConnection(connexion_stratev_dic["dbname"], user_name=connexion_stratev_dic["user_db"], password=connexion_stratev_dic["password_db"], ip_host=connexion_stratev_dic["server_db"], num_port=connexion_stratev_dic["port_number"], schema_name=connexion_stratev_dic["schema"])

    # raster_dic = {"MNH" : r'/mnt/RAM_disk/MNH_14062022_CF.tif', "TXT" : r'/mnt/RAM_disk/img_origine_txtSFS.tif'}
    # classificationVerticalStratum(connexion, connexion_stratev_dic, r'/mnt/RAM_disk/ZE_out_segmentation.gpkg', raster_dic, format_type = 'GPKG', save_intermediate_result = True, overwrite = True)
    # #Test la version de postgres
    # postgresversion = versionPostgreSQL(database_name='postgres', user_name='postgres', password='postgres', ip_host='localhost', num_port='5432', schema_name='')

    # #Test la version de postgis
    # postgisversion = versionPostGIS(database_name='template_postgis', user_name='postgres', password='postgres', ip_host='localhost', num_port='5432', schema_name='')


    # # # Classification en formes végétales horizontales

    #Création d'un schema pour la partie classification en formes végétales horizontales
    #createSchema(connexion, 'classification_fv')

    #Connexion au schema de classification en strates verticales

    #Strate arborée
    #connexion = openConnection('etape2', user_name='postgres', password="", ip_host='localhost', num_port='5432', schema_name='donneelidar')

    # #Initialisation du dictionnaire contenant les valeurs seuils pour la classification des entités de la strate arborée
    #treethresholds = {"seuil_surface" : 5, "seuil_compacite_1" : 0.7, "seuil_compacite_2" : 0.5, "seuil_convexite" : 0.7, "seuil_elongation" : 2.5, "val_largeur_max_alignement" : 5, "val_buffer" : 1}

    #detectInTreeStratum(connexion, tablename, treethresholds, output_tree_layer, connexion_fv_dic, save_results_as_layer = False, save_intermediate_results = False)
    #connexion_fv_dic = {"dbname" : 'etape2', "user_db" : 'postgres', "password_db" : "", "server_db" : 'localhost', "port_number" : '5432', "schema" : 'donneelidar'}
    #detectInShrubStratum(connexion, 'sgts_veg4',  r'/mnt/RAM_disk/output_vectorshrub.gpkg', connexion_fv_dic = connexion_fv_dic, thresholds = treethresholds, save_results_as_layer = True, save_intermediate_results = True)

    #Calcul des indicateurs de végétation

   #0. Préparation de la table finale de cartographie qu'on nommera "vegetation" dans un nouveau schema
   # createSchema(connexion, 'data_final')
  #  connexion = openConnection('etape2', user_name='postgres', password="", ip_host='localhost', num_port='5432', schema_name='donneelidar')

    query = """
    CREATE TABLE vegetation AS
        SELECT t1.geom, t1.strate, t1.fv 
        FROM classification_fv.strate_arboree AS t1
        UNION 
        SELECT t2.geom, t2.strate, t2.fv
        FROM classification_fv.strate_arbustive AS t2 
        UNION 
        SELECT t3.geom, t3.strate, t3.fv
        FROM classification_fv.strate_herbacee AS t3; 
    """

  #   addUniqId(connexion, 'vegetation')

  #   addSpatialIndex(connexion, 'vegetation')
    
  #  # Création des colonnes correspondant aux indicateurs descrptifs de la végétation
  #  addColumn(connexion, 'vegetation', 'surface', 'float')
  #  addColumn(connexion, 'vegetation', 'hauteur_med', 'float')
  #  addColumn(connexion, 'vegetation', 'hauteur_et', 'float')
  #  addColumn(connexion, 'vegetation', 'hauteur_max', 'float')
  #  addColumn(connexion, 'vegetation', 'hauteur_min', 'float')
  #  addColumn(connexion, 'vegetation', 'perc_feuillu', 'float')
  #  addColumn(connexion, 'vegetation', 'perc_conifere', 'float')
  #  addColumn(connexion, 'vegetation', 'perc_persistant', 'float')
  #  addColumn(connexion, 'vegetation', 'perc_caduque', 'float')
  #  addColumn(connexion, 'vegetation', 'type_sol', 'varchar(100)')




