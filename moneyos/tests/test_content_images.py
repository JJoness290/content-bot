import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from moneyos.app.core.content_generator import generate_autopilot_draft


def main() -> None:
    content = generate_autopilot_draft(
        topic="Budgeting tips for beginners",
        angle="friendly buyer guide",
        keywords=["budgeting", "saving", "finance"],
        affiliate_placeholders=["[Primary offer – Official Site]", "[Secondary offer – Official Site]"],
    )
    assert "![" not in content
    assert "https://source.unsplash.com/" not in content
    lines = content.splitlines()
    assert lines[0] == "Budgeting tips for beginners"
    assert lines[1] == ""
    assert lines[2].startswith("<img src=\"https://source.unsplash.com/1600x900/?")
    assert lines[3] == ""
    image_lines = [
        i for i, line in enumerate(lines) if line.startswith("<img src=\"https://source.unsplash.com/1600x900/?")
    ]
    assert image_lines
    for idx in image_lines:
        assert lines[idx].startswith("<img src=\"https://source.unsplash.com/1600x900/?")
        assert lines[idx] == lines[idx].strip()
        assert lines[idx] != ""
        assert idx > 0
        assert lines[idx - 1] == ""
        assert idx + 1 < len(lines)
        assert lines[idx + 1] == ""


if __name__ == "__main__":
    main()
