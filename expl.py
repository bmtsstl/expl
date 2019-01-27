from pathlib import Path
import urwid
import subprocess


class Pane(urwid.Frame):
    def __init__(self, path):
        path = self._convert_path(path)
        addressbar = AddressBar(path)
        entrylistbox = EntryListBox(path, self)
        super().__init__(entrylistbox, header=addressbar)
        self.path = path

    def browse(self, path):
        self.path = self._convert_path(path)
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

    @staticmethod
    def _convert_path(v):
        if isinstance(v, str):
            v = Path(v)
        elif not isinstance(v, Path):
            raise TypeError('expected {} but {} found.'.format(Path, type(v)))
        return v.resolve()


class EntryListBox(urwid.ListBox):
    def __init__(self, path, pane):
        super().__init__([])
        self._pane = pane
        self.update(path)

    def update(self, path):
        self.path = path
        self.body = [Entry(p, self._pane) for p in path.iterdir()]

    def keypress(self, size, key):
        if key == 'c':
            clipboard.copy([self.focus.path])
            return
        if key == 'x':
            clipboard.cut([self.focus.path])
            return
        if key == 'v':
            clipboard.paste(self.path)
            self.update(self.path)
            return
        return super().keypress(size, key)


class Entry(urwid.WidgetWrap):
    def __init__(self, path, pane):
        name = path.name
        if path.is_dir():
            name += '/'
        checkbox = urwid.CheckBox(name)
        super().__init__(checkbox)

        self._pane = pane
        self.path = path

    def keypress(self, size, key):
        if key == 'enter' and self.path.is_dir():
            self._pane.browse(self.path)
            return
        return key


class AddressBar(urwid.WidgetWrap):
    def __init__(self, path):
        super().__init__(urwid.Text(''))
        self.update(path)

    def update(self, path):
        self.path = path
        self._w.set_text(str(path))


class Footer(urwid.WidgetWrap):
    def __init__(self):
        self._w_text = urwid.Text('')
        self._w_edit = urwid.Edit('')
        self._input_callback = None
        super().__init__(self._w_text)

    def echo(self, msg):
        self._w_text.set_text(str(msg))

    def input(self, prompt, callback, text=''):
        self._w_edit.set_caption(prompt)
        self._w_edit.set_edit_text(text)
        self._input_callback = callback
        self._w = self._w_edit

    def keypress(self, size, key):
        if self._w is self._w_edit and key == 'enter':
            self._input_callback(self._w_edit.edit_text)
            self._w = self._w_text
            return
        return super().keypress(size, key)


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
