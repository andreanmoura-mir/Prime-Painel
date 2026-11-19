import csv
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
    SIANNET_USER, SIANNET_PASSWORD, PASTA_TELEMETRIA,
    PERFIL_CHROME, DATA_INICIO, DATA_FIM
)


class RoboTelemetria:
    def __init__(self):
        self.pasta_download = str(PASTA_TELEMETRIA)
        Path(self.pasta_download).mkdir(parents=True, exist_ok=True)
        self.driver = None

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

    # LOGIN
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

    # NAVEGAÇÃO
    def aguardar_pagina(self):
        WebDriverWait(self.driver, 60).until(
            lambda driver: driver.execute_script(
                "return document.readyState"
            ) == "complete"
        )

    def pesquisar_relatorio(self):
        print("\n[2/5] Pesquisando Relatorio Eventos Telemetria...")
        self.aguardar_pagina()
        self.driver.switch_to.default_content()

        campo = self.wait.until(
            EC.element_to_be_clickable((By.ID, "pesqAplicacao"))
        )
        campo.click()
        campo.send_keys(Keys.CONTROL, "a")
        campo.send_keys("Relatorio Eventos Telemetria")

        xpath = (
            "//ul[contains(@class, 'ui-autocomplete')]"
            "//a[contains(., 'Relatorio Eventos Telemetria')]"
        )
        self.wait.until(
            EC.element_to_be_clickable((By.XPATH, xpath))
        ).click()

        print("Relatório selecionado.")
        self.aguardar_formulario()

    # FORMULÁRIO / IFRAME
    def formulario_disponivel(self, driver):
        driver.switch_to.default_content()
        for iframe in driver.find_elements(By.TAG_NAME, "iframe"):
            driver.switch_to.default_content()
            driver.switch_to.frame(iframe)
            if (
                driver.find_elements(By.ID, "optCampanha")
                and driver.find_elements(By.ID, "optRelatorio")
                and driver.find_elements(By.ID, "saida")
                and driver.find_elements(By.ID, "btnPesquisar")
            ):
                return True
        driver.switch_to.default_content()
        return False

    def aguardar_formulario(self):
        print("Aguardando formulário de Eventos Telemetria...")
        WebDriverWait(self.driver, 60).until(self.formulario_disponivel)
        self.entrar_no_iframe()
        print("Formulário disponível.")

    def entrar_no_iframe(self):
        self.driver.switch_to.default_content()
        for iframe in self.driver.find_elements(By.TAG_NAME, "iframe"):
            self.driver.switch_to.default_content()
            self.driver.switch_to.frame(iframe)
            if (
                self.driver.find_elements(By.ID, "optCampanha")
                and self.driver.find_elements(By.ID, "optRelatorio")
                and self.driver.find_elements(By.ID, "saida")
            ):
                return
        self.driver.switch_to.default_content()
        raise TimeoutException(
            "Não foi possível localizar o formulário de Eventos Telemetria."
        )

    # COMPETÊNCIAS DO .ENV
    def obter_competencias(self):
        inicio = datetime.strptime(DATA_INICIO, "%d/%m/%Y")
        fim = datetime.strptime(DATA_FIM, "%d/%m/%Y")
        if inicio > fim:
            raise ValueError(
                "DATA_INICIO não pode ser posterior a DATA_FIM."
            )

        competencias = []
        ano, mes = inicio.year, inicio.month
        while (ano, mes) <= (fim.year, fim.month):
            competencias.append(f"{mes:02d}/{ano}")
            mes += 1
            if mes > 12:
                mes, ano = 1, ano + 1
        return competencias

    # CONFIGURAÇÃO DO RELATÓRIO
    def configurar_relatorio(self):
        print("\nConfigurando Relatorio Eventos Telemetria...")
        self.entrar_no_iframe()

        Select(self.driver.find_element(
            By.ID, "optCampanha"
        )).select_by_value("84")

        Select(self.driver.find_element(
            By.ID, "optRelatorio"
        )).select_by_value("relatorio_geral")

        Select(self.driver.find_element(
            By.ID, "saida"
        )).select_by_value("csv")

        print("Campanha: PRIME - 6ª Edição 2026 (84)")
        print("Relatório: Pontuação Geral")
        print("Formato: CSV")

    # GERAÇÃO / DOWNLOAD
    def gerar_relatorio(self):
        self.entrar_no_iframe()
        self.wait.until(
            EC.element_to_be_clickable((By.ID, "btnPesquisar"))
        ).click()
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

    def baixar_csv_bruto(self):
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
                "Download do Relatorio Eventos Telemetria "
                "não concluído em 120 segundos."
            )

        origem = Path(self.pasta_download) / arquivo_baixado
        destino = Path(self.pasta_download) / (
            "telemetria_bruto_" + datetime.now().strftime("%Y%m%d_%H%M%S")
            + ".csv"
        )
        os.rename(origem, destino)
        print(f"CSV bruto salvo: {destino.name}")
        return destino

    # LEITURA E TRATAMENTO DO CSV
    def ler_csv(self, arquivo):
        for encoding in ("utf-8-sig", "cp1252", "latin-1"):
            try:
                with open(arquivo, "r", encoding=encoding, newline="") as entrada:
                    amostra = entrada.read(8192)
                    entrada.seek(0)

                    try:
                        dialeto = csv.Sniffer().sniff(
                            amostra, delimiters=";,\\t|"
                        )
                    except csv.Error:
                        dialeto = csv.excel
                        dialeto.delimiter = ";"

                    leitor = csv.DictReader(entrada, dialect=dialeto)
                    linhas = list(leitor)
                    colunas = [
                        (coluna or "").strip().lstrip("\\ufeff")
                        for coluna in (leitor.fieldnames or [])
                    ]

                    if not colunas:
                        raise ValueError("O CSV não possui cabeçalho.")

                    return colunas, linhas

            except UnicodeDecodeError:
                continue

        raise ValueError("Não foi possível identificar a codificação do CSV.")

    @staticmethod
    def normalizar_nome_coluna(nome):
        import unicodedata

        nome = (nome or "").strip().lstrip("\\ufeff").lower()
        nome = unicodedata.normalize("NFKD", nome)
        nome = "".join(
            caractere for caractere in nome
            if not unicodedata.combining(caractere)
        )
        return nome

    def tratar_csv(self, arquivo_bruto, competencia):
        print(f"\\nTratando competência {competencia}...")

        colunas, linhas = self.ler_csv(arquivo_bruto)

        # Normaliza cabeçalhos: por exemplo, "função" vira "funcao".
        mapa_colunas = {
            self.normalizar_nome_coluna(coluna): coluna
            for coluna in colunas
        }

        identificacao = ["chapa", "matricula", "nome", "funcao"]
        indicadores = [
            "eventos-qtd",
            "eventos-pts",
            "kmviagens",
            "pontos-fke",
            "recalculando-rota",
            "grupo",
            "pontuacao"
        ]

        campos_mes = [
            f"{competencia}-{indicador}"
            for indicador in indicadores
        ]

        # "funcao" é mantida no arquivo tratado, mas pode não vir no CSV
        # exportado pelo Siannet. Nesse caso, a coluna fica vazia.
        campos_obrigatorios = [
            "chapa",
            "matricula",
            "nome"
        ] + campos_mes

        ausentes = [
            campo for campo in campos_obrigatorios
            if self.normalizar_nome_coluna(campo) not in mapa_colunas
        ]

        if ausentes:
            raise ValueError(
                "Colunas obrigatórias não encontradas no CSV bruto: "
                + ", ".join(ausentes)
                + f". Cabeçalhos recebidos: {colunas}"
            )

        campos_saida = identificacao + campos_mes

        competencia_nome = competencia.replace("/", "_")
        identificador = datetime.now().strftime("%Y%m%d_%H%M%S")
        destino = Path(self.pasta_download) / (
            f"telemetria_{competencia_nome}_{identificador}.csv"
        )

        with open(destino, "w", encoding="utf-8-sig", newline="") as saida:
            escritor = csv.DictWriter(
                saida,
                fieldnames=campos_saida,
                delimiter=";"
            )
            escritor.writeheader()

            for linha in linhas:
                linha_normalizada = {
                    self.normalizar_nome_coluna(chave): valor
                    for chave, valor in linha.items()
                    if chave is not None
                }

                registro = {}
                for campo in campos_saida:
                    chave_normalizada = self.normalizar_nome_coluna(campo)
                    registro[campo] = linha_normalizada.get(
                        chave_normalizada, ""
                    )

                escritor.writerow(registro)

        print(f"Arquivo tratado salvo: {destino.name}")
        print(f"Registros: {len(linhas)}")

        if "funcao" not in mapa_colunas:
            print(
                "Aviso: o CSV bruto não trouxe a coluna 'funcao'. "
                "Ela foi mantida vazia no arquivo tratado."
            )

        return str(destino)

    # EXECUÇÃO PRINCIPAL
    def extrair_telemetria(self):
        try:
            self.pesquisar_relatorio()
            competencias = self.obter_competencias()
            print(f"\nCompetências configuradas: {competencias}")

            self.configurar_relatorio()
            bruto = self.baixar_csv_bruto()

            tratados = []
            for competencia in competencias:
                tratados.append(self.tratar_csv(bruto, competencia))

            print("\nExtração de Eventos Telemetria concluída.")
            return {
                "arquivo_bruto": str(bruto),
                "arquivos_tratados": tratados
            }
        except Exception:
            print("\nERRO DURANTE A EXTRAÇÃO DE EVENTOS TELEMETRIA:")
            traceback.print_exc()
            raise

    # ENCERRAMENTO
    def fechar(self):
        if self.driver:
            self.driver.quit()
            print("Navegador encerrado.")
