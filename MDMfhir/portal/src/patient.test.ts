import { describe, expect, it } from 'vitest';
import { normalized, toPatient, PATIENT_DO } from './patient';

describe('normalización MPI', () => {
  it('elimina acentos, compacta espacios y convierte a mayúsculas', () => {
    expect(normalized('  María   José ')).toBe('MARIA JOSE');
  });
  it('conserva cada given como elemento individual del Patient', () => {
    const patient = toPatient({ identifierSystem: 'sys', identifierValue: '1', given: 'Ana, María', family: 'Pérez', secondSurname: '', birthDate: '2000-01-01', gender: 'female' });
    expect(patient.meta.profile).toContain(PATIENT_DO);
    expect(patient.name[0].given).toEqual(['Ana', 'María']);
  });
});
