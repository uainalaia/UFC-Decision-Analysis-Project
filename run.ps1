$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) {
    throw 'Install dependencies first. See README.md.'
}
& '.venv/Scripts/python.exe' -m streamlit run app/main.py
