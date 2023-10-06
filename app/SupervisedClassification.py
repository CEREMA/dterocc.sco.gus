#Import des librairie de Python
import os,sys,time

#Import des librairies /libs
from libs.Lib_display import bold,red,green,yellow,cyan,endC
from libs.Lib_operator import getExtensionApplication
from libs.Lib_raster import updateReferenceProjection, getGeometryImage, computeStatisticsImage
from libs.Lib_file import removeFile
from libs.Lib_text import appendTextFileCR

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 3

###########################################################################################################################################
# STRUCTURE StructRFParameter                                                                                                             #
###########################################################################################################################################
class StructRFParameter:
    """
    # Structure contenant les parametres utiles au calcul du model RF
    """
    def __init__(self):
        self.max_depth_tree = 0
        self.min_sample = 0
        self.ra_termin_criteria = 0.0
        self.cat_clusters = 0
        self.var_size_features = 0
        self.nbtrees_max = 0
        self.acc_obb_erreur = 0.0



###########################################################################################################################################
# FONCTION computeModelRF()                                                                                                               #
###########################################################################################################################################
def computeModelRF(sample_values_input, statistics_image_input, model_file_output, matrix_file_output, field_class, feat_list, rf_parametres_struct) :
    """
    # ROLE:
    #    Calcul le model utile à la creation de la classification selon l'algorithme RF
    #
    # ENTREES DE LA FONCTION :
    #    sample_values_input : fichier de valeur d'echantillons points au format .shp
    #    statistics_image_input : fichier statistique .xml
    #    model_file_output : fichier model résultat
    #    matrix_file_output : fichier matrice de confusion
    #    field_class : label (colonne) pour distinguer les classes exemple : "id"
    #    feat_list : liste des noms des champs à prendre en compte pour le model
    #    rf_parametres_struct : les paramètres du RF
    #
    # SORTIES DE LA FONCTION :
    #    auccun
    #    Eléments générés par la fonction : un fichier model ("*_model.txt")
    #
    """

    feat_list_str = ""
    for feat in feat_list:
        feat_list_str += feat + ' '

    # Calcul du model
    command = "otbcli_TrainVectorClassifier -io.vd %s -io.stats %s -io.out %s -io.confmatout %s -cfield %s -feat %s -classifier rf -classifier.rf.max %d -classifier.rf.min %d -classifier.rf.ra %f -classifier.rf.cat %d -classifier.rf.var %d -classifier.rf.nbtrees %d -classifier.rf.acc %f" %(sample_values_input,statistics_image_input,model_file_output,matrix_file_output,field_class,feat_list_str,rf_parametres_struct.max_depth_tree,rf_parametres_struct.min_sample,rf_parametres_struct.ra_termin_criteria,rf_parametres_struct.cat_clusters,rf_parametres_struct.var_size_features,rf_parametres_struct.nbtrees_max,rf_parametres_struct.acc_obb_erreur)

    if debug >= 3:
        print(command)

    exitCode = os.system(command)
    if exitCode != 0:
        raise NameError(cyan + "computeModelRF() : " + bold + red + "An error occured during otbcli_TrainVectorClassifier command. See error message above." + endC)

    #fd = os.open( model_file_output, os.O_RDWR|os.O_CREAT )
    #os.fsync(fd)
    #os.close(fd)

    return

###########################################################################################################################################
# FONCTION classifySupervised()                                                                                                           #
###########################################################################################################################################
def classifySupervised(image_input_list, sample_points_values_input, classification_file_output, confidence_file_output, model_output, model_input, field_class, classifier_mode, rf_parametres_struct, no_data_value, ram_otb=0,  format_raster='GTiff', extension_vector=".shp", save_results_intermediate=False, overwrite=True):
    """
    Rôle :
         Execute une classification supervisee sur des images (brutes ou avec neocanaux) en se basant sur des echantillons d'entrainement vectorises dans un shapefile.
        La classification se déroule en 6 etapes :
           1) calcul des statistiques de l'image,
           2) calcul des statistiques des polygones des échantillons,
           3) selection des échantillons à partir de l'image des polygones d'échantillon et des statistiques des polygones des échantillons,
           4) extraction des échantillons seléctionés à partir l'image et des échantillons points selectionés,
           5) creation du model a partir des echantillons points et des statistiques image,
           6) classification a partir des statistiques et du model
    
    Paramètres : 
        image_input_list : liste d'image d'entrée stacké au format .tif
        sample_points_values_input : fichier de points d'échantillons en entrée au format .shp
        classification_file_output : fichier resultat de la classification
        confidence_file_output : fichier contenant la carte de confiance associer à la classification
        model_output : fichier model sauvegarder en sortie avec se nom
        model_input : fichier model d'entrée, il ne sera pas regénérer mais utilisé directement
        field_class : label (colonne) pour distinguer les classes exemple : "id"
        classifier_mode : definie le choix du type de classification ("svm" ou "rf")
        rf_parametres_struct : les paramètres du RF
        no_data_value : Option : Value pixel of no data
        ram_otb : memoire RAM disponible pour les applications OTB
        format_raster : Format de l'image de sortie par défaut GTiff (GTiff, HFA...)
        extension_vector : extension du fichier vecteur de sortie, par defaut = '.shp'
        save_results_intermediate : fichiers de sorties intermediaires nettoyees, par defaut = False
        overwrite : supprime ou non les fichiers existants ayant le meme nom
    
    Sortie :
        Eléments générés par la fonction : deux fichiers statistics ("*_statistics.xml"), un fichier model ("*_model.txt"), une image classee("*_raw.tif")
    
    """

    # Mise à jour du Log
    starting_event = "classifySupervised() : Classifiy supervised starting : "

    print(endC)
    print(bold + green + "## START :  SUPERVISED CLASSIFICATION" + endC)
    print(endC)

    if debug >= 3:
        print(cyan + "classifySupervised() : " + endC + "image_input_list : " + str(image_input_list) + endC)
        print(cyan + "classifySupervised() : " + endC + "sample_points_values_input : " + str(sample_points_values_input) + endC)
        print(cyan + "classifySupervised() : " + endC + "classification_file_output : " + str(classification_file_output) + endC)
        print(cyan + "classifySupervised() : " + endC + "confidence_file_output : " + str(confidence_file_output) + endC)
        print(cyan + "classifySupervised() : " + endC + "model_output : " + str(model_output) + endC)
        print(cyan + "classifySupervised() : " + endC + "model_input : " + str(model_input) + endC)
        print(cyan + "classifySupervised() : " + endC + "field_class : " + str(field_class) + endC)
        print(cyan + "classifySupervised() : " + endC + "classifier_mode : " + str(classifier_mode) + endC)
        print(cyan + "classifySupervised() : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "classifySupervised() : " + endC + "ram_otb : " + str(ram_otb) + endC)
        print(cyan + "classifySupervised() : " + endC + "format_raster : " + str(format_raster) + endC)
        print(cyan + "classifySupervised() : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "classifySupervised() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "classifySupervised() : " + endC + "overwrite : " + str(overwrite) + endC)

    # Constantes
    CODAGE_16B = "uint16"
    CODAGE_F = "float"

    EXT_XML = ".xml"
    EXT_TEXT = ".txt"

    SUFFIX_STATISTICS = "_statistics"
    SUFFIX_IMAGE = "_image"
    SUFFIX_POLYGON = "_polygon"
    SUFFIX_SAMPLE = "_sample"
    SUFFIX_POINTS = "_points"
    SUFFIX_VALUES = "_values"
    SUFFIX_MODEL = "_model"
    SUFFIX_MATRIX = "_matrix"
    SUFFIX_MERGE = "_merge"

    BAND_NAME = "band_"

    # 0. PREPARATION DES FICHIERS TEMPORAIRES
    #----------------------------------------

    # Définir les fichiers de sortie temporaire (statistiques image / statistiques polygone / model)
    image_input = image_input_list[0]
    nb_input_images = len(image_input_list)
    name = os.path.splitext(os.path.basename(image_input))[0]
    repertory_output = os.path.dirname(classification_file_output)
    statistics_image_output = repertory_output + os.sep + name + SUFFIX_IMAGE + SUFFIX_STATISTICS + EXT_XML
    sample_points_values_output = repertory_output + os.sep + name +  SUFFIX_SAMPLE + SUFFIX_VALUES + extension_vector
    matrix_file_output = repertory_output + os.sep + name + SUFFIX_MATRIX + EXT_TEXT

    pass_compute_model = False
    if model_input != "" :
        model_file_output = model_input
        pass_compute_model = True
    elif model_output != "" :
        model_file_output = model_output
    else :
        model_file_output = repertory_output + os.sep + name + SUFFIX_MODEL + EXT_TEXT
    
    # 1. CALCUL DES STATISTIQUES DE L'IMAGE SAT
    #------------------------------------------

    print(cyan + "classifySupervised() : " + bold + green + "Statistics computation for input images ..." + endC)

    # Vérification de l'existence des images pour calculer les statistiques
    list_image_input_str = ""
    for image_input_tmp in image_input_list :
        list_image_input_str = image_input_tmp + " "
        if not os.path.isfile(image_input_tmp):
            raise NameError(cyan + "classifySupervised() : " + bold + red + "No image %s available.\n" %(image_input_tmp) + endC)

    # Si les statistiques existent deja et que overwrite n'est pas activé
    check = os.path.isfile(statistics_image_output)
    if check and not overwrite:
        print(bold + yellow + "Statistics computation %s already done for image and will not be calculated again." %(statistics_image_output) + endC)
    else:   # Si non ou si la vérification est désactivée : calcul des statistiques de l'image

        # Suppression de l'éventuel fichier existant
        if check:
            try:
                removeFile(statistics_image_output)
            except Exception:
                pass # Si le fichier ne peut pas être supprimé, on suppose qu'il n'existe pas et on passe à la suite

        # Calcul statistique
        if nb_input_images == 1:
            computeStatisticsImage(image_input, statistics_image_output)

        else :
            command = "otbcli_ComputeImagesStatistics -il %s -out %s" %(list_image_input_str, statistics_image_output)
            if ram_otb > 0:
                    command += " -ram %d" %(ram_otb)

            if debug >= 3:
                print(command)

            exitCode = os.system(command)
            if exitCode != 0:
                raise NameError(cyan + "classifySupervised() : " + bold + red + "An error occured during otbcli_ComputeImagesStatistics command. See error message above." + endC)

        print(cyan + "classifySupervised() : " + bold + green + "Statistics image are ready." + endC)

    # 2.CALCUL DU MODELE
    #----------------------------- 
    
    print(cyan + "classifySupervised() : " + bold + green + "Classification model computation for input images ..." + endC)

    # Vérification de l'existence du vecteur de valeurs d'entrainement pour creer le modèle de classification
    if not os.path.isfile(sample_points_values_input):
        raise NameError(cyan + "classifySupervised() : " + bold + red + "No training vector %s available.\n" %(sample_points_values_input) + endC)

    # Vérification de l'existence du fichier statistique pour creer le modèle de classification
    if not os.path.isfile(statistics_image_output):
        raise NameError(cyan + "classifySupervised() : " + bold + red + "No statistics file %s available.\n" %(statistics_image_output) + endC)

    # Si modèle de classification associé à l'image existe deja et que overwrite n'est pas activé
    check = os.path.isfile(model_file_output)
    if check and not overwrite:
        print(cyan + "classifySupervised() : " + bold + yellow + "Model %s already computed and will not be calculated again." %(model_file_output) + endC)
    else: # Si non ou si la vérification est désactivée : calcul du model pour la classification

        # Suppression de l'éventuel fichier existant
        if check:
            try:
                removeFile(model_file_output)
            except Exception:
                pass # Si le fichier ne peut pas être supprimé, on suppose qu'il n'existe pas et on passe à la suite

        # Récupération des champs utiles pour le calcul du model
        cols, rows, bands = getGeometryImage(image_input)
        feat_list = []
        for i in range(bands) :
            feat_list.append(BAND_NAME + str(i))

        # Calcul du model en fonction de l'algo choisi
        if classifier_mode.lower() == "rf" :
            computeModelRF(sample_points_values_input, statistics_image_output, model_file_output, matrix_file_output, field_class, feat_list, rf_parametres_struct)
        
        print(cyan + "classifySupervised() : " + bold + green + "Model are ready." + endC)

    # 3. CLASSIFICATION DE L'IMAGE
    #-----------------------------

    print(cyan + "classifySupervised() : " + bold + green + "Classification image creation for input images with model %s ..." %(model_file_output) + endC)

    # Vérification de l'existence du fichier modèle pour faire la classification
    if not os.path.isfile(model_file_output):
        raise NameError (cyan + "classifySupervised() : " + bold + red + '\n' + "No classification model %s available." %(model_file_output) + endC)

    # Si la classification existe deja et que overwrite n'est pas activé
    check = os.path.isfile(classification_file_output)
    if check and not overwrite:
        print(cyan + "classifySupervised() : " + bold + yellow + "Classification image %s already computed and will not be create again."  %(classification_file_output) + endC)
    else: # Si non ou si la vérification est désactivée : création de la classification

        # Suppression de l'éventuel fichier existant
        if check:
            try:
                removeFile(classification_file_output)
            except Exception:
                pass # Si le fichier ne peut pas être supprimé, on suppose qu'il n'existe pas et on passe à la suite

        # Tempo attente fin d'ecriture du model sur le disque
        time.sleep(5)

        # Pour toutes les images d'entrée à classer
        classification_file_output_list = []
        for image_input_tmp in image_input_list :
            if nb_input_images == 1 :
                classification_file_output_tmp = classification_file_output
            else :
                 image_name =  os.path.splitext(os.path.basename(image_input_tmp))[0]
                 classification_file_output_tmp = os.path.splitext(classification_file_output)[0] + "_" + image_name + os.path.splitext(classification_file_output)[1]
                 classification_file_output_list.append(classification_file_output_tmp)

            # Création de la classification
            command = "otbcli_ImageClassifier -in %s -imstat %s -model %s -out %s %s" %(image_input_tmp, statistics_image_output, model_file_output, classification_file_output_tmp, CODAGE_16B)

            if confidence_file_output != "" :
                command += " -confmap %s %s" %(confidence_file_output, CODAGE_F)

            if ram_otb > 0:
                command += " -ram %d" %(ram_otb)

            if debug >= 3:
                print(command)

            exitCode = os.system(command)
            if exitCode != 0:
                raise NameError(cyan + "classifySupervised() : " + bold + red + "An error occured during otbcli_ImageClassifier command. See error message above." + endC)

            # Bug OTB mise a jour de la projection du résultat de la classification
            updateReferenceProjection(image_input_tmp, classification_file_output_tmp)

        # Si plusieurs images demander fusion des classifications
        if nb_input_images > 1 :

            file_name = os.path.splitext(os.path.basename(classification_file_output))[0]
            pixel_size_x, pixel_size_y = getPixelWidthXYImage(image_input)

            # Fichier txt temporaire liste des fichiers a merger
            list_file_tmp = repertory_output + os.sep + file_name + SUFFIX_MERGE + EXT_TEXT

            for classification_file_output_tmp in classification_file_output_list:
                appendTextFileCR(list_file_tmp, classification_file_output_tmp)

            cmd_merge = "gdal_merge" + getExtensionApplication() + " -of " + format_raster + " -ps " + str(pixel_size_x) + " " + str(pixel_size_y) + " -n " + str(no_data_value) + " -o "  + classification_file_output + " --optfile " + list_file_tmp
            print(cmd_merge)
            exit_code = os.system(cmd_merge)
            if exit_code != 0:
                raise NameError(cyan + "classifySupervised() : " + bold + red + "!!! Une erreur c'est produite au cours du merge des classification. Voir message d'erreur."  + endC)

        print(cyan + "classifySupervised() : " + bold + green + "Classification complete." + endC)


    # 7. SUPPRESSION DES FICHIERS INTERMEDIAIRES
    #-------------------------------------------

    # Suppression des données intermédiaires
    if not save_results_intermediate:
        if model_output == "" and model_input == "" and os.path.isfile(model_file_output) :
            removeFile(model_file_output)
        if nb_input_images > 1 :
            removeFile(list_file_tmp)
            for classification_file_output_tmp in classification_file_output_list :
                removeFile(classification_file_output_tmp)

    print(endC)
    print(bold + green + "## END :  SUPERVISED CLASSIFICATION" + endC)
    print(endC)

    # Mise à jour du Log
    ending_event = "classifySupervised() : Classifiy supervised ending : "

    return
