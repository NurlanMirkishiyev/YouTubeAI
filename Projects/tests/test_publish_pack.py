from PIL import Image

import publish_pack as pp

SCENES = [{"section": "Hook", "duration": 10}, {"section": "Hook", "duration": 10},
          {"section": "Section 1: A", "duration": 30}, {"section": "Section 2: B", "duration": 5},
          {"section": "Recap", "duration": 40}, {"section": "Call to Action", "duration": 20}]


def test_fmt_ts():
    assert pp.fmt_ts(0) == "00:00"
    assert pp.fmt_ts(754.2) == "12:34"
    assert pp.fmt_ts(3725) == "1:02:05"


def test_chapters_start_at_zero_and_drop_short():
    assert pp.chapters(SCENES, 4.0, 125.0) == [
        (0.0, "Intro"), (24.0, "A"), (59.0, "Recap"), (99.0, "Call to Action")]


def test_chapters_need_three():
    assert pp.chapters(SCENES[:3], 4.0, 60.0) == []


def test_fit_tags_dedupes_and_limits():
    tags = ["Trademark", "trademark", "a, b"] + ["x" * 100] * 10
    out = pp.fit_tags(tags, limit=120)
    assert out[:2] == ["Trademark", "a b"]
    assert sum(len(t) for t in out) + len(out) - 1 <= 120


def test_pick_title():
    assert pp.pick_title(["x" * 90, "Good Title"]) == "Good Title"
    assert len(pp.pick_title(["word " * 30])) <= 70


def test_description_has_chapters():
    d = pp.description("Sum.", [(0.0, "Hook"), (24.0, "A"), (59.0, "Recap")], ["eli5", "#business"])
    assert "00:00 Hook" in d and "00:24 A" in d and "#eli5 #business" in d


def test_pack_problems(tmp_path):
    (tmp_path / "title.txt").write_text("T", encoding="utf-8")
    (tmp_path / "description.txt").write_text("00:00 Hook", encoding="utf-8")
    (tmp_path / "tags.txt").write_text("a,b", encoding="utf-8")
    Image.new("RGB", (1280, 720)).save(tmp_path / "thumbnail.png")
    pp.write_midrolls(str(tmp_path), [100.0, 250.0, 400.0])
    pp.write_checklist(str(tmp_path), ["A", "B", "C"])
    assert pp.pack_problems(str(tmp_path)) == []
    Image.new("RGB", (100, 100)).save(tmp_path / "thumbnail.png")
    assert pp.pack_problems(str(tmp_path))


def test_music_credit_for_cc_by_track():
    c = pp.music_credit(r"C:\YouTubeAI\Music\Carefree.mp3", {"Carefree.mp3": "Carefree"})
    assert '"Carefree" Kevin MacLeod (incompetech.com)' in c
    assert "Creative Commons: By Attribution 4.0" in c


def test_music_credit_empty_for_unknown_or_missing_track():
    assert pp.music_credit(None, {"Carefree.mp3": "Carefree"}) == ""
    assert pp.music_credit("own.mp3", {"Carefree.mp3": "Carefree"}) == ""


def test_description_appends_credit():
    d = pp.description("Sum.", [(0.0, "Hook")], ["eli5"], credit="Music: X")
    assert d.rstrip().endswith("Music: X") and "00:00 Hook" in d


def test_description_names_the_verified_source():
    """#58: tedqiqat menbeyi YouTube description-da da gorunur."""
    import publish_pack as pp
    src = {"publisher": "Federal Reserve Banks", "year": 2025, "url": "https://www.fedsmallbusiness.org/r.pdf"}
    line = pp.source_line(src)
    assert line == "Source: Federal Reserve Banks (2025) - https://www.fedsmallbusiness.org/r.pdf"
    assert pp.source_line({}) == ""
    assert line in pp.description("Summary.", [(0.0, "Intro")], [], line)


# --- Faza 4 (istifadeci 2026-10-07): RPM - mid-roll, lead magnet/affiliate, upload checklist ---

def _sections(starts: list[float], total: float) -> list[dict]:
    """Bolme baslanğiclari (s) -> scenes (intro 0 ile)."""
    bounds = starts + [total]
    return [{"section": f"S{i}", "duration": bounds[i + 1] - bounds[i]} for i in range(len(starts))]


def test_midrolls_sit_one_second_before_a_section_change():
    scenes = _sections([0, 70, 200, 330, 470, 600], 680)
    points = pp.midrolls(scenes, 0.0, 680)
    starts = {70, 200, 330, 470, 600}
    assert points and all(p + 1 in starts for p in points)


def test_midrolls_skip_the_first_minute_and_stay_two_minutes_apart():
    scenes = _sections([0, 30, 59, 150, 200, 290, 420, 560, 640], 700)
    points = pp.midrolls(scenes, 0.0, 700)
    assert min(points) >= 60
    assert all(b - a >= 120 for a, b in zip(points, points[1:]))
    assert 3 <= len(points) <= 4


def test_midrolls_are_at_most_four_and_spread_over_the_video():
    starts = [0] + list(range(65, 700, 61))
    points = pp.midrolls(_sections(starts, 720), 0.0, 720)
    assert len(points) == 4
    assert points[-1] - points[0] >= 360          # yalniz evvelde toplanmir


def test_midrolls_file_lists_timestamps(tmp_path):
    pp.write_midrolls(str(tmp_path), [129.0, 269.5, 400.0])
    lines = [ln for ln in (tmp_path / "midrolls.txt").read_text(encoding="utf-8").splitlines()
             if ln and not ln.startswith("#")]
    assert lines == ["02:09", "04:29", "06:40"]


def test_description_adds_lead_magnet_and_affiliate_blocks_from_config():
    extra = pp.monetization_block("https://b-datamation.com/checklist",
                                  ["Bookkeeping app - https://x.test/a", "Invoicing - https://x.test/b"])
    d = pp.description("Sum.", [(0.0, "Intro")], ["eli5"], credit="Music: X", extra=extra)
    assert "https://b-datamation.com/checklist" in d and "https://x.test/b" in d
    assert "affiliate" in d.lower()              # FTC: affiliate linkleri aciqlanir
    assert d.index("checklist") < d.index("Music: X")


def test_empty_config_writes_no_monetization_block():
    assert pp.monetization_block("", []) == ""
    assert "affiliate" not in pp.monetization_block("https://b.test/c", []).lower()


def test_config_reads_links_from_the_environment(monkeypatch):
    import config
    monkeypatch.setenv("LEAD_MAGNET_URL", " https://b.test/c ")
    monkeypatch.setenv("AFFILIATE_LINKS", "App - https://x.test/a | Tool - https://x.test/b")
    assert config.lead_magnet_url() == "https://b.test/c"
    assert config.affiliate_links() == ["App - https://x.test/a", "Tool - https://x.test/b"]
    monkeypatch.setenv("AFFILIATE_LINKS", "")
    assert config.affiliate_links() == []


def test_upload_checklist_has_every_required_step(tmp_path):
    pp.write_checklist(str(tmp_path), ["Title One", "Title Two", "Title Three"])
    text = (tmp_path / "upload_checklist.txt").read_text(encoding="utf-8")
    for needle in ("not made for kids", "all ad formats", "midrolls.txt", "Title One", "Title Three",
                   "thumbnail", "ET"):
        assert needle.lower() in text.lower(), needle


def test_pack_problems_require_midrolls_and_checklist(tmp_path):
    (tmp_path / "title.txt").write_text("T", encoding="utf-8")
    (tmp_path / "description.txt").write_text("00:00 Hook", encoding="utf-8")
    (tmp_path / "tags.txt").write_text("a,b", encoding="utf-8")
    Image.new("RGB", (1280, 720)).save(tmp_path / "thumbnail.png")
    assert "midrolls.txt yoxdur" in pp.pack_problems(str(tmp_path))
    pp.write_midrolls(str(tmp_path), [100.0])
    pp.write_checklist(str(tmp_path), ["A", "B", "C"])
    assert pp.pack_problems(str(tmp_path)) == ["mid-roll 1 (3..4 lazimdir)"]
    pp.write_midrolls(str(tmp_path), [100.0, 250.0, 400.0])
    assert pp.pack_problems(str(tmp_path)) == []
