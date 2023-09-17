# coding: utf-8

import argparse
import json
import matplotlib.pyplot as plt
import os
import random
import re
import requests
import statistics
from datetime import datetime, timedelta
from twython import Twython
from types import SimpleNamespace


# données critiques

# Parse input arguments
parser = argparse.ArgumentParser()
parser.add_argument('--twitter-consumer-key',
                    default=os.getenv('TWITTER_CONSUMER_KEY'))
parser.add_argument('--twitter-consumer-secret',
                    default=os.getenv('TWITTER_CONSUMER_SECRET'))
parser.add_argument('--twitter-access-token',
                    default=os.getenv('TWITTER_ACCESS_TOKEN'))
parser.add_argument('--twitter-access-token-secret',
                    default=os.getenv('TWITTER_ACCESS_TOKEN_SECRET'))
parser.add_argument('--bordeaux-metropole-key',
                    default=os.getenv('BORDEAUX_METROPOLE_KEY'))
args = parser.parse_args()

## twitter key
consumer_key = args.twitter_consumer_key
consumer_secret = args.twitter_consumer_secret
access_token = args.twitter_access_token
access_token_secret = args.twitter_access_token_secret

## bordeaux metropole key
bordeaux_metropole_key = args.bordeaux_metropole_key

twitter = Twython(
    consumer_key,
    consumer_secret,
    access_token,
    access_token_secret
)

url = "http://data.bordeaux-metropole.fr/geojson/aggregate/ST_PARK_P?"

# source : https://twitter.com/CirculationBxM/status/1452609190208417792?s=20
placesEntrePonts = 366

today = datetime.now().date()
start = datetime(today.year, today.month, today.day)
start = start - timedelta(days=1)
datetime_end =  start + timedelta(hours=23, minutes=59, seconds=59)

params = dict(
    key=bordeaux_metropole_key,
    # filter='{"ident": ["CUBPK17", "CUBPK02", "CUBPK18", "CUBPK27", "CUBPK14"]}',
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
    if value.properties.gid in [245, 229, 233, 227, 243, 228]:
        matchObj = re.match( regexDate, value.properties.time, re.M|re.I)
        time = int(matchObj.group(1))

        if time in timeRes:
            if hasattr(value.properties, 'total'):
                timeRes[time]['total'] += value.properties.total
                timeRes[time]['libres'] += value.properties.libres
                timeRes[time]['total_libres'] += value.properties.libres
        else:
            if hasattr(value.properties, 'total'):
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
n = plt.bar(['%dh' % i for i in range(24)], valuesTauxOccupation, color=(1, 0, 0, 0.6))
plt.xlabel('Heure')
plt.ylabel(u'Taux de remplissage')
plt.axis([0, 24, 0, 100])
plt.xticks(rotation=45)
plt.grid(True)
plt.title(titre)
plt.figtext(0.6, 0.05, 'Auteur : @policedepierrot')
plt.figtext(0.05, 0.05, 'Source : Bordeaux Métropole')
plt.figtext(0.05, 0.1, 'Moyenne totale de places libres par heure : {0} sur {1} places'.format(int(moyenne_jour_place_libre), int(moyenne_jour_places_totales)))
plt.figtext(0.05, 0.15, 'Parkings hors voirie entre les ponts sur les quais rive gauche')
plt.subplots_adjust(bottom=0.35)
#plt.show()
plt.savefig('foo.png')

kmTotal = min_jour_place_libre * 5 / 1000

ratioPlace = min_jour_place_libre / placesEntrePonts * 100
liberable = 'liberables' if kmTotal >= 2 else 'liberable'
tweet_text = "Hier, au minimum, {0} places étaient libres dans les parkings hors voirie entre les ponts de Pierre et Chaban. Cela correspond à {1:.2f}km {2} soit {3:.2f}% des places en surface. \n #liberonsLesQuais".format(int(min_jour_place_libre), float(kmTotal), liberable, float(ratioPlace))

image = open('foo.png', 'rb')
response = twitter.upload_media(media=image)
media_id = [response['media_id']]
twitter.update_status(status=tweet_text, media_ids=media_id)
