"""Smoke check: hotkey thread -> Tk event dispatch -> capture -> editor."""
import threading
import queue
from types import SimpleNamespace
import quick_color as q

app = q.QuickColor.__new__(q.QuickColor)
app.root = q.tk.Tk()
app.root.withdraw()
app.overlay = app.editor = app.image = app.pending = None
app.vars = {}
app.show_original = False
app.events = queue.Queue()
app.hotkey_ready = threading.Event()
app.hotkey_ok = False
worker = threading.Thread(target=app.listen_hotkey, daemon=True)
worker.start()
assert app.hotkey_ready.wait(3) and app.hotkey_ok, 'Hotkey registration failed'
assert q.user32.PostThreadMessageW(app.hotkey_thread_id, 0x0312, 1, 0), 'Hotkey message failed'
assert app.events.get(timeout=3) == 'capture'
app.select()
app.root.update_idletasks()
rect = q.wintypes.RECT()
hwnd = q.user32.GetAncestor(app.overlay.winfo_id(), 2)
q.user32.GetWindowRect(hwnd, q.ctypes.byref(rect))
assert (rect.left, rect.top, rect.right-rect.left, rect.bottom-rect.top) == (app.left, app.top, *app.screen.size), 'Overlay and screenshot coordinates differ'
print(f'Virtual desktop: origin=({app.left},{app.top}), bitmap={app.screen.size}, overlay matches', flush=True)
app.begin(SimpleNamespace(x_root=app.left+40, y_root=app.top+40))
app.finish(SimpleNamespace(x_root=app.left+360, y_root=app.top+280))
app.root.update_idletasks()
app.render()
assert app.image.size == (320, 240)
assert app.editor.winfo_exists()
app.schedule()
timer = app.pending
app.schedule()
assert timer == app.pending, 'Dragging must not postpone the queued frame'
def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)
entries = [w for w in descendants(app.editor) if isinstance(w, q.ttk.Spinbox)]
assert len(entries) == 5
entries[0].delete(0, 'end')
entries[0].insert(0, '12.345')
app.root.tk.call(entries[0].cget('command'))
assert app.vars['hue'].get() == 12.345
for widget in descendants(app.editor):
    if widget.winfo_manager() and isinstance(widget, (q.ttk.Button, q.ttk.Spinbox)):
        assert widget.winfo_rooty() + widget.winfo_height() <= app.editor.winfo_rooty() + app.editor.winfo_height(), 'Control clipped'
app.vars['hue'].set(90)
app.render()
app.set_tint('#ff8800')
assert app.vars['tint'].get() == 0.25
app.render()
app.compare_image(True)
app.render()
app.reset()
assert app.vars['hue'].get() == 0
assert app.vars['tint'].get() == 0
q.user32.PostThreadMessageW(app.hotkey_thread_id, 0x0012, 0, 0)
worker.join(3)
assert not worker.is_alive()
app.root.destroy()
print('PASS: registered hotkey, thread delivery, screen crop, floating editor, sliders, compare, reset', flush=True)
