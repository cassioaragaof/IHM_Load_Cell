# ======================================================================
# Projeto: IHM para Célula de Carga
# ======================================================================
import sys
import numpy as np
import pandas as pd
from PyQt5.QtWidgets import QApplication, QMessageBox, QFileDialog
from PyQt5.QtCore import QTimer
from ui_interface import VisualMainWindow
from serial_worker import SerialWorker

TEMPO_ENSAIO_SEGUNDOS = 5.0  

class IhmController:
    def __init__(self):
        self.view = VisualMainWindow()
        
        self.modo_leitura = "CASO_2" 
        self.capacidade_celula = 20.0
        self.sensibilidade_mv_v = 1.0
        self.tensao_excitacao = 5.0
        
        self.tara = 0.0
        self.ultimo_valor_bruto = 0.0
        self.em_ensaio = False
        self.tempo_restante = 0
        self.amostras_ensaio = []
        self.dados_exportacao = None

        self.cronometro_timer = QTimer()
        self.cronometro_timer.setInterval(50) 
        self.cronometro_timer.timeout.connect(self.atualizar_cronometro)

        # Configuração do Relógio
        self.view.gauge_timer.atualizar_tempo(TEMPO_ENSAIO_SEGUNDOS, TEMPO_ENSAIO_SEGUNDOS, False, False)

        self.hardware = SerialWorker(port='AUTO', baudrate=9600)
        self.hardware.leitura_bruta.connect(self.receber_fluxo_dados)
        self.hardware.erro_conexao.connect(self.exibir_erro)
        self.hardware.porta_conectada.connect(self.ao_conectar_porta)
        
        self.view.btn_tara.clicked.connect(self.aplicar_tara)
        self.view.btn_iniciar_ensaio.clicked.connect(self.iniciar_ensaio_estabilizacao)
        self.view.btn_salvar_csv.clicked.connect(self.salvar_relatorio_csv)
        self.view.btn_aplicar_config.clicked.connect(self.salvar_configuracoes)
        self.view.closeEvent = self.ao_fechar

        self.hardware.start()
        self.view.show()

    def salvar_configuracoes(self):
        if self.view.radio_caso1.isChecked():
            self.modo_leitura = "CASO_1"
        else:
            self.modo_leitura = "CASO_2"
            
        self.capacidade_celula = self.view.spin_capacidade.value()
        self.sensibilidade_mv_v = self.view.spin_sensibilidade.value()
        self.tensao_excitacao = self.view.spin_excitacao.value()
        
        self.tara = 0.0
        QMessageBox.information(self.view, "Sucesso", "Configurações da Célula aplicadas com sucesso!\nA Tara foi reiniciada.")
        self.view.tabs.setCurrentIndex(0)

    def calcular_peso_real(self, valor_bruto):
        if self.modo_leitura == "CASO_2":
            return valor_bruto
        elif self.modo_leitura == "CASO_1":
            max_tensao_saida_mv = self.sensibilidade_mv_v * self.tensao_excitacao
            if max_tensao_saida_mv == 0: return 0.0
            return (valor_bruto / max_tensao_saida_mv) * self.capacidade_celula

    def receber_fluxo_dados(self, valor_bruto):
        self.ultimo_valor_bruto = valor_bruto
        peso_base = self.calcular_peso_real(valor_bruto)
        peso_real = peso_base - self.tara

        if self.em_ensaio:
            self.amostras_ensaio.append(peso_real)

        # 1. Calcula a porcentagem real da carga aplicada
        porcentagem = (peso_real / self.capacidade_celula) * 100
        
        # 2. Avalia se está em sobrecarga (acima de 100%)
        esta_em_sobrecarga = porcentagem > 100.0
        
        # 3. Limita a barra visualmente a 100% para não quebrar a UI
        porcentagem_visual = max(0, min(100, porcentagem)) 
        
        # 4. Formata o texto final
        if esta_em_sobrecarga:
            texto_peso = f"⚠️ {peso_real:.2f} kg"
        else:
            texto_peso = f"{peso_real:.2f} kg"
        
        # 5. Envia os dados para a interface, passando a flag de sobrecarga
        self.view.atualizar_valores_fatais(texto_peso, porcentagem_visual, esta_em_sobrecarga)

    def aplicar_tara(self):
        self.tara = self.calcular_peso_real(self.ultimo_valor_bruto)

    def iniciar_ensaio_estabilizacao(self):
        self.em_ensaio = True
        self.amostras_ensaio = [] 
        self.tempo_restante = TEMPO_ENSAIO_SEGUNDOS
        
        self.view.btn_iniciar_ensaio.setEnabled(False)
        self.view.btn_tara.setEnabled(False)
        self.view.btn_salvar_csv.setEnabled(False)
        self.view.tabs.setTabEnabled(1, False) 
        
        self.view.label_cronometro.setStyleSheet("color: #FF9800;")
        self.view.label_cronometro.setText("MANTENHA A CARGA ESTÁVEL! Capturando dados...")
        
        # Inicia a Animação do Gauge (Ativo)
        self.view.gauge_timer.atualizar_tempo(self.tempo_restante, TEMPO_ENSAIO_SEGUNDOS, ativo=True)
        
        self.cronometro_timer.start()

    def atualizar_cronometro(self):
        # Decrementa alinhado aos 50ms do QTimer
        self.tempo_restante -= 0.05 
        
        # Atualiza o visual do relógio
        self.view.gauge_timer.atualizar_tempo(self.tempo_restante, TEMPO_ENSAIO_SEGUNDOS, ativo=True)

        if self.tempo_restante <= 0:
            self.finalizar_ensaio_estatistico()

    def finalizar_ensaio_estatistico(self):
        self.cronometro_timer.stop()
        self.em_ensaio = False
        self.tempo_restante = 0.0
        
        self.view.btn_iniciar_ensaio.setEnabled(True)
        self.view.btn_tara.setEnabled(True)
        self.view.tabs.setTabEnabled(1, True)
        
        self.view.label_cronometro.setStyleSheet("color: #00E676; font-weight: bold;")
        self.view.label_cronometro.setText("✓ Medição Concluída com Sucesso!")

        # Animação do Gauge (Concluído: Verde)
        self.view.gauge_timer.atualizar_tempo(self.tempo_restante, TEMPO_ENSAIO_SEGUNDOS, ativo=False, concluido=True)

        if len(self.amostras_ensaio) > 1:
            serie_dados = pd.Series(self.amostras_ensaio)
            total_amostras = len(serie_dados)
            media = serie_dados.mean()                     
            variancia = serie_dados.var(ddof=1)            
            dispersao = np.max(self.amostras_ensaio) - np.min(self.amostras_ensaio)

            self.view.atualizar_relatorio_estatistico(total_amostras, media, variancia, dispersao)
            
            self.dados_exportacao = pd.DataFrame({
                "Amostra": range(1, total_amostras + 1),
                "Peso_Lido_kg": self.amostras_ensaio,
                "Media_do_Ensaio_kg": media,
                "Variancia_do_Ensaio": variancia,
                "Dispersao_Amplitude_kg": dispersao,
                "Modo_Aquisicao": self.modo_leitura
            })
            
            self.view.btn_salvar_csv.setEnabled(True)
        else:
            self.view.lbl_stat_status.setText("Erro: Nenhuma amostra capturada.")

    def salvar_relatorio_csv(self):
        if self.dados_exportacao is None or self.dados_exportacao.empty:
            return

        opcoes = QFileDialog.Options()
        caminho_arquivo, _ = QFileDialog.getSaveFileName(
            self.view, "Guardar Relatório CSV", "relatorio_ensaio.csv", 
            "Ficheiros CSV (*.csv);;Todos os Ficheiros (*)", options=opcoes
        )
        
        if caminho_arquivo:
            try:
                self.dados_exportacao.to_csv(caminho_arquivo, index=False, sep=';', decimal=',')
                QMessageBox.information(self.view, "Sucesso", f"Relatório guardado com sucesso!")
            except Exception as e:
                QMessageBox.critical(self.view, "Erro", f"Não foi possível guardar o ficheiro:\n{str(e)}")

    def ao_conectar_porta(self, porta):
        self.view.setWindowTitle(f"IHM Instrumentação Estatística [{porta}]")
        self.view.lbl_stat_status.setText(f"Status do Sistema: Conectado à porta {porta} (Modo Contínuo)")
        self.view.lbl_stat_status.setStyleSheet("color: #00E676;")

    def exibir_erro(self, mensagem):
        self.view.lbl_stat_status.setText("Status do Sistema: Erro na Conexão")
        self.view.lbl_stat_status.setStyleSheet("color: #FF5252;")
        QMessageBox.critical(self.view, "Falha de Hardware", mensagem)

    def ao_fechar(self, event):
        self.cronometro_timer.stop()
        self.hardware.stop()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    controller = IhmController()
    sys.exit(app.exec_())