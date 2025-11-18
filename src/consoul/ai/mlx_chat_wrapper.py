"""MLX Chat Wrapper - Compatible with modern mlx-lm API.

This wrapper provides chat model functionality for MLX models using
mlx_lm directly, avoiding subprocess and MLXPipeline issues.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult

if TYPE_CHECKING:
    from langchain_core.callbacks.manager import CallbackManagerForLLMRun

DEFAULT_SYSTEM_PROMPT = """You are a helpful, respectful, and honest assistant."""


class MLXChatWrapper(BaseChatModel):
    """MLX chat model wrapper using mlx_lm directly.

    Loads models directly with mlx_lm.load() instead of using MLXPipeline
    to avoid subprocess issues (fds_to_keep errors).

    Example:
        .. code-block:: python

            from consoul.ai.mlx_chat_wrapper import MLXChatWrapper

            chat = MLXChatWrapper(
                model_id="mlx-community/Phi-3.5-mini-instruct-4bit",
                max_tokens=2048,
                temperature=0.7,
            )
    """

    model: Any = None  # MLX model
    tokenizer: Any = None  # MLX tokenizer
    model_id: str = ""
    max_tokens: int = 2048
    temperature: float = 0.7
    top_p: float = 1.0
    min_p: float = 0.0
    repetition_penalty: float | None = None
    repetition_context_size: int | None = 20
    verbose: bool = False
    system_message: SystemMessage = SystemMessage(content=DEFAULT_SYSTEM_PROMPT)

    def __init__(self, **kwargs: Any):
        import logging
        import os

        logger = logging.getLogger(__name__)

        # Extract model_id before calling super().__init__
        model_id = kwargs.get("model_id", "")
        logger.info(f"MLXChatWrapper.__init__ called with model_id={model_id}")

        super().__init__(**kwargs)

        # Disable tqdm progress bars to avoid multiprocessing issues in TUI
        # This prevents "bad value(s) in fds_to_keep" errors during HF downloads
        os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"

        # Load model using mlx_lm directly
        try:
            from mlx_lm import load

            logger.info(
                f"MLX: Loading model directly with mlx_lm.load('{self.model_id}')..."
            )
            logger.info(
                "MLX: Progress bars disabled to avoid TUI multiprocessing issues"
            )
            self.model, self.tokenizer = load(self.model_id)
            logger.info("MLX: Model loaded successfully")
        except ImportError as e:
            raise ImportError(
                "Could not import mlx_lm. Please install it with `pip install mlx-lm`."
            ) from e
        except ValueError as e:
            if "fds_to_keep" in str(e):
                raise RuntimeError(
                    f"Failed to load MLX model due to multiprocessing issue.\n\n"
                    f"This happens when downloading models from HuggingFace in a TUI.\n\n"
                    f"Workaround: Pre-download the model before starting the TUI:\n"
                    f"  python -c \"from mlx_lm import load; load('{self.model_id}')\"\n\n"
                    f"Or use a locally cached model (check ~/.cache/huggingface/hub/)"
                ) from e
            raise
        except Exception as e:
            logger.error(f"MLX: Failed to load model: {e}", exc_info=True)
            raise

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Generate a response from the MLX model."""
        try:
            from mlx_lm import generate
            from mlx_lm.sample_utils import make_logits_processors, make_sampler
        except ImportError as e:
            raise ImportError(
                "Could not import mlx_lm python package. "
                "Please install it with `pip install mlx-lm`."
            ) from e

        # Convert messages to chat prompt format
        llm_input = self._to_chat_prompt(messages)

        # Create sampler and logits processors
        sampler = make_sampler(
            self.temperature,
            self.top_p,
            self.min_p,
            1,  # min_tokens_to_keep
        )

        # Only create logits processors if we have repetition penalty
        logits_processors = None
        if self.repetition_penalty is not None:
            logits_processors = make_logits_processors(
                None, self.repetition_penalty, self.repetition_context_size or 20
            )

        # Call mlx-lm generate directly
        response_text = generate(
            model=self.model,
            tokenizer=self.tokenizer,
            prompt=llm_input,
            max_tokens=self.max_tokens,
            verbose=self.verbose,
            sampler=sampler,
            logits_processors=logits_processors,
        )

        # Create chat result
        message = AIMessage(content=response_text)
        generation = ChatGeneration(message=message)
        return ChatResult(generations=[generation])

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Async generate - delegates to sync for now."""
        return self._generate(messages, stop, run_manager, **kwargs)

    def _to_chat_prompt(self, messages: list[BaseMessage]) -> str:
        """Convert a list of messages into a prompt format expected by MLX model."""
        if not messages:
            raise ValueError("At least one HumanMessage must be provided!")

        if not isinstance(messages[-1], HumanMessage):
            raise ValueError("Last message must be a HumanMessage!")

        # Convert to ChatML format dicts
        messages_dicts = [self._to_chatml_format(m) for m in messages]

        # Use tokenizer's chat template if available
        if hasattr(self.tokenizer, "apply_chat_template"):
            return str(
                self.tokenizer.apply_chat_template(
                    messages_dicts,
                    tokenize=False,
                    add_generation_prompt=True,
                )
            )

        # Fallback: simple concatenation
        prompt_parts = []
        for msg_dict in messages_dicts:
            role = msg_dict["role"]
            content = msg_dict["content"]
            if role == "system":
                prompt_parts.append(f"System: {content}\n")
            elif role == "user":
                prompt_parts.append(f"User: {content}\n")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}\n")

        prompt_parts.append("Assistant:")
        return "".join(prompt_parts)

    def _to_chatml_format(self, message: BaseMessage) -> dict[str, Any]:
        """Convert LangChain message to ChatML format."""
        if isinstance(message, SystemMessage):
            role = "system"
        elif isinstance(message, AIMessage):
            role = "assistant"
        elif isinstance(message, HumanMessage):
            role = "user"
        else:
            raise ValueError(f"Unknown message type: {type(message)}")

        return {"role": role, "content": message.content}

    @property
    def _llm_type(self) -> str:
        return "mlx-chat-wrapper"
