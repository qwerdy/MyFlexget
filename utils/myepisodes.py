import os
import urllib
import urllib2
import cookielib
import pickle
from HTMLParser import HTMLParser
from datetime import date, timedelta

cur_dir = os.path.dirname(os.path.abspath(__file__))


class Myepisodes(object):
    def __init__(self, username, password):
        self.url = "http://www.myepisodes.com/login.php"
        self.values = {'username': username, 'password': password, 'action': 'Login', 'u': ''}
        self.data = urllib.urlencode(self.values)
        self.cookiefile = os.path.join(cur_dir, 'myepisodes.cookie')
        self.cj = cookielib.LWPCookieJar()
        self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cj))
        self.loggedIn = False
        self.login()

    #def __del__(self):
    #    print('Myepisodes: __del__')

    def login(self, force=False):
        if not force and os.path.isfile(self.cookiefile):
            self.cj.load(self.cookiefile)
            self.loggedIn = True
            #print 'Myepisodes: Loaded cookie'
        else:
            self.response = self.opener.open(self.url, self.data)
            self.loggedIn = self.response.read().find('(Logout)') > 0
            if self.loggedIn:
                self.cj.save(self.cookiefile)
                #print 'Myepisodes: Login'

    def logged_in(self):
        return self.loggedIn

    def get_myShows(self):
        url = 'http://www.myepisodes.com/shows.php?type=manage'
        response = self.opener.open(url).read().replace("&", "_amp;_")
        if response.find('(Logout)') < 0:   # Not logged in?
            self.login(True)                # Try to log in
            if not self.loggedIn:           # If login itself failed, return None
                return None
            else:
                response = self.opener.open(url).read()  # If logged successfully, try get list
                if response.find('(Logout)') < 0:        # If we are not logged in now, give up!
                    return None
        parser = Scrape_myShows()
        parser.feed(response)
        parser.close
        return parser.get_shows()

    def get_dayShows(self, day='tomorrow'):
        url = 'http://www.myepisodes.com/views.php'
        response = self.opener.open(url).read().replace("&", "_amp;_")  # Something doesnt like the ampersign
        if response.find('(Logout)') < 0:
            self.login(True)
            if not self.loggedIn:
                return None
            else:
                response = self.opener.open(url).read()
                if response.find('(Logout)') < 0:
                    return None
        parser = Scrape_dayShows(day)
        parser.feed(response)
        parser.close

        return parser.get_shows()

    def set_aquired(self, aq_show, aq_season, aq_episode):
        cur_dir = os.path.dirname(os.path.abspath(__file__))
        if not os.path.isfile(os.path.join(cur_dir, 'shows.pickle')) or not aq_show.strip():
            return False
        shows = pickle.load(open(os.path.join(cur_dir, 'shows.pickle'), 'r'))
        show_id = None
        show_uniqe = None
        if aq_season and aq_episode:
            aq_season = str(aq_season)
            aq_episode = str(aq_episode)
            show_uniqe = '%sx%s' % (aq_season.zfill(2), aq_episode.zfill(2))
        for show in shows:
            if show['showname'].lower() == aq_show.lower():
                show_id = show['id']
                #if exact episode match, break. If no exact match is found, last name match is used.
                if show_uniqe and show['number'] == show_uniqe:
                    break
        if show_id is None:
            return False
        url = 'http://www.myepisodes.com/views.php?type=save'
        values = {'action': 'Save Status', show_id: 'on', 'checkboxes': show_id[1:]}
        data = urllib.urlencode(values)
        self.opener.open(url, data)
        return True


class Scrape_dayShows(HTMLParser):

    def __init__(self, day='tomorrow'):
        HTMLParser.__init__(self)
        if day == 'today':
            theDay = date.today()
        elif day == 'yesterday':
            theDay = date.today() - timedelta(1)
        else:
            theDay = date.today() + timedelta(1)

        self.in_episode = False
        self.in_date = False
        self.in_dateA = False
        self.in_validep = False
        self.in_showname = False
        self.in_number = False
        self.date_format = "%d-%b-%Y"
        self.shows = []
        self.buffshow = {}

        one_day_ago = (theDay - timedelta(1)).strftime(self.date_format)
        two_day_ago = (theDay - timedelta(2)).strftime(self.date_format)
        three_day_ago = (theDay - timedelta(3)).strftime(self.date_format)
        four_day_ago = (theDay - timedelta(4)).strftime(self.date_format)

        theDay = theDay.strftime(self.date_format)
        self.previous_lookup = [theDay, one_day_ago, two_day_ago, three_day_ago, four_day_ago]

    #def __del__(self):
    #    print('Scrape_dayShows: __del__')

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        try:
            if attrs['class'].find('Episode_') == 0:
                self.in_episode = True
        except:
            pass

        if self.in_episode:
            if self.in_date and tag == 'a':
                self.in_dateA = True
            if tag == 'input' and self.in_validep and attrs['id'].find('A') == 0:
                self.buffshow['id'] = attrs['id']
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
        if self.in_dateA and data in self.previous_lookup:
            self.in_validep = True
            self.buffshow['date'] = data.strip()
            if data in self.previous_lookup[1:]:
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
