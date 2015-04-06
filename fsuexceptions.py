from chimera.core.exceptions import ChimeraException


class FSUException(ChimeraException):
    """
    Base class for FSU exceptions hierarchy.
    """
    def __init__(self, code, msg=""):
        ChimeraException.__init__(self, msg)
        self.code = code

    def __str__(self):
        return "%s (%d)" % (self.message, self.code)
