export type Patient = Record<string, any> & { resourceType: 'Patient'; id?: string };
export const baseUrl = import.meta.env.VITE_FHIR_BASE_URL || 'http://localhost:8080/fhir';

async function request(path: string, init?: RequestInit) {
  const response = await fetch(`${baseUrl}${path}`, { headers: { Accept: 'application/fhir+json', ...(init?.body ? { 'Content-Type': 'application/fhir+json' } : {}) }, ...init });
  const body = await response.json().catch(() => undefined);
  if (!response.ok) throw new Error(body?.issue?.[0]?.diagnostics || `${response.status} ${response.statusText}`);
  return body;
}

export const createPatient = (patient: Patient) => request('/Patient', { method: 'POST', body: JSON.stringify(patient) });
export const patientHistory = (id: string) => request(`/Patient/${id}/_history`);
export async function mdmLinks(id: string): Promise<Record<string, any>[]> {
  const result = await request(`/$mdm-query-links?resourceId=${encodeURIComponent(`Patient/${id}`)}`);
  if (result?.resourceType !== 'Parameters') throw new Error('Respuesta MDM inesperada: se esperaba Parameters.');
  return (result.parameter ?? [])
    .filter((parameter: any) => parameter.name === 'link')
    .map((parameter: any) => Object.fromEntries((parameter.part ?? []).map((part: any) => [
      part.name, Object.entries(part).find(([key]) => key.startsWith('value'))?.[1],
    ])));
}
export const readPatient = (id: string) => request(`/Patient/${id}`);
