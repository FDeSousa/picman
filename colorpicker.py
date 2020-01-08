from kivy.app import App
from kivy.uix.colorpicker import ColorPicker
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import ObjectProperty

class ColorPickerApp(App):
    title = "Color Picker Example"


class ColorPickerLayout(BoxLayout):
    ti = ObjectProperty(None)
    def color_change(self, r=None, g=None, b=None, a=None):
        print('Called color_change')


if __name__ == '__main__':
    ColorPickerApp().run()
