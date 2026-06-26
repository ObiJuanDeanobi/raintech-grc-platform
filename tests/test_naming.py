from cmmc_tracker.naming import generated_evidence_filename, sanitize_filename_part


def test_filename_generation_preserves_objective_and_extension():
    name = generated_evidence_filename(
        "AC.L2-3.1.1a",
        "auth user list",
        ".pdf",
    )

    assert name == "AC.L2-3.1.1a-auth user list.pdf"


def test_filename_sanitizes_invalid_characters():
    assert sanitize_filename_part('SSP: "CUI"/Scope?') == "SSP CUI Scope"


def test_filename_collision_suffixes_are_stable():
    used = set()
    first = generated_evidence_filename("IA.L1-3.5.1a", "MFA", "png", used)
    second = generated_evidence_filename("IA.L1-3.5.1a", "MFA", "png", used)

    assert first == "IA.L1-3.5.1a-MFA.png"
    assert second == "IA.L1-3.5.1a-MFA-001.png"
