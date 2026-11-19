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
    SIANNET_USER, SIANNET_PASSWORD, PASTA_EVENTOS_VIAGENS,
    PERFIL_CHROME, DATA_INICIO, DATA_FIM
)


class RoboEventosViagens:
    def __init__(self):
        self.pasta_download = str(PASTA_EVENTOS_VIAGENS)
        Path(self.pasta_download).mkdir(parents=True, exist_ok=True)

        self.options = Options()
        self.options.add_argument("--start-maximized")
        self.options.add_argument(f"--user-data-dir={PERFIL_CHROME}")
        self.options.add_experimental_option("prefs", {
            "download.default_directory": self.pasta_download,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        })

        self.service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(
            service=self.service, options=self.options
        )
        self.wait = WebDriverWait(self.driver, 60)

    def login_siannet(self):
        print("\n[1/5] Acessando Siannet...")
        if not SIANNET_USER or not SIANNET_PASSWORD:
            raise ValueError("Credenciais do Siannet não configuradas no .env")

        self.driver.get("https://siannet.gestaosian.com/")
        self.wait.until(
            EC.element_to_be_clickable((By.ID, "nlogin"))
        ).send_keys(SIANNET_USER)
        self.wait.until(
            EC.element_to_be_clickable((By.ID, "npasswd"))
        ).send_keys(SIANNET_PASSWORD)
        self.wait.until(EC.element_to_be_clickable((
            By.CSS_SELECTOR, "button[onclick*='ValidaForm']"
        ))).click()
        self.wait.until(
            EC.visibility_of_element_located((By.ID, "pesqAplicacao"))
        )
        print("Login realizado com sucesso!")

    def aguardar_pagina(self):
        WebDriverWait(self.driver, 60).until(
            lambda driver: driver.execute_script(
                "return document.readyState"
            ) == "complete"
        )

    def pesquisar_relatorio(self):
        print(
            "\n[2/5] Pesquisando Relatório Resumo "
            "Eventos/Viagens Telemetria..."
        )
        self.aguardar_pagina()
        self.driver.switch_to.default_content()

        campo = self.wait.until(
            EC.element_to_be_clickable((By.ID, "pesqAplicacao"))
        )
        campo.click()
        campo.send_keys(Keys.CONTROL, "a")
        campo.send_keys("Resumo Eventos/Viagens Telemetria")

        xpath = (
            "//ul[contains(@class, 'ui-autocomplete')]"
            "//a[contains(., 'Resumo Eventos/Viagens Telemetria')]"
        )
        self.wait.until(
            EC.element_to_be_clickable((By.XPATH, xpath))
        ).click()

        print("Relatório selecionado.")
        self.aguardar_formulario()

    def formulario_disponivel(self, driver):
        driver.switch_to.default_content()
        for iframe in driver.find_elements(By.TAG_NAME, "iframe"):
            driver.switch_to.default_content()
            driver.switch_to.frame(iframe)
            if all(driver.find_elements(By.ID, campo) for campo in (
                "tipo_relatorio", "pesq_inicio", "pesq_final",
                "identificacao", "saida"
            )):
                return True
        driver.switch_to.default_content()
        return False

    def aguardar_formulario(self):
        print("Aguardando formulário de Eventos/Viagens...")
        WebDriverWait(self.driver, 60).until(self.formulario_disponivel)
        self.entrar_no_iframe()
        print("Formulário disponível.")

    def entrar_no_iframe(self):
        self.driver.switch_to.default_content()
        for iframe in self.driver.find_elements(By.TAG_NAME, "iframe"):
            self.driver.switch_to.default_content()
            self.driver.switch_to.frame(iframe)
            if all(self.driver.find_elements(By.ID, campo) for campo in (
                "tipo_relatorio", "pesq_inicio", "pesq_final", "saida"
            )):
                return
        self.driver.switch_to.default_content()
        raise TimeoutException(
            "Não foi possível localizar o formulário "
            "Relatório Resumo Eventos/Viagens Telemetria."
        )

    def preencher_periodo(self):
        """
        Atualiza as duas datas juntas antes de disparar os eventos do
        formulário. Isso evita que o Siannet valide uma data nova contra
        a outra data antiga ainda presente no formulário.
        """
        campo_inicio = self.wait.until(
            EC.presence_of_element_located((By.ID, "pesq_inicio"))
        )
        campo_final = self.wait.until(
            EC.presence_of_element_located((By.ID, "pesq_final"))
        )

        self.driver.execute_script("""
            const inicio = arguments[0];
            const final = arguments[1];
            const valorInicio = arguments[2];
            const valorFinal = arguments[3];

            const setter = Object.getOwnPropertyDescriptor(
                window.HTMLInputElement.prototype, 'value'
            ).set;

            // Primeiro atualiza os dois valores, sem disparar validação.
            setter.call(inicio, valorInicio);
            setter.call(final, valorFinal);

            // Só depois notifica o formulário, com as duas datas já definidas.
            for (const el of [inicio, final]) {
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
            }

            final.dispatchEvent(new Event('blur', { bubbles: true }));
        """, campo_inicio, campo_final, DATA_INICIO, DATA_FIM)

        valor_inicio = campo_inicio.get_attribute("value")
        valor_final = campo_final.get_attribute("value")

        if valor_inicio != DATA_INICIO or valor_final != DATA_FIM:
            raise RuntimeError(
                "O Siannet não manteve o período informado. "
                f"Início: {valor_inicio} | Final: {valor_final}"
            )

        print(f"Data inicial confirmada: {valor_inicio}")
        print(f"Data final confirmada: {valor_final}")

    def configurar_relatorio(self):
        print("\n[3/5] Configurando relatório...")
        inicio = datetime.strptime(DATA_INICIO, "%d/%m/%Y")
        fim = datetime.strptime(DATA_FIM, "%d/%m/%Y")
        if inicio > fim:
            raise ValueError(
                "DATA_INICIO não pode ser posterior a DATA_FIM."
            )

        self.entrar_no_iframe()

        Select(self.driver.find_element(
            By.ID, "tipo_relatorio"
        )).select_by_value("eventos")

        self.preencher_periodo()

        Select(self.driver.find_element(
            By.ID, "identificacao"
        )).select_by_value("todos")
        Select(self.driver.find_element(
            By.ID, "saida"
        )).select_by_value("csv")

        # Validação final: não gera o relatório se o Siannet tiver
        # revertido qualquer uma das datas.
        data_inicio_atual = self.driver.find_element(
            By.ID, "pesq_inicio"
        ).get_attribute("value")
        data_final_atual = self.driver.find_element(
            By.ID, "pesq_final"
        ).get_attribute("value")

        if data_inicio_atual != DATA_INICIO or data_final_atual != DATA_FIM:
            raise RuntimeError(
                "As datas não permaneceram no formulário do Siannet. "
                f"Início: {data_inicio_atual} | Final: {data_final_atual}"
            )

        print("Tipo de relatório: Eventos")
        print(f"Data inicial confirmada: {data_inicio_atual}")
        print(f"Data final confirmada: {data_final_atual}")
        print("Identificação: Todos")
        print("Formato: CSV")

    def gerar_relatorio(self):
        self.entrar_no_iframe()
        botao = self.wait.until(EC.element_to_be_clickable((
            By.CSS_SELECTOR, "input[onclick='CarregarRelatorio();']"
        )))
        botao.click()
        print("Relatório solicitado. Aguardando janela de download...")

    def clicar_download(self):
        def localizar_botao(driver):
            driver.switch_to.default_content()
            seletor = (
                By.XPATH,
                "//span[contains(@class, 'ui-button-text') "
                "and normalize-space()='Download']"
            )
            for iframe in driver.find_elements(By.TAG_NAME, "iframe"):
                driver.switch_to.default_content()
                driver.switch_to.frame(iframe)
                encontrados = driver.find_elements(*seletor)
                if encontrados and encontrados[0].is_displayed():
                    return encontrados[0]

            driver.switch_to.default_content()
            encontrados = driver.find_elements(*seletor)
            if encontrados and encontrados[0].is_displayed():
                return encontrados[0]
            return False

        botao = WebDriverWait(self.driver, 90).until(localizar_botao)
        self.driver.execute_script(
            "arguments[0].click();",
            botao.find_element(By.XPATH, "./..")
        )
        self.driver.switch_to.default_content()
        print("Download solicitado.")

    def baixar_csv(self):
        anteriores = set(os.listdir(self.pasta_download))
        self.gerar_relatorio()
        self.clicar_download()
        print("Aguardando conclusão do download...")

        arquivo_baixado = None
        for _ in range(120):
            arquivos = os.listdir(self.pasta_download)
            novos = set(arquivos) - anteriores
            csvs = [
                nome for nome in novos if nome.lower().endswith(".csv")
            ]
            parciais = [
                nome for nome in arquivos if nome.endswith(".crdownload")
            ]
            if csvs and not parciais:
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
                "Download do Relatório Resumo Eventos/Viagens "
                "não concluído em 120 segundos."
            )

        origem = Path(self.pasta_download) / arquivo_baixado
        destino = Path(self.pasta_download) / (
            "eventos_viagens_"
            + datetime.now().strftime("%Y%m%d_%H%M%S")
            + ".csv"
        )
        os.rename(origem, destino)
        print(f"Arquivo salvo: {destino.name}")
        return str(destino)

    def extrair_eventos_viagens(self):
        try:
            self.pesquisar_relatorio()
            self.configurar_relatorio()
            arquivo = self.baixar_csv()
            print("\nExtração de Eventos/Viagens concluída.")
            return arquivo
        except Exception:
            print("\nERRO DURANTE A EXTRAÇÃO DE EVENTOS/VIAGENS:")
            traceback.print_exc()
            raise

    def fechar(self):
        if getattr(self, "driver", None):
            self.driver.quit()
            print("Navegador encerrado.")


if __name__ == "__main__":
    bot = None
    try:
        bot = RoboEventosViagens()
        bot.login_siannet()
        arquivo = bot.extrair_eventos_viagens()
        print(f"\nExtração concluída: {arquivo}")
    finally:
        if bot:
            bot.fechar()
