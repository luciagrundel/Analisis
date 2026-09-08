import type { Patient } from './fhir';

export const PATIENT_DO = 'https://digital.msp.gob.do/fhir/conectaton/StructureDefinition/PatientDO';
export const SECOND_SURNAME_DO = 'https://digital.msp.gob.do/fhir/conectaton/StructureDefinition/SegundoApellidoDO';

export function normalized(value = '') {
  return value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/\s+/g, ' ').trim().toLocaleUpperCase('es');
}

export function displayPatient(patient?: Patient) {
  if (!patient) return '—';
  const name = patient.name?.[0] || {};
  return [...(name.given || []), name.family].filter(Boolean).join(' ') || patient.id || 'Sin nombre';
}

export function toPatient(form: Record<string, string>): Patient {
  return {
    resourceType: 'Patient',
    meta: { profile: [PATIENT_DO] },
    identifier: form.identifierValue ? [{ system: form.identifierSystem, value: form.identifierValue }] : [],
    name: [{
      given: form.given.split(',').map((v) => v.trim()).filter(Boolean), family: form.family,
      extension: form.secondSurname ? [{ url: SECOND_SURNAME_DO, valueString: form.secondSurname }] : []
    }],
    birthDate: form.birthDate,
    gender: form.gender
  };
}
