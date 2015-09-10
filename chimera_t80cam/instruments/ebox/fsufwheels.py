from adshli.hli import ads_var_single

from chimera.core.exceptions import ChimeraException


class FSUFWheels():
    """
    Solunia class to interface with the filter wheels component.
    """

    def __init__(self):
        """
        Initialize PLC registers.
        """
        # CAM filter wheel position vector (0 -> 12)
        self._vread0 = ads_var_single(self.conn, '.wDWORD_READ[0]', 'i')
        # CAM filter wheel position request vector
        self._wPOS_REQ = ads_var_single(
            self.conn, '.wPOSITIONING_REQUESTED_T80_CAM_BOX', 'i')
        # CAM filter wheels stop motion request vector (bit)
        # self._bSTOP_REQ = ads_var_single(
        # self.conn, '.bSTOP_POSITIONING_REQUESTED_FILTERS_WHEEL', 'b')
        # CAM/POL filter wheels commands vector
        self._vread1 = ads_var_single(self.conn, '.wDWORD_READ[1]', 'i')
        self._vread10 = ads_var_single(self.conn, '.wDWORD_READ[10]', 'i')
        self._vread11 = ads_var_single(self.conn, '.wDWORD_READ[11]', 'i')
        self._vread12 = ads_var_single(self.conn, '.wDWORD_READ[12]', 'i')
        self._vread20 = ads_var_single(self.conn, '.wDWORD_READ[20]', 'i')
        self._vread21 = ads_var_single(self.conn, '.wDWORD_READ[21]', 'i')
        self._vread22 = ads_var_single(self.conn, '.wDWORD_READ[22]', 'i')
        # CAM filter wheels status vectors
        self._vwrite0 = ads_var_single(self.conn, '.wDWORD_WRITE[0]', 'i')
        self._vwrite1 = ads_var_single(self.conn, '.wDWORD_WRITE[1]', 'i')
        self._vwrite10 = ads_var_single(self.conn, '.wDWORD_WRITE[10]', 'i')
        self._vwrite20 = ads_var_single(self.conn, '.wDWORD_WRITE[20]', 'i')
