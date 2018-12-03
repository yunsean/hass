"""
Support for the GPSLogger platform.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/device_tracker.gpslogger/
"""
import logging
import time
import asyncio
from hmac import compare_digest

from aiohttp.web import Request, HTTPUnauthorized
import voluptuous as vol

from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv
from homeassistant.const import (
    CONF_PASSWORD, HTTP_UNPROCESSABLE_ENTITY
)
from homeassistant.const import (CONF_VALUE_TEMPLATE, ATTR_ENTITY_ID, EVENT_HOMEASSISTANT_START,
    CONF_ICON_TEMPLATE, CONF_SENSORS)
from homeassistant.components.http import (
    CONF_API_PASSWORD, HomeAssistantView
)
from homeassistant.helpers.event import async_track_state_change
# pylint: disable=unused-import
from homeassistant.components.device_tracker import (  # NOQA
    DOMAIN, PLATFORM_SCHEMA
)
from homeassistant.helpers.typing import HomeAssistantType, ConfigType

_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = ['http']

SENSOR_SCHEMA = vol.Schema({
    vol.Required(CONF_VALUE_TEMPLATE): cv.template
})
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_PASSWORD): cv.string,
    vol.Optional(CONF_SENSORS): vol.Schema({cv.slug: SENSOR_SCHEMA}),
})

async def async_setup_scanner(hass: HomeAssistantType, config: ConfigType,
                              async_see, discovery_info=None):
    """Set up an endpoint for the GPSLogger application."""
    hass.http.register_view(GPSLoggerView(hass, async_see, config))
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
            elif key == 'altitude':
                attrs['altitude'] = data['altitude']
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
