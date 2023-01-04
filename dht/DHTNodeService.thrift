namespace py DHTNodeService
typedef i32 int

service DHTNodeService
{
	string findSuccessor(1: int Id),
	string findPredecessor(1: int Id),
	string getClosestPrecedingFinger(1: int Id),
	string getSuccessor(),
	string getPredecessor(),
	void updateFingerTable(1: string node, 2: int i),
	void updatePredecessor(1: string node),
	list<string> setWord(1: string key, 2: string value),
	list<string> getWord(1: string key),
	list<int> getSuccessorUpdates(1: string node),
	list<string> getAllNodesDetails(1: int Id),
	
}


