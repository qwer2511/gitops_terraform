import json
import tempfile
import unittest
from pathlib import Path

from serverops.inventory import ServerEntry, load_inventory, save_inventory


class InventoryTests(unittest.TestCase):
    def test_default_inventory_has_local_server(self):
        rows = load_inventory(None)
        self.assertTrue(rows)
        self.assertTrue(rows[0].local)

    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as td:
            path = str(Path(td) / "servers.json")
            source = [ServerEntry(name="WEB01", host="10.0.0.11", user="ops", group="WEB", port=2222)]
            save_inventory(source, path)
            loaded = load_inventory(path)
            self.assertEqual(loaded[0].name, "WEB01")
            self.assertEqual(loaded[0].port, 2222)
            self.assertEqual(loaded[0].group, "WEB")

    def test_reject_invalid_port(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "servers.json"
            path.write_text(json.dumps({"servers": [{"name": "bad", "port": 70000}]}), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_inventory(str(path))


if __name__ == "__main__":
    unittest.main()
