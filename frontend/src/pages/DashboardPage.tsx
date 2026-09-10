import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { resumeApi } from '../api/resumes';
import { jobApi } from '../api/jobs';
import { analysisApi, AnalysisListItem } from '../api/analyses';
import { Resume } from '../types/resume';
import {
  FileText,
  Briefcase,
  Sparkles,
  ShieldCheck,
  User,
  Target,
  Compass,
  MessageSquare,
  History,
  ArrowRight,
} from 'lucide-react';

export const DashboardPage: React.FC = () => {
  const { user, profile } = useAuth();
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [jobsCount, setJobsCount] = useState(0);
  const [recentAnalyses, setRecentAnalyses] = useState<AnalysisListItem[]>([]);

  useEffect(() => {
    const loadStats = async () => {
      try {
        const [resumesData, jobsData, analysesData] = await Promise.all([
          resumeApi.getResumes(),
          jobApi.getJobs(),
          analysisApi.getAnalyses(),
        ]);
        setResumes(resumesData.items);
        setJobsCount(jobsData.length);
        setRecentAnalyses(analysesData);
      } catch (err) {
        console.error('Failed to load dashboard metrics', err);
      }
    };
    loadStats();
  }, []);

  const primaryResume = resumes.find((r) => r.is_primary) || resumes[0];
  const latestAnalysis = recentAnalyses[0];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      {/* Welcome Header */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 mb-8">
        <div>
          <div className="flex items-center gap-2 text-brand-400 text-xs font-semibold uppercase tracking-wider mb-1">
            <ShieldCheck className="h-4 w-4" /> Authenticated Candidate Intelligence Portal
          </div>
          <h1 className="text-3xl font-extrabold text-white font-display">
            Welcome, {profile?.full_name || user?.email?.split('@')[0]}
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            {profile?.target_role ? `${profile.target_role} • ` : ''}
            {profile?.years_of_experience ? `${profile.years_of_experience} yrs exp • ` : ''}
            {user?.email}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            to="/profile"
            className="px-4 py-2 rounded-xl bg-slate-900 border border-slate-700/80 hover:border-brand-500/40 text-slate-300 hover:text-white text-xs font-semibold flex items-center gap-2 transition-all shadow-sm"
          >
            <User className="h-3.5 w-3.5 text-brand-400" />
            <span>Profile</span>
          </Link>

          <Link
            to="/analysis"
            className="px-4 py-2 rounded-xl bg-brand-600 hover:bg-brand-500 text-slate-950 text-xs font-bold flex items-center gap-2 transition-all shadow-md shadow-brand-600/30"
          >
            <Sparkles className="h-3.5 w-3.5" />
            <span>Run Matcher</span>
          </Link>
        </div>
      </div>

      {/* Quick Status Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 mb-10">
        <Link
          to="/resumes"
          className="glass-panel p-5 rounded-2xl border border-slate-800 hover:border-brand-500/40 transition-all group block"
        >
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider group-hover:text-brand-300 transition-colors">
              Primary Resume
            </span>
            <FileText className="h-4 w-4 text-blue-400 group-hover:scale-110 transition-transform" />
          </div>
          <div className="text-xl font-bold text-white group-hover:text-brand-400 transition-colors truncate">
            {primaryResume ? primaryResume.name : 'Upload Resume'}
          </div>
          <span className="text-xs text-slate-500 mt-1 block">
            {resumes.length} document{resumes.length === 1 ? '' : 's'} managed
          </span>
        </Link>

        <Link
          to="/jobs"
          className="glass-panel p-5 rounded-2xl border border-slate-800 hover:border-emerald-500/40 transition-all group block"
        >
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider group-hover:text-emerald-300 transition-colors">
              Target Jobs
            </span>
            <Briefcase className="h-4 w-4 text-emerald-400 group-hover:scale-110 transition-transform" />
          </div>
          <div className="text-xl font-bold text-white group-hover:text-emerald-400 transition-colors">
            {jobsCount} Job{jobsCount === 1 ? '' : 's'}
          </div>
          <span className="text-xs text-slate-500 mt-1 block">Tracked opportunities</span>
        </Link>

        <Link
          to="/analysis"
          className="glass-panel p-5 rounded-2xl border border-slate-800 hover:border-purple-500/40 transition-all group block"
        >
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider group-hover:text-purple-300 transition-colors">
              Latest Match Score
            </span>
            <Target className="h-4 w-4 text-purple-400 group-hover:scale-110 transition-transform" />
          </div>
          <div className="text-xl font-bold text-white group-hover:text-purple-400 transition-colors">
            {latestAnalysis && latestAnalysis.overall_score !== null ? `${latestAnalysis.overall_score}%` : '—'}
          </div>
          <span className="text-xs text-slate-500 mt-1 block truncate">
            {latestAnalysis ? latestAnalysis.job_title || 'Standalone Audit' : 'Ready to evaluate'}
          </span>
        </Link>

        <Link
          to="/history"
          className="glass-panel p-5 rounded-2xl border border-slate-800 hover:border-teal-500/40 transition-all group block"
        >
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider group-hover:text-teal-300 transition-colors">
              Evaluations
            </span>
            <History className="h-4 w-4 text-teal-400 group-hover:scale-110 transition-transform" />
          </div>
          <div className="text-xl font-bold text-white group-hover:text-teal-400 transition-colors">
            {recentAnalyses.length}
          </div>
          <span className="text-xs text-slate-500 mt-1 block">Historical runs logged</span>
        </Link>
      </div>

      {/* Action Navigation Grid */}
      <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
        <Sparkles className="h-4 w-4 text-brand-400" />
        <span>Career Intelligence Navigation</span>
      </h2>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-10">
        <Link
          to="/analysis"
          className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 hover:border-brand-500/40 hover:bg-slate-900 transition-all group"
        >
          <div className="h-10 w-10 rounded-xl bg-brand-500/10 border border-brand-500/20 flex items-center justify-center text-brand-400 mb-4 group-hover:scale-105 transition-transform">
            <Target className="h-5 w-5" />
          </div>
          <h3 className="text-base font-bold text-white mb-1 group-hover:text-brand-300 transition-colors">
            Resume ↔ Job Matcher
          </h3>
          <p className="text-xs text-slate-400 leading-relaxed mb-4">
            Benchmark resume against any job posting, calculate match percentage, find missing skills, and run ATS audit.
          </p>
          <span className="text-xs font-semibold text-brand-400 flex items-center gap-1">
            <span>Launch Matcher</span>
            <ArrowRight className="h-3 w-3 group-hover:translate-x-1 transition-transform" />
          </span>
        </Link>

        <Link
          to="/roadmap"
          className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 hover:border-teal-500/40 hover:bg-slate-900 transition-all group"
        >
          <div className="h-10 w-10 rounded-xl bg-teal-500/10 border border-teal-500/20 flex items-center justify-center text-teal-400 mb-4 group-hover:scale-105 transition-transform">
            <Compass className="h-5 w-5" />
          </div>
          <h3 className="text-base font-bold text-white mb-1 group-hover:text-teal-300 transition-colors">
            Personalized Roadmap
          </h3>
          <p className="text-xs text-slate-400 leading-relaxed mb-4">
            Stage-by-stage learning curriculum generated specifically to bridge missing technical requirements and skill gaps.
          </p>
          <span className="text-xs font-semibold text-teal-400 flex items-center gap-1">
            <span>View Learning Path</span>
            <ArrowRight className="h-3 w-3 group-hover:translate-x-1 transition-transform" />
          </span>
        </Link>

        <Link
          to="/interview"
          className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 hover:border-purple-500/40 hover:bg-slate-900 transition-all group"
        >
          <div className="h-10 w-10 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400 mb-4 group-hover:scale-105 transition-transform">
            <MessageSquare className="h-5 w-5" />
          </div>
          <h3 className="text-base font-bold text-white mb-1 group-hover:text-purple-300 transition-colors">
            Interview Preparation
          </h3>
          <p className="text-xs text-slate-400 leading-relaxed mb-4">
            Practice targeted technical, system design, and behavioral questions synthesized from your experience and target role.
          </p>
          <span className="text-xs font-semibold text-purple-400 flex items-center gap-1">
            <span>Practice Questions</span>
            <ArrowRight className="h-3 w-3 group-hover:translate-x-1 transition-transform" />
          </span>
        </Link>
      </div>
    </div>
  );
};

