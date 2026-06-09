import requests
from datetime import datetime

BCB_BASE_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"

def buscar_serie(codigo: int, data_inicio: str, data_fim: str) -> list:
    """
    Busca uma série temporal do Banco Central.

    codigo: código da série (ex: 433 = IPCA mensal)
    data_inicio / data_fim: formato DD/MM/YYYY
    """
    url = BCB_BASE_URL.format(codigo=codigo)

    params = {
        "formato": "json",
        "dataInicial": data_inicio,
        "dataFinal": data_fim
    }

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Buscando série {codigo}...")

    response = requests.get(url, params=params, timeout=10)

    # Se a API retornar erro (404, 500, etc), isso lança uma exceção
    response.raise_for_status()

    dados = response.json()
    print(f"✓ {len(dados)} registros recebidos")

    return dados


# Esse bloco só roda quando você executa esse arquivo diretamente
if __name__ == "__main__":
    dados_ipca = buscar_serie(
        codigo=433,            # IPCA mensal
        data_inicio="01/01/2023",
        data_fim="31/12/2023"
    )

    print("\nPrimeiros 3 registros:")
    for registro in dados_ipca[:3]:
        print(registro)