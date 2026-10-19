param([string]$OutputDirectory)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
$projectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
if (-not $OutputDirectory) { $OutputDirectory = Join-Path $projectRoot 'transfer' }
$null = New-Item -ItemType Directory -Force -Path $OutputDirectory
$archivePath = Join-Path $OutputDirectory ('Galaxies-transfer-' + (Get-Date -Format 'yyyy-MM-dd-HHmmss') + '.zip')
$rootNames = @('README.md','HANDOVER.md','VERIFICATION.md','TRANSFER-START-HERE.txt','NEXT-GALAXY-GUIDE.txt','package.json','server.mjs','launch.ps1','stop.ps1','Launch Fleet Planner.cmd','Stop Fleet Planner.cmd')
$files = @($rootNames | ForEach-Object { Get-Item -LiteralPath (Join-Path $projectRoot $_) })
foreach ($folder in @('dist','source','scripts','tests','qa','data-merge')) {
    $files += Get-ChildItem -LiteralPath (Join-Path $projectRoot $folder) -Recurse -File
}
$files += Get-ChildItem -LiteralPath (Join-Path $projectRoot 'local-data') -File | Where-Object { $_.Name -match '^state(?:-[a-z0-9]+)?\.json(?:\.previous)?$' }
if (Test-Path -LiteralPath (Join-Path $projectRoot 'AGENTS.md')) { $files += Get-Item -LiteralPath (Join-Path $projectRoot 'AGENTS.md') }
$manifest = [System.Collections.Generic.List[object]]::new()
$stateHashes = @{}
$sha = [System.Security.Cryptography.SHA256]::Create()
$archive = [System.IO.Compression.ZipFile]::Open($archivePath, [System.IO.Compression.ZipArchiveMode]::Create)
try {
    foreach ($file in ($files | Sort-Object FullName -Unique)) {
        $relative = $file.FullName.Substring($projectRoot.Length + 1).Replace('\','/')
        $bytes = [System.IO.File]::ReadAllBytes($file.FullName)
        $digest = [BitConverter]::ToString($sha.ComputeHash($bytes)).Replace('-','').ToLowerInvariant()
        $entry = $archive.CreateEntry('Galaxies/' + $relative, [System.IO.Compression.CompressionLevel]::Optimal)
        $stream = $entry.Open()
        try { $stream.Write($bytes,0,$bytes.Length) } finally { $stream.Dispose() }
        $manifest.Add([ordered]@{path=$relative;bytes=$bytes.Length;sha256=$digest})
        if ($relative.StartsWith('local-data/')) { $stateHashes[$file.FullName] = $digest }
    }
    foreach ($statePath in $stateHashes.Keys) {
        $current = (Get-FileHash -LiteralPath $statePath -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($current -ne $stateHashes[$statePath]) { throw 'A save changed while packaging. Create a fresh archive after the save finishes.' }
    }
    $metadata = [ordered]@{createdAtUtc=[DateTime]::UtcNow.ToString('o');project='Galaxies fleet planner';fileCount=$manifest.Count;files=$manifest}
    $json = $metadata | ConvertTo-Json -Depth 6
    $entry = $archive.CreateEntry('Galaxies/TRANSFER-MANIFEST.json')
    $writer = [System.IO.StreamWriter]::new($entry.Open(),[System.Text.UTF8Encoding]::new($false))
    try { $writer.Write($json) } finally { $writer.Dispose() }
} finally { $archive.Dispose(); $sha.Dispose() }

# Verify all compressed payload bytes by reading the finished archive back.
$archive = [System.IO.Compression.ZipFile]::OpenRead($archivePath)
$sha = [System.Security.Cryptography.SHA256]::Create()
try {
    if ($archive.Entries.Count -ne ($manifest.Count + 1)) { throw 'Archive entry count does not match.' }
    foreach ($item in $manifest) {
        $entry = $archive.GetEntry('Galaxies/' + $item.path)
        if (-not $entry -or $entry.Length -ne $item.bytes) { throw "Missing or wrong-sized entry: $($item.path)" }
        $stream = $entry.Open()
        try { $digest = [BitConverter]::ToString($sha.ComputeHash($stream)).Replace('-','').ToLowerInvariant() } finally { $stream.Dispose() }
        if ($digest -ne $item.sha256) { throw "Checksum mismatch: $($item.path)" }
    }
} finally { $archive.Dispose(); $sha.Dispose() }
$archiveHash = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash.ToLowerInvariant()
[System.IO.File]::WriteAllText($archivePath+'.sha256', $archiveHash+'  '+[System.IO.Path]::GetFileName($archivePath)+[Environment]::NewLine)
[pscustomobject]@{archive=$archivePath;files=$manifest.Count;bytes=(Get-Item -LiteralPath $archivePath).Length;sha256=$archiveHash;verified=$true} | ConvertTo-Json
