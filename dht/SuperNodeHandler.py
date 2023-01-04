import hashlib
import random
import sys
import os
if not os.path.isfile("config.cfg"):
	print("please provide config.cfg before running")
	sys.exit()
import configparser
class SuperNodeHandler:
	def __init__(self):
		self.nodesInDHT = []
		self.DHTSize = int(self.getDataFromConfig('node_count'))
		if self.DHTSize < 5:
			print("DHTSize should be greater than 4. Please update the config file")
			sys.exit()
		self.noOfBits = int(self.getDataFromConfig('bits'))
		self.nodeJoinInProgress = ""
		self.keySpace = pow(2, self.noOfBits)
		if self.DHTSize > self.keySpace:
			print("DHTSize should be less than key space. Please update the config file")
			sys.exit()
		self.nextNodeIndex = 0
		
	''' get data from the config file '''	
	def getDataFromConfig(self, key):
		parser = configparser.ConfigParser()
		parser.read('config.cfg')
		return parser['DHT'][key]
	
	''' returns random node information from the DHT to the new node joining the network'''
	def GetNodeForJoin(self, address, port):
		#if super node is busy joining another node send NACK
		if self.nodeJoinInProgress!="":
			print("Rejected join request")
			return "-1, NACK"
		
		self.nodeJoinInProgress = address+", "+str(port)
		
		#using sha1 hashing to give a unique identifier to the node within the keyspace
		#nodeId = int.from_bytes(hashlib.sha1(self.nodeJoinInProgress.encode("utf-8")).digest(),'big')
		nodeId = int(self.nextNodeIndex * pow(2, self.noOfBits) / self.DHTSize)
		self.nextNodeIndex = self.nextNodeIndex+1
		#nodeId = (nodeId) % self.keySpace
		print("Node Id created by super node for new node: "+str(nodeId))
		newNode = address+", "+str(port)+", "+str(nodeId)
		if(len(self.nodesInDHT)==0):
			self.nodesInDHT.append(newNode)
			return str(nodeId)+", "+newNode
		else:
			randomNodeInDHT = self.getRandomNodeInDHT()
			self.nodesInDHT.append(newNode)
			return str(nodeId)+", "+randomNodeInDHT
			
	'''after the new node joins the networks it notifies the super node '''
	def PostNode(self, address, port):
		if self.nodeJoinInProgress == (address+", "+str(port)):
			self.nodeJoinInProgress = ""
			print("Node joined successfully")
			
	def getRandomNodeInDHT(self):
		index = random.randint(0,len(self.nodesInDHT)-1)
		return self.nodesInDHT[index]
		
	'''returns a random node in the DHT to perform the task'''
	def GetNodeForClient(self):
		if self.nodeJoinInProgress!="" or len(self.nodesInDHT) < self.DHTSize:
			print("DHT join still in progress")
			return "NACK"
		return self.getRandomNodeInDHT()
		
		
		
    	

