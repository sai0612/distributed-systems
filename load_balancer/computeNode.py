
import sys
import os
sys.path.append('gen-py')
#check if all necessary files are present
if not os.path.isfile("env.txt"):
	print("please provide env.txt before running")
	sys.exit()
f = open("env.txt", "r")
f1 = f.readlines()
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
import random
import cv2 as cv
import numpy as np
import time
from threading import Thread
import threading
import traceback

# relative module

class Handler:
    def __init__(self):
        self.prob = None 

    def edgeDetection(self, imagePath, node, image):
    	#get scheduler type and load probabilities from config file
    	parser = configparser.ConfigParser()
    	parser.read('config.cfg')
    	scheduler = parser['Scheduler']['scheduler_type']
    	probabilities = parser['Scheduler']['load_probability']
    	delay = parser['Scheduler']['delay']
    	inputpath=imagePath+"/input_dir"
    	sys.path.append(inputpath)
    	files=next(os.walk(inputpath))[2]
    	self.prob = probabilities.split(",")
    	
    	#checks if the task has to be rejected or not
    	if scheduler == "load_balancing" and float(random.random())<float(self.prob[node]):
    		print("Image "+files[image]+" rejected on node "+str(node))
    		return False
    	
    	#runs each task on a different thread
    	Thread(target = self.edgeDetect, args=(imagePath, image, node, delay)).start()
    	return True
    
    def edgeDetect(self,imagePath,image,node, delay):
    	try:
    		startTime = time.time()
    	
    		inputpath=imagePath+"/input_dir"
    		sys.path.append(inputpath)
    		files=next(os.walk(inputpath))[2]
    	
    		#checks if delay has to be injected to the job or not
    		if float(random.random()) < float(self.prob[node]):
    			print("Waiting on node "+str(node)+" to work on image "+files[image])
    			time.sleep(int(delay))
    		
    		#canny edge detection	
    		input_image = inputpath+'/'+files[image]
    		output_image = imagePath+"/output_dir/"+files[image]
    	
    		img = cv.imread(input_image)
    		print("")
    	
    		print('Working on image '+files[image]+ " on Node "+str(node))
    		gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
    		edge = cv.Canny(gray, threshold1 =70, threshold2=120)
    		vis = img.copy()
    		vis = np.uint8(vis/2.)
    		vis[edge != 0] = (255, 255, 255)
    	
    		#saves the output image 
    		cv.imwrite(output_image, vis)
    	
    		endTime = time.time()
    		print("")
    		print('Edge dectection completed on image '+files[image])
    		print("Time Elapsed: "+str(endTime-startTime))
    		data = files[image]+" "+str(node)+" "+str(endTime-startTime)
    		
    		#get server host name and port number
    		host = getHost('server')
    		port = getPort('server')
    		
    		#make the return RPC call to return results to server
    		transport = TSocket.TSocket(host, port=port)
    		transport = TTransport.TBufferedTransport(transport)
    		protocol = TBinaryProtocol.TBinaryProtocol(transport)
    		client = edgeDetectionService.Client(protocol)
    		transport.open()
    		client.sendLogData(data)
    		transport.close()
    	except:
    		traceback.print_exc()

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
	nodenumber=sys.argv[1]
	#get compute node port number from config file
	port = getPort('node_'+nodenumber)
	#create thrift compute node socket as a threaded server
	transport = TSocket.TServerSocket(port=port)
	tfactory = TTransport.TBufferedTransportFactory()
	pfactory = TBinaryProtocol.TBinaryProtocolFactory()
	server = TServer.TThreadedServer(processor, transport, tfactory, pfactory)
	
	print('Starting the Compute Node '+str(nodenumber))
	server.serve()
	print('done.')
