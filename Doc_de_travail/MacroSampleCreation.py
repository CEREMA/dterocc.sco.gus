

def macroSampleCreation(image_input, input_vector_class, output_raster_class, emprisevector, erosionoption = True, format_vector='ESRI Shapefile'):
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
    cutoutVectors(emprisevector, [input_vector_class], [cut_file_tmp], overwrite=True, format_vector='ESRI Shapefile')

    # Erosion si option choisit
    if erosionoption :
        bufferVector(cut_file_tmp, erosion_file_tmp, -1, col_name_buf = "", fact_buf=1.0, quadsecs=10, format_vector='ESRI Shapefile')
    else :
        erosion_file_tmp = cut_file_tmp
    # Creation d'un masque binaire
    if raster_sample_output != "" and image_input != "" :
        repertory_output = os.path.dirname(output_raster_class)
        if not os.path.isdir(repertory_output):
            os.makedirs(repertory_output)
        rasterizeBinaryVector(erosion_file_tmp, image_input, output_raster_class, 1)

    return
