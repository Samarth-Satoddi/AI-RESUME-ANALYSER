import React, { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { jobApi, Job } from '../api/jobs';
import {
  jobSearchApi,
  RankedJobOpportunity,
  SavedJob,
  SearchListItem,
  JobSearchQuery,
} from '../api/jobSearch';
import { resumeApi } from '../api/resumes';
import { Resume } from '../types/resume';
import {
  Briefcase,
  Plus,
  Trash2,
  ExternalLink,
  Loader2,
  Calendar,
  Building,
  Target,
  Sparkles,
  X,
  Search,
  Bookmark,
  BookmarkCheck,
  CheckCircle2,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  MapPin,
  Clock,
  DollarSign,
  ArrowUpDown,
  RotateCcw,
  Globe,
} from 'lucide-react';

type TabType = 'discovered' | 'saved' | 'manual' | 'history';

export const JobsPage: React.FC = () => {
  const navigate = useNavigate();

  // Active Tab
  const [activeTab, setActiveTab] = useState<TabType>('discovered');

  // Manual Jobs State
  const [manualJobs, setManualJobs] = useState<Job[]>([]);
  const [manualLoading, setManualLoading] = useState(false);

  // Discovered Jobs & Search State
  const [discoveredJobs, setDiscoveredJobs] = useState<RankedJobOpportunity[]>([]);
  const [discoveredLoading, setDiscoveredLoading] = useState(false);
  const [activeSearchId, setActiveSearchId] = useState<string | null>(null);
  const [searchStatus, setSearchStatus] = useState<string | null>(null);
  const [searchStats, setSearchStats] = useState<{ found: number; analyzed: number; matched: number }>({
    found: 0,
    analyzed: 0,
    matched: 0,
  });

  // Saved Jobs State
  const [savedJobs, setSavedJobs] = useState<SavedJob[]>([]);
  const [savedLoading, setSavedLoading] = useState(false);

  // Search History State
  const [searchHistory, setSearchHistory] = useState<SearchListItem[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  // Filter & Sort State
  const [minScoreFilter, setMinScoreFilter] = useState<number>(0);
  const [remoteOnlyFilter, setRemoteOnlyFilter] = useState<boolean>(false);
  const [keywordFilter, setKeywordFilter] = useState<string>('');
  const [sortBy, setSortBy] = useState<string>('best_match');
  const [expandedCardId, setExpandedCardId] = useState<string | null>(null);

  // Resumes for Selection
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [selectedResumeId, setSelectedResumeId] = useState<string>('');

  // Modals
  const [showManualModal, setShowManualModal] = useState(false);
  const [showSearchModal, setShowSearchModal] = useState(false);

  // Manual Form State
  const [isManualSubmitting, setIsManualSubmitting] = useState(false);
  const [manualTitle, setManualTitle] = useState('');
  const [manualCompany, setManualCompany] = useState('');
  const [manualDescription, setManualDescription] = useState('');
  const [manualSourceUrl, setManualSourceUrl] = useState('');

  // Search Form State
  const [searchRole, setSearchRole] = useState('Python Backend Developer');
  const [searchLocation, setSearchLocation] = useState('Bangalore');
  const [searchRemote, setSearchRemote] = useState(true);
  const [searchExperience, setSearchExperience] = useState('0-2 years');
  const [searchEmploymentType, setSearchEmploymentType] = useState('full-time');
  const [searchPostedDays, setSearchPostedDays] = useState(14);
  const [searchSkills, setSearchSkills] = useState<string[]>([]);
  const [skillInput, setSkillInput] = useState('');
  const [isSearchSubmitting, setIsSearchSubmitting] = useState(false);

  // Polling Ref
  const pollTimerRef = useRef<number | null>(null);

  // Load initial data
  useEffect(() => {
    fetchResumesAndDefaults();
    fetchManualJobs();
    fetchSavedJobs();
    fetchHistory();
  }, []);

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollTimerRef.current) {
        window.clearTimeout(pollTimerRef.current);
      }
    };
  }, []);

  const fetchResumesAndDefaults = async () => {
    try {
      const [resData, defData] = await Promise.all([
        resumeApi.getResumes(),
        jobSearchApi.getDefaults(),
      ]);

      if (resData.items && resData.items.length > 0) {
        setResumes(resData.items);
        const primary = resData.items.find((r) => r.is_primary) || resData.items[0];
        setSelectedResumeId(defData.recommended_resume_id || primary.id);
      }

      if (defData.target_role) setSearchRole(defData.target_role);
      if (defData.location) setSearchLocation(defData.location);
      if (defData.experience_level) setSearchExperience(defData.experience_level);
      if (defData.skills && defData.skills.length > 0) setSearchSkills(defData.skills);
    } catch {
      // Graceful fallback to defaults
    }
  };

  const fetchManualJobs = async () => {
    try {
      setManualLoading(true);
      const data = await jobApi.getJobs();
      setManualJobs(data);
    } catch {
      // Ignored
    } finally {
      setManualLoading(false);
    }
  };

  const fetchSavedJobs = async () => {
    try {
      setSavedLoading(true);
      const data = await jobSearchApi.getSavedJobs();
      setSavedJobs(data);
    } catch {
      // Ignored
    } finally {
      setSavedLoading(false);
    }
  };

  const fetchHistory = async () => {
    try {
      setHistoryLoading(true);
      const data = await jobSearchApi.listSearches();
      setSearchHistory(data);
      // If searches exist and no active search results loaded yet, load latest search results
      if (data.length > 0 && !activeSearchId) {
        loadSearchResults(data[0].id);
      }
    } catch {
      // Ignored
    } finally {
      setHistoryLoading(false);
    }
  };

  const loadSearchResults = async (searchId: string) => {
    try {
      setDiscoveredLoading(true);
      setActiveSearchId(searchId);
      const res = await jobSearchApi.getSearchResults(searchId, {
        min_score: minScoreFilter > 0 ? minScoreFilter : undefined,
        remote_only: remoteOnlyFilter ? true : undefined,
        sort_by: sortBy,
      });
      setDiscoveredJobs(res.results);
      setActiveTab('discovered');
    } catch {
      // Ignored
    } finally {
      setDiscoveredLoading(false);
    }
  };

  // Poll search status until completed
  const pollSearchStatus = async (searchId: string) => {
    try {
      const statusRes = await jobSearchApi.getSearchStatus(searchId);
      setSearchStatus(statusRes.status);
      setSearchStats({
        found: statusRes.jobs_found,
        analyzed: statusRes.jobs_analyzed,
        matched: statusRes.jobs_matched,
      });

      if (statusRes.status === 'completed') {
        loadSearchResults(searchId);
        fetchHistory();
      } else if (statusRes.status === 'failed') {
        alert(`Job search failed: ${statusRes.error_message || 'Unknown error'}`);
        setDiscoveredLoading(false);
      } else {
        // Keep polling
        pollTimerRef.current = window.setTimeout(() => pollSearchStatus(searchId), 1500);
      }
    } catch {
      setDiscoveredLoading(false);
    }
  };

  const handleStartSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchRole.trim()) {
      alert('Please specify a target role.');
      return;
    }

    setIsSearchSubmitting(true);
    setDiscoveredLoading(true);
    setShowSearchModal(false);
    setActiveTab('discovered');

    try {
      const query: JobSearchQuery = {
        role: searchRole.trim(),
        location: searchLocation.trim() || undefined,
        remote: searchRemote,
        experience: searchExperience,
        employment_type: searchEmploymentType,
        posted_within_days: searchPostedDays,
        skills: searchSkills,
        resume_id: selectedResumeId || undefined,
        limit: 30,
      };

      const startRes = await jobSearchApi.startSearch(query);
      setActiveSearchId(startRes.search_id);
      setSearchStatus(startRes.status);
      setSearchStats({ found: 0, analyzed: 0, matched: 0 });

      // Start polling
      pollSearchStatus(startRes.search_id);
    } catch {
      alert('Failed to initiate job search agent.');
      setDiscoveredLoading(false);
    } finally {
      setIsSearchSubmitting(false);
    }
  };

  const handleCreateManualJob = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!manualTitle.trim() || !manualDescription.trim()) {
      alert('Job title and description are required.');
      return;
    }

    setIsManualSubmitting(true);
    try {
      const created = await jobApi.createJob({
        title: manualTitle,
        company: manualCompany || undefined,
        description: manualDescription,
        source_url: manualSourceUrl || undefined,
      });
      setManualJobs([created, ...manualJobs]);
      setShowManualModal(false);
      setManualTitle('');
      setManualCompany('');
      setManualDescription('');
      setManualSourceUrl('');
      setActiveTab('manual');
    } catch {
      alert('Failed to parse job description.');
    } finally {
      setIsManualSubmitting(false);
    }
  };

  const handleDeleteManualJob = async (id: string, jobTitle: string) => {
    if (!window.confirm(`Delete job posting for "${jobTitle}"?`)) return;
    try {
      await jobApi.deleteJob(id);
      setManualJobs(manualJobs.filter((j) => j.id !== id));
    } catch {
      alert('Failed to delete job.');
    }
  };

  const handleToggleSaveJob = async (job: RankedJobOpportunity) => {
    try {
      if (job.is_saved) {
        await jobSearchApi.unsaveJob(job.listing_id);
        setDiscoveredJobs((prev) =>
          prev.map((j) => (j.listing_id === job.listing_id ? { ...j, is_saved: false, application_status: 'discovered' } : j))
        );
        setSavedJobs((prev) => prev.filter((s) => s.job_listing_id !== job.listing_id));
      } else {
        const saved = await jobSearchApi.saveJob(job.listing_id);
        setDiscoveredJobs((prev) =>
          prev.map((j) => (j.listing_id === job.listing_id ? { ...j, is_saved: true, application_status: 'saved' } : j))
        );
        setSavedJobs([saved, ...savedJobs]);
      }
    } catch {
      alert('Failed to update bookmark.');
    }
  };

  const handleUpdateStatus = async (listingId: string, newStatus: string) => {
    try {
      const updated = await jobSearchApi.updateApplicationStatus(listingId, newStatus);
      setSavedJobs((prev) =>
        prev.map((s) => (s.job_listing_id === listingId ? updated : s))
      );
      setDiscoveredJobs((prev) =>
        prev.map((j) => (j.listing_id === listingId ? { ...j, application_status: newStatus, is_saved: true } : j))
      );
    } catch {
      alert('Failed to update application status.');
    }
  };

  const addSkillChip = () => {
    if (skillInput.trim() && !searchSkills.includes(skillInput.trim())) {
      setSearchSkills([...searchSkills, skillInput.trim()]);
      setSkillInput('');
    }
  };

  const removeSkillChip = (skill: string) => {
    setSearchSkills(searchSkills.filter((s) => s !== skill));
  };

  // Filter and sort discovered jobs client-side if needed
  const filteredDiscoveredJobs = discoveredJobs.filter((job) => {
    if (minScoreFilter > 0 && job.overall_match_score < minScoreFilter) return false;
    if (remoteOnlyFilter && job.remote_type !== 'remote') return false;
    if (keywordFilter.trim()) {
      const kw = keywordFilter.toLowerCase();
      const matchInTitle = job.title.toLowerCase().includes(kw);
      const matchInCompany = (job.company || '').toLowerCase().includes(kw);
      const matchInSkills = job.matched_skills.some((s) => s.toLowerCase().includes(kw));
      if (!matchInTitle && !matchInCompany && !matchInSkills) return false;
    }
    return true;
  });

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30';
    if (score >= 60) return 'text-cyan-400 bg-cyan-500/10 border-cyan-500/30';
    return 'text-amber-400 bg-amber-500/10 border-amber-500/30';
  };

  const getSourceBadge = (source: string) => {
    const s = (source || '').toLowerCase();
    if (s.includes('greenhouse')) {
      return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
    } else if (s.includes('remotive')) {
      return 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20';
    } else if (s.includes('arbeitnow')) {
      return 'bg-purple-500/10 text-purple-400 border-purple-500/20';
    } else if (s.includes('mock') || s.includes('development')) {
      return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
    }
    return 'bg-slate-800/60 text-slate-300 border-slate-700';
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      {/* Header */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 mb-8">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-3xl font-extrabold tracking-tight text-white font-display">
              Target Job Opportunities
            </h1>
            <span className="px-2.5 py-0.5 rounded-full bg-brand-500/10 border border-brand-500/30 text-brand-400 text-xs font-bold tracking-wide uppercase">
              AI Agent Enabled
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Discover matching job listings automatically or deconstruct manual descriptions to benchmark resume alignment
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowManualModal(true)}
            className="px-4 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white border border-slate-800 font-semibold text-xs flex items-center gap-2 transition-all cursor-pointer shadow-sm"
          >
            <Plus className="h-4 w-4" />
            <span>+ Manual Job</span>
          </button>

          <button
            onClick={() => setShowSearchModal(true)}
            className="px-4 py-2.5 rounded-xl bg-gradient-to-r from-brand-600 to-cyan-600 hover:from-brand-500 hover:to-cyan-500 text-slate-950 font-bold text-xs flex items-center gap-2 transition-all shadow-lg shadow-brand-600/30 cursor-pointer"
          >
            <Search className="h-4 w-4" />
            <span>🔎 Find Jobs Automatically</span>
          </button>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800/80 mb-6 pb-2 overflow-x-auto">
        <button
          onClick={() => setActiveTab('discovered')}
          className={`px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-2 transition-all cursor-pointer ${
            activeTab === 'discovered'
              ? 'bg-brand-500/15 text-brand-400 border border-brand-500/30 shadow-sm'
              : 'text-slate-400 hover:text-white hover:bg-slate-900'
          }`}
        >
          <Sparkles className="h-3.5 w-3.5" />
          <span>AI Discovered Jobs</span>
          {discoveredJobs.length > 0 && (
            <span className="px-1.5 py-0.2 rounded-md bg-brand-500/20 text-brand-300 text-[10px]">
              {discoveredJobs.length}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab('saved')}
          className={`px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-2 transition-all cursor-pointer ${
            activeTab === 'saved'
              ? 'bg-brand-500/15 text-brand-400 border border-brand-500/30 shadow-sm'
              : 'text-slate-400 hover:text-white hover:bg-slate-900'
          }`}
        >
          <Bookmark className="h-3.5 w-3.5" />
          <span>Saved & Applications</span>
          {savedJobs.length > 0 && (
            <span className="px-1.5 py-0.2 rounded-md bg-slate-800 text-slate-300 text-[10px]">
              {savedJobs.length}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab('manual')}
          className={`px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-2 transition-all cursor-pointer ${
            activeTab === 'manual'
              ? 'bg-brand-500/15 text-brand-400 border border-brand-500/30 shadow-sm'
              : 'text-slate-400 hover:text-white hover:bg-slate-900'
          }`}
        >
          <Briefcase className="h-3.5 w-3.5" />
          <span>Manual Opportunities</span>
          {manualJobs.length > 0 && (
            <span className="px-1.5 py-0.2 rounded-md bg-slate-800 text-slate-300 text-[10px]">
              {manualJobs.length}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab('history')}
          className={`px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-2 transition-all cursor-pointer ${
            activeTab === 'history'
              ? 'bg-brand-500/15 text-brand-400 border border-brand-500/30 shadow-sm'
              : 'text-slate-400 hover:text-white hover:bg-slate-900'
          }`}
        >
          <Clock className="h-3.5 w-3.5" />
          <span>Search History</span>
          {searchHistory.length > 0 && (
            <span className="px-1.5 py-0.2 rounded-md bg-slate-800 text-slate-300 text-[10px]">
              {searchHistory.length}
            </span>
          )}
        </button>
      </div>

      {/* SEARCH PROGRESS BANNER */}
      {discoveredLoading && (
        <div className="glass-panel p-6 rounded-2xl border border-brand-500/30 bg-brand-500/5 mb-8 animate-in fade-in">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-4">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-xl bg-brand-500/20 border border-brand-500/30 flex items-center justify-center text-brand-400">
                <Loader2 className="h-5 w-5 animate-spin" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <span>AI Job Search Agent In Progress</span>
                  <span className="text-xs px-2 py-0.5 rounded bg-brand-500/20 text-brand-300 font-mono">
                    {searchStatus?.toUpperCase() || 'SEARCHING'}
                  </span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Scanning verified job sources, extracting requirements, and matching against your selected resume
                </p>
              </div>
            </div>

            <div className="flex items-center gap-4 text-xs font-mono text-slate-300 bg-slate-950/60 px-4 py-2 rounded-xl border border-slate-800">
              <div>Found: <span className="font-bold text-cyan-400">{searchStats.found}</span></div>
              <div>Analyzed: <span className="font-bold text-amber-400">{searchStats.analyzed}</span></div>
              <div>Matched: <span className="font-bold text-brand-400">{searchStats.matched}</span></div>
            </div>
          </div>

          {/* Stepper Progress */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 pt-2 border-t border-slate-800/80 text-[11px]">
            <div className="flex items-center gap-1.5 text-brand-400">
              <CheckCircle2 className="h-3.5 w-3.5" />
              <span>Query Sources</span>
            </div>
            <div className="flex items-center gap-1.5 text-brand-400">
              <CheckCircle2 className="h-3.5 w-3.5" />
              <span>Normalize & Deduplicate</span>
            </div>
            <div className={`flex items-center gap-1.5 ${searchStatus === 'analyzing' || searchStatus === 'matching' ? 'text-brand-400' : 'text-slate-500'}`}>
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              <span>Analyze Requirements</span>
            </div>
            <div className={`flex items-center gap-1.5 ${searchStatus === 'matching' ? 'text-brand-400' : 'text-slate-500'}`}>
              <Target className="h-3.5 w-3.5" />
              <span>Match & Rank Jobs</span>
            </div>
          </div>
        </div>
      )}

      {/* ================= TAB 1: AI DISCOVERED JOBS ================= */}
      {activeTab === 'discovered' && (
        <div>
          {/* Filters & Sorting Toolbar */}
          <div className="glass-panel p-4 rounded-2xl border border-slate-800/80 mb-6 flex flex-wrap items-center justify-between gap-4">
            <div className="flex flex-wrap items-center gap-3">
              <div className="relative">
                <Search className="h-3.5 w-3.5 text-slate-500 absolute left-3 top-3" />
                <input
                  type="text"
                  value={keywordFilter}
                  onChange={(e) => setKeywordFilter(e.target.value)}
                  placeholder="Filter by role, company, skill..."
                  className="pl-8 pr-3 py-1.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-brand-500 w-48 sm:w-64"
                />
              </div>

              {/* Match Score Presets */}
              <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-xl border border-slate-800 text-xs">
                <button
                  onClick={() => setMinScoreFilter(0)}
                  className={`px-2.5 py-1 rounded-lg font-medium transition-colors ${
                    minScoreFilter === 0 ? 'bg-brand-500/20 text-brand-300' : 'text-slate-400 hover:text-white'
                  }`}
                >
                  All Matches
                </button>
                <button
                  onClick={() => setMinScoreFilter(60)}
                  className={`px-2.5 py-1 rounded-lg font-medium transition-colors ${
                    minScoreFilter === 60 ? 'bg-cyan-500/20 text-cyan-300' : 'text-slate-400 hover:text-white'
                  }`}
                >
                  60%+
                </button>
                <button
                  onClick={() => setMinScoreFilter(80)}
                  className={`px-2.5 py-1 rounded-lg font-medium transition-colors ${
                    minScoreFilter === 80 ? 'bg-emerald-500/20 text-emerald-300' : 'text-slate-400 hover:text-white'
                  }`}
                >
                  80%+ High Match
                </button>
              </div>

              {/* Remote Toggle */}
              <button
                onClick={() => setRemoteOnlyFilter(!remoteOnlyFilter)}
                className={`px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all flex items-center gap-1.5 cursor-pointer ${
                  remoteOnlyFilter
                    ? 'bg-cyan-500/15 border-cyan-500/30 text-cyan-400'
                    : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-white'
                }`}
              >
                <span>Remote Only</span>
              </button>
            </div>

            {/* Sort Selector */}
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-500 flex items-center gap-1">
                <ArrowUpDown className="h-3 w-3" />
                <span>Sort by:</span>
              </span>
              <select
                value={sortBy}
                onChange={(e) => {
                  setSortBy(e.target.value);
                  if (activeSearchId) loadSearchResults(activeSearchId);
                }}
                className="px-3 py-1.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white focus:outline-none focus:border-brand-500"
              >
                <option value="best_match">Best Composite Match</option>
                <option value="highest_skill">Highest Skill Match</option>
                <option value="experience">Best Experience Fit</option>
                <option value="newest">Newest Postings</option>
              </select>
            </div>
          </div>

          {/* Results List */}
          {discoveredJobs.length === 0 && !discoveredLoading ? (
            <div className="glass-panel p-12 rounded-2xl border border-slate-800 text-center">
              <div className="h-16 w-16 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-500 mx-auto mb-4">
                <Sparkles className="h-8 w-8 text-brand-400" />
              </div>
              <h3 className="text-base font-bold text-white mb-1">No AI Job Searches Run Yet</h3>
              <p className="text-xs text-slate-400 max-w-md mx-auto mb-6">
                Launch the Job Search Agent to automatically scan verified feeds, analyze skill overlap, and rank opportunities tailored to your resume.
              </p>
              <button
                onClick={() => setShowSearchModal(true)}
                className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-brand-600 to-cyan-600 hover:from-brand-500 hover:to-cyan-500 text-slate-950 text-xs font-bold inline-flex items-center gap-2 transition-all cursor-pointer shadow-lg shadow-brand-600/20"
              >
                <Search className="h-4 w-4" />
                <span>Find Matching Jobs Now</span>
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              {filteredDiscoveredJobs.map((job) => {
                const isExpanded = expandedCardId === job.listing_id;

                return (
                  <div
                    key={job.listing_id}
                    className="glass-panel p-6 rounded-2xl border border-slate-800/90 hover:border-slate-700 transition-all bg-slate-900/40"
                  >
                    <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                      {/* Left Header */}
                      <div className="space-y-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="text-xs font-mono font-bold text-slate-500">#{job.rank}</span>
                          <h3 className="text-lg font-bold text-white leading-tight">{job.title}</h3>
                          {job.remote_type === 'remote' && (
                            <span className="px-2 py-0.5 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 text-[10px] font-bold">
                              Remote
                            </span>
                          )}
                          {job.remote_type === 'hybrid' && (
                            <span className="px-2 py-0.5 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-400 text-[10px] font-bold">
                              Hybrid
                            </span>
                          )}
                        </div>

                        <div className="flex flex-wrap items-center gap-4 text-xs text-slate-400 pt-0.5">
                          {job.company && (
                            <div className="flex items-center gap-1.5 text-slate-300 font-medium">
                              <Building className="h-3.5 w-3.5 text-slate-500" />
                              <span>{job.company}</span>
                            </div>
                          )}
                          {job.location && (
                            <div className="flex items-center gap-1 text-slate-400">
                              <MapPin className="h-3.5 w-3.5 text-slate-500" />
                              <span>{job.location}</span>
                            </div>
                          )}
                          {job.salary_min && (
                            <div className="flex items-center gap-1 text-emerald-400 font-mono">
                              <DollarSign className="h-3.5 w-3.5" />
                              <span>
                                {job.salary_min.toLocaleString()} - {job.salary_max ? job.salary_max.toLocaleString() : ''} {job.currency}
                              </span>
                            </div>
                          )}
                          {job.posted_at && (
                            <div className="flex items-center gap-1 text-slate-500">
                              <Calendar className="h-3.5 w-3.5" />
                              <span>{new Date(job.posted_at).toLocaleDateString()}</span>
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Right: Match Score Badge & Bookmark */}
                      <div className="flex items-center gap-3 self-end md:self-auto">
                        <div
                          className={`px-3.5 py-1.5 rounded-xl border font-mono font-bold text-sm flex items-center gap-2 ${getScoreColor(
                            job.overall_match_score
                          )}`}
                        >
                          <Target className="h-4 w-4" />
                          <span>{job.overall_match_score.toFixed(0)}% MATCH</span>
                        </div>

                        <button
                          onClick={() => handleToggleSaveJob(job)}
                          className={`p-2 rounded-xl border transition-colors cursor-pointer ${
                            job.is_saved
                              ? 'bg-brand-500/20 border-brand-500/40 text-brand-300'
                              : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-white'
                          }`}
                          title={job.is_saved ? 'Unsave Job' : 'Save Job Opportunity'}
                        >
                          {job.is_saved ? <BookmarkCheck className="h-4 w-4" /> : <Bookmark className="h-4 w-4" />}
                        </button>
                      </div>
                    </div>

                    {/* AI Explanation Snippet */}
                    {job.ai_explanation && (
                      <div className="mt-4 p-3 rounded-xl bg-slate-950/80 border border-slate-800/80 text-xs text-slate-300 flex items-start gap-2.5">
                        <Sparkles className="h-4 w-4 text-brand-400 shrink-0 mt-0.5" />
                        <p className="leading-relaxed">{job.ai_explanation}</p>
                      </div>
                    )}

                    {/* Skills Summary */}
                    <div className="mt-4 flex flex-wrap items-center gap-2">
                      {job.matched_skills.slice(0, 5).map((skill, idx) => (
                        <span
                          key={idx}
                          className="px-2.5 py-1 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-[11px] font-medium flex items-center gap-1"
                        >
                          <CheckCircle2 className="h-3 w-3 text-emerald-400" />
                          <span>{skill}</span>
                        </span>
                      ))}

                      {job.missing_skills.slice(0, 3).map((ms, idx) => (
                        <span
                          key={idx}
                          className={`px-2.5 py-1 rounded-lg border text-[11px] font-medium flex items-center gap-1 ${
                            ms.priority === 'high'
                              ? 'bg-rose-500/10 border-rose-500/20 text-rose-300'
                              : 'bg-amber-500/10 border-amber-500/20 text-amber-300'
                          }`}
                        >
                          <AlertTriangle className="h-3 w-3" />
                          <span>Missing: {ms.skill_name}</span>
                        </span>
                      ))}

                      <button
                        onClick={() => setExpandedCardId(isExpanded ? null : job.listing_id)}
                        className="text-[11px] font-semibold text-slate-400 hover:text-white ml-auto flex items-center gap-1 cursor-pointer"
                      >
                        <span>{isExpanded ? 'Hide Details' : 'Full Match Breakdown'}</span>
                        {isExpanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                      </button>
                    </div>

                    {/* Expandable Score Breakdown */}
                    {isExpanded && (
                      <div className="mt-5 pt-4 border-t border-slate-800/80 space-y-4 animate-in fade-in">
                        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 text-center">
                          <div className="p-2.5 rounded-xl bg-slate-950 border border-slate-800">
                            <span className="text-[10px] text-slate-500 uppercase tracking-wider block">Skills</span>
                            <span className="text-sm font-bold text-white font-mono">{job.skill_score.toFixed(0)}%</span>
                          </div>
                          <div className="p-2.5 rounded-xl bg-slate-950 border border-slate-800">
                            <span className="text-[10px] text-slate-500 uppercase tracking-wider block">Keywords</span>
                            <span className="text-sm font-bold text-white font-mono">{job.keyword_score.toFixed(0)}%</span>
                          </div>
                          <div className="p-2.5 rounded-xl bg-slate-950 border border-slate-800">
                            <span className="text-[10px] text-slate-500 uppercase tracking-wider block">Semantic</span>
                            <span className="text-sm font-bold text-white font-mono">{job.semantic_score.toFixed(0)}%</span>
                          </div>
                          <div className="p-2.5 rounded-xl bg-slate-950 border border-slate-800">
                            <span className="text-[10px] text-slate-500 uppercase tracking-wider block">Experience</span>
                            <span className="text-sm font-bold text-white font-mono">{job.experience_score.toFixed(0)}%</span>
                          </div>
                          <div className="p-2.5 rounded-xl bg-slate-950 border border-slate-800">
                            <span className="text-[10px] text-slate-500 uppercase tracking-wider block">Education</span>
                            <span className="text-sm font-bold text-white font-mono">{job.education_score.toFixed(0)}%</span>
                          </div>
                        </div>

                        <div>
                          <h4 className="text-xs font-semibold text-slate-300 mb-1.5">Description Snippet</h4>
                          <p className="text-xs text-slate-400 leading-relaxed bg-slate-950/60 p-3 rounded-xl border border-slate-800">
                            {job.description_snippet}
                          </p>
                        </div>
                      </div>
                    )}

                    {/* Bottom Action Row */}
                    <div className="mt-5 pt-4 border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-3">
                      <div className="flex flex-wrap items-center gap-3">
                        <span className={`px-2.5 py-1 rounded-lg border text-[11px] font-semibold flex items-center gap-1.5 ${getSourceBadge(job.source)}`}>
                          <Globe className="h-3 w-3" />
                          <span>Source: {job.source}</span>
                        </span>

                        {job.url && (
                          <a
                            href={job.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="px-3.5 py-1.5 rounded-xl bg-cyan-500/15 hover:bg-cyan-500/25 text-cyan-300 hover:text-cyan-200 border border-cyan-500/30 text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer shadow-sm"
                          >
                            <ExternalLink className="h-3.5 w-3.5" />
                            <span>View Original Job</span>
                          </a>
                        )}
                      </div>

                      <div className="flex items-center gap-2">
                        {job.is_saved && (
                          <select
                            value={job.application_status}
                            onChange={(e) => handleUpdateStatus(job.listing_id, e.target.value)}
                            className="px-2.5 py-1.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-brand-300 font-semibold focus:outline-none"
                          >
                            <option value="saved">Status: Saved</option>
                            <option value="applied">Status: Applied</option>
                            <option value="interview">Status: Interview</option>
                            <option value="rejected">Status: Rejected</option>
                            <option value="offer">Status: Offer</option>
                          </select>
                        )}

                        <button
                          onClick={() => navigate(`/analysis?job_id=${job.job_id}`)}
                          className="px-3.5 py-1.5 rounded-xl bg-brand-600/20 hover:bg-brand-600/30 text-brand-300 hover:text-brand-200 border border-brand-500/30 text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer"
                        >
                          <Target className="h-3.5 w-3.5 text-brand-400" />
                          <span>Detailed Alignment & Roadmap</span>
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* ================= TAB 2: SAVED & APPLICATIONS ================= */}
      {activeTab === 'saved' && (
        <div className="space-y-4">
          {savedLoading ? (
            <div className="py-20 text-center">
              <Loader2 className="h-8 w-8 animate-spin text-brand-500 mx-auto mb-2" />
              <p className="text-xs text-slate-400">Loading saved jobs...</p>
            </div>
          ) : savedJobs.length === 0 ? (
            <div className="glass-panel p-12 rounded-2xl border border-slate-800 text-center">
              <div className="h-16 w-16 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-500 mx-auto mb-4">
                <Bookmark className="h-8 w-8 text-slate-600" />
              </div>
              <h3 className="text-base font-bold text-white mb-1">No Saved Jobs Yet</h3>
              <p className="text-xs text-slate-400 max-w-md mx-auto mb-6">
                Bookmark top opportunities from AI Discovered Jobs to track application stages from applied to offer.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {savedJobs.map((saved) => (
                <div key={saved.id} className="glass-panel p-5 rounded-2xl border border-slate-800 flex flex-col justify-between">
                  <div>
                    <div className="flex items-start justify-between gap-3 mb-2">
                      <h3 className="text-base font-bold text-white leading-snug">{saved.title}</h3>
                      <button
                        onClick={() => jobSearchApi.unsaveJob(saved.job_listing_id).then(() => fetchSavedJobs())}
                        className="text-slate-500 hover:text-rose-400 transition-colors p-1"
                        title="Remove bookmark"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>

                    <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400 mb-4">
                      {saved.company && <span>{saved.company}</span>}
                      {saved.location && <span>• {saved.location}</span>}
                      {saved.remote_type === 'remote' && <span className="text-cyan-400">• Remote</span>}
                    </div>
                  </div>

                  <div className="pt-4 border-t border-slate-800/80 flex items-center justify-between gap-3">
                    <select
                      value={saved.status}
                      onChange={(e) => handleUpdateStatus(saved.job_listing_id, e.target.value)}
                      className="px-3 py-1.5 rounded-xl bg-slate-950 border border-slate-800 text-xs font-semibold text-brand-300 focus:outline-none"
                    >
                      <option value="saved">Stage: Saved</option>
                      <option value="applied">Stage: Applied</option>
                      <option value="interview">Stage: Interview</option>
                      <option value="rejected">Stage: Rejected</option>
                      <option value="offer">Stage: Offer</option>
                    </select>

                    {saved.url && (
                      <a
                        href={saved.url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-xs text-slate-400 hover:text-white flex items-center gap-1"
                      >
                        <span>Open Listing</span>
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ================= TAB 3: MANUAL OPPORTUNITIES ================= */}
      {activeTab === 'manual' && (
        <div>
          {manualLoading ? (
            <div className="py-20 text-center">
              <Loader2 className="h-8 w-8 animate-spin text-brand-500 mx-auto mb-2" />
              <p className="text-xs text-slate-400">Loading manual jobs...</p>
            </div>
          ) : manualJobs.length === 0 ? (
            <div className="glass-panel p-12 rounded-2xl border border-slate-800 text-center">
              <div className="h-16 w-16 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-500 mx-auto mb-4">
                <Briefcase className="h-8 w-8 text-slate-500" />
              </div>
              <h3 className="text-base font-bold text-white mb-1">No manual jobs entered</h3>
              <p className="text-xs text-slate-400 max-w-md mx-auto mb-6">
                Paste any custom job description to parse qualifications and evaluate candidate alignment.
              </p>
              <button
                onClick={() => setShowManualModal(true)}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-750 text-white text-xs font-semibold inline-flex items-center gap-2 transition-colors cursor-pointer"
              >
                <Plus className="h-4 w-4 text-brand-400" />
                <span>Add First Job</span>
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {manualJobs.map((job) => (
                <div
                  key={job.id}
                  className="glass-panel p-6 rounded-2xl border border-slate-800 hover:border-slate-700 transition-all flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-start justify-between gap-4 mb-3">
                      <div>
                        <h3 className="text-lg font-bold text-white leading-snug">{job.title}</h3>
                        <div className="flex items-center gap-3 text-xs text-slate-400 mt-1">
                          {job.company && (
                            <div className="flex items-center gap-1">
                              <Building className="h-3.5 w-3.5 text-slate-500" />
                              <span>{job.company}</span>
                            </div>
                          )}
                          <div className="flex items-center gap-1">
                            <Calendar className="h-3.5 w-3.5 text-slate-500" />
                            <span>{new Date(job.created_at).toLocaleDateString()}</span>
                          </div>
                        </div>
                      </div>

                      <button
                        onClick={() => handleDeleteManualJob(job.id, job.title)}
                        className="p-1.5 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors cursor-pointer"
                        title="Delete job"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>

                    <div className="mb-4">
                      <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-2">
                        Requirements ({job.requirements.length})
                      </span>
                      <div className="flex flex-wrap gap-1.5 max-h-24 overflow-y-auto">
                        {job.requirements.map((r) => (
                          <span
                            key={r.id}
                            className={`px-2 py-0.5 rounded text-[11px] font-medium border ${
                              r.is_required
                                ? 'bg-brand-500/10 text-brand-300 border-brand-500/20'
                                : 'bg-slate-800 text-slate-300 border-slate-700'
                            }`}
                          >
                            {r.normalized_skill_name}
                          </span>
                        ))}
                      </div>
                    </div>

                    <p className="text-xs text-slate-400 line-clamp-3 leading-relaxed mb-6">{job.description}</p>
                  </div>

                  <div className="flex items-center justify-between pt-4 border-t border-slate-800/80">
                    {job.source_url ? (
                      <a
                        href={job.source_url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-xs text-slate-500 hover:text-slate-300 flex items-center gap-1 transition-colors"
                      >
                        <span>View Posting</span>
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    ) : (
                      <span className="text-xs text-slate-600">Manual Entry</span>
                    )}

                    <button
                      onClick={() => navigate(`/analysis?job_id=${job.id}`)}
                      className="px-3.5 py-1.5 rounded-xl bg-brand-600/20 hover:bg-brand-600/30 text-brand-300 hover:text-brand-200 border border-brand-500/30 text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer"
                    >
                      <Target className="h-3.5 w-3.5 text-brand-400" />
                      <span>Match Against Resume</span>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ================= TAB 4: SEARCH HISTORY ================= */}
      {activeTab === 'history' && (
        <div className="space-y-4">
          {historyLoading ? (
            <div className="py-20 text-center">
              <Loader2 className="h-8 w-8 animate-spin text-brand-500 mx-auto mb-2" />
              <p className="text-xs text-slate-400">Loading history...</p>
            </div>
          ) : searchHistory.length === 0 ? (
            <div className="glass-panel p-12 rounded-2xl border border-slate-800 text-center">
              <Clock className="h-8 w-8 text-slate-600 mx-auto mb-3" />
              <h3 className="text-base font-bold text-white mb-1">No search history</h3>
              <p className="text-xs text-slate-400">Automated job searches will appear here for quick access.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {searchHistory.map((sh) => (
                <div
                  key={sh.id}
                  className="glass-panel p-5 rounded-2xl border border-slate-800 flex items-center justify-between gap-4"
                >
                  <div>
                    <h4 className="text-sm font-bold text-white">{sh.query_role}</h4>
                    <div className="flex items-center gap-3 text-xs text-slate-400 mt-1">
                      {sh.location && <span>{sh.location}</span>}
                      {sh.remote && <span className="text-cyan-400">• Remote</span>}
                      <span>• {new Date(sh.created_at).toLocaleDateString()}</span>
                      <span>• {sh.jobs_matched} matches</span>
                    </div>
                  </div>

                  <button
                    onClick={() => loadSearchResults(sh.id)}
                    className="px-3.5 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer"
                  >
                    <RotateCcw className="h-3.5 w-3.5 text-brand-400" />
                    <span>View Results</span>
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ================= MODAL: FIND JOBS AUTOMATICALLY ================= */}
      {showSearchModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-2xl max-h-[90vh] flex flex-col shadow-2xl">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800">
              <div className="flex items-center gap-2.5">
                <div className="h-8 w-8 rounded-lg bg-gradient-to-tr from-brand-600 to-cyan-500 flex items-center justify-center text-slate-950 font-bold">
                  <Search className="h-4 w-4" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">AI Job Search Agent</h3>
                  <p className="text-[11px] text-slate-400">Discover and match live openings across verified feeds</p>
                </div>
              </div>
              <button
                onClick={() => setShowSearchModal(false)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleStartSearch} className="p-6 space-y-4 overflow-y-auto flex-1">
              {/* Resume Selector */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                  Benchmark Against Resume *
                </label>
                <select
                  value={selectedResumeId}
                  onChange={(e) => setSelectedResumeId(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-white text-xs font-medium focus:outline-none focus:border-brand-500"
                >
                  {resumes.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.name} {r.is_primary ? '(Primary Resume)' : ''}
                    </option>
                  ))}
                </select>
              </div>

              {/* Target Role & Location */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                    Target Role Title *
                  </label>
                  <input
                    type="text"
                    required
                    value={searchRole}
                    onChange={(e) => setSearchRole(e.target.value)}
                    placeholder="e.g. Python Backend Developer"
                    className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white placeholder-slate-500 text-xs focus:outline-none focus:border-brand-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                    Target Location
                  </label>
                  <input
                    type="text"
                    value={searchLocation}
                    onChange={(e) => setSearchLocation(e.target.value)}
                    placeholder="e.g. Bangalore, London, New York"
                    className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white placeholder-slate-500 text-xs focus:outline-none focus:border-brand-500"
                  />
                </div>
              </div>

              {/* Experience & Employment Type */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                    Experience Level
                  </label>
                  <select
                    value={searchExperience}
                    onChange={(e) => setSearchExperience(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white text-xs focus:outline-none focus:border-brand-500"
                  >
                    <option value="0-2 years">0-2 years (Entry)</option>
                    <option value="3-5 years">3-5 years (Mid)</option>
                    <option value="5+ years">5+ years (Senior)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                    Employment
                  </label>
                  <select
                    value={searchEmploymentType}
                    onChange={(e) => setSearchEmploymentType(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white text-xs focus:outline-none focus:border-brand-500"
                  >
                    <option value="full-time">Full-time</option>
                    <option value="contract">Contract</option>
                    <option value="internship">Internship</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                    Posted Within
                  </label>
                  <select
                    value={searchPostedDays}
                    onChange={(e) => setSearchPostedDays(Number(e.target.value))}
                    className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white text-xs focus:outline-none focus:border-brand-500"
                  >
                    <option value={3}>Last 3 days</option>
                    <option value={7}>Last 7 days</option>
                    <option value={14}>Last 14 days</option>
                    <option value={30}>Last 30 days</option>
                  </select>
                </div>
              </div>

              {/* Remote Checkbox */}
              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="remoteCheckbox"
                  checked={searchRemote}
                  onChange={(e) => setSearchRemote(e.target.checked)}
                  className="rounded border-slate-800 text-brand-600 focus:ring-brand-500 h-4 w-4 bg-slate-950"
                />
                <label htmlFor="remoteCheckbox" className="text-xs text-slate-300 font-medium cursor-pointer">
                  Prioritize Remote and Work-From-Home roles
                </label>
              </div>

              {/* Target Skills Tags */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                  Target Skills (Auto-inferred from resume)
                </label>
                <div className="flex items-center gap-2 mb-2">
                  <input
                    type="text"
                    value={skillInput}
                    onChange={(e) => setSkillInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addSkillChip())}
                    placeholder="Type skill & hit enter..."
                    className="flex-1 px-3 py-1.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-brand-500"
                  />
                  <button
                    type="button"
                    onClick={addSkillChip}
                    className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold cursor-pointer"
                  >
                    Add
                  </button>
                </div>

                <div className="flex flex-wrap gap-1.5 max-h-24 overflow-y-auto p-2 rounded-xl bg-slate-950 border border-slate-800/80">
                  {searchSkills.map((s, idx) => (
                    <span
                      key={idx}
                      className="px-2.5 py-1 rounded-lg bg-brand-500/15 border border-brand-500/30 text-brand-300 text-xs flex items-center gap-1.5 font-medium"
                    >
                      <span>{s}</span>
                      <X
                        className="h-3 w-3 text-brand-400 hover:text-white cursor-pointer"
                        onClick={() => removeSkillChip(s)}
                      />
                    </span>
                  ))}
                </div>
              </div>

              {/* Submit Buttons */}
              <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowSearchModal(false)}
                  className="px-4 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-white transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSearchSubmitting}
                  className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-brand-600 to-cyan-600 hover:from-brand-500 hover:to-cyan-500 text-slate-950 font-bold text-xs flex items-center gap-2 transition-all cursor-pointer shadow-md shadow-brand-600/30"
                >
                  {isSearchSubmitting ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      <span>Launching Agent...</span>
                    </>
                  ) : (
                    <>
                      <Sparkles className="h-4 w-4" />
                      <span>Launch AI Job Search Agent</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ================= MODAL: MANUAL JOB ENTRY ================= */}
      {showManualModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-2xl max-h-[90vh] flex flex-col shadow-2xl">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800">
              <div className="flex items-center gap-2.5">
                <div className="h-8 w-8 rounded-lg bg-brand-500/10 border border-brand-500/20 flex items-center justify-center text-brand-400">
                  <Briefcase className="h-4 w-4" />
                </div>
                <h3 className="text-base font-bold text-white">Add Manual Job Description</h3>
              </div>
              <button
                onClick={() => setShowManualModal(false)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleCreateManualJob} className="p-6 space-y-4 overflow-y-auto flex-1">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                    Job Title *
                  </label>
                  <input
                    type="text"
                    required
                    value={manualTitle}
                    onChange={(e) => setManualTitle(e.target.value)}
                    placeholder="e.g. Senior Backend Engineer"
                    className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white placeholder-slate-500 text-xs focus:outline-none focus:border-brand-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                    Company Name
                  </label>
                  <input
                    type="text"
                    value={manualCompany}
                    onChange={(e) => setManualCompany(e.target.value)}
                    placeholder="e.g. Stripe, Netflix, Google"
                    className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white placeholder-slate-500 text-xs focus:outline-none focus:border-brand-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                  Job Description / Requirements Text *
                </label>
                <textarea
                  required
                  rows={8}
                  value={manualDescription}
                  onChange={(e) => setManualDescription(e.target.value)}
                  placeholder="Paste the full job posting description here including responsibilities and required qualifications..."
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-white placeholder-slate-500 text-xs leading-relaxed focus:outline-none focus:border-brand-500 font-sans"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                  Source Link (Optional)
                </label>
                <input
                  type="url"
                  value={manualSourceUrl}
                  onChange={(e) => setManualSourceUrl(e.target.value)}
                  placeholder="https://company.com/careers/job-id"
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-white placeholder-slate-500 text-xs focus:outline-none focus:border-brand-500"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowManualModal(false)}
                  className="px-4 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-white transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isManualSubmitting}
                  className="px-5 py-2 rounded-xl bg-brand-600 hover:bg-brand-500 text-slate-950 font-bold text-xs flex items-center gap-2 transition-all cursor-pointer shadow-md shadow-brand-600/30"
                >
                  {isManualSubmitting ? (
                    <>
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      <span>Parsing Requirements...</span>
                    </>
                  ) : (
                    <span>Save & Extract Requirements</span>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
