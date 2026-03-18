import { createWriteStream, mkdirSync } from 'fs';
import type { WriteStream } from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const LOGS_DIR = path.resolve(__dirname, '../../logs');

// ─── ANSI colours (console only) ─────────────────────────────────────────────
const C = {
  reset:   '\x1b[0m',
  dim:     '\x1b[2m',
  bold:    '\x1b[1m',
  cyan:    '\x1b[36m',
  yellow:  '\x1b[33m',
  green:   '\x1b[32m',
  red:     '\x1b[31m',
  blue:    '\x1b[34m',
  magenta: '\x1b[35m',
};

function ts(): string {
  return new Date().toISOString().replace('T', ' ').substring(0, 19);
}

function strip(text: string): string {
  // eslint-disable-next-line no-control-regex
  return text.replace(/\x1b\[[0-9;]*m/g, '');
}

export class AgentLogger {
  private stream: WriteStream;
  readonly logPath: string;

  constructor() {
    mkdirSync(LOGS_DIR, { recursive: true });
    const stamp = new Date().toISOString().replace(/[:.]/g, '-').substring(0, 19);
    this.logPath = path.join(LOGS_DIR, `run-${stamp}.log`);
    this.stream = createWriteStream(this.logPath, { flags: 'a' });
    this.raw(`Agent run started — ${new Date().toISOString()}\n${'═'.repeat(72)}\n`);
  }

  // ─── Core write ────────────────────────────────────────────────────────────

  private write(consoleText: string, fileText?: string): void {
    process.stdout.write(consoleText);
    this.stream.write(strip(fileText ?? consoleText));
  }

  private raw(text: string): void {
    this.stream.write(text);
  }

  // ─── Public API ────────────────────────────────────────────────────────────

  divider(): void {
    this.write(
      `${C.dim}${'─'.repeat(72)}${C.reset}\n`,
      `${'─'.repeat(72)}\n`,
    );
  }

  turn(n: number): void {
    const line = `\n[${ts()}] ${C.bold}${'─'.repeat(20)} TURN ${n} ${'─'.repeat(20)}${C.reset}\n`;
    this.write(line, `\n[${ts()}] ${'─'.repeat(20)} TURN ${n} ${'─'.repeat(20)}\n`);
  }

  thinking(text: string): void {
    const indented = text.trim().split('\n').map(l => `    ${l}`).join('\n');
    this.write(
      `[${ts()}] ${C.magenta}[THINKING]${C.reset}\n${C.dim}${indented}${C.reset}\n`,
      `[${ts()}] [THINKING]\n${indented}\n`,
    );
  }

  claude(text: string): void {
    const indented = text.trim().split('\n').map(l => `  ${l}`).join('\n');
    this.write(
      `[${ts()}] ${C.blue}[CLAUDE]${C.reset}\n${indented}\n`,
      `[${ts()}] [CLAUDE]\n${indented}\n`,
    );
  }

  toolCallStart(name: string, grade?: string, textLength?: number): void {
    const args = [grade && `grade=${grade}`, textLength && `len=${textLength}`].filter(Boolean).join(', ');
    this.write(
      `[${ts()}]   ${C.yellow}→ ${name}${C.reset}(${args})\n`,
      `[${ts()}]   → ${name}(${args})\n`,
    );
  }

  toolCallEnd(name: string, durationMs: number, summary: string): void {
    this.write(
      `[${ts()}]   ${C.green}✓ ${name}${C.reset} ${C.dim}[${(durationMs / 1000).toFixed(1)}s]${C.reset}  ${summary}\n`,
      `[${ts()}]   ✓ ${name} [${(durationMs / 1000).toFixed(1)}s]  ${summary}\n`,
    );
  }

  toolCallError(name: string, durationMs: number, error: string): void {
    this.write(
      `[${ts()}]   ${C.red}✗ ${name}${C.reset} ${C.dim}[${(durationMs / 1000).toFixed(1)}s]${C.reset}  ERROR: ${error}\n`,
      `[${ts()}]   ✗ ${name} [${(durationMs / 1000).toFixed(1)}s]  ERROR: ${error}\n`,
    );
  }

  iteration(n: number, glaBand: string, text: string, reasoning: string): void {
    this.write(
      `[${ts()}]   ${C.cyan}${C.bold}● ITERATION ${n}${C.reset} ${C.dim}band: ${glaBand}${C.reset}\n`,
      `[${ts()}]   ● ITERATION ${n}  band: ${glaBand}\n`,
    );
    const header = `\n${'═'.repeat(72)}\n  ITERATION ${n}  (band: ${glaBand})\n${'═'.repeat(72)}`;
    this.raw(`${header}\n\n${text}\n\nReasoning: ${reasoning}\n`);
  }

  aligned(chars: number): void {
    this.write(
      `[${ts()}]   ${C.green}${C.bold}✔ ALIGNED${C.reset}  ${chars} chars\n`,
      `[${ts()}]   ✔ ALIGNED  ${chars} chars\n`,
    );
  }

  alignedText(grade: string, text: string, rationale: string): void {
    const header = `\n${'═'.repeat(72)}\n  ALIGNED TEXT  (grade ${grade})\n${'═'.repeat(72)}`;
    this.raw(`${header}\n\n${text}\n\nRationale: ${rationale}\n`);
  }

  info(message: string): void {
    this.write(
      `[${ts()}] ${C.dim}${message}${C.reset}\n`,
      `[${ts()}] ${message}\n`,
    );
  }

  warn(message: string): void {
    this.write(
      `[${ts()}] ${C.yellow}[WARN]${C.reset} ${message}\n`,
      `[${ts()}] [WARN] ${message}\n`,
    );
  }

  error(message: string): void {
    this.write(
      `[${ts()}] ${C.red}[ERROR]${C.reset} ${message}\n`,
      `[${ts()}] [ERROR] ${message}\n`,
    );
  }

  summary(totalTurns: number, totalTools: number, durationMs: number): void {
    const line = [
      `\n[${ts()}] ${'═'.repeat(72)}`,
      `[${ts()}] Run complete — ${totalTurns} turns · ${totalTools} tool calls · ${(durationMs / 1000).toFixed(1)}s`,
      `[${ts()}] Log written to: ${this.logPath}`,
      `[${ts()}] ${'═'.repeat(72)}\n`,
    ].join('\n');
    this.write(
      line.replace(/(\[.*?\])/g, `${C.dim}$1${C.reset}`),
      line,
    );
  }

  close(): void {
    this.stream.end();
  }
}
