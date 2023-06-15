#from ImagesAssemblyGUS import assembleRasters
from MnhCreation import MnhCreation
#assembleRasters(r'/mnt/RAM_disk/TEST_IMAGEASSEMBLY/empriseTEST.gpkg', ['/mnt/RAM_disk/TEST_IMAGEASSEMBLY/Data'],r'/mnt/RAM_disk/TEST_IMAGEASSEMBLY/img_ass.tif')

MnhCreation(r'/mnt/RAM_disk/DSM_PRODUITS_RGE.tif', r'/mnt/RAM_disk/MNT_RGEALTI_1M_ZONE_DE_NANCY.tif', r'/mnt/RAM_disk/MNHtest.tif', r'/mnt/RAM_disk/MGN_contours.shp', r'/mnt/RAM_disk/ORT_20220614_NADIR_16B_MGN.tif',  epsg=2154, nivellement = True, format_raster = 'GTiff', format_vector = 'ESRI Shapefile',  rewrite = True, save_results_intermediate = True)
