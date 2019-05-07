# -*- coding: UTF-8 -*-
import json
import os
import sys
from tkinter import ALL, SW, VERTICAL, Canvas, E, Frame, N, S, W
from tkinter.ttk import Scrollbar, Treeview
from xml.etree import ElementTree as et

from tkreadonly import normalize_sequence

from galley.monitor import project_visitor


class WindowTooSmallException(Exception):
    pass


def nodify(node):
    "Escape any problem characters in a node name"
    return node.replace('\\', '/')


DEFAULT_STYLE = {
    'display': 'inline',
    'font': ('helvetica', 14, 'normal', 'normal'),
    'margin': (0, 0, 0, 0),
    'padding': (0, 0, 0, 0),
    'white-space': 'normal',
    'line-height': 1.3,
    'color': 'black',
}

STYLE = {
    'html': {
        'display': 'block',
    },
    'address': {
        'display': 'block',
    },
    'blockquote': {
        'display': 'block',
        'margin-left': 40,
        'margin-right': 40,
    },
    'body': {
        'display': 'block',
        'margin': (8, 8, 8, 8),
    },
    'dd': {
        'display': 'block',
    },
    'div': {
        'display': 'block',
    },
    'dl': {
        'display': 'block',
    },
    'dt': {
        'display': 'block',
    },
    'fieldset': {
        'display': 'block',
    },
    'form': {
        'display': 'block',
    },
    'frame': {
        'display': 'block',
    },
    'frameset': {
        'display': 'block',
    },
    'h1': {
        'display': 'block',
        'font-size': 28,
        'font-weight': 'bold',
        'margin': (8, 0, 8, 0),
    },
    'h2': {
        'display': 'block',
        'font-size': 21,
        'font-weight': 'bold',
        'margin': (10, 0, 10, 0),
    },
    'h3': {
        'display': 'block',
        'font-size': 16,
        'font-weight': 'bold',
        'margin': (12, 0, 12, 0),
    },
    'h4': {
        'display': 'block',
        'font-weight': 'bold',
        'font-style': 'italic',
        'margin': (16, 0, 16, 0),
    },
    'h5': {
        'display': 'block',
        'font-size': 12,
        'font-weight': 'bold',
        'margin': (21, 0, 21, 0),
    },
    'h6': {
        'display': 'block',
        'font-size': 10,
        'font-style': 'italic',
        'margin': (24, 0, 24, 0),
    },
    'noframes': {
        'display': 'block',
    },
    'ol': {
        'display': 'block',
    },
    'p': {
        'display': 'block',
    },
    'ul': {
        'display': 'block',
    },
    'center': {
        'display': 'block',
    },
    'dir': {
        'display': 'block',
    },
    'hr': {
        'display': 'block',
    },
    'menu': {
        'display': 'block',
    },
    'pre': {
        'display': 'block',
        'margin-left': 20,
        'white-space': 'pre',
        'font-family': 'courier',
    },

    'head': {
        'display': None,
    },

    'table': {
        'display': 'table'
    },
    'tr': {
        'display': 'table-row'
    },
    'thead': {
        'display': 'table-header-group'
    },
    'tbody': {
        'display': 'table-row-group'
    },
    'tfoot': {
        'display': 'table-footer-group'
    },
    'td': {
        'display': 'table-cell'
    },
    'th': {
        'display': 'table-cell',
        'font-weight': 'bold',
        'text-align': 'center'
    },
    'caption': {
        'display': 'table-caption',
        'text-align': 'center',
    },

    'li': {
        'display': 'list-item'
    },

    'span': {
    },
    'a': {
        'color': '#0000cc',
    },
    'em': {
        'font-style': 'italic',
    },
    'i': {
        'font-style': 'italic',
    },
    'strong': {
        'font-weight': 'bold',
    },
    'code': {
        'font-family': 'courier'
    },
    'tt': {
        'font-family': 'courier'
    }

}


class RenderContextFrame(object):
    def __init__(self, node):
        self.node = node
        if node is None:
            style = DEFAULT_STYLE
        else:
            style = STYLE.get(node.tag, {})

        for key, value in style.items():
            setattr(self, key.replace('-', '_'), value)

    def __getattr__(self, attr):
        "Silence all AttributeErrors"
        try:
            return super(RenderContextFrame, self).__getattr__(attr)
        except AttributeError:
            return None

    @property
    def margin(self):
        return (self.margin_top, self.margin_right, self.margin_bottom, self.margin_left)

    @margin.setter
    def margin(self, value):
        self.margin_top, self.margin_right, self.margin_bottom, self.margin_left = value

    @property
    def padding(self):
        return (self.padding_top, self.padding_right, self.padding_bottom, self.padding_left)

    @padding.setter
    def padding(self, value):
        self.padding_top, self.padding_right, self.padding_bottom, self.padding_left = value

    @property
    def font(self):
        return ' '.join([str(f) for f in [
                self.font_family,
                self.font_size,
                self.font_style if self.font_style != 'normal' else '',
                self.font_weight if self.font_weight != 'normal' else ''
            ] if f])

    @font.setter
    def font(self, value):
        self.font_family, self.font_size, self.font_style, self.font_weight = value

    @property
    def extra(self):
        if self.node is not None and self.node.tag == 'a':
            return {'href': self.node.attrib['href']}
        return {}


class RenderContext(object):
    INHERITED_PROPERTIES = set([
        'color',
        'font', 'font_family', 'font_size', 'font_weight', 'font_style',
        'line_height',
    ])

    def __init__(self, widget):
        self._widget = widget
        self.frames = [RenderContextFrame(None)]

        self.origin = (0, 0)
        self.limits = (0, 0)

        self.x_offset = 0
        self.y_offset = 0
        self.line_box_height = 0
        self.line_box = []

    def __getattr__(self, attr):
        """Inspect the render context stack for the requested attribute.

        CSS is a cascading process
        """
        value = None
        index = -1
        if attr in RenderContext.INHERITED_PROPERTIES:
            while value is None or value == 'inherit':
                value = getattr(self.frames[index], attr)
                index = index - 1
        else:
            value = getattr(self.frames[-1], attr)
            if value is None:
                value = getattr(self.frames[0], attr)
        return value

    @property
    def tags(self):
        tags = set()
        for frame in self.frames:
            if frame.node is not None and frame.node.tag in ('a',):
                tags.add('a')
        return tuple(tags)

    @property
    def extra(self):
        args = {}
        for frame in self.frames:
            args.update(frame.extra)
        return args

    @property
    def margin(self):
        return (self.margin_top, self.margin_right, self.margin_bottom, self.margin_left)

    @property
    def padding(self):
        return (self.padding_top, self.padding_right, self.padding_bottom, self.padding_left)

    @property
    def font(self):
        return ' '.join([str(f) for f in [
                self.font_family,
                self.font_size,
                self.font_style if self.font_style != 'normal' else '',
                self.font_weight if self.font_weight != 'normal' else ''
            ] if f])

    def _apply(self, direction):
        self.origin = (
            self.origin[0] + self.margin[3] * direction,
            self.origin[1] + self.margin[0] * direction
        )

        self.origin = (
            self.origin[0] + self.padding[3] * direction,
            self.origin[1] + self.padding[0] * direction
        )

        self.limits = (
            self.limits[0] + self.margin[1] * direction,
            self.limits[1] + self.margin[2] * direction
        )

        self.limits = (
            self.limits[0] + self.padding[1] * direction,
            self.limits[1] + self.padding[2] * direction
        )

    def push(self, frame):
        # If we're starting a new block element, then:
        #  * clear anything in the line buffer
        #  * Update the origin to include the y offset (since the
        #    bounding box will start at the y offset of the last
        #    line box
        #  * Set the new y offset to 0 (since we're starting a new
        #    line box
        if frame.display in ('block', 'list-item'):
            self.clear()
            self.origin = (self.origin[0], self.origin[1] + self.y_offset)
            self.y_offset = 0

        self.frames.append(frame)

        self._apply(1)
        # print('START CONTEXT', frame.node, self.origin)

    def pop(self):
        # If we're leaving a block element, then:
        #  * clear anything in the line buffer
        #  * update the y_offset to include the bottom padding and
        #    margin.
        if self.frames[-1].display in ('block', 'list-item'):
            self.clear()
            self.y_offset += self.margin[2]
            self.y_offset += self.padding[2]

        self._apply(-1)

        frame = self.frames.pop()
        return frame

    def clear(self):
        # Adjust the y coordinate to match the maximum line height
        # print('CLEAR', self.origin, self.line_box, [f.node for f in self.frames])
        for offset, obj in self.line_box:
            self._widget.coords(
                obj,
                (self.origin[0] + offset[0], self.origin[1] + offset[1] + self.line_box_height)
            )

        # Carriage return on the line.
        self.x_offset = 0
        self.y_offset += self.line_box_height * self.line_height
        self.line_box_height = 0
        self.line_box = []


class SimpleHTMLView(Frame, object):
    def __init__(self, *args, **kwargs):
        # Initialize the base frame with the remaining arguments.
        super(SimpleHTMLView, self).__init__(*args, **kwargs)

        self._filename = None
        self.document = None

        # The Main Text Widget
        self.html = Canvas(
            self,
            # background=self.style.background_color,
        )

        self.html.grid(column=0, row=0, sticky=(N, S, E, W))

        # Handle canvas resize events by redrawing content.
        self.html.bind('<Configure>', self.redraw)

        # Set up storage for ID anchors
        self.element_id = {}

        # Set up storage and handlers for links.
        self.href = {}

        self.html.tag_bind('a', '<Enter>', lambda e: self.html.config(cursor='pointinghand'))
        self.html.tag_bind('a', '<Leave>', lambda e: self.html.config(cursor=''))

        # Set up internal event handlers on links
        self._link_bindings = {}
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

        self.html.bind_all('<MouseWheel>', self._on_mousewheel)
        self.html.bind_all('<4>', self._on_mousewheel)
        self.html.bind_all('<5>', self._on_mousewheel)

        # Configure the weights for the grid.
        # All the weight goes to the code view.
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=0)
        self.rowconfigure(0, weight=1)

    def _insert_text(self, text, context):
        max_width = self.html.winfo_width() - context.origin[0] - context.limits[0]

        start = 0
        end = 1

        words = text.split(' ')

        # print(
        #     'INSERT',
        #     text,
        #     context.node.tag,
        #     context.font,
        #     context.origin,
        #     context.x_offset,
        #     context.y_offset,
        #     max_width,
        #     context.tags
        # )
        widget = self.html.create_text(
            context.origin[0] + context.x_offset,
            context.origin[1] + context.y_offset,
            anchor=SW,
            font=context.font,
            fill=context.color,
            tags=context.tags,
            text=''
        )

        # Index the widget against any ID (if one was provided)
        try:
            element_id = context.node.attrib['id']
            self.element_id[element_id] = widget
        except AttributeError:
            pass
        except KeyError:
            pass

        # If this content has an HREF associated with it, store the
        # widget ID so that it can be found if clicked on.
        try:
            self.href[widget] = context.extra['href']
        except KeyError:
            pass

        dirty = False
        while end <= len(words):
            # print('try', context.x_offset, context.y_offset, ' '.join(words[start:end]))
            self.html.itemconfig(widget, text=' '.join(words[start:end]))

            # Get the dimensions of the rendered text.
            (x, y, x2, y2) = self.html.bbox(widget)
            height = y2 - y
            width = x2 - x

            # print('END/HEIGHT', context.x_offset + width, height)

            if height > context.line_box_height:
                context.line_box_height = height

            if context.x_offset + width >= max_width:
                # if start == end - 1:
                #     raise WindowTooSmallException()

                # print('   LINE OVERRUN; output:',' '.join(words[start:end - 1]), 'width',width)
                # We've exceeded the line length. Output the line.
                self.html.itemconfig(
                    widget,
                    text=' '.join(words[start:end - 1])
                )

                # Add the text element to the line buffer, and
                # start a new
                context.line_box.append(((context.x_offset, context.y_offset), widget))
                start = end - 1
                end = start
                # print('Remainder', words[start:], start, end, len(words))

                # Clear the line.
                # print('CLEAR BY FULL LINE BOX')
                context.clear()

                # Set up a new empty text container.
                widget = self.html.create_text(
                    context.origin[0] + context.x_offset,
                    context.origin[1] + context.y_offset,
                    anchor=SW,
                    font=context.font,
                    tags=context.tags,
                    text=''
                )

                # If this content has an HREF associated with it, store the
                # widget ID so that it can be found if clicked on.
                try:
                    self.href[widget] = context.extra['href']
                except KeyError:
                    pass

                dirty = False
            else:
                dirty = True

            end = end + 1

        if dirty:
            # print('   BLOCK FITS; output:', ' '.join(words[start:end - 1]), 'width', width)
            context.line_box.append(((context.x_offset, context.y_offset), widget))
            context.x_offset += width

    def _display(self, node, context):
        context.push(RenderContextFrame(node))

        if node.text:
            if context.white_space == 'pre':
                normalized = node.text.strip()
            else:
                normalized = node.text.replace('\n', ' ').strip()
            if normalized:
                # print('   ', node.tag, 'text', normalized.split())
                self._insert_text(normalized, context)

        for child in node:
            self._display(child, context)

        context.pop()

        if node.tail:
            if context.white_space == 'pre':
                normalized = node.tail.strip()
            else:
                normalized = node.tail.replace('\n', ' ').strip()
            if normalized:
                # print('   ', node.tag, 'tail', normalized.split())
                self._insert_text(normalized, context)

    def _on_mousewheel(self, event):
        "Respond to scroll events on the canvas"

        # Only scroll if the scrollbar is actuall active.
        if self.vScrollbar.get() != (0.0, 1.0):
            # Non-OSX platforms return much larger delta values.
            if sys.platform == 'darwin':
                delta = -1 * event.delta
            else:
                delta = -1 * event.delta / 120

            self.html.yview_scroll(delta, 'units')

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

            self.href = {}
            self.element_id = {}

            with open(value) as htmlfile:
                content = json.load(htmlfile)
                self.document = et.fromstring('<body>%s</body>' % content['body'].encode('UTF-8'))
                self.redraw()

    def redraw(self, event=None):
        "Redraw the canvas. This reflows all content on the page."
        if self.document is not None and self.winfo_width() > 100:
            try:
                self.html.delete(ALL)
                context = RenderContext(self.html)
                self._display(self.document, context)
                # print('CLEAR BY END OF DRAW')
                context.clear()
                self.html.config(scrollregion=self.html.bbox(ALL))
            except WindowTooSmallException:
                print('Window too small to render.')

    def refresh(self):
        "Force a refresh of the file currently in the view"
        # Remember the old file, set the internal tracking of the
        # filename to None, then use the property to set the filename
        # again. Since the internal representation has changed, this
        # will force a reload.

        ypos = self.html.yview()

        filename = self._filename
        self._filename = None
        self.filename = filename

        self.html.yview_moveto(ypos[0])

    def link_bind(self, sequence, func):
        "Bind a sequence on link clicks to the given function"
        self._link_bindings[normalize_sequence(sequence)] = func

    def _on_link_handler(self, sequence):
        "Create an internal handler for events on a link event."
        def link_handler(event):
            items = self.html.find_closest(self.html.canvasx(event.x), self.html.canvasy(event.y))
            try:
                url = self.href[items[0]]
                handler = self._link_bindings[sequence]

                # Modify the event for passing on external handlers
                event.widget = self
                event.url = url
                handler(event)
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
