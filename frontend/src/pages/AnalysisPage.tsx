import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { resumeApi } from '../api/resumes';
import { jobApi, Job } from '../api/jobs';
import { analysisApi, FullAnalysisResponse, BulletImprovement } from '../api/analyses';
import { Resume } from '../types/resume';
import {
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  FileText,
  Briefcase,
  ArrowRight,
  Loader2,
  Compass,
  MessageSquare,
  Wand2,
} from 'lucide-react';

export const AnalysisPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const [resumes, setResumes] = useState<Resume[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selectedResumeId, setSelectedResumeId] = useState<string>('');
  const [selectedJobId, setSelectedJobId] = useState<string>(searchParams.get('job_id') || '');

  const [isRunning, setIsRunning] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<FullAnalysisResponse | null>(null);

  // Bullet Enhancer State
  const [inputBullet, setInputBullet] = useState('');
  const [isImprovingBullet, setIsImprovingBullet] = useState(false);
  const [improvedResult, setImprovedResult] = useState<BulletImprovement | null>(null);

  useEffect(() => {
    const loadInitialData = async () => {
      try {
        const [resumesData, jobsData] = await Promise.all([
          resumeApi.getResumes(),
          jobApi.getJobs(),
        ]);
        setResumes(resumesData.items);
        setJobs(jobsData);

        // Auto-select primary resume
        const primary = resumesData.items.find((r) => r.is_primary) || resumesData.items[0];
        if (primary) setSelectedResumeId(primary.id);
      } catch (err) {
        console.error('Failed loading initial options', err);
      }
    };
    loadInitialData();
  }, []);

  const handleRunAnalysis = async () => {
    if (!selectedResumeId) {
      alert('Please select a resume to analyze.');
      return;
    }

    setIsRunning(true);
    try {
      const data = await analysisApi.runAnalysis({
        resume_id: selectedResumeId,
        job_id: selectedJobId || undefined,
      });
      setAnalysisResult(data);
    } catch (err) {
      alert('Analysis execution failed. Please ensure the resume is parsed.');
    } finally {
      setIsRunning(false);
    }
  };

  const handleImproveBullet = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputBullet.trim()) return;

    setIsImprovingBullet(true);
    try {
      const targetRole = jobs.find((j) => j.id === selectedJobId)?.title || 'Software Engineer';
      const result = await analysisApi.improveBullet({
        bullet: inputBullet,
        target_role: targetRole,
      });
      setImprovedResult(result);
    } catch {
      alert('Failed to enhance bullet.');
    } finally {
      setIsImprovingBullet(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-extrabold tracking-tight text-white font-display">
          AI Career Intelligence & ATS Matcher
        </h1>
        <p className="text-sm text-slate-400 mt-1">
          Evaluate resume quality, benchmark ATS compatibility, discover skill gaps, and generate tailored recommendations
        </p>
      </div>

      {/* Selection Control Panel */}
      <div className="glass-panel p-6 rounded-2xl border border-slate-800 mb-10 shadow-xl">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5 items-end">
          {/* Select Resume */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <FileText className="h-4 w-4 text-brand-400" />
              <span>Select Candidate Resume *</span>
            </label>
            <select
              value={selectedResumeId}
              onChange={(e) => setSelectedResumeId(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-white text-sm focus:outline-none focus:border-brand-500"
            >
              <option value="">-- Choose Resume Document --</option>
              {resumes.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name} {r.is_primary ? '(Primary)' : ''}
                </option>
              ))}
            </select>
          </div>

          {/* Select Job */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <Briefcase className="h-4 w-4 text-emerald-400" />
              <span>Benchmark Target Job (Optional)</span>
            </label>
            <select
              value={selectedJobId}
              onChange={(e) => setSelectedJobId(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-white text-sm focus:outline-none focus:border-brand-500"
            >
              <option value="">-- Standalone Resume Audit (No Job) --</option>
              {jobs.map((j) => (
                <option key={j.id} value={j.id}>
                  {j.title} {j.company ? `at ${j.company}` : ''}
                </option>
              ))}
            </select>
          </div>

          {/* Trigger Button */}
          <div>
            <button
              onClick={handleRunAnalysis}
              disabled={isRunning || !selectedResumeId}
              className="w-full py-2.5 px-4 rounded-xl bg-gradient-to-r from-brand-600 to-teal-500 hover:from-brand-500 hover:to-teal-400 text-slate-950 font-bold text-sm flex items-center justify-center gap-2 transition-all shadow-lg shadow-brand-500/20 cursor-pointer disabled:opacity-50"
            >
              {isRunning ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Processing Analysis...</span>
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4 text-slate-950" />
                  <span>Run Comprehensive Evaluation</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Results View */}
      {analysisResult && (
        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
          {/* Top Score Dials */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-5">
            <div className="glass-panel p-6 rounded-2xl border border-brand-500/30 text-center">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                Overall Score
              </span>
              <div className="text-4xl font-extrabold text-white font-display mb-1">
                {analysisResult.overall_score}
                <span className="text-lg text-slate-500 font-normal">/100</span>
              </div>
              <span className="text-xs text-brand-400 font-medium">Weighted Composite</span>
            </div>

            <div className="glass-panel p-6 rounded-2xl border border-blue-500/30 text-center">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                ATS Score
              </span>
              <div className="text-4xl font-extrabold text-white font-display mb-1">
                {analysisResult.ats_score}
                <span className="text-lg text-slate-500 font-normal">/100</span>
              </div>
              <span className="text-xs text-blue-400 font-medium">Formatting & Keywords</span>
            </div>

            <div className="glass-panel p-6 rounded-2xl border border-emerald-500/30 text-center">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                Skill Match
              </span>
              <div className="text-4xl font-extrabold text-white font-display mb-1">
                {analysisResult.skill_score}
                <span className="text-lg text-slate-500 font-normal">/100</span>
              </div>
              <span className="text-xs text-emerald-400 font-medium">
                {analysisResult.skills_detected_count} skills verified
              </span>
            </div>

            <div className="glass-panel p-6 rounded-2xl border border-purple-500/30 text-center">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                Semantic Match
              </span>
              <div className="text-4xl font-extrabold text-white font-display mb-1">
                {analysisResult.semantic_score}
                <span className="text-lg text-slate-500 font-normal">/100</span>
              </div>
              <span className="text-xs text-purple-400 font-medium">Domain & Terminology</span>
            </div>
          </div>

          {/* Quick Action Navigation Bar */}
          {analysisResult.analysis_id && (
            <div className="flex flex-wrap items-center gap-4 p-4 rounded-2xl bg-slate-900 border border-slate-800">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Explore Modules:
              </span>
              <button
                onClick={() => navigate(`/roadmap?analysis_id=${analysisResult.analysis_id}`)}
                className="px-3.5 py-1.5 rounded-xl bg-brand-500/10 hover:bg-brand-500/20 text-brand-300 border border-brand-500/20 text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer"
              >
                <Compass className="h-3.5 w-3.5" />
                <span>Personalized Learning Roadmap ({analysisResult.roadmap_item_count} Stages)</span>
                <ArrowRight className="h-3 w-3" />
              </button>

              <button
                onClick={() => navigate(`/interview?analysis_id=${analysisResult.analysis_id}`)}
                className="px-3.5 py-1.5 rounded-xl bg-teal-500/10 hover:bg-teal-500/20 text-teal-300 border border-teal-500/20 text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer"
              >
                <MessageSquare className="h-3.5 w-3.5" />
                <span>Tailored Interview Questions ({analysisResult.interview_question_count} Qs)</span>
                <ArrowRight className="h-3 w-3" />
              </button>
            </div>
          )}

          {/* Matched vs Missing Skills Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Matched Skills */}
            <div className="glass-panel p-6 rounded-2xl border border-slate-800">
              <div className="flex items-center gap-2 mb-4">
                <CheckCircle2 className="h-5 w-5 text-emerald-400" />
                <h3 className="text-base font-bold text-white">
                  Matched Skills ({analysisResult.matched_skills.length})
                </h3>
              </div>
              <div className="flex flex-wrap gap-2">
                {analysisResult.matched_skills.length === 0 ? (
                  <span className="text-xs text-slate-500">Run with a target job to compare skills.</span>
                ) : (
                  analysisResult.matched_skills.map((s, idx) => (
                    <span
                      key={idx}
                      className="px-2.5 py-1 rounded-lg bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 text-xs font-medium"
                    >
                      {s}
                    </span>
                  ))
                )}
              </div>
            </div>

            {/* Missing Skills */}
            <div className="glass-panel p-6 rounded-2xl border border-slate-800">
              <div className="flex items-center gap-2 mb-4">
                <AlertTriangle className="h-5 w-5 text-rose-400" />
                <h3 className="text-base font-bold text-white">
                  Identified Skill Gaps ({analysisResult.missing_skills.length})
                </h3>
              </div>
              <div className="flex flex-wrap gap-2">
                {analysisResult.missing_skills.length === 0 ? (
                  <span className="text-xs text-slate-500">No critical missing skills detected!</span>
                ) : (
                  analysisResult.missing_skills.map((s, idx) => (
                    <span
                      key={idx}
                      className={`px-2.5 py-1 rounded-lg text-xs font-medium border ${
                        s.priority === 'high'
                          ? 'bg-rose-500/10 text-rose-300 border-rose-500/20'
                          : 'bg-amber-500/10 text-amber-300 border-amber-500/20'
                      }`}
                    >
                      {s.name} <span className="text-[10px] opacity-75 uppercase">({s.priority})</span>
                    </span>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* Strengths & Weaknesses */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="glass-panel p-6 rounded-2xl border border-slate-800">
              <h3 className="text-sm font-bold text-emerald-400 uppercase tracking-wider mb-3">
                Detected Strengths
              </h3>
              <ul className="space-y-2 text-xs text-slate-300">
                {analysisResult.strengths.map((str, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="text-emerald-400 font-bold">✓</span>
                    <span>{str}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="glass-panel p-6 rounded-2xl border border-slate-800">
              <h3 className="text-sm font-bold text-amber-400 uppercase tracking-wider mb-3">
                Areas for Improvement
              </h3>
              <ul className="space-y-2 text-xs text-slate-300">
                {analysisResult.weaknesses.map((w, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="text-amber-400 font-bold">!</span>
                    <span>{w}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* AI Recommendations */}
          <div className="glass-panel p-6 rounded-2xl border border-slate-800">
            <div className="flex items-center gap-2 mb-4">
              <Sparkles className="h-5 w-5 text-brand-400" />
              <h3 className="text-base font-bold text-white">AI Tailored Recommendations</h3>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {analysisResult.recommendations.map((rec, idx) => (
                <div key={idx} className="p-4 rounded-xl bg-slate-950/60 border border-slate-800">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="h-2 w-2 rounded-full bg-brand-400" />
                    <span className="text-xs font-bold text-white">Recommendation #{idx + 1}</span>
                  </div>
                  <p className="text-xs text-slate-300 leading-relaxed">{rec}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Interactive Bullet Enhancer Tool */}
          <div className="rounded-2xl bg-gradient-to-r from-slate-900 to-slate-850 border border-slate-800 p-8">
            <div className="flex items-center gap-2 mb-2">
              <Wand2 className="h-5 w-5 text-brand-400" />
              <h3 className="text-lg font-bold text-white">AI Resume Bullet Point Enhancer</h3>
            </div>
            <p className="text-xs text-slate-400 mb-6">
              Paste any bullet point from your resume to refactor it using action verbs and the STAR accomplishment framework.
            </p>

            <form onSubmit={handleImproveBullet} className="space-y-4">
              <div className="flex flex-col sm:flex-row gap-3">
                <input
                  type="text"
                  value={inputBullet}
                  onChange={(e) => setInputBullet(e.target.value)}
                  placeholder="e.g. Worked on database queries and helped backend APIs"
                  className="flex-1 px-4 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-white placeholder-slate-500 text-xs focus:outline-none focus:border-brand-500"
                />
                <button
                  type="submit"
                  disabled={isImprovingBullet || !inputBullet.trim()}
                  className="px-5 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-500 text-slate-950 font-bold text-xs flex items-center justify-center gap-2 transition-all cursor-pointer disabled:opacity-50"
                >
                  {isImprovingBullet ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Wand2 className="h-3.5 w-3.5" />}
                  <span>Refactor Bullet</span>
                </button>
              </div>

              {improvedResult && (
                <div className="p-4 rounded-xl bg-slate-950 border border-brand-500/30 space-y-2 mt-4 animate-in fade-in">
                  <div>
                    <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">
                      Refactored Bullet:
                    </span>
                    <p className="text-xs text-emerald-300 font-medium leading-relaxed mt-1">
                      {improvedResult.improved}
                    </p>
                  </div>
                  <div>
                    <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">
                      Why this works:
                    </span>
                    <p className="text-xs text-slate-400 leading-relaxed mt-0.5">
                      {improvedResult.rationale}
                    </p>
                  </div>
                </div>
              )}
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
