"""
Funções reutilizáveis de padronização do Prime Painel.

Este módulo NÃO altera os CSVs originais.
As funções são aplicadas sobre cópias dos DataFrames durante o processamento.
"""

import re
import unicodedata
from typing import Any

import pandas as pd


def normalizar_nome_coluna(nome: Any) -> str:
    """Padroniza cabeçalhos sem perder o significado original."""
    texto = str(nome).strip().lower()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = texto.replace("ª", "a").replace("º", "o")
    texto = re.sub(r"[^a-z0-9]+", "_", texto)
    return texto.strip("_")


def normalizar_texto(valor: Any) -> Any:
    """Remove espaços excedentes, preservando valores ausentes."""
    if pd.isna(valor):
        return pd.NA

    texto = str(valor).replace("\u00a0", " ")
    texto = re.sub(r"\s+", " ", texto).strip()

    return texto if texto else pd.NA


def normalizar_identificador(valor: Any, largura: int | None = None) -> Any:
    """
    Normaliza chapa/matrícula como TEXTO.
    Nunca converte identificadores para número.

    Se largura for informada, completa com zeros à esquerda.
    Só use largura depois de confirmar o tamanho oficial do identificador.
    """
    if pd.isna(valor):
        return pd.NA

    texto = str(valor).strip()

    # Corrige identificadores que eventualmente tenham sido lidos como 1234.0.
    if re.fullmatch(r"\d+\.0+", texto):
        texto = texto.split(".", 1)[0]

    # Remove espaços internos e caracteres de formatação, mantendo apenas dígitos.
    digitos = re.sub(r"\D", "", texto)

    if not digitos:
        return pd.NA

    if set(digitos) == {"0"}:
        return pd.NA

    if largura:
        digitos = digitos.zfill(largura)

    return digitos


def normalizar_chapa(valor: Any) -> Any:
    """Chapa padronizada como texto; não força largura sem regra confirmada."""
    return normalizar_identificador(valor)


def normalizar_matricula(valor: Any) -> Any:
    """Matrícula padronizada como texto; não força largura sem regra confirmada."""
    return normalizar_identificador(valor)


def normalizar_data_coluna(serie: pd.Series, formato: str = "%d/%m/%Y") -> pd.Series:
    """Converte datas brasileiras para datetime; valores inválidos ficam como NaT."""
    return pd.to_datetime(
        serie.map(normalizar_texto),
        format=formato,
        errors="coerce",
        dayfirst=True,
    )


def normalizar_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Retorna uma cópia com cabeçalhos padronizados e textos sem espaços excedentes.
    Não converte automaticamente números ou datas: isso será feito por coluna,
    com regras específicas para cada relatório.
    """
    tratado = df.copy()
    tratado.columns = [normalizar_nome_coluna(col) for col in tratado.columns]

    # Se dois cabeçalhos diferentes virarem o mesmo nome, interrompe para evitar
    # sobrescrever uma coluna silenciosamente.
    duplicadas = tratado.columns[tratado.columns.duplicated()].tolist()
    if duplicadas:
        raise ValueError(
            "A padronização gerou nomes de colunas duplicados: "
            + ", ".join(sorted(set(duplicadas)))
        )

    for coluna in tratado.select_dtypes(include=["object"]).columns:
        tratado[coluna] = tratado[coluna].map(normalizar_texto)

    return tratado


def normalizar_chaves(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza as colunas de identificação existentes, sem exigir que todas existam."""
    tratado = df.copy()

    if "chapa" in tratado.columns:
        tratado["chapa"] = tratado["chapa"].map(normalizar_chapa).astype("string")

    if "matricula" in tratado.columns:
        tratado["matricula"] = tratado["matricula"].map(normalizar_matricula).astype("string")

    if "nome" in tratado.columns:
        tratado["nome"] = tratado["nome"].map(normalizar_texto).astype("string")

    return tratado
