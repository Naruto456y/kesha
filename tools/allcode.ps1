Get-ChildItem -Recurse -File -Include *.py |
  Where-Object { $_.FullName -notmatch '\\(__pycache__|\.venv|venv|node_modules|\.git|\.idea|build|dist|backups|models|\.pytest_cache)\\' } |
  ForEach-Object {
    "`n========== $($_.FullName) ==========`n"
    Get-Content $_.FullName -Raw
  } | Out-File -FilePath all_code.txt -Encoding utf8

Write-Host "Done: all_code.txt ($([math]::Round((Get-Item all_code.txt).Length / 1KB)) KB)"
