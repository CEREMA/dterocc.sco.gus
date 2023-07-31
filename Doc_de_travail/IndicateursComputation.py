from __future__ import print_function
import os,sys,glob,shutil,string, argparse
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_file import cleanTempData, deleteDir, removeFile
from CrossingVectorRaster import *
from rasterstats import *
from Lib_postgis import *

def createAllIndicatorsAttributs():
    """
    """

    # Connexion à la base de donnée et au schéma

    # Création des attributs concernés pour toutes les entités de la table

    return

def areaIndicator(connexion, tablename, columnname):
    """
    Rôle : implémente l'attribut de surface

    Paramètres :
        connexion : 
        tablename :
        columnname : 
    """

    query = """
    UPDATE %s as t SET %s = public.ST_AREA(t.geom) WHERE t.fid = t.fid;
    """ %(tablename, columnname)

    #Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    return

def heightIndicators(connexion, connexion_dic,tablename, columnnamelist, img_mnh, repertory):

    """
    Rôle : implémente les attributs de hauteur

    Paramètres :
        connexion : 
        connexion_dic : 
        tablename : 
        columnnamelist : liste des noms de colonne des attributs de hauteur
        img_mnh : image MNH 
        repertory : repertoire temporaire dans lequel on sauvegarde les données intermédiaires
    """
    #Création d'un fichier vecteur temporaire 
    

    # #Fichiers intermédiaires MSAVI2
    # file_out_suffix_ndvi = "_tmp_ndvi"
    # ndvi_file_tmp = repertory_output + os.sep + file_name + file_out_suffix_ndvi + extension
    filetablevegin = repertory + os.sep + 'couche_vegetation_bis.gpkg'
    filetablevegout = repertory + os.sep + 'couche_vegetation_stats_mnh.gpkg'

    #Export de la table vegetation
    exportVectorByOgr2ogr(connexion_dic["dbname"], filetablevegin, tablename, user_name=connexion_dic["user_db"], password=connexion_dic["password_db"], ip_host=connexion_dic["server_db"], num_port=connexion_dic["port_number"],schema_name=connexion_dic["schema"], format_type='GPKG')


    #Calcul des statistiques de hauteur : min, max, mediane et écart-type   
    col_to_add_list = ["min", "max", "median", "mean","std"]
    col_to_delete_list = ["unique", "range"]
    class_label_dico = {}
    statisticsVectorRaster(img_mnh, filetablevegin, filetablevegout, band_number=1,enable_stats_all_count = False, enable_stats_columns_str = False, enable_stats_columns_real = True, col_to_delete_list = col_to_delete_list, col_to_add_list = col_to_add_list, class_label_dico = class_label_dico, path_time_log = "", clean_small_polygons = False, format_vector = 'GPKG',  save_results_intermediate= False, overwrite= True)
    
    tablenameout = 'tab_stats_hauteur_vegetation'
    #Import de la couche vecteur avec les statistiques en tant que table intermédiaire dans la bd
    importVectorByOgr2ogr(connexion_dic["dbname"], filetablevegout, tablenameout, user_name=connexion_dic["user_db"], password=connexion_dic["password_db"], ip_host=connexion_dic["server_db"], num_port=connexion_dic["port_number"],schema_name=connexion_dic["schema"], epsg=str(2154))


    #Implémentation des attributs  
    for id in range(len(columnnamelist)):
        if "max" in columnnamelist[id] :
            query = """
            UPDATE %s as t1 SET %s = t2.max FROM %s AS t2 WHERE t2.ogc_fid = t1.fid;
            """ %(tablename, columnnamelist[id], tablenameout)
        elif "min" in columnnamelist[id] :
            query = """
            UPDATE %s as t1 SET %s = t2.min FROM %s AS t2 WHERE t2.ogc_fid = t1.fid;
            """ %(tablename,columnnamelist[id], tablenameout)
        elif "mean" in columnnamelist[id] :
            query = """
            UPDATE %s as t1 SET %s = t2.mean FROM %s AS t2 WHERE t2.ogc_fid = t1.fid;
            """ %(tablename,columnnamelist[id], tablenameout)
        elif "median" in columnnamelist[id] :
            query = """
            UPDATE %s as t1 SET %s = t2.median FROM %s AS t2 WHERE t2.ogc_fid = t1.fid;
            """ %(tablename,columnnamelist[id], tablenameout)
        elif "std" in columnnamelist[id] :
            query = """
            UPDATE %s as t1 SET %s = t2.std FROM %s AS t2 WHERE t2.ogc_fid = t1.fid;
            """ %(tablename,columnnamelist[id], tablenameout)

        #Exécution de la requête SQL
        if debug >= 1:
            print(query)
        executeQuery(connexion, query)
    
    #Suppression du fichier vecteur intermediaire et de la table intermédiaire 
    if os.path.isfile(filetablevegin) :
        removeVectorFile(filetablevegin)
    if os.path.isfile(filetablevegout) :
        removeVectorFile(filetablevegout)

    dropTable(connexion, tablenameout)

    return

def calculateSpringAndWinterNdviImage(img_spg_input, img_wtr_input):

   


    repertory_output = os.path.dirname(img_spg_input) +os.sep + 'TMP_CALC_NDVI_IMAGE'
    extension = os.path.splitext(img_spg_input)[1]
    img_ndvi_spg = repertory_output + os.sep + 'img_ndvi_printemps' + extension
    img_ndvi_wtr = repertory_output + os.sep + 'img_ndvi_hiver' + extension

     #Creation du dossier temporaire s'il n'existe pas déjà :
    if not os.path.isdir(repertory_output):
        os.makedirs(repertory_output)

    #Calcul des images ndvi de printemps_été et d'hiver 
    cmd_ndvi_spg = "otbcli_BandMath -il %s -out %s -exp '(im1b4-im1b1)/(im1b4+im1b1)'" %(img_spg_input, img_ndvi_spg)
    os.system(cmd_ndvi_spg)

    cmd_ndvi_wtr = "otbcli_BandMath -il %s -out %s -exp '(im1b4-im1b1)/(im1b4+im1b1)'" %(img_wtr_input, img_ndvi_wtr)
    os.system(cmd_ndvi_wtr)

    return img_ndvi_spg, img_ndvi_wtr


def indicatorEvergreenDeciduous(connexion, connexion_dic, img_ref,img_ndvi_spg, img_ndvi_wtr, tablename, seuil = 0.10, columns_indics_name = ['perc_persistant', 'perc_caduque'], superimpose_choice = False, save_intermediate_results = False):
    """
    Rôle : cette fonction permet de calculer le pourçentage de persistants et de caduques sur les polygones en entrée

    Paramètres :
        connexion : variable de connexion à la BD
        connexion_dic : dictionnaire des paramètres de connexion à la base de données et au schéma correspondant
        img_ref : image Pléiades de référence
        img_ndvi_spg : image ndvi printemps
        img_ndvi_wtr : image ndvi hiver
        tablename : nom de la  table contenant les polygones de végétation détaillés de type nomduschema.nomdelatable
        seuil : valeur du seuil de PIR pour distinguer les conifères des feuillus. Par défaut : 0.10
        columns_indics_name : liste des noms de colonne des indicateurs à implémenter. Par défaut :['perc_persistant', 'perc_caduque'] 
        superimpose_choice : choix d'appliquer un superimpose sur une des deux images ndvi produites pour qu'elles se superposent parfaitement. Par défaut : False
        save_intermediate_results : garder ou non les fichiers temporaires. Par défaut : False

    """
    #Création du dossier temporaire et des fichiers temporaires
    repertory_output = os.path.dirname(img_ref) + os.sep + 'TMP_CALC_INDICATEURS_PERSCADU'
    extension = os.path.splitext(img_ref)[1]
    image_pers_out = repertory_output + os.sep + 'img_mask_persistants' + extension
    image_cadu_out = repertory_output + os.sep + 'img_mask_caduques' + extension

    vect_fv_pers_out = repertory_output + os.sep + 'vect_fv_stats_pers.gpkg'
    vect_fv_cadu_out = repertory_output + os.sep + 'vect_fv_stats_cadu.gpkg'


    filetablevegin = repertory_output + os.sep + 'couche_vegetation_bis.gpkg'

    #Creation du dossier temporaire s'il n'existe pas déjà :
    if not os.path.isdir(repertory_output):
        os.makedirs(repertory_output)

    # #Export de la table vegetation
    # exportVectorByOgr2ogr(connexion_dic["dbname"], filetablevegin, tablename, user_name=connexion_dic["user_db"], password=connexion_dic["password_db"], ip_host=connexion_dic["server_db"], num_port=connexion_dic["port_number"],schema_name=connexion_dic["schema"], format_type='GPKG')
   

    # #Superimpose si souhaité 
    # if superimpose_choice :
    #     img_ndvi_si_wtr = repertory_output + os.sep + 'img_ndvi_si_hiver' + extension
    #     cmd_superimpose = "otbcli_Superimpose -inr %s -inm %s -out %s" %(img_ndvi_spg,img_ndvi_wtr, img_ndvi_si_wtr)
    #     try:
    #         os.system(cmd_superimpose)
    #         img_ndvi_wtr = img_ndvi_si_wtr
    #     except :
    #         raise Exception("La fonction Superimpose s'est mal déroulée.")
        

    # #Calcul du masque de caduques
    # cmd_mask_cadu = "otbcli_BandMath -il %s %s -out '%s?&nodata=-99' uint8 -exp '(abs(im2b1-im1b1)>%s)?1:0'" %(img_ndvi_spg, img_ndvi_wtr, image_cadu_out, seuil)
    # try:
    #     os.system(cmd_mask_cadu)
    # except :
    #     raise Exception("Les deux images NDVI n'ont pas la même emprise. Veuillez relancer le programme en sélectionnant l'option de Superimpose")

    # #Calcul du masque de persistants
    # cmd_mask_pers = "otbcli_BandMath -il %s %s -out '%s?&nodata=-99' uint8 -exp '(abs(im2b1-im1b1)<=%s)?1:0'" %(img_ndvi_spg, img_ndvi_wtr, image_pers_out, seuil)
    # os.system(cmd_mask_pers)
    

    # #Statistiques zonales sur les polygones de formes végétales concernées : tous les segments appartennant à la strate arborée et arbustive
    # col_to_add_list = ["count"]
    # col_to_delete_list = ["unique", "range", "max", "median", "mean","std", "sum"]
    # class_label_dico = {0:'non', 1:'oui'}
    # statisticsVectorRaster(image_cadu_out, filetablevegin, vect_fv_cadu_out, band_number=1,enable_stats_all_count = False, enable_stats_columns_str = False, enable_stats_columns_real = True, col_to_delete_list = col_to_delete_list, col_to_add_list = col_to_add_list, class_label_dico = class_label_dico, path_time_log = "", clean_small_polygons = False, format_vector = 'GPKG',  save_results_intermediate= False, overwrite= True)
    
    # statisticsVectorRaster(image_pers_out, filetablevegin, vect_fv_pers_out, band_number=1,enable_stats_all_count = False, enable_stats_columns_str = False, enable_stats_columns_real = True, col_to_delete_list = col_to_delete_list, col_to_add_list = col_to_add_list, class_label_dico = class_label_dico, path_time_log = "", clean_small_polygons = False, format_vector = 'GPKG',  save_results_intermediate= False, overwrite= True)
    
    # #Export des données dans la BD et concaténation des colonnes

    # table_cadu = 'tab_fv_cadu'
    # importVectorByOgr2ogr(connexion_dic["dbname"], vect_fv_cadu_out, table_cadu, user_name=connexion_dic["user_db"], password=connexion_dic["password_db"], ip_host=connexion_dic["server_db"], num_port=connexion_dic["port_number"],schema_name=connexion_dic["schema"], epsg = str(2154))

    # table_pers = 'tab_fv_pers'
    # importVectorByOgr2ogr(connexion_dic["dbname"], vect_fv_pers_out, table_pers, user_name=connexion_dic["user_db"], password=connexion_dic["password_db"], ip_host=connexion_dic["server_db"], num_port=connexion_dic["port_number"],schema_name=connexion_dic["schema"], epsg = str(2154))

    # query = """
    # CREATE TABLE tab_indic_pers_cadu AS
    #     SELECT t1.ogc_fid AS fid, t1.oui AS pers_count, t2.oui AS cadu_count
    #     FROM %s AS t1, %s AS t2
    #     WHERE t1.ogc_fid = t2.ogc_fid;
    # """ %(table_pers,table_cadu)

    # #Exécution de la requête SQL
    # if debug >= 1:
    #     print(query)
    # executeQuery(connexion, query)

    #Update de l'attribut perc_caduque et perc_persistant

    query = """
    UPDATE %s AS t SET %s = t2.pers_count FROM tab_indic_pers_cadu AS t2 WHERE t.fid = t2.fid and t.strate in ('arbore', 'arbustif');
    """ %(tablename, columns_indics_name[0])

    query += """
    UPDATE %s AS t SET %s = t2.cadu_count FROM tab_indic_pers_cadu AS t2 WHERE t.fid = t2.fid and t.strate in ('arbore', 'arbustif');
    """ %(tablename, columns_indics_name[1])

    #Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    #Suppression du dossier temporaire
    if not save_intermediate_results:
        if os.path.exists(repertory_output):
            removeDir(repertory_output)

    return

def indicatorConiferousDeciduous(connexion, connexion_dic, image_input, tablename, seuil = 1300, columns_indics_name = ['perc_conifere', 'perc_feuillu'], save_intermediate_results = False):
    """
    Rôle : cette fonction permet de calculer le pourçentage de feuillus et de conifères sur les polygones en entrée

    Paramètres :
        connexion : variable de connexion à la BD
        connexion_dic : dictionnaire des paramètres de connexion à la base de données et au schéma correspondant
        image_input : image Pléiades d'entrée
        tablename : nom de la  table contenant les polygones de végétation détaillés de type nomduschema.nomdelatable
        seuil : valeur du seuil de PIR pour distinguer les conifères des feuillus. Par défaut : 1300
        columns_indics_name : liste des noms de colonne des indicateurs à implémenter. Par défaut :['perc_conifere', 'perc_feuillu'] 
        save_intermediate_results : garder ou non les fichiers temporaires

    """
    #Création du dossier temporaire et des fichiers temporaires
    repertory_output = os.path.dirname(image_input) + os.sep + 'TMP_CALC_INDICATEURS_CONFEUI'
    extension = os.path.splitext(image_input)[1]
    image_conif_out = repertory_output + os.sep + 'img_mask_coniferous' + extension
    image_feuill_out = repertory_output + os.sep + 'img_mask_feuillus' + extension

    vect_fv_conif_out = repertory_output + os.sep + 'vect_fv_stats_conif.gpkg'
    vect_fv_feuill_out = repertory_output + os.sep + 'vect_fv_stats_feuil.gpkg'

    #Creation du dossier temporaire s'il n'existe pas déjà :
    if not os.path.isdir(repertory_output):
        os.makedirs(repertory_output)

    #Calcul du masque de conifères
    cmd_mask_conif = "otbcli_BandMath -il %s -out %s -exp '(im1b4<%s)?1:0'" %(image_input, image_conif_out, seuil)
   # os.system(cmd_mask_conif)

    #Calcul du masque de feuillus
    cmd_mask_decid = "otbcli_BandMath -il %s -out %s -exp '(im1b4>=%s)?1:0'" %(image_input, image_feuill_out, seuil)
  #  os.system(cmd_mask_decid)

    #Export de la table vegetation

    filetablevegin = repertory_output + os.sep + 'couche_vegetation_bis.gpkg'

    #Export de la table vegetation
    # exportVectorByOgr2ogr(connexion_dic["dbname"], filetablevegin, tablename, user_name=connexion_dic["user_db"], password=connexion_dic["password_db"], ip_host=connexion_dic["server_db"], num_port=connexion_dic["port_number"],schema_name=connexion_dic["schema"], format_type='GPKG')



    #Statistiques zonales sur les polygones de formes végétales concernées : tous les segments appartennant à la strate arborée et arbustive
    col_to_add_list = ["count"]
    col_to_delete_list = ["unique", "range", "max", "median", "mean","std", "sum"]
    class_label_dico = {0:'non', 1:'oui'}
   # statisticsVectorRaster(image_conif_out, filetablevegin, vect_fv_conif_out, band_number=1,enable_stats_all_count = False, enable_stats_columns_str = False, enable_stats_columns_real = True, col_to_delete_list = col_to_delete_list, col_to_add_list = col_to_add_list, class_label_dico = class_label_dico, path_time_log = "", clean_small_polygons = False, format_vector = 'GPKG',  save_results_intermediate= False, overwrite= True)
    
   # statisticsVectorRaster(image_feuill_out, filetablevegin, vect_fv_feuill_out, band_number=1,enable_stats_all_count = False, enable_stats_columns_str = False, enable_stats_columns_real = True, col_to_delete_list = col_to_delete_list, col_to_add_list = col_to_add_list, class_label_dico = class_label_dico, path_time_log = "", clean_small_polygons = False, format_vector = 'GPKG',  save_results_intermediate= False, overwrite= True)
    
    #Export des données dans la BD et concaténation des colonnes

    table_conif = 'tab_fv_conif'
   # importVectorByOgr2ogr(connexion_dic["dbname"], vect_fv_conif_out, table_conif, user_name=connexion_dic["user_db"], password=connexion_dic["password_db"], ip_host=connexion_dic["server_db"], num_port=connexion_dic["port_number"],schema_name=connexion_dic["schema"], epsg=str(2154))

    table_feuill = 'tab_fv_feuill'
   # importVectorByOgr2ogr(connexion_dic["dbname"], vect_fv_feuill_out, table_feuill, user_name=connexion_dic["user_db"], password=connexion_dic["password_db"], ip_host=connexion_dic["server_db"], num_port=connexion_dic["port_number"],schema_name=connexion_dic["schema"], epsg=str(2154))

    query = """
    CREATE TABLE tab_indic_conif_decid AS
        SELECT t1.ogc_fid as fid, t1.oui AS conif_perc, t2.oui AS decid_perc
        FROM %s AS t1, %s AS t2
        WHERE t1.ogc_fid = t2.ogc_fid;
    """ %(table_conif, table_feuill)

    #Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    #Update de l'attribut perc_conif et perc_decid

    query = """
    UPDATE %s AS t SET %s = t2.conif_perc FROM tab_indic_conif_decid AS t2 WHERE t.fid = t2.fid and t.strate in ('arbore', 'arbustif');
    """ %(tablename, columns_indics_name[0])

    query += """
    UPDATE %s AS t SET %s = t2.decid_perc FROM tab_indic_conif_decid AS t2 WHERE t.fid = t2.fid and t.strate in ('arbore', 'arbustif');
    """ %(tablename, columns_indics_name[1])

    #Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    #Suppression du dossier temporaire
    if not save_intermediate_results:
        if os.path.exists(repertory_output):
            removeDir(repertory_output)


    return


def indicatorTypeofGround(connexion, connexion_dic, img_ref, img_ndvi_wtr, tablename, seuil  = 0.3, column_indic_name = 'type_sol', save_intermediate_results = False):
    """
    Rôle : cette fonction permet d'indiquer si le sol sous-jacent à la végétation est de type perméable ou imperméable

    Paramètres :
        connexion : variable de connexion à la BD
        connexion_dic : dictionnaire des paramètres de connexion à la base de données et au schéma correspondant
        image_ref : image Pléiades de référence
        tablename : nom de la  table contenant les polygones de végétation détaillés de type nomduschema.nomdelatable
        seuil : valeur du seuil de NDVI pour distinguer les surfaces perméables d'imperméables. Par défaut : 0.3
        column_indic_name : nom de la colonne de l'indicateur de type de sol. Par défaut : 'type_sol'
        save_intermediate_results : garder ou non les fichiers temporaires

    """
    #Création du dossier temporaire et des fichiers temporaires
    repertory_output = os.path.dirname(img_ref) + os.sep + 'TMP_CALC_INDICATEURS_TYPESOL'
    extension = os.path.splitext(img_ref)[1]
    image_permeable = repertory_output + os.sep + 'img_mask_permeable' + extension
    image_impermeable = repertory_output + os.sep + 'img_mask_impermeable' + extension

    vect_fv_perm_out = repertory_output + os.sep + 'vect_fv_stats_perm.gpkg'
    vect_fv_imperm_out = repertory_output + os.sep + 'vect_fv_stats_imperm.gpkg'

    #Creation du dossier temporaire s'il n'existe pas déjà :
    if not os.path.isdir(repertory_output):
        os.makedirs(repertory_output)
   
    # Import de la table vegetation en couche gpkg

    filetablevegin = repertory_output + os.sep + 'couche_vegetation_bis.gpkg'
 
    # exportVectorByOgr2ogr(connexion_dic["dbname"], filetablevegin, tablename, user_name=connexion_dic["user_db"], password=connexion_dic["password_db"], ip_host=connexion_dic["server_db"], num_port=connexion_dic["port_number"],schema_name=connexion_dic["schema"], format_type='GPKG')
    
    # #Calcul du masque perméable
    # cmd_mask_permeable = "otbcli_BandMath -il %s -out '%s?&nodata=-99' uint8 -exp '(im1b1<%s)?1:0'" %(img_ndvi_wtr, image_permeable, seuil)
    # os.system(cmd_mask_permeable)
    

    # #Calcul du masque imperméable
    # cmd_mask_impermeable = "otbcli_BandMath -il %s -out '%s?&nodata=-99' uint8 -exp '(im1b1<=%s)?1:0'" %(img_ndvi_wtr, image_impermeable, seuil)
    # os.system(cmd_mask_impermeable)
    

    # #Statistiques zonales sur les polygones de formes végétales concernées : tous les segments appartennant à la strate arborée et arbustive
    # col_to_add_list = ["count"]
    # col_to_delete_list = ["unique", "range", "max", "median", "mean","std", "sum"]
    # class_label_dico = {0:'non', 1:'oui'}
    # statisticsVectorRaster(image_permeable, filetablevegin, vect_fv_perm_out, band_number=1,enable_stats_all_count = False, enable_stats_columns_str = False, enable_stats_columns_real = True, col_to_delete_list = col_to_delete_list, col_to_add_list = col_to_add_list, class_label_dico = class_label_dico, path_time_log = "", clean_small_polygons = False, format_vector = 'GPKG',  save_results_intermediate= False, overwrite= True)
    
    # statisticsVectorRaster(image_impermeable, filetablevegin, vect_fv_imperm_out, band_number=1,enable_stats_all_count = False, enable_stats_columns_str = False, enable_stats_columns_real = True, col_to_delete_list = col_to_delete_list, col_to_add_list = col_to_add_list, class_label_dico = class_label_dico, path_time_log = "", clean_small_polygons = False, format_vector = 'GPKG',  save_results_intermediate= False, overwrite= True)
    
    #Export des données dans la BD et concaténation des colonnes

    table_perm = 'tab_fv_perm'
    # importVectorByOgr2ogr(connexion_dic["dbname"], vect_fv_perm_out, table_perm, user_name=connexion_dic["user_db"], password=connexion_dic["password_db"], ip_host=connexion_dic["server_db"], num_port=connexion_dic["port_number"],schema_name=connexion_dic["schema"], epsg=str(2154))

    table_imperm = 'tab_fv_imperm'
    # importVectorByOgr2ogr(connexion_dic["dbname"], vect_fv_imperm_out, table_imperm, user_name=connexion_dic["user_db"], password=connexion_dic["password_db"], ip_host=connexion_dic["server_db"], num_port=connexion_dic["port_number"],schema_name=connexion_dic["schema"], epsg=str(2154))

    query = """
    CREATE TABLE tab_indic_perm_imperm AS
        SELECT t1.ogc_fid AS fid, t1.oui AS perm_count, t2.oui AS imp_count
        FROM %s AS t1, %s AS t2
        WHERE t1.ogc_fid = t2.ogc_fid;
    """ %(table_perm,table_imperm)

    #Exécution de la requête SQL
    # if debug >= 1:
    #     print(query)
   # executeQuery(connexion, query)

    #Update de l'attribut perc_caduque et perc_persistant

    query = """
     UPDATE %s AS t SET %s = 'permeable herbace' FROM tab_indic_perm_imperm AS t2 WHERE t.fid = t2.ogc_fid AND t2.perm_count >= 50.0;
    """ %(tablename, column_indic_name)
    
    query += """
     UPDATE %s AS t SET %s = 'impermeable' FROM tab_indic_perm_imperm AS t2 WHERE t.fid = t2.ogc_fid AND t2.perm_count < 50.0;
    """ %(tablename, column_indic_name)

    #Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    #Correction pour les boisements et la strate herbacée --> hypothèse que ce n'est que du sol perméable sous-jacent
    query = """
    UPDATE %s AS t SET %s = 'permeable herbace' WHERE t.fv in ('boisement arbore', 'boisement arbustif');
    """ %(tablename, column_indic_name) 

    #Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)
    closeConnection(connexion)
    #Suppression du dossier temporaire
    if not save_intermediate_results:
        if os.path.exists(repertory_output):
            removeDir(repertory_output)

    return

