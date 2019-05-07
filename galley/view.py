# -*- coding: UTF-8 -*-
"""A module containing a visual representation of the connection

This is the "View" of the MVC world.
"""
import os
from queue import Query, Empty
import threading
from tkinter import *
from tkinter.font import *
from tkinter.ttk import *
import tkinter.messagebox as tkMessageBox
from urllib.parse import urlparse
import webbrowser

from tkreadonly import ReadOnlyText

from galley import VERSION, NUM_VERSION
from galley.widgets import SimpleHTMLView, FileView
from galley.monitor import file_monitor, FileChange
from galley.worker import (
    sphinx_worker,
    ReloadConfig,
    BuildAll,
    BuildSpecific,
    Quit,
    Output,
    WarningOutput,
    Progress,
    InitializationStart,
    InitializationEnd,
    BuildStart,
    BuildEnd
)


def filename_normalizer(base_path):
    """Generate a fuction that will normalize a full path into a
    display name, by removing a common prefix.

    In most situations, this will be removing the current working
    directory.
    """
    def _normalizer(filename):
        if filename.startswith(base_path) and filename[len(base_path)] == os.sep:
            return filename[len(base_path)+1:]
        else:
            return filename
    return _normalizer



class MainWindow(object):
    def __init__(self, root, options):
        '''
        -----------------------------------------------------
        | main button toolbar                               |
        -----------------------------------------------------
        |       < ma | in content area >                    |
        |            |                                      |
        | File list  | File name                            |
        |            |                                      |
        -----------------------------------------------------
        |     status bar area                               |
        -----------------------------------------------------

        '''

        # Obtain and expand the current working directory.
        base_path = os.path.abspath(os.getcwd())
        self.base_path = os.path.normcase(base_path)

        # Create a filename normalizer based on the CWD.
        self.filename_normalizer = filename_normalizer(self.base_path)

        # Root window
        self.root = root
        self.root.title('Galley')
        self.root.geometry('1024x768')

        # Prevent the menus from having the empty tearoff entry
        self.root.option_add('*tearOff', FALSE)
        # Catch the close button
        self.root.protocol("WM_DELETE_WINDOW", self.cmd_quit)
        # Catch the "quit" event.
        self.root.createcommand('exit', self.cmd_quit)

        # The browsing history.
        self._history = []
        self._history_index = 0
        self._traversing_history = False

        # The default source file extension. This will be updated once we have
        # parsed the project config file.
        self.source_extension = '.rst'

        # Known warnings, indexed by source file.
        self.warning_output = {}

        # Setup the menu
        self._setup_menubar()

        # Set up the main content for the window.
        self._setup_button_toolbar()
        self._setup_main_content()
        self._setup_status_bar()

        # Now configure the weights for the root frame
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=0)
        self.root.rowconfigure(1, weight=1)
        self.root.rowconfigure(2, weight=0)

        # Set up a background worker thread to build docs.
        self.work_queue = Queue()
        self.results_queue = Queue()
        self.worker_thread = threading.Thread(target=sphinx_worker, args=(os.path.join(self.base_path, 'docs'), self.work_queue, self.results_queue))
        self.worker_thread.daemon = True
        self.worker_thread.start()

        # Set up a background monitor thread.
        self.stop_event = threading.Event()
        self.monitor_thread = threading.Thread(target=file_monitor, args=(os.path.join(self.base_path, 'docs'), self.stop_event, self.results_queue))
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

        # Requeue for another update in 40ms (24*40ms == 1s - so this is
        # as fast as we need to update to match human visual acuity)
        self.root.after(40, self.handle_background_tasks)


    ######################################################
    # Internal GUI layout methods.
    ######################################################

    def _setup_menubar(self):
        # Menubar
        self.menubar = Menu(self.root)

        # self.menu_Apple = Menu(self.menubar, name='Apple')
        # self.menubar.add_cascade(menu=self.menu_Apple)

        self.menu_file = Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_file, label='File')

        self.menu_help = Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_help, label='Help')

        # self.menu_Apple.add_command(label='Test', command=self.cmd_dummy)

        # self.menu_file.add_command(label='New', command=self.cmd_dummy, accelerator="Command-N")
        # self.menu_file.add_command(label='Close', command=self.cmd_dummy)

        self.menu_help.add_command(label='Open Documentation', command=self.cmd_galley_docs)
        self.menu_help.add_command(label='Open Galley project page', command=self.cmd_galley_page)
        self.menu_help.add_command(label='Open Galley on GitHub', command=self.cmd_galley_github)
        self.menu_help.add_command(label='Open BeeWare project page', command=self.cmd_beeware_page)

        # last step - configure the menubar
        self.root['menu'] = self.menubar

    def _setup_button_toolbar(self):
        '''
        The button toolbar runs as a horizontal area at the top of the GUI.
        It is a persistent GUI component
        '''

        # Main toolbar
        self.toolbar = Frame(self.root)
        self.toolbar.grid(column=0, row=0, sticky=(W, E))

        # Buttons on the toolbar
        self.back_button = Button(self.toolbar, text='◀', command=self.cmd_back, state=DISABLED)
        self.back_button.grid(column=0, row=0)

        self.forward_button = Button(self.toolbar, text='▶', command=self.cmd_forward, state=DISABLED)
        self.forward_button.grid(column=1, row=0)

        self.rebuild_all_button = Button(self.toolbar, text='Rebuild all', command=self.cmd_rebuild_all, state=DISABLED)
        self.rebuild_all_button.grid(column=2, row=0)

        self.rebuild_file_button = Button(self.toolbar, text='Rebuild', command=self.cmd_rebuild_file, state=DISABLED)
        self.rebuild_file_button.grid(column=3, row=0)

        self.reload_config_button = Button(self.toolbar, text='Reload', command=self.cmd_reload_config, state=DISABLED)
        self.reload_config_button.grid(column=4, row=0)

        self.toolbar.columnconfigure(0, weight=0)
        self.toolbar.rowconfigure(0, weight=0)

    def _setup_main_content(self):
        '''
        Sets up the main content area. It is a persistent GUI component
        '''

        # Main content area
        self.content = PanedWindow(self.root, orient=HORIZONTAL)
        self.content.grid(column=0, row=1, sticky=(N, S, E, W))

        # Create the tree/control area on the file frame
        self._setup_project_file_tree()

        # Create the output/viewer area on the content frame
        self._setup_html_area()

        # Set up weights for the left frame's content
        self.content.columnconfigure(0, weight=1)
        self.content.rowconfigure(0, weight=1)

        self.content.pane(0, weight=1)
        self.content.pane(1, weight=4)

    def _setup_project_file_tree(self):

        self.project_file_tree_frame = Frame(self.content)
        self.project_file_tree_frame.grid(column=0, row=0, sticky=(N, S, E, W))

        self.project_file_tree = FileView(self.project_file_tree_frame, normalizer=self.filename_normalizer, root=os.path.join(self.base_path, 'docs'))
        self.project_file_tree.grid(column=0, row=0, sticky=(N, S, E, W))

        # # The tree's vertical scrollbar
        self.project_file_tree_scrollbar = Scrollbar(self.project_file_tree_frame, orient=VERTICAL)
        self.project_file_tree_scrollbar.grid(column=1, row=0, sticky=(N, S))

        # # Tie the scrollbar to the text views, and the text views
        # # to each other.
        self.project_file_tree.config(yscrollcommand=self.project_file_tree_scrollbar.set)
        self.project_file_tree_scrollbar.config(command=self.project_file_tree.yview)

        # Setup weights for the "project_file_tree" tree
        self.project_file_tree_frame.columnconfigure(0, weight=1)
        self.project_file_tree_frame.columnconfigure(1, weight=0)
        self.project_file_tree_frame.rowconfigure(0, weight=1)

        # Handlers for GUI events
        self.project_file_tree.bind('<<TreeviewSelect>>', self.on_file_selected)

        self.content.add(self.project_file_tree_frame)

    def _setup_html_area(self):
        self.html_frame = Frame(self.content)
        self.html_frame.grid(column=1, row=0, sticky=(N, S, E, W))

        # Label for current file
        self.current_file = StringVar()
        self.current_file_label = Label(self.html_frame, textvariable=self.current_file)
        self.current_file_label.grid(column=0, row=0, columnspan=3, sticky=(W, E))

        # Code display area
        self.html = SimpleHTMLView(self.html_frame)
        self.html.grid(column=0, row=1, columnspan=3, sticky=(N, S, E, W))

        self.html.link_bind('<1>', self.on_link_click)

        # Warnings
        self.warnings_label = Label(self.html_frame, text='Warnings:')
        self.warnings_label.grid(column=0, row=2, pady=5, sticky=(N, E,))

        self.warnings = ReadOnlyText(self.html_frame, height=6)
        self.warnings.grid(column=1, row=2, pady=5, columnspan=2, sticky=(N, S, E, W,))
        self.warnings.tag_configure('warning', wrap=WORD, lmargin1=5, lmargin2=20, spacing1=2, spacing3=2)
        self.warnings_scrollbar = Scrollbar(self.html_frame, orient=VERTICAL)
        self.warnings_scrollbar.grid(column=2, row=2, pady=5, sticky=(N, S))
        self.warnings.config(yscrollcommand=self.warnings_scrollbar.set)
        self.warnings_scrollbar.config(command=self.warnings.yview)

        # Set up weights for the html frame's content
        self.html_frame.columnconfigure(0, weight=0)
        self.html_frame.columnconfigure(1, weight=1)
        self.html_frame.columnconfigure(2, weight=0)
        self.html_frame.rowconfigure(0, weight=0)
        self.html_frame.rowconfigure(1, weight=4)
        self.html_frame.rowconfigure(2, weight=1)

        self.content.add(self.html_frame)

    def _setup_status_bar(self):
        # Status bar
        self.statusbar = Frame(self.root)
        self.statusbar.grid(column=0, row=2, sticky=(W, E))

        # Current status
        self.run_status = StringVar()
        self.run_status_label = Label(self.statusbar, textvariable=self.run_status)
        self.run_status_label.grid(column=0, row=0, sticky=(W, E))
        self.run_status.set('Not running')

        # Progress bar; initially started, because we don't know how long initialization will take.
        self.progress_value = IntVar()
        # self.progress = Progressbar(self.statusbar, orient=HORIZONTAL, length=200, mode='indeterminate', maximum=100, variable=self.progress_value)
        self.progress = Progressbar(self.statusbar, orient=HORIZONTAL, length=200, mode='indeterminate')
        self.progress.grid(column=1, row=0, sticky=(W, E))

        # Main window resize handle
        self.grip = Sizegrip(self.statusbar)
        self.grip.grid(column=2, row=0, sticky=(S, E))

        # Set up weights for status bar frame
        self.statusbar.columnconfigure(0, weight=1)
        self.statusbar.columnconfigure(1, weight=0)
        self.statusbar.columnconfigure(2, weight=0)
        self.statusbar.rowconfigure(0, weight=0)

    ######################################################
    # Utility methods for controlling content
    ######################################################

    def show_file(self, filename, anchor=None):
        """Show the content of the nominated file.

        If specified, bookmark is the HTML href anchor to display. If the
        anchor isn't currently visible, the window will be scrolled until
        it is.
        """
        # TEMP: Rework into HTML view
        path, ext = os.path.splitext(filename)
        compiled_filename = path.replace(os.path.join(self.base_path, 'docs'), os.path.join(self.base_path, 'docs', '_build', 'json')) + '.fjson'

        # Set the filename label for the current file
        self.current_file.set(self.filename_normalizer(filename))

        try:
            # Update the html view; this means changing the displayed file
            # if necessary, and updating the current line.
            if filename != self.html.filename:
                self.html.filename = compiled_filename

            # self.html.anchor = anchor

            # Show the warnings panel (if needed)
            self._show_warnings(filename)

            # Add this file to history.
            path, ext = os.path.splitext(filename)
            path = path.replace('docs/_build/json', 'docs')

            # History traversal is a temporary operation. If we're traversing
            # history, we won't push this onto the stack... but only this once.
            # Traversal state is reset immediately afterwards.
            if not self._traversing_history:
                if self._history_index:
                    self.forward_button.configure(state=DISABLED)
                    self.back_button.configure(state=NORMAL)

                self._history = self._history[:self._history_index] + [path + self.source_extension]
                self._history_index = self._history_index + 1
            else:
                self._traversing_history = False

        except IOError:
            tkMessageBox.showerror(message='%s has not been compiled to HTML' % self.filename_normalizer(filename))

    def _show_warnings(self, filename):
        "Show the warnings output panel"

        # Build a list of all displayed warnings
        warnings = []
        # First, the global warnings
        for (lineno, warning) in self.warning_output.get(None, []):
            if lineno:
                warnings.append('○ Line %s: %s' % (lineno, warning))
            else:
                warnings.append('○ %s' % warning)

        # Then, the file specific warnings.
        for (lineno, warning) in self.warning_output.get(filename, []):
            if lineno:
                warnings.append('● Line %s: %s' % (lineno, warning))
            else:
                warnings.append('● %s' % warning)

        # If there are warnings, show the widget, and populate it.
        # Otherwise, hide the widget.
        self.warnings.delete('1.0', END)
        for warning in warnings:
            self.warnings.insert(END, warning, 'warning')
            self.warnings.insert(END, '\n')


    ######################################################
    # TK Main loop
    ######################################################

    def mainloop(self):
        self.root.mainloop()

    def handle_background_tasks(self):
        "Background queue handler"
        try:
            while True:
                result = self.results_queue.get(block=False)

                ########################
                # Output from the worker
                ########################

                if isinstance(result, Output):
                    self.run_status.set(result.message.capitalize())

                elif isinstance(result, WarningOutput):
                    if result.filename:
                        source_file = os.path.join(self.base_path, 'docs', result.filename)
                        self.project_file_tree.item(source_file, tags=['file', 'warning'])

                    # Archive the warning.
                    self.warning_output.setdefault(result.filename, []).append((result.lineno, result.message))

                elif isinstance(result, InitializationStart):
                    # Handle the "Start of sphinx init" message
                    self.progress.configure(mode='indeterminate', variable=None, maximum=None)
                    self.rebuild_all_button.configure(state=DISABLED)
                    self.rebuild_file_button.configure(state=DISABLED)
                    self.reload_config_button.configure(state=DISABLED)
                    self.progress.start()

                elif isinstance(result, InitializationEnd):
                    # Handle the "End of Sphinx init" message.
                    # Stop the progress spinner, and activate the work buttons.
                    self.run_status.set('Sphinx initialized.')
                    self.progress.stop()

                    self.rebuild_all_button.configure(state=ACTIVE)
                    self.rebuild_file_button.configure(state=ACTIVE)
                    self.reload_config_button.configure(state=ACTIVE)

                    # We can now inspect the extension type from the sphinx config.
                    self.source_extension = result.extension

                    # Set the initial file
                    self.project_file_tree.selection_set(os.path.join(self.base_path, 'docs', 'index' + self.source_extension))

                elif isinstance(result, BuildStart):
                    # Build start; set up the progress bar, set initial progress to 0
                    self.progress_value.set(0)
                    self.progress.configure(mode='determinate', maximum=100, variable=self.progress_value)

                    # Disable all the buttons so no new commands can be issued
                    self.rebuild_all_button.configure(state=DISABLED)
                    self.rebuild_file_button.configure(state=DISABLED)
                    self.reload_config_button.configure(state=DISABLED)

                    if result.filenames is None:
                        # Build is for all files. Clear the warnings, and
                        # set all files as dirty.
                        filenames = self.project_file_tree.tag_has('file')

                        self.warning_output = {}
                    else:
                        # Build is for a selection of files. Clear the global warnings
                        # and the file warnings, and set selected files as dirty.
                        filenames = result.filenames

                        self.warning_output[None] = []
                        for f in filenames:
                            self.warning_output[f] = []

                    for f in filenames:
                        self.project_file_tree.item(f, tags=['file', 'dirty'])

                elif isinstance(result, Progress):
                    try:
                        base, max_val = {
                            # Progress messages that will be received from a build.
                            # The returned values is a tuple, consisting of:
                            #  * The overall progress value when this task is at 0%
                            #  * The delta that will be added when the task is 100%
                            'reading sources': (0, 30),
                            'looking for now-outdated files': (30, 2),
                            'pickling environment': (32, 2),
                            'checking consistency': (34, 2),
                            'preparing documents': (36, 2),
                            'writing output': (38, 30),
                            'writing additional files': (68, 2),
                            'copying images': (70, 20),
                            'copying downloadable files': (90, 2),
                            'copying static files': (92, 2),
                            'dumping search index': (94, 2),
                            'dumping object inventory': (96, 2),
                            'writing templatebuiltins.js': (98, 2),
                        }[result.stage]

                        progress = int(base + max_val * result.progress / 100.0)
                        self.progress_value.set(progress)

                        # If this is a 'writing output' update, we have a file generated
                        # so update the markup of the tree
                        if result.stage == 'writing output':
                            source_file = os.path.join(self.base_path, 'docs', result.context + self.source_extension)
                            if not self.project_file_tree.tag_has('warning', source_file):
                                self.project_file_tree.item(source_file, tags=['file'])

                    except KeyError:
                        pass

                elif isinstance(result, BuildEnd):
                    # Build complete; mark progress as 100%
                    self.progress_value.set(100)

                    # Disable all the buttons so no new commands can be issued
                    self.rebuild_all_button.configure(state=ACTIVE)
                    self.rebuild_file_button.configure(state=ACTIVE)
                    self.reload_config_button.configure(state=ACTIVE)

                    current_file = self.project_file_tree.selection()[0]
                    if result.filenames is None or current_file in result.filenames:
                        self.html.refresh()
                        self._show_warnings(current_file)

                #########################
                # Output from the monitor
                #########################

                elif isinstance(result, FileChange):
                    # Make sure the new files are in the tree
                    for f in result.new:
                        dirname, filename = os.path.split(f)
                        self.project_file_tree.insert_dirname(dirname)
                        self.project_file_tree.insert_filename(dirname, filename)

                    # Enqueue a build task for all the new and modified documents.
                    self.work_queue.put(BuildSpecific(result.new + result.modified))

        except Empty:
            # queue.get() raises an exception when the queue is empty.
            # This means there is no more output to consume at this time.
            pass

        # Requeue for another update in 40ms (24*40ms == 1s - so this is
        # as fast as we need to update to match human visual acuity)
        self.root.after(40, self.handle_background_tasks)

    ######################################################
    # TK Command handlers
    ######################################################

    def cmd_quit(self):
        "Quit the program"
        # Notify the worker and monitor threads that we want to quit
        self.work_queue.put(Quit())
        self.stop_event.set()

        # Wait for the threads to die.
        self.worker_thread.join()
        self.monitor_thread.join()

        # Quit the main app.
        self.root.quit()

    def cmd_back(self, event=None):
        "Move back on the history stack"
        # We're traversing history, so flag it.
        self._traversing_history = True

        # Move back into history
        self._history_index = self._history_index - 1
        self.project_file_tree.selection_set(self._history[self._history_index - 1])

        # Update button state
        if self._history_index == 1:
            self.back_button.configure(state=DISABLED)
        self.forward_button.configure(state=NORMAL)

    def cmd_forward(self, event=None):
        "Move forward on the history stack"
        self._traversing_history = True
        self._history_index = self._history_index + 1
        self.project_file_tree.selection_set(self._history[self._history_index - 1])

        # Update button state
        if self._history_index == len(self._history):
            self.forward_button.configure(state=DISABLED)
        self.back_button.configure(state=NORMAL)

    def cmd_rebuild_all(self, event=None):
        "Rebuild the project."
        self.work_queue.put(BuildAll())

    def cmd_rebuild_file(self, event=None):
        "Rebuild the current file."
        # Determine the currently selected file
        filename = self.project_file_tree.selection()[0]

        # If the currently selected item is a file, build it.
        if filename and os.path.isfile(filename):
            self.work_queue.put(BuildSpecific([filename]))

    def cmd_reload_config(self, event=None):
        "Rebuild the current file."
        # Determine the currently selected file
        self.work_queue.put(ReloadConfig())

    def cmd_galley_page(self):
        "Show the Galley project page"
        webbrowser.open_new('http://pybee.org/galley')

    def cmd_galley_github(self):
        "Show the Galley GitHub repo"
        webbrowser.open_new('http://github.com/pybee/galley')

    def cmd_galley_docs(self):
        "Show the Galley documentation"
        # If this is a formal release, show the docs for that
        # version. otherwise, just show the head docs.
        if len(NUM_VERSION) == 3:
            webbrowser.open_new('https://galley.readthedocs.io/en/v%s/' % VERSION)
        else:
            webbrowser.open_new('https://galley.readthedocs.io/')

    def cmd_beeware_page(self):
        "Show the BeeWare project page"
        webbrowser.open_new('http://pybee.org/')

    ######################################################
    # Handlers for GUI actions
    ######################################################

    def on_file_selected(self, event):
        "When a file is selected, highlight the file and line"
        if event.widget.selection():
            filename = event.widget.selection()[0]

            if os.path.isfile(filename):
                # Display the file in the html view
                self.show_file(filename=filename)

    def on_link_click(self, event):
        "When a link is clicked, open the new URL"
        url_parts = urlparse(event.url)
        if url_parts.netloc and url_parts.scheme:
            webbrowser.open_new(event.url)
        else:
            # Link refers to HTML; convert back to source filename.
            path, ext = os.path.splitext(url_parts.path)
            filename = os.path.join(self.base_path, 'docs', path[:-1] + self.source_extension)
            index_filename = os.path.join(self.base_path, 'docs', path, 'index' + self.source_extension)
            if os.path.isfile(filename):
                self.project_file_tree.selection_set(filename)
            elif os.path.isfile(index_filename):
                self.project_file_tree.selection_set(index_filename)
            else:
                tkMessageBox.showerror(message="Couldn't find %s" % self.filename_normalizer(filename))

