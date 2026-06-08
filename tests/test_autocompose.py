import unittest
from unittest.mock import patch

from src import autocompose


class FakeContainerSummary:
    name = "svc"
    short_id = "abc123"


class FakeContainerWithAttrs:
    def __init__(self, attrs):
        self.attrs = attrs


class FakeContainers:
    def __init__(self, attrs):
        self._attrs = attrs
        self._summary = FakeContainerSummary()

    def list(self, **_kwargs):
        return [self._summary]

    def get(self, _cid):
        return FakeContainerWithAttrs(self._attrs)


class FakeNetwork:
    def __init__(self, name, internal=False):
        self.attrs = {"Name": name, "Internal": internal}


class FakeNetworks:
    def __init__(self, networks):
        self._networks = [FakeNetwork(name, internal) for name, internal in networks]

    def list(self):
        return self._networks


class FakeDockerClient:
    def __init__(self, attrs, networks):
        self.containers = FakeContainers(attrs)
        self.networks = FakeNetworks(networks)


def make_attrs(networks, healthcheck=None):
    return {
        "Name": "/svc",
        "HostConfig": {
            "CapDrop": None,
            "CgroupParent": None,
            "Dns": None,
            "DnsSearch": None,
            "ExtraHosts": None,
            "Links": None,
            "LogConfig": {"Type": None, "Config": None},
            "SecurityOpt": None,
            "Ulimits": None,
            "VolumeDriver": None,
            "VolumesFrom": None,
            "IpcMode": None,
            "Privileged": None,
            "RestartPolicy": {"Name": None},
            "ReadonlyRootfs": None,
            "Devices": None,
            "PortBindings": {},
        },
        "Config": {
            "Env": None,
            "Image": "test:latest",
            "Labels": {},
            "Entrypoint": None,
            "User": None,
            "WorkingDir": None,
            "Domainname": None,
            "Hostname": None,
            "OpenStdin": None,
            "Tty": None,
            "Cmd": None,
            "ExposedPorts": {},
            "Healthcheck": healthcheck,
        },
        "NetworkSettings": {"Networks": networks, "MacAddress": None},
        "Mounts": [],
    }


class GenerateTests(unittest.TestCase):
    def test_preserves_network_aliases(self):
        attrs = make_attrs(
            {
                "custom_net": {
                    "Aliases": ["svc", "db"],
                }
            }
        )
        fake_client = FakeDockerClient(attrs, networks=[("custom_net", False)])

        with patch("src.autocompose.docker.from_env", return_value=fake_client):
            cfile, c_networks, _ = autocompose.generate("svc")

        self.assertEqual(cfile["svc"]["networks"], {"custom_net": {"aliases": ["svc", "db"]}})
        self.assertEqual(
            c_networks,
            {"custom_net": {"external": True, "name": "custom_net"}},
        )

    def test_serializes_healthcheck_config(self):
        attrs = make_attrs(
            {"custom_net": {}},
            healthcheck={
                "Test": ["CMD-SHELL", "echo ok"],
                "Interval": 1000000000,
                "Timeout": 2000000000,
                "Retries": 3,
                "StartPeriod": 3000000000,
            },
        )
        fake_client = FakeDockerClient(attrs, networks=[("custom_net", False)])

        with patch("src.autocompose.docker.from_env", return_value=fake_client):
            cfile, _, _ = autocompose.generate("svc")

        self.assertEqual(
            cfile["svc"]["healthcheck"],
            {
                "test": ["CMD-SHELL", "echo ok"],
                "interval": "1000000000ns",
                "timeout": "2000000000ns",
                "retries": 3,
                "start_period": "3000000000ns",
            },
        )

    def test_simple_custom_network_uses_list_form(self):
        attrs = make_attrs({"custom_net": {}})
        fake_client = FakeDockerClient(attrs, networks=[("custom_net", True)])

        with patch("src.autocompose.docker.from_env", return_value=fake_client):
            cfile, c_networks, _ = autocompose.generate("svc")

        self.assertEqual(cfile["svc"]["networks"], ["custom_net"])
        self.assertEqual(
            c_networks,
            {"custom_net": {"external": False, "name": "custom_net"}},
        )

    def test_default_network_still_uses_network_mode(self):
        attrs = make_attrs({"bridge": {}})
        fake_client = FakeDockerClient(attrs, networks=[("bridge", False)])

        with patch("src.autocompose.docker.from_env", return_value=fake_client):
            cfile, c_networks, _ = autocompose.generate("svc")

        self.assertEqual(cfile["svc"]["network_mode"], "bridge")
        self.assertNotIn("networks", cfile["svc"])
        self.assertIsNone(c_networks)


if __name__ == "__main__":
    unittest.main()
