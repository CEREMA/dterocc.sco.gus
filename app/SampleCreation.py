#Import des librairies Python
import os,sys,glob,shutil

#Import des librairies /libs
from libs.Lib_display import bold,red,green,yellow,cyan,endC
from libs.Lib_file import cleanTempData, deleteDir, removeFile, removeVectorFile, copyVectorFile
from libs.Lib_raster import createBinaryMaskThreshold, applyMaskAnd, rasterizeBinaryVector
from libs.Lib_vector import simplifyVector, cutoutVectors, bufferVector, fusionVectors, filterSelectDataVector, getAttributeNameList, getNumberFeature, getGeometryType


# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 3

###########################################################################################################################################
# FONCTION createAllSamples()                                                                                                             #
###########################################################################################################################################
def createAllSamples(image_input, vector_to_cut_input, vectors_samples_output, rasters_samples_output, params_to_find_samples, simplify_vector_param=10.0, format_vector='ESRI Shapefile', extension_vector=".shp", save_results_intermediate=False, overwrite=True):
    """
    Rôle : crééer tous les échantillons d'apprentissage à partir de BD exogènes

    Paramètres :
        image_input : image d'entrée brute
        vector_to_cut_input : vecteur de découpage (zone d'étude)
        vectors_samples_output : dictionnaire contenant, par classe, le chemin de sauvegarde du fichier de sortie au format vecteur
        rasters_samples_output : dictionnaire contenant, par classe, le chemin de sauvegarde du fichier de sortie au format raster (optionnel)
        params_to_find_samples : dictionnaire contenant, par classe, les paramètres de recherche des échantillons d'apprentissage au format {"nom_classe":[['chemin premier base', buffer, requêtesql],['chemin deuxieme base]] } . 
                                Ex :{"bâti":[['/mnt/RAM_disk/BDTOPO/BATIMENT.shp', 2, 'select *']] } 
        simplify_vector_param : parmetre de simplification des polygones
        format_vector : format du fichier vecteur. Optionnel, par default : 'ESRI Shapefile'
        extension_vector : extension du fichier vecteur de sortie, par defaut = '.shp'
        save_results_intermediate : fichiers de sorties intermediaires nettoyees, par defaut = False
        overwrite : boolen ecrasement ou non des fichiers ayant un nom similaire, par defaut à True      
    """
    for key in vectors_samples_output.keys():
        bd_vector_list = [params_to_find_samples[key][i][0] for i in range(len(params_to_find_samples[key]))]  
        bd_buff_list = [params_to_find_samples[key][i][1] for i in range(len(params_to_find_samples[key]))]    
        sql_expression_list = [params_to_find_samples[key][i][2] for i in range(len(params_to_find_samples[key]))]   
        createSamples(image_input, vector_to_cut_input, vectors_samples_output[key], rasters_samples_output[key], bd_vector_list, bd_buff_list, sql_expression_list, key,simplify_vector_param, format_vector, extension_vector, save_results_intermediate, overwrite)

    return 

###########################################################################################################################################
# FONCTION createSamples()                                                                                                                #
###########################################################################################################################################
def createSamples(image_input, vector_to_cut_input, vector_sample_output, raster_sample_output, bd_vector_input_list, bd_buff_list, sql_expression_list, sample_name="", simplify_vector_param=10.0, format_vector='ESRI Shapefile', extension_vector=".shp", save_results_intermediate=False, overwrite=True) :
    """
    Rôle : créé une couche d'échantillons d'apprentissage à partir de une ou plusieurs BD exogènes
        
    
    Paramètres :
        image_input : image d'entrée brute
        vector_to_cut_input : le vecteur pour le découpage (zone d'étude)
        vector_sample_output : fichier vecteur au format shape de sortie contenant l'echantillon
        raster_sample_output : optionel fichier raster au format GTiff de sortie contenant l'echantillon
        bd_vector_input_list : liste des vecteurs de la bd exogene pour créer l'échantillon
        bd_buff_list : liste des valeurs des buffers associés au traitement à appliquer aux vecteurs de bd exogenes
        sql_expression_list : liste d'expression sql pour le filtrage des fichiers vecteur de bd exogenes
        sample_name : nom de l'echantillon 
        simplify_vector_param : parmetre de simplification des polygones
        format_vector : format du fichier vecteur. Optionnel, par default : 'ESRI Shapefile'
        extension_vector : extension du fichier vecteur de sortie, par defaut = '.shp'
        save_results_intermediate : fichiers de sorties intermediaires nettoyees, par defaut = False
        overwrite : boolen ecrasement ou non des fichiers ayant un nom similaire, par defaut à True
    """

    starting_event = "createSamples() : create samples starting : "

    if debug >= 3:
        print(bold + green + "createSamples() : Variables dans la fonction" + endC)
        print(cyan + "createSamples() : " + endC + "image_input : " + str(image_input) + endC)
        print(cyan + "createSamples() : " + endC + "vector_to_cut_input : " + str(vector_to_cut_input) + endC)
        print(cyan + "createSamples() : " + endC + "vector_sample_output : " + str(vector_sample_output) + endC)
        print(cyan + "createSamples() : " + endC + "raster_sample_output : " + str(raster_sample_output) + endC)
        print(cyan + "createSamples() : " + endC + "bd_vector_input_list : " + str(bd_vector_input_list) + endC)
        print(cyan + "createSamples() : " + endC + "bd_buff_list : " + str(bd_buff_list) + endC)
        print(cyan + "createSamples() : " + endC + "sql_expression_list : " + str(sql_expression_list) + endC)
        print(cyan + "createSamples() : " + endC + "sample_name : " + str(sample_name) + endC)
        print(cyan + "createSamples() : " + endC + "simplify_vector_param : " + str(simplify_vector_param) + endC)
        print(cyan + "createSamples() : " + endC + "format_vector : " + str(format_vector))
        print(cyan + "createSamples() : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "createSamples() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "createSamples() : " + endC + "overwrite : " + str(overwrite) + endC)

    # Constantes
    FOLDER_MASK_TEMP = "Mask_"
    FOLDER_CUTTING_TEMP = "Cut_"
    FOLDER_FILTERING_TEMP = "Filter_"
    FOLDER_BUFF_TEMP = "Buff_"

    SUFFIX_MASK_CRUDE = "_crude"
    SUFFIX_MASK = "_mask"
    SUFFIX_VECTOR_CUT = "_cut"
    SUFFIX_VECTOR_FILTER = "_filt"
    SUFFIX_VECTOR_BUFF = "_buff"

    CODAGE = "uint8"

    # ETAPE 1 : NETTOYER LES DONNEES EXISTANTES

    print(cyan + "createSamples() : " + bold + green + "Nettoyage de l'espace de travail..." + endC)

    print(raster_sample_output)

    # Nom du repertoire de calcul
    repertory_samples_output = os.path.dirname(vector_sample_output)

    # Test si le vecteur echantillon existe déjà et si il doit être écrasés
    check = os.path.isfile(vector_sample_output) or os.path.isfile(raster_sample_output)

    if check and not overwrite: # Si les fichiers echantillons existent deja et que overwrite n'est pas activé
        print(bold + yellow + "File sample : " + vector_sample_output + " already exists and will not be created again." + endC)
    else :
        if check:
            try:
                removeVectorFile(vector_sample_output)
                removeFile(raster_sample_output)
            except Exception:
                pass # si le fichier n'existe pas, il ne peut pas être supprimé : cette étape est ignorée

        # Définition des répertoires temporaires
        repertory_mask_temp = repertory_samples_output + os.sep + FOLDER_MASK_TEMP + sample_name
        repertory_samples_cutting_temp = repertory_samples_output + os.sep + FOLDER_CUTTING_TEMP + sample_name
        repertory_samples_filtering_temp = repertory_samples_output + os.sep + FOLDER_FILTERING_TEMP + sample_name
        repertory_samples_buff_temp = repertory_samples_output + os.sep + FOLDER_BUFF_TEMP + sample_name

        if debug >= 4:
            print(cyan + "createSamples() : " + endC + "Création du répertoire : " + str(repertory_mask_temp))
            print(cyan + "createSamples() : " + endC + "Création du répertoire : " + str(repertory_samples_cutting_temp))
            print(cyan + "createSamples() : " + endC + "Création du répertoire : " + str(repertory_samples_buff_temp))

        # Création des répertoires temporaire qui n'existent pas
        if not os.path.isdir(repertory_samples_output):
            os.makedirs(repertory_samples_output)
        if not os.path.isdir(repertory_mask_temp):
            os.makedirs(repertory_mask_temp)
        if not os.path.isdir(repertory_samples_cutting_temp):
            os.makedirs(repertory_samples_cutting_temp)
        if not os.path.isdir(repertory_samples_filtering_temp):
            os.makedirs(repertory_samples_filtering_temp)
        if not os.path.isdir(repertory_samples_buff_temp):
            os.makedirs(repertory_samples_buff_temp)

        # Nettoyage des répertoires temporaire qui ne sont pas vide
        cleanTempData(repertory_mask_temp)
        cleanTempData(repertory_samples_cutting_temp)
        cleanTempData(repertory_samples_filtering_temp)
        cleanTempData(repertory_samples_buff_temp)

        print(cyan + "createSamples() : " + bold + green + "... fin du nettoyage" + endC)

        # ETAPE 2 : DECOUPAGE DES VECTEURS

        print(cyan + "createSamples() : " + bold + green + "Decoupage des echantillons ..." + endC)

        if vector_to_cut_input == None :
            # 2.1 : Création du masque délimitant l'emprise de la zone par image
            image_name = os.path.splitext(os.path.basename(image_input))[0]
            vector_mask = repertory_mask_temp + os.sep + image_name + SUFFIX_MASK_CRUDE + extension_vector
            cols, rows, num_band = getGeometryImage(image_input)
            no_data_value = getNodataValueImage(image_input, num_band)
            if no_data_value == None :
                no_data_value = 0
            createVectorMask(image_input, vector_mask, no_data_value, format_vector)

            # 2.2 : Simplification du masque
            vector_simple_mask = repertory_mask_temp + os.sep + image_name + SUFFIX_MASK + extension_vector
            simplifyVector(vector_mask, vector_simple_mask, simplify_vector_param, format_vector)
        else :
            vector_simple_mask = vector_to_cut_input

        # 2.3 : Découpage des vecteurs de bd exogenes avec le masque
        vectors_cut_list = []
        for vector_input in bd_vector_input_list :
            vector_name = os.path.splitext(os.path.basename(vector_input))[0]
            vector_cut = repertory_samples_cutting_temp + os.sep + vector_name + SUFFIX_VECTOR_CUT + extension_vector
            vectors_cut_list.append(vector_cut)
        cutoutVectors(vector_simple_mask, bd_vector_input_list, vectors_cut_list, format_vector)

        print(cyan + "createSamples() : " + bold + green + "... fin du decoupage" + endC)

        # ETAPE 3 : FILTRAGE DES VECTEURS

        print(cyan + "createSamples() : " + bold + green + "Filtrage des echantillons ..." + endC)

        vectors_filtered_list = []
        if sql_expression_list != [] :
            for idx_vector in range (len(bd_vector_input_list)):
                vector_name = os.path.splitext(os.path.basename(bd_vector_input_list[idx_vector]))[0]
                vector_cut = vectors_cut_list[idx_vector]
                if idx_vector < len(sql_expression_list) :
                    sql_expression = sql_expression_list[idx_vector]
                    
                else :
                    sql_expression = ""
                vector_filtered = repertory_samples_filtering_temp + os.sep + vector_name + SUFFIX_VECTOR_FILTER + extension_vector
                vectors_filtered_list.append(vector_filtered)

                # Filtrage par ogr2ogr
                print(sql_expression)
                if sql_expression != "" or sql_expression != '':
                    names_attribut_list = getAttributeNameList(vector_cut, format_vector)
                    column = "'"
                    for name_attribut in names_attribut_list :
                        column += name_attribut + ", "
                    column = column[0:len(column)-2]
                    column += "'"
                    ret = filterSelectDataVector(vector_cut, vector_filtered, column, sql_expression, format_vector)
                    if not ret :
                        print(cyan + "createSamples() : " + bold + yellow + "Attention problème lors du filtrage des BD vecteurs l'expression SQL %s est incorrecte" %(sql_expression) + endC)
                        copyVectorFile(vector_cut, vector_filtered)
                else :
                    print(cyan + "createSamples() : " + bold + yellow + "Pas de filtrage sur le fichier du nom : " + endC + vector_filtered)
                    copyVectorFile(vector_cut, vector_filtered)

        else :
            print(cyan + "createSamples() : " + bold + yellow + "Pas de filtrage demandé" + endC)
            for idx_vector in range (len(bd_vector_input_list)):
                vector_cut = vectors_cut_list[idx_vector]
                vectors_filtered_list.append(vector_cut)

        print(cyan + "createSamples() : " + bold + green + "... fin du filtrage" + endC)

        # ETAPE 4 : BUFFERISATION DES VECTEURS

        print(cyan + "createSamples() : " + bold + green + "Mise en place des tampons..." + endC)

        vectors_buffered_list = []
        if bd_buff_list != [] :
            # Parcours des vecteurs d'entrée
            for idx_vector in range (len(bd_vector_input_list)):
                vector_name = os.path.splitext(os.path.basename(bd_vector_input_list[idx_vector]))[0]
                buffer_str = bd_buff_list[idx_vector]

                buff = 0.0
                col_name_buf = ""
                is_buff_str = False
                try:
                    buff = float(buffer_str)
                except :
                    is_buff_str = True
                    col_name_buf = buffer_str
                    print(cyan + "createSamples() : " + bold + green + "Pas de valeur buffer mais un nom de colonne pour les valeur à bufferiser : " + endC + col_name_buf)

                vector_filtered = vectors_filtered_list[idx_vector]
                vector_buffered = repertory_samples_buff_temp + os.sep + vector_name + SUFFIX_VECTOR_BUFF + extension_vector

                if is_buff_str or buff != 0:
                    if os.path.isfile(vector_filtered):
                        if debug >= 3:
                            print(cyan + "createSamples() : " + endC + "vector_filtered : " + str(vector_filtered) + endC)
                            print(cyan + "createSamples() : " + endC + "vector_buffered : " + str(vector_buffered) + endC)
                            print(cyan + "createSamples() : " + endC + "buff : " + str(buff) + endC)
                        bufferVector(vector_filtered, vector_buffered, buff, col_name_buf, 0.5, 10, format_vector)
                    else :
                        print(cyan + "createSamples() : " + bold + yellow + "Pas de fichier du nom : " + endC + vector_filtered)

                else :
                    print(cyan + "createSamples() : " + bold + yellow + "Pas de tampon sur le fichier du nom : " + endC + vector_filtered)
                    copyVectorFile(vector_filtered, vector_buffered)

                vectors_buffered_list.append(vector_buffered)

        else :
            print(cyan + "createSamples() : " + bold + yellow + "Pas de tampon demandé" + endC)
            for idx_vector in range (len(bd_vector_input_list)):
                vector_filtered = vectors_filtered_list[idx_vector]
                vectors_buffered_list.append(vector_filtered)

        print(cyan + "createSamples() : " + bold + green + "... fin de la mise en place des tampons" + endC)

        # ETAPE 5 : FUSION DES SHAPES

        print(cyan + "createSamples() : " + bold + green + "Fusion par classe ..." + endC)

        # si une liste de fichier shape à fusionner existe
        if not vectors_buffered_list:
            print(cyan + "createSamples() : " + bold + yellow + "Pas de fusion sans donnee à fusionner" + endC)
        # s'il n'y a qu'un fichier shape en entrée
        elif len(vectors_buffered_list) == 1:
            print(cyan + "createSamples() : " + bold + yellow + "Pas de fusion pour une seule donnee à fusionner" + endC)
            copyVectorFile(vectors_buffered_list[0], vector_sample_output)
        else :
            # Fusion des fichiers shape
            vectors_buffered_controled_list = []
            for vector_buffered in vectors_buffered_list :
                if os.path.isfile(vector_buffered) and (getGeometryType(vector_buffered, format_vector) in ('POLYGON', 'MULTIPOLYGON')) and (getNumberFeature(vector_buffered, format_vector) > 0):
                    vectors_buffered_controled_list.append(vector_buffered)
                else :
                    print(cyan + "createSamples() : " + bold + red + "Attention fichier bufferisé est vide il ne sera pas fusionné : " + endC + vector_buffered, file=sys.stderr)

            fusionVectors(vectors_buffered_controled_list, vector_sample_output, format_vector)

        print(cyan + "createSamples() : " + bold + green + "... fin de la fusion" + endC)

    # ETAPE 6 : CREATION DU FICHIER RASTER RESULTAT SI DEMANDE

    # Creation d'un masque binaire
    if raster_sample_output != "" and image_input != "" :
        repertory_output = os.path.dirname(raster_sample_output)
        if not os.path.isdir(repertory_output):
            os.makedirs(repertory_output)
        rasterizeBinaryVector(vector_sample_output, image_input, raster_sample_output, 1, CODAGE)

    # ETAPE 7 : SUPPRESIONS FICHIERS INTERMEDIAIRES INUTILES

    # Suppression des données intermédiaires
    if not save_results_intermediate:

        # Supression du fichier de decoupe si celui ci a été créer
        if vector_simple_mask != vector_to_cut_input :
            if os.path.isfile(vector_simple_mask) :
                removeVectorFile(vector_simple_mask)

        # Suppression des repertoires temporaires
        deleteDir(repertory_mask_temp)
        deleteDir(repertory_samples_cutting_temp)
        deleteDir(repertory_samples_filtering_temp)
        deleteDir(repertory_samples_buff_temp)

    # Mise à jour du Log
    ending_event = "createSamples() : create samples ending : "

    return


###########################################################################################################################################
# FONCTION prepareAllSamples()                                                                                                            #
###########################################################################################################################################
def prepareAllSamples(image_input, dic_classes_params, vector_to_cut_input, format_vector = 'ESRI Shapefile'):
    """
    Rôle : centralise la découpe des couches d'échantillons d'apprentissage selon l'emprise de la zone d'étude et d'une potentielle érosion

    Paramètres :
        image_input : image d'entrée brute
        dic_classes_params : dictionnaire des paramètres de préparation des échantillons d'apprentissage par classe.
                            Format :{"nomclasse" :[vector_class_input, raster_class_output, erosionoption]} 
        vector_to_cut_input : vecteur de découpage (zone d'étude)
        format_vector : format de la donnée vectorielle, par défaut : 'ESRI Shapefile'  
    """
    for key, value in dic_classes_params.items():
        prepareSamples(image_input, value[0], value[1], vector_to_cut_input, value[2], format_vector)
    
    return

###########################################################################################################################################
# FONCTION prepareSamples()                                                                                                               #
###########################################################################################################################################
def prepareSamples(image_ref, input_vector_class, output_raster_class, emprisevector, erosionoption = True, format_vector='ESRI Shapefile'):
    """
    Rôle : découper la couche d'échantillons d'apprentissage selon l'emprise de la zone d'étude et option d'érosion de 1m

    Paramètres :
        image_ref : image raster de référence pour la rasterisation en fin de fonction
        input_vector_class : couche vecteur d'échantillons d'apprentissage
        output_raster_class : couche raster d'échantillons d'apprentissage de sortie prête à être améliorée
        emprisevector : couche vecteur de l'emprise de la zone d'étude
        erosionoption : choix d'érosion de la couche d'échantillon en entrée, par défaut : True
        format_vector : format de la donnée vectorielle, par défaut : 'ESRI Shapefile'

    """

    if debug >= 2:
        print(" ")
        print(bold + green + "prepareSamples() : Variables dans la fonction" + endC)
        print(cyan + "prepareSamples() : " + endC + "image de référence : " + str(image_ref) + endC)
        print(cyan + "prepareSamples() : " + endC + "couche vecteur des échantillons à préparer : " + str(input_vector_class) + endC)
        print(cyan + "prepareSamples() : " + endC + "couche raster des échantillons en sortie : " + str(output_raster_class) + endC)
        print(cyan + "prepareSamples() : " + endC + "fichier vecteur emprise de la zone d'étude : " + str(emprisevector) + endC)
        print(cyan + "prepareSamples() : " + endC + "Erosion des polygones échantillons de 1m : " + str(erosionoption) + endC)
        print(cyan + "prepareSamples() : " + endC + "Format de la donnée vecteur en entrée : " + str(format_vector) + endC)

    if debug >= 3:
        print(cyan + "prepareSamples() : " + bold + green + "Traitement en cours..." + endC)

    # Création d'un fichier intermédiaire
    repertory_output = os.path.dirname(output_raster_class)
    file_name = os.path.splitext(os.path.basename(output_raster_class))[0]
    extension_vecteur = os.path.splitext(input_vector_class)[1]
    extension_raster = os.path.splitext(output_raster_class)[1]

    # Préparation des fichiers temporaires
    file_cut_suffix = "_cut"
    cut_file_tmp = repertory_output + os.sep + file_name + file_cut_suffix + extension_vecteur

    file_erosion_suffix = "_erosion"
    erosion_file_tmp = repertory_output + os.sep + file_name + file_erosion_suffix + extension_vecteur

    # Découpage du fichier vecteur de la classe avec l'emprise de la zone d'étude
    cutoutVectors(emprisevector, [input_vector_class], [cut_file_tmp], overwrite=True, format_vector=format_vector)

    # Erosion si option choisit
    if erosionoption :
        bufferVector(cut_file_tmp, erosion_file_tmp, -1, col_name_buf = "", fact_buf=1.0, quadsecs=10, format_vector=format_vector)
    else :
        erosion_file_tmp = cut_file_tmp
   # erosion_file_tmp = r'/mnt/RAM_disk/output_vector_erosion.gpkg'
    # Creation d'un masque binaire
    if output_raster_class != "" and image_ref != "" :
        repertory_output = os.path.dirname(output_raster_class)
        if not os.path.isdir(repertory_output):
            os.makedirs(repertory_output)
        # Préparation des fichiers temporaires
        file_cut_suffix = "_cutcut"
        cutcut_file_tmp = repertory_output + os.sep + file_name + file_cut_suffix + extension_raster
        rasterizeBinaryVector(erosion_file_tmp, image_ref, cutcut_file_tmp, 1)
        cutImageByVector(emprisevector ,cutcut_file_tmp, output_raster_class)

    if debug >= 3:
        print(cyan + "prepareSamples() : " + bold + green + "Fin du traitement." + endC)


    return

####################################################################################################################################
# FONCTION cleanSamples()                                                                                                          #
####################################################################################################################################
def cleanAllSamples(images_in_output, correction_images_dic, extension_raster = ".tif", save_results_intermediate = False, overwrite = False):
    """
    Rôle : nettoyer l'ensemble des couches d'échantillons d'apprentissage de classe

    Paramètres :
        images_in_output : dictionnaire des images d'entrée et de sortie des échantillons d'apprentissage.
                          Format :{"nomclasse" :[img_input, img_output], etc } 
        correction_images_dic : dictionnaire des corrections à apporter par classe et quel traitement.
                          Format :{"nomclasse" :[[nomtraitement, img_masque, seuilmin, seuilmax],[nomtraitement2, img_masque2, seuilmin2, seuilmax2]], etc} 
        extension_raster : extension des fichiers raster de sortir. Par defaut : '.tif'
        save_results_intermediate : fichiers de sorties intermediaires nettoyees. Par defaut : False
        overwrite : boolen ecrasement ou non des fichiers ayant un nom similaire. Par defaut : False
    """

    for key in images_in_output.keys():
        image_input = images_in_output[key][0]
        image_output = images_in_output[key][0]
        #Création du dictionnaire des corrections
        for treatment in correction_images_dic[key]:
            dic_correct_treat[treatment[0]] =[treatment[1], treatment[2], treatment[3]] 

        cleanSamples(image_input, image_output, dic_correct_treat, extension_raster, save_results_intermediate, overwrite)

    return 

####################################################################################################################################
# FONCTION cleanSamples()                                                                                                          #
####################################################################################################################################
def cleanSamples(image_input, image_output, correction_images_input_dic, extension_raster=".tif", save_results_intermediate= False, overwrite=False):
    """
    Rôle : nettoyer les pixels classés

    Paramètres :
        image_input : image du masque d'entrée à traiter
        image_output : image de sortie corrigée
        correction_images_input_dic : liste des images pour la correction et des seuils associés --> {"nom du traitement" : [imagemasque, seuilmin, seuilmax]}
        extension_raster : extension des fichiers raster de sortir. Par defaut : '.tif'
        save_results_intermediate : fichiers de sorties intermediaires nettoyees. Par defaut : False
        overwrite : boolen ecrasement ou non des fichiers ayant un nom similaire. Par defaut : False
    """
    if debug >= 3:
        print(" ")
        print(bold + green + "cleanSamples() : Variables dans la fonction" + endC)
        print(cyan + "cleanSamples() : " + endC + "image des échantillons à traiter : " + str(image_input) + endC)
        print(cyan + "cleanSamples() : " + endC + "image des échantillons nettoyées : " + str(image_output) + endC)
        print(cyan + "cleanSamples() : " + endC + "dictionnaire des traitements : " + str(correction_images_input_dic) + endC)
        print(cyan + "cleanSamples() : " + endC + "extension de la donnée raster : " + str(extension_raster) + endC)
        print(cyan + "cleanSamples() : " + endC + "sauvegarde des résultats intermédiaires : " + str(save_results_intermediate) + endC)
        print(cyan + "cleanSamples() : " + endC + "ré-écriture : " + str(overwrite) + endC)

    print(cyan + "cleanSamples() : " + bold + green + "Traitement en cours..." + endC)

    # Définition du répertoire temporaire
    repertory_samples_output = os.path.dirname(image_output)
    repertory_temp = repertory_samples_output + os.sep + "TMP_SAMPLES_CLEAN"

    # Création du répertoire temporaire si il n'existe pas
    if not os.path.isdir(repertory_temp):
        os.makedirs(repertory_temp)

    # Nettoyage du répertoire temporaire si il n'est pas vide
    cleanTempData(repertory_temp)

    # Test si le fichier résultat existent déjà et si ils doivent être écrasés
    check = os.path.isfile(image_output)
    if check and not overwrite: # Si les fichiers echantillons existent deja et que overwrite n'est pas activé
        print(bold + yellow + "File output : " + image_output + " already exists and will not be created again." + endC)
    else :
        if check:
            try:
                removeFile(image_output)
            except Exception:
                pass # si le fichier n'existe pas, il ne peut pas être supprimé : cette étape est ignorée

        # Information issue de la liste des paramètres de traitement
        if correction_images_input_dic == {} :
            # Pas de traitement à faire simple copie
            if debug >= 1:
                print(cyan + "processSamples() : " + endC + "Copy file" +  image_input + " to " + image_output)
            shutil.copyfile(image_input, image_output)
        else :
            # Liste de tous les traitement à faire
            cpt_treat = 0
            sample_raster_file_output = image_output
            # Parcourt le dictionnaire des traitements à effectuer
            for idx_treatment in correction_images_input_dic:
                print(cyan + "cleanSamples() : " + endC + "Début du traitement de la couche %s avec un filtrage sur le %s." %(image_input, idx_treatment))
                # Récupération de la liste des paramètres pour ce traitement
                treatment_info_list = correction_images_input_dic[idx_treatment]
                # Récupération du masque qui sert au nettoyage
                file_mask_input = treatment_info_list[0]

                threshold_min = float(treatment_info_list[1])
                threshold_max = float(treatment_info_list[2])

                if cpt_treat == 0:
                    sample_raster_file_input_temp = image_input

                # Appel de la fonction de traitement
                processingSample(sample_raster_file_input_temp, sample_raster_file_output, file_mask_input, threshold_min, threshold_max, repertory_temp)

                cpt_treat+=1

                if cpt_treat != len(correction_images_input_dic) :
                    sample_raster_file_input_temp = os.path.splitext(sample_raster_file_output)[0] +str(cpt_treat) + extension_raster
                    os.rename(sample_raster_file_output, sample_raster_file_input_temp)

                # Nettoyage du traitement precedent
                sample_raster_file_input_temp_before = os.path.splitext(sample_raster_file_output)[0] +str(cpt_treat-1) + extension_raster
                if os.path.isfile(sample_raster_file_input_temp_before) :
                    removeFile(sample_raster_file_input_temp_before)

    print(cyan + "cleanSamples() : " + bold + green + "Fin des traitements" + endC)

    # Suppression des données intermédiaires
    if not save_results_intermediate:

        # Supression des .geom dans le dossier
        for to_delete in glob.glob(repertory_samples_output + os.sep + "*.geom"):
            removeFile(to_delete)

        # Suppression du repertoire temporaire
        deleteDir(repertory_temp)

    return


###########################################################################################################################################
# FONCTION processSamples()                                                                                                               #
###########################################################################################################################################
def processingSample(sample_raster_file_input, sample_raster_file_output, file_mask_input, threshold_min, threshold_max, repertory_temp) :
    """
    Rôle : traiter fichier d'apprentissage avec le fichier d'amelioration

    Paramètres :
        sample_raster_file_input : fichier d'entrée contenant les echantillons à traiter
        sample_raster_file_output : fichier de sortie contenant les echantillons crées
        file_mask_input : le fichier d'entrée d'amélioration servant de base pour le masque
        threshold_min : seuil minimal pour la rasterisation en fichier binaire (masque) du fichier d'amélioration
        threshold_max : seuil maximal pour la rasterisation en fichier binaire (masque) du fichier d'amélioration
        repertory_temp : repertoire temporaire de travail
    """

    if debug >= 3:
        print(" ")
        print(bold + green + "processingSample() : Variables dans la fonction" + endC)
        print(cyan + "processingSample() : " + endC + "sample_raster_file_input : " + str(sample_raster_file_input) + endC)
        print(cyan + "processingSample() : " + endC + "sample_raster_file_output : " + str(sample_raster_file_output) + endC)
        print(cyan + "processingSample() : " + endC + "file_mask_input : " + str(file_mask_input) + endC)
        print(cyan + "processingSample() : " + endC + "threshold_min : " + str(threshold_min) + endC)
        print(cyan + "processingSample() : " + endC + "threshold_max : " + str(threshold_max) + endC)
        print(cyan + "processingSample() : " + endC + "repertory_temp : " + str(repertory_temp) + endC)

    print(cyan + "processingSample() : " + bold + green + "Traitement en cours..." + endC)

    # Traitement préparation
    file_mask_output_temp = repertory_temp + os.sep + os.path.splitext(os.path.basename(file_mask_input))[0] + "_mask_tmp" + os.path.splitext(file_mask_input)[1]
    if os.path.isfile(file_mask_output_temp) :
        removeFile(file_mask_output_temp)

    # Creation masque binaire
    createBinaryMaskThreshold(file_mask_input, file_mask_output_temp, threshold_min, threshold_max)

    # Masquage des zones non retenues
    applyMaskAnd(sample_raster_file_input, file_mask_output_temp, sample_raster_file_output)

    print(cyan + "processingSample() : " + bold + green + "Fin du traitement" + endC)


    return
