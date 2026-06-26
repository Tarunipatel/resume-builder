import { useState, useRef, useCallback } from 'react'
import axios from 'axios'
import './App.css'

const API = 'http://localhost:8000'

// ── Helpers ───────────────────────────────────────────────────────────
function fmt(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1048576) return (bytes / 1024).toFixed(0) + ' KB'
  return (bytes / 1048576).toFixed(1) + ' MB'
}
function initials(name) {
  return name.split(' ').filter(Boolean).map(w => w[0]).join('').slice(0, 2).toUpperCase()
}

// ── Score ring ────────────────────────────────────────────────────────
function ScoreRing({ score }) {
  const r = 20, circ = 2 * Math.PI * r
  const offset = circ - (score / 100) * circ
  const color = score >= 70 ? '#2e7d52' : score >= 50 ? '#b07d1a' : '#b94040'
  return (
    <svg width="52" height="52" style={{ flexShrink: 0 }}>
      <circle cx="26" cy="26" r={r} fill="none" stroke="#e8e2d9" strokeWidth="3.5" />
      <circle
        cx="26" cy="26" r={r} fill="none"
        stroke={color} strokeWidth="3.5"
        strokeDasharray={circ} strokeDashoffset={offset}
        strokeLinecap="round" transform="rotate(-90 26 26)"
        style={{ transition: 'stroke-dashoffset 0.8s ease' }}
      />
      <text x="26" y="31" textAnchor="middle" fontSize="12" fontWeight="800" fill={color} fontFamily="Inter,sans-serif">
        {score}
      </text>
    </svg>
  )
}

// ── Diff modal ────────────────────────────────────────────────────────
function DiffModal({ result, originalText, onClose }) {
  return (
    <div className="overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-head">
          <div>
            <h3>{result.student_name}</h3>
            <p>Original on the left, improved on the right</p>
          </div>
          <button className="modal-x" onClick={onClose}>×</button>
        </div>
        <div className="modal-cols">
          <div className="diff-col">
            <div className="diff-col-lbl">
              <span className="lbl-dot" style={{ background: '#c5bfb4' }} /> Original
            </div>
            {originalText}
          </div>
          <div className="diff-col">
            <div className="diff-col-lbl">
              <span className="lbl-dot" style={{ background: '#2e7d52' }} /> Improved
            </div>
            {result.improved_text}
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Topbar stepper ────────────────────────────────────────────────────
const STEPS = [
  { num: 1, label: 'Upload & Screen' },
  { num: 2, label: 'Review Results'  },
  { num: 3, label: 'Improve CVs'     },
]

function Topbar({ step, screenResult, onGoto }) {
  return (
    <header className="topbar">
      <div className="topbar-brand">
        <span className="brand-dot" />
        PlacementCV
      </div>

      <nav className="stepper">
        {STEPS.map((s, i) => {
          const isDone   = step > s.num
          const isActive = step === s.num
          const isLocked = step < s.num

          // Step 2 clickable if screened, step 3 clickable if screened + partial cvs exist
          const canClick = isDone || (
            s.num === 2 && screenResult ||
            s.num === 3 && screenResult?.results.some(r => r.match_level === 'partial' && !r.error)
          )

          return (
            <div key={s.num} className="step-item">
              <button
                className={`step-btn ${isDone ? 'done' : isActive ? 'active' : 'locked'} ${canClick && !isActive ? 'clickable' : ''}`}
                onClick={() => canClick && !isActive && onGoto(s.num)}
              >
                <div className="step-circle">
                  {isDone ? '✓' : isLocked ? '🔒' : s.num}
                </div>
                <span className="step-text">{s.label}</span>
              </button>
              {i < STEPS.length - 1 && <div className="step-connector" />}
            </div>
          )
        })}
      </nav>

      <div className="topbar-right">Placement office tool</div>
    </header>
  )
}

// ── Step 1: Upload & Screen ───────────────────────────────────────────
function UploadPage({ files, setFiles, jd, setJd, onScreen, loading, progress }) {
  const [dragging, setDragging] = useState(false)
  const inputRef = useRef()

  const addFiles = useCallback((incoming) => {
    const valid = Array.from(incoming).filter(f => f.name.endsWith('.pdf') || f.name.endsWith('.docx'))
    setFiles(prev => {
      const existing = new Set(prev.map(f => f.name))
      return [...prev, ...valid.filter(f => !existing.has(f.name))]
    })
  }, [setFiles])

  const removeFile = name => setFiles(f => f.filter(x => x.name !== name))
  const onDrop = e => { e.preventDefault(); setDragging(false); addFiles(e.dataTransfer.files) }

  return (
    <div className="page-content">
      <div className="page-header">
        <div className="page-eyebrow">Step 1 of 3</div>
        <h1 className="page-title">Upload CVs and <em>paste the job description</em></h1>
        <p className="page-sub">
          Add the student resumes and the role you are hiring for. We will score each CV
          against the job description and rank them for you.
        </p>
      </div>

      <div className="input-grid">
        <div className="card">
          <div className="card-head">
            <div className="card-step">Upload</div>
            <h3>Student CVs</h3>
            <p>PDF or DOCX, up to 50 files at once</p>
          </div>
          <div className="card-body">
            <div
              className={`drop-zone ${dragging ? 'dragging' : ''}`}
              onClick={() => inputRef.current.click()}
              onDragOver={e => { e.preventDefault(); setDragging(true) }}
              onDragLeave={() => setDragging(false)}
              onDrop={onDrop}
            >
              <span className="dz-icon">📁</span>
              <h4>Drop files here or <span className="dz-link">browse</span></h4>
              <p>.pdf and .docx accepted</p>
              {files.length > 0 && (
                <div className="count-tag">{files.length} file{files.length !== 1 ? 's' : ''} selected</div>
              )}
              <input
                ref={inputRef} type="file" multiple accept=".pdf,.docx"
                style={{ display: 'none' }}
                onChange={e => addFiles(e.target.files)}
              />
            </div>
            {files.length > 0 && (
              <div className="file-list">
                {files.map(f => (
                  <div key={f.name} className="file-row">
                    <span className="file-icon">{f.name.endsWith('.pdf') ? '📕' : '📘'}</span>
                    <span className="file-name">{f.name}</span>
                    <span className="file-size">{fmt(f.size)}</span>
                    <button className="file-remove" onClick={() => removeFile(f.name)}>×</button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="card">
          <div className="card-head">
            <div className="card-step">Paste</div>
            <h3>Job Description</h3>
            <p>Include the role, required skills, and responsibilities</p>
          </div>
          <div className="card-body">
            <textarea
              className="jd-area"
              placeholder="Software Engineer, Backend&#10;&#10;We are looking for someone with 2 years of Python experience, familiarity with REST APIs, and exposure to cloud platforms like AWS or GCP...&#10;&#10;Paste the full job description here."
              value={jd}
              onChange={e => setJd(e.target.value)}
            />
            <p className="jd-hint">More detail means better keyword matching and scoring.</p>
          </div>
        </div>
      </div>

      <div className="action-bar">
        <button
          className="btn btn-primary"
          onClick={onScreen}
          disabled={loading || !files.length || !jd.trim()}
        >
          {loading
            ? 'Screening...'
            : `Screen ${files.length > 0 ? files.length : ''} resume${files.length !== 1 ? 's' : ''}`}
        </button>
        {files.length > 0 && !loading && (
          <button className="btn btn-outline" onClick={() => setFiles([])}>Clear files</button>
        )}
      </div>

      {loading && (
        <div className="progress-wrap">
          <div className="spinner" />
          <div className="progress-info">
            <div className="progress-title">Scoring {files.length} resume{files.length !== 1 ? 's' : ''} against the job description</div>
            <div className="progress-desc">This usually takes under a minute...</div>
            <div className="progress-track">
              <div className="progress-fill" style={{ width: `${progress}%` }} />
            </div>
          </div>
          <div className="progress-pct">{progress}%</div>
        </div>
      )}
    </div>
  )
}

// ── Step 2: Ranked Results ────────────────────────────────────────────
function ResultsPage({ screenResult, onGoImprove, onReset }) {
  const strong  = screenResult.results.filter(r => r.match_level === 'strong'  && !r.error)
  const partial = screenResult.results.filter(r => r.match_level === 'partial' && !r.error)
  const poor    = screenResult.results.filter(r => r.match_level === 'poor'    && !r.error)
  const errors  = screenResult.results.filter(r => r.error)

  const exportTxt = (cv) => {
    const blob = new Blob([cv.original_text], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    Object.assign(document.createElement('a'), {
      href: url, download: `${cv.student_name.replace(/ /g, '_')}_cv.txt`
    }).click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="page-content">
      <div className="page-header">
        <div className="page-eyebrow">Step 2 of 3 — {screenResult.job_title}</div>
        <h1 className="page-title">Ranked results — <em>{screenResult.screened} CVs screened</em></h1>
        <p className="page-sub">
          CVs are sorted best-to-worst against the job description. Strong fits are ready to go.
          The middle group needs targeted edits — you can improve those on the next step.
        </p>
      </div>

      <div className="summary-bar">
        <div className="summary-tile summary-strong">
          <div className="summary-num">{strong.length}</div>
          <div className="summary-lbl">Strong fit</div>
          <div className="summary-range">Score 70 and above</div>
        </div>
        <div className="summary-tile summary-partial">
          <div className="summary-num">{partial.length}</div>
          <div className="summary-lbl">Worth improving</div>
          <div className="summary-range">Score 50 to 69</div>
        </div>
        <div className="summary-tile summary-poor">
          <div className="summary-num">{poor.length}</div>
          <div className="summary-lbl">Poor fit</div>
          <div className="summary-range">Score below 50</div>
        </div>
      </div>

      {strong.length > 0 && (
        <div className="tier-section">
          <div className="tier-header">
            <span className="tier-dot t-strong" />
            <span className="tier-title">Strong fits</span>
            <span className="tier-count">{strong.length}</span>
            <span className="tier-desc">Ready to send — no edits needed</span>
          </div>
          <div className="cv-list">
            {strong.map(cv => (
              <div key={cv.filename} className="cv-card tier-strong-card">
                <div className="cv-card-left">
                  <ScoreRing score={cv.score} />
                  <div>
                    <div className="cv-name">{cv.student_name}</div>
                    <div className="cv-meta">{cv.email}</div>
                  </div>
                </div>
                <div className="cv-card-mid">
                  {cv.why_strong.slice(0, 3).map((w, i) => (
                    <div key={i} className="why-item">
                      <span className="why-dot dot-green" />
                      {w}
                    </div>
                  ))}
                </div>
                <div className="cv-card-right">
                  <span className="tier-badge badge-strong">Strong fit</span>
                  <button className="btn btn-outline btn-sm" onClick={() => exportTxt(cv)}>Export CV</button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {partial.length > 0 && (
        <div className="tier-section">
          <div className="tier-header">
            <span className="tier-dot t-partial" />
            <span className="tier-title">Worth improving</span>
            <span className="tier-count">{partial.length}</span>
            <span className="tier-desc">Go to Step 3 to rewrite these CVs</span>
          </div>
          <div className="cv-list">
            {partial.map(cv => (
              <div key={cv.filename} className="cv-card tier-partial-card">
                <div className="cv-card-left">
                  <ScoreRing score={cv.score} />
                  <div>
                    <div className="cv-name">{cv.student_name}</div>
                    <div className="cv-meta">{cv.email}</div>
                  </div>
                </div>
                <div className="cv-card-mid">
                  {cv.missing_keywords.slice(0, 4).map((k, i) => (
                    <span key={i} className="tag missing" style={{ display: 'inline-block', marginRight: 4, marginBottom: 2 }}>{k}</span>
                  ))}
                </div>
                <div className="cv-card-right">
                  <span className="tier-badge badge-partial">Worth improving</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {poor.length > 0 && (
        <div className="tier-section">
          <div className="tier-header">
            <span className="tier-dot t-poor" />
            <span className="tier-title">Poor fit</span>
            <span className="tier-count">{poor.length}</span>
            <span className="tier-desc">Missing core requirements</span>
          </div>
          <div className="cv-list">
            {poor.map(cv => (
              <div key={cv.filename} className="cv-card tier-poor-card">
                <div className="cv-card-left">
                  <ScoreRing score={cv.score} />
                  <div>
                    <div className="cv-name">{cv.student_name}</div>
                    <div className="cv-meta">{cv.email}</div>
                  </div>
                </div>
                <div className="cv-card-mid">
                  <span className="poor-note">Missing core requirements — a CV rewrite would not meaningfully help.</span>
                </div>
                <div className="cv-card-right">
                  <span className="tier-badge badge-poor">Poor fit</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {errors.length > 0 && (
        <div className="tier-section">
          <div className="tier-header">
            <span className="tier-dot t-poor" />
            <span className="tier-title">Could not process</span>
            <span className="tier-count">{errors.length}</span>
          </div>
          <div className="cv-list">
            {errors.map(cv => (
              <div key={cv.filename} className="cv-card tier-error-card">
                <div className="cv-card-left">
                  <div><div className="cv-name">{cv.filename}</div></div>
                </div>
                <div className="cv-card-mid">
                  <div className="error-box" style={{ padding: '6px 10px' }}>{cv.error}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="page-actions">
        <div className="page-actions-left">
          <button className="btn btn-outline" onClick={onReset}>Start over</button>
        </div>
        {partial.length > 0 && (
          <div className="page-actions-right">
            <button className="btn btn-primary" onClick={onGoImprove}>
              Improve {partial.length} CV{partial.length !== 1 ? 's' : ''} in Step 3
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

// ── Step 3: Improve CVs ───────────────────────────────────────────────
function ImprovePage({ screenResult, jd, onBack }) {
  const partial = screenResult.results.filter(r => r.match_level === 'partial' && !r.error)
  const [improvingId, setImprovingId] = useState(null)
  const [improved, setImproved]       = useState({}) // filename -> ImprovedCV
  const [diff, setDiff]               = useState(null)

  const handleImprove = async (cv) => {
    setImprovingId(cv.filename)
    try {
      const form = new FormData()
      form.append('job_description', jd)
      form.append('filename', cv.filename)
      form.append('cv_text', cv.original_text)
      const res = await axios.post(`${API}/api/improve-one`, form)
      setImproved(m => ({ ...m, [cv.filename]: res.data }))
    } catch (err) {
      alert(err.response?.data?.detail || 'Improvement failed, try again.')
    } finally {
      setImprovingId(null)
    }
  }

  const downloadPdf = async (data) => {
    try {
      const form = new FormData()
      form.append('student_name', data.student_name)
      form.append('improved_text', data.improved_text)
      const res = await axios.post(`${API}/api/single-pdf`, form, { responseType: 'blob' })
      const url = URL.createObjectURL(res.data)
      Object.assign(document.createElement('a'), {
        href: url, download: `${data.student_name.replace(/ /g, '_')}_improved.pdf`
      }).click()
      URL.revokeObjectURL(url)
    } catch { alert('Download failed.') }
  }

  const improvedCount = Object.keys(improved).length

  return (
    <div className="page-content">
      <div className="page-header">
        <div className="page-eyebrow">Step 3 of 3 — {screenResult.job_title}</div>
        <h1 className="page-title">Improve the <em>{partial.length} shortlisted CVs</em></h1>
        <p className="page-sub">
          These CVs have relevant experience but need targeted edits to better match the role.
          Click "Improve" on each one to get a rewritten version and a download-ready PDF.
        </p>
      </div>

      <div className="improve-intro">
        <div className="improve-intro-icon">✏️</div>
        <p>
          <strong>How this works:</strong> Each CV is rewritten by AI to naturally include the right
          keywords, strengthen bullet points, and align the experience section with what this role requires.
          You will see a before/after comparison and can download the improved PDF.
          {improvedCount > 0 && <strong> {improvedCount} of {partial.length} done so far.</strong>}
        </p>
      </div>

      <div className="cv-list">
        {partial.map(cv => {
          const imp = improved[cv.filename]
          const isImproving = improvingId === cv.filename

          return (
            <div key={cv.filename} className={`cv-card tier-partial-card ${imp ? 'is-improved' : ''}`}>
              <div className="cv-card-left">
                <ScoreRing score={imp ? imp.ats_score_after : cv.score} />
                <div>
                  <div className="cv-name">{cv.student_name}</div>
                  <div className="cv-meta">{cv.email}</div>
                </div>
              </div>

              <div className="cv-card-mid">
                {imp ? (
                  imp.key_changes.slice(0, 3).map((c, i) => (
                    <div key={i} className="why-item">
                      <span className="why-dot dot-green" />{c}
                    </div>
                  ))
                ) : (
                  cv.suggestions.slice(0, 3).map((s, i) => (
                    <div key={i} className="suggestion-item">
                      <span className="sugg-num">{i + 1}</span>{s}
                    </div>
                  ))
                )}
              </div>

              <div className="cv-card-right">
                {imp ? (
                  <>
                    <span className="tier-badge badge-improved">Improved</span>
                    <button className="btn btn-outline btn-sm" onClick={() => setDiff(cv.filename)}>Compare</button>
                    <button className="btn btn-green btn-sm" onClick={() => downloadPdf(imp)}>Download PDF</button>
                  </>
                ) : (
                  <>
                    <span className="tier-badge badge-partial">Needs edit</span>
                    <button
                      className="btn btn-primary btn-sm"
                      onClick={() => handleImprove(cv)}
                      disabled={isImproving || !!improvingId}
                    >
                      {isImproving ? 'Improving...' : 'Improve this CV'}
                    </button>
                  </>
                )}
              </div>

              {diff === cv.filename && imp && (
                <DiffModal
                  result={imp}
                  originalText={cv.original_text}
                  onClose={() => setDiff(null)}
                />
              )}
            </div>
          )
        })}
      </div>

      <div className="page-actions">
        <div className="page-actions-left">
          <button className="btn btn-outline" onClick={onBack}>Back to results</button>
        </div>
      </div>
    </div>
  )
}

// ── Home page ─────────────────────────────────────────────────────────
const MOCK_CVS = [
  { name: 'Ananya Sharma',   score: 84, level: 'strong',  badge: 'Strong fit',       sub: 'B.Tech CSE · 3 projects in Python' },
  { name: 'Rohan Mehta',     score: 61, level: 'partial', badge: 'Worth improving',  sub: 'B.Tech IT · REST API experience' },
  { name: 'Priya Iyer',      score: 78, level: 'strong',  badge: 'Strong fit',       sub: 'MCA · Cloud certified' },
  { name: 'Karan Joshi',     score: 38, level: 'poor',    badge: 'Poor fit',         sub: 'B.Sc CS · No backend experience' },
]

function HomePage({ onLaunch }) {
  return (
    <div>
      {/* Nav */}
      <nav className="home-nav">
        <div className="home-nav-brand">
          <span className="brand-dot" style={{ background: '#2e7d52' }} />
          PlacementCV
        </div>
        <div className="home-nav-links">
          <button className="home-nav-link" onClick={() => document.getElementById('how').scrollIntoView({ behavior: 'smooth' })}>How it works</button>
          <button className="home-nav-link" onClick={() => document.getElementById('features').scrollIntoView({ behavior: 'smooth' })}>Features</button>
          <button className="home-nav-cta" onClick={onLaunch}>Open tool</button>
        </div>
      </nav>

      {/* Hero */}
      <section className="home-hero">
        <div className="home-hero-inner">
          <div>
            <span className="hero-kicker">For college placement offices</span>
            <h1 className="home-h1">
              Screen 50 CVs.<br />
              In the time it takes to<br />
              <em>read one.</em>
            </h1>
            <p className="home-hero-sub">
              Upload your student batch, paste a job description, and PlacementCV
              scores every resume against the role — ranking them into three tiers so
              you know exactly where to focus.
            </p>
            <div className="home-hero-btns">
              <button className="btn-hero-main" onClick={onLaunch}>
                Start screening
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M1 7h12M8 2l5 5-5 5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/></svg>
              </button>
              <button className="btn-hero-sec" onClick={() => document.getElementById('how').scrollIntoView({ behavior: 'smooth' })}>
                See how it works
              </button>
            </div>
          </div>

          {/* Mock ranked card list */}
          <div className="hero-visual">
            {MOCK_CVS.map((cv, i) => (
              <div key={i} className={`mock-card ${cv.level === 'strong' && i === 0 ? 'featured' : ''}`}>
                <div className={`mock-ring ${cv.level}`}>{cv.score}</div>
                <div className="mock-info">
                  <div className="mock-name">{cv.name}</div>
                  <div className="mock-sub">{cv.sub}</div>
                </div>
                <span className={`mock-badge ${cv.level}`}>{cv.badge}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Stat strip */}
      <div className="stat-strip">
        <div className="strip-stat"><div className="strip-num">50</div><div className="strip-lbl">CVs per batch</div></div>
        <div className="strip-stat"><div className="strip-num">3</div><div className="strip-lbl">Tiers — strong, partial, poor</div></div>
        <div className="strip-stat"><div className="strip-num">PDF</div><div className="strip-lbl">Improved CVs, ready to send</div></div>
        <div className="strip-stat"><div className="strip-num">0</div><div className="strip-lbl">Manual reviewing needed</div></div>
      </div>

      {/* Problem */}
      <section className="problem-section">
        <div className="problem-inner">
          <h2>Placement officers shouldn't have to<br /><em>read every CV by hand.</em></h2>
          <p>
            A typical placement batch has 40 to 80 students. A single company visit might
            bring 3 different roles. That is up to 240 CV reads — before you have even
            shortlisted anyone.
          </p>
          <p>
            PlacementCV scores every CV against the job description in one go, shows you
            who is job-ready, who needs a few edits, and who is genuinely not a fit. Then
            it rewrites the editable ones and generates download-ready PDFs.
          </p>
        </div>
      </section>

      {/* How it works */}
      <section className="how-section" id="how">
        <div className="how-inner">
          <div className="section-eyebrow">How it works</div>
          <div className="section-title">Three steps. One batch.</div>
          <div className="steps-grid">
            <div className="step-card">
              <div className="step-card-num">01</div>
              <h3>Upload and screen</h3>
              <p>Drop in the whole student batch — PDF and Word files both work. Paste the job description from any listing. Every CV gets scored 0 to 100 against the role.</p>
              <span className="step-card-tag tag-screen">Screening</span>
            </div>
            <div className="step-card">
              <div className="step-card-num">02</div>
              <h3>Review the ranked list</h3>
              <p>CVs are grouped into three tiers: strong fits above 70, worth improving between 50 and 70, and poor fits below 50. Strong fits show you exactly why they match.</p>
              <span className="step-card-tag tag-review">Ranking</span>
            </div>
            <div className="step-card">
              <div className="step-card-num">03</div>
              <h3>Improve what needs it</h3>
              <p>For each CV in the middle tier, click Improve. The AI rewrites it to better match the role, shows you the changes, and generates a PDF ready to submit.</p>
              <span className="step-card-tag tag-improve">Improvement</span>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="features-section" id="features">
        <div className="features-inner">
          <div className="section-eyebrow">What you get</div>
          <div className="section-title">Everything a placement office needs.</div>
          <div className="features-grid">
            <div className="feat-card">
              <div className="feat-icon fi-g">📊</div>
              <h3>0 to 100 match score per CV</h3>
              <p>Each resume is scored against the specific job description you paste — not a generic rubric. The score reflects actual keyword overlap, relevant experience, and skill match.</p>
            </div>
            <div className="feat-card">
              <div className="feat-icon fi-a">🎯</div>
              <h3>Three-tier ranking, instantly</h3>
              <p>Strong fits are highlighted and ready to forward. The middle tier shows you exactly what is missing and what to fix. Poor fits are flagged so you don't waste time on them.</p>
            </div>
            <div className="feat-card">
              <div className="feat-icon fi-b">✏️</div>
              <h3>Per-CV improvement suggestions</h3>
              <p>For every partially-matching CV, you get a numbered list of specific, actionable edits — not vague advice. Then one click rewrites the whole resume automatically.</p>
            </div>
            <div className="feat-card">
              <div className="feat-icon fi-c">📄</div>
              <h3>Download-ready improved PDFs</h3>
              <p>Every improved CV generates a clean, formatted PDF. Download them one by one or export a ZIP of the whole improved batch. No copy-pasting, no reformatting.</p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="cta-section">
        <div className="cta-inner">
          <h2>Ready to screen your<br /><em>next placement batch?</em></h2>
          <p>No signup needed. Add your Anthropic API key to the backend and you're running.</p>
          <button className="btn-cta-white" onClick={onLaunch}>
            Open the tool
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M1 7h12M8 2l5 5-5 5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/></svg>
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer className="home-footer">
        <div className="home-footer-brand">
          <span className="brand-dot" style={{ background: 'rgba(255,255,255,0.3)' }} />
          PlacementCV
        </div>
        <div className="home-footer-links">
          <span className="home-footer-link">Built for placement offices</span>
          <span className="home-footer-link">Powered by Claude AI</span>
        </div>
      </footer>
    </div>
  )
}

// ── App root ──────────────────────────────────────────────────────────
export default function App() {
  const [view, setView]               = useState('home')  // 'home' | 'tool'
  const [step, setStep]               = useState(1)
  const [files, setFiles]             = useState([])
  const [jd, setJd]                   = useState('')
  const [loading, setLoading]         = useState(false)
  const [progress, setProgress]       = useState(0)
  const [screenResult, setScreenResult] = useState(null)

  const launchTool = () => { setView('tool'); window.scrollTo(0, 0) }

  const screen = async () => {
    if (!files.length || !jd.trim()) return
    setLoading(true); setProgress(10)
    const form = new FormData()
    form.append('job_description', jd)
    files.forEach(f => form.append('files', f))
    try {
      const iv = setInterval(() => setProgress(p => Math.min(p + 5, 88)), 700)
      const res = await axios.post(`${API}/api/screen`, form)
      clearInterval(iv); setProgress(100)
      setScreenResult(res.data)
      setStep(2)
    } catch (err) {
      alert(err.response?.data?.detail || 'Something went wrong. Is the backend running?')
    } finally {
      setLoading(false)
    }
  }

  const reset = () => {
    setStep(1); setFiles([]); setScreenResult(null); setProgress(0)
  }

  if (view === 'home') {
    return <HomePage onLaunch={launchTool} />
  }

  return (
    <div className="page">
      <Topbar step={step} screenResult={screenResult} onGoto={setStep} />

      {step === 1 && (
        <UploadPage
          files={files} setFiles={setFiles}
          jd={jd} setJd={setJd}
          onScreen={screen} loading={loading} progress={progress}
        />
      )}

      {step === 2 && screenResult && (
        <ResultsPage
          screenResult={screenResult}
          onGoImprove={() => setStep(3)}
          onReset={reset}
        />
      )}

      {step === 3 && screenResult && (
        <ImprovePage
          screenResult={screenResult}
          jd={jd}
          onBack={() => setStep(2)}
        />
      )}

      <footer className="footer">
        <div className="footer-left"><span className="brand-dot" /> PlacementCV</div>
        <div className="footer-right">Powered by Claude AI</div>
      </footer>
    </div>
  )
}
