"""
Support for getting data from websites with scraping.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.scrape/
"""
import logging

import voluptuous as vol
from requests.auth import HTTPBasicAuth, HTTPDigestAuth

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.components.sensor.rest import RestData
from homeassistant.const import (
    CONF_NAME, CONF_RESOURCE, CONF_UNIT_OF_MEASUREMENT, STATE_UNKNOWN,
    CONF_VALUE_TEMPLATE, CONF_VERIFY_SSL, CONF_USERNAME, CONF_HEADERS,
    CONF_PASSWORD, CONF_AUTHENTICATION, HTTP_BASIC_AUTHENTICATION,
    HTTP_DIGEST_AUTHENTICATION)
from homeassistant.helpers.entity import Entity
import homeassistant.helpers.config_validation as cv

REQUIREMENTS = ['lxml==4.2.5']

_LOGGER = logging.getLogger(__name__)

CONF_XPATH = 'xpath'
DEFAULT_NAME = 'Web scrape'
DEFAULT_VERIFY_SSL = True

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_RESOURCE): cv.string,
    vol.Required(CONF_XPATH): cv.string,
    vol.Optional(CONF_AUTHENTICATION):
        vol.In([HTTP_BASIC_AUTHENTICATION, HTTP_DIGEST_AUTHENTICATION]),
    vol.Optional(CONF_HEADERS): vol.Schema({cv.string: cv.string}),
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_PASSWORD): cv.string,
    vol.Optional(CONF_UNIT_OF_MEASUREMENT): cv.string,
    vol.Optional(CONF_USERNAME): cv.string,
    vol.Optional(CONF_VALUE_TEMPLATE): cv.template,
    vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): cv.boolean,
})


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Web scrape sensor."""
    name = config.get(CONF_NAME)
    resource = config.get(CONF_RESOURCE)
    method = 'GET'
    payload = None
    headers = config.get(CONF_HEADERS)
    verify_ssl = config.get(CONF_VERIFY_SSL)
    xpath = config.get(CONF_XPATH)
    unit = config.get(CONF_UNIT_OF_MEASUREMENT)
    username = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)
    value_template = config.get(CONF_VALUE_TEMPLATE)
    if value_template is not None:
        value_template.hass = hass

    if username and password:
        if config.get(CONF_AUTHENTICATION) == HTTP_DIGEST_AUTHENTICATION:
            auth = HTTPDigestAuth(username, password)
        else:
            auth = HTTPBasicAuth(username, password)
    else:
        auth = None
    rest = RestData(method, resource, auth, headers, payload, verify_ssl)
    rest.update()

    if rest.data is None:
        _LOGGER.error("Unable to fetch data from %s", resource)
        return False

    add_entities([
        ScrapeSensor(rest, name, xpath, value_template, unit)], True)


class ScrapeSensor(Entity):
    """Representation of a web scrape sensor."""

    def __init__(self, rest, name, xpath, value_template, unit):
        """Initialize a web scrape sensor."""
        self.rest = rest
        self._name = name
        self._state = STATE_UNKNOWN
        self._xpath = xpath
        self._value_template = value_template
        self._unit_of_measurement = unit

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return self._unit_of_measurement

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    def update(self):
        """Get the latest data from the source and updates the state."""
        self.rest.update()

        from lxml import etree

        raw_data = etree.HTML(self.rest.data)
        try:
            value = raw_data.xpath(self._xpath)[0]
            _LOGGER.error(value)
        except IndexError:
            _LOGGER.error("Unable to extract data from HTML")
            return

        if self._value_template is not None:
            self._state = self._value_template.render_with_possible_json_value(value, STATE_UNKNOWN)
        else:
            self._state = value
