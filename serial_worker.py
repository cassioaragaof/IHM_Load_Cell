# serial_worker.py
import serial
import serial.tools.list_ports
from PyQt5.QtCore import QThread, pyqtSignal

class SerialWorker(QThread):
    leitura_bruta = pyqtSignal(float)
    erro_conexao = pyqtSignal(str)
    porta_conectada = pyqtSignal(str)

    def __init__(self, port='AUTO', baudrate=9600):
        super().__init__()
        self.port_config = port
        self.baudrate = baudrate
        self.running = True

    def _rastrear_porta(self):
        portas = serial.tools.list_ports.comports()
        palavras_chave = ["arduino", "ch340", "cp210", "ftdi", "usb-serial"]
        for p in portas:
            if any(t in p.description.lower() or t in p.hwid.lower() for t in palavras_chave):
                return p.device
        return portas[0].device if len(portas) == 1 else None

    def run(self):
        porta = self.port_config
        if porta == 'AUTO':
            porta = self._rastrear_porta()
            if not porta:
                self.erro_conexao.emit("Arduino não detetado. Verifique a ligação USB.")
                return
        
        self.porta_conectada.emit(porta)

        try:
            with serial.Serial(porta, self.baudrate, timeout=1) as ser:
                ser.reset_input_buffer()
                while self.running:
                    if ser.in_waiting > 0:
                        linha = ser.readline().decode('utf-8', errors='ignore').strip()
                        if linha:
                            try:
                                self.leitura_bruta.emit(float(linha))
                            except ValueError:
                                pass
        except Exception as e:
            self.erro_conexao.emit(str(e))

    def stop(self):
        self.running = False
        self.wait()