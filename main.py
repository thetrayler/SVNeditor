import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import json
from datetime import datetime


class FileEditorApp:
    # Универсальный путь через переменные окружения
    SAVES_DIR = os.path.join(
        os.environ.get("USERPROFILE", os.path.expanduser("~")),
        "AppData", "LocalLow", "DefaultCompany", "Hypper Sandbox", "Saves"
    )

    def __init__(self, root):
        self.root = root
        self.root.title("Редактор SVN файлов — Hypper Sandbox")
        self.root.geometry("1000x650")
        self.root.minsize(800, 550)

        self.current_file_path = None
        self.encoding = "UTF-8"
        self.json_data = None          # распарсенный JSON текущего файла

        os.makedirs(self.SAVES_DIR, exist_ok=True)

        self._create_widgets()
        self.refresh_saves_list()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------- UI ----------

    def _create_widgets(self):
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True)

        # ===== Левая панель =====
        left_frame = ttk.LabelFrame(main_paned, text="Сохранённые файлы (Saves)", padding=5)
        ttk.Button(left_frame, text="🔄 Обновить", command=self.refresh_saves_list)\
            .pack(fill=tk.X, pady=(0, 5))

        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        scroll = ttk.Scrollbar(list_frame)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.saves_listbox = tk.Listbox(list_frame, yscrollcommand=scroll.set,
                                        activestyle="none", exportselection=False)
        self.saves_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.config(command=self.saves_listbox.yview)
        self.saves_listbox.bind("<Double-Button-1>", self._on_saves_double_click)
        self.saves_listbox.bind("<Return>", self._on_saves_double_click)

        btn_frame = ttk.Frame(left_frame)
        btn_frame.pack(fill=tk.X, pady=(5, 0))
        ttk.Button(btn_frame, text="Открыть", command=self._on_saves_double_click)\
            .pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))
        ttk.Button(btn_frame, text="Удалить", command=self.delete_selected_save)\
            .pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 0))

        main_paned.add(left_frame, weight=1)

        # ===== Правая часть =====
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=4)

        # Верхняя панель
        top_frame = ttk.Frame(right_frame, padding=10)
        top_frame.pack(fill=tk.X)
        ttk.Button(top_frame, text="Выбрать файл...", command=self.choose_file)\
            .pack(side=tk.LEFT)
        self.file_label = ttk.Label(top_frame, text="Файл не выбран",
                                    relief=tk.SUNKEN, anchor=tk.W, padding=5)
        self.file_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))

        # Информация
        info_frame = ttk.LabelFrame(right_frame, text="Информация о файле", padding=10)
        info_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        self.info_label = ttk.Label(info_frame,
                                    text="Путь: —\nРазмер: —\nКодировка: —\nПропов: —",
                                    justify=tk.LEFT)
        self.info_label.pack(anchor=tk.W)

        # Панель сварки
        weld_frame = ttk.LabelFrame(right_frame, text="Сварка пропов (weld)", padding=10)
        weld_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        row = ttk.Frame(weld_frame)
        row.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(row, text="От SaveId:").pack(side=tk.LEFT)
        self.weld_from_var = tk.StringVar()
        ttk.Entry(row, textvariable=self.weld_from_var, width=8)\
            .pack(side=tk.LEFT, padx=(5, 15))

        ttk.Label(row, text="До SaveId:").pack(side=tk.LEFT)
        self.weld_to_var = tk.StringVar()
        ttk.Entry(row, textvariable=self.weld_to_var, width=8)\
            .pack(side=tk.LEFT, padx=(5, 15))

        self.bidirectional_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row, text="Двусторонняя", variable=self.bidirectional_var)\
            .pack(side=tk.LEFT, padx=(0, 15))

        self.loop_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row, text="Замкнуть в кольцо", variable=self.loop_var)\
            .pack(side=tk.LEFT)

        row2 = ttk.Frame(weld_frame)
        row2.pack(fill=tk.X)
        ttk.Button(row2, text="Сварить по цепочке", command=self.weld_chain)\
            .pack(side=tk.LEFT)
        ttk.Button(row2, text="Очистить weld в диапазоне", command=self.clear_weld_range)\
            .pack(side=tk.LEFT, padx=(5, 0))
        ttk.Button(row2, text="💾 Сохранить изменения (в Saves)", command=self.save_to_saves)\
            .pack(side=tk.RIGHT)

        # Область редактирования
        edit_frame = ttk.LabelFrame(right_frame, text="Содержимое файла", padding=10)
        edit_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        text_scroll = ttk.Scrollbar(edit_frame)
        text_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_area = tk.Text(edit_frame, wrap=tk.NONE, yscrollcommand=text_scroll.set,
                                 font=("Consolas", 10), undo=True)
        self.text_area.pack(fill=tk.BOTH, expand=True)
        text_scroll.config(command=self.text_area.yview)

        # Статусбар
        self.status_var = tk.StringVar(value="Готово")
        ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN,
                  anchor=tk.W, padding=3).pack(fill=tk.X, side=tk.BOTTOM)

        self.root.bind("<Control-s>", lambda e: self.save_to_saves())
        self.root.bind("<Control-o>", lambda e: self.choose_file())

    # ---------- Работа с JSON ----------

    def _sync_json_from_text(self):
        """Парсит текст из редактора в self.json_data."""
        try:
            self.json_data = json.loads(self.text_area.get("1.0", "end-1c"))
            return True
        except json.JSONDecodeError as e:
            messagebox.showerror("Ошибка JSON", f"Не удалось распарсить:\n{e}")
            return False

    def _sync_text_from_json(self):
        """Выводит self.json_data в редактор (с отступами)."""
        self.text_area.delete("1.0", tk.END)
        self.text_area.insert("1.0", json.dumps(self.json_data, ensure_ascii=False, indent=2))

    def _get_props(self):
        if not self.json_data or "props" not in self.json_data:
            return []
        return self.json_data["props"]

    def _prop_by_saveid(self, save_id):
        for p in self._get_props():
            if p.get("saveId") == save_id:
                return p
        return None

    # ---------- Сварка ----------

    def weld_chain(self):
        """Последовательно сварочный диапазон [from, to]."""
        if not self._sync_json_from_text():
            return

        try:
            start = int(self.weld_from_var.get())
            end = int(self.weld_to_var.get())
        except ValueError:
            messagebox.showerror("Ошибка", "SaveId должны быть целыми числами.")
            return

        if start > end:
            start, end = end, start

        missing = []
        weldd_count = 0
        for sid in range(start, end + 1):
            prop = self._prop_by_saveid(sid)
            if prop is None:
                missing.append(sid)
                continue
            # цель — следующий saveId, а для последнего — либо кольцо, либо ничего
            if sid < end:
                target = sid + 1
            elif self.loop_var.get():
                target = start
            else:
                continue

            # для двусторонней сварки добавляем и себя в цель
            self._add_weld(prop, target)
            if self.bidirectional_var.get():
                target_prop = self._prop_by_saveid(target)
                if target_prop is not None:
                    self._add_weld(target_prop, sid)
            weldd_count += 1

        self._sync_text_from_json()
        msg = f"Сварено пар: {weldd_count}"
        if missing:
            msg += f"\nПропущены SaveId (не найдены): {missing}"
        self.status_var.set(msg.split("\n")[0])
        messagebox.showinfo("Готово", msg)

    def _add_weld(self, prop, target_save_id):
        lst = prop.get("weldTargetSaveIds")
        if not isinstance(lst, list):
            lst = []
        if target_save_id not in lst:
            lst.append(target_save_id)
        # сортируем и убираем дубли — так удобнее читать
        prop["weldTargetSaveIds"] = sorted(set(lst))

    def clear_weld_range(self):
        """Очищает weldTargetSaveIds у пропов в диапазоне."""
        if not self._sync_json_from_text():
            return
        try:
            start = int(self.weld_from_var.get())
            end = int(self.weld_to_var.get())
        except ValueError:
            messagebox.showerror("Ошибка", "SaveId должны быть целыми числами.")
            return
        if start > end:
            start, end = end, start

        count = 0
        for sid in range(start, end + 1):
            prop = self._prop_by_saveid(sid)
            if prop is not None:
                prop["weldTargetSaveIds"] = []
                count += 1
        self._sync_text_from_json()
        messagebox.showinfo("Готово", f"Очищено пропов: {count}")
        self.status_var.set(f"Очищено: {count}")

    # ---------- Панель Saves ----------

    def refresh_saves_list(self):
        self.saves_listbox.delete(0, tk.END)
        self._saves_files = []
        try:
            entries = [f for f in os.listdir(self.SAVES_DIR)
                       if os.path.isfile(os.path.join(self.SAVES_DIR, f))]
        except FileNotFoundError:
            os.makedirs(self.SAVES_DIR, exist_ok=True)
            entries = []

        entries.sort(
            key=lambda f: os.path.getmtime(os.path.join(self.SAVES_DIR, f)),
            reverse=True,
        )
        for name in entries:
            full = os.path.join(self.SAVES_DIR, name)
            mtime = datetime.fromtimestamp(os.path.getmtime(full))
            size = os.path.getsize(full)
            line = f"{name}   —   {mtime:%d.%m %H:%M}   ({self._format_size(size)})"
            self.saves_listbox.insert(tk.END, line)
            self._saves_files.append(name)

        self.status_var.set(f"Файлов в Saves: {len(self._saves_files)}")

    def _on_saves_double_click(self, event=None):
        sel = self.saves_listbox.curselection()
        if not sel:
            return
        filename = self._saves_files[sel[0]]
        self.load_file(os.path.join(self.SAVES_DIR, filename))

    def delete_selected_save(self):
        sel = self.saves_listbox.curselection()
        if not sel:
            return
        filename = self._saves_files[sel[0]]
        full_path = os.path.join(self.SAVES_DIR, filename)
        if not messagebox.askyesno("Удаление", f"Удалить файл?\n{filename}"):
            return
        try:
            os.remove(full_path)
            self.refresh_saves_list()
            self.status_var.set(f"Удалён: {filename}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось удалить:\n{e}")

    # ---------- Загрузка/сохранение ----------

    def choose_file(self):
        path = filedialog.askopenfilename(
            title="Выберите файл",
            filetypes=[("JSON / текстовые", "*.json *.txt"), ("Все файлы", "*.*")],
        )
        if path:
            self.load_file(path)

    def load_file(self, path):
        try:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                self.encoding = "UTF-8"
            except UnicodeDecodeError:
                with open(path, "r", encoding="cp1251") as f:
                    content = f.read()
                self.encoding = "CP1251"
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось прочитать файл:\n{e}")
            return

        self.current_file_path = path
        self.text_area.delete("1.0", tk.END)
        self.text_area.insert("1.0", content)
        self.file_label.config(text=os.path.basename(path))

        # пробуем сразу распарсить
        self.json_data = None
        try:
            self.json_data = json.loads(content)
        except json.JSONDecodeError:
            pass

        props_count = len(self._get_props()) if self.json_data else 0
        size = os.path.getsize(path)
        self.info_label.config(
            text=f"Путь: {path}\n"
                 f"Размер: {self._format_size(size)}\n"
                 f"Кодировка: {self.encoding}\n"
                 f"Пропов: {props_count}"
        )
        self.status_var.set(f"Загружен: {path}")

    def save_to_saves(self):
        """Сохраняет содержимое редактора (уже валидный JSON) в Saves."""
        if not self._sync_json_from_text():
            return

        if self.current_file_path:
            base_name = os.path.basename(self.current_file_path)
        else:
            base_name = "save.json"
            from tkinter import simpledialog
            name = simpledialog.askstring("Имя файла",
                                          "Введите имя файла:",
                                          initialvalue="save.json")
            if not name:
                return
            base_name = name

        target = os.path.join(self.SAVES_DIR, base_name)

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
            content = json.dumps(self.json_data, ensure_ascii=False, indent=2)
            with open(target, "w", encoding=self.encoding) as f:
                f.write(content)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить:\n{e}")
            return

        self.refresh_saves_list()
        self.status_var.set(f"Сохранено: {os.path.basename(target)}")
        messagebox.showinfo("Успех", f"Файл сохранён:\n{target}")

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