import { afterEach, describe, expect, it, vi } from 'vitest';
import { baseUrl, mdmLinks } from './fhir';

afterEach(() => vi.unstubAllGlobals());

describe('mdmLinks', () => {
  it('queries the server operation with the source filter and reads Parameters values', async () => {
    const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({
      resourceType: 'Parameters',
      parameter: [
        { name: 'total', valueDecimal: 1 },
        { name: 'link', part: [
          { name: 'sourceResourceId', valueString: 'Patient/1054' },
          { name: 'goldenResourceId', valueString: 'Patient/1052' },
          { name: 'matchResult', valueString: 'MATCH' },
          { name: 'eidMatch', valueBoolean: false },
          { name: 'score', valueDecimal: 0 },
        ] },
      ],
    })));
    vi.stubGlobal('fetch', fetch);
    expect(await mdmLinks('1054')).toEqual([{
      sourceResourceId: 'Patient/1054', goldenResourceId: 'Patient/1052',
      matchResult: 'MATCH', eidMatch: false, score: 0,
    }]);
    expect(fetch.mock.calls[0][0]).toBe(`${baseUrl}/$mdm-query-links?resourceId=Patient%2F1054`);
  });

  it('returns no links while MDM is still processing', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({
      resourceType: 'Parameters', parameter: [{ name: 'total', valueDecimal: 0 }],
    }))));
    expect(await mdmLinks('1054')).toEqual([]);
  });

  it('reports OperationOutcome errors', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({
      resourceType: 'OperationOutcome', issue: [{ diagnostics: 'MDM unavailable' }],
    }), { status: 400 })));
    await expect(mdmLinks('1054')).rejects.toThrow('MDM unavailable');
  });
});
