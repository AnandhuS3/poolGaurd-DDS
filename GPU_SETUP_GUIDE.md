# PoolGuard System: GPU Setup & Migration Guide

This guide provides the exact steps required to set up the Drowning Detection System (DDS) on a **new Windows/Linux system equipped with an NVIDIA GPU**. 

Following these steps ensures that PyTorch and YOLO models utilize your GPU for real-time inference instead of heavily taxing the CPU.

---

## 💻 Prerequisites & System Requirements

Before touching the codebase, strictly ensure the new system has these installed:

1. **Python:** Version 3.8 to 3.11. (Python 3.12+ might have dependency issues).
2. **Node.js:** Version 18+ (for running the React frontend).
3. **Flutter SDK:** Installed and added to system `PATH` (for the mobile app).
4. **PostgreSQL:** Version 14 or higher.

---

## 🎮 Step 1: NVIDIA GPU Environment Setup

To run deep learning models on a GPU, the underlying driver architecture must be set up properly.

1. **VGA Drivers:** Update your PC's display drivers using [NVIDIA GeForce Experience](https://www.nvidia.com/en-us/geforce/geforce-experience/).
2. **CUDA Toolkit:**
   * Download and install the **[CUDA Toolkit 11.8](https://developer.nvidia.com/cuda-11-8-0-download-archive)**.
   * *(Note: PyTorch 2.1.2 works exceptionally well with CUDA 11.8 or 12.1. We specify 11.8 here as it is highly stable).*
3. **cuDNN:**
   * Download the matching **[cuDNN library](https://developer.nvidia.com/cudnn)** for CUDA 11.x.
   * Extract the ZIP file and copy the contents of the `bin`, `include`, and `lib` folders directly into your CUDA installation directory (usually `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8`).

---

## 🗄️ Step 2: Database Initialization

The backend requires a PostgreSQL database to manage users, sessions, and alerts.

1. Open **pgAdmin 4** (installed with PostgreSQL) or psql command-line.
2. Create a new database:
   ```sql
   CREATE DATABASE poolguard_db;
   ```
3. Create a user (if you don't want to use the default `postgres` user) and grant privileges:
   ```sql
   CREATE USER postgres WITH ENCRYPTED PASSWORD 'root12';
   GRANT ALL PRIVILEGES ON DATABASE poolguard_db TO postgres;
   ```

---

## ⚙️ Step 3: Backend Setup (Python & PyTorch)

1. **Copy the Project**
   Transfer the complete `v5-poss` directory to the new system.
   
2. **Open Terminal inside `v5-poss` folder**

3. **Create and Activate a Virtual Environment**
   ```cmd
   python -m venv .venv
   .venv\Scripts\activate
   ```
   *(For Linux/Mac use: `source .venv/bin/activate`)*

4. **Install CUDA-Enabled PyTorch First (CRITICAL)**
   Do not just run `pip install -r requirements.txt`. You MUST install the PyTorch version that targets your specific GPU Toolkit first:
   ```cmd
   pip install torch==2.1.2 torchvision==0.16.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cu118
   ```

5. **Verify GPU Availability**
   Run the following in your terminal to ensure PyTorch sees the GPU:
   ```cmd
   python -c "import torch; print('CUDA Available:', torch.cuda.is_available())"
   ```
   *If this outputs `True`, your GPU is ready.*

6. **Install Remaining Dependencies**
   ```cmd
   pip install -r backend/config/requirements.txt
   ```

7. **Configure Environments (`.env`)**
   Inside the `backend/config/` directory:
   * Copy `.env.example` -> `.env`.
   * Open `.env` and fill out your PostgreSQL credentials (`DB_HOST`, `DB_USER`, `DB_PASSWORD`), and ensure the `FIREBASE_SA_PATH` exactly matches the absolute path to your Firebase service account JSON on the *new* system.

8. **Initialize the Database Schema**
   ```cmd
   python backend/database/init_database.py
   ```

9. **Start the Backend Server**
   ```cmd
   python backend/main.py
   ```
   *The server should now be running on `http://localhost:8000`.*

---

## 🌐 Step 4: Frontend (React) Setup

1. Open a new terminal inside `v5-poss/frontend`
2. Install npm modules:
   ```cmd
   npm install
   ```
3. Start the Web UI:
   ```cmd
   npm run dev
   ```

---

## 📱 Step 5: Mobile App (Flutter) Setup

1. Open a new terminal inside `v5-poss/mobile`
2. Download packages:
   ```cmd
   flutter pub get
   ```
3. Make sure to create a `.env` file inside the `mobile/` directory containing your backend IP:
   ```env
   API_BASE_URL=http://<YOUR_LOCAL_IP_ADDRESS>:8000
   ```
   *(Note: Find your local ID by typing `ipconfig` in the terminal and copying the IPv4 address. Do not use `localhost` if you are testing on a physical Android/iOS device!)*
4. Run the app:
   ```cmd
   flutter run
   ```

🎉 **You're fully operational on the new GPU machine!**
