#!/usr/bin/env python

import sys
from myepisodes import Myepisodes
import model

season = None
episode = None

try:
    show = sys.argv[1]
except:
    sys.exit()

try:
    season = sys.argv[2]
    episode = sys.argv[3]
except:
    pass

creds = model.get_credentials()
username = ''
password = ''

for cred in creds:
    username = cred.myusername
    password = cred.mypassword

myep = Myepisodes(username, password)
if not myep.logged_in():
    sys.exit()

myep.set_aquired(show, season, episode)
