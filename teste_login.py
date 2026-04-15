"""
teste_login.py — Testa o login no PROJUDI localmente com navegador visível.

Uso:
  python teste_login.py                         → testa CPF/senha do config.ini [projudi]
  python teste_login.py NICOLAS                 → testa o usuário NICOLAS GOMES
  python teste_login.py LUIS                    → testa o usuário LUIS ALBERT
  python teste_login.py HELADIO                 → testa o usuário HELÁDIO JÚNIOR
  python teste_login.py --processo 00000000000  → testa login + busca de 1 processo
"""
import sys, time, configparser, re
from pathlib import Path
from playwright.sync_api import sync_playwright

# ── Importa funções do projudi.py ──
sys.path.insert(0, str(Path(__file__).parent))
import projudi

INI = Path(__file__).parent / "config.ini"

def _ler_credenciais(filtro: str = ""):
    cfg = configparser.ConfigParser()
    cfg.read(INI, encoding="utf-8")

    # Se filtro vazio: usa [projudi] cpf/senha do config
    if not filtro:
        cpf   = cfg.get("projudi", "cpf",   fallback="")
        senha = cfg.get("projudi", "senha", fallback="")
        label = "projudi"
        return cpf, senha, label

    # Procura nos usuários cadastrados
    filtro_up = filtro.upper()
    i = 0
    while cfg.has_option("usuarios", f"cpf_{i}"):
        label = cfg.get("usuarios", f"label_{i}", fallback="")
        if filtro_up in label.upper():
            cpf   = cfg.get("usuarios", f"cpf_{i}",   fallback="")
            senha = cfg.get("usuarios", f"senha_{i}", fallback="")
            return cpf, senha, label
        i += 1

    print(f"❌ Usuário '{filtro}' não encontrado no config.ini.")
    sys.exit(1)


def _log(msg):
    print(msg, flush=True)


def main():
    args = sys.argv[1:]
    numero_teste = None
    filtro_usuario = ""

    i = 0
    while i < len(args):
        if args[i] == "--processo" and i + 1 < len(args):
            numero_teste = args[i + 1]
            i += 2
        else:
            filtro_usuario = args[i]
            i += 1

    cpf, senha, label = _ler_credenciais(filtro_usuario)

    if not cpf or not senha:
        print("❌ CPF ou senha vazio no config.ini.")
        sys.exit(1)

    cpf_mask = cpf[:3] + ".***.***-" + cpf[-2:] if len(re.sub(r'\D','',cpf)) == 11 else cpf
    print(f"\n{'='*55}")
    print(f"  Usuário : {label}")
    print(f"  CPF     : {cpf_mask}")
    print(f"  Processo: {numero_teste or '(nenhum — só login + menus)'}")
    print(f"{'='*55}\n")

    with sync_playwright() as pw:
        # headless=False: navegador visível para depuração visual
        browser = pw.chromium.launch(
            headless=False,
            slow_mo=300,   # 300 ms entre ações — dá para acompanhar visualmente
            args=["--no-sandbox"],
        )
        context = browser.new_context(
            no_viewport=True,
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()

        try:
            # ── 1. LOGIN ──
            projudi.login(page, cpf, senha, _log)

            # ── 2. CAPTURA DE URLs ──
            print()
            url_2g, url_1g = projudi.get_urls_busca(page, _log)
            print(f"\n  URL 2º Grau : {url_2g or '(não encontrada)'}")
            print(f"  URL 1º Grau : {url_1g or '(não encontrada)'}")

            if not url_2g and not url_1g:
                print("\n⚠️  Nenhuma URL de busca encontrada — verifique os menus no navegador.")
            else:
                print("\n✅ Login e menus OK.\n")

            # ── 3. TESTE DE PROCESSO (opcional) ──
            if numero_teste:
                print(f"\n{'='*55}")
                print(f"  Testando processo: {numero_teste}")
                print(f"{'='*55}\n")
                dados = projudi.analisar_processo(
                    page, numero_teste, url_2g, url_1g, _log,
                    extrair_textos=True,
                )
                print(f"\n{'='*55}")
                print(f"  Grau        : {dados.get('grau')}")
                print(f"  Tipo        : {dados.get('tipo')}")
                print(f"  Turma/Vara  : {dados.get('turma_vara')}")
                print(f"  Relator/Juiz: {dados.get('relator_juiz')}")
                print(f"  Data Decisão: {dados.get('data_decisao')}")
                print(f"  Transitado  : {dados.get('transitado')}")
                tam_acordao  = len(dados.get('texto_acordao', ''))
                tam_sentenca = len(dados.get('texto_sentenca', ''))
                tam_peticao  = len(dados.get('texto_peticao', ''))
                print(f"  Acórdão     : {tam_acordao} chars")
                print(f"  Sentença    : {tam_sentenca} chars")
                print(f"  Petição     : {tam_peticao} chars")
                print(f"{'='*55}\n")

            # Mantém o navegador aberto 10s para inspeção visual antes de fechar
            print("Fechando navegador em 10 segundos... (Ctrl+C para cancelar)")
            time.sleep(10)

        except KeyboardInterrupt:
            print("\n(Cancelado pelo usuário)")
        except Exception as e:
            print(f"\n❌ ERRO: {e}")
            import traceback; traceback.print_exc()
            print("\nNavegador permanece aberto para inspeção. Pressione Enter para fechar.")
            try:
                input()
            except Exception:
                time.sleep(30)
        finally:
            try:
                browser.close()
            except Exception:
                pass


if __name__ == "__main__":
    main()
