import { describe, expect, it, vi } from 'vitest';

vi.mock('../src/db/db', () => ({ db: {} }));

import { getTools } from '../src/agents/tools';

describe('eval agent tools', () => {
	it('drops only the excluded built-in tools', async () => {
		const allTools = Object.keys(await getTools(null, {}, {}));
		const evalTools = Object.keys(await getTools(null, {}, { excludeBuiltinTools: ['story'] }));

		expect(allTools).toContain('story');
		expect(evalTools).not.toContain('story');
		expect(evalTools.sort()).toEqual(allTools.filter((name) => name !== 'story').sort());
	});
});
