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
    vistos    = set()
    resultado = []
    for oid in orgao_ids:
        itens = _buscar_orgao(nome_adv, data_ini, data_fim, oid)
        novos = 0
        for item in itens:
            proc = item.get('PROCESSO', '')
            if proc and proc not in vistos:
                vistos.add(proc)
                resultado.append(item)
                novos += 1
        _log(f"   📋 DJEN órgão {oid}: {len(itens)} publicação(ões), {novos} nova(s)")
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
