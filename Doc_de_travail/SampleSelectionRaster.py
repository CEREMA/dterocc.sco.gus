#! /usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.                                                                               #
#############################################################################################################################################

#############################################################################################################################################
#                                                                                                                                           #
# SCRIPT FAIT UNE SELECTIONNE DES POINTS D'ECHANTILLONS D'APPRENTISSAGE DIRECTEMENT DANS LES FICHIERS MASK MACRO D'APPRENTISSAGE            #
#                                                                                                                                           #
#############################################################################################################################################
"""
Nom de l'objet : selectSamples.py
Description :
-------------
Objectif : Selectionner des points d'echantillons d'apprentissage par tirage aléatoire, pour la classification dans les fichiers masques macro d'apprentissage
ceux-ci sont d'abord fusionnés.
Rq : utilisation des OTB Applications :  otbcli_BandMath, otbcli_SampleExtraction

Date de creation : 16/03/2017
----------
Histoire :
----------
Origine : Nouveau
16/03/2017 : Création
-----------------------------------------------------------------------------------------------------
Modifications :

------------------------------------------------------
A Reflechir/A faire :

"""

# Import des bibliothèques python
from __future__ import print_function
import os, sys, glob, argparse, copy, random, math, threading
from osgeo import gdal, ogr
from Lib_raster import identifyPixelValues, countPixelsOfValue, getRawDataImage, getGeometryImage, getEmpriseImage, getPixelWidthXYImage, getProjectionImage
from Lib_vector import createPointsFromCoordList, getAttributeValues, getAttributeNameList, createEmpriseShapeReduced, fusionVectors
from Lib_text import writeTextFile, appendTextFileCR
from Lib_file import removeVectorFile, removeFile
from Lib_operator import switch, case
from Lib_math import average, standardDeviation
from Lib_log import timeLine
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
debug = 5

###########################################################################################################################################
# STRUCTURE StructInfoMicoClass                                                                                                           #
###########################################################################################################################################
class StructInfoMicoClass:
    """
    # Structure contenant contenant les informations nombre de points, valeur du label macroclass et liste de points associé à une macro classe
    """
    def __init__(self):
        self.label_class = 0
        self.nb_points = 0
        self.info_points_list = None
        self.sample_points_list = None

###########################################################################################################################################
# FONCTION selectSamples                                                                                                                  #
###########################################################################################################################################
def selectSamples(image_input_list, sample_image_input, vector_output, table_statistics_output, sampler_strategy, select_ratio_floor, ratio_per_class_dico, name_column, no_data_value, rand_seed=0, ram_otb=0, epsg=2154, format_vector='ESRI Shapefile', extension_vector=".shp", save_results_intermediate=False, overwrite=True) :
    """
    # ROLE:
    #     fonction de selection de points d'échantillons dans un fichier raster apres fusion de toute les fichiers macro, de facon aléatoire
    #
    # ENTREES DE LA FONCTION :
    #    image_input_list : liste d'image d'entrée stacké au format .tif
    #    sample_image_input : image d'echantillons de macro classes d'entrée .tif
    #    vector_output : fichier vecteur résultat de la vectorisation de la classification
    #    table_statistics_output : fichier contenant le resultat des statistiques sur les valeurs des points par macro classes .csv
    #    sampler_strategy : mode de strategie de selection
    #    select_ratio_floor : ratio de taux de selection pour toutes les macro classes avec une valeur plancher
    #    ratio_per_class_dico : dictionaire de ratio  de taux de selection pour chaque macro classe
    #    name_column : nom de la colonne du fichier shape contenant l'information de classification
    #    no_data_value : Option : Value pixel of no data
    #    rand_seed : graine pour la partie randon sample
    #    ram_otb : memoire RAM disponible pour les applications OTB
    #    epsg : Optionnel : par défaut 2154
    #    format_vector : format du fichier vecteur. Optionnel, par default : 'ESRI Shapefile'
    #    extension_vector : extension du fichier vecteur de sortie, par defaut = '.shp'
    #    save_results_intermediate : sauvegarde les fichier de sorties intermediaires, par defaut = False
    #    overwrite : supprime ou non les fichiers existants ayant le meme nom
    #
    # SORTIES DE LA FONCTION :
    #    Le fichier vecteur de points d'échantions
    #    Eléments modifiés auccun
    #
    """

    # Mise à jour du Log
    starting_event = "selectSamples() : Select points in raster mask macro input starting : "

    if debug >= 3:
        print(cyan + "selectSamples() : " + endC + "image_input_list : " + str(image_input_list) + endC)
        print(cyan + "selectSamples() : " + endC + "sample_image_input : " + str(sample_image_input) + endC)
        print(cyan + "selectSamples() : " + endC + "vector_output : " + str(vector_output) + endC)
        print(cyan + "selectSamples() : " + endC + "table_statistics_output : " + str(table_statistics_output) + endC)
        print(cyan + "selectSamples() : " + endC + "sampler_strategy : " + str(sampler_strategy) + endC)
        print(cyan + "selectSamples() : " + endC + "select_ratio_floor : " + str(select_ratio_floor) + endC)
        print(cyan + "selectSamples() : " + endC + "ratio_per_class_dico : " + str(ratio_per_class_dico) + endC)
        print(cyan + "selectSamples() : " + endC + "name_column : " + str(name_column) + endC)
        print(cyan + "selectSamples() : " + endC + "no_data_value : " + str(no_data_value) + endC)
        print(cyan + "selectSamples() : " + endC + "rand_seed : " + str(rand_seed) + endC)
        print(cyan + "selectSamples() : " + endC + "ram_otb : " + str(ram_otb) + endC)
        print(cyan + "selectSamples() : " + endC + "epsg : " + str(epsg) + endC)
        print(cyan + "selectSamples() : " + endC + "format_vector : " + str(format_vector) + endC)
        print(cyan + "selectSamples() : " + endC + "extension_vector : " + str(extension_vector) + endC)
        print(cyan + "selectSamples() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "selectSamples() : " + endC + "overwrite : " + str(overwrite) + endC)

    # Constantes
    EXT_XML = ".xml"

    SUFFIX_SAMPLE = "_sample"
    SUFFIX_STATISTICS = "_statistics"
    SUFFIX_POINTS = "_points"
    SUFFIX_VALUE = "_value"

    BAND_NAME = "band_"
    COLUMN_CLASS = "class"
    COLUMN_ORIGINFID = "originfid"

    NB_POINTS = "nb_points"
    AVERAGE = "average"
    STANDARD_DEVIATION = "st_dev"

    print(cyan + "selectSamples() : " + bold + green + "DEBUT DE LA SELECTION DE POINTS" + endC)

    # Definition variables et chemins
    repertory_output = os.path.dirname(vector_output)
    filename = os.path.splitext(os.path.basename(vector_output))[0]
    sample_points_output = repertory_output + os.sep + filename +  SUFFIX_SAMPLE + extension_vector
    file_statistic_points = repertory_output + os.sep + filename + SUFFIX_STATISTICS + SUFFIX_POINTS + EXT_XML

    if debug >= 3:
        print(cyan + "selectSamples() : " + endC + "file_statistic_points : " + str(file_statistic_points) + endC)

    # 0. EXISTENCE DU FICHIER DE SORTIE
    #----------------------------------

    # Si le fichier vecteur points de sortie existe deja et que overwrite n'est pas activé
    check = os.path.isfile(vector_output)
    if check and not overwrite:
        print(bold + yellow + "Samples points already done for file %s and will not be calculated again." %(vector_output) + endC)
    else:   # Si non ou si la vérification est désactivée : creation du fichier d'échantillons points

        # Suppression de l'éventuel fichier existant
        if check:
            try:
                removeVectorFile(vector_output)
            except Exception:
                pass # Si le fichier ne peut pas être supprimé, on suppose qu'il n'existe pas et on passe à la suite
        if os.path.isfile(table_statistics_output) :
            try:
                removeFile(table_statistics_output)
            except Exception:
                pass # Si le fichier ne peut pas être supprimé, on suppose qu'il n'existe pas et on passe à la suite


        # 1. STATISTIQUE SUR L'IMAGE DES ECHANTILLONS RASTEUR
        #----------------------------------------------------

        if debug >= 3:
            print(cyan + "selectSamples() : " + bold + green + "Start statistique sur l'image des echantillons rasteur..." + endC)

        id_macro_list = identifyPixelValues(sample_image_input)

        if 0 in id_macro_list :
            id_macro_list.remove(0)

        min_macro_class_nb_points = -1
        min_macro_class_label = 0
        infoStructPointSource_dico = {}

        writeTextFile(file_statistic_points, '<?xml version="1.0" ?>\n')
        appendTextFileCR(file_statistic_points, '<GeneralStatistics>')
        appendTextFileCR(file_statistic_points, '    <Statistic name="pointsPerClassRaw">')

        if debug >= 2:
            print("Nombre de points par macro classe :" + endC)
        for id_macro in id_macro_list :
            nb_pixels = countPixelsOfValue(sample_image_input, id_macro)

            if debug >= 2:
                print("MacroClass : " + str(id_macro) + ", nb_points = " + str(nb_pixels))
            appendTextFileCR(file_statistic_points, '        <StatisticPoints class="%d" value="%d" />' %(id_macro, nb_pixels))

            if min_macro_class_nb_points == -1 or min_macro_class_nb_points > nb_pixels :
                min_macro_class_nb_points = nb_pixels
                min_macro_class_label = id_macro

            infoStructPointSource_dico[id_macro] = StructInfoMicoClass()
            infoStructPointSource_dico[id_macro].label_class = id_macro
            infoStructPointSource_dico[id_macro].nb_points = nb_pixels
            infoStructPointSource_dico[id_macro].info_points_list = []
            infoStructPointSource_dico[id_macro].sample_points_list = []
            del nb_pixels

        if debug >= 2:
            print("MacroClass min points find : " + str(min_macro_class_label) + ", nb_points = " + str(min_macro_class_nb_points))

        appendTextFileCR(file_statistic_points, '    </Statistic>')

        pending_event = cyan + "selectSamples() : " + bold + green + "End statistique sur l'image des echantillons rasteur. " + endC
        if debug >= 3:
            print(pending_event)

        # 2. CHARGEMENT DE L'IMAGE DES ECHANTILLONS
        #------------------------------------------

        if debug >= 3:
            print(cyan + "selectSamples() : " + bold + green + "Start chargement de l'image des echantillons..." + endC)

        # Information image
        cols, rows, bands = getGeometryImage(sample_image_input)
        xmin, xmax, ymin, ymax = getEmpriseImage(sample_image_input)
        pixel_width, pixel_height = getPixelWidthXYImage(sample_image_input)
        projection_input, _ = getProjectionImage(sample_image_input)
        if projection_input == None or projection_input == 0 :
            projection_input = epsg
        else :
            projection_input = int(projection_input)

        pixel_width = abs(pixel_width)
        pixel_height = abs(pixel_height)

        # Lecture des données
        raw_data = getRawDataImage(sample_image_input)

        if debug >= 3:
            print("projection = " + str(projection_input))
            print("cols = " + str(cols))
            print("rows = " + str(rows))

        # Creation d'une structure dico contenent tous les points différents de zéro
        progress = 0
        pass_prog = False
        for y_row in range(rows) :
            for x_col in range(cols) :
                value_class = raw_data[y_row][x_col]
                if value_class != 0 :
                    infoStructPointSource_dico[value_class].info_points_list.append(x_col + (y_row * cols))

            # Barre de progression
            if debug >= 4:
                if  ((float(y_row) / rows) * 100.0 > progress) and not pass_prog :
                    progress += 1
                    pass_prog = True
                    print("Progression => " + str(progress) + "%")
                if ((float(y_row) / rows) * 100.0  > progress + 1) :
                    pass_prog = False

        del raw_data

        pending_event = cyan + "selectSamples() : " + bold + green + "End chargement de l'image des echantillons. " + endC
        if debug >= 3:
            print(pending_event)

        # 3. SELECTION DES POINTS D'ECHANTILLON
        #--------------------------------------

        if debug >= 3:
            print(cyan + "selectSamples() : " + bold + green + "Start selection des points d'echantillon..." + endC)

        appendTextFileCR(file_statistic_points, '    <Statistic name="pointsPerClassSelect">')

        # Rendre deterministe la fonction aléatoire de random.sample
        if rand_seed > 0:
            random.seed( rand_seed )

        # Pour toute les macro classes
        # Selon la stategie de selection
        nb_points_ratio = 0
        if case('percent'):
            for key in ratio_per_class_dico:
                select_ratio_class = ratio_per_class_dico[key]
                nb_points_ratio = int(infoStructPointSource_dico[id_macro].nb_points * select_ratio_class / 100)
                infoStructPointSource_dico[id_macro].sample_points_list = random.sample(range(infoStructPointSource_dico[id_macro].nb_points), nb_points_ratio)
                print(infoStructPointSource_dico[id_macro].sample_points_list)
                break


            if debug >= 2:
                print("macroClass = " + str(id_macro) + ", nb_points_ratio " + str(nb_points_ratio))
            appendTextFileCR(file_statistic_points, '        <StatisticPoints class="%d" value="%d" />' %(id_macro, nb_points_ratio))

        appendTextFileCR(file_statistic_points, '    </Statistic>')
        appendTextFileCR(file_statistic_points, '</GeneralStatistics>')

        pending_event = cyan + "selectSamples() : " + bold + green + "End selection des points d'echantillon. " + endC
        if debug >= 3:
            print(pending_event)

        # 4. PREPARATION DES POINTS D'ECHANTILLON
        #----------------------------------------

        if debug >= 3:
            print(cyan + "selectSamples() : " + bold + green + "Start preparation des points d'echantillon..." + endC)

        # Création du dico de points
        points_random_value_dico = {}
        index_dico_point = 0
        for macro_class in infoStructPointSource_dico :
            macro_class_struct = infoStructPointSource_dico[macro_class]
            label_class = macro_class_struct.label_class
            point_attr_dico = {name_column:int(label_class), COLUMN_CLASS:int(label_class), COLUMN_ORIGINFID:0}

            for id_point in macro_class_struct.sample_points_list:

                # Recuperer les valeurs des coordonnees des points
                coor_x = float(xmin + (int(macro_class_struct.info_points_list[id_point] % cols) * pixel_width)) + (pixel_width / 2.0)
                coor_y = float(ymax - (int(macro_class_struct.info_points_list[id_point] / cols) * pixel_height)) - (pixel_height / 2.0)
                points_random_value_dico[index_dico_point] = [[coor_x, coor_y], point_attr_dico]
                del coor_x
                del coor_y
                index_dico_point += 1
            del point_attr_dico
        del infoStructPointSource_dico

        pending_event = cyan + "selectSamples() : " + bold + green + "End preparation des points d'echantillon. " + endC
        if debug >=3:
            print(pending_event)

        # 5. CREATION DU FICHIER SHAPE DE POINTS D'ECHANTILLON
        #-----------------------------------------------------

        if debug >= 3:
            print(cyan + "selectSamples() : " + bold + green + "Start creation du fichier shape de points d'echantillon..." + endC)

        # Définir les attibuts du fichier résultat
        attribute_dico = {name_column:ogr.OFTInteger, COLUMN_CLASS:ogr.OFTInteger, COLUMN_ORIGINFID:ogr.OFTInteger}

        # Creation du fichier shape
        createPointsFromCoordList(attribute_dico, points_random_value_dico, sample_points_output, projection_input, format_vector)
        del attribute_dico
        del points_random_value_dico

        pending_event = cyan + "selectSamples() : " + bold + green + "End creation du fichier shape de points d'echantillon. " + endC
        if debug >=3:
            print(pending_event)

        # 6.  EXTRACTION DES POINTS D'ECHANTILLONS
        #-----------------------------------------

        if debug >= 3:
            print(cyan + "selectSamples() : " + bold + green + "Start extraction des points d'echantillon dans l'image..." + endC)

        # Cas ou l'on a une seule image
        if len(image_input_list) == 1:
            # Extract sample
            image_input = image_input_list[0]
            command = "otbcli_SampleExtraction -in %s -vec %s -outfield prefix -outfield.prefix.name %s -out %s -field %s" %(image_input, sample_points_output, BAND_NAME, vector_output, name_column)
            if ram_otb > 0:
                command += " -ram %d" %(ram_otb)
            if debug >= 3:
                print(command)
            exitCode = os.system(command)
            if exitCode != 0:
                raise NameError(cyan + "selectSamples() : " + bold + red + "An error occured during otbcli_SampleExtraction command. See error message above." + endC)

        # Cas de plusieurs imagettes
        else :

            # Le repertoire de sortie
            repertory_output = os.path.dirname(vector_output)
            # Initialisation de la liste pour le multi-threading et la liste de l'ensemble des echantions locaux
            thread_list = []
            vector_local_output_list = []

            # Obtenir l'emprise des images d'entrées pour redecouper le vecteur d'echantillon d'apprentissage pour chaque image
            for image_input in image_input_list :
                # Definition des fichiers sur emprise local
                file_name = os.path.splitext(os.path.basename(image_input))[0]
                emprise_local_sample = repertory_output + os.sep + file_name + SUFFIX_SAMPLE + extension_vector
                vector_sample_local_output = repertory_output + os.sep + file_name + SUFFIX_VALUE + extension_vector
                vector_local_output_list.append(vector_sample_local_output)

                # Gestion sans thread...
                SampleLocalExtraction(image_input, sample_points_output, emprise_local_sample, vector_sample_local_output, name_column, BAND_NAME, ram_otb, format_vector, extension_vector, save_results_intermediate)

                # Gestion du multi threading
                thread = threading.Thread(target=SampleLocalExtraction, args=(image_input, sample_points_output, emprise_local_sample, vector_sample_local_output, name_column, BAND_NAME, ram_otb, format_vector, extension_vector, save_results_intermediate))
                thread.start()
                thread_list.append(thread)

            # Extraction des echantions points des images
            try:
                for thread in thread_list:
                    thread.join()
            except:
                print(cyan + "selectSamples() : " + bold + red + "Erreur lors de l'éextaction des valeurs d'echantion : impossible de demarrer le thread" + endC, file=sys.stderr)

            # Fusion des multi vecteurs de points contenant les valeurs des bandes de l'image
            fusionVectors(vector_local_output_list, vector_output, format_vector)

            # Clean des vecteurs point sample local file
            for vector_sample_local_output in vector_local_output_list :
                removeVectorFile(vector_sample_local_output)

        if debug >= 3:
            print(cyan + "selectSamples() : " + bold + green + "End extraction des points d'echantillon dans l'image." + endC)

        # 7. CALCUL DES STATISTIQUES SUR LES VALEURS DES POINTS D'ECHANTILLONS SELECTIONNEES
        #-----------------------------------------------------------------------------------

        if debug >= 3:
            print(cyan + "selectSamples() : " + bold + green + "Start calcul des statistiques sur les valeurs des points d'echantillons selectionnees..." + endC)

        # Si le calcul des statistiques est demandé presence du fichier stat
        if table_statistics_output != "":

            # On récupère la liste de données
            pending_event = cyan + "selectSamples() : " + bold + green + "Encours calcul des statistiques part1... " + endC
            if debug >=4:
                print(pending_event)

            attribute_name_dico = {}
            name_field_value_list = []
            names_attribut_list = getAttributeNameList(vector_output, format_vector)
            if debug >=4:
                print("names_attribut_list = " + str(names_attribut_list))

            attribute_name_dico[name_column] = ogr.OFTInteger
            for name_attribut in names_attribut_list :
                if BAND_NAME in name_attribut :
                    attribute_name_dico[name_attribut] = ogr.OFTReal
                    name_field_value_list.append(name_attribut)

            name_field_value_list.sort()

            res_values_dico = getAttributeValues(vector_output, None, None, attribute_name_dico, format_vector)
            del attribute_name_dico

            # Trie des données par identifiant macro classes
            pending_event = cyan + "selectSamples() : " + bold + green + "Encours calcul des statistiques part2... " + endC
            if debug >=4:
                print(pending_event)

            data_value_by_macro_class_dico = {}
            stat_by_macro_class_dico = {}

            # Initilisation du dico complexe
            for id_macro in id_macro_list :
                data_value_by_macro_class_dico[id_macro] = {}
                stat_by_macro_class_dico[id_macro] = {}
                for name_field_value in res_values_dico :
                    if name_field_value != name_column :
                        data_value_by_macro_class_dico[id_macro][name_field_value] = []
                        stat_by_macro_class_dico[id_macro][name_field_value] = {}
                        stat_by_macro_class_dico[id_macro][name_field_value][AVERAGE] = 0.0
                        stat_by_macro_class_dico[id_macro][name_field_value][STANDARD_DEVIATION] = 0.0

            # Trie des valeurs
            pending_event = cyan + "selectSamples() : " + bold + green + "Encours calcul des statistiques part3... " + endC
            if debug >=4:
                print(pending_event)

            for index in range(len(res_values_dico[name_column])) :
                id_macro = res_values_dico[name_column][index]
                for name_field_value in name_field_value_list :
                    data_value_by_macro_class_dico[id_macro][name_field_value].append(res_values_dico[name_field_value][index])
            del res_values_dico

            # Calcul des statistiques
            pending_event = cyan + "selectSamples() : " + bold + green + "Encours calcul des statistiques part4... " + endC
            if debug >=4:
                print(pending_event)

            for id_macro in id_macro_list :
                for name_field_value in name_field_value_list :
                    try :
                        stat_by_macro_class_dico[id_macro][name_field_value][AVERAGE] = average(data_value_by_macro_class_dico[id_macro][name_field_value])
                    except:
                        stat_by_macro_class_dico[id_macro][name_field_value][AVERAGE] = 0
                    try :
                        stat_by_macro_class_dico[id_macro][name_field_value][STANDARD_DEVIATION] = standardDeviation(data_value_by_macro_class_dico[id_macro][name_field_value])
                    except:
                        stat_by_macro_class_dico[id_macro][name_field_value][STANDARD_DEVIATION] = 0
                    try :
                        stat_by_macro_class_dico[id_macro][name_field_value][NB_POINTS] = len(data_value_by_macro_class_dico[id_macro][name_field_value])
                    except:
                        stat_by_macro_class_dico[id_macro][name_field_value][NB_POINTS] = 0

            del data_value_by_macro_class_dico

            # Creation du fichier statistique .csv
            pending_event = cyan + "selectSamples() : " + bold + green + "Encours calcul des statistiques part5... " + endC
            if debug >= 4:
                print(pending_event)

            text_csv = " macro classes ; Champs couche image ; Nombre de points  ; Moyenne ; Ecart type \n"
            writeTextFile(table_statistics_output, text_csv)
            for id_macro in id_macro_list :
                for name_field_value in name_field_value_list :
                    # Ecriture du fichier
                    text_csv = " %d " %(id_macro)
                    text_csv += " ; %s" %(name_field_value)
                    text_csv += " ; %d" %(stat_by_macro_class_dico[id_macro][name_field_value][NB_POINTS])
                    text_csv += " ; %f" %(stat_by_macro_class_dico[id_macro][name_field_value][AVERAGE])
                    text_csv += " ; %f" %(stat_by_macro_class_dico[id_macro][name_field_value][STANDARD_DEVIATION])
                    appendTextFileCR(table_statistics_output, text_csv)
            del name_field_value_list

        else :
            if debug >=3:
                print(cyan + "selectSamples() : " + bold + green + "Pas de calcul des statistiques sur les valeurs des points demander!!!." + endC)

        del id_macro_list

        pending_event = cyan + "selectSamples() : " + bold + green + "End calcul des statistiques sur les valeurs des points d'echantillons selectionnees. " + endC
        if debug >= 3:
            print(pending_event)


    # 8. SUPRESSION DES FICHIERS INTERMEDIAIRES
    #------------------------------------------

    if not save_results_intermediate:

        if os.path.isfile(sample_points_output) :
            removeVectorFile(sample_points_output)

    print(cyan + "selectSamples() : " + bold + green + "FIN DE LA SELECTION DE POINTS" + endC)

    # Mise à jour du Log
    ending_event = "selectSamples() : Select points in raster mask macro input ending : "

    return

###########################################################################################################################################
# FONCTION SampleLocalExtraction()                                                                                                        #
###########################################################################################################################################
def SampleLocalExtraction(image_input, sample_points, emprise_local_sample, vector_sample_local_output, name_column, band_name, ram_otb=0, format_vector='ESRI Shapefile', extension_vector=".shp", save_results_intermediate=False):
    """
    # ROLE:
    #     Extracteur des valeurs de toutes les bandes pour les points d'echantillons pour d'une image
    #
    # ENTREES DE LA FONCTION :
    #     image_input : imagette d'entrée
    #     sample_points : vecteur points d'echantillons global
    #     emprise_local_sample : zone vecteur d'echantion local sur l'emprise de l'imagette
    #     vector_sample_local_output : vecteur points d'echantillons sur la zone de sortie
    #     name_column : nom de la colonne id
    #     band_name : prefixe nom des colonnes
    #     ram_otb : memoire RAM disponible pour les applications OTB
    #     format_vector : format du fichier vecteur. Optionnel, par default : 'ESRI Shapefile'
    #     extension_vector : extension du fichier vecteur de sortie, par defaut = '.shp'
    #     save_results_intermediate : sauvegarde les fichier de sorties intermediaires, par defaut = False
    # SORTIES DE LA FONCTION :
    #     Vecteur polygonisé
    #
    """

    # Creation de la zone local
    empr_xmin, empr_xmax, empr_ymin, empr_ymax = getEmpriseImage(image_input)
    createEmpriseShapeReduced(sample_points, empr_xmin, empr_ymin, empr_xmax, empr_ymax, emprise_local_sample, format_vector)

    # Extract sample
    command = "otbcli_SampleExtraction -in %s -vec %s -outfield prefix -outfield.prefix.name %s -out %s -field %s" %(image_input, emprise_local_sample, band_name, vector_sample_local_output, name_column)
    if ram_otb > 0:
        command += " -ram %d" %(ram_otb)
    print(command)
    exitCode = os.system(command)
    if exitCode != 0:
        raise NameError(cyan + "SampleLocalExtraction() : " + bold + red + "An error occured during otbcli_SampleExtraction command. See error message above." + endC)

    # Clean temp file
    if not save_results_intermediate :
        removeVectorFile(emprise_local_sample)

    return
