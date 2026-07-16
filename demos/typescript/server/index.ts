import 'dotenv/config';
import express from 'express';
import { registerMathStandardsAlignment } from './math-standards-alignment.js';

const app = express();
app.use(express.json());

app.get('/api/health', (_req, res) => {
  res.json({ status: 'ok' });
});

// Each evaluator feature registers its own routes. Add new evaluators here.
registerMathStandardsAlignment(app);

const PORT = 3001;
const server = app.listen(PORT, () => {
  console.log(`API server listening on http://localhost:${PORT}`);
});

// Exit promptly on restart/Ctrl-C: close the listener and drop keep-alive
// sockets so the process doesn't hang until tsx force-kills it after 5s.
for (const signal of ['SIGINT', 'SIGTERM'] as const) {
  process.on(signal, () => {
    server.close(() => process.exit(0));
    server.closeAllConnections();
  });
}
