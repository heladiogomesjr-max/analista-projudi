"""
projudi.py — Automação do PROJUDI via Playwright
Baseado no projudi_bot.py funcional do APP JURÍDICO.

Funções públicas:
  novo_browser(pw)                          → (browser, page)
  login(page, cpf, senha, log)
  get_urls_busca(page, log)                 → (url_2g, url_1g)
  analisar_processo(page, numero, url_2g, url_1g, log)  → dict com textos extraídos
"""
import io, re, json, time
import requests as req_http
import pdfplumber
from bs4 import BeautifulSoup

BASE     = "https://projudi.tjam.jus.br"
URL_LOGIN = f"{BASE}/projudi/usuario/logon.do?actionType=inicio"


# ══════════════════════════════════════════════════════════════
# BROWSER
# ══════════════════════════════════════════════════════════════
def novo_browser(pw):
    browser = pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
    context = browser.new_context(
        no_viewport=True,
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
    )
    return browser, context.new_page()


# ══════════════════════════════════════════════════════════════
# LOGIN  (idêntico ao projudi_bot.py funcional)
# ══════════════════════════════════════════════════════════════
def login(page, cpf, senha, log):
    log("🔑 Fazendo login no PROJUDI...")

    def _ir_para_login():
        """
        Garante chegada na URL de login SEM jsessionid nem _tj expirados.

        Quando a sessão expira, o PROJUDI redireciona qualquer URL para
        logon.do;jsessionid=EXPIRADO?_tj=TOKEN_ANTIGO — incluindo o _tj da
        requisição original para "lembrar" o destino pós-login.
        Navegar para about:blank primeiro elimina contexto/referrer do browser,
        impede que o servidor associe a nova requisição ao token expirado.
        """
        try:
            page.goto("about:blank", wait_until="domcontentloaded", timeout=5000)
        except Exception:
            pass
        try:
            page.context.clear_cookies()
        except Exception:
            pass
        page.goto(URL_LOGIN)
        page.wait_for_load_state("domcontentloaded")

    _ir_para_login()

    try:
        page.wait_for_selector("#login", timeout=12000)
    except Exception:
        log(f"   ⚠️ Formulário não encontrado (URL atual: {page.url[:100]}). Tentando novamente...")
        _ir_para_login()
        page.wait_for_selector("#login", timeout=15000)
    # Formata CPF como XXX.XXX.XXX-XX (campo do PROJUDI tem máscara)
    cpf_digits = cpf.replace(".", "").replace("-", "").strip()
    if len(cpf_digits) == 11:
        cpf_fmt = f"{cpf_digits[:3]}.{cpf_digits[3:6]}.{cpf_digits[6:9]}-{cpf_digits[9:]}"
    else:
        cpf_fmt = cpf
    page.fill("#login", cpf_fmt)
    page.fill("input[name=senha]", senha)
    try:
        page.click(
            "input[type='submit'], button[type='submit'], #entrar, #btnEntrar",
            timeout=3000,
        )
    except Exception:
        page.keyboard.press("Enter")

    # Aguarda networkidle — igual ao teste_leitura_docs.py funcional
    try:
        page.wait_for_load_state("networkidle", timeout=30000)
    except Exception:
        pass

    # Aguarda o menu aparecer em qualquer frame (PROJUDI usa frameset)
    # Tenta no frame principal primeiro; se falhar, verifica frames filhos
    menu_ok = False
    try:
        page.wait_for_selector(
            "a:has-text('Processos 2º Grau'), #menuPrincipal",
            timeout=40000, state="attached"
        )
        menu_ok = True
    except Exception:
        # Busca nos frames filhos (menu fica num frame separado)
        for _ in range(20):   # até 10 s
            for frame in page.frames:
                try:
                    if frame.locator("a:has-text('Processos 2º Grau')").count() > 0:
                        menu_ok = True
                        break
                except Exception:
                    continue
            if menu_ok:
                break
            time.sleep(0.5)

    if menu_ok:
        log("✅ Login OK.")
    elif "logon" not in page.url.lower():
        log("✅ Login OK (confirmação pela URL).")
    else:
        log(f"❌ Login falhou. URL atual: {page.url}")
        try:
            # Captura texto de erro da página de login
            err_text = page.locator("body").inner_text(timeout=3000)[:400].replace("\n", " ")
            log(f"❌ Conteúdo da página: {err_text}")
        except Exception:
            pass
        raise RuntimeError("Falha no login. Verifique CPF e senha.")


# ══════════════════════════════════════════════════════════════
# CAPTURA DE URLs DE MENU
# ══════════════════════════════════════════════════════════════
def _get_url_menu(page, texto_menu):
    """
    Retorna a URL do item de menu pelo texto visível.
    Tenta 3 estratégias em ordem crescente de complexidade.
    """
    texto_menu_js = json.dumps(texto_menu)  # escapa aspas/caracteres especiais para JS

    # Estratégia 1: <a> com href direto (igual ao projudi_bot.py funcional)
    try:
        elem = page.locator(f"a:has-text('{texto_menu}')").last
        if elem.count() > 0:
            href = elem.get_attribute("href") or ""
            if href and not href.startswith("javascript"):
                return href if href.startswith("http") else BASE + href
    except Exception:
        pass

    # Estratégia 2: extrai URL do onclick/href via JS (sem navegar)
    try:
        url = page.evaluate(f"""() => {{
            const alvo = {texto_menu_js}.replace(/\\s+/g,' ').toLowerCase();
            const alt  = alvo.replace('1º','1°').replace('2º','2°');
            for (const el of document.querySelectorAll('*')) {{
                const t = (el.innerText||el.textContent||'')
                    .replace(/\\u00a0/g,' ').replace(/\\s+/g,' ').trim().toLowerCase();
                if (t !== alvo && t !== alt) continue;
                for (const c of [el, el.parentElement, el.closest('a'), el.closest('td')]) {{
                    if (!c) continue;
                    for (const attr of ['href','onclick']) {{
                        const v = c.getAttribute(attr) || '';
                        const m = v.match(/['"](\\/projudi[^'"\\s]+)['"]/);
                        if (m) return m[1];
                    }}
                }}
            }}
            return '';
        }}""") or ""
        if url:
            return url if url.startswith("http") else BASE + url
    except Exception:
        pass

    # Estratégia 3: clica no elemento mais profundo e captura a URL do frame resultante
    urls_antes = {f.url for f in page.frames}
    try:
        page.evaluate(f"""() => {{
            const alvo = {texto_menu_js}.replace(/\\s+/g,' ').toLowerCase();
            const alt  = alvo.replace('1º','1°').replace('2º','2°');
            let melhor = null;
            for (const el of document.querySelectorAll('*')) {{
                const t = (el.innerText||el.textContent||'')
                    .replace(/\\u00a0/g,' ').replace(/\\s+/g,' ').trim().toLowerCase();
                if (t === alvo || t === alt) melhor = el;
            }}
            if (melhor) melhor.click();
        }}""")
    except Exception:
        return ""

    for _ in range(5):
        try:
            page.wait_for_load_state("networkidle", timeout=2000)
        except Exception:
            pass
        for frame in page.frames:
            try:
                u = frame.url
                if (u and u not in urls_antes and "/projudi/" in u
                        and "logon" not in u.lower() and u != "about:blank"):
                    return u if u.startswith("http") else BASE + u
            except Exception:
                continue
    return ""


def get_urls_busca(page, log):
    """
    Obtém as URLs de busca do 2º e 1º Grau do menu do PROJUDI.
    IMPORTANTE: captura AMBAS as URLs ANTES de navegar para qualquer uma delas.
    A estratégia 3 de _get_url_menu pode navegar a página — por isso 2g e 1g
    são capturadas com estratégias 1 e 2 (sem navegar) antes de qualquer clique.
    """
    log("🔗 Localizando menus de busca...")

    def _href_direto(texto):
        """Estratégia 1 (igual ao projudi_bot.py): <a> com href direto."""
        try:
            elem = page.locator(f"a:has-text('{texto}')").last
            if elem.count() > 0:
                href = elem.get_attribute("href") or ""
                if href and not href.startswith("javascript"):
                    return href if href.startswith("http") else BASE + href
        except Exception:
            pass
        return ""

    def _onclick_url(texto):
        """Estratégia 2: extrai URL do onclick/href via JS sem navegar."""
        texto_js = json.dumps(texto)
        try:
            url = page.evaluate(f"""() => {{
                const alvo = {texto_js}.replace(/\\s+/g,' ').toLowerCase();
                const alt  = alvo.replace('1º','1°').replace('2º','2°');
                for (const el of document.querySelectorAll('*')) {{
                    const t = (el.innerText||el.textContent||'')
                        .replace(/\\u00a0/g,' ').replace(/\\s+/g,' ').trim().toLowerCase();
                    if (t !== alvo && t !== alt) continue;
                    for (const c of [el,el.parentElement,el.closest('a'),el.closest('td')]) {{
                        if (!c) continue;
                        for (const attr of ['href','onclick']) {{
                            const v = c.getAttribute(attr)||'';
                            const m = v.match(/['"](\\/projudi[^'"\\s]+)['"]/);
                            if (m) return m[1];
                        }}
                    }}
                }}
                return '';
            }}""") or ""
            if url:
                return url if url.startswith("http") else BASE + url
        except Exception:
            pass
        return ""

    def _clicar_e_capturar(texto):
        """Estratégia 3 (último recurso): clica e captura frame. Usada isoladamente."""
        texto_js = json.dumps(texto)
        urls_antes = {f.url for f in page.frames}
        try:
            page.evaluate(f"""() => {{
                const alvo = {texto_js}.replace(/\\s+/g,' ').toLowerCase();
                const alt  = alvo.replace('1º','1°').replace('2º','2°');
                let melhor = null;
                for (const el of document.querySelectorAll('*')) {{
                    const t = (el.innerText||el.textContent||'')
                        .replace(/\\u00a0/g,' ').replace(/\\s+/g,' ').trim().toLowerCase();
                    if (t === alvo || t === alt) melhor = el;
                }}
                if (melhor) melhor.click();
            }}""")
        except Exception:
            return ""
        for _ in range(5):
            try:
                page.wait_for_load_state("networkidle", timeout=2000)
            except Exception:
                pass
            for frame in page.frames:
                try:
                    u = frame.url
                    if (u and u not in urls_antes and "/projudi/" in u
                            and "logon" not in u.lower() and u != "about:blank"):
                        return u if u.startswith("http") else BASE + u
                except Exception:
                    continue
        return ""

    def _href_nos_frames(texto):
        """
        PROJUDI usa frameset — o menu fica num frame filho, não no frame principal.
        Percorre todos os frames da página para encontrar o link.
        """
        for frame in page.frames:
            try:
                elem = frame.locator(f"a:has-text('{texto}')").last
                if elem.count() > 0:
                    href = elem.get_attribute("href") or ""
                    if href and not href.startswith("javascript"):
                        url = href if href.startswith("http") else BASE + href
                        pass  # URL capturada sem log verboso
                        return url
            except Exception:
                continue
        return ""

    # Captura 2g e 1g — busca em frames primeiro (PROJUDI usa frameset)
    url_2g = _href_nos_frames("Processos 2º Grau") or _href_direto("Processos 2º Grau") or _onclick_url("Processos 2º Grau")
    url_1g = _href_nos_frames("Processos 1º Grau") or _href_direto("Processos 1º Grau") or _onclick_url("Processos 1º Grau")

    # Somente se ainda não capturou, usa clique (um de cada vez, preservando menu)
    if not url_2g:
        url_2g = _clicar_e_capturar("Processos 2º Grau")
        # Após clicar, navega de volta ao menu para capturar 1g
        if url_2g and not url_1g:
            try:
                page.go_back()
                page.wait_for_load_state("domcontentloaded")
            except Exception as e:
                log(f"   ⚠️ go_back após captura 2g: {e}")

    if not url_1g:
        url_1g = _clicar_e_capturar("Processos 1º Grau")

    if not url_2g:
        log("⚠️ URL 2º Grau não obtida.")
    if not url_1g:
        log("⚠️ URL 1º Grau não obtida.")

    return url_2g, url_1g


# ══════════════════════════════════════════════════════════════
# HELPERS INTERNOS
# ══════════════════════════════════════════════════════════════
def _campo_pagina(page, rotulos):
    """Busca label→valor na página com 4 estratégias em cascata."""
    try:
        for r in rotulos:
            el = page.query_selector(f"td:has-text('{r}') + td")
            if el:
                v = el.inner_text().strip()
                if len(v) > 2:
                    return v

        soup = BeautifulSoup(page.content(), "html.parser")

        for r in rotulos:
            for td in soup.find_all("td", string=lambda x: x and r in x):
                prox = td.find_next_sibling("td")
                if prox:
                    v = prox.get_text(strip=True)
                    if len(v) > 2:
                        return v

        for r in rotulos:
            for tag in soup.find_all(["td","th","label","span","b","strong"]):
                t = tag.get_text(strip=True)
                if r.lower() in t.lower() and len(t) < 50:
                    prox = tag.find_next_sibling(["td","th","span"])
                    if prox:
                        v = prox.get_text(strip=True)
                        if len(v) > 2:
                            return v
                    pai = tag.find_parent("td")
                    if pai:
                        irm = pai.find_next_sibling("td")
                        if irm:
                            v = irm.get_text(strip=True)
                            if len(v) > 2:
                                return v

        rots_js = json.dumps(rotulos)
        v = page.evaluate(f"""() => {{
            const rots = {rots_js};
            for (const el of document.querySelectorAll('td,th,span,b,label,div')) {{
                const t = (el.innerText||el.textContent||'').trim();
                if (rots.some(r => t.toLowerCase().includes(r.toLowerCase())) && t.length < 50) {{
                    const nx = el.nextElementSibling || el.closest('td')?.nextElementSibling;
                    if (nx) {{
                        const v = (nx.innerText||nx.textContent||'').trim();
                        if (v.length > 2) return v;
                    }}
                }}
            }}
            return '';
        }}""")
        if v and len(v) > 2:
            return v
    except Exception:
        pass
    return ""


def _clicar_aba(page, nome):
    try:
        # Usa text-is (exact match) como no teste_leitura_docs.py funcional
        aba = page.locator(f"a:text-is('{nome}')").first
        if aba.count() == 0:
            # Fallback com has-text
            aba = page.locator(f"a:has-text('{nome}')").first
        if aba.count() == 0:
            return False
        aba.click()
        try:
            page.wait_for_load_state("networkidle", timeout=6000)
        except Exception:
            time.sleep(2)
        return True
    except Exception:
        return False


def _ler_tabela(page):
    return page.evaluate("""() => {
        const btns = Array.from(document.querySelectorAll('a[href="javascript://nop/"]'));

        function coletarSubLinhas(startNode) {
            // Coleta TRs de sub-documentos a partir de um nó inicial,
            // varrendo irmãos dentro do mesmo tbody E no tbody seguinte.
            const subTextos = [];
            const arquivos  = [];

            function processar(tr) {
                if (!tr) return false;
                if (tr.querySelector('a[href="javascript://nop/"]')) return false; // outro evento
                const sub = (tr.innerText||tr.textContent||'').replace(/\\s+/g,' ').trim();
                if (!sub) return true;
                subTextos.push(sub);
                const m = sub.match(/[Aa]rquivo:\\s*(.+?)\\s+(?:Ass\\.|online\\.pdf|\\d{4}-\\d{2}-|$)/);
                if (m && m[1].trim()) arquivos.push(m[1].trim().toLowerCase());
                return true;
            }

            // 1. Irmãos dentro do mesmo tbody
            let next = startNode.nextElementSibling;
            while (next) {
                if (!processar(next)) break;
                next = next.nextElementSibling;
            }

            // 2. TRs no tbody seguinte (PROJUDI coloca sub-linhas em tbody separado)
            const tbody = startNode.closest('tbody');
            if (tbody) {
                const nextTbody = tbody.nextElementSibling;
                if (nextTbody && nextTbody.tagName === 'TBODY') {
                    const trs = nextTbody.querySelectorAll('tr');
                    for (const tr of trs) {
                        if (!processar(tr)) break;
                    }
                }
            }

            return { subTextos, arquivos };
        }

        function textoTr(tr) {
            return tr ? (tr.innerText||tr.textContent||'').replace(/\\s+/g,' ').trim() : '';
        }
        function isJsOnly(t) {
            return /^\\s*var\\s+aj_/.test(t) || t.length < 5;
        }
        // Busca o texto do evento no TR predecessor quando o TR atual só tem JS
        function textoAnterior(tr) {
            // 1. Irmãos anteriores no mesmo tbody
            let prev = tr.previousElementSibling;
            while (prev) {
                if (prev.querySelector('a[href="javascript://nop/"]')) break;
                const t = textoTr(prev);
                if (t && !isJsOnly(t)) return t;
                prev = prev.previousElementSibling;
            }
            // 2. Último TR do tbody anterior
            const tbody = tr.closest('tbody');
            const prevTbody = tbody ? tbody.previousElementSibling : null;
            if (prevTbody && prevTbody.tagName === 'TBODY') {
                const trs = Array.from(prevTbody.querySelectorAll('tr')).reverse();
                for (const pt of trs) {
                    if (pt.querySelector('a[href="javascript://nop/"]')) break;
                    const t = textoTr(pt);
                    if (t && !isJsOnly(t)) return t;
                }
            }
            return '';
        }

        return btns.map((a, idx) => {
            const tr = a.closest('tr');
            let texto = textoTr(tr);
            let arquivos = [];
            if (tr) {
                // Câmara Cível: botão i+ fica em TR separado do texto do evento
                if (isJsOnly(texto)) texto = textoAnterior(tr);
                const { subTextos, arquivos: arqs } = coletarSubLinhas(tr);
                texto = (texto + ' ' + subTextos.join(' ')).trim().slice(0, 800);
                arquivos = arqs;
            }
            return { idx, texto, arquivos };
        });
    }""")


def _clicar_iplus(page, idx):
    hrefs_antes = set(page.evaluate("""() =>
        Array.from(document.querySelectorAll('a[href]'))
            .map(a => a.getAttribute('href'))
            .filter(h => h && !h.startsWith('javascript') && h !== '#')
    """))
    page.evaluate(f"""() => {{
        const btns = Array.from(document.querySelectorAll('a[href="javascript://nop/"]'));
        if (btns[{idx}]) btns[{idx}].click();
    }}""")
    time.sleep(2)
    hrefs_depois = page.evaluate("""() =>
        Array.from(document.querySelectorAll('a[href]'))
            .map(a => ({ href: a.getAttribute('href'), texto: (a.innerText||'').trim().slice(0,60) }))
            .filter(l => l.href && !l.href.startsWith('javascript') && l.href !== '#'
                         && !l.href.includes('include_common'))
    """)
    novos = [l for l in hrefs_depois if l['href'] not in hrefs_antes]
    if novos:
        href      = novos[0]['href']
        pdf_nome  = novos[0].get('texto', '')
        url       = href if href.startswith('http') else f"{BASE}{href}"
        return url, pdf_nome
    return "", ""


def _extrair_pdf(page, url_pdf, log):
    try:
        cookies = {c["name"]: c["value"] for c in page.context.cookies()}
        headers = {"User-Agent": "Mozilla/5.0", "Referer": page.url}
        resp = req_http.get(url_pdf, cookies=cookies, headers=headers, timeout=30)
        if resp.status_code != 200:
            return ""
        kb = len(resp.content) // 1024
        with pdfplumber.open(io.BytesIO(resp.content)) as pdf:
            total   = len(pdf.pages)
            paginas = [p.extract_text() or "" for p in pdf.pages]
        texto = "\n".join(paginas).strip()
        log(f"      PDF: {kb} KB · {total} págs. · {len(texto)} chars")
        return texto
    except Exception as e:
        log(f"      ❌ PDF: {e}")
        return ""


# Nomes de arquivo nas sub-linhas "Arquivo: X" (campo `arquivos` de _ler_tabela).
ARQUIVOS_DOC = {
    "acordao":  ["acórdão","acordão","acordao"],
    "sentenca": ["sentença","sentenca","sentencas","sentenças",
                 "sentença de","sentenca de",
                 "decisão monocrática","decisao monocratica","decisão monocrática"],
    "peticao_inicial": ["petição inicial","peticao inicial",
                        "petição de inicial","peticao de inicial",
                        "petição inicial (protocolo)","peticao inicial (protocolo)"],
}

# Palavras no TEXTO DO EVENTO — matching secundário quando não há sub-linhas com arquivo nomeado.
PALAVRAS_EVENTO = {
    "acordao":  ["juntada de acórdão", "juntada de acordao",
                 "juntada de provimento"],  # Câmaras Cíveis usam "provimento"
    "sentenca": ["arquivo: sentença", "arquivo: sentenças", "arquivo: sentenca",
                 "arquivo: sentenca de", "arquivo: sentencas",
                 "sentença", "sentenca", "arquivo: decisão", "arquivo: decisao",
                 "arquivo: decisão monocrática", "arquivo: decisao monocratica",
                 # variações de indeferimento de petição inicial
                 "indeferida a petição", "indeferida a peticao",
                 "indeferimento da petição", "indeferimento da peticao",
                 "petição indeferida", "peticao indeferida",
                 "indeferida a inicial"],
}

# Fallback para sentença: eventos de decisão quando nenhum arquivo é identificado.
PALAVRAS_SENTENCA_FALLBACK = [
    "julgada improcedente", "julgada procedente", "julgada parcialmente",
    "julga improcedente", "julga procedente", "julga parcialmente procedente",
    "julgamento improcedente", "julgamento procedente",
    "decisão monocrática", "decisao monocratica",
]

# Para petição inicial (sem sub-documento padronizado): matching no texto do evento
PALAVRAS_PETICAO = ["petição inicial","peticao inicial","petição de inicial",
                    "peticao de inicial","de inicial","protocolo inicial",
                    "distribuição","distribuicao",
                    "juntada de petição inicial","juntada de peticao inicial",
                    "protocolo de petição","protocolo de peticao",
                    "recebimento de petição inicial","recebimento de peticao inicial"]


_PALAVRAS_TRANSITO = ["transitado em julgado", "trânsito em julgado",
                       "certidão de trânsito", "certidao de transito",
                       "baixa definitiva", "transito em julgado"]

def _e_embargos(texto_evento):
    """Retorna True se o texto do evento indica Embargos de Declaração."""
    tl = texto_evento.lower()
    return any(p in tl for p in [
        "embargos de declaração", "embargos declaratórios", "embargos declaratorios",
        "emb. decl", "emb decl", "embargos declar", "julgamento de embargos",
        "ed de acórdão", "ed de acordao", "ed -", "- ed", "embargo de declaração",
    ])


def _extrair_data_e_transito(page):
    """
    Lê a tabela de movimentações e retorna:
      data_decisao:    data (DD/MM/YYYY) do evento de sentença ou acórdão
      transitado:      True se houver evento de trânsito em julgado (por keyword)
      texto_movimentos: todos os eventos formatados como texto para a IA
    """
    eventos = _ler_tabela(page)
    data_decisao = ""
    transitado   = False
    palavras_decisao = PALAVRAS_EVENTO["sentenca"] + PALAVRAS_EVENTO["acordao"]
    nomes_decisao    = ARQUIVOS_DOC["sentenca"] + ARQUIVOS_DOC["acordao"]
    linhas_mov = []
    for ev in eventos:
        tl = ev['texto'].lower()
        if any(p in tl for p in _PALAVRAS_TRANSITO):
            transitado = True
        é_decisao = (any(p in tl for p in palavras_decisao)
                     or any(a in nomes_decisao for a in ev.get('arquivos', [])))
        if not data_decisao and é_decisao:
            m = re.search(r'\b(\d{2}/\d{2}/\d{4})\b', ev['texto'])
            if m:
                data_decisao = m.group(1)
        linhas_mov.append(ev['texto'])
    texto_movimentos = "\n".join(linhas_mov)
    return data_decisao, transitado, texto_movimentos


def _extrair_doc(page, evento, url_retorno, log):
    """Expande um evento (iPlus) e extrai o texto do documento vinculado."""
    nome_hint = ""
    # Arquivo label (ex: "Petição Inicial", "Sentença") — para com " Ass." ou double-space ou data
    m_arq = re.search(r'[Aa]rquivo:\s*(.{3,120}?)(?:\s{2,}|\s+Ass\.|\d{4}-\d{2}-\d{2}|$)', evento['texto'])
    if m_arq:
        nome_hint = m_arq.group(1).strip()
    elif len(evento['texto']) > 5:
        nome_hint = evento['texto'][:80]

    url_doc, pdf_link_nome = _clicar_iplus(page, evento['idx'])
    if not url_doc:
        log("      ⚠️ Nenhum link novo ao expandir.")
        _clicar_aba(page, "Movimentações")
        return ""

    # Enriquece nome_hint com o nome real do arquivo (ex: "PARCCREDPESS ... .pdf")
    if pdf_link_nome and pdf_link_nome.lower() != 'online.pdf':
        if nome_hint and pdf_link_nome.lower() not in nome_hint.lower():
            nome_hint = f"{nome_hint} | {pdf_link_nome}"
        elif not nome_hint:
            nome_hint = pdf_link_nome

    if "arquivo.do" in url_doc:
        texto = _extrair_pdf(page, url_doc, log)
    else:
        try:
            page.goto(url_doc, timeout=30000)
            page.wait_for_load_state("domcontentloaded")
            texto = page.evaluate("document.body ? document.body.innerText : ''")
            if len(texto) < 200:
                texto = _extrair_pdf(page, url_doc, log)
        except Exception as e:
            log(f"      ❌ {e}")
            texto = ""

    if texto and nome_hint:
        texto = f"[ARQUIVO: {nome_hint}]\n\n{texto}"

    try:
        page.goto(url_retorno, timeout=15000)
        page.wait_for_load_state("domcontentloaded")
        try:
            page.wait_for_load_state("networkidle", timeout=5000)
        except Exception:
            time.sleep(1)
    except Exception as e:
        log(f"      ⚠️ Retorno à página do processo: {e}")
    _clicar_aba(page, "Movimentações")
    time.sleep(1)
    return texto


def _extrair_movimentacoes(page, tipos, url_retorno, log, orgao=""):
    """
    Extrai documentos das movimentações do processo.

    Estratégia:
      1. Filtra eventos pelo nome do arquivo na sub-linha (campo `arquivos`) — mais preciso.
      2. Fallback: texto do evento bate com PALAVRAS_EVENTO.
      3. Fallback sentença: eventos de decisão sem arquivo nomeado (PALAVRAS_SENTENCA_FALLBACK).

    Retorna mérito (mais antigo) e embargos (mais recente), quando há 2+ candidatos distintos.
    """
    resultado = {k: "" for k in tipos}
    resultado["acordao_embargos"]  = ""
    resultado["sentenca_embargos"] = ""

    eventos = _ler_tabela(page)
    if not eventos:
        log("      ⚠️ Tabela de movimentações vazia.")
        return resultado

    orgao_up = orgao.upper()
    _e_camara = 'CÂMARA' in orgao_up or 'CAMARA' in orgao_up or 'NÚCLEO' in orgao_up

    for tipo in tipos:
        if tipo in ("acordao", "sentenca"):
            nomes_arq = ARQUIVOS_DOC.get(tipo, [])
            palavras  = list(PALAVRAS_EVENTO.get(tipo, []))
            if tipo == "acordao" and not _e_camara:
                palavras = [p for p in palavras if p != "juntada de provimento"]

            # 1ª prioridade: arquivo de nome correto na sub-linha
            candidatos = [e for e in eventos
                          if any(a in nomes_arq for a in e.get('arquivos', []))]

            # 2ª prioridade: texto do evento
            if not candidatos:
                candidatos = [e for e in eventos
                              if any(p in e['texto'].lower() for p in palavras)]

            # 3ª prioridade (só sentença): eventos de decisão sem arquivo nomeado
            if not candidatos and tipo == "sentenca":
                candidatos = [e for e in eventos
                              if any(p in e['texto'].lower() for p in PALAVRAS_SENTENCA_FALLBACK)]
                if candidatos:
                    log(f"      ⚠️ Sentença não encontrada — usando fallback (evento de decisão/julgamento).")

            if not candidatos:
                log(f"      ⚠️ '{tipo}' — nenhum candidato encontrado.")
                continue

            # PROJUDI exibe do mais recente ao mais antigo.
            # Separa mérito de embargos pelo CONTEÚDO do evento (não apenas cronologia):
            #   - Candidatos cujo texto indica embargos → lista de embargos
            #   - Restantes → lista de mérito (pega o mais antigo como base)
            candidatos_emb    = [e for e in candidatos if _e_embargos(e['texto'])]
            candidatos_merito = [e for e in candidatos if not _e_embargos(e['texto'])]

            # Se nenhum evento indica explicitamente embargos, cai no critério cronológico
            # (mais antigo = mérito, mais recente = embargos) — comportamento anterior como fallback
            if not candidatos_merito:
                candidatos_merito = candidatos
                candidatos_emb    = []

            merito   = candidatos_merito[-1]   # mais antigo dos de mérito
            embargos = candidatos_emb[0] if candidatos_emb else None  # embargos mais recente

            resultado[tipo] = _extrair_doc(page, merito, url_retorno, log)
            if embargos:
                resultado[f"{tipo}_embargos"] = _extrair_doc(page, embargos, url_retorno, log)

        else:
            # petição inicial
            # 1ª prioridade: arquivo de nome correto na sub-linha (igual à lógica de acórdão/sentença)
            nomes_arq_pet = ARQUIVOS_DOC.get(tipo, [])
            evento = next(
                (e for e in eventos if any(a in nomes_arq_pet for a in e.get('arquivos', []))),
                None
            ) if nomes_arq_pet else None

            # 2ª prioridade: matching no texto do evento
            if not evento:
                evento = next(
                    (e for e in eventos if any(p in e['texto'].lower() for p in PALAVRAS_PETICAO)),
                    None
                )

            if not evento:
                if tipo == "peticao_inicial" and eventos:
                    # 3ª prioridade: evento com Seq. 1 — no PROJUDI a petição inicial é
                    # sempre o primeiro movimento (seq. 1) da tabela de movimentações.
                    # O texto da TR começa com o número da sequência: "1 YYYY-MM-DD..."
                    def _seq_num(e):
                        m = re.match(r'^\s*(\d+)\s', e['texto'])
                        return int(m.group(1)) if m else 9999
                    evento_seq1 = min(eventos, key=_seq_num)
                    if _seq_num(evento_seq1) == 1:
                        evento = evento_seq1
                        log(f"      ℹ️ Petição: usando Seq. 1 — {evento['texto'][:70]}")
                    else:
                        # fallback final: evento mais antigo sem certidão/emenda
                        _excluir_kw = ("certidão", "certidao", "emenda", "despacho",
                                       "ofício", "oficio", "mandado", "citação", "citacao")
                        nomes_excluir = ARQUIVOS_DOC.get("acordao", []) + ARQUIVOS_DOC.get("sentenca", [])
                        sem_excluidos = [e for e in eventos
                                         if not any(kw in e['texto'].lower() for kw in _excluir_kw)
                                         and not any(a in nomes_excluir for a in e.get('arquivos', []))]
                        evento = sem_excluidos[-1] if sem_excluidos else eventos[-1]
                        log(f"      ⚠️ Petição inicial não encontrada por keywords. Usando evento mais antigo: {evento['texto'][:70]}")
                else:
                    log(f"      ⚠️ '{tipo}' não encontrado nos eventos.")
                    continue

            resultado[tipo] = _extrair_doc(page, evento, url_retorno, log)

    return resultado


# ══════════════════════════════════════════════════════════════
# EXTRAÇÃO DE CABEÇALHO
# ══════════════════════════════════════════════════════════════
def _extrair_cabecalho_2g(page):
    """Relator e órgão julgador — garante networkidle antes (igual ao projudi_bot.py)."""
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    relator = _campo_pagina(page, ["Relator:", "Relator"])
    orgao   = _campo_pagina(page, ["Órgão Julgador:", "Órgão Julgador", "Órgão:", "Turma:"])
    return relator.strip(), orgao.strip()


def enriquecer_cabecalho_2g(page, processos, url_busca_2g, log, limite=150):
    """
    Para cada processo sem relator/turma, navega na página individual e extrai os dados.
    Usa a URL direta capturada na listagem quando disponível; caso contrário usa _navegar_2g.
    Limita a 'limite' processos por chamada para controlar o tempo de execução.
    """
    pendentes = [p for p in processos if not p.get('RELATOR') or not p.get('TURMA/CÂMARA')]
    if not pendentes:
        return
    if limite:
        pendentes = pendentes[:limite]
    log(f"🔍 Enriquecendo {len(pendentes)} processo(s) com relator/turma...")
    for i, p in enumerate(pendentes):
        num  = p.get('NÚMERO DO PROCESSO', '')
        url  = p.get('_url', '')
        try:
            if url:
                page.goto(url, timeout=20000)
                try:
                    page.wait_for_load_state("networkidle", timeout=10000)
                except Exception:
                    pass
            else:
                ok = _navegar_2g(page, num, url_busca_2g, log)
                if not ok:
                    continue
            relator, turma = _extrair_cabecalho_2g(page)
            if relator:
                p['RELATOR'] = relator
            if turma:
                p['TURMA/CÂMARA'] = turma
            log(f"   [{i+1}/{len(pendentes)}] {num}: {turma or '?'} | {relator or '?'}")
        except Exception as e:
            log(f"   [{i+1}/{len(pendentes)}] {num}: erro — {e}")


def _extrair_cabecalho_1g(page):
    """Juiz e vara/juízo da página do 1º Grau."""
    url_proc = page.url

    juiz = _campo_pagina(page, ["Juiz:", "Juiz(a):", "Magistrado:", "Juiz Titular:", "Juíza:"])
    if not juiz:
        juiz = page.evaluate("""() => {
            for (const img of document.querySelectorAll('img[id]')) {
                const id = img.id.toUpperCase();
                if (id.includes('JUIZ') || id.includes('MAGISTRAD')) {
                    const parent = img.closest('td') || img.parentElement;
                    if (parent) {
                        const walker = document.createTreeWalker(parent, NodeFilter.SHOW_TEXT);
                        let node;
                        while ((node = walker.nextNode())) {
                            const t = node.textContent.trim();
                            if (t.length > 3) return t;
                        }
                    }
                }
            }
            return '';
        }""") or ""

    vara = ""
    try:
        aba = page.locator("a:has-text('Informações Gerais')").first
        if aba.count() > 0 and aba.is_visible():
            aba.click()
            try:
                page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                time.sleep(2)

            vara = page.evaluate("""() => {
                for (const label of document.querySelectorAll('label')) {
                    const t = (label.innerText || label.textContent || '').trim();
                    if (t.includes('Juízo') || t.includes('Juizo') || t.includes('Vara')) {
                        let next = label.nextSibling;
                        while (next) {
                            const v = (next.textContent || '').trim();
                            if (v.length > 2) return v;
                            next = next.nextSibling;
                        }
                        const el = label.nextElementSibling;
                        if (el) {
                            const v = (el.innerText || el.textContent || '').trim();
                            if (v.length > 2) return v;
                        }
                        const td = label.closest('td');
                        if (td) {
                            const ntd = td.nextElementSibling;
                            if (ntd) return ntd.textContent.trim();
                        }
                    }
                }
                return '';
            }""") or ""
            vara = vara.strip()

            page.goto(url_proc, timeout=20000)
            page.wait_for_load_state("domcontentloaded")
            try:
                page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                time.sleep(2)
    except Exception:
        pass

    if not vara:
        vara = _campo_pagina(page, ["Vara:", "Unidade:", "Juízo:", "Juizo:", "Órgão:"])

    return juiz.strip(), vara.strip()


# ══════════════════════════════════════════════════════════════
# ACESSO À ÍNTEGRA DOS AUTOS
# ══════════════════════════════════════════════════════════════
def _solicitar_acesso_integra(page, log):
    """
    Se a página exibir o botão 'Acesso à íntegra dos autos' (habilitacaoProvisoria),
    navega para o formulário, aceita o termo e clica em Salvar.
    Retorna True se o acesso foi solicitado.
    """
    try:
        btn = page.locator("#habilitacaoProvisoriaButton")
        try:
            visivel = btn.count() > 0 and btn.is_visible(timeout=2000)
        except Exception:
            visivel = False
        if not visivel:
            return False

        log("   🔓 Solicitando acesso à íntegra dos autos...")
        onclick = btn.get_attribute("onclick") or ""
        m = re.search(r"document\.location\.href='([^']+)'", onclick)
        if m:
            url_hab = m.group(1)
            url_hab = url_hab if url_hab.startswith("http") else BASE + url_hab
            page.goto(url_hab, timeout=20000)
        else:
            btn.click()
        page.wait_for_load_state("domcontentloaded")
        try:
            page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            time.sleep(2)

        # Aceita o termo
        chk = page.locator("#termoAceito")
        if chk.count() > 0:
            try:
                if not chk.is_checked():
                    chk.check()
            except Exception:
                pass

        # Clica em Salvar
        salvar = page.locator("#saveButton")
        if salvar.count() > 0:
            salvar.click()
            try:
                page.wait_for_load_state("domcontentloaded")
                page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                time.sleep(2)

        return True
    except Exception as e:
        log(f"   ⚠️ Acesso à íntegra: {e}")
        return False


# ══════════════════════════════════════════════════════════════
# NAVEGAÇÃO
# ══════════════════════════════════════════════════════════════
def _navegar_2g(page, numero_raw, url_busca, log):
    """Navega para um processo de 2º Grau — idêntico ao projudi_bot.py."""
    page.goto(url_busca)
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_selector("#numeroRecurso", timeout=10000)
    page.fill("#numeroRecurso", "")
    page.fill("#numeroRecurso", numero_raw)
    try:
        page.click(
            "input[value='Pesquisar'], button:has-text('Pesquisar'), input[type='submit']",
            timeout=3000,
        )
    except Exception:
        page.keyboard.press("Enter")
    page.wait_for_load_state("domcontentloaded")
    try:
        page.wait_for_load_state("networkidle", timeout=10000)
    except Exception:
        time.sleep(3)

    link = page.locator("a[href*='/projudi/processo/recursal/recurso.do']").first
    if link.count() > 0 and link.is_visible():
        link.click()
        page.wait_for_load_state("domcontentloaded")
        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            time.sleep(2)
        return True

    soup = BeautifulSoup(page.content(), "html.parser")
    for padrao in ["/projudi/processo/recursal/recurso.do",
                   "/projudi/processo/recursal/", "/projudi/processo/"]:
        a = soup.find("a", href=lambda x: x and padrao in x)
        if a:
            href = a["href"]
            url  = href if href.startswith("http") else f"{BASE}{href}"
            page.goto(url, timeout=60000)
            page.wait_for_load_state("domcontentloaded")
            try:
                page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                time.sleep(2)
            return True

    return False


def _navegar_1g(page, numero_raw, url_busca, log):
    """Navega para um processo de 1º Grau."""
    page.goto(url_busca)
    page.wait_for_load_state("domcontentloaded")
    try:
        page.wait_for_load_state("networkidle", timeout=8000)
    except Exception:
        time.sleep(2)

    campo = None
    for sel in ["#numeroProcesso", "input[name='numeroProcesso']",
                "#numero", "#numeroCNJ", "input[name='numero']"]:
        try:
            el = page.locator(sel).first
            if el.count() > 0 and el.is_visible():
                campo = sel
                break
        except Exception:
            continue

    if not campo:
        log("      ⚠️ Campo de busca do 1º Grau não encontrado.")
        return False

    page.fill(campo, "")
    page.fill(campo, numero_raw)
    try:
        page.click(
            "input[value='Pesquisar'], button:has-text('Pesquisar'), input[type='submit']",
            timeout=3000,
        )
    except Exception:
        page.keyboard.press("Enter")
    page.wait_for_load_state("domcontentloaded")
    try:
        page.wait_for_load_state("networkidle", timeout=10000)
    except Exception:
        time.sleep(3)

    link = page.locator("a[href*='/projudi/processo.do']").first
    if link.count() > 0 and link.is_visible():
        link.click()
        page.wait_for_load_state("domcontentloaded")
        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            time.sleep(2)
        return True

    soup = BeautifulSoup(page.content(), "html.parser")
    a = soup.find("a", href=lambda x: x and "/projudi/processo.do" in x)
    if a:
        href = a["href"]
        url  = href if href.startswith("http") else f"{BASE}{href}"
        page.goto(url, timeout=60000)
        page.wait_for_load_state("domcontentloaded")
        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            time.sleep(2)
        return True

    return False


# ══════════════════════════════════════════════════════════════
# PIPELINE PRINCIPAL
# ══════════════════════════════════════════════════════════════
def analisar_processo(page, numero, url_2g, url_1g, log,
                      extrair_textos=True, relator_filtro=None):
    """
    Pesquisa o processo no PROJUDI (2º Grau primeiro, 1º Grau como fallback)
    e extrai os textos das peças processuais.

    relator_filtro: se informado, o processo é ignorado (sem baixar documentos)
                    quando o relator/juiz da capa não contém esse texto.

    Retorna dict com:
      grau, tipo, turma_vara, relator_juiz,
      texto_acordao, texto_sentenca, texto_peticao
      ignorado: True quando filtrado por relator
    """
    numero_raw              = re.sub(r"[^0-9]", "", numero).zfill(20)
    grau                    = None
    tipo                    = ""
    turma_vara              = ""
    relator_juiz            = ""
    texto_acordao           = ""
    texto_acordao_embargos  = ""
    texto_sentenca          = ""
    texto_sentenca_embargos = ""
    texto_peticao           = ""
    data_decisao            = ""
    transitado              = False
    transitado_1g           = False   # trânsito especificamente no 1º grau
    texto_movimentos        = ""      # histórico de movimentos (para a IA avaliar trânsito)
    texto_movimentos_1g     = ""
    juiz_sentenca           = ""      # juiz do 1º grau (quando processo vem do 2g sem acórdão)
    vara_sentenca           = ""

    # ── 2º GRAU ──
    encontrado_2g = False
    if url_2g:
        try:
            log("   🔎 Buscando no 2º Grau...")
            encontrado_2g = _navegar_2g(page, numero_raw, url_2g, log)
        except Exception as e:
            log(f"   ⚠️ 2º Grau: {e}")

    if encontrado_2g:
        grau        = 2
        tipo        = "ACÓRDÃO"
        url_proc_2g = page.url

        if _solicitar_acesso_integra(page, log):
            page.goto(url_proc_2g, timeout=20000)
            page.wait_for_load_state("domcontentloaded")
            try:
                page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                time.sleep(2)

        relator_juiz, turma_vara = _extrair_cabecalho_2g(page)
        log(f"   2g: {turma_vara or '?'} | {relator_juiz or '?'}")

        # Filtro por relator — antes de baixar qualquer documento
        if relator_filtro and relator_filtro.lower() not in relator_juiz.lower():
            log(f"   ⏭️ Relator '{relator_juiz}' ≠ filtro '{relator_filtro}'. Pulando download.")
            return {
                "grau": grau, "tipo": tipo,
                "turma_vara": turma_vara, "relator_juiz": relator_juiz,
                "texto_acordao": "", "texto_acordao_embargos": "",
                "texto_sentenca": "", "texto_sentenca_embargos": "",
                "texto_peticao": "", "data_decisao": "", "transitado": False,
                "ignorado": True,
            }

        try:
            page.goto(url_proc_2g, timeout=20000)
            page.wait_for_load_state("domcontentloaded")
            try:
                page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                time.sleep(2)
            if _clicar_aba(page, "Movimentações"):
                data_decisao, transitado, texto_movimentos = _extrair_data_e_transito(page)
                if extrair_textos:
                    docs = _extrair_movimentacoes(page, ["acordao"], url_proc_2g, log, orgao=turma_vara)
                    texto_acordao          = docs.get("acordao", "")
                    texto_acordao_embargos = docs.get("acordao_embargos", "")
        except Exception as e:
            log(f"   ⚠️ Acórdão: {e}")

        # Extrai sentença e petição via link do 1º Grau na página do 2g
        try:
            page.goto(url_proc_2g, timeout=20000)
            page.wait_for_load_state("domcontentloaded")
            try:
                page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                time.sleep(2)

            # Tenta com filter has_text primeiro (como no teste_leitura_docs.py)
            link_1g = page.locator("a[href*='/projudi/processo.do?_tj=']").filter(has_text="Processo:").first
            if link_1g.count() == 0:
                link_1g = page.locator("a[href*='/projudi/processo.do?_tj=']").first
            if link_1g.count() == 0:
                link_1g = page.locator("a[href*='/projudi/processo.do']").first
            if link_1g.count() > 0:
                link_1g.click()
                page.wait_for_load_state("domcontentloaded")
                try:
                    page.wait_for_load_state("networkidle", timeout=10000)
                except Exception:
                    time.sleep(2)
                url_1g_proc = page.url
                if _solicitar_acesso_integra(page, log):
                    page.goto(url_1g_proc, timeout=20000)
                    page.wait_for_load_state("domcontentloaded")
                    try:
                        page.wait_for_load_state("networkidle", timeout=8000)
                    except Exception:
                        time.sleep(2)
                juiz_sentenca, vara_sentenca = _extrair_cabecalho_1g(page)
                if juiz_sentenca:
                    log(f"   1g: {vara_sentenca or '?'} | {juiz_sentenca or '?'}")
                if _clicar_aba(page, "Movimentações"):
                    data_1g, transitado_1g, texto_movimentos_1g = _extrair_data_e_transito(page)
                    if not data_decisao:
                        data_decisao = data_1g
                        transitado   = transitado_1g
                    if not texto_movimentos:
                        texto_movimentos = texto_movimentos_1g
                    if extrair_textos:
                        # Extrai sentença primeiro
                        docs_1g = _extrair_movimentacoes(
                            page, ["sentenca"], url_1g_proc, log, orgao=turma_vara
                        )
                        texto_sentenca          = docs_1g.get("sentenca", "")
                        texto_sentenca_embargos = docs_1g.get("sentenca_embargos", "")
                        docs_pet = _extrair_movimentacoes(
                            page, ["peticao_inicial"], url_1g_proc, log, orgao=turma_vara
                        )
                        texto_peticao = docs_pet.get("peticao_inicial", "")
            else:
                # Agravo de Instrumento (nº 4009...) e outros recursos de 2g sem origem
                # no PROJUDI não têm link para o 1º Grau — é comportamento esperado.
                log("   ⚠️ Link do 1º Grau não encontrado (pode ser Agravo de Instrumento ou recurso sem origem no PROJUDI).")
        except Exception as e:
            log(f"   ⚠️ 1º Grau (via 2g): {e}")

    else:
        # ── FALLBACK: 1º GRAU ──
        log("   ⚠️ Não localizado no 2º Grau. Tentando 1º Grau...")
        encontrado_1g = False
        if url_1g:
            try:
                encontrado_1g = _navegar_1g(page, numero_raw, url_1g, log)
            except Exception as e:
                log(f"   ⚠️ 1º Grau: {e}")

        if encontrado_1g:
            grau        = 1
            tipo        = "SENTENÇA"
            url_proc_1g = page.url
            if _solicitar_acesso_integra(page, log):
                page.goto(url_proc_1g, timeout=20000)
                page.wait_for_load_state("domcontentloaded")
                try:
                    page.wait_for_load_state("networkidle", timeout=8000)
                except Exception:
                    time.sleep(2)

            relator_juiz, turma_vara = _extrair_cabecalho_1g(page)
            log(f"   1g: {turma_vara or '?'} | {relator_juiz or '?'}")

            # Filtro por relator — antes de baixar qualquer documento
            if relator_filtro and relator_filtro.lower() not in relator_juiz.lower():
                log(f"   ⏭️ Juiz '{relator_juiz}' ≠ filtro '{relator_filtro}'. Pulando download.")
                return {
                    "grau": grau, "tipo": tipo,
                    "turma_vara": turma_vara, "relator_juiz": relator_juiz,
                    "texto_acordao": "", "texto_acordao_embargos": "",
                    "texto_sentenca": "", "texto_sentenca_embargos": "",
                    "texto_peticao": "", "data_decisao": "", "transitado": False,
                    "ignorado": True,
                }

            try:
                if _clicar_aba(page, "Movimentações"):
                    data_decisao, transitado, texto_movimentos = _extrair_data_e_transito(page)
                    transitado_1g = transitado   # processo só no 1g: transitado = transitado_1g
                    texto_movimentos_1g = texto_movimentos
                    if extrair_textos:
                        # Extrai sentença primeiro
                        docs_1g = _extrair_movimentacoes(
                            page, ["sentenca"], url_proc_1g, log, orgao=turma_vara
                        )
                        texto_sentenca          = docs_1g.get("sentenca", "")
                        texto_sentenca_embargos = docs_1g.get("sentenca_embargos", "")
                        docs_pet = _extrair_movimentacoes(
                            page, ["peticao_inicial"], url_proc_1g, log, orgao=turma_vara
                        )
                        texto_peticao = docs_pet.get("peticao_inicial", "")
            except Exception as e:
                log(f"   ⚠️ Docs 1º Grau: {e}")
        else:
            log("   ❌ Processo não encontrado em nenhum grau.")
            return {
                "grau": None, "tipo": "NÃO LOCALIZADO",
                "turma_vara": "", "relator_juiz": "",
                "texto_acordao": "", "texto_sentenca": "", "texto_peticao": "",
            }

    return {
        "grau":                     grau,
        "tipo":                     tipo,
        "turma_vara":               turma_vara,
        "relator_juiz":             relator_juiz,
        "juiz_sentenca":            juiz_sentenca,
        "vara_sentenca":            vara_sentenca,
        "texto_acordao":            texto_acordao,
        "texto_acordao_embargos":   texto_acordao_embargos,
        "texto_sentenca":           texto_sentenca,
        "texto_sentenca_embargos":  texto_sentenca_embargos,
        "texto_peticao":            texto_peticao,
        "data_decisao":             data_decisao,
        "transitado":               transitado,
        "transitado_1g":            transitado_1g,
        "texto_movimentos":         texto_movimentos,
    }


# ══════════════════════════════════════════════════════════════
# DISTRIBUIÇÕES 2º GRAU
# ══════════════════════════════════════════════════════════════

def get_url_distribuicoes_2g(page, log):
    """Encontra a URL da busca de processos recursais (recursoBusca.do) nos frames."""
    log("🔗 Localizando página de distribuições 2º grau...")
    for frame in page.frames:
        try:
            href = frame.evaluate("""() => {
                for (const a of document.querySelectorAll('a[href]')) {
                    const h = a.getAttribute('href') || '';
                    if (h.includes('recursoBusca')) return h;
                }
                return '';
            }""")
            if href:
                return href if href.startswith('http') else BASE + href
        except Exception:
            pass
    # Fallback: regex no HTML bruto
    for frame in page.frames:
        try:
            html = frame.content()
            m = re.search(r'["\'](/projudi/processo/recursal/recursoBusca\.do[^"\']*)["\']', html)
            if m:
                return BASE + m.group(1)
        except Exception:
            pass
    log("   ⚠️ Link recursoBusca não encontrado nos frames.")
    return ""


def _extrair_processos_tabela_dist(html_content):
    """Extrai processos de uma página HTML da tabela recursoBusca."""
    soup = BeautifulSoup(html_content, 'html.parser')
    processos = []
    _CNJ_RE = re.compile(r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}')

    for table in soup.find_all('table'):
        rows = table.find_all('tr')
        if len(rows) < 2:
            continue
        if not _CNJ_RE.search(table.get_text()):
            continue

        # recursive=False: ignora td/th de tabelas aninhadas (ex: célula de partes)
        headers = [c.get_text(strip=True).lower()
                   for c in rows[0].find_all(['th', 'td'], recursive=False)]

        for row in rows[1:]:
            # recursive=False garante alinhamento correto com os headers
            cells = row.find_all(['td', 'th'], recursive=False)
            if not cells:
                continue
            textos = [c.get_text(' ', strip=True) for c in cells]

            numero = ''
            url_proc = ''
            for cell in cells:
                for a in cell.find_all('a'):
                    t = a.get_text(strip=True)
                    if _CNJ_RE.match(t):
                        numero = t
                        href = a.get('href', '')
                        if href and not href.startswith('javascript'):
                            url_proc = href if href.startswith('http') else BASE + href
                        break
                if numero:
                    break
            if not numero:
                for t in textos:
                    m = _CNJ_RE.search(t)
                    if m:
                        numero = m.group(0)
                        break
            if not numero:
                continue

            data_dist = relator = classe = turma = partes = ''
            for idx, h in enumerate(headers):
                if idx >= len(textos):
                    break
                v = textos[idx].strip()
                if not v or v == numero:
                    continue
                if any(k in h for k in ('distribui', 'data dist', 'dt dist')):
                    m = re.search(r'\d{2}/\d{2}/\d{4}', v)
                    if m:
                        data_dist = m.group(0)
                elif 'relator' in h:
                    relator = v.upper()
                elif any(k in h for k in ('classe', 'tipo recurso', 'tipo proc')):
                    if not _CNJ_RE.search(v):
                        classe = v
                elif any(k in h for k in ('turma', 'câmara', 'camara', 'órgão', 'orgao')):
                    turma = v
                elif any(k in h for k in ('parte', 'autor', 'requer', 'apelant')):
                    partes = v

            # Fallback: qualquer data no texto da linha
            if not data_dist:
                for t in textos:
                    m = re.search(r'\d{2}/\d{2}/\d{4}', t)
                    if m and t != numero:
                        data_dist = m.group(0)
                        break

            processos.append({
                'NÚMERO DO PROCESSO':   numero,
                'DATA DE DISTRIBUIÇÃO': data_dist,
                'RELATOR':              relator,
                'TURMA/CÂMARA':         turma,
                'CLASSE':               classe,
                'PARTES':               partes,
                '_url':                 url_proc,   # URL direta do processo (uso interno)
            })

        if processos:
            break

    return processos


def _obter_total_paginas(page):
    """
    Lê o maior número de página nos links de paginação do recursoBuscaForm.
    Os links usam javascript: com atribuição direta ao campo ativosPageNumber,
    ex: href="javascript:document.forms['recursoBuscaForm']['ativosPageNumber'].value='23';..."
    """
    try:
        return int(page.evaluate(r"""() => {
            var max = 1;
            document.querySelectorAll('a').forEach(function(a) {
                var src = (a.getAttribute('href') || '') + (a.getAttribute('onclick') || '');
                var m = src.match(/\[.ativosPageNumber.\]\s*\.value\s*=\s*.(\d+)./);
                if (m) { var n = parseInt(m[1]); if (n > max) max = n; }
            });
            return max;
        }""") or 1)
    except Exception:
        return 1


def _parse_data_dist(s):
    """Converte dd/MM/yyyy para date, ou None se inválido."""
    if not s:
        return None
    try:
        from datetime import date as _date
        p = s.strip().split('/')
        return _date(int(p[2]), int(p[1]), int(p[0]))
    except Exception:
        return None


def _frame_com_maior_conteudo(page):
    """Retorna o frame com maior volume de HTML (onde ficam as tabelas de resultado)."""
    melhor = page.main_frame
    maior_sz = 0
    for frm in page.frames:
        try:
            sz = int(frm.evaluate("() => document.body ? document.body.innerHTML.length : 0") or 0)
            if sz > maior_sz:
                maior_sz = sz
                melhor = frm
        except Exception:
            pass
    return melhor


def _aguardar_frame_conteudo(page, min_chars=2000, timeout_s=10):
    """Aguarda até o frame com conteúdo ter pelo menos min_chars de HTML."""
    import time as _time
    deadline = _time.time() + timeout_s
    while _time.time() < deadline:
        frm = _frame_com_maior_conteudo(page)
        try:
            sz = int(frm.evaluate("() => document.body ? document.body.innerHTML.length : 0") or 0)
            if sz >= min_chars:
                return frm
        except Exception:
            pass
        try:
            page.wait_for_timeout(400)
        except Exception:
            _time.sleep(0.4)
    return _frame_com_maior_conteudo(page)


def buscar_processos_ativos_2g(page, url_dist, log, max_paginas=300,
                                data_ini=None, data_fim=None):
    """
    Scrapa processos recursais ativos ordenados por data de distribuição DESC.
    data_ini / data_fim: strings 'dd/MM/yyyy' para filtrar o período.
    Como a ordem é DESC, encerra a paginação assim que todas as datas da
    página ficam anteriores a data_ini (não há mais nada no intervalo).
    """
    if not url_dist:
        log("   ❌ URL de distribuições não fornecida.")
        return []

    _d_ini = _parse_data_dist(data_ini)
    _d_fim = _parse_data_dist(data_fim)
    periodo = ""
    if data_ini or data_fim:
        periodo = f" | Período: {data_ini or '...'} → {data_fim or '...'}"
    log(f"📋 Carregando página de distribuições 2º grau{periodo}...")

    try:
        page.goto(url_dist)
        try:
            page.wait_for_load_state("networkidle", timeout=20000)
        except Exception:
            pass
    except Exception as e:
        log(f"   ❌ Falha ao navegar: {e}")
        return []

    # Localiza o frame que contém o formulário de busca.
    # O PROJUDI usa frameset — após page.goto, o conteúdo pode estar num sub-frame.
    def _frame_com_form():
        for frm in page.frames:
            try:
                if int(frm.evaluate("() => document.forms.length") or 0) > 0:
                    return frm
            except Exception:
                pass
        return page.main_frame

    frame = _frame_com_form()
    log(f"   📍 Frame do formulário: {(frame.url or 'main')[:80]}")

    log("   🔃 Submetendo formulário (ordenação DESC + filtros de data)...")
    _CAMPOS_INI = ['dataDistribuicaoInicio', 'dtDistribuicaoInicio',
                   'periodoInicio', 'ativoDataDistribuicaoInicio',
                   'ativoDataIni', 'dataIni']
    _CAMPOS_FIM = ['dataDistribuicaoFim', 'dtDistribuicaoFim',
                   'periodoFim', 'ativoDataDistribuicaoFim',
                   'ativoDataFim', 'dataFim']
    ini_js = (data_ini or '').replace("'", "\\'")
    fim_js = (data_fim or '').replace("'", "\\'")
    campos_ini_js = str(_CAMPOS_INI)
    campos_fim_js = str(_CAMPOS_FIM)
    try:
        form_info = frame.evaluate(f"""() => {{
            var f = document.forms['recursoBuscaForm']
                 || document.forms['buscaForm']
                 || document.forms['pesquisaForm']
                 || document.forms[0];
            if (!f) return 'SEM_FORM';
            try {{ f['ativosPageNumber'].value = '1'; }} catch(e) {{}}
            try {{ f['ativosSortColumn'].value = 'r.dataDistribuicao'; }} catch(e) {{}}
            try {{ f['ativosSortOrder'].value = 'DESC'; }} catch(e) {{}}
            var ini = '{ini_js}', fim = '{fim_js}';
            if (ini) {campos_ini_js}.forEach(function(n){{ try{{f[n].value=ini;}}catch(e){{}} }});
            if (fim) {campos_fim_js}.forEach(function(n){{ try{{f[n].value=fim;}}catch(e){{}} }});
            f.submit();
            return f.name || f.id || 'form[0]';
        }}""")
        log(f"   📋 Form submetido: {form_info}")
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        # Aguarda frame filho do frameset de resultado ter conteúdo real
        _aguardar_frame_conteudo(page)
    except Exception as e:
        log(f"   ⚠️ Não foi possível submeter formulário ({e}). Extraindo na ordem atual.")

    processos = []
    pagina = 1
    total_paginas = None  # descoberto na primeira página

    while pagina <= max_paginas:
        # Após submissão/paginação, PROJUDI retorna um frameset com ≈376 chars.
        # O conteúdo real fica num frame filho — aguarda ele carregar.
        frame_alvo = _aguardar_frame_conteudo(page)
        try:
            html = frame_alvo.content()
        except Exception:
            html = page.content()

        novos = _extrair_processos_tabela_dist(html)
        if not novos:
            # Diagnóstico: loga todos os frames e seus tamanhos
            try:
                log(f"   🔍 Total frames: {len(page.frames)}")
                for frm in page.frames:
                    try:
                        sz = len(frm.content())
                        log(f"   🔍 Frame: {(frm.url or 'about:blank')[:100]} ({sz} chars)")
                    except Exception as _fe:
                        log(f"   🔍 Frame [ERR]: {(frm.url or 'about:blank')[:80]} → {_fe}")
                _qualquer_num = re.search(r'\d{7}[\-\.]\d{2}', html)
                if _qualquer_num:
                    log(f"   🔍 Amostra num: {html[max(0,_qualquer_num.start()-5):_qualquer_num.start()+40]!r}")
                else:
                    log(f"   🔍 Sem número de processo no HTML do frame alvo ({len(html)} chars)")
                    log(f"   🔍 Amostra: {html[500:900]!r}")
            except Exception as _e:
                log(f"   🔍 Erro diagnóstico: {_e}")
            log(f"   ⚠️ Página {pagina}: nenhum processo extraído — encerrando.")
            break

        # Filtro de data: aplica data_fim (remove futuros) e detecta saída do intervalo
        if _d_fim or _d_ini:
            filtrados = []
            passou_do_intervalo = False
            for p in novos:
                d = _parse_data_dist(p.get('DATA DE DISTRIBUIÇÃO', ''))
                if _d_fim and d and d > _d_fim:
                    continue                    # mais novo que fim — pula
                if _d_ini and d and d < _d_ini:
                    passou_do_intervalo = True  # mais antigo que ini — para paginação
                    continue
                filtrados.append(p)
            novos = filtrados
            if passou_do_intervalo:
                processos.extend(novos)
                log(f"   🛑 Data anterior a {data_ini} encontrada — encerrando busca.")
                break

        processos.extend(novos)

        # Na primeira página descobre o total de páginas pelos links de paginação
        if total_paginas is None:
            try:
                total_paginas = min(int(frame_alvo.evaluate(r"""() => {
                    var max = 1;
                    document.querySelectorAll('a').forEach(function(a) {
                        var src = (a.getAttribute('href') || '') + (a.getAttribute('onclick') || '');
                        var m = src.match(/\[.ativosPageNumber.\]\s*\.value\s*=\s*.(\d+)./);
                        if (m) { var n = parseInt(m[1]); if (n > max) max = n; }
                    });
                    return max;
                }""") or 1), max_paginas)
            except Exception:
                total_paginas = 1
        log(f"   📄 Página {pagina}/{total_paginas or '?'}: {len(novos)} processo(s) | Total: {len(processos)}")

        if pagina >= (total_paginas or 1):
            break

        pagina += 1
        try:
            frame_alvo.evaluate(f"""() => {{
                var f = document.forms['recursoBuscaForm']
                     || document.forms['buscaForm']
                     || document.forms[0];
                if (!f) return;
                try {{ f['ativosPageNumber'].value = '{pagina}'; }} catch(e) {{}}
                f.submit();
            }}""")
            try:
                page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                pass
            _aguardar_frame_conteudo(page)
        except Exception as e:
            log(f"   ⚠️ Erro ao avançar página: {e}")
            break

    # Ordena por DATA DE DISTRIBUIÇÃO DESC em Python como garantia,
    # independente de o servidor ter aplicado a ordenação corretamente.
    from datetime import date as _date_cls
    processos.sort(
        key=lambda p: _parse_data_dist(p.get('DATA DE DISTRIBUIÇÃO', '')) or _date_cls.min,
        reverse=True,
    )

    log(f"   ✅ Total: {len(processos)} processo(s) ativo(s) em {pagina} página(s).")
    return processos
