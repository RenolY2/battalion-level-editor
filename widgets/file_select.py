from PyQt5.Qt import QDialog, QWidget, QVBoxLayout, QListWidget


class FileSelect(QDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        self.listbox = QListWidget(self)
        layout.addWidget(self.listbox)

        self.listbox.doubleClicked.connect(self.set_selected)

        self.listbox.doubleClicked.connect(self.set_selected)

        self.selected = None

    def set_file_list(self, filelist):
        self.listbox.clear()

        for file in filelist:
            self.listbox.addItem(file)

    def set_selected(self, item):
        self.selected = self.listbox.currentItem().text()
        self.close()

    @staticmethod
    def open_file_list(parent, filelist, title, startat=0):
        dialog = FileSelect(parent)
        dialog.setWindowTitle(title)
        dialog.set_file_list(filelist)
        dialog.listbox.setCurrentRow(startat)

        dialog.exec()

        result = dialog.selected
        pos = dialog.listbox.currentRow()
        dialog.deleteLater()
        return result, pos