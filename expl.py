from pathlib import Path
import urwid
import subprocess


class Top(urwid.Frame):
    def __init__(self, path):
        pane = Pane(path)
        footer = Footer()
        super().__init__(pane, footer=footer)

    def echo(self, msg):
        return self['footer'].echo(msg)

    def input(self, prompt, callback, text=''):
        def wrapped_callback(text):
            self.contents['body'] = (self.contents['body'][0].base_widget, self.contents['body'][1])
            self.focus_position = 'body'
            return callback(text)
        self['footer'].input(prompt, wrapped_callback, text)
        self.contents['body'] = (urwid.WidgetDisable(self.contents['body'][0]), self.contents['body'][1])
        self.focus_position = 'footer'


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
            return
        if key == 'r':
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
            jobrunner.copy(self._src, dst)
        elif self._op == 'cut':
            jobrunner.move(self._src, dst)
            self.clear()

    def clear(self):
        self._src = []
        self._op = None


class JobRunner:
    def copy(self, src, dst):
        src = [str(s) for s in src]
        dst = str(dst)
        cmd = ['cp', '-r', '--'] + src + [dst]
        self.prompt('copy?', cmd)

    def move(self, src, dst):
        src = [str(s) for s in src]
        dst = str(dst)
        cmd = ['mv', '--'] + src + [dst]
        self.prompt('move?', cmd)

    def prompt(self, text, cmd):
        def callback(input_text):
            if input_text != 'Y' and input_text != 'y' and input_text != '':
                top.echo('canceled')
                return
            subprocess.run(cmd, check=True)
            top.echo('done')
        top.input(text + ' (Y/n)', callback)


top = Top('.')
clipboard = Clipboard()
jobrunner = JobRunner()


def main():
    try:
        urwid.MainLoop(top).run()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
