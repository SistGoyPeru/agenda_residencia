$s = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$r = Invoke-WebRequest -Uri "http://127.0.0.1:8123/cuentas/entrar/" -UseBasicParsing -WebSession $s
$token = ([regex]::Match($r.Content, '"csrfmiddlewaretoken" value="([^"]+)"')).Groups[1].Value
$body = "username=admin&password=admin123&csrfmiddlewaretoken=$token&next=/"
Invoke-WebRequest -Uri "http://127.0.0.1:8123/cuentas/entrar/" -Method Post -Body $body -ContentType "application/x-www-form-urlencoded" -UseBasicParsing -WebSession $s | Out-Null
$x = Invoke-WebRequest -Uri "http://127.0.0.1:8123/reportes/mensual/pdf/?mes=2026-11" -UseBasicParsing -WebSession $s
Write-Host "PDF status: $($x.StatusCode)"
Write-Host "Tamaño: $($x.RawContent.Length) bytes"
Write-Host "Content-Disposition: $($x.Headers['Content-Disposition'])"
