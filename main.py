### IMPORTS ###
#Librairies Python
import sys,os, json
from osgeo import ogr ,osr

#Librairies /libs
from libs.Lib_display import bold,red,green,cyan,endC
from libs.Lib_postgis import createDatabase, openConnection, createExtension, closeConnection, dataBaseExist, schemaExist, createSchema

#Applications /apps
from app.SampleCreation import createAllSamples, prepareAllSamples
from app.CleanCoverClasses import cleanCoverClasses
from app.SampleSelectionRaster import selectSamples
from app.SupervisedClassification import classifySupervised, StructRFParameter
from app.MajorityFilter import filterImageMajority
from app.VerticalStratumDetection import classificationVerticalStratum, segmentationImageVegetetation
from app.VegetationFormStratumDetection import cartographyVegetation
from app.DhmCreation import mnhCreation
from app.NeochannelComputation import neochannelComputation
from app.DataConcatenation import concatenateData
from app.ImagesAssembly import assemblyRasters
from app.IndicatorsComputation import createAndImplementFeatures

if __name__ == "__main__":

    #Option debug permet l'affichage de commentaires en plus des basiques lors du lancement des différentes étapes 
    debug = 3

    ##############################
    # RECUPERATION DES VARIABLES #
    ##############################  

    with open('config.json') as f:
      config = json.load(f)

    img_ref = config["data_entry"]["img_RVBPIR_ref"]  
    img_ref_PAN = config["data_entry"]["img_PAN_ref"] 
    shp_zone = config["data_entry"]["studyzone_shp"] 
    img_winter = config["data_entry"]["img_winter"] 
    img_mnt = config["data_entry"]["img_dtm"] 
    img_mns = config["data_entry"]["img_dsm"]



    ########################################
    # RENSEIGNEMENT DES DONNEES EN ENTREE  #  
    ########################################

    img_ref = r'/mnt/Data/10_Agents_travaux_en_cours/Mathilde/12-Cartographie_vegetation_MGN_octobre2023/ProjetGUS/ORT_20220614_NADIR_16B_MGN_V2.tif'

    img_ref_PAN = r'/mnt/Data/10_Agents_travaux_en_cours/Mathilde/RAMDISKDU11072023/ProjetGUS/0-Data/00-DonneesEntrees/ORT_P1AP_MGN.tif'
    #NB : l'image PAN doit aussi être découpée à la même emprise que l'image de référence --> pour que la superposition des résultats suivant puisse se faire correctement 

    shp_zone = r'/mnt/Data/10_Agents_travaux_en_cours/Mathilde/12-Cartographie_vegetation_MGN_octobre2023/ProjetGUS/MGN_contours.shp'

    img_mnt =  r''

    img_mns = r''

    img_mnh = r'/mnt/Data/10_Agents_travaux_en_cours/Mathilde/12-Cartographie_vegetation_MGN_octobre2023/ProjetGUS/mnh.tif'

    img_spring = img_ref

    img_winter = r'/mnt/Data/20_Etudes_Encours/ENVIRONNEMENT/2022_GreenUrbanSat/0-IMAGES_SATELLITES/2021/NANCY/2021_12_21/16Bits/Assemblage_zone_etude_MGN/ORT_20211221_NADIR_16B_MGN.tif'

    img_texture = r'/mnt/Data/10_Agents_travaux_en_cours/Mathilde/12-Cartographie_vegetation_MGN_octobre2023/ProjetGUS/TMP_NEOCHANNELSCOMPUTATION/ORT_20220614_NADIR_16B_MGN_V2_txtSFS.tif'

    img_ocs_2 = r'/mnt/Data/10_Agents_travaux_en_cours/Mathilde/12-Cartographie_vegetation_MGN_octobre2023/ProjetGUS/img_ocs_MGN.tif'

    #Données optionnelles fournis

    #mnh
    if config["data_entry"]["entry_options"]["img_dhm"] != None :
      img_mnh = config["data_entry"]["entry_options"]["img_dhm"]
    

    #ocs
    if config["data_entry"]["entry_options"]["img_ocs"] != None :
      img_ocs = config["data_entry"]["entry_options"]["img_ocs"]
    

    #polygones d'échantillons d'apprentissage  
    if config["data_entry"]["entry_options"]["data_classes"]["createsamples"] == 'False' : 
      create_samples = False
      bati = config["data_entry"]["entry_options"]["data_classes"]["build"] 
      route =  config["data_entry"]["entry_options"]["data_classes"]["road"] 
      solnu =  config["data_entry"]["entry_options"]["data_classes"]["baresoil"] 
      eau =  config["data_entry"]["entry_options"]["data_classes"]["water"] 
      vegetation = config["data_entry"]["entry_options"]["data_classes"]["vegetation"] 
    else :
      create_samples = True


    ########################################
    #   RENSEIGNEMENT DES PARAMETRES ET    # 
    #            VALEURS SEUILS            #  
    ########################################

    #Paramètres nettoyage des échantillons d'apprentissage à partir d'un seuil appliqué sur indices radiométriques


    #Paramètres de l'algorithme de classification supervisée RF 
    params_RF = config["vegetation_extraction"]["rf_params"]

    #Fournir les paramètres de connexion à la base de donnée 
    connexion_ini_dic = config["database_params"]
    connexion_ini_dic ={
        "dbname": "gus",
        "user_db": "postgres",
        "password_db": "postgres",
        "server_db": "172.22.130.99",
        "port_number": 5432,
        "schema" : ""
    } 

    connexion_0 ={
        "dbname": "gus",
        "user_db": "postgres",
        "password_db": "postgres",
        "server_db": "172.22.130.99",
        "port_number": 5432,
        "schema" : ""
    } 


   # connexion_0 = config["database_params"]
    connexion_0["dbname"] = ""
    connexion_0["schema"] = ""

    if connexion_ini_dic["dbname"] == "":
      connexion_ini_dic["dbname"] = "gus"

    #Paramètres de segmentation
    minsize = config["segmentation"]["minsize"]

    num_class = {
      "bati" : config["vegetation_extraction"]["classes_numbers"]["build"],
      "route" : config["vegetation_extraction"]["classes_numbers"]["road"],
      "sol nu" : config["vegetation_extraction"]["classes_numbers"]["baresoil"],
      "eau" : config["vegetation_extraction"]["classes_numbers"]["water"],
      "vegetation" : config["vegetation_extraction"]["classes_numbers"]["vegetation"]
    }  

    #Seuils pour la distinction des strates verticales
    dic_seuils_stratesV = config["vertical_stratum_detection"] 
    
    #Seuils pour la détection des formes végétales horizontales
    treethresholds = config["vegetation_form_stratum_detection"]["tree"] 
    
    shrubthresholds = config["vegetation_form_stratum_detection"]["shrub"] 

    herbaceousthresholds = config["vegetation_form_stratum_detection"]["herbaceous"]

    dic_thresholds = {
      "tree" : treethresholds,
      "shrub" : shrubthresholds,
      "herbaceous" : herbaceousthresholds
    } 

    #Paramètres de calcul des attributs
    #On n'a pas forcément besoin d'aller chercher dans le fichier config. 
    dic_attributs ={
      "paysage" : [['paysage', 'varchar(100)']], 
      "area_indicator" : [['surface', 'float']],
      "height_indicators" : [['h_moy', 'float'], ['h_med', 'float'], ['h_et', 'float'], ['h_min', 'float'], ['h_max', 'float']],
      "coniferousdeciduous_indicators" : [['perc_persistant', 'float'], ['perc_caduc', 'float']],
      "evergreendeciduous_indicators" : [['perc_conifere', 'float'], ['perc_feuillu', 'float']],
      "typeofground_indicator" : [['type_sol', 'varchar(100)']],
      "confidence_indices" :[['idc_surface', 'float'], ['idc_h', 'float'], ['idc_prescadu', 'float'], ['idc_coniffeuil', 'float'], ['idc_typesol', 'float']]  
    } 
     
    dic_params ={
      "img_ref" : img_ref,
      "img_mnh" : img_mnh,
      "img_wtr" : img_winter,
      "ndvi_difference_everdecid_thr" : config["indicators_computation"]["evergreen_deciduous"]["ndvi_difference_thr"],
      "superimpose_choice" : True,
      "pir_difference_thr" : config["indicators_computation"]["coniferous_deciduous"]["pir_difference_thr"],
      "ndvi_difference_groundtype_thr" : config["indicators_computation"]["ground_type"]["ndvi_difference_thr"]
    } 
 

    ########################################
    # CRÉATION ARCHITECTURE DOSSIER PROJET #  
    ########################################

    ##Emplacement du repertoire
    repertory_prj = config["repertory"] 
    path_prj = repertory_prj + os.sep + 'ProjetGUS'
    

    #Dossier de stockage des datas
    path_data = path_prj + os.sep + '0-Data'  
    path_data_entry = path_data + os.sep + '00-DonneesEntrees'
    path_data_prod = path_data + os.sep + '01-DonneesProduites'

    path_tmp_neochannels = path_data_prod + os.sep + 'TMP_NEOCHANNELS'

    #Dossier de sauvegarde des résultats d'extraction de la végétation 
    path_extractveg = path_prj + os.sep + '1-ExtractionVegetation'  

    path_tmp_preparesamples = path_extractveg + os.sep + 'TMP_PREPARE_SAMPLE'

    path_tmp_cleansamples = path_extractveg + os.sep + 'TMP_CLEAN_SAMPLE'

    path_tmp_selectsamples = path_extractveg + os.sep + 'TMP_SELECT_SAMPLE'

    #Dossier de sauvegarde des résultats de distinction des strates verticales végétales
    path_stratesveg = path_prj + os.sep + '2-DistinctionStratesV'

    #Dossier de sauvegarde des résultats de distinction des formes végétales
    path_fv = path_prj + os.sep + '3-DistinctionFormesVegetales'  

    #Dossier de sauvegarde des résultats de calcul des attributs descriptifs de la végétation
    path_datafinal = path_prj + os.sep + '4-Calcul_attributs_descriptifs'  
    
    ##Création des répertoires s'ils n'existent pas
    if  not os.path.exists(path_prj):
      os.makedirs(path_prj)

    if not os.path.exists(path_data):
      os.makedirs(path_data)

    if not os.path.exists(path_data_entry):
      os.makedirs(path_data_entry)

    if not os.path.exists(path_data_prod):
      os.makedirs(path_data_prod)

    if not os.path.exists(path_tmp_neochannels):
      os.makedirs(path_tmp_neochannels)

    if not os.path.exists(path_extractveg):
      os.makedirs(path_extractveg)

    if not os.path.exists(path_tmp_preparesamples):
      os.makedirs(path_tmp_preparesamples)

    if not os.path.exists(path_tmp_cleansamples):
      os.makedirs(path_tmp_cleansamples)

    if not os.path.exists(path_tmp_selectsamples):
      os.makedirs(path_tmp_selectsamples)

    if not os.path.exists(path_stratesveg):
      os.makedirs(path_stratesveg)

    if not os.path.exists(path_fv):
      os.makedirs(path_fv)

    if not os.path.exists(path_datafinal):
      os.makedirs(path_datafinal)



    #######################################################
    # CRÉATION DES CHEMINS D'ACCES DANS LE DOSSIER PROJET # 
    #                 AUX FICHIERS CRÉÉS                  #  
    #######################################################
     
    img_stack = path_data_prod + os.sep + 'img_stack.tif'

    if img_mnh == '':
      img_mnh = path_data_prod + os.sep + 'mnh.tif'

    img_ndvi = path_tmp_neochannels + os.sep + 'img_ref_NDVI.tif'
    img_ndwi = path_tmp_neochannels + os.sep + 'img_ref_NDWI.tif'
    img_msavi = path_tmp_neochannels+ os.sep + 'img_ref_MSAVI.tif'
    img_sfs = path_tmp_neochannels + os.sep + 'img_ref_SFS.tif'
    img_teinte = path_tmp_neochannels + os.sep + 'img_ref_SFS.tif'

    img_sfs = r'/mnt/Data/10_Agents_travaux_en_cours/Mathilde/12-Cartographie_vegetation_MGN_octobre2023/ProjetGUS/TMP_NEOCHANNELSCOMPUTATION/ORT_20220614_NADIR_16B_MGN_V2_txtSFS.tif'

    dic_neochannels = {
      "ndvi" : img_ndvi,
      "ndwi": img_ndwi,
      "msavi" : img_msavi,
      "sfs" : img_sfs,
      "teinte" : img_teinte
    } 

    img_neocanaux = path_data_prod + os.sep + 'img_neocanaux.tif'

    #Création des chemins d'accès aux couches d'échantillons d'apprentissage si elles n'ont pas été indiquée
    if create_samples == True :
      bati = path_data_entry + os.sep + 'bati_vector.shp'
      bati_img = path_data_entry + os.sep + 'bati_raster.tif'

      route =  path_data_entry + os.sep + 'route_vector.shp'
      route_img = path_data_entry + os.sep + 'route_raster.tif'

      solnu =  path_data_entry + os.sep + 'solnu_vector.shp'
      solnu_img = path_data_entry + os.sep + 'solnu_raster.tif'
      
      eau =  path_data_entry + os.sep + 'eau_vector.shp'
      eau_img = path_data_entry + os.sep + 'eau_raster.tif'
      
      vegetation =  path_data_entry + os.sep + 'vegetation_vector.shp'
      vegetation_img = path_data_entry + os.sep + 'vegetation_raster.tif'

      rasters_samples_output ={
        "bati" : bati_img,
        "route" : route_img,
        "solnu" : solnu_img,
        "eau" : eau_img,
        "vegetation" : vegetation_img
      }


      #Paramètres création des échantillons d'apprentissage

      if create_samples ==  True:
        li_data_bati = []
        li_data_route = []
        li_data_solnu = [] 
        li_data_eau = []
        li_data_vegetation = []

        for data in config["vegetation_extraction"]["samples_creation"]["build"]:
          dic = config["vegetation_extraction"]["samples_creation"]["build"].get(data)
          li_data_bati.append([dic["source"], dic["buffer"], dic["exp"]])

        for data in config["vegetation_extraction"]["samples_creation"]["road"]:
          dic = config["vegetation_extraction"]["samples_creation"]["road"].get(data)
          li_data_route.append([dic["source"], dic["buffer"], dic["exp"]])

        for data in config["vegetation_extraction"]["samples_creation"]["baresoil"]:
          dic = config["vegetation_extraction"]["samples_creation"]["baresoil"].get(data)
          li_data_solnu.append([dic["source"], dic["buffer"], dic["exp"]])

        for data in config["vegetation_extraction"]["samples_creation"]["water"]:
          dic = config["vegetation_extraction"]["samples_creation"]["water"].get(data)
          li_data_eau.append([dic["source"], dic["buffer"], dic["exp"]])

        for data in config["vegetation_extraction"]["samples_creation"]["vegetation"]:
          dic = config["vegetation_extraction"]["samples_creation"]["vegetation"].get(data)
          li_data_vegetation.append([dic["source"], dic["buffer"], dic["exp"]])

        params_to_find_samples = {
          "bati" : li_data_bati,
          "route" : li_data_route,
          "solnu" : li_data_solnu,
          "eau" : li_data_eau,
          "vegetation" : li_data_vegetation
        }  

    vectors_samples_output ={
        "bati" : bati,
        "route" : route,
        "solnu" : solnu,
        "eau" : eau,
        "vegetation" : vegetation
      }
    
    #Chemins d'accès vers le pré-nettoyage des couches d'échantillons d'apprentissage
    bati_prepare = path_tmp_preparesamples + os.sep + 'bati_vector_prepare.tif'
    route_prepare = path_tmp_preparesamples + os.sep + 'route_vector_prepare.tif'
    solnu_prepare = path_tmp_preparesamples + os.sep + 'solnu_vector_prepare.tif'
    eau_prepare = path_tmp_preparesamples + os.sep + 'eau_vector_prepare.tif'
    vegetation_prepare = path_tmp_preparesamples + os.sep + 'vegetation_vector_prepare.tif'

    #Dictionnaire des paramètres de préparation des échantillons d'apprentissage
    dic_img_preparesamples ={
      "bati" :[bati, bati_prepare, True],
      "route" : [route, route_prepare, False],
      "sol nu" : [solnu, solnu_prepare, True],
      "eau" : [eau, eau_prepare, True],
      "vegetation" : [vegetation, vegetation_prepare, True]  
    } 

    #Chemins d'accès vers le nettoyage des couches d'échantillons d'apprentissage 
    bati_clean = path_tmp_cleansamples + os.sep + 'bati_vector_clean.tif'
    route_clean = path_tmp_cleansamples + os.sep + 'route_vector_clean.tif'
    solnu_clean = path_tmp_cleansamples + os.sep + 'solnu_vector_clean.tif'
    eau_clean = path_tmp_cleansamples + os.sep + 'eau_vector_clean.tif'
    vegetation_clean = path_tmp_cleansamples + os.sep + 'vegetation_vector_clean.tif'

    dic_img_cleansamples = {
        "bâti" : [bati_prepare, bati_clean],
        "route" : [route_prepare, route_clean],
        "solnu" : [solnu_prepare, solnu_clean],
        "eau" : [eau_prepare, eau_clean],
        "vegetation" : [vegetation_prepare, vegetation_clean]     
    } 

    li_data_bati = []
    li_data_route = []
    li_data_solnu = [] 
    li_data_eau = []
    li_data_vegetation = []

    for data in config["vegetation_extraction"]["samples_cleaning"]["build"]:
      dic = config["vegetation_extraction"]["samples_cleaning"]["build"].get(data)
      if dic["name"] in dic_neochannels :
        name = str(dic["name"])
        print(dic["name"], name)
        dic["source"] = dic_neochannels[name]
      li_data_bati.append([dic["name"], dic["source"], dic["min"], dic["max"]])
        

    for data in config["vegetation_extraction"]["samples_cleaning"]["road"]:
      dic = config["vegetation_extraction"]["samples_cleaning"]["road"].get(data)
      if dic["name"] in dic_neochannels :
        name = str(dic["name"])
        dic["source"] = dic_neochannels[name]
      li_data_route.append([dic["name"], dic["source"], dic["min"], dic["max"]])

    for data in config["vegetation_extraction"]["samples_cleaning"]["baresoil"]:
      dic = config["vegetation_extraction"]["samples_cleaning"]["baresoil"].get(data)
      if dic["name"] in dic_neochannels :
        name = str(dic["name"])
        dic["source"] = dic_neochannels[name]
      li_data_solnu.append([dic["name"], dic["source"], dic["min"], dic["max"]])

    for data in config["vegetation_extraction"]["samples_cleaning"]["water"]:
      dic = config["vegetation_extraction"]["samples_cleaning"]["water"].get(data)
      if dic["name"] in dic_neochannels :
        name = str(dic["name"])
        dic["source"] = dic_neochannels[name]
      li_data_eau.append([dic["name"], dic["source"], dic["min"], dic["max"]])

    for data in config["vegetation_extraction"]["samples_cleaning"]["vegetation"]:
      dic = config["vegetation_extraction"]["samples_cleaning"]["vegetation"].get(data)
      if dic["name"] in dic_neochannels :
        name = str(dic["name"])
        dic["source"] = dic_neochannels[name]
      li_data_vegetation.append([dic["name"], dic["source"], dic["min"], dic["max"]])

    correction_images_dic = {
        "bati" : li_data_bati,
        "route" : li_data_route,
        "solnu" : li_data_solnu,
        "eau" : li_data_eau,
        "vegetation" : li_data_vegetation
    }
    
    #Chemin d'accès vers la couche unique des échantillons d'apprentissage 
    mask_samples_input_list = [bati_clean, route_clean, solnu_clean, eau_clean, vegetation_clean]

    image_samples_merged_output = path_tmp_cleansamples + os.sep + 'img_samples_merged.tif'

    #Chemin d'accès vers la couche et le fichier statistique des échantillons d'apprentissage sélectionnés 
    samplevector = path_tmp_selectsamples + os.sep + 'sample_vector_selected.shp'
    table_statistics_output = path_tmp_selectsamples + os.sep + 'statistics_sample_vector_selected.csv'

    #Chemin d'accès vers l'image ocs 
    img_classif = path_extractveg + os.sep + 'img_classification.tif'
    img_classif_confid = path_extractveg + os.sep + 'img_classification_confidence.tif' 
    img_classif_filtered = path_extractveg + os.sep + 'img_classification_filtered.tif'

    #Chemin d'accès vers la couche de segments végétation 
    sgts_veg = path_stratesveg + os.sep + 'img_sgt_vegetation.gpkg' 

    #Chemins d'accès vers les données des strates verticales 
    path_stratesv_vegetation = path_stratesveg + os.sep + 'img_stratesV.gpkg'  
    path_st_arbore = path_stratesveg + os.sep + 'strate_arbore.gpkg'
    path_st_arbustif = path_stratesveg + os.sep + 'strate_arbustive.gpkg'
    path_st_herbace = path_stratesveg + os.sep + 'strate_herbace.gpkg'

    output_stratesv_layers ={
      "tree" : path_st_arbore,
      "shrub" : path_st_arbustif,
      "herbaceous" : path_st_herbace,
      "output_stratesv" : path_stratesv_vegetation
    } 

    #Chemins d'accès vers les données des formes végétales horizontales 
    path_fv_vegetation = path_fv + os.sep + 'vegetation_fv.gpkg'
    fv_st_arbore = path_fv + os.sep + 'fv_st_arbore.gpkg'
    fv_st_arbustif = path_fv + os.sep + 'fv_st_arbustif.gpkg'
    fv_st_herbace = path_fv + os.sep + 'fv_st_herbace.gpkg'

    output_fv_layers ={
      "tree" : fv_st_arbore,
      "shrub" : fv_st_arbustif,
      "herbaceous" : fv_st_herbace,
      "output_fv" : path_fv_vegetation
    } 


    #Chemin d'accès vers la donnée finale de cartographie détaillée de la végétation 
    path_finaldata = path_datafinal + os.sep + "cartographie_detaillee_vegetation.gpkg" 


    #######################################################
    #           CRÉATION DE LA BASE DE DONNÉES            # 
    #######################################################

    #Dictionnaire des paramètres BD de classification en strates verticales 
    connexion_stratev_dic = connexion_ini_dic
    connexion_stratev_dic["schema"] = 'classification_stratesv'

    #Dictionnaire des paramètres BD des données finales (cartographie) dont les formes végétales horizontales
    connexion_datafinal_dic = connexion_ini_dic
    connexion_datafinal_dic["schema"] = 'data_final'
    connexion = openConnection(connexion_0["dbname"], user_name=connexion_0["user_db"], password=connexion_0["password_db"], ip_host=connexion_0["server_db"], num_port=connexion_0["port_number"], schema_name=connexion_0["schema"])

    #Création de la base de données 
    if dataBaseExist(connexion, connexion_ini_dic["dbname"]) == False:
      createDatabase(connexion_ini_dic["dbname"], user_name=connexion_ini_dic["user_db"], password=connexion_ini_dic["password_db"], ip_host=connexion_ini_dic["server_db"], num_port=connexion_ini_dic["port_number"], schema_name=connexion_ini_dic["schema"])
      closeConnection(connexion)
    #Connexion à la base de données
    connexion = openConnection(connexion_ini_dic["dbname"], user_name=connexion_ini_dic["user_db"], password=connexion_ini_dic["password_db"], ip_host=connexion_ini_dic["server_db"], num_port=connexion_ini_dic["port_number"], schema_name=connexion_ini_dic["schema"])

    #Création des extensions : postgis et sfcgal
    createExtension(connexion, 'postgis')
    createExtension(connexion, 'postgis_sfcgal')

    #Création des schémas
    if schemaExist(connexion, connexion_stratev_dic["schema"]) == False:
      createSchema(connexion, connexion_stratev_dic["schema"]) 
    if createSchema(connexion, connexion_datafinal_dic["schema"]) == False:
      createSchema(connexion, connexion_datafinal_dic["schema"])
    
    closeConnection(connexion)

    #######################################################
    #                   TRAITEMENTS                       #  
    #######################################################
    
    print(bold + cyan + "*********************************************** \n*** Cartographie détaillée de la végétation *** \n***********************************************" + endC)


    if debug >= 1:
      print(bold + cyan + "\nCréation structure du dossier de projet" + endC)
      print("Répertoire : " + repertory_prj)

    
    #0# PRE-TRAITEMENTS #0#  
    if debug >= 1:
      print(bold + cyan + "\n*0* PRÉ-TRAITEMENTS" + endC)
    # IMAGES ASSEMBLY
    if config["steps_to_run"]["img_assembly"] == True:
      if debug >= 1:
        print(cyan + "\nAssemblage des imagettes" + endC)
      
      img_tiles_repertory = config["repertory_img_assembly"] 

      assemblyImages(repertory, img_tiles_repertory, img_ref, no_data_value, epsg, save_results_intermediate = False, ext_txt = '.txt',  format_raster = 'GTiff')
    
    # MNH CREATION  
    if config["steps_to_run"]["create_DHM"] == True:
      if debug >= 1:
        print(cyan + "\nCréation du MNH" + endC)
   
      mnhCreation(img_mns, img_mnt, img_mnh, shp_zone , img_ref,  epsg=2154, nivellement = True, format_raster = 'GTiff', format_vector = 'ESRI Shapefile',  overwrite = True, save_intermediate_results = True)
  
    # CALCUL DES NEOCANAUX
    if config["steps_to_run"]["neochannels_computation"] == True:
      if debug >= 1:
        print(cyan + "\nCalcul des néocanaux" + endC)

      neochannelComputation(img_ref, img_ref_PAN, dic_neochannels, shp_zone, save_intermediate_results = False)


    dic_neochannels["mnh"] = img_mnh
     
    
    # CONCATENATION DES NEOCANAUX
    if config["steps_to_run"]["data_concatenation"] == True:
      if debug >= 1:
        print(cyan + "\nConcaténation des néocanaux" + endC)

    
      concatenateData(dic_neochannels, img_stack, img_ref, shp_zone)

   #ATTENTION : il se peut que, le mnh dusse subir un ré-échantillonnage et recalage par rapport à la donnée de base si il a a été fournit directement par l'opérateur 
   # nous avons donc créé un nouveau fichier mnh superimposé par rapport à l'image de référence (normalement situé dans le dossier temporaire des néochannels) 
 
  #   #1# EXTRACTION DE LA VEGETATION PAR CLASSIFICATION SUPERVISEE #1# 
    if config["steps_to_run"]["vegetation_extraction"] == False :
      img_classification_filtered = img_ocs
      if debug >= 1:
        print(bold + cyan + "\n*1* EXTRACTION DE LA VÉGÉTATION : le fichier image classifié est fournit et disponible via " + img_classification_filtered + endC)

    else :

      if debug >= 1:
        print(bold + cyan + "\n*1* EXTRACTION DE LA VÉGÉTATION" + endC)
     

      #1.Création des échantillons d'apprentissage
      if create_samples == True:
        if debug >= 1:
          print(cyan + "\nCréation des échantillons d'apprentissage" + endC)

        #createAllSamples(img_ref, shp_zone, vectors_samples_output, rasters_samples_output, params_to_find_samples, simplify_vector_param=10.0, format_vector='ESRI Shapefile', extension_vector=".shp", save_results_intermediate=False, overwrite=True)


      #2.Préparation des échantillons d'apprentissage
      if debug >= 1:
        print(cyan + "\nPréparation des échantillons d'apprentissage" + endC) 

      #prepareAllSamples(img_ref, dic_preparesamples, shp_zone, format_vector = 'ESRI Shapefile')
  
      #3.Nettoyage des échantillons d'apprentissage : érosion + filtrage avec les néocanaux
      if debug >= 1:
        print(cyan + "\nNettoyage des échantillons d'apprentissage" + endC) 

      #cleanAllSamples(dic_img_cleansamples, correction_images_dic, extension_raster = ".tif", save_results_intermediate = False, overwrite = False)

      
      #4.Nettoyage recouvrement des échantillons d'apprentissage
      if debug >= 1:
        print(cyan + "\nCorrection du recouvrement des échantillons d'apprentissage" + endC) 
        
      #cleanCoverClasses(img_ref, mask_samples_input_list, image_samples_merged_output)
      
      #5.Sélection des échantillons
      if debug >= 1:
        print(cyan + "\nSélection des échantillons d'apprentissage" + endC) 

      #selectSamples([img_stack], image_samples_merged_output, samplevector, table_statistics_output, sampler_strategy="percent", select_ratio_floor = 10, ratio_per_class_dico = {1:1.37,2:3.40,3:100,4:0.37,5:0.84}, name_column = 'ROI', no_data_value = 0)
      

      #6. Classification supervisée RF
      if debug >= 1:
        print(cyan + "\nClassification supervisée RF" + endC)

      rf_parametres_struct = StructRFParameter()
      rf_parametres_struct.max_depth_tree = params_RF["depth_tree"]
      rf_parametres_struct.min_sample = params_RF["sample_min"]
      rf_parametres_struct.ra_termin_criteria = params_RF["termin_criteria"]
      rf_parametres_struct.cat_clusters = params_RF["cluster"]
      rf_parametres_struct.var_size_features = params_RF["size_features"]
      rf_parametres_struct.nbtrees_max =  params_RF["num_tree"]
      rf_parametres_struct.acc_obb_erreur = params_RF["obb_erreur"]
      
      # classifySupervised([img_stack], samplevector, img_classif, '', model_output = '', model_input = '', field_class = 'ROI', classifier_mode = "rf", rf_parametres_struct = rf_parametres_struct,no_data_value = 0, ram_otb=0,  format_raster='GTiff', extension_vector=".shp")
      
      #7.Application du filtre majoritaire 
      if debug >= 1:
        print(cyan + "\nApplication du filtre majoritaire" + endC)  

      #filterImageMajority(img_classif, img_classif_filtered, umc_pixels = 8) 
      

    #2# DISTINCTION DES STRATES VERTICALES VEGETALES #2#  

    if config["steps_to_run"]["vertical_stratum_detection"]  == True :
      if debug >= 1:
        print(bold + cyan + "\nDistinction des strates verticales de végétation " + endC)
      
      if debug >= 1:
        print(bold + "\nParamètres : " + endC)
        print("Nom de la base de données : %s" %(connexion_ini_dic["dbname"]))
        print("Nom d'utilisateur : %s" %(connexion_ini_dic["user_db"]))
        print("Mot de passe : %s" %(connexion_ini_dic["password_db"]))
        print("Serveur: %s" %(connexion_ini_dic["server_db"]))
        print("Num port : %s" %(connexion_ini_dic["port_number"]))
        print("Schéma strates végétales : %s" %(connexion_stratev_dic["schema"]))
        print("Schéma données finales dont fv: %s" %(connexion_datafinal_dic["schema"]))
        print("Extensions : postgis, postgis_sfcgal")

      #1.Segmentation de l'image
      if debug >= 1:
        print(cyan + "\nSegmentation de l'image de végétation " + endC)
    
      #segmentationImageVegetetation(img_ref, img_classif_filtered, sgts_veg, param_minsize = minsize, num_class = num_class, format_vector='GPKG', save_intermediate_result = False, overwrite = False)

      #2.Classification en strates verticales
      if debug >= 1:
        print(cyan + "\nClassification des segments végétation en strates verticales " + endC)

      #Ouverture connexion 
      connexion = openConnection(connexion_stratev_dic["dbname"], user_name=connexion_stratev_dic["user_db"], password=connexion_stratev_dic["password_db"], ip_host=connexion_stratev_dic["server_db"], num_port=connexion_stratev_dic["port_number"], schema_name=connexion_stratev_dic["schema"])
      raster_dic = {
        "MNH" : dic_neochannels["mnh"],
        "TXT" : dic_neochannels["sfs"]
      }

      #Nom attribué à la table de référence des segments végétation classés en strates verticales 
      tab_ref_stratesv = 'segments_vegetation'
      schem_tab_ref_stratesv = 'classification_stratesv.segments_vegetation'
    
      output_tab_stratesv = classificationVerticalStratum(connexion, connexion_stratev_dic, output_stratesv_layers, sgts_veg, raster_dic, tab_ref = tab_ref_stratesv, dic_seuil = dic_seuils_stratesV, format_type = 'GPKG', save_intermediate_result = False, overwrite = False, debug = debug)
      
      closeConnection(connexion)

    #3# DETECTION DES FORMES VEGETALES HORIZONTALES #3# 
    if config["steps_to_run"]["vegetation_form_stratum_detection"] == True :
      if debug >= 1:
        print(cyan + "\nClassification des segments végétation en formes végétales" + endC)

      #Ouverture connexion 
      #connexion = openConnection(connexion_datafinal_dic["dbname"], user_name = connexion_datafinal_dic["user_db"], password=connexion_datafinal_dic["password_db"], ip_host = connexion_datafinal_dic["server_db"], num_port=connexion_datafinal_dic["port_number"], schema_name = connexion_datafinal_dic["schema"])
    
      #tab_veg = cartographyVegetation(connexion, connexion_datafinal_dic, schem_tab_ref_stratesv, dic_thresholds, output_fv_layers, save_intermediate_results = False, overwrite = False,  debug = debug)

      #closeConnection(connexion)

    tab_ref = "vegetation"

    #4# Calcul des indicateurs de végétation

    if config["steps_to_run"]["indicators_computation"] == True :
      if debug >= 1:
        print(cyan + "\nCalcul des attributs descriptifs des formes végétales" + endC)
      
      #Ouverture connexion 
      #connexion = openConnection(connexion_datafinal_dic["dbname"], user_name = connexion_datafinal_dic["user_db"], password=connexion_stratev_dic["password_db"], ip_host = connexion_datafinal_dic["server_db"], num_port=connexion_datafinal_dic["port_number"], schema_name = connexion_datafinal_dic["schema"])
    
      #createAndImplementFeatures(connexion, connexion_datafinal_dic, tab_ref, dic_attributs, dic_params, repertory = path_datafinal, output_layer = path_finaldata, save_intermediate_result = False)

      if debug >= 1:
        print(bold + green + "\nCartographie détaillée de la végétation disponible via le chemin :" + path_datafinal + endC)

      closeConnection(connexion)