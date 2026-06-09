import json
import pandas as pd
from pathlib import Path
from datetime import datetime

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")


def carregar_raw(caminho: Path) -> pd.DataFrame:
    """
    Lê um arquivo JSON raw e retorna um DataFrame com os dados.
    """
    with open(caminho, "r", encoding="utf-8") as f:
        payload = json.load(f)

    nome_serie = payload["serie"]
    dados = payload["dados"]

    # Transforma a lista de dicionários em DataFrame
    df = pd.DataFrame(dados)

    # Adiciona coluna com o nome da série — útil quando unir tudo
    df["serie"] = nome_serie

    return df, nome_serie


def transformar(df: pd.DataFrame, nome_serie: str) -> pd.DataFrame:
    """
    Aplica as transformações necessárias:
    - Converte 'data' de texto para datetime
    - Converte 'valor' de texto para float
    - Remove linhas com valor nulo
    - Renomeia colunas para padrão snake_case
    - Ordena por data
    """
    print(f"  Transformando '{nome_serie}'...")
    print(f"  Shape inicial: {df.shape}")

    # 1. Converter coluna de data
    df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y")

    # 2. Converter valor para número
    # errors="coerce" transforma valores inválidos em NaN ao invés de quebrar
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")

    # 3. Verificar e reportar nulos antes de remover
    nulos = df["valor"].isna().sum()
    if nulos > 0:
        print(f"  ⚠ {nulos} valores nulos encontrados — serão removidos")

    df = df.dropna(subset=["valor"])

    # 4. Ordenar por data
    df = df.sort_values("data").reset_index(drop=True)

    # 5. Adicionar coluna de quando foi processado
    df["processado_em"] = datetime.now().isoformat()

    print(f"  Shape final:   {df.shape}")
    print(f"  Período: {df['data'].min().date()} → {df['data'].max().date()}")
    print(f"  Valor mín: {df['valor'].min():.4f} | máx: {df['valor'].max():.4f} | média: {df['valor'].mean():.4f}")

    return df


def salvar_processed(df: pd.DataFrame, nome_serie: str) -> Path:
    """
    Salva o DataFrame transformado como CSV em data/processed.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome_arquivo = f"{nome_serie}_{timestamp}.csv"
    caminho = PROCESSED_DIR / nome_arquivo

    df.to_csv(caminho, index=False, encoding="utf-8")
    print(f"  💾 Salvo em: {caminho}")

    return caminho


def transformar_todos() -> dict:
    """
    Lê todos os arquivos raw, transforma e salva em processed.
    """
    arquivos_raw = list(RAW_DIR.glob("*.json"))

    if not arquivos_raw:
        print("Nenhum arquivo encontrado em data/raw")
        return {}

    print(f"\n{'='*50}")
    print(f"Iniciando transformação: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"{len(arquivos_raw)} arquivos encontrados em data/raw")
    print(f"{'='*50}\n")

    resultados = {"sucesso": [], "falha": []}

    for caminho in arquivos_raw:
        print(f"→ Arquivo: {caminho.name}")
        try:
            df_raw, nome_serie = carregar_raw(caminho)
            df_transformado = transformar(df_raw, nome_serie)
            salvar_processed(df_transformado, nome_serie)
            resultados["sucesso"].append(nome_serie)

        except Exception as e:
            print(f"  ✗ Erro ao transformar {caminho.name}: {e}")
            resultados["falha"].append(caminho.name)

        print()

    print(f"{'='*50}")
    print(f"Transformação concluída")
    print(f"  ✓ Sucesso: {len(resultados['sucesso'])} séries")
    print(f"  ✗ Falha:   {len(resultados['falha'])} séries")
    print(f"{'='*50}\n")

    return resultados


if __name__ == "__main__":
    transformar_todos()