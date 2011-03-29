import hashlib, hmac, time
from random import randint
from Bytes import BytesInput, BytesOutput
from struct import pack, unpack
from M2Crypto import DH

HANDSHAKE_SIZE 			= 1536
SHA256_DIGEST_SIZE		= 32
SERVER_KEY_SIZE 		= 68
PLAYER_KEY_SIZE 		= 62
GENUINE_SERVER_KEY_SIZE = 36
GENUINE_PLAYER_KEY_SIZE = 30
PUBLIC_KEY_SIZE 		= 128

SERVER_KEY = pack(">%dB" % SERVER_KEY_SIZE,  
	0x47,0x65,0x6e,0x75,0x69,0x6e,0x65,0x20,0x41,0x64,0x6f,0x62,0x65,0x20,0x46,0x6c,
	0x61,0x73,0x68,0x20,0x4d,0x65,0x64,0x69,0x61,0x20,0x53,0x65,0x72,0x76,0x65,0x72,
	0x20,0x30,0x30,0x31,0xf0,0xee,0xc2,0x4a,0x80,0x68,0xbe,0xe8,0x2e,0x00,0xd0,0xd1,
	0x02,0x9e,0x7e,0x57,0x6e,0xec,0x5d,0x2d,0x29,0x80,0x6f,0xab,0x93,0xb8,0xe6,0x36,
	0xcf,0xeb,0x31,0xae)
	
PLAYER_KEY = pack(">%dB" % PLAYER_KEY_SIZE, 
	0x47,0x65,0x6e,0x75,0x69,0x6e,0x65,0x20,0x41,0x64,0x6f,0x62,0x65,0x20,0x46,0x6c,
	0x61,0x73,0x68,0x20,0x50,0x6c,0x61,0x79,0x65,0x72,0x20,0x30,0x30,0x31,
	0xf0,0xee,0xc2,0x4a,0x80,0x68,0xbe,0xe8,0x2e,0x00,0xd0,0xd1,0x02,0x9e,0x7e,0x57,
	0x6e,0xec,0x5d,0x2d,0x29,0x80,0x6f,0xab,0x93,0xb8,0xe6,0x36,0xcf,0xeb,0x31,0xae);	
	
SCHEMES = {0x800001020:0, 0x80000302:1}
	
def readWelcome(input):
	if input.readByte() != 0x03:
		raise Exception, "Invalid Welcome"

def readHandshake(input):
	return input.read(HANDSHAKE_SIZE)
	
def makeHandshakeResponse(handshake):
	flash_plugin_version = unpack(">I", handshake[4:8])[0]
	#scheme = SCHEMES.get(flash_plugin_version, 0)
	scheme = validateClient(handshake)
	print "scheme", scheme
	
	handshake = prepareHandshake(handshake, scheme);
	
	output = BytesOutput(True)
	output.writeByte(0x03)
	output.write(makeHandshakePart1(handshake, scheme))
	output.write(makeHandshakePart2(handshake, scheme))
	return output.getBytes()
		
def makeHandshakePart1(handshake, scheme = 0):
	uptime = pack("!I", int(time.time()))
	version = pack(">4B", *(0x03, 0x05, 0x00, 0x01))
	
	size = HANDSHAKE_SIZE - 8
	message = pack(">%dB" % size, *[randint(0x00, 0xFF) for i in xrange(0, size)])
	
	message = uptime + version + message
	
	if ord(handshake[4]) != 0:
		return setHandshakeDigest(message, scheme)
	else:
		return message
		
def makeHandshakePart2(handshake, scheme = 0):
	if ord(handshake[4]) == 0:
		return handshake
	else:
		# uptime = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(unpack(">I", handshake[0:4])[0]))
		# version = handshake[4] + handshake[5] + handshake[6] + handshake[7]
		
		# print uptime, version
		
		offset = getOffset(handshake, scheme)
		offset = getOffset(handshake[0:HANDSHAKE_SIZE - SHA256_DIGEST_SIZE], scheme)
		
		key_part = handshake[offset:offset + SHA256_DIGEST_SIZE]
		digest_key = digest(SERVER_KEY, key_part)
		
		#signature_key = digest(digest_key, handshake[0:HANDSHAKE_SIZE - SHA256_DIGEST_SIZE])
		
		size = HANDSHAKE_SIZE - SHA256_DIGEST_SIZE
		random_data = pack(">%dB" % size, *[randint(0x00, 0xFF) for i in xrange(0, size)])
		
		hashed_key = digest(digest_key, random_data)
		
		return random_data + hashed_key
		
		#return handshake[0:HANDSHAKE_SIZE - SHA256_DIGEST_SIZE] + signature_key
		
		# size = HANDSHAKE_SIZE - SHA256_DIGEST_SIZE
		# random_data = pack(">%dB" % size, *[randint(0x00, 0xFF) for i in xrange(0, size)])
		
		# hashed_key = digest(new_key, random_data)
		
		# return random_data + hashed_key

def setHandshakeDigest(handshake, scheme = 0):
	offset = getOffset(handshake, scheme)
		
	message = handshake[0:offset] + handshake[offset + SHA256_DIGEST_SIZE:]
		
	key = digest(SERVER_KEY[0:GENUINE_SERVER_KEY_SIZE], message)
		
	return handshake[0:offset] + key + handshake[offset + SHA256_DIGEST_SIZE:]
	
def digest(key, message):
	h = hmac.new(key, message, hashlib.sha256)
	return h.digest()	
		
def getOffset(handshake, scheme = 0):
	scheme_offset = (12, 776)[scheme]
	offset = sum(unpack(">4B", handshake[scheme_offset-4:scheme_offset])) % 728 + scheme_offset
	
	if (offset + 32) >= HANDSHAKE_SIZE:
		raise Exception, "Invalid Handshake Offset"
	else:
		return offset
		

def calculateOffset(handshake, pointer, modulus, increment, size):
	offset = sum(unpack(">4B", handshake[pointer:pointer+4])) % modulus + increment
	if (offset + size) >= HANDSHAKE_SIZE:
		raise Exception, "Invalid Handshake Offset"
	else:
		return offset
		
def getDigestOffset(handshake, scheme = 0):
	if scheme == 0:
		return calculateOffset(handshake, 8, 728, 12, SHA256_DIGEST_SIZE)
	elif scheme == 1:
		return calculateOffset(handshake, 772, 728, 776, SHA256_DIGEST_SIZE)

def getPublicKeyOffset(handshake, scheme = 0):
	if scheme == 0:
		return calculateOffset(handshake, 1532, 632, 772, PUBLIC_KEY_SIZE)
	elif scheme == 1:
		return calculateOffset(handshake, 768, 632, 8, PUBLIC_KEY_SIZE)
	
def generatePublicKey():
	a = DH.gen_params(PUBLIC_KEY_SIZE, 2)
	a.gen_key()
	
	public_key = a.pub
	public_key_length = len(public_key)
	
	if public_key_length < PUBLIC_KEY_SIZE:
		length = PUBLIC_KEY_SIZE - public_key_length
		public_key = pack(">%dB" % length, *[0x00 for i in xrange(0, length)]) + public_key
	elif public_key_length > PUBLIC_KEY_SIZE:
		public_key = public_key[0:PUBLIC_KEY_SIZE]
		
	print "public key length:", len(public_key)
	return public_key

	
def prepareHandshake(handshake, scheme):
	public_key_offset = getPublicKeyOffset(handshake, scheme)
	
	public_key = generatePublicKey()
	
	return handshake[0:public_key_offset] + public_key + handshake[public_key_offset + PUBLIC_KEY_SIZE:]
	
def validateClientScheme(data, scheme):
	offset = getOffset(data, scheme)
	temp_data = data[0:offset] + data[offset + SHA256_DIGEST_SIZE:]
	temp_hash = digest(PLAYER_KEY[0:GENUINE_PLAYER_KEY_SIZE], temp_data)

	for i in range(SHA256_DIGEST_SIZE):
		if data[offset + i] != temp_hash[i]:
			return False
	return True
	
def validateClient(data):
	if validateClientScheme(data, 0):
		print "scheme: 2"
		return 0
	elif validateClientScheme(data, 1):
		print "scheme: 1"
		return 1
	else:
		print "validation failed"
		return 1
	# else:
		# raise Exception, "Invalid Handshake Scheme"
		