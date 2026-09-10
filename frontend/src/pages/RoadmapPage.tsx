import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { analysisApi, RoadmapResponse } from '../api/analyses';
import {
  Compass,
  CheckCircle2,
  Clock,
  ArrowRight,
  Loader2,
  Layers,
} from 'lucide-react';

export const RoadmapPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const analysisId = searchParams.get('analysis_id');

  const [roadmap, setRoadmap] = useState<RoadmapResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [completedItems, setCompletedItems] = useState<Record<string, boolean>>({});

  useEffect(() => {
    const fetchRoadmap = async () => {
      try {
        setLoading(true);
        if (analysisId) {
          const data = await analysisApi.getRoadmap(analysisId);
          setRoadmap(data);
        } else {
          // Fetch latest analysis
          const list = await analysisApi.getAnalyses();
          if (list.length > 0) {
            const data = await analysisApi.getRoadmap(list[0].id);
            setRoadmap(data);
          }
        }
      } catch (err) {
        console.error('Failed to load roadmap', err);
      } finally {
        setLoading(false);
      }
    };
    fetchRoadmap();
  }, [analysisId]);

  const toggleComplete = (id: string) => {
    setCompletedItems((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const completedCount = Object.values(completedItems).filter(Boolean).length;
  const totalCount = roadmap?.items.length || 0;
  const progressPercent = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 mb-8">
        <div>
          <div className="flex items-center gap-2 text-brand-400 text-xs font-semibold uppercase tracking-wider mb-1">
            <Compass className="h-4 w-4" /> Career Skill Acquisition Engine
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white font-display">
            {roadmap?.title || 'Personalized Learning Roadmap'}
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            {roadmap?.description || 'Custom stage-by-stage curriculum to bridge missing technical requirements'}
          </p>
        </div>

        {roadmap && (
          <div className="flex items-center gap-4 p-3 rounded-2xl bg-slate-900 border border-slate-800">
            <div className="text-right">
              <span className="text-xs text-slate-400 font-medium block">Curriculum Progress</span>
              <span className="text-sm font-bold text-white">
                {completedCount} of {totalCount} Completed ({progressPercent}%)
              </span>
            </div>
            <div className="h-10 w-10 rounded-xl bg-brand-500/10 border border-brand-500/20 flex items-center justify-center text-brand-400 font-bold text-xs">
              {progressPercent}%
            </div>
          </div>
        )}
      </div>

      {loading ? (
        <div className="py-20 text-center">
          <Loader2 className="h-8 w-8 animate-spin text-brand-500 mx-auto mb-2" />
          <p className="text-xs text-slate-400">Synthesizing personalized curriculum...</p>
        </div>
      ) : !roadmap || roadmap.items.length === 0 ? (
        <div className="glass-panel p-12 rounded-2xl border border-slate-800 text-center">
          <div className="h-16 w-16 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-500 mx-auto mb-4">
            <Compass className="h-8 w-8" />
          </div>
          <h3 className="text-base font-bold text-white mb-1">No active roadmap generated yet</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto mb-6">
            Run a resume-to-job matching evaluation in the Analysis module to identify skill gaps and generate your custom learning path.
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
          {roadmap.items.map((item, index) => {
            const isDone = Boolean(completedItems[item.id]);
            return (
              <div
                key={item.id}
                className={`glass-panel p-6 rounded-2xl border transition-all ${
                  isDone
                    ? 'border-emerald-500/30 bg-emerald-950/10'
                    : 'border-slate-800 hover:border-slate-700'
                }`}
              >
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                  <div className="flex items-start gap-4">
                    <button
                      onClick={() => toggleComplete(item.id)}
                      className={`h-8 w-8 rounded-xl flex items-center justify-center transition-colors shrink-0 mt-0.5 cursor-pointer ${
                        isDone
                          ? 'bg-emerald-500 text-slate-950'
                          : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
                      }`}
                    >
                      <CheckCircle2 className="h-5 w-5" />
                    </button>

                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                          Stage {index + 1}
                        </span>
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border ${
                            item.priority === 'high'
                              ? 'bg-rose-500/10 text-rose-300 border-rose-500/20'
                              : 'bg-amber-500/10 text-amber-300 border-amber-500/20'
                          }`}
                        >
                          {item.priority} Priority
                        </span>
                      </div>
                      <h3
                        className={`text-base font-bold transition-all ${
                          isDone ? 'line-through text-slate-500' : 'text-white'
                        }`}
                      >
                        {item.topic}
                      </h3>
                      <div className="flex items-center gap-4 text-xs text-slate-400 mt-2">
                        <div className="flex items-center gap-1.5">
                          <Clock className="h-3.5 w-3.5 text-slate-500" />
                          <span>Estimated {item.estimated_days} days</span>
                        </div>
                        {item.prerequisites && item.prerequisites.length > 0 && (
                          <div className="flex items-center gap-1.5">
                            <Layers className="h-3.5 w-3.5 text-slate-500" />
                            <span>Prerequisites: {item.prerequisites.join(', ')}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>

                  <span
                    className={`text-xs font-semibold shrink-0 ${
                      isDone ? 'text-emerald-400' : 'text-slate-500'
                    }`}
                  >
                    {isDone ? 'Completed' : 'Pending'}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
