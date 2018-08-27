import RiotConsts as Consts
import sqlite3
import time
import json
import copy


#checks if match is in local database
#if so removes it from matchList and returns a dictionary
def checkLocalForMatches(conn, matchList):
    usefulGames = {}
    loopList = copy.deepcopy(matchList)
    for game in loopList:
        gameId = game['gameId']
        query = "SELECT match_data FROM matches WHERE match_id = ?"
        result = queryDb(conn, query, [gameId], True)
        if result:
            print("Found local data")
            gameData = json.loads(result[0])
            usefulGames[gameId] = gameData
            matchList.remove(game)
                    
    return usefulGames

#quick note to future readers
#gameKeys uses a list cast to prevent iteration issues
#caused when modifying the dictKeys object during a loop
#otherwise values will not be properly converted to ints
def deJsonify(localMatchDict):
    for key,game in localMatchDict.items():
        gameKeys = list(game.keys())
        for key2 in gameKeys:
            if isinstance(key2, str):
                if key2.isnumeric():
                    game[int(key2)] = game.pop(key2)
    return

def storeMatchData(conn, parsedMatchData):
    for matchId, matchData in parsedMatchData.items():
        jsonified = json.dumps(matchData, indent=1)
        query = "INSERT INTO matches (match_id, match_data) VALUES (?, ?)"
        queryDb(conn, query, [matchId, jsonified])
    return


def generateDatabase():
    conn = sqlite3.connect('test.db', isolation_level=None)
    conn.execute('PRAGMA journal_mode=wal;')
    conn.commit()
    with conn as cur, open('databaseSetup.sql', 'r') as myfile:
        cur.executescript(myfile.read())
    return conn

def showTables(conn):
    with conn as cur:
        results = cur.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
        for name in results:
            print(name)

def resetMatches(conn):
    with conn as cur, open('databaseSetup.sql', 'r') as myfile:
        results = cur.execute("DROP TABLE matches;")
        query = myfile.read()
        cur.executescript(query)

def queryDb(conn, query, args=[], one=False):
    returnValue = None
    with conn as cur:
        returnValue = cur.execute(query, args).fetchall()
    return (returnValue[0] if returnValue else None) if one else returnValue

#Should only be ran after updating static data with all functions from RiotMain.py
def updateStaticInDb(conn):
    with open('databaseSetup.sql', 'r') as myfile:
        queryDb(conn, "DROP TABLE IF EXISTS static;")
        conn.executescript(myfile.read())
    with open(Consts.URL['localItemData'], 'r') as itemData, open(Consts.URL['localChampData'],'r') as champData, open(Consts.URL['localSsData']) as ssData, open(Consts.URL['localRuneData']) as runeData:
        query = "INSERT INTO static (tag,data) VALUES (?, ?)"
        queryDb(conn, query, ['item_data', itemData.read()])
        queryDb(conn, query, ['champ_data', champData.read()])
        queryDb(conn, query, ['ss_data', ssData.read()])
        queryDb(conn, query, ['rune_data', runeData.read()])
    return

def requestLocalItemData(conn):
    result = queryDb(conn, "SELECT data FROM static WHERE tag = ?", ['item_data'], one=True)[0]
    return json.loads(result)

def requestLocalChampData(conn):
    result = queryDb(conn, "SELECT data FROM static WHERE tag = ?", ['champ_data'], one=True)[0]
    return json.loads(result)

def requestLocalSsData(conn):
    result = queryDb(conn, "SELECT data FROM static WHERE tag = ?", ['ss_data'], one=True)[0]
    return json.loads(result)

def requestLocalRuneData(conn):
    result = queryDb(conn, "SELECT data FROM static WHERE tag = ?", ['rune_data'], one=True)[0]
    return json.loads(result)
