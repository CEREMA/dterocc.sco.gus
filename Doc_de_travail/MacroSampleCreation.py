"""
Date de création : 26/06/2023

Choses à faire :
    - remplacer les paramètres en entrée de macroSamplePrepare par des listes de couches à traiter
    - boucler le fonction sur la liste des couches à traiter
"""


# Import des bibliothèques python
from __future__ import print_function
import os,sys,glob,shutil,string, argparse
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_file import cleanTempData, deleteDir, removeFile
from Lib_raster import createBinaryMaskThreshold, filterBinaryRaster, applyMaskAnd, applyMaskOr, rasterizeBinaryVector
from Lib_vector import *
from ImagesAssemblyGUS import  *


# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 3


###########################################################################################################################################
# FONCTION macroSamplesPrepare()                                                                                                          #
###########################################################################################################################################
def macroSamplesPrepare(image_ref, input_vector_class, output_raster_class, emprisevector, erosionoption = True, format_vector='ESRI Shapefile'):
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

    if debug >= 3:
        print(" ")
        print(bold + green + "macroSamplesPrepare() : Variables dans la fonction" + endC)
        print(cyan + "macroSamplesPrepare() : " + endC + "image de référence : " + str(image_ref) + endC)
        print(cyan + "macroSamplesPrepare() : " + endC + "couche vecteur des échantillons à préparer : " + str(input_vector_class) + endC)
        print(cyan + "macroSamplesPrepare() : " + endC + "couche raster des échantillons en sortie : " + str(output_raster_class) + endC)
        print(cyan + "macroSamplesPrepare() : " + endC + "fichier vecteur emprise de la zone d'étude : " + str(emprisevector) + endC)
        print(cyan + "macroSamplesPrepare() : " + endC + "Erosion des polygones échantillons de 1m : " + str(erosionoption) + endC)
        print(cyan + "macroSamplesPrepare() : " + endC + "Format de la donnée vecteur en entrée : " + str(format_vector) + endC)

    print(cyan + "macroSamplesPrepare() : " + bold + green + "Traitement en cours..." + endC)

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

    print(cyan + "macroSamplesPrepare() : " + bold + green + "Fin du traitement." + endC)


    return


###########################################################################################################################################
# FONCTION macroSamplesClean()                                                                                                          #
###########################################################################################################################################
def macroSamplesClean(image_input, image_output, correction_images_input_dic, extension_raster=".tif", save_results_intermediate=True, overwrite=True):
    """
    Rôle : nettoyer les pixels classés

    Paramètres :
        image_input : image du masque d'entrée à traiter
        image_output : image de sortie corrigée
        correction_images_input_dic : liste des images pour la correction et des seuils associés --> {"nom du traitement" : [imagemasque, seuilmin, seuilmax]}
        extension_raster : extension des fichiers raster de sortie, par defaut = '.tif'
        save_results_intermediate : fichiers de sorties intermediaires nettoyees, par defaut = False
        overwrite : boolen ecrasement ou non des fichiers ayant un nom similaire, par defaut à True
    """
    if debug >= 3:
        print(" ")
        print(bold + green + "macroSamplesClean() : Variables dans la fonction" + endC)
        print(cyan + "macroSamplesClean() : " + endC + "image des échantillons à traiter : " + str(image_input) + endC)
        print(cyan + "macroSamplesClean() : " + endC + "image des échantillons nettoyées : " + str(image_output) + endC)
        print(cyan + "macroSamplesClean() : " + endC + "dictionnaire des traitements : " + str(correction_images_input_dic) + endC)
        print(cyan + "macroSamplesClean() : " + endC + "extension de la donnée raster : " + str(extension_raster) + endC)
        print(cyan + "macroSamplesClean() : " + endC + "sauvegarde des résultats intermédiaires : " + str(save_results_intermediate) + endC)
        print(cyan + "macroSamplesClean() : " + endC + "ré-écriture : " + str(overwrite) + endC)

    print(cyan + "macroSamplesClean() : " + bold + green + "Traitement en cours..." + endC)

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
                print(cyan + "processMacroSamples() : " + endC + "Copy file" +  image_input + " to " + image_output)
            shutil.copyfile(image_input, image_output)
        else :
            # Liste de tous les traitement à faire
            cpt_treat = 0
            sample_raster_file_output = image_output
            # Parcourt le dictionnaire des traitements à effectuer
            for idx_treatment in correction_images_input_dic:
                print(cyan + "macroSamplesClean() : " + endC + "Début du traitement de la couche %s avec un filtrage sur le %s." %(image_input, idx_treatment))
                # Récupération de la liste des paramètres pour ce traitement
                treatment_info_list = correction_images_input_dic[idx_treatment]
                # Récupération du masque qui sert au nettoyage
                file_mask_input = treatment_info_list[0]

                threshold_min = float(treatment_info_list[1])
                threshold_max = float(treatment_info_list[2])

                if cpt_treat == 0:
                    sample_raster_file_input_temp = image_input

                # Appel de la fonction de traitement
                processingMacroSample(sample_raster_file_input_temp, sample_raster_file_output, file_mask_input, threshold_min, threshold_max, repertory_temp)

                cpt_treat+=1

                if cpt_treat != len(correction_images_input_dic) :
                    sample_raster_file_input_temp = os.path.splitext(sample_raster_file_output)[0] +str(cpt_treat) + extension_raster
                    os.rename(sample_raster_file_output, sample_raster_file_input_temp)

                # Nettoyage du traitement precedent
                sample_raster_file_input_temp_before = os.path.splitext(sample_raster_file_output)[0] +str(cpt_treat-1) + extension_raster
                if os.path.isfile(sample_raster_file_input_temp_before) :
                    removeFile(sample_raster_file_input_temp_before)

    print(cyan + "macroSamplesClean() : " + bold + green + "Fin des traitements" + endC)

    # Suppression des données intermédiaires
    if not save_results_intermediate:

        # Supression des .geom dans le dossier
        for to_delete in glob.glob(repertory_samples_output + os.sep + "*.geom"):
            removeFile(to_delete)

        # Suppression du repertoire temporaire
        deleteDir(repertory_temp)

    return


###########################################################################################################################################
# FONCTION processMacroSamples()                                                                                                          #
###########################################################################################################################################
def processingMacroSample(sample_raster_file_input, sample_raster_file_output, file_mask_input, threshold_min, threshold_max, repertory_temp) :
    """
    Rôle : traiter fichier d'apprentissage avec le fichier d'amelioration

    Paramètres :
        sample_raster_file_input : fichier d'entrée contenant les echantillons macro à traiter
        sample_raster_file_output : fichier de sortie contenant les echantillons macro crées
        file_mask_input : le fichier d'entrée d'amélioration servant de base pour le masque
        threshold_min : seuil minimal pour la rasterisation en fichier binaire (masque) du fichier d'amélioration
        threshold_max : seuil maximal pour la rasterisation en fichier binaire (masque) du fichier d'amélioration
        repertory_temp : repertoire temporaire de travail
    """

    if debug >= 3:
        print(" ")
        print(bold + green + "processingMacroSample() : Variables dans la fonction" + endC)
        print(cyan + "processingMacroSample() : " + endC + "sample_raster_file_input : " + str(sample_raster_file_input) + endC)
        print(cyan + "processingMacroSample() : " + endC + "sample_raster_file_output : " + str(sample_raster_file_output) + endC)
        print(cyan + "processingMacroSample() : " + endC + "file_mask_input : " + str(file_mask_input) + endC)
        print(cyan + "processingMacroSample() : " + endC + "threshold_min : " + str(threshold_min) + endC)
        print(cyan + "processingMacroSample() : " + endC + "threshold_max : " + str(threshold_max) + endC)
        print(cyan + "processingMacroSample() : " + endC + "repertory_temp : " + str(repertory_temp) + endC)

    print(cyan + "processingMacroSample() : " + bold + green + "Traitement en cours..." + endC)

    # Traitement préparation
    file_mask_output_temp = repertory_temp + os.sep + os.path.splitext(os.path.basename(file_mask_input))[0] + "_mask_tmp" + os.path.splitext(file_mask_input)[1]
    if os.path.isfile(file_mask_output_temp) :
        removeFile(file_mask_output_temp)

    # Creation masque binaire
    createBinaryMaskThreshold(file_mask_input, file_mask_output_temp, threshold_min, threshold_max)

    # Masquage des zones non retenues
    applyMaskAnd(sample_raster_file_input, file_mask_output_temp, sample_raster_file_output)

    print(cyan + "processingMacroSample() : " + bold + green + "Fin du traitement" + endC)


    return
