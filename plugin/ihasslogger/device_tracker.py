"""
Support for the GPSLogger platform.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/device_tracker.gpslogger/
"""
import logging
import time
import asyncio
import json
import requests
import math
from hmac import compare_digest

from aiohttp.web import Request, HTTPUnauthorized
import voluptuous as vol

from homeassistant.helpers import location
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv
from homeassistant.const import (
    CONF_PASSWORD, HTTP_UNPROCESSABLE_ENTITY
)
from homeassistant.const import (CONF_VALUE_TEMPLATE, ATTR_ENTITY_ID, EVENT_HOMEASSISTANT_START, ATTR_FRIENDLY_NAME, 
    CONF_ICON_TEMPLATE, CONF_SENSORS, ATTR_LATITUDE, ATTR_LONGITUDE, ATTR_ATTRIBUTION, STATE_HOME)
from homeassistant.components.http import (
    CONF_API_PASSWORD, HomeAssistantView
)
from homeassistant.helpers.event import async_track_state_change
# pylint: disable=unused-import
from homeassistant.components.device_tracker import (  # NOQA
    DOMAIN, PLATFORM_SCHEMA
)
from homeassistant.helpers.typing import HomeAssistantType, ConfigType
from homeassistant.helpers.config_validation import (ENTITY_SERVICE_SCHEMA)
from homeassistant.const import (ATTR_ENTITY_ID)

_LOGGER = logging.getLogger(__name__)
CONF_BAIDUAK = "baidu_lbsak"
CONF_TTS_DOMAIN = "tts_domain"
CONF_TTS_SERVICE = "tts_service"
CONF_TTS_MESSAGE = "tts_message"

SENSOR_SCHEMA = vol.Schema({
    vol.Required(CONF_VALUE_TEMPLATE): cv.template
})
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_PASSWORD): cv.string,
    vol.Optional(CONF_BAIDUAK): cv.string,
    vol.Optional(CONF_TTS_DOMAIN): cv.string,
    vol.Optional(CONF_TTS_SERVICE): cv.string,
    vol.Optional(CONF_TTS_MESSAGE): cv.string,
    vol.Optional(CONF_SENSORS): vol.Schema({cv.slug: SENSOR_SCHEMA}),
})

ATTR_FRIENDLY_NAME = "friendly_name"
DATA_KEY = "ihass-logger"
SERVICE_REPORT_ADDRESS = 'report_address'
SERVICE_REPORT_ADDRESS_SCHEMA = ENTITY_SERVICE_SCHEMA.extend({
    vol.Optional(ATTR_FRIENDLY_NAME): cv.string,
})

async def async_setup_scanner(hass: HomeAssistantType, config: ConfigType,
                              async_see, discovery_info=None):
    """Set up an endpoint for the GPSLogger application."""
    if DATA_KEY not in hass.data:
        hass.data[DATA_KEY] = {}
    baidu_ak = config.get(CONF_BAIDUAK)
    tts_domain = config.get(CONF_TTS_DOMAIN)
    tts_service = config.get(CONF_TTS_SERVICE)
    tts_message = config.get(CONF_TTS_MESSAGE, "message")
    def getAddress(lat, lng):
        url = "http://api.map.baidu.com/geocoder/v2/?location=" + str(lat) + "," + str(lng) + "&output=json&coordtype=wgs84ll&pois=1&ak=" + baidu_ak
        header = {'Referer':'http://hass.yunsean.com'}
        payload = {
            'output':'json',
            'ak': baidu_ak
            }
        addinfo = []
        try:
            content = requests.get(url, params=payload, headers=header).json()
            _LOGGER.error(content)
            building = None
            if len(content['result']['pois']) > 0:
                building = content['result']['pois'][0]['name']
            return content['result']['formatted_address'], building
        except Exception as ex:
            _LOGGER.error(ex)
            return None, None
    def getDistance(lat2, lng2):
        home = hass.states.get("zone.home")
        if not home or not home.attributes.get(ATTR_LONGITUDE) or not home.attributes.get(ATTR_LATITUDE):
            return None
        lng1 = home.attributes.get(ATTR_LONGITUDE)
        lat1 = home.attributes.get(ATTR_LATITUDE)
        x1 = math.pi / 180 * lng1
        x2 = math.pi / 180 * lng2
        y1 = math.pi / 180 * lat1
        y2 = math.pi / 180 * lat2
        radius = 6371.0
        return math.acos(math.sin(y1) * math.sin(y2) + math.cos(y1) * math.cos(y2) * math.cos(x2 - x1)) * radius

    async def async_service_handler(service):
        """Map services to methods on Xiaomi Philips Lights."""
        entity_ids = service.data.get(ATTR_ENTITY_ID)  
        friendly_name = service.data.get(ATTR_FRIENDLY_NAME)  
        if not baidu_ak or not tts_service:
            return
        if not entity_ids or len(entity_ids) < 1:
            _LOGGER.warn("No entity_id pointed.")
            await hass.services.async_call(tts_domain, tts_service, {tts_message: "未指定播报对象！"}, blocking=True)
            return
        entity_id = entity_ids[0]    
        entity = hass.states.get(entity_id)
        if not entity:
            await hass.services.async_call(tts_domain, tts_service, {tts_message: "未找到指定的播报对象！"}, blocking=True)
            return
        name = friendly_name
        if not friendly_name and entity.attributes.get(ATTR_FRIENDLY_NAME):
            name = entity.attributes.get(ATTR_FRIENDLY_NAME)
        if not name:
            name = ""
        if hass.states.is_state(entity_id, STATE_HOME):
            await hass.services.async_call(tts_domain, tts_service, {tts_message: name + "当前在家呢！"}, blocking=True)
            return
        if not entity.attributes.get(ATTR_LONGITUDE) or not entity.attributes.get(ATTR_LATITUDE):
            await hass.services.async_call(tts_domain, tts_service, {tts_message: "未上报经纬度"}, blocking=True)
            return
        longitude = entity.attributes.get(ATTR_LONGITUDE)
        latitude = entity.attributes.get(ATTR_LATITUDE)
        address, building = getAddress(latitude, longitude)
        distant = getDistance(latitude, longitude)
        if not building and not distant:
            info = "查询地理位置失败！"
        elif building:
            info = name + "当前位于" + address + "的" + building + "，距离你%.1f" % distant + "公里"
        else:
            info = name + "当前位于" + address + "，距离你%.1f" % distant + "公里"
        await hass.services.async_call(tts_domain, tts_service, {tts_message: info}, blocking=True)

    hass.http.register_view(GPSLoggerView(hass, async_see, config))          
    hass.services.async_register(DOMAIN, SERVICE_REPORT_ADDRESS, async_service_handler, schema = SERVICE_REPORT_ADDRESS_SCHEMA)
    return True

class GPSLoggerView(HomeAssistantView):
    """View to handle GPSLogger requests."""

    url = '/api/gpslogger'
    name = 'api:gpslogger'

    def __init__(self, hass, async_see, config):
        """Initialize GPSLogger url endpoints."""
        self._value_templates = {}
        self._template_devices = {}
        self._state_cache = {}
        self._entities = []
        self.hass = hass
        if config[CONF_SENSORS]:
            for device, device_config in config[CONF_SENSORS].items():
                value_template = device_config[CONF_VALUE_TEMPLATE]
                if value_template is not None:
                    entities = device_config.get(ATTR_ENTITY_ID) or value_template.extract_entities()
                    for entity in entities:
                        self._template_devices[entity] = device
                    self._entities.extend(entities)
                    value_template.hass = hass
                    self._value_templates[device] = value_template    
        self.async_see = async_see
        self._password = config.get(CONF_PASSWORD)
        # this component does not require external authentication if
        # password is set
        self.requires_auth = self._password is None
        
        @callback
        def template_bsensor_state_listener(entity, old_state, new_state):
            """Handle the target device state changes."""
            if entity in self._template_devices:
                device = self._template_devices[entity]
                location_name = self._value_templates[device].async_render()
                if device in self._state_cache:
                    state = self._state_cache[device]
                    hass.async_add_job(self.async_see(
                        dev_id=device,
                        location_name=location_name,
                        gps=state["gps"], 
                        battery=state["battery"],
                        gps_accuracy=state["accuracy"],
                        attributes=state["attributes"]
                    ))
                else:
                    hass.async_add_job(self.async_see(
                        dev_id=device,
                        location_name=location_name
                    ))
        @callback
        def template_bsensor_startup(event):
            """Update template on startup."""
            if len(self._entities) > 0:
                async_track_state_change(self.hass, self._entities, template_bsensor_state_listener)            
        self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, template_bsensor_startup)

    async def get(self, request: Request):
        """Handle for GPSLogger message received as GET."""
        hass = request.app['hass']
        data = request.query

        if self._password is not None:
            authenticated = CONF_API_PASSWORD in data and compare_digest(
                self._password,
                data[CONF_API_PASSWORD]
            )
            if not authenticated:
                raise HTTPUnauthorized()

        if 'gps' in data :
            gps_location = tuple(data['gps'].split(','))
        elif 'latitude' not in data or 'longitude' not in data:
            _LOGGER.error("Latitude and longitude not specified")
            return ('Latitude and longitude not specified.', HTTP_UNPROCESSABLE_ENTITY)
        else:
            gps_location = (data['latitude'], data['longitude']) 

        if 'device' not in data:
            _LOGGER.error("Device id not specified")
            return ('Device id not specified.', HTTP_UNPROCESSABLE_ENTITY)
        else:
            device = data['device'].replace('-', '')
            
        accuracy = 200
        battery = -1
        if 'accuracy' in data:
            accuracy = int(float(data['accuracy']))
        if 'battery' in data:
            battery = float(data['battery'])            
        
        location_name = None
        if device in self._value_templates:
            location_name = self._value_templates[device].async_render()

        attrs = {}
        for key in data:
            if key == 'speed':
                attrs['speed'] = float(data['speed'])
            elif key == 'direction':
                attrs['direction'] = float(data['direction'])
            elif key == 'altitude':
                attrs['altitude'] = float(data['altitude'])
            elif key == 'provider':
                attrs['provider'] = data['provider']
            elif key == 'batteryTemperature':
                attrs['batteryTemperature'] = data['batteryTemperature']
            elif key == 'charging':
                attrs['charging'] = data['charging']
            elif key == 'interactive':
                attrs['interactive'] = data['interactive']
            elif key == 'wifi':
                attrs['wifi'] = data['wifi']
            elif key == 'app':
                attrs['app'] = data['app']
            elif key == 'address':
                attrs['address'] = data['address']
        hass.async_add_job(self.async_see(
            dev_id=device,
            location_name=location_name,
            gps=gps_location, 
            battery=battery,
            gps_accuracy=accuracy,
            attributes=attrs
        ))
        self._state_cache[device] = {"gps": gps_location, "battery": battery, "accuracy": accuracy, "attributes": attrs}

        return 'Setting location for {}'.format(device)
