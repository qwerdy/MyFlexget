from flask import Flask
import os
import sys

app = Flask(__name__)
app.secret_key = 'randomshitfacereggie'  # os.urandom(24)

app_folder = os.path.dirname(os.path.abspath(__file__))

#Remove whitespace
app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True

_menu = []


#########################################
### Debug log
#########################################
class MyOutput():
    def __init__(self, logfile):
        self.log = open(logfile, 'a')

    def write(self, text):
        self.log.write(text)
        self.log.flush()

    def close(self):
        self.log.close()

sys.stdout = MyOutput(os.path.join(app_folder, 'tmp', 'myflexget.log'))
#########################################


@app.context_processor
def variables():
    return {'menu': _menu}


def load_plugins():
    import plugins
    dir = plugins.__path__[0]

    plugin_names = []
    for file in os.listdir(dir):
        path = os.path.join(dir, file, '__init__.py')
        if os.path.isfile(path):
            plugin_names.append(file)

    for name in plugin_names:
        print('Loading plugin from: %s' % name)
        exec("import plugins.%s" % name)


def register_plugin(plugin, menu=None, order=128):
    print('  Registering plugin: %s' % plugin.name)

    app.register_blueprint(plugin)
    if menu:
        register_menu(plugin.url_prefix, menu, order)


def register_menu(href, caption, order=128):
    global _menu
    print('  Registering menu: %s -> %s' % (caption, href))
    _menu.append({'href': href, 'caption': caption, 'order': order})
    _menu = sorted(_menu, key=lambda m: m['order'])
