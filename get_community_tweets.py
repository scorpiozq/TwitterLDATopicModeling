#!/usr/bin/python
# https://dev.twitter.com/overview/api/response-codes
import sys
import pickle
import tweepy
import unicodedata
import os
import ast
import json
import pyprind
from collections import defaultdict

# populate access credentials into list
def get_access_creds():
    i = 0 
    credentials = defaultdict(list)

    print('Building list of developer access credentials...')
    with open('twitter_dev_accounts.txt', 'r') as infile:
        for line in infile:
            if line.strip():
                credentials[i].append(line.strip())
            else:
                if(verify_working_credentials(credentials[i])):
                    i += 1
                else:
                    del credentials[i]

    return credentials

def verify_working_credentials(credentials):
    verified = True
    consumer_key = credentials[0]
    consumer_secret = credentials[1]
    access_token = credentials[2]
    access_secret = credentials[3]

    auth = tweepy.auth.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_secret)
    api = tweepy.API(auth)

    try:
        api.verify_credentials()

    except tweepy.TweepError as e:
        verified = False

    except Exception as e:
        print(str(e))

    finally:
        return verified

# authenticates to the Twitter API and handles connection issues
def authenticate(credentials):
    index = 0
    # changes the access credentials each time to avoid api rate limit
    while True:
        if(isinstance(credentials, list)):
            consumer_key = credentials[0]
            consumer_secret = credentials[1]
            access_token = credentials[2]
            access_secret = credentials[3]
        else:
            consumer_key = credentials[index][0]
            consumer_secret = credentials[index][1]
            access_token = credentials[index][2]
            access_secret = credentials[index][3]
                
        auth = tweepy.auth.OAuthHandler(consumer_key, consumer_secret)
        auth.set_access_token(access_token, access_secret)
        api = tweepy.API(auth)

        # handles connection status updates
        try:
            limit = api.rate_limit_status()
            status_limit = limit['resources']['statuses']['/statuses/user_timeline']['remaining']
            if status_limit > 100:
                return api

        except tweepy.TweepError as e:
            pass
            #print(e.message[0]['message'])

        except Exception as e:
            print(str(e))

        finally:
            if index == (len(credentials) - 1):
                index = 0
            else:
                index += 1

# writes the Tweet metadata being scraped to a file as:
# tweet_type, user_id, RT_user_id, RT_count, tweet_id, hashtags, screen_name
def write_tweet_meta(tweets, meta_filename, followers_filename):
    with open(meta_filename, 'a') as clique_tweet_metadata:
        for tweet in tweets:
            user_followers = {}
            favorite_count = tweet.favorite_count
            tweet_id = tweet.id_str
            screen_name = tweet.user.screen_name
            retweet_count = tweet.retweet_count
            user_id = tweet.user.id
            follower_count = tweet.user.followers_count
        
            # pickle dictionary to save memory
            if os.path.exists(followers_filename):
                with open(followers_filename, 'rb') as follower_dump:
                    user_followers = pickle.load(follower_dump)

            # get the follower count of each user
            if not any(str(user_id) in key for key in user_followers):
                user_followers[str(user_id)] = str(follower_count)
            
            # pickle dictionary to save memory
            with open(followers_filename, 'wb') as follower_dump:
                pickle.dump(user_followers, follower_dump)
                
            user_followers = {}

            # extract hashtags
            tagList = tweet.entities.get('hashtags')
            # check if there are hashtags
            if(len(tagList) > 0):
                hashtags = [tag['text'] for tag in tagList]
        
            # if the tweet is not a retweet
            if not hasattr(tweet, 'retweeted_status'):
                out = '%s\t%s\t%s\t%s\t%s\t%s\t%s\t\n' % ('T', user_id, user_id, retweet_count, tweet_id, hashtags, screen_name) 
            # if it is retweet, get user id of original tweet 
            else:
                # must be defined in the else because if incoming tweet is not a retweet
                rt_user_id = tweet.retweeted_status.user.id
                rt_screen_name = tweet.retweeted_status.user.screen_name
                orig_tweet_id = tweet.retweeted_status.id_str
        
                out = '%s\t%s\t%s\t%s\t%s\t%s\t%s\t\n' % ('RT', user_id, rt_user_id, retweet_count, orig_tweet_id, hashtags, rt_screen_name) 
            clique_tweet_metadata.write(out)

def get_followers(user_id, api):
    followers = []
    while True:
        try:
            cursor = tweepy.Cursor(api.followers, id=user_id).pages()
            for page in cursor:
                followers += page

        except tweepy.TweepError as e:
            pass
            #print(e.message[0]['message'])

        except Exception as e:
            print(str(e))
                
        finally:
            return tweets

def unfollow_users(credentials, comm_set):
    dev_ids = []
    for index in credentials:
        developer_id = credentials[index][2].split('-')[0]
        if(developer_id in dev_ids):
            continue

        api = authenticate(credentials[index])
        for user_id in comm_set:
            try:
                api.destroy_friendship(user_id) 
                print(str(developer_id) + ' unfollowed ' + str(user_id))

            except tweepy.TweepError as e:
                pass
                #print(e.message[0]['message'])

            except Exception as e:
                print(str(e))
        
        dev_ids.append(developer_id)

def follow_users(credentials, comm_set):
    dev_ids = []
    for index in credentials:
        developer_id = credentials[index][2].split('-')[0]
        if(developer_id in dev_ids):
            continue

        api = authenticate(credentials[index])
        for user_id in comm_set:
            try:
                api.create_friendship(user_id) 
                print(str(developer_id) + ' now following ' + str(user_id))

            except tweepy.TweepError as e:
                pass
                #print(e.message[0]['message'])

            except Exception as e:
                print(str(e))

        dev_ids.append(developer_id)

def get_tweets(user_id, api):
    tweets = []
    while True:
        try:
            cursor = tweepy.Cursor(api.user_timeline, user_id).pages()
            for page in cursor:
                tweets += page

        except tweepy.TweepError as e:
            pass
            #print(e.message[0]['message'])

        except Exception as e:
            print(str(e))

        finally:
            return tweets
            
def user_status_count(api, user_id):
    count = 0

    try: 
        user = api.get_user(user_id=user_id)
        if(user.statuses_count):
            count = user.statuses_count

    except tweepy.TweepError as e:
        pass
        #print(e.message[0]['message'])

    except Exception as e:
        print(str(e))

    finally:
        return count

def write_tweets(tweets, tweet_filename):
    with open(tweet_filename, 'w') as user_tweets:
        for tweet in tweets:
            user_tweets.write(tweet.text.encode("utf-8") + '\n')

def main(topology):
    inactive_users = {}
    active_users = {}
    credentials = get_access_creds()
    tweets_dir = './dnld_tweets/'

    with open(topology, 'r') as inp_file:
        comm_set = set(user for community in inp_file for user in ast.literal_eval(community))

    if not os.path.exists(os.path.dirname(tweets_dir)):
        os.makedirs(os.path.dirname(tweets_dir), 0o755)
    
    n = len(comm_set)
    bar = pyprind.ProgPercent(n, track_time=True, title='Downloading Tweets') 
    while comm_set:
        user = comm_set.pop()
        bar.update(item_id=user)
    
        api = authenticate(credentials)

        # don't waste time trying to download tweets for inactive user
        status_count = user_status_count(api, user)

        # skip user if you've already downloaded their tweets
        if os.path.exists(tweets_dir + str(user)):
            if status_count > 10:
                active_users[str(user)] = status_count
            else:
                inactive_users[str(user)] = status_count 
            continue

        tweets = get_tweets(user, api)

        if tweets:
            tweet_filename = tweets_dir + str(user)
            write_tweets(tweets, tweet_filename)

            if status_count > 10:
                active_users[str(user)] = status_count
            else:
                inactive_users[str(user)] = status_count 
        else:
                inactive_users[str(user)] = 0 

    with open('user_tweet_count.json', 'w') as outfile:
        json.dump(active_users, outfile, sort_keys=True, indent=4)

    with open('inactive_users.json', 'w') as outfile:
        json.dump(inactive_users, outfile, sort_keys=True, indent=4)

if __name__ == '__main__':
    sys.exit(main(sys.argv[1]))
