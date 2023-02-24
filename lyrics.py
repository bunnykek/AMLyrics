import argparse
import requests
import bs4
import json
import re
import os

REGEX = re.compile("https://music.apple.com/(\w{2})/album/.+?/(\d+)(\?i=(\d+))?")

with open("config.json") as f:
    config = json.load(f)

    AUTH_BEARER = config['auth_bearer']
    TOKEN = config['media-user-token']
    SYNCED = config['synced_lyrics']
    PLAIN = config['plain_lyrics']
    LYRIC_PATH = config['lyric_file_path']


HEADERS = {
    "authorization": AUTH_BEARER,
    "media-user-token": TOKEN,
    "Origin": "https://music.apple.com",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:95.0) Gecko/20100101 Firefox/95.0",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://music.apple.com/",
    "content-type": "application/json",
    "x-apple-renewal": "true",
    "DNT": "1",
    "Connection": "keep-alive",
    'l': 'en-US'
}

def zpad(val, n):
    bits = val.split('.')
    return "%s.%s" % (bits[0].zfill(n), bits[1])

class Lyrics:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def getAlbumLyric(self, albumid: str, region: str):
        print("Getting lyrics for the whole album...")
        metadata = self.session.get(f"https://api.music.apple.com/v1/catalog/{region}/albums/{albumid}").json()
        metadata = metadata['data'][0]
        
        album = metadata['attributes']['name']
        year = metadata['attributes']['releaseDate'][0:4]
        artist = metadata['attributes']['artistName']

        for track in metadata['relationships']['tracks']['data']:
            self.getTrackLyric(track['id'], region, album, artist, year)


    def getTrackLyric(self, trackID: str, region: str, album= None, artist= None, year= None):
        response = self.session.get(f'https://amp-api.music.apple.com/v1/catalog/{region}/songs/{trackID}/lyrics')
        result = response.json()
        soup =  bs4.BeautifulSoup(result['data'][0]['attributes']['ttml'], 'lxml')
        metadata = self.session.get(f"https://api.music.apple.com/v1/catalog/{region}/songs/{trackID}").json()
        metadata = metadata['data'][0]
        

        title = metadata['attributes']['name']
        trackNo = metadata['attributes']['trackNumber']

        if not album and not artist and not year:
            artist = metadata['attributes']['artistName']
            album = metadata['attributes']['albumName']
            year = metadata['attributes']['releaseDate'][0:4]

        plain_lyric = f"Title: {title}\nAlbum: {album}\nArtist: {artist}\n\n"
        synced_lyric = f"[ti:{title}]\n[ar:{artist}]\n[al:{album}]\n\n"
        paragraphs = soup.find_all("p")

        if 'itunes:timing="None"' in result['data'][0]['attributes']['ttml']:
            synced_lyric = None
            for line in paragraphs:
                plain_lyric += line.text+'\n'

        else:
            for paragraph in paragraphs:
                begin = paragraph.get('begin')
                splits = begin.split(':')
                millisec = zpad(splits[-1], 2)
                minutes = '00'
                try:
                    minutes = splits[-2].zfill(2)
                except:
                    pass
                timeStamp = minutes+":"+millisec
                text = paragraph.text
                plain_lyric += text+'\n'
                synced_lyric += f'[{timeStamp}]{text}\n'
        
        lyric_path = LYRIC_PATH.format(title=title, artist=artist, album=album, trackNo=str(trackNo), year=year)

        if not os.path.exists('/'.join(lyric_path.split('/')[:-1])):
            os.makedirs('/'.join(lyric_path.split('/')[:-1]))

        if SYNCED:
            with open(lyric_path+'.lrc', "w+") as f:
                f.write(synced_lyric)
        if PLAIN:
            with open(lyric_path+'.txt', 'w+') as f:
                f.write(plain_lyric)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Apple Music lyrics module.")
    parser.add_argument('URL', help="Album or track URL")
    args = parser.parse_args()
    url = args.URL
    region, albumid, trackFlag, trackid = REGEX.search(url).groups()
    am = Lyrics()
    
    if trackFlag:
        am.getTrackLyric(trackid, region)
    
    else:
        am.getAlbumLyric(albumid, region)