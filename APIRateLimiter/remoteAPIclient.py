import pika
import uuid
import threading
import time
import json

testArguments = [{'methodName' : 'byName',
                 'summonerString': 'Keyboard Warrìor'},
                 
                 {'methodName' : 'byName',
                 'summonerString': 'Keyboard Warrìor'}]

class remoteAPIclient(object):
    internal_lock = threading.Lock()
    resultStorage = {}

    def __init__(self, rpc_queue):
        self.rpc_queue = rpc_queue
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
        self.channel = self.connection.channel()
        
        result = self.channel.queue_declare(exclusive=True)
        self.callback_queue = result.method.queue
        
        thread = threading.Thread(target=self._process_data_events)
        thread.setDaemon(True)
        thread.start()

    def _process_data_events(self):

        self.channel.basic_consume(self._on_response, no_ack=True, queue=self.callback_queue)

        while True:
            with self.internal_lock:
                self.connection.process_data_events()
            time.sleep(0.1)

    def _on_response(self, ch, method, props, body):
        self.resultStorage[props.correlation_id] = body

    def send_request(self, apiArguments):
        corr_id = str(uuid.uuid4())
        self.resultStorage[corr_id] = None
        with self.internal_lock:
            self.channel.basic_publish(exchange = '',
                                       routing_key = self.rpc_queue,
                                       properties = pika.BasicProperties( reply_to = self.callback_queue,
                                                                          correlation_id = corr_id,
                                                                          content_type='application/json',
                                                                          content_encoding='utf-8',),
                                       body = apiArguments)
        return corr_id

    def delete_results(self, corr_id_list):
        with self.internal_lock:
            for corr_id in corr_id_list:
                del self.resultStorage[corr_id]
                                                                          
def rpcCall(remoteClient, apiArguments):
    jsonified = json.dumps(apiArguments)
    return remoteClient.send_request(jsonified)

def rpcCheck(remoteClient, idList):
    resultList = []
    for corr_id in idList:
        while remoteClient.resultStorage[corr_id] is None:
            time.sleep(0.1)
        resultList.append(remoteClient.resultStorage[corr_id])
    remoteClient.delete_results(idList)
    return resultList

def rpcFixResults(resultList):
    for n in range(len(resultList)):
        result = resultList[n]
        decoded = result.decode('utf-8')
        objectified = json.loads(decoded)
        resultList[n] = objectified

#takes in a remoteClient object and a list of dictionaries
#representing the arguments for all requests to be performed
def rpcFullRequest(remoteClient, apiArguments):
    idList = []
    for argList in apiArguments:
        idList.append(rpcCall(remoteClient, argList))
    results = rpcCheck(remoteClient, idList)
    rpcFixResults(results)
    return results

if __name__ == '__main__':
    remote = remoteAPIclient('remoteAPI_queue')
    idStorage = []
    start = time.perf_counter()
    for n in range(1):
        for arguments in testArguments:
            idStorage.append(rpcCall(remote, arguments))
    results = rpcCheck(remote, idStorage)
    end = time.perf_counter()
    rpcFixResults(results)
    print(str(end-start))



















