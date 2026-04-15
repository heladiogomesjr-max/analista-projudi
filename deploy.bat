@echo off
SET KEY=C:\Users\Admin\.ssh\ssh-key-2026-04-03.key
SET SERVER=opc@129.146.135.39

echo Corrigindo permissao da chave SSH...
icacls "%KEY%" /inheritance:r /grant:r "Admin:R" >nul 2>&1

echo Fazendo deploy para a VM...
ssh -i "%KEY%" %SERVER% "cd /opt/analista-projudi && sudo git pull origin main && sudo systemctl restart analista-projudi && sudo systemctl status analista-projudi --no-pager -l"

echo.
echo Deploy concluido!
pause
