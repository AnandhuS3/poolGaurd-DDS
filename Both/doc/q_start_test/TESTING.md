# Testing Guide for PoolGuard

## Pre-Testing Checklist

- [ ] Python 3.8+ installed
- [ ] All dependencies installed (`pip install -r requirements.txt`)
- [ ] `best.pt` model file in root directory
- [ ] Port 8000 is available

## Quick Start Test

1. **Run the startup script**:

   ```bash
   # Windows
   start.bat

   # Or manually
   python app.py
   ```

2. **Verify server started**:

   - You should see: `Server starting at: http://0.0.0.0:8000`
   - No error messages

3. **Open browser**:
   - Navigate to `http://localhost:8000`
   - You should see the PoolGuard interface

## Test Cases

### Test 1: Video Upload

1. Click "Choose File"
2. Select a video file (MP4, AVI, etc.)
3. Click "Start Analysis"
4. **Expected**:
   - Status changes to "Uploading..." then "Processing..."
   - Video frames appear on canvas with bounding boxes
   - Person count updates in sidebar

### Test 2: YouTube URL

1. Paste a YouTube URL in the text field
2. Click "Start Analysis"
3. **Expected**:
   - Video downloads
   - Processing begins automatically
   - Same behavior as uploaded video

### Test 3: Real-time Tracking

**Monitor these elements during processing:**

- [ ] Bounding boxes appear around detected persons
- [ ] Each person has a unique ID
- [ ] IDs persist across frames (not changing rapidly)
- [ ] Status colors change based on detection:
  - Green = Safe
  - Orange = Warning
  - Red = Danger

### Test 4: Sidebar Updates

**Check that sidebar shows:**

- [ ] Total persons detected
- [ ] Drowning alerts count
- [ ] List of tracked persons with IDs
- [ ] Event log with timestamps

### Test 5: Controls

1. **Stop Button**:

   - Click "Stop" during processing
   - Video should pause
   - Status shows "Stopped"

2. **Reset Button**:
   - Click "Reset"
   - Canvas clears
   - All counts reset to 0
   - Event log clears

### Test 6: Multiple Persons

Use a video with multiple people:

- [ ] All persons get unique IDs
- [ ] Each person tracked independently
- [ ] No ID swapping between persons

### Test 7: Drowning Detection

**If using a video with drowning scenarios:**

- [ ] System detects drowning posture
- [ ] Status changes from "safe" to "warning" to "danger"
- [ ] Alert appears in event log
- [ ] Bounding box turns red

## Performance Tests

### Test 8: Video Quality

Try videos with different resolutions:

- [ ] 480p: Should process smoothly
- [ ] 720p: Good performance
- [ ] 1080p: May be slower but functional

### Test 9: Long Videos

Test with a 5-10 minute video:

- [ ] Processing continues without crashes
- [ ] Memory usage stays reasonable
- [ ] WebSocket connection remains stable

### Test 10: Error Handling

1. **No file selected**:

   - Click "Start Analysis" without selecting file
   - **Expected**: Error message

2. **Invalid file**:

   - Try uploading a non-video file
   - **Expected**: Error message

3. **Network disconnect**:
   - Start processing, then disable network
   - **Expected**: Connection error message

## Browser Compatibility

Test in multiple browsers:

- [ ] Chrome/Edge (Chromium)
- [ ] Firefox
- [ ] Safari (if on Mac)

## Common Issues & Solutions

### Issue: Video not processing

**Check:**

- Is `best.pt` file present?
- Are dependencies installed?
- Any error in terminal/console?

### Issue: No bounding boxes

**Possible causes:**

- Model confidence too high (lower in config.py)
- Video has no persons
- Model not trained properly

### Issue: IDs keep changing

**Solution:**

- Adjust DeepSORT parameters in config.py
- Increase `n_init` for stricter tracking
- Adjust `max_cosine_distance`

### Issue: Slow processing

**Solutions:**

- Use GPU if available
- Lower video resolution
- Increase `FRAME_SKIP` in config.py
- Reduce `JPEG_QUALITY` in config.py

### Issue: WebSocket disconnects

**Check:**

- Server is still running
- No timeout errors in console
- Firewall not blocking WebSocket

## Performance Metrics

Expected performance (with GPU):

- **480p**: 30+ FPS
- **720p**: 20-25 FPS
- **1080p**: 10-15 FPS

Expected performance (CPU only):

- **480p**: 5-10 FPS
- **720p**: 2-5 FPS
- **1080p**: 1-3 FPS

## Logging

Check terminal output for:

- Frame processing times
- Detection counts
- Tracking updates
- Error messages

## Success Criteria

✅ System is working correctly if:

1. Videos process without crashes
2. Bounding boxes appear and track persons
3. IDs remain consistent (mostly)
4. Sidebar updates in real-time
5. Alerts trigger when configured
6. No memory leaks during long processing

## Report Issues

If tests fail, collect:

1. Error messages from terminal
2. Browser console errors (F12)
3. Video specifications (resolution, codec)
4. Python version and OS
5. GPU info (if using)

## Next Steps

After successful testing:

1. Test with your actual pool videos
2. Adjust detection thresholds in config.py
3. Fine-tune DeepSORT parameters
4. Consider training model with more data
5. Deploy to production server
