import { execFile } from 'node:child_process';
import { createHash } from 'node:crypto';
import fs from 'node:fs/promises';
import path from 'node:path';
import { promisify } from 'node:util';

import { executeQuery } from '../agents/tools/execute-sql';
import { env } from '../env';
import type { ToolContext } from '../types/tools';
import { extractConfiguredDatabases, readProjectContext } from '../utils/nao-config';

const execFileAsync = promisify(execFile);
const EXCLUDED_TOP_LEVEL_FOLDERS = new Set(['tests']);
const FINGERPRINTED_DATABASE_TYPES = new Set(['duckdb']);

export interface EvalEnvironment {
	nao: Revision & { version: string };
	context: { sha256: string; files: ContextFile[] };
	repos: (Revision & { name: string })[];
	data: DatabaseFingerprint[];
}

interface Revision {
	commit: string | null;
	dirty: boolean | null;
}

interface ContextFile {
	path: string;
	sha256: string;
}

interface DatabaseFingerprint {
	databaseId: string;
	tables: TableFingerprint[];
	error?: string;
}

interface TableFingerprint {
	table: string;
	rowCount: string;
	checksum: string;
}

/**
 * Identifies everything a run depends on besides the question: the code, the project files the
 * agent can read, the linked repos, and the warehouse contents. `tests/` is excluded because the
 * eval dataset is fingerprinted separately and outputs change during a run.
 */
export async function describeEvalEnvironment(
	projectFolder: string,
	toolContext: ToolContext,
): Promise<EvalEnvironment> {
	const [nao, context, repos, data] = await Promise.all([
		describeNaoRevision(),
		fingerprintContext(projectFolder),
		describeRepoRevisions(projectFolder),
		fingerprintDatabases(projectFolder, toolContext),
	]);
	return { nao, context, repos, data };
}

async function describeNaoRevision(): Promise<EvalEnvironment['nao']> {
	if (env.APP_COMMIT !== 'unknown') {
		return { version: env.APP_VERSION, commit: env.APP_COMMIT, dirty: null };
	}
	return { version: env.APP_VERSION, ...(await readGitRevision(process.cwd())) };
}

async function fingerprintContext(projectFolder: string): Promise<EvalEnvironment['context']> {
	const paths = await listContextFiles(projectFolder);
	const files = await Promise.all(
		paths.map(async (relativePath) => ({
			path: relativePath,
			sha256: sha256(await fs.readFile(path.join(projectFolder, relativePath))),
		})),
	);
	const manifest = files.map((file) => `${file.path}\t${file.sha256}\n`).join('');
	return { sha256: sha256(manifest), files };
}

async function listContextFiles(projectFolder: string, relativeFolder = ''): Promise<string[]> {
	const entries = await fs.readdir(path.join(projectFolder, relativeFolder), { withFileTypes: true });
	const nested = await Promise.all(
		entries
			.filter((entry) => isContextEntry(entry, relativeFolder))
			.map(async (entry) => {
				const relativePath = path.posix.join(relativeFolder, entry.name);
				return entry.isDirectory() ? listContextFiles(projectFolder, relativePath) : [relativePath];
			}),
	);
	return nested.flat().sort();
}

function isContextEntry(entry: { name: string; isFile(): boolean; isDirectory(): boolean }, relativeFolder: string) {
	if (entry.name.startsWith('.')) {
		return false;
	}
	if (relativeFolder === '' && EXCLUDED_TOP_LEVEL_FOLDERS.has(entry.name)) {
		return false;
	}
	return entry.isFile() || entry.isDirectory();
}

async function describeRepoRevisions(projectFolder: string): Promise<EvalEnvironment['repos']> {
	const { repos } = readProjectContext(projectFolder);
	return Promise.all(
		repos
			.filter((repo) => repo.localPath)
			.map(async (repo) => ({
				name: repo.name,
				...(await readGitRevision(path.resolve(projectFolder, repo.localPath!))),
			})),
	);
}

async function readGitRevision(folder: string): Promise<Revision> {
	const git = (...args: string[]) => execFileAsync('git', ['-c', 'safe.directory=*', '-C', folder, ...args]);
	try {
		const [{ stdout: commit }, { stdout: status }] = await Promise.all([
			git('rev-parse', 'HEAD'),
			git('status', '--porcelain'),
		]);
		return { commit: commit.trim(), dirty: status.trim() !== '' };
	} catch {
		return { commit: null, dirty: null };
	}
}

async function fingerprintDatabases(projectFolder: string, toolContext: ToolContext): Promise<DatabaseFingerprint[]> {
	const databases = extractConfiguredDatabases(projectFolder).filter(
		(database) => database.type && FINGERPRINTED_DATABASE_TYPES.has(database.type),
	);
	return Promise.all(databases.map((database) => fingerprintDatabase(database.id, toolContext)));
}

async function fingerprintDatabase(databaseId: string, toolContext: ToolContext): Promise<DatabaseFingerprint> {
	try {
		const tables = await listTables(databaseId, toolContext);
		const fingerprints = [];
		for (const table of tables) {
			fingerprints.push(await fingerprintTable(databaseId, table, toolContext));
		}
		return { databaseId, tables: fingerprints };
	} catch (error) {
		return { databaseId, tables: [], error: error instanceof Error ? error.message : String(error) };
	}
}

async function listTables(databaseId: string, toolContext: ToolContext): Promise<string[]> {
	const result = await executeQuery(
		{
			database_id: databaseId,
			sql_query: `SELECT table_catalog, table_schema, table_name FROM information_schema.tables
				WHERE table_type = 'BASE TABLE' AND table_schema NOT IN ('information_schema', 'pg_catalog')
				ORDER BY 1, 2, 3`,
		},
		toolContext,
	);
	return result.data.map((row) =>
		[row.table_catalog, row.table_schema, row.table_name].map((part) => quoteIdentifier(String(part))).join('.'),
	);
}

/** Sums a hash of every row, so the checksum ignores row order and file layout but changes with any value. */
async function fingerprintTable(
	databaseId: string,
	table: string,
	toolContext: ToolContext,
): Promise<TableFingerprint> {
	const result = await executeQuery(
		{
			database_id: databaseId,
			sql_query: `SELECT COUNT(*)::VARCHAR AS row_count, COALESCE(SUM(hash(t)::HUGEINT), 0)::VARCHAR AS checksum FROM ${table} t`,
		},
		toolContext,
	);
	const [row] = result.data;
	return { table, rowCount: String(row.row_count), checksum: String(row.checksum) };
}

function quoteIdentifier(identifier: string): string {
	return `"${identifier.replaceAll('"', '""')}"`;
}

function sha256(content: string | Buffer): string {
	return createHash('sha256').update(content).digest('hex');
}
