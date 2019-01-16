import unittest
from unittest import mock
import expl

from pathlib import Path
import tempfile
import shutil


class TestCase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp()).resolve()
        for i in range(5):
            fpath = self.tmpdir / str(i)
            fpath.touch()
        for i in range(5, 10):
            dpath = self.tmpdir / str(i)
            dpath.mkdir()
            for j in range(5):
                fpath = dpath / str(j)
                fpath.touch()
            for j in range(5):
                fpath = dpath / (str(i) + str(j))
                fpath.touch()

    def tearDown(self):
        shutil.rmtree(str(self.tmpdir))

    def test_pane(self):
        pane = expl.Pane()
        self.assertEqual(pane.path, None)
        self.assertEqual(pane.addressbar.path, None)
        self.assertEqual(pane.entrylistbox.path, None)

        pane.browse(self.tmpdir)
        self.assertEqual(pane.path, self.tmpdir)
        self.assertEqual(pane.addressbar.path, self.tmpdir)
        self.assertEqual(pane.entrylistbox.path, self.tmpdir)

        pane.keypress((100, 100), 'r')
        self.assertEqual(pane.path, self.tmpdir)
        self.assertEqual(pane.addressbar.path, self.tmpdir)
        self.assertEqual(pane.entrylistbox.path, self.tmpdir)

        for path in self.tmpdir.iterdir():
            if not path.is_dir():
                continue

            pane.browse(path)
            self.assertEqual(pane.path, path)
            self.assertEqual(pane.addressbar.path, path)
            self.assertEqual(pane.entrylistbox.path, path)

            pane.browse(path / '..')
            self.assertEqual(pane.path, self.tmpdir)
            self.assertEqual(pane.addressbar.path, self.tmpdir)
            self.assertEqual(pane.entrylistbox.path, self.tmpdir)

            pane.browse(path)
            pane.keypress((100, 100), 'backspace')
            self.assertEqual(pane.path, self.tmpdir)
            self.assertEqual(pane.addressbar.path, self.tmpdir)
            self.assertEqual(pane.entrylistbox.path, self.tmpdir)

    @mock.patch.object(expl, 'Pane', mock.Mock(spec_set=expl.Pane))
    def test_entrylistbox(self):
        pane = expl.Pane()

        entrylistbox = expl.EntryListBox()
        self.assertEqual(entrylistbox.path, None)
        self.assertTrue(len(entrylistbox.body) == 0)

        entrylistbox.set_pane(pane)
        self.assertTrue(len(entrylistbox.body) == 0)

        entrylistbox = expl.EntryListBox(self.tmpdir)
        self.assertEqual(
            [entry.path for entry in entrylistbox.body],
            list(self.tmpdir.iterdir()))

        entrylistbox.set_pane(pane)
        for entry in entrylistbox.body:
            self.assertEqual(entry._pane, pane)

        for path in self.tmpdir.iterdir():
            if not path.is_dir():
                continue
            entrylistbox.update(path)
            for entry in entrylistbox.body:
                self.assertEqual(entry._pane, pane)

    @mock.patch.object(expl, 'Pane', mock.Mock(spec_set=expl.Pane))
    def test_entry(self):
        pane = expl.Pane()
        size = (100, 1)

        for path in self.tmpdir.iterdir():
            entry = expl.Entry(path)
            if path.is_dir():
                self.assertEqual(entry._w.label, path.name + '/')
            else:
                self.assertEqual(entry._w.label, path.name)

            key = entry.keypress(size, 'enter')
            self.assertEqual(key, 'enter')

            key = entry.keypress(size, 'backspace')
            self.assertEqual(key, 'backspace')

            entry.set_pane(pane)
            key = entry.keypress(size, 'enter')
            if path.is_dir():
                self.assertEqual(key, None)
                pane.browse.assert_called_with(path)
            else:
                self.assertEqual(key, 'enter')
                pane.browse.assert_not_called()
            pane.reset_mock()

            key = entry.keypress(size, 'backspace')
            self.assertEqual(key, 'backspace')
            pane.browse.assert_not_called()
            pane.reset_mock()

    def test_clipboard(self):
        clipboard = expl.Clipboard()
        self.assertEqual(clipboard._src, [])
        self.assertEqual(clipboard._op, None)

        clipboard.copy(self.tmpdir.iterdir())
        self.assertEqual(clipboard._src, list(self.tmpdir.iterdir()))
        self.assertEqual(clipboard._op, 'copy')

        clipboard.cut(self.tmpdir.iterdir())
        self.assertEqual(clipboard._src, list(self.tmpdir.iterdir()))
        self.assertEqual(clipboard._op, 'cut')

        def lspath(path):
            return sorted(path.iterdir())

        def lsname(path):
            return sorted([p.name for p in path.iterdir()])

        srcpath = lspath(self.tmpdir)
        srcname = lsname(self.tmpdir)
        with tempfile.TemporaryDirectory() as dst:
            dst = Path(dst)
            clipboard.copy(srcpath)
            clipboard.paste(dst)
            self.assertEqual(lsname(self.tmpdir), srcname)
            self.assertEqual(lsname(dst), srcname)
            self.assertEqual(sorted(clipboard._src), srcpath)
            self.assertEqual(clipboard._op, 'copy')

        with tempfile.TemporaryDirectory() as dst:
            dst = Path(dst)
            clipboard.cut(self.tmpdir.iterdir())
            clipboard.paste(dst)
            self.assertEqual(lsname(self.tmpdir), [])
            self.assertEqual(lsname(dst), srcname)
            self.assertEqual(sorted(clipboard._src), [])
            self.assertEqual(clipboard._op, None)


if __name__ == '__main__':
    unittest.main()
