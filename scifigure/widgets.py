from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel, QTextEdit, QVBoxLayout


class ChatInput(QTextEdit):
    send_requested = pyqtSignal()

    def keyPressEvent(self, event):  # noqa: N802
        if event.key() in {Qt.Key_Return, Qt.Key_Enter} and not (event.modifiers() & Qt.ShiftModifier):
            self.send_requested.emit()
            return
        super().keyPressEvent(event)


class MetricCard(QFrame):
    def __init__(self, name: str, value: str = "--") -> None:
        super().__init__()
        self.setObjectName("Card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        self.value_label = QLabel(value)
        self.value_label.setObjectName("MetricValue")
        self.name_label = QLabel(name)
        self.name_label.setObjectName("MetricName")
        layout.addWidget(self.value_label)
        layout.addWidget(self.name_label)

    def set_value(self, value: str) -> None:
        self.value_label.setText(value)


class ChatBubble(QFrame):
    def __init__(self, who: str, text: str) -> None:
        super().__init__()
        self.setObjectName("Card")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        label = QLabel(f"<b>{who}</b><br>{text}")
        label.setWordWrap(True)
        layout.addWidget(label)
