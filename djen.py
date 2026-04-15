"""
djen.py — Busca de publicações no DJEN (Diário de Justiça Eletrônico Nacional)

Estratégia de fallback:
  1. Tenta a API REST diretamente (rápido).
  2. Se a API bloquear (403/429/conexão recusada — comum em IPs de datacenter),
     usa Playwright para navegar o portal web do DJEN como um navegador real.
"""
import json
import re
import time
import requests
from bs4 import BeautifulSoup

DJEN_API_URL = "https://comunicaapi.pje.jus.br/api/v1/comunicacao"

# Proxy brasileiro (Google Cloud Run — southamerica-east1 São Paulo)
# Usado quando o servidor está fora do Brasil e a API bloqueia o IP
DJEN_PROXY_URL = "https://djen-proxy-201961766759.southamerica-east1.run.app/api/v1/comunicacao"

# Mapa legado (mantido para compatibilidade)
ORGAOS = {'1': 69475, '2': 69559, '3': 69642}

# Lookup id → nome para exibição nos logs
_NOMES_ORGAOS = {
    # Turmas Recursais
    69475: "1ª Turma Recursal",
    69559: "2ª Turma Recursal",
    69642: "3ª Turma Recursal",
    69560: "4ª Turma Recursal - Fazenda",
    # Câmaras / Tribunal
    69474: "Primeira Câmara Cível",
    69470: "Segunda Câmara Cível",
    69466: "Terceira Câmara Cível",
    69476: "Câmaras Reunidas",
    69469: "Câmara Criminal",
    69467: "Tribunal Pleno",
    69484: "Secretaria Judiciária de Recursos",
    # Juizados Especiais — Manaus
    44842: "1º JE Cível Manaus",  46577: "2º JE Cível Manaus",
    46658: "3º JE Cível Manaus",  44235: "4º JE Cível Manaus",
    46551: "5º JE Cível Manaus",  51675: "6º JE Cível Manaus",
    51775: "7º JE Cível Manaus",  42290: "8º JE Cível Manaus",
    44233: "9º JE Cível Manaus",  44331: "10º JE Cível Manaus",
    44272: "11º JE Cível Manaus", 44256: "12º JE Cível Manaus",
    44349: "13º JE Cível Manaus", 44230: "14º JE Cível Manaus",
    51133: "15º JE Cível Manaus", 44241: "16º JE Cível Manaus",
    51209: "17º JE Cível Manaus", 42896: "18º JE Cível Manaus",
    42871: "19º JE Cível Manaus", 42879: "20º JE Cível Manaus",
    50064: "21º JE Cível Manaus", 51667: "22º JE Cível Manaus",
    49348: "23º JE Cível Manaus",
    51773: "1º JE Criminal Manaus", 52088: "2º JE Criminal Manaus",
    51774: "1º JE Fazenda Manaus",  51782: "2º JE Fazenda Manaus",
    51781: "3º JE Fazenda Manaus",  44546: "CEJUSC Cível Manaus",
    # Varas Cíveis — Manaus
    61706: "1ª Vara Cível Manaus",  61803: "2ª Vara Cível Manaus",
    61700: "3ª Vara Cível Manaus",  61622: "4ª Vara Cível Manaus",
    51210: "5ª Vara Cível Manaus",  51668: "6ª Vara Cível Manaus",
    51670: "7ª Vara Cível Manaus",  61742: "8ª Vara Cível Manaus",
    61663: "9ª Vara Cível Manaus",  61715: "10ª Vara Cível Manaus",
    61716: "11ª Vara Cível Manaus", 61753: "12ª Vara Cível Manaus",
    71138: "13ª Vara Cível Manaus", 61713: "14ª Vara Cível Manaus",
    61702: "16ª Vara Cível Manaus", 51676: "17ª Vara Cível Manaus",
    61704: "18ª Vara Cível Manaus", 52165: "19ª Vara Cível Manaus",
    61662: "20ª Vara Cível Manaus", 61714: "21ª Vara Cível Manaus",
    60939: "22ª Vara Cível Manaus", 61744: "23ª Vara Cível Manaus",
    # Varas de Família — Manaus
    61634: "1ª Vara Família Manaus", 64950: "2ª Vara Família Manaus",
    73709: "3ª Vara Família Manaus", 63940: "4ª Vara Família Manaus",
    61659: "5ª Vara Família Manaus", 61665: "6ª Vara Família Manaus",
    61752: "7ª Vara Família Manaus", 61635: "8ª Vara Família Manaus",
    61692: "9ª Vara Família Manaus",
    # Varas da Fazenda — Manaus
    69478: "1ª Vara Fazenda Manaus", 67395: "2ª Vara Fazenda Manaus",
    65080: "3ª Vara Fazenda Manaus", 71078: "3ª Vara Fazenda/Saúde Manaus",
    69564: "4ª Vara Fazenda Manaus",
}

# Headers que imitam um navegador — evitam bloqueio por User-Agent
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://pje.jus.br/",
    "Origin": "https://pje.jus.br",
    "Connection": "keep-alive",
}

# Códigos HTTP que indicam bloqueio de IP/rate-limit (vale tentar fallback)
# 400 NÃO entra aqui: é "bad request" (parâmetro inválido ou sem resultados),
# não bloqueio — cair no fallback apenas desperdiça tempo e mascara o problema.
_CODIGOS_BLOQUEIO = {403, 429, 503, 502}


def limpar_html(texto):
    if not texto or not isinstance(texto, str):
        return ""
    limpo = BeautifulSoup(texto, "html.parser").get_text(" ", strip=True)
    return re.sub(r'[\000-\010\013-\014\016-\037]', "", limpo)


# ══════════════════════════════════════════════════════════════
# BUSCA VIA API REST
# ══════════════════════════════════════════════════════════════

def _buscar_via_api(params, usar_proxy=False):
    """
    Faz a busca paginada via API REST.
    Retorna (lista, bloqueado):
      - lista: itens encontrados (pode ser [] se bloqueado)
      - bloqueado: True se recebeu resposta de bloqueio
    """
    url = DJEN_PROXY_URL if usar_proxy else DJEN_API_URL
    lista = []
    pagina = 1
    while True:
        params['pagina'] = pagina
        try:
            r = requests.get(
                url, params=params,
                headers=_HEADERS, timeout=30,
            )
        except requests.exceptions.ConnectionError:
            return lista, True
        except requests.exceptions.Timeout:
            return lista, True
        except Exception:
            return lista, True

        if r.status_code in _CODIGOS_BLOQUEIO:
            return lista, True
        if r.status_code != 200:
            break

        try:
            dados = r.json()
        except Exception:
            break

        itens = dados.get('items', [])
        if not itens:
            break

        for i in itens:
            lista.append(_normalizar_item(i))

        pagina += 1
        time.sleep(0.3)

    return lista, False


# ══════════════════════════════════════════════════════════════
# BUSCA VIA PLAYWRIGHT (fallback)
# ══════════════════════════════════════════════════════════════

def _buscar_via_playwright(nome_adv, data_ini, data_fim, orgao_id):
    """
    Navega o portal web do DJEN usando Playwright para contornar bloqueio
    de IP de datacenter. Retorna lista de itens no mesmo formato da API.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return []

    # URL da API interna usada pelo portal — pode ser chamada via fetch do browser
    api_url = DJEN_API_URL
    resultados = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
            ],
        )
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="pt-BR",
            extra_http_headers={
                "Accept-Language": "pt-BR,pt;q=0.9",
            },
        )
        page = context.new_page()

        # Remove flag de webdriver para não ser detectado como bot
        page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        pagina = 1
        while True:
            params_str = (
                f"nomeAdvogado={requests.utils.quote(nome_adv)}"
                f"&dataDisponibilizacaoInicio={data_ini}"
                f"&dataDisponibilizacaoFim={data_fim}"
                f"&siglaTribunal=TJAM"
                f"&itensPorPagina=100"
                f"&meio=D"
                f"&pagina={pagina}"
            )
            if orgao_id:
                params_str += f"&orgaoId={orgao_id}"

            url_fetch = f"{api_url}?{params_str}"
            try:
                resp = page.evaluate(f"""
                    async () => {{
                        const r = await fetch({repr(url_fetch)}, {{
                            headers: {{
                                'Accept': 'application/json',
                                'Accept-Language': 'pt-BR,pt;q=0.9',
                            }}
                        }});
                        return {{ status: r.status, body: await r.text() }};
                    }}
                """)
            except Exception:
                break

            if resp.get('status') != 200:
                break

            try:
                dados = json.loads(resp.get('body', '{}'))
            except Exception:
                break

            itens = dados.get('items', [])
            if not itens:
                break

            for i in itens:
                resultados.append(_normalizar_item(i))

            pagina += 1
            time.sleep(0.5)

        context.close()
        browser.close()

    return resultados


# ══════════════════════════════════════════════════════════════
# NORMALIZAÇÃO DE ITEM
# ══════════════════════════════════════════════════════════════

def _normalizar_item(i):
    num = i.get('numero_processo', '')
    num_fmt = (
        f"{num[:7]}-{num[7:9]}.{num[9:13]}.{num[13]}.{num[14:16]}.{num[16:]}"
        if len(num) == 20 else num
    )
    data = i.get('data_disponibilizacao', '')
    data_fmt = (
        f"{data[8:10]}/{data[5:7]}/{data[0:4]}" if len(data) == 10 else data
    )
    texto_pub = limpar_html(
        i.get('texto', '') or i.get('conteudo', '') or
        i.get('textoPublicacao', '') or ''
    )
    return {
        'PROCESSO':   num_fmt,
        'turma_djen': i.get('nomeOrgao', '').upper(),
        'data_pub':   data_fmt,
        'texto':      texto_pub,
    }


# ══════════════════════════════════════════════════════════════
# PONTO DE ENTRADA PÚBLICO
# ══════════════════════════════════════════════════════════════

def buscar(nome_adv, data_ini, data_fim, opcao_turma, log=None):
    """
    Retorna lista de dicts com processos do DJEN.

    opcao_turma: '0' = todas, '1'/'2'/'3' = turmas específicas (legado),
                 orgaoId numérico (ex: 69475),
                 ou lista/string separada por vírgula com múltiplos IDs
                 (ex: '69475,69559' ou [69475, 69559]).

    Tenta primeiro via API REST com headers de navegador.
    Se bloqueado (IP de datacenter / cloud), usa Playwright como fallback.
    """
    def _log(msg):
        if log:
            log(msg)

    orgao_ids = _resolver_orgaos(opcao_turma)

    # Sem filtro de órgão — busca única
    if not orgao_ids:
        resultado = _buscar_orgao(nome_adv, data_ini, data_fim, None)
        _log(f"   📋 DJEN (todos os órgãos): {len(resultado)} publicação(ões)")
        return resultado

    # Múltiplos órgãos — uma requisição por órgão, resultados mesclados
    vistos      = set()
    resultado   = []
    # Nomes reais que a API retornou para cada órgão (aprendidos dos resultados)
    nomes_reais = set()

    for oid in orgao_ids:
        itens = _buscar_orgao(nome_adv, data_ini, data_fim, oid)
        nome_orgao = (
            itens[0].get('turma_djen') if itens
            else _NOMES_ORGAOS.get(oid, str(oid))
        )
        if itens:
            nomes_reais.add(itens[0].get('turma_djen', ''))
        novos = 0
        for item in itens:
            proc = item.get('PROCESSO', '')
            if proc and proc not in vistos:
                vistos.add(proc)
                resultado.append(item)
                novos += 1
        _log(f"   📋 DJEN {nome_orgao}: {len(itens)} publicação(ões), {novos} nova(s)")

    # Busca global complementar: captura publicações indexadas sob órgão-pai
    # que não aparecem nas buscas por orgaoId específico
    nomes_alvo = {_NOMES_ORGAOS.get(oid, '').upper() for oid in orgao_ids}
    nomes_alvo |= nomes_reais          # adiciona os nomes reais aprendidos da API
    nomes_alvo.discard('')

    if nomes_alvo:
        _log(f"   🔍 DJEN buscando complemento global...")
        todos = _buscar_orgao(nome_adv, data_ini, data_fim, None)
        complementares = 0
        for item in todos:
            proc  = item.get('PROCESSO', '')
            turma = item.get('turma_djen', '')
            if proc and proc not in vistos and turma in nomes_alvo:
                vistos.add(proc)
                resultado.append(item)
                complementares += 1
        if complementares:
            _log(f"   📋 DJEN complemento global: +{complementares} processo(s) adicional(is)")
        else:
            _log(f"   📋 DJEN complemento global: nenhum adicional encontrado")

    _log(f"   📋 DJEN total: {len(resultado)} processo(s) únicos")
    return resultado


def _resolver_orgaos(opcao_turma):
    """Converte opcao_turma em lista de orgaoIds inteiros (vazia = todos)."""
    if opcao_turma is None:
        return []
    # Já é lista
    if isinstance(opcao_turma, (list, tuple)):
        ids = []
        for v in opcao_turma:
            try:
                ids.append(int(v))
            except (ValueError, TypeError):
                leg = ORGAOS.get(str(v))
                if leg:
                    ids.append(leg)
        return ids
    # String
    s = str(opcao_turma).strip()
    if s in ('0', '', 'None'):
        return []
    # Vírgula separada
    partes = [p.strip() for p in s.split(',') if p.strip()]
    ids = []
    for p in partes:
        try:
            ids.append(int(p))
        except (ValueError, TypeError):
            leg = ORGAOS.get(p)
            if leg:
                ids.append(leg)
    return ids


def _buscar_orgao(nome_adv, data_ini, data_fim, orgao_id):
    """Busca publicações para um único órgão (ou todos se orgao_id=None)."""
    params = {
        'nomeAdvogado':               nome_adv,
        'dataDisponibilizacaoInicio': data_ini,
        'dataDisponibilizacaoFim':    data_fim,
        'siglaTribunal':              'TJAM',
        'itensPorPagina':             100,
        'meio':                       'D',
    }
    if orgao_id:
        params['orgaoId'] = orgao_id

    # 1ª tentativa: API REST direta
    lista, bloqueado = _buscar_via_api(params)
    if not bloqueado:
        return lista

    # 2ª tentativa: proxy brasileiro
    lista, bloqueado = _buscar_via_api(params, usar_proxy=True)
    if not bloqueado:
        return lista

    # 3ª tentativa: Playwright
    return _buscar_via_playwright(nome_adv, data_ini, data_fim, orgao_id)
