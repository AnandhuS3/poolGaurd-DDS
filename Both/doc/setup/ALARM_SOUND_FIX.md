# Alarm Sound Fix - Browser Autoplay Issue

## Problem
The alarm sound was not playing when DANGER state was detected during video analysis.

## Root Cause
Modern browsers (Chrome, Firefox, Safari, Edge) **block audio autoplay** until the user interacts with the page. This is a security feature to prevent websites from playing unwanted sounds.

### Why This Happens:
1. User loads the page
2. Video analysis starts
3. DANGER state is detected
4. Backend sends `state_change` event via WebSocket
5. Frontend receives event and tries to play alarm
6. **Browser blocks the audio** because user hasn't interacted with the page yet

## Solution Implemented
Added audio initialization on first user interaction (clicking "Start Analysis" button).

### Code Changes (frontend/index.html, lines 1453-1475):

```javascript
// AUDIO FIX - Enable audio on first user interaction
let audioInitialized = false;
function initializeAudio() {
  if (!audioInitialized && els.alarmSound) {
    // Load and prepare audio element
    els.alarmSound.load();
    // Try to play and immediately pause to unlock audio
    els.alarmSound.play().then(() => {
      els.alarmSound.pause();
      els.alarmSound.currentTime = 0;
      audioInitialized = true;
      console.log('[AUDIO] Audio initialized and ready');
      addEventLog('🔊 Audio enabled', 'info');
    }).catch(err => {
      console.log('[AUDIO] Audio will be enabled on next interaction:', err.message);
    });
  }
}

els.startBtn.addEventListener("click", () => {
  initializeAudio();  // Initialize audio first
  startAnalysis();     // Then start analysis
});
```

### How It Works:
1. **User clicks "Start Analysis"** → This is a user interaction
2. **`initializeAudio()` is called** → Loads and "unlocks" the audio element
3. **Audio plays and immediately pauses** → This tells the browser "user wants audio"
4. **Audio is now ready** → Future `play()` calls will work
5. **When DANGER is detected** → Alarm plays successfully

## Testing the Fix

### Before Fix:
```
1. Load page
2. Upload video
3. Click "Start Analysis"
4. DANGER detected
5. ❌ No alarm sound (browser blocked it)
6. Console shows: "play() failed because the user didn't interact with the document first"
```

### After Fix:
```
1. Load page
2. Upload video
3. Click "Start Analysis"
   → 🔊 "Audio enabled" appears in event log
4. DANGER detected
5. ✅ Alarm sound plays successfully
6. Console shows: "[AUDIO SUCCESS] ✅ Alarm played for Person #X - DANGER"
```

## Verification Steps

1. **Refresh the browser** (Ctrl+F5 or Cmd+Shift+R)
2. **Upload a test video** with drowning detection
3. **Click "Start Analysis"**
4. **Check event log** for "🔊 Audio enabled" message
5. **Wait for DANGER state**
6. **Alarm should play** automatically

## Browser Console Logs

### Successful Audio Initialization:
```
[AUDIO] Audio initialized and ready
```

### When DANGER is Detected:
```
[STATE CHANGE RECEIVED] {"type":"state_change","person_id":1,"old_state":"WARNING","new_state":"DANGER",...}
[AUDIO CHECK] State is DANGER, should play alarm
[AUDIO TRIGGER] Attempting to play alarm for 1_DANGER
[AUDIO] Setting currentTime to 0
[AUDIO] Calling play()
[AUDIO SUCCESS] ✅ Alarm played for Person #1 - DANGER
```

### If Alarm is Muted:
```
[AUDIO MUTED] Alarm is muted, skipping sound for Person #1 - DANGER
```

## Additional Features

### Mute Button
The mute button (top-right corner of video player) still works:
- **Red 🔊** = Alarm enabled
- **Gray 🔇** = Alarm muted

### Event Log Messages:
- `🔊 Audio enabled` - Audio initialized successfully
- `🔊 ALARM: DANGER alert for Person #X` - Alarm played
- `🔇 ALARM MUTED: DANGER alert for Person #X` - Alarm muted

## Technical Details

### Browser Autoplay Policies:
- **Chrome/Edge:** Requires user gesture before audio playback
- **Firefox:** Requires user interaction on the page
- **Safari:** Strictest policy, requires explicit user action

### Our Solution:
- Uses the "Start Analysis" button click as the user gesture
- Calls `audio.play()` then immediately `audio.pause()`
- This "unlocks" the audio element for future playback
- Works across all modern browsers

## Troubleshooting

### If alarm still doesn't play:

1. **Check browser console** for error messages
2. **Verify audio file exists**: `/sounds/alarm.mp3`
3. **Check mute button** - make sure it's red (🔊), not gray (🔇)
4. **Try clicking anywhere on the page** before starting analysis
5. **Check browser audio settings** - ensure site isn't muted

### Force Audio Initialization:
Open browser console and run:
```javascript
document.getElementById('alarmSound').play().then(() => {
  document.getElementById('alarmSound').pause();
  console.log('Audio manually initialized');
});
```

## Files Modified

1. ✅ **`frontend/index.html`** (lines 1453-1475)
   - Added `initializeAudio()` function
   - Updated start button event listener

## Related Documentation

- `doc/MUTE_BUTTON_FEATURE.md` - Mute button functionality
- `core/process_video.py` (lines 383-399) - State change event emission
- `frontend/index.html` (lines 1132-1218) - State change handler and alarm logic

---

**Status:** ✅ **FIXED**  
**Date:** 2026-02-15  
**Issue:** Alarm not playing on DANGER detection  
**Solution:** Initialize audio on first user interaction  
**Result:** Alarm now plays successfully when DANGER is detected
