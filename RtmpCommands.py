import Amf

ARG_TYPE_NULL 		= 0x00
ARG_TYPE_NUMBER 	= 0x01
ARG_TYPE_BOOL 		= 0x02
ARG_TYPE_STRING 	= 0x03
ARG_TYPE_OBJECT 	= 0x04
ARG_TYPE_OPTIONAL 	= 0x80	
	
class RtmpCommands(object):
	def __init__(self):
		self.commands = {}
		
	def register(self, name, command, types):
		self.commands[name] = (command, types)
		
	def has(self, name):
		return (name in self.commands)
		
	def checkArg(self, type, arg):
		if (type == ARG_TYPE_NULL):
			if Amf.isnull(arg):
				return ARG_TYPE_NULL
			else:
				return None
		elif type == ARG_TYPE_NUMBER:
			return Amf.number(arg)
		elif type == ARG_TYPE_BOOL:
			return Amf.bool(arg)
		elif type == ARG_TYPE_STRING:
			return Amf.string(arg)
		elif type == ARG_TYPE_OBJECT:
			return Amf.object(arg)
		elif (type & 0xF0) == ARG_TYPE_OPTIONAL:
			if Amf.isnull(arg):
				return ARG_TYPE_NULL
			else:
				return self.checkArg(type & 0x0F, arg)
		
	def checkArgs(self, types, args):
		result = []
		len_types = len(types)
		len_args = len(args)
		
		if len_args > len_types:
			return None
		
		for i in xrange(len_args):
			arg = self.checkArg(types[i], args[i])
			if arg is None:
				return None
			elif arg == ARG_TYPE_NULL:
				arg = None
			result.append(arg)
			
		for i in xrange(len_args, len_types):
			if (types[i] & 0xF0) != ARG_TYPE_OPTIONAL:
				return None
			else:
				result.append(None)
		
		return result
	
	def execute(self, name, info, args):
		if name not in self.commands:
			return False
			
		command, types = self.commands[name]
			
		valid_args = self.checkArgs(types, args)
		if valid_args is None:
			return False
		
		command(info, *valid_args)
		return True