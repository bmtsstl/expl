#!/usr/bin/env python3
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import urwid

import expl


class PaneTestCase(unittest.TestCase):
    def test_init(self):
        with tempfile.TemporaryDirectory() as tempdir:
            tempdir = Path(tempdir)
            pane = expl.Pane(tempdir)
            self.assertEqual(pane.path, tempdir)
            self.assertEqual(pane.addressbar.path, tempdir)
            self.assertEqual(pane.entrylistbox.path, tempdir)

    def test_browse(self):
        with tempfile.TemporaryDirectory() as tempdir:
            subdir = Path(tempdir, 'subdir')
            subdir.mkdir()

            pane = expl.Pane(tempdir)
            pane.browse(subdir)
            self.assertEqual(pane.path, subdir)
            self.assertEqual(pane.addressbar.path, subdir)
            self.assertEqual(pane.entrylistbox.path, subdir)

    def test_keypress_enter(self):
        with tempfile.TemporaryDirectory() as tempdir:
            tempdir = Path(tempdir)
            pane = expl.Pane(tempdir)
            pane.keypress((100, 100), 'enter')
            self.assertEqual(pane.path, tempdir)

            Path(tempdir, 'dummy').touch()
            pane.browse(tempdir)
            pane.keypress((100, 100), 'enter')
            self.assertEqual(pane.path, tempdir)

        with tempfile.TemporaryDirectory() as tempdir:
            tempdir = Path(tempdir)
            subdir = Path(tempdir, 'subdir')
            subdir.mkdir()

            pane = expl.Pane(tempdir)
            key = pane.keypress((100, 100), 'enter')
            self.assertEqual(key, None)
            self.assertEqual(pane.path, subdir)

    def test_keypress_backspace(self):
        with tempfile.TemporaryDirectory() as tempdir:
            tempdir = Path(tempdir)
            subdir = Path(tempdir, 'subdir')
            subdir.mkdir()

            pane = expl.Pane(subdir)
            key = pane.keypress((100, 100), 'backspace')
            self.assertEqual(key, None)
            self.assertEqual(pane.path, tempdir)


class TestCase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp()).resolve()
        self.tmpdir.joinpath('1').touch()
        self.tmpdir.joinpath('A').mkdir()
        self.tmpdir.joinpath('B').mkdir()
        self.tmpdir.joinpath('B', 'B1').touch()
        self.tmpdir.joinpath('C').mkdir()
        self.tmpdir.joinpath('C', 'C1').touch()
        self.tmpdir.joinpath('C', 'C2').touch()

    def tearDown(self):
        shutil.rmtree(str(self.tmpdir))

    def test_top(self):
        top = expl.Top('.')

        top.echo('test')
        self.assertEqual(top['footer']._w.text, 'test')

        top.input('prompt', lambda text: None)
        self.assertIs(top.focus, top['footer'])
        self.assertIs(type(top.contents['body'][0]), urwid.WidgetDisable)

        size = (100, 100)
        for c in 'input':
            top.keypress(size, c)
        top.keypress(size, 'enter')
        self.assertIs(top.focus, top['body'])
        self.assertIsNot(type(top.contents['body'][0]), urwid.WidgetDisable)

    @mock.patch.object(expl, 'Pane', mock.Mock(spec_set=expl.Pane))
    def test_entrylistbox(self):
        pane = expl.Pane()

        entrylistbox = expl.EntryListBox(self.tmpdir, pane)
        paths = sorted(self.tmpdir.iterdir())
        focused_path = paths[0] if len(paths) > 0 else None
        self.assertEqual([entry.path for entry in entrylistbox.body], paths)
        for entry in entrylistbox.body:
            self.assertEqual(entry._pane, pane)
        self.assertEqual(entrylistbox.focused_path(), focused_path)

        for path in self.tmpdir.iterdir():
            if not path.is_dir():
                continue
            paths = sorted(path.iterdir())
            focused_path = paths[0] if len(paths) > 0 else None

            entrylistbox.update(path)
            self.assertEqual(
                [entry.path for entry in entrylistbox.body], paths)
            for entry in entrylistbox.body:
                self.assertEqual(entry._pane, pane)
            self.assertEqual(entrylistbox.focused_path(), focused_path)

    @mock.patch.object(expl, 'Pane', mock.Mock(spec_set=expl.Pane))
    def test_entry(self):
        pane = expl.Pane()
        for path in self.tmpdir.iterdir():
            entry = expl.Entry(path, pane)
            if path.is_dir():
                self.assertEqual(entry._w.label, path.name + '/')
            else:
                self.assertEqual(entry._w.label, path.name)

    def test_footer(self):
        footer = expl.Footer()
        self.assertIs(type(footer._w_text), urwid.Text)
        self.assertIs(type(footer._w_edit), urwid.Edit)
        self.assertIs(footer._w, footer._w_text)

        footer.echo('test')
        self.assertEqual(footer._w_text.text, 'test')

        def callback(text):
            nonlocal input_text
            input_text = text
        input_text = ''
        footer.input('prompt', callback)
        self.assertEqual(footer._w_edit.caption, 'prompt')
        self.assertIs(footer._w, footer._w_edit)

        footer.echo('test2')
        self.assertEqual(footer._w_text.text, 'test2')
        self.assertIs(footer._w, footer._w_edit)

        size = (100,)
        for c in 'input':
            footer.keypress(size, c)
        footer.keypress(size, 'enter')
        self.assertEqual(footer._w_edit.edit_text, 'input')
        self.assertIs(footer._w, footer._w_text)
        self.assertEqual(input_text, 'input')

    @mock.patch.object(expl, 'jobrunner', mock.Mock(spec_set=expl.jobrunner))
    def test_clipboard(self):
        clipboard = expl.Clipboard()
        self.assertEqual(clipboard._src, [])
        self.assertEqual(clipboard._op, None)

        with tempfile.TemporaryDirectory() as dst:
            clipboard.copy(self.tmpdir.iterdir())
            self.assertEqual(clipboard._src, list(self.tmpdir.iterdir()))
            self.assertEqual(clipboard._op, 'copy')

            clipboard.paste(dst)
            self.assertEqual(clipboard._src, list(self.tmpdir.iterdir()))
            self.assertEqual(clipboard._op, 'copy')
            expl.jobrunner.copy.assert_called_once_with(
                list(self.tmpdir.iterdir()), dst)
            expl.jobrunner.copy.reset_mock()

            clipboard.clear()
            self.assertEqual(clipboard._src, [])
            self.assertEqual(clipboard._op, None)

            clipboard.cut(self.tmpdir.iterdir())
            self.assertEqual(clipboard._src, list(self.tmpdir.iterdir()))
            self.assertEqual(clipboard._op, 'cut')

            clipboard.paste(dst)
            self.assertEqual(clipboard._src, [])
            self.assertEqual(clipboard._op, None)
            expl.jobrunner.move.assert_called_once_with(
                list(self.tmpdir.iterdir()), dst)
            expl.jobrunner.move.reset_mock()

    @mock.patch.object(expl, 'top', mock.Mock(spec_set=expl.top))
    def test_jobrunner(self):
        jobrunner = expl.JobRunner()

        def lspath(path):
            return sorted(path.iterdir())

        def lsname(path):
            return sorted([p.name for p in path.iterdir()])

        jobrunner.prompt('prompt', ['true'])
        expl.top.input.assert_called_once()
        self.assertEqual(expl.top.input.call_args[0][0], 'prompt (Y/n)')
        callback = expl.top.input.call_args[0][1]
        expl.top.input.reset_mock()

        callback('')
        expl.top.echo.assert_called_once_with('done')
        expl.top.echo.reset_mock()

        callback('n')
        expl.top.echo.assert_called_once_with('canceled')
        expl.top.echo.reset_mock()

        ls = lsname(self.tmpdir)
        with tempfile.TemporaryDirectory() as dst:
            dst = Path(dst)
            jobrunner.copy(lspath(self.tmpdir), dst)
            expl.top.input.assert_called_once()
            callback = expl.top.input.call_args[0][1]
            expl.top.input.reset_mock()

            callback('y')
            self.assertEqual(lsname(self.tmpdir), ls)
            self.assertEqual(lsname(dst), ls)

            jobrunner.rename(lspath(dst)[0])
            expl.top.input.assert_called_once()
            callback = expl.top.input.call_args[0][1]
            expl.top.input.reset_mock()

            callback('renamed')
            self.assertTrue('renamed' in lsname(dst))

            jobrunner.delete(lspath(dst))
            expl.top.input.assert_called_once()
            callback = expl.top.input.call_args[0][1]
            expl.top.input.reset_mock()

            callback('y')
            self.assertEqual(lsname(dst), [])

        with tempfile.TemporaryDirectory() as dst:
            dst = Path(dst)
            jobrunner.move(lspath(self.tmpdir), dst)
            expl.top.input.assert_called_once()
            callback = expl.top.input.call_args[0][1]
            expl.top.input.reset_mock()

            callback('y')
            self.assertEqual(lsname(self.tmpdir), [])
            self.assertEqual(lsname(dst), ls)

            jobrunner.move(lspath(dst), self.tmpdir)
            expl.top.input.assert_called_once()
            callback = expl.top.input.call_args[0][1]
            expl.top.input.reset_mock()

            callback('y')
            self.assertEqual(lsname(self.tmpdir), ls)
            self.assertEqual(lsname(dst), [])


if __name__ == '__main__':
    unittest.main()
