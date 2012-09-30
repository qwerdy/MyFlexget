import os
import sys
import web
import threading
from apscheduler.scheduler import Scheduler
import subprocess

import model
import functions
from myepisodes import Myepisodes




#########################################
### Debug log
#########################################
class MyOutput():
    def __init__(self, logfile):
        self.log = open(logfile, 'w')
 
    def write(self, text):
        self.log.write(text)
        self.log.flush()
 
    def close(self):
        self.log.close()

sys.stdout = MyOutput('tmp/myflexget.txt')
#########################################


render = web.template.render('templates/')

myep = None  #Holder for Myepisode instance
sched = None #Holder for scheduler

def look_for_shows(day = ''):
    global atestvar, myep, sched
    if myep and myep.logged_in():
        print('Fetching shows and generating config file!')
        functions.generateyml(myep, sched, day=day)
    else:
        print('Could not fetch shows, not logged in!')


urls = (
    "/", "home",
    "/home", "home",
    "/shows", "shows",
    "/settings", "settings",
    "/ajax", "ajax"
)
app = web.application(urls, globals())

class home:
    def GET(self):

        global atestvar, myep, sched

        param = web.input(t=None,u=None)
        if param.t == 'start':
            if not myep:
                creds = model.get_credentials()
                username = ''
                password = ''
                for cred in creds:
                    username = cred.myusername
                    password = cred.mypassword
                myep = Myepisodes(username, password)
                if myep.logged_in():
                    sched = Scheduler()
                    sched.start()
                    sched.add_cron_job(look_for_shows, hour='23', minute='20')
                    print('Schedule added')
                    raise web.seeother('')
                else:
                    myep = None
                    return render.layout(render.main_home('failed'), render.leftbar_home(False))
            raise web.seeother('')
        elif not myep or not myep.logged_in():
            return render.layout(render.main_home('false'), render.leftbar_home(False))
        elif param.t == 'stop':
            myep = None
            sched.shutdown()
            sched = None
            return render.layout(render.main_home('false'), render.leftbar_home(False))
        elif param.t == 'nextshows':
            shows = myep.get_dayShows()
            return render.layout(render.main_home('true', shows), render.leftbar_home(True))
        elif param.t == 'runnow':
            print('Running flexget manually!')
            functions.flexget()
            raise web.seeother('')
        elif param.t == 'config':
            if param.u == 'new':
                print('Regenarting config file(tomorrow), demanded by user!')
                functions.generateyml(myep)
            elif param.u == 'newtoday':
                print('Regenarting config file(today), demanded by user!')
                functions.generateyml(myep, day='today')
            elif param.u == 'newyesterday':
                print('Regenarting config file(yesterday), demanded by user!')
                functions.generateyml(myep, day='yesterday')
            elif param.u == 'newsched':
                print('Regenarting config file & schedules, demanded by user!')
                look_for_shows()
            elif param.u == 'newschedtoday':
                print('Regenarting config file & schedules(today), demanded by user!')
                look_for_shows('today')
            if os.path.isfile('tmp/testconfig.yml'):
                f = open ('tmp/testconfig.yml', 'r')
                content = f.read()
                f.close()
            else:
                content = ''
            return render.layout(render.main_home('generated', fileout=content), render.leftbar_home(True))
        elif param.t == 'logfile':
            if os.path.isfile('tmp/myflexget.txt'):
                f = open ('tmp/myflexget.txt', 'r')
                content = f.read()
                f.close()
            else:
                content = ''
            return render.layout(render.main_home('logfile', fileout=content), render.leftbar_home(True))
        elif param.t == 'logfile2':
            if os.path.isfile('tmp/flexget.log'):
                f = open('tmp/flexget.log', 'r')
                content = f.read()
                f.close()
            else:
                content = ''
            return render.layout(render.main_home('logfile', fileout=content), render.leftbar_home(True))
        else:
            jobs = sched.get_jobs()
            return render.layout(render.main_home('true', jobs=jobs), render.leftbar_home(True))

class shows:

    def POST(self):
        params = web.input(id='', name='', feed_name='', hq=None, ignore=None)
        hq = '0' if params.hq == None else '1'
        ignore = '0' if params.ignore == None else '1'
        if params.name == '':
            raise web.seeother('shows?s=new')
        elif params.id != '':
            model.update_show(params.id, params.name, params.feed_name, hq, ignore)
        else:
            model.new_show(params.name, params.feed_name, hq, ignore)
        raise web.seeother('shows')

    def GET(self):
        params = web.input(s=None, n=None)

        if params.s != 'delete':
            shows = model.get_shows()

        if params.s == 'new':
            return render.layout(render.main_shows(), render.leftbar_shows(shows, web.urlquote))
        elif params.s == 'delete' and params.id != None:
            model.delete_show(params.id)
            shows = model.get_shows()
            return render.layout(render.main_shows(True, id=params.id), render.leftbar_shows(shows, web.urlquote))
        elif params.s ==  'update' and params.n != None:
            show = model.get_show(params.n)
            result = False
            for row in show:
                result = True
                hq = 'checked' if row.hq == 1 else ''
                ignore = 'checked' if row.ignore == 1 else ''
                return render.layout(render.main_shows(name=row.name, feed_name=row.feed_name, hq=hq, ignore=ignore, id=row.id), render.leftbar_shows(shows, web.urlquote))
            if not result:
                return render.layout(render.main_shows(shows=False), render.leftbar_shows(shows, web.urlquote))
        else:
            return render.layout(render.main_shows(), render.leftbar_shows(shows, web.urlquote))

class settings:

    def POST(self):
        params = web.input(s=None)
        if params.s == "flexget":
            params = web.input(
                email = '',
                rss = '',
                flexget = '',
                path = '',
                dq = 'hdtv',
                hq = '720p',
                lm = 0,
            )

            if params.rss == '' or params.flexget == '' or params.path == '':
                return render.layout(render.main_settings_flexget('empty', params.email, params.rss, params.flexget, params.path, params.dq, params.hq, params.lm), render.leftbar_settings())
            else:
                error = functions.check_settings(params.flexget, params.path)
                model.set_settings(params.email, params.rss, params.flexget, params.path, params.dq, params.hq, params.lm)
                return render.layout(render.main_settings_flexget('saved', params.email, params.rss, params.flexget, params.path, params.dq, params.hq, params.lm, error), render.leftbar_settings())
        elif params.s == 'myepisodes':
            params = web.input(
                myusername = '',
                mypassword = '',
            )
            
            if params.myusername == '' or params.mypassword == '':
                return render.layout(render.main_settings_credentials('empty', params.myusername, params.mypassword), render.leftbar_settings())
            else:
                model.set_credentials(params.myusername, params.mypassword)
                return render.layout(render.main_settings_credentials('saved', params.myusername, params.mypassword), render.leftbar_settings())
        elif params.s == 'general':
            p = web.input(start = 1, end = 8)
            #need some extra validation .....
            start = int(p.start) if p.start != '' else 1
            end   = int(p.end)   if p.end   != '' else 8
            start = start if start < 24 and start >= 0  else 1
            end   = end   if end   < 24 and end > start else 8
            model.set_times(start, end)
            return render.layout(render.main_settings_general('saved', start, end), render.leftbar_settings())

    def GET(self):
        params = web.input(s=None)
        main = ''

        if params.s == None or params.s == "flexget":
            settings = model.get_settings()
            for s in settings:
                error = functions.check_settings(s.flexget, s.downloadpath)
                return render.layout(render.main_settings_flexget('get', s.email, s.rssfeed, s.flexget, s.downloadpath, s.def_quality, s.high_quality, s.limit_number, error), render.leftbar_settings())
        elif params.s == "myepisodes":
            creds = model.get_credentials()
            username = ''
            password = ''
            for row in creds:
                username = row.myusername
                password = row.mypassword
            return render.layout(render.main_settings_credentials('get', username, password), render.leftbar_settings())
        elif params.s == 'general':
            result = model.get_times()
            start = 1
            end   = 8
            for time in result:
                start = time.fetch_start
                end   = time.fetch_end
            return render.layout(render.main_settings_general('get', start, end), render.leftbar_settings())

class ajax:
    global myep
    def GET(self):
        output = ''
        get = web.input(q=None)
        if get.q == 'showlist':
            if not myep or not myep.logged_in():
                return render.ajax_shows(auth=False)
            else:
                shows = myep.get_myShows()
                return render.ajax_shows(shows)

if __name__ == "__main__":
    app.run()
