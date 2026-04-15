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
]


def _cfg():
    c = configparser.ConfigParser()
    c.read(CONFIG_PATH, encoding='utf-8')
    return c


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
        rows_clean.append({col: linha.get(col, '') for col in COLUNAS_SHEETS})

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
