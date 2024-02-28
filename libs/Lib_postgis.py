#!/usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################
# Copyright (©) CEREMA/DTerOCC/DT/OSECC  All rights reserved.               #
#############################################################################

#############################################################################
#                                                                           #
#     FONCTIONS EN LIEN AVEC DES REQUETES SQL PostgreSQL / PostGIS          #
#                                                                           #
#############################################################################
"""
 Ce module défini des fonctions en lien avec des requetes SQL vers l'outil PostgreSQL / PostGIS.
 Notes diverses :
 Pour utiliser certains modules (notamment createDatabase() / dropDatabase() / importVectorByOgr2ogr() / exportVectorByOgr2ogr() / importShape() / exportShape() / importRaster()),
 il est préférable d'être déconnecté de la base de données (conflit d'accès).
"""

#Import des librairies Python
import os, sys, csv, psycopg2, re, platform
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

#Import des librairies de /apps
from libs.Lib_display import bold,black,red,green,yellow,blue,magenta,cyan,endC
from libs.Lib_text import readTextFile, appendTextFileCR

debug = 2

########################################################################
# FONCTION openConnection()                                            #
########################################################################
def openConnection(database_name, user_name='postgres', password='postgres', ip_host='localhost', num_port='5432', schema_name='public'):
    """
    # Rôle : se connecter à une base de données
    # Paramètres en entrée :
    #   database_name : nom de la base de données à laquelle se connecter
    #   user_name : nom d'utilisateur du serveur PostgreSQL (par défaut : 'postgres')
    #   password : mot de passe du serveur PostgreSQL (par défaut : 'postgres')
    #   ip_host : adresse IP du serveur PostgreSQL (par défaut : 'localhost')
    #   num_port : numéro de port du serveur PostgreSQL (par défaut : '5432')
    #   schema_name : nom du schema à utiliser (par défaut : 'public')
    # Paramètre de retour :
    #   les paramètres de la connexion
    """

    connection = None
    try:
        if schema_name == '' :
            connection = psycopg2.connect(dbname=database_name, user=user_name, password=password, host=ip_host, port=num_port, connect_timeout=60)
        else :
            option_shema = "--search_path=" + "{}".format(schema_name)
            connection = psycopg2.connect(dbname=database_name, user=user_name, password=password, host=ip_host, port=num_port, connect_timeout=60, options=option_shema)
    except psycopg2.DatabaseError as err:
        if connection:
            connection.rollback()
            connection.close()
        e = "OS error: {0}".format(err)
        print(bold + red + "openConnection() : Error %s - Impossible d'ouvrir la connexion à la base de données %s (machine hôte : %s, utilisateur : %s)" %(e, database_name, ip_host, user_name) + endC, file=sys.stderr)
        sys.exit(1)
    return connection

########################################################################
# FONCTION closeConnection()                                           #
########################################################################
def closeConnection(connection):
    """
    # Rôle : se déconnecter d'une une base de données
    # Paramètres en entrée :
    #   connection : laissez tel quel, récupère les informations de connexion à la base de données
    """

    if connection:
        connection.close()
    return

########################################################################
# FONCTION executeQuery()                                              #
########################################################################
def executeQuery(connection, query):
    """
    # Rôle : exécuter une requête SQL
    # Paramètres en entrée :
    #   connection : laissez tel quel, récupère les informations de connexion à la base de données
    #   query : requête SQL à exécuter dans la base de données (par exemple, 'SELECT * FROM table WHERE condition')
    """

    if debug >= 4:
        print("Exécution de la requête '%s'" % (query))
    connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = connection.cursor()
    cursor.execute(query)
    connection.commit()
    cursor.close()
    return

########################################################################
# FONCTION checkPassword()                                             #
########################################################################
def checkPassword(user_name='postgres', password='postgres', ip_host='localhost', num_port='5432'):
    """
    # Rôle : teste l'existence de la ligne contenant les identifiants de connexions dans fichier 'pgpass' (fonction qui utilise psql : importShape et importRaster)
    # Paramètres en entrée :
    #   user_name : nom d'utilisateur du serveur PostgreSQL (par défaut : 'postgres')
    #   password : mot de passe du serveur PostgreSQL (par défaut : 'postgres')
    #   ip_host : adresse IP du serveur PostgreSQL (par défaut : 'localhost')
    #   num_port : numéro de port du serveur PostgreSQL (par défaut : '5432')
    """

    osSystem = platform.system()
    if "Windows" in osSystem:
        file_pgpass = os.path.expanduser('~') + "\\AppData\\Roaming\\postgresql\\pgpass.conf"
    else:
        file_pgpass = os.path.expanduser('~') + "/.pgpass"

    line_pgpass = str(ip_host) + ":" + str(num_port) + ":*:" + str(user_name) + ":" + str(password)

    find = False
    if os.path.isfile(file_pgpass):
        text = readTextFile(file_pgpass)
        for line in text.split('\n'):
            if line_pgpass in line:
                find = True
                break

    if not find:
        appendTextFileCR(file_pgpass, line_pgpass)
        # Le fichier n'aime pas avoir plus de droit d'accès...
        os.chmod(file_pgpass, 0o600)

    return

########################################################################
# FONCTION createDatabase()                                            #
########################################################################
def createDatabase(database_name, user_name='postgres', password='postgres', ip_host='localhost', num_port='5432', schema_name=''):
    """
    # Rôle : créer une nouvelle base de données basée sur le template PostGIS
    # Paramètres en entrée :
    #   database_name : nom de la base de données à créer
    #   user_name : nom d'utilisateur du serveur PostgreSQL (par défaut : 'postgres')
    #   password : mot de passe du serveur PostgreSQL (par défaut : 'postgres')
    #   ip_host : adresse IP du serveur PostgreSQL (par défaut : 'localhost')
    #   num_port : numéro de port du serveur PostgreSQL (par défaut : '5432')
    #   schema_name : nom du schema à utiliser (par défaut : '')
    """

    connection = None
    connection = openConnection('postgres', user_name, password, ip_host, num_port, '')
    query = "CREATE DATABASE %s " % (database_name)
    query += "  WITH ENCODING = 'UTF8' "
    query += "  OWNER = postgres "
    query += "  TEMPLATE 'template_postgis' "
    query += "  CONNECTION LIMIT = -1;"
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM pg_database WHERE datname = '%s'" % (database_name))
    test = cursor.fetchall()
    if test == [] or test == None:
        try:
            connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = connection.cursor()
            cursor.execute(query)
            connection.commit()
            cursor.close()
            connection.close()
        except psycopg2.DatabaseError as err:
            if connection:
                connection.rollback()
                connection.close()
            e = "OS error: {0}".format(err)
            print(bold + red + "createDatabase() : Error %s - Impossible de créer la base de données %s" %(e, database_name) + endC, file=sys.stderr)
    return

########################################################################
# FONCTION dropDatabase()                                              #
########################################################################
def dropDatabase(database_name, user_name='postgres', password='postgres', ip_host='localhost', num_port='5432', schema_name=''):
    """
    # Rôle : supprimer une base de données existante
    # Paramètres en entrée :
    #   database_name : nom de la base de données à supprimer
    #   user_name : nom d'utilisateur du serveur PostgreSQL (par défaut : 'postgres')
    #   password : mot de passe du serveur PostgreSQL (par défaut : 'postgres')
    #   ip_host : adresse IP du serveur PostgreSQL (par défaut : 'localhost')
    #   num_port : numéro de port du serveur PostgreSQL (par défaut : '5432')
    #   schema_name : nom du schema à utiliser (par défaut : '')
    """

    connection = None
    connection = openConnection('postgres', user_name, password, ip_host, num_port, '')
    query = "DROP DATABASE IF EXISTS %s;" % (database_name)
    try:
        connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = connection.cursor()
        cursor.execute(query)
        connection.commit()
        cursor.close()
        connection.close()
    except psycopg2.DatabaseError as err:
        if connection:
            connection.rollback()
            connection.close()
        e = "OS error: {0}".format(err)
        print(bold + red + "dropDatabase() : Error %s - Impossible de supprimer la base de données %s" %(e, database_name) + endC, file=sys.stderr)
    return

########################################################################
# FONCTION createSchema()                                              #
########################################################################
def createSchema(connection, schema_name):
    """
    # Rôle : créer un nouveau schéma
    # Paramètres en entrée :
    #   connection : laissez tel quel, récupère les informations de connexion à la base de données
    #   schema_name : nom du schéma à créer
    """

    try:
        query = "CREATE SCHEMA IF NOT EXISTS %s AUTHORIZATION postgres;" % (schema_name)
        executeQuery(connection, query)
    except psycopg2.DatabaseError as err:
        if connection:
            connection.rollback()
        e = "OS error: {0}".format(err)
        print(bold + red + "createSchema() : Error %s - Impossible de créer le schéma %s" % (e, schema_name) + endC, file=sys.stderr)
        return -1
    return 0

########################################################################
# FONCTION dropSchema()                                                #
########################################################################
def dropSchema(connection, schema_name, cascade=True):
    """
    # Rôle : supprimer un schéma existant
    # Paramètres en entrée :
    #   connection : laissez tel quel, récupère les informations de connexion à la base de données
    #   schema_name : nom du schema à supprimer
    #   cascade : suppression des éléments du schéma
    """

    try:
        if cascade :
            query = "DROP SCHEMA IF EXISTS %s CASCADE;" % (schema_name)
        else:
            query = "DROP SCHEMA IF EXISTS %s;" % (schema_name)
        executeQuery(connection, query)
    except psycopg2.DatabaseError as err:
        if connection:
            connection.rollback()
        e = "OS error: {0}".format(err)
        print(bold + red + "dropSchema() : Error %s - Impossible de supprimer le schéma %s" % (e, schema_name) + endC, file=sys.stderr)
        return -1
    return 0

########################################################################
# FONCTION createTable()                                               #
########################################################################
def createTable(connection, table_name, columns_table_dico):
    """
    # Rôle : créer une nouvelle table
    # Paramètres en entrée :
    #   connection : laissez tel quel, récupère les informations de connexion à la base de données
    #   table_name : nom de la table à créer
    #   columns_table_dico : dictionnaire des noms de colonnes et du type de données associées (de la forme : [('column1', 'type1'), ('column2', 'type2'), ('column3', 'type3')])
    """

    try:
        dropTable(connection, table_name)
        cpt_column = 0
        query = "CREATE TABLE %s (" % (table_name)
        for column in columns_table_dico:
            name_column = column[0]
            type_column = column[1]
            query += name_column + " " + type_column
            if cpt_column == 0:
                query += " PRIMARY KEY, "
            else :
                query += ", "
            cpt_column += 1
        query = query[:-2]
        query += ");"
        executeQuery(connection, query)
    except psycopg2.DatabaseError as err:
        if connection:
            connection.rollback()
        e = "OS error: {0}".format(err)
        print(bold + red + "createTable() : Error %s - Impossible de créer la table %s" % (e, table_name) + endC, file=sys.stderr)
        return -1
    return 0

########################################################################
# FONCTION dropTable()                                                 #
########################################################################
def dropTable(connection, table_name):
    """
    # Rôle : supprimer une table existante
    # Paramètres en entrée :
    #   connection : laissez tel quel, récupère les informations de connexion à la base de données
    #   table_name : nom de la table à supprimer
    """

    try:
        query = "DROP TABLE IF EXISTS %s;" % (table_name)
        executeQuery(connection, query)
    except psycopg2.DatabaseError as err:
        if connection:
            connection.rollback()
        e = "OS error: {0}".format(err)
        print(bold + red + "dropTable() : Error %s - Impossible de supprimer la table %s" % (e, table_name) + endC, file=sys.stderr)
        return -1
    return 0

########################################################################
# FONCTION fillTable()                                                 #
########################################################################
def fillTable(connection, table_name, columns_table_dico, data):
    """
    # Rôle : remplir une table
    # Paramètres en entrée :
    #   connection : laissez tel quel, récupère les informations de connexion à la base de données
    #   table_name : nom de la table à remplir
    #   columns_table_dico : dictionnaire des noms de colonnes et du type de données associées (de la forme : [('Id', 'INT'), ('Name', 'TEXT'), ('Price', 'INT')])
    #   data : données à insérer dans la table (de la forme : [(1, 'Audi', 52642),(2, 'Mercedes', 57127),(3, 'Skoda', 9000),(4, 'Volvo', 29000),(5, 'Bentley', 350000),(6, 'Citroen', 21000),(7, 'Hummer', 41400),(8, 'Volkswagen', 21600)])
    """

    try:
        cursor = connection.cursor()
        query = "INSERT INTO %s (" % (table_name)
        for column in columns_table_dico:
            name_column = column[0]
            query += name_column + ", "
        query = query[:-2]
        query += ") VALUES ("
        for column in columns_table_dico:
            query += "%s, "
        query = query[:-2]
        query += ");"
        cursor.executemany(query, data)
        connection.commit()
    except psycopg2.DatabaseError as err:
        if connection:
            connection.rollback()
        e = "OS error: {0}".format(err)
        print(bold + red + "fillTable() : Error %s - Impossible de remplir la table %s" % (e, table_name) + endC, file=sys.stderr)
        return -1
    return 0

########################################################################
# FONCTION renameTable()                                               #
########################################################################
def renameTable(connection, old_table_name, new_table_name):
    """
    # Rôle : renommer une table
    # Paramètres en entrée :
    #   connection : laissez tel quel, récupère les informations de connexion à la base de données
    #   old_table_name : ancien nom de la table (existant)
    #   new_table_name : nouveau nom à donnée à la table
    """

    try:
        query = "ALTER TABLE %s RENAME TO %s;" % (old_table_name, new_table_name)
        executeQuery(connection, query)
    except psycopg2.DatabaseError as err:
        if connection:
            connection.rollback()
        print(bold + red + "renameTable() : Error %s - Impossible de renommer la table %s" % (e, old_table_name) + endC, file=sys.stderr)
        return -1
    return 0

########################################################################
# FONCTION copyTable()                                                 #
########################################################################
def copyTable(connection, table_name_scr, table_name_dst):
    """
    # Rôle : copier une table
    # Paramètres en entrée :
    #   connection : laissez tel quel, récupère les informations de connexion à la base de données
    #   table_name_scr : nom de la table à copier
    #   table_name_dst : nom à donner pour la nouvelle table
    """

    try:
        query = "CREATE TABLE %s AS TABLE %s;" % (table_name_dst, table_name_scr)
        executeQuery(connection, query)
    except psycopg2.DatabaseError as err:
        if connection:
            connection.rollback()
        e = "OS error: {0}".format(err)
        print(bold + red + "copyTable() : Error %s - Impossible de copier la table %s" % (e, table_name_scr) + endC, file=sys.stderr)
        return -1
    return 0

########################################################################
# FONCTION addData()                                                   #
########################################################################
def addData(connection, table_name, data):
    """
    # Rôle : ajouter des données dans une table
    # Paramètres en entrée :
    #   connection : laissez tel quel, récupère les informations de connexion à la base de données
    #   table_name : nom de la table à traiter
    #   data : données à insérer dans la table (de la forme : (9, 'Renault', 15000))
    """

    try:
        query = "INSERT INTO %s VALUES %s;" % (table_name, data)
        executeQuery(connection, query)
    except psycopg2.DatabaseError as err:
        if connection:
            connection.rollback()
        e = "OS error: {0}".format(err)
        print(bold + red + "addData() : Error %s - Impossible d'ajouter la donnée %s à la table %s" % (e, str(data), table_name) + endC, file=sys.stderr)
        return -1
    return 0

########################################################################
# FONCTION dropColumn()                                                #
########################################################################
def dropColumn(connexion, tablename, columnname):
    """
    Rôle : supprime une colonne d'une table

    Paramètres :
        connexion : connexion à la base donnée et au schéma correspondant
        tablename : nom de la table correspondant aux segments de végétation
        columnname : nom de la colonne à supprimer
    """

    query = """
    ALTER TABLE %s DROP COLUMN IF EXISTS %s;
    """ %(tablename, columnname)

    # Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    return

########################################################################
# FONCTION addUniqId()                                                 #
########################################################################
def addUniqId(connexion, tablename):
    """
    Rôle : créé un identifiant unique fid généré automatiquement

    Paramètres :
        connexion : connexion à la base donnée et au schéma correspondant
        tablename : nom de la table correspondant aux segments de végétation
    """

    query = """
    ALTER TABLE %s ADD COLUMN fid SERIAL PRIMARY KEY;
    """ %(tablename)

    #Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    return

########################################################################
# FONCTION addSpatialIndex()                                           #
########################################################################
def addSpatialIndex(connexion, tablename, geomcolumn = 'geom', nameindex = ''):
    """
    Rôle : créé un index spatial associé à la colonne géometrie

    Paramètres :
        connexion : connexion à la base donnée et au schéma correspondant
        tablename : nom de la table correspondant aux segments de végétation
        geomcolumn : nom de la colonne géometrie, par défaut : 'geom'
        nameindex : nom de l'index dans le cas où on souhaite lui en donné un spécifiquement. Par défaut : ''
    """
    if nameindex == '':
        nameindex = 'idx_gist_' + tablename
    query = """
    DROP INDEX IF EXISTS %s;
    CREATE INDEX %s ON %s USING gist(%s);
    """ %(nameindex,nameindex,  tablename, geomcolumn)

    #Exécution de la requête SQL
    if debug >= 1:
        print(query)
    executeQuery(connexion, query)

    return

########################################################################
# FONCTION addIndex()                                                  #
########################################################################
def addIndex(connexion, table_name, column_name, name_index):
    """
    Rôle : créé un index sur une colonne de la table

    Paramètres :
        connexion : laisser tel quel, récupère les informations de connexion à la base
        table_name : nom de la table
        column_name : nom de la colonne
        name_index : nom de l'index
    """
    print("Création d'un index spatial :")
    query = """
    CREATE INDEX %s ON %s(%s);
    """ %(name_index,table_name, column_name )
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    return

########################################################################
# FONCTION addColumn()                                                 #
########################################################################
def addColumn(connexion, tablename, columnname, columntype, debug = 0):
    """
    Rôle : créé un attribut d'une table dans la db

    Paramètres :
        connexion : connexion à la base donnée et au schéma correspondant
        tablename : nom de la table correspondant aux segments de végétation
        attributname : nom de l'attribut ajouté
        columntype : type de l'attribut ex : float, varchar, int, etc ...
    """

    query = """
    ALTER TABLE %s ADD COLUMN IF NOT EXISTS %s %s;
    """ %(tablename, columnname, columntype)

    #Exécution de la requête SQL
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    return

########################################################################
# FONCTION deleteData()                                                #
########################################################################
def deleteData(connection, table_name, column_name, data_name):
    """
    # Rôle : supprimer des données d'une table selon condition
    # Paramètres en entrée :
    #   connection : laissez tel quel, récupère les informations de connexion à la base de données
    #   table_name : nom de la table à traiter
    #   column_name : nom de la colonne à traiter
    #   data_name : nom de la donnée à supprimer
    """

    try:
        query = "DELETE FROM %s WHERE %s = '%s';" % (table_name, column_name, data_name)
        executeQuery(connection, query)
    except psycopg2.DatabaseError as err:
        if connection:
            connection.rollback()
        e = "OS error: {0}".format(err)
        print(bold + red + "deleteData() : Error %s - Impossible de supprimer la donnée %s de la table %s" % (e, data_name, table_name) + endC, file=sys.stderr)
        return -1
    return 0

########################################################################
# FONCTION getData()                                                   #
########################################################################
def getData(connection, table_name, column_name):
    """
    # Rôle : récupérer des données d'une colonne dans une table
    # Paramètres en entrée :
    #   connection : laissez tel quel, récupère les informations de connexion à la base de données
    #   table_name : nom de la table
    #   column_name : nom de la colonne à récupérer
    # Paramètre de retour :
    #   la liste des données d'une colonne d'une table
    """

    data_list = None
    try:
        cursor = connection.cursor()
        query = "SELECT %s FROM %s;" % (column_name, table_name)
        cursor.execute(query)
        data_list = cursor.fetchall()
    except psycopg2.DatabaseError as err:
        if connection:
            connection.rollback()
        e = "OS error: {0}".format(err)
        print(bold + red + "getData() : Error %s - Impossible de récupérer les données de la table %s" % (e, table_name) + endC, file=sys.stderr)
    return data_list

########################################################################
# FONCTION updateData()                                                #
########################################################################
def updateData(connection, table_name, column_name, new_value, condition):
    """
    # Rôle : mettre à jour un champs de la table suivant condition
    # Paramètres en entrée :
    #   connection : laissez tel quel, récupère les informations de connexion à la base de données
    #   table_name : nom de la table à traiter
    #   column_name : nom de la colonne à traiter
    #   new_value : nouvelle valeur à attribuer
    #   condition : condition pour la mise à jour de la table
    """

    try:
        query = "UPDATE %s SET %s = '%s' WHERE %s;" % (table_name, column_name, new_value, condition)
        executeQuery(connection, query)
    except psycopg2.DatabaseError as err:
        if connection:
            connection.rollback()
        e = "OS error: {0}".format(err)
        print(bold + red + "updateData() : Error %s - Impossible de mettre à jour la table %s" % (e, table_name) + endC, file=sys.stderr)
        return -1
    return 0

########################################################################
# FONCTION topologyCorrections()                                       #
########################################################################
def topologyCorrections(connection, table_name, geometry_column='geom'):
    """
    # Rôle : correction des erreurs topologiques
    # Paramètres en entrée :
    #   connection : laissez tel quel, récupère les informations de connexion à la base de données
    #   table_name : nom de la table à traiter
    """

    try:
        query = "UPDATE %s SET %s = public.ST_CollectionExtract(public.ST_ForceCollection(public.ST_MakeValid(%s)),3) WHERE NOT public.ST_IsValid(%s);" % (table_name, geometry_column, geometry_column, geometry_column)
        executeQuery(connection, query)
    except psycopg2.DatabaseError as err:
        if connection:
            connection.rollback()
        e = "OS error: {0}".format(err)
        print(bold + red + "topologyCorrections() : Error %s - Impossible de corriger les erreurs topologiques de la table %s" % (e, table_name) + endC, file=sys.stderr)
        return -1
    return 0

########################################################################
# FONCTION importVectorByOgr2ogr()                                     #
########################################################################
def importVectorByOgr2ogr(database_name, vector_name, table_name, user_name='postgres', password='postgres', ip_host='localhost', num_port='5432', schema_name='public', epsg='2154', codage='UTF-8'):
    """
    # Rôle : importer des données vecteurs dans une base de données PostgreSQL (via ogr2ogr)
    # Paramètres en entrée :
    #   database_name : nom de la base de données
    #   vector_name : nom du fichier (.csv) complet à importer
    #   table_name : nom à donner à la table
    #   user_name : nom d'utilisateur du serveur PostgreSQL (par défaut : 'postgres')
    #   password : mot de passe du serveur PostgreSQL (par défaut : 'postgres')
    #   ip_host : adresse IP du serveur PostgreSQL (par défaut : 'localhost')
    #   num_port : numéro de port du serveur PostgreSQL (par défaut : '5432')
    #   schema_name : nom du schema à utiliser (par défaut : 'public')
    #   epsg : code EPSG de la projection des données à importer (par défaut : '2154')
    #   codage : encodage de caractères du fichier shape à importer (par défaut : 'UTF-8')
    # Paramètre de retour :
    #   le nom de la table dans laquelle le fichier a été importé (modifié si ne respecte pas le regexp)
    """

    # Test de la validité du nom de la table (doit commencer par une lettre)
    regexp = "[A-Za-z]"
    if re.match(regexp, table_name[0]) is None:
        table_name = 't' + table_name

    # On efface la table si elle existe precedement
    connection = openConnection(database_name, user_name, password, ip_host, num_port, schema_name)
    dropTable(connection, table_name)
    closeConnection(connection)

    # Commande d'import avec ogr2ogr
    command = ""
    if codage != 'UTF-8':
        command += "PGCLIENTENCODING=%s " % (codage)
    command += "ogr2ogr -append -a_srs 'EPSG:%s' -f 'PostgreSQL' PG:'host=%s port=%s dbname=%s user=%s password=%s' %s -nln %s.%s -nlt GEOMETRY -lco LAUNDER=yes -lco GEOMETRY_NAME=geom" % (epsg, ip_host, num_port, database_name, user_name, password, vector_name, schema_name, table_name)

    try:
        if debug>=3:
            print(command)
        os.system(command)

    except Exception as err:
        e = "OS error: {0}".format(err)
        print(bold + red + "importVectorByOgr2ogr() : Error %s - Impossible d'importer les données de '%s'" % (e, vector_name) + endC, file=sys.stderr)
        return -1

    return table_name

########################################################################
# FONCTION exportVectorByOgr2ogr()                                     #
########################################################################
def exportVectorByOgr2ogr(database_name, vector_name, table_name, user_name='postgres', password='postgres', ip_host='localhost', num_port='5432', schema_name='public', format_type='ESRI Shapefile'):
    """
    # Rôle : exporter une table d'une base de données vers un fichier vecteur (via ogr2ogr)
    # Paramètres en entrée :
    #   database_name : nom de la base de données
    #   vector_name : nom du fichier (.csv) complet correspondant à la table exportée
    #   table_name : nom de la table contenant les données à exporter
    #   user_name : nom d'utilisateur du serveur PostgreSQL (par défaut : 'postgres')
    #   password : mot de passe du serveur PostgreSQL (par défaut : 'postgres')
    #   ip_host : adresse IP du serveur PostgreSQL (par défaut : 'localhost')
    #   num_port : numéro de port du serveur PostgreSQL (par défaut : '5432')
    #   schema_name : nom du schema à utiliser (par défaut : 'public')
    #   format_type : format d'export des données (par défaut : 'ESRI Shapefile')
    """

    # Commande d'export avec ogr2ogr
    command = "ogr2ogr -f '%s' %s PG:'host=%s port=%s dbname=%s user=%s password=%s' -sql 'SELECT * FROM %s.%s'" % (format_type, vector_name, ip_host, num_port, database_name, user_name, password, schema_name, table_name)

    try:
        if debug>=3:
            print(command)
        os.system(command)

    except Exception as err:
        e = "OS error: {0}".format(err)
        print(bold + red + "exportVectorByOgr2ogr() : Error %s - Impossible d'exporter la table '%s'" % (e, table_name) + endC, file=sys.stderr)
        return -1

    return 0

########################################################################
# FONCTION importShape()                                               #
########################################################################
def importShape(database_name, vector_name, table_name, user_name='postgres', password='postgres', ip_host='localhost', num_port='5432', schema_name='public', epsg='2154', codage='utf-8'):
    """
    # Rôle : importer un vecteur dans une base de données (via shp2pgsql : https://postgis.net/docs/using_postgis_dbmanagement.html#shp2pgsql_usage)
    # Paramètres en entrée :
    #   database_name : nom de la base de données
    #   vector_name : nom du fichier vecteur à importer
    #   table_name : nom à donner à la table où le shape sera importé
    #   user_name : nom d'utilisateur du serveur PostgreSQL (par défaut : 'postgres')
    #   password : mot de passe du serveur PostgreSQL (par défaut : 'postgres')
    #   ip_host : adresse IP du serveur PostgreSQL (par défaut : 'localhost')
    #   num_port : numéro de port du serveur PostgreSQL (par défaut : '5432')
    #   schema_name : nom du schema à utiliser (par défaut : 'public')
    #   epsg : code EPSG du système de coordonnées du fichier shape à importer (par défaut : '2154')
    #   codage : encodage de caractères du fichier shape à importer (par défaut : 'utf-8')
    # Paramètre de retour :
    #   le nom de la table dans laquelle le fichier a été importé (modifié si ne respecte pas le regexp)
    """

    # Intégrer le mot de passe dans le fichier 'pgpass' si ligne n'existe pas déjà
    checkPassword(user_name=user_name, password=password, ip_host=ip_host, num_port=num_port)

    # Test de la validité du nom de la table (doit commencer par une lettre)
    regexp = "[A-Za-z]"
    if re.match(regexp, table_name[0]) is None:
        table_name = 't' + table_name

    # Commande
    command = "shp2pgsql -D -I -d -s '%s' -W %s %s %s.%s" % (epsg, codage, vector_name, schema_name, table_name)
    command += " | psql -d %s -h %s -p %s -U %s" % (database_name, ip_host, num_port, user_name)

    try:
        if debug>=3:
            print(command)
        os.system(command)
    except Exception as err:
        e = "OS error: {0}".format(err)
        print(bold + red + "importShape() : Error %s - Impossible d'importer les données de '%s'" % (e, vector_name) + endC, file=sys.stderr)
        return -1

    return table_name

########################################################################
# FONCTION exportShape()                                               #
########################################################################
def exportShape(database_name, vector_name, table_name, user_name='postgres', password='postgres', ip_host='localhost', num_port='5432', schema_name='public'):
    """
    # Rôle : exporter un vecteur d'une base de données (via shp2pgsql : http://bostongis.com/pgsql2shp_shp2pgsql_quickguide.bqg)
    # Paramètres en entrée :
    #   database_name : nom de la base de données
    #   vector_name : nom du fichier vecteur qui sera exporté
    #   table_name : nom de la table contenant les données à exporter
    #   user_name : nom d'utilisateur du serveur PostgreSQL (par défaut : 'postgres')
    #   password : mot de passe du serveur PostgreSQL (par défaut : 'postgres')
    #   ip_host : adresse IP du serveur PostgreSQL (par défaut : 'localhost')
    #   num_port : numéro de port du serveur PostgreSQL (par défaut : '5432')
    #   schema_name : nom du schema à utiliser (par défaut : 'public')
    """

    command = "pgsql2shp -h %s -p %s -u %s -P %s -f %s -g 'geom' %s %s.%s" % (ip_host, num_port, user_name, password, vector_name, database_name, schema_name, table_name)

    try:
        if debug>=3:
            print(command)
        os.system(command)
    except Exception as err:
        e = "OS error: {0}".format(err)
        print(bold + red + "exportShape() : Error %s - Impossible d'exporter la table '%s'" % (e, table_name) + endC, file=sys.stderr)
        return -1

    return 0

########################################################################
# FONCTION importRaster()                                              #
########################################################################
def importRaster(database_name, file_name, table_name, user_name='postgres', password='postgres', ip_host='localhost', num_port='5432', schema_name='public', epsg='2154', nodata_value='0', tile_size='200x200', overview_factor='2,4,8'):
    """
    # Rôle : importer un raster dans une base de données (via raster2pgsql : http://postgis.net/docs/manual-dev/using_raster_dataman.html#RT_Raster_Loader)
    # Paramètres en entrée :
    #   database_name : nom de la base de données
    #   file_name : nom du fichier raster à importer
    #   table_name : nom à donner à la table où le raster sera importé
    #   user_name : nom d'utilisateur du serveur PostgreSQL (par défaut : 'postgres')
    #   password : mot de passe du serveur PostgreSQL (par défaut : 'postgres')
    #   ip_host : adresse IP du serveur PostgreSQL (par défaut : 'localhost')
    #   num_port : numéro de port du serveur PostgreSQL (par défaut : '5432')
    #   epsg : code EPSG du système de coordonnées du fichier raster à importer (par défaut : '2154')
    #   nodata_value : valeur NoData du fichier raster à importer (par défaut : '0')
    #   schema_name : nom du schema à utiliser (par défaut : 'public')
    #   tile_size : taille des tuiles générés lors de l'import, au format "LARGEURxHAUTEUR" sans espace (par défaut : '200x200')
    #   overview_factor : valeurs des miniatures/pyramides générées lors de l'import (par défaut : '2,4,8')
    # Paramètre de retour :
    #   le nom de la table dans laquelle le fichier a été importé (modifié si ne respecte pas le regexp)
    """

    # Intégrer le mot de passe dans le fichier 'pgpass' si ligne n'existe pas déjà
    checkPassword(user_name=user_name, password=password, ip_host=ip_host, num_port=num_port)

    # Test de la validité du nom de la table (doit commencer par une lettre)
    regexp = "[A-Za-z]"
    if re.match(regexp, table_name[0]) is None:
        table_name = 't' + table_name

    # Commande
    command = "raster2pgsql -d -C -s %s -t %s -l %s -N %s %s %s.%s" % (epsg, tile_size, overview_factor, nodata_value, file_name, schema_name, table_name)
    command += " | psql -d %s -h %s -p %s -U %s" % (database_name, ip_host, num_port, user_name)

    try:
        if debug>=3:
            print(command)
        os.system(command)
    except Exception as err:
        e = "OS error: {0}".format(err)
        print(bold + red + "importRaster() : Error %s - Impossible d'importer les données de '%s'" % (e, file_name) + endC, file=sys.stderr)
        return -1

    return table_name

########################################################################
# FONCTION exportRaster()                                              #
########################################################################
def exportRaster(database_name, file_name, table_name, user_name='postgres', password='postgres', ip_host='localhost', num_port='5432', schema_name='public'):
    """
    !!! ATTENTION en cours de developpement fonction à terminer apres avoir trouver la fonction pgsql2raster et ses parametres !!!
    # Rôle : exporter un raster d'une base de données(via pgsql2raster : www.cef-cfr.ca/uploads/Membres/WKTRasterSpecifications0.7.pdf)
    # Paramètres en entrée :
    #   database_name : nom de la base de données
    #   file_name : nom du fichier raster qui sera exporté
    #   table_name : nom de la table contenant les données à exporter
    #   user_name : nom d'utilisateur du serveur PostgreSQL (par défaut : 'postgres')
    #   password : mot de passe du serveur PostgreSQL (par défaut : 'postgres')
    #   ip_host : adresse IP du serveur PostgreSQL (par défaut : 'localhost')
    #   num_port : numéro de port du serveur PostgreSQL (par défaut : '5432')
    #   schema_name : nom du schema à utiliser (par défaut : 'public')
    """

    command = "pgsql2raster -f %s -h %s -p %s -u %s -r raster %s.%s" % (file_name, ip_host, password, user_name, schema_name, table_name)
    #"‘SELECT ST_Accum(ST_Band(raster,1)) FROM coverandtemp WHERE prov=‘BC’ GROUP BY prov’"

    try:
        if debug>=3:
            print(command)
        os.system(command)
    except Exception as err:
        e = "OS error: {0}".format(err)
        print(bold + red + "exportRaster() : Error %s - Impossible d'exporter la table '%s'" % (e, table_name) + endC, file=sys.stderr)
        return -1

    return 0

########################################################################
# FONCTION importDataCSV()                                             #
########################################################################
def importDataCSV(connection, csv_name, table_name, columns_table_dico, delimiter=";"):
    """
    # Rôle : importer des données .csv dans une base de données
    # Paramètres en entrée :
    #   connection : laissez tel quel, récupère les informations de connexion à la base de données
    #   csv_name : nom du fichier (.csv) complet à importer
    #   table_name : nom à donner à la table où le csv sera importé
    #   columns_table_dico : dictionnaire des noms de colonnes et du type de données associées [('column1', 'type1'), ('column2', 'type2'), ('column3', 'type3')])
    #   delimiter : séparateur de texte du fichier .csv (par défaut : ';')
    """

    cursor = connection.cursor()
    createTable(connection, table_name, columns_table_dico)
    f = open(csv_name, 'r')
    cursor.copy_from(f, table_name, sep=delimiter)
    f.close()
    connection.commit()
    return

########################################################################
# FONCTION exportDataCSV()                                             #
########################################################################
def exportDataCSV(connection, table_name, csv_name, delimiter=";"):
    """
    # Rôle : exporter des données d'une base de données en .csv
    # Paramètres en entrée :
    #   connection : laissez tel quel, récupère les informations de connexion à la base de données
    #   table_name : nom de la table contenant les données à exporter
    #   csv_name : nom du fichier (.csv) complet qui sera exporté
    #   delimiter : séparateur de texte du fichier .csv (par défaut : ';')
    """

    data_read = readTable(connection, table_name)
    with open(csv_name, 'w') as f:
        writer = csv.writer(f, delimiter=delimiter)
        for row in data_read:
            writer.writerow(row)
    return

########################################################################
# FONCTION readTable()                                                 #
########################################################################
def readTable(connection, table_name):
    """
    # Rôle : lire une table
    # Paramètres en entrée :
    #   connection : laissez tel quel, récupère les informations de connexion à la base de données
    #   table_name : nom de la table où récupérer les données à lire
    # Paramètre de retour :
    #   les données de la table
    """

    data_read = None
    try:
        query = "SELECT * FROM %s;" % (table_name)
        cursor = connection.cursor()
        cursor.execute(query)
        data_read = cursor.fetchall()
    except psycopg2.DatabaseError as err:
        e = "OS error: {0}".format(err)
        print(bold + red + "readTable() : Error %s - Impossible de lire la table %s" % (e, table_name) + endC, file=sys.stderr)
        data_read = None
    return data_read

########################################################################
# FONCTION postTable()                                                 #
########################################################################
def postTable(connection, table_name):
    """
    # Rôle : afficher le contenu d'une table dans la console
    # Paramètres en entrée :
    #   connection : laissez tel quel, récupère les informations de connexion à la base de données
    #   table_name : nom de la table où récupérer les données à afficher
    """

    data_read = readTable(connection, table_name)
    for row in data_read:
        print(row)
    return

########################################################################
# FONCTION getAllDatabases()                                           #
########################################################################
def getAllDatabases(user_name='postgres', password='postgres', ip_host='localhost', num_port='5432', schema_name=''):
    """
    # Rôle : lister les bases de données d'un serveur
    # Paramètres en entrée :
    #   user_name : nom d'utilisateur du serveur PostgreSQL (par défaut : 'postgres')
    #   password : mot de passe du serveur PostgreSQL (par défaut : 'postgres')
    #   ip_host : adresse IP du serveur PostgreSQL (par défaut : 'localhost')
    #   num_port : numéro de port du serveur PostgreSQL (par défaut : '5432')
    #   schema_name : nom du schema à utiliser (par défaut : '')
    # Paramètre de retour :
    #   la liste des bases de données
    """

    databases_list = None
    connection = psycopg2.connect(dbname='postgres', user=user_name, password=password, host=ip_host, port=num_port)
    cursor = connection.cursor()
    query = "SELECT datname FROM pg_catalog.pg_database;"
    cursor.execute(query)
    databases_list = cursor.fetchall()
    closeConnection(connection)
    print(bold + "Liste des bases de données du serveur '%s' :" % (ip_host) + endC)
    for row in sorted(databases_list):
        print("    %s" % (row))
    return databases_list

########################################################################
# FONCTION getAllSchemas()                                             #
########################################################################
def getAllSchemas(connection):
    """
    # Rôle : lister les schémas d'une base de données
    # Paramètres en entrée :
    #   connection : laissez tel quel, récupère les informations de connexion à la base de données
    # Paramètre de retour :
    #   la liste des schémas de la base de données
    """

    schemas_list = None
    cursor = connection.cursor()
    query = "SELECT nspname FROM pg_catalog.pg_namespace;"
    cursor.execute(query)
    schemas_list = cursor.fetchall()

    for row in sorted(schemas_list):
        print("    %s" % (row))
    return schemas_list

########################################################################
# FONCTION getAllTables()                                              #
########################################################################
def getAllTables(connection, schema_name):
    """
    # Rôle : lister les tables d'un schéma
    # Paramètres en entrée :
    #   connection : laissez tel quel, récupère les informations de connexion à la base de données
    #   schema_name : nom du schéma dans lequel lister les tables existantes
    # Paramètre de retour :
    #   la liste des tables du schéma
    """

    tables_list = None
    cursor = connection.cursor()
    query = "SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = '%s';" % (schema_name)
    cursor.execute(query)
    tables_list = cursor.fetchall()
    print(bold + "Liste des tables du schéma '%s' :" % (schema_name) + endC)
    for row in sorted(tables_list):
        print("    %s" % (row))
    return tables_list

########################################################################
# FONCTION getAllColumns()                                             #
########################################################################
def getAllColumns(connection, table_name):
    """
    # Rôle : lister les colonnes d'une table
    # Paramètres en entrée :
    #   connection : laissez tel quel, récupère les informations de connexion à la base de données
    #   table_name : nom de la table dans laquelle afficher les colonnes
    # Paramètre de retour :
    #   la liste des colonnes de la table
    """

    columns_list = None
    cursor = connection.cursor()
    query = "SELECT attname FROM pg_attribute WHERE attrelid = '%s'::regclass AND attnum > 0 AND NOT attisdropped ORDER BY attnum;" % (table_name)
    cursor.execute(query)
    columns_list = cursor.fetchall()
    print(bold + "Liste des colonnes de la table '%s' :" % (table_name) + endC)
    for row in columns_list:
        print("    %s" % (row))
    return columns_list

########################################################################
# FONCTION versionPostgreSQL()                                         #
########################################################################
def versionPostgreSQL(database_name='postgres', user_name='postgres', password='postgres', ip_host='localhost', num_port='5432', schema_name=''):
    """
    # Rôle : afficher la version de PostgreSQL
    # Paramètres en entrée :
    #   database_name : nom de la base de données
    #   user_name : nom d'utilisateur du serveur PostgreSQL (par défaut : 'postgres')
    #   password : mot de passe du serveur PostgreSQL (par défaut : 'postgres')
    #   ip_host : adresse IP du serveur PostgreSQL (par défaut : 'localhost')
    #   num_port : numéro de port du serveur PostgreSQL (par défaut : '5432')
    #   schema_name : nom du schema à utiliser (par défaut : '')
    # Paramètre de retour :
    #   la version de PostgresSQL
    """

    connection = openConnection(database_name, user_name, password, ip_host, num_port)
    cursor = connection.cursor()
    cursor.execute("SELECT version();")
    postgresql_version = cursor.fetchone()
    closeConnection(connection)
    if debug >= 3:
        print(bold + "Version de PostgreSQL : " + endC + str(postgresql_version))
    return postgresql_version

########################################################################
# FONCTION versionPostGIS()                                            #
########################################################################
def versionPostGIS(database_name='template_postgis', user_name='postgres', password='postgres', ip_host='localhost', num_port='5432', schema_name=''):
    """
    # Rôle : afficher la version de PostGIS
    # Paramètres en entrée :
    #   database_name : nom de la base de données
    #   user_name : nom d'utilisateur du serveur PostgreSQL (par défaut : 'postgres')
    #   password : mot de passe du serveur PostgreSQL (par défaut : 'postgres')
    #   ip_host : adresse IP du serveur PostgreSQL (par défaut : 'localhost')
    #   num_port : numéro de port du serveur PostgreSQL (par défaut : '5432')
    #   schema_name : nom du schema à utiliser (par défaut : '')
    # Paramètre de retour :
    #   la version de PostGIS
    """

    connection = openConnection(database_name, user_name, password, ip_host, num_port)
    cursor = connection.cursor()
    cursor.execute("SELECT PostGIS_Full_Version();")
    postgis_version = cursor.fetchone()
    closeConnection(connection)
    if debug >= 3:
        print(bold + "Version de PostGIS : " + endC + str(postgis_version))
    return postgis_version

########################################################################
# FONCTION versionPostGIS()                                            #
########################################################################
def createExtension(connexion, extension_name, debug = 0):
    """
    Rôle : créer un extension dans la BD

    Paramètres :
      connexion : paramètre unique de connexion à la base de données pgsql
      extension_name : nom d'utilisateur du serveur PostgreSQL (par défaut : 'postgres')

    """
    query = """
    CREATE EXTENSION IF NOT EXISTS %s WITH SCHEMA public;
    """ %(extension_name)
    if debug >= 3:
        print(query)
    executeQuery(connexion, query)

    return

def dataBaseExist(connexion, dbname):
    """
    Rôle : renvoie si la base de données existe déjà

    Paramètre :
        connexion : laisser tel quel, récupère les informations de connexion à la base
        dbname : nom de la base de données

    Sortie :
        True ou False en fonction de l'existence de la BD
    """
    exist = False

    query = """ SELECT 1 FROM pg_database WHERE datname = '%s';""" %(dbname)

    cursor = connexion.cursor()
    cursor.execute(query)
    result = cursor.fetchone()[0]

    if result == 1 :
        exist = True

    return exist

def schemaExist(connexion, schema_name):
    """
    Rôle : renvoie si le schema existe déjà

    Paramètre :
        connexion : laisser tel quel, récupère les informations de connexion à la base
        schema_name : nom du schema

    Sortie :
        True ou False en fonction de l'existence du schéma dans la db
    """
    exist = False
    li_schema = getAllSchemas(connexion)

    if schema_name in li_schema:
        exist = True

    return exist
