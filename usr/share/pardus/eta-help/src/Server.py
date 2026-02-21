#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jul 29 23:47:11 2024

@author: fatih
"""

import json

import gi

gi.require_version("GLib", "2.0")
gi.require_version('Soup', '2.4')
from gi.repository import GLib, Gio, Soup


class Server(object):
    def __init__(self):

        self.session = Soup.Session(user_agent="application/json")

    def post(self, uri, dic):
        print("post")
        message = Soup.Message.new("POST", uri)
        message.set_request('Content-type:application/json', Soup.MemoryUse.COPY, json.dumps(dic).encode('utf-8'))
        message.request_headers.append('Content-type', 'application/json')
        self.session.send_async(message, None, self.on_finished, message)

    def on_finished(self, session, result, message):
        print("on_finished")
        try:
            input_stream = session.send_finish(result)
        except GLib.Error as error:
            if message.status_code == Soup.Status.SSL_FAILED:
                self.session.props.ssl_strict = False
            print("on_finished Error: {}, {}".format(error.domain, error.message))
            self.on_server_response(False, None, error_message="{}".format(error.message))
            return False

        status_code = message.status_code
        print("status_code: {}".format(status_code))

        if input_stream:
            if status_code == 404:
                self.on_server_response(False, None)  # Send to MainWindow
                return False
            data_input_stream = Gio.DataInputStream.new(input_stream)
            line, length = data_input_stream.read_line_utf8()

            self.on_server_response(True, json.loads(line))

        input_stream.close_async(GLib.PRIORITY_LOW, None, self._close_stream, None)

    def _close_stream(self, session, result, data):
        try:
            session.close_finish(result)
        except GLib.Error as error:
            print("_close_stream Error: {}, {}".format(error.domain, error.message))

