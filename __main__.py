import myflexget


def main():
    myflexget.load_plugins()
    print
    print myflexget.app.url_map
    print
    myflexget.app.debug = True
    myflexget.app.run(host='0.0.0.0', port=8088, reloader_interval=60)

if __name__ == "__main__":
    main()
