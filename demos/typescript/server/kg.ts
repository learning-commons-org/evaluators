// The published SDK does not (yet) export its KnowledgeGraphClient, so the demo
// calls the Knowledge Graph REST API directly to list standards for the picker.
const KG_BASE_URL = 'https://api.learningcommons.org/knowledge-graph/v0';
const CCSS_FRAMEWORK_UUID = 'c6496676-d7cb-11e8-824f-0242ac160002';

export interface StandardOption {
  statementCode: string;
  description: string;
}

async function kgGet(path: string, params: Record<string, string>, apiKey: string): Promise<any> {
  const url = new URL(`${KG_BASE_URL}${path}`);
  for (const [key, value] of Object.entries(params)) {
    url.searchParams.set(key, value);
  }
  const response = await fetch(url, { headers: { 'x-api-key': apiKey } });
  if (!response.ok) {
    const body = await response.text().catch(() => '');
    throw new Error(`Knowledge Graph request failed (${response.status}): ${body}`);
  }
  return response.json();
}

async function getFrameworkUuid(jurisdiction: string, apiKey: string): Promise<string> {
  if (jurisdiction === 'Multi-State') return CCSS_FRAMEWORK_UUID;

  const data = await kgGet(
    '/standards-frameworks',
    { jurisdiction, academicSubject: 'Mathematics', limit: '1' },
    apiKey,
  );
  const uuid = (data.data ?? [])[0]?.caseIdentifierUUID;
  if (!uuid) {
    throw new Error(`No standards framework found for jurisdiction "${jurisdiction}"`);
  }
  return uuid;
}

export async function listStandards(
  grade: string,
  jurisdiction: string,
  apiKey: string,
): Promise<StandardOption[]> {
  const frameworkUuid = await getFrameworkUuid(jurisdiction, apiKey);
  const data = await kgGet(
    '/academic-standards',
    {
      standardsFrameworkCaseIdentifierUUID: frameworkUuid,
      gradeLevel: grade,
      normalizedStatementType: 'Standard',
      academicSubject: 'Mathematics',
      limit: '500',
    },
    apiKey,
  );

  if (data.pagination?.hasMore) {
    throw new Error(
      `Grade "${grade}" has more than 500 standards; the demo does not paginate. ` +
        `Raise the limit or add cursor pagination.`,
    );
  }

  return (data.data ?? [])
    .filter((item: any) => item.statementCode != null)
    .map((item: any) => ({
      statementCode: item.statementCode,
      description: item.description ?? '',
    }));
}
