from RiotAPI import RiotAPI
from sqlInterface import *
from urllib.parse import quote
import RiotConsts as Consts

import sqlite3
import time
import json
import pprint
import os
import datetime

test = "keyboard warrÌor"
api_key = 'RGAPI-dfd3a27b-1d61-4124-be45-14bceacce875'

def getAccountId(summonerString):
    api = RiotAPI(api_key)
    print(quote(summonerString))
    summoner = api.get_summoner_by_name(quote(summonerString))
    accountId = summoner['accountId']
    return accountId

#returns list of matches for an account and queue if specified
def getMatchList(accountId, queueNumber=None, startIndex=0, endIndex=100):
    api = RiotAPI(api_key)
    args = {'beginIndex' : startIndex, 'endIndex' : endIndex}
    if queueNumber:
        args['queue'] = queueNumber
    fullMatchDataAll = api.get_match_list(accountId, args)
    matchList = fullMatchDataAll['matches']
    return matchList

#sorts matchList by champion for sorting purposes
def sortMatchListByChamp(matchList):
    matchHistoryByChampion = {}
    for game in matchList:
        if game['champion'] not in matchHistoryByChampion:
            matchHistoryByChampion[game['champion']] = []
        matchHistoryByChampion[game['champion']].append(game)

    return matchHistoryByChampion

#returns list of games for said champion
def selectChampion(matchHistoryByChampion, championId):
    return matchHistoryByChampion[championId]

#selects the n most recent matches from a list, default is 20
def selectMatches(matchList, n=20):
    if(len(matchList) < n):
        return matchList
    return matchList[0:n]

#gets detailed match data for matches in a list
#WARNING, DO NOT PASS IN UNSHORTENED MATCH LIST#
#API RATE LIMITS WILL SCREW YOU#
def getDetailedMatchData(matchList):
    api = RiotAPI(api_key)
    detailedMatchData = {}
    for game in matchList:
        print("requesting offsite data")
        gameId = game['gameId']
        detailedMatchData[gameId] = api.get_match_info(gameId)
    return detailedMatchData

#extracts data from detailedMatch DTO into more usable format defined as follows:
def parseDetailedMatchDataHistoryView(detailedMatchData, accountId):
    usefulMatchData = {}
    for game, data in detailedMatchData.items():
        usefulMatchData[game] = {}
        currentGameMatchData = usefulMatchData[game]

        primaryPlayerId = None
        for playerArray in data['participantIdentities']:
            playerData = playerArray['player']
            participantId = playerArray['participantId']

            currentGameMatchData[participantId] = {}
            currentGameMatchData[participantId]['summonerInfo'] = playerData

            if(playerData['accountId'] == accountId):
                currentGameMatchData['primaryPlayerId'] = playerArray['participantId']

        currentGameMatchData['blueTeam'] = data['teams'][0]
        currentGameMatchData['redTeam'] = data['teams'][1]
        time = data['gameDuration']
        m,s = divmod(time, 60)
        currentGameMatchData['gameDuration'] = [m, s, time]
        playerIndex = 1
        for stats in data['participants']:
            currentGameMatchData[playerIndex]['stats'] = stats
            playerIndex += 1

    return usefulMatchData

##Need to make safe for exceptions
def forceUpdateChampionData():
    api = RiotAPI(api_key)
    champStuff = api.get_champ_data_all_ddragon()
    champStuff['LUT'] = {}
    storagePath = os.path.dirname(Consts.URL['localChampData'])
    if not os.path.exists(storagePath):
        os.makedirs(storagePath, exist_ok=True)
    for key, info in champStuff['data'].items():
        champStuff['LUT'][int( info['key'] )] = info['id']
    try:
        os.remove(Consts.URL['localChampData'])
    except OSError:
        pass

    with open(Consts.URL['localChampData'], 'w') as output:
        json.dump(champStuff, output, indent=4)

    return

def updateSquareChampionAssetsAll():
    api = RiotAPI(api_key)
    championData = api.get_champ_data()
    for name in championData['data']:
        championId = championData['data'][name]['key']
        api.get_square_champ_asset(championId, championData)

    return

def updateSquareItemAssetsAll():
    api = RiotAPI(api_key)
    itemData = api.get_item_data()
    for itemId in itemData['data']:
        api.get_square_item_asset(itemId, itemData)

    return

def updateSquareSsAssetsAll():
    api = RiotAPI(api_key)
    ssData = api.get_ss_data()
    for spellName in ssData['data']:
        spellId = ssData['data'][spellName]['key']
        api.get_square_ss_asset(spellId, ssData)

    return

def updateSquareRuneAssetsAll():
    api = RiotAPI(api_key)
    runeData = api.get_rune_data()
    for key, runeTrees in runeData.items():
        isTree = False
        if key == 'trees':
            isTree = True
        for runeId in runeTrees:
            api.get_square_rune_asset(runeId, runeData, isTree)

def getSquareChampAsset(conn, championId):
    api = RiotAPI(api_key)
    champData = {}
    if conn:
        champData = requestLocalChampData(conn)
    return api.get_square_champ_asset(championId, champData)

def getSquareItemAsset(conn, itemId):
    api = RiotAPI(api_key)
    itemData = {}
    if conn:
        itemData = requestLocalItemData(conn)
    return api.get_square_item_asset(itemId, itemData)

def getSquareSsAsset(conn, spellId):
    api = RiotAPI(api_key)
    ssData = {}
    if conn:
        ssData = requestLocalSsData(conn)
    return api.get_square_ss_asset(spellId, ssData)

def getSquareRuneAsset(conn, runeId):
    api = RiotAPI(api_key)
    runeData = {}
    if conn:
        runeData = requestLocalRuneData(conn)
    tree = isTree(runeId, runeData)
    return api.get_square_rune_asset(runeId, runeData, tree)

def isTree(runeId, runeData):
    testId = str(runeId)
    for treeValue in runeData['trees'].keys():
        if testId == treeValue:
            return True
    return False

def mergeLocalDataAndNewData(matchList, localMatchList):
    matchList.update(localMatchList)
    return

def fullRequestGeneral(conn, summonerString, n, championId = None, startIndex = 0):
    accountId = getAccountId(summonerString)
    endingIndex = int(startIndex) + int(n)
    print(startIndex)
    matchList = getMatchList(accountId, startIndex=startIndex, endIndex=endingIndex)
    if championId:
        matchList = sortMatchListByChamp(matchList)
        matchList = selectChampion(matchList, championId)
    matchList = selectMatches(matchList, n)
    localMatches = checkLocalForMatches(conn, matchList)
    deJsonify(localMatches)
    offsiteData = getDetailedMatchData(matchList)
    finalDataStorage = parseDetailedMatchDataHistoryView(offsiteData, accountId)
    storeMatchData(conn, finalDataStorage)
    mergeLocalDataAndNewData(finalDataStorage, localMatches)
    return finalDataStorage

def insertChampPortraitsPlayerNames(conn, finalMatchData):
    for gameId, game in finalMatchData.items():
        portraitStorage = []
        nameStorage = []
        for key, summoner in game.items():
            if isinstance(key, int):
                portraitStorage.append(getSquareChampAsset(conn, summoner['stats']['championId']))
                nameStorage.append(summoner['summonerInfo']['summonerName'])
        game['champPortraits'] = portraitStorage
        game['playerNames'] = nameStorage
    return

def insertPrimaryPlayerItems(conn, finalMatchData):
    for gameId, game in finalMatchData.items():
        itemStorage = []
        summoner = game[game['primaryPlayerId']]
        for n in range(0,7):
            item = 'item' + str(n)
            itemStorage.append(getSquareItemAsset(conn, summoner['stats']['stats'][item]))
        itemStorage.insert(3, itemStorage.pop())
        game['primaryPlayerItems'] = itemStorage
    return

def insertPrimaryPlayerSs(conn, finalMatchData):
    for gameId, game in finalMatchData.items():
        ssStorage = []
        summoner = game[game['primaryPlayerId']]
        ssStorage.append(getSquareSsAsset(conn, summoner['stats']['spell1Id']))
        ssStorage.append(getSquareSsAsset(conn, summoner['stats']['spell2Id']))
        game['primaryPlayerSs'] = ssStorage
    return

def insertPrimaryPlayerRunes(conn, finalMatchData):
    for gameId, game in finalMatchData.items():
        runeStorage = []
        summoner = game[game['primaryPlayerId']]
        runeStorage.append(getSquareRuneAsset(conn, summoner['stats']['stats']['perk0']))
        runeStorage.append(getSquareRuneAsset(conn, summoner['stats']['stats']['perkSubStyle']))
        game['primaryPlayerRunes'] = runeStorage
    return
                
    
    
    

