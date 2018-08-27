import RiotConsts as Consts
import requests
import urllib
import json
import shutil
import os


class RiotAPI(object):

    def __init__(self, api_key, region = Consts.REGIONS['north_america']):
        self.api_key=api_key
        self.region=region

    def request(self, api_url, params = {}):
        args = {'api_key' : self.api_key}
        for key, value in params.items():
            if key not in args:
                args[key]=value
        response = requests.get(
            Consts.URL['base'].format(
                proxy=self.region,
                url = api_url
                ),
            params=args
        )
        return response

    def ddInfoRequest(self, api_url, params = {}):
        args = {'api_key' : self.api_key}
        for key, value in params.items():
            if key not in args:
                args[key]=value
        response = requests.get(
            Consts.URL['ddragonBase'].format(
                patch=Consts.API_VERSIONS['lol_patch'],
                url = api_url
                ),
            params=args
        )
        print(response.url)
        return response.json()
    
    def ddImageRetrieve(self, api_url, fileLocation, runes=False):
        if runes:
            url = Consts.URL['ddragonBaseRunes'].format(
                url = api_url
            )
        else:
            url = Consts.URL['ddragonBase'].format(
                patch=Consts.API_VERSIONS['lol_patch'],
                url = api_url
            )
        storagePath = os.path.dirname(fileLocation)
        if not os.path.exists(storagePath):
            os.makedirs(storagePath, exist_ok=True)
            
        with urllib.request.urlopen(url) as response, open(fileLocation, 'wb') as image:
            shutil.copyfileobj(response, image)

        return fileLocation
            

    def get_summoner_by_name(self, name):
        api_url = Consts.URL['summoner_by_name'].format(
            version=Consts.API_VERSIONS['summoner'],
            names=name
            )
        return self.request(api_url)

    def get_match_list(self, accountId, optionalParams={}):
        api_url = Consts.URL['match_list'].format(
            version = Consts.API_VERSIONS['match_list'],
            accountIds = accountId
        )
        return self.request(api_url, optionalParams)

    def get_match_info(self, gameId):
        api_url = Consts.URL['detailed_match'].format(
            version = Consts.API_VERSIONS['detailed_match'],
            gameIds = gameId
        )
        return self.request(api_url)

    def get_champ_data_all_ddragon(self):
        api_url = Consts.URL['ddInfo'].format(
            infoName = 'champion.json'
        )
        return self.ddInfoRequest(api_url)

    def get_item_data_all_ddragon(self):
        api_url = Consts.URL['ddInfo'].format(
            infoName = 'item.json'
        )
        return self.ddInfoRequest(api_url)

    def get_ss_data_all_ddragon(self):
        api_url = Consts.URL['ddInfo'].format(
            infoName = 'summoner.json'
        )
        return self.ddInfoRequest(api_url)

    def get_rune_data_all_ddragon(self):
        api_url = Consts.URL['ddInfo'].format(
            infoName = 'runesReforged.json'
        )
        return self.ddInfoRequest(api_url)

    def get_item_data(self):
        if not os.path.exists(Consts.URL['localItemData']):
            itemStuff = self.get_item_data_all_ddragon()
            with open(Consts.URL['localItemData'],'w') as output:
                json.dump(itemStuff, output, indent=4)

        with open(Consts.URL['localItemData'],'r') as readIn:
            return json.load(readIn)

    def get_ss_data(self):
        if not os.path.exists(Consts.URL['localSsData']):
            ssStuff = self.get_ss_data_all_ddragon()
            ssStuff['LUT'] = {}
            for spell, info in ssStuff['data'].items():
                ssStuff['LUT'][int( info['key'] )] = info['id']

            with open(Consts.URL['localSsData'],'w') as output:
                json.dump(ssStuff, output, indent=4)

        with open(Consts.URL['localSsData'],'r') as readIn:
            return json.load(readIn)

    def get_rune_data(self):
        if not os.path.exists(Consts.URL['localRuneData']):
            runeStuff = self.get_rune_data_all_ddragon()
            betterFormat = {'trees' : {}, 'runes' : {}}
            for tree in runeStuff:
                for subtree in tree.pop('slots'):
                    for rune in subtree['runes']:
                        runeId = rune['id']
                        rune.pop('id')
                        betterFormat['runes'][runeId] = rune
                treeId = tree['id']
                tree.pop('id')
                betterFormat['trees'][treeId] = tree

            with open(Consts.URL['localRuneData'], 'w') as output:
                json.dump(betterFormat, output, indent=4)

        with open(Consts.URL['localRuneData'], 'r') as readIn:
            return json.load(readIn)


    def get_champ_data(self):
        
        if not os.path.exists(Consts.URL['localChampData']):
            champStuff = self.get_champ_data_all_ddragon()
            champStuff['LUT'] = {}
            for key, info in champStuff['data'].items():
                champStuff['LUT'][int( info['key'] )] = info['id']

            with open(Consts.URL['localChampData'], 'w') as output:
                json.dump(champStuff, output, indent=4)
            
        with open(Consts.URL['localChampData'], 'r') as readIn:
            return json.load(readIn)

    def get_square_champ_asset(self, championId, championData = {}):
        if isinstance(championId, int):
            championId = str(championId)

        if not championData:
            print('OpeningFileForChampData')
            championData = self.get_champ_data()

        name = championData['LUT'][championId]
        fileName = championData['data'][name]['image']['full']

        fileLocation = Consts.URL['localSquare'].format(
            names = name,
            files = fileName
        )

        if os.path.exists(fileLocation):
            return fileLocation
        
        api_url = Consts.URL['ddChampImages'].format(
            imageName = fileName
        )
        return self.ddImageRetrieve(api_url, fileLocation)
    

    def get_square_item_asset(self, itemId, itemData = {}):
        if isinstance(itemId, int):
            itemId = str(itemId)
        if not itemData:
            print('OpeningFileForItemData')
            itemData = self.get_item_data()
        if itemId == '0':
            return None
        try:
            fileName = itemData['data'][itemId]['image']['full']
        except:
            return None
        fileLocation = Consts.URL['localSquareItem'].format(
            files = fileName
        )
        if os.path.exists(fileLocation):
            return fileLocation

        api_url = Consts.URL['ddItemImages'].format(
            imageName = fileName
        )

        return self.ddImageRetrieve(api_url, fileLocation)

    def get_square_ss_asset(self, spellId, ssData = {}):
        if isinstance(spellId, int):
            spellId = str(spellId)
        if not ssData:
            itemData = self.get_ss_data()

        spellName = ssData['LUT'][spellId]
        fileName = ssData['data'][spellName]['image']['full']
        fileLocation = Consts.URL['localSquareSs'].format(
            files = fileName
        )
        if os.path.exists(fileLocation):
            return fileLocation

        api_url = Consts.URL['ddSsImages'].format(
            imageName=fileName
        )
        return self.ddImageRetrieve(api_url, fileLocation)

    def get_square_rune_asset(self, runeId, runeData = {}, tree=False):
        if isinstance(runeId, int):
            runeId = str(runeId)
        if not runeData:
            runeData = self.get_rune_data()

        runeOrTree = 'runes'
        if tree:
            runeOrTree = 'trees'

        fileName = runeData[runeOrTree][runeId]['icon']
        fileLocation = Consts.URL['localSquareRune'].format(
            files=fileName
        )
        if os.path.exists(fileLocation):
            return fileLocation

        api_url = Consts.URL['ddRuneImages'].format(
            imageName=fileName
        )

        return self.ddImageRetrieve(api_url, fileLocation, True)







        
        
