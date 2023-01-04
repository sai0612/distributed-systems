
import sys
import os
import random
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
from edgeDetectionService import edgeDetectionService
from thrift.transport import TSocket
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol
from thrift.server import TServer
import configparser
from threading import Thread
import time
import cv2 as cv
import traceback

class Handler:
    def __init__(self):
    	self.totalTasks = 0
    	self.logFile = "log.txt"
    
    '''create a connection and sends tasks to compute nodes'''
    def helper(self, node, image):
    	parser = configparser.ConfigParser()
    	parser.read('config.cfg')
    	imagespath = parser['Path']['files']
    	
    	#get compute nodes host name and port number
    	host = getHost('node_'+str(node))
    	port = getPort('node_'+str(node))
    	
    	#create client connection to compute nodes
    	transport1 = TSocket.TSocket(host, port=port)
    	transport1 = TTransport.TBufferedTransport(transport1)
    	protocol1 = TBinaryProtocol.TBinaryProtocol(transport1)
    	client1 = edgeDetectionService.Client(protocol1)
    	transport1.open()
    	
    	#assign task to compute node for edge detection
    	accepted  = client1.edgeDetection(imagespath, node, image)
    	transport1.close()
    	return accepted
    
    '''assigns tasks to compute nodes'''	
    def filter(self, n1):
    	try:
    		print("")
    		print("---------------------CLIENT REQUESTED NEW JOB---------------------------")
    		
    		startTime = time.time()
    		self.totalTasks=0
    		self.logFile = 'log.txt'
    		open(self.logFile, "w").close()
    		
    		#get input sample images
    		inputpath=n1+"/input_dir"
    		sys.path.append(inputpath)
    		files=next(os.walk(inputpath))[2]
    		numOfImages = 0
    	
    		#one image per task
    		for image in range(0, len(files)):
    			accepted = False
    			img = cv.imread(inputpath+'/'+files[image])
    			if img is not None:
    				numOfImages=numOfImages+1
    			while not accepted:
    				#choose a compute node at random
    				random_node = random.randint(0, 3)
    				accepted = self.helper(random_node, image)
    				if accepted:
    					print("Image "+files[image]+" sent to on compute node "+str(random_node)+" for edge detection")
    		#wait until all tasks are completed
    		while self.totalTasks!=numOfImages:
    			pass
    		endTime = time.time()
    		#logs the computation time for the job in an output file
    		outputFile = open(self.logFile, "a")
    		outputFile.write("Total time taken by the job(in secs): "+str(endTime-startTime))
    		return self.logFile
    	except:
    		traceback.print_exc()
    	return None
    	
    def sendLogData(self, time):
    	#print output to the console
    	data = time.split(" ")
    	print("")
    	print("Edge detection of image "+data[0]+" completed on node "+data[1])
    	print("Time Elapsed(in secs): "+data[2])
    	outputFile = open(self.logFile, "a")
    	outputFile.write(time+"\n")
    	self.totalTasks=self.totalTasks+1

'''get host name from machine.text file for the RPC call'''
def getHost(key):
	parser = configparser.ConfigParser()
	parser.read('config.cfg')
	filepath = parser['Path']['nodes']
	lines = []
	host = ""
	sys.path.append(filepath)
	
	with open(filepath) as f:
		lines = f.readlines()
	for line in lines:
		if key in line:
			s = line.split(' ')
			host = s[1].rstrip("\n")
	return host

'''get port number from config file for the RPC call'''
def getPort(key):
	parser = configparser.ConfigParser()
	parser.read('config.cfg')
	return parser['Port'][key]
	
if __name__ == '__main__':
	handler = Handler()
	processor = edgeDetectionService.Processor(handler)
	#get server port number from config file
	port = getPort('server')
	#create thrift server socket as a threaded server
	transport = TSocket.TServerSocket(port=port)
	tfactory = TTransport.TBufferedTransportFactory()
	pfactory = TBinaryProtocol.TBinaryProtocolFactory()
	server = TServer.TThreadedServer(processor, transport, tfactory, pfactory)
	
	print('Starting the server...')
	server.serve()
	print('done.')
