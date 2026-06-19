import sys
from PyQt5.QtWidgets import (QMainWindow, QLabel, QVBoxLayout, QHBoxLayout, 
                             QWidget, QPushButton, QProgressBar, QGroupBox,
                             QTabWidget, QRadioButton, QDoubleSpinBox, QFormLayout)
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QFont, QPainter, QPen, QColor

class GaugeRelogio(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(130, 130)
        self.max_value = 5.0
        self.current_value = 5.0
        self.is_active = False
        self.is_finished = False

    def atualizar_tempo(self, atual, maximo, ativo, concluido=False):
        self.current_value = atual
        self.max_value = maximo
        self.is_active = ativo
        self.is_finished = concluido
        self.update() 

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing) 
        tamanho = min(self.width(), self.height())
        rect = QRectF((self.width() - tamanho) / 2 + 10, 
                      (self.height() - tamanho) / 2 + 10, 
                      tamanho - 20, tamanho - 20)
        
        pen_fundo = QPen(QColor("#2b2b2b"), 10)
        painter.setPen(pen_fundo)
        painter.drawArc(rect, 0, 360 * 16)

        if self.is_active:
            pen_progresso = QPen(QColor("#FF9800"), 10) 
        elif self.is_finished:
            pen_progresso = QPen(QColor("#00E676"), 10) 
        else:
            pen_progresso = QPen(QColor("#555555"), 10) 
            
        pen_progresso.setCapStyle(Qt.RoundCap) 
        painter.setPen(pen_progresso)

        ratio = self.current_value / self.max_value if self.max_value > 0 else 0
        angulo_preenchimento = int(-360 * ratio * 16) 
        painter.drawArc(rect, 90 * 16, angulo_preenchimento)

        painter.setPen(QColor("#FFFFFF"))
        painter.setFont(QFont("Segoe UI", 22, QFont.Bold))
        texto = f"{abs(self.current_value):.1f}s"
        painter.drawText(rect, Qt.AlignCenter, texto)


class VisualMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IHM - Instrumentação Estatística Avançada")
        self.resize(680, 780)
        self._aplicar_estilos()
        self._init_ui()

    def _aplicar_estilos(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #121212; }
            QLabel { color: #ffffff; font-family: 'Segoe UI', Arial; font-size: 16px; }
            QGroupBox { border: 1px solid #333333; border-radius: 6px; margin-top: 15px; color: #b3b3b3; font-weight: bold; font-size: 16px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
            QPushButton { background-color: #2196F3; color: white; border-radius: 4px; padding: 12px; font-size: 18px; font-weight: bold; }
            QPushButton:hover { background-color: #1E88E5; }
            QPushButton:disabled { background-color: #444444; color: #888888; }
            QProgressBar { border: 1px solid #333; border-radius: 4px; text-align: center; color: white; font-weight: bold; font-size: 16px; background-color: #1e1e1e; }
            QProgressBar::chunk { background-color: #00E676; }
            QTabWidget::pane { border: 1px solid #333; border-radius: 4px; }
            QTabBar::tab { background: #252525; color: #ffffff; padding: 0px 10px; border: 1px solid #333; font-weight: bold; font-size: 18px; min-width: 280px; min-height: 45px; }
            QTabBar::tab:selected { background: #2196F3; color: white; border-bottom-color: #2196F3; }
            QRadioButton { color: white; font-size: 18px; spacing: 10px; }
            QDoubleSpinBox { background-color: #222; color: white; border: 1px solid #555; padding: 8px; font-size: 18px; }
        """)

    def _init_ui(self):
        self.tabs = QTabWidget()
        self.aba_medicao = QWidget()
        self.aba_config = QWidget()
        self.tabs.addTab(self.aba_medicao, "Medição")
        self.tabs.addTab(self.aba_config, "Configurações")
        self.setCentralWidget(self.tabs)
        self._construir_aba_medicao()
        self._construir_aba_config()

    def _construir_aba_medicao(self):
        layout_principal = QVBoxLayout()

        self.label_peso = QLabel("0.00 kg")
        self.label_peso.setAlignment(Qt.AlignCenter)
        self.label_peso.setStyleSheet("color: #00E676; margin: 10px 0; font-size: 75px; font-weight: bold;")
        layout_principal.addWidget(self.label_peso)

        self.barra_carga = QProgressBar()
        self.barra_carga.setFixedHeight(30)
        layout_principal.addWidget(self.barra_carga)

        grupo_ensaio = QGroupBox("Controlo de Ensaio (Estabilização)")
        layout_ensaio = QVBoxLayout()
        layout_botoes = QHBoxLayout()
        self.btn_iniciar_ensaio = QPushButton("INICIAR MEDIÇÃO")
        self.btn_tara = QPushButton("TARA")
        self.btn_tara.setStyleSheet("background-color: #555555;")
        layout_botoes.addWidget(self.btn_tara)
        layout_botoes.addWidget(self.btn_iniciar_ensaio)
        layout_ensaio.addLayout(layout_botoes)

        layout_relogio = QHBoxLayout()
        self.gauge_timer = GaugeRelogio()
        layout_relogio.addWidget(self.gauge_timer, alignment=Qt.AlignCenter)
        layout_ensaio.addLayout(layout_relogio)

        self.label_cronometro = QLabel("Aguardando comando de inicialização...")
        self.label_cronometro.setFont(QFont("Segoe UI", 16))
        self.label_cronometro.setAlignment(Qt.AlignCenter)
        self.label_cronometro.setStyleSheet("color: #aaaaaa;")
        layout_ensaio.addWidget(self.label_cronometro)
        
        grupo_ensaio.setLayout(layout_ensaio)
        layout_principal.addWidget(grupo_ensaio)

        grupo_stats = QGroupBox("Relatório de Instrumentação")
        layout_stats = QVBoxLayout()
        layout_stats.setSpacing(10)

        self.lbl_stat_amostras = QLabel("Nº de Amostras Coletadas: -")
        self.lbl_stat_media = QLabel("Média Calculada (μ): -")
        self.lbl_stat_variancia = QLabel("Variância Amostral (σ²): -")
        self.lbl_stat_dispersao = QLabel("Dispersão / Amplitude (Máx - Mín): -")
        self.lbl_stat_status = QLabel("Status: Desconectado")
        self.lbl_stat_status.setStyleSheet("color: #888888; font-style: italic;")

        for lbl in [self.lbl_stat_amostras, self.lbl_stat_media, self.lbl_stat_variancia, self.lbl_stat_dispersao, self.lbl_stat_status]:
            lbl.setFont(QFont("Segoe UI", 16))
            layout_stats.addWidget(lbl)

        self.btn_salvar_csv = QPushButton("💾 EXPORTAR RELATÓRIO (.CSV)")
        self.btn_salvar_csv.setStyleSheet("background-color: #4CAF50; margin-top: 5px;")
        self.btn_salvar_csv.setEnabled(False)
        layout_stats.addWidget(self.btn_salvar_csv)

        grupo_stats.setLayout(layout_stats)
        layout_principal.addWidget(grupo_stats)
        self.aba_medicao.setLayout(layout_principal)

    def _construir_aba_config(self):
        layout_config = QVBoxLayout()
        layout_config.setSpacing(25)
        layout_config.setAlignment(Qt.AlignTop)

        grupo_modo = QGroupBox("1. Seleção do Modo de Aquisição")
        layout_modo = QVBoxLayout()
        layout_modo.setSpacing(10)
        self.radio_caso2 = QRadioButton("Caso 2: Receber Direto em Kg (Cálculo feito no Arduino)")
        self.radio_caso1 = QRadioButton("Caso 1: Receber Tensão em mV (Cálculo feito pelo PC)")
        self.radio_caso2.setChecked(True)
        layout_modo.addWidget(self.radio_caso2)
        layout_modo.addWidget(self.radio_caso1)
        grupo_modo.setLayout(layout_modo)
        layout_config.addWidget(grupo_modo)

        self.grupo_params = QGroupBox("2. Parâmetros da Célula (Apenas para o Caso 1)")
        layout_form = QFormLayout()
        layout_form.setSpacing(12)
        
        self.spin_capacidade = QDoubleSpinBox()
        self.spin_capacidade.setRange(0.1, 50000.0)
        self.spin_capacidade.setValue(20.0)
        self.spin_capacidade.setSuffix(" kg")

        self.spin_sensibilidade = QDoubleSpinBox()
        self.spin_sensibilidade.setRange(0.01, 10.0)
        self.spin_sensibilidade.setValue(1.0)
        self.spin_sensibilidade.setSuffix(" mV/V")
        self.spin_sensibilidade.setSingleStep(0.1)

        self.spin_excitacao = QDoubleSpinBox()
        self.spin_excitacao.setRange(1.0, 24.0)
        self.spin_excitacao.setValue(5.0)
        self.spin_excitacao.setSuffix(" V")

        layout_form.addRow(QLabel("Capacidade Máxima da Célula:"), self.spin_capacidade)
        layout_form.addRow(QLabel("Sensibilidade (mV/V):"), self.spin_sensibilidade)
        layout_form.addRow(QLabel("Tensão de Excitação do Módulo:"), self.spin_excitacao)
        
        self.grupo_params.setLayout(layout_form)
        self.grupo_params.setEnabled(False)
        layout_config.addWidget(self.grupo_params)

        self.btn_aplicar_config = QPushButton("APLICAR CONFIGURAÇÕES")
        layout_config.addWidget(self.btn_aplicar_config)

        self.aba_config.setLayout(layout_config)
        self.radio_caso1.toggled.connect(self._alternar_painel_params)

    def _alternar_painel_params(self):
        self.grupo_params.setEnabled(self.radio_caso1.isChecked())

    def atualizar_valores_fatais(self, peso, porcentagem, sobrecarga=False):
        self.label_peso.setText(peso)
        self.barra_carga.setValue(int(porcentagem))
        
        if sobrecarga:
            self.label_peso.setStyleSheet("color: #FF5252; margin: 10px 0; font-size: 75px; font-weight: bold;")
            self.barra_carga.setStyleSheet("""
                QProgressBar { border: 1px solid #FF5252; border-radius: 4px; text-align: center; color: white; font-weight: bold; font-size: 16px; background-color: #330000; }
                QProgressBar::chunk { background-color: #FF5252; }
            """)
        else:
            self.label_peso.setStyleSheet("color: #00E676; margin: 10px 0; font-size: 75px; font-weight: bold;")
            self.barra_carga.setStyleSheet("""
                QProgressBar { border: 1px solid #333; border-radius: 4px; text-align: center; color: white; font-weight: bold; font-size: 16px; background-color: #1e1e1e; }
                QProgressBar::chunk { background-color: #00E676; }
            """)