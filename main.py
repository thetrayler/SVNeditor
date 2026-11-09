import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import json
from datetime import datetime
from abc import ABC, abstractmethod


# ============================================================
#                    БАЗОВЫЙ КЛАСС ИНСТРУМЕНТА
# ============================================================

class BaseTool(ABC):
    """Базовый класс инструмента.

    Наследник должен определить:
      - icon: str       — эмодзи/символ для кнопки
      - title: str      — отображаемое название
      - build_ui(parent) — нарисовать свои элементы
      - apply()          — применить к self.app.json_data

    Возврат apply(): None при успехе / строка-ошибка при провале.
    """

    icon = "🛠"
    title = "Инструмент"

    def __init__(self, app):
        self.app = app

    @abstractmethod
    def build_ui(self, parent):
        ...

    @abstractmethod
    def apply(self) -> str | None:
        ...


# ============================================================
#                    ИНСТРУМЕНТ: СВАРКА
# ============================================================

class WeldTool(BaseTool):
    icon = "🔗"
    title = "Сварка"

    def build_ui(self, parent):
        self.from_var = tk.StringVar()
        self.to_var = tk.StringVar()
        self.bidirectional_var = tk.BooleanVar(value=False)
        self.loop_var = tk.BooleanVar(value=False)

        parent.columnconfigure(1, weight=1)

        # --- Строка 0: От ---
        ttk.Label(parent, text="От Id пропа:").grid(
            row=0, column=0, sticky="w", padx=(0, 5), pady=2)
        ttk.Entry(parent, textvariable=self.from_var, width=10).grid(
            row=0, column=1, sticky="w", pady=2)

        # --- Строка 1: До ---
        ttk.Label(parent, text="До Id пропа:").grid(
            row=1, column=0, sticky="w", padx=(0, 5), pady=2)
        ttk.Entry(parent, textvariable=self.to_var, width=10).grid(
            row=1, column=1, sticky="w", pady=2)

        # --- Строка 2: чекбоксы ---
        ttk.Checkbutton(parent, text="Двусторонняя",
                        variable=self.bidirectional_var).grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(5, 2))
        ttk.Checkbutton(parent, text="Замкнуть в кольцо",
                        variable=self.loop_var).grid(
            row=2, column=1, sticky="e", pady=(5, 2))

    def apply(self) -> str | None:
        try:
            start = int(self.from_var.get())
            end = int(self.to_var.get())
        except ValueError:
            messagebox.showerror("Ошибка", "Id пропов должны быть целыми числами.")
            return None
        if start > end:
            start, end = end, start

        missing = []
        count = 0
        for sid in range(start, end + 1):
            prop = self.app._prop_by_saveid(sid)
            if prop is None:
                missing.append(sid)
                continue

            if sid < end:
                target = sid + 1
            elif self.loop_var.get():
                target = start
            else:
                continue

            self._add_weld(prop, target)
            if self.bidirectional_var.get():
                target_prop = self.app._prop_by_saveid(target)
                if target_prop is not None:
                    self._add_weld_keep_both(target_prop, sid)
            count += 1

        msg = f"Сварено пар: {count}"
        if missing:
            msg += f"\nПропущены id (не найдены): {missing}"
        self.app.status_var.set(msg.split("\n")[0])
        messagebox.showinfo("Готово", msg)
        return None

    # --- вспомогательные ---

    def _add_weld(self, prop, target_save_id):
        """Добавляет weld prop → target и убирает обратную связь."""
        lst = prop.get("weldTargetSaveIds")
        if not isinstance(lst, list):
            lst = []
        if target_save_id not in lst:
            lst.append(target_save_id)
        prop["weldTargetSaveIds"] = sorted(set(lst))

        target_prop = self.app._prop_by_saveid(target_save_id)
        if target_prop is not None:
            rev = target_prop.get("weldTargetSaveIds")
            if isinstance(rev, list):
                source_id = prop.get("saveId")
                if source_id in rev:
                    rev.remove(source_id)
                    target_prop["weldTargetSaveIds"] = rev

    def _add_weld_keep_both(self, prop, target_save_id):
        lst = prop.get("weldTargetSaveIds")
        if not isinstance(lst, list):
            lst = []
        if target_save_id not in lst:
            lst.append(target_save_id)
        prop["weldTargetSaveIds"] = sorted(set(lst))


# ============================================================
#                    ИНСТРУМЕНТ: ОЧИСТКА СВАРКИ
# ============================================================

class ClearWeldTool(BaseTool):
    icon = "🧹"
    title = "Очистка сварки"

    def build_ui(self, parent):
        self.from_var = tk.StringVar()
        self.to_var = tk.StringVar()
        self.bidirectional_var = tk.BooleanVar(value=False)
        self.loop_var = tk.BooleanVar(value=False)

        parent.columnconfigure(1, weight=1)

        # --- Строка 0: От ---
        ttk.Label(parent, text="От Id пропа:").grid(
            row=0, column=0, sticky="w", padx=(0, 5), pady=2)
        ttk.Entry(parent, textvariable=self.from_var, width=10).grid(
            row=0, column=1, sticky="w", pady=2)

        # --- Строка 1: До ---
        ttk.Label(parent, text="До Id пропа:").grid(
            row=1, column=0, sticky="w", padx=(0, 5), pady=2)
        ttk.Entry(parent, textvariable=self.to_var, width=10).grid(
            row=1, column=1, sticky="w", pady=2)

    def apply(self) -> str | None:
        try:
            start = int(self.from_var.get())
            end = int(self.to_var.get())
        except ValueError:
            messagebox.showerror("Ошибка", "Id пропов должны быть целыми числами.")
            return None
        if start > end:
            start, end = end, start

        count = 0
        for sid in range(start, end + 1):
            prop = self.app._prop_by_saveid(sid)
            if prop is not None:
                prop["weldTargetSaveIds"] = []
                count += 1
        messagebox.showinfo("Готово", f"Очищено пропов: {count}")
        self.app.status_var.set(f"Очищено: {count}")
        return None


# ============================================================
#                    ИНСТРУМЕНТ: ВИДИМОСТЬ ПРОПОВ
# ============================================================

class VisibilityTool(BaseTool):
    icon = "👁"
    title = "Видимость пропов"

    def build_ui(self, parent):
        self.from_var = tk.StringVar()
        self.to_var = tk.StringVar()
        self.visible_var = tk.BooleanVar(value=True)  # по умолчанию «сделать видимыми»

        parent.columnconfigure(1, weight=1)

        # --- Строка 0: От ---
        ttk.Label(parent, text="От Id пропа:").grid(
            row=0, column=0, sticky="w", padx=(0, 5), pady=2)
        ttk.Entry(parent, textvariable=self.from_var, width=10).grid(
            row=0, column=1, sticky="w", pady=2)

        # --- Строка 1: До ---
        ttk.Label(parent, text="До Id пропа:").grid(
            row=1, column=0, sticky="w", padx=(0, 5), pady=2)
        ttk.Entry(parent, textvariable=self.to_var, width=10).grid(
            row=1, column=1, sticky="w", pady=2)

        # --- Строка 2: галочка видимости ---
        ttk.Checkbutton(
            parent,
            text="Сделать видимым (снять — сделать невидимым)",
            variable=self.visible_var,
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(8, 2))

    def apply(self) -> str | None:
        # 1. Парсим диапазон
        try:
            start = int(self.from_var.get())
            end = int(self.to_var.get())
        except ValueError:
            messagebox.showerror("Ошибка", "Id пропов должны быть целыми числами.")
            return None
        if start > end:
            start, end = end, start

        # 2. Определяем целевое значение invisible
        #    галочка включена  → invisible = False (проп виден)
        #    галочка выключена → invisible = True  (проп скрыт)
        target_invisible = not self.visible_var.get()

        # 3. Применяем
        changed = 0
        missing = []
        for sid in range(start, end + 1):
            prop = self.app._prop_by_saveid(sid)
            if prop is None:
                missing.append(sid)
                continue
            # ставим булево, а не строку — так игра точно прочитает
            if prop.get("invisible") != target_invisible:
                prop["invisible"] = target_invisible
                changed += 1

        # 4. Сообщение
        state = "видимыми" if self.visible_var.get() else "невидимыми"
        msg = f"Сделано {state}: {changed} пропов"
        if missing:
            msg += f"\nПропущены id (не найдены): {missing}"
        self.app.status_var.set(msg.split("\n")[0])
        messagebox.showinfo("Готово", msg)
        return None


# ============================================================
#                     ГЛАВНОЕ ПРИЛОЖЕНИЕ
# ============================================================

class FileEditorApp:
    SAVES_DIR = os.path.join(
        os.environ.get("USERPROFILE", os.path.expanduser("~")),
        "AppData", "LocalLow", "DefaultCompany", "Hypper Sandbox", "Saves"
    )

    # Регистрация инструментов: добавляй сюда новые классы
    TOOL_CLASSES = [WeldTool, ClearWeldTool, VisibilityTool]

    def __init__(self, root):
        self.root = root
        self.root.title("Редактор SVN файлов — Hypper Sandbox")
        self.root.geometry("1200x700")
        self.root.minsize(950, 600)

        self.current_file_path = None
        self.encoding = "UTF-8"
        self.json_data = None

        os.makedirs(self.SAVES_DIR, exist_ok=True)

        self.tools = [cls(self) for cls in self.TOOL_CLASSES]
        self.active_tool = None
        self.tool_buttons = {}

        self._create_widgets()
        self.refresh_saves_list()

        # Активируем первый инструмент
        if self.tools:
            self._select_tool(self.tools[0])

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------- UI ----------

    def _create_widgets(self):
        # Верхняя строка: открыть + имя файла + сохранить
        top_frame = ttk.Frame(self.root, padding=10)
        top_frame.pack(fill=tk.X)

        ttk.Button(top_frame, text="Выбрать файл...", command=self.choose_file)\
            .pack(side=tk.LEFT)

        self.file_label = ttk.Label(top_frame, text="Файл не выбран",
                                    relief=tk.SUNKEN, anchor=tk.W, padding=5)
        self.file_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 10))

        ttk.Button(top_frame, text="💾 Сохранить (в Saves)", command=self.save_to_saves)\
            .pack(side=tk.RIGHT)

        # Основной разделитель: 3 панели
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 5))

        # ===== 1. Левая панель: Saves =====
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

        # ===== 2. Центр: редактор =====
        center_frame = ttk.Frame(main_paned)
        main_paned.add(center_frame, weight=5)

        info_frame = ttk.LabelFrame(center_frame, text="Информация о файле", padding=10)
        info_frame.pack(fill=tk.X, pady=(0, 10))
        self.info_label = ttk.Label(info_frame,
                                    text="Путь: —\nРазмер: —\nКодировка: —\nПропов: —",
                                    justify=tk.LEFT)
        self.info_label.pack(anchor=tk.W)

        edit_frame = ttk.LabelFrame(center_frame, text="Содержимое файла", padding=10)
        edit_frame.pack(fill=tk.BOTH, expand=True)
        text_scroll = ttk.Scrollbar(edit_frame)
        text_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_area = tk.Text(edit_frame, wrap=tk.NONE, yscrollcommand=text_scroll.set,
                                 font=("Consolas", 10), undo=True)
        self.text_area.pack(fill=tk.BOTH, expand=True)
        text_scroll.config(command=self.text_area.yview)

        # ===== 3. Правая панель: инструменты =====
        tools_outer = ttk.LabelFrame(main_paned, text="Инструменты", padding=5)

        # Список кнопок-инструментов (иконка + название)
        self.tool_selector = ttk.Frame(tools_outer)
        self.tool_selector.pack(fill=tk.X, pady=(0, 8))

        for tool in self.tools:
            btn = ttk.Button(
                self.tool_selector,
                text=f"{tool.icon}  {tool.title}",
                command=lambda t=tool: self._select_tool(t),
            )
            btn.pack(fill=tk.X, pady=2)
            self.tool_buttons[tool] = btn

        ttk.Separator(tools_outer, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)

        # Заголовок активного инструмента
        self.active_tool_title = ttk.Label(
            tools_outer, text="", font=("Segoe UI", 10, "bold")
        )
        self.active_tool_title.pack(anchor=tk.W, pady=(0, 5))

        # Контейнер для UI активного инструмента
        self.tool_ui_container = ttk.Frame(tools_outer)
        self.tool_ui_container.pack(fill=tk.X)

        ttk.Button(tools_outer, text="▶ Применить", command=self._apply_active_tool)\
            .pack(fill=tk.X, side=tk.BOTTOM, pady=(10, 0))

        main_paned.add(tools_outer, weight=2)

        # Статусбар
        self.status_var = tk.StringVar(value="Готово")
        ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN,
                  anchor=tk.W, padding=3).pack(fill=tk.X, side=tk.BOTTOM)

        self.root.bind("<Control-s>", lambda e: self.save_to_saves())
        self.root.bind("<Control-o>", lambda e: self.choose_file())

    # ---------- Переключение инструментов ----------

    def _select_tool(self, tool: BaseTool):
        # Перепарсим JSON, чтобы инструмент работал с актуальным состоянием
        # if not self._sync_json_from_text():
        #     return

        self.active_tool = tool

        # Подсветим активную кнопку
        for t, btn in self.tool_buttons.items():
            btn.state(["pressed"] if t is tool else ["!pressed"])

        self.active_tool_title.config(text=f"{tool.icon}  {tool.title}")

        # Очищаем контейнер и строим UI нового инструмента
        for w in self.tool_ui_container.winfo_children():
            w.destroy()
        tool.build_ui(self.tool_ui_container)

    def _apply_active_tool(self):
        if self.active_tool is None:
            messagebox.showinfo("Инструмент", "Выберите инструмент справа.")
            return
        if not self._sync_json_from_text():
            return

        err = self.active_tool.apply()
        if err:
            messagebox.showerror("Ошибка", err)
            return

        # Синхронизируем редактор с изменённым json_data
        self._sync_text_from_json()

    # ---------- Работа с JSON ----------

    def _sync_json_from_text(self):
        try:
            self.json_data = json.loads(self.text_area.get("1.0", "end-1c"))
            return True
        except json.JSONDecodeError as e:
            messagebox.showerror("Ошибка JSON", f"Не удалось распарсить:\n{e}")
            return False

    def _sync_text_from_json(self):
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
            filetypes=[
                ("Hypper Sandbox save", "*.svn"),
                ("JSON", "*.json"),
                ("Текстовые", "*.txt"),
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
        if not self._sync_json_from_text():
            return

        if self.current_file_path:
            base_name = os.path.basename(self.current_file_path)
        else:
            from tkinter import simpledialog
            name = simpledialog.askstring("Имя файла", "Введите имя файла:",
                                          initialvalue="save.json")
            if not name:
                return
            base_name = name

        # Приводим к .svn
        base, ext = os.path.splitext(base_name)
        if ext.lower() != ".svn":
            base_name = base + ".svn"

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
                b, e = os.path.splitext(base_name)
                target = os.path.join(self.SAVES_DIR, f"{b}_{stamp}{e}")

        try:
            content = json.dumps(self.json_data, ensure_ascii=False, indent=2)
            with open(target, "w", encoding=self.encoding) as f:
                f.write(content)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить:\n{e}")
            return

        self.current_file_path = target
        self.file_label.config(text=os.path.basename(target))

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
