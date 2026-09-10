import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { analysisApi, InterviewQuestion } from '../api/analyses';
import {
  MessageSquare,
  HelpCircle,
  ChevronDown,
  ChevronUp,
  Lightbulb,
  Loader2,
  ArrowRight,
  ShieldCheck,
} from 'lucide-react';

export const InterviewPrepPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const analysisId = searchParams.get('analysis_id');

  const [questions, setQuestions] = useState<InterviewQuestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState<string>('All');
  const [expandedId, setExpandedId] = useState<string | null>(null);

  useEffect(() => {
    const fetchQuestions = async () => {
      try {
        setLoading(true);
        if (analysisId) {
          const data = await analysisApi.getInterviewQuestions(analysisId);
          setQuestions(data);
        } else {
          const list = await analysisApi.getAnalyses();
          if (list.length > 0) {
            const data = await analysisApi.getInterviewQuestions(list[0].id);
            setQuestions(data);
          }
        }
      } catch (err) {
        console.error('Failed to load interview questions', err);
      } finally {
        setLoading(false);
      }
    };
    fetchQuestions();
  }, [analysisId]);

  const categories = ['All', ...Array.from(new Set(questions.map((q) => q.category)))];

  const filtered = selectedCategory === 'All'
    ? questions
    : questions.filter((q) => q.category === selectedCategory);

  const toggleExpand = (id: string) => {
    setExpandedId(expandedId === id ? null : id);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 mb-8">
        <div>
          <div className="flex items-center gap-2 text-teal-400 text-xs font-semibold uppercase tracking-wider mb-1">
            <MessageSquare className="h-4 w-4" /> Targeted Technical & Behavioral Preparation
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white font-display">
            Role-Specific Interview Questions
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Practice questions synthesized directly from your resume's experience and target job requirements
          </p>
        </div>
      </div>

      {/* Category Filter Tabs */}
      {questions.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 mb-8">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
                selectedCategory === cat
                  ? 'bg-brand-600 text-slate-950 shadow-md shadow-brand-600/30'
                  : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      )}

      {loading ? (
        <div className="py-20 text-center">
          <Loader2 className="h-8 w-8 animate-spin text-brand-500 mx-auto mb-2" />
          <p className="text-xs text-slate-400">Synthesizing targeted interview prompts...</p>
        </div>
      ) : questions.length === 0 ? (
        <div className="glass-panel p-12 rounded-2xl border border-slate-800 text-center">
          <div className="h-16 w-16 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-500 mx-auto mb-4">
            <HelpCircle className="h-8 w-8" />
          </div>
          <h3 className="text-base font-bold text-white mb-1">No interview questions generated yet</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto mb-6">
            Run a resume-to-job matching evaluation in the Analysis module to generate customized behavioral and technical questions.
          </p>
          <button
            onClick={() => navigate('/analysis')}
            className="px-4 py-2 rounded-xl bg-brand-600 hover:bg-brand-500 text-slate-950 text-xs font-semibold inline-flex items-center gap-1.5 transition-colors cursor-pointer"
          >
            <span>Go to Analysis Matcher</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {filtered.map((q) => {
            const isExpanded = expandedId === q.id;
            return (
              <div
                key={q.id}
                className="glass-panel p-6 rounded-2xl border border-slate-800 hover:border-slate-700 transition-all"
              >
                <div
                  onClick={() => toggleExpand(q.id)}
                  className="flex items-start justify-between gap-4 cursor-pointer select-none"
                >
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <span className="px-2.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-slate-800 text-slate-300 border border-slate-700">
                        {q.category}
                      </span>
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border ${
                          q.difficulty === 'hard'
                            ? 'bg-rose-500/10 text-rose-300 border-rose-500/20'
                            : 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20'
                        }`}
                      >
                        {q.difficulty}
                      </span>
                    </div>

                    <h3 className="text-base font-bold text-white leading-relaxed">
                      {q.question}
                    </h3>
                  </div>

                  <div className="p-1 rounded-lg text-slate-400 hover:text-white transition-colors">
                    {isExpanded ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
                  </div>
                </div>

                {isExpanded && (
                  <div className="mt-6 pt-5 border-t border-slate-800/80 space-y-4 animate-in fade-in">
                    {q.why_it_matters && (
                      <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-850">
                        <div className="flex items-center gap-2 text-xs font-bold text-teal-400 uppercase tracking-wider mb-1">
                          <ShieldCheck className="h-4 w-4" />
                          <span>What Interviewers Are Looking For</span>
                        </div>
                        <p className="text-xs text-slate-300 leading-relaxed">
                          {q.why_it_matters}
                        </p>
                      </div>
                    )}

                    {q.answer_guidance && (
                      <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-850">
                        <div className="flex items-center gap-2 text-xs font-bold text-amber-400 uppercase tracking-wider mb-1">
                          <Lightbulb className="h-4 w-4" />
                          <span>Recommended Response Concepts & Strategy</span>
                        </div>
                        <p className="text-xs text-slate-300 leading-relaxed">
                          {q.answer_guidance}
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
