#!/usr/bin/python

from __future__ import print_function

import os
import platform
import datetime
import logging

logger = logging.getLogger(__name__)

# input in Py2.x calls eval, which is terrible, so use raw_input instead
try:
    read_input = raw_input
# In case we're in Py3.x, we don't have raw_input, so use input instead
except:
    read_input = input

Is_Windows = (platform.system() == "Windows")
Categories = ('Unknown', 'Image', 'Video')
File_Types = {
    '': Categories[0],
    '.RAF': Categories[1],
    '.JPG': Categories[1],
    '.MOV': Categories[2],
}

def creation_date(target):
    """
    Try to get the date that a file was created, falling back to when it was
    last modified if that isn't possible.
    See https://stackoverflow.com/a/39501288/1709587 for explanation.
    """
    stat = os.stat(target)
    result = None
    if Is_Windows:
        result = stat.st_ctime
    else:
        try:
            result = stat.st_birthtime
        except AttributeError:
            # Probably on Linux. No easy way to get creation dates here,
            # so we'll settle for when its content was last modified.
            result = stat.st_mtime

    return datetime.datetime.fromtimestamp(result)

def human_sizing(size_bytes):
    scales = ('', 'K', 'M', 'G', 'T', 'P', 'E')
    scaled_bytes = size_bytes
    scale_num = 0
    while scaled_bytes > 1024 and scale_num < len(scales) - 1:
        scaled_bytes /= 1024.0
        scale_num += 1
    return (scaled_bytes, scales[scale_num] + 'B')

def category_req_stdin(filename, extension):
    logging.info('File [%s] has extension [%s], which is uncategorised.', filename, extension)
    logging.info('Known categories: (%s)', ', '.join('[%s]%s' % (c[0], c[1:]) for c in Categories))
    category = read_input('What category should it be? (Default: [%s]%s)  ' % (Categories[0][0], Categories[0][1:]))

    if category:
        category = category.lower()
        for f in Categories:
            if f.lower().startswith(category):
                logging.info('Category for extension [%s] set as [%s]' % (extension, f))
                category = f
                break
        else:
            category = Categories[0]
    else:
        category = Categories[0]

    File_Types[extension] = category

    return category

def categorise_file_type(filename, category_req):
    (path, extension) = os.path.splitext(filename.upper())
    try:
        category = File_Types[extension]
    except KeyError:
        category = category_req(filename, extension)

    return (extension, category)

def make_dirs(target):
    logging.debug("Attempting to make path(s): %s", target)
    try:
        os.makedirs(target)
    except OSError as e:
        logging.debug("Error [%s] on attempting to make path(s): %s", e, target)
        return False
    else:
        return True

def copy_file_action(destination_fmt, do_action=True):
    def action(filepath, category, crdate):
        filename = os.path.basename(filepath)
        params = {'category': category, 'year': crdate.year, 'month': crdate.month, 'day': crdate.day}
        destination_folder = destination_fmt % params
        destination_path = os.path.join(destination_folder, filename)
        logging.debug('Copying [%s] to [%s]' % (filepath, destination_path))
        if do_action:
            make_dirs(destination_folder)
            # TODO! Copy the file across, creating the target folder
            pass
    return action

def walk_path(top, action, category_req):
    logging.info("Walking from top-level directory: %s" % top)
    total_files = 0
    total_bytes = 0

    categorised_files = dict()

    for root, dirs, files in os.walk(top):
        if files:
            file_count = len(files)
            total_files += file_count
            space_used = 0

            encountered_filetypes = dict()
            for name in files:
                filepath = os.path.normpath(os.path.join(root, name))
                space_used += os.path.getsize(filepath)
                total_bytes += space_used
                crdate = creation_date(filepath)

                logging.debug('File [%s] created on [%s]' % (filepath, crdate))

                (extension, category) = categorise_file_type(name, category_req)
                if category not in categorised_files:
                    categorised_files[category] = set()
                categorised_files[category].add(filepath)

                action(filepath, category, crdate)

            (human_size, scale) = human_sizing(space_used)

            logging.info("[%s] consumes %0.02f %s in %d files" % (root, human_size, scale, file_count))

    (human_size, scale) = human_sizing(total_bytes)
    logging.info("%s contains total of %d files consuming %0.02f %s" % (top, total_files, human_size, scale))

def import_files(src, dst, subdst_fmt, category_req=category_req_stdin):
    """
    Walk path src and copy files to dst/subdst_fmt

    src is the top-level directory to walk
    dst is the top-level target directory for copying
    subdst_fmt is the format for categorising imported files
    category_req is the optional function for requesting the file type categorisation
    """
    destination = os.path.join(dst, subdst_fmt)
    action = copy_file_action(destination)
    walk_path(src, action, category_req)

def main():
    logging.basicConfig(level=logging.DEBUG)
    src = "/Users/filipedesousa/Pictures/TestLibrary.aplibrary/Masters"
    dst = "/Users/filipedesousa/Documents/MediaLibrary"
    subdst_fmt = os.path.join("%(category)s", "%(year)d", "%(month)d", "%(day)d")
    # src = "/Volumes/Photos/Aperture Library.aplibrary/Masters"
    # dst = "/Volumes/Photos/Library"
    import_files(src, dst, subdst_fmt)

if __name__ == '__main__':
    main()
