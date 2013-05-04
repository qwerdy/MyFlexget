import os
from   datetime   import date, timedelta, datetime
import time
import subprocess
import pickle

import shared
import prowlpy
import model

fg_path = '/usr/local/bin/flexget' # default flexget path

def flexget():
    global fg_path
    print('Running flexget!')
    devnull = open(os.devnull, 'w')
    flexget = subprocess.Popen([fg_path, '-c', os.path.dirname(__file__) + '/tmp/testconfig.yml'], stdout=devnull, stderr=devnull)
    devnull.close()
    if shared.sched is not None and len(shared.sched.get_jobs()) == 1:
        time.sleep(60) #allow flexget to do its thing
        show_list = shared.myep.get_dayShows('today')
        ignore_list = model.get_ignored_shows_list()
        missing_shows = ""
        for show in show_list:
            if show['aquired'] or show['showname'] in ignore_list:
                continue
            missing_shows += '- ' + show['showname'] + '\n'
        if missing_shows:
            missing_shows = "Missing Shows:\n" + missing_shows
        else:
            missing_shows = "All shows downloaded :)\n"
        msg = 'echo "Scheduler Done...\n\n ' + missing_shows  + '" | mailx -s "MyFlexget" torrent@ymze.com'
        print 'Sending "scheduler done"  mail!'
        subprocess.Popen(msg, shell=True)

def generateyml(day='',sched=True):
    global fg_path
    show_list = shared.myep.get_dayShows(day=day)
    new_shows = 0
    prowl_extra = ''

    settings = model.get_settings()
    for s in settings:
        dq   = s.def_quality
        hq   = s.high_quality
        rss  = s.rssfeed
        path = s.downloadpath
        start = s.fetch_start
        end   = s.fetch_end
        mail_addr = s.email
        fg_path = s.flexget
        prowl_api = s.prowl_api

    prowl = prowlpy.Prowl(prowl_api) if prowl_api else None

    if len(show_list) > 0:
        feed_names = model.get_shows_dir()
        ig_shows = model.get_ignored_shows_list()  
        prowl_msg = ''
        shows = []
        first_show = 25 #invalid value, will be overwritten
        last_show  = -1 # ---------------||----------------
        for show in show_list:
            if show['aquired'] == False and show['showname'] not in ig_shows:
                shows.append(show['showname'])
                if 'previous' not in show:
                    new_shows += 1
                    prowl_msg += '- '+ show['showname'] +'\n'
                    airing = int(show['time'][:2])
                    first_show = airing if first_show > airing else first_show
                    last_show  = airing if last_show  < airing else last_show
                else:
                    prowl_extra += '- '+ show['showname'] +'\n'
            #Rename shows in show_list to match feed_names, show_list is dumped to pickle later:
            show['showname'] = show['showname'] if not show['showname'] in feed_names else feed_names[show['showname']]


        #
        # Problem with UTF-8 characters !?  :
        #
        hq_shows = model.get_hq_shows_list()                                 #high quality shows
        hq_shows = set(shows).intersection(hq_shows)                         #--------||--------
        dq_shows = list(set(shows)-set(hq_shows))                            #Default quality shows

        #Rename shows to feed_names:
        hq_shows = [x if not x in feed_names else feed_names[x] for x in hq_shows]
        dq_shows = [x if not x in feed_names else feed_names[x] for x in dq_shows]

        pickle.dump(show_list, open('tmp/shows.pickle', 'wb'))                   #Dump list WITH feed_names
 
        script = os.path.dirname(__file__) + '/setaquired.py "%(series_name)s" "%(series_season)s" "%(series_episode)s"'

        f = open('tmp/testconfig.yml', 'w')
        
        f.write('tasks:\n')
        f.write('  feed1:\n')
        f.write('    inputs:\n')
        for feed in rss.split(';'):
            f.write('      - rss: '+ feed +'\n')
        f.write('    series:\n')
        f.write('      '+ dq +':\n')
        for show in dq_shows:
            f.write('        - '+ show +'\n')
        for show in hq_shows:
            f.write('        - '+ show +':\n')
            #f.write('            timeframe: x hours\n')
            f.write('            quality: '+ hq  +'\n')
        f.write('    download: '+ path + '\n')
        f.write('    exec: '+ script  +'\n')
    
        f.close()
        
        if sched and shared.sched is not None and new_shows:
            f_start = first_show + start
            f_end   = last_show  + start + end
            #if f_start > 23 or f_end > 23: # crossing midnight
            #    start = f_start if f_start < 24 else (f_start - 24)
            #    end   = f_end   if f_end   < 24 else (f_end   - 24)
            tomorrow = date.today() + timedelta(1)
            if day == 'today':
                tomorrow = date.today()
                if f_end <= datetime.now().hour:
                    print 'Scheduler would never be runned'
                    return
            elif day == 'yesterday':
                print 'Scheduler would never be runned'
                return
            shared.sched.add_cron_job(flexget, year=tomorrow.year, month=tomorrow.month, day=tomorrow.day, hour=str(f_start)+'-'+str(f_end))

    if new_shows == 0:
        prowl_msg = 'No new episodes today  :('

    if sched:
        try:
            if prowl is not None:
                prowl.add('Python', 'TV shows ('+str(new_shows)+')', prowl_msg, -2)
        except Exception, msg:
            print(msg)
        if mail_addr:
            msg = prowl_msg
            if prowl_extra:
                msg += "\n\nStill looking for:\n"+prowl_extra
            msg = 'echo "'+msg+'" | mailx -s "Todays episodes '+str(new_shows)+'" '+mail_addr
            print 'Sending sched mail!'
            subprocess.Popen(msg, shell=True)

def check_settings(flexget, path):
    error = []
    if not os.access(flexget, os.R_OK):
        error.append('Flexget: could not access: '+flexget)
    if not os.access(path[0:path.find('{')], os.W_OK): #stop if match flexget pattern
        error.append('Download Path: is not writable: '+path)
    if not os.access('tmp/', os.W_OK):
        error.append('Tmp: tmp/ is not writable')