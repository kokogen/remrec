# tests/test_gdrive_auth.py
import pytest
from unittest.mock import patch, MagicMock
from gdrive_auth import gdrive_authenticate

@patch("gdrive_auth.os.path.exists")
@patch("gdrive_auth.InstalledAppFlow.from_client_secrets_file")
@patch("builtins.input", return_value="credentials.json")
def test_gdrive_authenticate_new_token(mock_input, mock_flow, mock_exists):
    """Test the authentication process when no token exists."""
    mock_exists.return_value = False
    mock_creds = MagicMock()
    mock_flow.return_value.run_local_server.return_value = mock_creds
    
    with patch("builtins.open", new_callable=pytest.mock.mock_open) as mock_file:
        gdrive_authenticate()
        mock_file.assert_called_with("gdrive_token.json", "w")
        mock_creds.to_json.assert_called_once()

@patch("gdrive_auth.os.path.exists")
@patch("gdrive_auth.Credentials.from_authorized_user_info")
def test_gdrive_authenticate_existing_token(mock_creds_from_info, mock_exists):
    """Test the authentication process when a valid token already exists."""
    mock_exists.return_value = True
    mock_creds = MagicMock(valid=True)
    mock_creds_from_info.return_value = mock_creds
    
    with patch("builtins.open", new_callable=pytest.mock.mock_open, read_data='{}'):
        gdrive_authenticate()
        mock_creds.refresh.assert_not_called()
