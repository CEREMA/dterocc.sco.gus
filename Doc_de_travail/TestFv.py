from DetectVegetationFormStratum import detectInTreeStratum
from Lib_postgis import *

connexion = openConnection('etape2', user_name='postgres', password='', ip_host='localhost', num_port='5432', schema_name='donneelidar')
cursor =  connexion.cursor()

detectInTreeStratum(connexion, 'sgts_veg4')
