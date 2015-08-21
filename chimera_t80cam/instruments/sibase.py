
import os
import re
import logging

import numpy as N
from astropy.io.fits import Header
from astropy.io import fits as pyfits

import select

from si.client import SIClient, AckException
from si.commands.camera import *
from si.packet import Packet
from si.packets.ack import Ack

from chimera.interfaces.camera import (CCD, CameraFeature, ReadoutMode,
                                       InvalidReadoutMode, CameraStatus,
                                       Shutter)

from chimera.util.image import Image, ImageUtil
from chimera.instruments.camera import CameraBase
from chimera.util.enum import Enum
from chimera.core.lock import lock
from chimera.core.exceptions import ChimeraException
from chimera.core.version import _chimera_name_, _chimera_long_description_
from chimera.controllers.imageserver.util import getImageServer

from collections import defaultdict
from itertools import count

import datetime as dt
import time

ImgType = Enum("U16", "I16", "U32", "I32", "SGL", "DBL")


class SIException(ChimeraException):
    pass

log = logging.getLogger(__name__)

class SIBase(CameraBase):
    """
    Spectral Instruments Base camera class. Defines functions to control the
    camera alone. This can be used as base class for cameras with different
    filterwheels, etc.

    Author: Tiago Ribeiro
    Date: April/2015
    """

    __config__ = {'device': 'ethernet', 'ccd': CCD.IMAGING, 'temp_delta': 2.0,
                  'camera_model': 'Spectral Instruments 1110 SN 105',
                  'ccd_model': 'e2V CCD 290-99',
                  'camera_host': '127.0.0.1', 'camera_port': 2055,
                  'localhost': False,
                  "local_filename" : 'tmp.fits',
                  "local_path" : '/tmp/'}

    def __init__(self):
        CameraBase.__init__(self)

        self.abort.clear()
        self.client = None
        self.pars = list()
        self.stats = list()
        self.sgl2 = list()

        self.ccd = 0

        # self.lastTemp = None
        #
        # self.lastFrameStartTime = None
        # self.lastFrameTemp = None
        # self.lastFrameFilename = ""

        # self._isFanning = False

        # self.setHz(1.0 / 5)

        self._supports = {CameraFeature.TEMPERATURE_CONTROL: True,
                          CameraFeature.PROGRAMMABLE_GAIN: True,
                          CameraFeature.PROGRAMMABLE_OVERSCAN: False,
                          CameraFeature.PROGRAMMABLE_FAN: False,
                          CameraFeature.PROGRAMMABLE_LEDS: True,
                          CameraFeature.PROGRAMMABLE_BIAS_LEVEL: False}

        self._nCCDs = 0  # number of installed CCDs

        self._ccds = {self.ccd: CCD.IMAGING}

        self._adcs = {"12 bits": 0}  # Check

        countBinns = count(0)
        self._binnings = defaultdict(countBinns.next)

        # self._binning_factors = {'1x1':1}

        self._gain = []

        self._ros = []

        self._readoutModes = {}

        # self._cameraParameters = {}

        self.imghdr = Header()

    def __start__(self):
        self.open()
        self.log.info("retrieving information from camera...")
        self.get_status()
        self.get_config()
        self.get_camera_settings()

    def __stop__(self):
        try:
            # self.stopFan()
            # WARNING: NEVER do this on this camera!!
            # self.stopCooling()
            self.close()
        except SIException:
            pass

    @lock
    def open(self):
        """
        Open connection with SI Camera server.

        :return:
        """
        self.log.debug("Connecting to SI Camera Server @ %s:%s" % (
            self["camera_host"], self["camera_port"]))

        self.client = SIClient(self['camera_host'], self['camera_port'])
        try:
            self.client.connect()
        except SIException as e:
            self.log.critical("Connection error: {}".format(e))
            return False
        return True

    @lock
    def close(self):
        self.client.disconnect()

    @lock
    def get_config(self):
        """
        Get the camera configuration parameters.

        .. method:: configure()

        """
        self.pars = []
        lines = self.client.executeCommand(
            GetCameraParameters()).parameterlist.splitlines()
        for i in range(len(lines)):
            self.pars += [re.split(',(.+),', lines[i])]
        for i in range(len(self.pars) - 1):
            if "Installed CCDs" in self.pars[i][1]:
                self._nCCDs = int(self.pars[i][2])
                # if "Serial Binning" in cam.pars[i][1]:
                #     self.sbin = cam.pars[i][2]
                # if "Parallel Binning" in cam.pars[i][1]:
                #     self.pbin = cam.pars[i][2]

        if self._nCCDs == 0:
            self._nCCDs = 1

        for i in range(self._nCCDs):
            self._ccds[i] = i

        self._binnings = {"1x1": 0}
        self._binning_factors = {"1x1": 1}

        # ToDo: Read gain from camera parameters
        self._gain = [0, 1]

        # ToDo: Read read-out-speed from camera parameters
        self._ros = ['101MHz', '500kHz', '250kHz', '100kHz']

        # This readoutMode stores only geometrical information.
        for ccd in self._ccds.keys():
            romode = {}
            mode = 0
            for g in self._gain:
                readoutMode = ReadoutMode()
                readoutMode.mode = mode
                readoutMode.gain = g
                readoutMode.width, readoutMode.height = self.getPhysicalSize()
                readoutMode.pixelWidth, readoutMode.pixelHeight = \
                    self.getPixelSize()
                romode[mode] = readoutMode
            self._readoutModes[ccd] = romode

    @lock
    def get_status(self):
        """
        Return camera status table.
            Generates an instance list of lists containing group,name.value
             strings.
        .. method:: get_status()
            Generates an instance list of lists containing name,value,unit
             strings.
        """
        lines = self.client.executeCommand(
            GetStatusFromCamera()).statuslist.splitlines()
        self.stats = []
        for i in range(len(lines)):
            self.stats += [re.split(',(.+),', lines[i])]

    @lock
    def get_camera_settings(self):
        """
        Return the SGLII settings.
        :return:
        """
        self.sgl2 = self.client.executeCommand(GetSIImageSGLIISettings())

    @lock
    def get_acq_modes(self):
        """

        :return:
        """
        self.acqmodes = self.client.executeCommand(
            GetAcquisitionModes()).menuinfolist.splitlines()

    @lock
    def get_xml_files(self, thefile):
        # Get the main files list
        xmlfiles = self.client.executeCommand(
            GetCameraXMLFile('files.xml')).fileslist

        # flist = []
        # root = ETree.fromstring(xmlfiles)
        #
        # for k in root.iter(tag='name'):
        #     if ‘_q’ not in k.text:
        #         flist.append(k.text)
        # flist now contains the list of all xml files; lets go pick each
        # for f in flist:
        #     pass

    @lock
    def startCooling(self, tempC):
        # TODO: works, doesn't return
        # send command
        try:
            ack = self.client.executeCommand(SetCooler(1))
        except AckException:
            return False
        else:
            return True

    @lock
    def stopCooling(self):
        # send command
        try:
            ack = self.client.executeCommand(SetCooler(0))
        except AckException:
            return False
        else:
            return True

    @lock
    def isCooling(self):
        NotImplementedError()

    def isFanning(self):
        return False

    @lock
    def getTemperature(self):
        ttpl = list()
        try:
            self.get_status()
        except:
            self.log.warning('Could not update camera temperature.')
        for i in range(len(self.stats)):
            if "CCD Temp." in self.stats[i][0]:
                ttpl.append(self.stats[i][1].replace(',', '.'))
        return float(ttpl[self.getCurrentCCD()])

    @lock
    def getSetPoint(self):
        """
        Return the CCD(s) temperature set point.
        .. Note:: the value stored in the camera's registry is in K*10.

        :return: temperature in C.
        """
        for i in range(len(self.pars)):
            if "Temperature Setpoint" in self.pars[i][1]:
                temp = (int(self.pars[i][2]) / 10.) - 273.15
        return temp

    def getCCDs(self):
        return self._ccds

    def getCurrentCCD(self):
        return self.ccd

    def getBinnings(self):
        """
        Return available binnings.

        If there is a predefined set of binnings imposed by other cameras,
        it will be returned as a dict. Otherwise a dict with the current
        values  is returned.
        :return:
        """
        # sb = str(self.sgl2.serial_binning)
        # pb = str(self.sgl2.parallel_binning)
        # return {"{0:s}x{1:s}".format(sb, pb): 0}
        return self._binnings

    def getADCs(self):
        return self._adcs

    def getPhysicalSize(self):
        length, heigth = 0, 0
        for i in range(len(self.pars)):
            if "Serial Active Pix." in self.pars[i]:
                length = int(self.pars[i][2])
            elif "Parallel Active Pix." in self.pars[i]:
                heigth = int(self.pars[i][2])

        return length, heigth

    def getPixelSize(self):
        xsize, ysize = self.getPhysicalSize()

        length, heigth = 0, 0
        for i in range(len(self.pars)):
            if "Image Area Size X" in self.pars[i]:
                length = float(self.pars[i][2])  # /xsize
            elif "Image Area Size Y" in self.pars[i]:
                heigth = float(self.pars[i][2])  # /ysize

        return length, heigth

    def getOverscanSize(self, ccd=None):
        # ToDo: Select CCD
        length, heigth = 0, 0
        for i in range(len(self.pars)):
            if "Serial Pre-Masked" in self.pars[i]:
                length = int(self.pars[i][2])
            elif "Parallel Pre-Masked" in self.pars[i]:
                heigth = int(self.pars[i][2])

        return (length, heigth)

    def getReadoutModes(self):
        return self._readoutModes

    def supports(self, feature=None):
        return self._supports[feature]

    def _expose(self, imageRequest):

        shutterRequest = imageRequest['shutter']

        if shutterRequest == Shutter.OPEN:
            shutter = self.client.executeCommand(
                SetAcquisitionType(0))  # Light
        elif shutterRequest == Shutter.CLOSE:
            shutter = self.client.executeCommand(SetAcquisitionType(1))  # Dark
        elif shutterRequest == Shutter.LEAVE_AS_IS:  # As it was
            pass
        else:
            self.log.warning("Incorrect shutter option (%s)."
                             " Leaving shutter intact" % shutterRequest)

        if not imageRequest['binning']:
            srl_bin, prl_bin = 1, 1
        else:
            try:
                srl_bin, prl_bin = imageRequest['binning'].split('x')
            except:
                self.log.error('Could not determine binning. Using 1x1')
                srl_bin, prl_bin = 1, 1
                pass

                #  (mode, binning, top, left, width, height) =
                #  self._getReadoutModeInfo(imageRequest["binning"],
                # imageRequest["window"])

        self.client.executeCommand(
            SetAcquisitionMode(0))  # Chimera will always execute SINGLE FRAMES
        self.client.executeCommand(SetExposureTime(imageRequest["exptime"]))
        # self.client.executeCommand(SetNumberOfFrames(self["frames"]))
        # self.client.executeCommand(
        # SetCCDFormatParameters(0, 4096, srl_bin, 0, 4096, prl_bin))

        cmd = Acquire()
        cmd_to_send = cmd.command()
        # save time exposure started
        self.__lastFrameStart = dt.datetime.utcnow()
        self.lastFrameTemp = self.getTemperature()

        status = CameraStatus.OK

        # ok, start it
        self.exposeBegin(imageRequest)

        # send Acquire command
        bytes_sent = self.client.sk.send(cmd_to_send.toStruct())

        # check acknowledge
        ret = select.select([self.client.sk], [], [])
        if not ret[0]:
            raise SIException('No answer from camera')

        if ret[0][0] == self.client.sk:

            header = Packet()
            header_data = self.client.recv(len(header))
            header.fromStruct(header_data)

            if header.id == 129:
                ack = Ack()
                ack.fromStruct(
                    header_data + self.client.recv(header.length - len(header)))

                if not ack.accept:
                    raise AckException(
                        "Camera did not accepted command...")
            else:
                raise AckException(
                        "No acknowledge received from camera...")

        self.abort.clear()

        while self._isExposing():
            # [ABORT POINT]
            if self.abort.isSet():
                self.abortExposure()
                status = CameraStatus.ABORTED
                break

            # end exposure and returns
        return self._endExposure(imageRequest, status)

    def _endExposure(self, request, status):
        self.exposeComplete(request, status)
        return True

    def abortExposure(self, readout=True):
        # Send temination to camera
        self.client.executeCommand(TerminateAcquisition())
        # Readout
        # self._readout(imageRequest)

    def _isExposing(self):
        status = self.client.executeCommand(InquireAcquisitionStatus())
        return status.exp_done_percent < 100

    def _isReadingOut(self):
        status = self.client.executeCommand(InquireAcquisitionStatus())
        return status.readout_done_percent < 100

    def _readout(self, imageRequest):
        # self.readoutBegin(imageRequest)

        # TODO: get initial sizes from pars...
        # imgarray = N.zeros((4096, 4096), N.int32)
        #while not self.abort.isSet():
        status = CameraStatus.OK
        if self.abort.isSet():
            status = CameraStatus.ABORTED

        self.abort.clear()

        while self._isReadingOut():

            if self.abort.isSet():
                self.abortExposure(readout=False)
                status = CameraStatus.ABORTED
                break

        # Get orphan packet from Acquire command issue in _expose
        cmd = Acquire()

        while True:

            ret = select.select([self.client.sk], [], [])

            if not ret[0]:
                break

            if ret[0][0] == self.client.sk:

                header = Packet()
                header_data = self.client.recv(len(header))
                header.fromStruct(header_data)

                if header.id == 131:  # incoming data pkt
                    data = cmd.result()  # data structure as defined in data.py
                    data.fromStruct(
                        header_data + self.client.recv(header.length - len(header)))
                    #data.fromStruct (header_data + self.recv (header.length))
                    # logging.debug(data)
                    self.log.debug("data type is {}".format(data.data_type))
                    break

        (mode, binning, top, left, width, height) = self._getReadoutModeInfo(
            imageRequest["binning"], imageRequest["window"])

        # headers = {}
        # pix = N.zeros((height,width),dtype=N.uint16)

       # LAST ABORT POINT
        if self.abort.isSet():
            self.readoutComplete(None, CameraStatus.ABORTED)
            return None

        if not self["localhost"]:
            self.log.debug('Remote mode')

            serial_length, parallel_length, img_buffer = self.client.executeCommand(
                RetrieveImage(0))

            pix = N.array(img_buffer, dtype=N.uint16)

            if len(pix) != width * height:
                raise SIException("Wrong image size. Expected %i x %i (%i), got %i" % (width,
                                                                                     height,
                                                                                     width *
                                                                                     height,
                                                                                     len(pix)))

            pix = pix.reshape(width, height)
            pix.byteswap(True)

            header = self.client.executeCommand(GetImageHeader(1))

            headers = self._processHeader(header)

            headers["frame_start_time"] = self.__lastFrameStart
            headers["frame_temperature"] = self.getTemperature()
            headers["binning_factor"] = self._binning_factors[binning]

            proxy = self._saveImage(
                imageRequest, pix, headers)

        else:
            self.log.debug('Local mode. Saving file to %s'%(os.path.join(self["local_path"],self["local_filename"])))
            # Save the image to the local disk and read them instead. Should be much faster.
            # Todo: Get rid of "local_path" and "local_filename" and use temporary files
            self.client.executeCommand(SetSaveToFolderPath(self["local_path"]))
            self.client.executeCommand(SaveImage(self["local_filename"],'I16'))

            # Need to do this in order to fix the image header
            hdu = pyfits.open(os.path.join(self["local_path"],
                                              self["local_filename"]))

            # pix += hdu[0].data
            badcards = ['PG0_38',
                        'PG0_39',
                        'PG0_40',
                        'PG0_60',
                        'PG0_65']
            for card in badcards:
                self.log.debug('Removing card "%s" from header'%card)
                hdu[0].header.remove(card)

            # hdu[0].verify('silentfix+warn')

            # headers = dict(hdu[0].header)

            filename = ''

            if imageRequest:
                try:
                    filename = imageRequest["filename"]
                except KeyError:
                    if not filename:
                        raise TypeError("Invalid filename, you must pass filename=something"
                                        "or a valid ImageRequest object")

            filename = ImageUtil.makeFilename(filename)

            self.log.debug('Adding header information')

            hdu[0].header.set("DATE", ImageUtil.formatDate(dt.datetime.utcnow()), "date of file creation")
            hdu[0].header.set("AUTHOR", _chimera_name_, _chimera_long_description_)

            if imageRequest:
                for header in imageRequest.headers:
                    try:
                        hdu[0].header.set(*header)
                    except Exception, e:
                        log.warning("Couldn't add %s: %s" % (str(header), str(e)))

            (mode, binning, top, left,
            width, height) = self._getReadoutModeInfo(imageRequest["binning"],
                                                      imageRequest["window"])
            binFactor = self._binning_factors[binning]
            pix_w, pix_h = self.getPixelSize()

            if self["telescope_focal_length"] is not None:  # If there is no telescope_focal_length defined, don't store WCS
                focal_length = self["telescope_focal_length"]

                scale_x = binFactor * (((180 / N.pi) / focal_length) * (pix_w * 0.001))
                scale_y = binFactor * (((180 / N.pi) / focal_length) * (pix_h * 0.001))

                full_width, full_height = self.getPhysicalSize()
                CRPIX1 = ((int(full_width / 2.0)) - left) - 1
                CRPIX2 = ((int(full_height / 2.0)) - top) - 1

                # Adding WCS coordinates according to FITS standard.
                # Quick sheet: http://www.astro.iag.usp.br/~moser/notes/GAi_FITSimgs.html
                # http://adsabs.harvard.edu/abs/2002A%26A...395.1061G
                # http://adsabs.harvard.edu/abs/2002A%26A...395.1077C
                wcs = [("CRPIX1", CRPIX1, "coordinate system reference pixel"),
                    ("CRPIX2", CRPIX2, "coordinate system reference pixel"),
                    ("CD1_1",  scale_x * N.cos(self["rotation"]*N.pi/180.), "transformation matrix element (1,1)"),
                    ("CD1_2", -scale_y * N.sin(self["rotation"]*N.pi/180.), "transformation matrix element (1,2)"),
                    ("CD2_1", scale_x * N.sin(self["rotation"]*N.pi/180.), "transformation matrix element (2,1)"),
                    ("CD2_2", scale_y * N.cos(self["rotation"]*N.pi/180.), "transformation matrix element (2,2)")]
                for card in wcs:
                    hdu[0].header.set(*card)

            chimeraCards = [('DATE-OBS',
                     ImageUtil.formatDate(
                         self.__lastFrameStart),
                     'Date exposure started'),

                    ('CCD-TEMP', self.getTemperature(),
                     'CCD Temperature at Exposure Start [deg. C]'),

                    ("EXPTIME", float(imageRequest['exptime']) or 0.,
                     "exposure time in seconds"),

                    ('IMAGETYP', imageRequest['type'].strip(),
                     'Image type'),

                    ('SHUTTER', str(imageRequest['shutter']),
                     'Requested shutter state'),

                    ('INSTRUME', str(self['camera_model']), 'Name of instrument'),
                    ('CCD',    str(self['ccd_model']), 'CCD Model'),
                    ('CCD_DIMX', self.getPhysicalSize()
                     [0], 'CCD X Dimension Size'),
                    ('CCD_DIMY', self.getPhysicalSize()
                     [1], 'CCD Y Dimension Size'),
                    ('CCDPXSZX', self.getPixelSize()[0],
                     'CCD X Pixel Size [micrometer]'),
                    ('CCDPXSZY', self.getPixelSize()[1],
                     'CCD Y Pixel Size [micrometer]')]

            for card in chimeraCards:
                hdu[0].header.set(*card)

            self.log.debug('Writting new fits to disk')
            hdu.writeto(filename,output_verify='silentfix+warn')
            hdu.close()
            self.log.debug('Registering image and creating proxy')
            # register image on ImageServer
            server = getImageServer(self.getManager())
            img = Image.fromFile(filename)
            proxy = server.register(img)


        # I'll skip a call to saveImage and do all its work in here. A call to it was introducing a big overhead given
        # the large size of the data on our camera.
        # proxy = self._saveImage(
        #     imageRequest, pix, headers)
        self.log.debug('Readout complete')

        # # [ABORT POINT]
        # if self.abort.isSet():
        #     self.readoutComplete(None, CameraStatus.ABORTED)
        #     return None

        self.readoutComplete(proxy, CameraStatus.OK)
        return proxy

        # return

    def _processHeader(self, header):

        headers = {}
        n_headers = len(header) / 80

        for k in range(n_headers):
            line = header[k * 80:(k + 1) * 80]

            name = line[0:8].strip()
            rest = line[9:]

            if rest.find('/'):
                l = rest.split("/")
                if len(l) != 2:
                    continue

                value, comment = l[0], l[1]
                value = value.strip()
                comment = comment[0:comment.rfind(',')].strip()

                headers[name] = (value, comment)
            else:
                value = rest.strip()
                headers[name] = (value, "")

        return headers

    # def _getReadoutModeInfo(self, binning, window):
    #     """
    #     Check if the given binning and window could be used on the given CCD.
    #     Returns a tuple (modeId, binning, top, left, width, height)
    #     """
    #     # We need to override this method in order to handle the unrestricted
    #     # binnings of this camera.
    #     mode = None
    #
    #     if binning not in self._binnings:
    #         self._binnings.setdefault(binning,
    #                                   max(self._binnings.values()) + 1)
    #         self._binning_factors.setdefault(binning, max(
    #             self._binning_factors.values()) + 1)
    #
    #     mode = self.getReadoutModes()[self.getCurrentCCD()][binId]
    #
    #     left = 0
    #     top = 0
    #     width, height = mode.getSize()
    #
    #     if window is not None:
    #         try:
    #             xx, yy = window.split(",")
    #             xx = xx.strip()
    #             yy = yy.strip()
    #             x1, x2 = xx.split(":")
    #             y1, y2 = yy.split(":")
    #
    #             x1 = int(x1)
    #             x2 = int(x2)
    #             y1 = int(y1)
    #             y2 = int(y2)
    #
    #             left = min(x1, x2) - 1
    #             top = min(y1, y2) - 1
    #             width = (max(x1, x2) - min(x1, x2)) + 1
    #             height = (max(y1, y2) - min(y1, y2)) + 1
    #
    #             if left < 0 or left >= mode.width:
    #                 raise InvalidReadoutMode(
    #                     "Invalid subframe: left=%d, ccd width (in this "
    #                     "binning)=%d" % (left, mode.width))
    #
    #             if top < 0 or top >= mode.height:
    #                 raise InvalidReadoutMode(
    #                     "Invalid subframe: top=%d, ccd height (in this "
    #                     "binning)=%d" % (top, mode.height))
    #
    #             if width > mode.width:
    #                 raise InvalidReadoutMode(
    #                     "Invalid subframe: width=%d, ccd width (int this "
    #                     "binning)=%d" % (width, mode.width))
    #
    #             if height > mode.height:
    #                 raise InvalidReadoutMode(
    #                     "Invalid subframe: height=%d, ccd height (int this "
    #                     "binning)=%d" % (height, mode.height))
    #
    #         except ValueError:
    #             left = 0
    #             top = 0
    #             width, height = mode.getSize()
    #
    #     if not binning:
    #         binning = self.getBinnings().keys().pop(
    #             self.getBinnings().keys().index("1x1"))
    #
    #     return (mode, binning, top, left, width, height)


def getMetadata(self, request):
    return self.imghdr.items()
