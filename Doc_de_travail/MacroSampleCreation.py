"""
Date de création : 26/06/2023

Choses à faire :
    - remplacer les paramètres en entrée de macroSamplePrepare par des listes de couches à traiter
    - boucler le fonction sur la liste des couches à traiter
"""



from __future__ import print_function
import os,sys,glob,shutil,string, argparse
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_log import timeLine
from Lib_file import cleanTempData, deleteDir, removeFile
from Lib_raster import *
from Lib_vector import *

def macroSamplePrepare(image_input, input_vector_class, output_raster_class, emprisevector, erosionoption = True, format_vector='ESRI Shapefile'):
    """
    Rôle : découper la couche d'échantillons d'apprentissage selon l'emprise de la zone d'étude et option d'érosion de 1m

    Paramètres :
        image_input : image raster en entrée
        input_vector_class : couche vecteur d'échantillons d'apprentissage
        output_raster_class : couche raster d'échantillons d'apprentissage de sortie prête à être améliorée
        emprisevector : couche vecteur de l'emprise de la zone d'étude
        erosionoption : choix d'érosion de la couche d'échantillon en entrée, par défaut : True
        format_vector : format de la donnée vectorielle, par défaut : 'ESRI Shapefile'

    """

    # Création d'un fichier intermédiaire
    # repertory_output = os.path.dirname(output_raster_class)
    # file_name = os.path.splitext(os.path.basename(output_raster_class))[0]
    # extension_vecteur = os.path.splitext(input_vector_class)[1]
    # extension_raster = os.path.splitext(output_raster_class)[1]

    # # Préparation des fichiers temporaires
    # file_cut_suffix = "_cut"
    # cut_file_tmp = repertory_output + os.sep + file_name + file_cut_suffix + extension_vecteur

    # file_erosion_suffix = "_erosion"
    # erosion_file_tmp = repertory_output + os.sep + file_name + file_erosion_suffix + extension_vecteur

    # # Découpage du fichier vecteur de la classe avec l'emprise de la zone d'étude
    # cutoutVectors(emprisevector, [input_vector_class], [cut_file_tmp], overwrite=True, format_vector=format_vector)

    # # Erosion si option choisit
    # if erosionoption :
        # bufferVector(cut_file_tmp, erosion_file_tmp, -1, col_name_buf = "", fact_buf=1.0, quadsecs=10, format_vector=format_vector)
    # else :
        # erosion_file_tmp = cut_file_tmp
    erosion_file_tmp = r'/mnt/RAM_disk/output_vector_erosion.gpkg'
    # Creation d'un masque binaire
    if output_raster_class != "" and image_input != "" :
        repertory_output = os.path.dirname(output_raster_class)
        if not os.path.isdir(repertory_output):
            os.makedirs(repertory_output)
        rasterizeBinaryVector(erosion_file_tmp, image_input, output_raster_class, 1)

    return

def macroSampleCleaning(image_input, image_output, correction_images_input_list, extension_raster=".tif", save_results_intermediate=False, overwrite=True):
    """
    Rôle : nettoyer les pixels classés

    Paramètres :
        image_input : image du masque d'entrée à traiter
        image_output : image de sortie corrigée
        correction_images_input_dic : liste des images pour la correction et des seuils associés
        extension_raster : extension des fichiers raster de sortie, par defaut = '.tif'
        save_results_intermediate : fichiers de sorties intermediaires nettoyees, par defaut = False
        overwrite : boolen ecrasement ou non des fichiers ayant un nom similaire, par defaut à True
    """

    # Définition du répertoire temporaire
    repertory_samples_output = os.path.dirname(image_output)
    repertory_temp = repertory_samples_output + os.sep + FOLDER_MASK_TEMP

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
        if correction_images_input_list == [] :
            # Pas de traitement à faire simple copie
            if debug >= 1:
                print(cyan + "processMacroSamples() : " + endC + "Copy file" +  image_input + " to " + image_output)
            shutil.copyfile(image_input, image_output)
        else :
            # Liste de tous les traitement à faire
            cpt_treat = 0
            sample_raster_file_output = image_output
            for idx_treatement in range(len(correction_images_input_list)):

                treatement_info_list = treatment_mask_list[idx_treatement]
                file_mask_input = correction_images_input_list[idx_treatement]

                if debug >= 3:
                    print(cyan + "processMacroSamples() : " + endC + "Traitement parametres : " + str(treatement_info_list) + " avec l'image : " + file_mask_input)

                base_mask_name = treatement_info_list[0]
                threshold_min = float(treatement_info_list[1])
                threshold_max = float(treatement_info_list[2])

                if len(treatement_info_list) >= 4:
                    filter_size_zone_0 = int(treatement_info_list[3])
                else :
                    filter_size_zone_0 = 0

                if len(treatement_info_list) >= 5:
                    filter_size_zone_1 = int(treatement_info_list[4])
                else :
                    filter_size_zone_1 = 0

                if len(treatement_info_list) >= 6:
                    mask_operator = str(treatement_info_list[5])
                else :
                    mask_operator = "and"

                if cpt_treat == 0:
                    sample_raster_file_input_temp = image_input

                # Appel de la fonction de traitement
                processingMacroSample(sample_raster_file_input_temp, sample_raster_file_output, file_mask_input, threshold_min, threshold_max, filter_size_zone_0, filter_size_zone_1, mask_operator, repertory_temp, CODAGE, path_time_log)

                cpt_treat+=1

                if cpt_treat != len(correction_images_input_list) :
                    sample_raster_file_input_temp = os.path.splitext(sample_raster_file_output)[0] +str(cpt_treat) + extension_raster
                    os.rename(sample_raster_file_output, sample_raster_file_input_temp)

                # Nettoyage du traitement precedent
                sample_raster_file_input_temp_before = os.path.splitext(sample_raster_file_output)[0] +str(cpt_treat-1) + extension_raster
                if os.path.isfile(sample_raster_file_input_temp_before) :
                    removeFile(sample_raster_file_input_temp_before)

    print(cyan + "processMacroSamples() : " + bold + green + "Fin des traitements" + endC)

    # Suppression des données intermédiaires
    if not save_results_intermediate:

        # Supression des .geom dans le dossier
        for to_delete in glob.glob(repertory_samples_output + os.sep + "*.geom"):
            removeFile(to_delete)

        # Suppression du repertoire temporaire
        deleteDir(repertory_temp)

    return

# Import des bibliothèques python
from __future__ import print_function
import os,sys,glob,shutil,string, argparse
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_log import timeLine
from Lib_file import cleanTempData, deleteDir, removeFile
from Lib_raster import createBinaryMaskThreshold, filterBinaryRaster, applyMaskAnd, applyMaskOr

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 3

###########################################################################################################################################
# FONCTION processMacroSamples()                                                                                                          #
###########################################################################################################################################
def processingMacroSample(sample_raster_file_input, sample_raster_file_output, file_mask_input, threshold_min, threshold_max, filter_size_zone_0, filter_size_zone_1, mask_operator, repertory_temp, codage, path_time_log) :
    """
    # ROLE:
    #    Traiter fichier d'apprentissage avec le fichier d'amelioration
    #
    # ENTREES DE LA FONCTION :
    #    sample_raster_file_input : fichier d'entrée contenant les echantillons macro à traiter
    #    sample_raster_file_output : fichier de sortie contenant les echantillons macro crées
    #    file_mask_input : le fichier d'entrée d'amélioration servant de base pour le masque
    #    threshold_min : seuil minimal pour la rasterisation en fichier binaire (masque) du fichier d'amélioration
    #    threshold_max : seuil maximal pour la rasterisation en fichier binaire (masque) du fichier d'amélioration
    #    filter_size_zone_0 : parametre de filtrage du masque définie la taille de la feparser.add_argument('-debug','--debug',default=3,help="Option : Value of level debug trace, default : 3 ",type=int, required=False)nêtre pour les zones à 0
    #    filter_size_zone_1 : parametre de filtrage du masque définie la taille de la fenêtre pour les zones à 1
    #    mask_operator : operateur de fusion entre l'image source et le nouveau masque creer : possible :(and, or)
    #    repertory_temp : repertoire temporaire de travail
    #    codage : type de codage du fichier de sortie
    #    path_time_log : le fichier de log de sortie
    #
    # SORTIES DE LA FONCTION :
    #    auccun
    #    Eléments générés par la fonction : raster d'echantillon masquer avec le fichier d'amelioration
    #
    """

    if debug >= 3:
        print(" ")
        print(bold + green + "processingMacroSample() : Variables dans la fonction" + endC)
        print(cyan + "processingMacroSample() : " + endC + "sample_raster_file_input : " + str(sample_raster_file_input) + endC)
        print(cyan + "processingMacroSample() : " + endC + "sample_raster_file_output : " + str(sample_raster_file_output) + endC)
        print(cyan + "processingMacroSample() : " + endC + "file_mask_input : " + str(file_mask_input) + endC)
        print(cyan + "processingMacroSample() : " + endC + "threshold_min : " + str(threshold_min) + endC)
        print(cyan + "processingMacroSample() : " + endC + "threshold_max : " + str(threshold_max) + endC)
        print(cyan + "processingMacroSample() : " + endC + "filter_size_zone_0 : " + str(filter_size_zone_0) + endC)
        print(cyan + "processingMacroSample() : " + endC + "filter_size_zone_1 : " + str(filter_size_zone_1) + endC)
        print(cyan + "processingMacroSample() : " + endC + "mask_operator : " + str(mask_operator) + endC)
        print(cyan + "processingMacroSample() : " + endC + "repertory_temp : " + str(repertory_temp) + endC)
        print(cyan + "processingMacroSample() : " + endC + "codage : " + str(codage) + endC)
        print(cyan + "processingMacroSample() : " + endC + "path_time_log : " + str(path_time_log) + endC)

    print(cyan + "processingMacroSample() : " + bold + green + "Traitement en cours..." + endC)

    # Traitement préparation
    file_mask_output_temp = repertory_temp + os.sep + os.path.splitext(os.path.basename(file_mask_input))[0] + "_mask_tmp" + os.path.splitext(file_mask_input)[1]
    if os.path.isfile(file_mask_output_temp) :
        removeFile(file_mask_output_temp)
    file_mask_filtered_output_temp = repertory_temp + os.sep + os.path.splitext(os.path.basename(file_mask_input))[0] + "_mask_filtered_tmp" + os.path.splitext(file_mask_input)[1]
    if os.path.isfile(file_mask_filtered_output_temp) :
        removeFile(file_mask_filtered_output_temp)

    # Creation masque binaire
    createBinaryMaskThreshold(file_mask_input, file_mask_output_temp, threshold_min, threshold_max)

    # Filtrage binaire
    if filter_size_zone_0 != 0 or filter_size_zone_1 != 0 :
        filterBinaryRaster(file_mask_output_temp, file_mask_filtered_output_temp, filter_size_zone_0, filter_size_zone_1)
    else :
        file_mask_filtered_output_temp = file_mask_output_temp

    # Masquage des zones non retenues
    if mask_operator.lower() == "and" :
        applyMaskAnd(sample_raster_file_input, file_mask_filtered_output_temp, sample_raster_file_output, codage)
    elif mask_operator.lower() == "or" :
        applyMaskOr(sample_raster_file_input, file_mask_filtered_output_temp, sample_raster_file_output, codage)
    else :
        raise NameError (cyan + "processingMacroSample() : " + bold + red  + "Mask operator unknown : " + str(mask_operator) + endC)

    print(cyan + "processingMacroSample() : " + bold + green + "Fin du traitement" + endC)


    return
