﻿from math import sqrt

from PySide6.QtCore import Qt, QPointF, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from sovereign_cad.desktop.document import CADObject


class CADView(QWidget):

    coordinatesChanged = Signal(float, float)

    def __init__(self, document, parent=None):
        super().__init__(parent)

        self.document = document

        self.tool = "SELECT"

        self.zoom = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0

        self.start_point = None
        self.current_point = None

        self.panning = False
        self.last_mouse = None

        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)

    # --------------------------------------------------------

    def world_to_screen(self, x, y):
        return QPointF(
            self.width() / 2 + (x + self.pan_x) * self.zoom,
            self.height() / 2 - (y + self.pan_y) * self.zoom
        )

    def screen_to_world(self, point):
        x = (
            point.x() - self.width() / 2
        ) / self.zoom - self.pan_x

        y = -(
            point.y() - self.height() / 2
        ) / self.zoom - self.pan_y

        return x, y

    # --------------------------------------------------------

    def set_tool(self, tool):
        self.tool = tool.upper()
        self.start_point = None
        self.current_point = None

        if self.tool == "SELECT":
            self.setCursor(Qt.ArrowCursor)
        else:
            self.setCursor(Qt.CrossCursor)

        self.update()

    # --------------------------------------------------------

    def paintEvent(self, event):
        painter = QPainter(self)

        painter.fillRect(
            self.rect(),
            QColor(25, 28, 33)
        )

        painter.setRenderHint(
            QPainter.Antialiasing
        )

        self.draw_grid(painter)

        for obj in self.document.objects:
            self.draw_object(painter, obj)

        self.draw_preview(painter)

    # --------------------------------------------------------

    def draw_grid(self, painter):
        painter.setPen(
            QPen(QColor(48, 52, 60), 1)
        )

        grid = max(20, int(25 * self.zoom))

        for x in range(0, self.width(), grid):
            painter.drawLine(x, 0, x, self.height())

        for y in range(0, self.height(), grid):
            painter.drawLine(0, y, self.width(), y)

        origin = self.world_to_screen(0, 0)

        painter.setPen(
            QPen(QColor(100, 100, 100), 1)
        )

        painter.drawLine(
            0,
            int(origin.y()),
            self.width(),
            int(origin.y())
        )

        painter.drawLine(
            int(origin.x()),
            0,
            int(origin.x()),
            self.height()
        )

    # --------------------------------------------------------

    def draw_object(self, painter, obj):

        if obj.selected:
            color = QColor(0, 200, 255)
            width = 3
        else:
            color = QColor(230, 230, 230)
            width = 2

        painter.setPen(QPen(color, width))

        if obj.kind == "LINE":

            p1 = self.world_to_screen(
                obj.data["x1"],
                obj.data["y1"]
            )

            p2 = self.world_to_screen(
                obj.data["x2"],
                obj.data["y2"]
            )

            painter.drawLine(p1, p2)

        elif obj.kind == "CIRCLE":

            center = self.world_to_screen(
                obj.data["x"],
                obj.data["y"]
            )

            radius = obj.data["radius"] * self.zoom

            painter.drawEllipse(
                center,
                radius,
                radius
            )

        elif obj.kind == "RECTANGLE":

            x1 = min(obj.data["x1"], obj.data["x2"])
            x2 = max(obj.data["x1"], obj.data["x2"])

            y1 = min(obj.data["y1"], obj.data["y2"])
            y2 = max(obj.data["y1"], obj.data["y2"])

            p1 = self.world_to_screen(x1, y2)
            p2 = self.world_to_screen(x2, y1)

            painter.drawRect(
                p1.x(),
                p1.y(),
                p2.x() - p1.x(),
                p2.y() - p1.y()
            )

    # --------------------------------------------------------

    def draw_preview(self, painter):

        if self.start_point is None:
            return

        if self.current_point is None:
            return

        painter.setPen(
            QPen(
                QColor(255, 200, 0),
                1,
                Qt.DashLine
            )
        )

        x1, y1 = self.start_point
        x2, y2 = self.current_point

        if self.tool == "LINE":

            painter.drawLine(
                self.world_to_screen(x1, y1),
                self.world_to_screen(x2, y2)
            )

        elif self.tool == "CIRCLE":

            radius = sqrt(
                (x2 - x1) ** 2 +
                (y2 - y1) ** 2
            )

            painter.drawEllipse(
                self.world_to_screen(x1, y1),
                radius * self.zoom,
                radius * self.zoom
            )

        elif self.tool == "RECTANGLE":

            left = min(x1, x2)
            right = max(x1, x2)

            bottom = min(y1, y2)
            top = max(y1, y2)

            p1 = self.world_to_screen(left, top)
            p2 = self.world_to_screen(right, bottom)

            painter.drawRect(
                p1.x(),
                p1.y(),
                p2.x() - p1.x(),
                p2.y() - p1.y()
            )

    # --------------------------------------------------------

    def mousePressEvent(self, event):

        if event.button() == Qt.MiddleButton:
            self.panning = True
            self.last_mouse = event.position()
            return

        if event.button() != Qt.LeftButton:
            return

        x, y = self.screen_to_world(event.position())

        if self.tool == "SELECT":

            obj = self.hit_test(x, y)

            if obj is None:
                self.document.clear_selection()
            else:
                self.document.select(obj.id)

            self.update()
            return

        if self.start_point is None:
            self.start_point = (x, y)
            self.current_point = (x, y)
            self.update()
            return

        x1, y1 = self.start_point

        if self.tool == "LINE":

            self.document.add(
                CADObject(
                    kind="LINE",
                    data={
                        "x1": x1,
                        "y1": y1,
                        "x2": x,
                        "y2": y
                    }
                )
            )

        elif self.tool == "CIRCLE":

            radius = sqrt(
                (x - x1) ** 2 +
                (y - y1) ** 2
            )

            if radius > 0:

                self.document.add(
                    CADObject(
                        kind="CIRCLE",
                        data={
                            "x": x1,
                            "y": y1,
                            "radius": radius
                        }
                    )
                )

        elif self.tool == "RECTANGLE":

            self.document.add(
                CADObject(
                    kind="RECTANGLE",
                    data={
                        "x1": x1,
                        "y1": y1,
                        "x2": x,
                        "y2": y
                    }
                )
            )

        self.start_point = None
        self.current_point = None

        self.update()

    # --------------------------------------------------------

    def mouseMoveEvent(self, event):

        x, y = self.screen_to_world(event.position())

        self.coordinatesChanged.emit(x, y)

        if self.panning and self.last_mouse is not None:

            dx = event.position().x() - self.last_mouse.x()
            dy = event.position().y() - self.last_mouse.y()

            self.pan_x += dx / self.zoom
            self.pan_y -= dy / self.zoom

            self.last_mouse = event.position()

            self.update()

            return

        if self.start_point is not None:

            self.current_point = (x, y)

            self.update()

    # --------------------------------------------------------

    def mouseReleaseEvent(self, event):

        if event.button() == Qt.MiddleButton:
            self.panning = False
            self.last_mouse = None

    # --------------------------------------------------------

    def wheelEvent(self, event):

        if event.angleDelta().y() > 0:
            self.zoom *= 1.15
        else:
            self.zoom /= 1.15

        self.zoom = max(
            0.05,
            min(self.zoom, 100.0)
        )

        self.update()

    # --------------------------------------------------------

    def keyPressEvent(self, event):

        if event.key() == Qt.Key_Escape:
            self.start_point = None
            self.current_point = None
            self.update()
            return

        if event.key() == Qt.Key_Delete:

            if self.document.delete_selected():
                self.update()

            return

        if (
            event.modifiers() & Qt.ControlModifier and
            event.key() == Qt.Key_Z
        ):

            if self.document.undo():
                self.update()

            return

        if (
            event.modifiers() & Qt.ControlModifier and
            event.key() == Qt.Key_Y
        ):

            if self.document.redo():
                self.update()

            return

        super().keyPressEvent(event)

    # --------------------------------------------------------

    def hit_test(self, x, y):

        threshold = 10 / self.zoom

        for obj in reversed(self.document.objects):

            if obj.kind == "LINE":

                x1 = obj.data["x1"]
                y1 = obj.data["y1"]

                x2 = obj.data["x2"]
                y2 = obj.data["y2"]

                dx = x2 - x1
                dy = y2 - y1

                length_sq = dx * dx + dy * dy

                if length_sq == 0:
                    continue

                t = (
                    (x - x1) * dx +
                    (y - y1) * dy
                ) / length_sq

                t = max(0, min(1, t))

                px = x1 + t * dx
                py = y1 + t * dy

                distance = sqrt(
                    (x - px) ** 2 +
                    (y - py) ** 2
                )

                if distance <= threshold:
                    return obj

            elif obj.kind == "CIRCLE":

                distance = sqrt(
                    (x - obj.data["x"]) ** 2 +
                    (y - obj.data["y"]) ** 2
                )

                if abs(
                    distance -
                    obj.data["radius"]
                ) <= threshold:

                    return obj

            elif obj.kind == "RECTANGLE":

                x1 = min(obj.data["x1"], obj.data["x2"])
                x2 = max(obj.data["x1"], obj.data["x2"])

                y1 = min(obj.data["y1"], obj.data["y2"])
                y2 = max(obj.data["y1"], obj.data["y2"])

                if x1 <= x <= x2 and y1 <= y <= y2:
                    return obj

        return None
