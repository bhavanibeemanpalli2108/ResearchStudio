import { useEffect, useState } from 'react';
import { Link, NavLink, Route, Routes, useNavigate } from 'react-router-dom';
import {
  Activity,
  ArrowUpRight,
  Atom,
  BookOpen,
  Command,
  FlaskConical,
  LayoutDashboard,
  Lightbulb,
  Menu,
  Moon,
  Plus,
  Search,
  Settings,
  ShieldCheck,
  Sun,
  Workflow,
  X,
} from 'lucide-react';
import { Dashboard, HistoryPage, SettingsPage } from './pages';
import { CreatePage } from './create';
import { RunPage } from './run';
import { Button, Modal, useTheme } from './ui';
import { useProjects } from './hooks';
const navigation = [
  { to: '/', label: 'Overview', icon: LayoutDashboard },
  { to: '/history', label: 'Research projects', icon: BookOpen },
  { to: '/workspace', label: 'Live workspace', icon: Workflow },
  { to: '/ideas', label: 'Idea explorer', icon: Lightbulb },
  { to: '/experiments', label: 'Experiments', icon: FlaskConical },
  { to: '/analytics', label: 'Analytics', icon: Activity },
  { to: '/explainability', label: 'Explainability', icon: ShieldCheck },
  { to: '/paper', label: 'Paper & artifacts', icon: BookOpen },
];
export function App() {
  const { theme, toggle } = useTheme();
  const [mobile, setMobile] = useState(false);
  const [search, setSearch] = useState(false);
  const [term, setTerm] = useState('');
  const projects = useProjects();
  const navigate = useNavigate();
  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        setSearch((open) => !open);
      }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, []);
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <aside className={`sidebar ${mobile ? 'open' : ''}`}>
        <Link to="/" className="brand" onClick={() => setMobile(false)}>
          <span className="brand-mark">
            <Atom size={24} />
          </span>
          <span>Reseon</span>
        </Link>
        <div className="nav-label">WORKSPACE</div>
        <nav aria-label="Main navigation">
          {navigation.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} end={to === '/'} onClick={() => setMobile(false)}>
              <Icon size={17} />
              {label}
              {to === '/workspace' && <span className="nav-dot" />}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="local-card">
            <span className={projects.isError ? 'offline-dot' : 'green-dot'} />
            {projects.isError
              ? 'Backend unavailable'
              : projects.isLoading
                ? 'Connecting to backend'
                : 'Connected to local backend'}
            <p>Your research. Your infrastructure.</p>
            <a href="http://127.0.0.1:8765" target="_blank" rel="noreferrer">
              Open upstream inspector
              <ArrowUpRight size={13} />
            </a>
          </div>
          <NavLink className="bottom-link" to="/settings">
            <Settings size={17} />
            Settings & providers
          </NavLink>
          <div className="profile">
            <span className="profile-avatar">RS</span>
            <div>
              Researcher<small>Local workspace</small>
            </div>
            <span className="version">v0.1</span>
          </div>
        </div>
      </aside>
      {mobile && (
        <button
          className="mobile-scrim"
          aria-label="Close navigation"
          onClick={() => setMobile(false)}
        />
      )}
      <div className="main-shell">
        <header className="topbar">
          <div className="topbar-left">
            <button
              className="icon-button mobile-menu"
              aria-label="Open navigation"
              onClick={() => setMobile(true)}
            >
              <Menu size={20} />
            </button>
            <span className="topbar-product">Agentic Scientist</span>
            <span className="topbar-slash">/</span>
            <span>Research platform</span>
            <span className="beta">BETA</span>
          </div>
          <div className="topbar-right">
            <button className="search-trigger" onClick={() => setSearch(true)}>
              <Search size={14} />
              <span>Search projects</span>
              <kbd>
                <Command size={10} /> K
              </kbd>
            </button>
            <button
              className="icon-button"
              onClick={toggle}
              aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}
            >
              {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
            </button>
            <Link to="/create" className="button primary small">
              <Plus size={15} />
              <span>New research</span>
            </Link>
          </div>
        </header>
        <main id="main" className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/create" element={<CreatePage />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="/projects/:projectId" element={<HistoryPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            {['workspace', 'ideas', 'experiments', 'analytics', 'explainability', 'paper'].map(
              (section) => (
                <Route
                  key={section}
                  path={`/${section}/:runId?`}
                  element={<RunPage section={section} />}
                />
              ),
            )}
            <Route
              path="*"
              element={
                <div className="empty">
                  <h1>Page not found</h1>
                  <Link to="/">Return to overview</Link>
                </div>
              }
            />
          </Routes>
          <footer className="page-footer">
            <span>
              <Atom size={12} /> Built for curious minds.
            </span>
            <span>Agentic Scientist · Local-first research</span>
          </footer>
        </main>
      </div>
      <Modal
        open={search}
        onOpenChange={setSearch}
        title="Find your research"
        description="Search projects in this workspace."
      >
        <div className="search-field">
          <Search size={18} />
          <input
            autoFocus
            value={term}
            onChange={(e) => setTerm(e.target.value)}
            placeholder="Search by title, question, or domain"
            aria-label="Search projects"
          />
          {term && (
            <button className="icon-button" onClick={() => setTerm('')} aria-label="Clear search">
              <X size={15} />
            </button>
          )}
        </div>
        <div className="search-results">
          {projects.data
            ?.filter((p) =>
              `${p.title} ${p.question} ${p.domain}`.toLowerCase().includes(term.toLowerCase()),
            )
            .map((p) => (
              <button
                key={p.id}
                onClick={() => {
                  setSearch(false);
                  navigate(`/projects/${p.id}`);
                }}
              >
                <BookOpen size={16} />
                <span>
                  {p.title}
                  <small>{p.domain}</small>
                </span>
                <ArrowUpRight size={15} />
              </button>
            ))}
          {!projects.data?.length && <p>No projects yet. Start your first research project.</p>}
        </div>
        <Button
          variant="secondary"
          onClick={() => {
            setSearch(false);
            navigate('/create');
          }}
        >
          <Plus size={16} />
          Start new research
        </Button>
      </Modal>
    </div>
  );
}
