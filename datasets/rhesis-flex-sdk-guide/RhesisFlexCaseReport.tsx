import {useMemo, useState} from 'react';
import useBaseUrl from '@docusaurus/useBaseUrl';
import archive from '@site/src/data/rhesis-flex-results.json';

const variants = [['evidence', 'Evidence only'], ['gold', 'Gold SQL only'], ['combined', 'Evidence + Gold SQL']] as const;
type Variant = typeof variants[number][0];
type Sort = 'case_number' | 'question_id' | Variant;

function resultClass(value: string) {
  return value === 'Pass' ? 'pass' : value === 'Fail' ? 'fail' : 'review';
}

export default function RhesisFlexCaseReport() {
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('all');
  const [sort, setSort] = useState<{key: Sort; descending: boolean}>({key: 'case_number', descending: false});
  const [page, setPage] = useState(1);
  const [size, setSize] = useState(30);
  const filtered = useMemo(() => archive.cases.filter(item => {
    const terms = search.toLowerCase().trim().split(/\s+/).filter(Boolean);
    const text = JSON.stringify(item).toLowerCase();
    const values = variants.map(([key]) => item.runs[key].category);
    return terms.every(term => text.includes(term)) && (filter === 'all'
      || filter === 'errors' && values.some(v => v.endsWith('error'))
      || filter === 'fail' && values.includes('Fail')
      || filter === 'disagreement' && new Set(values).size > 1
      || filter === 'different-sql' && !item.same_actual_sql);
  }), [search, filter]);
  const sorted = useMemo(() => [...filtered].sort((a, b) => {
    const delta = sort.key === 'case_number' || sort.key === 'question_id'
      ? Number(a[sort.key]) - Number(b[sort.key])
      : a.runs[sort.key].category.localeCompare(b.runs[sort.key].category);
    return sort.descending ? -delta : delta;
  }), [filtered, sort]);
  const pages = Math.max(1, Math.ceil(sorted.length / size));

  function heading(key: Sort, label: string) {
    const active = sort.key === key;
    return <th key={key} scope="col" aria-sort={active ? sort.descending ? 'descending' : 'ascending' : undefined}>
      <button type="button" onClick={() => {setSort({key, descending: active && !sort.descending}); setPage(1);}}>
        {label} <span aria-hidden="true">{active ? sort.descending ? '▼' : '▲' : '↕'}</span>
      </button>
    </th>;
  }

  return <div className="rhesisFlexReport">
    <section className="birdCaseTable" aria-label="Filter the 30 FLEX questions">
      <div className="birdCaseTable__filters">
        <label className="birdCaseTable__search" htmlFor="flex-search">Search questions
          <input id="flex-search" type="search" placeholder="Question ID, question, evidence, SQL, judge reason" value={search} onChange={e => {setSearch(e.target.value); setPage(1);}} />
        </label>
        <label htmlFor="flex-filter">Filter questions
          <select id="flex-filter" aria-label="Filter questions" value={filter} onChange={e => {setFilter(e.target.value); setPage(1);}}>
            <option value="all">All questions</option>
            <option value="fail">At least one judge returned Fail</option>
            <option value="errors">At least one operational error</option>
            <option value="disagreement">Different outcomes across runs</option>
            <option value="different-sql">Different actual SQL across runs</option>
          </select>
        </label>
        <button className="birdCaseTable__reset" type="button" disabled={!search && filter === 'all'} onClick={() => {setSearch(''); setFilter('all'); setPage(1);}}>Reset filters</button>
      </div>
      <p aria-live="polite"><strong>{filtered.length} of 30 questions</strong></p>
      <div className="birdCaseTable__scroll" role="region" aria-label="Three-run case comparison" tabIndex={0}>
        <table><thead><tr>
          {heading('case_number', 'Case number')}{heading('question_id', 'Question ID')}
          <th scope="col">Question</th>
          {variants.map(([key, label]) => heading(key, label))}
          <th scope="col">Same actual SQL?</th>
        </tr></thead><tbody>
          {sorted.slice((page - 1) * size, page * size).map(item => <tr key={item.question_id}>
            <td>{item.case_number}</td><td><a href={`#case-${item.question_id}`}>{item.question_id} →</a></td>
            <td className="birdCaseTable__question">{item.question}</td>
            {variants.map(([key]) => <td key={key}><span className={`birdCaseTable__result birdCaseTable__result--${resultClass(item.runs[key].category)}`}>{item.runs[key].category}</span></td>)}
            <td>{item.same_actual_sql ? 'Yes' : 'No'}</td>
          </tr>)}
          {!filtered.length && <tr><td colSpan={7}>No matching questions.</td></tr>}
        </tbody></table>
      </div>
      <div className="birdCaseTable__pagination">
        <label htmlFor="flex-page-size">Rows per page <select id="flex-page-size" aria-label="Rows per page" value={size} onChange={e => {setSize(Number(e.target.value)); setPage(1);}}>{[10, 20, 30].map(n => <option key={n} value={n}>{n}</option>)}</select></label>
        <button type="button" disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</button>
        <span>Page {page} of {pages}</span>
        <button type="button" disabled={page >= pages} onClick={() => setPage(page + 1)}>Next</button>
      </div>
    </section>
  </div>;
}

export function RhesisFlexCase({questionId}: {questionId: string}) {
  const root = useBaseUrl('/datasets/rhesis-flex-reference-required/');
  const item = archive.cases.find(item => item.question_id === questionId);
  if (!item) throw new Error(`Unknown FLEX question ${questionId}`);
  return <section className="rhesisFlexReport rhesisEvidenceCase">
      <p><strong>Question:</strong> {item.question}</p>
      <p><strong>Analysis:</strong> {item.analysis}</p>
      <p><strong>Actual SQL across the three runs:</strong> {item.same_actual_sql ? 'Identical' : 'Different — compare each run separately'}</p>
      <table><thead><tr><th>Reference</th><th>LLM judgment</th><th>Execution results match Gold?</th></tr></thead><tbody>
        {variants.map(([key, label]) => <tr key={key}><td><a href={`#case-${item.question_id}-${key}`}>{label}</a></td><td><span className={`birdCaseTable__result birdCaseTable__result--${resultClass(item.runs[key].category)}`}>{item.runs[key].category}</span></td><td>{item.runs[key].execution_accuracy === null ? 'Not available' : item.runs[key].execution_accuracy ? 'Yes' : 'No'}</td></tr>)}
      </tbody></table>
      {variants.map(([key, label]) => {
        const result = item.runs[key];
        return <section key={key} className="rhesisFlexReport__variant">
          <h4 id={`case-${item.question_id}-${key}`}>{label} · {result.category}</h4>
          <div className="rhesisEvidenceSqlScroll"><div className="rhesisEvidenceSql">
            <div className="rhesisEvidenceSql__header">Expected response · judge reference</div>
            <div className="rhesisEvidenceSql__header">{result.sql_format_error ? 'Actual API output · SQL execution rejected' : 'NL2SQL actual SQL'}</div>
            <div className="rhesisEvidenceSql__evidence">
              {key !== 'gold' && <><strong>Evidence</strong><p>{item.evidence || 'The source evidence is empty.'}</p></>}
              {key !== 'evidence' && <><strong>Gold SQL</strong><pre><code>{item.gold_sql_formatted}</code></pre></>}
              <details><summary>Stored expected_response JSON</summary><pre><code>{JSON.stringify(JSON.parse(result.expected_response), null, 2)}</code></pre></details>
            </div>
            <pre className="rhesisEvidenceSql__code"><code>{result.sql_format_error ? result.actual_sql : result.actual_sql_formatted}</code></pre>
          </div></div>
          <p><strong>Judge:</strong> {result.judge_called ? 'Called' : 'Not called'} · {result.score === null ? 'No valid score' : `${result.score} (${result.category})`} · <strong>Native Rhesis:</strong> {result.native_execution} / {result.native_verdict || 'no verdict'} · <strong>Execution branch:</strong> {result.branch || 'Not reached'}</p>
          {result.error && <p role="note"><strong>Error:</strong> {typeof result.error === 'string' ? result.error : JSON.stringify(result.error)}</p>}
          <p><strong>{!result.judge_reply ? 'No LLM judgment was produced' : result.score === null ? 'Raw LLM reply — no accepted score' : 'LLM judge reasoning'}</strong></p>
          {result.judge_reply && <blockquote style={{whiteSpace: 'pre-wrap', overflowWrap: 'anywhere'}}>{result.judge_reply}</blockquote>}
          <p><a href={`${archive.runs[key].run_url}&selectedresult=${result.result_id}`}>Rhesis result</a> · <a href={`${root}runs/${key}/api-proofs/${item.question_id}.json`}>API and empty-knowledge proof</a>{result.prompt_file && <> · <a href={`${root}${result.prompt_file}`}>Complete prompt for this judgment</a></>}{result.audit_file && <> · <a href={`${root}${result.audit_file}`}>Scoring audit, raw reply and SQL results</a></>}</p>
          <details><summary>Identifiers and result sizes</summary>
            <p>API query: <code>{result.query_id}</code><br />API trace: <code>{result.trace_id}</code><br />SQL SHA-256: <code>{result.actual_sql_sha256}</code></p>
            <p>Gold rows: {result.gold_row_count ?? 'unavailable'} · Actual rows: {result.actual_row_count ?? 'unavailable'}. Full rows are in the judge audit download.</p>
          </details>
        </section>;
      })}
    </section>;
}
