from engine.parser import parse


def test_empty_input():
    cmd = parse("")
    assert cmd.error == "empty"


def test_whitespace_only():
    cmd = parse("   ")
    assert cmd.error == "empty"


def test_unknown_verb():
    cmd = parse("frizzle the bargle")
    assert cmd.error == "unknown_verb"
    assert cmd.verb is None


def test_simple_look():
    cmd = parse("look")
    assert cmd.verb == "look"
    assert cmd.obj is None


def test_look_at_thing():
    cmd = parse("look at the console")
    assert cmd.verb == "look"
    # "at" gets stripped as a connector, articles stripped
    assert cmd.obj == "console"


def test_examine_synonyms():
    for v in ["examine", "x", "inspect", "check"]:
        assert parse(f"{v} mop").verb == "examine"


def test_direction_as_verb():
    cmd = parse("n")
    assert cmd.verb == "go"
    assert cmd.obj == "north"


def test_go_with_connector():
    cmd = parse("go to the east")
    assert cmd.verb == "go"
    assert cmd.obj == "east"


def test_talk_default():
    cmd = parse("talk to tigh")
    assert cmd.verb == "talk"
    assert cmd.obj == "tigh"
    assert cmd.target is None


def test_talk_about_topic():
    cmd = parse("talk to tigh about the flask")
    assert cmd.verb == "talk"
    assert cmd.obj == "tigh"
    assert cmd.target == "flask"


def test_ask_about_topic():
    cmd = parse("ask hadrian about baltar")
    assert cmd.verb == "talk"
    assert cmd.obj == "hadrian"
    assert cmd.target == "baltar"


def test_use_on_target():
    cmd = parse("use canteen on tap")
    assert cmd.verb == "use"
    assert cmd.obj == "canteen"
    assert cmd.target == "tap"


def test_give_to():
    cmd = parse("give canteen to colonel")
    assert cmd.verb == "give"
    assert cmd.obj == "canteen"
    assert cmd.target == "colonel"


def test_inventory_shortcuts():
    for v in ["i", "inv", "inventory"]:
        assert parse(v).verb == "inventory"


def test_take_synonyms():
    for v in ["take", "get", "grab"]:
        assert parse(f"{v} mop").verb == "take"


def test_frak_alone():
    cmd = parse("frak")
    assert cmd.verb == "frak"


def test_punctuation_stripped():
    cmd = parse("examine the locker!")
    assert cmd.verb == "examine"
    assert cmd.obj == "locker"


def test_quit_synonyms():
    for v in ["quit", "exit", "q"]:
        assert parse(v).verb == "quit"


def test_underscores_preserved_in_tokens():
    """Save slot names like 'mid_quest' must not get split into two tokens."""
    cmd = parse("save mid_quest")
    assert cmd.verb == "save"
    assert cmd.obj == "mid_quest"
