#!/usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.               #
#############################################################################

from libs.Lib_raster import  deletePixelsSuperpositionMasks, mergeListRaster, updateReferenceProjection
import os

###########################################################################################################################################
# FONCTION cleanCoverClasses()                                                                                                            #
###########################################################################################################################################
def cleanCoverClasses(img_ref, mask_samples_macro_input_list, image_samples_merged_output):
    """
    Rôle : nettoie les pixels d'apprentissage de classes différentes se recouvrants

    Paramètre :
        img_ref : image Pléiades de référence
        mask_samples_macro_input_list : liste des images des échantillons d'apprentissage
        image_samples_merged_output : fichier raster de sortie contenant les échantillons en une seule bande

    """
    # Creation des fichiers temporaires de sortie si ils ne sont pas spécifier

    length_mask = len(mask_samples_macro_input_list)
    images_mask_cleaned_list = []
    images_out_list = []
    temporary_files_list = []
    image_input_list = []

    extension_raster =  os.path.splitext(image_samples_merged_output)[1]

    # Le repertoire intermédiaire est situé dans le dossier où se sauvegarde le résultat
    repertory_base_output = os.path.dirname(image_samples_merged_output)
    filename = os.path.splitext(os.path.basename(image_samples_merged_output))[0]

    for macroclass_id in range(length_mask):

        repertory_output = repertory_base_output + os.sep + os.path.splitext(os.path.basename(mask_samples_macro_input_list[macroclass_id]))[0]
        if not os.path.isdir(repertory_output):
            os.makedirs(repertory_output)
        samples_image_input = mask_samples_macro_input_list[macroclass_id]
        filename = os.path.splitext(os.path.basename(samples_image_input))[0]
        image_mask_cleaned =  repertory_output + os.sep + filename + "mask_clean" + extension_raster
        image_out = repertory_output + os.sep + filename + "cleaned" + extension_raster
        if os.path.isfile(samples_image_input) :
            image_input_list.append(samples_image_input)
            images_mask_cleaned_list.append(image_mask_cleaned)
            images_out_list.append(image_out)

    # Suppression des pixels possédant la même valeur binaire sur plusieurs images
    print(image_input_list)
    print(images_mask_cleaned_list)
    if length_mask > 1:
        deletePixelsSuperpositionMasks(image_input_list, images_mask_cleaned_list)
    else:
        images_mask_cleaned_list = image_input_list

    # Attribution des valeurs de label aux masques de chaque classe pour les pixels valant 1
    length = len(images_mask_cleaned_list)
    for img in range(len(images_mask_cleaned_list)):
        command = "otbcli_BandMath -il %s -out %s -exp '(im1b1==1)?%s:0'" %(images_mask_cleaned_list[img],images_out_list[img], str(img+1))
        exitCode = os.system(command)
        if exitCode != 0:
            print(command)

    mergeListRaster(images_out_list, image_samples_merged_output, "uint16")
    updateReferenceProjection(img_ref, image_samples_merged_output)

    return
