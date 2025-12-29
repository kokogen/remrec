# tests/test_gdrive_auth.py
import pytest
from unittest.mock import patch, MagicMock, mock_open, call
from src.gdrive_auth import gdrive_authenticate

@patch("src.gdrive_auth.os.path.exists")
@patch("src.gdrive_auth.InstalledAppFlow.from_client_config")
@patch("builtins.input", return_value="credentials.json")
@patch("src.gdrive_auth.json.load") # Patch json.load
@patch("builtins.open", new_callable=mock_open) # Patch builtins.open
def test_gdrive_authenticate_new_token(
    mock_open_func, mock_json_load, mock_input, mock_flow, mock_exists
):
    """Test the authentication process when no token exists."""
    # Configure mock_exists for the two calls: TOKEN_FILE (False), creds_path (True)
    mock_exists.side_effect = [False, True]

    # Configure mock_json_load for json.load(credentials.json)
    mock_json_load.return_value = {
        "installed": {"client_id": "test_id", "client_secret": "test_secret"}
    }

    mock_creds = MagicMock()
    mock_creds.to_json.return_value = "mock_json_token"  # Mock the to_json call
    mock_flow.return_value.run_local_server.return_value = mock_creds

    gdrive_authenticate()

    print(f"mock_exists calls: {mock_exists.call_args_list}")
    print(f"mock_input calls: {mock_input.call_args_list}")

    mock_exists.assert_has_calls([
        call("gdrive_token.json"),  # First call for TOKEN_FILE
        call("credentials.json"),   # Second call for creds_path
    ])
    mock_input.assert_called_once_with("Enter the path to your credentials.json file: ")
    mock_json_load.assert_called_once()
    mock_flow.assert_called_once_with(
        {"installed": {"client_id": "test_id", "client_secret": "test_secret"}},
        ["https://www.googleapis.com/auth/drive"],
    )
    mock_creds.to_json.assert_called_once()
    # Assert that open was called to write the token
    mock_open_func.assert_called_with("gdrive_token.json", "w")
    mock_open_func().write.assert_called_once_with("mock_json_token")

@patch("src.gdrive_auth.os.path.exists")
@patch("src.gdrive_auth.Credentials.from_authorized_user_info")
def test_gdrive_authenticate_existing_token(mock_creds_from_info, mock_exists):
    """Test the authentication process when a valid token already exists."""
    mock_exists.return_value = True
    mock_creds = MagicMock(valid=True)
    mock_creds_from_info.return_value = mock_creds
    
    with patch("builtins.open", new_callable=mock_open, read_data='{}'):
        gdrive_authenticate()
        mock_creds.refresh.assert_not_called()
