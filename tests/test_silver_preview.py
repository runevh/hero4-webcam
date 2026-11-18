"""Exercise startup ordering without contacting a camera or changing settings."""
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import silver_preview as preview


class PreviewSetupTests(unittest.TestCase):
    def setup_mocks(self, reply):
        connection = MagicMock()
        connection.__enter__.return_value.recv.side_effect = [reply, b'']
        return connection

    def test_failed_shell_setup_does_not_change_camera_mode(self):
        with patch.object(preview.socket, 'create_connection', return_value=self.setup_mocks(b'failed')), \
             patch.object(preview, 'api') as api:
            with self.assertRaisesRegex(RuntimeError, 'Camera setup failed'):
                preview.configure()
            api.assert_not_called()

    def test_success_selects_only_tested_mode_and_preview_settings(self):
        with patch.object(preview.socket, 'create_connection', return_value=self.setup_mocks(b'SILVER_READY\n')), \
             patch.object(preview, 'api') as api, patch.object(preview.time, 'sleep'):
            preview.configure()
        self.assertEqual([call.args[0] for call in api.call_args_list], [
            '/setting/3/8', '/setting/2/8', '/setting/4/0', '/setting/64/0',
            '/setting/62/2400000', '/command/mode?p=1', '/command/mode?p=0'])

    def test_http_failure_stops_setup(self):
        with patch.object(preview.socket, 'create_connection', return_value=self.setup_mocks(b'SILVER_READY\n')), \
             patch.object(preview, 'api', side_effect=RuntimeError('HTTP 500')) as api:
            with self.assertRaisesRegex(RuntimeError, 'HTTP 500'):
                preview.configure()
            self.assertEqual(api.call_count, 1)


if __name__ == '__main__':
    unittest.main()
