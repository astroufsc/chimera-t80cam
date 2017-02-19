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

        self._wPOS_REQU_T80_POL_BOX_FILTER_WHEEL1 = ads_var_single(
            self.conn, '.wPOSITIONING_REQUESTED_T80_POL_BOX_FILTER_WHEEL1', 'i')

        self._wPOS_REQU_T80_POL_BOX_FILTER_WHEEL2 = ads_var_single(
            self.conn, '.wPOSITIONING_REQUESTED_T80_POL_BOX_FILTER_WHEEL2', 'i')

        self._wPOS_REQU_T80_POL_BOX_WHEEL = ads_var_single(
            self.conn, '.wPOSITIONING_REQUESTED_T80_POL_BOX_WHEEL', 'i')

        self._wPOS_REQU_T80_POL_BOX_FILTER = ads_var_single(
            self.conn, '.wPOSITIONING_REQUESTED_T80_POL_BOX_FILTER', 'i')

        # CAM filter wheels stop motion request vector (bit)
        # self._bSTOP_REQ = ads_var_single(
        # self.conn, '.bSTOP_POSITIONING_REQUESTED_FILTERS_WHEEL', 'b')
        # CAM/POL filter wheels commands vector
        self._vread1 = ads_var_single(self.conn, '.wDWORD_READ[1]', 'i')
        self._vread2 = ads_var_single(self.conn, '.wDWORD_READ[2]', 'i')
        self._vread2 = ads_var_single(self.conn, '.wDWORD_READ[2]', 'i')
        self._vread3 = ads_var_single(self.conn, '.wDWORD_READ[3]', 'i')
        self._vread10 = ads_var_single(self.conn, '.wDWORD_READ[10]', 'i')
        self._vread11 = ads_var_single(self.conn, '.wDWORD_READ[11]', 'i')
        self._vread12 = ads_var_single(self.conn, '.wDWORD_READ[12]', 'i')
        self._vread20 = ads_var_single(self.conn, '.wDWORD_READ[20]', 'i')
        self._vread21 = ads_var_single(self.conn, '.wDWORD_READ[21]', 'i')
        self._vread22 = ads_var_single(self.conn, '.wDWORD_READ[22]', 'i')
        # CAM filter wheels status vectors
        self._vwrite0 = ads_var_single(self.conn, '.wDWORD_WRITE[0]', 'i')
        self._vwrite1 = ads_var_single(self.conn, '.wDWORD_WRITE[1]', 'i')
        self._vwrite2 = ads_var_single(self.conn, '.wDWORD_WRITE[2]', 'i')
        self._vwrite3 = ads_var_single(self.conn, '.wDWORD_WRITE[3]', 'i')
        self._vwrite10 = ads_var_single(self.conn, '.wDWORD_WRITE[10]', 'i')
        self._vwrite20 = ads_var_single(self.conn, '.wDWORD_WRITE[20]', 'i')

        self._rlREAL_READ0 = ads_var_single(self.conn, '.rlREAL_READ[0]', 'd')  # FILTER WHEEL COORDINATE
        self._rlREAL_READ1 = ads_var_single(self.conn, '.rlREAL_READ[1]', 'd')  # ANALYSER WHEEL COORDINATE
        self._rlREAL_READ2 = ads_var_single(self.conn, '.rlREAL_READ[2]', 'd')  # FILTER WHEEL HOME COORDINATE
        self._rlREAL_READ3 = ads_var_single(self.conn, '.rlREAL_READ[3]', 'd')  # ANALYSER WHEEL FILTER COORDINATE
        self._rlREAL_READ4 = ads_var_single(self.conn, '.rlREAL_READ[4]', 'd')  # FILTER WHEEL VELOCITY PERCENTAGE
        self._rlREAL_READ5 = ads_var_single(self.conn, '.rlREAL_READ[5]', 'd')  # ANALYSER WHEEL VELOCITY PERCENTAGE

        # Operation mode position or angle/home
        self._bFILTER_1_AND_2_HOME_MODE = ads_var_single(self.conn, '.bFILTER_1_AND_2_HOME_MODE', '?')

        # HOME position stored at the PLC server
        ## Wheel 1
        self._lrINITIAL_ANGLE_POS_M1 = self._rlREAL_READ0 = ads_var_single(self.conn,'.lrINITIAL_ANGLE_POS_M1','d')
        ## Wheel 2
        self._lrINITIAL_ANGLE_POS_M2 = self._rlREAL_READ0 = ads_var_single(self.conn,'.lrINITIAL_ANGLE_POS_M2','d')

