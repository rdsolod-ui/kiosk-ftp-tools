import asyncio
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
import uuid
from unittest.mock import patch

from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer
from kiosk_ftp_tools import app


@unittest.skipUnless(sys.platform == 'win32', 'Windows Credential Manager required')
class Integration(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.remote = root / 'remote'
        self.local = root / 'local'
        self.remote.mkdir()
        self.local.mkdir()
        self.user = 'test-' + uuid.uuid4().hex
        password = uuid.uuid4().hex
        authorizer = DummyAuthorizer()
        authorizer.add_user(self.user, password, str(self.remote), perm='elradfmwMT')
        class Handler(FTPHandler):
            pass
        Handler.authorizer = authorizer
        self.server = FTPServer(('127.0.0.1', 0), Handler)
        self.port = self.server.socket.getsockname()[1]
        self.credential = f'kiosk-ftp-tools/127.0.0.1:{self.port}'
        app.vault().set_password(self.credential, self.user, password)
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={'timeout': 0.1}, daemon=True)
        self.thread.start()
        self.settings = patch.multiple(app, HOST='127.0.0.1', PORT=self.port,
                                      USER=self.user, TLS=False, CREDENTIAL=self.credential,
                                      TRANSFER=self.local)
        self.settings.start()

    def tearDown(self):
        self.settings.stop()
        self.server.close_all()
        self.thread.join(timeout=2)
        app.vault().delete_password(self.credential, self.user)
        self.temp.cleanup()

    def test_transfer_and_overwrite_protection(self):
        data = 'UTF-8 transfer: пример\n'.encode()
        (self.local / 'source.txt').write_bytes(data)
        (self.remote / 'existing.txt').write_bytes(b'preserve')
        self.assertEqual(app.status()['port'], self.port)
        app.upload('source.txt', '/existing.txt')
        self.assertEqual((self.remote / 'existing.txt').read_bytes(), b'preserve')
        uploaded = [p for p in self.remote.iterdir() if p.name != 'existing.txt']
        self.assertEqual(len(uploaded), 1)
        app.download('/' + uploaded[0].name, 'result.txt')
        self.assertEqual((self.local / 'result.txt').read_bytes(), data)
        with self.assertRaises(FileExistsError):
            app.download('/existing.txt', 'result.txt')
        self.assertEqual((self.local / 'result.txt').read_bytes(), data)
        self.assertEqual(app.verify()['roundtrip'], 'passed')
        self.assertEqual(len(list(self.remote.iterdir())), 2)

    def test_mcp_installed_entrypoint(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        data = b'MCP roundtrip\n'
        (self.local / 'source.txt').write_bytes(data)
        async def run():
            env = dict(os.environ, KIOSK_FTP_HOST='127.0.0.1', KIOSK_FTP_PORT=str(self.port),
                       KIOSK_FTP_USER=self.user, KIOSK_FTP_TLS='false', KIOSK_FTP_LOCAL_DIR=str(self.local))
            executable = Path(sys.executable).parent / 'kiosk-ftp-mcp.exe'
            params = StdioServerParameters(command=str(executable), env=env)
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as client:
                    await client.initialize()
                    self.assertEqual(len((await client.list_tools()).tools), 4)
                    for name, args in [('kiosk_status', {}),
                                       ('kiosk_upload', {'local': 'source.txt', 'remote': '/new.txt'}),
                                       ('kiosk_list', {})]:
                        result = await client.call_tool(name, args)
                        self.assertFalse(result.isError, result.content)
                    uploaded = list(self.remote.iterdir())
                    self.assertEqual(len(uploaded), 1)
                    result = await client.call_tool('kiosk_download', {'remote': '/' + uploaded[0].name, 'local': 'result.txt'})
                    self.assertFalse(result.isError, result.content)
                    self.assertEqual((self.local / 'result.txt').read_bytes(), data)
        asyncio.run(run())
