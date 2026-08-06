// Generated spec types are in kg-api.d.ts — see npm run generate:kg-types.
// We use string for normalizedStatementType and gradeLevel rather than the
// spec's strict enum types so the interfaces remain compatible if the API
// returns values outside the current spec.

/**
 * Jurisdictions supported by the LC Knowledge Graph.
 * Values match the KG API's jurisdiction field exactly.
 */
export enum Jurisdiction {
  MultiState = 'Multi-State',
  Alabama = 'Alabama',
  Alaska = 'Alaska',
  Arizona = 'Arizona',
  Arkansas = 'Arkansas',
  California = 'California',
  Colorado = 'Colorado',
  Connecticut = 'Connecticut',
  Delaware = 'Delaware',
  Florida = 'Florida',
  Georgia = 'Georgia',
  Hawaii = 'Hawaii',
  Idaho = 'Idaho',
  Illinois = 'Illinois',
  Indiana = 'Indiana',
  Iowa = 'Iowa',
  Kansas = 'Kansas',
  Kentucky = 'Kentucky',
  Louisiana = 'Louisiana',
  Maine = 'Maine',
  Maryland = 'Maryland',
  Massachusetts = 'Massachusetts',
  Michigan = 'Michigan',
  Minnesota = 'Minnesota',
  Mississippi = 'Mississippi',
  Missouri = 'Missouri',
  Montana = 'Montana',
  Nebraska = 'Nebraska',
  Nevada = 'Nevada',
  NewHampshire = 'New Hampshire',
  NewJersey = 'New Jersey',
  NewMexico = 'New Mexico',
  NewYork = 'New York',
  NorthCarolina = 'North Carolina',
  NorthDakota = 'North Dakota',
  Ohio = 'Ohio',
  Oklahoma = 'Oklahoma',
  Oregon = 'Oregon',
  Pennsylvania = 'Pennsylvania',
  RhodeIsland = 'Rhode Island',
  SouthCarolina = 'South Carolina',
  SouthDakota = 'South Dakota',
  Tennessee = 'Tennessee',
  Texas = 'Texas',
  Utah = 'Utah',
  Vermont = 'Vermont',
  Virginia = 'Virginia',
  Washington = 'Washington',
  WashingtonDC = 'Washington, D.C.',
  WestVirginia = 'West Virginia',
  Wisconsin = 'Wisconsin',
  Wyoming = 'Wyoming',
}

/**
 * An academic standard from the LC Knowledge Graph (spec: StandardsFrameworkItem).
 * Subset of fields used for alignment evaluation.
 */
export interface AcademicStandard {
  caseIdentifierUUID: string;
  statementCode: string | null | undefined;
  description: string | null | undefined;
  statementType: string | null | undefined;
  normalizedStatementType: string | null | undefined;
  gradeLevel: string[];
}

/**
 * A learning component from the LC Knowledge Graph.
 * description is guaranteed non-null — nulls are filtered at fetch time.
 * identifier is the KG system UUID echoed back by the model to verify
 * each evaluation maps to the correct learning component.
 */
export interface LearningComponent {
  identifier: string;
  description: string;
}

/** Resolved info from a standard code lookup. */
export interface StandardInfo {
  uuid: string;
  description?: string;
  /** The KG's spelling — use for display and joins. CCSS sub-standards are lowercase. */
  statementCode: string;
  /** Canonical lookup key (see normalizeStatementCode) — dedupe on this. */
  normalizedCode: string;
  /** Code matched multiple standards; uuid/description are the first match. */
  ambiguous?: boolean;
}
