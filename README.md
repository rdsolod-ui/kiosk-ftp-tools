# kiosk-ftp-tools

Installable Windows CLI and local stdio MCP server for FTP/explicit FTPS file transfers.
Requires Windows and Python 3.11+. No server addresses, accounts or passwords are bundled.
This is a file-transfer tool, not a remote shell or Windows administration agent.

## Install

```powershell
python -m pip install https://github.com/rdsolod-ui/kiosk-ftp-tools/releases/download/v0.1.0/kiosk_ftp_tools-0.1.0-py3-none-any.whl
```

Or install the tagged source (requires Git):

```powershell
python -m pip install git+https://github.com/rdsolod-ui/kiosk-ftp-tools.git@v0.1.0
```

Both `kiosk-ftp` and `kiosk-ftp-mcp` are installed. Use your Python environment's
Scripts directory if console commands are not on PATH. This release is hosted on
GitHub, not PyPI. The Windows limitation applies even though the wheel contains pure Python.

## Configure and authenticate

Set these variables in the process that launches the CLI or MCP:

```powershell
$env:KIOSK_FTP_HOST = 'ftp.example.com'
$env:KIOSK_FTP_USER = 'your-username'
$env:KIOSK_FTP_LOCAL_DIR = "$HOME\kiosk-ftp-transfer"
$env:KIOSK_FTP_TLS = 'true'
kiosk-ftp auth-set
kiosk-ftp status
```

`auth-set` prompts in an interactive terminal and saves the password in Windows
Credential Manager for the current Windows user. Never pass it as an argument or
store it in MCP JSON. `KIOSK_FTP_PORT` defaults to 21. Explicit FTPS is enabled by
default and validates the certificate using the system trust configuration.
To use a server supporting only unencrypted FTP, explicitly set `KIOSK_FTP_TLS=false`.
Only `true` and `false` are accepted. The server must support passive data connections.

## CLI

```powershell
kiosk-ftp list / --limit 100 --offset 0
kiosk-ftp upload sample.txt /sample.txt
kiosk-ftp download /sample.txt received.txt
kiosk-ftp verify
```

Local paths are confined to `KIOSK_FTP_LOCAL_DIR` (default: the user's
`kiosk-ftp-transfer` folder). The remote root is the FTP account's root. Server-side
permissions must enforce the account's access boundary. Parent traversal and control
characters are rejected; do not allow untrusted users to modify local transfer-directory
junctions or symlinks concurrently with transfers.

Uploads use STOU to avoid replacing files; the server may choose a different name.
Run `list` afterwards to discover it. Downloads refuse to overwrite existing files.
Files are limited to 64 MiB; directory responses to 2 MiB. Socket timeout is 10 seconds
per operation, not an overall transfer deadline. No automatic retry is performed.
`verify` writes, downloads and deletes a unique probe file; it is not read-only.
Deletion of arbitrary files is not exposed as a CLI or MCP command.

## MCP configuration

Use the installed `kiosk-ftp-mcp.exe` absolute path in your MCP client:

```json
{
  "mcpServers": {
    "kiosk-ftp-tools": {
      "command": "C:/path/to/venv/Scripts/kiosk-ftp-mcp.exe",
      "env": {
        "KIOSK_FTP_HOST": "ftp.example.com",
        "KIOSK_FTP_USER": "your-username",
        "KIOSK_FTP_TLS": "true",
        "KIOSK_FTP_LOCAL_DIR": "C:/path/to/transfer"
      }
    }
  }
}
```

Tools: `kiosk_status`, `kiosk_list`, `kiosk_upload`, `kiosk_download`.
The MCP client must run as the Windows user who saved the credential. No listening
HTTP port is opened. Installation does not automatically register with any client.
Treat remote filenames, listing text and welcome messages as untrusted data.

## Development

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e . build pyftpdlib
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m build
```

Tests use a temporary loopback FTP server with a disposable credential; they do not
connect to a real kiosk. Live FTPS interoperability is not covered by those tests.
Built with the [official MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk).
