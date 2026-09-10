import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { 
  FileText, 
  Briefcase, 
  Sparkles, 
  CheckCircle2, 
  ArrowRight, 
  Activity,
  Layers
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const LandingPage: React.FC = () => {
  const { isAuthenticated } = useAuth();
  const [health, setHealth] = useState<{ status: string } | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    fetch('/health')
      .then((res) => res.json())
      .then((data) => {
        setHealth(data);
        setLoading(false);
      })
      .catch((err) => {
        console.warn('Backend not currently reachable via proxy:', err);
        setLoading(false);
      });
  }, []);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 flex flex-col justify-center">
      <div className="text-center max-w-3xl mx-auto mb-16">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-brand-500/10 border border-brand-500/20 text-brand-400 text-xs font-semibold mb-6">
          <Sparkles className="h-3.5 w-3.5" /> Next-Gen AI Resume & Job Matching Architecture
        </div>
        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-white leading-tight mb-6 font-display">
          Bridge the Gap Between <span className="bg-gradient-to-r from-teal-400 via-brand-500 to-emerald-400 bg-clip-text text-transparent">Your Resume</span> & Target Roles
        </h1>
        <p className="text-lg text-slate-400 leading-relaxed mb-8">
          Deconstruct resumes with geometric NLP parsing, evaluate ATS quality transparently, match against job requirements using dense embeddings, and receive actionable upskilling roadmaps.
        </p>

        <div className="flex items-center justify-center gap-4">
          {isAuthenticated ? (
            <Link
              to="/dashboard"
              className="px-6 py-3 rounded-xl bg-brand-600 hover:bg-brand-500 text-slate-950 font-bold text-sm transition-all shadow-lg shadow-brand-600/30 flex items-center gap-2"
            >
              <span>Go to Dashboard</span>
              <ArrowRight className="h-4 w-4" />
            </Link>
          ) : (
            <>
              <Link
                to="/register"
                className="px-6 py-3 rounded-xl bg-brand-600 hover:bg-brand-500 text-slate-950 font-bold text-sm transition-all shadow-lg shadow-brand-600/30 flex items-center gap-2"
              >
                <span>Get Started Free</span>
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link
                to="/login"
                className="px-6 py-3 rounded-xl bg-slate-900 hover:bg-slate-850 border border-slate-700/80 text-white font-semibold text-sm transition-all"
              >
                Sign In
              </Link>
            </>
          )}
        </div>
      </div>

      {/* Feature Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-16">
        <div className="glass-panel p-6 rounded-2xl border border-slate-800 glass-panel-hover">
          <div className="h-12 w-12 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center mb-4 text-blue-400">
            <FileText className="h-6 w-6" />
          </div>
          <h3 className="text-lg font-bold text-white mb-2">Resume Intelligence</h3>
          <p className="text-sm text-slate-400 leading-relaxed mb-4">
            Multi-format extraction (PDF, DOCX, TXT) with section segmentation, 1,200+ skill taxonomy matching, and ATS quality benchmarking.
          </p>
          <div className="flex items-center text-xs text-blue-400 font-semibold gap-1">
            <span>Section NLP & ATS Scoring</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </div>
        </div>

        <div className="glass-panel p-6 rounded-2xl border border-slate-800 glass-panel-hover">
          <div className="h-12 w-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mb-4 text-emerald-400">
            <Briefcase className="h-6 w-6" />
          </div>
          <h3 className="text-lg font-bold text-white mb-2">Job Requirement Parser</h3>
          <p className="text-sm text-slate-400 leading-relaxed mb-4">
            Dissects raw job postings into mandatory vs. preferred skills, required experience levels, and domain responsibilities.
          </p>
          <div className="flex items-center text-xs text-emerald-400 font-semibold gap-1">
            <span>Requirement Matrix</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </div>
        </div>

        <div className="glass-panel p-6 rounded-2xl border border-slate-800 glass-panel-hover">
          <div className="h-12 w-12 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center mb-4 text-purple-400">
            <Layers className="h-6 w-6" />
          </div>
          <h3 className="text-lg font-bold text-white mb-2">Semantic Match Engine</h3>
          <p className="text-sm text-slate-400 leading-relaxed mb-4">
            Hybrid matching combining deterministic skill overlap with sentence-transformers embeddings for deep contextual alignment.
          </p>
          <div className="flex items-center text-xs text-purple-400 font-semibold gap-1">
            <span>Cosine Vectors & Roadmap</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </div>
        </div>
      </div>

      {/* System Status Banner */}
      <div className="rounded-2xl bg-gradient-to-r from-slate-900 to-slate-850 border border-slate-800 p-6 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="h-10 w-10 rounded-full bg-brand-500/20 text-brand-400 flex items-center justify-center">
            <CheckCircle2 className="h-5 w-5" />
          </div>
          <div>
            <h4 className="text-white font-semibold">Phase 3: Authentication & Security Subsystem Active</h4>
            <p className="text-xs text-slate-400">
              JWT Bearer auth, bcrypt password security, session token rotation, and candidate profile management ready.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-xs font-mono text-brand-400">
          <Activity className={`h-3 w-3 ${health?.status === 'healthy' ? 'text-emerald-400 animate-pulse' : 'text-amber-400'}`} />
          <span>{loading ? 'Probing...' : health?.status === 'healthy' ? 'API Operational' : 'Offline'}</span>
        </div>
      </div>
    </div>
  );
};
