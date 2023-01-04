import sys
import os
sys.path.append('gen-py')
#check if all necessary files are present
if not os.path.isfile("env.txt"):
	print("please provide env.txt before running")
	sys.exit()
path_variables = open("env.txt", "r")
f1 = path_variables.readlines()
for line in f1:
    	data = line.split(" ")
    	sys.path.append(data[1].rstrip("\n"))
if not os.path.isfile("config.cfg"):
	print("please provide config.cfg before running")
	sys.exit()
import configparser
import random
import time
import shutil
import threading
from thrift.transport import TSocket
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol
from thrift.server import TServer
from QuorumService import QuorumService

class NodeHandler:
	def __init__(self, nodeIndex):
		parser = configparser.ConfigParser()
		parser.read('config.cfg')
		self.addresses = parser['Node']['address'].rstrip("\n").split(", ")
		self.ports = parser['Node']['port'].rstrip("\n").split(", ")
		self.currAddress = self.addresses[nodeIndex]
		self.currPort = int(self.ports[nodeIndex])
		self.coordIndex = int(parser['Node']['coord'])
		self.coordAddress = self.addresses[self.coordIndex]
		self.coordPort = int(self.ports[self.coordIndex])
		self.nodeIndex = nodeIndex
		self.nodes = []
		for i in range(0, len(self.addresses)):
			self.nodes.append(self.addresses[i]+", "+self.ports[i])
		self.fileVersion = {}
		self.fileReplica = {}
		self.replicaPath = parser['Node']['replica'].rstrip("\n")+str(nodeIndex)
		self.createReplicaFiles(parser['Quorum']['files'].rstrip("\n"))
		
		#if the current node is coordinator then initialize locks for each file
		if self.coordIndex == nodeIndex:
			self.fileLock = {}
			for fname in self.fileVersion.keys():
				self.fileLock[fname] = threading.RLock()
			self.readQuorumSize = int(parser['Quorum']['quorum_read'])
			self.writeQuorumSize = int(parser['Quorum']['quorum_write'])
		
	''' Create replica files in each node'''
	def createReplicaFiles(self, filesPath):
		files = os.listdir(filesPath)
		shutil.copytree(filesPath, self.replicaPath, dirs_exist_ok = True)
		for fname in files:
			self.fileVersion[fname] = 1
			self.fileReplica[fname] = self.replicaPath+"/"+fname
	
	''' Sends the write request to the coordinator and returns the status of the request'''		
	def write(self, file, data):
		print("")
		print("Write request to the file : "+file+" received from client")
		success = False
		if self.coordIndex == self.nodeIndex:
			print("Coordinator received the write request to the file: "+file)
			success = self.coordinatorWrite(file, data)
		else:
			print("Write request forwarded to the coordinator node")
			transport = TSocket.TSocket(self.coordAddress, port=self.coordPort)
			transport = TTransport.TBufferedTransport(transport)
			protocol = TBinaryProtocol.TBinaryProtocol(transport)
			client = QuorumService.Client(protocol)
			transport.open()
			success = client.coordinatorWrite(file, data)
			transport.close()
		print("")	
		return success
	
	'''Sends the read request to the coordinator and returns the content of the file'''	
	def read(self, file):
		print("")
		print("Read request to the file: "+file+" received from client")
		content = ""
		if self.coordIndex == self.nodeIndex:
			print("Coordinator received the read request to the file: "+file)
			content = self.coordinatorRead(file)
		else:
			print("Read request forwarded to the coordinator node")
			transport = TSocket.TSocket(self.coordAddress, port=self.coordPort)
			transport = TTransport.TBufferedTransport(transport)
			protocol = TBinaryProtocol.TBinaryProtocol(transport)
			client = QuorumService.Client(protocol)
			transport.open()
			content = client.coordinatorRead(file)
			transport.close()
		print("")	
		return content
	
		
	def coordinatorWrite(self, file, data):
		#if file is not present 
		if file not in self.fileLock:
			self.fileVersion[file] = 0
			self.fileLock[file] = threading.RLock()
			
		# Lock the file before the write so only one client can access it
		replicaFileLock = self.fileLock[file]
		replicaFileLock.acquire()
		#Coordinator picks ramdom nodes of size N_w 
		quorumNodes = self.getQuorumNodes(self.writeQuorumSize)
		print("Selected nodes for writing to the file "+file+" are: ")
		print(quorumNodes)
		maxVersion = 0
		currVersion = 0
		#Get the latest version of the file
		for node in quorumNodes:
			if node == self.nodes[self.nodeIndex]:
				currVersion = self.getFileVersion(file)
			else:
				address = node.split(", ")[0]
				port = int(node.split(", ")[1])
				transport = TSocket.TSocket(address, port=port)
				transport = TTransport.TBufferedTransport(transport)
				protocol = TBinaryProtocol.TBinaryProtocol(transport)
				client = QuorumService.Client(protocol)
				transport.open()
				currVersion = client.getFileVersion(file)
				transport.close()
			if maxVersion<currVersion:
				maxVersion = currVersion
				
		#write the data to the quorum nodes and set the version of the file to latest version +1
		success = False
		for node in quorumNodes:
			if node == self.nodes[self.nodeIndex]:
				success = self.fileWrite(file, data, maxVersion+1)
			else:
				address = node.split(", ")[0]
				port = int(node.split(", ")[1])
				transport = TSocket.TSocket(address, port=port)
				transport = TTransport.TBufferedTransport(transport)
				protocol = TBinaryProtocol.TBinaryProtocol(transport)
				client = QuorumService.Client(protocol)
				transport.open()
				success = client.fileWrite(file, data, maxVersion+1)
				transport.close()
		replicaFileLock.release()
		return success
		
	def coordinatorRead(self, file):
		#Coordinator picks ramdom nodes of size N_r
		quorumNodes = self.getQuorumNodes(self.readQuorumSize)
		print("Selected nodes for reading to the file "+file+" are: ")
		print(quorumNodes)
		maxVersion = 0
		currVersion = 0
		requiredNode = ""
		#Get the latest version of the file and the node information containing this file
		for node in quorumNodes:
			if node == self.nodes[self.nodeIndex]:
				currVersion = self.getFileVersion(file)
			else:
				address = node.split(", ")[0]
				port = int(node.split(", ")[1])
				transport = TSocket.TSocket(address, port=port)
				transport = TTransport.TBufferedTransport(transport)
				protocol = TBinaryProtocol.TBinaryProtocol(transport)
				client = QuorumService.Client(protocol)
				transport.open()
				currVersion = client.getFileVersion(file)
				transport.close()
			if maxVersion<currVersion:
				maxVersion = currVersion
				requiredNode = node
		#If the latest version is zero requested file is not present 
		if maxVersion == 0:
			print("File requested by the client is not found")
			return "File not found"
		content = ""
		
		#Read the file contents from the node with latest version
		if node == self.nodes[self.nodeIndex]:
			content = self.fileRead(file)
		else:
			address = requiredNode.split(", ")[0]
			port = int(requiredNode.split(", ")[1])
			transport = TSocket.TSocket(address, port=port)
			transport = TTransport.TBufferedTransport(transport)
			protocol = TBinaryProtocol.TBinaryProtocol(transport)
			client = QuorumService.Client(protocol)
			transport.open()
			content = client.fileRead(file)
			transport.close()
		return content
	
	''' Picks random nodes of given size from the network'''
	def getQuorumNodes(self, size):
		return random.sample(self.nodes, size)
	
	'''Get the version of the file in the current node'''	
	def getFileVersion(self, file):
		if file in self.fileVersion:
			return self.fileVersion[file]
		else:
			return 0
	
	'''return the file content in the current node '''		
	def fileRead(self, file):
		print("Reading from the file: "+file)
		filePath = self.fileReplica[file]
		fRead = open(filePath, "r")
		content = fRead.read()
		return content
	
	'''writes to the file in the current node'''
	def fileWrite(self, file, data, fileVersion):
		currNodeVersion = self.getFileVersion(file)
		print("Writing to the file: "+file)
		#if the file is not present new file is created
		if currNodeVersion == 0:
			self.fileReplica[file] = self.replicaPath+"/"+file
		elif currNodeVersion>=fileVersion:
			print("file is already uptodate")
			return False
		filePath = self.fileReplica[file]
		fWrite = open(filePath, "w")
		fWrite.write(str(fileVersion)+"\n"+data)
		self.fileVersion[file] = fileVersion
		return True
	
	'''List all the files and their latest versions by contacting the coordinator'''	
	def listAllFiles(self):
		if self.coordIndex == self.nodeIndex:
			files = self.coordinatorFiles()
		else:
			transport = TSocket.TSocket(self.coordAddress, port=self.coordPort)
			transport = TTransport.TBufferedTransport(transport)
			protocol = TBinaryProtocol.TBinaryProtocol(transport)
			client = QuorumService.Client(protocol)
			transport.open()
			files = client.coordinatorFiles()
			transport.close()
			
		return files
	
	''' Coordinator gets the latest version of all files'''	
	def coordinatorFiles(self):
		quorumNodes = self.getQuorumNodes(self.readQuorumSize)
		files = ""
		for fname in self.fileReplica.keys():
			maxVersion = 0
			currVersion = 0
			for node in quorumNodes:
				if node == self.nodes[self.nodeIndex]:
					currVersion = self.getFileVersion(fname)
				else:
					address = node.split(", ")[0]
					port = int(node.split(", ")[1])
					transport = TSocket.TSocket(address, port=port)
					transport = TTransport.TBufferedTransport(transport)
					protocol = TBinaryProtocol.TBinaryProtocol(transport)
					client = QuorumService.Client(protocol)
					transport.open()
					currVersion = client.getFileVersion(fname)
					transport.close()
				if maxVersion<currVersion:
					maxVersion = currVersion
			files = files+"File Name: "+fname+" File Version: "+str(maxVersion)+"\n"
		return files
			
	
		
			
		
		
		
			
	
		
		
		
    	

