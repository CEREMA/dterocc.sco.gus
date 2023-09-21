# IMPORTS DIVERS
import os, subprocess, platform, psutil, multiprocessing, threading ,ctypes, re, inspect


#########################################################################
# CLASSE QUI SIMULE UN SWITCH CASE                                      #
#########################################################################
class switch( object ):
    """
    # switch :
    # case :
    # Exemple d'utilisation:
    #       while switch(ident):
    #         if case(0):
    #            print("Autre : ")
    #            break
    #         if case(11000):
    #            print("Antropise : ")
    #            break
    #         if case(12200):
    #            print("Eau : ")
    #            break
    #         if case(21000):
    #            print("Ligneux : ")
    #            break
    #         if case(22000):
    #            print("NonLigneux : ")
    #            break
    #         break
    """

    value = None
    def __new__( class_, value ):
         class_.value = value
         return True

def case( *args ):
    return any( ( arg == switch.value for arg in args ) )