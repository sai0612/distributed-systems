namespace py edgeDetectionService
typedef i32 int

service edgeDetectionService
{
	bool edgeDetection(1:string imagePath, 2:int node, 3:int image),
	string filter(1:string n1),
	void sendLogData(1:string time)
}


