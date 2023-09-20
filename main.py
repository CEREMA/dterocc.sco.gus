from libs.Lib_display import bold,black,red,green,yellow,cyan,magenta,cyan,endC,displayIHM
from app.MnhCreation import mnhCreation
from app.NeochannelComputation_gus import neochannelComputation
from app.DataConcatenation import concatenateData
#from ImagesAssemblyGUS_ok import cutImageByVector
from libs.Lib_postgis import *
#from DetectVegetationFormStratumV1 import *
from libs.Lib_vector import *
import sys,os,glob
from osgeo import ogr ,osr
from app.SampleCreation import *
from app.CleanCoverClasses import * 
from app.SampleSelectionRaster import *
from app.SupervisedClassification import *
from app.MajorityFilter import *
from app.VerticalStratumDetection import *

if __name__ == "__main__":

    debug = 1
    #Préparation du parser
    #à faire par la suite
    print(bold + cyan + "*********************************************** \n*** Cartographie détaillée de la végétation *** \n***********************************************" + endC)

    #Structurer un dossier qui stockera toutes les données
    #Création du repertoire du projet 
    repertory_prj = r'/mnt/RAM_disk'
    path_prj = repertory_prj + os.sep + 'ProjetGUS'
    if  not os.path.exists(path_prj):
      os.makedirs(path_prj)

    #Dossier de stockage des datas
    path_data = path_prj + os.sep + '0-Data'  
    path_data_entry = path_data + os.sep + '00-DonneesEntrees'
    path_data_prod = path_data + os.sep + '01-DonneesProduites'

    # if not os.path.exists(path_data):
    #   os.makedirs(path_data)

    # if not os.path.exists(path_data_entry):
    #   os.makedirs(path_data_entry)

    # if not os.path.exists(path_data_prod):
    #   os.makedirs(path_data_prod)

    if debug >= 1:
      print(bold + cyan + "\nCréation structure du dossier de projet" + endC)
      print("Répertoire : " + repertory_prj)

    # DATAS
    img_tiles_repertory = ''
    img_ref = path_data_entry + os.sep + 'img_pleiades_ref.tif'

    img_ref = r'/mnt/Data/10_Agents_travaux_en_cours/Mathilde/RAMDISKDU11072023/ProjetGUS/0-Data/00-DonneesEntrees/ORT_20220614_NADIR_16B_MGN_V2.tif'
    shp_zone = r'/mnt/Data/10_Agents_travaux_en_cours/Mathilde/RAMDISKDU11072023/ProjetGUS/0-Data/00-DonneesEntrees/MGN_contours.shp'
    
   ## PRE-TRAITEMENTS ##  
    if debug >= 1:
      print(bold + cyan + "\n*0* PRÉ-TRAITEMENTS" + endC)
    # IMAGES ASSEMBLY
    if debug >= 1:
      print(cyan + "\nAssemblage des imagettes" + endC)
   #NB pour l'instant repertory n'est pas utilisé dans le code --> à revoir 
   # assemblyImages(repertory, img_tiles_repertory, img_ref, no_data_value, epsg, save_results_intermediate = False, ext_txt = '.txt',  format_raster = 'GTiff')

    # MNH CREATION  
    if debug >= 1:
      print(cyan + "\nCréation du MNH" + endC)

    img_mnt =  r'/mnt/Data/20_Etudes_Encours/ENVIRONNEMENT/2022_GreenUrbanSat/1-DATAS/1-DONNEES_ELEVATION/MNT/2021/NANCY/MNT_RGEALTI/MNT_RGEALTI_1M_ZONE_DE_NANCY.tif'
    img_mns = r'/mnt/Data/20_Etudes_Encours/ENVIRONNEMENT/2022_GreenUrbanSat/1-DATAS/1-DONNEES_ELEVATION/MNS/2022/NANCY/2022_06_14/MNSCARS/DSM_PRODUITS_RGE.tif'
    img_mnh = path_data_prod + os.sep + 'mnh.tif'
    
   # img_MNH = mnhCreation(img_mns, img_mnt, img_mnh, shp_zone , img_ref,  epsg=2154, nivellement = True, format_raster = 'GTiff', format_vector = 'ESRI Shapefile',  overwrite = True, save_intermediate_results = True)
    img_MNH = img_mnh
    # Stockage des données d'entrée dans un dossier : /  

    img_spring = img_ref

    # img_winter = 

   # NB : l'image PAN doit aussi être découpée à la même emprise que l'image de référence --> pour que la superposition des résultats suivant puisse se faire correctement 
    img_ref_PAN = r'/mnt/Data/10_Agents_travaux_en_cours/Mathilde/RAMDISKDU11072023/ProjetGUS/0-Data/00-DonneesEntrees/ORT_P1AP_MGN.tif'

    # CALCUL DES NEOCANAUX
    if debug >= 1:
      print(cyan + "\nCalcul des néocanaux" + endC)
   # img_neocanaux = path_data_prod + os.sep + 'img_neocanaux.tif'

   # neochannels = neochannelComputation(img_ref, img_ref_PAN, path_data_prod, shp_zone, save_intermediate_results = False)

  #   # Si la concaténation renvoie une erreur -->il va falloir superimpose le mnh 
  #   # cmd_superimpose = 'otbcli_Superimpose -inr %s -inm %s -out %s' %(img_ref, img_MNH_ini, img_MNH_si)
  #   # exit_code = os.system(cmd_superimpose)
  #   # cutImageByVector(shp_zone ,img_MNH_si, img_MNH)

    #en attendant
  #   neochannels ={
  #     "ndvi" : r'/mnt/RAM_disk/ProjetGUS/0-Data/01-DonneesProduites/TMP_NEOCHANNELSCOMPUTATION/ORT_20220614_NADIR_16B_MGN_V2_ndvi.tif',
  #     "msavi" : r'/mnt/RAM_disk/ProjetGUS/0-Data/01-DonneesProduites/TMP_NEOCHANNELSCOMPUTATION/ORT_20220614_NADIR_16B_MGN_V2_msavi2.tif',
  #     "ndwi" : r'/mnt/RAM_disk/ProjetGUS/0-Data/01-DonneesProduites/TMP_NEOCHANNELSCOMPUTATION/ORT_20220614_NADIR_16B_MGN_V2_ndwi2.tif',
  #     "hue" : r'/mnt/RAM_disk/ProjetGUS/0-Data/01-DonneesProduites/TMP_NEOCHANNELSCOMPUTATION/ORT_20220614_NADIR_16B_MGN_V2_hue.tif',
  #     "sfs" : r'/mnt/RAM_disk/ProjetGUS/0-Data/01-DonneesProduites/TMP_NEOCHANNELSCOMPUTATION/ORT_20220614_NADIR_16B_MGN_V2_txtSFS.tif'
  #    }  

   # img_to_concatenate =[ img_ref, img_MNH, neochannels["ndvi"], neochannels["msavi"],neochannels["ndwi"], neochannels["hue"],neochannels["sfs"]]
     
    
  #   # CONCATENATION DES NEOCANAUX
    if debug >= 1:
      print(cyan + "\nConcaténation des néocanaux" + endC)

    img_stack = path_data_prod + os.sep + 'img_stack.tif'

  
 #  concatenateData(img_to_concatenate, img_stack)

  #   ## EXTRACTION DE LA VEGETATION PAR CLASSIFICATION SUPERVISEE ## 
    if debug >= 1:
      print(bold + cyan + "\n*1* EXTRACTION DE LA VÉGÉTATION" + endC)

  #    #Dossier de stockage des datas
    path_extractveg = path_prj + os.sep + '1-ExtractionVegetation'  

  #   # if not os.path.exists(path_extractveg):
  #   #   os.makedirs(path_extractveg)    

  #   # path_tmp_preparesamples = path_extractveg + os.sep + 'TMP_PREPARE_SAMPLE'

  #   # if not os.path.exists(path_tmp_preparesamples):
  #   #   os.makedirs(path_tmp_preparesamples)

    path_tmp_cleansamples = path_extractveg + os.sep + 'TMP_CLEAN_SAMPLE'

  #   # if not os.path.exists(path_tmp_cleansamples):
  #   #   os.makedirs(path_tmp_cleansamples)

    path_tmp_selectsamples = path_extractveg + os.sep + 'TMP_SELECT_SAMPLE'

  #   # if not os.path.exists(path_tmp_selectsamples):
  #   #   os.makedirs(path_tmp_selectsamples)

  #   #1# Création des échantillons d'apprentissage
    if debug >= 1:
      print(cyan + "\nCréation des échantillons d'apprentissage" + endC) 
  #   #Fournir 5 couches vectorielles
  #   # bati = path_data_entry + os.sep + 'bati_vector.shp'
  #   # route =  path_data_entry + os.sep + 'route_vector.shp'
  #   # solnu =  path_data_entry + os.sep + 'solnu_vector.shp'
  #   # eau =  path_data_entry + os.sep + 'eau_vector.shp'
  #   # vegetation =  path_data_entry + os.sep + 'vegetation_vector.shp'

  #   # bati_prepare = path_tmp_preparesamples + os.sep + 'bati_vector_prepare.tif'
  #   # route_prepare = path_tmp_preparesamples + os.sep + 'route_vector_prepare.tif'
  #   # solnu_prepare = path_tmp_preparesamples + os.sep + 'solnu_vector_prepare.tif'
  #   # eau_prepare = path_tmp_preparesamples + os.sep + 'eau_vector_prepare.tif'
  #   # vegetation_prepare = path_tmp_preparesamples + os.sep + 'vegetation_vector_prepare.tif'

  #   # bati_clean = path_tmp_cleansamples + os.sep + 'bati_vector_clean.tif'
  #   # route_clean = path_tmp_cleansamples + os.sep + 'route_vector_clean.tif'
  #   # solnu_clean = path_tmp_cleansamples + os.sep + 'solnu_vector_clean.tif'
  #   # eau_clean = path_tmp_cleansamples + os.sep + 'eau_vector_clean.tif'
  #   # vegetation_clean = path_tmp_cleansamples + os.sep + 'vegetation_vector_clean.tif'

    image_samples_merged_output = path_tmp_cleansamples + os.sep + 'img_samples_merged.tif'

    samplevector = path_tmp_selectsamples + os.sep + 'sample_vector_selected.shp'
    table_statistics_output = path_tmp_selectsamples + os.sep + 'statistics_sample_vector_selected.csv'

    img_classif = path_extractveg + os.sep + 'img_classification.tif'
    img_classif_confid = path_extractveg + os.sep + 'img_classification_confidence.tif'

    img_classif_filtered = path_extractveg + os.sep + 'img_classification_filtered.tif'

    # vectors_samples_output ={
    #   "bati" : ,
    #   "route" : ,
    #   "solnu" : ,
    #   "eau" : ,
    #   "vegetation" :
    # }  
    # rasters_samples_output ={
    #   "bati" : '',
    #   "route" : '',
    #   "solnu" : '',
    #   "eau" : '',
    #   "vegetation" : ''
    # }
    # params_to_find_samples = {
    #   "bati" : ['',,],
    #   "route" : ['',,],
    #   "solnu" : ['',,],
    #   "eau" : ['',,],
    #   "vegetation" : ['',,]
    # } 

    # createAllSamples(img_ref, shp_zone, vectors_samples_output, rasters_samples_output, params_to_find_samples, simplify_vector_param=10.0, format_vector='ESRI Shapefile', extension_vector=".shp", save_results_intermediate=False, overwrite=True)


  #   #2# Préparation des échantillons d'apprentissage
    if debug >= 1:
      print(cyan + "\nPréparation des échantillons d'apprentissage" + endC) 

    # #Dictionnaire des paramètres de préparation des échantillons d'apprentissage
    # dic_preparesamples ={
    #   "bati" :[bati, bati_prepare, True],
    #   "route" : [route, route_prepare, False],
    #   "sol nu" : [solnu, solnu_prepare, True],
    #   "eau" : [eau, eau_prepare, True],
    #   "vegetation" : [vegetation, vegetation_prepare, True]  
    # } 

    # prepareAllSamples(img_ref, dic_preparesamples, shp_zone, format_vector = 'ESRI Shapefile')
 
  #   #3# Nettoyage des échantillons d'apprentissage : érosion + filtrage avec les néocanaux
    if debug >= 1:
      print(cyan + "\nNettoyage des échantillons d'apprentissage" + endC) 

      # images_in_output = {
      #   "bâti" : [bati_prepare, bati_clean],
      #   "route" : [route_prepare, route_clean],
      #   "solnu" : [solnu_prepare, solnu_clean],
      #   "eau" : [eau_prepare, eau_clean],
      #   "vegetation" : [vegetation_prepare, vegetation_clean]     
      # } 

      # correction_images_dic = {
      #   "bâti" :[["ndvi", neochannels["ndvi"] ,0, 0.35]],
      #   "route" : [["ndvi", neochannels["ndvi"] ,0, 0.35]],
      #   "solnu" : [["ndvi", neochannels["ndvi"] ,0, 0.2], ["hue", neochannels["hue"], 0, 50]],
      #   "eau" : [["ndwi", neochannels["ndwi"], -500, 1]],
      #   "vegetation" : [["ndvi", neochannels["ndvi"] ,0.35,1], ["msavi", neochannels["msavi"] ,0.4,1]]
      # } 

      # cleanAllSamples(images_in_output, correction_images_dic, extension_raster = ".tif", save_results_intermediate = False, overwrite = False)

  #  # mask_samples_input_list = [bati_clean, route_clean, solnu_clean, eau_clean, vegetation_clean]
    
  #   #4# Nettoyage recouvrement des échantillons d'apprentissage
    if debug >= 1:
      print(cyan + "\nCorrection du recouvrement des échantillons d'apprentissage" + endC) 
  #  # cleanCoverClasses(img_ref, mask_samples_input_list, image_samples_merged_output)
    
  #   #5# Sélection des échantillons
    if debug >= 1:
      print(cyan + "\nSélection des échantillons d'apprentissage" + endC) 

   # selectSamples([img_stack], image_samples_merged_output, samplevector, table_statistics_output, sampler_strategy="percent", select_ratio_floor = 10, ratio_per_class_dico = {1:1.37,2:3.40,3:100,4:0.37,5:0.84}, name_column = 'ROI', no_data_value = 0)
    

    #6# Classification supervisée RF
    if debug >= 1:
      print(cyan + "\nClassification supervisée RF" + endC)

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

   # classifySupervised([img_stack], samplevector, img_classif, '', model_output = '', model_input = '', field_class = 'ROI', classifier_mode = "rf", rf_parametres_struct = rf_parametres_struct,no_data_value = 0, ram_otb=0,  format_raster='GTiff', extension_vector=".shp")
    
    #7# Application du filtre majoritaire 
    if debug >= 1:
      print(cyan + "\nApplication du filtre majoritaire" + endC)  
  #  filterImageMajority(img_classif, img_classif_filtered, umc_pixels = 8) 
    

    ## CREATION ET PREPARATION DE LA BASE DE DONNEES ##  
    if debug >= 1:
      print(bold + cyan + "\nCréation de la base de données " + endC)

    #Paramètres de connexion 
    dbname = 'gus'
    user_db = 'postgres'
    password_db = 'postgres'
    server_db = '172.22.130.99'
    port_number = '5432'
    schema = ''

    #Dictionnaire des paramètres BD de base
    connexion_ini_dic = {
      "dbname" : 'gus',
      "user_db" : 'postgres',
      "password_db" : 'postgres',
      "server_db" : '172.22.130.99',
      "port_number" : '5432',
      "schema" : ''
    }

    #Dictionnaire des paramètres BD de classification en strates verticales 
    connexion_stratev_dic = connexion_ini_dic
    connexion_stratev_dic["schema"] = 'classification_stratesv'

    # #Dictionnaire des paramètres BD de classsification des formes végétales horizontales
    # connexion_fv_dic = connexion_ini_dic
    # connexion_fv_dic["schema"] = 'classification_fv'

    # #Dictionnaire des paramètres BD des données finales (cartographie)
    # connexion_datafinal_dic = connexion_ini_dic
    # connexion_datafinal_dic["schema"] = 'data_final'

    # #Création de la base de données 
    # createDatabase(connexion_ini_dic["dbname"], user_name=connexion_ini_dic["user_db"], password=connexion_ini_dic["password_db"], ip_host=connexion_ini_dic["server_db"], num_port=connexion_ini_dic["port_number"], schema_name=connexion_ini_dic["schema"])

    # #Connexion à la base de données
    # connexion = openConnection(connexion_ini_dic["dbname"], user_name=connexion_ini_dic["user_db"], password=connexion_ini_dic["password_db"], ip_host=connexion_ini_dic["server_db"], num_port=connexion_ini_dic["port_number"], schema_name=connexion_ini_dic["schema"])

    # #Création des extensions : postgis et sfcgal
    # createExtension(connexion, 'postgis')
    # createExtension(connexion, 'postgis_sfcgal')

    # #Création des schémas
    # createSchema(connexion, connexion_stratev_dic["schema"]) 
    # createSchema(connexion, connexion_fv_dic["schema"])
    # createSchema(connexion, connexion_datafinal_dic["schema"])

    # #Fermeture de la connexion de base
    # closeConnection(connexion) 
    if debug >= 1:
      print(bold + "\nParamètres : " + endC)
      print("Nom de la base de données : %s" %(connexion_ini_dic["dbname"]))
      print("Nom d'utilisateur : %s" %(connexion_ini_dic["user_db"]))
      print("Mot de passe : %s" %(connexion_ini_dic["password_db"]))
      print("Serveur: %s" %(connexion_ini_dic["server_db"]))
      print("Num port : %s" %(connexion_ini_dic["port_number"]))
      print("Schéma strates végétales : %s" %(connexion_stratev_dic["schema"]))
     # print("Schéma formes végétales : %s" %(connexion_fv_dic["schema"]))
     # print("Schéma données finales : %s" %(connexion_datafinal_dic["schema"]))
      print("Extensions : postgis, postgis_sfcgal")

    #1# Distinction des strates verticales de végétation
    if debug >= 1:
      print(bold + cyan + "\nDistinction des strates verticales de végétation " + endC)

    #Dossier de stockage des datas
    path_stratesveg = path_prj + os.sep + '2-DistinctionStratesV'  

    if not os.path.exists(path_stratesveg):
      os.makedirs(path_stratesveg)

    sgt_veg = path_stratesveg + os.sep + 'img_sgt_vegetation.gpkg' 

    stratesV = path_stratesveg + os.sep + 'img_stratesV.gpkg' 

    #1.1# Segmentation de l'image
    if debug >= 1:
      print(cyan + "\nSegmentation de l'image de végétation " + endC)
    #Paramètres de segmentation
    num_class = {
      "bati" : 1,
      "route" : 2,
      "sol nu" : 3,
      "eau" : 4,
      "vegetation" : 5
    }  
    minsize = 10
   # segmentationImageVegetetation(img_ref, img_classif_filtered, sgt_veg, param_minsize = minsize, num_class = num_class, format_vector='GPKG', save_intermediate_result = True, overwrite = False)

    #1.2# Classification en strates verticales
    if debug >= 1:
      print(cyan + "\nClassification des segments végétation en strates verticales " + endC)

    # #Ouverture connexion 
    connexion = openConnection(connexion_stratev_dic["dbname"], user_name=connexion_stratev_dic["user_db"], password=connexion_stratev_dic["password_db"], ip_host=connexion_stratev_dic["server_db"], num_port=connexion_stratev_dic["port_number"], schema_name=connexion_stratev_dic["schema"])
 
    img_txt_SFS = '/mnt/RAM_disk/ProjetGUS/0-Data/01-DonneesProduites/ORT_20220614_NADIR_16B_MGN_V2_txtSFS.tif'
    raster_dic = {
      "MNH" : img_MNH, 
      "TXT" : img_txt_SFS
    }
    tab_ref = 'segments_vegetation'
    dic_seuils_stratesV = {
      "seuil_h1" : 3,
      "seuil_h2" : 1, 
      "seuil_h3" : 2,
      "seuil_txt" : 11,
      "seuil_touch_arbo_vs_herba" : 15,
      "seuil_ratio_surf" : 25,
      "seuil_arbu_repres" : 20
    }

    output_tab_stratesv = classificationVerticalStratum(connexion, connexion_stratev_dic, stratesV, sgt_veg, raster_dic, tab_ref = tab_ref, dic_seuil = dic_seuils_stratesV, format_type = 'GPKG', save_intermediate_result = False, overwrite = False, debug = debug)
    
    # closeConnection(connexion)

    # #2# Détection des formes végétales horizontales
    if debug >= 1:
      print(cyan + "\nClassification des segments végétation en formes végétales" + endC)

    # #Dossier de stockage des datas
    # path_fv = path_prj + os.sep + '2-DistinctionFormesVegetales'  

    # if not os.path.exists(path_fv):
    #   os.makedirs(path_fv)

    # output_fv = path_fv + os.sep + 'vegetation_fv.gpkg'

    # fv_st_arbore = path_fv + os.sep + 'fv_st_arbore.gpkg'
    # fv_st_arbustif = path_fv + os.sep + 'fv_st_arbustif.gpkg'
    # fv_st_herbace = path_fv + os.sep + 'fv_st_herbace.gpkg'
    
    # #Ouverture connexion 
    # connexion = openConnection(connexion_fv_dic["dbname"], user_name = connexion_fv_dic["user_db"], password=connexion_stratev_dic["password_db"], ip_host = connexion_fv_dic["server_db"], num_port=connexion_stratev_dic["port_number"], schema_name = connexion_fv_dic["schema"])
 

    # treethresholds = {
    #   "seuil_surface" : 20,
    #   "seuil_compacite_1" : 0.7,
    #   "seuil_compacite_2" : 0.5,
    #   "seuil_convexite" : 0.7,
    #   "seuil_elongation" : 2.5,
    #   "val_largeur_max_alignement" : 5,
    #   "val_buffer" : 1
    # }
    # schrubthresholds = {
    #   "seuil_surface" : 5,
    #   "seuil_compacite_1" : 0.7,
    #   "seuil_compacite_2" : 0.5,
    #   "seuil_convexite" : 0.7,
    #   "seuil_elongation" : 2.5,
    #   "val_largeur_max_alignement" : 5,
    #   "val_buffer" : 1
    # }
    # dic_thresholds = {
    #   "tree" : treethresholds,
    #   "shrub" : shrubthresholds} 
    # schem_tab_ref = output_tab_stratesv
    # output_layers ={
    #   "tree" : fv_st_arbore,
    #   "shrub" : fv_st_arbustif,
    #   "herbaceous" : fv_st_herbace,
    #   "output_fv" : output_fv
    # }# dictionnaire des couches de sauvegarde  
    # #2.2#Elements arbustifs 

    # tab_veg = cartographyVegetation(connexion, connexion_dic, schem_tab_ref, dic_thresholds, output_layers, save_intermediate_results = False)

    # closeConnection(connexion)

    # #4# Calcul des indicateurs de végétation
    if debug >= 1:
      print(cyan + "\nCalcul des attributs descriptifs des formes végétales" + endC)
    # #Dossier de stockage des datas
    # path_datafinal = path_prj + os.sep + '5-Calcul_attributs_descriptifs'  

    # if not os.path.exists(path_datafinal):
    #   os.makedirs(path_datafinal)

    # output_layer = path_datafinal + os.sep + "cartographie_detaillee_vegetation.gpkg"

    # #Duplication de la couche tab_veg du schema  classification_fv vers data_final
    # query = """
    # CREATE TABLE %s AS 
    #   SELECT * FROM %s.%s;
    # """ %(tab_veg, connexion_fv_dic["schema"], tab_veg)

    # output_veg_final = path_datafinal + os.sep + 'cartographie_detaillee_vegetation.gpkg' 
  
    # #Ouverture connexion 
    # connexion = openConnection(connexion_datafinal_dic["dbname"], user_name = connexion_datafinal_dic["user_db"], password=connexion_stratev_dic["password_db"], ip_host = connexion_datafinal_dic["server_db"], num_port=connexion_datafinal_dic["port_number"], schema_name = connexion_datafinal_dic["schema"])
    
    # #Paramètres de calcul des attributs
    # dic_attributs = {
    #   "areaIndicator" :[[]], 
    #   "heightIndicators" :[[]],
    #   "evergreenDeciduousIndicators" :[[]],
    #   "coniferousDeciduousIndicators" :[[]],
    #   "typeOfGroundIndicator" :[[]]
    # }      
    # dic_params = {
    #   "img_mnh" : img_mnh,
    #   "img_ref" : img_ref,
    #   "img_wtr" : img_wtr,
    #   "thresh_evergdecid" : 0.10,
    #   "superimpose_choice" : False,
    #   "thresh_deciconif" : 1300,
    #   "thresh_soltype" : 0.3
    # } 

    # createAndImplementFeatures(connexion, connexion_dic, tab_ref, dic_attributs, dic_params, output_layer = output_layer, repertory, save_intermediate_result = False)
    path_datafinal = "ici" 
    if debug >= 1:
      print(bold + green + "\nCartographie détaillée de la végétation disponible via le chemin :" + path_datafinal + endC)

    # closeConnection(connexion)