import utils.session as sess
from plugins.db import db_get_raw
from utils import prowlpy
from myflexget import app_folder

import pickle
from datetime import date, timedelta, datetime
import time
import subprocess
import os


'''
Here we use our own database functions,
as these functions may be called from the scheduler,
outside of application context.
'''


def query(db, query, parse=False):
    cur = db.execute(query)
    result = cur.fetchall()
    cur.close()

    if parse:
        settings = {}
        for x in result:
            settings[x['key']] = x['value']
        return settings
    return result


def flexget(runnow=False):
    print('Running flexget!')
    db = db_get_raw()
    settings = query(db, 'select * from settings_new where id="flexget"', parse=True)
    if not 'flexget' in settings:
        print('ERROR: Cannot find flexget path!')
        db.close()
        return
    devnull = open(os.devnull, 'w')
    subprocess.Popen([settings['flexget'], '-c', os.path.join(app_folder, 'tmp', 'testconfig.yml'), '-L', 'verbose', '--cron', 'execute', '-v'],
                     stdout=devnull, stderr=devnull, close_fds=True)
    devnull.close()
    if not runnow and sess.mysched is not None and len(sess.mysched.get_jobs()) == 1 and 'email' in settings:  # Last call ?!
        time.sleep(60)  # allow flexget to do its thing
        show_list = sess.myep.get_dayShows('today')
        ignore_list = [s[0] for s in query(db, 'select name from shows where ignore="1"')]
        missing_shows = ""
        for show in show_list:
            if show['aquired'] or show['showname'] in ignore_list:
                continue
            missing_shows += '- ' + show['showname'] + '\n'
        if missing_shows:
            missing_shows = "Missing Shows:\n" + missing_shows
        else:
            missing_shows = "All shows downloaded :)\n"
        msg = 'echo "Scheduler Done...\n\n ' + missing_shows + '" | mailx -s "MyFlexget" %s' % settings['email']
        print('Sending "scheduler done"  mail!')
        subprocess.Popen(msg, shell=True, close_fds=True)
    db.close()


def generateyml(day='tomorrow', sched=True, notify=True):
    show_list = sess.myep.get_dayShows(day=day)
    new_shows = 0
    prowl_extra = ''

    db = db_get_raw()
    settings = query(db, 'select * from settings_new where id="flexget"', parse=True)
    schedule = query(db, 'select * from settings_new where id="schedule"', parse=True)

    if not 'rss' in settings or\
       not 'flexget' in settings or\
       not 'path' in settings or\
       not 'start' in schedule or\
       not 'end' in schedule:
            print('ERROR: generateyml: missing settings')
            db.close()
            return

    prowl = prowlpy.Prowl(settings['p_api']) if 'p_api' in settings else None

    if len(show_list) > 0:
        feed_names = {s['name']: s['feed_name'] for s in query(db, 'select name, feed_name from shows order by name')}
        ig_shows = [ss[0] for ss in query(db, 'select name from shows where ignore="1"')]
        prowl_msg = ''
        shows = []
        first_show = 25  # invalid value, will be overwritten
        last_show = -1   # ---------------||----------------
        for show in show_list:
            if not show['aquired'] and show['showname'] not in ig_shows:
                shows.append(show['showname'])
                if 'previous' not in show:
                    new_shows += 1
                    prowl_msg += '- ' + show['showname'] + '\n'
                    airing = int(show['time'][:2])
                    first_show = airing if first_show > airing else first_show
                    last_show = airing if last_show < airing else last_show
                else:
                    prowl_extra += '- ' + show['showname'] + '\n'
            #Rename shows in show_list to match feed_names, show_list is dumped to pickle later:
            show['showname'] = show['showname'] if not show['showname'] in feed_names else feed_names[show['showname']]

        #
        # Problem with UTF-8 characters !?  :
        #
        hq_shows = [sss[0] for sss in query(db, 'select name from shows where hq="1"')]    # high quality shows
        hq_shows = set(shows).intersection(hq_shows)                                  # --------||--------
        dq_shows = list(set(shows)-set(hq_shows))                                     # Default quality shows

        #Done with database:
        db.close()

        #Rename shows to feed_names:
        hq_shows = [x if not x in feed_names else feed_names[x] for x in hq_shows]
        dq_shows = [x if not x in feed_names else feed_names[x] for x in dq_shows]

        #Dump list WITH feed_names
        cur_dir = os.path.dirname(os.path.abspath(__file__))
        pickle.dump(show_list, open(os.path.join(cur_dir, 'shows.pickle'), 'wb'))

        f = open(os.path.join(app_folder, 'tmp', 'testconfig.yml'), 'w')

        f.write('tasks:\n')
        f.write('  feed1:\n')
        f.write('    verify_ssl_certificates: no\n')
        f.write('    inputs:\n')
        for feed in settings['rss'].split(';'):
            f.write('      - rss: ' + feed + '\n')
        f.write('    series:\n')
        if dq_shows:
            f.write('      ' + settings['dq'] + ':\n')
            for show in dq_shows:
                f.write('        - "' + show + '"\n')
        if hq_shows and 'hq' in settings:
            f.write('      ' + settings['hq'] + ':\n')
            for show in hq_shows:
                f.write('        - "' + show + '"\n')
        #f.write('    download: ' + settings['path'] + '\n')
        if 'script_exec' in settings:
            f.write('    exec: ' + settings['script_exec'] + '\n')

        f.close()

        if sched and sess.mysched is not None:
            if not new_shows:
                print('No new shows, no scheduler')
                return True
            f_start = first_show + int(schedule['start'])
            f_end = last_show + int(schedule['start']) + int(schedule['end'])
            #if f_start > 23 or f_end > 23: # crossing midnight
            #    start = f_start if f_start < 24 else (f_start - 24)
            #    end   = f_end   if f_end   < 24 else (f_end   - 24)
            tomorrow = date.today() + timedelta(1)
            if day == 'today':
                tomorrow = date.today()
                if f_end <= datetime.now().hour:
                    print('Scheduler would never be runned')
                    return
            elif day == 'yesterday':
                print('Scheduler would never be runned')
                return
            sess.mysched.add_job(flexget, 'cron', year=tomorrow.year, month=tomorrow.month, day=tomorrow.day, hour=str(f_start)+'-'+str(f_end))

    if new_shows == 0:
        prowl_msg = 'No new episodes today  :('

    if sched and notify:
        try:
            if prowl is not None:
                prowl.add('Python', 'TV shows ('+str(new_shows)+')', prowl_msg, -2)
        except Exception as e:
            print(e)
        if 'email' in settings:
            msg = prowl_msg
            if prowl_extra:
                msg += "\n\nStill looking for:\n"+prowl_extra
            msg = 'echo "'+msg+'" | mailx -s "Todays episodes '+str(new_shows)+'" '+settings['email']
            print('Sending sched mail!')
            subprocess.Popen(msg, shell=True, close_fds=True)
    return True
