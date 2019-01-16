from pathlib import Path
import urwid
import subprocess


class Pane(urwid.Frame):
    def __init__(self, path):
        addressbar = AddressBar()
        entrylistbox = EntryListBox()
        super().__init__(entrylistbox, header=addressbar)

        entrylistbox.set_pane(self)
        self.browse(path)

    def browse(self, path):
        if isinstance(path, str):
            path = Path(path)
        elif not isinstance(path, Path):
            raise TypeError('expected {} but {} found.'.format(Path, type(path)))
        path = path.resolve()

        self.path = path
        self.addressbar.update(self.path)
        self.entrylistbox.update(self.path)

    def keypress(self, size, key):
        if super().keypress(size, key) != key:
            return
        if key == 'r':
            self.browse(self.path)
            return
        if key == 'backspace':
            self.browse(self.path.parent)
            return
        return key

    @property
    def addressbar(self):
        return self.contents['header'][0]

    @property
    def entrylistbox(self):
        return self.contents['body'][0]


class EntryListBox(urwid.ListBox):
    def __init__(self, path=None):
        super().__init__([])
        self._pane = None
        self.path = None

        if path is not None:
            self.update(path)

    def update(self, path):
        self.path = path
        self.body = [Entry(p) for p in path.iterdir()]
        self._update_entry_callbacks()

    def set_pane(self, pane):
        self._pane = pane
        self._update_entry_callbacks()

    def keypress(self, size, key):
        if key == 'c':
            clipboard.copy([self.focus.path])
            return
        if key == 'x':
            clipboard.cut([self.focus.path])
            return
        if key == 'v':
            clipboard.paste(self.path)
            return
        return super().keypress(size, key)

    def _update_entry_callbacks(self):
        for entry in self.body:
            entry.set_pane(self._pane)


class Entry(urwid.WidgetWrap):
    def __init__(self, path):
        name = path.name
        if path.is_dir():
            name += '/'
        checkbox = urwid.CheckBox(name)
        super().__init__(checkbox)

        self._pane = None
        self.path = path

    def set_pane(self, pane):
        self._pane = pane

    def keypress(self, size, key):
        if key == 'enter' and self.path.is_dir() and self._pane is not None:
            self._pane.browse(self.path)
            return
        return key


class AddressBar(urwid.WidgetWrap):
    def __init__(self, path=None):
        super().__init__(urwid.Text(''))
        self.path = None

        if path is not None:
            self.update(path)

    def update(self, path):
        self.path = path
        self._w.set_text(str(path))


class Clipboard:
    def __init__(self):
        super().__init__()
        self.clear()

    def copy(self, src):
        self._src = list(src)
        self._op = 'copy'

    def cut(self, src):
        self._src = list(src)
        self._op = 'cut'

    def paste(self, dst):
        if self._op == 'copy':
            cmd = ['cp', '-r', '--'] + [str(s) for s in self._src] + [str(dst)]
            subprocess.run(cmd, check=True)
        elif self._op == 'cut':
            cmd = ['mv', '--'] + [str(s) for s in self._src] + [str(dst)]
            subprocess.run(cmd, check=True)
            self.clear()

    def clear(self):
        self._src = []
        self._op = None


clipboard = Clipboard()

if __name__ == '__main__':
    top = Pane(Path('.'))
    urwid.MainLoop(top).run()
