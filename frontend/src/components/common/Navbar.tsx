import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { Sparkles, User as UserIcon, LogOut, LayoutDashboard, FileText, Briefcase, Target, Compass, HelpCircle, History } from 'lucide-react';

export const Navbar: React.FC = () => {
  const { user, profile, isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <header className="border-b border-slate-800/80 bg-slate-900/60 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-brand-600 to-teal-400 flex items-center justify-center shadow-lg shadow-brand-500/20">
            <Sparkles className="h-5 w-5 text-slate-950" />
          </div>
          <div>
            <span className="font-display font-bold text-lg tracking-tight text-white block leading-tight">
              ResumeAI<span className="text-brand-500">.matcher</span>
            </span>
            <span className="text-xs text-slate-400 font-medium">Precision Career Intelligence</span>
          </div>
        </Link>

        <nav className="flex items-center gap-1 sm:gap-2">
          {isAuthenticated ? (
            <>
              <Link
                to="/dashboard"
                className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs sm:text-sm font-medium text-slate-300 hover:text-white hover:bg-slate-800/60 transition-colors"
              >
                <LayoutDashboard className="h-4 w-4 text-brand-400" />
                <span className="hidden md:inline">Dashboard</span>
              </Link>

              <Link
                to="/resumes"
                className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs sm:text-sm font-medium text-slate-300 hover:text-white hover:bg-slate-800/60 transition-colors"
              >
                <FileText className="h-4 w-4 text-brand-400" />
                <span className="hidden md:inline">Resumes</span>
              </Link>

              <Link
                to="/jobs"
                className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs sm:text-sm font-medium text-slate-300 hover:text-white hover:bg-slate-800/60 transition-colors"
              >
                <Briefcase className="h-4 w-4 text-amber-400" />
                <span className="hidden md:inline">Jobs</span>
              </Link>

              <Link
                to="/analysis"
                className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs sm:text-sm font-medium text-slate-300 hover:text-white hover:bg-slate-800/60 transition-colors"
              >
                <Target className="h-4 w-4 text-teal-400" />
                <span className="hidden md:inline">Analysis</span>
              </Link>

              <Link
                to="/roadmap"
                className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs sm:text-sm font-medium text-slate-300 hover:text-white hover:bg-slate-800/60 transition-colors"
              >
                <Compass className="h-4 w-4 text-purple-400" />
                <span className="hidden lg:inline">Roadmap</span>
              </Link>

              <Link
                to="/interview"
                className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs sm:text-sm font-medium text-slate-300 hover:text-white hover:bg-slate-800/60 transition-colors"
              >
                <HelpCircle className="h-4 w-4 text-emerald-400" />
                <span className="hidden lg:inline">Interview</span>
              </Link>

              <Link
                to="/history"
                className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs sm:text-sm font-medium text-slate-300 hover:text-white hover:bg-slate-800/60 transition-colors"
              >
                <History className="h-4 w-4 text-sky-400" />
                <span className="hidden xl:inline">History</span>
              </Link>

              <Link
                to="/profile"
                className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs sm:text-sm font-medium text-slate-300 hover:text-white hover:bg-slate-800/60 transition-colors"
              >
                <UserIcon className="h-4 w-4 text-teal-400" />
                <span className="hidden sm:inline">{profile?.full_name || user?.email?.split('@')[0]}</span>
              </Link>

              <button
                onClick={handleLogout}
                className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 border border-rose-500/20 transition-colors"
                title="Sign out"
              >
                <LogOut className="h-3.5 w-3.5" />
                <span>Logout</span>
              </button>
            </>
          ) : (
            <>
              <Link
                to="/login"
                className="px-3.5 py-1.5 rounded-lg text-sm font-medium text-slate-300 hover:text-white hover:bg-slate-800/60 transition-colors"
              >
                Sign In
              </Link>
              <Link
                to="/register"
                className="px-4 py-1.5 rounded-lg bg-brand-600 hover:bg-brand-500 text-slate-950 font-semibold text-sm transition-colors shadow-md shadow-brand-600/30"
              >
                Create Account
              </Link>
            </>
          )}
        </nav>
      </div>
    </header>
  );
};
