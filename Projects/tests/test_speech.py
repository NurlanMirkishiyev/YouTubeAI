"""Istifadeci 2026-10-05 (#54): reqemler duzgun ingilis telaffuzu ile oxunsun (TTS), altyazida "$4,000" formati."""
import pytest

from speech import to_display, to_speech


@pytest.mark.parametrize("text, spoken", [
    ("Rent is $4,000 a month.", "Rent is four thousand dollars a month."),
    ("It sells for $9.99 today.", "It sells for nine dollars and ninety-nine cents today."),
    ("Only $0.50 more.", "Only fifty cents more."),
    ("A $1.5 million loan.", "A one point five million dollars loan."),
    ("Margins fell 15% this year.", "Margins fell fifteen percent this year."),
    ("About 2.5% of sales.", "About two point five percent of sales."),
    ("We shipped 2,500 boxes.", "We shipped two thousand five hundred boxes."),
    ("In 2023 sales doubled.", "In twenty twenty-three sales doubled."),
    ("Sales doubled in 2023.", "Sales doubled in twenty twenty-three."),
    ("Prices rose 4.5, then 2023, 2024.", "Prices rose four point five, then twenty twenty-three, twenty twenty-four."),
    ("From 1994-2020 survival was 48.9%.",
     "From nineteen ninety-four to twenty twenty survival was forty-eight point nine percent."),
    ("That is 3x the cost.", "That is three times the cost."),
    ("Her 1st store opened.", "Her first store opened."),
    ("A $10k budget.", "A ten thousand dollars budget."),
])
def test_numbers_are_spelled_for_the_voice(text, spoken):
    assert to_speech(text) == spoken


def test_speech_leaves_text_without_digits_unchanged():
    assert to_speech("Profit is what is left over.") == "Profit is what is left over."


@pytest.mark.parametrize("text, shown", [
    ("It costs four thousand dollars a month.", "It costs $4,000 a month."),
    ("That is fifteen percent of sales.", "That is 15% of sales."),
    ("A price of nine dollars and ninety-nine cents.", "A price of $9.99."),
    ("Rent is $4000 now.", "Rent is $4,000 now."),
    ("We had 2500 orders.", "We had 2,500 orders."),
    ("Twenty-three customers came back.", "23 customers came back."),
    ("One common mistake is three steps away.", "One common mistake is three steps away."),
    ("In 2023 we grew.", "In 2023 we grew."),
])
def test_display_uses_digit_format(text, shown):
    assert to_display(text) == shown


def test_intro_card_speaks_the_cold_open_or_falls_back_to_the_topic():
    from timeline import intro_text
    md = "# T\n\n## Cold Open\n\nA $9.99 price can earn less than $10.\n\n## Hook\n\nText.\n"
    assert intro_text(md, "Why 9.99?") == "A $9.99 price can earn less than $10."
    assert intro_text("# T\n\n## Hook\n\nText.\n", "Why 9.99?") == "Why 9.99?"


def test_tts_sends_every_text_through_the_number_normaliser():
    """TTS venv-de kokoro var, burada yox - menbe seviyyesinde: synth to_speech-siz Kokoro-ya metn vermir."""
    import pathlib
    src = pathlib.Path(__file__).parents[1].joinpath("tts_gen.py").read_text(encoding="utf-8")
    body = src.split("def synth(", 1)[1].split("\ndef ", 1)[0]
    assert "to_speech(text)" in body and "intro_text(" in src
