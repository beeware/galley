# -*- coding: UTF-8 -*-
import hashlib
from HTMLParser import HTMLParser
import htmlentitydefs
import os
from ttk import *
from Tkinter import *

from tkreadonly import ReadOnlyText, normalize_sequence

from galley.monitor import project_visitor


def nodify(node):
    "Escape any problem characters in a node name"
    return node.replace('\\', '/')


class RenderingHTMLParser(HTMLParser):
    def __init__(self, html):
        self.html = html
        HTMLParser.__init__(self)
        self.html_tags = []

        # Reset the writing state.
        self.reset_state()

    BLOCK_TAGS = [
        # True display:block tags
        'address', 'blockquote',
        'dd', 'dl', 'dt',
        'fieldset', 'form',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'noframes', 'frame', 'frameset',
        'ol', 'ul', 'center',
        'p', 'div',
        'dir', 'hr', 'menu', 'pre',

        # display:list-item is treated like a block.
        'li',
    ]

    SILENCED_TAGS = [
        ('a', ['headerlink']),
    ]

    def reset_state(self):
        # Writing state
        self.pen_down = False
        self.cleared = True

        self.links = {}
        self.current_link = []

    @property
    def li_depth(self):
        return len([t[0] for t in self.html_tags if t[0] == 'li'])

    @property
    def text_tags(self):
        extra_tags = []
        if self.li_depth:
            extra_tags.append('li.%s' % self.li_depth)
        if self.current_link:
            extra_tags.append('a.%s' % self.current_link[-1])

        return tuple(t[0] for t in self.html_tags) + tuple(extra_tags)

    def handle_starttag(self, tag, attrs):
        """Handle the start of a new tag.

        Push the stack and re-evaluate whether the pen needs to be
        raised or lowered.
        """
        attr_dict = dict(attrs)

        self.html_tags.append((tag, attr_dict))

        # If we're starting a block tag, and the pen is down, and we're not
        # clear, output a newline.
        if tag in self.BLOCK_TAGS and self.pen_down and not self.cleared:
            self.html.insert(END, '\n')
            self.cleared = True

        # Now check to see if we need to raise or lower the pen.
        if tag == 'div' and attr_dict.get('class') == 'body':
            self.pen_down = True
        else:
            # Check the SILENCED_TAGS. If we're starting a silenced tag,
            # and all the classes match, raise the pen.
            classes = attr_dict.get('class', '').split(' ')
            for stag, sclasses in self.SILENCED_TAGS:
                if tag == stag and all(sclass in classes for sclass in sclasses):
                    self.pen_down = False
                    break

        if tag == 'a':
            href_hash = hashlib.md5(attr_dict['href']).hexdigest()[:8]
            self.current_link.append(href_hash)
            self.links[href_hash] = attr_dict['href']

        # Now look for extra content inserted on tag start
        if self.pen_down:
            if tag == 'li':
                extra = {
                    1: u'● ',
                    2: u'○ ',
                    3: u'◆ ',
                    4: u'◇ ',
                }.get(self.li_depth, u'✱ ')

                self.html.insert(END, extra, self.text_tags)

    def handle_endtag(self, tag):
        """Handle the end of a tag.

        Pop the stack and re-evaluate whether the pen needs to be
        raised or lowered.
        """
        # This assumes that all tags are balanced.
        tag, attr_dict = self.html_tags.pop()

        # Clear the current link.
        if tag == 'a':
            self.current_link.pop()

        # Now check to see if we need to raise or lower the pen.
        if tag == 'div' and attr_dict.get('class') == 'body':
            self.pen_down = False
        else:
            # Check the SILENCED_TAGS. If we're ending a silenced tag,
            # and all the classes match, drop the pen.
            classes = attr_dict.get('class', '').split(' ')
            for stag, sclasses in self.SILENCED_TAGS:
                if tag == stag and all(sclass in classes for sclass in sclasses):
                    self.pen_down = True
                    break

    def handle_data(self, data):
        """Handle actual visible content.

        If the pen is down, write the content.
        """
        # If the pen is currently down, and there is actual data (not just
        # the space between tags), write the data.
        if self.pen_down and data.strip():
            clean_text = data.replace('\n', ' ').replace('  ', ' ')
            self.html.insert(END, clean_text, self.text_tags)

            # print self.text_tags, clean_text
            # We've just output content, so we're no longer "clear"; the end
            # of the next block tag must output a newline.
            self.cleared = False

    def handle_entityref(self, data):
        """Handle an entity reference in data.

        If the pen is down, convert the entity into a unicode character
        and output it.
        """
        if self.pen_down:
            char = htmlentitydefs.entitydefs[data]
            self.html.insert(END, char, self.text_tags)

    def handle_charref(self, data):
        """Handle an entity reference in data.

        If the pen is down, convert the character reference into a unicode
        character and output it.
        """
        if self.pen_down:
            char = unichr(int(data))
            self.html.insert(END, char, self.text_tags)


class SimpleHTMLView(Frame, object):
    def __init__(self, *args, **kwargs):
        # Initialize the base frame with the remaining arguments.
        super(SimpleHTMLView, self).__init__(*args, **kwargs)

        self._filename = None

        # The Main Text Widget
        self.html = ReadOnlyText(self,
            width=80,
            height=25,
            wrap=WORD,
            # background=self.style.background_color,
            highlightthickness=0,
            bd=0,
            padx=4,
            cursor='arrow',
        )

        self.html.grid(column=0, row=0, sticky=(N, S, E, W))

        self.html.tag_configure("h1", font='helvetica 24 bold', spacing1=12, spacing3=12)
        self.html.tag_configure("h2", font='helvetica 18 bold', spacing1=9, spacing3=9)
        self.html.tag_configure("h3", font='helvetica 14 bold', spacing1=7, spacing3=7)
        self.html.tag_configure("h4", font='helvetica 13 bold italic', spacing1=6, spacing3=6)
        self.html.tag_configure("h5", font='helvetica 13 bold', spacing1=6, spacing3=6)
        self.html.tag_configure("h6", font='helvetica 13 italic', spacing1=6, spacing3=6)

        self.html.tag_configure("b", font='helvetica 12 bold')
        self.html.tag_configure("strong", font='helvetica 12 bold')

        self.html.tag_configure("i", font='helvetica 12 italic')
        self.html.tag_configure("em", font='helvetica 12 italic')

        self.html.tag_configure("p", font='helvetica 14', lmargin1=10, lmargin2=10, spacing1=5, spacing2=5, spacing3=5)

        self.html.tag_configure("li", font='helvetica 14', spacing1=5, spacing3=5)

        # self.html.tag_configure("li.0", font='helvetica 14', lmargin1=10, lmargin2=10)
        self.html.tag_configure("li.1", font='helvetica 14', lmargin1=20, lmargin2=20)
        self.html.tag_configure("li.2", font='helvetica 14', lmargin1=40, lmargin2=40)
        self.html.tag_configure("li.3", font='helvetica 14', lmargin1=60, lmargin2=60)
        self.html.tag_configure("li.4", font='helvetica 14', lmargin1=80, lmargin2=80)
        self.html.tag_configure("li.N", font='helvetica 14', lmargin1=100, lmargin2=100)

        self.html.tag_configure("pre", lmargin1=25, lmargin2=25)
        self.html.tag_configure("code", lmargin1=25, lmargin2=25, spacing1=10, spacing2=5, spacing3=10)

        self.html.tag_configure("a", foreground='blue', underline=1)
        # Set up internal event handlers on links
        for modifier in [
                    '',
                    'Alt-', 'Alt-Control-', 'Alt-Shift-', 'Alt-Control-Shift-',
                    'Control-', 'Control-Shift-',
                    'Shift-'
                ]:
            for action in ['Button', 'Double']:
                for button in range(1, 6):
                    sequence = '<%s%s-%s>' % (modifier, action, button)
                    self.html.tag_bind('a', sequence, self._on_link_handler(sequence))

        # The widgets vertical scrollbar
        self.vScrollbar = Scrollbar(self, orient=VERTICAL)
        self.vScrollbar.grid(column=1, row=0, sticky=(N, S))

        # Tie the scrollbar to the text views, and the text views
        # to each other.
        self.html.config(yscrollcommand=self.vScrollbar.set)
        self.vScrollbar.config(command=self.html.yview)

        # Configure the weights for the grid.
        # All the weight goes to the code view.
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=0)
        self.rowconfigure(0, weight=1)

        self.parser = RenderingHTMLParser(self.html)

        # Bound event handlers
        self._link_bindings = {}

    @property
    def filename(self):
        "Return the current file being displayed by the view"
        return self._filename

    @filename.setter
    def filename(self, value):
        "Set the file being displayed by the view"
        if self._filename != value:
            # Store the new filename
            self._filename = value

            self.html.delete('1.0', END)

            with open(value) as htmlfile:
                self.parser.feed(htmlfile.read())


    def refresh(self):
        "Force a refresh of the file currently in the view"
        # Remember the old file, set the internal tracking of the
        # filename to None, then use the property to set the filename
        # again. Since the internal representation has changed, this
        # will force a reload.
        filename = self._filename
        self._filename = None
        self.filename = filename

    def link_bind(self, sequence, func):
        "Bind a sequence on link clicks to the given function"
        self._link_bindings[normalize_sequence(sequence)] = func

    def _on_link_handler(self, sequence):
        "Create an internal handler for events on a link event."
        def link_handler(event):
            index = self.html.index('@%s,%s' % (event.x, event.y))
            tags = self.html.tag_names(index)
            try:
                href_hash = [t for t in tags if t.startswith('a.')][-1][2:]
                url = self.parser.links[href_hash]
                handler = self._link_bindings[sequence]

                # Modify the event for passing on external handlers
                event.widget = self
                event.url = url
                handler(event)
            except IndexError:
                # No <a> under the current event.
                # This is a probably bug in Tk; a click event in the Text widget
                # used to regain focus at an OS level causes a tag_bind
                # event to be generated, regardless if there is a bound tag
                # under the cursor.
                pass
            except KeyError:
                # No handler registered
                pass
        return link_handler


class FileView(Treeview):
    def __init__(self, *args, **kwargs):
        # Only a single stack frame can be selected at a time.
        kwargs['selectmode'] = 'browse'
        self.normalizer = kwargs.pop('normalizer')
        self.root = kwargs.pop('root', None)
        Treeview.__init__(self, *args, **kwargs)

        # Set up styles for line numbers
        self.tag_configure('directory', foreground='#999')
        self.tag_configure('dirty', foreground='orange')
        self.tag_configure('warning', foreground='red')

        # Populate the file view
        if self.root:
            os.path.walk(self.root, project_visitor(self.insert_dirname, self.insert_filename), None)

    def insert_dirname(self, dirname, data=None):
        "Ensure that a specific directory exists in the breakpoint tree"
        if not self.exists(nodify(dirname)):
            nodename = nodify(dirname)
            parent, child = os.path.split(dirname)
            if self.root:
                # We're displaying a subtree.
                if nodename == nodify(self.root):
                    # If this is the CWD, display at the root of the tree.
                    path = nodify(child)
                    base = ''
                else:
                    self.insert_dirname(parent, data)
                    base = nodify(parent)
                    path = nodify(child)
            else:
                # Check for the "root" on both unix and Windows
                if child == '':
                    path = nodify(parent)
                    base = ''
                else:
                    self.insert_dirname(parent, data)
                    base = nodify(parent)
                    path = nodify(child)

            # Establish the index at which to insert this child.
            # Do this by getting a list of children, sorting the list by name
            # and then finding how many would sort less than the label for
            # this node.
            files = sorted(self.get_children(base), reverse=False)
            index = len([item for item in files if item < nodify(dirname)])

            # Now insert a new node at the index that was found.
            self.insert(
                base, index, nodename,
                text=path,
                open=True,
                tags=['directory']
            )

    def insert_filename(self, dirname, filename, data=None):
        "Ensure that a specific filename exists in the breakpoint tree"
        full_filename = os.path.join(dirname, filename)
        if not self.exists(nodify(full_filename)):
            # If self.root is defined, we're only displaying files under that root.
            # If the normalized version of the filename is the same as the
            # filename, then the file *isn't* under the root. Don't bother trying
            # to add the file.
            # Alternatively, if self.root is *not* defined, *only* add the file if
            # if isn't under the project root.
            if full_filename == self.normalizer(full_filename):
                if self.root:
                    return
                self.insert_dirname(dirname, data)
            else:
                if self.root is None:
                    return

            # Establish the index at which to insert this child.
            # Do this by getting a list of children, sorting the list by name
            # and then finding how many would sort less than the label for
            # this node.
            files = sorted(self.get_children(nodify(dirname)), reverse=False)
            index = len([item for item in files if item < nodify(full_filename)])
            # Now insert a new node at the index that was found.
            self.insert(
                nodify(dirname), index, nodify(os.path.join(dirname, filename)),
                text=filename,
                open=True,
                tags=['file']
            )

    def selection_set(self, node):
        """Node names on the file tree are the filename.

        On Windows, this requires escaping, because backslashes
        in object IDs filenames cause problems with Tk.
         """
        Treeview.selection_set(self, nodify(node))
