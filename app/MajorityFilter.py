#!/usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.               #
#############################################################################

# Import des librairies python
import os,sys,glob

# Import des librairies de /libs
from libs.Lib_display import bold,red,green,cyan,endC
from libs.Lib_file import removeFile

# debug = 0 : affichage minimum de commentaires lors de l'execution du script
# debug = 1 : affichage intermédiaire de commentaires lors de l'execution du script
# debug = 2 : affichage supérieur de commentaires lors de l'execution du script etc...
# debug = 3

###########################################################################################################################################
# FONCTION filterImageMajority()                                                                                                          #
###########################################################################################################################################
def filterImageMajority(image_input, filtered_image_output, umc_pixels, ram_otb=0, save_results_intermediate=False, overwrite=True):
    """
    # ROLE:
    #    appliquer un filtre majoritaire à une image (classée ou non)
    #
    # ENTREES DE LA FONCTION :
    #    image_input : nom image à filtrer
    #    filtered_image_output : nom image filtrée de sortie
    #    umc_pixels : taille de l'umc en pixel cas traitement gdal_sieve
    #    ram_otb : memoire RAM disponible pour les applications OTB
    #    save_results_intermediate : fichiers de sorties intermediaires non nettoyées, par defaut = False
    #    overwrite : supprime ou non les fichiers existants ayant le meme nom, par defaut a True
    #
    # SORTIES DE LA FONCTION :
    #    aucun
    #   Eléments utilisés par la fonction : image à filtrer présentes dans un dossier spécifique
    #   Eléments générés par le script : image filtree sauvegardee dans le même dossier
    #
    """

    CODAGE = "uint16"

    if debug >= 2:
        print(bold + green + "filterImageMajority() : applique un filtre majoritaire à une image" + endC)
        print(cyan + "filterImageMajority() : " + endC + "image_input : " + str(image_input) + endC)
        print(cyan + "filterImageMajority() : " + endC + "filtered_image_output : " + str(filtered_image_output) + endC)
        print(cyan + "filterImageMajority() : " + endC + "umc_pixels : " + str(umc_pixels) + endC)
        print(cyan + "filterImageMajority() : " + endC + "ram_otb : " + str(ram_otb) + endC)
        print(cyan + "filterImageMajority() : " + endC + "save_results_intermediate : " + str(save_results_intermediate) + endC)
        print(cyan + "filterImageMajority() : " + endC + "overwrite : " + str(overwrite) + endC)

    # Vérification de l'existence d'une image filtrée
    check = os.path.isfile(filtered_image_output)

    # Si oui et si la vérification est activée, passage à l'étape suivante
    if check and not overwrite :
        print(cyan + "filterImageMajority() : " + bold + green +  "Image already filtered." + endC)
    # Si non ou si la vérification est désactivée, application du filtre
    else:
        # Tentative de suppresion du fichier
        try:
            removeFile(filtered_image_output)
        except Exception:
            # Ignore l'exception levée si le fichier n'existe pas (et ne peut donc pas être supprimé)
            pass

        # Par gdal_sieve
        command = "gdal_sieve.py -st %d -8 %s %s" %(umc_pixels,image_input,filtered_image_output)

        if debug >= 3:
            print(command)
        exitCode = os.system(command)
        if exitCode != 0:
            raise NameError(cyan + "filterImageMajority() : " + bold + red + "An error occured during otbcli_ClassificationMapRegularization command. See error message above.")
        print('\n' + cyan + "filterImageMajority() : " + bold + green + "Filter applied!" + endC)



    # Supression des .geom dans le dossier
    directory_output = os.path.dirname(filtered_image_output)
    for to_delete in glob.glob(directory_output + os.sep + "*.geom"):
        removeFile(to_delete)

    return


