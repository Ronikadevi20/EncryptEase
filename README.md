# EncryptEase Backend

This is the backend server for **EncryptEase**, a secure life management system that offers:
- Password Management
- Document Storage
- Bill Tracking
- AI-Powered Job Application Management
- User Settings and Security Enhancements

The backend is built using **Django** and **Django REST Framework (DRF)**, following a modular, scalable architecture.

---

## 📂 Project Structure

| Path | Description |
|-----|-------------|
| `applications/` | Handles job applications, resumes, cover letters, follow-up emails, interview sessions |
| `bills/` | Manages user bills, payment status, and receipts |
| `documents/` | Manages secure document storage, expiry alerts, and downloads |
| `passwords/` | Securely stores, categorizes, and manages user passwords |
| `settings_app/` | Manages user preferences (notifications, encryption settings, decoy mode) |
| `core/` | Project configuration, middleware, URL routing |
| `trash/` | all trash files logic |

---

## ⚙️ Requirements
create a .env file or in your settings.py add these three variables and keys if running locally
OPENROUTER_API_KEY =  '' 
OPENAI_API_KEY = ''
SECRET_KEY =''
Make sure you have:

- Python 3.10+
- pip
- virtualenv (recommended)

Install project dependencies:
cd /into the backend folder
```bash
pip install -r requirements.txt
python manage.py makemigrations 
python manage.py migarte
python manage.py runserver 
pip install dj-database-url