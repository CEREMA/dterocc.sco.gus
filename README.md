# dterocc.sco.gus

# Projet Green Urban Sat (GUS)

Ce projet a pour volonté de produire une méthodologie de cartographie détaillée de la végétation en milieu urbain répondant à plusieurs objectifs :
- réplicable mondialement
- fonction de support pour l'évaluation de services écosystémiques
- indépendant de bases de données locales ou nationales



## Principe

Ce dépôt GITHUB présente l'ensemble des scripts python produits afin de générer automatiquement une cartographie détaillée de la végétation, à partir d'une image Pléaides THRS donnée.

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


## Diagramme de classe
![Diagramme de structure](https://github.com/CEREMA/dterocc.sco.gus/blob/main/README.md)

## Utilisation du main

### Données à fournir

### Lancement des étapes



