import { useEffect, useState } from 'react';
import Select from 'react-select';

const GRADES = ['K', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12'];

interface StandardOption {
  statementCode: string;
  description: string;
}

interface SelectOption {
  value: string;
  label: string;
}

async function fetchJson(url: string, init?: RequestInit): Promise<any> {
  const response = await fetch(url, init);
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(body?.error ?? `Request failed (${response.status})`);
  }
  if (body === null) {
    throw new Error('Server returned a non-JSON response — is the backend running?');
  }
  return body;
}

export default function App() {
  const [jurisdictions, setJurisdictions] = useState<string[]>([]);
  const [grade, setGrade] = useState('3');
  const [jurisdiction, setJurisdiction] = useState('Multi-State');

  const [standards, setStandards] = useState<SelectOption[]>([]);
  const [standardsLoading, setStandardsLoading] = useState(false);
  const [selectedStandards, setSelectedStandards] = useState<SelectOption[]>([]);

  const [question, setQuestion] = useState('');
  const [evaluating, setEvaluating] = useState(false);
  const [output, setOutput] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    fetchJson('/api/jurisdictions')
      .then(setJurisdictions)
      .catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    let ignore = false;
    setSelectedStandards([]);
    setStandards([]);
    setStandardsLoading(true);
    setError('');
    const params = new URLSearchParams({ grade, jurisdiction });
    fetchJson(`/api/standards?${params}`)
      .then((list: StandardOption[]) => {
        if (ignore) return;
        setStandards(
          list.map((s) => ({
            value: s.statementCode,
            label: `${s.statementCode} — ${s.description}`,
          })),
        );
      })
      .catch((err) => {
        if (!ignore) setError(err.message);
      })
      .finally(() => {
        if (!ignore) setStandardsLoading(false);
      });
    return () => {
      ignore = true;
    };
  }, [grade, jurisdiction]);

  async function handleEvaluate() {
    setEvaluating(true);
    setError('');
    setOutput('');
    try {
      const results = await fetchJson('/api/evaluate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question,
          statementCodes: selectedStandards.map((s) => s.value),
          jurisdiction,
        }),
      });
      setOutput(JSON.stringify(results, null, 2));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setEvaluating(false);
    }
  }

  const canEvaluate = question.trim().length > 0 && selectedStandards.length > 0 && !evaluating;

  return (
    <main>
      <h1>Math Standards Alignment</h1>
      <p className="subtitle">
        Demo of <code>@learning-commons/evaluators</code> — checks whether a word problem
        aligns to selected academic standards.
      </p>

      <div className="row">
        <label>
          Grade
          <select value={grade} onChange={(e) => setGrade(e.target.value)}>
            {GRADES.map((g) => (
              <option key={g} value={g}>
                {g}
              </option>
            ))}
          </select>
        </label>

        <label>
          Jurisdiction
          <select value={jurisdiction} onChange={(e) => setJurisdiction(e.target.value)}>
            {jurisdictions.map((j) => (
              <option key={j} value={j}>
                {j}
              </option>
            ))}
          </select>
        </label>
      </div>

      <label>
        Standards ({standardsLoading ? 'loading…' : `${standards.length} available`})
        <Select
          isMulti
          options={standards}
          value={selectedStandards}
          onChange={(selected) => setSelectedStandards([...selected])}
          isLoading={standardsLoading}
          placeholder="Search and select one or more standards…"
        />
      </label>

      <label>
        Word problem
        <textarea
          rows={6}
          maxLength={10000}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Enter the math word problem to evaluate…"
        />
      </label>

      <button onClick={handleEvaluate} disabled={!canEvaluate}>
        {evaluating ? 'Evaluating…' : 'Evaluate'}
      </button>

      {error && <p className="error">{error}</p>}
      {output && <pre className="output">{output}</pre>}
    </main>
  );
}
