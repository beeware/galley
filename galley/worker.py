from collections import namedtuple
import re
import os

from sphinx.application import Sphinx


######################################################################
# Command types
######################################################################

ReloadConfig = namedtuple('ReloadConfig', [])

BuildAll = namedtuple('BuildAll', [])
BuildSpecific = namedtuple('BuildSpecific', ['filenames'])

Quit = namedtuple('Quit', [])


######################################################################
# Output message types
######################################################################

Output = namedtuple('Output', ['message'])
WarningOutput = namedtuple('Warning', ['filename', 'lineno', 'message'])
Progress = namedtuple('Progress', ['stage', 'progress', 'context'])

InitializationStart = namedtuple('InitializationStart', [])
InitializationEnd = namedtuple('InitializationEnd', ['extension'])

BuildStart = namedtuple('BuildStart', ['build_type'])
BuildEnd = namedtuple('BuildEnd', ['filenames'])


######################################################################
# Sphinx handler
######################################################################

class ANSIOutputHandler(object):
    "A File-like object that puts output onto a queue, stripping ANSI codes."
    def __init__(self, queue):
        self.queue = queue
        self.buffer = []

    def write(self, data):
        "Write the given data to the buffer"
        start = 0
        end = 0

        # The data provided by Sphinx may contain ANSI escape sequences. Strip them out.
        while end < len(data):
            ch = data[end]
            if ch == '\x1b':
                # Insert any accumulated text with the current mode
                self.buffer.append(data[start:end])

                # Read the escape code
                # mode = data[end + 1]
                end = end + 2
                params = []
                while ord(data[end]) not in range(64, 127):
                    param = []
                    while ord(data[end]) not in range(64, 127) and data[end] != ';':
                        param.append(data[end])
                        end = end + 1
                    params.append(int(''.join(param)))
                    if data[end] == ';':
                        end = end + 1
                # command = data[end]

                end = end + 1
                start = end

            elif ch == '\r' or ch == '\n':
                self.buffer.append(data[start:end])
                self.flush()
                start = end + 1
            end = end + 1

        self.buffer.append(data[start:end])

    def flush(self):
        "Flush the current buffer"
        if self.buffer:
            self.emit(''.join(self.buffer))
            self.buffer = []

    def emit(self, content):
        """Internal method to actually put the content onto the output queue

        Override on subclasses to do parsed content handling.
        """
        self.queue.put(Output(message=content))

SIMPLE_PROGRESS_RE = re.compile(r'(.+)\.\.\.$')
PERCENT_PROGRESS_RE = re.compile(r'([\w\s]+)\.\.\. \[([\s\d]{3})\%\] (.+)')

class SphinxStatusHandler(ANSIOutputHandler):
    "A Sphinx output handler for normal status update, stripping ANSI codes."
    def __init__(self, *args, **kwargs):
        super(SphinxStatusHandler, self).__init__(*args, **kwargs)
        self.task = None

    def emit(self, content):
        content = content.strip()
        if content:
            # Always output the status literally
            self.queue.put(Output(content))

            # Also check for certain key content, and output special messages
            if self.task:
                # There is an outstanding simple task. If we've got output, it
                # means we've completed that task.
                self.queue.put(Progress(stage=self.task, progress=100, context=None))
                self.task = None
            else:
                # Check for simple progress: 'doing stuff...'
                progress_match = SIMPLE_PROGRESS_RE.match(content)
                if progress_match:
                    self.task = progress_match.group(1)
                else:
                    # Check for percent progress: 'doing stuff...'
                    progress_match = PERCENT_PROGRESS_RE.match(content)
                    if progress_match:
                        self.queue.put(
                            Progress(
                                stage=progress_match.group(1),
                                progress=int(progress_match.group(2)),
                                context=progress_match.group(3)
                            )
                        )


class SphinxWarningHandler(ANSIOutputHandler):
    """A Sphinx output handler for, stripping ANSI codes..

    Parses warning content to extract context.
    """
    def emit(self, content):
        content = content.strip()
        if content:
            print "WARNING>>>", content
            if content.startswith('WARNING: '):
                self.queue.put(WarningOutput(filename=None, lineno=None, message=content[9:]))
            else:
                parts = content.split(':')
                self.queue.put(
                    WarningOutput(
                        filename=parts[0],
                        lineno=int(parts[1]) if parts[1] else None,
                        message=':'.join(parts[3:]).strip())
                    )


def sphinx_worker(base_path, work_queue, output_queue):
    "A background worker thread performing Sphinx compilations"
    # Set up the Sphinx instance
    srcdir = base_path
    confdir = srcdir
    outdir = os.path.join(srcdir, '_build', 'html')
    freshenv = False
    warningiserror = False
    buildername = 'html'
    # verbosity = 0
    # parallel = 0
    status = SphinxStatusHandler(output_queue)
    warning = SphinxWarningHandler(output_queue)
    # error = sys.stderr
    # warnfile = None
    confoverrides = {}
    tags = []
    doctreedir = os.path.join(outdir, '.doctrees')

    output_queue.put(InitializationStart())

    sphinx = Sphinx(srcdir, confdir, outdir, doctreedir, buildername,
                         confoverrides, status, warning, freshenv,
                         warningiserror, tags)

    output_queue.put(InitializationEnd(extension=sphinx.config.source_suffix))

    quit = False
    while not quit:
        # Get the next command off the work queue
        cmd = work_queue.get(block=True)

        if isinstance(cmd, Quit):
            quit = True

        elif isinstance(cmd, ReloadConfig):
            output_queue.put(InitializationStart())
            freshenv = True
            sphinx = Sphinx(srcdir, confdir, outdir, doctreedir, buildername,
                             confoverrides, status, warning, freshenv,
                             warningiserror, tags)
            output_queue.put(InitializationEnd(extension=sphinx.config.source_suffix))

        elif isinstance(cmd, BuildAll):
            output_queue.put(BuildStart(build_type='all'))
            sphinx.builder.build_all()
            output_queue.put(BuildEnd(filenames=None))

        elif isinstance(cmd, BuildSpecific):
            output_queue.put(BuildStart(build_type='specific'))
            sphinx.builder.build_specific(cmd.filenames)
            output_queue.put(BuildEnd(filenames=cmd.filenames))

        # Reset the warning count so that they don't accumulate between builds.
        sphinx._warncount = 0
