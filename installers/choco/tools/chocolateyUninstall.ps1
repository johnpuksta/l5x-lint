$toolsDir = "$(Split-Path -Parent $MyInvocation.MyCommand.Definition)"

Uninstall-ChocolateyPath "$toolsDir" "Machine"
