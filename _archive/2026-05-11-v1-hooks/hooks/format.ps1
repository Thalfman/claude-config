$data = [Console]::In.ReadToEnd() | ConvertFrom-Json
$path = $data.tool_input.file_path
if (-not $path) { exit 0 }
$ext = [System.IO.Path]::GetExtension($path).ToLower()
switch ($ext) {
    { $_ -in @('.js', '.ts', '.jsx', '.tsx', '.css', '.html', '.json', '.yaml', '.yml', '.md') } {
        npx prettier --write $path 2>$null
    }
    '.py' {
        black $path 2>$null
    }
}
exit 0
