# Building with extended thinking

---

<Note>
This feature is eligible for [Zero Data Retention (ZDR)](/docs/en/build-with-claude/api-and-data-retention). When your organization has a ZDR arrangement, data sent through this feature is not stored after the API response is returned.
</Note>

Extended thinking gives Claude enhanced reasoning capabilities for complex tasks, while providing varying levels of transparency into its step-by-step thought process before it delivers its final answer.

<Note>
For Claude Opus 4.7 and later models, use [adaptive thinking](/docs/en/build-with-claude/adaptive-thinking) (`thinking: {type: "adaptive"}`) with the [effort parameter](/docs/en/build-with-claude/effort). Manual extended thinking (`thinking: {type: "enabled", budget_tokens: N}`) is no longer supported on Claude Opus 4.7 or later models and returns a 400 error. For Claude Opus 4.6 and Claude Sonnet 4.6, adaptive thinking is also recommended; the manual configuration is still functional on these models but is deprecated and will be removed in a future model release.
</Note>

## Supported models

Manual extended thinking (`thinking: {type: "enabled", budget_tokens: N}`) is supported on all current Claude models **except Claude Opus 4.7 and later models**, where it is no longer accepted and returns a 400 error. A few models have mode-specific behavior:

- **Claude Opus 4.7 (`claude-opus-4-7`) and later models:** manual extended thinking is no longer supported. Use [adaptive thinking](/docs/en/build-with-claude/adaptive-thinking) (`thinking: {type: "adaptive"}`) with the [effort parameter](/docs/en/build-with-claude/effort) instead.
- **[Claude Mythos Preview](https://anthropic.com/glasswing):** [adaptive thinking](/docs/en/build-with-claude/adaptive-thinking) is the default; `thinking: {type: "enabled", budget_tokens: N}` is also accepted. `thinking: {type: "disabled"}` is not supported, and `display` defaults to `"omitted"` rather than returning thinking content. Pass `display: "summarized"` to receive summaries.
- **Claude Opus 4.6 (`claude-opus-4-6`):** [adaptive thinking](/docs/en/build-with-claude/adaptive-thinking) recommended; manual mode (`type: "enabled"`) is deprecated but still functional.
- **Claude Sonnet 4.6 (`claude-sonnet-4-6`):** [adaptive thinking](/docs/en/build-with-claude/adaptive-thinking) recommended; manual mode (`type: "enabled"`) with [interleaved mode](#interleaved-thinking) is deprecated but still functional.

<Note>
API behavior differs across Claude Sonnet 3.7 and Claude 4 models, but the API shapes remain exactly the same.

For more information, see [Differences in thinking across model versions](#differences-in-thinking-across-model-versions).
</Note>

## How extended thinking works

When extended thinking is turned on, Claude creates `thinking` content blocks where it outputs its internal reasoning. Claude incorporates insights from this reasoning before crafting a final response.

The API response includes `thinking` content blocks, followed by `text` content blocks.

Here's an example of the default response format:

```json
{
  "content": [
    {
      "type": "thinking",
      "thinking": "Let me analyze this step by step...",
      "signature": "WaUjzkypQ2mUEVM36O2TxuC06KN8xyfbJwyem2dw3URve/op91XWHOEBLLqIOMfFG/UvLEczmEsUjavL...."
    },
    {
      "type": "text",
      "text": "Based on my analysis..."
    }
  ]
}
```

For more information about the response format of extended thinking, see the [Messages API Reference](/docs/en/api/messages/create).

## How to use extended thinking

Here is an example of using extended thinking in the Messages API:

<CodeGroup>
```bash Shell
curl https://api.anthropic.com/v1/messages \
     --header "x-api-key: $ANTHROPIC_API_KEY" \
     --header "anthropic-version: 2023-06-01" \
     --header "content-type: application/json" \
     --data \
'{
    "model": "claude-sonnet-4-6",
    "max_tokens": 16000,
    "thinking": {
        "type": "enabled",
        "budget_tokens": 10000
    },
    "messages": [
        {
            "role": "user",
            "content": "Are there an infinite number of prime numbers such that n mod 4 == 3?"
        }
    ]
}'
```

```bash CLI
ant messages create \
  --transform content --format yaml \
    --model claude-sonnet-4-6 \
    --max-tokens 16000 \
    --thinking '{type: enabled, budget_tokens: 10000}' \
    --message '{role: user, content: Are there an infinite number of prime numbers such that n mod 4 == 3?}'
```

```python Python hidelines={1..2}
import anthropic

client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=16000,
    thinking={"type": "enabled", "budget_tokens": 10000},
    messages=[
        {
            "role": "user",
            "content": "Are there an infinite number of prime numbers such that n mod 4 == 3?",
        }
    ],
)

# The response contains summarized thinking blocks and text blocks
for block in response.content:
    if block.type == "thinking":
        print(f"\nThinking summary: {block.thinking}")
    elif block.type == "text":
        print(f"\nResponse: {block.text}")
```

```typescript TypeScript hidelines={1..2}
import Anthropic from "@anthropic-ai/sdk";

const client = new Anthropic();

const response = await client.messages.create({
  model: "claude-sonnet-4-6",
  max_tokens: 16000,
  thinking: {
    type: "enabled",
    budget_tokens: 10000
  },
  messages: [
    {
      role: "user",
      content: "Are there an infinite number of prime numbers such that n mod 4 == 3?"
    }
  ]
});

// The response contains summarized thinking blocks and text blocks
for (const block of response.content) {
  if (block.type === "thinking") {
    console.log(`\nThinking summary: ${block.thinking}`);
  } else if (block.type === "text") {
    console.log(`\nResponse: ${block.text}`);
  }
}
```

```csharp C#
using System;
using System.Threading.Tasks;
using Anthropic;
using Anthropic.Models.Messages;

class Program
{
    static async Task Main(string[] args)
    {
        AnthropicClient client = new();

        var parameters = new MessageCreateParams
        {
            Model = Model.ClaudeSonnet4_6,
            MaxTokens = 16000,
            Thinking = new ThinkingConfigEnabled(budgetTokens: 10000),
            Messages = [
                new() {
                    Role = Role.User,
                    Content = "Are there an infinite number of prime numbers such that n mod 4 == 3?"
                }
            ]
        };

        var message = await client.Messages.Create(parameters);

        foreach (var block in message.Content)
        {
            if (block.TryPickThinking(out ThinkingBlock? thinking))
            {
                Console.WriteLine($"\nThinking summary: {thinking.Thinking}");
            }
            else if (block.TryPickText(out TextBlock? text))
            {
                Console.WriteLine($"\nResponse: {text.Text}");
            }
        }
    }
}
```

```go Go hidelines={1..11,-1}
package main

import (
	"context"
	"fmt"
	"log"

	"github.com/anthropics/anthropic-sdk-go"
)

func main() {
	client := anthropic.NewClient()

	response, err := client.Messages.New(context.TODO(), anthropic.MessageNewParams{
		Model:     anthropic.Model("claude-sonnet-4-6"),
		MaxTokens: 16000,
		Thinking:  anthropic.ThinkingConfigParamOfEnabled(10000),
		Messages: []anthropic.MessageParam{
			anthropic.NewUserMessage(anthropic.NewTextBlock("Are there an infinite number of prime numbers such that n mod 4 == 3?")),
		},
	})
	if err != nil {
		log.Fatal(err)
	}

	for _, block := range response.Content {
		switch v := block.AsAny().(type) {
		case anthropic.ThinkingBlock:
			fmt.Printf("\nThinking summary: %s", v.Thinking)
		case anthropic.TextBlock:
			fmt.Printf("\nResponse: %s", v.Text)
		}
	}
}
```

```java Java hidelines={1..8,-2..}
import com.anthropic.client.AnthropicClient;
import com.anthropic.client.okhttp.AnthropicOkHttpClient;
import com.anthropic.models.messages.MessageCreateParams;
import com.anthropic.models.messages.Message;
import com.anthropic.models.messages.Model;

public class ExtendedThinkingExample {
    public static void main(String[] args) {
        AnthropicClient client = AnthropicOkHttpClient.fromEnv();

        MessageCreateParams params = MessageCreateParams.builder()
            .model(Model.CLAUDE_SONNET_4_6)
            .maxTokens(16000L)
            .enabledThinking(10000L)
            .addUserMessage("Are there an infinite number of prime numbers such that n mod 4 == 3?")
            .build();

        Message response = client.messages().create(params);

        response.content().forEach(block -> {
            block.thinking().ifPresent(thinkingBlock ->
                System.out.println("\nThinking summary: " + thinkingBlock.thinking())
            );
            block.text().ifPresent(textBlock ->
                System.out.println("\nResponse: " + textBlock.text())
            );
        });
    }
}
```

```php PHP hidelines={1..4}
<?php

use Anthropic\Client;

$client = new Client(apiKey: getenv("ANTHROPIC_API_KEY"));

$message = $client->messages->create(
    maxTokens: 16000,
    messages: [
        [
            'role' => 'user',
            'content' => 'Are there an infinite number of prime numbers such that n mod 4 == 3?'
        ]
    ],
    model: 'claude-sonnet-4-6',
    thinking: ['type' => 'enabled', 'budget_tokens' => 10000],
);

foreach ($message->content as $block) {
    if ($block->type === 'thinking') {
        echo "\nThinking summary: " . $block->thinking;
    } elseif ($block->type === 'text') {
        echo "\nResponse: " . $block->text;
    }
}
```

```ruby Ruby hidelines={1..2}
require "anthropic"

client = Anthropic::Client.new

message = client.messages.create(
  model: "claude-sonnet-4-6",
  max_tokens: 16000,
  thinking: {
    type: "enabled",
    budget_tokens: 10000
  },
  messages: [
    {
      role: "user",
      content: "Are there an infinite number of prime numbers such that n mod 4 == 3?"
    }
  ]
)

message.content.each do |block|
  case block.type
  when :thinking
    puts "\nThinking summary: #{block.thinking}"
  when :text
    puts "\nResponse: #{block.text}"
  end
end
```

</CodeGroup>

To turn on extended thinking, add a `thinking` object, with the `type` parameter set to `enabled` and the `budget_tokens` to a specified token budget for extended thinking. For Claude Opus 4.6 and Claude Sonnet 4.6, use `type: "adaptive"` instead. See [Adaptive thinking](/docs/en/build-with-claude/adaptive-thinking) for details. While `type: "enabled"` with `budget_tokens` is still functional on these models, it is deprecated and will be removed in a future release.

The `budget_tokens` parameter determines the maximum number of tokens Claude is allowed to use for its internal reasoning process. In Claude 4 and later models, this limit applies to full thinking tokens, and not to [the summarized output](#summarized-thinking). Larger budgets can improve response quality by enabling more thorough analysis for complex problems, although Claude may not use the entire budget allocated, especially at ranges above 32k.

<Warning>
`budget_tokens` is [deprecated](/docs/en/build-with-claude/overview#feature-availability) on Claude Opus 4.6 and Claude Sonnet 4.6 and will be removed in a future model release. Use [adaptive thinking](/docs/en/build-with-claude/adaptive-thinking) with the [effort parameter](/docs/en/build-with-claude/effort) to control thinking depth instead.
</Warning>

<Note>
[Claude Mythos Preview](https://anthropic.com/glasswing), Claude Opus 4.7, and Claude Opus 4.6 support up to 128k output tokens. Claude Sonnet 4.6 and Claude Haiku 4.5 support up to 64k. See the [models overview](/docs/en/about-claude/models/overview) for limits on legacy models. On the [Message Batches API](/docs/en/build-with-claude/batch-processing#extended-output-beta), the `output-300k-2026-03-24` [beta header](/docs/en/api/beta-headers) raises the output limit to 300k for Opus 4.7, Opus 4.6, and Sonnet 4.6.
</Note>

`budget_tokens` must be set to a value less than `max_tokens`. However, when using [interleaved thinking with tools](#interleaved-thinking), you can exceed this limit as the token limit becomes your entire context window.

### Summarized thinking

With extended thinking enabled, the Messages API for Claude 4 models returns a summary of Claude's full thinking process. Summarized thinking provides the full intelligence benefits of extended thinking, while preventing misuse. This is the default behavior on Claude 4 models when the `display` field on the thinking configuration is unset or set to `"summarized"`. On Claude Opus 4.7 and [Claude Mythos Preview](https://anthropic.com/glasswing), `display` defaults to `"omitted"` instead, so you must set `display: "summarized"` explicitly to receive summarized thinking.

Here are some important considerations for summarized thinking:

- You're charged for the full thinking tokens generated by the original request, not the summary tokens.
- The billed output token count will **not match** the count of tokens you see in the response.
- On Claude 4 models, the first few lines of thinking output are more verbose, providing detailed reasoning that's particularly helpful for prompt engineering purposes. [Claude Mythos Preview](https://anthropic.com/glasswing) summarizes from the first token, so its thinking blocks do not show this verbose preamble.
- As Anthropic seeks to improve the extended thinking feature, summarization behavior is subject to change.
- Summarization preserves the key ideas of Claude's thinking process with minimal added latency, enabling a streamable user experience and easy migration from Claude Sonnet 3.7 to Claude 4 and later models.
- Summarization is processed by a different model than the one you target in your requests. The thinking model does not see the summarized output.

<Note>
Claude Sonnet 3.7 continues to return full thinking output.

In rare cases where you need access to full thinking output for Claude 4 models, [contact our sales team](mailto:sales@anthropic.com).
</Note>

### Controlling thinking display

The `display` field on the thinking configuration controls how thinking content is returned in API responses. It accepts two values:

- `"summarized"`: Thinking blocks contain summarized thinking text. See [Summarized thinking](#summarized-thinking) for details. This is the default on Claude Opus 4.6, Claude Sonnet 4.6, and earlier Claude 4 models.
- `"omitted"`: Thinking blocks are returned with an empty `thinking` field. The `signature` field still carries the encrypted full thinking for multi-turn continuity (see [Thinking encryption](#thinking-encryption)). This is the default on Claude Opus 4.7 and [Claude Mythos Preview](https://anthropic.com/glasswing).

Setting `display: "omitted"` is useful when your application doesn't surface thinking content to users. The primary benefit is **faster time-to-first-text-token when streaming:** The server skips streaming thinking tokens entirely and delivers only the signature, so the final text response begins streaming sooner.

<Note>
No SDK currently includes `display` in its type definitions. The Python SDK forwards unrecognized dict keys to the API at runtime; passing `display` in the thinking dict works transparently. The TypeScript SDK requires a type assertion. The C#, Go, Java, PHP, and Ruby SDKs require a direct HTTP request until native support lands.
</Note>

Here are some important considerations for omitted thinking:

- You're still charged for the full thinking tokens. Omitting reduces latency, not cost.
- If you pass thinking blocks back in multi-turn conversations, pass them unchanged. The server decrypts the `signature` to reconstruct the original thinking for prompt construction (see [Preserving thinking blocks](/docs/en/build-with-claude/extended-thinking#preserving-thinking-blocks)). Any text you place in the `thinking` field of a round-tripped omitted block is ignored.
- `display` is invalid with `thinking.type: "disabled"` (there is nothing to display).
- When using `thinking.type: "adaptive"` and the model skips thinking for a simple request, no thinking block is produced regardless of `display`.

<Note>
The `signature` field is identical whether `display` is `"summarized"` or `"omitted"`. Switching `display` values between turns in a conversation is supported.
</Note>

<Note>
On [Claude Mythos Preview](https://anthropic.com/glasswing), `display` defaults to `"omitted"`. The examples in this section pass `display` explicitly so they apply to all models, but on Mythos Preview you can leave it unset and receive the same behavior. To receive summarized thinking on Mythos Preview, set `display: "summarized"` explicitly.
</Note>

Automated pipelines that never surface thinking content to end users can skip the overhead of receiving thinking tokens over the wire. Latency-sensitive applications get the same reasoning quality without waiting for thinking text to stream before the final response begins.

[Code examples in Shell, CLI, Python, TypeScript, C#, Go, Java, PHP, and Ruby tabs demonstrating `display: "omitted"` with curl / ant / SDK calls - preserved verbatim in original source]

When `display: "omitted"` is set, the response contains `thinking` blocks with an empty `thinking` field:

```json Output
{
  "content": [
    {
      "type": "thinking",
      "thinking": "",
      "signature": "EosnCkYICxIMMb3LzNrMu..."
    },
    {
      "type": "text",
      "text": "The answer is 12,231."
    }
  ]
}
```

When streaming with `display: "omitted"`, no `thinking_delta` events are emitted; see [Streaming thinking](#streaming-thinking) below for the event sequence.

### Streaming thinking

You can stream extended thinking responses using [server-sent events (SSE)](https://developer.mozilla.org/en-US/Web/API/Server-sent%5Fevents/Using%5Fserver-sent%5Fevents).

When streaming is enabled for extended thinking, you receive thinking content via `thinking_delta` events.

When `display: "omitted"` is set, no `thinking_delta` events are emitted. See [Controlling thinking display](#controlling-thinking-display).

For more documentation on streaming via the Messages API, see [Streaming Messages](/docs/en/build-with-claude/streaming).

[Shell/CLI/Python/TypeScript/C#/Go/Java/PHP/Ruby streaming code examples preserved verbatim in original source]

Example streaming output:
```sse Output
event: message_start
data: {"type": "message_start", "message": {"id": "msg_01...", "type": "message", "role": "assistant", "content": [], "model": "claude-sonnet-4-6", "stop_reason": null, "stop_sequence": null}}

event: content_block_start
data: {"type": "content_block_start", "index": 0, "content_block": {"type": "thinking", "thinking": "", "signature": ""}}

event: content_block_delta
data: {"type": "content_block_delta", "index": 0, "delta": {"type": "thinking_delta", "thinking": "I need to find the GCD of 1071 and 462 using the Euclidean algorithm.\n\n1071 = 2 × 462 + 147"}}

event: content_block_delta
data: {"type": "content_block_delta", "index": 0, "delta": {"type": "thinking_delta", "thinking": "\n462 = 3 × 147 + 21\n147 = 7 × 21 + 0\n\nSo GCD(1071, 462) = 21"}}

// Additional thinking deltas...

event: content_block_delta
data: {"type": "content_block_delta", "index": 0, "delta": {"type": "signature_delta", "signature": "EqQBCgIYAhIM1gbcDa9GJwZA2b3hGgxBdjrkzLoky3dl1pkiMOYds..."}}

event: content_block_stop
data: {"type": "content_block_stop", "index": 0}

event: content_block_start
data: {"type": "content_block_start", "index": 1, "content_block": {"type": "text", "text": ""}}

event: content_block_delta
data: {"type": "content_block_delta", "index": 1, "delta": {"type": "text_delta", "text": "The greatest common divisor of 1071 and 462 is **21**."}}

// Additional text deltas...

event: content_block_stop
data: {"type": "content_block_stop", "index": 1}

event: message_delta
data: {"type": "message_delta", "delta": {"stop_reason": "end_turn", "stop_sequence": null}}

event: message_stop
data: {"type": "message_stop"}
```

When `display: "omitted"` is set, the thinking block opens, a single `signature_delta` arrives, and the block closes without any `thinking_delta` events. Text streaming begins immediately after:

```sse Output
event: content_block_start
data: {"type":"content_block_start","index":0,"content_block":{"type":"thinking","thinking":"","signature":""}}

event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"signature_delta","signature":"EosnCkYICxIMMb3LzNrMu..."}}

event: content_block_stop
data: {"type":"content_block_stop","index":0}

event: content_block_start
data: {"type":"content_block_start","index":1,"content_block":{"type":"text","text":""}}
```

<Note>
When using streaming with thinking enabled, you might notice that text sometimes arrives in larger chunks alternating with smaller, token-by-token delivery. This is expected behavior, especially for thinking content.

The streaming system needs to process content in batches for optimal performance, which can result in this "chunky" delivery pattern, with possible delays between streaming events. Anthropic is continuously working to improve this experience, with future updates focused on making thinking content stream more smoothly.
</Note>

## Extended thinking with tool use

Extended thinking can be used alongside [tool use](/docs/en/agents-and-tools/tool-use/overview), allowing Claude to reason through tool selection and results processing.

When using extended thinking with tool use, be aware of the following limitations:

1. **Tool choice limitation**: Tool use with thinking only supports `tool_choice: {"type": "auto"}` (the default) or `tool_choice: {"type": "none"}`. Using `tool_choice: {"type": "any"}` or `tool_choice: {"type": "tool", "name": "..."}` will result in an error because these options force tool use, which is incompatible with extended thinking.

2. **Preserving thinking blocks**: During tool use, you must pass `thinking` blocks back to the API for the last assistant message. Include the complete unmodified block back to the API to maintain reasoning continuity.

### Toggling thinking modes in conversations

You can't toggle thinking in the middle of an assistant turn, including during tool use loops. The entire assistant turn should operate in a single thinking mode:

- **If thinking is enabled**, the final assistant turn should start with a thinking block.
- **If thinking is disabled**, the final assistant turn shouldn't contain any thinking blocks

From the model's perspective, **tool use loops are part of the assistant turn**. An assistant turn doesn't complete until Claude finishes its full response, which may include multiple tool calls and results.

For example, this sequence is all part of a **single assistant turn**:
```text
User: "What's the weather in Paris?"
Assistant: [thinking] + [tool_use: get_weather]
User: [tool_result: "20°C, sunny"]
Assistant: [text: "The weather in Paris is 20°C and sunny"]
```

Even though there are multiple API messages, the tool use loop is conceptually part of one continuous assistant response.

#### Graceful thinking degradation

When a mid-turn thinking conflict occurs (such as toggling thinking on or off during a tool use loop), the API automatically disables thinking for that request. To preserve model quality and remain on-distribution, the API may:

- Strip thinking blocks from the conversation when they would create an invalid turn structure
- Disable thinking for the current request when the conversation history is incompatible with thinking being enabled

This means that attempting to toggle thinking mid-turn won't cause an error, but thinking will be silently disabled for that request. To confirm whether thinking was active, check for the presence of `thinking` blocks in the response.

#### Practical guidance

**Best practice**: Plan your thinking strategy at the start of each turn rather than trying to toggle mid-turn.

**Example: Toggling thinking after completing a turn**
```text
User: "What's the weather?"
Assistant: [tool_use] (thinking disabled)
User: [tool_result]
Assistant: [text: "It's sunny"]
User: "What about tomorrow?"
Assistant: [thinking] + [text: "..."] (thinking enabled - new turn)
```

By completing the assistant turn before toggling thinking, you ensure that thinking is actually enabled for the new request.

<Note>
Toggling thinking modes also invalidates prompt caching for message history. For more details, see the [Extended thinking with prompt caching](#extended-thinking-with-prompt-caching) section.
</Note>

<section title="Example: Passing thinking blocks with tool results">

Here's a practical example showing how to preserve thinking blocks when providing tool results:

[Code examples follow for multiple languages showing weather tool usage with thinking blocks - content truncated due to length limitations in original file]

The API response includes thinking, text, and tool_use blocks:

```json Output
{
  "content": [
    {
      "type": "thinking",
      "thinking": "The user wants to know the current weather in Paris. I have access to a function `get_weather`...",
      "signature": "BDaL4VrbR2Oj0hO4XpJxT28J5TILnCrrUXoKiiNBZW9P+nr8XSj1zuZzAl4egiCCpQNvfyUuFFJP5CncdYZEQPPmLxYsNrcs...."
    },
    {
      "type": "text",
      "text": "I can help you get the current weather information for Paris. Let me check that for you"
    },
    {
      "type": "tool_use",
      "id": "toolu_01CswdEQBMshySk6Y9DFKrfq",
      "name": "get_weather",
      "input": {
        "location": "Paris"
      }
    }
  ]
}
```

[Continuation examples follow - content truncated]

The API response now includes **only** text

```json Output
{
  "content": [
    {
      "type": "text",
      "text": "Currently in Paris, the temperature is 88°F (31°C)"
    }
  ]
}
```

</section>

### Preserving thinking blocks

During tool use, you must pass `thinking` blocks back to the API, and you must include the complete unmodified block back to the API. This is critical for maintaining the model's reasoning flow and conversation integrity.

<Tip>
While you can omit `thinking` blocks from prior `assistant` role turns, always pass back all thinking blocks to the API for any multi-turn conversation. The API:
- Automatically filters the provided thinking blocks
- Uses the relevant thinking blocks necessary to preserve the model's reasoning
- Only bills for the input tokens for the blocks shown to Claude
</Tip>

<Note>
When toggling thinking modes during a conversation, remember that the entire assistant turn (including tool use loops) must operate in a single thinking mode. For more details, see [Toggling thinking modes in conversations](#toggling-thinking-modes-in-conversations).
</Note>

When Claude invokes tools, it is pausing its construction of a response to await external information. When tool results are returned, Claude continues building that existing response. This necessitates preserving thinking blocks during tool use, for a couple of reasons:

1. **Reasoning continuity**: The thinking blocks capture Claude's step-by-step reasoning that led to tool requests. When you post tool results, including the original thinking ensures Claude can continue its reasoning from where it left off.

2. **Context maintenance**: While tool results appear as user messages in the API structure, they're part of a continuous reasoning flow. Preserving thinking blocks maintains this conceptual flow across multiple API calls. For more information on context management, see the [guide on context windows](/docs/en/build-with-claude/context-windows).

**Important**: When providing `thinking` blocks, the entire sequence of consecutive `thinking` blocks must match the outputs generated by the model during the original request; you can't rearrange or modify the sequence of these blocks.

### Interleaved thinking

Extended thinking with tool use in Claude 4 models supports interleaved thinking, which enables Claude to think between tool calls and make more sophisticated reasoning after receiving tool results.

With interleaved thinking, Claude can:
- Reason about the results of a tool call before deciding what to do next
- Chain multiple tool calls with reasoning steps in between
- Make more nuanced decisions based on intermediate results

**Model support:**
- **[Claude Mythos Preview](https://anthropic.com/glasswing)**: Interleaved thinking happens automatically. Every inter-tool reasoning step moves into a thinking block instead of plain text, and thinking blocks are preserved across turns by default. No beta header is needed or supported.
- **Claude Opus 4.7**: Interleaved thinking is automatically enabled when using [adaptive thinking](/docs/en/build-with-claude/adaptive-thinking) (the only supported thinking mode on Opus 4.7). No beta header is needed.
- **Claude Opus 4.6**: Interleaved thinking is automatically enabled when using [adaptive thinking](/docs/en/build-with-claude/adaptive-thinking). No beta header is needed. The `interleaved-thinking-2025-05-14` beta header is **deprecated** on Opus 4.6 and is safely ignored if included.
- **Claude Sonnet 4.6**: Interleaved thinking is automatically enabled when using [adaptive thinking](/docs/en/build-with-claude/adaptive-thinking) (recommended). The `interleaved-thinking-2025-05-14` beta header with manual extended thinking (`thinking: {type: "enabled"}`) is still functional but deprecated.
- **Other Claude 4 models** (Opus 4.5, Opus 4.1, Opus 4 (deprecated), Sonnet 4.5, Sonnet 4 (deprecated)): Add [the beta header](/docs/en/api/beta-headers) `interleaved-thinking-2025-05-14` to your API request to enable interleaved thinking.

Here are some important considerations for interleaved thinking:
- With interleaved thinking, the `budget_tokens` can exceed the `max_tokens` parameter, as it represents the total budget across all thinking blocks within one assistant turn.
- Interleaved thinking is only supported for [tools used via the Messages API](/docs/en/agents-and-tools/tool-use/overview).
- Direct calls to the Claude API allow you to pass `interleaved-thinking-2025-05-14` in requests to any model, with no effect (except Opus 4.7 and Opus 4.6, where it's deprecated and safely ignored).
- On 3rd-party platforms (for example, [Amazon Bedrock](/docs/en/build-with-claude/claude-on-amazon-bedrock) and [Vertex AI](/docs/en/build-with-claude/claude-on-vertex-ai)), if you pass `interleaved-thinking-2025-05-14` to any model aside from Claude Opus 4.7, Claude Opus 4.6, Claude Sonnet 4.6, Claude Opus 4.5, Claude Opus 4.1, Opus 4 (deprecated), Sonnet 4.5, or Sonnet 4 (deprecated), your request will fail.

<section title="Tool use without interleaved thinking">

Without interleaved thinking, Claude thinks once at the start of the assistant turn. Subsequent responses after tool results continue without new thinking blocks.

```text
User: "What's the total revenue if we sold 150 units at $50 each,
       and how does this compare to our average monthly revenue?"

Turn 1: [thinking] "I need to calculate 150 * $50, then check the database..."
        [tool_use: calculator] { "expression": "150 * 50" }
  ↓ tool result: "7500"

Turn 2: [tool_use: database_query] { "query": "SELECT AVG(revenue)..." }
        ↑ no thinking block
  ↓ tool result: "5200"

Turn 3: [text] "The total revenue is $7,500, which is 44% above your
        average monthly revenue of $5,200."
        ↑ no thinking block
```

</section>

<section title="Tool use with interleaved thinking">

With interleaved thinking enabled, Claude can think after receiving each tool result, allowing it to reason about intermediate results before continuing.

```text
User: "What's the total revenue if we sold 150 units at $50 each,
       and how does this compare to our average monthly revenue?"

Turn 1: [thinking] "I need to calculate 150 * $50 first..."
        [tool_use: calculator] { "expression": "150 * 50" }
  ↓ tool result: "7500"

Turn 2: [thinking] "Got $7,500. Now I should query the database to compare..."
        [tool_use: database_query] { "query": "SELECT AVG(revenue)..." }
        ↑ thinking after receiving calculator result
  ↓ tool result: "5200"

Turn 3: [thinking] "$7,500 vs $5,200 average - that's a 44% increase..."
        [text] "The total revenue is $7,500, which is 44% above your
        average monthly revenue of $5,200."
        ↑ thinking before final answer
```

</section>

## Extended thinking with prompt caching

[Prompt caching](/docs/en/build-with-claude/prompt-caching) with thinking has several important considerations:

<Tip>
Extended thinking tasks often take longer than 5 minutes to complete. Consider using the [1-hour cache duration](/docs/en/build-with-claude/prompt-caching#1-hour-cache-duration) to maintain cache hits across longer thinking sessions and multi-step workflows.
</Tip>

**Thinking block context removal**
- Thinking blocks from previous turns are removed from context, which can affect cache breakpoints
- When continuing conversations with tool use, thinking blocks are cached and count as input tokens when read from cache
- This creates a tradeoff: while thinking blocks don't consume context window space visually, they still count toward your input token usage when cached
- If thinking becomes disabled and you pass thinking content in the current tool use turn, the thinking content will be stripped and thinking will remain disabled for that request

**Cache invalidation patterns**
- Changes to thinking parameters (enabled/disabled or budget allocation) invalidate message cache breakpoints
- [Interleaved thinking](#interleaved-thinking) amplifies cache invalidation, as thinking blocks can occur between multiple [tool calls](#extended-thinking-with-tool-use)
- System prompts and tools remain cached despite thinking parameter changes or block removal

<Note>
While thinking blocks are removed for caching and context calculations, they must be preserved when continuing conversations with [tool use](#extended-thinking-with-tool-use), especially with [interleaved thinking](#interleaved-thinking).
</Note>

### Understanding thinking block caching behavior

When using extended thinking with tool use, thinking blocks exhibit specific caching behavior that affects token counting:

**How it works:**

1. Caching only occurs when you make a subsequent request that includes tool results
2. When the subsequent request is made, the previous conversation history (including thinking blocks) can be cached
3. These cached thinking blocks count as input tokens in your usage metrics when read from the cache
4. When a non-tool-result user block is included, all previous thinking blocks are ignored and stripped from context

**Detailed example flow:**

**Request 1:**
```text
User: "What's the weather in Paris?"
```
**Response 1:**
```text
[thinking_block_1] + [tool_use block 1]
```

**Request 2:**
```text
User: ["What's the weather in Paris?"],
Assistant: [thinking_block_1] + [tool_use block 1],
User: [tool_result_1, cache=True]
```
**Response 2:**
```text
[thinking_block_2] + [text block 2]
```
Request 2 writes a cache of the request content (not the response). The cache includes the original user message, the first thinking block, tool use block, and the tool result.

**Request 3:**
```text
User: ["What's the weather in Paris?"],
Assistant: [thinking_block_1] + [tool_use block 1],
User: [tool_result_1, cache=True],
Assistant: [thinking_block_2] + [text block 2],
User: [Text response, cache=True]
```
For Claude Opus 4.5 and later (including Claude Opus 4.6), all previous thinking blocks are kept by default. For older models, because a non-tool-result user block was included, all previous thinking blocks are ignored. This request will be processed the same as:
```text
User: ["What's the weather in Paris?"],
Assistant: [tool_use block 1],
User: [tool_result_1, cache=True],
Assistant: [text block 2],
User: [Text response, cache=True]
```

**Key points:**
- This caching behavior happens automatically, even without explicit `cache_control` markers
- This behavior is consistent whether using regular thinking or interleaved thinking

<section title="System prompt caching (preserved when thinking changes)">

[Extensive code examples follow for multiple languages - truncated due to length]

</section>

## Differences in thinking across model versions

[This section appears to be referenced but is truncated in the provided content]

---

**[Content truncated here - the page continues but exceeds the context window. The final sections about differences across model versions and additional details on thinking encryption and other advanced topics are not fully included in this response.]**
