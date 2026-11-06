# LinguaBridge – Language Translation Tool

A Flask web application with user registration/login, language selection, API-based translation, translation history, copy, and browser text-to-speech.

## Features
- User registration and login (passwords are securely hashed).
- Login using username or email.
- Translation between the languages listed in the dropdown.
- MyMemory translation API integration (no API key required for basic use).
- Recent translation history saved separately for each user.
- Copy translated text and listen using the browser's speech synthesis.
- Responsive interface.

## Requirements
- Python 3.9 or later
- Internet connection (required for translation API requests)

## Run on Windows

1. Extract the ZIP file.
2. Open Command Prompt in the extracted `language_translation_tool` folder.
3. Create and activate a virtual environment:

   ```bat
   python -m venv venv
   venv\Scripts\activate
   ```

4. Install dependencies:

   ```bat
   pip install -r requirements.txt
   ```

5. Start the application:

   ```bat
   python app.py
   ```

6. Open this address in your browser:

   `http://127.0.0.1:5000`

7. Select **Create account**, register, and then log in.

The SQLite database file (`translator.db`) is created automatically the first time the application starts.

## Translation API
This project calls the MyMemory endpoint:
`https://api.mymemory.translated.net/get`

The free service has usage limits and availability can vary. If the service is temporarily unavailable or rate-limits requests, wait and retry. Do not treat machine translation as certified/legal/medical translation.

## Important before deployment
- Set a strong random `SECRET_KEY` environment variable.
- Turn off Flask debug mode (`debug=False`).
- Use HTTPS and add CSRF protection before public deployment.
- Review the translation provider's current terms, limits, and privacy policy before handling sensitive text.
- The included SQLite database is intended for a student/local demonstration, not high-volume production use.
