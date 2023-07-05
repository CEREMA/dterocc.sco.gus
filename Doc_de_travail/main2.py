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

if __name__ == "__main__":

    #Strate arborée
    connexion = openConnection('etape2', user_name='postgres', password="", ip_host='localhost', num_port='5432', schema_name='donneelidar')

    #Initialisation du dictionnaire contenant les valeurs seuils pour la classification des entités de la strate arborée
    connexion_fv_dic = {"dbname" : 'etape2', "user_db" : 'postgres', "password_db" : 'postgres', "server_db" : 'localhost', "port_number" : '5432', "schema" : 'donneelidar'}
    treethresholds = {"seuil_surface" : 30, "seuil_compacite_1" : 0.7, "seuil_compacite_2" : 0.5, "seuil_convexite" : 0.7, "seuil_elongation" : 2.5, "val_largeur_max_alignement" : 7, "val_buffer" : 1}
    detectInTreeStratum(connexion, 'sgts_veg4',  r'/mnt/RAM_disk/output_vectortree.gpkg', connexion_fv_dic = connexion_fv_dic, thresholds = treethresholds, save_results_as_layer = True, save_results_intermediate = True)
    shrubthresholds = {"seuil_surface" : 5, "seuil_compacite_1" : 0.7, "seuil_compacite_2" : 0.5, "seuil_convexite" : 0.7, "seuil_elongation" : 2.5, "val_largeur_max_alignement" : 5, "val_buffer" : 1}
    detectInShrubStratum(connexion, 'sgts_veg4',  r'/mnt/RAM_disk/output_vectorshrub.gpkg', connexion_fv_dic = connexion_fv_dic, thresholds = shrubthresholds, save_results_as_layer = True, save_results_intermediate = True)
