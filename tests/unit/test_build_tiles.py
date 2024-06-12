import unittest
from unittest.mock import patch, mock_open, MagicMock
from pathlib import Path
import json
import hashlib

# Import the functions to be tested
from task.build_tiles import (
    get_current_sqlite_hash,
    get_stored_hash,
    update_current_sqlite_hash,
)


class TestGeoJsonFunctions(unittest.TestCase):
    @patch("builtins.open", new_callable=mock_open, read_data='{"hash": "abc123"}')
    @patch("pathlib.Path.exists", return_value=True)
    def test_get_stored_hash_exists(self, mock_exists, mock_file):
        hash_path = Path("dummy_path.json")
        result = get_stored_hash(hash_path)
        self.assertEqual(result, "abc123")
        mock_file.assert_called_once_with(hash_path)
        mock_exists.assert_called_once()

    @patch("pathlib.Path.exists", MagicMock(return_value=False))
    def test_get_stored_hash_not_exists(self):
        hash_path = Path("dummy_path.json")
        result = get_stored_hash(hash_path)
        self.assertIsNone(result)

    @patch("builtins.open", new_callable=mock_open, read_data=b"test data")
    def test_get_current_sqlite_hash(self, mock_file):
        sqlite_path = Path("dummy_path.sqlite")
        expected_hash = hashlib.md5(b"test data").hexdigest()
        result = get_current_sqlite_hash(sqlite_path)
        self.assertEqual(result, expected_hash)
        mock_file.assert_called_once_with(sqlite_path, "rb")

    @patch("builtins.open", new_callable=mock_open)
    def test_update_current_sqlite_hash(self, mock_file):
        hash_path = Path("dummy_path.json")
        new_hash = "newhashvalue"
        update_current_sqlite_hash(hash_path, new_hash)
        mock_file.assert_called_once_with(hash_path, "w")
        mock_file().write.assert_called_once_with(json.dumps({"hash": new_hash}))


if __name__ == "__main__":
    unittest.main()
