
from chimera.core.lock import lock

from chimera_t80cam.instruments.sibase import SIBase
from chimera_t80cam.instruments.ebox.fsupolarimeter.fsupolarimeter import FsuPolarimeter


class T80Pol(SIBase, FsuPolarimeter):

    __config__ = {'device': 'ethernet'}

    def __init__(self):

        SIBase.__init__(self)
        FsuPolarimeter.__init__(self)

    @lock
    def open(self):
        self.connectSIClient()
        self.connectTWC()
        return True

    def getMetadata(self, request):
        camera_hdr = super(SIBase, self).getMetadata(request)
        polarimeter_hdr = super(FsuPolarimeter, self).getMetadata(request)

        return camera_hdr+polarimeter_hdr
