import json
import requests
import os,re,random,string
import hashlib
import time
import base64
import asyncio
import urllib
import requests
import re
import shlex
import async_timeout
import mpv
import imp
import json

from aiohttp import web
from io import BytesIO
import logging
_LOGGER = logging.getLogger(__name__)

from aiohttp.web import Request, HTTPUnauthorized
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant.components.http import (
    HomeAssistantView
)
from homeassistant.const import (
    ATTR_ENTITY_ID, HTTP_UNPROCESSABLE_ENTITY
)

SERVICE_PLAY = "play"
SERVICE_STOP = "stop"
SERVICE_TOGGLE = "toggle"
SERVICE_SET_VOLUME = "set_volume"
SERVICE_ADD_VOLUME = "add_volume"
SERVICE_SUB_VOLUME = "sub_volume"
SERVICE_PLAY_TTS = "play_tts"
CONF_MAX_VOLUME = "max_volume"
CONF_APIKEY = 'api_key'
CONF_SECRETKEY = 'secret_key'
CONF_SPEED =  'speed'
CONF_PITCH = 'pitch'
CONF_VOLUME = 'volume'
CONF_PERSON = 'person'
CONF_BASEPATH = "base_path"
CONF_CHANNELS = 'channels'
ATTR_URL = 'url'
ATTR_VOLUME = "volume"
ATTR_MESSAGE = "message"
ATTR_PLATFORM = "entity_id"
DOMAIN = 'broadcast'

SERVICE_PLAY_SCHEMA = vol.Schema({
    vol.Optional(ATTR_URL): cv.string,
    vol.Optional(ATTR_VOLUME): cv.string,
    vol.Optional(ATTR_ENTITY_ID): cv.entity_id,
    })
SERVICE_broadcast_SCHEMA = vol.Schema({
    }) 
SERVICE_SET_VOLUME_SCHEMA = vol.Schema({
    vol.Required(ATTR_VOLUME): cv.string,
    })   
SERVICE_PLAY_TTS_SCHEMA = vol.Schema({
    vol.Required(ATTR_MESSAGE): cv.string,
    vol.Optional(ATTR_VOLUME): cv.string,
    })    

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Optional(CONF_MAX_VOLUME, default = False): cv.boolean,
        vol.Optional(CONF_APIKEY): cv.string,
        vol.Optional(CONF_SECRETKEY): cv.string,
        vol.Optional(CONF_SPEED): cv.string,
        vol.Optional(CONF_PITCH): cv.string,
        vol.Optional(CONF_VOLUME): cv.string,
        vol.Optional(CONF_PERSON): cv.string,
        vol.Optional(CONF_BASEPATH): cv.string,
        vol.Optional(CONF_CHANNELS): vol.All(cv.ensure_list),
        }),
    }, extra=vol.ALLOW_EXTRA)

            
class AudioPlayer:  
        
    def __init__(self, hass, adjust_volume): 
        self._hass = hass
        self._ffplay = None
        self._url = None
        self._volume = 50
        self._adjst = adjust_volume
        self._latestUrl = None
        self._latestPlatform = None
        self._channels = None
        self._nexter = None
        self._nexterExt = None
        self.update_state()
        if adjust_volume:
            _LOGGER.error("auto adjust volume to max") 
        
    def path_observer(self, _name, value):
        self._url = value
        self.update_state()
        if self._nexter and not value:
            self._nexter.next()
        
    def volume_observer(self, _name, value): 
        self._volume = value
        self.update_state()
    
    def set_channels(self, channels):
        self._channels = channels
        self.update_state()
    def update_state(self):
        if self._hass != None:
            self._hass.states.async_set(DOMAIN + ".xmly", "off" if (self._url == None or self._latestPlatform != "xmly")  else "on", {
               "url": str(self._latestUrl) if self._latestPlatform == "xmly" else "None",
               "volume": str(self._volume),
               "name": "xmly",
               "friendly_name": "喜马拉雅FM"
            })
            self._hass.states.async_set(DOMAIN + ".qtfm", "off" if (self._url == None or self._latestPlatform != "qtfm")  else "on", {
               "url": str(self._latestUrl) if self._latestPlatform == "qtfm" else "None",
               "volume": str(self._volume),
               "name": "qtfm",
               "friendly_name": "蜻蜓FM"
            })
            self._hass.states.async_set(DOMAIN + ".voice", "off" if (self._url == None or self._latestPlatform != "voice")  else "on", {
               "volume": str(self._volume),
               "name": "voice",
               "friendly_name": "语音播放"
            })
            if self._channels:
                for channel in self._channels:
                    self._hass.states.async_set(DOMAIN + "." + channel, "off" if (self._url == None or self._latestPlatform != channel)  else "on", {
                        "url": str(self._latestUrl) if self._latestPlatform == channel else "None",
                       "volume": str(self._volume),
                       "name": channel,
                       "friendly_name": "音乐频道"
                    })
        
    @asyncio.coroutine
    def async_play(self, url = None, volume = None, platform = None, nexter=None):
        if url == None:
            url = self._latestUrl
        if url == None:
            return
        self._latestUrl = None
        if volume != None:
            self._volume = volume
        if platform != None:
            self._latestPlatform = platform
        yield from self.async_stop()       
        if self._adjst:
            try:
                import win32api
                WM_APPCOMMAND = 0x319
                APPCOMMAND_VOLUME_MAX = 0x0a
                APPCOMMAND_VOLUME_MIN = 0x09
                win32api.PostMessage(-1, WM_APPCOMMAND, 0x30292, APPCOMMAND_VOLUME_MAX * 0x10000)
            except ImportError:
                _LOGGER.warn("Not found win32api module")    
        self._ffplay = mpv.MPV(ytdl=True, volume=self._volume)
        self._ffplay.observe_property("path", self.path_observer)
        self._ffplay.play(url)
        self._latestUrl = url
        self._nexter = nexter
        self._nexterExt = nexter
        
    def play(self, url = None, volume = None, platform = None, nexter=None):
        if url == None:
            url = self._latestUrl
        if url == None:
            return
        self._latestUrl = None
        if volume != None:
            self._volume = volume
        if platform != None:
            self._latestPlatform = platform
        self._nexter = None
        if self._ffplay == None:
            return
        self._ffplay.terminate()
        self._url = None
        self.update_state() 
        if self._adjst:
            try: 
                import win32api
                WM_APPCOMMAND = 0x319
                APPCOMMAND_VOLUME_MAX = 0x0a
                APPCOMMAND_VOLUME_MIN = 0x09
                win32api.PostMessage(-1, WM_APPCOMMAND, 0x30292, APPCOMMAND_VOLUME_MAX * 0x10000)
            except ImportError:
                _LOGGER.warn("Not found win32api module")    
        self._ffplay = mpv.MPV(ytdl=True, volume=self._volume)
        self._ffplay.observe_property("path", self.path_observer)
        self._ffplay.play(url)
        self._latestUrl = url
        self._nexter = nexter
        self._nexterExt = nexter    
             
    @asyncio.coroutine
    def async_set_volume(self, vol):
        self._volume = vol
        url = self._url
        if url != None:
            yield from self.async_stop()
            yield from self.async_play(url)
            
    @asyncio.coroutine
    def async_add_volume(self):
        self._volume = self._volume + 10
        if self._volume > 100:
            self._volume = 100
        yield from self.async_set_volume(self._volume)
            
    @asyncio.coroutine
    def async_sub_volume(self):
        self._volume = self._volume - 10
        if self._volume < 10:
            self._volume = 10
        yield from self.async_set_volume(self._volume)    
        
    @asyncio.coroutine
    def async_toggle(self):
        if self._url == None:
            if self._latestUrl == None:
                return
            self._nexter = self._nexterExt
            yield from self.async_play(self._latestUrl)
        else:    
            self._nexter = None
            self._ffplay.terminate()
            self._url = None
            self._ffplay = None
        self.update_state()
        
    @asyncio.coroutine
    def async_stop(self):
        self._nexter = None
        if self._ffplay == None:
            return
        self._ffplay.terminate()
        self._url = None
        self.update_state()

TOKEN_INTERFACE = 'https://openapi.baidu.com/oauth/2.0/token'
TEXT2AUDIO_INTERFACE = 'http://tsn.baidu.com/text2audio'
class BaiduTTS:
    def __init__(self, basePath, apiKey, secretKey, speed = 5, pitch = 5, volume = 15, person = 0):
        self.apiKey = apiKey
        self.secretKey = secretKey
        self.speed = speed
        self.pitch = pitch
        self.volume = volume
        self.person = person
        self.player = AudioPlayer(None, False)
        self._mp3Path = ("" if (basePath == None) else basePath) + "/broadcast_tts.mp3"
        token = self.get_token()
        self.token = token
    def get_token(self):
        try:
            resp = requests.get(TOKEN_INTERFACE, verify=False, params={'grant_type': 'client_credentials',
                                                         'client_id': self.apiKey,
                                                         'client_secret':self.secretKey})
            if resp.status_code != 200:
                _LOGGER.error('Get token Http Error status_code:%s' % resp.status_code)
                return None
            resp.encoding = 'utf-8'
            tokenJson = resp.json()
            if not 'access_token' in tokenJson:
                _LOGGER.error('Get token Json Error!')
                return None
            return tokenJson['access_token']
        except Exception as ex:
            _LOGGER.error(ex)
            return None
    def generate_tts(self, message, file):
        try:
            if self.token == None:
                self.token = self.get_token()
            if self.token == None:
                _LOGGER.error('get_tts_audio Self.token is nil')
                return False
            resp = requests.get(TEXT2AUDIO_INTERFACE, verify=False, params={'tex': urllib.parse.quote(message),
                                                             'lan': 'zh',
                                                             'tok': self.token,
                                                             'ctp': '1',
                                                             'aue': 3,
                                                             'cuid': 'HomeAssistant',
                                                             'spd': self.speed,
                                                             'pit': self.pitch,
                                                             'vol': self.volume,
                                                             'per': self.person})
            if resp.status_code == 500:
                _LOGGER.error('Text2Audio Error:500 Not Support.')
                return False
            if resp.status_code == 501:
                _LOGGER.error('Text2Audio Error:501 Params Error')
                return False
            if resp.status_code == 502:
                _LOGGER.error('Text2Audio Error:502 TokenVerificationError.')
                _LOGGER.info('Now Get token!')
                self.token = self.get_token()
                return self.generate_tts(message, file)
            if resp.status_code == 503:
                _LOGGER.error('Text2Audio Error:503 Composite Error.')
                return False
            if resp.status_code != 200:
                _LOGGER.error('get_tts_audio Http Error status_code:%s' % resp.status_code)
                return False
            open(file, "wb").write(resp.content)
            return True    
        except Exception as ex:
            _LOGGER.error(ex)
            return False     
        
    @asyncio.coroutine
    def async_play_tts(self, message, volume):
        if message is None:
            _LOGGER.warning("message is not present.")
            return True       
        try:
            if not self.generate_tts(message, self._mp3Path):
                _LOGGER.error("generate tts failed.")
                return False    
            yield from self.player.async_play(self._mp3Path, volume)
        except Exception as error:
            _LOGGER.error(error)
            return False
        return True  
        
class VoiceUploader(HomeAssistantView):
    """View to handle Geofency requests."""
    url = '/api/broadcast/voice'
    name = 'api:broadcast:voice'
    def __init__(self, basePath, player):
        """Initialize Geofency url endpoints."""
        self._mp3Path = ("" if (basePath == None) else basePath) + "/broadcast_voice.mp3"
        self.player = player
    @asyncio.coroutine
    def post(self, request):
        """Handle Geofency requests."""
        queries = request.query
        if 'stop' in queries :
            yield from self.player.async_stop()
            return "stopped"
        else: 
            volume = 100
            if 'volume' in queries :
                volume = queries['volume']  
            with open(self._mp3Path, 'wb') as fil:
                while True:
                    data = yield from request.content.read(10240)
                    if not data:
                        break
                    fil.write(data)
            yield from self.player.async_play(self._mp3Path, volume, "voice")
            return "playing"
            

class FileListViewer(HomeAssistantView):
    """View to handle GPSLogger requests."""
    url = '/api/broadcast/files'
    name = 'api:broadcast:files'
    def __init__(self, players):
        """Initialize GPSLogger url endpoints."""        
        self._players = players
    async def get(self, request: Request):
        """Handle for GPSLogger message received as GET."""
        hass = request.app['hass']
        queries = request.query    
        if ATTR_ENTITY_ID not in queries :
            return ('Channel not specified.', HTTP_UNPROCESSABLE_ENTITY)
        channel = queries[ATTR_ENTITY_ID]
        channel = str(channel).replace(DOMAIN + ".", "")
        if channel not in self._players:
            return ('Channel not exist.', HTTP_UNPROCESSABLE_ENTITY)
        player = self._players[channel]
        result = player.files()    
        result = bytes(result, encoding = "utf8")
        response = web.StreamResponse()
        response.content_type = 'application/json'
        response.content_length = len(result)
        await response.prepare(request)
        await response.write(result)
        return response               
        
class FilePlayer:
    def __init__(self, channel, rootPath, player):
        self._channel = channel
        self.player = player
        self.allFile = []
        self.rootPath = rootPath.rstrip('/')
        self.getFiles(self.allFile, self.rootPath, ['.mp3', '.aac', '.flac', '.wav'])
        _LOGGER.error(rootPath + ' contain ' + str(len(self.allFile)) + ' files')
    def getFiles(self, allfiles, dir, extensions):
        for root, dirs, files in os.walk(dir):
            for filename in files:
                name, suf = os.path.splitext(filename)
                if suf in extensions:
                    allfiles.append(os.path.join(root, filename))
            for dir in dirs:
                self.getFiles(allfiles, os.path.join(root, dir), extensions)
    @asyncio.coroutine
    def async_play(self, url = None, volume = None):
        index = random.randint(0, len(self.allFile))
        file = self.allFile[index]
        if url:
            url = self.rootPath + str(url)
            if os.path.exists(url):
                file = url        
        yield from self.player.async_play(file, volume=volume, platform=self._channel, nexter=self)
    def next(self):
        index = random.randint(0, len(self.allFile))
        file = self.allFile[index]       
        self.player.play(file, platform=self._channel, nexter=self)
    def files(self):
        result = []
        for file in self.allFile:
            result.append(file.replace(self.rootPath, ''))
        return json.dumps(result)
        
@asyncio.coroutine
def async_setup(hass, config):
    conf = config.get(DOMAIN, {})
    adjust_volume = conf.get(CONF_MAX_VOLUME, False)
    player = AudioPlayer(hass, adjust_volume)
    basePath = conf.get(CONF_BASEPATH)
    apiKey = conf.get(CONF_APIKEY) 
    secretKey = conf.get(CONF_SECRETKEY)  
    speed = conf.get(CONF_SPEED, 5)
    pitch = conf.get(CONF_PITCH, 5)  
    volume = conf.get(CONF_VOLUME, 5) 
    person = conf.get(CONF_PERSON, 0) 
    channels = conf.get(CONF_CHANNELS)
    filePlayers = {}
    tts = BaiduTTS(basePath, apiKey, secretKey, speed, pitch, volume, person)    
    hass.http.register_view(VoiceUploader(basePath, player))
    if channels:
        channelNames = []
        for channel in channels:
            for key in channel:
                channelNames.append(key)
                filePlayers[key] = FilePlayer(key, channel[key], player)    
        player.set_channels(channelNames)
    hass.http.register_view(FileListViewer(filePlayers))
        
    @asyncio.coroutine
    def async_handle_play(service):
        url = service.data.get(ATTR_URL) 
        volume = service.data.get(ATTR_VOLUME) 
        entity_id = service.data.get(ATTR_ENTITY_ID) 
        platform = None
        if entity_id != None and str(entity_id).startswith(DOMAIN):
            platform = str(entity_id).replace(DOMAIN + ".", "")
        if platform and platform in filePlayers:
            yield from filePlayers[platform].async_play(url, volume)
        else:
            yield from player.async_play(url, volume, platform)
    @asyncio.coroutine
    def async_handle_stop(service):
        yield from player.async_stop()
    @asyncio.coroutine
    def async_handle_toggle(service):
        yield from player.async_toggle()
    @asyncio.coroutine
    def async_handle_add_volume(service):
        yield from player.async_add_volume()
    @asyncio.coroutine
    def async_handle_sub_volume(service):
        yield from player.async_sub_volume()
    @asyncio.coroutine
    def async_handle_set_volume(service):
        volume = service.data.get(ATTR_VOLUME) 
        yield from player.async_set_volume(int(volume))
    @asyncio.coroutine
    def async_handle_play_tts(service):
        message = service.data.get(ATTR_MESSAGE) 
        volume = service.data.get(ATTR_VOLUME) 
        if volume == None:
            volume = "80"
        yield from tts.async_play_tts(message, volume)
        
    hass.services.async_register(DOMAIN, SERVICE_PLAY, async_handle_play, schema=SERVICE_PLAY_SCHEMA)    
    hass.services.async_register(DOMAIN, SERVICE_STOP, async_handle_stop, schema=SERVICE_broadcast_SCHEMA)    
    hass.services.async_register(DOMAIN, SERVICE_TOGGLE, async_handle_toggle, schema=SERVICE_broadcast_SCHEMA)  
    hass.services.async_register(DOMAIN, SERVICE_ADD_VOLUME, async_handle_add_volume, schema=SERVICE_broadcast_SCHEMA)  
    hass.services.async_register(DOMAIN, SERVICE_SUB_VOLUME, async_handle_sub_volume, schema=SERVICE_broadcast_SCHEMA)    
    hass.services.async_register(DOMAIN, SERVICE_SET_VOLUME, async_handle_set_volume, schema=SERVICE_SET_VOLUME_SCHEMA)    
    hass.services.async_register(DOMAIN, SERVICE_PLAY_TTS, async_handle_play_tts, schema=SERVICE_PLAY_TTS_SCHEMA)                  
    return True
