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


def test_build_workflow_placeholders():
    wf = upscale.build_workflow("hd_x_01.png", "4x-UltraSharp.pth", "hd_x_01")
    assert wf["1"]["inputs"]["image"] == "hd_x_01.png"
    assert wf["2"]["inputs"]["model_name"] == "4x-UltraSharp.pth"
    assert wf["4"]["inputs"]["filename_prefix"] == "hd_x_01"
