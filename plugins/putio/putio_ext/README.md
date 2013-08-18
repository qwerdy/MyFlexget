putio
=====

Put.io downloader


This repo contains an python api-wrapper for put.io, and a download script for torrents/magnet-links.
The download script will start downloads on put.io, download the content, and then remove it from put.io.

######Usage: 
* putio_download.py (somefile.torrent | magnet-link) {(show-name show-season show-episode) | movie-title} {folder-id}

######eg:
* putio_download.py "http://example.com/show.torrent" "A fancy show" 3 14
* putio_download.py "magnet:?xt=urn:btih:0hb59ba3ce546e169b13ff7c6" "Awesome movie title"




I use this together with flexget to automatically download shows.



####Variables you should change in putio_download.py

    TOKEN = 'yourtokenhere'
    
    WORK_DIR = '/tmp/put.io'
    SHOW_DIR = '/tmp/download/serier'
    MOVIE_DIR = '/tmp/download/filmer'
    GENERIC_DIR = '/tmp/download'
    
    LOG_FILE = '/tmp/put.io/putio.log'
