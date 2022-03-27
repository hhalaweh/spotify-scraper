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
  
# Reading orders csv file
orders = pd.read_csv(csv_path, encoding = 'utf-8-sig')

# Creating dataframe with scraped data
cols = ['image_links', 'uri', 'duration_ms']
api_results = pd.DataFrame(columns = cols)

# Extracting data from spotify API
image_links = []
uri = []
duration_ms = []
songs = list(orders['Artist Name'].dropna() + ' ' + orders['Song Name'].dropna())

for song in songs:
    search_result = str(spotify_obj.search(song)) # Search for song and return JSON
    uri_search = re.search("'type': 'track', 'uri': '(.*)'}], 'limit': 1", search_result) # Extract song URI
    duration_search = re.search("'duration_ms': (.*), 'explicit':", search_result) # Extract song duration
    image_regex = re.compile('((https?):((//)|(\\\\))+([\w\d:#@%/;$()~_?\+-=\\\.&](#!)?)*)', re.DOTALL) # Extract song image link
    images = re.findall(image_regex, search_result)
    uri.append(uri_search.group(1))
    duration_ms.append(duration_search.group(1))
    for img in images:
      if img[0][8] == 'i':
        image_links.append(img[0])
        break
    print(song)

# Converting data to a result dataframe used in Photoshop
cols = ['Song Name', 'Artist Name', 'Image Link', 'URI', 'Duration (ms)']
temp_dict = {'Artist Name' : orders['Artist Name'].dropna(), 'Song Name' : orders['Song Name'].dropna(), 'Image Link' : image_links, 'URI' : uri, 'Duration (ms)' : duration_ms}
result_df = pd.DataFrame(temp_dict)
result_df['Spotify Code Link'] = list(map(lambda x: "https://scannables.scdn.co/uri/plain/png/ffffff/black/640/{}".format(x), result_df['URI']))
result_df['Min:Sec'] = list(map(convertMillis, result_df['Duration (ms)']))
result_df['Combination'] = list(orders['Artist Name'].dropna() + ' ' + orders['Song Name'].dropna())
result_df = result_df[['Artist Name', 'Song Name','Image Link', 'Spotify Code Link', 'Min:Sec', 'Combination']]

# Downloading images from links and saving them to a folder
try:
  os.mkdir(f'{main_path}Images')
  os.mkdir(f'{main_path}Excel Files')
except:
  pass

for index, row in result_df.iterrows():
  urllib.request.urlretrieve(row['Spotify Code Link'],"{}Images/{}.png".format(main_path, row['Combination'] + ' Code')) # Save spotify code image
  urllib.request.urlretrieve(row['Image Link'], "{}Images/{}.jpeg".format(main_path, row['Combination'] + ' Image')) # Save spotify album image

# Creating a new csv file with general information  
cols = ['Customer Name', 'Size', 'Song Name', 'Artist Name', 'Timestamp.1', 'Custom Photo', 'Text Color', 'Custom Quote', 'Extra Information (optional)']
design = orders[cols]
design['Min:Sec'] = result_df['Min:Sec'].to_numpy()
reorder = ['Customer Name', 'Size', 'Song Name', 'Artist Name', 'Timestamp.1', 'Min:Sec', 'Custom Photo', 'Text Color', 'Custom Quote', 'Extra Information (optional)']
design = design[reorder] # Reorder columns

design.to_csv(f'{main_path}Excel Files/design.csv', encoding = 'utf-8-sig') # Save design csv file

# Creating csv files used in Photoshop from the dataframe
grouped = design.groupby(design['Size'])
design['Image'] = list(map(lambda x: r"{}Images\{}".format(main_path_backslash, x), design['Artist Name'] + ' ' + design['Song Name'] + ' ' + 'Image' + '.jpeg'))
design['CodeImage'] = list(map(lambda x: r"{}Images\{}".format(main_path_backslash, x), design['Artist Name'] + ' ' + design['Song Name'] + ' ' + 'Code' + '.png'))
cols = ['Song Name', 'Artist Name', 'Timestamp.1', 'Min:Sec', 'Image', 'CodeImage', 'Size']
photoshop_input = design[cols]
photoshop_input.columns = ['SongName', 'ArtistName', 'Timestamp1', 'Timestamp2', 'Image', 'CodeImage', 'Size']
grouped = photoshop_input.groupby(photoshop_input['Size'])

try:
  a4 = grouped.get_group('A4')
  del a4['Size']
  a4.to_csv(f'{main_path}Excel Files/a4.csv', index = False, encoding = 'utf-8-sig')
  os.mkdir(f'{main_path}A4')
except:
  print("A4 not found.")

try:
  a5 = grouped.get_group('A5')
  del a5['Size']
  a5.to_csv(f'{main_path}Excel Files/a5.csv', index = False, encoding = 'utf-8-sig')
  os.mkdir(f'{main_path}A5')
except:
  print("A5 not found.")

try:
  a3 = grouped.get_group('A3')
  del a3['Size']
  a3.to_csv(f'{main_path}Excel Files/a3.csv', index = False, encoding = 'utf-8-sig')
  os.mkdir(f'{main_path}A3')
except:
  print("A3 not found.")

try:
  ck = grouped.get_group('CK')
  ck = ck['CodeImage']
  ck.to_csv(f'{main_path}Excel Files/ck.csv', index = False, encoding='utf-8-sig')
  os.mkdir(f'{main_path}CK')
except:
  print("CK not found.")

try:
  pk = grouped.get_group('PK')
  del pk['Size']
  pk.to_csv(f'{main_path}Excel Files/pk.csv', index = False, encoding = 'utf-8-sig')
  os.mkdir(f'{main_path}PK')
except:
  print("PK not found.")






    













