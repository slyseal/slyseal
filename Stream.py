from Frame import *
import FlvParser, Mp4Parser
import Rtmp
import os.path
import re
from struct import pack
from Bytes import BytesOutput
from time import time as getTime
import os
from stat import *

#=========================
# STATICS - GLOBALS
#=========================
try:
    stream_pool
except NameError:
    stream_pool = {}

# Base directory for media files
BASE_DIR = ""
	
STREAM_TYPE_FLV		= 0x03
STREAM_TYPE_MP4		= 0x04

FILE_PATTERN = re.compile(r"^[A-Za-z0-9_-][A-Za-z0-9_\/-]*(\.flv|\.mp4)?$")
def correctPath(path):
	root, extension = os.path.splitext(path)
	type = path[0:4].lower()
	if type in ("mp4:", "flv:"):
		path = path[4:]
	if extension.lower() not in (".flv", ".mp4"):
		if type in ("mp4:", "flv:"):
			path += '.' + type[0:3]
	return os.path.join(BASE_DIR, path)
	
def checkPath(path):
	return os.path.exists(path) and (FILE_PATTERN.match(path) is not None)

def getStreamInfo(path):
	if path in stream_pool:
		time = os.stat(path)[ST_MTIME]
		stream_info = stream_pool.get(path)
		if time == stream_info.time:
			return stream_info
		else:
			del stream_pool[path]
			
	info = StreamInfo(path)
	stream_pool[path] = info
	return info
	
def createStream(id, channel, path, rtmp):
	path = correctPath(path)
	info = getStreamInfo(path)
	if info is not None:
		if info.type == STREAM_TYPE_FLV:
			return FlvStream(id, channel, info, rtmp)
		elif info.type == STREAM_TYPE_MP4:
			return Mp4Stream(id, channel, info, rtmp)
			
	return None
	
	
#=========================
# STREAM INFO CLASS
#=========================
class StreamInfo(object):
	def __init__(self, path):
		if not checkPath(path):
			raise Exception, "STREAM: Invalid file '%s'" % path
			
		self.path = path
		
		root, extension = os.path.splitext(path)
		extension = extension.lower()
		
		self.time = os.stat(path)[ST_MTIME]
		
		with open(path, 'rb') as file:
			
			getInformation = None
			if extension == ".flv":
				self.type = STREAM_TYPE_FLV
				getInformation = FlvParser.getInformation
			elif extension == ".mp4":
				self.type = STREAM_TYPE_MP4
				getInformation = Mp4Parser.getInformation
			else:
				raise Exception, "STREAM: Unknown file extension '%s'" % extension
			
			if getInformation is not None:
				self.frames, self.metadata, self.descriptions = getInformation(path)
			else:
				raise Exception, "STREAM: invalid parser"
				
	def getFrame(self, index):
		if index < len(self.frames):
			return self.frames[index]
		else:
			return None
				
	def close(self):
		self.frames = None
		self.metadata = None
		self.descriptions = None

#=========================
# GENERIC STREAM CLASS
#=========================
class Stream(object):
	def __init__(self, id, channel, info, rtmp):
		self.id = id
		self.channel = channel
		self.info = info
		self.file = open(info.path, 'rb')
		self.rtmp = rtmp
		self.reset()
		self.init()
		
	def init(self):
		self.audio_count = 0
		self.video_count = 0
	
	def reset(self):
		self.base_time = 0
		self.index = 0
		#self.audio_count = 0
		#self.video_count = 0
	
	def getPath(self):
		return "prout" #debug
		if self.info is not None:
			return self.info.path
		else:
			return None
	
	def getTime(self):
		if (self.info is None) or (self.info.frames is None):
			return None
		len_frames = len(self.info.frames)
		index = (self.index, len_frames - 1)[self.index >= len_frames]
		return self.info.frames[index][0]
			
	def getFrame(self):
		return None
		
	def getDescription(self, type, first_time = False):
		return None
		
	def getVideoFrame(self,index, ref_time):
		return None
		
	def getSeekFrame(self):
		return None
		
	def getPauseFrame(self):
		return None
		
	def getMetadata(self):
		if (self.info is not None) and (self.info.metadata is not None):
			return self.info.metadata
		else:
			return None
		
	def seek(self, time):
		self.reset()
		
		keyframe_index = 0
		frame_index = 0
		
		if time > 0:
			for i in xrange(len(self.info.frames)):
				frame_index = i
				frame = self.info.frames[i]
				if frame is not None:
					self.base_time = frame[0]
					if frame[4] == True:
						keyframe_index = i
					if (frame[0] >= time) and (frame[1] == FRAME_TYPE_VIDEO):
						break
						
		self.index = frame_index + 1
		return keyframe_index
		
	def close(self):
		try:
			self.file.close()
		except:
			pass
		self.file = None
		self.rtmp = None
		self.info = None
		
#=========================
# FLV STREAM CLASS
#=========================
class FlvStream(Stream):
	pass
		

#=========================
# MP4 STREAM CLASS
#=========================		
class Mp4Stream(Stream):
	def getFrame(self):
		try:
			time, type, offset, size, keyframe, composition_time = self.info.frames[self.index]
		except:
			return None
			
		output = BytesOutput(True)
		
		first = False
		if (type == FRAME_TYPE_VIDEO):
			if (self.video_count == 0):
				first = True
			rtmp_type = Rtmp.RTMP_TYPE_VIDEO
			self.video_count += 1			
		elif (type == FRAME_TYPE_AUDIO):
			if (self.audio_count < 2):
				first = True
			rtmp_type = Rtmp.RTMP_TYPE_AUDIO
			self.audio_count += 1
			
		stream_id = None
			
		if first:
			output.write(self.getDescription(type, (time == 0)))
			stream_id = self.id
			
		data = BytesOutput(True)
		data.write(self.getFrameHeader(type, keyframe, False, composition_time))
		
		self.file.seek(offset, 0)
		data.write(self.file.read(size))
		
		timestamp = time - self.base_time
		
		output.write(self.rtmp.make(self.channel, (rtmp_type, data.getBytes()), timestamp, stream_id))
		
		self.index += 1
		self.base_time = time
		
		return (time, output.getBytes())
		
	def getFrameHeader(self, type, keyframe, description = False, ref_time = 0):
		output = BytesOutput(True)
		
		if type == FRAME_TYPE_VIDEO:
			output.writeByte((0x27, 0x17)[keyframe])
			output.writeByte((0x01, 0x00)[description])
			output.writeInt24(ref_time)
		elif type == FRAME_TYPE_AUDIO:
			output.writeByte(0xAF)
			output.writeByte((0x01, 0x00)[description])

		return output.getBytes()
		
	def getDescription(self, type, first_time = False):
		data = BytesOutput(True)
		
		data.write(self.getFrameHeader(type, True, True))
		
		if type == FRAME_TYPE_VIDEO:
			data.write(self.info.descriptions[0])
			return self.rtmp.make(self.channel, (Rtmp.RTMP_TYPE_VIDEO, data.getBytes()), 0, (None, self.id)[first_time])
		elif type == FRAME_TYPE_AUDIO:
			data.write(self.info.descriptions[1])
			return self.rtmp.make(self.channel, (Rtmp.RTMP_TYPE_AUDIO, data.getBytes()), 0, (None, self.id)[first_time])		
		else:
			return None
			
	def getVideoFrame(self, index, ref_time):
		try:
			time, type, offset, size, keyframe, composition_time = self.info.frames[index]
		except:
			return None
		if type != FRAME_TYPE_VIDEO:
			return None
			
		data = BytesOutput(True)
		data.write(self.getFrameHeader(type, keyframe, False, (time - ref_time) + composition_time))

		self.file.seek(offset, 0)
		data.write(self.file.read(size))
		
		self.video_count += 1
		return self.rtmp.make(self.channel, (Rtmp.RTMP_TYPE_VIDEO, data.getBytes()), 0, None)
		
	def getSeekFrame(self):
		data = pack(">2B", 0x57, 0x01)
		return self.rtmp.make(self.channel, (Rtmp.RTMP_TYPE_VIDEO, data), 0, None)
		
	def getPauseFrame(self):
		data = pack(">5B", 0x17, 0x02, 0x00, 0x00, 0x00)
		return self.rtmp.make(self.channel, (Rtmp.RTMP_TYPE_VIDEO, data), 0, None)
		
		
class FrameManader:
	def __init__(self):
		self.seek_time = 0
		
		self.video_index = 0
		self.audio_index = 0
		
		self.video_count = 0
		self.audio_count = 0
		
		self.video_frames = None
		self.audio_frames = None
		
	def getNextVideoFrame(self, increment = True):
		try:
			frame = self.video_frames[self.video_index]
			if increment:
				self.video_index += 1
		except:
			return None
		
	def getNextAudioFrame(self, increment = True):
		try:
			frame = self.audio_frames[self.audio_index]
			if increment:
				self.audio_index += 1
		except:
			return None
		
	def getNextFrame(self):
		audio_frame = getNextAudioFrame(False)
		video_frame = getNextVideoFrame(False)
		if video_frame is None:
			return audio_frame
		elif audio_frame is None:
			return video_frame
		elif video_frame[0] <= audio_frame[0]:
			self.video_index += 1
			return video_frame
		else:
			self.audio_index += 1
			return audio_frame
			
	
	def getChunk(self, limit = 65536):
		frames = []
		length = 0
		timestamp = 0
		next_video_frame = None
		while length < limit:
			frame = self.getNextFrame()
			if frame[1] == FRAME_TYPE_VIDEO:
				next_video_frame = self.getNextVideoFrame(False)
			elif (next_video_frame is not None) and (next_video_frame[3] + length > 70000):
					break
	
			frames.append(frame)
			length += frame[3]
			
	def getFirstChunk(self, limit = 65536):
		pass
					
				
			
			
			
			
			