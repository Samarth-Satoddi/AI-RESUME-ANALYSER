import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Resume, ResumeSection } from '../../types/resume';
import { resumeApi } from '../../api/resumes';
import {
  Star,
  Download,
  Trash2,
  Calendar,
  HardDrive,
  Loader2,
  Eye,
  X,
  Tag,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Sparkles,
  Award,
} from 'lucide-react';


interface ResumeCardProps {
  resume: Resume;
  onDelete: (id: string) => void;
  onSetPrimary: (updated: Resume) => void;
}

export const ResumeCard: React.FC<ResumeCardProps> = ({ resume, onDelete, onSetPrimary }) => {
  const navigate = useNavigate();
  const [isDeleting, setIsDeleting] = useState(false);
  const [isSettingPrimary, setIsSettingPrimary] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [showSections, setShowSections] = useState(false);
  const [isLoadingSections, setIsLoadingSections] = useState(false);
  const [sections, setSections] = useState<ResumeSection[]>([]);
  const [isReparsing, setIsReparsing] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const formatSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const formatDate = (isoString: string): string => {
    try {
      return new Date(isoString).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      });
    } catch {
      return isoString;
    }
  };

  const getParserStatusBadge = () => {
    if (resume.parser_status === 'completed') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          <CheckCircle2 className="h-3 w-3" /> Parsed
        </span>
      );
    }
    if (resume.parser_status === 'failed') {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
          <AlertCircle className="h-3 w-3" /> Failed
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
        <Loader2 className="h-3 w-3 animate-spin" /> Processing
      </span>
    );
  };

  const handleDownload = async () => {
    setIsDownloading(true);
    try {
      await resumeApi.downloadResume(resume.id, resume.original_filename);
    } catch {
      alert('Failed to download resume.');
    } finally {
      setIsDownloading(false);
    }
  };

  const handleSetPrimary = async () => {
    setIsSettingPrimary(true);
    try {
      const updated = await resumeApi.setPrimaryResume(resume.id);
      onSetPrimary(updated);
    } catch {
      alert('Failed to set resume as primary.');
    } finally {
      setIsSettingPrimary(false);
    }
  };

  const handleViewSections = async () => {
    setShowSections(true);
    setIsLoadingSections(true);
    try {
      const data = await resumeApi.getResumeSections(resume.id);
      setSections(data.sections);
    } catch {
      alert('Failed to load resume sections.');
    } finally {
      setIsLoadingSections(false);
    }
  };

  const handleReparse = async () => {
    setIsReparsing(true);
    try {
      const data = await resumeApi.parseResume(resume.id);
      setSections(data.sections);
    } catch {
      alert('Failed to reparse sections.');
    } finally {
      setIsReparsing(false);
    }
  };

  const handleDeleteClick = () => {
    setDeleteError(null);
    setShowDeleteConfirm(true);
  };

  const handleConfirmDelete = async () => {
    setIsDeleting(true);
    setDeleteError(null);
    try {
      await resumeApi.deleteResume(resume.id);
      setShowDeleteConfirm(false);
      onDelete(resume.id);
    } catch (err: any) {
      console.error('Failed to delete resume:', err);
      setDeleteError(err?.response?.data?.detail || 'Failed to delete resume. Please try again.');
      setIsDeleting(false);
    }
  };

  return (
    <>
      <div
        className={`glass-panel p-6 rounded-2xl border transition-all flex flex-col justify-between ${
          resume.is_primary ? 'border-brand-500/40 shadow-lg shadow-brand-500/5' : 'border-slate-800 hover:border-slate-700'
        }`}
      >
        <div>
          {/* Top Header: Type, Version & Primary Badge */}
          <div className="flex items-center justify-between gap-2 mb-4">
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 rounded-md text-[11px] font-bold uppercase tracking-wider bg-slate-800 text-slate-300 border border-slate-700">
                {resume.file_type} • v{resume.version_number}
              </span>
              {getParserStatusBadge()}
            </div>

            {resume.is_primary ? (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-brand-500/10 text-brand-400 border border-brand-500/20">
                <Star className="h-3 w-3 fill-brand-400" /> Primary
              </span>
            ) : (
              <button
                onClick={handleSetPrimary}
                disabled={isSettingPrimary}
                className="text-xs text-slate-400 hover:text-brand-300 font-medium transition-colors cursor-pointer"
              >
                {isSettingPrimary ? 'Setting...' : 'Set as Primary'}
              </button>
            )}
          </div>

          {/* Title & Filename */}
          <h3 className="text-lg font-bold text-white mb-1 truncate" title={resume.name}>
            {resume.name}
          </h3>
          <p className="text-xs text-slate-400 mb-4 truncate font-mono" title={resume.original_filename}>
            {resume.original_filename}
          </p>

          {/* File Size & Upload Date */}
          <div className="flex items-center gap-4 text-xs text-slate-400 mb-4">
            <div className="flex items-center gap-1.5">
              <HardDrive className="h-3.5 w-3.5 text-slate-500" />
              <span>{formatSize(resume.file_size)}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Calendar className="h-3.5 w-3.5 text-slate-500" />
              <span>Uploaded {formatDate(resume.created_at)}</span>
            </div>
          </div>

          {/* Detected Sections & Extracted Skills Metrics */}
          <div className="grid grid-cols-2 gap-2 p-2.5 rounded-xl bg-slate-950/60 border border-slate-850 mb-5">
            <div className="flex items-center gap-2 px-2 py-1">
              <Tag className="h-3.5 w-3.5 text-brand-400" />
              <div>
                <span className="text-[11px] text-slate-400 block">Sections</span>
                <span className="text-xs font-bold text-white">{resume.sections_count ?? 0} detected</span>
              </div>
            </div>
            <div className="flex items-center gap-2 px-2 py-1 border-l border-slate-800">
              <Award className="h-3.5 w-3.5 text-indigo-400" />
              <div>
                <span className="text-[11px] text-slate-400 block">Skills</span>
                <span className="text-xs font-bold text-white">{resume.skills_count ?? 0} extracted</span>
              </div>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div>
          {/* Analyze Resume Primary Button */}
          <button
            onClick={() => navigate(`/analysis?resume_id=${resume.id}`)}
            className="w-full mb-3 py-2 px-4 rounded-xl bg-gradient-to-r from-brand-600 to-indigo-600 hover:from-brand-500 hover:to-indigo-500 text-white font-semibold text-xs flex items-center justify-center gap-2 shadow-md shadow-brand-500/20 transition-all cursor-pointer"
            title={`Analyze ${resume.name}`}
          >
            <Sparkles className="h-3.5 w-3.5" />
            <span>Analyze Resume</span>
          </button>

          {/* Secondary Actions */}
          <div className="flex items-center justify-between pt-3 border-t border-slate-800/80">
            <button
              onClick={handleViewSections}
              className="text-xs font-semibold text-slate-300 hover:text-white flex items-center gap-1.5 transition-colors cursor-pointer px-2 py-1 rounded-lg hover:bg-slate-800/60"
            >
              <Eye className="h-3.5 w-3.5 text-brand-400" />
              <span>View Sections</span>
            </button>

            <div className="flex items-center gap-1.5">
              <button
                onClick={handleDownload}
                disabled={isDownloading}
                className="p-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors cursor-pointer"
                title="Download original file"
              >
                {isDownloading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />}
              </button>

              <button
                type="button"
                onClick={handleDeleteClick}
                disabled={isDeleting}
                className="p-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 hover:text-rose-300 border border-rose-500/20 transition-colors cursor-pointer"
                title="Delete resume"
              >
                {isDeleting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Detected Sections Modal */}
      {showSections && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-3xl max-h-[85vh] flex flex-col shadow-2xl">
            {/* Modal Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800">
              <div className="flex items-center gap-3">
                <div className="h-9 w-9 rounded-xl bg-brand-500/10 border border-brand-500/20 flex items-center justify-center text-brand-400">
                  <Tag className="h-4 w-4" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white leading-tight">
                    Detected Resume Sections
                  </h3>
                  <p className="text-xs text-slate-400">
                    {resume.name} • {sections.length} sections identified
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={handleReparse}
                  disabled={isReparsing}
                  className="px-2.5 py-1.5 rounded-lg bg-slate-800 text-xs font-medium text-slate-300 hover:text-white flex items-center gap-1.5 transition-colors cursor-pointer"
                  title="Re-run section detector"
                >
                  <RefreshCw className={`h-3.5 w-3.5 ${isReparsing ? 'animate-spin' : ''}`} />
                  <span>Reparse</span>
                </button>
                <button
                  onClick={() => setShowSections(false)}
                  className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition-colors cursor-pointer"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
            </div>

            {/* Modal Body */}
            <div className="p-6 overflow-y-auto space-y-4 flex-1">
              {isLoadingSections ? (
                <div className="py-12 text-center text-slate-400">
                  <Loader2 className="h-8 w-8 animate-spin text-brand-500 mx-auto mb-2" />
                  <p className="text-xs">Analyzing resume section boundaries...</p>
                </div>
              ) : sections.length === 0 ? (
                <div className="py-12 text-center text-slate-500 text-xs">
                  No structured sections detected. Click "Reparse" to extract again.
                </div>
              ) : (
                sections.map((sec) => (
                  <div
                    key={sec.id}
                    className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-slate-700 transition-colors"
                  >
                    <div className="flex items-center justify-between gap-2 mb-2">
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-brand-500/10 text-brand-400 border border-brand-500/20">
                          {sec.section_type}
                        </span>
                        <span className="text-xs text-slate-400 font-semibold">
                          {sec.section_order + 1}. {sec.section_type.toUpperCase()}
                        </span>
                      </div>
                      <span className="text-[10px] text-slate-600 font-mono">
                        order: {sec.section_order}
                      </span>
                    </div>
                    <pre className="text-xs text-slate-300 whitespace-pre-wrap font-sans leading-relaxed bg-slate-900/40 p-3 rounded-lg border border-slate-850 max-h-48 overflow-y-auto">
                      {sec.content || <span className="text-slate-600 italic">(Empty section content)</span>}
                    </pre>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md shadow-2xl p-6 text-left">
            <div className="flex items-center gap-3 mb-4">
              <div className="h-10 w-10 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400 shrink-0">
                <Trash2 className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-white">Delete Resume</h3>
                <p className="text-xs text-slate-400">This action cannot be undone</p>
              </div>
            </div>

            <p className="text-sm text-slate-300 mb-4 leading-relaxed">
              Are you sure you want to permanently delete <strong className="text-white font-semibold">{resume.name}</strong>? All extracted sections, skills, and analysis results linked to this resume will be removed.
            </p>

            {deleteError && (
              <div className="mb-4 p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center gap-2">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{deleteError}</span>
              </div>
            )}

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setShowDeleteConfirm(false)}
                disabled={isDeleting}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmDelete}
                disabled={isDeleting}
                className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold flex items-center gap-2 shadow-lg shadow-rose-600/20 transition-all cursor-pointer disabled:opacity-50"
              >
                {isDeleting ? (
                  <>
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    <span>Deleting...</span>
                  </>
                ) : (
                  <>
                    <Trash2 className="h-3.5 w-3.5" />
                    <span>Delete Resume</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

