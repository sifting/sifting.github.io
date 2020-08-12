from FbxCommon import *
from struct import pack
import os

def hashbones (bones):
	import binascii
	x = str (len (bones))
	for b in bones:
		x += '_' + b.GetName () + '.' + str (b.GetChildCount ())
	return binascii.crc32 (x)

def cir3mesh (scene, bones, meshes, base):
	VERSION = 1
	raw = pack ('<4cI', 'C', 'I', 'R', '3', VERSION)
	print ("Generating cir3mesh...")
	#Write out the bones
	print (" Writing out bones...")
	hash = hashbones (bones)
	block = pack ('<II', hash, len (bones))
	for b in bones:
		data = pack ('<I', len (b.GetName ()))
		data += str (b.GetName ())
		block += data
		print ("   {0}".format (b.GetName ()))
	raw += pack ('<I', len (block)) + block
	print ("   Hash: %x" % hash)
	#Write out meshes
	print (" Writing out meshes...")
	block = pack ('<I', len (meshes))
	#This handy helper goes and plumbs the depths of each bone's skin cluster
	#and saves the (bone, weight) tuple into a handy list. once all 
	#influences have been found, it returns the list.
	def handy_helper (mesh, index):
		x = []
		for i in range (mesh.GetDeformerCount (FbxDeformer.eSkin)):
			dform = mesh.GetDeformer (i, FbxDeformer.eSkin)
			for j in range (dform.GetClusterCount ()):
				cluster = dform.GetCluster (j)
				#Cache the bone index in the list
				bone = bones.index (cluster.GetLink ())
				#Cache the stores from the cluster
				indices = cluster.GetControlPointIndices ()
				weights = cluster.GetControlPointWeights ()
				try:
					k = indices.index (index)
					x.append ((bone, weights[k]))
				except ValueError:
					#This bone doesn't influence the given control point
					continue
		#Return result set
		return x
	#Digest meshes into something sane and usable
	for m in meshes:
		class Vertex:
			def __init__ (self, point, normal, uvs, weights):
				self.point = point
				#Compress the normal into 8 bit values
				self.cn = [0, 0, 0, 0]
				for i in range (3):
					self.cn[i] = int (127.0*normal[i])
				self.normal = normal
				#Compress the UVs into 16 bits
				self.cu = [int (0x7fff*uvs[0]), int (0x7fff*uvs[1])]
				self.uvs = uvs
				#Ensure no more than four weights
				if 4 < len (weights):
					raise Exception ("More than 4 weights/vertex!")
				#Ensure total influence is ~1.0
				if len (weights):
					sum = 0
					for w in weights: 
						sum += w[1]
					if sum < 0.99 or 1.01 < sum:
						raise Exception ("Normalise your weights!")
				#Set up the weights to fit inside 8 bit values
				#Also, there are always four of them
				x = [[0, 0], [0, 0], [0, 0], [0, 0]]
				for i in range (len (weights)):
					x[i][0] = weights[i][0]
					x[i][1] = int (255.0*weights[i][1])
				#Keep the source data around because we can
				self.weights = weights
				self.cw = x
			def compare (self, other):
				if self.point != other.point: return False
				if self.normal != other.normal: return False
				if self.uvs != other.uvs: return False
				#Not necessary to check weights, they're set per point
				return True
			def __eq__ (self, other):
				return self.compare (other)
			def __ne__ (self, other):
				return not self.compare (other)
			def __hash__ (self):
				hash = 5381
				for i in range (3):
					hash = ((hash<<5) + hash) ^ int (65535.0*self.point[i])
				return hash
		remap = {}
		verts = []
		indices = []
		uvs = m.GetLayer (0).GetUVs ()
		points = m.GetControlPoints () 
		for i in range (m.GetPolygonCount ()):
			for j in range (m.GetPolygonSize (i)):
				#Grab the control point
				cp = points[m.GetPolygonVertex (i, j)]
				#Grab normals
				if False:
					no = FbxVector4 (0, 0, 0, 0)
				else:
					no = FbxVector4 (0, 0, 0, 0)
				#Pull out UVs
				if uvs is not None:
					index = m.GetTextureUVIndex (i, j)
					uv = uvs.GetDirectArray ().GetAt (index)
				else:
					uv = FbxVertex2 (0, 0)	
				#Pull out vertex weights
				weights = handy_helper (m, cp)
				#Create a new unique vertex
				v = Vertex (cp, no, uv, weights)
				if not v in remap:
					num = len (verts)
					verts[num:] = [v]
					remap[v] = num
				id = remap[v]
				#Rewrite indices using new vertices as appropriate
				indices.append (id)
		#write mesh name
		data = pack ('<I', len (m.GetName ()))
		data += str (m.GetName ())
		#Write vertices
		data += pack ('<I', len (verts))
		for v in verts:
			data += pack ('<3f2h4B4B4B',\
							v.point[0], v.point[1], v.point[2],\
							v.cu[0], v.cu[1],\
							v.cn[0], v.cn[1], v.cn[2], v.cn[3],\
							v.cw[0][0], v.cw[1][0], v.cw[2][0], v.cw[3][0],\
							v.cw[0][1], v.cw[1][1], v.cw[2][1], v.cw[3][1])
		#Write indices
		data += pack ('<I', len (indices))
		for n in indices:
			data += pack ('<H', n)
		block += data
		print (" Mesh: {0}".format (m.GetName ()))
		print ("  Points {0}".format (len (points)))
		print ("  Verts: {0}".format (len (verts)))
		print ("  Indices: {0}".format (len (indices)))
	raw += pack ('<I', len (block)) + block
	#Dump it all to disk
	with open (base + '.cir3mesh', 'w') as f:
		f.write (raw)
	
def cir3anim (scene, bones, hits, hurts, base):
	VERSION = 1
	raw = pack ('<4cI', 'A', 'N', 'I', '3', VERSION)
	print ("Generating cir3anim...")
	settings = scene.GetGlobalSettings ()
	#Extract length of animation
	timeline = settings.GetTimelineDefaultTimeSpan ()
	length = timeline.GetDuration ().GetFramedTime ()
	nframes = length.GetFrameCount (settings.GetTimeMode ())
	rate = FbxTime.GetFrameRate (settings.GetTimeMode ())
	sec = length.GetSecondDouble ()
	print ("  Frames: %i" % nframes)
	print ("  Frame rate: %f" % rate)
	print ("  Length (seconds): %f" % sec)
	#Make a header for the animation
	hash = hashbones (bones)
	print ("  Hash: %x" % hash)
	header = pack ('<IIff', hash, nframes, sec, rate)
	raw += header
	#Sample each bone over each frame and write it to the raw blob
	block = pack ('<I', len (bones))
	print ('  Writing skeleton animation...')
	for b in bones:
		data = bytes ()
		time = FbxTime (0)
		#print (b.GetName ())
		for i in range (nframes):
			#Evaluate the local transform for this frame
			time.SetFrame (i, settings.GetTimeMode ())
			tform = b.EvaluateLocalTransform (time)
			#Decompose it into versor and translation vector
			q = tform.GetQ ()
			t = tform.GetT ()
			q.Normalize ()
			#Write to the data block
			data += pack ('<4f3f', q[0], q[1], q[2], q[3], t[0], t[1], t[2])
		block += data
	raw += pack ('<I', len (block)) + block
	#Now write out the hit shapes
	#should be hits lol
	block = pack ('<I', len (hurts))
	print ('  Writing hit shape animation...')
	for s in hurts:
		data = bytes ()
		time = FbxTime (0)
		for i in range (nframes):
			#Evaluate the GLOBAL transform for this frame
			time.SetFrame (i, settings.GetTimeMode ())
			tform = s.GetNode ().EvaluateGlobalTransform (time)
			t = tform.GetT ()
			#Write it to the block
			data += pack ('<3f', t[0], t[1], t[2])
		block += data
	raw += pack ('<I', len (block)) + block
	#Dump it all to disk
	with open (base + '.cir3anim', 'w') as f:
		f.write (raw)
		
def cir3bind (bones, base):
	VERSION = 1
	raw = pack ('<4cI', 'B', 'N', 'D', '3', VERSION)
	#Write out bind pose
	print ("Generating cir3bind...")
	hash = hashbones (bones)
	raw += pack ('<I', hash)
	print ("  Hash: %x" % hash)
	block = pack ('<I', len (bones))
	for b in bones:
		data = bytes ()
		mat = b.EvaluateLocalTransform (FbxTime (0)).Inverse ()
		#Write out as a 3x4 column major matrix
		for k in range (3):
			v = mat.GetColumn (k)
			data += pack ('<4f', v[0], v[1], v[2], v[3])
		block += data
	raw += pack ('<I', len (block)) + block
	#Dump it to disk
	with open (base + '.cir3bind', 'w') as f:
		f.write (raw)

def boot ():
	#Parse args
	import sys
	if len (sys.argv) <= 1:
		print ("Usage: cex <FBX>")
		return
	#Prepare the FBX SDK
	sdk, scene = InitializeSdkObjects ()
	#Load FBX
	if not LoadScene (sdk, scene, sys.argv[1]):
		raise Exception ("Failed to load FBX/DAE file!")
	#Clip path name
	base = os.path.splitext (sys.argv[1])[0]
	#Layer stuff
	_hurt = None
	_hit = None
	_meshes = None
	_layers = {}
	def ha_ha_im_bad (layer, what):
		x = _layers[layer]
		if not x: return False
		return x.IsMember (what)
	def is_hurt (what):
		return ha_ha_im_bad ('hurt', what)
	def is_hit (what):
		return ha_ha_im_bad ('hit', what)
	def is_mesh (what):
		return ha_ha_im_bad ('meshes', what)
	#Gather relevant display layers
	names = ['hit', 'hurt', 'meshes']
	for i in range (len (names)):
		x = scene.FindSrcObject (names[i])
		if not x:
			continue
		if x.ClassId.GetFbxFileTypeName () != 'CollectionExclusive':
			continue
		print ('Found hurt layer (%i)' % x.GetMemberCount ())
		for j in range (x.GetMemberCount ()):
			print ("  %s" % x.GetMember (j).GetName ())
		_layers[names[i]] = x
	#Gather relevant nodes for later processing
	root = scene.GetRootNode ()
	skel = None
	meshes = []
	hits = []
	hurts = []
	print ("Gathering nodes...")
	for i in range (root.GetChildCount ()):
		ch = root.GetChild (i)
		type = ch.GetNodeAttribute ().GetAttributeType ()
		#Grab skeleton node, ensuring there is only one of them
		if type == FbxNodeAttribute.eSkeleton:
			if skel is None:
				skel = ch
			else:
				raise Exception ("More than one skeleton!")
		#Gather meshes into appropriate places
		elif type == FbxNodeAttribute.eMesh:
			if is_mesh (ch):
				meshes.append (ch.GetNodeAttribute ())
			elif is_hit (ch):
				hits.append (ch.GetNodeAttribute ())
			elif is_hurt (ch):
				hurts.append (ch.GetNodeAttribute ())
	if skel is not None: print (" found a skeleton")
	else: print (" no skeleton found")
	print (" {0} meshes".format (len (meshes)))
	print (" {0} hit shapes".format (len (hits)))
	print (" {0} hurt shapes".format (len (hurts)))
	#Flatten skeleton into a list
	bones = []
	def collapse (node, depth):
		#Print out new hierarchy
		ident = " "
		for i in range (depth):
			ident += "  "
		print ("{0}{1}".format (ident, node.GetName ()))
		#Add to list and descend into children
		#Doing it this way ensures parents are always transformed before
		#their children, so we can skip any sort of recursion during runtime
		bones.append (node)
		for i in range (node.GetChildCount ()):
			collapse (node.GetChild (i), depth + 1)
	#Convert data into something sane and usable
	if skel is not None:
		print ("Collapsing skeleton...")
		collapse (skel, 0)
		#Write a cir3mesh if we have meshes too
		if len (meshes) != 0: 
			cir3mesh (scene, bones, meshes, base)
			cir3bind (bones, base)
		#Write animations
		cir3anim (scene, bones, hits, hurts, base)
	# Destroy all objects created by the FBX SDK.
	sdk.Destroy()

#Weird bootstrap
if __name__ == "__main__":
	boot ()
