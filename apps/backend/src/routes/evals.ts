import type { LlmSelectedModel } from '@nao/shared/types';
import { z } from 'zod/v4';

import type { App } from '../app';
import { noProjectMessage } from '../env';
import { authMiddleware } from '../middleware/auth';
import { TestAgentService, testAgentService } from '../services/test-agent.service';
import { llmSelectedModelSchema } from '../types/llm';

const CONTEXT_TOOLS = new Set(['execute_sql', 'read', 'grep']);

export const evalsRoutes = async (app: App) => {
	app.addHook('preHandler', authMiddleware);

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
				const modelSelection = model as LlmSelectedModel | undefined;
				const resolvedModelId =
					model?.modelId ?? (await testAgentService.resolveModelSelection(projectId)).modelId;
				const result = await testAgentService.runTest(projectId, input, modelSelection);
				const toolResults = TestAgentService.extractToolCalls(result)
					.filter((tc) => CONTEXT_TOOLS.has(tc.toolName))
					.map(({ toolName, args, result: output }) => ({ toolName, args, output }));

				return reply.send({
					text: result.text,
					model_id: resolvedModelId,
					tool_results: toolResults,
				});
			} catch (err) {
				const message = err instanceof Error ? err.message : 'Unknown error';
				return reply.status(500).send({ error: message });
			}
		},
	);
};
