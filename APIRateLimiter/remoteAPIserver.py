from rateLimiter import requestHandler, methodProcessor, workDelegator, methodProcess
from multiprocessing import Process, Queue, Pipe
import pika
import json
import requests

NUMWORKERS = 4

staticRegions = ['na1']

staticMethods = ['byAccount', 'byMatchId', 'byName']

maxLimits = {'byName': [2000, 0, 60],
            'byAccount': [1000, 0, 10],
            'byMatchId': [500, 0, 10]}

testArguments = [{'methodName' : 'byMatchId',
                 'matchId': 2841964828},
                 
                 {'methodName' : 'byName',
                 'summonerString': 'Keyboard Warrìor'}]

def requestHandlerSetup(conn, identifier, workQueue, errorQueue):
    msgConnection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
    channel = msgConnection.channel()
    channel.queue_declare(queue='remoteAPI_queue')

    wq = workQueue
    eq = errorQueue
    rh = requestHandler(conn, identifier)
    
    def on_request(ch, method, props, body):
        decoded = body.decode('utf-8')
        requestArguments = json.loads(decoded)
        print(" [%d] has a job" % identifier)
        rh.prepJob(requestArguments)
        response = rh.doJob(wq, eq)
        
        encodedResponse = response.text
        ch.basic_publish(exchange='',
                         routing_key = props.reply_to,
                         properties = pika.BasicProperties(correlation_id = props.correlation_id,
                                                           content_type='application/json',
                                                           content_encoding='utf-8',),
                         body = encodedResponse)
        ch.basic_ack(delivery_tag = method.delivery_tag)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(on_request, queue='remoteAPI_queue')

    print(" [%d] Waiting for API Requests" % identifier)
    channel.start_consuming()

if __name__ == '__main__':
    delegator = workDelegator('na1')
    for method in staticMethods:
        delegator_conn, method_conn = Pipe()
        delegator.add_new_method_connection(delegator_conn, method)
        methodList = maxLimits[method]
        p = Process(target=methodProcess, args=(method_conn, method, methodList))
        p.start()
        
    for n in range(NUMWORKERS*2):
        delegator_conn, worker_conn = Pipe()
        delegator.add_new_worker_connection(delegator_conn, n)
        p = Process(target=requestHandlerSetup, args=(worker_conn, n, delegator.workQueue, delegator.errorQueue))
        p.start()
    print('everything started')
    delegator.work_loop()
        
