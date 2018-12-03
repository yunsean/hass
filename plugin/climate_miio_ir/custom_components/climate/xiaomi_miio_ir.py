"""
Support for Xiaomi Mi Home Air Conditioner Companion (AC Partner)

For more details about this platform, please refer to the documentation
https://home-assistant.io/components/climate.xiaomi_miio
"""
import logging
import asyncio
import json
from functools import partial
from datetime import timedelta
import voluptuous as vol

from homeassistant.core import callback
from homeassistant.components.climate import (
    ClimateDevice, PLATFORM_SCHEMA, ATTR_OPERATION_MODE, SUPPORT_ON_OFF, SUPPORT_AWAY_MODE, SUPPORT_HOLD_MODE,
    SUPPORT_TARGET_TEMPERATURE, SUPPORT_OPERATION_MODE, SUPPORT_FAN_MODE, SUPPORT_AUX_HEAT, 
    SUPPORT_SWING_MODE, )
from homeassistant.const import (
    TEMP_CELSIUS, ATTR_TEMPERATURE, ATTR_UNIT_OF_MEASUREMENT, 
    CONF_NAME, CONF_HOST, CONF_TOKEN, )
from homeassistant.exceptions import PlatformNotReady
from homeassistant.helpers.event import async_track_state_change
import homeassistant.helpers.config_validation as cv
from homeassistant.util.json import load_json, save_json

_LOGGER = logging.getLogger(__name__)
CONFIGURATION_FILE = '.climate_ir.conf'
CONFIG_FILE_PATH = ""
ATTR_DEVICES = 'climates'
CONFIG_FILE = {ATTR_DEVICES: {}}

REQUIREMENTS = ['python-miio>=0.4.0']
DEPENDENCIES = ['sensor']

DEFAULT_NAME = 'Xiaomi AC Companion With Ir'

ATTR_SWING_MODE = 'swing_mode'
ATTR_FAN_SPEED = 'fan_speed'
ATTR_LOAD_POWER = 'load_power'
ATTR_AUX_HEAT = 'aux_heat'

SUPPORT_FLAGS = (SUPPORT_ON_OFF |
                 SUPPORT_TARGET_TEMPERATURE |
                 SUPPORT_FAN_MODE |
                 SUPPORT_OPERATION_MODE)

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
    
    global CONFIG_FILE
    global CONFIG_FILE_PATH
    CONFIG_FILE_PATH = hass.config.path(CONFIGURATION_FILE)
    CONFIG_FILE = load_json(CONFIG_FILE_PATH)    
    try:
        save_json(CONFIG_FILE_PATH, CONFIG_FILE)
    except HomeAssistantError:
        _LOGGER.error("load climate's states failed")
    if CONFIG_FILE == {}:
        CONFIG_FILE[ATTR_DEVICES] = {}

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
        unique_id = "{}-{}-ir".format(model, device_info.mac_address)
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
        self._support_away_mode = True if ('away-mode-on' in  instructsMap and 'away-mode-off' in instructsMap) else False
        self._support_hold_mode = True if ('hold-mode-on' in  instructsMap and 'hold-mode-off' in instructsMap) else False
        self._support_swing_mode = True if (swing_list != None and len(swing_list) > 1) else False

        self._available = False
        self._state_attrs = {
            ATTR_LOAD_POWER: None,
            ATTR_TEMPERATURE: None,
            ATTR_SWING_MODE: None,
            ATTR_FAN_SPEED: None,
            ATTR_OPERATION_MODE: None,
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
        
        try:
            state = CONFIG_FILE[ATTR_DEVICES][self._unique_id]
            self._current_swing_mode = state['swing_mode']
            self._current_operation = state['operation']
            self._current_fan_mode = state['fan_mode']
            self._target_temperature = state['temperature']
            self._aux_heat = state['aux_heat']
        except:
            _LOGGER.error("load latest state failed.")

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
        global CONFIG_FILE
        global CONFIG_FILE_PATH
        data = {"operation": self._current_operation,
            "fan_mode": self._current_fan_mode,
            "swing_mode": self._current_swing_mode,
            "temperature": self._target_temperature,
            "aux_heat": self._aux_heat}
        CONFIG_FILE[ATTR_DEVICES][self._unique_id] = data
        try:
            save_json(CONFIG_FILE_PATH, CONFIG_FILE)
        except HomeAssistantError:
            _LOGGER.error("save climate's states failed")

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
            _LOGGER.error("Got new state: %s", state)
            self._state_attrs.update({
                ATTR_LOAD_POWER: state.load_power,
                ATTR_TEMPERATURE: self._target_temperature,
                ATTR_SWING_MODE: self._current_swing_mode,
                ATTR_FAN_SPEED: self._current_fan_mode,
                ATTR_OPERATION_MODE: self._current_operation,
                ATTR_AUX_HEAT: self._aux_heat,
            })
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
        if self._support_away_mode:
            mode = mode | SUPPORT_AWAY_MODE
        if self._support_hold_mode:
            mode = mode | SUPPORT_HOLD_MODE
        return mode
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
        return True
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
    def current_operation(self):
        """Return current operation ie. heat, cool, idle."""
        return self._current_operation
    @property
    def operation_list(self):
        """Return the list of available operation modes."""
        return self._operation_list.split(',')
    @property
    def current_fan_mode(self):
        """Return the current fan mode."""
        return self._current_fan_mode
    @property
    def fan_list(self):
        """Return the list of available fan modes."""
        return self._fan_mode_list.split(',')
    @property
    def is_on(self) -> bool:
        """Return True if the entity is on."""
        return self._turn_on or self._power_on
        
    @asyncio.coroutine
    def async_turn_aux_heat_on(self):
        """Turn auxiliary heater on.
        This method must be run in the event loop and returns a coroutine.
        """
        self._aux_heat = True
        result = yield from self._try_command()  
    @asyncio.coroutine     
    def async_turn_aux_heat_off(self):
        """Turn auxiliary heater off.
        This method must be run in the event loop and returns a coroutine.
        """
        self._aux_heat = False
        result = yield from self._try_command() 

    @asyncio.coroutine   
    def async_turn_away_mode_on(self):
        """Turn away mode on.

        This method must be run in the event loop and returns a coroutine.
        """
        self._try_command('away-mode-on')
    @asyncio.coroutine   
    def async_turn_away_mode_off(self):
        """Turn away mode off.

        This method must be run in the event loop and returns a coroutine.
        """
        self._try_command('away-mode-off') 
         
    @asyncio.coroutine   
    def async_set_hold_mode(self, hold_mode):
        """Set new target hold mode.

        This method must be run in the event loop and returns a coroutine.
        """
        if hold_mode:
            self._try_command('hold-mode-on')
        else:
            self._try_command('hold-mode-on')  
        
    @asyncio.coroutine
    def async_set_temperature(self, **kwargs):
        """Set target temperature."""
        if kwargs.get(ATTR_TEMPERATURE) is not None:
            self._target_temperature = kwargs.get(ATTR_TEMPERATURE)
        if kwargs.get(ATTR_OPERATION_MODE) is not None:
            self._current_operation = kwargs.get(ATTR_OPERATION_MODE)
        yield from self._try_command()
    @asyncio.coroutine
    def async_set_swing_mode(self, swing_mode):
        """Set target temperature."""
        self._current_swing_mode = swing_mode
        yield from self._try_command()
    @asyncio.coroutine
    def async_set_fan_mode(self, fan):
        """Set the fan mode."""
        self._current_fan_mode = fan
        yield from self._try_command()
    @asyncio.coroutine
    def async_set_operation_mode(self, operation_mode):
        """Set operation mode."""
        self._current_operation = operation_mode
        yield from self._try_command()

    @property
    def current_swing_mode(self):
        """Return the current swing setting."""
        return self._current_swing_mode
    @property
    def swing_list(self):
        """List of available swing modes."""
        return self._swing_list.split(',')
