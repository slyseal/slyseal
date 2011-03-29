#!/usr/bin/python
# -*- coding: latin-1 -*-

import getopt, sys, time, os, socket, os.path
from Daemonize import Daemon
from Server import Server
from RtmpClient import RtmpClient

class RtmpServer(Server):
	def clientConnection(self, socket, handler):
		return RtmpClient(socket, handler)
	
	def getVersion(self):
		return "SSA/0,0,1,001"

class SsaDaemon(Daemon):
	def setHost(self, address = "localhost", port = 1935):
		self.host = (address, port)
		
	def run(self):
		server = RtmpServer()
		try:
			if self.host is None:
				self.host = ("localhost", 1935)
			print("host", self.host)
			server.start(self.host)
		except:
			print("error")
			server.logError()
			self.stop()
			sys.exit(-1)


def usage():
	print "SlySeal - help.\n"
	print "basic usage: %s start|stop|restart" % sys.argv[0]
	print '''	
options: 
-h, --help				help
-d, --directory="path/to/files"		directory containing the video files (defaults to current directory)
-a, --address=xxx.xxx.xxx.xxx 		host address (defaults to current host address)
-p, --port=xxxx 			port (defaults to 1935)
-n, --nodaemon				do not start in daemon mode, stay in console mode (only working mode on Windows)
'''
			
if __name__ == "__main__":
	#default params
	nodaemon = False
	host = socket.gethostbyname(socket.gethostname())
	port = 1935
	workingdir = os.path.dirname(sys.argv[0])
	if workingdir == '.':
		workingdir = os.getcwd()
	#print(workingdir, os.getuid())
	

	#read passed params
	try:
		opts, args = getopt.getopt(sys.argv[1:], "hd:a:p:n", ["help", "directory=", "address=", "port=", "nodaemon"])
	except getopt.GetoptError, err:
		# print help information and exit:
		print str(err) # will print something like "option -a not recognized"
		usage()
		sys.exit(2)
		
	for o, a in opts:
		if o in ("-h", "--help"):
			usage()
			sys.exit()
		elif o in ("-d", "--directory"):
			workingdir = a
		elif o in ("-a", "--address"):
			host = a
		elif o in ("-p", "--port"):
			port = a
		elif o in ("-n", "--nodaemon"):
			nodaemon = True
		else:
			assert False, "unhandled option"

	print('Binding SlySeal to %s:%d' % (host, port))
	print('Working directory is %s' % workingdir)
	print('Starting as daemon: %s' % ('Yes', 'No')[nodaemon])
	
	if nodaemon:
		server = RtmpServer()
		try:
			os.chdir(workingdir)
			server.start((host, port))
		except:
			server.logError()
			sys.exit(-1)				
	else:
		if len(args) == 0:
			print "Unknown command"
			sys.exit(2)
		
		command = args[0]
		
		log = os.path.join(workingdir, 'slyseal-daemon.log')
		pid = os.path.join(workingdir, 'slyseal-daemon.pid')
		daemon = SsaDaemon(pidfile=pid, stdout=log, stderr=log, workingdir=workingdir)
		daemon.setHost(host, port)

		if 'start' == command:
			daemon.start()
		elif 'stop' == command:
			daemon.stop()
		elif 'restart' == command:
			daemon.restart()
		else:
			print "Unknown command"
			sys.exit(2)
			
		print("ok")
		sys.exit(0)
