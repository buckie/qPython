# 
#  Copyright (c) 2011-2014 Exxeleron GmbH
# 
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
# 
#    http://www.apache.org/licenses/LICENSE-2.0
# 
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
# 

import cStringIO
import struct
import sys

from qtype import *  # @UnusedWildImport
from qcollection import qlist, QList, QTemporalList, QDictionary, QTable, QKeyedTable, get_list_qtype
from qpython.qtemporal import QTemporal, to_raw_qtemporal


class QWriterException(Exception):
    '''
    Indicates an error raised during data serialization.
    '''
    pass



ENDIANESS = '\1' if sys.byteorder == 'little' else '\0'


class QWriter(object):
    '''
    Provides serialization to q IPC protocol.
    
    :Parameters:
     - `stream` (`socket` or `None`) - stream for data serialization
     -  `protocol_version` (`integer`) - version IPC protocol
    '''

    _writer_map = {}
    serialize = Mapper(_writer_map)


    def __init__(self, stream, protocol_version):
        self._stream = stream
        self.protocol_version = protocol_version


    def write(self, data, msg_type):
        '''Serializes and pushes single data object to a wrapped stream.
        
        :Parameters:
         - `data` - data to be serialized
         - `msg_type` (one of the constants defined in :class:`.MessageType`) -
           type of the message
        
        :returns: if wraped stream is ``None`` serialized data, 
                  otherwise ``None`` 
        '''
        self._buffer = cStringIO.StringIO()

        # header and placeholder for message size
        self._buffer.write('%s%s\0\0\0\0\0\0' % (ENDIANESS, chr(msg_type)))

        self._write(data)

        # update message size
        data_size = self._buffer.tell()
        self._buffer.seek(4)
        self._buffer.write(struct.pack('i', data_size))

        # write data to socket
        if self._stream:
            self._stream.send(self._buffer.getvalue())
        else:
            return self._buffer.getvalue()


    def _write(self, data):
        if data is None:
            self._write_null()
        else:
            if isinstance(data, Exception) or (type(data) == type and issubclass(data, Exception)):
                data_type = Exception
            else:
                data_type = type(data)

            writer = self._writer_map.get(data_type, None)

            if writer:
                writer(self, data)
            else:
                qtype = Q_TYPE.get(type(data), None)

                if qtype:
                    self._write_atom(data, qtype)
                else:
                    raise QWriterException('Unable to serialize type: %s' % data.__class__ if isinstance(data, object) else type(data))


    def _write_null(self):
        self._buffer.write(struct.pack('=bx', QNULL))


    @serialize(Exception)
    def _write_error(self, data):
        self._buffer.write(struct.pack('b', QERROR))
        if isinstance(data, Exception):
            msg = data.__class__.__name__
            if data.message:
                msg = data.message
        else:
            msg = data.__name__

        self._buffer.write(msg)
        self._buffer.write('\0')


    def _write_atom(self, data, qtype):
        try:
            self._buffer.write(struct.pack('b', qtype))
            fmt = STRUCT_MAP[qtype]
            self._buffer.write(struct.pack(fmt, data))
        except KeyError:
            raise QWriterException('Unable to serialize type: %s' % data.__class__ if isinstance(data, object) else type(data))


    @serialize(tuple, list)
    def _write_generic_list(self, data):
        self._buffer.write(struct.pack('=bxi', QGENERAL_LIST, len(data)))
        for element in data:
            self._write(element)


    @serialize(str)
    def _write_string(self, data):
        if len(data) == 1:
            self._write_atom(ord(data), QCHAR)
        else:
            self._buffer.write(struct.pack('=bxi', QSTRING, len(data)))
            self._buffer.write(data)


    @serialize(numpy.string_)
    def _write_symbol(self, data):
        self._buffer.write(struct.pack('=b', QSYMBOL))
        if data:
            self._buffer.write(data)
        self._buffer.write('\0')

        
    @serialize(uuid.UUID)
    def _write_guid(self, data):
        self._buffer.write(struct.pack('=b', QGUID))
        self._buffer.write(data.bytes)


    @serialize(QTemporal)
    def _write_temporal(self, data):
        try:
            if self.protocol_version < 1 and (data.meta.qtype == QTIMESPAN or data.meta.qtype == QTIMESTAMP):
                raise QWriterException('kdb+ protocol version violation: data type %s not supported pre kdb+ v2.6' % hex(data.meta.qtype))
            
            self._buffer.write(struct.pack('=b', data.meta.qtype))
            fmt = STRUCT_MAP[data.meta.qtype]
            self._buffer.write(struct.pack(fmt, to_raw_qtemporal(data.raw, data.meta.qtype)))
        except KeyError:
            raise QWriterException('Unable to serialize type: %s' % data.__class__ if isinstance(data, object) else type(data))


    @serialize(QLambda)
    def _write_lambda(self, data):
        if not data.parameters:
            self._buffer.write(struct.pack('=b', QLAMBDA))
            self._buffer.write('\0')
            self._write_string(data.expression)
        else:
            self._buffer.write(struct.pack('=bi', QLAMBDA_PART, len(data.parameters) + 1))
            self._buffer.write(struct.pack('=b', QLAMBDA))
            self._buffer.write('\0')
            self._write_string(data.expression)
            for parameter in data.parameters:
                self._write(parameter)


    @serialize(QDictionary, QKeyedTable)
    def _write_dictionary(self, data):
        self._buffer.write(struct.pack('=b', QDICTIONARY))
        self._write(data.keys)
        self._write(data.values)


    @serialize(QTable)
    def _write_table(self, data):
        self._buffer.write(struct.pack('=bxb', QTABLE, QDICTIONARY))
        self._write(qlist(numpy.array(data.dtype.names), qtype = QSYMBOL_LIST))
        self._buffer.write(struct.pack('=bxi', QGENERAL_LIST, len(data.dtype)))
        for column in data.dtype.names:
            self._write_list(data[column], data.meta[column])


    @serialize(numpy.ndarray, QList, QTemporalList)
    def _write_list(self, data, qtype = None):
        if qtype is not None:
            qtype = -abs(qtype)
        
        if qtype is None:
            qtype = get_list_qtype(data)
            
        if self.protocol_version < 1 and (data.meta.qtype == QTIMESPAN_LIST or data.meta.qtype == QTIMESTAMP_LIST):
            raise QWriterException('kdb+ protocol version violation: data type %s not supported pre kdb+ v2.6' % hex(data.meta.qtype))

        if qtype == QGENERAL_LIST:
            self._write_generic_list(data)
        elif qtype == QCHAR:
            self._write_string(data.tostring())
        else:
            self._buffer.write(struct.pack('=bxi', -qtype, len(data)))
            if qtype == QSYMBOL:
                for symbol in data:
                    self._buffer.write('%s\0' % (symbol or ''))
            elif qtype == QGUID:
                if self.protocol_version < 3:
                    raise QWriterException('kdb+ protocol version violation: Guid not supported pre kdb+ v3.0')
                
                for guid in data:
                    self._buffer.write(guid.bytes)
            else:
                self._buffer.write(data.tostring())

