import os, sys, glob
from libs.Lib_display import bold,red,green,yellow,cyan,endC
from libs.Lib_file import removeFile

###########################################################################################################################################
# FONCTION concatenateData()                                                                                                              #
###########################################################################################################################################
def concatenateData(images_input_dic, stack_image_output, img_ref, shp_zone, code = "float", save_intermediate_result = False, overwrite = True, debug = 0):
    """
    Rôle : ajout de neocanaux (mnh, textures et/ou indices) deja calcules ou non a l'image d'origine

    Paramètres :
        images_input_dic : dictionnaire des fichiers a stacker ensemble
        stack_image_output : le nom de l'empilement image de sortie
        img_ref : image de référence du projet
        shp_zone : emprise de la zone d'étude
        code : encodage du fichier de sortie, par défaut : float
        save_intermediate_result : fichiers de sorties intermediaires non nettoyees, par defaut = False
        overwrite : si vrai, ecrase les fichiers existants, par défaut True
        debug : niveau de debug pour l'affichage des commentaires

    Sortie :
        le nom complet de l'image de sortie
        Elements generes : une image concatenee rangee

    """

    if debug >= 3:
        print(bold + green + "concatenateData() : fonction de concaténtaion des images en une unique image à plusieurs bandes." + endC)
        print(cyan + "concatenateData() : " + endC + "images_input_dic : " + str(images_input_dic) + endC)
        print(cyan + "concatenateData() : " + endC + "stack_image_output : " + str(stack_image_output) + endC)
        print(cyan + "concatenateData() : " + endC + "code : " + str(code) + endC)
        print(cyan + "concatenateData() : " + endC + "save_intermediate_result : " + str(save_intermediate_result) + endC)
        print(cyan + "concatenateData() : " + endC + "overwrite : " + str(overwrite) + endC)
        print(cyan + "concatenateData() : " + endC + "debug : " + str(debug) + endC)

    images_input_list = []
    for el in images_input_dic.values():
        images_input_list.append(el)

    check = os.path.isfile(stack_image_output)
    if check and not overwrite: # Si l'empilement existe deja et que overwrite n'est pas activé
        print(bold + yellow + "Le fichier " + stack_image_output + " existe déjà et ne sera pas recalculé." + endC)
    else:
        if check:
            try:
                removeFile(stack_image_output)
            except Exception:
                pass # si le fichier n'existe pas, il ne peut pas être supprimé : cette étape est ignorée

        print(bold + green + "Recherche de bandes à ajouter..." + endC)

        elements_to_stack_list_str = ""    # Initialisation de la liste des fichiers autres a empiler

        # Gestion des fichiers a ajouter
        for image_name_other in images_input_list:

            if debug >= 3:
                print(cyan + "concatenateChannels() : " + endC + "image_name_other : " + str(image_name_other) + endC)

            # Verification de l'existence de image_name_other
            if not os.path.isfile(image_name_other) :
                # Si image_name_other n'existe pas, message d'erreur
                raise NameError(cyan + "concatenateChannels() : " + bold + red + "Le fichier %s n'existe pas !"%(image_name_other) + endC)

            # Ajouter l'indice a la liste des indices a empiler
            elements_to_stack_list_str += " " + image_name_other

            if debug >= 1:
                print(cyan + "concatenateChannels() : " + endC + "elements_to_stack_list_str : " + str(elements_to_stack_list_str) + endC)

        # Stack de l'image avec les images additionnelles
        if len(elements_to_stack_list_str) > 0:

            # Assemble la liste d'image en une liste globale de fichiers d'entree
            print(bold + green + "concatenateChannels() : Assemblage des bandes %s ... "%(elements_to_stack_list_str) + endC)

            command = "otbcli_ConcatenateImages -progress true -il %s -out %s %s" %(elements_to_stack_list_str,stack_image_output,code)
            if debug >= 3:
                print(command)
            exitCode = os.system(command)
            if exitCode != 0:
                #Si otbcli n'a pas fonctionné -> cela peut forcément venir de la donnée d'élévation apportée qu'il faut superimpose avec le reste des néochannels
                repertory = os.path.dirname(images_input_dic["ndvi"])
                file_name_mnh = os.path.splitext(os.path.basename(images_input_dic["mnh"]))[0]
                extension = os.path.splitext(images_input_dic["mnh"])[1]
                file_tmp_mnh = repertory + os.sep + file_name_mnh + "_tmp_SI" + extension
                file_mnh = repertory + os.sep + file_name_mnh + extension

                cmd_superimpose = 'otbcli_Superimpose -inr %s -inm %s -out %s' %(img_ref, images_input_dic["mnh"], file_tmp_mnh)
                os.system(cmd_superimpose)
                cutImageByVector(shp_zone ,file_tmp_mnh, file_mnh)
                images_input_dic["mnh"] = file_mnh

                elements_to_stack_list_str = ""
                for el in images_input_dic.values():
                    elements_to_stack_list_str += " " + el

                #Relance de la concaténation
                command = "otbcli_ConcatenateImages -progress true -il %s -out %s %s" %(elements_to_stack_list_str,stack_image_output,code)
                if debug >= 3:
                    print(command)
                exitCode = os.system(command)
                if exitCode != 0:
                    print(command)
                    raise NameError(cyan + "concatenateChannels() : " + bold + red + "An error occured during otbcli_ConcatenateImages command. See error message above." + endC)
            print(bold + green + "concatenateChannels() : Channels successfully assembled" + endC)

    return images_input_dic
