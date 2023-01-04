
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
import configparser
from DHTSuperNodeService import DHTSuperNodeService
from SuperNodeHandler import SuperNodeHandler
from thrift.transport import TSocket
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol
from thrift.server import TServer

'''get port number from config file for the RPC call'''
def getPort(key):
	parser = configparser.ConfigParser()
	parser.read('config.cfg')
	return parser[key]['port']
		
if __name__ == '__main__':
	handler = SuperNodeHandler()
	processor = DHTSuperNodeService.Processor(handler)
	#get server port number from config file
	port = getPort('SuperNode')
	#create thrift server socket as a threaded server
	transport = TSocket.TServerSocket(port=int(port))
	tfactory = TTransport.TBufferedTransportFactory()
	pfactory = TBinaryProtocol.TBinaryProtocolFactory()
	server = TServer.TThreadPoolServer(processor, transport, tfactory, pfactory)
	
	print('Starting the Super Node...')
	server.serve()
	print('done.')
