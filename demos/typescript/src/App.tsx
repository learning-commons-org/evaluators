import { Routes, Route } from 'react-router-dom';
import HomePage from './pages/HomePage';
import { evaluators } from './evaluators';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      {evaluators.map((e) => (
        <Route key={e.path} path={e.path} element={e.element} />
      ))}
    </Routes>
  );
}
