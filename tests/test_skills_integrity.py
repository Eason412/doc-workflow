"""Repository-wide structural and standalone link checks for all Skills in doc-workflow."""
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "skills"
EXPECTED_SKILLS = {"project-docs", "translate", "writing-zh", "md-export"}
FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
INLINE_CODE = re.compile(r"`[^`\n]+`")
MD_LINK = re.compile(r"\[[^\]]+\]\(([^)#]+)(?:#[^)]*)?\)")


def strip_fenced_code(text: str) -> str:
    out = []
    in_fence = False
    marker = ""
    for line in text.splitlines():
        stripped = line.lstrip()
        if not in_fence and (stripped.startswith("```") or stripped.startswith("~~~")):
            in_fence = True
            marker = stripped[:3]
            continue
        if in_fence and stripped.startswith(marker):
            in_fence = False
            continue
        if not in_fence:
            out.append(line)
    return INLINE_CODE.sub("", "\n".join(out))


class SkillsIntegrityTests(unittest.TestCase):
    def test_expected_skill_directories_and_frontmatter(self):
        actual = {p.name for p in SKILLS_DIR.iterdir() if p.is_dir()}
        self.assertEqual(actual, EXPECTED_SKILLS)

        for name in sorted(EXPECTED_SKILLS):
            skill_dir = SKILLS_DIR / name
            skill_md = skill_dir / "SKILL.md"
            self.assertTrue(skill_md.is_file(), f"Missing SKILL.md in {name}")
            self.assertTrue((skill_dir / "agents" / "openai.yaml").is_file(), f"Missing openai.yaml in {name}")

            content = skill_md.read_text(encoding="utf-8")
            self.assertLessEqual(len(content.splitlines()), 85, f"{name}/SKILL.md exceeds 85 lines")
            match = FRONTMATTER.match(content)
            self.assertIsNotNone(match, f"{name}/SKILL.md missing YAML frontmatter")
            kv = {}
            for raw_line in match.group(1).splitlines():
                if ":" in raw_line:
                    k, v = raw_line.split(":", 1)
                    kv[k.strip()] = v.strip().strip('"')
            self.assertEqual(kv.get("name"), name)
            self.assertTrue(kv.get("description"))

    def test_skill_markdown_links_stay_self_contained(self):
        for name in sorted(EXPECTED_SKILLS):
            skill_dir = SKILLS_DIR / name
            md_files = [skill_dir / "SKILL.md"] + sorted((skill_dir / "references").glob("*.md"))
            for md in md_files:
                body = strip_fenced_code(md.read_text(encoding="utf-8"))
                for target in MD_LINK.findall(body):
                    if target.startswith(("http://", "https://", "mailto:")):
                        continue
                    resolved = (md.parent / target).resolve()
                    self.assertTrue(resolved.exists(), f"Broken link {target!r} in {md.relative_to(ROOT)}")
                    self.assertTrue(
                        resolved.is_relative_to(skill_dir.resolve()),
                        f"Link {target!r} in {md.relative_to(ROOT)} escapes standalone skill {name}",
                    )


if __name__ == "__main__":
    unittest.main()
