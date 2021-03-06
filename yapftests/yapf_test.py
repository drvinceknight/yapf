# -*- coding: utf-8 -*-
# Copyright 2015 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Tests for yapf.yapf."""

import io
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest

from yapf.yapflib import style
from yapf.yapflib import yapf_api

ROOT_DIR = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))

# Verification is turned off by default, but want to enable it for testing.
YAPF_BINARY = [sys.executable, '-m', 'yapf', '--verify']


class YapfTest(unittest.TestCase):

  def _Check(self, unformatted_code, expected_formatted_code):
    style.SetGlobalStyle(style.CreateGoogleStyle())
    formatted_code = yapf_api.FormatCode(unformatted_code)
    self.assertEqual(expected_formatted_code, formatted_code)

  def testSimple(self):
    unformatted_code = textwrap.dedent(u"""\
        print('foo')
        """)
    self._Check(unformatted_code, unformatted_code)

  def testNoEndingNewline(self):
    unformatted_code = textwrap.dedent(u"""\
        if True: pass""")
    expected_formatted_code = textwrap.dedent(u"""\
        if True: pass
        """)
    self._Check(unformatted_code, expected_formatted_code)


class CommandLineTest(unittest.TestCase):
  """Test how calling yapf from the command line acts."""

  @classmethod
  def setUpClass(cls):
    cls.test_tmpdir = tempfile.mkdtemp()

  @classmethod
  def tearDownClass(cls):
    shutil.rmtree(cls.test_tmpdir)

  def testUnicodeEncodingPipedToFile(self):
    unformatted_code = textwrap.dedent(u"""\
        def foo():
            print('⇒')
        """)

    with tempfile.NamedTemporaryFile(suffix='.py',
                                     dir=self.test_tmpdir) as outfile:
      with tempfile.NamedTemporaryFile(suffix='.py',
                                       dir=self.test_tmpdir) as testfile:
        testfile.write(unformatted_code.encode('UTF-8'))
        subprocess.check_call(YAPF_BINARY + ['--diff', testfile.name],
                              stdout=outfile)

  def testInPlaceReformatting(self):
    unformatted_code = textwrap.dedent(u"""\
        def foo():
          x = 37
        """)
    expected_formatted_code = textwrap.dedent(u"""\
        def foo():
            x = 37
        """)

    with tempfile.NamedTemporaryFile(suffix='.py',
                                     dir=self.test_tmpdir) as testfile:
      testfile.write(unformatted_code.encode('UTF-8'))
      testfile.seek(0)

      p = subprocess.Popen(YAPF_BINARY + ['--in-place', testfile.name])
      p.wait()

      with io.open(testfile.name, mode='r', newline='') as fd:
        reformatted_code = fd.read()

    self.assertEqual(reformatted_code, expected_formatted_code)

  def testReadFromStdin(self):
    unformatted_code = textwrap.dedent(u"""\
        def foo():
          x = 37
        """)
    expected_formatted_code = textwrap.dedent(u"""\
        def foo():
            x = 37
        """)

    p = subprocess.Popen(YAPF_BINARY,
                         stdout=subprocess.PIPE,
                         stdin=subprocess.PIPE,
                         stderr=subprocess.STDOUT)
    reformatted_code, stderrdata = p.communicate(
        unformatted_code.encode('utf-8'))
    self.assertIsNone(stderrdata)
    self.assertEqual(reformatted_code.decode('utf-8'), expected_formatted_code)

  def testSetGoogleStyle(self):
    unformatted_code = textwrap.dedent(u"""\
        def foo(): # trail
            x = 37 
        """)
    expected_formatted_code = textwrap.dedent(u"""\
        def foo():  # trail
          x = 37
        """)

    p = subprocess.Popen(YAPF_BINARY + ['--style=Google'],
                         stdout=subprocess.PIPE,
                         stdin=subprocess.PIPE,
                         stderr=subprocess.STDOUT)
    reformatted_code, stderrdata = p.communicate(
        unformatted_code.encode('utf-8'))
    self.assertIsNone(stderrdata)
    self.assertEqual(reformatted_code.decode('utf-8'), expected_formatted_code)

  def testSetCustomStyleBasedOnGoogle(self):
    unformatted_code = textwrap.dedent(u"""\
        def foo(): # trail
            x = 37
        """)
    expected_formatted_code = textwrap.dedent(u"""\
        def foo():    # trail
          x = 37
        """)

    with tempfile.NamedTemporaryFile(dir=self.test_tmpdir, mode='w') as f:
      f.write(textwrap.dedent('''\
          [style]
          based_on_style = Google
          SPACES_BEFORE_COMMENT = 4
          '''))
      f.flush()

      p = subprocess.Popen(YAPF_BINARY + ['--style={0}'.format(f.name)],
                           stdout=subprocess.PIPE,
                           stdin=subprocess.PIPE,
                           stderr=subprocess.STDOUT)
      reformatted_code, stderrdata = p.communicate(
          unformatted_code.encode('utf-8'))
      self.assertIsNone(stderrdata)
      self.assertEqual(reformatted_code.decode('utf-8'),
                       expected_formatted_code)

  def testReadSingleLineCodeFromStdin(self):
    unformatted_code = textwrap.dedent(u"""\
        if True: pass
        """)
    expected_formatted_code = textwrap.dedent(u"""\
        if True: pass
        """)

    p = subprocess.Popen(YAPF_BINARY,
                         stdout=subprocess.PIPE,
                         stdin=subprocess.PIPE,
                         stderr=subprocess.STDOUT)
    # We can't pipe unicode through subprocess - need to encode/decode at the
    # boundary.
    reformatted_code, stderrdata = p.communicate(
        unformatted_code.encode('utf-8'))
    self.assertIsNone(stderrdata)
    self.assertEqual(reformatted_code.decode('utf-8'), expected_formatted_code)

  def testEncodingVerification(self):
    unformatted_code = textwrap.dedent(u"""\
        '''The module docstring.'''
        # -*- coding: utf-8 -*-
        def f():
            x = 37
        """)

    with tempfile.NamedTemporaryFile(suffix='.py',
                                     dir=self.test_tmpdir) as outfile:
      with tempfile.NamedTemporaryFile(suffix='.py',
                                       dir=self.test_tmpdir) as testfile:
        testfile.write(unformatted_code.encode('utf-8'))
        subprocess.check_call(YAPF_BINARY + ['--diff', testfile.name],
                              stdout=outfile)

  def testReformattingSpecificLines(self):
    unformatted_code = textwrap.dedent(u"""\
        def h():
            if (xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0]) == 'aaaaaaaaaaa' and xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0].mmmmmmmm[0]) == 'bbbbbbb'):
                pass

        def g():
            if (xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0]) == 'aaaaaaaaaaa' and xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0].mmmmmmmm[0]) == 'bbbbbbb'):
                pass
        """)
    expected_formatted_code = textwrap.dedent(u"""\
        def h():
            if (xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0]) == 'aaaaaaaaaaa' and
                xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0].mmmmmmmm[0]) == 'bbbbbbb'):
                pass

        def g():
            if (xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0]) == 'aaaaaaaaaaa' and xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0].mmmmmmmm[0]) == 'bbbbbbb'):
                pass
        """)

    p = subprocess.Popen(YAPF_BINARY + ['--lines', '1-2'],
                         stdout=subprocess.PIPE,
                         stdin=subprocess.PIPE,
                         stderr=subprocess.STDOUT)
    reformatted_code, stderrdata = p.communicate(
        unformatted_code.encode('utf-8'))
    self.assertIsNone(stderrdata)
    self.assertEqual(reformatted_code.decode('utf-8'), expected_formatted_code)

  def testReformattingSkippingLines(self):
    unformatted_code = textwrap.dedent(u"""\
        def h():
            if (xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0]) == 'aaaaaaaaaaa' and xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0].mmmmmmmm[0]) == 'bbbbbbb'):
                pass

        # yapf: disable
        def g():
            if (xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0]) == 'aaaaaaaaaaa' and xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0].mmmmmmmm[0]) == 'bbbbbbb'):
                pass
        # yapf: enable
        """)
    expected_formatted_code = textwrap.dedent(u"""\
        def h():
            if (xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0]) == 'aaaaaaaaaaa' and
                xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0].mmmmmmmm[0]) == 'bbbbbbb'):
                pass

        # yapf: disable
        def g():
            if (xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0]) == 'aaaaaaaaaaa' and xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0].mmmmmmmm[0]) == 'bbbbbbb'):
                pass
        # yapf: enable
        """)

    p = subprocess.Popen(YAPF_BINARY,
                         stdout=subprocess.PIPE,
                         stdin=subprocess.PIPE,
                         stderr=subprocess.STDOUT)
    reformatted_code, stderrdata = p.communicate(
        unformatted_code.encode('utf-8'))
    self.assertIsNone(stderrdata)
    self.assertEqual(reformatted_code.decode('utf-8'), expected_formatted_code)

  def testReformattingSkippingToEndOfFile(self):
    unformatted_code = textwrap.dedent(u"""\
        def h():
            if (xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0]) == 'aaaaaaaaaaa' and xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0].mmmmmmmm[0]) == 'bbbbbbb'):
                pass

        # yapf: disable
        def g():
            if (xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0]) == 'aaaaaaaaaaa' and xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0].mmmmmmmm[0]) == 'bbbbbbb'):
                pass

        def f():
            def e():
                while (xxxxxxxxxxxxxxxxxxxxx(yyyyyyyyyyyyy[zzzzz]) == 'aaaaaaaaaaa' and
                       xxxxxxxxxxxxxxxxxxxxx(yyyyyyyyyyyyy[zzzzz].aaaaaaaa[0]) ==
                       'bbbbbbb'):
                    pass
        """)
    expected_formatted_code = textwrap.dedent(u"""\
        def h():
            if (xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0]) == 'aaaaaaaaaaa' and
                xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0].mmmmmmmm[0]) == 'bbbbbbb'):
                pass

        # yapf: disable
        def g():
            if (xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0]) == 'aaaaaaaaaaa' and xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0].mmmmmmmm[0]) == 'bbbbbbb'):
                pass

        def f():
            def e():
                while (xxxxxxxxxxxxxxxxxxxxx(yyyyyyyyyyyyy[zzzzz]) == 'aaaaaaaaaaa' and
                       xxxxxxxxxxxxxxxxxxxxx(yyyyyyyyyyyyy[zzzzz].aaaaaaaa[0]) ==
                       'bbbbbbb'):
                    pass
        """)

    p = subprocess.Popen(YAPF_BINARY,
                         stdout=subprocess.PIPE,
                         stdin=subprocess.PIPE,
                         stderr=subprocess.STDOUT)
    reformatted_code, stderrdata = p.communicate(
        unformatted_code.encode('utf-8'))
    self.assertIsNone(stderrdata)
    self.assertEqual(reformatted_code.decode('utf-8'), expected_formatted_code)

  def testReformattingSkippingSingleLine(self):
    unformatted_code = textwrap.dedent(u"""\
        def h():
            if (xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0]) == 'aaaaaaaaaaa' and xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0].mmmmmmmm[0]) == 'bbbbbbb'):
                pass

        def g():
            if (xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0]) == 'aaaaaaaaaaa' and xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0].mmmmmmmm[0]) == 'bbbbbbb'):  # yapf: disable
                pass
        """)
    expected_formatted_code = textwrap.dedent(u"""\
        def h():
            if (xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0]) == 'aaaaaaaaaaa' and
                xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0].mmmmmmmm[0]) == 'bbbbbbb'):
                pass


        def g():
            if (xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0]) == 'aaaaaaaaaaa' and xxxxxxxxxxxx.yyyyyyyy(zzzzzzzzzzzzz[0].mmmmmmmm[0]) == 'bbbbbbb'):  # yapf: disable
                pass
        """)

    p = subprocess.Popen(YAPF_BINARY,
                         stdout=subprocess.PIPE,
                         stdin=subprocess.PIPE,
                         stderr=subprocess.STDOUT)
    reformatted_code, stderrdata = p.communicate(
        unformatted_code.encode('utf-8'))
    self.assertIsNone(stderrdata)
    self.assertEqual(reformatted_code.decode('utf-8'), expected_formatted_code)

  def testDisableWholeDataStructure(self):
    unformatted_code = textwrap.dedent(u"""\
        A = set([
            'hello',
            'world',
        ])  # yapf: disable
        """)
    expected_formatted_code = textwrap.dedent(u"""\
        A = set([
            'hello',
            'world',
        ])  # yapf: disable
        """)

    p = subprocess.Popen(YAPF_BINARY,
                         stdout=subprocess.PIPE,
                         stdin=subprocess.PIPE,
                         stderr=subprocess.STDOUT)
    reformatted_code, stderrdata = p.communicate(
        unformatted_code.encode('utf-8'))
    self.assertIsNone(stderrdata)
    self.assertEqual(reformatted_code.decode('utf-8'), expected_formatted_code)


if __name__ == '__main__':
  unittest.main()
