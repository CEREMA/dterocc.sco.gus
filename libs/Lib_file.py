# -*- coding: utf-8 -*-
#!/usr/bin/python

#############################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.               #
#############################################################################

#############################################################################
#                                                                           #
# FONCTIONS DE MODIFICATION DE FICHIERS OU DE REPERTOIRES                   #
#                                                                           #
#############################################################################
"""
 Ce module défini des fonctions de manipulation, modification de fichiers et de répertoires.
"""

import os, sys, shutil, copy, time
from osgeo import ogr
from libs.Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC

debug = 1

#########################################################################
# FONCTION cleanTempData()                                              #
#########################################################################
def cleanTempData(rep_temp):
    """
    #   Role : Suppression de l'arborescence d'un repertoire temporaire
    #   Paramètres en entrée :
    #              rep_temp : répertoire temporaire à nettoyer
    """

    if os.path.exists(rep_temp):
        shutil.rmtree(rep_temp)
        time.sleep(1)  # Ajout d'un temps de latence d'une seconde pour eviter des bugs dus à la mise à jour des dossiers
    if not os.path.isdir(rep_temp):
        os.makedirs(rep_temp)
    return

#########################################################################
# FONCTION removeDir()                                                  #
#########################################################################
def removeDir(del_filename):
    """
    #   Role : Suppression d'un repertoire et sous repertoire (vide!)
    #   Paramètres :
    #      filename : Nom du repertoire à supprimer
    """

    # Supression du repertoire
    if os.path.exists(del_filename):
        os.removedirs(del_filename)
    return

#########################################################################
# FONCTION deleteDir()                                                  #
#########################################################################
def deleteDir(del_filename):
    """
    #   Role : Suppression d'un repertoire me plein et recursif
    #   Paramètres :
    #      filename : Nom du repertoire à supprimer
    """

    # Supression du repertoire
    if os.path.exists(del_filename):
        shutil.rmtree(del_filename)
    return

#########################################################################
# FONCTION renameFile()                                                 #
#########################################################################
def renameFile(old_filename, new_filename):
    """
    #   Role : Renommage de fichiers
    #   Paramètres :
    #      old_filename : Ancien nom
    #      new_filename : Nouveau nom
    """

    # Renomage du fichier
    if os.path.exists(old_filename):
        os.rename(old_filename, new_filename)
    else :
        print(bold + yellow + "Impossible de renomer le fichier : " + old_filename + " . Fichier inexistant!" + endC)
    return

#########################################################################
# FONCTION removeFile()                                                 #
#########################################################################
def removeFile(del_filename):
    """
    #   Role : Suppression de fichier
    #   Paramètres :
    #      filename : Nom du fichier à supprimer
    """

    # Supression du fichier
    if os.path.exists(del_filename):
        os.remove(del_filename)
    return

#########################################################################
# FONCTION removeVectorFile()                                           #
#########################################################################
def removeVectorFile(del_vector_name, format_vector='ESRI Shapefile'):
    """
    #   Role : Suppression de fichier vecteur
    #   Paramètres :
    #      del_vector_name : Nom du fichier vecteur à supprimer
    #      format_vector : format du fichier vecteur (par defaut : format shapefile)
    """

    # Récupération du driver
    driver = ogr.GetDriverByName(format_vector)
    # Supression du vecteur
    if os.path.exists(del_vector_name):
        driver.DeleteDataSource(del_vector_name)
    return

#########################################################################
# FONCTION copyVectorFile()                                             #
#########################################################################
def copyVectorFile(input_vector_name, output_vector_name, format_vector='ESRI Shapefile'):
    """
    #   Role : Copy de fichier vecteur
    #   Paramètres :
    #      input_vector_name : Nom du fichier vecteur à copier
    #      output_vector_name : Nom du fichier vecteur de sortie recopié
    #      format_vector : format du fichier vecteur (par defaut : format shapefile)
    """

    # Récupération du driver
    driver = ogr.GetDriverByName(format_vector)
    # Copie du vecteur
    if os.path.exists(input_vector_name):
        data_source = driver.Open(input_vector_name, 0)  # en lecture
        if os.path.exists(output_vector_name):
            driver.DeleteDataSource(output_vector_name)
        driver.CopyDataSource(data_source,output_vector_name)
        data_source.Destroy()
    else :
        print(bold + yellow + "Impossible de copier le fichier : " + input_vector_name + " . Fichier inexistant!" + endC)
    return

#########################################################################
# FONCTION renameVectorFile()                                           #
#########################################################################
def renameVectorFile(input_vector_name, output_vector_name):
    """
    #   Role : Renomage de fichier vecteur
    #   Paramètres :
    #      input_vector_name : Nom du fichier vecteur à copier
    #      output_vector_name : Nom du fichier vecteur de sortie renomé
    """

    # Renomage du fichier
    if os.path.exists(input_vector_name):
        base_name_input = os.path.splitext(input_vector_name)[0]
        base_name_output = os.path.splitext(output_vector_name)[0]
        os.rename(base_name_input + ".dbf", base_name_output + ".dbf")
        os.rename(base_name_input + ".prj", base_name_output + ".prj")
        os.rename(base_name_input + ".shx", base_name_output + ".shx")
        os.rename(base_name_input + ".shp", base_name_output + ".shp")
    else :
        print(bold + yellow + "Impossible de renomer le fichier : " + input_vector_name + " . Fichier inexistant!" + endC)
    return

#########################################################################
# FONCTION moveVectorFile()                                             #
#########################################################################
def moveVectorFile(input_vector_name, output_vector_name):
    """
    #   Role : Deplacementy de fichier vecteur
    #   Paramètres :
    #      input_vector_name : Nom du fichier vecteur à déplacer
    #      output_vector_name : Nom du fichier vecteur de sortie déplacé
    """

    # Renomage du fichier
    if os.path.exists(input_vector_name):
        base_name_input = os.path.splitext(input_vector_name)[0]
        base_name_output = os.path.splitext(output_vector_name)[0]
        shutil.move(base_name_input + ".dbf", base_name_output + ".dbf")
        shutil.move(base_name_input + ".prj", base_name_output + ".prj")
        shutil.move(base_name_input + ".shx", base_name_output + ".shx")
        shutil.move(base_name_input + ".shp", base_name_output + ".shp")
    else :
        print(bold + yellow + "Impossible de déplacer le fichier : " + input_vector_name + " . Fichier inexistant!" + endC)
    return

#########################################################################
# FONCTION getSubRepRecursifList()                                      #
#########################################################################
def getSubRepRecursifList(input_rep):
    """
    #   Role : Fournir dla liste de tous les sous répertoire en recursif d'un repertoire d'entrée
    #   Paramètres :
    #      input_rep : Nom du répertoir d'entrée
    #   Return le liste de tout les sous répertoir
    """

    # Variable
    sub_rep = [] # Recevra les noms des sous-répertoires

    # Trouver le contenu du répertoire input_rep
    for repertory in os.listdir(input_rep):
        path_rep = os.path.join(input_rep, repertory)
        if os.path.isdir(path_rep):
            temp_sub_list = getSubRepRecursifList(path_rep)
            if not temp_sub_list == []:
                sub_rep.extend(temp_sub_list)
            sub_rep.append(path_rep)

    # La liste des sous répertoire en sortie
    return sub_rep
