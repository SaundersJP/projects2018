from flask import Flask, render_template, request, session, g, jsonify
from urllib.parse import quote
from riotMain import *
from sqlInterface import *
import sqlite3

myAcc = "keyboard warr%C3%8Cor"
app = Flask(__name__, static_url_path='/static')


def get_db():
	if 'db' not in g:
		g.db = generateDatabase()
	return g.db

# @app.teardown_appcontext
# def close_connection(exception):
# 	db = getattr(g, '_database', None)
# 	if db is not None:
# 		db.close()

@app.route('/_get_matches', methods=['POST'])
def get_matches():
	summoner = request.form.get('summonerName')
	beginIndex = request.form.get('beginIndex')
	dbConn = get_db()
	gamesData = fullRequestGeneral(dbConn, summoner, 12, startIndex=int(beginIndex))
	insertChampPortraitsPlayerNames(dbConn, gamesData)
	insertPrimaryPlayerItems(dbConn, gamesData)
	insertPrimaryPlayerSs(dbConn, gamesData)
	insertPrimaryPlayerRunes(dbConn, gamesData)
	sortedKeys = sorted(gamesData.keys(), reverse=True)
	return jsonify({'data' : render_template('games.html', games=gamesData, keys=sortedKeys), 'count': len(gamesData.keys())})

@app.route('/')
def home():
	summoner = request.args.get('summonerName')
	if(summoner):
		session['summonerName'] = summoner
		return render_template('summoner.html')
	return render_template('home.html')

if __name__ == '__main__':
	app.secret_key = 'canYouFeelItNowMrCrabsSurelyYouCanFeelItNowMrCrabs'
	app.run(debug=True, threaded=True)
