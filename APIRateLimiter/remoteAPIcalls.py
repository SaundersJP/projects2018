from RiotAPI import RiotAPI
from urllib.parse import quote

import json

test = "keyboard warrÌor"
api_key = 'RGAPI-458dc77b-38c5-43e4-9399-77e44c5be975'

#expect argument dictionary where summoner name is scoped by key 'summonerString'
def getAccountId(args):
    summonerString = args['summonerString']
    api = RiotAPI(api_key)
    summoner = api.get_summoner_by_name(quote(summonerString))
    return summoner

#expects argument dictionary with 'accountId', 'queue', 'beginIndex', 'endIndex'
#'queue' should be none to request non-queue specific match info
def getMatchList(args):
    api = RiotAPI(api_key)
    accountId = args.pop('accountId')

    #prevents API request from submitting a bad URL 
    if not args['queue']:
        del args['queue'] 
    fullMatchDataAll = api.get_match_list(accountId, args)
    return fullMatchDataAll



#expects argument diction with 'matchId'
def getSingleDetailedMatchData(args):
    matchId = args['matchId']
    api = RiotAPI(api_key)
    detailedMatchData = api.get_match_info(matchId)
    return detailedMatchData


