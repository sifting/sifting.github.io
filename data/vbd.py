#Van Buren asset dump script
import os
import sys
from struct import unpack

def dump (file, manifest):
	GRP_MAGICK = 2
	GRP_VERSION = 1
	with open (file, 'rb') as f:
		#Read header and do basic sanity checks
		h = unpack ('<III', f.read (0xc))
		if h[0] != GRP_MAGICK:
			print ("file is not a GRP")
			return
		if h[1] != GRP_VERSION:
			print ("version must be 1")
			return
		#Extract file manifest
		cnt = h[2]
		files = []
		while cnt:
			files.append (unpack ('<II', f.read (0x8)))
			cnt -= 1
		#Create a directory for the goods
		p = os.path.splitext (file)[0]
		if not os.path.exists (p):
			os.makedirs (p)
		#Dump the files in the manifest
		num = 0
		for e in files:
			f.seek (e[0])
			data = f.read (e[1])
			#Do some lazy file type checks
			if data[:4] == 'RIFF': suffix = '.wav'
			elif data[:4] == 'EEN2': suffix = '.ent'
			elif data[:4] == 'B3D ': suffix = '.b3d'
			elif data[:4] == 'VEG ': suffix = '.veg'
			elif len (data) >= 4 and (unpack ('<I', data[:4])[0] == 0xcab067b8): suffix = '.skel'
			else: suffix = '.bin'
			#Dump the data
			with open (p + '/' + manifest[num][3] + suffix, 'wb') as bin:
				bin.write (data)
			num += 1
def main ():
	RHT_MAGICK = 1
	RHT_VERSION = 1
	if len (sys.argv) < 2:
		print ("vbd.py resource.rht")
		return
	
	with open (sys.argv[1], 'rb') as f:
		#Read header and do basic sanity checks
		#uint magick (must be 1)
		#uint version (must be 1)
		#uint total number of assets
		#uint offset to group name table
		#uint offset to item name table
		print ("Extract files from %s..." % sys.argv[1])
		h = unpack ('<IIIII', f.read (0x14))
		if h[0] != RHT_MAGICK:
			print ("file is not a RHT")
			return
		if h[1] != RHT_VERSION:
			print ("version must be 1")
			return
		#Extract file manifest
		#uint unk1 (always set to 1)
		#uint file id (monotonic increase from 0)
		#uint unk2
		#uint offset to name in item name table
		#uint offset to group name in group name table
		cnt = h[2]
		manifest = {}
		while cnt:
			def readstring ():
				#Read null terminated string
				str = ""
				while True:
					c = f.read (1)
					if c != '\0': str += c
					else: break
				return str
			#Read entry and add it to the appropriate manifest bucket
			e = unpack ('<IIIII', f.read (0x14))
			save = f.tell ()
			f.seek (h[4] + e[3])
			name = readstring ()
			f.seek (h[3] + e[4])
			group = readstring ()
			f.seek (save)
			#Ensure a manifest exists for the given group
			if group not in manifest:
				manifest[group] = []
			#Add the entry into the manifest
			manifest[group].append ((e[0], e[1], e[2], name, group))
			cnt -= 1
		#Print out info
		for k, v in manifest.iteritems ():
			print ("%i files in group %s" % (len (v), k))
			dump ('data/' + k + '.GRP', v)
	print ("Okay")

#Stupid python boilerplate
if __name__ == "__main__":
	main ()