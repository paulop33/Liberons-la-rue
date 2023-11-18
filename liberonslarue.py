# coding: utf-8

# données critiques

## twitter key
consumer_key = ''
consumer_secret = ''
access_token = ''
access_token_secret = ''

## bordeaux metropole key
bordeaux_metropole_key = ''

import matplotlib.pyplot as plt
import random
import requests
from datetime import datetime, timedelta
import json
from types import SimpleNamespace
import statistics
from twython import Twython
import re
from requests_oauthlib import OAuth1Session

twitter = Twython(
    consumer_key,
    consumer_secret,
    access_token,
    access_token_secret
)

url = "http://data.bordeaux-metropole.fr/geojson/aggregate/ST_PARK_P?"

today = datetime.now().date()
start = datetime(today.year, today.month, today.day)
start = start - timedelta(days=1)
datetime_end =  start + timedelta(hours=23, minutes=59, seconds=59)

params = dict(
    key=bordeaux_metropole_key,
    filter='{"secteur": "HYPER_CENTRE"}',
    attributes='{"libres":"average", "total":"average"}',
    rangeStart=start.astimezone(),
    rangeEnd=datetime_end.astimezone(),
    rangeStep='hour'
)

response = requests.get(url=url, params=params)
jsonresponse = json.loads(response.text, object_hook=lambda d: SimpleNamespace(**d))
timeRes = {}
regexDate = r"\d{4}-\d{2}-\d{2}T(\d{2}):00:00\+\d{2}:\d{2}"

for value in jsonresponse.features:
    matchObj = re.match( regexDate, value.properties.time, re.M|re.I)
    time = int(matchObj.group(1))

    if hasattr(value.properties, 'total'):
        if time in timeRes:
            timeRes[time]['total'] += value.properties.total
            timeRes[time]['libres'] += value.properties.libres
            timeRes[time]['total_libres'] += value.properties.libres
        else:
            timeRes[time] = {}
            timeRes[time]['total'] = value.properties.total
            timeRes[time]['libres'] = value.properties.libres
            timeRes[time]['total_libres'] = value.properties.libres

        timeRes[time]['taux_occupation'] = (timeRes[time]['total'] - timeRes[time]['libres']) / timeRes[time]['total']

valuesTauxOccupation = []
placesLibres = []
placesTotales = []

for time in range(0, 24):
    if time in timeRes:
        valuesTauxOccupation.append(timeRes[time].get('taux_occupation') * 100)
        placesLibres.append(timeRes[time].get('total_libres'))
        placesTotales.append(timeRes[time].get('total'))
    else:
        valuesTauxOccupation.append(0)

moyenne_jour = (1 - sum(placesLibres) / sum(placesTotales)) * 100
moyenne_jour_place_libre = statistics.mean(placesLibres)
moyenne_jour_places_totales = statistics.mean(placesTotales)
min_jour_place_libre = min(placesLibres)

titre = 'Taux d\'occupation du %s :  %0.1f%%' % (start.strftime('%d/%m/%Y'), moyenne_jour)
fig = plt.figure()
fig.patch.set_facecolor('xkcd:white')
n = ['%dh' % i for i in range(24)]
plt.bar(n, valuesTauxOccupation)

suspicionBug=False
for i in range(len(valuesTauxOccupation)):
    if (i-1 >= 0 and valuesTauxOccupation[i] == valuesTauxOccupation[i-1]):
        plt.annotate('*', xy=(n[i],valuesTauxOccupation[i]), ha='center', va='bottom')
        suspicionBug = True

plt.xlabel('Heure')
plt.ylabel(u'Taux de remplissage')
plt.axis([0, 24, 0, 100])
plt.xticks(rotation=45)
plt.grid(True)
plt.title(titre)
plt.figtext(0.6, 0.05, 'Auteur : @policedepierrot') 
plt.figtext(0.05, 0.05, 'Source : Bordeaux Métropole')
plt.figtext(0.05, 0.0, '* Suspicion d\'erreur dans les datas')
plt.figtext(0.05, 0.1, 'Moyenne totale de places libres par heure : {0} sur {1} places'.format(int(moyenne_jour_place_libre), int(moyenne_jour_places_totales))) 
plt.figtext(0.05, 0.15, 'Taux d\'occupation des parkings hors voirie de l\'hypercentre bordelais ') 
plt.subplots_adjust(bottom=0.35)
#plt.show()
plt.savefig('foo.png')

tweet_text = titre + "\n" + "Minimum de places libres : {0}, équivalent à {1:.2f}km libérables".format(int(min_jour_place_libre), float(min_jour_place_libre * 5 / 1000)) 
image = open('foo.png', 'rb')
response = twitter.upload_media(media=image)
media_id = [str(response['media_id'])]
twitter.update_status(status=tweet_text, media_ids=media_id)

# Make the request
oauth = OAuth1Session(
    consumer_key,
    client_secret=consumer_secret,
    resource_owner_key=access_token,
    resource_owner_secret=access_token_secret,
)

payload = {"text": tweet_text, "media": {"media_ids": media_id}}
# Making the request
response = oauth.post(
    "https://api.twitter.com/2/tweets",
    json=payload,
)
print("Tweeted: " + tweet_text)
