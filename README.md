# 🏊 PoolGuard - Drowning Detection System

**AI-powered real-time drowning detection with multi-person tracking, automated alerts, and role-based access control.**

---

## 🎯 GOAL

PoolGuard is a production-ready drowning detection system designed to enhance pool safety through:

- **Real-time Monitoring**: Continuous video analysis with YOLO object detection and DeepSORT tracking
- **Intelligent Alerts**: Multi-channel notifications (Email/SMS/WhatsApp) with configurable thresholds
- **Multi-Person Tracking**: Simultaneous tracking with color-coded status indicators (🟢 Safe, 🟠 Warning, 🔴 Danger)
- **User Management**: Role-based access (Admin/Guard/User) with JWT authentication
- **Global Support**: International phone validation (E.164), timezone configuration, region-agnostic deployment
- **Flexible Input**: Upload videos or analyze YouTube URLs in real-time

---

## ⚙️ HOW IT WORKS

### Architecture Overview

```
User Upload → WebSocket Connection → Frame Processing → Alert System
                                           ↓
                            YOLO Detection + DeepSORT Tracking
                                           ↓
                            State Analysis (Safe/Warning/Danger)
                                           ↓
                            Real-time Stream + Notifications
```

### Processing Pipeline

1. **Video Ingestion**: User uploads video or provides YouTube URL via web interface
2. **Frame Analysis**: Each frame processed through:
   - YOLO model for person detection (configurable confidence threshold)
   - DeepSORT for persistent ID tracking across frames
   - Position-based drowning detection with motion analysis
3. **State Management**: Track person states with frame-based timing:
   - Safe: Normal swimming behavior
   - Warning: Reduced motion detected (configurable duration)
   - Danger: Prolonged submersion triggers alert
4. **Alert Dispatch**: Automated notifications to registered users via configured channels
5. **Live Streaming**: Annotated frames streamed to frontend via WebSocket with bounding boxes

### Key Components

- **Backend**: FastAPI server (`core/app.py`) with WebSocket support
- **Detection Engine**: YOLO + DeepSORT (`core/process_video.py`)
- **Database**: MySQL for user management and alert logging
- **Frontend**: HTML/CSS/JS with real-time canvas rendering
- **Configuration**: Environment-based settings (`config/.env`)

---

## 🚀 EXECUTION GUIDE

### Prerequisites

- Python 3.8+
- MySQL 8.0+
- YOLO model weights (`weights/best.pt`)
- GPU recommended (CUDA-compatible) for optimal performance

### Installation

1. **Navigate to project directory**:
   ```bash
   cd c:\Users\Anandhu\Desktop\poj\ARk_2\mini_project\DDS\v4
   ```

2. **Install dependencies**:
   ```bash
   pip install -r config/requirements.txt
   ```

3. **Configure environment**:
   - Copy `config/.env.example` to `config/.env`
   - Update database credentials, SMTP settings, timezone, etc.

4. **Setup database**:
   - Create MySQL database (name specified in `.env`)
   - Tables auto-created on first run

5. **Place YOLO model**:
   - Ensure trained model exists at `weights/best.pt`

### Running the System

**Start the server**:
```bash
python main.py
```

**Access points**:
- Main Interface: `http://localhost:5000`
- Login: `http://localhost:5000/login`
- Register: `http://localhost:5000/register`
- Admin Panel: `http://localhost:5000/admin.html`

**Default credentials** (⚠️ CHANGE IMMEDIATELY):
- Username: `admin@dds.local`
- Password: `admin123`

### Using the System

1. **Register/Login**: Create account or use admin credentials
2. **Upload Video**: Choose file or paste YouTube URL
3. **Start Analysis**: Click "Start Analysis" to begin processing
4. **Monitor**: View live feed with bounding boxes and status indicators
5. **Alerts**: Registered users receive notifications on drowning detection
6. **Admin Functions**: Manage users, view logs, configure settings

### Configuration

**Detection parameters** (`core/config.py`):
- `CONFIDENCE_THRESHOLD`: YOLO detection confidence (default: 0.4)
- `WARNING_DURATION`: Frames before warning state (default: 90)
- `DANGER_DURATION`: Frames before danger alert (default: 150)
- `MOTION_THRESHOLD`: Movement detection sensitivity

**Tracking parameters**:
- `MAX_AGE`: Frames to keep track alive (default: 30)
- `N_INIT`: Frames to confirm track (default: 3)

### Project Structure

```
v4/
├── main.py                 # Entry point
├── core/                   # Core application logic
│   ├── app.py             # FastAPI server
│   ├── process_video.py   # Detection & tracking
│   └── config.py          # Configuration
├── config/                 # Environment & dependencies
│   ├── .env               # Environment variables
│   └── requirements.txt   # Python packages
├── database/              # Database models & migrations
├── frontend/              # HTML/CSS/JS interfaces
├── weights/               # YOLO model files
├── uploads/               # Temporary video storage
├── dlogs/                 # Application logs
└── doc/                   # Documentation
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Import errors | `pip install -r config/requirements.txt --upgrade` |
| Database connection failed | Verify MySQL running, check `.env` credentials |
| Model not found | Ensure `weights/best.pt` exists |
| Slow processing | Enable GPU, reduce video resolution, adjust frame skip |
| WebSocket errors | Check port availability, firewall settings |

### API Endpoints

- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User authentication
- `POST /api/video/upload` - Upload video file
- `POST /api/video/youtube` - Process YouTube URL
- `WS /ws/video/{session_id}` - WebSocket video stream
- `GET /api/alerts` - Retrieve alert history

---

## 📝 Additional Resources

- **Speed Configuration**: See `doc/summary_guide/SPEED_CONFIGURATION_GUIDE.md`
- **Refactoring Summary**: See `doc/summary_guide/REFACTORING_SUMMARY.md`
- **Logs**: Check `dlogs/` for error tracking

## 👏 Built With

FastAPI • YOLO (Ultralytics) • DeepSORT • OpenCV • MySQL • WebSockets
