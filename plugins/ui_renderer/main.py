import os
import re
import sys
import json
import math
import subprocess
from typing import Optional, Dict, Any, List

import numpy as np

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QLabel, QSplitter, QTreeWidget, QTreeWidgetItem,
    QPushButton, QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt, QPoint, QTimer
from PyQt6.QtGui import QFont, QSurfaceFormat

# QOpenGLWidget must come from QtOpenGLWidgets
from PyQt6.QtOpenGLWidgets import QOpenGLWidget

# PyOpenGL imports
from OpenGL.GL import *

# constants.py
MISSION_IDS = {
    0: [20001882, 20001884, 20001886, 20001888, 20001890],
    1: [20001835, 20001837, 20001839],
    2: [20001855, 20001858, 20001861, 20001864],
    3: [20001870, 20001872, 20001874],
    4: [20001832, 20001844, 20001847, 20001850]
}

FACTION_GAPS = [12, 20, 12, 12, 12]

FACTION_NAMES = ["Solar Empire","Western Frontier","Anglo Isles","Iron Legion","Tundran Territories"]

FACTION_ABBR = ["SE","WF","AI","IL","TT"]

BACKGROUND_SETTINGS = {
    0: {'x': -40, 'y': -140, 'scale': 1.95, 'rotation': 0},
    1: {'x': 640, 'y': 190, 'scale': 2.45, 'rotation': 5},
    2: {'x': -930, 'y': -380, 'scale': 2.50, 'rotation': 0},
    3: {'x': -490, 'y': -10, 'scale': 2.00, 'rotation': 15},
    4: {'x': 310, 'y': 220, 'scale': 2.45, 'rotation': 10}
}

class MSVector:
    """Position object compatible with the renderer (has .x and .z)"""
    def __init__(self, x=0.0, z=0.0):
        self.x = x
        self.z = z

# ---------------------------
# Utility - Matrix functions
# ---------------------------
def mat(a1, a2, b1, b2):
    """Return 3x3 numpy matrix representing 2D linear transform with translation column zero."""
    m = np.array([[a1, a2, 0.0],
                  [b1, b2, 0.0],
                  [0.0, 0.0, 1.0]], dtype=float)
    return m

def translate(x, y):
    return np.array([[1, 0, x],
                     [0, 1, y],
                     [0, 0, 1]], dtype=np.float32)

def scale(sx, sy):
    return np.array([[sx, 0, 0],
                     [0, sy, 0],
                     [0, 0, 1]], dtype=np.float32)

def rotate_deg(angle):
    rad = np.radians(angle)
    c, s = np.cos(rad), np.sin(rad)
    return np.array([[c, -s, 0],
                     [s, c, 0],
                     [0, 0, 1]], dtype=np.float32)

def transform_point(mtx, x, y):
    p = np.array([x, y, 1], dtype=np.float32)
    t = mtx @ p
    return t[0], t[1]

def point_in_poly(x, y, poly):
    # Ray-casting algorithm
    n = len(poly)
    inside = False
    px, py = poly[0]
    for i in range(1, n + 1):
        cx, cy = poly[i % n]
        if ((cy > y) != (py > y)) and (x < (px - cx) * (y - cy) / (py - cy + 1e-6) + cx):
            inside = not inside
        px, py = cx, cy
    return inside

class GLRendererWidget(QOpenGLWidget):
    def __init__(self, editor=None, parent=None):
        fmt = QSurfaceFormat()
        fmt.setDepthBufferSize(24)
        fmt.setMajorVersion(2)
        fmt.setMinorVersion(1)
        QSurfaceFormat.setDefaultFormat(fmt)

        super().__init__(parent)
        self.editor = editor  # Store editor reference
        self.level_data: Dict[str, Any] = {}
        self.lua_data: Dict[str, Any] = {}
        self.current_page: Optional[Dict[str, Any]] = None
        self.selected_widget: Optional[Dict[str, Any]] = None

        self.on_widget_selected_callback = None

        # view transform
        self.scale = 1.0
        
        # Fixed view offset - calculate once and keep stable
        self.view_offset = {'x': 0, 'y': 0}
        self.view_calculated = False

        # dragging state
        self.dragging_widget: Optional[Dict[str, Any]] = None
        self.drag_offset = {'x': 0.0, 'y': 0.0}

        # widget filtering
        self.full_widget_list = []
        self.filtered_widgets = []

        # continuous repaint
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.update)
        self._timer.start(30)

    # -----------------
    # Helpers
    # -----------------
    @staticmethod
    def safe_get(d, key, default=0):
        if isinstance(d, dict):
            return d.get(key, default)
        return default

    # -----------------
    # Public API
    # -----------------
    def set_data(self, level_data: Dict[str, Any], lua_data: Dict[str, Any]):
        self.level_data = level_data or {}
        self.lua_data = lua_data or {}

    def set_current_page(self, page):
        self.current_page = page
        self.selected_widget = None
        self.full_widget_list = page.get('widgets', []) or []
        self.filtered_widgets = self.full_widget_list
        self.view_calculated = False  # Recalculate view for new page
        self.update()

    def set_selected_widget(self, widget):
        """Set selected widget from tree view - this changes the view"""
        self.selected_widget = widget
        if widget and widget.get('children'):
            self.filtered_widgets = widget['children']
        elif widget:
            # Show the widget in context of its parent if available
            self.filtered_widgets = self.full_widget_list
        else:
            self.filtered_widgets = self.full_widget_list
        self.update()

    # -----------------
    # OpenGL lifecycle
    # -----------------
    def initializeGL(self):
        glClearColor(0.13, 0.13, 0.13, 1.0)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glDisable(GL_DEPTH_TEST)

    def resizeGL(self, w: int, h: int):
        glViewport(0, 0, w, h)
        self.view_calculated = False  # Recalculate view on resize
        self.update()

    # -----------------
    # Core drawing
    # -----------------
    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        if not self.current_page:
            return

        w, h = self.width(), self.height()

        # 2D projection
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0, w, h, 0, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        widgets = self.filtered_widgets or self.current_page.get('widgets', []) or []
        if not widgets:
            return

        # Calculate view offset only once (or when explicitly reset)
        if not self.view_calculated:
            def compute_bounds(widget_list, parent_pos=(0, 0)):
                min_x, min_y = float('inf'), float('inf')
                max_x, max_y = float('-inf'), float('-inf')
                for widget in widget_list:
                    if not isinstance(widget, dict):
                        continue
                    pos = widget.get('position') or {'x': 0, 'y': 0}
                    size = widget.get('size') or {'x': 64, 'y': 32}
                    px = float(pos.get('x', 0)) + parent_pos[0]
                    py = float(pos.get('y', 0)) + parent_pos[1]
                    sx = float(size.get('x', 64))
                    sy = float(size.get('y', 32))
                    min_x, min_y = min(min_x, px), min(min_y, py)
                    max_x, max_y = max(max_x, px + sx), max(max_y, py + sy)

                    # children
                    children = widget.get('children') or []
                    if children:
                        cminx, cminy, cmaxx, cmaxy = compute_bounds(children, (px, py))
                        min_x, min_y = min(min_x, cminx), min(min_y, cminy)
                        max_x, max_y = max(max_x, cmaxx), max(max_y, cmaxy)
                if min_x == float('inf'):
                    return 0, 0, 0, 0
                return min_x, min_y, max_x, max_y

            min_x, min_y, max_x, max_y = compute_bounds(widgets)
            content_width, content_height = max_x - min_x, max_y - min_y

            self.view_offset['x'] = (w - content_width) / 2 - min_x
            self.view_offset['y'] = (h - content_height) / 2 - min_y
            self.view_calculated = True

        # Use the stable offset
        base_mtx = translate(self.view_offset['x'], self.view_offset['y'])

        # recursive draw
        for widget in widgets:
            self._draw_widget_recursive(widget, base_mtx)

    def _widget_local_transform(self, widget):
        if not isinstance(widget, dict):
            return np.identity(3, dtype=np.float32)

        pos = widget.get('position') or {'x': 0, 'y': 0}
        sc = widget.get('scale') or {'x': 1, 'y': 1}
        rot = widget.get('rotation') or 0
        px, py = float(pos.get('x', 0)) * self.scale, float(pos.get('y', 0)) * self.scale
        sx, sy = float(sc.get('x', 1)), float(sc.get('y', 1))
        m = translate(px, py) @ (rotate_deg(rot) if rot else np.identity(3)) @ scale(sx, sy)
        return m

    def _compute_widget_corners(self, parent_mtx, widget):
        if not isinstance(widget, dict):
            return [(0,0),(0,0),(0,0),(0,0)]
        size = widget.get('size') or {'x': 64, 'y': 32}
        w, h = float(size.get('x',64))*self.scale, float(size.get('y',32))*self.scale
        m = parent_mtx @ self._widget_local_transform(widget)
        return [
            transform_point(m, 0,0),
            transform_point(m, w,0),
            transform_point(m, w,h),
            transform_point(m, 0,h)
        ]

    def _draw_quad(self, corners, fill_color, outline_color, line_width=2.0):
        glColor4f(*fill_color)
        glBegin(GL_POLYGON)
        for x,y in corners:
            glVertex2f(x,y)
        glEnd()
        glLineWidth(line_width)
        glColor4f(*outline_color)
        glBegin(GL_LINE_LOOP)
        for x,y in corners:
            glVertex2f(x,y)
        glEnd()
        glLineWidth(1.0)

    def _draw_widget_recursive(self, widget, parent_mtx, depth=0):
        if not isinstance(widget, dict):
            return

        corners = self._compute_widget_corners(parent_mtx, widget)

        depth_val = max(0, min(1, 1.0 - depth*0.12))
        base_r, base_g, base_b = depth_val*0.9, depth_val*0.9, depth_val*0.95
        fill_alpha, outline_alpha = 0.22, 0.95

        if self.selected_widget and widget.get('id') == self.selected_widget.get('id'):
            fill_col = (1,0.35,0.35,0.35)
            outline_col = (1,0.7,0.7,1.0)
            lw = 3.0
        else:
            fill_col = (base_r, base_g, base_b, fill_alpha)
            outline_col = (base_r+0.15, base_g+0.15, base_b+0.15, outline_alpha)
            lw = 2.0

        self._draw_quad(corners, fill_col, outline_col, lw)

        local_mtx = self._widget_local_transform(widget)
        combined_mtx = parent_mtx @ local_mtx
        for c in widget.get('children') or []:
            self._draw_widget_recursive(c, combined_mtx, depth+1)

    def _determine_widget_indices(self, widget):
        """
        Determine the faction and mission index for a widget based on its mission_id.
        Returns (faction_idx, mission_idx) or (None, None) if not found.
        """
        mission_id = widget.get('mission_id')
        if mission_id is None:
            return None, None

        for faction_idx, ids in MISSION_IDS.items():
            if mission_id in ids:
                mission_idx = ids.index(mission_id)
                return faction_idx, mission_idx

        return None, None

    # -----------------
    # Mouse interaction
    # -----------------

    def mousePressEvent(self, e):
        """Select only visible/rendered widgets by clicking in the OpenGL area."""
        if not self.current_page:
            return

        mx, my = e.position().x(), e.position().y()
        hit_widget = None

        # Use the stable view offset
        base_mtx = translate(self.view_offset['x'], self.view_offset['y'])
        
        widgets = self.filtered_widgets or self.current_page.get('widgets', []) or []
        if not widgets:
            return

        def hit_test(widget, parent_mtx):
            nonlocal hit_widget
            if not isinstance(widget, dict):
                return

            corners = self._compute_widget_corners(parent_mtx, widget)
            if point_in_poly(mx, my, corners):
                hit_widget = widget

            local_mtx = self._widget_local_transform(widget)
            combined_mtx = parent_mtx @ local_mtx
            for child in (widget.get('children') or []):
                hit_test(child, combined_mtx)

        for w in widgets:
            hit_test(w, base_mtx)

        # Handle selection
        if hit_widget:
            self.selected_widget = hit_widget
            self.dragging_widget = hit_widget
            
            # Store the current position and calculate offset
            pos = hit_widget.get('position') or {'x': 0, 'y': 0}
            current_x = pos.get('x', 0) * self.scale + self.view_offset['x']
            current_y = pos.get('y', 0) * self.scale + self.view_offset['y']
            self.drag_offset['x'] = mx - current_x
            self.drag_offset['y'] = my - current_y
        else:
            self.selected_widget = None
            self.dragging_widget = None

        self.update()


    def mouseMoveEvent(self, e):
        if not self.dragging_widget:
            return
        
        mx, my = e.position().x(), e.position().y()
        
        # Use the stable view offset
        new_x = (mx - self.drag_offset['x'] - self.view_offset['x']) / self.scale
        new_y = (my - self.drag_offset['y'] - self.view_offset['y']) / self.scale
        
        # Update the widget's display position
        pos = self.dragging_widget.setdefault('position', {'x': 0, 'y': 0})
        pos['x'], pos['y'] = new_x, new_y

        # Update the actual object reference
        pos_obj_ref = self.dragging_widget.get('pos_obj_ref')
        if pos_obj_ref:
            # Convert string msVector to object if necessary
            if isinstance(pos_obj_ref.msVector, str):
                parts = pos_obj_ref.msVector.split(',')
                if len(parts) >= 2:
                    pos_obj_ref.msVector = MSVector(float(parts[0]), float(parts[1]))
            
            # Assign new coordinates
            if hasattr(pos_obj_ref.msVector, 'x') and hasattr(pos_obj_ref.msVector, 'z'):
                pos_obj_ref.msVector.x = new_x
                pos_obj_ref.msVector.z = new_y

            # Mark as modified
            if self.editor:
                if hasattr(pos_obj_ref, 'modified'):
                    pos_obj_ref.modified = True
                if hasattr(self.editor, 'level_file') and self.editor.level_file:
                    if hasattr(self.editor.level_file, 'modified'):
                        self.editor.level_file.modified = True
                if hasattr(self.editor, 'set_unsaved_changes'):
                    self.editor.set_unsaved_changes(True)
                if hasattr(self.editor, 'level_view') and hasattr(self.editor.level_view, 'do_redraw'):
                    self.editor.level_view.do_redraw()

        self.update()

    def mouseReleaseEvent(self, e):
        """When drag ends, update the Lua file"""
        if self.dragging_widget and 'mission_id' in self.dragging_widget:
            # Get the final position
            pos = self.dragging_widget.get('position', {})
            mission_id = self.dragging_widget['mission_id']
            
            # Update Campaign.lua
            self.update_lua_mission_position(mission_id, pos['x'], pos['y'])
        
        self.dragging_widget = None

    def update_lua_mission_position(self, mission_id, x, y):
        """Update a specific mission position in Campaign.lua"""
        if not self.editor or not self.editor.current_gen_path:
            return
        
        lua_folder = os.path.splitext(self.editor.current_gen_path)[0] + ".xml_lua"
        lua_path = os.path.join(os.path.dirname(self.editor.current_gen_path), lua_folder, "Campaign.lua")
        
        if not os.path.exists(lua_path):
            print(f"Campaign.lua not found at {lua_path}")
            return
        
        with open(lua_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Match {X = <number>, Y = <number>} -- <mission_id>
        pattern = rf'(\{{\s*X\s*=\s*)\d+(\s*,\s*Y\s*=\s*)\d+(\s*\}},?\s*--\s*{mission_id})'
        replacement = rf'\g<1>{int(x)}\g<2>{int(y)}\g<3>'
        
        new_content, count = re.subn(pattern, replacement, content)
        
        if count == 0:
            print(f"No match found for mission {mission_id} in Campaign.lua")
            return
        
        with open(lua_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"Updated mission {mission_id} to position ({x}, {y}) in Campaign.lua")

# ---------------------------
# Main GUI window (left panes + GL view)
# ---------------------------
class GUIRendererWindow(QMainWindow):
    def __init__(self, level_data: Dict[str, Any], lua_data: Dict[str, Any], editor=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("GUI Renderer - OpenGL")
        self.resize(1400, 900)

        self.level_data = level_data or {}
        self.lua_data = lua_data or {}
        self.editor = editor  # Store editor reference

        self.lua_data = {}

        # Central widget and layout
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # Left panel
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(6, 6, 6, 6)

        left_layout.addWidget(QLabel("Pages:"))
        self.page_list = QListWidget()
        self.page_list.currentItemChanged.connect(self.on_page_selected)
        left_layout.addWidget(self.page_list, stretch=1)

        left_layout.addWidget(QLabel("Widget Hierarchy:"))
        self.widget_tree = QTreeWidget()
        self.widget_tree.setHeaderLabels(["Widget", "Type"])
        self.widget_tree.itemClicked.connect(self.on_widget_tree_click)
        left_layout.addWidget(self.widget_tree, stretch=2)

        self.info_label = QLabel("Select a page to view")
        self.info_label.setFont(QFont("Arial", 10))
        left_layout.addWidget(self.info_label)

        # Open Lua Folder button
        self.open_lua_button = QPushButton("Open Lua Folder", left_widget)
        self.open_lua_button.clicked.connect(self.open_lua_folder)
        left_layout.addWidget(self.open_lua_button)

        splitter.addWidget(left_widget)

        # Add Save to Lua button below Open Lua Folder
        self.save_lua_btn = QPushButton("Save to Lua", left_widget)
        self.save_lua_btn.clicked.connect(self.save_all_lua_files)
        left_layout.addWidget(self.save_lua_btn)

        # Right: OpenGL view
        self.gl_widget = GLRendererWidget(editor)
        self.gl_widget.set_data(self.level_data, self.lua_data)
        splitter.addWidget(self.gl_widget)

        splitter.setSizes([380, 1020])
        self.populate_page_list()

    def save_all_lua_files(self):
        if not self.lua_data:
            print("No Lua files loaded.")
            return

        folder_path = self._get_current_lua_folder()
        if not folder_path:
            print("Lua folder not found.")
            return

        for filename, content in self.lua_data.items():
            path = os.path.join(folder_path, filename)
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"Saved {filename}")
            except Exception as e:
                print(f"Failed to save {filename}: {e}")

    def populate_page_list(self):
        pages = self.level_data.get('pages', {})
        self.page_list.clear()
        for pid, pdata in pages.items():
            name = pdata.get('name') or f"Page_{pid}"
            total = self._count_widgets(pdata.get('widgets', []))
            item_text = f"{name} ({total} widgets)"
            self.page_list.addItem(item_text)
            item = self.page_list.item(self.page_list.count() - 1)
            item.setData(Qt.ItemDataRole.UserRole, pid)

        if self.page_list.count() > 0:
            self.page_list.setCurrentRow(0)

    def _count_widgets(self, widgets):
        c = 0
        for w in widgets:
            c += 1
            c += self._count_widgets(w.get('children', []))
        return c

    def on_page_selected(self, current, previous):
        if current is None:
            return
        pid = current.data(Qt.ItemDataRole.UserRole)
        pages = self.level_data.get('pages', {})
        page = pages.get(str(pid)) or pages.get(pid)
        if not page:
            return
        
        # If we have an editor reference, refresh the page data
        if self.editor:
            # Re-extract the widget data for this page to get fresh positions
            refreshed_page = self._refresh_page_data(pid)
            if refreshed_page:
                page = refreshed_page
                # Update our stored data
                self.level_data['pages'][pid] = page
        
        self.current_page = page
        self.gl_widget.set_current_page(page)
        
        # populate tree
        self.widget_tree.clear()
        for w in page.get('widgets', []):
            self._add_widget_tree_item(w, self.widget_tree)
        
        # script info
        script = page.get('script_name')
        if script:
            info_text = f"Page: {page.get('name')}  \nID: {page.get('id')}\nScript: {script}.lua"
        else:
            info_text = f"Page: {page.get('name')}\nID: {page.get('id')}"
            
        self.info_label.setText(info_text)

        # No open_script_btn anymore, so just optionally store the path
        if page.get('script_path'):
            page['_script_path'] = page.get('script_path')

    def _refresh_page_data(self, page_id):
        """Re-extract widget data for a specific page"""
        if not self.editor or not self.editor.level_file:
            return None
        
        # Find the page object
        page_obj = self.editor.level_file.objects.get(page_id)
        if not page_obj or page_obj.type != "cGUIPage":
            return None
        
        # Use the same logic as in the plugin to extract fresh data
        page_name = getattr(page_obj, 'customname', None) or getattr(page_obj, 'lua_name', '') or f"Page_{page_id}"
        
        page_data = {
            'id': page_id,
            'name': page_name,
            'widgets': [],
            'script_name': None,
            'script_path': None
        }
        
        # Get script info (this probably hasn't changed but include it for completeness)
        if hasattr(page_obj, 'mpScript') and page_obj.mpScript is not None:
            init_script = page_obj.mpScript
            if hasattr(init_script, 'mpScript') and init_script.mpScript is not None:
                game_script = init_script.mpScript
                if hasattr(game_script, 'mName'):
                    script_name = game_script.mName
                    page_data['script_name'] = script_name
                    
                    if self.editor.current_gen_path:
                        level_dir = os.path.dirname(self.editor.current_gen_path)
                        lua_folder = os.path.splitext(os.path.basename(self.editor.current_gen_path))[0] + ".xml_lua"
                        lua_path = os.path.join(level_dir, lua_folder, script_name + ".lua")
                        
                        if os.path.exists(lua_path):
                            page_data['script_path'] = lua_path
        
        # Build widget tree with fresh position data
        if hasattr(page_obj, 'mWidgetArray'):
            visited = set()
            widget_array = page_obj.mWidgetArray
            if isinstance(widget_array, list):
                for widget_obj in widget_array:
                    if widget_obj is not None and not widget_obj.deleted:
                        widget_tree = self._build_widget_tree_fresh(widget_obj, visited)
                        if widget_tree:
                            page_data['widgets'].append(widget_tree)
            elif widget_array is not None and not widget_array.deleted:
                widget_tree = self._build_widget_tree_fresh(widget_array, visited)
                if widget_tree:
                    page_data['widgets'].append(widget_tree)
        
        return page_data

    def _build_widget_tree_fresh(self, widget_obj, visited=None):
        """Rebuild widget tree with fresh data"""
        if visited is None:
            visited = set()
        
        if widget_obj is None or widget_obj.id in visited or widget_obj.deleted:
            return None
        
        visited.add(widget_obj.id)
        
        # Extract fresh widget data
        widget_data = self._get_widget_data_fresh(widget_obj, widget_obj.id)
        
        # Get child widgets
        if hasattr(widget_obj, 'mWidgetArray'):
            widget_array = widget_obj.mWidgetArray
            if isinstance(widget_array, list):
                for child_obj in widget_array:
                    if child_obj is not None and not child_obj.deleted:
                        child_widget = self._build_widget_tree_fresh(child_obj, visited)
                        if child_widget:
                            widget_data['children'].append(child_widget)
            elif widget_array is not None and not widget_array.deleted:
                child_widget = self._build_widget_tree_fresh(widget_array, visited)
                if child_widget:
                    widget_data['children'].append(child_widget)
        
        return widget_data

    def _get_widget_data_fresh(self, obj, obj_id):
        """Extract fresh widget data"""
        widget_data = {
            'id': obj_id,
            'type': obj.type,
            'name': getattr(obj, 'customname', None) or getattr(obj, 'lua_name', '') or f"{obj.type}_{obj_id}",
            'texture': None,
            'position': None,
            'size': None,
            'children': [],
            'obj_ref': obj,
            'pos_obj_ref': None,
            'msVector_ref': None
        }
        
        # Get fresh position data
        if hasattr(obj, 'mpPos') and obj.mpPos is not None:
            pos_obj = obj.mpPos
            widget_data['pos_obj_ref'] = pos_obj
            
            # Parse the current position value
            if hasattr(pos_obj, 'msVector'):
                msVector = pos_obj.msVector
                if isinstance(msVector, str):
                    parts = msVector.split(',')
                    if len(parts) >= 2:
                        widget_data['position'] = {'x': float(parts[0]), 'y': float(parts[1])}
                elif hasattr(msVector, 'x') and hasattr(msVector, 'z'):
                    widget_data['position'] = {'x': msVector.x, 'y': msVector.z}
                    widget_data['msVector_ref'] = msVector
        
        # Get size
        if hasattr(obj, 'mpSize') and obj.mpSize is not None:
            size_obj = obj.mpSize
            if hasattr(size_obj, 'msVector'):
                msVector = size_obj.msVector
                if isinstance(msVector, str):
                    parts = msVector.split(',')
                    if len(parts) >= 2:
                        widget_data['size'] = {'x': float(parts[0]), 'y': float(parts[1])}
                elif hasattr(msVector, 'x') and hasattr(msVector, 'z'):
                    widget_data['size'] = {'x': msVector.x, 'y': msVector.z}
        
        return widget_data

    def _add_widget_tree_item(self, widget: Dict[str, Any], parent):
        item = QTreeWidgetItem(parent)
        item.setText(0, widget.get('name', '<unnamed>'))
        item.setText(1, widget.get('type', ''))
        item.setData(0, Qt.ItemDataRole.UserRole, widget)
        for c in widget.get('children', []):
            self._add_widget_tree_item(c, item)
        item.setExpanded(True)

    def on_widget_tree_click(self, item, col):
        w = item.data(0, Qt.ItemDataRole.UserRole)
        if w:
            self.gl_widget.set_selected_widget(w)

    def open_lua_folder(self):
        folder = self._get_current_lua_folder()
        if folder and os.path.exists(folder):
            os.startfile(folder)
            self.load_lua_folder(folder)  # load all Lua files
        else:
            print("Lua folder not found")


    def load_lua_folder(self, folder_path):
        """Load all .lua files in a folder into self.lua_data"""
        if not os.path.exists(folder_path):
            print("Lua folder not found:", folder_path)
            return
        
        self.lua_data.clear()
        for file in os.listdir(folder_path):
            if file.lower().endswith(".lua"):
                path = os.path.join(folder_path, file)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    self.lua_data[file] = content
                    print(f"Loaded {file}")
                except Exception as e:
                    print(f"Failed to load {file}: {e}")

    def save_lua_file(self, filename, content):
        """Overwrite a lua file in the loaded folder"""
        folder_path = self._get_current_lua_folder()
        if not folder_path:
            return
        path = os.path.join(folder_path, filename)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Saved {filename}")

    def _get_current_lua_folder(self):
        if not self.editor or not self.editor.current_gen_path:
            return None
        xml_name = os.path.basename(self.editor.current_gen_path)
        lua_folder_name = os.path.splitext(xml_name)[0] + ".xml_lua"
        folder_path = os.path.join(os.path.dirname(self.editor.current_gen_path), lua_folder_name)
        return folder_path if os.path.exists(folder_path) else None
