namespace py DHTSuperNodeService
typedef i32 int

service DHTSuperNodeService
{
	string GetNodeForJoin(1:string address, 2:int port),
	void PostNode(1:string address, 2:int port),
	string GetNodeForClient()
}


