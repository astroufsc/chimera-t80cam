import logging

from adshli.hli import ads_device
from adshli.connection import ads_connection


connpars = dict(plc_ams_id="5.18.26.30.1.1",
                plc_ams_port=801,
                plc_ip_adr="192.168.100.1",
                plc_ip_port=48898,
                pc_ams_id="5.18.26.31.1.1",
                pc_ams_port=32788,
                timeout=5)

log = logging.getLogger(name=__name__)


class FSUConn():

    """
    FSU communication common class.
    """

    def __init__(self):
        try:
            self.conn = ads_connection(connpars['plc_ams_id'],
                                       connpars['plc_ams_port'],
                                       connpars['pc_ams_id'],
                                       connpars['pc_ams_port'])
        except Exception:
            print('Error in connection def.')
            # log.critical('Unable to connect to FSU')
        # Open a connection to the slave PLC controller.
        try:
            self.conn.open(connpars['plc_ip_adr'],
                           connpars['plc_ip_port'],
                           connpars['timeout'])
            print('Connected to EBox')
        except:
            print('Error in opening connection')
        self.device = ads_device(self.conn)
        # log.info('FSU device name:', str(self.device.device_name),
        # 'ADS state:', self.device.ads_state,
        # 'Device state:', self.device.device_state)
        # print('FSU device name:', self.device.device_name,
        #       'ADS state:', self.device.ads_state,
        #       'Device state:', self.device.device_state)
