param(
  [string]$Python = "python"
)

if (-not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
}

& $Python -m venv .venv
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install -e ".[dev]"
npm install

Write-Host "Bootstrap complete. Next steps:"
Write-Host "1. Update .env"
Write-Host "2. python scripts/run_alembic.py upgrade head"
Write-Host "3. python -m app.cli seed-journals"
Write-Host "4. npm --workspace apps/web run dev"

