from PIL import Image

import imaging
import upscale


def test_cover_box_sdxl_4x_to_16x9():
    assert imaging.cover_box(5376, 3072, 5120, 2880) == (0, 24, 5376, 3048)


def test_cover_box_too_wide():
    assert imaging.cover_box(2000, 1000, 1600, 900) == (111, 0, 1889, 1000)


def test_fit_cover_size():
    img = Image.new("RGB", (1344, 768), "red")
    assert imaging.fit_cover(img, 1280, 720).size == (1280, 720)


def test_is_bust_by_missing_shadow(tmp_path):
    full, bust = tmp_path / "front.png", tmp_path / "happy.png"
    for p in (full, bust):
        Image.new("RGBA", (10, 10)).save(p)
    Image.new("RGBA", (10, 3)).save(tmp_path / "front_shadow.png")
    assert not imaging.is_bust(str(full))
    assert imaging.is_bust(str(bust))


def test_cut_side():
    from PIL import ImageDraw
    im = Image.new("RGBA", (100, 150), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((0, 20, 80, 150), fill=(1, 1, 1, 255))      # sol teref yumru
    d.rectangle((40, 20, 99, 150), fill=(1, 1, 1, 255))   # sag teref duz kesik
    assert imaging.cut_side(im) == "right"
    round_only = Image.new("RGBA", (100, 150), (0, 0, 0, 0))
    ImageDraw.Draw(round_only).ellipse((10, 10, 90, 140), fill=(1, 1, 1, 255))
    assert imaging.cut_side(round_only) is None
    assert imaging.cut_side(Image.new("RGBA", (10, 10))) is None


def test_build_workflow_placeholders():
    wf = upscale.build_workflow("hd_x_01.png", "4x-UltraSharp.pth", "hd_x_01")
    assert wf["1"]["inputs"]["image"] == "hd_x_01.png"
    assert wf["2"]["inputs"]["model_name"] == "4x-UltraSharp.pth"
    assert wf["4"]["inputs"]["filename_prefix"] == "hd_x_01"
