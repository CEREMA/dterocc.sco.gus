#!/usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.               #
#############################################################################

### IMPORTS ###
# Librairies Python
import sys,os, json, re
from osgeo import ogr ,osr

# Librairies /libs
from Lib_display import bold,red,green,cyan,endC
from Lib_raster import cutImageByVector
from Lib_postgis import createDatabase, dropDatabase, openConnection, createExtension, closeConnection, dataBaseExist, schemaExist, createSchema, importVectorByOgr2ogr, dropColumn, renameColumn, executeQuery

# Applications /apps
from app.VerticalStratumDetection import classificationVerticalStratum, segmentationImageVegetetation
from app.VegetationFormStratumDetection import cartographyVegetation
from app.DhmCreation import mnhCreation
from app.ChannelComputation import neochannelComputation, createNDVI
from app.DataConcatenation import concatenateData
from app.GUSRastersAssembly import assemblyRasters
from app.IndicatorsComputation import createAndImplementFeatures
from app.LandscapeDetection import landscapeDetection, urbanLandscapeDetection

if __name__ == "__main__":

    debug = 1
    save_intermediate_result = False

    ##############################
    # RECUPERATION DES VARIABLES #
    ##############################
    file_conf = sys.argv[1]
    print('file_conf :', file_conf)
    f = open(file_conf)
    config = json.load(f)

    shp_zone = config["data_entry"]["studyzone_shp"]
    image_summer_ref = config["data_entry"]["img_summer_RVBPIR_ref"]
    image_summer_ref_PAN = config["data_entry"]["img_summer_PAN_ref"]
    image_winter = config["data_entry"]["img_winter_RVBPIR"]
    image_mnt = config["data_entry"]["img_dtm"]
    image_mns = config["data_entry"]["img_dsm"]
    img_ref = ""
    img_winter = ""

    if config["save_intermediate_result"] :
      save_intermediate_result = config["save_intermediate_result"]

    if config["display_comments"]:
      debug = 3

    if image_summer_ref == "" and not config_data["steps_to_run"]["img_assembly"] :
      print(bold + red + "Attention : aucune donnée n'est fournie pour le bon déroulement des étapes de production de la cartographie !!!" + endC)

    ########################################
    # RENSEIGNEMENT DES DONNEES EN ENTREE  #
    ########################################

    # Données optionnelles fournis

    # mnh
    if config["data_entry"]["entry_options"]["img_dhm"] != None :
      img_mnh = config["data_entry"]["entry_options"]["img_dhm"]

    # data paysages
    if config["indicators_computation"]["landscape"] != None :
      vect_landscape = config["indicators_computation"]["landscape"]
    else :
      vect_landscape = r''

    ########################################
    # CRÉATION ARCHITECTURE DOSSIER PROJET #
    ########################################

    # Emplacement du repertoire
    repertory_prj = config["repertory"]
    path_prj = repertory_prj + os.sep + 'ProjetGUS'

    # Dossier de stockage des datas
    path_data = path_prj + os.sep + '0-Data'
    path_data_entry = path_data + os.sep + '00-DonneesEntrees'
    path_data_prod = path_data + os.sep + '01-DonneesProduites'

    path_tmp_neochannels = path_data_prod + os.sep + 'TMP_NEOCHANNELS'
    path_image_assemble = path_data_prod + os.sep + 'TMP_IMG_ASSEMBLE'
    path_img_cut = path_data_prod + os.sep + 'TMP_IMG_CUT'


    # Dossier de sauvegarde des résultats de distinction des strates verticales végétales
    path_stratesveg = path_prj + os.sep + '2-DistinctionStratesV'

    # Dossier de sauvegarde des résultats de distinction des formes végétales
    path_fv = path_prj + os.sep + '3-DistinctionFormesVegetales'

    # Dossier de sauvegarde des résultats de calcul des attributs descriptifs de la végétation
    path_datafinal = path_prj + os.sep + '4-Calcul_attributs_descriptifs'

    # Dossier de sauvegarde des résultats de paysage
    path_landscape = path_prj + os.sep + '1-Paysages'


    ## Création des répertoires s'ils n'existent pas
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

    if not os.path.exists(path_image_assemble):
      os.makedirs(path_image_assemble)

    if not os.path.exists(path_img_cut):
      os.makedirs(path_img_cut)

    if not os.path.exists(path_stratesveg):
      os.makedirs(path_stratesveg)

    if not os.path.exists(path_fv):
      os.makedirs(path_fv)

    if not os.path.exists(path_datafinal):
      os.makedirs(path_datafinal)

    if not os.path.exists(path_landscape):
      os.makedirs(path_landscape)

    ########################################
    #   RENSEIGNEMENT DES PARAMETRES ET    #
    #            VALEURS SEUILS            #
    ########################################

    # Fournir les paramètres de connexion à la base de donnée
    connexion_ini_dic = config["database_params"]
    if connexion_ini_dic["dbname"] == "":
      connexion_ini_dic["dbname"] = "gus"

    connexion_0 = connexion_ini_dic

    # Paramètres de segmentation
    nature_mnh = config["info_mnh"]["pleiades_or_lidar"]
    if nature_mnh == "lidar" :
        minsize = 10
    else :
        minsize = 12

    # Paremètres de seuil de végétation avec le NDVI
    dic_ndvi_threshold = config["ndvi"]
    ndvi_threshold_summer = config["ndvi"]["threshold_summer"]
    ndvi_threshold_winter = config["ndvi"]["threshold_winter"]
    umc_pixels = config["ndvi"]["umc_pixels"]

    # Paramètres pour les routes
    dic_roads = config["roads"]

    # Seuils pour la distinction des strates verticales
    dic_seuils_stratesV = config["vertical_stratum_detection"]

    # Seuils pour la détection des formes végétales horizontales
    cleanfv = config["vegetation_form_stratum_detection"]["clean"]

    treethresholds = config["vegetation_form_stratum_detection"]["tree"]

    shrubthresholds = config["vegetation_form_stratum_detection"]["shrub"]

    herbaceousthresholds = {
            "rpg":  config["vegetation_form_stratum_detection"]["herbaceous"]["rpg"],
            "rpg_complete" : config["vegetation_form_stratum_detection"]["herbaceous"]["rpg_complete"],
            "paysages_urbains" : ""
        }


    dic_thresholds = {
      "tree" : treethresholds,
      "shrub" : shrubthresholds,
      "herbaceous" : herbaceousthresholds,
      "lcz" : config["data_entry"]["entry_options"]["lcz_information"]
    }

    # Paramètres de calcul des attributs
    # On n'a pas forcément besoin d'aller chercher dans le fichier config.
    dic_attributs = {
      "landscape_indicator" : [[config["indicators_computation"]["landscape"]["landscape_feature"]  ,config["indicators_computation"]["landscape"]["landscape_type"]]],
      "area_indicator" :  [[config["indicators_computation"]["area"]["area_feature"]  ,config["indicators_computation"]["area"]["area_type"]]],
      "height_indicators" : [[config["indicators_computation"]["height"]["mean_height_feature"]  ,config["indicators_computation"]["height"]["mean_height_type"]],
                             [config["indicators_computation"]["height"]["median_height_feature"]  ,config["indicators_computation"]["height"]["median_height_type"]],
                             [config["indicators_computation"]["height"]["std_height_feature"]  ,config["indicators_computation"]["height"]["std_height_type"]],
                             [config["indicators_computation"]["height"]["max_height_feature"]  ,config["indicators_computation"]["height"]["max_height_type"]],
                             [config["indicators_computation"]["height"]["min_height_feature"]  ,config["indicators_computation"]["height"]["min_height_type"]]],
      "coniferousdeciduous_indicators" : [[config["indicators_computation"]["coniferous_deciduous"]["coniferous_feature"]  ,config["indicators_computation"]["coniferous_deciduous"]["coniferous_type"]],
                                         [config["indicators_computation"]["coniferous_deciduous"]["deciduous_feature"]  ,config["indicators_computation"]["coniferous_deciduous"]["deciduous_type"]]],
      "evergreendeciduous_indicators" : [[config["indicators_computation"]["evergreen_deciduous"]["evergreen_feature"]  ,config["indicators_computation"]["evergreen_deciduous"]["evergreen_type"]],
                                          [config["indicators_computation"]["evergreen_deciduous"]["deciduous_feature"]  ,config["indicators_computation"]["evergreen_deciduous"]["deciduous_type"]]],
      "typeofground_indicator" : [[config["indicators_computation"]["ground_type"]["groundtype_feature"]  ,config["indicators_computation"]["ground_type"]["groundtype_type"]]],
      "confidence_indices" :[[config["indicators_computation"]["area"]["trust_area_feature"], config["indicators_computation"]["area"]["trust_area_type"]],
                             [config["indicators_computation"]["height"]["trust_height_feature"], config["indicators_computation"]["height"]["trust_height_type"]],
                             [config["indicators_computation"]["evergreen_deciduous"]["trust_everdecid_feature"], config["indicators_computation"]["evergreen_deciduous"]["trust_everdecid_type"]],
                             [config["indicators_computation"]["coniferous_deciduous"]["trust_conifdecid_feature"], config["indicators_computation"]["coniferous_deciduous"]["trust_conifdecid_type"]],
                             [config["indicators_computation"]["ground_type"]["trust_groundtype_feature"] , config["indicators_computation"]["ground_type"]["trust_groundtype_type"]]]
    }

    dic_params = {
      "img_ref" : img_ref,
      "img_mnh" : img_mnh,
      "img_wtr" : img_winter,
      "shp_zone" : shp_zone,
      "img_ndvi_spg" : "",
      "img_ndvi_wtr" : "",
      "ldsc_information" :{
        "dirname" : path_landscape,
        "img_landscape" : config["indicators_computation"]["landscape"]["landscape_data"],
        "ocsge" : config["data_entry"]["entry_options"]["ocsge"]   ,
        "lcz_information" : config["data_entry"]["entry_options"]["lcz_information"]   ,
        "lcz_urbain" : "",
        "img_ocs" : "",
        "ldsc_class" : config["indicators_computation"]["landscape"]["landscape_dic_classes"]
        },
      "ndvi_difference_everdecid_thr" : config["indicators_computation"]["evergreen_deciduous"]["ndvi_difference_thr"],
      "superimpose_choice" : False,
      "pir_difference_thr" : config["indicators_computation"]["coniferous_deciduous"]["pir_difference_thr"],
      "ndvi_difference_groundtype_thr" : config["indicators_computation"]["ground_type"]["ndvi_difference_thr"]
    }

    dic_vegetation_detection = {
          "vegetation_detection_step" : config["steps_to_run"]["vegetation_extraction"],
          "vegetation_mask" : config["data_entry"]["entry_options"]["mask_vegetation"]
      }

    #######################################################
    # CRÉATION DES CHEMINS D'ACCES DANS LE DOSSIER PROJET #
    #                 AUX FICHIERS CRÉÉS                  #
    #######################################################

    if img_ref == "" and config["steps_to_run"]["img_assembly"]:
      img_ref = path_data_entry + os.sep + 'img_ref.tif'

    img_stack = path_data_prod + os.sep + 'img_stack.tif'

    if img_mnh == '':
      img_mnh = path_data_prod + os.sep + 'mnh.tif'

    img_ndvi = path_tmp_neochannels + os.sep + 'img_ref_NDVI.tif'
    img_sfs = path_tmp_neochannels + os.sep + 'img_ref_SFS.tif'
    img_ndvi_winter = path_tmp_neochannels + os.sep + 'img_winter_NDVI.tif'

    img_ref_assemble = path_image_assemble + os.sep + 'img_ref.tif'
    img_ref_pan_assemble = path_image_assemble + os.sep + 'img_ref_pan.tif'
    img_winter_assemble = path_image_assemble + os.sep + 'img_winter.tif'
    img_pan_assemble_SI =  path_image_assemble + os.sep + 'img_pan_SI.tif'
    img_ref_assemble_SI =  path_image_assemble + os.sep + 'img_ref_SI.tif'
    img_winter_assemble_SI = path_image_assemble + os.sep + 'img_winter_SI.tif'

    img_ref = path_img_cut + os.sep + 'img_ref_cut.tif'
    img_ref_PAN = path_img_cut + os.sep + 'img_ref_pan_cut.tif'
    img_winter = path_img_cut + os.sep + 'img_winter_cut.tif'
    img_mnh_cut = path_tmp_neochannels + os.sep + 'img_mnh_cut.tif'
    rpg_cut = path_img_cut + os.sep + 'rpg_cut.gpkg'
    rpg_complete_cut = path_img_cut + os.sep + 'rpg_complete_cut.gpkg'

    dic_ndvi = {
        "ndvi_summer" : img_ndvi,
        "ndvi_winter" : img_ndvi_winter
    }


    dic_neochannels = {
      "ndvi" : img_ndvi,
      "sfs" : img_sfs,
    }

    img_neocanaux = path_data_prod + os.sep + 'img_neocanaux.tif'

    # Chemin d'accès vers la couche de segments végétation
    sgts_veg = path_stratesveg + os.sep + 'vect_sgt_vegetation.gpkg'
    sgts_tree = path_stratesveg + os.sep + 'vect_sgt_mnh_tree.gpkg'

    # Chemins d'accès vers les données des strates verticales
    path_stratesv_vegetation = path_stratesveg + os.sep + 'vect_stratesV.gpkg'
    path_st_arbore = path_stratesveg + os.sep + 'strate_arbore.gpkg'
    path_st_arbustif = path_stratesveg + os.sep + 'strate_arbustive.gpkg'
    path_st_herbace = path_stratesveg + os.sep + 'strate_herbace.gpkg'

    output_stratesv_layers ={
      "tree" : path_st_arbore,
      "shrub" : path_st_arbustif,
      "herbaceous" : path_st_herbace,
      "output_stratesv" : path_stratesv_vegetation
    }

    # Chemins d'accès vers les données des formes végétales horizontales
    path_fv_vegetation = path_fv + os.sep + 'vegetation_fv.gpkg'
    fv_st_arbore = path_fv + os.sep + 'fv_st_arbore.gpkg'
    fv_st_arbustif = path_fv + os.sep + 'fv_st_arbustif.gpkg'
    fv_st_herbace = path_fv + os.sep + 'fv_st_herbace.gpkg'

    output_fv_layers ={
      "tree" : fv_st_arbore,
      "shrub" : fv_st_arbustif,
      "herbaceous" : fv_st_herbace,
      "output_fv" : path_fv_vegetation,
      "img_ref" : img_ref
    }


    # Chemin d'accès vers la donnée finale de cartographie détaillée de la végétation
    path_finaldata = path_datafinal + os.sep + "cartographie_detaillee_vegetation.gpkg"

    #######################################################
    #           CRÉATION DE LA BASE DE DONNÉES            #
    #######################################################

    # Dictionnaire des paramètres BD de classification en strates verticales
    connexion_stratev_dic = connexion_ini_dic
    connexion_stratev_dic["schema"] = 'classification_stratesv'

    # Dictionnaire des paramètres BD des données finales (cartographie) dont les formes végétales horizontales
    connexion_datafinal_dic = connexion_ini_dic
    connexion_datafinal_dic["schema"] = 'data_final'

    # Création de la DB si elle n'est pas encore créée
    ###### -------- effacer la DB si elle existe ! -------- ######
    try :
        connexion = openConnection(connexion_0["dbname"], user_name=connexion_0["user_db"], password=connexion_0["password_db"], ip_host=connexion_0["server_db"], num_port=connexion_0["port_number"], schema_name=connexion_0["schema"])
    except:
        print("La BD " + connexion_0["dbname"]  +" n'existe pas, nous la créons.")
        createDatabase(connexion_ini_dic["dbname"], user_name=connexion_ini_dic["user_db"], password=connexion_ini_dic["password_db"], ip_host=connexion_ini_dic["server_db"], num_port=connexion_ini_dic["port_number"], schema_name=connexion_ini_dic["schema"])

    # Connexion à la base de données
    connexion = openConnection(connexion_ini_dic["dbname"], user_name=connexion_ini_dic["user_db"], password=connexion_ini_dic["password_db"], ip_host=connexion_ini_dic["server_db"], num_port=connexion_ini_dic["port_number"], schema_name=connexion_ini_dic["schema"])

    # Création des extensions : postgis et sfcgal
    createExtension(connexion, 'postgis')
    createExtension(connexion, 'postgis_sfcgal')

    # Création des schémas
    if schemaExist(connexion, connexion_stratev_dic["schema"]) == False:
      createSchema(connexion, connexion_stratev_dic["schema"])
    if schemaExist(connexion, connexion_datafinal_dic["schema"]) == False:
      createSchema(connexion, connexion_datafinal_dic["schema"])

    closeConnection(connexion)

    connexion = openConnection(connexion_stratev_dic["dbname"], user_name=connexion_stratev_dic["user_db"], password=connexion_stratev_dic["password_db"], ip_host=connexion_stratev_dic["server_db"], num_port=connexion_stratev_dic["port_number"], schema_name=connexion_stratev_dic["schema"])

    query ="""
    SELECT format('DROP TABLE %s.%s', table_schema, table_name)
    FROM information_schema.tables
    WHERE table_schema = '%s';
    """ %('%I', '%I',connexion_stratev_dic["schema"])
    cursor = connexion.cursor()
    cursor.execute(query)
    tables_schema = cursor.fetchall()
    for el in tables_schema:
        executeQuery(connexion, el[0])

    closeConnection(connexion)

    #######################################################
    #                   TRAITEMENTS                       #
    #######################################################

    print(bold + cyan + "*********************************************** \n*** Cartographie détaillée de la végétation *** \n***********************************************" + endC)


    if debug >= 1:
      print(bold + cyan + "\nCréation structure du dossier de projet" + endC)
      print("Répertoire : " + repertory_prj)


    # 0# PRE-TRAITEMENTS #0#
    if debug >= 1:
      print(bold + cyan + "\n*0* PRÉ-TRAITEMENTS" + endC)


    # IMAGES ASSEMBLY
    """
    img_ref_assemble = assemblyRasters(shp_zone, image_summer_ref, img_ref_assemble, format_raster = 'GTiff', format_vector = 'ESRI Shapefile', ext_list = ['tif','TIF','tiff','TIFF','ecw','ECW','jp2','JP2','asc','ASC'], rewrite = True, save_results_intermediate = save_intermediate_result)
    img_ref_pan_assemble = assemblyRasters(shp_zone, image_summer_ref_PAN, img_ref_pan_assemble, format_raster = 'GTiff', format_vector = 'ESRI Shapefile', ext_list = ['tif','TIF','tiff','TIFF','ecw','ECW','jp2','JP2','asc','ASC'], rewrite = True, save_results_intermediate = save_intermediate_result)
    img_winter_assemble = assemblyRasters(shp_zone, image_winter, img_winter_assemble, format_raster = 'GTiff', format_vector = 'ESRI Shapefile', ext_list = ['tif','TIF','tiff','TIFF','ecw','ECW','jp2','JP2','asc','ASC'], rewrite = True, save_results_intermediate = save_intermediate_result)
    """
    img_ref_assemble = image_summer_ref
    img_ref_pan_assemble = image_summer_ref_PAN
    img_winter_assemble = image_winter

    # Découpage des images sur l'emprise
    cutImageByVector(shp_zone ,img_ref_assemble, img_ref)
    cutImageByVector(shp_zone ,img_ref_pan_assemble, img_ref_PAN)
    cutImageByVector(shp_zone,img_winter_assemble, img_winter)

    # MNH CREATION
    if config["steps_to_run"]["create_DHM"]:
      if debug >= 1:
        print(cyan + "\nCréation du MNH" + endC)

      mnhCreation(image_mns, image_mnt, img_mnh, shp_zone , img_ref,  epsg=2154, nivellement = True, format_raster = 'GTiff', format_vector = 'ESRI Shapefile',  overwrite = True, save_intermediate_result=save_intermediate_result)

    # CALCUL DES NEOCANAUX
    # Calcul du NDVI, du SFS et découpage du MNH
    if config["steps_to_run"]["neochannels_computation"]:
      if debug >= 1:
        print(cyan + "\nCalcul des néocanaux" + endC)

      neochannelComputation(img_ref, img_ref_PAN, dic_neochannels, shp_zone, save_intermediate_result=save_intermediate_result, overwrite = True, debug=debug)

    else :
        createNDVI(img_ref, img_ndvi, channel_order = ["Red","Green","Blue","NIR"], codage="float", debug = debug)

    cutImageByVector(shp_zone, img_mnh, img_mnh_cut, no_data_value = -99)
    img_mnh = img_mnh_cut

    dic_ndvi["mnh"] = img_mnh
    dic_neochannels["mnh"] = img_mnh
    raster_dic = {
        "MNH" : dic_neochannels["mnh"],
        "TXT" : dic_neochannels["sfs"]
    }

    # CALCUL NDVI

    createNDVI(img_winter, img_ndvi_winter, channel_order = ["Red","Green","Blue","NIR"], codage="float", debug = debug)


    # CONCATENATION DES NEOCANAUX
    dic_stack = {
      "rvbpir" : img_ref,
      "mnh" : img_mnh,
      "sfs" : img_sfs,
      "ndvi" : img_ndvi,
    }

    if config["steps_to_run"]["data_concatenation"]:
      if debug >= 1:
        print(cyan + "\nConcaténation des néocanaux" + endC)

      concatenateData(dic_stack, img_stack, img_ref, shp_zone, debug=debug)

    else :
      if config["data_entry"]["entry_options"]["img_data_concatenation"] != "" :
        img_stack = config["data_entry"]["entry_options"]["img_data_concatenation"]

    # PAYSAGES

    dic_params["img_ref"] = img_ref
    dic_params["img_mnh"] = img_mnh
    dic_params["img_winter"] = img_winter
    dic_params["img_ndvi_spg"] = img_ndvi
    dic_params["img_ndvi_wtr"] = img_ndvi_winter


    # Ouverture connexion
    connexion = openConnection(connexion_datafinal_dic["dbname"], user_name = connexion_datafinal_dic["user_db"], password=connexion_datafinal_dic["password_db"], ip_host = connexion_datafinal_dic["server_db"], num_port=connexion_datafinal_dic["port_number"], schema_name = connexion_datafinal_dic["schema"])

    # Création des paysages
    if dic_params["ldsc_information"]["img_landscape"] == "":
        if debug >= 1:
            print(cyan + "\nCréation des paysages" + endC)
        result, dic_params = landscapeDetection(connexion, connexion_datafinal_dic ,dic_params, path_landscape, save_intermediate_result = save_intermediate_result,debug = 0)

    # Création des paysages urbains
    dic_params = urbanLandscapeDetection(connexion, connexion_datafinal_dic, dic_params, path_landscape, save_intermediate_result = False ,debug = 0)
    dic_thresholds["herbaceous"]["paysages_urbains"] = dic_params["ldsc_information"]["lcz_urbain"]

    # Fermeture connexion
    closeConnection(connexion)

    # DECOUPAGE DU RPG ET RPG COMPLETE SUR L'EMPRISE

    rpg = herbaceousthresholds["rpg"]
    rpg_complete = herbaceousthresholds["rpg_complete"]

    command = "ogr2ogr -clipsrc %s %s %s  -nlt POLYGONE -overwrite -f GPKG" %(shp_zone, rpg_cut, rpg)
    if debug >=2:
        print(command)
    exit_code = os.system(command)
    if exit_code != 0:
        print(cyan + "Découpage du RPG sur la zone d'étude : " + bold + red + "!!! Une erreur c'est produite au cours du découpage du vecteur : " + rpg + endC, file=sys.stderr)
    if debug >=2:
        print(cyan + "Découpage du RPG sur la zone d'étude : " + endC + "Le fichier vecteur " + rpg  + " a ete decoupe resultat : " + rpg_cut + " type geom = POLYGONE")

    herbaceousthresholds["rpg"] = rpg_cut

    if rpg_complete != "" and rpg_complete != None :

        command = "ogr2ogr -clipsrc %s %s %s  -nlt POLYGONE -overwrite -f GPKG" %(shp_zone, rpg_complete_cut, rpg_complete)
        if debug >=2:
            print(command)
        exit_code = os.system(command)
        if exit_code != 0:
            print(cyan + "Découpage du RPG sur la zone d'étude : " + bold + red + "!!! Une erreur c'est produite au cours du découpage du vecteur : " + rpg_complete + endC, file=sys.stderr)
        if debug >=2:
            print(cyan + "Découpage du RPG sur la zone d'étude : " + endC + "Le fichier vecteur " + rpg_complete  + " a ete decoupe resultat : " + rpg_complete_cut + " type geom = POLYGONE")

        herbaceousthresholds["rpg_complete"] = rpg_complete_cut


    # 2# DISTINCTION DES STRATES VERTICALES VEGETALES #2#
    if debug >= 1:
        print(bold + cyan + "\n*2* DISTINCTION DES STRATES VERTICALES VEGETALES" + endC)

    if config["steps_to_run"]["vertical_stratum_detection"]:
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

      # 1.Segmentation de l'image
      if debug >= 1:
        print(cyan + "\nSegmentation de l'image de végétation " + endC)


      segmentationImageVegetetation(img_stack, dic_ndvi, sgts_veg, sgts_tree, dic_ndvi_threshold, dic_vegetation_detection, param_minsize = minsize, format_vector='GPKG', save_intermediate_result = save_intermediate_result, overwrite = True)


      # 2.Classification en strates verticales
      if debug >= 1:
        print(cyan + "\nClassification des segments végétation en strates verticales " + endC)

      # Ouverture connexion
      connexion = openConnection(connexion_stratev_dic["dbname"], user_name=connexion_stratev_dic["user_db"], password=connexion_stratev_dic["password_db"], ip_host=connexion_stratev_dic["server_db"], num_port=connexion_stratev_dic["port_number"], schema_name=connexion_stratev_dic["schema"])

      # Nom attribué à la table de référence des segments végétation classés en strates verticales
      tab_ref_stratesv = 'segments_vegetation'
      schem_tab_ref_stratesv = 'data_final.segments_vegetation'

      tab_ref_stratesv = classificationVerticalStratum(connexion, connexion_stratev_dic, img_ref, output_stratesv_layers, sgts_veg, sgts_tree, raster_dic, tab_ref = tab_ref_stratesv, dic_seuil = dic_seuils_stratesV, format_type = 'GPKG', save_intermediate_result = save_intermediate_result, overwrite = True, debug = debug)

      closeConnection(connexion)


      print(bold + green + "\nLa distinction des strates vertciales végétales s'est bien déroulée. Le résultat est disponible dans la table %s et dans le(s) fichier(s) %s"%(tab_ref_stratesv, output_stratesv_layers) + endC)
    else :
      if not config["vertical_stratum_detection"]["db_table"]:
        schem_tab_ref_stratesv = connexion_stratev_dic["schema"] + '.' + 'segments_vegetation'
        tab_ref_stratesv = 'segments_vegetation'
      else :
        schem_tab_ref_stratesv = config["vertical_stratum_detection"]["db_table"]
        tab_ref_stratesv = schem_tab_ref_stratesv.split(".")[1]

    # 3# DETECTION DES FORMES VEGETALES HORIZONTALES #3#
    if debug >= 1:
        print(bold + cyan + "\n*3* DETECTION DES FORMES VEGETALES HORIZONTALES" + endC)

    if config["steps_to_run"]["vegetation_form_stratum_detection"]:
      if debug >= 1:
        print(cyan + "\nClassification des segments végétation en formes végétales" + endC)

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

      # Ouverture connexion
      connexion = openConnection(connexion_datafinal_dic["dbname"], user_name = connexion_datafinal_dic["user_db"], password=connexion_datafinal_dic["password_db"], ip_host = connexion_datafinal_dic["server_db"], num_port=connexion_datafinal_dic["port_number"], schema_name = connexion_datafinal_dic["schema"])

      tab_ref_fv = cartographyVegetation(connexion, connexion_datafinal_dic, schem_tab_ref_stratesv, shp_zone, dic_roads, dic_thresholds, raster_dic, output_fv_layers, cleanfv, save_intermediate_result = save_intermediate_result, overwrite = True,  debug = debug)

      closeConnection(connexion)
      print(bold + green + "\nLa détection des formes végétales horizontales s'est bien déroulée. Le résultat est disponible dans la table %s et dans le(s) fichier(s) %s"%(tab_ref_fv, output_fv_layers) + endC)

    else :
      if not config["vegetation_form_stratum_detection"]["db_table"] :
        tab_ref_fv = 'vegetation_to_clean'
      else:
        schem_tab_ref_fv = config["vegetation_form_stratum_detection"]["db_table"]
        tab_ref_fv = schem_tab_ref_fv.split(".")[1]

      print(bold + green + "\nLa donnée est déjà disponible. La table correspondant : " + tab_ref_fv + endC)

    # 4# Calcul des indicateurs de végétation
    if debug >= 1:
        print(bold + cyan + "\n*4* CALCUL DES ATTRIBUTS DESCRIPTIFS DES FORMES VEGETALES" + endC)

    if config["steps_to_run"]["indicators_computation"] == True :
      if debug >= 1:
        print(cyan + "\nCalcul des attributs descriptifs des formes végétales" + endC)

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

      # Import en base de la couche vecteur vegetation
      tab_ref_fv = 'vegetation_to_clean'
      vector_vegetation_clean = path_fv + os.sep + 'vegetation_fv_lis.gpkg'
      importVectorByOgr2ogr(connexion_datafinal_dic["dbname"], vector_vegetation_clean, tab_ref_fv, user_name=connexion_datafinal_dic["user_db"], password=connexion_datafinal_dic["password_db"], ip_host=connexion_datafinal_dic["server_db"], num_port=connexion_datafinal_dic["port_number"], schema_name=connexion_datafinal_dic["schema"], epsg=str(2154))

      # Ouverture connexion
      connexion = openConnection(connexion_datafinal_dic["dbname"], user_name = connexion_datafinal_dic["user_db"], password=connexion_datafinal_dic["password_db"], ip_host = connexion_datafinal_dic["server_db"], num_port=connexion_datafinal_dic["port_number"], schema_name = connexion_datafinal_dic["schema"])

      # Nettoyage des colonnes (suppression de la colonne cat et renomage de la colonne ogc_fid en fid)
      dropColumn(connexion, tab_ref_fv, "cat")

      # Calcul des indices

      createAndImplementFeatures(connexion, connexion_datafinal_dic, tab_ref_fv, dic_attributs, dic_params, repertory = path_datafinal, output_layer = path_finaldata, save_intermediate_result = save_intermediate_result, debug = debug)

      closeConnection(connexion)

    f.close()
