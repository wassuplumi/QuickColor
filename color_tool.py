"""Local image color adjustment tool. Requires Python, Pillow and Tkinter."""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from PIL import Image, ImageTk, ImageEnhance, ImageOps


def adjust(image, brightness=1, contrast=1, saturation=1, hue=0, red=1, green=1, blue=1):
    image = image.convert('RGB')
    if hue:
        h, s, v = image.convert('HSV').split()
        shift = round(hue * 255 / 360)
        h = h.point([(i + shift) % 256 for i in range(256)])
        image = Image.merge('HSV', (h, s, v)).convert('RGB')
    image = ImageEnhance.Color(image).enhance(saturation)
    image = ImageEnhance.Contrast(image).enhance(contrast)
    image = ImageEnhance.Brightness(image).enhance(brightness)
    channels = [c.point([max(0, min(255, round(i * gain))) for i in range(256)])
                for c, gain in zip(image.split(), (red, green, blue))]
    return Image.merge('RGB', channels)


class App:
    def __init__(self, root):
        self.root = root
        root.title('图像色彩实验室')
        root.geometry('1180x780')
        root.minsize(850, 600)
        self.original = None
        self.pending = None
        self.photos = []
        self.values = {}
        self.path = None
        bar = ttk.Frame(root, padding=12)
        bar.pack(fill='x')
        for text, action in [('打开图片', self.open), ('保存调整图', self.save), ('重置参数', self.reset)]:
            ttk.Button(bar, text=text, command=action).pack(side='left', padx=4)
        self.side_by_side = tk.BooleanVar(value=True)
        ttk.Checkbutton(bar, text='原图 / 调整后对比', variable=self.side_by_side,
                        command=self.schedule).pack(side='left', padx=18)
        self.status = tk.StringVar(value='打开一张图片开始；所有处理均在本机完成')
        ttk.Label(root, textvariable=self.status, padding=(16, 0, 16, 8)).pack(fill='x')
        main = ttk.Frame(root)
        main.pack(fill='both', expand=True)
        panel = ttk.Frame(main, padding=16, width=270)
        panel.pack(side='right', fill='y')
        self.canvas = tk.Canvas(main, bg='#202630', highlightthickness=0)
        self.canvas.pack(side='left', fill='both', expand=True, padx=(12, 0))
        self.canvas.bind('<Configure>', self.schedule)
        specs = [('brightness', '亮度', 0, 2, 1), ('contrast', '对比度', 0, 3, 1),
                 ('saturation', '饱和度', 0, 3, 1), ('hue', '色相偏移（度）', -180, 180, 0),
                 ('red', '红通道增益', 0, 2, 1), ('green', '绿通道增益', 0, 2, 1),
                 ('blue', '蓝通道增益', 0, 2, 1)]
        self.defaults = {key: default for key, _, _, _, default in specs}
        for key, name, low, high, default in specs:
            line = ttk.Frame(panel)
            line.pack(fill='x', pady=(8, 0))
            ttk.Label(line, text=name).pack(side='left')
            var = tk.DoubleVar(value=default)
            self.values[key] = var
            label = ttk.Label(line, width=7, anchor='e')
            label.pack(side='right')
            def changed(*_, v=var, lab=label):
                lab.config(text=f'{v.get():.2f}')
                self.schedule()
            var.trace_add('write', changed)
            changed()
            ttk.Scale(panel, from_=low, to=high, variable=var).pack(fill='x', pady=(3, 5))
        ttk.Label(panel, text='提示：饱和度设为 0 可查看灰度图。\n\n本工具用于图像辅助与对比实验。\n增强后的检测图不能用于色觉诊断，\n识别改善不代表生理色觉恢复。',
                  wraplength=245, foreground='#596575', justify='left').pack(fill='x', pady=20)
        self.schedule()

    def parameters(self):
        return {key: value.get() for key, value in self.values.items()}

    def open(self):
        path = filedialog.askopenfilename(filetypes=[('图片', '*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp'), ('所有文件', '*.*')])
        if not path:
            return
        try:
            with Image.open(path) as source:
                rgba = ImageOps.exif_transpose(source).convert('RGBA')
                background = Image.new('RGBA', rgba.size, 'white')
                self.original = Image.alpha_composite(background, rgba).convert('RGB')
            self.path = Path(path)
            self.status.set(f'{self.path.name}  ·  {self.original.width} × {self.original.height}  ·  预览自动适配，保存使用原始分辨率')
            self.reset()
        except Exception as exc:
            messagebox.showerror('无法打开图片', str(exc))

    def reset(self):
        for key, default in self.defaults.items():
            self.values[key].set(default)
        self.schedule()

    def schedule(self, *_):
        if self.pending:
            self.root.after_cancel(self.pending)
        self.pending = self.root.after(60, self.render)

    def render(self):
        self.pending = None
        self.canvas.delete('all')
        if self.original is None:
            self.canvas.create_text(max(100, self.canvas.winfo_width() // 2),
                                    max(100, self.canvas.winfo_height() // 2),
                                    text='点击「打开图片」\n拖动右侧滑块实时调整', fill='#d5dce6',
                                    font=('Microsoft YaHei UI', 16), justify='center')
            return
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        count = 2 if self.side_by_side.get() else 1
        slot = w / count
        preview = self.original.copy()
        preview.thumbnail((max(1, int(slot - 28)), max(1, h - 66)), Image.Resampling.LANCZOS)
        result = adjust(preview, **self.parameters())
        items = [('原图', preview), ('调整后', result)] if count == 2 else [('调整后', result)]
        self.photos = []
        for i, (label, img) in enumerate(items):
            photo = ImageTk.PhotoImage(img)
            self.photos.append(photo)
            x = slot * (i + 0.5)
            self.canvas.create_text(x, 24, text=label, fill='#d5dce6', font=('Microsoft YaHei UI', 12))
            self.canvas.create_image(x, (h + 32) / 2, image=photo)

    def save(self):
        if self.original is None:
            messagebox.showinfo('提示', '请先打开图片。')
            return
        path = filedialog.asksaveasfilename(initialfile=self.path.stem + '_调整.png',
                                          defaultextension='.png', filetypes=[('PNG 图片', '*.png'), ('JPEG 图片', '*.jpg')])
        if not path:
            return
        if Path(path).resolve() == self.path.resolve():
            if not messagebox.askyesno('覆盖原图', '保存位置与原图相同，确定覆盖吗？'):
                return
        try:
            self.root.config(cursor='watch')
            self.root.update_idletasks()
            result = adjust(self.original, **self.parameters())
            result.save(path, **({'quality': 95} if Path(path).suffix.lower() in ('.jpg', '.jpeg') else {}))
            messagebox.showinfo('已保存', f'调整图已按原始分辨率保存：\n{path}')
        except Exception as exc:
            messagebox.showerror('保存失败', str(exc))
        finally:
            self.root.config(cursor='')


if __name__ == '__main__':
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    window = tk.Tk()
    App(window)
    window.mainloop()
