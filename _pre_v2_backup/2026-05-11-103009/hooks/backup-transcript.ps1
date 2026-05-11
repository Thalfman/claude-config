$data = [Console]::In.ReadToEnd() | ConvertFrom-Json
$src = $data.transcript_path
if (-not $src -or -not (Test-Path $src)) { exit 0 }
$dest = "$env:USERPROFILE\.claude\transcript-backups"
$ts = Get-Date -Format 'yyyy-MM-dd-HHmmss'
Copy-Item $src "$dest\transcript-$ts.json" -ErrorAction SilentlyContinue
Get-ChildItem "$dest\*.json" -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -Skip 20 |
    Remove-Item -Force -ErrorAction SilentlyContinue
exit 0
