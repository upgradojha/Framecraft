// React is used only for UI state: no Redux, queues or custom state libraries.
import { useEffect, useMemo, useState } from 'react';
// Small icon components keep the visual language of the original Framecraft.
import {
  Aperture, ArrowDownToLine, ArrowRight, Check, CheckCircle2,
  ChevronRight, CircleHelp, FileImage, GalleryVerticalEnd,
  ImagePlus, Layers, LoaderCircle, LogOut, Menu, Plus,
  Settings2, Sparkles, WandSparkles, X
} from 'lucide-react';
// All server calls are in api.js so this page remains easy to explain.
import { api, imageUrl, transformUrl } from './api';

// Styles shown before /api/styles arrives: they match backend/app/styles.py.
const STYLES = [
  { id: 'bold', name: 'Bold & dramatic', label: 'Big headline, cinematic contrast', icon: '✦', color: 'amber' },
  { id: 'minimal', name: 'Clean & minimal', label: 'Negative space, premium typography', icon: '◌', color: 'mint' },
  { id: 'vibrant', name: 'Vibrant & energetic', label: 'Bright colors, expressive graphics', icon: '✳', color: 'pink' },
];

// Size options are supported by the low-cost GPT image editing model.
const SIZES = [
  { value: '1536x1024', name: 'Landscape · 3:2', note: 'Good for thumbnails' },
  { value: '1024x1024', name: 'Square · 1:1', note: 'Good for feed posts' },
  { value: '1024x1536', name: 'Portrait · 2:3', note: 'Good for posters' },
];

// Every new request starts with editable user choices, not hidden prompts.
const INITIAL = {
  prompt: '', headline: '', subtitle: '', extra_prompt: '',
  styles: ['bold'], image_size: '1536x1024', quality: 'low', output_format: 'jpeg',
};

// Shared logo appears on both auth and dashboard pages.
function Logo() {
  return <div className="brand">
    <span className="brand-symbol"><Aperture size={23}/></span>
    <span className="brand-name">framecraft<span className="brand-dot">.</span></span>
    <span className="brand-suffix">studio</span>
  </div>;
}

// The login page is displayed whenever /api/auth/me returns HTTP 401.
function AuthPage({ onSuccess }) {
  // true means Register; false means Sign in.
  const [register, setRegister] = useState(false);
  // Credentials stay only in this component until submitted.
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const [note, setNote] = useState('');

  // Signup and login are the same form, but call different Supabase-backed routes.
  async function submit(event) {
    event.preventDefault();
    setError(''); setNote(''); setPending(true);
    try {
      const result = register
        ? await api.signup({ email, password })
        : await api.login({ email, password });
      // Normally Confirm email is OFF for the college demo.
      if (result.needs_confirmation) setNote('Account created. Confirm the email before signing in.');
      else onSuccess({ id: result.user.id, email: result.user.email });
    } catch (failure) {
      setError(failure.message);
    } finally {
      setPending(false);
    }
  }

  return <div className="auth-layout">
    <aside className="auth-visual">
      <Logo/>
      <div className="auth-art"><div className="auth-glow">✳</div><div className="auth-art-label">FRAME / 01</div><div className="auth-art-title">MAKE IT<br/>UNMISSABLE.</div></div>
      <div><span className="eyebrow">YOUR PRIVATE CREATIVE STUDIO</span><h1>Big ideas.<br/><em>Better visuals.</em></h1><p>Generate artwork, keep it organized, and return to your creations whenever you sign in.</p></div>
      <div className="auth-caption">FASTAPI <span>·</span> SUPABASE <span>·</span> IMAGEKIT</div>
    </aside>
    <main className="auth-form-shell">
      <div className="auth-mobile-logo"><Logo/></div>
      <div className="auth-form-card">
        <div className="auth-eyebrow"><span/> MEMBER ACCESS</div>
        <h2>{register ? 'Create your account.' : 'Welcome back.'}</h2>
        <p>{register ? 'Register with email to start your own private gallery.' : 'Sign in to open your personal Framecraft workspace.'}</p>
        <form onSubmit={submit} className="auth-form">
          <label>Email address <input type="email" autoComplete="email" required value={email} onChange={e => setEmail(e.target.value)} placeholder="you@example.com"/></label>
          <label>Password <input type="password" minLength={6} required autoComplete={register ? 'new-password' : 'current-password'} value={password} onChange={e => setPassword(e.target.value)} placeholder="At least 6 characters"/></label>
          {error && <div className="error-alert" role="alert">{error}</div>}
          {note && <div className="info-alert">{note}</div>}
          <button disabled={pending} className="generate-button" type="submit">{pending ? <LoaderCircle className="spin" size={18}/> : <ArrowRight size={18}/>} {register ? 'Create account' : 'Sign in'}</button>
        </form>
        <div className="auth-switch">{register ? 'Already a member?' : 'New to Framecraft?'} <button onClick={() => { setRegister(!register); setError(''); setNote(''); }}>{register ? 'Sign in' : 'Create an account'}</button></div>
      </div>
      <div className="auth-bottom">© 2026 FRAMECRAFT · BUILT FOR CREATORS</div>
    </main>
  </div>;
}

// A small gallery card displays exactly what came back from PostgreSQL.
function ImageCard({ image, options }) {
  // Failed calls remain visible as failures, not as fake/generated placeholders.
  if (image.status !== 'success') {
    return <div className="output-card failed"><div className="output-failed"><X size={28}/><strong>{image.style_name} failed</strong><span>{image.error_message}</span></div></div>;
  }
  return <article className="output-card">
    <div className="output-image"><img src={imageUrl(image.image_url)} alt={`${image.style_name} generated thumbnail`}/></div>
    <div className="output-details"><strong>{image.style_name}</strong><span>{options?.image_size || ''} · {options?.quality || ''}</span></div>
    <div className="output-links"><a href={image.image_url} target="_blank" rel="noreferrer"><ArrowDownToLine size={15}/> Open / save original</a><a href={transformUrl(image.image_url, 1280, 720)} target="_blank" rel="noreferrer">YouTube crop ↗</a></div>
  </article>;
}

// The dashboard owns the current form, gallery and which sidebar tab is shown.
function Dashboard({ user, onLogout }) {
  // Form values come from the user, including all real AI API choices.
  const [form, setForm] = useState(INITIAL);
  const [file, setFile] = useState(null);
  const [view, setView] = useState('create');
  const [creations, setCreations] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [mobileMenu, setMobileMenu] = useState(false);
  const [model, setModel] = useState('');
  // Read real style prompt instructions from FastAPI instead of guessing them.
  const [presets, setPresets] = useState(STYLES);
  // The preview uses a browser object URL and is never sent to Supabase.
  const preview = useMemo(() => file ? URL.createObjectURL(file) : '', [file]);
  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);

  // Fetch only this logged-in user's saved creations from PostgreSQL.
  async function refreshHistory() {
    const rows = await api.creations();
    setCreations(rows);
    return rows;
  }
  // Load history once after the cookie was validated by /api/auth/me.
  useEffect(() => {
    refreshHistory().catch(failure => setError(failure.message));
    api.health().then(result => setModel(result.model)).catch(() => {});
    // Merge backend style text with local icons/colors for the matching cards.
    api.styles().then(items => setPresets(items.map(item => ({
      ...STYLES.find(local => local.id === item.id), ...item
    })))).catch(() => {});
  }, []);

  // Updating one named setting avoids a separate useState for every dropdown.
  function update(name, value) { setForm(current => ({ ...current, [name]: value })); }
  // The card remains selected when clicked twice; at least one style is required.
  function toggleStyle(style) {
    setForm(current => {
      const list = current.styles.includes(style)
        ? current.styles.filter(name => name !== style)
        : [...current.styles, style];
      return { ...current, styles: list.length ? list : current.styles };
    });
  }

  // Submit is deliberately a single request: no jobs, workers or EventSource.
  async function generate(event) {
    event.preventDefault(); setError('');
    if (!file) return setError('Choose a reference image first.');
    setBusy(true);
    try {
      const result = await api.create(file, form);
      // The response already contains the image URLs stored in PostgreSQL.
      await refreshHistory();
      setActiveId(result.id); setView('create');
      // Show a helpful note when an image API request failed.
      if (result.images.some(item => item.status === 'failed')) setError('Some styles failed. Check the result cards and backend terminal.');
      document.getElementById('results')?.scrollIntoView({ behavior: 'smooth' });
    } catch (failure) {
      setError(failure.message);
    } finally {
      setBusy(false);
    }
  }

  // Logout clears HttpOnly cookies on the backend before showing sign-in.
  async function logout() {
    try { await api.logout(); } finally { onLogout(); }
  }
  // The active result is found only in the logged-in user's own history list.
  const active = creations.find(item => item.id === activeId) || creations[0];
  // Using the selected preset, show the user what AI direction will be sent.
  const chosenStyles = presets.filter(style => form.styles.includes(style.id));
  // Counts are derived from saved data instead of being stored independently.
  const completed = creations.reduce((count, item) => count + item.images.filter(img => img.status === 'success').length, 0);

  return <div className="layout">
    <aside className={`sidebar ${mobileMenu ? 'mobile-open' : ''}`}>
      <div className="sidebar-top"><Logo/><button type="button" className="close-menu" onClick={() => setMobileMenu(false)} aria-label="Close menu"><X size={19}/></button></div>
      <div className="sidebar-label">WORKSPACE</div>
      <nav className="nav">
        <button className={`nav-link ${view === 'create' ? 'active' : ''}`} onClick={() => { setView('create'); setMobileMenu(false); }}><WandSparkles size={18}/> Create studio <ChevronRight size={16} className="nav-arrow"/></button>
        <button className={`nav-link ${view === 'library' ? 'active' : ''}`} onClick={() => { setView('library'); setMobileMenu(false); }}><GalleryVerticalEnd size={18}/> My creations <span className="nav-count">{creations.length}</span></button>
      </nav>
      <div className="sidebar-divider"/>
      <div className="sidebar-label">YOUR STUDIO</div>
      <div className="sidebar-stat"><span>Saved projects</span><strong>{creations.length}</strong></div>
      <div className="sidebar-stat"><span>Images generated</span><strong>{completed}</strong></div>
      <div className="sidebar-bottom"><div className="mini-promo"><div className="promo-stars">✳ <span>✦</span></div><strong>Better ideas.<br/>Better clicks.</strong><p>Create your next best visual.</p></div><div className="side-note"><CircleHelp size={17}/> Private user library</div></div>
    </aside>
    <div className="mobile-backdrop" onClick={() => setMobileMenu(false)}/>
    <div className="app-main">
      <header className="topbar"><div className="topbar-path"><button className="mobile-toggle" onClick={() => setMobileMenu(!mobileMenu)}><Menu size={21}/></button> Workspace <ChevronRight size={14}/><strong>{view === 'create' ? 'Create studio' : 'My creations'}</strong></div><div className="topbar-right"><span className="health-indicator"><span/> {model || 'Connected'}</span><span className="user-email">{user.email}</span><button className="icon-action" onClick={logout} title="Sign out"><LogOut size={17}/></button></div></header>
      <main className="content">
        {view === 'create' ? <>
          <section className="hero"><div className="hero-copy"><span className="small-intro">✳ YOUR CREATIVE SIDEKICK</span><h1>Make every<br/>frame <em>count.</em></h1><p>You choose every detail. We turn your image and brief into thumbnails with real AI — and save them to your private library.</p><div className="hero-facts"><span><Sparkles size={15}/> Real image API</span><span><Layers size={15}/> Your settings, your style</span></div></div><div className="hero-deco">✳<small>MAKE IT YOURS</small></div></section>
          <div className="section-heading"><div><span className="overline">CREATE A NEW PROJECT</span><h2>Fine-tune your <i>vision.</i></h2></div><span className="section-ordinal">01 — 04</span></div>
          <form onSubmit={generate} className="new-studio-grid">
            <div className="studio-main-col">
              <section className="panel studio-section"><div className="step-heading"><span className="step-number">01</span><div><h3>Your reference image</h3><p>The photo will be used in AI image editing and saved on ImageKit.</p></div><ImagePlus size={19}/></div><label className="simple-upload">{preview ? <img src={preview} alt="Your reference preview"/> : <div className="upload-placeholder"><ImagePlus size={32}/><strong>Choose an image</strong><span>JPEG, PNG or WebP · Max 8 MB</span></div>}<input type="file" accept="image/jpeg,image/png,image/webp" disabled={busy} onChange={event => setFile(event.target.files?.[0] || null)}/></label>{file && <small className="small-hint">Selected: {file.name} · click the preview to change</small>}</section>
              <section className="panel studio-section"><div className="step-heading"><span className="step-number">02</span><div><h3>Write your creative brief</h3><p>Everything you type below becomes part of the actual AI prompt.</p></div><Settings2 size={19}/></div>
                <label className="field-label">WHAT IS THE VIDEO / POST ABOUT?<textarea value={form.prompt} onChange={e => update('prompt', e.target.value)} placeholder="e.g. FastAPI and PostgreSQL tutorial for beginners, modern developer workspace, confident portrait" required minLength={5} maxLength={1500}/></label>
                <div className="two-fields"><label className="field-label">MAIN HEADLINE<input maxLength={140} placeholder="FASTAPI IN 10 MIN" value={form.headline} onChange={e => update('headline', e.target.value)}/></label><label className="field-label">SUPPORTING TEXT<input maxLength={200} placeholder="Learn Python backend" value={form.subtitle} onChange={e => update('subtitle', e.target.value)}/></label></div>
                <label className="field-label">EXTRA ART DIRECTION<textarea className="small-textarea" value={form.extra_prompt} maxLength={1000} onChange={e => update('extra_prompt', e.target.value)} placeholder="e.g. dark navy backdrop, neon green glow, subject on the right, large text on the left"/></label>
              </section>
            </div>
            <div className="studio-side-col">
              <section className="panel studio-section"><div className="step-heading"><span className="step-number">03</span><div><h3>Select your style</h3><p>Generate one, two, or three styles in a single request.</p></div></div>
                <div className="style-select-grid">{presets.map(style => <button key={style.id} type="button" disabled={busy} className={`style-option ${style.color} ${form.styles.includes(style.id) ? 'selected' : ''}`} onClick={() => toggleStyle(style.id)} aria-pressed={form.styles.includes(style.id)}><span className="style-icon">{style.icon}</span><span><strong>{style.name}</strong><small>{style.label}</small></span><span className="style-tick">{form.styles.includes(style.id) && <Check size={15}/>}</span></button>)}</div>
                <div className="style-explainer"><span className="overline">YOUR SELECTED ART DIRECTION</span><p>{chosenStyles.map(item => item.instruction || item.label).join(' · ')}</p></div>
              </section>
              <section className="panel studio-section"><div className="step-heading"><span className="step-number">04</span><div><h3>Image API settings</h3><p>These choices go directly to your selected image model.</p></div></div>
                <label className="field-label">OUTPUT SIZE<select value={form.image_size} onChange={e => update('image_size', e.target.value)}>{SIZES.map(item => <option value={item.value} key={item.value}>{item.name} · {item.value}</option>)}</select></label>
                <div className="two-fields"><label className="field-label">QUALITY<select value={form.quality} onChange={e => update('quality', e.target.value)}><option value="low">Low (lower cost)</option><option value="medium">Medium</option><option value="high">High</option></select></label><label className="field-label">FILE FORMAT<select value={form.output_format} onChange={e => update('output_format', e.target.value)}><option value="jpeg">JPEG</option><option value="webp">WebP</option><option value="png">PNG</option></select></label></div>
                <p className="small-hint">Actual model: <strong>{model || 'backend/.env → IMAGE_MODEL'}</strong>. Low quality is the lower-cost default; every selected style makes one billable request.</p>
              </section>
              <section className="prompt-summary"><span className="overline">REQUEST PREVIEW</span><strong>{form.headline || 'Your headline goes here'}</strong><p>{form.subtitle || 'Optional supporting text'}</p><div>{form.styles.join(' + ')} <span>·</span> {form.image_size} <span>·</span> {form.quality} <span>·</span> {form.output_format.toUpperCase()}</div></section>
              {error && <div className="error-alert" role="alert">{error}</div>}
              <button className="generate-button" type="submit" disabled={busy || !form.styles.length}>{busy ? <><LoaderCircle className="spin" size={18}/> Generating with real AI…</> : <><WandSparkles size={19}/> Generate {form.styles.length} image{form.styles.length === 1 ? '' : 's'} <ArrowRight size={18}/></>}</button>
              <p className="below-action">No demo images. A paid image API call will run with your settings.</p>
            </div>
          </form>
          <section id="results" className="results-section"><div className="section-heading"><div><span className="overline">MOST RECENT PROJECT</span><h2>Fresh off the <i>press.</i></h2></div></div>{active ? <><div className="active-job-detail"><span className="job-title">{active.prompt}</span><span className="job-date">{new Date(active.created_at).toLocaleString()}</span></div><div className="output-grid">{active.images.map(img => <ImageCard key={img.id} image={img} options={active}/>)}</div></> : <div className="empty-project"><FileImage size={34}/><strong>Nothing generated yet</strong><p>Fill in your image settings above and generate your first project.</p></div>}</section>
        </> : <section className="library-view"><span className="overline">YOUR PRIVATE GALLERY</span><h1>Everything you've <em>made.</em></h1><p className="library-lead">These creations belong to {user.email}. FastAPI filters by your verified Supabase user ID.</p>{!creations.length ? <div className="empty-project"><FileImage size={32}/><strong>No creations yet</strong></div> : <div className="project-list">{creations.map(item => <article key={item.id} className="saved-project"><div className="saved-heading"><div><span className="overline">{new Date(item.created_at).toLocaleDateString()}</span><h3>{item.headline || item.prompt}</h3><p>{item.prompt}</p><small>{item.image_size} · {item.quality} · {item.model_name} · {item.images.length} styles</small></div><button onClick={() => { setActiveId(item.id); setView('create'); }}><ArrowRight size={18}/> View in studio</button></div><div className="output-grid">{item.images.map(img => <ImageCard key={img.id} image={img} options={item}/>)}</div></article>)}</div>}</section>}
      </main>
      <footer className="footer"><span>© 2026 Framecraft Studio</span><span>React × FastAPI × Supabase × ImageKit</span></footer>
    </div>
  </div>;
}

// The top-level page checks the cookie only once when the browser opens /.
export default function App() {
  const [user, setUser] = useState(null);
  // Loading prevents a brief flash of the login screen on refresh.
  const [checking, setChecking] = useState(true);
  useEffect(() => {
    api.me().then(result => setUser(result.user))
      .catch(() => setUser(null))
      .finally(() => setChecking(false));
  }, []);
  if (checking) return <div className="boot-screen"><Logo/><LoaderCircle className="spin" size={26}/><span>Checking secure session…</span></div>;
  // Successful login immediately displays the exact same dashboard.
  return user ? <Dashboard user={user} onLogout={() => setUser(null)}/> : <AuthPage onSuccess={setUser}/>;
}
