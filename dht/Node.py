
import sys
import os
import random
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
	
import configparser
from DHTSuperNodeService import DHTSuperNodeService
from DHTNodeService import DHTNodeService
from NodeHandler import NodeHandler
from thrift.transport import TSocket
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol
from thrift.server import TServer

'''get port number from config file for the RPC call'''
def getPorts(key):
	parser = configparser.ConfigParser()
	parser.read('config.cfg')
	return parser[key]['port']
	
if __name__ == '__main__':
	node = int(sys.argv[1])
	parser = configparser.ConfigParser()
	parser.read('config.cfg')
	if node >= int(parser['DHT']['node_count']):
		print("Please provide node number within DHTSize")
		sys.exit()
	#get server port number from config file
	ports = getPorts('Node').split(", ")
	addresses = int(len(parser['Node']['address'].split(", ")))
	if len(ports) != int(parser['DHT']['node_count']) or addresses != int(parser['DHT']['node_count']):
		print("Please provide appropriate number of ports and node addresses")
		sys.exit()
	#create thrift server socket as a threaded server
	handler = NodeHandler(node)
	processor = DHTNodeService.Processor(handler)
	
	transport = TSocket.TServerSocket(port=ports[node])
	tfactory = TTransport.TBufferedTransportFactory()
	pfactory = TBinaryProtocol.TBinaryProtocolFactory()
	server = TServer.TThreadPoolServer(processor, transport, tfactory, pfactory)
	
	print('Starting the node '+str(node)+'...')
	server.serve()
	print('done.')
