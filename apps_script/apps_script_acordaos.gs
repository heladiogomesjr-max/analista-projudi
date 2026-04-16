// ╔══════════════════════════════════════════════════════════════╗
// ║  ANALISTA PROJUDI — Apps Script                             ║
// ║  Funções: doGet (leitura dashboard) + doPost (escrita)      ║
// ╚══════════════════════════════════════════════════════════════╝

// ── CONFIGURAÇÃO ─────────────────────────────────────────────
const ADVOGADOS = {
  'LUIS_ALBERT':   '1-YfvO5o66OxLWtCbRkE7XZE2OvJpdYS8InSd3mCyU0E',
  'NICOLAS_GOMES': '1ZiUz7JCigtXiKEcNZa4qU8nmjrMlOFmFLZfql3Lchg8',
};

const COLUNAS = [
  'NÚMERO DO PROCESSO',
  'DATA DA DECISÃO',
  'RELATOR/JUIZ',
  'STATUS DA DECISÃO',
  'MATÉRIA',
  'DANO MATERIAL',
  'DANO MORAL',
  'RESUMO DO PROCESSO',
  'TRANSITADO EM JULGADO?',
];

// Índice da coluna STATUS DA DECISÃO (base 0)
const I_STATUS = COLUNAS.indexOf('STATUS DA DECISÃO');

// Migração: renomeia abas antigas para o nome correto do PROJUDI
const RENOMEAR_ABAS = {
  '1 TURMA': '1ª Turma Recursal',
  '2 TURMA': '2ª Turma Recursal',
  '3 TURMA': '3ª Turma Recursal',
  '4 TURMA': '4ª Turma Recursal - Fazenda',
};

// Formatação da célula STATUS DA DECISÃO por valor
const STATUS_FORMATO = {
  'FAVORÁVEL':              { bg: '#b7e1cd', fg: '#0d6b3a' },
  'DESFAVORÁVEL':           { bg: '#f4cccc', fg: '#990000' },
  'EXTINTO SEM MÉRITO':     { bg: '#c9daf8', fg: '#1155cc' },
  'SENTENÇA ANULADA':       { bg: '#fff2cc', fg: '#b45309' },
  'ACORDO HOMOLOGADO':      { bg: '#d0e8f5', fg: '#1a5276' },
  'SEM PARECER CONCLUSIVO': { bg: '#efefef', fg: '#888888' },
};

// Abas ignoradas na leitura do dashboard
const ABAS_SISTEMA = ['_config', '_log', 'Config', 'Log'];

// Retorna true se a aba é de Turma Recursal ou Câmara (2º grau).
// APENAS "TURMA" e "CAMARA" identificam 2º grau com segurança.
// "CIVEL" foi removido: "Vara Cível" também contém essa palavra e é 1º grau.
function _ehOrgao2g(nome) {
  var n = nome.toUpperCase()
              .normalize('NFD').replace(/[\u0300-\u036f]/g, ''); // remove acentos
  return n.indexOf('TURMA')  !== -1
      || n.indexOf('CAMARA') !== -1;
}


// ── MIGRAÇÃO DE NOMES ─────────────────────────────────────────
function _migrarNomesAbas(ss) {
  if (!ss) return;
  ss.getSheets().forEach(function(ws) {
    var nome = ws.getName();
    if (RENOMEAR_ABAS[nome]) {
      ws.setName(RENOMEAR_ABAS[nome]);
    }
  });
}


// ── LEITURA (GET) ─────────────────────────────────────────────
function doGet(e) {
  var adv     = normalizar(e && e.parameter ? e.parameter.adv : 'LUIS_ALBERT');
  var sheetId = ADVOGADOS[adv];

  try {
    if (!sheetId) throw new Error('Planilha não configurada para: ' + adv);

    var ss = SpreadsheetApp.openById(sheetId);
    _migrarNomesAbas(ss);

    var rows = [];

    ss.getSheets().forEach(function(ws) {
      var nome = ws.getName();
      if (ABAS_SISTEMA.indexOf(nome) !== -1) return;
      if (!_ehOrgao2g(nome)) return; // ignora abas de Varas (1º grau)

      var data = ws.getDataRange().getValues();
      if (data.length < 2) return;

      var hdrs  = data[0].map(String);
      var iProc = hdrs.indexOf('NÚMERO DO PROCESSO');
      var iData = hdrs.indexOf('DATA DA DECISÃO');
      var iRel  = hdrs.indexOf('RELATOR/JUIZ');
      var iStat = hdrs.indexOf('STATUS DA DECISÃO');
      var iMat  = hdrs.indexOf('MATÉRIA');
      var iDm   = hdrs.indexOf('DANO MATERIAL');
      var iMo   = hdrs.indexOf('DANO MORAL');
      var iTj   = hdrs.indexOf('TRANSITADO EM JULGADO?');

      if (iProc === -1) return;

      for (var i = 1; i < data.length; i++) {
        var r = data[i];
        if (!r[iProc]) continue;
        rows.push({
          p:  String(r[iProc] || ''),
          d:  _formatData(r[iData]),
          r:  String(r[iRel]  || ''),
          s:  String(r[iStat] || ''),
          mt: String(r[iMat]  || ''),
          dm: parseNumero(r[iDm]),
          mo: parseNumero(r[iMo]),
          tv: nome,
          tj: iTj !== -1 ? String(r[iTj] || '') : '',
        });
      }
    });

    return ok({ data: rows, adv: adv, updatedAt: new Date().toISOString() });

  } catch (err) {
    return erro(err.message);
  }
}


// ── ESCRITA (POST) ────────────────────────────────────────────
function doPost(e) {
  try {
    var payload = JSON.parse(e.postData.contents);
    var adv     = normalizar(payload.adv || 'LUIS_ALBERT');
    var sheetId = payload.sheet_id || ADVOGADOS[adv];
    var tab     = (payload.tab || 'Geral').toString().trim();
    var rows    = payload.rows || [];
    var modo    = payload.modo || 'append';

    if (!sheetId) throw new Error('sheet_id não informado e advogado não configurado: ' + adv);

    var ss = SpreadsheetApp.openById(sheetId);
    _migrarNomesAbas(ss);

    var ws = ss.getSheetByName(tab);

    // Cria a aba se não existir
    if (!ws) {
      ws = ss.insertSheet(tab);
      _escreverCabecalho(ws);
    }

    // Modo replace: limpa dados (mantém cabeçalho)
    if (modo === 'replace' && ws.getLastRow() > 1) {
      ws.deleteRows(2, ws.getLastRow() - 1);
    }

    // Índice de processos existentes (evita duplicatas)
    var existentes = {};
    if (ws.getLastRow() > 1) {
      ws.getRange(2, 1, ws.getLastRow() - 1, 1).getValues()
        .forEach(function(r) { if (r[0]) existentes[String(r[0])] = true; });
    }

    var inseridos = 0;
    rows.forEach(function(row) {
      var proc = String(row['NÚMERO DO PROCESSO'] || '').trim();
      if (!proc || existentes[proc]) return;

      var novaLinha = COLUNAS.map(function(col) {
        return row[col] !== undefined ? row[col] : '';
      });

      _inserirLinhaFormatada(ws, novaLinha);
      existentes[proc] = true;
      inseridos++;
    });

    SpreadsheetApp.flush();
    return ok({ inseridos: inseridos, duplicatas: rows.length - inseridos, tab: tab });

  } catch (err) {
    return erro(err.message);
  }
}


// ── INSERÇÃO COM FORMATAÇÃO ───────────────────────────────────
function _inserirLinhaFormatada(ws, novaLinha) {
  var ultimaLinha = ws.getLastRow();
  var numCols     = COLUNAS.length;

  ws.appendRow(novaLinha);
  var novaIdx = ws.getLastRow();

  // Copia formato da linha anterior (preserva fonte, alinhamento, bordas)
  if (ultimaLinha > 1) {
    ws.getRange(ultimaLinha, 1, 1, numCols).copyTo(
      ws.getRange(novaIdx, 1, 1, numCols),
      SpreadsheetApp.CopyPasteType.PASTE_FORMAT,
      false
    );
  }

  // Aplica cor da célula STATUS DA DECISÃO conforme o valor
  var statusVal = String(novaLinha[I_STATUS] || '').trim();
  var fmt       = STATUS_FORMATO[statusVal];
  if (fmt) {
    var celStat = ws.getRange(novaIdx, I_STATUS + 1);
    celStat.setBackground(fmt.bg)
           .setFontColor(fmt.fg)
           .setFontWeight('bold');
  }
}


// ── CABEÇALHO (aba nova) ──────────────────────────────────────
function _escreverCabecalho(ws) {
  ws.appendRow(COLUNAS);
  ws.getRange(1, 1, 1, COLUNAS.length)
    .setFontWeight('bold')
    .setBackground('#1a1a18')
    .setFontColor('#f5f4f0')
    .setHorizontalAlignment('center');
  ws.setFrozenRows(1);
}


// ── UTILITÁRIOS ───────────────────────────────────────────────
function _formatData(v) {
  if (!v) return '';
  if (v instanceof Date) return Utilities.formatDate(v, Session.getScriptTimeZone(), 'dd/MM/yyyy');
  return String(v);
}

function normalizar(adv) {
  return String(adv || 'LUIS_ALBERT').toUpperCase().replace(/ /g, '_');
}

function parseNumero(v) {
  if (v === null || v === undefined || v === '') return 0;
  if (typeof v === 'number') return isNaN(v) ? 0 : v;   // já é número — não mexe no ponto decimal
  var n = parseFloat(String(v).replace(/[R$\s.]/g, '').replace(',', '.'));
  return isNaN(n) ? 0 : n;
}

function ok(data) {
  return ContentService
    .createTextOutput(JSON.stringify(Object.assign({ ok: true }, data)))
    .setMimeType(ContentService.MimeType.JSON);
}

function erro(msg) {
  return ContentService
    .createTextOutput(JSON.stringify({ ok: false, error: msg }))
    .setMimeType(ContentService.MimeType.JSON);
}
