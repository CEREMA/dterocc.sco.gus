from __future__ import print_function
import os,sys,glob,shutil,string, argparse
from Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC,displayIHM
from Lib_file import cleanTempData, deleteDir, removeFile


def vegetationMask(img_input, img_output, num_class = {"bati" : 1, "route" : 2, "sol nu" : 3, "eau" : 4, "vegetation" : 5}, overwrite = True):
    """
    Rôle : créé un masque de végétation à partir d'une image classifiée

    Paramètres :
        img_input : image classée en 5 classes
        img_output : image binaire : 1 pour la végétation et -1 pour non végétation
        num_class : dictionnaire reliant le nom de la classe au label, par défaut : {"bati" : 1, "route" : 2, "sol nu" : 3, "eau" : 4, "vegetation" : 5}
        overwrite : paramètre de ré-écriture, par défaut : True
    """

    #Verification de la non existence du fichier de sortie
    if overwrite == True and os.path.exists(img_output):
        os.remove(img_output)
    elif overwrite == False and os.path.exists(img_output):
        raise NameError(bold + red + "vegetationMask() : le fichier %s existe déjà" %(img_output)+ endC)

    exp = '"(im1b1==' + str(num_class["vegetation"]) + '?1:-1)"'
    print(exp)

    cmd_mask = "otbcli_BandMath -il %s -out %s -exp %s" %(img_input, img_output, exp)

    exitCode = os.system(cmd_mask)

    if exitCode != 0:
        print(cmd_mask)
        raise NameError(bold + red + "vegetationMask() : une erreur est apparue lors de la création du masque de végétation (commande otbcli_BandMath)" + endC)

    return

def segmentationImageVegetetation(img_original, img_input, file_output, param_minsize = 10, num_class = {"bati" : 1, "route" : 2, "sol nu" : 3, "eau" : 4, "vegetation" : 5}, format_vector='GPKG', save_intermediate_result = True, overwrite = True):
    """
    Rôle : segmente l'image en entrée à partir d'une fonction OTB_Segmentation MEANSHIFT

    Paramètre :
        img_original : image originale rvbpir
        img_input : image classée en 5 classes
        file_output : couche vecteur de sortie correspondant au résultat de segmentation
        param_minsize : paramètre de la segmentation : taille minimale des segments, par défaut : 10
        num_class : dictionnaire reliant le nom de la classe au label, par défaut : {"bati" : 1, "route" : 2, "sol nu" : 3, "eau" : 4, "vegetation" : 5}
        format_vector : format du fichier vecteur de sortie, par défaut : GPKG
        save_intermediate_result : paramètre de sauvegarde des fichiers intermédiaire, par défaut : True
        overwrite : paramètre de ré-écriture des fichiers

    Sortie :
        file_output : couche vecteur de sortie correspondant au résultat de segmentation
    """

    # Utilisation d'un fichier temporaire pour la couche masque
    repertory_output = os.path.dirname(file_output)
    file_name = os.path.splitext(os.path.basename(file_output))[0]
    extension = os.path.splitext(img_input)[1]

    file_out_suffix_mask_veg= "_mask_veg"
    mask_veg = repertory_output + os.sep + file_name + file_out_suffix_mask_veg + extension

    if os.path.exists(mask_veg):
        os.remove(mask_veg)

    #Création du masque de végétation
    vegetationMask(img_input, mask_veg, num_class)

    #Calcul de la segmentation Meanshift
    sgt_cmd = "otbcli_Segmentation -in %s -mode vector -mode.vector.out %s -mode.vector.inmask %s -filter meanshift  -filter.meanshift.minsize %s" %(img_original, file_output, mask_veg, param_minsize)

    exitCode = os.system(sgt_cmd)

    if exitCode != 0:
        print(sgt_cmd)
        raise NameError(bold + red + "segmentationVegetation() : une erreur est apparue lors de la segmentation de l'image (commande otbcli_Segmentation)." + endC)

    return
