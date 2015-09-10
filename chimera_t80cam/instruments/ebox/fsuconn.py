import logging

from adshli.hli import ads_device
from adshli.connection import ads_connection

log = logging.getLogger(name=__name__)

class FSUConn():
    """
    FSU communication common class.
    """

    def __init__(self,connpars):
        self.conn = ads_connection(connpars['plc_ams_id'],
                                   connpars['plc_ams_port'],
                                   connpars['pc_ams_id'],
                                   connpars['pc_ams_port'])
        # Open a connection to the slave PLC controller.
        self.conn.open(connpars['plc_ip_adr'],
                       connpars['plc_ip_port'],
                       connpars['plc_timeout'])
        self.device = ads_device(self.conn)

    def __del__(self):
        self.conn.close()
