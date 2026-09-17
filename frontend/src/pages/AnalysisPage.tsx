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
  Bot,
  User as UserIcon,
  Copy,
  Check,
  RotateCcw,
  Send,
} from 'lucide-react';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  intent?: string;
  bullet_improvement?: BulletImprovement;
  timestamp: string;
}

export const AnalysisPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const [resumes, setResumes] = useState<Resume[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selectedResumeId, setSelectedResumeId] = useState<string>('');
  const [selectedJobId, setSelectedJobId] = useState<string>(searchParams.get('job_id') || '');

  const [isRunning, setIsRunning] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<FullAnalysisResponse | null>(null);

  // AI Resume Assistant Chat State
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [isAssistantSending, setIsAssistantSending] = useState(false);
  const [assistantError, setAssistantError] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  useEffect(() => {
    const loadInitialData = async () => {
      try {
        const [resumesData, jobsData] = await Promise.all([
          resumeApi.getResumes(),
          jobApi.getJobs(),
        ]);
        setResumes(resumesData.items);
        setJobs(jobsData);

        // Check if specific resume_id requested in URL params
        const paramResumeId = searchParams.get('resume_id');
        const matchingResume = paramResumeId
          ? resumesData.items.find((r) => r.id === paramResumeId)
          : null;

        if (matchingResume) {
          setSelectedResumeId(matchingResume.id);
        } else {
          // Fall back to primary or first available
          const primary = resumesData.items.find((r) => r.is_primary) || resumesData.items[0];
          if (primary) setSelectedResumeId(primary.id);
        }
      } catch (err) {
        console.error('Failed loading initial options', err);
      }
    };
    loadInitialData();
  }, []);

  // Sync selectedResumeId when query param changes
  useEffect(() => {
    const paramResumeId = searchParams.get('resume_id');
    if (paramResumeId && resumes.some((r) => r.id === paramResumeId)) {
      setSelectedResumeId(paramResumeId);
    }
  }, [searchParams, resumes]);

  // Reset conversation and prior analysis when switching selected resume to prevent cross-contamination
  useEffect(() => {
    setChatMessages([]);
    setAssistantError(null);
    setAnalysisResult(null);
  }, [selectedResumeId]);

  const selectedResume = resumes.find((r) => r.id === selectedResumeId);

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

  const handleSendMessage = async (customMessage?: string) => {
    const text = (customMessage || chatInput).trim();
    if (!text || isAssistantSending) return;

    if (!selectedResumeId) {
      alert('Please select a resume first so the assistant can analyze it.');
      return;
    }

    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setChatMessages((prev) => [...prev, userMsg]);
    if (!customMessage) setChatInput('');
    setIsAssistantSending(true);
    setAssistantError(null);

    try {
      const history = chatMessages.map((m) => ({ role: m.role, content: m.content }));
      const resp = await analysisApi.sendChatMessage({
        resume_id: selectedResumeId,
        message: text,
        job_id: selectedJobId || undefined,
        conversation_history: history,
      });

      const assistantMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: resp.answer,
        intent: resp.intent,
        bullet_improvement: resp.bullet_improvement,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };

      setChatMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      const msg = err?.response?.data?.detail || 'Failed to communicate with AI Resume Assistant.';
      setAssistantError(msg);
    } finally {
      setIsAssistantSending(false);
    }
  };

  const handleCopyBullet = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleClearChat = () => {
    setChatMessages([]);
    setAssistantError(null);
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
                  {r.name} ({r.original_filename}) {r.is_primary ? '⭐ Primary' : ''}
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
        </div>
      )}

      {/* AI Resume Assistant (Career Advisor & Bullet Enhancer) */}
      <div className="rounded-2xl bg-gradient-to-r from-slate-900 to-slate-850 border border-slate-800 p-6 md:p-8 shadow-2xl mt-8">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-4 pb-4 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-brand-500/10 border border-brand-500/30 text-brand-400">
              <Bot className="h-6 w-6" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                AI Resume Assistant
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 uppercase tracking-wider">
                  Live Local LLM
                </span>
              </h3>
              <div className="flex flex-wrap items-center gap-2 mt-1">
                <p className="text-xs text-slate-400">
                  Ask questions about your selected resume, discover ATS weaknesses, or paste bullet points to refactor.
                </p>
                {selectedResume && (
                  <span className="px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-brand-500/10 text-brand-300 border border-brand-500/30 flex items-center gap-1.5">
                    <FileText className="h-3 w-3 text-brand-400" />
                    Active Resume: {selectedResume.name}
                  </span>
                )}
              </div>
            </div>
          </div>
              {chatMessages.length > 0 && (
                <button
                  type="button"
                  onClick={handleClearChat}
                  className="px-3 py-1.5 rounded-lg border border-slate-800 bg-slate-950/60 hover:bg-slate-800 text-slate-400 hover:text-white text-xs flex items-center gap-1.5 transition-colors cursor-pointer"
                >
                  <RotateCcw className="h-3.5 w-3.5" />
                  <span>Clear Conversation</span>
                </button>
              )}
            </div>

            {/* Quick Action Suggestion Chips */}
            <div className="mb-6">
              <span className="text-[11px] font-medium text-slate-400 block mb-2">Suggested Inquiries:</span>
              <div className="flex flex-wrap gap-2">
                {[
                  'What should I improve in my resume?',
                  'Why is my ATS score low?',
                  'What skills am I missing?',
                  'Improve this bullet: Developed a Python API',
                ].map((promptText, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => handleSendMessage(promptText)}
                    disabled={isAssistantSending}
                    className="px-3 py-1.5 rounded-xl bg-slate-950/70 border border-slate-800 hover:border-brand-500/50 text-slate-300 hover:text-brand-300 text-xs transition-all cursor-pointer disabled:opacity-50 text-left"
                  >
                    ✨ {promptText}
                  </button>
                ))}
              </div>
            </div>

            {/* Chat Conversation History */}
            {chatMessages.length > 0 && (
              <div className="space-y-4 mb-6 max-h-[460px] overflow-y-auto pr-1">
                {chatMessages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`flex flex-col ${
                      msg.role === 'user' ? 'items-end' : 'items-start'
                    }`}
                  >
                    <div className="flex items-center gap-2 mb-1 px-1">
                      {msg.role === 'user' ? (
                        <>
                          <span className="text-[11px] text-slate-500">{msg.timestamp}</span>
                          <span className="text-xs font-semibold text-slate-300 flex items-center gap-1">
                            You <UserIcon className="h-3 w-3 text-slate-400" />
                          </span>
                        </>
                      ) : (
                        <>
                          <span className="text-xs font-semibold text-brand-400 flex items-center gap-1">
                            <Bot className="h-3.5 w-3.5" /> AI Career Advisor
                          </span>
                          {msg.intent && (
                            <span className="px-2 py-0.5 rounded-md text-[10px] font-medium bg-slate-800 text-slate-300 border border-slate-700">
                              Intent: {msg.intent.replace('_', ' ')}
                            </span>
                          )}
                          <span className="text-[11px] text-slate-500">{msg.timestamp}</span>
                        </>
                      )}
                    </div>

                    <div
                      className={`p-4 rounded-2xl max-w-2xl text-xs leading-relaxed ${
                        msg.role === 'user'
                          ? 'bg-brand-950/40 border border-brand-500/30 text-slate-100 rounded-tr-none'
                          : 'bg-slate-950/90 border border-slate-800 text-slate-200 rounded-tl-none space-y-3'
                      }`}
                    >
                      <div className="whitespace-pre-wrap">{msg.content}</div>

                      {/* Structured Bullet Improvement Card */}
                      {msg.bullet_improvement && (
                        <div className="mt-3 p-3.5 rounded-xl bg-slate-900 border border-brand-500/40 space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                              Refactored Bullet:
                            </span>
                            <button
                              type="button"
                              onClick={() => handleCopyBullet(msg.bullet_improvement!.improved, msg.id)}
                              className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-[11px] text-slate-300 flex items-center gap-1 transition-colors cursor-pointer"
                            >
                              {copiedId === msg.id ? (
                                <>
                                  <Check className="h-3 w-3 text-emerald-400" />
                                  <span className="text-emerald-400">Copied</span>
                                </>
                              ) : (
                                <>
                                  <Copy className="h-3 w-3 text-slate-400" />
                                  <span>Copy</span>
                                </>
                              )}
                            </button>
                          </div>
                          <p className="text-xs text-emerald-300 font-medium leading-relaxed">
                            {msg.bullet_improvement.improved}
                          </p>
                          <div>
                            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">
                              Why this works:
                            </span>
                            <p className="text-xs text-slate-400 leading-relaxed mt-0.5">
                              {msg.bullet_improvement.rationale}
                            </p>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {assistantError && (
              <div className="mb-4 p-3 rounded-xl bg-red-950/40 border border-red-800/60 text-red-300 text-xs flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-red-400 shrink-0" />
                <span>{assistantError}</span>
              </div>
            )}

            {/* Input bar */}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSendMessage();
              }}
              className="space-y-3"
            >
              <div className="flex flex-col sm:flex-row gap-3">
                <input
                  type="text"
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  placeholder="Ask about your resume or paste a bullet point to improve..."
                  disabled={isAssistantSending}
                  className="flex-1 px-4 py-3 rounded-xl bg-slate-950 border border-slate-800 text-white placeholder-slate-500 text-xs focus:outline-none focus:border-brand-500 transition-colors"
                />
                <button
                  type="submit"
                  disabled={isAssistantSending || !chatInput.trim()}
                  className="px-6 py-3 rounded-xl bg-brand-600 hover:bg-brand-500 text-slate-950 font-bold text-xs flex items-center justify-center gap-2 transition-all cursor-pointer disabled:opacity-50 shadow-lg shadow-brand-500/10"
                >
                  {isAssistantSending ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      <span>Thinking...</span>
                    </>
                  ) : (
                    <>
                      <Send className="h-4 w-4" />
                      <span>Send</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
    </div>
  );
};
