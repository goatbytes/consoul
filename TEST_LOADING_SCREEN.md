# Testing the Consoul Loading Screen

## Quick Test (Interactive)

Run the standalone test application:

```bash
cd ~/Development/github/goatbytes/consoul
poetry run python examples/test_loading_standalone.py
```

This will show an interactive menu with 5 animation styles:
1. **Sound Wave (Logo Style)** - Recommended! Matches the Consoul logo
2. **Matrix Rain** - Classic binary rain effect
3. **Binary Wave** - Sine wave patterns
4. **Code Stream** - Scrolling Python code
5. **Pulse** - Pulsing binary from center

Click any button to see the loading animation with:
- Animated background
- "CONSOUL" ASCII logo
- Progress bar with status messages
- Smooth fade-out transition

Press `q` to quit.

## Testing Each Animation

### 1. Sound Wave (Primary - Logo Style)
```bash
cd ~/Development/github/goatbytes/consoul
poetry run python -c "
from consoul.tui.loading import ConsoulLoadingScreen
from consoul.tui.animations import AnimationStyle
from textual.app import App

class TestApp(App):
    def on_mount(self):
        screen = ConsoulLoadingScreen(
            animation_style=AnimationStyle.SOUND_WAVE,
            show_progress=True
        )
        self.push_screen(screen)

TestApp().run()
"
```

### 2. Matrix Rain
Change `AnimationStyle.SOUND_WAVE` to `AnimationStyle.MATRIX_RAIN`

### 3. Binary Wave
Change to `AnimationStyle.BINARY_WAVE`

### 4. Code Stream
Change to `AnimationStyle.CODE_STREAM`

### 5. Pulse
Change to `AnimationStyle.PULSE`

## What to Look For

✅ **Animation smoothness**: Should run at ~30 FPS without stuttering
✅ **Colors**: Blue gradient (#0085CC) matching Consoul brand
✅ **ASCII logo**: "CONSOUL" text should be visible and centered
✅ **Progress bar**: Shows percentage and fills from left to right
✅ **Messages**: Status text updates ("Initializing...", "Loading...", etc.)
✅ **Fade-out**: Smooth opacity transition when complete
✅ **CPU usage**: Should be minimal (<5% on modern systems)

## Expected Behavior

1. App starts showing the animation selector
2. Click a button to launch loading screen
3. Loading screen appears with:
   - Animated background
   - CONSOUL logo in center
   - "Initializing Consoul..." message
   - Progress bar at bottom
4. Progress updates every 1 second (20% → 40% → 60% → 80% → 100%)
5. Shows "Ready!" at 100%
6. Fades out smoothly over 1 second
7. Returns to animation selector

## Terminal Requirements

- **Color support**: 256-color terminal recommended
- **Font**: Monospace font with Unicode support
- **Size**: At least 80x24 characters

## Troubleshooting

### Import errors
```bash
cd ~/Development/github/goatbytes/consoul
poetry install
```

### Animation not smooth
- Check CPU usage
- Try a different terminal emulator
- Reduce animation complexity (use PULSE instead of SOUND_WAVE)

### Colors look wrong
- Ensure your terminal supports 256 colors
- Try: `export TERM=xterm-256color`

## Integration Test

To test with the full Consoul app (requires all dependencies):

```bash
cd ~/Development/github/goatbytes/consoul
poetry install
poetry run consoul
```

Then modify `src/consoul/tui/app.py` to show the loading screen on startup (see `docs/loading-screen.md` for integration instructions).

## Performance Benchmarks

Expected performance on modern hardware:
- **CPU**: 1-2% while animating
- **Memory**: <10MB for loading screen widget
- **Startup time**: <100ms to render first frame
- **Frame rate**: 30 FPS consistently

## Visual Comparison

### Sound Wave (Recommended)
```
║  ║    ║  ║    ║  ║    ║  ║
║  ║    ║  ║    ║  ║    ║  ║
Vertical bars pulsing like waveforms
```

### Matrix Rain
```
1 0 1 0 1
  1 0 1 0
0 1 0 1 1
Binary digits falling down
```

### Binary Wave
```
~~~~~
   ~~~~~
      ~~~~~
Sine wave made of 0s and 1s
```

### Code Stream
```
from consoul import Consoul →
console.chat('Hello!') →
Python code scrolling left
```

### Pulse
```
    0 1 0
  1 0 1 0 1
    0 1 0
Expanding binary pattern
```

## Success Criteria

- ✅ All 5 animation styles work
- ✅ Colors use Consoul brand palette
- ✅ Progress bar updates smoothly
- ✅ Fade transitions are smooth
- ✅ No errors or crashes
- ✅ Runs on macOS/Linux/Windows terminals

## Next Steps

After testing, integrate into ConsoulApp:
1. See `docs/loading-screen.md` for integration guide
2. Add to `on_mount()` in `src/consoul/tui/app.py`
3. Test with real initialization tasks
4. Add CLI flag `--no-loading-screen` for quick startup
