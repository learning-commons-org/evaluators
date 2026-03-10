import Anthropic from '@anthropic-ai/sdk';
import { TextComplexityEvaluator, GradeLevelAppropriatenessEvaluator } from '@learning-commons/evaluators';
import { ALL_TOOLS } from './tools.js';
import { SYSTEM_PROMPT, buildUserPrompt } from './prompts.js';
import { AgentLogger } from './logger.js';
import type { AgentConfig, DifferentiatedSet, TextVariant, VariantLevel } from './types.js';

const SUPPORTED_GRADES = new Set(['3', '4', '5', '6', '7', '8', '9', '10', '11', '12']);

export class DifferentiationAgent {
  private client: Anthropic;
  private complexityEvaluator: TextComplexityEvaluator;
  private glaEvaluator: GradeLevelAppropriatenessEvaluator;
  private logger: AgentLogger;
  private maxTurns: number;

  readonly logPath: string;

  constructor(config: AgentConfig = {}) {
    this.client = new Anthropic({
      apiKey: config.anthropicApiKey ?? process.env.ANTHROPIC_API_KEY,
    });

    const evaluatorConfig = {
      openaiApiKey: config.openaiApiKey ?? process.env.OPENAI_API_KEY,
      googleApiKey: config.googleApiKey ?? process.env.GOOGLE_API_KEY,
      telemetry: { enabled: false },
    };

    this.complexityEvaluator = new TextComplexityEvaluator(evaluatorConfig);
    this.glaEvaluator = new GradeLevelAppropriatenessEvaluator(evaluatorConfig);
    this.logger = new AgentLogger();
    this.maxTurns = config.maxTurns ?? 40;
    this.logPath = this.logger.logPath;
  }

  async generate(text: string, grade: string): Promise<DifferentiatedSet> {
    if (!SUPPORTED_GRADES.has(grade)) {
      throw new Error(`Grade must be one of: ${[...SUPPORTED_GRADES].join(', ')}`);
    }

    const { logger } = this;
    const runStart = Date.now();

    logger.divider();
    logger.info(`Differentiation Agent  ·  target grade ${grade}  ·  source text ${text.length} chars`);
    logger.divider();

    const messages: Anthropic.MessageParam[] = [
      { role: 'user', content: buildUserPrompt(text, grade) },
    ];

    const variants = new Map<VariantLevel, TextVariant>();
    let turns = 0;
    let totalToolCalls = 0;

    while (turns < this.maxTurns) {
      turns++;
      logger.turn(turns);

      const response = await this.client.messages.create({
        model: 'claude-opus-4-6',
        max_tokens: 8192,
        thinking: { type: 'adaptive' },
        system: SYSTEM_PROMPT,
        tools: ALL_TOOLS,
        messages,
      });

      messages.push({ role: 'assistant', content: response.content });

      for (const block of response.content) {
        if (block.type === 'thinking') {
          logger.thinking(block.thinking);
        } else if (block.type === 'text' && block.text.trim()) {
          logger.claude(block.text.trim());
        }
      }

      if (response.stop_reason === 'end_turn') {
        logger.info('stop_reason: end_turn — agent finished');
        break;
      }

      if (response.stop_reason !== 'tool_use') {
        logger.warn(`Unexpected stop_reason: ${response.stop_reason}`);
        break;
      }

      const toolUseBlocks = response.content.filter(
        (b): b is Anthropic.ToolUseBlock => b.type === 'tool_use',
      );

      totalToolCalls += toolUseBlocks.length;
      logger.info(
        `Executing ${toolUseBlocks.length} tool call(s) in parallel: ${toolUseBlocks.map((b) => b.name).join(', ')}`,
      );

      const toolResults = await Promise.all(
        toolUseBlocks.map(async (toolUse): Promise<Anthropic.ToolResultBlockParam> => {
          try {
            const content = await this.executeTool(toolUse, variants);
            return { type: 'tool_result', tool_use_id: toolUse.id, content };
          } catch (error) {
            const message = error instanceof Error ? error.message : String(error);
            logger.toolCallError(toolUse.name, 0, message);
            return { type: 'tool_result', tool_use_id: toolUse.id, content: `Error: ${message}`, is_error: true };
          }
        }),
      );

      messages.push({ role: 'user', content: toolResults });

      if (variants.size === 3) {
        logger.info('All three variants submitted — wrapping up');
        break;
      }
    }

    logger.summary(turns, totalToolCalls, Date.now() - runStart);
    logger.close();

    if (variants.size < 3) {
      const missing = (['below', 'at', 'above'] as VariantLevel[]).filter((l) => !variants.has(l));
      throw new Error(`Agent did not produce all variants. Missing: ${missing.join(', ')}`);
    }

    return {
      originalText: text,
      targetGrade: grade,
      below: variants.get('below')!,
      at: variants.get('at')!,
      above: variants.get('above')!,
    };
  }

  private async executeTool(
    toolUse: Anthropic.ToolUseBlock,
    variants: Map<VariantLevel, TextVariant>,
  ): Promise<string> {
    const { logger } = this;

    switch (toolUse.name) {
      case 'evaluate_text_complexity': {
        const { text, grade } = toolUse.input as { text: string; grade: string };
        const t0 = Date.now();
        logger.toolCallStart('evaluate_text_complexity', grade, text.length);

        const result = await this.complexityEvaluator.evaluate(text, grade);
        const vocab = result.vocabulary;
        const sentence = result.sentenceStructure;
        const vocabScore = 'score' in vocab ? vocab.score : 'error';
        const sentenceScore = 'score' in sentence ? sentence.score : 'error';

        logger.toolCallEnd('evaluate_text_complexity', Date.now() - t0, `grade=${grade}  vocab: ${vocabScore}  sentence: ${sentenceScore}`);

        return JSON.stringify({
          grade,
          vocabulary: { score: vocabScore, reasoning: 'reasoning' in vocab ? vocab.reasoning : String(vocab.error) },
          sentenceStructure: { score: sentenceScore, reasoning: 'reasoning' in sentence ? sentence.reasoning : String(sentence.error) },
        });
      }

      case 'evaluate_grade_level': {
        const { text } = toolUse.input as { text: string };
        const t0 = Date.now();
        logger.toolCallStart('evaluate_grade_level', undefined, text.length);

        const result = await this.glaEvaluator.evaluate(text);

        logger.toolCallEnd('evaluate_grade_level', Date.now() - t0, `band: ${result.score}`);

        return JSON.stringify({ gradeBand: result.score, reasoning: result.reasoning });
      }

      case 'submit_variant': {
        const { level, grade, text, rationale } = toolUse.input as { level: VariantLevel; grade: string; text: string; rationale: string };

        logger.submit(level, grade, text.length);
        logger.variant(level, grade, text, rationale);

        variants.set(level, { level, grade, text, rationale });

        return JSON.stringify({ accepted: true, level, variantsRemaining: 3 - variants.size });
      }

      default:
        throw new Error(`Unknown tool: ${toolUse.name}`);
    }
  }
}
