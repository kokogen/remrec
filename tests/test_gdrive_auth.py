# tests/test_gdrive_auth.py
from unittest.mock import patch, MagicMock, mock_open, call
from src.gdrive_auth import gdrive_authenticate

@patch("src.gdrive_auth.os.path.exists")
@patch("src.gdrive_auth.InstalledAppFlow.from_client_config")
@patch("builtins.input", return_value="credentials.json")
@patch("src.gdrive_auth.json.load")
def test_gdrive_authenticate_new_token(
    mock_json_load, mock_input, mock_flow, mock_exists
):
    """Test the authentication process when no token exists."""
    def mock_path_exists(path):
        if path == "gdrive_token.json":
            return False
        elif path == "credentials.json":
            return True
        return False

    mock_exists.side_effect = mock_path_exists
    mock_json_load.return_value = {"installed": {}}
    mock_creds = MagicMock()
    mock_creds.to_json.return_value = "mock_json_token"
    mock_flow.return_value.run_local_server.return_value = mock_creds

    with patch("builtins.open", mock_open()) as mock_file:
        gdrive_authenticate()
        mock_exists.assert_has_calls([call("gdrive_token.json"), call("credentials.json")])
        mock_flow.assert_called_once()
        mock_creds.to_json.assert_called_once()
        mock_file.assert_called_with("gdrive_token.json", "w")
        mock_file().write.assert_called_once_with("mock_json_token")

@patch("src.gdrive_auth.os.path.exists")
@patch("src.gdrive_auth.Credentials.from_authorized_user_info")
def test_gdrive_authenticate_existing_token(mock_creds_from_info, mock_exists):
    """Test the authentication process when a valid token already exists."""
    mock_exists.return_value = True
    mock_creds = MagicMock(valid=True)
    mock_creds_from_info.return_value = mock_creds
    
    with patch("builtins.open", mock_open(read_data='{}')):
        gdrive_authenticate()
        mock_creds.refresh.assert_not_called()
