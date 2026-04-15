Set objFSO = CreateObject("Scripting.FileSystemObject")
source = "C:\Users\Owner\OneDrive\CAM\DERIVED_RULES.md"
dest = "C:\Users\Owner\OneDrive\HeartSync\.agents\DERIVED_RULES.md"
objFSO.CopyFile source, dest, True
WScript.Echo "Copied DERIVED_RULES.md to HeartSync"
