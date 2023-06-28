from MnhCreation import MnhCreation
from NeochannelComputation_gus import neochannelComputation
from DataConcatenation import concatenateData
from ImagesAssemblyGUS_ok import cutImageByVector

if __name__ == "__main__":

    #Préparation du parser
    #à faire par la suite


    #1# Assemblage des tuiles d'images Pléiades sur l'emprise de la zone d'étude
    #Soit elles sont déjà assemblées et on ne fait que découper avec la fonction suivante


    #cutImageByVector(r'/mnt/RAM_disk/MGN_contours.shp' ,r'/mnt/RAM_disk/ORT_20220614_NADIR_16B_MGN.tif', r'/mnt/RAM_disk/ORT_20220614_NADIR_16B_MGN_V2.tif')
    #Soit elles doivent êtres assemblées

    #images_input_list = [r'/mnt/RAM_disk/ORT_20220614_NADIR_16B_MGN_V2.tif', r'/mnt/RAM_disk/MNHtest.tif', r'/mnt/RAM_disk/img_origine_hue.tif', r'/mnt/RAM_disk/img_origine_msavi2.tif', r'/mnt/RAM_disk/img_origine_ndvi.tif', r'/mnt/RAM_disk/img_origine_ndwi2.tif', r'/mnt/RAM_disk/img_origine_tmp_txtSFS_u.tif']
    images_input_list = [r'/mnt/RAM_disk/ORT_20220614_NADIR_16B_MGN_V2.tif', r'/mnt/RAM_disk/MNHtest.tif']
    #2# Calcul du MNH
    #mnh = MnhCreation(r'/mnt/RAM_disk/DSM_PRODUITS_RGE.tif', r'/mnt/Data/20_Etudes_Encours/ENVIRONNEMENT/2022_GreenUrbanSat/1-DATAS/1-DONNEES_ELEVATION/MNT/2021/NANCY/MNT_RGEALTI/MNT_RGEALTI_1M_ZONE_DE_NANCY.tif', r'/mnt/RAM_disk/MNHtest.tif', r'/mnt/RAM_disk/MGN_contours.shp', r'/mnt/RAM_disk/ORT_20220614_NADIR_16B_MGN.tif',  epsg=2154, nivellement = True, format_raster = 'GTiff', format_vector = 'ESRI Shapefile',  rewrite = True, save_results_intermediate = True)


    #3# Calcul des néocanaux
    neochannels = neochannelComputation(r'/mnt/RAM_disk/ORT_20220614_NADIR_16B_MGN_V2.tif', r'/mnt/RAM_disk/ORT_P1AP_MGN.tif', r'/mnt/RAM_disk/img_origine.tif', r'/mnt/RAM_disk/MGN_contours.shp')

    for el in neochannels:
        images_input_list.append(el)
    # Phase de test si les emprises correspondent bien

    #4# Concatnéation des néocanaux
    concatenateData(images_input_list, r'/mnt/RAM_disk/final.tif')

    #5# Création des échantillons d'apprentissage
    #Fournir 5 couches vectorielles
    bati = ''
    route = ''
    solnu = ''
    eau = ''
    vegetation = ''

    #6# Nettoyage des échantillons d'apprentissage : érosion + filtrage avec les néocanaux

