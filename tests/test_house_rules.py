"""Public project style and presentation claims stay locked in CI."""
from pathlib import Path

from bayhack.benchmark import run_benchmark


ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".py", ".md", ".html", ".svg", ".yml", ".yaml", ".txt"}


def public_text_files():
    for path in ROOT.rglob("*"):
        if (
            path.is_file()
            and ".git" not in path.parts
            and ".venv" not in path.parts
            and path.suffix.lower() in TEXT_SUFFIXES
        ):
            yield path


def test_no_em_dashes_in_public_project_text():
    forbidden = (chr(0x2014), "&" + "mdash;", "&#" + "8212;")
    violations = []
    for path in public_text_files():
        text = path.read_text()
        if any(token in text for token in forbidden):
            violations.append(str(path.relative_to(ROOT)))
    assert not violations, f"em dash found in: {violations}"


def test_public_story_is_track_c_verified_tube_access_first():
    readme = (ROOT / "README.md").read_text()
    site = (ROOT / "docs" / "index.html").read_text()
    for phrase in (
        "TubeProof",
        "Track C",
        "verified tube access",
        "independent physical",
        "partial uncap",
        "No verified opening, no pipetting",
        "No verified closure",
        "liquid handling",
    ):
        assert phrase.lower() in (readme + site).lower()
    assert "Track A remains available as a fallback" in readme
    assert "TEM1_TRACK_A.md" in readme
    assert "python3 -m bayhack.track_c_demo" in readme
    assert "python3 -m bayhack.track_c_dashboard" in readme
    assert "python3 -m bayhack.preflight" in readme
    assert "No modeled value may be described as measured" in readme


def test_generic_fallback_benchmark_remains_green():
    result = run_benchmark(seeds=range(1, 11))
    assert result["avg_runs"] == 6.0
    assert result["reaction_volume_saved_ul"] == 800.0
    assert result["tips_saved"] == 40.0


def test_projector_slide_has_real_repo_qr():
    slide = (ROOT / "docs" / "slide.html").read_text()
    qr = (ROOT / "docs" / "qr.svg").read_text()
    assert 'src="qr.svg"' in slide
    assert 'id="qr-path"' in qr
    assert '#3c8446' in qr


def test_authorship_rules_name_di_omics():
    rules = (ROOT / "HOUSE_RULES.md").read_text()
    assert "Git author and committer name must be `di-omics`" in rules
    assert "co-author trailers" in rules
