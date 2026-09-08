import { useState } from 'react';
import { createRoot } from 'react-dom/client';
import { createPatient, mdmLinks, patientHistory, readPatient, type Patient } from './fhir';
import { displayPatient, toPatient } from './patient';
import './styles.css';

const initial = { identifierSystem: 'https://mpi.demo.local/cedula', identifierValue: '', given: '', family: '', secondSurname: '', birthDate: '', gender: 'unknown' };

function entries(bundle: any) { return bundle?.entry?.map((entry: any) => entry.resource ?? entry) ?? []; }
function linkValue(link: any, key: string) { return link[key] ?? link?.resource?.[key]; }

function App() {
  const [form, setForm] = useState(initial); const [source, setSource] = useState<Patient>();
  const [links, setLinks] = useState<any[]>([]); const [golden, setGolden] = useState<Patient>(); const [history, setHistory] = useState<any[]>([]); const [error, setError] = useState(''); const [busy, setBusy] = useState(false);
  const loadDetails = async (patient: Patient) => {
    if (!patient.id) return; setSource(patient); setError(''); setLinks([]); setGolden(undefined); setHistory([]);
    const [foundLinks, historyBundle] = await Promise.all([mdmLinks(patient.id), patientHistory(patient.id)]);
    setLinks(foundLinks); setHistory(entries(historyBundle));
    const goldenRef = foundLinks.find((link) => link.matchResult === 'MATCH')?.goldenResourceId;
    if (goldenRef) setGolden(await readPatient(String(goldenRef).replace('Patient/', ''))); else setGolden(undefined);
  };
  const submit = async (patient: Patient) => {
    setBusy(true); setError('');
    try {
      const created = await createPatient(patient);
      try { await loadDetails(created); }
      catch (e: any) { setError(`Patient/${created.id} se creó correctamente, pero no se pudieron cargar sus detalles: ${e.message}`); }
    } catch (e: any) { setError(e.message); } finally { setBusy(false); }
  };
  const refresh = async () => {
    if (!source) return; setBusy(true);
    try { await loadDetails(source); } catch (e: any) { setError(e.message); } finally { setBusy(false); }
  };
  const importFile = async (file?: File) => { if (!file) return; try { const json = JSON.parse(await file.text()); if (json.resourceType !== 'Patient') throw new Error('El archivo debe contener un recurso FHIR Patient individual.'); await submit(json); } catch (e: any) { setError(e.message); } };
  return <main>
    <header><span>FHIR R4 · HAPI MDM</span><h1>Portal MPI didáctico</h1><p>Crea o importa un Patient y revisa los enlaces MDM sin ejecutar acciones sobre ellos.</p></header>
    <section className="grid input-grid"><form onSubmit={(e) => { e.preventDefault(); submit(toPatient(form)); }}><h2>Alta manual</h2>
      {Object.entries({ 'Sistema de identificador': 'identifierSystem', 'Identificador': 'identifierValue', 'Nombres (separados por coma)': 'given', 'Primer apellido': 'family', 'Segundo apellido': 'secondSurname', 'Fecha de nacimiento': 'birthDate' }).map(([label, key]) => <label key={key}>{label}<input required={key !== 'secondSurname'} type={key === 'birthDate' ? 'date' : 'text'} value={(form as any)[key]} onChange={(e) => setForm({ ...form, [key]: e.target.value })} /></label>)}
      <label>Sexo<select value={form.gender} onChange={(e) => setForm({ ...form, gender: e.target.value })}><option value="female">female</option><option value="male">male</option><option value="other">other</option><option value="unknown">unknown</option></select></label><button disabled={busy}>Crear Patient</button></form>
      <aside><h2>Importar JSON</h2><p>Admite exclusivamente un recurso FHIR <code>Patient</code> individual.</p><input type="file" accept="application/json,.json" onChange={(e) => importFile(e.target.files?.[0])} /><p className="hint">El perfil PatientDO se declara en <code>meta.profile</code>; no se valida en el servidor.</p></aside></section>
    {error && <p className="error">{error}</p>}
    {source && <button disabled={busy} onClick={refresh}>Actualizar enlaces e historial</button>}
    {source && <><section><h2>Resultado para {displayPatient(source)}</h2><p className="hint">ID: {source.id}. Las operaciones de aceptar, rechazar, fusionar y desvincular no están habilitadas.</p><div className="links">{links.length ? links.map((link, i) => <article key={i}><strong>{linkValue(link, 'matchResult') || linkValue(link, 'linkSource') || 'MDM_LINK'}</strong><pre>{JSON.stringify(link, null, 2)}</pre></article>) : <p>No hay enlaces MDM devueltos todavía.</p>}</div></section>
    <section><h2>Comparación lado a lado</h2><div className="grid compare"><PatientCard title="Patient fuente" patient={source} /><PatientCard title="Golden Record" patient={golden} /></div></section>
    <section><h2>Historial disponible</h2><h3>Versiones FHIR del Patient</h3>{history.length ? <ul>{history.map((item, i) => <li key={i}>v{item.meta?.versionId ?? '?'} — {item.meta?.lastUpdated ?? 'sin fecha'}</li>)}</ul> : <p>Sin versiones devueltas.</p>}<h3>MDM_LINK</h3><p>Se muestra el estado y los metadatos que devuelve la consulta de enlaces MDM actual.</p></section></>}
  </main>;
}
function PatientCard({ title, patient }: { title: string; patient?: Patient }) { const name = patient?.name?.[0] || {}; return <article className="card"><h3>{title}</h3>{patient ? <dl><dt>ID</dt><dd>{patient.id || 'nuevo'}</dd><dt>Identificador</dt><dd>{patient.identifier?.map((i: any) => `${i.system} | ${i.value}`).join(', ') || '—'}</dd><dt>Nombres</dt><dd>{(name.given || []).join(' ')}</dd><dt>Apellidos</dt><dd>{[name.family, name.extension?.[0]?.valueString].filter(Boolean).join(' ')}</dd><dt>Nacimiento / sexo</dt><dd>{patient.birthDate} / {patient.gender}</dd></dl> : <p>Sin Golden Record asociado.</p>}</article>; }
createRoot(document.getElementById('root')!).render(<App />);
