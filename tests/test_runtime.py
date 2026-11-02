import sys, tempfile, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from runtime_manager import Engine, config


class RuntimeTests(unittest.TestCase):
    def test_defaults_without_env(self):
        with tempfile.TemporaryDirectory() as d:
            e = Engine(d)
            self.assertEqual(e.port, 1235)
            self.assertEqual(e.cfg['CHAT_FAST_MODE'], 'true')

    def test_env_overrides_and_windows_paths(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, '.env').write_text('SCOUT_PORT=1236\nSCOUT_MODEL_PATH=models\\\\4B\\\\x.gguf',
                                       encoding='utf8')
            e = Engine(d)
            self.assertEqual(e.port, 1236)
            self.assertEqual(e.path(e.cfg['SCOUT_MODEL_PATH']), Path(d) / 'models/4B/x.gguf')

    def test_missing_files_reported(self):
        with tempfile.TemporaryDirectory() as d:
            e = Engine(d)
            e.port = 65531
            with self.assertRaises(FileNotFoundError):
                e.connect()

    def test_config_ignores_comments(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, '.env').write_text('# comment\nCHAT_FAST_MODE=false\n', encoding='utf8')
            self.assertEqual(config(d)['CHAT_FAST_MODE'], 'false')


if __name__ == '__main__':
    unittest.main()
