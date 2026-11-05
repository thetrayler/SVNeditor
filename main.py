import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import shutil
from datetime import datetime


class FileEditorApp:
    # Папка для сохранений — рядом с самим скриптом
    SAVES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Saves")

    def __init__(self, root):
        self.root = root
        self.root.title("Редактор файлов")
        self.root.geometry("900x600")
        self.root.minsize(750, 500)

        self.current_file_path = None
        self.encoding = "UTF-8"

        # Создаём папку Saves, если её нет
        os.makedirs(self.SAVES_DIR, exist_ok=True)

        self._create_widgets()
        self.refresh_saves_list()

        # Обновляем список при закрытии
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------- Построение интерфейса ----------

    def _create_widgets(self):
        # --- Основной разделитель: слева панель, справа редактор ---
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True)

        # ===== Левая панель: список сохранённых файлов =====
        left_frame = ttk.LabelFrame(main_paned, text="Сохранённые файлы (Saves)", padding=5)

        # Кнопка обновления списка
        refresh_btn = ttk.Button(
            left_frame, text="🔄 Обновить", command=self.refresh_saves_list
        )
        refresh_btn.pack(fill=tk.X, pady=(0, 5))

        # Список файлов с прокруткой
        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        scroll = ttk.Scrollbar(list_frame)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.saves_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scroll.set,
            activestyle="none",
            exportselection=False,
        )
        self.saves_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.config(command=self.saves_listbox.yview)

        # Двойной клик открывает файл
        self.saves_listbox.bind("<Double-Button-1>", self._on_saves_double_click)
        self.saves_listbox.bind("<Return>", self._on_saves_double_click)

        # Кнопки управления сохранёнными файлами
        btn_frame = ttk.Frame(left_frame)
        btn_frame.pack(fill=tk.X, pady=(5, 0))

        ttk.Button(btn_frame, text="Открыть", command=self._on_saves_double_click)\
            .pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))
        ttk.Button(btn_frame, text="Удалить", command=self.delete_selected_save)\
            .pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 0))

        main_paned.add(left_frame, weight=1)

        # ===== Правая часть: редактор =====
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=4)

        # --- Верхняя панель: выбор исходного файла ---
        top_frame = ttk.Frame(right_frame, padding=10)
        top_frame.pack(fill=tk.X)

        ttk.Button(
            top_frame, text="Выбрать файл...", command=self.choose_file
        ).pack(side=tk.LEFT)

        self.file_label = ttk.Label(
            top_frame,
            text="Файл не выбран",
            relief=tk.SUNKEN,
            anchor=tk.W,
            padding=5,
        )
        self.file_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))

        # --- Информация о файле ---
        info_frame = ttk.LabelFrame(right_frame, text="Информация о файле", padding=10)
        info_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.info_label = ttk.Label(
            info_frame,
            text="Путь: —\nРазмер: —\nКодировка: —",
            justify=tk.LEFT,
        )
        self.info_label.pack(anchor=tk.W)

        # --- Область редактирования ---
        edit_frame = ttk.LabelFrame(right_frame, text="Содержимое файла", padding=10)
        edit_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        text_scroll = ttk.Scrollbar(edit_frame)
        text_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.text_area = tk.Text(
            edit_frame,
            wrap=tk.WORD,
            yscrollcommand=text_scroll.set,
            font=("Consolas", 10),
            undo=True,
        )
        self.text_area.pack(fill=tk.BOTH, expand=True)
        text_scroll.config(command=self.text_area.yview)

        # --- Нижняя панель: кнопки действий ---
        bottom_frame = ttk.Frame(right_frame, padding=10)
        bottom_frame.pack(fill=tk.X)

        ttk.Button(
            bottom_frame, text="Сохранить в Saves", command=self.save_to_saves
        ).pack(side=tk.RIGHT, padx=(5, 0))

        ttk.Button(
            bottom_frame, text="Перезагрузить", command=self.reload_file
        ).pack(side=tk.RIGHT)

        # --- Статусбар ---
        self.status_var = tk.StringVar(value="Готово")
        status_bar = ttk.Label(
            self.root,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W,
            padding=3,
        )
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

        # Горячие клавиши
        self.root.bind("<Control-s>", lambda e: self.save_to_saves())
        self.root.bind("<Control-o>", lambda e: self.choose_file())

    # ---------- Работа с панелью сохранённых файлов ----------

    def refresh_saves_list(self):
        """Перестраивает список файлов в папке Saves (сортировка по mtime)."""
        self.saves_listbox.delete(0, tk.END)
        self._saves_files = []

        try:
            entries = [
                f for f in os.listdir(self.SAVES_DIR)
                if os.path.isfile(os.path.join(self.SAVES_DIR, f))
            ]
        except FileNotFoundError:
            os.makedirs(self.SAVES_DIR, exist_ok=True)
            entries = []

        # Сортировка по последнему изменению — новейшие сверху
        entries.sort(
            key=lambda f: os.path.getmtime(os.path.join(self.SAVES_DIR, f)),
            reverse=True,
        )

        for name in entries:
            full = os.path.join(self.SAVES_DIR, name)
            mtime = datetime.fromtimestamp(os.path.getmtime(full))
            size = os.path.getsize(full)
            # Показываем: имя, дата, размер
            line = f"{name}   —   {mtime:%d.%m %H:%M}   ({self._format_size(size)})"
            self.saves_listbox.insert(tk.END, line)
            self._saves_files.append(name)

        self.status_var.set(f"Файлов в Saves: {len(self._saves_files)}")

    def _on_saves_double_click(self, event=None):
        sel = self.saves_listbox.curselection()
        if not sel:
            return
        filename = self._saves_files[sel[0]]
        full_path = os.path.join(self.SAVES_DIR, filename)
        self.load_file(full_path)

    def delete_selected_save(self):
        sel = self.saves_listbox.curselection()
        if not sel:
            messagebox.showinfo("Внимание", "Выберите файл в списке.")
            return
        filename = self._saves_files[sel[0]]
        full_path = os.path.join(self.SAVES_DIR, filename)

        if not messagebox.askyesno("Удаление", f"Удалить файл?\n{filename}"):
            return

        try:
            os.remove(full_path)
            self.status_var.set(f"Удалён: {filename}")
            self.refresh_saves_list()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось удалить:\n{e}")

    # ---------- Загрузка/сохранение ----------

    def choose_file(self):
        """Выбор исходного файла для редактирования."""
        path = filedialog.askopenfilename(
            title="Выберите файл",
            filetypes=[
                ("Текстовые файлы", "*.txt *.md *.py *.json *.csv *.log"),
                ("Все файлы", "*.*"),
            ],
        )
        if path:
            self.load_file(path)

    def load_file(self, path):
        try:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                encoding = "UTF-8"
            except UnicodeDecodeError:
                with open(path, "r", encoding="cp1251") as f:
                    content = f.read()
                encoding = "CP1251"
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось прочитать файл:\n{e}")
            return

        self.current_file_path = path
        self.encoding = encoding

        self.text_area.delete("1.0", tk.END)
        self.text_area.insert("1.0", content)
        self.file_label.config(text=os.path.basename(path))

        size = os.path.getsize(path)
        self.info_label.config(
            text=f"Путь: {path}\n"
                 f"Размер: {self._format_size(size)}\n"
                 f"Кодировка: {encoding}"
        )
        self.status_var.set(f"Загружен: {path}")

    def save_to_saves(self):
        """Сохраняет текущее содержимое в папку Saves.

        Имя берётся из исходного файла, либо запрашивается у пользователя.
        При совпадении имени добавляется временная метка, чтобы не затирать
        предыдущие версии.
        """
        if not self.current_file_path:
            messagebox.showinfo("Внимание", "Сначала выберите файл.")
            return

        base_name = os.path.basename(self.current_file_path)
        target = os.path.join(self.SAVES_DIR, base_name)

        # Если такой файл уже есть — предложим перезаписать или сохранить как копию
        if os.path.exists(target):
            answer = messagebox.askyesnocancel(
                "Файл существует",
                f"Файл «{base_name}» уже есть в Saves.\n\n"
                f"Да — перезаписать\n"
                f"Нет — сохранить с меткой времени\n"
                f"Отмена — ничего не делать",
            )
            if answer is None:
                return
            if answer is False:
                stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                name, ext = os.path.splitext(base_name)
                target = os.path.join(self.SAVES_DIR, f"{name}_{stamp}{ext}")

        try:
            content = self.text_area.get("1.0", "end-1c")
            with open(target, "w", encoding=self.encoding) as f:
                f.write(content)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить файл:\n{e}")
            return

        self.refresh_saves_list()
        self.status_var.set(f"Сохранено в Saves: {os.path.basename(target)}")
        messagebox.showinfo("Успех", f"Файл сохранён:\n{target}")

    def reload_file(self):
        """Перечитывает текущий файл с диска."""
        if not self.current_file_path:
            messagebox.showinfo("Внимание", "Файл не выбран.")
            return
        if messagebox.askyesno(
            "Подтверждение",
            "Отменить несохранённые изменения и перезагрузить файл?",
        ):
            self.load_file(self.current_file_path)

    # ---------- Вспомогательное ----------

    @staticmethod
    def _format_size(size: int) -> str:
        for unit in ("Б", "КБ", "МБ", "ГБ"):
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} ТБ"

    def _on_close(self):
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = FileEditorApp(root)
    root.mainloop()