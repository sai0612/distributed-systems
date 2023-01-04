namespace py QuorumService
typedef i32 int

service QuorumService
{
	bool write(1: string file, 2: string data),
	string read(1: string file),
	bool coordinatorWrite(1: string file, 2: string data),
	string coordinatorRead(1: string file),
	bool fileWrite(1: string file, 2: string data, 3: int fileVersion),
	string fileRead(1: string file),
	int getFileVersion(1: string file),
	string listAllFiles(),
	string coordinatorFiles(),
}


