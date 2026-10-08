"""Faza 5.3/5.5/5.7 (istifadeci 2026-10-07): vahid keyfiyyet qapisi + xeta sinifleri kataloqu + run sonrasi audit.
- Her hesabat movcud olmali, skriptin cari sha256-si ile uygun olmali ve "problems": [] olmalidir (fail-closed).
- Elave: SFX hadisesi > 0, foto sehnelerinde danisilan pul/faiz reqemlerinin >= 80%-inde overlay, qerar movzusunda
  table + threshold, cold open-da typewriter, motion_history oxsarligi <= 50%.
- Neticə: qa/quality_gate.json + qa/self_audit.md. Pipeline-in son merhelesidir: deliver yalniz qapi kecende.
Istifade:  Projects\\.venv\\Scripts\\python Projects\\quality_gate.py Episodes\\<slug> [--write-catalog]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Callable

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402
import qa_stamp  # noqa: E402

OVERLAY_MIN = 0.80
SIMILARITY_MAX = 0.50
MIN_SECONDS, MAX_SECONDS = 600.0, 720.0       # istifadeci: 10-12 deq
CATALOG = r"C:\YouTubeAI\docs\error_classes.md"

CHECKS = ("script_qa", "math_check", "case_model", "captions_qa", "bg_qa", "owl_qa", "chart_empty", "motion", "sfx",
          "overlay", "decision_visuals", "publish", "video")

# 5.5: xeta sinifleri - teyin -> hansi qapi tutur -> hansi test. Yeni xeta: evvel movcud sinfe aiddirmi yoxla;
# aiddirse hemin qapinin niye buraxdigini duzelt (yalniz simptom yox).
ERROR_CLASSES: list[dict] = [
    {"name": "Hesab səhvi", "definition": "ssenaridəki hesablama nəticəsi yanlışdır",
     "checks": ["math_check"], "tests": ["test_number_accuracy.py::test_real_bug_monthly_total_is_caught"]},
    {"name": "Buraxılmış dəyişən", "definition": "qərar hesabı case-in bir dəyişənini unudur (naive hesab)",
     "checks": ["script_qa", "case_model"],
     "tests": ["test_case_model.py::test_naive_calculation_that_drops_a_variable_is_caught"]},
    {"name": "Case uyğunsuzluğu", "definition": "case kəmiyyəti modeldəkindən fərqlidir",
     "checks": ["script_qa", "case_model"],
     "tests": ["test_case_model.py::test_case_quantity_that_contradicts_the_model_is_caught"]},
    {"name": "Uydurma rəqəm", "definition": "model, mənbə, il və ya sabitdən gəlməyən rəqəm",
     "checks": ["math_check"], "tests": ["test_number_audit.py::test_given_number_outside_the_model_is_caught"]},
    {"name": "Köhnə mənbə", "definition": "3 ildən köhnə mənbə ilsiz sitat olunur",
     "checks": ["script_qa"], "tests": ["test_research.py::test_old_source_must_be_named_with_its_year"]},
    {"name": "Tərif/analogiya", "definition": "termin səhv izah olunur və ya analogiya yanıldır / başqa biznesdir",
     "checks": ["script_qa"],
     "tests": ["test_script_story.py::test_review_checks_story_consistency_and_source_faithfulness",
               "test_script_story.py::test_analogies_are_everyday_images_never_another_business"]},
    {"name": "Vəd cavabsız", "definition": "video qərar sualına konkret qayda ilə cavab vermir",
     "checks": ["script_qa"], "tests": ["test_script_story.py::test_answer_must_be_a_concrete_conditional_rule"]},
    {"name": "Təkrar", "definition": "eyni rəqəm 2 dəfədən çox deyilir, Recap misal/rəqəm təkrarlayır",
     "checks": ["script_qa"],
     "tests": ["test_script_story.py::test_same_figure_three_times_in_one_section_is_a_repeat",
               "test_script_story.py::test_recap_with_an_example_is_rejected"]},
    {"name": "Generik kart", "definition": "flow/timeline addımı case-ə bağlı deyil (Analyze → Evaluate…)",
     "checks": ["chart_empty"], "tests": ["test_data_visuals.py::test_generic_flow_steps_are_rejected"]},
    {"name": "Boş chart", "definition": "chart-ın ilk saniyələrində yalnız başlıq görünür",
     "checks": ["chart_empty"],
     "tests": ["test_remotion_build.py::test_chart_scenes_render_a_skeleton_from_the_first_frame"]},
    {"name": "Generik foto", "definition": "case biznesinin literal kadrı olmayan foto > 10%",
     "checks": ["bg_qa"],
     "tests": ["test_literal_frames.py::test_stage_fails_when_more_than_ten_percent_of_photos_are_generic"]},
    {"name": "Təkrar kadr", "definition": "epizodda eyni obyekt/fon iki dəfə",
     "checks": ["bg_qa"], "tests": ["test_no_repeats.py::test_check_bgs_stage_fails_while_duplicates_remain"]},
    {"name": "Uşaqsayağı görünüş", "definition": "oyuncaq/cizgi fon, uşaq musiqisi",
     "checks": ["bg_qa"], "tests": ["test_adult_look.py::test_judge_rejects_childish_images"]},
    {"name": "Səs səviyyəsi", "definition": "yekun səs −14 ±1 LUFS deyil",
     "checks": ["video"], "tests": ["test_sfx.py::test_master_mixes_sfx_before_loudnorm_to_minus_14"]},
    {"name": "TTS dili/tələffüzü", "definition": "rəqəm səsdə səhv/başqa dildə oxunur",
     "checks": ["captions_qa"], "tests": ["test_speech.py::test_numbers_are_spelled_for_the_voice",
                                          "test_captions.py::test_mispronounced_number_is_reported"]},
    {"name": "Altyazı formatı", "definition": "altyazı ssenaridən deyil və ya rəqəm \"$4,000\" formatında deyil",
     "checks": ["captions_qa"], "tests": ["test_captions.py::test_srt_uses_display_numbers"]},
    {"name": "Etiket toqquşması", "definition": "chart/overlay/sayğac bayquş və ya altyazı ilə üst-üstə düşür",
     "checks": ["overlay"],
     "tests": ["test_remotion_build.py::test_overlay_box_avoids_the_owl_and_the_captions",
               "test_remotion_build.py::test_wide_owl_on_a_chart_scene_stays_right_of_the_chart_area",
               "test_data_visuals.py::test_map_counter_and_box_avoid_owl_and_captions"]},
    {"name": "Eyni animasiya", "definition": "hərəkət planı son epizodlara > 50% oxşardır",
     "checks": ["motion"], "tests": ["test_motion.py::test_history_similarity_above_half_changes_the_theme"]},
    {"name": "Sabit kodlanmış data", "definition": "chart-da danışıqda olmayan rəqəm",
     "checks": ["chart_empty"], "tests": ["test_visuals.py::test_number_not_in_narration_is_rejected",
                                          "test_data_visuals.py::test_timeseries_number_not_said_is_rejected"]},
    {"name": "Ölü vaxt (səssiz kart)", "definition": "qara kart + sükut; typewriter səhnə müddətini uzadır",
     "checks": ["motion", "video"],
     "tests": ["test_remotion_build.py::test_props_carry_the_motion_plan_and_emphasis"]},
    {"name": "SFX səviyyəsi/sıxlığı", "definition": "SFX nitqdən < 18 dB aşağı, 10 s-də > 2, söz ortasında",
     "checks": ["sfx"], "tests": ["test_sfx.py::test_density_is_at_most_two_per_ten_seconds",
                                  "test_sfx.py::test_sfx_sits_at_least_18_db_below_speech"]},
    {"name": "Real şəxs haqqında mənbəsiz hüquqi iddia", "definition": "real şəxs/şirkət haqqında ittiham (sued, fraud…)",
     "checks": ["script_qa"],
     "tests": ["test_script_story.py::test_unsourced_legal_claim_about_a_real_company_is_caught"]},
]


def _load(ep: str, name: str) -> dict | None:
    path = os.path.join(ep, name)
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _report(ep: str, name: str) -> tuple[dict | None, list[str]]:
    """Moherlu hesabat: yoxdursa / kohnedirse / problem varsa -> problem siyahisi."""
    rep = _load(ep, name)
    if rep is None:
        return None, [f"{name} yoxdur"]
    if not qa_stamp.is_fresh(ep, rep):
        return rep, [f"{name} kohnedir (skript sonradan deyisib)"]
    return rep, list(rep.get("problems") or [])


def _case_model(ep: str) -> list[str]:
    plan = (_load(ep, "meta.json") or {}).get("plan") or {}
    if config.CASE_MODEL and not (plan.get("model") and plan.get("model_result")):
        return ["case modeli / model_result yoxdur (meta.json plan)"]
    return []


def _bg(ep: str) -> list[str]:
    import stages
    rep, probs = _report(ep, "bg_qa.json")
    if rep is not None:
        if rep.get("duplicates"):
            probs.append(f"tekrar kadrlar: {rep['duplicates']}")
        if float(rep.get("generic_share") or 0) > stages.GENERIC_MAX:
            probs.append(f"generik foto {rep['generic_share']:.0%} > {stages.GENERIC_MAX:.0%}")
    return probs


def _owl(ep: str, slug: str) -> list[str]:
    import stages
    rep, probs = _report(ep, "owl_qa.json")
    if rep is None:
        return probs
    ctx = stages.Ctx(topic="", slug=slug, ep_dir=ep, words=0, music=None, min_seconds=0, max_seconds=0, provider="")
    return probs + stages.verify_owls(ctx)


def _motion(ep: str) -> tuple[list[str], list[str]]:
    import remotion_build as rb
    rep, probs = _report(ep, os.path.join("qa", "motion.json"))
    empty: list[str] = []
    if rep is not None:
        if config.TYPEWRITER and not rep.get("typewriter_cold_open"):
            probs.append("cold open-da typewriter yoxdur")
        if float(rep.get("similarity_max") or 0) > SIMILARITY_MAX:
            probs.append(f"motion_history oxsarligi {rep['similarity_max']:.0%} > 50%")
        if float(rep.get("chart_empty_share") or 0) > rb.EMPTY_MAX:
            empty.append(f"bos chart payi {rep['chart_empty_share']:.1%} > {rb.EMPTY_MAX:.0%}")
    else:
        empty.append("qa/motion.json yoxdur")
    return list(dict.fromkeys(probs)), empty


def _sfx(ep: str) -> list[str]:
    rep, probs = _report(ep, os.path.join("qa", "sfx.json"))
    if rep is not None and config.SFX and int(rep.get("count") or 0) <= 0:
        probs.append("SFX hadisesi yoxdur")
    return probs


def overlay_coverage(props: dict) -> float:
    """Foto sehnelerinde danisilan pul/faiz reqemi olan sehnelerin neçesinde overlay var (sehnede <= 1 overlay)."""
    import remotion_build as rb
    fps, start, need, have = props["fps"], props["introFrames"], 0, 0
    for s in props["scenes"]:
        if not s.get("visual") and rb.number_overlay(props["words"], start / fps, s["frames"], fps):
            need += 1
            have += bool(s.get("overlay"))
        start += s["frames"]
    return have / need if need else 1.0


def _overlay(ep: str) -> list[str]:
    props = _load(ep, "remotion_props.json")
    if props is None:
        return ["remotion_props.json yoxdur"]
    cov = overlay_coverage(props)
    if config.NUMBER_OVERLAY and cov < OVERLAY_MIN:
        return [f"foto reqemlerinin yalniz {cov:.0%}-inde overlay var (min {OVERLAY_MIN:.0%})"]
    return []


def _decision(ep: str) -> list[str]:
    plan = (_load(ep, "meta.json") or {}).get("plan") or {}
    if not (plan.get("model") or {}).get("threshold"):
        return []
    kinds = {((s.get("visual") or {}).get("kind")) for s in ((_load(ep, "scenes.json") or {}).get("scenes") or [])}
    return [f"qerar movzusunda {k} sehnesi yoxdur" for k in ("table", "threshold") if k not in kinds]


def _video(path: str, lo: float = MIN_SECONDS, hi: float = MAX_SECONDS) -> list[str]:
    import checks
    if not os.path.isfile(path):
        return [f"{os.path.basename(path)} yoxdur"]
    probs = checks.final_video_problems(path)
    secs = checks.duration(path)
    if not lo <= secs <= hi:
        probs.append(f"muddet {secs / 60:.2f} deq ({lo / 60:.0f}-{hi / 60:.0f} deq lazimdir)")
    return probs


def gate(ep: str, slug: str, video: Callable[[str], list[str]] | None = None,
         pack: Callable[[str], list[str]] | None = None) -> dict:
    import math_check
    import script_qa
    if pack is None:
        from publish_pack import pack_problems as pack
    video = video or _video
    motion_probs, empty = _motion(ep)
    res = {
        "script_qa": script_qa.report_problems(ep),
        "math_check": math_check.report_problems(ep),           # number_audit-in son hokmu de buradadir
        "case_model": _case_model(ep),
        "captions_qa": _report(ep, "captions_qa.json")[1],
        "bg_qa": _bg(ep),
        "owl_qa": _owl(ep, slug),
        "chart_empty": empty,
        "motion": motion_probs,
        "sfx": _sfx(ep),
        "overlay": _overlay(ep),
        "decision_visuals": _decision(ep),
        "publish": pack(os.path.join(ep, "youtube")),
        "video": video(os.path.join(ep, f"{slug}.mp4")),
    }
    return {"passed": not any(res.values()), "checks": res}


def self_audit(result: dict) -> str:
    """5.7: kataloqdaki her sinif ucun "yoxlandi / netice" (sinfin qapilarinin cari neticesi)."""
    lines = ["# Self audit — xəta sinifləri", "", "| Sinif | Qapı | Nəticə |", "|---|---|---|"]
    for c in ERROR_CLASSES:
        probs = [p for k in c["checks"] for p in result["checks"].get(k, [])]
        verdict = "yoxlandı: OK" if not probs else "XƏTA: " + "; ".join(str(p) for p in probs)[:300]
        lines.append(f"| {c['name']} | {', '.join(c['checks'])} | {verdict} |")
    lines += ["", f"**Qapı:** {'KEÇDİ' if result['passed'] else 'KEÇMƏDİ'}"]
    return "\n".join(lines) + "\n"


def write_outputs(ep: str, result: dict) -> None:
    qa = os.path.join(ep, "qa")
    os.makedirs(qa, exist_ok=True)
    with open(os.path.join(qa, "quality_gate.json"), "w", encoding="utf-8") as f:
        json.dump({**result, "problems": [f"{k}: {p}" for k, v in result["checks"].items() for p in v]},
                  f, ensure_ascii=False, indent=1)
    with open(os.path.join(qa, "self_audit.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(self_audit(result))


def catalog_markdown() -> str:
    """docs/error_classes.md bu funksiyadan yaradilir (test sinxronlugu yoxlayir)."""
    lines = ["# Xəta sinifləri kataloqu", "",
             "Generated from `Projects/quality_gate.py` (`ERROR_CLASSES`) — əl ilə redaktə etmə: "
             "`python Projects/quality_gate.py --write-catalog`.", "",
             "Yeni xəta tapılanda əvvəlcə mövcud sinfə aid olub-olmadığı yoxlanır. Aiddirsə, həmin qapının niyə "
             "buraxdığı düzəldilir (yalnız simptom yox); aid deyilsə yeni sinif + qapı + test əlavə olunur.", "",
             "| Sinif | Tərif | Qapı (quality_gate) | Test |", "|---|---|---|---|"]
    for c in ERROR_CLASSES:
        tests = "<br>".join(f"`{t}`" for t in c["tests"])
        lines.append(f"| {c['name']} | {c['definition']} | {', '.join(c['checks'])} | {tests} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("episode_dir", nargs="?")
    ap.add_argument("--slug")
    ap.add_argument("--min-seconds", type=float, default=MIN_SECONDS)
    ap.add_argument("--max-seconds", type=float, default=MAX_SECONDS)
    ap.add_argument("--write-catalog", action="store_true")
    a = ap.parse_args()
    if a.write_catalog:
        with open(CATALOG, "w", encoding="utf-8", newline="\n") as f:
            f.write(catalog_markdown())
        print("katalog ->", CATALOG)
        if not a.episode_dir:
            return
    ep = a.episode_dir
    slug = a.slug or os.path.basename(os.path.normpath(ep))
    result = gate(ep, slug, video=lambda p: _video(p, a.min_seconds, a.max_seconds))
    write_outputs(ep, result)
    for k, v in result["checks"].items():
        print(f"  {k:17s} {'OK' if not v else v}")
    if not result["passed"]:
        raise SystemExit("keyfiyyet qapisi KECMEDI - bax: qa/quality_gate.json, qa/self_audit.md")
    print("keyfiyyet qapisi KECDI")


if __name__ == "__main__":
    main()
