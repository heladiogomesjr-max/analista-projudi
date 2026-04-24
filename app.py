"""
app.py — Servidor Flask (interface web)
Execução: python app.py  →  http://127.0.0.1:5001
"""
import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

import os, uuid, time, threading, configparser, secrets
from collections import Counter
from functools import wraps
from flask import Flask, request, render_template_string, jsonify, send_file, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash

# ══════════════════════════════════════════════════════════════
# DADOS ESTÁTICOS — ÓRGÃOS TJAM E RELATORES
# ══════════════════════════════════════════════════════════════
_ORGAOS_TURMAS = [
    (69475, "1ª Turma Recursal"),
    (69559, "2ª Turma Recursal"),
    (69642, "3ª Turma Recursal"),
    (69560, "4ª Turma Recursal - Fazenda"),
]

_ORGAOS_CAMARAS = [
    (69474, "Primeira Câmara Cível"),
    (69470, "Segunda Câmara Cível"),
    (69466, "Terceira Câmara Cível"),
    (69476, "Câmaras Reunidas"),
    (69469, "Câmara Criminal"),
    (69467, "Tribunal Pleno"),
    (69484, "Secretaria Judiciária de Recursos"),
]

_ORGAOS_JE_MANAUS = [
    (44842, "1º Juizado Especial Cível da Comarca de Manaus"),
    (46577, "2º Juizado Especial Cível da Comarca de Manaus"),
    (46658, "3º Juizado Especial Cível da Comarca de Manaus"),
    (44235, "4º Juizado Especial Cível da Comarca de Manaus"),
    (46551, "5º Juizado Especial Cível da Comarca de Manaus"),
    (51675, "6º Juizado Especial Cível da Comarca de Manaus"),
    (51775, "7º Juizado Especial Cível da Comarca de Manaus"),
    (42290, "8º Juizado Especial Cível da Comarca de Manaus"),
    (44233, "9º Juizado Especial Cível da Comarca de Manaus"),
    (44331, "10º Juizado Especial Cível da Comarca de Manaus"),
    (44272, "11º Juizado Especial Cível da Comarca de Manaus"),
    (44256, "12º Juizado Especial Cível da Comarca de Manaus"),
    (44349, "13º Juizado Especial Cível da Comarca de Manaus"),
    (44230, "14º Juizado Especial Cível da Comarca de Manaus"),
    (51133, "15º Juizado Especial Cível da Comarca de Manaus"),
    (44241, "16º Juizado Especial Cível da Comarca de Manaus"),
    (51209, "17º Juizado Especial Cível da Comarca de Manaus"),
    (42896, "18º Juizado Especial Cível da Comarca de Manaus"),
    (42871, "19º Juizado Especial Cível da Comarca de Manaus"),
    (42879, "20º Juizado Especial Cível da Comarca de Manaus"),
    (50064, "21º Juizado Especial Cível da Comarca de Manaus"),
    (51667, "22º Juizado Especial Cível da Comarca de Manaus"),
    (49348, "23º Juizado Especial Cível da Comarca de Manaus"),
    (51773, "1º Juizado Especial Criminal da Comarca de Manaus"),
    (52088, "2º Juizado Especial Criminal da Comarca de Manaus"),
    (51774, "1º Juizado Especial da Fazenda Pública Estadual e Municipal"),
    (51782, "2º Juizado Especial da Fazenda Pública Estadual e Municipal"),
    (51781, "3º Juizado Especial da Fazenda Pública Estadual e Municipal"),
    (44546, "CEJUSC Cível Manaus"),
]

_ORGAOS_VARAS_MANAUS = [
    (61706, "1ª Vara Cível e de Acidentes de Trabalho de Manaus"),
    (61803, "2ª Vara Cível e de Acidentes de Trabalho de Manaus"),
    (61700, "3ª Vara Cível e de Acidentes de Trabalho de Manaus"),
    (61622, "4ª Vara Cível e de Acidentes de Trabalho de Manaus"),
    (51210, "5ª Vara Cível e de Acidentes de Trabalho de Manaus"),
    (51668, "6ª Vara Cível e de Acidentes de Trabalho de Manaus"),
    (51670, "7ª Vara Cível e de Acidentes de Trabalho de Manaus"),
    (61742, "8ª Vara Cível e de Acidentes de Trabalho de Manaus"),
    (61663, "9ª Vara Cível e de Acidentes de Trabalho de Manaus"),
    (61715, "10ª Vara Cível e de Acidentes de Trabalho de Manaus"),
    (61716, "11ª Vara Cível e de Acidentes de Trabalho de Manaus"),
    (61753, "12ª Vara Cível e de Acidentes de Trabalho de Manaus"),
    (71138, "13ª Vara Cível e de Acidentes de Trabalho de Manaus"),
    (61713, "14ª Vara Cível e de Acidentes de Trabalho de Manaus"),
    (61702, "16ª Vara Cível e de Acidentes de Trabalho de Manaus"),
    (51676, "17ª Vara Cível e de Acidentes de Trabalho de Manaus"),
    (61704, "18ª Vara Cível e de Acidentes de Trabalho de Manaus"),
    (52165, "19ª Vara Cível e de Acidentes de Trabalho de Manaus"),
    (61662, "20ª Vara Cível e de Acidentes de Trabalho de Manaus"),
    (61714, "21ª Vara Cível e de Acidentes de Trabalho de Manaus"),
    (60939, "22ª Vara Cível e de Acidentes de Trabalho de Manaus"),
    (61744, "23ª Vara Cível e de Acidentes de Trabalho de Manaus"),
    (61634, "1ª Vara de Família de Manaus"),
    (64950, "2ª Vara de Família (Lúcio Fonte) de Manaus"),
    (73709, "3ª Vara de Família (Azarias Menescal) de Manaus"),
    (63940, "4ª Vara de Família de Manaus"),
    (61659, "5ª Vara de Família (Euza Maria) de Manaus"),
    (61665, "6ª Vara de Família de Manaus"),
    (61752, "7ª Vara de Família de Manaus"),
    (61635, "8ª Vara de Família (Euza Maria) de Manaus"),
    (61692, "9ª Vara de Família de Manaus"),
    (69478, "1ª Vara da Fazenda Pública de Manaus"),
    (67395, "2ª Vara da Fazenda Pública de Manaus"),
    (65080, "3ª Vara da Fazenda Pública de Manaus"),
    (71078, "3ª Vara da Fazenda Pública de Manaus - Saúde"),
    (69564, "4ª Vara da Fazenda Pública de Manaus"),
    (71324, "1ª Vara Criminal de Manaus"),
    (69479, "6ª Vara Criminal de Manaus"),
    (71147, "9ª Vara Criminal de Manaus"),
    (71294, "10ª Vara Criminal de Manaus"),
    (71342, "11ª Vara Criminal de Manaus"),
    (73708, "7ª Vara Criminal de Manaus"),
    (71143, "Vara Especializada do Meio Ambiente de Manaus"),
    (71213, "Vara Especializada da Dívida Ativa Estadual de Manaus"),
    (71379, "Vara Especializada da Dívida Ativa Municipal de Manaus"),
    (61703, "Vara de Registros Públicos de Manaus"),
    (61681, "Vara de Órfãos e Sucessões de Manaus"),
    (61210, "Central de Plantão Cível de Manaus"),
    (48475, "Central de Cartas Precatórias Criminais de Manaus"),
    (71480, "Central de Cartas Precatórias de Manaus - Família"),
    (61893, "Juizado da Infância e Juventude Cível de Manaus"),
    (44546, "CEJUSC Cível Manaus"),
    (65337, "2ª Unidade do 1º Núcleo de Justiça 4.0 - Acidentes do Trabalho"),
    (38346, "2ª Unidade do 2º Núcleo da Justiça 4.0 - Previdenciário"),
    (65274, "1º Juizado Especializado da Violência Doméstica (Maria da Penha) - Manaus"),
    (61743, "2º Juizado Especializado da Violência Doméstica (Maria da Penha) - Manaus"),
    (65273, "3º Juizado Especializado da Violência Doméstica (Maria da Penha) - Manaus"),
    (61680, "4º Juizado Especializado da Violência Doméstica (Maria da Penha) - Manaus"),
    (61573, "5º Juizado Especializado da Violência Doméstica (Maria da Penha) - Manaus"),
    (71137, "6º Juizado Especializado da Violência Doméstica (Maria da Penha) - Manaus"),
    (71583, "Vara de Plantão Maria da Penha - Manaus"),
    (61891, "1ª V.E.C.U.T.E. de Manaus"),
    (65084, "2ª V.E.C.U.T.E. de Manaus"),
    (71293, "3ª V.E.C.U.T.E. de Manaus"),
    (71197, "4ª V.E.C.U.T.E. de Manaus"),
    (71196, "2ª Vara Especializada em Crimes contra a Dignidade Sexual - Manaus"),
    (103876, "Vara de Garantias Inquéritos de Manaus - Criminais"),
    (103882, "Vara de Garantias Inquéritos de Manaus - Interior"),
    (71179, "Vara de Garantias Custódia de Manaus"),
    (71244, "2ª Vara do Tribunal do Júri de Manaus"),
    (73711, "Presidência - Central de Precatórios"),
]

_ORGAOS_INTERIOR = [
    (13599, "1º Juizado Especial da Comarca de Coari"),
    (17717, "1ª Vara da Comarca de Coari - Criminal"),
    (13841, "1ª Vara da Comarca de Coari - Família"),
    (13768, "2ª Vara da Comarca de Coari - Cível"),
    (44849, "2ª Vara da Comarca de Coari - Fazenda Pública"),
    (80887, "1º Juizado Especial da Comarca de Coari - Fazenda Pública"),
    (19856, "1ª Vara da Comarca de Humaitá - Família"),
    (13709, "2ª Vara da Comarca de Humaitá - Cível"),
    (44192, "2ª Vara da Comarca de Humaitá - Fazenda Pública"),
    (13646, "1º Juizado Especial da Comarca de Humaitá"),
    (45241, "2ª Vara da Comarca de Iranduba - Cível"),
    (46516, "2ª Vara da Comarca de Iranduba - JE Cível"),
    (21003, "1ª Vara da Comarca de Itacoatiara - Criminal"),
    (14185, "2ª Vara da Comarca de Itacoatiara - Família"),
    (13789, "3ª Vara da Comarca de Itacoatiara - Cível"),
    (14053, "1º Juizado Especial da Comarca de Itacoatiara"),
    (14063, "1ª Vara da Comarca de Manacapuru - Criminal"),
    (21480, "1º Juizado Especial da Comarca de Manacapuru"),
    (50859, "1º Juizado Especial da Comarca de Manacapuru - Fazenda Pública"),
    (50223, "3ª Vara da Comarca de Manacapuru - Cível"),
    (50734, "3ª Vara da Comarca de Manacapuru - Fazenda Pública"),
    (14254, "1ª Vara da Comarca de Manicoré - Família"),
    (14145, "2ª Vara da Comarca de Manicoré - Cível"),
    (44844, "2ª Vara da Comarca de Manicoré - Fazenda Pública"),
    (16743, "2ª Vara da Comarca de Manicoré - JE Cível"),
    (18098, "1ª Vara da Comarca de Maués - Família"),
    (14298, "2ª Vara da Comarca de Maués - Cível"),
    (15576, "2ª Vara da Comarca de Maués - JE Cível"),
    (13689, "1º Juizado Especial da Comarca de Parintins"),
    (13621, "3ª Vara da Comarca de Parintins - Cível"),
    (13849, "2ª Vara da Comarca de Parintins - Família"),
    (13636, "3ª Vara da Comarca de Parintins - Registros Públicos"),
    (36735, "2ª Vara da Comarca de Parintins - Violência Doméstica"),
    (13705, "1ª Vara da Comarca de Tabatinga - Família"),
    (15715, "2ª Vara da Comarca de Tabatinga - Cível"),
    (13710, "2ª Vara da Comarca de Tabatinga - JE Cível"),
    (13978, "1ª Vara da Comarca de Tefé - Família"),
    (13746, "2ª Vara da Comarca de Tefé - Cível"),
    (13641, "1º Juizado Especial da Comarca de Tefé"),
    (44324, "1º Juizado Especial da Comarca de Tefé - Fazenda Pública"),
    (13615, "Vara Única da Comarca de Anori"),
    (13716, "Vara Única da Comarca de Autazes"),
    (13750, "Vara Única da Comarca de Alvarães"),
    (13767, "Vara Única da Comarca de Alvarães - JE Cível"),
    (40500, "Vara Única da Comarca de Apuí - Criminal"),
    (18158, "Vara Única da Comarca de Benjamin Constant"),
    (35069, "Vara Única da Comarca de Beruri - Criminal"),
    (34256, "Vara Única da Comarca de Beruri - JE Cível"),
    (17907, "Vara Única da Comarca de Boa Vista do Ramos"),
    (16440, "Vara Única da Comarca de Boca do Acre - Criminal"),
    (13612, "Vara Única da Comarca de Boca do Acre - Cível"),
    (13607, "Vara Única da Comarca de Boca do Acre - JE Cível"),
    (14058, "Vara Única da Comarca de Caapiranga"),
    (15525, "Vara Única da Comarca de Canutama"),
    (42252, "Vara Única da Comarca de Careiro Castanho - Criminal"),
    (18937, "Vara Única da Comarca de Careiro Castanho - JE Cível"),
    (17065, "Vara Única da Comarca de Codajás - Criminal"),
    (42226, "Vara Única da Comarca de Codajás - Família"),
    (14296, "Vara Única da Comarca de Eirunepé"),
    (20981, "Vara Única da Comarca de Fonte Boa - Criminal"),
    (17176, "Vara Única da Comarca de Ipixuna"),
    (17616, "Vara Única da Comarca de Itamarati - Criminal"),
    (14301, "Vara Única da Comarca de Itamarati - Cível"),
    (13600, "Vara Única da Comarca de Lábrea"),
    (18490, "Vara Única da Comarca de Manaquiri"),
    (21725, "Vara Única da Comarca de Maraã"),
    (14944, "Vara Única da Comarca de Nhamundá - JE Cível"),
    (44117, "Vara Única da Comarca de Nova Olinda do Norte - Criminal"),
    (42418, "Vara Única da Comarca de Nova Olinda do Norte - Cível"),
    (44460, "Vara Única da Comarca de Nova Olinda do Norte - JE Cível"),
    (13720, "Vara Única da Comarca de Novo Aripuanã - JE Cível"),
    (26634, "Vara Única da Comarca de Presidente Figueiredo - Criminal"),
    (13922, "Vara Única da Comarca de Presidente Figueiredo - Cível"),
    (15533, "Vara Única da Comarca de Rio Preto da Eva - Cível"),
    (14222, "Vara Única da Comarca de Rio Preto da Eva - JE Cível"),
    (61092, "Vara Única da Comarca de Santa Isabel do Rio Negro"),
    (15817, "Vara Única da Comarca de Santo Antônio do Içá - Criminal"),
    (14237, "Vara Única da Comarca de Santo Antônio do Içá - Cível"),
    (17548, "Vara Única da Comarca de São Gabriel da Cachoeira - Cível"),
    (17060, "Vara Única da Comarca de São Gabriel da Cachoeira - JE Cível"),
    (42242, "Vara Única da Comarca de São Paulo de Olivença"),
    (13935, "Vara Única da Comarca de São Sebastião do Uatumã - JE Cível"),
    (13917, "Vara Única da Comarca de Tapauá"),
    (41022, "Vara Única da Comarca de Uarini - Criminal"),
    (15513, "Vara Única da Comarca de Uarini - Cível"),
    (23191, "Vara Única da Comarca de Uarini - JE Cível"),
    (41560, "Polo 3: Vara de Plantão da Comarca de Carauari"),
    (77535, "Polo 3: Vara de Plantão da Comarca de Guajará"),
    (91787, "Polo 3: Vara de Plantão da Comarca de Ipixuna"),
    (41571, "Polo 3: Vara de Plantão da Comarca de Pauini"),
    (92517, "Polo 6: Vara de Plantão da Comarca de Anamã"),
    (40461, "Vara Única da Comarca de Anamã - Violência Doméstica"),
]

_RELATORES_TJAM = [
    "Alexandre Henrique Novaes De Araújo",
    "Antônio Carlos Marinho Bezerra Júnior",
    "Cássio André Borges Dos Santos",
    "Flávio Henrique Albuquerque De Freitas",
    "Francisco Soares De Souza",
    "Jorsenildo Dourado Do Nascimento",
    "Luciana Da Eira Nasser",
    "Luiz Pires De Carvalho Neto",
    "Maria Do Perpétuo Socorro Da Silva Menezes",
    "Sanã Nogueira Almendros De Oliveira",
    "Vicente De Oliveira Rocha Pinheiro",
]


def _build_orgao_select(name):
    """Gera o HTML do <select> de órgãos julgadores com optgroups."""
    def opts(lst):
        return "".join(f'<option value="{oid}">{nome}</option>' for oid, nome in lst)
    return (
        f'<select name="{name}">'
        '<option value="0">— Todos os Órgãos —</option>'
        '<optgroup label="🏛️ Turmas Recursais">'  + opts(_ORGAOS_TURMAS)  + '</optgroup>'
        '<optgroup label="⚖️ Câmaras / Tribunal">' + opts(_ORGAOS_CAMARAS) + '</optgroup>'
        '<optgroup label="🏢 Juizados Especiais — Manaus">' + opts(_ORGAOS_JE_MANAUS) + '</optgroup>'
        '<optgroup label="📋 Varas / Outros — Manaus">'    + opts(_ORGAOS_VARAS_MANAUS) + '</optgroup>'
        '<optgroup label="🗺️ Comarcas do Interior">'       + opts(_ORGAOS_INTERIOR) + '</optgroup>'
        '</select>'
    )


def _build_relator_select(name):
    """Gera o HTML do <select> de relatores."""
    opts = '<option value="">— Todos os Relatores —</option>'
    opts += "".join(f'<option value="{r}">{r}</option>' for r in _RELATORES_TJAM)
    return f'<select name="{name}">{opts}</select>'

import workers
import ia as ia_mod

app  = Flask(__name__)

def _get_secret_key():
    caminho = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.ini")
    cfg = configparser.ConfigParser()
    cfg.read(caminho, encoding="utf-8")
    chave = cfg.get("app_login", "secret_key", fallback="")
    if not chave:
        chave = secrets.token_hex(32)
        if not cfg.has_section("app_login"):
            cfg.add_section("app_login")
        cfg.set("app_login", "secret_key", chave)
        with open(caminho, "w", encoding="utf-8") as f:
            cfg.write(f)
    return chave

app.secret_key = _get_secret_key()
jobs = {}
_job_ativo = None          # job_id do processamento mais recente (in-memory)
_job_ativo_lock = threading.Lock()

PASTA  = os.path.dirname(os.path.abspath(__file__))
OUTPUT = os.path.join(PASTA, "output")
os.makedirs(OUTPUT, exist_ok=True)


# ══════════════════════════════════════════════════════════════
# CONFIGURAÇÃO  (config.ini)
# ══════════════════════════════════════════════════════════════
def _carregar_config():
    cfg = configparser.ConfigParser()
    cfg.read(os.path.join(PASTA, "config.ini"), encoding="utf-8")
    anthropic_key = cfg.get("claude", "api_key", fallback="")
    return {
        "api_key":       anthropic_key,  # legado
        "cpf":           cfg.get("projudi",  "cpf",   fallback=""),
        "senha":         cfg.get("projudi",  "senha", fallback=""),
        "nome_advogado": cfg.get("advogado", "nome",  fallback=""),
        "porta":   cfg.getint("app",  "porta", fallback=5001),
        "api_keys": {
            "anthropic": anthropic_key,
            "openai":    cfg.get("openai",   "api_key", fallback=""),
            "google":    cfg.get("google",   "api_key", fallback=""),
            "groq":      cfg.get("groq",     "api_key", fallback=""),
            "mistral":   cfg.get("mistral",  "api_key", fallback=""),
            "deepseek":  cfg.get("deepseek", "api_key", fallback=""),
            "xai":       cfg.get("xai",      "api_key", fallback=""),
        },
    }


def _get_api_key(provider_selecionado, modelo_ia=""):
    """Resolve a chave pelo provedor selecionado no formulário."""
    cfg = _carregar_config()
    if provider_selecionado:
        chave = cfg["api_keys"].get(provider_selecionado, "").strip()
        if chave:
            return chave
    provider = ia_mod._detectar_provider(modelo_ia) if modelo_ia else "anthropic"
    return cfg["api_keys"].get(provider, "").strip() or cfg["api_key"]


# ══════════════════════════════════════════════════════════════
# GESTÃO DE USUÁRIOS  (config.ini → secção [usuarios])
# ══════════════════════════════════════════════════════════════
def _listar_usuarios():
    """Retorna lista de dicts {cpf, label, nome, djen_nome} cadastrados no config.ini."""
    cfg = configparser.ConfigParser()
    cfg.read(os.path.join(PASTA, "config.ini"), encoding="utf-8")
    usuarios = []
    if cfg.has_section("usuarios"):
        i = 0
        while cfg.has_option("usuarios", f"cpf_{i}"):
            cpf   = cfg.get("usuarios", f"cpf_{i}", fallback="")
            label = cfg.get("usuarios", f"label_{i}", fallback=cpf)
            # Nome completo: tenta nome_i, depois seção do advogado, depois label
            nome  = cfg.get("usuarios", f"nome_{i}", fallback="")
            adv_key = "_".join(label.strip().lower().split()[:2])
            if not nome:
                nome = cfg.get(adv_key, "nome", fallback="") if cfg.has_section(adv_key) else ""
            if not nome:
                nome = label
            # Nome para busca DJEN: campo djen_nome na seção do advogado, fallback para nome
            djen_nome = cfg.get(adv_key, "djen_nome", fallback="") if cfg.has_section(adv_key) else ""
            if not djen_nome:
                djen_nome = nome
            if cpf:
                usuarios.append({"cpf": cpf, "label": label, "nome": nome, "djen_nome": djen_nome})
            i += 1
    return usuarios


def _salvar_usuario(cpf, senha, label="", nome="", sheet_id=""):
    """Salva ou atualiza um usuário na secção [usuarios] do config.ini.
    Também cria/atualiza a seção dedicada [adv_key] com nome e sheet_id."""
    caminho = os.path.join(PASTA, "config.ini")
    cfg = configparser.ConfigParser()
    cfg.read(caminho, encoding="utf-8")
    if not cfg.has_section("usuarios"):
        cfg.add_section("usuarios")

    adv_key = "_".join((label or cpf).strip().lower().split()[:2]) or "advogado"

    # Verifica se CPF já existe (atualiza senha/label/nome)
    i = 0
    while cfg.has_option("usuarios", f"cpf_{i}"):
        if cfg.get("usuarios", f"cpf_{i}") == cpf:
            cfg.set("usuarios", f"senha_{i}", senha)
            if label:
                cfg.set("usuarios", f"label_{i}", label)
            if nome:
                cfg.set("usuarios", f"nome_{i}", nome)
            _salvar_secao_advogado(cfg, adv_key, nome or label, sheet_id)
            with open(caminho, "w", encoding="utf-8") as f:
                cfg.write(f)
            return
        i += 1

    # Novo usuário
    cfg.set("usuarios", f"cpf_{i}",   cpf)
    cfg.set("usuarios", f"senha_{i}", senha)
    cfg.set("usuarios", f"label_{i}", label or cpf)
    if nome:
        cfg.set("usuarios", f"nome_{i}", nome)
    _salvar_secao_advogado(cfg, adv_key, nome or label, sheet_id)
    with open(caminho, "w", encoding="utf-8") as f:
        cfg.write(f)


def _salvar_secao_advogado(cfg, adv_key, nome, sheet_id):
    """Cria ou atualiza a seção [adv_key] com nome completo e sheet_id."""
    if not cfg.has_section(adv_key):
        cfg.add_section(adv_key)
    if nome:
        cfg.set(adv_key, "nome", nome)
    if sheet_id:
        cfg.set(adv_key, "sheet_id", sheet_id)


def _get_senha_usuario(cpf):
    """Retorna a senha de um CPF cadastrado."""
    cfg = configparser.ConfigParser()
    cfg.read(os.path.join(PASTA, "config.ini"), encoding="utf-8")
    if cfg.has_section("usuarios"):
        i = 0
        while cfg.has_option("usuarios", f"cpf_{i}"):
            if cfg.get("usuarios", f"cpf_{i}") == cpf:
                return cfg.get("usuarios", f"senha_{i}", fallback="")
            i += 1
    return ""


def _get_advogado_key(cpf):
    """Mapeia CPF → chave do advogado no config.ini (para integração com Sheets)."""
    cfg = configparser.ConfigParser()
    cfg.read(os.path.join(PASTA, "config.ini"), encoding="utf-8")
    # Percorre [usuarios] para encontrar o label associado ao CPF
    if cfg.has_section("usuarios"):
        i = 0
        while cfg.has_option("usuarios", f"cpf_{i}"):
            if cfg.get("usuarios", f"cpf_{i}") == cpf:
                label = cfg.get("usuarios", f"label_{i}", fallback="")
                # Converte "LUIS ALBERT" → "luis_albert"
                key = label.strip().lower().split()[0:2]
                return "_".join(key) if key else "luis_albert"
            i += 1
    return cfg.get("sheets", "advogado_padrao", fallback="luis_albert")


# ══════════════════════════════════════════════════════════════
# AUTENTICAÇÃO DO APP
# ══════════════════════════════════════════════════════════════
def _get_app_login():
    """Retorna (usuario, senha_hash) do config.ini [app_login]. Cria padrão se não existir."""
    caminho = os.path.join(PASTA, "config.ini")
    cfg = configparser.ConfigParser()
    cfg.read(caminho, encoding="utf-8")
    if not cfg.has_section("app_login"):
        cfg.add_section("app_login")
        cfg.set("app_login", "usuario", "admin")
        cfg.set("app_login", "senha_hash", generate_password_hash("admin123"))
        with open(caminho, "w", encoding="utf-8") as f:
            cfg.write(f)
    return (
        cfg.get("app_login", "usuario",    fallback="admin"),
        cfg.get("app_login", "senha_hash", fallback=""),
    )


def _verificar_login(usuario, senha):
    u, h = _get_app_login()
    return usuario == u and check_password_hash(h, senha)


_LOGIN_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Login — Analista PROJUDI</title>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',Tahoma,Arial,sans-serif;background:#eef2f7;
     color:#1a1a2e;min-height:100vh;display:flex;align-items:center;justify-content:center}
.card{background:#fff;border-radius:16px;box-shadow:0 4px 24px rgba(0,0,0,.10);
      padding:40px 36px;width:100%;max-width:380px}
.logo{text-align:center;margin-bottom:28px}
.logo h1{font-size:1.4rem;font-weight:700;color:#1565c0}
.logo p{font-size:.85rem;color:#6b7280;margin-top:4px}
label{display:block;font-size:.85rem;font-weight:600;color:#374151;margin-bottom:5px}
input{width:100%;padding:10px 14px;border:1.5px solid #d1d5db;border-radius:8px;
      font-size:.95rem;font-family:inherit;color:#1a1a2e;outline:none;
      transition:border-color .2s;margin-bottom:18px}
input:focus{border-color:#1565c0}
.btn{width:100%;padding:12px;background:#1565c0;color:#fff;border:none;
     border-radius:10px;font-size:1rem;font-weight:700;font-family:inherit;
     cursor:pointer;transition:background .2s}
.btn:hover{background:#0d47a1}
.erro{background:#fde8e8;border-left:4px solid #c62828;border-radius:8px;
      padding:10px 14px;font-size:.88rem;color:#c62828;margin-bottom:16px}
</style>
</head>
<body>
<div class="card">
  <div class="logo">
    <h1>⚖️ Analista PROJUDI</h1>
    <p>Acesso restrito</p>
  </div>
  {% if erro %}
  <div class="erro">{{ erro }}</div>
  {% endif %}
  <form method="POST" action="/login">
    <label for="usuario">Usuário</label>
    <input id="usuario" name="usuario" type="text" autocomplete="username"
           placeholder="usuário" required autofocus>
    <label for="senha">Senha</label>
    <input id="senha" name="senha" type="password" autocomplete="current-password"
           placeholder="senha" required>
    <button class="btn" type="submit">Entrar</button>
  </form>
</div>
</body>
</html>"""


# ══════════════════════════════════════════════════════════════
# LIMPEZA AUTOMÁTICA DE JOBS ANTIGOS
# ══════════════════════════════════════════════════════════════
def _cleanup_jobs():
    """Remove jobs finalizados com mais de 4 horas e seus arquivos."""
    while True:
        time.sleep(3600)  # verifica a cada hora
        agora = time.time()
        for job_id in list(jobs.keys()):
            job = jobs.get(job_id, {})
            if job.get('status') not in ('done', 'error', 'cancelled'):
                continue
            if agora - job.get('criado_em', agora) < 4 * 3600:
                continue
            for key in ('file', 'docx_file'):
                f = job.get(key)
                if f and os.path.exists(f):
                    try:
                        os.remove(f)
                    except Exception:
                        pass
            jobs.pop(job_id, None)


# ══════════════════════════════════════════════════════════════
# CSS COMPARTILHADO
# ══════════════════════════════════════════════════════════════
_CSS = """
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',Tahoma,Arial,sans-serif;background:#eef2f7;color:#1a1a2e;min-height:100vh}
.wrap{max-width:860px;margin:0 auto;padding:28px 16px 60px}
h1.title{text-align:center;color:#1a3a5c;font-size:1.5rem;font-weight:700;margin-bottom:4px}
.subtitle{text-align:center;color:#607d8b;font-size:.88rem;margin-bottom:24px}

/* ABAS */
.tabs{display:flex;border-radius:12px 12px 0 0;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.1)}
.tab-btn{flex:1;padding:16px 12px;font-size:.95rem;font-weight:700;font-family:inherit;
         border:none;cursor:pointer;transition:.2s;display:flex;align-items:center;
         justify-content:center;gap:8px}
.tab-btn.djen{background:#d0e8ff;color:#1565c0}
.tab-btn.xlsx{background:#d4edda;color:#2e7d32}
.tab-btn.djen.active{background:#1565c0;color:#fff}
.tab-btn.xlsx.active{background:#2e7d32;color:#fff}
.tab-btn:not(.active):hover{filter:brightness(.94)}
.tab-content{display:none;background:#fff;border-radius:0 0 14px 14px;
             box-shadow:0 4px 18px rgba(0,0,0,.09);padding:28px}
.tab-content.active{display:block}
.tab-desc{font-size:.84rem;color:#607d8b;margin-bottom:20px;padding:10px 14px;
          border-radius:8px;background:#f8fafc;border-left:3px solid #90caf9}
.tab-desc.g{border-left-color:#a5d6a7}

/* FORMULÁRIO */
.lbl{display:block;font-weight:600;font-size:.86rem;margin-bottom:5px;color:#374151}
input[type=text],input[type=password],input[type=date],input[type=number],select{
  width:100%;padding:9px 12px;border:1.5px solid #d1d5db;border-radius:8px;font-size:.92rem;
  font-family:inherit;color:#1a1a2e;background:#fff;outline:none;transition:border-color .2s}
input:focus,select:focus{border-color:#1976d2}
textarea{width:100%;padding:9px 12px;border:1.5px solid #d1d5db;border-radius:8px;font-size:.92rem;
         font-family:inherit;color:#1a1a2e;background:#fff;outline:none;transition:border-color .2s;resize:vertical}
textarea:focus{border-color:#1976d2}
.row{display:flex;gap:12px}.row .fg{flex:1}
.fg{margin-bottom:14px}
.sec{border-radius:10px;padding:14px 16px;margin-bottom:16px}
.sec h3{font-size:.83rem;font-weight:700;margin-bottom:10px;text-transform:uppercase;letter-spacing:.4px}
.sec-blue{background:#e3f2fd;border-left:4px solid #1976d2}.sec-blue h3{color:#1565c0}
.sec-green{background:#e8f5e9;border-left:4px solid #43a047}.sec-green h3{color:#2e7d32}
.sec-gray{background:#f3f4f6;border-left:4px solid #9ca3af}.sec-gray h3{color:#4b5563}
.sec-amber{background:#fff8e1;border-left:4px solid #f9a825}.sec-amber h3{color:#b45309}
.sec-purple{background:#f3e5f5;border-left:4px solid #7b1fa2}.sec-purple h3{color:#6a1b9a}
.upload-lbl{display:block;border:2px dashed #9ca3af;border-radius:10px;padding:26px;
            text-align:center;cursor:pointer;background:#fafcff;transition:.2s}
.upload-lbl:hover{border-color:#2e7d32;background:#e8f5e9}
.upload-lbl input{display:none}
.upload-icon{font-size:1.8rem;margin-bottom:6px}
.fn{display:none;font-family:monospace;background:#e8f5e9;border-radius:6px;
    padding:3px 12px;font-size:.83rem;margin-top:8px}
.btn-submit{display:block;width:100%;padding:13px;font-size:1rem;font-weight:700;
            font-family:inherit;border:none;border-radius:10px;cursor:pointer;
            color:#fff;margin-top:4px;transition:opacity .2s}
.btn-submit:hover{opacity:.88}
.btn-submit.djen{background:#1565c0}
.btn-submit.xlsx{background:#2e7d32}

/* STATUS */
#logbox{background:#1e1e1e;color:#d4edda;font-family:monospace;font-size:.82rem;
        border-radius:8px;padding:16px;min-height:500px;max-height:70vh;overflow-y:auto;white-space:pre-wrap}
.prog-wrap{background:#e5e7eb;border-radius:8px;height:10px;margin-bottom:8px;overflow:hidden}
.prog{height:100%;border-radius:8px;background:#1565c0;width:5%;transition:width .4s;
      background-image:linear-gradient(45deg,rgba(255,255,255,.15)25%,transparent 25%,
        transparent 50%,rgba(255,255,255,.15)50%,rgba(255,255,255,.15)75%,transparent 75%);
      background-size:40px 40px;animation:stripe 1s linear infinite}
@keyframes stripe{0%{background-position:0 0}100%{background-position:40px 0}}
.prog.done{background:#2e7d32;animation:none}
.prog.err{background:#c62828;animation:none}
.prog.cancelled{background:#f57f17;animation:none}
.prog.paused{animation:none}
.status-box{background:#fff;border-radius:14px;box-shadow:0 4px 18px rgba(0,0,0,.09);padding:28px}
.acts{margin-top:20px;display:none;gap:10px;justify-content:center;flex-wrap:wrap}
.btn-act{border-radius:8px;padding:10px 22px;font-weight:700;font-size:.92rem;
         text-decoration:none;display:inline-block;border:none;cursor:pointer;font-family:inherit}
.btn-dl{background:#1565c0;color:#fff}
.btn-docx{background:#7b1fa2;color:#fff}
.btn-dash{background:#00838f;color:#fff}
.btn-new{background:#455a64;color:#fff}
.alert-err{background:#fce4ec;border:1px solid #e57373;border-radius:8px;
           padding:12px 16px;color:#b71c1c;margin-top:12px;font-size:.9rem;display:none}
.toggle-wrap{display:flex;align-items:center;gap:12px;margin-bottom:16px;padding:12px 16px;
             background:#fff;border-radius:10px;border:1.5px solid #e5e7eb}
.toggle-lbl{flex:1;font-weight:600;font-size:.92rem;color:#374151}
.toggle-sub{font-size:.8rem;color:#9ca3af;display:block;margin-top:2px}
.switch{position:relative;display:inline-block;width:48px;height:26px;flex-shrink:0}
.switch input{opacity:0;width:0;height:0}
.slider{position:absolute;cursor:pointer;inset:0;background:#d1d5db;border-radius:26px;transition:.3s}
.slider:before{position:absolute;content:"";height:20px;width:20px;left:3px;bottom:3px;
               background:#fff;border-radius:50%;transition:.3s;box-shadow:0 1px 3px rgba(0,0,0,.2)}
input:checked+.slider{background:#1565c0}
input:checked+.slider:before{transform:translateX(22px)}

/* CONTROLES JOB (pausar/cancelar) */
.job-ctrl{display:flex;gap:10px;justify-content:center;margin-top:14px}
.btn-ctrl{padding:9px 22px;border:none;border-radius:8px;font-weight:700;cursor:pointer;
          font-size:.9rem;font-family:inherit;transition:opacity .2s}
.btn-ctrl:hover{opacity:.85}
.btn-pausar{background:#f57f17;color:#fff}
.btn-cancelar{background:#c62828;color:#fff}

/* SELETOR DE USUÁRIO */
.user-box{background:#f8fafc;border:1.5px solid #e5e7eb;border-radius:10px;
          padding:12px 14px;margin-bottom:14px}
.user-box-title{font-size:.8rem;font-weight:700;color:#6b7280;text-transform:uppercase;
                letter-spacing:.4px;margin-bottom:8px}
.user-sel-row{display:flex;gap:8px;align-items:center}
.user-sel-row select{flex:1}
.btn-sm{padding:7px 13px;border:none;border-radius:7px;font-weight:700;cursor:pointer;
        font-size:.82rem;font-family:inherit;white-space:nowrap}
.btn-sm-blue{background:#1565c0;color:#fff}
.btn-sm-gray{background:#607d8b;color:#fff}
.user-add-panel{display:none;background:#fff;border:1px solid #e5e7eb;border-radius:8px;
                padding:12px;margin-top:10px}
.user-add-panel .add-title{font-size:.84rem;font-weight:700;color:#374151;margin-bottom:8px}
</style>
"""

# ══════════════════════════════════════════════════════════════
# HTML — FRAGMENTO DO SELETOR DE USUÁRIO (reutilizado nos dois forms)
# ══════════════════════════════════════════════════════════════
def _user_selector_html(tab_id):
    return f"""
      <div class="user-box">
        <div class="user-box-title">👤 Usuários salvos</div>
        <div class="user-sel-row">
          <select id="sel-user-{tab_id}" onchange="selecionarUsuario(this,'{tab_id}')">
            <option value="">— Digitar manualmente —</option>
          </select>
          <button type="button" class="btn-sm btn-sm-gray"
                  onclick="toggleAddUser('{tab_id}')">+ Cadastrar</button>
        </div>
        <div class="user-add-panel" id="add-panel-{tab_id}">
          <div class="add-title">Cadastrar novo usuário</div>
          <div class="row">
            <div class="fg">
              <label class="lbl">CPF / Login</label>
              <input type="text" id="new-cpf-{tab_id}" placeholder="000.000.000-00">
            </div>
            <div class="fg">
              <label class="lbl">Senha</label>
              <input type="password" id="new-senha-{tab_id}">
            </div>
          </div>
          <div class="fg">
            <label class="lbl">Nome / Apelido <small style="font-weight:400;color:#9ca3af">(opcional)</small></label>
            <input type="text" id="new-label-{tab_id}" placeholder="Ex: Luis Albert">
          </div>
          <button type="button" class="btn-sm btn-sm-blue" onclick="salvarUsuario('{tab_id}')">
            💾 Salvar
          </button>
        </div>
      </div>
    """


# ══════════════════════════════════════════════════════════════
# HTML — FORMULÁRIO PRINCIPAL
# ══════════════════════════════════════════════════════════════
FORM_HTML = """<!DOCTYPE html>
<html lang="pt-br"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Analista PROJUDI</title>""" + _CSS + """</head><body>
<div class="wrap">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px">
    <div>
      <h1 class="title">⚖️ Analista PROJUDI</h1>
      <p class="subtitle">Análise automática de processos — DECISÃO · TIPO · MATÉRIA · RESUMO</p>
    </div>
    <a href="/logout" style="font-size:.82rem;color:#6b7280;text-decoration:none;
       border:1px solid #d1d5db;border-radius:8px;padding:6px 14px;white-space:nowrap;
       background:#fff;transition:.2s" onmouseover="this.style.background='#f3f4f6'"
       onmouseout="this.style.background='#fff'">Sair</a>
  </div>

  <!-- Banner de job em segundo plano -->
  <div id="banner-job" style="display:none;margin-bottom:18px;padding:14px 18px;
       border-radius:12px;font-size:.9rem;font-weight:600;
       align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px">
    <span id="banner-texto"></span>
    <div style="display:flex;gap:8px;flex-wrap:wrap">
      <a id="banner-btn-status" href="#" style="padding:7px 16px;border-radius:8px;
         background:#1565c0;color:#fff;text-decoration:none;font-size:.85rem;font-weight:700">
        ▶ Retomar Monitoramento
      </a>
      <a id="banner-btn-dl" href="#" style="display:none;padding:7px 16px;border-radius:8px;
         background:#2e7d32;color:#fff;text-decoration:none;font-size:.85rem;font-weight:700">
        📥 Baixar Planilha
      </a>
      <a id="banner-btn-docx" href="#" style="display:none;padding:7px 16px;border-radius:8px;
         background:#6a1b9a;color:#fff;text-decoration:none;font-size:.85rem;font-weight:700">
        📄 Baixar Relatório
      </a>
    </div>
  </div>

  <div class="tabs">
    <button class="tab-btn djen active" onclick="abrirAba('djen',this)">
      🔍 Modo 1 — Busca pelo DJEN
    </button>
    <button class="tab-btn xlsx" onclick="abrirAba('xlsx',this)">
      📂 Modo 2 — Upload de Planilha
    </button>
  </div>

  <!-- ABA DJEN -->
  <div id="aba-djen" class="tab-content active">
    <p class="tab-desc">
      Pesquisa publicações no DJEN pelo nome do advogado e período.
      Para cada processo encontrado, acessa o PROJUDI, extrai as peças e classifica com IA.
    </p>
    <form action="/iniciar_djen" method="POST">

      <div class="sec sec-blue">
        <h3>🔍 Parâmetros DJEN</h3>
        <div class="fg">
          <label class="lbl">Nome do Advogado (busca no DJEN)</label>
          <input type="text" name="nome_adv" required>
        </div>
        <div class="row">
          <div class="fg">
            <label class="lbl">Data de Início</label>
            <input type="date" name="data_ini" required>
          </div>
          <div class="fg">
            <label class="lbl">Data de Fim</label>
            <input type="date" name="data_fim" required>
          </div>
        </div>
        <div class="row">
          <div class="fg">
            <label class="lbl">Órgão Julgador</label>
            """ + _build_orgao_select('turma') + """
          </div>
          <div class="fg">
            <label class="lbl">Relator / Juiz</label>
            """ + _build_relator_select('relator_filtro') + """
          </div>
        </div>
      </div>

      <div class="sec sec-blue">
        <h3>🔑 Credenciais PROJUDI</h3>
        """ + _user_selector_html("djen") + """
        <div class="row">
          <div class="fg">
            <label class="lbl">CPF / Login</label>
            <input type="text" name="cpf" id="cpf-djen" required>
          </div>
          <div class="fg">
            <label class="lbl">Senha</label>
            <input type="password" name="senha" id="senha-djen" required>
          </div>
        </div>
      </div>

      <div class="toggle-wrap">
        <label class="toggle-lbl">
          🧠 Classificação com IA
          <span class="toggle-sub">Desative para extrair dados sem chamar a IA</span>
        </label>
        <label class="switch">
          <input type="checkbox" name="usar_ia" value="1" id="chk-ia-djen" checked
                 onchange="document.getElementById('sec-ia-djen').style.display=this.checked?'':'none'">
          <span class="slider"></span>
        </label>
      </div>

      <div class="sec sec-amber" id="sec-ia-djen">
        <h3>📊 Relatório Analítico</h3>
        <p style="font-size:.84rem;color:#6b7280;margin:0">Ao final da análise, a IA gerará automaticamente um relatório em <strong>.docx</strong> com padrões, tendências por relator, contradições entre julgamentos e recomendações estratégicas.</p>
      </div>

      <button type="submit" class="btn-submit djen">▶ Buscar no DJEN e Analisar</button>
    </form>
  </div>

  <!-- ABA XLSX -->
  <div id="aba-xlsx" class="tab-content">
    <p class="tab-desc g">
      Carregue uma planilha .xlsx com a coluna <strong>PROCESSO</strong> preenchida.
      O sistema pesquisa cada processo no PROJUDI (2º Grau primeiro, depois 1º Grau),
      extrai as peças e classifica com IA.
    </p>
    <form action="/iniciar_xlsx" method="POST" enctype="multipart/form-data">

      <div class="fg">
        <label class="lbl">📋 Números de Processos (um por linha)</label>
        <textarea name="numeros_texto" rows="5"
                  placeholder="Cole ou digite os números aqui, um por linha&#10;Ex:&#10;0001234-56.2025.8.04.1000&#10;0009876-54.2025.8.04.4700"></textarea>
        <div style="color:#6b7280;font-size:.8rem;margin-top:4px">Ou envie uma planilha abaixo (a caixa de texto tem prioridade)</div>
      </div>

      <div class="fg">
        <label class="lbl">📂 Planilha de Processos (.xlsx) <span style="color:#9ca3af;font-weight:400">— opcional se usar caixa acima</span></label>
        <label class="upload-lbl" for="arq">
          <div class="upload-icon">📄</div>
          <div style="font-weight:600;margin-bottom:4px">Clique para selecionar o arquivo</div>
          <div style="color:#6b7280;font-size:.83rem">Coluna obrigatória: <strong>PROCESSO</strong></div>
          <input type="file" id="arq" name="arquivo" accept=".xlsx,.xls"
                 onchange="var s=document.getElementById('fn2');s.textContent=this.files[0].name;s.style.display='inline-block'">
        </label>
        <span id="fn2" class="fn"></span>
      </div>

      <div class="sec sec-green">
        <h3>🔑 Credenciais PROJUDI</h3>
        """ + _user_selector_html("xlsx") + """
        <div class="row">
          <div class="fg">
            <label class="lbl">CPF / Login</label>
            <input type="text" name="cpf" id="cpf-xlsx" required>
          </div>
          <div class="fg">
            <label class="lbl">Senha</label>
            <input type="password" name="senha" id="senha-xlsx" required>
          </div>
        </div>
      </div>

      <div class="sec sec-gray">
        <h3>🔍 Filtros</h3>
        <div class="row">
          <div class="fg">
            <label class="lbl">Relator / Juiz</label>
            """ + _build_relator_select('relator_filtro') + """
          </div>
        </div>
      </div>

      <div class="toggle-wrap">
        <label class="toggle-lbl">
          🧠 Classificação com IA
          <span class="toggle-sub">Desative para extrair dados sem chamar a IA</span>
        </label>
        <label class="switch">
          <input type="checkbox" name="usar_ia" value="1" id="chk-ia-xlsx" checked
                 onchange="document.getElementById('sec-ia-xlsx').style.display=this.checked?'':'none'">
          <span class="slider"></span>
        </label>
      </div>

      <div class="sec sec-amber" id="sec-ia-xlsx">
        <h3>📊 Relatório Analítico</h3>
        <p style="font-size:.84rem;color:#6b7280;margin:0">Ao final da análise, a IA gerará automaticamente um relatório em <strong>.docx</strong> com padrões, tendências por relator, contradições entre julgamentos e recomendações estratégicas.</p>
      </div>

      <button type="submit" class="btn-submit xlsx">▶ Analisar Planilha no PROJUDI</button>
    </form>
  </div>
</div>

<script>
// ── Alternância de abas ──────────────────────────────────────
function abrirAba(id, btn) {
  document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('aba-' + id).classList.add('active');
  btn.classList.add('active');
}

// ── Gestão de usuários ───────────────────────────────────────
window.addEventListener('load', function() {
  fetch('/api/usuarios').then(r => r.json()).then(lista => {
    ['djen','xlsx'].forEach(tab => {
      var sel = document.getElementById('sel-user-' + tab);
      lista.forEach(function(u) {
        var opt = document.createElement('option');
        opt.value = u.cpf;
        opt.textContent = u.label || u.cpf;
        opt.dataset.djenNome = u.djen_nome || u.nome || u.label || '';
        sel.appendChild(opt);
      });
    });
  }).catch(function(){});
});

function selecionarUsuario(sel, tab) {
  if (!sel.value) return;
  // Auto-preenche nome_adv no formulário DJEN com o nome correto para a API
  if (tab === 'djen') {
    var opt = sel.options[sel.selectedIndex];
    var nomeAdv = document.querySelector('[name="nome_adv"]');
    if (nomeAdv && opt.dataset.djenNome) nomeAdv.value = opt.dataset.djenNome;
  }
  fetch('/api/usuario_senha?cpf=' + encodeURIComponent(sel.value))
    .then(r => r.json())
    .then(function(d) {
      document.getElementById('cpf-' + tab).value   = sel.value;
      document.getElementById('senha-' + tab).value = d.senha || '';
    });
}

function toggleAddUser(tab) {
  var p = document.getElementById('add-panel-' + tab);
  p.style.display = (p.style.display === 'none' || !p.style.display) ? 'block' : 'none';
}

function salvarUsuario(tab) {
  var cpf   = document.getElementById('new-cpf-' + tab).value.trim();
  var senha = document.getElementById('new-senha-' + tab).value.trim();
  var label = document.getElementById('new-label-' + tab).value.trim();
  if (!cpf || !senha) { alert('CPF e senha são obrigatórios.'); return; }
  fetch('/api/usuarios', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({cpf: cpf, senha: senha, label: label})
  }).then(r => r.json()).then(function(d) {
    if (d.ok) {
      ['djen','xlsx'].forEach(function(t) {
        var sel = document.getElementById('sel-user-' + t);
        var existe = Array.from(sel.options).some(function(o){ return o.value === cpf; });
        if (!existe) {
          var opt = document.createElement('option');
          opt.value = cpf;
          opt.textContent = label || cpf;
          sel.appendChild(opt);
        }
      });
      document.getElementById('add-panel-' + tab).style.display = 'none';
      document.getElementById('new-cpf-' + tab).value   = '';
      document.getElementById('new-senha-' + tab).value = '';
      document.getElementById('new-label-' + tab).value = '';
      alert('Usuário salvo com sucesso!');
    } else {
      alert('Erro: ' + (d.error || 'desconhecido'));
    }
  }).catch(function(){ alert('Erro ao salvar usuário.'); });
}

// ── Banner de job em segundo plano ────────────────────────────
(function verificarJobAtivo() {
  fetch('/api/job_ativo')
    .then(function(r) { return r.json(); })
    .then(function(d) {
      var banner = document.getElementById('banner-job');
      if (!d.job_id) { banner.style.display = 'none'; return; }
      banner.style.display = 'flex';
      var texto  = document.getElementById('banner-texto');
      var btnSt  = document.getElementById('banner-btn-status');
      var btnDl  = document.getElementById('banner-btn-dl');
      var btnDoc = document.getElementById('banner-btn-docx');

      btnSt.href = '/status/' + d.job_id;

      if (d.status === 'running') {
        banner.style.background = '#e3f0ff';
        banner.style.border     = '1px solid #90caf9';
        banner.style.color      = '#1a3a6c';
        var pct = d.pct ? (' — ' + d.pct + '%') : '';
        texto.textContent = '⏳ Processamento em andamento' + pct
          + (d.subtitulo ? ' · ' + d.subtitulo : '');
        btnSt.textContent = '▶ Retomar Monitoramento';
      } else if (d.status === 'done') {
        banner.style.background = '#e8f5e9';
        banner.style.border     = '1px solid #a5d6a7';
        banner.style.color      = '#1b5e20';
        texto.textContent = '✅ Processamento concluído — resultado disponível';
        btnSt.textContent = '📊 Ver Status';
        if (d.tem_arquivo) {
          btnDl.href             = '/download/' + d.job_id;
          btnDl.style.display    = 'inline-block';
        }
        if (d.tem_relatorio) {
          btnDoc.href            = '/download_relatorio/' + d.job_id;
          btnDoc.style.display   = 'inline-block';
        }
      } else if (d.status === 'cancelled') {
        banner.style.background = '#fff8e1';
        banner.style.border     = '1px solid #ffe082';
        banner.style.color      = '#5d4037';
        texto.textContent = '⛔ Processamento cancelado — dados parciais disponíveis';
        btnSt.textContent = '📊 Ver Status';
        if (d.tem_arquivo) {
          btnDl.href             = '/download/' + d.job_id;
          btnDl.style.display    = 'inline-block';
        }
      } else {
        banner.style.display = 'none'; // error ou status desconhecido
        return;
      }
    })
    .catch(function() {});
})();
</script>
</body></html>"""


# ══════════════════════════════════════════════════════════════
# HTML — PÁGINA RE-ANÁLISE
# ══════════════════════════════════════════════════════════════
REANALISE_HTML = """<!DOCTYPE html>
<html lang="pt-br"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Re-análise do Sheets</title>""" + _CSS + """
<style>
.form-card{background:#1e1e1e;border-radius:10px;padding:24px;max-width:680px;margin:24px auto;}
.form-card h2{color:#bb86fc;margin-bottom:16px;font-size:1.1rem;}
label{display:block;color:#aaa;font-size:.85rem;margin-bottom:4px;margin-top:14px;}
select,textarea{width:100%;background:#121212;color:#e0e0e0;border:1px solid #333;
  border-radius:6px;padding:8px 10px;font-size:.9rem;box-sizing:border-box;}
textarea{min-height:90px;resize:vertical;font-family:monospace;}
.checks{display:flex;flex-wrap:wrap;gap:8px;margin-top:6px;}
.checks label{display:flex;align-items:center;gap:5px;color:#ddd;font-size:.85rem;
  background:#2a2a2a;border-radius:5px;padding:5px 10px;cursor:pointer;margin:0;}
.checks input{accent-color:#bb86fc;}
.hint{font-size:.75rem;color:#888;margin-top:4px;}
.btn-go{margin-top:20px;width:100%;padding:11px;background:#bb86fc;color:#000;
  border:none;border-radius:7px;font-size:.95rem;font-weight:700;cursor:pointer;}
.btn-go:hover{background:#ce93d8;}
.back{display:inline-block;margin:16px auto 0;color:#888;font-size:.82rem;text-decoration:none;}
.back:hover{color:#ddd;}
.sep{border:none;border-top:1px solid #2a2a2a;margin:18px 0;}
</style>
</head><body>
<div class="wrap">
  <h1 class="title">🔄 Re-análise do Sheets</h1>
  <p class="subtitle">Lê processos já analisados, re-processa com o prompt atual e atualiza o Sheets</p>

  <form method="POST" action="/iniciar_reanalise">
  <div class="form-card">
    <h2>👤 Usuário</h2>
    <label>Credenciais PROJUDI</label>
    <select name="cpf" id="sel-cpf" onchange="atualizarSenha()">
      {% for u in usuarios %}
      <option value="{{ u.cpf }}">{{ u.label }}</option>
      {% endfor %}
    </select>
    <input type="hidden" name="senha" id="inp-senha">
  </div>

  <div class="form-card">
    <h2>🔍 Filtros (deixe tudo desmarcado para re-analisar todos)</h2>

    <label>Filtrar por MATÉRIA</label>
    <div class="checks">
      {% for m in materias %}
      <label><input type="checkbox" name="filtro_materia" value="{{ m }}"> {{ m }}</label>
      {% endfor %}
    </div>

    <hr class="sep">

    <label>Filtrar por STATUS</label>
    <div class="checks">
      {% for s in status_opcoes %}
      <label><input type="checkbox" name="filtro_status" value="{{ s }}"> {{ s }}</label>
      {% endfor %}
    </div>

    <hr class="sep">

    <label>Ou informe processos específicos (um por linha)</label>
    <textarea name="processos_manual" placeholder="0284295-34.2023.8.04.0001&#10;0000943-97.2023.8.04.0001"></textarea>
    <p class="hint">Se preencher esta caixa, os filtros acima são ignorados.</p>
  </div>

  <div class="form-card">
    <button type="submit" class="btn-go">🚀 Iniciar Re-análise em Segundo Plano</button>
  </div>
  </form>

  <div style="text-align:center">
    <a href="/" class="back">← Voltar para a página principal</a>
  </div>
</div>
<script>
const _senhas = {{ senhas_json | safe }};
function atualizarSenha() {
  var cpf = document.getElementById('sel-cpf').value;
  document.getElementById('inp-senha').value = _senhas[cpf] || '';
}
atualizarSenha();
</script>
</body></html>"""


# ══════════════════════════════════════════════════════════════
# HTML — PÁGINA DE STATUS
# ══════════════════════════════════════════════════════════════
STATUS_HTML = """<!DOCTYPE html>
<html lang="pt-br"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Analisando...</title>""" + _CSS + """</head><body>
<div class="wrap">
  <h1 class="title" id="titulo">⏳ Analisando processos...</h1>
  <p class="subtitle" id="sub">Iniciando...</p>
  <div class="status-box">
    <div class="prog-wrap"><div class="prog" id="prog"></div></div>
    <div id="logbox"></div>

    <!-- Botões pausar / cancelar (visíveis enquanto roda) -->
    <div class="job-ctrl" id="ctrl-btns">
      <button class="btn-ctrl btn-pausar" id="btn-pausar" onclick="togglePausa()">
        ⏸️ Pausar
      </button>
      <button class="btn-ctrl btn-cancelar" onclick="cancelarJob()">
        ⛔ Cancelar
      </button>
    </div>

    <!-- Botões de ação finais -->
    <div class="acts" id="acts">
      <a id="btn-dl"   href="#" class="btn-act btn-dl"   style="display:none">📥 Baixar Planilha</a>
      <a id="btn-docx" href="#" class="btn-act btn-docx" style="display:none">📄 Baixar Relatório</a>
      <a id="btn-dash" href="#" class="btn-act btn-dash" style="display:none">📊 Ver Dashboard</a>
      <a href="/"           class="btn-act btn-new">🔄 Nova Análise</a>
    </div>
    <div class="alert-err" id="err"></div>
  </div>
</div>
<script>
const JID="{{ job_id }}";
let idx = 0;
let pausado = false;

const lb = document.getElementById('logbox');

function cor(m) {
  if (m.includes('✅') || m.includes('OK'))     return '<span style="color:#6fcf97">'  + m + '</span>';
  if (m.includes('❌') || m.includes('Erro'))   return '<span style="color:#eb5757">'  + m + '</span>';
  if (m.includes('⚠️'))                         return '<span style="color:#f2c94c">'  + m + '</span>';
  if (m.includes('⏸️') || m.includes('▶️'))     return '<span style="color:#f9a825">'  + m + '</span>';
  if (m.includes('⛔'))                         return '<span style="color:#ef5350">'  + m + '</span>';
  if (m.includes('🤖') || m.includes('🔎') || m.includes('📥'))
                                                return '<span style="color:#56ccf2">'  + m + '</span>';
  if (m.includes('═'))                          return '<span style="color:#bb86fc">'  + m + '</span>';
  return '<span style="color:#d4edda">' + m + '</span>';
}

function poll() {
  fetch('/progresso/' + JID).then(r => r.json()).then(function(d) {
    var atBottom = lb.scrollHeight - lb.scrollTop - lb.clientHeight < 40;
    d.logs.slice(idx).forEach(function(m) { lb.insertAdjacentHTML('beforeend', cor(m) + '\\n'); });
    idx = d.logs.length;
    if (atBottom) lb.scrollTop = lb.scrollHeight;

    var pct = d.pct || 5;
    document.getElementById('prog').style.width = pct + '%';
    document.getElementById('sub').textContent  = d.subtitulo || '';

    // Sincroniza estado de pausa
    if (d.pausado !== undefined) {
      pausado = d.pausado;
      document.getElementById('btn-pausar').textContent = pausado ? '▶️ Retomar' : '⏸️ Pausar';
    }

    if (d.status === 'done') {
      var p = document.getElementById('prog');
      p.style.width = '100%'; p.className = 'prog done';
      document.getElementById('titulo').textContent = '✅ Análise concluída!';
      document.getElementById('sub').textContent = '';
      document.getElementById('ctrl-btns').style.display = 'none';
      if (d.tem_arquivo) {
        var ba = document.getElementById('btn-dl');
        ba.href = '/download/' + JID;
        ba.style.display = 'inline-block';
      }
      if (d.tem_relatorio) {
        var bd = document.getElementById('btn-docx');
        bd.href = '/download_relatorio/' + JID;
        bd.style.display = 'inline-block';
      }
      if (d.tem_linhas) {
        var bda = document.getElementById('btn-dash');
        bda.href = '/dashboard/' + JID;
        bda.style.display = 'inline-block';
      }
      document.getElementById('acts').style.display = 'flex';
      return;
    }

    if (d.status === 'cancelled') {
      var p = document.getElementById('prog');
      p.className = 'prog cancelled';
      document.getElementById('titulo').textContent = '⛔ Processamento cancelado';
      document.getElementById('sub').textContent = '';
      document.getElementById('ctrl-btns').style.display = 'none';
      if (d.tem_arquivo) {
        var ba = document.getElementById('btn-dl');
        ba.href = '/download/' + JID;
        ba.style.display = 'inline-block';
      }
      if (d.tem_relatorio) {
        var bd = document.getElementById('btn-docx');
        bd.href = '/download_relatorio/' + JID;
        bd.style.display = 'inline-block';
      }
      if (d.tem_linhas) {
        var bda = document.getElementById('btn-dash');
        bda.href = '/dashboard/' + JID;
        bda.style.display = 'inline-block';
      }
      document.getElementById('acts').style.display = 'flex';
      return;
    }

    if (d.status === 'error') {
      document.getElementById('prog').className = 'prog err';
      document.getElementById('titulo').textContent = '❌ Erro na análise';
      document.getElementById('ctrl-btns').style.display = 'none';
      var e = document.getElementById('err');
      e.textContent = d.error; e.style.display = 'block';
      if (d.tem_arquivo) {
        var ba = document.getElementById('btn-dl');
        ba.href = '/download/' + JID;
        ba.style.display = 'inline-block';
      }
      if (d.tem_linhas) {
        var bda = document.getElementById('btn-dash');
        bda.href = '/dashboard/' + JID;
        bda.style.display = 'inline-block';
      }
      document.getElementById('acts').style.display = 'flex';
      return;
    }

    setTimeout(poll, 2000);
  }).catch(function() { setTimeout(poll, 3000); });
}

function togglePausa() {
  fetch('/pausar/' + JID, {method: 'POST'})
    .then(r => r.json())
    .then(function(d) {
      pausado = d.pausado;
      document.getElementById('btn-pausar').textContent = pausado ? '▶️ Retomar' : '⏸️ Pausar';
      var p = document.getElementById('prog');
      if (pausado) {
        p.classList.add('paused');
      } else {
        p.classList.remove('paused');
      }
    });
}

function cancelarJob() {
  if (confirm('Cancelar o processamento?\\nOs dados já coletados serão salvos e o relatório será gerado.')) {
    fetch('/cancelar/' + JID, {method: 'POST'});
    // Feedback imediato: desabilita botões e mostra "cancelando"
    var btns = document.querySelectorAll('#ctrl-btns .btn-ctrl');
    btns.forEach(function(b) { b.disabled = true; b.style.opacity = '0.5'; });
    document.getElementById('btn-pausar').textContent = '⛔ Cancelando...';
    document.getElementById('sub').textContent = 'Encerrando processo atual e gerando relatório...';
  }
}

poll();
</script></body></html>"""


# ══════════════════════════════════════════════════════════════
# HTML — DASHBOARD ANALÍTICO
# ══════════════════════════════════════════════════════════════
DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="pt-br"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Dashboard — Analista PROJUDI</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.2/dist/chart.umd.min.js"></script>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',Tahoma,Arial,sans-serif;background:#0f172a;color:#e2e8f0;min-height:100vh}
.dash-wrap{max-width:1100px;margin:0 auto;padding:28px 16px 60px}
.dash-header{display:flex;align-items:center;justify-content:space-between;
             margin-bottom:28px;flex-wrap:wrap;gap:12px}
.dash-header h1{font-size:1.4rem;font-weight:800;color:#f1f5f9}
.dash-header .sub{font-size:.85rem;color:#94a3b8;margin-top:3px}
.btn-row{display:flex;gap:10px;flex-wrap:wrap}
.btn-h{padding:9px 20px;border:none;border-radius:8px;font-weight:700;font-size:.88rem;
       cursor:pointer;text-decoration:none;font-family:inherit;display:inline-block}
.btn-back{background:#334155;color:#f1f5f9}
.btn-dld{background:#1565c0;color:#fff}
.btn-docx{background:#6a1b9a;color:#fff}

/* Cards de resumo */
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px;margin-bottom:28px}
.card{background:#1e293b;border-radius:14px;padding:20px 22px;
      border-left:4px solid #334155;box-shadow:0 2px 12px rgba(0,0,0,.3)}
.card.fav{border-left-color:#22c55e}
.card.desf{border-left-color:#ef4444}
.card.sem{border-left-color:#f59e0b}
.card.total{border-left-color:#3b82f6}
.card-val{font-size:2rem;font-weight:800;line-height:1;margin-bottom:4px}
.card.fav .card-val{color:#22c55e}
.card.desf .card-val{color:#ef4444}
.card.sem .card-val{color:#f59e0b}
.card.total .card-val{color:#3b82f6}
.card-lbl{font-size:.8rem;color:#94a3b8;font-weight:600;text-transform:uppercase;letter-spacing:.5px}
.card-sub{font-size:.78rem;color:#64748b;margin-top:3px}

/* Grid de gráficos */
.charts-top{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:20px}
.chart-box{background:#1e293b;border-radius:14px;padding:20px;
           box-shadow:0 2px 12px rgba(0,0,0,.3)}
.chart-box.full{grid-column:1/-1}
.chart-title{font-size:.9rem;font-weight:700;color:#94a3b8;text-transform:uppercase;
             letter-spacing:.5px;margin-bottom:16px}
.chart-canvas-wrap{position:relative}

@media(max-width:640px){
  .charts-top{grid-template-columns:1fr}
  .chart-box.full{grid-column:auto}
}

/* Tabela de processos */
.proc-section{margin-top:28px}
.proc-section-title{font-size:.95rem;font-weight:700;color:#94a3b8;text-transform:uppercase;
  letter-spacing:.5px;margin-bottom:14px;display:flex;align-items:center;gap:8px}
.proc-table-wrap{overflow-x:auto;border-radius:12px;box-shadow:0 2px 12px rgba(0,0,0,.3)}
.proc-table{width:100%;border-collapse:collapse;font-size:.82rem}
.proc-table thead th{background:#1e293b;color:#64748b;font-weight:700;text-transform:uppercase;
  letter-spacing:.4px;padding:10px 12px;text-align:left;border-bottom:2px solid #334155;
  white-space:nowrap}
.proc-table tbody tr{border-bottom:1px solid #1e293b;transition:background .15s}
.proc-table tbody tr:hover{background:#1e293b}
.proc-table tbody td{padding:10px 12px;vertical-align:middle;background:#0f172a}
/* faixa colorida por status */
.proc-table tbody tr.row-fav td:first-child{border-left:4px solid #22c55e}
.proc-table tbody tr.row-desf td:first-child{border-left:4px solid #ef4444}
.proc-table tbody tr.row-sem td:first-child{border-left:4px solid #f59e0b}
.proc-table tbody tr.row-nl td:first-child{border-left:4px solid #475569}
/* badges de tipo */
.badge{display:inline-block;padding:3px 8px;border-radius:6px;font-size:.75rem;
  font-weight:700;letter-spacing:.3px;white-space:nowrap}
.badge-acordao{background:#1e3a8a;color:#93c5fd}
.badge-sent-ag{background:#78350f;color:#fcd34d}
.badge-sent{background:#134e4a;color:#5eead4}
.badge-1g{background:#422006;color:#fdba74}
.badge-outro{background:#1e293b;color:#94a3b8}
/* badges de status */
.badge-fav{background:#14532d;color:#4ade80}
.badge-desf{background:#450a0a;color:#fca5a5}
.badge-sem{background:#431407;color:#fdba74}
.badge-ext{background:#312e81;color:#a5b4fc}
.badge-anul{background:#4a1d96;color:#c4b5fd}
.badge-st-nl{background:#1e293b;color:#64748b}
/* coluna relator */
.rel-name{color:#cbd5e1;font-weight:500}
/* materia pill */
.mat-pill{display:inline-block;padding:2px 7px;border-radius:4px;background:#1e3a5f;
  color:#60a5fa;font-size:.75rem;font-weight:600;letter-spacing:.3px}
/* valor */
.val-txt{color:#4ade80;font-weight:600;font-size:.8rem}
/* data */
.date-txt{color:#64748b;font-size:.79rem;white-space:nowrap}
/* número processo */
.proc-num{color:#e2e8f0;font-family:monospace;font-size:.8rem;white-space:nowrap}
/* separador de seção visual quando tem acórdão */
.acordao-sep{background:#172033 !important}
.acordao-sep td{border-top:2px solid #1e3a8a !important}
</style>
</head><body>
<div class="dash-wrap">
  <div class="dash-header">
    <div>
      <h1>📊 Dashboard Analítico</h1>
      <div class="sub" id="dash-sub">Carregando dados...</div>
    </div>
    <div class="btn-row">
      <a href="/" class="btn-h btn-back">← Nova Análise</a>
      <a id="btn-dl-dash"   href="#" class="btn-h btn-dld"  style="display:none">📥 Baixar Planilha</a>
      <a id="btn-docx-dash" href="#" class="btn-h btn-docx" style="display:none">📄 Baixar Relatório</a>
    </div>
  </div>

  <!-- Filtro de período -->
  <div id="filtro-bar" style="display:none;background:#1e293b;border-radius:12px;padding:14px 18px;
       margin-bottom:20px;display:flex;align-items:center;gap:12px;flex-wrap:wrap">
    <span style="font-size:.82rem;color:#94a3b8;font-weight:600;white-space:nowrap">📅 Período:</span>
    <input type="date" id="f-ini" style="background:#0f172a;color:#e2e8f0;border:1px solid #334155;
           border-radius:7px;padding:6px 10px;font-size:.83rem;cursor:pointer"
           oninput="aplicarFiltro()">
    <span style="color:#475569;font-size:.85rem">até</span>
    <input type="date" id="f-fim" style="background:#0f172a;color:#e2e8f0;border:1px solid #334155;
           border-radius:7px;padding:6px 10px;font-size:.83rem;cursor:pointer"
           oninput="aplicarFiltro()">
    <button onclick="limparFiltro()" style="background:#334155;color:#94a3b8;border:none;
            border-radius:7px;padding:6px 12px;font-size:.82rem;cursor:pointer">✕ Limpar</button>
    <span id="f-contagem" style="font-size:.8rem;color:#64748b;margin-left:auto"></span>
  </div>

  <!-- Cards -->
  <div class="cards" id="cards-wrap"></div>

  <!-- Gráficos -->
  <div class="charts-top" id="charts-wrap" style="display:none">
    <div class="chart-box">
      <div class="chart-title">Status das Decisões</div>
      <div class="chart-canvas-wrap" style="height:280px">
        <canvas id="chart-status"></canvas>
      </div>
    </div>
    <div class="chart-box">
      <div class="chart-title">Tipo de Decisão</div>
      <div class="chart-canvas-wrap" style="height:280px">
        <canvas id="chart-tipo"></canvas>
      </div>
    </div>
    <div class="chart-box full">
      <div class="chart-title">Distribuição por Matéria</div>
      <div class="chart-canvas-wrap" id="wrap-materia">
        <canvas id="chart-materia"></canvas>
      </div>
    </div>
    <div class="chart-box full">
      <div class="chart-title">Decisões por Relator / Juiz</div>
      <div class="chart-canvas-wrap" id="wrap-relator">
        <canvas id="chart-relator"></canvas>
      </div>
    </div>
  </div>

  <!-- Tabela de processos -->
  <div class="proc-section" id="proc-section" style="display:none">
    <div class="proc-section-title">📋 Processos Analisados</div>
    <div class="proc-table-wrap">
      <table class="proc-table">
        <thead>
          <tr>
            <th>#</th>
            <th>Nº do Processo</th>
            <th>Grau / Doc</th>
            <th>Status da Decisão</th>
            <th>Relator / Juiz</th>
            <th>Matéria</th>
            <th>Condenação</th>
            <th>Data</th>
          </tr>
        </thead>
        <tbody id="proc-tbody"></tbody>
      </table>
    </div>
  </div>
</div>

<script>
const JID = "{{ job_id }}";
const COR_FAV  = '#22c55e';
const COR_DESF = '#ef4444';
const COR_SEM  = '#f59e0b';
const COR_NL   = '#64748b';

// ── Filtro de data e re-renderização ─────────────────────────
var _chartStatus=null,_chartTipo=null,_chartMateria=null,_chartRelator=null,_allData=null;

function _parseData(str){
  if(!str||str==='—') return null;
  var p=str.split('/');
  if(p.length!==3) return null;
  return new Date(parseInt(p[2]),parseInt(p[1])-1,parseInt(p[0]));
}

function aplicarFiltro(){
  if(!_allData) return;
  var ini=document.getElementById('f-ini').value;
  var fim=document.getElementById('f-fim').value;
  var dIni=ini?new Date(ini):null;
  var dFim=fim?new Date(fim+'T23:59:59'):null;
  var procs=(_allData.processos||[]).slice();
  if(dIni||dFim){
    procs=procs.filter(function(p){
      var d=_parseData(p.data);
      if(!d) return false;
      if(dIni&&d<dIni) return false;
      if(dFim&&d>dFim) return false;
      return true;
    });
  }
  document.getElementById('f-contagem').textContent=(dIni||dFim)?procs.length+' processo(s) no período':'';
  _renderDashboard(procs);
}

function limparFiltro(){
  document.getElementById('f-ini').value='';
  document.getElementById('f-fim').value='';
  document.getElementById('f-contagem').textContent='';
  aplicarFiltro();
}

function _reconstruirContagens(procs2g){
  var sc={},mc={},tc={},rc={};
  procs2g.forEach(function(p){
    var st=p.status||'',mt=p.materia||'',tp=p.tipo||'',rl=p.relator||'';
    if(st) sc[st]=(sc[st]||0)+1;
    if(mt) mc[mt]=(mc[mt]||0)+1;
    if(tp) tc[tp]=(tc[tp]||0)+1;
    if(rl&&st){if(!rc[rl])rc[rl]={};rc[rl][st]=(rc[rl][st]||0)+1;}
  });
  return{sc:sc,mc:mc,tc:tc,rc:rc};
}

function _sortCrono(arr){
  return arr.slice().sort(function(a,b){
    var da=_parseData(a.data),db=_parseData(b.data);
    if(!da&&!db) return 0; if(!da) return 1; if(!db) return -1;
    return da-db;
  });
}

function _renderDashboard(procs){
  var procs2g=_sortCrono(procs.filter(function(p){return p.grau!=='outros';}));
  var procs1g=_sortCrono(procs.filter(function(p){return p.grau==='outros';}));
  var t2g=procs2g.length, t1g=procs1g.length;
  document.getElementById('dash-sub').textContent=
    t2g+' processo(s) de 2º grau'+(t1g>0?' · '+t1g+' de 1º grau':'');

  var cnt=_reconstruirContagens(procs2g);
  var fav=cnt.sc['FAVORÁVEL']||0, desf=cnt.sc['DESFAVORÁVEL']||0;
  var aprov=t2g>0?((fav/t2g)*100).toFixed(1):'0.0';
  document.getElementById('cards-wrap').innerHTML=[
    {cls:'total',val:t2g,lbl:'2º Grau — Turmas/Câmaras',sub:'processos analisados'},
    {cls:'fav',val:fav,lbl:'Favoráveis',sub:'para o consumidor'},
    {cls:'desf',val:desf,lbl:'Desfavoráveis',sub:'para o consumidor'},
    {cls:'sem',val:aprov+'%',lbl:'Aproveitamento',sub:'decisões favoráveis'},
  ].map(function(c){return'<div class="card '+c.cls+'"><div class="card-val">'+c.val+'</div>'
    +'<div class="card-lbl">'+c.lbl+'</div><div class="card-sub">'+c.sub+'</div></div>';}).join('');

  document.getElementById('charts-wrap').style.display=t2g>0?'grid':'none';
  if(t2g===0&&t1g===0){document.getElementById('proc-section').style.display='none';return;}

  var statusLabels=Object.keys(cnt.sc),statusData=Object.values(cnt.sc);
  if(_chartStatus) _chartStatus.destroy();
  _chartStatus=new Chart(document.getElementById('chart-status'),{
    type:'doughnut',
    data:{labels:statusLabels,datasets:[{data:statusData,backgroundColor:statusLabels.map(corStatus),borderColor:'#1e293b',borderWidth:3}]},
    options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{position:'bottom',labels:{color:'#94a3b8',font:{size:12}}},
      tooltip:{callbacks:{label:function(c){var tot=statusData.reduce(function(a,b){return a+b;},0);
        return c.label+': '+c.parsed+' ('+(c.parsed/tot*100).toFixed(1)+'%)';}}}}}
  });

  var tipoLabels=Object.keys(cnt.tc),tipoData=Object.values(cnt.tc);
  if(_chartTipo) _chartTipo.destroy();
  _chartTipo=new Chart(document.getElementById('chart-tipo'),{
    type:'doughnut',
    data:{labels:tipoLabels,datasets:[{data:tipoData,backgroundColor:['#3b82f6','#8b5cf6','#06b6d4','#f59e0b','#64748b'],borderColor:'#1e293b',borderWidth:3}]},
    options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{position:'bottom',labels:{color:'#94a3b8',font:{size:12}}}}}
  });

  var PALETA=['#3b82f6','#8b5cf6','#06b6d4','#f59e0b','#10b981','#f43f5e','#a78bfa','#34d399','#fb923c','#60a5fa','#c084fc','#2dd4bf','#fbbf24','#4ade80','#f472b6'];
  var matE=Object.entries(cnt.mc).filter(function(e){return e[0];}).sort(function(a,b){return b[1]-a[1];});
  document.getElementById('wrap-materia').style.height=Math.max(220,matE.length*38)+'px';
  if(_chartMateria) _chartMateria.destroy();
  _chartMateria=new Chart(document.getElementById('chart-materia'),{
    type:'bar',
    data:{labels:matE.map(function(e){return e[0];}),datasets:[{label:'Processos',data:matE.map(function(e){return e[1];}),
      backgroundColor:matE.map(function(_,i){return PALETA[i%PALETA.length];}),borderRadius:6}]},
    options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false},
      tooltip:{callbacks:{label:function(c){return' '+c.parsed.x+' processo(s)';}}}},
      scales:{x:{grid:{color:'#1e3a5f'},ticks:{color:'#94a3b8'}},y:{grid:{color:'transparent'},ticks:{color:'#cbd5e1',font:{size:11}}}}}
  });

  var relE=Object.entries(cnt.rc).filter(function(e){return e[0];})
    .sort(function(a,b){return Object.values(b[1]).reduce(function(s,v){return s+v;},0)-Object.values(a[1]).reduce(function(s,v){return s+v;},0);});
  var todosS=[];
  relE.forEach(function(e){Object.keys(e[1]).forEach(function(s){if(todosS.indexOf(s)===-1)todosS.push(s);});});
  document.getElementById('wrap-relator').style.height=Math.max(220,relE.length*44)+'px';
  if(_chartRelator) _chartRelator.destroy();
  _chartRelator=new Chart(document.getElementById('chart-relator'),{
    type:'bar',
    data:{labels:relE.map(function(e){return e[0];}),datasets:todosS.map(function(st){return{
      label:st,data:relE.map(function(e){return e[1][st]||0;}),backgroundColor:corStatus(st),borderRadius:4};})},
    options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,
      plugins:{legend:{position:'bottom',labels:{color:'#94a3b8',font:{size:11}}},tooltip:{mode:'index',intersect:false}},
      scales:{x:{stacked:true,grid:{color:'#1e3a5f'},ticks:{color:'#94a3b8'}},
        y:{stacked:true,grid:{color:'transparent'},ticks:{color:'#cbd5e1',font:{size:11}}}}}
  });

  function _tipoBadge(p){var tp=(p.tipo||'').toUpperCase();
    if(tp==='ACÓRDÃO'||tp==='ACORDAO') return'<span class="badge badge-acordao">🏛️ ACÓRDÃO</span>';
    if(tp==='SENTENÇA'||tp==='SENTENCA') return p.dist2g==='SIM'
      ?'<span class="badge badge-sent-ag">⏳ SENT. (aguard. acórdão)</span>'
      :'<span class="badge badge-1g">⚖️ SENT. 1º GRAU</span>';
    if(tp==='NÃO LOCALIZADO') return'<span class="badge badge-outro">❓ N. LOC.</span>';
    if(tp==='ERRO') return'<span class="badge badge-outro">❌ ERRO</span>';
    return'<span class="badge badge-outro">'+(p.tipo||'—')+'</span>';}
  function _stBadge(st){if(!st) return'<span class="badge badge-st-nl">—</span>';var s=st.toUpperCase();
    if(s.includes('FAVOR')&&!s.includes('DESFA')) return'<span class="badge badge-fav">✅ FAVORÁVEL</span>';
    if(s.includes('DESFA'))   return'<span class="badge badge-desf">❌ DESFAVORÁVEL</span>';
    if(s.includes('EXTINTO')) return'<span class="badge badge-ext">🚫 EXTINTO S/ MÉRITO</span>';
    if(s.includes('ANULAD'))  return'<span class="badge badge-anul">↩️ SENT. ANULADA</span>';
    if(s.includes('SEM PAR')) return'<span class="badge badge-sem">⚠️ SEM PARECER</span>';
    if(s.includes('ACORDO'))  return'<span class="badge badge-fav">🤝 ACORDO</span>';
    return'<span class="badge badge-st-nl">'+st+'</span>';}
  function _row(p,i){var s=(p.status||'').toUpperCase();
    var cls=s.includes('FAVOR')&&!s.includes('DESFA')?'row-fav':s.includes('DESFA')?'row-desf':s?'row-sem':'row-nl';
    return'<tr class="'+cls+'">'
      +'<td style="color:#475569;text-align:center;padding-left:8px">'+(i+1)+'</td>'
      +'<td><span class="proc-num">'+p.numero+'</span></td>'
      +'<td>'+_tipoBadge(p)+'</td><td>'+_stBadge(p.status)+'</td>'
      +'<td>'+(p.relator?'<span class="rel-name">'+p.relator+'</span>':'<span style="color:#475569">—</span>')+'</td>'
      +'<td>'+(p.materia?'<span class="mat-pill">'+p.materia+'</span>':'<span style="color:#475569">—</span>')+'</td>'
      +'<td>'+(p.valor?'<span class="val-txt">'+p.valor+'</span>':'<span style="color:#334155">—</span>')+'</td>'
      +'<td><span class="date-txt">'+(p.data||'—')+'</span></td></tr>';}

  var rows='';
  procs2g.forEach(function(p,i){rows+=_row(p,i);});
  if(procs1g.length>0){
    rows+='<tr><td colspan="8" style="background:#1a1a0a;color:#f59e0b;font-weight:700;font-size:.8rem;'
      +'padding:10px 14px;text-transform:uppercase;letter-spacing:.5px;'
      +'border-top:2px solid #78350f;border-bottom:1px solid #78350f;">'
      +'⚠️ Sentenças / Processos sem acórdão de Turma — excluídos das estatísticas acima ('
      +procs1g.length+')</td></tr>';
    procs1g.forEach(function(p,i){rows+=_row(p,i);});
  }
  document.getElementById('proc-tbody').innerHTML=rows;
  document.getElementById('proc-section').style.display=rows?'block':'none';
}
// ─────────────────────────────────────────────────────────────
const COR_ERR  = '#94a3b8';

const PALETA_MATERIAS = [
  '#3b82f6','#8b5cf6','#06b6d4','#f59e0b','#10b981',
  '#f43f5e','#a78bfa','#34d399','#fb923c','#60a5fa',
  '#c084fc','#2dd4bf','#fbbf24','#4ade80','#f472b6',
];

function corStatus(s) {
  if (!s) return COR_NL;
  s = s.toUpperCase();
  if (s.includes('FAVOR'))  return COR_FAV;
  if (s.includes('DESFA'))  return COR_DESF;
  if (s.includes('SEM PAR') || s.includes('ANULAD') || s.includes('EXTINT')) return COR_SEM;
  return COR_NL;
}

fetch('/dashboard_data/' + JID)
  .then(function(r){return r.json();})
  .then(function(d) {
    _allData = d;

    // Links de download
    if (d.tem_arquivo) {
      var bl = document.getElementById('btn-dl-dash');
      bl.href = '/download/' + JID; bl.style.display = 'inline-block';
    }
    if (d.tem_relatorio) {
      var bd = document.getElementById('btn-docx-dash');
      bd.href = '/download_relatorio/' + JID; bd.style.display = 'inline-block';
    }

    // Barra de filtro
    if ((d.processos||[]).length > 0)
      document.getElementById('filtro-bar').style.display = 'flex';

    // Banner 1g
    var t1g = d.total_1g || 0;
    if (t1g > 0) {
      var banner = document.createElement('div');
      banner.style.cssText = 'background:#78350f;color:#fef3c7;border-radius:10px;padding:12px 18px;'
        + 'margin-bottom:18px;font-size:.85rem;font-weight:600;border-left:4px solid #f59e0b;';
      banner.innerHTML = '⚠️ ' + t1g + ' processo(s) sem acórdão de Turma/Câmara foram '
        + '<strong>excluídos das estatísticas e gráficos acima</strong>. '
        + 'Aparecem separados no final da tabela.';
      document.getElementById('cards-wrap').before(banner);
    }

    aplicarFiltro();
  })
  .catch(function(err) {
    document.getElementById('dash-sub').textContent = 'Erro ao carregar dados: ' + err;
  });
</script>
</body></html>"""


# ══════════════════════════════════════════════════════════════
# ROTAS
# ══════════════════════════════════════════════════════════════
@app.before_request
def _requer_login():
    rotas_publicas = {"login", "static", "api_login"}
    if request.endpoint not in rotas_publicas and not session.get("logado"):
        # Permite requisições com Bearer token válido (API externa)
        auth = request.headers.get('Authorization', '')
        if auth.startswith('Bearer ') and auth[7:] in _tokens:
            return None
        # Requisições /api/* sem token retornam 401 JSON em vez de redirecionar
        if request.path.startswith('/api/'):
            return jsonify({'ok': False, 'error': 'não autenticado'}), 401
        return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    erro = None
    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        senha   = request.form.get("senha",   "").strip()
        if _verificar_login(usuario, senha):
            session["logado"] = True
            return redirect(url_for("index"))
        erro = "Usuário ou senha incorretos."
    return render_template_string(_LOGIN_HTML, erro=erro)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
def index():
    return render_template_string(FORM_HTML)


# ── Gestão de usuários ────────────────────────────────────────
@app.route("/api/usuarios", methods=["GET"])
def api_listar_usuarios():
    return jsonify(_listar_usuarios())


@app.route("/api/usuarios", methods=["POST"])
def api_salvar_usuario():
    data = request.get_json(force=True, silent=True) or {}
    cpf      = str(data.get("cpf",      "")).strip()
    senha    = str(data.get("senha",    "")).strip()
    label    = str(data.get("label",    "")).strip()
    nome     = str(data.get("nome",     "")).strip()
    sheet_id = str(data.get("sheet_id", "")).strip()
    if not cpf or not senha:
        return jsonify({"ok": False, "error": "CPF e senha são obrigatórios."}), 400
    try:
        _salvar_usuario(cpf, senha, label, nome, sheet_id)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/usuario_senha")
def api_usuario_senha():
    cpf = request.args.get("cpf", "").strip()
    return jsonify({"senha": _get_senha_usuario(cpf)})


# ── Jobs DJEN / XLSX ──────────────────────────────────────────
@app.route("/iniciar_djen", methods=["POST"])
def iniciar_djen():
    cpf           = request.form.get("cpf", "").strip()
    senha         = request.form.get("senha", "").strip()
    usar_ia       = request.form.get("usar_ia") == "1"
    modelo_ia     = ia_mod.MODELO_PADRAO if usar_ia else None
    api_key       = _get_api_key(ia_mod._detectar_provider(ia_mod.MODELO_PADRAO)) if usar_ia else ""
    if usar_ia and not api_key:
        return "Chave API não configurada. Verifique o config.ini.", 400

    nome_adv      = request.form.get("nome_adv", "").strip()
    nome_advogado = _carregar_config().get("nome_advogado", "")
    data_ini      = request.form.get("data_ini", "").strip()
    data_fim      = request.form.get("data_fim", "").strip()
    turma            = request.form.get("turma", "0").strip()
    relator          = request.form.get("relator_filtro", "").strip()
    filtro_texto     = ""
    filtro_tipo_doc  = True
    batch = 0

    global _job_ativo
    job_id = uuid.uuid4().hex[:8]
    jobs[job_id] = {
        'logs': [], 'status': 'running', 'file': None,
        'error': '', 'pct': 5, 'subtitulo': 'Iniciando...',
        'pausado': False, 'cancelado': False,
        'linhas': [], 'criado_em': time.time(),
    }
    with _job_ativo_lock:
        _job_ativo = job_id
    threading.Thread(
        target=workers.processar_job_djen,
        args=(job_id, jobs, nome_adv, data_ini, data_fim,
              turma, relator, cpf, senha, api_key, batch,
              filtro_texto, modelo_ia, nome_advogado, usar_ia),
        kwargs={"advogado_key": _get_advogado_key(cpf), "filtro_tipo_doc": filtro_tipo_doc},
        daemon=True,
    ).start()
    return redirect(url_for('status_page', job_id=job_id))


@app.route("/iniciar_xlsx", methods=["POST"])
@app.route("/iniciar", methods=["POST"])
def iniciar_xlsx():
    arq           = request.files.get("arquivo")
    numeros_texto = request.form.get("numeros_texto", "").strip()

    tem_arquivo = arq and arq.filename != ""
    if not tem_arquivo and not numeros_texto:
        return "Informe os números dos processos na caixa de texto ou envie uma planilha.", 400

    job_id  = uuid.uuid4().hex[:8]
    caminho = ""
    if tem_arquivo:
        caminho = os.path.join(OUTPUT, f"upload_{job_id}.xlsx")
        arq.save(caminho)

    cpf           = request.form.get("cpf", "").strip()
    senha         = request.form.get("senha", "").strip()
    usar_ia       = request.form.get("usar_ia") == "1"
    modelo_ia     = ia_mod.MODELO_PADRAO if usar_ia else None
    api_key       = _get_api_key(ia_mod._detectar_provider(ia_mod.MODELO_PADRAO)) if usar_ia else ""
    nome_advogado = _carregar_config().get("nome_advogado", "")
    relator       = request.form.get("relator_filtro", "").strip()
    if usar_ia and not api_key:
        return "Chave API não configurada. Verifique o config.ini.", 400
    batch = 0

    global _job_ativo
    jobs[job_id] = {
        'logs': [], 'status': 'running', 'file': None,
        'error': '', 'pct': 5, 'subtitulo': 'Iniciando...',
        'pausado': False, 'cancelado': False,
        'linhas': [], 'criado_em': time.time(),
    }
    with _job_ativo_lock:
        _job_ativo = job_id
    threading.Thread(
        target=workers.processar_job_xlsx,
        args=(job_id, jobs, caminho, cpf, senha, api_key, batch, modelo_ia, nome_advogado, usar_ia),
        kwargs={"numeros_texto": numeros_texto, "relator_filtro": relator,
                "advogado_key": _get_advogado_key(cpf)},
        daemon=True,
    ).start()
    return redirect(url_for('status_page', job_id=job_id))


# ── Re-análise do Sheets ──────────────────────────────────────
_MATERIAS_OPCOES = [
    "OUTRO", "COBRANCA_IND", "CARTAO_CREDITO", "EMPRESTIMO_CONSIGNADO",
    "SEGURO_PRESTAMISTA", "CONTA_CORRENTE", "FINANCIAMENTO", "SAQUE_TERMINAL",
]
_STATUS_OPCOES = [
    "FAVORÁVEL", "DESFAVORÁVEL", "EXTINTO SEM MÉRITO",
    "SENTENÇA ANULADA", "ACORDO HOMOLOGADO", "SEM PARECER CONCLUSIVO",
]

@app.route("/reanalise")
def reanalise_page():
    import json as _json
    usuarios = _listar_usuarios()
    senhas   = {}
    for u in usuarios:
        senhas[u['cpf']] = _get_senha_usuario(u['cpf'])
    return render_template_string(
        REANALISE_HTML,
        usuarios=usuarios,
        senhas_json=_json.dumps(senhas),
        materias=_MATERIAS_OPCOES,
        status_opcoes=_STATUS_OPCOES,
    )


@app.route("/iniciar_reanalise", methods=["POST"])
def iniciar_reanalise():
    cpf              = request.form.get("cpf", "").strip()
    senha            = request.form.get("senha", "").strip()
    filtro_materia   = request.form.getlist("filtro_materia")
    filtro_status    = request.form.getlist("filtro_status")
    processos_texto  = request.form.get("processos_manual", "").strip()
    processos_manual = [p.strip() for p in processos_texto.splitlines() if p.strip()] if processos_texto else None

    if not senha:
        senha = _get_senha_usuario(cpf)
    if not cpf or not senha:
        return "CPF/senha não encontrados. Verifique o config.ini.", 400

    api_key       = _get_api_key(ia_mod._detectar_provider(ia_mod.MODELO_PADRAO))
    modelo_ia     = ia_mod.MODELO_PADRAO
    nome_advogado = _carregar_config().get("nome_advogado", "")
    advogado_key  = _get_advogado_key(cpf)

    if not api_key:
        return "Chave API não configurada. Verifique o config.ini.", 400

    global _job_ativo
    job_id = uuid.uuid4().hex[:8]
    jobs[job_id] = {
        'logs': [], 'status': 'running', 'file': None,
        'error': '', 'pct': 3, 'subtitulo': 'Lendo Sheets...',
        'pausado': False, 'cancelado': False,
        'linhas': [], 'criado_em': time.time(),
    }
    with _job_ativo_lock:
        _job_ativo = job_id
    threading.Thread(
        target=workers.processar_job_reanalise,
        kwargs={
            "job_id":           job_id,
            "jobs":             jobs,
            "advogado_key":     advogado_key,
            "cpf":              cpf,
            "senha":            senha,
            "api_key":          api_key,
            "modelo_ia":        modelo_ia,
            "nome_advogado":    nome_advogado,
            "filtro_materia":   filtro_materia or None,
            "filtro_status":    filtro_status  or None,
            "processos_manual": processos_manual,
        },
        daemon=True,
    ).start()
    return redirect(url_for('status_page', job_id=job_id))


# ── Controle de jobs ──────────────────────────────────────────
@app.route("/pausar/<job_id>", methods=["POST"])
def pausar(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "não encontrado"}), 404
    job['pausado'] = not job.get('pausado', False)
    if job['pausado']:
        job['logs'].append("⏸️ Pausa solicitada — aguardando término do processo atual...")
    return jsonify({"pausado": job['pausado']})


@app.route("/cancelar/<job_id>", methods=["POST"])
def cancelar(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "não encontrado"}), 404
    job['cancelado'] = True
    job['pausado']   = False  # despausa para o loop notar o cancelamento
    job['logs'].append("⛔ Cancelamento solicitado — encerrando processo atual...")
    return jsonify({"ok": True})


# ── Status page (URL estável para retomar monitoramento) ─────
@app.route("/status/<job_id>")
def status_page(job_id):
    if job_id not in jobs:
        return redirect(url_for('index'))
    return render_template_string(STATUS_HTML, job_id=job_id)


@app.route("/api/job_ativo")
def api_job_ativo():
    with _job_ativo_lock:
        jid = _job_ativo
    if not jid or jid not in jobs:
        return jsonify({"job_id": None})
    job  = jobs[jid]
    arq  = job.get('file')
    docx = job.get('docx_file')
    return jsonify({
        "job_id":        jid,
        "status":        job['status'],
        "pct":           job.get('pct', 0),
        "subtitulo":     job.get('subtitulo', ''),
        "tem_arquivo":   bool(arq  and os.path.exists(arq)),
        "tem_relatorio": bool(docx and os.path.exists(docx)),
    })


# ── Progresso / download / dashboard ─────────────────────────
@app.route("/progresso/<job_id>")
def progresso(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "não encontrado"}), 404
    arq  = job.get('file')
    docx = job.get('docx_file')
    return jsonify({
        'logs':          job['logs'],
        'status':        job['status'],
        'error':         job['error'],
        'pct':           job['pct'],
        'subtitulo':     job['subtitulo'],
        'pausado':       job.get('pausado', False),
        'tem_arquivo':   bool(arq and os.path.exists(arq)),
        'tem_relatorio': bool(docx and os.path.exists(docx)),
        'tem_linhas':    bool(job.get('linhas')),
    })


@app.route("/download/<job_id>")
def download(job_id):
    job = jobs.get(job_id)
    caminho = job.get('file') if job else None
    if not caminho or not os.path.exists(caminho):
        return "Arquivo não disponível. O servidor pode ter sido reiniciado — refaça a análise.", 404
    return send_file(
        caminho, as_attachment=True,
        download_name=os.path.basename(caminho),
    )


@app.route("/download_relatorio/<job_id>")
def download_relatorio(job_id):
    job = jobs.get(job_id)
    caminho = job.get('docx_file') if job else None
    if not caminho or not os.path.exists(caminho):
        return "Relatório não disponível. O servidor pode ter sido reiniciado — refaça a análise.", 404
    return send_file(
        caminho, as_attachment=True,
        download_name=os.path.basename(caminho),
    )


@app.route("/dashboard/<job_id>")
def dashboard(job_id):
    if job_id not in jobs:
        return "Job não encontrado.", 404
    return render_template_string(DASHBOARD_HTML, job_id=job_id)


@app.route("/dashboard_data/<job_id>")
def dashboard_data(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "não encontrado"}), 404

    linhas = job.get('linhas', [])

    def _e_acordao(l):
        """Apenas acórdãos confirmados contam como decisão de Turma/Câmara."""
        tp = (l.get("TIPO") or "").strip().upper()
        return tp in ("ACÓRDÃO", "ACORDAO")

    _tipos_ignorar = {"ERRO", "NÃO LOCALIZADO", "NAO LOCALIZADO"}
    linhas_2g = [l for l in linhas if _e_acordao(l)]
    linhas_outros = [l for l in linhas if not _e_acordao(l)
                     and (l.get("TIPO") or "").strip().upper() not in _tipos_ignorar]

    status_counts  = Counter()
    materia_counts = Counter()
    tipo_counts    = Counter()
    relator_counts = {}

    for l in linhas_2g:
        st = (l.get("STATUS DA DECISÃO") or "").strip() or "SEM DECISÃO"
        mt = (l.get("MATÉRIA")           or "").strip()
        tp = (l.get("TIPO")              or "").strip() or "DESCONHECIDO"
        rl = (l.get("RELATOR/JUIZ")      or "").strip()

        status_counts[st]  += 1
        tipo_counts[tp]    += 1
        if mt:
            materia_counts[mt] += 1
        if rl:
            if rl not in relator_counts:
                relator_counts[rl] = {}
            relator_counts[rl][st] = relator_counts[rl].get(st, 0) + 1

    def _proc_dict(l, grau_label):
        tp     = (l.get("TIPO")               or "").strip()
        dist2g = (l.get("DISTRIBUÍDO 2º GRAU") or "").strip()
        tem_ac = (l.get("TEM ACÓRDÃO 2º GRAU") or "").strip()
        return {
            "numero":  (l.get("NÚMERO DO PROCESSO") or "").strip(),
            "tipo":    tp,
            "status":  (l.get("STATUS DA DECISÃO")  or "").strip(),
            "relator": (l.get("RELATOR/JUIZ")        or "").strip(),
            "materia": (l.get("MATÉRIA")             or "").strip(),
            "data":    (l.get("DATA DA DECISÃO")     or "").strip(),
            "dist2g":  dist2g,
            "tem_ac":  tem_ac,
            "valor":   (l.get("VALOR DA CONDENAÇÃO") or "").strip(),
            "grau":    grau_label,
        }

    processos = (
        [_proc_dict(l, "2g")    for l in linhas_2g] +
        [_proc_dict(l, "outros") for l in linhas_outros]
    )

    return jsonify({
        "total":          len(linhas),
        "total_2g":       len(linhas_2g),
        "total_1g":       len(linhas_outros),
        "status_counts":  dict(status_counts.most_common()),
        "materia_counts": dict(materia_counts.most_common()),
        "tipo_counts":    dict(tipo_counts.most_common()),
        "relator_counts": relator_counts,
        "processos":      processos,
        "tem_arquivo":    bool(job.get('file')),
        "tem_relatorio":  bool(job.get('docx_file')),
    })


# ══════════════════════════════════════════════════════════════
# API EXTERNA — CORS + TOKEN AUTH (para o analista.html no Vercel)
# ══════════════════════════════════════════════════════════════

_CORS_ORIGINS = {
    'https://project-4av3r.vercel.app',
    'http://localhost:5500',
    'http://127.0.0.1:5500',
}

_tokens: dict = {}
_TOKEN_TTL = 7 * 24 * 3600   # 7 dias — sobrevive reinicializações do servidor
_TOKENS_FILE = os.path.join(PASTA, 'tokens.json')


def _tokens_carregar():
    global _tokens
    try:
        if os.path.exists(_TOKENS_FILE):
            import json as _json
            dados = _json.loads(open(_TOKENS_FILE).read())
            agora = time.time()
            _tokens = {k: v for k, v in dados.items()
                       if agora - v.get('criado_em', 0) < _TOKEN_TTL}
    except Exception:
        _tokens = {}


def _tokens_salvar():
    try:
        import json as _json
        # Escrita atômica: grava em .tmp e renomeia para evitar corrupção em crash
        tmp = _TOKENS_FILE + '.tmp'
        with open(tmp, 'w') as f:
            f.write(_json.dumps(_tokens))
        os.replace(tmp, _TOKENS_FILE)
    except Exception:
        pass


_tokens_carregar()


def _token_valido(token):
    if not token or token not in _tokens:
        return False
    if time.time() - _tokens[token]['criado_em'] > _TOKEN_TTL:
        del _tokens[token]
        _tokens_salvar()
        return False
    return True


def _require_api_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('logado'):
            return f(*args, **kwargs)
        token = request.headers.get('Authorization', '').removeprefix('Bearer ').strip()
        if _token_valido(token):
            return f(*args, **kwargs)
        return jsonify({'ok': False, 'error': 'Não autenticado'}), 401
    return decorated


@app.after_request
def _cors_headers(response):
    origin = request.headers.get('Origin', '')
    if origin in _CORS_ORIGINS:
        response.headers['Access-Control-Allow-Origin']  = origin
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response


@app.route('/api/login', methods=['POST', 'OPTIONS'])
def api_login():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    data    = request.get_json(force=True, silent=True) or {}
    usuario = str(data.get('usuario', '')).strip()
    senha   = str(data.get('senha',   '')).strip()
    if _verificar_login(usuario, senha):
        token = secrets.token_hex(32)
        _tokens[token] = {'usuario': usuario, 'criado_em': time.time()}
        _tokens_salvar()
        return jsonify({'ok': True, 'token': token})
    return jsonify({'ok': False, 'error': 'Usuário ou senha incorretos'}), 401


@app.route('/api/jobs', methods=['GET', 'OPTIONS'])
@_require_api_auth
def api_jobs():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    resultado = []
    for jid, job in jobs.items():
        arq  = job.get('file',      '')
        docx = job.get('docx_file', '')
        resultado.append({
            'job_id':        jid,
            'status':        job['status'],
            'pct':           job.get('pct', 0),
            'subtitulo':     job.get('subtitulo', ''),
            'pausado':       job.get('pausado',   False),
            'cancelado':     job.get('cancelado', False),
            'advogado_key':  job.get('advogado_key', ''),
            'criado_em':     job.get('criado_em', 0),
            'tem_arquivo':   bool(arq  and os.path.exists(arq)),
            'tem_relatorio': bool(docx and os.path.exists(docx)),
            'logs_tail':     job.get('logs', [])[-6:],
            'error':         job.get('error', ''),
        })
    resultado.sort(key=lambda x: x['criado_em'], reverse=True)
    return jsonify({'ok': True, 'jobs': resultado})


@app.route('/api/progresso/<job_id>', methods=['GET', 'OPTIONS'])
@_require_api_auth
def api_progresso(job_id):
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    job = jobs.get(job_id)
    if not job:
        return jsonify({'error': 'não encontrado'}), 404
    return jsonify({
        'logs':          job['logs'],
        'status':        job['status'],
        'error':         job['error'],
        'pct':           job['pct'],
        'subtitulo':     job['subtitulo'],
        'pausado':       job.get('pausado', False),
        'tem_arquivo':   bool(job.get('file')      and os.path.exists(job.get('file', ''))),
        'tem_relatorio': bool(job.get('docx_file') and os.path.exists(job.get('docx_file', ''))),
    })


@app.route('/api/pausar/<job_id>', methods=['POST', 'OPTIONS'])
@_require_api_auth
def api_pausar(job_id):
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    job = jobs.get(job_id)
    if not job:
        return jsonify({'error': 'não encontrado'}), 404
    job['pausado'] = not job.get('pausado', False)
    if job['pausado']:
        job['logs'].append('⏸️ Pausa solicitada — aguardando término do processo atual...')
    return jsonify({'pausado': job['pausado']})


@app.route('/api/cancelar/<job_id>', methods=['POST', 'OPTIONS'])
@_require_api_auth
def api_cancelar(job_id):
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    job = jobs.get(job_id)
    if not job:
        return jsonify({'error': 'não encontrado'}), 404
    job['cancelado'] = True
    job['pausado']   = False
    job['logs'].append('⛔ Cancelamento solicitado — encerrando processo atual...')
    return jsonify({'ok': True})


@app.route('/api/iniciar_djen', methods=['POST', 'OPTIONS'])
@_require_api_auth
def api_iniciar_djen():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    data          = request.get_json(force=True, silent=True) or {}
    cpf           = str(data.get('cpf',         '')).strip()
    senha         = str(data.get('senha',        '')).strip()
    if not senha or senha == 'undefined':
        senha = _get_senha_usuario(cpf)
    nome_adv      = str(data.get('nome_adv',     '')).strip()
    data_ini      = str(data.get('data_ini',     '')).strip()
    data_fim      = str(data.get('data_fim',     '')).strip()
    turma           = str(data.get('turma',           '0')).strip()
    relator         = str(data.get('relator',          '')).strip()
    filtro_texto    = ""
    filtro_tipo_doc = True
    usar_ia         = bool(data.get('usar_ia',         True))
    modelo_ia     = str(data.get('modelo_ia',    ia_mod.MODELO_PADRAO)).strip() or ia_mod.MODELO_PADRAO
    nome_advogado = _carregar_config().get('nome_advogado', '')
    batch = 0

    api_key = _get_api_key(ia_mod._detectar_provider(modelo_ia)) if usar_ia else ''
    if usar_ia and not api_key:
        return jsonify({'ok': False, 'error': 'Chave API não configurada'}), 400

    global _job_ativo
    job_id = uuid.uuid4().hex[:8]
    jobs[job_id] = {
        'logs': [], 'status': 'running', 'file': None,
        'error': '', 'pct': 5, 'subtitulo': 'Iniciando...',
        'pausado': False, 'cancelado': False,
        'linhas': [], 'criado_em': time.time(),
    }
    with _job_ativo_lock:
        _job_ativo = job_id
    threading.Thread(
        target=workers.processar_job_djen,
        args=(job_id, jobs, nome_adv, data_ini, data_fim,
              turma, relator, cpf, senha, api_key, batch,
              filtro_texto, modelo_ia, nome_advogado, usar_ia),
        kwargs={'advogado_key': _get_advogado_key(cpf), 'filtro_tipo_doc': filtro_tipo_doc},
        daemon=True,
    ).start()
    return jsonify({'ok': True, 'job_id': job_id})


@app.route('/api/iniciar_xlsx', methods=['POST', 'OPTIONS'])
@_require_api_auth
def api_iniciar_xlsx():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    data          = request.get_json(force=True, silent=True) or {}
    cpf           = str(data.get('cpf',          '')).strip()
    senha         = str(data.get('senha',         '')).strip()
    if not senha or senha == 'undefined':
        senha = _get_senha_usuario(cpf)
    numeros_texto = str(data.get('numeros_texto', '')).strip()
    relator       = str(data.get('relator',       '')).strip()
    usar_ia       = bool(data.get('usar_ia',      True))
    modelo_ia     = str(data.get('modelo_ia',     ia_mod.MODELO_PADRAO)).strip() or ia_mod.MODELO_PADRAO
    nome_advogado = _carregar_config().get('nome_advogado', '')
    batch = 0

    if not numeros_texto:
        return jsonify({'ok': False, 'error': 'Informe os números dos processos'}), 400

    api_key = _get_api_key(ia_mod._detectar_provider(modelo_ia)) if usar_ia else ''
    if usar_ia and not api_key:
        return jsonify({'ok': False, 'error': 'Chave API não configurada'}), 400

    global _job_ativo
    job_id = uuid.uuid4().hex[:8]
    jobs[job_id] = {
        'logs': [], 'status': 'running', 'file': None,
        'error': '', 'pct': 5, 'subtitulo': 'Iniciando...',
        'pausado': False, 'cancelado': False,
        'linhas': [], 'criado_em': time.time(),
    }
    with _job_ativo_lock:
        _job_ativo = job_id
    threading.Thread(
        target=workers.processar_job_xlsx,
        args=(job_id, jobs, '', cpf, senha, api_key, batch, modelo_ia, nome_advogado, usar_ia),
        kwargs={'numeros_texto': numeros_texto, 'relator_filtro': relator,
                'advogado_key': _get_advogado_key(cpf)},
        daemon=True,
    ).start()
    return jsonify({'ok': True, 'job_id': job_id})


@app.route('/api/iniciar_reanalise', methods=['POST', 'OPTIONS'])
@_require_api_auth
def api_iniciar_reanalise():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    data             = request.get_json(force=True, silent=True) or {}
    cpf              = str(data.get('cpf',   '')).strip()
    senha            = str(data.get('senha', '')).strip()
    if not senha or senha == 'undefined':
        senha = _get_senha_usuario(cpf)
    filtro_materia   = data.get('filtro_materia', []) or []
    filtro_status    = data.get('filtro_status',  []) or []
    processos_texto  = str(data.get('processos_manual', '')).strip()
    processos_manual = [p.strip() for p in processos_texto.splitlines() if p.strip()] if processos_texto else None
    modelo_ia        = ia_mod.MODELO_PADRAO
    nome_advogado    = _carregar_config().get('nome_advogado', '')
    advogado_key     = _get_advogado_key(cpf)

    api_key = _get_api_key(ia_mod._detectar_provider(modelo_ia))
    if not api_key:
        return jsonify({'ok': False, 'error': 'Chave API não configurada'}), 400

    global _job_ativo
    job_id = uuid.uuid4().hex[:8]
    jobs[job_id] = {
        'logs': [], 'status': 'running', 'file': None,
        'error': '', 'pct': 3, 'subtitulo': 'Lendo Sheets...',
        'pausado': False, 'cancelado': False,
        'linhas': [], 'criado_em': time.time(),
    }
    with _job_ativo_lock:
        _job_ativo = job_id
    threading.Thread(
        target=workers.processar_job_reanalise,
        kwargs={
            'job_id':           job_id,
            'jobs':             jobs,
            'advogado_key':     advogado_key,
            'cpf':              cpf,
            'senha':            senha,
            'api_key':          api_key,
            'modelo_ia':        modelo_ia,
            'nome_advogado':    nome_advogado,
            'filtro_materia':   filtro_materia or None,
            'filtro_status':    filtro_status  or None,
            'processos_manual': processos_manual,
        },
        daemon=True,
    ).start()
    return jsonify({'ok': True, 'job_id': job_id})


@app.route('/api/iniciar_distribuicoes', methods=['POST', 'OPTIONS'])
@_require_api_auth
def api_iniciar_distribuicoes():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    data      = request.get_json(force=True, silent=True) or {}
    cpf       = str(data.get('cpf',      '')).strip()
    senha     = str(data.get('senha',    '')).strip()
    data_ini  = str(data.get('data_ini', '')).strip() or None
    data_fim  = str(data.get('data_fim', '')).strip() or None
    if not senha or senha == 'undefined':
        senha = _get_senha_usuario(cpf)
    if not cpf:
        return jsonify({'ok': False, 'error': 'CPF não informado'}), 400

    advogado_key  = _get_advogado_key(cpf)
    nome_advogado = ''
    for u in _listar_usuarios():
        if u.get('cpf') == cpf:
            nome_advogado = u.get('nome', '')
            break

    job_id = uuid.uuid4().hex[:8]
    jobs[job_id] = {
        'logs': [], 'status': 'running', 'file': None,
        'error': '', 'pct': 5, 'subtitulo': 'Iniciando...',
        'pausado': False, 'cancelado': False,
        'linhas': [], 'criado_em': time.time(),
        'tipo': 'distribuicoes',
    }
    threading.Thread(
        target=workers.processar_job_distribuicoes,
        args=(job_id, jobs, cpf, senha, advogado_key, nome_advogado),
        kwargs={'data_ini': data_ini, 'data_fim': data_fim},
        daemon=True,
    ).start()
    return jsonify({'ok': True, 'job_id': job_id})


@app.route('/api/distribuicoes', methods=['GET', 'OPTIONS'])
@_require_api_auth
def api_distribuicoes():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    adv = request.args.get('adv', '').strip()
    if not adv:
        return jsonify({'ok': False, 'error': 'adv obrigatório'}), 400
    try:
        import sheets as _sh, json as _json
        adv_key = adv.lower().replace(' ', '_')
        result = _sh.ler_distribuicoes(advogado_key=adv_key)
        # data=None sinaliza falha (timeout/erro de rede); data=[] significa aba vazia
        if result.get('data') is None:
            return jsonify({'ok': False,
                            'error': 'Falha ao carregar dados do Sheets. Tente novamente em instantes.'}), 503
        total_projudi = 0
        try:
            _cp = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache_dist.json')
            with open(_cp) as _cf:
                total_projudi = _json.load(_cf).get(adv_key, {}).get('total_projudi', 0)
        except Exception:
            pass
        return jsonify({'ok': True, 'data': result.get('data', []),
                        'updatedAt': result.get('updatedAt'), 'adv': adv,
                        'totalJulgados': result.get('totalJulgados', 0),
                        'totalProjudi': total_projudi})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


def _iniciar_scheduler_distribuicoes():
    """Dispara verificação de distribuições às 00:05 todos os dias."""
    from datetime import datetime, timedelta

    def _segundos_ate_meia_noite():
        agora  = datetime.now()
        alvo   = (agora + timedelta(days=1)).replace(hour=0, minute=5, second=0, microsecond=0)
        if agora.hour == 0 and agora.minute < 5:
            alvo = agora.replace(hour=0, minute=5, second=0, microsecond=0)
        return max(0, (alvo - agora).total_seconds())

    def _executar():
        while True:
            time.sleep(_segundos_ate_meia_noite())
            for usuario in _listar_usuarios():
                cpf   = usuario.get('cpf', '')
                senha = _get_senha_usuario(cpf)
                if not cpf or not senha:
                    continue
                adv_key = _get_advogado_key(cpf)
                jid = uuid.uuid4().hex[:8]
                jobs[jid] = {
                    'logs': [], 'status': 'running', 'file': None,
                    'error': '', 'pct': 5, 'subtitulo': 'Auto 00:05...',
                    'pausado': False, 'cancelado': False,
                    'linhas': [], 'criado_em': time.time(),
                    'tipo': 'distribuicoes',
                }
                threading.Thread(
                    target=workers.processar_job_distribuicoes,
                    args=(jid, jobs, cpf, senha, adv_key, usuario.get('nome', '')),
                    daemon=True,
                ).start()

    threading.Thread(target=_executar, daemon=True).start()


# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import webbrowser, subprocess, sys

    def _liberar_porta(porta):
        try:
            import socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(("127.0.0.1", porta)) != 0:
                    return
            result = subprocess.check_output(
                f'netstat -ano | findstr :{porta}', shell=True
            ).decode(errors="ignore")
            pids = set()
            for linha in result.splitlines():
                partes = linha.split()
                if partes and partes[-1].isdigit():
                    pids.add(partes[-1])
            for pid in pids:
                if pid != "0":
                    subprocess.call(f"taskkill /PID {pid} /F", shell=True,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"⚡ Porta {porta} liberada (PIDs: {', '.join(pids)}).")
        except Exception as e:
            print(f"⚠️  Não foi possível liberar a porta {porta}: {e}")

    _cfg   = _carregar_config()
    _porta = _cfg["porta"]

    _liberar_porta(_porta)

    # Thread de limpeza automática de jobs antigos
    threading.Thread(target=_cleanup_jobs, daemon=True).start()

    _iniciar_scheduler_distribuicoes()

    def _abrir_browser():
        time.sleep(1.5)
        webbrowser.open(f"http://127.0.0.1:{_porta}")

    threading.Thread(target=_abrir_browser, daemon=True).start()
    app.run(debug=False, port=_porta, threaded=True)
