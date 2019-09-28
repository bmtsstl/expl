#!/usr/bin/env python3
import subprocess
from pathlib import Path

import urwid


class Top(urwid.Frame):
    def __init__(self, path):
        pane = Pane(path)
        footer = Footer()
        super().__init__(pane, footer=footer)
        self._expl_pane = pane
        self._expl_footer = footer

    def echo(self, msg):
        return self._expl_footer.echo(msg)

    def input(self, prompt, callback, default=''):
        def wrapped_callback(*args, **kwargs):
            self.contents['body'] = (
                self._expl_pane, *self.contents['body'][1:])
            self.focus_position = 'body'
            return callback(*args, **kwargs)
        self._expl_footer.input(prompt, wrapped_callback, default=default)
        self.contents['body'] = (
            urwid.WidgetDisable(self._expl_pane),
            *self.contents['body'][1:]
        )
        self.focus_position = 'footer'


class Pane(urwid.Frame):
    def __init__(self, path):
        path = Path(path).resolve()
        addressbar = AddressBar(path)
        entrylistbox = EntryListBox(path)
        super().__init__(entrylistbox, header=addressbar)
        self.path = path

    def browse(self, path):
        self.path = Path(path).resolve()
        self.addressbar.update(self.path)
        self.entrylistbox.update(self.path)

    def keypress(self, size, key):
        if key == 'enter' and isinstance(self.focus, EntryListBox):
            focused_path = self.focus.focused_path()
            if focused_path is not None and focused_path.is_dir():
                self.browse(self.focus.focused_path())
                return
        if key == 'backspace':
            self.browse(self.path.parent)
            return
        if super().keypress(size, key) != key:
            return
        return key

    @property
    def addressbar(self):
        return self.contents['header'][0]

    @property
    def entrylistbox(self):
        return self.contents['body'][0]


class EntryListBox(urwid.ListBox):
    def __init__(self, path):
        super().__init__([])
        self.update(path)

    def update(self, path):
        self.path = path
        self.body = [Entry(p) for p in path.iterdir()]
        self.body.sort(key=lambda entry: entry.path)

    def focused_path(self):
        if isinstance(self.focus, Entry):
            return self.focus.path
        return None

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
        if key == 'd':
            jobrunner.delete([self.focus.path])
            return
        if key == 'r':
            jobrunner.rename(self.focus.path)
            return
        if key == 'f5':
            self.update(self.path)
            return
        return super().keypress(size, key)


class Entry(urwid.WidgetWrap):
    def __init__(self, path):
        path = Path(path).resolve()
        name = path.name
        if path.is_dir():
            name += '/'
        checkbox = urwid.CheckBox(name)
        super().__init__(checkbox)
        self.path = path


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

    def input(self, prompt, callback, default=''):
        self._w_edit.set_caption(prompt)
        self._w_edit.set_edit_text(default)
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
        top.echo(str(len(self._src)) + ' copied to clipboard')

    def cut(self, src):
        self._src = list(src)
        self._op = 'cut'
        top.echo(str(len(self._src)) + ' cutted to clipboard')

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

    def delete(self, path):
        path = [str(p) for p in path]
        cmd = ['rm', '-r', '--'] + path
        self.prompt('delete?', cmd)

    def prompt(self, text, cmd, default=''):
        def callback(input_text):
            if input_text != 'Y' and input_text != 'y' and input_text != '':
                top.echo('canceled')
                return
            subprocess.run(cmd, check=True)
            top.echo('done')
        top.input(text + ' (Y/n)', callback, default)

    def rename(self, path):
        path = Path(path)

        def callback(text):
            renamed_path = path.with_name(text)
            if renamed_path.exists():
                top.echo(text + ' already exists')
                return
            cmd = ['mv', str(path), str(renamed_path)]
            subprocess.run(cmd, check=True)
            top.echo('done')
        top.input('rename: ', callback, default=path.name)


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
