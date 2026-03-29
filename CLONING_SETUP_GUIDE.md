# Device Migration & Cloning Setup Guide

This guide explains how to properly set up the PoolGuard system after cloning the repository to a new computer. 

Since configuration files (like `.env`) and model weights are ignored by Git (to prevent leaking credentials or committing large files), you must recreate them on your new device.

---

## 1. Prerequisites
Ensure the new device has the following installed:
- Python 3.8+
- Node.js 18+
- PostgreSQL 14.0+
- Flutter SDK & Android Studio (if compiling the mobile app)
- Git

## 2. Backend Setup
The backend requires its `.env` file, database initialization, and missing model weights.

**Step 1. Virtual Environment**
Open a terminal in the project root:
```bash
python -m venv .venv
# Activate:
# Windows: .venv\Scripts\activate
# Mac/Linux: source .venv/bin/activate
pip install -r backend/config/requirements.txt
```

**Step 2. Model Weights**
Download or copy your model weights and place them into the `assets/weights` folder. You will need:
- `best.pt`
- `best1.pt`
- `yolov8n-pose.pt`

**Step 3. Database & Secrets (.env)**
1. Create a new file at `backend/config/.env`. You can copy `backend/config/.env.example` if it exists.
2. Fill in the required values. *Example:*
   ```env
   DB_USER=postgres
   DB_PASSWORD=your_password
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=poolguard_db
   JWT_SECRET_KEY=your_secure_string_here
   SMTP_USERNAME=your_gmail@gmail.com
   SMTP_PASSWORD=your_app_password
   ```
3. Copy your specific `firebase-sa.json` (Firebase Admin SDK key) file to `backend/config/` and ensure the `FIREBASE_SA_PATH` in `.env` points to its absolute path on the new machine.

**Step 4. Initialize Database**
Still in the activated virtual environment, run:
```bash
python backend/database/init_database.py
```

## 3. Frontend Setup
The web frontend needs its node modules.

```bash
cd frontend
npm install
npm run dev
```
*(Optionally configure `frontend/.env` if your backend isn't running on `localhost:8000`)*

## 4. Mobile App Setup
If you want to run the mobile app locally, it must know the local IP address of your new device so it can communicate with the backend.

**Step 1. Configure the Local IP in `.env`**
1. Find your machine's local IP address (run `ipconfig` on Windows or `ifconfig` on Mac/Linux).
2. Create `mobile/.env` and set the `API_BASE_URL` to your new machine's IP:
   ```env
   # Development (local machine / LAN)
   API_BASE_URL=http://<YOUR_NEW_LOCAL_IP>:8000
   ```

**Step 2. Add Firebase Config Files**
Git ignores Firebase configuration files. You need to copy these from your old device or download them from your Firebase Console.
- **Android:** Place `google-services.json` inside `mobile/android/app/`
- **iOS:** Place `GoogleService-Info.plist` inside `mobile/ios/Runner/`

**Step 3. Install packages & Run**
```bash
cd mobile
flutter clean
flutter pub get
flutter run
```

---

## 5. Testing the Setup
1. Launch your PostgreSQL server.
2. Run the root script `start_backend.bat` (or manually run `uvicorn main:app --reload` from inside `/backend`).
3. View the frontend at `http://localhost:5173`.
4. Launch the mobile app on a physical device or emulator. Ensure the backend and the device are on the same Wi-Fi network.
