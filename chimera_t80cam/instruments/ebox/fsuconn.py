import logging

from adshli.hli import ads_device
from adshli.connection import ads_connection

log = logging.getLogger(name=__name__)

class FSUConn():
    """
    FSU communication common class.
    """

    def __init__(self,connpars):
        self.conn = None
        self.device = None

        self._plc_ams_id = connpars['plc_ams_id']
        self._plc_ams_port = connpars['plc_ams_port']
        self._pc_ams_id = connpars['pc_ams_id']
        self._pc_ams_port = connpars['pc_ams_port']

        self._plc_ip_adr = connpars['plc_ip_adr']
        self._plc_ip_port = connpars['plc_ip_port']
        self._plc_timeout = connpars['plc_timeout']

        self.connect_plc()

    def __del__(self):
        self.conn.close()

    def disconnect_plc(self):
        self.conn.close()

    def connect_plc(self):
        self.conn = ads_connection(self._plc_ams_id,
                                   self._plc_ams_port,
                                   self._pc_ams_id,
                                   self._pc_ams_port)

        # Open a connection to the slave PLC controller.
        self.conn.open(self._plc_ip_adr,
                       self._plc_ip_port,
                       self._plc_timeout)

        self.device = ads_device(self.conn)
