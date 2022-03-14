# Importing the libraries
import urllib.request
import pandas as pd
import base64
import requests
import datetime
from urllib.parse import urlencode 
import re
import math
import os
import os.path
from os import path
import configparser as cp

# Reading variables from config file
config = cp.ConfigParser()
config.read('config.ini')
client_id = config['credentials']['client_id']
client_secret = config['credentials']['client_secret']
csv_path = config['paths']['csv_path']
main_path = config['paths']['main_path']
main_path_backslash = config['paths']['main_path_backslash']

# Spotify API class
class spotify_api(object):
  access_token = None
  access_token_expires = datetime.datetime.now()
  access_token_did_expire = True 
  client_id = None
  client_secret = None
  token_url = 'https://accounts.spotify.com/api/token' 

  def __init__(self, client_id, client_secret, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.client_id = client_id
    self.client_secret = client_secret
  
  def get_client_credentials(self):
    # Returns base64 encoded string
    client_id = self.client_id
    client_secret = self.client_secret

    if client_secret == None or client_id == None:
      raise Exception("You must set client_id and client_secret")
    
    client_creds =  f"{client_id}:{client_secret}"
    client_creds_b64 = base64.b64encode(client_creds.encode())
    
    return client_creds_b64.decode()

  def get_token_headers(self):
    client_creds_b64 = self.get_client_credentials()
    
    return {
    "Authorization" : f"Basic {client_creds_b64}"
    }

  def get_token_data(self):
    return {
    "grant_type" : "client_credentials"
    }

  def perform_auth(self):
    token_url = self.token_url
    token_data = self.get_token_data()
    token_headers = self.get_token_headers()
    r = requests.post(token_url, data=token_data, headers = token_headers)

    if r.status_code not in range(200,299):
      raise Exception("Could not authenticate client")
    
    data = r.json()
    now = datetime.datetime.now()
    access_token = data['access_token']
    expires_in = data['expires_in']
    expires = now + datetime.timedelta(seconds = expires_in)
    self.access_token = access_token
    self.access_token_expires = expires
    self.access_token_did_expire = expires < now
    
    return True

  def get_access_token(self):
    token = self.access_token
    expires = self.access_token_expires
    now = datetime.datetime.now()
    
    if expires < now:
      self.perform_auth()
      return self.get_access_token()
    elif token == None:
      self.perform_auth()
      return self.get_access_token()
    
    return token

  def search(self, query, search_type='track', limit = 1):
    access_token = self.get_access_token()
    headers = {
    "Authorization" : f"Bearer {access_token}"
    }
    data = urlencode({'q' : query, 'type' : search_type.lower(), 'limit' : limit})
    endpoint = "https://api.spotify.com/v1/search"
    lookup_url = f"{endpoint}?{data}"
    r = requests.get(lookup_url, headers = headers)
    print(r.status_code)
    
    if r.status_code not in range(200,299):
      return {}
    
    return r.json()

# Initiating API object
spotify_obj = spotify_api(client_id, client_secret)


# Conversion function
def convertMillis(millis):
    minutes = math.floor(int(millis) / 60000)
    seconds = format(((int(millis) % 60000) / 1000), '.0f')
    return str(minutes) + ":" + ('0' if int(seconds) < 10 else '') + str(int(seconds))
  
# Download images

if __name__ == '__main__':
  uri2 = ""
  duration_ms2 = ""
  image_links2 = ""
  i = input("Name of the song: ")

  x = str(spotify_obj.search(f'{i}'))
  link_regex = re.compile('((https?):((//)|(\\\\))+([\w\d:#@%/;$()~_?\+-=\\\.&](#!)?)*)', re.DOTALL)
  uri_search = re.search("'type': 'track', 'uri': '(.*)'}], 'limit': 1", x)
  duration_search = re.search("'duration_ms': (.*), 'explicit':", x)
  links = re.findall(link_regex, x)
  uri2 = "https://scannables.scdn.co/uri/plain/png/ffffff/black/640/{}".format(uri_search.group(1))
  duration_ms2 = convertMillis(duration_search.group(1))
  for lnk in links:
    if lnk[0][8] == 'i':
      image_links2 = lnk[0]
      break

  urllib.request.urlretrieve(uri2,"{}{}.png".format(main_path, i + ' Code'))
  urllib.request.urlretrieve(image_links2, "{}{}.jpeg".format(main_path, i + ' Image'))

  print(duration_ms2)
  input('Press ENTER to exit')


    













