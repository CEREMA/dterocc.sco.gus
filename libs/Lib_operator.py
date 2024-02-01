#Import des librairies Python
import os, platform
debug = 1
#########################################################################
# FONCTION getExtensionApplication()                                    #
#########################################################################
def getExtensionApplication():
    """
    # ROLE :
    #   La fonction retourne le type d'extension approprier pour certaines applications
    #   en fonction du systeme d'environement
    # ENTREES :
    # SORTIES :
    #   Return l'extension
    """

    extend_cmd = ""
    os_system = platform.system()
    if 'Windows' in os_system :
        extend_cmd = ".bat"
    elif 'Linux' in os_system :
        extend_cmd = ".py"
    else :
        raise NameError ("!!! Erreur le type de systeme n'a pu être déterminer : " + os_system)
    return extend_cmd

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
