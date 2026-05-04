#!/usr/bin/env python3
"""Strip noise from a Claude Code session JSONL, preserving full conversation signal."""

import json
import sys
from collections import defaultdict

def strip_session(input_path, output_path):
    messages = []
    with open(input_path) as f:
        for line in f:
            try:
                messages.append(json.loads(line))
            except:
                continue

    # Extract session metadata from first record that has it
    session_meta = {}
    for m in messages:
        if m.get('sessionId') and not session_meta:
            session_meta = {
                'sessionId': m.get('sessionId'),
                'cwd': m.get('cwd'),
                'version': m.get('version'),
                'gitBranch': m.get('gitBranch'),
            }
            break

    # Build tool_use_id -> tool info map from assistant messages
    tool_map = {}
    for m in messages:
        if m.get('type') != 'assistant':
            continue
        msg = m.get('message', {})
        if not isinstance(msg, dict):
            continue
        content = msg.get('content', [])
        if not isinstance(content, list):
            continue
        for block in content:
            if isinstance(block, dict) and block.get('type') == 'tool_use':
                tool_map[block.get('id', '')] = {
                    'name': block.get('name', ''),
                    'input': block.get('input', {}),
                }

    # Collect subagent prompts from progress records before discarding them
    subagent_prompts = {}
    for m in messages:
        if m.get('type') == 'progress':
            data = m.get('data', {})
            prompt = data.get('prompt')
            agent_id = data.get('agentId')
            if prompt and agent_id and agent_id not in subagent_prompts:
                subagent_prompts[agent_id] = prompt[:500]

    output = []

    # Session header
    output.append({
        'type': 'session_metadata',
        **session_meta,
        'subagent_tasks': subagent_prompts,
    })

    for m in messages:
        mtype = m.get('type')

        # Keep system records (turn_duration)
        if mtype == 'system':
            output.append({
                'type': 'system',
                'subtype': m.get('subtype'),
                'durationMs': m.get('durationMs'),
                'timestamp': m.get('timestamp'),
            })
            continue

        # Skip noise record types entirely
        if mtype in ('progress', 'file-history-snapshot', 'last-prompt'):
            continue

        if mtype == 'user' and 'uuid' in m:
            msg = m.get('message', {})
            if not isinstance(msg, dict):
                continue
            content = msg.get('content', '')

            # Process content blocks
            if isinstance(content, list):
                cleaned_blocks = []
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    if block.get('type') == 'text':
                        cleaned_blocks.append(block)
                    elif block.get('type') == 'tool_result':
                        # Smart filter tool results
                        tool_id = block.get('tool_use_id', '')
                        tool_info = tool_map.get(tool_id, {'name': 'unknown', 'input': {}})
                        tool_name = tool_info['name']
                        tool_input = tool_info['input']

                        result_content = block.get('content', '')
                        if isinstance(result_content, list):
                            for sub in result_content:
                                if isinstance(sub, dict) and sub.get('type') == 'text':
                                    result_content = sub.get('text', '')
                                    break
                            else:
                                result_content = json.dumps(result_content)

                        is_error = block.get('is_error', False)

                        if is_error:
                            # Keep errors fully
                            filtered = str(result_content)
                        elif tool_name in ('Read', 'Glob', 'Grep'):
                            fp = tool_input.get('file_path', tool_input.get('pattern', tool_input.get('path', '')))
                            line_count = str(result_content).count('\n')
                            filtered = f'[{tool_name}: {fp} — {line_count} lines]'
                        elif tool_name == 'Bash':
                            text = str(result_content)
                            if len(text) > 500:
                                filtered = text[:500] + f'\n[...truncated, {len(text)} chars total]'
                            else:
                                filtered = text
                        else:
                            text = str(result_content)
                            if len(text) > 500:
                                filtered = text[:500] + f'\n[...truncated, {len(text)} chars total]'
                            else:
                                filtered = text

                        cleaned_blocks.append({
                            'type': 'tool_result',
                            'tool_use_id': tool_id,
                            'tool_name': tool_name,
                            'is_error': is_error,
                            'content': filtered,
                        })
                    elif block.get('type') == 'tool_reference':
                        cleaned_blocks.append(block)
                content = cleaned_blocks
            elif isinstance(content, str):
                content = content

            record = {
                'type': 'user',
                'timestamp': m.get('timestamp'),
                'uuid': m.get('uuid'),
                'parentUuid': m.get('parentUuid'),
                'content': content,
            }
            # Flag permission mode changes
            if m.get('permissionMode'):
                record['permissionMode'] = m['permissionMode']
            if m.get('isMeta'):
                record['isMeta'] = True

            output.append(record)

        elif mtype == 'assistant' and 'uuid' in m:
            msg = m.get('message', {})
            if not isinstance(msg, dict):
                continue
            content = msg.get('content', [])

            cleaned_blocks = []
            if isinstance(content, list):
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    if block.get('type') == 'text' and block.get('text', '').strip():
                        cleaned_blocks.append({'type': 'text', 'text': block['text']})
                    elif block.get('type') == 'tool_use':
                        inp = block.get('input', {})
                        summary = {'type': 'tool_use', 'name': block.get('name', '')}
                        name = block['name']
                        if name in ('Read', 'Edit', 'Write'):
                            summary['file_path'] = inp.get('file_path', '')
                        elif name == 'Bash':
                            summary['command'] = inp.get('command', '')[:200]
                        elif name == 'Grep':
                            summary['pattern'] = inp.get('pattern', '')
                            summary['path'] = inp.get('path', '')
                        elif name == 'Glob':
                            summary['pattern'] = inp.get('pattern', '')
                        elif name == 'Agent':
                            summary['prompt'] = inp.get('prompt', '')[:300]
                        elif name == 'WebSearch':
                            summary['query'] = inp.get('query', '')
                        elif name == 'WebFetch':
                            summary['url'] = inp.get('url', '')
                        elif name in ('AskUserQuestion',):
                            summary['question'] = inp.get('question', '')[:300]
                        summary['id'] = block.get('id', '')
                        cleaned_blocks.append(summary)
                    # Skip thinking blocks entirely

            record = {
                'type': 'assistant',
                'timestamp': m.get('timestamp'),
                'uuid': m.get('uuid'),
                'parentUuid': m.get('parentUuid'),
                'content': cleaned_blocks,
            }
            # Include error info if present
            if m.get('error'):
                record['error'] = m['error']
            if m.get('isApiErrorMessage'):
                record['isApiErrorMessage'] = True

            output.append(record)

    with open(output_path, 'w') as f:
        for record in output:
            f.write(json.dumps(record) + '\n')

    return len(messages), len(output)

if __name__ == '__main__':
    input_path = sys.argv[1]
    output_path = sys.argv[2]
    orig, stripped = strip_session(input_path, output_path)
    import os
    orig_size = os.path.getsize(input_path)
    new_size = os.path.getsize(output_path)
    print(f'Records: {orig} -> {stripped}')
    print(f'Size: {orig_size/1024:.1f}KB -> {new_size/1024:.1f}KB ({(1-new_size/orig_size)*100:.1f}% reduction)')
