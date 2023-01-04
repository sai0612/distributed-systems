#!/usr/bin/env python


import sys
import time
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
from thrift import Thrift
from DHTSuperNodeService import DHTSuperNodeService
from DHTNodeService import DHTNodeService
import configparser
from thrift.transport import TSocket
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol

''' client contacts super node and gets the information of a random node in DHT'''
def getNode():
	parser = configparser.ConfigParser()
	parser.read('config.cfg')
	port= parser['SuperNode']['port']
	address = parser['SuperNode']['address']
	transport = TSocket.TSocket(address, port=int(port))
	transport = TTransport.TBufferedTransport(transport)
	protocol = TBinaryProtocol.TBinaryProtocol(transport)
	client = DHTSuperNodeService.Client(protocol)
	randomNodeInfo = None
	transport.open()
	randomNodeInfo = client.GetNodeForClient()
	transport.close()
	return randomNodeInfo

''' client contacts the random node to put a new word into the dictionary '''
def setWord(key, value, nodeInfo):
	nodeInfo = nodeInfo.split(", ")
	#connecting to the random node in DHT
	transport = TSocket.TSocket(nodeInfo[0], port=int(nodeInfo[1]))
	transport = TTransport.TBufferedTransport(transport)
	protocol = TBinaryProtocol.TBinaryProtocol(transport)
	client = DHTNodeService.Client(protocol)
	transport.open()
	wordPath = client.setWord(key, value)
	if wordPath[1] == "Fail":
		print("The word is already present in dictionary. Please try another word")
		transport.close()
		return
	print("Word "+key+" set successful")
	print("The path to reach the word: ", wordPath[0])
	transport.close()	

''' client contacts the random node to get the meaning of a word '''	
def getWord(key, nodeInfo):
	nodeInfo = nodeInfo.split(", ")
	transport = TSocket.TSocket(nodeInfo[0], port=int(nodeInfo[1]))
	transport = TTransport.TBufferedTransport(transport)
	protocol = TBinaryProtocol.TBinaryProtocol(transport)
	client = DHTNodeService.Client(protocol)
	transport.open()
	response = client.getWord(key)
	if response[0] == "":
		print("Entered word meaning not found")
	else:
		print("Word: "+key)
		print("Meaning: "+response[0])
		print("The path to reach the word: ", response[1])
	transport.close()

''' client contacts the random node to put some new words into the dictionary '''
def multipleSet(nodeInfo, filename):
	if not os.path.isfile(filename):
		print("File not found. Please provide appropriate filename")
		return
	dictionary = open(filename, "r")
	f1 = dictionary.readlines()
	for i in range(0, len(f1), 2):
		key = f1[i].rstrip("\n")
		value = f1[i+1].split(": ")[1].rstrip("\n")
		setWord(key, value, nodeInfo)

''' gets infomation about the nodes in DHT '''	
def getAllNodesInfo(nodeInfo):
	nodeInfo = nodeInfo.split(", ")
	transport = TSocket.TSocket(nodeInfo[0], port=int(nodeInfo[1]))
	transport = TTransport.TBufferedTransport(transport)
	protocol = TBinaryProtocol.TBinaryProtocol(transport)
	client = DHTNodeService.Client(protocol)
	transport.open()
	response = client.getAllNodesDetails(int(nodeInfo[2]))
	print("Information of all nodes present in DHT:")
	for i in range(0, len(response)):
		print(response[i])
	transport.close()
	
			
def main():
	# if the command line input is a file of multiple words and meanings
	if len(sys.argv)>1:
		task = sys.argv[1]
		nodeId = "NACK"
		while nodeId == "NACK":
			randomNodeInfo = getNode()
			nodeId = randomNodeInfo.split(", ")[0]
			if nodeId == "NACK":
				print("DHT is not ready")
				time.sleep(100)
			else:
				multipleSet(randomNodeInfo, sys.argv[1])
			
	task = "set"
	while task!="exit":
		task = input("Enter the task for the server 1.get 2.set 3.getnodes 4.exit: ")
		if task == "get":
			word = input("Enter the word to get the meaning: ")
			randomNodeInfo = getNode()
			nodeId = randomNodeInfo.split(", ")[0]
			if nodeId == "NACK":
				print("DHT is not ready")
			else:
				getWord(word, randomNodeInfo)
		elif task == "set":
			word = input("Enter the word: ")
			meaning = input("Enter the meaning: ")
			randomNodeInfo = getNode()
			nodeId = randomNodeInfo.split(", ")[0]
			if nodeId == "NACK":
				print("DHT is not ready")
			else:
				setWord(word, meaning, randomNodeInfo)
		elif task == "getnodes":
			randomNodeInfo = getNode()
			nodeId = randomNodeInfo.split(", ")[0]
			if nodeId == "NACK":
				print("DHT is not ready")
			else:
				getAllNodesInfo(randomNodeInfo)
		elif task != "exit":
			print("Please enter valid input")
		print()
				
		
if __name__ == '__main__':
    try:
        main()
    except Thrift.TException as tx:
        print('%s' % tx.message)
