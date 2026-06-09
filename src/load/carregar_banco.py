import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime

PROCESSED_DIR = Path("data/processed")
DB_PATH = Path("data/indicadores.db")


def conectar() -> sqlite3.Connection:
    """
    Cria ou conecta ao banco SQLite.
    Se o arquivo não existir, o SQLite cria automaticamente.
    """
    conn = sqlite3.connect(DB_PATH)
    print(f"  📂 Banco: {DB_PATH}")
    return conn


def criar_tabelas(conn: sqlite3.Connection):
    """
    Cria as tabelas se ainda não existirem.
    """
    cursor = conn.cursor()

    # Tabela principal com os dados das séries
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS indicadores (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            serie       TEXT    NOT NULL,
            data        TEXT    NOT NULL,
            valor       REAL    NOT NULL,
            carregado_em TEXT   NOT NULL,
            UNIQUE(serie, data)  -- impede duplicatas da mesma série na mesma data
        )
    """)

    # Tabela de log de cada execução do pipeline
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS log_carga (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            serie        TEXT    NOT NULL,
            arquivo      TEXT    NOT NULL,
            registros    INTEGER NOT NULL,
            executado_em TEXT    NOT NULL
        )
    """)

    conn.commit()
    print("  ✓ Tabelas verificadas/criadas")


def carregar_csv(conn: sqlite3.Connection, caminho: Path) -> int:
    """
    Lê um CSV processed e insere no banco.
    Usa INSERT OR IGNORE para pular duplicatas silenciosamente.
    Retorna o número de registros inseridos.
    """
    # Ignora arquivos vazios
    if caminho.stat().st_size == 0:
    	print(f"  ⚠ Arquivo vazio ignorado: {caminho.name}")
    	return 0

    df = pd.read_csv(caminho)
    nome_serie = df["serie"].iloc[0]
    agora = datetime.now().isoformat()

    cursor = conn.cursor()
    inseridos = 0

    for _, row in df.iterrows():
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO indicadores (serie, data, valor, carregado_em)
                VALUES (?, ?, ?, ?)
            """, (
                row["serie"],
                str(row["data"]),
                float(row["valor"]),
                agora
            ))
            if cursor.rowcount > 0:
                inseridos += 1

        except Exception as e:
            print(f"  ⚠ Erro ao inserir linha: {e}")

    # Registra no log de carga
    cursor.execute("""
        INSERT INTO log_carga (serie, arquivo, registros, executado_em)
        VALUES (?, ?, ?, ?)
    """, (nome_serie, caminho.name, inseridos, agora))

    conn.commit()
    return inseridos


def carregar_todos():
    """
    Lê todos os CSVs de processed e carrega no banco.
    """
    arquivos = list(PROCESSED_DIR.glob("*.csv"))

    if not arquivos:
        print("Nenhum arquivo encontrado em data/processed")
        return

    print(f"\n{'='*50}")
    print(f"Iniciando carga: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"{len(arquivos)} arquivos encontrados em data/processed")
    print(f"{'='*50}\n")

    conn = conectar()
    criar_tabelas(conn)
    print()

    total_inseridos = 0

    for caminho in arquivos:
        print(f"→ Carregando: {caminho.name}")
        inseridos = carregar_csv(conn, caminho)
        print(f"  ✓ {inseridos} registros inseridos (duplicatas ignoradas)")
        total_inseridos += inseridos
        print()

    conn.close()

    print(f"{'='*50}")
    print(f"Carga concluída")
    print(f"  Total inserido: {total_inseridos} registros")
    print(f"  Banco em: {DB_PATH}")
    print(f"{'='*50}\n")


def consultar(sql: str) -> pd.DataFrame:
    """
    Executa uma query e retorna o resultado como DataFrame.
    Útil para verificar os dados depois da carga.
    """
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(sql, conn)
    conn.close()
    return df


if __name__ == "__main__":
    # 1. Carrega todos os CSVs no banco
    carregar_todos()

    # 2. Verifica o resultado com queries SQL
    print("Verificando dados no banco...\n")

    # Quantos registros por série?
    print("── Registros por série:")
    df = consultar("""
        SELECT
            serie,
            COUNT(*)        AS total_registros,
            MIN(data)       AS data_mais_antiga,
            MAX(data)       AS data_mais_recente,
            ROUND(AVG(valor), 4) AS media_valor
        FROM indicadores
        GROUP BY serie
        ORDER BY serie
    """)
    print(df.to_string(index=False))

    # Log das cargas
    print("\n── Log de cargas:")
    df_log = consultar("SELECT * FROM log_carga ORDER BY executado_em DESC")
    print(df_log.to_string(index=False))