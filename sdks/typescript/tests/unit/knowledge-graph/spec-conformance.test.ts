import { describe, it, expect, vi, beforeEach } from 'vitest';
import { KnowledgeGraphClient } from '../../../src/knowledge-graph/client.js';
import { Jurisdiction } from '../../../src/knowledge-graph/types.js';
import type { AcademicStandard } from '../../../src/knowledge-graph/types.js';
import type { paths, components } from '../../../src/knowledge-graph/kg-api.js';

// These assertions guard the seam between the generated spec types
// (kg-api.d.ts, regenerated via `npm run generate:kg-types`) and the
// hand-written types in types.ts. They are enforced by `tsc --noEmit`, so a
// spec regeneration that drifts from our implementation fails typecheck
// rather than silently changing runtime behaviour.

type Exact<A, B> = [A] extends [B] ? ([B] extends [A] ? true : never) : never;

type SpecJurisdiction = components['schemas']['JurisdictionENUM'];
type SpecGradeLevel = components['schemas']['GradeLevelENUM'];

type SpecStandard = components['schemas']['StandardsFrameworkItem'];

// The spec types /academic-standards as PaginatedResponse (whose `data` is an
// untyped Record<string, never>[]) intersected with a StandardsFrameworkItem[]
// override. Reading through that intersection is fine, but it cannot be
// constructed, so fixtures below use the schema directly. This asserts the
// endpoint really is the schema we pin them to.
type StandardsListBody =
  paths['/academic-standards']['get']['responses'][200]['content']['application/json'];
export const listEndpointReturnsSpecStandard: NonNullable<
  StandardsListBody['data']
>[number] extends SpecStandard
  ? true
  : never = true;

// types.ts hand-maintains Jurisdiction to give consumers a named enum. If the
// spec adds or removes a jurisdiction, this stops compiling.
export const jurisdictionsMatchSpec: Exact<`${Jurisdiction}`, SpecJurisdiction> = true;

// Mirrors the projection in client.ts getStandardsByGradeLevel. Fails to compile if
// the spec renames, removes, or incompatibly narrows any mapped field.
export function projectSpecStandard(item: SpecStandard): AcademicStandard {
  return {
    caseIdentifierUUID: item.caseIdentifierUUID,
    statementCode: item.statementCode ?? null,
    description: item.description ?? null,
    statementType: item.statementType ?? null,
    normalizedStatementType: item.normalizedStatementType ?? null,
    gradeLevel: item.gradeLevel ?? [],
  };
}

// types.ts widens the spec's enums to string deliberately, so the API can
// return values outside the current spec without breaking consumers.
export const gradeLevelAcceptsSpecValues: Exact<
  SpecGradeLevel extends AcademicStandard['gradeLevel'][number] ? true : never,
  true
> = true;

function okResponse(body: unknown) {
  const text = JSON.stringify(body);
  return {
    ok: true,
    status: 200,
    headers: new Headers({ 'content-type': 'application/json' }),
    json: () => Promise.resolve(body),
    text: () => Promise.resolve(text),
  };
}

beforeEach(() => { vi.unstubAllGlobals(); });

// A response item carrying every field the current spec marks required,
// including ones we do not project. Regenerating the spec with a new required
// field should not change what getStandardsByGradeLevel returns.
const fullSpecItem: SpecStandard = {
  identifier: 'id-1',
  caseIdentifierUUID: 'uuid-1',
  statementCode: '3.MD.C.7.d',
  description: 'Recognize area as additive',
  statementType: 'Standard',
  normalizedStatementType: 'Standard',
  jurisdiction: 'Multi-State',
  gradeLevel: ['3'],
  author: 'Learning Commons',
  provider: 'Learning Commons',
  license: 'CC BY-4.0',
  attributionStatement: 'Provided by Learning Commons under CC BY-4.0.',
  hasChildren: false,
};

describe('Knowledge Graph spec conformance', () => {
  it('projects a fully spec-shaped standard to exactly the AcademicStandard fields', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(okResponse({ data: [fullSpecItem] })));

    const [standard] = await new KnowledgeGraphClient('k').getStandardsByGradeLevel('3');

    expect(standard).toEqual({
      caseIdentifierUUID: 'uuid-1',
      statementCode: '3.MD.C.7.d',
      description: 'Recognize area as additive',
      statementType: 'Standard',
      normalizedStatementType: 'Standard',
      gradeLevel: ['3'],
    });
    // Unprojected spec fields must not leak into the public shape.
    expect(Object.keys(standard).sort()).toEqual([
      'caseIdentifierUUID',
      'description',
      'gradeLevel',
      'normalizedStatementType',
      'statementCode',
      'statementType',
    ]);
  });

  it('defaults gradeLevel to an empty array when the spec returns null', async () => {
    const item: SpecStandard = { ...fullSpecItem, gradeLevel: null };
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(okResponse({ data: [item] })));

    const [standard] = await new KnowledgeGraphClient('k').getStandardsByGradeLevel('3');

    expect(standard.gradeLevel).toEqual([]);
  });

  it('sends every jurisdiction in the enum through to the framework lookup query', async () => {
    // Multi-State short-circuits to a hardcoded framework UUID and issues no
    // framework lookup at all, so it is covered separately below.
    const jurisdictions = Object.values(Jurisdiction).filter(
      (j) => j !== Jurisdiction.MultiState,
    );

    const sent: (string | null)[] = [];
    for (const jurisdiction of jurisdictions) {
      const fetchMock = vi.fn().mockResolvedValue(
        okResponse({ data: [{ caseIdentifierUUID: 'fw-1' }] }),
      );
      vi.stubGlobal('fetch', fetchMock);

      await new KnowledgeGraphClient('k').getStandardsByGradeLevel('3', { jurisdiction });

      const url = new URL((fetchMock.mock.calls[0][0] as Request).url);
      expect(url.pathname).toContain('/standards-frameworks');
      sent.push(url.searchParams.get('jurisdiction'));
    }

    // Comparing the whole set proves the loop covered every enum member, and
    // that values carrying spaces and punctuation ("Washington, D.C.",
    // "New Hampshire") survive query encoding unaltered.
    expect([...sent].sort()).toEqual([...jurisdictions].sort());
  });

  it('resolves Multi-State without a framework lookup request', async () => {
    const fetchMock = vi.fn().mockResolvedValue(okResponse({ data: [] }));
    vi.stubGlobal('fetch', fetchMock);

    await new KnowledgeGraphClient('k').getStandardsByGradeLevel('3', {
      jurisdiction: Jurisdiction.MultiState,
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const url = new URL((fetchMock.mock.calls[0][0] as Request).url);
    expect(url.pathname).toContain('/academic-standards');
    // Pins the hardcoded CCSS framework UUID the short-circuit substitutes.
    expect(url.searchParams.get('standardsFrameworkCaseIdentifierUUID')).toBe(
      'c6496676-d7cb-11e8-824f-0242ac160002',
    );
  });
});
