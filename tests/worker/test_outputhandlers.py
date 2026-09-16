import unittest
from queue import Queue

from galley.worker import (ANSIOutputHandler, Output, Progress,
                           SphinxStatusHandler, SphinxWarningHandler,
                           WarningOutput)


class ANSIOutputHandlerTest(unittest.TestCase):
    def setUp(self):
        self.queue = Queue()
        self.handler = ANSIOutputHandler(self.queue)

    def test_simple_string(self):
        "A simple string can be output and flushed"
        self.handler.write("hello world")
        self.handler.flush()

        output = self.queue.get(block=False)
        self.assertEqual(output, Output(message='hello world'))

        # Nothing left in the queue
        self.assertTrue(self.queue.empty())

    def test_single_param_ansi_string(self):
        self.handler.write("hello\x1b[1m world")
        self.handler.flush()

        output = self.queue.get(block=False)
        self.assertEqual(output, Output(message='hello world'))

        # Nothing left in the queue
        self.assertTrue(self.queue.empty())

    def test_multi_param_ansi_string(self):
        self.handler.write("hello\x1b[32;40m world")
        self.handler.flush()

        output = self.queue.get(block=False)
        self.assertEqual(output, Output(message='hello world'))

        # Nothing left in the queue
        self.assertTrue(self.queue.empty())

    def test_newline_flush(self):
        self.handler.write("hello world\ngoodbye world\n")

        output = self.queue.get(block=False)
        self.assertEqual(output, Output(message='hello world'))

        output = self.queue.get(block=False)
        self.assertEqual(output, Output(message='goodbye world'))

        # Nothing left in the queue
        self.assertTrue(self.queue.empty())

    def test_carriage_return_flush(self):
        self.handler.write("hello world\rgoodbye world\r")

        output = self.queue.get(block=False)
        self.assertEqual(output, Output(message='hello world'))

        output = self.queue.get(block=False)
        self.assertEqual(output, Output(message='goodbye world'))

        # Nothing left in the queue
        self.assertTrue(self.queue.empty())


class SphinxStatusHandlerTest(unittest.TestCase):
    def setUp(self):
        self.queue = Queue()
        self.handler = SphinxStatusHandler(self.queue)

    def test_simple_message(self):
        "A simple string can be output and flushed"
        self.handler.write("hello world")
        self.handler.flush()

        output = self.queue.get(block=False)
        self.assertEqual(output, Output(message='hello world'))

        # Nothing left in the queue
        self.assertTrue(self.queue.empty())

    def test_stripping(self):
        "Messages are stripped; empty messages aren't sent"
        self.handler.write("  prefix\nsuffix  \n   \n\n  both   ")
        self.handler.flush()

        output = self.queue.get(block=False)
        self.assertEqual(output, Output(message='prefix'))

        output = self.queue.get(block=False)
        self.assertEqual(output, Output(message='suffix'))

        output = self.queue.get(block=False)
        self.assertEqual(output, Output(message='both'))

        # Nothing left in the queue
        self.assertTrue(self.queue.empty())

    def test_simple_progress(self):
        "Simple tasks are identified and reported."

        # Output the initial message:
        self.handler.write("dumping object inventory...")
        self.handler.flush()

        # Only the raw output is returned
        output = self.queue.get(block=False)
        self.assertEqual(output, Output(message="dumping object inventory..."))

        # Nothing left in the queue
        self.assertTrue(self.queue.empty())

        # Output the completion message
        self.handler.write("done")
        self.handler.flush()

        # The raw output *and* the progress message is output.
        output = self.queue.get(block=False)
        self.assertEqual(output, Output(message="done"))

        output = self.queue.get(block=False)
        self.assertEqual(output, Progress(stage='dumping object inventory', progress=100, context=None))

        # Nothing left in the queue
        self.assertTrue(self.queue.empty())

        # Task state has been flushed
        self.handler.write("More stuff done.")
        self.handler.flush()

        # The raw output *and* the progress message is output.
        output = self.queue.get(block=False)
        self.assertEqual(output, Output(message="More stuff done."))

        # Nothing left in the queue
        self.assertTrue(self.queue.empty())

    def test_percent_progress(self):
        "Progress indicators are extracted and sent as parsed messages"

        self.handler.write("copying downloadable files... [  2%] /path/to/file.sh")
        self.handler.flush()
        self.handler.write("copying downloadable files... [ 80%] /path/to/other_file.bat")
        self.handler.flush()
        self.handler.write("copying downloadable files... [100%] /path/to/3rd-file.sh")
        self.handler.flush()

        # Output comes in pairs -- a normal output with the full message, then a parsed output.
        output = self.queue.get(block=False)
        self.assertEqual(output, Output(message="copying downloadable files... [  2%] /path/to/file.sh"))
        output = self.queue.get(block=False)
        self.assertEqual(output, Progress(stage='copying downloadable files', progress=2, context='/path/to/file.sh'))

        output = self.queue.get(block=False)
        self.assertEqual(output, Output(message="copying downloadable files... [ 80%] /path/to/other_file.bat"))
        output = self.queue.get(block=False)
        self.assertEqual(
            output,
            Progress(stage='copying downloadable files', progress=80, context='/path/to/other_file.bat')
        )

        output = self.queue.get(block=False)
        self.assertEqual(output, Output(message="copying downloadable files... [100%] /path/to/3rd-file.sh"))
        output = self.queue.get(block=False)
        self.assertEqual(
            output,
            Progress(stage='copying downloadable files', progress=100, context='/path/to/3rd-file.sh')
        )

        # Nothing left in the queue
        self.assertTrue(self.queue.empty())


class SphinxWarningHandlerTest(unittest.TestCase):
    def setUp(self):
        self.queue = Queue()
        self.handler = SphinxWarningHandler(self.queue)

    def test_global_warning(self):
        "A gloabl warning message is parsed correctly"

        self.handler.write("WARNING: html_static_path entry '/beeware/galley/docs/_static' does not exist")
        self.handler.flush()

        output = self.queue.get(block=False)
        self.assertEqual(
            output,
            WarningOutput(
                filename=None,
                lineno=None,
                message="html_static_path entry '/beeware/galley/docs/_static' does not exist"
            )
        )

        # Nothing left in the queue
        self.assertTrue(self.queue.empty())

    def test_file_warning_missing_for_document(self):
        "A warning message that mentions a filename is parsed for file name/number content"

        self.handler.write(
            "/beeware/galley/docs/internals/newfile.rst:: "
            "WARNING: document isn't included in any toctree"
        )
        self.handler.flush()

        output = self.queue.get(block=False)
        self.assertEqual(
            output,
            WarningOutput(
                filename="/beeware/galley/docs/internals/newfile.rst",
                lineno=None,
                message="document isn't included in any toctree"
            )
        )

        # Nothing left in the queue
        self.assertTrue(self.queue.empty())

    def test_file_warning_for_glob_match(self):
        "A warning message that mentions a filename is parsed for file name/number content"

        self.handler.write(
            "/beeware/galley/docs/index.rst:65: "
            "WARNING: toctree glob pattern u'releases' didn't match any documents"
        )
        self.handler.flush()

        output = self.queue.get(block=False)
        self.assertEqual(
            output,
            WarningOutput(
                filename="/beeware/galley/docs/index.rst",
                lineno=65,
                message="toctree glob pattern u'releases' didn't match any documents"
            )
        )

        # Nothing left in the queue
        self.assertTrue(self.queue.empty())
