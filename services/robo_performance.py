
import os
import time
import traceback
from datetime import datetime
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

from config.settings import (
    SIANNET_USER,
    SIANNET_PASSWORD,
    PASTA_PERFORMANCE,
    PERFIL_CHROME,
    DATA_INICIO,
    DATA_FIM
)


class RoboPerformance:

    def __init__(self):
        self.pasta_download = str(PASTA_PERFORMANCE)
        Path(self.pasta_download).mkdir(parents=True, exist_ok=True)

        self.driver = None

        self.options = Options()
        self.options.add_argument("--start-maximized")
        self.options.add_argument(f"--user-data-dir={PERFIL_CHROME}")

        preferencias = {
            "download.default_directory": self.pasta_download,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }

        self.options.add_experimental_option("prefs", preferencias)

        self.service = Service(ChromeDriverManager().install())

        self.driver = webdriver.Chrome(
            service=self.service,
            options=self.options
        )

        self.wait = WebDriverWait(self.driver, 60)

    # --------------------------------------------------
    # LOGIN
    # --------------------------------------------------

    def login_siannet(self):
        print("\n[1/5] Acessando Siannet...")

        if not SIANNET_USER or not SIANNET_PASSWORD:
            raise ValueError(
                "Credenciais do Siannet não configuradas no .env"
            )

        self.driver.get("https://siannet.gestaosian.com/")

        self.wait.until(
            EC.element_to_be_clickable((By.ID, "nlogin"))
        ).send_keys(SIANNET_USER)

        self.wait.until(
            EC.element_to_be_clickable((By.ID, "npasswd"))
        ).send_keys(SIANNET_PASSWORD)

        self.wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "button[onclick*='ValidaForm']")
            )
        ).click()

        self.wait.until(
            EC.visibility_of_element_located(
                (By.ID, "pesqAplicacao")
            )
        )

        print("Login realizado com sucesso!")

    # --------------------------------------------------
    # NAVEGAÇÃO ATÉ O RELATÓRIO
    # --------------------------------------------------

    def aguardar_pagina(self):
        WebDriverWait(self.driver, 60).until(
            lambda driver: driver.execute_script(
                "return document.readyState"
            ) == "complete"
        )

    def pesquisar_performance(self):
        print("\n[2/5] Pesquisando relatório de Performance...")

        self.aguardar_pagina()
        self.driver.switch_to.default_content()

        campo = self.wait.until(
            EC.element_to_be_clickable(
                (By.ID, "pesqAplicacao")
            )
        )

        campo.click()
        campo.send_keys(Keys.CONTROL, "a")
        campo.send_keys("Relatorio Performance")

        xpath = (
            "//ul[contains(@class, 'ui-autocomplete')]"
            "//a[contains(text(), 'Relatorio Performance')]"
        )

        resultado = self.wait.until(
            EC.element_to_be_clickable((By.XPATH, xpath))
        )

        resultado.click()

        print("Relatório selecionado.")

        self.aguardar_formulario()

    # --------------------------------------------------
    # LOCALIZAÇÃO DO FORMULÁRIO
    # --------------------------------------------------

    def formulario_disponivel(self, driver):
        driver.switch_to.default_content()

        iframes = driver.find_elements(By.TAG_NAME, "iframe")

        for iframe in iframes:
            driver.switch_to.default_content()
            driver.switch_to.frame(iframe)

            campanha = driver.find_elements(
                By.ID, "optCampanha"
            )

            relatorio = driver.find_elements(
                By.ID, "optRelatorio"
            )

            competencia = driver.find_elements(
                By.ID, "mesAno"
            )

            if campanha and relatorio and competencia:
                return True

        driver.switch_to.default_content()
        return False

    def aguardar_formulario(self):
        print("Aguardando formulário de Performance...")

        WebDriverWait(self.driver, 60).until(
            self.formulario_disponivel
        )

        self.entrar_no_iframe()

        print("Formulário de Performance disponível.")

    def entrar_no_iframe(self):
        self.driver.switch_to.default_content()

        for iframe in self.driver.find_elements(By.TAG_NAME, "iframe"):
            self.driver.switch_to.default_content()
            self.driver.switch_to.frame(iframe)

            if (
                self.driver.find_elements(By.ID, "optCampanha")
                and self.driver.find_elements(By.ID, "mesAno")
            ):
                return

        self.driver.switch_to.default_content()

        raise TimeoutException(
            "Não foi possível localizar o formulário de Performance."
        )

    # --------------------------------------------------
    # PERÍODO
    # --------------------------------------------------

    def obter_competencias(self):
        inicio = datetime.strptime(DATA_INICIO, "%d/%m/%Y")
        fim = datetime.strptime(DATA_FIM, "%d/%m/%Y")

        if inicio > fim:
            raise ValueError(
                "DATA_INICIO não pode ser posterior a DATA_FIM."
            )

        competencias = []

        ano = inicio.year
        mes = inicio.month

        while (ano, mes) <= (fim.year, fim.month):
            competencias.append(f"{mes:02d}/{ano}")

            mes += 1

            if mes > 12:
                mes = 1
                ano += 1

        return competencias

    # --------------------------------------------------
    # SELEÇÃO DA CAMPANHA
    # --------------------------------------------------

    def selecionar_campanha(self, competencia):
        self.entrar_no_iframe()

        seletor = Select(
            self.driver.find_element(By.ID, "optCampanha")
        )

        mes, ano = map(int, competencia.split("/"))

        competencia_data = datetime(ano, mes, 1)

        campanha_encontrada = None

        for opcao in seletor.options:
            valor = opcao.get_attribute("value")

            data_inicio = opcao.get_attribute("dataini")
            data_fim = opcao.get_attribute("datafim")

            if not valor or not data_inicio or not data_fim:
                continue

            try:
                inicio = datetime.strptime(
                    data_inicio, "%d/%m/%Y"
                )

                fim = datetime.strptime(
                    data_fim, "%d/%m/%Y"
                )

                if inicio <= competencia_data <= fim:
                    campanha_encontrada = valor
                    break

            except ValueError:
                continue

        if not campanha_encontrada:
            raise ValueError(
                f"Nenhuma campanha encontrada para {competencia}."
            )

        seletor.select_by_value(campanha_encontrada)

        print(
            f"Campanha selecionada: {campanha_encontrada}"
        )

        WebDriverWait(self.driver, 60).until(
            lambda driver: len(
                Select(
                    driver.find_element(By.ID, "mesAno")
                ).options
            ) > 1
        )

    # --------------------------------------------------
    # CONFIGURAÇÃO DO RELATÓRIO
    # --------------------------------------------------

    def configurar_relatorio(self, competencia):
        print(f"\nConfigurando competência {competencia}...")

        self.entrar_no_iframe()

        self.selecionar_campanha(competencia)

        self.entrar_no_iframe()

        relatorio = Select(
            self.driver.find_element(By.ID, "optRelatorio")
        )

        relatorio.select_by_value("performance_motoristas")

        saida = Select(
            self.driver.find_element(By.ID, "saida")
        )

        saida.select_by_value("csv")

        seletor_mes = Select(
            self.driver.find_element(By.ID, "mesAno")
        )

        competencia_encontrada = False

        for opcao in seletor_mes.options:
            texto = opcao.text.strip()
            valor = (opcao.get_attribute("value") or "").strip()

            if texto == competencia or valor == competencia:
                seletor_mes.select_by_value(
                    opcao.get_attribute("value")
                )
                competencia_encontrada = True
                break

        if not competencia_encontrada:
            raise ValueError(
                f"Competência {competencia} não disponível na campanha."
            )

        print("Relatório: performance_motoristas")
        print("Formato: CSV")
        print(f"Competência: {competencia}")

    # --------------------------------------------------
    # GERAÇÃO E DOWNLOAD
    # --------------------------------------------------

    def gerar_relatorio(self):
        self.entrar_no_iframe()

        botao = self.wait.until(
            EC.element_to_be_clickable(
                (By.ID, "btnPesquisar")
            )
        )

        botao.click()

        print("Relatório solicitado. Aguardando janela de download...")

    def clicar_download(self):
        def localizar_botao(driver):
            driver.switch_to.default_content()

            elementos = [
                (By.XPATH,
                 "//span[contains(@class, 'ui-button-text') "
                 "and normalize-space()='Download']")
            ]

            for iframe in driver.find_elements(By.TAG_NAME, "iframe"):
                driver.switch_to.default_content()
                driver.switch_to.frame(iframe)

                for seletor in elementos:
                    encontrados = driver.find_elements(*seletor)

                    if encontrados and encontrados[0].is_displayed():
                        return encontrados[0]

            driver.switch_to.default_content()

            for seletor in elementos:
                encontrados = driver.find_elements(*seletor)

                if encontrados and encontrados[0].is_displayed():
                    return encontrados[0]

            return False

        botao = WebDriverWait(self.driver, 90).until(
            localizar_botao
        )

        self.driver.execute_script(
            "arguments[0].click();",
            botao.find_element(By.XPATH, "./..")
        )

        self.driver.switch_to.default_content()

        print("Download solicitado.")

    def baixar_csv(self, competencia):
        arquivos_anteriores = set(
            os.listdir(self.pasta_download)
        )

        self.gerar_relatorio()

        self.clicar_download()

        print("Aguardando conclusão do download...")

        arquivo_baixado = None

        for _ in range(120):
            arquivos = os.listdir(self.pasta_download)

            novos = set(arquivos) - arquivos_anteriores

            csvs = [
                arquivo for arquivo in novos
                if arquivo.lower().endswith(".csv")
            ]

            downloads_parciais = [
                arquivo for arquivo in arquivos
                if arquivo.endswith(".crdownload")
            ]

            if csvs and not downloads_parciais:
                arquivo_baixado = max(
                    csvs,
                    key=lambda nome: os.path.getmtime(
                        Path(self.pasta_download) / nome
                    )
                )
                break

            time.sleep(1)

        if not arquivo_baixado:
            raise TimeoutError(
                f"Download de Performance {competencia} "
                "não concluído em 120 segundos."
            )

        origem = Path(self.pasta_download) / arquivo_baixado

        identificador = datetime.now().strftime("%Y%m%d_%H%M%S")

        competencia_nome = competencia.replace("/", "_")

        destino = (
            Path(self.pasta_download)
            / f"performance_{competencia_nome}_{identificador}.csv"
        )

        os.rename(origem, destino)

        print(f"Arquivo salvo: {destino.name}")

        return str(destino)

    # --------------------------------------------------
    # EXECUÇÃO PRINCIPAL
    # --------------------------------------------------

    def extrair_performance(self):
        try:
            # Abre o relatório antes de procurar os campos do formulário
            self.pesquisar_performance()

            print("\n[3/5] Preparando competências...")

            competencias = self.obter_competencias()

            print(f"Competências encontradas: {competencias}")

            arquivos = []

            for competencia in competencias:
                print("\n" + "=" * 50)
                print(f"PROCESSANDO PERFORMANCE: {competencia}")
                print("=" * 50)

                self.configurar_relatorio(competencia)

                arquivo = self.baixar_csv(competencia)

                arquivos.append(arquivo)

            print("\nTodas as competências foram processadas.")

            return arquivos

        except Exception:
            print("\nERRO DURANTE A EXTRAÇÃO DE PERFORMANCE:")
            traceback.print_exc()
            raise

    # --------------------------------------------------
    # ENCERRAMENTO
    # --------------------------------------------------

    def fechar(self):
        if self.driver:
            self.driver.quit()
            print("Navegador encerrado.")
