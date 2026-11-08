$s = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$r = Invoke-WebRequest -Uri "http://127.0.0.1:8123/cuentas/entrar/" -UseBasicParsing -WebSession $s
$token = ([regex]::Match($r.Content, '"csrfmiddlewaretoken" value="([^"]+)"')).Groups[1].Value
$body = "username=admin&password=admin123&csrfmiddlewaretoken=$token&next=/"
Invoke-WebRequest -Uri "http://127.0.0.1:8123/cuentas/entrar/" -Method Post -Body $body -ContentType "application/x-www-form-urlencoded" -UseBasicParsing -WebSession $s | Out-Null
$x = Invoke-WebRequest -Uri "http://127.0.0.1:8123/usuarios/" -UseBasicParsing -WebSession $s
Write-Host "=== USUARIOS ($($x.StatusCode)) ==="
$x.Content | Select-String -Pattern "usuario_editar|usuario_borrar|usuario_activar_plan|usuario_nueva" | Select-Object -First 10
$d = Invoke-WebRequest -Uri "http://127.0.0.1:8123/" -UseBasicParsing -WebSession $s
Write-Host "=== DASHBOARD ($($d.StatusCode)) ==="
$d.Content | Select-String -Pattern "reportes/mensual|planes/" | Select-Object -First 5
