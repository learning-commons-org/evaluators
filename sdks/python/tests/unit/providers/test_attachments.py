"""Where each adapter puts image attachments: on the final user turn, ahead of its text.

The three vendors spell an inline image three ways — an OpenAI ``input_image`` data URL, an
Anthropic base64 ``image`` block, a Gemini inline-data part — and every one of them must
land in the same place, carry the same bytes and media type, and leave every other turn,
and every text-only request, exactly as it was.
"""

from __future__ import annotations

import base64
from typing import Any

import pytest

from learning_commons_evaluators.providers import ImageAttachment, Message
from tests.unit.providers import test_anthropic_sdk, test_google_genai, test_openai_sdk

PNG = ImageAttachment(data=b"\x89PNG first image bytes", media_type="image/png")
JPEG = ImageAttachment(data=b"\xff\xd8\xff second image bytes", media_type="image/jpeg")

CONVERSATION: list[Message] = [
    {"role": "system", "content": "You are a reviewer."},
    {"role": "user", "content": "first"},
    {"role": "assistant", "content": "reply"},
    {"role": "user", "content": "second"},
]

SYSTEM_ONLY: list[Message] = [{"role": "system", "content": "You are a reviewer."}]


def b64(attachment: ImageAttachment) -> str:
    return base64.b64encode(attachment.data).decode("ascii")


class TestOpenAI:
    def call(self, client: Any) -> dict[str, Any]:
        return dict(client.responses.parse.await_args.kwargs)

    async def run(self, messages: list[Message], **kwargs: Any) -> dict[str, Any]:
        client = test_openai_sdk._client(parsed=test_openai_sdk._Verdict(score=1, reasoning="r"))
        await test_openai_sdk._adapter(client).generate_structured(
            messages, test_openai_sdk._Verdict, **kwargs
        )
        return self.call(client)

    def test_declares_attachment_support(self) -> None:
        assert test_openai_sdk._adapter(test_openai_sdk._client()).supports_attachments is True

    async def test_places_images_on_the_last_user_turn_ahead_of_its_text(self) -> None:
        kwargs = await self.run(CONVERSATION, attachments=[PNG, JPEG])
        assert kwargs["instructions"] == "You are a reviewer."
        assert kwargs["input"] == [
            {"role": "user", "content": "first"},
            {"role": "assistant", "content": "reply"},
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_image",
                        "image_url": f"data:image/png;base64,{b64(PNG)}",
                        "detail": "auto",
                    },
                    {
                        "type": "input_image",
                        "image_url": f"data:image/jpeg;base64,{b64(JPEG)}",
                        "detail": "auto",
                    },
                    {"type": "input_text", "text": "second"},
                ],
            },
        ]

    async def test_sends_a_text_only_request_exactly_as_before(self) -> None:
        kwargs = await self.run(CONVERSATION)
        assert kwargs["input"][-1] == {"role": "user", "content": "second"}

    async def test_refuses_attachments_with_no_user_turn_to_carry_them(self) -> None:
        with pytest.raises(ValueError, match="need a user message"):
            await self.run(SYSTEM_ONLY, attachments=[PNG])


class TestAnthropic:
    async def run(self, messages: list[Message], **kwargs: Any) -> dict[str, Any]:
        client = test_anthropic_sdk._client(parsed=test_anthropic_sdk._Verdict(aligned=True))
        await test_anthropic_sdk._adapter(client).generate_structured(
            messages, test_anthropic_sdk._Verdict, **kwargs
        )
        return dict(client.messages.parse.await_args.kwargs)

    def test_declares_attachment_support(self) -> None:
        adapter = test_anthropic_sdk._adapter(test_anthropic_sdk._client())
        assert adapter.supports_attachments is True

    async def test_places_images_on_the_last_user_turn_ahead_of_its_text(self) -> None:
        kwargs = await self.run(CONVERSATION, attachments=[PNG, JPEG])
        assert kwargs["system"] == "You are a reviewer."
        assert kwargs["messages"] == [
            {"role": "user", "content": "first"},
            {"role": "assistant", "content": "reply"},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": "image/png", "data": b64(PNG)},
                    },
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": "image/jpeg", "data": b64(JPEG)},
                    },
                    {"type": "text", "text": "second"},
                ],
            },
        ]

    async def test_sends_a_text_only_request_exactly_as_before(self) -> None:
        kwargs = await self.run(CONVERSATION)
        assert kwargs["messages"][-1] == {"role": "user", "content": "second"}

    async def test_refuses_attachments_with_no_user_turn_to_carry_them(self) -> None:
        with pytest.raises(ValueError, match="need a user message"):
            await self.run(SYSTEM_ONLY, attachments=[PNG])


class TestGoogle:
    async def run(self, messages: list[Message], **kwargs: Any) -> Any:
        client = test_google_genai._client(text='{"grade_band": "2-3", "met": 0}')
        await test_google_genai._adapter(client).generate_structured(
            messages, test_google_genai._Verdict, **kwargs
        )
        return client.aio.models.generate_content.await_args.kwargs

    def test_declares_attachment_support(self) -> None:
        adapter = test_google_genai._adapter(test_google_genai._client())
        assert adapter.supports_attachments is True

    async def test_places_images_on_the_last_user_turn_ahead_of_its_text(self) -> None:
        kwargs = await self.run(CONVERSATION, attachments=[PNG, JPEG])
        assert kwargs["config"].system_instruction == "You are a reviewer."
        first, reply, last = kwargs["contents"]
        assert (first.role, [p.text for p in first.parts]) == ("user", ["first"])
        assert (reply.role, [p.text for p in reply.parts]) == ("model", ["reply"])
        assert last.role == "user"
        images, text = last.parts[:2], last.parts[2]
        assert [(p.inline_data.data, p.inline_data.mime_type) for p in images] == [
            (PNG.data, "image/png"),
            (JPEG.data, "image/jpeg"),
        ]
        assert text.text == "second"
        assert len(last.parts) == 3

    async def test_sends_a_text_only_request_exactly_as_before(self) -> None:
        kwargs = await self.run(CONVERSATION)
        [part] = kwargs["contents"][-1].parts
        assert part.text == "second"
        assert part.inline_data is None

    async def test_refuses_attachments_with_no_user_turn_to_carry_them(self) -> None:
        with pytest.raises(ValueError, match="need a user message"):
            await self.run(SYSTEM_ONLY, attachments=[PNG])
