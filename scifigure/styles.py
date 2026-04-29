APP_QSS = """
QMainWindow {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #EEF4FF, stop:0.42 #F8FBFF, stop:1 #F2F7FE);
}
QWidget {
    color: #172033;
    font-size: 13px;
}
QMenuBar {
    background: rgba(255,255,255,0.82);
    border-bottom: 1px solid #DFE9F5;
    padding: 4px;
}
QMenuBar::item {
    padding: 6px 10px;
    border-radius: 8px;
}
QMenuBar::item:selected {
    background: #EAF1FF;
    color: #1D4ED8;
}
QMenu {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    padding: 6px;
}
QMenu::item {
    padding: 7px 26px 7px 12px;
    border-radius: 8px;
}
QMenu::item:selected {
    background: #DBEAFE;
}
QFrame#SidePanel, QFrame#Inspector, QFrame#Card, QTextEdit, QPlainTextEdit, QTableView, QLabel#MascotCard {
    background: rgba(255,255,255,0.96);
    border: 1px solid #E2E8F0;
    border-radius: 20px;
}
QFrame#SidePanel, QFrame#Inspector {
    border: 1px solid #D8E2F3;
}
QLabel#AppTitle {
    color: #0F172A;
    font-size: 26px;
    font-weight: 900;
    letter-spacing: 0.25px;
}
QLabel#Subtle {
    color: #64748B;
}
QLabel#MetricValue {
    font-size: 20px;
    font-weight: 900;
    color: #2563EB;
}
QLabel#MetricName {
    color: #64748B;
    font-size: 11px;
}
QPushButton {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #2563EB, stop:1 #4F46E5);
    border: none;
    border-radius: 14px;
    color: white;
    padding: 10px 15px;
    font-weight: 800;
}
QPushButton:hover { background: #1D4ED8; }
QPushButton:pressed { background: #1E40AF; }
QPushButton:disabled { background: #CBD5E1; color: #F8FAFC; }
QPushButton#Secondary {
    background: #EAF1FF;
    color: #1E40AF;
    border: 1px solid #CFE0FF;
}
QPushButton#Secondary:hover { background: #DBEAFE; }
QPushButton#Danger {
    background: #FEE2E2;
    color: #B91C1C;
    border: 1px solid #FECACA;
}
QPushButton#Danger:hover { background: #FECACA; }
QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox {
    background: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 11px;
    padding: 7px 10px;
    min-height: 24px;
}
QComboBox:focus, QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 1px solid #2563EB;
}
QTextEdit, QPlainTextEdit {
    padding: 10px;
    selection-background-color: #BFDBFE;
}
QTableView {
    gridline-color: #E2E8F0;
    alternate-background-color: #F8FAFC;
    selection-background-color: #DBEAFE;
    selection-color: #0F172A;
}
QHeaderView::section {
    background: #F1F5F9;
    border: none;
    border-right: 1px solid #E2E8F0;
    border-bottom: 1px solid #E2E8F0;
    padding: 8px;
    font-weight: 800;
}
QTabWidget::pane {
    border: 1px solid #E2E8F0;
    border-radius: 16px;
    background: #FFFFFF;
}
QTabBar::tab {
    background: #E2E8F0;
    color: #334155;
    padding: 9px 18px;
    border-top-left-radius: 12px;
    border-top-right-radius: 12px;
    margin-right: 4px;
}
QTabBar::tab:selected {
    background: #FFFFFF;
    color: #1D4ED8;
    font-weight: 800;
}
QScrollBar:vertical {
    background: transparent;
    width: 10px;
}
QScrollBar::handle:vertical {
    background: #CBD5E1;
    border-radius: 5px;
}
QScrollBar::handle:vertical:hover {
    background: #94A3B8;
}


QToolButton#ChartTypeCard {
    background: #FFFFFF;
    border: 1px solid #D8E4F2;
    border-radius: 16px;
    padding: 10px;
    font-weight: 800;
    color: #172033;
}

QToolButton#ChartTypeCard:hover {
    border: 2px solid #2563EB;
    background: #F8FBFF;
}

QToolButton#ChartTypeCard:checked {
    border: 2px solid #2563EB;
    background: #EEF6FF;
}

"""