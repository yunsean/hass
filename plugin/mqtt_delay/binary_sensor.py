"""
Support for MQTT binary sensors.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/binary_sensor.mqtt/
"""
import asyncio
import logging
import time
from threading import Timer
from typing import Optional

import voluptuous as vol

from homeassistant.core import callback
from homeassistant.components import mqtt
from homeassistant.components.binary_sensor import (
    BinarySensorDevice, DEVICE_CLASSES_SCHEMA)
from homeassistant.const import (
    CONF_FORCE_UPDATE, CONF_NAME, CONF_VALUE_TEMPLATE, CONF_PAYLOAD_ON,
    CONF_PAYLOAD_OFF, CONF_DEVICE_CLASS)
from homeassistant.components.mqtt import (ATTR_DISCOVERY_HASH, CONF_DEVICE, 
    CONF_STATE_TOPIC, CONF_AVAILABILITY_TOPIC, CONF_PAYLOAD_AVAILABLE,
    CONF_PAYLOAD_NOT_AVAILABLE, CONF_QOS, MqttAvailability,
    MqttDiscoveryUpdate, MqttEntityDeviceInfo, MqttAttributes)
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = 'MQTT Binary sensor'
CONF_UNIQUE_ID = 'unique_id'
CONF_COUNT_TO_ON = 'count_to_on'
CONF_AFTER_TO_OFF = 'after_to_off'
CONF_WAIT_TO_ON = 'wait_to_on'
CONF_DELAY_TO_ON = 'delay_to_on'
DEFAULT_PAYLOAD_OFF = 'OFF'
DEFAULT_PAYLOAD_ON = 'ON'
DEFAULT_FORCE_UPDATE = False

PLATFORM_SCHEMA = mqtt.MQTT_RO_PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_PAYLOAD_ON, default=DEFAULT_PAYLOAD_ON): cv.string,
    vol.Optional(CONF_COUNT_TO_ON, default=1): cv.string,
    vol.Optional(CONF_AFTER_TO_OFF, default=60): cv.string,
    vol.Optional(CONF_WAIT_TO_ON, default=5): cv.string,
    vol.Optional(CONF_DELAY_TO_ON, default=0): cv.string,
    vol.Optional(CONF_DEVICE_CLASS): DEVICE_CLASSES_SCHEMA,
    vol.Optional(CONF_FORCE_UPDATE, default=DEFAULT_FORCE_UPDATE): cv.boolean,
    vol.Optional(CONF_UNIQUE_ID): cv.string,
}).extend(mqtt.MQTT_AVAILABILITY_SCHEMA.schema)


@asyncio.coroutine
def async_setup_platform(hass, config, async_add_entities,
                         discovery_info=None):
    """Set up the MQTT binary sensor."""
    if discovery_info is not None:
        config = PLATFORM_SCHEMA(discovery_info)

    value_template = config.get(CONF_VALUE_TEMPLATE)
    if value_template is not None:
        value_template.hass = hass

    async_add_entities([MqttBinarySensor(
        config,
        config.get(CONF_NAME),
        config.get(CONF_STATE_TOPIC),
        config.get(CONF_AVAILABILITY_TOPIC),
        config.get(CONF_DEVICE_CLASS),
        config.get(CONF_QOS),
        config.get(CONF_FORCE_UPDATE),
        config.get(CONF_PAYLOAD_ON),
        config.get(CONF_COUNT_TO_ON),
        config.get(CONF_WAIT_TO_ON),
        config.get(CONF_DELAY_TO_ON),
        config.get(CONF_AFTER_TO_OFF),
        config.get(CONF_PAYLOAD_AVAILABLE),
        config.get(CONF_PAYLOAD_NOT_AVAILABLE),
        value_template,
        config.get(CONF_UNIQUE_ID),
        None,
        None
    )])

def do_timeout(self):
    if self.timer:
        self.timer.cancel()
    self.pending = False   
    self.timer = None
    self._state = False
    self.async_schedule_update_ha_state()
    self.last_fire = 0    
    
def do_start(self):
    self.start()

class MqttBinarySensor(MqttAttributes, MqttAvailability, MqttEntityDeviceInfo, BinarySensorDevice):
    """Representation a binary sensor that is updated by MQTT."""

    def __init__(self, config, name, state_topic, availability_topic, device_class,
                 qos, force_update, payload_on, count_to_on, wait_to_on, delay_to_on, after_to_off, payload_available,
                 payload_not_available, value_template,
                 unique_id: Optional[str], config_entry=None, discovery_hash=None):
        """Initialize the MQTT binary sensor."""
        self._name = name
        self._state = False
        self._state_topic = state_topic
        self._device_class = device_class
        self._payload_on = payload_on
        self._wait_to_on = int(wait_to_on)
        self._count_to_on = int(count_to_on)
        self._after_to_off = int(after_to_off)
        self._delay_to_on = int(delay_to_on)
        self._qos = qos
        self._force_update = force_update
        self._template = value_template
        self._unique_id = unique_id
        self.last_fire = 0
        self.timer = None
        self.count = 0
        self.pending = False

        device_config = config.get(CONF_DEVICE)
        MqttAttributes.__init__(self, config)
        MqttAvailability.__init__(self, config)
        MqttEntityDeviceInfo.__init__(self, device_config, config_entry)

    @asyncio.coroutine
    def async_added_to_hass(self):
        """Subscribe mqtt events."""
        yield from super().async_added_to_hass()

        @callback
        def state_message_received(topic, payload, qos):
            """Handle a new received MQTT state message."""
            if self._template is not None:
                payload = self._template.async_render_with_possible_json_value(payload)
            if payload == self._payload_on:
                self.on_payload_on()
            else:
                self.on_payload_off()

        yield from mqtt.async_subscribe(
            self.hass, self._state_topic, state_message_received, self._qos)       
            
    def start(self):
        self.pending = False
        self._state = True
        self.async_schedule_update_ha_state()
        self.last_fire = 0 
           
    def on_payload_off(self):
        if (not self._state) and self.pending:
            if self.timer:
                self.timer.cancel()
            self.pending = False        
            self.timer = None
        elif self._state and (time.time() - self.last_fire > 3):  
            if self.timer:
                self.timer.cancel()
            self.timer = Timer(self._after_to_off, do_timeout, (self,))
            self.timer.start()
            self.last_fire = time.time() 
        
    def on_payload_on(self):
        if (not self._state) and (not self.pending) and (time.time() - self.last_fire >= self._wait_to_on):
            self.last_fire = time.time()
            self.count = 0
        if (not self._state) and (not self.pending) and (time.time() - self.last_fire < self._wait_to_on):
            self.count = self.count + 1
            if self.count >= self._count_to_on:
                self.start()
            elif (self._delay_to_on > 0) and (not self.pending):
                self.pending = True
                if self.timer:
                    self.timer.cancel()
                self.timer = Timer(self._delay_to_on, do_start, (self,))
                self.timer.start()
        if self._state and self.timer:
            self.timer.cancel()        
            self.timer = None
            self.last_fire = 0

    @property
    def should_poll(self):
        """Return the polling state."""
        return False

    @property
    def name(self):
        """Return the name of the binary sensor."""
        return self._name

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        return self._state

    @property
    def device_class(self):
        """Return the class of this sensor."""
        return self._device_class

    @property
    def force_update(self):
        """Force update."""
        return self._force_update

    @property
    def unique_id(self):
        """Return a unique ID."""
        return self._unique_id
