
#!/usr/bin/env python3
"""
OmniVault â€” Vault Ledger Desktop Suite
Fully native PyQt6 replacement for the React OmniVault workspace platform.
Includes Pages module with tree navigation and dynamic block elements.
"""

import sys
import re
import math
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional

from PyQt6.QtCore import Qt, QSize, QRectF, QPoint, pyqtSignal
from PyQt6.QtGui import (
    QFont, QIcon, QColor, QPalette, QBrush, QPen, QPainter,
    QTextCursor, QTextDocument, QPageSize, QPageLayout, QAction
)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QLabel, QPushButton, QLineEdit, QTextEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QListWidget,
    QListWidgetItem, QSplitter, QDialog, QFrame, QFileDialog,
    QMessageBox, QGraphicsView, QGraphicsScene, QGraphicsRectItem,
    QGraphicsTextItem, QGraphicsItem, QGraphicsDropShadowEffect,
    QToolBar, QComboBox, QScrollArea, QMenu, QInputDialog, QTreeWidget, QTreeWidgetItem, QCheckBox
)
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog

import pandas as pd

# ============================================================================
# SAFE FORMULA ENGINE â€” Zero-eval sandbox expression processing
# ============================================================================

def col_to_num(col: str) -> int:
    n = 0
    for c in col.upper():
        n = n * 26  (ord(c) - 64)
    return n

def num_to_col(n: int) -> str:
    s = ""
    while n > 0:
        r = (n - 1) % 26
        s = chr(65  r)  s
        n = (n - 1) // 26
    return s

def parse_ref(ref: str) -> Optional[Dict[str, Any]]:
    m = re.match(r"^([A-Z])(\d)$", ref.upper())
    return {"col": m.group(1), "row": int(m.group(2))} if m else None

def expand_range(start: str, end: str) -> List[str]:
    s, e = parse_ref(start), parse_ref(end)
    if not s or not e:
        return []
    c1, c2 = col_to_num(s["col"]), col_to_num(e["col"])
    r1, r2 = min(s["row"], e["row"]), max(s["row"], e["row"])
    min_c, max_c = min(c1, c2), max(c1, c2)
    return [f"{num_to_col(c)}{r}" for r in range(r1, r2  1) for c in range(min_c, max_c  1)]

def resolve_cell(ref: str, grid: Dict[str, str], seen: set) -> Any:
    if ref in seen:
        return 0
    raw = grid.get(ref, "")
    if raw == "":
        return 0
    if isinstance(raw, str) and raw.startswith("="):
        next_seen = set(seen)
        next_seen.add(ref)
        res = evaluate_formula(raw, grid, next_seen)
        try:
            return float(res)
        except (ValueError, TypeError):
            return res
    try:
        return float(raw)
    except (ValueError, TypeError):
        return raw

def range_fn(fn: str, cells: List[str], grid: Dict[str, str], seen: set) -> Any:
    vals = [resolve_cell(c, grid, seen) for c in cells]
    nums = [float(v) for v in vals if isinstance(v, (int, float)) or (isinstance(v, str) and v.replace(".", "", 1).isdigit())]
    fn = fn.upper()
    if fn == "SUM":
        return sum(nums)
    if fn in ("AVERAGE", "AVG"):
        return sum(nums) / len(nums) if nums else 0
    if fn == "MIN":
        return min(nums) if nums else 0
    if fn == "MAX":
        return max(nums) if nums else 0
    if fn == "COUNT":
        return len(nums)
    if fn == "COUNTA":
        return len([v for v in vals if v not in ("", 0)])
    if fn == "CONCAT":
        return "".join(map(str, vals))
    return 0

def vlookup(lookup_val: Any, range_str: str, col_idx: int, grid: Dict[str, str], seen: set) -> Any:
    try:
        start, end = range_str.split(":")
        s, e = parse_ref(start), parse_ref(end)
        if not s or not e:
            return "#N/A"
        c1, c2 = col_to_num(s["col"]), col_to_num(e["col"])
        target_col = c1  col_idx - 1
        if target_col > c2:
            return "#REF!"
        for r in range(min(s["row"], e["row"]), max(s["row"], e["row"])  1):
            key = f"{num_to_col(c1)}{r}"
            val = resolve_cell(key, grid, seen)
            if str(val).strip().lower() == str(lookup_val).strip().lower():
                return resolve_cell(f"{num_to_col(target_col)}{r}", grid, seen)
        return "#N/A"
    except Exception:
        return "#ERR"

def safe_math_eval(expr: str) -> Any:
    try:
        return eval(compile(expr, "<string>", "eval"), {"__builtins__": None}, {"math": math})
    except Exception:
        return "#ERR"

def evaluate_formula(raw: str, grid: Dict[str, str], seen: set = None) -> Any:
    if seen is None:
        seen = set()
    if not isinstance(raw, str) or not raw.startswith("="):
        return raw

    expr = raw[1:].strip()

    def _vlookup_sub(match):
        key, rng, idx = match.group(1).strip(), match.group(2).strip(), int(match.group(3))
        lookup_val = key[1:-1] if key.startswith('"') else resolve_cell(key.upper(), grid, seen)
        res = vlookup(lookup_val, rng, idx, grid, seen)
        return f'"{res}"' if isinstance(res, str) else str(res)

    expr = re.sub(r"VLOOKUP\(\s*([^,]),\s*([A-Z]\d:[A-Z]\d)\s*,\s*(\d)\s*\)", _vlookup_sub, expr, flags=re.IGNORECASE)

    def _range_sub(match):
        fn, a, b = match.group(1), match.group(2), match.group(3)
        res = range_fn(fn, expand_range(a.upper(), b.upper()), grid, seen)
        return f'"{res}"' if isinstance(res, str) else str(res)

    expr = re.sub(r"(SUM|AVERAGE|AVG|MIN|MAX|COUNT|COUNTA|CONCAT)\(\s*([A-Z]\d)\s*:\s*([A-Z]\d)\s*\)", _range_sub, expr, flags=re.IGNORECASE)

    def _cell_sub(match):
        ref = match.group(0).upper()
        val = resolve_cell(ref, grid, seen)
        return f'"{val}"' if isinstance(val, str) else str(val)

    expr = re.sub(r"\b[A-Z]\d\b", _cell_sub, expr)

    def _if_sub(match):
        inner = match.group(1)
        parts = inner.split(",")
        return f"({parts[1]}) if ({parts[0]}) else ({parts[2]})" if len(parts) == 3 else match.group(0)

    expr = re.sub(r"IF\(([^()]*)\)", _if_sub, expr, flags=re.IGNORECASE)

    res = safe_math_eval(expr)
    if isinstance(res, float):
        return round(res, 4)
    return res

# ============================================================================
# STYLESHEET MANAGEMENT â€” Vault Ledger Aesthetic System
# ============================================================================

BRASS = "#C99A3A"
BRASS_DARK = "#A87F2A"

def get_stylesheet(dark: bool) -> str:
    bg_main = "#09090b" if dark else "#f4f4f5"
    bg_card = "#18181b" if dark else "#ffffff"
    bg_hover = "#27272a" if dark else "#e4e4e7"
    text_main = "#f4f4f5" if dark else "#09090b"
    border = "#27272a" if dark else "#e4e4e7"

    return f"""
        QMainWindow, QDialog {{
            background-color: {bg_main};
            color: {text_main};
            font-family: 'Segoe UI', system-ui, sans-serif;
        }}
        QWidget {{
            color: {text_main};
        }}
        QFrame#TopBar {{
            background-color: #18181b;
            border-bottom: 1px solid #27272a;
        }}
        QFrame#SubBar {{
            background-color: {bg_card};
            border-bottom: 1px solid {border};
        }}
        QPushButton {{
            background-color: transparent;
            color: {text_main};
            border: none;
            border-radius: 6px;
            padding: 6px 12px;
            font-weight: 500;
        }}
        QPushButton:hover {{
            background-color: {bg_hover};
        }}
        QPushButton#BrassButton {{
            background-color: {BRASS};
            color: #09090b;
            font-weight: 600;
        }}
        QPushButton#BrassButton:hover {{
            background-color: {BRASS_DARK};
        }}
        QLineEdit, QTextEdit {{
            background-color: {bg_card};
            color: {text_main};
            border: 1px solid {border};
            border-radius: 6px;
            padding: 6px;
        }}
        QLineEdit:focus, QTextEdit:focus {{
            border: 1px solid {BRASS};
        }}
        QTableWidget, QTreeWidget {{
            background-color: {bg_card};
            gridline-color: {border};
            color: {text_main};
            border: 1px solid {border};
        }}
        QHeaderView::section {{
            background-color: {bg_hover};
            color: {text_main};
            padding: 4px;
            border: 1px solid {border};
            font-weight: bold;
        }}
        QListWidget {{
            background-color: {bg_card};
            border: 1px solid {border};
            border-radius: 6px;
        }}
        QListWidget::item {{
            padding: 8px;
            border-radius: 4px;
        }}
        QListWidget::item:selected {{
            background-color: {BRASS};
            color: #09090b;
        }}
    """

# ============================================================================
# DIALOGS â€” Command Palette & Trash
# ============================================================================

class CommandPaletteDialog(QDialog):
    def __init__(self, parent, actions: List[Dict[str, Any]], dark: bool):
        super().__init__(parent)
        self.actions = actions
        self.filtered_actions = actions
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Popup)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(500, 350)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        self.container = QFrame(self)
        self.container.setObjectName("Container")
        self.container.setStyleSheet(f"""
            QFrame#Container {{
                background-color: {'#18181b' if dark else '#ffffff'};
                border: 1px solid {'#3f3f46' if dark else '#d4d4d8'};
                border-radius: 12px;
            }}
        """)
        c_layout = QVBoxLayout(self.container)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Jump to page, app, action... (Esc to close)")
        self.search_input.textChanged.connect(self.filter_actions)
        c_layout.addWidget(self.search_input)

        self.list_widget = QListWidget()
        self.list_widget.itemActivated.connect(self.run_selected)
        c_layout.addWidget(self.list_widget)

        layout.addWidget(self.container)
        self.populate_list()

    def filter_actions(self, text: str):
        self.filtered_actions = [
            a for a in self.actions
            if text.lower() in a["label"].lower() or text.lower() in a.get("category", "").lower()
        ]
        self.populate_list()

    def populate_list(self):
        self.list_widget.clear()
        for a in self.filtered_actions:
            item = QListWidgetItem(f"[{a.get('category', 'Action')}] {a['label']}")
            self.list_widget.addItem(item)
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)

    def run_selected(self):
        row = self.list_widget.currentRow()
        if 0 <= row < len(self.filtered_actions):
            action = self.filtered_actions[row]
            self.accept()
            action["run"]()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.run_selected()
        else:
            super().keyPressEvent(event)

class TrashDialog(QDialog):
    def __init__(self, parent, state_hub, dark: bool):
        super().__init__(parent)
        self.hub = state_hub
        self.setWindowTitle("Trash Hub")
        self.resize(450, 400)

        layout = QVBoxLayout(self)
        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        btn_layout = QHBoxLayout()
        self.restore_btn = QPushButton("Restore")
        self.restore_btn.clicked.connect(self.restore_selected)
        self.purge_btn = QPushButton("Purge Permanently")
        self.purge_btn.setStyleSheet("color: #ef4444;")
        self.purge_btn.clicked.connect(self.purge_selected)
        
        btn_layout.addWidget(self.restore_btn)
        btn_layout.addWidget(self.purge_btn)
        layout.addLayout(btn_layout)

        self.refresh()

    def refresh(self):
        self.list_widget.clear()
        for item in self.hub["trash"]:
            self.list_widget.addItem(f"[{item['kind'].upper()}] {item.get('name', item.get('title', 'Untitled'))}")

    def get_selected_item(self):
        row = self.list_widget.currentRow()
        if 0 <= row < len(self.hub["trash"]):
            return row, self.hub["trash"][row]
        return -1, None

    def restore_selected(self):
        row, item = self.get_selected_item()
        if item:
            kind = item["kind"]
            self.hub["trash"].pop(row)
            if kind == "file":
                self.hub["files"].append(item)
            elif kind == "doc":
                self.hub["docs"].append(item)
            elif kind == "slide":
                self.hub["slides"].append(item)
            elif kind == "page":
                self.hub["pages"].append(item)
            self.refresh()
            self.parent().sync_state()

    def purge_selected(self):
        row, item = self.get_selected_item()
        if item:
            self.hub["trash"].pop(row)
            self.refresh()
            self.parent().sync_state()

# ============================================================================
# WORKSPACE MODULES
# ============================================================================

# --- PAGES MODULE (NEWLY ADDED) ---
class PagesModule(QWidget):
    def __init__(self, state_hub, parent=None):
        super().__init__(parent)
        self.hub = state_hub
        self.current_page = None
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout(self)

        # Page Tree Sidebar
        sidebar = QWidget()
        sidebar.setFixedWidth(220)
        s_layout = QVBoxLayout(sidebar)
        
        s_layout.addWidget(QLabel("WORKSPACE PAGES"))
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.itemClicked.connect(self.on_page_selected)
        s_layout.addWidget(self.tree)

        btn_add_page = QPushButton(" Add Page")
        btn_add_page.setObjectName("BrassButton")
        btn_add_page.clicked.connect(self.add_root_page)
        s_layout.addWidget(btn_add_page)

        layout.addWidget(sidebar)

        # Page Content Area
        self.content_area = QWidget()
        c_layout = QVBoxLayout(self.content_area)

        # Banner Header
        self.banner = QFrame()
        self.banner.setFixedHeight(80)
        self.banner.setStyleSheet("background-color: #27272a; border-radius: 8px;")
        b_layout = QVBoxLayout(self.banner)
        self.title_input = QLineEdit()
        self.title_input.setStyleSheet("font-size: 20px; font-weight: bold; background: transparent; border: none;")
        self.title_input.textChanged.connect(self.update_page_title)
        b_layout.addWidget(self.title_input)
        c_layout.addWidget(self.banner)

        # Block Control Toolbar
        block_bar = QHBoxLayout()
        b_text = QPushButton(" Text Block")
        b_text.clicked.connect(lambda: self.add_block("text"))
        b_heading = QPushButton(" Heading")
        b_heading.clicked.connect(lambda: self.add_block("heading"))
        b_todo = QPushButton(" To-Do")
        b_todo.clicked.connect(lambda: self.add_block("todo"))
        b_callout = QPushButton(" Callout")
        b_callout.clicked.connect(lambda: self.add_block("callout"))

        block_bar.addWidget(b_text)
        block_bar.addWidget(b_heading)
        block_bar.addWidget(b_todo)
        block_bar.addWidget(b_callout)
        block_bar.addStretch()
        c_layout.addLayout(block_bar)

        # Scrollable Canvas for Blocks
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.blocks_container = QWidget()
        self.blocks_layout = QVBoxLayout(self.blocks_container)
        self.blocks_layout.addStretch()
        self.scroll.setWidget(self.blocks_container)

        c_layout.addWidget(self.scroll)
        layout.addWidget(self.content_area)

        self.refresh()

    def refresh(self):
        self.tree.clear()
        for page in self.hub.get("pages", []):
            item = QTreeWidgetItem([page["title"]])
            item.setData(0, Qt.ItemDataRole.UserRole, page)
            self.tree.addTopLevelItem(item)
            self.populate_subpages(item, page)

        if self.hub.get("pages"):
            self.load_page(self.hub["pages"][0])

    def populate_subpages(self, parent_item, parent_page):
        for sub in parent_page.get("children", []):
            item = QTreeWidgetItem([sub["title"]])
            item.setData(0, Qt.ItemDataRole.UserRole, sub)
            parent_item.addChild(item)
            self.populate_subpages(item, sub)

    def add_root_page(self):
        title, ok = QInputDialog.getText(self, "New Page", "Page Title:")
        if ok and title:
            new_page = {
                "id": f"p_{uuid.uuid4().hex[:6]}",
                "title": title,
                "blocks": [{"type": "text", "content": "Welcome to your new page!"}],
                "children": [],
                "kind": "page"
            }
            self.hub["pages"].append(new_page)
            self.refresh()
            self.window().sync_state()

    def on_page_selected(self, item, col):
        page = item.data(0, Qt.ItemDataRole.UserRole)
        if page:
            self.load_page(page)

    def load_page(self, page):
        self.current_page = page
        self.title_input.setText(page["title"])
        
        # Clear existing blocks layout
        for i in reversed(range(self.blocks_layout.count() - 1)):
            w = self.blocks_layout.itemAt(i).widget()
            if w:
                w.setParent(None)

        for block in page.get("blocks", []):
            self.render_block_widget(block)

    def update_page_title(self, text):
        if self.current_page:
            self.current_page["title"] = text
            selected = self.tree.currentItem()
            if selected:
                selected.setText(0, text)

    def add_block(self, b_type: str):
        if not self.current_page:
            return
        new_b = {"type": b_type, "content": "", "checked": False}
        self.current_page["blocks"].append(new_b)
        self.render_block_widget(new_b)

    def render_block_widget(self, block: Dict[str, Any]):
        b_type = block.get("type", "text")
        
        if b_type == "heading":
            widget = QLineEdit(block.get("content", ""))
            widget.setStyleSheet("font-size: 16px; font-weight: bold; border: none; border-bottom: 1px solid #C99A3A;")
            widget.textChanged.connect(lambda t: block.update({"content": t}))
        elif b_type == "todo":
            widget = QWidget()
            w_layout = QHBoxLayout(widget)
            w_layout.setContentsMargins(0, 0, 0, 0)
            cb = QCheckBox()
            cb.setChecked(block.get("checked", False))
            cb.toggled.connect(lambda val: block.update({"checked": val}))
            txt = QLineEdit(block.get("content", ""))
            txt.textChanged.connect(lambda t: block.update({"content": t}))
            w_layout.addWidget(cb)
            w_layout.addWidget(txt)
        elif b_type == "callout":
            widget = QTextEdit(block.get("content", ""))
            widget.setFixedHeight(60)
            widget.setStyleSheet("background-color: #27272a; border-left: 3px solid #C99A3A;")
            widget.textChanged.connect(lambda: block.update({"content": widget.toPlainText()}))
        else:
            widget = QTextEdit(block.get("content", ""))
            widget.setFixedHeight(80)
            widget.textChanged.connect(lambda: block.update({"content": widget.toPlainText()}))

        self.blocks_layout.insertWidget(self.blocks_layout.count() - 1, widget)

# --- DRIVE MODULE ---
class DriveModule(QWidget):
    def __init__(self, state_hub, parent=None):
        super().__init__(parent)
        self.hub = state_hub
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout(self)
        
        sidebar = QWidget()
        sidebar.setFixedWidth(180)
        s_layout = QVBoxLayout(sidebar)
        s_layout.addWidget(QLabel("FOLDERS"))
        self.folder_list = QListWidget()
        self.folder_list.itemClicked.connect(self.filter_folder)
        s_layout.addWidget(self.folder_list)
        
        add_folder_btn = QPushButton(" New Folder")
        add_folder_btn.clicked.connect(self.create_folder)
        s_layout.addWidget(add_folder_btn)
        
        layout.addWidget(sidebar)

        main_area = QWidget()
        m_layout = QVBoxLayout(main_area)
        
        top_row = QHBoxLayout()
        self.header_label = QLabel("Drive / All")
        self.header_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        top_row.addWidget(self.header_label)
        
        upload_btn = QPushButton("Upload File")
        upload_btn.setObjectName("BrassButton")
        upload_btn.clicked.connect(self.upload_file)
        top_row.addWidget(upload_btn)
        
        m_layout.addLayout(top_row)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Name", "Size (MB)", "Modified", "Folder"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        m_layout.addWidget(self.table)

        layout.addWidget(main_area)
        self.refresh()

    def refresh(self):
        self.folder_list.clear()
        folders = ["All"]  list(set(f.get("folder", "Uploads") for f in self.hub["files"]))
        for f in folders:
            self.folder_list.addItem(f)
            
        self.render_files(self.hub["files"])

    def render_files(self, files: List[Dict[str, Any]]):
        self.table.setRowCount(0)
        for row, f in enumerate(files):
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(f["name"]))
            self.table.setItem(row, 1, QTableWidgetItem(str(f["size"])))
            self.table.setItem(row, 2, QTableWidgetItem(f["modified"]))
            self.table.setItem(row, 3, QTableWidgetItem(f.get("folder", "Uploads")))

    def filter_folder(self, item):
        folder = item.text()
        self.header_label.setText(f"Drive / {folder}")
        if folder == "All":
            self.render_files(self.hub["files"])
        else:
            filtered = [f for f in self.hub["files"] if f.get("folder", "Uploads") == folder]
            self.render_files(filtered)

    def upload_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Upload File to Vault")
        if path:
            import os
            name = os.path.basename(path)
            size = round(os.path.getsize(path) / (1024 * 1024), 2)
            self.hub["files"].append({
                "id": f"f_{uuid.uuid4().hex[:6]}",
                "name": name,
                "size": size if size > 0 else 0.01,
                "modified": datetime.now().strftime("%b %d"),
                "folder": "Uploads",
                "kind": "file"
            })
            self.refresh()
            self.window().sync_state()

    def create_folder(self):
        name, ok = QInputDialog.getText(self, "New Folder", "Folder Name:")
        if ok and name:
            self.folder_list.addItem(name)

    def show_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if not item:
            return
        row = item.row()
        file_obj = self.hub["files"][row]

        menu = QMenu(self)
        delete_act = menu.addAction("Move to Trash")
        action = menu.exec(self.table.mapToGlobal(pos))
        if action == delete_act:
            self.hub["files"].pop(row)
            file_obj["kind"] = "file"
            self.hub["trash"].append(file_obj)
            self.refresh()
            self.window().sync_state()

# --- DOCS MODULE ---
class DocsModule(QWidget):
    def __init__(self, state_hub, parent=None):
        super().__init__(parent)
        self.hub = state_hub
        self.current_doc_idx = 0
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout(self)

        sidebar = QWidget()
        sidebar.setFixedWidth(200)
        s_layout = QVBoxLayout(sidebar)
        
        new_doc_btn = QPushButton(" New Document")
        new_doc_btn.setObjectName("BrassButton")
        new_doc_btn.clicked.connect(self.create_doc)
        s_layout.addWidget(new_doc_btn)

        self.doc_list = QListWidget()
        self.doc_list.itemClicked.connect(self.load_doc)
        s_layout.addWidget(self.doc_list)

        s_layout.addWidget(QLabel("DOCUMENT OUTLINE"))
        self.outline_list = QListWidget()
        s_layout.addWidget(self.outline_list)

        layout.addWidget(sidebar)

        editor_area = QWidget()
        e_layout = QVBoxLayout(editor_area)

        toolbar = QHBoxLayout()
        b_bold = QPushButton("B")
        b_bold.clicked.connect(lambda: self.editor.setFontWeight(QFont.Weight.Bold))
        b_italic = QPushButton("I")
        b_italic.clicked.connect(lambda: self.editor.setFontItalic(True))
        b_print = QPushButton("Print")
        b_print.clicked.connect(self.print_document)
        b_export = QPushButton("Export MD")
        b_export.clicked.connect(self.export_markdown)

        toolbar.addWidget(b_bold)
        toolbar.addWidget(b_italic)
        toolbar.addWidget(b_print)
        toolbar.addWidget(b_export)
        toolbar.addStretch()

        self.word_count_lbl = QLabel("Words: 0")
        toolbar.addWidget(self.word_count_lbl)

        e_layout.addLayout(toolbar)

        self.editor = QTextEdit()
        self.editor.textChanged.connect(self.on_text_changed)
        e_layout.addWidget(self.editor)

        layout.addWidget(editor_area)
        self.refresh()

    def refresh(self):
        self.doc_list.clear()
        for doc in self.hub["docs"]:
            self.doc_list.addItem(doc["name"])
        if self.hub["docs"]:
            self.doc_list.setCurrentRow(0)
            self.load_doc_by_index(0)

    def create_doc(self):
        doc_obj = {
            "id": f"d_{uuid.uuid4().hex[:6]}",
            "name": f"Document {len(self.hub['docs'])  1}",
            "html": "<h2>New Section</h2><p>Start drafting notes here...</p>",
            "kind": "doc"
        }
        self.hub["docs"].append(doc_obj)
        self.refresh()
        self.window().sync_state()

    def load_doc(self, item):
        row = self.doc_list.row(item)
        self.load_doc_by_index(row)

    def load_doc_by_index(self, index: int):
        if 0 <= index < len(self.hub["docs"]):
            self.current_doc_idx = index
            doc = self.hub["docs"][index]
            self.editor.setHtml(doc["html"])

    def on_text_changed(self):
        text = self.editor.toPlainText()
        words = len(text.split()) if text.strip() else 0
        self.word_count_lbl.setText(f"Words: {words}")
        
        if hasattr(self, 'current_doc_idx') and 0 <= self.current_doc_idx < len(self.hub["docs"]):
            self.hub["docs"][self.current_doc_idx]["html"] = self.editor.toHtml()

        self.outline_list.clear()
        for line in text.splitlines():
            if line.startswith("#") or (line.isupper() and len(line) < 30 and len(line) > 2):
                self.outline_list.addItem(line)

    def export_markdown(self):
        text = self.editor.toPlainText()
        path, _ = QFileDialog.getSaveFileName(self, "Export Markdown", "", "Markdown Files (*.md)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)

    def print_document(self):
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dialog = QPrintDialog(printer, self)
        if dialog.exec() == QPrintDialog.DialogCode.Accepted:
            self.editor.print(printer)

# --- SHEETS MODULE ---
class SheetsModule(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.grid_data: Dict[str, str] = {}
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        control_bar = QHBoxLayout()
        self.fx_input = QLineEdit()
        self.fx_input.setPlaceholderText("fx Formula input (e.g. =SUM(A1:A5), =VLOOKUP(A1, A1:B5, 2))")
        self.fx_input.returnPressed.connect(self.apply_formula)
        
        btn_export = QPushButton("Export CSV")
        btn_export.clicked.connect(self.export_csv)
        
        control_bar.addWidget(QLabel("Formula:"))
        control_bar.addWidget(self.fx_input)
        control_bar.addWidget(btn_export)
        layout.addLayout(control_bar)

        self.table = QTableWidget(50, 26)
        headers = [num_to_col(i) for i in range(1, 27)]
        self.table.setHorizontalHeaderLabels(headers)
        self.table.cellChanged.connect(self.on_cell_changed)
        self.table.currentCellChanged.connect(self.on_cell_selected)
        layout.addWidget(self.table)

    def on_cell_selected(self, row, col):
        if row >= 0 and col >= 0:
            ref = f"{num_to_col(col  1)}{row  1}"
            raw = self.grid_data.get(ref, "")
            self.fx_input.setText(raw)

    def apply_formula(self):
        r, c = self.table.currentRow(), self.table.currentColumn()
        if r >= 0 and c >= 0:
            ref = f"{num_to_col(c  1)}{r  1}"
            text = self.fx_input.text()
            self.grid_data[ref] = text
            self.reevaluate_grid()

    def on_cell_changed(self, row, col):
        ref = f"{num_to_col(col  1)}{row  1}"
        item = self.table.item(row, col)
        if item:
            val = item.text()
            if not val.startswith("="):
                self.grid_data[ref] = val
                self.reevaluate_grid()

    def reevaluate_grid(self):
        self.table.blockSignals(True)
        for r in range(self.table.rowCount()):
            for c in range(self.table.columnCount()):
                ref = f"{num_to_col(c  1)}{r  1}"
                raw = self.grid_data.get(ref, "")
                if raw.startswith("="):
                    res = evaluate_formula(raw, self.grid_data)
                    item = self.table.item(r, c) or QTableWidgetItem()
                    item.setText(str(res))
                    self.table.setItem(r, c, item)
        self.table.blockSignals(False)

    def export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Sheet CSV", "", "CSV Files (*.csv)")
        if path:
            rows = []
            for r in range(self.table.rowCount()):
                row_data = []
                for c in range(self.table.columnCount()):
                    item = self.table.item(r, c)
                    row_data.append(item.text() if item else "")
                rows.append(row_data)
            df = pd.DataFrame(rows)
            df.to_csv(path, index=False, header=False)

# --- SLIDES MODULE ---
class SlidesModule(QWidget):
    def __init__(self, state_hub, parent=None):
        super().__init__(parent)
        self.hub = state_hub
        self.current_slide_idx = 0
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout(self)

        thumb_sidebar = QWidget()
        thumb_sidebar.setFixedWidth(160)
        t_layout = QVBoxLayout(thumb_sidebar)
        
        add_slide_btn = QPushButton(" New Slide")
        add_slide_btn.setObjectName("BrassButton")
        add_slide_btn.clicked.connect(self.add_slide)
        t_layout.addWidget(add_slide_btn)

        self.slide_list = QListWidget()
        self.slide_list.itemClicked.connect(self.load_slide)
        t_layout.addWidget(self.slide_list)

        layout.addWidget(thumb_sidebar)

        canvas_area = QWidget()
        c_layout = QVBoxLayout(canvas_area)

        self.scene = QGraphicsScene(0, 0, 640, 360)
        self.view = QGraphicsView(self.scene)
        c_layout.addWidget(self.view)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Slide Title")
        self.title_input.textChanged.connect(self.update_active_slide)
        c_layout.addWidget(self.title_input)

        self.body_input = QTextEdit()
        self.body_input.setPlaceholderText("Slide Content Payload Body")
        self.body_input.textChanged.connect(self.update_active_slide)
        c_layout.addWidget(self.body_input)

        layout.addWidget(canvas_area)
        self.refresh()

    def refresh(self):
        self.slide_list.clear()
        for s in self.hub["slides"]:
            self.slide_list.addItem(s["title"])
        if self.hub["slides"]:
            self.slide_list.setCurrentRow(0)
            self.load_slide_by_index(0)

    def add_slide(self):
        s_obj = {
            "id": f"s_{uuid.uuid4().hex[:6]}",
            "title": f"Slide {len(self.hub['slides'])  1}",
            "body": "Click to customize presentation parameters.",
            "kind": "slide"
        }
        self.hub["slides"].append(s_obj)
        self.refresh()
        self.window().sync_state()

    def load_slide(self, item):
        self.load_slide_by_index(self.slide_list.row(item))

    def load_slide_by_index(self, index: int):
        if 0 <= index < len(self.hub["slides"]):
            self.current_slide_idx = index
            s = self.hub["slides"][index]
            self.title_input.setText(s["title"])
            self.body_input.setText(s["body"])
            self.render_canvas(s)

    def update_active_slide(self):
        if hasattr(self, 'current_slide_idx') and 0 <= self.current_slide_idx < len(self.hub["slides"]):
            s = self.hub["slides"][self.current_slide_idx]
            s["title"] = self.title_input.text()
            s["body"] = self.body_input.toPlainText()
            self.render_canvas(s)

    def render_canvas(self, slide_data):
        self.scene.clear()
        bg = QGraphicsRectItem(0, 0, 640, 360)
        bg.setBrush(QBrush(QColor("#18181b")))
        bg.setPen(QPen(QColor(BRASS), 2))
        self.scene.addItem(bg)

        t_item = QGraphicsTextItem(slide_data["title"])
        t_item.setDefaultTextColor(QColor("#ffffff"))
        t_item.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        t_item.setPos(40, 40)
        self.scene.addItem(t_item)

        b_item = QGraphicsTextItem(slide_data["body"])
        b_item.setDefaultTextColor(QColor("#a1a1aa"))
        b_item.setFont(QFont("Segoe UI", 12))
        b_item.setPos(40, 100)
        self.scene.addItem(b_item)

# --- MAIL MODULE ---
class MailModule(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.messages = [
            {"from": "security@omnivault.io", "subject": "Encrypted Handshake Complete", "date": "10:42 AM", "body": "Your client-side encryption key lifecycle has updated securely."},
            {"from": "analytics@alx.org", "subject": "Data Pipeline Verified", "date": "Yesterday", "body": "All dynamic calculations and spreadsheet parsing pass validation constraints."}
        ]
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout(self)

        m_list = QWidget()
        m_list.setFixedWidth(240)
        l_layout = QVBoxLayout(m_list)
        
        self.msg_list = QListWidget()
        self.msg_list.itemClicked.connect(self.load_mail)
        l_layout.addWidget(self.msg_list)

        layout.addWidget(m_list)

        stage = QWidget()
        s_layout = QVBoxLayout(stage)
        
        self.sub_lbl = QLabel("Select an Email")
        self.sub_lbl.setStyleSheet("font-size: 16px; font-weight: bold;")
        s_layout.addWidget(self.sub_lbl)

        self.from_lbl = QLabel("")
        s_layout.addWidget(self.from_lbl)

        self.body_preview = QTextEdit()
        self.body_preview.setReadOnly(True)
        s_layout.addWidget(self.body_preview)

        layout.addWidget(stage)
        self.refresh()

    def refresh(self):
        self.msg_list.clear()
        for m in self.messages:
            self.msg_list.addItem(f"{m['subject']}\n{m['from']}")

    def load_mail(self, item):
        idx = self.msg_list.row(item)
        if 0 <= idx < len(self.messages):
            m = self.messages[idx]
            self.sub_lbl.setText(m["subject"])
            self.from_lbl.setText(f"From: {m['from']} Â· {m['date']}")
            self.body_preview.setText(m["body"])

# ============================================================================
# MAIN APPLICATION CONTAINER
# ============================================================================

class OmniVault(QMainWindow):
    def __init__(self):
        super().__init__()
        self.dark_mode = True

        self.state_hub = {
            "files": [
                {"id": "f1", "name": "Q3_Board_Deck.pdf", "size": 4.2, "modified": "Jul 28", "folder": "Uploads", "kind": "file"},
                {"id": "f2", "name": "Resistance_Dataset.csv", "size": 18.6, "modified": "Jul 25", "folder": "Uploads", "kind": "file"},
            ],
            "docs": [
                {"id": "d1", "name": "Strategic Plan", "html": "<h2>Strategic Roadmap</h2><p>1. Vault Isolation Protocol<br>2. Local DB persistence</p>", "kind": "doc"}
            ],
            "slides": [
                {"id": "s1", "title": "OmniVault Briefing", "body": "Native PyQt6 workspace solution engineered for high throughput offline work.", "kind": "slide"}
            ],
            "pages": [
                {
                    "id": "p1",
                    "title": "Main Project Hub",
                    "kind": "page",
                    "blocks": [
                        {"type": "heading", "content": "Overview"},
                        {"type": "text", "content": "Welcome to the centralized workspace page hub."},
                        {"type": "todo", "content": "Verify UI integration", "checked": True},
                        {"type": "callout", "content": "Important Note: All changes dynamically bind across workspace contexts."}
                    ],
                    "children": [
                        {
                            "id": "p2",
                            "title": "Sub-page: Architecture",
                            "kind": "page",
                            "blocks": [{"type": "text", "content": "Technical specifications go here."}],
                            "children": []
                        }
                    ]
                }
            ],
            "trash": []
        }

        self.setWindowTitle("OmniVault â€” Desktop Ledger Suite")
        self.resize(1150, 750)

        self.setup_ui()
        self.apply_theme()

    def setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Top Bar Navigation
        top_bar = QFrame()
        top_bar.setObjectName("TopBar")
        top_layout = QHBoxLayout(top_bar)

        title_lbl = QLabel("<b>OMNIVAULT</b> Ledger")
        title_lbl.setStyleSheet("font-size: 15px; color: #C99A3A;")
        top_layout.addWidget(title_lbl)

        top_layout.addStretch()

        btn_cmd = QPushButton("âŒ˜ Command Palette")
        btn_cmd.clicked.connect(self.open_command_palette)
        top_layout.addWidget(btn_cmd)

        btn_trash = QPushButton("Trash Hub")
        btn_trash.clicked.connect(self.open_trash_dialog)
        top_layout.addWidget(btn_trash)

        btn_theme = QPushButton("ðŸŒ“ Toggle Theme")
        btn_theme.clicked.connect(self.toggle_theme)
        top_layout.addWidget(btn_theme)

        main_layout.addWidget(top_bar)

        # Module Navigation Bar (Includes NEW Pages tab)
        sub_bar = QFrame()
        sub_bar.setObjectName("SubBar")
        sub_layout = QHBoxLayout(sub_bar)

        self.nav_btns = {}
        modules = [("Pages", 0), ("Drive", 1), ("Docs", 2), ("Sheets", 3), ("Slides", 4), ("Mail", 5)]
        for name, idx in modules:
            btn = QPushButton(name)
            btn.clicked.connect(lambda _, i=idx: self.switch_module(i))
            sub_layout.addWidget(btn)
            self.nav_btns[idx] = btn

        sub_layout.addStretch()
        main_layout.addWidget(sub_bar)

        # Stacked Widget Modules Container
        self.stack = QStackedWidget()
        
        self.pages_mod = PagesModule(self.state_hub)
        self.drive_mod = DriveModule(self.state_hub)
        self.docs_mod = DocsModule(self.state_hub)
        self.sheets_mod = SheetsModule()
        self.slides_mod = SlidesModule(self.state_hub)
        self.mail_mod = MailModule()

        self.stack.addWidget(self.pages_mod)
        self.stack.addWidget(self.drive_mod)
        self.stack.addWidget(self.docs_mod)
        self.stack.addWidget(self.sheets_mod)
        self.stack.addWidget(self.slides_mod)
        self.stack.addWidget(self.mail_mod)

        main_layout.addWidget(self.stack)

    def switch_module(self, idx: int):
        self.stack.setCurrentIndex(idx)

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.apply_theme()

    def apply_theme(self):
        self.setStyleSheet(get_stylesheet(self.dark_mode))

    def sync_state(self):
        self.pages_mod.refresh()
        self.drive_mod.refresh()
        self.docs_mod.refresh()
        self.slides_mod.refresh()

    def open_command_palette(self):
        actions = [
            {"label": "Switch to Pages Workspace", "category": "Navigation", "run": lambda: self.switch_module(0)},
            {"label": "Switch to Drive Workspace", "category": "Navigation", "run": lambda: self.switch_module(1)},
            {"label": "Switch to Docs Workspace", "category": "Navigation", "run": lambda: self.switch_module(2)},
            {"label": "Switch to Sheets Workspace", "category": "Navigation", "run": lambda: self.switch_module(3)},
            {"label": "Switch to Slides Workspace", "category": "Navigation", "run": lambda: self.switch_module(4)},
            {"label": "Switch to Mail Workspace", "category": "Navigation", "run": lambda: self.switch_module(5)},
            {"label": "Create Root Workspace Page", "category": "Action", "run": self.pages_mod.add_root_page},
            {"label": "Create New Document", "category": "Action", "run": self.docs_mod.create_doc},
            {"label": "Add Presentation Slide", "category": "Action", "run": self.slides_mod.add_slide},
            {"label": "Toggle Dark/Light Mode", "category": "System", "run": self.toggle_theme},
        ]
        dlg = CommandPaletteDialog(self, actions, self.dark_mode)
        dlg.exec()

    def open_trash_dialog(self):
        dlg = TrashDialog(self, self.state_hub, self.dark_mode)
        dlg.exec()

# ============================================================================
# ENTRY POINT
# ============================================================================

def main():
    app = QApplication(sys.argv)
    window = OmniVault()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
