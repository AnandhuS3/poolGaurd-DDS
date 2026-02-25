# 🔐 Credentials Setup Guide

## Quick Start

### 1. Copy the template file
```bash
cp .env.example .env
```

### 2. Edit `.env` and add your credentials

Open `.env` in a text editor and fill in:

```env
# Database
DB_USER=root
DB_PASSWORD=your_mysql_password

# Email (Get from https://myaccount.google.com/apppasswords)
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your_16_char_app_password

# Notification Recipients
NOTIFICATION_RECIPIENTS=guard1@example.com,guard2@example.com
```

### 3. That's it! Your credentials are now secure

The `.env` file is automatically:
- ✅ Excluded from Git (won't be committed)
- ✅ Loaded by the application automatically
- ✅ Separated from code for security

## 📧 Gmail App Password Setup

1. Go to: https://myaccount.google.com/apppasswords
2. Sign in to your Google account
3. Create a new app password:
   - Select app: **Mail**
   - Select device: **Other (Custom name)** → Type "Drowning Detection"
4. Click **Generate**
5. Copy the 16-character password (format: `xxxx xxxx xxxx xxxx`)
6. Paste into `.env` as `SMTP_PASSWORD` (remove spaces)

## 🔒 Security Best Practices

1. **NEVER commit `.env` to Git** (already in .gitignore)
2. **Keep `.env` file permissions restricted** (only you can read)
3. **Use different passwords for dev/production**
4. **Rotate passwords regularly** (every 3-6 months)
5. **If credentials leak, revoke immediately!**

## 🔄 Changing Credentials

Just update values in `.env` and restart the application:

```bash
# Edit .env
notepad .env

# Restart app
python app.py
```

## 👥 Team Setup

When sharing with team members:

1. **NEVER share your `.env` file**
2. Share `.env.example` instead
3. Each person creates their own `.env`
4. Each person uses their own Gmail app password

## ❓ Troubleshooting

**Problem**: "Credentials loaded from .env file" not showing

**Solution**: 
```bash
pip install python-dotenv
```

**Problem**: Empty passwords

**Solution**: Check `.env` file exists and has correct format (no quotes around values)

**Problem**: Gmail login fails

**Solution**: 
1. Enable 2-Step Verification on Google account
2. Generate new App Password
3. Use the 16-character password (no spaces)

## 📁 File Structure

```
v3/
├── .env                 ← Your actual credentials (NEVER commit!)
├── .env.example         ← Template (safe to commit)
├── credentials.py       ← Loads .env (auto-generated)
├── config.py           ← Imports from credentials.py
└── app.py              ← Uses config.py
```

## ✅ Verification

Test if credentials are loading:

```bash
python -c "import credentials; print('✅ Loaded:', credentials.SMTP_USERNAME)"
```

Should output:
```
✅ Credentials loaded from .env file
✅ Loaded: your-email@gmail.com
```
