from Client import Client
from RtmpCommands import *
import Handshake
import Rtmp
import Amf
from Bytes import BytesInput, BytesOutput
from time import time as getTime
import Stream
from struct import pack

class StreamInfo:
	def __init__(self, id):
		self.id = id
		self.time = getTime()
		self.stream = None
		self.buffer_time = 100
		self.start_time = 0.0
		self.cur_time = 0
		self.duration = None
		self.channel_id = 0
		self.paused = None
		self.stopped = False
		self.seek_pause = False
		self.seek_time = 0
		self.seek_index = 0
		self.caching = None
		self.sleep = 0.0
		self.blocked = None
		self.start = 0.0
		self.length = 0.0
		
	def close(self):
		if self.stream is not None:
			try:
				self.stream.close()
			except:
				pass
			self.stream = None

# Broadcast Types
BROADCAST_START 	= 0x00
BROADCAST_SEEK		= 0x01
BROADCAST_UNPAUSE	= 0x02
		
# Rtmp Client State
STATE_WAITING_FOR_HANDSHAKE 			= 0x00
STATE_WAITING_FOR_HANDSHAKE_RESPONSE 	= 0x01
STATE_READY 							= 0x02
STATE_WAITING_FOR_BODY 					= 0x03
	
class RtmpClient(Client):
	BUFFER_TIME_S = 3.0

	def init(self):
		self.id = "BHAIsmrI"
		self.rtmp = Rtmp.Rtmp()
		self.streams = [None]
		self.state = (STATE_WAITING_FOR_HANDSHAKE,)
		self.initializeCommands()
		
	def exit(self):
		for stream in self.streams:
			self.closeStream(stream)
		self.rtmp = None
		self.streams = None
		self.commands = None
		
	def readMessage(self, buffer):
		input = BytesInput(bytes=buffer, bigendian=True)
		length = len(buffer)
		state = self.state[0]
		
		# Waiting for handshake
		if state == STATE_WAITING_FOR_HANDSHAKE:
			if length < (Handshake.HANDSHAKE_SIZE + 1):
				return None
			else:
				Handshake.readWelcome(input)
				handshake = Handshake.readHandshake(input)
				self.writeMessage(Handshake.makeHandshakeResponse(handshake))
				self.state = (STATE_WAITING_FOR_HANDSHAKE_RESPONSE,)
				return (Handshake.HANDSHAKE_SIZE + 1, None)
		
		# Waiting for handshake response
		elif state == STATE_WAITING_FOR_HANDSHAKE_RESPONSE:
			if length < Handshake.HANDSHAKE_SIZE:
				return None
			else:
				handshake = Handshake.readHandshake(input)
				self.state = (STATE_READY,)
				return (Handshake.HANDSHAKE_SIZE, None)
				
		# Ready to receive message - read header
		elif state == STATE_READY:
			header_size = Rtmp.headerSizeFromByte(input.getByte())
			if length < header_size:
				return None
			else:
				header = self.rtmp.readHeader(input)
				body_length = self.rtmp.bodyLength(header, True)
				self.state = (STATE_WAITING_FOR_BODY, (header, body_length))
				return (header_size, None)
				
		# Waiting for message body
		elif state == STATE_WAITING_FOR_BODY:
			header, body_length = self.state[1]
			if length < body_length:
				return None
			else:
				packet = self.rtmp.readPacket(header, input)
				message = (None, (header, packet))[packet is not None]
				self.state = (STATE_READY,)
				return (body_length, message)
		else:
			return None
			
			
	def processMessage(self, message):
		header, packet = message
		type = packet[0]
		
		if type == Rtmp.RTMP_TYPE_COMMAND:
			name, id, args = packet[1]
			#print("COMMAND %d: %s (%s)" % (id, name, str(args))) #DEBUG
			info = (id, header)
			
			if not self.commands.has(name):
				self.logError("Unknown Command %d: %s (%s)" % (id, name, str(args)))
			elif not self.commands.execute(name, info, args):
				self.logError("Mismatch arguments for Command %d: %s (%s)" % (id, name, str(args)))
				
		elif type == Rtmp.RTMP_TYPE_CONTROL:
			stream_id, control = packet[1]
			control_type = control[0]
			if control_type == Rtmp.RTMP_CONTROL_CLIENT_BUFFER:
				stream = self.getStream(stream_id)
				if stream is not None:
					stream.buffer_time = control[1]
	
	def refresh(self):
		time = getTime()
		for stream in self.streams:
			if (not self.blocking()) and (stream is not None) and (stream.stream is not None) and (stream.sleep < time):
				if stream.caching is not None:
					self.cacheFrames(stream)
				if (stream.caching is None) and (stream.paused is None) and (not stream.stopped):
					self.play(stream, time)
					
		
	# ** COMMANDS ** #
	def commandConnect(self, info, object, val = False):
		self.log(str(object)) #debug
		#self.log(object.get('swfUrl')[1])
		#if not self.handler.server.checkUrl(object.get('swfUrl')[1]):
		#	raise Exception, "Invalid URL"
		
		
		self.sendServerBW()
		self.sendClientBW()
		
		self.sendClear()
		
		self.sendNetConnectionConnectSuccess(info)
		
		self.sendOnBWDone(info)
		
	def commandCreateStream(self, info, _):
		self.sendCreateStreamResponse(info, self.createStream())
		
	def commandCloseStream(self, info, _, stream_id):
		self.closeStream(self.getStream(stream_id))
		
	def commandPlay(self, info, _, file, start, length):
		stream = self.getStream(info[1][4])
		if stream is None: return
		
		self.log("%s - Playing: %s" % (self.address, file)) #debug
		
		stream.close()
		stream.channel_id = 5
		stream.time = getTime()
		
		if start is not None:
			stream.start = start
		if length is not None:
			stream.length = int(stream.start + length)
		
		try:
			stream.stream = Stream.createStream(stream.id, stream.channel_id, file, self.rtmp)
		except:
			self.sendNetStreamPlayStreamNotFound(stream, file)
			raise Exception, "Stream Not Found (%s)" % file
			
		if start > 0:
			self.seek(stream, start, BROADCAST_START)
		else:
			self.startBroadcast(stream, BROADCAST_START)
	
	def commandPause(self, info, _, pause = False, time = None):
		stream = self.getStream(info[1][4])
		if stream is None: return
		
		if pause == True:
			stream.paused = getTime()
		elif stream.paused is not None:
			if stream.seek_pause:
				stream.seek_pause = False
				stream.paused = None
				self.seek(stream, (stream.seek_time, time)[time is not None], BROADCAST_UNPAUSE)
			else:
				stream.start_time += getTime() - stream.paused
				stream.paused = None
			
			

	def commandSeek(self, info, _, time):
		stream = self.getStream(info[1][4])
		if stream is None: return
		
		self.seek(stream, time, BROADCAST_SEEK)
	
	# ** INTERNAL COMMANDS ** #
	def getStream(self, stream_id):
		try:
			return self.streams[stream_id]
		except:
			return None
		
	def createStream(self):
		id = 1
		for i in xrange(1, len(self.streams)):
			if self.streams[i] is None:
				break
			else:
				id += 1
				
		if id == len(self.streams):
			self.streams.append(None)
			
		self.initStream(id)
		return id
		
	def initStream(self, id):
		self.streams[id] = StreamInfo(id)
		
	def closeStream(self, stream):
		if stream is not None:
			stream.close()
			self.streams[stream.id] = None
		
	def printTime(self, time):
		time = int(time / 1000)
		min, sec = divmod(time, 60)
		return "%02d:%02d" % (min, sec)
		
	def play(self, stream, time):
		if stream.blocked is not None:
			stream.start_time += time - stream.blocked
			stream.blocked = None
			
		rel_time = int((time - stream.start_time) * 1000.0) + (stream.buffer_time * 2)

		while rel_time > stream.cur_time:
			frame = stream.stream.getFrame()
			
			if (frame is None) or ((stream.length > 0) and (frame[0] > stream.length)):
				self.stop(stream)
				return
			else:
				
				stream.cur_time = frame[0]
				self.writeMessage(frame[1])
				
				if self.blocking():
					stream.blocked = getTime()
					return
					
		#self.sleep = getTime() + self.BUFFER_TIME_S / 2
	
	def seek(self, stream, time, type):
		stream.seek_time = time
		stream.seek_index = stream.stream.seek(time)
		
		self.startBroadcast(stream, type)
		
		self.cacheFrames(stream, (type == BROADCAST_START))
		
	def startBroadcast(self, stream, type):
		stream.stopped = False
		stream.start_time = getTime() - self.BUFFER_TIME_S - (float(stream.seek_time) / 1000.0)
		seek_time = stream.seek_time - (0, stream.cur_time)[stream.cur_time < stream.seek_time]
		stream.cur_time = stream.stream.base_time
		stream.sleep = 0.0
		
		start = (type == BROADCAST_START)
		stream_id = (None, stream.id)[start]
		
		self.rtmp.setChunkSize(4096)
		self.sendChunkSize(self.rtmp.getChunkSize())
		
		if type == BROADCAST_SEEK:
			self.sendClearPlay(stream.id)
		
		self.sendReset(stream.id)
		self.sendClear(stream.id)
		
		if type == BROADCAST_START:
			self.sendNetStreamPlayReset(stream, 0, stream_id)
		elif type == BROADCAST_SEEK:
			self.sendNetStreamSeekNotify(stream, seek_time, (stream_id, stream.id)[seek_time == stream.seek_time])
		elif type == BROADCAST_UNPAUSE:
			self.sendNetStreamUnpauseNotify(stream, 0, stream_id)

		self.sendNetStreamPlayStart(stream, 0, stream_id)
		
		self.sendRtmpSampleAccess(stream, stream_id)
		self.sendBlankAudioFrame(stream, stream_id)
			
		self.sendNetStreamDataStart(stream, stream_id)
		if type != BROADCAST_START:
			self.sendBlankVideoFrame(stream, stream_id)
		self.sendMetaData(stream, stream_id)
		
			
	def cacheFrames(self, stream, start = False):
		if stream.caching is None:
			stream.caching = [stream.seek_index, start, getTime()]
		while stream.caching is not None:
			if stream.caching[0] < stream.stream.index:
				if stream.caching[0] == stream.seek_index:
					self.writeMessage(stream.stream.getDescription(Stream.FRAME_TYPE_VIDEO, stream.caching[1]))
				self.writeMessage(stream.stream.getVideoFrame(stream.caching[0], stream.seek_time))
				stream.caching[0] += 1
			else:
				stream.start_time += getTime() - stream.caching[2]
				stream.caching = None
				self.writeMessage(stream.stream.getSeekFrame())
				
				if stream.paused is not None:
					stream.seek_pause = True
					self.writeMessage(stream.stream.getPauseFrame())
					self.writeMessage(stream.stream.getDescription(Stream.FRAME_TYPE_AUDIO))
					self.sendBlankAudioFrame(stream)
					self.sendClearPlay(stream.id)
				else:
					self.writeMessage(stream.stream.getDescription(Stream.FRAME_TYPE_AUDIO))
					#self.paused = getTime()
			if self.blocking():
				break
			
	def stop(self, stream):
		stream.stopped = True
		self.writeMessage(stream.stream.getPauseFrame())
		self.writeMessage(stream.stream.getPauseFrame())
		self.sendClearPlay(stream.id)
		self.sendNetStreamPlayStop(stream)

	def initializeCommands(self):
		self.commands = RtmpCommands()
		self.commands.register("connect", self.commandConnect, (ARG_TYPE_OBJECT,ARG_TYPE_OPTIONAL | ARG_TYPE_BOOL))
		self.commands.register("createStream", self.commandCreateStream, (ARG_TYPE_NULL,))
		self.commands.register("play", self.commandPlay, (ARG_TYPE_NULL, ARG_TYPE_STRING, ARG_TYPE_OPTIONAL | ARG_TYPE_NUMBER, ARG_TYPE_OPTIONAL | ARG_TYPE_NUMBER))
		self.commands.register("pause", self.commandPause, (ARG_TYPE_NULL, ARG_TYPE_OPTIONAL | ARG_TYPE_BOOL, ARG_TYPE_NUMBER))
		self.commands.register("pauseRaw", self.commandPause, (ARG_TYPE_NULL, ARG_TYPE_OPTIONAL | ARG_TYPE_BOOL, ARG_TYPE_NUMBER))
		self.commands.register("seek", self.commandSeek, (ARG_TYPE_NULL, ARG_TYPE_NUMBER))
		self.commands.register("closeStream", self.commandCloseStream, (ARG_TYPE_NULL, ARG_TYPE_NUMBER))
		self.commands.register("deleteStream", self.commandCloseStream, (ARG_TYPE_NULL, ARG_TYPE_NUMBER))
		
	# ** MESSAGES ** #
	def sendChunkSize(self, size):
		self.writeMessage(self.rtmp.make(2, (Rtmp.RTMP_TYPE_CHUNK_SIZE, size)))
		
	def sendClear(self, stream_id = 0):
		self.writeMessage(self.rtmp.make(2, (Rtmp.RTMP_TYPE_CONTROL, (stream_id, (Rtmp.RTMP_CONTROL_CLEAR,)))))
		
	def sendClearPlay(self, stream_id = 0):
		self.writeMessage(self.rtmp.make(2, (Rtmp.RTMP_TYPE_CONTROL, (stream_id, (Rtmp.RTMP_CONTROL_CLEAR_PLAY,)))))
		
	def sendReset(self, stream_id = 0):
		self.writeMessage(self.rtmp.make(2, (Rtmp.RTMP_TYPE_CONTROL, (stream_id, (Rtmp.RTMP_CONTROL_RESET,)))))
		
	def sendServerBW(self, value = 0):
		self.writeMessage(self.rtmp.make(2, (Rtmp.RTMP_TYPE_SERVER_BW, value)))
		
	def sendClientBW(self, value = 0):
		self.writeMessage(self.rtmp.make(2, (Rtmp.RTMP_TYPE_CLIENT_BW, value)))
		
	def sendCreateStreamResponse(self, info, stream_id):
		self.writeMessage(self.rtmp.make(info[1][0], (Rtmp.RTMP_TYPE_COMMAND, ("_result", info[0], [
			Amf.encode(None),
			Amf.encode(stream_id)
		]))))
		
	def sendNetConnectionConnectSuccess(self, info):
		self.writeMessage(self.rtmp.make(info[1][0], (Rtmp.RTMP_TYPE_COMMAND, ("_result", info[0], [ 
			Amf.encode({
				'fmsVer' : self.handler.server.getVersion(),
				'capabilities' : 31.0,
				'mode' : 1
			}),
			Amf.encode({
				'level' : "status",
				'code' : "NetConnection.Connect.Success",
				'description' : "Connection succeeded.",
				'objectEncoding' : 0.0
			})
		]))))
		
	def sendOnBWDone(self, info):
		self.writeMessage(self.rtmp.make(info[1][0], (Rtmp.RTMP_TYPE_COMMAND, ("onBWDone", 0, [
			Amf.encode(None)
		])))) 

	def sendMetaData(self, stream, stream_id = None):
		#self.writeMessage(self.rtmp.make(stream.channel_id, (Rtmp.RTMP_TYPE_COMMAND, ("onMetaData", 0, [
		#	Amf.encode(None),
		#	Amf.encode(stream.stream.getMetadata())
		#])), 0, stream_id))
		output = BytesOutput(True)
		Amf.write(output, Amf.encode("onMetaData"))
		Amf.write(output, Amf.encode(stream.stream.getMetadata()))
		self.writeMessage(self.rtmp.make(stream.channel_id, (Rtmp.RTMP_TYPE_NOTIFY, output.getBytes()), 0, stream_id))
		
	def sendNetStreamPlayStreamNotFound(self, stream, file):
		self.writeMessage(self.rtmp.make(stream.channel_id, (Rtmp.RTMP_TYPE_COMMAND, ("onStatus", 0, [
			Amf.encode(None), 
			Amf.encode({
				'level': "status",
				'code': "NetStream.Play.StreamNotFound",
				'details': file,
				'clientid': self.id
			})
		])), 0, stream.id))
		
	def sendNetStreamPlayReset(self, stream, timestamp = 0, stream_id = None):
		self.writeMessage(self.rtmp.make(4, (Rtmp.RTMP_TYPE_COMMAND, ("onStatus", 0, [
			Amf.encode(None),
			Amf.encode({
				'level': "status",
				'code': "NetStream.Play.Reset",
				'description': "Playing and resetting %s." % stream.stream.getPath(),
				'details': stream.stream.getPath(),
				'clientid': self.id
			})
		])),  timestamp, stream_id)) #4 - stream.channel_id
		
	def sendNetStreamPlayStart(self, stream, timestamp = 0, stream_id = None):
		self.writeMessage(self.rtmp.make(stream.channel_id, (Rtmp.RTMP_TYPE_COMMAND, ("onStatus", 0, [
			Amf.encode(None),
			Amf.encode({
				'level': "status",
				'code': "NetStream.Play.Start",
				'description': "Started playing %s." % stream.stream.getPath(),
				'details': stream.stream.getPath(),
				'clientid': self.id
			})
		])), timestamp, stream_id))
		
	def sendNetStreamPlayStop(self, stream, timestamp = 0, stream_id = None):
		self.writeMessage(self.rtmp.make(stream.channel_id, (Rtmp.RTMP_TYPE_COMMAND, ("onStatus", 0, [
			Amf.encode(None),
			Amf.encode({
				'level': "status",
				'code': "NetStream.Play.Stop",
				'description': "Stopped playing %s." % stream.stream.getPath(),
				'details': stream.stream.getPath(),
				'clientid': self.id
			})
		])),  timestamp, stream_id))
		
	def sendNetStreamUnpauseNotify(self, stream, timestamp = 0, stream_id = None):
		self.writeMessage(self.rtmp.make(stream.channel_id, (Rtmp.RTMP_TYPE_COMMAND, ("onStatus", 0, [
			Amf.encode(None),
			Amf.encode({
				'level': "status",
				'code': "NetStream.Unpause.Notify",
				'description': "Unpausing %s." % stream.stream.getPath(),
				'details': stream.stream.getPath(),
				'clientid': self.id
			}),
		])), timestamp, stream_id))
		
	def sendNetStreamSeekNotify(self, stream, timestamp = 0, stream_id = None):
		self.writeMessage(self.rtmp.make(stream.channel_id, (Rtmp.RTMP_TYPE_COMMAND, ("onStatus", 0, [
			Amf.encode(None), 
			Amf.encode({
				'level': "status",
				'code': "NetStream.Seek.Notify",
				'description': "Seeking %d (stream ID: %d)." % (stream.seek_time, stream.id),
				'details': stream.stream.getPath(),
				'clientid': self.id
			})
		])), timestamp, stream_id))
		
	def sendRtmpSampleAccess(self, stream, stream_id = None):
		output = BytesOutput(True)
		Amf.write(output, Amf.encode("|RtmpSampleAccess"))
		Amf.write(output, Amf.encode(False))
		Amf.write(output, Amf.encode(False))
		self.writeMessage(self.rtmp.make(5, (Rtmp.RTMP_TYPE_NOTIFY, output.getBytes()), 0, stream_id))
		
	def sendBlankAudioFrame(self, stream, stream_id = None):
		self.writeMessage(self.rtmp.make(stream.channel_id, (Rtmp.RTMP_TYPE_AUDIO, ''), 0, stream_id))
		
	def sendBlankVideoFrame(self, stream, stream_id = None):
		self.writeMessage(self.rtmp.make(stream.channel_id, (Rtmp.RTMP_TYPE_VIDEO, pack(">2B", 0x57, 0x00)), 0, stream_id))
	
	def sendNetStreamDataStart(self, stream, stream_id = None):
		output = BytesOutput(True)
		Amf.write(output, Amf.encode("onStatus"))
		Amf.write(output, Amf.encode({"code": "NetStream.Data.Start"}))
		self.writeMessage(self.rtmp.make(5, (Rtmp.RTMP_TYPE_NOTIFY, output.getBytes()), 0, stream_id))
		
	def logError(self, msg):
		self.handler.server.logError(msg)
		