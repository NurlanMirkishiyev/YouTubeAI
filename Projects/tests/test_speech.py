import speech


def test_numbers_are_read_as_words_and_nothing_else_changes():
    assert speech.to_speech("It costs $4,000 a year.") == "It costs four thousand dollars a year."
    assert speech.to_speech("Only 2% pay.") == "Only two percent pay."
    assert speech.to_speech("Meta made $201 billion.") == "Meta made two hundred and one billion dollars."
    assert speech.to_speech("In 2023, it grew.") == "In twenty twenty-three, it grew."
    assert speech.to_speech("No numbers here!") == "No numbers here!"


def test_scaled_money_and_plain_thousands():
    assert speech.to_speech("$196 billion") == "one hundred and ninety-six billion dollars"
    assert speech.to_speech("1,000,000 users") == "one million users"
    assert speech.to_speech("$100,000") == "one hundred thousand dollars"
    assert speech.to_speech("$5") == "five dollars"


def test_decimal_percent_keeps_every_fraction_digit():
    assert speech.to_speech("2.5%") == "two point five percent"
    assert speech.to_speech("2.50%") == "two point five zero percent"


def test_year_and_trailing_punctuation_survive():
    assert speech.to_speech("In 2024, it grew.") == "In twenty twenty-four, it grew."
    assert speech.to_speech("$4,000.") == "four thousand dollars."


def test_decades_are_spoken_as_plurals():
    assert speech.to_speech("the 1990s") == "the nineteen nineties"
    assert speech.to_speech("the 90s") == "the nineties"


def test_ordinals_are_spoken_as_ordinals():
    assert speech.to_speech("1st place") == "first place"


def test_digits_glued_to_letters_are_split_from_the_letters():
    assert speech.to_speech("10x growth") == "ten x growth"
    assert speech.to_speech("Q3") == "Q three"


def test_cents_are_spoken_as_dollars_and_cents():
    assert speech.to_speech("$4,000.50") == "four thousand dollars and fifty cents"
    assert speech.to_speech("$1.05") == "one dollar and five cents"
    assert speech.to_speech("$0.50") == "zero dollars and fifty cents"
