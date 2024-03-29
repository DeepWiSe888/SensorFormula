import struct
#import sfpy
import numpy as np


'''
/* SENSOR_TYPE_DEFINE */
#define RADAR     (1)
#define LIDAR     (2)      //(1<<1)
#define THERMAL   (4)      //(1<<2)
#define CAMERA    (8)      //(1<<3)

/* DATA_TYPE_DEFINE */
#define DATA_TYPE_UNDEFINED     (0)
#define DATA_TYPE_ADC           (1)
#define DATA_TYPE_IQ            (2)
#define DATA_TYPE_IMAGE         (3)
#define DATA_TYPE_POINTCLOUD    (4)
'''


class umat(object):
    def __init__(self):
        self.RADAR = 1
        self.LIDAR = 2
        self.THERMAL = 4
        self.CAMERA = 8
        self.sensor_type = 1
        self.data_type = 0
        self.timestamp = 0
        self.timestamp_ms = 0
        self.fps = 0
        self.dims = None  # np array
        self.data = None  # np array

    # def __init__(self, buf_bytes=None):
    #    self.RADAR = 1
    #    self.LIDAR = 2
    #    self.THERMAL = 4
    #    self.CAMERA = 8
    #    self.load_buf(self, buf_bytes)

    # note : buf_bytes contains a whole frame packet, no need seeking for frame head.
    def load_buf(self, buf_bytes):
        # title size 64: char: '#sf01#umat#....'
        # label size 20: ver(i8), sensor_type(i8), data_type(i8), floatsize(i8), dims(i32*4)
        self.sensor_type, = struct.unpack("B", buf_bytes[65:66])
        self.data_type, = struct.unpack("B", buf_bytes[66:67])
        read_dims = struct.unpack("4i", buf_bytes[68:68+4*4])
        fdatacnt = 2
        self.dims = np.array(read_dims)
        self.dims[self.dims == 0] = 1
        for a in self.dims:
            fdatacnt = fdatacnt*a
        # timestamp size 8 : secs(i32), milli-sec(i32)
        self.timestamp, self.timestamp_ms = struct.unpack("ii", buf_bytes[84:84+8])
        # data : complex array
        fdata = struct.unpack("{}f".format(fdatacnt), buf_bytes[92:])
        f = np.array(fdata)
        iq = f[0::2] + 1j*f[1::2]
        iq_dims = iq.reshape(self.dims)
        iq_squeeze = iq_dims.squeeze()
        self.data = iq_squeeze

    def dump_buf(self):
        # title size 64
        title_str = '#sf01#umat'+' '*64
        # buf_title = struct.pack('s', title_str)
        buf_title = bytes(title_str[0:64], encoding='ascii')
        # label size 20: ver(i8), sensor_type(i8), data_type(i8), floatsize(i8), dims(i32*4)
        tmp_dims = np.zeros(4, dtype=np.int32)
        tmp_dims[0:len(self.dims)] = self.dims
        buf_label = struct.pack('bbbbiiii', 1, self.sensor_type, self.data_type, 4, tmp_dims[0], tmp_dims[1], tmp_dims[2], tmp_dims[3])
        # timestamp size 8
        buf_time = struct.pack('ii', self.timestamp, self.timestamp_ms)
        # data [i,q] * cnt
        iqdatacnt = 1
        for a in self.dims:
            iqdatacnt = iqdatacnt*a
        fdatacnt = iqdatacnt*2
        tmp_iq = self.data.reshape(iqdatacnt)
        tmp_fdata = np.zeros(fdatacnt, dtype=np.float)
        tmp_fdata[0::2] = np.real(tmp_iq)
        tmp_fdata[1::2] = np.imag(tmp_iq)
        buf_data = struct.pack("{}f".format(fdatacnt), *tmp_fdata)
        buf = buf_title+buf_label+buf_time+buf_data
        return buf

    def create_mimo(self, ntx, nrx, bins, fps):
        self.dims = [ntx, nrx, bins]
        self.data = None

    def create_siso(self, bins, fps):
        self.dims = [bins]
        self.data = None


def load_file(filename):
    f = open(filename, 'rb')
    buf = f.read()
    m = umat()
    m.load_buf(buf)
    f.close()
    return m
