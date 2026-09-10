import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { analysisApi, AnalysisListItem } from '../api/analyses';
import {
  History,
  FileText,
  Briefcase,
  Calendar,
  ArrowRight,
  Loader2,
  TrendingUp,
} from 'lucide-react';

export const AnalysisHistoryPage: React.FC = () => {
  const navigate = useNavigate();
  const [analyses, setAnalyses] = useState<AnalysisListItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        setLoading(true);
        const data = await analysisApi.getAnalyses();
        setAnalyses(data);
      } catch (err) {
        console.error('Failed to load history', err);
      } finally {
        setLoading(false);
      }
    };
    fetchHistory();
  }, []);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <div className="mb-8">
        <div className="flex items-center gap-2 text-brand-400 text-xs font-semibold uppercase tracking-wider mb-1">
          <History className="h-4 w-4" /> Historical Evaluations & Progression
        </div>
        <h1 className="text-3xl font-extrabold tracking-tight text-white font-display">
          Analysis & Match History
        </h1>
        <p className="text-sm text-slate-400 mt-1">
          Review score improvements, ATS audits, and matching evaluations conducted across your career progression
        </p>
      </div>

      {loading ? (
        <div className="py-20 text-center">
          <Loader2 className="h-8 w-8 animate-spin text-brand-500 mx-auto mb-2" />
          <p className="text-xs text-slate-400">Loading analysis history...</p>
        </div>
      ) : analyses.length === 0 ? (
        <div className="glass-panel p-12 rounded-2xl border border-slate-800 text-center">
          <div className="h-16 w-16 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-500 mx-auto mb-4">
            <TrendingUp className="h-8 w-8" />
          </div>
          <h3 className="text-base font-bold text-white mb-1">No evaluations completed yet</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto mb-6">
            Run your first resume evaluation or benchmark against a job description in the Analysis module.
          </p>
          <button
            onClick={() => navigate('/analysis')}
            className="px-4 py-2 rounded-xl bg-brand-600 hover:bg-brand-500 text-slate-950 text-xs font-semibold inline-flex items-center gap-1.5 transition-colors cursor-pointer"
          >
            <span>Run First Evaluation</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {analyses.map((item) => (
            <div
              key={item.id}
              className="glass-panel p-6 rounded-2xl border border-slate-800 hover:border-slate-700 transition-all flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6"
            >
              <div className="space-y-2">
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-1.5 text-xs text-slate-300 font-semibold">
                    <FileText className="h-4 w-4 text-brand-400" />
                    <span>{item.resume_name}</span>
                  </div>

                  {item.job_title && (
                    <>
                      <span className="text-slate-600">•</span>
                      <div className="flex items-center gap-1.5 text-xs text-emerald-300 font-medium">
                        <Briefcase className="h-3.5 w-3.5 text-emerald-400" />
                        <span>{item.job_title}</span>
                      </div>
                    </>
                  )}
                </div>

                <div className="flex items-center gap-4 text-xs text-slate-500">
                  <div className="flex items-center gap-1">
                    <Calendar className="h-3.5 w-3.5 text-slate-600" />
                    <span>{new Date(item.created_at).toLocaleDateString()}</span>
                  </div>
                  <span className="capitalize px-2 py-0.5 rounded bg-slate-900 text-slate-400 text-[10px]">
                    {item.status}
                  </span>
                </div>
              </div>

              {/* Scores Cluster */}
              <div className="flex items-center gap-6">
                <div className="text-center">
                  <span className="text-[10px] uppercase font-bold text-slate-500 block">Overall</span>
                  <span className="text-xl font-extrabold text-white">
                    {item.overall_score !== null ? `${item.overall_score}%` : '—'}
                  </span>
                </div>

                <div className="text-center">
                  <span className="text-[10px] uppercase font-bold text-slate-500 block">ATS</span>
                  <span className="text-xl font-extrabold text-blue-400">
                    {item.ats_score !== null ? `${item.ats_score}%` : '—'}
                  </span>
                </div>

                <div className="text-center">
                  <span className="text-[10px] uppercase font-bold text-slate-500 block">Skill</span>
                  <span className="text-xl font-extrabold text-emerald-400">
                    {item.skill_score !== null ? `${item.skill_score}%` : '—'}
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => navigate(`/roadmap?analysis_id=${item.id}`)}
                    className="p-2 rounded-xl bg-slate-800 text-slate-300 hover:text-white text-xs font-semibold transition-colors cursor-pointer"
                    title="View Roadmap"
                  >
                    Roadmap
                  </button>
                  <button
                    onClick={() => navigate(`/interview?analysis_id=${item.id}`)}
                    className="p-2 rounded-xl bg-slate-800 text-slate-300 hover:text-white text-xs font-semibold transition-colors cursor-pointer"
                    title="View Interview Qs"
                  >
                    Interview
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
