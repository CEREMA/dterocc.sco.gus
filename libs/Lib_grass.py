#Import des librairies Python
import grass.script as grass
import grass.script.setup as gsetup
import sys,os,shutil,glob, time, subprocess

#Import des librairies de /libs
from libs.Lib_display import bold,red,green,blue,cyan,endC
from libs.Lib_file import deleteDir
from libs.Lib_raster import getPixelSizeImage, getProjectionImage, getEmpriseImage, getPixelWidthXYImage

# debug = 0 : affichage minimum de commentaires lors de l'exécution du script
# debug = 3 : affichage maximum de commentaires lors de l'exécution du script. Intermédiaire : affichage intermédiaire

# debug = 3

# ATTENTION : pour appeler GRASS, il faut avoir mis à jour le fichier .profile (/home/scgsi/.profile). Ajouter à la fin du fichier (attention au numéro de version de GRASS qui peut changer, ici 7.2) :
'''
# Paramétrages GRASS :
export GISBASE="/usr/lib/grass72"
export PATH="$PATH:$GISBASE/bin:$GISBASE/scripts"
export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:$GISBASE/lib"
export GIS_LOCK=$$
export GISRC="$HOME/.grass7"
export PYTHONPATH="$PYTHONPATH:$GISBASE/etc/python"
'''

#########################################################################
# FONCTION connectionGrass()                                            #
#########################################################################
def connectionGrass(gisbase, gisdb, location="", mapset="PERMANENT", projection=2154) :
    """
    Rôle : Permet l'initialisation si la base GRASS avant création ou la connexion à une base GRASS déjà créer
   
    Paramètres :
       gisbase : variable d'environnement de GRASS. Par défaut, os.environ['GISBASE'].
       gisdb : nom de la géodatabase, 1er niveau. Par défaut, "GRASS_database".
       location : nom du secteur de la géodatabase, 2ème niveau. Par défaut, "".
       mapset : nom du jeu de cartes de la géodatabase, 3ème niveau. Par défaut, "PERMANENT".
       projection : code EPSG (entier), de l'espace de travail. Par défaut, 2154.
    """
    if location == "" :
        gsetup.init(gisbase, gisdb)
    else :
        if not os.path.exists(gisdb + os.sep + location):
            grass.core.create_location(gisdb, location, projection)
        gsetup.init(gisbase, gisdb, location, mapset)
    return

#########################################################################
# FONCTION initializeGrass()                                            #
#########################################################################
def initializeGrass(work_dir, xmin, xmax, ymin, ymax, pixel_size_x, pixel_size_y, projection=2154, gisbase=os.environ['GISBASE'], gisdb="GRASS_database", location="LOCATION", mapset="MAPSET", clean_old=True, overwrite=True):
    """
    #   Rôle : Permet la initialisation d'une base GRASS, pour l'appel de fonctions Grass
    #   Paramètres :
    #       work_dir : dossier de traitement, où seront stockées les données de la géodatabase (généralement, un dossier temporaire)
    #       xmin : valeur de l'emprise minimale en X, de l'espace de travail
    #       xmax : valeur de l'emprise maximale en X, de l'espace de travail
    #       ymin : valeur de l'emprise minimale en Y, de l'espace de travail
    #       ymax : valeur de l'emprise maximale en Y, de l'espace de travail
    #       pixel_size_x : résolution spatiale en X (largeur), de l'espace de travail
    #       pixel_size_y : résolution spatiale en Y (hauteur), de l'espace de travail
    #       projection : code EPSG (entier), de l'espace de travail. Par défaut, 2154.
    #       gisbase : variable d'environnement de GRASS. Par défaut, os.environ['GISBASE'].
    #       gisdb : nom de la géodatabase, 1er niveau. Par défaut, "GRASS_database".
    #       location : nom du secteur de la géodatabase, 2ème niveau. Par défaut, "LOCATION".
    #       mapset : nom du jeu de cartes de la géodatabase, 3ème niveau. Par défaut, "MAPSET".
    #       clean_old : nettoyage de la géodatabase si elle existe déjà. Par défaut, True.
    #       overwrite : (option) supprime ou non les fichiers existants ayant le meme nom.
    """

    # On récupère le nom du dossier de traitement, dans lequel on rajoute un sous-dossier (1er niveau de la géodatabase)
    gisdb = work_dir + os.sep + gisdb

    if debug >= 2:
        print(cyan + "initializeGrass() : " + bold + green + "Preparation de la geodatabase GRASS dans le dossier : " + endC + work_dir)

    # Nettoyage des données GRASS venant d'un traitement précédent : attention, on repart à 0 !
    if os.path.exists(gisdb) and clean_old:
        deleteDir(gisdb)

    # Création du 1er niveau de la géodatabase : 'gisdb'
    if not os.path.exists(gisdb):
        os.makedirs(gisdb)

    # Initialisation de la connexion à la géodatabase encore vide (pour récupérer les scripts GRASS et créer le 2ème niveau)
    connectionGrass(gisbase, gisdb)

    # Création du 2ème niveau de la géodatabase : 'location', avec un système de coordonnées spécifique
    # Initialisation de la connexion à la géodatabase par défaut (pour créer notre propre 'mapset')
    connectionGrass(gisbase, gisdb, location, 'PERMANENT', projection)

    # Création du 3ème niveau de la géodatabase : 'mapset', avec une emprise et une résolution spatiale spécifiques
    if not os.path.exists(gisdb + os.sep + location + os.sep + mapset):
        os.makedirs(gisdb + os.sep + location + os.sep + mapset)
    grass.run_command('g.region', n=ymax, s=ymin, e=xmax, w=xmin, ewres=abs(pixel_size_x), nsres=abs(pixel_size_y), overwrite=overwrite)

    # Copie des fichiers de paramètres du 'mapset' "PERMANENT" vers le nouveau 'mapset' (pour garder un original, et si on veut travailler dans plusieurs 'mapset')
    for file_to_copy in glob.glob(gisdb + os.sep + location + os.sep + "PERMANENT" + os.sep + "*"):
        shutil.copy(file_to_copy, gisdb + os.sep + location + os.sep + mapset)

    # Initialisation du 'mapset' de travail
    connectionGrass(gisbase, gisdb, location, mapset, projection)

    if debug >= 2:
        print(cyan + "initializeGrass() : " + bold + green + "Geodatabase GRASS prete." + endC)

    # Renvoie les informations de connexion (propres)
    return gisbase, gisdb, location, mapset

#########################################################################
# FONCTION cleanGrass()                                                 #
#########################################################################
def cleanGrass(work_dir, gisdb="GRASS_database", save_results_intermediate=False):
    """
    #   Rôle : Nettoyage de la géodatabase GRASS
    #   Paramètres :
    #       work_dir : dossier de traitement, où seront stockées les données de la géodatabase (généralement, un dossier temporaire)
    #       gisdb : nom de la géodatabase, 1er niveau. Par défaut, "GRASS_database".
    #       save_results_intermediate : (option) fichiers de sorties intermediaires non nettoyées, par defaut = False
    """

    if not save_results_intermediate :
        shutil.rmtree(os.path.join(work_dir, gisdb))
    return

#########################################################################
# FONCTION importVectorOgr2Grass()                                      #
#########################################################################
def importVectorOgr2Grass(input_vector, output_name, overwrite=True):
    """
    #   Rôle : import de données vecteurs (de la librairie OGR) vers la géodatabase GRASS
    #   Paramètres :
    #       input_vector : fichier vecteur à importer
    #       output_name : nom du fichier dans la géodatabase
    #       overwrite : (option) supprime ou non les fichiers existants ayant le meme nom.
    """

    if debug >= 2:
        print(cyan + "importVectorOgr2Grass() : " + bold + green + "Import vecteur GRASS : " + endC + input_vector + " vers " + output_name)
    grass.run_command('v.in.ogr', input=input_vector, output=output_name, overwrite=overwrite, stderr=subprocess.PIPE)

    return

#########################################################################
# FONCTION exportVectorOgr2Grass()                                      #
#########################################################################
def exportVectorOgr2Grass(input_name, output_vector, format_vector="ESRI_Shapefile", overwrite=True):
    """
    #   Rôle : export de données vecteurs (de la librairie OGR) depuis la géodatabase GRASS
    #   Paramètres :
    #       input_name : nom du fichier dans la géodatabase à exporter
    #       output_vector : fichier vecteur en sortie
    #       format_vector : format du vecteur de sortie (par défaut, 'ESRI_Shapefile')
    #       overwrite : (option) supprime ou non les fichiers existants ayant le meme nom.
    """

    if debug >= 2:
        print(cyan + "exportVectorOgr2Grass() : " + bold + green + "Export vecteur GRASS : " + endC + input_name + " vers " + output_vector)

    format_vector = format_vector.replace(' ', '_')

    grass.run_command('v.out.ogr', input=input_name, output=output_vector, format=format_vector, overwrite=overwrite, stderr=subprocess.PIPE)

    return

#########################################################################
# FONCTION importRasterGdal2Grass()                                     #
#########################################################################
def importRasterGdal2Grass(input_raster, output_name, overwrite=True):
    """
    #   Rôle : import de données rasters (de la librairie GDAL) vers la géodatabase GRASS
    #   Paramètres :
    #       input_raster : fichier raster à importer
    #       output_name : nom du fichier dans la géodatabase
    #       overwrite : (option) supprime ou non les fichiers existants ayant le meme nom.
    """

    if debug >= 2:
        print(cyan + "importRasterGdal2Grass() : " + bold + green + "Import raster GRASS : " + endC + input_raster + " vers " + output_name)
    grass.run_command('r.in.gdal', input=input_raster, output=output_name, overwrite=overwrite, stderr=subprocess.PIPE)

    return

#########################################################################
# FONCTION exportRasterGdal2Grass()                                     #
#########################################################################
def exportRasterGdal2Grass(input_name, output_raster, format_raster="GTiff", overwrite=True):
    """
    #   Rôle : export de données rasters (de la librairie GDAL) depuis la géodatabase GRASS
    #   Paramètres :
    #       input_name : nom du fichier dans la géodatabase à exporter
    #       output_raster : fichier raster en sortie
    #       format_raster : format du raster en sortie (par défaut, 'GTiff')
    #       overwrite : (option) supprime ou non les fichiers existants ayant le meme nom.
    """

    if debug >= 2:
        print(cyan + "exportRasterGdal2Grass() : " + bold + green + "Export raster GRASS : " + endC + input_name + " vers " + output_raster)
    grass.run_command('r.out.gdal', input=input_name, output=output_raster, format=format_raster, overwrite=overwrite, stderr=subprocess.PIPE, type='UInt16', nodata=5666)

    return

#########################################################################
# FONCTION vectorisationGrass()                                         #
#########################################################################
def vectorisationGrass(raster_input, vector_output, mmu, douglas=None, hermite=None, angle=True, format_vector='ESRI_Shapefile', overwrite=True):
    """
    #   Rôle : Permet la vectorisation d'un fichicher raster avec GRASS
    #   Paramètres :
    #       raster_input : fichier raster à vectoriser
    #       vector_output : fichier vecteur en sortie
    #       mmu : Mininal Mapping Unit (shapefile area unit) (integer)
    #       douglas : option Douglas-Peucker reduction value (integer)
    #       hermite : option Hermite smoothing level (integer)
    #       angle : Smooth corners of pixels (45°) (boolean) (par défaut, True)
    #       format_vector : format du vecteur de sortie (par défaut, 'ESRI_Shapefile')
    #       overwrite : (option) supprime ou non les fichiers existants ayant le meme nom.
    #
    # ATTENTION! (A confirmer!) ne marche que pour des rasters dont le nombre de lignes et de colonnes est limités (max ligne max colonnes à définir)
    #
    """

    format_vector = format_vector.replace(' ', '_')

    # Import du rasteur d'entrée
    leng_name_raster = len(os.path.splitext(os.path.basename(raster_input))[0])
    if leng_name_raster > 16 :
        leng_name_raster = 16
    name_raster_geobase = "R" + os.path.splitext(os.path.basename(raster_input))[0][0:leng_name_raster]
    leng_name_vector = len(os.path.splitext(os.path.basename(vector_output))[0])
    if leng_name_vector > 16 :
        leng_name_vector = 16
    name_vector_geobase = "V" + os.path.splitext(os.path.basename(vector_output))[0][0:leng_name_vector]

    timeinit = time.time()

    # Import raster dans Grass
    importRasterGdal2Grass(raster_input, name_raster_geobase, overwrite)
    timeimport = time.time()
    if debug >= 2:
        print(cyan + "vectorisationGrass() : " + bold + green + "Importation raster : " + str(timeimport - timeinit) + " seconds" + endC)

    if angle:
        # Vectorization with corners of pixel smoothing
        grass.run_command("r.to.vect", flags = "sv", input=name_raster_geobase, output=name_vector_geobase, type="area", overwrite=overwrite, stderr=subprocess.PIPE)
    else:
        # Vectorization without corners of pixel smoothing
        grass.run_command("r.to.vect", flags = "v",input =name_raster_geobase, output=name_vector_geobase, type="area", overwrite=overwrite, stderr=subprocess.PIPE)
    timevect = time.time()
    if debug >= 2:
        print(cyan + "vectorisationGrass() : " + bold + green + "Vectorization : " + str(timevect - timeimport) + " seconds" + endC)

    inputvector = name_vector_geobase
    # Douglas simplification
    if douglas is not None and not douglas == 0:
        grass.run_command("v.generalize", input = "%s"%(name_vector_geobase), method="douglas", threshold="%s"%(douglas), output=name_vector_geobase+"_Douglas", overwrite=overwrite, stderr=subprocess.PIPE)
        inputvector = name_vector_geobase + "_Douglas"
        timedouglas = time.time()
        if debug >= 2:
            print(cyan + "vectorisationGrass() : " + bold + green + "Douglas simplification : " + str(timedouglas - timevect) + " seconds" + endC)
        timevect = timedouglas

    # Hermine simplification
    if hermite is not None and not hermite == 0:
        grass.run_command("v.generalize", input = "%s"%(inputvector), method="hermite", threshold="%s"%(hermite), output=name_vector_geobase+"_Hermine", overwrite=overwrite, stderr=subprocess.PIPE)
        inputvector = name_vector_geobase + "_Hermine"

        timehermine = time.time()
        if debug >= 2:
            print(cyan + "vectorisationGrass() : " + bold + green + "Hermine smoothing : " + str(timehermine - timevect) + " seconds" + endC)
        timevect = timehermine

    # Delete non class polygons (sea water, nodata and crown entities)
    grass.run_command("v.edit", map="%s"%(inputvector), tool="delete", where="cat < 1", stderr=subprocess.PIPE)

    # Delete under MMU limit
    grass.run_command("v.clean", input="%s"%(inputvector), output=name_vector_geobase+"_Cleanarea", tool="rmarea", thres=mmu, type="area", stderr=subprocess.PIPE)

    # Export vector file
    exportVectorOgr2Grass(name_vector_geobase+"_Cleanarea", vector_output, format_vector, overwrite)

    timeexp = time.time()
    if debug >= 2:
        print(cyan + "vectorisationGrass() : " + bold + green + "Exportation vector : " + str(timeexp - timevect) + "seconds" + endC)

    timeend = time.time()
    if debug >= 2:
        print(cyan + "vectorisationGrass() : " + bold + green + "Global Vectorization and Simplification process : " + str(timeend - timeinit) + " seconds" + endC)

    return


#########################################################################
# FONCTION convertRGBtoHIS()                                            #
#########################################################################
def convertRGBtoHIS(image_input, image_output, raster_red_input, raster_green_input, raster_blue_input):
    """
    #   Rôle : convertit une image RGB en HIS avec GRASS
    #   Paramètres :
    #       raster_red_input : fichier raster de la bande rouge
    #       raster_green_input : fichier raster de la bande verte
    #       raster_blue_input : fichier raster de la bande bleue
    #
    #   Sortie :
    #       raster_hue_output : image de la teinte
    #       raster_intensity_output : image de l'intensite
    #       raster_saturation_output : image de la saturation
    #
    """

    timeinit = time.time()
    # RECUPERATIONS DE DONNEES UTILES
    repository = os.path.dirname(raster_red_input)+"/"
    area_pixel =  getPixelSizeImage(raster_red_input)                   # Superficie, en m d'un pixel de l'image. Exemple pour une image à 5m : area_pixel = 25
    pixel_size_x, pixel_size_y = getPixelWidthXYImage(raster_red_input) # taille d'un pixel
    epsg, _ = getProjectionImage(raster_red_input)                      # Recuperation de la valeur de la projection du rasteur d'entrée
    xmin, xmax, ymin, ymax = getEmpriseImage(raster_red_input)          # Recuperation de l'emprise du rasteur d'entrée

    # PARAMETRAGE DES IMAGES TEINTE, SATURATION, INTENSITE
    filename = os.path.splitext(os.path.basename(image_output))[0]
    raster_hue_output = repository + filename + "_H.tif"
    raster_intensity_output = repository + filename + "_I.tif"
    raster_saturation_output = repository + filename + "_S.tif"


    name_raster_hue = filename + "_H"
    name_raster_intensity = filename + "_I"
    name_raster_saturation = filename + "_S"

    # INITIALISATION DE LA CONNEXION A L'ENVIRONNEMENT GRASS
    initializeGrass(repository, xmin, xmax, ymin, ymax, pixel_size_x, pixel_size_y, projection=epsg)

    # PARAMETRAGE DES IMAGES ROUGE VERT ET BLEUE
    # Noms des rasters
    name_raster_red = os.path.splitext(os.path.basename(raster_red_input))[0]
    name_raster_green = os.path.splitext(os.path.basename(raster_green_input))[0]
    name_raster_blue = os.path.splitext(os.path.basename(raster_blue_input))[0]

    # Import des raster
    # Import de l'image Rouge
    importRasterGdal2Grass(raster_red_input, name_raster_red)
    timeexp = time.time()
    if debug >= 20:
        print(cyan + "convertRGBtoHIS() : " + bold + green + "Import raster rouge dans Grass : " + str(timeexp - timevect) + "seconds" + endC)

    # Import de l'image Vert
    importRasterGdal2Grass(raster_green_input, name_raster_green)
    timeexp = time.time()
    if debug >= 20:
        print(cyan + "convertRGBtoHIS() : " + bold + green + "Import raster vert dans Grass : " + str(timeexp - timevect) + "seconds" + endC)

    # Import del'image Bleu
    importRasterGdal2Grass(raster_blue_input, name_raster_blue)
    timeexp = time.time()
    if debug >= 202:
        print(cyan + "convertRGBtoHIS() : " + bold + green + "Import raster bleu dans Grass : " + str(timeexp - timevect) + "seconds" + endC)
    # LANCEMENT DE LA CONVERSION
    grass.run_command('i.rgb.his', red = name_raster_red, green = name_raster_green, blue = name_raster_blue, hue = name_raster_hue, intensity = name_raster_intensity, saturation = name_raster_saturation)

    timeexp = time.time()
    if debug >= 202:
        print(cyan + "convertRGBtoHIS() : " + bold + green + "Conversion de RVB vers HIS terminée " + str(timeexp - timevect) + "seconds" + endC)
    # EXPORT DES IMAGES
    exportRasterGdal2Grass(name_raster_hue, raster_hue_output)

    timeexp = time.time()
    if debug >= 202:
        print(cyan + "convertRGBtoHIS() : " + bold + green + "Export raster teinte terminé " + str(timeexp - timevect) + "seconds" + endC)

    exportRasterGdal2Grass(name_raster_intensity , raster_intensity_output)

    timeexp = time.time()
    if debug >= 202:
        print(cyan + "convertRGBtoHIS() : " + bold + green + "Export raster intensite terminé " + str(timeexp - timevect) + "seconds" + endC)

    exportRasterGdal2Grass(name_raster_saturation , raster_saturation_output)

    timeexp = time.time()
    if debug >= 202:
        print(cyan + "convertRGBtoHIS() : " + bold + green + "Export raster saturation terminé " + str(timeexp - timevect) + "seconds" + endC)

    # SUPPRESSION DES FICHIERS NON UTILES
    os.remove(raster_red_input)
    os.remove(raster_green_input)
    os.remove(raster_blue_input)
    cleanGrass(repository)

    return raster_hue_output, raster_intensity_output, raster_saturation_output

#########################################################################
# FONCTION rasterStatsV()                                               #
#########################################################################
def rasterStatsV(image_input, vector_input, stats_list, repository):
    """
    #   Rôle : calcul les statistiques d'une couche raster sur une emprise vectorielle
    #   Paramètres :
    #       image_input : fichier raster de calcul des statistiques
    #       vector_input : fichier vecteur sur lequel on calcul les statistiques de l'image_input
    #       vector_output : fichier vecteur contenant les polygones avec les statistiques calculées en attributs
    #       stats_list : liste des statistiques à calcule. Par défaut : 
    #       repository : répertoire de stockage des données intermédiaires. Par défaut : '' 
    #
    #   Sortie :
    #       vector_output : chemin du fichier vecteur contenant les polygones avec les statistiques calculées en attributs
    #
    """

    timeinit = time.time()

    # RECUPERATIONS DE DONNEES UTILES
    if repository == '':
        repository = os.path.dirname(vector_input)
    area_pixel =  getPixelSizeImage(image_input)                   # Superficie, en m d'un pixel de l'image. Exemple pour une image à 5m : area_pixel = 25
    pixel_size_x, pixel_size_y = getPixelWidthXYImage(image_input) # taille d'un pixel
    epsg, _ = getProjectionImage(image_input)                      # Recuperation de la valeur de la projection du rasteur d'entrée
    xmin, xmax, ymin, ymax = getEmpriseImage(image_input)          # Recuperation de l'emprise du rasteur d'entrée

    # PARAMETRAGE DES IMAGES TEINTE, SATURATION, INTENSITE
    file_r, file_extension_r = os.path.splitext(image_input)
    file_v, file_extension_v = os.path.splitext(vector_input)
    filename_r =  os.path.splitext(os.path.basename(image_input))[0]
    filename_v =  os.path.splitext(os.path.basename(vector_input))[0]
    vector_output = repository + os.sep + "_STATS" + file_extension_v


    # INITIALISATION DE LA CONNEXION A L'ENVIRONNEMENT GRASS
    initializeGrass(repository, xmin, xmax, ymin, ymax, pixel_size_x, pixel_size_y, projection=epsg)

    # PARAMETRAGE
    name_raster = filename_r 
    name_vector = filename_v

    # Import des raster
    # Import de l'image raster
    importRasterGdal2Grass(image_input, name_raster)
    timeexp = time.time()
    if debug >= 20:
        print(cyan + "rasterStatsV() : " + bold + green + "Import raster dans Grass : " + str(timeexp - timevect) + "seconds" + endC)

    # Import de la couche vecteur
    importVectorOgr2Grass(vector_input, name_vector)
    timeexp = time.time()
    if debug >= 20:
        print(cyan + "rasterStatsV() : " + bold + green + "Import vecteur dans Grass : " + str(timeexp - timevect) + "seconds" + endC)

    # CREATION DE LA VARIABLE METHOD
    stats = stats_list[0]
    for i in range(1,len(stats_list)):
        stats += "," + stats_list[i]

    # LANCEMENT DE LA CONVERSION
    grass.run_command('r.rast.stats', map = name_vector, raster = name_raster, method = stats )


    # EXPORT DE LA DONNEE VECTEUR
    exportVectorOgr2Grass(name_vector, vector_output, format_vector="GPKG", overwrite=True)

    timeexp = time.time()
    if debug >= 202:
        print(cyan + "rasterStatsV() : " + bold + green + "Export donnée vecteur de statistiques" + str(timeexp - timevect) + "seconds" + endC)

    # SUPPRESSION DES FICHIERS NON UTILES
    cleanGrass(repository)

    return vector_output