# dterocc.sco.gus

# Projet Green Urban Sat (GUS)
=

Ce projet a pour volonté de produire une méthodologie de cartographie détaillée de la végétation en milieu urbain répondant à plusieurs objectifs :
- réplicable mondialement
- fonction de support pour l'évaluation de services écosystémiques
- indépendant de bases de données locales ou nationales
- servir de base à l'évaluation de 5 services écosystémiques : sevrice de régulation du climat local, service de régulation de la qualité de l'air, service de support socio- culturels, service de continuité écologique et service d'irrigation.


## Principe
=

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
=

Le dépot est composé de deux dossiers et d'un fichier `main.py` à la racine :

| Dossier / fichier | Description                |
| :-------- | :------------------------- |
| libs | Répertorie toutes les librairies utilisées dans les applications |
| app | Répertorie tous les fichiers `.py` d'applications appelées dans le main |
|`main.py` | Script principal du lancement de l'application |

## Configuration des librairies et du code
=

Nous garantissons un bon fonctionnement de l'application sous la configuration Ubuntu 22. 04. 2 LTS.

### Librairies python
-

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
-

| Logiciel | Version                |
| :-------- | :------------------------- |
| OTB | 8. 0. 1 |
| GDAL | 3. 4. 1 |
| GRASS GIS | 7. 8. 7 |
| SAGA | 7. 3. 0 |
| PostgreSQL | 14. 9 |


## Téléchargement et lancement 
=

Le lancement du code se décompose en trois étapes :
1. le téléchargement du repertoire complet
2. le remplissage du fichier `config.xml`
3. le lancement des scripts en ouvrant une invite de commande à la racine du dossier (là où se situe le fichier main) et en lançant la commande : `python main.py`

NB : il faudra bien vérifier dans le fichier `main.py` que toutes les étapes sont bien décommentées

## Utilisation du main
=

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

#### Détection de formes végétales horizontales

| Fonction | Usage | Optionnel |
| :------- | :----| :---------- |
| *openConnection()* | Nécessaire pour la connection au schéma de la db dans laquelle les traitements spatiaux vont êtres réalisés | Non |
| *cartographyVegetation()* | Cartographie des formes végétales horizontales de la végétation  | Non | 

#### Calcul des attributs descriptifs

| Fonction | Usage | Optionnel |
| :------- | :----| :---------- |
| *openConnection()* | Nécessaire pour la connection au schéma de la db dans laquelle les traitements spatiaux vont êtres réalisés | Non |  
| *createAndImplementFeatures()* | Création et calcul des attributs descriptifs des formes végétales produites précedemment | Non |


## Fichier de configuration
=

Nous mettons à disposition un fichier de configuration `config.xml` qui permet de renseigner les éléments nécessaires au bon déroulement des étapes de cartographie. Les grandes lignes sont présentées dans le tableau suivant, mais vous trouverez un fichier `config_ini.xml` dans le dépôt.
NB : 

| Balise | Définition |
| :-------- | :------------------------- |
| *repertory* | Répertoire de création du dossier du projet |
| *data_entry* | Données d'entrée initiales |
| *db_params* | Paramètres de création de la base de données PgSql |
| *vegetation_extraction* | Paramètres pour l'extraction de la végétation |
| *vertical_stratum_detection* | Paramètres pour la distinction des strates verticales de végétation |
| *vegetation_form_stratum_detection* | Paramètres de détection des formes végétales horizontales |
| *indicators_computation* | Paramètres de calcul des attributs descriptifs |

Nous prévoyons un minimum de données à fournir pour lancer le script, mais l'opérateur peut très bien apporter lui-même certaines données :

| Balise optionnelle | Définition |
| :------------------- | :--------- |
| *dir_img_assembly* | Repertoire des imagettes à assembler |
| *img_dhm* | image MNH |
| *img_ocs* | image de classification en classes |
| *data_classes* | 5 couches vecteurs dans lesquelles on va sélectionner les échantillons d'apprentissage |
| *samples_creation* | informations pour créer les échantillons d'apprentissage automatiquement (dans le cas où la balise data_classes n'est pas renseignée) |

## Auteur
=

Cerema Toulouse / DT / OSECC (pôle satellite)

## Diagramme de classe
=
![Diagramme de structure](https://github.com/CEREMA/dterocc.sco.gus/blob/main/README.md)