
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
    """

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
        tablename : 
        columnnamelist : liste des noms de colonne des attributs de hauteur
    """
    #Création d'un fichier vecteur temporaire 
    

    # #Fichiers intermédiaires MSAVI2
    # file_out_suffix_ndvi = "_tmp_ndvi"
    # ndvi_file_tmp = repertory_output + os.sep + file_name + file_out_suffix_ndvi + extension
    filetablevegin = repertory + 'couche_vegetation_bis.gpkg'
    filetablevegout = repertory + 'couche_vegetation_stats_mnh.gpkg'

    #Export de la table vegetation
    exportVectorByOgr2ogr(connexion_di["dbname"], filetablevegin, tablename, user_name=connexion_dic["user_db"], password=connexion_dic["password_db"], ip_host=connexion_dic["server_db"], num_port=connexion_dic["port_number"],schema_name=connexion_dic["user_name"], format_type='GPKG')


    #Calcul des statistiques de hauteur : min, max, mediane et écart-type   
    ol_to_add_list = ["min", "max", "median", "mean","std"]
    col_to_delete_list = ["unique", "range"]
    class_label_dico = {}
    statisticsVectorRaster(img_mnh, filetablevegin, filetablevegout, band_number=1,enable_stats_all_count = False, enable_stats_columns_str = False, enable_stats_columns_real = True, col_to_delete_list = col_to_delete_list, col_to_add_list = col_to_add_list, class_label_dico = class_label_dico, path_time_log = "", clean_small_polygons = False, format_vector = 'GPKG',  save_results_intermediate= False, overwrite= True)
    
    tablenameout = ''
    #Import de la couche vecteur avec les statistiques en tant que table intermédiaire dans la bd
    importVectorByOgr2ogr(connexion_dic["dbname"], filetablevegout, tablenameout, user_name=connexion_dic["user_db"], password=connexion_dic["password_db"], ip_host=connexion_dic["server_db"], num_port=connexion_dic["port_number"],schema_name=connexion_dic["user_name"], format_type='GPKG')

    #Implémentation des attributs  
    for id in columnnamelist:
        if "max" in columnnamelis[id] :
            query = """
            UPDATE %s as t1 SET %s = t2.max FROM %s AS t2 WHERE t1.fid = t2.fid;
            """ %(tablename, columnnamelis[id], tablenameout)
        elif "min" in columnnamelis[id] :
            query = """
            UPDATE %s as t1 SET %s = t2.min FROM %s AS t2 WHERE t1.fid = t2.fid;
            """ %(tablename,columnnamelis[id], tablenameout)
        elif "mean" in columnnamelis[id] :
            query = """
            UPDATE %s as t1 SET %s = t2.mean FROM %s AS t2 WHERE t1.fid = t2.fid;
            """ %(tablename,columnnamelis[id], tablenameout)
        elif "median" in columnnamelis[id] :
            query = """
            UPDATE %s as t1 SET %s = t2.median FROM %s AS t2 WHERE t1.fid = t2.fid;
            """ %(tablename,columnnamelis[id], tablenameout)
        elif "std" in columnnamelis[id] :
            query = """
            UPDATE %s as t1 SET %s = t2.std FROM %s AS t2 WHERE t1.fid = t2.fid;
            """ %(tablename,columnnamelis[id], tablenameout)

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

def indicatorEvergreenDeciduous(connexion, connexion_dic, vect_fv_in, img_prtps, img_hiver, table_fv_name, seuil = 0.10, columns_indics_name = ['perc_persistant', 'perc_caduque'] save_intermediate_results = False):
    """
    Rôle : cette fonction permet de calculer le pourçentage de persistants et de caduques sur les polygones en entrée

    Paramètres :
        connexion : variable de connexion à la BD
        connexion_dic : dictionnaire des paramètres de connexion à la base de données et au schéma correspondant
        vect_fv_in : couche vecteur de la végétation
        img_prtps : image Pléiades de printemps / été
        img_hiver : image Pléiades d'hiver
        table_fv_name : nom de la  table contenant les polygones de végétation détaillés de type nomduschema.nomdelatable
        seuil : valeur du seuil de PIR pour distinguer les conifères des feuillus. Par défaut : 0.10
        columns_indics_name : liste des noms de colonne des indicateurs à implémenter. Par défaut :['perc_persistant', 'perc_caduque'] 
        save_intermediate_results : garder ou non les fichiers temporaires. Par défaut : False

    """
    #Création du dossier temporaire et des fichiers temporaires
    repertory_output = os.path.dirname(img_prtps) + '_TMP_CALC_INDICATEURS_PERSCADU'
    extension = os.path.splitext(img_prtps)[1]
    image_pers_out = repertory_output + os.sep + 'img_mask_persistants' + extension
    image_cadu_out = repertory_output + os.sep + 'img_mask_caduques' + extension

    vect_fv_pers_out = repertory_output + os.sep + 'vect_fv_stats_pers.gpkg'
    vect_fv_cadu_out = repertory_output + os.sep + 'vect_fv_stats_cadu.gpkg'

    img_ndvi_prtps = repertory_output + os.sep + 'img_ndvi_printemps' + extension
    img_ndvi_hiver = repertory_output + os.sep + 'img_ndvi_hiver' + extension

    #Calcul des images ndvi de printemps_été et d'hiver 
    cmd_ndvi_prtps = "otbcli_BandMath -il %s -out %s -exp '(im1b4-im1b1)/(im1b4+im1b1)'" %(img_prtps, img_ndvi_prtps)
    os.system(cmd_ndvi_prtps)

    cmd_ndvi_hiver = "otbcli_BandMath -il %s -out %s -exp '(im1b4-im1b1)/(im1b4+im1b1)'" %(img_hiver, img_ndvi_hiver)
    os.system(cmd_ndvi_hiver)

    #Calcul du masque de caduques
    cmd_mask_cadu = "otbcli_BandMath -il %s %s -out '%s?&nodata=-99' uint8 -exp '(abs(im2b1-im1b1)>%s)?1:0'" %(img_ndvi_prtps, img_ndvi_hiver, image_cadu_out, seuil)
    os.system(cmd_mask_cadu)

    #Calcul du masque de caduques
    cmd_mask_pers = "otbcli_BandMath -il %s %s -out '%s?&nodata=-99' uint8 -exp '(abs(im2b1-im1b1)<=%s)?1:0'" %(img_ndvi_prtps, img_ndvi_hiver, image_pers_out, seuil)
    os.system(cmd_mask_pers)

    #Statistiques zonales sur les polygones de formes végétales concernées : tous les segments appartennant à la strate arborée et arbustive
    ol_to_add_list = ["count", "sum"]
    col_to_delete_list = ["unique", "range", "max", "median", "mean","std"]
    class_label_dico = {}
    statisticsVectorRaster(image_cadu_out, vect_fv_in, vect_fv_cadu_out, band_number=1,enable_stats_all_count = False, enable_stats_columns_str = False, enable_stats_columns_real = True, col_to_delete_list = col_to_delete_list, col_to_add_list = col_to_add_list, class_label_dico = class_label_dico, path_time_log = "", clean_small_polygons = False, format_vector = 'GPKG',  save_results_intermediate= False, overwrite= True)
    
    statisticsVectorRaster(image_pers_out, vect_fv_in, vect_fv_pers_out, band_number=1,enable_stats_all_count = False, enable_stats_columns_str = False, enable_stats_columns_real = True, col_to_delete_list = col_to_delete_list, col_to_add_list = col_to_add_list, class_label_dico = class_label_dico, path_time_log = "", clean_small_polygons = False, format_vector = 'GPKG',  save_results_intermediate= False, overwrite= True)
    
    #Export des données dans la BD et concaténation des colonnes

    table_cadu = 'tab_fv_cadu'
    importVectorByOgr2ogr(connexion_dic["dbname"], vect_fv_cadu_out, table_cadu, user_name=connexion_dic["user_db"], password=connexion_dic["password_db"], ip_host=connexion_dic["server_db"], num_port=connexion_dic["port_number"],schema_name=connexion_dic["user_name"], format_type='GPKG')

    table_pers = 'tab_fv_pers'
    importVectorByOgr2ogr(connexion_dic["dbname"], vect_fv_pers_out, table_pers, user_name=connexion_dic["user_db"], password=connexion_dic["password_db"], ip_host=connexion_dic["server_db"], num_port=connexion_dic["port_number"],schema_name=connexion_dic["user_name"], format_type='GPKG')

    query = """
    CREATE TABLE tab_indic_pers_cadu AS
        SELECT t1.fid, t1.sum AS pers_sum t1.count AS pers_count, t2.sum AS cadu_sum, t2.count AS cadu_count
        FROM %s AS t1, %s AS t2
        WHERE t1.fid = t2.fid;
    """ %(table_pers,table_cadu)

    #Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    #Update de l'attribut perc_caduque et perc_persistant

    query = """
    UPDATE %s AS t SET %s = (t2.pers_count*100/t2.pers_sum) FROM tab_indic_pers_cadu AS t2 WHERE t.fid = t2.fid and t.strate in ('arbore', 'arbustive');
    """ %(table_fv_name, columns_indics_nam[0])

    query += """
    UPDATE %s AS t SET %s = (t2.cadu_count*100/t2.cadu_sum) FROM tab_indic_pers_cadu AS t2 WHERE t.fid = t2.fid and t.strate in ('arbore', 'arbustive');
    """ %(table_fv_name, columns_indics_nam[1])

    #Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    #Suppression du dossier temporaire
    if not save_intermediate_results:
        if os.path.exists(repertory_output):
            removeDir(repertory_output)

    return

def indicatorConiferousDeciduous(connexion, connexion_dic, image_input, vect_fv_in, table_fv_name, seuil = 1300, columns_indics_name = ['perc_conifere', 'perc_feuillu'], save_intermediate_results = False):
    """
    Rôle : cette fonction permet de calculer le pourçentage de feuillus et de conifères sur les polygones en entrée

    Paramètres :
        connexion : variable de connexion à la BD
        connexion_dic : dictionnaire des paramètres de connexion à la base de données et au schéma correspondant
        image_input : image Pléiades d'entrée
        vect_fv_in : couche vecteur de la végétation
        table_fv_name : nom de la  table contenant les polygones de végétation détaillés de type nomduschema.nomdelatable
        seuil : valeur du seuil de PIR pour distinguer les conifères des feuillus. Par défaut : 1300
        columns_indics_name : liste des noms de colonne des indicateurs à implémenter. Par défaut :['perc_conifere', 'perc_feuillu'] 
        save_intermediate_results : garder ou non les fichiers temporaires

    """
    #Création du dossier temporaire et des fichiers temporaires
    repertory_output = os.path.dirname(image_input) + '_TMP_CALC_INDICATEURS_CONFEUI'
    extension = os.path.splitext(image_input)[1]
    image_conif_out = repertory_output + os.sep + 'img_mask_coniferous' + extension
    image_feuill_out = repertory_output + os.sep + 'img_mask_feuillus' + extension

    vect_fv_conif_out = repertory_output + os.sep + 'vect_fv_stats_conif.gpkg'
    vect_fv_feuill_out = repertory_output + os.sep + 'vect_fv_stats_feuil.gpkg'


    #Calcul du masque de conifères
    cmd_mask_conif = "otbli_BandMath -il %s -out %s -exp '(im1b4<%s)?1:0'" %(image_input, image_conif_out, seuil)
    os.system(cmd_mask_conif)

    #Calcul du masque de feuillus
    cmd_mask_decid = "otbli_BandMath -il %s -out %s -exp '(im1b4>=%s)?1:0'" %(image_input, image_feuill_out, seuil)
    os.system(cmd_mask_decid)

    #Statistiques zonales sur les polygones de formes végétales concernées : tous les segments appartennant à la strate arborée et arbustive
    ol_to_add_list = ["count", "sum"]
    col_to_delete_list = ["unique", "range", "max", "median", "mean","std"]
    class_label_dico = {}
    statisticsVectorRaster(image_conif_out, vect_fv_in, vect_fv_conif_out, band_number=1,enable_stats_all_count = False, enable_stats_columns_str = False, enable_stats_columns_real = True, col_to_delete_list = col_to_delete_list, col_to_add_list = col_to_add_list, class_label_dico = class_label_dico, path_time_log = "", clean_small_polygons = False, format_vector = 'GPKG',  save_results_intermediate= False, overwrite= True)
    
    statisticsVectorRaster(image_feuill_out, vect_fv_in, vect_fv_feuill_out, band_number=1,enable_stats_all_count = False, enable_stats_columns_str = False, enable_stats_columns_real = True, col_to_delete_list = col_to_delete_list, col_to_add_list = col_to_add_list, class_label_dico = class_label_dico, path_time_log = "", clean_small_polygons = False, format_vector = 'GPKG',  save_results_intermediate= False, overwrite= True)
    
    #Export des données dans la BD et concaténation des colonnes

    table_conif = 'tab_fv_conif'
    importVectorByOgr2ogr(connexion_dic["dbname"], vect_fv_conif_out, table_conif, user_name=connexion_dic["user_db"], password=connexion_dic["password_db"], ip_host=connexion_dic["server_db"], num_port=connexion_dic["port_number"],schema_name=connexion_dic["user_name"], format_type='GPKG')

    table_feuill = 'tab_fv_feuill'
    importVectorByOgr2ogr(connexion_dic["dbname"], vect_fv_feuill_out, table_feuill, user_name=connexion_dic["user_db"], password=connexion_dic["password_db"], ip_host=connexion_dic["server_db"], num_port=connexion_dic["port_number"],schema_name=connexion_dic["user_name"], format_type='GPKG')

    query = """
    CREATE TABLE tab_indic_conif_decid AS
        SELECT t1.fid, t1.sum AS conif_sum t1.count AS conif_count, t2.sum AS decid_sum, t2.count AS decid_count
        FROM %s AS t1, %s AS t2
        WHERE t1.fid = t2.fid;
    """ 
    #Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    #Update de l'attribut perc_conif et perc_decid

    query = """
    UPDATE %s AS t SET %s = (t2.conif_count*100/t2.conif_sum) FROM tab_indic_conif_decid AS t2 WHERE t.fid = t2.fid and t.strate in ('arbore', 'arbustive');
    """ %(table_fv_name, columns_indics_nam[0])

    query += """
    UPDATE %s AS t SET %s = (t2.decid_count*100/t2.decid_sum) FROM tab_indic_conif_decid AS t2 WHERE t.fid = t2.fid and t.strate in ('arbore', 'arbustive');
    """ %(table_fv_name, columns_indics_nam[1])

    #Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    #Suppression du dossier temporaire
    if not save_intermediate_results:
        if os.path.exists(repertory_output):
            removeDir(repertory_output)

    return
