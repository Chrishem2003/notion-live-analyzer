from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from sovereign_cad.desktop.document import CADDocument
from sovereign_cad.desktop.cad_view import CADView


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("SovereignCAD")

        self.resize(1400, 900)

        self.document = CADDocument()

        self.view = CADView(self.document)

        self.setCentralWidget(self.view)

        self.create_toolbar()
        self.create_command_bar()

        self.coordinates = QLabel(
            "X: 0.00   Y: 0.00"
        )

        self.statusBar().addPermanentWidget(
            self.coordinates
        )

        self.view.coordinatesChanged.connect(
            self.update_coordinates
        )

    def create_toolbar(self):

        toolbar = QToolBar("CAD Tools")

        toolbar.setMovable(False)

        self.addToolBar(toolbar)

        tools = [
            ("Select", "SELECT"),
            ("Line", "LINE"),
            ("Circle", "CIRCLE"),
            ("Rectangle", "RECTANGLE"),
        ]

        for label, command in tools:

            button = QPushButton(label)

            button.clicked.connect(
                lambda checked=False, cmd=command:
                self.activate_tool(cmd)
            )

            toolbar.addWidget(button)

        toolbar.addSeparator()

        undo_button = QPushButton("Undo")

        undo_button.clicked.connect(
            self.undo
        )

        toolbar.addWidget(undo_button)

        redo_button = QPushButton("Redo")

        redo_button.clicked.connect(
            self.redo
        )

        toolbar.addWidget(redo_button)

    def create_command_bar(self):

        container = QWidget()

        layout = QVBoxLayout(container)

        self.command_input = QLineEdit()

        self.command_input.setPlaceholderText(
            "Command: LINE, CIRCLE, RECTANGLE, SELECT, UNDO..."
        )

        self.command_input.returnPressed.connect(
            self.execute_command
        )

        layout.addWidget(
            self.command_input
        )

        self.setMenuWidget(container)

    def activate_tool(self, tool):

        self.view.set_tool(tool)

        self.view.setFocus()

    def execute_command(self):

        command = (
            self.command_input.text()
            .strip()
            .upper()
        )

        self.command_input.clear()

        aliases = {
            "L": "LINE",
            "C": "CIRCLE",
            "REC": "RECTANGLE",
            "S": "SELECT",
            "U": "UNDO",
        }

        command = aliases.get(
            command,
            command
        )

        if command in [
            "LINE",
            "CIRCLE",
            "RECTANGLE",
            "SELECT"
        ]:

            self.activate_tool(command)
            return

        if command == "UNDO":
            self.undo()
            return

        if command == "REDO":
            self.redo()
            return

        if command == "DELETE":

            if self.document.delete_selected():
                self.view.update()

    def undo(self):

        if self.document.undo():
            self.view.update()

    def redo(self):

        if self.document.redo():
            self.view.update()

    def update_coordinates(self, x, y):

        self.coordinates.setText(
            f"X: {x:.2f}   Y: {y:.2f}"
        )
