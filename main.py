import kivy
kivy.require('1.10.1')

from contextlib import contextmanager
from io import BytesIO
from collections import OrderedDict

from kivy.app import App
from kivy.clock import Clock, mainthread
from kivy.core.image import Image as CoreImage
from kivy.graphics import Color, Rectangle
from kivy.loader import Loader
from kivy.metrics import dp, sp
from kivy.properties import StringProperty, ListProperty, ObjectProperty, NumericProperty, ReferenceListProperty
from kivy.uix.behaviors import FocusBehavior
from kivy.uix.behaviors.compoundselection import CompoundSelectionBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.scatter import Scatter
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.slider import Slider
from kivy.uix.splitter import Splitter
from kivy.uix.stacklayout import StackLayout
from kivy.uix.tabbedpanel import TabbedPanel
from kivy.uix.textinput import TextInput

from kivy.garden.simpletablelayout import SimpleTableLayout

import datetime
import exifparse
import multiprocessing
import os
import PIL
import psutil
import rawpy
import threading


class PropertyLabel(Label):
    bcolor = ListProperty([1, 1, 1, 1])
    colspan = 1
    rowspan = 1
    padding_x = NumericProperty(5)
    padding_y = NumericProperty(5)
    padding = ReferenceListProperty(padding_x, padding_y)
    font_size = NumericProperty(20)

    def __init__(self, **kwargs):
        self.colspan = kwargs.pop('colspan', 1)
        self.rowspan = kwargs.pop('rowspan', 1)
        super().__init__(**kwargs)
        self.bind(size=self.setter('text_size'))


class PropertyText(TextInput):
    bcolor = ListProperty([1, 1, 1, 1])
    colspan = 1
    rowspan = 1
    font_size = NumericProperty(20)

    def __init__(self, **kwargs):
        self.colspan = kwargs.pop('colspan', 1)
        self.rowspan = kwargs.pop('rowspan', 1)
        super().__init__(**kwargs)


class Sidebar(Splitter):
    layout_content = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.layout_content:
            self.layout_content.bind(
                minimum_height=self.layout_content.setter('height'))


class MetadataTable(SimpleTableLayout):
    pass


class ImageLibraryScreen(Screen):
    pass


class SelectableGrid(FocusBehavior, CompoundSelectionBehavior, GridLayout):
    metadata_layout = None

    def __init__(self, **kwargs):
        GridLayout.__init__(self, **kwargs)

    def keyboard_on_key_down(self, window, keycode, text, modifiers):
        if super().keyboard_on_key_down(window, keycode, text, modifiers):
            return True
        if self.select_with_key_down(window, keycode, text, modifiers):
            return True
        return False

    def keyboard_on_key_up(self, window, keycode):
        if super().keyboard_on_key_up(window, keycode):
            return True
        if self.select_with_key_up(window, keycode):
            return True
        return False

    def add_widget(self, widget):
        widget.bind(on_touch_down=self.button_touch_down
            # , on_touch_up=self.button_touch_up
                    )
        return super().add_widget(widget)

    def button_touch_down(self, button, touch):
        if button.collide_point(*touch.pos):
            self.select_with_touch(button, touch)

    def button_touch_up(self, button, touch):
        if not (button.collide_point(*touch.pos) or self.touch_multiselect):
            self.deselect_node(button)

    @mainthread
    def select_node(self, node):
        try:
            if hasattr(node, 'select'):
                node.select()
                node.selected = True
        except Exception as e:
            print('SelectableGrid.select_node(node={}); node.select() failed. Exception: {}'.format(node, e))

        try:
            if hasattr(node, 'parent'):
                if hasattr(node.parent, 'select'):
                    node.parent.select()
                    node.parent.selected = True
        except Exception as e:
            print('SelectableGrid.select_node(node={}); node.parent.select() failed. Exception: {}'.format(node, e))

        return super().select_node(node)

    @mainthread
    def deselect_node(self, node):
        try:
            if hasattr(node, 'deselect'):
                node.deselect()
                node.selected = False
        except Exception as e:
            print('SelectableGrid.deselect_node(node={}); node.deselect() failed. Exception: {}'.format(node, e))

        try:
            if hasattr(node, 'parent'):
                if hasattr(node.parent, 'deselect'):
                    node.parent.deselect()
                    node.parent.selected = False
        except Exception as e:
            print('SelectableGrid.deselect_node(node={}); node.parent.deselect() failed. Exception: {}'.format(node, e))

        super().deselect_node(node)

    @mainthread
    def on_selected_nodes(self, grid, nodes):
        if self.metadata_layout is None:
            # Get the layout, which is branched off on the root screen
            # parent 0 is the scrollview for the grid
            # parent 1 is the boxlayout holding the main screen panel
            # parent 2 is the boxlayout holding the image screen layout
            # parent 3 is the image screen itself, which holds the ids
            print('='*80)
            print('on_selected_nodes')
            print('self={} ({}): {}; {}\n'.format(self.id, self, self.children, self.ids))
            print('self.parent={} ({}): {}; {}\n'.format(self.parent.id, self.parent, self.parent.children, self.parent.ids))
            print('self.parent.parent={} ({}): {}; {}\n'.format(self.parent.parent.id, self.parent.parent, self.parent.parent.children, self.parent.parent.ids))
            print('self.parent.parent.parent={} ({}): {}; {}\n'.format(self.parent.parent.parent.id, self.parent.parent.parent, self.parent.parent.parent.children, self.parent.parent.parent.ids))
            print('self.parent.parent.parent.parent={} ({}): {}; {}\n'.format(self.parent.parent.parent.parent.id, self.parent.parent.parent.parent, self.parent.parent.parent.parent.children, self.parent.parent.parent.parent.ids))
            print('='*80)
            self.metadata_layout = self.parent.parent.parent.parent.ids.metadata_layout

        metadata_table = None

        try:
            metadata_table = self.metadata_layout.children[-1].children[-1]
            while metadata_table.children:
                metadata_table.remove_widget(metadata_table.children[0])
        except Exception as e:
            print('{}.on_selected_nodes(grid={}, nodes={}); Caught {}: {}'
                  .format(self.__class__.__name__, grid, nodes,
                          e.__class__.__name__, e))

        if not metadata_table:
            metadata_table = MetadataTable(id='metadata_table', cols=1, rows=1, size_hint=(1.0, None))
            self.metadata_layout.add_widget(metadata_table)

        if len(nodes) == 1:
            # Single node selected, display the metadata
            metadata_list = nodes[0].metadata
            metadata_table.cols = 3
            metadata_table.rows = (len(metadata_list) +
                sum(sum(i.rows for i in v if i) for v in metadata_list.values()))
            metadata_table.height = metadata_table.rows * sp(20)

            for category, properties in metadata_list.items():
                metadata_table.add_widget(PropertyLabel(text=category, colspan=3, bold=True, halign='center', valign='middle', font_size=30))
                for prop in properties:
                    try:
                        metadata_table.add_widget(PropertyLabel(text=f"{prop.name}:", bold=True, size_hint=(1.0, 1.0), rowspan=prop.rows, halign='right', valign='top'))
                    except:
                        print(f'Exception raised while adding label for "{prop.name}" data "{prop.data}"')
                        print(f'Properties:({", ".join(properties)})')
                        raise

                    try:
                        metadata_table.add_widget(PropertyText(text=prop.data, multiline=True, rowspan=prop.rows, colspan=2))
                    except:
                        print(f'Exception raised while adding text input for "{prop.name}" data "{prop.data}"')
                        print(f'Properties:({", ".join(str(p) for p in properties)})')
                        raise
        elif len(nodes) == 0:
            # No nodes selected, display defaults
            metadata_table.rows = 1
            metadata_table.cols = 1
            metadata_table.add_widget(
                PropertyLabel(text="No nodes selected",
                              size_hint=(1.0, None),
                              bcolor=[1, 0, 0, 1],
                              halign='center',
                              valign='middle',
                              font_size=30))
        else:
            # More than one node selected, display how many
            metadata_table.rows = 1
            metadata_table.cols = 1
            metadata_table.add_widget(
                PropertyLabel(text=f"{len(nodes)} nodes selected",
                              size_hint=(1.0, None),
                              bcolor=[1, 0, 0, 1],
                              halign='center',
                              valign='middle',
                              font_size=30))

        self.metadata_layout.do_layout()


class Image(Image):
    def on_touch_down(self, touch):
        pass


class SelectablePicture(BoxLayout):
    # Properties to control the background colour of the widget
    r = NumericProperty(0.3)
    g = NumericProperty(0.5)
    b = NumericProperty(0.7)
    a = NumericProperty(0)
    background_colour = ReferenceListProperty(r, g, b, a)
    # Properties to control the border colour of the widget
    border_r = NumericProperty(0.75)
    border_g = NumericProperty(0.75)
    border_b = NumericProperty(0.75)
    border_a = NumericProperty(0)
    border_colour = ReferenceListProperty(border_r, border_g, border_b, border_a)
    # Properties to control the border sizing of the widget
    border_x = NumericProperty(0)
    border_y = NumericProperty(0)
    border_width = NumericProperty(0)
    border_height = NumericProperty(0)
    border = ReferenceListProperty(border_x, border_y, border_width, border_height)
    border_thickness = NumericProperty(1)
    # Texture of the image to display
    texture = ObjectProperty(None)
    # Filename source of the image
    source = StringProperty(None)
    # Metadata container for the image
    metadata = None

    def __init__(self, source, metadata, texture=None, **kwargs):
        super().__init__(source=source, texture=texture, **kwargs)
        self.metadata = metadata
        self.deselect()

    def select(self):
        # self.background_colour = (0, 0, 1, 1)
        self.a = 1
        # self.border_colour = (1, 1, 1, 1)
        self.border_a = 1

    def deselect(self):
        # self.background_colour = (0, 0, 0, 0)
        self.a = 0
        # self.border_colour = (0, 0, 0, 0)
        self.border_a = 0


@contextmanager
def report_memory_usage(block_name):
    proc = psutil.Process(os.getpid())
    start_bytes = proc.memory_info().rss
    print('[{}] Start of [{}]: {} MB'.format(
          datetime.datetime.now(), block_name, start_bytes / float(2 ** 20))
    )

    try:
        yield proc
    finally:
        end_bytes = proc.memory_info().rss
        print('[{}] End of [{}]: {} MB (Delta: {} MB) '.format(
              datetime.datetime.now(), block_name, end_bytes / float(2 ** 20),
              (end_bytes - start_bytes) / float(2 ** 20)
            )
        )


def _load_jpg_callback(filename):
    def action(filename):
        return Image(source=filename, size_hint=(1.0, 1.0))
    process = multiprocessing.Process(target=action, args=(filename,), daemon=True)
    process.start()
    return process


def _post_jpg_callback(process):
    process.join()


def _load_converted_callback(filename):
    pass


def _post_converted_callback(process):
    pass


def _load_raw_callback(filename):
    pass


def _post_raw_callback(process):
    pass


def load_image_file_metadata(filename):
    parser = exifparse.CategorisedExifData(filename)
    return parser.categorised


class KivyPILApp(App):
    title = "Photo Viewer"
    stop_event = threading.Event()

    def _load_jpg(self, filename):
        with report_memory_usage('Original JPG'):
            self.add_image_with_label(filename)

    def _convert_jpg(self, filename):
        with report_memory_usage('Converted JPG'):
            data = BytesIO()
            PIL.Image.open(filename).convert('1').save(data, format='png')
            data.seek(0)
            im = CoreImage(BytesIO(data.read()), ext='png')

            self.add_image_with_label(filename, im.texture)

    def _load_raw(self, filename):
        with report_memory_usage('RAW'):
            raw = rawpy.imread(filename)
            rgb = raw.postprocess()

            data = BytesIO()
            PIL.Image.fromarray(rgb).save(data, format='png')
            data.seek(0)
            im = CoreImage(BytesIO(data.read()), ext='png')

            self.add_image_with_label(filename, im.texture)

    @mainthread
    def add_image_with_label(self, filename, texture=None):
        metadata = load_image_file_metadata(filename)
        picture = SelectablePicture(filename, metadata, texture)
        self.root.current_screen.ids.image_layout.add_widget(picture)

    @mainthread
    def add_proxyimage_with_label(self, filename, proxyimage):
        picture = SelectablePicture(filename, None, proxyimage)

    def build(self):
        sm = ScreenManager()
        sm.add_widget(ImageLibraryScreen(name=ImageLibraryScreen.__name__))
        return sm

    def _load_callback(self, filename):
        print('_load_callback(filename={})'.format(filename))
        with report_memory_usage('Load callback converting JPG'):
            data = BytesIO()
            PIL.Image.open(filename).convert('1').save(data, format='png')
            data.seek(0)
            im = CoreImage(BytesIO(data.read()), ext='png')
            return im

    def _post_callback(self, im):
        print('_post_callback(im={})'.format(im))
        return im.texture

    def _on_load(self, *args, **kwargs):
        print('_on_load(*args={}, **kwargs={})'.format(args, kwargs))

    def on_start(self, **kwargs):
        image_dir = os.path.join(os.path.dirname(__file__), 'images')
        image_jpg_original = os.path.join(image_dir, 'DSCF2364.JPG')
        image_raf_original = os.path.join(image_dir, 'DSCF2364.RAF')

        # print('Trying Loader.image')
        proxyImage = Loader.image(image_jpg_original, load_callback=self._load_callback, post_callback=self._post_callback)
        # print('Binding on_load')
        # proxyImage.bind(on_load=self._on_load)
        # print('Going back to regularly scheduled programming')

        frame_wait = 0

        frame_wait += 1
        Clock.schedule_once(lambda dt: self._load_jpg(image_jpg_original), frame_wait)
        frame_wait += 2
        Clock.schedule_once(lambda dt: self._convert_jpg(image_jpg_original), frame_wait)
        # frame_wait += 4
        # Clock.schedule_once(lambda dt: self._load_raw(image_raf_original), frame_wait)
        # frame_wait += 8

    def on_stop(self):
        self.stop_event.set()

    def on_pause(self):
        return True

    def on_resume(self):
        return True


if __name__ == "__main__":
    KivyPILApp().run()
