$toolsDir = "$(Split-Path -Parent $MyInvocation.MyCommand.Definition)"
$exePath = "$toolsDir\l5x-lint-windows-x86_64.exe"

if (!(Test-Path $exePath)) {
  throw "Binary not found at $exePath"
}

Install-ChocolateyPath "$toolsDir" "Machine"
