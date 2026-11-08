$s = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$r = Invoke-WebRequest -Uri "http://127.0.0.1:8123/cuentas/entrar/" -UseBasicParsing -WebSession $s
$token = ([regex]::Match($r.Content, '"csrfmiddlewaretoken" value="([^"]+)"')).Groups[1].Value
$body = "username=admin&password=admin123&csrfmiddlewaretoken=$token&next=/"
Invoke-WebRequest -Uri "http://127.0.0.1:8123/cuentas/entrar/" -Method Post -Body $body -ContentType "application/x-www-form-urlencoded" -UseBasicParsing -WebSession $s | Out-Null
$x = Invoke-WebRequest -Uri "http://127.0.0.1:8123/usuarios/" -UseBasicParsing -WebSession $s
Write-Host "=== USUARIOS ($($x.StatusCode)) ==="
$x.Content | Select-String -Pattern "/usuarios/" | Select-Object -First 20
