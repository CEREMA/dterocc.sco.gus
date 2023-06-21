#from ImagesAssemblyGUS import assembleRasters
from MnhCreation import MnhCreation
from ImagesAssemblyGUS_ok import cutImageByVector
from NeochannelComputation_gus import neochannelComputation
#assembleRasters(r'/mnt/RAM_disk/TEST_IMAGEASSEMBLY/empriseTEST.gpkg', ['/mnt/RAM_disk/TEST_IMAGEASSEMBLY/Data'],r'/mnt/RAM_disk/TEST_IMAGEASSEMBLY/img_ass.tif')

MnhCreation(r'/mnt/RAM_disk/DSM_PRODUITS_RGE.tif', r'/mnt/RAM_disk/srtm_30m.tif', r'/mnt/RAM_disk/MNHtest.tif', r'/mnt/RAM_disk/MGN_contours.shp', r'/mnt/RAM_disk/ORT_20220614_NADIR_16B_MGN.tif',  epsg=2154, nivellement = True, format_raster = 'GTiff', format_vector = 'ESRI Shapefile',  rewrite = True, save_results_intermediate = True)



#la commande ci-dessous permet de couper l'image PANCHROMATIQUE avec l'emprise de la zone d'étude
#cutImageByVector(r'/mnt/Data/20_Etudes_Encours/ENVIRONNEMENT/2022_GreenUrbanSat/1-DATAS/0-EMPRISES_ETUDE/NANCY/MGN_contours.shp', r'/mnt/Donnees_Source/Pleiades/2022/NANCY/2022_06_14/bundle/ORT_P1AP--2022061439342579CP.tif', r'/mnt/RAM_disk/ORT_P1AP_MGN.tif', no_data_value=-999)


#r = neochannelComputation(r'/mnt/RAM_disk/ORT_20220614_NADIR_16B_MGN.tif', r'/mnt/RAM_disk/ORT_P1AP_MGN.tif', r'/mnt/RAM_disk/img_origine.tif')
#print(r)
