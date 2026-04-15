@echo off
SET KEY=C:\Users\Admin\.ssh\ssh-key-2026-04-03.key
SET SERVER=opc@129.146.135.39
SET PASTA=C:\Users\Admin\OneDrive\Documentos\PROJETOS\ANALISTA PROJUDI

echo Corrigindo permissao da chave SSH...
icacls "%KEY%" /inheritance:r /grant:r "Admin:R" >nul 2>&1

echo Enviando arquivos para o servidor...
scp -i "%KEY%" "%PASTA%\app.py"          %SERVER%:/tmp/app.py
scp -i "%KEY%" "%PASTA%\workers.py"      %SERVER%:/tmp/workers.py
scp -i "%KEY%" "%PASTA%\ia.py"           %SERVER%:/tmp/ia.py
scp -i "%KEY%" "%PASTA%\projudi.py"      %SERVER%:/tmp/projudi.py
scp -i "%KEY%" "%PASTA%\djen.py"         %SERVER%:/tmp/djen.py
scp -i "%KEY%" "%PASTA%\sheets.py"       %SERVER%:/tmp/sheets.py
scp -i "%KEY%" "%PASTA%\MODELO.xlsx"     %SERVER%:/tmp/MODELO.xlsx

echo Instalando no servidor e reiniciando servico...
ssh -i "%KEY%" %SERVER% "sudo cp /tmp/app.py /tmp/workers.py /tmp/ia.py /tmp/projudi.py /tmp/djen.py /tmp/sheets.py /tmp/MODELO.xlsx /opt/analista-projudi/ && sudo systemctl restart analista-projudi && sudo systemctl status analista-projudi --no-pager -l"

echo.
echo Deploy concluido!
pause
