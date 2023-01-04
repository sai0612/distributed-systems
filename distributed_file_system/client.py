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
from QuorumService import QuorumService
import configparser
from thrift.transport import TSocket
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol
import random
from multiprocessing import Process
from multiprocessing import Manager

''' client gets addresses and ports of all file server nodes present in the network'''
def getNodes():
	parser = configparser.ConfigParser()
	parser.read('config.cfg')
	node_count= int(parser['Quorum']['node_count'])
	addresses = parser['Node']['address'].rstrip("\n").split(", ")
	ports = parser['Node']['port'].rstrip("\n").split(", ")
	nodes = []
	
	for i in range(0, node_count):
		nodes.append(addresses[i]+", "+ports[i])
	return nodes
	
'''get a random node from the file server nodes'''
def getRandomNode(nodes_info):
	return random.choice(nodes_info)
	
'''read the file contents '''
def read(filename, node_info, times = None):
	node_address = node_info.split(", ")[0]
	node_port = node_info.split(", ")[1]
	transport = TSocket.TSocket(node_address, port=int(node_port))
	transport = TTransport.TBufferedTransport(transport)
	protocol = TBinaryProtocol.TBinaryProtocol(transport)
	client = QuorumService.Client(protocol)
	transport.open()
	startTime = time.time()
	file_content = client.read(filename)
	endTime = time.time()
	if file_content == "File not found":
		print(file_content)
	else:
		print("------------Contents of the file "+filename+"-----------")
		print(file_content)
		print("Time taken to read the file: "+str(endTime-startTime))
	if times is not None:
		times.append(endTime-startTime)
	transport.close()
	
'''write the contents to the file '''
def write(filename, content, node_info, times = None):
	node_address = node_info.split(", ")[0]
	node_port = node_info.split(", ")[1]
	transport = TSocket.TSocket(node_address, port=int(node_port))
	transport = TTransport.TBufferedTransport(transport)
	protocol = TBinaryProtocol.TBinaryProtocol(transport)
	client = QuorumService.Client(protocol)
	transport.open()
	startTime = time.time()
	success = client.write(filename, content)
	endTime = time.time()
	if not success:
		print("Write could not be performed")
	else:
		print("write operation completed succesfully")
		print("Time taken to write the file: "+str(endTime-startTime))
	if times is not None:
		times.append(endTime-startTime)
	
	transport.close()	

'''list of all the files with versions '''
def listAllFiles(node_info):
	node_address = node_info.split(", ")[0]
	node_port = node_info.split(", ")[1]
	transport = TSocket.TSocket(node_address, port=int(node_port))
	transport = TTransport.TBufferedTransport(transport)
	protocol = TBinaryProtocol.TBinaryProtocol(transport)
	client = QuorumService.Client(protocol)
	transport.open()
	files = client.listAllFiles()
	print("------------Files-----------")
	print(files)
	transport.close()

def readall(filesPath, nodes_info):
	
	files = os.listdir(filesPath)
	threads = []
	times = Manager().list()
	for fname in files:
		randomNodeInfo = getRandomNode(nodes_info)
		process = Process(target = read, args=(fname, randomNodeInfo, times))
		threads.append(process)
	for thread in threads:
		thread.start()
	for thread in threads:
		thread.join()
	print("Average time taken for all reads is: "+str(sum(times)/len(times)))
		
def writeall(filesPath, nodes_info):
	files = os.listdir(filesPath)
	threads = []
	times = Manager().list()
	for fname in files:
		content = "testing simultaneous write for work load"
		randomNodeInfo = getRandomNode(nodes_info)
		thread = Process(target = write, args=(fname, content, randomNodeInfo, times))
		threads.append(thread)
	for thread in threads:
		thread.start()
	for thread in threads:
		thread.join()
	print("Average time taken for all reads is: "+str(sum(times)/len(times)))
					
def main():
	parser = configparser.ConfigParser()
	parser.read('config.cfg')
	quorumReadCount= int(parser['Quorum']['quorum_read'])
	quorumWriteCount= int(parser['Quorum']['quorum_write'])
	node_count= int(parser['Quorum']['node_count'])
	
	if node_count >= quorumReadCount+quorumWriteCount or quorumWriteCount <= node_count/2:
		print("The condition for quorum based protocol is not satisfied")
		sys.exit()
	# client gets addresses and ports of all file server nodes present in the network
	nodes_info = getNodes()
			
	task = "read"
	while task!="exit":
		task = input("Enter the task for the server 1.read 2.write 3.list files 4.exit 5.readall 6.writeall: ")
		if task == "read":
			file = input("Enter the file name to read: ")
			randomNodeInfo = getRandomNode(nodes_info)
			read(file, randomNodeInfo)
		elif task == "write":
			file = input("Enter the file name to write: ")
			content = input("Enter the content of the file: ")
			randomNodeInfo = getRandomNode(nodes_info)
			write(file, content, randomNodeInfo)
		elif task == "list files":
			randomNodeInfo = getRandomNode(nodes_info)
			listAllFiles(randomNodeInfo)
		elif task == "readall":
			readall(parser['Quorum']['files'].rstrip("\n"), nodes_info)
		elif task == "writeall":
			writeall(parser['Quorum']['files'].rstrip("\n"), nodes_info)
		elif task != "exit":
			print("Please enter valid input")
		print()
				
		
if __name__ == '__main__':
    try:
        main()
    except Thrift.TException as tx:
        print('%s' % tx.message)
