
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
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from config.settings import (
    SIANNET_USER,
    SIANNET_PASSWORD,
    PASTA_ESCALADOS,
    PERFIL_CHROME,
    DATA_INICIO,
    DATA_FIM
)


class RoboSiannet:

    def __init__(self):
        self.pasta_download = str(PASTA_ESCALADOS)
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

    def login_siannet(self):
        print("\n[1/4] Acessando Siannet...")

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

    def aguardar_pagina(self):
        print("Aguardando carregamento da página...")

        WebDriverWait(self.driver, 60).until(
            lambda driver: driver.execute_script(
                "return document.readyState"
            ) == "complete"
        )

    def pesquisar_escalados(self):
        print("\n[2/4] Pesquisando relatório de Escalados...")

        self.aguardar_pagina()
        self.driver.switch_to.default_content()

        campo = self.wait.until(
            EC.element_to_be_clickable(
                (By.ID, "pesqAplicacao")
            )
        )

        print("Campo de pesquisa disponível.")

        campo.click()
        campo.send_keys(Keys.CONTROL, "a")
        campo.send_keys("Info")

        xpath = (
            "//ul[contains(@class, 'ui-autocomplete')]"
            "//a[contains(text(), 'Informações De Escalados')]"
        )

        resultado = self.wait.until(
            EC.element_to_be_clickable((By.XPATH, xpath))
        )

        resultado.click()

        print("Relatório selecionado. Aguardando carregamento...")

        self.aguardar_relatorio()

    def aguardar_relatorio(self):
        def formulario_disponivel(driver):
            driver.switch_to.default_content()

            iframes = driver.find_elements(By.TAG_NAME, "iframe")

            if iframes:
                for iframe in iframes:
                    driver.switch_to.default_content()
                    driver.switch_to.frame(iframe)

                    inicio = driver.find_elements(
                        By.ID, "pesq_inicio"
                    )

                    fim = driver.find_elements(
                        By.ID, "pesq_fim"
                    )

                    if inicio and fim:
                        return True

                driver.switch_to.default_content()

            return False

        WebDriverWait(self.driver, 60).until(
            formulario_disponivel
        )

        self.driver.switch_to.default_content()

        for iframe in self.driver.find_elements(By.TAG_NAME, "iframe"):
            self.driver.switch_to.frame(iframe)

            if (
                self.driver.find_elements(By.ID, "pesq_inicio")
                and self.driver.find_elements(By.ID, "pesq_fim")
            ):
                break

            self.driver.switch_to.default_content()

        print("Formulário do relatório disponível.")

    def preencher_periodo(self):
        print("\n[3/4] Preenchendo período...")

        js = """
        const campo = arguments[0];
        const valor = arguments[1];

        const setter = Object.getOwnPropertyDescriptor(
            window.HTMLInputElement.prototype, 'value'
        ).set;

        setter.call(campo, valor);

        campo.dispatchEvent(new Event('input', {bubbles: true}));
        campo.dispatchEvent(new Event('change', {bubbles: true}));
        """

        campo_inicio = self.wait.until(
            EC.presence_of_element_located(
                (By.ID, "pesq_inicio")
            )
        )

        campo_fim = self.wait.until(
            EC.presence_of_element_located(
                (By.ID, "pesq_fim")
            )
        )

        self.driver.execute_script(
            js, campo_inicio, DATA_INICIO
        )

        self.driver.execute_script(
            js, campo_fim, DATA_FIM
        )

        print(f"Período: {DATA_INICIO} até {DATA_FIM}")

        botao = self.wait.until(
            EC.element_to_be_clickable(
                (By.NAME, "pesquisar")
            )
        )

        botao.click()

        self.wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//table//td")
            )
        )

        print("Pesquisa concluída.")

    def baixar_csv(self):
        print("\n[4/4] Solicitando arquivo CSV...")

        arquivos_anteriores = set(
            os.listdir(self.pasta_download)
        )

        botao_csv = self.wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "img[src*='file_csv.png']")
            )
        )

        self.driver.execute_script(
            "arguments[0].click();", botao_csv
        )

        botao_download = self.wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//span[contains(@class, 'ui-button-text') "
                    "and normalize-space()='Download']"
                )
            )
        )

        self.driver.execute_script(
            "arguments[0].click();",
            botao_download.find_element(By.XPATH, "./..")
        )

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
                arquivo_baixado = csvs[0]
                break

            time.sleep(1)

        if not arquivo_baixado:
            raise TimeoutError(
                "O download do CSV não foi concluído em 120 segundos."
            )

        origem = Path(self.pasta_download) / arquivo_baixado

        identificador = datetime.now().strftime("%Y%m%d_%H%M%S")

        destino = (
            Path(self.pasta_download)
            / f"escalados_{identificador}.csv"
        )

        os.rename(origem, destino)

        print(f"Arquivo salvo: {destino.name}")

        return str(destino)

    def extrair_escalados(self):
        try:
            self.pesquisar_escalados()
            self.preencher_periodo()
            return self.baixar_csv()

        except Exception:
            print("\nERRO DURANTE A EXTRAÇÃO:")
            traceback.print_exc()
            raise

    def fechar(self):
        if self.driver:
            self.driver.quit()
            print("Navegador encerrado.")
