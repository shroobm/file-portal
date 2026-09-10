"""Levers (docs/18 modularity gate): every key has a signed default and a range or menu;
anything missing, unparseable or out of range falls back AND is named, never silently ignored."""

from indexer.config import Paths, Settings, lever_menu, lever_range


def test_absent_file_means_signed_defaults_and_no_fallbacks(tmp_path):
    settings = Settings.load(tmp_path / "nope.toml")
    assert settings.effective() == {
        "passage_chars": 800,
        "passage_max_chars": 1200,
        "threads": 4,
        "top_k": 5,
        "serve_port": 8765,
        "model": "sentence-transformers/all-MiniLM-L6-v2",
        "query_mode": "hybrid",
        "rerank": "off",
        "fts_tokenizer": "unicode61",
    }
    assert settings.fallbacks == ()


def test_out_of_range_wrong_type_and_off_menu_fall_back_and_are_named(tmp_path):
    toml = tmp_path / "indexer.toml"
    toml.write_text(
        '[index]\npassage_chars = 5\nthreads = "x"\ntop_k = true\nquery_mode = "magic"\n'
        'model = ""\nfts_tokenizer = "icu"\n'
    )

    settings = Settings.load(toml)

    assert settings.passage_chars == 800 and settings.threads == 4 and settings.top_k == 5
    assert settings.query_mode == "hybrid" and settings.fts_tokenizer == "unicode61"
    assert settings.model.startswith("sentence-transformers/")
    assert settings.fallbacks == (
        "passage_chars=5->800",
        "threads='x'->4",
        "top_k=True->5",
        "model=''->sentence-transformers/all-MiniLM-L6-v2",
        "query_mode='magic'->hybrid",
        "fts_tokenizer='icu'->unicode61",
    )


def test_max_below_target_is_raised_to_target_and_named(tmp_path):
    toml = tmp_path / "indexer.toml"
    toml.write_text("[index]\npassage_chars = 1000\npassage_max_chars = 300\n")

    settings = Settings.load(toml)

    assert settings.passage_max_chars == 1000
    assert settings.fallbacks == ("passage_max_chars=300->1000",)


def test_menus_and_ranges_are_the_bounds_the_loader_enforces():
    assert lever_range("top_k") == (1, 50)
    assert lever_menu("query_mode") == ("hybrid", "vector", "keyword")
    assert lever_menu("model") == ()


def test_ensure_exist_never_creates_the_vault(tmp_path):
    paths = Paths.from_root(tmp_path / "file-portal")
    paths.ensure_exist()
    assert paths.index.is_dir() and paths.models.is_dir() and paths.logs.is_dir()
    assert not paths.vault_bare.exists(), "exactly one side initialises the vault; not this one"
