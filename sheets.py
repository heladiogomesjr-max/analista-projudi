"""
sheets.py — Integração com Google Sheets via Apps Script (doPost)

Uso:
    from sheets import inserir_na_planilha
    inserir_na_planilha([linha_dict], turma_vara="1ª Turma Recursal",
                        advogado_key="luis_albert", log=print)
"""
import configparser
import os
import requests

PASTA = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(PASTA, 'config.ini')

COLUNAS_SHEETS = [
    'NÚMERO DO PROCESSO',
    'DATA DA DECISÃO',
    'RELATOR/JUIZ',
    'STATUS DA DECISÃO',
    'MATÉRIA',
    'DANO MATERIAL',
    'DANO MORAL',
    'RESUMO DO PROCESSO',
    'TRANSITADO EM JULGADO?',
]

# Mapeamento de nome da coluna no Sheets → chave no dict do worker
_ALIAS_COLUNAS = {
    'TRANSITADO EM JULGADO?': 'TRANSITADO EM JULGADO? (SIM OU NÃO)',
}


def _cfg():
    c = configparser.ConfigParser()
    c.read(CONFIG_PATH, encoding='utf-8')
    return c


def ler_da_planilha(advogado_key=None, log=None):
    """
    Lê todos os processos já analisados do Google Sheets via Apps Script doGet.
    Retorna lista de dicts com chaves: p, d, r, s, mt, dm, mo, tv, tj
    """
    if log is None:
        log = print

    cfg = _cfg()
    if not advogado_key:
        advogado_key = cfg.get('sheets', 'advogado_padrao', fallback='luis_albert')

    url = cfg.get('sheets', 'apps_script_url', fallback='').strip()
    if not url or url.startswith('#'):
        log("   ⚠️ Sheets: URL do Apps Script não configurada em config.ini → [sheets] apps_script_url")
        return []

    adv = advogado_key.upper().replace(' ', '_')
    try:
        resp = requests.get(url, params={'adv': adv}, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        if result.get('ok'):
            rows = result.get('data', [])
            log(f"   📊 Sheets: {len(rows)} processos lidos ({adv})")
            return rows
        else:
            log(f"   ⚠️ Sheets: {result.get('error', 'erro desconhecido')}")
            return []
    except requests.exceptions.Timeout:
        log("   ⚠️ Sheets: timeout ao ler do Google Sheets (30s)")
        return []
    except Exception as e:
        log(f"   ⚠️ Sheets: falha ao ler — {e}")
        return []


def inserir_na_planilha(linhas, turma_vara, advogado_key=None, log=None, modo='append'):
    """
    Envia linhas para a planilha Google Sheets via Apps Script doPost.

    Parâmetros
    ----------
    linhas        : list[dict]   — lista de processos (colunas do workers.py)
    turma_vara    : str          — nome da aba de destino (ex: "1ª Turma Recursal")
    advogado_key  : str          — seção do config.ini (ex: "luis_albert")
    log           : callable     — função de log (default: print)
    modo          : 'append' | 'replace'
    """
    if log is None:
        log = print

    cfg = _cfg()

    if not advogado_key:
        advogado_key = cfg.get('sheets', 'advogado_padrao', fallback='luis_albert')

    url = cfg.get('sheets', 'apps_script_url', fallback='').strip()
    if not url or url.startswith('#'):
        log("   ⚠️ Sheets: URL do Apps Script não configurada em config.ini → [sheets] apps_script_url")
        return False

    sheet_id = ''
    if cfg.has_section(advogado_key):
        sheet_id = cfg.get(advogado_key, 'sheet_id', fallback='').strip()

    rows_clean = []
    for linha in linhas:
        proc = str(linha.get('NÚMERO DO PROCESSO') or '').strip()
        if not proc:
            continue
        rows_clean.append({
            col: linha.get(col) or linha.get(_ALIAS_COLUNAS.get(col, col), '')
            for col in COLUNAS_SHEETS
        })

    if not rows_clean:
        return True

    payload = {
        'adv':      advogado_key.upper().replace(' ', '_'),
        'tab':      turma_vara or 'Geral',
        'rows':     rows_clean,
        'modo':     modo,
    }
    if sheet_id:
        payload['sheet_id'] = sheet_id

    try:
        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        if result.get('ok'):
            ins = result.get('inseridos', len(rows_clean))
            dup = result.get('duplicatas', 0)
            msg = f"   📊 Sheets: {ins} inserido(s) na aba '{turma_vara}'"
            if dup:
                msg += f" ({dup} duplicata(s) ignorada(s))"
            log(msg)
            return True
        else:
            log(f"   ⚠️ Sheets: {result.get('error', 'erro desconhecido')}")
            return False
    except requests.exceptions.Timeout:
        log("   ⚠️ Sheets: timeout ao conectar ao Apps Script (30s)")
        return False
    except Exception as e:
        log(f"   ⚠️ Sheets: falha ao inserir — {e}")
        return False


COLUNAS_DIST = [
    'NÚMERO DO PROCESSO',
    'DATA DE DISTRIBUIÇÃO',
    'RELATOR',
    'TURMA/CÂMARA',
    'CLASSE',
    'STATUS DO JULGAMENTO',
    'DATA DE CAPTURA',
]


def inserir_distribuicoes(processos, advogado_key=None, log=None):
    """Envia processos recursais ativos para a aba 'Distribuições 2G' do Sheets."""
    if log is None:
        log = print
    cfg = _cfg()
    if not advogado_key:
        advogado_key = cfg.get('sheets', 'advogado_padrao', fallback='luis_albert')
    url = cfg.get('sheets', 'apps_script_url', fallback='').strip()
    if not url or url.startswith('#'):
        log("   ⚠️ Sheets: URL do Apps Script não configurada.")
        return False
    sheet_id = ''
    if cfg.has_section(advogado_key):
        sheet_id = cfg.get(advogado_key, 'sheet_id', fallback='').strip()

    rows_clean = [
        {col: p.get(col, '') for col in COLUNAS_DIST}
        for p in processos
        if str(p.get('NÚMERO DO PROCESSO') or '').strip()
    ]
    if not rows_clean:
        return True

    base_payload = {
        'adv':  advogado_key.upper().replace(' ', '_'),
        'tab':  'Distribuições 2G',
        'modo': 'upsert',
        'tipo': 'distribuicoes',
    }
    if sheet_id:
        base_payload['sheet_id'] = sheet_id

    CHUNK = 100
    total_chunks = (len(rows_clean) + CHUNK - 1) // CHUNK
    ok_count = 0
    for i in range(0, len(rows_clean), CHUNK):
        chunk = rows_clean[i:i + CHUNK]
        chunk_num = i // CHUNK + 1
        payload = dict(base_payload)
        payload['rows']       = chunk
        payload['batch_mode'] = 'replace_first' if chunk_num == 1 else 'append_rest'
        payload['cleanup']    = (chunk_num == total_chunks)
        try:
            resp = requests.post(url, json=payload, timeout=180)
            resp.raise_for_status()
            result = resp.json()
            if result.get('ok'):
                ok_count += result.get('inseridos', len(chunk))
                log(f"   📊 Sheets lote {chunk_num}/{total_chunks}: {result.get('inseridos', len(chunk))} rows ✓")
            else:
                log(f"   ⚠️ Sheets lote {chunk_num}/{total_chunks}: {result.get('error', 'erro')}")
                return False
        except Exception as e:
            log(f"   ⚠️ Sheets (distribuições) lote {chunk_num}/{total_chunks}: {e}")
            return False

    log(f"   📊 Distribuições: {ok_count} row(s) em {total_chunks} lote(s).")
    return True


def ler_distribuicoes(advogado_key=None, log=None):
    """Lê processos da aba 'Distribuições 2G' do Sheets."""
    if log is None:
        log = lambda *a: None
    cfg = _cfg()
    if not advogado_key:
        advogado_key = cfg.get('sheets', 'advogado_padrao', fallback='luis_albert')
    url = cfg.get('sheets', 'apps_script_url', fallback='').strip()
    if not url or url.startswith('#'):
        return []
    adv = advogado_key.upper().replace(' ', '_')
    try:
        resp = requests.get(url, params={'adv': adv, 'action': 'distribuicoes'}, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        if result.get('ok'):
            return {
                'data':          result.get('data', []),
                'updatedAt':     result.get('updatedAt'),
                'totalJulgados': result.get('totalJulgados', 0),
            }
        return {'data': [], 'updatedAt': None, 'totalJulgados': 0}
    except Exception:
        return {'data': [], 'updatedAt': None}
