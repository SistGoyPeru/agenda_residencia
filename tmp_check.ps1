$s = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$r = Invoke-WebRequest -Uri "http://127.0.0.1:8123/cuentas/entrar/" -UseBasicParsing -WebSession $s
$token = ([regex]::Match($r.Content, '"csrfmiddlewaretoken" value="([^"]+)"')).Groups[1].Value
$body = "username=admin&password=admin123&csrfmiddlewaretoken=$token&next=/"
Invoke-WebRequest -Uri "http://127.0.0.1:8123/cuentas/entrar/" -Method Post -Body $body -ContentType "application/x-www-form-urlencoded" -UseBasicParsing -WebSession $s | Out-Null
foreach ($u in @("/usuarios/", "/usuarios/nueva/", "/planes/")) {
  try { $x = Invoke-WebRequest -Uri "http://127.0.0.1:8123$u" -UseBasicParsing -WebSession $s -ErrorAction Stop; Write-Host "$u : $($x.StatusCode)" } catch { Write-Host "$u : ERROR $($_.Exception.Response.StatusCode)" }
}
