from io import BytesIO
from struct import pack, unpack
import warnings
warnings.simplefilter('error')

class BytesInput(object):
	def __init__(self, bytes = None, bigendian = True):
		self.endianess = ("<", ">")[bigendian]
		self.buffer = BytesIO(bytes)

	def setEndianess(self, big = True):
		if big:
			self.endianess = ">"
		else:
			self.endianess = "<"
			
	def readByte(self):
		return unpack("%sB" % self.endianess, self.buffer.read(1))[0]
		
	def readInt(self):
		return unpack("%si" % self.endianess, self.buffer.read(4))[0]

	def readUInt(self):
		return unpack("%sI" % self.endianess, self.buffer.read(4))[0]
		
	def readLong(self):
		return unpack("%sl" % self.endianess, self.buffer.read(4))[0]

	def readULong(self):
		return unpack("%sL" % self.endianess, self.buffer.read(4))[0]
			
	def readFloat(self):
		return unpack("%sf" % self.endianess, self.buffer.read(4))[0]

	def readDouble(self):
		return unpack("%sd" % self.endianess, self.buffer.read(8))[0]
		
	def readInt8(self):
		return unpack("%sb" % self.endianess, self.buffer.read(1))[0]
		
	def readUInt8(self):
		return unpack("%sB" % self.endianess, self.buffer.read(1))[0]
		
	def readInt16(self):
		return unpack("%sh" % self.endianess, self.buffer.read(2))[0]
		
	def readUInt16(self):
		return unpack("%sH" % self.endianess, self.buffer.read(2))[0]
		
	def readInt24(self):
		n = self.readUInt24()
		if (n & 0x800000) != 0:
			return n - 0x1000000
		return n
		
	def readUInt24(self):
		bytes = unpack("%s3B" % self.endianess, self.buffer.read(3))
		if self.endianess == ">":
			return (bytes[2] | (bytes[1] << 8) | (bytes[0] << 16))
		else:
			return (bytes[0] | (bytes[1] << 8) | (bytes[2] << 16))
			
	def readInt32(self):
		return self.readInt()
		
	def readUInt32(self):
		return self.readUInt()
		
	def readInt64(self):
		return unpack("%sq" % self.endianess, self.buffer.read(8))[0]
		
	def readUInt64(self):
		return unpack("%sQ" % self.endianess, self.buffer.read(8))[0]
		
	def readBool(self):
		return unpack("%s?" % self.endianess, self.buffer.read(1))[0]
		
	def readString(self, number):
		return self.buffer.read(number)
		
	def read(self, number = None):
		return self.buffer.read(number)
		
	def seek(self, offset, whence = 0):
		self.buffer.seek(offset, whence)
		
	def tell(self):
		return self.buffer.tell()
		
	def getByte(self, offset = 0):
		old_offset = self.tell()
		self.seek(offset)
		byte = self.buffer.read(1)
		self.seek(old_offset)
	
		return unpack("%sB" % self.endianess, byte)[0]
			

		
class BytesOutput(object):
	def __init__(self, bigendian = True):
		self.endianess = ("<", ">")[bigendian]
		self.buffer = BytesIO()
		
	def setEndianess(self, big = True):
		if big:
			self.endianess = ">"
		else:
			self.endianess = "<"
			
	def getBytes(self):
		return self.buffer.getvalue()
		
	def writeByte(self, value):
		self.buffer.write(pack("%sB" % self.endianess, value))
		
	def writeInt(self, value):
		self.buffer.write(pack("%si" % self.endianess, value))

	def writeUInt(self, value):
		self.buffer.write(pack("%sI" % self.endianess, value))
		
	def writeLong(self, value):
		self.buffer.write(pack("%sl" % self.endianess, value))

	def writeULong(self, value):
		self.buffer.write(pack("%sL" % self.endianess, value))
			
	def writeFloat(self, value):
		self.buffer.write(pack("%sf" % self.endianess, value))

	def writeDouble(self, value):
		self.buffer.write(pack("%sd" % self.endianess, value))
		
	def writeInt8(self, value):
		self.buffer.write(pack("%sb" % self.endianess, value))
		
	def writeUInt8(self, value):
		self.buffer.write(pack("%sB" % self.endianess, value))
		
	def writeInt16(self, value):
		self.buffer.write(pack("%sh" % self.endianess, value))
		
	def writeUInt16(self, value):
		self.buffer.write(pack("%sH" % self.endianess, value))
		
	def writeInt24(self, value):
		self.writeUInt24(value & 0xFFFFFF)
		
	def writeUInt24(self, value):
		if self.endianess == ">":
			bytes = ((value >> 16), ((value >> 8) & 0xFF), (value & 0xFF))
		else:
			bytes = ((value & 0xFF), ((value >> 8) & 0xFF), (value >> 16))
		self.buffer.write(pack("%s3B" % self.endianess, bytes[0], bytes[1], bytes[2]))
		
	def writeInt32(self, value):
		self.writeInt()
		
	def writeUInt32(self, value):
		self.writeUInt()
		
	def writeInt64(self, value):
		self.buffer.write(pack("%sq" % self.endianess, value))
		
	def writeUInt64(self, value):
		self.buffer.write(pack("%sQ" % self.endianess, value))
		
	def writeBool(self, value):
		self.buffer.write(pack("%s?" % self.endianess, value))
		
	def writeString(self, value):
		self.buffer.write(value)
		
	def write(self, value):
		self.buffer.write(value)
		
	def writeBytes(self, data, start, length):
		bytes = BytesInput(data)
		bytes.seek(start, 0)
		while length > 0:
			self.writeByte(bytes.readByte())
			length -= 1
		