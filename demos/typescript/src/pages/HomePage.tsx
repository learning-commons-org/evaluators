import { Link } from 'react-router-dom';
import { evaluators } from '../evaluators';

export default function HomePage() {
  return (
    <main>
      <h1>Learning Commons Evaluators</h1>
      <p className="subtitle">
        Interactive demos of the <code>@learning-commons/evaluators</code> TypeScript SDK.
        Pick an evaluator to try it.
      </p>

      {evaluators.length === 0 ? (
        <p>No evaluator demos registered yet.</p>
      ) : (
        <ul className="evaluator-list">
          {evaluators.map((e) => (
            <li key={e.path}>
              <Link to={e.path}>
                <span className="evaluator-title">{e.title}</span>
                <span className="evaluator-desc">{e.description}</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
