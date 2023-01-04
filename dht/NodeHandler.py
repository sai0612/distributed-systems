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
import hashlib
import random
import time
from thrift.transport import TSocket
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol
from thrift.server import TServer
from DHTSuperNodeService import DHTSuperNodeService
from DHTNodeService import DHTNodeService

class FingerTableContent:
	def __init__(self):
		self.succNodeInfo = ""
		self.start = None
		self.end = None
	def setSuccNodeInfo(self, node):
		self.succNodeInfo = node
	
class NodeHandler:
	
	def __init__(self, nodeIndex):
		parser = configparser.ConfigParser()
		parser.read('config.cfg')
		self.address = parser['Node']['address'].split(", ")[nodeIndex]
		self.port = int(parser['Node']['port'].split(", ")[nodeIndex])
		self.DHTSize = int(parser['DHT']['node_count'])
		self.noOfBits = int(parser['DHT']['bits'])
		self.keySpace = pow(2, self.noOfBits)
		self.fingerTable = []
		self.successor = None
		self.predecessor = None
		self.nodeId = None
		self.dictionary = {}
		self.cache = {}
		self.joinDHT()
		
	''' contacts super node to join DHT '''	
	def joinDHT(self):
		nodeId = -1
		parser = configparser.ConfigParser()
		parser.read('config.cfg')
		port= parser['SuperNode']['port']
		address = parser['SuperNode']['address']
		transport = TSocket.TSocket(address, port=int(port))
		transport = TTransport.TBufferedTransport(transport)
		protocol = TBinaryProtocol.TBinaryProtocol(transport)
		client = DHTSuperNodeService.Client(protocol)
		randomNodeInfo = None
		
		#contact super node until join request is granted
		while nodeId == -1:
			transport.open()
			randomNodeInfo = client.GetNodeForJoin(self.address, self.port)
			nodeId = int(randomNodeInfo.split(", ")[0])
			if nodeId != -1:
				break
			time.sleep(100)
			
		
		self.nodeId = nodeId
		randomNodeAddress = randomNodeInfo.split(", ")[1]
		randomNodePort = randomNodeInfo.split(", ")[2]
		randomNodeId = randomNodeInfo.split(", ")[3]
		randomNodeInfo = randomNodeAddress+", "+randomNodePort+", "+randomNodeId
		
		#initialize finger table for the new node
		for i in range(0, self.noOfBits):
			finger = FingerTableContent()
			finger.start = (self.nodeId+pow(2, i))%self.keySpace
			finger.end = (self.nodeId+pow(2, i+1))%self.keySpace
			self.fingerTable.append(finger)
			
		#if it is the first node to join the network
		if randomNodeAddress == self.address and int(randomNodePort) == self.port:
			self.predecessor = randomNodeInfo
			for i in range (0, self.noOfBits):
				self.fingerTable[i].succNodeInfo = randomNodeInfo
			self.successor = self.fingerTable[0].succNodeInfo
		else:
			self.initFingerTable(randomNodeInfo)
			
			#update predecessor for the successor
			succNode = self.successor.split(", ")
			transport1 = TSocket.TSocket(succNode[0], port=int(succNode[1]))
			transport1 = TTransport.TBufferedTransport(transport1)
			protocol1 = TBinaryProtocol.TBinaryProtocol(transport1)
			client1 = DHTNodeService.Client(protocol1)
			transport1.open()
			client1.updatePredecessor(self.address+", "+str(self.port)+", "+str(self.nodeId))
			transport1.close()
			
			#update other nodes finger tables
			for i in range(0, self.noOfBits):
				predecessor = self.findPredecessor((self.nodeId - pow(2, i) + self.keySpace+1)%self.keySpace).split(", ")
				if (predecessor[0] != self.address or int(predecessor[1]) != self.port):
					transport1 = TSocket.TSocket(predecessor[0], port=int(predecessor[1]))
					transport1 = TTransport.TBufferedTransport(transport1)
					protocol1 = TBinaryProtocol.TBinaryProtocol(transport1)
					client1 = DHTNodeService.Client(protocol1)
					transport1.open()
					client1.updateFingerTable(self.address+", "+str(self.port)+", "+str(self.nodeId), i)
					transport1.close()
			succNode = self.successor.split(", ")
			transport1 = TSocket.TSocket(succNode[0], port=int(succNode[1]))
			transport1 = TTransport.TBufferedTransport(transport1)
			protocol1 = TBinaryProtocol.TBinaryProtocol(transport1)
			client1 = DHTNodeService.Client(protocol1)
			transport1.open()
			updatedIndices = client1.getSuccessorUpdates(self.address+", "+str(self.port)+", "+str(self.nodeId))
			transport1.close()
			
			#update the current node finger table
			
			for j in range(0, len(updatedIndices)):
				succId = int(self.fingerTable[updatedIndices[j]].succNodeInfo.split(", ")[2])
				normal = 1
				if self.fingerTable[updatedIndices[j]].start>succId:
					normal=0
				if (normal == 1 and (self.nodeId>=self.fingerTable[updatedIndices[j]].start and self.nodeId<succId) or (normal ==0 and (self.nodeId>=self.fingerTable[updatedIndices[j]].start or self.nodeId<succId))):
					self.fingerTable[updatedIndices[j]].setSuccNodeInfo(self.address+", "+str(self.port)+", "+str(self.nodeId))
				
		
		#notify super node about the successful join	
		client.PostNode(self.address, self.port)	
		transport.close()
		
		#print the new node finger table
		print("Node Information of the new node")
		print(self.getNodeInfo())
			
		print(str(self.nodeId), " Node joined the DHT successfully")
	
	''' initialize finger table and successor and predecessor info '''	
	def initFingerTable(self, randomNodeInfo):
		randomNodeInfo = randomNodeInfo.split(", ")
		
		# get info of the successor node from the random Node
		transport1 = TSocket.TSocket(randomNodeInfo[0], port=int(randomNodeInfo[1]))
		transport1 = TTransport.TBufferedTransport(transport1)
		protocol1 = TBinaryProtocol.TBinaryProtocol(transport1)
		client1 = DHTNodeService.Client(protocol1)
		transport1.open()
		self.fingerTable[0].succNodeInfo = client1.findSuccessor(int(self.fingerTable[0].start))
		self.successor = self.fingerTable[0].succNodeInfo
		transport1.close()
		
		#get info of the predecessor node from the successor node
		succNode = self.successor.split(", ")
		transport1 = TSocket.TSocket(succNode[0], port=int(succNode[1]))
		transport1 = TTransport.TBufferedTransport(transport1)
		protocol1 = TBinaryProtocol.TBinaryProtocol(transport1)
		client1 = DHTNodeService.Client(protocol1)
		transport1.open()
		self.predecessor = client1.getPredecessor()
		transport1.close()
		
		# fill the finger table
		for i in range(0, self.noOfBits-1):
			succNode = self.fingerTable[i].succNodeInfo.split(", ")
			if self.inRange(self.fingerTable[i+1].start, (self.nodeId -1 +self.keySpace)%self.keySpace, int(succNode[2])):
				self.fingerTable[i+1].setSuccNodeInfo(succNode[0]+", "+succNode[1]+", "+succNode[2])
			else:
				transport1 = TSocket.TSocket(randomNodeInfo[0], port=int(randomNodeInfo[1]))
				transport1 = TTransport.TBufferedTransport(transport1)
				protocol1 = TBinaryProtocol.TBinaryProtocol(transport1)
				client1 = DHTNodeService.Client(protocol1)
				transport1.open()
				self.fingerTable[i+1].setSuccNodeInfo(client1.findSuccessor(self.fingerTable[i+1].start))
				transport1.close()
				
	''' get the successor node info '''			
	def findSuccessor(self, Id):
		#returns the predecessor of the current node
		predNodeInfo = self.findPredecessor(Id).split(", ")
		
		#if the predecessor is current node return successor of current node
		if (predNodeInfo[0] == self.address and int(predNodeInfo[1]) == self.port):
			return self.getSuccessor()
		
		transport1 = TSocket.TSocket(predNodeInfo[0], port=int(predNodeInfo[1]))
		transport1 = TTransport.TBufferedTransport(transport1)
		protocol1 = TBinaryProtocol.TBinaryProtocol(transport1)
		client1 = DHTNodeService.Client(protocol1)
		transport1.open()
		#get the successor node
		successorNode = client1.getSuccessor()
		transport1.close()	
		return successorNode
	
	''' get the predecessor node info '''
	def findPredecessor(self, Id):
		nodeInfo = [self.address, str(self.port), str(self.nodeId)]
		succId = int(self.getSuccessor().split(", ")[2])
		normal = 1
		if int(nodeInfo[2])>=succId:
			normal=0
			
		#finds the closest finger and contacts it to get the predecessor
		while ((normal==1 and (Id<=int(nodeInfo[2]) or Id> succId)) or (normal==0 and (Id<=int(nodeInfo[2])and Id> succId))):
			if (nodeInfo[0]==self.address and int(nodeInfo[1]) == self.port):
				nodeInfo = self.getClosestPrecedingFinger(Id).split(", ")
			else:
				transport1 = TSocket.TSocket(nodeInfo[0], port=int(nodeInfo[1]))
				transport1 = TTransport.TBufferedTransport(transport1)
				protocol1 = TBinaryProtocol.TBinaryProtocol(transport1)
				client1 = DHTNodeService.Client(protocol1)
				transport1.open()
				nodeInfo = client1.getClosestPrecedingFinger(Id).split(", ")
				transport1.close()
			if (nodeInfo[0]==self.address and int(nodeInfo[1]) == self.port):
				succId = int(self.getSuccessor().split(", ")[2])
				if int(nodeInfo[2])>=succId:
					normal=0
				else:
					normal=1
				isInRange = self.inRange(Id, int(nodeInfo[2]), (succId+1)%self.keySpace)
			else:
				transport1 = TSocket.TSocket(nodeInfo[0], port=int(nodeInfo[1]))
				transport1 = TTransport.TBufferedTransport(transport1)
				protocol1 = TBinaryProtocol.TBinaryProtocol(transport1)
				client1 = DHTNodeService.Client(protocol1)
				transport1.open()
				succId = int(client1.getSuccessor().split(", ")[2])
				isInRange = self.inRange(Id, int(nodeInfo[2]), (succId+1)%self.keySpace)
				if int(nodeInfo[2])>=succId:
					normal=0
				else:
					normal=1
				transport1.close()
		return nodeInfo[0]+", "+nodeInfo[1]+", "+nodeInfo[2]
	
	''' getter - returns the successor of current node '''	
	def getSuccessor(self):
		return self.successor
	
	''' getter - returns the predecessor of current node '''
	def getPredecessor(self):
		return self.predecessor
		
	'''checks if the given id is in the range'''
	def inRange(self, Id, start, end):
		if ((end-start +self.keySpace)%self.keySpace) == 1:
			return True
		if start<end:
			return (Id>start and Id<end)
		elif start>end:
			return (Id>start or Id<end)
		else:
			return False
	
	'''returns the closest preceding finger to the given id in the current node finger table'''	
	def getClosestPrecedingFinger(self, Id):
		normal = 1
		if self.nodeId>=Id:
			normal =0
		for i in range(self.noOfBits-1,-1, -1):
			if normal==1:
				if (int(self.fingerTable[i].succNodeInfo.split(", ")[2])>self.nodeId and int(self.fingerTable[i].succNodeInfo.split(", ")[2])<Id):
					return self.fingerTable[i].succNodeInfo
			else:
				if (int(self.fingerTable[i].succNodeInfo.split(", ")[2])>self.nodeId or int(self.fingerTable[i].succNodeInfo.split(", ")[2])<Id):
					return self.fingerTable[i].succNodeInfo
		return self.address+", "+str(self.port)+", "+str(self.nodeId)
		
	'''updates the finger table at index i'''
	def updateFingerTable(self, node, i):
		succId = int(node.split(", ")[2])
		normal =1
		if self.nodeId>=int(self.fingerTable[i].succNodeInfo.split(", ")[2]):
			normal =0
		if ((normal == 1 and (succId>=self.nodeId and succId<int(self.fingerTable[i].succNodeInfo.split(", ")[2])))or (normal == 0 and (succId>=self.nodeId or succId<int(self.fingerTable[i].succNodeInfo.split(", ")[2]))) and self.nodeId!=succId):
			self.fingerTable[i].setSuccNodeInfo(node)
			#if the index is 0 update the sucessor
			if i == 0:
				self.successor = node
			#check if the predecessor is the new node
			if self.predecessor != node:
				predecessor = self.predecessor.split(", ")
				transport1 = TSocket.TSocket(predecessor[0], port=int(predecessor[1]))
				transport1 = TTransport.TBufferedTransport(transport1)
				protocol1 = TBinaryProtocol.TBinaryProtocol(transport1)
				client1 = DHTNodeService.Client(protocol1)
				transport1.open()
				#update the fingertable of its predecessors
				client1.updateFingerTable(node, i)
				transport1.close()
		#prints the updated finger tables
		print("Updated Finger Table:")
		print(self.getNodeInfo())
			
	'''updates the current node predecessor'''			
	def updatePredecessor(self, node):
		self.predecessor = node
		
	'''get the updates from the successor's finger table'''
	def getSuccessorUpdates(self, node):
		updatedIndices = []
		for i in range(0, self.noOfBits):
			if self.fingerTable[i].succNodeInfo == node:
				updatedIndices.append(i)
		return updatedIndices
		
	'''check if key is present the node, if node forwards request to the closest node where the word is stored'''		
	def getWord(self, key):
		key = key.lower()
		#hashes the key using sha1 hashing
		hashedKey = int.from_bytes(hashlib.sha1(key.encode("utf-8")).digest(),'big')
		hashedKey = (hashedKey) % self.keySpace
		path = self.address+", "+str(self.port)+", "+str(self.nodeId)
		
		#checks if current node has the word
		if (self.inRange(hashedKey, int(self.predecessor.split(", ")[2]), (self.nodeId+1)%self.keySpace) or (key in self.dictionary)):
			if key in self.dictionary:
				return [self.dictionary[key], path]
			else:
				return ["", path]
		#forwards the request to the closest node where word is stored
		else:
			if key in self.cache:
				return [self.cache[key], path]
			nodeInfo = ""
			for i in range(self.noOfBits-1, -1, -1):
				if self.inRange(hashedKey, (self.fingerTable[i].start-1+self.keySpace) % self.keySpace, self.fingerTable[i].end):
					nodeInfo = self.fingerTable[i].succNodeInfo
					
			nodeInfo = nodeInfo.split(", ")
			transport1 = TSocket.TSocket(nodeInfo[0], port=int(nodeInfo[1]))
			transport1 = TTransport.TBufferedTransport(transport1)
			protocol1 = TBinaryProtocol.TBinaryProtocol(transport1)
			client1 = DHTNodeService.Client(protocol1)
			transport1.open()
			response = client1.getWord(key)
			transport1.close()
			response[1] = path+" -> "+response[1]
			return response
			
	'''stores the word based on the hash value'''
	def setWord(self, key, value):
		key = key.lower()
		value = value.lower()
		#hashes the key using sha1 hashing
		hashedKey = int.from_bytes(hashlib.sha1(key.encode("utf-8")).digest(),'big')
		hashedKey = (hashedKey) % self.keySpace
		path = self.address+", "+str(self.port)+", "+str(self.nodeId)
		if self.inRange(hashedKey, int(self.predecessor.split(", ")[2]), (self.nodeId+1)%self.keySpace):
			if key in self.dictionary:
				return [path, "Fail"]
			else:
				self.dictionary[key] = value
				return [path, "Success"]
		#forwards the request to the closest node where word need to be stored based on hashed value
		else:
			
			nodeInfo = ""
			for i in range(self.noOfBits-1, -1, -1):
				if self.inRange(hashedKey, (self.fingerTable[i].start-1+self.keySpace) % self.keySpace, self.fingerTable[i].end):
					nodeInfo = self.fingerTable[i].succNodeInfo
					
			nodeInfo = nodeInfo.split(", ")
			transport1 = TSocket.TSocket(nodeInfo[0], port=int(nodeInfo[1]))
			transport1 = TTransport.TBufferedTransport(transport1)
			protocol1 = TBinaryProtocol.TBinaryProtocol(transport1)
			client1 = DHTNodeService.Client(protocol1)
			transport1.open()
			response = client1.setWord(key, value)
			transport1.close()
			if response[1] != "Fail":
				self.cache[key] = value
			response[0] = path+" -> "+response[0]
			return response	
			
	''' Gets the node information of all the nodes in DHT'''		
	def getAllNodesDetails(self, Id):
		succNode = self.successor.split(", ")
		nodesInfo = []
		if Id == int(succNode[2]):
			nodesInfo.append(self.getNodeInfo())
			return nodesInfo
		
		transport1 = TSocket.TSocket(succNode[0], port=int(succNode[1]))
		transport1 = TTransport.TBufferedTransport(transport1)
		protocol1 = TBinaryProtocol.TBinaryProtocol(transport1)
		client1 = DHTNodeService.Client(protocol1)
		transport1.open()
		response = client1.getAllNodesDetails(Id)
		transport1.close()
		response.append(self.getNodeInfo())
		return response
	
	''' Gets the node information '''	
	def getNodeInfo(self):
		nodeInfo = ""
		nodeInfo = nodeInfo+"\nNodeId: "+str(self.nodeId)+"\n"+"Node Address: "+self.address+"\n"
		nodeInfo = nodeInfo+"\nNode Successor: "+self.successor+"\n"+"Node Predecessor: "+self.predecessor+"\n"+"\nFinger Table: "+"\n"
		for i in range(0, self.noOfBits):
			nodeInfo = nodeInfo + "Succ Node: "+self.fingerTable[i].succNodeInfo+" Start: "+ str(self.fingerTable[i].start)+" End: "+ str(self.fingerTable[i].end)+"\n"
		if len(self.dictionary)!=0:
			nodeInfo = nodeInfo + "\nData stored in the node: "+"\n"
			nodeInfo = nodeInfo + "\n\n".join(['%s::  %s' % (key, value) for (key, value) in self.dictionary.items()])
		return nodeInfo
		
		
			
	
		
		
		
    	

