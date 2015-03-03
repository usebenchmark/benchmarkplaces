import os

import requests
from rauth import OAuth1Session

GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
YELP_CONSUMER_KEY = os.environ.get('YELP_CONSUMER_KEY')
YELP_CONSUMER_SECRET = os.environ.get('YELP_CONSUMER_SECRET')
YELP_ACCESS_TOKEN = os.environ.get('YELP_ACCESS_TOKEN')
YELP_ACCESS_TOKEN_SECRET = os.environ.get('YELP_ACCESS_TOKEN_SECRET')
FOURSQUARE_CLIENT_ID = os.environ.get('FOURSQUARE_CLIENT_ID')
FOURSQUARE_CLIENT_SECRET = os.environ.get('FOURSQUARE_CLIENT_SECRET')
FOURSQUARE_API_VERSION = 20150228
FACEBOOK_APP_ID = os.environ.get('FACEBOOK_APP_ID')
FACEBOOK_APP_SECRET = os.environ.get('FACEBOOK_APP_SECRET')

RADIUS = 500  # meters


class APIError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class Provider(object):
    def __init__(self):
        pass

    def search_places(self, *args, **kwargs):
        raise NotImplementedError

    def place_details(self, *args, **kwargs):
        raise NotImplementedError


class Google(Provider):
    name = 'google'

    def get_geo_coords(self, address):
        url = 'https://maps.googleapis.com/maps/api/geocode/json'
        params = {'address': address, 'key': GOOGLE_API_KEY}
        res = requests.get(url, params=params)

        if res.ok:
            data = res.json()
            # TODO We should probably verify the address with the results.
            try:
                lat = data['results'][0]['geometry']['location']['lat']
                lng = data['results'][0]['geometry']['location']['lng']
            except KeyError:
                # TODO raise exception
                pass
            return lat, lng
        else:
            raise APIError('An error occurred with %s API' % self.name)

    def search_places(self, name, address, **kwargs):
        url = 'https://maps.googleapis.com/maps/api/place/nearbysearch/json'
        lat, lng = self.get_geo_coords(address)
        coords = '%s,%s' % (lat, lng,)
        params = {'key': GOOGLE_API_KEY,
                  'keyword': name,
                  'address': address,
                  'radius': RADIUS,
                  'location': coords}
        res = requests.get(url, params=params)

        if res.ok:
            return res.json()['results']
        else:
            raise APIError('An error occurred with %s API' % self.name)


class Yelp(Provider):
    name = 'yelp'

    def search_places(self, name, address, **kwargs):
        url = 'http://api.yelp.com/v2/search'
        params = {'radius_filter': RADIUS,
                  'location': address,
                  'term': name}

        session = OAuth1Session(YELP_CONSUMER_KEY,
                                YELP_CONSUMER_SECRET,
                                access_token=YELP_ACCESS_TOKEN,
                                access_token_secret=YELP_ACCESS_TOKEN_SECRET)
        res = session.get(url, params=params)

        if res.ok:
            return res.json()['businesses']
        else:
            raise APIError('An error occurred with %s API' % self.name)


class Foursquare(Provider):
    name = 'foursquare'

    def search_places(self, name, address, **kwargs):
        url = 'https://api.foursquare.com/v2/venues/search'
        google = Google()
        lat, lng = google.get_geo_coords(address)
        coords = '%s,%s' % (lat, lng,)
        params = {'radius': RADIUS,
                  'query': name,
                  'client_id': FOURSQUARE_CLIENT_ID,
                  'client_secret': FOURSQUARE_CLIENT_SECRET,
                  'v': FOURSQUARE_API_VERSION,
                  'll': coords}
        res = requests.get(url, params=params)
        if res.ok:
            return res.json()['response']['venues']
        else:
            raise APIError('An error occurred with %s API' % self.name)


class Facebook(Provider):
    name = 'facebook'

    def search_places(self, name, address, **kwargs):
        url = 'https://graph.facebook.com/search'
        access_token = '%s|%s' % (FACEBOOK_APP_ID, FACEBOOK_APP_SECRET,)
        google = Google()
        lat, lng = google.get_geo_coords(address)
        coords = '%s,%s' % (lat, lng,)
        params = {'access_token': access_token,
                  'type': 'place',
                  'q': name,
                  'center': coords,
                  'distance': RADIUS}
        res = requests.get(url, params=params)
        if res.ok:
            return res.json()['data']
        else:
            raise APIError('An error occurred with %s API' % self.name)
