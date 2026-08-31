import tempfile
import unittest
from pathlib import Path

from serverops.inventory import ServerEntry
from serverops.os_compat import family_from_release, parse_os_release, service_candidates, OSProfile
from serverops.ssh_client import ssh_options
from serverops.transfer import make_zip, sha256_file


class OSCompatTests(unittest.TestCase):
    def test_detect_rhel_family(self):
        data = parse_os_release('ID="rocky"\nID_LIKE="rhel centos fedora"\nVERSION_ID="9.7"\n')
        self.assertEqual(family_from_release(data), "rhel")

    def test_detect_debian_family(self):
        data = parse_os_release('ID=ubuntu\nID_LIKE=debian\nVERSION_ID="24.04"\n')
        self.assertEqual(family_from_release(data), "debian")

    def test_service_aliases(self):
        profile = OSProfile(family="debian")
        self.assertEqual(service_candidates("sshd", profile)[0], "ssh")
        self.assertEqual(service_candidates("httpd", profile)[0], "apache2")


class SSHOptionTests(unittest.TestCase):
    def test_jump_host_and_key_are_included(self):
        server = ServerEntry(name="WEB01", host="10.0.0.10", user="ops", key_file="~/.ssh/id_ed25519", jump_host="jump@10.0.0.2")
        opts = ssh_options(server)
        self.assertIn("-J", opts)
        self.assertIn("jump@10.0.0.2", opts)
        self.assertIn("-i", opts)


class TransferTests(unittest.TestCase):
    def test_zip_and_sha256(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "sample"
            source.mkdir()
            (source / "a.txt").write_text("hello", encoding="utf-8")
            archive_dir = Path(td) / "out"
            archive = make_zip(str(source), str(archive_dir))
            self.assertTrue(Path(archive).is_file())
            digest = sha256_file(archive)
            self.assertEqual(len(digest), 64)


if __name__ == "__main__":
    unittest.main()
