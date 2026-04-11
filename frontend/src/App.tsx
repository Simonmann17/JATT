import { FormEvent, useEffect, useMemo, useState } from 'react';

import { getApplications, importGmail, parseEmail } from './api';
import type { Application, ImportMessage } from './types';

function formatDate(input: string | null): string {
  if (!input) return '—';
  const date = new Date(input);
  return Number.isNaN(date.valueOf()) ? input : date.toLocaleString();
}

export default function App() {
  const [applications, setApplications] = useState<Application[]>([]);
  const [loadingApps, setLoadingApps] = useState(false);
  const [appsError, setAppsError] = useState<string | null>(null);

  const [rawEmail, setRawEmail] = useState('');
  const [parseLoading, setParseLoading] = useState(false);
  const [parseError, setParseError] = useState<string | null>(null);

  const [limit, setLimit] = useState(5);
  const [lookbackDays, setLookbackDays] = useState(90);
  const [senderFilter, setSenderFilter] = useState('');
  const [importLoading, setImportLoading] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);
  const [imported, setImported] = useState<ImportMessage[]>([]);

  async function loadApplications() {
    setLoadingApps(true);
    setAppsError(null);
    try {
      const rows = await getApplications();
      setApplications(rows);
    } catch (err) {
      setAppsError(err instanceof Error ? err.message : 'Unknown error while loading applications.');
    } finally {
      setLoadingApps(false);
    }
  }

  useEffect(() => {
    void loadApplications();
  }, []);

  const appCountText = useMemo(() => {
    if (loadingApps) return 'Loading applications...';
    return `${applications.length} tracked applications`;
  }, [applications.length, loadingApps]);

  async function onParseSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!rawEmail.trim()) return;

    setParseLoading(true);
    setParseError(null);

    try {
      await parseEmail(rawEmail);
      setRawEmail('');
      await loadApplications();
    } catch (err) {
      setParseError(err instanceof Error ? err.message : 'Failed to parse email.');
    } finally {
      setParseLoading(false);
    }
  }

  async function onImportSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    setImportLoading(true);
    setImportError(null);

    try {
      const messages = await importGmail({
        limit,
        lookback_days: lookbackDays,
        sender_filter: senderFilter
      });
      setImported(messages);
    } catch (err) {
      setImportError(err instanceof Error ? err.message : 'Failed to import from Gmail.');
    } finally {
      setImportLoading(false);
    }
  }

  return (
    <div className="app-shell">
      <div className="bg-orb orb-a" />
      <div className="bg-orb orb-b" />

      <header className="hero">
        <p className="eyebrow">JATT Frontend</p>
        <h1>Track job applications without touching Swagger.</h1>
        <p className="subtext">
          This UI uses your existing FastAPI endpoints for parsing emails, importing Gmail subjects,
          and listing saved applications.
        </p>
      </header>

      <main className="grid">
        <section className="card">
          <h2>Parse Raw Email</h2>
          <p className="muted">Paste a Workday email body and save parsed fields to your database.</p>
          <form onSubmit={onParseSubmit} className="stack">
            <textarea
              className="textarea"
              value={rawEmail}
              onChange={(event) => setRawEmail(event.target.value)}
              placeholder="Paste full email text here..."
              rows={12}
            />
            <button className="button" type="submit" disabled={parseLoading || !rawEmail.trim()}>
              {parseLoading ? 'Parsing...' : 'Parse & Save'}
            </button>
            {parseError && <p className="error">{parseError}</p>}
          </form>
        </section>

        <section className="card">
          <h2>Import Gmail Preview</h2>
          <p className="muted">Pull recent Gmail messages based on your query filters.</p>
          <form onSubmit={onImportSubmit} className="stack">
            <label className="label" htmlFor="limit">
              Limit
            </label>
            <input
              id="limit"
              className="input"
              type="number"
              min={1}
              max={100}
              value={limit}
              onChange={(event) => setLimit(Number(event.target.value))}
            />

            <label className="label" htmlFor="lookbackDays">
              Lookback Days
            </label>
            <input
              id="lookbackDays"
              className="input"
              type="number"
              min={1}
              max={3650}
              value={lookbackDays}
              onChange={(event) => setLookbackDays(Number(event.target.value))}
            />

            <label className="label" htmlFor="senderFilter">
              Sender Filter (optional)
            </label>
            <input
              id="senderFilter"
              className="input"
              type="text"
              placeholder="example@workday.com"
              value={senderFilter}
              onChange={(event) => setSenderFilter(event.target.value)}
            />

            <button className="button" type="submit" disabled={importLoading}>
              {importLoading ? 'Importing...' : 'Import Gmail'}
            </button>
            {importError && <p className="error">{importError}</p>}
          </form>

          {imported.length > 0 && (
            <div className="results">
              <h3>Imported Messages</h3>
              <ul className="list">
                {imported.map((message, idx) => (
                  <li key={`${message.subject}-${idx}`}>
                    <strong>{message.sender}</strong>
                    <span>{message.subject}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>

        <section className="card full-width">
          <div className="row-between">
            <div>
              <h2>Applications</h2>
              <p className="muted">{appCountText}</p>
            </div>
            <button className="button ghost" type="button" onClick={() => void loadApplications()}>
              Refresh
            </button>
          </div>

          {appsError && <p className="error">{appsError}</p>}

          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Company</th>
                  <th>Job Title</th>
                  <th>Status</th>
                  <th>Applied At</th>
                  <th>Received At</th>
                </tr>
              </thead>
              <tbody>
                {applications.map((app) => (
                  <tr key={app.id}>
                    <td>{app.id}</td>
                    <td>{app.company ?? '—'}</td>
                    <td>{app.job_title ?? '—'}</td>
                    <td>{app.status ?? '—'}</td>
                    <td>{formatDate(app.applied_at)}</td>
                    <td>{formatDate(app.email_received_at)}</td>
                  </tr>
                ))}
                {!loadingApps && applications.length === 0 && (
                  <tr>
                    <td colSpan={6} className="empty-row">
                      No applications saved yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      </main>
    </div>
  );
}
