# PoolGuard Quick Reference

## Start Server

```bash
python app.py
# OR
start.bat
```

## Access Interface

```
http://localhost:8000
```

## Key Configuration (config.py)

| Parameter               | Default | Description                |
| ----------------------- | ------- | -------------------------- |
| `CONFIDENCE_THRESHOLD`  | 0.4     | Detection confidence (0-1) |
| `DROWNING_CLASS_ID`     | 1       | YOLO class for drowning    |
| `DROWNING_DURATION_SEC` | 5       | Seconds before alert       |
| `MAX_AGE`               | 30      | Max frames to keep track   |
| `JPEG_QUALITY`          | 85      | Streaming quality (1-100)  |

## Status Colors

- 🟢 **Green**: Person is safe
- 🟠 **Orange**: Warning - potential drowning detected
- 🔴 **Red**: Danger - drowning alert triggered

## API Endpoints

| Endpoint               | Method    | Purpose               |
| ---------------------- | --------- | --------------------- |
| `/`                    | GET       | Web interface         |
| `/analyze/upload`      | POST      | Upload video          |
| `/analyze/youtube`     | POST      | Download from YouTube |
| `/ws/process`          | WebSocket | Real-time processing  |
| `/download/{filename}` | GET       | Download result       |

## Troubleshooting

### No Detections

→ Lower `CONFIDENCE_THRESHOLD` in config.py

### IDs Keep Changing

→ Increase `N_INIT` in config.py

### Too Slow

→ Increase `FRAME_SKIP` or lower `JPEG_QUALITY`

### False Alerts

→ Increase `DROWNING_DURATION_SEC`

## File Structure

```
v3/
├── app.py              # Backend server
├── process_video.py    # Video processing
├── config.py           # Configuration
├── best.pt            # YOLO model
├── requirements.txt    # Dependencies
├── client/
│   └── index.html     # Frontend
├── uploads/           # Temp uploads
└── output/            # Results
```

## Dependencies

```bash
pip install -r requirements.txt
```

## Common Commands

**Install deps:**

```bash
pip install -r requirements.txt
```

**Check Python:**

```bash
python --version
```

**Test GPU:**

```bash
python -c "import torch; print(torch.cuda.is_available())"
```

**List packages:**

```bash
pip list
```

## Support Files

- `README.md` - Full documentation
- `TESTING.md` - Test procedures
- `.gitignore` - Git exclusions
- `start.bat` - Windows launcher

## Model Training

Your `best.pt` should detect:

- Class 0: Normal person
- Class 1: Drowning person

Retrain if needed using YOLOv8:

```bash
yolo train data=your_data.yaml model=yolov8n.pt epochs=100
```

## Performance Tips

1. Use GPU for 10x speed boost
2. Lower resolution for faster processing
3. Skip frames if real-time not critical
4. Adjust JPEG quality vs bandwidth
5. Close other heavy applications

## Security Notes

⚠️ For production:

- Enable authentication
- Use HTTPS
- Limit upload sizes
- Validate inputs
- Use reverse proxy
- Set CORS properly

## Contact

For issues, check:

1. Terminal logs
2. Browser console (F12)
3. README.md troubleshooting
4. Model performance
