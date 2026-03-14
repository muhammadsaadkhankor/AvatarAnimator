import { useState, useRef } from 'react'
import { Group } from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader'
import { GLTFExporter } from 'three/examples/jsm/exporters/GLTFExporter'
import type { GLTF } from 'three/examples/jsm/loaders/GLTFLoader'

const API = 'http://localhost:5000/api'

const ANIMATION_NAMES = [
  'Idle', 'Talking', 'Angry', 'Sad',
  'Surprised', 'Disappointed', 'Thoughtfullheadshake'
]

type Stage = 'idle' | 'uploading' | 'pipeline' | 'combining' | 'done' | 'error'

export default function App(): JSX.Element {
  const [stage, setStage]         = useState<Stage>('idle')
  const [avatarFile, setAvatarFile] = useState<File | null>(null)
  const [token, setToken]         = useState('')
  const [charId, setCharId]       = useState('')
  const [log, setLog]             = useState<string[]>([])
  const [error, setError]         = useState('')
  const fileRef = useRef<HTMLInputElement>(null)

  const addLog = (msg: string) => setLog(prev => [...prev, msg])

  // ── Upload avatar to backend → public/models/avatar.glb ──────────────────
  async function uploadAvatar(file: File): Promise<boolean> {
    const fd = new FormData()
    fd.append('file', file)
    const r = await fetch(`${API}/upload-avatar`, { method: 'POST', body: fd })
    const d = await r.json()
    if (!r.ok) { setError(d.error); return false }
    return true
  }

  // ── Start pipeline via backend, listen on SSE ─────────────────────────────
  async function startPipeline() {
    if (!avatarFile || !token) return
    setError(''); setLog([]); setStage('uploading')

    addLog('Uploading avatar...')
    const ok = await uploadAvatar(avatarFile)
    if (!ok) { setStage('error'); return }

    addLog('Starting pipeline...')
    setStage('pipeline')

    const r = await fetch(`${API}/pipeline`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token, character_id: charId || undefined })
    })
    if (!r.ok) {
      const d = await r.json()
      setError(d.error); setStage('error'); return
    }

    // Listen to SSE progress
    const es = new EventSource(`${API}/progress`)
    es.onmessage = (e) => {
      const msg: string = e.data
      if (msg.startsWith('STEP:')) {
        addLog(msg.slice(5))
      } else if (msg.startsWith('DONE:')) {
        es.close()
        addLog('✅ ' + msg.slice(5))
        combineAndDownload()
      } else if (msg.startsWith('ERROR:')) {
        es.close()
        setError(msg.slice(6))
        setStage('error')
      }
    }
    es.onerror = () => { es.close(); setError('Connection lost'); setStage('error') }
  }

  // ── Combine avatar + animations in-browser, trigger download ─────────────
  async function combineAndDownload() {
    setStage('combining')
    addLog('Combining avatar + animations...')
    try {
      const loader   = new GLTFLoader()
      const exporter = new GLTFExporter()
      const group    = new Group()

      const avatar = await load(loader, '/models/avatar.glb')
      group.add(avatar.scene)
      group.animations = []

      for (const name of ANIMATION_NAMES) {
        try {
          const anim = await load(loader, `/animations/${name}.glb`)
          if (anim.animations[0]) {
            anim.animations[0].name = name
            group.animations.push(anim.animations[0])
            addLog(`  ✓ ${name}`)
          }
        } catch {
          addLog(`  ⚠ ${name} not found, skipping`)
        }
      }

      addLog(`Exporting GLB with ${group.animations.length} animations...`)
      exporter.parse(
        avatar.scene,
        (glb) => {
          triggerDownload(glb as ArrayBuffer, 'avatar_with_animations.glb')
          setStage('done')
          addLog('🎉 Done! File downloaded.')
        },
        (err) => { setError(String(err)); setStage('error') },
        { binary: true, animations: group.animations }
      )
    } catch (e) {
      setError(String(e)); setStage('error')
    }
  }

  function triggerDownload(buf: ArrayBuffer, name: string) {
    const a = document.createElement('a')
    a.href = URL.createObjectURL(new Blob([buf], { type: 'application/octet-stream' }))
    a.download = name
    a.click()
  }

  function load(loader: GLTFLoader, path: string): Promise<GLTF> {
    return new Promise((res, rej) => loader.load(path, res, undefined, rej))
  }

  const busy = stage === 'uploading' || stage === 'pipeline' || stage === 'combining'

  return (
    <div style={styles.app}>
      <h1 style={styles.title}>🎭 AutoAnim</h1>
      <p style={styles.sub}>Upload avatar → Download Mixamo animations → Combined GLB</p>

      {/* Avatar upload */}
      <div style={styles.card}>
        <label style={styles.label}>Avatar GLB</label>
        <div
          style={{ ...styles.dropzone, ...(avatarFile ? styles.dropzoneActive : {}) }}
          onClick={() => !busy && fileRef.current?.click()}
        >
          {avatarFile
            ? <span>📦 {avatarFile.name} ({(avatarFile.size / 1024 / 1024).toFixed(2)} MB)</span>
            : <span>Drop .glb here or click to browse</span>
          }
        </div>
        <input
          ref={fileRef} type="file" accept=".glb" hidden
          onChange={e => { if (e.target.files?.[0]) setAvatarFile(e.target.files[0]) }}
        />
      </div>

      {/* Token */}
      <div style={styles.card}>
        <label style={styles.label}>Mixamo Token</label>
        <p style={styles.hint}>mixamo.com → F12 → Console → <code>localStorage.access_token</code></p>
        <input
          style={styles.input}
          type="password"
          placeholder="Paste token here..."
          value={token}
          onChange={e => setToken(e.target.value)}
          disabled={busy}
        />
        <input
          style={{ ...styles.input, marginTop: 8 }}
          type="text"
          placeholder="Character ID (optional — skip re-upload)"
          value={charId}
          onChange={e => setCharId(e.target.value)}
          disabled={busy}
        />
      </div>

      {/* Action */}
      {stage !== 'done' && (
        <button
          style={{ ...styles.btn, ...(busy || !avatarFile || !token ? styles.btnDisabled : {}) }}
          onClick={startPipeline}
          disabled={busy || !avatarFile || !token}
        >
          {busy ? '⏳ Running...' : '🚀 Start Pipeline'}
        </button>
      )}

      {/* Log */}
      {log.length > 0 && (
        <div style={styles.log}>
          {log.map((l, i) => <div key={i}>{l}</div>)}
        </div>
      )}

      {/* Error */}
      {error && <div style={styles.error}>❌ {error}</div>}

      {/* Done — re-download */}
      {stage === 'done' && (
        <div style={styles.card}>
          <button style={styles.btn} onClick={combineAndDownload}>
            ⬇️ Download Again
          </button>
          <button style={{ ...styles.btn, ...styles.btnSecondary, marginTop: 10 }}
            onClick={() => { setStage('idle'); setLog([]); setAvatarFile(null); setToken('') }}>
            🔄 New Project
          </button>
        </div>
      )}
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  app: {
    maxWidth: 600,
    margin: '0 auto',
    padding: '40px 20px',
    fontFamily: 'Inter, system-ui, sans-serif',
    color: '#e2e8f0',
  },
  title: { fontSize: 32, fontWeight: 800, margin: '0 0 6px', textAlign: 'center' },
  sub:   { color: '#94a3b8', textAlign: 'center', marginBottom: 32 },
  card:  {
    background: '#1e1e2e',
    border: '1px solid #2d2d4a',
    borderRadius: 12,
    padding: 20,
    marginBottom: 16,
  },
  label: { display: 'block', fontWeight: 600, marginBottom: 8 },
  hint:  { fontSize: 13, color: '#94a3b8', marginBottom: 10 },
  dropzone: {
    border: '2px dashed #2d2d4a',
    borderRadius: 8,
    padding: '24px 16px',
    textAlign: 'center',
    cursor: 'pointer',
    color: '#94a3b8',
    transition: 'border-color .2s',
  },
  dropzoneActive: { borderColor: '#7c5cfc', color: '#e2e8f0' },
  input: {
    width: '100%',
    padding: '12px 14px',
    background: '#0f0f1a',
    border: '1px solid #2d2d4a',
    borderRadius: 8,
    color: '#e2e8f0',
    fontSize: 14,
    boxSizing: 'border-box',
  },
  btn: {
    width: '100%',
    padding: '14px',
    background: 'linear-gradient(135deg,#7c5cfc,#9333ea)',
    color: '#fff',
    border: 'none',
    borderRadius: 10,
    fontSize: 16,
    fontWeight: 700,
    cursor: 'pointer',
    display: 'block',
  },
  btnDisabled: { opacity: 0.45, cursor: 'not-allowed' },
  btnSecondary: { background: '#2d2d4a' },
  log: {
    background: '#0f0f1a',
    border: '1px solid #2d2d4a',
    borderRadius: 10,
    padding: '14px 16px',
    fontSize: 13,
    lineHeight: 1.8,
    color: '#94a3b8',
    marginBottom: 16,
    whiteSpace: 'pre-wrap',
  },
  error: {
    background: 'rgba(248,113,113,.1)',
    border: '1px solid rgba(248,113,113,.3)',
    borderRadius: 10,
    padding: '14px 16px',
    color: '#f87171',
    fontSize: 14,
    whiteSpace: 'pre-wrap',
  },
}
