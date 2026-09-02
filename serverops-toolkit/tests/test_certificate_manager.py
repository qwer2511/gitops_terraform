import unittest

from serverops.cert_manager import (
    CertificateReplaceRequest,
    _config_test_command,
    planned_steps,
    replace_certificate,
    validate_request,
)
from serverops.inventory import ServerEntry
from serverops.ssh_client import SSHResult


class FakeRunner:
    def __init__(self, fail_contains=""):
        self.commands = []
        self.fail_contains = fail_contains

    def __call__(self, server, command, timeout):
        self.commands.append(command)
        if self.fail_contains and self.fail_contains in command:
            return SSHResult(1, "", "forced failure", 1, "")
        if command == "date +%Y%m%d_%H%M%S":
            return SSHResult(0, "20260902_101530", "", 1, "")
        if command.startswith("openssl x509"):
            return SSHResult(0, "subject=CN=test\nissuer=CN=CA\nnotAfter=Sep 2 00:00:00 2027 GMT", "", 1, "")
        if "systemctl is-active" in command:
            return SSHResult(0, "active", "", 1, "")
        if "journalctl" in command:
            return SSHResult(0, "Sep 02 service started", "", 1, "")
        return SSHResult(0, "ok", "", 1, "")


class CertificateManagerTests(unittest.TestCase):
    def request(self):
        return CertificateReplaceRequest(
            "www",
            "/etc/pki/tls/certs/www.crt",
            "/tmp/www.crt",
            "nginx",
            service_action="restart",
        )

    def test_plan_contains_backup_and_rollback(self):
        steps = planned_steps(self.request())
        self.assertTrue(any("백업" in item for item in steps))
        self.assertTrue(any("롤백" in item for item in steps))

    def test_reject_relative_path(self):
        req = self.request()
        req.new_cert = "new.crt"
        with self.assertRaises(ValueError):
            validate_request(req)

    def test_reject_same_current_and_new_path(self):
        req = self.request()
        req.new_cert = req.current_cert
        with self.assertRaises(ValueError):
            validate_request(req)

    def test_nginx_config_test(self):
        self.assertEqual(_config_test_command("nginx"), "nginx -t")

    def test_success_flow(self):
        fake = FakeRunner()
        result = replace_certificate(ServerEntry(name="test", host="10.0.0.1"), self.request(), runner=fake)
        self.assertTrue(result.ok)
        self.assertEqual(result.backup_cert, "/etc/pki/tls/certs/www.crt.20260902_101530.bak")
        self.assertFalse(result.rolled_back)
        self.assertTrue(any("cp -a" in command for command in fake.commands))
        self.assertTrue(any("nginx -t" in command for command in fake.commands))
        self.assertTrue(any("systemctl restart" in command for command in fake.commands))
        self.assertIn("service started", result.service_log)

    def test_config_failure_rolls_back(self):
        fake = FakeRunner("nginx -t")
        result = replace_certificate(ServerEntry(name="test", host="10.0.0.1"), self.request(), runner=fake)
        self.assertFalse(result.ok)
        self.assertTrue(result.rolled_back)
        self.assertTrue(any("cp -pf" in command for command in fake.commands))


if __name__ == "__main__":
    unittest.main()
