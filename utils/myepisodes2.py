import os
import requests
import pickle
from HTMLParser import HTMLParser
from datetime import date, timedelta

cur_dir = os.path.dirname(os.path.abspath(__file__))


class Myepisodes(object):
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.cookiefile = os.path.join(cur_dir, 'myepisodes2.cookie')
        self.cookies = None
        self.loggedIn = False

        self.s = requests.Session()

        # self.data = urllib.urlencode(self.values)
        # self.cj = cookielib.LWPCookieJar()
        # self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cj))

        self.login()

    def login(self, force=False):
        if not force and os.path.isfile(self.cookiefile):
            with open(self.cookiefile, 'rb') as f:
                self.cookies = pickle.load(f)
                self.s.cookies.update(self.cookies)
            self.loggedIn = True
            print 'Myepisodes: Loaded cookie'
        else:
            url = 'http://www.myepisodes.com/login.php'
            params = {'action': 'login'}
            values = {'username': self.username, 'password': self.password, 'action': 'Login', 'u': ''}

            response = self.s.post(url, params=params, data=values)

            self.loggedIn = response.text.find('(Logout)') > 0
            if self.loggedIn:
                self.cookies = self.s.cookies
                self.s.cookies.update(self.cookies)
                with open(self.cookiefile, 'wb') as f:
                    pickle.dump(self.cookies, f)
                print 'Myepisodes: Login'
            else:
                print 'Myepisodes: NOT Login'

    def logged_in(self):
        return self.loggedIn

    def get_myShows(self, try_login=True):
        url = 'http://www.myepisodes.com/myshows/manage/'
        response = self.s.get(url)

        if response.text.find('(Logout)') < 0:   # Not logged in?
            if not try_login:
                return None

            self.login(True)                # Try to log in
            if not self.loggedIn:           # If login itself failed, return None
                return None
            else:
                return self.get_myShows(False)

        parser = Scrape_myShows()
        parser.feed(response.text)
        parser.close
        return parser.get_shows()

    def get_dayShows(self, day='tomorrow', try_login=True):
        url = 'http://www.myepisodes.com/ajax/service.php?mode=view_privatelist'

        values = {'eps_filters[]': [1, 2, 4096]}
        response = self.s.post(url, data=values)
        if response.text.find('<table class="mylist" ') < 0: # ....
            if not try_login:
                return None

            self.login(True)
            if not self.loggedIn:
                return None
            else:
                return self.get_dayShows(day, False)

        parser = Scrape_dayShows(day)
        parser.feed(response.text)
        parser.close

        return parser.get_shows()

    def set_aquired(self, aq_show, aq_season = None, aq_episode = None):
        if aq_season is None and aq_episode is None:
            return self.set_aquired_by_episode_id(aq_show)

        cur_dir = os.path.dirname(os.path.abspath(__file__))
        if not os.path.isfile(os.path.join(cur_dir, 'shows.pickle')) or not aq_show.strip():
            return False
        shows = pickle.load(open(os.path.join(cur_dir, 'shows.pickle'), 'r'))
        episode_id = None
        show_uniqe = None
        if aq_season and aq_episode:
            aq_season = str(aq_season)
            aq_episode = str(aq_episode)
            show_uniqe = '%sx%s' % (aq_season.zfill(2), aq_episode.zfill(2))
        for show in shows:
            if show['showname'].lower() == aq_show.lower():
                episode_id = show['id']
                #if exact episode match, break. If no exact match is found, last name match is used.
                if show_uniqe and show['number'] == show_uniqe:
                    break
        if episode_id is None:
            return False

        return self.set_aquired_by_episode_id('V'+episode_id[1:])


    def set_aquired_by_episode_id(self, episode_id):
        url = 'http://www.myepisodes.com/ajax/service.php?mode=eps_update'
        if not episode_id.startswith('A'):
            episode_id = 'A' + episode_id
        values = {episode_id: 'true'}
        response = self.s.post(url, data=values)

        return response

    def set_watched(self, episode_id):
        url = 'http://www.myepisodes.com/ajax/service.php?mode=eps_update'
        if not episode_id.startswith('V'):
            episode_id = 'V' + episode_id
        values = {episode_id: 'true'}
        response = self.s.post(url, data=values)

        return response


class Scrape_dayShows(HTMLParser):

    def __init__(self, day='tomorrow'):
        HTMLParser.__init__(self)
        if day == 'today':
            self.theDay = date.today()
        elif day == 'yesterday':
            self.theDay = date.today() - timedelta(1)
        elif day == 'tomorrow':
            self.theDay = date.today() + timedelta(1)
        else:
            self.theDay = None

        self.in_episode = False
        self.in_date = False
        self.in_dateA = False
        self.in_validep = False
        self.in_showname = False
        self.in_number = False
        self.date_format = "%d-%b-%Y"
        self.shows = []
        self.buffshow = {}

        if self.theDay is not None:
            one_day_ago = (self.theDay - timedelta(1)).strftime(self.date_format)
            two_day_ago = (self.theDay - timedelta(2)).strftime(self.date_format)
            three_day_ago = (self.theDay - timedelta(3)).strftime(self.date_format)
            four_day_ago = (self.theDay - timedelta(4)).strftime(self.date_format)

            self.theDay = self.theDay.strftime(self.date_format)
            self.previous_lookup = [self.theDay, one_day_ago, two_day_ago, three_day_ago, four_day_ago]

    #def __del__(self):
    #    print('Scrape_dayShows: __del__')

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        try:
            if tag == 'tr' and attrs['class'].find('header') < 0:
                self.in_episode = True
        except:
            pass

        if self.in_episode:
            if self.in_date and tag == 'a':
                self.in_dateA = True
            if tag == 'input' and self.in_validep and attrs['name'].find('A') == 0:
                self.buffshow['id'] = attrs['name']
                if 'checked' in attrs:
                    self.buffshow['aquired'] = True
                else:
                    self.buffshow['aquired'] = False

            try:
                if attrs['class'] == 'date':
                    self.in_date = True
                elif attrs['class'] == 'showname':
                    self.in_showname = True
                elif attrs['class'] == 'longnumber':
                    self.in_number = True
            except:
                pass

    def handle_data(self, data):
        if self.in_date:
            self.buffshow['time'] = data
        if self.in_dateA and (self.theDay is None or data in self.previous_lookup):
            self.in_validep = True
            self.buffshow['date'] = data.strip()
            if self.theDay is not None and data in self.previous_lookup[1:]:
                self.buffshow['previous'] = True
        elif self.in_validep:
            if self.in_showname:
                self.buffshow['showname'] = data.replace("_amp;_", "&")
            elif self.in_number:
                self.buffshow['number'] = data

    def handle_endtag(self, tag):
        if self.in_episode and tag == 'tr':
            self.in_episode = False
            if self.in_validep:
                self.shows.append(self.buffshow)
            self.in_validep = False
            self.buffshow = {}
        elif self.in_date and tag == 'td':
            self.in_date = False
            self.in_dateA = False
        elif self.in_showname and tag == 'td':
            self.in_showname = False
        elif self.in_number and tag == 'td':
            self.in_number = False

    def get_shows(self):
        return self.shows


class Scrape_myShows(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.in_select = False
        self.in_option = False
        self.shows = []

    #def __del__(self):
    #    print('Scrape_myShows: __del__')

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'select' and attrs['id'] == 'shows':
            self.in_select = True
        elif self.in_select and tag == 'option':
            self.in_option = True

    def handle_data(self, data):
        if self.in_select and self.in_option:
            self.shows.append(data.replace("_amp;_", "&").strip())

    def handle_endtag(self, tag):
        if tag == 'select':
            self.in_select = False
        if self.in_option:
            self.in_option = False

    def get_shows(self):
        return self.shows
