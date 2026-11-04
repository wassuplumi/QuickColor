"""Windows: Alt+Shift+C, select screen area, adjust in a floating window."""
import ctypes
from ctypes import wintypes
import tkinter as tk
import threading
import queue
import logging
import os
import sys
from pathlib import Path
from tkinter import ttk, messagebox, colorchooser
from PIL import Image, ImageGrab, ImageTk, ImageDraw
from color_tool import adjust

LOG_DIR = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'QuickColor'
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(filename=LOG_DIR / 'runtime.log', level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s', encoding='utf-8')

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
user32.GetAncestor.restype = wintypes.HWND
user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT]
user32.SetWindowPos.restype = wintypes.BOOL
kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.CreateMutexW.restype = wintypes.HANDLE
MUTEX = kernel32.CreateMutexW(None, False, 'Local\\QuickColorScreenshotTool')
if kernel32.GetLastError() == 183:
    user32.MessageBoxW(None, '工具已经在运行，按 Alt + Shift + C 框选屏幕。', '截图调色', 0)
    raise SystemExit
try:
    user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
except Exception:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass


class QuickColor:
    def __init__(self):
        self.root = tk.Tk()
        self.root.report_callback_exception = self.callback_error
        self.root.withdraw()
        self.overlay = None
        self.editor = None
        self.image = None
        self.pending = None
        self.vars = {}
        self.tint_color = '#ffffff'
        self.show_original = False
        self.preview_key = None
        self.tray = None
        self.events = queue.Queue()
        self.hotkey_ready = threading.Event()
        self.hotkey_ok = False
        self.hotkey_thread = threading.Thread(target=self.listen_hotkey, daemon=True)
        self.hotkey_thread.start()
        self.hotkey_ready.wait(3)
        if not self.hotkey_ok:
            messagebox.showerror('快捷键被占用', 'Alt + Shift + C 已被其他程序占用，请关闭冲突程序后重新启动。')
            self.root.destroy()
            return
        logging.info('Started; Alt+Shift+C registered')
        self.start_tray()
        self.root.after(60, self.poll)
        self.root.after(100, self.welcome)
        self.root.protocol('WM_DELETE_WINDOW', self.quit)
        try:
            self.root.mainloop()
        finally:
            if getattr(self, 'hotkey_thread_id', None):
                user32.PostThreadMessageW(self.hotkey_thread_id, 0x0012, 0, 0)

    def listen_hotkey(self):
        self.hotkey_thread_id = kernel32.GetCurrentThreadId()
        self.hotkey_ok = bool(user32.RegisterHotKey(None, 1, 0x0001 | 0x0004 | 0x4000, ord('C')))
        self.hotkey_ready.set()
        if not self.hotkey_ok:
            return
        msg = wintypes.MSG()
        try:
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                if msg.message == 0x0312 and msg.wParam == 1:
                    logging.info('Hotkey received')
                    self.events.put('capture')
        finally:
            user32.UnregisterHotKey(None, 1)

    def welcome(self):
        if getattr(self, 'notice', None) is not None and self.notice.winfo_exists():
            self.notice.deiconify()
            self.notice.lift()
            return
        self.notice = tk.Toplevel(self.root)
        self.notice.title('截图调色 · 已启动')
        self.notice.attributes('-topmost', True)
        self.notice.resizable(False, False)
        box = ttk.Frame(self.notice, padding=20)
        box.pack()
        ttk.Label(box, text='按 Alt + Shift + C 框选屏幕', font=('Microsoft YaHei UI', 12)).pack(pady=(0, 10))
        ttk.Label(box, text='框选后拖动滑块调色，Esc 取消框选。\n关闭窗口后继续在后台运行。\n右下角托盘彩色圆环：右键可框选或退出。').pack()
        ttk.Button(box, text='立即框选', command=self.capture).pack(fill='x', pady=(14, 4))
        ttk.Button(box, text='隐藏，等待快捷键', command=self.notice.destroy).pack(fill='x', pady=4)
        ttk.Button(box, text='退出工具', command=self.quit).pack(fill='x', pady=4)

    def start_tray(self):
        try:
            import pystray
            icon = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
            draw = ImageDraw.Draw(icon)
            for i, color in enumerate(['#ff6868', '#ffc857', '#52cf9b', '#5bafff', '#b58cff', '#fa80b5']):
                draw.pieslice((5, 5, 59, 59), i*60, (i+1)*60, fill=color)
            draw.ellipse((23, 23, 41, 41), fill='#ffffff')
            menu = pystray.Menu(
                pystray.MenuItem('框选调色  Alt+Shift+C', lambda *_: self.events.put('capture'), default=True),
                pystray.MenuItem('显示控制面板', lambda *_: self.events.put('panel')),
                pystray.MenuItem('退出工具', lambda *_: self.events.put('quit')))
            self.tray = pystray.Icon('QuickColor', icon, '截图调色 · Alt+Shift+C', menu)
            def ready(icon):
                icon.visible = True
                logging.info('Tray icon visible')
            threading.Thread(target=self.tray.run, kwargs={'setup': ready}, daemon=True).start()
        except Exception:
            logging.exception('Tray unavailable')

    def poll(self):
        try:
            while True:
                event = self.events.get_nowait()
                if event == 'capture':
                    self.capture()
                elif event == 'panel':
                    self.welcome()
                elif event == 'quit':
                    self.quit()
                    return
        except queue.Empty:
            pass
        except Exception:
            logging.exception('Capture dispatch failed')
        finally:
            if not getattr(self, 'stopping', False):
                self.root.after(60, self.poll)

    def callback_error(self, exc_type, exc_value, tb):
        logging.error('Window callback failed', exc_info=(exc_type, exc_value, tb))
        messagebox.showerror('截图调色遇到错误', f'{exc_value}\n错误日志：{LOG_DIR / "runtime.log"}')

    def capture(self):
        if self.overlay is not None:
            return
        if getattr(self, 'notice', None) is not None and self.notice.winfo_exists():
            self.notice.destroy()
        if self.editor is not None and self.editor.winfo_exists():
            self.editor.withdraw()
        self.root.after(180, self.select)

    def select(self):
        if self.overlay is not None:
            return
        try:
            self.screen = ImageGrab.grab(all_screens=True)
        except Exception as exc:
            messagebox.showerror('无法截图', str(exc))
            self.restore()
            return
        self.left = user32.GetSystemMetrics(76)
        self.top = user32.GetSystemMetrics(77)
        width, height = self.screen.size
        self.overlay = tk.Toplevel(self.root)
        self.overlay.overrideredirect(True)
        self.overlay.geometry(f'{width}x{height}+0+0')
        self.overlay.attributes('-topmost', True)
        self.canvas = tk.Canvas(self.overlay, highlightthickness=0, cursor='crosshair')
        self.canvas.pack(fill='both', expand=True)
        self.overlay.update_idletasks()
        # winfo_id is Tk's inner window. Move its native top-level wrapper,
        # using physical virtual-desktop coordinates (which can be negative).
        hwnd = user32.GetAncestor(self.overlay.winfo_id(), 2)
        if not user32.SetWindowPos(hwnd, wintypes.HWND(-1), self.left, self.top, width, height, 0x0040):
            self.overlay.destroy()
            self.overlay = None
            messagebox.showerror('框选窗口定位失败', '无法定位多屏框选窗口，请重新尝试。')
            self.restore()
            return
        self.overlay.update_idletasks()
        self.screen_photo = ImageTk.PhotoImage(self.screen)
        self.canvas.create_image(0, 0, image=self.screen_photo, anchor='nw')
        self.canvas.create_rectangle(0, 0, width, height, fill='black', stipple='gray50', outline='')
        self.canvas.create_text(30, 40, anchor='nw', text='拖动框选需要调色的区域 · Esc 取消', fill='white', font=('Microsoft YaHei UI', 17))
        self.start = None
        self.rect = None
        self.canvas.bind('<ButtonPress-1>', self.begin)
        self.canvas.bind('<B1-Motion>', self.drag)
        self.canvas.bind('<ButtonRelease-1>', self.finish)
        self.overlay.bind('<Escape>', lambda _: self.cancel())
        self.overlay.bind('<Button-3>', lambda _: self.cancel())
        self.overlay.focus_force()
        self.overlay.grab_set()

    def begin(self, event):
        self.start = self.selection_point(event)
        if self.rect:
            self.canvas.delete(self.rect)
        self.rect = self.canvas.create_rectangle(*self.start, *self.start, outline='#40dfff', width=3)

    def selection_point(self, event):
        # Convert screen coordinates into the captured virtual-desktop bitmap.
        x = event.x_root - self.left
        y = event.y_root - self.top
        return max(0, min(self.screen.width, x)), max(0, min(self.screen.height, y))

    def drag(self, event):
        if self.start:
            self.canvas.coords(self.rect, *self.start, *self.selection_point(event))

    def close_overlay(self):
        self.overlay.grab_release()
        self.overlay.destroy()
        self.overlay = None
        self.screen_photo = None

    def restore(self):
        if self.editor is not None and self.editor.winfo_exists():
            self.editor.deiconify()

    def cancel(self):
        self.close_overlay()
        self.screen = None
        self.restore()

    def finish(self, event):
        if not self.start:
            return
        end = self.selection_point(event)
        x1, x2 = sorted((self.start[0], end[0]))
        y1, y2 = sorted((self.start[1], end[1]))
        if x2 - x1 < 8 or y2 - y1 < 8:
            self.cancel()
            return
        self.image = self.screen.crop((x1, y1, x2, y2)).convert('RGB')
        self.screen = None
        self.close_overlay()
        self.open_editor()

    def open_editor(self):
        if self.pending:
            self.root.after_cancel(self.pending)
            self.pending = None
        if self.editor is not None and self.editor.winfo_exists():
            self.editor.destroy()
        self.editor = tk.Toplevel(self.root)
        self.editor.title('截图调色 · Alt+Shift+C 重新框选')
        self.editor.attributes('-topmost', True)
        self.editor.geometry('760x700')
        self.editor.minsize(650, 600)
        self.view = tk.Canvas(self.editor, bg='#252a32', highlightthickness=0)
        # Allocate controls first so the expandable preview cannot push them
        # outside the client area on high-DPI displays.
        self.view.bind('<Configure>', self.schedule)
        panel = ttk.Frame(self.editor, padding=(12, 0, 12, 8))
        panel.pack(side='bottom', fill='x')
        self.view.pack(side='top', fill='both', expand=True, padx=8, pady=8)
        self.vars = {}
        self.tint_color = '#ffffff'
        for row, (key, label, low, high, default) in enumerate([
            ('hue', '色相', -180, 180, 0), ('saturation', '饱和度', 0, 3, 1),
            ('contrast', '对比度', 0, 3, 1), ('brightness', '亮度', 0, 2, 1),
            ('tint', '着色强度', 0, 1, 0)]):
            var = tk.DoubleVar(value=default)
            self.vars[key] = var
            ttk.Label(panel, text=label, width=8).grid(row=row, column=0, pady=3)
            value_text = tk.StringVar(value=f'{default:.3f}')
            step = 1 if key == 'hue' else 0.01
            def commit(event=None, v=var, text=value_text, low=low, high=high):
                try:
                    value = float(text.get())
                    if not __import__('math').isfinite(value):
                        raise ValueError
                    v.set(max(low, min(high, value)))
                except ValueError:
                    text.set(f'{v.get():.3f}')
                return 'break' if event and event.type == '2' else None
            entry = ttk.Spinbox(panel, from_=low, to=high, increment=step, textvariable=value_text,
                                width=8, command=commit)
            entry.grid(row=row, column=2, padx=(6, 0))
            entry.bind('<Return>', commit)
            entry.bind('<FocusOut>', commit)
            def change(*_, v=var, text=value_text):
                text.set(f'{v.get():.3f}')
                self.schedule()
            slider = ttk.Scale(panel, from_=low, to=high, variable=var, takefocus=True)
            slider.grid(row=row, column=1, sticky='ew', padx=5, pady=5)
            def nudge(event, direction=None, v=var, low=low, high=high, step=step):
                direction = direction if direction is not None else (1 if event.delta > 0 else -1)
                amount = step / 10 if event.state & 1 else step
                v.set(round(max(low, min(high, v.get() + direction * amount)), 4))
                return 'break'
            slider.bind('<Left>', lambda e, fn=nudge: fn(e, -1))
            slider.bind('<Right>', lambda e, fn=nudge: fn(e, 1))
            slider.bind('<MouseWheel>', nudge)
            var.trace_add('write', change)
            change()
        panel.columnconfigure(1, weight=1)
        actions = ttk.Frame(panel)
        palette = ttk.Frame(panel)
        palette.grid(row=5, column=0, columnspan=3, sticky='ew', pady=(6, 0))
        ttk.Button(palette, text='调色盘…', command=self.choose_color).pack(side='left')
        self.swatch = tk.Label(palette, text='  #FFFFFF  ', bg=self.tint_color, relief='solid', borderwidth=1)
        self.swatch.pack(side='left', padx=10)
        ttk.Label(palette, text='选颜色后拖动“着色强度”').pack(side='left')
        actions.grid(row=6, column=0, columnspan=3, sticky='ew', pady=(8, 0))
        ttk.Button(actions, text='重新框选', command=self.capture).pack(side='left')
        ttk.Button(actions, text='重置', command=self.reset).pack(side='left', padx=6)
        self.compare = ttk.Button(actions, text='按住看原图')
        self.compare.pack(side='left')
        self.compare.bind('<ButtonPress-1>', lambda _: self.compare_image(True))
        self.compare.bind('<ButtonRelease-1>', lambda _: self.compare_image(False))
        self.compare.bind('<Leave>', lambda _: self.compare_image(False))
        ttk.Button(actions, text='退出工具', command=self.quit).pack(side='right')
        ttk.Label(panel, text='滚轮 / 方向键微调 · 按住 Shift 更精细 · 数值输入后按回车', foreground='#667080').grid(row=7, column=0, columnspan=3, pady=(8, 0))
        ttk.Label(panel, text='仅调整截图预览 · 不改变原窗口 · 不用于色觉诊断', foreground='#667080').grid(row=8, column=0, columnspan=3, pady=(4, 0))
        self.show_original = False
        self.editor.update_idletasks()
        required_width = max(650, panel.winfo_reqwidth() + 24)
        required_height = max(600, panel.winfo_reqheight() + 200)
        self.editor.minsize(required_width, required_height)
        self.editor.geometry(f'{max(760, required_width)}x{max(700, required_height)}')
        self.editor.lift()
        self.editor.focus_force()
        self.schedule()

    def compare_image(self, original):
        self.show_original = original
        self.schedule()

    def reset(self):
        for key, var in self.vars.items():
            var.set(0 if key in ('hue', 'tint') else 1)
        self.tint_color = '#ffffff'
        self.swatch.config(bg=self.tint_color, fg='black', text='  #FFFFFF  ')

    def choose_color(self):
        _, color = colorchooser.askcolor(color=self.tint_color, parent=self.editor, title='选择着色颜色')
        if color:
            self.set_tint(color)

    def set_tint(self, color):
        self.tint_color = color
        rgb = tuple(int(color[i:i+2], 16) for i in (1, 3, 5))
        foreground = 'black' if sum(rgb) > 380 else 'white'
        self.swatch.config(bg=color, fg=foreground, text=f'  {color.upper()}  ')
        if self.vars['tint'].get() == 0:
            self.vars['tint'].set(0.25)
        self.schedule()

    def schedule(self, *_):
        # Throttle, rather than debounce: continuous movement must still render.
        if not self.pending:
            self.pending = self.root.after(16, self.render)

    def render(self):
        self.pending = None
        if self.editor is None or not self.editor.winfo_exists():
            return
        size = (max(1, self.view.winfo_width()-12), max(1, self.view.winfo_height()-12))
        cache_key = (id(self.image), size)
        if getattr(self, 'preview_key', None) != cache_key:
            self.preview_image = self.image.copy()
            self.preview_image.thumbnail(size, Image.Resampling.LANCZOS)
            self.preview_key = cache_key
        im = self.preview_image
        if not self.show_original:
            im = adjust(im, **{key: var.get() for key, var in self.vars.items() if key != 'tint'})
            strength = self.vars['tint'].get()
            if strength:
                im = Image.blend(im, Image.new('RGB', im.size, self.tint_color), strength)
        self.photo = ImageTk.PhotoImage(im)
        self.view.delete('all')
        self.view.create_image(self.view.winfo_width()/2, self.view.winfo_height()/2, image=self.photo)

    def quit(self):
        self.stopping = True
        logging.info('User requested exit')
        if getattr(self, 'tray', None):
            self.tray.stop()
        self.root.destroy()


if __name__ == '__main__':
    QuickColor()
