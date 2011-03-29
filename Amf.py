from struct import pack, unpack
from time import time
from datetime import date
import types
import Bytes

# Amf Values
AMF_VALUE_NULL 			= 0x00
AMF_VALUE_NUMBER 		= 0x01
AMF_VALUE_BOOL 			= 0x02
AMF_VALUE_STRING 		= 0x03
AMF_VALUE_OBJECT 		= 0x04
AMF_VALUE_DATE 			= 0x05
AMF_VALUE_UNDEFINED 	= 0x06
	
# Amf Types
AMF_TYPE_NUMBER 		= 0x00
AMF_TYPE_BOOL 			= 0x01
AMF_TYPE_STRING 		= 0x02
AMF_TYPE_OBJECT 		= 0x03
AMF_TYPE_RESERVED 		= 0x04
AMF_TYPE_NULL 			= 0x05
AMF_TYPE_UNDEFINED 		= 0x06
AMF_TYPE_REFERENCE 		= 0x07
AMF_TYPE_ECMA_ARRAY 	= 0x08
AMF_TYPE_FIELD_END 		= 0x09
AMF_TYPE_STRICT_ARRAY 	= 0x0A
AMF_TYPE_DATE 			= 0x0B
AMF_TYPE_LONG_STRING 	= 0x0C
AMF_TYPE_UNSUPPORTED 	= 0x0D
AMF_TYPE_RECORDSET 		= 0x0E
AMF_TYPE_XML_DOCUMENT 	= 0x0F
AMF_TYPE_TYPE_OBJECT 	= 0x10
AMF_TYPE_AMF_PLUS 		= 0x11


def readType(input, type):
	# Number
	if type == AMF_TYPE_NUMBER:
		try:
			value = long(input.readDouble())
		except ValueError:
			value = 0	
		return (AMF_VALUE_NUMBER, value)		
	# Boolean
	elif type == AMF_TYPE_BOOL:
		return (AMF_VALUE_BOOL, input.readBool())		
	# String
	elif type == AMF_TYPE_STRING:
		return (AMF_VALUE_STRING, input.readString(input.readUInt16()))		
	# Object - Array
	elif (type == AMF_TYPE_OBJECT) or (type == AMF_TYPE_ECMA_ARRAY):
		fields = {}
		size = None
		if type == AMF_TYPE_ECMA_ARRAY:
			size = input.readUInt()
		while 1:
			b1 = input.readByte()
			b2 = input.readByte()
			name = input.readString((b1 << 8) | b2)
			field_type = input.readByte()
			if field_type == AMF_TYPE_FIELD_END:
				break
			fields[name] = readType(input, field_type)
		return (AMF_VALUE_OBJECT, fields, size)	
	# Reserved
	elif type == AMF_TYPE_RESERVED:
		raise Exception, "Not Implemented: Reserved"		
	# Null
	elif type == AMF_TYPE_NULL:
		return (AMF_VALUE_NULL,)		
	# Undefined
	elif type == AMF_TYPE_UNDEFINED:
		return (AMF_VALUE_UNDEFINED,)		
	# Reference
	elif type == AMF_TYPE_REFERENCE:
		raise Exception, "Not Implemented: Reference"		
	# Strict Array
	elif type == AMF_TYPE_STRICT_ARRAY:
		raise Exception, "Not Implemented: Strict Array"		
	# Date
	elif type == AMF_TYPE_DATE:
		time_ms = input.readDouble()
		time_zone_min = input.readUInt16()
		return (AMF_VALUE_DATE, date.fromtimestamp(time_ms + (time_zone_min * 60 * 1000.0)))		
	# Long String
	elif type == AMF_TYPE_LONG_STRING:
		return (AMF_VALUE_STRING, input.readString(input.readUInt()))		
	# Unsupported
	elif type == AMF_TYPE_UNSUPPORTED:
		raise Exception, "Unsupported Type"		
	# Recordset
	elif type == AMF_TYPE_RECORDSET:
		raise Exception, "Not Implemented: Recordset"		
	# XML Document
	elif type == AMF_TYPE_XML_DOCUMENT:
		raise Exception, "Not Implemented: Xml Document"		
	# Type Object
	elif type == AMF_TYPE_TYPE_OBJECT:
		raise Exception, "Not Implemented: Type Object"		
	# Amf Plus
	elif type == AMF_TYPE_AMF_PLUS:
		raise Exception, "Not Implemented: Amf Plus"	
	# Unknown
	else:
		raise Exception, "Unknown AMF Data Type: " + str(type)
		

#Input must be a BytesInput object		
def read(input):
	return readType(input, input.readByte())

#Input must be a BytesOutput object - Value is an Amf Value (tuple)
def write(output, value):
	type = value[0]

	# Null
	if type == AMF_VALUE_NULL:
		output.writeByte(AMF_TYPE_NULL)	
	# Number
	elif type == AMF_VALUE_NUMBER:
		output.writeByte(AMF_TYPE_NUMBER)
		output.writeDouble(value[1])		
	# Boolean
	elif type == AMF_VALUE_BOOL:
		output.writeByte(AMF_TYPE_BOOL)
		output.writeBool(value[1])		
	# String
	elif type == AMF_VALUE_STRING:
		size = len(value[1])
		if size <= 0xFFFF:
			output.writeByte(AMF_TYPE_STRING)
			output.writeUInt16(size)
		else:
			output.writeByte(AMF_TYPE_LONG_STRING)
			output.writeUInt(size)
		output.writeString(value[1])		
	# Object
	elif type == AMF_VALUE_OBJECT:
		if value[2] == None:
			output.writeByte(AMF_TYPE_OBJECT)
		else:
			output.writeByte(AMF_TYPE_ECMA_ARRAY)
			output.writeUInt(value[2])
		for name, field in value[1].items():
			output.writeUInt16(len(name))
			output.writeString(name)
			write(output, field)
		output.write(pack('>3B', 0x00, 0x00, AMF_TYPE_FIELD_END)) #VERIFICATION		
	# Date
	elif type == AMF_VALUE_DATE:
		output.writeDouble(time.time())
		output.writeUInt16(0) #Time zone lost in the process		
	# Undefined
	elif type == AMF_VALUE_UNDEFINED:
		output.writeByte(AMF_TYPE_UNDEFINED)
		
def encode(value):
	value_type = type(value)
	# Null
	if value_type == types.NoneType:
		return (AMF_VALUE_NULL,)
	# Number
	elif value_type in (types.IntType, types.LongType, types.FloatType):
		return (AMF_VALUE_NUMBER, value)
	# Boolean
	elif value_type == types.BooleanType:
		return (AMF_VALUE_BOOL, value)
	# String
	elif value_type == types.StringType:
		return (AMF_VALUE_STRING, value)
	# Object
	elif value_type == types.DictType:
		fields = {}
		for name, field in value.items():
			fields[name] = encode(field)
		return (AMF_VALUE_OBJECT, fields, None)
	# Unsupported
	else:
		raise Exception, "Can't encode %s" % str(value)
		
def number(value):
	if (value is not None) and (value[0] == AMF_VALUE_NUMBER):
		return value[1]
	return None
	
def bool(value):
	if (value is not None) and (value[0] == AMF_VALUE_BOOL):
		return value[1]
	return None

def string(value):
	if (value is not None) and (value[0] == AMF_VALUE_STRING):
		return value[1]
	return None
	
def object(value):
	if (value is not None) and (value[0] == AMF_VALUE_OBJECT):
		return value[1]
	return None
	
def isnull(value):
	return ((value is not None) and ((value[0] == AMF_VALUE_NULL) or (value[0] == AMF_VALUE_UNDEFINED)))
		
