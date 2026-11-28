import type { LlmSelectedModel } from '@nao/shared/types';
import { z } from 'zod/v4';

import type { App } from '../app';
import { noProjectMessage } from '../env';
import { authMiddleware } from '../middleware/auth';
import { retrieveProjectById } from '../queries/project.queries';
import { defaultAgentToolsExcluding } from '../services/agent';
import { describeEvalEnvironment } from '../services/eval-environment.service';
import { TestAgentService, testAgentService } from '../services/test-agent.service';
import { llmSelectedModelSchema } from '../types/llm';

/** Stories are saved against the chat, and eval runs use a temporary chat that is never persisted. */
const EVAL_EXCLUDED_TOOLS = ['story'];

export const evalsRoutes = async (app: App) => {
	app.addHook('preHandler', authMiddleware);

	app.get('/environment', async (request, reply) => {
		const projectId = request.project?.id;
		if (!projectId) {
			return reply.status(400).send({ error: noProjectMessage() });
		}

		const project = await retrieveProjectById(projectId);
		if (!project.path) {
			return reply.status(400).send({ error: 'The project has no local folder to describe.' });
		}

		const environment = await describeEvalEnvironment(project.path, {
			projectFolder: project.path,
			chatId: '',
			userId: request.user.id,
			projectId,
			supportsCustomCharts: false,
			agentSettings: null,
			envVars: {},
			azureAccessToken: null,
			queryResults: new Map(),
			generatedArtifacts: { charts: [], maps: [], stories: [] },
		});
		return reply.send(environment);
	});

	app.post(
		'/chat',
		{
			schema: {
				body: z.object({
					input: z.string(),
					model: llmSelectedModelSchema.optional(),
				}),
			},
		},
		async (request, reply) => {
			const projectId = request.project?.id;
			if (!projectId) {
				return reply.status(400).send({ error: noProjectMessage() });
			}

			try {
				const { input, model } = request.body;
				const resolvedModel = await testAgentService.resolveModelSelection(
					projectId,
					model as LlmSelectedModel | undefined,
				);
				const result = await testAgentService.runTest(
					projectId,
					input,
					resolvedModel,
					undefined,
					defaultAgentToolsExcluding(EVAL_EXCLUDED_TOOLS),
				);
				const toolResults = TestAgentService.extractToolCalls(result).map(
					({ toolName, toolCallId, args, result: output }) => ({ toolName, toolCallId, args, output }),
				);

				return reply.send({
					text: result.text,
					model: resolvedModel,
					tool_results: toolResults,
					usage: result.usage,
					cost: result.cost,
					duration_ms: result.durationMs,
					run_context: {
						system_prompt: result.runContext.systemPrompt,
						memory_count: result.runContext.memoryCount,
						tools: result.runContext.tools,
						call_settings: result.runContext.callSettings,
					},
				});
			} catch (err) {
				const message = err instanceof Error ? err.message : 'Unknown error';
				return reply.status(500).send({ error: message });
			}
		},
	);
};
