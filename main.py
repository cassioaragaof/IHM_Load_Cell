import sys
import numpy as np
import pandas as pd
from PyQt5.QtWidgets import QApplication, QMessageBox, QFileDialog
from PyQt5.QtCore import QTimer
from ui_interface import VisualMainWindow
from serial_worker import SerialWorker
import pyqtgraph as pg

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

        self.tamanho_grafico = 100
        self.historico_peso = [0.0] * self.tamanho_grafico

        self.cronometro_timer = QTimer()
        self.cronometro_timer.setInterval(50) 
        self.cronometro_timer.timeout.connect(self.atualizar_cronometro)

        self.view.gauge_timer.atualizar_tempo(TEMPO_ENSAIO_SEGUNDOS, TEMPO_ENSAIO_SEGUNDOS, False, False)

        self.hardware = SerialWorker(port='AUTO', baudrate=9600)
        self.hardware.leitura_bruta.connect(self.receber_fluxo_dados)
        
        # Sinais de Hardware atualizados
        self.hardware.erro_conexao.connect(self.exibir_status_pesquisa)
        self.hardware.porta_conectada.connect(self.ao_conectar_porta)
        self.hardware.desconectado.connect(self.ao_desconectar)
        
        self.view.btn_tara.clicked.connect(self.aplicar_tara)
        self.view.btn_iniciar_ensaio.clicked.connect(self.iniciar_ensaio_estabilizacao)
        self.view.btn_salvar_csv.clicked.connect(self.salvar_relatorio_csv)
        self.view.btn_aplicar_config.clicked.connect(self.salvar_configuracoes)
        self.view.closeEvent = self.ao_fechar
        self.view.grafico_peso.setYRange(-1, self.capacidade_celula * 1.1)
        
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
        
        limite_superior = self.capacidade_celula * 1.1
        self.view.grafico_peso.setYRange(-1, limite_superior)
        
        self.historico_peso = [0.0] * self.tamanho_grafico
        self.view.linha_grafico.setData(self.historico_peso)
        
        self.receber_fluxo_dados(self.ultimo_valor_bruto)
        
        self.exibir_popup(
            "Configurações", 
            "Parâmetros aplicados com sucesso!", 
            f"A capacidade foi ajustada para {self.capacidade_celula} kg.\nO gráfico e os alarmes de sobrecarga foram reconfigurados dinamicamente e a Tara foi zerada.", 
            "info"
        )
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

        porcentagem = (peso_real / self.capacidade_celula) * 100
        esta_em_sobrecarga = porcentagem > 100.0
        porcentagem_visual = max(0, min(100, porcentagem)) 
        
        if esta_em_sobrecarga:
            texto_peso = f"⚠️ {peso_real:.2f} kg" 
        else:
            texto_peso = f"{peso_real:.2f} kg"
        
        self.view.atualizar_valores_fatais(texto_peso, porcentagem_visual, esta_em_sobrecarga)

        self.historico_peso.pop(0) 
        self.historico_peso.append(peso_real) 
        self.view.linha_grafico.setData(self.historico_peso) 

        if esta_em_sobrecarga:
            self.view.linha_grafico.setPen(pg.mkPen(color='#FF5252', width=3))
        else:
            self.view.linha_grafico.setPen(pg.mkPen(color='#00E676', width=2))

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
        
        self.view.gauge_timer.atualizar_tempo(self.tempo_restante, TEMPO_ENSAIO_SEGUNDOS, ativo=True)
        self.cronometro_timer.start()

    def atualizar_cronometro(self):
        self.tempo_restante -= 0.05 
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
                self.exibir_popup(
                    "Exportação", 
                    "Relatório guardado com sucesso!", 
                    f"O ficheiro foi salvo em:\n{caminho_arquivo}", 
                    "info"
                )
            except Exception as e:
                self.exibir_popup(
                    "Erro", 
                    "Falha ao guardar o relatório", 
                    f"Verifique se o ficheiro não está aberto noutro programa.\nDetalhes técnicos: {str(e)}", 
                    "erro"
                )

    def ao_conectar_porta(self, porta):
        self.view.setWindowTitle(f"IHM Instrumentação Estatística [{porta}]")
        self.view.lbl_stat_status.setText(f"Status do Sistema: Conectado à porta {porta} (Modo Contínuo)")
        self.view.lbl_stat_status.setStyleSheet("color: #00E676;")
        
    def exibir_status_pesquisa(self, mensagem):
        self.view.lbl_stat_status.setText(f"Status do Sistema: {mensagem}")
        self.view.lbl_stat_status.setStyleSheet("color: #FF9800;") 

    def ao_desconectar(self):
        self.view.setWindowTitle("IHM Instrumentação Estatística [Desconectado]")
        self.view.lbl_stat_status.setText("Status do Sistema: Arduino Desconectado / Mau Contato")
        self.view.lbl_stat_status.setStyleSheet("color: #FF5252;")
        
        if self.em_ensaio:
            self.cronometro_timer.stop()
            self.em_ensaio = False
            self.tempo_restante = 0.0
            
            self.view.btn_iniciar_ensaio.setEnabled(True)
            self.view.btn_tara.setEnabled(True)
            self.view.tabs.setTabEnabled(1, True)
            
            self.view.label_cronometro.setStyleSheet("color: #FF5252; font-weight: bold;")
            self.view.label_cronometro.setText("⚠️ ENSAIO INTERROMPIDO: Conexão perdida!")
            self.view.gauge_timer.atualizar_tempo(5.0, 5.0, ativo=False, concluido=False)
            
        QMessageBox.critical(self.view, "Alerta de Hardware", 
                             "⚠️ Mau contato no USB ou Arduino desconectado subitamente!\n\n"
                             "Por favor, verifique o cabo e reconecte. O sistema tentará voltar automaticamente...")


    def ao_fechar(self, event):
        self.cronometro_timer.stop()
        self.hardware.stop()
        event.accept()
        
    def exibir_popup(self, titulo_janela, titulo_interno, detalhes, tipo="info"):
        msg = QMessageBox(self.view)
        msg.setWindowTitle(titulo_janela)
        msg.setText(f"<h3>{titulo_interno}</h3>")
        msg.setInformativeText(detalhes)
        
        if tipo == "erro":
            msg.setIcon(QMessageBox.Critical)
        elif tipo == "aviso":
            msg.setIcon(QMessageBox.Warning)
        else:
            msg.setIcon(QMessageBox.Information)
            
        msg.exec_()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    controller = IhmController()
    sys.exit(app.exec_())