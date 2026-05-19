$ErrorActionPreference = "Stop"
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (!(Test-Path .env)) {
  Copy-Item .env.example .env
}
New-Item -ItemType Directory -Force -Path data, logs, sample_datasets | Out-Null
Write-Host "SmartVision setup complete. Run: .\.venv\Scripts\uvicorn.exe api_gateway.main:app --reload"
