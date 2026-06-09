import requests
import json
import time
from datetime import datetime
from pathlib import Path

BCB_BASE_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"

# Diretório onde os dados brutos serão salvos
RAW_DIR = Path("data/raw")

# Catálogo de séries que vamos extrair
# Formato: "nome_amigavel": codigo_bcb
SERIES = {
    "ipca_mensal":     433,   # Inflação mensal (%)
    "selic_diaria":    1,     # Taxa SELIC diária (%)
    "dolar_comercial": 1,     # Dólar comercial - venda
    "pib_mensal":      4380,  # PIB mensal (R$ milhões)
}

# Séries corretas por código
SERIES = {
    "ipca_mensal":     433,
    "selic_diaria":    11,    # SELIC Over (% a.d.)
    "dolar_comercial": 10813, # Taxa de câmbio - Dólar americano (venda)
    "igpm_mensal":     189,   # IGP-M mensal (%)
}


def buscar_serie(nome: str, codigo: int, data_inicio: str, data_fim: str) -> list | None:
    """
    Busca uma série do BCB com retry automático em caso de falha.
    Retorna a lista de registros ou None se todas as tentativas falharem.
    """
    url = BCB_BASE_URL.format(codigo=codigo)
    params = {
        "formato": "json",
        "dataInicial": data_inicio,
        "dataFinal": data_fim
    }

    MAX_TENTATIVAS = 3
    ESPERA_ENTRE_TENTATIVAS = 2  # segundos

    for tentativa in range(1, MAX_TENTATIVAS + 1):
        try:
            print(f"  [{tentativa}/{MAX_TENTATIVAS}] Buscando '{nome}' (série {codigo})...")

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            dados = response.json()
            print(f"  ✓ {len(dados)} registros recebidos")
            return dados

        except requests.exceptions.Timeout:
            print(f"  ✗ Timeout na tentativa {tentativa}")

        except requests.exceptions.HTTPError as e:
            print(f"  ✗ Erro HTTP: {e}")
            # Erro 4xx = problema nos parâmetros, retry não vai resolver
            if response.status_code < 500:
                print(f"  ✗ Erro do cliente (4xx), abortando '{nome}'")
                return None

        except requests.exceptions.ConnectionError:
            print(f"  ✗ Sem conexão na tentativa {tentativa}")

        # Aguarda antes de tentar de novo (exceto na última tentativa)
        if tentativa < MAX_TENTATIVAS:
            print(f"  ⏳ Aguardando {ESPERA_ENTRE_TENTATIVAS}s antes de tentar novamente...")
            time.sleep(ESPERA_ENTRE_TENTATIVAS)

    print(f"  ✗ '{nome}' falhou após {MAX_TENTATIVAS} tentativas")
    return None


def salvar_raw(nome: str, dados: list, data_inicio: str, data_fim: str) -> Path:
    """
    Salva os dados brutos em JSON na pasta data/raw.
    O nome do arquivo inclui a série e o timestamp da extração.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome_arquivo = f"{nome}_{timestamp}.json"
    caminho = RAW_DIR / nome_arquivo

    # Envelope com metadados — sempre salve de onde veio e quando
    payload = {
        "serie": nome,
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "extraido_em": datetime.now().isoformat(),
        "total_registros": len(dados),
        "dados": dados
    }

    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"  💾 Salvo em: {caminho}")
    return caminho


def extrair_todas_as_series(data_inicio: str, data_fim: str) -> dict:
    """
    Extrai todas as séries do catálogo e salva cada uma em raw.
    Retorna um resumo do que funcionou e o que falhou.
    """
    print(f"\n{'='*50}")
    print(f"Iniciando extração: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"Período: {data_inicio} a {data_fim}")
    print(f"{'='*50}\n")

    resultados = {"sucesso": [], "falha": []}

    for nome, codigo in SERIES.items():
        print(f"→ Série: {nome}")

        dados = buscar_serie(nome, codigo, data_inicio, data_fim)

        if dados:
            salvar_raw(nome, dados, data_inicio, data_fim)
            resultados["sucesso"].append(nome)
        else:
            resultados["falha"].append(nome)

        print()  # linha em branco entre séries

    # Resumo final
    print(f"{'='*50}")
    print(f"Extração concluída")
    print(f"  ✓ Sucesso: {len(resultados['sucesso'])} séries → {resultados['sucesso']}")
    print(f"  ✗ Falha:   {len(resultados['falha'])} séries → {resultados['falha']}")
    print(f"{'='*50}\n")

    return resultados


if __name__ == "__main__":
    extrair_todas_as_series(
        data_inicio="01/01/2023",
        data_fim="31/12/2023"
    )