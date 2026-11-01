import os
import re
import unittest

from _load import ROOT

SKILLS = ["revos-replica-recon", "revos-replica-architect", "revos-replica-design",
          "revos-replica-build", "revos-replica-backend", "revos-replica-test",
          "revos-replica-diff", "revos-replica-entrepreneur", "revos-replica-brand",
          "revos-replica-launch", "revos-replica-deploy"]


def frontmatter(path):
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    return (m.group(1) if m else ""), text


class Repo(unittest.TestCase):
    def test_eleven_skill_folders_in_building(self):
        found = sorted(d for d in os.listdir(ROOT)
                       if os.path.isfile(os.path.join(ROOT, d, "SKILL.md")))
        self.assertEqual(found, sorted(SKILLS))

    def test_frontmatter_name_and_description(self):
        for s in SKILLS:
            fm, text = frontmatter(os.path.join(ROOT, s, "SKILL.md"))
            self.assertIn("name: %s\n" % s, fm + "\n", s)
            self.assertRegex(fm, r"description: ", s)
            self.assertGreater(len(fm), 200, "%s description is too thin" % s)
            self.assertGreater(len(text.splitlines()), 60, s)

    def test_every_skill_keeps_the_mit_licence(self):
        for s in SKILLS:
            with open(os.path.join(ROOT, s, "LICENSE"), encoding="utf-8") as fh:
                self.assertIn("Copyright (c) 2026 Jake Schincariol", fh.read(), s)

    def test_no_old_skill_names_left(self):
        old = re.compile(r"(?<![\w-])replica-(recon|architect|design|build|backend|test|"
                         r"diff|entrepreneur|brand|launch|deploy)\b")
        bad = []
        for dirpath, dirnames, filenames in os.walk(ROOT):
            for fn in filenames:
                if fn.endswith((".md", ".py", ".json", ".ts", ".csv")):
                    path = os.path.join(dirpath, fn)
                    with open(path, encoding="utf-8") as fh:
                        if old.search(fh.read()):
                            bad.append(os.path.relpath(path, ROOT))
        self.assertEqual(bad, [])

    def test_no_em_dashes_anywhere(self):
        bad = []
        for dirpath, dirnames, filenames in os.walk(ROOT):
            dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__")]
            for fn in filenames:
                if fn.endswith((".md", ".py", ".json", ".ts", ".csv")):
                    path = os.path.join(dirpath, fn)
                    with open(path, encoding="utf-8") as fh:
                        if chr(0x2014) in fh.read():
                            bad.append(os.path.relpath(path, ROOT))
        self.assertEqual(bad, [])


if __name__ == "__main__":
    unittest.main()
