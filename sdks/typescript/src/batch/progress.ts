import type { BatchResult } from './types.js';

/**
 * Progress tracker for batch evaluation
 */
export class ProgressTracker {
  private totalTasks: number;
  private completed = 0;
  private successful = 0;
  private failed = 0;
  private startTime: number;
  private perEvaluator = new Map<string, { completed: number; successful: number; failed: number }>();

  constructor(totalTasks: number) {
    this.totalTasks = totalTasks;
    this.startTime = Date.now();
  }

  update(result: BatchResult): void {
    this.completed++;

    if (result.status === 'success') {
      this.successful++;
    } else {
      this.failed++;
    }

    // Track per-evaluator stats
    if (!this.perEvaluator.has(result.evaluatorId)) {
      this.perEvaluator.set(result.evaluatorId, { completed: 0, successful: 0, failed: 0 });
    }

    const stats = this.perEvaluator.get(result.evaluatorId)!;
    stats.completed++;
    if (result.status === 'success') {
      stats.successful++;
    } else {
      stats.failed++;
    }
  }

  getPercentage(): number {
    return Math.round((this.completed / this.totalTasks) * 100);
  }

  getElapsedSeconds(): number {
    return Math.round((Date.now() - this.startTime) / 1000);
  }

  getEstimatedRemainingSeconds(): number {
    if (this.completed === 0) return 0;

    const elapsed = Date.now() - this.startTime;
    const avgTimePerTask = elapsed / this.completed;
    const remaining = this.totalTasks - this.completed;

    return Math.round((avgTimePerTask * remaining) / 1000);
  }

  formatElapsed(): string {
    const seconds = this.getElapsedSeconds();
    if (seconds < 60) return `${seconds}s`;

    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds}s`;
  }

  formatEstimatedRemaining(): string {
    const seconds = this.getEstimatedRemainingSeconds();
    if (seconds < 60) return `${seconds}s`;

    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds}s`;
  }

  getProgressBar(width = 20): string {
    const percentage = this.getPercentage();
    const filled = Math.round((percentage / 100) * width);
    const empty = width - filled;

    return '█'.repeat(filled) + '░'.repeat(empty);
  }

  display(): void {
    // Rewind exactly what the previous display() printed: bar, blank, timing, then one
    // line per evaluator. Adding or removing a line below means changing this count here
    // and the +1 in displaySummary(), or the redraw eats real output.
    if (this.completed > 1) {
      const linesToClear = 3 + this.perEvaluator.size;
      process.stdout.write(`\x1b[${linesToClear}A`); // Move cursor up
      process.stdout.write('\x1b[J'); // Clear from cursor to end of screen
    }

    console.log(
      `${this.getProgressBar()} ${this.getPercentage()}% (${this.completed}/${this.totalTasks})`
    );

    // Show per-evaluator progress
    for (const [evalId, stats] of this.perEvaluator.entries()) {
      const status =
        stats.completed === stats.successful
          ? '✓'
          : stats.failed > 0
            ? '✗'
            : '⏳';
      console.log(
        `  ${status} ${evalId}: ${stats.successful}/${stats.completed} successful`
      );
    }

    console.log(
      `\n⏱  Elapsed: ${this.formatElapsed()} | Estimated remaining: ${this.formatEstimatedRemaining()}`
    );
  }

  displaySummary(): void {
    // display()'s lines plus the blank line it ends on.
    const linesToClear = 3 + this.perEvaluator.size + 1;
    process.stdout.write(`\x1b[${linesToClear}A`);
    process.stdout.write('\x1b[J');

    console.log('\n✅ Batch evaluation completed!\n');
    console.log(`Total tasks: ${this.totalTasks}`);
    console.log(`Successful: ${this.successful} ✓`);
    console.log(`Failed: ${this.failed} ✗`);
    console.log(`Duration: ${this.formatElapsed()}`);

    // Show per-evaluator summary
    if (this.perEvaluator.size > 1) {
      console.log('\nResults per evaluator:');
      for (const [evalId, stats] of this.perEvaluator.entries()) {
        console.log(
          `  ${evalId}: ${stats.successful} successful, ${stats.failed} failed`
        );
      }
    }
    console.log();
  }
}
