$version = "0.0.0"  # stamped by CI from VERSION at release
$checksum = ""

$packageName = "l5x-lint"
$url = "https://github.com/JohnPrice/l5x-lint/releases/download/v${version}/l5x-lint-windows-x86_64.exe"
$binDir = "$(Split-Path -Parent $MyInvocation.MyCommand.Definition)"
$exePath = "$binDir\l5x-lint.exe"

Install-ChocolateyZipPackage -PackageName "$packageName" `
  -Url "$url" `
  -Checksum "$checksum" `
  -ChecksumType "sha256" `
  -UnzipLocation "$binDir"

Install-ChocolateyPath "$binDir" "Machine"
