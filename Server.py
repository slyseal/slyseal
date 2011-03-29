import socket, select, sys, traceback
from urlparse import urlsplit
from time import time, localtime, strftime
from Client import Client
from Handler import Handler

class Server(object):
	MAX_HANDLERS	= 10
	MAX_CLIENTS		= 1000 # Max Clients per Handler
	LISTEN_COUNT	= 10
	
	def __init__(self):
		self.socket = None
		#self.loadAllowedDomains()
		
	def start(self, address):
		try:
			self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			self.socket.bind(address)
			self.socket.listen(self.LISTEN_COUNT)
			
			self.handlers = [Handler(self) for i in range(self.MAX_HANDLERS)]
		
			self.loop()
		except:
			self.logError()
			
		self.exit(-1)
	
	def loop(self):
		while 1:
			try:
				r, w, e = select.select([self.socket], [], [self.socket], 0.01)
				if len(e) > 0:
					break
				elif len(r) > 0:
					self.handleSocket(*self.socket.accept())
			except:
				self.logError()
				break
				
	def handleSocket(self, socket, address):
		socket.setblocking(0)
		
		clients, handler = min([(len(handler.clients), handler) for handler in self.handlers])
		
		if clients < self.MAX_CLIENTS:
			print("PEER [%s:%d] assigned to thread '%s'" % (address[0], address[1], handler.thread.getName()))
			handler.connect(socket)
		else:
			self.closeSocket(socket)
			
	def closeSocket(self, socket):
		try:
			socket.close()
		except:
			pass
		socket = None
		
	# API
	def logError(self, msg = None):
		if msg is None:
			traceback.print_exc()
		else:
			print("[%s] ERROR\t%s" % (strftime("%Y/%m/%d %H:%M:%S", localtime()), msg))
		
	def clientConnection(self, socket, handler):
		return Client(socket, handler)
	
	def getVersion(self):
		return ""
		
	def exit(self, result):
		print("exiting")
		self.closeSocket(self.socket)
		sys.exit(result)
	
	# def loadAllowedDomains(self):
		# self.allowed_domains = []
		# with open('.domains', 'r') as file:
			# for line in file:
				# self.allowed_domains.append(line.rstrip())
				
	# def checkUrl(self, url):
		# object = urlsplit(url)
		# return (object.hostname in self.allowed_domains)
		

	

		
		