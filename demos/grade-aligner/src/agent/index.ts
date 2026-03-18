import Anthropic from '@anthropic-ai/sdk';
import { TextComplexityEvaluator, GradeLevelAppropriatenessEvaluator } from '@learning-commons/evaluators';
import { ALL_TOOLS } from './tools.js';
import { SYSTEM_PROMPT, buildUserPrompt } from './prompts.js';
import { AgentLogger } from './logger.js';
import type { AgentConfig, AlignmentIteration, AlignmentResult } from './types.js';
import { gradeToBand } from './types.js';

const SUPPORTED_GRADES = new Set(['3', '4', '5', '6', '7', '8', '9', '10', '11', '12']);

// Local state threaded through tool execution within a single align() call
interface RunState {
  iterations: AlignmentIteration[];
  aligned: { text: string; rationale: string } | null;
  originalGlaBand: string | null;
}

export class GradeAlignerAgent {
  private client: Anthropic;
  private complexityEvaluator: TextComplexityEvaluator;
  private glaEvaluator: GradeLevelAppropriatenessEvaluator;
  private logger: AgentLogger;
  private model: string;
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
    this.model = config.model ?? 'claude-opus-4-6';
    this.maxTurns = config.maxTurns ?? 10;
    this.logPath = this.logger.logPath;
  }

  async align(text: string, grade: string): Promise<AlignmentResult> {
    if (!text.trim()) {
      throw new Error('text must not be empty');
    }
    if (!SUPPORTED_GRADES.has(grade)) {
      throw new Error(`Grade must be one of: ${[...SUPPORTED_GRADES].join(', ')}`);
    }

    const { logger } = this;
    const targetBand = gradeToBand(parseInt(grade, 10));
    const runStart = Date.now();

    logger.divider();
    logger.info(`Grade Aligner  ·  target grade ${grade} (${targetBand})  ·  source text ${text.length} chars`);
    logger.divider();

    const messages: Anthropic.MessageParam[] = [
      { role: 'user', content: buildUserPrompt(text, grade, targetBand) },
    ];

    const state: RunState = { iterations: [], aligned: null, originalGlaBand: null };
    let turns = 0;
    let totalToolCalls = 0;

    while (turns < this.maxTurns) {
      turns++;
      logger.turn(turns);

      const response = await this.client.messages.create({
        model: this.model,
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
            const content = await this.executeTool(toolUse, state);
            return { type: 'tool_result', tool_use_id: toolUse.id, content };
          } catch (error) {
            const message = error instanceof Error ? error.message : String(error);
            logger.toolCallError(toolUse.name, 0, message);
            return { type: 'tool_result', tool_use_id: toolUse.id, content: `Error: ${message}`, is_error: true };
          }
        }),
      );

      messages.push({ role: 'user', content: toolResults });

      if (state.aligned !== null) {
        logger.info('Aligned text submitted — wrapping up');
        break;
      }
    }

    logger.summary(turns, totalToolCalls, Date.now() - runStart);
    logger.close();

    if (state.aligned === null) {
      throw new Error('Agent did not produce an aligned text within the turn limit');
    }
    if (state.originalGlaBand === null) {
      throw new Error('Agent never called evaluate_grade_level — cannot determine original grade band');
    }

    const finalGlaBand = state.iterations.length > 0
      ? state.iterations[state.iterations.length - 1].glaBand
      : state.originalGlaBand;

    return {
      originalText: text,
      targetGrade: grade,
      originalGlaBand: state.originalGlaBand,
      finalGlaBand,
      alignedText: state.aligned.text,
      rationale: state.aligned.rationale,
      iterations: state.iterations,
    };
  }

  private async executeTool(toolUse: Anthropic.ToolUseBlock, state: RunState): Promise<string> {
    switch (toolUse.name) {
      case 'evaluate_text_complexity': {
        const { text, grade } = toolUse.input as { text: string; grade: string };
        return this.runComplexityEval(text, grade);
      }

      case 'evaluate_grade_level': {
        const { text } = toolUse.input as { text: string };
        const result = await this.runGlaEval(text);
        state.originalGlaBand ??= result.gradeBand;
        return JSON.stringify(result);
      }

      case 'record_iteration': {
        const { text, gla_band, reasoning } = toolUse.input as { text: string; gla_band: string; reasoning: string };
        const n = state.iterations.length + 1;
        this.logger.iteration(n, gla_band, text, reasoning);
        state.iterations.push({ text, glaBand: gla_band, reasoning });
        return JSON.stringify({ recorded: true, iterationNumber: n });
      }

      case 'submit_aligned_text': {
        const { text, rationale } = toolUse.input as { text: string; rationale: string };
        this.logger.aligned(text.length);
        this.logger.alignedText('aligned', text, rationale);
        state.aligned = { text, rationale };
        return JSON.stringify({ accepted: true });
      }

      default:
        throw new Error(`Unknown tool: ${toolUse.name}`);
    }
  }

  private async runComplexityEval(text: string, grade: string): Promise<string> {
    const t0 = Date.now();
    this.logger.toolCallStart('evaluate_text_complexity', grade, text.length);

    const result = await this.complexityEvaluator.evaluate(text, grade);
    const vocab = result.vocabulary;
    const sentence = result.sentenceStructure;
    const vocabScore = 'score' in vocab ? vocab.score : 'error';
    const sentenceScore = 'score' in sentence ? sentence.score : 'error';

    this.logger.toolCallEnd('evaluate_text_complexity', Date.now() - t0, `grade=${grade}  vocab: ${vocabScore}  sentence: ${sentenceScore}`);

    return JSON.stringify({
      grade,
      vocabulary: { score: vocabScore, reasoning: 'reasoning' in vocab ? vocab.reasoning : String(vocab.error) },
      sentenceStructure: { score: sentenceScore, reasoning: 'reasoning' in sentence ? sentence.reasoning : String(sentence.error) },
    });
  }

  private async runGlaEval(text: string): Promise<{ gradeBand: string; reasoning: string }> {
    const t0 = Date.now();
    this.logger.toolCallStart('evaluate_grade_level', undefined, text.length);

    const result = await this.glaEvaluator.evaluate(text);

    this.logger.toolCallEnd('evaluate_grade_level', Date.now() - t0, `band: ${result.score}`);
    return { gradeBand: result.score, reasoning: result.reasoning };
  }
}
