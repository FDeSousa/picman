import kivy
kivy.require('1.10.0')

from kivy.app import App

KV_TEMPLATES = 'ui'

class TestApp(App):
    kv_directory = KV_TEMPLATES
