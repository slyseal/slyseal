"""
RtmpPacket:
	0x01 -> ChunkSize	# size:Integer
	0x03 -> BytesRead	# nb_bytes:Integer
	0x04 -> Control		# stream_id:Integer, control:RtmpControl
	0x05 -> ServerBW	# timestamp:Integer
	0x06 -> ClientBW	# timestamp:Integer
	0x08 -> Audio		# data:Bytes
	0x09 -> Video		# data:Bytes
	0x12 -> Notify		# data:Bytes
	0x13 -> Shared		# data:SharedObjectData
	0x14 -> Command		# name:String, id:Integer, args:Array<AmfValue>
	0xFF -> Unknown		# type:Integer, body:Bytes
	
RtmpControl:
	0x00 -> Clear
	0x01 -> ClearPlay
	0x03 -> ClientBuffer	# value:Integer
	0x04 -> Reset
	0x06 -> Ping			# value:Integer
	0x07 -> Pong			# value:Integer
	0xFF -> Unknown			# type:Integer, ?value1:Integer, ?value2:Integer
	
RtmpHeader:
	channel_id
	timestamp
	size
	type
	stream_id
	
RtmpChannel:
	header
	buffer
	size
"""

from Bytes import BytesInput, BytesOutput
import Amf
from time import time as getTime


# Rtmp Types
RTMP_TYPE_CHUNK_SIZE 	= 0x01
RTMP_TYPE_BYTES_READ 	= 0x03
RTMP_TYPE_CONTROL 		= 0x04
RTMP_TYPE_SERVER_BW 	= 0x05
RTMP_TYPE_CLIENT_BW 	= 0x06
RTMP_TYPE_AUDIO 		= 0x08
RTMP_TYPE_VIDEO 		= 0x09
RTMP_TYPE_NOTIFY 		= 0x12
RTMP_TYPE_SHARED 		= 0x13
RTMP_TYPE_COMMAND 		= 0x14
RTMP_TYPE_UNKNOWN		= 0xFF
	
# Rtmp Control
RTMP_CONTROL_CLEAR 			= 0x00
RTMP_CONTROL_CLEAR_PLAY 	= 0x01
RTMP_CONTROL_CLIENT_BUFFER 	= 0x03
RTMP_CONTROL_RESET 			= 0x04
RTMP_CONTROL_PING		 	= 0x06
RTMP_CONTROL_PONG 			= 0x07
RTMP_CONTROL_UNKNOWN		= 0xFF

RTMP_CONTROL_SIZES = (0, 0, None, 4, 0, 4, 4)

def headerSizeFromByte(size):
	size = size >> 6
	if size == 0x00: return 12
	elif size == 0x01: return 8
	elif size == 0x02: return 4
	elif size == 0x03: return 1

def headerSizeToByte(size):
	if size == 12: return 0x00
	elif size == 8: return 0x01
	elif size == 4: return 0x02
	elif size == 1: return 0x03
	
class Rtmp:
	def __init__(self):
		self.read_chunk_size = 128
		self.write_chunk_size = 128
		self.headers = {}
		self.channels = {}
		
	def setChunkSize(self, size):
		self.read_chunk_size = size
		self.write_chunk_size = size
		
	def getChunkSize(self):
		return self.write_chunk_size
		
	def getLastHeader(self, channel_id):
		header = self.headers.get(channel_id)
		if header is None:
			header = [channel_id, None, None, None, None]
			self.headers[channel_id] = header
		return header
		
	def readHeader(self, input):
		header_type = input.readByte()
		header_size = headerSizeFromByte(header_type)
		channel_id = header_type & 0x3F
		last_header = self.getLastHeader(channel_id)
		if header_size >= 4:
			last_header[1] = input.readUInt24()
		if header_size >= 8:
			last_header[2] = input.readUInt24()
			last_header[3] = input.readByte()
		if header_size >= 12:
			input.setEndianess(False)
			last_header[4] = input.readUInt()
			input.setEndianess(True)
		return last_header
		
	def makeHeader(self, header):
		output = BytesOutput(True)
		
		header_size = 1
		if header[4] is not None:
			header_size = 12
		elif header[3] is not None:
			header_size = 8
		elif header[1] is not None:
			header_size = 4
			
		output.writeByte(header[0] | (headerSizeToByte(header_size) << 6))
		
		if header_size >= 4:
			output.writeUInt24(header[1])
		if header_size >= 8:
			output.writeUInt24(header[2])
			output.writeByte(header[3])
		if (header_size >= 12):
			output.setEndianess(False)
			output.writeUInt(header[4])
			output.setEndianess(True)
		
		return output.getBytes()
		
	def make(self, channel_id, packet, timestamp = 0, stream_id = 0):
		type = packet[0]
		header = [channel_id, timestamp, None, type, stream_id]
		
		data = BytesOutput(True)
		
		# 0x01 - Chunk Size
		if type == RTMP_TYPE_CHUNK_SIZE:
			data.writeUInt(packet[1])
			
		# 0x03 - Bytes Read
		elif type == RTMP_TYPE_BYTES_READ:
			data.writeUInt(packet[1])
			
		# 0x04 - Control
		elif type == RTMP_TYPE_CONTROL:
			control_stream_id, control = packet[1]
			control_type = control[0]
			value1 = None
			value2 = None
			
			# 0x00 - Clear
			if control_type == RTMP_CONTROL_CLEAR:
				pass
				
			# 0x01 - Clear Play
			elif control_type == RTMP_CONTROL_CLEAR_PLAY:
				pass
				
			# 0x03 - Client Buffer
			elif control_type == RTMP_CONTROL_CLIENT_BUFFER:
				value1 = control[1]
				
			# 0x04 - Reset
			elif control_type == RTMP_CONTROL_RESET:
				pass
				
			# 0x06 - Ping
			elif control_type == RTMP_CONTROL_PING:
				value1 = control[1]
				
			# 0x07 - Pong
			elif control_type == RTMP_CONTROL_PONG:
				value1 = control[1]
				
			# Unknown
			elif control_type == RTMP_CONTROL_UNKNOWN:
				control_type = control[1]
				value1 = control[2]
				value2 = control[3]

			data.writeUInt16(control_type)
			data.writeUInt(control_stream_id)
			
			if value1 is not None:
				data.writeUInt(value1)
			if value2 is not None:
				data.writeUInt(value2)
				
		# 0x05 - Server BW
		elif type == RTMP_TYPE_SERVER_BW:
			data.writeUInt(0x002625A0)
			
		# 0x06 - Client BW
		elif type == RTMP_TYPE_CLIENT_BW:
			data.writeUInt(0x002625A0)
			data.writeByte(0x02)
			
		# 0x08 - Audio
		elif type == RTMP_TYPE_AUDIO:
			data.write(packet[1])
			
		# 0x09 - Video
		elif type == RTMP_TYPE_VIDEO:
			data.write(packet[1])
			
		# 0x12 - Notify
		elif type == RTMP_TYPE_NOTIFY:
			data.writeString(packet[1])
			
		# 0x13 - Shared
		elif type == RTMP_TYPE_SHARED:
			raise Exception, "Not implemented" #TODO -> Shared Object functions
			
		# 0x14 - Command
		elif type == RTMP_TYPE_COMMAND:
			name, id, args = packet[1]
			Amf.write(data, (3, name)) #Command name
			Amf.write(data, (1, id)) #Command id
			for arg in args: # Args (Amf Values)
				Amf.write(data, arg)
				
		# Unknown
		elif type == RTMP_TYPE_UNKNOWN: 
			type, body = packet[1]
			header[4] = type
			data.write(body)
			
		# Other
		else:
			header[4] = None
			
		data = data.getBytes()
		length = len(data)
		header[2] = length

		
		output = BytesOutput(True)
		
		output.write(self.makeHeader(header))
		if length > 0:
			pos = self.write_chunk_size
			if length <= pos:
				output.write(data)
			else:
				output.write(buffer(data, 0, pos))
				length -= pos
				while length > 0:
					output.writeByte(header[0] | (headerSizeToByte(1) << 6))
					n = (length, self.write_chunk_size)[length > self.write_chunk_size]
					output.write(buffer(data, pos, n))
					pos += n
					length -= n

		return output.getBytes()
		
	def processBody(self, header, body):
		type = header[3]
		
		input = BytesInput(bytes=body, bigendian=True)
		
		# 0x01 - Chunk Size
		if type == RTMP_TYPE_CHUNK_SIZE:
			self.read_chunk_size = input.readUInt()
			return None
			
		# 0x03 - Bytes Read
		elif type == RTMP_TYPE_BYTES_READ:
			return (RTMP_TYPE_BYTES_READ, input.readUInt())
			
		# 0x04 - Control
		elif type == RTMP_TYPE_CONTROL:
			control = None
			control_type = input.readUInt16()
			control_stream_id = input.readUInt()
			
			body_size = RTMP_CONTROL_SIZES[control_type]
			body_length = len(body)
			
			if (body_size is not None) and (body_length != (body_size + 6)):
				raise Exception, "Invalid control size(%s, %s)" % (type, len(body))
				
			# 0x00 - Clear
			if control_type == RTMP_CONTROL_CLEAR:
				control = (RTMP_CONTROL_CLEAR,)
				
			# 0x01 - Clear Play
			elif control_type == RTMP_CONTROL_CLEAR_PLAY:
				control = (RTMP_CONTROL_CLEAR_PLAY,)
				
			# 0x03 - Client Buffer
			elif control_type == RTMP_CONTROL_CLIENT_BUFFER:
				control = (RTMP_CONTROL_CLIENT_BUFFER, input.readUInt())
				
			# 0x04 - Reset
			elif control_type == RTMP_CONTROL_RESET:
				control = (RTMP_CONTROL_RESET,)
				
			# 0x06 - Ping
			elif control_type == RTMP_CONTROL_PING:
				control = (RTMP_CONTROL_PING, input.readUInt())
				
			# 0x07 - Pong
			elif control_type == RTMP_CONTROL_PONG:
				control = (RTMP_CONTROL_PONG, input.readUInt()) #TODO - verify second value (, input.readUInt())
			
			# Unknown
			else:
				if (body_length != 6) and (body_length != 10) and (body_length != 14):
					raise Exception, "Invalid control size(%s, %s)" % (type, len(body))
					
				value1 = None
				value2 = None
				
				if body_length > 6:
					value1 = input.readUInt()
				if body_length > 10:
					value2 = input.readUInt()
					
				control = (RTMP_CONTROL_UNKNOWN, control_type, value1, value2)
			return (RTMP_TYPE_CONTROL, (control_stream_id, control))
		
		# 0x05 - Server BW
		elif type == RTMP_TYPE_SERVER_BW:
			return (RTMP_TYPE_SERVER_BW, header[1])
		
		# 0x06 - Client BW
		elif type == RTMP_TYPE_CLIENT_BW:
			return (RTMP_TYPE_CLIENT_BW, header[1])
		
		# 0x08 - Audio
		elif type == RTMP_TYPE_AUDIO:
			return (RTMP_TYPE_AUDIO, body)
		
		# 0x09 - Video
		elif type == RTMP_TYPE_VIDEO:
			return (RTMP_TYPE_VIDEO, body)
		
		# 0x12 - Notify
		elif type == RTMP_TYPE_NOTIFY:
			return (RTMP_TYPE_NOTIFY, body)
		
		# 0x13 - Shared
		elif type == RTMP_TYPE_SHARED:
			raise Exception, "Not implemented" #TODO -> Shared Object functions
		
		# 0x14 - Command
		elif type == RTMP_TYPE_COMMAND:
			amf_type, name = Amf.read(input)
			if amf_type != Amf.AMF_VALUE_STRING:
				raise Exception, "Invalid Command Name"
				
			amf_type, command_id = Amf.read(input)
			if amf_type != Amf.AMF_VALUE_NUMBER:
				raise Exception, "Invalid Command ID"
				
			args = []
			while 1:
				try:
					byte = input.readByte()
				except:
					break
				else:
					if byte is not None:
						args.append(Amf.readType(input, byte))
					else:
						break
			return (RTMP_TYPE_COMMAND, (name, command_id, args))
		
		# Unknown
		else:
			return (RTMP_TYPE_UNKNOWN, (type, body))
			
			
	def bodyLength(self, header, read):
		chunk_size = (self.write_chunk_size, self.read_chunk_size)[read == True]
		channel = self.channels.get(header[0])
		if channel is None:
			if header[2] < chunk_size:
				return header[2]
			else:
				return chunk_size
		else:
			if channel[2] < chunk_size:
				return channel[2]
			else:
				return chunk_size		

	def readPacket(self, header, input):
		channel = self.channels.get(header[0])
		if channel is None:
			header_size = header[2]
			if header_size < self.read_chunk_size:
				return self.processBody(header, input.read(header_size))
			buffer = BytesOutput(True)
			buffer.write(input.read(self.read_chunk_size))
			self.channels[header[0]] = [header, buffer, header_size - self.read_chunk_size]
		else:
			channel_header = channel[0]
			if header[1] != channel_header[1]:
				raise Exception, "Timestamp Changed"
			if header[4] != channel_header[4]:
				raise Exception, "Stream Id Changed"
			if header[3] != channel_header[3]:
				raise Exception, "Type Changed"
			if header[2] != channel_header[2]:
				raise Exception, "Size Changed"
			if channel[2] > self.read_chunk_size:
				channel[1].write(input.read(self.read_chunk_size))
				channel[2] -= self.read_chunk_size
			else:
				channel[1].write(input.read(channel[2]))
				del self.channels[header[0]]
				return self.processBody(channel[0], channel[1].getBytes())
				
		return None
			
		