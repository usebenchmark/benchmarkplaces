import os
import pytz
from datetime import datetime

from rauth import OAuth1Service, OAuth1Session

CONSUMER_KEY = os.environ.get('TWITTER_CONSUMER_KEY')
CONSUMER_SECRET = os.environ.get('TWITTER_CONSUMER_SECRET')
ACCESS_TOKEN = os.environ.get('ACCESS_TOKEN')
ACCESS_TOKEN_SECRET = os.environ.get('ACCESS_TOKEN_SECRET')
BASE_URL = 'https://api.twitter.com/1.1/'
FORMAT = '%a %b %d %H:%M:%S +0000 %Y' # twitter time format
COUNT = 100 # default tweet count

consumer_creds = {'consumer_key': CONSUMER_KEY,
                  'consumer_secret': CONSUMER_SECRET}
access_token_creds = {'access_token': ACCESS_TOKEN,
                      'access_token_secret': ACCESS_TOKEN_SECRET}


class TwitterSerializer(object):
    def search_tweets(self, data):
        serialized = []
        for x in data:
            tweet = {}
            tweet['text'] = x.get('text')
            tweet['review_id'] = x.get('id_str')
            tweet['author'] = x.get('user', {}).get('screen_name')
            tweet['source'] = 'twitter'
            tweet['source_created_on'] = \
                datetime.strptime(x.get('created_at'), FORMAT).replace(tzinfo=pytz.UTC)
            tweet['oem'] = x
            serialized.append(tweet)
        return serialized


class TwitterSession(OAuth1Session):
    def __init__(self, *args, **kwargs):
        args = args if len(args) else [CONSUMER_KEY, CONSUMER_SECRET]
        kwargs.update(access_token_creds)
        super(TwitterSession, self).__init__(*args, **kwargs)


class Twitter(OAuth1Service):
    serializer = TwitterSerializer()

    def __init__(self, *args, **kwargs):
        a = args if len(args) else [CONSUMER_KEY, CONSUMER_SECRET]
        kw = {'name': 'twitter',
              'base_url': BASE_URL,
              'session_obj': TwitterSession}
        kw.update(kwargs)
        super(Twitter, self).__init__(*a, **kw)

    def search_tweets(self, q, **kwargs):
        params = {'q': q, 'count': COUNT}
        params.update(kwargs)
        response = self.get_session().get('search/tweets.json',
                                          params=params)
        if response.ok:
            return self.serializer.search_tweets(response.json()['statuses'])
        else:
            raise SourceError('An error occurred with %s API' % self.name,
                              response)
