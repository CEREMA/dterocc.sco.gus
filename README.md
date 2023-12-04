# dterocc.sco.gus

# Projet Green Urban Sat (GUS)

Ce projet a pour volonté de produire une méthodologie de cartographie détaillée de la végétation en milieu urbain répondant à plusieurs objectifs :
- réplicable mondialement
- fonction de support pour l'évaluation de services écosystémiques
- indépendant de bases de données locales ou nationales
- servir de base à l'évaluation de 5 services écosystémiques : sevrice de régulation du climat local, service de régulation de la qualité de l'air, service de support socio- culturels, service de continuité écologique et service d'irrigation.


## Principe

Ce dépôt GITHUB présente l'ensemble des scripts python produits afin de générer automatiquement une cartographie détaillée de la végétation, à partir d'une image Pléaides THRS donnée.

Cette cartographie se présente sous la forme d'une couche vecteur décrivant la végétation avec une table attributaire se présentant sous la forme suivante :

| fid | strate | fv | paysage | surface | h_moy | h_med | h_et | h_min | h_max | perc_persistant | perc_caduc | perc_conifere | perc_feuillu | 
| :------ | :------ | :------ | :------ |:------ | :------ |:------ | :------ |:------ | :------ | :------ | :------ |:------ | :------ |
| Identifiant unique de la forme végétale (fv) | Strate verticale à laquelle la fv appartient | Label de la fv | Paysage dans lequel s'inscrit la fv | Surface de la fv | Hauteur moyenne | Hauteur médiane | Écart-type de hauteur | Hauteur minimale | Hauteur maximale | Pourcentage de la fv composée de couvert persistant | Pourcentage de la fv composée de couvert caduc | Pourcentage de la fv composée de conifères | Pourcentage de la fv composée de feuillus |

Les indices de confiance :
| idc_surface | idc_h | idc_prescadu | idc_coniffeuil | idc_typesol | 
| :------ | :------ |:------ | :------ |:------ | 
| Indice de confiance de la surface | Indice de confiance de la hauteur | Indice de confiance du pourcentage de caduc et persistant | Indice de confiance du pourcentage de caduc et persistant | Indice de confiance sur la valeur de type de sol renseignée |

## Composition du dépôt

Le dépot est composé de deux dossiers et d'un fichier `main.py` à la racine :

| Dossier / fichier | Description                |
| :-------- | :------------------------- |
| libs | Répertorie toutes les librairies utilisées dans les applications |
| app | Répertorie tous les fichiers `.py` d'applications appelées dans le main |
|`main.py` | Script principal du lancement de l'application |

## Configuration des librairies et du code

Nous garantissons un bon fonctionnement de l'application sous la configuration Ubuntu 22. 04. 2 LTS.

### Librairies python

Version Python 3. 10. 12

| Principales librairie |
| :-------- |
| os |
| sys |
| glob | 
| copy | 
| time | 
| subprocess | 
| math |
| psycopg2 |
| numpy |

### Logiciels annexes

| Logiciel | Version                |
| :-------- | :------------------------- |
| OTB | 8. 0. 1 |
| GDAL | 3. 4. 1 |
| GRASS GIS | 7. 8. 7 |
| SAGA | 7. 3. 0 |
| PostgreSQL | 14. 9 |


## Téléchargement et lancement 

Le lancement du code se décompose en trois étapes :
1. le téléchargement du repertoire complet
2. le remplissage du fichier `config.json`
3. le lancement des scripts en ouvrant une invite de commande à la racine du dossier (là où se situe le fichier main) et en lançant la commande : `python main.py`

NB : il faudra bien vérifier dans le fichier `main.py` que toutes les étapes sont bien décommentées

## Utilisation du main

Le main est divisé en deux parties : 
    - les imports
    - le lancement des scripts (__name__ == '__main__')

### Les imports

Il y a deux types d'imports :
- les imports de fonctions Python ou de librairies annexes
- les imports de fonctions provenants des `.py` de `/app`

### Le lancement des scripts

Cette partie est divisée en quatre sous-parties : 
- le renseignement des données d'entrée
- la création et l'implémentation des variables à partir des données fournies 
- la création de l'environnement : dossier du projet, chemins de sauvegarde, base de données pgsql/postgis
- le lancement des étapes de production de la cartographie

#### Pré-traitements 

| Fonction | Usage | Optionnel |
| :------- | :----| :---------|
| *assemblyImages()* | Assemblage des imagettes Pléiades |  Oui |
| *mnhCreation()* | Création d'un Modèle Numérique de Hauteur à partir d'un MNS et d'un MNT | Oui |
| *neochannelComputation()* | Calcul des images d'indices radiométriques dérivés de l'image Pléaides de référence| Oui |
| *concatenateData()* | Concaténation des données une seule couche raster | Non |

Certaines fonctions sont optionnelles lorsqu'il y a possibilité que l'opérateur apporte lui-même la donnée produite par cette fonction.

#### Extraction de la végétation

| Fonction | Usage | Optionnel |
| :------- | :---- | :--------- |
| *createAllSamples()* | Création des couches d'échantillons d'apprentissage | Oui |
| *prepareAllSamples()* | Découpe des couches d'échantillons d'apprentissage selon l'emprise de la zone d'étude et une potentielle érosion | Non |
| *cleanAllSamples()* | Nettoyage des échantillons d'apprentissage à partir de filtres sur les indices radiométriques | Non |
| *cleanCoverClasses()* | Nettoyage des échantillons d'apprentissage pour éviter les recouvrements de classes | Non |
| *selectSamples()* | Sélection de pourcentages d'échantillons d'apprentissage parmi ceux créés et nettoyés | Non |
| *classifySupervised()* | Classification supervisée à partir de l'algorithme Random Forest | Non |
| *filterImageMajority()* | Homogénéisation de l'image de classification | Non |


#### Distinction des strates verticales de la végétation

| Fonction | Usage | Optionnel |
| :------- | :----| :--------|
| *openConnection()* | Nécessaire pour la connection au schéma de la db dans laquelle les traitements spatiaux vont êtres réalisés | Non |
| *segmentationImageVegetation()* | Création de la couche vecteur des segments de végétation à partir de l'algorithme de segmentation Meanshift | Non |
| *classificationVerticalStratum()* | Classification des segments végétation en strates verticales (arboré, arbustif et herbacé) | Non |
| *closeConnection()* | Nécessaire pour fermer la connection au schéma de la db dans laquelle les traitements spatiaux vont êtres réalisés | Non |

#### Détection de formes végétales horizontales

| Fonction | Usage | Optionnel |
| :------- | :----| :---------- |
| *openConnection()* | Nécessaire pour la connection au schéma de la db dans laquelle les traitements spatiaux vont êtres réalisés | Non |
| *cartographyVegetation()* | Cartographie des formes végétales horizontales de la végétation  | Non | 
| *closeConnection()* | Nécessaire pour fermer la connection au schéma de la db dans laquelle les traitements spatiaux vont êtres réalisés | Non |

#### Calcul des attributs descriptifs

| Fonction | Usage | Optionnel |
| :------- | :----| :---------- |
| *openConnection()* | Nécessaire pour la connection au schéma de la db dans laquelle les traitements spatiaux vont êtres réalisés | Non |  
| *createAndImplementFeatures()* | Création et calcul des attributs descriptifs des formes végétales produites précedemment | Non |
| *closeConnection()* | Nécessaire pour fermer la connection au schéma de la db dans laquelle les traitements spatiaux vont êtres réalisés | Non |


## Fichier de configuration

Nous mettons à disposition un fichier de configuration `config.json` qui permet de renseigner les éléments nécessaires au bon déroulement des étapes de cartographie. Les grandes lignes sont présentées dans le tableau suivant, mais vous trouverez un fichier `config_defs.json` définissant chacun des termes à renseigner dans le dépôt.
 
| Balise | Définition |
| :-------- | :------------------------- |
| *repertory* | Répertoire de création du dossier du projet |
| *steps_to_run* | Gestion des étapes de traitements |   
| *data_entry* | Données d'entrée initiales |
| *db_params* | Paramètres de création de la base de données PgSql |
| *vegetation_extraction* | Paramètres pour l'extraction de la végétation |
| *vertical_stratum_detection* | Paramètres pour la distinction des strates verticales de végétation |
| *vegetation_form_stratum_detection* | Paramètres de détection des formes végétales horizontales |
| *indicators_computation* | Paramètres de calcul des attributs descriptifs |

Via la balise `steps_to_run`, l'opérateur choisit quelles étapes il veut faire tourner. Attention, chaque étape nécessite l'apport de données qui sont à fournir dans les balises suivantes.

Nous prévoyons un minimum de données à fournir pour lancer le script, mais l'opérateur peut très bien apporter lui-même certaines données via la balise `data_entry > entry_options`. En gardant bien les mêmes formats que la donnée produite (nom des champs, extension, etc.)

De plus, il existe une particularité pour le renseignement des informations en balise `vegetation_extraction > samples_cleaning` : si les indices radiométriques servants à nettoyer et filtrer les échantillons d'apprentissage ont été produits dans une étape précédente au script, nous retrouverons l'information `source` via l'arborescence du dossier de projet créé (à condition de bien respecter les noms des indices attribués dans le code : ndvi, msavi, ndwi, hue, mnh, etc.). Cette balise permet à l'opérateur d'ajouter une autre donnée de filtrage qui n'est pas produite via les scripts.

Enfin, il existe la balise `vertical_stratum_detection > height_or_texture` qui permet à l'opérateur de prioriser la hauteur ou la texture dans la classification des segments en strates verticales. Deux possibilités s'offrent donc : 
- priorisation de la hauteur (valeur "height") où seule la donnée de hauteur est utilisée pour la première étape de la classification en strates verticales. NB : nous privilégions ce choix lorsque la donnée d'élévation est précise (ex : LiDAR).
- priorisation de la texture (valeur "texture") où une sueil appliqué sur la texture assure la distinction végétation herbacée vs végétation arborée et arbustive. La distinction de l'arboré et de l'arbustif se réalisant classiquement avec la donnée de hauteur. NB : nous privilégions ce choix lorsque la donnée d'élévation est peu précise (ex : MNH dérivé de la donnée satellitaire).

Ensuite, une seconde étape de classification de la strate arbustive permet de nettoyer cette strate qui a tendance à la surestimation.

### Attention
Attention, si vous ne voulez pas faire tourner toutes les étapes (`steps_to_run`), des informations sont à fournir si vous n'avez pas utilisé les scripts dédiés pour les produire : 
- `steps_to_run > data_concatenation` = False -> fournir l'image concaténée via la balise `data_entry > entry_options > img_data_concatenation`
- `steps_to_run > vegetation_extraction` = False -> fournir l'image classifiée via la balise `data_entry > entry_options > img_ocs`
- `steps_to_run > vertical_stratum_detection` = False -> fournir le schema et le table de la donnée via la balise `vertical_stratum_detection > db_table`
- `steps_to_run > vegetation_form_stratum_detection` = False -> fournir le schema et le table de la donnée via la balise `vegetation_form_stratum_detection > db_table`

## Dossier configuration chaîne iota2

Pour la distinction des formes végétales "prairie" et "culture" au sein de la strate herbacée, nous nécessitons l'apport d'une image classifiée "prairie/culture" sur la zone d'étude. L'opérateur fournit cette donnée via la variable `vegetation_form_stratum_detection > herbaceous > img_grasscrops`.

Nous mettons à disposition une méthode de production de cette classification à partir de la chaîne iota2 développée par le Cesbio et disponible en gratuitement via ce [lien](https://framagit.org/iota2-project/iota2).

La méthode se déroule en quatre grandes étapes :
1. Télécharger 12 images Sentinel-2 (une image par mois) sur la zone d'étude. 

NB : en France, nous disposons d'images Sentinel-2 L3 correspondant aux synthèses mensuelles. 

2. Préparer les données d'entrée :
- orthorectifier et ré-échantillonner les images les unes par rapport aux autres
- calculer les néocanaux dérivés des bandes de chaque image : NDVI,NDWI et BI
- concaténer l'ensemble des données en une unique image multi-bande 
- préparer les données d'apprentissage en allant chercher dans le RPG les classes correspondant aux "prairies" et "cultures". 
- nettoyer les échantillons d'apprentissage afin d'éviter un recouvrement de classes

3. Remplir le fichier de configuration de la chaîne iota2 dont un exemple est disponible dans le dossier `config_iota\GusConfigIota2.cfg` 

4. Lancer la chaîne

Attention : nous préconisons la vérification du référentiel de projection de l'image classifiée finale. Si elle n'est pas dans le même référentiel que le projet, il faudra reprojeter l'image via, par exemple, l'application d'un gdalwarp. 

## Auteur

Cerema Toulouse / DT / OSECC (pôle satellite)

## Diagramme de classe

![Diagramme de structure](https://github.com/CEREMA/dterocc.sco.gus/blob/main/README.md)