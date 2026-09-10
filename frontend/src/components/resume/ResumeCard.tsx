import React, { useState } from 'react';
import { Resume, ResumeSection } from '../../types/resume';
import { resumeApi } from '../../api/resumes';
import {
  Star,
  Download,
  Trash2,
  Calendar,
  Layers,
  HardDrive,
  Loader2,
  Eye,
  X,
  Tag,
  RefreshCw,
} from 'lucide-react';


interface ResumeCardProps {
  resume: Resume;
  onDelete: (id: string) => void;
  onSetPrimary: (updated: Resume) => void;
}

export const ResumeCard: React.FC<ResumeCardProps> = ({ resume, onDelete, onSetPrimary }) => {
  const [isDeleting, setIsDeleting] = useState(false);
  const [isSettingPrimary, setIsSettingPrimary] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [showSections, setShowSections] = useState(false);
  const [isLoadingSections, setIsLoadingSections] = useState(false);
  const [sections, setSections] = useState<ResumeSection[]>([]);
  const [isReparsing, setIsReparsing] = useState(false);

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

  const handleDelete = async () => {
    if (!window.confirm(`Are you sure you want to delete "${resume.name}"?`)) {
      return;
    }

    setIsDeleting(true);
    try {
      await resumeApi.deleteResume(resume.id);
      onDelete(resume.id);
    } catch {
      alert('Failed to delete resume.');
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
          {/* Top Header: Type & Badges */}
          <div className="flex items-center justify-between gap-2 mb-4">
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 rounded-md text-[11px] font-bold uppercase tracking-wider bg-slate-800 text-slate-300 border border-slate-700">
                {resume.file_type}
              </span>
              <span className="inline-flex items-center gap-1 text-xs text-slate-400 font-medium">
                <Layers className="h-3 w-3 text-slate-500" />
                <span>v{resume.version_number}</span>
              </span>
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

          {/* Title & Metadata */}
          <h3 className="text-lg font-bold text-white mb-1 truncate" title={resume.name}>
            {resume.name}
          </h3>
          <p className="text-xs text-slate-400 mb-4 truncate" title={resume.original_filename}>
            {resume.original_filename}
          </p>

          <div className="flex items-center gap-4 text-xs text-slate-400 mb-6">
            <div className="flex items-center gap-1.5">
              <HardDrive className="h-3.5 w-3.5 text-slate-500" />
              <span>{formatSize(resume.file_size)}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Calendar className="h-3.5 w-3.5 text-slate-500" />
              <span>{formatDate(resume.created_at)}</span>
            </div>
          </div>
        </div>

        {/* Action Footer */}
        <div className="flex items-center justify-between pt-4 border-t border-slate-800/80">
          <button
            onClick={handleViewSections}
            className="text-xs font-semibold text-brand-400 hover:text-brand-300 flex items-center gap-1.5 transition-colors cursor-pointer"
          >
            <Eye className="h-3.5 w-3.5" />
            <span>Sections</span>
          </button>

          <div className="flex items-center gap-2">
            <button
              onClick={handleDownload}
              disabled={isDownloading}
              className="p-2 rounded-lg bg-slate-800/80 hover:bg-slate-750 text-slate-300 hover:text-white transition-colors cursor-pointer"
              title="Download original file"
            >
              {isDownloading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
            </button>

            <button
              onClick={handleDelete}
              disabled={isDeleting}
              className="p-2 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 hover:text-rose-300 border border-rose-500/20 transition-colors cursor-pointer"
              title="Delete resume"
            >
              {isDeleting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
            </button>
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
    </>
  );
};

