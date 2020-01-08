from collections import OrderedDict
from datetime import datetime
import math
import exif

def metering_mode_to_description(mm):
    metering_modes = {
        0: 'Unknown',
        1: 'Average',
        2: 'Center-weighted average',
        3: 'Spot',
        4: 'Multi-spot',
        5: 'Pattern',
        6: 'Partial',
        255: 'Other'
    }
    return metering_modes.get(mm) or ""

def exposure_program_to_description(ep):
    exposure_modes = {
        0: 'Not defined',
        1: 'Manual',
        2: 'Normal program',
        3: 'Aperture priority',
        4: 'Shutter priority',
        5: 'Creative program',
        6: 'Action program',
        7: 'Portrait mode',
        8: 'Landscape mode',
    }
    return exposure_modes.get(ep) or ""

def exposure_time_to_fraction_of_second(et):
    return (f"{et:.1f}" if et >= 0.1 else f"1/{1/et:.1f}").replace(".0", "")

def photographic_sensitivity_to_iso(ps):
    return f"ISO {ps}"

def f_number_to_aperture(fn):
    return f"\u0192/{fn:.1f}".replace(".0", "")

def exposure_bias_value_to_exposure_bias(ebv):
    return f"{ebv:.1f} ev".replace(".0", "")

def focal_length_to_focal_length_mm(fl):
    return f"{fl:.1f}mm".replace(".0", "")

def pixel_dimensions_to_pixel_size(x, y):
    return f"{x} x {y}\n({round(x*y/10**6):.1f} MP)"

def pixel_dimensions_to_aspect_ratio(x, y):
    gcd = math.gcd(x, y)
    return f"{x/gcd:.1f}:{y/gcd:.1f}".replace(".0", "")

def exif_datetime_to_datetime(edt):
    return (datetime
        .strptime(edt, '%Y:%m:%d %H:%M:%S')
        .strftime('%A %d %B %Y\n%H:%M:%S'))

def flash_to_description(f):
    flash_modes = {
        0x0000: 'Flash did not fire',
        0x0001: 'Flash fired',
        0x0005: 'Strobe return light not detected',
        0x0007: 'Strobe return light detected',
        0x0009: 'Flash fired, compulsory flash mode',
        0x000d: 'Flash fired, compulsory flash mode, return light not detected',
        0x000f: 'Flash fired, compulsory flash mode, return light detected',
        0x0010: 'Flash did not fire, compulsory flash mode',
        0x0018: 'Flash did not fire, auto mode',
        0x0019: 'Flash fired, auto mode',
        0x001d: 'Flash fired, auto mode, return light not detected',
        0x001f: 'Flash fired, auto mode, return light detected',
        0x0020: 'No flash function',
        0x0041: 'Flash fired, red-eye reduction mode',
        0x0045: 'Flash fired, red-eye reduction mode, return light not detected',
        0x0047: 'Flash fired, red-eye reduction mode, return light detected',
        0x0049: 'Flash fired, compulsory flash mode, red-eye reduction mode',
        0x004d: 'Flash fired, compulsory flash mode, red-eye reduction mode, return light not detected',
        0x004f: 'Flash fired, compulsory flash mode, red-eye reduction mode, return light detected',
        0x0059: 'Flash fired, auto mode, red-eye reduction mode',
        0x005d: 'Flash fired, auto mode, return light not detected, red-eye reduction mode',
        0x005f: 'Flash fired, auto mode, return light detected, red-eye reduction mode',
    }
    # 16 (0x10) (0b10000)
    return flash_modes.get(f, f"Unknown: {f} (0x{f:02X}) (0b{f:02b})")


class ExifDataItem:
    __name = None
    __data = None
    __cols = None
    __rows = None

    def __init__(self, name, data, cols=1, rows=1):
        self.__name = name
        self.__data = data
        self.__cols = cols
        self.__rows = rows

    @property
    def name(self):
        return self.__name

    @property
    def data(self):
        return self.__data

    @property
    def cols(self):
        return self.__cols

    @property
    def rows(self):
        return self.__rows

    def __str__(self):
        return f"ExifDataItem {{name=[{self.name}], data=[{self.data}], cols=[{self.cols}], rows=[{self.rows}]}}"


class ExifParserBase:
    alias = None
    function = None
    cols = 1
    rows = 1

    def __init__(self, alias=None, function=None, cols=1, rows=1):
        self.alias = alias
        self.function = function
        self.cols = cols
        self.rows = rows


class ExifParserItem(ExifParserBase):
    name = None

    def __init__(self, name, alias=None, function=None, cols=1, rows=1):
        super().__init__(alias, function, cols, rows)
        self.name = name

    def parse(self, exif_data):
        data = exif_data.get(self.name)

        if data is None:
            return None

        if self.function is not None:
            data = self.function(data)

        del exif_data[self.name]

        return ExifDataItem(self.alias or self.name, data, self.cols, self.rows)


class ExifParserPair(ExifParserBase):
    name_a = None
    name_b = None

    def __init__(self, names, alias, function=None, cols=1, rows=1):
        super().__init__(alias, function, cols, rows)
        if isinstance(names, (tuple, list)) and len(names) == 2:
            self.name_a, self.name_b = names
        else:
            raise Exception('Parameter "names" must be a tuple or list of two items only')

    def parse(self, exif_data):
        data_a = exif_data.get(self.name_a)
        data_b = exif_data.get(self.name_b)

        if data_a is None and data_b is None:
            return None

        if self.function is not None:
            data = self.function(data_a, data_b)
        else:
            data = (data_a, data_b)

        del exif_data[data_a]
        del exif_data[data_b]

        return ExifDataItem(self.alias, data, self.cols, self.rows)


_Categories = OrderedDict([
    ('Camera', (
        ExifParserItem('make', 'Make'),
        ExifParserItem('model', 'Model'),
        ExifParserItem('software', 'Software', rows=2),
    )),
    ('Lens', (
        ExifParserItem('lens_make', 'Make'),
        ExifParserItem('lens_model', 'Model'),
        ExifParserItem('lens_serial_number', 'Serial Number'),
        ExifParserItem('lens_specification', 'Specification'),
        ExifParserItem('max_aperture_value', 'Max. Aperture', f_number_to_aperture),
    )),
    ('Photo', (
        ExifParserItem('focal_length', 'Focal Length', focal_length_to_focal_length_mm),
        ExifParserItem('focal_length_in_35mm_film', 'Focal Length (35mm)', focal_length_to_focal_length_mm),
        ExifParserItem('f_number', 'Aperture', f_number_to_aperture),
        ExifParserItem('photographic_sensitivity', 'ISO', photographic_sensitivity_to_iso),
        ExifParserItem('exposure_time', 'Exposure Time', exposure_time_to_fraction_of_second),
        ExifParserItem('exposure_program', 'Exposure Program', exposure_program_to_description),
        ExifParserItem('exposure_bias_value', 'Exposure Bias', exposure_bias_value_to_exposure_bias),
        ExifParserItem('metering_mode', 'Metering Mode', metering_mode_to_description),
        ExifParserItem('flash', 'Flash', flash_to_description, rows=2),
    )),
    ('File', (
        # ExifParserItem('color_space', 'Color Profile'),
        ExifParserPair(('pixel_x_dimension', 'pixel_y_dimension'), 'Pixel Size', pixel_dimensions_to_pixel_size, rows=2),
        ExifParserPair(('pixel_x_dimension', 'pixel_y_dimension'), 'Aspect Ratio', pixel_dimensions_to_aspect_ratio),
        ExifParserItem('datetime_original', 'Date', exif_datetime_to_datetime, rows=2),
    )),
    # ('GPS', (
    # ))
])


class CategorisedExifData:
    def __init__(self, filename):
        self.__categorised = OrderedDict()
        with open(filename, 'rb') as image_file:
            exif_data = exif.Image(image_file)
            if exif_data.has_exif:
                self.__parse(exif_data)
                self.__print(exif_data)

    def __parse(self, exif_data):
        for category_name, items in _Categories.items():
            self.__categorised[category_name] = [e for e in (i.parse(exif_data) for i in items) if e]

    def __print(self, exif_data):
        pass

    @property
    def categorised(self):
        return self.__categorised
