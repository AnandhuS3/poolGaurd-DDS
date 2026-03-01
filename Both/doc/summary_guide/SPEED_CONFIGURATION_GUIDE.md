# 🎬 Video Analysis Speed Configuration Guide

## Current Setting: ✅ **REAL-TIME (1:1 Speed)**

The analysis speed has been configured to **match the original video speed** for maximum accuracy.

---

## ⚙️ **Configuration:**

**File:** `core/config.py` lines 68-69

```python
SKIP_FRAMES = 1  # Process every frame (matches video speed, most accurate)
JPEG_QUALITY = 85  # Higher quality for better visualization
```

---

## 📊 **Speed Options Explained:**

### **Current: SKIP_FRAMES = 1** (Real-Time)
- **Processes:** Every single frame
- **Speed:** Matches video playback (1:1 ratio)
- **Accuracy:** ✅ **Maximum** - No frames missed
- **CPU Usage:** ⚠️ **High** - Requires good hardware
- **Use Case:** Production, critical monitoring, maximum accuracy

**Example:** 30 FPS video → Processes 30 frames/second

---

### **Alternative: SKIP_FRAMES = 2** (Balanced)
- **Processes:** Every 2nd frame
- **Speed:** 2x faster than video
- **Accuracy:** ✅ **Very Good** - Minimal frames missed
- **CPU Usage:** ⚠️ **Medium**
- **Use Case:** Good balance of speed and accuracy

**Example:** 30 FPS video → Processes 15 frames/second

---

### **Alternative: SKIP_FRAMES = 3** (Fast)
- **Processes:** Every 3rd frame
- **Speed:** 3x faster than video
- **Accuracy:** ✅ **Good** - Some frames skipped
- **CPU Usage:** ✅ **Low**
- **Use Case:** Quick analysis, testing, older hardware

**Example:** 30 FPS video → Processes 10 frames/second

---

## 🎯 **Detection Thresholds (Frame-Based):**

With **SKIP_FRAMES = 1** (current setting):

| State | Frames Needed | Time @ 30 FPS | Time @ 60 FPS |
|-------|---------------|---------------|---------------|
| SAFE | 0-29 | 0-1s | 0-0.5s |
| WARNING | 30-59 | 1-2s | 0.5-1s |
| DANGER | 60+ | 2s+ | 1s+ |

**Note:** Thresholds are **frame-based**, not time-based, so they adapt to video FPS automatically!

---

## 🚀 **Performance Impact:**

### **SKIP_FRAMES = 1** (Current)
```
✅ Pros:
- Maximum accuracy
- No frames missed
- Best for production
- Smooth tracking

⚠️ Cons:
- Slower processing
- Higher CPU usage
- May lag on weak hardware
```

### **SKIP_FRAMES = 3** (Previous)
```
✅ Pros:
- 3x faster processing
- Lower CPU usage
- Works on older hardware
- Still good accuracy

⚠️ Cons:
- Skips 2 out of 3 frames
- May miss quick events
- Less smooth tracking
```

---

## 🔧 **How to Change Speed:**

### **Option 1: Edit Config File**

1. Open `core/config.py`
2. Find line 68: `SKIP_FRAMES = 1`
3. Change to desired value:
   - `SKIP_FRAMES = 1` → Real-time (current)
   - `SKIP_FRAMES = 2` → 2x faster
   - `SKIP_FRAMES = 3` → 3x faster
4. Save file
5. Restart server: `python main.py`

---

### **Option 2: Quick Presets**

#### **Preset A: Maximum Accuracy (Current)**
```python
SKIP_FRAMES = 1
JPEG_QUALITY = 85
USE_MOTION_DETECTION = True
```
**Best for:** Production, critical monitoring

---

#### **Preset B: Balanced Performance**
```python
SKIP_FRAMES = 2
JPEG_QUALITY = 80
USE_MOTION_DETECTION = True
```
**Best for:** General use, good hardware

---

#### **Preset C: Fast Processing**
```python
SKIP_FRAMES = 3
JPEG_QUALITY = 75
USE_MOTION_DETECTION = True
```
**Best for:** Testing, older hardware, quick analysis

---

## 📈 **Performance Monitoring:**

The UI shows real-time performance metrics:

```
Processing Speed: 28.5 FPS (0.95x)
```

**What it means:**
- **FPS:** Frames processed per second
- **Ratio:** Speed compared to video FPS
  - `1.0x` = Matches video speed ✅
  - `< 1.0x` = Slower than video ⚠️
  - `> 1.0x` = Faster than video 🚀

---

## 🎬 **Video Playback vs Analysis:**

### **How It Works:**

The system uses **dual-stream processing**:

1. **Video Player:** Plays at native speed (30 FPS)
2. **AI Analysis:** Processes frames based on SKIP_FRAMES
3. **Synchronization:** Analysis frames overlay on video

**With SKIP_FRAMES = 1:**
- Video plays at 30 FPS
- AI processes at 30 FPS
- **Perfect sync!** ✅

**With SKIP_FRAMES = 3:**
- Video plays at 30 FPS
- AI processes at 10 FPS
- Analysis finishes 3x faster than video

---

## 💡 **Smart Motion Detection:**

Even with `SKIP_FRAMES = 1`, the system has **smart optimization**:

```python
USE_MOTION_DETECTION = True  # Enabled by default
MOTION_THRESHOLD = 1500
```

**How it works:**
- Detects motion between frames
- If motion < threshold → Reuses previous detection
- Saves CPU without skipping frames
- **Automatic optimization!** 🚀

---

## 🧪 **Testing Different Speeds:**

### **Test 1: Check Current Speed**
1. Upload a video
2. Watch the performance metrics
3. Look for: `Processing Speed: X FPS (Y.Yx)`

### **Test 2: Compare Accuracy**
1. Test with `SKIP_FRAMES = 1` (every frame)
2. Test with `SKIP_FRAMES = 3` (every 3rd frame)
3. Compare detection results

### **Test 3: Measure CPU Usage**
- Open Task Manager
- Watch CPU usage during analysis
- Adjust SKIP_FRAMES if too high

---

## ⚠️ **Troubleshooting:**

### **Analysis is slower than video:**
```
Processing Speed: 15 FPS (0.5x)
```
**Solutions:**
1. Increase `SKIP_FRAMES` to 2 or 3
2. Reduce `JPEG_QUALITY` to 70-75
3. Close other applications
4. Use GPU acceleration (if available)

---

### **Analysis is too fast:**
```
Processing Speed: 90 FPS (3.0x)
```
**Solutions:**
1. Decrease `SKIP_FRAMES` to 1
2. Increase `JPEG_QUALITY` to 85-95
3. This is actually good! Means your hardware is powerful

---

### **Choppy video playback:**
**Cause:** CPU overloaded
**Solutions:**
1. Increase `SKIP_FRAMES` to 2 or 3
2. Reduce `JPEG_QUALITY`
3. Disable `USE_MOTION_DETECTION` (not recommended)

---

## 📊 **Recommended Settings by Hardware:**

### **High-End PC (GPU Available):**
```python
SKIP_FRAMES = 1
JPEG_QUALITY = 95
USE_MOTION_DETECTION = True
```

### **Mid-Range PC:**
```python
SKIP_FRAMES = 1  # or 2
JPEG_QUALITY = 85
USE_MOTION_DETECTION = True
```

### **Low-End PC / Laptop:**
```python
SKIP_FRAMES = 3
JPEG_QUALITY = 70
USE_MOTION_DETECTION = True
```

---

## 🎯 **Current Configuration Summary:**

✅ **SKIP_FRAMES:** 1 (Process every frame)  
✅ **JPEG_QUALITY:** 85 (High quality)  
✅ **USE_MOTION_DETECTION:** True (Smart optimization)  
✅ **MOTION_THRESHOLD:** 1500  

**Result:** Analysis matches video speed with maximum accuracy!

---

## 🔄 **To Apply Changes:**

After editing `config.py`:

```bash
# Stop server (Ctrl+C)
python main.py
```

Or use the auto-restart command:
```bash
# Windows PowerShell
Stop-Process -Name python -Force; python main.py
```

---

## 📝 **Notes:**

- **Frame-based thresholds** automatically adapt to video FPS
- **Motion detection** provides automatic optimization
- **JPEG_QUALITY** affects encoding speed, not detection accuracy
- **SKIP_FRAMES** affects detection accuracy and CPU usage

---

**Status:** ✅ **Configured for real-time analysis (1:1 speed)**  
**Next:** Restart server and test with video upload!
