import logging
import time

from adshli.hli import ads_var_single

from chimera.instruments.ebox.fsuconn import FSUConn


log = logging.getLogger(name=__name__)


class FSUFilterWheel(FSUConn):

    """
    Solunia class to interface with the filter wheels component.
    """

    def __init__(self):
        # Connect to the slave CPU
        FSUConn.__init__(self)

    def __start__(self):
        """
        Initialize object from Chimera.
        """
        # CAM filter wheel position vector (0 -> 12)
        self._vread0 = ads_var_single(self.conn, '.wDWORD_READ[0]', 'i')
        # CAM filter wheel position request vector
        self._wPOS_REQ = ads_var_single(
            self.conn, '.wPOSITIONING_REQUESTED_T80_CAM_BOX', 'i')
        # CAM filter wheels commands vector
        self._vread1 = ads_var_single(self.conn, '.wDWORD_READ[1]', 'i')
        # CAM filter wheels status vectors
        self._vwrite0 = ads_var_single(self.conn, '.wDWORD_WRITE[0]', 'i')
        self._vwrite1 = ads_var_single(self.conn, '.wDWORD_WRITE[1]', 'i')
        self._vwrite10 = ads_var_single(self.conn, '.wDWORD_WRITE[10]', 'i')
        self._vwrite12 = ads_var_single(self.conn, '.wDWORD_WRITE[12]', 'i')
        self._vwrite13 = ads_var_single(self.conn, '.wDWORD_WRITE[13]', 'i')

    def move_pos(self, filterpos):
        # Ensure the motion bit is set to zero
        if (self._vread1.read() & 1) != 0:
            self._vread1.write(self._vread1.read() ^ 1)
        # Set the filter position vector
        self._vread0.write(filterpos)
        # print 'WD_READ[0] = ', self._vread0.read()
        while self.get_req_pos() != filterpos:
            # print 'Waiting for variable to set...'
            time.sleep(0.1)
        print 'wPOSITIONING_REQUESTED_T80_CAM_BOX = ', self._wPOS_REQ.read()
        print 'WD_READ[0] = ', bin(self._vread0.read())
        # Move it
        self._vread1.write(self._vread1.read() ^ 1)
        print 'Moving flag: ', bin(self._vwrite1.read())
        print self._vwrite1.read() & (1 << 2)
        print self._vwrite1.read() & (1 << 3)
        time.sleep(0.5)
        # print not ((self._vwrite1.read() & (1 << 2) != 0) and
        #            (self._vwrite1.read() & (1 << 3) != 0))
        while not ((self._vwrite1.read() & (1 << 2) != 0) and
                   (self._vwrite1.read() & (1 << 3) != 0)):
            # Not in position yet
            time.sleep(0.5)
            print 'Moving flag: ', bin(self._vwrite1.read())
            print ((self._vwrite1.read() & (1 << 2) != 0),
                   (self._vwrite1.read() & (1 << 3) != 0))
            continue

    def move_stop(self):
        """
        Stop all filter wheels motion.

        .. method:: move_stop()
            Aborts any current rotation of all filter wheels.
        """
        # This is accomplished by flipping bit 5
        self._vread1.write(self._vread1.read() | (1 << 5))

    def get_pos(self):
        """
        Get current filter position.

        .. method:: get_pos()
            Returns the current filter by
            :return: filter position.
            :rtype: int.
        """
        blonks = self._vread0.read()
        return blonks

    def get_req_pos(self):
        return self._wPOS_REQ.read()

    def check_hw(self):
        """
        Check hardware sanity.

        .. method:: check_hw()
            Checks al PLC registers for fault conditions.

        :return: various fault messages/exceptions.
        """
        # The vectors are:
        # .wDWORD_WRITE[0] bit 0: timeout filter wheel position
        # .wDWORD_WRITE[0] bit 1: timeout analyser wheel position
        # .wDWORD_WRITE[0] bit 2: shutter error flag
        # .wDWORD_WRITE[0] bit 3: shutter opened flag
        # .wDWORD_WRITE[0] bit 4: filter wheel encoder disconnected or inverted
        # .wDWORD_WRITE[0] bit 5: analyser wheel encoder disconnected or
        #                         inverted
        # .wDWORD_WRITE[0] bit 6: filter wheel motor disconnected
        # .wDWORD_WRITE[0] bit 7: analyser wheel motor disconnected
        #
        # .wDWORD_WRITE[1] bit 0: filter wheel motor inverted
        # .wDWORD_WRITE[1] bit 1: analyser wheel motor inverted
        # .wDWORD_WRITE[1] bit 2: filter wheel position reached flag
        # .wDWORD_WRITE[1] bit 3: analyser wheel position reached flag
        # .wDWORD_WRITE[1] bit 4: filter wheel error flag
        # .wDWORD_WRITE[1] bit 5: analyser wheel error flag
        #
        # .wDWORD_WRITE[10] bit 0: wave plate enabled flag
        # .wDWORD_WRITE[10] bit 1: wave plate error flag
        # .wDWORD_WRITE[10] bit 2: wave plate position reached flag
        # .wDWORD_WRITE[10] bit 3: wave plate homed flag
        # .wDWORD_WRITE[10] bit 4: wave plate encoder disconnected or inverted
        # .wDWORD_WRITE[10] bit 5: wave plate motor disconnected
        #
        # .wDWORD_WRITE[12]: error number of the function block M3 servomotor
        #                   (wave plate)
        # .wDWORD_WRITE[13]: error number for the axis M3 servomotor (wave
        #                   plate)

        # For convenience, make all arrays' length 8
        vec_msgs = [('Filter wheel: position timeout',
                     'Analyser wheel: position timeout',
                     'Shutter: error',
                     'Shutter: opened',
                     'Filter wheel encoder: disconnected or inverted',
                     'Analyser wheel encoder: disconnected or inverted',
                     'Filter wheel: motor disconnected',
                     'Analyser wheel: motor disconnected'),
                    ('Filter wheel: motor inverted',
                     'Analyser wheel: motor inverted',
                     'Filter wheel: position reached',
                     'Analyser wheel: position reached',
                     'Filter wheel: error flag',
                     'Analyser wheel: error flag',
                     '',
                     ''),
                    ('Wave plate: enabled',
                     'Wave plate: error',
                     'Wave plate: position reached',
                     'Wave plate: homed',
                     'Wave plate: encoder disconnected or inverted',
                     'Wave plate: motor disconnected',
                     '',
                     '')]

        # Let's start
        for statbit in range(0, 8):
            if self._vwrite0.read() & (1 << statbit) == 1:
                print vec_msgs[statbit]
        for statbit in range(0, 8):
            if self._vwrite1.read() & (1 << statbit) == 1:
                print vec_msgs[statbit]
        for statbit in range(0, 8):
            if self._vwrite10.read() & (1 << statbit) == 1:
                print vec_msgs[statbit]
        # Now take care of the full reg values : 12, 13
        # for idx in [12, 13]:
        print('Function blk M3 servo (wplate) error number: {0}'.format(
            self._vwrite12.read()))
        print('Function blk M3 servo axis (wplate)error number: {0}'.format(
            self._vwrite13.read()))
        # TODO: return values and decisions for error conditions found.


