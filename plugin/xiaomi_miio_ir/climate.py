"""
Support for Xiaomi Mi Home Air Conditioner Companion (AC Partner)

For more details about this platform, please refer to the documentation
https://home-assistant.io/components/climate.xiaomi_miio
"""
import enum
import json
import time
import logging
import asyncio
from functools import partial
from datetime import timedelta
import voluptuous as vol
from typing import Any, Dict, List, Optional

from homeassistant.core import callback
from homeassistant.components.climate import (
    ClimateDevice, PLATFORM_SCHEMA, )
from homeassistant.components.climate.const import (
    ATTR_HVAC_MODE, DOMAIN, HVAC_MODES, HVAC_MODE_OFF, HVAC_MODE_HEAT, 
    HVAC_MODE_COOL, HVAC_MODE_AUTO, HVAC_MODE_DRY, HVAC_MODE_FAN_ONLY,
    SUPPORT_SWING_MODE, SUPPORT_FAN_MODE, SUPPORT_AUX_HEAT, SUPPORT_TARGET_TEMPERATURE, )
from homeassistant.const import (
    ATTR_ENTITY_ID, ATTR_TEMPERATURE, ATTR_UNIT_OF_MEASUREMENT, CONF_NAME,
    CONF_HOST, CONF_TOKEN, CONF_TIMEOUT, TEMP_CELSIUS, )
from homeassistant.exceptions import PlatformNotReady
from homeassistant.helpers.event import async_track_state_change
import homeassistant.helpers.config_validation as cv
from homeassistant.util.dt import utcnow
from homeassistant.util.json import load_json, save_json

_LOGGER = logging.getLogger(__name__)
ATTR_DEVICES = 'climates'
CONFIG_FILENAME = '.xiaomi_miio_ir' 

SUCCESS = ['ok']

DEFAULT_NAME = 'Xiaomi AC Companion With Ir'
DATA_KEY = 'climate.xiaomi_miio_ir'
TARGET_TEMPERATURE_STEP = 1

DEFAULT_TIMEOUT = 10
DEFAULT_SLOT = 30

ATTR_AIR_CONDITION_MODEL = 'ac_model'
ATTR_SWING_MODE = 'swing_mode'
ATTR_SWING_MODE = 'swing_mode'
ATTR_FAN_MODE = 'fan_mode'
ATTR_LOAD_POWER = 'load_power'
ATTR_AUX_HEAT = 'aux_heat'
ATTR_LED = 'led'

SUPPORT_FLAGS = (SUPPORT_TARGET_TEMPERATURE |
                 SUPPORT_FAN_MODE)

CONF_SENSOR = 'target_sensor'
CONF_MIN_TEMP = 'min_temp'
CONF_MAX_TEMP = 'max_temp'
CONF_INSTRUCTS = 'instructs'
CONF_FAN_MODE = 'fan_mode_list'
CONF_OPERATION = 'operation_list'
CONF_SWING = 'swing_list'
CONF_AUX_HEAT = 'support_aux_heat'
CONF_IS_LUMI = 'is_lumi'
CONF_MIN_POWER = 'min_work_power'

SCAN_INTERVAL = timedelta(seconds=15)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_TOKEN): vol.All(cv.string, vol.Length(min=32, max=32)),
    vol.Required(CONF_SENSOR): cv.entity_id,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_MIN_TEMP, default=18): vol.Coerce(int),
    vol.Optional(CONF_MAX_TEMP, default=30): vol.Coerce(int),
    vol.Optional(CONF_INSTRUCTS): vol.All(cv.ensure_list),
    vol.Optional(CONF_FAN_MODE): cv.string,
    vol.Optional(CONF_OPERATION): cv.string,
    vol.Optional(CONF_SWING): cv.string,
    vol.Optional(CONF_AUX_HEAT, default=False): cv.boolean,
    vol.Optional(CONF_IS_LUMI, default=False): cv.boolean,
    vol.Optional(CONF_MIN_POWER, default=0): vol.Coerce(int),
})

# pylint: disable=unused-argument
@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """Set up the air conditioning companion from config."""
    from miio import AirConditioningCompanion, DeviceException

    host = config.get(CONF_HOST)
    name = config.get(CONF_NAME)
    token = config.get(CONF_TOKEN)
    min_temp = config.get(CONF_MIN_TEMP)
    max_temp = config.get(CONF_MAX_TEMP)
    sensor_entity_id = config.get(CONF_SENSOR)
    instructs = config.get(CONF_INSTRUCTS)
    fan_mode_list = config.get(CONF_FAN_MODE)
    operation_list = config.get(CONF_OPERATION)
    swing_list = config.get(CONF_SWING)
    aux_heat = config.get(CONF_AUX_HEAT)
    is_lumi = config.get(CONF_IS_LUMI)
    min_power = config.get(CONF_MIN_POWER)
    if fan_mode_list == None:
        fan_mode_list = 'Low,Medium,High,Auto'
    if operation_list == None:
        operation_list = 'Heat,Cool,Dehumidify,Ventilate'
    instructsMap = {}
    for instruct in instructs:
        parts = instruct.split(':', 1)
        if len(parts) > 1:
            instructsMap[parts[0]] = parts[1]
    _LOGGER.info("Initializing with host %s (token %s...)", host, token[:5])

    try:
        device = AirConditioningCompanion(host, token)
        device_info = device.info()
        model = device_info.model
        unique_id = "{}-{}".format(model, device_info.mac_address)
        _LOGGER.info("%s %s %s detected",
                     model,
                     device_info.firmware_version,
                     device_info.hardware_version)
    except DeviceException as ex:
        _LOGGER.error("Device unavailable or token incorrect: %s", ex)
        raise PlatformNotReady

    async_add_devices([XiaomiAirConditioningCompanion(
        hass, name, device, unique_id, sensor_entity_id, min_temp, max_temp, instructsMap, fan_mode_list, operation_list, swing_list, aux_heat, is_lumi, min_power)],
        update_before_add=True)

class XiaomiAirConditioningCompanion(ClimateDevice):
    """Representation of a Xiaomi Air Conditioning Companion."""

    def __init__(self, hass, name, device, unique_id, sensor_entity_id, min_temp, max_temp, instructsMap, fan_mode_list, operation_list, swing_list, aux_heat, is_lumi, min_power):

        """Initialize the climate device."""
        self.hass = hass
        self._name = name
        self._device = device
        self._unique_id = unique_id
        self._sensor_entity_id = sensor_entity_id
        self._support_aux_heat = aux_heat
        self._support_swing_mode = True if (swing_list != None and len(swing_list) > 1) else False

        self._available = False
        self._state_attrs = {
            ATTR_LOAD_POWER: None,
            ATTR_TEMPERATURE: None,
            ATTR_SWING_MODE: None,
            ATTR_FAN_MODE: None,
            ATTR_HVAC_MODE: None,
        }

        self._min_temp = min_temp
        self._max_temp = max_temp
        self._current_temperature = 25
        self._current_swing_mode = 'Off'
        self._current_operation = 'Cool'
        self._current_fan_mode = 'Auto'
        self._target_temperature = 25
        self._fan_mode_list = fan_mode_list
        self._operation_list = operation_list
        self._instructs_map = instructsMap
        self._swing_list = swing_list
        self._aux_heat = False
        self._is_lumi = is_lumi
        self._min_power = min_power
        self._turn_on = False
        self._power_on = False
        self._latest_power_on = time.time()
        
        try:            
            with open(self.hass.config.path(CONFIG_FILENAME)) as fptr:
                states = json.loads(fptr.read())
            if not states:
                states = {ATTR_DEVICES: {}}
            state = states[ATTR_DEVICES][self._unique_id]
            self._current_swing_mode = state['swing_mode']
            self._current_operation = state['operation']
            self._current_fan_mode = state['fan_mode']
            self._target_temperature = state['temperature']
            self._aux_heat = state['aux_heat']
        except:
            _LOGGER.warn("load latest state failed.")

        if sensor_entity_id:
            async_track_state_change(hass, sensor_entity_id, self._async_sensor_changed)
            sensor_state = hass.states.get(sensor_entity_id)
            if sensor_state:
                self._async_update_temp(sensor_state)

    @callback
    def _async_update_temp(self, state):
        """Update thermostat with latest state from sensor."""
        if state.state is None or state.state == 'unknown':
            return
        unit = state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
        try:
            self._current_temperature = self.hass.config.units.temperature(float(state.state), unit)
        except ValueError as ex:
            _LOGGER.error('Unable to update from sensor: %s', ex)

    @asyncio.coroutine
    def _async_sensor_changed(self, entity_id, old_state, new_state):
        """Handle temperature changes."""
        if new_state is None:
            return
        self._async_update_temp(new_state)


    def save_config(self):
        try:
            with open(self.hass.config.path(CONFIG_FILENAME)) as fptr:
                states = json.loads(fptr.read())
        except:
            states = None
        if not states:
            states = {ATTR_DEVICES: {}}
        states[ATTR_DEVICES][self._unique_id] = {
            "operation": self._current_operation,
            "fan_mode": self._current_fan_mode,
            "swing_mode": self._current_swing_mode,
            "temperature": self._target_temperature,
            "aux_heat": self._aux_heat
        } 
        with open(self.hass.config.path(CONFIG_FILENAME), "w") as fptr:
            fptr.write(json.dumps(states))

    
    @asyncio.coroutine
    def _try_command(self, key = None):
        """Call a AC companion command handling error messages."""
        self.save_config()
        if self._turn_on == False:
            key = 'close'
            instruct = self._instructs_map[key] if key in self._instructs_map else None
        elif key != None:
            instruct = self._instructs_map[key] if key in self._instructs_map else None
        else:
            self._target_temperature = int(self._target_temperature)
            instruct = None
            if self._aux_heat:
                if True:
                    key = self._current_operation.lower() + '-' + self._current_fan_mode.lower() + '-' + self._current_swing_mode.lower() + '-' + str(self._target_temperature) + '-aux'
                    instruct = self._instructs_map[key] if key in self._instructs_map else None
                if instruct == None:    
                    key = self._current_operation.lower() + '-' + self._current_fan_mode.lower() + '-' + self._current_swing_mode.lower() + '-' + str(self._target_temperature) + '-aux'
                    instruct = self._instructs_map[key] if key in self._instructs_map else None
                if instruct == None:
                    key = self._current_operation.lower() + '-' + self._current_fan_mode.lower() + '-' + self._current_swing_mode.lower() + '-aux'
                    instruct = self._instructs_map[key] if key in self._instructs_map else None
                if instruct == None and self._current_swing_mode.lower() == 'on':
                    key = self._current_operation.lower() + '-' + self._current_fan_mode.lower() + '-' + 'off' + '-' + str(self._target_temperature) + '-aux'
                    instruct = self._instructs_map[key] if key in self._instructs_map else None
                if instruct == None and self._current_fan_mode.lower() != 'auto':
                    key = self._current_operation.lower() + '-' + 'auto' + '-' + self._current_swing_mode.lower() + '-' + str(self._target_temperature) + '-aux'
                    instruct = self._instructs_map[key] if key in self._instructs_map else None
                if instruct == None:
                    key = self._current_operation.lower() + '-' + 'auto' + '-' + 'off' + '-' + str(self._target_temperature) + '-aux'
                    instruct = self._instructs_map[key] if key in self._instructs_map else None
                if instruct == None:
                    key = self._current_operation.lower() + '-' + 'auto' + '-' + 'off' + '-aux'
                    instruct = self._instructs_map[key] if key in self._instructs_map else None  
                if instruct == None:
                    key = self._current_operation.lower() + '-' + 'auto' + '-aux'
                    instruct = self._instructs_map[key] if key in self._instructs_map else None
                if instruct == None:
                    key = self._current_operation.lower() + '-aux'
                    instruct = self._instructs_map[key] if key in self._instructs_map else None
            if instruct == None:    
                key = self._current_operation.lower() + '-' + self._current_fan_mode.lower() + '-' + self._current_swing_mode.lower() + '-' + str(self._target_temperature)
                instruct = self._instructs_map[key] if key in self._instructs_map else None
            if instruct == None:
                key = self._current_operation.lower() + '-' + self._current_fan_mode.lower() + '-' + self._current_swing_mode.lower()
                instruct = self._instructs_map[key] if key in self._instructs_map else None
            if instruct == None and self._current_swing_mode.lower() == 'on':
                key = self._current_operation.lower() + '-' + self._current_fan_mode.lower() + '-' + 'off' + '-' + str(self._target_temperature)
                instruct = self._instructs_map[key] if key in self._instructs_map else None
            if instruct == None and self._current_fan_mode.lower() != 'auto':
                key = self._current_operation.lower() + '-' + 'auto' + '-' + self._current_swing_mode.lower() + '-' + str(self._target_temperature)
                instruct = self._instructs_map[key] if key in self._instructs_map else None
            if instruct == None:
                key = self._current_operation.lower() + '-' + 'auto' + '-' + 'off' + '-' + str(self._target_temperature)
                instruct = self._instructs_map[key] if key in self._instructs_map else None
            if instruct == None:
                key = self._current_operation.lower() + '-' + 'auto' + '-' + 'off'
                instruct = self._instructs_map[key] if key in self._instructs_map else None  
            if instruct == None:
                key = self._current_operation.lower() + '-' + 'auto'
                instruct = self._instructs_map[key] if key in self._instructs_map else None
            if instruct == None:
                key = self._current_operation.lower()
                instruct = self._instructs_map[key] if key in self._instructs_map else None
        if instruct == None:
            _LOGGER.error("Can not convert instruct for key =" + key + ", operation=" + self._current_operation.lower() + ", fan mode=" + self._current_fan_mode.lower() + ", swing mode=" + self._current_swing_mode.lower() + ", temperature=" + str(self._target_temperature))
            return False
        _LOGGER.error("Will send instruct for:" + key)  
        from miio import DeviceException
        try:                      
            self._device.send('send_ir_code', [instruct])
            return True
        except DeviceException as exc:
            _LOGGER.error(mask_error, exc)
            return False

    @asyncio.coroutine
    def async_turn_on(self, speed: str = None, **kwargs) -> None:
        """Turn the miio device on."""
        state = self._turn_on
        if self._is_lumi:
            self._device.on()
            yield from asyncio.sleep(3)
        self._turn_on = True
        result = yield from self._try_command()
        if not result:
            self._turn_on = state
        else:    
            self._latest_power_on = time.time()

    @asyncio.coroutine
    def async_turn_off(self, **kwargs) -> None:
        """Turn the miio device off."""
        state = self._turn_on
        self._turn_on = False
        self._device.off()
        result = yield from self._try_command()
        if not result:
            self._turn_on = state

    @asyncio.coroutine
    def async_update(self):
        """Update the state of this climate device."""
        from miio import DeviceException
        from miio.airconditioningcompanion import SwingMode
        try:
            state = yield from self.hass.async_add_job(self._device.status)
            if self._min_power == 0:
                self._power_on = state.is_on
            else:
                self._power_on = state.load_power >= self._min_power
            if self._power_on:
                self._latest_power_on = time.time()
            if self._turn_on and (time.time() - self._latest_power_on > 120):
                self._turn_on = False
            self._state_attrs.update({
                ATTR_LOAD_POWER: state.load_power,
                ATTR_TEMPERATURE: self._target_temperature,
                ATTR_SWING_MODE: self._current_swing_mode,
                ATTR_FAN_MODE: self._current_fan_mode,
                ATTR_HVAC_MODE: self._current_operation,
                ATTR_AUX_HEAT: self._aux_heat,
                ATTR_LED: state.led,
            })
            self._available = True
        except DeviceException as ex:
            self._available = False
            _LOGGER.error("Got exception while fetching the state: %s", ex)

    @property
    def supported_features(self):
        """Return the list of supported features."""
        mode = SUPPORT_FLAGS
        if self._support_swing_mode:
            mode = mode | SUPPORT_SWING_MODE
        if self._support_aux_heat:
            mode = mode | SUPPORT_AUX_HEAT
        return mode

    @property
    def state(self) -> str:
        """Return the current state."""
        if self._turn_on or self._power_on:
            return self._current_operation
        else:
            return HVAC_MODE_OFF

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        return self._min_temp

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return self._max_temp

    @property
    def target_temperature_step(self):
        """Return the target temperature step."""
        return 1

    @property
    def should_poll(self):
        """Return the polling state."""
        return True

    @property
    def unique_id(self):
        """Return an unique ID."""
        return self._unique_id

    @property
    def name(self):
        """Return the name of the climate device."""
        return self._name

    @property
    def available(self):
        """Return true when state is known."""
        return self._available

    @property
    def device_state_attributes(self):
        """Return the state attributes of the device."""
        return self._state_attrs
    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return TEMP_CELSIUS

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._current_temperature
    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._target_temperature

    @property
    def hvac_mode(self):
        """Return new hvac mode ie. heat, cool, fan only."""
        return self._current_operation.lower()
    @property
    def hvac_modes(self):
        """Return the list of available hvac modes."""
        return self._operation_list.lower().split(',')

    @property
    def fan_mode(self):
        """Return the current fan mode."""
        return self._current_fan_mode.lower()
    @property
    def fan_modes(self):
        """Return the list of available fan modes."""
        return self._fan_mode_list.lower().split(',')

    @property
    def swing_mode(self):
        """Return the current swing setting."""
        return self._current_swing_mode.lower()
    @property
    def swing_modes(self):
        """List of available swing modes."""
        return self._swing_list.lower().split(',')

    @property
    def preset_mode(self) -> Optional[str]:
        return None
    @property
    def preset_modes(self) -> Optional[List[str]]:
        return None

    @property
    def is_aux_heat(self) -> Optional[bool]:
        return self._aux_heat    

    @asyncio.coroutine
    def async_set_temperature(self, **kwargs):
        """Set target temperature."""
        if kwargs.get(ATTR_TEMPERATURE) is not None:
            self._target_temperature = kwargs.get(ATTR_TEMPERATURE)
        if kwargs.get(ATTR_HVAC_MODE) is not None:
            self._current_operation = kwargs.get(ATTR_HVAC_MODE)
        yield from self._try_command()
    @asyncio.coroutine
    def async_set_swing_mode(self, swing_mode):
        """Set target temperature."""
        self._current_swing_mode = swing_mode
        yield from self._try_command()
    @asyncio.coroutine
    def async_set_fan_mode(self, fan_mode):
        """Set the fan mode."""
        self._current_fan_mode = fan_mode
        yield from self._try_command()
    @asyncio.coroutine
    def async_set_hvac_mode(self, hvac_mode):
        """Set operation mode."""
        self._current_operation = hvac_mode
        yield from self._try_command()
    @asyncio.coroutine
    def async_turn_aux_heat_on(self) -> None:
        """Turn auxiliary heater on."""
        self._aux_heat = True
        yield from self._try_command()
    @asyncio.coroutine
    def async_turn_aux_heat_off(self) -> None:
        """Turn auxiliary heater off."""
        self._aux_heat = False
        yield from self._try_command()

