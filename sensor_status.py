import appdaemon.plugins.hass.hassapi as hass
from enum import Enum, unique

#
# Lock Status
#
# Displays sensor status on Homeseer HS-W*200+ devices
# (LEDs 2-7 ignored for switches and fan controllers)
#


# valid colors:
#  Off = 0
#  Red = 1
#  Green = 2
#  Blue = 3
#  Magenta = 4
#  Yellow = 5
#  Cyan = 6
#  White = 7


class SensorStatus(hass.Hass):
  # LED config parameters
  LEDS = {x: x + 20 for x in range(1,8)}
  COLORS = {
    "Off",
    "Red",
    "Green",
    "Blue",
    "Magenta",
    "Yellow",
    "Cyan",
    "White",
  }

  def initialize(self):
    self.leds = {led: None for led in self.LEDS}
    self.INTERESTING_COLORS = self.COLORS - {self.args["bg_color"], "Off"}
    for led, sensors in self.args["sensors"].items():
      for sensor in sensors:
        self.listen_state(self.callback, sensor, led=led)
    self.set_leds()
    self.log("initialized")
    
  def callback(self, entity, attribute, old, new, kwargs):
    led = kwargs["led"]
    self.vlog(3, f"callback: {entity} {old}->{new} for led {kwargs['led']}")
    self.set_led(led, self.get_color(led))

  def device_id(self, display):
    return self.hass_get_entity(display)["device_id"]

  def get_color(self, led):
    if led not in self.args["sensors"]:
      return "Off"
    for sensor in self.args["sensors"].get(led):
      state = self.get_state(sensor)
      if not state:
        return "Off"
      if state in self.args["state_colors"]:
        return self.args["state_colors"][state]
    return self.args["bg_color"]

  def set_leds(self):
    for led in self.LEDS:
      self.set_led(led, self.get_color(led))
    # proactively disable if nothing interesting was found
    if not self.active():
      self.disable()

  def active(self):
    return any(c in self.INTERESTING_COLORS for c in self.leds.values())

  def set_led(self, led, color):
    # no-op
    if color == self.leds[led]:
      return
      
    self.log(f"setting led {led} to {color}")
    for display in self.args["displays"]:
      self.vlog(2, f"setting led {led} to {color} on {display}")
      self.set_device(display, self.LEDS[led], color)

    # handle activation
    active_before = self.active()
    self.leds[led]=color
    active_after = self.active()
    if active_after and not active_before:
      self.enable()
    if active_before and not active_after:
      self.disable()

  def enable(self):
    self.log("enabling displays")
    for display in self.args["displays"]:
      self.vlog(1, f"enabling display {display} ({self.device_id(display)})")
      self.set_device(display, 13, True)

  def disable(self):
    self.log("disabling displays")
    for display in self.args["displays"]:
      self.vlog(1, f"disabling display {display}")
      self.set_device(display, 13, False)

  def set_device(self, display, parameter, value):
    self.log(f"setting parameter {parameter} to {value} for {display}")
    device_id = self.device_id(display)
    self.call_service(
      "zwave_js/set_config_parameter",
      device_id=device_id,
      parameter=parameter,
      value=value,
    )

  #
  # logging utility
  #
  def vlog(self, level, msg, *args):
    if level <= self.args.get("vlog", 0):
      self.log(f"VLOG({level}): {msg}", *args, level="INFO")