"""Local template invariants; no installation, Docker calls or host writes."""
from pathlib import Path
import shlex
import unittest
import xml.etree.ElementTree as ET

from moonshine_stt_wyoming.config import Config
from moonshine_stt_wyoming.models import manifest

ROOT = Path(__file__).resolve().parents[1]


class UnraidTemplateTests(unittest.TestCase):
    def setUp(self):
        self.root = ET.parse(ROOT / "templates/moonshine-stt-wyoming.xml").getroot()
        self.configs = self.root.findall("Config")

    def test_defaults_accepted_by_application(self):
        env = {c.attrib["Target"]: c.text for c in self.configs if c.attrib["Type"] == "Variable"}
        config = Config.from_env(env)
        self.assertEqual((config.model, config.threads, config.port, config.language),
                         ("small-streaming-de", 1, 10300, "de"))
        self.assertTrue(config.auto_download)
        self.assertEqual(config.max_concurrent_requests, 1)

    def test_dropdown_first_option_is_default_and_values_are_valid(self):
        for c in self.configs:
            if c.attrib["Type"] != "Variable":
                continue
            options = c.attrib["Default"].split("|")
            self.assertEqual(c.text, options[0])
            for option in options:
                env = {c.attrib["Target"]: option}
                models = manifest()["models"]
                if c.attrib["Target"] == "MOONSHINE_MODEL":
                    env["MOONSHINE_LANGUAGE"] = models[option]["language"]
                elif c.attrib["Target"] == "MOONSHINE_LANGUAGE":
                    env["MOONSHINE_MODEL"] = next(name for name, spec in models.items() if spec["language"] == option)
                Config.from_env(env)

    def test_security_and_planned_release_repository(self):
        self.assertEqual(self.root.attrib["version"], "2")
        self.assertEqual(self.root.findtext("Network"), "bridge")
        self.assertEqual(self.root.findtext("Privileged"), "false")
        extra = shlex.split(self.root.findtext("ExtraParams"))
        for required in ("--user=99:100", "--read-only", "--cap-drop=ALL",
                         "--security-opt=no-new-privileges"):
            self.assertIn(required, extra)
        self.assertFalse(any(c.attrib["Type"] == "Device" for c in self.configs))
        self.assertEqual(self.root.findtext("Repository"), "ghcr.io/marco-taylor/moonshine-stt-wyoming:latest")
        for tag in ("Registry", "TemplateURL", "Support", "Project", "ReadMe"):
            self.assertIn("marco-taylor/moonshine-stt-wyoming", self.root.findtext(tag))
        for tag in ("WebUI", "Icon"):
            self.assertFalse(self.root.findtext(tag))
        self.assertEqual(self.root.findtext("License"), "Apache-2.0")

    def test_mount_and_port_consistency(self):
        paths = [c for c in self.configs if c.attrib["Type"] == "Path"]
        ports = [c for c in self.configs if c.attrib["Type"] == "Port"]
        self.assertEqual(len(paths), 1)
        self.assertEqual(paths[0].attrib["Target"], "/app/models")
        self.assertEqual(paths[0].attrib["Mode"], "rw")
        self.assertEqual(paths[0].text, "/mnt/user/appdata/moonshine-stt-wyoming/models")
        self.assertEqual(len(ports), 1)
        self.assertEqual((ports[0].attrib["Target"], ports[0].text, ports[0].attrib["Mode"]),
                         ("10300", "10300", "tcp"))

    def test_unique_targets_and_required_descriptions(self):
        targets = [c.attrib["Target"] for c in self.configs]
        self.assertEqual(len(targets), len(set(targets)))
        for c in self.configs:
            self.assertGreater(len(c.attrib["Description"]), 25)
            self.assertEqual(c.attrib["Mask"], "false")
            self.assertIn(c.attrib["Display"], ("always", "advanced"))
