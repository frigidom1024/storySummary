import asyncio
import os
import json
import traceback

os.environ['DEEPSEEK_API_KEY'] = 'sk-4ff06504656a45c9b4b60adfdaa16d5c'
os.environ['DEEPSEEK_API_BASE'] = 'https://api.deepseek.com/v1'

from src.writing.agents.style import StyleLearningAgent

async def test():
    try:
        agent = StyleLearningAgent(debug_mode=True)
        with open('samples/product/《神的九十亿个名字》.txt', 'r', encoding='utf-8') as f:
            script = f.read()
        print(f'Script length: {len(script)} chars')
        profile = await agent.learn_profile(script)

        result = {
            'structure_style': profile.structure_style,
            'narrative_style': profile.narrative_style,
            'intro_style': profile.intro_style,
            'reflection_style': profile.reflection_style,
        }

        os.makedirs('output', exist_ok=True)
        with open('output/style_test_result.json', 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print('Done - saved to output/style_test_result.json')
    except Exception as e:
        with open('output/error.log', 'w', encoding='utf-8') as f:
            f.write(traceback.format_exc())
        import sys
        print(f'Error: {e}', file=sys.stderr)
        raise

if __name__ == '__main__':
    asyncio.run(test())