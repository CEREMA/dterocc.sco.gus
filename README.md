# dterocc.sco.gus

# Projet SCO Green Urban Sat (GUS)

Le projet GUS a permis le développement d'une méthodologie de cartographie détaillée de la végétation urbaine, sur le territoire test de la Métropole du Grand Nancy, réplicable nationalement voire mondialement car indépendante des bases de données locales.

La méthode utilise les images et données de hauteur (MNH) issues de données satellitaires à très haute résolution spatiale (THRS) Pléiades, mais est également adaptable aux données Pléiades Neo et aux futures missions THRS (CO3D notamment).

Cette cartographie a pour objectif final de servir de support pour l'évaluation de 5 services écosystémiques : régulation du climat local, régulation de la qualité de l'air, bénéfices socio-culturels, continuités écologiques et irrigation.
Cette partie constitue le coeur du projet Des Hommes et Des Arbres (DHDA) sur la Métropole du Grand Nancy (MGN).

Les partenaires du projet GUS sont le Cerema (pôle satellitaire de la Dter Occitanie et équipe de recherche TEAM de la Dter Est), TerraNIS, le LIVE, la MGN, et le CNES via le SCO.
Les partenaires remercient le SCO pour le cofinancement du projet.

## Principe

Ce dépôt GITHUB présente l'ensemble des scripts python permettant de générer automatiquement la cartographie détaillée de la végétation, à partir de deux images d'entrée Pléiades (une image d'été stéréoscopique et une image d'hiver monoscopique).

La cartographie GUS se présente sous la forme d'une couche vectorielle décrivant la végétation en formes végétales (fv) selon 9 classes :
- Strate arborée :
    - Arbre Isolé
    - Alignement d’Arbres
    - Boisement Arboré
- Strate arbustive :
    - Arbuste Isolé
    - Alignement d’Arbustes
    - Boisement Arbustif
- Strate herbacée :
    - Prairie
    - Culture
    - Pelouse

La table attributaire se présente sous la forme suivante :

| nom de l'attribut | fid | strate | fv | paysage | surface | h_moy | h_med | h_et | h_min | h_max | perc_persistant | perc_caduc | perc_conifere | perc_feuillu | type_sol |
| :------ | :------ | :------ | :------ | :------ |:------ | :------ |:------ | :------ |:------ | :------ | :------ | :------ |:------ | :------ | :------ |
| Description | Identifiant unique de la fv | Strate verticale | Classe fv | Paysage | Surface de la fv (m²) | Hauteur moyenne (m) | Hauteur médiane (m) | Écart-type de hauteur (m) | Hauteur minimale (q10) (m) | Hauteur maximale (q90) (m) | Pourcentage de couvert persistant (%) | Pourcentage de couvert caduc (%) | Pourcentage de conifères (%) | Pourcentage de feuillus (%) | Type de sol |
| Valeurs | int | A:Arboré Au:Arbustif H:Herbacé | AI:Arbre Isolé AA:Alignement d’Arbres BOA:Boisement Arboré AuI:Arbuste Isolé AAu:Alignement d’Arbustes BOAu:Boisement Arbustif PR:Prairie C:Culture PE:Pelouse | 1:urbain 2:bord de voirie 3:bord de surfaces en eau 4:agricole et forestier 5:autres milieux naturels | float | float | float | float | float | float | float (0-100) | float (0-100) | float (0-100) | float (0-100) | Surface végétalisée / non végétalisée |

Les indices de confiance (non remplis à l'heure actuelle) :
| idc_surface | idc_h | idc_prescadu | idc_coniffeuil | idc_typesol |
| :------ | :------ |:------ | :------ |:------ |
| Indice de confiance de la surface | Indice de confiance de la hauteur | Indice de confiance du pourcentage de caduc et persistant | Indice de confiance du pourcentage de feuillu et conifère | Indice de confiance sur le type de sol |

## Composition du dépôt

Le dépot est composé de deux dossiers et d'un fichier `main.py` à la racine :

| Dossier / fichier | Description                |
| :-------- | :------------------------- |
| libs | Contient les librairies utilisées dans les applications |
| app | Contient les fichiers python d'applications appelées dans le main |
|`main.py` | Script principal du lancement de l'application |

## Configuration des librairies et du code

Nous garantissons un bon fonctionnement de l'application sous la configuration Ubuntu 22. 04. 2 LTS.

### Librairies python

Version Python 3. 10. 12

Principales librairies : os, sys, glob, copy, time, subprocess, math, psycopg2, numpy

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
3. le lancement des scripts en ouvrant un terminal à la racine du dossier (où se situe le fichier main) avec la commande : `python main.py config.json`

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
| *GUSRasterAssembly()* | Assemblage des imagettes Pléiades |  Oui |
| *mnhCreation()* | Création d'un Modèle Numérique de Hauteur à partir d'un MNS et d'un MNT | Oui |
| *channelComputation()* | Calcul des images d'indices radiométriques dérivés de l'image Pléaides de référence| Oui |
| *concatenateData()* | Concaténation des données une seule couche raster | Non |

Certaines fonctions sont optionnelles lorsqu'il y a possibilité que l'opérateur apporte lui-même la donnée produite par cette fonction.

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

NB : particularités pour le calcul de l'image "paysages" qui n'est pas directement réalisé dans le fichier `main.py` mais dans la fonction *app/IndicatorsComputation/landscapeIndicator()*.

En ne renseignant pas l'image des paysages détectés dans la balise `indicators_computation > landscape > landscape_data`. Le script va se lancer dans la production de cette même donnée via la fonction *landscapeDetection()* qui aura la possbilité d'utiliser deux méthodes en fonction des informations renseignés au niveau des balises :
1. `data_entry > entry_options > lcz_information > lcz_data`  : si la donnée LCZ est renseignée, la donnée paysages sera dérivée de cette donnée LCZ.
2. `data_entry > entry_options > img_ocs` : la donnée paysages sera dérivée de la donnée satellitaire.

## Fichier de configuration

Nous mettons à disposition un fichier de configuration `config.json` qui permet de renseigner les éléments nécessaires au bon déroulement des étapes de cartographie. Les grandes lignes sont présentées dans le tableau suivant, mais vous trouverez un fichier `config_defs.json` définissant chacun des termes à renseigner dans le dépôt.

| Balise | Définition |
| :-------- | :------------------------- |
| *repertory* | Répertoire de création du dossier du projet |
| *save_intermediate_result* | Paramètre de sauvegarde des résultats intermédiaires |
| *display_comments* | Paramètre d'affichage des commentaires intermédiaires |
| *steps_to_run* | Gestion des étapes de traitements |
| *data_entry* | Données d'entrée initiales |
| *db_params* | Paramètres de création de la base de données PgSql |
| *vegetation_extraction* | Paramètres pour l'extraction de la végétation |
| *vertical_stratum_detection* | Paramètres pour la distinction des strates verticales de végétation |
| *vegetation_form_stratum_detection* | Paramètres de détection des formes végétales horizontales |
| *indicators_computation* | Paramètres de calcul des attributs descriptifs |

Via la balise `steps_to_run`, l'opérateur choisit quelles étapes il veut faire tourner. Attention, chaque étape nécessite l'apport de données qui sont à fournir dans les balises suivantes.

Nous prévoyons un minimum de données à fournir pour lancer le script, mais l'opérateur peut très bien apporter lui-même certaines données via la balise `data_entry > entry_options`. En gardant bien les mêmes formats que la donnée produite (nom des champs, extension, etc.)

Enfin, la balise `vertical_stratum_detection > height_or_texture` permet de prioriser la hauteur ou la texture dans la classification des segments en strates verticales. Deux possibilités :
- priorisation de la hauteur (valeur "height") : seule la donnée de hauteur est utilisée pour la première étape de la classification en strates verticales. NB : nous privilégions ce choix lorsque la donnée d'élévation est précise (ex : LiDAR).
- priorisation de la texture (valeur "texture") : la distinction entre végétation herbacée est ligneuse est effectuée sur la texture. La distinction entre arboré et arbustif est ensuite réalisé avec la donnée de hauteur. Ce choix est à privilégier lorsque la donnée d'élévation est peu précise (MNH satellitaire).

Une seconde étape de reclassification des strates est ensuite effectuée par voisinages pour corriger des principales erreurs.

### Attention
Attention, si vous ne voulez pas faire tourner toutes les étapes (`steps_to_run`), des informations sont à fournir si vous n'avez pas utilisé les scripts dédiés pour les produire :
- `steps_to_run > data_concatenation` = False -> fournir l'image concaténée via la balise `data_entry > entry_options > img_data_concatenation`
- `steps_to_run > vegetation_extraction` = False -> fournir le masque de végétation via la balise `data_entry > entry_options > mask_vegetation`
- `steps_to_run > vertical_stratum_detection` = False -> fournir le schema et la table de la donnée via la balise `vertical_stratum_detection > db_table`
- `steps_to_run > vegetation_form_stratum_detection` = False -> fournir le schema et la table de la donnée via la balise `vegetation_form_stratum_detection > db_table`

## Auteurs

Mathilde Segaud - Cerema Occitanie / DT / OSECC (pôle satellite)

Maëlle Klein - Cerema Occitanie / DT / OSECC (pôle satellite)

Gilles Fouvet - Cerema Occitanie / DT / OSECC (pôle satellite)

Benjamin Piccinini - Cerema Occitanie / DT / OSECC (pôle satellite)

## Contact

Emma Bousquet

Pôle satellitaire - Direction territoriale Occitanie

Complexe scientifique de Rangueil - 1 av. du colonel Roche 31400 TOULOUSE

emma.bousquet@cerema.fr



