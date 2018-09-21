
# Copyright (c) 2013 Calin Crisan
# This file is part of motionEye.
#
# motionEye is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>. 

import datetime
import logging
import os
import re
import subprocess
import time
import utils

from tornado.ioloop import IOLoop
import paho.mqtt.client as mqtt

import config
import settings
import remote

def start():
    client = mqtt.Client()
    client.on_connect = _on_connect
    client.on_message = _on_message 
    client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)
    logging.debug("Connecting to MQTT broker '"+settings.MQTT_SERVER+ "' on port '"+str(settings.MQTT_PORT)+"' with username '"+settings.MQTT_USERNAME + "'" )
    client.connect(settings.MQTT_SERVER, settings.MQTT_PORT, 60)
    client.loop_start()
    return client

def stop(client):
    client.loop_stop()

def _on_connect(client, userdata, flags, rc):
    logging.debug("MQTT connected with result code "+str(rc))
    client.subscribe(settings.MQTT_MOTION_DETECTION_TOPIC)

def _on_message(client, userdata, msg):
    logging.debug("%s %s" % (msg.topic, str(msg.payload)))
    client.publish("/motion/log", "received message (%s): %s" % (msg.topic, msg.payload))
    if (msg.topic == settings.MQTT_MOTION_DETECTION_TOPIC):
        if (msg.payload.lower() == "off"):
            _set_all_motion_detection(False)
            return
        elif (msg.payload.lower() == "on"):
            _set_all_motion_detection(True)
            return

    logging.error("could not interpret message %s on topic %s" % (msg.payload, msg.topic))

def _set_all_motion_detection(enable):
    import motionctl

    def on_set_config_response(error=None):
        if error is None:
            logging.debug("Saving motion detection failed")
        else:
            logging.debug("Motion detection saved successfully")

    def on_get_config_response(remote_ui_config=None, error=None):
        remote_ui_config["motion_detection"] = enable
        remote.set_config(local_config, remote_ui_config, on_set_config_response)

    for camera_id in config.get_camera_ids():
        camera_config = config.get_camera(camera_id)
        if not utils.is_local_motion_camera(camera_config):
            local_config = config.get_camera(camera_id)
            remote.get_config(local_config, on_get_config_response)
            logging.debug('motion detection %s by config for remote camera with id %s' % (str(enable), camera_id))
        elif not camera_config['@motion_detection']:
            logging.debug('motion detection %s by config for local camera with id %s' % (str(enable), camera_id))
            motionctl.set_motion_detection(camera_id, enable)
        else:
            logging.error("Couldn't categorize camera with id %s" % camera_id)
