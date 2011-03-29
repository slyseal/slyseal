import socket
from time import time, localtime, strftime
from errno import EALREADY, EINPROGRESS, EWOULDBLOCK, ECONNRESET, \
     ENOTCONN, ESHUTDOWN, EINTR, EISCONN, EBADF, ECONNABORTED, errorcode
	 
from Handler import Handler


class Client(object):
	MESSAGE_HEADER_SIZE		= 1
	READ_BUFFER_SIZE		= (1 << 12) # 4KB
	MAX_READ_BUFFER_SIZE	= (1 << 16) # 64 KB
	WRITE_BUFFER_SIZE		= (1 << 18) # 256 KB 2048
	BLOCKING_SIZE			= (1 << 17) # 128 KB 1024
	
	IDLE_TIMEOUT 			= 600 # 10 minutes
	
	def __init__(self, socket, handler):
		self.socket = socket
		self.address = "%s:%d" % socket.getpeername()
		self.handler = handler
		self.descriptor = socket.fileno()
		
		self.read_buffer = ''
		self.write_buffer = ''
		
		self.last_activity = time()
		
		self.running = False
		
		self.init()
		
		self.running = True
		
		#print("%s - Connection" % self.address) #DEBUG
		self.log("%s - Connection" % self.address)
		
		#self.f = open("data.raw", "wb") #DEBUG
		
	def disconnect(self):
		self.running = False
		try:
			self.socket.shutdown(scoket.SHUT_RDWR)
		except:
			pass
		self.handler.disconnect(self)
		
		self.log("%s - Disconnection" % self.address) #DEBUG
		
	def close(self):
		self.exit()
		
		self.log("%s - Closing" % self.address) #DEBUG
		
		self.running = None
		self.socket = None
		self.address = None
		self.handler = None
		self.read_buffer = None
		self.write_buffer = None
		self.last_activity = None
		
		#self.f.close() #DEBUG
		
		
					
	def read(self):
		if self.running and (self.socket is not None):
			try:
				data = self.socket.recv(self.READ_BUFFER_SIZE)
				if not data:
					self.disconnect()
					return
			except socket.error, why:
				if why.args[0] in (ECONNRESET, ENOTCONN, ESHUTDOWN, ECONNABORTED):
					self.disconnect()
					return
				else:
					raise
					
			self.read_buffer += data
			
			if len(self.read_buffer) > self.MAX_READ_BUFFER_SIZE:
				raise Exception, "Max read buffer size reached"
				
	def write(self):
		if self.running and (self.socket is not None) and (len(self.write_buffer) > 0):
			try:
				result = self.socket.send(self.write_buffer)
			except socket.error, why:
				if why.args[0] == EWOULDBLOCK:
					return
				elif why.args[0] in (ECONNRESET, ENOTCONN, ESHUTDOWN, ECONNABORTED):
					self.disconnect()
					return
				else:
					raise
			self.write_buffer = self.write_buffer[result:]
			
			self.last_activity = time()
				
				
	def process(self):
		if self.running and (len(self.read_buffer) > 0):
			pos = 0
			length = len(self.read_buffer)
			while length > 0:
				message = self.readMessage(buffer(self.read_buffer, pos))
				if message is None:
					break
				else:
					pos += message[0]
					length -= message[0]
					
					if message[1] is not None:
						self.processMessage(message[1])
			
			if pos > 0:
				self.read_buffer = self.read_buffer[pos:]
		
			self.last_activity = time()
			
	def update(self):
		if not self.running:
			return
		if (time() - self.last_activity) > self.IDLE_TIMEOUT:
			#self.disconnect()
			return
		self.process()
		self.refresh()
			
			
	def blocking(self):
		return (len(self.write_buffer) > self.BLOCKING_SIZE)

	# API
	def init(self):
		pass
	
	def exit(self):
		pass
		
	def processMessage(self, message):
		pass
		
	def readMessage(self, buffer):
		return (0, None)
				
	def writeMessage(self, data):
		if data is not None:
			self.write_buffer += data
			#self.f.write(data) #DEBUG
		return not self.blocking()
		
	def refresh(self):
		pass
		
	def log(self, msg):
		print("[%s] INFO\t%s" % (strftime("%Y/%m/%d %H:%M:%S", localtime()), msg))
				