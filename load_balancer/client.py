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
from edgeDetectionService import edgeDetectionService
import configparser
from thrift.transport import TSocket
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol
import traceback

'''get host name from machine.txt for the RPC call'''
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


def main():
	try:
		#get server host name and port
		host = getHost('server')
		port = getPort('server')
		
		#create client connection
		transport = TSocket.TSocket(host, port=port)
		transport = TTransport.TBufferedTransport(transport)
		protocol = TBinaryProtocol.TBinaryProtocol(transport)
		client = edgeDetectionService.Client(protocol)
		transport.open()
		
		parser = configparser.ConfigParser()
		parser.read('config.cfg')
		imagespath = parser['Path']['files']
    		#call edge dectection service
		logFile = client.filter(imagespath)
    		
    		#print output to the console
		outputFile = open(logFile, "r")
		f1 = outputFile.readlines()
		for line in range(0, len(f1)-1):
			data = f1[line].split(" ")
			print("")
			print("Edge detection of image "+data[0]+" completed on node "+data[1])
			print("Time Elapsed(in secs): "+data[2])
		print(f1[len(f1)-1])
		time.sleep(600)
	
		transport.close()
	except:
		traceback.print_exc()


if __name__ == '__main__':
    try:
        main()
    except Thrift.TException as tx:
        print('%s' % tx.message)
