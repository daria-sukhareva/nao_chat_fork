import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const executeQuery = vi.hoisted(() => vi.fn());
vi.mock('../src/agents/tools/execute-sql', () => ({ executeQuery }));
vi.mock('../src/db/db', () => ({ db: {} }));

import { describeEvalEnvironment } from '../src/services/eval-environment.service';
import type { ToolContext } from '../src/types/tools';

const TOOL_CONTEXT = { projectFolder: '' } as ToolContext;

let projectFolder: string;

function writeProjectFile(relativePath: string, content: string) {
	const filePath = path.join(projectFolder, relativePath);
	fs.mkdirSync(path.dirname(filePath), { recursive: true });
	fs.writeFileSync(filePath, content);
}

beforeEach(() => {
	projectFolder = fs.mkdtempSync(path.join(os.tmpdir(), 'nao-eval-env-'));
	writeProjectFile('RULES.md', 'Never say session.');
	writeProjectFile('docs/metrics_tree.md', '# tree');
	writeProjectFile('tests/evals/golden_dataset.jsonl', '{}');
	writeProjectFile('.env', 'SECRET=1');
	executeQuery.mockReset();
});

afterEach(() => {
	fs.rmSync(projectFolder, { recursive: true, force: true });
});

describe('describeEvalEnvironment context fingerprint', () => {
	it('hashes project files but skips tests and hidden files', async () => {
		const { context } = await describeEvalEnvironment(projectFolder, TOOL_CONTEXT);

		expect(context.files.map((file) => file.path)).toEqual(['RULES.md', 'docs/metrics_tree.md']);
	});

	it('changes the context hash when a file changes and keeps it otherwise', async () => {
		const before = await describeEvalEnvironment(projectFolder, TOOL_CONTEXT);
		const unchanged = await describeEvalEnvironment(projectFolder, TOOL_CONTEXT);
		writeProjectFile('RULES.md', 'Never say session.\nRead docs/metrics_tree.md.');
		const after = await describeEvalEnvironment(projectFolder, TOOL_CONTEXT);

		expect(unchanged.context.sha256).toBe(before.context.sha256);
		expect(after.context.sha256).not.toBe(before.context.sha256);
	});

	it('ignores changes to the eval dataset and outputs', async () => {
		const before = await describeEvalEnvironment(projectFolder, TOOL_CONTEXT);
		writeProjectFile('tests/outputs/evals_results.json', '{}');
		const after = await describeEvalEnvironment(projectFolder, TOOL_CONTEXT);

		expect(after.context.sha256).toBe(before.context.sha256);
	});
});

describe('describeEvalEnvironment data fingerprint', () => {
	beforeEach(() => {
		writeProjectFile(
			'nao_config.yaml',
			['databases:', '  - name: duckdb_analytics', '    type: duckdb', '    path: /data/analytics.duckdb'].join(
				'\n',
			),
		);
	});

	it('checksums every table of each DuckDB database', async () => {
		executeQuery
			.mockResolvedValueOnce({
				data: [{ table_catalog: 'analytics', table_schema: 'ANALYTICS', table_name: 'fact_visits' }],
			})
			.mockResolvedValueOnce({ data: [{ row_count: '85', checksum: '42455895469550826104' }] });

		const { data } = await describeEvalEnvironment(projectFolder, TOOL_CONTEXT);

		expect(data).toEqual([
			{
				databaseId: 'duckdb_analytics',
				tables: [
					{
						table: '"analytics"."ANALYTICS"."fact_visits"',
						rowCount: '85',
						checksum: '42455895469550826104',
					},
				],
			},
		]);
		expect(executeQuery.mock.calls[1][0].sql_query).toContain('FROM "analytics"."ANALYTICS"."fact_visits" t');
	});

	it('records a failed fingerprint instead of failing the request', async () => {
		executeQuery.mockRejectedValueOnce(new Error('database is locked'));

		const { data } = await describeEvalEnvironment(projectFolder, TOOL_CONTEXT);

		expect(data).toEqual([{ databaseId: 'duckdb_analytics', tables: [], error: 'database is locked' }]);
	});
});

describe('describeEvalEnvironment revisions', () => {
	it('reports no commit for a linked repo that is not a git checkout', async () => {
		writeProjectFile(
			'nao_config.yaml',
			['repos:', '  - name: kwwhat', `    local_path: ${projectFolder}`].join('\n'),
		);

		const { repos } = await describeEvalEnvironment(projectFolder, TOOL_CONTEXT);

		expect(repos).toEqual([{ name: 'kwwhat', commit: null, dirty: null }]);
	});

	it('reads the nao commit of the running checkout', async () => {
		const { nao } = await describeEvalEnvironment(projectFolder, TOOL_CONTEXT);

		expect(nao.commit).toMatch(/^[0-9a-f]{40}$/);
		expect(typeof nao.dirty).toBe('boolean');
	});
});
