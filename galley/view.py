# -*- coding: UTF-8 -*-
"""A module containing a visual representation of the connection

This is the "View" of the MVC world.
"""
import os
from Tkinter import *
from tkFont import *
from ttk import *
import tkMessageBox
import urlparse
import webbrowser

from galley import VERSION, NUM_VERSION
from galley.widgets import SimpleHTMLView, FileView

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

        # Set the initial file
        self.project_file_tree.selection_set(os.path.join(self.base_path, 'docs', 'index.rst'))

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

        self.rebuild_button = Button(self.toolbar, text='Run', command=self.cmd_rebuild)
        self.rebuild_button.grid(column=2, row=0)

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
        self.current_file_label.grid(column=0, row=0, sticky=(W, E))

        # Code display area
        self.html = SimpleHTMLView(self.html_frame)
        self.html.grid(column=0, row=1, sticky=(N, S, E, W))

        self.html.link_bind('<1>', self.on_link_click)

        # Set up weights for the html frame's content
        self.html_frame.columnconfigure(0, weight=1)
        self.html_frame.rowconfigure(0, weight=0)
        self.html_frame.rowconfigure(1, weight=1)

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

        # Main window resize handle
        self.grip = Sizegrip(self.statusbar)
        self.grip.grid(column=1, row=0, sticky=(S, E))

        # Set up weights for status bar frame
        self.statusbar.columnconfigure(0, weight=1)
        self.statusbar.columnconfigure(1, weight=0)
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
        html_filename = path.replace(os.path.join(self.base_path, 'docs'), os.path.join(self.base_path, 'docs', '_build', 'html')) + '.html'

        # Set the filename label for the current file
        self.current_file.set(self.filename_normalizer(filename))

        try:
            # Update the html view; this means changing the displayed file
            # if necessary, and updating the current line.
            if filename != self.html.filename:
                self.html.filename = html_filename

            # self.html.anchor = anchor

            # Add this file to history.
            path, ext = os.path.splitext(filename)
            path = path.replace('docs/_build/html', 'docs')

            # History traversal is a temporary operation. If we're traversing
            # history, we won't push this onto the stack... but only this once.
            # Traversal state is reset immediately afterwards.
            if not self._traversing_history:
                if self._history_index:
                    self.forward_button.configure(state=DISABLED)
                    self.back_button.configure(state=NORMAL)

                self._history = self._history[:self._history_index] + [path + '.rst']
                self._history_index = self._history_index + 1
            else:
                self._traversing_history = False

        except IOError:
            tkMessageBox.showerror(message='%s has not been compiled to HTML' % self.filename_normalizer(filename))


    ######################################################
    # TK Main loop
    ######################################################

    def mainloop(self):
        self.root.mainloop()

    ######################################################
    # TK Command handlers
    ######################################################

    def cmd_quit(self):
        "Quit the program"
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

    def cmd_rebuild(self, event=None):
        "Rebuild the project... whatever that means"

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
            webbrowser.open_new('http://galley.readthedocs.org/en/v%s/' % VERSION)
        else:
            webbrowser.open_new('http://galley.readthedocs.org/')

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
        url_parts = urlparse.urlparse(event.url)
        if url_parts.netloc and url_parts.scheme:
            webbrowser.open_new(event.url)
        else:
            # Link refers to HTML; convert back to source filename.
            path, ext = os.path.splitext(url_parts.path)
            self.project_file_tree.selection_set(os.path.join(self.base_path, 'docs', path + '.rst'))
