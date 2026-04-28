from unittest.mock import MagicMock, patch

from src.auth import generate_pkce_challange, generate_pkce_challenge, main


def test_generate_pkce_legacy_wrapper_matches_current_helper():
    """Ensures the misspelled historical helper remains compatible."""
    with patch(
        "src.auth.generate_pkce_challenge", return_value=("verifier", "challenge")
    ):
        assert generate_pkce_challange() == ("verifier", "challenge")


@patch("src.auth.get_refresh_token")
@patch("src.auth.DropboxAuthSettings")
def test_auth_main_uses_minimal_dropbox_settings(mock_settings, mock_get_refresh_token):
    """Ensures Dropbox auth bootstrap does not require full app settings."""
    mock_settings.return_value = MagicMock(DROPBOX_APP_KEY="app-key")

    main()

    mock_get_refresh_token.assert_called_once_with("app-key")


@patch("src.auth.get_refresh_token")
@patch("src.auth.DropboxAuthSettings", side_effect=ValueError("missing"))
def test_auth_main_handles_missing_app_key(
    mock_settings, mock_get_refresh_token, capsys
):
    """Ensures missing bootstrap config exits before starting OAuth."""
    main()

    output = capsys.readouterr().out
    assert "DROPBOX_APP_KEY" in output
    mock_get_refresh_token.assert_not_called()


def test_generate_pkce_challenge_returns_verifier_and_challenge():
    """Ensures the PKCE helper returns populated values."""
    verifier, challenge = generate_pkce_challenge()

    assert verifier
    assert challenge
