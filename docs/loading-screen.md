# Consoul Loading Screen

## Overview

The Consoul loading screen provides a branded, animated startup experience that displays while the TUI initializes. It features custom animations matching the Consoul logo aesthetic with sound wave patterns.

## Features

- **Brand-aligned animations**: Sound wave pattern matching the Consoul logo
- **Multiple animation styles**: Matrix rain, binary wave, code stream, pulse, and sound wave
- **Progress tracking**: Optional progress bar with status messages
- **Smooth transitions**: Fade-in/fade-out effects
- **Configurable**: Control animation style and visibility via TuiConfig

## Architecture

### Modules

1. **`consoul/tui/animations.py`**
   - `AnimationStyle`: Enum of available animation styles
   - `BinaryAnimator`: Core animation engine generating frame data
   - Supports custom Consoul brand colors (Sky Blue #0085CC gradient)

2. **`consoul/tui/loading.py`**
   - `BinaryCanvas`: Widget that renders animations
   - `LoadingScreen`: Composable widget with message and progress
   - `ConsoulLoadingScreen`: Screen wrapper for use in Textual apps

### Configuration

Add to `TuiConfig` (already implemented in `consoul/tui/config.py`):

```python
# Loading Screen
show_loading_screen: bool = True
loading_animation_style: Literal["sound_wave", "matrix_rain", "binary_wave", "code_stream", "pulse"] = "sound_wave"
loading_show_progress: bool = True
```

## Integration Guide

### Option 1: Screen-based Integration (Recommended)

Show loading screen before pushing the main app screen:

```python
from consoul.tui.loading import ConsoulLoadingScreen
from consoul.tui.animations import AnimationStyle

class ConsoulApp(App):
    def on_mount(self) -> None:
        """Show loading screen during initialization."""
        if self.config.show_loading_screen:
            loading_screen = ConsoulLoadingScreen(
                animation_style=AnimationStyle[self.config.loading_animation_style.upper()],
                show_progress=self.config.loading_show_progress,
            )
            self.push_screen(loading_screen)
            self._perform_initialization(loading_screen)

    @work
    async def _perform_initialization(self, loading_screen: ConsoulLoadingScreen) -> None:
        """Perform async initialization with progress updates."""
        # Step 1: Initialize AI models
        loading_screen.update_progress("Loading AI models...", 25)
        await self._init_ai_models()

        # Step 2: Load conversation history
        loading_screen.update_progress("Loading conversation history...", 50)
        await self._load_conversations()

        # Step 3: Initialize tools
        loading_screen.update_progress("Initializing tools...", 75)
        await self._init_tools()

        # Step 4: Finalize
        loading_screen.update_progress("Ready!", 100)
        await asyncio.sleep(0.5)

        # Fade out and show main UI
        await loading_screen.fade_out(duration=1.0)
        self.pop_screen()
```

### Option 2: Inline Widget

Use `LoadingScreen` as a widget within existing layouts:

```python
from consoul.tui.loading import LoadingScreen

class MyContainer(Container):
    def compose(self) -> ComposeResult:
        yield LoadingScreen(
            message="Initializing...",
            style=AnimationStyle.SOUND_WAVE,
            show_progress=True
        )
```

## Animation Styles

### Sound Wave (Recommended - matches logo)
```python
AnimationStyle.SOUND_WAVE
```
Vertical bars animated like sound waveforms, echoing the Consoul logo design.

### Matrix Rain
```python
AnimationStyle.MATRIX_RAIN
```
Classic falling binary digits in Consoul brand colors.

### Binary Wave
```python
AnimationStyle.BINARY_WAVE
```
Sine wave pattern using binary characters.

### Code Stream
```python
AnimationStyle.CODE_STREAM
```
Horizontally scrolling Python code with syntax highlighting.

### Pulse
```python
AnimationStyle.PULSE
```
Pulsing binary pattern radiating from center.

## Example Usage

See `examples/test_loading_standalone.py` for a working demo:

```bash
cd ~/Development/github/goatbytes/consoul
python examples/test_loading_standalone.py
```

## TODO Integration Points

To fully integrate into `ConsoulApp`:

1. **Modify `ConsoulApp.on_mount()`** (`src/consoul/tui/app.py:561`)
   - Check `self.config.show_loading_screen`
   - Push `ConsoulLoadingScreen` before initialization
   - Move heavy initialization (AI model loading, tool registry, etc.) into async worker
   - Update progress during each initialization step
   - Fade out and pop screen when complete

2. **Add CLI flag** (`src/consoul/tui/cli.py`)
   ```python
   @click.option("--no-loading-screen", is_flag=True, help="Skip loading screen")
   ```

3. **Handle config file settings**
   - Respect `show_loading_screen` from user's config file
   - Allow override via CLI flag

## Color Scheme

The loading screen uses Consoul brand colors defined in `consoul/tui/themes.py`:

- **Primary (Sky Blue)**: `#0085CC`
- **Secondary (Deep Purple)**: `#44385E`
- **Background**: Dark theme default
- **Text**: White/Light gray for contrast

Animations automatically use these colors through the blue/purple color schemes.

## Performance Considerations

- Animations run at 30 FPS
- Minimal CPU usage (~1-2% on modern systems)
- No blocking operations during animation
- Smooth transitions using Textual's animation system

## Future Enhancements

- [ ] Add actual Consoul logo rendering (PNG/SVG to ASCII art)
- [ ] Custom animation combining logo + waveforms
- [ ] Particle effects for "Ready!" state
- [ ] Customizable messages per initialization step
- [ ] Accessibility: Option for static/minimal animation mode
