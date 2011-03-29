from __future__ import with_statement 
from struct import unpack
from Frame import *


# AVC Decoder Configuration Record
"""
def parseAvcDescription(bytes):
	version, profile, compatibiliy, level = unpack(">4B", bytes[0:4])
	lengthSizeMinusOne = unpack(">B", bytes[4])[0] & 0x03
	numOfSequenceParameterSets = unpack(">B", bytes[5])[0] & 0x1F
	bytes = bytes[6:-1]
	for i in range(numOfSequenceParameterSets):
		sequenceParameterLength = unpack(">H", bytes[0:2])[0]
		sequenceParameterNALUnit = unpack(">%iB" % (sequenceParameterLength) , bytes[2:sequenceParameterLength + 2])
		bytes = bytes[sequenceParameterLength + 2:-1]
	numOfPictureParameterSets = unpack(">B", bytes[0])[0]
	print numOfPictureParameterSets, len(bytes)
	bytes = bytes[1:-1]
	for i in range(numOfPictureParameterSets):
		pictureParameterLength = unpack(">H", bytes[0:2])[0]
		print pictureParameterLength, len(bytes)
		pictureParameterNALUnit = unpack(">%iB" % (pictureParameterLength) , bytes[2:pictureParameterLength + 2])
		bytes = bytes[pictureParameterLength + 2:-1]
	print "AVC", profile, level, lengthSizeMinusOne
"""

# Read Atom Header (start, size, type, end)
def readAtomHeader(file):
	try:
		start = file.tell()
		size = unpack('>I', file.read(4))[0]
		type = file.read(4).lower()
		if size == 1:
			size = unpack('>L', file.read(8))[0]
		end = start + size
		return (type, end)
	except:
		return (None, None)

# Build Metadata Dictionary
def buildMetadata(type, movie):
	pass
		
	
# Build Track [header, samples]
def buildTrack(trak):
	# Chunk (offset, size, id, sample)
	# Samples (dts, cto, offset, size, keyframe, description_index)
	
	samples = None
	chunks = None
	
	header, media, reference, edit = trak
	
	media_header, media_handler, media_information = media
	
	extra_header, data_information, sample_table = media_information
	
	st_decoding_time, st_composition_time, st_sample_description, st_sample_size, st_sample_to_chunk, st_chunk_offset, st_sync_sample, stsh, stdp = sample_table
	
	# Samples
	sample_size, nb_samples, entries = st_sample_size
	if sample_size == 0:
		samples = [[0, 0, 0, size, False, 0] for size in entries]
	else:
		samples = [[0, 0, 0, sample_size, False, 0]] * nb_samples

	# Decoding time
	entry_count, entries = st_decoding_time
	s = 0
	delta = 0
	for i in xrange(entry_count):
		sample_count, sample_delta = entries[i*2], entries[(i*2) + 1]
		for j in xrange(sample_count):
			samples[s][0] = delta
			delta += sample_delta
			s += 1
		
	# Composition time
	if st_composition_time:
		entry_count, entries = st_composition_time
		s = 0
		for i in xrange(entry_count):
			sample_count, sample_offset = entries[i*2], entries[(i*2) + 1]
			for j in xrange(sample_count):
				if s >= nb_samples: break
				samples[s][1] = sample_offset
				s += 1		

	# Chunk offset
	nb_chunks, entries = st_chunk_offset
	chunks = [[offset, 0, 0] for offset in entries]

	# Sample to chunk
	entry_count, entries, offset = st_sample_to_chunk
	last = nb_chunks
	for i in xrange(entry_count):
		k = entry_count - i - 1
		first_chunk, samples_per_chunk, sample_description_index = (entries[3*k] - offset), entries[(3*k) + 1], (entries[(3*k) + 2] - offset)
		for j in xrange(first_chunk, last):
			chunks[j][1] = samples_per_chunk
			chunks[j][2] = sample_description_index
		last = first_chunk

	# Sample description index and offset
	s = 0
	offset = 0
	for i in xrange(nb_chunks):
		chunk = chunks[i]
		offset = chunk[0]
		for j in xrange(chunk[1]):
			samples[s][2] = offset
			samples[s][5] = chunk[2]
			offset += samples[s][3]
			s += 1

	# Random Access Points
	if st_sync_sample:
		entry_count, entries, offset = st_sync_sample
		for i in xrange(entry_count):
			samples[entries[i] - offset][4] = True
			
	descriptions = st_sample_description[1]
	header = buildTrackHeader((header, media_header, extra_header, media_handler, descriptions))
	
	return (header, samples)

# Build Track Header
def buildTrackHeader(complete_header):
	track_type = complete_header[3][0]
	type = {"vide":"video", "sound":"audio"}.get(track_type, track_type)
	format, description = complete_header[4][0]
	id = complete_header[0][2]
	timescale, duration = complete_header[1][2:4]
	
	return (id, type, format, description, timescale, duration, complete_header)
	
# Check validity
def isValid(type):
	return type[0] in ('isom', 'mp42')
	
def normalizeTime(time, timescale):
	if time == 0:
		return 0
	return int(round(1000.0 * time / timescale))
	
# Get frames from a given track
def getFramesFromTrack(track, frametype):
	timescale = float(track[0][4])
	samples = track[1]

	if frametype == 7:
		with open("ff.txt", "w") as f:
			for d, c, o, s, k, i in samples:
				d = int(round(1000.0 * d / timescale))
				c = int(round(1000.0 * float(c) / timescale))
				f.write("%8d - %8d - %8d - %8d - %8d - %8d\n" % (d, c, o, s, k, i))
	
	frames = [(normalizeTime(sample[0], timescale), frametype, sample[2], sample[3], sample[4], normalizeTime(sample[1], timescale)) for sample in samples]
	return frames	
	
# Get frames from tracks
def getFrames(tracks):
	video_frames = None
	audio_frames = None
	
	for track in tracks:
		format = track[0][2]
		if (format == "avc1") and (video_frames == None):
			video_frames = getFramesFromTrack(track, FRAME_TYPE_VIDEO)
		elif (format == "mp4a") and (audio_frames == None):
			audio_frames = getFramesFromTrack(track, FRAME_TYPE_AUDIO)
			
	if video_frames == None:
		return audio_frames
	elif audio_frames == None:
		return video_frames
	else:
		frames = video_frames + audio_frames
		frames.sort()
		return frames
	
# Get Video and Audio descriptions
def getDescriptions(tracks):
	video_description = None
	audio_description = None
	
	for header, samples in tracks:
		format, description = header[2:4]
		if (format == "avc1") and (video_description == None):
			video_description = description[1]
		elif (format == "mp4a") and (audio_description == None):
			audio_description = description[1]
			
	return (video_description, audio_description)
		
# Get Movie Duration
def getDuration(movie = None, path = None):
	if path is not None:
		type, movie = parse(path)
	
	if (movie is not None) and (movie[0] is not None):
		header = movie[0]
		return float(header[3]) / float(header[2])
	else:
		return None
	
# Get built tracks
def getTracks(movie):
	if movie:
		return [buildTrack(track) for track in movie[1]]
	else:
		return None
		
# Get Metadata
def getMetadata(type, movie, duration):
	width = 0
	height = 0
	for track in movie[1]:
		if track[1][1][0] == "vide":
			width, height = track[0][5:7]
	metadata = {
		"duration":duration / 1000.0,
		"width":width,
		"height":height
		}
	return metadata
	
	if movie:
		return buildMetadata(type, movie)
	else:
		return None
		
# Get Information [frames, metadata, descriptions]
def getInformation(path):
	type, movie = parse(path)
	tracks = getTracks(movie)
	frames = getFrames(tracks)
	metadata = getMetadata(type, movie, frames[len(frames) - 1][0])
	descriptions = getDescriptions(tracks)
	return (frames, metadata, descriptions)
		
# Parse file
def parse(path):
	type = None
	movie = None
	with open(path, "rb") as file:
		while True:
			atom_type, atom_end = readAtomHeader(file)
			if atom_type == None:
				break
			elif atom_type == "ftyp":
				type = parseFtyp(file, atom_end)
			elif atom_type == "moov":
				movie = parseMoov(file, atom_end)
			elif atom_type == "mdat":
				pass
			
			file.seek(atom_end - file.tell(), 1)
			
	return (type, movie);
	
# File Type Box
def parseFtyp(file, end):
	major_brand = file.read(4)
	minor_brand = unpack(">I", file.read(4))[0]
	compatible_brands = []
	while (file.tell() < end):
		compatible_brands.append(file.read(4))
	return (major_brand, minor_brand, compatible_brands)

# Movie Box
def parseMoov(file, end):
	header = None
	tracks = []
	iods = None
	while (file.tell() < end):
		atom_type, atom_end = readAtomHeader(file)
		if atom_type == None:
			break
		elif atom_type == "mvhd":
			header = parseMvhd(file, atom_end)
		elif atom_type == "trak":
			tracks.append(parseTrak(file, atom_end))
		elif atom_type == "iods":
			iods = parseIods(file, atom_end)			
		
		file.seek(atom_end - file.tell(), 1)

	return (header, tracks)
	
# Initial Object Descriptor Box
def parseIods(file, end):
	file.seek(4, 1) # version + flags
	return file.read(end - file.tell())

# Movie Header Box
def parseMvhd(file, end):
	version = unpack(">B", file.read(1))[0]
	flags = file.seek(3, 1)
	if (version == 1):
		creation_time = unpack(">Q", file.read(8))[0]
		modification_time = unpack(">Q", file.read(8))[0]
		timescale = unpack(">I", file.read(4))[0]
		duration = unpack(">Q", file.read(8))[0]
	else:
		creation_time = unpack(">I", file.read(4))[0]
		modification_time = unpack(">I", file.read(4))[0]
		timescale = unpack(">I", file.read(4))[0]
		duration = unpack(">I", file.read(4))[0]
	rate = float(unpack(">I", file.read(4))[0]) / (2 << 15)
	volume = float(unpack(">H", file.read(2))[0]) / (2 << 7)
	file.seek(10, 1) # reserved
	matrix = unpack(">9I", file.read(4 * 9))
	file.seek(24, 1) # reserved
	next_track_id = unpack(">I", file.read(4))[0]
	return (creation_time, modification_time, timescale, duration, rate, volume, matrix, next_track_id)
	
	
# Track Box
def parseTrak(file, end):
	header = None
	media = None
	reference = None
	edit = None
	while (file.tell() < end):
		atom_type, atom_end = readAtomHeader(file)
		if atom_type == None:
			break
		elif atom_type == "tkhd":
			header = parseTkhd(file, atom_end)
		elif atom_type == "tref":
			reference = parseTref(file, atom_end)
		elif atom_type == "mdia":
			media = parseMdia(file, atom_end)
		elif atom_type == "edts":
			edit = parseEdts(file, atom_end)
		
		file.seek(atom_end - file.tell(), 1)
	
	return (header, media, reference, edit)
		
# Track Header Box
def parseTkhd(file, end):
	version = unpack(">B", file.read(1))[0]
	flags = file.seek(3, 1)
	if (version == 1):
		creation_time = unpack(">Q", file.read(8))[0]
		modification_time = unpack(">Q", file.read(8))[0]
		track_id = unpack(">I", file.read(4))[0]
		file.seek(4, 1) # Reserved
		duration = unpack(">Q", file.read(8))[0]
	else:
		creation_time = unpack(">I", file.read(4))[0]
		modification_time = unpack(">I", file.read(4))[0]
		track_id = unpack(">I", file.read(4))[0]
		file.seek(4, 1) # Reserved
		duration = unpack(">I", file.read(4))[0]
	file.seek(12, 1) # Reserved + layer + alternate_group -- 2*4 + 2 + 2
	volume = float(unpack(">H", file.read(2))[0]) / (2 << 8)
	file.seek(2, 1)
	matrix = unpack(">9I", file.read(4 * 9))
	width = float(unpack(">I", file.read(4))[0]) / (2 << 15)
	height = float(unpack(">I", file.read(4))[0]) / (2 << 15)
	
	return (creation_time, modification_time, track_id, duration, volume, width, height)
	
# Track Reference Box	
def parseTref(file, end):
	references = []
	while (file.tell() < end):
		atom_type, atom_end = readAtomHeader(file)  # TrackReferenceTypeBox Preamble
		references.append(unpack(">I", file.read(4))[0])
	return references
	
# Edit Box
def parseEdts(file, end):
	edit_list = None
	while (file.tell() < end):
		atom_type, atom_end = readAtomHeader(file)
		if atom_type == None:
			break
		elif atom_type == "elst":
			edit_list = parseElst(file, atom_end)
			
		file.seek(end - file.tell(), 1)
		
	return edit_list
			
# Edit List Box
def parseElst(file, end):
	version = unpack(">B", file.read(1))[0]
	flags = file.seek(3, 1)
	entries = unpack(">I", file.read(4))[0]
	count = 2 * entries
	if version == 1:
		table = unpack(">%ii" % (count), file.read(8 * count))
	else:
		table = unpack(">%ii" % (count), file.read(4 * count))
	media_times = [(table[i], table[i + 1]) for i in xrange(0, count, 2)] # segment_duration, media_time
	media_rate_integer = unpack(">h", file.read(2))[0]
	media_rate_fraction = unpack(">h", file.read(2))[0]
	
	return (entries, media_times, media_rate_integer, media_rate_fraction)
	
	
# Media Box
def parseMdia(file, end):
	header = None
	handler = None
	information = None
	while (file.tell() < end):
		atom_type, atom_end = readAtomHeader(file)
		if atom_type == None:
			break
		elif atom_type == "mdhd":
			header = parseMdhd(file, atom_end)
		elif atom_type == "hdlr":
			handler = parseHdlr(file, atom_end)
		elif atom_type == "minf":
			information = parseMinf(file, atom_end)
		
		file.seek(atom_end - file.tell(), 1)
			
	return (header, handler, information)
			
# Media Header Box
def parseMdhd(file, end):
	version = unpack(">B", file.read(1))[0]
	flags = file.seek(3, 1)
	if (version == 1):
		creation_time = unpack(">Q", file.read(8))[0]
		modification_time = unpack(">Q", file.read(8))[0]
		timescale = unpack(">I", file.read(4))[0]
		duration = unpack(">Q", file.read(8))[0]
	else:
		creation_time = unpack(">I", file.read(4))[0]
		modification_time = unpack(">I", file.read(4))[0]
		timescale = unpack(">I", file.read(4))[0]
		duration = unpack(">I", file.read(4))[0]
	language_coded = unpack(">H", file.read(2))[0]
	char1 = str(language_coded >> 10)
	char2 = str((language_coded << 22) >> 27)
	char3 = str((language_coded << 27) >> 27)
	language = char1 + char2 + char3
	file.seek(2, 1) # 2 -- reserved
	
	return (creation_time, modification_time, timescale, duration, language)

# Media Handler Box		
def parseHdlr(file, end):
	file.seek(4, 1) # Version + flags
	file.seek(4, 1) # Reserved
	type = file.read(4)
	file.seek(12, 1) # reserved
	name = file.read(end - file.tell())
	return (type, name)
	
# Media Information Box
def parseMinf(file, end):
	header = None
	data_information = None
	sample_table = None
	while (file.tell() < end):
		atom_type, atom_end = readAtomHeader(file)
		if atom_type == None:
			break
		elif atom_type == "vmhd":
			header = parseVmhd(file, atom_end)
		elif atom_type == "smhd":
			header = parseSmhd(file, atom_end)
		elif atom_type == "hmhd":
			header = parseHmhd(file, atom_end)
		elif atom_type == "nmhd":
			header = parseNmhd(file, atom_end)
		elif atom_type == "dinf":
			data_information = parseDinf(file, atom_end)
		elif atom_type == "stbl":
			sample_table = parseStbl(file, atom_end)

		file.seek(atom_end - file.tell(), 1)
			
	return (header, data_information, sample_table)
	
# Video Media Header Box
def parseVmhd(file, end):
	file.seek(4, 1) # version  + flags
	graphicsmode = unpack(">H", file.read(2))[0]
	opcode = unpack(">3H", file.read(6))
	return ("vide", (graphicsmode, opcode))

# Sound Media Header Box		
def parseSmhd(file, end):
	file.seek(4, 1) # version  + flags
	balance = unpack(">H", file.read(2))[0]
	file.seek(2, 1) # 2 -- reserved
	return ("soun", (balance))

# Hint Media Header Box		
def parseHmhd(file, end):
	file.seek(4, 1) # version  + flags
	maxPDUsize = unpack(">H", file.read(2))[0]
	minPDUsize = unpack(">H", file.read(2))[0]
	maxbitrate = unpack(">I", file.read(4))[0]
	avgbitrate = unpack(">I", file.read(4))[0]
	file.seek(4, 1) # 4 -- reserved
	return ("hint", (maxPDUsize, minPDUsize, maxbitrate, avgbitrate))
		
# Null Media Header Box	
def parseNmhd(file, end):
	file.seek(4, 1) # version  + flags
	return ("null", None)
			
# Data Information Box
def parseDinf(file, end):
	atom_type, atom_end = readAtomHeader(file) # Dref
	reference = parseDref(file, atom_end)
	return reference
			
# Data Reference Url Box
def parseUrl_(file, end):
	file.seek(4, 1) # version + flags
	location = file.read(end - file.tell())
	return ("url", location)
		
# Data Reference Url Named Box
def parseUrn_(file, end):
	file.seek(4, 1) # version + flags
	name_location = file.read(end - file.tell())
	return ("urn", name_location)

# Data Reference Box
def parseDref(file, end):
	file.seek(4, 1) # version + flags
	entry_count = unpack(">I", file.read(4))[0]
	references = []
	for i in xrange(entry_count):
		atom_type, atom_end = readAtomHeader(file)
		if type == "url ":
			references.append(parseUrl_(file, atom_end))
		elif type == "urn ":
			references.append(parseUrn_(file, atom_end))
	return (entry_count, references)
	
# Sample Table Box
def parseStbl(file, end):
	decoding_time_to_sample = None
	composition_time_to_sample = None
	sample_description = None
	sample_size = None
	sample_to_chunk = None
	chunk_offset = None
	sync_sample = None
	shadow_sync_sample = None
	degradation_priority = None
	
	while (file.tell() < end):
		atom_type, atom_end = readAtomHeader(file)
		if atom_type == None:
			break
		elif atom_type == "stts":
			decoding_time_to_sample = parseStts(file, atom_end)
		elif atom_type == "ctts":
			composition_time_to_sample = parseCtts(file, atom_end)
		elif atom_type == "stsd":
			sample_description = parseStsd(file, atom_end)
		elif atom_type == "stsz":
			sample_size = parseStsz(file, atom_end)
		elif atom_type == "stz2":
			sample_size = parseStz2(file, atom_end)
		elif atom_type == "stsc":
			sample_to_chunk = parseStsc(file, atom_end)
		elif atom_type == "stco":
			chunk_offset = parseStco(file, atom_end)
		elif atom_type == "co64":
			chunk_offset = parseCo64(file, atom_end)
		elif atom_type == "stss":
			sync_sample = parseStss(file, atom_end)
		elif atom_type == "stsh":
			shadow_sync_sample = parseStsh(file, atom_end)
		elif atom_type == "stdp":
			degradation_priority = parseStdp(file, atom_end)
		
		file.seek(atom_end - file.tell(), 1)
			
	return 	(decoding_time_to_sample, composition_time_to_sample, sample_description, sample_size, sample_to_chunk, chunk_offset, sync_sample, shadow_sync_sample, degradation_priority)

# Sample Entry
def parseSampleEntry(file):
	file.seek(6, 1) # reserved
	data_reference_index = unpack(">H", file.read(2))[0]
	return data_reference_index
	
# Audio Sample  Entry [data_reference_index, channel_count, sample_size, sample_rate]
def parseAudioSampleEntry(file):
	data_reference_index = parseSampleEntry(file)
	file.seek(8, 1) # reserved
	channel_count = unpack(">H", file.read(2))[0]
	sample_size = unpack(">H", file.read(2))[0]
	file.seek(4, 1) # reserved
	sample_rate = unpack(">I", file.read(4))[0] >> 16
	return (data_reference_index, channel_count, sample_size, sample_rate)
	
# Visual Sample Entry
def parseVisualSampleEntry(file):
	data_reference_index = parseSampleEntry(file)
	file.seek(16, 1) # reserved -- 2 + 2 + 3*4
	width = unpack(">H", file.read(2))[0]
	height = unpack(">H", file.read(2))[0]
	horizontal_resolution = float(unpack(">I", file.read(4))[0]) / (2 << 15)
	vertical_resolution = float(unpack(">I", file.read(4))[0]) / (2 << 15)
	file.seek(4, 1) # reserved
	frame_count = unpack(">H", file.read(2))[0]
	compressor_name_length = unpack(">B", file.read(1))[0]
	compressor_name = file.read(compressor_name_length)
	file.seek(32 - 1 - compressor_name_length, 1) # compressor name padding
	depth = unpack(">H", file.read(2))[0]
	file.seek(2, 1) # reserved
	
	return (data_reference_index, width, height, horizontal_resolution, vertical_resolution, frame_count, compressor_name, depth)
		
# Avc1 Box
def parseAvc1(file, end):
	information = parseVisualSampleEntry(file)
	description = None
	pixel_aspect = None
	while (file.tell() < end):
		atom_type, atom_end = readAtomHeader(file)
		if atom_type == None:
			break
		elif atom_type == "pasp":
			pixel_aspect = unpack(">2I", file.read(8))
		elif atom_type == "avcc":
			description = file.read(atom_end - file.tell())
		else:
			file.seek(atom_end - file.tell(), 1)
	return (information, description, pixel_aspect)

# Base Descriptor - Tag (8 bits) - Length - (8 or 32 bits (0x808080XX))
def readBaseDescriptor(file):
	tag = file.read(1)
	len = unpack(">B", file.read(1))[0]
	if ((len & 0x80) != 0): # Extended Descriptor -> 32 bits Length
		file.seek(2, 1) # two 0x80 bytes
		len = unpack(">B", file.read(1))[0] # length
	return len
	
# Mp4a Box
def parseMp4a(file, end):
	information = parseAudioSampleEntry(file)
	atom_type, atom_end = readAtomHeader(file) #  Esds
	file.seek(4, 1) # version + flags
	readBaseDescriptor(file) # ES Descriptor
	file.seek(2 + 1, 1)
	readBaseDescriptor(file) # Config Descriptor
	file.seek(1 + 1 + 3 + 4 + 4, 1)
	len = readBaseDescriptor(file) # Specific Descriptor
	description = file.read(len)
	file.seek(atom_end - file.tell(), 1) # If there is something else
	return (information, description)

# Sample Description Box
def parseStsd(file, length):
	file.seek(4, 1) # Version
	entry_count = unpack(">I", file.read(4))[0]

	descriptions = []
	
	for i in xrange(entry_count):
		format, atom_end = readAtomHeader(file)
		if format == "avc1":
			descriptions.append((format, parseAvc1(file, atom_end)))
		elif format == "mp4a":
			descriptions.append((format, parseMp4a(file, atom_end)))
		else:
			descriptions.append((format, file.read(atom_end - file.tell())))
			
	return (entry_count, descriptions)
	

# Decoding Time To Sample Box
def parseStts(file, end):
	file.seek(4, 1) # Version
	entry_count =  unpack(">I", file.read(4))[0]
	count = 2 * entry_count
	entries = unpack(">%iI" % (count), file.read(4 * count))
	return (entry_count, entries)
	
# Composition Time Offset Box
def parseCtts(file, end):
	file.seek(4, 1) # Version
	entry_count =  unpack(">I", file.read(4))[0]
	count = 2 * entry_count
	entries = unpack(">%iI" % (count), file.read(4 * count))
	return (entry_count, entries)
		
# Sample Size Box
def parseStsz(file, end):
	file.seek(4, 1) # Version
	sample_size = unpack(">I", file.read(4))[0]
	sample_count = unpack(">I", file.read(4))[0]
	entries = unpack(">%iI" % (sample_count), file.read(4 * sample_count))
	return (sample_size, sample_count, entries)
	
# Compact Sample Size Box
def parseStz2(file, end):
	file.seek(4, 1) # Version
	field_size = unpack(">B", file.read(1))[0]
	sample_count = unpack(">I", file.read(4))[0]
	if field_size == 4:
		table = unpack(">%iB" % (sample_count / 2), file.read(sample_count / 2))
		entries = []
		for i in xrange(sample_count / 2):
			entry = table[i]
			entries.append(entry >> 4)
			entries.append(entry & 0x0F)
	elif field_size == 8:
		entries = unpack(">%iB" % (sample_count), file.read(sample_count))

	elif field_size == 16:
		entries = unpack(">%iH" % (sample_count), file.read(2 * sample_count))
	return (sample_count, entries)
	
# Sample To Chunk Box
def parseStsc(file, end):
	file.seek(4, 1) # Version
	entry_count = unpack(">I", file.read(4))[0]
	count = 3 * entry_count
	entries = unpack(">%iI" % (count), file.read(4 * count)) # First Chunk, samples_per_chunk, sample_description_index
	offset = 1
	return (entry_count, entries, offset)
	
# Chunk Offset Box
def parseStco(file, end):
	file.seek(4, 1) # Version
	entry_count =  unpack(">I", file.read(4))[0]
	entries = unpack(">%iI" % (entry_count), file.read(4 * entry_count))
	return (entry_count, entries)
	
# Large Chunk Offset Box
def parseCo64(file, end):
	file.seek(4, 1) # Version
	entry_count =  unpack(">I", file.read(4))[0]
	entries = unpack(">%iQ" % (entry_count), file.read(8 * entry_count))
	return (entry_count, entries)

# Sync Sample Box
def parseStss(file, end):
	file.seek(4, 1) # Version
	entry_count = unpack(">I", file.read(4))[0]
	entries = unpack(">%iI" % (entry_count), file.read(4 * entry_count))
	offset = (0, 1)[entries[0] == 1]
	return (entry_count, entries, offset)
	
# Shadow Sync Sample Box
def parseStsh(file, end):
	file.seek(4, 1) # Version
	entry_count = unpack(">I", file.read(4))[0]
	count = 2 * entry_count
	entries = None
	offset = 0
	if entry_count > 0:
		entries = unpack(">%iI" % (count), file.read(4 * count)) # shadowed_sample_number, sync_sample_number
		offset = (0, 1)[entries[0] == 1]
	return (entry_count, entries, offset)

# Degradation Priority box
def parseStdp(file, end):
	file.seek(4, 1) # Version
	entry_count = (end - file.tell()) / 2
	entries = unpack(">%iH" % (entry_count), file.read(2 * entry_count))
	return (entry_count, entries)
		