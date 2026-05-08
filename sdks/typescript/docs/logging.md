# Logging

Control logging verbosity with `logLevel`:

```typescript
import { VocabularyEvaluator, LogLevel } from "@learning-commons/evaluators";

const evaluator = new VocabularyEvaluator({
  googleApiKey: "...",
  openaiApiKey: "...",
  logLevel: LogLevel.INFO, // SILENT | ERROR | WARN | INFO | DEBUG
});
```

Or provide a custom logger:

```typescript
import type { Logger } from "@learning-commons/evaluators";

const customLogger: Logger = {
  debug: (msg, ctx) => myLogger.debug(msg, ctx),
  info: (msg, ctx) => myLogger.info(msg, ctx),
  warn: (msg, ctx) => myLogger.warn(msg, ctx),
  error: (msg, ctx) => myLogger.error(msg, ctx),
};

const evaluator = new VocabularyEvaluator({
  googleApiKey: "...",
  openaiApiKey: "...",
  logger: customLogger,
});
```
