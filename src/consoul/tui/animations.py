"""Binary animation generators for Consoul loading screens.

This module provides various animation styles for the Consoul loading screen,
featuring brand-colored waveforms and binary patterns.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum

__all__ = ["AnimationStyle", "BinaryAnimator"]


class AnimationStyle(str, Enum):
    """Available animation styles for the Consoul loading screen."""

    SOUND_WAVE = "sound_wave"  # Primary - matches logo
    MATRIX_RAIN = "matrix_rain"
    BINARY_WAVE = "binary_wave"
    CODE_STREAM = "code_stream"
    PULSE = "pulse"


@dataclass
class BinaryColumn:
    """Represents a column of falling binary digits."""

    x: int
    y: float
    speed: float
    length: int
    chars: list[str]


@dataclass
class CodeSnippet:
    """Represents a scrolling code snippet."""

    x: float
    y: int
    text: str
    speed: float
    syntax_colors: list[str]


@dataclass
class WaveformColumn:
    """Represents a sound wave column for the logo animation."""

    x: int
    amplitude: float
    phase: float
    speed: float


class BinaryAnimator:
    """Generates binary-themed animation frames for Consoul."""

    def __init__(
        self,
        width: int,
        height: int,
        style: AnimationStyle = AnimationStyle.SOUND_WAVE,
    ) -> None:
        """Initialize the binary animator.

        Args:
            width: Width of the animation area
            height: Height of the animation area
            style: Animation style to use
        """
        self.width = width
        self.height = height
        self.style = style
        self.frame = 0
        self._columns: list[BinaryColumn] = []
        self._code_snippets: list[CodeSnippet] = []
        self._waveform_columns: list[WaveformColumn] = []
        self._initialize_animation()

    def _initialize_animation(self) -> None:
        """Initialize animation-specific data structures."""
        if self.style == AnimationStyle.MATRIX_RAIN:
            self._initialize_matrix_rain()
        elif self.style == AnimationStyle.CODE_STREAM:
            self._initialize_code_stream()
        elif self.style == AnimationStyle.SOUND_WAVE:
            self._initialize_sound_wave()

    def _initialize_matrix_rain(self) -> None:
        """Initialize columns for matrix rain effect."""
        num_columns = max(1, self.width // 2)
        for i in range(num_columns):
            self._columns.append(
                BinaryColumn(
                    x=i * 2,
                    y=random.uniform(-self.height, 0),
                    speed=random.uniform(0.3, 1.5),
                    length=random.randint(5, 15),
                    chars=[random.choice(["0", "1"]) for _ in range(15)],
                )
            )

    def _initialize_sound_wave(self) -> None:
        """Initialize waveform columns matching the logo aesthetic."""
        num_columns = max(1, self.width // 2)
        for i in range(num_columns):
            self._waveform_columns.append(
                WaveformColumn(
                    x=i * 2,
                    amplitude=random.uniform(3, 8),
                    phase=random.uniform(0, 2 * math.pi),
                    speed=random.uniform(0.05, 0.15),
                )
            )

    def _get_syntax_colors(self, code: str) -> list[str]:
        """Generate syntax highlighting colors for code.

        Args:
            code: Code string to highlight

        Returns:
            List of color codes (one per character)
        """
        colors = []
        keywords = {
            "def",
            "class",
            "import",
            "from",
            "return",
            "if",
            "else",
            "for",
            "while",
            "in",
            "with",
            "as",
            "async",
            "await",
            "lambda",
            "try",
            "except",
            "match",
            "case",
        }

        i = 0
        while i < len(code):
            char = code[i]

            # Comments (including emojis and branding)
            if char == "#":
                # Color entire comment in green
                while i < len(code):
                    colors.append("#28A745")  # Green for comments
                    i += 1
                break

            # String literals
            if char in ('"', "'"):
                quote = char
                colors.append("#0085CC")  # Consoul blue for strings
                i += 1
                while i < len(code) and code[i] != quote:
                    colors.append("#0085CC")
                    i += 1
                if i < len(code):
                    colors.append("#0085CC")
                    i += 1
                continue

            # Numbers
            if char.isdigit():
                colors.append("#44385E")  # Purple for numbers
                i += 1
                while i < len(code) and (code[i].isdigit() or code[i] == "."):
                    colors.append("#44385E")
                    i += 1
                continue

            # Keywords
            if char.isalpha() or char == "_":
                word_start = i
                while i < len(code) and (code[i].isalnum() or code[i] == "_"):
                    i += 1
                word = code[word_start:i]

                color = "#0085CC" if word in keywords else "#FFFFFF"

                for _ in range(len(word)):
                    colors.append(color)
                continue

            # Default
            colors.append("#FFFFFF")
            i += 1

        return colors

    def _initialize_code_stream(self) -> None:
        """Initialize code snippets for horizontal scrolling effect."""
        # Massive pool of inspiring, branded code samples showcasing real AI capabilities
        code_samples = [
            # === CONSOUL SDK - Simple & Powerful ===
            "from consoul import Consoul",
            "console = Consoul()",
            "response = consoul.chat('Explain quantum computing in 3 sentences')",
            "console = Consoul(model='claude-3-5-sonnet', temperature=0.7)",
            "answer = console.ask('What is love?', show_tokens=True)",
            "from consoul.tui import ConsoulApp; app = ConsoulApp().run()",
            # === INSPIRING AI USE CASES ===
            "# AI that understands your codebase",
            "consoul.chat('Refactor this function for better performance')",
            "consoul.chat('Find security vulnerabilities in auth.py')",
            "consoul.chat('Generate unit tests for my API endpoints')",
            "consoul.chat('Explain this error and suggest a fix', attach='screenshot.png')",
            "consoul.chat('Translate this app to Spanish while preserving UX')",
            # === REAL-TIME STREAMING ===
            "async for token in model.astream('Write a sci-fi story'): print(token, end='')",
            "for chunk in stream_response(model, messages): yield chunk",
            "with Live(console) as live: live.update(streaming_markdown)",
            "# Watch AI think in real-time",
            # === MULTIMODAL MAGIC ===
            "image = analyze_image('diagram.png', 'Explain this architecture')",
            "response = chat_with_vision(prompt, image_path='ui_mockup.jpg')",
            "consoul.chat('What does this graph tell us?', attach='metrics.png')",
            "# AI that sees what you see",
            # === TOOL-AUGMENTED AI ===
            "console = Consoul(tools=True)  # AI with superpowers",
            "consoul.chat('Search the web for latest Python 3.13 features')",
            "consoul.chat('List all TODO comments in my project')",
            "consoul.chat('Run tests and fix any failures')",
            "approved = await approval_provider.request_approval(tool_call)",
            "result = await bash_tool.execute({'command': 'git status'})",
            # === CONVERSATION INTELLIGENCE ===
            "history = ConversationHistory(persist=True, db_path='~/.consoul')",
            "history.add_user_message('Remember: I prefer functional style')",
            "context = history.get_context_window(max_tokens=4000)",
            "# AI that remembers your preferences",
            "conversations = db.search('machine learning', limit=10)",
            # === GOATBYTES BRANDING ===
            "# Built with ❤️ by GoatBytes.IO",
            "# GoatBytes.IO: Crafting Digital Excellence Since 2024",
            "# Powered by GoatBytes.IO - Where Innovation Meets Code",
            "author = 'Jared Rummler <jared@goatbytes.io>'",
            "website = 'https://goatbytes.io'",
            "# GoatBytes: Consoul, Gira, and future innovations",
            "from goatbytes.consoul import magic",
            # === EASTER EGGS & PERSONALITY ===
            "# 🐐 GoatBytes: Greatest Of All Time Bytes",
            "# No goats were harmed making this AI assistant",
            "print('🐐 Baaaa-rilliant code!')",
            "# This AI is a goat",
            "if goat_mode: print('🐐' * 42)  # The answer to everything",
            "# TODO: Add more goat puns (we're not kidding around)",
            # === REAL CONSOUL FEATURES ===
            "console.export_conversation('important_chat.json')",
            "console.switch_model('gpt-4o')  # Hot-swap AI models",
            "profile = config.get_profile('development')",
            "theme = TuiConfig(theme='consoul-dark', show_timestamps=True)",
            "cost = calculate_cost('claude-3-5-sonnet', input_tokens=1000)",
            # === ADVANCED PATTERNS ===
            "@dataclass class AgentConfig: model: str; temperature: float",
            "async def smart_retry(func, max_attempts=3): ...",
            "with contextmanager() as ctx: await process_with_ai(ctx)",
            "result = await asyncio.gather(*[ai_task(i) for i in range(10)])",
            "match response.type: case 'text': render(response) case _: log()",
            # === MOTIVATIONAL COMMENTS ===
            "# AI is not replacing developers; it's amplifying them",
            "# The future is collaborative intelligence",
            "# Code with AI, ship faster, innovate more",
            "# Your AI pair programmer, always available",
            "# Dream it. Code it. Ship it. 🚀",
            # === PRACTICAL WORKFLOWS ===
            "consoul.chat('Review this PR and suggest improvements')",
            "consoul.chat('Generate API docs from these type hints')",
            "consoul.chat('Optimize this SQL query for PostgreSQL')",
            "consoul.chat('Convert this callback hell to async/await')",
            "consoul.chat('Migrate from Jest to Vitest')",
            # === LANGCHAIN INTEGRATION ===
            "from langchain_anthropic import ChatAnthropic",
            "from langchain_openai import ChatOpenAI",
            "from langchain_core.messages import HumanMessage, AIMessage",
            "chain = prompt | model | output_parser",
            "response = chain.invoke({'question': 'What is AI?'})",
            # === PYTHON BEST PRACTICES ===
            "[x for x in data if x.valid and x.score > 0.8]",
            "result = {k: v for k, v in items() if v is not None}",
            "with open('data.json') as f: data = json.load(f)",
            "async with aiohttp.ClientSession() as session: await fetch(session)",
            "from pathlib import Path; files = Path('.').rglob('*.py')",
            # === ERROR HANDLING ===
            "try: result = await ai_call() except AIError as e: handle(e)",
            "if not response.valid: raise ConsoulException('Invalid response')",
            "assert isinstance(output, str), 'AI must return string'",
            # === STREAMING & REAL-TIME ===
            "for token in stream: print(token, end='', flush=True)",
            "async for event in sse_stream: yield json.loads(event.data)",
            "with Spinner('Thinking...') as spinner: result = await model.ainvoke()",
            # === DATABASE & PERSISTENCE ===
            "db.save_conversation(session_id, messages, metadata)",
            "conversations = db.list_recent(limit=50, user_id=current_user)",
            "db.cleanup_old_sessions(retention_days=30)",
            "embedding = vectorstore.embed_documents([text])[0]",
            # === TOOL DEFINITIONS ===
            "@tool def search_web(query: str) -> str: ...",
            "@tool def analyze_code(filepath: str) -> dict: ...",
            "registry.register(bash_tool, read_tool, search_tool)",
            "tools = get_tools_by_category(ToolCategory.FILE_EDIT)",
            # === CONFIG & SETTINGS ===
            "config = ConsoulConfig(provider='anthropic', model='opus')",
            "profile = Profile(name='prod', tools_enabled=True)",
            "settings = load_config(Path.home() / '.consoul' / 'config.yaml')",
            # === TUI GOODNESS ===
            "from textual.app import App, ComposeResult",
            "from rich.console import Console; console = Console()",
            "from rich.markdown import Markdown; md = Markdown(text)",
            "widget.refresh(layout=True)",
            "app.push_screen(LoadingScreen())",
            # === MULTIMODAL CONTINUED ===
            "vision_response = model.invoke([image_message, text_message])",
            "image_data = base64.b64encode(open('img.png', 'rb').read())",
            # === INSPIRATIONAL MESSAGES ===
            "# NOTE: Consoul = Console + Soul ✨",
            "# The soul of your terminal experience",
            "# AI-powered development, human-centered design",
            "# Consoul: Making AI accessible, powerful, beautiful",
            "# From zero to AI in 3 lines of Python",
            # === PROFESSIONAL PATTERNS ===
            "logger.info(f'AI response: {response.content[:100]}...')",
            "metrics.record('ai_tokens_used', response.tokens)",
            "cache.set(f'response:{hash(prompt)}', response, ttl=3600)",
            # === CREATIVE AI APPLICATIONS ===
            "consoul.chat('Write a haiku about Python decorators')",
            "consoul.chat('Generate 5 creative variable names for a retry counter')",
            "consoul.chat('Explain monads using a cooking analogy')",
            "# AI as your creative collaborator",
            # === FUTURE VISION ===
            "# The future: AI that codes while you dream",
            "# Imagine: Natural language -> Production code",
            "# Tomorrow: AI teammates, not just tools",
            "# GoatBytes is building that future 🚀",
            # === ACTUAL HUMAN QUESTIONS ===
            "consoul.chat('Why is my Docker container eating all my RAM?')",
            "consoul.chat('Help me understand why this regex works')",
            "consoul.chat('I got a 403 error, what am I doing wrong?')",
            "consoul.chat('How do I exit vim?' + ' ' * 42 + '# just kidding')",
            "consoul.chat('Explain this stack trace like I am 5')",
            "consoul.chat('Is this a memory leak or am I just bad at Python?')",
            # === LATE NIGHT CODING ===
            "consoul.chat('Why does this work locally but not in prod?')",
            "consoul.chat('Should I use a class or just functions here?')",
            "consoul.chat('Is there a better way to do this?')",
            "# It's 2am and the deploy is in 6 hours",
            "consoul.chat('Quick: what does 0o755 mean in Python?')",
            "consoul.chat('Help me write a commit message for this mess')",
            # === LEARNING MODE ===
            "consoul.chat('Teach me decorators without the academic jargon')",
            "consoul.chat('What actually happens when I import a module?')",
            "consoul.chat('Explain asyncio to someone who learned Python in 2010')",
            "consoul.chat('Why do people hate ORM so much?')",
            "consoul.chat('When should I actually use a generator?')",
            # === DEBUG MODE ===
            "consoul.chat('I changed nothing and now it is broken')",
            "consoul.chat('TypeError: expected str but got NoneType. Where?')",
            "consoul.chat('Git says I have a detached HEAD. Am I in danger?')",
            "consoul.chat('My tests pass locally, fail in CI. Classic.')",
            "# Works on my machine ¯\\_(ツ)_/¯",
            # === REAL WORK ===
            "consoul.chat('Convert this SQL to SQLAlchemy ORM')",
            "consoul.chat('How do I paginate this API response?')",
            "consoul.chat('Make this function less terrible')",
            "consoul.chat('I need a regex that validates emails (yes really)')",
            "consoul.chat('What is the Pythonic way to do X?')",
            # === PROCRASTINATION ===
            "consoul.chat('Settle this: tabs or spaces?')",
            "consoul.chat('Tell me a joke about JavaScript')",
            "consoul.chat('Rate this variable name: data2_final_FINAL_v3')",
            "consoul.chat('Is HTML a programming language?' + '  # bait')",
            "consoul.chat('Write a passive aggressive comment for legacy code')",
            # === HONEST QUESTIONS ===
            "consoul.chat('Should I learn Rust or Go?' + ' # or just stick with Python')",
            "consoul.chat('Is my code slow or is the API just trash?')",
            "consoul.chat('How many try/except blocks is too many?')",
            "consoul.chat('Do I really need to write docs for this?')",
            "# TODO: ask AI to do my job interview",
            # === QUICK WINS ===
            "consoul.chat('One-liner to reverse a dict in Python')",
            "consoul.chat('How to mock datetime.now() in pytest')",
            "consoul.chat('Show me the import statement I always forget')",
            "consoul.chat('Quick chmod command for executable scripts')",
            "consoul.chat('I need a UUID right now')",
            # === EXISTENTIAL DEVELOPER THOUGHTS ===
            "# Is this tech debt or just how we write code now?",
            "# Should I refactor this or just leave it for the next person?",
            "# Note to self: AI is a tool not a replacement for thinking",
            "consoul.chat('Am I overthinking this or is it actually complex?')",
            # === COPY-PASTE CULTURE ===
            "consoul.chat('Fix this code I found on StackOverflow from 2012')",
            "consoul.chat('Modernize this code from a tutorial')",
            "consoul.chat('This snippet works but I do not know why')",
            "# If it works, do not touch it",
            # === FRIDAY AFTERNOON VIBES ===
            "consoul.chat('Make this code less cringe before I push it')",
            "consoul.chat('Is this a clever solution or am I being dumb?')",
            "consoul.chat('Help me name this thing' + ' # hardest problem in CS')",
            "# Ship it and deal with the consequences Monday",
            # === REALITY CHECK ===
            "consoul.chat('Will this scale to 1000 users?' + ' # we have 12')",
            "consoul.chat('Do I need Kubernetes for this?' + ' # probably not')",
            "consoul.chat('Should I use blockchain?' + ' # definitely not')",
            "# Premature optimization is... well you know",
            # === THE GOOD STUFF ===
            "consoul.chat('Help me architect this feature properly')",
            "consoul.chat('Code review: what did I miss?')",
            "consoul.chat('Suggest test cases I have not thought of')",
            "consoul.chat('How would you approach this problem?')",
            "# Pair programming with AI is actually pretty great",
        ]

        num_snippets = max(3, self.height // 4)
        for i in range(num_snippets):
            code = random.choice(code_samples)
            self._code_snippets.append(
                CodeSnippet(
                    x=random.uniform(-len(code), self.width * 1.5),
                    y=int(i * (self.height / num_snippets)),
                    text=code,
                    speed=random.uniform(0.3, 1.0),
                    syntax_colors=self._get_syntax_colors(code),
                )
            )

    def get_frame(self) -> list[tuple[int, int, str, int, str | None]]:
        """Generate the current animation frame.

        Returns:
            List of (x, y, char, intensity, color) tuples where:
            - intensity is 0-100
            - color is optional hex color code (None means use default coloring)
        """
        if self.style == AnimationStyle.MATRIX_RAIN:
            return self._get_matrix_rain_frame()
        elif self.style == AnimationStyle.BINARY_WAVE:
            return self._get_binary_wave_frame()
        elif self.style == AnimationStyle.PULSE:
            return self._get_pulse_frame()
        elif self.style == AnimationStyle.CODE_STREAM:
            return self._get_code_stream_frame()
        elif self.style == AnimationStyle.SOUND_WAVE:
            return self._get_sound_wave_frame()
        return []

    def _get_matrix_rain_frame(self) -> list[tuple[int, int, str, int, str | None]]:
        """Generate a matrix rain animation frame."""
        frame_data: list[tuple[int, int, str, int, str | None]] = []

        for column in self._columns:
            column.y += column.speed

            if column.y > self.height + column.length:
                column.y = random.uniform(-column.length, -1)
                column.speed = random.uniform(0.3, 1.5)
                column.length = random.randint(5, 15)
                column.chars = [random.choice(["0", "1"]) for _ in range(15)]

            for i in range(column.length):
                y = int(column.y - i)
                if 0 <= y < self.height and 0 <= column.x < self.width:
                    intensity = int(100 * (1 - i / column.length))
                    char_idx = (i + self.frame // 3) % len(column.chars)
                    frame_data.append(
                        (column.x, y, column.chars[char_idx], intensity, None)
                    )

        return frame_data

    def _get_binary_wave_frame(self) -> list[tuple[int, int, str, int, str | None]]:
        """Generate a wave animation frame."""
        frame_data: list[tuple[int, int, str, int, str | None]] = []

        for y in range(self.height):
            for x in range(0, self.width, 2):
                wave = math.sin((x / self.width) * 4 * math.pi + self.frame * 0.1)
                wave += math.sin((y / self.height) * 3 * math.pi + self.frame * 0.15)

                intensity = int(50 + 50 * wave / 2)
                char = "1" if wave > 0 else "0"

                if random.random() < 0.1:
                    char = random.choice(["0", "1"])

                frame_data.append((x, y, char, intensity, None))

        return frame_data

    def _get_pulse_frame(self) -> list[tuple[int, int, str, int, str | None]]:
        """Generate a pulsing binary pattern frame."""
        frame_data: list[tuple[int, int, str, int, str | None]] = []

        center_x = self.width // 2
        center_y = self.height // 2
        pulse = abs(math.sin(self.frame * 0.1))

        for y in range(self.height):
            for x in range(0, self.width, 2):
                dx = x - center_x
                dy = y - center_y
                distance = math.sqrt(dx * dx + dy * dy)

                wave = math.sin(distance * 0.3 - self.frame * 0.2)
                intensity = int(50 + 50 * wave * pulse)

                char_val = int((distance + self.frame * 0.5) % 2)
                char = "1" if char_val == 0 else "0"

                frame_data.append((x, y, char, intensity, None))

        return frame_data

    def _get_code_stream_frame(self) -> list[tuple[int, int, str, int, str | None]]:
        """Generate horizontal scrolling code stream frame."""
        frame_data: list[tuple[int, int, str, int, str | None]] = []

        for snippet in self._code_snippets:
            snippet.x -= snippet.speed

            if snippet.x + len(snippet.text) < 0:
                snippet.x = self.width + random.uniform(10, 30)
                snippet.speed = random.uniform(0.3, 1.0)

            for i, char in enumerate(snippet.text):
                x = int(snippet.x + i)
                y = snippet.y

                if 0 <= x < self.width and 0 <= y < self.height:
                    color = (
                        snippet.syntax_colors[i]
                        if i < len(snippet.syntax_colors)
                        else "#FFFFFF"
                    )
                    frame_data.append((x, y, char, 100, color))

        return frame_data

    def _get_sound_wave_frame(self) -> list[tuple[int, int, str, int, str | None]]:
        """Generate sound wave animation matching the Consoul logo."""
        frame_data: list[tuple[int, int, str, int, str | None]] = []

        center_y = self.height // 2

        for column in self._waveform_columns:
            # Update phase for animation
            column.phase += column.speed

            # Calculate wave height
            wave_height = column.amplitude * math.sin(column.phase)

            # Draw vertical bar
            start_y = int(center_y - abs(wave_height))
            end_y = int(center_y + abs(wave_height))

            for y in range(max(0, start_y), min(self.height, end_y + 1)):
                if 0 <= column.x < self.width and 0 <= y < self.height:
                    # Distance from center determines intensity
                    dist_from_center = abs(y - center_y)
                    max_dist = abs(wave_height) if wave_height != 0 else 1
                    intensity = int(100 * (1 - dist_from_center / max(max_dist, 1)))

                    # Use rounded block characters for smooth waveform look
                    chars = ["▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
                    char_idx = min(int(intensity / 100 * len(chars)), len(chars) - 1)
                    char = chars[char_idx]

                    frame_data.append((column.x, y, char, intensity, None))

        return frame_data

    def advance(self) -> None:
        """Advance the animation to the next frame."""
        self.frame += 1
