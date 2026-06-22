import serial
import serial.tools.list_ports
import time
from PyQt5.QtCore import QThread, pyqtSignal

class SerialWorker(QThread):
    leitura_bruta = pyqtSignal(float)
    erro_conexao = pyqtSignal(str)
    porta_conectada = pyqtSignal(str)
    desconectado = pyqtSignal()
    
    def __init__(self, port='AUTO', baudrate=9600):
        super().__init__()
        self.port_config = port
        self.baudrate = baudrate
        self.running = True
        self.is_connected = False

    def _rastrear_porta(self):
        portas = serial.tools.list_ports.comports()
        palavras_chave = ["arduino", "ch340", "cp210", "ftdi", "usb-serial"]
        for p in portas:
            if any(t in p.description.lower() or t in p.hwid.lower() for t in palavras_chave):
                return p.device
        return portas[0].device if len(portas) == 1 else None

    def run(self):
        ja_avisou_falta_arduino = False

        while self.running:
            porta = self.port_config
            if porta == 'AUTO':
                porta = self._rastrear_porta()

            if not porta:
                if not ja_avisou_falta_arduino:
                    self.erro_conexao.emit("Aguardando conexão com o Arduino via USB...")
                    ja_avisou_falta_arduino = True
                time.sleep(1.5)
                continue

            try:
                with serial.Serial(porta, self.baudrate, timeout=1) as ser:
                    self.is_connected = True
                    ja_avisou_falta_arduino = False
                    self.porta_conectada.emit(porta)
                    ser.reset_input_buffer()

                    while self.running:
                        try:
                            if ser.in_waiting > 0:
                                linha = ser.readline().decode('utf-8', errors='ignore').strip()
                                if linha:
                                    try:
                                        self.leitura_bruta.emit(float(linha))
                                    except ValueError:
                                        pass
                        except OSError:
                            break 
                        except serial.SerialException:
                            break
                        
                        time.sleep(0.01) 
            except Exception:
                pass 
            
            if self.is_connected:
                self.is_connected = False
                ja_avisou_falta_arduino = False 
                
                if self.running:
                    self.desconectado.emit() 
            
            if self.running:
                time.sleep(1.5) 
    def stop(self):
        self.running = False
        self.wait()