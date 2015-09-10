
from chimera.core.lock import lock

from chimera_t80cam.instruments.sibase import SIBase
from chimera_t80cam.instruments.ebox.fsufilters.fsufilters import FsuFilters

class T80Cam(SIBase,FsuFilters):

    __config__ = {'device': 'ethernet'}

    def __init__(self):

        SIBase.__init__(self)
        FsuFilters.__init__(self)

    @lock
    def open(self):
        # super(SIBase,self).open()
        # super(FsuFilters,self).open()
        self.connectSIClient()
        self.connectTWC()
        return True
        # if super(SIBase,self).open() and super(FsuFilters,self).open():
        #     return True
        # else:
        #     return False


    def getMetadata(self, request):
        cameraHDR = super(SIBase,self).getMetadata(request)
        filterHDR = super(FsuFilters,self).getMetadata(request)

        return cameraHDR+filterHDR