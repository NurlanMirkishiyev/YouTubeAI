def test_existing_modules_import():
    import montage  # noqa: F401
    import script_gen

    assert script_gen.WPM == 199.0
