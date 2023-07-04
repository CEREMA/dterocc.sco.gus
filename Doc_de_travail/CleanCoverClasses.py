
from Lib_raster import *

def cleanCoverClasses(mask_samples_macro_input_list):
    """
    Rôle : nettoie les pixels d'apprentissage de classes différentes se recouvrants

    Paramètre :
        mask_samples_macro_input_list : liste des images des échantillons d'apprentissage

    """
    # Creation des fichiers temporaires de sortie si ils ne sont pas spécifier

    length_mask = len(mask_samples_macro_input_list)
    images_mask_cleaned_list = []
    temporary_files_list = []
    repertory_output_tmp_list = []

    for macroclass_id in range(length_mask):

        repertory_output = repertory_base_output + os.sep + str(mask_samples_macro_input_list[macroclass_id])
        if not os.path.isdir(repertory_output):
            os.makedirs(repertory_output)
        repertory_output_tmp_list.append(repertory_output)
        samples_image_input = mask_samples_macro_input_list[macroclass_id]
        filename = os.path.splitext(os.path.basename(samples_image_input))[0]
        image_mask_cleaned =  repertory_output + os.sep + filename + SUFFIX_MASK_CLEAN + extension_raster
        images_mask_cleaned_list.append(image_mask_cleaned)

    # Suppression des pixels possédant la même vleur binaire sur plusieurs images
    if length_mask > 1:
        image_name = os.path.splitext(os.path.basename(image_input))[0]
        deletePixelsSuperpositionMasks(mask_samples_macro_input_list, images_mask_cleaned_list)
    else:
        images_mask_cleaned_list = mask_samples_macro_input_list

    return images_mask_cleaned_list
