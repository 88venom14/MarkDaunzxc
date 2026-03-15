import tkinter as tk
from tkinter import messagebox, filedialog
from tkinter.scrolledtext import ScrolledText
from PIL import Image, ImageTk, ImageGrab
import json
import os
import re
import shutil
from datetime import datetime
import markdown

IMAGES_DIR = "images"
MIN_WINDOW_WIDTH = 900
MIN_WINDOW_HEIGHT = 600


def ensure_images_dir():
    if not os.path.exists(IMAGES_DIR):
        os.makedirs(IMAGES_DIR)


class DrawingPopup(tk.Toplevel):
    def __init__(self, parent, on_save_callback):
        super().__init__(parent)
        self.title("Рисование")
        self.geometry("400x300")
        self.resizable(False, False)

        self.color = "black"
        self.last_x = None
        self.last_y = None
        self.on_save_callback = on_save_callback

        self._create_canvas()
        self._create_buttons()

    def _create_canvas(self):
        self.canvas = tk.Canvas(
            self, bg="white", width=400, height=250, cursor="cross"
        )
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.canvas.bind("<ButtonPress-1>", self._on_button_press)
        self.canvas.bind("<B1-Motion>", self._on_mouse_drag)

    def _create_buttons(self):
        frame = tk.Frame(self)
        frame.pack(fill=tk.X)

        tk.Button(
            frame, text="Очистить", command=self.clear, width=10
        ).pack(side=tk.LEFT, padx=5, pady=5)
        tk.Button(
            frame, text="Сохранить и вставить",
            command=self.save, width=18, bg="lightgreen"
        ).pack(side=tk.RIGHT, padx=5, pady=5)

    def _on_button_press(self, event):
        self.last_x = event.x
        self.last_y = event.y

    def _on_mouse_drag(self, event):
        if self.last_x is not None and self.last_y is not None:
            self.canvas.create_line(
                self.last_x, self.last_y, event.x, event.y,
                fill=self.color, width=2, capstyle=tk.ROUND, smooth=True
            )
        self.last_x = event.x
        self.last_y = event.y

    def clear(self):
        self.canvas.delete("all")

    def save(self):
        self.update()
        x = self.winfo_rootx() + self.canvas.winfo_x()
        y = self.winfo_rooty() + self.canvas.winfo_y()
        x1 = x + self.canvas.winfo_width()
        y1 = y + self.canvas.winfo_height()

        img = ImageGrab.grab().crop((x, y, x1, y1))
        filename = f"{IMAGES_DIR}/draw_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.png"
        img.save(filename, "PNG")

        self.on_save_callback(filename)
        self.destroy()


class ContentDisplay(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.images_cache = {}
        self.canvas_items = []
        self._create_widgets()

    def _create_widgets(self):
        self.canvas = tk.Canvas(self, bg="white", highlightthickness=0)
        self.scrollbar = tk.Scrollbar(
            self, orient="vertical", command=self.canvas.yview
        )
        self.scrollable_frame = tk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window(
            (0, 0), window=self.scrollable_frame, anchor="nw"
        )
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

    def clear(self):
        for item in self.canvas_items:
            item.destroy()
        self.canvas_items = []
        self.images_cache.clear()

    def set_content(self, content):
        self.clear()
        lines = content.split('\n')
        for line in lines:
            self._add_line(line)

    def _add_line(self, line):
        match = re.match(r'^!\[image\]\(([^)]+)\)$', line.strip())
        if match:
            self._add_image(match.group(1))
        elif line.strip():
            self._add_text_label(line)
        else:
            self._add_empty_line()

    def _add_image(self, img_path):
        if os.path.exists(img_path):
            try:
                img = Image.open(img_path)
                img.thumbnail((400, 400))
                photo = ImageTk.PhotoImage(img)

                label = tk.Label(self.scrollable_frame, image=photo)
                label.image = photo
                label.pack(pady=2)

                self.images_cache[len(self.images_cache)] = photo
                self.canvas_items.append(label)
            except Exception as e:
                self._add_error_label(f"Ошибка: {e}")
        else:
            self._add_warning_label("Картинка не найдена")

    def _add_text_label(self, text):
        label = tk.Label(
            self.scrollable_frame, text=text,
            anchor="w", font=("Consolas", 11)
        )
        label.pack(fill="x", padx=2)
        self.canvas_items.append(label)

    def _add_empty_line(self):
        label = tk.Label(self.scrollable_frame, text="", height=1)
        label.pack(fill="x")
        self.canvas_items.append(label)

    def _add_error_label(self, message):
        label = tk.Label(
            self.scrollable_frame, text=f"⚠ {message}", fg="red"
        )
        label.pack()
        self.canvas_items.append(label)

    def _add_warning_label(self, message):
        label = tk.Label(
            self.scrollable_frame, text=f"⚠ {message}", fg="orange"
        )
        label.pack()
        self.canvas_items.append(label)


class NotesApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Заметки с Markdown")
        self.root.minsize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
        
        icon_path = os.path.join(os.path.dirname(__file__), "photo_2026-03-15_22-35-31.ico")
        if os.path.exists(icon_path):
            self.root.iconbitmap(icon_path)

        self.notes_file = "notes.json"
        self.notes = self.load_notes()
        self.current_note_id = None
        self.original_content = ""

        self._create_widgets()
        self.load_notes_list()

    def load_notes(self):
        if os.path.exists(self.notes_file):
            with open(self.notes_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def save_notes(self):
        with open(self.notes_file, "w", encoding="utf-8") as f:
            json.dump(self.notes, f, ensure_ascii=False, indent=2)

    def _create_widgets(self):
        self._create_left_panel()
        self._create_right_panel()

    def _create_left_panel(self):
        left = tk.Frame(self.root, bg="#f0f0f0")
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=5, pady=5)

        tk.Label(
            left, text="Все заметки", bg="#f0f0f0",
            font=("Arial", 13, "bold")
        ).pack()

        self.listbox = tk.Listbox(left, width=22)
        self.listbox.pack(fill=tk.BOTH, expand=True, pady=8)
        self.listbox.bind("<<ListboxSelect>>", self.select_note)

        tk.Button(left, text="Новая заметка", command=self.new_note).pack(
            fill=tk.X
        )
        tk.Button(
            left, text="Удалить", command=self.delete_note,
            bg="#f44336", fg="white"
        ).pack(fill=tk.X, pady=2)

    def _create_right_panel(self):
        right = tk.Frame(self.root)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        tk.Label(right, text="Заголовок:").pack(anchor=tk.W, pady=(10, 2))
        self.title_entry = tk.Entry(right, font=("Arial", 12))
        self.title_entry.pack(fill=tk.X, pady=(0, 7))

        self._create_buttons_row(right)
        self._create_content_area(right)

    def _create_buttons_row(self, parent):
        btn_frame = tk.Frame(parent)
        btn_frame.pack(fill=tk.X, pady=4)

        self.edit_btn = tk.Button(
            btn_frame, text="✏️ Редактировать",
            command=self.toggle_edit, bg="#FF9800", fg="white"
        )
        self.edit_btn.pack(side=tk.LEFT, padx=2)

        self.view_btn = tk.Button(
            btn_frame, text="👁 Просмотр",
            command=self.toggle_view, bg="#2196F3", fg="white"
        )
        self.view_btn.pack(side=tk.LEFT, padx=2)

        tk.Button(
            btn_frame, text="📷 Рисовать", command=self.open_drawing,
            bg="#6bc46d", fg="black"
        ).pack(side=tk.LEFT, padx=2)

        tk.Button(
            btn_frame, text="📎 Вставить картинку",
            command=self.insert_image_file, bg="#007ACC", fg="white"
        ).pack(side=tk.LEFT, padx=2)

        tk.Button(
            btn_frame, text="👁 Предпросмотр MD",
            command=self.preview_note, bg="#9C27B0", fg="white"
        ).pack(side=tk.RIGHT, padx=2)

        tk.Button(
            btn_frame, text="💾 Сохранить", command=self.save_note,
            bg="#4CAF50", fg="white"
        ).pack(side=tk.RIGHT, padx=2)

    def _create_content_area(self, parent):
        self.text = ScrolledText(
            parent, font=("Consolas", 11), wrap=tk.WORD, width=70, height=25
        )
        self.text.pack(fill=tk.BOTH, expand=True, pady=5)

        self.display = ContentDisplay(parent)
        self.display.pack(fill=tk.BOTH, expand=True, pady=5)
        self.display.pack_forget()

    def toggle_edit(self):
        self.display.pack_forget()
        self.text.pack(fill=tk.BOTH, expand=True, pady=5)
        self.edit_btn.config(state=tk.DISABLED)
        self.view_btn.config(state=tk.NORMAL)

    def toggle_view(self):
        self.original_content = self.text.get("1.0", tk.END).strip()
        self.text.pack_forget()
        self.display.pack(fill=tk.BOTH, expand=True, pady=5)
        self.display.set_content(self.original_content)
        self.view_btn.config(state=tk.DISABLED)
        self.edit_btn.config(state=tk.NORMAL)

    def open_drawing(self):
        DrawingPopup(self.root, self.insert_image_at_cursor)

    def insert_image_file(self):
        filetypes = [
            ("Изображения", "*.png *.jpg *.jpeg *.gif *.bmp *.webp"),
            ("Все файлы", "*.*")
        ]
        filepath = filedialog.askopenfilename(
            title="Выберите изображение", filetypes=filetypes
        )

        if filepath:
            try:
                filename = os.path.basename(filepath)
                dest_path = os.path.join(IMAGES_DIR, filename)
                shutil.copy2(filepath, dest_path)
                self.insert_image_at_cursor(dest_path)
            except Exception as e:
                messagebox.showerror(
                    "Ошибка", f"Не удалось вставить картинку: {e}"
                )

    def insert_image_at_cursor(self, image_filename):
        self.text.insert(tk.INSERT, f"\n![image]({image_filename})\n")

    def preview_note(self):
        content = self.text.get("1.0", tk.END).strip()
        content = self.convert_image_tags_to_markdown(content)
        html = markdown.markdown(
            content, extensions=['extra', 'codehilite', 'nl2br']
        )

        preview_win = tk.Toplevel(self.root)
        preview_win.title("Предпросмотр Markdown")
        preview_win.geometry("700x600")

        text_widget = ScrolledText(
            preview_win, font=("Consolas", 10),
            wrap=tk.WORD, width=80, height=35
        )
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text_widget.insert(tk.END, html)
        text_widget.config(state=tk.DISABLED)

    def convert_image_tags_to_markdown(self, content):
        def replace_tag(match):
            img_path = match.group(1)
            return f"![image]({img_path})"

        content = re.sub(r'\[image:([^\]]+)\]', replace_tag, content)
        return content

    def new_note(self):
        self.current_note_id = None
        self.title_entry.delete(0, tk.END)
        self.text.delete("1.0", tk.END)
        self.original_content = ""
        self.display.clear()
        self.toggle_edit()

    def save_note(self):
        title = self.title_entry.get().strip()

        if not title:
            messagebox.showwarning(
                "Нет заголовка", "Введите заголовок заметки"
            )
            return

        if self.display.winfo_ismapped():
            content = self.original_content
        else:
            content = self.text.get("1.0", tk.END).strip()

        note = {
            "title": title,
            "content": content,
            "created": datetime.now().strftime("%d.%m.%Y %H:%M")
        }

        if self.current_note_id is not None:
            self.notes[self.current_note_id] = note
        else:
            self.notes.append(note)
            self.current_note_id = len(self.notes) - 1

        self.save_notes()
        self.original_content = content

        messagebox.showinfo("Сохранено", "Заметка сохранена!")
        self.load_notes_list()

    def delete_note(self):
        if self.current_note_id is not None:
            if 0 <= self.current_note_id < len(self.notes):
                del self.notes[self.current_note_id]
                self.save_notes()
                self.current_note_id = None
                self.new_note()
                self.load_notes_list()
                messagebox.showinfo("Удалено", "Заметка удалена.")

    def select_note(self, event):
        sel = self.listbox.curselection()
        if not sel:
            return

        idx = sel[0]
        if idx >= len(self.notes):
            return

        note = self.notes[idx]
        self.current_note_id = idx
        self.title_entry.delete(0, tk.END)
        self.title_entry.insert(0, note.get("title", ""))
        self.text.delete("1.0", tk.END)
        self.text.insert("1.0", note.get("content", ""))
        self.original_content = note.get("content", "")

        self.toggle_view()

    def load_notes_list(self):
        self.listbox.delete(0, tk.END)
        for note in self.notes:
            self.listbox.insert(tk.END, note.get("title", "Без имени"))


def main():
    ensure_images_dir()

    root = tk.Tk()
    app = NotesApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
