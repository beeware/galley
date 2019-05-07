import os
import sys
from collections import namedtuple

######################################################################
# Output message types
######################################################################

FileChange = namedtuple('FileChange', ['new', 'modified'])


def project_visitor(on_dir, on_file):
    """A filesystem visitor factory

    Returns os.walk-compatible visitor functions that will
    invoke on_dir(dirname, data) and on_file(dirname, filename, data)
    whenever a new directory or file is detected, respectively.
    """
    def _visitor(data, dirname, filesindir):
        prune = []
        on_dir(dirname, data)
        for filename in filesindir:
            if os.path.isdir(os.path.join(dirname, filename)):
                if filename in ('.git', '.hg') or filename.endswith('.egg-info') or filename.startswith('_'):
                    prune.append(filename)
            else:
                name, ext = os.path.splitext(filename)
                if ext in ('.txt', '.rst'):
                    on_file(dirname, filename, data)
                else:
                    prune.append(filename)

        for filename in prune:
            filesindir.remove(filename)

    return _visitor


class Monitor(object):
    "An object to track file modification data"
    def __init__(self):
        self.modification_time = {}
        self.reset()

    def reset(self):
        self.new_dirs = []
        self.modified_dirs = []

        self.new_files = []
        self.modified_files = []


def gather_dir(dirname, monitor):
    "The visitor utility method to catch directory modifications"
    stat = os.stat(dirname)
    current_mtime = stat.st_mtime
    if sys.platform == "win32":
        current_mtime -= stat.st_ctime

    try:
        old_mtime = monitor.modification_time[dirname][None]
        if old_mtime < current_mtime:
            monitor.modified_dirs.append(dirname)
    except KeyError:
        monitor.new_dirs.append(dirname)

    # Record the new modification time.
    monitor.modification_time.setdefault(dirname, {})[None] = current_mtime


def gather_file(dirname, filename, monitor):
    "The visitor utility method to catch file modifications"
    stat = os.stat(os.path.join(dirname, filename))
    current_mtime = stat.st_mtime
    if sys.platform == "win32":
        current_mtime -= stat.st_ctime

    try:
        old_mtime = monitor.modification_time[dirname][filename]
        if old_mtime < current_mtime:
            monitor.modified_files.append(os.path.join(dirname, filename))
    except KeyError:
        monitor.new_files.append(os.path.join(dirname, filename))

    # Record the new modification time.
    monitor.modification_time[dirname][filename] = current_mtime


def file_monitor(base_path, stop_event, output_queue):
    "The actual thread method that checks for file modifications"
    monitor = Monitor()
    os.walk(base_path, project_visitor(gather_dir, gather_file), monitor)

    while not stop_event.is_set():
        stop_event.wait(1.0)
        monitor.reset()
        os.walk(base_path, project_visitor(gather_dir, gather_file), monitor)

        if monitor.new_files or monitor.modified_files:
            output_queue.put(FileChange(monitor.new_files, monitor.modified_files))
