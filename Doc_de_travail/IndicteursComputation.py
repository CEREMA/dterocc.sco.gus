
def createAllIndicatorsAttributs():
    """
    """

    # Connexion à la base de donnée et au schéma

    # Création des attributs concernés pour toutes les entités de la table

    return


def indicatorConiferousDeciduous():
    """
    Rôle : cette fonction permet de calculer le pourçentage de feuillus et de conifères sur les polygones en entrée
    """

    #Calcul du masque de conifères
    cmd_mask_conif = "otbli_BandMath -il %s -out %s -exp '(im1b4<1300)?1:0'"


    #Calcul du masque de feuillus
    cmd_mask_decid = "otbli_BandMath -il %s -out %s -exp '(im1b4>=1300)?1:0'"

    #Calcul du masque avec les trois tupes : conifères, feuillus et ombres
    cmd_

    #Statistiques zonales sur les polygones de formes végétales concernées : tous les segments appartennant à la strate arborée et arbustive

    #Calcul des statistiques zonales sur l'ensemble des polygones de végétation (même si on n'en a pas besoin pour la strate herbacé)



