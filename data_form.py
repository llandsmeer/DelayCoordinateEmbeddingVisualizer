import sys
import traceback
import signal
import pandas as pd
from PyQt5 import QtCore, QtGui, QtWidgets

class DataFormDialog(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.filename = None
        layout = QtWidgets.QVBoxLayout()
        self.editor = QtWidgets.QPlainTextEdit()
        self.editor.setFont(QtGui.QFont('monospace'))
        self.editor.setPlainText(self.build_code())
        self.view = QtWidgets.QTableWidget()
        self.output = QtWidgets.QPlainTextEdit()
        self.output.setFont(QtGui.QFont('monospace'))
        self.output.setReadOnly(True)
        top = QtWidgets.QVBoxLayout()
        bottom = QtWidgets.QVBoxLayout()
        splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        mid = QtWidgets.QHBoxLayout()
        mid.setAlignment(QtCore.Qt.AlignRight)
        self.status = QtWidgets.QLabel('No data')
        mid.addWidget(self.status)
        run = QtWidgets.QPushButton('Run')
        run.clicked.connect(self.run)
        load = QtWidgets.QPushButton('Open File')
        load.clicked.connect(self.load)
        mid.addWidget(load)
        mid.addWidget(run)
        buttons = QtWidgets.QDialogButtonBox()
        buttons.addButton('OK', QtWidgets.QDialogButtonBox.AcceptRole)
        buttons.addButton('Cancel', QtWidgets.QDialogButtonBox.RejectRole)
        buttons.accepted.connect(self.try_accept)
        buttons.rejected.connect(self.reject)
        top.addWidget(self.editor)
        bottom.addWidget(self.view)
        topw = QtWidgets.QWidget()
        bottomw = QtWidgets.QWidget()
        topw.setLayout(top)
        bottomw.setLayout(bottom)
        splitter.addWidget(topw)
        splitter.addWidget(bottomw)
        splitter.addWidget(self.output)
        layout.addLayout(mid)
        layout.addWidget(splitter)
        layout.addWidget(buttons)
        splitter.setSizes([0, 100, 0])
        self.splitter = splitter
        self.setStyleSheet('QSplitter::handle { background-color: #666 }')
        self.setLayout(layout)
        self.run()
        self.view.itemSelectionChanged.connect(self.selection)
        self.df = False
        self.col = None

    def try_accept(self):
        if self.col is None:
            mbox = QtWidgets.QMessageBox()
            mbox.setText('No data selected')
            mbox.exec()
        else:
            self.accept()

    def build_code(self):
        if self.filename is None:
            return ''
        with open(self.filename) as f:
            header = next(f)
        if '\t' in header:
            sep = '\\t'
        elif ',' in header:
            sep = ','
        else:
            return f'df = pd.read_csv("{self.filename}")'
        return f'df = pd.read_csv("{self.filename}", sep="{sep}")'

    def selection(self):
        self.col = None
        if self.df is None:
            return
        sel = self.view.selectedIndexes()
        if not sel:
            return
        cols = set(idx.column() for idx in sel)
        if len(cols) > 1 or len(sel) != len(self.df):
            col = sel[0].column()
            self.view.selectColumn(col)
        col = sel[0].column()
        self.col = self.df.iloc[:, col]


    def load(self):
        filename = QtWidgets.QFileDialog.getOpenFileName(self,
                                                         'Open Data File',
                                                         'Data (*.csv, *.tsv, *.txt);;All Files (*)')[0]
        self.setfile(filename)

    def setfile(self, filename):
        self.filename = filename
        self.editor.setPlainText(self.build_code())
        self.run()

    def run(self):
        self.splitter.setSizes([0, 100, 0])
        self.output.setPlainText('')
        code = self.editor.toPlainText()
        obj = compile(code, '<dialog>', 'exec')
        env = {'pd': pd}
        try:
            exec(obj, env)
        except Exception as ex:
            #text = '\n'.join(traceback.format_exception(ex))
            self.splitter.setSizes([0, 0, 100])
            text = traceback.format_exc()
            self.output.setPlainText(text)
            self.load_df(None)
        df = env.get('df')
        self.df = df
        self.load_df(df)

    def load_df(self, df):
        self.col = None
        if df is None:
            self.view.setRowCount(0)
            self.view.setColumnCount(0)
            self.status.setText('No data')
            return
        head = df.head(200)
        rows, cols = head.shape
        self.view.setRowCount(rows)
        self.view.setColumnCount(cols)
        for idx, row in head.iterrows():
            for jdx, cell in enumerate(row):
                item = QtWidgets.QTableWidgetItem(str(cell))
                self.view.setItem(idx, jdx, item)
        self.view.setHorizontalHeaderLabels([str(name) for name in head.columns])
        self.view.setVerticalHeaderLabels([str(name) for name in head.index])
        self.status.setText(f'{len(df)} rows')


def main():
    app = QtWidgets.QApplication(sys.argv)
    signal.signal(signal.SIGINT, lambda *a: app.quit())
    timer = QtCore.QTimer()
    timer.start(200)
    timer.timeout.connect(lambda: 'run interpreter to allow ctrl-c exit')
    window = Window()
    window.resize(800, 600)
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
