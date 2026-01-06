import sys
import cv2
from PyQt5 import QtCore, QtGui, QtWidgets


# ---------- Поток для чтения видео с камеры ----------

class CameraWorker(QtCore.QThread):
    frameReady = QtCore.pyqtSignal(QtGui.QImage)

    def __init__(self, source, parent=None):
        super().__init__(parent)
        self.source = source
        self._running = False

    def run(self):
        cap = cv2.VideoCapture(self.source)
        self._running = cap.isOpened()
        while self._running:
            ret, frame = cap.read()
            if not ret:
                break
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame.shape
            bytes_per_line = ch * w
            qimg = QtGui.QImage(frame.data, w, h, bytes_per_line, QtGui.QImage.Format_RGB888)
            self.frameReady.emit(qimg)
            self.msleep(30)
        cap.release()

    def stop(self):
        self._running = False
        self.wait()


# ---------- Диалог добавления камеры ----------

class AddCameraDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        # убираем системный заголовок
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint | QtCore.Qt.Dialog
        )
        self.setModal(True)
        self.resize(420, 180)

        self._drag_pos = QtCore.QPoint()

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # кастомный title‑bar
        title_bar = QtWidgets.QFrame()
        title_bar.setObjectName("DialogTitleBar")
        tl = QtWidgets.QHBoxLayout(title_bar)
        tl.setContentsMargins(10, 4, 10, 4)
        tl.setSpacing(8)

        title_label = QtWidgets.QLabel("Добавить камеру")
        title_label.setObjectName("DialogTitleLabel")

        btn_close = QtWidgets.QPushButton("×")
        btn_close.setObjectName("DialogTitleButtonClose")
        btn_close.clicked.connect(self.reject)

        tl.addWidget(title_label)
        tl.addStretch()
        tl.addWidget(btn_close)

        # поддержка перетаскивания
        title_bar.mousePressEvent = self.title_bar_mouse_press
        title_bar.mouseMoveEvent = self.title_bar_mouse_move

        main_layout.addWidget(title_bar)

        # содержимое
        content = QtWidgets.QFrame()
        content.setObjectName("DialogContent")
        layout = QtWidgets.QVBoxLayout(content)
        layout.setContentsMargins(16, 12, 16, 16)
        layout.setSpacing(10)

        form = QtWidgets.QFormLayout()
        form.setLabelAlignment(QtCore.Qt.AlignLeft)
        form.setFormAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(8)

        self.name_edit = QtWidgets.QLineEdit()
        self.name_edit.setObjectName("DialogLineEdit")
        self.url_edit = QtWidgets.QLineEdit()
        self.url_edit.setObjectName("DialogLineEdit")
        self.url_edit.setPlaceholderText("rtsp://user:pass@ip:554/stream или 0 для вебкамеры")

        form.addRow("Название:", self.name_edit)
        form.addRow("Источник:", self.url_edit)

        layout.addLayout(form)

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addStretch()

        btn_cancel = QtWidgets.QPushButton("Отмена")
        btn_cancel.setObjectName("DialogSecondaryButton")
        btn_cancel.clicked.connect(self.reject)

        btn_ok = QtWidgets.QPushButton("Добавить")
        btn_ok.setObjectName("DialogPrimaryButton")
        btn_ok.clicked.connect(self.accept)

        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)

        layout.addLayout(btn_row)

        main_layout.addWidget(content)

    def title_bar_mouse_press(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def title_bar_mouse_move(self, event):
        if event.buttons() == QtCore.Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()

    def get_data(self):
        name = self.name_edit.text().strip()
        src_text = self.url_edit.text().strip()
        if src_text == "0":
            src = 0
        else:
            src = src_text
        return name, src


# ---------- Главное окно ----------

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        # убираем системный заголовок и рамку
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint | QtCore.Qt.Window
        )
        self.setWindowTitle("")          # без текста
        self.setWindowIcon(QtGui.QIcon())  # без иконки

        self.resize(1200, 700)
        self.current_worker = None
        self.sources = []
        self._drag_pos = QtCore.QPoint()

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        main_layout = QtWidgets.QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.left_panel = self.create_left_panel()
        main_layout.addWidget(self.left_panel)

        self.right_panel = self.create_right_panel()
        main_layout.addWidget(self.right_panel, 1)

        self.apply_discord_style()

        # начальные камеры
        self.add_camera("Локальная камера", 0)
        # пример RTSP (раскомментируй и подставь свои данные)
        # self.add_camera("RTSP Камера 1", "rtsp://user:pass@192.168.1.10:554/stream1")

    # ----- Кастомный title‑bar -----

    def create_title_bar(self):
        bar = QtWidgets.QFrame()
        bar.setObjectName("TitleBar")
        layout = QtWidgets.QHBoxLayout(bar)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(8)

        title_label = QtWidgets.QLabel("Camera Panel")
        title_label.setObjectName("TitleLabel")

        layout.addWidget(title_label)
        layout.addStretch()

        btn_min = QtWidgets.QPushButton("—")
        btn_min.setObjectName("TitleButton")
        btn_min.clicked.connect(self.showMinimized)

        btn_close = QtWidgets.QPushButton("×")
        btn_close.setObjectName("TitleButtonClose")
        btn_close.clicked.connect(self.close)

        layout.addWidget(btn_min)
        layout.addWidget(btn_close)

        # поддержка перетаскивания
        bar.mousePressEvent = self.title_bar_mouse_press
        bar.mouseMoveEvent = self.title_bar_mouse_move

        return bar

    def title_bar_mouse_press(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def title_bar_mouse_move(self, event):
        if event.buttons() == QtCore.Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()

    # ----- Левая панель -----

    def create_left_panel(self):
        panel = QtWidgets.QFrame()
        panel.setFixedWidth(240)
        layout = QtWidgets.QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        header_layout = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("Камеры")
        title.setObjectName("SidebarTitle")

        btn_add = QtWidgets.QPushButton("+")
        btn_add.setObjectName("IconButton")
        btn_add.setToolTip("Добавить камеру")
        btn_add.clicked.connect(self.show_add_camera_dialog)

        btn_del = QtWidgets.QPushButton("-")
        btn_del.setObjectName("IconButton")
        btn_del.setToolTip("Удалить выбранную камеру")
        btn_del.clicked.connect(self.delete_current_camera)

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(btn_add)
        header_layout.addWidget(btn_del)

        self.camera_list = QtWidgets.QListWidget()
        self.camera_list.setObjectName("CameraList")
        self.camera_list.itemSelectionChanged.connect(self.on_camera_selected)

        layout.addLayout(header_layout)
        layout.addWidget(self.camera_list, 1)

        return panel

    # ----- Правая панель -----

    def create_right_panel(self):
        panel = QtWidgets.QFrame()
        layout = QtWidgets.QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # кастомный title bar
        title_bar = self.create_title_bar()
        layout.addWidget(title_bar)

        content = QtWidgets.QFrame()
        content_layout = QtWidgets.QVBoxLayout(content)
        content_layout.setContentsMargins(12, 12, 12, 12)
        content_layout.setSpacing(8)

        top_bar = QtWidgets.QHBoxLayout()
        self.status_label = QtWidgets.QLabel("Нет выбранной камеры")
        self.status_label.setObjectName("StatusLabel")

        top_bar.addWidget(self.status_label)
        top_bar.addStretch()

        self.btn_start = QtWidgets.QPushButton("▶ Старт")
        self.btn_start.setObjectName("PrimaryButton")
        self.btn_stop = QtWidgets.QPushButton("⏹ Стоп")
        self.btn_stop.setObjectName("SecondaryButton")

        self.btn_start.clicked.connect(self.start_stream)
        self.btn_stop.clicked.connect(self.stop_stream)

        top_bar.addWidget(self.btn_start)
        top_bar.addWidget(self.btn_stop)

        self.video_label = QtWidgets.QLabel()
        self.video_label.setObjectName("VideoLabel")
        self.video_label.setAlignment(QtCore.Qt.AlignCenter)
        self.video_label.setMinimumSize(640, 360)
        self.video_label.setText("Видео не запущено")

        content_layout.addLayout(top_bar)
        content_layout.addWidget(self.video_label, 1)

        layout.addWidget(content)

        return panel

    # ----- Работа со списком камер -----

    def add_camera(self, name, source):
        item = QtWidgets.QListWidgetItem(name)
        self.camera_list.addItem(item)
        self.sources.append(source)

    def show_add_camera_dialog(self):
        dlg = AddCameraDialog(self)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            name, src = dlg.get_data()
            if name and src != "":
                self.add_camera(name, src)

    def delete_current_camera(self):
        row = self.camera_list.currentRow()
        if row < 0:
            return
        name = self.camera_list.item(row).text()
        reply = QtWidgets.QMessageBox.question(
            self,
            "Удаление камеры",
            f"Удалить камеру '{name}'?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if reply == QtWidgets.QMessageBox.Yes:
            self.camera_list.takeItem(row)
            del self.sources[row]
            self.stop_stream()
            self.status_label.setText("Камера удалена")

    # ----- Работа с видео -----

    def on_camera_selected(self):
        row = self.camera_list.currentRow()
        if row < 0:
            return
        name = self.camera_list.currentItem().text()
        self.status_label.setText(f"Выбрана: {name}")

    def start_stream(self):
        row = self.camera_list.currentRow()
        if row < 0:
            return
        source = self.sources[row]

        if self.current_worker is not None:
            self.current_worker.stop()
            self.current_worker = None

        self.current_worker = CameraWorker(source)
        self.current_worker.frameReady.connect(self.update_frame)
        self.current_worker.start()
        self.status_label.setText(f"Поток запущен (камера {row})")

    def stop_stream(self):
        if self.current_worker is not None:
            self.current_worker.stop()
            self.current_worker = None
        self.video_label.setText("Видео остановлено")
        self.video_label.setPixmap(QtGui.QPixmap())
        self.status_label.setText("Поток остановлен")

    def update_frame(self, qimg):
        pix = QtGui.QPixmap.fromImage(qimg)
        self.video_label.setPixmap(pix.scaled(
            self.video_label.size(),
            QtCore.Qt.KeepAspectRatio,
            QtCore.Qt.SmoothTransformation
        ))

    # ----- Стилизация под Discord + анимация кнопок -----

    def apply_discord_style(self):
        self.setStyleSheet("""
        QMainWindow {
            background-color: #202225;
        }
        QFrame {
            background-color: #2f3136;
            color: #dcddde;
        }

        /* ---- основной title bar окна ---- */
        #TitleBar {
            background-color: #202225;
            border-bottom: 1px solid #111214;
        }
        #TitleLabel {
            color: #ffffff;
            font-size: 13px;
            font-weight: 600;
        }
        #TitleButton, #TitleButtonClose {
            background: transparent;
            color: #b9bbbe;
            border-radius: 4px;
            padding: 2px 8px;
        }
        #TitleButton:hover {
            background-color: #3a3c43;
            color: #ffffff;
        }
        #TitleButtonClose:hover {
            background-color: #ed4245;
            color: #ffffff;
        }

        /* ---- диалог: title bar ---- */
        #DialogTitleBar {
            background-color: #202225;
            border-bottom: 1px solid #111214;
        }
        #DialogTitleLabel {
            color: #ffffff;
            font-size: 13px;
            font-weight: 600;
        }
        #DialogTitleButtonClose {
            background: transparent;
            color: #b9bbbe;
            border-radius: 4px;
            padding: 2px 8px;
        }
        #DialogTitleButtonClose:hover {
            background-color: #ed4245;
            color: #ffffff;
        }

        /* ---- диалог: содержимое ---- */
        #DialogContent {
            background-color: #2f3136;
        }
        #DialogLineEdit {
            background-color: #202225;
            border-radius: 4px;
            border: 1px solid #111214;
            padding: 4px 6px;
            color: #dcddde;
            selection-background-color: #5865f2;
        }
        #DialogLineEdit:focus {
            border: 1px solid #5865f2;
        }

        QLabel {
            color: #dcddde;
        }

        /* ---- диалог: кнопки ---- */
        #DialogPrimaryButton {
            background-color: #5865f2;
            border-radius: 4px;
            padding: 6px 14px;
            color: white;
            border: none;
            font-weight: 500;
        }
        #DialogPrimaryButton:hover {
            background-color: #4752c4;
        }
        #DialogPrimaryButton:pressed {
            background-color: #3c45a5;
        }

        #DialogSecondaryButton {
            background-color: #4f545c;
            border-radius: 4px;
            padding: 6px 14px;
            color: #dcddde;
            border: none;
            font-weight: 500;
        }
        #DialogSecondaryButton:hover {
            background-color: #5b6069;
        }
        #DialogSecondaryButton:pressed {
            background-color: #464a52;
        }

        /* ---- остальное, как было ---- */
        #CameraList {
            background-color: #2f3136;
            border: none;
            padding: 4px;
        }
        #CameraList::item {
            padding: 6px 8px;
            border-radius: 4px;
        }
        #CameraList::item:selected {
            background-color: #40444b;
        }
        #SidebarTitle {
            font-size: 16px;
            font-weight: bold;
            color: #ffffff;
            margin-left: 4px;
        }
        #StatusLabel {
            color: #b9bbbe;
        }
        #VideoLabel {
            background-color: #18191c;
            border-radius: 8px;
            border: 1px solid #202225;
            color: #72767d;
        }

        QPushButton {
            background-color: #5865f2;
            border-radius: 6px;
            padding: 6px 14px;
            color: white;
            border: none;
            font-weight: 500;
        }
        QPushButton:hover {
            background-color: #4752c4;
            padding-top: 5px;
            padding-bottom: 7px;
        }
        QPushButton:pressed {
            background-color: #3c45a5;
            padding-top: 7px;
            padding-bottom: 5px;
        }

        #SecondaryButton {
            background-color: #4f545c;
        }
        #SecondaryButton:hover {
            background-color: #5b6069;
        }
        #SecondaryButton:pressed {
            background-color: #464a52;
        }

        #IconButton {
            background-color: #4f545c;
            min-width: 26px;
            max-width: 26px;
            padding: 2px 0;
        }
        #IconButton:hover {
            background-color: #5b6069;
        }
        #IconButton:pressed {
            background-color: #464a52;
        }
        QPushButton:focus {
    outline: none;
}

QPushButton {
    outline: 0;
}

*:focus {
    outline: none;
}
                   
    """)


    def closeEvent(self, event):
        if self.current_worker is not None:
            self.current_worker.stop()
        event.accept()


# ---------- Точка входа ----------

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())
