# Run as Administrator to add stpetebrazilianjiujitsu.test to Windows hosts file
$hostsPath = "C:\Windows\System32\drivers\etc\hosts"
$entries = @(
    "127.0.0.1 stpetebrazilianjiujitsu.test",
    "127.0.0.1 www.stpetebrazilianjiujitsu.test",
    "127.0.0.1 www.stpetebjj.test"
)
$current = Get-Content $hostsPath -Raw
foreach ($entry in $entries) {
    $domain = ($entry -split "\s+")[1]
    if ($current -notmatch [regex]::Escape($domain)) {
        Add-Content -Path $hostsPath -Value "`r`n$entry"
        Write-Host "Added: $entry" -ForegroundColor Green
    } else {
        Write-Host "Already present: $entry" -ForegroundColor Yellow
    }
}
