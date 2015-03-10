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


class Serializer(object):
    def __init__(self, *args, **kwargs):
        pass

    def serialize(self, data, **kwargs):
        serialized = []
        for i in data:
            obj = {}
            for k, v in kwargs.iteritems():
                obj[k] = i.get(v)
            obj['raw'] = i
            serialized.append(obj)
        return serialized


class YelpSerializer(Serializer):
    def search_places(self, data):
        serialized = []
        for i in data:
            address = ' '.join(i['location']['display_address'])
            obj = {'address': address,
                   'place_id': i['id'],
                   'name': i['name'],
                   'raw': i}
            serialized.append(obj)
        return serialized


class FacebookSerializer(Serializer):
    def search_places(self, data):
        serialized = []
        for i in data:
            obj = {'address': i['location']['street'],
                   'place_id': i['id'],
                   'name': i['name'],
                   'raw': i}
            serialized.append(obj)
        return serialized


class FoursquareSerializer(Serializer):
    def search_places(self, data):
        serialized = []
        for i in data:
            address = ' '.join(i['location']['formattedAddress'])
            obj = {'address': address,
                   'place_id': i['id'],
                   'name': i['name'],
                   'raw': i}
            serialized.append(obj)
        return serialized

    def get_place_details(self, data):
        return self.serialize(data)


class GoogleSerializer(Serializer):
    def search_places(self, data):
        return self.serialize(data,
                              address='vicinity',
                              place_id='id',
                              name='name')

    def get_place_details(self, data):
        return self.serialize(data)


class Provider(object):
    def __init__(self):
        if self.serializer:
            self.serializer = self.serializer()

    def search_places(self, *args, **kwargs):
        raise NotImplementedError

    def get_place_details(self, *args, **kwargs):
        raise NotImplementedError


class Google(Provider):
    name = 'google'
    serializer = GoogleSerializer

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
        params.update(**kwargs)
        res = requests.get(url, params=params)

        if res.ok:
            return self.serializer.search_places(res.json()['results'])
        else:
            raise APIError('An error occurred with %s API' % self.name)

    def get_place_details(self, place_id, **kwargs):
        url = 'https://maps.googleapis.com/maps/api/place/details/json'
        params = {'key': GOOGLE_API_KEY,
                  'placeid': place_id}
        params.update(**kwargs)
        res = requests.get(url, params=params)

        if res.ok:
            return res.json()['result']
        else:
            raise APIError('An error occurred with %s API' % self.name)


class Yelp(Provider):
    name = 'yelp'
    serializer = YelpSerializer

    def search_places(self, name, address, **kwargs):
        url = 'http://api.yelp.com/v2/search'
        params = {'radius_filter': RADIUS,
                  'location': address,
                  'term': name}
        params.update(**kwargs)

        session = OAuth1Session(YELP_CONSUMER_KEY,
                                YELP_CONSUMER_SECRET,
                                access_token=YELP_ACCESS_TOKEN,
                                access_token_secret=YELP_ACCESS_TOKEN_SECRET)
        res = session.get(url, params=params)

        if res.ok:
            return self.serializer.search_places(res.json()['businesses'])
        else:
            raise APIError('An error occurred with %s API' % self.name)

    def get_place_details(self, yelp_id, **kwargs):
        url = 'http://api.yelp.com/v2/business/%s' % (yelp_id)
        params = {}
        params.update(**kwargs)

        session = OAuth1Session(YELP_CONSUMER_KEY,
                                YELP_CONSUMER_SECRET,
                                access_token=YELP_ACCESS_TOKEN,
                                access_token_secret=YELP_ACCESS_TOKEN_SECRET)
        res = session.get(url, params=params)

        if res.ok:
            return res.json()
        else:
            raise APIError('An error occurred with %s API' % self.name)


class Foursquare(Provider):
    name = 'foursquare'
    serializer = FoursquareSerializer

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
        params.update(**kwargs)
        res = requests.get(url, params=params)
        if res.ok:
            return self.serializer.search_places(
                res.json()['response']['venues'])
        else:
            raise APIError('An error occurred with %s API' % self.name)

    def get_place_details(self, venue_id):
        url = 'https://api.foursquare.com/v2/venues/%s' % (venue_id)
        params = {'client_id': FOURSQUARE_CLIENT_ID,
                  'client_secret': FOURSQUARE_CLIENT_SECRET,
                  'v': FOURSQUARE_API_VERSION}
        res = requests.get(url, params=params)
        if res.ok:
            return res.json()['response']
        else:
            raise APIError('An error occurred with %s API' % self.name)


class Facebook(Provider):
    name = 'facebook'
    serializer = FacebookSerializer

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
        params.update(**kwargs)
        res = requests.get(url, params=params)
        if res.ok:
            return self.serializer.search_places(res.json()['data'])
        else:
            raise APIError('An error occurred with %s API' % self.name)

    def get_place_details(self, place_id, **kwargs):
        url = 'https://graph.facebook.com/%s' % place_id
        access_token = '%s|%s' % (FACEBOOK_APP_ID, FACEBOOK_APP_SECRET,)
        params = {'access_token': access_token}
        res = requests.get(url, params=params)
        if res.ok:
            return res.json()
        else:
            raise APIError('An error occurred with %s API' % self.name)
