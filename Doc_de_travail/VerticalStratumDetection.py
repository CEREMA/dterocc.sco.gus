from __future__ import print_function
import os,sys,glob,shutil,string, argparse
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_file import cleanTempData, deleteDir, removeFile
from CrossingVectorRaster import *
import pandas as pd
import geopandas as gpd
from rasterstats import *

def vegetationMask(img_input, img_output, num_class = {"bati" : 1, "route" : 2, "sol nu" : 3, "eau" : 4, "vegetation" : 5}, overwrite = True):
    """
    Rôle : créé un masque de végétation à partir d'une image classifiée

    Paramètres :
        img_input : image classée en 5 classes
        img_output : image binaire : 1 pour la végétation et -1 pour non végétation
        num_class : dictionnaire reliant le nom de la classe au label, par défaut : {"bati" : 1, "route" : 2, "sol nu" : 3, "eau" : 4, "vegetation" : 5}
        overwrite : paramètre de ré-écriture, par défaut : True
    """

    #Verification de la non existence du fichier de sortie
    if overwrite == True and os.path.exists(img_output):
        os.remove(img_output)
    elif overwrite == False and os.path.exists(img_output):
        raise NameError(bold + red + "vegetationMask() : le fichier %s existe déjà" %(img_output)+ endC)

    exp = '"(im1b1==' + str(num_class["vegetation"]) + '?1:-1)"'
    print(exp)

    cmd_mask = "otbcli_BandMath -il %s -out %s -exp %s" %(img_input, img_output, exp)

    exitCode = os.system(cmd_mask)

    if exitCode != 0:
        print(cmd_mask)
        raise NameError(bold + red + "vegetationMask() : une erreur est apparue lors de la création du masque de végétation (commande otbcli_BandMath)" + endC)

    return

def segmentationImageVegetetation(img_original, img_input, file_output, param_minsize = 10, num_class = {"bati" : 1, "route" : 2, "sol nu" : 3, "eau" : 4, "vegetation" : 5}, format_vector='GPKG', save_intermediate_result = True, overwrite = True):
    """
    Rôle : segmente l'image en entrée à partir d'une fonction OTB_Segmentation MEANSHIFT

    Paramètre :
        img_original : image originale rvbpir
        img_input : image classée en 5 classes
        file_output : couche vecteur de sortie correspondant au résultat de segmentation
        param_minsize : paramètre de la segmentation : taille minimale des segments, par défaut : 10
        num_class : dictionnaire reliant le nom de la classe au label, par défaut : {"bati" : 1, "route" : 2, "sol nu" : 3, "eau" : 4, "vegetation" : 5}
        format_vector : format du fichier vecteur de sortie, par défaut : GPKG
        save_intermediate_result : paramètre de sauvegarde des fichiers intermédiaire, par défaut : True
        overwrite : paramètre de ré-écriture des fichiers

    Sortie :
        file_output : couche vecteur de sortie correspondant au résultat de segmentation
    """

    # Utilisation d'un fichier temporaire pour la couche masque
    repertory_output = os.path.dirname(file_output)
    file_name = os.path.splitext(os.path.basename(file_output))[0]
    extension = os.path.splitext(img_input)[1]

    file_out_suffix_mask_veg= "_mask_veg"
    mask_veg = repertory_output + os.sep + file_name + file_out_suffix_mask_veg + extension

    if os.path.exists(mask_veg):
        os.remove(mask_veg)

    #Création du masque de végétation
    vegetationMask(img_input, mask_veg, num_class)

    #Calcul de la segmentation Meanshift
    sgt_cmd = "otbcli_Segmentation -in %s -mode vector -mode.vector.out %s -mode.vector.inmask %s -filter meanshift  -filter.meanshift.minsize %s" %(img_original, file_output, mask_veg, param_minsize)

    exitCode = os.system(sgt_cmd)

    if exitCode != 0:
        print(sgt_cmd)
        raise NameError(bold + red + "segmentationVegetation() : une erreur est apparue lors de la segmentation de l'image (commande otbcli_Segmentation)." + endC)

    return

def classificationVerticalStratum(connexion, connexion_dic, sgts_input, raster_dic, format_type = 'GPKG', save_intermediate_result = False, overwrite = True):
    """
    Rôle : classe les segments en trois strates : arborée, arbustive et herbacée

    Paramètres :
        connexion : image originale rvbpir
        connexion_dic : dictionnaire des paramètres de connexion selon le modèle : {"dbname" : 'projetgus', "user_db" : 'postgres', "password_db" : '', "server_db" : 'localhost', "port_number" : '5432', "schema" : ''}
        sgts_input : image classée en 5 classes
        raster_dic : dictionnaire associant le type de donnée récupéré avec le fichier raster contenant les informations, par exemple : {"mnh" : filename}
        format_type : format de la donnée vecteur en entrée, par défaut : GPKG
        save_intermediate_result : paramètre de sauvegarde des fichiers intermédiaire, par défaut : False
        overwrite : paramètre de ré-écriture des fichiers, par défaut True

    Sortie :
        file_output : couche vecteur de sortie correspondant au résultat de segmentation
    """
    li_tablename = []

    #Création d'une nouvelle couche avec les valeurs médianes de chaque image
    #Création du fichier
    repertory_output = os.path.dirname(sgts_input)
    file_name = os.path.splitext(os.path.basename(sgts_input))[0]
    extension_vecteur = os.path.splitext(sgts_input)[1]

    file_mnh_out = repertory_output + os.sep + file_name + "MNH" + extension_vecteur
    calc_statMedian(sgts_input, raster_dic["MNH"], file_mnh_out)

    #Export de la donnée dans la BD
    tablename_mnh = "table_sgts_mnh"
    exportVectorByOgr2ogr(connexion_dic["db_name"], file_mnh_out, tablename_mnh, user_name=connexion_dic["user_db"], password=connexion_dic["password_db"], ip_host=connexion_dic["server_db"], num_port=connexion_dic["port_number"], schema_name=connexion_dic["schema"], format_type=format_type)

    file_txt_out = repertory_output + os.sep + file_name + "TXT" + extension_vecteur
    calc_statMedian(sgts_input, raster_dic["TXT"], file_txt_out)

    #Export de la donnée dans la BD
    tablename_txt = "table_sgts_txt"
    exportVectorByOgr2ogr(connexion_dic["db_name"], file_txt_out, tablename_txt, user_name=connexion_dic["user_db"], password=connexion_dic["password_db"], ip_host=connexion_dic["server_db"], num_port=connexion_dic["port_number"], schema_name=connexion_dic["schema"], format_type=format_type)


    #Supprimer le fichier si on ne veut pas le sauvegarder
    if not save_intermediate_result :
        os.remove(file_mnh_out)
        os.remove(file_txt_out)


    #Merge des colonnes de statistiques en une seule table "segments_vegetation" : deux tables à merger normalement
    query = """
    CREATE TABLE segments_vegetation AS
        SELECT t1.median
        FROM %s as t1
        JOIN %s as t2 ON fid = fid;
    """ %(tablename_txt, tablename_mnh)



    return



def calc_statMedian(vector_input, image_input, vector_output):
    """
    Rôle : croisement raster/vecteur où on va calculer la médiane du raster sur l'emprise des entités vecteurs

    Paramètres :
        vector_input : couche vecteur sur laquelle on vient calculer la médiane du raster input
        image_input : couche raster
        vector_output : couche vecteur en sortie pour lequelle on a calculé les statistiques
    """
    #data = gpd.read_file(vector_input)
    #for el in data :
    #    print(zonal_stats(data[1],image_input, stats=['median']))
    #med = zonal_stats(vector_input, image_input, stats=['median'])
    #print(med)
    #On utilise rasterStats
    col_to_add_list = ["median_mnh"]
    col_to_delete_list = []
    class_label_dico = {}
    statisticsVectorRaster(image_input, vector_input, vector_output, band_number=1,enable_stats_all_count = False, enable_stats_columns_str = False, enable_stats_columns_real = True, col_to_delete_list = col_to_delete_list, col_to_add_list = col_to_add_list, class_label_dico = class_label_dico, path_time_log = "", clean_small_polygons = False, format_vector = 'GPKG',  save_results_intermediate= False, overwrite= True)
    return


