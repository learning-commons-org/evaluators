import type { ReactElement } from 'react';
import MathStandardsAlignmentPage from './pages/MathStandardsAlignmentPage';

// Single registration point for evaluator demos. Adding a new evaluator page is
// one entry here plus its page component — the home page and router pick it up
// automatically.
export interface EvaluatorDemo {
  path: string;
  title: string;
  description: string;
  element: ReactElement;
}

export const evaluators: EvaluatorDemo[] = [
  {
    path: '/math-standards-alignment',
    title: 'Math Standards Alignment',
    description: 'Check whether a math word problem aligns to selected academic standards.',
    element: <MathStandardsAlignmentPage />,
  },
];
