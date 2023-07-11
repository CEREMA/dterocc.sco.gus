
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
    
    #Suppression du fichier vecteur intermediaire et de la table intermédiaire 
    if os.path.isfile(filetablevegin) :
        removeVectorFile(filetablevegin)
    if os.path.isfile(filetablevegout) :
        removeVectorFile(filetablevegout)

    dropTable(connexion, tablenameout)

    return

def indicatorConiferousDeciduous():
    """
    Rôle : cette fonction permet de calculer le pourçentage de feuillus et de conifères sur les polygones en entrée
    """

    #Calcul du masque de conifères
    cmd_mask_conif = "otbli_BandMath -il %s -out %s -exp '(im1b4<1300)?1:0'"


    #Calcul du masque de feuillus
    cmd_mask_decid = "otbli_BandMath -il %s -out %s -exp '(im1b4>=1300)?1:0'"

    #Calcul du masque avec les trois tupes : conifères, feuillus et ombres
    cmd_

    #Statistiques zonales sur les polygones de formes végétales concernées : tous les segments appartennant à la strate arborée et arbustive

    #Calcul des statistiques zonales sur l'ensemble des polygones de végétation (même si on n'en a pas besoin pour la strate herbacé)



