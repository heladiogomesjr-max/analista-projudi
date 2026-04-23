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

const COLUNAS_DIST = [
  'NÚMERO DO PROCESSO',
  'DATA DE DISTRIBUIÇÃO',
  'RELATOR',
  'TURMA/CÂMARA',
  'CLASSE',
  'STATUS DO JULGAMENTO',
  'DATA DE CAPTURA',
];

const STATUS_JULGAMENTO_FORMATO = {
  'Pendente': { bg: '#fff2cc', fg: '#7d4e00' },
  'Pautado':  { bg: '#c9daf8', fg: '#1155cc' },
  'Julgado':  { bg: '#b7e1cd', fg: '#0d6b3a' },
};

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


// ── LIMPEZA DE ABAS ───────────────────────────────────────────
function _limparAbas(ss) {
  var removidas = [];
  ss.getSheets().forEach(function(ws) {
    var nome = ws.getName();
    if (ABAS_SISTEMA.indexOf(nome) !== -1) return;
    if (_ehOrgao2g(nome)) return;
    ss.deleteSheet(ws);
    removidas.push(nome);
  });
  return removidas;
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
  var params  = e && e.parameter ? e.parameter : {};
  var adv     = normalizar(params.adv || 'LUIS_ALBERT');
  var sheetId = ADVOGADOS[adv];

  // Limpeza: remove abas de Vara/JE (não são Turma/Câmara)
  if (params.action === 'cleanup') {
    try {
      if (!sheetId) throw new Error('Planilha não configurada para: ' + adv);
      var ss        = SpreadsheetApp.openById(sheetId);
      var removidas = _limparAbas(ss);
      return ok({ removidas: removidas, total: removidas.length });
    } catch (err) {
      return erro(err.message);
    }
  }

  // Padronização: converte RELATOR/JUIZ para caixa alta em todas as abas
  if (params.action === 'uppercase_relator') {
    try {
      if (!sheetId) throw new Error('Planilha não configurada para: ' + adv);
      var ss         = SpreadsheetApp.openById(sheetId);
      var colRelator = COLUNAS.indexOf('RELATOR/JUIZ') + 1; // base-1 para Sheets
      var totalCels  = 0;
      ss.getSheets().forEach(function(ws) {
        var nome = ws.getName();
        if (ABAS_SISTEMA.indexOf(nome) !== -1) return;
        if (!_ehOrgao2g(nome)) return;
        var lastRow = ws.getLastRow();
        if (lastRow < 2) return;
        var range = ws.getRange(2, colRelator, lastRow - 1, 1);
        var vals  = range.getValues();
        var atualizados = vals.map(function(row) {
          return [row[0] ? String(row[0]).toUpperCase() : row[0]];
        });
        range.setValues(atualizados);
        totalCels += lastRow - 1;
      });
      return ok({ atualizados: totalCels });
    } catch (err) {
      return erro(err.message);
    }
  }

  // Leitura da aba Distribuições 2G
  if (params.action === 'distribuicoes') {
    try {
      if (!sheetId) throw new Error('Planilha não configurada para: ' + adv);
      var ss  = SpreadsheetApp.openById(sheetId);
      var ws  = ss.getSheetByName('Distribuições 2G');
      if (!ws || ws.getLastRow() < 2) return ok({ data: [], adv: adv });
      var data = ws.getDataRange().getValues();
      var hdrs = data[0].map(String);
      var iDataDist = hdrs.indexOf('DATA DE DISTRIBUIÇÃO');
      var iDataCap  = hdrs.indexOf('DATA DE CAPTURA');
      var rows = [];
      for (var i = 1; i < data.length; i++) {
        var r = data[i];
        var obj = {};
        hdrs.forEach(function(h, idx) {
          if (idx === iDataDist || idx === iDataCap) {
            obj[h] = _formatData(r[idx]);
          } else {
            obj[h] = String(r[idx] || '');
          }
        });
        if (obj['NÚMERO DO PROCESSO']) rows.push(obj);
      }
      var wsJulg0 = ss.getSheetByName('Julgados');
      var totalJulgados = wsJulg0 ? Math.max(0, wsJulg0.getLastRow() - 1) : 0;
      return ok({ data: rows, adv: adv, updatedAt: new Date().toISOString(), totalJulgados: totalJulgados });
    } catch (err) {
      return erro(err.message);
    }
  }

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
    _limparAbas(ss);

    // Modo distribuições: usa COLUNAS_DIST e aba 'Distribuições 2G'
    if (payload.tipo === 'distribuicoes') {
      var wsDist = ss.getSheetByName('Distribuições 2G');
      if (!wsDist) {
        wsDist = ss.insertSheet('Distribuições 2G');
        wsDist.appendRow(COLUNAS_DIST);
        wsDist.getRange(1, 1, 1, COLUNAS_DIST.length)
          .setFontWeight('bold').setBackground('#1a1a18').setFontColor('#f5f4f0')
          .setHorizontalAlignment('center');
        wsDist.setFrozenRows(1);
      }

      var iStatusDist = COLUNAS_DIST.indexOf('STATUS DO JULGAMENTO');
      var batchMode   = payload.batch_mode || 'replace_first';
      var doCleanup   = payload.cleanup !== false;

      // Filtra e monta matriz de dados (sem chamadas à planilha)
      var dataToWrite = [];
      rows.forEach(function(row) {
        if (!_normProc(row['NÚMERO DO PROCESSO'])) return;
        dataToWrite.push(COLUNAS_DIST.map(function(col) {
          return row[col] !== undefined ? row[col] : '';
        }));
      });
      var inseridosDist = dataToWrite.length;

      var startRow;
      if (batchMode === 'replace_first') {
        // Limpa todas as linhas de dados existentes (1 chamada)
        var lastExisting = wsDist.getLastRow();
        if (lastExisting > 1) {
          wsDist.deleteRows(2, lastExisting - 1);
        }
        startRow = 2;
      } else {
        // append_rest: escreve após a última linha
        startRow = wsDist.getLastRow() + 1;
      }

      // Escreve todo o lote em 1 chamada
      if (dataToWrite.length > 0) {
        wsDist.getRange(startRow, 1, dataToWrite.length, COLUNAS_DIST.length)
          .setValues(dataToWrite);
      }

      // Formatação do STATUS em batch: setBackgrounds/setFontColors/setFontWeights
      // aceitam matrizes — 3 chamadas para N linhas
      if (iStatusDist !== -1 && dataToWrite.length > 0) {
        var bgMatrix  = dataToWrite.map(function(r) {
          var f = STATUS_JULGAMENTO_FORMATO[String(r[iStatusDist] || '')];
          return [f ? f.bg : null];
        });
        var fgMatrix  = dataToWrite.map(function(r) {
          var f = STATUS_JULGAMENTO_FORMATO[String(r[iStatusDist] || '')];
          return [f ? f.fg : null];
        });
        var fwMatrix  = dataToWrite.map(function(r) {
          return [STATUS_JULGAMENTO_FORMATO[String(r[iStatusDist] || '')] ? 'bold' : 'normal'];
        });
        var statusRange = wsDist.getRange(startRow, iStatusDist + 1, dataToWrite.length, 1);
        statusRange.setBackgrounds(bgMatrix);
        statusRange.setFontColors(fgMatrix);
        statusRange.setFontWeights(fwMatrix);
      }

      // Remove linhas Julgado (only on final batch) + arquiva em aba Julgados
      if (doCleanup && iStatusDist !== -1) {
        var julgadosNorm = {};
        ss.getSheets().forEach(function(ws2) {
          var n2 = ws2.getName();
          if (ABAS_SISTEMA.indexOf(n2) !== -1 || n2 === 'Distribuições 2G' || n2 === 'Julgados') return;
          if (!_ehOrgao2g(n2)) return;
          var lr2 = ws2.getLastRow();
          if (lr2 < 2) return;
          ws2.getRange(2, 1, lr2 - 1, 1).getValues().forEach(function(rv) {
            if (rv[0]) julgadosNorm[_normProc(rv[0])] = true;
          });
        });
        var lastR = wsDist.getLastRow();
        if (lastR > 1) {
          var allDistData = wsDist.getRange(2, 1, lastR - 1, COLUNAS_DIST.length).getValues();
          var rowsToDelete = [];
          for (var ri = 0; ri < allDistData.length; ri++) {
            var procNorm  = _normProc(allDistData[ri][0]);
            var statusCel = String(allDistData[ri][iStatusDist] || '');
            if (statusCel === 'Julgado' || julgadosNorm[procNorm]) {
              rowsToDelete.push(ri + 2);
            }
          }

          // Arquiva em aba Julgados antes de excluir
          if (rowsToDelete.length > 0) {
            var COLUNAS_JULG = COLUNAS_DIST.concat(['DATA DO JULGAMENTO']);
            var wsJulg = ss.getSheetByName('Julgados');
            if (!wsJulg) {
              wsJulg = ss.insertSheet('Julgados');
              wsJulg.appendRow(COLUNAS_JULG);
              wsJulg.getRange(1, 1, 1, COLUNAS_JULG.length)
                .setFontWeight('bold').setBackground('#1a1a18').setFontColor('#f5f4f0')
                .setHorizontalAlignment('center');
              wsJulg.setFrozenRows(1);
            }
            var julgLastRow = wsJulg.getLastRow();
            var julgExist   = {};
            if (julgLastRow > 1) {
              wsJulg.getRange(2, 1, julgLastRow - 1, 1).getValues().forEach(function(r) {
                if (r[0]) julgExist[_normProc(r[0])] = true;
              });
            }
            var hoje    = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'dd/MM/yyyy');
            var newJulg = [];
            rowsToDelete.forEach(function(sheetRow) {
              var rowData = allDistData[sheetRow - 2];
              var pn = _normProc(rowData[0]);
              if (!julgExist[pn]) {
                newJulg.push(rowData.concat([hoje]));
                julgExist[pn] = true;
              }
            });
            if (newJulg.length > 0) {
              wsJulg.getRange(julgLastRow + 1, 1, newJulg.length, COLUNAS_JULG.length)
                .setValues(newJulg);
            }
          }

          for (var d = rowsToDelete.length - 1; d >= 0; d--) {
            wsDist.deleteRow(rowsToDelete[d]);
          }
        }
      }

      SpreadsheetApp.flush();
      return ok({ inseridos: inseridosDist, tab: 'Distribuições 2G' });
    }

    // Rejeita abas que não sejam Turma/Câmara (2º grau)
    if (!_ehOrgao2g(tab)) {
      return ok({ inseridos: 0, duplicatas: 0, tab: tab, aviso: 'aba ignorada (não é Turma/Câmara)' });
    }

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

    // Modo upsert: atualiza linha existente pelo NÚMERO DO PROCESSO, senão insere nova
    if (modo === 'upsert') {
      var lastRow = ws.getLastRow();
      var idxPorProc = {};
      if (lastRow > 1) {
        ws.getRange(2, 1, lastRow - 1, 1).getValues()
          .forEach(function(r, i) {
            if (r[0]) idxPorProc[_normProc(r[0])] = i + 2; // +2: base-1 + pular cabeçalho
          });
      }
      var inseridos = 0;
      rows.forEach(function(row) {
        var proc = _normProc(row['NÚMERO DO PROCESSO']);
        if (!proc) return;
        var novaLinha = COLUNAS.map(function(col) {
          return row[col] !== undefined ? row[col] : '';
        });
        if (idxPorProc[proc]) {
          ws.getRange(idxPorProc[proc], 1, 1, COLUNAS.length).setValues([novaLinha]);
          _aplicarFormatoStatus(ws, idxPorProc[proc], novaLinha);
        } else {
          _inserirLinhaFormatada(ws, novaLinha);
          idxPorProc[proc] = ws.getLastRow();
        }
        inseridos++;
      });
      SpreadsheetApp.flush();
      return ok({ inseridos: inseridos, tab: tab });
    }

    // Índice de processos existentes (evita duplicatas — modo append)
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

  _aplicarFormatoStatus(ws, novaIdx, novaLinha);
}

function _aplicarFormatoStatus(ws, rowIdx, novaLinha) {
  var statusVal = String(novaLinha[I_STATUS] || '').trim();
  var fmt       = STATUS_FORMATO[statusVal];
  if (fmt) {
    ws.getRange(rowIdx, I_STATUS + 1)
      .setBackground(fmt.bg)
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
function _normProc(v) {
  return String(v || '').replace(/\D/g, '');
}

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
