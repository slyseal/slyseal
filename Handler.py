import select
import threading
from Queue import Queue, Empty
from time import sleep, time

class Handler(object):
	CONNECT 	= 0x01
	DISCONNECT 	= 0x02

	def __init__(self, server):
		self.server = server
		self.clients = {}
		self.queue = Queue()
		self.thread = threading.Thread(target=self.loop)
		self.thread.start()
		
	def loop(self):
		while 1:
			try:
				self.handle()
			except:
				self.clean()
				self.server.logError()
				break

	def handle(self):
		while 1:
			try:
				message = self.queue.get(len(self.clients) == 0)
			except Empty:
				break
			else:
				if message[0] == Handler.CONNECT:
					self.addClient(message[1])
				elif message[0] == Handler.DISCONNECT:
					self.removeClient(message[1])

		fd_list = self.clients.keys()
		read_list, write_list, exception_list = select.select(fd_list, fd_list, fd_list, 0.0)

		#t = time()
		self.handleException(exception_list)
		self.handleRead(read_list)
		self.handleUpdate()
		self.handleWrite(write_list)
		#print(time() - t)

		
		sleep(0.01)
		
	def handleException(self, list):
		for fd in list:
			client = self.clients.get(fd, None)
			if client is not None:
				self.removeClient(client)
			elif fd in self.clients:
				del self.clients[fd]
			
	def handleRead(self, list):
		for fd in list:
			client = self.clients.get(fd, None)
			if client is not None:
				try:
					client.read()
				except:
					self.removeClient(client)
			elif fd in self.clients:
				del self.clients[fd]
				
	def handleWrite(self, list):
		for fd in list:
			client = self.clients.get(fd, None)
			if client is not None:
				try:
					client.write()
				except:
					self.removeClient(client)
			elif fd in self.clients:
				del self.clients[fd]
		
	def handleUpdate(self):
		for fd, client in self.clients.items():
			if client is not None:
				try:
					client.update()
				except:
					self.removeClient(client)
			else:
				del self.clients[fd]
		
	def closeSocket(self, socket):
		if socket is not None:
			try:
				socket.close()
			except:
				pass
			socket = None
		
	def closeClient(self, client):
		if client is not None:
			self.closeSocket(client.socket)
			try:
				client.close()
			except:
				pass
			client = None	
		
	def removeClient(self, client):
		self.server.logError() #DEBUG
		if client is not None:
			if client.descriptor in self.clients:
				del self.clients[client.descriptor]
			self.closeClient(client)
		
	def addClient(self, socket):
		try:
			client = self.server.clientConnection(socket, self)
		except:
			self.server.logError() #DEBUG
			self.closeSocket(socket)
		else:	
			self.clients[socket.fileno()] = client

	
	def clean(self):
		new_clients = {}
		for fd, client in self.clients.items():
			socket = client.socket
			if socket is not None:
				try:
					socket.getpeername()
				except:
					self.closeClient(client)
				else:
					new_clients[fd] = client
		self.clients = new_clients		
	
	def connect(self, socket):
		self.queue.put((Handler.CONNECT, socket), False)
		
	def disconnect(self, client):
		self.queue.put((Handler.DISCONNECT, client), False)
		
	# def checkUrl(self, url):
		# return self.server.checkUrl(url)
		
		
