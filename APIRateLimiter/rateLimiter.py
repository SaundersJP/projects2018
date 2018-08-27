from RiotAPI import RiotAPI
from remoteAPIcalls import getAccountId, getMatchList, getSingleDetailedMatchData
from multiprocessing import Process, Queue, Array, Pipe

import requests
import time
import json
import sys
import pprint

NUMWORKERS = 4

staticRegions = ['na1']

staticMethods = ['byAccount', 'byMatchId', 'byName']

maxLimits = {'byName': [2000, 0, 60],
            'byAccount': [1000, 0, 10],
            'byMatchId': [500, 0, 10]}

class requestHandler():
    
    functionTable = {'byName' : lambda args: getAccountId(args),
                     'byAccount' : lambda args: getMatchList(args),
                     'byMatchId' : lambda args: getSingleDetailedMatchData(args) }
    
    def __init__(self, conn, identifier):
        self.connection = conn
        self.id = identifier
        self.method = None
        self.args = None
        self.waiting = False

    def prepJob(self, args):
        self.method = args['methodName']
        del args['methodName']
        self.args = args

    def doJob(self, workQueue, errorQueue):
        workQueue.put([self.method, self.id])
        approval = self.connection.recv()
        
        response = requestHandler.functionTable[self.method](self.args)
        if response.status_code != 200:
            errorQueue.put([response.status_code])
        #processHeader
        return response

    def examineHeader(self, response):
        pass

    def generateErrorMessage(self, errorCode, wait=None):
        pass

#methodLimitList = [MaxRate, Counter, ResetInterval]
class methodProcessor():
    def __init__(self, conn, name, methodLimitList):
        self.connection = conn
        self.name = name
        self.limit = methodLimitList
        self.time = time.perf_counter()
        self.storedJob = None

    def under_limit(self):
        return (self.limit[1] < self.limit[0])

    def wait_until_reset(self):
        currentTime = time.perf_counter()
        potentialWait = self.limit[2] - (currentTime - self.time)
        if potentialWait > 0:
            time.sleep( (int(potentialWait) + 1) )
        self.time = currentTime
        self.limit[1] = 0

    #requests are list of [type, data, ...]
    def work_loop(self):
        while True:
            if self.storedJob:
                delegatorRequest = self.storedJob
            else:
                delegatorRequest = self.connection.recv()

            requestType = delegatorRequest[0]
            #[type, sleepDuration, globalTimeOut]
            if requestType == 'timeout':
                time.sleep(delegatorRequest[1])
                if not delegatorRequest[2]:
                    self.time = time.perf_counter()
                    self.limit[1] = 0
                continue
            
            #[type, conn]
            if requestType == 'worker':
                
                if self.under_limit():
                    if self.limit[1] == 0:
                        self.time = time.perf_counter()
                    workConn = delegatorRequest[1]
                    workConn.send("approved")
                    self.limit[1] += 1
                    self.storedJob = None
                    continue
                else:
                    print('method maybe Waiting')
                    self.storedJob = delegatorRequest
                    self.wait_until_reset()
                    continue
        

class workDelegator():
    def __init__(self, region='na1'):
        self.limits = {'appBurst': [20, 0, 1],
                        'appContinuous': [100, 0, 120]}

        self.workerConnections = {}
        self.methodConnections = {}
        self.region = region
        self.workQueue = Queue()
        self.errorQueue = Queue()
        self.burstTime = time.perf_counter()
        self.continuousTime = time.perf_counter()
        self.spawnedProcesses = []
        self.done = 0

    def add_new_worker_connection(self, parentConn, childId):
        self.workerConnections[childId] = parentConn

    def add_new_method_connection(self, parentConn, methodName):
        self.methodConnections[methodName] = parentConn

    def under_limit(self, key):
        return self.limits[key][1] < self.limits[key][0]

    def wait_until_reset(self, key):
        limit = self.limits[key]
        currentTime = time.perf_counter()
        if key == 'appContinuous':
            potentialWait = limit[2] - (currentTime - self.continuousTime)
            print("estimated sleep time = " + str(potentialWait))
            if potentialWait > 0:
                print("continuous sleep")
                time.sleep( (int(potentialWait) + 5) )
                print("sleep complete")
            limit[1] = 0
            self.limits['appBurst'][1] = 0
        else:
            potentialWait = limit[2] - (currentTime - self.burstTime)
            if potentialWait > 0:
                time.sleep( (int(potentialWait) + 5) )
            limit[1] = 0
            
    def send_worker_to_method(self, methodRequested, workerId):
        mType = methodRequested
        workerConnection = self.workerConnections[workerId]
        self.methodConnections[mType].send(['worker', workerConnection])

    def work_loop(self):
        while True:
            if not self.errorQueue.empty():
                data = self.errorQueue.get()
                print(str(data))
                continue
            
            if not self.workQueue.empty():
                
                if(self.limits['appContinuous'][1] == 0):
                    self.continuousTime = time.perf_counter()
                if(self.limits['appBurst'][1] == 0):
                    self.burstTime = time.perf_counter()
                    
                if not self.under_limit('appContinuous'):
                    print('global maybe waiting')
                    self.wait_until_reset('appContinuous')
                    continue
                    
                if not self.under_limit('appBurst'):
                    print('global maybe waiting')
                    self.wait_until_reset('appBurst')
                    continue

                workerRequest = self.workQueue.get()
                self.limits['appBurst'][1] += 1
                self.limits['appContinuous'][1] += 1
            
                methodRequested = workerRequest[0]
                workerId = workerRequest[1]
                self.send_worker_to_method(methodRequested, workerId)
                continue

            


testArguments = [{'methodName' : 'byMatchId',
                 'matchId': 2841964828},
                 
                 {'methodName' : 'byName',
                 'summonerString': 'Keyboard Warrìor'}]

def methodProcess(conn, name, methodList):
    mp = methodProcessor(conn, name, methodList)
    mp.work_loop()

def requestProcess(conn, identifier, workQueue, errorQueue):
    rh = requestHandler(conn, identifier)
    rh.prepJob(testArguments[0])
    rh.doJob(workQueue, errorQueue)
    

def terminateProcesses(processList):
    for process in processList:
        process.terminate()


if __name__ == '__main__':
    delegator = workDelegator('na1')
    processList = []
    for method in staticMethods:
        delegator_conn, method_conn = Pipe()
        delegator.add_new_method_connection(delegator_conn, method)
        methodList = maxLimits[method]
        p = Process(target=methodProcess, args=(method_conn, method, methodList))
        processList.append(p)
        p.start()
        
    for n in range(2):
        delegator_conn, worker_conn = Pipe()
        delegator.add_new_worker_connection(delegator_conn, n)
        p = Process(target=requestProcess, args=(worker_conn, n, delegator.workQueue, delegator.errorQueue))
        processList.append(p)
        p.start()

    delegator.work_loop()
        
        
                
